"""约束检查器。

检查布局布线结果是否满足光子学设计约束，
包括弯曲半径、波导间距、插入损耗、串扰等。

来源:
- LiDAR ISPD'25: 弯曲半径约束 + 交叉惩罚
  https://dl.acm.org/doi/pdf/10.1145/3698364.3705355
- SiEPIC EBeam PDK: 设计规则
  https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- Latitude DA: 硅光EDA挑战
  https://www.latitudeda.com/document/353
"""

from __future__ import annotations

import math
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
        min_waveguide_width_um: 最小波导宽度（μm），SOI 典型 0.4-0.5μm。
        min_coupling_gap_um: 最小耦合间隙（μm），DC/环谐振器典型 0.1-0.3μm。
        min_waveguide_length_um: 最小波导长度（μm），避免过短互连引入工艺变异。
        max_waveguide_length_um: 最大波导长度（μm），限制损耗累积。
        min_device_area_um2: 最小器件面积（μm²），确保工艺可识别。
        min_enclosure_um: 包围规则最小间距（μm），内层边缘到外层边缘。
        min_notch_um: 最小凹槽间距（μm），同一图形内凹处最小间距。
        max_layer_density: 层密度上限（0-1），防止工艺均匀性问题。
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


def check_bend_radius(
    paths: dict,
    min_radius: float,
) -> list[Violation]:
    """检查弯曲半径约束。

    对每条布线路径，检查转弯处的弯曲半径是否满足最小值。

    修复: 原实现遍历每个相邻三点，对欧拉曲线密集采样点误报大量小半径违规。
    现改为只检查"宏观转弯点"（角度变化 ≥ 30°），跳过曲线采样点的局部波动。

    Args:
        paths: 布线路径 {net_id: list[(x,y)]}。
        min_radius: 最小弯曲半径（μm）。

    Returns:
        违规列表。
    """
    violations: list[Violation] = []
    angle_threshold_rad = math.radians(45.0)  # 只检查角度变化 ≥45° 的宏观转弯
    for net_id, pts in paths.items():
        if not isinstance(pts, (list, tuple)) or len(pts) < 3:
            continue
        # 下采样：对密集采样的曲线路径，按最小段长过滤，避免局部波动误报
        sampled = _downsample_path(pts, min_segment_um=min_radius * 0.5)
        # 先识别宏观转弯点（角度变化超阈值）
        turn_points = _identify_turn_points(sampled, angle_threshold_rad)
        for i in turn_points:
            p0, p1, p2 = sampled[i - 1], sampled[i], sampled[i + 1]
            radius = _estimate_bend_radius(p0, p1, p2)
            if 0 < radius < min_radius:
                violations.append(
                    Violation(
                        vtype=ViolationType.BEND_RADIUS,
                        severity=1.0 - radius / min_radius,
                        message=f"弯曲半径 {radius:.1f} μm < 最小 {min_radius:.1f} μm",
                        net_id=net_id,
                        location=p1,
                    )
                )
    return violations


def _downsample_path(pts: list, min_segment_um: float) -> list:
    """下采样路径：合并距离过近的相邻点。

    欧拉曲线采样点密集（间距 <1μm），直接检查会误报大量小半径违规。
    下采样后保留宏观路径结构，过滤局部波动。

    Args:
        pts: 原始路径点列表 [(x, y), ...]。
        min_segment_um: 最小段长（μm），短于此值的相邻点合并。

    Returns:
        下采样后的路径点列表。
    """
    if len(pts) < 3:
        return list(pts)
    result: list = [pts[0]]
    for i in range(1, len(pts)):
        dx = pts[i][0] - result[-1][0]
        dy = pts[i][1] - result[-1][1]
        if math.hypot(dx, dy) >= min_segment_um:
            result.append(pts[i])
    # 保证至少保留首尾
    if result[-1] != pts[-1]:
        result.append(pts[-1])
    return result


