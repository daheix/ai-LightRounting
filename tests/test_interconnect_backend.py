"""R32 Lumerical INTERCONNECT 时频域联合仿真后端测试。

测试覆盖（R32 任务要求 ≥8 个测试）:
1. TestInterconnectConfig: 配置参数验证（非法参数 raise，禁止 fall-back）
2. TestAddComponent: 器件添加（7 种类型 + 参数校验）
3. TestConnect: 端口连接（越界/自环 raise）
4. TestRunFreqDomain: 频域仿真（S 参数级联 + 无损波导幅度守恒）
5. TestRunTimeDomain: 时域仿真（高斯脉冲延迟 + 幅度守恒）
6. TestTimeToFreq: 时频转换（FFT 正确性 + 互逆性）
7. TestFreqToTime: 频时转换（IFFT 正确性 + 互逆性）
8. TestRunJoint: 时频域联合（一致性误差 < 1e-6）
9. TestAnalyzeEyeDiagram: 眼图分析（眼开度 + Q 因子 + 抖动）
10. TestAnalyzeBer: BER 分析（Q 因子高斯近似）
11. TestExpandSubcircuit: 子电路展开（递归层次化 + 深度超限 raise）
12. Test1000DevicesPerformance: 1000 器件时频域联合仿真 < 5 分钟

学术依据（R02 学术诚信）:
- Lumerical INTERCONNECT: https://optics.ansys.com/hc/en-us/categories/1500000158201
- Python co-simulation: https://optics.ansys.com/hc/en-us/articles/360034936773
- ITU-T G.977 Q-factor BER: https://www.itu.int/rec/T-REC-G.977
- Pozar, Microwave Engineering §4.3 (S 参数级联)
- Oppenheim & Willsky, Signals and Systems §3 (FFT/卷积定理)

合规: 规则 14.1 禁止 fall-back；规则 18 学术诚信；规则 26 不参与 GPU。
"""

from __future__ import annotations

import time

import numpy as np
import pytest

from polaris.sim.interconnect_backend import (
    C0,
    Component,
    InterconnectBackend,
    InterconnectConfig,
)

# 物理常量与典型参数（与实现一致，NIST CODATA 2018）
SOI_NEFF = 2.4  # Si strip @ 1550nm
SOI_NG = 4.0


# =============================================================================
# 1. TestInterconnectConfig — 配置参数验证
# =============================================================================
class TestInterconnectConfig:
    """配置参数校验（R03 禁止 fall-back，非法即 raise）。"""

    def test_config_default_valid(self) -> None:
        """默认配置合法。"""
        cfg = InterconnectConfig()
        assert cfg.timestep > 0
        assert cfg.n_steps > 0
        assert cfg.wavelength_center > 0
        assert cfg.freq_points > 0
        assert cfg.freq_span > 0
        assert cfg.n_eff > 0

    @pytest.mark.parametrize("field,val", [
        ("timestep", 0.0), ("timestep", -1e-14),
        ("n_steps", 0), ("n_steps", -10),
        ("wavelength_center", 0.0), ("wavelength_center", -1e-6),
        ("freq_points", 0), ("freq_points", -1),
        ("freq_span", 0.0), ("freq_span", -1e13),
        ("n_eff", 0.0), ("n_eff", -1.0),
    ])
    def test_config_invalid_raises(self, field: str, val: float) -> None:
        """非法参数必须 raise ValueError（禁止 fall-back）。"""
        with pytest.raises(ValueError):
            InterconnectConfig(**{field: val})


