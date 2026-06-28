"""LEF/DEF 读写子模块。

LEF/DEF 语法实现遵循下列权威来源（规则 18 学术诚信）：
- OpenROAD Project, "OpenDB LEF/DEF Reference", 2024,
  https://github.com/The-OpenROAD-Project/OpenDB
- OpenROAD Project, "OpenROAD"（LEF/DEF 解析）,
  https://github.com/The-OpenROAD-Project/OpenROAD
- Cadence, "LEF/DEF Language Reference", 5.8
- Wikipedia, "Library Exchange Format",
  https://en.wikipedia.org/wiki/Library_Exchange_Format
- Mead & Conway, "Introduction to VLSI Systems", Addison-Wesley 1980
- Rubin, "Computer Aids for VLSI Design" Appendix B,
  https://iue.tuwien.ac.at/phd/minixhofer/node51.html

LEF 定义 MACRO（→ Cell，含 OBS/PIN RECT 几何）；
DEF 定义 COMPONENTS（→ Instance，+ PLACED (x y) N）。
"""

from __future__ import annotations

import re

from polaris.io.multi_format import Cell, FormatLayout, Instance, LayerInfo, Point, Shape

__all__ = ["read_lef_def", "write_lef_def"]


def read_lef_def(text: str) -> FormatLayout:
    """解析 LEF/DEF 混合文本为 FormatLayout。

    LEF 的 MACRO 段 → Cell（含 OBS/PIN RECT 几何）；
    DEF 的 COMPONENTS 段 → Instance（按 cell_name 归属到对应 Cell）。
    """
    layers: dict[str, LayerInfo] = {}
    cells: list[Cell] = []
    instances: list[Instance] = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("MACRO"):
            cell, i, layers = _lef_parse_macro(lines, i, layers)
            cells.append(cell)
        elif line.startswith("COMPONENTS"):
            instances, i = _def_parse_components(lines, i)
        else:
            i += 1
    if not cells:
        cells = [Cell(name="lef_def_layout")]
    _lef_def_attach_instances(cells, instances)
    return FormatLayout(
        name="lef_def_layout",
        cells=cells,
        layers=layers,
        top_cell=cells[-1].name,
        unit="um",
    )


def _lef_def_attach_instances(cells: list[Cell], instances: list[Instance]) -> None:
    """将实例按 cell_name 归属到对应 Cell。"""
    cell_map = {c.name: c for c in cells}
    for inst in instances:
        target = cell_map.get(inst.cell_name)
        if target is None:
            raise ValueError(f"LEF/DEF 实例引用未知 MACRO: {inst.cell_name}")
        target.instances.append(inst)


def _lef_parse_macro(lines: list[str], i: int, layers: dict[str, LayerInfo]):
    """解析 LEF MACRO 段。"""
    header = lines[i].split()
    name = header[1] if len(header) > 1 else "macro"
    shapes: list[Shape] = []
    cur_layer = "default"
    i += 1
    while i < len(lines):
        line = lines[i].strip()
        if (line.startswith("END") and line[3:].strip() == name) or line == "END":
            i += 1
            break
        if line.startswith("OBS") or line.startswith("PIN"):
            shapes, cur_layer, i, layers = _lef_parse_obs(
                lines, i, shapes, cur_layer, layers
            )
        else:
            i += 1
    return Cell(name=name, shapes=shapes), i, layers


def _lef_parse_obs(
    lines: list[str], i: int, shapes: list[Shape],
    cur_layer: str, layers: dict[str, LayerInfo],
):
    """解析 LEF OBS/PIN 内的 LAYER/RECT/POLYGON 几何。

    分词前移除语句终止符 ``;``（LEF 语句以 ``;`` 结尾），
    避免 ``;`` 进入 POLYGON 顶点的 float 转换。
    """
    i += 1
    while i < len(lines):
        line = lines[i].strip()
        if line == "END":
            i += 1
            break
        toks = line.replace(";", "").split()
        if len(toks) >= 2 and toks[0] == "LAYER":
            cur_layer = toks[1]
            layers.setdefault(cur_layer, LayerInfo(name=cur_layer, number=len(layers)))
        elif len(toks) >= 5 and toks[0] == "RECT":
            shapes.append(_lef_rect_shape(toks, cur_layer))
        elif len(toks) >= 7 and toks[0] == "POLYGON":
            shapes.append(_lef_polygon_shape(toks, cur_layer))
        i += 1
    return shapes, cur_layer, i, layers