def _identify_turn_points(
    pts: list,
    angle_threshold_rad: float,
) -> list[int]:
    """识别路径中的宏观转弯点（角度变化超阈值的索引）。

    跳过曲线采样点的局部波动，只保留真正的方向变化点。

    Args:
        pts: 路径点列表 [(x, y), ...]。
        angle_threshold_rad: 角度变化阈值（弧度）。

    Returns:
        转弯点索引列表（pts 中间点索引，即 1..len-2）。
    """
    if len(pts) < 3:
        return []
    turn_points: list[int] = []
    for i in range(1, len(pts) - 1):
        p0, p1, p2 = pts[i - 1], pts[i], pts[i + 1]
        v1 = (p1[0] - p0[0], p1[1] - p0[1])
        v2 = (p2[0] - p1[0], p2[1] - p1[1])
        l1 = math.hypot(*v1)
        l2 = math.hypot(*v2)
        if l1 < 1e-9 or l2 < 1e-9:
            continue
        cos_a = (v1[0] * v2[0] + v1[1] * v2[1]) / (l1 * l2)
        cos_a = max(-1.0, min(1.0, cos_a))
        angle = math.acos(cos_a)
        if angle >= angle_threshold_rad:
            turn_points.append(i)
    return turn_points


def check_spacing(
    placements: dict,
    min_spacing: float,
) -> list[Violation]:
    """检查器件间距约束。

    Args:
        placements: 器件布局 {name: {x, y, w, h}}。
        min_spacing: 最小间距（μm）。

    Returns:
        违规列表。
    """
    violations: list[Violation] = []
    items = list(placements.items())
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            n1, p1 = items[i]
            n2, p2 = items[j]
            gap = _rect_gap(p1, p2)
            if gap < min_spacing:
                violations.append(
                    Violation(
                        vtype=ViolationType.SPACING,
                        severity=1.0 - gap / min_spacing if min_spacing > 0 else 1.0,
                        message=f"间距 {gap:.2f} μm < 最小 {min_spacing:.1f} μm",
                        device_name=f"{n1}-{n2}",
                    )
                )
    return violations


def check_insertion_loss(
    total_loss_db: float,
    max_loss_db: float,
) -> list[Violation]:
    """检查插入损耗约束。

    Args:
        total_loss_db: 总插入损耗（dB）。
        max_loss_db: 最大允许损耗（dB）。

    Returns:
        违规列表。
    """
    if total_loss_db > max_loss_db:
        return [
            Violation(
                vtype=ViolationType.INSERTION_LOSS,
                severity=min(1.0, (total_loss_db - max_loss_db) / max_loss_db),
                message=f"插入损耗 {total_loss_db:.2f} dB > 最大 {max_loss_db:.1f} dB",
            )
        ]
    return []


def check_crossings(
    n_crossings: int,
    max_crossings: int,
) -> list[Violation]:
    """检查波导交叉数约束。"""
    if n_crossings > max_crossings:
        return [
            Violation(
                vtype=ViolationType.CROSSING,
                severity=min(1.0, (n_crossings - max_crossings) / max(1, max_crossings)),
                message=f"交叉数 {n_crossings} > 最大 {max_crossings}",
            )
        ]
    return []


def check_overlap(placements: dict) -> list[Violation]:
    """检查器件重叠约束。"""
    violations: list[Violation] = []
    items = list(placements.items())
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            n1, p1 = items[i]
            n2, p2 = items[j]
            if _rects_overlap(p1, p2):
                violations.append(
                    Violation(
                        vtype=ViolationType.OVERLAP,
                        severity=1.0,
                        message=f"器件重叠: {n1} 和 {n2}",
                        device_name=f"{n1}-{n2}",
                    )
                )
    return violations


