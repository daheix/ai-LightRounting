"""R34: AlphaChip 预训练-微调范式 — EWC 防遗忘（Fisher + EWC 正则化器）。

从 transfer_learning.py 拆分（facade 模式，保持外部 import 路径不变）。

实现 EWC（Elastic Weight Consolidation）防灾难性遗忘：
1. Fisher 信息矩阵计算（参数梯度平方期望）
2. EWC 正则化器（对重要参数施加 L2 约束）

纯 NumPy/CPU 实现（🚫不参与 GPU，R04 战略决策）。

来源:
- Kirkpatrick et al., 2017 PNAS, EWC (Elastic Weight Consolidation)
  https://www.pnas.org/doi/10.1073/pnas.1611835114
- Fisher, 1925, 统计推断的 Fisher 信息
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

import numpy as np

from polaris.trainer.pretrain import PretrainSample

logger = logging.getLogger(__name__)


# =============================================================================
# Fisher 信息矩阵（EWC 核心组件，Kirkpatrick et al. 2017 PNAS）
# =============================================================================


class FisherInformation:
    """Fisher 信息矩阵计算器（EWC 核心组件）。

    Fisher 信息矩阵近似为参数梯度的平方期望：
    F_i = E[(∂log p(y|x,θ)/∂θ_i)²] ≈ (1/N) Σ_n (∂L_n/∂θ_i)²

    来源:
    - Kirkpatrick et al., 2017 PNAS, EWC
      https://www.pnas.org/doi/10.1073/pnas.1611835114
    - Fisher, 1925, 统计推断的 Fisher 信息

    Attributes:
        fisher: Fisher 信息矩阵（与参数同形状的列表）。
        params: 对应的参数快照（θ*）。
    """

    def __init__(self) -> None:
        """初始化 Fisher 信息矩阵计算器。"""
        self.fisher: list[np.ndarray] = []
        self.params: list[np.ndarray] = []

    def compute(
        self,
        agent,
        samples: list[PretrainSample],
        n_samples: int = 32,
    ) -> None:
        """计算 Fisher 信息矩阵。

        对每个样本计算损失对参数的梯度，平方后取平均。

        Args:
            agent: GNN-PPO 智能体（须有 parameters 方法）。
            samples: 预训练样本列表。
            n_samples: 采样样本数（Fisher 计算开销大，默认 32）。
        """
        if not samples:
            raise ValueError("samples 不能为空")
        if not hasattr(agent, "parameters"):
            raise ValueError("agent 须实现 parameters 方法")
        params = agent.parameters()
        n = min(n_samples, len(samples))
        # 初始化 Fisher 累加器
        fisher_sum = [np.zeros_like(p.data) for p in params]
        for i in range(n):
            sample = samples[i]
            # 清零梯度
            for p in params:
                p.grad = None
            # 计算损失梯度（用代理损失：节点特征重建）
            self._compute_sample_gradient(agent, sample)
            # 累加梯度平方
            for j, p in enumerate(params):
                if p.grad is not None:
                    fisher_sum[j] += p.grad ** 2
        # 平均
        self.fisher = [f / n for f in fisher_sum]
        self.params = [p.data.copy() for p in params]
        logger.info("Fisher 信息矩阵计算完成: %d 参数组, %d 样本", len(self.fisher), n)

    def _compute_sample_gradient(self, agent, sample: PretrainSample) -> None:
        """计算单个样本的损失梯度（代理损失：节点特征重建）。

        用 GNN 前向 + MSE 重建损失作为 Fisher 估计的代理。
        这是 EWC 实践中常用的简化（无需完整 RL rollout）。

        Args:
            agent: GNN-PPO 智能体。
            sample: 预训练样本。
        """
        # 用 StateEncoder 前向计算 embedding
        if not hasattr(agent, "state_encoder"):
            raise ValueError("agent 须有 state_encoder 属性")
        from polaris.trainer.gnn_ppo import GNNGraphState

        graph_state = GNNGraphState(
            node_feats=sample.node_feats,
            edge_index=sample.edge_index,
            grid_feat=np.zeros((8, 8), dtype=np.float64),
            edge_feats=sample.edge_feats if sample.edge_feats.size > 0 else None,
        )
        emb = agent._encode_graph(graph_state)
        # 代理损失：embedding 的 L2 范数（简化 Fisher 估计）
        loss = (emb * emb).sum()
        loss.backward()

    def get_ewc_penalty(self, current_params: list[np.ndarray]) -> float:
        """计算 EWC 正则化惩罚值。

        L_ewc = Σ_i F_i * (θ_i - θ*_i)²

        Args:
            current_params: 当前参数列表。

        Returns:
            EWC 惩罚值。
        """
        if not self.fisher:
            return 0.0
        penalty = 0.0
        for f, theta_star, theta in zip(self.fisher, self.params, current_params, strict=True):
            diff = theta - theta_star
            penalty += float(np.sum(f * diff * diff))
        return penalty


# =============================================================================
# EWC 正则化器（R34.md §6.2 创新点 3: EWC 防遗忘）
# =============================================================================


@dataclass
class EWCConfig:
    """EWC 正则化配置。

    Attributes:
        ewc_lambda: EWC 正则化系数（默认 100.0，Kirkpatrick 2017 推荐）。
        fisher_n_samples: Fisher 计算采样数（默认 32）。
    """

    ewc_lambda: float = 100.0
    fisher_n_samples: int = 32


class EWCRegularizer:
    """EWC 正则化器（弹性权重巩固）。

    微调时对重要参数施加 L2 约束，防止遗忘预训练知识。
    总损失 = L_task + λ * Σ_i F_i * (θ_i - θ*_i)²

    来源:
    - Kirkpatrick et al., 2017 PNAS, EWC
      https://www.pnas.org/doi/10.1073/pnas.1611835114

    Attributes:
        fisher: Fisher 信息矩阵计算器。
        config: EWC 配置。
    """

    def __init__(self, config: EWCConfig | None = None) -> None:
        """初始化 EWC 正则化器。

        Args:
            config: EWC 配置（None 用默认值）。
        """
        self.config = config or EWCConfig()
        self.fisher = FisherInformation()

    def compute_fisher(self, agent, samples: list[PretrainSample]) -> None:
        """计算 Fisher 信息矩阵。

        Args:
            agent: GNN-PPO 智能体。
            samples: 预训练样本列表。
        """
        self.fisher.compute(agent, samples, self.config.fisher_n_samples)

    def compute_penalty(self, agent) -> float:
        """计算当前 EWC 惩罚值。

        Args:
            agent: GNN-PPO 智能体。

        Returns:
            EWC 惩罚值（已乘 λ）。
        """
        if not self.fisher.fisher:
            return 0.0
        current_params = [p.data for p in agent.parameters()]
        return self.config.ewc_lambda * self.fisher.get_ewc_penalty(current_params)

    def apply_gradient_penalty(self, agent) -> None:
        """将 EWC 梯度惩罚加到参数梯度上。

        ∂L_ewc/∂θ_i = 2 * λ * F_i * (θ_i - θ*_i)

        Args:
            agent: GNN-PPO 智能体。
        """
        if not self.fisher.fisher:
            return
        params = agent.parameters()
        for p, f, theta_star in zip(
            params, self.fisher.fisher, self.fisher.params, strict=True
        ):
            if p.grad is None:
                p.grad = np.zeros_like(p.data)
            # EWC 梯度: 2 * λ * F * (θ - θ*)
            p.grad = p.grad + 2.0 * self.config.ewc_lambda * f * (p.data - theta_star)


__all__ = [
    "EWCConfig",
    "EWCRegularizer",
    "FisherInformation",
]
