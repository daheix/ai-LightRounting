"""PoLaRIS Web Server - 流水线执行模块（polaris-gui 子模块）。

从 ``web_server.py`` 拆分而来，包含布局布线流水线执行与 Showcase 全流程:
- _extract_placements / _extract_paths: 结果提取
- _run_pipeline: 一键布局布线
- _run_showcase_background: 端到端 Demo Showcase 后台执行

来源:
- Python http.server: https://docs.python.org/3/library/http.server.html
- DREAMPlace (GPU 布局布线深度学习) https://arxiv.org/abs/2004.10746
- AlphaChip (Google RL 宏布局) https://www.nature.com/articles/s41586-021-03544-w
- TILOS MacroPlacement benchmark
  https://github.com/TILOS-AI-CAD-Institute/MacroPlacement
- Apollo (ASU 布局布线 RL) https://github.com/ASU-LOPE-Group/Apollo
- LiDAR ISPD 2025 (布线竞赛) https://arxiv.org/html/2505.17239v1
- gdsfactory PDK 流水线 https://github.com/gdsfactory/gdsfactory

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU。
"""

from __future__ import annotations

import logging
import threading
import traceback
from datetime import datetime
from pathlib import Path

from .web_server_helpers import _showcase_lock, logger
from .web_server_presets import _build_circuit

def _extract_placements(result) -> list[dict]:
    """从 PipelineResult 提取器件布局列表。"""
    placements = []
    for name, pl in result.placements.items():
        placements.append({"name": name, "x": pl["x"], "y": pl["y"], "w": pl["w"], "h": pl["h"]})
    return placements


def _extract_paths(result) -> list[dict]:
    """从 PipelineResult 提取布线路径列表。"""
    paths = []
    for conn_key, pts in result.paths.items():
        if hasattr(pts, "points"):
            points, length_um, loss_db = pts.points, pts.length_um, pts.loss_db
        elif isinstance(pts, list):
            points, length_um, loss_db = pts, 0.0, 0.0
        else:
            points = pts.get("points", [])
            length_um = pts.get("length_um", 0)
            loss_db = pts.get("loss_db", 0)
        paths.append(
            {
                "connection": conn_key,
                "points": points,
                "length_um": length_um,
                "loss_db": loss_db,
            }
        )
    return paths


def _run_pipeline(preset_id: str, router_type: str = "curvy") -> dict:
    """运行布局布线流水线，返回结果 dict。

    R391 修复: 原 raise ImportError 依赖未迁移的 polaris_orchestrator.
    IntegratedPipeline，现调用 polaris_flow STAGE_EXECUTORS 1-4 阶段
    （PDK 加载→电路构建→布局→布线），复用 R391 打通的标准化流水线。

    默认使用 curvy router（euler 弯曲布线），自动满足弯曲半径约束。
    "default" 映射到 "curvy"，因为 A* 网格布线的直角弯半径 < min_bend_radius，
    会产生 DRC 违规。curvy router 用 euler 曲线替换直角弯，损耗更低。

    来源: LiDAR ISPD'25 curvy-aware routing
      https://dl.acm.org/doi/10.1145/3698364.3705355

    Returns:
        含 placements/paths/circuit/n_placed/n_paths/total_length_um 的 SimpleNamespace。
    """
    import tempfile
    from types import SimpleNamespace

    from polaris_core import circuit_to_dict
    from polaris_flow.executors import STAGE_EXECUTORS
    from polaris_flow.recipe import Recipe
    from polaris_flow.workspace import Workspace

    circuit = _build_circuit(preset_id)
    circuit_dict = circuit_to_dict(circuit)

    router_algo = "curvy" if router_type in ("default", "curvy") else router_type

    tmp = tempfile.mkdtemp(prefix="polaris_pipeline_")
    recipe = Recipe(
        preset_id=preset_id,
        platform="SOI",
        placement_algo="analytical",
        router_algo=router_algo,
    )
    ws = Workspace(output_dir=tmp, job_id=f"pipeline-{preset_id}")
    prev: dict = {}
    for stage_id in (1, 2, 3, 4):
        out = STAGE_EXECUTORS[stage_id](recipe, ws, prev)
        prev.update(out)

    return SimpleNamespace(
        circuit=circuit_dict,
        placements=prev["placements"],
        paths=prev["routes"],
        n_placed=prev.get("n_placed", len(prev["placements"])),
        n_paths=prev.get("n_paths", len(prev["routes"])),
        total_length_um=prev.get("total_length_um", 0.0),
        router_type=router_algo,
    )


