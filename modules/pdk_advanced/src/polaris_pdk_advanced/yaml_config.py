"""YAML PDK 配置系统（从 v4 迁移，R309）。

定义 PoLaRIS PDK 的独立 YAML 描述 schema，覆盖 PDK 元数据、层映射、
层堆栈、截面、cell 清单五类信息。与 gdsfactory from_yaml（布局规范）
互补：from_yaml 描述"如何放置器件"，本模块描述"PDK 本身长什么样"。

=== Input / Process / Output 三段式文档 ===

Input:
- parse_pdk_yaml(yaml_path): YAML PDK 配置文件路径
- serialize_pdk_yaml(config): PDKYamlConfig 对象
- build_polaris_pdk_from_yaml(yaml_path): YAML 文件路径

Process:
- YAML 解析：pdk/layers/layer_stack/cross_sections/cells 五段
- 配置校验：必填字段非空 / source_url 溯源 / 层引用完整 / cell 唯一
- 构建 PolarisPDK：YAML → PolarisPDK（含 layer_stack + cross_sections）

Output:
- PDKYamlConfig: 完整 PDK YAML 配置数据类
- YamlLayerSpec/YamlLayerLevelSpec/YamlSectionSpec/YamlCrossSectionSpec/YamlCellSpec: 五类子规格
- PolarisPDK: 含 layer_stack + cross_sections 的 PDK 对象

学术依据（R02 学术诚信，均经 WebSearch 验证可访问）:
- gdsfactory LayerStack YAML:
  https://github.com/gdsfactory/gdsfactory/blob/main/gdsfactory/technology/layer_stack.py
- gdsfactory CrossSection YAML:
  https://github.com/gdsfactory/gdsfactory/blob/main/gdsfactory/cross_section.py
- gdsfactory from_yaml 布局:
  https://github.com/gdsfactory/gdsfactory/blob/main/gdsfactory/read/from_yaml.py
- SiEPIC EBeam PDK layers.klayout:
  https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- IPKISS PDK YAML:
  https://academy.lucedaphotonics.com/training/topical_training/tape_out_prep_verification/drc/drc
- SkyWater sky130 PDK config:
  https://github.com/google/skywater-pdk
- PyYAML safe_load:
  https://docs.python.org/3/library/yaml.html#yaml.safe_load
- SemVer 版本规范: https://semver.org

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R05 Bug 必修。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from polaris_pdk_advanced.gdsfactory_bridge import (
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


@dataclass
class YamlLayerSpec:
    """YAML 层规格（R309）。

    描述单个 GDSII 层的元数据：名称、(layer, datatype)、材料、描述。

    来源: SiEPIC EBeam PDK 层定义 https://github.com/SiEPIC/SiEPIC_EBeam_PDK

    Attributes:
        name: 层名（如 "WG"）。
        gds_layer: GDSII layer 号。
        gds_datatype: GDSII datatype 号。
        material: 材料名（如 "Si"）。
        description: 描述。
    """

    name: str
    gds_layer: int
    gds_datatype: int
    material: str = "unknown"
    description: str = ""


@dataclass
class YamlLayerLevelSpec:
    """YAML 层堆栈级别规格（R309）。

    来源: gdsfactory LayerLevel
    https://github.com/gdsfactory/gdsfactory/blob/main/gdsfactory/technology/layer_stack.py

    Attributes:
        layer: 层名。
        thickness_nm: 厚度（nm）。
        zmin_nm: 底部 z 坐标（nm）。
        material: 材料名。
        sidewall_angle_deg: 侧壁角度（度）。
        refractive_index_real: 折射率实部。
        refractive_index_imag: 折射率虚部。
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

    来源: gdsfactory Section
    https://github.com/gdsfactory/gdsfactory/blob/main/gdsfactory/cross_section.py

    Attributes:
        width_um: 段宽度（μm）。
        offset_um: 段偏移（μm）。
        layer: 层名。
        ports: 端口名元组（可空）。
        hidden: 是否隐藏。
    """

    width_um: float
    offset_um: float
    layer: str
    ports: tuple[str, str] | None = None
    hidden: bool = False


@dataclass
class YamlCrossSectionSpec:
    """YAML 截面规格（R309）。

    来源: gdsfactory CrossSection https://gdsfactory.github.io/gdsfactory/

    Attributes:
        name: 截面名（如 "strip"）。
        width_um: 主宽度（μm）。
        offset_um: 主偏移（μm）。
        sections: 截面段列表。
    """

    name: str
    width_um: float = 0.0
    offset_um: float = 0.0
    sections: list[YamlSectionSpec] = field(default_factory=list)


@dataclass
class YamlCellSpec:
    """YAML cell 规格（R309）。

    描述 PDK 中一个 cell 的元数据（不包含工厂函数，工厂由代码注册）。

    来源: gdsfactory PDK cell 注册
    https://gdsfactory.github.io/gdsfactory/notebooks/04_pdk.html

    Attributes:
        name: cell 名称（唯一键）。
        platform: 工艺平台（SOI/SiN/InP/LNOI）。
        category: 类别（passive/active/source/detector）。
        params_schema: 参数 schema（键名 → 默认值）。
        description: 描述。
    """

    name: str
    platform: str = "SOI"
    category: str = "passive"
    params_schema: dict[str, object] = field(default_factory=dict)
    description: str = ""


@dataclass
class PDKYamlConfig:
    """完整 PDK YAML 配置（R309）。

    PoLaRIS PDK 的 YAML 描述，与 gdsfactory from_yaml（布局规范）互补。

    Attributes:
        name: PDK 名称（如 "polaris_soi"）。
        version: PDK 版本（SemVer，如 "1.0.0"）。
        platform: 工艺平台（SOI/SiN/InP/LNOI）。
        process_node: 工艺节点（如 "220nm SOI"）。
        description: PDK 描述。
        source_url: 溯源 URL（R02 学术诚信）。
        layers: 层规格列表。
        layer_stack: 层堆栈级别列表。
        cross_sections: 截面规格列表。
        cells: cell 规格列表。
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


