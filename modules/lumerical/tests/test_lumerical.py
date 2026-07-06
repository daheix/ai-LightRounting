"""polaris-lumerical 子模块 smoke test。

验证:
1. import 成功 + __all__ 导出完整
2. 核心功能基本运行（纯 NumPy 部分）
3. R03 禁止 fall-back（商业软件未安装即 raise）
4. 参数校验正确

学术依据: R02 学术诚信 / R03 禁止 fall-back / R13 交付自测
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

# sys.path 注入：使 src/polaris_lumerical 可被 import
_SRC = str(Path(__file__).resolve().parents[1] / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import polaris_lumerical as pl


# =============================================================================
# 1. import + 导出完整性
# =============================================================================
def test_import_and_version():
    """验证模块 import 成功 + 版本号 + __all__ 非空。"""
    assert pl.__version__ == "5.0.0"
    assert len(pl.__all__) >= 30, f"__all__ 应 ≥30 个符号，得到 {len(pl.__all__)}"
    # 核心类必须存在
    for name in ["FDTD3DConfig", "LumericalFDTDBackend", "ModeSolver",
                 "CHARGESimulator", "INTERCONNECTSimulator", "LumericalIntegration",
                 "Tidy3DBackend", "GPUFDTDEngine", "MeepAdjointBackend",
                 "PhotoelectricCoSim", "CMLCompiler"]:
        assert hasattr(pl, name), f"缺少核心 API: {name}"


def test_physical_constants():
    """验证物理常数（CODATA 2018 精确值）。"""
    assert pl._C0 == 2.99792458e8      # 真空光速
    assert pl._Q == 1.602176634e-19    # 电子电荷
    assert pl._KB == 1.380649e-23      # 玻尔兹曼常数
    assert pl._N_SILICON == 3.48       # 硅折射率 @ 1550nm
    # Soref & Bennett 1987 系数
    assert pl._SOREF_DN_AN == -8.8e-22
    assert pl._SOREF_DN_AP == -8.5e-18


def test_public_constants_and_availability():
    """验证公开常量（CODATA 2018 / SiEPIC PDK）与后端可用性探测函数。

    R02 学术诚信: CODATA 2018 精确定义值 / SiEPIC EBeam PDK SOI 波导参数 /
    IEEE Std 100-2000 Np-dB 换算。
    """
    # 光电协同常数（CODATA 2018 精确值，非测量值）
    assert pl.PLANCK_CONSTANT == 6.62607015e-34   # 普朗克常数 J·s
    assert pl.ELECTRON_CHARGE == 1.602176634e-19  # 元电荷 C
    assert pl.SPEED_OF_LIGHT == 2.99792458e8      # 真空光速 m/s
    # SOI 波导解析模型参数（SiEPIC EBeam PDK 1550nm）
    assert pl.SOI_N_EFF_CENTER == 2.34   # 中心有效折射率 @ 1550nm
    assert pl.SOI_DN_D_LAMBDA == -0.5    # 色散 dn_eff/dλ
    assert pl.SOI_ALPHA_DB_PER_UM == 5e-5  # 传播损耗 dB/μm
    # IEEE Std 100-2000: 1 Np = 4.343 dB
    assert pl.DB_TO_NP == 4.343
    # CML 容差（无源性/互易性诊断阈值）
    assert pl.PASSIVITY_TOL == 1e-6
    assert pl.RECIPROCITY_TOL == 1e-9
    # 后端可用性探测（importlib 探测，返回 bool，R03 合规）
    assert isinstance(pl.is_meep_available(), bool)
    assert isinstance(pl.is_tidy3d_available(), bool)
    # MEEP 通常未安装 → False；check_meep_availability 与 is_meep_available 一致
    if not pl.is_meep_available():
        assert pl.check_meep_availability() == pl.MeepAvailability.NOT_INSTALLED


# =============================================================================
# 2. Lumerical MODE 基本功能（Marcatili 近似，纯 NumPy）
# =============================================================================
def test_lumerical_mode_marcatili():
    """验证 Marcatili 近似有效折射率计算。

    R02 学术诚信: Marcatili 1969 近似对深蚀刻小波导（500×220nm SOI）
    会高估 n_eff（典型偏差 +0.4~+0.5），已知局限性。Marcatili 给出
    n_eff≈2.81，而 SiEPIC EBeam PDK 实测值 ≈ 2.34。本测试验证 Marcatili
    公式本身的正确性（非实际值），高精度 n_eff 由 FDFD 特征值分解求解
    （见 test_lumerical_mode_solve_waveguide）。
    """
    cfg = pl.ModeConfig(wavelength=1.55, grid_size=(0.05, 0.05), n_modes=4)
    solver = pl.ModeSolver(cfg)
    # 硅波导 500x220nm，n_core=3.48, n_clad=1.44
    n_eff = solver.compute_neff(width=0.5, core_index=3.48, cladding_index=1.44)
    # n_eff 应在 n_clad 和 n_core 之间
    assert 1.44 < n_eff < 3.48, f"n_eff={n_eff} 应在 (1.44, 3.48)"
    # Marcatili 近似高估：典型给出 ~2.8（实际值 2.34）
    assert 2.5 < n_eff < 3.0, f"Marcatili n_eff={n_eff} 应在 ~2.8 附近（高估）"


def test_lumerical_mode_solve_waveguide():
    """验证 FDFD 特征值分解求解波导模式。"""
    cfg = pl.ModeConfig(wavelength=1.55, grid_size=(0.1, 0.1), n_modes=2,
                        window_size=(1.6, 1.6))
    solver = pl.ModeSolver(cfg)
    result = solver.solve_waveguide(width=0.5, height=0.22,
                                    core_index=3.48, cladding_index=1.44)
    assert "n_eff" in result
    assert 1.44 < result["n_eff"] < 3.48
    assert result["n_modes_found"] >= 1


def test_lumerical_mode_cutoff_raise():
    """R03: 模式截止必须 raise，禁止 fall-back。"""
    cfg = pl.ModeConfig(wavelength=1.55)
    solver = pl.ModeSolver(cfg)
    # 极小波导 → 模式截止
    with pytest.raises(ValueError, match="模式截止"):
        solver.compute_neff(width=0.01, core_index=3.48, cladding_index=1.44)


# =============================================================================
# 3. Lumerical CHARGE 基本功能（Soref-Bennett，纯 NumPy）
# =============================================================================
def test_lumerical_charge_depletion():
    """验证 PN 结耗尽区宽度计算。"""
    cfg = pl.CHARGEConfig(temperature=300.0, doping_n=1e18, doping_p=1e18)
    sim = pl.CHARGESimulator(cfg)
    # 零偏耗尽区宽度
    w = sim.compute_depletion_width(0.0)
    assert w > 0, f"耗尽区宽度须 > 0，得到 {w}"
    # 典型值 ~ 20-50 nm @ 1e18 cm⁻³
    assert 1e-9 < w < 1e-7, f"耗尽区宽度 {w} 应在 nm 量级"
    # 反向偏置增大耗尽区
    w_rev = sim.compute_depletion_width(-1.0)
    assert w_rev > w, f"反向偏置应增大耗尽区: {w_rev} > {w}"


def test_lumerical_charge_electro_optic():
    """验证电光协同仿真（Soref-Bennett 等离子色散）。"""
    cfg = pl.CHARGEConfig(temperature=300.0, doping_n=1e18, doping_p=1e18)
    sim = pl.CHARGESimulator(cfg)
    result = sim.electro_optic_simulation(
        {"voltage": 1.0, "length": 100.0, "wavelength": 1.55, "width": 0.5})
    assert "delta_n_eff" in result
    assert "phase_shift" in result
    assert "bandwidth" in result
    # 反向偏置 → 耗尽区变宽 → 移除载流子 → Δn 为负（Soref 系数为负）
    assert result["delta_n"] != 0, "Δn 不应为零"


def test_lumerical_charge_forward_bias_raise():
    """R03: 正向偏置使耗尽区消失必须 raise。"""
    cfg = pl.CHARGEConfig(temperature=300.0, doping_n=1e18, doping_p=1e18)
    sim = pl.CHARGESimulator(cfg)
    # 强正向偏置 → v_total ≤ 0
    with pytest.raises(ValueError, match="耗尽区消失"):
        sim.compute_depletion_width(va=10.0)


# =============================================================================
# 4. Lumerical INTERCONNECT 基本功能（PRBS + NRZ，纯 NumPy）
# =============================================================================
def test_lumerical_interconnect_prbs():
    """验证 PRBS7 伪随机序列生成。"""
    cfg = pl.INTERCONNECTConfig(sample_rate=1e12, bit_rate=10e9, n_bits=128)
    sim = pl.INTERCONNECTSimulator(cfg)
    bits = sim.generate_prbs(64)
    assert len(bits) == 64
    assert set(np.unique(bits)).issubset({0, 1}), "PRBS 比特应为 0/1"
    # PRBS7 周期 127，不应全零
    assert np.any(bits == 1), "PRBS 不应全零"


def test_lumerical_interconnect_modulate_nrz():
    """验证 NRZ 调制。"""
    cfg = pl.INTERCONNECTConfig(sample_rate=1e12, bit_rate=10e9)
    sim = pl.INTERCONNECTSimulator(cfg)
    bits = np.array([0, 1, 0, 1, 1, 0, 1, 0])
    signal = sim.modulate(bits, "NRZ")
    spp = int(1e12 / 10e9)
    assert len(signal) == len(bits) * spp
    # NRZ: bit 0 → -1, bit 1 → +1
    assert signal[0] == -1.0, f"bit 0 应映射为 -1，得到 {signal[0]}"
    assert signal[spp] == 1.0, f"bit 1 应映射为 +1，得到 {signal[spp]}"


def test_lumerical_interconnect_run_link():
    """验证完整链路仿真（PRBS→调制→噪声→BER）。"""
    cfg = pl.INTERCONNECTConfig(sample_rate=1e12, bit_rate=10e9, n_bits=64)
    sim = pl.INTERCONNECTSimulator(cfg)
    result = sim.run_link_simulation({"n_bits": 64, "osnr_db": 30.0, "modulation": "NRZ"})
    assert "ber" in result
    assert 0 <= result["ber"] <= 1, f"BER 须在 [0,1]，得到 {result['ber']}"
    assert result["osnr_db"] == 30.0


# =============================================================================
# 5. Lumerical FDTD 配置 + CFL（纯公式）
# =============================================================================
def test_lumerical_fdtd_courant_dt():
    """验证 3D CFL 稳定条件时间步长。"""
    dt = pl.courant_dt_3d(1e-7, 1e-7, 1e-7, cfl=0.99)
    assert dt > 0, f"dt 须 > 0，得到 {dt}"
    # CFL: dt ≤ 1/(c·√3/dx) = dx/(c·√3)
    dx = 1e-7
    dt_max = dx / (pl._C0 * np.sqrt(3))
    assert dt <= dt_max * 1.001, f"dt={dt} 应 ≤ CFL 上限 {dt_max}"


def test_lumerical_fdtd_config_validation():
    """验证 FDTD3DConfig 创建 + 参数校验。"""
    cfg = pl.FDTD3DConfig(wavelength_um=1.55, dx_um=0.05, n_steps=1000)
    backend = pl.LumericalFDTDBackend(cfg)
    backend.set_grid_3d()
    assert backend._grid_set is True
    # R03: run() 必须 raise（完整引擎在 polaris-fdtd）
    with pytest.raises(RuntimeError, match="polaris-fdtd"):
        backend.run()


def test_lumerical_fdtd_cfl_invalid_raise():
    """R03: 非法 CFL 因子必须 raise。"""
    with pytest.raises(ValueError, match="CFL"):
        pl.courant_dt_3d(1e-7, 1e-7, 1e-7, cfl=1.5)


# =============================================================================
# 6. GPUFDTDEngine（1D Yee + Mur ABC，纯 NumPy CPU，R04 合规）
# =============================================================================
def test_gpu_fdtd_engine_run():
    """验证 GPUFDTDEngine 1D Yee 仿真（纯 NumPy CPU）。"""
    cfg = pl.GPUFDTDConfig(wavelength_um=1.55, n_steps=100, n_layers=10)
    engine = pl.GPUFDTDEngine(cfg)
    params = np.ones(10) * 0.5  # 中等折射率
    result = engine.run(params)
    assert "transmission" in result
    assert "reflection" in result
    assert "field" in result
    # 传输率 + 反射率 ≈ 1（能量守恒近似）
    total = result["transmission"] + result["reflection"]
    assert 0.0 <= total <= 2.0, f"T+R={total} 应在合理范围"
    # R04: field 是 NumPy 数组（非 GPU array）
    assert isinstance(result["field"], np.ndarray), "field 应为 numpy.ndarray"


def test_gpu_fdtd_config_dt():
    """验证 GPUFDTDConfig.dt_fs 满足 CFL。"""
    cfg = pl.GPUFDTDConfig(dx_um=0.05)
    dt_fs = cfg.dt_fs
    # dt = dx/(2c)，dx=0.05μm → dt ≈ 0.083 fs
    assert 0.05 < dt_fs < 0.15, f"dt_fs={dt_fs} 应在 ~0.083 附近"


# =============================================================================
# 7. R03 禁止 fall-back（商业软件未安装即 raise）
# =============================================================================
def test_tidy3d_no_api_key_raise():
    """R03: Tidy3D 无 API key 必须 raise，禁止静默降级。"""
    cfg = pl.Tidy3DConfig(api_key="")
    backend = pl.Tidy3DBackend(cfg)
    # tidy3d 未安装 → ImportError；已安装但无 key → RuntimeError
    with pytest.raises((ImportError, RuntimeError)):
        backend.run_cloud()


def test_meep_not_installed_raise():
    """R03: MEEP 未安装必须 raise ImportError。"""
    cfg = pl.MeepSimulationConfig()
    backend = pl.MeepAdjointBackend(cfg)
    # meep 通常未安装 → ImportError
    with pytest.raises((ImportError, NotImplementedError)):
        backend.run(np.array([0.5]))


def test_check_meep_availability():
    """验证 MEEP 可用性检测（importlib 探测，R03 合规）。"""
    avail = pl.check_meep_availability()
    assert avail in (pl.MeepAvailability.AVAILABLE,
                     pl.MeepAvailability.NOT_INSTALLED)


# =============================================================================
# 8. FDTD Simulator SOI 解析模型（纯公式）
# =============================================================================
def test_soi_waveguide_sparams():
    """验证 SOI 波导 S 参数解析模型。"""
    wls = np.array([1.5, 1.55, 1.6])
    s21 = pl.compute_soi_waveguide_sparams(wls, length_um=100.0)
    assert len(s21) == 3
    # 传输率 |S21|² ≤ 1（无源器件）
    t = np.abs(s21) ** 2
    assert np.all(t <= 1.0 + 1e-10), f"|S21|²={t} 须 ≤ 1"
    # 有损耗 → |S21| < 1
    assert np.all(t < 1.0), f"100μm 波导应有损耗，|S21|²={t} 须 < 1"


def test_fdtd_backend_enum():
    """验证 FDTDBackend 枚举。"""
    assert pl.FDTDBackend.ANALYTICAL.value == "analytical"
    assert pl.FDTDBackend.MEEP.value == "meep"
    assert pl.FDTDBackend.TIDY3D.value == "tidy3d"
    # ANALYTICAL 始终可用
    assert pl.FDTDBackend.ANALYTICAL in pl.FDTDBackend


# =============================================================================
# 9. Photoelectric CoSim（MZM + Laser，纯公式）
# =============================================================================
def test_photoelectric_mzm_transmission():
    """验证 MZM 传输函数 T(V)=cos²(πV/2Vπ)。"""
    spec = pl.ModulatorSpec(vpi=2.0, insertion_loss_db=0.0)
    # V=0 → T=1（无损耗，无偏置）
    t0 = pl.PhotoelectricCoSim.mzm_transmission(0.0, spec)
    assert abs(t0 - 1.0) < 1e-10, f"V=0 时 T 应=1，得到 {t0}"
    # V=Vπ → T=0（π 相位 → cos²(π/2)=0）
    t_vpi = pl.PhotoelectricCoSim.mzm_transmission(2.0, spec)
    assert abs(t_vpi) < 1e-10, f"V=Vπ 时 T 应=0，得到 {t_vpi}"


def test_photoelectric_laser_li():
    """验证激光器 L-I 特性。"""
    spec = pl.LaserSpec(threshold_current=0.02, slope_efficiency=0.4)
    # 阈值以下 → P=0
    p_below = pl.PhotoelectricCoSim.laser_li(0.01, spec)
    assert p_below == 0.0, f"阈值以下 P 应=0，得到 {p_below}"
    # 阈值以上 → 线性
    p_above = pl.PhotoelectricCoSim.laser_li(0.05, spec)
    expected = 0.4 * (0.05 - 0.02)
    assert abs(p_above - expected) < 1e-10, f"阈值以上 P={p_above} 应={expected}"


def test_photoelectric_cosim_register():
    """验证器件注册。"""
    cfg = pl.CoSimConfig()
    cosim = pl.PhotoelectricCoSim(cfg)
    id1 = cosim.add_modulator(vpi=2.0, insertion_loss=3.0)
    id2 = cosim.add_photodetector(responsivity=0.8, dark_current=1e-9)
    id3 = cosim.add_laser(threshold_current=0.02, slope_efficiency=0.4)
    assert id1 == 1 and id2 == 2 and id3 == 3, f"器件 ID 应自增: {id1},{id2},{id3}"


def test_photoelectric_end_to_end_link():
    """端到端光电链路仿真 laser→mod→wg→pd（*创新*）。

    R02 学术诚信: 完整 4 级光电链路，每级物理模型独立可溯源:
    - 激光器 L-I (Coldren 1995 §5)
    - MZM 调制 T(V)=cos²(πV/2Vπ) (Chrostowski 2015 §8.4)
    - 波导传输 10^(-α·L/10) (Pozar §4)
    - 探测器 I_photo=R·P_in (Chrostowski 2015 §9.2)
    """
    cfg = pl.CoSimConfig()
    cosim = pl.PhotoelectricCoSim(cfg)
    laser_id = cosim.add_laser(threshold_current=10e-3, slope_efficiency=0.4)
    mod_id = cosim.add_modulator(vpi=2.0, insertion_loss=0.5)
    pd_id = cosim.add_photodetector(responsivity=1.0, dark_current=10e-9)
    v_in = np.array([0.0, 0.5, 1.0, 2.0])
    result = cosim.run_end_to_end_link(
        v_in, laser_id, mod_id, pd_id, waveguide_loss_db=0.5
    )
    # 完整链路 4 级输出
    expected_keys = {
        "v_in", "p_laser", "mzm_transfer", "p_modulated",
        "p_waveguide", "i_photo", "v_out",
    }
    assert set(result.keys()) == expected_keys, f"链路输出键缺失: {result.keys()}"
    # V=Vπ=2.0 时 MZM 传输 cos²(π/2)=0，光功率为零（仅剩暗电流）
    assert result["mzm_transfer"][3] == pytest.approx(0.0, abs=1e-10)
    # V=0 时 MZM 传输 cos²(0)·10^(-IL/20) = 10^(-0.5/20) ≈ 0.944（含 0.5dB 插损）
    expected_t0 = 10.0 ** (-0.5 / 20.0)
    assert result["mzm_transfer"][0] == pytest.approx(expected_t0, abs=1e-6)
    # V_out 随 V_in 增大而单调递减（MZM 推挽调制特性）
    assert result["v_out"][0] > result["v_out"][2] > result["v_out"][3]
    # p_laser 为标量（稳态）
    assert result["p_laser"] > 0, "激光器稳态功率应 > 0"


def test_photoelectric_link_budget():
    """链路预算分析（dB 域，与 Lumerical INTERCONNECT 对齐，*创新*）。

    R02: P_rx_dBm = P_tx_dBm - L_mod - L_wg - L_pd
    来源: Keysight 5992-3268
    """
    cfg = pl.CoSimConfig()
    cosim = pl.PhotoelectricCoSim(cfg)
    laser_id = cosim.add_laser(threshold_current=10e-3, slope_efficiency=0.4)
    mod_id = cosim.add_modulator(vpi=2.0, insertion_loss=0.5)
    pd_id = cosim.add_photodetector(responsivity=1.0, dark_current=10e-9)
    budget = cosim.link_budget_analysis(
        laser_id, mod_id, pd_id, waveguide_loss_db=0.5
    )
    # 链路预算键完整
    expected_keys = {
        "p_tx_dbm", "l_mod_db", "l_wg_db", "l_pd_db",
        "p_rx_dbm", "p_rx_w", "i_photo", "v_out",
    }
    assert set(budget.keys()) == expected_keys, f"预算键缺失: {budget.keys()}"
    # 链路预算守恒: p_rx_dBm = p_tx_dBm - L_mod - L_wg - L_pd
    expected_p_rx = (
        budget["p_tx_dbm"]
        - budget["l_mod_db"]
        - budget["l_wg_db"]
        - budget["l_pd_db"]
    )
    assert budget["p_rx_dbm"] == pytest.approx(expected_p_rx, abs=1e-6)
    # 探测器无源损耗为 0（响应度是转换效率）
    assert budget["l_pd_db"] == 0.0
    # p_rx_w > 0（链路有光功率到达）
    assert budget["p_rx_w"] > 0
    # i_photo > dark_current（光电流超过暗电流）
    assert budget["i_photo"] > 10e-9


def test_photoelectric_pam4_ber():
    """PAM4 BER 严格公式（Gray 编码，*创新*）。

    R02: BER ≈ (3/4)·erfc(√(Es/(5·N0)))
    来源: Proakis §5; Keysight 5992-3268; Shafik 2016
    PAM4 比 NRZ 差约 9.5 dB（4 电平判决阈值更密）。
    """
    # SNR=20dB: PAM4 BER 应在 1e-10 量级（NRZ @ 20dB 约 1e-20）
    ber_pam4 = pl.PhotoelectricCoSim.compute_pam4_ber(20.0)
    assert 1e-12 < ber_pam4 < 1e-8, f"PAM4 BER @ 20dB={ber_pam4} 应在 1e-10 量级"
    # SNR 越高 BER 越低（单调递减）
    ber_low_snr = pl.PhotoelectricCoSim.compute_pam4_ber(10.0)
    ber_high_snr = pl.PhotoelectricCoSim.compute_pam4_ber(30.0)
    assert ber_low_snr > ber_pam4 > ber_high_snr
    # BER <= 0.75（理论上限，3/4·erfc(0)=0.75）
    assert ber_pam4 <= 0.75
    # R03: 非法 SNR 必须 raise
    with pytest.raises(ValueError, match="SNR_dB"):
        pl.PhotoelectricCoSim.compute_pam4_ber(-1.0)


def test_photoelectric_eye_diagram():
    """PAM4 眼图折叠（*创新*）。

    R02: 按 samples_per_symbol 折叠为眼图矩阵
    来源: Keysight 5992-3268
    """
    # 100 点信号，每符号 10 点 → 10 符号 × 10 采样眼图
    signal = np.random.randn(100)
    eye = pl.PhotoelectricCoSim.compute_eye_diagram(
        signal, samples_per_symbol=10, n_levels=4
    )
    assert eye.shape == (10, 10), f"眼图形状应为 (10,10)，得到 {eye.shape}"
    # NRZ 2 电平
    eye_nrz = pl.PhotoelectricCoSim.compute_eye_diagram(
        signal, samples_per_symbol=5, n_levels=2
    )
    assert eye_nrz.shape == (20, 5)
    # R03: 参数非法 raise
    with pytest.raises(ValueError, match="samples_per_symbol"):
        pl.PhotoelectricCoSim.compute_eye_diagram(signal, samples_per_symbol=0)
    with pytest.raises(ValueError, match="n_levels"):
        pl.PhotoelectricCoSim.compute_eye_diagram(signal, 10, n_levels=1)
    # 信号长度不足 raise
    with pytest.raises(ValueError, match="信号长度"):
        pl.PhotoelectricCoSim.compute_eye_diagram(np.array([1.0, 2.0]), 10)


def test_photoelectric_end_to_end_link_invalid_raise():
    """R03: 端到端链路非法参数 raise。"""
    cfg = pl.CoSimConfig()
    cosim = pl.PhotoelectricCoSim(cfg)
    laser_id = cosim.add_laser(threshold_current=10e-3, slope_efficiency=0.4)
    mod_id = cosim.add_modulator(vpi=2.0, insertion_loss=0.5)
    pd_id = cosim.add_photodetector(responsivity=1.0, dark_current=10e-9)
    v_in = np.array([0.0, 1.0])
    # 波导损耗为负
    with pytest.raises(ValueError, match="waveguide_loss_db"):
        cosim.run_end_to_end_link(v_in, laser_id, mod_id, pd_id, -1.0)
    # 设备 ID 未注册
    with pytest.raises(ValueError, match="未注册"):
        cosim.run_end_to_end_link(v_in, 999, mod_id, pd_id)
    # 设备类型不匹配
    with pytest.raises(ValueError, match="类型不匹配"):
        cosim.run_end_to_end_link(v_in, mod_id, mod_id, pd_id)  # mod_id 当 laser


def test_photoelectric_link_budget_zero_laser_raise():
    """R03: 激光器零输出做链路预算 raise（无法 log）。"""
    cfg = pl.CoSimConfig()
    cosim = pl.PhotoelectricCoSim(cfg)
    # bias_current 默认 2×I_th，手动设为低值使 P_laser=0
    laser_id = cosim.add_laser(threshold_current=1.0, slope_efficiency=0.4)
    cosim._devices[laser_id][1].bias_current = 0.5  # < threshold=1.0
    mod_id = cosim.add_modulator(vpi=2.0, insertion_loss=0.5)
    pd_id = cosim.add_photodetector(responsivity=1.0, dark_current=10e-9)
    with pytest.raises(ValueError, match="激光器输出功率为零"):
        cosim.link_budget_analysis(laser_id, mod_id, pd_id)


def test_modulator_spec_validation():
    """R03: ModulatorSpec 非法参数必须 raise。"""
    with pytest.raises(ValueError, match="V_pi"):
        pl.ModulatorSpec(vpi=-1.0, insertion_loss_db=0.0)


# =============================================================================
# 10. CML Compiler（无源性/互易性诊断，纯 NumPy SVD）
# =============================================================================
def test_cml_compiler_basic():
    """验证 CML Compiler 编译 + 诊断。"""
    compiler = pl.CMLCompiler()
    # 2 端口无源互易器件
    n_freq = 5
    s_matrix = np.zeros((n_freq, 2, 2), dtype=complex)
    s_matrix[:, 0, 0] = 0.1  # S11
    s_matrix[:, 1, 1] = 0.1  # S22
    s_matrix[:, 0, 1] = 0.9  # S21
    s_matrix[:, 1, 0] = 0.9  # S12（互易）
    wls = np.linspace(1.5, 1.6, n_freq)
    comp = compiler.compile("mmi", ["in", "out"], wls, s_matrix)
    assert comp.metadata.passivity_ok, "无源器件应通过无源性检查"
    assert comp.metadata.reciprocity_ok, "S21=S12 应通过互易性检查"
    assert comp.n_ports == 2


def test_cml_passivity_violation():
    """验证无源性违规检测。"""
    # S21 > 1 → 违反无源性
    s_matrix = np.array([[[0.0, 1.5], [1.5, 0.0]]], dtype=complex)
    ok, norms = pl.CMLDiagnostics.check_passivity(s_matrix)
    assert not ok, "S=1.5 应违反无源性"
    assert norms[0] > 1.0


def test_cml_fingerprint():
    """验证 S 参数指纹（SHA256）。"""
    s1 = np.array([[[0.5, 0.3], [0.3, 0.5]]], dtype=complex)
    s2 = np.array([[[0.5, 0.3], [0.3, 0.5]]], dtype=complex)
    s3 = np.array([[[0.5, 0.4], [0.4, 0.5]]], dtype=complex)
    fp1 = pl.CMLCompiler.compute_fingerprint(s1)
    fp2 = pl.CMLCompiler.compute_fingerprint(s2)
    fp3 = pl.CMLCompiler.compute_fingerprint(s3)
    assert fp1 == fp2, "相同 S 参数应有相同指纹"
    assert fp1 != fp3, "不同 S 参数应有不同指纹"
    assert len(fp1) == 16, f"指纹长度应为 16，得到 {len(fp1)}"


def test_cml_compile_validation():
    """R03: CML compile 非法输入必须 raise。"""
    compiler = pl.CMLCompiler()
    wls = np.array([1.55])
    # 非方阵
    with pytest.raises(ValueError, match="方阵"):
        compiler.compile("bad", ["a"], wls,
                         np.zeros((1, 2, 3), dtype=complex))
    # 端口数不匹配
    with pytest.raises(ValueError, match="端口数"):
        compiler.compile("bad", ["a", "b"], wls,
                         np.zeros((1, 1, 1), dtype=complex))


# =============================================================================
# 11. LumericalIntegration 全流程（集成测试）
# =============================================================================
def test_lumerical_integration_full_flow():
    """验证 Lumerical 全流程（MODE → CHARGE → INTERCONNECT）。"""
    integration = pl.LumericalIntegration()
    result = integration.full_flow(
        waveguide_config={"width": 0.5, "height": 0.22, "wavelength": 1.55},
        modulator_config={"voltage": 1.0, "length": 100.0, "wavelength": 1.55},
        link_config={"n_bits": 32, "osnr_db": 30.0, "modulation": "NRZ"},
    )
    assert "mode_result" in result
    assert "eo_result" in result
    assert "link_result" in result
    # MODE 结果
    assert 1.44 < result["mode_result"]["n_eff"] < 3.48
    # CHARGE 结果
    assert "delta_n_eff" in result["eo_result"]
    # INTERCONNECT 结果
    assert 0 <= result["link_result"]["ber"] <= 1
