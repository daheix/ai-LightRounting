"""GDSII 端口提取工具（R332，GDSII Port Extractor）。

从 GDSII 文件的端口层（PORT/PIN/PORT_GEOM）提取端口几何信息，
并关联文本层（TEXT/LABEL）的端口名，用于布局布线的端口对接。

## 核心概念

- **端口层（Port Layer）**: 标记端口位置的几何层
  - SiEPIC: PIN=(69,0), PORT=(70,0)
  - gdsfactory: PORT_GEOM=(99,0)
- **文本层（Text Layer）**: 端口名标签层
  - SiEPIC: TEXT=(10,0), LABEL=(11,0)
- **端口匹配**: 用空间邻近将文本标签关联到最近的端口几何

## 算法

1. 读取 GDSII 文件
2. 从 port_layers 提取端口几何（box/polygon），递归遍历顶层 cell
3. 每个端口几何计算: 中心点、bbox、宽高
4. 从 text_layers 提取文本标签（位置、内容）
5. 对每个端口，查找距离最近的文本标签（距离 ≤ match_distance_um）
6. 返回端口列表

## KLayout 0.30.9 API 关键事实（实测）

- Cell.begin_shapes_rec(li): 递归迭代 ShapeIterator（含子 cell）
- Shape.is_box() / Shape.bbox(): 判断/获取 Box
- Shape.is_polygon() / Shape.polygon: 判断/获取 Polygon
- Shape.is_text() / Shape.text_string / Shape.text_pos: 文本
- Box.left/right/bottom/top: bbox 边界（dbu）
- Polygon.bbox(): polygon 的 bbox（dbu）
- Layout.dbu: 数据库单位（μm）

## 学术依据

- KLayout Cell.begin_shapes_rec:
  https://www.klayout.org/doc-qt5/code/class_Cell.html
- KLayout Shape class:
  https://www.klayout.org/doc-qt5/code/class_Shape.html
- KLayout Box class:
  https://www.klayout.org/doc-qt5/code/class_Box.html
- KLayout Database API:
  https://klayout.org/downloads/master/doc-qt5/programming/database_api.html
- GDSII 格式:
  https://en.wikipedia.org/wiki/GDS_File
- SiEPIC EBeam PDK 端口定义:
  https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- gdsfactory Port 定义:
  https://gdsfactory.github.io/gdsfactory/api.html#gdsfactory.Port
- KLayout 文本提取:
  https://www.klayout.org/doc-qt4/code/class_Shape.html
- 最近邻匹配（Nearest Neighbor）:
  https://en.wikipedia.org/wiki/Nearest_neighbor_search

合规: R01 / R02 / R03 / R04 / R05 / R11。
"""

from __future__ import annotations

import json
import logging
import math
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

__all__ = [
    "PortInfo",
    "PortReport",
    "extract_ports",
    "generate_port_report",
]


# =============================================================================
# 默认层配置（SiEPIC EBeam PDK + gdsfactory）
# =============================================================================
# 来源: SiEPIC EBeam PDK https://github.com/SiEPIC/SiEPIC_EBeam_PDK
# 来源: gdsfactory https://gdsfactory.github.io/gdsfactory/
DEFAULT_PORT_LAYERS: list[tuple[int, int]] = [
    (70, 0),  # PORT (SiEPIC)
    (69, 0),  # PIN (SiEPIC)
    (99, 0),  # PORT_GEOM (gdsfactory)
]
DEFAULT_TEXT_LAYERS: list[tuple[int, int]] = [
    (10, 0),  # TEXT (SiEPIC)
    (11, 0),  # LABEL (SiEPIC)
]
DEFAULT_MATCH_DISTANCE_UM: float = 5.0


# =============================================================================
# 内部 KLayout 导入
# =============================================================================
def _import_klayout_db():
    """导入 klayout.db，未安装 raise ImportError（R03）。"""
    try:
        import klayout.db as db
    except ImportError as e:
        raise ImportError(
            "klayout 未安装，无法执行 GDSII 端口提取。"
            "安装方式: pip install klayout。"
            f"原始错误: {e}"
        ) from e
    return db


# =============================================================================
# 数据类
# =============================================================================
@dataclass
class PortInfo:
    """单个端口信息（R332）。

    Attributes:
        name: 端口名（匹配到的文本标签，无匹配为空字符串）。
        layer: GDSII 层号。
        datatype: GDSII datatype。
        position_um: 端口中心位置 (x, y) μm。
        bbox_um: 端口 bbox (xmin, ymin, xmax, ymax) μm。
        width_um: 端口宽度（μm）。
        height_um: 端口高度（μm）。
        cell_name: 端口所在 cell 名。
        text_matched: 是否成功匹配到文本标签。
    """

    name: str = ""
    layer: int = 0
    datatype: int = 0
    position_um: tuple[float, float] = (0.0, 0.0)
    bbox_um: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    width_um: float = 0.0
    height_um: float = 0.0
    cell_name: str = ""
    text_matched: bool = False


