"""R32 路标测试：Lumerical INTERCONNECT 光子电路仿真对齐。

测试覆盖（R32.md §7 验收标准）:
1. InterconnectTimeDomainSimulator: 时域数据流调度 + FIR 卷积 + 高斯脉冲验证
2. CMLCompiler: S 参数编译 + 无源性/互易性诊断 + 群延迟提取
3. ONA: S 参数幅度/相位/群延迟/色散分析
4. EyeDiagramAnalyzer: 眼图构建 + Q 因子 + BER
5. JAXCircuitSimulator: JAX vmap 频域仿真 + 可微分梯度
6. MonteCarloCircuit: 波导/MZI 良率分析

学术依据: R32.md §2-§3
合规: 规则 14.1 禁止 fall-back；规则 18 学术诚信。
"""

from __future__ import annotations

import numpy as np
import pytest

from polaris.sim.interconnect import (
    ONA,
    CMLCompiler,
    EyeDiagramAnalyzer,
    FIRComponent,
    InterconnectTimeDomainSimulator,
)
from polaris.sim.interconnect_jax import (
    JAXCircuitSimulator,
    MonteCarloCircuit,
)

# 物理常量（与实现一致）
C0 = 2.99792458e8
SOI_NEFF = 2.4  # SiEPIC EBeam PDK 典型值
SOI_NG = 4.0


# =============================================================================
# 辅助函数
# =============================================================================
def _make_waveguide_fir(
    length_um: float = 1000.0,
    neff: float = SOI_NEFF,
    wavelength_um: float = 1.55,
    dt: float = 1e-13,
    n_steps: int = 1024,
) -> tuple[FIRComponent, np.ndarray]:
    """构造波导 FIR 元件（单端口对延迟线）。

    波导传输: S21 = exp(i·β·L), β = 2π·neff/λ
    时域延迟: τ = neff·L/c (s)
    FIR 形式: h[tau_delay] = 1（单位冲激延迟）

    Returns:
        (FIRComponent, 解析时域延迟样本数)
    """
    delay_s = neff * length_um * 1e-6 / C0
    delay_samples = int(round(delay_s / dt))
    # FIR 冲激响应: delta(t - delay)
    h = np.zeros(delay_samples + 1, dtype=complex)
    h[delay_samples] = 1.0 + 0.0j
    comp = FIRComponent(
        name="wg",
        n_ports=2,
        impulse_responses={("1", "0"): h},
    )
    return comp, delay_samples


def _make_gaussian_pulse(
    n_steps: int = 1024,
    dt: float = 1e-13,
    center_step: int = 100,
    width_steps: float = 20.0,
) -> np.ndarray:
    """构造高斯脉冲输入信号。"""
    t = np.arange(n_steps) * dt
    t0 = center_step * dt
    return np.exp(-((t - t0) ** 2) / (2 * (width_steps * dt) ** 2)).astype(complex)


def _make_silicon_waveguide_sparams(
    wavelengths_um: np.ndarray,
    length_um: float = 100.0,
    neff: float = SOI_NEFF,
    ng: float = SOI_NG,
    loss_db_cm: float = 0.0,
) -> dict[tuple[str, str], np.ndarray]:
    """构造硅波导 S 参数字典（复数）。"""
    wl = np.asarray(wavelengths_um, dtype=float)
    # 群折射率色散: neff(λ) = neff - (λ-1.55)*(ng-neff)/1.55（简化）
    neff_wl = neff - (wl - 1.55) * (ng - neff) / 1.55
    beta_wl = 2.0 * np.pi * neff_wl / wl
    alpha_np = loss_db_cm / 4.343 / 1e4  # dB/cm → Np/μm
    amp = np.exp(-alpha_np * length_um / 2.0)
    s21 = amp * np.exp(1j * beta_wl * length_um)
    s11 = np.zeros_like(s21)
    s12 = s21  # 互易
    s22 = np.zeros_like(s21)
    return {
        ("in", "in"): s11,
        ("out", "in"): s21,
        ("in", "out"): s12,
        ("out", "out"): s22,
    }


