"""R34: AlphaChip 预训练-微调范式对齐（transfer_learning.py）。

实现多平台迁移学习、EWC 防遗忘、课程学习与微调接口：
1. Fisher 信息矩阵计算（EWC 核心组件）
2. EWC 正则化器（防止灾难性遗忘）
3. 课程学习调度器（5→100 节点渐进训练）
4. 多平台迁移学习器（SOI→SiN/InP/LNOI）
5. 自监督预训练器（掩码节点预测 + 边类型预测）
6. 微调器（加载 checkpoint 后继续训练）

本文件为 facade（拆分自原 transfer_learning.py），实现细节移至子模块，外部 import 路径不变：
- polaris.trainer.transfer_learning_ewc: FisherInformation + EWCConfig + EWCRegularizer
- polaris.trainer.transfer_learning_curriculum: CurriculumLevel + DEFAULT_CURRICULUM + CurriculumScheduler
- polaris.trainer.transfer_learning_platform: TransferResult + PlatformTransferLearner
- polaris.trainer.transfer_learning_selfsupervised: SelfSupervisedConfig + SelfSupervisedPretrainer
- polaris.trainer.transfer_learning_finetune: FineTuneConfig + FineTuner

纯 NumPy/CPU 实现（🚫不参与 GPU，R04 战略决策）。

来源:
- Kirkpatrick et al., 2017 PNAS, EWC (Elastic Weight Consolidation)
  https://www.pnas.org/doi/10.1073/pnas.1611835114
- Pan & Yang, 2010 IEEE TKDE, 迁移学习综述
  https://ieeexplore.ieee.org/document/5288526
- Bengio et al., ICML 2009, Curriculum Learning
  https://dl.acm.org/doi/abs/10.1145/1553374.1553380
- Mirhoseini et al., Nature 2021, AlphaChip 预训练-微调
  https://www.nature.com/articles/s41586-021-03544-w
- Hou et al., KDD 2022, GraphMAE 自监督图预训练
  https://arxiv.org/abs/2205.10803
"""

from __future__ import annotations

# Facade re-export：保持外部 `from polaris.trainer.transfer_learning import ...` 路径不变
from polaris.trainer.transfer_learning_curriculum import (  # noqa: F401
    DEFAULT_CURRICULUM,
    CurriculumLevel,
    CurriculumScheduler,
)
from polaris.trainer.transfer_learning_ewc import (  # noqa: F401
    EWCConfig,
    EWCRegularizer,
    FisherInformation,
)
from polaris.trainer.transfer_learning_finetune import (  # noqa: F401
    FineTuneConfig,
    FineTuner,
)
from polaris.trainer.transfer_learning_platform import (  # noqa: F401
    PlatformTransferLearner,
    TransferResult,
)
from polaris.trainer.transfer_learning_selfsupervised import (  # noqa: F401
    SelfSupervisedConfig,
    SelfSupervisedPretrainer,
)

__all__ = [
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
