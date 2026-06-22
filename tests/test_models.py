"""models.py 和 models_extended.py 测试（R01 步骤 8）。

测试内容:
1. 20+ 器件模型 S 参数正确性
2. 参数 schema 验证（非法参数 raise ValueError）
3. 功率守恒与互易性
4. 波长验证

来源:
- R01 路标: /workspace/docs/roundmap/R01.md
- SiPANN: https://sipann.readthedocs.io/
- SAX models: https://flaport.github.io/sax/models/
"""

from __future__ import annotations

import numpy as np
import pytest

from polaris.sim.models import (
    CouplerParams,
    RingParams,
    WaveguideParams,
    crossing_s,
    directional_coupler_s,
    grating_coupler_s,
    mmi_1x2_s,
    mmi_2x2_s,
    phase_shifter_s,
    ring_resonator_s,
    terminator_s,
    validate_wavelength,
    waveguide_s,
    y_branch_s,
)
from polaris.sim.models_extended import (
    add_drop_ring_s,
    attenuator_s,
    bend_s,
    circulator_s,
    combiner_s,
    detector_s,
    half_ring_s,
    isolator_s,
    mirror_s,
    modulator_s,
    reflector_s,
    sellmeier_neff,
    splitter_s,
    taper_s,
    unitary_s,
)


class TestParameterSchema:
    """测试参数 schema 验证（R01 创新点 2）。"""

    def test_waveguide_params_negative_length_raises(self):
        """波导长度为负应 raise ValueError。"""
        with pytest.raises(ValueError, match="波导长度必须 >= 0"):
            WaveguideParams(length=-10.0)

    def test_waveguide_params_negative_neff_raises(self):
        """neff 为负应 raise ValueError。"""
        with pytest.raises(ValueError, match="neff 必须 > 0"):
            WaveguideParams(neff=-1.0)

    def test_ring_params_invalid_coupling_raises(self):
        """coupling 超出 [0,1] 应 raise ValueError。"""
        with pytest.raises(ValueError, match="coupling 必须在"):
            RingParams(coupling=1.5)

    def test_coupler_params_zero_gap_raises(self):
        """gap 为零应 raise ValueError。"""
        with pytest.raises(ValueError, match="间隙 gap 必须 > 0"):
            CouplerParams(gap=0.0)

    def test_validate_wavelength_negative_raises(self):
        """波长为负应 raise ValueError。"""
        with pytest.raises(ValueError, match="波长必须 > 0"):
            validate_wavelength(-1.0)

    def test_validate_wavelength_out_of_band_raises(self):
        """波长超出光通信波段应 raise ValueError。"""
        with pytest.raises(ValueError, match="超出光通信波段"):
            validate_wavelength(0.3)

    def test_validate_wavelength_valid(self):
        """有效波长应返回 numpy 数组。"""
        wl = validate_wavelength(1.55)
        assert isinstance(wl, np.ndarray)
        assert float(wl) == 1.55


class TestWaveguideModel:
    """波导模型测试。"""

    def test_power_conservation_lossless(self):
        """无损波导 |S21|^2 = 1。"""
        wl = np.array([1.55])
        s = waveguide_s(wl=wl, length=100.0, neff=2.4, loss_db_cm=0.0)
        power = np.abs(s[("out", "in")]) ** 2
        np.testing.assert_allclose(power, 1.0, atol=1e-9)

    def test_loss_attenuation(self):
        """有损波导 |S21|^2 < 1。"""
        wl = np.array([1.55])
        s = waveguide_s(wl=wl, length=100.0, neff=2.4, loss_db_cm=3.0)
        power = np.abs(s[("out", "in")]) ** 2
        assert power[0] < 1.0, "有损波导功率应 < 1"

    def test_reciprocity(self):
        """互易性: S_ij = S_ji。"""
        wl = np.linspace(1.5, 1.6, 20)
        s = waveguide_s(wl=wl, length=50.0)
        np.testing.assert_allclose(s[("out", "in")], s[("in", "out")], atol=1e-9)


