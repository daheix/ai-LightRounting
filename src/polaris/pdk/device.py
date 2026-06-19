"""光器件核心数据类与几何变换工具（SubTask 2.1 + 2.4）。

数据结构对齐光子 PDK 业界最佳实践：
- IPKISS/Luceda PDK 的 ``PCell`` + ``Port`` 模型（器件含端口列表、包围盒、
  电光参数与工艺约束），波导模板参数化（core_width / n_eff 等）
  来源: https://academy.lucedaphotonics.com/pdks/cornerstone/cornerstone
  来源: http://docs.lucedaphotonics.com.s3-website-us-west-1.amazonaws.com/tutorials/layout_tutorial/index.html
- KLayoutPhotonicPCells 的端口追踪（位置、朝向、宽度）与器件层级组合
  来源: https://sebastian-goeldi.github.io/KLayoutPhotonicPCells-core/_modules/kppc/photonics.html
- gdspy 的 ``rotate``（弧度，逆时针）与 ``get_bounding_box``
  （返回 [[xmin, ymin], [xmax, ymax]]）几何变换约定
  来源: https://gdspy.readthedocs.io/en/stable/reference.html
- gdsfactory 组件（端口 layer / port_type / cross_section + metadata）
  来源: https://pypi.org/project/gdsfactory/4.4.14/

旋转采用标准数学坐标系（y 轴朝上、x 轴朝右），正角度为逆时针（CCW），
与 gdspy.rotate 及 IPKISS ``angle`` 参数约定一致；光子版图常用 90/180/270
度直角旋转，方向同步变换以便曼哈顿布线。
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from polaris.pdk.port import Direction, Port
from polaris.pdk.source import Source


@dataclass
class BoundingBox:
    """器件包围盒（μm）。

    轴对齐包围盒（AABB），与 gdspy ``get_bounding_box`` 返回的
    ``[[xmin, ymin], [xmax, ymax]]`` 语义一致。
    """

    xmin: float
    ymin: float
    xmax: float
    ymax: float


# 逆时针 90 度方向映射表：N -> W -> S -> E -> N
# （标准数学坐标系下，朝向随器件逆时针旋转而旋转）
_ROT90: dict[Direction, Direction] = {
    Direction.NORTH: Direction.WEST,
    Direction.WEST: Direction.SOUTH,
    Direction.SOUTH: Direction.EAST,
    Direction.EAST: Direction.NORTH,
}


def _rotate_point(x: float, y: float, angle_deg: int) -> tuple[float, float]:
    """绕原点逆时针旋转点（仅支持 0/90/180/270 度）。

    Args:
        x: 原 x 坐标（μm）。
        y: 原 y 坐标（μm）。
        angle_deg: 旋转角度（0/90/180/270 度）。

    Returns:
        旋转后的 ``(new_x, new_y)`` 坐标（μm）。
    """
    if angle_deg == 0:
        return x, y
    if angle_deg == 90:  # 逆时针 90 度: (x, y) -> (-y, x)
        return -y, x
    if angle_deg == 180:  # 逆时针 180 度: (x, y) -> (-x, -y)
        return -x, -y
    if angle_deg == 270:  # 逆时针 270 度: (x, y) -> (y, -x)
        return y, -x
    raise ValueError(f"仅支持 0/90/180/270 度旋转，得到 {angle_deg}")


def _rotate_direction(direction: Direction, angle_deg: int) -> Direction:
    """逆时针旋转端口朝向（仅支持 0/90/180/270 度）。"""
    steps = (angle_deg // 90) % 4
    result = direction
    for _ in range(steps):
        result = _ROT90[result]
    return result


@dataclass
class Device:
    """光器件模型（基于公开文献真实参数）。

    字段对齐 IPKISS ``PCell`` 与 gdsfactory ``Component`` 的核心信息：
    唯一标识、工艺平台、器件类别、端口列表、包围盒、电光参数、
    文献来源与设计约束。所有参数须可溯源（见 ``source`` 字段）。

    Attributes:
        device_id: 唯一标识。
        platform: 工艺平台（SOI/SiN/InP/LNOI）。
        category: 器件类别（passive/active/source/detector）。
        name: 器件类型名（如 ``ring_resonator``）。
        ports: 端口列表（相对器件原点定义）。
        bbox: 器件包围盒（μm）。
        params: 电光参数字典（含单位，如 ``{"loss_db_cm": 2.0}``）。
        source: 文献来源（每个参数须可溯源）。
        constraints: 设计约束（最小间距/弯曲半径/禁布区等）。
    """

    device_id: str
    platform: str
    category: str
    name: str
    ports: list[Port]
    bbox: BoundingBox
    params: dict = field(default_factory=dict)
    source: Source | None = None
    constraints: dict = field(default_factory=dict)

    def translate(self, dx: float, dy: float) -> Device:
        """平移器件（返回新实例，端口与包围盒同步更新）。

        Args:
            dx: x 方向平移量（μm）。
            dy: y 方向平移量（μm）。

        Returns:
            平移后的新 ``Device`` 实例，原实例不变。
        """
        new_ports = [replace(p, x=p.x + dx, y=p.y + dy) for p in self.ports]
        new_bbox = replace(
            self.bbox,
            xmin=self.bbox.xmin + dx,
            ymin=self.bbox.ymin + dy,
            xmax=self.bbox.xmax + dx,
            ymax=self.bbox.ymax + dy,
        )
        return replace(self, ports=new_ports, bbox=new_bbox)

    def rotate(self, angle_deg: float) -> Device:
        """旋转器件（angle_deg 为 90/180/270 度，返回新实例）。

        采用逆时针旋转（标准数学坐标系，y 轴朝上），与 gdspy.rotate 及
        IPKISS ``angle`` 参数约定一致。端口坐标、朝向与包围盒同步更新：
        包围盒由旋转后的四个角点重新计算轴对齐包围盒。

        Args:
            angle_deg: 旋转角度（须为 90/180/270 度的整数倍）。

        Returns:
            旋转后的新 ``Device`` 实例，原实例不变。
        """
        # 归一化到 [0, 360)，仅允许直角旋转
        normalized = angle_deg % 360
        nearest = round(normalized / 90) * 90
        if abs(normalized - nearest) > 1e-9:
            raise ValueError(f"仅支持 0/90/180/270 度旋转，得到 {angle_deg}")
        angle = int(nearest) % 360

        # 0 度：返回等价新实例（端口亦复制，保持不可变语义）
        if angle == 0:
            return replace(self, ports=[replace(p) for p in self.ports])

        # 旋转所有端口坐标与朝向
        new_ports = []
        for p in self.ports:
            rx, ry = _rotate_point(p.x, p.y, angle)
            new_ports.append(
                replace(p, x=rx, y=ry, direction=_rotate_direction(p.direction, angle))
            )

        # 旋转包围盒四个角点，重新计算轴对齐包围盒
        corners = [
            (self.bbox.xmin, self.bbox.ymin),
            (self.bbox.xmax, self.bbox.ymin),
            (self.bbox.xmax, self.bbox.ymax),
            (self.bbox.xmin, self.bbox.ymax),
        ]
        rotated = [_rotate_point(cx, cy, angle) for cx, cy in corners]
        xs = [c[0] for c in rotated]
        ys = [c[1] for c in rotated]
        new_bbox = BoundingBox(min(xs), min(ys), max(xs), max(ys))

        return replace(self, ports=new_ports, bbox=new_bbox)

    def footprint(self) -> tuple[float, float]:
        """返回器件占用的宽×高（μm）。

        Returns:
            ``(width, height)``，由包围盒的 xmax-xmin 与 ymax-ymin 得到。
        """
        return (self.bbox.xmax - self.bbox.xmin, self.bbox.ymax - self.bbox.ymin)
