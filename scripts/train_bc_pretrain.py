#!/usr/bin/env python3
"""Behavior Cloning 预训练入口脚本。

从 SiEPIC 真实 GDS 提取的专家示范数据集预训练 PPO 策略网络，
作为 RL 微调的初始化（避免冷启动，加速 PPO 收敛）。

流程:
1. 加载 data/expert_demos/ 专家示范数据集
2. 创建 PPOAgent（连续动作版，与 train_2m.py 兼容）
3. 调用 agent.pretrain() 进行 BC 预训练
4. 保存检查点到 checkpoints/bc_pretrain/

来源:
- Pomerleau, NeurIPS 1989, ALVINN
  https://papers.nips.cc/paper/95-alvinn-an-autonomous-land-vehicle-in-a-neural-network
- Ross & Bagnell, AISTATS 2011, DAgger
  https://arxiv.org/abs/1011.0686
- SiEPIC_EBeam_PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK (MIT, UBC)

用法:
    python scripts/train_bc_pretrain.py --epochs 50 --batch-size 16 --lr 1e-3
    python scripts/train_bc_pretrain.py --output checkpoints/bc_pretrain
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import numpy as np

# 确保 src/ 在 sys.path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

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
logger = logging.getLogger("train_bc")


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    p = argparse.ArgumentParser(description="Behavior Cloning 预训练")
    p.add_argument(
        "--data-dir",
        type=str,
        default="data/expert_demos",
        help="专家示范数据目录（默认 data/expert_demos）",
    )
    p.add_argument(
        "--output",
        type=str,
        default="checkpoints/bc_pretrain",
        help="检查点输出目录（默认 checkpoints/bc_pretrain）",
    )
    p.add_argument("--epochs", type=int, default=50, help="BC 训练轮数")
    p.add_argument("--batch-size", type=int, default=16, help="批量大小")
    p.add_argument("--lr", type=float, default=1e-3, help="学习率")
    p.add_argument("--hidden-dim", type=int, default=64, help="网络隐藏层维度")
    p.add_argument(
        "--loss-type",
        type=str,
        default="nll",
        choices=["nll", "mse"],
        help="BC 损失类型（nll 负对数似然 / mse 均方误差）",
    )
    p.add_argument("--grad-clip", type=float, default=1.0, help="梯度裁剪")
    p.add_argument("--log-every", type=int, default=10, help="日志打印间隔")
    p.add_argument("--seed", type=int, default=42, help="随机种子")
    return p.parse_args()


def main() -> int:
    """BC 预训练主入口。

    Returns:
        退出码（0 成功，非 0 失败）。
    """
    args = parse_args()
    np.random.seed(args.seed)

    # 1. 加载专家数据
    logger.info("加载专家示范数据: %s", args.data_dir)
    ds = ExpertDataset(args.data_dir)
    ds.load()
    n_samples = len(ds)
    if n_samples == 0:
        logger.error("专家数据集为空，无法训练")
        return 1
    obs_all, action_all = ds.get_all()
    logger.info(
        "专家数据: %d 样本, obs_dim=%d, action_dim=%d",
        n_samples,
        obs_all.shape[1],
        action_all.shape[1],
    )

    # 2. 创建 PPOAgent（连续动作版）
    config = PPOConfig(lr=args.lr)
    agent = PPOAgent(
        obs_dim=OBS_DIM,
        action_dim=ACTION_DIM,
        config=config,
        hidden_dim=args.hidden_dim,
    )
    logger.info(
        "PPOAgent 创建: obs_dim=%d, action_dim=%d, hidden=%d, lr=%s, loss=%s",
        OBS_DIM,
        ACTION_DIM,
        args.hidden_dim,
        args.lr,
        args.loss_type,
    )

    # 3. BC 预训练
    logger.info("开始 BC 预训练: %d epochs, batch=%d", args.epochs, args.batch_size)
    bc_config = BCConfig(
        n_epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        loss_type=args.loss_type,
        grad_clip=args.grad_clip,
        log_every=args.log_every,
    )
    history = agent.pretrain(obs_all, action_all, config=bc_config)
    final = history[-1]
    logger.info(
        "BC 预训练完成: loss=%.6f, mse=%.6f, nll=%.6f",
        final["loss"],
        final.get("mse", 0.0),
        final.get("nll", 0.0),
    )

    # 4. 保存检查点
    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)
    ckpt_path = out_dir / "bc_pretrain.json"
    agent.save(str(ckpt_path))
    logger.info("检查点已保存: %s", ckpt_path)

    # 5. 保存训练历史
    history_path = out_dir / "bc_history.json"
    history_path.write_text(
        json.dumps(
            {
                "config": {
                    "epochs": args.epochs,
                    "batch_size": args.batch_size,
                    "lr": args.lr,
                    "loss_type": args.loss_type,
                    "hidden_dim": args.hidden_dim,
                    "grad_clip": args.grad_clip,
                    "seed": args.seed,
                },
                "data": {
                    "data_dir": args.data_dir,
                    "n_samples": n_samples,
                    "obs_dim": OBS_DIM,
                    "action_dim": ACTION_DIM,
                },
                "final_metrics": final,
                "history": history,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    logger.info("训练历史已保存: %s", history_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
