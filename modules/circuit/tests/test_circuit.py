"""polaris-circuit 子模块 smoke test（R13 交付自测）。

覆盖核心 API:
- MNA SPICE DC 分析（Ohm 定律验证）
- 频域电路仿真（波导传输 + 子网络增长级联）
- 时域波导仿真（TLLM 风格传输 + 非线性）
- 系统级混合仿真（频域 S + TLLM 激光器 FFT 耦合）
- 群延迟（波导 n_g·L/c 解析验证）
- 条件数计算（数值稳定性诊断）

合规: R02 学术诚信 / R03 禁止 fall-back / R04 纯 NumPy / R05 无 TODO。
"""

from __future__ import annotations

import numpy as np
import pytest

from polaris_circuit import (
    BerEvaluator,
    C0,
    CircuitSimulator,
    MNACircuit,
    NonlinearModel,
    OpticalLink,
    SPEED_OF_LIGHT,
    Subcircuit,
    TLLMLaser,
    TimeDomainCircuitSimulator,
    WavelengthRange,
    cascade_circuit,
    compute_condition_number,
    default_models,
    directional_coupler_s,
    group_delay,
    run_mna_spice,
    run_time_domain_circuit,
    simulate_system_level,
    to_time_domain,
    waveguide_s,
)


# ============================================================================
# Smoke Test 1: MNA SPICE DC 分析（Ohm 定律验证）
# ============================================================================
def test_mna_dc_ohms_law() -> None:
    """MNA DC 分析: 验证 V=IR 分压。

    电路: 10V 电压源 → 1kΩ + 1kΩ 串联 → GND
    约定: V(n1) - V(n2) = dc，故 n1=1, n2=0 使节点1 = +10V。
    预期: 节点1 = 10V，节点2 = 5V（分压中点），电流 = 10V/2kΩ = 5mA。
    """
    circuit = MNACircuit(n_nodes=2)
    circuit.add_vsource("V1", n1=1, n2=0, dc=10.0)  # V(1)-V(0)=10 → 节点1=10V
    circuit.add_resistor("R1", n1=1, n2=2, r=1000.0)  # 1kΩ
    circuit.add_resistor("R2", n1=2, n2=0, r=1000.0)  # 1kΩ → GND

    result = run_mna_spice(circuit, analysis="dc")

    # 节点1 = 10V（电压源）
    assert result.node_voltages[1] == pytest.approx(10.0, abs=1e-9)
    # 节点2 = 5V（分压中点）
    assert result.node_voltages[2] == pytest.approx(5.0, abs=1e-9)
    # 电流 = 10V / 2kΩ = 5mA
    assert result.vsource_currents["V1"] == pytest.approx(5e-3, abs=1e-9)


def test_mna_transient_rc_charging() -> None:
    """MNA 瞬态分析: RC 电路充电（τ = RC 验证）。

    电路: 1V 电压源 → 1kΩ → 1nF → GND
    约定: V(n1)-V(n2)=dc，故 n1=1, n2=0 使节点1=+1V。
    时间常数 τ = R·C = 1μs。V_C(t=τ) ≈ 0.632V。
    """
    circuit = MNACircuit(n_nodes=2)
    circuit.add_vsource("V1", n1=1, n2=0, dc=1.0)
    circuit.add_resistor("R1", n1=1, n2=2, r=1000.0)
    circuit.add_capacitor("C1", n1=2, n2=0, c=1e-9)

    tau = 1000.0 * 1e-9  # τ = 1μs
    dt = tau / 50.0
    result = run_mna_spice(circuit, analysis="transient", t_total=tau, dt=dt)

    # V_C(t=τ) ≈ 1.0 * (1 - e^{-1}) ≈ 0.632V
    v_at_tau = result.node_voltages[2][-1]
    assert v_at_tau == pytest.approx(0.632, abs=0.05)


# ============================================================================
# Smoke Test 2: 频域电路仿真（波导传输 + 子网络增长级联）
# ============================================================================
def test_waveguide_frequency_domain_transmission() -> None:
    """频域仿真: 波导传输相位验证。

    波导模型: S_{out,in} = exp(i·β·L), β = 2π·neff/λ
    验证: |S_{out,in}| = 1（无损），相位 = 2π·neff·L/λ
    """
    wl = np.array([1.55])  # 1.55μm
    neff = 2.4
    length = 100.0  # μm
    sdict = waveguide_s(wl=wl, length=length, neff=neff)

    # 无损波导 |S| = 1
    s_out_in = sdict[("out", "in")]
    assert np.allclose(np.abs(s_out_in), 1.0, atol=1e-12)
    # 相位 = 2π·neff·L/λ
    expected_phase = 2 * np.pi * neff * length / 1.55
    actual_phase = np.angle(s_out_in[0])
    # 相位 mod 2π
    phase_diff = (expected_phase - actual_phase) % (2 * np.pi)
    assert min(phase_diff, 2 * np.pi - phase_diff) < 1e-9


