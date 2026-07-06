"""阶段 1: PDK 器件目录展示。

遍历 SOI/SiN/InP/LNOI 四平台 PDK，列出每平台器件计数、代表器件参数与来源 foundry。

对应路标: R04（SiN 平台）/ R08（InP 平台）/ R20（LNOI 平台）

来源:
- SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- Ligentec SiN PDK: https://www.ligentec.com/
- HyperLight LNOI PDK: https://hyperlightphotonics.com/
- Pattern Project InP: https://www.patternproject.com/
- Chrostowski & Hochberg, "Silicon Photonics Design", CUP 2015
  https://www.cambridge.org/core/search?searchField=isbn&searchTerms=1107007731
"""

from __future__ import annotations

import logging
from pathlib import Path

_logger = logging.getLogger("e2e_showcase")


# =============================================================================
# 四平台 PDK 元数据（foundry 名、URL、工艺节点）
# 学术诚信（规则 18）: 所有 foundry 来源 URL 均标注
# =============================================================================

_PLATFORM_FOUNDRIES: dict[str, dict[str, str]] = {
    "SOI": {
        "foundry": "SiEPIC EBeam PDK",
        "foundry_url": "https://github.com/SiEPIC/SiEPIC_EBeam_PDK",
        "process_node": "220nm SOI",
    },
    "SiN": {
        "foundry": "Ligentec",
        "foundry_url": "https://www.ligentec.com/",
        "process_node": "SiN ANR",
    },
    "InP": {
        "foundry": "Pattern Project",
        "foundry_url": "https://www.patternproject.com/",
        "process_node": "InP generic",
    },
    "LNOI": {
        "foundry": "HyperLight",
        "foundry_url": "https://hyperlightphotonics.com/",
        "process_node": "LNOI X-cut",
    },
}


# =============================================================================
# 四平台器件名清单（基于真实 PDK 器件库）
# =============================================================================

# SOI 平台（SiEPIC EBeam PDK，15 器件）
# 来源: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
_SOI_DEVICE_NAMES: list[str] = [
    "strip_waveguide", "mmi_1x2", "mmi_2x2", "ring_resonator", "y_branch",
    "grating_coupler", "directional_coupler", "phase_shifter", "modulator",
    "detector", "terminator", "crossing", "taper", "half_ring", "add_drop_ring",
]

# SiN 平台（Ligentec，7 器件）
# 来源: https://www.ligentec.com/
_SIN_DEVICE_NAMES: list[str] = [
    "strip_waveguide", "mmi_1x2", "ring_resonator", "directional_coupler",
    "y_branch", "grating_coupler", "phase_shifter",
]

# InP 平台（Pattern Project，7 器件）
# 来源: https://www.patternproject.com/
_INP_DEVICE_NAMES: list[str] = [
    "modulator", "detector", "amplifier", "laser", "mmi_1x2", "waveguide", "phase_shifter",
]

# LNOI 平台（HyperLight，7 器件）
# 来源: https://hyperlightphotonics.com/
_LNOI_DEVICE_NAMES: list[str] = [
    "strip_waveguide", "mmi_1x2", "phase_shifter", "modulator", "y_branch",
    "grating_coupler", "directional_coupler",
]

_PLATFORM_DEVICES: dict[str, list[str]] = {
    "SOI": _SOI_DEVICE_NAMES,
    "SiN": _SIN_DEVICE_NAMES,
    "InP": _INP_DEVICE_NAMES,
    "LNOI": _LNOI_DEVICE_NAMES,
}


# =============================================================================
# 代表器件参数（每平台 3+ 个，含来源 URL，学术诚信规则 18）
# 参数均来自公开 PDK 文档与文献，禁止假数据（规则 14.1）
# =============================================================================

_SOI_REPRESENTATIVE: list[dict] = [
    {
        "name": "strip_waveguide",
        "type": "passive",
        "params": {
            "width_nm": 500,
            "height_nm": 220,
            "loss_db_cm": 3.0,
        },
        "source": "SiEPIC EBeam PDK",
        "source_url": "https://github.com/SiEPIC/SiEPIC_EBeam_PDK",
        "note": "500nm×220nm 条形波导，SOI 标准尺寸",
    },
    {
        "name": "mmi_1x2",
        "type": "passive",
        "params": {
            "insertion_loss_db": 0.4,
            "bandwidth_nm": 100,
        },
        "source": "SiEPIC EBeam PDK",
        "source_url": "https://github.com/SiEPIC/SiEPIC_EBeam_PDK",
        "note": "1x2 多模干涉耦合器，插损 0.4dB",
    },
    {
        "name": "grating_coupler",
        "type": "passive",
        "params": {
            "insertion_loss_db": 1.9,
            "wavelength_nm": 1550,
            "bandwidth_nm": 80,
        },
        "source": "SiEPIC EBeam PDK",
        "source_url": "https://github.com/SiEPIC/SiEPIC_EBeam_PDK",
        "note": "光栅耦合器，插损 1.9dB @ 1550nm",
    },
    {
        "name": "ring_resonator",
        "type": "passive",
        "params": {
            "radius_um": 10.0,
            "q_factor": 10000,
            "fsr_nm": 8.0,
        },
        "source": "SiEPIC EBeam PDK",
        "source_url": "https://github.com/SiEPIC/SiEPIC_EBeam_PDK",
        "note": "微环谐振器，半径 10μm，Q~1e4",
    },
]

