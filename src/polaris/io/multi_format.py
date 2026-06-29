"""多格式版图互操作：统一数据模型与格式调度器。

本模块定义统一的 ``FormatLayout`` 数据模型，并通过 ``MultiFormatIO``
按格式名分发到私有子模块（``_cif``/``_gerber``/``_dxf``/``_odbpp``/``_lef_def``）
的读写实现。每种格式实现 read/write 并保证往返一致性。

格式与权威来源（规则 18 学术诚信，所有语法均来自下列规范源码/文档）：
- ODB++ Solution Alliance, "ODB++ Format Specification", 2023,
  http://www.odb-sa.com/
- Autodesk, "DXF Reference", AutoCAD 2024,
  https://images.autodesk.com/adskfiles/acad_dxf.pdf
- Mead & Conway, "Introduction to VLSI Systems", Addison-Wesley 1980,
  Appendix C: CIF；Caltech Technical Report 2686 (1980-02-11)；
  Rubin "Computer Aids for VLSI Design" Appendix B,
  https://iue.tuwien.ac.at/phd/minixhofer/node51.html
- UCAMCO, "The Gerber File Format Specification", Rev 2024.06,
  https://www.ucamco.com/files/downloads/file/81/the_gerber_file_format_specification.pdf
- OpenROAD Project, "OpenDB LEF/DEF Reference", 2024,
  https://github.com/The-OpenROAD-Project/OpenDB
- Si2 OpenAccess, "OpenAccess 22.60 API Reference", 2024,
  https://si2.org/openaccess/  (openaccess.py 实现其 ASCII 交换子集)

*创新* 统一 ``FormatLayout`` 中间表示：将六种异构格式映射到单一
dataclass 模型 (Cell/Instance/Shape/LayerInfo)，使 read→write→read
往返保持几何一致。底层逻辑：每种格式的几何原语 (CIF B/P/W、Gerber
D01/D03、DXF LINE/LWPOLYLINE) 均可无损映射到 {rect, polygon, path,
circle, text} 五类 Shape，层信息映射到 LayerInfo。案例：CIF 的
``B len wid cx cy`` ↔ rect Shape(points=[(cx,cy)], width=len, height=wid)；
Gerber 的 ``D03`` flash ↔ circle Shape(diameter=孔径直径)。
支持理论：IC 版图本质是分层的多边形集合（Mead & Conway 1980），
故五类原语构成最小完备集，可覆盖六种格式的几何语义。
"""

from __future__ import annotations

import importlib
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

__all__ = [
    "Point",
    "Shape",
    "Instance",
    "Cell",
    "LayerInfo",
    "FormatLayout",
    "MultiFormatIO",
    "SUPPORTED_FORMATS",
    "layouts_equal",
]


# ---------------------------------------------------------------------------
# 统一数据模型
# ---------------------------------------------------------------------------


@dataclass
class Point:
    """二维点（坐标单位由 FormatLayout.unit 记录）。"""

    x: float
    y: float


@dataclass
class Shape:
    """几何形状（统一表示五类原语）。

    Attributes:
        shape_type: ``"rect"``/``"polygon"``/``"path"``/``"circle"``/``"text"``。
        layer: 所属层名。
        points: 顶点列表。rect/circle/text 取中心点；polygon/path 取顶点序列。
        width: rect 的 x 长度 / path 的线宽 / circle 的直径。
        height: rect 的 y 长度。
        text: text 类型的字符串内容。
        angle: 旋转角度（度）。
    """

    shape_type: str
    layer: str
    points: list[Point] = field(default_factory=list)
    width: float = 0.0
    height: float = 0.0
    text: str = ""
    angle: float = 0.0


@dataclass
class Instance:
    """单元实例（单元调用，含变换）。"""

    name: str
    cell_name: str
    origin: Point
    angle: float = 0.0
    mirror: bool = False
    mag: float = 1.0


@dataclass
class Cell:
    """单元：含一组形状与一组实例。"""

    name: str
    shapes: list[Shape] = field(default_factory=list)
    instances: list[Instance] = field(default_factory=list)


@dataclass
class LayerInfo:
    """层信息。"""

    name: str
    number: int = 0
    datatype: int = 0
    purpose: str = ""


@dataclass
class FormatLayout:
    """统一版图数据模型。

    Attributes:
        name: 版图名。
        cells: 单元列表。
        layers: 层名 → 层信息。
        top_cell: 顶层单元名。
        unit: 坐标单位（``"um"``/``"mm"``/``"inch"``/``"centimicron"``/``"dbu"``）。
    """

    name: str
    cells: list[Cell] = field(default_factory=list)
    layers: dict[str, LayerInfo] = field(default_factory=dict)
    top_cell: str = ""
    unit: str = "um"


# ---------------------------------------------------------------------------
# 往返一致性比较工具
# ---------------------------------------------------------------------------


def _shape_key(s: Shape) -> tuple:
    """生成 Shape 的可比较键（浮点容差 1e-6）。"""
    pts = tuple((round(p.x, 6), round(p.y, 6)) for p in s.points)
    return (
        s.shape_type,
        s.layer,
        pts,
        round(s.width, 6),
        round(s.height, 6),
        s.text,
        round(s.angle, 6),
    )


