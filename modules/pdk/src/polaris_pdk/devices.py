"""PDK 器件数据定义（polaris-pdk 子模块，数据层）。

从 catalog.py 拆分而来（R11 质量门禁：文件 ≤800 行）。本文件仅包含
4 平台 36 器件的纯数据结构（list[dict]），不含查询逻辑。

详细文献溯源与平台 foundry 来源标注见 ``catalog.py`` 模块 docstring
（R02 学术诚信）。

文献来源（R02 学术诚信，≥5 个 URL）:
1. SiEPIC EBeam PDK (UBC, Lukas Chrostowski), 220nm SOI 工艺,
   https://github.com/SiEPIC/SiEPIC_EBeam_PDK
2. Ligentec ANR PDK, SiN TriPleX 平台, https://www.ligentec.com/
3. JePPIX / Pattern Project InP generic 平台, https://www.jeppix.eu/
4. HyperLight LNOI X-cut 平台, https://hyperlightphotonics.com/
5. Chrostowski & Hochberg, "Silicon Photonics Design", CUP 2015,
   https://www.cambridge.org/core/books/photonic-electronics/
6. gdsfactory (open-source photonics PDK framework),
   https://github.com/gdsfactory/gdsfactory

合规: R02 / R03 / R04（纯数据结构，不参与 GPU）。
"""

from __future__ import annotations

from typing import Any


def make_source(title: str, authors: str, year: int, url: str) -> dict[str, Any]:
    """构建来源标注 dict（R02 学术诚信，每个器件可溯源）。

    原 catalog.py 内部名为 ``_src``，拆分后改为 ``make_source`` 公开，
    供 devices 数据构建使用。
    """
    return {"title": title, "authors": authors, "year": year, "url": url}


# ---------------------------------------------------------------------------
# 36 器件目录（4 平台 × 9 器件）
# ---------------------------------------------------------------------------
# 每个器件 dict 字段:
#   platform / device_type / name / category / foundry / process_node
#   params（含 pdk_reference 标注来源 PDK）
#   source（文献溯源 dict）
#   ports（端口列表 [(name, x_um, y_um, direction), ...]）
#   bbox_um（包围盒 {xmin, ymin, xmax, ymax}）
DEVICES: list[dict[str, Any]] = [
    # ====================================================================
    # SOI 平台（SiEPIC EBeam PDK, 220nm SOI）— 9 器件
    # ====================================================================
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
        "source": make_source("SiEPIC EBeam PDK strip waveguide",
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
        "source": make_source("三星 300mm 硅光平台 OFC 2026 + SiEPIC EBeam PDK",
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
        "source": make_source("SiEPIC EBeam PDK Y branch",
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
        "source": make_source("硅光工艺平台比较（iccsz.com）",
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
        "source": make_source("SiEPIC EBeam PDK ring resonator",
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
        "source": make_source("SiEPIC EBeam PDK directional coupler",
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
        "source": make_source("AIM Photonics 无源硅基光电子芯片元件教程",
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
        "source": make_source("SiEPIC EBeam PDK thermo-optic phase shifter",
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
        "source": make_source("AIM Photonics Ge photodetector",
                       "AIM Photonics", 2024,
                       "https://www.latitudeda.com/document/716"),
        "ports": [("in", 0.0, 0.0, "west"), ("rf_out", 10.0, 2.0, "south")],
        "bbox_um": {"xmin": 0.0, "ymin": -2.0, "xmax": 10.0, "ymax": 2.0},
    },

    # ====================================================================
    # SiN 平台（Ligentec ANR PDK, SiN TriPleX）— 9 器件
    # ====================================================================
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
        "source": make_source("Ligentec ANR SiN LPCVD waveguide",
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
        "source": make_source("LioniX TriPleX double-stripe SiN waveguide",
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
        "source": make_source("Ligentec ANR SiN grating coupler",
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
        "source": make_source("EPFL Damascene SiN high-Q microring",
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
        "source": make_source("Ligentec ANR SiN MMI 1x2",
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
        "source": make_source("Ligentec ANR SiN directional coupler",
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
        "source": make_source("Ligentec ANR SiN MZI",
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
        "source": make_source("Ligentec ANR SiN thermo-optic phase shifter",
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
        "source": make_source("IMEC Damascene SiN waveguide (8-inch)",
                       "IMEC", 2023, "https://doi.org/10.3390/app13063660"),
        "ports": [("in", 0.0, 0.0, "west"), ("out", 10.0, 0.0, "east")],
        "bbox_um": {"xmin": 0.0, "ymin": -0.75, "xmax": 10.0, "ymax": 0.75},
    },

    # ====================================================================
    # InP 平台（Pattern Project / JEPPIX, InP generic）— 9 器件
    # ====================================================================
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
        "source": make_source("InP-Based Foundry PICs for Optical Interconnects",
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
        "source": make_source("InP-Based Foundry PICs for Optical Interconnects",
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
        "source": make_source("InP-Based Foundry PICs for Optical Interconnects",
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
        "source": make_source("InP-Based Foundry PICs for Optical Interconnects",
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
        "source": make_source("InP-Based Foundry PICs for Optical Interconnects",
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
        "source": make_source("InP Photonic Integrated Circuits for Free Space Optical Links",
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
        "source": make_source("InP Photonic Integrated Circuits for Free Space Optical Links",
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
        "source": make_source("InP Photonic Integrated Circuits for Free Space Optical Links",
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
        "source": make_source("SemiNex high-power InP SOA",
                       "SemiNex", 2024, "https://www.aptechnologies.co.uk/news"),
        "ports": [("in", 0.0, 0.0, "west"), ("out", 2000.0, 0.0, "east")],
        "bbox_um": {"xmin": 0.0, "ymin": -1.0, "xmax": 2000.0, "ymax": 1.0},
    },

    # ====================================================================
    # LNOI 平台（HyperLight LNOI PDK, X-cut TFLN）— 9 器件
    # ====================================================================
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
        "source": make_source("LNOI platform: wafer-scale lithium niobate PICs",
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
        "source": make_source("LNOI platform: wafer-scale lithium niobate PICs",
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
        "source": make_source("High-confinement LNOI Mach-Zehnder modulator",
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
        "source": make_source("U-T double-layer traveling-wave electrode LNOI modulator",
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
        "source": make_source("薄膜铌酸锂电光调制器研究进展",
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
        "source": make_source("Thin-film lithium niobate integrated photonics (TFLN review)",
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
        "source": make_source("Integrated LN EO modulators operating at CMOS-compatible voltages",
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
        "source": make_source("Integrated lithium niobate electro-optic modulators "
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
        "source": make_source("HyperLight LNOI PDK Y branch",
                       "HyperLight", 2024,
                       "https://hyperlightphotonics.com/"),
        "ports": [("in", 0.0, 0.0, "west"),
                  ("out1", 20.0, 1.0, "east"), ("out2", 20.0, -1.0, "east")],
        "bbox_um": {"xmin": 0.0, "ymin": -1.75, "xmax": 20.0, "ymax": 1.75},
    },
]


__all__ = ["PLATFORM_META", "DEVICES", "make_source"]
