"""PoLaRIS Adjoint 逆向设计子模块（polaris-inverse）。

提供稳定 Python API（optimize_waveguide_width），基于 JAX 可微 FDTD + jax.grad
自动微分优化波导宽度，对标 Lumerical lumopt 手动伴随方程逆向设计。

## 核心创新（*创新*）

- 用 JAX ``jax.grad`` 自动微分计算 FoM 对波导宽度参数的梯度，
  替代 lumopt 手动推导伴随方程（adjoint equation）。
  - 底层逻辑: 反向模式自动微分（reverse-mode AD）= 伴随方法（Giles & Pierce
    2000 SIAM Review 数学等价），梯度计算开销与参数数无关（链式法则 + 一次反向）。
  - 支持理论: Mahau 2024 arXiv:2412.12360 验证了 JAX 可微 FDTD 可行性；
    Hughes 2018 ACS Photonics 证明 autograd = adjoint。
  - 案例: 硅波导宽度逆向设计，本子模块实现。
- heavy-ball 动量优化器（Polyak 1964），抑制梯度符号交替震荡；
  梯度裁剪 [-1,1] 防 NaN 爆炸。

## 设计原则

- 对外 API 返回 JSON-serializable dict（与 polaris-core / polaris-place 等一致）
- 纯 JAX(CPU) 实现（R04: 不参与 GPU；R03: 禁止 fall-back，JAX 不可用 raise）
- 不修改 src/polaris/ 原代码；本子模块独立迁移 fdtd_jax_backend 核心内核

## 来源（R02 学术诚信，≥5 个文献 URL）

- Yee 1966 IEEE TAP "Numerical solution of initial boundary value problems
  involving Maxwell's equations in isotropic media"
  https://doi.org/10.1109/TAP.1966.1138693
- Taflove & Hagness 2005 "Computational Electrodynamics: The FDTD Method"
- Mahau 2024 arXiv:2412.12360 "Differentiable FDTD for inverse design"
  https://arxiv.org/abs/2412.12360
- Polyak 1964 "Some methods of speeding up the convergence of iteration methods"
- Jensen & Sigmund 2011 "Topology optimization for nano-photonics"
  https://doi.org/10.1002/lpor.201000014
- lumopt: https://github.com/chriskeraly/lumopt
- Gedney 1996 IEEE TAP（单轴各向异性 PML）https://doi.org/10.1109/8.546249
- Hughes 2018 ACS Photonics（autograd = adjoint）https://arxiv.org/abs/1811.01255
- Giles & Pierce 2000 SIAM Review "An Introduction to the Adjoint Approach"
"""

from __future__ import annotations

from polaris_inverse.adjoint import (
    EPS_R_SI,
    EPS_R_SIO2,
    GRID_DX_M,
    GRID_NX,
    GRID_NY,
    GRID_NZ,
    INITIAL_WIDTH_PIXELS,
    LEARNING_RATE,
    MOMENTUM,
    N_ITERATIONS,
    PML_N_LAYERS,
    TARGET_WAVELENGTH_UM,
    epsilon_r_from_width,
    fom_fn,
    run_adjoint_optimization,
)
from polaris_inverse.fdtd_jax import DifferentiableFDTD, GedneyPML, YeeGrid3D
from polaris_inverse.showcase import (
    N_GROUP_SI,
    N_SI,
    N_SIO2,
    WAVELENGTH_UM,
    mmi_fom,
    optimize_mmi,
    optimize_wdm,
    optimize_ybranch,
    run_showcase,
    wdm_fom,
    ybranch_fom,
)

__version__ = "5.0.0"


def optimize_waveguide_width(
    n_iterations: int = 50, learning_rate: float = 0.5
) -> dict:
    """Adjoint 逆向设计：JAX jax.grad 自动微分优化波导宽度。

    使用 JAX 可微分 FDTD 计算波导传输场，用 ``jax.grad`` 自动计算 FoM 对
    波导宽度参数的梯度（*创新*，替代 lumopt 手动伴随方程），heavy-ball
    动量优化器（Polyak 1964）+ 梯度裁剪防 NaN。

    优化目标: 最大化监视器时域信号峰值（正比于目标波长透过率，Taflove 2005 §13.2）。
    网格 24×12×8, dx=200nm，真实 Si 芯(eps_si=12.08) + SiO₂ 包层(eps_bg=2.085)。

    Args:
        n_iterations: 优化迭代次数（默认 50）。lumopt 商业工具通常 50-200 次迭代，
            50 次为可收敛的最小值（来源: Jensen & Sigmund 2011 §3）。
        learning_rate: 学习率（默认 0.5）。配合动量 0.9，每步宽度变化 ≤0.5 像素，
            可在 [0.5, ny/2-1] 范围内细粒度搜索，避免边界震荡。

    Returns:
        优化结果 dict::

            {
                "initial_width_nm": float,    # 初始波导半宽度 (nm)
                "optimal_width_nm": float,    # 优化后波导半宽度 (nm)
                "initial_fom": float,         # 初始 FoM
                "final_fom": float,           # 最终 FoM
                "improvement_db": float,      # FoM 改善量 (dB)
                "fom_history": list[float],   # FoM 历史（长度 n_iterations+1）
                "converged": bool,            # 是否收敛（最后 3 步变化 <1%）
                "iterations": int,            # 实际迭代次数
            }

    Raises:
        RuntimeError: JAX 不可用或优化过程出现 NaN（R03 禁止 fall-back，失败即 raise）。
        ValueError: n_iterations/learning_rate 参数非法。
    """
    return run_adjoint_optimization(
        n_iterations=n_iterations, learning_rate=learning_rate
    )


__all__ = [
    "optimize_waveguide_width",
    "DifferentiableFDTD",
    "GedneyPML",
    "YeeGrid3D",
    "epsilon_r_from_width",
    "fom_fn",
    "run_adjoint_optimization",
    "EPS_R_SI",
    "EPS_R_SIO2",
    "GRID_NX",
    "GRID_NY",
    "GRID_NZ",
    "GRID_DX_M",
    "PML_N_LAYERS",
    "N_ITERATIONS",
    "LEARNING_RATE",
    "MOMENTUM",
    "INITIAL_WIDTH_PIXELS",
    "TARGET_WAVELENGTH_UM",
    # D12 showcase (R36)
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
    "__version__",
]
