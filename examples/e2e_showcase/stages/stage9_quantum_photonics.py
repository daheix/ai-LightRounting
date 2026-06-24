"""阶段 9: 量子光子验证。

执行玻色采样、HOM 干涉与 KLM 量子门仿真，输出量子光子验证结果。

验证项:
- 4 光子 4 模玻色采样概率分布与守恒验证（总和 = 1）
- HOM 干涉 |1,1⟩ 概率 = 0（量子干涉抑制符合计数）
- KLM CNOT 成功率 = 0.25 与 Hadamard 门酉性
- R2 新增: 蒙特卡洛玻色采样稳定性验证（D13）

对应路标: R35（玻色采样 + HOM + KLM）/ R2-D13（蒙特卡洛验证）

公式来源:
- 玻色采样: Aaronson & Arkhipov, STOC 2011,
  https://arxiv.org/abs/0910.4698
  P(s) = |Per(U_{S,T})|² / (Π s_i! · Π n_j!)
- HOM 干涉: Hong, Ou, Mandel, PRL 1987,
  https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.59.2044
  50:50 分束器输入 |1,1⟩，|1,1⟩ 输出概率 = 0
- KLM 方案: Knill, Laflamme, Milburn, Nature 2001,
  https://www.nature.com/articles/35051009
  CNOT 成功率 = 1/4，Hadamard 门 H = (1/√2)[[1,1],[1,-1]]
- Clements 分解: Clements et al., Optica 2016,
  https://doi.org/10.1364/OPTICA.3.001460
  M×M 酉矩阵分解为 M(M-1)/2 个分束器
- Ryser 算法: Ryser, 1963, Combinatorial Mathematics
  Per(A) = (-1)^n Σ_{S⊆[n]} (-1)^|S| Π_i Σ_{j∈S} A_{i,j}
- 蒙特卡洛方法: Metropolis & Ulam 1949;
  JAX vmap 并行: https://docs.jax.dev/en/latest/_autosummary/jax.vmap.html
"""

from __future__ import annotations

import json
import logging
import math
from pathlib import Path

import numpy as np

from polaris.sim import (
    boson_sampling_distribution,
    clements_unitary,
    hom_interference,
    klm_cnot_success_probability,
    klm_hadamard_gate,
)
from polaris.sim.monte_carlo import monte_carlo_simulate

_logger = logging.getLogger("e2e_showcase")

# 概率守恒容差（规则 14.1：错误必须 raise，不容忍数值漂移）
_PROB_TOL = 1e-6
# 酉性验证容差
_UNITARY_TOL = 1e-6
# KLM CNOT 理论成功率（Knill et al., Nature 2001）
_KLM_CNOT_EXPECTED = 0.25

# R2-D13: 蒙特卡洛玻色采样验证参数
# 演示用任意参数（非物理常量），用于生成有效 4×4 酉矩阵
# theta 控制分束比，phi 控制相对相位（Clements et al., Optica 2016）
_CLEMENTS_THETAS = np.array(
    [math.pi / 4, math.pi / 6, math.pi / 3, math.pi / 5, math.pi / 8, math.pi / 7]
)
_CLEMENTS_PHIS = np.array(
    [0.0, math.pi / 4, math.pi / 2, math.pi / 3, math.pi / 6, math.pi / 5]
)
# 蒙特卡洛采样数（R2-D13: 玻色采样稳定性验证）
_MC_N_SAMPLES = 200
# 蒙特卡洛参数扰动标准差（1%，模拟制造工艺波动）
_MC_SIGMA = 0.01
# 蒙特卡洛概率守恒容差（扰动后概率总和仍应接近 1）
_MC_PROB_TOL = 1e-4


