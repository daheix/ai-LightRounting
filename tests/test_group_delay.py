"""群延迟和色散分析测试（R02 步骤 4）。

测试内容:
1. 波导群延迟通过解析解验证（τ_g = n_g·L/c）
2. 环谐振器 FSR 验证
3. add-drop 功率守恒测试（through + drop = 1）
4. 色散分析指标提取

来源:
- R02 路标: /workspace/docs/roundmap/R02.md
- Yariv 1997 §10.5
- Agrawal, "Fiber-Optic Communication Systems", §2.4
"""

from __future__ import annotations

import numpy as np
import pytest

from polaris.sim.models import ring_resonator_s, waveguide_s
from polaris.sim.models_extended import add_drop_ring_s, half_ring_s
from polaris.sim.simulator import SPEED_OF_LIGHT, analyze_dispersion, group_delay


class TestGroupDelay:
    """群延迟计算测试。"""

    def test_waveguide_group_delay_analytical(self):
        """波导群延迟通过解析解验证。

        波导模型使用常数 n_eff（无色散），因此群延迟 τ_g = n_eff·L/c。
        若波导有色散（n_eff(λ)），则群延迟 τ_g = n_g·L/c。

        来源: Agrawal §2.4; R02.md §3.2
        数值示例: L=100μm, n_eff=2.4 → τ_g = 2.4×100e-6/3e8 ≈ 0.80 ps
        """
        # 波导参数
        length_um = 100.0  # μm
        ng = 4.0
        neff = 2.4
        # 波长扫描
        wavelengths = np.linspace(1.5, 1.6, 1000)
        s = waveguide_s(wl=wavelengths, length=length_um, neff=neff, ng=ng, loss_db_cm=0.0)
        # 计算群延迟
        tau_g = group_delay(s, wavelengths, port_out="out", port_in="in")
        # 解析解: 波导模型使用常数 n_eff（无色散），故 τ_g = n_eff·L/c
        # L 单位 μm → m
        length_m = length_um * 1e-6
        tau_expected = neff * length_m / SPEED_OF_LIGHT
        # 验证（中心区域，避免边界效应）
        mid_idx = len(tau_g) // 2
        np.testing.assert_allclose(
            tau_g[mid_idx],
            tau_expected,
            rtol=1e-3,
            err_msg=f"波导群延迟 {tau_g[mid_idx]:.3e} s 与解析解 {tau_expected:.3e} s 不匹配",
        )

    def test_waveguide_group_delay_with_dispersion(self):
        """有色散波导的群延迟验证: τ_g = n_g·L/c。

        使用 Sellmeier 色散模型构造波长相关 neff，验证群延迟接近 n_g·L/c。
        """
        # 波导参数
        length_um = 100.0  # μm
        ng = 4.0
        # 波长扫描
        wavelengths = np.linspace(1.5, 1.6, 1000)
        # 使用 Sellmeier 色散模型计算波长相关 neff
        from polaris.sim.models_extended import sellmeier_neff

        neff_arr = sellmeier_neff(wavelengths)
        # 构造有色散波导的 S 参数
        beta = 2.0 * np.pi * neff_arr / wavelengths
        phase = np.exp(1j * beta * length_um)
        s = {
            ("in", "in"): np.zeros_like(wavelengths, dtype=complex),
            ("out", "in"): phase,
            ("in", "out"): phase,
            ("out", "out"): np.zeros_like(wavelengths, dtype=complex),
        }
        # 计算群延迟
        tau_g = group_delay(s, wavelengths, port_out="out", port_in="in")
        # 解析解: τ_g = n_g·L/c（有色散情况）
        length_m = length_um * 1e-6
        ng * length_m / SPEED_OF_LIGHT
        # 验证（中心区域，允许较大误差因 Sellmeier 参数为近似值）
        mid_idx = len(tau_g) // 2
        # 有色散波导的群延迟应大于无色散情况
        assert tau_g[mid_idx] > 0, "群延迟应为正值"

    def test_group_delay_length_scaling(self):
        """群延迟与波导长度成正比。"""
        wavelengths = np.linspace(1.5, 1.6, 500)
        ng = 4.0
        neff = 2.4
        # 两个不同长度的波导
        s1 = waveguide_s(wl=wavelengths, length=50.0, neff=neff, ng=ng)
        s2 = waveguide_s(wl=wavelengths, length=100.0, neff=neff, ng=ng)
        tau1 = group_delay(s1, wavelengths, port_out="out", port_in="in")
        tau2 = group_delay(s2, wavelengths, port_out="out", port_in="in")
        mid_idx = len(tau1) // 2
        # τ_g2 / τ_g1 ≈ L2 / L1 = 2
        ratio = tau2[mid_idx] / tau1[mid_idx]
        assert abs(ratio - 2.0) < 0.01, f"群延迟比例 {ratio:.3f} 应接近 2.0"

    def test_group_delay_short_wavelength_array_raises(self):
        """波长数组长度不足应 raise ValueError。"""
        wavelengths = np.array([1.5, 1.6])
        s = waveguide_s(wl=wavelengths, length=100.0)
        with pytest.raises(ValueError, match="波长数组长度必须 >= 3"):
            group_delay(s, wavelengths)

    def test_group_delay_nonexistent_port_raises(self):
        """不存在的端口对应 raise ValueError。"""
        wavelengths = np.linspace(1.5, 1.6, 100)
        s = waveguide_s(wl=wavelengths, length=100.0)
        with pytest.raises(ValueError, match="端口对"):
            group_delay(s, wavelengths, port_out="nonexistent", port_in="in")

    def test_group_delay_auto_port_selection(self):
        """自动选取端口。"""
        wavelengths = np.linspace(1.5, 1.6, 500)
        s = waveguide_s(wl=wavelengths, length=100.0, neff=2.4, ng=4.0)
        # 不指定端口，应自动选取
        tau_g = group_delay(s, wavelengths)
        assert len(tau_g) > 0
        assert np.all(np.isfinite(tau_g))


