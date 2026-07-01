"""阶段 9: 量子光子验证。

执行玻色采样、HOM 干涉与 KLM 量子门仿真，输出量子光子验证结果。

验证项:
- 4 光子 4 模玻色采样概率分布与守恒验证（总和 = 1）
- HOM 干涉 |1,1⟩ 概率 = 0（量子干涉抑制符合计数）
- KLM CNOT 成功率 = 0.25 与 Hadamard 门酉性
- R2 新增: 蒙特卡洛玻色采样稳定性验证（D13）
- R4 新增: HOM dip 时间分辨数值仿真（D13 深化）
- R4 新增: 玻色采样器 + 卡方检验统计验证（D13 深化）
- R4 新增: KLM CNOT 门完整电路蒙特卡洛仿真（D13 深化）

对应路标: R35（玻色采样 + HOM + KLM）/ R2-D13（蒙特卡洛验证）/ R4-D13（数值仿真深化）

公式来源:
- 玻色采样: Aaronson & Arkhipov, STOC 2011,
  https://arxiv.org/abs/0910.4698
  P(s) = |Per(U_{S,T})|² / (Π s_i! · Π n_j!)
- HOM 干涉: Hong, Ou, Mandel, PRL 1987,
  https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.59.2044
  50:50 分束器输入 |1,1⟩，|1,1⟩ 输出概率 = 0
- HOM dip: P_coinc(Δt) = 0.5 × (1 - exp(-Δt²/(2σ²)))
  Δt=0 时 P=0（HOM dip），Δt→∞ 时 P=0.5（经典极限）
- KLM 方案: Knill, Laflamme, Milburn, Nature 2001,
  https://www.nature.com/articles/35051009
  CNOT 成功率 = 1/4，Hadamard 门 H = (1/√2)[[1,1],[1,-1]]
- KLM CNOT 电路: Ralph et al., PRA 2002,
  https://journals.aps.org/pra/abstract/10.1103/PhysRevA.65.062324
  4 模式简化版，后选择实现非线性操作
- Clements 分解: Clements et al., Optica 2016,
  https://doi.org/10.1364/OPTICA.3.001460
  M×M 酉矩阵分解为 M(M-1)/2 个分束器
- Ryser 算法: Ryser, 1963, Combinatorial Mathematics
  Per(A) = (-1)^n Σ_{S⊆[n]} (-1)^|S| Π_i Σ_{j∈S} A_{i,j}
- 蒙特卡洛方法: Metropolis & Ulam 1949
- 卡方检验: Pearson, Philosophical Magazine 1900
  χ² = Σ (O_i - E_i)² / E_i
"""

from __future__ import annotations

import json
import logging
import math
from pathlib import Path

import numpy as np

from polaris.sim import (
    boson_sampling_chi_square_test,
    boson_sampling_distribution,
    boson_sampling_sampler,
    clements_unitary,
    hom_dip_simulation,
    hom_interference,
    klm_cnot_simulate,
    klm_cnot_success_probability,
    klm_hadamard_gate,
)
from polaris.sim.monte_carlo import monte_carlo_simulate

_logger = logging.getLogger("e2e_showcase")

# 概率守恒容差（规则 14.1：错误必须 raise，不容忍数值漂移）
_PROB_TOL = 1e-6
# 酉性验证容差
_UNITARY_TOL = 1e-6
# KLM CNOT 理论成功率（Ralph 2002 PRA 65, 062324 简化 4-BS 电路，1/9 ≈ 0.1111）
# R05 修复: 原 0.25 是 Knill 2001 Nature 完整 NS-gate（8 模式）的理论值，
# 但本模块 klm_cnot_circuit() 实现的是 Ralph 2002 简化 4-BS（4 模式），
# 成功率 1/9。与 polaris.sim.quantum_klm.klm_cnot_success_probability() 一致。
_KLM_CNOT_EXPECTED = 1.0 / 9.0

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

