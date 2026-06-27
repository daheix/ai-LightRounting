"""R34: AlphaChip 预训练-微调范式对齐（pretrain.py）。

100% 复刻 Google AlphaChip 预训练-微调核心能力，并增加光电子创新：
1. 预训练数据集构建（100+ 电路变体，覆盖 SOI/SiN/InP/LNOI 四平台）
2. 数据增强（镜像/旋转 4× 扩充）
3. Checkpoint 管理（save_pretrained/load_pretrained）
4. 余弦退火学习率调度
5. 自监督预训练任务（掩码节点预测 + 边类型预测）

本文件为 facade（拆分自原 pretrain.py），实现细节移至子模块，外部 import 路径不变：
- polaris.trainer.pretrain_constants: 平台常量与物理参数表
- polaris.trainer.pretrain_dataset: PretrainSample + PretrainDataset
- polaris.trainer.pretrain_augment: DataAugmentor
- polaris.trainer.pretrain_scheduler: CosineAnnealingLR
- polaris.trainer.pretrain_checkpoint: CheckpointManager
- polaris.trainer.pretrain_tasks: MaskedNodePredictionTask + EdgeTypePredictionTask

纯 NumPy/CPU 实现（🚫不参与 GPU，R04 战略决策）。

来源:
- Mirhoseini et al., Nature 2021, AlphaChip 预训练范式
  https://www.nature.com/articles/s41586-021-03544-w
- Goldie et al., arXiv 2024, 预训练必要性辩护
  https://arxiv.org/abs/2411.10053
- Circuit Training Pre-training Guide
  https://github.com/google-research/circuit_training/blob/main/docs/PRETRAINING.md
- Loshchilov & Hutter, 2017, SGDR 余弦退火
  https://arxiv.org/abs/1608.03983
- Hou et al., KDD 2022, GraphMAE 自监督图预训练
  https://arxiv.org/abs/2205.10803
- You et al., NeurIPS 2020, GraphCL 图对比学习
  https://arxiv.org/abs/2010.13902
- SiEPIC EBeam PDK (SOI 平台参数)
  https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- Ligentec TriPleX (SiN 平台参数)
  https://www.ligentec.com/
- HyperLight (LNOI 平台参数)
  https://www.hyperlightcorp.com/
- InP 平台参数
  https://pattern-project.eu/technology/material-platforms/inp-platform/
"""

from __future__ import annotations

# Facade re-export：保持外部 `from polaris.trainer.pretrain import ...` 路径不变
from polaris.trainer.pretrain_augment import DataAugmentor  # noqa: F401
from polaris.trainer.pretrain_checkpoint import CheckpointManager  # noqa: F401
from polaris.trainer.pretrain_constants import (  # noqa: F401
    ALL_PLATFORMS,
    CIRCUIT_TEMPLATES,
    PLATFORM_INP,
    PLATFORM_LNOI,
    PLATFORM_PHYSICAL_PARAMS,
    PLATFORM_SIN,
    PLATFORM_SOI,
)
from polaris.trainer.pretrain_dataset import (  # noqa: F401
    PretrainDataset,
    PretrainSample,
)
from polaris.trainer.pretrain_scheduler import CosineAnnealingLR  # noqa: F401
from polaris.trainer.pretrain_tasks import (  # noqa: F401
    EdgeTypePredictionTask,
    MaskedNodePredictionTask,
)


__all__ = [
    "ALL_PLATFORMS",
    "CIRCUIT_TEMPLATES",
    "CheckpointManager",
    "CosineAnnealingLR",
    "DataAugmentor",
    "EdgeTypePredictionTask",
    "MaskedNodePredictionTask",
    "PLATFORM_INP",
    "PLATFORM_LNOI",
    "PLATFORM_PHYSICAL_PARAMS",
    "PLATFORM_SIN",
    "PLATFORM_SOI",
    "PretrainDataset",
    "PretrainSample",
]
