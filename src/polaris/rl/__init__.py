"""强化学习（RL）子包。

R34-R35 路标：Google AlphaChip 强化学习布局对齐模块。

学术依据：
- Google DeepMind AlphaChip:
  https://deepmind.google/discover/blog/alphachip-a-new-approach-to-chip-layout/
- Mirhoseini et al., Nature 2024: https://doi.org/10.1038/s41586-024-07714-9
- R34 Edge-GNN: polaris.rl.edge_gnn（纯 NumPy CPU，对标 AlphaChip edge-based GNN）

参考文献：
[1] Mirhoseini A, Goldie A, Yazgan M, et al. A graph placement methodology for fast chip design[J]. Nature, 2021, 594(7862): 207-212. https://www.nature.com/articles/s41586-021-03544-w
[2] Mirhoseini A, Goldie A, Yazgan M, et al. Chip placement with deep reinforcement learning[J]. Nature, 2024, 626(7999): 55-62. https://doi.org/10.1038/s41586-024-07714-9
[3] Schulman J, Wolski F, Dhariwal P, et al. Proximal policy optimization algorithms[J]. arXiv preprint arXiv:1707.06347, 2017. https://arxiv.org/abs/1707.06347
[4] Basso A, et al. RL + R-GCN for analog IC layout-aware floorplanning[C]//NeurIPS 2025 Workshop on ML for Systems. 2025. https://mlforsystems.org/assets/papers/neurips2025/paper42.pdf
[5] Google Research. Circuit training: An open-source framework for chip placement with RL[CP/OL]. 2021. https://github.com/google-research/circuit_training
[6] Veličković P, Cucurull G, Casanova A, et al. Graph attention networks[C]//International Conference on Learning Representations (ICLR). 2018. https://arxiv.org/abs/1710.10903
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
