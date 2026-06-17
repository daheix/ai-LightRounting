"""器件端口数据类（SubTask 2.2）。

端口定义器件与外部波导的连接点：相对器件原点的坐标、朝向、波导类型与模式宽度。
端口模型参考光子 PDK 业界最佳实践：
- IPKISS/Luceda PDK 的 ``Port`` 概念（位置 + 朝向 + 波导模板宽度）
  来源: https://academy.lucedaphotonics.com/pdks/cornerstone/cornerstone
- KLayoutPhotonicPCells 的 ``PortCreation``（x, y, rot, length, name；
  端口追踪位置、朝向与宽度）
  来源: https://sebastian-goeldi.github.io/KLayoutPhotonicPCells-core/_modules/kppc/photonics.html
- gdsfactory 端口扩展（layer / port_type / cross_section）
  来源: https://pypi.org/project/gdsfactory/4.4.14/
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Direction(Enum):
    """端口朝向（光子版图常用四正方向，便于直角旋转与曼哈顿布线）。

    采用标准数学坐标系（y 轴朝上、x 轴朝右）：
    ``NORTH`` 朝 +y，``SOUTH`` 朝 -y，``EAST`` 朝 +x，``WEST`` 朝 -x。
    """

    NORTH = "north"
    SOUTH = "south"
    EAST = "east"
    WEST = "west"


@dataclass
class Port:
    """器件端口（相对器件原点定义）。

    Attributes:
        name: 端口名（如 ``in``、``out``、``in1``、``out1``）。
        x: 相对原点 x 坐标（μm）。
        y: 相对原点 y 坐标（μm）。
        direction: 朝向（光波导出射方向）。
        waveguide_type: 波导类型（如 ``strip``、``rib``、``sin_strip``）。
        width: 模式宽度（μm），用于连接时宽度匹配校验。
    """

    name: str
    x: float
    y: float
    direction: Direction
    waveguide_type: str
    width: float