def _build_clements_unitary() -> np.ndarray:
    """用 Clements 分解生成 4×4 酉矩阵。

    Clements 三角形拓扑: M=4 模需 M(M-1)/2 = 6 个分束器，
    每个分束器由 (theta, phi) 参数化。

    公式来源:
    - Clements et al., Optica 2016,
      https://doi.org/10.1364/OPTICA.3.001460

    Returns:
        4×4 酉矩阵（complex）。

    Raises:
        ValueError: 生成的矩阵不满足酉性。
    """
    n_modes = 4
    # Clements 三角形拓扑: 6 个分束器参数（theta, phi 各 6 个）
    # theta 控制分束比，phi 控制相对相位
    # R2: 使用模块级常量 _CLEMENTS_THETAS/_CLEMENTS_PHIS（演示用任意参数）
    thetas = _CLEMENTS_THETAS
    phis = _CLEMENTS_PHIS
    n_bs = n_modes * (n_modes - 1) // 2
    _logger.info(
        "Clements 分解: %d 模, %d 个分束器 (theta/phi 各 %d)",
        n_modes,
        n_bs,
        n_bs,
    )
    unitary = clements_unitary(n_modes, thetas=thetas, phis=phis)
    # 验证酉性: U @ U† = I
    identity = np.eye(n_modes, dtype=complex)
    unitary_err = float(np.max(np.abs(unitary @ unitary.conj().T - identity)))
    if unitary_err > _UNITARY_TOL:
        raise ValueError(
            f"Clements 酉矩阵酉性验证失败: 最大误差 {unitary_err:.2e} > 容差 {_UNITARY_TOL}"
        )
    _logger.info("Clements 酉性验证通过: 最大误差 %.2e", unitary_err)
    return unitary


