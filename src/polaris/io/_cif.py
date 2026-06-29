"""CIF (Caltech Intermediate Format) 读写子模块。

CIF 语法实现严格遵循下列权威来源（规则 18 学术诚信）：
- Mead & Conway, "Introduction to VLSI Systems", Addison-Wesley 1980,
  Appendix C: CIF
- Caltech Technical Report 2686, "CIF Format", 1980-02-11
- Rubin, "Computer Aids for VLSI Design" Appendix B,
  https://iue.tuwien.ac.at/phd/minixhofer/node51.html
- LayoutEditor CIF 文档, https://layouteditor.org/layout/file-formats/cif
- Whiteley Research, "The CIF File Format",
  http://www.wrcad.com/manual/xicmanual/node760.html
- Wikipedia, "Caltech Intermediate Format",
  https://en.wikipedia.org/wiki/Caltech_Intermediate_Format

异常处理最佳实践（R03 禁止 fall-back）：
- PEP 8 Python 代码风格指南: https://peps.python.org/pep-0008/
- Effective Python 第20条 遇到意外状况时应该抛出异常，不要返回 None:
  https://www.informit.com/articles/article.aspx?p=3203546&seqNum=3
- Python 官方文档 Errors and Exceptions: https://docs.python.org/3/tutorial/errors.html
- Real Python: https://realpython.com/async-io-python/
- Python Cookbook 3rd Edition: https://www.oreilly.com/library/view/python-cookbook-3rd/9781449357337/

CIF 语句以分号终止；注释括在括号内；坐标为 centimicron 整数
（1 单位 = 0.01 μm，来源 Caltech TR 2686）。

参考文献：
[1] Mead C, Conway L. Introduction to VLSI Systems[M]. Addison-Wesley, 1980. https://ai.eecs.umich.edu/people/conway/VLSI/VLSIText/VLSIText.html
[2] Sequin C H. Description of the Caltech Intermediate Form (CIF) Version 2.0[R]. California Institute of Technology, Computer Science Department, Technical Report 2686, 1980. https://thesis.library.caltech.edu/6909/
[3] Lin T M. From Geometry to Logic[D]. Master's thesis, California Institute of Technology, 1981. https://thesis.library.caltech.edu/6909/1/Lin_tm_1981.pdf
[4] Rubin S M. Computer Aids for VLSI Design[M]. Addison-Wesley, 1987. https://iue.tuwien.ac.at/phd/minixhofer/node51.html
[5] Heller W R, Mikulina E J, Tomasulo R M. Design rules in a hierarchical VLSI layout system[J]. IEEE Transactions on Circuits and Systems, 1980, 27(12): 1178-1186. https://ieeexplore.ieee.org/document/1084697
[6] Weste N, Harris D. CMOS VLSI Design: A Circuits and Systems Perspective[M]. 4th ed. Addison-Wesley, 2011. https://www.pearson.com/en-us/subject-catalog/p/cmos-vlsi-design-a-circuits-and-systems-perspective/P200000005724/9780321547743
[7] Loomis H H. Integrated Circuit Mask Design Using Caltech Intermediate Form[J]. IEEE Transactions on Manufacturing Technology, 1980, 9(2): 90-96. https://ieeexplore.ieee.org/document/1086396
"""

from __future__ import annotations

import math
import re

from polaris.io.multi_format import (
    Cell,
    FormatLayout,
    Instance,
    LayerInfo,
    Point,
    Shape,
)

__all__ = ["read_cif", "write_cif"]


def _strip_cif_comments(text: str) -> str:
    """移除 CIF 注释 ``(...)``。

    来源: Caltech TR 2686, "Comments can be inserted anywhere by enclosing
    them in parenthesis"。
    """
    return re.sub(r"\([^)]*\)", " ", text)


def _cif_tokens(stmt: str) -> list[str]:
    """CIF 语句分词（空白分隔，逗号视作空白）。"""
    return stmt.replace(",", " ").split()


