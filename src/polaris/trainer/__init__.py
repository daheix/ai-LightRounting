"""AI 训练框架（OptiLearn）子包。

负责 PPO 智能体（actor-critic + clip + GAE）、训练数据集合成
与训练主循环（采样→GNN→PPO→环境→奖励→更新）。

R34: AlphaChip 预训练-微调范式对齐（pretrain + transfer_learning）。

参考文献：
[1] Schulman J, Wolski F, Dhariwal P, et al. Proximal policy optimization algorithms[J]. arXiv preprint arXiv:1707.06347, 2017. https://arxiv.org/abs/1707.06347
[2] Schulman J, Moritz P, Levine S, et al. High-dimensional continuous control using generalized advantage estimation[J]. arXiv preprint arXiv:1506.02438, 2015. https://arxiv.org/abs/1506.02438
[3] Mirhoseini A, Goldie A, Yazgan M, et al. A graph placement methodology for fast chip design[J]. Nature, 2021, 594(7862): 207-212. https://www.nature.com/articles/s41586-021-03544-w
[4] Bengio Y, Louradour J, Collobert R, et al. Curriculum learning[C]//International Conference on Machine Learning (ICML). 2009: 41-48. https://api.digie.ai/publications/Curriculum_learning-Bengio.pdf
[5] Kirkpatrick J, Pascanu R, Rabinowitz N, et al. Overcoming catastrophic forgetting in neural networks[J]. Proceedings of the National Academy of Sciences, 2017, 114(13): 3521-3526. https://doi.org/10.1073/pnas.1611835114
[6] He K, Zhang X, Ren S, et al. Deep residual learning for image recognition[C]//IEEE Conference on Computer Vision and Pattern Recognition (CVPR). 2016: 770-778. https://arxiv.org/abs/1512.03385
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