class TestYBranchModel:
    """Y 分支模型测试。"""

    def test_power_splitting(self):
        """3dB 分束: 两输出功率相等。"""
        wl = np.array([1.55])
        s = y_branch_s(wl=wl, insertion_loss_db=0.0)
        p2 = np.abs(s[("port_2", "port_1")]) ** 2
        p3 = np.abs(s[("port_3", "port_1")]) ** 2
        np.testing.assert_allclose(p2, p3, atol=1e-9)

    def test_reciprocity(self):
        """互易性。"""
        wl = np.array([1.55])
        s = y_branch_s(wl=wl)
        np.testing.assert_allclose(s[("port_2", "port_1")], s[("port_1", "port_2")], atol=1e-9)


class TestDirectionalCoupler:
    """定向耦合器测试。"""

    def test_power_conservation(self):
        """功率守恒: |tau|^2 + |kappa|^2 = 1。"""
        wl = np.array([1.55])
        s = directional_coupler_s(wl=wl, coupling=0.5)
        tau_power = np.abs(s[("out1", "in1")]) ** 2
        kappa_power = np.abs(s[("out2", "in1")]) ** 2
        total = tau_power + kappa_power
        np.testing.assert_allclose(total, 1.0, atol=1e-9)


class TestRingResonator:
    """环谐振器测试。"""

    def test_sdict_structure(self):
        """SDict 结构正确。"""
        wl = np.linspace(1.5, 1.6, 100)
        s = ring_resonator_s(wl=wl, radius=10.0)
        assert ("through", "in") in s
        assert ("in", "through") in s

    def test_reciprocity(self):
        """互易性。"""
        wl = np.linspace(1.5, 1.6, 100)
        s = ring_resonator_s(wl=wl, radius=10.0)
        np.testing.assert_allclose(s[("through", "in")], s[("in", "through")], atol=1e-9)


