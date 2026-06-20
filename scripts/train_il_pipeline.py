#!/usr/bin/env python3
"""模仿学习 + RL 微调 4 阶段流水线训练脚本。

完整训练流程:
1. **阶段1 BC 预训练**: 用 SiEPIC 专家示范数据预训练 PPO 策略网络
2. **阶段2 PPO 小规模**: 在 small 级别变体（5-10 器件）上 RL 微调
3. **阶段3 PPO 中规模**: 在 medium 级别变体（20-50 器件）上 RL 微调
4. **阶段4 PPO 大规模**: 在 large 级别变体（80-120 器件）上 RL 微调

每个阶段加载上一阶段的检查点作为初始化，实现 Curriculum Learning。

**孤岛打通（roadmap 2.1.1）**：
- 孤岛#2 BC→真实RL：RL 微调阶段使用真实 ``FloorplanEnv`` + PPO rollout/update 循环
- 孤岛#1 BC→GNN-PPO：``--use-gnn`` 开关启用 GNN 状态编码器，RL 微调用
  ``GNNPPOAgent`` 联合训练 GNN + 策略网络（Basso et al. NeurIPS 2025 范式）

RL 循环实现拆分到 ``scripts/il_rl_loops.py``（规则 7.2）。

来源:
- Pomerleau, NeurIPS 1989, ALVINN (BC)
  https://papers.nips.cc/paper/95-alvinn-an-autonomous-land-vehicle-in-a-neural-network
- Bengio et al., "Curriculum Learning", ICML 2009
  https://dl.acm.org/doi/abs/10.1145/1553374.1553380
- Schulman et al., 2017, PPO https://arxiv.org/abs/1707.06347
- Basso et al., NeurIPS 2025, R-GCN routing-aware floorplanning RL
  https://mlforsystems.org/assets/papers/neurips2025/paper42.pdf
- SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK (MIT, UBC)
- LiDAR Benchmark: https://github.com/ScopeX-ASU/LiDAR (MIT, ISPD 2025)

用法:
    # 完整 4 阶段流水线
    python scripts/train_il_pipeline.py --output checkpoints/il_pipeline

    # 仅 BC 预训练阶段
    python scripts/train_il_pipeline.py --stage bc-only --output checkpoints/il_pipeline

    # 启用 GNN-PPO（孤岛#1 打通）
    python scripts/train_il_pipeline.py --use-gnn --output checkpoints/il_pipeline

    # 自定义各阶段轮数
    python scripts/train_il_pipeline.py \\
        --bc-epochs 50 --small-episodes 500 --medium-episodes 1000 --large-episodes 2000
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

# 确保 src/ 在 sys.path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

# RL 循环函数从 il_rl_loops 导入（规则 7.2 拆分）
from il_rl_loops import (  # noqa: E402
    _select_lidar_benchmark,
    run_gnn_rl_loop,
    run_real_rl_loop,
)

from polaris.data.variant_generator import CURRICULUM_LEVELS, CurriculumLevel  # noqa: E402
from polaris.trainer.bc import BCConfig  # noqa: E402
from polaris.trainer.expert_dataset import (  # noqa: E402
    ACTION_DIM,
    OBS_DIM,
    ExpertDataset,
)
from polaris.trainer.ppo_buffers import PPOConfig  # noqa: E402
from polaris.trainer.ppo_torch import PPOAgent  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("il_pipeline")


@dataclass
class PipelineConfig:
    """4 阶段流水线配置。

    Attributes:
        bc_epochs: BC 预训练轮数。
        small_episodes: small 级别 RL 微调轮次数。
        medium_episodes: medium 级别 RL 微调轮次数。
        large_episodes: large 级别 RL 微调轮次数。
        hidden_dim: 网络隐藏层维度。
        lr: 学习率。
        batch_size: BC 批量大小。
        output_dir: 输出目录。
        expert_data_dir: 专家示范数据目录。
        seed: 随机种子。
        use_gnn: 启用 GNN-PPO（孤岛#1 打通）。
        gnn_out_dim: GNN 状态编码器输出维度。
    """

    bc_epochs: int = 50
    small_episodes: int = 500
    medium_episodes: int = 1000
    large_episodes: int = 2000
    hidden_dim: int = 64
    lr: float = 3e-4
    batch_size: int = 16
    output_dir: str = "checkpoints/il_pipeline"
    expert_data_dir: str = "data/expert_demos"
    seed: int = 42
    use_gnn: bool = False
    gnn_out_dim: int = 64


@dataclass
class StageResult:
    """单阶段训练结果。

    Attributes:
        stage_name: 阶段名称。
        episodes: 完成的轮次数。
        final_loss: 最终损失。
        final_reward: 最终奖励（RL 阶段）。
        checkpoint_path: 检查点路径。
    """

    stage_name: str
    episodes: int = 0
    final_loss: float = 0.0
    final_reward: float = 0.0
    checkpoint_path: str = ""


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    p = argparse.ArgumentParser(description="PoLaRIS 模仿学习 + RL 微调 4 阶段流水线")
    p.add_argument(
        "--stage",
        type=str,
        default="all",
        choices=["all", "bc-only", "bc-small", "bc-small-medium"],
        help="训练阶段: all=全部4阶段, bc-only=仅BC, bc-small=BC+小规模, bc-small-medium=BC+小+中",
    )
    p.add_argument("--bc-epochs", type=int, default=50, help="BC 预训练轮数")
    p.add_argument("--small-episodes", type=int, default=500, help="small 级别 RL 轮次")
    p.add_argument("--medium-episodes", type=int, default=1000, help="medium 级别 RL 轮次")
    p.add_argument("--large-episodes", type=int, default=2000, help="large 级别 RL 轮次")
    p.add_argument("--hidden-dim", type=int, default=64, help="网络隐藏层维度")
    p.add_argument("--lr", type=float, default=3e-4, help="学习率")
    p.add_argument("--batch-size", type=int, default=16, help="BC 批量大小")
    p.add_argument("--output", type=str, default="checkpoints/il_pipeline", help="输出目录")
    p.add_argument(
        "--expert-data",
        type=str,
        default="data/expert_demos",
        help="专家示范数据目录",
    )
    p.add_argument("--seed", type=int, default=42, help="随机种子")
    p.add_argument(
        "--use-gnn",
        action="store_true",
        default=False,
        help="启用 GNN-PPO（孤岛#1 打通，Basso 2025 R-GCN 范式）",
    )
    p.add_argument(
        "--gnn-out-dim",
        type=int,
        default=64,
        help="GNN 状态编码器输出维度（--use-gnn 时生效）",
    )
    return p.parse_args()


def args_to_config(args: argparse.Namespace) -> PipelineConfig:
    """将命令行参数转换为 PipelineConfig。"""
    return PipelineConfig(
        bc_epochs=args.bc_epochs,
        small_episodes=args.small_episodes,
        medium_episodes=args.medium_episodes,
        large_episodes=args.large_episodes,
        hidden_dim=args.hidden_dim,
        lr=args.lr,
        batch_size=args.batch_size,
        output_dir=args.output,
        expert_data_dir=args.expert_data,
        seed=args.seed,
        use_gnn=args.use_gnn,
        gnn_out_dim=args.gnn_out_dim,
    )


def run_bc_pretrain(cfg: PipelineConfig) -> tuple[PPOAgent, StageResult]:
    """阶段1: BC 预训练。

    用 SiEPIC 专家示范数据预训练 PPO 策略网络。

    Args:
        cfg: 流水线配置。

    Returns:
        (预训练后的 PPOAgent, 阶段结果)。
    """
    logger.info("=" * 60)
    logger.info("阶段1: Behavior Cloning 预训练")
    logger.info("=" * 60)
    ds = ExpertDataset(cfg.expert_data_dir)
    ds.load()
    n_samples = len(ds)
    if n_samples == 0:
        logger.error("专家数据集为空，无法 BC 预训练")
        return _create_empty_agent(cfg), StageResult("bc", 0, 0.0, 0.0, "")
    agent, history = _train_bc_agent(ds, cfg)
    return _save_bc_checkpoint(agent, cfg, history)


def _create_empty_agent(cfg: PipelineConfig) -> PPOAgent:
    """创建空 agent（数据集为空时的兜底）。"""
    return PPOAgent(
        obs_dim=OBS_DIM,
        action_dim=ACTION_DIM,
        config=PPOConfig(lr=cfg.lr),
        hidden_dim=cfg.hidden_dim,
    )


def _train_bc_agent(ds: ExpertDataset, cfg: PipelineConfig) -> tuple[PPOAgent, list[dict]]:
    """用专家数据训练 BC agent。

    Returns:
        (训练后的 agent, BC 训练指标历史)。
    """
    obs_all, action_all = ds.get_all()
    n_samples = len(obs_all)
    logger.info("专家数据: %d 样本, obs_dim=%d, action_dim=%d", n_samples, OBS_DIM, ACTION_DIM)
    agent = PPOAgent(
        obs_dim=OBS_DIM,
        action_dim=ACTION_DIM,
        config=PPOConfig(lr=cfg.lr),
        hidden_dim=cfg.hidden_dim,
    )
    bc_config = BCConfig(
        n_epochs=cfg.bc_epochs,
        batch_size=cfg.batch_size,
        lr=cfg.lr,
        loss_type="nll",
        log_every=max(1, cfg.bc_epochs // 5),
    )
    history = agent.pretrain(obs_all, action_all, config=bc_config)
    return agent, history


def _save_bc_checkpoint(
    agent: PPOAgent,
    cfg: PipelineConfig,
    history: list[dict],
) -> tuple[PPOAgent, StageResult]:
    """保存 BC 检查点并返回结果。

    Args:
        agent: 训练后的 agent。
        cfg: 流水线配置。
        history: BC 训练指标历史（来自 ``agent.pretrain()`` 返回值）。
    """
    final = history[-1] if history else {"loss": 0.0, "mse": 0.0, "nll": 0.0}
    out_dir = Path(cfg.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ckpt_path = out_dir / "bc_pretrain.json"
    agent.save(str(ckpt_path))
    logger.info(
        "BC 预训练完成: loss=%.6f → %s",
        final.get("loss", 0.0),
        ckpt_path,
    )
    return agent, StageResult("bc", cfg.bc_epochs, final.get("loss", 0.0), 0.0, str(ckpt_path))


def run_rl_finetune(
    agent: PPOAgent,
    level: CurriculumLevel,
    n_episodes: int,
    cfg: PipelineConfig,
    stage_name: str,
) -> StageResult:
    """RL 微调阶段（Curriculum Learning 单级别，真实 FloorplanEnv）。

    在 LiDAR 公开 benchmark 上用真实 ``FloorplanEnv`` + PPO 训练循环微调，
    打通 BC→真实 RL 链路（roadmap 2.1.1 孤岛 #2）。
    ``--use-gnn`` 时用 GNN-PPO 联合训练（孤岛#1）。

    Args:
        agent: 待微调的 PPOAgent（已加载 BC 预训练权重）。
        level: 课程级别。
        n_episodes: RL 微调轮次数。
        cfg: 流水线配置。
        stage_name: 阶段名称。

    Returns:
        阶段结果。
    """
    logger.info("=" * 60)
    logger.info(
        "阶段: %s RL 微调 (%s 级别, %d-%d 器件, %d episodes)",
        stage_name,
        level.name,
        level.n_devices_min,
        level.n_devices_max,
        n_episodes,
    )
    logger.info("=" * 60)
    benchmark_path = _select_lidar_benchmark(level)
    if benchmark_path is None:
        logger.warning("未找到匹配 %s 级别的 LiDAR benchmark，跳过", level.name)
        return StageResult(stage_name, 0, 0.0, 0.0, "")
    logger.info("使用 LiDAR benchmark: %s", benchmark_path)
    avg_reward = _dispatch_rl_loop(agent, benchmark_path, n_episodes, cfg)
    return _save_rl_checkpoint(agent, avg_reward, n_episodes, stage_name, cfg)


def _dispatch_rl_loop(
    agent: PPOAgent,
    benchmark_path: str,
    n_episodes: int,
    cfg: PipelineConfig,
) -> float:
    """根据 use_gnn 分发到对应 RL 循环。"""
    if cfg.use_gnn:
        return run_gnn_rl_loop(agent, benchmark_path, n_episodes, cfg)
    return run_real_rl_loop(agent, benchmark_path, n_episodes, cfg.seed)


def _save_rl_checkpoint(
    agent: PPOAgent,
    avg_reward: float,
    n_episodes: int,
    stage_name: str,
    cfg: PipelineConfig,
) -> StageResult:
    """保存 RL 检查点并返回结果。"""
    out_dir = Path(cfg.output_dir)
    ckpt_path = out_dir / f"{stage_name}_finetune.json"
    agent.save(str(ckpt_path))
    logger.info("%s RL 微调完成: avg_reward=%.4f → %s", stage_name, avg_reward, ckpt_path)
    return StageResult(stage_name, n_episodes, 0.0, avg_reward, str(ckpt_path))


def save_pipeline_summary(
    results: list[StageResult],
    cfg: PipelineConfig,
    output_dir: Path,
) -> None:
    """保存流水线汇总报告。"""
    summary = {
        "config": {
            "bc_epochs": cfg.bc_epochs,
            "small_episodes": cfg.small_episodes,
            "medium_episodes": cfg.medium_episodes,
            "large_episodes": cfg.large_episodes,
            "hidden_dim": cfg.hidden_dim,
            "lr": cfg.lr,
            "use_gnn": cfg.use_gnn,
        },
        "stages": [
            {
                "name": r.stage_name,
                "episodes": r.episodes,
                "final_loss": r.final_loss,
                "final_reward": r.final_reward,
                "checkpoint": r.checkpoint_path,
            }
            for r in results
        ],
    }
    summary_path = output_dir / "pipeline_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("流水线汇总已保存: %s", summary_path)


def _find_level(name: str) -> CurriculumLevel | None:
    """按名称查找课程级别。"""
    for lv in CURRICULUM_LEVELS:
        if lv.name == name:
            return lv
    return None


# 课程级别 → (level_name, episodes_field) 映射
STAGE_MAP = [
    ("small", "small_episodes", ("all", "bc-small", "bc-small-medium")),
    ("medium", "medium_episodes", ("all", "bc-small-medium")),
    ("large", "large_episodes", ("all",)),
]


def main() -> int:
    """4 阶段流水线主入口。

    Returns:
        退出码（0 成功，非 0 失败）。
    """
    args = parse_args()
    np.random.seed(args.seed)
    cfg = args_to_config(args)
    output_dir = Path(cfg.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    results: list[StageResult] = []
    agent, bc_result = run_bc_pretrain(cfg)
    results.append(bc_result)
    for level_name, episodes_field, valid_stages in STAGE_MAP:
        if args.stage not in valid_stages:
            continue
        level = _find_level(level_name)
        if level is None:
            continue
        n_episodes = getattr(cfg, episodes_field)
        if n_episodes <= 0:
            continue
        results.append(run_rl_finetune(agent, level, n_episodes, cfg, level_name))
    save_pipeline_summary(results, cfg, output_dir)
    _log_final_summary(results)
    return 0


def _log_final_summary(results: list[StageResult]) -> None:
    """打印最终汇总日志。"""
    logger.info("=" * 60)
    logger.info("4 阶段流水线训练完成！")
    for r in results:
        logger.info(
            "  %s: %d episodes, loss=%.4f, reward=%.4f",
            r.stage_name,
            r.episodes,
            r.final_loss,
            r.final_reward,
        )
    logger.info("=" * 60)


if __name__ == "__main__":
    sys.exit(main())
