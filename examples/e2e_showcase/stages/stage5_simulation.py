"""阶段 5: 仿真验证。

对 MZI 电路执行 1500-1600nm 频域 S 参数扫描，计算谐振波长与消光比；
对 Clements 4x4 计算酉矩阵传输并验证酉性；对 MZI 调制器生成 PAM4 眼图，
计算 BER 与 SNR。

公式来源:
- MZI 传输率: T = sin²(π·n_eff·ΔL/λ)
  — Saleh & Teich, "Photonics", 2019
- 消光比: ER = 10·log10(T_max/T_min)
- PAM4 BER: Shafik et al., IEEE CommSurveys 2016
  https://ieeexplore.ieee.org/document/7545186
- Clements 分解: Clements et al., Optica 2016
  https://doi.org/10.1364/OPTICA.3.001460

API 来源:
- SAX 频域仿真: https://flaport.github.io/sax/
- Simphony 光子电路仿真: https://simphonyphotonics.readthedocs.io/
"""

from __future__ import annotations

import csv
import json
import logging
from pathlib import Path

import numpy as np

from polaris.sim import (
    clements_unitary,
    compute_ber,
    compute_eye_diagram,
    compute_snr_db,
    generate_pam4_signal,
    grating_coupler_s,
    mmi_1x2_s,
    mmi_2x2_s,
    waveguide_s,
)

_logger = logging.getLogger("e2e_showcase")

# MZI 电路参数（与 stage3/stage4 一致）
_MZI_WG1_LENGTH_UM = 100.0  # 波导臂 1 长度 (μm)
_MZI_WG2_LENGTH_UM = 120.0  # 波导臂 2 长度 (μm)
_MZI_NEFF = 2.4  # 有效折射率（Si 220nm SOI 典型值，来源: SiEPIC EBeam PDK）
_MZI_WG_LOSS_DB_CM = 3.0  # 波导损耗 (dB/cm，来源: SiEPIC EBeam PDK 典型值)

# 波长扫描参数
_WL_START_NM = 1500
_WL_STOP_NM = 1600
_WL_N_POINTS = 101


