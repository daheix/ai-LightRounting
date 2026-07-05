"""分布式 PPO 训练框架 - 神经网络模块（polaris-quantum-advanced 子模块）。

从 ``distributed_ppo.py`` 拆分而来，包含 PPO 算法使用的神经网络:
- _BaseMLP: 基础 MLP 网络（NumPy 实现，R04 不参与 GPU）
- _PolicyNetwork: 策略网络（Actor，输出动作分布）
- _ValueNetwork: 价值网络（Critic，输出状态价值）

学术依据（R02）:
- Schulman et al., "Proximal Policy Optimization Algorithms", arXiv:1707.06347, 2017.
  URL: https://arxiv.org/abs/1707.06347
- Mnih et al., "Asynchronous Methods for Deep Reinforcement Learning", ICML 2016.
  URL: http://proceedings.mlr.press/v48/mniha16.html
- Williams, "Simple Statistical Gradient-Following Algorithms for
  Connectionist Reinforcement Learning", MLJ 1992.
  URL: https://link.springer.com/article/10.1007/BF00992696
- Sutton & Barto, "Reinforcement Learning: An Introduction", 2nd ed., 2018.
  URL: http://incompleteideas.net/book/the-book-2nd.html
- Goodfellow et al., "Deep Learning", MIT Press 2016（MLP/反向传播）
  URL: https://www.deeplearningbook.org/

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU。
"""

from __future__ import annotations

from typing import Any

import numpy as np
from numpy.typing import NDArray

class _BaseMLP:
    """基础 MLP 网络（纯 NumPy 实现，R04 不参与 GPU）。"""

    def __init__(self, obs_dim: int, hidden_dim: int, output_dim: int, lr: float) -> None:
        self.obs_dim = obs_dim
        self.hidden_dim = hidden_dim
        self.output_dim = output_dim
        self.lr = lr
        rng = np.random.default_rng(42)
        self.W1 = rng.normal(0, np.sqrt(2.0 / obs_dim), (obs_dim, hidden_dim))
        self.b1 = np.zeros(hidden_dim)
        self.W2 = rng.normal(0, np.sqrt(2.0 / hidden_dim), (hidden_dim, hidden_dim))
        self.b2 = np.zeros(hidden_dim)
        self.W3 = rng.normal(0, np.sqrt(2.0 / hidden_dim), (hidden_dim, output_dim))
        self.b3 = np.zeros(output_dim)
        self._m = [np.zeros_like(p) for p in self._params()]
        self._v = [np.zeros_like(p) for p in self._params()]
        self._t = 0

    def _params(self) -> list[NDArray[np.float64]]:
        return [self.W1, self.b1, self.W2, self.b2, self.W3, self.b3]

    def _forward(self, obs: NDArray[np.float64]) -> tuple[NDArray, NDArray, NDArray]:
        h1 = np.tanh(obs @ self.W1 + self.b1)
        h2 = np.tanh(h1 @ self.W2 + self.b2)
        out = h2 @ self.W3 + self.b3
        return h1, h2, out

    def _backward(self, obs: NDArray, h1: NDArray, h2: NDArray,
                  grad_out: NDArray) -> list[NDArray]:
        grad_W3 = h2.T @ grad_out
        grad_b3 = np.sum(grad_out, axis=0)
        grad_h2 = grad_out @ self.W3.T
        grad_h2_pre = grad_h2 * (1 - h2 ** 2)
        grad_W2 = h1.T @ grad_h2_pre
        grad_b2 = np.sum(grad_h2_pre, axis=0)
        grad_h1 = grad_h2_pre @ self.W2.T
        grad_h1_pre = grad_h1 * (1 - h1 ** 2)
        grad_W1 = obs.T @ grad_h1_pre
        grad_b1 = np.sum(grad_h1_pre, axis=0)
        return [grad_W1, grad_b1, grad_W2, grad_b2, grad_W3, grad_b3]

    def _adam_update(self, grads: list[NDArray], max_grad_norm: float) -> float:
        grad_norm = float(np.sqrt(sum(np.sum(g ** 2) for g in grads)))
        if grad_norm > max_grad_norm:
            scale = max_grad_norm / grad_norm
            grads = [g * scale for g in grads]
        self._t += 1
        beta1, beta2, eps = 0.9, 0.999, 1e-8
        params = self._params()
        for i, (p, g) in enumerate(zip(params, grads)):
            self._m[i] = beta1 * self._m[i] + (1 - beta1) * g
            self._v[i] = beta2 * self._v[i] + (1 - beta2) * (g ** 2)
            m_hat = self._m[i] / (1 - beta1 ** self._t)
            v_hat = self._v[i] / (1 - beta2 ** self._t)
            p -= self.lr * m_hat / (np.sqrt(v_hat) + eps)
        return grad_norm


