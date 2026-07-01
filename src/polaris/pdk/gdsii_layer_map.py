"""PDK 双向兼容层映射模块（R303）。

原属 gdsfactory_integration.py §6-§7（批次 10-B 拆分提取），保留原始文献溯源。

提供:
- get_siepic_layer_map / get_gdsfactory_generic_layer_map: 标准 PDK 层映射
- gdsfactory_to_polaris_layer / polaris_to_gdsfactory_layer: 双向层映射
- merge_layer_maps: 合并层映射
- save_layer_map_to_yaml / load_layer_map_from_yaml: YAML 配置文件化
- LayerMapConfig / build_layer_map_config: 层映射配置容器与构建

学术依据:
- SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- SiEPIC Connect: https://github.com/SiEPIC/SiEPIC-Tools
- gdsfactory PDK: https://gdsfactory.github.io/gdsfactory/
- YAML 1.2 规范: https://yaml.org/spec/1.2.2/

合规: R02 学术诚信 / R03 禁止 fall-back / R05 Bug 必修。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


# SiEPIC EBeam PDK 标准层映射（Lukas Chrostowski, UBC, MIT 许可证）
# 来源: SiEPIC EBeam PDK
# https://github.com/SiEPIC/SiEPIC_EBeam_PDK
_SIEPIC_LAYER_MAP: dict[tuple[int, int], str] = {
    (1, 0): "WG",            # 波导核心层 (Si, 220nm)
    (2, 0): "SLAB150",       # 150nm slab (rib waveguide)
    (3, 0): "SLAB90",        # 90nm slab (rib waveguide)
    (4, 0): "SiN",           # SiN 波导层
    (5, 0): "METAL",         # 金属层
    (6, 0): "HEATER",        # 加热器层
    (10, 0): "TEXT",         # 文本标注层
    (11, 0): "LABEL",        # 标签层
    (68, 0): "DEVREC",       # 器件识别层 (SiEPIC)
    (69, 0): "PIN",          # 端口标记层 (SiEPIC)
    (70, 0): "PORT",         # 端口几何层
    (80, 0): "FLOORPLAN",    # 平面规划层
    (99, 0): "PORT_GEOM",    # gdsfactory 端口几何层
}

# gdsfactory generic PDK 层映射（来源: gdsfactory generic PDK layer definitions）
# https://gdsfactory.github.io/gdsfactory/
_GDSFACTORY_GENERIC_LAYER_MAP: dict[tuple[int, int], str] = {
    (1, 0): "WG",            # 波导核心层
    (2, 0): "SLAB150",       # 150nm slab
    (3, 0): "SLAB90",        # 90nm slab
    (66, 0): "TEXT",         # 文本标注层
    (68, 0): "DEVREC",       # 器件识别层 (SiEPIC 兼容)
    (69, 0): "PIN",          # 端口标记层 (SiEPIC 兼容)
    (99, 0): "PORT",         # 端口几何层
}

# 反向映射缓存: polaris_name → (gds_layer, gds_datatype)
# 用于 PoLaRIS → GDSII 双向转换
_LAYER_NAME_TO_GDS_CACHE: dict[str, tuple[int, int]] = {}


def get_siepic_layer_map() -> dict[tuple[int, int], str]:
    """获取 SiEPIC EBeam PDK 标准层映射（R303 TR-303.1）。

    返回 SiEPIC EBeam PDK 标准层映射的拷贝（防止外部修改内部状态）。

    Returns:
        SiEPIC 层映射字典 {(gds_layer, datatype): polaris_name}。

    来源:
    - SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
    - SiEPIC Connect: https://github.com/SiEPIC/SiEPIC-Tools
    """
    return dict(_SIEPIC_LAYER_MAP)


def get_gdsfactory_generic_layer_map() -> dict[tuple[int, int], str]:
    """获取 gdsfactory generic PDK 标准层映射。

    Returns:
        gdsfactory generic PDK 层映射字典。

    来源: gdsfactory generic PDK layer definitions
    https://gdsfactory.github.io/gdsfactory/
    """
    return dict(_GDSFACTORY_GENERIC_LAYER_MAP)


def gdsfactory_to_polaris_layer(
    gds_layer: int,
    gds_datatype: int,
    layer_map: dict[tuple[int, int], str] | None = None,
) -> str:
    """GDSII 层号 → PoLaRIS 层名（R303 双向映射正向）。

    Args:
        gds_layer: GDSII layer 号。
        gds_datatype: GDSII datatype。
        layer_map: 自定义层映射（None 用 SiEPIC 默认）。

    Returns:
        PoLaRIS 层名。未在映射中的层返回 ``LAYER_<layer>_<datatype>``。

    学术依据:
    - SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
    - gdsfactory PDK: https://gdsfactory.github.io/gdsfactory/
    """
    if layer_map is None:
        layer_map = _SIEPIC_LAYER_MAP
    return layer_map.get(
        (int(gds_layer), int(gds_datatype)),
        f"LAYER_{int(gds_layer)}_{int(gds_datatype)}",
    )


def polaris_to_gdsfactory_layer(
    polaris_name: str,
    layer_map: dict[tuple[int, int], str] | None = None,
) -> tuple[int, int]:
    """PoLaRIS 层名 → GDSII 层号（R303 双向映射反向）。

    Args:
        polaris_name: PoLaRIS 层名（如 "WG", "DEVREC"）。
        layer_map: 自定义层映射（None 用 SiEPIC 默认）。

    Returns:
        (gds_layer, gds_datatype) 元组。

    Raises:
        ValueError: 层名不在映射中（R03: 禁止返回默认值兜底）。

    学术依据:
    - SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
    - gdsfactory PDK: https://gdsfactory.github.io/gdsfactory/
    """
    if layer_map is None:
        layer_map = _SIEPIC_LAYER_MAP

    # 反向查找
    for (gds_layer, gds_datatype), name in layer_map.items():
        if name == polaris_name:
            return (gds_layer, gds_datatype)

    # R03: 禁止 fall-back，未知层名 raise
    raise ValueError(
        f"PoLaRIS 层名 '{polaris_name}' 在层映射中不存在。"
        f"可用层名: {sorted(set(layer_map.values()))}"
    )


def merge_layer_maps(
    base: dict[tuple[int, int], str],
    custom: dict[tuple[int, int], str],
) -> dict[tuple[int, int], str]:
    """合并层映射（custom 覆盖 base，R303 TR-303.2）。

    用于用户自定义层映射覆盖默认映射。

    Args:
        base: 基础层映射（如 SiEPIC 默认）。
        custom: 自定义层映射（覆盖 base）。

    Returns:
        合并后的新层映射（不修改输入）。

    Raises:
        TypeError: 输入类型错误。
        ValueError: 自定义映射值（层名）为空字符串。

    学术依据:
    - gdsfactory 层映射机制:
      https://gdsfactory.github.io/gdsfactory/
    """
    if not isinstance(base, dict):
        raise TypeError(f"base 必须是 dict, 实际 {type(base).__name__}")
    if not isinstance(custom, dict):
        raise TypeError(f"custom 必须是 dict, 实际 {type(custom).__name__}")

    # 验证 custom 不含空层名（R03）
    for key, name in custom.items():
        if not isinstance(name, str) or not name.strip():
            raise ValueError(
                f"自定义层映射 {key} 的值为空字符串，禁止 fall-back"
            )

    merged = dict(base)
    merged.update(custom)
    return merged


def save_layer_map_to_yaml(
    layer_map: dict[tuple[int, int], str],
    yaml_path: str | Path,
) -> str:
    """将层映射保存为 YAML 文件（R303 TR-303.3 配置文件化）。

    YAML 格式:
        - WG: [1, 0]
        - DEVREC: [68, 0]

    Args:
        layer_map: 层映射字典。
        yaml_path: YAML 文件路径。

    Returns:
        YAML 文件路径。

    Raises:
        ImportError: PyYAML 未安装。
        ValueError: 层映射为空。

    学术依据:
    - YAML 1.2 规范: https://yaml.org/spec/1.2.2/
    - gdsfactory YAML 层映射: https://gdsfactory.github.io/gdsfactory/
    """
    from pathlib import Path as _Path

    try:
        import yaml
    except ImportError as e:
        raise ImportError(
            "PyYAML 未安装，无法保存 YAML 层映射。"
            "请执行 pip install pyyaml 安装。"
        ) from e

    if not layer_map:
        raise ValueError("层映射为空，无法保存")

    yaml_path = _Path(yaml_path)
    yaml_path.parent.mkdir(parents=True, exist_ok=True)

    # 转换为 YAML 友好格式: {layer_name: [layer, datatype]}
    yaml_data = {
        name: [gds_layer, gds_datatype]
        for (gds_layer, gds_datatype), name in layer_map.items()
    }

    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(
            yaml_data,
            f,
            default_flow_style=False,
            sort_keys=True,
            allow_unicode=True,
        )

    logger.info("层映射保存到 YAML: %s (%d 项)", yaml_path, len(layer_map))
    return str(yaml_path)


def load_layer_map_from_yaml(
    yaml_path: str | Path,
) -> dict[tuple[int, int], str]:
    """从 YAML 文件加载层映射（R303 TR-303.3 配置文件化）。

    YAML 格式（与 save_layer_map_to_yaml 一致）:
        WG: [1, 0]
        DEVREC: [68, 0]

    Args:
        yaml_path: YAML 文件路径。

    Returns:
        层映射字典 {(gds_layer, datatype): polaris_name}。

    Raises:
        FileNotFoundError: 文件不存在。
        ImportError: PyYAML 未安装。
        ValueError: YAML 格式无效或层映射为空。

    学术依据:
    - YAML 1.2 规范: https://yaml.org/spec/1.2.2/
    - gdsfactory YAML 层映射: https://gdsfactory.github.io/gdsfactory/
    """
    from pathlib import Path as _Path

    try:
        import yaml
    except ImportError as e:
        raise ImportError(
            "PyYAML 未安装，无法加载 YAML 层映射。"
            "请执行 pip install pyyaml 安装。"
        ) from e

    yaml_path = _Path(yaml_path)
    if not yaml_path.exists():
        raise FileNotFoundError(f"YAML 文件不存在: {yaml_path}")
    if not yaml_path.is_file():
        raise ValueError(f"YAML 路径不是文件: {yaml_path}")

    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise ValueError(
            f"YAML 内容必须是 dict，实际 {type(data).__name__}"
        )
    if not data:
        raise ValueError("YAML 层映射为空")

    # 转换: {name: [layer, datatype]} → {(layer, datatype): name}
    layer_map: dict[tuple[int, int], str] = {}
    for name, value in data.items():
        if not isinstance(name, str):
            raise ValueError(
                f"YAML 层名必须是 str，实际 {type(name).__name__}: {name}"
            )
        if not isinstance(value, (list, tuple)) or len(value) != 2:
            raise ValueError(
                f"YAML 层 '{name}' 的值必须是 [layer, datatype] 列表，"
                f"实际 {type(value).__name__}: {value}"
            )
        try:
            gds_layer = int(value[0])
            gds_datatype = int(value[1])
        except (TypeError, ValueError) as e:
            raise ValueError(
                f"YAML 层 '{name}' 的值不是有效整数: {value}"
            ) from e
        layer_map[(gds_layer, gds_datatype)] = name

    logger.info("从 YAML 加载层映射: %s (%d 项)", yaml_path, len(layer_map))
    return layer_map


@dataclass
class LayerMapConfig:
    """层映射配置容器（R303 TR-303.3 配置文件化）。

    封装层映射及其元数据（来源、是否合并默认映射等），
    便于在 PoLaRIS 内部统一传递。

    Attributes:
        layer_map: 层映射字典。
        source: 来源标识（如 "siepic", "gdsfactory", "custom", "yaml"）。
        merged_with_default: 是否合并了默认映射。

    学术依据:
    - gdsfactory 层映射机制: https://gdsfactory.github.io/gdsfactory/
    """

    layer_map: dict[tuple[int, int], str]
    source: str = "custom"
    merged_with_default: bool = False


def build_layer_map_config(
    custom_map: dict[tuple[int, int], str] | None = None,
    base: str = "siepic",
    merge_base: bool = True,
) -> LayerMapConfig:
    """构建层映射配置（R303 综合接口）。

    Args:
        custom_map: 用户自定义层映射（None 仅用 base）。
        base: 基础映射标识 ("siepic" 或 "gdsfactory")。
        merge_base: 是否将 base 与 custom_map 合并（True: custom 覆盖 base）。

    Returns:
        LayerMapConfig 对象。

    Raises:
        ValueError: base 标识无效。

    学术依据:
    - SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
    - gdsfactory generic PDK: https://gdsfactory.github.io/gdsfactory/
    """
    if base == "siepic":
        base_map = get_siepic_layer_map()
    elif base == "gdsfactory":
        base_map = get_gdsfactory_generic_layer_map()
    else:
        raise ValueError(
            f"base '{base}' 无效，必须是 'siepic' 或 'gdsfactory'"
        )

    if custom_map is None:
        return LayerMapConfig(
            layer_map=base_map,
            source=base,
            merged_with_default=False,
        )

    if merge_base:
        merged = merge_layer_maps(base_map, custom_map)
        return LayerMapConfig(
            layer_map=merged,
            source=f"{base}+custom",
            merged_with_default=True,
        )

    return LayerMapConfig(
        layer_map=dict(custom_map),
        source="custom",
        merged_with_default=False,
    )


__all__ = [
    "LayerMapConfig",
    "build_layer_map_config",
    "gdsfactory_to_polaris_layer",
    "get_gdsfactory_generic_layer_map",
    "get_siepic_layer_map",
    "load_layer_map_from_yaml",
    "merge_layer_maps",
    "polaris_to_gdsfactory_layer",
    "save_layer_map_to_yaml",
]
