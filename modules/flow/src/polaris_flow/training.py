"""训练流水线: 基准数据 → 变体生成 → RL训练 → 仿真校验。

R390 清理: TrainingPipeline.__init__ 始终 raise ImportError（依赖
polaris_orchestrator 的 IntegratedPipeline/PipelineConfig，v5.0 未迁移），
因此原 train()/_train_floorplan_agent/_train_routing_agent/_build_train_config/
_extract_best_reward/_extract_avg_loss/_run_calibration/_save_checkpoint/
_load_benchmarks 及 13 个 _parse_* 辅助函数均为死代码（~480 行）。
保留 TrainingConfig/TrainingResult 数据类与 TrainingPipeline 桩（__init__ raise）。

来源:
- ChiPFormer ICML'23: 离线RL + 迁移学习
  https://arxiv.org/pdf/2306.14744.pdf
- PPO 标准训练循环: UC Berkeley Scalable AI Lecture 15 (2026)
  https://scalable-ai.eecs.berkeley.edu/assets/lecture_slides/lecture_15.pdf
- CleanRL ppo.py 单文件训练循环
  https://github.com/vwxyzjn/cleanrl
- DREAMPlace (解析法布局基准，训练评估对标), Lin et al., TCAD 2020
  https://arxiv.org/abs/2004.10746
- OpenROAD 开源 EDA 训练基准流水线
  https://theopenroadproject.org/
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # 类型注解仅用于静态检查，运行时不解析（PEP 563 `from __future__ import annotations`）
    from polaris_nn.data.variant_generator import VariantConfig

logger = logging.getLogger(__name__)


@dataclass
class TrainingConfig:
    """训练流水线配置。

    Attributes:
        benchmark_dir: 基准数据目录。
        variant_config: 变体生成配置（None 表示不生成变体，仅用基准数据）。
        pipeline_config: 一体化流水线配置（用于最终验证）。
        num_episodes: 训练轮次数。
        hidden_dim: 隐藏层维度。
        lr: 学习率。
        save_dir: 检查点保存目录。
        calibrate_every: 每N轮校准一次。
        train_floorplan_enabled: 是否训练布局 agent。
        train_routing_enabled: 是否训练布线 agent。
        rollout_steps: 每轮采样步数。
        canvas_w: 画布宽（μm）。
        canvas_h: 画布高（μm）。
        grid_size: 栅格大小（μm）。
        sim_feedback: 是否启用 SimLoop 约束反馈。
        seed: 随机种子。
    """

    benchmark_dir: str = "data/benchmarks"
    variant_config: VariantConfig | None = None
    pipeline_config: object | None = None  # PipelineConfig（v5.0 未迁移）
    num_episodes: int = 50
    hidden_dim: int = 64
    lr: float = 3e-4
    save_dir: str = "checkpoints"
    calibrate_every: int = 10
    train_floorplan_enabled: bool = True
    train_routing_enabled: bool = True
    rollout_steps: int = 64
    canvas_w: float = 1000.0
    canvas_h: float = 1000.0
    grid_size: float = 10.0
    sim_feedback: bool = False
    seed: int = 42


@dataclass
class TrainingResult:
    """训练结果。

    Attributes:
        episodes_completed: 完成的训练轮次。
        best_reward: 最佳奖励（布局与布线中的最大值）。
        avg_loss_db: 平均插入损耗。
        calibration_passed: 校准是否通过。
        calibration_result: 校准详细结果。
        checkpoint_path: 检查点路径。
        floorplan_logs: 布局训练日志。
        routing_logs: 布线训练日志。
    """

    episodes_completed: int = 0
    best_reward: float = 0.0
    avg_loss_db: float = 0.0
    calibration_passed: bool = False
    calibration_result: object | None = None  # CalibrationResult（v5.0 未迁移）
    checkpoint_path: str = ""
    floorplan_logs: list[dict] = field(default_factory=list)
    routing_logs: list[dict] = field(default_factory=list)


class TrainingPipeline:
    """训练流水线桩（stub）。

    R390 清理: 原实现依赖 polaris_orchestrator.IntegratedPipeline 和
    PipelineConfig（v5.0 未迁移），__init__ 始终 raise ImportError。
    原 ~480 行方法（train/_train_*/_load_benchmarks/_save_checkpoint 等）
    全部为不可达死代码，已删除。保留桩类供 __all__ 导出兼容。

    迁移指南: 改用 polaris_trainer.train_loop.train_ppo / train_with_env_factory
    直接训练，或迁移 IntegratedPipeline 后恢复完整实现。
    """

    def __init__(self, config: TrainingConfig | None = None) -> None:
        self.config = config or TrainingConfig()
        raise ImportError(
            "TrainingPipeline 需要 polaris_orchestrator 子模块提供 IntegratedPipeline"
            "（v5.0 polaris_orchestrator 未迁移 IntegratedPipeline/PipelineConfig，"
            "R03 禁止 fall-back）。请改用 polaris_trainer.train_loop.train_ppo / "
            "train_with_env_factory 直接训练。"
        )


__all__ = [
    "TrainingPipeline",
    "TrainingConfig",
    "TrainingResult",
]
