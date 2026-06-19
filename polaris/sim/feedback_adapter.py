"""反馈适配器。

将仿真约束违规转化为布局布线调整建议，
指导下一轮布局布线优化。

来源:
- Apollo arXiv 2025: 布线感知布局反馈
  https://arxiv.org/html/2504.18813v1
- ICLR'26 专家RL: 领域知识注入
  https://openreview.net/forum?id=yqvNwfxRR6
"""

from __future__ import annotations

from dataclasses import dataclass, field

from polaris.sim.constraint_checker import Violation, ViolationType


@dataclass
class PlacementHint:
    """布局调整建议。

    Attributes:
        device_name: 目标器件名。
        dx: 建议X方向偏移（μm，正=右移）。
        dy: 建议Y方向偏移（μm，正=上移）。
        reason: 调整原因。
        priority: 优先级（0-1，1=最高）。
    """

    device_name: str = ""
    dx: float = 0.0
    dy: float = 0.0
    reason: str = ""
    priority: float = 0.5


@dataclass
class RoutingHint:
    """布线调整建议。

    Attributes:
        net_id: 目标网标识。
        avoid_region: 建议避开的区域 (x, y, w, h)。
        prefer_layer: 建议使用的层（可选）。
        reason: 调整原因。
    """

    net_id: str = ""
    avoid_region: tuple[float, float, float, float] | None = None
    prefer_layer: str = ""
    reason: str = ""


@dataclass
class FeedbackResult:
    """反馈结果。

    Attributes:
        placement_hints: 布局调整建议列表。
        routing_hints: 布线调整建议列表。
        should_retry: 是否需要重试布局布线。
        summary: 反馈摘要。
    """

    placement_hints: list[PlacementHint] = field(default_factory=list)
    routing_hints: list[RoutingHint] = field(default_factory=list)
    should_retry: bool = False
    summary: str = ""


class FeedbackAdapter:
    """反馈适配器。

    将约束违规转化为布局布线调整建议，
    指导下一轮布局布线优化。

    来源:
    - Apollo arXiv 2025: https://arxiv.org/html/2504.18813v1
    """

    def __init__(self) -> None:
        self._handlers: dict[ViolationType, tuple[str, str]] = {
            ViolationType.OVERLAP: ("placement", "_adapt_overlap"),
            ViolationType.SPACING: ("placement", "_adapt_spacing"),
            ViolationType.BEND_RADIUS: ("routing", "_adapt_bend"),
            ViolationType.INSERTION_LOSS: ("placement", "_adapt_loss"),
            ViolationType.CROSSING: ("placement", "_adapt_crossing"),
        }

    def adapt(self, violations: list[Violation]) -> FeedbackResult:
        """将违规转化为调整建议。

        Args:
            violations: 约束违规列表。

        Returns:
            FeedbackResult（含布局/布线调整建议）。
        """
        p_hints: list[PlacementHint] = []
        r_hints: list[RoutingHint] = []

        for v in violations:
            entry = self._handlers.get(v.vtype)
            if entry is None:
                continue
            kind, method_name = entry
            handler = getattr(self, method_name)
            hint = handler(v)
            if hint is not None:
                if kind == "placement":
                    p_hints.append(hint)
                else:
                    r_hints.append(hint)

        should_retry = len(violations) > 0
        summary = f"{len(violations)} 违规 → {len(p_hints)} 布局建议 + {len(r_hints)} 布线建议"

        return FeedbackResult(
            placement_hints=p_hints,
            routing_hints=r_hints,
            should_retry=should_retry,
            summary=summary,
        )

    @staticmethod
    def _adapt_overlap(v: Violation) -> PlacementHint | None:
        """重叠 → 拉开间距。"""
        if not v.device_name:
            return None
        parts = v.device_name.split("-")
        if len(parts) < 2:
            return None
        return PlacementHint(
            device_name=parts[1],
            dx=50.0,
            dy=50.0,
            reason=f"与 {parts[0]} 重叠",
            priority=1.0,
        )

    @staticmethod
    def _adapt_spacing(v: Violation) -> PlacementHint | None:
        """间距不足 → 增加间距。"""
        if not v.device_name:
            return None
        parts = v.device_name.split("-")
        if len(parts) < 2:
            return None
        offset = 20.0 * (1.0 + v.severity)
        return PlacementHint(
            device_name=parts[1],
            dx=offset,
            dy=0.0,
            reason=f"与 {parts[0]} 间距不足",
            priority=0.8,
        )

    @staticmethod
    def _adapt_bend(v: Violation) -> RoutingHint | None:
        """弯曲半径不足 → 避开该区域。"""
        region = None
        if v.location:
            region = (v.location[0] - 20, v.location[1] - 20, 40, 40)
        return RoutingHint(
            net_id=v.net_id,
            avoid_region=region,
            reason=f"弯曲半径不足: {v.message}",
        )

    @staticmethod
    def _adapt_loss(v: Violation) -> PlacementHint | None:
        """损耗超标 → 缩短路径。"""
        return PlacementHint(
            dx=-10.0,
            dy=-10.0,
            reason=f"损耗超标: {v.message}",
            priority=0.6,
        )

    @staticmethod
    def _adapt_crossing(v: Violation) -> PlacementHint | None:
        """交叉过多 → 调整布局减少交叉。"""
        return PlacementHint(
            dx=30.0,
            dy=0.0,
            reason="减少波导交叉",
            priority=0.7,
        )


__all__ = [
    "FeedbackAdapter",
    "FeedbackResult",
    "PlacementHint",
    "RoutingHint",
]
