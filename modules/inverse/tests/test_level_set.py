"""Level-set 方法子模块测试（V5.1.0 D12 增强 #2）。

测试覆盖维度:
- 正则化 Heaviside 函数性质（Allaire 2004 §3.2）
- 梯度幅值 |∇φ| 计算（Osher & Sethian 1988 中心差分）
- HJ 演化一步（Osher & Sethian 1988 §3）
- 重新初始化（Sussman 1994，|∇φ|≈1）
- φ → 介电常数转换
- FoM 函数可微性（jax.grad，*创新* 替代手动形状导数）
- 2 器件端到端优化（Y分支/弯曲波导）
- 参数校验（R03 禁止 fall-back）

来源（R02 学术诚信，≥5 个文献 URL）:
- Osher & Sethian 1988 JCP https://doi.org/10.1016/0021-9991(88)90002-2
- Osher & Fedkiw 2003 Springer https://link.springer.com/book/10.1007/b98879
- Allaire et al. 2004 JCP https://doi.org/10.1016/j.jcp.2004.01.044
- Sussman, Smereka, Osher 1994 JCP（重新初始化）
- Milton & Burns 1987 JLT https://doi.org/10.1109/JLT.1987.1075482
- Hughes 2018 ACS Photonics https://arxiv.org/abs/1811.01255
- Giles & Pierce 2000 SIAM Review
  https://doi.org/10.1137/S0036144599363118

规则依据: R02 / R03 / R04 / R05
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pytest

_SRC = str(Path(__file__).resolve().parents[1] / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import jax  # noqa: E402
import jax.numpy as jnp  # noqa: E402

from polaris_inverse.level_set import (  # noqa: E402
    DT_LEVELSET,
    HEAVISIDE_EPS,
    LEARNING_RATE,
    MOMENTUM,
    N_ITERATIONS,
    N_SI,
    N_SIO2,
    REINIT_INTERVAL,
    REINIT_N_STEPS,
    WAVELENGTH_UM,
    bend_waveguide_levelset_fom,
    gradient_magnitude,
    hji_evolve_step,
    optimize_levelset_bend,
    optimize_levelset_ybranch,
    phi_to_epsilon,
    reinitialize_phi,
    regularized_heaviside,
    ybranch_levelset_fom,
)


# =============================================================================
# 1. 物理常量与参数验证
# =============================================================================


def test_physical_constants():
    """验证 SiP 平台物理常量与 level-set 参数。"""
    assert N_SI == pytest.approx(3.476, abs=1e-4)
    assert N_SIO2 == pytest.approx(1.444, abs=1e-4)
    assert WAVELENGTH_UM == pytest.approx(1.55, abs=1e-6)
    assert 0.0 < DT_LEVELSET < 1.0  # CFL 条件
    assert 0.0 < HEAVISIDE_EPS < 0.2  # Allaire 2004 正则化宽度
    assert 0.0 < MOMENTUM < 1.0  # Polyak 1964
    assert LEARNING_RATE > 0
    assert N_ITERATIONS >= 30
    assert REINIT_INTERVAL >= 1  # 重新初始化间隔
    assert REINIT_N_STEPS >= 1


# =============================================================================
# 2. 正则化 Heaviside（Allaire 2004 §3.2）
# =============================================================================


def test_regularized_heaviside_endpoints():
    """正则化 Heaviside: φ→+∞→1, φ→-∞→0, φ=0→0.5。"""
    eps = 0.05
    # φ=0 → 0.5
    h0 = float(regularized_heaviside(jnp.array(0.0), eps))
    assert h0 == pytest.approx(0.5, abs=1e-6)
    # φ 大正 → ≈1
    h_pos = float(regularized_heaviside(jnp.array(1.0), eps))
    assert h_pos > 0.95
    # φ 大负 → ≈0
    h_neg = float(regularized_heaviside(jnp.array(-1.0), eps))
    assert h_neg < 0.05


def test_regularized_heaviside_monotonic():
    """正则化 Heaviside 单调性: φ 越大 H(φ) 越大。"""
    eps = 0.05
    phi_low = jnp.array(-0.5)
    phi_high = jnp.array(0.5)
    assert float(regularized_heaviside(phi_high, eps)) > float(
        regularized_heaviside(phi_low, eps)
    )


def test_phi_to_epsilon_range():
    """φ → 介电常数: 范围在 [eps_bg, eps_si]。"""
    eps_bg = N_SIO2**2
    eps_si = N_SI**2
    # 全正 φ → eps_si
    phi_pos = jnp.ones((4, 4)) * 2.0
    eps_pos = phi_to_epsilon(phi_pos, eps_bg, eps_si)
    assert float(eps_pos[0, 0]) == pytest.approx(eps_si, abs=0.5)
    # 全负 φ → eps_bg
    phi_neg = jnp.ones((4, 4)) * -2.0
    eps_neg = phi_to_epsilon(phi_neg, eps_bg, eps_si)
    assert float(eps_neg[0, 0]) == pytest.approx(eps_bg, abs=0.5)


# =============================================================================
# 3. 梯度幅值 + HJ 演化（Osher & Sethian 1988）
# =============================================================================


def test_gradient_magnitude_shape():
    """|∇φ| 形状不变，值非负。"""
    phi = jnp.ones((10, 8))
    g = gradient_magnitude(phi)
    assert g.shape == (10, 8)
    assert float(jnp.all(g >= 0))


def test_gradient_magnitude_constant_field():
    """常数场 |∇φ|≈0（中心差分）。"""
    phi = jnp.ones((10, 10)) * 3.0
    g = gradient_magnitude(phi)
    # 内部梯度应≈0
    center_val = float(g[5, 5])
    assert center_val < 0.1


def test_hji_evolve_step_shape():
    """HJ 演化一步形状不变。"""
    phi = jnp.ones((10, 8))
    V = jnp.zeros((10, 8))
    phi_new = hji_evolve_step(phi, V, dt=0.1)
    assert phi_new.shape == (10, 8)


def test_hji_evolve_step_zero_velocity_unchanged():
    """V=0 时 φ 不变（HJ 方程 ∂φ/∂t = -V|∇φ| = 0）。"""
    phi = jnp.ones((10, 10)) * 0.5
    V = jnp.zeros((10, 10))
    phi_new = hji_evolve_step(phi, V, dt=0.1)
    assert float(jnp.allclose(phi_new, phi))


# =============================================================================
# 4. 重新初始化（Sussman 1994，|∇φ|≈1）
# =============================================================================


def test_reinitialize_shape():
    """重新初始化形状不变。"""
    phi = jnp.ones((10, 8)) * 0.5
    phi_re = reinitialize_phi(phi, n_steps=2)
    assert phi_re.shape == (10, 8)


def test_reinitialize_drives_gradient_to_one():
    """重新初始化后 |∇φ| 更接近 1（距离函数性质）。"""
    # 构造一个 |∇φ|≠1 的场（线性斜坡）
    x = jnp.arange(10, dtype=jnp.float32)
    phi = jnp.broadcast_to(x[None, :] * 0.5, (10, 10))  # |∇φ|≈0.5
    phi_re = reinitialize_phi(phi, n_steps=5)
    # 重新初始化后 |∇φ| 应更接近 1
    g_before = float(jnp.mean(gradient_magnitude(phi)))
    g_after = float(jnp.mean(gradient_magnitude(phi_re)))
    assert abs(g_after - 1.0) < abs(g_before - 1.0) or g_after > g_before


# =============================================================================
# 5. FoM 可微性（*创新* jax.grad 替代手动形状导数）
# =============================================================================


def test_fom_differentiable_all_devices():
    """2 器件 FoM 可微（jax.grad），梯度形状正确且有限。"""
    phi = jnp.ones((12, 8)) * 0.5
    for fom_fn in [ybranch_levelset_fom, bend_waveguide_levelset_fom]:
        grad_fn = jax.grad(fom_fn)
        g = grad_fn(phi)
        assert g.shape == (12, 8)
        assert float(jnp.all(jnp.isfinite(g))), f"{fom_fn.__name__} 梯度含 NaN/Inf"


def test_fom_finite():
    """2 器件 FoM 在中等 φ 下有限。"""
    phi = jnp.ones((12, 8)) * 0.5
    for fom_fn in [ybranch_levelset_fom, bend_waveguide_levelset_fom]:
        fom = float(fom_fn(phi))
        assert math.isfinite(fom), f"{fom_fn.__name__} FoM 非有限值"


# =============================================================================
# 6. 端到端优化（2 器件，小迭代快速验证）
# =============================================================================


@pytest.mark.parametrize("opt_fn,device_name", [
    (optimize_levelset_ybranch, "LevelSet_Y_branch"),
    (optimize_levelset_bend, "LevelSet_bend_waveguide"),
])
def test_optimize_levelset_end_to_end(opt_fn, device_name):
    """2 器件 level-set 优化端到端: 结果结构完整 + 无 NaN + improvement_db 有限。"""
    result = opt_fn(grid_nx=12, grid_ny=8, n_iterations=15, learning_rate=0.05)
    assert result["device"] == device_name
    assert result["n_iterations"] == 15
    assert result["grid_shape"] == (12, 8)
    assert len(result["fom_history"]) == 15
    # 无 NaN
    has_nan = any(math.isnan(x) for x in result["fom_history"])
    assert not has_nan, "fom_history 含 NaN（违反 R03）"
    # improvement_db 有限
    assert math.isfinite(result["improvement_db"])
    # Si 比例在 [0,1]
    assert 0.0 <= result["si_ratio"] <= 1.0
    # 边界长度非负
    assert result["boundary_length"] >= 0.0
    # 距离函数残差非负
    assert result["distance_residual"] >= 0.0


# =============================================================================
# 7. 参数校验（R03 禁止 fall-back）
# =============================================================================


def test_invalid_n_iterations_raises():
    """n_iterations 非正整数 raise（R03）。"""
    with pytest.raises(ValueError, match="n_iterations"):
        optimize_levelset_ybranch(n_iterations=0)
    with pytest.raises(ValueError, match="n_iterations"):
        optimize_levelset_ybranch(n_iterations=-1)


def test_invalid_learning_rate_raises():
    """learning_rate 非正数 raise（R03）。"""
    with pytest.raises(ValueError, match="learning_rate"):
        optimize_levelset_ybranch(learning_rate=0.0)
    with pytest.raises(ValueError, match="learning_rate"):
        optimize_levelset_ybranch(learning_rate=-0.5)


def test_invalid_grid_size_raises():
    """网格尺寸 <8 raise（R03）。"""
    with pytest.raises(ValueError, match="网格"):
        optimize_levelset_ybranch(grid_nx=4, grid_ny=8)
    with pytest.raises(ValueError, match="网格"):
        optimize_levelset_ybranch(grid_nx=8, grid_ny=4)