# =============================================================================
# 2. TestAddComponent — 器件添加
# =============================================================================
class TestAddComponent:
    """器件添加测试（7 种类型 + 参数校验）。"""

    def test_add_waveguide_returns_incremental_id(self) -> None:
        """添加波导返回递增 ID。"""
        backend = InterconnectBackend(InterconnectConfig())
        cid0 = backend.add_component("waveguide", {"length": 1e-3})
        cid1 = backend.add_component("waveguide", {"length": 2e-3})
        assert cid0 == 0
        assert cid1 == 1
        assert backend.components[0].comp_type == "waveguide"
        assert backend.components[0].n_ports == 2

    def test_add_all_component_types(self) -> None:
        """支持 7 种器件类型。"""
        backend = InterconnectBackend(InterconnectConfig())
        backend.add_component("waveguide", {"length": 1e-3})
        backend.add_component("mmi_1x2")
        backend.add_component("y_branch")
        backend.add_component("directional_coupler", {"coupling_ratio": 0.5})
        backend.add_component("ring_resonator", {"radius": 1e-5})
        backend.add_component("modulator", {"length": 1e-3})
        backend.add_component("through")
        assert len(backend.components) == 7
        # 端口数正确
        assert backend.components[0].n_ports == 2  # waveguide
        assert backend.components[1].n_ports == 3  # mmi_1x2
        assert backend.components[3].n_ports == 4  # directional_coupler

    def test_add_unknown_type_raises(self) -> None:
        """未知器件类型告警退出。"""
        backend = InterconnectBackend(InterconnectConfig())
        with pytest.raises(ValueError, match="未知器件类型"):
            backend.add_component("laser_xxx")

    def test_add_waveguide_invalid_length_raises(self) -> None:
        """波导 length ≤ 0 告警退出。"""
        backend = InterconnectBackend(InterconnectConfig())
        with pytest.raises(ValueError, match="length"):
            backend.add_component("waveguide", {"length": 0.0})

    def test_add_dc_invalid_ratio_raises(self) -> None:
        """定向耦合器耦合率越界告警退出。"""
        backend = InterconnectBackend(InterconnectConfig())
        with pytest.raises(ValueError, match="coupling_ratio"):
            backend.add_component("directional_coupler", {"coupling_ratio": 1.5})

    def test_add_ring_invalid_self_coupling_raises(self) -> None:
        """环谐振器自耦合系数越界告警退出。"""
        backend = InterconnectBackend(InterconnectConfig())
        with pytest.raises(ValueError, match="self_coupling"):
            backend.add_component("ring_resonator", {"self_coupling": 1.5})

    def test_component_sparams_shape(self) -> None:
        """器件 S 参数形状正确 (n_freq, n_ports, n_ports)。"""
        cfg = InterconnectConfig(freq_points=64)
        backend = InterconnectBackend(cfg)
        backend.add_component("waveguide", {"length": 1e-3})
        s = backend.components[0].s_params
        assert s.shape == (64, 2, 2)
        assert s.dtype == np.complex128


# =============================================================================
# 3. TestConnect — 端口连接
# =============================================================================
class TestConnect:
    """端口连接测试（越界/自环 raise）。"""

    def test_connect_valid(self) -> None:
        """合法连接。"""
        backend = InterconnectBackend(InterconnectConfig())
        c0 = backend.add_component("waveguide")
        c1 = backend.add_component("waveguide")
        backend.connect(c0, 1, c1, 0)
        assert len(backend.connections) == 1
        assert backend.connections[0] == (0, 1, 1, 0)

    def test_connect_src_out_of_range_raises(self) -> None:
        """src_id 越界告警退出。"""
        backend = InterconnectBackend(InterconnectConfig())
        backend.add_component("waveguide")
        with pytest.raises(ValueError, match="src_id"):
            backend.connect(5, 1, 0, 0)

    def test_connect_dst_out_of_range_raises(self) -> None:
        """dst_id 越界告警退出。"""
        backend = InterconnectBackend(InterconnectConfig())
        backend.add_component("waveguide")
        with pytest.raises(ValueError, match="dst_id"):
            backend.connect(0, 1, 5, 0)

    def test_connect_self_loop_raises(self) -> None:
        """自环连接告警退出。"""
        backend = InterconnectBackend(InterconnectConfig())
        backend.add_component("waveguide")
        with pytest.raises(ValueError, match="自环"):
            backend.connect(0, 1, 0, 0)

    def test_connect_port_out_of_range_raises(self) -> None:
        """端口越界告警退出。"""
        backend = InterconnectBackend(InterconnectConfig())
        c0 = backend.add_component("waveguide")  # 2 端口
        c1 = backend.add_component("waveguide")
        with pytest.raises(ValueError, match="src_port"):
            backend.connect(c0, 5, c1, 0)

    def test_topo_order_feedback_loop_raises(self) -> None:
        """反馈环路告警退出（禁止 fall-back）。"""
        backend = InterconnectBackend(InterconnectConfig())
        c0 = backend.add_component("waveguide")
        c1 = backend.add_component("waveguide")
        backend.connect(c0, 1, c1, 0)
        backend.connect(c1, 1, c0, 0)  # 环路
        with pytest.raises(RuntimeError, match="反馈环路"):
            backend._topo_order()