# Showcase 输出子目录列表
_SHOWCASE_SUBDIRS = ["logs", "gds", "verilog_a", "spice", "reports"]


def _run_showcase_background(run_id: str, output_dir: str) -> None:
    """在后台线程中运行端到端 Demo Showcase 全流程。

    顺序执行 9 个阶段，每阶段用 StageLogger 包裹，结构化日志写入
    output_dir/logs/showcase.jsonl。运行前清空 JSONL 文件，避免历史记录污染。

    Args:
        run_id: 运行 ID（时间戳格式 YYYYMMDD_HHMMSS）。
        output_dir: 输出目录路径。
    """
    try:
        # 添加 examples/e2e_showcase 到 sys.path，使 stages/ 与同级模块可被导入
        showcase_dir = Path(__file__).parent.parent.parent.parent.parent / "examples" / "e2e_showcase"
        if str(showcase_dir) not in sys.path:
            sys.path.insert(0, str(showcase_dir))

        from logging_config import StageLogger, setup_logging  # noqa: E402
        from stages import (  # noqa: E402
            stage1_pdk_catalog,
            stage2_circuit_spec,
            stage3_ai_placement,
            stage4_routing,
            stage5_simulation,
            stage6_drc_lvs,
            stage7_gds_export,
            stage8_opto_electrical,
            stage9_quantum_photonics,
        )

        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        for subdir in _SHOWCASE_SUBDIRS:
            (out_dir / subdir).mkdir(parents=True, exist_ok=True)

        # 清空 JSONL 日志文件，避免历史记录污染本次运行结果
        jsonl_path = out_dir / "logs" / "showcase.jsonl"
        jsonl_path.write_text("", encoding="utf-8")

        setup_logging(out_dir)

        stages = [
            (1, "PDK 器件目录展示", stage1_pdk_catalog),
            (2, "电路规格定义", stage2_circuit_spec),
            (3, "AI 布局", stage3_ai_placement),
            (4, "智能布线", stage4_routing),
            (5, "仿真验证", stage5_simulation),
            (6, "DRC/LVS 验证", stage6_drc_lvs),
            (7, "GDS 导出", stage7_gds_export),
            (8, "光电协同", stage8_opto_electrical),
            (9, "量子光子验证", stage9_quantum_photonics),
        ]

        for stage_id, stage_name, stage_module in stages:
            with StageLogger(stage_id, stage_name, out_dir) as sl:
                # 记录输入参数（修复 P0: inputs 字段始终为空）
                sl.log_input("output_dir", str(out_dir))
                sl.log_input("stage_module", stage_module.__name__)
                result = stage_module.run(out_dir)
                if result:
                    for key, value in result.items():
                        sl.log_output(key, value)

        # R05 Bug 修复 v4.0-WEB-LOCK: _showcase_runs 写操作加锁
        with _showcase_lock:
            _showcase_runs[run_id]["status"] = "done"
        logger.info("Showcase 运行完成: run_id=%s", run_id)
    except Exception as e:
        logger.error(
            "Showcase 运行失败: run_id=%s, 错误: %s\n%s",
            run_id, e, traceback.format_exc(),
        )
        # R05 Bug 修复 v4.0-WEB-LOCK: _showcase_runs 写操作加锁
        with _showcase_lock:
            _showcase_runs[run_id]["status"] = "failed"
            _showcase_runs[run_id]["error"] = str(e)



__all__ = ["_run_pipeline", "_run_showcase_background"]
