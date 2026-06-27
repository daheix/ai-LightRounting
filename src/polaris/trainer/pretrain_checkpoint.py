"""R34: AlphaChip 预训练-微调范式 — Checkpoint 管理。

从 pretrain.py 拆分（facade 模式，保持外部 import 路径不变）。

实现 save_pretrained/load_pretrained 接口，支持 GNN-PPO 智能体的
checkpoint 保存与加载，用于预训练-微调范式。

纯 NumPy/CPU 实现（🚫不参与 GPU，R04 战略决策）。

来源:
- Mirhoseini et al., Nature 2021, AlphaChip checkpoint 发布
  https://www.nature.com/articles/s41586-021-03544-w
- Circuit Training Pre-trained Checkpoint
  https://github.com/google-research/circuit_training/?tab=readme-ov-file#PreTrainedModelCheckpoint
- Hugging Face Hub checkpoint 标准
  https://huggingface.co/
- Goldie et al., arXiv 2024, 预训练必要性辩护
  https://arxiv.org/abs/2411.10053
- Circuit Training Pre-training Guide
  https://github.com/google-research/circuit_training/blob/main/docs/PRETRAINING.md
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from polaris.trainer.pretrain_constants import (
    ALL_PLATFORMS,
    CIRCUIT_TEMPLATES,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Checkpoint 管理（R34.md §7.2: save_pretrained/load_pretrained）
# =============================================================================


class CheckpointManager:
    """预训练 checkpoint 管理器。

    实现 save_pretrained/load_pretrained 接口，支持 GNN-PPO 智能体的
    checkpoint 保存与加载，用于预训练-微调范式。

    来源:
    - Mirhoseini et al., Nature 2021, AlphaChip checkpoint 发布
      https://www.nature.com/articles/s41586-021-03544-w
    - Circuit Training Pre-trained Checkpoint
      https://github.com/google-research/circuit_training/?tab=readme-ov-file#PreTrainedModelCheckpoint
    - Hugging Face Hub checkpoint 标准
      https://huggingface.co/

    Attributes:
        checkpoint_dir: checkpoint 保存目录。
    """

    def __init__(self, checkpoint_dir: str | Path = "checkpoints") -> None:
        """初始化 checkpoint 管理器。

        Args:
            checkpoint_dir: checkpoint 保存目录。
        """
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def save_pretrained(
        self,
        agent,
        path: str | Path,
        metadata: dict | None = None,
    ) -> Path:
        """保存预训练 checkpoint。

        Args:
            agent: GNN-PPO 智能体（须有 save 方法）。
            path: checkpoint 文件路径。
            metadata: 额外元信息（平台/电路类型/训练步数等）。

        Returns:
            checkpoint 文件路径。
        """
        if not hasattr(agent, "save"):
            raise ValueError("agent 须实现 save 方法")
        ckpt_path = Path(path)
        ckpt_path.parent.mkdir(parents=True, exist_ok=True)
        # 调用 agent.save 保存 PPO + GNN 参数
        agent.save(ckpt_path)
        # 追加预训练元信息
        state = json.loads(ckpt_path.read_text(encoding="utf-8"))
        state["pretrain_metadata"] = {
            "version": "R34-v1.0",
            "platforms": list(ALL_PLATFORMS),
            "circuit_templates": list(CIRCUIT_TEMPLATES),
            "created_at": "2026-06-23",
            "source": "PoLaRIS R34 AlphaChip 预训练-微调对齐",
            "papers": [
                "Mirhoseini et al., Nature 2021",
                "Goldie et al., arXiv 2024",
            ],
            **(metadata or {}),
        }
        ckpt_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("预训练 checkpoint 已保存: %s", ckpt_path)
        return ckpt_path

    def load_pretrained(self, agent, path: str | Path) -> dict:
        """加载预训练 checkpoint。

        Args:
            agent: GNN-PPO 智能体（须有 load 方法）。
            path: checkpoint 文件路径。

        Returns:
            预训练元信息字典。
        """
        if not hasattr(agent, "load"):
            raise ValueError("agent 须实现 load 方法")
        ckpt_path = Path(path)
        if not ckpt_path.exists():
            raise FileNotFoundError(f"checkpoint 不存在: {ckpt_path}")
        agent.load(ckpt_path)
        state = json.loads(ckpt_path.read_text(encoding="utf-8"))
        metadata = state.get("pretrain_metadata", {})
        logger.info("预训练 checkpoint 已加载: %s", ckpt_path)
        return metadata

    def list_checkpoints(self) -> list[Path]:
        """列出所有 checkpoint 文件。

        Returns:
            checkpoint 文件路径列表（按修改时间排序）。
        """
        return sorted(
            self.checkpoint_dir.glob("*.json"),
            key=lambda p: p.stat().st_mtime,
        )


__all__ = [
    "CheckpointManager",
]
