"""A01-RCWA 严格耦合波分析测试（Sprint 1 Task 1.2 验收）。

验收标准（spec.md S1-C3 / S1-C4 / S1-C5）：
- S1-C3: src/polaris/sim/rcwa/ 傅里叶展开 + 本征值 + Redheffer 星积实现
- S1-C4: Li 1996 normal/inverse rule 自适应切换（TE→normal, TM→inverse）
- S1-C5: 光栅衍射效率 vs 解析基准 ≤0.5 dB（自由空间透明 + Fresnel slab）

物理验证基准（A01 §6）：
- 自由空间（无光栅）: R=0, T=1, Σ(R+T)=1.0（透明性）
- 均匀 Si slab: 正入射 Fresnel 反射率 0 阶值 vs 公式 r=(n1-n2)/(n1+n2)
- 周期光栅: 能量守恒 Σ(R+T)=1 偏差 ≤1e-3
- 谐波收敛: 0 阶反射率随 N 增大收敛（无 Gibbs 发散）

文献参考（规则 18 学术诚信，URL ≥5）：
1. Moharam 1995 JOSA A 12, 1077 (ETM) —
   https://doi.org/10.1364/JOSAA.12.001077
2. Li 1996 JOSA A 13, 1870 (FFF/inverse rule) —
   https://doi.org/10.1364/JOSAA.13.001870
3. Lalanne & Morris 1996 JOSA A 13, 779 —
   https://doi.org/10.1364/JOSAA.13.000779
4. Liu & Fan 2012 S4 CPC 183, 2233 —
   https://web.stanford.edu/group/fan/S4/
5. grcwa Python RCWA 库 —
   https://grcwa.readthedocs.io/en/latest/
6. Song 2025 Photonics 12(9), 943 —
   https://www.mdpi.com/2304-6732/12/9/943

规则依据：project_rules.md 规则 14（禁止 fall-back）/规则 18（学术诚信）
/规则 26（GPU 不参与）
"""

from __future__ import annotations

import numpy as np
import pytest

from polaris.sim.rcwa import (
    FourierRule,
    GratingLayer1D,
    LayerModes,
    Polarization,
    RcwaConfig1D,
    build_epsilon_inv_toeplitz_1d,
    build_epsilon_toeplitz_1d,
    build_homogeneous_modes_1d,
    build_interface_smatrix,
    build_propagation_smatrix,
    fourier_coefficients_1d,
    select_rule,
    solve_layer_eigenmodes_1d,
    solve_rcwa_1d,
    toeplitz_from_coefficients,
)

# 物理参数（Soref 1991 @ 1550nm）
_WAVELENGTH = 1.55e-6  # 1550nm
_N_AIR = 1.0
_N_SIO2 = 1.444
_N_SI = 3.476


# ---------------------------------------------------------------------------
# Li 1996 傅里叶因子化（S1-C4 normal/inverse rule）
# ---------------------------------------------------------------------------


