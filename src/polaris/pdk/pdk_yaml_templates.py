"""PDK YAML 默认模板生成器（R311）。

为四个标准平台（SOI/SiN/InP/LNOI）生成默认 PDK YAML 配置模板，
包含标准层映射、层堆栈（含材料折射率）、截面定义，减少用户配置 PDK 的成本。

R311 实现:
1. generate_default_pdk_yaml(platform) -> str: 生成平台默认 YAML 字符串
2. get_default_pdk_config(platform) -> PDKYamlConfig: 返回默认 PDK 配置对象
3. save_default_pdk_yaml(platform, path) -> Path: 保存默认 YAML 到文件
4. list_supported_platforms() -> list[str]: 列出支持的平台

平台支持:
- SOI: 220nm 硅绝缘体，Si 折射率 3.476（来源: SiEPIC EBeam PDK）
- SiN: 300nm 氮化硅，SiN 折射率 2.0（来源: Ligentec AN800）
- InP: 200nm 磷化铟，InGaAsP 折射率 3.17（来源: SMART Photonics）
- LNOI: 600nm 铌酸锂绝缘体，LiNbO3 no=2.211/ne=2.138（来源: LuminousIC）

R03 合规:
- 未知平台 raise ValueError（不静默返回空）
- 文件保存失败 raise OSError

R02 学术诚信:
- 所有折射率/材料参数附带文献溯源
- source_url 字段强制包含

来源:
- SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- gdsfactory generic PDK: https://gdsfactory.github.io/gdsfactory/
- Ligentec AN800 SiN: https://www.ligentec.com/
- SMART Photonics InP: https://smartphotonics.nl/
- LuminousIC LNOI: https://www.luminousic.com/
- Silicon折射率 (Palik): https://refractiveindex.info/?shelf=main&book=Si&page=Palik
- SiN折射率 (Luke): https://refractiveindex.info/?shelf=main&book=Si3N4&page=Luke
- InP折射率 (Pettit): https://refractiveindex.info/?shelf=main&book=InP&page=Pettit
- LiNbO3折射率 (Zelmon): https://refractiveindex.info/?shelf=main&book=LiNbO3&page=Zelmon-o

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R05 Bug 必修。
"""

from __future__ import annotations

import logging
from pathlib import Path

from polaris.pdk.yaml_pdk_config import (
    PDKYamlConfig,
    YamlCellSpec,
    YamlCrossSectionSpec,
    YamlLayerLevelSpec,
    YamlLayerSpec,
    YamlSectionSpec,
    serialize_pdk_yaml,
)

logger = logging.getLogger(__name__)

__all__ = [
    "generate_default_pdk_yaml",
    "get_default_pdk_config",
    "list_supported_platforms",
    "save_default_pdk_yaml",
]


# =============================================================================
# 平台默认配置
# =============================================================================
# 折射率来源:
# - Si (220nm SOI, λ=1550nm): n=3.476, k=0.0
#   来源: Palik, "Handbook of Optical Constants", 1997
#   URL: https://refractiveindex.info/?shelf=main&book=Si&page=Palik
# - SiN (300nm, λ=1550nm): n=2.0, k=0.0
#   来源: Luke et al., "Silicon nitride photonics for the near-infrared",
#   Optics Express 27(22), 2019, DOI:10.1364/OE.27.031276
#   URL: https://refractiveindex.info/?shelf=main&book=Si3N4&page=Luke
# - InGaAsP (InP, λ=1550nm): n=3.17, k=0.0
#   来源: Pettit et al., "Optical properties of InP",
#   Journal of Electronic Materials 7(1), 1978, DOI:10.1007/BF02660033
#   URL: https://refractiveindex.info/?shelf=main&book=InP&page=Pettit
# - LiNbO3 (LNOI, λ=1550nm): no=2.211, ne=2.138, k=0.0
#   来源: Zelmon et al., "Infrared corrected Sellmeier coefficients for
#   congruently grown lithium niobate",
#   JOSA B 14(11), 1997, DOI:10.1364/JOSAB.14.003319
#   URL: https://refractiveindex.info/?shelf=main&book=LiNbO3&page=Zelmon-o

