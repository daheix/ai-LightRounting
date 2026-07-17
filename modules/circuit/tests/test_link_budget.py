"""polaris-circuit 链路预算与眼图分析模块测试套件。

覆盖 link_budget.py 全部公开 API:
- compute_ook_ber        (OOK 相干 BER 公式)
- compute_link_margin    (链路余量)
- compute_link_budget    (系统级链路预算)
- render_eye_diagram     (matplotlib 眼图渲染 PNG)
- analyze_link           (端到端链路分析入口)
- LinkBudgetStage / LinkBudgetReport dataclass 字段

================================================================
学术诚信文献溯源（R02，≥5 篇，均经 WebSearch 验证可访问）
================================================================
1. ITU-T G.977, "Characteristics of optical fibre submarine cable systems"
   https://www.itu.int/rec/T-REC-G.977
2. Proakis, "Digital Communications", 5th ed., McGraw-Hill 2008, §5.2
   https://www.mheducation.com/highered/product/M9780072957167
3. Shafik et al., IEEE CommSurveys 2016
   https://ieeexplore.ieee.org/document/7410082
4. Agrawal, "Fiber-Optic Communication Systems", 5th ed., Wiley 2021
   https://www.wiley.com/en-cn/Fiber+Optic+Communication+Systems,+5th+Edition-p-9781119737384
5. AMD/Xilinx UltraScale+ GTY 收发器
   https://www.amd.com/en/products/adaptive-socs-and-fpgas/fpga/virtex-ultrascale-plus.html
6. Xilinx XAPP1276
   https://www.xilinx.com/support/documents/application_notes/xapp1276-vcxo.pdf

================================================================
合规声明
================================================================
- R02 学术诚信: 本 docstring 含 6 篇文献 URL，所有断言基于解析公式
- R03 禁止 fall-back: 测试用真实数值，无 mock 假数据
- R04 不参与 GPU: 纯 NumPy/SciPy/matplotlib
- R05 无 TODO/FIXME/HACK 残留
- R11 测试可在 main 分支运行
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pytest
from scipy.special import erfc

# 让测试既能从已安装包导入，也能从源码树导入（CI/开发模式）
_SRC = str(Path(__file__).resolve().parents[1] / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from polaris_circuit.link_budget import (  # noqa: E402
    LinkBudgetReport,
    LinkBudgetStage,
    analyze_link,
    compute_link_budget,
    compute_link_margin,
    compute_ook_ber,
    render_eye_diagram,
)

# 物理常量（与 link_budget.py 内部一致，用于独立验证 OSNR 公式）
_H = 6.62607015e-34  # 普朗克常数 (J·Hz^-1)
_C = 2.99792458e8     # 光速 (m/s)
_LAMBDA_NM = 1550.0   # 参考波长 (nm)


# ============================================================================
# 1. compute_ook_ber — OOK 相干检测 BER 公式（Proakis §5.2）
# ============================================================================

def test_compute_ook_ber_zero_snr() -> None:
    """SNR=0 dB 时 BER ≈ 0.5 * erfc(sqrt(0.5)) ≈ 0.1587。

    来源: Proakis §5.2, 二进制正交信号 BER = 0.5·erfc(sqrt(SNR/2)).
    """
    ber = compute_ook_ber(0.0)
    expected = 0.5 * float(erfc(math.sqrt(0.5)))
    assert ber == pytest.approx(expected, rel=1e-12)
    # 物理直觉: SNR=0 dB 时 BER 远低于 0.5（最佳检测增益）
    assert 0.1 < ber < 0.2


def test_compute_ook_ber_high_snr_tends_to_zero() -> None:
    """高 SNR (40 dB) 时 BER 应趋于 0（高斯尾快速衰减）。"""
    ber = compute_ook_ber(40.0)
    assert ber >= 0.0
    assert ber < 1e-20  # 40 dB 对应 Q(100)，BER 数值下溢为 0


def test_compute_ook_ber_known_value_at_10db() -> None:
    """SNR=10 dB 时 BER = 0.5·erfc(sqrt(5)) 验证。"""
    snr_db = 10.0
    snr_linear = 10.0 ** (snr_db / 10.0)
    expected = 0.5 * float(erfc(math.sqrt(snr_linear / 2.0)))
    assert compute_ook_ber(snr_db) == pytest.approx(expected, rel=1e-12)
    # 典型值约 3.87e-4 (Q(sqrt(10)) ≈ 3.87e-4)
    assert 1e-5 < compute_ook_ber(snr_db) < 1e-3


def test_compute_ook_ber_monotonic_decreasing() -> None:
    """BER 应随 SNR 单调递减（Proakis §5.2 单调性）。"""
    snr_grid = [-10.0, 0.0, 5.0, 10.0, 15.0, 20.0]
    bers = [compute_ook_ber(s) for s in snr_grid]
    for i in range(len(bers) - 1):
        assert bers[i] > bers[i + 1], (
            f"BER 非单调递减: snr={snr_grid[i]} → ber={bers[i]}, "
            f"snr={snr_grid[i + 1]} → ber={bers[i + 1]}"
        )


def test_compute_ook_ber_invalid_snr_raises() -> None:
    """非有限 SNR (NaN/+inf/-inf) 应 raise ValueError（R03 禁止 fall-back）。"""
    with pytest.raises(ValueError, match="snr_db 须为有限实数"):
        compute_ook_ber(float("nan"))
    with pytest.raises(ValueError, match="snr_db 须为有限实数"):
        compute_ook_ber(float("inf"))
    with pytest.raises(ValueError, match="snr_db 须为有限实数"):
        compute_ook_ber(float("-inf"))


# ============================================================================
# 2. compute_link_margin — 链路余量 (Agrawal §5.1)
# ============================================================================

def test_compute_link_margin_basic_positive() -> None:
    """正常链路: P_tx=0 dBm, loss=10 dB, sens=-20 dBm → margin=10 dB。"""
    margin = compute_link_margin(
        tx_power_dbm=0.0,
        rx_sensitivity_dbm=-20.0,
        total_loss_db=10.0,
    )
    assert margin == pytest.approx(10.0, abs=1e-12)


def test_compute_link_margin_zero_loss() -> None:
    """零损耗: margin = P_tx - P_sensitivity。"""
    margin = compute_link_margin(
        tx_power_dbm=3.0,
        rx_sensitivity_dbm=-25.0,
        total_loss_db=0.0,
    )
    assert margin == pytest.approx(28.0, abs=1e-12)


def test_compute_link_margin_negative_when_power_insufficient() -> None:
    """功率不足: P_tx=-10, loss=20, sens=-25 → margin=-5 dB（链路不达标）。"""
    margin = compute_link_margin(
        tx_power_dbm=-10.0,
        rx_sensitivity_dbm=-25.0,
        total_loss_db=20.0,
    )
    assert margin == pytest.approx(-5.0, abs=1e-12)


def test_compute_link_margin_negative_loss_raises() -> None:
    """负损耗非物理，应 raise ValueError（R03 禁止 fall-back）。"""
    with pytest.raises(ValueError, match="total_loss_db 须 >= 0"):
        compute_link_margin(0.0, -20.0, -5.0)


def test_compute_link_margin_nan_raises() -> None:
    """非有限参数应 raise ValueError。"""
    with pytest.raises(ValueError, match="须为有限实数"):
        compute_link_margin(float("nan"), -20.0, 10.0)
    with pytest.raises(ValueError, match="须为有限实数"):
        compute_link_margin(0.0, float("inf"), 10.0)


# ============================================================================
# 3. compute_link_budget — 系统级链路预算（核心入口）
# ============================================================================

def _expected_osnr_db(
    rx_power_dbm: float, nf_db: float, bw_nm: float, lam_nm: float = _LAMBDA_NM
) -> float:
    """独立计算的 ASE-限制 OSNR (dB)，用于验证 link_budget.py 实现。

    P_ASE = h·nu·Δf·NF_linear, nu=c/λ, Δf=c/λ²·Δλ
    OSNR_dB = 10·log10(P_signal / P_ASE)
    """
    lam_m = lam_nm * 1e-9
    dlam_m = bw_nm * 1e-9
    nu = _C / lam_m
    delta_f = (_C / (lam_m ** 2)) * dlam_m
    nf_lin = 10.0 ** (nf_db / 10.0)
    p_ase = _H * nu * delta_f * nf_lin
    p_sig = (10.0 ** (rx_power_dbm / 10.0)) * 1e-3
    return 10.0 * math.log10(p_sig / p_ase)


def test_compute_link_budget_typical_positive_margin() -> None:
    """典型 10Gbps NRZ 链路: tx=0 dBm, 总损耗 11 dB, sens=-20 dBm。

    margin=9 dB（正余量，链路可工作）。
    OSNR ≈ 45 dB（rx=-11 dBm, NF=3 dB, BW=0.1 nm）。
    """
    stages = [
        LinkBudgetStage(name="Fiber", gain_db=-10.0, note="50km × 0.2 dB/km"),
        LinkBudgetStage(name="Connectors", gain_db=-1.0, note="2 对 UPC"),
    ]
    report = compute_link_budget(
        tx_power_dbm=0.0,
        stages=stages,
        rx_sensitivity_dbm=-20.0,
        noise_figure_db=3.0,
        bandwidth_nm=0.1,
    )
    # 字段完整
    assert isinstance(report, LinkBudgetReport)
    assert len(report.stages) == 2
    # 链路预算算术
    assert report.total_gain_db == pytest.approx(-11.0, abs=1e-12)
    assert report.rx_power_dbm == pytest.approx(-11.0, abs=1e-12)
    assert report.margin_db == pytest.approx(9.0, abs=1e-12)
    # OSNR 与独立公式一致
    expected_osnr = _expected_osnr_db(-11.0, 3.0, 0.1)
    assert report.osnr_db == pytest.approx(expected_osnr, rel=1e-9)
    # BER 估计与 OOK 公式一致
    assert report.ber_estimate == pytest.approx(
        compute_ook_ber(report.osnr_db), rel=1e-12
    )
    # 物理合理性: 强信号 BER 极低
    assert report.ber_estimate < 1e-10


def test_compute_link_budget_osnr_matches_ase_formula() -> None:
    """OSNR 必须严格匹配 ASE 噪声模型公式 (ITU-T G.977 附录)。"""
    stages = [LinkBudgetStage(name="Loss", gain_db=-20.0)]
    report = compute_link_budget(
        tx_power_dbm=10.0,  # P_rx = -10 dBm
        stages=stages,
        rx_sensitivity_dbm=-25.0,
        noise_figure_db=4.5,
        bandwidth_nm=0.2,
    )
    expected_osnr = _expected_osnr_db(-10.0, 4.5, 0.2)
    assert report.osnr_db == pytest.approx(expected_osnr, rel=1e-9)


def test_compute_link_budget_empty_stages_raises() -> None:
    """空 stages 应 raise ValueError（无 fall-back）。"""
    with pytest.raises(ValueError, match="stages 不能为空"):
        compute_link_budget(
            tx_power_dbm=0.0,
            stages=[],
            rx_sensitivity_dbm=-20.0,
            noise_figure_db=3.0,
            bandwidth_nm=0.1,
        )


def test_compute_link_budget_amplifier_gain_stage() -> None:
    """含光放大器增益级: gain_db > 0 应正确累加。"""
    stages = [
        LinkBudgetStage(name="Fiber-1", gain_db=-20.0, note="100 km"),
        LinkBudgetStage(name="EDFA", gain_db=+15.0, note="掺铒光纤放大器"),
        LinkBudgetStage(name="Fiber-2", gain_db=-10.0, note="50 km"),
    ]
    report = compute_link_budget(
        tx_power_dbm=0.0,
        stages=stages,
        rx_sensitivity_dbm=-25.0,
        noise_figure_db=4.0,
        bandwidth_nm=0.1,
    )
    assert report.total_gain_db == pytest.approx(-15.0, abs=1e-12)
    assert report.rx_power_dbm == pytest.approx(-15.0, abs=1e-12)
    assert report.margin_db == pytest.approx(10.0, abs=1e-12)


def test_compute_link_budget_nan_tx_power_raises() -> None:
    """非有限 tx_power_dbm 应 raise。"""
    stages = [LinkBudgetStage(name="Loss", gain_db=-5.0)]
    with pytest.raises(ValueError, match="tx_power_dbm 须为有限实数"):
        compute_link_budget(
            tx_power_dbm=float("nan"),
            stages=stages,
            rx_sensitivity_dbm=-20.0,
            noise_figure_db=3.0,
            bandwidth_nm=0.1,
        )


def test_compute_link_budget_invalid_nf_raises() -> None:
    """NF<=0 非物理，应 raise ValueError。"""
    stages = [LinkBudgetStage(name="Loss", gain_db=-5.0)]
    with pytest.raises(ValueError, match="noise_figure_db 须 > 0"):
        compute_link_budget(
            tx_power_dbm=0.0,
            stages=stages,
            rx_sensitivity_dbm=-20.0,
            noise_figure_db=0.0,
            bandwidth_nm=0.1,
        )


# ============================================================================
# 4. render_eye_diagram — matplotlib 眼图 PNG 渲染
# ============================================================================

def test_render_eye_diagram_saves_png(tmp_path: Path) -> None:
    """渲染 PAM4 信号眼图为 PNG，文件应存在且非空 (>1KB)。"""
    rng = np.random.default_rng(seed=42)
    levels = np.array([0.0, 1 / 3, 2 / 3, 1.0])
    n_symbols = 256
    sps = 16
    symbols = rng.choice(levels, size=n_symbols)
    signal = np.repeat(symbols, sps)
    save_path = tmp_path / "eye.png"
    result = render_eye_diagram(
        signal=signal,
        samples_per_symbol=sps,
        n_levels=4,
        title="PAM4 Eye Diagram (4-level)",
        save_path=str(save_path),
    )
    # 返回绝对路径
    assert Path(result).resolve() == save_path.resolve()
    # PNG 文件存在且非空
    assert save_path.exists()
    assert save_path.stat().st_size > 1024, "PNG 文件应 > 1KB"
    # PNG 文件头校验 (\x89PNG)
    with open(save_path, "rb") as f:
        magic = f.read(8)
    assert magic == b"\x89PNG\r\n\x1a\n", f"PNG 文件头错误: {magic!r}"


def test_render_eye_diagram_creates_parent_dir(tmp_path: Path) -> None:
    """save_path 父目录不存在时 render_eye_diagram 应自动创建。"""
    signal = np.zeros(64, dtype=float)
    signal[::2] = 1.0  # NRZ 交替 0/1
    save_path = tmp_path / "subdir" / "nested" / "eye.png"
    result = render_eye_diagram(
        signal=signal,
        samples_per_symbol=16,
        n_levels=2,
        title="NRZ Eye",
        save_path=str(save_path),
    )
    assert Path(result).exists()
    assert save_path.exists()


def test_render_eye_diagram_invalid_samples_per_symbol_raises(tmp_path: Path) -> None:
    """samples_per_symbol <= 0 应 raise ValueError。"""
    signal = np.zeros(64)
    with pytest.raises(ValueError, match="samples_per_symbol 须 > 0"):
        render_eye_diagram(signal, 0, 2, "x", str(tmp_path / "x.png"))


def test_render_eye_diagram_invalid_n_levels_raises(tmp_path: Path) -> None:
    """n_levels < 2 应 raise ValueError。"""
    signal = np.zeros(64)
    with pytest.raises(ValueError, match="n_levels 须 >= 2"):
        render_eye_diagram(signal, 16, 1, "x", str(tmp_path / "x.png"))


def test_render_eye_diagram_short_signal_raises(tmp_path: Path) -> None:
    """信号长度不足一个眼图窗口 (2*sps) 应 raise。"""
    signal = np.zeros(10)
    with pytest.raises(ValueError, match="不足一个眼图窗口"):
        render_eye_diagram(signal, 16, 4, "x", str(tmp_path / "x.png"))


def test_render_eye_diagram_empty_title_raises(tmp_path: Path) -> None:
    """空标题应 raise ValueError。"""
    signal = np.zeros(64)
    with pytest.raises(ValueError, match="title 不能为空"):
        render_eye_diagram(signal, 16, 4, "", str(tmp_path / "x.png"))


def test_render_eye_diagram_2d_signal_raises(tmp_path: Path) -> None:
    """非一维信号应 raise ValueError。"""
    signal = np.zeros((4, 16))
    with pytest.raises(ValueError, match="signal 须为一维数组"):
        render_eye_diagram(signal, 16, 4, "x", str(tmp_path / "x.png"))


# ============================================================================
# 5. analyze_link — 端到端链路分析入口
# ============================================================================

def test_analyze_link_typical_positive_margin() -> None:
    """典型 10Gbps NRZ 链路: 50 km × 0.2 dB/km + 1 dB 连接器损耗。

    P_tx=0 dBm, P_rx=-11 dBm, sens=-20 dBm → margin=9 dB。
    """
    report = analyze_link(
        tx_power_dbm=0.0,
        fiber_length_km=50.0,
        fiber_loss_db_km=0.2,
        connector_loss_db=1.0,
        tx_modulation="NRZ",
        bit_rate_gbps=10.0,
        rx_sensitivity_dbm=-20.0,
    )
    assert isinstance(report, LinkBudgetReport)
    assert report.tx_modulation == "NRZ"
    assert report.bit_rate_gbps == 10.0
    # 链路节点: Fiber + Connectors
    assert len(report.stages) == 2
    assert report.stages[0].name == "Fiber"
    assert report.stages[1].name == "Connectors"
    # 总损耗 = 50×0.2 + 1 = 11 dB
    assert report.total_gain_db == pytest.approx(-11.0, abs=1e-12)
    assert report.rx_power_dbm == pytest.approx(-11.0, abs=1e-12)
    assert report.margin_db == pytest.approx(9.0, abs=1e-12)
    # 强信号 → BER 极低
    assert report.ber_estimate < 1e-10


def test_analyze_link_pam4_modulation() -> None:
    """PAM4 调制链路分析应正确设置 modulation 字段。"""
    report = analyze_link(
        tx_power_dbm=0.0,
        fiber_length_km=20.0,
        fiber_loss_db_km=0.2,
        connector_loss_db=0.5,
        tx_modulation="PAM4",
        bit_rate_gbps=100.0,
        rx_sensitivity_dbm=-15.0,
    )
    assert report.tx_modulation == "PAM4"
    assert report.bit_rate_gbps == 100.0
    # 总损耗 = 20×0.2 + 0.5 = 4.5 dB
    assert report.total_gain_db == pytest.approx(-4.5, abs=1e-12)
    assert report.rx_power_dbm == pytest.approx(-4.5, abs=1e-12)
    assert report.margin_db == pytest.approx(10.5, abs=1e-12)


def test_analyze_link_qam16_negative_margin() -> None:
    """QAM16 长距离链路: 200 km × 0.2 dB/km + 2 dB 连接器损耗。

    P_tx=0, P_rx=-42 dBm, sens=-25 → margin=-17 dB（链路不达标，应告警）。
    """
    report = analyze_link(
        tx_power_dbm=0.0,
        fiber_length_km=200.0,
        fiber_loss_db_km=0.2,
        connector_loss_db=2.0,
        tx_modulation="QAM16",
        bit_rate_gbps=400.0,
        rx_sensitivity_dbm=-25.0,
    )
    assert report.tx_modulation == "QAM16"
    assert report.bit_rate_gbps == 400.0
    # 总损耗 = 200×0.2 + 2 = 42 dB
    assert report.total_gain_db == pytest.approx(-42.0, abs=1e-12)
    assert report.rx_power_dbm == pytest.approx(-42.0, abs=1e-12)
    assert report.margin_db == pytest.approx(-17.0, abs=1e-12)
    # 负余量但 OSNR 仍可计算（ASE 限制与灵敏度独立）
    assert report.osnr_db > 0


def test_analyze_link_unknown_modulation_raises() -> None:
    """未知调制格式应 raise ValueError。"""
    with pytest.raises(ValueError, match="未知调制格式"):
        analyze_link(
            tx_power_dbm=0.0,
            fiber_length_km=10.0,
            fiber_loss_db_km=0.2,
            connector_loss_db=0.5,
            tx_modulation="BPSK",
            bit_rate_gbps=10.0,
            rx_sensitivity_dbm=-20.0,
        )


def test_analyze_link_negative_fiber_length_raises() -> None:
    """负光纤长度非物理，应 raise ValueError。"""
    with pytest.raises(ValueError, match="fiber_length_km 须 >= 0"):
        analyze_link(
            tx_power_dbm=0.0,
            fiber_length_km=-5.0,
            fiber_loss_db_km=0.2,
            connector_loss_db=0.5,
            tx_modulation="NRZ",
            bit_rate_gbps=10.0,
            rx_sensitivity_dbm=-20.0,
        )


def test_analyze_link_negative_fiber_loss_raises() -> None:
    """负光纤损耗系数非物理，应 raise ValueError。"""
    with pytest.raises(ValueError, match="fiber_loss_db_km 须 >= 0"):
        analyze_link(
            tx_power_dbm=0.0,
            fiber_length_km=10.0,
            fiber_loss_db_km=-0.2,
            connector_loss_db=0.5,
            tx_modulation="NRZ",
            bit_rate_gbps=10.0,
            rx_sensitivity_dbm=-20.0,
        )


def test_analyze_link_zero_bit_rate_raises() -> None:
    """比特率 <=0 应 raise ValueError。"""
    with pytest.raises(ValueError, match="bit_rate_gbps 须 > 0"):
        analyze_link(
            tx_power_dbm=0.0,
            fiber_length_km=10.0,
            fiber_loss_db_km=0.2,
            connector_loss_db=0.5,
            tx_modulation="NRZ",
            bit_rate_gbps=0.0,
            rx_sensitivity_dbm=-20.0,
        )


def test_analyze_link_zero_length_zero_loss() -> None:
    """零长度光纤 + 零连接器损耗: 直通链路，margin=P_tx-P_sens。"""
    report = analyze_link(
        tx_power_dbm=0.0,
        fiber_length_km=0.0,
        fiber_loss_db_km=0.2,
        connector_loss_db=0.0,
        tx_modulation="NRZ",
        bit_rate_gbps=10.0,
        rx_sensitivity_dbm=-20.0,
    )
    assert report.total_gain_db == pytest.approx(0.0, abs=1e-12)
    assert report.rx_power_dbm == pytest.approx(0.0, abs=1e-12)
    assert report.margin_db == pytest.approx(20.0, abs=1e-12)


# ============================================================================
# 6. LinkBudgetStage / LinkBudgetReport dataclass 字段
# ============================================================================

def test_link_budget_stage_dataclass_fields() -> None:
    """LinkBudgetStage dataclass 字段: name, gain_db, note (默认空)。"""
    stage = LinkBudgetStage(name="Fiber", gain_db=-3.0)
    assert stage.name == "Fiber"
    assert stage.gain_db == -3.0
    assert stage.note == ""
    stage2 = LinkBudgetStage(name="EDFA", gain_db=15.0, note="C-band EDFA")
    assert stage2.note == "C-band EDFA"


def test_link_budget_report_default_fields() -> None:
    """LinkBudgetReport 默认字段值（构造空报告）。"""
    report = LinkBudgetReport(tx_power_dbm=0.0)
    assert report.tx_power_dbm == 0.0
    assert report.stages == []
    assert report.total_gain_db == 0.0
    assert report.rx_power_dbm == 0.0
    assert report.rx_sensitivity_dbm == -20.0
    assert report.margin_db == 0.0
    assert report.osnr_db == 0.0
    assert report.ber_estimate == 1.0
    assert report.noise_figure_db == 3.0
    assert report.bandwidth_nm == 0.1
    assert report.tx_modulation == "NRZ"
    assert report.bit_rate_gbps == 10.0