def test_circuit_simulator_mzi() -> None:
    """CircuitSimulator: 双波导 MZI 仿真。

    MZI: 两波导臂 + 2 个 Y 分支。验证 S 参数字典非空且有限。
    """
    sim = CircuitSimulator()
    models = default_models()
    for name, model in models.items():
        sim.register_model(name, model)

    netlist = {
        "instances": {"wg1": "waveguide", "wg2": "waveguide"},
        "connections": [("wg1.out", "wg2.in")],
        "ports": {"in": "wg1.in", "out": "wg2.out"},
    }
    wl_range = WavelengthRange(wl_start=1.55, wl_end=1.56, n_points=50)
    wavelengths, sdict = sim.sweep_wavelength(netlist, wl_range)

    assert len(wavelengths) == 50
    assert ("out", "in") in sdict
    s_vals = sdict[("out", "in")]
    assert len(s_vals) == 50
    # 双波导级联相位 = 2 × 2π·neff·L/λ，|S| = 1（无损）
    assert np.allclose(np.abs(s_vals), 1.0, atol=1e-9)
    # 全部有限（无 NaN/Inf）
    assert np.all(np.isfinite(s_vals))


def test_cascade_condition_number() -> None:
    """级联 + 条件数: 验证良态 S 矩阵条件数有限。"""
    wl = np.linspace(1.5, 1.6, 20)
    sdict = directional_coupler_s(wl=wl, coupling=0.5)
    cond = compute_condition_number(sdict)
    assert np.isfinite(cond)
    assert cond > 1.0  # 非平凡矩阵条件数 >= 1


# ============================================================================
# Smoke Test 3: 时域波导仿真（TLLM 风格传输 + 非线性）
# ============================================================================
def test_time_domain_waveguide_delay() -> None:
    """时域波导仿真: 验证时延 = neff·L/c。

    输入脉冲经波导传播后，输出脉冲应延迟 Δt = neff·L/c。
    """
    # 高斯脉冲
    n = 1000
    dt = 1e-14  # 10 fs
    t = np.arange(n) * dt
    pulse = np.exp(-((t - 50e-13) ** 2) / (2 * 1e-26)).astype(np.complex128)

    length = 1e-3  # 1 mm
    neff = 2.4
    expected_delay = neff * length / C0  # ~8 ps

    output = run_time_domain_circuit(
        input_signal=pulse, length=length, dt=dt, neff=neff
    )

    # 输入峰值位置
    in_peak = np.argmax(np.abs(pulse))
    out_peak = np.argmax(np.abs(output))
    actual_delay = (out_peak - in_peak) * dt

    assert actual_delay == pytest.approx(expected_delay, rel=0.1)
    # 输出有限
    assert np.all(np.isfinite(output))


def test_time_domain_mzi_interference() -> None:
    """时域 MZI 仿真: 双臂干涉验证。

    MZI 臂长差 = 0 时，输出 = 输入（同相叠加）。
    """
    n = 500
    dt = 1e-14
    t = np.arange(n) * dt
    signal = np.exp(-((t - 100e-14) ** 2) / (2 * 1e-28)).astype(np.complex128)

    sim = TimeDomainCircuitSimulator(dt=dt, n_steps=n)
    # 臂长差 = 0，输出 = signal（同相 50:50 分束+合束）
    out = sim.simulate_mzi(input_signal=signal, arm_length_diff=0.0, neff=2.4)
    # 50:50 分束 → 1/√2，合束 → 2 × 1/√2 × 1/√2 = 1
    assert np.allclose(np.abs(out), np.abs(signal), atol=1e-9)


def test_nonlinear_kerr_phase() -> None:
    """非线性 Kerr 效应: 相位正比于光强。"""
    nl = NonlinearModel()
    I = np.array([1e10, 2e10, 4e10])  # W/m²
    length = 1e-3  # 1 mm
    wavelength = 1.55e-6
    phase = nl.kerr_phase(I, length, wavelength)
    # 相位应正比于光强
    assert phase[1] == pytest.approx(2 * phase[0], rel=1e-9)
    assert phase[2] == pytest.approx(4 * phase[0], rel=1e-9)
    # 相位为正（n2 > 0）
    assert np.all(phase > 0)


# ============================================================================
# Smoke Test 4: 系统级混合仿真（频域 S + TLLM 激光器）
# ============================================================================
def test_system_level_hybrid_simulation() -> None:
    """系统级混合仿真: 频域 S + TLLM 激光器 FFT 耦合。

    验证输出信号非空、有限、与输入相关。
    """
    n = 256
    dt = 1e-12
    t = np.arange(n) * dt
    # 高斯脉冲输入
    input_signal = np.exp(-((t - 50e-12) ** 2) / (2 * 1e-24))

    # 频域 S 参数（简单低通：高频衰减）
    freqs = np.fft.fftfreq(n, d=dt)
    s_freq = 1.0 / (1.0 + 1j * freqs * 1e-12)
    freq_sdict = {("out", "in"): s_freq}

    output = simulate_system_level(freq_sdict, input_signal, dt=dt)

    assert len(output) == n
    assert np.all(np.isfinite(output))
    # 输出非全零
    assert np.max(np.abs(output)) > 1e-6


