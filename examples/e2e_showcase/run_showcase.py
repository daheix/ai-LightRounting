"""PoLaRIS 端到端 Demo Showcase 主入口。

按 9 个阶段顺序执行全流程，每阶段输出结构化日志（控制台彩色 + JSONL 文件），
全流程结束后生成 Markdown 汇总报告。

9 阶段流程:
    1. PDK 器件目录展示
    2. 电路规格定义
    3. AI 布局
    4. 智能布线
    5. 仿真验证
    6. DRC/LVS 验证
    7. GDS 导出
    8. 光电协同
    9. 量子光子验证

运行方式:
    # 全流程运行
    python examples/e2e_showcase/run_showcase.py

    # 单阶段运行
    python examples/e2e_showcase/run_showcase.py --stage 5

    # 跳过报告生成
    python examples/e2e_showcase/run_showcase.py --no-report

    # 指定输出目录
    python examples/e2e_showcase/run_showcase.py --output-dir out/my_showcase

来源:
- PoLaRIS 项目: https://github.com/daheix/ai-LightRounting
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Any

# 确保脚本所在目录在 sys.path 中，使 stages/ 和同级模块可被导入
_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from logging_config import StageLogger, setup_logging  # noqa: E402
from report_generator import generate_report  # noqa: E402
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
    stage10_adjoint_inverse_design,
)

# 输出子目录列表
_OUTPUT_SUBDIRS = ["logs", "gds", "verilog_a", "spice", "reports"]

# 10 阶段定义: (阶段 ID, 阶段名称, 阶段模块)
STAGES: list[tuple[int, str, Any]] = [
    (1, "PDK 器件目录展示", stage1_pdk_catalog),
    (2, "电路规格定义", stage2_circuit_spec),
    (3, "AI 布局", stage3_ai_placement),
    (4, "智能布线", stage4_routing),
    (5, "仿真验证", stage5_simulation),
    (6, "DRC/LVS 验证", stage6_drc_lvs),
    (7, "GDS 导出", stage7_gds_export),
    (8, "光电协同", stage8_opto_electrical),
    (9, "量子光子验证", stage9_quantum_photonics),
    (10, "Adjoint 逆向设计", stage10_adjoint_inverse_design),
]


def create_output_dirs(output_dir: Path) -> None:
    """创建输出目录结构。

    创建 logs/、gds/、verilog_a/、spice/、reports/ 子目录。

    Args:
        output_dir: 输出根目录。
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    for subdir in _OUTPUT_SUBDIRS:
        (output_dir / subdir).mkdir(parents=True, exist_ok=True)


def run_single_stage(stage_id: int, stage_name: str, stage_module: Any, output_dir: Path) -> dict:
    """运行单个阶段，用 StageLogger 包裹。

    Args:
        stage_id: 阶段编号。
        stage_name: 阶段名称。
        stage_module: 阶段模块（需有 run 函数）。
        output_dir: 输出目录。

    Returns:
        阶段结果摘要 dict，含 stage_id/name/status/duration/result/error 字段。
    """
    summary: dict[str, Any] = {
        "stage_id": stage_id,
        "name": stage_name,
        "status": "done",
        "duration": 0.0,
        "result": {},
        "error": None,
    }
    start = time.time()
    try:
        with StageLogger(stage_id, stage_name, output_dir) as sl:
            # 记录输入参数（修复 P0: inputs 字段始终为空）
            sl.log_input("output_dir", str(output_dir))
            sl.log_input("stage_module", stage_module.__name__)
            result = stage_module.run(output_dir)
            if result:
                for key, value in result.items():
                    sl.log_output(key, value)
            summary["result"] = result
    except Exception as e:
        summary["status"] = "failed"
        summary["error"] = f"{type(e).__name__}: {e}"
    summary["duration"] = time.time() - start
    return summary


def run_all_stages(output_dir: Path, stage_filter: int | None = None) -> list[dict]:
    """运行全部（或指定）阶段。

    Args:
        output_dir: 输出目录。
        stage_filter: 若指定，仅运行该阶段编号（1-9）。

    Returns:
        各阶段结果摘要列表。
    """
    results: list[dict] = []
    for stage_id, stage_name, stage_module in STAGES:
        if stage_filter is not None and stage_id != stage_filter:
            continue
        summary = run_single_stage(stage_id, stage_name, stage_module, output_dir)
        results.append(summary)
    return results


def print_summary(results: list[dict]) -> None:
    """打印全流程汇总表。

    Args:
        results: 各阶段结果摘要列表。
    """
    bar = "=" * 60
    print(f"\n{bar}")
    print("PoLaRIS 端到端 Demo Showcase 汇总")
    print(bar)
    for r in results:
        status = r["status"]
        duration = r["duration"]
        marker = "[OK]" if status == "done" else "[FAIL]"
        print(f"  阶段 {r['stage_id']}: {r['name']:<20s} {marker} {status:<6s} ({duration:.2f}s)")
        if r["error"]:
            print(f"         错误: {r['error']}")
    print(bar)
    n_done = sum(1 for r in results if r["status"] == "done")
    n_failed = sum(1 for r in results if r["status"] == "failed")
    print(f"  总计: {n_done} 成功, {n_failed} 失败")
    print(bar)


def parse_args() -> argparse.Namespace:
    """解析命令行参数。

    Returns:
        解析后的参数命名空间。
    """
    parser = argparse.ArgumentParser(
        description="PoLaRIS 端到端 Demo Showcase — 9 阶段全流程演示",
    )
    parser.add_argument(
        "--stage",
        type=int,
        choices=range(1, 11),
        default=None,
        help="仅运行指定阶段（1-10），不指定则运行全部 10 阶段",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="out/e2e_showcase",
        help="输出目录（默认: out/e2e_showcase）",
    )
    parser.add_argument(
        "--no-report",
        action="store_true",
        help="跳过汇总报告生成",
    )
    return parser.parse_args()


def main() -> None:
    """主入口：解析参数、创建目录、运行阶段、生成报告。"""
    args = parse_args()
    output_dir = Path(args.output_dir)

    create_output_dirs(output_dir)
    setup_logging(output_dir)

    results = run_all_stages(output_dir, stage_filter=args.stage)
    print_summary(results)

    if not args.no_report:
        report_path = generate_report(output_dir)
        print(f"\n汇总报告已生成: {report_path}")


if __name__ == "__main__":
    main()