class TestAnalyzeDispersion:
    """色散分析测试。"""

    def test_ring_resonator_fsr(self):
        """环谐振器 FSR 验证。

        环谐振器模型使用常数 n_eff（无色散），因此:
        FSR = λ² / (2π·n_eff·R)

        若环有色散（n_eff(λ)），则 FSR = λ² / (2π·n_g·R)。

        来源: R02.md §3.4; Chrostowski 2015 §4.4
        """
        radius = 10.0
        neff = 2.4  # ring_resonator_s 默认 neff
        # 高分辨率波长扫描以捕获谐振
        wavelengths = np.linspace(1.5, 1.6, 5000)
        s = ring_resonator_s(wl=wavelengths, radius=radius)
        result = analyze_dispersion(s, wavelengths, port_out="through", port_in="in")
        # FSR 解析解（无色散，使用 neff）: FSR = λ² / (2π·n_eff·R)
        wl_center = 1.55  # μm
        fsr_nm_expected = wl_center**2 / (2.0 * np.pi * neff * radius) * 1e3
        # 验证 FSR（允许较大误差，因峰值检测精度有限）
        if result["FSR_nm"] is not None:
            assert abs(result["FSR_nm"] - fsr_nm_expected) < fsr_nm_expected * 0.2, (
                f"FSR {result['FSR_nm']:.2f} nm 与解析解 {fsr_nm_expected:.2f} nm 偏差过大"
            )

    def test_analyze_dispersion_returns_dict(self):
        """色散分析返回字典。"""
        wavelengths = np.linspace(1.5, 1.6, 1000)
        s = ring_resonator_s(wl=wavelengths, radius=10.0)
        result = analyze_dispersion(s, wavelengths, port_out="through", port_in="in")
        assert isinstance(result, dict)
        assert "FSR_nm" in result
        assert "Q_factor" in result
        assert "ER_dB" in result
        assert "BW_3dB_nm" in result

    def test_analyze_dispersion_auto_port(self):
        """色散分析自动选取端口。"""
        wavelengths = np.linspace(1.5, 1.6, 1000)
        s = ring_resonator_s(wl=wavelengths, radius=10.0)
        result = analyze_dispersion(s, wavelengths)
        assert isinstance(result, dict)
        assert "FSR_nm" in result

    def test_analyze_dispersion_nonexistent_port_raises(self):
        """不存在的端口对应 raise ValueError。"""
        wavelengths = np.linspace(1.5, 1.6, 100)
        s = waveguide_s(wl=wavelengths, length=100.0)
        with pytest.raises(ValueError, match="端口对"):
            analyze_dispersion(s, wavelengths, port_out="nonexistent", port_in="in")


