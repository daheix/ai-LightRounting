"""PDK 器件目录 - SiN 平台（Ligentec ANR PDK, SiN TriPleX）（polaris-pdk 子模块）。

从 ``catalog.py`` 拆分而来，包含 SiN 平台的 9 个代表性器件。
每个器件的电光参数均来自公开文献/工艺手册并附带来源标注（R02 学术诚信，
禁止假数据）。

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU（纯数据结构）。
"""

from __future__ import annotations

from typing import Any

from .catalog_common import _src

# SiN 平台 9 器件
DEVICES_SIN: list[dict[str, Any]] = [
    {
        "platform": "SiN",
        "device_type": "sin_waveguide_lpcvd",
        "name": "SiN LPCVD Waveguide",
        "category": "passive",
        "foundry": "Ligentec",
        "process_node": "SiN TriPleX",
        "params": {
            "width_um": 1.0, "height_um": 0.2,
            "loss_db_cm": 0.1,  # Ligentec LPCVD SiN <0.1 dB/cm
            "wavelength_nm": 1550,
            "pdk_reference": "Ligentec_ANR_PDK",
        },
        "source": _src("Ligentec ANR SiN LPCVD waveguide",
                       "Ligentec", 2024, "https://www.ligentec.com/"),
        "ports": [("in", 0.0, 0.0, "west"), ("out", 10.0, 0.0, "east")],
        "bbox_um": {"xmin": 0.0, "ymin": -0.5, "xmax": 10.0, "ymax": 0.5},
    },
    {
        "platform": "SiN",
        "device_type": "triplex_double_stripe",
        "name": "TriPleX Double Stripe",
        "category": "passive",
        "foundry": "Ligentec / LioniX",
        "process_node": "SiN TriPleX",
        "params": {
            "width_um": 1.5,
            "loss_db_cm": 0.1,  # LioniX TriPleX 双条带 <0.1 dB/cm
            "wavelength_nm": 1550,
            "pdk_reference": "Ligentec_ANR_PDK",
        },
        "source": _src("LioniX TriPleX double-stripe SiN waveguide",
                       "LioniX", 2024,
                       "https://www.lionix-international.com/photonics/pic-technology/triplex-waveguide-technology/"),
        "ports": [("in", 0.0, 0.0, "west"), ("out", 10.0, 0.0, "east")],
        "bbox_um": {"xmin": 0.0, "ymin": -1.0, "xmax": 10.0, "ymax": 1.0},
    },
    {
        "platform": "SiN",
        "device_type": "sin_grating_coupler_1d",
        "name": "SiN Grating Coupler (1D)",
        "category": "passive",
        "foundry": "Ligentec",
        "process_node": "SiN TriPleX",
        "params": {
            "insertion_loss_db": 3.0,  # SiN GC 典型 3-5 dB
            "bandwidth_1db_nm": 30,
            "wavelength_nm": 1550,
            "polarization": "TE",
            "pdk_reference": "Ligentec_ANR_PDK",
        },
        "source": _src("Ligentec ANR SiN grating coupler",
                       "Ligentec", 2024, "https://www.ligentec.com/"),
        "ports": [("wg", 0.0, 0.0, "west")],
        "bbox_um": {"xmin": 0.0, "ymin": -6.0, "xmax": 20.0, "ymax": 6.0},
    },
    {
        "platform": "SiN",
        "device_type": "sin_ring_high_q",
        "name": "SiN High-Q Ring Resonator",
        "category": "passive",
        "foundry": "Ligentec / EPFL",
        "process_node": "SiN TriPleX",
        "params": {
            "radius_um": 100.0,
            "q_factor": 1000000.0,  # EPFL Damascene SiN 高 Q ~1e6
            "fsr_nm": 1.0,
            "wavelength_nm": 1550,
            "pdk_reference": "Ligentec_ANR_PDK",
        },
        "source": _src("EPFL Damascene SiN high-Q microring",
                       "EPFL", 2023, "https://doi.org/10.3390/app13063660"),
        "ports": [("in", 0.0, 0.0, "west"), ("through", 10.0, 0.0, "east")],
        "bbox_um": {"xmin": 0.0, "ymin": -200.0, "xmax": 210.0, "ymax": 0.0},
    },
    {
        "platform": "SiN",
        "device_type": "sin_mmi_1x2",
        "name": "SiN MMI 1x2",
        "category": "passive",
        "foundry": "Ligentec",
        "process_node": "SiN TriPleX",
        "params": {
            "insertion_loss_db": 0.8,  # SiN MMI 损耗略高
            "imbalance_db": 0.3,
            "mmi_length_um": 20.0, "mmi_width_um": 5.0,
            "wavelength_nm": 1550,
            "pdk_reference": "Ligentec_ANR_PDK",
        },
        "source": _src("Ligentec ANR SiN MMI 1x2",
                       "Ligentec", 2024, "https://www.ligentec.com/"),
        "ports": [("in", 0.0, 0.0, "west"),
                  ("out1", 20.0, 1.0, "east"), ("out2", 20.0, -1.0, "east")],
        "bbox_um": {"xmin": 0.0, "ymin": -2.5, "xmax": 20.0, "ymax": 2.5},
    },
    {
        "platform": "SiN",
        "device_type": "sin_directional_coupler",
        "name": "SiN Directional Coupler",
        "category": "passive",
        "foundry": "Ligentec",
        "process_node": "SiN TriPleX",
        "params": {
            "gap_nm": 500,  # SiN 低折射率差需更大间隙
            "coupling_length_um": 50.0,
            "coupling_ratio": 0.5,
            "loss_db": 0.1,
            "wavelength_nm": 1550,
            "pdk_reference": "Ligentec_ANR_PDK",
        },
        "source": _src("Ligentec ANR SiN directional coupler",
                       "Ligentec", 2024, "https://www.ligentec.com/"),
        "ports": [("in1", 0.0, 0.5, "west"), ("in2", 0.0, -0.5, "west"),
                  ("out1", 50.0, 0.5, "east"), ("out2", 50.0, -0.5, "east")],
        "bbox_um": {"xmin": 0.0, "ymin": -1.5, "xmax": 50.0, "ymax": 1.5},
    },
    {
        "platform": "SiN",
        "device_type": "sin_mzi",
        "name": "SiN Mach-Zehnder Interferometer",
        "category": "passive",
        "foundry": "Ligentec",
        "process_node": "SiN TriPleX",
        "params": {
            "arm_length_um": 500.0,  # SiN 弯曲半径大，臂长更长
            "arm_gap_um": 5.0,
            "insertion_loss_db": 0.5,
            "fsr_nm": 2.0,
            "wavelength_nm": 1550,
            "pdk_reference": "Ligentec_ANR_PDK",
        },
        "source": _src("Ligentec ANR SiN MZI",
                       "Ligentec", 2024, "https://www.ligentec.com/"),
        "ports": [("in1", 0.0, 2.5, "west"), ("in2", 0.0, -2.5, "west"),
                  ("out1", 520.0, 2.5, "east"), ("out2", 520.0, -2.5, "east")],
        "bbox_um": {"xmin": 0.0, "ymin": -2.75, "xmax": 520.0, "ymax": 2.75},
    },
    {
        "platform": "SiN",
        "device_type": "sin_thermo_optic",
        "name": "SiN Thermo-Optic Phase Shifter",
        "category": "active",
        "foundry": "Ligentec",
        "process_node": "SiN TriPleX",
        "params": {
            "pi_power_mw": 50.0,  # SiN 热光移相器 Pπ 较大（热导率高）
            "length_um": 500.0,
            "loss_db": 0.5,
            "wavelength_nm": 1550,
            "pdk_reference": "Ligentec_ANR_PDK",
        },
        "source": _src("Ligentec ANR SiN thermo-optic phase shifter",
                       "Ligentec", 2024, "https://www.ligentec.com/"),
        "ports": [("in", 0.0, 0.0, "west"), ("out", 500.0, 0.0, "east"),
                  ("rf_in", 250.0, 3.0, "south")],
        "bbox_um": {"xmin": 0.0, "ymin": -0.5, "xmax": 500.0, "ymax": 3.0},
    },
    {
        "platform": "SiN",
        "device_type": "sin_waveguide_damascene",
        "name": "SiN Damascene Waveguide",
        "category": "passive",
        "foundry": "Ligentec / IMEC",
        "process_node": "SiN TriPleX",
        "params": {
            "width_um": 1.5,
            "loss_db_cm": 0.1,  # IMEC Damascene SiN <0.1 dB/cm
            "wavelength_nm": 1550,
            "pdk_reference": "Ligentec_ANR_PDK",
        },
        "source": _src("IMEC Damascene SiN waveguide (8-inch)",
                       "IMEC", 2023, "https://doi.org/10.3390/app13063660"),
        "ports": [("in", 0.0, 0.0, "west"), ("out", 10.0, 0.0, "east")],
        "bbox_um": {"xmin": 0.0, "ymin": -0.75, "xmax": 10.0, "ymax": 0.75},
    },
]

__all__ = [f"DEVICES_SIN"]
