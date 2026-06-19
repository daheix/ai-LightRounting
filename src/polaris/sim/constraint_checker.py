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
    """违规类型枚举。"""

    BEND_RADIUS = "bend_radius"  # 弯曲半径不足
    SPACING = "spacing"  # 波导间距不足
    INSERTION_LOSS = "insertion_loss"  # 插入损耗超标
    CROSSTALK = "crosstalk"  # 串扰超标
    CROSSING = "crossing"  # 波导交叉过多
    OVERLAP = "overlap"  # 器件重叠
    THERMAL = "thermal"  # 热串扰
    MIN_WIDTH = "min_width"  # 波导宽度不足
    COUPLING_GAP = "coupling_gap"  # 耦合间隙不足


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
    """

    min_bend_radius_um: float = 5.0
    min_spacing_um: float = 1.0
    max_insertion_loss_db: float = 10.0
    max_crosstalk_db: float = -20.0
    max_crossings: int = 5
    safe_thermal_distance_um: float = 100.0
    min_waveguide_width_um: float = 0.4
    min_coupling_gap_um: float = 0.1


def check_bend_radius(
    paths: dict,
    min_radius: float,
) -> list[Violation]:
    """检查弯曲半径约束。

    对每条布线路径，检查转弯处的弯曲半径是否满足最小值。

    Args:
        paths: 布线路径 {net_id: list[(x,y)]}。
        min_radius: 最小弯曲半径（μm）。

    Returns:
        违规列表。
    """
    violations: list[Violation] = []
    for net_id, pts in paths.items():
        if not isinstance(pts, (list, tuple)) or len(pts) < 3:
            continue
        for i in range(1, len(pts) - 1):
            p0, p1, p2 = pts[i - 1], pts[i], pts[i + 1]
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
    """

    total_loss_db: float = 0.0
    n_crossings: int = 0
    waveguide_widths: dict[str, float] | None = None
    coupling_gaps: dict[str, float] | None = None


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
        if ctx.waveguide_widths is not None:
            violations.extend(check_min_width(ctx.waveguide_widths, cfg.min_waveguide_width_um))
        if ctx.coupling_gaps is not None:
            violations.extend(check_coupling_gap(ctx.coupling_gaps, cfg.min_coupling_gap_um))
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
]
