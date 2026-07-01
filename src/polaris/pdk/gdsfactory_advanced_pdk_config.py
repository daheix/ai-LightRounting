"""R305 PDK 双向兼容增强 — SiEPIC/Generic/Custom 配置文件支持。

批次 10-B 拆分说明（2026-07-01）:
    从 gdsfactory_advanced.py（原 1337 行）抽出 R305 PDK 兼容配置模块。

来源（R02 学术诚信，≥5 文献 URL）:
1. gdsfactory PDK tutorial: https://gdsfactory.github.io/gdsfactory/notebooks/08_pdk.html
2. gdsfactory PDK import: https://gdsfactory.github.io/gdsfactory/notebooks/09_pdk_import.html
3. SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
4. Chrostowski & Hochberg, "Silicon Photonics Design", CUP 2015
   https://doi.org/10.1017/CBO9781316084168
5. gdsfactory generic PDK layer_stack:
   https://gdsfactory.github.io/gdsfactory/notebooks/03_layer_stack.html
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# gdsfactory generic PDK 层映射（文献 1: notebooks/03_layer_stack）
GENERIC_PDK_CONFIG: dict[str, Any] = {
    "pdk_name": "generic",
    "foundry": "gdsfactory generic (MIT)",
    "process_node": "SOI 220nm",
    "source_url": "https://gdsfactory.github.io/gdsfactory/notebooks/08_pdk.html",
    "layer_map": {
        "1,0": "WG",          # 220nm 硅核心
        "2,0": "SLAB150",     # 150nm slab（浅刻蚀）
        "3,0": "SLAB90",      # 90nm slab（调制器）
        "47,0": "HEATER",     # 加热电阻
        "41,0": "M1",         # 金属 1
        "45,0": "M2",         # 金属 2
        "66,0": "TEXT",       # 文本标注
        "68,0": "DEVREC",     # 器件识别（连接性检查）
        "1,10": "PORT",       # 光学端口 pin
        "1,11": "PORTE",      # 电学端口 pin
        "64,0": "FLOORPLAN",  # 掩膜底图
    },
    "port_layers": ["1,10", "1,11"],
    "cross_section_params": {"width_um": 0.5, "radius_um": 5.0},
}

# SiEPIC EBeam PDK 层映射（文献 3: SiEPIC_EBeam_PDK，兼容 generic 方案）
SIEPIC_PDK_CONFIG: dict[str, Any] = {
    "pdk_name": "siepic",
    "foundry": "AMF / UBC (SiEPIC EBeam)",
    "process_node": "AMF SOI 220nm",
    "source_url": "https://github.com/SiEPIC/SiEPIC_EBeam_PDK",
    "layer_map": {
        "1,0": "WG",
        "2,0": "SLAB150",
        "3,0": "SLAB90",
        "68,0": "DEVREC",
        "69,0": "PIN",        # SiEPIC 端口标记层
        "1,10": "PORT",
        "1,11": "PORTE",
        "66,0": "TEXT",
        "64,0": "FLOORPLAN",
    },
    "port_layers": ["1,10", "1,11"],
    "cross_section_params": {"width_um": 0.5, "radius_um": 5.0},
}

# 预设 PDK 配置注册表
_PRESET_PDK_CONFIGS: dict[str, dict[str, Any]] = {
    "generic": GENERIC_PDK_CONFIG,
    "siepic": SIEPIC_PDK_CONFIG,
}


@dataclass
class PDKCompatibilityConfig:
    """PDK 双向兼容配置（R305）。

    封装 SiEPIC/Generic/Custom PDK 的层映射、端口层、截面参数，
    使 PoLaRIS 与 gdsfactory PDK 双向兼容。

    Attributes:
        pdk_name: PDK 名（generic/siepic/自定义）。
        layer_map: GDS (layer,datatype) → 层名 映射。
        port_layers: 端口 pin 所在 GDS 层列表。
        cross_section_params: 截面参数（宽度/半径等）。
        foundry: 代工厂描述。
        process_node: 工艺节点。
        source_url: PDK 来源 URL（R02 溯源）。
    """

    pdk_name: str
    layer_map: dict[tuple[int, int], str]
    port_layers: list[tuple[int, int]]
    cross_section_params: dict[str, float]
    foundry: str = ""
    process_node: str = ""
    source_url: str = ""


def _parse_layer_key(key: str) -> tuple[int, int]:
    """将 '1,0' 字符串解析为 (1, 0) 元组。"""
    parts = key.split(",")
    if len(parts) != 2:
        raise ValueError(f"层键格式错误（应为 'layer,datatype'）: {key!r}")
    return (int(parts[0]), int(parts[1]))


def _config_dict_to_dataclass(d: dict[str, Any]) -> PDKCompatibilityConfig:
    """将原始 dict 配置转为 PDKCompatibilityConfig dataclass。"""
    layer_map = {(_parse_layer_key(k)): v for k, v in d["layer_map"].items()}
    port_layers = [_parse_layer_key(k) for k in d.get("port_layers", [])]
    return PDKCompatibilityConfig(
        pdk_name=d["pdk_name"],
        layer_map=layer_map,
        port_layers=port_layers,
        cross_section_params=dict(d.get("cross_section_params", {})),
        foundry=d.get("foundry", ""),
        process_node=d.get("process_node", ""),
        source_url=d.get("source_url", ""),
    )


def get_preset_pdk_config(name: str) -> PDKCompatibilityConfig:
    """获取预设 PDK 配置（generic/siepic）。

    Args:
        name: 预设名（generic/siepic）。

    Returns:
        PDKCompatibilityConfig 实例。

    Raises:
        KeyError: 预设名不存在（R03：不静默返回默认值）。
    """
    if name not in _PRESET_PDK_CONFIGS:
        raise KeyError(
            f"预设 PDK 不存在: {name!r}（可用: {sorted(_PRESET_PDK_CONFIGS)}）"
        )
    return _config_dict_to_dataclass(_PRESET_PDK_CONFIGS[name])


def load_pdk_config(yaml_path: str | Path) -> PDKCompatibilityConfig:
    """从 YAML 文件加载自定义 PDK 配置（R305）。

    YAML schema 见 PDKCompatibilityConfig 字段。层键格式 'layer,datatype'。

    Args:
        yaml_path: YAML 配置文件路径。

    Returns:
        PDKCompatibilityConfig 实例。

    Raises:
        FileNotFoundError: 文件不存在。
        ValueError: YAML 解析或字段缺失。
    """
    import yaml  # 局部导入，PyYAML 为项目既有依赖

    path = Path(yaml_path)
    if not path.exists():
        raise FileNotFoundError(f"PDK 配置文件不存在: {path}")
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        raise ValueError(f"YAML 解析失败: {e}") from e
    if not isinstance(raw, dict):
        raise ValueError(f"PDK 配置必须为 dict，实际为 {type(raw).__name__}")
    if "pdk_name" not in raw or "layer_map" not in raw:
        raise ValueError("PDK 配置缺少必填字段 'pdk_name' 或 'layer_map'")
    return _config_dict_to_dataclass(raw)


def save_pdk_config(config: PDKCompatibilityConfig, yaml_path: str | Path) -> None:
    """将 PDK 配置保存为 YAML 文件（R305）。

    Args:
        config: PDKCompatibilityConfig 实例。
        yaml_path: 输出 YAML 路径。

    Raises:
        OSError: 写入失败。
    """
    import yaml

    raw = {
        "pdk_name": config.pdk_name,
        "foundry": config.foundry,
        "process_node": config.process_node,
        "source_url": config.source_url,
        "layer_map": {f"{k[0]},{k[1]}": v for k, v in config.layer_map.items()},
        "port_layers": [f"{l[0]},{l[1]}" for l in config.port_layers],
        "cross_section_params": dict(config.cross_section_params),
    }
    Path(yaml_path).write_text(
        yaml.safe_dump(raw, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )


def merge_pdk_configs(
    base: PDKCompatibilityConfig, *overrides: PDKCompatibilityConfig
) -> PDKCompatibilityConfig:
    """合并多个 PDK 配置（后者覆盖前者同层定义，R305 跨 PDK 复用）。

    Args:
        base: 基础配置。
        *overrides: 覆盖配置（按顺序覆盖）。

    Returns:
        合并后的新配置。

    Raises:
        ValueError: 层映射冲突（同 (layer,datatype) 映射到不同层名）。
    """
    merged_layers = dict(base.layer_map)
    merged_ports = list(base.port_layers)
    merged_xs = dict(base.cross_section_params)
    pdk_name = base.pdk_name
    for ov in overrides:
        for lk, ln in ov.layer_map.items():
            if lk in merged_layers and merged_layers[lk] != ln:
                raise ValueError(
                    f"层映射冲突: {lk} 在 {pdk_name}={merged_layers[lk]} "
                    f"vs {ov.pdk_name}={ln}（R03：禁止静默覆盖）"
                )
            merged_layers[lk] = ln
        for pl in ov.port_layers:
            if pl not in merged_ports:
                merged_ports.append(pl)
        merged_xs.update(ov.cross_section_params)
        pdk_name = f"{pdk_name}+{ov.pdk_name}"
    return PDKCompatibilityConfig(
        pdk_name=pdk_name,
        layer_map=merged_layers,
        port_layers=merged_ports,
        cross_section_params=merged_xs,
        foundry=base.foundry,
        process_node=base.process_node,
        source_url=base.source_url,
    )


def validate_pdk_compatibility(config: PDKCompatibilityConfig) -> list[str]:
    """校验 PDK 配置完整性，返回问题列表（R305）。

    Args:
        config: PDKCompatibilityConfig 实例。

    Returns:
        问题描述列表（空列表表示通过）。
    """
    issues: list[str] = []
    if not config.pdk_name:
        issues.append("pdk_name 为空")
    if not config.layer_map:
        issues.append("layer_map 为空")
    # 端口层必须在层映射中
    for pl in config.port_layers:
        if pl not in config.layer_map:
            issues.append(f"端口层 {pl} 未在 layer_map 中定义")
    # 截面参数必填项
    if config.cross_section_params:
        if "width_um" not in config.cross_section_params:
            issues.append("cross_section_params 缺少 width_um")
        if "radius_um" not in config.cross_section_params:
            issues.append("cross_section_params 缺少 radius_um")
    return issues


__all__ = [
    "PDKCompatibilityConfig",
    "GENERIC_PDK_CONFIG",
    "SIEPIC_PDK_CONFIG",
    "get_preset_pdk_config",
    "load_pdk_config",
    "save_pdk_config",
    "merge_pdk_configs",
    "validate_pdk_compatibility",
]
