"""PCell ↔ gdsfactory Component 双向兼容（R306）。

实现 PoLaRIS PCellMultiView 与 gdsfactory Component 的双向转换，使
PoLaRIS 原生 PCell 可与 gdsfactory 生态互操作。

双向转换映射:
1. PCellMultiView → gdsfactory Component:
   - layout_view.polygons → component.add_polygon(layers)
   - layout_view.ports → component.add_port(name, center, orientation, width)
   - netlist_view → component.metadata['netlist']
   - params → component.metadata['polaris_params']

2. gdsfactory Component → PCellMultiView:
   - component.ports → layout_view.ports
   - component.bbox() → bbox（写入 params['bbox']）
   - component.metadata → PCellMultiView.info
   - 多边形几何需 GDSII 层提取（依赖 klayout，可选）

R03 合规设计:
- gdsfactory 不可用 raise ImportError（不静默兜底）
- PCell 无端口 raise ValueError（不返回空 Component）
- 层名不在层映射中 raise KeyError（不跳过）
- 几何参数无效 raise ValueError（不静默丢弃）

来源:
- gdsfactory Component API: https://gdsfactory.github.io/gdsfactory/api.html
- gdsfactory 多边形/端口: https://gdsfactory.github.io/gdsfactory/notebooks/01_geometry.html
- IPKISS PCell: https://www.lucedaphotonics.com/zh_CN/products/ipkiss
- Gamma et al., "Design Patterns", 1994（Adapter Pattern）
- PoLaRIS PCellMultiView: polaris.pdk.pcell.PCellMultiView
- gdsfactory @gf.cell: https://gdsfactory.github.io/gdsfactory/
- klayout Layer: https://www.klayout.de/doc-qt5/manual/classLayer.html
- gdsfactory 端口约定: https://gdsfactory.github.io/gdsfactory/notebooks/02_ports.html
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import numpy as np

from polaris.pdk.pcell import PCellMultiView
from polaris.pdk.port import Direction, Port

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


# =============================================================================
# 数据类定义
# =============================================================================
@dataclass
class PCellBridgeConfig:
    """PCell ↔ gdsfactory 转换配置（R306）。

    Attributes:
        default_layer: 默认 GDSII 层 (layer, datatype)，当 PCell 多边形未指定
            GDSII 层时使用。默认 (1, 0) 对应 SiEPIC WG 层。
        layer_map: PoLaRIS 层名 → GDSII (layer, datatype) 映射。
            默认使用 SiEPIC PDK 层映射（13 层）。
        port_width_default: 端口默认宽度（μm），当 Port.width 为 0 或未设置时使用。
        export_netlist: 是否导出 netlist_view 到 component.metadata['netlist']。
        export_params: 是否导出 PCell params 到 component.metadata['polaris_params']。

    默认值来源:
    - default_layer (1, 0): SiEPIC EBeam PDK WG 层
      来源: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
    - layer_map: SiEPIC 13 层标准映射
      来源: SiEPIC_EBeam_PDK/layers.klayout
    """

    default_layer: tuple[int, int] = (1, 0)
    layer_map: dict[str, tuple[int, int]] = field(default_factory=lambda: {
        "WG": (1, 0),
        "SLAB150": (2, 0),
        "SLAB90": (3, 0),
        "SiN": (4, 0),
        "METAL": (5, 0),
        "HEATER": (6, 0),
        "TEXT": (7, 0),
        "LABEL": (8, 0),
        "DEVREC": (68, 0),
        "PIN": (69, 0),
        "PORT": (70, 0),
        "FLOORPLAN": (99, 0),
        "PORT_GEOM": (71, 0),
    })
    port_width_default: float = 0.5
    export_netlist: bool = True
    export_params: bool = True


# =============================================================================
# 方向辅助函数
# =============================================================================
def direction_to_orientation(direction: Direction) -> float:
    """将 PoLaRIS Direction 转换为 gdsfactory 端口朝向角（度）。

    gdsfactory 端口朝向约定: 0°=东(+x), 90°=北(+y), 180°=西(-x), 270°=南(-y)
    PoLaRIS Direction: EAST=+x, NORTH=+y, WEST=-x, SOUTH=-y

    Args:
        direction: PoLaRIS Direction 枚举值。

    Returns:
        gdsfactory 朝向角（度）。

    Raises:
        ValueError: 未知 Direction。

    来源:
    - gdsfactory 端口朝向: https://gdsfactory.github.io/gdsfactory/notebooks/02_ports.html
    """
    mapping = {
        Direction.EAST: 0.0,
        Direction.NORTH: 90.0,
        Direction.WEST: 180.0,
        Direction.SOUTH: 270.0,
    }
    if direction not in mapping:
        raise ValueError(
            f"未知 Direction: {direction!r}，必须是 EAST/NORTH/WEST/SOUTH"
        )
    return mapping[direction]


def orientation_to_direction(orientation_deg: float) -> Direction:
    """将 gdsfactory 端口朝向角转换为 PoLaRIS Direction。

    朝向角四象限量化到最近的正方向（EAST/NORTH/WEST/SOUTH）。

    Args:
        orientation_deg: gdsfactory 朝向角（度）。

    Returns:
        PoLaRIS Direction 枚举值。

    来源:
    - gdsfactory 端口朝向: https://gdsfactory.github.io/gdsfactory/notebooks/02_ports.html
    """
    # 归一化到 [0, 360)
    angle = orientation_deg % 360.0
    # 四象限量化: [315, 45) → EAST, [45, 135) → NORTH, [135, 225) → WEST, [225, 315) → SOUTH
    if angle < 45.0 or angle >= 315.0:
        return Direction.EAST
    if angle < 135.0:
        return Direction.NORTH
    if angle < 225.0:
        return Direction.WEST
    return Direction.SOUTH


# =============================================================================
# PCellMultiView → gdsfactory Component
# =============================================================================
def pcell_to_gdsfactory_component(
    pcell: PCellMultiView,
    config: PCellBridgeConfig | None = None,
):
    """将 PoLaRIS PCellMultiView 转换为 gdsfactory Component（R306）。

    转换映射:
    - pcell.name → component.name
    - pcell.layout_view.polygons → component.add_polygon (layer 映射)
    - pcell.layout_view.ports → component.add_port (name/center/orientation/width)
    - pcell.netlist_view → component.metadata['netlist']（可选）
    - pcell.params → component.metadata['polaris_params']（可选）

    Args:
        pcell: PoLaRIS PCellMultiView 对象。
        config: 转换配置（None 用默认配置）。

    Returns:
        gdsfactory Component 对象。

    Raises:
        ImportError: gdsfactory 未安装。
        ValueError: PCell 无端口 / 多边形点数 < 3 / 层名未在 layer_map 中。
        KeyError: 层名未在 layer_map 中（R03 合规）。

    来源:
    - gdsfactory Component: https://gdsfactory.github.io/gdsfactory/api.html#gdsfactory.Component
    - gdsfactory add_polygon: https://gdsfactory.github.io/gdsfactory/notebooks/01_geometry.html
    - gdsfactory add_port: https://gdsfactory.github.io/gdsfactory/notebooks/02_ports.html
    """
    try:
        import gdsfactory as gf
    except ImportError as e:
        raise ImportError(
            "gdsfactory 未安装，无法将 PCell 转换为 gdsfactory Component。"
            "安装方式: pip install gdsfactory。"
            f"原始错误: {e}"
        ) from e

    cfg = config or PCellBridgeConfig()

    if not pcell.layout_view.ports:
        raise ValueError(
            f"PCell {pcell.name!r} 无端口，无法转换为 gdsfactory Component。"
            f"请先调用 pcell.add_port() 添加端口。"
        )

    component = gf.Component(name=pcell.name)

    # 步骤 1: 转换多边形
    for points, layer_name in pcell.layout_view.polygons:
        pts = np.asarray(points, dtype=float)
        if pts.shape[0] < 3:
            raise ValueError(
                f"多边形点数 {pts.shape[0]} < 3，无法构成多边形（layer={layer_name}）"
            )
        # 层名 → GDSII (layer, datatype)
        if layer_name in cfg.layer_map:
            gds_layer = cfg.layer_map[layer_name]
        elif layer_name == "default":
            gds_layer = cfg.default_layer
        else:
            raise KeyError(
                f"层名 {layer_name!r} 不在 layer_map 中。"
                f"可用层: {sorted(cfg.layer_map.keys())}。"
                f"请在 PCellBridgeConfig.layer_map 中添加该层，或使用 'default' 层名。"
            )
        component.add_polygon(pts, layer=gds_layer)

    # 步骤 2: 转换端口
    for port in pcell.layout_view.ports:
        orientation = direction_to_orientation(port.direction)
        width = port.width if port.width > 0 else cfg.port_width_default
        component.add_port(
            name=port.name,
            center=(port.x, port.y),
            orientation=orientation,
            width=width,
            port_type="optical",
        )

    # 步骤 3: 导出 netlist（可选）
    if cfg.export_netlist:
        component.metadata["netlist"] = pcell.get_netlist()

    # 步骤 4: 导出 params（可选）
    if cfg.export_params:
        component.metadata["polaris_params"] = dict(pcell.params)

    # 附加 info
    if pcell.info:
        component.metadata["polaris_info"] = dict(pcell.info)

    logger.info(
        "PCell→gdsfactory 转换完成: %s, %d 多边形, %d 端口",
        pcell.name,
        len(pcell.layout_view.polygons),
        len(pcell.layout_view.ports),
    )

    return component


# =============================================================================
# gdsfactory Component → PCellMultiView
# =============================================================================
def gdsfactory_component_to_pcell(
    component,
    config: PCellBridgeConfig | None = None,
) -> PCellMultiView:
    """将 gdsfactory Component 转换为 PoLaRIS PCellMultiView（R306）。

    转换映射:
    - component.name → pcell.name
    - component.ports → pcell.add_port (orientation → Direction 量化)
    - component.metadata → pcell.info
    - component.bbox() → pcell.params['bbox'] = (xmin, ymin, xmax, ymax)

    注: 多边形几何需通过 GDSII 文件中转（依赖 klayout 读取），
    本函数不提取多边形，仅提取端口和 metadata。如需多边形，请使用
    ``gdsfactory_to_polaris_device`` 走 GDSII 路径。

    Args:
        component: gdsfactory Component 对象。
        config: 转换配置（None 用默认配置）。

    Returns:
        PoLaRIS PCellMultiView 对象。

    Raises:
        ValueError: 组件无端口 / 端口名重复 / 端口朝向无法量化。
        AttributeError: component 缺少必需属性（.name/.ports）。

    来源:
    - gdsfactory Component.ports: https://gdsfactory.github.io/gdsfactory/api.html
    - gdsfactory Component.metadata: https://gdsfactory.github.io/gdsfactory/api.html
    - PoLaRIS PCellMultiView: polaris.pdk.pcell.PCellMultiView
    """
    cfg = config or PCellBridgeConfig()

    name = getattr(component, "name", None) or "gdsfactory_component"
    pcell = PCellMultiView(name=name, params={})

    # 步骤 1: 转换端口
    ports = list(component.ports) if hasattr(component, "ports") else []
    if not ports:
        raise ValueError(
            f"gdsfactory Component {name!r} 无端口，无法转换为 PCell。"
            f"请确保组件已定义端口（component.add_port()）。"
        )
    seen_names = _convert_gdsfactory_ports(pcell, ports, cfg)

    # 步骤 2: 转换 metadata → info
    metadata = getattr(component, "metadata", {}) or {}
    _convert_gdsfactory_metadata(pcell, metadata)

    # 步骤 3: 提取 bbox（可选信息）
    _convert_gdsfactory_bbox(pcell, component)

    logger.info(
        "gdsfactory→PCell 转换完成: %s, %d 端口",
        name,
        len(seen_names),
    )

    return pcell


def _convert_gdsfactory_ports(
    pcell: PCellMultiView,
    ports: list,
    cfg: "PCellBridgeConfig",
) -> set[str]:
    """将 gdsfactory 端口列表转换为 PCell 端口（CC ≤ 6）。"""
    seen_names: set[str] = set()
    for port in ports:
        port_name = getattr(port, "name", None) or f"o{len(seen_names) + 1}"
        if port_name in seen_names:
            raise ValueError(
                f"端口名 {port_name!r} 重复。"
                f"gdsfactory Component 的端口名必须唯一。"
            )
        seen_names.add(port_name)

        x, y = _extract_port_center(port)
        orientation = float(getattr(port, "orientation", 0.0) or 0.0)
        direction = orientation_to_direction(orientation)
        width = float(getattr(port, "width", cfg.port_width_default))

        pcell.add_port(
            name=port_name,
            x=x, y=y,
            direction=direction,
            width=width,
        )
    return seen_names


def _extract_port_center(port) -> tuple[float, float]:
    """从 gdsfactory port 对象提取 (x, y) 坐标（兼容 Port/NamedTuple 两种格式）。"""
    center = getattr(port, "center", (0.0, 0.0))
    if hasattr(center, "x"):
        return float(center.x), float(center.y)
    return float(center[0]), float(center[1])


def _convert_gdsfactory_metadata(
    pcell: PCellMultiView,
    metadata: dict,
) -> None:
    """转换 gdsfactory metadata → PCell.info，并提取 polaris_params（CC ≤ 4）。"""
    for key, value in metadata.items():
        # 跳过已处理的关键字段
        if key in ("netlist", "polaris_params"):
            continue
        pcell.info[key] = value

    # 提取 polaris_params（如果原 PCell 转换而来）
    if "polaris_params" in metadata:
        pcell.params.update(metadata["polaris_params"])


def _convert_gdsfactory_bbox(pcell: PCellMultiView, component) -> None:
    """提取 component.bbox() 到 pcell.params['bbox']（可选，失败静默跳过）。"""
    bbox_fn = getattr(component, "bbox", None)
    if not callable(bbox_fn):
        return
    bbox = bbox_fn()
    extracted = _extract_bbox_tuple(bbox)
    if extracted is not None:
        pcell.params["bbox"] = extracted


def _extract_bbox_tuple(bbox) -> tuple[float, float, float, float] | None:
    """从 klayout Box / list/tuple 提取 (xmin, ymin, xmax, ymax)。"""
    # klayout Box 有 left/bottom/right/top 属性
    if hasattr(bbox, "left"):
        return (
            float(bbox.left), float(bbox.bottom),
            float(bbox.right), float(bbox.top),
        )
    # 某些版本的 bbox 返回 list/tuple
    if hasattr(bbox, "__iter__"):
        bbox_list = list(bbox)
        if len(bbox_list) >= 4:
            return tuple(float(v) for v in bbox_list[:4])
    # bbox 为 None 或无 left/__iter__ 属性时跳过（不强求）
    return None


# =============================================================================
# 往返一致性验证
# =============================================================================
def pcell_round_trip(
    pcell: PCellMultiView,
    config: PCellBridgeConfig | None = None,
) -> tuple:
    """PCell → gdsfactory Component → PCell 往返转换，验证一致性（R306）。

    用于验证双向转换的数据完整性。返回往返后的 PCell 和差异报告。

    一致性检查:
    - 端口数一致
    - 端口名一致（集合相等）
    - 端口位置一致（容差 1e-6 μm）
    - 端口宽度一致（容差 1e-6 μm）
    - 端口方向一致（Direction 相同）

    Args:
        pcell: 原始 PCellMultiView。
        config: 转换配置。

    Returns:
        (往返后的 PCell, 差异报告 dict)。
        差异报告 keys: 'port_count_match', 'port_names_match',
        'port_positions_match', 'port_directions_match'。

    Raises:
        ImportError: gdsfactory 未安装。
        ValueError: 原始 PCell 无端口 / 往返后端口数不一致（R03 合规）。

    来源:
    - gdsfactory 往返测试: https://gdsfactory.github.io/gdsfactory/notebooks/01_geometry.html
    """
    cfg = config or PCellBridgeConfig()

    # 正向: PCell → gdsfactory
    component = pcell_to_gdsfactory_component(pcell, cfg)

    # 反向: gdsfactory → PCell
    pcell_back = gdsfactory_component_to_pcell(component, cfg)

    # 一致性检查
    original_ports = {p.name: p for p in pcell.layout_view.ports}
    roundtrip_ports = {p.name: p for p in pcell_back.layout_view.ports}

    diff: dict[str, Any] = {
        "port_count_match": len(original_ports) == len(roundtrip_ports),
        "port_names_match": set(original_ports.keys()) == set(roundtrip_ports.keys()),
        "port_positions_match": True,
        "port_directions_match": True,
        "port_widths_match": True,
    }

    if diff["port_names_match"]:
        for name, orig_port in original_ports.items():
            rt_port = roundtrip_ports[name]
            # 位置容差 1e-6 μm
            if abs(orig_port.x - rt_port.x) > 1e-6 or abs(orig_port.y - rt_port.y) > 1e-6:
                diff["port_positions_match"] = False
            # 方向一致
            if orig_port.direction != rt_port.direction:
                diff["port_directions_match"] = False
            # 宽度一致
            if abs(orig_port.width - rt_port.width) > 1e-6:
                diff["port_widths_match"] = False

    if not diff["port_count_match"]:
        raise ValueError(
            f"往返转换端口数不一致: 原始 {len(original_ports)} vs 往返 {len(roundtrip_ports)}"
        )

    return pcell_back, diff


__all__ = [
    "PCellBridgeConfig",
    "direction_to_orientation",
    "gdsfactory_component_to_pcell",
    "orientation_to_direction",
    "pcell_round_trip",
    "pcell_to_gdsfactory_component",
]
