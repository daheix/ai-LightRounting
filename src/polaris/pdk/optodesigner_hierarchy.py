"""R20 路标：Synopsys OptoDesigner - 层级化设计（unlimited hierarchy levels）。

支持无限层级嵌套：TopCell = Compose({Instance_i(Cell_i, p_i, T_i)})。
子实例可以是 PyCell 或 HierarchyDesign（递归嵌套）。

## 学术依据

- Weste & Harris, "CMOS VLSI Design: A Circuits and Systems Perspective",
  4th ed., Addison-Wesley, 2010（层级化设计）
  URL: https://www.pearson.com/us/higher-education/program/
       Weste-CMOS-VLSI-Design-A-Circuits-and-Systems-Perspective-4th-Edition/PGM320852.html
- Synopsys OptoDesigner 官方文档（hierarchy levels）
  URL: https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner.html

## 合规性

- project_rules.md 规则 14.1: 禁止 fall-back / 假数据 / mock
- project_rules.md 规则 18: 所有参数来自公开文献，标注来源 URL
- R20 路标: docs/roundmap/R20.md
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from polaris.pdk.optodesigner_design_intent import _URL_CMOS_VLSI
from polaris.pdk.optodesigner_pycell import PyCell


@dataclass
class _Instance:
    """层级化设计中的实例引用（内部数据结构）。

    Attributes:
        cell: 被引用的 PyCell。
        position: 放置位置 (x, y)。
        rotation: 旋转角度（度）。
        flip: 是否水平翻转。
    """

    cell: PyCell
    position: tuple[float, float]
    rotation: float = 0.0
    flip: bool = False


class HierarchyDesign:
    """OptoDesigner 层级化设计复用（unlimited hierarchy levels）。

    支持无限层级嵌套：TopCell = Compose({Instance_i(Cell_i, p_i, T_i)})。
    子实例可以是 PyCell 或 HierarchyDesign（递归嵌套）。

    学术依据: Weste & Harris, CMOS VLSI Design, 4th ed., 2010
    URL: https://www.pearson.com/us/higher-education/program/
         Weste-CMOS-VLSI-Design-A-Circuits-and-Systems-Perspective-4th-Edition/PGM320852.html

    公式: TopCell = Compose({Instance_i(Cell_i, p_i, T_i)})
    """

    def __init__(self, name: str) -> None:
        """初始化层级化设计。

        Args:
            name: 顶层设计名称。
        """
        self.name = name
        self._instances: list[_Instance] = []
        # 子层级设计（支持递归嵌套）
        self._sub_designs: list[tuple[HierarchyDesign, tuple[float, float], float, bool]] = []

    def add_instance(
        self,
        cell: PyCell,
        position: tuple[float, float],
        rotation: float = 0.0,
        flip: bool = False,
    ) -> None:
        """添加 PyCell 实例到层级设计。

        Args:
            cell: 被引用的 PyCell。
            position: 放置位置 (x, y)（μm）。
            rotation: 旋转角度（度）。
            flip: 是否水平翻转。
        """
        self._instances.append(_Instance(cell, position, rotation, flip))

    def add_sub_design(
        self,
        design: HierarchyDesign,
        position: tuple[float, float],
        rotation: float = 0.0,
        flip: bool = False,
    ) -> None:
        """添加子层级设计（递归嵌套）。

        Args:
            design: 子 HierarchyDesign。
            position: 放置位置 (x, y)。
            rotation: 旋转角度（度）。
            flip: 是否水平翻转。
        """
        self._sub_designs.append((design, position, rotation, flip))

    def _transform_point(
        self, point: tuple[float, float], position: tuple[float, float],
        rotation: float, flip: bool
    ) -> tuple[float, float]:
        """对点应用平移+旋转+翻转变换。"""
        x, y = point
        if flip:
            x = -x
        rad = math.radians(rotation)
        cos_r, sin_r = math.cos(rad), math.sin(rad)
        rx = x * cos_r - y * sin_r
        ry = x * sin_r + y * cos_r
        return (rx + position[0], ry + position[1])

    def flatten(self) -> PyCell:
        """展平层级化设计为单个 PyCell。

        递归展平所有子实例与子层级设计，合并多边形与端口。

        Returns:
            展平后的 PyCell。
        """
        all_polys: list = []
        all_ports: list = []
        for inst in self._instances:
            for poly in inst.cell.polygons:
                transformed = [self._transform_point(p, inst.position, inst.rotation, inst.flip)
                               for p in poly]
                all_polys.append(transformed)
            for port in inst.cell.ports:
                name, px, py, pang, pw = port
                tx, ty = self._transform_point((px, py), inst.position, inst.rotation, inst.flip)
                all_ports.append((f"{inst.cell.name}_{name}", tx, ty, pang + inst.rotation, pw))
        for design, pos, rot, flip in self._sub_designs:
            sub_cell = design.flatten()
            for poly in sub_cell.polygons:
                transformed = [self._transform_point(p, pos, rot, flip) for p in poly]
                all_polys.append(transformed)
            for port in sub_cell.ports:
                name, px, py, pang, pw = port
                tx, ty = self._transform_point((px, py), pos, rot, flip)
                all_ports.append((f"{design.name}_{name}", tx, ty, pang + rot, pw))
        return PyCell(
            name=self.name,
            params={"flattened": True},
            polygons=all_polys,
            ports=all_ports,
            metadata={"source": _URL_CMOS_VLSI},
        )

    def hierarchy_depth(self) -> int:
        """计算层级深度。

        顶层为 1，每层子设计递归 +1。

        Returns:
            层级深度（≥1）。
        """
        if not self._sub_designs:
            return 1
        return 1 + max(d.hierarchy_depth() for d, *_ in self._sub_designs)

    @property
    def instance_count(self) -> int:
        """直接子实例数量（PyCell + 子设计）。"""
        return len(self._instances) + len(self._sub_designs)


__all__ = [
    "HierarchyDesign",
]