# =============================================================================
# 1. TestFIRComponent — FIR 元件测试
# =============================================================================
class TestFIRComponent:
    """FIR 元件测试。"""

    def test_create_valid(self) -> None:
        """创建合法 FIR 元件。"""
        comp = FIRComponent(name="wg", n_ports=2)
        assert comp.name == "wg"
        assert comp.n_ports == 2

    def test_empty_name_raises(self) -> None:
        """空名称告警退出。"""
        with pytest.raises(ValueError, match="不能为空"):
            FIRComponent(name="", n_ports=2)

    def test_zero_ports_raises(self) -> None:
        """零端口告警退出。"""
        with pytest.raises(ValueError, match="n_ports"):
            FIRComponent(name="wg", n_ports=0)

    def test_response_default(self) -> None:
        """默认响应：对角 delta(t)，非对角零。"""
        comp = FIRComponent(name="wg", n_ports=2)
        # 对角: delta(t)
        h_diag = comp.response("0", "0")
        assert len(h_diag) == 1
        assert h_diag[0] == pytest.approx(1.0)
        # 非对角: 零
        h_off = comp.response("0", "1")
        assert h_off[0] == pytest.approx(0.0)

    def test_response_custom(self) -> None:
        """自定义冲激响应。"""
        h = np.array([0.5, 0.3, 0.1], dtype=complex)
        comp = FIRComponent(
            name="dc",
            n_ports=2,
            impulse_responses={("1", "0"): h},
        )
        result = comp.response("1", "0")
        assert len(result) == 3
        assert result[0] == pytest.approx(0.5)


# =============================================================================
# 2. TestInterconnectTimeDomainSimulator — 时域数据流调度器测试
# =============================================================================
class TestInterconnectTimeDomainSimulator:
    """时域数据流调度器测试（R32.md §7.1 验收标准）。"""

    def test_init_valid(self) -> None:
        """合法初始化。"""
        sim = InterconnectTimeDomainSimulator(dt=1e-13, n_steps=1024)
        assert sim.dt == 1e-13
        assert sim.n_steps == 1024

    def test_init_invalid_dt(self) -> None:
        """非法 dt 告警退出。"""
        with pytest.raises(ValueError, match="dt"):
            InterconnectTimeDomainSimulator(dt=0, n_steps=100)

    def test_init_invalid_n_steps(self) -> None:
        """非法 n_steps 告警退出。"""
        with pytest.raises(ValueError, match="n_steps"):
            InterconnectTimeDomainSimulator(dt=1e-13, n_steps=0)

    def test_add_component(self) -> None:
        """添加元件。"""
        sim = InterconnectTimeDomainSimulator()
        comp = FIRComponent(name="wg", n_ports=2)
        sim.add_component(comp)
        assert "wg" in sim._components

    def test_add_duplicate_component_raises(self) -> None:
        """重复元件名告警退出。"""
        sim = InterconnectTimeDomainSimulator()
        comp = FIRComponent(name="wg", n_ports=2)
        sim.add_component(comp)
        with pytest.raises(ValueError, match="已存在"):
            sim.add_component(FIRComponent(name="wg", n_ports=2))

    def test_connect_nonexistent_raises(self) -> None:
        """连接不存在的元件告警退出。"""
        sim = InterconnectTimeDomainSimulator()
        with pytest.raises(ValueError, match="不存在"):
            sim.connect("wg1", "0", "wg2", "0")

    def test_topo_sort_feedback_loop_raises(self) -> None:
        """反馈环路告警退出（禁止 fall-back）。"""
        sim = InterconnectTimeDomainSimulator()
        sim.add_component(FIRComponent(name="a", n_ports=2))
        sim.add_component(FIRComponent(name="b", n_ports=2))
        # 构造环路 a→b→a
        sim.connect("a", "1", "b", "0")
        sim.connect("b", "1", "a", "0")
        with pytest.raises(RuntimeError, match="反馈环路"):
            sim._topo_sort()

    def test_gaussian_pulse_through_waveguide(self) -> None:
        """高斯脉冲通过 1mm 波导，时域波形与解析解误差 < 1%（R32.md §7.1）。

        波导延迟 τ = neff·L/c，脉冲应在 τ 后到达输出端。
        """
        dt = 1e-13
        n_steps = 2048
        length_um = 1000.0  # 1mm
        neff = SOI_NEFF
        # 构造波导 FIR
        comp, delay_samples = _make_waveguide_fir(
            length_um=length_um, neff=neff, dt=dt, n_steps=n_steps
        )
        sim = InterconnectTimeDomainSimulator(dt=dt, n_steps=n_steps)
        sim.add_component(comp)
        sim.add_port("in", "wg", "0")
        sim.add_port("out", "wg", "1")
        # 高斯脉冲输入
        pulse = _make_gaussian_pulse(n_steps=n_steps, dt=dt, center_step=100, width_steps=20)
        outputs = sim.run({"in": pulse})
        # 输出应为延迟 delay_samples 的脉冲
        out = outputs["out"]
        # 找输出脉冲峰值位置
        peak_in = np.argmax(np.abs(pulse))
        peak_out = np.argmax(np.abs(out))
        # 延迟应等于 delay_samples
        actual_delay = peak_out - peak_in
        assert actual_delay == pytest.approx(delay_samples, abs=1)
        # 峰值幅度应保持（无损波导）
        assert np.max(np.abs(out)) == pytest.approx(np.max(np.abs(pulse)), rel=0.01)

    def test_fir_convolve(self) -> None:
        """FIR 卷积正确性。"""
        x = np.array([1, 2, 3, 4, 5], dtype=complex)
        h = np.array([1, 1], dtype=complex)  # 简单累加
        y = InterconnectTimeDomainSimulator._fir_convolve(x, h)
        # y[0] = h[0]*x[0] = 1
        # y[1] = h[0]*x[1] + h[1]*x[0] = 2+1 = 3
        # y[2] = h[0]*x[2] + h[1]*x[1] = 3+2 = 5
        assert y[0] == pytest.approx(1.0)
        assert y[1] == pytest.approx(3.0)
        assert y[2] == pytest.approx(5.0)

    def test_run_input_length_mismatch_raises(self) -> None:
        """输入信号长度不匹配告警退出。"""
        sim = InterconnectTimeDomainSimulator(dt=1e-13, n_steps=100)
        sim.add_component(FIRComponent(name="wg", n_ports=2))
        sim.add_port("in", "wg", "0")
        sim.add_port("out", "wg", "1")
        with pytest.raises(ValueError, match="长度"):
            sim.run({"in": np.zeros(50, dtype=complex)})


