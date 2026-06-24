"""AI 训练框架（OptiLearn）子包。

负责 PPO 智能体（actor-critic + clip + GAE）、训练数据集合成
与训练主循环（采样→GNN→PPO→环境→奖励→更新）。
<<<<<<< HEAD

R34: AlphaChip 预训练-微调范式对齐（pretrain + transfer_learning）。
"""

# R34: AlphaChip 预训练-微调范式对齐
from polaris.trainer.pretrain import (
    ALL_PLATFORMS,
    CIRCUIT_TEMPLATES,
    PLATFORM_INP,
    PLATFORM_LNOI,
    PLATFORM_PHYSICAL_PARAMS,
    PLATFORM_SIN,
    PLATFORM_SOI,
    CheckpointManager,
    CosineAnnealingLR,
    DataAugmentor,
    EdgeTypePredictionTask,
    MaskedNodePredictionTask,
    PretrainDataset,
    PretrainSample,
)
from polaris.trainer.transfer_learning import (
    DEFAULT_CURRICULUM,
    CurriculumLevel,
    CurriculumScheduler,
    EWCConfig,
    EWCRegularizer,
    FineTuneConfig,
    FineTuner,
    FisherInformation,
    PlatformTransferLearner,
    SelfSupervisedConfig,
    SelfSupervisedPretrainer,
    TransferResult,
)

__all__ = [
    # R34 pretrain.py
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
    # R34 transfer_learning.py
    "CurriculumLevel",
    "CurriculumScheduler",
    "DEFAULT_CURRICULUM",
    "EWCConfig",
    "EWCRegularizer",
    "FineTuneConfig",
    "FineTuner",
    "FisherInformation",
    "PlatformTransferLearner",
    "SelfSupervisedConfig",
    "SelfSupervisedPretrainer",
    "TransferResult",
]
=======
"""
>>>>>>> trae/solo-agent-pkVjID
