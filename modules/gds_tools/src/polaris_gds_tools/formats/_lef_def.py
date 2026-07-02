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

import math
import re

from polaris.io.multi_format import Cell, FormatLayout, Instance, LayerInfo, Point, Shape

__all__ = ["read_lef_def", "write_lef_def"]


def _fmt_lef_float(x: float) -> str:
    """LEF/DEF 距离值格式化（强制定点，禁科学计数法 + NaN/Inf 检测）。

    R05 Bug 修复 v4.0-LEFDEF-FMT（第1轮迭代发现）:
    原代码 ``f"( {inst.origin.x} {inst.origin.y} )"`` 用默认 str()
    会产生科学计数法（1e-05）或浮点精度伪影（0.30000000000000004），
    LEF/DEF 5.8 语法禁止科学计数法，导致 OpenROAD/KLayout 解析失败。

    修复:
    1. NaN/Inf → raise ValueError（R03 禁止 fall-back）
    2. ``:.6f`` 定点格式（0.001nm 分辨率，足够 LEF/DEF DATABASE MICRONS 10000）
    3. 去尾零美化（1.500000 → 1.5）保持可读

    规则: R03 禁止 fall-back / R05 Bug 必修 / R02 学术诚信
    文献:
    - LEF/DEF 5.8 Reference §2.1 Distance values
  https://www.ispd.cc/contests/18/lefdefref.pdf
    - OpenROAD LEF/DEF parser (禁止科学计数法)
  https://github.com/The-OpenROAD-Project/OpenDB
    - Python format spec §format-spec:
  https://docs.python.org/3/library/string.html#format-specification-mini-language
    - IEEE 754 NaN/Inf 处理: https://en.wikipedia.org/wiki/IEEE_754
    - KLayout LEF/DEF 输出: https://www.klayout.org/doc/manual/lef_def.html
    """
    v = float(x)
    if math.isnan(v) or math.isinf(v):
        raise ValueError(
            f"LEF/DEF 距离值非法（NaN/Infinity 不允许）: {x!r}. "
            f"R03 禁止 fall-back：拒绝写出损坏几何，由上游修复数据。"
        )
    s = f"{v:.6f}"
    # 去尾零: 1.500000 → 1.5; 1.000000 → 1
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s if s else "0"


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
    """解析 DEF COMPONENTS 段。

    完整支持 LEF/DEF 5.8 的 8 种 orient：N/E/S/W/FN/FS/FE/FW
    （来源: LEF/DEF 5.8 Language Reference §Components）。
    对称解析 angle + mirror，与 ``_lef_def_orient`` 反向映射一致
    （R05 Bug 修复 v3.3-IO-2）。
    """
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
            angle, mirror = _lef_def_parse_orient(m.group(5))
            instances.append(Instance(
                name=m.group(1),
                cell_name=m.group(2),
                origin=Point(float(m.group(3)), float(m.group(4))),
                angle=angle,
                mirror=mirror,
            ))
        i += 1
    return instances, i


# LEF/DEF 5.8 §Components: 8 种合法 orient
# 来源: http://coriolis.lip6.fr/doc/lefdef/lefdefref/DEFSyntax.html
_LEF_DEF_ORIENT_TO_TRANSFORM: dict[str, tuple[float, bool]] = {
    "N": (0.0, False),    # North (默认)
    "E": (90.0, False),   # East (顺时针 90°)
    "S": (180.0, False),  # South (180°)
    "W": (270.0, False),  # West (270°)
    "FN": (0.0, True),    # Flipped North (镜像 N)
    "FE": (90.0, True),   # Flipped East
    "FS": (180.0, True),  # Flipped South
    "FW": (270.0, True),  # Flipped West
}
# 反向映射：(angle_rounded, mirror) → orient 字符串
_LEF_DEF_TRANSFORM_TO_ORIENT: dict[tuple[int, bool], str] = {
    (int(round(a)), m): o for o, (a, m) in _LEF_DEF_ORIENT_TO_TRANSFORM.items()
}


def _lef_def_parse_orient(orient: str) -> tuple[float, bool]:
    """LEF/DEF orient 字符串 → (angle, mirror)。

    Args:
        orient: ``N``/``E``/``S``/``W``/``FN``/``FE``/``FS``/``FW`` 之一。

    Returns:
        (angle_degrees, mirror_flag) 元组。

    Raises:
        ValueError: 未知 orient 值。
    """
    key = orient.upper()
    if key not in _LEF_DEF_ORIENT_TO_TRANSFORM:
        raise ValueError(f"LEF/DEF 未知 orient: {orient}")
    return _LEF_DEF_ORIENT_TO_TRANSFORM[key]


def _lef_def_orient(angle: float, mirror: bool) -> str:
    """(angle, mirror) → LEF/DEF orient 字符串。

    LEF/DEF 5.8 标准仅支持 4 个正交角度（0/90/180/270）+ 镜像标志，
    不支持 magnification 与任意角度（来源: LEF/DEF 5.8 LRM §Components）。

    Args:
        angle: 旋转角度（度），必须为 0/90/180/270 之一。
        mirror: 是否镜像。

    Returns:
        ``N``/``E``/``S``/``W``/``FN``/``FE``/``FS``/``FW`` 之一。

    Raises:
        ValueError: 角度不在 4 个正交值中。
    """
    key = (int(round(angle)) % 360, mirror)
    if key not in _LEF_DEF_TRANSFORM_TO_ORIENT:
        raise ValueError(
            f"LEF/DEF 5.8 仅支持 0/90/180/270 正交角度，收到 angle={angle}"
        )
    return _LEF_DEF_TRANSFORM_TO_ORIENT[key]


def write_lef_def(layout: FormatLayout) -> str:
    """将 FormatLayout 写为 LEF/DEF 混合文本。

    Instance 完整序列化 orient（N/E/S/W/FN/FS/FE/FW），与
    ``_def_parse_components`` 对称（R05 Bug 修复 v3.3-IO-2）。
    LEF/DEF 5.8 标准不支持 magnification，mag != 1.0 时 raise
    （禁止 fall-back 静默丢失，规则 R03）。
    """
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
                if inst.mag != 1.0:
                    raise ValueError(
                        f"LEF/DEF 5.8 不支持 magnification（实例 {inst.name} "
                        f"mag={inst.mag}）；请改用 OpenAccess 格式"
                    )
                orient = _lef_def_orient(inst.angle, inst.mirror)
                lines.append(
                    f"- {inst.name} {inst.cell_name} + PLACED "
                    f"( {_fmt_lef_float(inst.origin.x)} {_fmt_lef_float(inst.origin.y)} ) "
                    f"{orient} ;"
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
                f"      RECT {_fmt_lef_float(x1)} {_fmt_lef_float(y1)} "
                f"{_fmt_lef_float(x2)} {_fmt_lef_float(y2)} ;", "  END"]
    if s.shape_type == "polygon":
        pts = " ".join(
            f"{_fmt_lef_float(p.x)} {_fmt_lef_float(p.y)}" for p in s.points
        )
        return ["  OBS", f"    LAYER {s.layer} ;",
                f"      POLYGON {pts} ;", "  END"]
    raise ValueError(f"LEF/DEF 不支持形状类型: {s.shape_type}")
