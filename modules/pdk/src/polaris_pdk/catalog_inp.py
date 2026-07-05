"""PDK 器件目录 - InP 平台（Pattern Project / JEPPIX, InP generic）（polaris-pdk 子模块）。

从 ``catalog.py`` 拆分而来，包含 InP 平台的 9 个代表性器件。
每个器件的电光参数均来自公开文献/工艺手册并附带来源标注（R02 学术诚信，
禁止假数据）。

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU（纯数据结构）。
"""

from __future__ import annotations

from typing import Any

from .catalog_common import _src

# InP 平台 9 器件
DEVICES_INP: list[dict[str, Any]] = [
    {
        "platform": "InP",
        "device_type": "inp_waveguide",
        "name": "InP Active Waveguide",
        "category": "passive",
        "foundry": "Pattern Project / Fraunhofer HHI",
        "process_node": "InP generic",
        "params": {
            "width_um": 2.0,
            "loss_db_cm": 2.0,  # InP 有源波导 ~2 dB/cm
            "wavelength_nm": 1550,
            "pdk_reference": "Pattern_Project_InP_PDK",
        },
        "source": _src("InP-Based Foundry PICs for Optical Interconnects",
                       "Soares et al.", 2019,
                       "https://doi.org/10.3390/app9081588"),
        "ports": [("in", 0.0, 0.0, "west"), ("out", 10.0, 0.0, "east")],
        "bbox_um": {"xmin": 0.0, "ymin": -1.0, "xmax": 10.0, "ymax": 1.0},
    },
    {
        "platform": "InP",
        "device_type": "eam_modulator",
        "name": "EAM Modulator",
        "category": "active",
        "foundry": "Pattern Project / Fraunhofer HHI",
        "process_node": "InP generic",
        "params": {
            "bandwidth_ghz": 45.0,  # EAM 带宽 ~45GHz
            "length_um": 200.0,
            "wavelength_nm": 1550,
            "pdk_reference": "Pattern_Project_InP_PDK",
        },
        "source": _src("InP-Based Foundry PICs for Optical Interconnects",
                       "Soares et al.", 2019,
                       "https://doi.org/10.3390/app9081588"),
        "ports": [("in", 0.0, 0.0, "west"), ("out", 200.0, 0.0, "east"),
                  ("rf_in", 100.0, 3.0, "south")],
        "bbox_um": {"xmin": 0.0, "ymin": -1.0, "xmax": 200.0, "ymax": 3.0},
    },
    {
        "platform": "InP",
        "device_type": "inp_photodetector",
        "name": "InP Photodetector",
        "category": "detector",
        "foundry": "Pattern Project / Fraunhofer HHI",
        "process_node": "InP generic",
        "params": {
            "responsivity_a_w": 0.8,  # InP PD 响应率 >0.8 A/W
            "bandwidth_ghz": 60.0,
            "dark_current_na": 5.0,
            "wavelength_nm": 1550,
            "pdk_reference": "Pattern_Project_InP_PDK",
        },
        "source": _src("InP-Based Foundry PICs for Optical Interconnects",
                       "Soares et al.", 2019,
                       "https://doi.org/10.3390/app9081588"),
        "ports": [("in", 0.0, 0.0, "west"), ("rf_out", 10.0, 3.0, "south")],
        "bbox_um": {"xmin": 0.0, "ymin": -1.0, "xmax": 10.0, "ymax": 3.0},
    },
    {
        "platform": "InP",
        "device_type": "soa",
        "name": "Semiconductor Optical Amplifier",
        "category": "active",
        "foundry": "Pattern Project / Fraunhofer HHI",
        "process_node": "InP generic",
        "params": {
            "gain_db": 20.0,  # SOA 增益 ~20dB
            "gain_db_per_100um": 4.0,  # ~4dB/100μm
            "length_um": 500.0,
            "wavelength_nm": 1550,
            "pdk_reference": "Pattern_Project_InP_PDK",
        },
        "source": _src("InP-Based Foundry PICs for Optical Interconnects",
                       "Soares et al.", 2019,
                       "https://doi.org/10.3390/app9081588"),
        "ports": [("in", 0.0, 0.0, "west"), ("out", 500.0, 0.0, "east")],
        "bbox_um": {"xmin": 0.0, "ymin": -1.0, "xmax": 500.0, "ymax": 1.0},
    },
    {
        "platform": "InP",
        "device_type": "dfb_laser",
        "name": "DFB Laser",
        "category": "source",
        "foundry": "Pattern Project / Fraunhofer HHI",
        "process_node": "InP generic",
        "params": {
            "output_power_mw": 3.0,  # DFB 输出功率 >3mW
            "smsr_db": 40.0,
            "wavelength_nm": 1550,
            "pdk_reference": "Pattern_Project_InP_PDK",
        },
        "source": _src("InP-Based Foundry PICs for Optical Interconnects",
                       "Soares et al.", 2019,
                       "https://doi.org/10.3390/app9081588"),
        "ports": [("out", 0.0, 0.0, "east")],
        "bbox_um": {"xmin": 0.0, "ymin": -1.0, "xmax": 400.0, "ymax": 1.0},
    },
    {
        "platform": "InP",
        "device_type": "dbr_laser",
        "name": "DBR Laser",
        "category": "source",
        "foundry": "Pattern Project / UCSB",
        "process_node": "InP generic",
        "params": {
            "output_power_mw": 3.0,
            "smsr_db": 35.0,
            "tuning_range_nm": 5.0,
            "wavelength_nm": 1550,
            "pdk_reference": "Pattern_Project_InP_PDK",
        },
        "source": _src("InP Photonic Integrated Circuits for Free Space Optical Links",
                       "Zhao et al.", 2018,
                       "https://doi.org/10.1109/JSTQE.2018.2866565"),
        "ports": [("out", 0.0, 0.0, "east")],
        "bbox_um": {"xmin": 0.0, "ymin": -1.0, "xmax": 600.0, "ymax": 1.0},
    },
    {
        "platform": "InP",
        "device_type": "sgdbr_laser",
        "name": "SGDBR Laser",
        "category": "source",
        "foundry": "Pattern Project / UCSB",
        "process_node": "InP generic",
        "params": {
            "output_power_mw": 2.0,
            "smsr_db": 45.0,
            "tuning_range_nm": 44.0,  # SGDBR 调谐 1521-1565nm
            "wavelength_nm": 1550,
            "pdk_reference": "Pattern_Project_InP_PDK",
        },
        "source": _src("InP Photonic Integrated Circuits for Free Space Optical Links",
                       "Zhao et al.", 2018,
                       "https://doi.org/10.1109/JSTQE.2018.2866565"),
        "ports": [("out", 0.0, 0.0, "east")],
        "bbox_um": {"xmin": 0.0, "ymin": -1.0, "xmax": 800.0, "ymax": 1.0},
    },
    {
        "platform": "InP",
        "device_type": "inp_mzm",
        "name": "InP Mach-Zehnder Modulator",
        "category": "active",
        "foundry": "Pattern Project / UCSB",
        "process_node": "InP generic",
        "params": {
            "vpi_v": 3.0,  # InP MZM Vπ ~3V
            "bandwidth_ghz": 40.0,
            "length_um": 1000.0,
            "wavelength_nm": 1550,
            "pdk_reference": "Pattern_Project_InP_PDK",
        },
        "source": _src("InP Photonic Integrated Circuits for Free Space Optical Links",
                       "Zhao et al.", 2018,
                       "https://doi.org/10.1109/JSTQE.2018.2866565"),
        "ports": [("in", 0.0, 0.0, "west"), ("out", 1000.0, 0.0, "east"),
                  ("rf_in", 500.0, 3.0, "south")],
        "bbox_um": {"xmin": 0.0, "ymin": -1.0, "xmax": 1000.0, "ymax": 3.0},
    },
    {
        "platform": "InP",
        "device_type": "soa_high_power",
        "name": "High-Power SOA",
        "category": "active",
        "foundry": "Pattern Project / SemiNex",
        "process_node": "InP generic",
        "params": {
            "output_power_mw": 1000.0,  # 高功率 SOA >1W 输出
            "gain_db": 30.0,
            "pce_percent": 25.0,  # 功率转换效率 ~25%@25°C
            "length_um": 2000.0,
            "wavelength_nm": 1550,
            "pdk_reference": "Pattern_Project_InP_PDK",
        },
        "source": _src("SemiNex high-power InP SOA",
                       "SemiNex", 2024, "https://www.aptechnologies.co.uk/news"),
        "ports": [("in", 0.0, 0.0, "west"), ("out", 2000.0, 0.0, "east")],
        "bbox_um": {"xmin": 0.0, "ymin": -1.0, "xmax": 2000.0, "ymax": 1.0},
    },
]

__all__ = [f"DEVICES_INP"]