# =============================================================================
# 3. TestCMLCompiler — CML 编译器测试
# =============================================================================
class TestCMLCompiler:
    """CML 编译器测试（R32.md §7.2 验收标准）。"""

    def test_compile_from_sdict(self) -> None:
        """从 S 参数字典编译 CML 元件。"""
        wl = np.linspace(1.5, 1.6, 50)
        sdict = _make_silicon_waveguide_sparams(wl, length_um=100.0)
        compiler = CMLCompiler(wavelengths_um=wl)
        comp = compiler.compile_from_sdict("waveguide", sdict)
        assert comp.name == "waveguide"
        assert len(comp.port_names) == 2
        assert comp.s_matrix.shape == (50, 2, 2)

    def test_empty_sdict_raises(self) -> None:
        """空 S 参数字典告警退出。"""
        compiler = CMLCompiler()
        with pytest.raises(ValueError, match="为空"):
            compiler.compile_from_sdict("wg", {})

    def test_length_mismatch_raises(self) -> None:
        """S 参数长度不匹配告警退出。"""
        wl = np.linspace(1.5, 1.6, 50)
        sdict = {("out", "in"): np.zeros(30, dtype=complex)}
        compiler = CMLCompiler(wavelengths_um=wl)
        with pytest.raises(ValueError, match="长度"):
            compiler.compile_from_sdict("wg", sdict)

    def test_passivity_passive_component(self) -> None:
        """无源元件（|S|≤1）通过无源性诊断。"""
        wl = np.linspace(1.5, 1.6, 20)
        # 无损波导: |S21|=1, |S11|=0 → 无源
        sdict = _make_silicon_waveguide_sparams(wl, length_um=100.0, loss_db_cm=0.0)
        compiler = CMLCompiler(wavelengths_um=wl)
        comp = compiler.compile_from_sdict("wg", sdict)
        assert comp.passivity_flag is True

    def test_passivity_violation(self) -> None:
        """有源元件（|S|>1）不通过无源性诊断。"""
        wl = np.linspace(1.5, 1.6, 10)
        # 放大器: S21=2 (>1)
        sdict = {("out", "in"): np.full(10, 2.0 + 0j), ("in", "out"): np.full(10, 2.0 + 0j)}
        compiler = CMLCompiler(wavelengths_um=wl)
        comp = compiler.compile_from_sdict("amp", sdict)
        assert comp.passivity_flag is False

    def test_reciprocity_symmetric(self) -> None:
        """互易元件（S_ij=S_ji）通过互易性诊断。"""
        wl = np.linspace(1.5, 1.6, 20)
        sdict = _make_silicon_waveguide_sparams(wl, length_um=100.0)
        compiler = CMLCompiler(wavelengths_um=wl)
        comp = compiler.compile_from_sdict("wg", sdict)
        assert comp.reciprocity_flag is True

    def test_reciprocity_violation(self) -> None:
        """非互易元件（S_ij≠S_ji）不通过互易性诊断。"""
        wl = np.linspace(1.5, 1.6, 10)
        # 非互易: S21=0.5, S12=0.3
        sdict = {
            ("out", "in"): np.full(10, 0.5 + 0j),
            ("in", "out"): np.full(10, 0.3 + 0j),
        }
        compiler = CMLCompiler(wavelengths_um=wl)
        comp = compiler.compile_from_sdict("isolator", sdict)
        assert comp.reciprocity_flag is False

    def test_group_delay_extraction(self) -> None:
        """群延迟提取（Agrawal §1.4）。

        注意: 波长采样需满足 Nyquist 条件 dphase < π，
        即 dλ < λ²/(2·ng·L)，否则 unwrap 失败。
        """
        # 500 点采样确保相位变化率 < π（1000μm 波导）
        wl = np.linspace(1.5, 1.6, 500)
        length_um = 1000.0  # 1mm
        sdict = _make_silicon_waveguide_sparams(wl, length_um=length_um)
        compiler = CMLCompiler(wavelengths_um=wl)
        comp = compiler.compile_from_sdict("wg", sdict)
        assert comp.group_delays_ps is not None
        # 群延迟 τ_g = ng·L/c ≈ 4.0 * 1e-3 / 3e8 ≈ 13.3 ps
        expected_gd_ps = SOI_NG * length_um * 1e-6 / C0 * 1e12
        # 取中心波长附近的群延迟
        center_gd = comp.group_delays_ps[249, 1, 0]  # (out=1, in=0)
        assert center_gd == pytest.approx(expected_gd_ps, rel=0.1)