@dataclass
class PortReport:
    """GDSII 端口提取报告（R332）。

    Attributes:
        file_path: GDSII 文件路径。
        top_cell_name: 顶层 cell 名。
        dbu: 数据库单位（μm）。
        ports: 端口列表 PortInfo。
        port_layers: 使用的端口层列表。
        text_layers: 使用的文本层列表。
        match_distance_um: 文本匹配距离阈值（μm）。
    """

    file_path: str = ""
    top_cell_name: str = ""
    dbu: float = 0.0
    ports: list[PortInfo] = field(default_factory=list)
    port_layers: list[tuple[int, int]] = field(default_factory=list)
    text_layers: list[tuple[int, int]] = field(default_factory=list)
    match_distance_um: float = 0.0


# =============================================================================
# 端口提取主入口
# =============================================================================
def extract_ports(
    gds_path: str | Path,
    port_layers: list[tuple[int, int]] | None = None,
    text_layers: list[tuple[int, int]] | None = None,
    top_cell_name: str | None = None,
    match_distance_um: float | None = None,
) -> PortReport:
    """从 GDSII 提取端口信息（R332）。

    从端口层提取端口几何，并关联文本层的端口名。

    Args:
        gds_path: GDSII 文件路径。
        port_layers: 端口层列表（None 用默认 SiEPIC+gdsfactory）。
        text_layers: 文本层列表（None 用默认 SiEPIC）。
        top_cell_name: 顶层 cell 名（None 用第一个 top cell）。
        match_distance_um: 文本匹配距离阈值 μm（None 用 5.0）。
            端口几何与文本标签距离 ≤ 此值才匹配。

    Returns:
        PortReport 端口提取报告。

    Raises:
        FileNotFoundError: 文件不存在。
        ValueError: 文件无效 / top_cell_name 不存在 / 无 cell /
            match_distance_um <= 0 / port_layers 空。
        ImportError: klayout 未安装。
        RuntimeError: 读取失败。

    来源:
    - KLayout Cell.begin_shapes_rec:
      https://www.klayout.org/doc-qt5/code/class_Cell.html
    - SiEPIC EBeam PDK 端口:
      https://github.com/SiEPIC/SiEPIC_EBeam_PDK
    """
    db = _import_klayout_db()
    path = Path(gds_path)
    if not path.exists():
        raise FileNotFoundError(f"GDSII 文件不存在: {gds_path}")
    if not path.is_file():
        raise ValueError(f"路径不是文件: {gds_path}")

    if port_layers is None:
        port_layers = list(DEFAULT_PORT_LAYERS)
    if text_layers is None:
        text_layers = list(DEFAULT_TEXT_LAYERS)
    if not port_layers:
        raise ValueError(
            "port_layers 不能为空。禁止 fall-back（R03）。"
        )
    if match_distance_um is None:
        match_distance_um = DEFAULT_MATCH_DISTANCE_UM
    if match_distance_um <= 0:
        raise ValueError(
            f"match_distance_um ({match_distance_um}) 必须 > 0。"
            f"禁止 fall-back（R03）。"
        )

    ly = db.Layout()
    try:
        ly.read(str(path))
    except Exception as e:
        raise RuntimeError(
            f"klayout 读取文件失败: {type(e).__name__}: {e}。"
            f"禁止 fall-back（R03）。"
        ) from e

    dbu = float(ly.dbu)

    # 获取顶层 cell
    top_cell_indices = list(ly.each_top_cell())
    if not top_cell_indices:
        raise ValueError(
            f"GDSII 文件 {gds_path} 无顶层 cell，文件可能为空或损坏"
        )

    if top_cell_name is not None:
        top_cell_obj = ly.cell(top_cell_name)
        if top_cell_obj is None:
            available = sorted(ly.cell(ci).name for ci in ly.each_top_cell())
            raise ValueError(
                f"top_cell_name '{top_cell_name}' 不存在。"
                f"可用顶层 cells: {available}"
            )
        top_cell = top_cell_obj
    else:
        top_cell = ly.cell(top_cell_indices[0])

    top_cell_name_str = str(top_cell.name)

    # 收集端口几何（递归遍历顶层 cell）
    # RecursiveShapeIterator: at_end() / next() / shape() / cell()
    # 来源: https://www.klayout.org/doc-qt4/code/class_RecursiveShapeIterator.html
    ports: list[PortInfo] = []
    for (layer_num, datatype) in port_layers:
        li = _find_layer(ly, layer_num, datatype)
        if li is None:
            continue  # 该层不存在，跳过（非错误，文件可能无此层）
        it = top_cell.begin_shapes_rec(li)
        while not it.at_end():
            shape = it.shape()
            port = _shape_to_port(shape, layer_num, datatype, dbu, top_cell_name_str)
            if port is not None:
                ports.append(port)
            it.next()

    # 收集文本标签
    texts: list[tuple[str, float, float]] = []  # (text, x_um, y_um)
    for (layer_num, datatype) in text_layers:
        li = _find_layer(ly, layer_num, datatype)
        if li is None:
            continue
        it = top_cell.begin_shapes_rec(li)
        while not it.at_end():
            shape = it.shape()
            if shape.is_text():
                text_str = str(shape.text_string)
                pos = shape.text_pos
                x_um = float(pos.x) * dbu
                y_um = float(pos.y) * dbu
                texts.append((text_str, x_um, y_um))
            it.next()

    # 文本匹配：对每个端口找最近的文本
    for port in ports:
        best_name = ""
        best_dist = float("inf")
        px, py = port.position_um
        for (text_str, tx, ty) in texts:
            dist = math.hypot(px - tx, py - ty)
            if dist < best_dist:
                best_dist = dist
                best_name = text_str
        if best_name and best_dist <= match_distance_um:
            port.name = best_name
            port.text_matched = True

    logger.info(
        "GDSII 端口提取: %s (%d 端口, %d 文本标签)",
        path, len(ports), len(texts),
    )

    return PortReport(
        file_path=str(gds_path),
        top_cell_name=top_cell_name_str,
        dbu=dbu,
        ports=ports,
        port_layers=port_layers,
        text_layers=text_layers,
        match_distance_um=match_distance_um,
    )


