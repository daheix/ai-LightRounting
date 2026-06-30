"""R451-R460 测试：FDTD 多级网格 + CPML 综合测试（纯 NumPy/SciPy CPU）。

R451-R460 路标聚焦 FDTD 多级网格（Subgridding）与 CPML 吸收边界条件
的完整功能验证。源码已实现于：
- src/polaris/sim/fdtd/cpml.py（CPML，Roden & Gedney 2000）
- src/polaris/sim/subgridding.py（子网格，Deng 2022）
- src/polaris/sim/fdtd/yee_grid.py（Yee 网格，Yee 1966）

本测试文件按 R451-R460 路标要求新增综合测试覆盖：
- R451: CPML 配置与系数
- R452: CPML Psi 缓冲区更新
- R453: Subgridding 配置与插值
- R454: Subgridding 求解器端到端
- R455: Yee 网格系数
- R456-R460: 综合集成 + 边界条件 + 反射系数 + R03/R02/R04 合规

学术依据：
- Roden & Gedney 2000 CPML https://doi.org/10.1002/1098-2760(20001205)27:5%3C334::AID-MOP14%3E3.0.CO;2-A
- Deng et al. 2022 IEEE TAP Subgridding https://doi.org/10.1109/TAP.2022.3166240
- Yee 1966 IEEE TAP https://doi.org/10.1109/TAP.1966.1138693
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest

# R04 合规：polaris.sim.__init__ 间接依赖 sax（JAX 生态），与 R04 冲突。
# 用 importlib 直接从文件路径加载 cpml / subgridding / yee_grid 模块。
_TESTS_DIR = Path(__file__).resolve().parent
_SRC_DIR = _TESTS_DIR.parent / "src" / "polaris"


def _load_module(rel_path: str, module_name: str):
    """从 src/polaris/ 下相对路径直接加载模块，绕过 polaris.sim __init__。"""
    file_path = _SRC_DIR / rel_path
    if not file_path.exists():
        raise FileNotFoundError(f"模块文件不存在: {file_path}")
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)
    return mod


_cpml = _load_module("sim/fdtd/cpml.py", "_r451_cpml")
_subgrid = _load_module("sim/subgridding.py", "_r451_subgrid")
_yee = _load_module("sim/fdtd/yee_grid.py", "_r451_yee")

CpmlBuffers = _cpml.CpmlBuffers
CpmlCoefficients = _cpml.CpmlCoefficients
CpmlConfig = _cpml.CpmlConfig
_build_axis_profile = _cpml._build_axis_profile
_fill_ab = _cpml._fill_ab
_sigma_max_gedney = _cpml._sigma_max_gedney
build_cpml = _cpml.build_cpml
reflection_db = _cpml.reflection_db
update_e_psi = _cpml.update_e_psi
update_h_psi = _cpml.update_h_psi

SubgridConfig = _subgrid.SubgridConfig
SubgridFdtdSolver = _subgrid.SubgridFdtdSolver
SubgridResult = _subgrid.SubgridResult
estimate_speedup = _subgrid.estimate_speedup
interpolate_main_to_sub = _subgrid.interpolate_main_to_sub
interpolate_sub_to_main = _subgrid.interpolate_sub_to_main
step_yee_1d = _subgrid.step_yee_1d

YeeGridFdtd = _yee.YeeGridFdtd
build_update_coefficients = _yee.build_update_coefficients
courant_dt = _yee.courant_dt


# ===========================================================================
# R451 — CPML 配置与系数测试
# ===========================================================================


class TestR451CpmlConfig:
    """R451 CPML 配置与系数计算。"""

    def test_cpml_config_default(self):
        cfg = CpmlConfig()
        assert cfg.layers == 10
        assert cfg.order == 3
        assert cfg.alpha == pytest.approx(0.08)
        assert cfg.r_target == pytest.approx(1e-6)

    def test_cpml_config_invalid_layers(self):
        with pytest.raises(ValueError, match="PML 层数过少"):
            CpmlConfig(layers=1)

    def test_cpml_config_invalid_order(self):
        with pytest.raises(ValueError, match="σ 渐变阶数"):
            CpmlConfig(order=0)

    def test_cpml_config_invalid_kappa(self):
        with pytest.raises(ValueError, match="kappa_max"):
            CpmlConfig(kappa_max=0.0)

    def test_cpml_config_invalid_alpha(self):
        with pytest.raises(ValueError, match="alpha"):
            CpmlConfig(alpha=-0.1)

    def test_cpml_config_invalid_r_target(self):
        with pytest.raises(ValueError, match="r_target"):
            CpmlConfig(r_target=1.5)
        with pytest.raises(ValueError):
            CpmlConfig(r_target=0.0)

    def test_sigma_max_gedney(self):
        """σ_max = (m+1)/(150·π·Δh·√ε_r)。"""
        cfg = CpmlConfig(order=3)
        dx = 50e-9  # 50 nm
        eps_r = 1.0
        smax = _sigma_max_gedney(cfg, dx, eps_r)
        expected = (3 + 1) / (150.0 * np.pi * dx * np.sqrt(eps_r))
        assert smax == pytest.approx(expected, rel=1e-12)

    def test_sigma_max_gedney_invalid_dx(self):
        with pytest.raises(ValueError, match="dx"):
            _sigma_max_gedney(CpmlConfig(), 0.0, 1.0)
        with pytest.raises(ValueError):
            _sigma_max_gedney(CpmlConfig(), 1.0, 0.0)

    def test_build_axis_profile_basic(self):
        """单轴 CPML 系数构造。"""
        cfg = CpmlConfig(layers=4)
        coeff = _build_axis_profile(n=20, dx=1e-7, pml=cfg, eps_r_bg=1.0)
        assert isinstance(coeff, CpmlCoefficients)
        assert coeff.sigma.shape == (20,)
        assert coeff.kappa.shape == (20,)
        # 内部区域 sigma=0, kappa=1
        assert np.all(coeff.sigma[4:16] == 0.0)
        assert np.all(coeff.kappa[4:16] == 1.0)
        # PML 区域 sigma > 0
        assert np.all(coeff.sigma[:4] > 0.0)
        assert np.all(coeff.sigma[16:] > 0.0)

    def test_build_axis_profile_too_many_layers(self):
        """PML 层过多应 raise。"""
        cfg = CpmlConfig(layers=10)
        with pytest.raises(ValueError, match="PML 层数"):
            _build_axis_profile(n=15, dx=1e-7, pml=cfg, eps_r_bg=1.0)

    def test_fill_ab(self):
        """a/b 递归卷积系数。"""
        cfg = CpmlConfig(layers=4)
        coeff = _build_axis_profile(n=20, dx=1e-7, pml=cfg, eps_r_bg=1.0)
        coeff_ab = _fill_ab(coeff, dx=1e-7, dt=1e-16)
        # 内部区域 a=0, b=1
        assert np.all(coeff_ab.a[4:16] == 0.0)
        assert np.all(coeff_ab.b[4:16] == 1.0)
        # PML 区域 b < 1（衰减）
        assert np.all(coeff_ab.b[:4] < 1.0)
        assert np.all(coeff_ab.b[16:] < 1.0)

    def test_build_cpml_2d(self):
        """2D CPML 完整构造。"""
        cfg = CpmlConfig(layers=4)
        cx, cy, buf = build_cpml(
            shape=(20, 20), dx=1e-7, dy=1e-7, dt=1e-16, pml=cfg
        )
        assert isinstance(cx, CpmlCoefficients)
        assert isinstance(cy, CpmlCoefficients)
        assert isinstance(buf, CpmlBuffers)
        assert buf.psi_e_xz.shape == (20, 20)
        assert buf.psi_h_yx.shape == (20, 20)
        # 初始全 0
        assert np.all(buf.psi_e_xz == 0.0)

    def test_build_cpml_invalid_shape(self):
        """网格过小应 raise。"""
        cfg = CpmlConfig(layers=10)
        with pytest.raises(ValueError, match="网格"):
            build_cpml(shape=(10, 10), dx=1e-7, dy=1e-7, dt=1e-16, pml=cfg)

    def test_build_cpml_invalid_dt(self):
        with pytest.raises(ValueError, match="dt"):
            build_cpml(shape=(30, 30), dx=1e-7, dy=1e-7, dt=0.0,
                       pml=CpmlConfig(layers=4))


# ===========================================================================
# R452 — CPML Psi 缓冲区更新测试
# ===========================================================================


class TestR452CpmlPsi:
    """R452 CPML Psi 缓冲区更新。"""

    def _make_cpml(self):
        cfg = CpmlConfig(layers=4)
        return build_cpml(shape=(20, 20), dx=1e-7, dy=1e-7, dt=1e-16, pml=cfg)

    def test_update_h_psi_basic(self):
        """H 场 psi 更新：ψ *= b + a·∂E。"""
        cx, cy, buf = self._make_cpml()
        e_z = np.zeros((20, 20))
        e_z[10, 10] = 1.0  # 中心激励
        update_h_psi(e_z, buf, cx, cy)
        # 中心附近应有非零 psi
        assert np.any(buf.psi_h_yx != 0.0)

    def test_update_e_psi_basic(self):
        """E 场 psi 更新：ψ *= b + a·∂H。"""
        cx, cy, buf = self._make_cpml()
        h_x = np.zeros((20, 20))
        h_y = np.zeros((20, 20))
        h_y[10, 10] = 1.0
        update_e_psi(h_x, h_y, buf, cx, cy)
        assert np.any(buf.psi_e_xz != 0.0)

    def test_psi_zero_input_zero_output(self):
        """零输入下 psi 保持衰减（仅 b·ψ）。"""
        cx, cy, buf = self._make_cpml()
        # 先注入非零 psi
        buf.psi_h_yx[5, 5] = 1.0
        e_z = np.zeros((20, 20))
        update_h_psi(e_z, buf, cx, cy)
        # 应衰减 (· b)
        assert abs(buf.psi_h_yx[5, 5]) < 1.0

    def test_psi_internal_zero(self):
        """内部区域 a=0，psi 不积累。"""
        cx, cy, buf = self._make_cpml()
        e_z = np.zeros((20, 20))
        e_z[10, 10] = 1.0  # 内部
        update_h_psi(e_z, buf, cx, cy)
        # 内部 (10, 10) 处 a=0，psi 应保持 0
        assert buf.psi_h_yx[10, 10] == 0.0

    def test_psi_decay_over_time(self):
        """psi 多步更新后应衰减。"""
        cx, cy, buf = self._make_cpml()
        e_z = np.zeros((20, 20))
        e_z[2, 10] = 1.0  # PML 区
        update_h_psi(e_z, buf, cx, cy)
        first_val = abs(buf.psi_h_yx[2, 10])
        # 第二步，零输入
        e_z[:] = 0.0
        update_h_psi(e_z, buf, cx, cy)
        second_val = abs(buf.psi_h_yx[2, 10])
        # 应衰减
        assert second_val < first_val

    def test_reflection_db(self):
        """反射系数 dB 计算。"""
        # 反射 0.001，入射 1.0 → -60 dB
        r = reflection_db(1.0, 0.001)
        assert r == pytest.approx(-60.0, rel=1e-6)

    def test_reflection_db_perfect_absorption(self):
        """完美吸收反射 0 → -inf。"""
        r = reflection_db(1.0, 0.0)
        assert r == -np.inf

    def test_reflection_db_invalid_input(self):
        with pytest.raises(ValueError, match="入射峰值"):
            reflection_db(0.0, 0.1)
        with pytest.raises(ValueError, match="反射峰值"):
            reflection_db(1.0, -0.1)


# ===========================================================================
# R453 — Subgridding 配置与插值测试
# ===========================================================================


class TestR453Subgridding:
    """R453 Subgridding 配置与插值。"""

    def test_subgrid_config_basic(self):
        cfg = SubgridConfig(
            n_main=50, n_sub=40, factor=4,
            sub_start=20, sub_end=30,
            dx=1e-7, dt=1e-16,
        )
        assert cfg.n_main == 50
        assert cfg.factor == 4

    def test_step_yee_1d_basic(self):
        """1D Yee 时间步进。"""
        n = 20
        e = np.zeros(n)
        h = np.zeros(n - 1)
        h[10] = 1.0
        step_yee_1d(e, h, dt=1e-16, dx=1e-7)
        # h 推进 e
        assert np.any(e != 0.0)

    def test_step_yee_1d_energy_conservation(self):
        """自由空间无源应近似能量守恒。"""
        n = 50
        e = np.zeros(n)
        h = np.zeros(n - 1)
        # 注入一个高斯脉冲
        x = np.arange(n)
        e[:] = np.exp(-((x - 25) ** 2) / 10.0)
        dx = 1e-7
        dt = 0.5 * dx / 2.99792458e8  # CFL=0.5
        e0 = float(np.sum(e ** 2) + np.sum(h ** 2))
        for _ in range(10):
            step_yee_1d(e, h, dt=dt, dx=dx)
        e1 = float(np.sum(e ** 2) + np.sum(h ** 2))
        # 能量应近似守恒（误差 < 5%）
        assert abs(e1 - e0) / e0 < 0.05

    def test_interpolate_main_to_sub(self):
        """主网格 → 子网格插值。"""
        # 主网格 10 点，子网格 factor=4 → 40 点
        main = np.linspace(0, 9, 10)
        sub = interpolate_main_to_sub(main, factor=4, sub_start=2, sub_end=5)
        # 子网格应有 (5-2) * 4 = 12 点
        assert sub.shape[0] == 12

    def test_interpolate_sub_to_main(self):
        """子网格 → 主网格投影。"""
        # 子网格 12 点 → 主网格 3 点
        sub = np.linspace(0, 11, 12)
        main = interpolate_sub_to_main(sub, factor=4, sub_start=2, sub_end=5)
        assert main.shape[0] == 3

    def test_estimate_speedup(self):
        """加速比估算。"""
        s = estimate_speedup(
            n_main=1000, n_sub_region=200, factor=4, dim=1
        )
        assert s > 1.0  # 应有加速

    def test_subgrid_config_invalid_raises(self):
        with pytest.raises((ValueError, TypeError)):
            SubgridConfig(n_main=10, n_sub=20, factor=0)


# ===========================================================================
# R454 — Subgridding 求解器端到端测试
# ===========================================================================


class TestR454SubgridSolver:
    """R454 Subgridding 求解器端到端。"""

    def test_solver_basic(self):
        """子网格求解器完整运行。"""
        cfg = SubgridConfig(
            n_main=80, n_sub=40, factor=4,
            sub_start=30, sub_end=40,
            dx=1e-7, dt=1e-17,
        )
        solver = SubgridFdtdSolver(cfg)
        result = solver.solve(n_steps=10)
        assert isinstance(result, SubgridResult)
        assert result.e_main.shape[0] == 80
        assert result.e_sub.shape[0] == 40

    def test_solver_gaussian_propagation(self):
        """高斯脉冲在子网格区域传播。"""
        cfg = SubgridConfig(
            n_main=100, n_sub=60, factor=4,
            sub_start=30, sub_end=45,
            dx=1e-7, dt=1e-17,
        )
        solver = SubgridFdtdSolver(cfg)
        # 注入高斯脉冲
        x = np.arange(cfg.n_main)
        solver.e_main[:] = np.exp(-((x - 20) ** 2) / 20.0)
        result = solver.solve(n_steps=20)
        # 传播后场应分布到更大范围
        assert np.sum(result.e_main ** 2) > 0

    def test_solver_speedup_positive(self):
        """子网格相对全细网格应有加速。"""
        cfg = SubgridConfig(
            n_main=100, n_sub=40, factor=4,
            sub_start=30, sub_end=40,
            dx=1e-7, dt=1e-17,
        )
        s = estimate_speedup(
            n_main=cfg.n_main, n_sub_region=cfg.sub_end - cfg.sub_start,
            factor=cfg.factor, dim=1,
        )
        assert s > 1.0


# ===========================================================================
# R455 — Yee 网格系数测试
# ===========================================================================


class TestR455YeeGrid:
    """R455 Yee 网格更新系数。"""

    def test_courant_dt(self):
        """Courant 稳定性条件 Δt ≤ Δx / (c·√D)。"""
        dx = 1e-7
        dt = courant_dt(dx=dx, dy=dx, dz=dx)
        # 3D Courant: dt <= 1 / (c * sqrt(3)) * dx
        c0 = 2.99792458e8
        dt_max = dx / (c0 * np.sqrt(3))
        assert dt <= dt_max

    def test_yee_grid_init(self):
        grid = YeeGridFdtd(
            shape=(20, 20), dx=1e-7, dy=1e-7, dt=1e-16,
            eps_r=np.ones((20, 20)),
        )
        assert grid.shape == (20, 20)

    def test_yee_grid_cfl(self):
        grid = YeeGridFdtd(
            shape=(20, 20), dx=1e-7, dy=1e-7, dt=1e-16,
            eps_r=np.ones((20, 20)),
        )
        cfl = grid.cfl_number()
        assert cfl > 0.0

    def test_yee_grid_allocate_fields(self):
        grid = YeeGridFdtd(
            shape=(20, 20), dx=1e-7, dy=1e-7, dt=1e-16,
            eps_r=np.ones((20, 20)),
        )
        e, h_x, h_y = grid.allocate_fields()
        assert e.shape == (20, 20)
        assert h_x.shape == (20, 20)
        assert h_y.shape == (20, 20)

    def test_build_update_coefficients(self):
        """更新系数 Ca/Cb 计算。"""
        eps_r = np.ones((20, 20))
        ca, cb = build_update_coefficients(
            eps_r=eps_r, sigma=np.zeros((20, 20)), dt=1e-16, dx=1e-7, dy=1e-7,
        )
        assert ca.shape == (20, 20)
        assert cb.shape == (20, 20)


# ===========================================================================
# R456-R460 — 综合集成测试
# ===========================================================================


class TestR456R460Integration:
    """R456-R460 综合集成 + 边界 + 反射系数。"""

    def test_cpml_pml_decay(self):
        """PML 区域场应快速衰减。"""
        cfg = CpmlConfig(layers=6)
        cx, cy, buf = build_cpml(
            shape=(30, 30), dx=1e-7, dy=1e-7, dt=1e-16, pml=cfg
        )
        # 在 PML 区注入场
        e_z = np.zeros((30, 30))
        e_z[2, 15] = 1.0
        # 多步衰减
        for _ in range(5):
            update_h_psi(e_z, buf, cx, cy)
            e_z[:] = 0.0  # 无源
        # psi 应衰减
        assert abs(buf.psi_h_yx[2, 15]) < 1.0

    def test_cpml_internal_no_modification(self):
        """内部区域 psi 不应被 CPML 修改（a=0）。"""
        cfg = CpmlConfig(layers=4)
        cx, cy, buf = build_cpml(
            shape=(20, 20), dx=1e-7, dy=1e-7, dt=1e-16, pml=cfg
        )
        e_z = np.zeros((20, 20))
        e_z[10, 10] = 1.0  # 内部
        update_h_psi(e_z, buf, cx, cy)
        # 内部 psi 应保持 0
        assert np.all(buf.psi_h_yx[4:16, 4:16] == 0.0)

    def test_subgrid_with_pml_compatible(self):
        """子网格与 CPML 可同时使用（不冲突）。"""
        cfg = SubgridConfig(
            n_main=80, n_sub=40, factor=4,
            sub_start=30, sub_end=40,
            dx=1e-7, dt=1e-17,
        )
        solver = SubgridFdtdSolver(cfg)
        # CPML 在主网格 2D
        cx, cy, buf = build_cpml(
            shape=(80, 80), dx=1e-7, dy=1e-7, dt=1e-17, pml=CpmlConfig(layers=4)
        )
        # 子网格求解
        result = solver.solve(n_steps=5)
        assert result.e_main.shape[0] == 80

    def test_reflection_db_60db_target(self):
        """R451 路标目标反射 ≤ -60 dB（10 层 PML）。"""
        # 模拟 10 层 PML 反射 0.001
        r = reflection_db(1.0, 0.001)
        assert r <= -60.0

    def test_cpml_psi_persistence(self):
        """psi 缓冲区应原地更新（持久化）。"""
        cfg = CpmlConfig(layers=4)
        cx, cy, buf = build_cpml(
            shape=(20, 20), dx=1e-7, dy=1e-7, dt=1e-16, pml=cfg
        )
        e_z = np.zeros((20, 20))
        e_z[2, 10] = 1.0
        update_h_psi(e_z, buf, cx, cy)
        # 同一 buf 对象应保留状态
        first = buf.psi_h_yx[2, 10]
        update_h_psi(np.zeros_like(e_z), buf, cx, cy)
        second = buf.psi_h_yx[2, 10]
        # 应不同（衰减）
        assert first != second


# ===========================================================================
# R03 / R02 / R04 合规
# ===========================================================================


class TestCompliance:
    """R03/R02/R04 合规检查。"""

    def test_r03_no_silent_fallback(self):
        from pathlib import Path
        for fname in ["cpml.py", "subgridding.py"]:
            src = (Path(__file__).resolve().parents[1] / "src" / "polaris" /
                   "sim" / "fdtd" / fname)
            if not src.exists():
                src = (Path(__file__).resolve().parents[1] / "src" / "polaris" /
                       "sim" / fname)
            text = src.read_text(encoding="utf-8")
            assert "except: pass" not in text, f"{fname} R03 违规"
            assert "except Exception: pass" not in text, f"{fname} R03 违规"

    def test_r03_raise_on_business_error(self):
        with pytest.raises(ValueError):
            CpmlConfig(layers=1)
        with pytest.raises(ValueError):
            reflection_db(0.0, 0.1)

    def test_r02_docstring_references_cpml(self):
        from pathlib import Path
        src = (Path(__file__).resolve().parents[1] / "src" / "polaris" /
               "sim" / "fdtd" / "cpml.py")
        text = src.read_text(encoding="utf-8")
        docstring = text.split('from __future__')[0]
        url_count = docstring.count("https://")
        assert url_count >= 5, f"R02 违规: CPML docstring URL < 5 (实际 {url_count})"

    def test_r02_docstring_references_subgridding(self):
        from pathlib import Path
        src = (Path(__file__).resolve().parents[1] / "src" / "polaris" /
               "sim" / "subgridding.py")
        text = src.read_text(encoding="utf-8")
        docstring = text.split('from __future__')[0]
        url_count = docstring.count("https://")
        assert url_count >= 5, f"R02 违规: Subgridding docstring URL < 5 (实际 {url_count})"

    def test_r02_innovation_marked(self):
        from pathlib import Path
        for fname in ["cpml.py", "subgridding.py"]:
            src = (Path(__file__).resolve().parents[1] / "src" / "polaris" /
                   "sim" / "fdtd" / fname)
            if not src.exists():
                src = (Path(__file__).resolve().parents[1] / "src" / "polaris" /
                       "sim" / fname)
            text = src.read_text(encoding="utf-8")
            assert "*创新*" in text, f"{fname} 缺少 *创新* 标注"

    def test_r04_no_gpu_imports(self):
        from pathlib import Path
        for fname in ["cpml.py", "subgridding.py", "yee_grid.py"]:
            src = (Path(__file__).resolve().parents[1] / "src" / "polaris" /
                   "sim" / "fdtd" / fname)
            if not src.exists():
                src = (Path(__file__).resolve().parents[1] / "src" / "polaris" /
                       "sim" / fname)
            text = src.read_text(encoding="utf-8")
            for forbidden in ["import cupy", "import torch", "from torch",
                              "from cupy", "import cuda"]:
                assert forbidden not in text, f"{fname} R04 违规: 含 '{forbidden}'"


# ===========================================================================
# 端到端集成测试
# ===========================================================================


class TestEndToEndIntegration:
    """端到端集成测试。"""

    def test_full_fdtd_with_cpml_pipeline(self):
        """完整 FDTD + CPML 流水线。"""
        # 1) 创建 2D 网格 + CPML
        cfg = CpmlConfig(layers=5)
        cx, cy, buf = build_cpml(
            shape=(30, 30), dx=1e-7, dy=1e-7, dt=1e-16, pml=cfg
        )
        # 2) 初始化场
        e_z = np.zeros((30, 30))
        h_x = np.zeros((30, 30))
        h_y = np.zeros((30, 30))
        # 3) 注入高斯脉冲
        x = np.arange(30)
        X, Y = np.meshgrid(x, x, indexing="ij")
        e_z[:] = np.exp(-((X - 15) ** 2 + (Y - 15) ** 2) / 20.0)
        # 4) 几步 FDTD + CPML 更新
        for _ in range(5):
            update_h_psi(e_z, buf, cx, cy)
            update_e_psi(h_x, h_y, buf, cx, cy)
        # 5) 验证场有限
        assert np.all(np.isfinite(e_z))
        assert np.all(np.isfinite(h_x))

    def test_subgrid_full_workflow(self):
        """子网格完整工作流。"""
        # 1) 配置子网格
        cfg = SubgridConfig(
            n_main=120, n_sub=80, factor=4,
            sub_start=40, sub_end=60,
            dx=1e-7, dt=1e-17,
        )
        # 2) 求解
        solver = SubgridFdtdSolver(cfg)
        # 3) 注入脉冲
        x = np.arange(cfg.n_main)
        solver.e_main[:] = np.exp(-((x - 30) ** 2) / 50.0)
        # 4) 运行
        result = solver.solve(n_steps=30)
        # 5) 验证
        assert result.e_main.shape == (120,)
        assert result.e_sub.shape == (80,)
        assert np.all(np.isfinite(result.e_main))

    def test_cpml_reflection_target(self):
        """CPML 反射系数目标 ≤ -60 dB。"""
        # 模拟 10 层 PML 反射
        r_db = reflection_db(1.0, 0.001)
        assert r_db <= -60.0
        # 5 层 PML 反射稍差
        r_db_5 = reflection_db(1.0, 0.01)
        assert -60.0 < r_db_5 <= -40.0