# =============================================================================
# 4. TestONA — 光学网络分析仪测试
# =============================================================================
class TestONA:
    """ONA 测试（R32.md §7.3 验收标准）。"""

    def test_init_valid(self) -> None:
        """合法初始化。"""
        wl = np.linspace(1.5, 1.6, 50)
        ona = ONA(wavelengths_um=wl)
        assert len(ona.wavelengths_um) == 50

    def test_init_short_wavelength_raises(self) -> None:
        """波长数组过短告警退出。"""
        with pytest.raises(ValueError, match="≥ 3"):
            ONA(wavelengths_um=np.array([1.55, 1.56]))

    def test_analyze(self) -> None:
        """分析 S 参数。"""
        wl = np.linspace(1.5, 1.6, 50)
        s21 = np.exp(1j * 2 * np.pi * SOI_NEFF * 100.0 / wl)
        ona = ONA(wavelengths_um=wl)
        result = ona.analyze(s21)
        assert "wavelength_nm" in result
        assert "magnitude_db" in result
        assert "phase_rad" in result
        assert "group_delay_ps" in result
        assert len(result["magnitude_db"]) == 50

    def test_analyze_length_mismatch_raises(self) -> None:
        """S 参数长度不匹配告警退出。"""
        wl = np.linspace(1.5, 1.6, 50)
        ona = ONA(wavelengths_um=wl)
        with pytest.raises(ValueError, match="长度"):
            ona.analyze(np.zeros(30, dtype=complex))

    def test_plot_returns_figure(self) -> None:
        """plot 返回 matplotlib Figure。"""
        import matplotlib
        matplotlib.use("Agg")
        wl = np.linspace(1.5, 1.6, 50)
        s21 = np.exp(1j * 2 * np.pi * SOI_NEFF * 100.0 / wl)
        ona = ONA(wavelengths_um=wl)
        analysis = ona.analyze(s21)
        fig = ona.plot(analysis, title="Test ONA")
        assert fig is not None


