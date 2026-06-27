"""PICWave 时域仿真后端 R15 测试。

测试内容:
1. TestPICWaveConfig: 配置参数验证（非法参数 raise）
2. TestNodeConnection: 节点添加与连接（类型校验/越界 raise）
3. TestBasicSimulation: 基础时域仿真（线性波导链）
4. TestKerrNonlinear: Kerr 非线性（功率相关相移，|E| 守恒）
5. TestTPAAbsorption: TPA 双光子吸收（功率损耗）
6. TestCarrierLifetime: 自由载流子寿命（衰减 + 生成）
7. TestSParamExtraction: S 参数 FFT 提取（频率定位）
8. TestEnergyConservation: 无源线性系统能量守恒
9. Test200DevicesPerformance: 200 器件时域仿真 < 60s
10. TestCFLCondition: CFL 条件违反即 raise

来源（R02 学术诚信）:
- R15 路标 PICWave 时域仿真
- Lowery 1997 TLLM: https://ieeexplore.ieee.org/document/601500
- Agrawal 2001 Nonlinear Fiber Optics:
  https://www.sciencedirect.com/book/9780123695161/nonlinear-fiber-optics
- Lin et al. 2007 Si 非线性参数:
  https://opg.optica.org/oe/abstract.cfm?uri=oe-15-6-3454
- Courant 1928 CFL: https://link.springer.com/article/10.1007/BF01448839
"""

from __future__ import annotations

import time

import numpy as np
import pytest

from polaris.sim.picwave_backend import (
    C0,
    H_PLANCK,
    PICWaveConfig,
    PICWaveTimeDomainBackend,
)


# ---------------------------------------------------------------------------
# 1. TestPICWaveConfig — 配置参数验证
# ---------------------------------------------------------------------------
class TestPICWaveConfig:
    """配置参数校验（R03 禁止 fall-back，非法即 raise）。"""

    def test_config_validation_default(self):
        """默认配置合法。"""
        cfg = PICWaveConfig()
        assert cfg.dt > 0
        assert cfg.n_steps > 0
        assert cfg.wavelength > 0

    @pytest.mark.parametrize("bad_field,bad_val", [
        ("dt", 0.0), ("dt", -1e-14),
        ("n_steps", 0), ("n_steps", -10),
        ("wavelength", 0.0), ("wavelength", -1e-6),
        ("n_eff", 0.0), ("n_eff", -1.0),
        ("n_g", 0.0),
        ("n2", -1e-18), ("beta_tpa", -1e-11),
        ("tau_carrier", 0.0), ("tau_carrier", -1e-9),
        ("A_eff", 0.0), ("A_eff", -1e-13),
    ])
    def test_config_invalid_raises(self, bad_field, bad_val):
        """非法参数必须 raise ValueError（禁止 fall-back）。"""
        with pytest.raises(ValueError):
            PICWaveConfig(**{bad_field: bad_val})


# ---------------------------------------------------------------------------
# 2. TestNodeConnection — 节点添加与连接
# ---------------------------------------------------------------------------
class TestNodeConnection:
    """节点与连接管理。"""

    def test_add_node(self):
        """添加节点返回递增 ID。"""
        backend = PICWaveTimeDomainBackend(PICWaveConfig())
        nid0 = backend.add_node("waveguide", {"length": 1e-6})
        nid1 = backend.add_node("nonlinear", {"length": 2e-6})
        assert nid0 == 0
        assert nid1 == 1
        assert len(backend.nodes) == 2
        assert backend.nodes[0].node_type == "waveguide"
        assert backend.nodes[1].length == 2e-6

    def test_add_node_invalid_type_raises(self):
        """未知节点类型 raise。"""
        backend = PICWaveTimeDomainBackend(PICWaveConfig())
        with pytest.raises(ValueError, match="未知节点类型"):
            backend.add_node("magic_waveguide")

    def test_add_node_invalid_length_raises(self):
        """节点长度非正 raise。"""
        backend = PICWaveTimeDomainBackend(PICWaveConfig())
        with pytest.raises(ValueError, match="length"):
            backend.add_node("waveguide", {"length": 0.0})

    def test_connect(self):
        """连接两节点。"""
        backend = PICWaveTimeDomainBackend(PICWaveConfig())
        n0 = backend.add_node("source", {"length": 1e-6})
        n1 = backend.add_node("waveguide", {"length": 1e-6})
        backend.connect(n0, n1, delay=1e-14)
        assert len(backend.connections) == 1
        assert backend.connections[0].src_id == n0
        assert backend.connections[0].dst_id == n1

    def test_connect_out_of_range_raises(self):
        """节点 ID 越界 raise。"""
        backend = PICWaveTimeDomainBackend(PICWaveConfig())
        backend.add_node("source", {"length": 1e-6})
        with pytest.raises(ValueError, match="越界"):
            backend.connect(0, 5, delay=1e-14)
        with pytest.raises(ValueError, match="越界"):
            backend.connect(-1, 0, delay=1e-14)

    def test_connect_negative_delay_raises(self):
        """负延迟 raise。"""
        backend = PICWaveTimeDomainBackend(PICWaveConfig())
        n0 = backend.add_node("source", {"length": 1e-6})
        n1 = backend.add_node("waveguide", {"length": 1e-6})
        with pytest.raises(ValueError, match="delay 不能为负"):
            backend.connect(n0, n1, delay=-1e-14)