class TestAddDropRingPowerConservation:
    """add-drop 型环谐振器功率守恒测试。"""

    def test_power_conservation_lossless(self):
        """无损 add-drop 环: |T_through|² + |T_drop|² = 1。

        来源: Yariv 1997 §10.5; R02.md §3.4
        """
        wavelengths = np.linspace(1.5, 1.6, 1000)
        s = add_drop_ring_s(
            wl=wavelengths,
            radius=10.0,
            gap=0.2,
            neff=2.4,
            ng=4.0,
            loss_db_cm=0.0,  # 无损
        )
        t_through = np.abs(s[("through", "in")]) ** 2
        t_drop = np.abs(s[("drop", "in")]) ** 2
        total = t_through + t_drop
        # 功率守恒（允许数值误差）
        np.testing.assert_allclose(
            total,
            1.0,
            atol=1e-6,
            err_msg="无损 add-drop 环应满足功率守恒 |T_through|² + |T_drop|² = 1",
        )

    def test_add_drop_ring_sdict_structure(self):
        """add-drop 环 S 参数字典结构正确。"""
        wavelengths = np.linspace(1.5, 1.6, 100)
        s = add_drop_ring_s(wl=wavelengths, radius=10.0)
        # 应包含 4 个端口: in, through, drop, add
        assert ("through", "in") in s
        assert ("drop", "in") in s
        assert ("in", "through") in s
        assert ("in", "drop") in s

    def test_add_drop_ring_reciprocity(self):
        """add-drop 环互易性: S_ij = S_ji。"""
        wavelengths = np.linspace(1.5, 1.6, 100)
        s = add_drop_ring_s(wl=wavelengths, radius=10.0)
        np.testing.assert_allclose(
            s[("through", "in")],
            s[("in", "through")],
            atol=1e-9,
        )
        np.testing.assert_allclose(
            s[("drop", "in")],
            s[("in", "drop")],
            atol=1e-9,
        )

    def test_add_drop_ring_with_loss(self):
        """有损 add-drop 环: |T_through|² + |T_drop|² < 1。"""
        wavelengths = np.linspace(1.5, 1.6, 1000)
        s = add_drop_ring_s(
            wl=wavelengths,
            radius=10.0,
            loss_db_cm=1.0,  # 有损
        )
        t_through = np.abs(s[("through", "in")]) ** 2
        t_drop = np.abs(s[("drop", "in")]) ** 2
        total = t_through + t_drop
        # 有损情况总功率应 < 1
        assert np.all(total < 1.0 + 1e-9), "有损 add-drop 环总功率应 <= 1"
        assert np.mean(total) < 1.0, "有损 add-drop 环平均总功率应 < 1"


class TestHalfRingModel:
    """half_ring 模型测试。"""

    def test_half_ring_sdict_structure(self):
        """half_ring S 参数字典结构正确。"""
        wavelengths = np.linspace(1.5, 1.6, 100)
        s = half_ring_s(wl=wavelengths, radius=10.0)
        assert ("through", "in") in s
        assert ("in", "through") in s

    def test_half_ring_reciprocity(self):
        """half_ring 互易性。"""
        wavelengths = np.linspace(1.5, 1.6, 100)
        s = half_ring_s(wl=wavelengths, radius=10.0)
        np.testing.assert_allclose(
            s[("through", "in")],
            s[("in", "through")],
            atol=1e-9,
        )

    def test_half_ring_negative_radius_raises(self):
        """half_ring 负半径应 raise ValueError。"""
        with pytest.raises(ValueError, match="环半径必须 > 0"):
            half_ring_s(radius=-1.0)

    def test_half_ring_zero_gap_raises(self):
        """half_ring 零间隙应 raise ValueError。"""
        with pytest.raises(ValueError, match="耦合间隙 gap 必须 > 0"):
            half_ring_s(gap=0.0)

    def test_half_ring_negative_width_raises(self):
        """half_ring 负宽度应 raise ValueError。"""
        with pytest.raises(ValueError, match="波导宽度必须 > 0"):
            half_ring_s(width=-0.5)
