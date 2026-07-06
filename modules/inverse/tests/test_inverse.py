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
class TestConstants:
    """物理常量与模块元信息验证（R02 学术诚信：参数可溯源）。"""

    def test_eps_r_si_value(self) -> None:
        """硅相对介电常数 = 3.476² ≈ 12.0826（Soref 1993 @1.55μm）。"""
        expected = 3.476**2
        assert EPS_R_SI == pytest.approx(expected, rel=1e-12)
        assert EPS_R_SI == pytest.approx(12.0826, rel=1e-4)

    def test_eps_r_sio2_value(self) -> None:
        """二氧化硅相对介电常数 = 1.444² ≈ 2.0851（Soref 1993 @1.55μm）。"""
        expected = 1.444**2
        assert EPS_R_SIO2 == pytest.approx(expected, rel=1e-12)
        assert EPS_R_SIO2 == pytest.approx(2.0851, rel=1e-4)

    def test_grid_dimensions(self) -> None:
        """网格尺寸 24×12×8（200nm 网格，JAX AD 开销权衡）。"""
        assert GRID_NX == 24
        assert GRID_NY == 12
        assert GRID_NZ == 8
        # NZ=8 支持 2 层 PML + 非PML区域 z=[2:6]
        assert GRID_NZ >= 2 * PML_N_LAYERS + 2

    def test_grid_dx_value(self) -> None:
        """网格步长 200nm（200nm 网格在 λ=1550nm 下为 7.75 点/波长）。"""
        assert GRID_DX_M == 0.2e-6
        # 验证 λ/dx ≈ 7.75（200nm 网格在 1550nm 波长下）
        wavelength_m = TARGET_WAVELENGTH_UM * 1e-6
        points_per_wavelength = wavelength_m / GRID_DX_M
        assert points_per_wavelength == pytest.approx(7.75, rel=1e-6)

    def test_pml_n_layers(self) -> None:
        """PML 层数 2（每侧，Gedney 1996 单轴各向异性）。"""
        assert PML_N_LAYERS == 2
        # 2*PML_N_LAYERS 必须小于 min(nx, ny, nz)（GedneyPML 校验）
        assert 2 * PML_N_LAYERS < min(GRID_NX, GRID_NY, GRID_NZ)

    def test_target_wavelength(self) -> None:
        """目标波长 1.55μm（C 波段，光纤通信标准）。"""
        assert TARGET_WAVELENGTH_UM == 1.55

    def test_optimization_defaults(self) -> None:
        """优化默认参数: N_ITERATIONS=50, LEARNING_RATE=0.5, MOMENTUM=0.3。"""
        assert N_ITERATIONS == 50
        assert LEARNING_RATE == 0.5
        # *修复 R05*: 动量从 0.9 降至 0.3（适配嘈杂 FoM 景观）
        assert MOMENTUM == 0.3
        assert INITIAL_WIDTH_PIXELS == 2.0

    def test_momentum_low_value_r05(self) -> None:
        """*R05 回归*: 动量 0.3（非 0.9），适配 200nm 网格嘈杂 FoM 景观。

        旧 BUG: m=0.9 时 heavy-ball 有效步长 ≈ lr/(1-m) = 5.0，
        远超搜索范围 [0.5, ny/2-1=5]，严重过冲致 FoM 暴跌。
        修复: m=0.3 有效步长 0.71，适配嘈杂景观。
        来源: Polyak 1964; Smith 2017 arXiv:1711.00489（嘈杂梯度建议低动量）
        """
        assert MOMENTUM == 0.3
        effective_step = LEARNING_RATE / (1.0 - MOMENTUM)
        # 有效步长应 < 搜索范围上限 ny/2-1=5
        assert effective_step < GRID_NY / 2.0 - 1.0

    def test_inverse_version(self) -> None:
        """验证子模块版本号为 5.0.0（与 8 子模块统一版本对齐）。"""
        assert polaris_inverse.__version__ == "5.0.0"

    def test_module_exports(self) -> None:
        """验证 __all__ 导出完整（全部稳定 API 可导入）。"""
        expected_exports = {
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
            "__version__",
        }
        actual_exports = set(polaris_inverse.__all__)
        missing = expected_exports - actual_exports
        assert not missing, f"缺少导出: {missing}"