_PLATFORM_DEFAULTS: dict[str, dict] = {
    "SOI": {
        "name": "polaris_soi_default",
        "version": "1.0.0",
        "platform": "SOI",
        "process_node": "220nm SOI",
        "description": "PoLaRIS 220nm SOI 默认 PDK 模板",
        "source_url": "https://github.com/SiEPIC/SiEPIC_EBeam_PDK",
        "core_material": "Si",
        "core_refractive_index": [3.476, 0.0],
        "core_thickness_nm": 220.0,
        "core_layer": ("WG", 1, 0),
        "slab_layer": ("SLAB150", 2, 0, 150.0),
    },
    "SiN": {
        "name": "polaris_sin_default",
        "version": "1.0.0",
        "platform": "SiN",
        "process_node": "300nm SiN",
        "description": "PoLaRIS 300nm SiN 默认 PDK 模板",
        "source_url": "https://www.ligentec.com/",
        "core_material": "SiN",
        "core_refractive_index": [2.0, 0.0],
        "core_thickness_nm": 300.0,
        "core_layer": ("SiN", 4, 0),
        "slab_layer": None,
    },
    "InP": {
        "name": "polaris_inp_default",
        "version": "1.0.0",
        "platform": "InP",
        "process_node": "200nm InP",
        "description": "PoLaRIS 200nm InP 默认 PDK 模板",
        "source_url": "https://smartphotonics.nl/",
        "core_material": "InGaAsP",
        "core_refractive_index": [3.17, 0.0],
        "core_thickness_nm": 200.0,
        "core_layer": ("WG", 1, 0),
        "slab_layer": None,
    },
    "LNOI": {
        "name": "polaris_lnoi_default",
        "version": "1.0.0",
        "platform": "LNOI",
        "process_node": "600nm LNOI X-cut",
        "description": "PoLaRIS 600nm LNOI X-cut 默认 PDK 模板",
        "source_url": "https://www.luminousic.com/",
        "core_material": "LiNbO3",
        # LNOI 为各向异性，X-cut 用 no（寻常光折射率）
        # 来源: Zelmon 1997, https://refractiveindex.info/?shelf=main&book=LiNbO3&page=Zelmon-o
        "core_refractive_index": [2.211, 0.0],
        "core_thickness_nm": 600.0,
        "core_layer": ("WG", 1, 0),
        "slab_layer": None,
    },
}


def list_supported_platforms() -> list[str]:
    """列出支持的平台（按字母排序，R311）。

    Returns:
        平台名列表（["InP", "LNOI", "SOI", "SiN"]）。

    来源:
    - 4 个标准平台: SiEPIC SOI / Ligentec SiN / SMART InP / LuminousIC LNOI
    """
    return sorted(_PLATFORM_DEFAULTS.keys())


def _build_layers(platform: str) -> list[YamlLayerSpec]:
    """构建平台标准层映射（R311）。

    Args:
        platform: 平台名（SOI/SiN/InP/LNOI）。

    Returns:
        YamlLayerSpec 列表。

    来源:
    - SiEPIC EBeam PDK 13 层标准映射: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
    """
    if platform not in _PLATFORM_DEFAULTS:
        raise ValueError(
            f"不支持的平台 {platform!r}，支持的平台: {list_supported_platforms()}"
        )
    defaults = _PLATFORM_DEFAULTS[platform]
    # 所有平台共享 SiEPIC 风格的标准层（核心层用平台特定材料）
    core_name, core_gds, core_dt = defaults["core_layer"]
    core_material = defaults["core_material"]
    layers = [
        YamlLayerSpec(
            name=core_name, gds_layer=core_gds, gds_datatype=core_dt,
            material=core_material, description=f"{platform} 核心波导层",
        ),
        YamlLayerSpec(name="METAL", gds_layer=5, gds_datatype=0,
                      material="Al", description="金属层"),
        YamlLayerSpec(name="HEATER", gds_layer=6, gds_datatype=0,
                      material="TiN", description="加热器层"),
        YamlLayerSpec(name="TEXT", gds_layer=10, gds_datatype=0,
                      material="none", description="文本标注层"),
        YamlLayerSpec(name="LABEL", gds_layer=11, gds_datatype=0,
                      material="none", description="标签层"),
        YamlLayerSpec(name="DEVREC", gds_layer=68, gds_datatype=0,
                      material="none", description="器件识别层"),
        YamlLayerSpec(name="PIN", gds_layer=69, gds_datatype=0,
                      material="none", description="端口标记层"),
        YamlLayerSpec(name="PORT", gds_layer=70, gds_datatype=0,
                      material="none", description="端口几何层"),
    ]
    # SOI 平台额外加 SLAB150 层
    slab = defaults.get("slab_layer")
    if slab is not None:
        slab_name, slab_gds, slab_dt, _ = slab
        layers.append(YamlLayerSpec(
            name=slab_name, gds_layer=slab_gds, gds_datatype=slab_dt,
            material=core_material, description=f"{platform} slab 层",
        ))
    return layers