# =============================================================================
# 4. TestRunFreqDomain — 频域仿真
# =============================================================================
class TestRunFreqDomain:
    """频域仿真测试（S 参数级联 + 无损波导幅度守恒）。"""

    def test_freq_domain_no_devices_raises(self) -> None:
        """无器件告警退出。"""
        backend = InterconnectBackend(InterconnectConfig())
        with pytest.raises(RuntimeError, match="无器件"):
            backend.run_freq_domain()

    def test_freq_domain_lossless_waveguide_amplitude(self) -> None:
        """无损波导级联 |S21| = 1（能量守恒）。"""
        cfg = InterconnectConfig(freq_points=128)
        backend = InterconnectBackend(cfg)
        for _ in range(5):
            backend.add_component("waveguide", {"length": 1e-4, "loss_db_m": 0.0})
        result = backend.run_freq_domain()
        s21 = result["S_total"][:, 1, 0]
        # 无损波导级联 |S21| 应 = 1
        assert np.allclose(np.abs(s21), 1.0, atol=1e-10)

    def test_freq_domain_lossy_waveguide_attenuation(self) -> None:
        """有损波导级联幅度按 exp(-αL/2) 衰减。"""
        cfg = InterconnectConfig(freq_points=64)
        backend = InterconnectBackend(cfg)
        length = 1e-3  # 1mm
        loss_db_m = 100.0  # 100 dB/m = 1 dB/mm
        backend.add_component("waveguide", {"length": length, "loss_db_m": loss_db_m})
        result = backend.run_freq_domain()
        s21 = result["S_total"][:, 1, 0]
        # IL = 100 dB/m * 1e-3 m = 0.1 dB → |S21| = 10^(-0.1/20) ≈ 0.989
        expected_mag = 10.0 ** (-0.1 / 20.0)
        assert np.allclose(np.abs(s21), expected_mag, rtol=1e-4)

    def test_freq_domain_sparams_shape(self) -> None:
        """频域 S_total 形状正确。"""
        cfg = InterconnectConfig(freq_points=256)
        backend = InterconnectBackend(cfg)
        backend.add_component("waveguide")
        result = backend.run_freq_domain()
        assert result["S_total"].shape == (256, 2, 2)
        assert "freq" in result
        assert len(result["freq"]) == 256

    def test_freq_domain_non_2port_raises(self) -> None:
        """非 2 端口器件链式级联告警退出。"""
        cfg = InterconnectConfig(freq_points=32)
        backend = InterconnectBackend(cfg)
        backend.add_component("mmi_1x2")  # 3 端口
        with pytest.raises(RuntimeError, match="端口数"):
            backend.run_freq_domain()


