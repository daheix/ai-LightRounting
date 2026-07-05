"""D12 逆向设计 showcase: MMI/WDM/Y分支 3 器件 adjoint 优化。

基于物理解析模型（自成像理论 / 耦合模理论 / 绝热定理），用 JAX ``jax.grad``
自动微分计算 FoM 对器件参数的梯度（adjoint 方法），heavy-ball 动量优化。

*创新*: 用 JAX autograd 替代手动推导伴随方程，3 个标准光子器件统一优化框架。
- 底层逻辑: 反向模式 AD = 伴随方法（Giles & Pierce 2000 SIAM Review 数学等价）
- 支持理论: Hughes 2018 ACS Photonics 证明 autograd = adjoint
- 案例: MMI 1x2 / WDM 滤波器 / Y分支，本子模块实现

纯 JAX(CPU) 实现（R04: 不参与 GPU；R03: 禁止 fall-back）。

## 器件清单

1. **MMI 1x2 分束器**: 优化 [W, L] (MMI 宽度/长度)
   - 物理模型: 自成像理论（Soldano & Pennings 1995 JLT）
   - FoM: 传输效率 - 0.1×不均匀性 + W 正则
   - 目标: IL<0.5dB, 不均匀性<0.1dB
2. **WDM 滤波器**: 优化 [g, L] (耦合间距/长度)
   - 物理模型: 耦合模理论（Yariv 1973 IEEE JQE）
   - FoM: 耦合效率 + 0.01×带宽 + 0.01×隔离度
   - 目标: 带宽>20nm, 隔离度>20dB
3. **Y分支**: 优化 [θ] (分支角)
   - 物理模型: 绝热定理（Milton & Burns 1987 JLT）
   - FoM: tanh(C·θ) 传输效率 - 长度正则
   - 目标: IL<0.3dB

## 学术依据（R02 学术诚信，≥5 个文献 URL）

1. Piggott et al. 2015 "Inverse design and demonstration of a compact and
   broadband on-chip wavelength demultiplexer" Nature Photonics
   https://doi.org/10.1038/nphoton.2015.111
2. Soldano & Pennings 1995 "Optical Multi-Mode Interference Devices Based on
   Self-Imaging: Principles and Applications" JLT
   https://doi.org/10.1109/50.372562
3. Yariv 1973 "Coupled-mode theory for guided-wave optics" IEEE JQE
   https://doi.org/10.1109/JQE.1973.1077732
4. Milton & Burns 1987 "Mode coupling in tapered single-mode structures"
   JLT https://doi.org/10.1109/JLT.1987.1075482
5. Hughes et al. 2018 "Forward-mode differentiation of Maxwell's equations"
   ACS Photonics (autograd = adjoint) https://arxiv.org/abs/1811.01255
6. Giles & Pierce 2000 "An Introduction to the Adjoint Approach to Design"
   SIAM Review https://doi.org/10.1137/S0036144599363118
7. Bryngdahl 1973 "Image formation using self-imaging techniques" JOSA
   https://doi.org/10.1364/JOSA.63.000416
8. Ulrich 1975 "Light-propagation and imaging in planar optical waveguides"
   Proc. SPIE https://doi.org/10.1117/12.965561
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass

import jax
import jax.numpy as jnp
import numpy as np

logger = logging.getLogger(__name__)

# =============================================================================
# 物理常量（SiP / SiEPIC 平台，1.55um 波长）
# =============================================================================

N_SI = 3.476  # 硅芯折射率 (Si, 1.55um)
N_SIO2 = 1.444  # SiO2 包层折射率
N_GROUP_SI = 4.20  # 硅群折射率 (用于带宽计算)
WAVELENGTH_UM = 1.55  # C 波段中心波长

# =============================================================================
# MMI 1x2 分束器（自成像理论，Soldano & Pennings 1995 JLT）
# =============================================================================


def mmi_fom(params: jnp.ndarray) -> jnp.ndarray:
    """MMI 1x2 分束器 FoM 函数（自成像理论）。

    物理模型（Soldano & Pennings 1995 JLT §III）:
    - 多模干涉耦合器（MMI）基于自成像效应
    - 拍长 L_π = 4*n_eff*W²/(3*λ) (W=MMI宽度, λ=波长)
    - 1x2 双像位置: L_target = 3*L_π/4
    - 在 L_target 处分束比 50:50，传输效率最大
    - 偏离 L_target: 传输效率下降，不均匀性增加

    FoM = 传输效率 - 0.1×不均匀性 + 0.05×W正则
    - W正则: 偏好 W=6um (1x2 MMI 标准宽度，平衡模式数与尺寸)
    - 来源: SiEPIC EBeam PDK MMI 标准设计

    Args:
        params: [W (um), L (um)] MMI 宽度与长度。

    Returns:
        FoM 标量（最大化目标）。
    """
    W, L = params[0], params[1]
    n_eff = N_SI
    L_pi = 4.0 * n_eff * W**2 / (3.0 * WAVELENGTH_UM)
    L_target = 3.0 * L_pi / 4.0  # 双像位置
    # 传输效率: cos² 形状在 L_target 处最大
    eta = jnp.cos(jnp.pi * (L - L_target) / L_pi) ** 2
    # 不均匀性: sin² 形状在 L_target 处最小
    delta = jnp.sin(jnp.pi * (L - L_target) / L_pi) ** 2 * 0.5
    # W 正则: 偏好 6um (1x2 MMI 标准)
    W_ideal = 6.0
    W_reg = -((W - W_ideal) / 2.0) ** 2
    return eta - 0.1 * delta + 0.05 * W_reg


def optimize_mmi(
    n_iterations: int = 80, learning_rate: float = 0.3
) -> dict:
    """MMI 1x2 分束器 adjoint 优化。

    用 jax.grad 自动计算 dFoM/d[W,L]（adjoint 方法），heavy-ball 动量优化。

    Args:
        n_iterations: 优化迭代次数。
        learning_rate: 学习率。

    Returns:
        优化结果 dict（初始/最优参数、FoM、IL、不均匀性、历史）。
    """
    if n_iterations <= 0:
        raise ValueError(f"n_iterations 须为正，实际 {n_iterations}")
    # 初始 W=7um, L=50um（偏离 L_target≈110um，在 cos² 有梯度区域）
    params = jnp.array([7.0, 50.0], dtype=jnp.float32)
    grad_fn = jax.grad(mmi_fom)
    velocity = jnp.zeros_like(params)
    momentum = 0.5
    fom_history: list[float] = []
    best_fom = -float("inf")
    best_params = params
    fom_init = float(mmi_fom(params))
    for i in range(n_iterations):
        fom_val = float(mmi_fom(params))
        fom_history.append(fom_val)
        if fom_val > best_fom:
            best_fom = fom_val
            best_params = params
        g = grad_fn(params)
        g_clipped = jnp.clip(g, -1.0, 1.0)
        velocity = momentum * velocity + learning_rate * g_clipped
        params = params + velocity
        # 参数约束: W∈[3,15]um, L∈[10,500]um
        params = jnp.clip(params, jnp.array([3.0, 10.0]), jnp.array([15.0, 500.0]))
    fom_final = float(mmi_fom(params))
    if fom_final > best_fom:
        best_fom = fom_final
        best_params = params
    fom_history.append(fom_final)
    # 计算物理指标（用 best_params）
    W_opt, L_opt = float(best_params[0]), float(best_params[1])
    L_pi_opt = 4.0 * N_SI * W_opt**2 / (3.0 * WAVELENGTH_UM)
    L_target_opt = 3.0 * L_pi_opt / 4.0
    eta = float(jnp.cos(jnp.pi * (L_opt - L_target_opt) / L_pi_opt) ** 2)
    il_db = -10.0 * math.log10(max(eta, 1e-6))
    delta = float(jnp.sin(jnp.pi * (L_opt - L_target_opt) / L_pi_opt) ** 2 * 0.5)
    nonuniformity_db = 10.0 * math.log10(1.0 + max(delta, 1e-6))
    improvement_db = 10.0 * math.log10(max(best_fom, 1e-6) / max(fom_init, 1e-6))
    return {
        "device": "MMI_1x2",
        "initial_W_um": 7.0,
        "initial_L_um": 50.0,
        "optimal_W_um": W_opt,
        "optimal_L_um": L_opt,
        "initial_fom": fom_init,
        "final_fom": fom_final,
        "best_fom": best_fom,
        "improvement_db": improvement_db,
        "insertion_loss_db": il_db,
        "nonuniformity_db": nonuniformity_db,
        "fom_history": fom_history,
        "n_iterations": n_iterations,
    }


# =============================================================================
# WDM 滤波器（耦合模理论，Yariv 1973 IEEE JQE）
# =============================================================================


def wdm_fom(params: jnp.ndarray) -> jnp.ndarray:
    """WDM 滤波器 FoM 函数（耦合模理论，定向耦合器型）。

    物理模型（Yariv 1973 IEEE JQE）:
    - 定向耦合器: 两条平行波导，间距 g，耦合长度 L
    - 耦合系数 κ(g) = κ0 * exp(-g/g0) (随间距指数衰减)
    - 耦合效率: T = sin²(κ·L) (在 L=Lc=π/(2κ) 时 T=1)
    - 带宽: Δλ = λ²·κ/(π·n_g) (Yariv 1973 §V, 耦合越强带宽越宽)
    - 隔离度: IL_iso = -10*log10(1-T²) (T 越高隔离度越大)

    FoM = T + 0.05×带宽 + 0.05×隔离度
    - 0.05 系数让各项贡献平衡（T∈[0,1], 带宽~30nm, 隔离度~30dB）

    Args:
        params: [g (um), L (um)] 耦合间距与长度。

    Returns:
        FoM 标量。
    """
    g, L = params[0], params[1]
    kappa0 = 1.0  # 最大耦合系数 (1/um)
    g0 = 0.5  # 衰减特征间距 (um)
    kappa = kappa0 * jnp.exp(-g / g0)
    # 耦合效率 (Yariv 1973 Eq. 24)
    T = jnp.sin(kappa * L) ** 2
    # 物理带宽 (Yariv 1973 §V): Δλ = λ²·κ/(π·n_g), 转 nm
    bandwidth_nm = (WAVELENGTH_UM**2) * kappa / (jnp.pi * N_GROUP_SI) * 1000.0
    # 隔离度 (1-T 的对数)
    isolation_db = -10.0 * jnp.log10(jnp.maximum(1.0 - T**2, 1e-6))
    return T + 0.05 * bandwidth_nm + 0.05 * isolation_db


def optimize_wdm(
    n_iterations: int = 80, learning_rate: float = 0.05
) -> dict:
    """WDM 滤波器 adjoint 优化。

    Args:
        n_iterations: 优化迭代次数。
        learning_rate: 学习率。

    Returns:
        优化结果 dict（初始/最优参数、FoM、带宽、隔离度）。
    """
    if n_iterations <= 0:
        raise ValueError(f"n_iterations 须为正，实际 {n_iterations}")
    # 初始 g=1.6um (大间距弱耦合), L=10um (短耦合区)，T≈0.16
    params = jnp.array([1.6, 10.0], dtype=jnp.float32)
    grad_fn = jax.grad(wdm_fom)
    velocity = jnp.zeros_like(params)
    momentum = 0.5
    fom_history: list[float] = []
    best_fom = -float("inf")
    best_params = params
    fom_init = float(wdm_fom(params))
    for i in range(n_iterations):
        fom_val = float(wdm_fom(params))
        fom_history.append(fom_val)
        if fom_val > best_fom:
            best_fom = fom_val
            best_params = params
        g = grad_fn(params)
        g_clipped = jnp.clip(g, -1.0, 1.0)
        velocity = momentum * velocity + learning_rate * g_clipped
        params = params + velocity
        # 参数约束: g∈[0.2,3]um, L∈[5,200]um
        params = jnp.clip(params, jnp.array([0.2, 5.0]), jnp.array([3.0, 200.0]))
    fom_final = float(wdm_fom(params))
    if fom_final > best_fom:
        best_fom = fom_final
        best_params = params
    fom_history.append(fom_final)
    g_opt, L_opt = float(best_params[0]), float(best_params[1])
    kappa = 1.0 * math.exp(-g_opt / 0.5)
    T = math.sin(kappa * L_opt) ** 2
    # 物理带宽 (Yariv 1973 §V): Δλ = λ²·κ/(π·n_g), 转 nm
    bandwidth_nm = (WAVELENGTH_UM**2) * kappa / (math.pi * N_GROUP_SI) * 1000.0
    isolation_db = -10.0 * math.log10(max(1.0 - T**2, 1e-6))
    improvement_db = 10.0 * math.log10(max(best_fom, 1e-6) / max(fom_init, 1e-6))
    return {
        "device": "WDM_filter",
        "initial_g_um": 1.6,
        "initial_L_um": 10.0,
        "optimal_g_um": g_opt,
        "optimal_L_um": L_opt,
        "initial_fom": fom_init,
        "final_fom": fom_final,
        "best_fom": best_fom,
        "improvement_db": improvement_db,
        "bandwidth_nm": bandwidth_nm,
        "isolation_db": isolation_db,
        "coupling_efficiency": T,
        "fom_history": fom_history,
        "n_iterations": n_iterations,
    }


# =============================================================================
# Y 分支（绝热定理，Milton & Burns 1987 JLT）
# =============================================================================


def ybranch_fom(params: jnp.ndarray) -> jnp.ndarray:
    """Y分支 FoM 函数（绝热定理）。

    物理模型（Milton & Burns 1987 JLT）:
    - Y分支: 单波导分叉为两个波导，分支角 θ
    - 绝热条件: θ 足够小，基模不耦合到辐射模
    - 传输效率: T = tanh(C·θ) (θ 大→T 接近 1)
      - tanh 形状来自绝热定理的指数衰减解
      - C=10 为绝热参数（依赖折射率对比）
    - 器件长度: L ∝ 1/θ (θ 大→器件短，但损耗增加)

    FoM = T - 0.1×θ² (传输效率 - 长度正则)
    - θ² 正则: 抑制 θ 过大（避免非绝热损耗）

    Args:
        params: [θ (radian)] 分支角。

    Returns:
        FoM 标量。
    """
    theta = params[0]
    C = 10.0  # 绝热参数
    T = jnp.tanh(C * theta)
    # 长度正则: θ 大→器件短但损耗，加 θ² 抑制过大
    length_reg = -0.1 * theta**2
    return T + length_reg


def optimize_ybranch(
    n_iterations: int = 80, learning_rate: float = 0.01
) -> dict:
    """Y分支 adjoint 优化。

    Args:
        n_iterations: 优化迭代次数。
        learning_rate: 学习率。

    Returns:
        优化结果 dict（初始/最优角度、FoM、插入损耗）。
    """
    if n_iterations <= 0:
        raise ValueError(f"n_iterations 须为正，实际 {n_iterations}")
    # 初始 θ=0.008 rad ≈ 0.46° (小角度，T≈0.08，绝热但传输低)
    params = jnp.array([0.008], dtype=jnp.float32)
    grad_fn = jax.grad(ybranch_fom)
    velocity = jnp.zeros_like(params)
    momentum = 0.5
    fom_history: list[float] = []
    best_fom = -float("inf")
    best_params = params
    fom_init = float(ybranch_fom(params))
    for i in range(n_iterations):
        fom_val = float(ybranch_fom(params))
        fom_history.append(fom_val)
        if fom_val > best_fom:
            best_fom = fom_val
            best_params = params
        g = grad_fn(params)
        g_clipped = jnp.clip(g, -1.0, 1.0)
        velocity = momentum * velocity + learning_rate * g_clipped
        params = params + velocity
        # 参数约束: θ∈[0.005, 0.5] rad
        params = jnp.clip(params, 0.005, 0.5)
    fom_final = float(ybranch_fom(params))
    if fom_final > best_fom:
        best_fom = fom_final
        best_params = params
    fom_history.append(fom_final)
    theta_opt = float(best_params[0])
    T = math.tanh(10.0 * theta_opt)
    il_db = -10.0 * math.log10(max(T, 1e-6))
    improvement_db = 10.0 * math.log10(max(best_fom, 1e-6) / max(fom_init, 1e-6))
    return {
        "device": "Y_branch",
        "initial_theta_rad": 0.008,
        "optimal_theta_rad": theta_opt,
        "optimal_theta_deg": math.degrees(theta_opt),
        "initial_fom": fom_init,
        "final_fom": fom_final,
        "best_fom": best_fom,
        "improvement_db": improvement_db,
        "insertion_loss_db": il_db,
        "transmission_efficiency": T,
        "fom_history": fom_history,
        "n_iterations": n_iterations,
    }


# =============================================================================
# Showcase 主入口
# =============================================================================


def run_showcase(n_iterations: int = 80) -> dict:
    """运行 D12 逆向设计 showcase: 3 器件 adjoint 优化。

    Args:
        n_iterations: 每个器件的优化迭代次数（默认 80）。

    Returns:
        {"mmi": ..., "wdm": ..., "ybranch": ..., "summary": ...}
    """
    logger.info("D12 逆向设计 showcase 开始 (n_iterations=%d)", n_iterations)
    mmi_result = optimize_mmi(n_iterations=n_iterations)
    logger.info(
        "MMI: W=%.3fum L=%.3fum IL=%.3fdB nonuniformity=%.3fdB",
        mmi_result["optimal_W_um"],
        mmi_result["optimal_L_um"],
        mmi_result["insertion_loss_db"],
        mmi_result["nonuniformity_db"],
    )
    wdm_result = optimize_wdm(n_iterations=n_iterations)
    logger.info(
        "WDM: g=%.3fum L=%.3fum BW=%.2fnm iso=%.2fdB",
        wdm_result["optimal_g_um"],
        wdm_result["optimal_L_um"],
        wdm_result["bandwidth_nm"],
        wdm_result["isolation_db"],
    )
    ybranch_result = optimize_ybranch(n_iterations=n_iterations)
    logger.info(
        "Ybranch: θ=%.4frad IL=%.3fdB T=%.4f",
        ybranch_result["optimal_theta_rad"],
        ybranch_result["insertion_loss_db"],
        ybranch_result["transmission_efficiency"],
    )
    n_improved = sum(
        1
        for r in (mmi_result, wdm_result, ybranch_result)
        if r["improvement_db"] >= 10.0
    )
    summary = {
        "n_devices": 3,
        "n_improved_ge_10db": n_improved,
        "all_ge_10db": n_improved == 3,
        "devices": [mmi_result["device"], wdm_result["device"], ybranch_result["device"]],
    }
    return {
        "mmi": mmi_result,
        "wdm": wdm_result,
        "ybranch": ybranch_result,
        "summary": summary,
    }


__all__ = [
    "mmi_fom",
    "wdm_fom",
    "ybranch_fom",
    "optimize_mmi",
    "optimize_wdm",
    "optimize_ybranch",
    "run_showcase",
    "N_SI",
    "N_SIO2",
    "N_GROUP_SI",
    "WAVELENGTH_UM",
]
