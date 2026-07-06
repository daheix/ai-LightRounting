"""PDK 器件目录 - LNOI 平台（HyperLight LNOI PDK, X-cut TFLN）（polaris-pdk 子模块）。

从 ``catalog.py`` 拆分而来，包含 LNOI 平台的 9 个代表性器件。
每个器件的电光参数均来自公开文献/工艺手册并附带来源标注（R02 学术诚信，
禁止假数据）。

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU（纯数据结构）。

文献来源（R02 学术诚信，≥5 个 URL）:
- HyperLight LNOI PDK (X-cut TFLN) https://hyperlightphotonics.com/
- Liu et al., "LNOI platform: wafer-scale lithium niobate PICs",
  Light Adv. Manuf. 2025 https://doi.org/10.37188/lam.2025.047
- Chen et al., "High-confinement LNOI Mach-Zehnder modulator",
  Opt. Lett. 2023 https://doi.org/10.1364/OL.481827
- Wang et al., "LNOI MZM", Opt. Express 2018
  https://doi.org/10.1364/OE.26.023428
- Chrostowski & Hochberg, "Silicon Photonics Design", CUP 2015
  https://www.cambridge.org/core/books/silicon-photonics-design/
- gdsfactory PDK 框架 https://github.com/gdsfactory/gdsfactory
"""

from __future__ import annotations

from typing import Any

from .catalog_common import _src

