"""拓扑优化子模块测试（V5.1.0 D12 增强 #1）。

测试覆盖维度:
- SIMP 密度插值物理正确性
- 灵敏度滤波（cone kernel 卷积）形状保持
- Heaviside 投影二值化特性
- FoM 函数可微性（jax.grad，*创新* 替代手动拓扑导数）
- 3 器件端到端优化（MMI 1x2/2x2/WDM）
- 参数校验（R03 禁止 fall-back）
- R05 回归: FoM 恒正（improvement_db 语义正确）

来源（R02 学术诚信，≥5 个文献 URL）:
- Bendsøe & Sigmund 2003 "Topology Optimization" Springer
  https://link.springer.com/book/10.1007/978-3-662-05086-6
- Jensen & Sigmund 2011 Laser Photonics Rev
  https://doi.org/10.1002/lpor.201000014
- Wang et al. 2011 Struct Multidisc Optim
  https://doi.org/10.1007/s00158-010-0564-1
- Lazarov & Sigmund 2011 Int J Numer Methods Eng
  https://doi.org/10.1002/nme.3072
- Piggott et al. 2015 Nature Photonics
  https://doi.org/10.1038/nphoton.2015.111
- Hughes 2018 ACS Photonics（autograd = adjoint）
  https://arxiv.org/abs/1811.01255
- Giles & Pierce 2000 SIAM Review
  https://doi.org/10.1137/S0036144599363118

规则依据: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R05 Bug 必修
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pytest

# 让测试既能从已安装包导入，也能从源码树导入
_SRC = str(Path(__file__).resolve().parents[1] / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import jax  # noqa: E402
import jax.numpy as jnp  # noqa: E402

from polaris_inverse.topology_opt import (  # noqa: E402
    FILTER_RADIUS_PX,
    LEARNING_RATE,
    MOMENTUM,
    N_ITERATIONS,
    N_SI,
    N_SIO2,
    PROJECTION_BETA,
    PROJECTION_ETA,
    SIMP_PENALTY_P,
    WAVELENGTH_UM,
    heaviside_projection,
    mmi_1x2_topology_fom,
    mmi_2x2_topology_fom,
    optimize_topology_mmi_1x2,
    optimize_topology_mmi_2x2,
    optimize_topology_wdm,
    sensitivity_filter,
    simp_interpolation,
    wdm_topology_fom,
)


# =============================================================================
# 1. 物理常量验证
# =============================================================================


def test_physical_constants():
    """验证 SiP 平台物理常量（Soref 1993 IEEE JQE）。"""
    assert N_SI == pytest.approx(3.476, abs=1e-4)
    assert N_SIO2 == pytest.approx(1.444, abs=1e-4)
    assert WAVELENGTH_UM == pytest.approx(1.55, abs=1e-6)
    assert SIMP_PENALTY_P == 3.0  # Bendsøe & Sigmund 2003 标准
    assert 0.0 < PROJECTION_ETA < 1.0  # Wang 2011 阈值
    assert PROJECTION_BETA > 0  # 投影锐度
    assert FILTER_RADIUS_PX > 0  # Lazarov & Sigmund 2011
    assert 0.0 < MOMENTUM < 1.0  # Polyak 1964 heavy-ball
    assert LEARNING_RATE > 0
    assert N_ITERATIONS >= 30


# =============================================================================
# 2. SIMP 密度插值（Bendsøe & Sigmund 2003 §1.3）
# =============================================================================


def test_simp_interpolation_endpoints():
    """SIMP 端点: ρ=0→eps_bg, ρ=1→eps_si。"""
    eps_bg = N_SIO2**2
    eps_si = N_SI**2
    # ρ=0 → eps_bg
    d0 = simp_interpolation(jnp.zeros((4, 4)), eps_bg, eps_si)
    assert float(jnp.allclose(d0, eps_bg))
    # ρ=1 → eps_si
    d1 = simp_interpolation(jnp.ones((4, 4)), eps_bg, eps_si)
    assert float(jnp.allclose(d1, eps_si))


def test_simp_interpolation_monotonic():
    """SIMP 单调性: ρ 越大 eps 越大（p>0）。"""
    eps_bg = N_SIO2**2
    eps_si = N_SI**2
    rho_low = jnp.ones((2, 2)) * 0.3
    rho_high = jnp.ones((2, 2)) * 0.7
    eps_low = float(simp_interpolation(rho_low, eps_bg, eps_si)[0, 0])
    eps_high = float(simp_interpolation(rho_high, eps_bg, eps_si)[0, 0])
    assert eps_high > eps_low


# =============================================================================
# 3. 灵敏度滤波（Lazarov & Sigmund 2011 cone kernel）
# =============================================================================


def test_sensitivity_filter_shape_preserved():
    """滤波后形状不变（R05 卷积维度修复回归）。"""
    g = jnp.ones((12, 8))
    filtered = sensitivity_filter(g, g, radius=1.5)
    assert filtered.shape == (12, 8)


def test_sensitivity_filter_uniform_unchanged():
    """均匀梯度滤波后应近似不变（cone 核归一化）。"""
    g = jnp.ones((10, 10))
    filtered = sensitivity_filter(g, g, radius=1.5)
    # 均匀场滤波后内部应≈1（边界略小，SAME padding 零填充）
    center_val = float(filtered[5, 5])
    assert center_val == pytest.approx(1.0, abs=0.2)


# =============================================================================
# 4. Heaviside 投影（Wang 2011 §2.2）
# =============================================================================


def test_heaviside_projection_endpoints():
    """投影端点: ρ=0→≈0, ρ=1→≈1, ρ=η→0.5。"""
    beta = 8.0  # 高锐度近似二值
    eta = 0.5
    # ρ=0
    p0 = float(heaviside_projection(jnp.array(0.0), beta, eta))
    assert p0 < 0.1
    # ρ=1
    p1 = float(heaviside_projection(jnp.array(1.0), beta, eta))
    assert p1 > 0.9
    # ρ=η=0.5 → 0.5
    p_half = float(heaviside_projection(jnp.array(0.5), beta, eta))
    assert p_half == pytest.approx(0.5, abs=0.05)


def test_heaviside_projection_monotonic():
    """投影单调性: ρ 越大投影值越大。"""
    beta = 4.0
    eta = 0.5
    rho_low = jnp.array(0.2)
    rho_high = jnp.array(0.8)
    p_low = float(heaviside_projection(rho_low, beta, eta))
    p_high = float(heaviside_projection(rho_high, beta, eta))
    assert p_high > p_low


# =============================================================================
# 5. FoM 可微性（*创新* jax.grad 替代手动拓扑导数）
# =============================================================================


def test_fom_differentiable_all_devices():
    """3 器件 FoM 可微（jax.grad 不报错），梯度形状正确。"""
    density = jnp.ones((12, 8)) * 0.5
    for fom_fn in [
        mmi_1x2_topology_fom,
        mmi_2x2_topology_fom,
        wdm_topology_fom,
    ]:
        grad_fn = jax.grad(fom_fn)
        g = grad_fn(density)
        assert g.shape == (12, 8)
        assert float(jnp.all(jnp.isfinite(g))), f"{fom_fn.__name__} 梯度含 NaN/Inf"


def test_fom_positive():
    """R05 回归: 3 器件 FoM 在均匀密度 0.5 下恒正（improvement_db 语义正确）。"""
    density = jnp.ones((12, 8)) * 0.5
    for fom_fn in [
        mmi_1x2_topology_fom,
        mmi_2x2_topology_fom,
        wdm_topology_fom,
    ]:
        fom = float(fom_fn(density))
        assert fom > 0, f"{fom_fn.__name__} FoM={fom} 应为正（R05 修复）"


# =============================================================================
# 6. 端到端优化（3 器件，小迭代快速验证）
# =============================================================================


@pytest.mark.parametrize("opt_fn,device_name", [
    (optimize_topology_mmi_1x2, "Topology_MMI_1x2"),
    (optimize_topology_mmi_2x2, "Topology_MMI_2x2"),
    (optimize_topology_wdm, "Topology_WDM"),
])
def test_optimize_topology_end_to_end(opt_fn, device_name):
    """3 器件拓扑优化端到端: 结果结构完整 + 无 NaN + improvement_db 有限。"""
    result = opt_fn(grid_nx=12, grid_ny=8, n_iterations=15, learning_rate=0.1)
    # 结果结构
    assert result["device"] == device_name
    assert result["n_iterations"] == 15
    assert result["grid_shape"] == (12, 8)
    assert len(result["fom_history"]) == 15
    # 无 NaN
    has_nan = any(math.isnan(x) for x in result["fom_history"])
    assert not has_nan, "fom_history 含 NaN（违反 R03）"
    # FoM 为正（R05 修复）
    assert result["initial_fom"] > 0
    assert result["best_fom"] > 0
    # improvement_db 有限且 >= 0（best-checkpoint 语义）
    assert math.isfinite(result["improvement_db"])
    assert result["improvement_db"] >= 0.0
    # 二值化比例在 [0,1]
    assert 0.0 <= result["binary_ratio"] <= 1.0
    assert 0.0 <= result["final_density_grayness"] <= 1.0


# =============================================================================
# 7. 参数校验（R03 禁止 fall-back）
# =============================================================================


def test_invalid_n_iterations_raises():
    """n_iterations 非正整数 raise ValueError（R03）。"""
    with pytest.raises(ValueError, match="n_iterations"):
        optimize_topology_mmi_1x2(n_iterations=0)
    with pytest.raises(ValueError, match="n_iterations"):
        optimize_topology_mmi_1x2(n_iterations=-5)


def test_invalid_learning_rate_raises():
    """learning_rate 非正数 raise ValueError（R03）。"""
    with pytest.raises(ValueError, match="learning_rate"):
        optimize_topology_mmi_1x2(learning_rate=0.0)
    with pytest.raises(ValueError, match="learning_rate"):
        optimize_topology_mmi_1x2(learning_rate=-0.1)


def test_invalid_grid_size_raises():
    """网格尺寸 <8 raise ValueError（R03）。"""
    with pytest.raises(ValueError, match="网格"):
        optimize_topology_mmi_1x2(grid_nx=4, grid_ny=8)
    with pytest.raises(ValueError, match="网格"):
        optimize_topology_mmi_1x2(grid_nx=8, grid_ny=4)
