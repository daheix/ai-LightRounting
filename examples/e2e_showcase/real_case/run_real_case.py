"""真实 PIC 设计 Case 端到端运行脚本。

选取 100Gbps MZI 调制器（对标 Intel 100G CWDM4）+ Clements 4x4 光矩阵，
以 SiEPIC EBeam PDK 实测参数为输入，复用 12 阶段工业流程 stage 代码跑完整流程。

R03 合规：失败即 raise，禁止任何 fall-back。

复用的 stage 模块（不重新实现 stage 逻辑，仅编排调用）:
- stage1_pdk_catalog: PDK 器件目录展示（SOI/SiN/InP/LNOI 四平台）
- stage2_circuit_spec: 电路规格定义（MZI / Clements 4x4 / 玻色采样）
- stage3_simulation: 仿真验证（S 参数 / 酉矩阵 / PAM4 / FDTD，原理图级）
- stage4_inverse_design: Adjoint 逆向设计（器件优化，版图前）
- stage5_ai_placement: AI 布局
- stage6_routing: 智能布线
- stage7_postlayout_sim: 版图后仿真（含布线寄生）
- stage8_drc_lvs: DRC/LVS 验证
- stage9_yield_analysis: 良率分析（蒙特卡洛，流片前签核）
- stage10_opto_electrical: 光电协同（Verilog-A / SPICE / PAM4 眼图）
- stage11_quantum_photonics: 量子光子验证
- stage12_gds_export: GDS 导出

来源:
- SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- Intel 100G CWDM4 QSFP28 Optical Module datasheet
  https://www.intel.com/content/www/us/en/products/network-io/ethernet/100-gbe/100g-cwdm4-qsfp28-optical-module.html
- IEEE 802.3bs 100GBASE-LR4: https://standards.ieee.org/ieee/802.3bs/10869/
- Clements et al., Optica 2016: https://doi.org/10.1364/OPTICA.3.001460
- Luceda IPKISS 设计流程: https://docs.lucedaphotonics.com/
- Synopsys OptoCompiler: https://www.synopsys.com/photonic-solutions.html
"""

from __future__ import annotations

import logging
import sys
import time
from pathlib import Path

# 确保 e2e_showcase 目录在 sys.path 中，使 stages/ 与 real_case 可被导入
# （与 run_showcase.py 同样的 sys.path 处理方式）
_SCRIPT_DIR = Path(__file__).resolve().parent  # real_case/
_SHOWCASE_DIR = _SCRIPT_DIR.parent  # e2e_showcase/
if str(_SHOWCASE_DIR) not in sys.path:
    sys.path.insert(0, str(_SHOWCASE_DIR))

# R390 修复：注入 18 个子模块源码路径（与 run_showcase.py 一致）
# 缺失此注入会导致 `ModuleNotFoundError: No module named 'polaris_inverse'`
# 等子模块无法导入（stage4_inverse_design 依赖 polaris_inverse，
# stage7/9 依赖 polaris_flow/polaris_yield）
_PROJECT_ROOT = _SCRIPT_DIR.parent.parent.parent  # /workspace
_SUBMODULES_V5 = [
    "core", "sparam", "place", "route", "pdk", "drc", "lvs", "gdsio", "fdtd",
    "inverse", "boson", "klm", "pam4", "fde", "eme", "bpm", "fdfd", "orchestrator",
    "flow", "yield",
]
for _sub in _SUBMODULES_V5:
    _src_dir = _PROJECT_ROOT / "modules" / _sub / "src"
    if _src_dir.is_dir() and str(_src_dir) not in sys.path:
        sys.path.insert(0, str(_src_dir))

# 复用现有 stage 代码（sys.path 已含 e2e_showcase 目录）
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
)
from real_case.real_inputs import get_all_params, validate_no_mock  # noqa: E402

_logger = logging.getLogger("e2e_showcase")


# =============================================================================
# 12 阶段编排表（stage_id, 中文名, stage 模块）
# 工业流程对齐 Luceda/Synopsys：先仿真后版图、良率签核后 GDS 导出
# =============================================================================
STAGES = [
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
]


