"""V-trace off-policy 修正（第42轮 P1-4 深化，IMPALA）。

实现 V-trace 算法用于 off-policy 强化学习修正，对标 DeepMind IMPALA。

## 架构

- ``VTraceConfig``：V-trace 配置
- ``VTraceResult``：V-trace 计算结果
- ``TrajectoryBatch``：轨迹数据封装（第56轮重构，降低参数个数）
- ``compute_vtrace``：V-trace 主算法
- ``ImpalaLearner``：IMPALA 风格 learner

## 商业差距

P1-4 分布式训练深化：
- 商业标杆：DeepMind IMPALA V-trace off-policy 修正
- A3C 是 on-policy，IMPALA 通过 V-trace 支持 off-policy
- 允许行为策略与目标策略不同，提高样本效率

## 来源

- IMPALA: Espeholt et al., 2018,
  https://arxiv.org/abs/1802.01561
- V-trace: Munos et al., 2016,
  https://arxiv.org/abs/1602.01783
- Ray RLlib IMPALA:
  https://docs.ray.io/en/latest/rllib/algorithms/impala.html
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import numpy as np


@dataclass(frozen=True)
class VTraceConfig:
    """V-trace 配置。

    Attributes:
        rho_bar: 截断重要性采样系数上限（ρ̄）。
            来源: Espeholt 2018，典型值 1.0。
        c_bar: 截断重要性采样系数下限（c̄）。
            来源: Espeholt 2018，典型值 1.0。
        gamma: 折扣因子。
        lambda_: GAE lambda 参数（λ）。
    """

    rho_bar: float = 1.0
    c_bar: float = 1.0
    gamma: float = 0.99
    lambda_: float = 1.0


@dataclass
class VTraceResult:
    """V-trace 计算结果。

    Attributes:
        vs: V-trace 值估计（n_steps,）。
        pg_advantages: 策略梯度优势（n_steps,）。
        rhos: 重要性采样系数（n_steps,）。
        cs: 截断重要性采样系数（n_steps,）。
    """

    vs: np.ndarray = field(default_factory=lambda: np.array([]))
    pg_advantages: np.ndarray = field(default_factory=lambda: np.array([]))
    rhos: np.ndarray = field(default_factory=lambda: np.array([]))
    cs: np.ndarray = field(default_factory=lambda: np.array([]))


@dataclass
class TrajectoryBatch:
    """轨迹数据封装（第56轮重构）。

    将 V-trace 所需的 5 个等长轨迹数组合并为一个数据类，
    使函数签名从 7 参数降至 3 参数，符合质量门禁上限 5。

    Attributes:
        values: 状态值估计 V(s_t)（n_steps,）。
        rewards: 奖励 r_t（n_steps,）。
        logprobs_behavior: 行为策略 log π_μ(a|s)（n_steps,）。
        logprobs_target: 目标策略 log π_θ(a|s)（n_steps,）。
        dones: episode 结束标志（n_steps,）。
    """

    values: np.ndarray
    rewards: np.ndarray
    logprobs_behavior: np.ndarray
    logprobs_target: np.ndarray
    dones: np.ndarray

    def __post_init__(self) -> None:
        """校验轨迹长度一致。"""
        n = len(self.values)
        if not (
            len(self.rewards) == n
            and len(self.logprobs_behavior) == n
            and len(self.logprobs_target) == n
            and len(self.dones) == n
        ):
            raise ValueError("轨迹数组长度不一致")


def _compute_truncated_ratios(
    batch: TrajectoryBatch, cfg: VTraceConfig
) -> tuple[np.ndarray, np.ndarray]:
    """计算截断重要性采样系数 ρ̄_t 和 c̄_t。

    ρ_t = exp(log π_θ - log π_μ)
    ρ̄_t = min(ρ_t, ρ̄)
    c̄_t = min(ρ_t, c̄)
    """
    log_ratio = batch.logprobs_target - batch.logprobs_behavior
    rhos = np.exp(log_ratio)
    cs = np.exp(log_ratio)
    rhos = np.minimum(rhos, cfg.rho_bar)
    cs = np.minimum(cs, cfg.c_bar)
    return rhos, cs


def _compute_vs_values(
    batch: TrajectoryBatch,
    rhos: np.ndarray,
    cs: np.ndarray,
    last_value: float,
    cfg: VTraceConfig,
) -> np.ndarray:
    """计算 V-trace 值估计 v_s（后向递推）。"""
    n = len(batch.values)
    vs = np.zeros(n)
    vs[-1] = batch.values[-1] + rhos[-1] * (
        batch.rewards[-1] + cfg.gamma * (1 - batch.dones[-1]) * last_value - batch.values[-1]
    )
    for t in range(n - 2, -1, -1):
        delta = rhos[t] * (
            batch.rewards[t]
            + cfg.gamma * (1 - batch.dones[t]) * batch.values[t + 1]
            - batch.values[t]
        )
        vs[t] = (
            batch.values[t]
            + delta
            + (cfg.gamma * cfg.lambda_ * cs[t] * (1 - batch.dones[t]))
            * (vs[t + 1] - batch.values[t + 1])
        )
    return vs


def _compute_pg_advantages(
    batch: TrajectoryBatch,
    rhos: np.ndarray,
    vs: np.ndarray,
    last_value: float,
    cfg: VTraceConfig,
) -> np.ndarray:
    """计算策略梯度优势 A_t = ρ̄_t (r_t + γ v_{t+1} - V(x_t))。"""
    n = len(batch.values)
    pg_advantages = np.zeros(n)
    for t in range(n):
        next_v = vs[t + 1] if t + 1 < n else last_value
        pg_advantages[t] = rhos[t] * (
            batch.rewards[t] + cfg.gamma * (1 - batch.dones[t]) * next_v - batch.values[t]
        )
    return pg_advantages


def compute_vtrace(
    batch: TrajectoryBatch,
    last_value: float = 0.0,
    config: VTraceConfig | None = None,
) -> VTraceResult:
    """计算 V-trace 值估计和策略梯度优势。

    V-trace 算法（Espeholt et al. 2018）：
    1. 计算重要性采样系数 ρ_t = π(a|s) / μ(a|s)
    2. 截断：ρ̄_t = min(ρ_t, ρ̄), c̄_t = min(ρ_t, c̄)
    3. 计算 V-trace 值：v_s = V(x_s) + Σ γ^(t-s) (Π c̄_i) δ_t V
       其中 δ_t V = ρ_̄t (r_t + γ V(x_{t+1}) - V(x_t))
    4. 策略梯度优势：A_t = ρ_̄t (r_t + γ v_{t+1} - V(x_t))

    Args:
        batch: 轨迹数据封装（values/rewards/logprobs/dones）。
        last_value: 最后一个状态的 bootstrap 值。
        config: V-trace 配置。

    Returns:
        V-trace 计算结果。
    """
    cfg = config or VTraceConfig()
    rhos, cs = _compute_truncated_ratios(batch, cfg)
    vs = _compute_vs_values(batch, rhos, cs, last_value, cfg)
    pg_advantages = _compute_pg_advantages(batch, rhos, vs, last_value, cfg)
    return VTraceResult(
        vs=vs,
        pg_advantages=pg_advantages,
        rhos=rhos,
        cs=cs,
    )


class ImpalaLearner:
    """IMPALA 风格 learner。

    使用 V-trace 进行 off-policy 修正，对标 DeepMind IMPALA。

    来源:
        Espeholt et al., 2018, https://arxiv.org/abs/1802.01561
    """

    def __init__(
        self,
        value_fn: Callable[[np.ndarray], float],
        config: VTraceConfig | None = None,
    ) -> None:
        """初始化 IMPALA learner。

        Args:
            value_fn: 状态值函数 V(s)。
            config: V-trace 配置。
        """
        self.value_fn = value_fn
        self.config = config or VTraceConfig()

    def compute_targets(
        self,
        observations: np.ndarray,
        rewards: np.ndarray,
        logprobs_behavior: np.ndarray,
        logprobs_target: np.ndarray,
        dones: np.ndarray,
        last_observation: np.ndarray | None = None,
    ) -> VTraceResult:
        """计算 V-trace 目标。

        Args:
            observations: 观测序列（n_steps, obs_dim）。
            rewards: 奖励序列（n_steps,）。
            logprobs_behavior: 行为策略 log 概率。
            logprobs_target: 目标策略 log 概率。
            dones: episode 结束标志。
            last_observation: 最后一个观测（用于 bootstrap）。

        Returns:
            V-trace 计算结果。
        """
        values = np.array([self.value_fn(obs) for obs in observations])
        last_value = self.value_fn(last_observation) if last_observation is not None else 0.0
        batch = TrajectoryBatch(
            values=values,
            rewards=rewards,
            logprobs_behavior=logprobs_behavior,
            logprobs_target=logprobs_target,
            dones=dones,
        )
        return compute_vtrace(batch, last_value, self.config)


def create_vtrace_config(
    rho_bar: float = 1.0,
    c_bar: float = 1.0,
    gamma: float = 0.99,
    lambda_: float = 1.0,
) -> VTraceConfig:
    """工厂函数：创建 V-trace 配置。"""
    return VTraceConfig(
        rho_bar=rho_bar,
        c_bar=c_bar,
        gamma=gamma,
        lambda_=lambda_,
    )


def create_impala_learner(
    value_fn: Callable[[np.ndarray], float],
    config: VTraceConfig | None = None,
) -> ImpalaLearner:
    """工厂函数：创建 IMPALA learner。"""
    return ImpalaLearner(value_fn, config)


def run_vtrace(
    batch: TrajectoryBatch,
    last_value: float = 0.0,
    config: VTraceConfig | None = None,
) -> VTraceResult:
    """工厂函数：运行 V-trace 计算。"""
    return compute_vtrace(batch, last_value, config)
