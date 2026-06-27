"""R34: AlphaChip 预训练-微调范式 — 课程学习调度器。

从 transfer_learning.py 拆分（facade 模式，保持外部 import 路径不变）。

实现课程学习调度器，按器件数从少到多排序训练任务，让模型逐步学习复杂布局。
默认课程：5→10→20→50→100 节点（R34.md §7.4 要求）。

纯 NumPy/CPU 实现（🚫不参与 GPU，R04 战略决策）。

来源:
- Bengio et al., ICML 2009, Curriculum Learning
  https://dl.acm.org/doi/abs/10.1145/1553374.1553380
- Kirkpatrick et al., 2017 PNAS, EWC
  https://www.pnas.org/doi/10.1073/pnas.1611835114
- Pan & Yang, 2010 IEEE TKDE, 迁移学习综述
  https://ieeexplore.ieee.org/document/5288526
- Mirhoseini et al., Nature 2021, AlphaChip 预训练-微调
  https://www.nature.com/articles/s41586-021-03544-w
- Hou et al., KDD 2022, GraphMAE 自监督图预训练
  https://arxiv.org/abs/2205.10803
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from polaris.trainer.pretrain import PretrainSample

logger = logging.getLogger(__name__)


# =============================================================================
# 课程学习调度器（R34.md §6.2 创新点 4: 课程学习）
# =============================================================================


@dataclass
class CurriculumLevel:
    """课程学习级别（Bengio et al., ICML 2009）。

    Attributes:
        name: 级别名称。
        n_devices_min: 器件数下限。
        n_devices_max: 器件数上限。
        n_epochs: 该级别训练轮数。
    """

    name: str
    n_devices_min: int
    n_devices_max: int
    n_epochs: int


# 默认课程：5→10→20→50→100 节点（R34.md §7.4 要求）
DEFAULT_CURRICULUM: list[CurriculumLevel] = [
    CurriculumLevel("L1_easy", 5, 10, 20),
    CurriculumLevel("L2_medium", 10, 20, 30),
    CurriculumLevel("L3_hard", 20, 50, 40),
    CurriculumLevel("L4_expert", 50, 100, 50),
]


class CurriculumScheduler:
    """课程学习调度器（由易到难渐进训练）。

    按器件数从少到多排序训练任务，让模型逐步学习复杂布局。

    来源:
    - Bengio et al., ICML 2009, Curriculum Learning
      https://dl.acm.org/doi/abs/10.1145/1553374.1553380

    Attributes:
        levels: 课程级别列表。
        current_level: 当前级别索引。
        current_epoch: 当前级别内已训练轮数。
    """

    def __init__(
        self,
        levels: list[CurriculumLevel] | None = None,
    ) -> None:
        """初始化课程学习调度器。

        Args:
            levels: 课程级别列表（None 用默认 5→100 课程）。

        Raises:
            ValueError: levels 为空列表。
        """
        if levels is None:
            self.levels = list(DEFAULT_CURRICULUM)
        else:
            if not levels:
                raise ValueError("课程级别列表不能为空")
            self.levels = list(levels)
        self.current_level = 0
        self.current_epoch = 0

    def get_current_samples(
        self,
        all_samples: list[PretrainSample],
    ) -> list[PretrainSample]:
        """获取当前级别的样本。

        Args:
            all_samples: 全部样本列表。

        Returns:
            当前级别器件数范围内的样本。
        """
        if self.current_level >= len(self.levels):
            return all_samples
        level = self.levels[self.current_level]
        return [
            s for s in all_samples
            if level.n_devices_min <= s.n_devices <= level.n_devices_max
        ]

    def step(self) -> bool:
        """训练一步，返回是否晋升到下一级别。

        Returns:
            True 表示已晋升到下一级别，False 表示仍在当前级别。
        """
        if self.current_level >= len(self.levels):
            return False
        self.current_epoch += 1
        level = self.levels[self.current_level]
        if self.current_epoch >= level.n_epochs:
            self.current_level += 1
            self.current_epoch = 0
            if self.current_level < len(self.levels):
                logger.info(
                    "课程学习晋升: %s → %s",
                    level.name,
                    self.levels[self.current_level].name,
                )
                return True
            logger.info("课程学习完成: 已通过全部 %d 级别", len(self.levels))
        return False

    def is_finished(self) -> bool:
        """课程学习是否完成。"""
        return self.current_level >= len(self.levels)

    def reset(self) -> None:
        """重置调度器到初始级别。"""
        self.current_level = 0
        self.current_epoch = 0


__all__ = [
    "DEFAULT_CURRICULUM",
    "CurriculumLevel",
    "CurriculumScheduler",
]