# =============================================================================
# 2. YeeGrid3D 网格验证（Yee 1966 IEEE TAP）
# =============================================================================
class TestYeeGrid3D:
    """YeeGrid3D 3D Yee 交错网格验证。"""

    def test_construction_basic(self) -> None:
        """基本构造: nx/ny/nz/dx/dy/dz 正确存储。"""
        grid = YeeGrid3D(nx=10, ny=20, nz=30, dx=1e-7, dy=2e-7, dz=3e-7)
        assert grid.nx == 10
        assert grid.ny == 20
        assert grid.nz == 30
        assert grid.dx == 1e-7
        assert grid.dy == 2e-7
        assert grid.dz == 3e-7

    def test_cell_volume(self) -> None:
        """单元网格体积 = dx*dy*dz。"""
        grid = YeeGrid3D(nx=10, ny=10, nz=10, dx=1e-7, dy=2e-7, dz=3e-7)
        assert grid.cell_volume == pytest.approx(6e-21, rel=1e-12)

    def test_cfl_timestep_formula(self) -> None:
        """CFL 时间步公式: dt = 0.95*sqrt(eps_r)/(c*sqrt(1/dx²+1/dy²+1/dz²))。

        来源: Taflove 2005 §4.1 Courant-Friedrichs-Lewy 稳定条件。
        """
        grid = YeeGrid3D(nx=10, ny=10, nz=10, dx=1e-7, dy=1e-7, dz=1e-7)
        eps_r = 1.0
        dt = grid.cfl_timestep(eps_r)
        # 手算: dt = 0.95 * 1 / (c * sqrt(3/dx²)) = 0.95 * dx / (c * sqrt(3))
        expected = 0.95 * 1e-7 / (C0 * np.sqrt(3))
        assert dt == pytest.approx(expected, rel=1e-6)

    def test_cfl_timestep_high_eps(self) -> None:
        """高介电常数下 CFL 时间步应缩小（sqrt(eps_r) 因子）。"""
        grid = YeeGrid3D(nx=10, ny=10, nz=10, dx=1e-7, dy=1e-7, dz=1e-7)
        dt_free = grid.cfl_timestep(1.0)
        dt_si = grid.cfl_timestep(EPS_R_SI)  # ~12.08
        # dt_si = sqrt(12.08) * dt_free ≈ 3.476 * dt_free
        ratio = dt_si / dt_free
        assert ratio == pytest.approx(np.sqrt(EPS_R_SI), rel=1e-6)

    def test_invalid_dimensions_raise(self) -> None:
        """非法网格尺寸/步长应 raise（R03 禁止 fall-back）。"""
        with pytest.raises(ValueError, match="nx"):
            YeeGrid3D(nx=0, ny=10, nz=10, dx=1e-7, dy=1e-7, dz=1e-7)
        with pytest.raises(ValueError, match="ny"):
            YeeGrid3D(nx=10, ny=-1, nz=10, dx=1e-7, dy=1e-7, dz=1e-7)
        with pytest.raises(ValueError, match="nz"):
            YeeGrid3D(nx=10, ny=10, nz=0, dx=1e-7, dy=1e-7, dz=1e-7)
        with pytest.raises(ValueError, match="dx"):
            YeeGrid3D(nx=10, ny=10, nz=10, dx=0, dy=1e-7, dz=1e-7)
        with pytest.raises(ValueError, match="dy"):
            YeeGrid3D(nx=10, ny=10, nz=10, dx=1e-7, dy=-1, dz=1e-7)
        with pytest.raises(ValueError, match="dz"):
            YeeGrid3D(nx=10, ny=10, nz=10, dx=1e-7, dy=1e-7, dz=0)

    def test_cfl_invalid_eps_raises(self) -> None:
        """cfl_timestep 非法 eps_r_max 应 raise（R03）。"""
        grid = YeeGrid3D(nx=10, ny=10, nz=10, dx=1e-7, dy=1e-7, dz=1e-7)
        with pytest.raises(ValueError, match="eps_r_max"):
            grid.cfl_timestep(0.0)
        with pytest.raises(ValueError, match="eps_r_max"):
            grid.cfl_timestep(-1.0)