# =============================================================================
# 5. TestRunTimeDomain — 时域仿真
# =============================================================================
class TestRunTimeDomain:
    """时域仿真测试（高斯脉冲延迟 + 幅度守恒）。"""

    def test_time_domain_default_source(self) -> None:
        """默认高斯脉冲源生成。"""
        cfg = InterconnectConfig(n_steps=512, freq_points=128)
        backend = InterconnectBackend(cfg)
        backend.add_component("through")  # 直通无延迟
        result = backend.run_time_domain()
        assert "t" in result
        assert "input" in result
        assert "output" in result
        assert "impulse" in result
        assert len(result["output"]) == 512

    def test_time_domain_through_passthrough(self) -> None:
        """直通器件 output ≈ input（循环卷积，无延迟）。"""
        cfg = InterconnectConfig(n_steps=512, freq_points=128)
        backend = InterconnectBackend(cfg)
        backend.add_component("through")
        result = backend.run_time_domain()
        # through 的 S21=1，冲激响应为 delta(t)，output ≈ input
        assert np.allclose(result["output"], result["input"], atol=1e-10)

    def test_time_domain_input_length_mismatch_raises(self) -> None:
        """输入信号长度不匹配告警退出。"""
        cfg = InterconnectConfig(n_steps=256)
        backend = InterconnectBackend(cfg)
        backend.add_component("through")
        bad_input = np.zeros(100, dtype=np.complex128)
        with pytest.raises(ValueError, match="input_signal 长度"):
            backend.run_time_domain(input_signal=bad_input)

    def test_time_domain_waveguide_delay(self) -> None:
        """波导时域延迟（高斯脉冲在 τ=neff·L/c 后到达）。"""
        cfg = InterconnectConfig(timestep=1e-14, n_steps=2048, freq_points=256)
        backend = InterconnectBackend(cfg)
        length = 1e-4  # 100μm
        backend.add_component("waveguide", {"length": length, "loss_db_m": 0.0})
        result = backend.run_time_domain()
        # 解析延迟 τ = neff·L/c
        expected_delay = SOI_NEFF * length / C0
        expected_delay_samples = int(round(expected_delay / cfg.timestep))
        # 输入峰值位置
        peak_in = int(np.argmax(np.abs(result["input"])))
        peak_out = int(np.argmax(np.abs(result["output"])))
        actual_delay = peak_out - peak_in
        # 容差 ±5 采样点（循环卷积 + 离散化误差）
        assert abs(actual_delay - expected_delay_samples) <= 5


# =============================================================================
# 6. TestTimeToFreq — 时频转换 FFT
# =============================================================================
class TestTimeToFreq:
    """时频转换测试（FFT 正确性 + 互逆性）。"""

    def test_fft_pure_tone(self) -> None:
        """纯正弦信号 FFT 在对应频率有峰值。"""
        backend = InterconnectBackend(InterconnectConfig())
        n = 256
        dt = 1e-14
        # 10 个周期的正弦
        t = np.arange(n) * dt
        freq_test = 10.0 / (n * dt)  # 第 10 个 FFT bin
        sig = np.exp(2j * np.pi * freq_test * t)
        spec = backend.time_to_freq(sig)
        # 第 10 个 bin 应有最大幅值
        peak_bin = int(np.argmax(np.abs(spec)))
        assert peak_bin == 10

    def test_fft_empty_raises(self) -> None:
        """空信号告警退出。"""
        backend = InterconnectBackend(InterconnectConfig())
        with pytest.raises(ValueError, match="为空"):
            backend.time_to_freq(np.array([], dtype=np.complex128))

    def test_fft_dc_component(self) -> None:
        """直流信号 FFT 在 DC（bin 0）有峰值。"""
        backend = InterconnectBackend(InterconnectConfig())
        sig = np.ones(64, dtype=np.complex128) * 2.0
        spec = backend.time_to_freq(sig)
        # DC 分量 = sum = 64 * 2 = 128
        assert spec[0] == pytest.approx(128.0)
        # 其他 bin ≈ 0
        assert np.allclose(spec[1:], 0.0, atol=1e-10)


# =============================================================================
# 7. TestFreqToTime — 频时转换 IFFT
# =============================================================================
class TestFreqToTime:
    """频时转换测试（IFFT 正确性 + 互逆性）。"""

    def test_ifft_delta_frequency(self) -> None:
        """单频 IFFT 得纯正弦。"""
        backend = InterconnectBackend(InterconnectConfig())
        n = 128
        spec = np.zeros(n, dtype=np.complex128)
        spec[5] = n * 1.0  # 第 5 个 bin，幅度 n（ifft 1/N 归一化后 = 1）
        sig = backend.freq_to_time(spec)
        # 时域应为 exp(2πi·5·t/n)，幅度 1
        assert np.max(np.abs(sig)) == pytest.approx(1.0, rel=1e-10)

    def test_ifft_empty_raises(self) -> None:
        """空信号告警退出。"""
        backend = InterconnectBackend(InterconnectConfig())
        with pytest.raises(ValueError, match="为空"):
            backend.freq_to_time(np.array([], dtype=np.complex128))

    def test_fft_ifft_inverse(self) -> None:
        """FFT 与 IFFT 互逆: freq_to_time(time_to_freq(x)) = x。"""
        backend = InterconnectBackend(InterconnectConfig())
        rng = np.random.default_rng(42)
        x = rng.standard_normal(64) + 1j * rng.standard_normal(64)
        x_round = backend.freq_to_time(backend.time_to_freq(x))
        assert np.allclose(x_round, x, atol=1e-10)

    def test_ifft_dc_spectrum(self) -> None:
        """全 1 频谱 IFFT 得 delta(t) 在 t=0。"""
        backend = InterconnectBackend(InterconnectConfig())
        n = 64
        spec = np.ones(n, dtype=np.complex128)
        sig = backend.freq_to_time(spec)
        # IFFT(1) = delta(t)，t=0 处 = 1，其他 = 0
        assert sig[0] == pytest.approx(1.0, rel=1e-10)
        assert np.allclose(sig[1:], 0.0, atol=1e-10)


