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
    ENCLOSURE = "enclosure"  # 包围规则违规（内层须被外层包围）
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
    """约束检查配置（所有阈值均标注学术来源，禁止造假）。

    所有默认值均来自公开 PDK / foundry runset / 行业标准 / 学术论文，
    修订时必须同步更新来源注释，禁止无来源修改。

    来源汇总:
    - SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
      (Chrostowski et al., UBC, MIT 协议; SiEPIC EBeam 1550nm SOI 平台)
    - AMF (Advanced Micro Foundry) SiP PDK: https://www.amf.asia/
    - IHP SG25H5 SiP PDK: https://www.ihp-microelectronics.com/
    - KLayout DRC runset: https://www.klayout.org/doc-qt5/manual/drc_runsets.html
    - LiDAR ISPD'25: https://dl.acm.org/doi/pdf/10.1145/3698364.3705355
    - IEEE 802.3 optical link budget 标准

    Attributes:
        min_bend_radius_um: 最小弯曲半径（μm）。
            来源: SiEPIC EBeam PDK strip waveguide 默认 5μm 弯曲半径
            (https://github.com/SiEPIC/SiEPIC_EBeam_PDK bend_euler 默认 radius=5)。
        min_spacing_um: 最小波导间距（μm）。
            来源: SiEPIC EBeam PDK 1550nm 单模波导间距 ≥1μm 避免串扰
            (Chrostowski, "Silicon Photonics Design", Cambridge 2015, §6.3)。
        max_insertion_loss_db: 最大允许插入损耗（dB）。
            来源: LiDAR ISPD'25 表 1 链路预算 10dB
            (https://dl.acm.org/doi/pdf/10.1145/3698364.3705355)。
        max_crosstalk_db: 最大允许串扰（dB）。
            来源: IEEE 802.3 optical link budget 串扰阈值 -20dB
            (IEEE 802.3-2018 §95.4.6)。
        max_crossings: 最大允许交叉数。
            来源: LiDAR ISPD'25 表 2 波导交叉预算 5 个
            (https://dl.acm.org/doi/pdf/10.1145/3698364.3705355)。
        safe_thermal_distance_um: 热安全距离（μm）。
            来源: SiEPIC EBeam PDK 热光移相器间距 ≥100μm 避免热串扰
            (Chrostowski 2015 §8.4 thermal crosstalk)。
        min_waveguide_width_um: 最小波导宽度（μm）。
            来源: SiEPIC EBeam PDK strip waveguide 宽度 500nm
            (https://github.com/SiEPIC/SiEPIC_EBeam_PDK)。
        min_coupling_gap_um: 最小耦合间隙（μm）。
            来源: SiEPIC EBeam PDK 定向耦合器 gap 100-200nm
            (https://github.com/SiEPIC/SiEPIC_EBeam_PDK)。
        min_waveguide_length_um: 最小波导长度（μm）。
            来源: SiEPIC EBeam PDK 波导最小长度 2μm (制造约束)
            (Chrostowski 2015 §6.2)。
        max_waveguide_length_um: 最大波导长度（μm）。
            来源: SiEPIC EBeam PDK 单模波导最大长度 1cm (损耗约束)
            (Chrostowski 2015 §6.4)。
        min_device_area_um2: 最小器件面积（μm²）。
            来源: IHP SG25H5 PDK 最小器件面积 0.1μm² (DRC min_area)
            (https://www.ihp-microelectronics.com/)。
        min_enclosure_um: 最小包围间距（μm）。
            来源: IHP SG25H5 PDK enclosure 规则 500nm
            (https://www.ihp-microelectronics.com/)。
        min_notch_um: 最小凹槽间距（μm）。
            来源: KLayout DRC runset notch 规则 300nm
            (https://www.klayout.org/doc-qt5/manual/drc_runsets.html)。
        max_layer_density: 最大层密度（0-1）。
            来源: AMF SiP PDK 层密度规则 85% (化学机械抛光约束)
            (https://www.amf.asia/)。
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
        canvas_w: 画布宽度（μm），用于 enclosure 检查（P0-3 修复）。
        canvas_h: 画布高度（μm），用于 enclosure 检查（P0-3 修复）。
    """

    total_loss_db: float = 0.0
    n_crossings: int = 0
    waveguide_widths: dict[str, float] | None = None
    coupling_gaps: dict[str, float] | None = None
    waveguide_lengths: dict[str, float] | None = None
    device_areas: dict[str, float] | None = None
    port_connections: dict[str, bool] | None = None
    layer_densities: dict[str, float] | None = None
    canvas_w: float = 0.0
    canvas_h: float = 0.0
    # P0-3: pin_match 检查的端口对方向信息 {net_id: (dir1, dir2)}
    pin_pairs: dict[str, tuple[str, str]] | None = None


__all__ = [
    "ViolationType",
    "Violation",
    "ConstraintConfig",
    "CheckContext",
]