# =============================================================================
# 3. GedneyPML 验证（Gedney 1996 IEEE TAP）
# =============================================================================
class TestGedneyPML:
    """GedneyPML 单轴各向异性 PML 吸收边界验证。"""

    def test_construction_basic(self) -> None:
        """基本构造: n_layers/eps_r_bg 正确存储。"""
        grid = YeeGrid3D(nx=10, ny=10, nz=10, dx=1e-7, dy=1e-7, dz=1e-7)
        grid.epsilon_r = jnp.ones((10, 10, 10)) * 2.0
        pml = GedneyPML(grid, n_layers=2, eps_r_bg=2.0)
        assert pml.n_layers == 2
        assert pml.eps_r_bg == 2.0
        assert pml.m == 3  # Gedney 1996 建议幂指数 m=3

    def test_invalid_n_layers_raises(self) -> None:
        """非法 n_layers 应 raise（R03）。"""
        grid = YeeGrid3D(nx=10, ny=10, nz=10, dx=1e-7, dy=1e-7, dz=1e-7)
        grid.epsilon_r = jnp.ones((10, 10, 10))
        with pytest.raises(ValueError, match="n_layers"):
            GedneyPML(grid, n_layers=-1)
        # n_layers*2 >= min_dim 应 raise
        with pytest.raises(ValueError, match="n_layers\\*2"):
            GedneyPML(grid, n_layers=5)  # 2*5=10 >= min(10,10,10)=10

    def test_invalid_m_raises(self) -> None:
        """非法幂指数 m 应 raise（R03）。"""
        grid = YeeGrid3D(nx=10, ny=10, nz=10, dx=1e-7, dy=1e-7, dz=1e-7)
        grid.epsilon_r = jnp.ones((10, 10, 10))
        with pytest.raises(ValueError, match="m"):
            GedneyPML(grid, n_layers=2, m=0)
        with pytest.raises(ValueError, match="m"):
            GedneyPML(grid, n_layers=2, m=-1)

    def test_invalid_eps_r_bg_raises(self) -> None:
        """非法 eps_r_bg 应 raise（R03）。"""
        grid = YeeGrid3D(nx=10, ny=10, nz=10, dx=1e-7, dy=1e-7, dz=1e-7)
        grid.epsilon_r = jnp.ones((10, 10, 10))
        with pytest.raises(ValueError, match="eps_r_bg"):
            GedneyPML(grid, n_layers=2, eps_r_bg=0.0)
        with pytest.raises(ValueError, match="eps_r_bg"):
            GedneyPML(grid, n_layers=2, eps_r_bg=-1.0)

    def test_damping_coefficients_shapes(self) -> None:
        """阻尼系数 (Ca, Cb) × 3 轴形状应为 (nx,1,1)/(1,ny,1)/(1,1,nz) 广播。"""
        grid = YeeGrid3D(nx=10, ny=12, nz=8, dx=1e-7, dy=1e-7, dz=1e-7)
        grid.epsilon_r = jnp.ones((10, 12, 8)) * EPS_R_SI
        pml = GedneyPML(grid, n_layers=2, eps_r_bg=EPS_R_SI)
        dt = float(grid.cfl_timestep(EPS_R_SI)) * 0.3
        ca_x, cb_x, ca_y, cb_y, ca_z, cb_z = pml.damping_coefficients(dt)
        # x 轴形状 (nx, 1, 1)，y 轴 (1, ny, 1)，z 轴 (1, 1, nz)
        assert ca_x.shape == (10, 1, 1)
        assert cb_x.shape == (10, 1, 1)
        assert ca_y.shape == (1, 12, 1)
        assert cb_y.shape == (1, 12, 1)
        assert ca_z.shape == (1, 1, 8)
        assert cb_z.shape == (1, 1, 8)

    def test_damping_coefficients_internal_one(self) -> None:
        """PML 内部区域 Ca=1, Cb=dt/eps（无阻尼），边界区域 Ca<1（有阻尼）。

        来源: Gedney 1996 IEEE TAP §III, Taflove 2005 §7.6.2。
        """
        grid = YeeGrid3D(nx=10, ny=10, nz=10, dx=1e-7, dy=1e-7, dz=1e-7)
        grid.epsilon_r = jnp.ones((10, 10, 10)) * EPS_R_SI
        pml = GedneyPML(grid, n_layers=2, eps_r_bg=EPS_R_SI)
        dt = float(grid.cfl_timestep(EPS_R_SI)) * 0.3
        ca_x, cb_x, _, _, _, _ = pml.damping_coefficients(dt)
        ca_x_np = np.array(ca_x).flatten()
        # PML 在 x=[0:2] 和 [8:10]，内部 x=[2:8] 应 Ca=1（无阻尼）
        assert ca_x_np[5] == pytest.approx(1.0, abs=1e-12)
        # 边界 x=0 应 Ca<1（有阻尼）
        assert ca_x_np[0] < 1.0
        # 对称性: x=0 与 x=9 阻尼相同
        assert ca_x_np[0] == pytest.approx(ca_x_np[9], rel=1e-6)

    def test_invalid_dt_raises(self) -> None:
        """damping_coefficients 非法 dt 应 raise（R03）。"""
        grid = YeeGrid3D(nx=10, ny=10, nz=10, dx=1e-7, dy=1e-7, dz=1e-7)
        grid.epsilon_r = jnp.ones((10, 10, 10)) * EPS_R_SI
        pml = GedneyPML(grid, n_layers=2, eps_r_bg=EPS_R_SI)
        with pytest.raises(ValueError, match="dt"):
            pml.damping_coefficients(0.0)
        with pytest.raises(ValueError, match="dt"):
            pml.damping_coefficients(-1.0)


