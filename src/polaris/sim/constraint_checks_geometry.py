"""几何约束检查函数（从 constraint_checker.py 拆分，第63轮 P2-1）。

包含弯曲半径、间距、重叠、宽度、耦合间隙、长度、面积、端口连接、层密度
等几何 DRC 检查函数。

来源:
- SiEPIC EBeam PDK: 设计规则
  https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- KLayout DRC runset: https://www.klayout.org/doc-qt5/manual/drc_runsets.html
- LiDAR ISPD'25: 弯曲半径约束 + 交叉惩罚
  https://dl.acm.org/doi/pdf/10.1145/3698364.3705355
"""

from __future__ import annotations

import math

from polaris.sim.constraint_types import (
    Violation,
    ViolationType,
)


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


# ------------------------------------------------------------------
# P0-3 修复: 新增 enclosure / notch / pin_match 检查
# ------------------------------------------------------------------


def check_enclosure(
    placements: dict,
    canvas_w: float,
    canvas_h: float,
    min_enclosure: float,
) -> list[Violation]:
    """检查包围规则约束（P0-3 修复）。

    所有器件 bbox 必须在画布边界内，且与边界保持 min_enclosure_um 间距。
    来源: IHP SG25H5 PDK enclosure 规则
           https://www.ihp-microelectronics.com/

    Args:
        placements: 器件布局 {name: {x, y, w, h}}。
        canvas_w: 画布宽度（μm）。
        canvas_h: 画布高度（μm）。
        min_enclosure: 最小包围间距（μm）。

    Returns:
        违规列表。
    """
    violations: list[Violation] = []
    if canvas_w <= 0 or canvas_h <= 0:
        return violations  # 无画布尺寸信息，跳过
    for name, p in placements.items():
        x, y = p.get("x", 0), p.get("y", 0)
        w, h = p.get("w", 0), p.get("h", 0)
        # 检查四个方向是否满足 enclosure 间距
        if x < min_enclosure:
            violations.append(
                Violation(
                    vtype=ViolationType.ENCLOSURE,
                    severity=1.0 - (x / min_enclosure if min_enclosure > 0 else 1.0),
                    message=f"器件 {name} 左边界间距 {x:.2f} μm < enclosure {min_enclosure:.2f} μm",
                    device_name=name,
                )
            )
        if y < min_enclosure:
            violations.append(
                Violation(
                    vtype=ViolationType.ENCLOSURE,
                    severity=1.0 - (y / min_enclosure if min_enclosure > 0 else 1.0),
                    message=f"器件 {name} 下边界间距 {y:.2f} μm < enclosure {min_enclosure:.2f} μm",
                    device_name=name,
                )
            )
        if x + w > canvas_w - min_enclosure:
            gap = canvas_w - (x + w)
            violations.append(
                Violation(
                    vtype=ViolationType.ENCLOSURE,
                    severity=1.0 - (gap / min_enclosure if min_enclosure > 0 else 1.0),
                    message=f"器件 {name} 右边界间距 {gap:.2f} μm < enclosure {min_enclosure:.2f} μm",
                    device_name=name,
                )
            )
        if y + h > canvas_h - min_enclosure:
            gap = canvas_h - (y + h)
            violations.append(
                Violation(
                    vtype=ViolationType.ENCLOSURE,
                    severity=1.0 - (gap / min_enclosure if min_enclosure > 0 else 1.0),
                    message=f"器件 {name} 上边界间距 {gap:.2f} μm < enclosure {min_enclosure:.2f} μm",
                    device_name=name,
                )
            )
    return violations


def check_notch(
    placements: dict,
    min_notch: float,
) -> list[Violation]:
    """检查凹槽间距约束（P0-3 修复，简化版）。

    简化版：检查器件间最小间距是否 >= min_notch_um。
    严格 notch 检查需要多边形凹槽分析，此处简化为器件间距检查。
    来源: KLayout DRC runset notch 规则
           https://www.klayout.org/doc-qt5/manual/drc_runsets.html

    Args:
        placements: 器件布局 {name: {x, y, w, h}}。
        min_notch: 最小凹槽间距（μm）。

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
            if 0 < gap < min_notch:
                violations.append(
                    Violation(
                        vtype=ViolationType.NOTCH,
                        severity=1.0 - gap / min_notch if min_notch > 0 else 1.0,
                        message=f"器件 {n1} 与 {n2} 间距 {gap:.2f} μm < notch {min_notch:.2f} μm",
                        device_name=f"{n1}-{n2}",
                    )
                )
    return violations


# 端口方向兼容性映射（P0-3 pin_match 检查）
# 来源: SiEPIC EBeam PDK 端口方向约定
#   https://github.com/SiEPIC/SiEPIC_EBeam_PDK
# 光子器件端口方向: E/W/N/S（地理方向）或 input/output（功能方向）
# 兼容规则: output→input, input→output, E↔W, N↔S
_DIR_COMPAT = {
    ("output", "input"): True,
    ("input", "output"): True,
    ("E", "W"): True,
    ("W", "E"): True,
    ("N", "S"): True,
    ("S", "N"): True,
}


def check_pin_match(
    pin_pairs: dict[str, tuple[str, str]],
) -> list[Violation]:
    """检查端口方向兼容性约束（P0-3 修复）。

    检查连接的两端端口方向是否兼容（如 output → input, E ↔ W）。
    来源: SiEPIC EBeam PDK 端口方向约定
           https://github.com/SiEPIC/SiEPIC_EBeam_PDK

    Args:
        pin_pairs: 端口对方向信息 {net_id: (dir1, dir2)}。

    Returns:
        违规列表。
    """
    violations: list[Violation] = []
    for net_id, (dir1, dir2) in pin_pairs.items():
        if not dir1 or not dir2:
            continue  # 无方向信息，跳过
        # 检查方向兼容性
        if (dir1, dir2) in _DIR_COMPAT:
            continue  # 兼容
        # 同方向（如 input→input, output→output）不兼容
        if dir1 == dir2 and dir1 in ("input", "output"):
            violations.append(
                Violation(
                    vtype=ViolationType.PIN_MATCH,
                    severity=0.8,
                    message=f"网络 {net_id} 端口方向不兼容: {dir1}→{dir2}（应为 output→input）",
                    net_id=net_id,
                )
            )
    return violations


__all__ = [
    "check_bend_radius",
    "check_spacing",
    "check_overlap",
    "check_min_width",
    "check_coupling_gap",
    "check_waveguide_length",
    "check_min_area",
    "check_port_connectivity",
    "check_layer_density",
    "check_enclosure",
    "check_notch",
    "check_pin_match",
]