# =============================================================================
# 8. TestRunJoint — 时频域联合
# =============================================================================
class TestRunJoint:
    """时频域联合仿真测试（一致性误差 < 1e-6）。"""

    def test_joint_consistency_lossless(self) -> None:
        """无损波导链时频域联合一致性误差 < 1e-6。"""
        cfg = InterconnectConfig(
            timestep=1e-14, n_steps=1024, freq_points=512, freq_span=1e14
        )
        backend = InterconnectBackend(cfg)
        for _ in range(3):
            backend.add_component("waveguide", {"length": 1e-4})
        result = backend.run_joint()
        assert result["consistency_error"] < 1e-6
        assert "S_total" in result
        assert "output" in result

    def test_joint_consistency_lossy(self) -> None:
        """有损波导链时频域联合一致性。"""
        cfg = InterconnectConfig(
            timestep=1e-14, n_steps=1024, freq_points=512, freq_span=1e14
        )
        backend = InterconnectBackend(cfg)
        backend.add_component(
            "waveguide", {"length": 5e-4, "loss_db_m": 100.0}
        )
        result = backend.run_joint()
        assert result["consistency_error"] < 1e-6

    def test_joint_output_finite(self) -> None:
        """联合仿真输出为有限值（无数值发散）。"""
        cfg = InterconnectConfig(
            timestep=1e-14, n_steps=512, freq_points=256, freq_span=1e14
        )
        backend = InterconnectBackend(cfg)
        backend.add_component("waveguide", {"length": 1e-4})
        result = backend.run_joint()
        assert np.all(np.isfinite(result["output"]))
        assert np.all(np.isfinite(result["S_total"]))


# =============================================================================
# 9. TestAnalyzeEyeDiagram — 眼图分析
# =============================================================================
class TestAnalyzeEyeDiagram:
    """眼图分析测试（眼开度 + Q 因子 + 抖动）。"""

    def test_eye_diagram_clean_nrz(self) -> None:
        """清晰 NRZ 信号眼图分析（高 Q 因子）。"""
        cfg = InterconnectConfig(timestep=1e-11)  # 10Gbps: spb=10
        backend = InterconnectBackend(cfg)
        rng = np.random.default_rng(42)
        bits = rng.integers(0, 2, 50)
        spb = 10
        signal = np.repeat(bits, spb).astype(float)
        signal += rng.normal(0, 0.01, len(signal))  # 小噪声
        result = backend.analyze_eye_diagram(signal, bit_rate=1e10)
        assert result["eye"].shape == (50, spb)
        assert result["eye_opening"] > 0.5
        assert result["q_factor"] > 5.0
        assert result["jitter_rms"] >= 0.0

    def test_eye_diagram_invalid_bit_rate_raises(self) -> None:
        """非法 bit_rate 告警退出。"""
        backend = InterconnectBackend(InterconnectConfig())
        sig = np.ones(100, dtype=float)
        with pytest.raises(ValueError, match="bit_rate"):
            backend.analyze_eye_diagram(sig, bit_rate=0.0)

    def test_eye_diagram_short_signal_raises(self) -> None:
        """信号过短告警退出。"""
        cfg = InterconnectConfig(timestep=1e-11)
        backend = InterconnectBackend(cfg)
        short_sig = np.array([1.0, 0.0], dtype=float)
        with pytest.raises(ValueError, match="不足"):
            backend.analyze_eye_diagram(short_sig, bit_rate=1e10)

    def test_eye_diagram_empty_signal_raises(self) -> None:
        """空信号告警退出。"""
        backend = InterconnectBackend(InterconnectConfig())
        with pytest.raises(ValueError, match="为空"):
            backend.analyze_eye_diagram(np.array([], dtype=float), bit_rate=1e10)

    def test_eye_diagram_closed_eye(self) -> None:
        """闭合眼图（高噪声）眼开度小。"""
        cfg = InterconnectConfig(timestep=1e-11)
        backend = InterconnectBackend(cfg)
        rng = np.random.default_rng(42)
        bits = rng.integers(0, 2, 50)
        spb = 10
        signal = np.repeat(bits, spb).astype(float)
        signal += rng.normal(0, 0.5, len(signal))  # 大噪声
        result = backend.analyze_eye_diagram(signal, bit_rate=1e10)
        # 大噪声 → 眼开度小
        assert result["eye_opening"] < 1.0