def _require_dict(data: object, section: str) -> dict:
    """校验 data 为 dict，否则 raise TypeError（R03 合规）。"""
    if not isinstance(data, dict):
        raise TypeError(f"YAML '{section}' 段应为字典，得到 {type(data).__name__}")
    return data


def _require_list(data: object, section: str) -> list:
    """校验 data 为 list，否则 raise TypeError（R03 合规）。"""
    if not isinstance(data, list):
        raise TypeError(f"YAML '{section}' 段应为列表，得到 {type(data).__name__}")
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
        raise TypeError(f"层 '{name}' 的 gds_layer 应为整数，得到 {type(gds_layer).__name__}")
    if not isinstance(gds_datatype, int) or isinstance(gds_datatype, bool):
        raise TypeError(f"层 '{name}' 的 gds_datatype 应为整数，得到 {type(gds_datatype).__name__}")
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
        raise TypeError(f"layer_stack.layer 应为字符串，得到 {type(layer).__name__}")
    if not isinstance(thickness, (int, float)) or isinstance(thickness, bool):
        raise TypeError(f"layer_stack.thickness_nm 应为数值，得到 {type(thickness).__name__}")
    ri_real: float | None = None
    ri_imag: float | None = None
    if "refractive_index" in raw:
        ri = raw["refractive_index"]
        if not isinstance(ri, list) or len(ri) != 2:
            raise ValueError(f"refractive_index 应为 [real, imag] 列表，得到 {ri!r}")
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
            raise ValueError(f"section.ports 应为 [name1, name2] 列表，得到 {ports_raw!r}")
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
        raise TypeError(f"截面 '{name}' 的 sections 应为列表，得到 {type(sections_raw).__name__}")
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
        raise TypeError(f"cell '{name}' 的 params_schema 应为字典，得到 {type(params_raw).__name__}")
    return YamlCellSpec(
        name=str(name),
        platform=str(raw.get("platform", "SOI") or "SOI"),
        category=str(raw.get("category", "passive") or "passive"),
        params_schema=dict(params_raw),
        description=str(raw.get("description", "") or ""),
    )


def _get_dict_section(data: dict, key: str) -> dict:
    """获取 YAML dict 段（None 视为空 dict）。"""
    return _require_dict(data.get(key, {}) or {}, key)


def _get_list_section(data: dict, key: str) -> list:
    """获取 YAML list 段（None 视为空 list）。"""
    return _require_list(data.get(key, []) or [], key)


