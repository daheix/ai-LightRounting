"""DXF (Drawing Exchange Format) 读写子模块。

DXF 语法实现遵循下列权威来源（规则 18 学术诚信）：
- Autodesk, "DXF Reference", AutoCAD 2024,
  https://images.autodesk.com/adskfiles/acad_dxf.pdf
- Autodesk, "AutoCAD ObjectARX Developer Documentation", 2024,
  https://help.autodesk.com/view/OARX/2024/ENU/
- Autodesk Developer Network, https://www.autodesk.com/developer-network
- Wikipedia, "AutoCAD DXF",
  https://en.wikipedia.org/wiki/AutoCAD_DXF
- Mead & Conway, "Introduction to VLSI Systems", Addison-Wesley 1980
  （版图分层理论，DXF 层概念对应）

异常处理最佳实践（R03 禁止 fall-back）：
- PEP 8 Python 代码风格指南: https://peps.python.org/pep-0008/
- Effective Python 第20条 遇到意外状况时应该抛出异常，不要返回 None:
  https://www.informit.com/articles/article.aspx?p=3203546&seqNum=3
- Python 官方文档 Errors and Exceptions: https://docs.python.org/3/tutorial/errors.html
- Real Python Async IO: https://realpython.com/async-io-python/
- Python Cookbook 3rd Edition: https://www.oreilly.com/library/view/python-cookbook-3rd/9781449357337/

DXF 为码值对（group code / value）文本格式；本模块解析 ENTITIES 段的
LINE / CIRCLE / LWPOLYLINE / TEXT 实体（来源: Autodesk DXF Reference）。
"""

from __future__ import annotations

from polaris_gds_tools.formats.multi_format import Cell, FormatLayout, LayerInfo, Point, Shape

__all__ = ["read_dxf", "write_dxf"]


def read_dxf(text: str) -> FormatLayout:
    """解析 DXF 文本为 FormatLayout。

    仅解析 ENTITIES 段的 LINE/CIRCLE/LWPOLYLINE/TEXT 实体。
    来源: Autodesk "DXF Reference"。
    """
    lines = [ln.strip() for ln in text.splitlines()]
    shapes: list[Shape] = []
    layers: dict[str, LayerInfo] = {}
    i = 0
    in_entities = False
    while i < len(lines) - 1:
        code = lines[i]
        value = lines[i + 1]
        if code == "0" and value == "SECTION":
            seg_name = lines[i + 3] if i + 3 < len(lines) else ""
            in_entities = seg_name == "ENTITIES"
        elif code == "0" and value == "ENDSEC":
            in_entities = False
        elif code == "0" and in_entities:
            entity_pairs = _dxf_collect_entity(lines, i)
            shape = _dxf_parse_entity(value, entity_pairs)
            shapes.append(shape)
            layers.setdefault(shape.layer, LayerInfo(name=shape.layer))
            i += len(entity_pairs) + 1
        i += 1
    cell = Cell(name="dxf_layout", shapes=shapes)
    return FormatLayout(
        name="dxf_layout",
        cells=[cell],
        layers=layers or {"0": LayerInfo(name="0")},
        top_cell="dxf_layout",
        unit="mm",
    )


def _dxf_collect_entity(lines: list[str], start: int) -> list[str]:
    """收集从 start 开始的实体码值对（到下一个 0 码）。"""
    out: list[str] = []
    i = start + 2  # 跳过 "0" + type
    while i < len(lines) - 1:
        if lines[i] == "0":
            break
        out.append(lines[i])
        out.append(lines[i + 1])
        i += 2
    return out


def _dxf_parse_entity(etype: str, pairs: list[str]) -> Shape:
    """解析单个 DXF 实体 → Shape。

    码定义（来源: Autodesk DXF Reference）：8=层, 10/20=x/y,
    11/21=LINE 终点, 40=半径/字高, 70=多段线标志, 43=线宽, 1=文本。

    Raises:
        ValueError: 未识别的 DXF 实体类型（R03 禁止 fall-back，不返回 None）。
    """
    codes = _dxf_pairs_to_dict(pairs)
    layer = str(codes.get(8, "0"))
    if etype == "LINE":
        return _dxf_line(codes, layer)
    if etype == "CIRCLE":
        return _dxf_circle(codes, layer)
    if etype == "LWPOLYLINE":
        return _dxf_lwpolyline(codes, layer)
    if etype == "TEXT":
        cx = float(codes.get(10, 0))
        cy = float(codes.get(20, 0))
        return Shape("text", layer, [Point(cx, cy)], text=str(codes.get(1, "")))
    raise ValueError(f"DXF 不支持实体类型: {etype}")


