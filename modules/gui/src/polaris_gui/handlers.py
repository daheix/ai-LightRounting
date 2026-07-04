"""PoLaRIS Web Server 业务逻辑处理器（handlers.py）。

从 web_server.py 拆分而来（R11 质量门禁：文件≤800行），保留原始文献溯源。

包含 Web Server 的业务逻辑层：
- 全局状态（调度器/追踪器/Showcase 运行记录）的线程安全懒初始化
- 电路预设构建（MZI / Ring）
- 流水线运行与结果提取
- Showcase 后台线程执行

文献来源（R02 学术诚信，≥5 条）：
1. Python http.server: https://docs.python.org/3/library/http.server.html
2. Python threading.Lock: https://docs.python.org/3/library/threading.html#lock-objects
3. Double-checked locking: https://en.wikipedia.org/wiki/Double-checked_locking
4. SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
5. KLayout DRC 文档: https://www.klayout.org/doc-qt5/manual/drc_runsets.html
6. KLayout LVS 文档: https://www.klayout.org/downloads/master/doc-qt5/manual/lvs_compare.html
7. OWASP Error Handling: https://owasp.org/www-community/Improper_Error_Handling
8. CWE-209 Information Exposure: https://cwe.mitre.org/data/definitions/209.html

合规: R02 学术诚信 / R03 禁止 fall-back / R05 Bug 必修。
"""

from __future__ import annotations

import logging
import sys
import threading
import traceback
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from polaris_flow.scheduler import JobScheduler
    from polaris_flow.tracker import JobTracker

logger = logging.getLogger(__name__)

_STATIC_DIR = Path(__file__).parent / "static"

# Showcase 运行状态字典: {run_id: {"status": str, "output_dir": str, "error": str|None}}
# R05 Bug 修复 v4.0-WEB-LOCK（第1轮迭代发现）:
# 原 _showcase_runs 全局字典无锁，后台线程写 + HTTP 线程读存在竞态。
# 改为 threading.Lock 保护所有读写操作。
_showcase_runs: dict[str, dict] = {}
_showcase_lock = threading.Lock()

# 全局作业调度器与追踪器（对齐 Cadence ADE-XL 作业队列模型）
# R05 Bug 修复 v4.0-WEB-LOCK: 懒初始化加锁，防止 ThreadingHTTPServer 下创建多实例
_global_scheduler: JobScheduler | None = None
_global_tracker: JobTracker | None = None
_global_lock = threading.Lock()

# Showcase 输出子目录列表
_SHOWCASE_SUBDIRS = ["logs", "gds", "verilog_a", "spice", "reports"]


def _get_scheduler() -> JobScheduler:
    """获取全局作业调度器（懒初始化，线程安全）。

    首次调用时创建 JobScheduler 实例，注入标准 10 阶段执行函数，
    后续调用复用同一实例。对齐 Cadence ADE-XL 的全局作业队列模型。

    R05 Bug 修复 v4.0-WEB-LOCK: 加 _global_lock 双重检查锁定，
    防止 ThreadingHTTPServer 下多线程并发创建多个 scheduler 实例。
    文献: Python threading.Lock https://docs.python.org/3/library/threading.html#lock-objects
    文献: Double-checked locking https://en.wikipedia.org/wiki/Double-checked_locking
    """
    global _global_scheduler
    if _global_scheduler is None:
        with _global_lock:
            # 双重检查锁定：进入锁后再检查一次，防止多线程同时通过第一次检查
            if _global_scheduler is None:
                from polaris_flow.executors import STAGE_EXECUTORS
                from polaris_flow.scheduler import JobScheduler

                _global_scheduler = JobScheduler(
                    max_workers=4, stage_executors=STAGE_EXECUTORS
                )
    return _global_scheduler


def _get_tracker() -> JobTracker:
    """获取全局作业追踪器（懒初始化，线程安全）。

    首次调用时创建 JobTracker 实例，扫描 out/jobs 目录，
    后续调用复用同一实例。

    R05 Bug 修复 v4.0-WEB-LOCK: 加 _global_lock 双重检查锁定。
    """
    global _global_tracker
    if _global_tracker is None:
        with _global_lock:
            if _global_tracker is None:
                from polaris_flow.tracker import JobTracker

                _global_tracker = JobTracker(base_output_dir="out/jobs")
    return _global_tracker


def _get_presets() -> list[dict]:
    """获取预设电路列表。"""
    return [
        {
            "id": "mzi",
            "name": "MZI 干涉仪",
            "description": "马赫-曾德尔干涉仪（2x2 MMI + 波导臂）",
            "devices": 5,
            "platform": "SOI",
        },
        {
            "id": "ring",
            "name": "微环谐振器",
            "description": "单微环 + 总线波导",
            "devices": 4,
            "platform": "SOI",
        },
        {
            "id": "clements_4x4",
            "name": "Clements 4x4 光矩阵",
            "description": "可编程光子线性计算单元（4x4）",
            "devices": 28,
            "platform": "SOI",
        },
    ]