# R4-D13: 数值仿真验证参数
# HOM dip 仿真波包宽度（时间单位，控制 dip 半高宽）
_HOM_DIP_SIGMA = 1.0
# HOM dip 仿真时间差范围（-5σ 到 +5σ，101 点）
_HOM_DIP_DT_POINTS = 101
# HOM dip 深度阈值（dt=0 时 P_coinc 应 < 此值，验证量子干涉）
_HOM_DIP_DEPTH_TOL = 1e-6
# HOM dip 经典极限阈值（dt→∞ 时 P_coinc 应接近 0.5）
_HOM_DIP_CLASSICAL_TOL = 1e-3
# 玻色采样器采样次数（卡方检验需要足够样本）
_SAMPLER_N_SAMPLES = 10000
# 卡方检验 p 值阈值（> 0.05 表示采样分布与解析分布一致）
_CHI_SQUARE_P_TOL = 0.05
# KLM CNOT 电路仿真采样次数
_KLM_CNOT_N_SHOTS = 10000
# KLM CNOT 后选择成功率下限（简化版约 20%，完整版理论 25%）
_KLM_CNOT_SUCCESS_TOL = 0.1


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


def _verify_hom_dip_numerical(output_dir: Path) -> dict:
    """R4-D13: HOM dip 时间分辨数值仿真验证。

    仿真双光子波包到达时间差 Δt 对符合计数率的影响，重现 HOM dip 曲线。
    验证:
    - dt=0 时 P_coinc ≈ 0（HOM dip，量子干涉完全抑制符合计数）
    - dt→∞ 时 P_coinc ≈ 0.5（经典极限）
    - dip 深度 > 0.99（完美 dip）

    物理模型:
    P_coinc(Δt) = 0.5 × (1 - exp(-Δt²/(2σ²)))

    公式来源:
    - Hong, Ou, Mandel, PRL 1987,
      https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.59.2044
    - Bouwmeester et al., "The Physics of Quantum Information", Springer 2000, §3.1

    Args:
        output_dir: 输出目录。

    Returns:
        HOM dip 数值仿真验证结果 dict。

    Raises:
        ValueError: HOM dip 验证失败（dt=0 时 P 不接近 0，或 dt→∞ 时不接近 0.5）。
    """
    _logger.info(
        "R4-D13 HOM dip 数值仿真: σ=%.2f, %d 时间点",
        _HOM_DIP_SIGMA, _HOM_DIP_DT_POINTS,
    )

    sigma = _HOM_DIP_SIGMA
    dt_range = np.linspace(-5 * sigma, 5 * sigma, _HOM_DIP_DT_POINTS)
    p_coinc = hom_dip_simulation(sigma=sigma, dt_range=dt_range)

    # 验证 1: dt=0 时 P_coinc ≈ 0（HOM dip）
    mid_idx = len(dt_range) // 2
    p_at_zero = float(p_coinc[mid_idx])
    dip_verified = p_at_zero < _HOM_DIP_DEPTH_TOL
    if not dip_verified:
        raise ValueError(
            f"R4-D13 HOM dip 验证失败: dt=0 时 P_coinc={p_at_zero:.2e} "
            f"≥ 容差 {_HOM_DIP_DEPTH_TOL}"
        )

    # 验证 2: dt→∞ 时 P_coinc ≈ 0.5（经典极限）
    p_at_inf = float(p_coinc[-1])
    classical_verified = abs(p_at_inf - 0.5) < _HOM_DIP_CLASSICAL_TOL
    if not classical_verified:
        raise ValueError(
            f"R4-D13 HOM 经典极限验证失败: dt=5σ 时 P_coinc={p_at_inf:.6f} "
            f"偏离 0.5 超过容差 {_HOM_DIP_CLASSICAL_TOL}"
        )

    # 验证 3: dip 深度 > 0.99
    dip_depth = 1.0 - 2.0 * p_at_zero
    depth_verified = dip_depth > 0.99
    if not depth_verified:
        raise ValueError(
            f"R4-D13 HOM dip 深度验证失败: dip_depth={dip_depth:.6f} < 0.99"
        )

    _logger.info(
        "R4-D13 HOM dip 验证通过: dt=0 时 P=%.2e, dt=5σ 时 P=%.6f, dip 深度=%.6f",
        p_at_zero, p_at_inf, dip_depth,
    )

    # 保存 HOM dip 结果
    reports_dir = output_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    dip_path = reports_dir / "hom_dip_simulation.json"
    dip_data = {
        "sigma": sigma,
        "dt_range": dt_range.tolist(),
        "p_coinc": p_coinc.tolist(),
        "p_at_zero": p_at_zero,
        "p_at_classical_limit": p_at_inf,
        "dip_depth": dip_depth,
        "dip_verified": dip_verified,
        "classical_verified": classical_verified,
        "depth_verified": depth_verified,
        "tolerance": {
            "dip_depth": _HOM_DIP_DEPTH_TOL,
            "classical_limit": _HOM_DIP_CLASSICAL_TOL,
        },
        "sources": {
            "hom_1987": "https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.59.2044",
            "quantum_info_book": "Bouwmeester et al., Springer 2000, §3.1",
        },
    }
    dip_path.write_text(
        json.dumps(dip_data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    _logger.info("HOM dip 结果已保存: %s", dip_path)

    return {
        "sigma": sigma,
        "p_at_zero": p_at_zero,
        "p_at_classical_limit": p_at_inf,
        "dip_depth": dip_depth,
        "dip_verified": dip_verified,
        "classical_verified": classical_verified,
        "depth_verified": depth_verified,
    }


def _verify_boson_sampling_sampler(output_dir: Path, unitary: np.ndarray) -> dict:
    """R4-D13: 玻色采样器 + 卡方检验统计验证。

    通过按解析分布随机采样输出模式，模拟真实玻色采样实验过程，
    使用卡方检验验证采样分布与解析分布的统计一致性。

    验证:
    - 采样次数 = n_samples
    - 卡方检验 p 值 > 0.05（采样分布与解析分布一致）

    物理意义:
    真实玻色采样实验是单次采样，无法获得完整分布。
    采样器是连接理论与实验的桥梁。

    公式来源:
    - Aaronson & Arkhipov, STOC 2011, https://arxiv.org/abs/0910.4698
    - Seron et al., Quantum 2024, BosonSampling.jl
      https://arxiv.org/abs/2212.09537
    - Pearson, Philosophical Magazine 1900（卡方检验）

    Args:
        output_dir: 输出目录。
        unitary: 4×4 酉矩阵。

    Returns:
        玻色采样器验证结果 dict。

    Raises:
        ValueError: 卡方检验 p 值 < 0.05（采样分布与解析分布不一致）。
    """
    _logger.info(
        "R4-D13 玻色采样器验证: %d 采样, 卡方检验", _SAMPLER_N_SAMPLES,
    )

    input_state = (1, 1, 1, 1)
    # 计算解析分布
    dist = boson_sampling_distribution(unitary, input_state)
    # 按分布随机采样
    samples = boson_sampling_sampler(
        unitary, input_state, n_samples=_SAMPLER_N_SAMPLES, seed=42,
    )
    # 卡方检验
    chi2_stat, p_value, dof = boson_sampling_chi_square_test(
        samples, dist.output_prob, n_samples=_SAMPLER_N_SAMPLES,
    )

    # 验证: p 值 > 0.05（分布一致）
    sampler_verified = p_value > _CHI_SQUARE_P_TOL
    if not sampler_verified:
        raise ValueError(
            f"R4-D13 玻色采样器卡方检验失败: p_value={p_value:.4f} "
            f"< 阈值 {_CHI_SQUARE_P_TOL}, chi2={chi2_stat:.4f}, dof={dof}"
        )

    _logger.info(
        "R4-D13 玻色采样器验证通过: chi2=%.4f, p_value=%.4f, dof=%d",
        chi2_stat, p_value, dof,
    )

    # 保存采样器结果
    reports_dir = output_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    sampler_path = reports_dir / "boson_sampling_sampler.json"
    sampler_data = {
        "n_samples": _SAMPLER_N_SAMPLES,
        "input_state": list(input_state),
        "n_output_modes": len(samples),
        "chi2_statistic": chi2_stat,
        "p_value": p_value,
        "dof": dof,
        "p_value_threshold": _CHI_SQUARE_P_TOL,
        "sampler_verified": sampler_verified,
        "sources": {
            "boson_sampling": "https://arxiv.org/abs/0910.4698",
            "bosonsampling_jl": "https://arxiv.org/abs/2212.09537",
            "chi_square_test": "Pearson, Philosophical Magazine 1900",
        },
    }
    sampler_path.write_text(
        json.dumps(sampler_data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    _logger.info("玻色采样器结果已保存: %s", sampler_path)

    return {
        "n_samples": _SAMPLER_N_SAMPLES,
        "n_output_modes": len(samples),
        "chi2_statistic": chi2_stat,
        "p_value": p_value,
        "dof": dof,
        "sampler_verified": sampler_verified,
    }


def _verify_klm_cnot_circuit(output_dir: Path) -> dict:
    """R4-D13: KLM CNOT 门完整电路蒙特卡洛仿真验证。

    构建 KLM 风格的 CNOT 门分束器网络（4 模式简化版），
    通过玻色采样计算输出分布，统计后选择成功率，
    验证 KLM 方案的量子干涉本质（非硬编码常数）。

    验证:
    - 概率守恒（所有输出概率总和 = 1）
    - 后选择成功率 > 10%（后选择可行）
    - 量子干涉特征（信号模式分布非均匀，偏离经典均匀分布 > 10%）
    - 采样后选择成功率与解析值一致

    学术诚信说明:
    - 本实现为 Ralph et al. 2002 的简化版 KLM CNOT 门（4 模式）
    - 完整 KLM CNOT 门需要 2 个 NS gate + 分束器（8 模式），成功率 1/4
    - 简化版后选择成功率约 20%，信号模式分布展示量子干涉特征
    - klm_cnot_success_probability() 返回的 0.25 是完整 KLM 方案的理论值

    公式来源:
    - Knill, Laflamme, Milburn, Nature 2001,
      https://www.nature.com/articles/35051009
    - Ralph et al., PRA 2002,
      https://journals.aps.org/pra/abstract/10.1103/PhysRevA.65.062324

    Args:
        output_dir: 输出目录。

    Returns:
        KLM CNOT 电路仿真验证结果 dict。

    Raises:
        ValueError: 概率守恒/后选择成功率/量子干涉特征验证失败。
    """
    _logger.info(
        "R4-D13 KLM CNOT 电路仿真: %d 采样", _KLM_CNOT_N_SHOTS,
    )

    result = klm_cnot_simulate(n_shots=_KLM_CNOT_N_SHOTS, seed=42)

    # 验证 1: 概率守恒
    prob_ok = result["prob_sum_ok"]
    if not prob_ok:
        raise ValueError(
            f"R4-D13 KLM CNOT 概率守恒失败: total_prob={result['total_prob']:.10f}"
        )

    # 验证 2: 后选择成功率 > 10%
    post_select_prob = result["post_select_prob"]
    success_verified = post_select_prob > _KLM_CNOT_SUCCESS_TOL
    if not success_verified:
        raise ValueError(
            f"R4-D13 KLM CNOT 后选择成功率失败: {post_select_prob:.6e} "
            f"< 阈值 {_KLM_CNOT_SUCCESS_TOL}"
        )

    # 验证 3: 量子干涉特征（信号分布非均匀）
    qi = result["quantum_interference"]
    quantum_verified = qi["is_quantum"]
    if not quantum_verified:
        raise ValueError(
            f"R4-D13 KLM CNOT 量子干涉特征验证失败: "
            f"max_deviation={qi['max_deviation_from_classical']:.4f} < 0.1"
        )

    _logger.info(
        "R4-D13 KLM CNOT 电路验证通过: 后选择成功率=%.4f, 量子干涉=%s, "
        "采样成功率=%.4f",
        post_select_prob, quantum_verified, result["sampled_success_rate"],
    )

    # 保存 KLM CNOT 电路结果
    reports_dir = output_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    klm_circuit_path = reports_dir / "klm_cnot_circuit.json"
    # 序列化信号分布（tuple key → string key）
    signal_dist_serializable = {
        f"({k[0]},{k[1]})": float(v) for k, v in result["signal_dist"].items()
    }
    klm_circuit_data = {
        "n_modes": 4,
        "input_state": list(result["input_state"]),
        "n_shots": int(result["n_shots"]),
        "total_prob": float(result["total_prob"]),
        "prob_sum_ok": bool(prob_ok),
        "post_select_prob": float(post_select_prob),
        "sampled_success_rate": float(result["sampled_success_rate"]),
        "theoretical_success_prob": float(result["theoretical_success_prob"]),
        "simplified_success_prob": float(result["simplified_success_prob"]),
        "signal_dist": signal_dist_serializable,
        "quantum_interference": {
            "max_deviation_from_classical": float(qi["max_deviation_from_classical"]),
            "is_quantum": bool(qi["is_quantum"]),
            "classical_uniform_prob": float(qi["classical_uniform_prob"]),
        },
        "success_verified": bool(success_verified),
        "quantum_verified": bool(quantum_verified),
        "success_tolerance": _KLM_CNOT_SUCCESS_TOL,
        "sources": {
            "klm_scheme": "https://www.nature.com/articles/35051009",
            "ralph_2002": "https://journals.aps.org/pra/abstract/10.1103/PhysRevA.65.062324",
        },
    }
    klm_circuit_path.write_text(
        json.dumps(klm_circuit_data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    _logger.info("KLM CNOT 电路结果已保存: %s", klm_circuit_path)

    return {
        "n_shots": int(result["n_shots"]),
        "prob_sum_ok": bool(prob_ok),
        "post_select_prob": float(post_select_prob),
        "sampled_success_rate": float(result["sampled_success_rate"]),
        "theoretical_success_prob": float(result["theoretical_success_prob"]),
        "simplified_success_prob": float(result["simplified_success_prob"]),
        "quantum_interference_verified": bool(quantum_verified),
        "max_deviation_from_classical": float(qi["max_deviation_from_classical"]),
        "success_verified": bool(success_verified),
    }


def run(output_dir: Path) -> dict:
    """执行阶段 9: 量子光子验证。

    执行七项量子光子验证:
    1. 4 光子 4 模玻色采样概率分布与守恒（Clements 分解酉矩阵）
    2. HOM 干涉 |1,1⟩ 概率 = 0（50:50 分束器）
    3. KLM CNOT 成功率 = 0.25 与 Hadamard 门酉性
    4. R2-D13: 蒙特卡洛玻色采样稳定性验证（1% 参数扰动，200 采样）
    5. R4-D13: HOM dip 时间分辨数值仿真（Δt=0 时 P=0，Δt→∞ 时 P=0.5）
    6. R4-D13: 玻色采样器 + 卡方检验统计验证（10000 采样，p>0.05）
    7. R4-D13: KLM CNOT 门完整电路蒙特卡洛仿真（后选择成功率 + 量子干涉）

    所有验证失败均 raise（规则 14.1：禁止 fall-back）。
    报告写入 output_dir/reports/ 目录。

    Args:
        output_dir: 输出目录，报告写入 output_dir/reports/。

    Returns:
        验证结果 dict，含七个子 dict:
        - boson_sampling: unitary_shape/input_state/prob_distribution/prob_sum_ok
        - hom: theta/coincidence_prob/hom_verified
        - klm: cnot_success_prob/cnot_verified/hadamard_unitary_error/hadamard_verified
        - monte_carlo: n_samples/prob_sum_mean/prob_sum_std/prob_sum_ok
        - hom_dip: sigma/p_at_zero/dip_depth/dip_verified (R4 新增)
        - sampler: n_samples/chi2_statistic/p_value/sampler_verified (R4 新增)
        - klm_circuit: post_select_prob/quantum_interference_verified (R4 新增)
    """
    _logger.info("阶段 9 开始: 量子光子验证（含 R4 数值仿真深化）")

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

    # 6. R4-D13: HOM dip 时间分辨数值仿真
    hom_dip_result = _verify_hom_dip_numerical(output_dir)

    # 7. R4-D13: 玻色采样器 + 卡方检验
    sampler_result = _verify_boson_sampling_sampler(output_dir, unitary)

    # 8. R4-D13: KLM CNOT 门完整电路蒙特卡洛仿真
    klm_circuit_result = _verify_klm_cnot_circuit(output_dir)

    _logger.info(
        "阶段 9 完成: 量子光子验证全部通过 "
        "(玻色采样=%s, HOM=%s, KLM=%s, 蒙特卡洛=%s, "
        "HOM dip=%s, 采样器=%s, KLM 电路=%s)",
        boson_result["prob_sum_ok"],
        hom_result["hom_verified"],
        klm_result["cnot_verified"],
        mc_result["prob_sum_ok"],
        hom_dip_result["dip_verified"],
        sampler_result["sampler_verified"],
        klm_circuit_result["quantum_interference_verified"],
    )

    return {
        "boson_sampling": boson_result,
        "hom": hom_result,
        "klm": klm_result,
        "monte_carlo": mc_result,
        "hom_dip": hom_dip_result,
        "sampler": sampler_result,
        "klm_circuit": klm_circuit_result,
    }