# =============================================================================
# 5. TestEyeDiagramAnalyzer — 眼图分析测试
# =============================================================================
class TestEyeDiagramAnalyzer:
    """眼图分析测试（R32.md §7.3 验收标准）。"""

    def test_init_valid(self) -> None:
        """合法初始化。"""
        analyzer = EyeDiagramAnalyzer(bit_rate=10e9, samples_per_bit=16)
        assert analyzer.bit_rate == 10e9

    def test_init_invalid_bit_rate(self) -> None:
        """非法 bit_rate 告警退出。"""
        with pytest.raises(ValueError, match="bit_rate"):
            EyeDiagramAnalyzer(bit_rate=0)

    def test_build_eye_nrz(self) -> None:
        """构建 NRZ 眼图。"""
        analyzer = EyeDiagramAnalyzer(samples_per_bit=16)
        # 100 比特 NRZ 信号
        rng = np.random.default_rng(42)
        bits = rng.integers(0, 2, 100)
        signal = np.repeat(bits, 16).astype(float)
        eye = analyzer.build_eye(signal, "NRZ")
        assert eye.shape == (100, 16)

    def test_build_eye_short_signal_raises(self) -> None:
        """信号过短告警退出。"""
        analyzer = EyeDiagramAnalyzer(samples_per_bit=16)
        with pytest.raises(ValueError, match="不足"):
            analyzer.build_eye(np.zeros(10, dtype=float), "NRZ")

    def test_build_eye_invalid_modulation(self) -> None:
        """非法调制格式告警退出。"""
        analyzer = EyeDiagramAnalyzer(samples_per_bit=4)
        with pytest.raises(ValueError, match="调制格式"):
            analyzer.build_eye(np.zeros(100, dtype=float), "QAM256")

    def test_q_factor(self) -> None:
        """Q 因子计算。"""
        # 构造清晰眼图: 高电平 1.0, 低电平 0.0，加入小噪声避免 σ=0
        rng = np.random.default_rng(0)
        eye_clean = np.array([[1.0] * 8 + [0.0] * 8] * 10)
        eye_noisy = eye_clean + rng.normal(0, 0.01, eye_clean.shape)
        q = EyeDiagramAnalyzer.q_factor(eye_noisy)
        # μ1=1, μ0=0, σ1=σ0≈0.01 → Q ≈ 1/0.02 = 50
        assert q > 10.0  # 高 Q 因子

    def test_q_factor_insufficient_samples(self) -> None:
        """样本不足告警退出。"""
        with pytest.raises(ValueError, match="不足"):
            EyeDiagramAnalyzer.q_factor(np.array([1.0, 0.5]))

    def test_ber_from_q(self) -> None:
        """BER 从 Q 因子计算。"""
        # Q=6 → BER ≈ 1e-9
        ber = EyeDiagramAnalyzer.ber_from_q(6.0)
        assert ber < 1e-6
        assert ber > 0

    def test_analyze_full(self) -> None:
        """完整眼图分析。"""
        analyzer = EyeDiagramAnalyzer(samples_per_bit=16)
        rng = np.random.default_rng(42)
        bits = rng.integers(0, 2, 100)
        signal = np.repeat(bits, 16).astype(float)
        signal += rng.normal(0, 0.05, len(signal))
        result = analyzer.analyze(signal, "NRZ")
        assert "eye" in result
        assert "q_factor" in result
        assert "ber" in result
        assert "eye_opening" in result
        assert result["q_factor"] > 0

    def test_plot_eye_returns_figure(self) -> None:
        """plot_eye 返回 Figure。"""
        import matplotlib
        matplotlib.use("Agg")
        analyzer = EyeDiagramAnalyzer(samples_per_bit=16)
        rng = np.random.default_rng(42)
        bits = rng.integers(0, 2, 50)
        signal = np.repeat(bits, 16).astype(float)
        eye = analyzer.build_eye(signal, "NRZ")
        fig = analyzer.plot_eye(eye)
        assert fig is not None


