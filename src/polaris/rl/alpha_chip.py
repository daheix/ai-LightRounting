"""R34-R35 路标：Google AlphaChip 强化学习布局对齐模块。

对标 Google DeepMind AlphaChip（强化学习芯片布局），将电子 IC 布局 RL
方法扩展到光子 IC 布局，实现 PoLaRIS 与 AlphaChip 的功能对齐。

## 模块组成

1. ``AlphaChipConfig`` — AlphaChip RL 布局配置（→ ``alpha_chip_config``）
2. ``PhotonicPlacementEncoder`` — 光子布局状态编码器（→ ``alpha_chip_encoder``）
3. ``PhotonicPlacementReward`` — 光子布局多目标奖励函数（→ ``alpha_chip_reward``）
4. ``AlphaChipAgent`` — AlphaChip 强化学习布局智能体（→ ``alpha_chip_agent``）
5. ``AlphaChipTrainer`` — AlphaChip 训练器（→ ``alpha_chip_trainer``）

## 文件拆分（facade 模式）

本文件为 facade，将原 1096 行单文件按功能拆分为 5 个子模块，保持外部
``from polaris.rl.alpha_chip import X`` 路径不变。各子模块：

- ``alpha_chip_config.py`` — 配置 dataclass + 光学/网格常量 + logger
- ``alpha_chip_encoder.py`` — 光子布局状态编码器
- ``alpha_chip_reward.py`` — 光子布局多目标奖励函数
- ``alpha_chip_agent.py`` — AlphaChip RL 布局智能体（Edge-GNN + PPO）
- ``alpha_chip_trainer.py`` — AlphaChip 训练器（PPO clip + GAE）

依赖链单向（config → encoder/reward → agent → trainer），无循环导入。

## 学术依据

- Google DeepMind AlphaChip:
  https://deepmind.google/discover/blog/alphachip-a-new-approach-to-chip-layout/
- Mirhoseini et al., Nature 2024, "AlphaChip":
  https://doi.org/10.1038/s41586-024-07714-9
- Mirhoseini et al., Nature 2021, "A graph placement methodology for fast chip design"
  DOI: 10.1038/s41586-021-03544-w
- Schulman et al., 2017, PPO: https://arxiv.org/abs/1707.06347
- Gilmer et al., 2017, MPNN（消息传递神经网络）: https://arxiv.org/abs/1704.01212
- DREAMPlace RUDY 拥塞估计: https://arxiv.org/abs/2004.10746
- Sutton & Barto, 2018, "Reinforcement Learning: An Introduction" §13（策略梯度）

## 【创新】光子布局扩展

AlphaChip 原为电子 IC 布局设计，本模块将其扩展到光子 IC 布局：
- 电子 IC 优化目标：线长 / 拥塞 / 面积
- 光子 IC 增加光学约束：波导交叉数 / 弯曲半径违反 / 波导长度均匀性（相位匹配）
- 创新逻辑：光子波导交叉引入插入损耗与串扰，弯曲半径过小引入辐射损耗，
  波导长度不均匀导致相位失配，故需在 AlphaChip 奖励函数中增加光学约束项。

## 架构统一（D05 Task 10）

复用 PoLaRIS 已有成熟实现，禁止自实现简化版（规则 R09 单文件版本升级、
R03 禁止 fall-back）：
- 图编码器：复用 ``polaris.engine.alphachip_gnn.AlphaChipEdgeGNN``
  （AlphaChip Edge-GNN + 多关系边变换 + GAT + GlobalAttention 读出），
  替代旧版自实现简化版 numpy GNN。
- 策略/价值训练：复用 ``polaris.trainer.ppo_torch.PPOAgent``（PPO clip + GAE），
  替代旧版自实现简化版 REINFORCE + baseline。
- 连续动作（归一化 x,y）经量化映射到离散网格位置，保留 ``select_action``
  返回网格索引的外部接口。
"""

from __future__ import annotations

from polaris.rl.alpha_chip_agent import AlphaChipAgent  # noqa: F401

# facade re-export：保持外部 `from polaris.rl.alpha_chip import X` 路径不变
from polaris.rl.alpha_chip_config import (  # noqa: F401
    _CANVAS_SIZE,
    _DEVICE_TYPES,
    _GRID_CELL_SIZE,
    _MIN_BEND_RADIUS,
    _NET_TYPES,
    AlphaChipConfig,
    logger,
)
from polaris.rl.alpha_chip_encoder import PhotonicPlacementEncoder  # noqa: F401
from polaris.rl.alpha_chip_reward import PhotonicPlacementReward  # noqa: F401
from polaris.rl.alpha_chip_trainer import AlphaChipTrainer  # noqa: F401

__all__ = [
    "AlphaChipConfig",
    "PhotonicPlacementEncoder",
    "PhotonicPlacementReward",
    "AlphaChipAgent",
    "AlphaChipTrainer",
]
