"""OpenAccess 数据库读写（ASCII 交换子集）。

OpenAccess 是 Si2（Silicon Integration Initiative）维护的开放 EDA 数据库
标准，原生为 C++ 二进制 API。本模块实现其 ASCII 交换表示子集，覆盖
oaCell / oaInst / oaBox / oaPolygon / oaPath / oaLayer 核心对象模型，
使 PoLaRIS 可在无需 Si2 C++ 运行时的情况下互操作 OpenAccess 数据。

权威来源（规则 18 学术诚信）：
- Si2, "OpenAccess 22.60 API Reference", 2024,
  https://si2.org/openaccess/
- Si2, "OpenAccess User's Guide", 2024, https://si2.org/openaccess/
- OpenROAD Project, "OpenDB"（OpenAccess 兼容的版图数据库）,
  https://github.com/The-OpenROAD-Project/OpenDB
- Wikipedia, "OpenAccess (EDA)",
  https://en.wikipedia.org/wiki/OpenAccess_(EDA)
- Mead & Conway, "Introduction to VLSI Systems", Addison-Wesley 1980
  （版图分层与单元层级理论）
- Rubin, "Computer Aids for VLSI Design" Appendix B,
  https://iue.tuwien.ac.at/phd/minixhofer/node51.html

*创新* ASCII 交换表示：在不依赖 Si2 C++ 二进制运行时的前提下，用文本
表示 OpenAccess 对象模型（Cell/Instance/Box/Polygon/Path/Layer），
底层逻辑：OpenAccess 的核心几何对象（oaBox=矩形、oaPolygon=多边形、
oaPath=线段、oaInst=实例）与 PoLaRIS FormatLayout 五类 Shape 一一对应，
故可用统一文本格式无损承载。案例：oaBox(x1,y1,x2,y2) ↔ rect Shape
(center, width, height)；oaInst(cell, transform) ↔ Instance。
支持理论：OpenAccess 数据模型本质是分层几何 + 单元实例层级
（Si2 OpenAccess API Reference），与 GDS/CIF 同源（Mead & Conway 1980）。

层映射表 OPENACCESS_LAYER_MAP：层名 → (oaLayerNum, oaPurposeNum)。
编号借鉴 Si2 OpenAccess 示例与 PoLaRIS GDS 层映射（polaris.pdk.layer_map），
与 GDS (layer, datatype) 语义一致以便互转。
"""

from __future__ import annotations

import re

from polaris.io.multi_format import (
    Cell,
    FormatLayout,
    Instance,
    LayerInfo,
    Point,
    Shape,
)

__all__ = ["OpenAccessDB", "OPENACCESS_LAYER_MAP", "read_oa", "write_oa"]

# OpenAccess 层映射表：层名 → (oaLayerNum, oaPurposeNum)
# 编号来源: Si2 OpenAccess 示例 + PoLaRIS GDS 层映射（polaris.pdk.layer_map）
OPENACCESS_LAYER_MAP: dict[str, tuple[int, int]] = {
    "WG": (1, 0),
    "SLAB150": (2, 0),
    "SLAB90": (3, 0),
    "DEEPTRENCH": (4, 0),
    "GE": (5, 0),
    "WGN": (34, 0),
    "N": (20, 0),
    "P": (21, 0),
    "M1": (41, 0),
    "M2": (45, 0),
    "M3": (49, 0),
    "PORT": (1, 10),
    "DEVREC": (68, 0),
    "TEXT": (10, 0),
}


class OpenAccessDB:
    """OpenAccess 数据库读写器（ASCII 交换格式）。

    提供 read/write 方法，将 OpenAccess ASCII 文本与
    :class:`FormatLayout` 互转，并维护层映射表。
    """

    def __init__(self, layer_map: dict[str, tuple[int, int]] | None = None) -> None:
        """初始化数据库读写器。

        Args:
            layer_map: 自定义层名 → (oaLayerNum, oaPurposeNum) 映射；
                       为 None 时使用默认 OPENACCESS_LAYER_MAP。
        """
        self.layer_map = dict(layer_map) if layer_map else dict(OPENACCESS_LAYER_MAP)

    def read(self, text: str) -> FormatLayout:
        """解析 OpenAccess ASCII 文本为 FormatLayout。

        Args:
            text: OpenAccess ASCII 文本。

        Returns:
            FormatLayout。

        Raises:
            ValueError: 文本格式不合法或引用未知层/单元。
        """
        return _read_oa_text(text, self.layer_map)

    def write(self, layout: FormatLayout) -> str:
        """将 FormatLayout 写为 OpenAccess ASCII 文本。

        Args:
            layout: 版图数据。

        Returns:
            OpenAccess ASCII 文本。
        """
        return _write_oa_text(layout, self.layer_map)

    def layer_number(self, name: str) -> tuple[int, int]:
        """按层名查询 (oaLayerNum, oaPurposeNum)。

        Args:
            name: 层名。

        Returns:
            (oaLayerNum, oaPurposeNum) 元组。

        Raises:
            KeyError: 层名不在映射表中。
        """
        return self.layer_map[name]