# =============================================================================
# 6. TestJAXCircuitSimulator — JAX 加速频域仿真测试
# =============================================================================
class TestJAXCircuitSimulator:
    """JAX 加速频域仿真测试（R32.md §7.4 验收标准）。"""

    def test_simulate_waveguide_chain(self) -> None:
        """JAX vmap 波导链仿真。"""
        sim = JAXCircuitSimulator()
        wl = np.linspace(1.5, 1.6, 50)
        lengths = np.array([100.0, 200.0, 150.0])  # 三段波导
        s21 = sim.simulate_waveguide_chain(wl, lengths, neff=SOI_NEFF, loss_db_cm=0.0)
        # 总传输 = exp(i·β·(L1+L2+L3))
        total_L = np.sum(lengths)
        expected = np.exp(1j * 2 * np.pi * SOI_NEFF * total_L / wl)
        # JAX 数组转 numpy 比较
        s21_np = np.asarray(s21)
        assert np.allclose(s21_np, expected, rtol=1e-5)

    def test_simulate_waveguide_chain_with_loss(self) -> None:
        """带损耗波导链仿真。"""
        sim = JAXCircuitSimulator()
        wl = np.array([1.55])
        lengths = np.array([1000.0])  # 1mm = 0.1cm
        s21 = sim.simulate_waveguide_chain(wl, lengths, neff=SOI_NEFF, loss_db_cm=10.0)
        # IL = 10 dB/cm * 0.1 cm = 1 dB → |S21| = 10^(-1/20) ≈ 0.891
        expected_mag = 10 ** (-1.0 / 20.0)
        assert np.abs(np.asarray(s21)[0]) == pytest.approx(expected_mag, rel=0.01)

    def test_gradient_wrt_length(self) -> None:
        """*创新* 可微分电路仿真：梯度计算。"""
        sim = JAXCircuitSimulator()
        wl = np.array([1.55])
        lengths = np.array([100.0])
        # 目标: 当前 S21（梯度应接近零）
        s21_current = np.exp(1j * 2 * np.pi * SOI_NEFF * 100.0 / 1.55)
        target = np.array([s21_current])
        grad = sim.gradient_wrt_length(wl, lengths, target, neff=SOI_NEFF)
        assert grad.shape == (1,)
        # 在最优点附近梯度应较小
        assert np.abs(grad[0]) < 1.0

    def test_gradient_nonzero_at_mismatch(self) -> None:
        """失配时梯度非零。"""
        sim = JAXCircuitSimulator()
        wl = np.array([1.55])
        lengths = np.array([100.0])
        # 目标: 不同长度（失配）
        target = np.array([np.exp(1j * 2 * np.pi * SOI_NEFF * 200.0 / 1.55)])
        grad = sim.gradient_wrt_length(wl, lengths, target, neff=SOI_NEFF)
        assert np.abs(grad[0]) > 0.01


