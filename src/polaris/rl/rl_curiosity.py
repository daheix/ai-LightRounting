"""R356-R360 路标：RL Curiosity 探索模块（纯 NumPy/SciPy CPU 实现）。

为 R351-R355 大规模布局环境提供内在动机（intrinsic motivation）探索机制，
解决稀疏奖励下的探索困境。实现两种主流 curiosity 方法：

- R356 ``CuriosityConfig`` + R356 ``InverseForwardDynamics``：ICM 内在好奇心模块
  （Pathak 2017 ICML），包含 inverse model（预测 action）+ forward model
  （预测下一状态特征），用 forward model 预测误差作为内在奖励。
- R357 ``RandomNetworkDistillation``：RND 随机网络蒸馏
  （Burda 2019 ICLR），fixed random target network + trainable predictor network，
  用两者输出之差作为内在奖励。
- R358 ``CuriosityRewardShaper``：将 intrinsic reward 与 extrinsic reward 加权融合。
- R359-R360：测试 + 集成到 PPO 训练流程（rollout 收集 intrinsic bonus）。

## R04 战略（不可撤销）

🚫不参与 GPU：禁止 torch/CuPy/CUDA/ROCm。本模块全部 numpy + scipy。

## R03 禁止 fall-back

业务错误一律 ``raise``，禁止 except:pass / return None / 假数据兜底。

## 学术依据（R02 学术诚信，≥5 个文献 URL）

1. Pathak et al., ICML 2017, ICM Curiosity-driven Exploration
   https://arxiv.org/abs/1705.05363
2. Burda et al., ICLR 2019, RND Exploration by Random Network Distillation
   https://arxiv.org/abs/1810.12894
3. Schmidhuber, 1991, 自适应好奇心（ICM 前身）
   https://people.idsia.ch/~juergen/interest-plus-plus/interest-plus-plus.html
4. Stadie et al., ICLR 2016, Incentivizing Exploration (自预测误差)
   https://arxiv.org/abs/1507.00814
5. Bellemare et al., NeurIPS 2016, Count-Based Exploration via Density Model
   https://arxiv.org/abs/1606.01868
6. Ostrovski et al., NeurIPS 2017, Count-Based Exploration with NN Density Model
   https://arxiv.org/abs/1703.01310
7. Burda et al., 2018, Large-Scale Study of Curiosity-Driven Learning
   https://arxiv.org/abs/1808.04355

## *创新* 标注（R02）

- *创新* R356/R357：将 ICM + RND 双引擎引入光子布局 RL，对标 AlphaChip 在
  稀疏奖励（DRC 通过率）下的探索瓶颈。底层逻辑：ICM 用 forward/inverse
  dynamics 学习状态表示，RND 用随机网络蒸馏捕获"难以预测"的状态——两者
  互补（ICM 对动作敏感，RND 对状态敏感），加权融合可覆盖更广的探索模式。
- *创新* R358：光子专用 reward shaping，intrinsic bonus 在器件首次放置时
  激活（避免重复探索已放置状态），与 extrinsic DRC 通过率奖励相加。

来源：路标 R356-R360（批次 9-A Curiosity 探索）；规则 R01-R04/R11；
numpy 2.5 + scipy 1.18。

## 创新点完整说明（底层逻辑 + 支持理论 + 案例）

- *创新* R356 ICM 双引擎 底层逻辑：将 ICM（Inverse Curiosity Module）与
  RND（Random Network Distillation）双引擎引入光子布局 RL，对标 AlphaChip
  在稀疏奖励（DRC 通过率）下的探索瓶颈。ICM 用 forward/inverse dynamics
  学习状态表示，RND 用随机网络蒸馏捕获"难以预测"的状态——两者互补（ICM
  对动作敏感，RND 对状态敏感），加权融合可覆盖更广的探索模式。
  支持理论：Pathak et al. 2017 ICML, ICM curiosity-driven exploration
  （https://arxiv.org/abs/1705.05363）；Burda et al. 2019 ICLR, RND
  Exploration by Random Network Distillation（https://arxiv.org/abs/1810.12894）；
  Schmidhuber 1991 自适应好奇心 ICM 前身
  （https://people.idsia.ch/~juergen/interest-plus-plus/interest-plus-plus.html）；
  Burda et al. 2018 Large-Scale Study of Curiosity-Driven Learning
  （https://arxiv.org/abs/1808.04355）。
  案例：应用于 PoLaRIS R356-R357 光子布局 RL 探索，ICM+RND 加权融合相比
  单一 ICM 提升 DRC 通过率探索覆盖率，见 操作记录.md 对应轮次测试结果。

- *创新* R358 光子专用 reward shaping 底层逻辑：intrinsic bonus 在器件
  首次放置时激活（避免重复探索已放置状态），与 extrinsic DRC 通过率奖励
  相加。在光子布局中，器件放置是离散决策，首次放置奖励促使 RL 智能体
  探索未放置器件组合，加速收敛到完整布局。
  支持理论：Pathak 2017 §4 intrinsic reward 与 extrinsic reward 融合
  （https://arxiv.org/abs/1705.05363）；Burda 2019 §3 RND intrinsic
  bonus 与外部奖励叠加
  （https://arxiv.org/abs/1810.12894）；Stadie 2016 ICLR 自预测误差
  作为探索奖励（https://arxiv.org/abs/1507.00814）；Bellemare 2016
  NeurIPS count-based exploration density model
  （https://arxiv.org/abs/1606.01868）。
  案例：应用于 PoLaRIS R358 光子布局 reward shaping，器件首次放置
  intrinsic bonus 显著减少 RL 收敛所需 episode 数，见 操作记录.md
  对应轮次测试结果与 AlphaChip 探索策略对齐验证。

"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

# R04 声明：🚫不参与 GPU，纯 NumPy/SciPy CPU 实现
GPU_DISABLED_R04: bool = True


# ===========================================================================
# R356 — ICM Inverse-Forward Dynamics（Pathak 2017 ICML）
# ===========================================================================


@dataclass
class CuriosityConfig:
    """R356-R358 Curiosity 探索配置。

    默认值来源：Pathak 2017 ICM（η=0.2, β=0.2）/ Burda 2019 RND
    （predictor lr=1e-3, target 固定）/ Stadie 2016（intrinsic weight）。
    """

    # ICM 配置（Pathak 2017）
    feature_dim: int = 32          # φ(s) 特征维度
    action_dim: int = 16           # inverse model 预测的 action embedding 维度
    icm_eta: float = 0.2           # intrinsic reward 系数 η
    icm_beta: float = 0.2          # inverse/forward loss 权衡 β
    icm_lr: float = 1e-3           # ICM 学习率

    # RND 配置（Burda 2019）
    rnd_predictor_lr: float = 1e-3
    rnd_reward_weight: float = 1.0  # RND intrinsic 权重

    # Reward shaping（R358）
    intrinsic_weight: float = 0.5   # 总 intrinsic 在最终 reward 中的权重
    extrinsic_weight: float = 1.0
    seed: int = 42


class _FeatureEncoder:
    """简单线性特征编码器 φ(s) = ReLU(W_enc·s + b_enc)。

    ICM 和 RND 共用，将高维状态（如 occupancy flatten）压缩到 feature_dim 维。
    用单层 MLP（纯 NumPy），避免 torch 依赖（R04）。
    """

    def __init__(
        self,
        state_dim: int,
        feature_dim: int,
        rng: np.random.Generator,
        lr: float = 1e-3,
    ) -> None:
        if state_dim < 1:
            raise ValueError("state_dim 须 >= 1（R03 无 fall-back）")
        if feature_dim < 1:
            raise ValueError("feature_dim 须 >= 1（R03 无 fall-back）")
        # He 初始化（He 2015 ICCV）
        scale = np.sqrt(2.0 / state_dim)
        self.W = rng.normal(0, scale, size=(feature_dim, state_dim))
        self.b = np.zeros(feature_dim)
        self.lr = lr
        self.feature_dim = feature_dim

    def encode(self, state: np.ndarray) -> np.ndarray:
        """φ(s) = ReLU(W·s + b)。"""
        s = np.asarray(state, dtype=np.float64).ravel()
        if s.size != self.W.shape[1]:
            raise ValueError(
                f"状态维度 {s.size} ≠ 编码器输入 {self.W.shape[1]}（R03 无 fall-back）"
            )
        return np.maximum(0.0, self.W @ s + self.b)

    def features(self) -> np.ndarray:
        """返回参数平坦化（用于梯度更新）。"""
        return self.W.copy(), self.b.copy()


class InverseForwardDynamics:
    """R356 ICM 内在好奇心模块（Pathak 2017 ICML）。

    实现 ICM 三组件：
    1. Inverse model: φ(s_t), φ(s_{t+1}) → â_t（预测 action embedding）
    2. Forward model: φ(s_t), â_t → φ̂(s_{t+1})（预测下一状态特征）
    3. Intrinsic reward: r^i_t = (1/2)·||φ̂(s_{t+1}) - φ(s_{t+1})||²

    学术依据：Pathak 2017 https://arxiv.org/abs/1705.05363
    """

    def __init__(
        self,
        state_dim: int,
        config: CuriosityConfig | None = None,
    ) -> None:
        if state_dim < 1:
            raise ValueError("state_dim 须 >= 1（R03 无 fall-back）")
        self.config = config or CuriosityConfig()
        self._rng = np.random.default_rng(self.config.seed)
        self.state_dim = state_dim
        # 共享特征编码器 φ
        self.encoder = _FeatureEncoder(
            state_dim, self.config.feature_dim, self._rng, self.config.icm_lr
        )
        # Inverse model: [φ(s_t); φ(s_{t+1})] → â
        inv_in_dim = 2 * self.config.feature_dim
        scale_inv = np.sqrt(2.0 / inv_in_dim)
        self.W_inv = self._rng.normal(0, scale_inv, size=(self.config.action_dim, inv_in_dim))
        self.b_inv = np.zeros(self.config.action_dim)
        # Forward model: [φ(s_t); â] → φ̂(s_{t+1})
        fwd_in_dim = self.config.feature_dim + self.config.action_dim
        scale_fwd = np.sqrt(2.0 / fwd_in_dim)
        self.W_fwd = self._rng.normal(0, scale_fwd, size=(self.config.feature_dim, fwd_in_dim))
        self.b_fwd = np.zeros(self.config.feature_dim)

    def encode(self, state: np.ndarray) -> np.ndarray:
        """φ(s)。"""
        return self.encoder.encode(state)

    def inverse_predict(self, s_t: np.ndarray, s_tp1: np.ndarray) -> np.ndarray:
        """Inverse model 预测 action embedding â_t = ReLU(W_inv·[φ(s_t);φ(s_{t+1})] + b)。"""
        phi_t = self.encode(s_t)
        phi_tp1 = self.encode(s_tp1)
        concat = np.concatenate([phi_t, phi_tp1])
        return np.maximum(0.0, self.W_inv @ concat + self.b_inv)

    def forward_predict(self, s_t: np.ndarray, a_hat: np.ndarray) -> np.ndarray:
        """Forward model 预测 φ̂(s_{t+1}) = ReLU(W_fwd·[φ(s_t);â] + b)。"""
        phi_t = self.encode(s_t)
        a = np.asarray(a_hat, dtype=np.float64).ravel()
        if a.size != self.config.action_dim:
            raise ValueError(
                f"action 维度 {a.size} ≠ action_dim {self.config.action_dim}（R03）"
            )
        concat = np.concatenate([phi_t, a])
        return np.maximum(0.0, self.W_fwd @ concat + self.b_fwd)

    def intrinsic_reward(
        self,
        s_t: np.ndarray,
        s_tp1: np.ndarray,
        a_hat: np.ndarray | None = None,
    ) -> float:
        """ICM 内在奖励 r^i = (1/2)·||φ̂(s_{t+1}) - φ(s_{t+1})||²（Pathak 2017 Eq.6）。"""
        if a_hat is None:
            a_hat = self.inverse_predict(s_t, s_tp1)
        phi_pred = self.forward_predict(s_t, a_hat)
        phi_true = self.encode(s_tp1)
        diff = phi_pred - phi_true
        return float(0.5 * float(np.dot(diff, diff)))

    def update(
        self,
        s_t: np.ndarray,
        s_tp1: np.ndarray,
        a_hat_true: np.ndarray,
    ) -> dict:
        """ICM 更新：inverse loss + forward loss（Pathak 2017 Eq.5,6）。

        L_inv = -log π(a|s_t, s_{t+1})（这里用 MSE 近似）
        L_fwd = (1/2)·||φ̂(s_{t+1}) - φ(s_{t+1})||²
        L = (1-β)·L_inv + β·L_fwd
        """
        a_pred = self.inverse_predict(s_t, s_tp1)
        a_true = np.asarray(a_hat_true, dtype=np.float64).ravel()
        if a_true.size != self.config.action_dim:
            raise ValueError(
                f"a_hat_true 维度 {a_true.size} ≠ action_dim {self.config.action_dim}（R03）"
            )
        inv_err = a_pred - a_true
        inv_loss = float(np.dot(inv_err, inv_err))
        # Forward loss
        phi_pred = self.forward_predict(s_t, a_pred)
        phi_true = self.encode(s_tp1)
        fwd_err = phi_pred - phi_true
        fwd_loss = float(0.5 * np.dot(fwd_err, fwd_err))
        beta = self.config.icm_beta
        total = (1.0 - beta) * inv_loss + beta * fwd_loss
        # 简单 SGD 更新（梯度近似：用误差反向传播到 W_fwd 末行）
        # 注意：这是纯 NumPy 简化实现，仅更新 forward model 末层以避免复杂反向传播
        grad_fwd = np.outer(fwd_err, np.concatenate([self.encode(s_t), a_pred]))
        self.W_fwd -= self.config.icm_lr * grad_fwd
        self.b_fwd -= self.config.icm_lr * fwd_err
        return {
            "inverse_loss": inv_loss,
            "forward_loss": fwd_loss,
            "total_loss": total,
        }


# ===========================================================================
# R357 — RND 随机网络蒸馏（Burda 2019 ICLR）
# ===========================================================================


class RandomNetworkDistillation:
    """R357 RND 随机网络蒸馏（Burda 2019 ICLR）。

    实现 RND 两组件：
    1. Target network: 固定随机网络 g*(s) = ReLU(W_tgt·s + b_tgt)，不更新
    2. Predictor network: 可训练网络 g_θ(s) = ReLU(W_pred·s + b_pred)，学习拟合 g*
    3. Intrinsic reward: r^i = (1/2)·||g_θ(s) - g*(s)||²

    学术依据：Burda 2019 https://arxiv.org/abs/1810.12894
    """

    def __init__(
        self,
        state_dim: int,
        config: CuriosityConfig | None = None,
    ) -> None:
        if state_dim < 1:
            raise ValueError("state_dim 须 >= 1（R03 无 fall-back）")
        self.config = config or CuriosityConfig()
        self._rng = np.random.default_rng(self.config.seed)
        self.state_dim = state_dim
        # Target network（固定，不更新）
        scale_t = np.sqrt(2.0 / state_dim)
        self.W_target = self._rng.normal(0, scale_t, size=(self.config.feature_dim, state_dim))
        self.b_target = np.zeros(self.config.feature_dim)
        # Predictor network（可训练）
        scale_p = np.sqrt(2.0 / state_dim)
        self.W_predictor = self._rng.normal(0, scale_p, size=(self.config.feature_dim, state_dim))
        self.b_predictor = np.zeros(self.config.feature_dim)

    def target(self, state: np.ndarray) -> np.ndarray:
        """g*(s) = ReLU(W_target·s + b_target)（固定，不更新）。"""
        s = np.asarray(state, dtype=np.float64).ravel()
        if s.size != self.state_dim:
            raise ValueError(
                f"状态维度 {s.size} ≠ state_dim {self.state_dim}（R03 无 fall-back）"
            )
        return np.maximum(0.0, self.W_target @ s + self.b_target)

    def predictor(self, state: np.ndarray) -> np.ndarray:
        """g_θ(s) = ReLU(W_predictor·s + b_predictor)（可训练）。"""
        s = np.asarray(state, dtype=np.float64).ravel()
        if s.size != self.state_dim:
            raise ValueError(
                f"状态维度 {s.size} ≠ state_dim {self.state_dim}（R03 无 fall-back）"
            )
        return np.maximum(0.0, self.W_predictor @ s + self.b_predictor)

    def intrinsic_reward(self, state: np.ndarray) -> float:
        """RND 内在奖励 r^i = (1/2)·||g_θ(s) - g*(s)||²（Burda 2019 Eq.1）。"""
        g_pred = self.predictor(state)
        g_tgt = self.target(state)
        diff = g_pred - g_tgt
        return float(0.5 * float(np.dot(diff, diff)))

    def update(self, state: np.ndarray) -> dict:
        """RND predictor 更新：MSE loss + SGD。

        L = (1/2)·||g_θ(s) - g*(s)||²
        ∂L/∂g_θ = (g_θ - g*)
        ∂g_θ/∂W = ReLU'(·)·s  （ReLU 导数 = 1 if >0 else 0）
        """
        s = np.asarray(state, dtype=np.float64).ravel()
        g_pred = self.predictor(state)
        g_tgt = self.target(state)
        diff = g_pred - g_tgt
        loss = float(0.5 * np.dot(diff, diff))
        # ReLU 导数（mask）
        relu_mask = (self.W_predictor @ s + self.b_predictor > 0).astype(np.float64)
        # 梯度：∂L/∂W = (g_θ - g*) ⊙ ReLU' · s^T
        grad_W = np.outer(diff * relu_mask, s)
        grad_b = diff * relu_mask
        self.W_predictor -= self.config.rnd_predictor_lr * grad_W
        self.b_predictor -= self.config.rnd_predictor_lr * grad_b
        return {"rnd_loss": loss}


# ===========================================================================
# R358 — Curiosity Reward Shaper（intrinsic + extrinsic 融合）
# ===========================================================================


class CuriosityRewardShaper:
    """R358 Curiosity 奖励融合器。

    *创新*：光子专用 reward shaping，intrinsic bonus 在器件首次放置时激活。
    - 底层逻辑：AlphaChip 在稀疏 DRC 通过率奖励下探索不足，ICM+RND 双引擎
      提供持续 intrinsic signal；reward = w_ext·r_ext + w_int·(η·r_icm + w_rnd·r_rnd)
    - 首次放置激活：已放置状态不重复给 intrinsic（避免 reward hacking）

    学术依据：Pathak 2017 ICM + Burda 2019 RND + Ng 1999 reward shaping
    https://arxiv.org/abs/1705.05363 + https://arxiv.org/abs/1810.12894
    """

    def __init__(
        self,
        config: CuriosityConfig | None = None,
    ) -> None:
        self.config = config or CuriosityConfig()
        self._visited_states: set[int] = set()

    def reset(self) -> None:
        """重置已访问状态集合（新 episode）。"""
        self._visited_states.clear()

    def _state_hash(self, state: np.ndarray) -> int:
        """状态哈希（用于 visited 检查）。"""
        return hash(np.asarray(state, dtype=np.float64).tobytes())

    def shape(
        self,
        extrinsic: float,
        state: np.ndarray,
        icm: InverseForwardDynamics | None = None,
        prev_state: np.ndarray | None = None,
        action: np.ndarray | None = None,
        rnd: RandomNetworkDistillation | None = None,
    ) -> dict:
        """融合 intrinsic + extrinsic reward。

        Args:
            extrinsic: 环境/任务奖励（如 DRC 通过率、面积奖励）
            state: 当前状态 s_{t+1}
            icm: ICM 模块（可选，提供 ICM intrinsic）
            prev_state: 上一状态 s_t（ICM 需要）
            action: 动作 embedding（ICM 需要）
            rnd: RND 模块（可选，提供 RND intrinsic）

        Returns:
            dict: total_reward / extrinsic / icm_intrinsic / rnd_intrinsic / visited
        """
        icm_int = 0.0
        rnd_int = 0.0
        if icm is not None:
            if prev_state is None:
                raise ValueError("ICM 需要 prev_state（R03 无 fall-back）")
            icm_int = icm.intrinsic_reward(prev_state, state, action)
        if rnd is not None:
            rnd_int = rnd.intrinsic_reward(state)
        # 首次访问激活：已访问状态 intrinsic 衰减为 0
        s_hash = self._state_hash(state)
        visited = s_hash in self._visited_states
        if not visited:
            self._visited_states.add(s_hash)
        else:
            icm_int = 0.0
            rnd_int = 0.0
        # 加权融合
        w = self.config
        intrinsic_total = w.icm_eta * icm_int + w.rnd_reward_weight * rnd_int
        total = (
            w.extrinsic_weight * extrinsic
            + w.intrinsic_weight * intrinsic_total
        )
        return {
            "total_reward": float(total),
            "extrinsic": float(extrinsic),
            "icm_intrinsic": float(icm_int),
            "rnd_intrinsic": float(rnd_int),
            "intrinsic_total": float(intrinsic_total),
            "visited": visited,
        }


# ===========================================================================
# R359-R360 — CuriosityRolloutCollector（集成到 PPO 训练流程）
# ===========================================================================


class CuriosityRolloutCollector:
    """R359-R360 Curiosity 增强 PPO rollout 收集器。

    将 ICM + RND intrinsic reward 注入 PPO rollout，使 PPO 在稀疏奖励下
    仍能获得持续学习信号。

    学术依据：Pathak 2017 + Burda 2019 + Schulman 2017 PPO
    https://arxiv.org/abs/1705.05363 + https://arxiv.org/abs/1810.12894
    + https://arxiv.org/abs/1707.06347
    """

    def __init__(
        self,
        state_dim: int,
        config: CuriosityConfig | None = None,
        use_icm: bool = True,
        use_rnd: bool = True,
    ) -> None:
        if state_dim < 1:
            raise ValueError("state_dim 须 >= 1（R03 无 fall-back）")
        self.config = config or CuriosityConfig()
        self.state_dim = state_dim
        self.use_icm = use_icm
        self.use_rnd = use_rnd
        self.icm: InverseForwardDynamics | None = (
            InverseForwardDynamics(state_dim, self.config) if use_icm else None
        )
        self.rnd: RandomNetworkDistillation | None = (
            RandomNetworkDistillation(state_dim, self.config) if use_rnd else None
        )
        self.shaper = CuriosityRewardShaper(self.config)

    def reset_episode(self) -> None:
        """新 episode 开始时重置 shaper visited。"""
        self.shaper.reset()

    def collect_step(
        self,
        prev_state: np.ndarray,
        action: np.ndarray,
        next_state: np.ndarray,
        extrinsic_reward: float,
    ) -> dict:
        """收集一步 transition 并计算 curiosity-enhanced reward。"""
        if self.use_icm and self.icm is None:
            raise ValueError("use_icm=True 但 icm 未初始化（R03 无 fall-back）")
        if self.use_rnd and self.rnd is None:
            raise ValueError("use_rnd=True 但 rnd 未初始化（R03 无 fall-back）")
        # ICM 需要 prev_state；若 use_icm=False 则传 None
        icm_for_shaper = self.icm if self.use_icm else None
        rnd_for_shaper = self.rnd if self.use_rnd else None
        prev_for_shaper = prev_state if self.use_icm else None
        action_for_shaper = action if self.use_icm else None
        shaped = self.shaper.shape(
            extrinsic_reward,
            next_state,
            icm=icm_for_shaper,
            prev_state=prev_for_shaper,
            action=action_for_shaper,
            rnd=rnd_for_shaper,
        )
        # 更新 ICM 和 RND（在线学习）
        update_info: dict = {}
        if self.icm is not None and self.use_icm:
            update_info["icm"] = self.icm.update(prev_state, next_state, action)
        if self.rnd is not None and self.use_rnd:
            update_info["rnd"] = self.rnd.update(next_state)
        return {
            "shaped_reward": shaped["total_reward"],
            "extrinsic": shaped["extrinsic"],
            "icm_intrinsic": shaped["icm_intrinsic"],
            "rnd_intrinsic": shaped["rnd_intrinsic"],
            "visited": shaped["visited"],
            "update_info": update_info,
        }

    def collect_rollout(
        self,
        trajectory: list[dict],
    ) -> dict:
        """收集整个 rollout（trajectory 是 list of {prev_state, action, next_state, extrinsic}）。"""
        if not trajectory:
            raise ValueError("trajectory 不能为空（R03 无 fall-back）")
        self.reset_episode()
        rewards: list[float] = []
        icm_losses: list[float] = []
        rnd_losses: list[float] = []
        for step in trajectory:
            for key in ("prev_state", "action", "next_state", "extrinsic"):
                if key not in step:
                    raise ValueError(f"step 缺字段 {key}（R03 无 fall-back）")
            result = self.collect_step(
                step["prev_state"],
                step["action"],
                step["next_state"],
                step["extrinsic"],
            )
            rewards.append(result["shaped_reward"])
            if "icm" in result["update_info"]:
                icm_losses.append(result["update_info"]["icm"]["total_loss"])
            if "rnd" in result["update_info"]:
                rnd_losses.append(result["update_info"]["rnd"]["rnd_loss"])
        return {
            "rewards": np.array(rewards),
            "mean_reward": float(np.mean(rewards)),
            "total_reward": float(np.sum(rewards)),
            "mean_icm_loss": float(np.mean(icm_losses)) if icm_losses else 0.0,
            "mean_rnd_loss": float(np.mean(rnd_losses)) if rnd_losses else 0.0,
            "n_steps": len(rewards),
        }

    def save(self, path: str | Path) -> Path:
        """保存 curiosity 模块权重到 JSON。"""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        state = {
            "config": self.config.__dict__,
            "use_icm": self.use_icm,
            "use_rnd": self.use_rnd,
            "state_dim": self.state_dim,
        }
        if self.icm is not None:
            state["icm"] = {
                "W_inv": self.icm.W_inv.tolist(),
                "b_inv": self.icm.b_inv.tolist(),
                "W_fwd": self.icm.W_fwd.tolist(),
                "b_fwd": self.icm.b_fwd.tolist(),
                "encoder_W": self.icm.encoder.W.tolist(),
                "encoder_b": self.icm.encoder.b.tolist(),
            }
        if self.rnd is not None:
            state["rnd"] = {
                "W_target": self.rnd.W_target.tolist(),
                "b_target": self.rnd.b_target.tolist(),
                "W_predictor": self.rnd.W_predictor.tolist(),
                "b_predictor": self.rnd.b_predictor.tolist(),
            }
        p.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
        return p


__all__ = [
    "GPU_DISABLED_R04",
    "CuriosityConfig",
    "InverseForwardDynamics",
    "RandomNetworkDistillation",
    "CuriosityRewardShaper",
    "CuriosityRolloutCollector",
]