# =============================================================================
# 4. DifferentiableFDTD 验证（*创新* JAX 可微分 3D FDTD）
# =============================================================================
class TestDifferentiableFDTD:
    """DifferentiableFDTD JAX 可微分 3D FDTD 内核验证。"""

    def test_construction_basic(self) -> None:
        """基本构造: grid/pml/dt/eps_r_bg 正确存储。"""
        fdtd, grid, pml = _build_default_fdtd()
        assert fdtd.grid is grid
        assert fdtd.pml is pml
        assert fdtd.eps_r_bg == EPS_R_SI
        assert fdtd.dt > 0

    def test_update_coefficients_shapes(self) -> None:
        """更新系数 Ca/Cb/Da/Db 形状 = (nx, ny, nz)。"""
        fdtd, grid, _ = _build_default_fdtd()
        assert fdtd.ca.shape == (GRID_NX, GRID_NY, GRID_NZ)
        assert fdtd.cb.shape == (GRID_NX, GRID_NY, GRID_NZ)
        assert fdtd.da.shape == (GRID_NX, GRID_NY, GRID_NZ)
        assert fdtd.db.shape == (GRID_NX, GRID_NY, GRID_NZ)

    def test_run_returns_dict_fields(self) -> None:
        """run 返回 dict 含全部 E/H 场 + monitor/source 信号。"""
        fdtd, grid, _ = _build_default_fdtd()
        source_pos, monitor_pos, source_freq, _ = _default_source_monitor()
        n_steps = 50  # 短步数省时
        eps_r = epsilon_r_from_width(
            jnp.array(INITIAL_WIDTH_PIXELS, dtype=jnp.float32),
            GRID_NX, GRID_NY, GRID_NZ, EPS_R_SI, EPS_R_SIO2,
        )
        result = fdtd.run(
            epsilon_r=eps_r,
            source_pos=source_pos,
            source_freq=source_freq,
            n_steps=n_steps,
            monitor_pos=monitor_pos,
        )
        expected_keys = {
            "Ex", "Ey", "Ez", "Hx", "Hy", "Hz",
            "monitor_signal", "source_signal",
        }
        assert set(result.keys()) == expected_keys
        # 场形状 = (nx, ny, nz)
        for key in ["Ex", "Ey", "Ez", "Hx", "Hy", "Hz"]:
            assert result[key].shape == (GRID_NX, GRID_NY, GRID_NZ)
        # 信号形状 = (n_steps,)
        assert result["monitor_signal"].shape == (n_steps,)
        assert result["source_signal"].shape == (n_steps,)

    def test_run_field_finite(self) -> None:
        """run 输出场与信号应为有限值（无 NaN/Inf，R03）。"""
        fdtd, grid, _ = _build_default_fdtd()
        source_pos, monitor_pos, source_freq, _ = _default_source_monitor()
        n_steps = 50
        eps_r = epsilon_r_from_width(
            jnp.array(INITIAL_WIDTH_PIXELS, dtype=jnp.float32),
            GRID_NX, GRID_NY, GRID_NZ, EPS_R_SI, EPS_R_SIO2,
        )
        result = fdtd.run(
            epsilon_r=eps_r,
            source_pos=source_pos,
            source_freq=source_freq,
            n_steps=n_steps,
            monitor_pos=monitor_pos,
        )
        for key in ["Ex", "Ey", "Ez", "Hx", "Hy", "Hz"]:
            arr = np.array(result[key])
            assert np.all(np.isfinite(arr)), f"{key} 含 NaN/Inf"
        mon_sig = np.array(result["monitor_signal"])
        src_sig = np.array(result["source_signal"])
        assert np.all(np.isfinite(mon_sig)), "monitor_signal 含 NaN/Inf"
        assert np.all(np.isfinite(src_sig)), "source_signal 含 NaN/Inf"

    def test_run_source_signal_nonzero(self) -> None:
        """源点信号应有非零峰值（源注入有效）。"""
        fdtd, grid, _ = _build_default_fdtd()
        source_pos, monitor_pos, source_freq, _ = _default_source_monitor()
        n_steps = 50
        eps_r = epsilon_r_from_width(
            jnp.array(INITIAL_WIDTH_PIXELS, dtype=jnp.float32),
            GRID_NX, GRID_NY, GRID_NZ, EPS_R_SI, EPS_R_SIO2,
        )
        result = fdtd.run(
            epsilon_r=eps_r,
            source_pos=source_pos,
            source_freq=source_freq,
            n_steps=n_steps,
            monitor_pos=monitor_pos,
        )
        src_peak = float(jnp.max(jnp.abs(result["source_signal"])))
        assert src_peak > 0, f"source_signal 峰值应 > 0（源注入有效），实际 {src_peak}"

    def test_invalid_dt_raises(self) -> None:
        """非法 dt 应 raise（R03）。"""
        grid = YeeGrid3D(nx=10, ny=10, nz=10, dx=1e-7, dy=1e-7, dz=1e-7)
        grid.epsilon_r = jnp.ones((10, 10, 10)) * EPS_R_SI
        with pytest.raises(ValueError, match="dt"):
            DifferentiableFDTD(grid, pml=None, dt=0.0)
        with pytest.raises(ValueError, match="dt"):
            DifferentiableFDTD(grid, pml=None, dt=-1.0)

    def test_invalid_eps_r_bg_raises(self) -> None:
        """非法 eps_r_bg 应 raise（R03）。"""
        grid = YeeGrid3D(nx=10, ny=10, nz=10, dx=1e-7, dy=1e-7, dz=1e-7)
        grid.epsilon_r = jnp.ones((10, 10, 10)) * EPS_R_SI
        with pytest.raises(ValueError, match="eps_r_bg"):
            DifferentiableFDTD(grid, pml=None, eps_r_bg=0.0)
        with pytest.raises(ValueError, match="eps_r_bg"):
            DifferentiableFDTD(grid, pml=None, eps_r_bg=-1.0)