def _lef_rect_shape(toks: list[str], layer: str) -> Shape:
    """LEF RECT x1 y1 x2 y2 → rect Shape（中心 + 宽高）。"""
    x1, y1, x2, y2 = (float(t) for t in toks[1:5])
    return Shape("rect", layer, [Point((x1 + x2) / 2, (y1 + y2) / 2)],
                 width=x2 - x1, height=y2 - y1)


def _lef_polygon_shape(toks: list[str], layer: str) -> Shape:
    """LEF POLYGON x1 y1 ... → polygon Shape。"""
    nums = [float(t) for t in toks[1:]]
    pts = [Point(nums[i], nums[i + 1]) for i in range(0, len(nums), 2)]
    return Shape("polygon", layer, pts)


def _def_parse_components(lines: list[str], i: int) -> tuple[list[Instance], int]:
    """解析 DEF COMPONENTS 段。"""
    instances: list[Instance] = []
    i += 1
    while i < len(lines):
        line = lines[i].strip()
        if line == "END COMPONENTS":
            i += 1
            break
        m = re.match(
            r"-\s+(\S+)\s+(\S+)\s+\+ PLACED\s*\(\s*([\d.]+)\s+([\d.]+)\s*\)\s+(\S+)",
            line,
        )
        if m:
            instances.append(Instance(
                name=m.group(1),
                cell_name=m.group(2),
                origin=Point(float(m.group(3)), float(m.group(4))),
                angle=0.0 if m.group(5) == "N" else 90.0,
            ))
        i += 1
    return instances, i


def write_lef_def(layout: FormatLayout) -> str:
    """将 FormatLayout 写为 LEF/DEF 混合文本。"""
    lines = ["VERSION 5.8 ;", "UNITS DATABASE MICRONS 1000 ;",
             "NOWIREEXTENSIONATPIN ON ;"]
    for cell in layout.cells:
        lines.append(f"MACRO {cell.name}")
        lines.append("  ORIGIN 0 0 ;")
        for s in cell.shapes:
            lines.extend(_lef_shape_lines(s))
        lines.append(f"END {cell.name}")
    lines.append("END LIBRARY")
    if any(c.instances for c in layout.cells):
        total = sum(len(c.instances) for c in layout.cells)
        lines.append(f"COMPONENTS {total} ;")
        for cell in layout.cells:
            for inst in cell.instances:
                lines.append(
                    f"- {inst.name} {inst.cell_name} + PLACED "
                    f"( {inst.origin.x} {inst.origin.y} ) N ;"
                )
        lines.append("END COMPONENTS")
    lines.append("END DESIGN")
    return "\n".join(lines) + "\n"


def _lef_shape_lines(s: Shape) -> list[str]:
    """单形状 → LEF OBS 语句。"""
    if s.shape_type == "rect":
        c = s.points[0] if s.points else Point(0, 0)
        x1, y1 = c.x - s.width / 2, c.y - s.height / 2
        x2, y2 = c.x + s.width / 2, c.y + s.height / 2
        return ["  OBS", f"    LAYER {s.layer} ;",
                f"      RECT {x1} {y1} {x2} {y2} ;", "  END"]
    if s.shape_type == "polygon":
        pts = " ".join(f"{p.x} {p.y}" for p in s.points)
        return ["  OBS", f"    LAYER {s.layer} ;",
                f"      POLYGON {pts} ;", "  END"]
    raise ValueError(f"LEF/DEF 不支持形状类型: {s.shape_type}")