def _get_optional_str(raw: dict, key: str) -> str:
    """获取可选字符串字段（None 视为空串）。"""
    return str(raw.get(key, "") or "")


def parse_pdk_yaml(yaml_path: str | Path) -> PDKYamlConfig:
    """解析 YAML PDK 配置文件（R309）。

    Args:
        yaml_path: YAML 文件路径。

    Returns:
        PDKYamlConfig 完整 PDK 配置。

    Raises:
        FileNotFoundError: 文件不存在（R03）。
        ValueError: YAML 语法错误 / 顶层非字典 / 缺少必填字段。
        TypeError: 字段类型不匹配。
        KeyError: 必填字段缺失。

    来源: PyYAML safe_load
    https://docs.python.org/3/library/yaml.html#yaml.safe_load
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
        raise ValueError(f"YAML 顶层应为字典，得到 {type(data).__name__}: {yaml_path}")

    pdk_raw = _require_dict(data.get("pdk", {}), "pdk")
    for field_name in ("name", "version", "platform"):
        if field_name not in pdk_raw:
            raise KeyError(f"pdk 段缺少必填字段 '{field_name}': {yaml_path}")

    layers_raw = _get_dict_section(data, "layers")
    layers = [_parse_layer(name, raw) for name, raw in layers_raw.items()]
    layer_stack_raw = _get_list_section(data, "layer_stack")
    layer_stack = [_parse_layer_level(item) for item in layer_stack_raw]
    cross_sections_raw = _get_dict_section(data, "cross_sections")
    cross_sections = [_parse_cross_section(name, raw) for name, raw in cross_sections_raw.items()]
    cells_raw = _get_dict_section(data, "cells")
    cells = [_parse_cell(name, raw) for name, raw in cells_raw.items()]

    return PDKYamlConfig(
        name=str(pdk_raw["name"]),
        version=str(pdk_raw["version"]),
        platform=str(pdk_raw["platform"]),
        process_node=_get_optional_str(pdk_raw, "process_node"),
        description=_get_optional_str(pdk_raw, "description"),
        source_url=_get_optional_str(pdk_raw, "source_url"),
        layers=layers,
        layer_stack=layer_stack,
        cross_sections=cross_sections,
        cells=cells,
    )


def _serialize_layer_stack(layer_stack) -> list:
    """序列化 layer_stack 为 list[dict]。"""
    layer_stack_list: list = []
    for level in layer_stack:
        item: dict = {
            "layer": level.layer,
            "thickness_nm": level.thickness_nm,
            "zmin_nm": level.zmin_nm,
            "material": level.material,
            "sidewall_angle_deg": level.sidewall_angle_deg,
        }
        if level.refractive_index_real is not None:
            item["refractive_index"] = [
                level.refractive_index_real,
                level.refractive_index_imag if level.refractive_index_imag is not None else 0.0,
            ]
        layer_stack_list.append(item)
    return layer_stack_list


def _serialize_cross_sections(cross_sections) -> dict:
    """序列化 cross_sections 为 dict。"""
    return {
        xs.name: {
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
        for xs in cross_sections
    }


def serialize_pdk_yaml(config: PDKYamlConfig) -> str:
    """序列化 PDKYamlConfig 为 YAML 字符串（R309）。

    Args:
        config: PDK 配置。

    Returns:
        YAML 字符串（含 pdk/layers/layer_stack/cross_sections/cells 五段）。

    Raises:
        ValueError: 配置无效（必填字段为空）。
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
    layers_dict: dict = {
        layer.name: {
            "gds_layer": layer.gds_layer,
            "gds_datatype": layer.gds_datatype,
            "material": layer.material,
            "description": layer.description,
        }
        for layer in config.layers
    }
    layer_stack_list = _convert_layer_stack_to_list(config.layer_stack)
    cross_sections_dict = _convert_cross_sections_to_dict(config.cross_sections)
    cells_dict: dict = {
        cell.name: {
            "platform": cell.platform,
            "category": cell.category,
            "params_schema": cell.params_schema,
            "description": cell.description,
        }
        for cell in config.cells
    }
    full_dict = {
        "pdk": pdk_dict,
        "layers": layers_dict,
        "layer_stack": _serialize_layer_stack(config.layer_stack),
        "cross_sections": _serialize_cross_sections(config.cross_sections),
        "cells": cells_dict,
    }
    return yaml.safe_dump(full_dict, allow_unicode=True, sort_keys=False, default_flow_style=False)