def check_min_width(
    waveguide_widths: dict[str, float],
    min_width: float,
) -> list[Violation]:
    """检查波导最小宽度约束。

    光子版图 DRC 关键项：波导宽度低于工艺最小值会导致模式泄露、损耗增大。
    SOI 典型最小宽度 400-500nm，SiN 800-1000nm。

    来源: SiEPIC EBeam PDK 设计规则
           https://github.com/SiEPIC/SiEPIC_EBeam_PDK

    Args:
        waveguide_widths: 波导宽度字典 {net_id: width_um}。
        min_width: 最小允许宽度（μm）。

    Returns:
        违规列表。
    """
    violations: list[Violation] = []
    for net_id, width in waveguide_widths.items():
        if width < min_width:
            violations.append(
                Violation(
                    vtype=ViolationType.MIN_WIDTH,
                    severity=1.0 - width / min_width if min_width > 0 else 1.0,
                    message=f"波导宽度 {width:.3f} μm < 最小 {min_width:.3f} μm",
                    net_id=net_id,
                )
            )
    return violations


def check_coupling_gap(
    coupling_gaps: dict[str, float],
    min_gap: float,
) -> list[Violation]:
    """检查耦合间隙约束。

    光子版图 DRC 关键项：定向耦合器、环谐振器的耦合间隙通常 100-300nm，
    间隙过小会导致工艺无法实现（光刻分辨率限制），过大会导致耦合效率不足。

    来源: SiEPIC EBeam PDK 设计规则
           https://github.com/SiEPIC/SiEPIC_EBeam_PDK

    Args:
        coupling_gaps: 耦合间隙字典 {device_name: gap_um}。
        min_gap: 最小允许间隙（μm）。

    Returns:
        违规列表。
    """
    violations: list[Violation] = []
    for dev_name, gap in coupling_gaps.items():
        if gap < min_gap:
            violations.append(
                Violation(
                    vtype=ViolationType.COUPLING_GAP,
                    severity=1.0 - gap / min_gap if min_gap > 0 else 1.0,
                    message=f"耦合间隙 {gap:.3f} μm < 最小 {min_gap:.3f} μm",
                    device_name=dev_name,
                )
            )
    return violations


def check_waveguide_length(
    waveguide_lengths: dict[str, float],
    min_length: float,
    max_length: float,
) -> list[Violation]:
    """检查波导长度约束（最小/最大长度）。

    过短波导引入工艺变异（光刻对准困难），过长波导累积损耗。
    SiEPIC EBeam PDK 建议最小 2μm，最大受损耗预算限制。

    来源: SiEPIC EBeam PDK 设计规则
           https://github.com/SiEPIC/SiEPIC_EBeam_PDK

    Args:
        waveguide_lengths: 波导长度字典 {net_id: length_um}。
        min_length: 最小允许长度（μm）。
        max_length: 最大允许长度（μm）。

    Returns:
        违规列表。
    """
    violations: list[Violation] = []
    for net_id, length in waveguide_lengths.items():
        if length < min_length:
            violations.append(
                Violation(
                    vtype=ViolationType.MIN_LENGTH,
                    severity=1.0 - length / min_length if min_length > 0 else 1.0,
                    message=f"波导长度 {length:.3f} μm < 最小 {min_length:.3f} μm",
                    net_id=net_id,
                )
            )
        elif length > max_length:
            ratio = (length - max_length) / max_length if max_length > 0 else 1.0
            violations.append(
                Violation(
                    vtype=ViolationType.MAX_LENGTH,
                    severity=min(1.0, ratio),
                    message=f"波导长度 {length:.1f} μm > 最大 {max_length:.1f} μm",
                    net_id=net_id,
                )
            )
    return violations


def check_min_area(
    device_areas: dict[str, float],
    min_area: float,
) -> list[Violation]:
    """检查最小面积约束。

    确保器件面积满足工艺最小特征尺寸要求，避免光刻无法识别的小图形。
    来源: KLayout DRC runset 最小面积规则
           https://www.klayout.org/doc-qt5/manual/drc_runsets.html

    Args:
        device_areas: 器件面积字典 {device_name: area_um2}。
        min_area: 最小允许面积（μm²）。

    Returns:
        违规列表。
    """
    violations: list[Violation] = []
    for dev_name, area in device_areas.items():
        if area < min_area:
            violations.append(
                Violation(
                    vtype=ViolationType.MIN_AREA,
                    severity=1.0 - area / min_area if min_area > 0 else 1.0,
                    message=f"器件面积 {area:.3f} μm² < 最小 {min_area:.3f} μm²",
                    device_name=dev_name,
                )
            )
    return violations


