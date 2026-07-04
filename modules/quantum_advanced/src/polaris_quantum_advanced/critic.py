"""PPO 价值网络（Critic）— V(s) 状态价值估计（纯 NumPy，R04 不参与 GPU）。

从 distributed_ppo.py 拆分而来（R11 质量门禁：文件≤800行），保留原始文献溯源。

学术依据（R02）:
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
- Kingma & Ba, "Adam: A Method for Stochastic Optimization", ICLR 2015.
  URL: https://arxiv.org/abs/1412.6980
- He et al., "Delving Deep into Rectifiers", ICCV 2015（He 初始化）.
  URL: https://arxiv.org/abs/1502.01852

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R05 Bug 必修。
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from polaris_quantum_advanced.actor import _BaseMLP


class _ValueNetwork(_BaseMLP):
    """价值网络（Critic），估计 V(s)。

    使用 MSE loss 训练: L^VF(θ) = E_t[(V_θ(s_t) - R_t)²]

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
        """价值函数更新，MSE loss。

        L^VF(θ) = E_t[(V_θ(s_t) - R_t)²]
        ∇L^VF / ∇V = 2(V_θ(s_t) - R_t) / N

        文献:
        - Schulman et al., "GAE", arXiv:1506.02438, 2016
          URL: https://arxiv.org/abs/1506.02438
        """
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


__all__ = ["_ValueNetwork"]
