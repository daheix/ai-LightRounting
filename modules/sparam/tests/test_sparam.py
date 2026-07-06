"""polaris-sparam 子模块深度测试（v5.0 扩展版）。

覆盖全部 9 个公开 API（``__all__``）:
- port_key: 端口对字符串键格式
- waveguide_s: 波导传播 S 参数（相位 + 损耗）
- mmi_1x2_s: MMI 1x2 3dB 分束器（功率守恒 + π/2 相位）
- mmi_2x2_s: MMI 2x2 bar/cross 分束器
- grating_coupler_s: 光栅耦合器高斯波长响应
- ring_resonator_s: 全通型单总线环谐振器（Lorentzian 谐振）
- directional_coupler_s: 定向耦合器（耦合模理论）
- simulate_mzi_sparam: MZI Bar 端波长扫描 + 谐振/消光比
- compute_clements_unitary: Clements 网格 M×M 酉矩阵构造

测试类别:
- 物理量守恒（功率守恒、互易性 S_ij=S_ji、酉性 U·U†=I）
- 解析公式验证（直接对照 S = exp(-α·L/2 + j·2π·neff·L/λ) 等闭式解）
- 边界条件（无损 / 零长度 / 零耦合 / 全耦合）
- R03 禁止 fall-back: 非法参数必须 raise
- R05 回归防护: 阻止已修 Bug 复发

来源（R02 学术诚信，≥5 个文献 URL）:
- Saleh & Teich, "Fundamentals of Photonics", Wiley 2019, §4.4（MZI 传输率）
  https://www.wiley.com/en-us/Fundamentals+of+Photonics%2C+3rd+Edition-p-9781119303930
- Clements et al., "Optimal design for universal multiport interferometers",
  Optica 3(12), 1460-1465 (2016)
  https://opg.optica.org/optica/fulltext.cfm?uri=optica-3-12-1460
- Soldano & Pennings, "Optical multi-mode interference devices",
  J. Lightwave Technol. 13(4), 1995
  https://ieeexplore.ieee.org/document/374358
- SiEPIC EBeam PDK https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- Simphony MZI 教程
  https://simphonyphotonics.readthedocs.io/en/stable/tutorials/mzi.html
- Yariv, "Optical Electronics in Modern Communications", 1997 §10.5（环谐振器）
  https://doi.org/10.1093/oso/9780195106266.001.0001
- Yariv & Yeh, "Optical Waves in Crystals", Wiley 1984, Ch.13（耦合模理论）
  https://www.wiley.com/en-us/Optical+Waves+in+Crystals
- Reck et al., PRL 73, 58 (1994)（分束器酉矩阵）
  https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.73.58
- Chrostowski & Hochberg, "Silicon Photonics Design", Cambridge 2015
  https://www.cambridge.org/core/search?searchField=isbn&searchTerms=1107007731

合规: R02 学术诚信 / R03 禁止 fall-back / R04 纯 NumPy / R05 无 TODO。
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

import polaris_sparam  # noqa: E402
from polaris_sparam import (  # noqa: E402
    compute_clements_unitary,
    directional_coupler_s,
    grating_coupler_s,
    mmi_1x2_s,
    mmi_2x2_s,
    port_key,
    ring_resonator_s,
    simulate_mzi_sparam,
    waveguide_s,
)

# 源码用 4.343 近似 10·log10(e)=4.34294...，故功率衰减相对偏差 ~1e-5
_WAVEGUIDE_LOSS_REL_TOL = 1e-4


# ===========================================================================
# port_key
# ===========================================================================
class TestPortKey:
    """port_key 格式与可逆性测试。"""

    def test_port_key_format_and_type(self):
        """port_key 应返回 str((out, in)) 形式，类型为 str（JSON 友好）。"""
        key = port_key("out", "in")
        assert key == "('out', 'in')"
        assert isinstance(key, str)
        assert port_key("out1", "in2") == "('out1', 'in2')"

    def test_port_key_eval_roundtrip(self):
        """键应可被 eval 还原为 tuple（与源码 docstring 一致）。"""
        key = port_key("out1", "in2")
        parsed = eval(key)
        assert parsed == ("out1", "in2")
        assert isinstance(parsed, tuple)


# ===========================================================================
# waveguide_s
# ===========================================================================
class TestWaveguideS:
    """波导传播 S 参数模型测试。

    公式: S = exp(-α·L/2 + j·2π·neff·L/λ)
        α [1/μm] = loss_db_cm / 4.343 / 1e4
    """

    def test_length_zero_unit_transmission(self):
        """长度 0 → S=1+0j（无衰减无相位）。"""
        result = waveguide_s([1.55], length_um=0.0, neff=2.4, loss_db_cm=3.0)
        s = result[port_key("out", "in")][0]
        assert math.isclose(s.real, 1.0, rel_tol=1e-12)
        assert math.isclose(s.imag, 0.0, abs_tol=1e-12)
        assert math.isclose(abs(s), 1.0, rel_tol=1e-12)

    def test_lossless_unit_power(self):
        """无损波导 |S|² = 1（功率守恒）。"""
        s = waveguide_s([1.55], length_um=100.0, neff=2.4, loss_db_cm=0.0)
        power = abs(s[port_key("out", "in")][0]) ** 2
        assert math.isclose(power, 1.0, rel_tol=1e-12)

    def test_lossy_power_attenuation(self):
        """有损波导功率衰减: |S|² = exp(-loss_db_cm·L_cm/4.343)（源码用 4.343 近似）。"""
        # L=100μm=0.01cm, loss_db_cm=3.0
        # 源码: |S|² = exp(-α·L) = exp(-loss_db_cm·L_cm/4.343)
        s = waveguide_s([1.55], length_um=100.0, neff=2.4, loss_db_cm=3.0)
        power = abs(s[port_key("out", "in")][0]) ** 2
        expected = math.exp(-3.0 * 0.01 / 4.343)
        assert math.isclose(power, expected, rel_tol=_WAVEGUIDE_LOSS_REL_TOL)

    def test_phase_correctness(self):
        """相位 φ = 2π·neff·L/λ 解析验证（取 L=λ/neff 使 φ=2π，S 实数=1）。"""
        length = 1.55 / 2.4  # 使 2π·neff·L/λ = 2π
        s = waveguide_s([1.55], length_um=length, neff=2.4, loss_db_cm=0.0)
        val = s[port_key("out", "in")][0]
        # φ = 2π → e^{j2π} = 1
        assert math.isclose(val.real, 1.0, rel_tol=1e-9)
        assert abs(val.imag) < 1e-9

    def test_reciprocity_no_reflection_multi_wavelength(self):
        """互易性 S_out_in==S_in_out、无反射 S_in_in==0、多波长等长返回。"""
        wl = [1.50, 1.55, 1.60, 1.65]
        s = waveguide_s(wl, length_um=50.0, neff=2.4, loss_db_cm=2.0)
        # 互易
        assert s[port_key("out", "in")] == s[port_key("in", "out")]
        # 无反射
        assert all(v == 0 for v in s[port_key("in", "in")])
        assert all(v == 0 for v in s[port_key("out", "out")])
        # 多波长等长
        assert len(s[port_key("out", "in")]) == 4
        assert all(isinstance(v, complex) for v in s[port_key("out", "in")])

    def test_invalid_params_raises(self):
        """非法参数 raise ValueError（R03 禁止 fall-back）。"""
        with pytest.raises(ValueError, match="波导长度"):
            waveguide_s([1.55], length_um=-1.0)
        with pytest.raises(ValueError, match="neff"):
            waveguide_s([1.55], length_um=10.0, neff=0.0)
        with pytest.raises(ValueError, match="loss_db_cm"):
            waveguide_s([1.55], length_um=10.0, loss_db_cm=-1.0)
        with pytest.raises(ValueError, match="波长"):
            waveguide_s([0.0], length_um=10.0)
        with pytest.raises(ValueError, match="波长"):
            waveguide_s([-1.55], length_um=10.0)


# ===========================================================================
# mmi_1x2_s
# ===========================================================================
class TestMmi1x2:
    """MMI 1x2 S 参数模型测试。

    公式: S = sqrt(10^(-il/10)/2) · exp(j·π/2)
    """

    def test_power_split_and_conservation(self):
        """3dB 等功分束 + 功率守恒 P_out1+P_out2 = 10^(-il/10)。"""
        il_db = 0.4
        mmi = mmi_1x2_s([1.55], insertion_loss_db=il_db)
        p1 = abs(mmi[port_key("out1", "in")][0]) ** 2
        p2 = abs(mmi[port_key("out2", "in")][0]) ** 2
        assert math.isclose(p1, p2, rel_tol=1e-12)
        assert math.isclose(p1 + p2, 10.0 ** (-il_db / 10.0), rel_tol=1e-9)

    def test_pi2_phase_and_lossless_split(self):
        """MMI 固有 π/2 相位（S 纯虚数）+ 零插损每输出 |S|²=1/2。"""
        # 默认参数 π/2 相位
        mmi = mmi_1x2_s([1.55])
        val = mmi[port_key("out1", "in")][0]
        assert abs(val.real) < 1e-12
        assert math.isclose(val.imag, abs(val), rel_tol=1e-9)
        # 零插损 3dB
        mmi0 = mmi_1x2_s([1.55], insertion_loss_db=0.0)
        p1 = abs(mmi0[port_key("out1", "in")][0]) ** 2
        assert math.isclose(p1, 0.5, rel_tol=1e-12)

    def test_reciprocity_no_reflection(self):
        """互易性 + 对角/交叉反射项为 0。"""
        mmi = mmi_1x2_s([1.55, 1.60])
        assert mmi[port_key("out1", "in")] == mmi[port_key("in", "out1")]
        assert mmi[port_key("out2", "in")] == mmi[port_key("in", "out2")]
        for diag in [("in", "in"), ("out1", "out1"), ("out2", "out2"),
                     ("out1", "out2"), ("out2", "out1")]:
            assert all(v == 0 for v in mmi[port_key(*diag)])

    def test_invalid_insertion_loss_raises(self):
        """负插损应 raise ValueError。"""
        with pytest.raises(ValueError, match="insertion_loss_db"):
            mmi_1x2_s([1.55], insertion_loss_db=-0.1)


# ===========================================================================
# mmi_2x2_s
# ===========================================================================
class TestMmi2x2:
    """MMI 2x2 S 参数模型测试。

    bar: 实数（0 相位）, cross: 乘 exp(j·π/2)（纯虚数）
    振幅 = sqrt(10^(-il/10)/2)
    """

    def test_bar_real_cross_imaginary(self):
        """bar 分量实数，cross 分量纯虚数（π/2 相位差）。"""
        mmi = mmi_2x2_s([1.55], insertion_loss_db=0.5)
        bar = mmi[port_key("out1", "in1")][0]
        cross = mmi[port_key("out2", "in1")][0]
        assert abs(bar.imag) < 1e-12
        assert abs(cross.real) < 1e-12

    def test_equal_amplitudes_and_power(self):
        """bar/cross 振幅相等（3dB）+ 每输入功率守恒 = 10^(-il/10)。"""
        il_db = 0.5
        mmi = mmi_2x2_s([1.55], insertion_loss_db=il_db)
        bar = abs(mmi[port_key("out1", "in1")][0])
        cross = abs(mmi[port_key("out2", "in1")][0])
        assert math.isclose(bar, cross, rel_tol=1e-12)
        bar_p = abs(mmi[port_key("out1", "in1")][0]) ** 2
        cross_p = abs(mmi[port_key("out2", "in1")][0]) ** 2
        assert math.isclose(bar_p + cross_p, 10.0 ** (-il_db / 10.0), rel_tol=1e-9)

    def test_reciprocity_no_reflection(self):
        """4 端口互易性 S_ij==S_ji + 4 个对角反射项为 0。"""
        mmi = mmi_2x2_s([1.55, 1.60])
        assert mmi[port_key("out1", "in1")] == mmi[port_key("in1", "out1")]
        assert mmi[port_key("out2", "in2")] == mmi[port_key("in2", "out2")]
        assert mmi[port_key("out2", "in1")] == mmi[port_key("in1", "out2")]
        assert mmi[port_key("out1", "in2")] == mmi[port_key("in2", "out1")]
        for diag in [("in1", "in1"), ("in2", "in2"),
                     ("out1", "out1"), ("out2", "out2")]:
            assert all(v == 0 for v in mmi[port_key(*diag)])

    def test_invalid_insertion_loss_raises(self):
        """负插损应 raise ValueError。"""
        with pytest.raises(ValueError, match="insertion_loss_db"):
            mmi_2x2_s([1.55], insertion_loss_db=-0.1)


# ===========================================================================
# grating_coupler_s
# ===========================================================================
class TestGratingCoupler:
    """光栅耦合器高斯波长响应测试。

    公式: S = sqrt(10^(-il/10)) · exp(-((λ-peak)/bw)²)
    """

    def test_peak_amplitude(self):
        """峰值波长处 |S| = sqrt(10^(-il/10))（高斯归一）。"""
        il_db = 1.9
        gc = grating_coupler_s([1.55], peak_wl=1.55,
                               bandwidth_3db=0.04, insertion_loss_db=il_db)
        amp = abs(gc[port_key("waveguide", "fiber")][0])
        expected = math.sqrt(10.0 ** (-il_db / 10.0))
        assert math.isclose(amp, expected, rel_tol=1e-9)

    def test_off_peak_and_symmetry(self):
        """偏离中心波长振幅下降 + 高斯响应关于峰值对称。"""
        gc = grating_coupler_s([1.54, 1.55, 1.56], peak_wl=1.55,
                               bandwidth_3db=0.04)
        a_left = abs(gc[port_key("waveguide", "fiber")][0])
        a_peak = abs(gc[port_key("waveguide", "fiber")][1])
        a_right = abs(gc[port_key("waveguide", "fiber")][2])
        assert a_peak > a_left  # 峰值最高
        assert math.isclose(a_left, a_right, rel_tol=1e-12)  # 左右对称

    def test_3db_bandwidth(self):
        """3dB 半宽: |λ-peak|=bw 时振幅 = peak·exp(-1)。

        插损 0 → 峰值振幅 1，半宽处 = exp(-1) ≈ 0.368。
        """
        bw = 0.04
        gc = grating_coupler_s([1.55 + bw], peak_wl=1.55,
                               bandwidth_3db=bw, insertion_loss_db=0.0)
        amp_off = abs(gc[port_key("waveguide", "fiber")][0])
        assert math.isclose(amp_off, math.exp(-1.0), rel_tol=1e-9)

    def test_reciprocity_no_reflection(self):
        """互易性 S_wg_fiber==S_fiber_wg + 无反射 S_fiber_fiber==S_wg_wg==0。"""
        gc = grating_coupler_s([1.55, 1.60])
        assert gc[port_key("waveguide", "fiber")] == gc[port_key("fiber", "waveguide")]
        assert all(v == 0 for v in gc[port_key("fiber", "fiber")])
        assert all(v == 0 for v in gc[port_key("waveguide", "waveguide")])

    def test_invalid_params_raises(self):
        """非正带宽 / 负插损应 raise ValueError。"""
        with pytest.raises(ValueError, match="bandwidth_3db"):
            grating_coupler_s([1.55], bandwidth_3db=0.0)
        with pytest.raises(ValueError, match="insertion_loss_db"):
            grating_coupler_s([1.55], insertion_loss_db=-0.1)


# ===========================================================================
# ring_resonator_s
# ===========================================================================
class TestRingResonator:
    """全通型单总线环谐振器测试。

    传输函数: T = (t - a·e^{iφ}) / (1 - t·a·e^{iφ})
        t = √(1-coupling), a = 10^(-loss·L/1e4/20), φ = 2π·neff·L/λ
    """

    def test_sdict_structure_and_no_reflection(self):
        """全通型 4 端口对存在 + 对角反射项为 0。"""
        s = ring_resonator_s([1.55])
        for k in [port_key("through", "in"), port_key("in", "through"),
                  port_key("in", "in"), port_key("through", "through")]:
            assert k in s
        assert all(v == 0 for v in s[port_key("in", "in")])
        assert all(v == 0 for v in s[port_key("through", "through")])

    def test_reciprocity(self):
        """互易性: S_through_in == S_in_through。"""
        wl = np.linspace(1.50, 1.60, 200)
        s = ring_resonator_s(wl.tolist())
        assert s[port_key("through", "in")] == s[port_key("in", "through")]

    def test_resonance_dip_exists(self):
        """高分辨率扫描应出现谐振陷波: min(|T|) < max(|T|)。"""
        # FSR = λ²/(neff·L), L=2π·R, R=10 → FSR ≈ 15.9nm，需精细采样
        wl = np.linspace(1.50, 1.60, 5000)
        s = ring_resonator_s(wl.tolist(), radius_um=10.0, coupling=0.01)
        power = np.abs(np.array(s[port_key("through", "in")])) ** 2
        assert power.min() < power.max(), "环谐振器应出现谐振陷波"
        # 远离谐振 |T| 接近 1（弱损耗 + 弱耦合）
        assert power.max() > 0.999

    def test_invalid_params_raises(self):
        """非正半径 / coupling 越界 / 负损耗应 raise ValueError。"""
        with pytest.raises(ValueError, match="radius_um"):
            ring_resonator_s([1.55], radius_um=0.0)
        with pytest.raises(ValueError, match="coupling"):
            ring_resonator_s([1.55], coupling=-0.1)
        with pytest.raises(ValueError, match="coupling"):
            ring_resonator_s([1.55], coupling=1.1)
        with pytest.raises(ValueError, match="loss_db_cm"):
            ring_resonator_s([1.55], loss_db_cm=-0.1)


# ===========================================================================
# directional_coupler_s
# ===========================================================================
class TestDirectionalCoupler:
    """定向耦合器测试（耦合模理论 CMT）。

    κL = arcsin(√coupling), tau=cos(κL), kappa=sin(κL)·e^{jπ/2}
    """

    def test_power_conservation(self):
        """功率守恒: |tau|² + |kappa|² = 1（CMT 单位性）。"""
        dc = directional_coupler_s([1.55], coupling=0.3)
        tau_p = abs(dc[port_key("out1", "in1")][0]) ** 2
        kappa_p = abs(dc[port_key("out2", "in1")][0]) ** 2
        assert math.isclose(tau_p + kappa_p, 1.0, rel_tol=1e-9)

    def test_3db_coupling_amplitude(self):
        """3dB 耦合 (coupling=0.5): |tau|=|kappa|=1/√2。"""
        dc = directional_coupler_s([1.55], coupling=0.5)
        tau = abs(dc[port_key("out1", "in1")][0])
        kappa = abs(dc[port_key("out2", "in1")][0])
        assert math.isclose(tau, 1.0 / math.sqrt(2.0), rel_tol=1e-9)
        assert math.isclose(kappa, 1.0 / math.sqrt(2.0), rel_tol=1e-9)

    def test_cross_pi2_phase(self):
        """交叉端口 π/2 相位差（CMT 标准）: cross 纯虚数，tau 实数。"""
        dc = directional_coupler_s([1.55], coupling=0.5)
        cross = dc[port_key("out2", "in1")][0]
        tau = dc[port_key("out1", "in1")][0]
        assert abs(cross.real) < 1e-12
        assert abs(tau.imag) < 1e-12

    def test_zero_full_coupling_bounds(self):
        """边界: coupling=0 全直通(tau=1,kappa=0), coupling=1 全交叉(tau=0,kappa=1)。"""
        # 全直通
        dc0 = directional_coupler_s([1.55], coupling=0.0)
        assert math.isclose(abs(dc0[port_key("out1", "in1")][0]), 1.0, rel_tol=1e-12)
        assert math.isclose(abs(dc0[port_key("out2", "in1")][0]), 0.0, abs_tol=1e-12)
        # 全交叉
        dc1 = directional_coupler_s([1.55], coupling=1.0)
        assert math.isclose(abs(dc1[port_key("out1", "in1")][0]), 0.0, abs_tol=1e-12)
        assert math.isclose(abs(dc1[port_key("out2", "in1")][0]), 1.0, rel_tol=1e-12)

    def test_reciprocity_and_invalid_raises(self):
        """4 端口互易性 + 非法参数 raise。"""
        dc = directional_coupler_s([1.55, 1.60], coupling=0.4)
        assert dc[port_key("out1", "in1")] == dc[port_key("in1", "out1")]
        assert dc[port_key("out2", "in1")] == dc[port_key("in1", "out2")]
        assert dc[port_key("out1", "in2")] == dc[port_key("in2", "out1")]
        assert dc[port_key("out2", "in2")] == dc[port_key("in2", "out2")]
        # 非法参数
        with pytest.raises(ValueError, match="coupling"):
            directional_coupler_s([1.55], coupling=-0.1)
        with pytest.raises(ValueError, match="coupling"):
            directional_coupler_s([1.55], coupling=1.5)
        with pytest.raises(ValueError, match="length_um"):
            directional_coupler_s([1.55], length_um=0.0)
        with pytest.raises(ValueError, match="gap_um"):
            directional_coupler_s([1.55], gap_um=0.0)
        with pytest.raises(ValueError, match="neff"):
            directional_coupler_s([1.55], neff=0.0)


# ===========================================================================
# simulate_mzi_sparam
# ===========================================================================
class TestMziSparam:
    """MZI Bar 端波长扫描测试。

    公式: T_bar = R²+T²+2·R·T·cos(Δφ), Δφ=2π·neff·ΔL/λ
    设计: R=0.48, T=0.52, ΔL 使 Bar 端陷波落在 1549nm (m=9)
    """

    def test_default_101_points(self):
        """None 输入默认 1500-1600nm 101 点扫描。"""
        result = simulate_mzi_sparam()
        assert result["n_points"] == 101

    def test_resonance_near_1549nm(self):
        """谐振陷波波长应落在 1548-1550nm（设计目标 1549nm）。"""
        result = simulate_mzi_sparam()
        assert 1548.0 <= result["resonant_wavelength_nm"] <= 1550.0, (
            f"谐振波长应 ≈ 1549nm，得到 {result['resonant_wavelength_nm']}"
        )

    def test_extinction_ratio_properties(self):
        """理论 ER ≈ 27.96dB + 物理 ER ≤ 理论 + 物理 ER > 20dB。"""
        result = simulate_mzi_sparam()
        # 理论 ER = 10·log10(1/(R-T)²), R-T=0.04
        expected_er = 10.0 * math.log10(1.0 / (0.48 - 0.52) ** 2)
        assert math.isclose(result["extinction_ratio_db"], expected_er,
                            rel_tol=1e-6)
        # 物理 ER ≤ 理论 ER（有限采样错过精确极值）
        assert result["extinction_ratio_physical_db"] <= \
               result["extinction_ratio_db"] + 1e-9
        # 物理 ER > 20dB（采样足够精细）
        assert result["extinction_ratio_physical_db"] > 20.0

    def test_t_max_t_min_bounds(self):
        """T_max < 1（采样错过相长点）, T_min ≈ (R-T)²=0.0016（陷波落在 1549nm 采样点）。"""
        result = simulate_mzi_sparam()
        assert result["T_max"] < 1.0 + 1e-9
        assert result["T_max"] > 0.5
        # T_min 应接近 (R-T)² = 0.0016（1549nm 是采样点 1500+49）
        assert result["T_min"] < 0.01, f"T_min 应 ≈ 0.0016, 得到 {result['T_min']}"

    def test_custom_and_invalid_raises(self):
        """自定义波长扫描 + 非法参数 raise。"""
        # 自定义
        wl = [1540.0, 1545.0, 1549.0, 1555.0, 1560.0]
        result = simulate_mzi_sparam(wavelength_nm=wl)
        assert result["n_points"] == 5
        # 点数 < 2
        with pytest.raises(ValueError, match="扫描点数"):
            simulate_mzi_sparam(wavelength_nm=[1550.0])
        # 非正波长
        with pytest.raises(ValueError, match="波长"):
            simulate_mzi_sparam(wavelength_nm=[1500.0, -1600.0])
        # 标量波长（size<2）
        with pytest.raises(ValueError):
            simulate_mzi_sparam(wavelength_nm=1550.0)


# ===========================================================================
# compute_clements_unitary
# ===========================================================================
class TestClementsUnitary:
    """Clements 酉矩阵分解测试。

    分束器 2×2 酉 U_BS(θ,φ) = [[cos θ, -e^{-iφ}sin θ],[e^{iφ}sin θ, cos θ]]
    """

    def test_4x4_unitarity(self):
        """4×4 酉性误差 < 1e-10（默认参数）。"""
        result = compute_clements_unitary(n_modes=4)
        U = np.array(result["unitary"], dtype=complex)
        assert U.shape == (4, 4)
        assert result["unitarity_error"] < 1e-10
        assert result["is_unitary"] is True
        # 独立验证 U·U† = I
        err = float(np.max(np.abs(U @ U.conj().T - np.eye(4))))
        assert err < 1e-10

    def test_reproducibility_and_various_modes(self):
        """固定种子 42 可复现 + 不同模式数（1,2,3,5,8）均满足酉性。"""
        # 可复现
        r1 = compute_clements_unitary(n_modes=4)
        r2 = compute_clements_unitary(n_modes=4)
        np.testing.assert_array_equal(
            np.array(r1["unitary"], dtype=complex),
            np.array(r2["unitary"], dtype=complex),
        )
        # 不同模式数酉性
        for n in [1, 2, 3, 5, 8]:
            result = compute_clements_unitary(n_modes=n)
            U = np.array(result["unitary"], dtype=complex)
            assert U.shape == (n, n)
            err = float(np.max(np.abs(U @ U.conj().T - np.eye(n))))
            assert err < 1e-10, f"n_modes={n} 酉性误差 {err} ≥ 1e-10"
        # n_modes=1 边界: U=[[1]]
        r1m = compute_clements_unitary(n_modes=1)
        U1 = np.array(r1m["unitary"], dtype=complex)
        assert U1.shape == (1, 1)
        assert math.isclose(U1[0, 0].real, 1.0, rel_tol=1e-12)

    def test_invalid_and_list_type(self):
        """n_modes<1 raise + 返回 list[list[Python complex]]。"""
        with pytest.raises(ValueError, match="n_modes"):
            compute_clements_unitary(n_modes=0)
        with pytest.raises(ValueError, match="n_modes"):
            compute_clements_unitary(n_modes=-1)
        # 返回类型
        result = compute_clements_unitary(n_modes=3)
        U = result["unitary"]
        assert isinstance(U, list)
        assert isinstance(U[0], list)
        assert isinstance(U[0][0], complex)


# ===========================================================================
# 模块元信息
# ===========================================================================
class TestModuleMetadata:
    """子模块元信息与导出测试。"""

    def test_version_is_5_0_0(self):
        """子模块版本号 5.0.0（7 子模块统一）。"""
        assert polaris_sparam.__version__ == "5.0.0"

    def test_all_exports_complete(self):
        """__all__ 应包含全部 9 个公开 API + __version__。"""
        expected = {
            "waveguide_s", "mmi_1x2_s", "mmi_2x2_s", "grating_coupler_s",
            "ring_resonator_s", "directional_coupler_s",
            "simulate_mzi_sparam", "compute_clements_unitary",
            "port_key", "__version__",
        }
        assert set(polaris_sparam.__all__) == expected
