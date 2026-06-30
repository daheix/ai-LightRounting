"""强化学习（RL）子包。

R34-R35 路标：Google AlphaChip 强化学习布局对齐模块。

学术依据：
- Google DeepMind AlphaChip:
  https://deepmind.google/discover/blog/alphachip-a-new-approach-to-chip-layout/
- Mirhoseini et al., Nature 2024: https://doi.org/10.1038/s41586-024-07714-9
- R34 Edge-GNN: polaris.rl.edge_gnn（纯 NumPy CPU，对标 AlphaChip edge-based GNN）
"""

from polaris.rl.alpha_chip import (
    AlphaChipAgent,
    AlphaChipConfig,
    AlphaChipTrainer,
    PhotonicPlacementEncoder,
    PhotonicPlacementReward,
)
from polaris.rl.edge_gnn import EdgeGNN, EdgeGNNConfig

__all__ = [
    "AlphaChipConfig",
    "PhotonicPlacementEncoder",
    "PhotonicPlacementReward",
    "AlphaChipAgent",
    "AlphaChipTrainer",
    "EdgeGNN",
    "EdgeGNNConfig",
]