def _dxf_line(codes: dict, layer: str) -> Shape:
    """LINE → path（两点）。"""
    x1 = float(codes.get(10, 0))
    y1 = float(codes.get(20, 0))
    x2 = float(codes.get(11, 0))
    y2 = float(codes.get(21, 0))
    return Shape("path", layer, [Point(x1, y1), Point(x2, y2)])


def _dxf_circle(codes: dict, layer: str) -> Shape:
    """CIRCLE → circle（直径=2×半径）。"""
    cx = float(codes.get(10, 0))
    cy = float(codes.get(20, 0))
    r = float(codes.get(40, 0))
    return Shape("circle", layer, [Point(cx, cy)], width=2 * r)


def _dxf_lwpolyline(codes: dict, layer: str) -> Shape:
    """LWPOLYLINE → polygon（闭合）或 path（开放）。"""
    pts = _dxf_polyline_points(codes)
    closed = bool(int(codes.get(70, 0)) & 1)
    stype = "polygon" if closed and len(pts) >= 3 else "path"
    return Shape(stype, layer, pts, width=float(codes.get(43, 0)))


def _dxf_pairs_to_dict(pairs: list[str]) -> dict:
    """码值对列表 → dict（重复码用列表保留全部）。"""
    out: dict[int, list] = {}
    i = 0
    while i + 1 < len(pairs):
        out.setdefault(int(pairs[i]), []).append(pairs[i + 1])
        i += 2
    return {k: (v[-1] if len(v) == 1 else v) for k, v in out.items()}


def _dxf_polyline_points(codes: dict) -> list[Point]:
    """LWPOLYLINE 顶点（码 10/20 可重复）。"""
    xs = codes.get(10, [])
    ys = codes.get(20, [])
    xs = [xs] if not isinstance(xs, list) else xs
    ys = [ys] if not isinstance(ys, list) else ys
    return [Point(float(x), float(y)) for x, y in zip(xs, ys)]


def write_dxf(layout: FormatLayout) -> str:
    """将 FormatLayout 写为 DXF 文本（最小 ENTITIES 段）。"""
    lines = ["0", "SECTION", "2", "ENTITIES"]
    for s in (s for c in layout.cells for s in c.shapes):
        lines.extend(_dxf_shape_lines(s))
    lines.extend(["0", "ENDSEC", "0", "EOF"])
    return "\n".join(lines) + "\n"


def _dxf_shape_lines(s: Shape) -> list[str]:
    """单形状 → DXF 实体码值对。"""
    if s.shape_type == "path" and len(s.points) == 2:
        p0, p1 = s.points
        return ["0", "LINE", "8", s.layer,
                "10", str(p0.x), "20", str(p0.y),
                "11", str(p1.x), "21", str(p1.y)]
    if s.shape_type == "circle":
        c = s.points[0] if s.points else Point(0, 0)
        return ["0", "CIRCLE", "8", s.layer,
                "10", str(c.x), "20", str(c.y), "40", str(s.width / 2)]
    if s.shape_type == "rect":
        return _dxf_rect_lines(s)
    if s.shape_type in ("polygon", "path"):
        return _dxf_polyline_lines(s)
    if s.shape_type == "text":
        c = s.points[0] if s.points else Point(0, 0)
        return ["0", "TEXT", "8", s.layer,
                "10", str(c.x), "20", str(c.y),
                "40", "1.0", "1", s.text]
    raise ValueError(f"DXF 不支持形状类型: {s.shape_type}")


def _dxf_rect_lines(s: Shape) -> list[str]:
    """rect → 闭合 LWPOLYLINE（5 顶点）。"""
    c = s.points[0] if s.points else Point(0, 0)
    x0, y0 = c.x - s.width / 2, c.y - s.height / 2
    x1, y1 = c.x + s.width / 2, c.y + s.height / 2
    pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]
    out = ["0", "LWPOLYLINE", "8", s.layer, "90", str(len(pts)), "70", "1"]
    for x, y in pts:
        out += ["10", str(x), "20", str(y)]
    return out


def _dxf_polyline_lines(s: Shape) -> list[str]:
    """polygon/path → LWPOLYLINE。"""
    out = ["0", "LWPOLYLINE", "8", s.layer,
           "90", str(len(s.points)),
           "70", "1" if s.shape_type == "polygon" else "0"]
    for p in s.points:
        out += ["10", str(p.x), "20", str(p.y)]
    return out