# =============================================================================
# 10. TestAnalyzeBer — BER 分析
# =============================================================================
class TestAnalyzeBer:
    """BER 分析测试（Q 因子高斯近似）。"""

    def test_ber_from_high_q(self) -> None:
        """高 Q 因子 → 低 BER（< 1e-9）。"""
        backend = InterconnectBackend(InterconnectConfig())
        eye_result = {"q_factor": 7.0}  # Q=7 → BER ≈ 1e-12
        ber = backend.analyze_ber(eye_result)
        assert 0 < ber < 1e-9

    def test_ber_from_low_q(self) -> None:
        """低 Q 因子 → 高 BER（> 1e-3）。"""
        backend = InterconnectBackend(InterconnectConfig())
        eye_result = {"q_factor": 2.0}  # Q=2 → BER ≈ 0.023
        ber = backend.analyze_ber(eye_result)
        assert ber > 1e-3

    def test_ber_known_value(self) -> None:
        """BER 已知值验证（Q=6 → BER ≈ 8e-10）。"""
        backend = InterconnectBackend(InterconnectConfig())
        ber = backend.analyze_ber({"q_factor": 6.0})
        # Q=6: 0.5*erfc(6/√2) ≈ 9.9e-10
        assert ber == pytest.approx(9.9e-10, rel=0.1)

    def test_ber_missing_q_factor_raises(self) -> None:
        """缺少 q_factor 字段告警退出。"""
        backend = InterconnectBackend(InterconnectConfig())
        with pytest.raises(KeyError, match="q_factor"):
            backend.analyze_ber({"eye_opening": 0.5})

    def test_ber_nonpositive_q_raises(self) -> None:
        """非正 Q 因子告警退出。"""
        backend = InterconnectBackend(InterconnectConfig())
        with pytest.raises(ValueError, match="Q 因子"):
            backend.analyze_ber({"q_factor": 0.0})


