"""3D 逆向设计子模块测试（V5.1.0 D12 增强 #3）。

测试覆盖维度:
- 3D SIMP 密度插值（Bendsøe & Sigmund 2003 3D 版本）
- 3D 灵敏度滤波（Lazarov & Sigmund 2011 3D cone kernel，R05 卷积维度修复）
- 3D 体素化（voxelization，Su 2020 SPINS）
- FoM 函数可微性（jax.grad，*创新* 替代手动 3D 伴随 Maxwell 方程）
- 2 器件端到端优化（3D taper/光栅耦合器）
- 参数校验（R03 禁止 fall-back，含 ny>=4 宽松校验回归）

来源（R02 学术诚信，≥5 个文献 URL）:
- Piggott et al. 2017 Nature Photonics
  https://doi.org/10.1038/nphoton.2017.102
- Hughes et al. 2018 ACS Photonics https://arxiv.org/abs/1811.01255
- Su et al. 2020 Nanophotonics https://doi.org/10.1515/nanoph-2019-0392
- Sanchis et al. 2009 IEEE PTL https://doi.org/10.1109/LPT.2009.2028268
- Saleh & Teich 2019 "Fundamentals of Photonics" Wiley §7.2
- Taflove & Hagness 2005 "Computational Electrodynamics"
- Giles & Pierce 2000 SIAM Review
  https://doi.org/10.1137/S0036144599363118
- Bendsøe & Sigmund 2003 "Topology Optimization" Springer
  https://link.springer.com/book/10.1007/978-3-662-05086-6

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

from polaris_inverse.adjoint_3d import (  # noqa: E402
    FILTER_RADIUS_PX,
    GRATING_DUTY_CYCLE,
    GRATING_PERIOD_UM,
    LEARNING_RATE,
    MOMENTUM,
    N_ITERATIONS,
    N_GROUP_SI,
    N_SI,
    N_SIO2,
    SIMP_PENALTY_P,
    TAPER_RADIATION_ALPHA,
    WAVELENGTH_UM,
    grating_coupler_3d_fom,
    optimize_3d_adjoint_grating,
    optimize_3d_adjoint_taper,
    sensitivity_filter_3d,
    simp_interpolation_3d,
    taper_3d_fom,
    voxelize_3d,
)


# =============================================================================
# 1. 物理常量与参数验证
# =============================================================================


def test_physical_constants():
    """验证 3D 逆向设计物理常量与参数。"""
    assert N_SI == pytest.approx(3.476, abs=1e-4)
    assert N_SIO2 == pytest.approx(1.444, abs=1e-4)
    assert N_GROUP_SI == pytest.approx(4.20, abs=0.01)
    assert WAVELENGTH_UM == pytest.approx(1.55, abs=1e-6)
    assert SIMP_PENALTY_P == 3.0  # Bendsøe & Sigmund 2003
    assert 0.0 < MOMENTUM < 1.0  # Polyak 1964
    assert LEARNING_RATE > 0
    assert N_ITERATIONS >= 20  # 3D 计算量大，迭代数较少
    assert FILTER_RADIUS_PX > 0  # 滤波半径
    assert TAPER_RADIATION_ALPHA > 0  # 辐射损耗系数
    assert 0.0 < GRATING_DUTY_CYCLE < 1.0  # 占空比
    assert GRATING_PERIOD_UM > 0  # 光栅周期


# =============================================================================
# 2. 3D SIMP 密度插值（Bendsøe & Sigmund 2003 3D 版本）
# =============================================================================


def test_simp_3d_endpoints():
    """3D SIMP 端点: ρ=0→eps_bg, ρ=1→eps_si。"""
    eps_bg = N_SIO2**2
    eps_si = N_SI**2
    d0 = simp_interpolation_3d(jnp.zeros((4, 4, 4)), eps_bg, eps_si)
    assert float(jnp.allclose(d0, eps_bg))
    d1 = simp_interpolation_3d(jnp.ones((4, 4, 4)), eps_bg, eps_si)
    assert float(jnp.allclose(d1, eps_si))


def test_simp_3d_shape():
    """3D SIMP 形状保持。"""
    density = jnp.ones((8, 6, 10)) * 0.5
    eps = simp_interpolation_3d(density, N_SIO2**2, N_SI**2)
    assert eps.shape == (8, 6, 10)


# =============================================================================
# 3. 3D 灵敏度滤波（R05 卷积维度修复回归）
# =============================================================================


def test_sensitivity_filter_3d_shape():
    """3D 滤波形状保持（R05 卷积维度修复回归）。"""
    g = jnp.ones((8, 6, 8))
    filtered = sensitivity_filter_3d(g, g, radius=1.2)
    assert filtered.shape == (8, 6, 8)


def test_sensitivity_filter_3d_uniform():
    """均匀 3D 梯度滤波后内部近似不变。"""
    g = jnp.ones((10, 8, 10))
    filtered = sensitivity_filter_3d(g, g, radius=1.2)
    center_val = float(filtered[5, 4, 5])
    assert center_val == pytest.approx(1.0, abs=0.3)


# =============================================================================
# 4. 3D 体素化（Su 2020 SPINS）
# =============================================================================


def test_voxelize_3d_range():
    """体素化: 输出在 [eps_bg, eps_si]。"""
    eps_bg = N_SIO2**2
    eps_si = N_SI**2
    density = jnp.ones((6, 4, 6)) * 0.5
    eps = voxelize_3d(density, eps_bg, eps_si)
    eps_min = float(jnp.min(eps))
    eps_max = float(jnp.max(eps))
    assert eps_bg <= eps_min
    assert eps_max <= eps_si


# =============================================================================
# 5. FoM 可微性（*创新* jax.grad 替代手动 3D 伴随方程）
# =============================================================================


def test_fom_3d_differentiable_all_devices():
    """2 器件 3D FoM 可微，梯度形状正确且有限。"""
    density = jnp.ones((8, 6, 8)) * 0.5
    for fom_fn in [taper_3d_fom, grating_coupler_3d_fom]:
        grad_fn = jax.grad(fom_fn)
        g = grad_fn(density)
        assert g.shape == (8, 6, 8)
        assert float(jnp.all(jnp.isfinite(g))), f"{fom_fn.__name__} 梯度含 NaN/Inf"


def test_fom_3d_finite():
    """2 器件 3D FoM 在中等密度下有限。"""
    density = jnp.ones((8, 6, 8)) * 0.5
    for fom_fn in [taper_3d_fom, grating_coupler_3d_fom]:
        fom = float(fom_fn(density))
        assert math.isfinite(fom), f"{fom_fn.__name__} FoM 非有限值"


# =============================================================================
# 6. 端到端优化（2 器件，小迭代快速验证）
# =============================================================================


@pytest.mark.parametrize("opt_fn,device_name", [
    (optimize_3d_adjoint_taper, "Adjoint3D_taper"),
    (optimize_3d_adjoint_grating, "Adjoint3D_grating_coupler"),
])
def test_optimize_3d_adjoint_end_to_end(opt_fn, device_name):
    """2 器件 3D 逆向设计端到端: 结果结构完整 + 无 NaN + improvement_db 有限。"""
    result = opt_fn(
        grid_nx=10, grid_ny=5, grid_nz=8, n_iterations=10, learning_rate=0.03
    )
    assert result["device"] == device_name
    assert result["n_iterations"] == 10
    assert result["grid_shape"] == (10, 5, 8)
    assert len(result["fom_history"]) == 10
    # 无 NaN
    has_nan = any(math.isnan(x) for x in result["fom_history"])
    assert not has_nan, "fom_history 含 NaN（违反 R03）"
    # improvement_db 有限
    assert math.isfinite(result["improvement_db"])
    # Si 比例在 [0,1]
    assert 0.0 <= result["si_ratio"] <= 1.0
    # 二值化比例在 [0,1]
    assert 0.0 <= result["binary_ratio"] <= 1.0


def test_optimize_3d_taper_small_grid():
    """3D taper 最小网格验证（ny=4，SOI 厚度方向）。"""
    result = optimize_3d_adjoint_taper(
        grid_nx=8, grid_ny=4, grid_nz=8, n_iterations=8
    )
    assert result["grid_shape"] == (8, 4, 8)
    assert len(result["fom_history"]) == 8


# =============================================================================
# 7. 参数校验（R03 禁止 fall-back，含 ny>=4 宽松校验回归）
# =============================================================================


def test_invalid_n_iterations_raises():
    """n_iterations 非正整数 raise（R03）。"""
    with pytest.raises(ValueError, match="n_iterations"):
        optimize_3d_adjoint_taper(n_iterations=0)
    with pytest.raises(ValueError, match="n_iterations"):
        optimize_3d_adjoint_taper(n_iterations=-3)


def test_invalid_learning_rate_raises():
    """learning_rate 非正数 raise（R03）。"""
    with pytest.raises(ValueError, match="learning_rate"):
        optimize_3d_adjoint_taper(learning_rate=0.0)
    with pytest.raises(ValueError, match="learning_rate"):
        optimize_3d_adjoint_taper(learning_rate=-0.1)


def test_invalid_grid_size_raises():
    """3D 网格 nx<8 或 nz<8 raise（R03）。"""
    with pytest.raises(ValueError, match="网格"):
        optimize_3d_adjoint_taper(grid_nx=4, grid_ny=6, grid_nz=8)
    with pytest.raises(ValueError, match="网格"):
        optimize_3d_adjoint_taper(grid_nx=8, grid_ny=6, grid_nz=4)


def test_invalid_grid_ny_raises():
    """3D 网格 ny<4 raise（R03，SOI 厚度方向最小 4 像素）。"""
    with pytest.raises(ValueError, match="网格"):
        optimize_3d_adjoint_taper(grid_nx=8, grid_ny=2, grid_nz=8)


def test_ny_4_accepted():
    """ny=4（SOI 厚度方向）应被接受（R05 校验宽松回归）。"""
    result = optimize_3d_adjoint_taper(
        grid_nx=8, grid_ny=4, grid_nz=8, n_iterations=5
    )
    assert result["grid_shape"][1] == 4