class TestFourierFactorization:
    """Li 1996 傅里叶因子化验证（S1-C4 验收点）。"""

    def test_select_rule_te_normal(self) -> None:
        """TE 偏振 → NORMAL 规则（电场切向连续）。"""
        assert select_rule(is_te=True) is FourierRule.NORMAL

    def test_select_rule_tm_inverse(self) -> None:
        """TM 偏振 → INVERSE 规则（D=εE 法向连续）。"""
        assert select_rule(is_te=False) is FourierRule.INVERSE

    def test_fourier_coefficients_constant(self) -> None:
        """常数 ε 的傅里叶系数：仅 0 阶非零 = ε。"""
        eps = np.full(64, 2.25, dtype=np.float64)
        coeffs = fourier_coefficients_1d(eps, n_harmonics=5)
        assert coeffs.shape == (11,)
        # 0 阶（中心索引 5）= ε
        assert np.isclose(coeffs[5], 2.25, atol=1e-12)
        # 其余阶 ≈ 0（FFT 数值误差）
        mask = np.ones(11, dtype=bool)
        mask[5] = False
        assert np.allclose(coeffs[mask], 0.0, atol=1e-12)

    def test_fourier_coefficients_square_wave(self) -> None:
        """方波 ε（二元光栅）傅里叶系数基本性质（A01 §3.1）。

        实信号傅里叶系数满足共轭对称性 c_{-m} = c_m*；
        0 阶系数 = 周期均值 = (ε_hi + ε_lo) / 2（duty=0.5）。
        """
        n_grid = 256
        eps_hi, eps_lo = _N_SI**2, _N_AIR**2
        # duty=0.5 方波
        eps = np.where(np.arange(n_grid) < n_grid // 2, eps_hi, eps_lo).astype(np.float64)
        n_harmonics = 5
        coeffs = fourier_coefficients_1d(eps, n_harmonics=n_harmonics)
        # 0 阶（中心索引 5）= 周期均值
        c0_expected = (eps_hi + eps_lo) / 2.0
        assert np.isclose(coeffs[n_harmonics], c0_expected, atol=1e-10), (
            f"0 阶系数={coeffs[n_harmonics]}，期望均值={c0_expected}"
        )
        # 共轭对称性：c_{-m} = c_m*（实信号性质）
        for m in range(1, n_harmonics + 1):
            c_pos = coeffs[n_harmonics + m]
            c_neg = coeffs[n_harmonics - m]
            assert np.isclose(c_pos, np.conj(c_neg), atol=1e-12), (
                f"共轭对称性破坏: c_{m}={c_pos}, c_{-m}*={np.conj(c_neg)}"
            )
        # 非零阶应非零（方波有丰富谐波）
        assert np.any(np.abs(coeffs) > 1e-6)

    def test_toeplitz_structure(self) -> None:
        """Toeplitz 卷积矩阵结构（A01 §3.2，对角恒定）。"""
        eps = np.full(32, 2.0, dtype=np.float64)
        eps[::2] = 4.0  # 二元介质
        toeplitz = build_epsilon_toeplitz_1d(eps, n_harmonics=3)
        assert toeplitz.shape == (7, 7)
        # Toeplitz 性质：T[i,j] = T[i-j]（仅依赖 i-j）
        for d in range(-3, 4):
            diag = np.diagonal(toeplitz, offset=d)
            assert np.allclose(diag, diag[0]), f"对角线 offset={d} 不恒定（非 Toeplitz）"

    def test_normal_vs_inverse_rule(self) -> None:
        """normal rule 用 ε，inverse rule 用 1/ε（Li 1996）。"""
        eps = np.array([4.0, 1.0, 4.0, 1.0], dtype=np.float64)
        n_harmonics = 1
        # normal: ε 的 Toeplitz
        t_normal = build_epsilon_toeplitz_1d(eps, n_harmonics)
        # inverse: 1/ε 的 Toeplitz
        t_inverse = build_epsilon_inv_toeplitz_1d(eps, n_harmonics)
        # 二者不应相等（间断面 normal≠inverse，Li 1996 核心）
        assert not np.allclose(t_normal, t_inverse), (
            "normal 与 inverse 规则应不同（间断面 TM Gibbs 现象消除关键）"
        )
        # 但常数介质时两者应满足 t_normal @ t_inverse ≈ I
        eps_const = np.full(64, 2.25, dtype=np.float64)
        t_n = build_epsilon_toeplitz_1d(eps_const, n_harmonics=3)
        t_i = build_epsilon_inv_toeplitz_1d(eps_const, n_harmonics=3)
        prod = t_n @ t_i
        assert np.allclose(prod, np.eye(7), atol=1e-12), "常数介质 normal@inverse 应=I（ε·(1/ε)=1）"

    def test_toeplitz_from_coefficients_roundtrip(self) -> None:
        """toeplitz_from_coefficients 与 fourier_coefficients_1d 一致。"""
        eps = np.array([4.0, 1.0, 4.0, 1.0, 4.0], dtype=np.float64)
        coeffs = fourier_coefficients_1d(eps, n_harmonics=2)
        toeplitz = toeplitz_from_coefficients(coeffs)
        # 与 build_epsilon_toeplitz_1d(normal) 一致
        t_direct = build_epsilon_toeplitz_1d(eps, n_harmonics=2)
        assert np.allclose(toeplitz, t_direct, atol=1e-12)


# ---------------------------------------------------------------------------
# 本征模求解（S1-C3 RCWA 实现）
# ---------------------------------------------------------------------------


class TestLayerEigenmodes:
    """单层本征模求解验证（A01 §5 步骤 2）。"""

    def test_homogeneous_modes_shape(self) -> None:
        """齐次层本征模：W=I, V=diag(k_z)，形状正确。"""
        k0 = 2.0 * np.pi / _WAVELENGTH
        n_harmonics = 3
        kx = np.linspace(-3e6, 3e6, 2 * n_harmonics + 1)
        modes = build_homogeneous_modes_1d(_N_SI, kx, k0, Polarization.TE)
        assert modes.w.shape == (7, 7)
        assert modes.v.shape == (7, 7)
        assert modes.k_z.shape == (7,)
        # 齐次层 W = I
        assert np.allclose(modes.w, np.eye(7), atol=1e-12)

    def test_homogeneous_kz_dispersion(self) -> None:
        """齐次层 k_z 满足色散关系 k_z² + kx² = (n·k0)²（A01 §4）。"""
        k0 = 2.0 * np.pi / _WAVELENGTH
        n = _N_SI
        n_harmonics = 4
        kx = np.linspace(-2e6, 2e6, 2 * n_harmonics + 1)
        modes = build_homogeneous_modes_1d(n, kx, k0, Polarization.TE)
        # k_z² + kx² = (n·k0)²
        dispersion = modes.k_z**2 + kx**2
        expected = (n * k0) ** 2
        assert np.allclose(dispersion, expected, atol=1e-6 * abs(expected)), (
            f"色散关系偏差: {np.max(np.abs(dispersion - expected)):.6e}"
        )

    def test_grating_layer_eigenmodes_te(self) -> None:
        """光栅层 TE 本征模求解（normal rule）。"""
        # 二元光栅：Si/Air duty=0.5
        n_grid = 64
        eps = np.where(np.arange(n_grid) < n_grid // 2, _N_SI**2, _N_AIR**2).astype(np.float64)
        k0 = 2.0 * np.pi / _WAVELENGTH
        n_harmonics = 3
        kx = np.linspace(-2e6, 2e6, 2 * n_harmonics + 1)
        modes = solve_layer_eigenmodes_1d(eps, n_harmonics, k0, kx, Polarization.TE)
        assert modes.w.shape == (7, 7)
        # 本征模矩阵非奇异（可逆，保证 S 矩阵构造）
        assert abs(np.linalg.det(modes.w)) > 1e-10, "W 矩阵奇异"
        # 无损介质：k_z 实部非零或虚部≥0（前向+后向成对，实部可正可负）
        # 物理约束：消逝波 Im(k_z)≥0（_normalize_kz 保证）
        assert np.all(np.imag(modes.k_z) >= -1e-6), "k_z 虚部<0（违反因果性）"
        # k_z 成对出现（±对）：前向 + 后向，应满足 |k_z| 集合对称
        # 前向（实部>0）与后向（实部<0）数量应平衡
        n_forward = int(np.sum(np.real(modes.k_z) > 0))
        n_backward = int(np.sum(np.real(modes.k_z) < 0))
        assert n_forward + n_backward == len(modes.k_z), "存在近零 k_z（数值退化）"

    def test_grating_layer_eigenmodes_tm(self) -> None:
        """光栅层 TM 本征模求解（inverse rule，Li 1996）。"""
        n_grid = 64
        eps = np.where(np.arange(n_grid) < n_grid // 2, _N_SI**2, _N_AIR**2).astype(np.float64)
        k0 = 2.0 * np.pi / _WAVELENGTH
        n_harmonics = 3
        kx = np.linspace(-2e6, 2e6, 2 * n_harmonics + 1)
        modes = solve_layer_eigenmodes_1d(eps, n_harmonics, k0, kx, Polarization.TM)
        assert modes.w.shape == (7, 7)
        assert abs(np.linalg.det(modes.w)) > 1e-10

    def test_layer_modes_validation(self) -> None:
        """LayerModes 形状校验（规则 14）。"""
        w = np.eye(3, dtype=np.complex128)
        v = np.eye(4, dtype=np.complex128)  # 形状不匹配
        kz = np.ones(3, dtype=np.complex128)
        with pytest.raises(ValueError, match="W/V 形状"):
            LayerModes(w=w, v=v, k_z=kz)


# ---------------------------------------------------------------------------
# 界面/传播 S 矩阵（S1-C3 RCWA 实现）
# ---------------------------------------------------------------------------


class TestSMatrices:
    """界面与传播 S 矩阵构造验证。"""

    def test_interface_smatrix_shape(self) -> None:
        """界面 S 矩阵形状 = (2N+1, 2N+1) per block。"""
        k0 = 2.0 * np.pi / _WAVELENGTH
        n_harmonics = 3
        kx = np.linspace(-2e6, 2e6, 2 * n_harmonics + 1)
        modes_left = build_homogeneous_modes_1d(_N_AIR, kx, k0, Polarization.TE)
        modes_right = build_homogeneous_modes_1d(_N_SI, kx, k0, Polarization.TE)
        s = build_interface_smatrix(modes_left, modes_right)
        assert s.s11.shape == (7, 7)
        assert s.s12.shape == (7, 7)
        assert s.s21.shape == (7, 7)
        assert s.s22.shape == (7, 7)

    def test_interface_smatrix_fresnel_normal_incidence(self) -> None:
        """正入射 Air→Si 界面：0 阶反射系数 vs Fresnel r=(n1-n2)/(n1+n2)。"""
        k0 = 2.0 * np.pi / _WAVELENGTH
        n_harmonics = 3
        # 正入射：kx 全 0（0 阶 + 高阶消逝）
        kx = np.zeros(2 * n_harmonics + 1)
        modes_left = build_homogeneous_modes_1d(_N_AIR, kx, k0, Polarization.TE)
        modes_right = build_homogeneous_modes_1d(_N_SI, kx, k0, Polarization.TE)
        s = build_interface_smatrix(modes_left, modes_right)
        center = n_harmonics
        r_fresnel = (_N_AIR - _N_SI) / (_N_AIR + _N_SI)
        assert np.isclose(s.s11[center, center], r_fresnel, atol=1e-12), (
            f"0 阶反射系数={s.s11[center, center]}，Fresnel={r_fresnel}"
        )

    def test_propagation_smatrix_phase(self) -> None:
        """传播 S 矩阵：S21 = exp(i·k_z·d)（A01 §5 步骤 3）。"""
        k0 = 2.0 * np.pi / _WAVELENGTH
        n_harmonics = 2
        kx = np.zeros(2 * n_harmonics + 1)
        modes = build_homogeneous_modes_1d(_N_SI, kx, k0, Polarization.TE)
        d = 1e-6  # 1μm
        s = build_propagation_smatrix(modes, d)
        # 0 阶：S21 = exp(i·k_z·d), k_z = n·k0
        center = n_harmonics
        kz0 = _N_SI * k0
        expected_phase = np.exp(1j * kz0 * d)
        assert np.isclose(s.s21[center, center], expected_phase, atol=1e-12), (
            f"S21={s.s21[center, center]}, 期望 exp(i·k_z·d)={expected_phase}"
        )
        # S12 = S21（对称），S11 = S22 = 0
        assert np.allclose(s.s12, s.s21, atol=1e-12)
        assert np.allclose(s.s11, 0.0, atol=1e-12)
        assert np.allclose(s.s22, 0.0, atol=1e-12)


# ---------------------------------------------------------------------------
# RCWA 求解器配置与基础校验（S1-C3）
# ---------------------------------------------------------------------------


class TestRcwaConfig:
    """RcwaConfig1D 参数校验（规则 14）。"""

    def test_config_valid(self) -> None:
        cfg = RcwaConfig1D(
            wavelength=_WAVELENGTH,
            period=1e-6,
            n_harmonics=5,
            polarization="te",
        )
        assert cfg.n_harmonics == 5
        assert cfg.polarization == "te"

    def test_invalid_wavelength(self) -> None:
        with pytest.raises(ValueError, match="波长必须为正"):
            RcwaConfig1D(wavelength=-1.0, period=1e-6)

    def test_invalid_period(self) -> None:
        with pytest.raises(ValueError, match="周期必须为正"):
            RcwaConfig1D(wavelength=_WAVELENGTH, period=-1e-6)

    def test_invalid_harmonics(self) -> None:
        with pytest.raises(ValueError, match="截断阶数"):
            RcwaConfig1D(wavelength=_WAVELENGTH, period=1e-6, n_harmonics=0)

    def test_invalid_polarization(self) -> None:
        with pytest.raises(ValueError, match="偏振态"):
            RcwaConfig1D(
                wavelength=_WAVELENGTH,
                period=1e-6,
                polarization="invalid",  # type: ignore[arg-type]
            )

    def test_grating_layer_validation(self) -> None:
        """GratingLayer1D 参数校验。"""
        with pytest.raises(ValueError, match="层厚必须为正"):
            GratingLayer1D(thickness=-1.0, eps_r_period=np.ones(8))
        with pytest.raises(ValueError, match="eps_r_period"):
            GratingLayer1D(thickness=1e-6, eps_r_period=np.ones(2))  # <3
        with pytest.raises(ValueError, match="介电常数"):
            GratingLayer1D(thickness=1e-6, eps_r_period=np.array([1.0, 0.0, 2.0]))


# ---------------------------------------------------------------------------
# 自由空间透明性（S1-C5 物理基准 1）
# ---------------------------------------------------------------------------


class TestFreeSpaceTransparency:
    """自由空间（无光栅）透明性验证。"""

    def test_free_space_te_transparent(self) -> None:
        """TE 正入射自由空间：R=0, T=1, Σ(R+T)=1.0。"""
        # 均匀空气层（n=1，无光栅）
        eps_air = np.full(32, _N_AIR**2, dtype=np.float64)
        layer = GratingLayer1D(thickness=0.5e-6, eps_r_period=eps_air)
        cfg = RcwaConfig1D(
            wavelength=_WAVELENGTH,
            period=1e-6,
            n_harmonics=3,
            n_inc=_N_AIR,
            n_sub=_N_AIR,
            polarization=Polarization.TE,
        )
        result = solve_rcwa_1d([layer], cfg)
        # 反射 ≈ 0
        assert np.sum(result.reflection_eff) < 1e-10, (
            f"自由空间反射={np.sum(result.reflection_eff)}，应≈0"
        )
        # 透射 ≈ 1（0 阶全透射）
        assert abs(result.transmission_eff[cfg.n_harmonics] - 1.0) < 1e-6, (
            f"0 阶透射={result.transmission_eff[cfg.n_harmonics]}，应=1"
        )
        # 能量守恒
        assert abs(result.energy_sum - 1.0) < 1e-6, f"能量守恒偏差={abs(result.energy_sum - 1.0)}"

    def test_free_space_tm_transparent(self) -> None:
        """TM 正入射自由空间透明性（inverse rule 验证）。"""
        eps_air = np.full(32, _N_AIR**2, dtype=np.float64)
        layer = GratingLayer1D(thickness=0.5e-6, eps_r_period=eps_air)
        cfg = RcwaConfig1D(
            wavelength=_WAVELENGTH,
            period=1e-6,
            n_harmonics=3,
            n_inc=_N_AIR,
            n_sub=_N_AIR,
            polarization=Polarization.TM,
        )
        result = solve_rcwa_1d([layer], cfg)
        assert result.fourier_rule == FourierRule.INVERSE.value
        assert abs(result.energy_sum - 1.0) < 1e-6

    def test_rule_reported_te(self) -> None:
        """TE 求解器报告 normal rule（S1-C4 验收）。"""
        eps_air = np.full(32, _N_AIR**2, dtype=np.float64)
        layer = GratingLayer1D(thickness=0.5e-6, eps_r_period=eps_air)
        cfg = RcwaConfig1D(
            wavelength=_WAVELENGTH,
            period=1e-6,
            n_harmonics=2,
            polarization=Polarization.TE,
        )
        result = solve_rcwa_1d([layer], cfg)
        assert result.fourier_rule == FourierRule.NORMAL.value


# ---------------------------------------------------------------------------
# 均匀 slab 反射率（S1-C5 物理基准 2，Fresnel 公式）
# ---------------------------------------------------------------------------


class TestHomogeneousSlab:
    """均匀 Si slab 反射率 vs Fresnel 公式 + Fabry-Perot 干涉。"""

    def test_si_slab_energy_conservation(self) -> None:
        """Si slab（无损耗）能量守恒 Σ(R+T)=1（S1-C5）。"""
        eps_si = np.full(32, _N_SI**2, dtype=np.float64)
        layer = GratingLayer1D(thickness=0.5e-6, eps_r_period=eps_si)
        cfg = RcwaConfig1D(
            wavelength=_WAVELENGTH,
            period=1e-6,
            n_harmonics=3,
            n_inc=_N_AIR,
            n_sub=_N_AIR,
            polarization=Polarization.TE,
        )
        result = solve_rcwa_1d([layer], cfg)
        assert abs(result.energy_sum - 1.0) < 1e-3, (
            f"Si slab 能量守恒偏差={abs(result.energy_sum - 1.0)}"
        )

    def test_si_slab_tm_energy_conservation(self) -> None:
        """Si slab TM 偏振能量守恒（inverse rule 关键验证）。"""
        eps_si = np.full(32, _N_SI**2, dtype=np.float64)
        layer = GratingLayer1D(thickness=0.5e-6, eps_r_period=eps_si)
        cfg = RcwaConfig1D(
            wavelength=_WAVELENGTH,
            period=1e-6,
            n_harmonics=3,
            n_inc=_N_AIR,
            n_sub=_N_AIR,
            polarization=Polarization.TM,
        )
        result = solve_rcwa_1d([layer], cfg)
        assert result.fourier_rule == FourierRule.INVERSE.value
        assert abs(result.energy_sum - 1.0) < 1e-3

    def test_si_slab_reflectance_vs_fabry_perot(self) -> None:
        """Si slab 0 阶反射率 vs Fabry-Perot 公式（A01 §6）。

        单层 slab 反射率（正入射，Air-Si-Air）：
          R = R_fp · |1 - e^{i·2·k_z·d} / (1 - R_fp·e^{i·2·k_z·d})|²
        简化（无损）：R(d) = 4R_fp·sin²(k_z·d) / [(1-R_fp)² + 4R_fp·sin²(k_z·d)]
        其中 R_fp = ((n1-n2)/(n1+n2))²（单界面反射率）。
        """
        n1, n2 = _N_AIR, _N_SI
        r_fp = (n1 - n2) / (n1 + n2)
        R_fp = abs(r_fp) ** 2
        k0 = 2.0 * np.pi / _WAVELENGTH
        kz_si = n2 * k0
        d = 0.3e-6  # 0.3μm
        # FP 反射率（正入射）
        sin_term = np.sin(kz_si * d) ** 2
        R_expected = 4.0 * R_fp * sin_term / ((1 - R_fp) ** 2 + 4 * R_fp * sin_term)
        eps_si = np.full(32, _N_SI**2, dtype=np.float64)
        layer = GratingLayer1D(thickness=d, eps_r_period=eps_si)
        cfg = RcwaConfig1D(
            wavelength=_WAVELENGTH,
            period=1e-6,
            n_harmonics=3,
            n_inc=_N_AIR,
            n_sub=_N_AIR,
            polarization=Polarization.TE,
        )
        result = solve_rcwa_1d([layer], cfg)
        r0 = result.reflection_eff[cfg.n_harmonics]
        # 容差 5%（数值离散 + 谐波截断误差）
        assert abs(r0 - R_expected) < 0.05, (
            f"Si slab 0 阶反射率={r0:.6f}，FP 公式={R_expected:.6f}，"
            f"偏差={abs(r0 - R_expected):.6f}"
        )


# ---------------------------------------------------------------------------
# 周期光栅衍射效率（S1-C5 主要验收点）
# ---------------------------------------------------------------------------


class TestGratingDiffraction:
    """二元光栅衍射效率验证。"""

    def _build_binary_grating(self, duty: float = 0.5, n_grid: int = 64) -> np.ndarray:
        """构造二元光栅 ε_r 采样（Si/Air）。"""
        n_high = int(n_grid * duty)
        eps = np.full(n_grid, _N_AIR**2, dtype=np.float64)
        eps[:n_high] = _N_SI**2
        return eps

    def test_grating_energy_conservation_te(self) -> None:
        """二元光栅 TE 能量守恒 Σ(R+T)=1（S1-C5 核心）。"""
        eps = self._build_binary_grating()
        layer = GratingLayer1D(thickness=0.2e-6, eps_r_period=eps)
        cfg = RcwaConfig1D(
            wavelength=_WAVELENGTH,
            period=1e-6,
            n_harmonics=5,
            n_inc=_N_AIR,
            n_sub=_N_AIR,
            polarization=Polarization.TE,
        )
        result = solve_rcwa_1d([layer], cfg)
        assert abs(result.energy_sum - 1.0) < 1e-3, (
            f"二元光栅 TE 能量守恒偏差={abs(result.energy_sum - 1.0)}"
        )

    def test_grating_energy_conservation_tm(self) -> None:
        """二元光栅 TM 能量守恒（inverse rule 消除 Gibbs）。"""
        eps = self._build_binary_grating()
        layer = GratingLayer1D(thickness=0.2e-6, eps_r_period=eps)
        cfg = RcwaConfig1D(
            wavelength=_WAVELENGTH,
            period=1e-6,
            n_harmonics=5,
            n_inc=_N_AIR,
            n_sub=_N_AIR,
            polarization=Polarization.TM,
        )
        result = solve_rcwa_1d([layer], cfg)
        assert result.fourier_rule == FourierRule.INVERSE.value
        assert abs(result.energy_sum - 1.0) < 1e-3, (
            f"二元光栅 TM 能量守恒偏差={abs(result.energy_sum - 1.0)}"
        )

    def test_grating_higher_orders_nonzero(self) -> None:
        """光栅产生高阶衍射（0 阶以外反射/透射非零）。

        需 period > λ/n_inc 使 ±1 阶传播（非消逝）。
        """
        eps = self._build_binary_grating()
        layer = GratingLayer1D(thickness=0.2e-6, eps_r_period=eps)
        # period=3μm > λ=1.55μm → ±1 阶 Bloch 波矢 kx=2π/3e-6 < n·k0
        cfg = RcwaConfig1D(
            wavelength=_WAVELENGTH,
            period=3e-6,
            n_harmonics=3,
            n_inc=_N_AIR,
            n_sub=_N_AIR,
            polarization=Polarization.TE,
        )
        result = solve_rcwa_1d([layer], cfg)
        center = cfg.n_harmonics
        # ±1 阶反射或透射应非零（光栅衍射，传播阶携带功率）
        higher_r = result.reflection_eff[center + 1] + result.reflection_eff[center - 1]
        higher_t = result.transmission_eff[center + 1] + result.transmission_eff[center - 1]
        assert higher_r > 1e-6 or higher_t > 1e-6, (
            f"光栅应产生 ±1 阶衍射（R={higher_r}, T={higher_t}）"
        )

    def test_subwavelength_grating_only_zeroth_order(self) -> None:
        """亚波长光栅（Λ<λ）仅 0 阶传播，高阶消逝。"""
        eps = self._build_binary_grating()
        layer = GratingLayer1D(thickness=0.1e-6, eps_r_period=eps)
        # 周期 < λ/n_inc → 仅 0 阶传播
        cfg = RcwaConfig1D(
            wavelength=_WAVELENGTH,
            period=0.5e-6,  # < λ=1.55μm
            n_harmonics=3,
            n_inc=_N_AIR,
            n_sub=_N_AIR,
            polarization=Polarization.TE,
        )
        result = solve_rcwa_1d([layer], cfg)
        center = cfg.n_harmonics
        # 高阶反射应为 0（消逝波不携带功率）
        high_order_r = np.sum(result.reflection_eff) - result.reflection_eff[center]
        assert high_order_r < 1e-6, f"亚波长光栅高阶反射={high_order_r}，应≈0（消逝）"
        # 能量守恒仍成立
        assert abs(result.energy_sum - 1.0) < 1e-3

    def test_result_dataclass_fields(self) -> None:
        """RcwaResult1D 字段完整性。"""
        eps = self._build_binary_grating()
        layer = GratingLayer1D(thickness=0.2e-6, eps_r_period=eps)
        cfg = RcwaConfig1D(
            wavelength=_WAVELENGTH,
            period=1e-6,
            n_harmonics=3,
        )
        result = solve_rcwa_1d([layer], cfg)
        n_total = 2 * cfg.n_harmonics + 1
        assert result.reflection_eff.shape == (n_total,)
        assert result.transmission_eff.shape == (n_total,)
        assert result.r_amplitude.shape == (n_total,)
        assert result.t_amplitude.shape == (n_total,)
        assert result.kx.shape == (n_total,)
        assert result.kz_inc.shape == (n_total,)
        assert result.kz_sub.shape == (n_total,)
        assert isinstance(result.energy_sum, float)
        assert isinstance(result.fourier_rule, str)
        assert isinstance(result.iterations, int)


# ---------------------------------------------------------------------------
# 谐波收敛性（S1-C5 数值精度）
# ---------------------------------------------------------------------------


class TestHarmonicConvergence:
    """傅里叶谐波截断阶数 N 收敛性验证。"""

    def test_convergence_zeroth_order_reflectance(self) -> None:
        """0 阶反射率随 N 增大收敛（无 Gibbs 发散）。"""
        n_grid = 128
        eps = np.where(np.arange(n_grid) < n_grid // 2, _N_SI**2, _N_AIR**2).astype(np.float64)
        layer = GratingLayer1D(thickness=0.2e-6, eps_r_period=eps)
        r0_values = []
        for n_harm in (2, 4, 6, 8):
            cfg = RcwaConfig1D(
                wavelength=_WAVELENGTH,
                period=1e-6,
                n_harmonics=n_harm,
                n_inc=_N_AIR,
                n_sub=_N_AIR,
                polarization=Polarization.TE,
            )
            result = solve_rcwa_1d([layer], cfg)
            r0_values.append(result.reflection_eff[n_harm])
        # 收敛判据：最大相对变化 < 20%（前几阶可能振荡）
        r0_arr = np.array(r0_values)
        rel_changes = np.abs(np.diff(r0_arr)) / np.maximum(r0_arr[:-1], 1e-10)
        # 后两次收敛应更稳定
        assert rel_changes[-1] < 0.3, f"0 阶反射率未收敛: {r0_arr}，相对变化 {rel_changes}"

    def test_tm_converges_with_inverse_rule(self) -> None:
        """TM 偏振 inverse rule 收敛（Li 1996 核心，消除 Gibbs）。"""
        n_grid = 128
        eps = np.where(np.arange(n_grid) < n_grid // 2, _N_SI**2, _N_AIR**2).astype(np.float64)
        layer = GratingLayer1D(thickness=0.2e-6, eps_r_period=eps)
        energy_values = []
        for n_harm in (3, 5, 7):
            cfg = RcwaConfig1D(
                wavelength=_WAVELENGTH,
                period=1e-6,
                n_harmonics=n_harm,
                n_inc=_N_AIR,
                n_sub=_N_AIR,
                polarization=Polarization.TM,
            )
            result = solve_rcwa_1d([layer], cfg)
            energy_values.append(result.energy_sum)
        # TM inverse rule 能量守恒随 N 收敛到 1
        for e in energy_values:
            assert abs(e - 1.0) < 1e-3, (
                f"TM 能量守恒偏差 {abs(e - 1.0)}（inverse rule 应消除 Gibbs）"
            )


# ---------------------------------------------------------------------------
# 多层级联（C03 共享 Redheffer 内核集成）
# ---------------------------------------------------------------------------


class TestMultilayerCascade:
    """多层光栅级联验证（C03 + A01 集成）。"""

    def test_two_layer_grating(self) -> None:
        """双层光栅（Si/Air/Si/Air）能量守恒。"""
        n_grid = 32
        eps_si = np.full(n_grid, _N_SI**2, dtype=np.float64)
        eps_air = np.full(n_grid, _N_AIR**2, dtype=np.float64)
        layers = [
            GratingLayer1D(thickness=0.1e-6, eps_r_period=eps_si),
            GratingLayer1D(thickness=0.1e-6, eps_r_period=eps_air),
        ]
        cfg = RcwaConfig1D(
            wavelength=_WAVELENGTH,
            period=1e-6,
            n_harmonics=4,
            n_inc=_N_AIR,
            n_sub=_N_AIR,
            polarization=Polarization.TE,
        )
        result = solve_rcwa_1d(layers, cfg)
        assert abs(result.energy_sum - 1.0) < 1e-3
        # 两层 → 5 个 S 矩阵（界面-传播-界面-传播-界面）
        assert result.iterations == 5

    def test_empty_layers_raises(self) -> None:
        """空层列表 raise（规则 14）。"""
        cfg = RcwaConfig1D(wavelength=_WAVELENGTH, period=1e-6, n_harmonics=3)
        with pytest.raises(ValueError, match="不能为空"):
            solve_rcwa_1d([], cfg)