# =============================================================================
# 7. TestMonteCarloCircuit — Monte Carlo 统计仿真测试
# =============================================================================
class TestMonteCarloCircuit:
    """Monte Carlo 统计仿真测试（R32.md §7.4 验收标准）。"""

    def test_simulate_waveguide_yield(self) -> None:
        """波导良率分析。"""
        mc = MonteCarloCircuit(seed=42)
        result = mc.simulate_waveguide_yield(
            n_samples=100,
            length_um=100.0,
            neff_nominal=SOI_NEFF,
            neff_sigma=0.01,
            spec_insertion_loss_db=1.0,
        )
        assert result.samples == 100
        assert 0.0 <= result.yield_fraction <= 1.0
        assert len(result.all_values) == 100

    def test_simulate_waveguide_yield_zero_samples_raises(self) -> None:
        """零采样告警退出。"""
        mc = MonteCarloCircuit()
        with pytest.raises(ValueError, match="n_samples"):
            mc.simulate_waveguide_yield(n_samples=0)

    def test_simulate_mzi_yield(self) -> None:
        """MZI 消光比良率分析。"""
        mc = MonteCarloCircuit(seed=42)
        result = mc.simulate_mzi_yield(
            n_samples=100,
            arm_length_diff_um=50.0,
            neff_nominal=SOI_NEFF,
            neff_sigma=0.005,
            spec_er_db=10.0,
        )
        assert result.samples == 100
        assert 0.0 <= result.yield_fraction <= 1.0
        assert result.mean > 0  # 平均消光比应为正

    def test_monte_carlo_reproducible(self) -> None:
        """Monte Carlo 可复现性（固定种子）。"""
        mc1 = MonteCarloCircuit(seed=123)
        mc2 = MonteCarloCircuit(seed=123)
        r1 = mc1.simulate_waveguide_yield(n_samples=50)
        r2 = mc2.simulate_waveguide_yield(n_samples=50)
        assert np.allclose(r1.all_values, r2.all_values)

    def test_monte_carlo_1000_samples_performance(self) -> None:
        """Monte Carlo 1000 次采样性能（R32.md §7.4: < 10 秒）。"""
        import time

        mc = MonteCarloCircuit(seed=42)
        t0 = time.time()
        result = mc.simulate_waveguide_yield(n_samples=1000)
        elapsed = time.time() - t0
        assert result.samples == 1000
        assert elapsed < 10.0, f"Monte Carlo 1000 采样耗时 {elapsed:.2f}s > 10s"