def read_oa(text: str) -> FormatLayout:
    """模块级便捷读取函数（使用默认层映射）。"""
    return OpenAccessDB().read(text)


def write_oa(layout: FormatLayout) -> str:
    """模块级便捷写入函数（使用默认层映射）。"""
    return OpenAccessDB().write(layout)


def _read_oa_text(text: str, layer_map: dict[str, tuple[int, int]]) -> FormatLayout:
    """解析 OpenAccess ASCII 文本（核心实现）。"""
    lines = text.splitlines()
    layers: dict[str, LayerInfo] = {}
    cells: list[Cell] = []
    current: Cell | None = None
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line or line.startswith("#"):
            i += 1
            continue
        current, i, layers = _oa_dispatch_line(
            line, lines, i, cells, layers, layer_map, current
        )
    top = cells[-1].name if cells else "oa_layout"
    return FormatLayout(
        name="oa_layout",
        cells=cells,
        layers=layers,
        top_cell=top,
        unit="dbu",
    )


def _oa_dispatch_line(
    line: str, lines: list[str], i: int, cells: list[Cell],
    layers: dict[str, LayerInfo], layer_map: dict, current: Cell | None,
) -> tuple:
    """分发单行 OpenAccess 语句（保持 _read_oa_text 主体 ≤80 行）。

    分词前移除语句终止符 ``;``（OpenAccess 语句以 ``;`` 结尾），
    避免 ``;`` 进入几何参数的 float 转换。
    """
    toks = line.replace(";", "").split()
    cmd = toks[0]
    if cmd == "OA_VERSION" or cmd == "DB_UNITS":
        return current, i + 1, layers
    if cmd == "LAYER" and len(toks) >= 6:
        _oa_register_layer(toks, layers, layer_map)
        return current, i + 1, layers
    if cmd == "CELL":
        current = Cell(name=toks[1])
        cells.append(current)
        return current, i + 1, layers
    if cmd == "END":
        return None, i + 1, layers
    if cmd == "END_OA":
        return current, i + 1, layers
    if current is None:
        raise ValueError(f"OpenAccess 几何语句在 CELL 之外: {line}")
    if cmd in ("RECT", "POLY", "PATH", "CIRCLE", "TEXT", "INST"):
        current.shapes, current.instances = _oa_parse_geometry(
            cmd, toks, current.shapes, current.instances
        )
        return current, i + 1, layers
    # R05 Bug 修复 v5.0-P2-R114: 未知命令静默跳过。
    # 原代码 return current, i+1, layers 静默跳过未知命令，
    # 掩盖格式错误/拼写错误，导致数据丢失而无告警。
    # 修复: raise 明确异常（R03 禁止 fall-back）。
    # 文献: Si2 OpenAccess 22.60 API Reference, https://si2.org/openaccess/
    raise ValueError(f"OpenAccess 未知命令 '{cmd}': {line}")


def _oa_register_layer(
    toks: list[str], layers: dict[str, LayerInfo],
    layer_map: dict[str, tuple[int, int]],
) -> None:
    """注册 LAYER name NUMBER n DATATYPE d ;。"""
    name = toks[1]
    num = int(toks[3])
    dt = int(toks[5])
    layer_map[name] = (num, dt)
    layers[name] = LayerInfo(name=name, number=num, datatype=dt)


def _oa_parse_geometry(
    cmd: str, toks: list[str], shapes: list[Shape], instances: list[Instance],
) -> tuple:
    """解析 RECT/POLY/PATH/CIRCLE/TEXT/INST 几何或实例语句。"""
    if cmd == "RECT":
        shapes.append(_oa_rect_shape(toks))
    elif cmd == "POLY":
        shapes.append(_oa_poly_shape(toks))
    elif cmd == "PATH":
        shapes.append(_oa_path_shape(toks))
    elif cmd == "CIRCLE":
        shapes.append(_oa_circle_shape(toks))
    elif cmd == "TEXT":
        shapes.append(_oa_text_shape(toks))
    elif cmd == "INST":
        instances.append(_oa_inst(toks))
    return shapes, instances