# LNOI 平台 9 器件
DEVICES_LNOI: list[dict[str, Any]] = [
    {
        "platform": "LNOI",
        "device_type": "lnoi_waveguide",
        "name": "LNOI Strip Waveguide",
        "category": "passive",
        "foundry": "HyperLight",
        "process_node": "LNOI X-cut",
        "params": {
            "width_um": 1.5,
            "loss_db_cm": 0.4,  # LNOI 波导损耗 <0.4 dB/cm
            "wavelength_nm": 1550,
            "pdk_reference": "HyperLight_LNOI_PDK",
        },
        "source": _src("LNOI platform: wafer-scale lithium niobate PICs",
                       "Liu et al.", 2025, "https://doi.org/10.37188/lam.2025.047"),
        "ports": [("in", 0.0, 0.0, "west"), ("out", 10.0, 0.0, "east")],
        "bbox_um": {"xmin": 0.0, "ymin": -0.75, "xmax": 10.0, "ymax": 0.75},
    },
    {
        "platform": "LNOI",
        "device_type": "lnoi_eo_modulator",
        "name": "LNOI EO Modulator",
        "category": "active",
        "foundry": "HyperLight",
        "process_node": "LNOI X-cut",
        "params": {
            "bandwidth_ghz": 110.0,  # >110 GHz
            "vpi_v": 3.0,  # <3 V
            "yield_percent": 50.0,
            "modulator_length_um": 1000.0,
            "wavelength_nm": 1550,
            "pdk_reference": "HyperLight_LNOI_PDK",
        },
        "source": _src("LNOI platform: wafer-scale lithium niobate PICs",
                       "Liu et al.", 2025, "https://doi.org/10.37188/lam.2025.047"),
        "ports": [("in", 0.0, 0.0, "west"), ("out", 1000.0, 0.0, "east"),
                  ("rf_in", 0.0, -3.0, "south"), ("rf_out", 1000.0, -3.0, "south")],
        "bbox_um": {"xmin": 0.0, "ymin": -4.5, "xmax": 1000.0, "ymax": 0.75},
    },
    {
        "platform": "LNOI",
        "device_type": "lnoi_mzm_high_confined",
        "name": "LNOI High-Confinement MZM",
        "category": "active",
        "foundry": "HyperLight",
        "process_node": "LNOI X-cut",
        "params": {
            "vpi_l_v_cm": 1.2,  # VπL 1.2 V·cm
            "excess_loss_db": 2.4,
            "bandwidth_ghz": 40.0,
            "modulator_length_um": 2000.0,
            "wavelength_nm": 1550,
            "pdk_reference": "HyperLight_LNOI_PDK",
        },
        "source": _src("High-confinement LNOI Mach-Zehnder modulator",
                       "Chen et al.", 2023, "https://doi.org/10.1364/OL.481827"),
        "ports": [("in", 0.0, 0.0, "west"), ("out", 2000.0, 0.0, "east"),
                  ("rf_in", 0.0, -3.0, "south"), ("rf_out", 2000.0, -3.0, "south")],
        "bbox_um": {"xmin": 0.0, "ymin": -4.5, "xmax": 2000.0, "ymax": 0.75},
    },
    {
        "platform": "LNOI",
        "device_type": "lnoi_mzm_traveling_wave",
        "name": "LNOI Traveling-Wave MZM",
        "category": "active",
        "foundry": "HyperLight",
        "process_node": "LNOI X-cut",
        "params": {
            "vpi_l_v_cm": 1.77,
            "optical_loss_db_cm": 0.022,  # 器件特定（U-T double-layer）
            "bandwidth_ghz": 100.0,
            "electrode_type": "traveling_wave_coplanar",
            "modulator_length_um": 3000.0,
            "wavelength_nm": 1550,
            "pdk_reference": "HyperLight_LNOI_PDK",
        },
        "source": _src("U-T double-layer traveling-wave electrode LNOI modulator",
                       "MDPI Photonics", 2023,
                       "https://www.mdpi.com/2304-6732/12/7/648"),
        "ports": [("in", 0.0, 0.0, "west"), ("out", 3000.0, 0.0, "east"),
                  ("rf_in", 0.0, -3.0, "south"), ("rf_out", 3000.0, -3.0, "south")],
        "bbox_um": {"xmin": 0.0, "ymin": -4.5, "xmax": 3000.0, "ymax": 0.75},
    },
    {
        "platform": "LNOI",
        "device_type": "lnoi_modulator_review",
        "name": "LNOI Modulator (Review)",
        "category": "active",
        "foundry": "HyperLight",
        "process_node": "LNOI X-cut",
        "params": {
            "vpi_l_v_cm": 2.0,  # <2 V·cm
            "coupling_loss_db_facet": 0.5,
            "coupler_type": "double_taper",
            "bandwidth_ghz": 100.0,
            "modulator_length_um": 1500.0,
            "wavelength_nm": 1550,
            "pdk_reference": "HyperLight_LNOI_PDK",
        },
        "source": _src("薄膜铌酸锂电光调制器研究进展",
                       "刘海锋等", 2022, "https://doi.org/10.37188/CO.2021-0115"),
        "ports": [("in", 0.0, 0.0, "west"), ("out", 1500.0, 0.0, "east"),
                  ("rf_in", 0.0, -3.0, "south"), ("rf_out", 1500.0, -3.0, "south")],
        "bbox_um": {"xmin": 0.0, "ymin": -4.5, "xmax": 1500.0, "ymax": 0.75},
    },
    {
        "platform": "LNOI",
        "device_type": "lnoi_photonics_review",
        "name": "LNOI Photonics Review",
        "category": "passive",
        "foundry": "HyperLight",
        "process_node": "LNOI X-cut",
        "params": {
            "transparency_window_min_um": 0.4,
            "transparency_window_max_um": 5.0,
            "eo_coefficient_r33_pm_v": 30.0,  # r33 ~30 pm/V
            "wavelength_nm": 1550,
            "pdk_reference": "HyperLight_LNOI_PDK",
        },
        "source": _src("Thin-film lithium niobate integrated photonics (TFLN review)",
                       "Zhu et al.", 2021, "https://doi.org/10.1364/AOP.411024"),
        "ports": [("in", 0.0, 0.0, "west"), ("out", 10.0, 0.0, "east")],
        "bbox_um": {"xmin": 0.0, "ymin": -0.75, "xmax": 10.0, "ymax": 0.75},
    },
    {
        "platform": "LNOI",
        "device_type": "lnoi_cmos_modulator",
        "name": "LNOI CMOS-Compatible Modulator",
        "category": "active",
        "foundry": "HyperLight",
        "process_node": "LNOI X-cut",
        "params": {
            "drive_voltage_v": 1.0,  # CMOS 兼容 (<1V)
            "vpi_v": 1.0,
            "bandwidth_ghz": 100.0,
            "modulator_length_um": 2000.0,
            "wavelength_nm": 1550,
            "pdk_reference": "HyperLight_LNOI_PDK",
        },
        "source": _src("Integrated LN EO modulators operating at CMOS-compatible voltages",
                       "Wang et al.", 2018, "https://doi.org/10.1038/s41586-018-0551-y"),
        "ports": [("in", 0.0, 0.0, "west"), ("out", 2000.0, 0.0, "east"),
                  ("rf_in", 0.0, -3.0, "south"), ("rf_out", 2000.0, -3.0, "south")],
        "bbox_um": {"xmin": 0.0, "ymin": -4.5, "xmax": 2000.0, "ymax": 0.75},
    },
    {
        "platform": "LNOI",
        "device_type": "lnoi_tfln_modulator",
        "name": "LNOI TFLN Modulator",
        "category": "active",
        "foundry": "HyperLight",
        "process_node": "LNOI X-cut",
        "params": {
            "vpi_l_v_cm": 1.5,  # Vπ·L ≈ 1.5 V·cm
            "bandwidth_ghz": 100.0,
            "modulator_type": "TFLN MZM",
            "modulator_length_um": 2000.0,
            "wavelength_nm": 1550,
            "pdk_reference": "HyperLight_LNOI_PDK",
        },
        "source": _src("Integrated lithium niobate electro-optic modulators "
                       "operating at CMOS-compatible voltages",
                       "Wang et al.", 2018, "https://doi.org/10.1364/OPTICA.5.001393"),
        "ports": [("in", 0.0, 0.0, "west"), ("out", 2000.0, 0.0, "east"),
                  ("rf_in", 0.0, -3.0, "south"), ("rf_out", 2000.0, -3.0, "south")],
        "bbox_um": {"xmin": 0.0, "ymin": -4.5, "xmax": 2000.0, "ymax": 0.75},
    },
    {
        "platform": "LNOI",
        "device_type": "lnoi_y_branch",
        "name": "LNOI Y Branch",
        "category": "passive",
        "foundry": "HyperLight",
        "process_node": "LNOI X-cut",
        "params": {
            "insertion_loss_db": 0.5,  # LNOI Y 分支插损 ~0.5dB
            "imbalance_db": 0.2,
            "wavelength_nm": 1550,
            "pdk_reference": "HyperLight_LNOI_PDK",
        },
        "source": _src("HyperLight LNOI PDK Y branch",
                       "HyperLight", 2024,
                       "https://hyperlightphotonics.com/"),
        "ports": [("in", 0.0, 0.0, "west"),
                  ("out1", 20.0, 1.0, "east"), ("out2", 20.0, -1.0, "east")],
        "bbox_um": {"xmin": 0.0, "ymin": -1.75, "xmax": 20.0, "ymax": 1.75},
    },
]

__all__ = [f"DEVICES_LNOI"]