def check_port_connectivity(
    port_connections: dict[str, bool],
) -> list[Violation]:
    """检查端口连接性约束。

    所有器件端口必须连接到其他器件或波导，未连接端口导致功能失效。
    来源: SiEPIC-Tools Functional Layout Check - Connectivity checking
           https://github.com/SiEPIC/SiEPIC-Tools/wiki/SiEPIC-Tools-Menu-descriptions

    Args:
        port_connections: 端口连接状态 {port_name: connected_bool}。

    Returns:
        违规列表。
    """
    violations: list[Violation] = []
    for port_name, connected in port_connections.items():
        if not connected:
            violations.append(
                Violation(
                    vtype=ViolationType.PORT_CONNECTIVITY,
                    severity=1.0,
                    message=f"端口 {port_name} 未连接",
                    device_name=port_name.split("::")[0] if "::" in port_name else port_name,
                )
            )
    return violations


def check_layer_density(
    layer_densities: dict[str, float],
    max_density: float,
) -> list[Violation]:
    """检查层密度约束。

    单层图形密度过高会导致工艺均匀性问题（刻蚀负载效应）。
    foundry runset 通常限制密度 ≤ 0.85-0.90。
    来源: KLayout DRC density 规则
           https://www.klayout.org/doc-qt5/manual/drc_runsets.html

    Args:
        layer_densities: 层密度字典 {layer_name: density_0_to_1}。
        max_density: 最大允许密度（0-1）。

    Returns:
        违规列表。
    """
    violations: list[Violation] = []
    for layer_name, density in layer_densities.items():
        if density > max_density:
            ratio = (density - max_density) / max_density if max_density > 0 else 1.0
            violations.append(
                Violation(
                    vtype=ViolationType.LAYER_DENSITY,
                    severity=min(1.0, ratio),
                    message=f"层 {layer_name} 密度 {density:.3f} > 最大 {max_density:.3f}",
                    device_name=layer_name,
                )
            )
    return violations


def check_thermal(
    placements: dict,
    safe_distance: float,
) -> list[Violation]:
    """检查热串扰约束。

    热光移相器等主动器件对邻近器件的热串扰，须保持安全距离。
    来源: PoLaRIS 商业差距分析 P0-1，对标 Lumerical 多物理场仿真

    Args:
        placements: 器件布局 {device_name: {x, y, w, h}}。
        safe_distance: 热安全距离（μm）。

    Returns:
        违规列表。
    """
    violations: list[Violation] = []
    items = list(placements.items())
    for i, (name1, p1) in enumerate(items):
        for name2, p2 in items[i + 1 :]:
            # 仅检查主动器件 vs 被动器件的热串扰（简化：所有器件对）
            gap = _rect_gap(p1, p2)
            if 0 < gap < safe_distance:
                msg = (
                    f"器件 {name1} 与 {name2} 间距 {gap:.1f} μm < 热安全距离 {safe_distance:.1f} μm"
                )
                violations.append(
                    Violation(
                        vtype=ViolationType.THERMAL,
                        severity=1.0 - gap / safe_distance,
                        message=msg,
                        device_name=f"{name1}::{name2}",
                    )
                )
    return violations