# ---------------------------------------------------------------------------
# 3. TestBasicSimulation — 基础时域仿真
# ---------------------------------------------------------------------------
class TestBasicSimulation:
    """基础线性时域仿真。"""

    @staticmethod
    def _build_chain(n_steps: int = 1024) -> PICWaveTimeDomainBackend:
        """构建 source -> waveguide -> detector 链。"""
        cfg = PICWaveConfig(dt=1e-14, n_steps=n_steps)
        backend = PICWaveTimeDomainBackend(cfg)
        n0 = backend.add_node("source", {"length": 2e-6, "alpha": 0.0})
        n1 = backend.add_node("waveguide", {"length": 2e-6, "alpha": 0.0})
        n2 = backend.add_node("detector", {"length": 2e-6, "alpha": 0.0})
        backend.connect(n0, n1, delay=1e-14, length=0.0)
        backend.connect(n1, n2, delay=1e-14, length=0.0)
        backend.mark_port(0, n0)
        backend.mark_port(1, n1)
        backend.mark_port(2, n2)
        return backend

    def test_run_basic(self):
        """基础仿真：注入脉冲，各端口均有非零信号。"""
        backend = self._build_chain()
        result = backend.run(source_port=0)
        assert result["t"].shape == (1024,)
        assert set(result["E_ports"].keys()) == {0, 1, 2}
        e1 = result["E_ports"][1]
        e2 = result["E_ports"][2]
        # 端口 1、2 应接收到非零信号（脉冲传播到达）
        assert np.max(np.abs(e1)) > 1e-10, "端口 1 无信号"
        assert np.max(np.abs(e2)) > 1e-10, "端口 2 无信号"
        # 端口 2 信号应晚于端口 1（因果性，额外延迟）
        t_peak1 = result["t"][np.argmax(np.abs(e1))]
        t_peak2 = result["t"][np.argmax(np.abs(e2))]
        assert t_peak2 >= t_peak1

    def test_run_no_port_raises(self):
        """无端口定义 raise（禁止 fall-back）。"""
        cfg = PICWaveConfig(dt=1e-14, n_steps=64)
        backend = PICWaveTimeDomainBackend(cfg)
        backend.add_node("source", {"length": 2e-6})
        with pytest.raises(RuntimeError, match="无端口"):
            backend.run()

    def test_run_unknown_source_port_raises(self):
        """未标记源端口 raise。"""
        backend = self._build_chain(n_steps=64)
        with pytest.raises(RuntimeError, match="未标记"):
            backend.run(source_port=99)


