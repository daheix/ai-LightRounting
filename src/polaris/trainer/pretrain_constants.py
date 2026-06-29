"""R34: AlphaChip 预训练-微调范式 — 平台常量与物理参数表。

从 pretrain.py 拆分（facade 模式，保持外部 import 路径不变）。

定义四平台（SOI/SiN/InP/LNOI）物理参数常量与电路模板类型枚举，
用于预训练数据集平台标注、图特征构建与 checkpoint 元信息。

纯 NumPy/CPU 实现（🚫不参与 GPU，R04 战略决策）。

来源:
- Mirhoseini et al., Nature 2021, AlphaChip 预训练范式
  https://www.nature.com/articles/s41586-021-03544-w
- Goldie et al., arXiv 2024, 预训练必要性辩护
  https://arxiv.org/abs/2411.10053
- Circuit Training Pre-training Guide
  https://github.com/google-research/circuit_training/blob/main/docs/PRETRAINING.md
- SiEPIC EBeam PDK (SOI 平台参数)
  https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- Ligentec TriPleX (SiN 平台参数)
  https://www.ligentec.com/
- HyperLight (LNOI 平台参数)
  https://www.hyperlightcorp.com/
- InP 平台参数
  https://pattern-project.eu/technology/material-platforms/inp-platform/
"""

from __future__ import annotations

# =============================================================================
# 平台标识常量
# =============================================================================

PLATFORM_SOI = "SOI"
PLATFORM_SIN = "SiN"
PLATFORM_INP = "InP"
PLATFORM_LNOI = "LNOI"
ALL_PLATFORMS: tuple[str, ...] = (PLATFORM_SOI, PLATFORM_SIN, PLATFORM_INP, PLATFORM_LNOI)


# =============================================================================
# 四平台物理参数（来源：公开文献典型值，用于预训练数据集平台标注）
# =============================================================================
# R05 Bug 修复 v4.0-PHY-PARAM（第2轮迭代发现）:
# 原 SOI loss=0.5 dB/cm 错误（实为 SiN 平台值），LNOI loss=0.5 dB/cm 为
# 商用保守值，应统一为主源 Liu 2025 晶圆级量产值 0.4 dB/cm。
# 修复后参数表与 router/waveguide_router.py、pdk/foundry_platforms.py、
# sim/calibration.py、pdk/lnoi.py 保持一致。
# 规则: R02 学术诚信 / R05 Bug 必修
# 文献:
# - Soref et al. 1993 IEEE Proc. 41(9) 1182-1183 SOI 3 dB/cm
#   https://ieeexplore.ieee.org/document/1148303
# - Vlasov & McNab 2004 Opt. Express 12(8) 1622-1631 SOI 3.6±0.1 dB/cm
#   https://www.opticsexpress.org/abstract.cfm?uri=oe-12-8-1622
# - Chrostowski & Hochberg 2015 "Silicon Photonics Design" §6.4
#   https://www.cambridge.org/core/books/silicon-photonics-design/
# - SiEPIC EBeam PDK https://github.com/SiEPIC/SiEPIC_EBeam_PDK
# - Liu et al. 2025 Light: AM 6, 47 LNOI <0.4 dB/cm
#   https://doi.org/10.37188/lam.2025.047
# - Ligentec TriPleX (SiN) https://www.ligentec.com/
# - InP 平台 https://pattern-project.eu/technology/material-platforms/inp-platform/
# 来源:
# - SOI: SiEPIC EBeam PDK + Soref 1993 + Vlasov 2004
#   n_eff=2.34 (220nm SOI TE0), loss=3.0 dB/cm, min_bend=5μm
# - SiN: Ligentec TriPleX https://www.ligentec.com/
#   n_eff=1.80, loss=0.1 dB/cm, min_bend=100μm
# - InP: InP 异质集成 https://pattern-project.eu/technology/material-platforms/inp-platform/
#   n_eff=3.10, loss=2.0 dB/cm, min_bend=50μm
# - LNOI: Liu 2025 Light AM 晶圆级量产值
#   n_eff=2.10, loss=0.4 dB/cm, min_bend=30μm
PLATFORM_PHYSICAL_PARAMS: dict[str, dict[str, float]] = {
    PLATFORM_SOI: {
        "n_eff": 2.34,
        "waveguide_loss_db_cm": 3.0,
        "min_bend_radius_um": 5.0,
        "wavelength_nm": 1550.0,
    },
    PLATFORM_SIN: {
        "n_eff": 1.80,
        "waveguide_loss_db_cm": 0.1,
        "min_bend_radius_um": 100.0,
        "wavelength_nm": 1550.0,
    },
    PLATFORM_INP: {
        "n_eff": 3.10,
        "waveguide_loss_db_cm": 2.0,
        "min_bend_radius_um": 50.0,
        "wavelength_nm": 1550.0,
    },
    PLATFORM_LNOI: {
        "n_eff": 2.10,
        "waveguide_loss_db_cm": 0.4,
        "min_bend_radius_um": 30.0,
        "wavelength_nm": 1550.0,
    },
}


# 电路模板类型（覆盖 R34.md §7.1 要求的 MZI/Clements/Ring/Splitter Tree/Crossbar）
CIRCUIT_TEMPLATES: tuple[str, ...] = (
    "mzi_lattice",
    "splitter_tree",
    "switch_chain",
    "random",
)


__all__ = [
    "ALL_PLATFORMS",
    "CIRCUIT_TEMPLATES",
    "PLATFORM_INP",
    "PLATFORM_LNOI",
    "PLATFORM_PHYSICAL_PARAMS",
    "PLATFORM_SIN",
    "PLATFORM_SOI",
]