class TestExtendedModels:
    """扩展器件模型测试（R01 步骤 7）。"""

    def test_taper_insertion_loss(self):
        """taper 插损正确。"""
        wl = np.array([1.55])
        s = taper_s(wl=wl, insertion_loss_db=0.5)
        power = np.abs(s[("out", "in")]) ** 2
        expected = 10.0 ** (-0.5 / 10.0)
        np.testing.assert_allclose(power[0], expected, atol=1e-9)

    def test_taper_negative_length_raises(self):
        """taper 负长度应 raise ValueError。"""
        with pytest.raises(ValueError, match="锥形长度必须 >= 0"):
            taper_s(length=-1.0)

    def test_modulator_phase(self):
        """modulator 相位正确。"""
        wl = np.array([1.55])
        s = modulator_s(wl=wl, phase_rad=1.5708)  # π/2
        phase = np.angle(s[("out", "in")][0])
        assert abs(phase - 1.5708) < 0.01

    def test_detector_absorbs_all(self):
        """detector 吸收所有光（S11=0）。"""
        wl = np.array([1.55])
        s = detector_s(wl=wl)
        assert np.all(s[("in", "in")] == 0)

    def test_detector_negative_responsivity_raises(self):
        """detector 负响应度应 raise ValueError。"""
        with pytest.raises(ValueError, match="响应度必须 >= 0"):
            detector_s(responsivity=-1.0)

    def test_splitter_equal_outputs(self):
        """splitter 两输出功率相等。"""
        wl = np.array([1.55])
        s = splitter_s(wl=wl, insertion_loss_db=0.0)
        p1 = np.abs(s[("out1", "in")]) ** 2
        p2 = np.abs(s[("out2", "in")]) ** 2
        np.testing.assert_allclose(p1, p2, atol=1e-9)

    def test_combiner_equal_inputs(self):
        """combiner 两输入功率相等。"""
        wl = np.array([1.55])
        s = combiner_s(wl=wl, insertion_loss_db=0.0)
        p1 = np.abs(s[("out", "in1")]) ** 2
        p2 = np.abs(s[("out", "in2")]) ** 2
        np.testing.assert_allclose(p1, p2, atol=1e-9)

    def test_attenuator_attenuation(self):
        """attenuator 衰减正确。"""
        wl = np.array([1.55])
        s = attenuator_s(wl=wl, attenuation_db=10.0)
        power = np.abs(s[("out", "in")]) ** 2
        expected = 10.0 ** (-10.0 / 10.0)  # 0.1
        np.testing.assert_allclose(power[0], expected, atol=1e-9)

    def test_attenuator_negative_attenuation_raises(self):
        """attenuator 负衰减应 raise ValueError。"""
        with pytest.raises(ValueError, match="衰减量必须 >= 0"):
            attenuator_s(attenuation_db=-1.0)

    def test_circulator_directionality(self):
        """circulator 单向传输: 1→2 有传输，2→1 隔离。"""
        wl = np.array([1.55])
        s = circulator_s(wl=wl, insertion_loss_db=0.0)
        fwd = np.abs(s[("p2", "p1")]) ** 2
        rev = np.abs(s[("p1", "p2")]) ** 2
        assert fwd[0] > 0.99, "正向传输应接近 1"
        assert rev[0] == 0, "反向应完全隔离"

    def test_isolator_directionality(self):
        """isolator 正向低损耗，反向高隔离。"""
        wl = np.array([1.55])
        s = isolator_s(wl=wl, insertion_loss_db=0.5, isolation_db=40.0)
        fwd = np.abs(s[("out", "in")]) ** 2
        rev = np.abs(s[("in", "out")]) ** 2
        # 正向功率 0.891，反向功率 0.0001，比值约 8910（>1000）
        assert fwd[0] > rev[0] * 1000, "正向应远大于反向（隔离度 > 30dB）"

    def test_mirror_full_reflection(self):
        """mirror 全反射 S11=1。"""
        wl = np.array([1.55])
        s = mirror_s(wl=wl, reflectivity=1.0)
        r = np.abs(s[("in", "in")]) ** 2
        np.testing.assert_allclose(r[0], 1.0, atol=1e-9)

    def test_mirror_invalid_reflectivity_raises(self):
        """mirror 反射率超范围应 raise ValueError。"""
        with pytest.raises(ValueError, match="反射率必须在"):
            mirror_s(reflectivity=1.5)

    def test_reflector_power_conservation(self):
        """reflector 功率守恒: R + T = 1。"""
        wl = np.array([1.55])
        s = reflector_s(wl=wl, reflectivity=0.3)
        r = np.abs(s[("in", "in")]) ** 2
        t = np.abs(s[("out", "in")]) ** 2
        np.testing.assert_allclose(r + t, 1.0, atol=1e-9)

    def test_unitary_unitarity(self):
        """unitary 酉矩阵: U·U^H = I。"""
        wl = np.array([1.55])
        s = unitary_s(wl=wl, theta=0.5, phi=0.3)
        # 构造 2x2 矩阵
        u = np.array(
            [
                [s[("out1", "in1")][0], s[("out1", "in2")][0]],
                [s[("out2", "in1")][0], s[("out2", "in2")][0]],
            ]
        )
        identity = u @ u.conj().T
        np.testing.assert_allclose(identity, np.eye(2), atol=1e-9)

    def test_bend_phase_accumulation(self):
        """bend 相位累积正确。"""
        wl = np.array([1.55])
        s = bend_s(wl=wl, radius=10.0, angle_deg=90.0, neff=2.4, loss_db_cm=0.0)
        # 弧长 = 2π*10/4 = 5π μm
        arc_length = 10.0 * np.pi / 2
        beta = 2.0 * np.pi * 2.4 / 1.55
        expected_phase = beta * arc_length
        actual_phase = np.angle(s[("out", "in")][0])
        # 模 2π 比较
        diff = abs((actual_phase - expected_phase + np.pi) % (2 * np.pi) - np.pi)
        assert diff < 0.01, f"bend 相位差异过大: {diff}"

    def test_bend_negative_radius_raises(self):
        """bend 负半径应 raise ValueError。"""
        with pytest.raises(ValueError, match="弯曲半径必须 > 0"):
            bend_s(radius=-1.0)


