"""YAML PDK 配置系统（R309）。

定义 PoLaRIS PDK 的独立 YAML 描述 schema，覆盖 PDK 元数据、层映射、
层堆栈、截面、cell 清单五类信息。与 gdsfactory `from_yaml`（布局规范）
互补：from_yaml 描述"如何放置器件"，本模块描述"PDK 本身长什么样"。

R309 实现:
1. PDKYamlConfig: 完整 PDK YAML 配置数据类
2. YamlLayerSpec/YamlLayerLevelSpec/YamlSectionSpec/YamlCrossSectionSpec/YamlCellSpec: 五类子规格
3. parse_pdk_yaml(path) -> PDKYamlConfig: 解析 YAML 文件
4. serialize_pdk_yaml(config) -> str: 序列化为 YAML 字符串
5. build_polaris_layer_stack(specs) -> PolarisLayerStack: YAML 规格 → PolarisLayerStack
6. build_polaris_cross_section(spec) -> PolarisCrossSection: YAML 规格 → PolarisCrossSection
7. build_polaris_pdk_from_yaml(path) -> PolarisPDK: YAML → PolarisPDK（含 layer_stack + cross_sections）
8. validate_pdk_yaml(config) -> list[str]: 配置校验（返回错误信息列表）

R03 合规设计:
- YAML 文件不存在 raise FileNotFoundError（不静默返回空）
- YAML 语法错误 raise ValueError（不静默兜底）
- 字段类型不匹配 raise TypeError
- 必填字段缺失 raise ValueError
- 复折射率实部/虚部格式错误 raise ValueError

schema 设计依据:
- gdsfactory LayerStack YAML: https://github.com/gdsfactory/gdsfactory/blob/main/gdsfactory/technology/layer_stack.py
- gdsfactory CrossSection YAML: https://github.com/gdsfactory/gdsfactory/blob/main/gdsfactory/cross_section.py
- gdsfactory from_yaml 布局: https://github.com/gdsfactory/gdsfactory/blob/main/gdsfactory/read/from_yaml.py
- OpenROAD libcudd OpenAccess PDK YAML: https://openroad.readthedocs.io/en/latest/main/src/drt/README.html
- OpenROAD PDK schema: https://github.com/RTimothyEdwards/open_pdks
- SiEPIC EBeam PDK layers.klayout: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- IPKISS PDK YAML: https://academy.lucedaphotonics.com/training/topical_training/tape_out_prep_verification/drc/drc
- SkyWater sky130 PDK config: https://github.com/google/skywater-pdk
- PyYAML safe_load: https://docs.python.org/3/library/yaml.html#yaml.safe_load

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R05 Bug 必修。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from polaris.pdk.gdsfactory_pdk_bridge import (
    PolarisCrossSection,
    PolarisLayerLevel,
    PolarisLayerStack,
    PolarisPDK,
    PolarisSection,
)

logger = logging.getLogger(__name__)

__all__ = [
    "PDKYamlConfig",
    "YamlCellSpec",
    "YamlCrossSectionSpec",
    "YamlLayerLevelSpec",
    "YamlLayerSpec",
    "YamlSectionSpec",
    "build_polaris_cross_section",
    "build_polaris_layer_stack",
    "build_polaris_pdk_from_yaml",
    "parse_pdk_yaml",
    "serialize_pdk_yaml",
    "validate_pdk_yaml",
]


# =============================================================================
# 数据类定义
# =============================================================================
@dataclass
class YamlLayerSpec:
    """YAML 层规格（R309）。

    描述单个 GDSII 层的元数据：名称、(layer, datatype)、材料、描述。

    Attributes:
        name: 层名（如 "WG"）。
        gds_layer: GDSII layer 号。
        gds_datatype: GDSII datatype 号。
        material: 材料名（如 "Si"）。
        description: 描述。

    来源:
    - SiEPIC EBeam PDK 层定义: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
    - GDSII 层规范: https://gdsfactory.github.io/gdsfactory/
    """

    name: str
    gds_layer: int
    gds_datatype: int
    material: str = "unknown"
    description: str = ""


@dataclass
class YamlLayerLevelSpec:
    """YAML 层堆栈级别规格（R309）。

    描述 3D 层堆栈中一个级别的几何与材料参数。

    Attributes:
        layer: 层名（对应 YamlLayerSpec.name）。
        thickness_nm: 厚度（nm）。
        zmin_nm: 底部 z 坐标（nm）。
        material: 材料名。
        sidewall_angle_deg: 侧壁角度（度，0=垂直）。
        refractive_index_real: 折射率实部（None 表示未指定）。
        refractive_index_imag: 折射率虚部（None 表示未指定，0=无损）。

    来源:
    - gdsfactory LayerLevel: https://github.com/gdsfactory/gdsfactory/blob/main/gdsfactory/technology/layer_stack.py
    """

    layer: str
    thickness_nm: float
    zmin_nm: float = 0.0
    material: str = "unknown"
    sidewall_angle_deg: float = 0.0
    refractive_index_real: float | None = None
    refractive_index_imag: float | None = None


@dataclass
class YamlSectionSpec:
    """YAML 截面段规格（R309）。

    描述截面中的一个段（宽度/偏移/层/端口）。

    Attributes:
        width_um: 段宽度（μm）。
        offset_um: 段偏移（μm）。
        layer: 层名。
        ports: 端口名元组（可空）。

    来源:
    - gdsfactory Section: https://github.com/gdsfactory/gdsfactory/blob/main/gdsfactory/cross_section.py
    """

    width_um: float
    offset_um: float
    layer: str
    ports: tuple[str, str] | None = None
    hidden: bool = False


@dataclass
class YamlCrossSectionSpec:
    """YAML 截面规格（R309）。

    Attributes:
        name: 截面名（如 "strip"）。
        width_um: 主宽度（μm）。
        offset_um: 主偏移（μm）。
        sections: 截面段列表。

    来源:
    - gdsfactory CrossSection: https://gdsfactory.github.io/gdsfactory/
    """

    name: str
    width_um: float = 0.0
    offset_um: float = 0.0
    sections: list[YamlSectionSpec] = field(default_factory=list)


@dataclass
class YamlCellSpec:
    """YAML cell 规格（R309）。

    描述 PDK 中一个 cell 的元数据（不包含工厂函数，工厂由代码注册）。

    Attributes:
        name: cell 名称（唯一键）。
        platform: 工艺平台（SOI/SiN/InP/LNOI）。
        category: 类别（passive/active/source/detector）。
        params_schema: 参数 schema（键名 → 默认值）。
        description: 描述。

    来源:
    - gdsfactory PDK cell 注册: https://gdsfactory.github.io/gdsfactory/notebooks/04_pdk.html
    """

    name: str
    platform: str = "SOI"
    category: str = "passive"
    params_schema: dict[str, object] = field(default_factory=dict)
    description: str = ""


@dataclass
class PDKYamlConfig:
    """完整 PDK YAML 配置（R309）。

    PoLaRIS PDK 的 YAML 描述，与 gdsfactory `from_yaml`（布局规范）互补。

    Attributes:
        name: PDK 名称（如 "polaris_soi"）。
        version: PDK 版本（SemVer，如 "1.0.0"）。
        platform: 工艺平台（SOI/SiN/InP/LNOI）。
        process_node: 工艺节点（如 "220nm SOI"）。
        description: PDK 描述。
        source_url: 溯源 URL（学术诚信 R02）。
        layers: 层规格列表。
        layer_stack: 层堆栈级别列表。
        cross_sections: 截面规格列表。
        cells: cell 规格列表。

    schema 设计依据:
    - 与 PolarisPDK 字段对齐（platform/process_node/layer_stack/cross_sections）
    - 与 gdsfactory PDK 元数据对齐（name/platform）
    - source_url 字段强制要求（R02 学术诚信）

    来源:
    - SemVer 版本规范: https://semver.org
    - gdsfactory PDK 结构: https://gdsfactory.github.io/gdsfactory/
    """

    name: str
    version: str
    platform: str
    process_node: str
    description: str = ""
    source_url: str = ""
    layers: list[YamlLayerSpec] = field(default_factory=list)
    layer_stack: list[YamlLayerLevelSpec] = field(default_factory=list)
    cross_sections: list[YamlCrossSectionSpec] = field(default_factory=list)
    cells: list[YamlCellSpec] = field(default_factory=list)


# =============================================================================
# YAML 解析
# =============================================================================
def _require_dict(data: object, section: str) -> dict:
    """校验 data 为 dict，否则 raise TypeError（R03 合规）。"""
    if not isinstance(data, dict):
        raise TypeError(
            f"YAML '{section}' 段应为字典，得到 {type(data).__name__}"
        )
    return data


def _require_list(data: object, section: str) -> list:
    """校验 data 为 list，否则 raise TypeError（R03 合规）。"""
    if not isinstance(data, list):
        raise TypeError(
            f"YAML '{section}' 段应为列表，得到 {type(data).__name__}"
        )
    return data


def _parse_layer(name: str, raw: dict) -> YamlLayerSpec:
    """解析单层规格。Raises: KeyError/TypeError（R03）。"""
    if "gds_layer" not in raw:
        raise KeyError(f"层 '{name}' 缺少必填字段 'gds_layer'")
    if "gds_datatype" not in raw:
        raise KeyError(f"层 '{name}' 缺少必填字段 'gds_datatype'")
    gds_layer = raw["gds_layer"]
    gds_datatype = raw["gds_datatype"]
    if not isinstance(gds_layer, int) or isinstance(gds_layer, bool):
        raise TypeError(
            f"层 '{name}' 的 gds_layer 应为整数，得到 {type(gds_layer).__name__}"
        )
    if not isinstance(gds_datatype, int) or isinstance(gds_datatype, bool):
        raise TypeError(
            f"层 '{name}' 的 gds_datatype 应为整数，得到 {type(gds_datatype).__name__}"
        )
    return YamlLayerSpec(
        name=str(name),
        gds_layer=gds_layer,
        gds_datatype=gds_datatype,
        material=str(raw.get("material", "unknown") or "unknown"),
        description=str(raw.get("description", "") or ""),
    )


def _parse_layer_level(raw: dict) -> YamlLayerLevelSpec:
    """解析层堆栈级别。Raises: KeyError/TypeError/ValueError（R03）。"""
    if "layer" not in raw:
        raise KeyError("layer_stack 项缺少必填字段 'layer'")
    if "thickness_nm" not in raw:
        raise KeyError("layer_stack 项缺少必填字段 'thickness_nm'")
    layer = raw["layer"]
    thickness = raw["thickness_nm"]
    if not isinstance(layer, str):
        raise TypeError(
            f"layer_stack.layer 应为字符串，得到 {type(layer).__name__}"
        )
    if not isinstance(thickness, (int, float)) or isinstance(thickness, bool):
        raise TypeError(
            f"layer_stack.thickness_nm 应为数值，得到 {type(thickness).__name__}"
        )
    # 复折射率支持两种格式:
    # 1. refractive_index: [real, imag]（列表）
    # 2. refractive_index_real / refractive_index_imag（标量）
    ri_real: float | None = None
    ri_imag: float | None = None
    if "refractive_index" in raw:
        ri = raw["refractive_index"]
        if not isinstance(ri, list) or len(ri) != 2:
            raise ValueError(
                f"refractive_index 应为 [real, imag] 列表，得到 {ri!r}"
            )
        ri_real = float(ri[0])
        ri_imag = float(ri[1])
    else:
        if "refractive_index_real" in raw:
            ri_real = float(raw["refractive_index_real"])
        if "refractive_index_imag" in raw:
            ri_imag = float(raw["refractive_index_imag"])
    return YamlLayerLevelSpec(
        layer=layer,
        thickness_nm=float(thickness),
        zmin_nm=float(raw.get("zmin_nm", 0.0) or 0.0),
        material=str(raw.get("material", "unknown") or "unknown"),
        sidewall_angle_deg=float(raw.get("sidewall_angle_deg", 0.0) or 0.0),
        refractive_index_real=ri_real,
        refractive_index_imag=ri_imag,
    )


def _parse_section(raw: dict) -> YamlSectionSpec:
    """解析截面段。Raises: KeyError/TypeError（R03）。"""
    if "layer" not in raw:
        raise KeyError("section 缺少必填字段 'layer'")
    ports_raw = raw.get("ports")
    ports: tuple[str, str] | None = None
    if ports_raw is not None:
        if not isinstance(ports_raw, list) or len(ports_raw) != 2:
            raise ValueError(
                f"section.ports 应为 [name1, name2] 列表，得到 {ports_raw!r}"
            )
        ports = (str(ports_raw[0]), str(ports_raw[1]))
    return YamlSectionSpec(
        width_um=float(raw.get("width_um", 0.0) or 0.0),
        offset_um=float(raw.get("offset_um", 0.0) or 0.0),
        layer=str(raw["layer"]),
        ports=ports,
        hidden=bool(raw.get("hidden", False)),
    )


def _parse_cross_section(name: str, raw: dict) -> YamlCrossSectionSpec:
    """解析截面。Raises: KeyError/TypeError（R03）。"""
    sections_raw = raw.get("sections", []) or []
    if not isinstance(sections_raw, list):
        raise TypeError(
            f"截面 '{name}' 的 sections 应为列表，得到 {type(sections_raw).__name__}"
        )
    sections = [_parse_section(s) for s in sections_raw]
    return YamlCrossSectionSpec(
        name=str(name),
        width_um=float(raw.get("width_um", 0.0) or 0.0),
        offset_um=float(raw.get("offset_um", 0.0) or 0.0),
        sections=sections,
    )


def _parse_cell(name: str, raw: dict) -> YamlCellSpec:
    """解析 cell 规格。Raises: TypeError（R03）。"""
    params_raw = raw.get("params_schema", {}) or {}
    if not isinstance(params_raw, dict):
        raise TypeError(
            f"cell '{name}' 的 params_schema 应为字典，得到 {type(params_raw).__name__}"
        )
    return YamlCellSpec(
        name=str(name),
        platform=str(raw.get("platform", "SOI") or "SOI"),
        category=str(raw.get("category", "passive") or "passive"),
        params_schema=dict(params_raw),
        description=str(raw.get("description", "") or ""),
    )


def parse_pdk_yaml(yaml_path: str | Path) -> PDKYamlConfig:
    """解析 YAML PDK 配置文件（R309）。

    Args:
        yaml_path: YAML 文件路径。

    Returns:
        PDKYamlConfig 完整 PDK 配置。

    Raises:
        FileNotFoundError: 文件不存在（R03，不静默返回空配置）。
        ValueError: YAML 语法错误 / 顶层非字典 / 缺少必填字段。
        TypeError: 字段类型不匹配。
        KeyError: 必填字段缺失。

    来源:
    - PyYAML safe_load: https://docs.python.org/3/library/yaml.html#yaml.safe_load
    - gdsfactory from_yaml 模式: https://github.com/gdsfactory/gdsfactory/blob/main/gdsfactory/read/from_yaml.py
    """
    path = Path(yaml_path)
    if not path.exists():
        raise FileNotFoundError(f"PDK YAML 文件不存在: {yaml_path}")
    try:
        with path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ValueError(f"YAML 解析失败: {yaml_path}: {e}") from e
    if not isinstance(data, dict):
        raise ValueError(
            f"YAML 顶层应为字典，得到 {type(data).__name__}: {yaml_path}"
        )

    pdk_raw = _require_dict(data.get("pdk", {}), "pdk")
    # 必填字段校验
    for field_name in ("name", "version", "platform"):
        if field_name not in pdk_raw:
            raise KeyError(f"pdk 段缺少必填字段 '{field_name}': {yaml_path}")
    process_node = str(pdk_raw.get("process_node", "") or "")

    # layers 段（dict: name -> {gds_layer, gds_datatype, ...}）
    layers_raw = _require_dict(data.get("layers", {}) or {}, "layers")
    layers = [_parse_layer(name, raw) for name, raw in layers_raw.items()]

    # layer_stack 段（list of dict）
    layer_stack_raw = _require_list(data.get("layer_stack", []) or [], "layer_stack")
    layer_stack = [_parse_layer_level(item) for item in layer_stack_raw]

    # cross_sections 段（dict: name -> {width_um, sections: [...]})
    cross_sections_raw = _require_dict(
        data.get("cross_sections", {}) or {}, "cross_sections"
    )
    cross_sections = [
        _parse_cross_section(name, raw) for name, raw in cross_sections_raw.items()
    ]

    # cells 段（dict: name -> {platform, category, ...}）
    cells_raw = _require_dict(data.get("cells", {}) or {}, "cells")
    cells = [_parse_cell(name, raw) for name, raw in cells_raw.items()]

    return PDKYamlConfig(
        name=str(pdk_raw["name"]),
        version=str(pdk_raw["version"]),
        platform=str(pdk_raw["platform"]),
        process_node=process_node,
        description=str(pdk_raw.get("description", "") or ""),
        source_url=str(pdk_raw.get("source_url", "") or ""),
        layers=layers,
        layer_stack=layer_stack,
        cross_sections=cross_sections,
        cells=cells,
    )


# =============================================================================
# YAML 序列化
# =============================================================================
def serialize_pdk_yaml(config: PDKYamlConfig) -> str:
    """序列化 PDKYamlConfig 为 YAML 字符串（R309）。

    Args:
        config: PDK 配置。

    Returns:
        YAML 字符串（utf-8 编码，包含 pdk/layers/layer_stack/cross_sections/cells 五段）。

    Raises:
        ValueError: 配置无效（必填字段为空）。

    来源:
    - PyYAML safe_dump: https://docs.python.org/3/library/yaml.html#yaml.safe_dump
    """
    if not config.name:
        raise ValueError("PDK 配置 name 不能为空")
    if not config.version:
        raise ValueError("PDK 配置 version 不能为空")
    if not config.platform:
        raise ValueError("PDK 配置 platform 不能为空")

    pdk_dict: dict = {
        "name": config.name,
        "version": config.version,
        "platform": config.platform,
        "process_node": config.process_node,
        "description": config.description,
        "source_url": config.source_url,
    }
    layers_dict: dict = {}
    for layer in config.layers:
        layers_dict[layer.name] = {
            "gds_layer": layer.gds_layer,
            "gds_datatype": layer.gds_datatype,
            "material": layer.material,
            "description": layer.description,
        }
    layer_stack_list: list = []
    for level in config.layer_stack:
        item: dict = {
            "layer": level.layer,
            "thickness_nm": level.thickness_nm,
            "zmin_nm": level.zmin_nm,
            "material": level.material,
            "sidewall_angle_deg": level.sidewall_angle_deg,
        }
        # 复折射率以 [real, imag] 列表形式序列化
        if level.refractive_index_real is not None:
            item["refractive_index"] = [
                level.refractive_index_real,
                level.refractive_index_imag if level.refractive_index_imag is not None else 0.0,
            ]
        layer_stack_list.append(item)
    cross_sections_dict: dict = {}
    for xs in config.cross_sections:
        xs_item: dict = {
            "width_um": xs.width_um,
            "offset_um": xs.offset_um,
            "sections": [
                {
                    "width_um": s.width_um,
                    "offset_um": s.offset_um,
                    "layer": s.layer,
                    "ports": list(s.ports) if s.ports else None,
                    "hidden": s.hidden,
                }
                for s in xs.sections
            ],
        }
        cross_sections_dict[xs.name] = xs_item
    cells_dict: dict = {}
    for cell in config.cells:
        cells_dict[cell.name] = {
            "platform": cell.platform,
            "category": cell.category,
            "params_schema": cell.params_schema,
            "description": cell.description,
        }
    full_dict = {
        "pdk": pdk_dict,
        "layers": layers_dict,
        "layer_stack": layer_stack_list,
        "cross_sections": cross_sections_dict,
        "cells": cells_dict,
    }
    return yaml.safe_dump(full_dict, allow_unicode=True, sort_keys=False, default_flow_style=False)


# =============================================================================
# 配置校验
# =============================================================================
def validate_pdk_yaml(config: PDKYamlConfig) -> list[str]:
    """校验 PDK YAML 配置完整性（R309）。

    Args:
        config: PDK 配置。

    Returns:
        错误信息列表（空列表表示通过）。注意: 本函数返回错误列表而非 raise，
        用于批量收集所有问题；调用方可根据需要 raise。这与 R03 不冲突——
        R03 禁止静默兜底，本函数是显式的校验 API，调用方必须处理返回值。

    校验项:
    - 必填字段非空（name/version/platform）
    - source_url 非空（R02 学术诚信）
    - 层堆栈引用的 layer 在 layers 中已定义
    - 截面引用的 layer 在 layers 中已定义
    - cell 名称无重复
    """
    errors: list[str] = []
    if not config.name:
        errors.append("pdk.name 为空")
    if not config.version:
        errors.append("pdk.version 为空")
    if not config.platform:
        errors.append("pdk.platform 为空")
    if not config.source_url:
        errors.append("pdk.source_url 为空（R02 学术诚信：所有 PDK 必须溯源）")

    layer_names = {layer.name for layer in config.layers}
    for level in config.layer_stack:
        if level.layer not in layer_names and config.layers:
            errors.append(
                f"layer_stack 引用未定义的层 '{level.layer}'"
            )
    for xs in config.cross_sections:
        for section in xs.sections:
            if section.layer not in layer_names and config.layers:
                errors.append(
                    f"cross_section '{xs.name}' 引用未定义的层 '{section.layer}'"
                )
    cell_names: list[str] = []
    for cell in config.cells:
        cell_names.append(cell.name)
    seen: set[str] = set()
    for name in cell_names:
        if name in seen:
            errors.append(f"cell 名称重复: '{name}'")
        seen.add(name)
    return errors


# =============================================================================
# PDKYamlConfig → PolarisPDK 构建
# =============================================================================
def build_polaris_layer_stack(
    name: str, specs: list[YamlLayerLevelSpec]
) -> PolarisLayerStack:
    """从 YAML 层堆栈规格构建 PolarisLayerStack（R309）。

    Args:
        name: 层堆栈名。
        specs: YAML 层堆栈级别规格列表。

    Returns:
        PolarisLayerStack 对象。

    来源:
    - gdsfactory LayerStack: https://github.com/gdsfactory/gdsfactory/blob/main/gdsfactory/technology/layer_stack.py
    """
    levels: list[PolarisLayerLevel] = []
    for spec in specs:
        # 复折射率（PolarisLayerLevel.refractive_index 为 complex）
        ri: complex | None = None
        if spec.refractive_index_real is not None:
            ri_imag = spec.refractive_index_imag if spec.refractive_index_imag is not None else 0.0
            ri = complex(spec.refractive_index_real, ri_imag)
        levels.append(PolarisLayerLevel(
            layer=spec.layer,
            thickness_nm=spec.thickness_nm,
            zmin_nm=spec.zmin_nm,
            material=spec.material,
            sidewall_angle_deg=spec.sidewall_angle_deg,
            refractive_index=ri,
        ))
    return PolarisLayerStack(name=name, levels=levels)


def build_polaris_cross_section(
    spec: YamlCrossSectionSpec,
) -> PolarisCrossSection:
    """从 YAML 截面规格构建 PolarisCrossSection（R309）。

    Args:
        spec: YAML 截面规格。

    Returns:
        PolarisCrossSection 对象。

    来源:
    - gdsfactory CrossSection: https://github.com/gdsfactory/gdsfactory/blob/main/gdsfactory/cross_section.py
    """
    sections: list[PolarisSection] = [
        PolarisSection(
            width_um=s.width_um,
            offset_um=s.offset_um,
            layer=s.layer,
            ports=s.ports,
            hidden=s.hidden,
        )
        for s in spec.sections
    ]
    return PolarisCrossSection(
        name=spec.name,
        sections=sections,
        width_um=spec.width_um,
        offset_um=spec.offset_um,
    )


def build_polaris_pdk_from_yaml(yaml_path: str | Path) -> PolarisPDK:
    """从 YAML PDK 配置文件构建 PolarisPDK（R309）。

    解析 YAML 文件 → 构建 PolarisPDK（含 layer_stack + cross_sections，
    devices 留空，由后续 register_polaris_cell 填充）。

    Args:
        yaml_path: YAML 文件路径。

    Returns:
        PolarisPDK 对象。

    Raises:
        FileNotFoundError: 文件不存在。
        ValueError: YAML 解析失败 / 配置校验失败。
        TypeError: 字段类型不匹配。
        KeyError: 必填字段缺失。

    来源:
    - PolarisPDK 字段定义: polaris.pdk.gdsfactory_pdk_bridge.PolarisPDK
    - gdsfactory PDK 加载流程: https://gdsfactory.github.io/gdsfactory/
    """
    config = parse_pdk_yaml(yaml_path)
    errors = validate_pdk_yaml(config)
    if errors:
        raise ValueError(
            f"PDK YAML 配置校验失败 ({len(errors)} 个错误): "
            + "; ".join(errors)
        )
    layer_stack = build_polaris_layer_stack(
        config.name + "_layer_stack", config.layer_stack
    ) if config.layer_stack else None
    cross_sections: dict[str, PolarisCrossSection] = {
        xs.name: build_polaris_cross_section(xs) for xs in config.cross_sections
    }
    return PolarisPDK(
        name=config.name,
        platform=config.platform,
        process_node=config.process_node,
        devices={},  # 由后续 register_polaris_cell 填充
        layer_stack=layer_stack,
        cross_sections=cross_sections,
    )