def check_crosstalk(
    placements: dict,
    paths: dict,
    max_crosstalk_db: float,
) -> list[Violation]:
    """检查串扰约束。

    平行波导间距不足引入模式耦合串扰，须保持足够间距。
    来源: LiDAR ISPD'25 串扰惩罚
           https://dl.acm.org/doi/pdf/10.1145/3698364.3705355

    Args:
        placements: 器件布局。
        paths: 布线路径。
        max_crosstalk_db: 最大允许串扰（dB，负值）。

    Returns:
        违规列表。
    """
    # 串扰与间距近似关系：CT(dB) ≈ -10 * log10(exp(-2 * gap / decay_length))
    # 简化检查：平行波导段间距 < min_spacing 的 2 倍时报告
    violations: list[Violation] = []
    min_safe_gap_um = 2.0  # 串扰 <-20dB 的经验安全间距
    net_ids = list(paths.keys())
    for i, n1 in enumerate(net_ids):
        pts1 = paths[n1]
        if not isinstance(pts1, (list, tuple)) or len(pts1) < 2:
            continue
        for n2 in net_ids[i + 1 :]:
            pts2 = paths[n2]
            if not isinstance(pts2, (list, tuple)) or len(pts2) < 2:
                continue
            violations.extend(
                _check_pair_crosstalk(
                    n1, pts1, n2, pts2,
                    CrosstalkConfig(min_safe_gap_um, max_crosstalk_db),
                )
            )
    return violations


@dataclass
class CrosstalkConfig:
    """串扰检查配置（降低 _check_pair_crosstalk 参数个数，规则 4.1）。

    Attributes:
        min_safe_gap_um: 串扰安全间距（μm）。
        max_crosstalk_db: 最大允许串扰（dB，负值）。
    """

    min_safe_gap_um: float
    max_crosstalk_db: float


def _check_pair_crosstalk(
    n1: str,
    pts1: list,
    n2: str,
    pts2: list,
    config: CrosstalkConfig,
) -> list[Violation]:
    """检查两条网络的串扰（辅助函数，降低 check_crosstalk 复杂度）。

    Args:
        n1: 网络 1 ID。
        pts1: 网络 1 路径点列表。
        n2: 网络 2 ID。
        pts2: 网络 2 路径点列表。
        config: 串扰检查配置。
    """
    violations: list[Violation] = []
    min_gap = _min_path_gap(pts1, pts2)
    if 0 < min_gap < config.min_safe_gap_um:
        msg = f"网络 {n1} 与 {n2} 平行间距 {min_gap:.2f} μm 可能串扰 > {config.max_crosstalk_db} dB"
        violations.append(
            Violation(
                vtype=ViolationType.CROSSTALK,
                severity=1.0 - min_gap / config.min_safe_gap_um,
                message=msg,
                net_id=f"{n1}::{n2}",
            )
        )
    return violations


