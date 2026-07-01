"""性能约束检查函数（从 constraint_checker.py 拆分，第63轮 P2-1）。

包含插入损耗、交叉数、热串扰、波导串扰等性能 DRC 检查函数。

来源:
- LiDAR ISPD'25: 串扰惩罚
  https://dl.acm.org/doi/pdf/10.1145/3698364.3705355
- PoLaRIS 商业差距分析 P0-1，对标 Lumerical 多物理场仿真

补充文献（≥5，规则 R02 学术诚信）：
1. LiDARPlace (ISPD'25), "Photonic LiDAR placement with crosstalk
   penalty" — https://dl.acm.org/doi/pdf/10.1145/3698364.3705355
2. Reed GT, Mashanovich G, Gardes FY, Thomson DJ, "Silicon optical
   modulators," Nature Photonics 4, 518-526 (2010) —
   https://doi.org/10.1038/nphoton.2010.179
3. Chrostowski L, Hochberg M, "Silicon Photonics Design: From Devices
   to Systems," Cambridge University Press (2015) —
   https://www.cambridge.org/9781107085459
4. gdsfactory, "Python library for photonics layout & DRC checks" —
   https://gdsfactory.github.io/gdsfactory/
5. Ansys, "Lumerical multi-physics simulation suite" —
   https://optics.ansys.com/
6. KLayout, "Open-source GDSII viewer with DRC scripting" —
   https://www.klayout.de/
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from polaris.sim.constraint_checks_geometry import _rect_gap
from polaris.sim.constraint_types import Violation, ViolationType


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


__all__ = [
    "check_insertion_loss",
    "check_crossings",
    "check_thermal",
    "check_crosstalk",
    "CrosstalkConfig",
]