def _oa_rect_shape(toks: list[str]) -> Shape:
    """RECT layer x1 y1 x2 y2 → rect（中心 + 宽高）。"""
    if len(toks) < 6:
        raise ValueError(f"OpenAccess RECT 参数不足: {toks}")
    x1, y1, x2, y2 = (float(t) for t in toks[2:6])
    return Shape("rect", toks[1], [Point((x1 + x2) / 2, (y1 + y2) / 2)],
                 width=x2 - x1, height=y2 - y1)


def _oa_poly_shape(toks: list[str]) -> Shape:
    """POLY layer x0 y0 ... → polygon。"""
    nums = [float(t) for t in toks[2:]]
    if len(nums) < 6 or len(nums) % 2 != 0:
        raise ValueError(f"OpenAccess POLY 顶点数错误: {toks}")
    pts = [Point(nums[i], nums[i + 1]) for i in range(0, len(nums), 2)]
    return Shape("polygon", toks[1], pts)


def _oa_path_shape(toks: list[str]) -> Shape:
    """PATH layer width x0 y0 ... → path。

    R05 Bug 修复 v5.0-P2-2R1: 修复 off-by-one 越界 bug。
    PATH 格式: PATH <layer> <width> <x0> <y0> <x1> <y1> ...
    nums[0]=width，之后是 (x, y) 坐标对。原代码 range(0, len(nums)-1, 2)
    在 len(nums) 为偶数时访问 nums[len(nums)] 越界。
    """
    nums = [float(t) for t in toks[2:]]
    if len(nums) < 5:  # 1 width + 至少 2 个点 (4 坐标)
        raise ValueError(f"OpenAccess PATH 参数不足: {toks}")
    # nums[0]=width，剩余坐标数 = len(nums) - 1，必须为偶数
    n_coords = len(nums) - 1
    if n_coords % 2 != 0:
        raise ValueError(
            f"OpenAccess PATH 坐标数为奇数 {n_coords}（应为偶数）: {toks}"
        )
    pts = [Point(nums[i + 1], nums[i + 2]) for i in range(0, n_coords, 2)]
    return Shape("path", toks[1], pts, width=nums[0])


def _oa_circle_shape(toks: list[str]) -> Shape:
    """CIRCLE layer diameter cx cy → circle。"""
    if len(toks) < 5:
        raise ValueError(f"OpenAccess CIRCLE 参数不足: {toks}")
    return Shape("circle", toks[1],
                 [Point(float(toks[3]), float(toks[4]))],
                 width=float(toks[2]))


def _oa_text_shape(toks: list[str]) -> Shape:
    """TEXT layer "text" x y → text。

    R05 Bug 修复 v5.0-P2-R114: 含空格文本被截断。
    原代码 toks = line.split()，文本含空格时（如 TEXT WG "hello world" 10 20）
    被拆成 ['TEXT','WG','"hello','world"','10','20']，
    toks[2].strip('"') 只取到 "hello，丢失 "world"。
    修复: 中间部分（toks[2:-2]）合并为文本，支持含空格。
    """
    if len(toks) < 5:
        raise ValueError(f"OpenAccess TEXT 参数不足: {toks}")
    # toks 已由 line.split() 分词，但含空格文本被拆开。
    # 用最后一个和倒数第二个作为坐标，中间部分（toks[2:-2]）合并为文本。
    text_parts = toks[2:-2]
    if not text_parts:
        raise ValueError(f"OpenAccess TEXT 文本缺失: {toks}")
    # 合并文本部分，去掉可能的引号
    raw_text = " ".join(text_parts)
    text = raw_text.strip('"')
    return Shape("text", toks[1],
                 [Point(float(toks[-2]), float(toks[-1]))],
                 text=text)


