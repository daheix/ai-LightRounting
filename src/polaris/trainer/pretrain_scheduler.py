"""R34: AlphaChip 预训练-微调范式 — 余弦退火学习率调度。

从 pretrain.py 拆分（facade 模式，保持外部 import 路径不变）。

实现 SGDR 余弦退火学习率调度，支持线性 warmup。

纯 NumPy/CPU 实现（🚫不参与 GPU，R04 战略决策）。

来源:
- Loshchilov & Hutter, 2017, SGDR (Stochastic Gradient Descent with
  Warm Restarts), https://arxiv.org/abs/1608.03983
- Mirhoseini et al., Nature 2021, AlphaChip 预训练范式
  https://www.nature.com/articles/s41586-021-03544-w
- Circuit Training Pre-training Guide
  https://github.com/google-research/circuit_training/blob/main/docs/PRETRAINING.md
- Goldie et al., arXiv 2024, 预训练必要性辩护
  https://arxiv.org/abs/2411.10053
- Hou et al., KDD 2022, GraphMAE 自监督图预训练
  https://arxiv.org/abs/2205.10803
"""

from __future__ import annotations

import math


# =============================================================================
# 余弦退火学习率调度（R34.md §3.4 + §7.2）
# =============================================================================


class CosineAnnealingLR:
    """余弦退火学习率调度器。

    公式: η(t) = η_min + 0.5 * (η_max - η_min) * (1 + cos(π * t / T))

    支持线性 warmup（前 warmup_steps 步线性增长到 η_max）。

    来源:
    - Loshchilov & Hutter, 2017, SGDR (Stochastic Gradient Descent with
      Warm Restarts), https://arxiv.org/abs/1608.03983

    Attributes:
        eta_max: 最大学习率。
        eta_min: 最小学习率。
        total_steps: 总训练步数（一个周期）。
        warmup_steps: warmup 步数（0=无 warmup）。
    """

    def __init__(
        self,
        eta_max: float = 3e-4,
        eta_min: float = 1e-6,
        total_steps: int = 1000,
        warmup_steps: int = 0,
    ) -> None:
        """初始化余弦退火调度器。

        Args:
            eta_max: 最大学习率（warmup 结束后的初始学习率）。
            eta_min: 最小学习率（退火结束值）。
            total_steps: 总训练步数。
            warmup_steps: warmup 步数（线性增长到 eta_max）。
        """
        if total_steps <= 0:
            raise ValueError(f"total_steps 须 > 0，得到 {total_steps}")
        if warmup_steps < 0:
            raise ValueError(f"warmup_steps 须 >= 0，得到 {warmup_steps}")
        if warmup_steps >= total_steps:
            raise ValueError(
                f"warmup_steps ({warmup_steps}) 须 < total_steps ({total_steps})"
            )
        self.eta_max = eta_max
        self.eta_min = eta_min
        self.total_steps = total_steps
        self.warmup_steps = warmup_steps

    def get_lr(self, step: int) -> float:
        """计算指定步数的学习率。

        Args:
            step: 当前步数（0-indexed）。

        Returns:
            当前学习率。
        """
        if step < 0:
            raise ValueError(f"step 须 >= 0，得到 {step}")
        # Warmup 阶段：线性增长
        if step < self.warmup_steps:
            return self.eta_max * (step + 1) / max(1, self.warmup_steps)
        # 余弦退火阶段
        progress = (step - self.warmup_steps) / max(
            1, self.total_steps - self.warmup_steps
        )
        progress = min(1.0, max(0.0, progress))
        return self.eta_min + 0.5 * (self.eta_max - self.eta_min) * (
            1.0 + math.cos(math.pi * progress)
        )


__all__ = [
    "CosineAnnealingLR",
]