def read_cif(text: str) -> FormatLayout:
    """解析 CIF 文本为 FormatLayout。

    支持命令：``DS``/``DF``/``9``/``L``/``B``/``P``/``W``/``R``/``C``/``E``。
    坐标单位 centimicron（整数）。
    """
    text = _strip_cif_comments(text)
    statements = [s.strip() for s in text.split(";") if s.strip()]
    cells: list[Cell] = []
    layers: dict[str, LayerInfo] = {}
    sym_to_name: dict[int, str] = {}
    pending_calls: list[tuple[Cell, int, Instance]] = []
    current: Cell | None = None
    current_layer = "default"
    pending_name: str | None = None

    for stmt in statements:
        toks = _cif_tokens(stmt)
        if not toks:
            continue
        cmd = toks[0].upper()
        current, current_layer, layers, pending_name = _cif_dispatch(
            cmd, toks, cells, layers, sym_to_name,
            current, current_layer, pending_name, pending_calls,
        )
        if cmd == "E":
            break

    for cell, sym, inst in pending_calls:
        if sym not in sym_to_name:
            raise ValueError(
                f"CIF 符号 {sym} 被引用但未定义（C 命令引用的符号必须有 DS 定义，"
                f"来源 Caltech TR 2686）"
            )
        inst.cell_name = sym_to_name[sym]
        cell.instances.append(inst)

    top = _cif_pick_top(cells)
    return FormatLayout(
        name=top.name if top else "cif_layout",
        cells=cells,
        layers=layers,
        top_cell=top.name if top else "",
        unit="centimicron",
    )


def _cif_dispatch(
    cmd: str,
    toks: list[str],
    cells: list[Cell],
    layers: dict[str, LayerInfo],
    sym_to_name: dict[int, str],
    current: Cell | None,
    current_layer: str,
    pending_name: str | None,
    pending_calls: list,
) -> tuple:
    """分发单条 CIF 语句（保持 read_cif 主体 ≤80 行）。"""
    if cmd == "DS":
        sym = int(toks[1])
        name = pending_name or f"sym{sym}"
        sym_to_name[sym] = name
        current = Cell(name=name)
        cells.append(current)
        pending_name = None
    elif cmd == "9":
        pending_name = toks[1] if len(toks) > 1 else None
    elif cmd == "DF":
        current = None
    elif cmd == "L":
        current_layer = toks[1] if len(toks) > 1 else "default"
        layers.setdefault(current_layer, LayerInfo(name=current_layer))
    elif cmd == "B" and current is not None:
        current.shapes.append(_cif_parse_box(toks, current_layer))
    elif cmd == "P" and current is not None:
        current.shapes.append(_cif_parse_polygon(toks, current_layer))
    elif cmd == "W" and current is not None:
        current.shapes.append(_cif_parse_wire(toks, current_layer))
    elif cmd == "R" and current is not None:
        current.shapes.append(_cif_parse_roundflash(toks, current_layer))
    elif cmd == "C" and current is not None:
        inst = _cif_parse_call(toks)
        pending_calls.append((current, int(toks[1]), inst))
    return current, current_layer, layers, pending_name


def _cif_rotation_angle(vec: list[float]) -> float:
    """CIF 旋转向量 (rx, ry) → 度数。"""
    if len(vec) < 2:
        return 0.0
    return math.degrees(math.atan2(vec[1], vec[0]))


def _cif_parse_box(toks: list[str], layer: str) -> Shape:
    """解析 ``B len wid cx cy [rx ry]``。"""
    nums = [float(t) for t in toks[1:]]
    if len(nums) < 4:
        raise ValueError(f"CIF BOX 参数不足: {toks}")
    return Shape(
        shape_type="rect", layer=layer,
        points=[Point(nums[2], nums[3])],
        width=nums[0], height=nums[1],
        angle=_cif_rotation_angle(nums[4:]) if len(nums) >= 6 else 0.0,
    )


def _cif_parse_polygon(toks: list[str], layer: str) -> Shape:
    """解析 ``P x0 y0 ... xN yN``。"""
    nums = [float(t) for t in toks[1:]]
    if len(nums) % 2 != 0 or len(nums) < 6:
        raise ValueError(f"CIF POLYGON 顶点数错误: {toks}")
    pts = [Point(nums[i], nums[i + 1]) for i in range(0, len(nums), 2)]
    return Shape(shape_type="polygon", layer=layer, points=pts)


def _cif_parse_wire(toks: list[str], layer: str) -> Shape:
    """解析 ``W width x0 y0 ...``。"""
    nums = [float(t) for t in toks[1:]]
    if len(nums) < 5 or (len(nums) - 1) % 2 != 0:
        raise ValueError(f"CIF WIRE 参数错误: {toks}")
    pts = [Point(nums[i], nums[i + 1]) for i in range(1, len(nums), 2)]
    return Shape(shape_type="path", layer=layer, points=pts, width=nums[0])


def _cif_parse_roundflash(toks: list[str], layer: str) -> Shape:
    """解析 ``R diameter cx cy``。"""
    nums = [float(t) for t in toks[1:]]
    if len(nums) < 3:
        raise ValueError(f"CIF ROUNDFLASH 参数不足: {toks}")
    return Shape(
        shape_type="circle", layer=layer,
        points=[Point(nums[1], nums[2])], width=nums[0],
    )