# =============================================================================
# 报告生成
# =============================================================================
def generate_port_report(
    gds_path: str | Path,
    port_layers: list[tuple[int, int]] | None = None,
    text_layers: list[tuple[int, int]] | None = None,
    top_cell_name: str | None = None,
    match_distance_um: float | None = None,
    output_format: str = "text",
) -> str:
    """生成 GDSII 端口提取报告字符串（R332）。

    Args:
        gds_path: GDSII 文件路径。
        port_layers: 端口层列表。
        text_layers: 文本层列表。
        top_cell_name: 顶层 cell 名。
        match_distance_um: 文本匹配距离阈值 μm。
        output_format: 输出格式（'text' / 'markdown' / 'json'）。

    Returns:
        报告字符串。

    Raises:
        ValueError: 不支持的格式 / 参数无效。
        FileNotFoundError: 文件不存在。
        ImportError: klayout 未安装。

    来源:
    - CommonMark: https://spec.commonmark.org/
    - JSON: https://www.json.org/
    """
    report = extract_ports(
        gds_path,
        port_layers=port_layers,
        text_layers=text_layers,
        top_cell_name=top_cell_name,
        match_distance_um=match_distance_um,
    )
    fmt = output_format.lower()
    if fmt == "text":
        return _render_text_report(report)
    if fmt == "markdown":
        return _render_markdown_report(report)
    if fmt == "json":
        return _render_json_report(report)
    raise ValueError(
        f"不支持的 output_format: {output_format}。"
        f"支持: text / markdown / json。"
    )


# =============================================================================
# 内部辅助函数
# =============================================================================
def _find_layer(ly, layer: int, datatype: int):
    """查找层，不存在返回 None（R332 内部函数）。"""
    for li in ly.layer_indices():
        info = ly.get_info(li)
        if int(info.layer) == layer and int(info.datatype) == datatype:
            return li
    return None


def _shape_to_port(shape, layer: int, datatype: int, dbu: float,
                   cell_name: str) -> PortInfo | None:
    """将 Shape 转换为 PortInfo（R332 内部函数）。

    支持 box 和 polygon。计算中心点、bbox、宽高。

    Returns:
        PortInfo 或 None（不支持的 shape 类型）。
    """
    if shape.is_box():
        b = shape.bbox()
        xmin = float(b.left) * dbu
        ymin = float(b.bottom) * dbu
        xmax = float(b.right) * dbu
        ymax = float(b.top) * dbu
        cx = (xmin + xmax) / 2.0
        cy = (ymin + ymax) / 2.0
        w = xmax - xmin
        h = ymax - ymin
        return PortInfo(
            name="",
            layer=layer,
            datatype=datatype,
            position_um=(cx, cy),
            bbox_um=(xmin, ymin, xmax, ymax),
            width_um=w,
            height_um=h,
            cell_name=cell_name,
            text_matched=False,
        )
    if shape.is_polygon():
        poly = shape.polygon
        b = poly.bbox()
        xmin = float(b.left) * dbu
        ymin = float(b.bottom) * dbu
        xmax = float(b.right) * dbu
        ymax = float(b.top) * dbu
        cx = (xmin + xmax) / 2.0
        cy = (ymin + ymax) / 2.0
        w = xmax - xmin
        h = ymax - ymin
        return PortInfo(
            name="",
            layer=layer,
            datatype=datatype,
            position_um=(cx, cy),
            bbox_um=(xmin, ymin, xmax, ymax),
            width_um=w,
            height_um=h,
            cell_name=cell_name,
            text_matched=False,
        )
    # 非_box 非_polygon 的 shape（如 text/path）跳过
    return None