class _PolicyNetwork(_BaseMLP):
    """策略网络（Actor），PPO-Clip 目标函数。

    文献:
    - Schulman et al., "Proximal Policy Optimization Algorithms", arXiv:1707.06347, 2017.
      URL: https://arxiv.org/abs/1707.06347
    - Williams, "Simple Statistical Gradient-Following Algorithms for
      Connectionist Reinforcement Learning", MLJ 1992.
      URL: https://link.springer.com/article/10.1007/BF00992696
    - Sutton & Barto, "Reinforcement Learning: An Introduction", 2nd ed., 2018.
      URL: http://incompleteideas.net/book/the-book-2nd.html
    - Mnih et al., "Asynchronous Methods for Deep Reinforcement Learning", ICML 2016.
      URL: http://proceedings.mlr.press/v48/mniha16.html
    - Schulman et al., "Trust Region Policy Optimization", ICML 2015.
      URL: https://arxiv.org/abs/1502.05477
    """

    def __init__(self, obs_dim: int, action_dim: int, lr: float = 3e-4) -> None:
        super().__init__(obs_dim, 64, action_dim, lr)
        self.action_dim = action_dim

    def forward(self, obs: NDArray[np.float64]) -> NDArray[np.float64]:
        _, _, logits = self._forward(obs)
        return logits

    def _softmax(self, logits: NDArray[np.float64]) -> NDArray[np.float64]:
        logits = logits - np.max(logits, axis=1, keepdims=True)
        exp_logits = np.exp(logits)
        probs = exp_logits / np.sum(exp_logits, axis=1, keepdims=True)
        probs = np.clip(probs, 1e-10, 1.0)
        probs = probs / np.sum(probs, axis=1, keepdims=True)
        return probs

    def act(self, obs: NDArray[np.float64], rng: np.random.Generator) -> tuple[int, float]:
        """采样动作，返回 (action, log_prob)。"""
        logits = self.forward(obs.reshape(1, -1))
        probs = self._softmax(logits)[0]
        action = int(rng.choice(self.action_dim, p=probs))
        log_prob = float(np.log(probs[action]))
        return action, log_prob

    def evaluate(self, obs: NDArray[np.float64],
                 actions: NDArray[np.int64]) -> tuple[NDArray, NDArray, NDArray]:
        """计算动作概率、log_prob 和熵。"""
        logits = self.forward(obs)
        probs = self._softmax(logits)
        action_probs = probs[np.arange(len(obs)), actions]
        log_probs = np.log(action_probs)
        entropy = -np.sum(probs * np.log(probs), axis=1)
        return log_probs, entropy, probs

    def update(self, obs_batch: NDArray[np.float64],
               action_batch: NDArray[np.int64],
               old_log_prob: NDArray[np.float64],
               advantages: NDArray[np.float64],
               clip_ratio: float = 0.2,
               entropy_coeff: float = 0.01,
               max_grad_norm: float = 0.5) -> dict[str, float]:
        """PPO-Clip 策略更新。

        L^CLIP(θ) = E_t[min(r_t(θ)·Â_t, clip(r_t(θ), 1−ε, 1+ε)·Â_t)]

        梯度计算: 对未截断样本，梯度为 -r_t · Â_t · ∇log π(a|s)；
        对截断样本，梯度为 0（停止梯度）。

        文献:
        - Schulman et al., PPO, arXiv:1707.06347, 2017. §3 eq.(7)
          URL: https://arxiv.org/abs/1707.06347
        """
        n = len(obs_batch)
        if n == 0:
            raise ValueError("批次不能为空")

        h1, h2, logits = self._forward(obs_batch)
        probs = self._softmax(logits)

        action_probs = probs[np.arange(n), action_batch]
        new_log_prob = np.log(action_probs)
        ratio = np.exp(new_log_prob - old_log_prob)

        surr1 = ratio * advantages
        surr2 = np.clip(ratio, 1 - clip_ratio, 1 + clip_ratio) * advantages
        min_surr = np.minimum(surr1, surr2)
        policy_loss = -float(np.mean(min_surr))

        entropy = -float(np.mean(np.sum(probs * np.log(probs), axis=1)))
        total_loss = policy_loss - entropy_coeff * entropy

        grad_logits = self._compute_policy_gradients(
            n, probs, action_batch, ratio, advantages, clip_ratio, entropy_coeff,
        )

        grads = self._backward(obs_batch, h1, h2, grad_logits)
        grad_norm = self._adam_update(grads, max_grad_norm)

        return {
            "policy_loss": policy_loss,
            "entropy": entropy,
            "total_loss": total_loss,
            "grad_norm": grad_norm,
        }

    def _compute_policy_gradients(
        self, n: int, probs: NDArray, action_batch: NDArray,
        ratio: NDArray, advantages: NDArray,
        clip_ratio: float, entropy_coeff: float,
    ) -> NDArray:
        """计算 PPO-Clip 策略梯度（含截断判断 + 熵正则梯度）。

        未截断梯度: -ratio * A * ∇log π(a|s)
        截断梯度: 0（停止梯度）
        ∇ log π(a)/d logits_j = δ_{aj} - π_j  (softmax 梯度)

        文献: Schulman et al., PPO, arXiv:1707.06347, 2017. §3
        """
        logits_grad = np.zeros_like(probs)
        for i in range(n):
            clipped_upper = (advantages[i] > 0) and (ratio[i] > 1 + clip_ratio)
            clipped_lower = (advantages[i] < 0) and (ratio[i] < 1 - clip_ratio)
            is_clipped = clipped_upper or clipped_lower
            if not is_clipped:
                a = action_batch[i]
                coeff = -ratio[i] * advantages[i] / n
                logits_grad[i, :] += coeff * (-probs[i, :])
                logits_grad[i, a] += coeff

        # 熵正则梯度: H = -Σ p_i log p_i
        log_p = np.log(probs)
        d_entropy_d_logits = probs * (log_p + 1)
        d_entropy_d_logits -= probs * np.sum(probs * (log_p + 1), axis=1, keepdims=True)
        logits_grad += -entropy_coeff * d_entropy_d_logits / n
        return logits_grad


