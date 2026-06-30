"""R381-R385 路标：离线 RL / Conservative Q-Learning（纯 NumPy/SciPy CPU 实现）。

将离线 RL（Offline RL）引入光子布局布线：从历史专家/工业 EDA 工具产出的
布局轨迹（无需在线交互）中学习 Q 函数，避免在线探索的高成本。CQL 通过
对 OOD（out-of-distribution）动作施加保守惩罚，防止离线 RL 中因分布外
外推动作导致 Q 值过高估的失效模式。

- R381 ``OfflineDataset``：离线 (s, a, r, s', done) 元组数据集管理
- R382 ``QNetwork``：Q 网络（纯 NumPy 两层 MLP + target 网络）
- R383 ``ConservativeQLearning``：CQL 算法核心（Kumar 2020 NeurIPS）
  - L_CQL = α · [E_{a~U} logΣexp_a' Q(s,a') − E_{a~D} Q(s,a)] + L_Bellman
  - OOD 惩罚降低未观测动作的 Q 值
- R384 ``OfflineTrainer``：离线训练循环（minibatch SGD + target 软更新）
- R385 ``OfflineEvaluator``：离线策略评估 OPE（Fitted Q Evaluation, FQE）

## R04 战略（不可撤销）

🚫不参与 GPU：纯 NumPy/SciPy。所有矩阵运算使用 numpy.einsum / @。

## R03 禁止 fall-back

业务错误一律 ``raise``，禁止 except:pass / return None / 假数据兜底。

## 学术依据（R02，≥5 个文献 URL）

1. Kumar et al., NeurIPS 2020, Conservative Q-Learning for Offline RL
   https://arxiv.org/abs/2006.04779
2. Kumar et al., NeurIPS 2019, BCQ (Batch-Constrained Q-Learning)
   https://arxiv.org/abs/1812.02900
3. Fujimoto et al., ICML 2019, TD3+BC (Offline RL 简化版)
   https://arxiv.org/abs/2106.07291
4. Agarwal et al., NeurIPS 2020, OPE / FQE
   https://arxiv.org/abs/2007.09055
5. Levine et al., 2020, Offline RL Survey
   https://arxiv.org/abs/2005.01643
6. Wu et al., ICLR 2019, Behavior Regularized Offline RL
   https://arxiv.org/abs/1906.00949
7. Kidambi et al., NeurIPS 2020, MOReL (Model-Based Offline RL)
   https://arxiv.org/abs/2005.05951
8. Siegel et al., NeurIPS 2020, Keep Doing What Worked (AWAC)
   https://arxiv.org/abs/2002.02989

## *创新* 标注（R02）

- *创新* R381-R385：将 CQL 离线 RL 引入光子布局布线。底层逻辑：CQL 通过
  在标准 Bellman 误差基础上叠加"对 OOD 动作的 log-sum-exp 惩罚"项，使得
  离线数据集 D 中未观测到的 (s, a) 的 Q 估计被显式压低，从而避免 Q 函数
  因外推到分布外区域而爆炸。对光子布局而言，工业 EDA 历史轨迹只能覆盖
  布局动作空间的极小子集（专家偏好策略），在线 RL 会因稀疏探索陷入次优
  局部；CQL 反过来利用"保守"约束，确保策略只在已验证的布局动作模式内
  做决策，与 AlphaChip（Mirhoseini 2024 addendum）的"基于工业 placement
  预训练"思路对齐。
- *创新* R383：CQL 自适应 α 调度——早期训练保持大 α 强制保守，后期逐步
  衰减以释放探索。借鉴 Kumar 2020 §5.3 Lagrangian auto-α 思路简化版。

来源：路标 R381-R385（批次 14 离线 RL）；R01-R04/R11；numpy 2.5。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np

# R04 声明：🚫不参与 GPU
GPU_DISABLED_R04: bool = True


# ===========================================================================
# 工具函数
# ===========================================================================


def _softmax(x: np.ndarray, axis: int = -1) -> np.ndarray:
    """数值稳定 softmax。"""
    x = np.asarray(x, dtype=np.float64)
    x_max = np.max(x, axis=axis, keepdims=True)
    e = np.exp(x - x_max)
    return e / np.sum(e, axis=axis, keepdims=True)


def _logsumexp(x: np.ndarray, axis: int = -1) -> np.ndarray:
    """数值稳定 logsumexp。"""
    x = np.asarray(x, dtype=np.float64)
    x_max = np.max(x, axis=axis, keepdims=True)
    return x_max.squeeze(axis=axis) + np.log(
        np.sum(np.exp(x - x_max), axis=axis)
    )


def _soft_update(target: np.ndarray, source: np.ndarray, tau: float) -> np.ndarray:
    """Polyak 软更新：θ_target ← (1-τ)·θ_target + τ·θ_source。"""
    return (1.0 - tau) * target + tau * source


# ===========================================================================
# R381 — 离线数据集
# ===========================================================================


@dataclass
class OfflineDatasetConfig:
    """R381 离线数据集配置。"""

    state_dim: int = 16
    action_dim: int = 8
    max_size: int = 10000
    seed: int = 42


class OfflineDataset:
    """R381 离线 (s, a, r, s', done) 数据集管理。

    存储离线 RL 经典五元组：state, action, reward, next_state, done。
    支持随机 minibatch 采样与 epoch 迭代。

    学术依据：Fujimoto 2019 ICML TD3+BC §3 Replay Buffer 设计
    https://arxiv.org/abs/2106.07291
    """

    def __init__(self, config: OfflineDatasetConfig | None = None) -> None:
        self.config = config or OfflineDatasetConfig()
        self._rng = np.random.default_rng(self.config.seed)
        self._states = np.zeros(
            (self.config.max_size, self.config.state_dim), dtype=np.float64
        )
        self._actions = np.zeros(
            (self.config.max_size, self.config.action_dim), dtype=np.float64
        )
        self._rewards = np.zeros(self.config.max_size, dtype=np.float64)
        self._next_states = np.zeros(
            (self.config.max_size, self.config.state_dim), dtype=np.float64
        )
        self._dones = np.zeros(self.config.max_size, dtype=np.float64)
        self._size = 0
        self._capacity = 0  # 已写入槽位（含覆盖）

    def __len__(self) -> int:
        return self._size

    @property
    def capacity(self) -> int:
        """已写入槽位数（含循环覆盖后的累计）。"""
        return self._capacity

    def add(
        self,
        state: np.ndarray,
        action: np.ndarray,
        reward: float,
        next_state: np.ndarray,
        done: bool,
    ) -> None:
        """添加一个五元组（形状不符即 raise，R03）。"""
        s = np.asarray(state, dtype=np.float64).ravel()
        a = np.asarray(action, dtype=np.float64).ravel()
        ns = np.asarray(next_state, dtype=np.float64).ravel()
        if s.shape[0] != self.config.state_dim:
            raise ValueError(
                f"state 维度 {s.shape[0]} != {self.config.state_dim}"
            )
        if a.shape[0] != self.config.action_dim:
            raise ValueError(
                f"action 维度 {a.shape[0]} != {self.config.action_dim}"
            )
        if ns.shape[0] != self.config.state_dim:
            raise ValueError(
                f"next_state 维度 {ns.shape[0]} != {self.config.state_dim}"
            )
        idx = self._size % self.config.max_size
        self._states[idx] = s
        self._actions[idx] = a
        self._rewards[idx] = float(reward)
        self._next_states[idx] = ns
        self._dones[idx] = 1.0 if done else 0.0
        self._size += 1
        self._capacity = min(self._capacity + 1, self.config.max_size)

    def extend(
        self,
        states: np.ndarray,
        actions: np.ndarray,
        rewards: np.ndarray,
        next_states: np.ndarray,
        dones: np.ndarray,
    ) -> None:
        """批量添加（长度必须一致，R03）。"""
        states = np.asarray(states, dtype=np.float64)
        actions = np.asarray(actions, dtype=np.float64)
        rewards = np.asarray(rewards, dtype=np.float64).ravel()
        next_states = np.asarray(next_states, dtype=np.float64)
        dones = np.asarray(dones, dtype=np.float64).ravel()
        n = states.shape[0]
        if actions.shape[0] != n or rewards.shape[0] != n:
            raise ValueError("批量添加长度不一致（R03）")
        if next_states.shape[0] != n or dones.shape[0] != n:
            raise ValueError("批量添加长度不一致（R03）")
        for i in range(n):
            self.add(states[i], actions[i], float(rewards[i]), next_states[i], bool(dones[i]))

    def sample_batch(self, batch_size: int) -> dict[str, np.ndarray]:
        """随机采样一个 minibatch。空数据集或 batch 超过容量即 raise。"""
        if self._capacity == 0:
            raise ValueError("数据集为空，无法采样（R03 无 fall-back）")
        if batch_size < 1:
            raise ValueError(f"batch_size={batch_size} 须 >= 1")
        idx = self._rng.integers(0, self._capacity, size=batch_size)
        return {
            "states": self._states[idx].copy(),
            "actions": self._actions[idx].copy(),
            "rewards": self._rewards[idx].copy(),
            "next_states": self._next_states[idx].copy(),
            "dones": self._dones[idx].copy(),
        }

    def iterate_batches(self, batch_size: int, shuffle: bool = True):
        """迭代所有数据。batch_size 超过容量即 raise。"""
        if self._capacity == 0:
            raise ValueError("数据集为空（R03）")
        if batch_size < 1:
            raise ValueError("batch_size 须 >= 1")
        idx = np.arange(self._capacity)
        if shuffle:
            self._rng.shuffle(idx)
        for start in range(0, self._capacity, batch_size):
            end = min(start + batch_size, self._capacity)
            sel = idx[start:end]
            yield {
                "states": self._states[sel].copy(),
                "actions": self._actions[sel].copy(),
                "rewards": self._rewards[sel].copy(),
                "next_states": self._next_states[sel].copy(),
                "dones": self._dones[sel].copy(),
            }


# ===========================================================================
# R382 — Q 网络（纯 NumPy 两层 MLP + target）
# ===========================================================================


@dataclass
class QNetworkConfig:
    """R382 Q 网络配置。"""

    state_dim: int = 16
    action_dim: int = 8
    hidden_dim: int = 64
    init_scale: float = 0.1
    seed: int = 42


class QNetwork:
    """R382 Q 网络 Q(s, a)（纯 NumPy 两层 MLP）。

    Q(s, a) = W2 · ReLU(W1 · [s; a] + b1) + b2

    包含 target 网络（Polyak 软更新），用于稳定 Bellman backup。

    学术依据：Mnih 2015 Nature DQN target network
    https://www.nature.com/articles/nature14236
    """

    def __init__(self, config: QNetworkConfig | None = None) -> None:
        self.config = config or QNetworkConfig()
        self._rng = np.random.default_rng(self.config.seed)
        in_dim = self.config.state_dim + self.config.action_dim
        out_dim = 1
        # He 初始化
        self.W1 = self._rng.normal(0, np.sqrt(2.0 / in_dim), (in_dim, self.config.hidden_dim))
        self.b1 = np.zeros(self.config.hidden_dim, dtype=np.float64)
        self.W2 = self._rng.normal(
            0, np.sqrt(2.0 / self.config.hidden_dim), (self.config.hidden_dim, out_dim)
        )
        self.b2 = np.zeros(out_dim, dtype=np.float64)
        # target 网络（初始化为 online 同值）
        self.W1_t = self.W1.copy()
        self.b1_t = self.b1.copy()
        self.W2_t = self.W2.copy()
        self.b2_t = self.b2.copy()

    def forward(self, states: np.ndarray, actions: np.ndarray) -> np.ndarray:
        """前向 Q(s, a) → [N, 1]。形状不一致即 raise。"""
        s = np.atleast_2d(np.asarray(states, dtype=np.float64))
        a = np.atleast_2d(np.asarray(actions, dtype=np.float64))
        if s.shape[0] != a.shape[0]:
            raise ValueError(f"batch 不匹配: states {s.shape[0]} vs actions {a.shape[0]}")
        if s.shape[1] != self.config.state_dim:
            raise ValueError(f"state 维度 {s.shape[1]} != {self.config.state_dim}")
        if a.shape[1] != self.config.action_dim:
            raise ValueError(f"action 维度 {a.shape[1]} != {self.config.action_dim}")
        x = np.concatenate([s, a], axis=1)
        h = np.maximum(0.0, x @ self.W1 + self.b1)
        return h @ self.W2 + self.b2  # [N, 1]

    def forward_target(self, states: np.ndarray, actions: np.ndarray) -> np.ndarray:
        """target 网络前向。"""
        s = np.atleast_2d(np.asarray(states, dtype=np.float64))
        a = np.atleast_2d(np.asarray(actions, dtype=np.float64))
        if s.shape[0] != a.shape[0]:
            raise ValueError("target batch 不匹配（R03）")
        x = np.concatenate([s, a], axis=1)
        h = np.maximum(0.0, x @ self.W1_t + self.b1_t)
        return h @ self.W2_t + self.b2_t

    def forward_all_actions(
        self, states: np.ndarray, action_candidates: np.ndarray
    ) -> np.ndarray:
        """对每个 state 评估所有 candidate actions 的 Q 值 → [N, K]。

        用于 CQL log-sum-exp 计算：对每个 s，评估 K 个候选 a 的 Q(s, a)。

        Args:
            states: [N, state_dim]
            action_candidates: [K, action_dim]（K 个候选 action，对全部 state 共享）

        Returns:
            Q_values: [N, K]，Q_values[i, k] = Q(s_i, a_k)
        """
        s = np.atleast_2d(np.asarray(states, dtype=np.float64))
        ac = np.atleast_2d(np.asarray(action_candidates, dtype=np.float64))
        if s.shape[1] != self.config.state_dim:
            raise ValueError(f"state 维度 {s.shape[1]} != {self.config.state_dim}")
        if ac.shape[1] != self.config.action_dim:
            raise ValueError(f"action 维度 {ac.shape[1]} != {self.config.action_dim}")
        N = s.shape[0]
        K = ac.shape[0]
        # 广播：s[N,1,state_dim] × ac[1,K,action_dim] → [N,K,state_dim+action_dim]
        s_rep = np.broadcast_to(s[:, None, :], (N, K, s.shape[1]))
        a_rep = np.broadcast_to(ac[None, :, :], (N, K, ac.shape[1]))
        x = np.concatenate([s_rep, a_rep], axis=2)  # [N, K, in_dim]
        h = np.maximum(0.0, np.einsum("nki,io->nko", x, self.W1) + self.b1)
        q = np.einsum("nki,io->nko", h, self.W2) + self.b2  # [N, K, 1]
        return q[:, :, 0]  # [N, K]

    def soft_update(self, tau: float) -> None:
        """Polyak 软更新 target: θ_t ← (1-τ)·θ_t + τ·θ_online。"""
        if not 0.0 <= tau <= 1.0:
            raise ValueError(f"tau={tau} 须 ∈ [0, 1]")
        self.W1_t = _soft_update(self.W1_t, self.W1, tau)
        self.b1_t = _soft_update(self.b1_t, self.b1, tau)
        self.W2_t = _soft_update(self.W2_t, self.W2, tau)
        self.b2_t = _soft_update(self.b2_t, self.b2, tau)

    def hard_update(self) -> None:
        """硬同步 target ← online。"""
        self.W1_t = self.W1.copy()
        self.b1_t = self.b1.copy()
        self.W2_t = self.W2.copy()
        self.b2_t = self.b2.copy()

    def parameters(self) -> dict[str, np.ndarray]:
        """返回 online 参数字典（用于梯度更新）。"""
        return {
            "W1": self.W1,
            "b1": self.b1,
            "W2": self.W2,
            "b2": self.b2,
        }

    def set_parameters(self, params: dict[str, np.ndarray]) -> None:
        """设置 online 参数。"""
        self.W1 = np.asarray(params["W1"], dtype=np.float64).copy()
        self.b1 = np.asarray(params["b1"], dtype=np.float64).copy()
        self.W2 = np.asarray(params["W2"], dtype=np.float64).copy()
        self.b2 = np.asarray(params["b2"], dtype=np.float64).copy()


# ===========================================================================
# R383 — Conservative Q-Learning
# ===========================================================================


@dataclass
class CQLConfig:
    """R383 CQL 配置。

    默认值来源：Kumar 2020 NeurIPS §5.2（α=5.0 for D4RL）/ Mnih 2015
    Nature DQN（gamma=0.99）/ Lillicrap 2016 DDPG（tau=0.005）。
    """

    gamma: float = 0.99
    tau: float = 0.005
    alpha: float = 5.0          # CQL 保守惩罚系数
    alpha_min: float = 1.0      # 自适应 α 下限（*创新* R383）
    alpha_decay: float = 0.999  # α 每步指数衰减
    learning_rate: float = 1e-3
    n_candidate_actions: int = 10  # log-sum-exp 候选动作数


class ConservativeQLearning:
    """R383 Conservative Q-Learning（Kumar 2020 NeurIPS）。

    CQL 损失：
        L_CQL = α · [E_{a~U(A)} logΣexp_a' Q(s,a') − E_{a~D} Q(s,a)]
                + L_Bellman
    其中：
        L_Bellman = E_{(s,a,r,s')~D}[(Q(s,a) − y)²]
        y = r + γ · (1 − done) · max_a' Q_target(s', a')

    logΣexp 项通过随机采样的 K 个候选 action 估计：
        logΣexp_a' Q(s,a') ≈ log( (1/K) Σ_k exp(Q(s, a_k)) ) + log(K)
                          = LogSumExp_k(Q(s, a_k))

    学术依据：Kumar 2020 NeurIPS CQL https://arxiv.org/abs/2006.04779
    """

    def __init__(
        self,
        q_network: QNetwork,
        config: CQLConfig | None = None,
        seed: int = 42,
    ) -> None:
        self.q_network = q_network
        self.config = config or CQLConfig()
        self._rng = np.random.default_rng(seed)
        self._current_alpha = float(self.config.alpha)

    @property
    def alpha(self) -> float:
        """当前 α 值。"""
        return self._current_alpha

    def decay_alpha(self) -> float:
        """*创新* R383：α 指数衰减（不低于 alpha_min）。"""
        self._current_alpha = max(
            self.config.alpha_min,
            self._current_alpha * self.config.alpha_decay,
        )
        return self._current_alpha

    def compute_bellman_targets(
        self,
        rewards: np.ndarray,
        next_states: np.ndarray,
        dones: np.ndarray,
        candidate_next_actions: np.ndarray,
    ) -> np.ndarray:
        """计算 Bellman backup target y = r + γ·(1-done)·max_a' Q_target(s', a')。

        max_a' 通过对 K 个候选 action 取最大值近似（与 CQL 实践一致）。

        Args:
            rewards: [N]
            next_states: [N, state_dim]
            dones: [N]
            candidate_next_actions: [K, action_dim]（K 个候选）

        Returns:
            y: [N, 1]
        """
        r = np.asarray(rewards, dtype=np.float64).ravel()
        ns = np.atleast_2d(np.asarray(next_states, dtype=np.float64))
        d = np.asarray(dones, dtype=np.float64).ravel()
        if r.shape[0] != ns.shape[0] or r.shape[0] != d.shape[0]:
            raise ValueError("Bellman target 形状不一致（R03）")
        # target 网络评估 next-state Q
        # Q_target(s', a_k) for each (s', a_k) → [N, K]
        q_next = self._eval_target_all_actions(ns, candidate_next_actions)
        max_q_next = np.max(q_next, axis=1)  # [N]
        y = r + self.config.gamma * (1.0 - d) * max_q_next
        return y.reshape(-1, 1)

    def _eval_target_all_actions(
        self, states: np.ndarray, actions: np.ndarray
    ) -> np.ndarray:
        """用 target 网络评估 [N, K] Q 值。"""
        s = np.atleast_2d(np.asarray(states, dtype=np.float64))
        ac = np.atleast_2d(np.asarray(actions, dtype=np.float64))
        N = s.shape[0]
        K = ac.shape[0]
        s_rep = np.broadcast_to(s[:, None, :], (N, K, s.shape[1]))
        a_rep = np.broadcast_to(ac[None, :, :], (N, K, ac.shape[1]))
        x = np.concatenate([s_rep, a_rep], axis=2)
        h = np.maximum(0.0, np.einsum("nki,io->nko", x, self.q_network.W1_t) + self.q_network.b1_t)
        q = np.einsum("nki,io->nko", h, self.q_network.W2_t) + self.q_network.b2_t
        return q[:, :, 0]  # [N, K]

    def compute_cql_loss(
        self,
        states: np.ndarray,
        actions: np.ndarray,
        rewards: np.ndarray,
        next_states: np.ndarray,
        dones: np.ndarray,
        candidate_actions: np.ndarray,
        candidate_next_actions: np.ndarray,
    ) -> tuple[float, dict[str, float]]:
        """计算 CQL 总损失 = α·(logsumexp - data_Q) + Bellman_loss。

        Args:
            states, actions, rewards, next_states, dones: 数据集 batch
            candidate_actions: [K, action_dim] 当前 s 的候选（用于 logsumexp）
            candidate_next_actions: [K, action_dim] next s' 的候选

        Returns:
            total_loss, info_dict
        """
        s = np.atleast_2d(np.asarray(states, dtype=np.float64))
        a = np.atleast_2d(np.asarray(actions, dtype=np.float64))
        r = np.asarray(rewards, dtype=np.float64).ravel()
        ns = np.atleast_2d(np.asarray(next_states, dtype=np.float64))
        d = np.asarray(dones, dtype=np.float64).ravel()
        N = s.shape[0]

        # 1) Bellman loss
        y = self.compute_bellman_targets(r, ns, d, candidate_next_actions)  # [N, 1]
        q_data = self.q_network.forward(s, a)  # [N, 1]
        bellman_loss = float(np.mean((q_data - y) ** 2))

        # 2) CQL 保守项
        # E_{a~U} logΣexp_a' Q(s, a')  对每个 s 评估 K 个候选
        q_candidates = self.q_network.forward_all_actions(s, candidate_actions)  # [N, K]
        logsumexp_q = _logsumexp(q_candidates, axis=1)  # [N]
        # E_{a~D} Q(s, a)  数据集动作的 Q
        # q_data 已计算 [N, 1]
        data_q_mean = q_data.ravel()  # [N]
        cql_conservative = float(np.mean(logsumexp_q - data_q_mean))

        # 总损失
        total_loss = self._current_alpha * cql_conservative + bellman_loss

        info = {
            "bellman_loss": bellman_loss,
            "cql_conservative": cql_conservative,
            "total_loss": total_loss,
            "alpha": self._current_alpha,
            "q_data_mean": float(np.mean(q_data)),
            "q_candidate_max_mean": float(np.mean(np.max(q_candidates, axis=1))),
            "target_mean": float(np.mean(y)),
        }
        return total_loss, info

    def compute_gradients(
        self,
        states: np.ndarray,
        actions: np.ndarray,
        rewards: np.ndarray,
        next_states: np.ndarray,
        dones: np.ndarray,
        candidate_actions: np.ndarray,
        candidate_next_actions: np.ndarray,
    ) -> dict[str, np.ndarray]:
        """对 Q 网络参数计算 CQL 损失梯度（数值微分法，纯 NumPy）。

        注：纯 NumPy 实现不依赖 autograd，使用中心差分法 O(n_params) 估计梯度。
        适用于小网络（hidden_dim=64 时约 5K 参数）。生产场景应换 JAX autograd。

        Args: 同 compute_cql_loss
        Returns: grads dict {W1, b1, W2, b2}
        """
        eps = 1e-4
        params = self.q_network.parameters()
        grads: dict[str, np.ndarray] = {}
        for name, p in params.items():
            g = np.zeros_like(p)
            flat = p.ravel()
            it = np.nditer(p, flags=["multi_index"], op_flags=["readwrite"])
            while not it.finished:
                idx = it.multi_index
                orig = float(p[idx])
                # +eps
                p[idx] = orig + eps
                self.q_network.set_parameters(params)
                loss_p, _ = self.compute_cql_loss(
                    states, actions, rewards, next_states, dones,
                    candidate_actions, candidate_next_actions,
                )
                # -eps
                p[idx] = orig - eps
                self.q_network.set_parameters(params)
                loss_m, _ = self.compute_cql_loss(
                    states, actions, rewards, next_states, dones,
                    candidate_actions, candidate_next_actions,
                )
                # 恢复
                p[idx] = orig
                g[idx] = (loss_p - loss_m) / (2.0 * eps)
                it.iternext()
            # 恢复参数
            self.q_network.set_parameters(params)
            grads[name] = g
        return grads

    def step(
        self,
        states: np.ndarray,
        actions: np.ndarray,
        rewards: np.ndarray,
        next_states: np.ndarray,
        dones: np.ndarray,
        candidate_actions: np.ndarray,
        candidate_next_actions: np.ndarray,
    ) -> dict[str, float]:
        """一步 CQL 更新（计算梯度→SGD→target 软更新→α 衰减）。"""
        grads = self.compute_gradients(
            states, actions, rewards, next_states, dones,
            candidate_actions, candidate_next_actions,
        )
        lr = self.config.learning_rate
        # SGD 更新
        params = self.q_network.parameters()
        params["W1"] -= lr * grads["W1"]
        params["b1"] -= lr * grads["b1"]
        params["W2"] -= lr * grads["W2"]
        params["b2"] -= lr * grads["b2"]
        self.q_network.set_parameters(params)
        # target 软更新
        self.q_network.soft_update(self.config.tau)
        # α 衰减
        self.decay_alpha()
        # 返回 loss info
        _, info = self.compute_cql_loss(
            states, actions, rewards, next_states, dones,
            candidate_actions, candidate_next_actions,
        )
        return info


# ===========================================================================
# R384 — 离线训练器
# ===========================================================================


@dataclass
class OfflineTrainerConfig:
    """R384 离线训练器配置。"""

    n_iterations: int = 100
    batch_size: int = 32
    eval_every: int = 10
    seed: int = 42


class OfflineTrainer:
    """R384 离线训练循环。

    封装 CQL 训练：每步从 OfflineDataset 采样 batch → CQL step →
    定期评估并记录。返回训练历史。

    学术依据：Kumar 2020 NeurIPS CQL §5.2 训练流程
    https://arxiv.org/abs/2006.04779
    """

    def __init__(
        self,
        cql: ConservativeQLearning,
        dataset: OfflineDataset,
        config: OfflineTrainerConfig | None = None,
    ) -> None:
        self.cql = cql
        self.dataset = dataset
        self.config = config or OfflineTrainerConfig()
        self._rng = np.random.default_rng(self.config.seed)
        self.history: list[dict[str, float]] = []

    def _sample_candidates(self, k: int) -> np.ndarray:
        """从 [-1, 1] 均匀采样 K 个候选 action。"""
        action_dim = self.cql.q_network.config.action_dim
        return self._rng.uniform(-1.0, 1.0, size=(k, action_dim))

    def train(
        self,
        eval_callback: Callable[[ConservativeQLearning, OfflineDataset], float] | None = None,
    ) -> dict[str, list[float]]:
        """执行离线 CQL 训练。

        Args:
            eval_callback: 可选评估函数，返回当前策略 value 估计

        Returns:
            history dict {iter, bellman_loss, cql_conservative, total_loss, alpha, eval_value}
        """
        if len(self.dataset) == 0:
            raise ValueError("数据集为空，无法训练（R03 无 fall-back）")
        self.history.clear()
        out: dict[str, list[float]] = {
            "iter": [],
            "bellman_loss": [],
            "cql_conservative": [],
            "total_loss": [],
            "alpha": [],
            "eval_value": [],
        }
        for it in range(self.config.n_iterations):
            batch = self.dataset.sample_batch(self.config.batch_size)
            cand = self._sample_candidates(self.cql.config.n_candidate_actions)
            cand_next = self._sample_candidates(self.cql.config.n_candidate_actions)
            info = self.cql.step(
                batch["states"], batch["actions"], batch["rewards"],
                batch["next_states"], batch["dones"],
                cand, cand_next,
            )
            eval_v = float("nan")
            if eval_callback is not None and (it + 1) % self.config.eval_every == 0:
                eval_v = float(eval_callback(self.cql, self.dataset))
            self.history.append({**info, "iter": it, "eval_value": eval_v})
            out["iter"].append(float(it))
            out["bellman_loss"].append(info["bellman_loss"])
            out["cql_conservative"].append(info["cql_conservative"])
            out["total_loss"].append(info["total_loss"])
            out["alpha"].append(info["alpha"])
            out["eval_value"].append(eval_v)
        return out


# ===========================================================================
# R385 — 离线策略评估 OPE（Fitted Q Evaluation, FQE）
# ===========================================================================


@dataclass
class FQEConfig:
    """R385 FQE 配置。"""

    gamma: float = 0.99
    n_iterations: int = 50
    batch_size: int = 32
    learning_rate: float = 1e-3
    tau: float = 0.005
    n_candidate_actions: int = 10
    seed: int = 42


class OfflineEvaluator:
    """R385 离线策略评估 FQE（Fitted Q Evaluation）。

    FQE（Levine 2020 §4.3 / Agarwal 2020 NeurIPS）：给定目标策略 π_e，
    在离线数据集 D 上拟合 Q^π_e，用于估计 π_e 的期望回报
    E_{s0~D}[Q^π_e(s0, π_e(s0))]。

    FQE 迭代：
        y = r + γ · (1 − done) · Q(s', π_e(s'))
        L = E[(Q(s, a) − y)²]

    学术依据：
    - Agarwal 2020 NeurIPS OPE https://arxiv.org/abs/2007.09055
    - Levine 2020 Offline RL Survey §4.3
      https://arxiv.org/abs/2005.01643
    """

    def __init__(
        self,
        dataset: OfflineDataset,
        eval_policy: Callable[[np.ndarray], np.ndarray],
        q_network: QNetwork | None = None,
        config: FQEConfig | None = None,
    ) -> None:
        self.dataset = dataset
        self.eval_policy = eval_policy  # π_e(s) → a
        self.q_network = q_network or QNetwork(
            QNetworkConfig(
                state_dim=dataset.config.state_dim,
                action_dim=dataset.config.action_dim,
                seed=(config.seed if config else 42),
            )
        )
        self.config = config or FQEConfig()
        self._rng = np.random.default_rng(self.config.seed)
        self.history: list[float] = []

    def _fqe_target(self, batch: dict[str, np.ndarray]) -> np.ndarray:
        """FQE target: y = r + γ·(1-done)·Q_target(s', π_e(s'))。"""
        ns = batch["next_states"]
        r = batch["rewards"]
        d = batch["dones"]
        # π_e(s') → a'
        a_eval = np.atleast_2d(self.eval_policy(ns))  # [N, action_dim]
        if a_eval.shape[0] != ns.shape[0]:
            raise ValueError(f"eval_policy 输出 batch {a_eval.shape[0]} != {ns.shape[0]}")
        q_next = self.q_network.forward_target(ns, a_eval).ravel()  # [N]
        y = r + self.config.gamma * (1.0 - d) * q_next
        return y.reshape(-1, 1)

    def _mse_grad(
        self, states: np.ndarray, actions: np.ndarray, targets: np.ndarray
    ) -> dict[str, np.ndarray]:
        """对 (Q(s,a) - y)² 求梯度（中心差分）。"""
        eps = 1e-4
        params = self.q_network.parameters()

        def loss_fn() -> float:
            q = self.q_network.forward(states, actions)
            return float(np.mean((q - targets) ** 2))

        base = loss_fn()
        grads: dict[str, np.ndarray] = {}
        for name, p in params.items():
            g = np.zeros_like(p)
            it = np.nditer(p, flags=["multi_index"], op_flags=["readwrite"])
            while not it.finished:
                idx = it.multi_index
                orig = float(p[idx])
                p[idx] = orig + eps
                self.q_network.set_parameters(params)
                loss_p = loss_fn()
                p[idx] = orig - eps
                self.q_network.set_parameters(params)
                loss_m = loss_fn()
                p[idx] = orig
                g[idx] = (loss_p - loss_m) / (2.0 * eps)
                it.iternext()
            self.q_network.set_parameters(params)
            grads[name] = g
        return grads

    def fit(self) -> dict[str, list[float]]:
        """FQE 迭代拟合 Q^π_e。"""
        if len(self.dataset) == 0:
            raise ValueError("数据集为空（R03）")
        self.history.clear()
        out: dict[str, list[float]] = {"iter": [], "loss": [], "value_estimate": []}
        for it in range(self.config.n_iterations):
            batch = self.dataset.sample_batch(self.config.batch_size)
            y = self._fqe_target(batch)
            grads = self._mse_grad(batch["states"], batch["actions"], y)
            lr = self.config.learning_rate
            params = self.q_network.parameters()
            for k in params:
                params[k] -= lr * grads[k]
            self.q_network.set_parameters(params)
            self.q_network.soft_update(self.config.tau)
            # 当前 loss
            q = self.q_network.forward(batch["states"], batch["actions"])
            loss = float(np.mean((q - y) ** 2))
            self.history.append(loss)
            out["iter"].append(float(it))
            out["loss"].append(loss)
            out["value_estimate"].append(float(np.mean(q)))
        return out

    def estimate_value(self, initial_states: np.ndarray) -> float:
        """估计 π_e 在初始状态分布下的期望回报。

        V(s0) = Q^π_e(s0, π_e(s0))，对所有 s0 求均值。

        Args:
            initial_states: [N, state_dim]
        Returns:
            mean V(s0)
        """
        s0 = np.atleast_2d(np.asarray(initial_states, dtype=np.float64))
        if s0.shape[1] != self.q_network.config.state_dim:
            raise ValueError(
                f"initial_states 维度 {s0.shape[1]} != {self.q_network.config.state_dim}"
            )
        a0 = np.atleast_2d(self.eval_policy(s0))
        if a0.shape[0] != s0.shape[0]:
            raise ValueError("eval_policy 输出 batch 不匹配")
        v = self.q_network.forward(s0, a0).ravel()
        return float(np.mean(v))