def _simulate_mzi_sparam(reports_dir: Path) -> dict:
    """MZI 频域 S 参数扫描。

    用 waveguide_s / mmi_1x2_s / mmi_2x2_s / grating_coupler_s 构建 MZI
    各器件 S 参数，结合 MZI 干涉传输率公式计算总传输率。

    公式来源:
        MZI 传输率: T = sin²(π·n_eff·ΔL/λ)
        — Saleh & Teich, "Photonics", 2019
        消光比: ER = 10·log10(T_max/T_min)

    Args:
        reports_dir: 报告输出目录。

    Returns:
        含 resonant_wavelength_nm / extinction_ratio_db / n_points / csv_path 的 dict。
    """
    _logger.info("MZI S 参数扫描: %d-%dnm, %d 点", _WL_START_NM, _WL_STOP_NM, _WL_N_POINTS)

    # 波长扫描: 1500-1600nm, 101 点
    wl_nm = np.linspace(_WL_START_NM, _WL_STOP_NM, _WL_N_POINTS)
    wl_um = wl_nm / 1000.0  # 转换为 μm（S 参数模型输入单位）

    # 臂长差
    delta_L = _MZI_WG2_LENGTH_UM - _MZI_WG1_LENGTH_UM  # ΔL = 20μm

    # 获取各器件 S 参数（调用 polaris.sim 模型）
    # 来源: waveguide_s/mmi_1x2_s/mmi_2x2_s/grating_coupler_s 来自 SiEPIC EBeam PDK
    wg1_s = waveguide_s(wl_um, length=_MZI_WG1_LENGTH_UM, neff=_MZI_NEFF,
                        loss_db_cm=_MZI_WG_LOSS_DB_CM)
    wg2_s = waveguide_s(wl_um, length=_MZI_WG2_LENGTH_UM, neff=_MZI_NEFF,
                        loss_db_cm=_MZI_WG_LOSS_DB_CM)
    mmi1_s = mmi_1x2_s(wl_um, insertion_loss_db=0.4)  # SiEPIC mmi1x2 1550nm
    mmi2_s = mmi_2x2_s(wl_um, insertion_loss_db=0.5)  # SiEPIC mmi2x2 1550nm
    gc_s = grating_coupler_s(wl_um, peak_wl=1.55, bandwidth_3db=0.04,
                             insertion_loss_db=1.9)

    # 从 S 参数提取振幅传输系数
    gc_amp = np.abs(gc_s[("waveguide", "fiber")])  # 光栅耦合器振幅传输
    gc_T = gc_amp ** 2  # 功率传输率

    mmi1_amp = np.abs(mmi1_s[("out1", "in")])  # MMI 1x2 每端口振幅
    mmi1_T = mmi1_amp ** 2  # 每端口功率传输率

    mmi2_amp = np.abs(mmi2_s[("out1", "in1")])  # MMI 2x2 bar 端振幅
    mmi2_T = mmi2_amp ** 2  # bar 端功率传输率

    # 波导振幅传输（含损耗）
    wg1_amp = np.abs(wg1_s[("out", "in")])
    wg2_amp = np.abs(wg2_s[("out", "in")])
    wg_loss_avg = (wg1_amp + wg2_amp) / 2.0  # 两臂平均振幅损耗

    # MZI 干涉传输率: T = sin²(π·n_eff·ΔL/λ)
    # 来源: Saleh & Teich, "Photonics", 2019
    # 两臂相位差 Δφ = 2π·n_eff·ΔL/λ，传输率 T = sin²(Δφ/2)
    phase_half = np.pi * _MZI_NEFF * delta_L / wl_um  # Δφ/2 = π·n_eff·ΔL/λ
    T_mzi = np.sin(phase_half) ** 2

    # 总传输率（含各器件级联损耗）
    # T_total = T_gc² × T_mmi1 × T_mzi × T_mmi2 × |wg|²
    T_total = gc_T * gc_T * mmi1_T * T_mzi * mmi2_T * (wg_loss_avg ** 2)

    # 谐振波长（传输率峰值对应的波长）
    peak_idx = int(np.argmax(T_total))
    resonant_wl_nm = float(wl_nm[peak_idx])

    # 消光比: ER = 10·log10(T_max/T_min)
    T_max = float(np.max(T_total))
    T_min = float(np.min(T_total))
    if T_min > 0:
        extinction_ratio_db = 10.0 * np.log10(T_max / T_min)
    else:
        extinction_ratio_db = float("inf")

    _logger.info(
        "MZI 谐振波长: %.2fnm, 消光比: %.2fdB (T_max=%.6f, T_min=%.6f)",
        resonant_wl_nm, extinction_ratio_db, T_max, T_min,
    )

    # 保存 S 参数数据到 CSV
    csv_path = reports_dir / "mzi_s_param.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "wavelength_nm", "T_mzi", "T_total", "T_total_db",
            "gc_T_db", "mmi1_T_db", "mmi2_T_db",
        ])
        for i in range(len(wl_nm)):
            t_total_db = 10 * np.log10(T_total[i]) if T_total[i] > 0 else float("-inf")
            writer.writerow([
                f"{wl_nm[i]:.2f}",
                f"{T_mzi[i]:.8f}",
                f"{T_total[i]:.8f}",
                f"{t_total_db:.4f}",
                f"{10 * np.log10(gc_T[i]):.4f}",
                f"{10 * np.log10(mmi1_T[i]):.4f}",
                f"{10 * np.log10(mmi2_T[i]):.4f}",
            ])

    _logger.info("MZI S 参数数据已保存: %s", csv_path)

    return {
        "resonant_wavelength_nm": resonant_wl_nm,
        "extinction_ratio_db": extinction_ratio_db,
        "n_points": _WL_N_POINTS,
        "wl_start_nm": _WL_START_NM,
        "wl_stop_nm": _WL_STOP_NM,
        "T_max": T_max,
        "T_min": T_min,
        "csv_path": str(csv_path),
    }


def _simulate_clements(reports_dir: Path) -> dict:
    """Clements 4x4 酉矩阵传输计算。

    用 clements_unitary 生成 4x4 酉矩阵，计算传输矩阵 T = |U|²，
    验证酉性 U @ U.conj().T ≈ I。

    来源:
        Clements et al., "Optimal design for universal multiport
        interferometers", Optica 2016, https://doi.org/10.1364/OPTICA.3.001460

    Args:
        reports_dir: 报告输出目录。

    Returns:
        含 n_modes / unitarity_error / is_unitary / json_path 的 dict。
    """
    n_modes = 4
    _logger.info("Clements %dx%d 酉矩阵计算", n_modes, n_modes)

    # 生成 4x4 酉矩阵（随机参数，固定种子保证可复现）
    U = clements_unitary(n_modes=n_modes)

    # 传输矩阵 T = |U|²（功率传输）
    T = np.abs(U) ** 2

    # 验证酉性: U @ U.conj().T ≈ I
    identity = np.eye(n_modes, dtype=complex)
    unitarity_error = float(np.max(np.abs(U @ U.conj().T - identity)))
    is_unitary = unitarity_error < 1e-6

    _logger.info(
        "Clements 酉性验证: error=%.2e, is_unitary=%s",
        unitarity_error, is_unitary,
    )

    # 保存酉矩阵到 JSON（复数拆分为实部和虚部）
    json_path = reports_dir / "clements_unitary.json"
    data = {
        "n_modes": n_modes,
        "source": "Clements et al., Optica 2016",
        "unitary_real": U.real.tolist(),
        "unitary_imag": U.imag.tolist(),
        "transmission": T.tolist(),
        "unitarity_error": unitarity_error,
        "is_unitary": is_unitary,
    }
    with json_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    _logger.info("Clements 酉矩阵已保存: %s", json_path)

    return {
        "n_modes": n_modes,
        "unitarity_error": unitarity_error,
        "is_unitary": is_unitary,
        "json_path": str(json_path),
    }