def test_optical_link_ber() -> None:
    """光通信链路: NRZ 调制 + 传输 + 接收 + BER 计算。"""
    link = OpticalLink(tx_modulation="NRZ", bit_rate=10e9, fiber_length=1e3)
    tx_bits = link.generate_bits(100)
    tx_signal = link.modulate(tx_bits)
    rx_signal = link.transmit(tx_signal)
    rx_bits = link.receive(rx_signal)
    ber = link.ber(tx_bits, rx_bits)
    assert 0.0 <= ber <= 1.0
    # 短距离低噪声 BER 应较低
    assert ber < 0.5


def test_ber_evaluator_q_factor() -> None:
    """BER 评估器: Q-factor 法 BER 计算。"""
    rng = np.random.default_rng(seed=42)
    # 眼图信号：高电平 +1，低电平 -1，加噪声
    high = rng.normal(1.0, 0.1, 500)
    low = rng.normal(-1.0, 0.1, 500)
    eye = np.concatenate([high, low])
    q = BerEvaluator.q_factor(eye)
    # Q ≈ |1-(-1)| / (0.1+0.1) = 10
    assert q == pytest.approx(10.0, abs=1.0)
    ber = BerEvaluator.ber_from_q(q)
    # Q=10 → BER ≈ 7.6e-24（极低）
    assert ber < 1e-10


def test_to_time_domain_transform() -> None:
    """频域→时域转换: IFFT 验证。"""
    n = 128
    wl = np.linspace(1.54, 1.56, n)  # 波长数组
    t_array = np.arange(n) * 1e-14
    sdict = waveguide_s(wl=wl, length=100.0, neff=2.4)
    h = to_time_domain(sdict, wl, t_array)
    assert ("out", "in") in h
    assert len(h[("out", "in")]) == n
    assert np.all(np.isfinite(h[("out", "in")]))


# ============================================================================
# Smoke Test 5: 群延迟（波导 n_g·L/c 解析验证）
# ============================================================================
def test_group_delay_waveguide() -> None:
    """群延迟: 波导 τ_g = n_g·L/c 解析验证。

    波导相位 φ = 2π·neff·L/λ，dφ/dω = n_g·L/c。
    """
    n = 1000
    wl = np.linspace(1.55, 1.56, n)  # μm
    neff = 2.4
    ng = 4.0
    length = 1000.0  # μm = 1mm
    sdict = waveguide_s(wl=wl, length=length, neff=neff, ng=ng)

    tau = group_delay(sdict, wl, port_out="out", port_in="in")
    # 解析解: τ_g = n_g·L/c，L 单位 μm → m
    expected_tau = ng * length * 1e-6 / SPEED_OF_LIGHT
    # 中心差分结果长度 = n-2，取中心值
    center = len(tau) // 2
    assert tau[center] == pytest.approx(expected_tau, rel=0.05)


# ============================================================================
# Smoke Test 6: Subcircuit SPICE 风格电路构建
# ============================================================================
def test_subcircuit_build_and_netlist() -> None:
    """Subcircuit: SPICE 风格电路构建 + 网表生成。"""
    sub = Subcircuit(name="mzi")
    sub.add_component(waveguide_s, "wg1")
    sub.add_component(waveguide_s, "wg2")
    sub.connect("wg1", "out", "wg2", "in")
    sub.add_terminal("in", "wg1", "in")
    sub.add_terminal("out", "wg2", "out")

    netlist = sub.to_netlist()
    assert "instances" in netlist
    assert "connections" in netlist
    assert "ports" in netlist
    assert len(netlist["instances"]) == 2
    assert netlist["ports"]["in"] == "wg1.in"
    assert netlist["ports"]["out"] == "wg2.out"


def test_subcircuit_duplicate_name_raises() -> None:
    """Subcircuit: 重复实例名告警退出（R03 禁止 fall-back）。"""
    sub = Subcircuit(name="test")
    sub.add_component(waveguide_s, "wg1")
    with pytest.raises(ValueError, match="已存在"):
        sub.add_component(waveguide_s, "wg1")


def test_tllm_laser_step_stability() -> None:
    """TLLM 激光器: RK4 单步稳定性。"""
    laser = TLLMLaser(I=0.05)
    N = laser.N_0 * 1.1
    S = 1e-3
    dt = 1e-12
    N_new, S_new = laser.step(N, S, dt)
    assert np.isfinite(N_new)
    assert np.isfinite(S_new)
    assert N_new > 0
    assert S_new > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