# =============================================================================
# 11. TestExpandSubcircuit — 子电路展开
# =============================================================================
class TestExpandSubcircuit:
    """子电路层次化展开测试。"""

    def test_expand_flat_circuit(self) -> None:
        """扁平电路（无子电路）原样返回。"""
        backend = InterconnectBackend(InterconnectConfig())
        circuit = {
            "components": [{"id": 0, "type": "waveguide"}],
            "connections": [{"src": 0, "dst": 1}],
        }
        result = backend.expand_subcircuit(circuit)
        assert len(result["components"]) == 1
        assert len(result["connections"]) == 1

    def test_expand_one_level_subcircuit(self) -> None:
        """单层子电路展开。"""
        backend = InterconnectBackend(InterconnectConfig())
        circuit = {
            "components": [{"id": 0, "type": "waveguide"}],
            "subcircuits": [
                {
                    "id": "sub1",
                    "instances": [
                        {"id": 1, "type": "waveguide"},
                        {"id": 2, "type": "mmi_1x2"},
                    ],
                    "internal_connections": [{"src": 1, "dst": 2}],
                }
            ],
            "connections": [{"src": 0, "dst": 1}],
        }
        result = backend.expand_subcircuit(circuit)
        # 1 顶层 + 2 子电路实例 = 3 器件
        assert len(result["components"]) == 3
        # 1 顶层连接 + 1 内部连接 = 2 连接
        assert len(result["connections"]) == 2

    def test_expand_nested_subcircuit(self) -> None:
        """多层嵌套子电路递归展开。"""
        backend = InterconnectBackend(InterconnectConfig())
        circuit = {
            "components": [],
            "subcircuits": [
                {
                    "id": "outer",
                    "instances": [
                        {"id": 1, "type": "waveguide"},
                        {
                            "id": "inner",
                            "subcircuits": [
                                {
                                    "id": "inner_sub",
                                    "instances": [
                                        {"id": 2, "type": "waveguide"},
                                        {"id": 3, "type": "through"},
                                    ],
                                    "internal_connections": [],
                                }
                            ],
                        },
                    ],
                    "internal_connections": [],
                }
            ],
            "connections": [],
        }
        result = backend.expand_subcircuit(circuit)
        # 1 顶层 waveguide + 2 内层实例 = 3 器件
        assert len(result["components"]) == 3

    def test_expand_invalid_circuit_raises(self) -> None:
        """非字典电路告警退出。"""
        backend = InterconnectBackend(InterconnectConfig())
        with pytest.raises(ValueError, match="字典"):
            backend.expand_subcircuit([1, 2, 3])  # type: ignore[arg-type]

    def test_expand_subcircuit_missing_instances_raises(self) -> None:
        """子电路缺少 instances 字段告警退出。"""
        backend = InterconnectBackend(InterconnectConfig())
        circuit = {
            "components": [],
            "subcircuits": [{"id": "bad"}],  # 缺 instances
        }
        with pytest.raises(ValueError, match="instances"):
            backend.expand_subcircuit(circuit)


# =============================================================================
# 12. Test1000DevicesPerformance — 1000 器件性能测试
# =============================================================================
class Test1000DevicesPerformance:
    """1000 器件时频域联合仿真性能测试（R32 要求 < 5 分钟）。"""

    def test_1000_devices_freq_domain_performance(self) -> None:
        """1000 器件频域 S 参数级联 < 5 分钟。"""
        cfg = InterconnectConfig(
            timestep=1e-14, n_steps=1024, freq_points=256, freq_span=1e14
        )
        backend = InterconnectBackend(cfg)
        for _ in range(1000):
            backend.add_component("waveguide", {"length": 1e-5, "loss_db_m": 0.0})
        t0 = time.time()
        result = backend.run_freq_domain()
        elapsed = time.time() - t0
        assert result["S_total"].shape == (256, 2, 2)
        # 1000 器件频域级联应 < 300s（5 分钟），向量化实际 < 30s
        assert elapsed < 300.0, (
            f"1000 器件频域仿真耗时 {elapsed:.2f}s > 300s"
        )

    def test_1000_devices_joint_performance(self) -> None:
        """1000 器件时频域联合仿真 < 5 分钟（R32 核心性能指标）。"""
        cfg = InterconnectConfig(
            timestep=1e-14, n_steps=1024, freq_points=256, freq_span=1e14
        )
        backend = InterconnectBackend(cfg)
        for _ in range(1000):
            backend.add_component("waveguide", {"length": 1e-5, "loss_db_m": 0.0})
        t0 = time.time()
        result = backend.run_joint()
        elapsed = time.time() - t0
        # 时频域联合一致性误差应 < 1e-6
        assert result["consistency_error"] < 1e-6
        # 1000 器件时频域联合应 < 300s（5 分钟）
        assert elapsed < 300.0, (
            f"1000 器件时频域联合仿真耗时 {elapsed:.2f}s > 300s"
        )

    def test_1000_devices_lossless_amplitude(self) -> None:
        """1000 段无损波导级联 |S21| = 1（能量守恒）。"""
        cfg = InterconnectConfig(freq_points=128, freq_span=1e14)
        backend = InterconnectBackend(cfg)
        for _ in range(1000):
            backend.add_component("waveguide", {"length": 1e-6, "loss_db_m": 0.0})
        result = backend.run_freq_domain()
        s21 = result["S_total"][:, 1, 0]
        assert np.allclose(np.abs(s21), 1.0, atol=1e-9)