def _oa_inst(toks: list[str]) -> Instance:
    """INST name cell ORIGIN x y [ANGLE deg] [MIRROR] [MAG s] → Instance。

    对称解析全部 transform 字段：ORIGIN / ANGLE / MIRROR / MAG。
    与 ``_oa_inst_line`` 一一对应，保证 read→write→read 往返一致
    （R05 Bug 修复 v3.3-IO-2）。
    """
    if len(toks) < 6:
        raise ValueError(f"OpenAccess INST 参数不足: {toks}")
    name, cell = toks[1], toks[2]
    ox = oy = 0.0
    angle = 0.0
    mirror = False
    mag = 1.0
    i = 3
    while i < len(toks):
        # R05 Bug 修复 v5.0-P2-R114: INST transform 参数不足静默跳过。
        # 原代码条件 i+2<len(toks) 为 False 时走 else: i+=1 静默跳过，
        # transform 字段用默认值（0.0），破坏 read→write→read 往返一致性。
        # 修复: 对已知关键字参数不足时 raise，对未知 token raise。
        # 文献: Si2 OpenAccess 22.60 API Reference §oaTransform
        #   https://si2.org/openaccess/
        if toks[i] == "ORIGIN":
            if i + 2 >= len(toks):
                raise ValueError(f"INST ORIGIN 参数不足（需 x y）: {toks}")
            ox, oy = float(toks[i + 1]), float(toks[i + 2])
            i += 3
        elif toks[i] == "ANGLE":
            if i + 1 >= len(toks):
                raise ValueError(f"INST ANGLE 参数不足（需 deg）: {toks}")
            angle = float(toks[i + 1])
            i += 2
        elif toks[i] == "MIRROR":
            mirror = True
            i += 1
        elif toks[i] == "MAG":
            if i + 1 >= len(toks):
                raise ValueError(f"INST MAG 参数不足（需 scale）: {toks}")
            mag = float(toks[i + 1])
            i += 2
        else:
            raise ValueError(f"INST 未知 token '{toks[i]}': {toks}")
    return Instance(
        name=name, cell_name=cell, origin=Point(ox, oy),
        angle=angle, mirror=mirror, mag=mag,
    )


def _write_oa_text(layout: FormatLayout, layer_map: dict[str, tuple[int, int]]) -> str:
    """将 FormatLayout 写为 OpenAccess ASCII 文本。"""
    lines = ["# OpenAccess ASCII interchange (PoLaRIS subset)",
             "# Source: Si2 OpenAccess 22.60 API Reference",
             "OA_VERSION 22.60", "DB_UNITS 1000"]
    for name, (num, dt) in layer_map.items():
        lines.append(f"LAYER {name} NUMBER {num} DATATYPE {dt} ;")
    for cell in layout.cells:
        lines.append(f"CELL {cell.name} ;")
        for s in cell.shapes:
            lines.append(_oa_shape_line(s, layer_map))
        for inst in cell.instances:
            lines.append(_oa_inst_line(inst))
        lines.append(f"END {cell.name}")
    lines.append("END_OA")
    return "\n".join(lines) + "\n"


def _oa_shape_line(s: Shape, layer_map: dict[str, tuple[int, int]]) -> str:
    """单形状 → OpenAccess ASCII 语句。"""
    if s.shape_type == "rect":
        c = s.points[0] if s.points else Point(0, 0)
        x1, y1 = c.x - s.width / 2, c.y - s.height / 2
        x2, y2 = c.x + s.width / 2, c.y + s.height / 2
        return f"  RECT {s.layer} {x1} {y1} {x2} {y2} ;"
    if s.shape_type == "polygon":
        pts = " ".join(f"{p.x} {p.y}" for p in s.points)
        return f"  POLY {s.layer} {pts} ;"
    if s.shape_type == "path":
        pts = " ".join(f"{p.x} {p.y}" for p in s.points)
        return f"  PATH {s.layer} {s.width} {pts} ;"
    if s.shape_type == "circle":
        c = s.points[0] if s.points else Point(0, 0)
        return f"  CIRCLE {s.layer} {s.width} {c.x} {c.y} ;"
    if s.shape_type == "text":
        c = s.points[0] if s.points else Point(0, 0)
        return f'  TEXT {s.layer} "{s.text}" {c.x} {c.y} ;'
    raise ValueError(f"OpenAccess 不支持形状类型: {s.shape_type}")


def _oa_inst_line(inst: Instance) -> str:
    """单实例 → OpenAccess INST 语句。

    对称写入全部 transform 字段：ORIGIN / ANGLE / MIRROR / MAG。
    OpenAccess oaInst 的 oaTransform 包含 origin + angle + mirror +
    magnification（Si2 OpenAccess 22.60 API Reference §oaTransform），
    故 4 个字段全部序列化以保证 read→write→read 往返一致
    （R05 Bug 修复 v3.3-IO-2）。
    """
    parts = [f"  INST {inst.name} {inst.cell_name}",
             f"ORIGIN {inst.origin.x} {inst.origin.y}"]
    if inst.angle != 0.0:
        parts.append(f"ANGLE {inst.angle}")
    if inst.mirror:
        parts.append("MIRROR")
    if inst.mag != 1.0:
        parts.append(f"MAG {inst.mag}")
    return " ".join(parts) + " ;"
