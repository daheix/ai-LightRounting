"""阶段 8: 光电协同 PAM4 链路分析。

光电协同 PAM4 眼图与 BER/SNR 分析（含光路损耗 + 探测器散粒噪声 + TIA 热噪声）。

PoLaRIS v5.0 迁移说明:
    旧 v4 含 Verilog-A 紧凑模型生成 + Ngspice 联合仿真网表 + MNA 求解器
    （polaris.sim.mna_spice / polaris.sim.verilog_a）。v5.0 未提供独立的
    SPICE 联合仿真子模块（无 polaris_spice），故本 stage 简化为调用
    polaris-pam4 子模块的稳定 API 进行光电协同 PAM4 链路分析，
    保留探测器噪声建模（散粒噪声 + 热噪声）作为光电协同的关键物理环节。
    Verilog-A 模型生成与 Ngspice 联合仿真待未来 polaris-spice 子模块建立后
    再恢复。

公式来源（R02 学术诚信）:
- PAM4 BER: Shafik et al., IEEE CommSurveys 2016
  https://ieeexplore.ieee.org/document/7410082
- PAM4 信号: OIF CEI-112G 标准 https://www.oiforum.com/
- 探测器散粒噪声: i_shot = √(2·q·R·P·B)
  来源: Saleh & Teich, "Photonics", 2019, §17.5
- 探测器热噪声: i_thermal = √(4·k·T·B/R_L)
  来源: Saleh & Teich, "Photonics", 2019, §17.4
- Ansys Lumerical INTERCONNECT 眼图分析
  https://optics.ansys.com/hc/en-us/articles/49697869166611
- Chrostowski & Hochberg, "Silicon Photonics Design", Cambridge 2015, §9
  https://www.cambridge.org/core/books/silicon-photonics-design/
- NIST CODATA 2018 物理常量
  https://physics.nist.gov/cuu/Constants/
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import numpy as np

from polaris_pam4 import (
    compute_ber,
    compute_eye_diagram,
    compute_snr_db,
    generate_pam4_signal,
)

_logger = logging.getLogger("e2e_showcase")

# =============================================================================
# 光电协同链路参数（与 stage5 纯光路 PAM4 不同）
# =============================================================================
# stage8: 光电协同 PAM4（含光路损耗 + 探测器散粒噪声 + TIA 热噪声）
# stage5: 纯光路 PAM4（仅光调制器噪声, n_symbols=1000, samples=16,
#         noise=0.05, seed=42）

# PAM4 信号参数（与 stage5 不同）
# 来源: OIF CEI-112G 标准 https://www.oiforum.com/
_PAM4_N_SYMBOLS = 2000  # stage5=1000, stage8=2000（更多符号）
_PAM4_BIT_RATE = 100e9  # 100 Gbps（与 stage5 相同）
_PAM4_SAMPLES_PER_SYMBOL = 32  # stage5=16, stage8=32（更高采样率）
_PAM4_BASE_NOISE_STD = 0.08  # stage5=0.05, stage8=0.08（含 TIA 噪声）
_PAM4_SEED = 88  # stage5=42, stage8=88（不同种子）

# 光路损耗（来自 stage4 MZI 电路典型值）
# 来源: stage4_routing.py 中 MZI 电路 total_loss_db 典型值
_OPTICAL_LOSS_DB = 5.7

# 探测器参数（Si 探测器典型值）
# 来源: Chrostowski 2015 §9.2, Saleh & Teich 2019 §17.5
_DETECTOR_RESPONSIVITY = 1.0  # A/W
_DETECTOR_DARK_CURRENT_A = 10e-9  # 10 nA
_LOAD_RESISTANCE_OHM = 50.0  # Ω（射频标准 50Ω）
_TEMPERATURE_K = 300.0  # K（室温 27°C）

# 物理常量
# 来源: NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
_Q_ELECTRON_C = 1.602e-19  # 电子电荷 (C)
_K_BOLTZMANN_J_K = 1.381e-23  # 玻尔兹曼常数 (J/K)

# 输入光功率（1 mW = 0 dBm，典型激光器输出）
_INPUT_OPTICAL_POWER_W = 1e-3  # 1 mW

# 链路预算参数
# 来源: IEEE 802.3ba 链路预算标准
_LINK_BUDGET_TARGET_DB = 20.0  # 目标链路预算 20 dB


# =============================================================================
# 探测器噪声建模（光电协同关键物理环节）
# =============================================================================
def _compute_detector_noise(bit_rate: float) -> dict:
    """计算探测器噪声（散粒噪声 + 热噪声）。

    散粒噪声: i_shot = √(2·q·R·P_signal·B)
    热噪声: i_thermal = √(4·k·T·B/R_L)

    来源:
    - Saleh & Teich, "Photonics", 2019, §17.4/§17.5
      https://www.wiley.com/en-us/Photonics%3A+From+Basics+to+Advanced+Course
    - Chrostowski 2015 §9.2
      https://www.cambridge.org/core/books/silicon-photonics-design/

    Args:
        bit_rate: 比特率（bps）。

    Returns:
        dict 含 shot_noise_a/thermal_noise_a/signal_power_w/optical_loss_db。
    """
    # 光路损耗（来自 stage4）
    optical_attenuation = 10 ** (-_OPTICAL_LOSS_DB / 10)

    # 信号功率（1mW 输入，经光路损耗）
    signal_power = _INPUT_OPTICAL_POWER_W * optical_attenuation

    # Nyquist 带宽 = bit_rate / 2
    # 来源: Nyquist 采样定理
    bandwidth = bit_rate / 2.0

    # 散粒噪声: i_shot = √(2·q·R·P·B)
    # 来源: Saleh & Teich 2019 §17.5
    shot_noise_std = np.sqrt(
        2 * _Q_ELECTRON_C * _DETECTOR_RESPONSIVITY * signal_power * bandwidth
    )

    # 热噪声: i_thermal = √(4·k·T·B/R_L)
    # 来源: Saleh & Teich 2019 §17.4
    thermal_noise_std = np.sqrt(
        4 * _K_BOLTZMANN_J_K * _TEMPERATURE_K * bandwidth / _LOAD_RESISTANCE_OHM
    )

    _logger.info(
        "探测器噪声: 散粒=%.4e A, 热噪声=%.4e A, 信号功率=%.4e W",
        shot_noise_std,
        thermal_noise_std,
        signal_power,
    )

    return {
        "shot_noise_a": float(shot_noise_std),
        "thermal_noise_a": float(thermal_noise_std),
        "signal_power_w": float(signal_power),
        "optical_loss_db": _OPTICAL_LOSS_DB,
    }


# =============================================================================
# 光电协同 PAM4 眼图与 BER 分析
# =============================================================================
def _generate_pam4_analysis(reports_dir: Path) -> dict:
    """生成光电协同 PAM4 眼图与 BER/SNR 分析。

    与 stage5 纯光路 PAM4 不同，stage8 含:
    - 光路损耗（来自 stage4）
    - 探测器散粒噪声
    - 探测器热噪声
    - TIA 基础噪声

    流程:
    1. 计算探测器噪声（散粒 + 热噪声）
    2. 合成总噪声 = √(base² + shot² + thermal²）
    3. 生成 PAM4 信号（不同参数: 2000 符号, 32 采样, seed=88）
    4. 计算眼图、BER、SNR

    PAM4 BER 公式: BER ≈ 0.5 * erfc(√(SNR/2))
    来源: Shafik et al., IEEE CommSurveys 2016
      https://ieeexplore.ieee.org/document/7410082

    Args:
        reports_dir: 报告输出目录。

    Returns:
        dict 含 BER/SNR/眼图/噪声分解等。

    Raises:
        RuntimeError: PAM4 分析失败（R03 禁止 fall-back）。
    """
    _logger.info("生成光电协同 PAM4 眼图与 BER 分析")

    # 步骤 1: 计算探测器噪声
    noise_info = _compute_detector_noise(_PAM4_BIT_RATE)
    shot_noise = noise_info["shot_noise_a"]
    thermal_noise = noise_info["thermal_noise_a"]

    # 步骤 2: 合成总噪声
    # 总噪声 = √(base² + shot² + thermal²）
    # base 噪声归一化到信号电平（信号幅度 ~1V）
    # shot/thermal 噪声单位是 A，需转换为 V（V = I × R_load）
    shot_noise_v = shot_noise * _LOAD_RESISTANCE_OHM
    thermal_noise_v = thermal_noise * _LOAD_RESISTANCE_OHM
    total_noise_std = float(
        np.sqrt(
            _PAM4_BASE_NOISE_STD ** 2
            + shot_noise_v ** 2
            + thermal_noise_v ** 2
        )
    )

    _logger.info(
        "总噪声: base=%.4f V, shot=%.4e V, thermal=%.4e V, total=%.4f V",
        _PAM4_BASE_NOISE_STD,
        shot_noise_v,
        thermal_noise_v,
        total_noise_std,
    )

    # 步骤 3: 生成 PAM4 信号（与 stage5 不同: 2000 符号, 32 采样, seed=88）
    # 来源: OIF CEI-112G 标准 https://www.oiforum.com/
    time, signal = generate_pam4_signal(
        n_symbols=_PAM4_N_SYMBOLS,
        bit_rate=_PAM4_BIT_RATE,
        samples_per_symbol=_PAM4_SAMPLES_PER_SYMBOL,
        seed=_PAM4_SEED,
    )
    _logger.info(
        "PAM4 信号: %d 符号, 比特率=%.2e bps, 采样点=%d, seed=%d",
        _PAM4_N_SYMBOLS,
        _PAM4_BIT_RATE,
        len(signal),
        _PAM4_SEED,
    )

    # 步骤 4: 计算眼图
    # 来源: Lumerical INTERCONNECT 眼图分析
    eye = compute_eye_diagram(
        signal=signal,
        samples_per_symbol=_PAM4_SAMPLES_PER_SYMBOL,
        n_levels=4,
    )
    _logger.info("眼图矩阵: %s (shape=%s)", eye.shape, eye.shape)

    # 步骤 5: 计算 BER（使用总噪声）
    # BER ≈ 0.5 * erfc(√(SNR/2))
    # 来源: Shafik et al., IEEE CommSurveys 2016
    ber = compute_ber(
        signal=signal,
        samples_per_symbol=_PAM4_SAMPLES_PER_SYMBOL,
        n_levels=4,
        noise_std=total_noise_std,
    )
    _logger.info("BER = %.6e (总噪声 std=%.4f V)", ber, total_noise_std)

    # 步骤 6: 计算 SNR
    # SNR_dB = 10 * log10(P_signal / P_noise)
    snr_db = compute_snr_db(signal=signal, noise_std=total_noise_std)
    _logger.info("SNR = %.2f dB", snr_db)

    # 步骤 7: 计算链路预算余量
    # 链路预算余量 = 目标预算 - 实际损耗
    # 来源: IEEE 802.3ba 链路预算标准
    link_budget_margin = _LINK_BUDGET_TARGET_DB - _OPTICAL_LOSS_DB

    # 步骤 8: 保存眼图数据到 JSON
    eye_path = reports_dir / "pam4_eye_optoelectronic.json"
    eye_data = {
        "stage": "stage8_opto_electrical",
        "description": "光电协同 PAM4（含光路损耗 + 探测器噪声 + TIA 噪声）",
        "n_symbols": _PAM4_N_SYMBOLS,
        "bit_rate_bps": _PAM4_BIT_RATE,
        "samples_per_symbol": _PAM4_SAMPLES_PER_SYMBOL,
        "seed": _PAM4_SEED,
        "noise_breakdown": {
            "base_noise_v": _PAM4_BASE_NOISE_STD,
            "shot_noise_v": float(shot_noise_v),
            "thermal_noise_v": float(thermal_noise_v),
            "total_noise_v": total_noise_std,
        },
        "optical_loss_db": _OPTICAL_LOSS_DB,
        "signal_power_w": noise_info["signal_power_w"],
        "ber": float(ber),
        "snr_db": float(snr_db),
        "link_budget_margin_db": float(link_budget_margin),
        "eye_shape": list(eye.shape),
        # 眼图矩阵下采样（每 4 个点取 1 个，避免 JSON 过大）
        "eye_data_downsampled": eye[::4, :].tolist(),
        "signal_mean": float(np.mean(signal)),
        "signal_std": float(np.std(signal)),
        # 公式来源标注（R02 学术诚信）
        "formula_source": {
            "ber": "BER ≈ 0.5 * erfc(√(SNR/2)), Shafik et al. IEEE CommSurveys 2016",
            "snr": "SNR_dB = 10 * log10(P_signal / P_noise)",
            "shot_noise": "i_shot = √(2·q·R·P·B), Saleh & Teich 2019 §17.5",
            "thermal_noise": "i_thermal = √(4·k·T·B/R_L), Saleh & Teich 2019 §17.4",
            "pam4": "OIF CEI-112G 标准, 4 电平 (0, 1/3, 2/3, 1)",
        },
        "migration_note": (
            "PoLaRIS v5.0: 简化为 polaris-pam4 调用，"
            "Verilog-A/Ngspice 联合仿真待 polaris-spice 子模块建立后恢复"
        ),
    }
    eye_path.write_text(json.dumps(eye_data, indent=2), encoding="utf-8")
    _logger.info("眼图数据保存: %s", eye_path.name)

    return {
        "ber": float(ber),
        "snr_db": float(snr_db),
        "eye_path": str(eye_path),
        "n_symbols": _PAM4_N_SYMBOLS,
        "bit_rate": _PAM4_BIT_RATE,
        "total_noise_std": total_noise_std,
        "shot_noise_a": float(shot_noise),
        "thermal_noise_a": float(thermal_noise),
        "optical_loss_db": _OPTICAL_LOSS_DB,
        "link_budget_margin_db": float(link_budget_margin),
    }


# =============================================================================
# 主流程
# =============================================================================
def run(output_dir: Path) -> dict:
    """执行阶段 8: 光电协同 PAM4 链路分析。

    v5.0 简化版（无 Verilog-A / Ngspice 联合仿真），保留光电协同的核心
    物理环节——探测器噪声建模（散粒噪声 + 热噪声）+ PAM4 眼图与 BER 分析。

    流程:
    1. 计算探测器噪声（散粒 + 热噪声）
    2. 合成总噪声
    3. 生成 PAM4 信号（polaris-pam4）
    4. 计算眼图、BER、SNR（polaris-pam4）
    5. 保存眼图数据到 JSON

    Args:
        output_dir: 输出目录。

    Returns:
        dict 含:
        - pam4: dict 含 BER/SNR/噪声分解
        - optical_loss_db: 光路损耗（来自 stage4）
        - detector_shot_noise_a: 探测器散粒噪声电流
        - detector_thermal_noise_a: 探测器热噪声电流
        - link_budget_margin_db: 链路预算余量
        - pam4_ber: 光电协同 PAM4 BER（与 stage5 不同）
        - pam4_snr_db: 光电协同 PAM4 SNR

    Raises:
        RuntimeError: PAM4 分析失败（R03 禁止 fall-back）。
    """
    _logger.info("阶段 8 开始: 光电协同 PAM4 链路分析（polaris-pam4）")
    output_dir = Path(output_dir)

    reports_dir = output_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    # 生成光电协同 PAM4 眼图与 BER
    # BER 公式: BER ≈ 0.5 * erfc(√(SNR/2))
    # 来源: Shafik et al., IEEE CommSurveys 2016
    #   https://ieeexplore.ieee.org/document/7410082
    pam4 = _generate_pam4_analysis(reports_dir)

    _logger.info(
        "阶段 8 完成: BER=%.2e, SNR=%.2f dB, 链路余量=%.2f dB",
        pam4["ber"],
        pam4["snr_db"],
        pam4["link_budget_margin_db"],
    )

    return {
        "pam4": pam4,
        "optical_loss_db": pam4["optical_loss_db"],
        "detector_shot_noise_a": pam4["shot_noise_a"],
        "detector_thermal_noise_a": pam4["thermal_noise_a"],
        "link_budget_margin_db": pam4["link_budget_margin_db"],
        "pam4_ber": pam4["ber"],
        "pam4_snr_db": pam4["snr_db"],
    }