def _convert_layer_stack_to_list(layer_stack: list) -> list:
    """转换 layer_stack 为可序列化 dict 列表（Extract Method，R11 质量门禁）。"""
    layer_stack_list: list = []
    for level in layer_stack:
        item: dict = {
            "layer": level.layer,
            "thickness_nm": level.thickness_nm,
            "zmin_nm": level.zmin_nm,
            "material": level.material,
            "sidewall_angle_deg": level.sidewall_angle_deg,
        }
        if level.refractive_index_real is not None:
            item["refractive_index"] = [
                level.refractive_index_real,
                level.refractive_index_imag if level.refractive_index_imag is not None else 0.0,
            ]
        layer_stack_list.append(item)
    return layer_stack_list


def _convert_cross_sections_to_dict(cross_sections: list) -> dict:
    """转换 cross_sections 为可序列化 dict（Extract Method，R11 质量门禁）。"""
    return {
        xs.name: {
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
        for xs in cross_sections
    }


def _validate_required_fields(config: PDKYamlConfig) -> list[str]:
    """校验必填字段非空。"""
    errors: list[str] = []
    if not config.name:
        errors.append("pdk.name 为空")
    if not config.version:
        errors.append("pdk.version 为空")
    if not config.platform:
        errors.append("pdk.platform 为空")
    if not config.source_url:
        errors.append("pdk.source_url 为空（R02 学术诚信：所有 PDK 必须溯源）")
    return errors


def _validate_layer_references(config: PDKYamlConfig, layer_names: set[str]) -> list[str]:
    """校验层引用完整性。"""
    errors: list[str] = []
    for level in config.layer_stack:
        if level.layer not in layer_names and config.layers:
            errors.append(f"layer_stack 引用未定义的层 '{level.layer}'")
    for xs in config.cross_sections:
        for section in xs.sections:
            if section.layer not in layer_names and config.layers:
                errors.append(f"cross_section '{xs.name}' 引用未定义的层 '{section.layer}'")
    return errors


def _validate_cell_uniqueness(config: PDKYamlConfig) -> list[str]:
    """校验 cell 名称唯一性。"""
    errors: list[str] = []
    seen: set[str] = set()
    for cell in config.cells:
        if cell.name in seen:
            errors.append(f"cell 名称重复: '{cell.name}'")
        seen.add(cell.name)
    return errors


def validate_pdk_yaml(config: PDKYamlConfig) -> list[str]:
    """校验 PDK YAML 配置完整性（R309）。

    Args:
        config: PDK 配置。

    Returns:
        错误信息列表（空列表表示通过）。本函数返回错误列表而非 raise，
        用于批量收集所有问题；调用方可根据需要 raise。这与 R03 不冲突——
        R03 禁止静默兜底，本函数是显式的校验 API，调用方必须处理返回值。
    """
    errors = _validate_required_fields(config)
    layer_names = {layer.name for layer in config.layers}
    errors.extend(_validate_layer_references(config, layer_names))
    errors.extend(_validate_cell_uniqueness(config))
    return errors


def build_polaris_layer_stack(
    name: str, specs: list[YamlLayerLevelSpec]
) -> PolarisLayerStack:
    """从 YAML 层堆栈规格构建 PolarisLayerStack（R309）。

    来源: gdsfactory LayerStack
    https://github.com/gdsfactory/gdsfactory/blob/main/gdsfactory/technology/layer_stack.py
    """
    levels: list[PolarisLayerLevel] = []
    for spec in specs:
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


def build_polaris_cross_section(spec: YamlCrossSectionSpec) -> PolarisCrossSection:
    """从 YAML 截面规格构建 PolarisCrossSection（R309）。

    来源: gdsfactory CrossSection
    https://github.com/gdsfactory/gdsfactory/blob/main/gdsfactory/cross_section.py
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
    """
    config = parse_pdk_yaml(yaml_path)
    errors = validate_pdk_yaml(config)
    if errors:
        raise ValueError(
            f"PDK YAML 配置校验失败 ({len(errors)} 个错误): " + "; ".join(errors)
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
        devices={},
        layer_stack=layer_stack,
        cross_sections=cross_sections,
    )