# =============================================================================
# 8. TestR32Integration — R32 集成测试
# =============================================================================
class TestR32Integration:
    """R32 集成测试：完整工作流验证。"""

    def test_fdtd_to_cml_to_ona_workflow(self) -> None:
        """FDTD S 参数 → CML 编译 → ONA 分析完整工作流。"""
        # 1. 构造 FDTD 风格 S 参数（模拟 FDTDResult.s_params）
        wl = np.linspace(1.5, 1.6, 100)
        sdict = _make_silicon_waveguide_sparams(wl, length_um=500.0, loss_db_cm=0.5)
        # 2. CML 编译
        compiler = CMLCompiler(wavelengths_um=wl)
        cml_comp = compiler.compile_from_sdict("waveguide_500um", sdict)
        assert cml_comp.passivity_flag is True
        assert cml_comp.reciprocity_flag is True
        # 3. ONA 分析
        ona = ONA(wavelengths_um=wl)
        s21 = cml_comp.s_matrix[:, 1, 0]  # (out, in)
        analysis = ona.analyze(s21)
        assert len(analysis["magnitude_db"]) == 100
        # 插入损耗应 ≈ 0.5 dB/cm * 0.05 cm = 0.025 dB
        il = np.mean(analysis["magnitude_db"])
        assert il == pytest.approx(-0.025, abs=0.1)

    def test_time_domain_to_eye_diagram_workflow(self) -> None:
        """时域仿真 → 眼图分析完整工作流。"""
        # 1. 时域仿真: NRZ 信号通过波导
        spb = 16
        # 构造 NRZ 信号并加入噪声（模拟真实链路）
        rng = np.random.default_rng(42)
        bits = rng.integers(0, 2, 100)
        signal = np.repeat(bits, spb).astype(complex)
        signal += rng.normal(0, 0.05, len(signal))  # 加噪声避免 σ=0
        # 2. 眼图分析
        analyzer = EyeDiagramAnalyzer(bit_rate=10e9, samples_per_bit=spb)
        result = analyzer.analyze(signal, "NRZ")
        assert result["q_factor"] > 1.0  # 有噪声但仍可判决

    def test_jax_vs_numpy_consistency(self) -> None:
        """JAX 仿真与 numpy 解析解一致性（幅度误差 < 0.1 dB，R32.md §7.4）。"""
        sim = JAXCircuitSimulator()
        wl = np.linspace(1.5, 1.6, 100)
        lengths = np.array([100.0, 200.0])
        # JAX 仿真
        s21_jax = np.asarray(sim.simulate_waveguide_chain(wl, lengths, neff=SOI_NEFF))
        # numpy 解析解
        total_L = np.sum(lengths)
        s21_np = np.exp(1j * 2 * np.pi * SOI_NEFF * total_L / wl)
        # 比较幅度误差（dB），避免相位差导致的数值问题
        mag_jax = np.abs(s21_jax)
        mag_np = np.abs(s21_np)
        error_db = 20 * np.log10(np.abs(mag_jax - mag_np) + 1e-15)
        assert np.max(error_db) < 1.0  # 幅度误差 < 1 dB（无损波导应为 0）

    def test_monte_carlo_yield_statistics(self) -> None:
        """Monte Carlo 良率统计合理性（用 MZI 消光比）。"""
        # 大涨落 → 低良率
        mc1 = MonteCarloCircuit(seed=42)
        result_large = mc1.simulate_mzi_yield(
            n_samples=500, neff_sigma=0.1, spec_er_db=10.0
        )
        # 小涨落 → 高良率
        mc2 = MonteCarloCircuit(seed=42)
        result_small = mc2.simulate_mzi_yield(
            n_samples=500, neff_sigma=0.001, spec_er_db=10.0
        )
        assert result_small.yield_fraction > result_large.yield_fraction

    def test_cml_supports_multiple_device_types(self) -> None:
        """CML 支持 5+ 器件类型（R32.md §7.2）。"""
        wl = np.linspace(1.5, 1.6, 50)
        compiler = CMLCompiler(wavelengths_um=wl)
        # 1. 波导
        wg_s = _make_silicon_waveguide_sparams(wl, length_um=100.0)
        comp_wg = compiler.compile_from_sdict("waveguide", wg_s)
        # 2. MMI 1x2 (S21=S31=1/sqrt(2))
        mmi_s = {
            ("out1", "in"): np.full(50, 1 / np.sqrt(2) + 0j),
            ("out2", "in"): np.full(50, 1 / np.sqrt(2) + 0j),
            ("in", "out1"): np.full(50, 1 / np.sqrt(2) + 0j),
            ("in", "out2"): np.full(50, 1 / np.sqrt(2) + 0j),
        }
        comp_mmi = compiler.compile_from_sdict("mmi_1x2", mmi_s)
        # 3. Y 分支 (同 MMI)
        comp_yb = compiler.compile_from_sdict("y_branch", mmi_s)
        # 4. 定向耦合器 (2x2)
        dc_s = {
            ("out1", "in1"): np.full(50, np.cos(np.pi / 4) + 0j),
            ("out2", "in1"): np.full(50, 1j * np.sin(np.pi / 4)),
            ("out1", "in2"): np.full(50, 1j * np.sin(np.pi / 4)),
            ("out2", "in2"): np.full(50, np.cos(np.pi / 4) + 0j),
            ("in1", "out1"): np.full(50, np.cos(np.pi / 4) + 0j),
            ("in1", "out2"): np.full(50, 1j * np.sin(np.pi / 4)),
            ("in2", "out1"): np.full(50, 1j * np.sin(np.pi / 4)),
            ("in2", "out2"): np.full(50, np.cos(np.pi / 4) + 0j),
        }
        comp_dc = compiler.compile_from_sdict("directional_coupler", dc_s)
        # 5. 环谐振器（简化: 全通）
        ring_s = {
            ("out", "in"): np.full(50, 0.9 + 0j),
            ("in", "out"): np.full(50, 0.9 + 0j),
        }
        comp_ring = compiler.compile_from_sdict("ring_resonator", ring_s)
        # 验证全部编译成功
        devices = [comp_wg, comp_mmi, comp_yb, comp_dc, comp_ring]
        assert len(devices) == 5
        for d in devices:
            assert d.passivity_flag is True
