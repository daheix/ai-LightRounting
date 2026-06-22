"""光子学专家知识注入 RL 奖励塑形（ICLR'26 方向）。

将光子学领域专家知识注入 RL 奖励函数，引导 agent
学习更符合光子学约束的布局布线策略。

方法参考：
- Expertise-Enhanced RL (ICLR'26): Expertise Can Be Helpful for
  Reinforcement Learning-based Macro Placement
  Gao et al., NJU/Huawei
  https://openreview.net/forum?id=yqvNwfxRR6
- Basso et al., NeurIPS 2025: routing-aware floorplanning
  https://mlforsystems.org/assets/papers/neurips2025/paper42.pdf
- LiDAR (ISPD'25): 弯曲半径约束 + 交叉惩罚
  https://dl.acm.org/doi/pdf/10.1145/3698364.3705355

核心思想：
1. 端口对齐偏好：连接的器件端口应尽量对齐（减少弯曲）
2. 弯曲半径惩罚：违反弯曲半径约束的放置给予负奖励
3. 交叉惩罚：波导交叉增加损耗，应尽量避免
4. 拥塞惩罚：高拥塞区域降低布线成功率
5. 热串扰惩罚：热敏感器件应远离热源
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import NamedTuple

import numpy as np


@dataclass
class ExpertRewardInput:
    """专家知识奖励计算输入。

    Attributes:
        device_positions: 器件位置 {device_id: (x, y)}。
        connections: 连接列表 [(dev1, port1, dev2, port2), ...]。
        congestion_map: 拥塞热力图（可选）。
        thermal_sources: 热源器件 ID 集合（可选）。
        thermal_sensitive: 热敏感器件 ID 集合（可选）。
    """

    device_positions: dict[str, tuple[float, float]]
    connections: list[tuple[str, str, str, str]]
    congestion_map: np.ndarray | None = None
    thermal_sources: set[str] | None = None
    thermal_sensitive: set[str] | None = None


@dataclass
class ExpertRewardConfig:
    """专家知识奖励配置。

    Attributes:
        port_alignment_weight: 端口对齐奖励权重。
        bend_violation_weight: 弯曲违规惩罚权重。
        crossing_weight: 交叉惩罚权重。
        congestion_weight: 拥塞惩罚权重。
        thermal_weight: 热串扰惩罚权重。
        min_bend_radius_um: 最小弯曲半径（μm）。
        min_spacing_um: 最小波导间距（μm）。
    """

    # 奖励权重来源: ICLR'26 Expertise-Enhanced RL (Gao et al., NJU/Huawei)
    # 端口对齐权重 0.3: 对齐对布线质量影响中等
    port_alignment_weight: float = 0.3
    # 弯曲违规权重 0.5: 弯曲半径违规导致制造失败，权重最高
    bend_violation_weight: float = 0.5
    # 交叉惩罚权重 0.2: 交叉增加 0.5-1dB 损耗
    crossing_weight: float = 0.2
    # 拥塞惩罚权重 0.2: 高拥塞降低布线成功率
    congestion_weight: float = 0.2
    # 热串扰惩罚权重 0.1: 热效应影响相对较小
    thermal_weight: float = 0.1
    # 最小弯曲半径 5.0μm: SiEPIC EBeam PDK 推荐 ≥5μm
    # 来源: SiEPIC_EBeam_PDK PCell, https://github.com/SiEPIC/SiEPIC_EBeam_PDK
    min_bend_radius_um: float = 5.0
    # 最小波导间距 1.0μm: SiEPIC EBeam 单模波导间距
    # 来源: SiEPIC EBeam Design Kit
    min_spacing_um: float = 1.0


@dataclass
class ExpertRewardResult:
    """专家知识奖励计算结果。

    Attributes:
        total_expert_reward: 总专家奖励。
        port_alignment_reward: 端口对齐奖励。
        bend_penalty: 弯曲违规惩罚。
        crossing_penalty: 交叉惩罚。
        congestion_penalty: 拥塞惩罚。
        thermal_penalty: 热串扰惩罚。
    """

    total_expert_reward: float = 0.0
    port_alignment_reward: float = 0.0
    bend_penalty: float = 0.0
    crossing_penalty: float = 0.0
    congestion_penalty: float = 0.0
    thermal_penalty: float = 0.0


def _port_alignment_score(
    device_positions: dict[str, tuple[float, float]],
    connections: list[tuple[str, str, str, str]],
) -> float:
    """计算端口对齐评分。

    连接的器件端口应尽量对齐（水平或垂直），减少弯曲次数。
    对齐度 = cos(连接方向角) 的绝对值，越接近 1 越好。

    来源: ICLR'26 专家知识 - 边缘偏好

    Args:
        device_positions: 器件位置 {device_id: (x, y)}。
        connections: 连接列表 [(dev1, port1, dev2, port2), ...]。

    Returns:
        端口对齐评分（0-1）。
    """
    if not connections:
        return 1.0
    alignment_sum = 0.0
    for dev1, _p1, dev2, _p2 in connections:
        if dev1 not in device_positions or dev2 not in device_positions:
            continue
        x1, y1 = device_positions[dev1]
        x2, y2 = device_positions[dev2]
        dx, dy = x2 - x1, y2 - y1
        dist = math.hypot(dx, dy)
        if dist < 1e-9:
            alignment_sum += 1.0
            continue
        # 对齐度 = max(|cos θ|, |sin θ|)，越接近1越对齐
        alignment = max(abs(dx / dist), abs(dy / dist))
        alignment_sum += alignment
    return alignment_sum / len(connections)


def _bend_violation_penalty(
    device_positions: dict[str, tuple[float, float]],
    connections: list[tuple[str, str, str, str]],
    min_bend_radius: float,
) -> float:
    """计算弯曲违规惩罚。

    如果两器件间路径的转弯半径小于 min_bend_radius，给予惩罚。
    简化估计：非对齐连接需要至少1个转弯，检查转弯弧长是否足够。

    来源: LiDAR ISPD'25 弯曲半径约束

    Args:
        device_positions: 器件位置。
        connections: 连接列表。
        min_bend_radius: 最小弯曲半径（μm）。

    Returns:
        弯曲违规惩罚（0-1，0=无违规）。
    """
    if not connections:
        return 0.0
    violations = 0
    for dev1, _, dev2, _ in connections:
        if dev1 not in device_positions or dev2 not in device_positions:
            continue
        x1, y1 = device_positions[dev1]
        x2, y2 = device_positions[dev2]
        dx, dy = abs(x2 - x1), abs(y2 - y1)
        # 非对齐连接需要转弯，检查较短边是否足够容纳弯曲
        if dx > 0 and dy > 0:
            min_side = min(dx, dy)
            # 弯曲弧长 ≈ π/2 * R
            required = math.pi / 2.0 * min_bend_radius
            if min_side < required:
                violations += 1
    return violations / max(1, len(connections))


def _crossing_penalty_estimate(
    device_positions: dict[str, tuple[float, float]],
    connections: list[tuple[str, str, str, str]],
) -> float:
    """估算交叉惩罚（基于连接线段相交检测）。

    使用器件中心点之间的直线段近似波导路径，
    检测交叉数并归一化为惩罚值。

    来源: LiDAR ISPD'25 交叉惩罚

    Args:
        device_positions: 器件位置。
        connections: 连接列表。

    Returns:
        交叉惩罚（0-1）。
    """
    if len(connections) < 2:
        return 0.0
    # 提取连接线段
    segments: list[tuple[tuple[float, float], tuple[float, float]]] = []
    for dev1, _, dev2, _ in connections:
        if dev1 in device_positions and dev2 in device_positions:
            segments.append((device_positions[dev1], device_positions[dev2]))
    # 检测交叉
    crossings = 0
    for i in range(len(segments)):
        for j in range(i + 1, len(segments)):
            if _lines_cross(segments[i], segments[j]):
                crossings += 1
    max_crossings = len(segments) * (len(segments) - 1) / 2
    return min(1.0, crossings / max(1, max_crossings))


def _lines_cross(
    seg1: tuple[tuple[float, float], tuple[float, float]],
    seg2: tuple[tuple[float, float], tuple[float, float]],
) -> bool:
    """检测两线段是否相交。"""
    (a1, a2), (b1, b2) = seg1, seg2
    d1 = _cross2d(b1, b2, a1)
    d2 = _cross2d(b1, b2, a2)
    d3 = _cross2d(a1, a2, b1)
    d4 = _cross2d(a1, a2, b2)
    return ((d1 > 0 and d2 < 0) or (d1 < 0 and d2 > 0)) and (
        (d3 > 0 and d4 < 0) or (d3 < 0 and d4 > 0)
    )


def _cross2d(
    o: tuple[float, float],
    a: tuple[float, float],
    b: tuple[float, float],
) -> float:
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def _thermal_penalty(
    device_positions: dict[str, tuple[float, float]],
    thermal_sources: set[str],
    thermal_sensitive: set[str],
    safe_distance_um: float = 100.0,
) -> float:
    """计算热串扰惩罚。

    热敏感器件（如微环谐振器）应远离热源（如热光移相器）。

    来源: 硅光热串扰研究，Xiao et al., Opt. Express 2020

    Args:
        device_positions: 器件位置。
        thermal_sources: 热源器件 ID 集合。
        thermal_sensitive: 热敏感器件 ID 集合。
        safe_distance_um: 安全距离（μm）。

    Returns:
        热串扰惩罚（0-1）。
    """
    if not thermal_sources or not thermal_sensitive:
        return 0.0
    violations = 0
    total_pairs = 0
    for src in thermal_sources:
        for sens in thermal_sensitive:
            if src not in device_positions or sens not in device_positions:
                continue
            total_pairs += 1
            dist = math.hypot(
                device_positions[src][0] - device_positions[sens][0],
                device_positions[src][1] - device_positions[sens][1],
            )
            if dist < safe_distance_um:
                violations += 1
    return violations / max(1, total_pairs)


class _PenaltyComponents(NamedTuple):
    """惩罚/奖励分量内部传递结构。"""

    port_reward: float
    bend_pen: float
    cross_pen: float
    cong_pen: float
    therm_pen: float


class ExpertRewardShaper:
    """光子学专家知识奖励塑形器（ICLR'26 方向）。

    将光子学领域知识注入 RL 奖励函数，引导 agent
    学习更符合光子学约束的布局策略。

    来源:
    - ICLR'26: https://openreview.net/forum?id=yqvNwfxRR6
    """

    def __init__(self, config: ExpertRewardConfig | None = None) -> None:
        self.config = config or ExpertRewardConfig()

    def compute(self, reward_input: ExpertRewardInput) -> ExpertRewardResult:
        """计算专家知识奖励。

        Args:
            reward_input: 专家知识奖励计算输入。

        Returns:
            ExpertRewardResult。
        """
        cfg = self.config
        penalties = self._compute_penalties(reward_input, cfg)

        # 加权求和
        total = (
            cfg.port_alignment_weight * penalties.port_reward
            - cfg.bend_violation_weight * penalties.bend_pen
            - cfg.crossing_weight * penalties.cross_pen
            - cfg.congestion_weight * penalties.cong_pen
            - cfg.thermal_weight * penalties.therm_pen
        )

        return ExpertRewardResult(
            total_expert_reward=total,
            port_alignment_reward=penalties.port_reward,
            bend_penalty=penalties.bend_pen,
            crossing_penalty=penalties.cross_pen,
            congestion_penalty=penalties.cong_pen,
            thermal_penalty=penalties.therm_pen,
        )

    @staticmethod
    def _compute_penalties(
        reward_input: ExpertRewardInput,
        cfg: ExpertRewardConfig,
    ) -> _PenaltyComponents:
        """计算各项惩罚/奖励分量。

        Args:
            reward_input: 专家知识奖励计算输入。
            cfg: 专家知识奖励配置。

        Returns:
            _PenaltyComponents 各项分量。
        """
        port_reward = _port_alignment_score(reward_input.device_positions, reward_input.connections)
        bend_pen = _bend_violation_penalty(
            reward_input.device_positions,
            reward_input.connections,
            cfg.min_bend_radius_um,
        )
        cross_pen = _crossing_penalty_estimate(
            reward_input.device_positions, reward_input.connections
        )
        cong_pen = 0.0
        if reward_input.congestion_map is not None:
            cong_pen = float(np.mean(reward_input.congestion_map))
        therm_pen = _thermal_penalty(
            reward_input.device_positions,
            reward_input.thermal_sources or set(),
            reward_input.thermal_sensitive or set(),
        )
        return _PenaltyComponents(port_reward, bend_pen, cross_pen, cong_pen, therm_pen)


__all__ = [
    "ExpertRewardShaper",
    "ExpertRewardConfig",
    "ExpertRewardInput",
    "ExpertRewardResult",
]
