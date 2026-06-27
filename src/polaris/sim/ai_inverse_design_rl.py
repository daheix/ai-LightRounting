"""R29 路标：AI 驱动光子逆向设计 - RL 强化学习逆向设计器。

【创新】用 RL agent 替代梯度优化，适用于非可微目标函数（如制造约束、鲁棒性）。

## 学术依据

- Sutton & Barto, "Reinforcement Learning: An Introduction", 2nd ed., 2018,
  http://incompleteideas.net/book/the-book-2nd.html
- Schulman et al., "Proximal Policy Optimization Algorithms", 2017,
  https://arxiv.org/abs/1707.06347
- Williams, "Simple statistical gradient-following algorithms for connectionist
  reinforcement learning", Machine Learning 1992,
  https://doi.org/10.1162/neco.1992.4.2.127（REINFORCE 策略梯度）

来源:
- lumopt: https://github.com/chriskeraly/lumopt
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from polaris.sim.ai_inverse_design_physics import _transfer_matrix_transmission


@dataclass
class RLDesignConfig:
    """RL 逆向设计配置。

    学术依据：Sutton & Barto 2018 §13（RL 优化黑盒函数），
    http://incompleteideas.net/book/the-book-2nd.html

    【创新】AI 驱动逆向设计：用 RL agent 替代梯度优化，
    适用于非可微目标函数（如制造约束、鲁棒性）。
    """

    state_dim: int = 100
    action_dim: int = 100
    learning_rate: float = 3e-4
    n_episodes: int = 1000


class RLInverseDesigner:
    """RL 驱动逆向设计器。

    【创新】用 RL agent 探索设计空间，替代传统梯度优化。

    创新逻辑：
    - 传统 adjoint 需可微目标函数，RL 可处理非可微约束
    - RL agent 学习"设计模式"而非单点优化
    - 支持多目标优化（传输率 + 制造约束 + 鲁棒性）

    支持理论：
    - Sutton & Barto 2018 §13（RL 优化黑盒函数）
    - PPO 算法（Schulman 2017, https://arxiv.org/abs/1707.06347）

    实现：REINFORCE 策略梯度（Williams 1992, https://doi.org/10.1162/neco.1992.4.2.127），
    高斯策略，奖励 = 传输率 + 制造约束 + 鲁棒性。
    """

    def __init__(self, config: RLDesignConfig) -> None:
        """初始化 RL 逆向设计器。

        Args:
            config: RL 配置。
        """
        self.config = config
        self.rng = np.random.default_rng(0)
        # 高斯策略参数：均值（线性）+ 对数标准差
        self.policy_mu = np.zeros(config.action_dim)
        self.policy_log_std = np.log(0.3)
        self._best_design: np.ndarray | None = None
        self._best_reward = -float("inf")

    def define_state(self, design: np.ndarray) -> np.ndarray:
        """定义状态（设计参数 + 性能指标）。

        Args:
            design: 设计参数。

        Returns:
            状态向量（设计参数拼接传输率）。
        """
        design = np.asarray(design, dtype=np.float64)
        t = _transfer_matrix_transmission(design, 1.55)
        return np.concatenate([design, [t]])

    def define_action(self, state: np.ndarray) -> np.ndarray:
        """定义动作（参数调整，高斯策略采样）。

        Args:
            state: 当前状态。

        Returns:
            动作向量（参数增量）。
        """
        dim = self.config.action_dim
        std = np.exp(self.policy_log_std)
        action = self.policy_mu + std * self.rng.standard_normal(dim)
        return action

    def compute_reward(self, design: np.ndarray, target: dict) -> float:
        """计算奖励（传输率 + 制造约束 + 鲁棒性）。

        Args:
            design: 设计参数。
            target: 目标字典。

        Returns:
            奖励值（越大越好）。
        """
        design = np.asarray(design, dtype=np.float64)
        design = np.clip(design, 0.0, 1.0)
        wl = target.get("wavelength", 1.55)
        t = _transfer_matrix_transmission(design, wl)
        # 制造约束：奖励平滑设计（相邻像素差异小，可制造）
        smoothness = 1.0 - np.mean(np.abs(np.diff(design)))
        # 鲁棒性：对小幅扰动的稳定性
        perturbed = design + self.rng.normal(0, 0.02, design.shape)
        t_pert = _transfer_matrix_transmission(np.clip(perturbed, 0, 1), wl)
        robustness = 1.0 - abs(t - t_pert)
        return float(0.6 * t + 0.2 * smoothness + 0.2 * robustness)

    def train(self, target: dict) -> dict:
        """训练 RL agent（REINFORCE 策略梯度）。

        Args:
            target: 目标字典。

        Returns:
            训练结果字典（reward_history/best_design/best_reward/episodes）。
        """
        reward_history: list[float] = []
        lr = self.config.learning_rate
        for _ep in range(self.config.n_episodes):
            design = self.rng.uniform(0, 1, self.config.action_dim)
            action = self.define_action(self.define_state(design))
            new_design = np.clip(design + 0.1 * action, 0, 1)
            reward = self.compute_reward(new_design, target)
            reward_history.append(reward)
            if reward > self._best_reward:
                self._best_reward = reward
                self._best_design = new_design.copy()
            # REINFORCE 梯度上升：mu += lr * grad(log_prob) * reward
            # 对高斯策略 N(mu, sigma)，d log pi / d mu = (action - mu) / sigma^2
            std = np.exp(self.policy_log_std)
            grad_mu = (action - self.policy_mu) / (std**2)
            self.policy_mu += lr * grad_mu * reward
            # 退火探索
            self.policy_log_std = max(self.policy_log_std - 1e-4, np.log(0.05))
        return {
            "reward_history": reward_history,
            "best_design": self._best_design,
            "best_reward": self._best_reward,
            "episodes": self.config.n_episodes,
        }

    def generate_design(self, target: dict) -> np.ndarray:
        """生成设计（用最优策略均值 + 训练缓存）。

        Args:
            target: 目标字典。

        Returns:
            设计参数数组。
        """
        if self._best_design is not None:
            return self._best_design.copy()
        # 未训练时用策略均值生成
        design = np.clip(0.5 + 0.3 * self.policy_mu, 0, 1)
        return design


__all__ = [
    "RLDesignConfig",
    "RLInverseDesigner",
]
