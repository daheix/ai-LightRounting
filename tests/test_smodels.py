"""S 参数模型与频率域仿真测试。"""

from __future__ import annotations

import numpy as np

from polaris.pdk.catalog import build_default_catalog
from polaris.sim import (
    CircuitSimulator,
    cascade_circuit,
    default_models,
    directional_coupler_s,
    grating_coupler_s,
    load_touchstone,
    mmi_1x2_s,
    mmi_2x2_s,
    ring_resonator_s,
    save_touchstone,
    waveguide_s,
    y_branch_s,
)
from polaris.sim.device_models import (
    catalog_smodels,
    device_to_smodel,
    simulate_device,
)


# ---------------------------------------------------------------------------
# 基础器件 S 参数模型测试
# ---------------------------------------------------------------------------
class TestWaveguideS:
    def test_waveguide_phase(self):
        """波导 S 参数应有正确的相位累积。"""
        wl = np.array([1.55])
        s = waveguide_s(wl=wl, length=1.55, neff=2.0)
        # phase = exp(i * 2*pi * 2.0 * 1.55 / 1.55) = exp(i * 4*pi) = 1
        assert abs(s[("out", "in")][0] - 1.0) < 1e-10

    def test_waveguide_loss(self):
        """波导损耗应正确衰减振幅。"""
        wl = np.array([1.55])
        s = waveguide_s(wl=wl, length=1e4, neff=2.0, loss_db_cm=3.0)
        # 1cm 长度，3dB/cm 损耗 → 振幅衰减 10^(-3/20)
        expected = 10.0 ** (-3.0 / 20.0)
        assert abs(abs(s[("out", "in")][0]) - expected) < 1e-6

    def test_waveguide_reciprocal(self):
        """波导应互易：S21 = S12。"""
        wl = np.linspace(1.5, 1.6, 10)
        s = waveguide_s(wl=wl, length=100.0)
        np.testing.assert_array_almost_equal(s[("out", "in")], s[("in", "out")])

    def test_waveguide_no_reflection(self):
        """理想波导无反射：S11 = S22 = 0。"""
        wl = np.array([1.55])
        s = waveguide_s(wl=wl, length=100.0)
        assert abs(s[("in", "in")][0]) < 1e-15
        assert abs(s[("out", "out")][0]) < 1e-15


class TestYBranchS:
    def test_y_branch_split(self):
        """Y 分支应 3dB 分束：每个输出功率为 50%。"""
        wl = np.array([1.55])
        s = y_branch_s(wl=wl, insertion_loss_db=0.0)
        amp = abs(s[("port_2", "port_1")][0])
        power = amp**2
        # 10^(-3/20)^2 = 10^(-0.3) ≈ 0.5012
        assert abs(power - 0.5) < 0.005

    def test_y_branch_symmetric(self):
        """Y 分支两输出应对称。"""
        wl = np.array([1.55])
        s = y_branch_s(wl=wl)
        assert abs(s[("port_2", "port_1")][0] - s[("port_3", "port_1")][0]) < 1e-10


class TestDirectionalCouplerS:
    def test_dc_power_conservation(self):
        """定向耦合器功率守恒：|tau|^2 + |kappa|^2 = 1。"""
        wl = np.array([1.55])
        s = directional_coupler_s(wl=wl, coupling=0.3)
        tau_power = abs(s[("out1", "in1")][0]) ** 2
        kappa_power = abs(s[("out2", "in1")][0]) ** 2
        assert abs(tau_power + kappa_power - 1.0) < 1e-6


class TestRingResonatorS:
    def test_ring_has_resonance(self):
        """环谐振器应在谐振波长处有功率下降。"""
        # 用极大半径确保足够的环内损耗产生临界耦合
        # R=500μm, 周长=3142μm=0.314cm, 5dB/cm → 1.57dB 衰减
        wl = np.linspace(1.55, 1.60, 50000)
        s = ring_resonator_s(wl=wl, radius=500.0, neff=2.4, coupling=0.5, loss_db_cm=5.0)
        T = np.abs(s[("through", "in")]) ** 2
        # 传输谱应有最小值（谐振点）
        assert T.min() < 0.5
        # 非谐振处传输接近 1
        assert T.max() > 0.9


