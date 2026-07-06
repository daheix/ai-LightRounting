"""PDK 器件目录 - SOI 平台（SiEPIC EBeam PDK, 220nm SOI）（polaris-pdk 子模块）。

从 ``catalog.py`` 拆分而来，包含 SOI 平台的 9 个代表性器件。
每个器件的电光参数均来自公开文献/工艺手册并附带来源标注（R02 学术诚信，
禁止假数据）。

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU（纯数据结构）。

文献来源（R02 学术诚信，≥5 个 URL）:
- SiEPIC EBeam PDK (220nm SOI) https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- Chrostowski & Hochberg, "Silicon Photonics Design", CUP 2015
  https://www.cambridge.org/core/books/silicon-photonics-design/
- gdsfactory PDK 框架 https://github.com/gdsfactory/gdsfactory
- AIM Photonics (US AIM) https://www.aimphotonics.com/
- Luceda IPKISS https://www.lucedaphotonics.com/
- AMF (Advanced Micro Foundry) https://www.advancedmicrofoundry.com/
"""

from __future__ import annotations

from typing import Any

from .catalog_common import _src

# SOI 平台 9 器件
DEVICES_SOI: list[dict[str, Any]] = [
    {
        "platform": "SOI",
        "device_type": "strip_waveguide",
        "name": "Strip Waveguide",
        "category": "passive",
        "foundry": "SiEPIC",
        "process_node": "220nm SOI",
        "params": {
            "width_um": 0.5, "height_um": 0.22,
            "loss_db_cm": 2.0,  # SiEPIC 典型 2-3 dB/cm
            "wavelength_nm": 1550,
            "pdk_reference": "SiEPIC_EBeam_PDK",
        },
        "source": _src("SiEPIC EBeam PDK strip waveguide",
                       "SiEPIC", 2024,
                       "https://github.com/SiEPIC/SiEPIC_EBeam_PDK"),
        "ports": [("in", 0.0, 0.0, "west"), ("out", 10.0, 0.0, "east")],
        "bbox_um": {"xmin": 0.0, "ymin": -0.25, "xmax": 10.0, "ymax": 0.25},
    },
    {
        "platform": "SOI",
        "device_type": "grating_coupler",
        "name": "Grating Coupler (1D Si)",
        "category": "passive",
        "foundry": "SiEPIC / Samsung 300mm",
        "process_node": "220nm SOI",
        "params": {
            # 三星 300mm 平台峰值耦合损耗 1.9dB（OFC 2026）
            "insertion_loss_db": 1.9,
            "siepic_typical_loss_db": 4.1,  # SiEPIC EBeam GC 典型 3-5 dB
            "bandwidth_1db_nm": 27,
            "wavelength_nm": 1550,
            "polarization": "TE",
            "pdk_reference": "SiEPIC_EBeam_PDK",
        },
        "source": _src("三星 300mm 硅光平台 OFC 2026 + SiEPIC EBeam PDK",
                       "Samsung / SiEPIC", 2026,
                       "https://cloud.tencent.com.cn/developer/article/2650050"),
        "ports": [("wg", 0.0, 0.0, "west")],
        "bbox_um": {"xmin": 0.0, "ymin": -6.0, "xmax": 20.0, "ymax": 6.0},
    },
    {
        "platform": "SOI",
        "device_type": "y_branch",
        "name": "Y Branch",
        "category": "passive",
        "foundry": "SiEPIC",
        "process_node": "220nm SOI",
        "params": {
            "insertion_loss_db": 0.3,  # SiEPIC Y 分支插损 <0.3dB
            "imbalance_db": 0.1,
            "wavelength_nm": 1550,
            "pdk_reference": "SiEPIC_EBeam_PDK",
        },
        "source": _src("SiEPIC EBeam PDK Y branch",
                       "SiEPIC", 2024,
                       "https://github.com/SiEPIC/SiEPIC_EBeam_PDK"),
        "ports": [("in", 0.0, 0.0, "west"),
                  ("out1", 10.0, 0.5, "east"), ("out2", 10.0, -0.5, "east")],
        "bbox_um": {"xmin": 0.0, "ymin": -1.0, "xmax": 10.0, "ymax": 1.0},
    },
    {
        "platform": "SOI",
        "device_type": "mmi_1x2",
        "name": "MMI 1x2",
        "category": "passive",
        "foundry": "SiEPIC",
        "process_node": "220nm SOI",
        "params": {
            "insertion_loss_db": 0.4,  # 插损 <0.5dB
            "imbalance_db": 0.2,
            "mmi_length_um": 10.0, "mmi_width_um": 3.0,
            "wavelength_nm": 1550,
            "pdk_reference": "SiEPIC_EBeam_PDK",
        },
        "source": _src("硅光工艺平台比较（iccsz.com）",
                       "iccsz", 2019,
                       "http://www.iccsz.com/site/cn/News/2019/05/18/20190518033317178663.htm"),
        "ports": [("in", 0.0, 0.0, "west"),
                  ("out1", 10.0, 0.5, "east"), ("out2", 10.0, -0.5, "east")],
        "bbox_um": {"xmin": 0.0, "ymin": -1.5, "xmax": 10.0, "ymax": 1.5},
    },
    {
        "platform": "SOI",
        "device_type": "ring_resonator",
        "name": "Ring Resonator",
        "category": "passive",
        "foundry": "SiEPIC",
        "process_node": "220nm SOI",
        "params": {
            "radius_um": 10.0,
            "q_factor": 10000.0,  # SiEPIC 典型 Q ~1e4
            "fsr_nm": 10.0,
            "wavelength_nm": 1550,
            "pdk_reference": "SiEPIC_EBeam_PDK",
        },
        "source": _src("SiEPIC EBeam PDK ring resonator",
                       "SiEPIC", 2024,
                       "https://github.com/SiEPIC/SiEPIC_EBeam_PDK"),
        "ports": [("in", 0.0, 0.0, "west"), ("through", 10.0, 0.0, "east"),
                  ("drop", 10.0, -20.0, "south")],
        "bbox_um": {"xmin": 0.0, "ymin": -20.0, "xmax": 20.0, "ymax": 0.0},
    },
    {
        "platform": "SOI",
        "device_type": "directional_coupler",
        "name": "Directional Coupler",
        "category": "passive",
        "foundry": "SiEPIC",
        "process_node": "220nm SOI",
        "params": {
            "gap_nm": 200,  # SiEPIC 默认耦合间隙 200nm
            "coupling_length_um": 10.0,
            "coupling_ratio": 0.5,  # 3dB 耦合
            "loss_db": 0.2,
            "wavelength_nm": 1550,
            "pdk_reference": "SiEPIC_EBeam_PDK",
        },
        "source": _src("SiEPIC EBeam PDK directional coupler",
                       "SiEPIC", 2024,
                       "https://github.com/SiEPIC/SiEPIC_EBeam_PDK"),
        "ports": [("in1", 0.0, 0.25, "west"), ("in2", 0.0, -0.25, "west"),
                  ("out1", 10.0, 0.25, "east"), ("out2", 10.0, -0.25, "east")],
        "bbox_um": {"xmin": 0.0, "ymin": -0.75, "xmax": 10.0, "ymax": 0.75},
    },
    {
        "platform": "SOI",
        "device_type": "mzi",
        "name": "Mach-Zehnder Interferometer",
        "category": "passive",
        "foundry": "SiEPIC / AIM",
        "process_node": "220nm SOI",
        "params": {
            "arm_length_um": 100.0,
            "arm_gap_um": 2.0,
            "insertion_loss_db": 1.0,
            "fsr_nm": 10.0,
            "wavelength_nm": 1550,
            "pdk_reference": "SiEPIC_EBeam_PDK",
        },
        "source": _src("AIM Photonics 无源硅基光电子芯片元件教程",
                       "AIM Photonics", 2024,
                       "https://www.latitudeda.com/document/716"),
        "ports": [("in1", 0.0, 1.0, "west"), ("in2", 0.0, -1.0, "west"),
                  ("out1", 120.0, 1.0, "east"), ("out2", 120.0, -1.0, "east")],
        "bbox_um": {"xmin": 0.0, "ymin": -1.25, "xmax": 120.0, "ymax": 1.25},
    },
    {
        "platform": "SOI",
        "device_type": "thermo_optic_phase_shifter",
        "name": "Thermo-Optic Phase Shifter",
        "category": "active",
        "foundry": "SiEPIC",
        "process_node": "220nm SOI",
        "params": {
            "pi_power_mw": 20.0,  # SiEPIC 热光移相器 Pπ ~20mW
            "length_um": 100.0,
            "loss_db": 0.5,
            "wavelength_nm": 1550,
            "pdk_reference": "SiEPIC_EBeam_PDK",
        },
        "source": _src("SiEPIC EBeam PDK thermo-optic phase shifter",
                       "SiEPIC", 2024,
                       "https://github.com/SiEPIC/SiEPIC_EBeam_PDK"),
        "ports": [("in", 0.0, 0.0, "west"), ("out", 100.0, 0.0, "east"),
                  ("rf_in", 50.0, 2.0, "south")],
        "bbox_um": {"xmin": 0.0, "ymin": -0.25, "xmax": 100.0, "ymax": 2.0},
    },
    {
        "platform": "SOI",
        "device_type": "ge_photodetector",
        "name": "Ge Photodetector",
        "category": "detector",
        "foundry": "SiEPIC / AIM",
        "process_node": "220nm SOI",
        "params": {
            "responsivity_a_w": 0.8,  # Ge PD 响应率 >0.8 A/W
            "bandwidth_ghz": 40.0,
            "dark_current_na": 10.0,
            "wavelength_nm": 1550,
            "pdk_reference": "SiEPIC_EBeam_PDK",
        },
        "source": _src("AIM Photonics Ge photodetector",
                       "AIM Photonics", 2024,
                       "https://www.latitudeda.com/document/716"),
        "ports": [("in", 0.0, 0.0, "west"), ("rf_out", 10.0, 2.0, "south")],
        "bbox_um": {"xmin": 0.0, "ymin": -2.0, "xmax": 10.0, "ymax": 2.0},
    },
]

__all__ = [f"DEVICES_SOI"]