class _ValueNetwork(_BaseMLP):
    """价值网络（Critic），估计 V(s)。

    文献:
    - Schulman et al., "High-Dimensional Continuous Control Using
      Generalized Advantage Estimation", ICLR 2016.
      URL: https://arxiv.org/abs/1506.02438
    - Sutton & Barto, "Reinforcement Learning: An Introduction", 2nd ed., 2018.
      URL: http://incompleteideas.net/book/the-book-2nd.html
    - Mnih et al., "Asynchronous Methods for Deep Reinforcement Learning", ICML 2016.
      URL: http://proceedings.mlr.press/v48/mniha16.html
    - Schulman et al., "Proximal Policy Optimization Algorithms", arXiv:1707.06347, 2017.
      URL: https://arxiv.org/abs/1707.06347
    - Sutton, "Learning to Predict by the Methods of Temporal Differences", MLJ 1988.
      URL: https://link.springer.com/article/10.1007/BF00115009
    """

    def __init__(self, obs_dim: int, lr: float = 1e-3) -> None:
        super().__init__(obs_dim, 64, 1, lr)

    def forward(self, obs: NDArray[np.float64]) -> NDArray[np.float64]:
        _, _, values = self._forward(obs)
        return values.squeeze(axis=-1)

    def update(self, obs_batch: NDArray[np.float64],
               returns: NDArray[np.float64],
               max_grad_norm: float = 0.5) -> dict[str, float]:
        """价值函数更新，MSE loss。"""
        n = len(obs_batch)
        if n == 0:
            raise ValueError("批次不能为空")

        h1, h2, values = self._forward(obs_batch)
        values = values.squeeze(axis=-1)
        value_loss = float(np.mean((values - returns) ** 2))

        grad_values = 2.0 * (values - returns) / n
        grad_out = grad_values.reshape(-1, 1)
        grads = self._backward(obs_batch, h1, h2, grad_out)
        grad_norm = self._adam_update(grads, max_grad_norm)

        return {
            "value_loss": value_loss,
            "value_grad_norm": grad_norm,
        }



__all__ = ["_BaseMLP", "_PolicyNetwork", "_ValueNetwork"]