# ---------------------------------------------------------------------------
# 4. TestKerrNonlinear — Kerr 非线性
# ---------------------------------------------------------------------------
class TestKerrNonlinear:
    """Kerr 自相位调制（Agrawal §2.3）。"""

    def test_kerr_phase_shift_power_dependent(self):
        """Kerr 产生功率相关相移，且 |E| 守恒（仅相位调制）。"""
        cfg = PICWaveConfig(dt=1e-15, n_steps=64)
        backend = PICWaveTimeDomainBackend(cfg)
        E_low = np.array([1.0 + 0.0j])
        E_high = np.array([10.0 + 0.0j])
        dt = 1e-15
        E_low_new = backend._step_kerr(E_low.copy(), dt)
        E_high_new = backend._step_kerr(E_high.copy(), dt)
        # Kerr 仅改相位，|E| 近似守恒（Euler 单步二阶误差 O(φ²)）
        assert abs(abs(E_low_new[0]) - abs(E_low[0])) < 1e-4
        assert abs(abs(E_high_new[0]) - abs(E_high[0])) < 1e-4
        # 相移 Δφ = v_g·γ·|E|²·dt，高功率相移更大
        phi_low = np.angle(E_low_new[0] / E_low[0])
        phi_high = np.angle(E_high_new[0] / E_high[0])
        assert phi_high > phi_low > 0
        # 相移比 ≈ 功率比 (100x)
        ratio = phi_high / phi_low
        assert 90.0 < ratio < 110.0

    def test_kerr_zero_field_no_change(self):
        """零场无相移。"""
        cfg = PICWaveConfig(dt=1e-15, n_steps=64)
        backend = PICWaveTimeDomainBackend(cfg)
        E = np.array([0.0 + 0.0j])
        E_new = backend._step_kerr(E, 1e-15)
        assert E_new[0] == 0.0


# ---------------------------------------------------------------------------
# 5. TestTPAAbsorption — TPA 双光子吸收
# ---------------------------------------------------------------------------
class TestTPAAbsorption:
    """TPA 双光子吸收（Agrawal §9.2）。"""

    def test_tpa_absorption_reduces_power(self):
        """TPA 降低 |E|，且高功率损耗比例更大。"""
        cfg = PICWaveConfig(dt=1e-15, n_steps=64, beta_tpa=0.8e-11)
        backend = PICWaveTimeDomainBackend(cfg)
        E_low = np.array([1.0 + 0.0j])
        E_high = np.array([10.0 + 0.0j])
        dt = 1e-15
        E_low_new = backend._step_tpa(E_low.copy(), dt)
        E_high_new = backend._step_tpa(E_high.copy(), dt)
        # TPA 降低功率
        assert abs(E_low_new[0]) < abs(E_low[0])
        assert abs(E_high_new[0]) < abs(E_high[0])
        # 高功率损耗比例更大（dP/P ∝ P）
        frac_low = 1.0 - abs(E_low_new[0]) / abs(E_low[0])
        frac_high = 1.0 - abs(E_high_new[0]) / abs(E_high[0])
        assert frac_high > frac_low > 0

    def test_tpa_zero_field_no_change(self):
        """零场无吸收。"""
        cfg = PICWaveConfig(dt=1e-15, n_steps=64)
        backend = PICWaveTimeDomainBackend(cfg)
        E = np.array([0.0 + 0.0j])
        E_new = backend._step_tpa(E, 1e-15)
        assert E_new[0] == 0.0


# ---------------------------------------------------------------------------
# 6. TestCarrierLifetime — 自由载流子寿命
# ---------------------------------------------------------------------------
class TestCarrierLifetime:
    """自由载流子速率方程（Agrawal §9.3）。"""

    def test_carrier_decay_without_light(self):
        """无光时载流子按 exp(-t/τ) 衰减。"""
        cfg = PICWaveConfig(dt=1e-14, n_steps=64, tau_carrier=1e-9)
        backend = PICWaveTimeDomainBackend(cfg)
        N0 = 1e20
        dt = 1e-14
        I_zero = np.array([0.0])  # 无光
        N = np.array([N0])
        N_new = backend._step_carrier(N, I_zero, dt)
        # 解析：N_new ≈ N0·(1 - dt/τ)（Euler 单步）
        expected = N0 * (1.0 - dt / cfg.tau_carrier)
        np.testing.assert_allclose(N_new[0], expected, rtol=1e-6)
        assert N_new[0] < N0

    def test_carrier_generation_with_light(self):
        """有光时载流子生成（TPA 产生电子-空穴对）。"""
        cfg = PICWaveConfig(dt=1e-14, n_steps=64, beta_tpa=0.8e-11)
        backend = PICWaveTimeDomainBackend(cfg)
        nu = C0 / cfg.wavelength
        I_strong = np.array([1e12])  # 强光 (W/m²)
        N = np.array([0.0])
        N_new = backend._step_carrier(N, I_strong, 1e-14)
        # 生成项 β·I²/(2hν) > 0
        gen = cfg.beta_tpa * I_strong[0] ** 2 / (2 * H_PLANCK * nu)
        expected = gen * 1e-14  # N 从 0 开始
        np.testing.assert_allclose(N_new[0], expected, rtol=1e-6)
        assert N_new[0] > 0

    def test_carrier_negative_raises(self):
        """载流子变负 raise（数值不稳定告警，禁止 fall-back）。"""
        cfg = PICWaveConfig(dt=1.0, n_steps=64, tau_carrier=1e-15)
        backend = PICWaveTimeDomainBackend(cfg)
        N = np.array([1.0])
        I_zero = np.array([0.0])
        # dt=1.0 >> τ，Euler 过冲导致负值
        with pytest.raises(RuntimeError, match="变负"):
            backend._step_carrier(N, I_zero, 1.0)