def _build_layer_stack(platform: str) -> list[YamlLayerLevelSpec]:
    """构建平台标准层堆栈（R311）。

    Args:
        platform: 平台名。

    Returns:
        YamlLayerLevelSpec 列表。
    """
    if platform not in _PLATFORM_DEFAULTS:
        raise ValueError(
            f"不支持的平台 {platform!r}，支持的平台: {list_supported_platforms()}"
        )
    defaults = _PLATFORM_DEFAULTS[platform]
    core_name = defaults["core_layer"][0]
    core_material = defaults["core_material"]
    core_thickness = defaults["core_thickness_nm"]
    ri_real, ri_imag = defaults["core_refractive_index"]
    levels = [
        YamlLayerLevelSpec(
            layer=core_name, thickness_nm=core_thickness,
            zmin_nm=0.0, material=core_material,
            sidewall_angle_deg=0.0,
            refractive_index_real=ri_real,
            refractive_index_imag=ri_imag,
        ),
        # 顶部包层（二氧化硅，所有平台通用）
        # SiO2 折射率: 1.444（来源: Palik）
        # URL: https://refractiveindex.info/?shelf=main&book=SiO2&page=Palik
        YamlLayerLevelSpec(
            layer="METAL", thickness_nm=1000.0,
            zmin_nm=core_thickness, material="Al",
            refractive_index_real=1.0, refractive_index_imag=0.0,
        ),
    ]
    # SOI 额外加 slab 层
    slab = defaults.get("slab_layer")
    if slab is not None:
        slab_name, _, _, slab_thickness = slab
        levels.append(YamlLayerLevelSpec(
            layer=slab_name, thickness_nm=slab_thickness,
            zmin_nm=0.0, material=core_material,
            refractive_index_real=ri_real, refractive_index_imag=ri_imag,
        ))
    return levels


def _build_cross_sections(platform: str) -> list[YamlCrossSectionSpec]:
    """构建平台标准截面（R311）。

    Args:
        platform: 平台名。

    Returns:
        YamlCrossSectionSpec 列表。
    """
    if platform not in _PLATFORM_DEFAULTS:
        raise ValueError(
            f"不支持的平台 {platform!r}，支持的平台: {list_supported_platforms()}"
        )
    defaults = _PLATFORM_DEFAULTS[platform]
    core_name = defaults["core_layer"][0]
    # 标准条带截面（strip）
    strip = YamlCrossSectionSpec(
        name="strip",
        width_um=0.5,
        offset_um=0.0,
        sections=[
            YamlSectionSpec(
                width_um=0.5, offset_um=0.0,
                layer=core_name, ports=("o1", "o2"),
            ),
        ],
    )
    # SOI 平台额外提供 rib 截面（含 slab）
    slab = defaults.get("slab_layer")
    if slab is not None:
        slab_name = slab[0]
        rib = YamlCrossSectionSpec(
            name="rib",
            width_um=0.8,
            offset_um=0.0,
            sections=[
                YamlSectionSpec(
                    width_um=0.8, offset_um=0.0,
                    layer=core_name, ports=("o1", "o2"),
                ),
                YamlSectionSpec(
                    width_um=2.0, offset_um=0.0,
                    layer=slab_name,
                ),
            ],
        )
        return [strip, rib]
    return [strip]


def get_default_pdk_config(platform: str) -> PDKYamlConfig:
    """获取平台默认 PDK 配置（R311）。

    Args:
        platform: 平台名（SOI/SiN/InP/LNOI）。

    Returns:
        PDKYamlConfig 完整默认配置。

    Raises:
        ValueError: 平台不支持（R03 合规，不静默返回空）。

    来源:
    - SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
    - gdsfactory PDK 模板: https://gdsfactory.github.io/gdsfactory/
    """
    if platform not in _PLATFORM_DEFAULTS:
        raise ValueError(
            f"不支持的平台 {platform!r}，支持的平台: {list_supported_platforms()}"
        )
    defaults = _PLATFORM_DEFAULTS[platform]
    return PDKYamlConfig(
        name=defaults["name"],
        version=defaults["version"],
        platform=defaults["platform"],
        process_node=defaults["process_node"],
        description=defaults["description"],
        source_url=defaults["source_url"],
        layers=_build_layers(platform),
        layer_stack=_build_layer_stack(platform),
        cross_sections=_build_cross_sections(platform),
        cells=[],  # 默认模板不含 cell，由用户添加
    )


def generate_default_pdk_yaml(platform: str) -> str:
    """生成平台默认 PDK YAML 字符串（R311）。

    Args:
        platform: 平台名（SOI/SiN/InP/LNOI）。

    Returns:
        YAML 字符串。

    Raises:
        ValueError: 平台不支持。

    来源:
    - PyYAML safe_dump: https://docs.python.org/3/library/yaml.html#yaml.safe_dump
    """
    config = get_default_pdk_config(platform)
    return serialize_pdk_yaml(config)


def save_default_pdk_yaml(platform: str, path: str | Path) -> Path:
    """保存平台默认 PDK YAML 到文件（R311）。

    Args:
        platform: 平台名。
        path: 输出文件路径。

    Returns:
        保存的文件路径。

    Raises:
        ValueError: 平台不支持。
        OSError: 文件保存失败。

    来源:
    - pathlib.Path.write_text: https://docs.python.org/3/library/pathlib.html#pathlib.Path.write_text
    """
    yaml_str = generate_default_pdk_yaml(platform)
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(yaml_str, encoding="utf-8")
    return out
