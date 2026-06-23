"""阶段 8: 光电协同。

生成 Verilog-A 紧凑模型、SPICE 联合仿真网表与 PAM4 眼图，
演示光电协同仿真能力。

产物:
- Verilog-A 模型文件（5 器件: 波导/MMI/环/调制器/探测器）
- Ngspice 联合仿真网表
- PAM4 眼图与 BER/SNR

对应路标: R35（Verilog-A + SPICE + PAM4 眼图）

公式来源（学术诚信，规则 18）:
- Verilog-A 紧凑模型: Ansys Lumerical CML Compiler
  https://optics.ansys.com/hc/en-us/sections/360005039133-CML-Compiler
- SPICE 时间步同步: Δt_sync = max(Δt_SPICE, Δt_optical)
  来源: Chrostowski, "Silicon Photonics Design", Cambridge 2015, §8
- PAM4 BER: Shafik et al., IEEE CommSurveys 2016
  https://ieeexplore.ieee.org/document/7545186
- PAM4 信号: OIF CEI-112G 标准 https://www.oiforum.com/
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import numpy as np

from polaris.sim.verilog_a import (
    DEFAULT_SPICE_TIMESTEP_S,
    SPICESimulationConfig,
    compute_ber,
    compute_eye_diagram,
    compute_snr_db,
    generate_detector_verilog_a,
    generate_mmi_1x2_verilog_a,
    generate_modulator_verilog_a,
    generate_pam4_signal,
    generate_ring_verilog_a,
    generate_spice_netlist,
    generate_waveguide_verilog_a,
    save_verilog_a,
)

_logger = logging.getLogger("e2e_showcase")

# PAM4 信号参数
# 来源: OIF CEI-112G 标准 https://www.oiforum.com/
_PAM4_N_SYMBOLS = 1000
_PAM4_BIT_RATE = 100e9  # 100 Gbps
_PAM4_SAMPLES_PER_SYMBOL = 16
_PAM4_NOISE_STD = 0.05  # 噪声标准差 (V)


# =============================================================================
# Verilog-A 模型生成
# =============================================================================
def _generate_verilog_a_models(va_dir: Path) -> list[dict]:
    """为 5 个器件生成 Verilog-A 紧凑模型文件。

    器件清单:
    - waveguide (length_um=100): 波导传输模型
    - mmi_1x2: 3dB 分束器
    - ring_resonator (radius_um=10): 环谐振器
    - modulator (V_pi=3.0): MZM 调制器
    - detector (responsivity=1.0): 光电探测器

    来源: Ansys Lumerical CML Compiler
      https://optics.ansys.com/hc/en-us/sections/360005039133-CML-Compiler

    Args:
        va_dir: Verilog-A 输出目录。

    Returns:
        模型信息列表，每项含 device_type/file_path/lines。

    Raises:
        RuntimeError: 模型生成或保存失败（规则 14.1: 无 fall-back）。
    """
    _logger.info("生成 Verilog-A 模型 (5 器件)")

    # 器件类型 → 生成器调用配置
    # 参数来源: Chrostowski 2015 + SiEPIC EBeam PDK 典型值
    device_configs = [
        {
            "device_type": "waveguide",
            "generator": generate_waveguide_verilog_a,
            "kwargs": {"length_um": 100.0},
        },
        {
            "device_type": "mmi_1x2",
            "generator": generate_mmi_1x2_verilog_a,
            "kwargs": {},
        },
        {
            "device_type": "ring_resonator",
            "generator": generate_ring_verilog_a,
            "kwargs": {"radius_um": 10.0},
        },
        {
            "device_type": "modulator",
            "generator": generate_modulator_verilog_a,
            "kwargs": {"v_pi": 3.0},
        },
        {
            "device_type": "detector",
            "generator": generate_detector_verilog_a,
            "kwargs": {"responsivity": 1.0},
        },
    ]

    results: list[dict] = []
    for cfg in device_configs:
        device_type = cfg["device_type"]
        _logger.info("生成 Verilog-A: %s", device_type)

        # 调用生成器（无 fall-back，失败即 raise）
        model = cfg["generator"](**cfg["kwargs"])

        # 保存到 output_dir/verilog_a/{device_type}.va
        file_path = va_dir / f"{device_type}.va"
        save_verilog_a(model, file_path)

        lines = len(model.verilog_a_code.splitlines())
        _logger.info(
            "Verilog-A 保存: %s (%d 行, module=%s)",
            file_path.name,
            lines,
            model.module_name,
        )
        results.append(
            {
                "device_type": device_type,
                "file_path": str(file_path),
                "lines": lines,
            }
        )

    _logger.info("Verilog-A 模型生成完成: %d 个器件", len(results))
    return results


# =============================================================================
# SPICE 联合仿真网表生成
# =============================================================================
def _generate_spice_netlist_file(
    va_dir: Path,
    spice_dir: Path,
) -> dict:
    """生成 Ngspice 联合仿真网表。

    用 generate_spice_netlist 生成网表，包含 5 个 Verilog-A 器件实例，
    保存到 output_dir/spice/cosim.cir。

    SPICE 时间步同步公式: Δt_sync = max(Δt_SPICE, Δt_optical)
    来源: Chrostowski, "Silicon Photonics Design", Cambridge 2015, §8

    Args:
        va_dir: Verilog-A 目录（用于读取模型列表）。
        spice_dir: SPICE 网表输出目录。

    Returns:
        dict 含 file_path/lines。

    Raises:
        RuntimeError: 网表生成失败（规则 14.1: 无 fall-back）。
    """
    _logger.info("生成 SPICE 联合仿真网表")

    # 重新生成模型对象（用于网表实例化）
    # 来源: Ngspice 用户手册 https://ngspice.sourceforge.io/docs.html
    models = [
        generate_waveguide_verilog_a(length_um=100.0),
        generate_mmi_1x2_verilog_a(),
        generate_ring_verilog_a(radius_um=10.0),
        generate_modulator_verilog_a(v_pi=3.0),
        generate_detector_verilog_a(responsivity=1.0),
    ]

    # SPICE 仿真配置
    # 时间步同步: Δt_sync = max(Δt_SPICE, Δt_optical)
    # 来源: Chrostowski 2015 §8
    config = SPICESimulationConfig(
        spice_timestep=DEFAULT_SPICE_TIMESTEP_S,
        optical_timestep=1e-13,
        total_time=1e-9,
        temperature=25.0,
    )
    _logger.info(
        "SPICE 配置: Δt_spice=%.2e s, Δt_optical=%.2e s, Δt_sync=%.2e s",
        config.spice_timestep,
        config.optical_timestep,
        config.sync_timestep,
    )

    # 生成网表（PAM4 输入信号）
    netlist = generate_spice_netlist(
        models=models,
        config=config,
        input_signal="pam4",
    )

    # 保存网表
    netlist_path = spice_dir / "cosim.cir"
    netlist_path.write_text(netlist, encoding="utf-8")
    lines = len(netlist.splitlines())
    _logger.info("SPICE 网表保存: %s (%d 行)", netlist_path.name, lines)

    return {"file_path": str(netlist_path), "lines": lines}


# =============================================================================
# PAM4 眼图与 BER 分析
# =============================================================================
def _generate_pam4_analysis(reports_dir: Path) -> dict:
    """生成 PAM4 眼图与 BER/SNR 分析。

    流程:
    1. 用 generate_pam4_signal 生成 PAM4 信号
    2. 用 compute_eye_diagram 计算眼图
    3. 用 compute_ber 计算 BER
    4. 用 compute_snr_db 计算 SNR
    5. 保存眼图数据到 output_dir/reports/pam4_eye.json

    PAM4 BER 公式: BER ≈ 0.5 * erfc(√(SNR/2))
    来源: Shafik et al., IEEE CommSurveys 2016
      https://ieeexplore.ieee.org/document/7545186

    PAM4 信号: 4 电平脉冲幅度调制 (0, 1/3, 2/3, 1)
    来源: OIF CEI-112G 标准 https://www.oiforum.com/

    Args:
        reports_dir: 报告输出目录。

    Returns:
        dict 含 ber/snr_db/eye_path/n_symbols/bit_rate。

    Raises:
        RuntimeError: PAM4 分析失败（规则 14.1: 无 fall-back）。
    """
    _logger.info("生成 PAM4 眼图与 BER 分析")

    # 步骤 1: 生成 PAM4 信号
    # 来源: OIF CEI-112G 标准 https://www.oiforum.com/
    time, signal = generate_pam4_signal(
        n_symbols=_PAM4_N_SYMBOLS,
        bit_rate=_PAM4_BIT_RATE,
        samples_per_symbol=_PAM4_SAMPLES_PER_SYMBOL,
        seed=42,
    )
    _logger.info(
        "PAM4 信号: %d 符号, 比特率=%.2e bps, 采样点=%d",
        _PAM4_N_SYMBOLS,
        _PAM4_BIT_RATE,
        len(signal),
    )

    # 步骤 2: 计算眼图
    # 来源: Lumerical INTERCONNECT 眼图分析
    eye = compute_eye_diagram(
        signal=signal,
        samples_per_symbol=_PAM4_SAMPLES_PER_SYMBOL,
        n_levels=4,
    )
    _logger.info("眼图矩阵: %s (shape=%s)", eye.shape, eye.shape)

    # 步骤 3: 计算 BER
    # BER ≈ 0.5 * erfc(√(SNR/2))
    # 来源: Shafik et al., IEEE CommSurveys 2016
    ber = compute_ber(
        signal=signal,
        samples_per_symbol=_PAM4_SAMPLES_PER_SYMBOL,
        n_levels=4,
        noise_std=_PAM4_NOISE_STD,
    )
    _logger.info("BER = %.6e (噪声 std=%.3f V)", ber, _PAM4_NOISE_STD)

    # 步骤 4: 计算 SNR
    # SNR_dB = 10 * log10(P_signal / P_noise)
    snr_db = compute_snr_db(signal=signal, noise_std=_PAM4_NOISE_STD)
    _logger.info("SNR = %.2f dB", snr_db)

    # 步骤 5: 保存眼图数据到 JSON
    eye_path = reports_dir / "pam4_eye.json"
    eye_data = {
        "n_symbols": _PAM4_N_SYMBOLS,
        "bit_rate_bps": _PAM4_BIT_RATE,
        "samples_per_symbol": _PAM4_SAMPLES_PER_SYMBOL,
        "noise_std_v": _PAM4_NOISE_STD,
        "ber": float(ber),
        "snr_db": float(snr_db),
        "eye_shape": list(eye.shape),
        # 眼图矩阵下采样（每 4 个点取 1 个，避免 JSON 过大）
        "eye_data_downsampled": eye[::4, :].tolist(),
        "signal_mean": float(np.mean(signal)),
        "signal_std": float(np.std(signal)),
        # 公式来源标注（学术诚信，规则 18）
        "formula_source": {
            "ber": "BER ≈ 0.5 * erfc(√(SNR/2)), Shafik et al. IEEE CommSurveys 2016",
            "snr": "SNR_dB = 10 * log10(P_signal / P_noise)",
            "pam4": "OIF CEI-112G 标准, 4 电平 (0, 1/3, 2/3, 1)",
        },
    }
    eye_path.write_text(json.dumps(eye_data, indent=2), encoding="utf-8")
    _logger.info("眼图数据保存: %s", eye_path.name)

    return {
        "ber": float(ber),
        "snr_db": float(snr_db),
        "eye_path": str(eye_path),
        "n_symbols": _PAM4_N_SYMBOLS,
        "bit_rate": _PAM4_BIT_RATE,
    }


# =============================================================================
# 主流程
# =============================================================================
def run(output_dir: Path) -> dict:
    """执行阶段 8: 光电协同。

    生成 5 个 Verilog-A 紧凑模型、Ngspice 联合仿真网表、PAM4 眼图与 BER。

    Args:
        output_dir: 输出目录。

    Returns:
        dict 含:
        - verilog_a_models: 5 器件列表，每项含 device_type/file_path/lines
        - spice_netlist: dict 含 file_path/lines
        - pam4: dict 含 ber/snr_db/eye_path/n_symbols/bit_rate

    Raises:
        RuntimeError: 任何步骤失败（规则 14.1: 无 fall-back）。
    """
    _logger.info("阶段 8 开始: 光电协同")
    output_dir = Path(output_dir)

    # 创建输出子目录
    va_dir = output_dir / "verilog_a"
    spice_dir = output_dir / "spice"
    reports_dir = output_dir / "reports"
    va_dir.mkdir(parents=True, exist_ok=True)
    spice_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    # 步骤 1: 生成 5 个 Verilog-A 模型
    # 来源: Ansys Lumerical CML Compiler
    #   https://optics.ansys.com/hc/en-us/sections/360005039133-CML-Compiler
    verilog_a_models = _generate_verilog_a_models(va_dir)

    # 步骤 2: 生成 Ngspice 联合仿真网表
    # SPICE 时间步同步: Δt_sync = max(Δt_SPICE, Δt_optical)
    # 来源: Chrostowski, "Silicon Photonics Design", Cambridge 2015, §8
    spice_netlist = _generate_spice_netlist_file(va_dir, spice_dir)

    # 步骤 3: 生成 PAM4 眼图与 BER
    # BER 公式: BER ≈ 0.5 * erfc(√(SNR/2))
    # 来源: Shafik et al., IEEE CommSurveys 2016
    #   https://ieeexplore.ieee.org/document/7545186
    pam4 = _generate_pam4_analysis(reports_dir)

    _logger.info(
        "阶段 8 完成: %d Verilog-A 模型, SPICE 网表 %d 行, BER=%.2e, SNR=%.2f dB",
        len(verilog_a_models),
        spice_netlist["lines"],
        pam4["ber"],
        pam4["snr_db"],
    )

    return {
        "verilog_a_models": verilog_a_models,
        "spice_netlist": spice_netlist,
        "pam4": pam4,
    }