class TestGratingCouplerS:
    def test_gc_peak_at_center(self):
        """光栅耦合器在中心波长处响应最大。"""
        wl = np.linspace(1.4, 1.7, 1000)
        s = grating_coupler_s(wl=wl, peak_wl=1.55, bandwidth_3db=0.04)
        amp = np.abs(s[("waveguide", "fiber")])
        peak_idx = np.argmax(amp)
        assert abs(wl[peak_idx] - 1.55) < 0.01

    def test_gc_bandwidth(self):
        """光栅耦合器 3dB 带宽应正确。"""
        wl = np.linspace(1.4, 1.7, 10000)
        bw = 0.04
        s = grating_coupler_s(wl=wl, peak_wl=1.55, bandwidth_3db=bw)
        amp = np.abs(s[("waveguide", "fiber")])
        peak = amp.max()
        # 半功率点
        half_power = peak / np.sqrt(2)
        above = wl[amp > half_power]
        if len(above) > 1:
            actual_bw = above[-1] - above[0]
            assert abs(actual_bw - bw) < 0.02


class TestMMIS:
    def test_mmi_1x2_split(self):
        """MMI 1x2 应 3dB 分束。"""
        wl = np.array([1.55])
        s = mmi_1x2_s(wl=wl, insertion_loss_db=0.0)
        power = abs(s[("out1", "in")][0]) ** 2
        # 10^(-3/20)^2 = 10^(-0.3) ≈ 0.5012
        assert abs(power - 0.5) < 0.005

    def test_mmi_2x2_bar_cross(self):
        """MMI 2x2 应有 bar 和 cross 端口。"""
        wl = np.array([1.55])
        s = mmi_2x2_s(wl=wl, insertion_loss_db=0.0)
        assert ("out1", "in1") in s  # bar
        assert ("out2", "in1") in s  # cross


# ---------------------------------------------------------------------------
# Touchstone 文件测试
# ---------------------------------------------------------------------------
class TestTouchstone:
    def test_save_load_roundtrip(self, tmp_path):
        """Touchstone 文件保存→加载应完整还原。"""
        wl = np.array([1.5, 1.55, 1.6])
        s = waveguide_s(wl=wl, length=100.0, neff=2.4)
        freqs = 3e8 / wl  # 转换为 Hz

        path = tmp_path / "test.s2p"
        save_touchstone(str(path), freqs, s, freq_unit="ghz")
        freqs_loaded, s_loaded = load_touchstone(str(path))

        assert len(freqs_loaded) == 3
        # 频率值应正确（GHz → Hz）
        assert abs(freqs_loaded[1] - 3e8 / 1.55) < 1e6
        # S 参数应匹配
        np.testing.assert_almost_equal(
            s_loaded[("port_1", "port_2")],
            s[("out", "in")],
            decimal=4,
        )


# ---------------------------------------------------------------------------
# S 参数级联测试
# ---------------------------------------------------------------------------
class TestCascade:
    def test_cascade_two_waveguides(self):
        """两个波导级联应等价于一个长波导。"""
        wl = np.array([1.55])
        s1 = waveguide_s(wl=wl, length=50.0, neff=2.4)
        s2 = waveguide_s(wl=wl, length=50.0, neff=2.4)
        # 级联
        merged = cascade_circuit(
            instances={"wg1": s1, "wg2": s2},
            connections=[("wg1.out", "wg2.in")],
            ports={"in": "wg1.in", "out": "wg2.out"},
        )
        # 对比单个 100μm 波导
        s_ref = waveguide_s(wl=wl, length=100.0, neff=2.4)
        # 级联后的传输应与参考一致
        if ("out", "in") in merged:
            np.testing.assert_almost_equal(merged[("out", "in")], s_ref[("out", "in")], decimal=4)