# ---------------------------------------------------------------------------
# 7. TestSParamExtraction — S 参数 FFT 提取
# ---------------------------------------------------------------------------
class TestSParamExtraction:
    """S 参数 FFT 提取。"""

    def test_sparam_frequency_localization(self):
        """已知正弦信号 FFT 后峰值在对应频率。"""
        cfg = PICWaveConfig(dt=1e-12, n_steps=4096)
        backend = PICWaveTimeDomainBackend(cfg)
        dt = cfg.dt
        f_target = 10e9  # 10 GHz
        t = np.arange(cfg.n_steps) * dt
        sig = np.sin(2 * np.pi * f_target * t)
        s_freq = backend.extract_sparams(sig)
        n_freq = cfg.n_steps // 2 + 1
        assert s_freq.shape == (n_freq,)
        freqs = np.fft.rfftfreq(cfg.n_steps, d=dt)
        peak_idx = np.argmax(np.abs(s_freq))
        # 峰值频率应接近 f_target
        assert abs(freqs[peak_idx] - f_target) < freqs[1] * 2

    def test_sparam_empty_raises(self):
        """空信号 raise（禁止 fall-back）。"""
        cfg = PICWaveConfig(dt=1e-14, n_steps=64)
        backend = PICWaveTimeDomainBackend(cfg)
        with pytest.raises(ValueError, match="为空"):
            backend.extract_sparams(np.array([]))

    def test_sparam_invalid_dt_raises(self):
        """非法 dt raise。"""
        cfg = PICWaveConfig(dt=1e-14, n_steps=64)
        backend = PICWaveTimeDomainBackend(cfg)
        with pytest.raises(ValueError, match="dt"):
            backend.extract_sparams(np.array([1.0, 2.0]), dt=-1.0)


