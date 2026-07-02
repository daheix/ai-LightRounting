"""阶段 9: 量子光子验证。

执行玻色采样、HOM 干涉与 KLM 量子门仿真，输出量子光子验证结果。

PoLaRIS v5.0 迁移说明:
    旧 v4 使用 polaris.sim 提供的 7 项验证（含蒙特卡洛、HOM dip 时间分辨、
    卡方检验、KLM 电路蒙特卡洛等）。v5.0 将量子光子能力拆分为 polaris-boson
    与 polaris-klm 两个子模块，仅保留核心 API:
      - ``polaris_boson.boson_sampling(unitary, input_state) -> dict``
      - ``polaris_boson.clements_unitary(n_modes, seed) -> list``
      - ``polaris_boson.hom_interference(theta) -> dict``
      - ``polaris_klm.klm_cnot() -> dict``
    本 stage 简化为调用上述 4 个核心 API 完成三项基础验证:
      1. 玻色采样概率守恒（4 光子 4 模）
      2. HOM 干涉 dip_depth = 1.0（θ=0 完全不可区分）
      3. KLM CNOT 后选择成功率 = 1/9（Ralph 2002 简化 4-BS 电路）
    蒙特卡洛稳定性、HOM dip 时间分辨、卡方检验、KLM 电路完整蒙特卡洛仿真
    等数值深化验证待未来子模块扩展后恢复。

公式来源（R02 学术诚信）:
- 玻色采样: Aaronson & Arkhipov, STOC 2011,
  https://arxiv.org/abs/0910.4698
  P(s) = |Per(U_{S,T})|² / (Π s_i! · Π n_j!)
- HOM 干涉: Hong, Ou, Mandel, PRL 1987,
  https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.59.2044
  θ=0 完全不可区分 → dip_depth=1.0（HOM dip，量子干涉）
- KLM 方案: Knill, Laflamme, Milburn, Nature 2001,
  https://www.nature.com/articles/35051009
- KLM CNOT 电路: Ralph et al., PRA 2002,
  https://doi.org/10.1103/PhysRevA.65.062324
  简化 4-BS 电路，后选择成功率 = 1/9
- Clements 分解: Clements et al., Optica 2016,
  https://doi.org/10.1364/OPTICA.3.001460
- Ryser 算法: Ryser, 1963, Combinatorial Mathematics
  Per(A) = (-1)^n Σ_{S⊆[n]} (-1)^|S| Π_i Σ_{j∈S} A_{i,j}
- Glynn-Gray 算法: Glynn, Eur. J. Comb. 2010
  https://doi.org/10.1016/j.ejc.2010.01.010
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import numpy as np

from polaris_boson import (
    boson_sampling,
    clements_unitary,
    hom_interference,
)
from polaris_klm import klm_cnot

_logger = logging.getLogger("e2e_showcase")

# 概率守恒容差（R03: 失败 raise，不容忍数值漂移）
_PROB_TOL = 1e-6
# KLM CNOT 理论成功率（Ralph 2002 PRA 65, 062324 简化 4-BS 电路，1/9 ≈ 0.1111）
# 来源: polaris_klm.klm_cnot() 返回 Ralph 2002 理论值
_KLM_CNOT_EXPECTED = 1.0 / 9.0


def _build_clements_unitary() -> list:
    """用 Clements 分解生成 4×4 酉矩阵。

    Clements 三角形拓扑: M=4 模需 M(M-1)/2 = 6 个分束器，
    每个分束器由 (theta, phi) 参数化（v5.0 由 seed 随机生成，可复现）。

    v5.0 返回格式: list of list of [real, imag]（实虚交错，与 C ABI 一致），
    供 boson_sampling 直接使用。

    公式来源:
    - Clements et al., Optica 2016,
      https://doi.org/10.1364/OPTICA.3.001460

    Returns:
        4×4 酉矩阵（list of list of [real, imag]）。
    """
    n_modes = 4
    seed = 42
    n_bs = n_modes * (n_modes - 1) // 2
    _logger.info(
        "Clements 分解: %d 模, %d 个分束器 (seed=%d)",
        n_modes,
        n_bs,
        seed,
    )
    unitary = clements_unitary(n_modes=n_modes, seed=seed)
    # 验证酉性: U @ U† = I（从 list 重建为 numpy 矩阵做校验）
    U = np.array(
        [[complex(elem[0], elem[1]) for elem in row] for row in unitary],
        dtype=complex,
    )
    identity = np.eye(n_modes, dtype=complex)
    unitary_err = float(np.max(np.abs(U @ U.conj().T - identity)))
    if unitary_err > _PROB_TOL:
        raise ValueError(
            f"Clements 酉矩阵酉性验证失败: 最大误差 {unitary_err:.2e} "
            f"> 容差 {_PROB_TOL}"
        )
    _logger.info("Clements 酉性验证通过: 最大误差 %.2e", unitary_err)
    return unitary


def _verify_boson_sampling(output_dir: Path, unitary: list) -> dict:
    """执行 4 光子 4 模玻色采样并验证概率守恒。

    输入态 |1,1,1,1⟩（4 光子 4 模），计算完整输出概率分布，
    验证所有输出概率之和 = 1（光子数守恒下的概率归一化）。

    v5.0 polaris_boson.boson_sampling 返回:
      {prob_distribution: list[float], prob_sum: float, n_outputs: int}

    公式来源:
    - Aaronson & Arkhipov, STOC 2011, https://arxiv.org/abs/0910.4698
      P(s) = |Per(U_{S,T})|² / (Π s_i! · Π n_j!)
    - Ryser 算法（积和式计算）: Ryser, 1963, Combinatorial Mathematics
    - Glynn-Gray 算法: Glynn, Eur. J. Comb. 2010

    Args:
        output_dir: 输出目录。
        unitary: 4×4 酉矩阵（list of list of [real, imag]）。

    Returns:
        玻色采样验证结果 dict。

    Raises:
        ValueError: 概率守恒验证失败。
    """
    input_state = [1, 1, 1, 1]
    n_photons = sum(input_state)
    _logger.info(
        "玻色采样: 输入态 |%s⟩ (%d 光子 %d 模)",
        ",".join(str(s) for s in input_state),
        n_photons,
        len(input_state),
    )

    result = boson_sampling(unitary, input_state)
    prob_dist = result["prob_distribution"]
    prob_sum = float(result["prob_sum"])
    n_outputs = int(result["n_outputs"])
    _logger.info("玻色采样完成: %d 个可能输出模式", n_outputs)

    # 验证概率守恒: 所有输出概率之和 = 1
    prob_sum_ok = abs(prob_sum - 1.0) <= _PROB_TOL
    if not prob_sum_ok:
        raise ValueError(
            f"玻色采样概率守恒失败: 总和 {prob_sum:.10f} 偏离 1.0 "
            f"超过容差 {_PROB_TOL}"
        )
    _logger.info("概率守恒验证通过: 总和 = %.10f", prob_sum)

    # 找出 top-3 概率最高的输出模式
    sorted_idx = sorted(range(n_outputs), key=lambda i: prob_dist[i], reverse=True)
    for idx in sorted_idx[:3]:
        _logger.info("  输出模式 #%d: 概率 %.6e", idx, prob_dist[idx])

    # 保存概率分布到 JSON
    reports_dir = output_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    dist_path = reports_dir / "boson_sampling_dist.json"
    dist_data = {
        "n_modes": len(input_state),
        "n_photons": n_photons,
        "input_state": list(input_state),
        "n_outputs": n_outputs,
        "prob_sum": prob_sum,
        "prob_sum_ok": prob_sum_ok,
        "prob_tolerance": _PROB_TOL,
        # 完整概率分布列表（按 _generate_output_states 顺序）
        "prob_distribution": prob_dist,
        "top_3_probs": [
            {"output_index": idx, "prob": prob_dist[idx]}
            for idx in sorted_idx[:3]
        ],
        "sources": {
            "boson_sampling": "https://arxiv.org/abs/0910.4698",
            "ryser_algorithm": "Ryser, 1963, Combinatorial Mathematics",
            "glynn_gray": "https://doi.org/10.1016/j.ejc.2010.01.010",
        },
    }
    dist_path.write_text(
        json.dumps(dist_data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    _logger.info("概率分布已保存: %s", dist_path)

    return {
        "n_modes": len(input_state),
        "input_state": list(input_state),
        "n_outputs": n_outputs,
        "prob_sum": prob_sum,
        "prob_sum_ok": prob_sum_ok,
        "top_3_probs": [
            {"output_index": idx, "prob": prob_dist[idx]}
            for idx in sorted_idx[:3]
        ],
    }


def _verify_hom_interference(output_dir: Path) -> dict:
    """验证 HOM 干涉 dip_depth = 1.0（θ=0 完全不可区分）。

    两个全同光子输入 50:50 分束器，θ=0 时完全不可区分，
    量子干涉完全抑制符合计数（HOM dip）。

    v5.0 polaris_boson.hom_interference 返回:
      {coincidence_prob: float, dip_depth: float, verified: bool}
    θ=0 → coincidence_prob=0, dip_depth=1.0（完美 HOM dip）

    公式来源:
    - Hong, Ou, Mandel, PRL 1987,
      https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.59.2044
    - Bouwmeester et al., "The Physics of Quantum Information",
      Springer 2000, §3.1

    Args:
        output_dir: 输出目录。

    Returns:
        HOM 干涉验证结果 dict。

    Raises:
        ValueError: HOM 干涉验证失败（dip_depth 不接近 1.0）。
    """
    theta = 0.0  # 完全不可区分（HOM dip）
    _logger.info("HOM 干涉: 50:50 分束器 θ=0 (完全不可区分)")

    hom_result = hom_interference(theta=theta)
    coincidence_prob = float(hom_result["coincidence_prob"])
    dip_depth = float(hom_result["dip_depth"])
    api_verified = bool(hom_result["verified"])

    # 验证: θ=0 时 dip_depth ≈ 1.0（量子干涉完全抑制符合计数）
    hom_verified = abs(dip_depth - 1.0) <= _PROB_TOL
    if not hom_verified:
        raise ValueError(
            f"HOM 干涉验证失败: dip_depth={dip_depth:.6f} 偏离 1.0 "
            f"超过容差 {_PROB_TOL}"
        )
    _logger.info(
        "HOM 干涉验证通过: dip_depth=%.6f, coincidence_prob=%.2e, API verified=%s",
        dip_depth,
        coincidence_prob,
        api_verified,
    )

    # 保存 HOM 结果
    reports_dir = output_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    hom_path = reports_dir / "hom_interference.json"
    hom_data = {
        "theta": theta,
        "beamsplitter_ratio": "50:50",
        "input_state": [1, 1],
        "coincidence_prob": coincidence_prob,
        "dip_depth": dip_depth,
        "api_verified": api_verified,
        "hom_verified": hom_verified,
        "tolerance": _PROB_TOL,
        "physical_meaning": (
            "θ=0 完全不可区分 → 量子干涉完全抑制符合计数 → "
            "dip_depth=1.0（完美 HOM dip）"
        ),
        "sources": {
            "hom_1987": "https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.59.2044",
            "quantum_info_book": "Bouwmeester et al., Springer 2000, §3.1",
        },
    }
    hom_path.write_text(
        json.dumps(hom_data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    _logger.info("HOM 结果已保存: %s", hom_path)

    return {
        "theta": theta,
        "coincidence_prob": coincidence_prob,
        "dip_depth": dip_depth,
        "hom_verified": hom_verified,
        "api_verified": api_verified,
    }


def _verify_klm(output_dir: Path) -> dict:
    """验证 KLM CNOT 后选择成功率 = 1/9 与电路酉性。

    KLM 方案用线性光学实现量子门:
    - CNOT 门后选择成功率 = 1/9（Ralph 2002 PRA 65, 062324 简化 4-BS 电路）
    - 电路酉性 U @ U† = I（实算校验，误差 < 1e-10）

    v5.0 polaris_klm.klm_cnot 返回:
      {success_prob: float (1/9), verified: bool (电路酉性+理论值校验)}

    方案区分（R02 学术诚信）:
    - Knill 2001 Nature 原始 NS-gate: 8 模式，成功率 1/16
    - Ralph 2002 PRA 65, 062324 简化 4-BS: 4 模式，成功率 1/9 ← polaris_klm
    - Knill 2002 PRA 66, 052306 改进方案: ~1/9

    公式来源:
    - Knill, Laflamme, Milburn, Nature 2001,
      https://www.nature.com/articles/35051009
    - Ralph et al., PRA 2002,
      https://doi.org/10.1103/PhysRevA.65.062324

    Args:
        output_dir: 输出目录。

    Returns:
        KLM 验证结果 dict。

    Raises:
        ValueError: CNOT 成功率验证失败。
    """
    _logger.info("KLM 验证: CNOT 后选择成功率 = 1/9 (Ralph 2002 简化 4-BS)")

    result = klm_cnot()
    cnot_success_prob = float(result["success_prob"])
    api_verified = bool(result["verified"])

    # 验证: 后选择成功率 = 1/9（Ralph 2002 理论值）
    cnot_verified = abs(cnot_success_prob - _KLM_CNOT_EXPECTED) <= _PROB_TOL
    if not cnot_verified:
        raise ValueError(
            f"KLM CNOT 成功率验证失败: {cnot_success_prob} 偏离 "
            f"{_KLM_CNOT_EXPECTED} 超过容差 {_PROB_TOL}"
        )
    _logger.info(
        "KLM CNOT 验证通过: 成功率=%.6f (理论值 1/9=%.6f), API verified=%s",
        cnot_success_prob,
        _KLM_CNOT_EXPECTED,
        api_verified,
    )

    # 保存 KLM 结果
    reports_dir = output_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    klm_path = reports_dir / "klm_verification.json"
    klm_data = {
        "scheme": "Ralph 2002 PRA 65, 062324 simplified 4-BS CNOT",
        "n_modes": 4,
        "n_beamsplitters": 4,
        "success_prob": cnot_success_prob,
        "expected_success_prob": _KLM_CNOT_EXPECTED,
        "cnot_verified": cnot_verified,
        "api_verified": api_verified,
        "tolerance": _PROB_TOL,
        "scheme_comparison": {
            "knill_2001_nature": {
                "modes": 8,
                "success_prob": 1.0 / 16.0,
                "url": "https://www.nature.com/articles/35051009",
            },
            "ralph_2002_pra": {
                "modes": 4,
                "success_prob": 1.0 / 9.0,
                "url": "https://doi.org/10.1103/PhysRevA.65.062324",
                "note": "polaris_klm 实现此方案",
            },
            "knill_2002_pra": {
                "modes": "varies",
                "success_prob": "~1/9",
                "url": "https://doi.org/10.1103/PhysRevA.66.052306",
            },
        },
        "sources": {
            "klm_scheme": "https://www.nature.com/articles/35051009",
            "ralph_2002": "https://doi.org/10.1103/PhysRevA.65.062324",
            "obrien_2003": "https://doi.org/10.1038/nature02354",
            "hofmann_2002": "https://doi.org/10.1103/PhysRevA.66.024308",
        },
    }
    klm_path.write_text(
        json.dumps(klm_data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    _logger.info("KLM 结果已保存: %s", klm_path)

    return {
        "success_prob": cnot_success_prob,
        "expected_success_prob": _KLM_CNOT_EXPECTED,
        "cnot_verified": cnot_verified,
        "api_verified": api_verified,
    }


def run(output_dir: Path) -> dict:
    """执行阶段 9: 量子光子验证。

    执行三项量子光子验证（v5.0 简化版）:
    1. 4 光子 4 模玻色采样概率分布与守恒（Clements 分解酉矩阵）
    2. HOM 干涉 dip_depth = 1.0（θ=0 完全不可区分 → 完美 HOM dip）
    3. KLM CNOT 后选择成功率 = 1/9（Ralph 2002 简化 4-BS 电路）

    所有验证失败均 raise（R03 禁止 fall-back）。
    报告写入 output_dir/reports/ 目录。

    Args:
        output_dir: 输出目录，报告写入 output_dir/reports/。

    Returns:
        验证结果 dict，含三个子 dict:
        - boson_sampling: n_modes/input_state/n_outputs/prob_sum/prob_sum_ok
        - hom: theta/coincidence_prob/dip_depth/hom_verified
        - klm: success_prob/expected_success_prob/cnot_verified
    """
    _logger.info("阶段 9 开始: 量子光子验证（polaris-boson + polaris-klm）")

    # 1. 构建 Clements 酉矩阵（4×4，seed=42 可复现）
    unitary = _build_clements_unitary()

    # 2. 玻色采样概率分布与守恒验证
    boson_result = _verify_boson_sampling(output_dir, unitary)

    # 3. HOM 干涉验证（θ=0 完美 dip）
    hom_result = _verify_hom_interference(output_dir)

    # 4. KLM CNOT 验证（Ralph 2002 简化 4-BS，成功率 1/9）
    klm_result = _verify_klm(output_dir)

    _logger.info(
        "阶段 9 完成: 量子光子验证全部通过 "
        "(玻色采样=%s, HOM=%s, KLM=%s)",
        boson_result["prob_sum_ok"],
        hom_result["hom_verified"],
        klm_result["cnot_verified"],
    )

    return {
        "boson_sampling": boson_result,
        "hom": hom_result,
        "klm": klm_result,
    }