def _render_text_report(report: PortReport) -> str:
    """渲染纯文本报告（R332 内部函数）。"""
    lines: list[str] = []
    lines.append("=" * 60)
    lines.append("GDSII 端口提取报告")
    lines.append("=" * 60)
    lines.append(f"文件路径: {report.file_path}")
    lines.append(f"顶层 cell: {report.top_cell_name}")
    lines.append(f"dbu: {report.dbu} μm")
    lines.append(f"端口层: {report.port_layers}")
    lines.append(f"文本层: {report.text_layers}")
    lines.append(f"匹配距离: {report.match_distance_um} μm")
    lines.append(f"端口总数: {len(report.ports)}")
    matched = sum(1 for p in report.ports if p.text_matched)
    lines.append(f"已匹配名: {matched}")
    lines.append("")
    lines.append("-" * 60)
    lines.append("端口列表")
    lines.append("-" * 60)
    for i, port in enumerate(report.ports):
        name = port.name if port.name else "(未匹配)"
        cx, cy = port.position_um
        lines.append(
            f"[{i}] {name}  层=({port.layer},{port.datatype})  "
            f"位置=({cx:.4f},{cy:.4f})μm  "
            f"尺寸={port.width_um:.4f}×{port.height_um:.4f}μm  "
            f"cell={port.cell_name}"
        )
    lines.append("=" * 60)
    return "\n".join(lines)


def _render_markdown_report(report: PortReport) -> str:
    """渲染 Markdown 报告（R332 内部函数）。"""
    lines: list[str] = []
    lines.append("# GDSII 端口提取报告")
    lines.append("")
    lines.append(f"- **文件路径**: `{report.file_path}`")
    lines.append(f"- **顶层 cell**: `{report.top_cell_name}`")
    lines.append(f"- **dbu**: {report.dbu} μm")
    lines.append(f"- **端口层**: {report.port_layers}")
    lines.append(f"- **文本层**: {report.text_layers}")
    lines.append(f"- **匹配距离**: {report.match_distance_um} μm")
    lines.append(f"- **端口总数**: {len(report.ports)}")
    matched = sum(1 for p in report.ports if p.text_matched)
    lines.append(f"- **已匹配名**: {matched}")
    lines.append("")
    lines.append("## 端口列表")
    lines.append("")
    lines.append(
        "| 序号 | 名称 | 层 | 位置 (μm) | 尺寸 (μm) | cell |"
    )
    lines.append("| ---: | --- | --- | --- | --- | --- |")
    for i, port in enumerate(report.ports):
        name = port.name if port.name else "(未匹配)"
        cx, cy = port.position_um
        lines.append(
            f"| {i} | {name} | ({port.layer},{port.datatype}) | "
            f"({cx:.4f},{cy:.4f}) | "
            f"{port.width_um:.4f}×{port.height_um:.4f} | "
            f"{port.cell_name} |"
        )
    return "\n".join(lines)


def _render_json_report(report: PortReport) -> str:
    """渲染 JSON 报告（R332 内部函数）。"""
    data = {
        "file_path": report.file_path,
        "top_cell_name": report.top_cell_name,
        "dbu": report.dbu,
        "port_layers": list(report.port_layers),
        "text_layers": list(report.text_layers),
        "match_distance_um": report.match_distance_um,
        "port_count": len(report.ports),
        "matched_count": sum(1 for p in report.ports if p.text_matched),
        "ports": [
            {
                "name": p.name,
                "layer": p.layer,
                "datatype": p.datatype,
                "position_um": list(p.position_um),
                "bbox_um": list(p.bbox_um),
                "width_um": p.width_um,
                "height_um": p.height_um,
                "cell_name": p.cell_name,
                "text_matched": p.text_matched,
            }
            for p in report.ports
        ],
    }
    return json.dumps(data, indent=2, ensure_ascii=False)