def _simulate_pam4(reports_dir: Path) -> dict:
    """PAM4 眼图仿真。

    用 generate_pam4_signal 生成 PAM4 信号，用 compute_eye_diagram 计算眼图，
    用 compute_ber 计算 BER，用 compute_snr_db 计算 SNR。

    公式来源:
        PAM4 BER: Shafik et al., IEEE CommSurveys 2016
        https://ieeexplore.ieee.org/document/7545186
        BER ≈ 0.5 * erfc(√(SNR/2))

    Args:
        reports_dir: 报告输出目录。

    Returns:
        含 ber / snr_db / n_symbols / bit_rate_gbps / json_path 的 dict。
    """
    n_symbols = 1000
    bit_rate = 100e9  # 100 Gbps
    samples_per_symbol = 16
    noise_std = 0.05

    _logger.info(
        "PAM4 眼图仿真: %d 符号, %.0f Gbps, %d 采样/符号",
        n_symbols, bit_rate / 1e9, samples_per_symbol,
    )

    # 生成 PAM4 信号
    # 来源: OIF CEI-112G 标准, https://www.oiforum.com/
    _time, signal = generate_pam4_signal(
        n_symbols=n_symbols,
        bit_rate=bit_rate,
        samples_per_symbol=samples_per_symbol,
        seed=42,
    )

    # 计算眼图
    eye = compute_eye_diagram(signal, samples_per_symbol=samples_per_symbol, n_levels=4)

    # 计算 BER
    # 来源: Shafik et al., IEEE CommSurveys 2016
    ber = compute_ber(
        signal, samples_per_symbol=samples_per_symbol,
        n_levels=4, noise_std=noise_std,
    )

    # 计算 SNR
    snr_db = compute_snr_db(signal, noise_std=noise_std)

    _logger.info("PAM4 眼图: BER=%.6e, SNR=%.2fdB", ber, snr_db)

    # 保存眼图数据到 JSON
    json_path = reports_dir / "pam4_eye.json"
    data = {
        "n_symbols": n_symbols,
        "bit_rate_gbps": bit_rate / 1e9,
        "samples_per_symbol": samples_per_symbol,
        "noise_std": noise_std,
        "ber": ber,
        "snr_db": snr_db,
        "eye_shape": list(eye.shape),
        "eye_data": eye.tolist(),
        "source": "Shafik et al., IEEE CommSurveys 2016",
    }
    with json_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    _logger.info("PAM4 眼图数据已保存: %s", json_path)

    return {
        "ber": ber,
        "snr_db": snr_db,
        "n_symbols": n_symbols,
        "bit_rate_gbps": bit_rate / 1e9,
        "json_path": str(json_path),
    }


def run(output_dir: Path) -> dict:
    """执行阶段 5: 仿真验证。

    对 MZI 电路执行频域 S 参数扫描，对 Clements 4x4 计算酉矩阵传输，
    对 MZI 调制器生成 PAM4 眼图。

    Args:
        output_dir: 输出目录（含 reports/ 子目录）。

    Returns:
        含 mzi_s_param / clements_unitary / pam4 三个子 dict 的结果。
    """
    _logger.info("阶段 5 开始: 仿真验证")

    reports_dir = output_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    # 1. MZI 频域 S 参数扫描
    mzi_result = _simulate_mzi_sparam(reports_dir)

    # 2. Clements 4x4 酉矩阵
    clements_result = _simulate_clements(reports_dir)

    # 3. PAM4 眼图仿真
    pam4_result = _simulate_pam4(reports_dir)

    _logger.info("阶段 5 完成: 仿真验证")

    return {
        "mzi_s_param": mzi_result,
        "clements_unitary": clements_result,
        "pam4": pam4_result,
    }
