"""反馈适配器：约束违规 → 布局布线调整建议。

从 v4 ``polaris/sim/feedback_adapter.py`` 迁移（R13 不保留 v4 兼容）。
将仿真约束违规转化为布局布线调整建议，指导下一轮布局布线优化。

## 设计原则

- 本模块独立于 v4 ``polaris.sim.constraint_checker``，本地定义
  ``ViolationType`` / ``Violation`` 类型（字段与 v4 对齐，便于后续接入
  polaris-constraint 子模块）
- 失败即 raise（R03 禁止 fall-back）
- 纯 NumPy/dataclass 实现（R04 不参与 GPU）

来源（R02 学术诚信，≥5 文献 URL）:
1. Apollo arXiv 2025 布线感知布局反馈:
   https://arxiv.org/html/2504.18813v1
2. ICLR'26 专家 RL 领域知识注入:
   https://openreview.net/forum?id=yqvNwfxRR6
3. KLayout DRC 文档:
   https://www.klayout.org/doc-qt5/manual/drc_runsets.html
4. KLayout LVS 文档:
   https://www.klayout.org/doc-qt5/manual/lvs_compare.html
5. SiEPIC EBeam PDK:
   https://github.com/SiEPIC/SiEPIC_EBeam_PDK
6. LiDAR ISPD'25:
   https://dl.acm.org/doi/pdf/10.1145/3698364.3705355
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ViolationType(Enum):
    """违规类型枚举（与 polaris.sim.constraint_types.ViolationType 对齐）。

    覆盖 SiEPIC EBeam PDK 与商业 foundry runset 常见规则类别。
    来源: https://github.com/SiEPIC/SiEPIC_EBeam_PDK；
         https://www.klayout.org/doc-qt5/manual/drc_runsets.html
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
    ENCLOSURE = "enclosure"  # 包围规则违规
    NOTCH = "notch"  # 凹槽间距不足
    PORT_CONNECTIVITY = "port_connectivity"  # 端口未连接
    PIN_MATCH = "pin_match"  # 端口宽度/类型不匹配
    LAYER_DENSITY = "layer_density"  # 层密度违规


@dataclass
class Violation:
    """约束违规记录（与 polaris.sim.constraint_types.Violation 字段对齐）。

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
    """反馈适配器：将约束违规转化为布局布线调整建议。

    来源: Apollo arXiv 2025 https://arxiv.org/html/2504.18813v1

    覆盖 5 类核心违规的反馈策略:
    - OVERLAP: 重叠 → 拉开间距（dx=dy=50μm）
    - SPACING: 间距不足 → 增加间距（20·(1+severity) μm）
    - BEND_RADIUS: 弯曲半径不足 → 避开区域（40×40μm）
    - INSERTION_LOSS: 损耗超标 → 缩短路径（dx=dy=-10μm）
    - CROSSING: 交叉过多 → 调整布局减少交叉（dx=30μm）
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
        summary = (
            f"{len(violations)} 违规 → {len(p_hints)} 布局建议 + "
            f"{len(r_hints)} 布线建议"
        )

        return FeedbackResult(
            placement_hints=p_hints,
            routing_hints=r_hints,
            should_retry=should_retry,
            summary=summary,
        )

    @staticmethod
    def _adapt_overlap(v: Violation) -> PlacementHint:
        """重叠 → 拉开间距。

        Raises:
            ValueError: 违例数据无效（设备名为空或格式错误）。
        """
        if not v.device_name:
            raise ValueError(f"重叠违例设备名为空: {v}")
        parts = v.device_name.split("-")
        if len(parts) < 2:
            raise ValueError(
                f"重叠违例设备名格式错误（期望 'dev1-dev2'）: {v.device_name}"
            )
        return PlacementHint(
            device_name=parts[1],
            dx=50.0,
            dy=50.0,
            reason=f"与 {parts[0]} 重叠",
            priority=1.0,
        )

    @staticmethod
    def _adapt_spacing(v: Violation) -> PlacementHint:
        """间距不足 → 增加间距。

        Raises:
            ValueError: 违例数据无效（设备名为空或格式错误）。
        """
        if not v.device_name:
            raise ValueError(f"间距违例设备名为空: {v}")
        parts = v.device_name.split("-")
        if len(parts) < 2:
            raise ValueError(
                f"间距违例设备名格式错误（期望 'dev1-dev2'）: {v.device_name}"
            )
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
    "ViolationType",
    "Violation",
    "PlacementHint",
    "RoutingHint",
    "FeedbackResult",
    "FeedbackAdapter",
]