def _mzi_circuit():
    """构建 MZI 干涉仪电路。

    端口名对齐 PDK 定义：
    - mmi_1x2: in, out1, out2（来源: polaris.pdk.soi.couplers._make_mmi_1x2_ports）
    - mmi_2x2: in1, in2, out1, out2（来源: polaris.pdk.soi.couplers._make_mmi_2x2_ports）
    """
    from polaris_core.specs import CircuitSpec, DeviceSpec

    return CircuitSpec(
        name="MZI",
        canvas_w=1000,
        canvas_h=600,
        devices=[
            DeviceSpec("gc1", "grating_coupler", 10, 10),
            DeviceSpec("mmi1", "mmi_1x2", 20, 10),
            # 波导 length 参数 = width_um（光传播方向为较长维度）
            # 来源: SiEPIC EBeam PDK strip waveguide 几何约定
            DeviceSpec("wg1", "strip_waveguide", 100, 0.5, params={"length": 100.0, "length_um": 100.0}),
            DeviceSpec("wg2", "strip_waveguide", 120, 0.5, params={"length": 120.0, "length_um": 120.0}),
            DeviceSpec("mmi2", "mmi_2x2", 20, 10),
        ],
        connections=[
            ("gc1", "out", "mmi1", "in"),
            ("mmi1", "out1", "wg1", "in"),
            ("mmi1", "out2", "wg2", "in"),
            ("wg1", "out", "mmi2", "in1"),
            ("wg2", "out", "mmi2", "in2"),
        ],
    )


def _ring_circuit():
    """构建微环谐振器电路。"""
    from polaris_core.specs import CircuitSpec, DeviceSpec

    return CircuitSpec(
        name="Ring",
        canvas_w=800,
        canvas_h=600,
        devices=[
            DeviceSpec("gc1", "grating_coupler", 10, 10),
            # 波导 length 参数 = width_um（光传播方向为较长维度）
            # 来源: SiEPIC EBeam PDK strip waveguide 几何约定
            DeviceSpec("wg1", "strip_waveguide", 200, 0.5, params={"length": 200.0, "length_um": 200.0}),
            DeviceSpec("ring1", "ring_resonator", 30, 30),
            DeviceSpec("gc2", "grating_coupler", 10, 10),
        ],
        connections=[
            ("gc1", "out", "wg1", "in"),
            ("wg1", "out", "ring1", "bus_in"),
            ("ring1", "bus_out", "gc2", "in"),
        ],
    )


_PRESET_BUILDERS = {
    "mzi": _mzi_circuit,
    "ring": _ring_circuit,
}


def _build_circuit(preset_id: str):
    """根据预设 ID 构建电路规格。"""
    if preset_id in _PRESET_BUILDERS:
        return _PRESET_BUILDERS[preset_id]()
    if preset_id == "clements_4x4":
        raise ImportError(
            "_build_circuit('clements_4x4') 需要 polaris_orchestrator 子模块提供 "
            "_default_demo_circuit（v5.0 polaris_orchestrator 未迁移该函数，"
            "R03 禁止 fall-back）。请在 polaris_gui 内联构建 Clements 电路。"
        )
    raise ValueError(f"未知预设: {preset_id}")


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

    默认使用 curvy router（euler 弯曲布线），自动满足弯曲半径约束。
    "default" 映射到 "curvy"，因为 A* 网格布线的直角弯半径 < min_bend_radius，
    会产生 DRC 违规。curvy router 用 euler 曲线替换直角弯，损耗更低。

    来源: LiDAR ISPD'25 curvy-aware routing
      https://dl.acm.org/doi/10.1145/3698364.3705355

    Raises:
        ImportError: polaris_orchestrator 未迁移 IntegratedPipeline（R03 禁止 fall-back）。
    """
    raise ImportError(
        "_run_pipeline 需要 polaris_orchestrator 子模块提供 "
        "IntegratedPipeline/PipelineConfig（v5.0 polaris_orchestrator 未迁移"
        "一体化流水线类，R03 禁止 fall-back）。"
        "请改用 polaris_flow 调度器执行布局布线流水线。"
    )


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


__all__ = [
    # 全局状态
    "_STATIC_DIR",
    "_showcase_runs",
    "_showcase_lock",
    "_global_scheduler",
    "_global_tracker",
    "_global_lock",
    "_SHOWCASE_SUBDIRS",
    "_PRESET_BUILDERS",
    # 业务函数
    "_get_scheduler",
    "_get_tracker",
    "_get_presets",
    "_mzi_circuit",
    "_ring_circuit",
    "_build_circuit",
    "_extract_placements",
    "_extract_paths",
    "_run_pipeline",
    "_run_showcase_background",
]