def _verify_boson_sampling(output_dir: Path, unitary: np.ndarray) -> dict:
    """执行 4 光子 4 模玻色采样并验证概率守恒。

    输入态 |1,1,1,1⟩（4 光子 4 模），计算完整输出概率分布，
    验证所有输出概率之和 = 1（光子数守恒下的概率归一化）。

    公式来源:
    - Aaronson & Arkhipov, STOC 2011, https://arxiv.org/abs/0910.4698
      P(s) = |Per(U_{S,T})|² / (Π s_i! · Π n_j!)
    - Ryser 算法（积和式计算）: Ryser, 1963, Combinatorial Mathematics

    Args:
        output_dir: 输出目录。
        unitary: 4×4 酉矩阵。

    Returns:
        玻色采样验证结果 dict。

    Raises:
        ValueError: 概率守恒验证失败。
    """
    input_state = (1, 1, 1, 1)
    n_photons = sum(input_state)
    _logger.info(
        "玻色采样: 输入态 |%s⟩ (%d 光子 %d 模)",
        ",".join(str(s) for s in input_state),
        n_photons,
        len(input_state),
    )

    result = boson_sampling_distribution(unitary, input_state)
    _logger.info("玻色采样完成: %d 个可能输出模式", len(result.output_prob))

    # 验证概率守恒: 所有输出概率之和 = 1
    prob_sum = float(sum(result.output_prob.values()))
    prob_sum_ok = abs(prob_sum - 1.0) <= _PROB_TOL
    if not prob_sum_ok:
        raise ValueError(
            f"玻色采样概率守恒失败: 总和 {prob_sum:.10f} 偏离 1.0 超过容差 {_PROB_TOL}"
        )
    _logger.info("概率守恒验证通过: 总和 = %.10f", prob_sum)

    # 找出 top-3 概率最高的输出模式
    sorted_outputs = sorted(result.output_prob.items(), key=lambda x: x[1], reverse=True)
    for state, prob in sorted_outputs[:3]:
        _logger.info(
            "  输出 |%s⟩: 概率 %.6e",
            ",".join(str(s) for s in state),
            prob,
        )

    # 保存概率分布到 JSON
    reports_dir = output_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    dist_path = reports_dir / "boson_sampling_dist.json"
    dist_data = {
        "n_modes": result.n_modes,
        "n_photons": result.n_photons,
        "input_state": list(input_state),
        "unitary_shape": [int(unitary.shape[0]), int(unitary.shape[1])],
        "n_outputs": len(result.output_prob),
        "prob_sum": prob_sum,
        "prob_sum_ok": prob_sum_ok,
        "prob_tolerance": _PROB_TOL,
        "distribution": {
            ",".join(str(s) for s in state): prob
            for state, prob in result.output_prob.items()
        },
        "sources": {
            "boson_sampling": "https://arxiv.org/abs/0910.4698",
            "ryser_algorithm": "Ryser, 1963, Combinatorial Mathematics",
        },
    }
    dist_path.write_text(
        json.dumps(dist_data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    _logger.info("概率分布已保存: %s", dist_path)

    return {
        "unitary_shape": [int(unitary.shape[0]), int(unitary.shape[1])],
        "input_state": list(input_state),
        "n_outputs": len(result.output_prob),
        "prob_distribution": {
            ",".join(str(s) for s in state): prob
            for state, prob in result.output_prob.items()
        },
        "prob_sum": prob_sum,
        "prob_sum_ok": prob_sum_ok,
    }


def _verify_hom_interference(output_dir: Path) -> dict:
    """验证 HOM 干涉 |1,1⟩ 概率 = 0。

    50:50 分束器（θ=π/4）输入两个全同光子 |1,1⟩，HOM 凹陷导致
    |1,1⟩ 输出概率为 0（量子干涉完全抑制符合计数），
    |2,0⟩ 与 |0,2⟩ 各占 50%。

    公式来源:
    - Hong, Ou, Mandel, PRL 1987,
      https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.59.2044

    Args:
        output_dir: 输出目录。

    Returns:
        HOM 干涉验证结果 dict。

    Raises:
        ValueError: HOM 干涉验证失败（|1,1⟩ 概率不为 0）。
    """
    theta = math.pi / 4  # 50:50 分束器
    _logger.info("HOM 干涉: 50:50 分束器 θ=π/4, 输入 |1,1⟩")

    hom_result = hom_interference(theta=theta)
    # hom_interference 返回 {"(2,0)": p, "(0,2)": p, "(1,1)": p}
    # 符合计数率 = |1,1⟩ 输出概率（HOM 凹陷下应为 0）
    coincidence_prob = float(hom_result["(1,1)"])
    hom_verified = abs(coincidence_prob) <= _PROB_TOL
    if not hom_verified:
        raise ValueError(
            f"HOM 干涉验证失败: |1,1⟩ 概率 {coincidence_prob:.2e} > 容差 {_PROB_TOL}"
        )
    _logger.info("HOM 干涉验证通过: |1,1⟩ 概率 = %.2e", coincidence_prob)
    _logger.info(
        "HOM 输出分布: |2,0⟩=%.6f, |0,2⟩=%.6f, |1,1⟩=%.2e",
        hom_result["(2,0)"],
        hom_result["(0,2)"],
        hom_result["(1,1)"],
    )

    # 保存 HOM 结果
    reports_dir = output_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    hom_path = reports_dir / "hom_interference.json"
    hom_data = {
        "theta": theta,
        "beamsplitter_ratio": "50:50",
        "input_state": [1, 1],
        "output_prob": hom_result,
        "coincidence_prob": coincidence_prob,
        "hom_verified": hom_verified,
        "tolerance": _PROB_TOL,
        "sources": {
            "hom_interference": "https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.59.2044",
        },
    }
    hom_path.write_text(
        json.dumps(hom_data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    _logger.info("HOM 结果已保存: %s", hom_path)

    return {
        "theta": theta,
        "coincidence_prob": coincidence_prob,
        "hom_verified": hom_verified,
    }


def _verify_klm(output_dir: Path) -> dict:
    """验证 KLM CNOT 成功率 = 0.25 与 Hadamard 门酉性。

    KLM 方案用线性光学实现量子门:
    - CNOT 门成功率为 1/4（25%），需要后选择（非确定性门）
    - Hadamard 门 H = (1/√2)[[1,1],[1,-1]]，满足 H @ H† = I（酉性）

    公式来源:
    - Knill, Laflamme, Milburn, Nature 2001,
      https://www.nature.com/articles/35051009

    Args:
        output_dir: 输出目录。

    Returns:
        KLM 验证结果 dict。

    Raises:
        ValueError: CNOT 成功率或 Hadamard 酉性验证失败。
    """
    _logger.info("KLM 验证: CNOT 成功率与 Hadamard 门酉性")

    # 1. KLM CNOT 成功率验证（理论值 0.25）
    cnot_success_prob = float(klm_cnot_success_probability())
    cnot_verified = abs(cnot_success_prob - _KLM_CNOT_EXPECTED) <= _PROB_TOL
    if not cnot_verified:
        raise ValueError(
            f"KLM CNOT 成功率验证失败: {cnot_success_prob} 偏离 "
            f"{_KLM_CNOT_EXPECTED} 超过容差 {_PROB_TOL}"
        )
    _logger.info(
        "KLM CNOT 成功率验证通过: %.4f (理论值 %.2f)",
        cnot_success_prob,
        _KLM_CNOT_EXPECTED,
    )

    # 2. Hadamard 门酉性验证: H @ H† = I
    hadamard = klm_hadamard_gate()
    identity = np.eye(2, dtype=complex)
    hadamard_err = float(np.max(np.abs(hadamard @ hadamard.conj().T - identity)))
    hadamard_verified = hadamard_err <= _UNITARY_TOL
    if not hadamard_verified:
        raise ValueError(
            f"Hadamard 门酉性验证失败: 最大误差 {hadamard_err:.2e} > 容差 {_UNITARY_TOL}"
        )
    _logger.info("Hadamard 门酉性验证通过: 最大误差 %.2e", hadamard_err)

    # 保存 KLM 结果
    reports_dir = output_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    klm_path = reports_dir / "klm_verification.json"
    klm_data = {
        "cnot_success_prob": cnot_success_prob,
        "cnot_expected": _KLM_CNOT_EXPECTED,
        "cnot_verified": cnot_verified,
        "cnot_tolerance": _PROB_TOL,
        "hadamard_gate": [
            [hadamard[0, 0].real, hadamard[0, 1].real],
            [hadamard[1, 0].real, hadamard[1, 1].real],
        ],
        "hadamard_unitary_error": hadamard_err,
        "hadamard_verified": hadamard_verified,
        "hadamard_tolerance": _UNITARY_TOL,
        "sources": {
            "klm_scheme": "https://www.nature.com/articles/35051009",
        },
    }
    klm_path.write_text(
        json.dumps(klm_data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    _logger.info("KLM 结果已保存: %s", klm_path)

    return {
        "cnot_success_prob": cnot_success_prob,
        "cnot_verified": cnot_verified,
        "hadamard_unitary_error": hadamard_err,
        "hadamard_verified": hadamard_verified,
    }


def _verify_monte_carlo_boson_sampling(output_dir: Path, unitary: np.ndarray) -> dict:
    """R2-D13: 蒙特卡洛玻色采样稳定性验证。

    对 Clements 酉矩阵的分束器参数（thetas/phis）施加 1% 高斯扰动，
    执行 N 次蒙特卡洛采样，验证玻色采样概率守恒在参数扰动下仍成立。

    物理意义: 模拟制造工艺波动（分束比误差 ±1%）对玻色采样的影响，
    验证量子光子电路的鲁棒性。

    方法:
    1. 将 thetas/phis 合并为基准参数向量
    2. 对参数施加高斯扰动，用 numpy 循环计算每次采样的概率总和
       （注: clements_unitary 内部含 float() 转换，不兼容 jax.vmap，
       故用 numpy 循环替代 monte_carlo_simulate）
    3. 验证所有采样的概率总和在 [1-ε, 1+ε] 范围内

    公式来源:
    - 蒙特卡洛方法: Metropolis & Ulam 1949
    - 玻色采样: Aaronson & Arkhipov 2011 https://arxiv.org/abs/0910.4698
    - Clements 分解: Clements et al., Optica 2016

    Args:
        output_dir: 输出目录。
        unitary: 基准 4×4 酉矩阵（用于验证基准概率守恒）。

    Returns:
        蒙特卡洛验证结果 dict。

    Raises:
        ValueError: 蒙特卡洛采样中概率守恒失败。
    """
    _logger.info(
        "R2-D13 蒙特卡洛玻色采样验证: %d 采样, σ=%.2f", _MC_N_SAMPLES, _MC_SIGMA
    )

    n_modes = 4
    input_state = (1, 1, 1, 1)
    # 基准参数: thetas(6) + phis(6) = 12 个参数
    base_params = np.concatenate([_CLEMENTS_THETAS, _CLEMENTS_PHIS])

    # 生成高斯随机扰动（Metropolis & Ulam 1949 蒙特卡洛方法）
    rng = np.random.default_rng(seed=42)
    noise = rng.normal(0, 1, size=(_MC_N_SAMPLES, len(base_params)))
    # 参数扰动: params_i = base · (1 + σ · ε)
    samples_params = base_params * (1 + _MC_SIGMA * noise)

    # numpy 循环执行蒙特卡洛采样
    # 注: clements_unitary 内部含 float() 转换，不兼容 jax.vmap，
    # 故用 numpy 循环替代 monte_carlo_simulate
    prob_sums = np.zeros(_MC_N_SAMPLES)
    for i in range(_MC_N_SAMPLES):
        thetas_p = samples_params[i, :6]
        phis_p = samples_params[i, 6:]
        u = clements_unitary(n_modes, thetas=thetas_p, phis=phis_p)
        result = boson_sampling_distribution(u, input_state)
        prob_sums[i] = sum(result.output_prob.values())

    # 统计分析
    prob_sum_mean = float(np.mean(prob_sums))
    prob_sum_std = float(np.std(prob_sums))
    prob_sum_min = float(np.min(prob_sums))
    prob_sum_max = float(np.max(prob_sums))

    # 概率守恒验证: 所有采样概率总和在 [1-ε, 1+ε] 范围内
    mc_prob_ok = bool(
        abs(prob_sum_mean - 1.0) < _MC_PROB_TOL
        and abs(prob_sum_min - 1.0) < _MC_PROB_TOL * 10
        and abs(prob_sum_max - 1.0) < _MC_PROB_TOL * 10
    )
    if not mc_prob_ok:
        raise ValueError(
            f"R2-D13 蒙特卡洛概率守恒失败: mean={prob_sum_mean:.8f}, "
            f"min={prob_sum_min:.8f}, max={prob_sum_max:.8f}, "
            f"容差={_MC_PROB_TOL}"
        )

    _logger.info(
        "R2-D13 蒙特卡洛验证通过: 概率总和 mean=%.8f, std=%.2e, "
        "min=%.8f, max=%.8f",
        prob_sum_mean, prob_sum_std, prob_sum_min, prob_sum_max,
    )

    # 保存蒙特卡洛结果到 JSON
    reports_dir = output_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    mc_path = reports_dir / "monte_carlo_boson_sampling.json"
    mc_data = {
        "n_samples": _MC_N_SAMPLES,
        "sigma": _MC_SIGMA,
        "input_state": list(input_state),
        "n_modes": n_modes,
        "prob_sum_mean": prob_sum_mean,
        "prob_sum_std": prob_sum_std,
        "prob_sum_min": prob_sum_min,
        "prob_sum_max": prob_sum_max,
        "prob_sum_ok": mc_prob_ok,
        "tolerance": _MC_PROB_TOL,
        "sources": {
            "monte_carlo": "Metropolis & Ulam 1949",
            "boson_sampling": "https://arxiv.org/abs/0910.4698",
            "clements": "https://doi.org/10.1364/OPTICA.3.001460",
        },
    }
    mc_path.write_text(
        json.dumps(mc_data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    _logger.info("蒙特卡洛结果已保存: %s", mc_path)

    return {
        "n_samples": _MC_N_SAMPLES,
        "sigma": _MC_SIGMA,
        "prob_sum_mean": prob_sum_mean,
        "prob_sum_std": prob_sum_std,
        "prob_sum_min": prob_sum_min,
        "prob_sum_max": prob_sum_max,
        "prob_sum_ok": mc_prob_ok,
    }


def run(output_dir: Path) -> dict:
    """执行阶段 9: 量子光子验证。

    执行四项量子光子验证:
    1. 4 光子 4 模玻色采样概率分布与守恒（Clements 分解酉矩阵）
    2. HOM 干涉 |1,1⟩ 概率 = 0（50:50 分束器）
    3. KLM CNOT 成功率 = 0.25 与 Hadamard 门酉性
    4. R2-D13: 蒙特卡洛玻色采样稳定性验证（1% 参数扰动，200 采样）

    所有验证失败均 raise（规则 14.1：禁止 fall-back）。
    报告写入 output_dir/reports/ 目录。

    Args:
        output_dir: 输出目录，报告写入 output_dir/reports/。

    Returns:
        验证结果 dict，含四个子 dict:
        - boson_sampling: unitary_shape/input_state/prob_distribution/prob_sum_ok
        - hom: theta/coincidence_prob/hom_verified
        - klm: cnot_success_prob/cnot_verified/hadamard_unitary_error/hadamard_verified
        - monte_carlo: n_samples/prob_sum_mean/prob_sum_std/prob_sum_ok
    """
    _logger.info("阶段 9 开始: 量子光子验证")

    # 1. 构建 Clements 酉矩阵（4×4）
    unitary = _build_clements_unitary()

    # 2. 玻色采样概率分布与守恒验证
    boson_result = _verify_boson_sampling(output_dir, unitary)

    # 3. HOM 干涉验证
    hom_result = _verify_hom_interference(output_dir)

    # 4. KLM 验证
    klm_result = _verify_klm(output_dir)

    # 5. R2-D13: 蒙特卡洛玻色采样稳定性验证
    mc_result = _verify_monte_carlo_boson_sampling(output_dir, unitary)

    _logger.info(
        "阶段 9 完成: 量子光子验证全部通过 "
        "(玻色采样概率守恒=%s, HOM 干涉=%s, KLM=%s, 蒙特卡洛=%s)",
        boson_result["prob_sum_ok"],
        hom_result["hom_verified"],
        klm_result["cnot_verified"],
        mc_result["prob_sum_ok"],
    )

    return {
        "boson_sampling": boson_result,
        "hom": hom_result,
        "klm": klm_result,
        "monte_carlo": mc_result,
    }
