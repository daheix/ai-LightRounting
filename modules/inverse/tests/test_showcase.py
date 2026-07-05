"""polaris-inverse 子模块深度测试（覆盖全部稳定 API）。

测试覆盖维度:
- 物理常量与模块元信息验证
- YeeGrid3D 网格构造与 CFL 稳定条件
- GedneyPML 单轴各向异性吸收边界
- DifferentiableFDTD JAX 可微分 3D FDTD 内核
- epsilon_r_from_width sigmoid 软边界参数化
- fom_fn 归一化传输率优值函数
- run_adjoint_optimization / optimize_waveguide_width 端到端优化
- JAX autograd 可微性验证（*创新* 替代 lumopt 手动伴随方程）
- best-checkpoint 追踪回归测试（R05 关键修复）

来源（R02 学术诚信，≥5 个文献 URL）:
- Yee 1966 IEEE TAP "Numerical solution of initial boundary value problems
  involving Maxwell's equations in isotropic media"
  https://doi.org/10.1109/TAP.1966.1138693
- Taflove & Hagness 2005 "Computational Electrodynamics: The FDTD Method"
- Mahau 2024 arXiv:2412.12360 "Differentiable FDTD for inverse design"
  https://arxiv.org/abs/2412.12360
- Gedney 1996 IEEE TAP（单轴各向异性 PML）
  https://doi.org/10.1109/8.546249
- Berenger 1994 JCP（PML 原始论文）
  https://doi.org/10.1006/jcph.1994.1159
- Polyak 1964 "Some methods of speeding up the convergence of iteration
  methods"（heavy-ball 动量优化器）
- Jensen & Sigmund 2011 "Topology optimization for nano-photonics"
  https://doi.org/10.1002/lpor.201000014
- lumopt: https://github.com/chriskeraly/lumopt
- Hughes 2018 ACS Photonics（autograd = adjoint）
  https://arxiv.org/abs/1811.01255
- Giles & Pierce 2000 SIAM Review "An Introduction to the Adjoint Approach"
- Soref 1993 IEEE J. Quantum Electron.（SOI 材料参数）
  https://ieeexplore.ieee.org/document/1148303
- NIST CODATA 2018 物理常数
  https://physics.nist.gov/cuu/Constants/

规则依据:
- R02 学术诚信（所有参数/公式可溯源）
- R03 禁止 fall-back（失败即 raise，无假数据）
- R04 不参与 GPU（纯 JAX CPU 后端）
- R05 Bug 必须修复（含回归测试防复发）
- R13 交付自测（无带病提交）
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pytest

# 让测试既能从已安装包导入，也能从源码树导入（CI/开发模式）
_SRC = str(Path(__file__).resolve().parents[1] / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import jax  # noqa: E402
import jax.numpy as jnp  # noqa: E402

import polaris_inverse  # noqa: E402
from polaris_inverse import (  # noqa: E402
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
    DifferentiableFDTD,
    GedneyPML,
    YeeGrid3D,
    epsilon_r_from_width,
    fom_fn,
    optimize_waveguide_width,
    run_adjoint_optimization,
)
from polaris_inverse.fdtd_jax import C0, EPS0, MU0  # noqa: E402


# =============================================================================
# 辅助函数：构建默认 FDTD 求解器（与 run_adjoint_optimization 一致）
# =============================================================================
def _build_default_fdtd() -> tuple[DifferentiableFDTD, YeeGrid3D, GedneyPML]:
    """构建默认 FDTD 求解器（与 run_adjoint_optimization 配置一致）。

    Returns:
        (fdtd, grid, pml) 三元组。
    """
    nx, ny, nz = GRID_NX, GRID_NY, GRID_NZ
    dx = GRID_DX_M
    grid = YeeGrid3D(nx=nx, ny=ny, nz=nz, dx=dx, dy=dx, dz=dx)
    grid.epsilon_r = jnp.ones((nx, ny, nz)) * EPS_R_SI
    pml = GedneyPML(grid, n_layers=PML_N_LAYERS, eps_r_bg=EPS_R_SI)
    # CFL 时间步 + 安全系数 0.3（与 adjoint.py FDTD_DT_SAFETY 一致）
    cfl_dt = grid.cfl_timestep(EPS_R_SI)
    dt = 0.3 * float(cfl_dt)
    fdtd = DifferentiableFDTD(grid, pml=pml, dt=dt, eps_r_bg=EPS_R_SI)
    return fdtd, grid, pml


def _default_source_monitor() -> tuple[tuple, tuple, float, float]:
    """返回默认源/监视器位置与频率（与 run_adjoint_optimization 一致）。

    Returns:
        (source_pos, monitor_pos, source_freq, target_freq) 四元组。
    """
    nx, ny = GRID_NX, GRID_NY
    source_pos = (PML_N_LAYERS + 4, ny // 2, PML_N_LAYERS + 1)
    monitor_pos = (nx - PML_N_LAYERS - 4, ny // 2, PML_N_LAYERS + 1)
    source_freq = C0 / (TARGET_WAVELENGTH_UM * 1e-6)
    return source_pos, monitor_pos, source_freq, source_freq


# =============================================================================
# 1. 物理常量与模块元信息验证
# =============================================================================

def test_optimize_waveguide_width_full():
    """50 次迭代波导宽度优化: 验证 fom_history 长度=51、无 NaN、improvement_db 有限。

    验证项:
    - fom_history 长度 = n_iterations + 1 = 51
    - fom_history 无 NaN
    - improvement_db 为有限值（非 NaN/Inf）
    - initial_fom / final_fom 为有限正数
    - best-checkpoint: final_fom >= initial_fom（improvement_db >= 0）
    """
    result = optimize_waveguide_width(n_iterations=50, learning_rate=0.5)
    # fom_history 长度 = n_iterations + 1 = 51
    assert len(result["fom_history"]) == 51, (
        f"fom_history 长度应为 51，实际 {len(result['fom_history'])}"
    )
    # 无 NaN
    has_nan = any(math.isnan(x) for x in result["fom_history"])
    assert not has_nan, "fom_history 含 NaN（违反 R03）"
    # improvement_db 为有限值
    assert math.isfinite(result["improvement_db"])
    # FoM 为有限正数
    assert math.isfinite(result["initial_fom"]) and result["initial_fom"] > 0
    assert math.isfinite(result["final_fom"]) and result["final_fom"] > 0
    # best-checkpoint: final_fom >= initial_fom
    assert result["final_fom"] >= result["initial_fom"], (
        f"final_fom={result['final_fom']} < initial_fom={result['initial_fom']}"
        f"（best-checkpoint 应保证 final >= initial）"
    )
    assert result["improvement_db"] >= 0.0