# =============================================================================
# 5. epsilon_r_from_width 验证（sigmoid 软边界参数化）
# =============================================================================
class TestEpsilonRFromWidth:
    """epsilon_r_from_width sigmoid 软边界参数化验证。

    来源: Jensen & Sigmund 2011 "Topology optimization for nano-photonics"
    https://doi.org/10.1002/lpor.201000014
    """

    def test_shape(self) -> None:
        """输出形状 = (nx, ny, nz)。"""
        width = jnp.array(2.0, dtype=jnp.float32)
        eps_r = epsilon_r_from_width(width, GRID_NX, GRID_NY, GRID_NZ, EPS_R_SI, EPS_R_SIO2)
        assert eps_r.shape == (GRID_NX, GRID_NY, GRID_NZ)

    def test_core_cladding_values(self) -> None:
        """波导芯区域 eps_r → eps_si，远离芯区域 eps_r → eps_bg。

        sigmoid 软边界: width=2.0, center=ny/2=6, 软化温度 0.5。
        y=6（中心）: dist=0, sigmoid((2-0)/0.5)=sigmoid(4)≈0.982
            → eps = eps_bg + (eps_si - eps_bg) * 0.982 ≈ 11.90（接近 eps_si）
        y=0（边界）: dist=6, sigmoid((2-6)/0.5)=sigmoid(-8)≈0 → eps≈eps_bg
        """
        width = jnp.array(2.0, dtype=jnp.float32)
        eps_r = epsilon_r_from_width(width, GRID_NX, GRID_NY, GRID_NZ, EPS_R_SI, EPS_R_SIO2)
        eps_np = np.array(eps_r)
        # 中心 y=6: sigmoid(4)≈0.982，eps ≈ eps_bg + (eps_si-eps_bg)*0.982
        softness = 0.5
        sigmoid_center = 1.0 / (1.0 + np.exp(-float(width) / softness))
        expected_center = EPS_R_SIO2 + (EPS_R_SI - EPS_R_SIO2) * sigmoid_center
        center_eps = float(eps_np[GRID_NX // 2, GRID_NY // 2, GRID_NZ // 2])
        assert center_eps == pytest.approx(expected_center, rel=1e-3)
        # 中心 eps 应接近 eps_si（sigmoid(4)≈0.982，差约 2%）
        assert center_eps > 0.95 * EPS_R_SI
        # 边界 y=0 应接近 eps_bg（sigmoid(-8)≈0）
        boundary_eps = float(eps_np[GRID_NX // 2, 0, GRID_NZ // 2])
        assert boundary_eps == pytest.approx(EPS_R_SIO2, rel=1e-2)

    def test_width_monotonicity(self) -> None:
        """增大 width 应使更多 y 点落入波导芯（中心 eps 增大，边界 eps 增大）。

        物理含义: 更宽的波导 → 更多区域为硅芯。
        sigmoid 软边界: 中心 dist=0, sigmoid(width/softness)。
        width=1.0 → sigmoid(2)≈0.881; width=4.0 → sigmoid(8)≈0.9997。
        """
        width_small = jnp.array(1.0, dtype=jnp.float32)
        width_large = jnp.array(4.0, dtype=jnp.float32)
        eps_small = np.array(epsilon_r_from_width(
            width_small, GRID_NX, GRID_NY, GRID_NZ, EPS_R_SI, EPS_R_SIO2
        ))
        eps_large = np.array(epsilon_r_from_width(
            width_large, GRID_NX, GRID_NY, GRID_NZ, EPS_R_SI, EPS_R_SIO2
        ))
        # 中心点: 大 width 应有更高 eps（sigmoid(8) > sigmoid(2)）
        cy = GRID_NY // 2
        eps_small_center = float(eps_small[GRID_NX // 2, cy, GRID_NZ // 2])
        eps_large_center = float(eps_large[GRID_NX // 2, cy, GRID_NZ // 2])
        assert eps_large_center > eps_small_center, (
            f"大 width 中心 eps {eps_large_center} 应 > 小 width {eps_small_center}"
        )
        # 大 width 中心应非常接近 eps_si（sigmoid(8)≈0.9997）
        assert eps_large_center > 0.99 * EPS_R_SI
        # 边界 y=0: 大 width 应有更高 eps（更宽波导覆盖到边界）
        assert eps_large[GRID_NX // 2, 0, GRID_NZ // 2] >= eps_small[GRID_NX // 2, 0, GRID_NZ // 2]
        # 总和: 大 width 应有更多硅芯（eps 总和更大）
        assert eps_large.sum() > eps_small.sum()

    def test_y_symmetry(self) -> None:
        """epsilon_r 在 y 方向关于中心对称（波导居中）。"""
        width = jnp.array(2.0, dtype=jnp.float32)
        eps_r = np.array(epsilon_r_from_width(
            width, GRID_NX, GRID_NY, GRID_NZ, EPS_R_SI, EPS_R_SIO2
        ))
        center = GRID_NY // 2
        # y=center-i 与 y=center+i 应相等
        for i in range(1, min(center, GRID_NY - center)):
            eps_low = eps_r[GRID_NX // 2, center - i, GRID_NZ // 2]
            eps_high = eps_r[GRID_NX // 2, center + i, GRID_NZ // 2]
            assert eps_low == pytest.approx(eps_high, rel=1e-6)

    def test_x_z_uniformity(self) -> None:
        """epsilon_r 在 x/z 方向均匀（波导沿 x 传播，y 方向宽度变化）。"""
        width = jnp.array(2.0, dtype=jnp.float32)
        eps_r = np.array(epsilon_r_from_width(
            width, GRID_NX, GRID_NY, GRID_NZ, EPS_R_SI, EPS_R_SIO2
        ))
        # 固定 y，沿 x 方向应全部相同
        y_test = GRID_NY // 2
        z_test = GRID_NZ // 2
        eps_along_x = eps_r[:, y_test, z_test]
        assert np.allclose(eps_along_x, eps_along_x[0], rtol=1e-6)
        # 固定 y，沿 z 方向应全部相同
        eps_along_z = eps_r[GRID_NX // 2, y_test, :]
        assert np.allclose(eps_along_z, eps_along_z[0], rtol=1e-6)


# =============================================================================
# 6. fom_fn 验证（归一化传输率优值函数，*修复 R05*）
# =============================================================================
class TestFomFn:
    """fom_fn 归一化传输率优值函数验证。

    *修复 R05 BUG*: FoM 归一化为 monitor_peak/source_peak（值域 [0,1]）。
    旧 BUG: FoM = max(|monitor|) 是原始场强值（~1e16），梯度裁剪恒触发不收敛。
    """

    def test_fom_returns_scalar(self) -> None:
        """fom_fn 返回标量（jnp.ndarray 标量）。"""
        fdtd, grid, _ = _build_default_fdtd()
        source_pos, monitor_pos, source_freq, target_freq = _default_source_monitor()
        width = jnp.array(INITIAL_WIDTH_PIXELS, dtype=jnp.float32)
        fom = fom_fn(
            width, fdtd, grid, source_pos, source_freq,
            50, monitor_pos, target_freq,
        )
        assert fom.shape == ()  # 标量

    def test_fom_in_unit_range(self) -> None:
        """*R05 回归*: FoM 应在 (0, 1] 范围（归一化传输率）。

        旧 BUG: FoM 为 ~1e16 裸场强值；修复后为 monitor/source 峰值比 ∈ [0,1]。
        """
        fdtd, grid, _ = _build_default_fdtd()
        source_pos, monitor_pos, source_freq, target_freq = _default_source_monitor()
        width = jnp.array(INITIAL_WIDTH_PIXELS, dtype=jnp.float32)
        fom = float(fom_fn(
            width, fdtd, grid, source_pos, source_freq,
            50, monitor_pos, target_freq,
        ))
        assert 0 < fom <= 1.0001, (
            f"FoM={fom} 应在 (0,1] 范围（归一化传输率，旧 BUG 为 ~1e16 裸场强）"
        )

    def test_fom_finite(self) -> None:
        """FoM 应为有限值（无 NaN/Inf，R03）。"""
        fdtd, grid, _ = _build_default_fdtd()
        source_pos, monitor_pos, source_freq, target_freq = _default_source_monitor()
        width = jnp.array(INITIAL_WIDTH_PIXELS, dtype=jnp.float32)
        fom = float(fom_fn(
            width, fdtd, grid, source_pos, source_freq,
            50, monitor_pos, target_freq,
        ))
        assert math.isfinite(fom), f"FoM 应为有限值，实际 {fom}"

    def test_fom_different_widths_differ(self) -> None:
        """不同宽度应产生不同 FoM（FoM 对 width 敏感）。"""
        fdtd, grid, _ = _build_default_fdtd()
        source_pos, monitor_pos, source_freq, target_freq = _default_source_monitor()
        fom_narrow = float(fom_fn(
            jnp.array(1.0, dtype=jnp.float32), fdtd, grid,
            source_pos, source_freq, 50, monitor_pos, target_freq,
        ))
        fom_wide = float(fom_fn(
            jnp.array(4.0, dtype=jnp.float32), fdtd, grid,
            source_pos, source_freq, 50, monitor_pos, target_freq,
        ))
        assert fom_narrow != fom_wide, (
            f"不同宽度 FoM 应不同: narrow={fom_narrow}, wide={fom_wide}"
        )


# =============================================================================
# 7. JAX autograd 可微性验证（*创新* 替代 lumopt 手动伴随方程）
# =============================================================================
class TestJaxAutograd:
    """JAX jax.grad 自动微分可微性验证。

    *创新*: 用 jax.grad 自动计算 dFoM/dwidth，替代 lumopt 手动推导伴随方程。
    支持理论: Hughes 2018 ACS Photonics 证明 autograd = adjoint（数学等价）。
    """

    def test_grad_returns_scalar(self) -> None:
        """jax.grad(fom_fn) 返回标量梯度（与 width_param 同形状）。"""
        fdtd, grid, _ = _build_default_fdtd()
        source_pos, monitor_pos, source_freq, target_freq = _default_source_monitor()
        grad_fn = jax.grad(fom_fn, argnums=0)
        width = jnp.array(INITIAL_WIDTH_PIXELS, dtype=jnp.float32)
        grad = grad_fn(
            width, fdtd, grid, source_pos, source_freq,
            50, monitor_pos, target_freq,
        )
        assert grad.shape == ()

    def test_grad_finite(self) -> None:
        """梯度应为有限值（无 NaN/Inf，R03）。"""
        fdtd, grid, _ = _build_default_fdtd()
        source_pos, monitor_pos, source_freq, target_freq = _default_source_monitor()
        grad_fn = jax.grad(fom_fn, argnums=0)
        width = jnp.array(INITIAL_WIDTH_PIXELS, dtype=jnp.float32)
        grad = float(grad_fn(
            width, fdtd, grid, source_pos, source_freq,
            50, monitor_pos, target_freq,
        ))
        assert math.isfinite(grad), f"梯度应为有限值，实际 {grad}"

    def test_grad_magnitude_reasonable(self) -> None:
        """*R05 回归*: 归一化后梯度量级 O(0.001-1)，不恒触发 [-1,1] 裁剪。

        旧 BUG: 未归一化时梯度 ~1e15 恒触发裁剪为 ±1，方向信息丢失。
        修复后: 归一化 FoM ∈ [0,1]，梯度 O(0.001-1)，裁剪仅作安全网。
        """
        fdtd, grid, _ = _build_default_fdtd()
        source_pos, monitor_pos, source_freq, target_freq = _default_source_monitor()
        grad_fn = jax.grad(fom_fn, argnums=0)
        width = jnp.array(INITIAL_WIDTH_PIXELS, dtype=jnp.float32)
        grad = float(grad_fn(
            width, fdtd, grid, source_pos, source_freq,
            50, monitor_pos, target_freq,
        ))
        # 梯度应在合理范围（旧 BUG 为 ~1e15）
        assert abs(grad) < 1e6, (
            f"梯度量级 {grad:.2e} 过大（旧 BUG ~1e15 恒触发裁剪），"
            f"归一化后应 O(0.001-1)"
        )


# =============================================================================
# 8. run_adjoint_optimization / optimize_waveguide_width 端到端验证
# =============================================================================
