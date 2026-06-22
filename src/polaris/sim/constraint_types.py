"""约束检查基础类型（从 constraint_checker.py 拆分，第63轮 P2-1）。

包含 ViolationType、Violation、ConstraintConfig、CheckContext 等基础数据类，
供 constraint_checker.py / constraint_checks_geometry.py / constraint_checks_performance.py
共享，避免循环导入。

来源:
- SiEPIC EBeam PDK: 设计规则
  https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- KLayout DRC runset: https://www.klayout.org/doc-qt5/manual/drc_runsets.html
- LiDAR ISPD'25: https://dl.acm.org/doi/pdf/10.1145/3698364.3705355
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ViolationType(Enum):
    """违规类型枚举。

    覆盖 SiEPIC EBeam PDK 与商业 foundry runset 常见规则类别
    （来源: https://github.com/SiEPIC/SiEPIC_EBeam_PDK；
    KLayout DRC 规则类别: https://www.klayout.org/doc-qt5/manual/drc_runsets.html）。
    """

    BEND_RADIUS = "bend_radius"  # 弯曲半径不足
    SPACING = "spacing"  # 波导间距不足
    INSERTION_LOSS = "insertion_loss"  # 插入损耗超标
    CROSSTALK = "crosstalk"  # 串扰超标
    CROSSING = "crossing"  # 波导交叉过多
    OVERLAP = "overlap"  # 器件重叠
    THERMAL = "thermal"  # 热串扰
    MIN_WIDTH = "min_width"  # 波导宽度不足
    COUPLING_GAP = "coupling_gap"  # 耦合间隙不足
    MIN_LENGTH = "min_length"  # 波导最小长度不足
    MAX_LENGTH = "max_length"  # 波导最大长度超标
    MIN_AREA = "min_area"  # 最小面积违规
    ENCLOSEMENT = "enclosure"  # 包围规则违规（内层须被外层包围）
    NOTCH = "notch"  # 凹槽间距不足（同一图形内凹处）
    PORT_CONNECTIVITY = "port_connectivity"  # 端口未连接
    PIN_MATCH = "pin_match"  # 端口宽度/类型不匹配
    LAYER_DENSITY = "layer_density"  # 层密度违规


@dataclass
class Violation:
    """约束违规记录。

    Attributes:
        vtype: 违规类型。
        severity: 严重程度（0-1，1=最严重）。
        message: 违规描述。
        device_name: 相关器件名（可选）。
        net_id: 相关网标识（可选）。
        location: 违规位置 (x, y)（可选）。
    """

    vtype: ViolationType
    severity: float = 0.0
    message: str = ""
    device_name: str = ""
    net_id: str = ""
    location: tuple[float, float] | None = None


@dataclass
class ConstraintConfig:
    """约束检查配置。

    Attributes:
        min_bend_radius_um: 最小弯曲半径（μm）。
        min_spacing_um: 最小波导间距（μm）。
        max_insertion_loss_db: 最大允许插入损耗（dB）。
        max_crosstalk_db: 最大允许串扰（dB）。
        max_crossings: 最大允许交叉数。
        safe_thermal_distance_um: 热安全距离（μm）。
        min_waveguide_width_um: 最小波导宽度（μm）。
        min_coupling_gap_um: 最小耦合间隙（μm）。
        min_waveguide_length_um: 最小波导长度（μm）。
        max_waveguide_length_um: 最大波导长度（μm）。
        min_device_area_um2: 最小器件面积（μm²）。
        min_enclosure_um: 最小包围间距（μm）。
        min_notch_um: 最小凹槽间距（μm）。
        max_layer_density: 最大层密度（0-1）。
    """

    min_bend_radius_um: float = 5.0
    min_spacing_um: float = 1.0
    max_insertion_loss_db: float = 10.0
    max_crosstalk_db: float = -20.0
    max_crossings: int = 5
    safe_thermal_distance_um: float = 100.0
    min_waveguide_width_um: float = 0.4
    min_coupling_gap_um: float = 0.1
    min_waveguide_length_um: float = 2.0
    max_waveguide_length_um: float = 10000.0
    min_device_area_um2: float = 0.1
    min_enclosure_um: float = 0.5
    min_notch_um: float = 0.3
    max_layer_density: float = 0.85


@dataclass
class CheckContext:
    """约束检查上下文（可选 DRC 输入）。

    用于向 ConstraintChecker.check 传递损耗、交叉数、波导宽度、耦合间隙等
    可选 DRC 输入，避免函数参数过多（规则 4.1：参数上限 5）。

    Attributes:
        total_loss_db: 总插入损耗（dB）。
        n_crossings: 波导交叉数。
        waveguide_widths: 波导宽度字典 {net_id: width_um}。
        coupling_gaps: 耦合间隙字典 {device_name: gap_um}。
        waveguide_lengths: 波导长度字典 {net_id: length_um}。
        device_areas: 器件面积字典 {device_name: area_um2}。
        port_connections: 端口连接状态 {port_name: connected_bool}。
        layer_densities: 层密度字典 {layer_name: density_0_to_1}。
    """

    total_loss_db: float = 0.0
    n_crossings: int = 0
    waveguide_widths: dict[str, float] | None = None
    coupling_gaps: dict[str, float] | None = None
    waveguide_lengths: dict[str, float] | None = None
    device_areas: dict[str, float] | None = None
    port_connections: dict[str, bool] | None = None
    layer_densities: dict[str, float] | None = None


__all__ = [
    "ViolationType",
    "Violation",
    "ConstraintConfig",
    "CheckContext",
]