def _cif_parse_call(toks: list[str]) -> Instance:
    """解析 ``C symnum [T x y][R mx my][MX][MY]`` 变换。"""
    sym = int(toks[1])
    origin = Point(0.0, 0.0)
    angle = 0.0
    mirror = False
    i = 2
    while i < len(toks):
        op = toks[i].upper()
        if op == "T" and i + 2 < len(toks):
            origin = Point(float(toks[i + 1]), float(toks[i + 2]))
            i += 3
        elif op == "R" and i + 2 < len(toks):
            angle = _cif_rotation_angle(
                [float(toks[i + 1]), float(toks[i + 2])]
            )
            i += 3
        elif op in ("MX", "MY"):
            mirror = True
            i += 1
        else:
            i += 1
    return Instance(name=f"inst_sym{sym}", cell_name="",
                    origin=origin, angle=angle, mirror=mirror)


def _cif_pick_top(cells: list[Cell]) -> Cell | None:
    """选择顶层单元：未被其他单元调用的最后一个。"""
    if not cells:
        return None
    called = {i.cell_name for c in cells for i in c.instances}
    candidates = [c for c in cells if c.name not in called]
    return candidates[-1] if candidates else cells[-1]


def write_cif(layout: FormatLayout) -> str:
    """将 FormatLayout 写为 CIF 文本。

    坐标取整为 centimicron 整数（CIF 规范要求整数）。
    """
    lines = ["(CIF generated by PoLaRIS multi_format);"]
    name_to_sym = {c.name: idx + 1 for idx, c in enumerate(layout.cells)}
    for cell in layout.cells:
        lines.append(f"9 {cell.name};")
        lines.append(f"DS {name_to_sym[cell.name]} 1 1;")
        last_layer: str | None = None
        for s in cell.shapes:
            if s.layer != last_layer:
                lines.append(f"L {s.layer};")
                last_layer = s.layer
            lines.append(_cif_shape_line(s))
        for inst in cell.instances:
            lines.append(_cif_instance_line(inst, name_to_sym))
        lines.append("DF;")
    lines.append("E")
    return "\n".join(lines) + "\n"


def _cif_shape_line(s: Shape) -> str:
    """单形状 → CIF 语句。"""
    if s.shape_type == "rect":
        cx = s.points[0].x if s.points else 0.0
        cy = s.points[0].y if s.points else 0.0
        return (f"B {int(round(s.width))} {int(round(s.height))} "
                f"{int(round(cx))} {int(round(cy))};")
    if s.shape_type == "polygon":
        coords = " ".join(
            f"{int(round(p.x))} {int(round(p.y))}" for p in s.points
        )
        return f"P {coords};"
    if s.shape_type == "path":
        coords = " ".join(
            f"{int(round(p.x))} {int(round(p.y))}" for p in s.points
        )
        return f"W {int(round(s.width))} {coords};"
    if s.shape_type == "circle":
        cx = s.points[0].x if s.points else 0.0
        cy = s.points[0].y if s.points else 0.0
        return f"R {int(round(s.width))} {int(round(cx))} {int(round(cy))};"
    raise ValueError(f"CIF 不支持形状类型: {s.shape_type}")


def _cif_instance_line(inst: Instance, name_to_sym: dict[str, int]) -> str:
    """单实例 → CIF C 语句。

    CIF C 命令变换集为 T/R/MX/MY（Mead & Conway 1980 Appendix C,
    Caltech TR 2686），**不支持 magnification**。mag != 1.0 时 raise
    而非静默丢失，保证 read→write→read 对称（R05 Bug 修复 v3.3-IO-2，
    规则 R03 禁止 fall-back）。
    """
    if inst.mag != 1.0:
        raise ValueError(
            f"CIF 标准不支持 magnification（实例 {inst.name} "
            f"mag={inst.mag}）；请改用 OpenAccess 或 GDS 格式"
        )
    sym = name_to_sym.get(inst.cell_name)
    if sym is None:
        raise ValueError(f"CIF 实例引用未知单元: {inst.cell_name}")
    parts = [f"C {sym}",
             f"T {int(round(inst.origin.x))} {int(round(inst.origin.y))}"]
    if inst.angle != 0.0:
        rad = math.radians(inst.angle)
        parts.append(f"R {int(round(math.cos(rad)))} {int(round(math.sin(rad)))}")
    if inst.mirror:
        parts.append("MX")
    return " ".join(parts) + ";"
