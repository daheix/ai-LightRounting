"""强化学习（RL）子包。

R34-R35 路标：Google AlphaChip 强化学习布局对齐模块。

学术依据：
- Google DeepMind AlphaChip:
  https://deepmind.google/discover/blog/alphachip-a-new-approach-to-chip-layout/
- Mirhoseini et al., Nature 2024: https://doi.org/10.1038/s41586-024-07714-9
"""

from polaris.rl.alpha_chip import (
    AlphaChipAgent,
    AlphaChipConfig,
    AlphaChipTrainer,
    PhotonicPlacementEncoder,
    PhotonicPlacementReward,
)

__all__ = [
    "AlphaChipConfig",
    "PhotonicPlacementEncoder",
    "PhotonicPlacementReward",
    "AlphaChipAgent",
    "AlphaChipTrainer",
]