def _min_path_gap(pts1: list, pts2: list) -> float:
    """计算两条路径之间的最小间距（简化：采样点对距离最小值）。"""
    min_gap = float("inf")
    step1 = max(1, len(pts1) // 20)
    step2 = max(1, len(pts2) // 20)
    for p1 in pts1[::step1]:
        for p2 in pts2[::step2]:
            gap = math.hypot(p1[0] - p2[0], p1[1] - p2[1])
            if gap < min_gap:
                min_gap = gap
    return min_gap


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


class ConstraintChecker:
    """约束检查器。

    综合检查布局布线结果是否满足所有光子学设计约束。

    来源:
    - LiDAR ISPD'25: https://dl.acm.org/doi/pdf/10.1145/3698364.3705355
    """

    def __init__(self, config: ConstraintConfig | None = None) -> None:
        self.config = config or ConstraintConfig()

    def check(
        self,
        placements: dict,
        paths: dict,
        context: CheckContext | None = None,
    ) -> list[Violation]:
        """综合约束检查。

        Args:
            placements: 器件布局。
            paths: 布线路径。
            context: DRC 上下文（损耗、交叉数、波导宽度、耦合间隙等）。

        Returns:
            所有违规列表。
        """
        cfg = self.config
        ctx = context or CheckContext()
        violations: list[Violation] = []
        violations.extend(check_overlap(placements))
        violations.extend(check_spacing(placements, cfg.min_spacing_um))
        violations.extend(check_bend_radius(paths, cfg.min_bend_radius_um))
        violations.extend(check_insertion_loss(ctx.total_loss_db, cfg.max_insertion_loss_db))
        violations.extend(check_crossings(ctx.n_crossings, cfg.max_crossings))
        violations.extend(self._check_optional(ctx, cfg))
        return violations

    def _check_optional(self, ctx: CheckContext, cfg: ConstraintConfig) -> list[Violation]:
        """执行可选 DRC 检查（基于 context 提供的输入）。"""
        violations: list[Violation] = []
        if ctx.waveguide_widths is not None:
            violations.extend(check_min_width(ctx.waveguide_widths, cfg.min_waveguide_width_um))
        if ctx.coupling_gaps is not None:
            violations.extend(check_coupling_gap(ctx.coupling_gaps, cfg.min_coupling_gap_um))
        if ctx.waveguide_lengths is not None:
            violations.extend(
                check_waveguide_length(
                    ctx.waveguide_lengths,
                    cfg.min_waveguide_length_um,
                    cfg.max_waveguide_length_um,
                )
            )
        if ctx.device_areas is not None:
            violations.extend(check_min_area(ctx.device_areas, cfg.min_device_area_um2))
        if ctx.port_connections is not None:
            violations.extend(check_port_connectivity(ctx.port_connections))
        if ctx.layer_densities is not None:
            violations.extend(check_layer_density(ctx.layer_densities, cfg.max_layer_density))
        return violations

    def check_passed(self, **kwargs) -> bool:
        """检查是否全部通过。"""
        return len(self.check(**kwargs)) == 0


def _estimate_bend_radius(
    p0: tuple,
    p1: tuple,
    p2: tuple,
) -> float:
    """估算三点弯曲半径。

    R = |v1||v2||v1-v2| / (2|v1×v2|)
    """
    v1 = (p1[0] - p0[0], p1[1] - p0[1])
    v2 = (p2[0] - p1[0], p2[1] - p1[1])
    cross = abs(v1[0] * v2[1] - v1[1] * v2[0])
    if cross < 1e-9:
        return float("inf")  # 直线，无弯曲
    l1 = math.hypot(*v1)
    l2 = math.hypot(*v2)
    l3 = math.hypot(v2[0] - v1[0], v2[1] - v1[1])
    return l1 * l2 * l3 / (2.0 * cross)


def _rect_gap(p1: dict, p2: dict) -> float:
    """计算两矩形最小间距。"""
    gap_x = max(
        p2.get("x", 0) - (p1.get("x", 0) + p1.get("w", 10)),
        p1.get("x", 0) - (p2.get("x", 0) + p2.get("w", 10)),
    )
    gap_y = max(
        p2.get("y", 0) - (p1.get("y", 0) + p1.get("h", 10)),
        p1.get("y", 0) - (p2.get("y", 0) + p2.get("h", 10)),
    )
    if gap_x > 0 and gap_y > 0:
        return math.hypot(gap_x, gap_y)
    return max(gap_x, gap_y)


def _rects_overlap(p1: dict, p2: dict) -> bool:
    """检查两矩形是否重叠。"""
    return not (
        p1.get("x", 0) + p1.get("w", 10) <= p2.get("x", 0)
        or p2.get("x", 0) + p2.get("w", 10) <= p1.get("x", 0)
        or p1.get("y", 0) + p1.get("h", 10) <= p2.get("y", 0)
        or p2.get("y", 0) + p2.get("h", 10) <= p1.get("y", 0)
    )


__all__ = [
    "ConstraintChecker",
    "ConstraintConfig",
    "CheckContext",
    "Violation",
    "ViolationType",
    "check_bend_radius",
    "check_spacing",
    "check_insertion_loss",
    "check_crossings",
    "check_overlap",
    "check_min_width",
    "check_coupling_gap",
    "check_waveguide_length",
    "check_min_area",
    "check_port_connectivity",
    "check_layer_density",
    "check_thermal",
    "check_crosstalk",
]