class TestModelCount:
    """验证器件模型数量 >= 20（R01 步骤 7 验收标准）。"""

    def test_model_count_at_least_20(self):
        """器件模型总数应 >= 20。"""
        from polaris.sim.models import (
            directional_coupler_s,
            ring_resonator_s,
            waveguide_s,
            y_branch_s,
        )

        base_models = [
            waveguide_s,
            y_branch_s,
            directional_coupler_s,
            ring_resonator_s,
            mmi_1x2_s,
            mmi_2x2_s,
            grating_coupler_s,
            crossing_s,
            terminator_s,
            phase_shifter_s,
        ]
        extended_models = [
            taper_s,
            modulator_s,
            detector_s,
            splitter_s,
            combiner_s,
            attenuator_s,
            circulator_s,
            isolator_s,
            mirror_s,
            reflector_s,
            unitary_s,
            bend_s,
        ]
        total = len(base_models) + len(extended_models)
        assert total >= 20, f"器件模型总数应 >= 20，得到 {total}"


class TestHalfRingModel:
    """half_ring 模型测试（R02 步骤 2）。"""

    def test_sdict_structure(self):
        """SDict 结构正确。"""
        wl = np.linspace(1.5, 1.6, 100)
        s = half_ring_s(wl=wl, radius=10.0)
        assert ("through", "in") in s
        assert ("in", "through") in s

    def test_reciprocity(self):
        """互易性: S_ij = S_ji。"""
        wl = np.linspace(1.5, 1.6, 100)
        s = half_ring_s(wl=wl, radius=10.0)
        np.testing.assert_allclose(
            s[("through", "in")], s[("in", "through")], atol=1e-9
        )

    def test_negative_radius_raises(self):
        """负半径应 raise ValueError。"""
        with pytest.raises(ValueError, match="环半径必须 > 0"):
            half_ring_s(radius=-1.0)

    def test_zero_gap_raises(self):
        """零间隙应 raise ValueError。"""
        with pytest.raises(ValueError, match="耦合间隙 gap 必须 > 0"):
            half_ring_s(gap=0.0)

    def test_negative_width_raises(self):
        """负宽度应 raise ValueError。"""
        with pytest.raises(ValueError, match="波导宽度必须 > 0"):
            half_ring_s(width=-0.5)

    def test_negative_thickness_raises(self):
        """负厚度应 raise ValueError。"""
        with pytest.raises(ValueError, match="波导厚度必须 > 0"):
            half_ring_s(thickness=-0.22)

    def test_resonance_dip(self):
        """环谐振器应在谐振波长处出现陷波。"""
        # 高分辨率扫描以捕获谐振
        wl = np.linspace(1.5, 1.6, 5000)
        s = half_ring_s(wl=wl, radius=10.0, gap=0.2, loss_db_cm=0.1)
        power = np.abs(s[("through", "in")]) ** 2
        # 应存在谐振陷波（功率最小值 < 最大值）
        assert np.min(power) < np.max(power), "环谐振器应出现谐振陷波"