def _inst_key(i: Instance) -> tuple:
    """生成 Instance 的可比较键。"""
    return (
        i.name,
        i.cell_name,
        (round(i.origin.x, 6), round(i.origin.y, 6)),
        round(i.angle, 6),
        i.mirror,
        round(i.mag, 6),
    )


def layouts_equal(a: FormatLayout, b: FormatLayout) -> bool:
    """语义比较两个版图（忽略形状/实例顺序，浮点容差 1e-6）。"""
    if set(a.layers.keys()) != set(b.layers.keys()):
        return False
    if len(a.cells) != len(b.cells):
        return False
    a_cells = {c.name: c for c in a.cells}
    b_cells = {c.name: c for c in b.cells}
    if a_cells.keys() != b_cells.keys():
        return False
    for name in a_cells:
        ca, cb = a_cells[name], b_cells[name]
        if set(_shape_key(s) for s in ca.shapes) != set(
            _shape_key(s) for s in cb.shapes
        ):
            return False
        if set(_inst_key(i) for i in ca.instances) != set(
            _inst_key(i) for i in cb.instances
        ):
            return False
    return True


# ---------------------------------------------------------------------------
# 格式调度表（懒加载子模块，避免循环导入）
# ---------------------------------------------------------------------------

# fmt -> (子模块相对名, 读函数名, 写函数名)
_FORMAT_MAP: dict[str, tuple[str, str, str]] = {
    "cif": ("._cif", "read_cif", "write_cif"),
    "gerber": ("._gerber", "read_gerber", "write_gerber"),
    "dxf": ("._dxf", "read_dxf", "write_dxf"),
    "odb++": ("._odbpp", "read_odbpp", "write_odbpp"),
    "odbpp": ("._odbpp", "read_odbpp", "write_odbpp"),
    "lef_def": ("._lef_def", "read_lef_def", "write_lef_def"),
    "lef/def": ("._lef_def", "read_lef_def", "write_lef_def"),
    "openaccess": (".openaccess", "read_oa", "write_oa"),
    "oa": (".openaccess", "read_oa", "write_oa"),
}

SUPPORTED_FORMATS = sorted(set(_FORMAT_MAP.keys()))


def _load_handler(fmt: str, func_name: str):
    """懒加载子模块并返回指定读写函数。

    Args:
        fmt: 格式名。
        func_name: ``"read_*"`` 或 ``"write_*"``。

    Returns:
        子模块中的函数对象。

    Raises:
        ValueError: 格式不支持。
    """
    entry = _FORMAT_MAP.get(fmt.lower())
    if entry is None:
        raise ValueError(
            f"不支持的格式: {fmt}（支持: {SUPPORTED_FORMATS}）"
        )
    mod = importlib.import_module(entry[0], package="polaris.io")
    return getattr(mod, func_name)


class MultiFormatIO:
    """多格式版图读写统一入口。

    通过格式名分发到对应子模块的 read/write 实现，对外提供统一
    ``read(path, fmt) -> FormatLayout`` 与
    ``write(layout, path, fmt) -> None`` 接口。
    """

    @staticmethod
    def read(path: str, fmt: str) -> FormatLayout:
        """从文件读取指定格式版图。

        Args:
            path: 文件路径。
            fmt: 格式名（``cif``/``gerber``/``dxf``/``odb++``/``lef_def``）。

        Returns:
            FormatLayout。

        Raises:
            FileNotFoundError: 文件不存在。
            ValueError: 格式不支持或文件解析失败。
        """
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"输入文件不存在: {path}")
        entry = _FORMAT_MAP.get(fmt.lower())
        if entry is None:
            raise ValueError(
                f"不支持的格式: {fmt}（支持: {SUPPORTED_FORMATS}）"
            )
        reader = _load_handler(fmt, entry[1])
        return reader(p.read_text(encoding="utf-8"))

    @staticmethod
    def write(layout: FormatLayout, path: str, fmt: str) -> None:
        """将版图写为指定格式文件。

        Args:
            layout: 版图数据。
            path: 输出文件路径。
            fmt: 格式名。

        Raises:
            ValueError: 格式不支持。
        """
        entry = _FORMAT_MAP.get(fmt.lower())
        if entry is None:
            raise ValueError(
                f"不支持的格式: {fmt}（支持: {SUPPORTED_FORMATS}）"
            )
        writer = _load_handler(fmt, entry[2])
        # R05 Bug 修复 v4.0-ATOMIC-01（第1轮迭代发现）:
        # 原 Path(path).write_text() 非原子，进程中断会导致文件截断/半写入，
        # 客户导入时解析失败丢失设计成果。改为原子写入（临时文件 + fsync + os.replace）
        # 规则: R03 禁止 fall-back / R05 Bug 必修
        # 文献: POSIX rename(2) 原子性 https://pubs.opengroup.org/onlinepubs/9699919799/functions/rename.html
        # 文献: Python os.replace https://docs.python.org/3/library/os.html#os.replace
        # 文献: atomicwrites 库 https://github.com/untitaker/python-atomicwrites
        content = writer(layout)
        target = Path(path)
        fd, tmp_name = tempfile.mkstemp(
            dir=target.parent, prefix=target.name + ".", suffix=".tmp"
        )
        tmp_path = Path(tmp_name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, target)
        except Exception:
            tmp_path.unlink(missing_ok=True)
            raise
