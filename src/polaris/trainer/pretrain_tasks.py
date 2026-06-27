"""R34: AlphaChip 预训练-微调范式 — 自监督预训练任务。

从 pretrain.py 拆分（facade 模式，保持外部 import 路径不变）。

实现两个自监督预训练任务：
1. 掩码节点预测（GraphMAE 风格，MSE 损失）
2. 边类型预测（NetSense/R-GCN 风格，交叉熵损失）

纯 NumPy/CPU 实现（🚫不参与 GPU，R04 战略决策）。

来源:
- Hou et al., KDD 2022, GraphMAE: Self-supervised Masked Graph Autoencoders
  https://arxiv.org/abs/2205.10803
- R-GCN (Schlichtkrull et al., ESWC 2018) 关系预测
  https://arxiv.org/abs/1703.06103
- You et al., NeurIPS 2020, GraphCL 图对比学习
  https://arxiv.org/abs/2010.13902
- Mirhoseini et al., Nature 2021, AlphaChip 预训练范式
  https://www.nature.com/articles/s41586-021-03544-w
- Circuit Training Pre-training Guide
  https://github.com/google-research/circuit_training/blob/main/docs/PRETRAINING.md
"""

from __future__ import annotations

import numpy as np

# =============================================================================
# 自监督预训练任务（R34.md §7.4: 掩码节点预测 + 边类型预测）
# =============================================================================


class MaskedNodePredictionTask:
    """掩码节点预测自监督任务（GraphMAE 风格）。

    随机掩码部分节点特征，用 GNN 重建被掩码节点的特征。
    损失函数: MSE(预测特征, 原始特征)

    来源:
    - Hou et al., KDD 2022, GraphMAE: Self-supervised Masked Graph Autoencoders
      https://arxiv.org/abs/2205.10803

    Attributes:
        mask_ratio: 掩码比例（默认 0.15，与 GraphMAE/BERT 一致）。
        mask_value: 掩码填充值（默认 0.0）。
    """

    def __init__(self, mask_ratio: float = 0.15, mask_value: float = 0.0) -> None:
        """初始化掩码节点预测任务。

        Args:
            mask_ratio: 掩码比例（0-1）。
            mask_value: 掩码填充值。
        """
        if not 0.0 <= mask_ratio <= 1.0:
            raise ValueError(f"mask_ratio 须在 [0, 1]，得到 {mask_ratio}")
        self.mask_ratio = mask_ratio
        self.mask_value = mask_value

    def apply_mask(self, node_feats: np.ndarray, rng: np.random.Generator) -> tuple[
        np.ndarray,
        np.ndarray,
    ]:
        """对节点特征施加掩码。

        Args:
            node_feats: 节点特征 [N, D]。
            rng: 随机数生成器。

        Returns:
            (masked_feats, mask_indices) 元组。
            masked_feats: 掩码后的特征 [N, D]。
            mask_indices: 被掩码的节点索引数组。
        """
        n = node_feats.shape[0]
        n_mask = max(1, int(n * self.mask_ratio))
        mask_indices = rng.choice(n, size=n_mask, replace=False)
        masked_feats = node_feats.copy()
        masked_feats[mask_indices] = self.mask_value
        return masked_feats, mask_indices

    def compute_loss(
        self,
        predicted_feats: np.ndarray,
        original_feats: np.ndarray,
        mask_indices: np.ndarray,
    ) -> float:
        """计算掩码节点预测损失（MSE）。

        Args:
            predicted_feats: GNN 预测的节点特征 [N, D]。
            original_feats: 原始节点特征 [N, D]。
            mask_indices: 被掩码的节点索引。

        Returns:
            MSE 损失值。
        """
        if len(mask_indices) == 0:
            return 0.0
        pred = predicted_feats[mask_indices]
        target = original_feats[mask_indices]
        return float(np.mean((pred - target) ** 2))


class EdgeTypePredictionTask:
    """边类型预测自监督任务（NetSense 风格）。

    预测边的关系类型（光波导/电信号/控制信号）。
    损失函数: 交叉熵

    来源:
    - R-GCN (Schlichtkrull et al., ESWC 2018) 关系预测
      https://arxiv.org/abs/1703.06103
    - NetSense (Wang et al., 2018) 边类型预测

    Attributes:
        n_edge_types: 边类型数（默认 3: 光波导/电信号/控制信号）。
    """

    def __init__(self, n_edge_types: int = 3) -> None:
        """初始化边类型预测任务。

        Args:
            n_edge_types: 边类型数。
        """
        if n_edge_types <= 0:
            raise ValueError(f"n_edge_types 须 > 0，得到 {n_edge_types}")
        self.n_edge_types = n_edge_types

    def extract_labels(self, edge_feats: np.ndarray) -> np.ndarray:
        """从边特征提取关系类型标签。

        边特征最后 3 维为 net 关系 one-hot（与 build_photonic_edge_features 一致）。
        标签 = argmax(最后 3 维)。

        Args:
            edge_feats: 边特征 [E, D]（最后 3 维为关系 one-hot）。

        Returns:
            边类型标签 [E]。
        """
        if edge_feats.shape[0] == 0:
            return np.zeros(0, dtype=np.int64)
        relation_cols = edge_feats[:, -self.n_edge_types :]
        return np.argmax(relation_cols, axis=1)

    def compute_loss(
        self,
        predicted_logits: np.ndarray,
        labels: np.ndarray,
    ) -> float:
        """计算边类型预测损失（交叉熵）。

        Args:
            predicted_logits: 预测 logits [E, n_edge_types]。
            labels: 真实标签 [E]。

        Returns:
            交叉熵损失值。
        """
        if len(labels) == 0:
            return 0.0
        # 数值稳定的 softmax + 交叉熵
        shifted = predicted_logits - predicted_logits.max(axis=1, keepdims=True)
        exp = np.exp(shifted)
        probs = exp / exp.sum(axis=1, keepdims=True)
        n = len(labels)
        return float(-np.mean(np.log(probs[np.arange(n), labels] + 1e-12)))


__all__ = [
    "EdgeTypePredictionTask",
    "MaskedNodePredictionTask",
]