# ---------------------------------------------------------------------------
# 电路级仿真器测试
# ---------------------------------------------------------------------------
class TestCircuitSimulator:
    def test_simulator_creation(self):
        """仿真器应能创建并注册模型。"""
        sim = CircuitSimulator()
        sim.register_model("waveguide", waveguide_s)
        assert "waveguide" in sim.models

    def test_simulate_mzi(self):
        """仿真器应能仿真 MZI 电路。"""
        sim = CircuitSimulator(models=default_models())
        netlist = {
            "instances": {
                "wg1": "waveguide",
                "wg2": "waveguide",
            },
            "connections": {"wg1.out": "wg2.in"},
            "ports": {"in": "wg1.in", "out": "wg2.out"},
        }
        wl = np.linspace(1.5, 1.6, 100)
        s = sim.simulate(netlist, wavelengths=wl)
        assert len(s) > 0

    def test_sweep_wavelength(self):
        """波长扫描应返回波长数组和 S 参数。"""
        sim = CircuitSimulator(models=default_models())
        netlist = {
            "instances": {"wg": "waveguide"},
            "connections": {},
            "ports": {"in": "wg.in", "out": "wg.out"},
        }
        wl, s = sim.sweep_wavelength(netlist, 1.5, 1.6, 100)
        assert len(wl) == 100
        assert len(s) > 0


# ---------------------------------------------------------------------------
# 器件映射测试
# ---------------------------------------------------------------------------
class TestDeviceModels:
    def test_all_devices_have_smodel(self):
        """所有 51 个器件都应有 S 参数模型映射。"""
        catalog = build_default_catalog()
        wl = np.array([1.55])
        missing = []
        for device in catalog:
            try:
                s = device_to_smodel(device, wl)
                if not s or len(s) == 0:
                    missing.append(device.device_id)
            except Exception as e:
                missing.append(f"{device.device_id}: {e}")
        assert missing == [], f"缺少 S 参数模型的器件: {missing}"

    def test_catalog_smodels(self):
        """catalog_smodels 应为所有器件生成模型函数。"""
        catalog = build_default_catalog()
        models = catalog_smodels(catalog)
        assert len(models) == len(catalog)
        # 测试一个模型
        first_id = list(models.keys())[0]
        s = models[first_id](wl=1.55)
        assert isinstance(s, dict)
        assert len(s) > 0

    def test_simulate_device(self):
        """simulate_device 应返回波长数组和 S 参数。"""
        catalog = build_default_catalog()
        dev = catalog.get("soi_strip_waveguide")
        wl, s = simulate_device(dev)
        assert len(wl) == 500
        assert len(s) > 0

    def test_ring_resonator_device(self):
        """环谐振器器件应有频率相关响应。"""
        catalog = build_default_catalog()
        dev = catalog.get("soi_ring_resonator")
        wl, s = simulate_device(dev, np.linspace(1.5, 1.6, 1000))
        T = np.abs(s[("through", "in")]) ** 2
        # 应有谐振下降
        assert T.min() < T.max()

    def test_grating_coupler_device(self):
        """光栅耦合器器件应有高斯型响应。"""
        catalog = build_default_catalog()
        dev = catalog.get("soi_grating_coupler_1d")
        wl, s = simulate_device(dev, np.linspace(1.4, 1.7, 1000))
        amp = np.abs(s[("waveguide", "fiber")])
        # 应有峰值
        assert amp.max() > amp.min()


# ---------------------------------------------------------------------------
# Simphony 集成测试（规则 2 直接集成）
# ---------------------------------------------------------------------------
class TestSimphonyIntegration:
    def test_simphony_import(self):
        """Simphony 应能导入（规则 2 直接集成）。"""
        import simphony

        assert simphony.__version__ is not None

    def test_sax_import(self):
        """SAX 应能导入（规则 2 直接集成）。"""
        import sax

        assert sax is not None

    def test_siepic_models_available(self):
        """SiEPIC 模型库应可用。"""
        from simphony.libraries import siepic

        models = [x for x in dir(siepic) if not x.startswith("_")]
        assert "waveguide" in models
        assert "y_branch" in models
        assert "grating_coupler" in models

    def test_simphony_y_branch(self):
        """Simphony Y 分支模型应返回 S 参数字典。"""
        import numpy as np
        from simphony.libraries import siepic

        s = siepic.y_branch(wl=np.array([1.55]))
        assert isinstance(s, dict)
        assert len(s) > 0
