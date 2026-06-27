"""R34-R35 路标：AlphaChip RL 布局配置与常量定义。

本模块从 ``alpha_chip.py`` 拆分而来（facade 模式），提供 AlphaChip
强化学习布局的全局配置 dataclass 与光学/网格常量。外部 import 路径
保持不变（``from polaris.rl.alpha_chip import AlphaChipConfig``）。

## 学术依据

- Google DeepMind AlphaChip:
  https://deepmind.google/discover/blog/alphachip-a-new-approach-to-chip-layout/
- Mirhoseini et al., Nature 2024, "AlphaChip":
  https://doi.org/10.1038/s41586-024-07714-9
- Mirhoseini et al., Nature 2021, "A graph placement methodology for fast
  chip design" DOI: 10.1038/s41586-021-03544-w
- Schulman et al., 2017, PPO: https://arxiv.org/abs/1707.06347
- Gilmer et al., 2017, MPNN: https://arxiv.org/abs/1704.01212
- Sutton & Barto, 2018, "Reinforcement Learning: An Introduction" §13

## 来源

- 拆分自: ``src/polaris/rl/alpha_chip.py``（原文件 1096 行 → 拆分后 ≤800 行）
- 路标: R34-R35
- 架构统一: D05 Task 10
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

# 光学约束参数（来源: SiEPIC EBeam PDK 标准值 + LiDAR ISPD'25 光学约束）
_MIN_BEND_RADIUS = 20.0  # 最小弯曲半径（μm），低于此值波导辐射损耗显著
_GRID_CELL_SIZE = 100.0  # 网格单元物理尺寸（μm）
_CANVAS_SIZE = 3200.0  # 画布物理尺寸（μm），对应 32×32 网格

# 器件类型映射（来源: PoLaRIS PDK catalog 标准器件类型）
_DEVICE_TYPES = {"mzi": 0, "ring": 1, "mmi": 2, "coupler": 3}
# 连接类型映射（来源: 光子电路网表标准连接类型）
_NET_TYPES = {"waveguide": 0, "crossing": 1, "bend": 2}

logger = logging.getLogger(__name__)


@dataclass
class AlphaChipConfig:
    """AlphaChip RL 布局配置。

    学术依据：Google DeepMind AlphaChip
    URL: https://deepmind.google/discover/blog/alphachip-a-new-approach-to-chip-layout/
    Nature 2024: https://doi.org/10.1038/s41586-024-07714-9

    Mirhoseini 2021 Nature: "A graph placement methodology for fast chip design"
    DOI: 10.1038/s41586-021-03544-w

    Attributes:
        grid_size: 布局网格 (grid_h, grid_w)。
        n_episodes: 训练轮数。
        learning_rate: 学习率。
        gnn_hidden: GNN 隐藏层维度。
        gnn_layers: GNN 层数。
        use_attention: 是否使用注意力机制。
        gamma: 折扣因子（来源: Sutton & Barto 2018 §13 默认值）。
    """

    grid_size: tuple = (32, 32)
    n_episodes: int = 10000
    learning_rate: float = 1e-4
    gnn_hidden: int = 128
    gnn_layers: int = 3
    use_attention: bool = True
    gamma: float = 0.99


__all__ = [
    "AlphaChipConfig",
    "_MIN_BEND_RADIUS",
    "_GRID_CELL_SIZE",
    "_CANVAS_SIZE",
    "_DEVICE_TYPES",
    "_NET_TYPES",
    "logger",
]