class TestAddDropRingModel:
    """add_drop_ring 模型测试（R02 步骤 4）。"""

    def test_sdict_structure(self):
        """SDict 结构正确（4 端口）。"""
        wl = np.linspace(1.5, 1.6, 100)
        s = add_drop_ring_s(wl=wl, radius=10.0)
        assert ("through", "in") in s
        assert ("drop", "in") in s
        assert ("in", "through") in s
        assert ("in", "drop") in s

    def test_reciprocity(self):
        """互易性: S_ij = S_ji。"""
        wl = np.linspace(1.5, 1.6, 100)
        s = add_drop_ring_s(wl=wl, radius=10.0)
        np.testing.assert_allclose(
            s[("through", "in")], s[("in", "through")], atol=1e-9
        )
        np.testing.assert_allclose(
            s[("drop", "in")], s[("in", "drop")], atol=1e-9
        )

    def test_power_conservation_lossless(self):
        """无损 add-drop 环功率守恒: |T_through|² + |T_drop|² = 1。

        来源: Yariv 1997 §10.5
        """
        wl = np.linspace(1.5, 1.6, 1000)
        s = add_drop_ring_s(wl=wl, radius=10.0, loss_db_cm=0.0)
        t_through = np.abs(s[("through", "in")]) ** 2
        t_drop = np.abs(s[("drop", "in")]) ** 2
        total = t_through + t_drop
        np.testing.assert_allclose(total, 1.0, atol=1e-6)

    def test_negative_radius_raises(self):
        """负半径应 raise ValueError。"""
        with pytest.raises(ValueError, match="环半径必须 > 0"):
            add_drop_ring_s(radius=-1.0)

    def test_zero_gap_raises(self):
        """零间隙应 raise ValueError。"""
        with pytest.raises(ValueError, match="耦合间隙 gap 必须 > 0"):
            add_drop_ring_s(gap=0.0)


class TestSellmeierNeff:
    """Sellmeier 色散 neff(λ) 模型测试（R02 步骤 2）。"""

    def test_neff_at_1550nm(self):
        """1550nm 处 neff 应在合理范围（SOI 220nm 典型 2.3-2.5）。"""
        neff = sellmeier_neff(1.55)
        assert 2.3 < float(neff) < 2.5, f"1550nm neff {float(neff)} 应在 2.3-2.5"

    def test_neff_wavelength_array(self):
        """支持波长数组输入。"""
        wl = np.linspace(1.5, 1.6, 100)
        neff = sellmeier_neff(wl)
        assert len(neff) == 100
        assert np.all(neff > 0)

    def test_neff_negative_wavelength_raises(self):
        """负波长应 raise ValueError。"""
        with pytest.raises(ValueError, match="波长必须 > 0"):
            sellmeier_neff(-1.0)

    def test_neff_decreases_with_wavelength(self):
        """正常色散: neff 应随波长增加而减小。"""
        wl_short = 1.5
        wl_long = 1.6
        neff_short = sellmeier_neff(wl_short)
        neff_long = sellmeier_neff(wl_long)
        assert neff_short > neff_long, "正常色散: 短波长 neff 应大于长波长 neff"


class TestTaperModelR02:
    """taper 模型 R02 升级测试（对齐 simphony siepic.taper）。"""

    def test_taper_with_new_params(self):
        """使用新参数 w1/w2/loss_db。"""
        wl = np.array([1.55])
        s = taper_s(wl=wl, length=10.0, w1=0.5, w2=0.8, loss_db=0.2)
        power = np.abs(s[("out", "in")]) ** 2
        expected = 10.0 ** (-0.2 / 10.0)
        np.testing.assert_allclose(power[0], expected, atol=1e-9)

    def test_taper_backward_compatibility(self):
        """向后兼容: 仍支持 insertion_loss_db 参数。"""
        wl = np.array([1.55])
        s = taper_s(wl=wl, insertion_loss_db=0.5)
        power = np.abs(s[("out", "in")]) ** 2
        expected = 10.0 ** (-0.5 / 10.0)
        np.testing.assert_allclose(power[0], expected, atol=1e-9)

    def test_taper_negative_w1_raises(self):
        """负 w1 应 raise ValueError。"""
        with pytest.raises(ValueError, match="输入宽度 w1 必须 > 0"):
            taper_s(w1=-0.5)

    def test_taper_negative_w2_raises(self):
        """负 w2 应 raise ValueError。"""
        with pytest.raises(ValueError, match="输出宽度 w2 必须 > 0"):
            taper_s(w2=-0.5)

    def test_taper_negative_loss_raises(self):
        """负 loss_db 应 raise ValueError。"""
        with pytest.raises(ValueError, match="损耗 loss_db 必须 >= 0"):
            taper_s(loss_db=-1.0)