def run(output_dir: Path) -> dict:
    """运行真实 case 端到端 12 阶段。

    以 100Gbps MZI 调制器（对标 Intel 100G CWDM4）+ Clements 4x4 光矩阵
    为演示电路，以 SiEPIC EBeam PDK 实测参数为输入，复用 12 阶段工业流程
    stage 代码跑完整流程，收集每阶段结果与耗时。

    Args:
        output_dir: 输出目录（各 stage 子产物保存至 logs/gds/verilog_a/
            spice/reports 子目录）。

    Returns:
        dict 含:
        - case_name: 真实 case 名称
        - benchmark: 商业对标产品
        - real_inputs: 真实输入参数注册表（6 分组）
        - stages: 12 阶段结果列表，每项含
          {stage_id, name, status, duration, result, error}
        - summary: {n_success, n_failed, total_duration}

    Raises:
        RuntimeError: 任何阶段失败（R03 无 fall-back，失败即 raise，
            禁止跳过失败阶段继续执行）。
    """
    # 1. 验证真实输入参数无 mock（R03 合规门禁）
    validate_no_mock()
    real_inputs = get_all_params()
    _logger.info("真实 case 输入参数验证通过（R03: 无 mock）")
    _logger.info(
        "真实 case: %s — 对标 %s",
        "100Gbps MZI 调制器 + Clements 4x4 光矩阵",
        "Intel 100G CWDM4 QSFP28 Optical Module",
    )

    # 2. 创建输出目录及子目录（与 stage 代码期望的子目录结构一致）
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    for subdir in ["logs", "gds", "verilog_a", "spice", "reports"]:
        (output_dir / subdir).mkdir(exist_ok=True)

    # 3. 顺序跑 12 阶段（R03: 任何阶段失败即 raise，禁止跳过）
    stage_results: list[dict] = []
    n_success = 0
    n_failed = 0
    total_start = time.time()

    for stage_id, stage_name, stage_module in STAGES:
        _logger.info("=" * 60)
        _logger.info("真实 case 阶段 %d: %s — 开始", stage_id, stage_name)
        stage_start = time.time()
        try:
            result = stage_module.run(output_dir)
            duration = time.time() - stage_start
            stage_results.append({
                "stage_id": stage_id,
                "name": stage_name,
                "status": "OK",
                "duration": duration,
                "result": result,
                "error": None,
            })
            n_success += 1
            _logger.info(
                "真实 case 阶段 %d: %s — 完成 (%.2fs)",
                stage_id, stage_name, duration,
            )
        except Exception as e:
            duration = time.time() - stage_start
            stage_results.append({
                "stage_id": stage_id,
                "name": stage_name,
                "status": "FAIL",
                "duration": duration,
                "result": None,
                "error": str(e),
            })
            n_failed += 1
            _logger.error(
                "真实 case 阶段 %d: %s — 失败: %s",
                stage_id, stage_name, e,
            )
            # R03: 失败即 raise，禁止 fall-back（不跳过失败阶段继续执行）
            raise RuntimeError(
                f"真实 case 阶段 {stage_id} ({stage_name}) 失败: {e}"
            ) from e

    total_duration = time.time() - total_start
    _logger.info("=" * 60)
    _logger.info(
        "真实 case 全流程完成: %d 成功 / %d 失败, 总耗时 %.2fs",
        n_success, n_failed, total_duration,
    )

    return {
        "case_name": "100Gbps MZI 调制器 + Clements 4x4 光矩阵",
        "benchmark": "Intel 100G CWDM4 QSFP28 Optical Module",
        "real_inputs": real_inputs,
        "stages": stage_results,
        "summary": {
            "n_success": n_success,
            "n_failed": n_failed,
            "total_duration": total_duration,
        },
    }


# =============================================================================
# 主入口（R390 修复：原脚本缺失 __main__ 块，直接运行无输出）
# =============================================================================
if __name__ == "__main__":
    import json

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    # 默认输出目录: out/real_case（与 analyze_results.py 期望路径一致）
    _DEFAULT_OUTPUT = (
        Path(__file__).resolve().parent.parent.parent.parent / "out" / "real_case"
    )
    _result = run(_DEFAULT_OUTPUT)

    # 保存汇总结果到 stage_results_summary.json（analyze_results.py 数据源）
    _summary_path = _DEFAULT_OUTPUT / "stage_results_summary.json"
    _DEFAULT_OUTPUT.mkdir(parents=True, exist_ok=True)
    with _summary_path.open("w", encoding="utf-8") as _f:
        # 将 stage 结果转为 analyze_results.py 期望的 stage_summaries 格式
        _stage_summaries = []
        for _s in _result["stages"]:
            _stage_summaries.append({
                "stage_id": _s["stage_id"],
                "name": _s["name"],
                "status": _s["status"],
                "duration": _s["duration"],
                "result": _s["result"],
                "error": _s["error"],
            })
        json.dump(
            {
                "case_name": _result["case_name"],
                "benchmark": _result["benchmark"],
                "stage_summaries": _stage_summaries,
                "summary": _result["summary"],
            },
            _f,
            ensure_ascii=False,
            indent=2,
            default=str,
        )

    print("=" * 60)
    print(f"真实 case 完成: {_result['summary']['n_success']} 成功 / "
          f"{_result['summary']['n_failed']} 失败, "
          f"总耗时 {_result['summary']['total_duration']:.2f}s")
    print(f"汇总结果: {_summary_path}")
    print("=" * 60)