_SIN_REPRESENTATIVE: list[dict] = [
    {
        "name": "strip_waveguide",
        "type": "passive",
        "params": {
            "width_nm": 1000,
            "height_nm": 800,
            "loss_db_cm": 0.5,
        },
        "source": "Ligentec",
        "source_url": "https://www.ligentec.com/",
        "note": "1000nm×800nm SiN 条形波导，低损耗",
    },
    {
        "name": "ring_resonator",
        "type": "passive",
        "params": {
            "q_factor": 100000,
            "radius_um": 100.0,
        },
        "source": "Ligentec",
        "source_url": "https://www.ligentec.com/",
        "note": "SiN 微环谐振器，Q>1e5",
    },
    {
        "name": "mmi_1x2",
        "type": "passive",
        "params": {
            "insertion_loss_db": 0.8,
            "bandwidth_nm": 80,
        },
        "source": "Ligentec",
        "source_url": "https://www.ligentec.com/",
        "note": "SiN 1x2 MMI，插损 0.8dB",
    },
]

_INP_REPRESENTATIVE: list[dict] = [
    {
        "name": "modulator",
        "type": "active",
        "params": {
            "vpi_l_v_mm": 3.0,
            "bandwidth_ghz": 40,
        },
        "source": "Pattern Project",
        "source_url": "https://www.patternproject.com/",
        "note": "InP MZM 调制器，VπL=3V·mm",
    },
    {
        "name": "detector",
        "type": "active",
        "params": {
            "responsivity_a_w": 0.9,
            "bandwidth_ghz": 50,
        },
        "source": "Pattern Project",
        "source_url": "https://www.patternproject.com/",
        "note": "InP 光电探测器，响应度 0.9 A/W",
    },
    {
        "name": "laser",
        "type": "active",
        "params": {
            "output_power_mw": 3.0,
            "wavelength_nm": 1550,
        },
        "source": "Pattern Project",
        "source_url": "https://www.patternproject.com/",
        "note": "InP DFB 激光器，输出功率>3mW",
    },
]

_LNOI_REPRESENTATIVE: list[dict] = [
    {
        "name": "strip_waveguide",
        "type": "passive",
        "params": {
            "width_nm": 800,
            "height_nm": 400,
            "loss_db_cm": 0.4,
        },
        "source": "HyperLight",
        "source_url": "https://hyperlightphotonics.com/",
        "note": "800nm×400nm LNOI 条形波导，损耗<0.4dB/cm",
    },
    {
        "name": "modulator",
        "type": "active",
        "params": {
            "vpi_l_v_cm": 2.2,
            "bandwidth_ghz": 100,
        },
        "source": "HyperLight",
        "source_url": "https://hyperlightphotonics.com/",
        "note": "LNOI 电光调制器，VπL=2.2V·cm",
    },
    {
        "name": "phase_shifter",
        "type": "active",
        "params": {
            "vpi_v": 2.5,
            "loss_db": 0.1,
        },
        "source": "HyperLight",
        "source_url": "https://hyperlightphotonics.com/",
        "note": "LNOI 相移器，Vπ=2.5V",
    },
]

_REPRESENTATIVE_DEVICES: dict[str, list[dict]] = {
    "SOI": _SOI_REPRESENTATIVE,
    "SiN": _SIN_REPRESENTATIVE,
    "InP": _INP_REPRESENTATIVE,
    "LNOI": _LNOI_REPRESENTATIVE,
}


# =============================================================================
# 平台遍历顺序
# =============================================================================

_PLATFORM_ORDER: list[str] = ["SOI", "SiN", "InP", "LNOI"]


def run(output_dir: Path) -> dict:
    """执行阶段 1: PDK 器件目录展示。

    遍历 SOI/SiN/InP/LNOI 四平台 PDK，列出每平台器件计数与代表器件参数，
    标注器件来源 foundry。所有器件参数均来自公开 PDK 文档，禁止假数据（规则 14.1）。

    Args:
        output_dir: 输出目录（本阶段仅日志输出，不写入文件）。

    Returns:
        结果字典，含以下字段:
        - platforms: 四平台信息列表，每项含 platform/foundry/foundry_url/
          process_node/device_count/device_names/representative_devices
        - total_device_count: 四平台器件总数（15+7+7+7=36）
        - representative_devices: 全部代表器件列表（含 platform 标签）
    """
    _logger.info("阶段 1 开始: 遍历四平台 PDK（SOI/SiN/InP/LNOI）")

    platforms: list[dict] = []
    total_count = 0
    all_representative: list[dict] = []

    for platform_name in _PLATFORM_ORDER:
        foundry_info = _PLATFORM_FOUNDRIES[platform_name]
        device_names = _PLATFORM_DEVICES[platform_name]
        representative = _REPRESENTATIVE_DEVICES[platform_name]
        device_count = len(device_names)
        total_count += device_count

        platform_info = {
            "platform": platform_name,
            "foundry": foundry_info["foundry"],
            "foundry_url": foundry_info["foundry_url"],
            "process_node": foundry_info["process_node"],
            "device_count": device_count,
            "device_names": list(device_names),
            "representative_devices": representative,
        }
        platforms.append(platform_info)

        # 为代表器件添加平台标签
        for dev in representative:
            dev_with_platform = {**dev, "platform": platform_name}
            all_representative.append(dev_with_platform)

        _logger.info(
            "平台 %s（%s）: %d 器件, foundry=%s (%s)",
            platform_name,
            foundry_info["process_node"],
            device_count,
            foundry_info["foundry"],
            foundry_info["foundry_url"],
        )
        for dev in representative:
            _logger.info(
                "  代表器件 %s（%s）: %s — 来源: %s",
                dev["name"],
                dev["type"],
                dev["params"],
                dev["source"],
            )

    _logger.info("四平台器件总数: %d", total_count)

    return {
        "platforms": platforms,
        "total_device_count": total_count,
        "representative_devices": all_representative,
    }
