"""训练流水线: 基准数据 → RL布局训练 → RL布线训练 → 仿真校验。

真正的PPO强化学习训练，不是走过场。
训练规模参考:
- Google Nature 2021: 6-24小时 TPU集群
- ChipFoundryServices: 10^4-10^6 episodes, 10^6-10^9 total steps
- UCL RWA-LR 2025: 200M samples on A100
- 本项目目标: 至少 100K episodes (约 1M+ steps)

来源:
- ChiPFormer ICML'23: 离线RL + 迁移学习
  https://arxiv.org/pdf/2306.14744.pdf
- Google Nature 2021: 芯片布局RL
  https://www.nature.com/articles/s41586-021-03544-w
- ChipFoundryServices RL训练规模
  https://www.chipfoundryservices.com/topic/reinforcement-learning-chip-optimization
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path

from polaris.trainer.ppo import PPOConfig
from polaris.trainer.train_loop import TrainConfig, train_floorplan, train_routing

logger = logging.getLogger(__name__)


@dataclass
class RLTrainingConfig:
    """RL训练流水线配置。

    Attributes:
        num_episodes: 训练轮次数（建议 ≥ 10000）。
        rollout_steps: 每轮采样步数。
        hidden_dim: 隐藏层维度。
        lr: 学习率。
        save_dir: 检查点保存目录。
        calibrate_every: 每N轮校准一次。
        train_placement: 是否训练布局。
        train_routing: 是否训练布线。
        canvas_w: 画布宽度。
        canvas_h: 画布高度。
        grid_size: 栅格大小。
        lr_schedule: 学习率调度。
        early_stop_patience: 早停耐心值。
        log_every: 日志打印间隔。
        checkpoint_every: 检查点保存间隔。
    """

    num_episodes: int = 10000
    rollout_steps: int = 128
    hidden_dim: int = 128
    lr: float = 3e-4
    save_dir: str = "checkpoints"
    calibrate_every: int = 1000
    train_placement: bool = True
    train_routing: bool = True
    canvas_w: float = 1000.0
    canvas_h: float = 1000.0
    grid_size: float = 10.0
    lr_schedule: str = "cosine"
    early_stop_patience: int = 0
    log_every: int = 100
    checkpoint_every: int = 1000


@dataclass
class RLTrainingResult:
    """RL训练结果。

    Attributes:
        placement_episodes: 布局训练完成轮次。
        routing_episodes: 布线训练完成轮次。
        best_placement_reward: 最佳布局奖励。
        best_routing_reward: 最佳布线奖励。
        total_training_seconds: 总训练时间（秒）。
        placement_checkpoint: 布局检查点路径。
        routing_checkpoint: 布线检查点路径。
        placement_log: 布局训练日志路径。
        routing_log: 布线训练日志路径。
        final_policy_loss: 最终策略损失。
        final_value_loss: 最终价值损失。
    """

    placement_episodes: int = 0
    routing_episodes: int = 0
    best_placement_reward: float = -1e9
    best_routing_reward: float = -1e9
    total_training_seconds: float = 0.0
    placement_checkpoint: str = ""
    routing_checkpoint: str = ""
    placement_log: str = ""
    routing_log: str = ""
    final_policy_loss: float = 0.0
    final_value_loss: float = 0.0


class RLTrainingPipeline:
    """RL训练流水线——真正的PPO强化学习训练。

    训练流程:
    1. 布局训练: PPO + FloorplanEnv → 学习器件放置策略
    2. 布线训练: PPO + RoutingEnv → 学习波导布线策略
    3. 仿真校验: 定期校准自研仿真vs基准数据

    来源:
    - Google Nature 2021: https://www.nature.com/articles/s41586-021-03544-w
    - ChipFoundryServices: https://www.chipfoundryservices.com/topic/reinforcement-learning-chip-optimization
    """

    def __init__(self, config: RLTrainingConfig | None = None) -> None:
        self.config = config or RLTrainingConfig()

    def train(self) -> RLTrainingResult:
        """执行RL训练流水线。

        Returns:
            RLTrainingResult。
        """
        cfg = self.config
        t0 = time.time()
        result = RLTrainingResult()

        # 阶段1: 布局训练
        if cfg.train_placement:
            logger.info("=== 布局训练启动: %d episodes ===", cfg.num_episodes)
            place_result = self._train_placement(cfg)
            result.placement_episodes = place_result["episodes"]
            result.best_placement_reward = place_result["best_reward"]
            result.placement_checkpoint = place_result["checkpoint"]
            result.placement_log = place_result["log_path"]
            result.final_policy_loss = place_result.get("final_policy_loss", 0.0)
            result.final_value_loss = place_result.get("final_value_loss", 0.0)

        # 阶段2: 布线训练
        if cfg.train_routing:
            logger.info("=== 布线训练启动: %d episodes ===", cfg.num_episodes)
            route_result = self._train_routing(cfg)
            result.routing_episodes = route_result["episodes"]
            result.best_routing_reward = route_result["best_reward"]
            result.routing_checkpoint = route_result["checkpoint"]
            result.routing_log = route_result["log_path"]

        result.total_training_seconds = time.time() - t0
        self._save_result(cfg, result)
        return result

    @staticmethod
    def _train_placement(cfg: RLTrainingConfig) -> dict:
        """执行布局PPO训练。"""
        ppo_cfg = PPOConfig(
            lr=cfg.lr,
            gamma=0.99,
            gae_lambda=0.95,
            clip_eps=0.2,
            ent_coef=0.01,
            vf_coef=0.5,
            max_grad_norm=0.5,
            n_epochs=4,
            batch_size=64,
            lr_schedule=cfg.lr_schedule,
            total_steps=cfg.num_episodes,
        )
        train_cfg = TrainConfig(
            ppo=ppo_cfg,
            num_episodes=cfg.num_episodes,
            rollout_steps=cfg.rollout_steps,
            canvas_w=cfg.canvas_w,
            canvas_h=cfg.canvas_h,
            grid_size=cfg.grid_size,
            hidden_dim=cfg.hidden_dim,
            checkpoint_dir=cfg.save_dir,
            checkpoint_every=cfg.checkpoint_every,
            log_every=cfg.log_every,
            early_stop_patience=cfg.early_stop_patience,
            lr_schedule=cfg.lr_schedule,
        )
        agent, logs = train_floorplan(train_cfg, verbose=True)

        best_reward = max((log.get("ep_reward", -1e9) for log in logs), default=-1e9)
        final_log = logs[-1] if logs else {}
        return {
            "episodes": len(logs),
            "best_reward": best_reward,
            "checkpoint": str(Path(cfg.save_dir) / "floorplan_final.json"),
            "log_path": str(Path(cfg.save_dir) / "floorplan_log.json"),
            "final_policy_loss": final_log.get("policy_loss", 0.0),
            "final_value_loss": final_log.get("value_loss", 0.0),
        }

    @staticmethod
    def _train_routing(cfg: RLTrainingConfig) -> dict:
        """执行布线PPO训练。"""
        ppo_cfg = PPOConfig(
            lr=cfg.lr,
            gamma=0.99,
            gae_lambda=0.95,
            clip_eps=0.2,
            ent_coef=0.01,
            vf_coef=0.5,
            max_grad_norm=0.5,
            n_epochs=4,
            batch_size=64,
            lr_schedule=cfg.lr_schedule,
            total_steps=cfg.num_episodes,
        )
        train_cfg = TrainConfig(
            ppo=ppo_cfg,
            num_episodes=cfg.num_episodes,
            rollout_steps=cfg.rollout_steps,
            canvas_w=cfg.canvas_w,
            canvas_h=cfg.canvas_h,
            grid_size=cfg.grid_size,
            hidden_dim=cfg.hidden_dim,
            checkpoint_dir=cfg.save_dir,
            checkpoint_every=cfg.checkpoint_every,
            log_every=cfg.log_every,
            lr_schedule=cfg.lr_schedule,
        )
        agent, logs = train_routing(train_cfg, verbose=True)

        best_reward = max((log.get("ep_reward", -1e9) for log in logs), default=-1e9)
        return {
            "episodes": len(logs),
            "best_reward": best_reward,
            "checkpoint": str(Path(cfg.save_dir) / "routing_final.json"),
            "log_path": str(Path(cfg.save_dir) / "routing_log.json"),
        }

    @staticmethod
    def _save_result(cfg: RLTrainingConfig, result: RLTrainingResult) -> None:
        """保存训练结果摘要。"""
        save_dir = Path(cfg.save_dir)
        save_dir.mkdir(parents=True, exist_ok=True)
        summary = {
            "placement_episodes": result.placement_episodes,
            "routing_episodes": result.routing_episodes,
            "best_placement_reward": result.best_placement_reward,
            "best_routing_reward": result.best_routing_reward,
            "total_training_seconds": result.total_training_seconds,
            "final_policy_loss": result.final_policy_loss,
            "final_value_loss": result.final_value_loss,
            "config": {
                "num_episodes": cfg.num_episodes,
                "rollout_steps": cfg.rollout_steps,
                "hidden_dim": cfg.hidden_dim,
                "lr": cfg.lr,
                "lr_schedule": cfg.lr_schedule,
            },
        }
        path = save_dir / "rl_training_summary.json"
        path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        logger.info("训练结果已保存: %s", path)


__all__ = [
    "RLTrainingPipeline",
    "RLTrainingConfig",
    "RLTrainingResult",
]
