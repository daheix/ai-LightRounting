"""PoLaRIS 端到端 Demo Showcase 主入口。

按 13 个阶段顺序执行全流程（12 阶段工业光电子设计流程 + 1 阶段 GUI 交互
演示），每阶段输出结构化日志（控制台彩色 + JSONL 文件），全流程结束后
生成 Markdown 汇总报告。

13 阶段流程（对齐 Luceda/Synopsys 商业工具链，先仿真后版图、良率签核后 GDS）:
    1. PDK 器件目录展示
    2. 电路规格定义
    3. 仿真验证（原理图级，版图前）
    4. Adjoint 逆向设计（器件优化，版图前）
    5. AI 布局
    6. 智能布线
    7. 版图后仿真（含布线寄生）
    8. DRC/LVS 验证
    9. 良率分析（蒙特卡洛，流片前签核）
    10. 光电协同
    11. 量子光子验证
    12. GDS 导出（流片交付最后一步）
    13. 交互式版图编辑（GUI 增强演示，非工业流程环节）

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
- Luceda IPKISS 设计流程: https://docs.lucedaphotonics.com/
- Synopsys OptoCompiler: https://www.synopsys.com/photonic-solutions.html
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

# PoLaRIS v5.0: 注入 18 个子模块源码路径（modules/<name>/src）
# 旧 v4 单包 src/polaris/ 已拆分为 18 个独立子模块，每个子模块位于
# modules/<name>/src/polaris_<name>/ 下，需将其父目录 src 加入 sys.path。
_PROJECT_ROOT = _SCRIPT_DIR.parent.parent  # /workspace
_SUBMODULES_V5 = [
    "core", "sparam", "place", "route", "pdk", "drc", "lvs", "gdsio", "fdtd",
    "inverse", "boson", "klm", "pam4", "fde", "eme", "bpm", "fdfd", "orchestrator",
    "flow", "yield",
]
for _sub in _SUBMODULES_V5:
    _src_dir = _PROJECT_ROOT / "modules" / _sub / "src"
    if _src_dir.is_dir() and str(_src_dir) not in sys.path:
        sys.path.insert(0, str(_src_dir))

from logging_config import StageLogger, setup_logging  # noqa: E402
from report_generator import generate_report  # noqa: E402
from stages import (  # noqa: E402
    stage1_pdk_catalog,
    stage2_circuit_spec,
    stage3_simulation,
    stage4_inverse_design,
    stage5_ai_placement,
    stage6_routing,
    stage7_postlayout_sim,
    stage8_drc_lvs,
    stage9_yield_analysis,
    stage10_opto_electrical,
    stage11_quantum_photonics,
    stage12_gds_export,
    stage13_interactive_layout_edit,
)

# 输出子目录列表
_OUTPUT_SUBDIRS = ["logs", "gds", "verilog_a", "spice", "reports"]

# 13 阶段定义: (阶段 ID, 阶段名称, 阶段模块)
# 工业流程对齐 Luceda/Synopsys：先仿真后版图、良率签核后 GDS 导出
STAGES: list[tuple[int, str, Any]] = [
    (1, "PDK 器件目录展示", stage1_pdk_catalog),
    (2, "电路规格定义", stage2_circuit_spec),
    (3, "仿真验证", stage3_simulation),
    (4, "Adjoint 逆向设计", stage4_inverse_design),
    (5, "AI 布局", stage5_ai_placement),
    (6, "智能布线", stage6_routing),
    (7, "版图后仿真", stage7_postlayout_sim),
    (8, "DRC/LVS 验证", stage8_drc_lvs),
    (9, "良率分析", stage9_yield_analysis),
    (10, "光电协同", stage10_opto_electrical),
    (11, "量子光子验证", stage11_quantum_photonics),
    (12, "GDS 导出", stage12_gds_export),
    (13, "交互式版图编辑", stage13_interactive_layout_edit),
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
        stage_filter: 若指定，仅运行该阶段编号（1-13）。

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
        description="PoLaRIS 端到端 Demo Showcase — 13 阶段全流程演示",
    )
    parser.add_argument(
        "--stage",
        type=int,
        choices=range(1, 14),
        default=None,
        help="仅运行指定阶段（1-13），不指定则运行全部 13 阶段",
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
    parser.add_argument(
        "--real-case",
        action="store_true",
        help="运行真实 PIC 设计 Case（100Gbps MZI + Clements 4x4，对标 Intel CWDM4），"
        "复用 12 阶段工业流程 stage 代码，生成真实完整结果展示报告",
    )
    return parser.parse_args()


def main() -> None:
    """主入口：解析参数、创建目录、运行阶段、生成报告。"""
    args = parse_args()
    output_dir = Path(args.output_dir)

    create_output_dirs(output_dir)
    setup_logging(output_dir)

    if args.real_case:
        # 真实 PIC 设计 Case 模式：复用 10 阶段 stage 代码，生成真实结果分析报告
        from real_case.run_real_case import run as run_real_case
        from real_case.analyze_results import get_analysis, get_statistics

        real_output_dir = output_dir.parent / "real_case"
        result = run_real_case(real_output_dir)

        # 真实性分析
        stage_results = [
            {"stage_id": s["stage_id"], "name": s["name"],
             "status": s["status"], "key_outputs": s["result"]}
            for s in result["stages"]
        ]
        analysis = get_analysis(stage_results)
        stats = get_statistics(analysis)

        print("\n" + "=" * 60)
        print("PoLaRIS 真实 PIC 设计 Case 端到端结果")
        print("=" * 60)
        print(f"  案例: {result['case_name']}")
        print(f"  对标: {result['benchmark']}")
        for s in result["stages"]:
            marker = "[OK]" if s["status"] == "OK" else "[FAIL]"
            print(f"  阶段 {s['stage_id']}: {s['name']:<20s} {marker} ({s['duration']:.2f}s)")
        print(f"  总计: {result['summary']['n_success']} 成功, "
              f"{result['summary']['n_failed']} 失败, "
              f"耗时 {result['summary']['total_duration']:.2f}s")
        print("=" * 60)
        print(f"  真实性统计: REAL_USABLE={stats['real_usable']}, "
              f"LIMITED_BY_COMPUTE={stats['limited_by_compute']}, "
              f"LIMITED_BY_DATA={stats['limited_by_data']}")
        print("=" * 60)
        print(f"\n真实完整结果展示报告: {real_output_dir / 'REAL_CASE_REPORT.md'}")
        return

    results = run_all_stages(output_dir, stage_filter=args.stage)
    print_summary(results)

    if not args.no_report:
        report_path = generate_report(output_dir)
        print(f"\n汇总报告已生成: {report_path}")


if __name__ == "__main__":
    main()