# ---------------------------------------------------------------------------
# 8. TestEnergyConservation — 无源线性系统能量守恒
# ---------------------------------------------------------------------------
class TestEnergyConservation:
    """无源线性系统能量守恒（无损耗、无增益、无非线性）。"""

    def test_energy_conservation_lossless(self):
        """无损耗链式电路：输出能量 ≈ 输入能量。"""
        cfg = PICWaveConfig(dt=1e-14, n_steps=2048)
        backend = PICWaveTimeDomainBackend(cfg)
        n0 = backend.add_node("source", {"length": 2e-6, "alpha": 0.0})
        n1 = backend.add_node("waveguide", {"length": 2e-6, "alpha": 0.0})
        backend.connect(n0, n1, delay=1e-14, alpha=0.0, length=0.0)
        backend.mark_port(0, n0)
        backend.mark_port(1, n1)
        # 自定义高斯脉冲（无载波，便于能量计算）
        dt = cfg.dt
        t = np.arange(cfg.n_steps) * dt
        sigma = 30 * dt
        t0 = 6 * sigma
        pulse = np.exp(-((t - t0) ** 2) / (2 * sigma * sigma))
        result = backend.run(source_port=0, source_wave=pulse.astype(np.complex128))
        e_in_energy = np.sum(np.abs(pulse) ** 2)
        e_out_energy = np.sum(np.abs(result["E_ports"][1]) ** 2)
        # 无损耗下能量守恒（容差 5%，边界延迟效应）
        ratio = e_out_energy / e_in_energy
        assert 0.95 < ratio < 1.05, f"能量不守恒: ratio={ratio}"

    def test_energy_loss_with_alpha(self):
        """有损耗时输出能量 < 输入能量。"""
        cfg = PICWaveConfig(dt=1e-14, n_steps=2048)
        backend = PICWaveTimeDomainBackend(cfg)
        n0 = backend.add_node("source", {"length": 2e-6, "alpha": 0.0})
        # alpha·L = 1e6·2e-6 = 2.0，|H|=exp(-1)≈0.368，能量损失 ~86%
        n1 = backend.add_node("waveguide", {"length": 2e-6, "alpha": 1.0e6})
        backend.connect(n0, n1, delay=1e-14, alpha=0.0, length=0.0)
        backend.mark_port(0, n0)
        backend.mark_port(1, n1)
        dt = cfg.dt
        t = np.arange(cfg.n_steps) * dt
        sigma = 30 * dt
        t0 = 6 * sigma
        pulse = np.exp(-((t - t0) ** 2) / (2 * sigma * sigma))
        result = backend.run(source_port=0, source_wave=pulse.astype(np.complex128))
        e_in_energy = np.sum(np.abs(pulse) ** 2)
        e_out_energy = np.sum(np.abs(result["E_ports"][1]) ** 2)
        assert e_out_energy < e_in_energy * 0.95, "有损耗应降低能量"


# ---------------------------------------------------------------------------
# 9. Test200DevicesPerformance — 200 器件时域仿真性能
# ---------------------------------------------------------------------------
class Test200DevicesPerformance:
    """200 器件时域仿真 < 60 秒（R15 性能要求）。"""

    def test_200_devices_performance(self):
        """200 个波导节点链式仿真 < 60s。"""
        cfg = PICWaveConfig(dt=1e-14, n_steps=1024)
        backend = PICWaveTimeDomainBackend(cfg)
        # 200 个 waveguide 节点链式
        n_nodes = 200
        ids = [
            backend.add_node("waveguide", {"length": 2e-6, "alpha": 0.0})
            for _ in range(n_nodes)
        ]
        for i in range(n_nodes - 1):
            backend.connect(ids[i], ids[i + 1], delay=1e-14, length=0.0)
        backend.mark_port(0, ids[0])
        backend.mark_port(1, ids[-1])

        t_start = time.perf_counter()
        result = backend.run(source_port=0)
        elapsed = time.perf_counter() - t_start
        assert elapsed < 60.0, f"200 器件仿真耗时 {elapsed:.2f}s > 60s"
        # 仿真应正常完成，输出端口有信号传播
        assert result["t"].shape == (1024,)
        assert np.max(np.abs(result["E_ports"][1])) > 0.0


# ---------------------------------------------------------------------------
# 10. TestCFLCondition — CFL 条件违反即 raise
# ---------------------------------------------------------------------------
class TestCFLCondition:
    """CFL 条件校验（Courant 1928）。"""

    def test_cfl_violation_raises(self):
        """dt 过大违反 CFL raise（禁止 fall-back）。"""
        # dt 远大于节点传播时间 L/v_g
        cfg = PICWaveConfig(dt=1e-10, n_steps=64)
        backend = PICWaveTimeDomainBackend(cfg)
        backend.add_node("waveguide", {"length": 1e-6})  # τ=L/v_g≈1.4e-14
        backend.mark_port(0, 0)
        with pytest.raises(ValueError, match="CFL"):
            backend.run(source_port=0)

    def test_cfl_satisfied_no_raise(self):
        """dt 满足 CFL 不 raise。"""
        cfg = PICWaveConfig(dt=1e-14, n_steps=64)
        backend = PICWaveTimeDomainBackend(cfg)
        backend.add_node("waveguide", {"length": 2e-6})  # τ≈2.8e-14 > dt
        backend.mark_port(0, 0)
        result = backend.run(source_port=0)
        assert result["t"].shape == (64,)
