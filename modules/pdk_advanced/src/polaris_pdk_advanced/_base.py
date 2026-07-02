"""高级 PDK 基础数据类（Port/Direction/BoundingBox/Device/Source）。

从 v4 旧包 src/polaris/pdk/{port,device,source}.py 迁移核心数据结构，
供本子模块的 gdsfactory_bridge / pcell / optodesigner / vpi_pdk 等模块共享。
polaris-pdk 子模块（catalog）仅含纯 dict 器件目录，不含这些类，故在此独立定义。

设计原则:
- 不可变 dataclass（frozen 或 replace 语义），便于安全共享
- 字段对齐 IPKISS PCell / gdsfactory Component 核心信息
- 禁止 fall-back（R03）：参数校验失败 raise
- 纯数据结构（R04: 不参与 GPU）

学术依据（R02 学术诚信）:
- IPKISS/Luceda PDK PCell+Port 模型:
  https://academy.lucedaphotonics.com/pdks/cornerstone/cornerstone
- KLayoutPhotonicPCells 端口追踪:
  https://sebastian-goeldi.github.io/KLayoutPhotonicPCells-core/_modules/kppc/photonics.html
- gdsfactory Component metadata:
  https://gdsfactory.github.io/gdsfactory/
- SiEPIC EBeam PDK 器件模型标准:
  https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- Chrostowski & Hochberg, Silicon Photonics Design, CUP 2015:
  https://www.cambridge.org/9781107085459

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R05 Bug 必修。
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum


class Direction(Enum):
    """端口朝向（光子版图常用四正方向，便于直角旋转与曼哈顿布线）。

    采用标准数学坐标系（y 轴朝上、x 轴朝右）：
    NORTH 朝 +y，SOUTH 朝 -y，EAST 朝 +x，WEST 朝 -x。
    """

    NORTH = "north"
    SOUTH = "south"
    EAST = "east"
    WEST = "west"


@dataclass
class Port:
    """器件端口（相对器件原点定义）。

    Attributes:
        name: 端口名（如 in/out/in1/out1）。
        x: 相对原点 x 坐标（μm）。
        y: 相对原点 y 坐标（μm）。
        direction: 朝向（光波导出射方向）。
        waveguide_type: 波导类型（如 strip/rib/sin_strip）。
        width: 模式宽度（μm），用于连接时宽度匹配校验。
    """

    name: str
    x: float
    y: float
    direction: Direction
    waveguide_type: str
    width: float


@dataclass
class BoundingBox:
    """器件包围盒（μm），轴对齐包围盒（AABB）。

    与 gdspy get_bounding_box 返回的 [[xmin,ymin],[xmax,ymax]] 语义一致。
    来源: https://gdspy.readthedocs.io/en/stable/reference.html
    """

    xmin: float
    ymin: float
    xmax: float
    ymax: float


@dataclass(frozen=True)
class Source:
    """文献来源（禁止假数据，每个参数须可溯源）。

    采用 frozen=True 使其不可变，便于作为器件 source 字段安全共享。

    Attributes:
        title: 文献/手册标题。
        authors: 作者或机构。
        year: 发表年份。
        url: 网址 URL（必填，溯源校验时须非空）。
        note: 备注（如 estimated 标注无可靠文献时的估算依据）。
    """

    title: str
    authors: str
    year: int
    url: str
    note: str = ""


# 逆时针 90 度方向映射表：N -> W -> S -> E -> N
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
        旋转后的 (new_x, new_y) 坐标（μm）。

    Raises:
        ValueError: 角度非 0/90/180/270 度。
    """
    if angle_deg == 0:
        return x, y
    if angle_deg == 90:
        return -y, x
    if angle_deg == 180:
        return -x, -y
    if angle_deg == 270:
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

    字段对齐 IPKISS PCell 与 gdsfactory Component 的核心信息：
    唯一标识、工艺平台、器件类别、端口列表、包围盒、电光参数、
    文献来源与设计约束。所有参数须可溯源（见 source 字段）。

    Attributes:
        device_id: 唯一标识。
        platform: 工艺平台（SOI/SiN/InP/LNOI）。
        category: 器件类别（passive/active/source/detector）。
        name: 器件类型名（如 ring_resonator）。
        ports: 端口列表（相对器件原点定义）。
        bbox: 器件包围盒（μm）。
        params: 电光参数字典（含单位，如 {"loss_db_cm": 2.0}）。
        source: 文献来源（每个参数须可溯源）。
        constraints: 设计约束（最小间距/弯曲半径/禁布区等）。
        process_node: 工艺节点标识（如 "220nm SOI"）。
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
    process_node: str | None = None

    def translate(self, dx: float, dy: float) -> Device:
        """平移器件（返回新实例，端口与包围盒同步更新）。

        Args:
            dx: x 方向平移量（μm）。
            dy: y 方向平移量（μm）。

        Returns:
            平移后的新 Device 实例，原实例不变。
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

        采用逆时针旋转（标准数学坐标系），与 gdspy.rotate 及 IPKISS angle
        参数约定一致。端口坐标、朝向与包围盒同步更新。

        Args:
            angle_deg: 旋转角度（须为 90/180/270 度的整数倍）。

        Returns:
            旋转后的新 Device 实例，原实例不变。

        Raises:
            ValueError: 角度非直角旋转。
        """
        normalized = angle_deg % 360
        nearest = round(normalized / 90) * 90
        if abs(normalized - nearest) > 1e-9:
            raise ValueError(f"仅支持 0/90/180/270 度旋转，得到 {angle_deg}")
        angle = int(nearest) % 360
        if angle == 0:
            return replace(self, ports=[replace(p) for p in self.ports])
        new_ports = [
            replace(
                p,
                x=_rotate_point(p.x, p.y, angle)[0],
                y=_rotate_point(p.x, p.y, angle)[1],
                direction=_rotate_direction(p.direction, angle),
            )
            for p in self.ports
        ]
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
        """返回器件占用的宽×高（μm）。"""
        return (self.bbox.xmax - self.bbox.xmin, self.bbox.ymax - self.bbox.ymin)


__all__ = [
    "BoundingBox",
    "Device",
    "Direction",
    "Port",
    "Source",
]
