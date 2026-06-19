"""GNN 端到端 PPO 智能体。

将 ``StateEncoder``（GNN 状态编码器）作为可训练模块纳入 PPO 训练循环，
实现图神经网络与策略网络的联合端到端优化。

设计思路：
1. ``GNNPPOAgent`` 组合 ``StateEncoder`` + ``PPOAgent``
2. rollout 时：用 StateEncoder 编码图特征得到 embedding，与扁平 obs 拼接，
   传入 ActorCritic 采样动作；同时存储图特征供 update 时重建可微路径
3. update 时：从存储的图特征重建 Tensor 计算图，经 StateEncoder 前向，
   梯度从 ActorCritic 的策略/价值损失流回 StateEncoder 参数

来源:
- Basso et al., NeurIPS 2025, routing-aware floorplanning RL
  https://mlforsystems.org/assets/papers/neurips2025/paper42.pdf
- Schulman et al., 2017, PPO https://arxiv.org/abs/1707.06347
- R-GCN: Schlichtkrull et al., 2018
  https://arxiv.org/abs/1703.06103
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from polaris.nn import Tensor
from polaris.trainer.ppo import PPOAgent, PPOConfig, Transition


@dataclass
class GNNGraphState:
    """单步图特征快照（供 update 时重建可微计算图）。

    将 rollout 时的图特征原始数组存储，避免在 buffer 中保存 Tensor
    导致计算图过长。update 时用这些数组重建 Tensor 前向。

    Attributes:
        node_feats: 节点特征 ``[N, node_feat_dim]``。
        edge_index: 边索引 ``[2, E]``。
        grid_feat: 栅格特征 ``[grid_h, grid_w]``。
    """

    node_feats: np.ndarray
    edge_index: np.ndarray
    grid_feat: np.ndarray


@dataclass
class GNNPPOConfig:
    """GNN-PPO 智能体配置（规则 4：参数分组降低函数参数数）。

    将 ``obs_dim``/``action_dim``/``gnn_out_dim``/``ppo_config``/``hidden_dim``
    聚合为单一配置对象，使 ``GNNPPOAgent.__init__`` 参数数低于警告阈值。

    Attributes:
        obs_dim: 扁平观测维度（须等于 gnn_out_dim 以支持加法注入）。
        action_dim: 动作维度。
        gnn_out_dim: GNN 编码器输出维度。
        ppo_config: PPO 超参数。
        hidden_dim: ActorCritic 隐藏层维度。
    """

    obs_dim: int
    action_dim: int
    gnn_out_dim: int
    ppo_config: PPOConfig | None = None
    hidden_dim: int = 64


@dataclass
class GNNMinibatch:
    """GNN 小批量数据（将 _process_gnn_minibatch 的参数打包）。

    Attributes:
        combined_obs: rollout 时存储的 combined obs ``[B, obs_dim]``。
        actions: 动作数组 ``[B, action_dim]``。
        old_logprobs: 旧对数概率 ``[B]``。
        advantages: 优势 ``[B]``。
        returns: 回报 ``[B]``。
        graph_states: 图特征快照列表 ``[B]``。
    """

    combined_obs: np.ndarray
    actions: np.ndarray
    old_logprobs: np.ndarray
    advantages: np.ndarray
    returns: np.ndarray
    graph_states: list[GNNGraphState]


class GNNPPOAgent:
    """GNN 端到端 PPO 智能体（StateEncoder + PPOAgent 联合训练）。

    将 GNN 状态编码器作为策略网络的可训练特征提取器，梯度从 PPO 的
    策略/价值损失流回 GNN 参数，实现端到端联合优化。

    来源:
    - Basso et al., NeurIPS 2025, routing-aware floorplanning RL
      https://mlforsystems.org/assets/papers/neurips2025/paper42.pdf
    - Schulman et al., 2017, PPO https://arxiv.org/abs/1707.06347
    """

    def __init__(self, state_encoder, config: GNNPPOConfig) -> None:
        """初始化 GNN-PPO 智能体。

        GNN embedding 通过逐元素加法注入 obs（要求 obs_dim == gnn_out_dim），
        这样梯度可通过 Tensor.__add__ 流回 GNN 参数，实现端到端训练。

        Args:
            state_encoder: StateEncoder 实例（可训练 GNN 编码器）。
            config: GNN-PPO 配置（obs_dim/action_dim/gnn_out_dim 等）。

        Raises:
            ValueError: 当 obs_dim != gnn_out_dim 时（加法注入要求维度一致）。
        """
        if config.obs_dim != config.gnn_out_dim:
            raise ValueError(
                f"GNN 端到端训练要求 obs_dim == gnn_out_dim（加法注入），"
                f"得到 obs_dim={config.obs_dim}, gnn_out_dim={config.gnn_out_dim}。"
            )
        self.state_encoder = state_encoder
        self.gnn_out_dim = config.gnn_out_dim
        self.ppo = PPOAgent(
            obs_dim=config.obs_dim,
            action_dim=config.action_dim,
            config=config.ppo_config,
            hidden_dim=config.hidden_dim,
        )
        # 将 GNN 参数加入优化器（同步扩展 Adam 动量缓冲区 m/v）
        gnn_params = state_encoder.parameters()
        self.ppo.optimizer.add_params(gnn_params)
        self.graph_buffer: list[GNNGraphState] = []

    def _encode_graph(self, graph_state: GNNGraphState) -> Tensor:
        """用 StateEncoder 编码图特征，返回可微 Tensor embedding。

        Args:
            graph_state: 图特征快照。

        Returns:
            GNN embedding Tensor ``[gnn_out_dim]``（含计算图）。
        """
        node_feats = Tensor(graph_state.node_feats)
        grid_feat = Tensor(graph_state.grid_feat)
        return self.state_encoder(node_feats, graph_state.edge_index, grid_feat)

    def get_action(self, obs_vec: np.ndarray, graph_state: GNNGraphState):
        """采样动作（前向推理，GNN 编码通过加法注入 obs）。

        Args:
            obs_vec: 扁平观测向量。
            graph_state: 图特征快照。

        Returns:
            (action, logprob, value) 元组。
        """
        gnn_emb = self._encode_graph(graph_state)
        combined = obs_vec + gnn_emb.data.flatten()
        return self.ppo.get_action(combined)

    def store(self, transition: Transition, graph_state: GNNGraphState) -> None:
        """存储转移数据（含图特征快照）。

        Args:
            transition: PPO 转移数据（obs/action/reward/logprob/value/done）。
            graph_state: 图特征快照。
        """
        gnn_emb = self._encode_graph(graph_state)
        combined = transition.obs + gnn_emb.data.flatten()
        self.ppo.store(
            Transition(
                combined,
                transition.action,
                transition.reward,
                transition.logprob,
                transition.value,
                transition.done,
            )
        )
        self.graph_buffer.append(graph_state)

    def update(self, last_value: float = 0.0) -> dict:
        """PPO 更新（多 epoch 小批量，GNN 参数联合更新）。

        在每个 minibatch 中，从 graph_buffer 重建可微 GNN 计算图，
        将 GNN embedding 通过加法注入到 obs，使梯度能流回 StateEncoder 参数。

        来源: Basso et al., NeurIPS 2025 端到端 GNN+RL 联合训练
        https://mlforsystems.org/assets/papers/neurips2025/paper42.pdf

        Args:
            last_value: 最后一步的价值估计（bootstrap）。

        Returns:
            训练指标字典。
        """
        self.ppo.compute_advantages(last_value)
        self.ppo.current_step += 1
        self.ppo.optimizer.lr = self.ppo._get_lr()

        n = len(self.ppo.buffer)
        if n == 0:
            return {"loss": 0.0, "policy_loss": 0.0, "value_loss": 0.0, "entropy": 0.0}

        mb_data = self._extract_buffer_data(n)
        indices = np.arange(n)
        batch_size = min(self.ppo.config.batch_size, n)
        metrics_sum = {"loss": 0.0, "policy_loss": 0.0, "value_loss": 0.0, "entropy": 0.0}
        n_updates = 0

        for _ in range(self.ppo.config.n_epochs):
            np.random.shuffle(indices)
            for start in range(0, n, batch_size):
                idx = indices[start : start + batch_size]
                mb = self._slice_minibatch(mb_data, idx)
                mb_metrics = self._process_gnn_minibatch(mb)
                for k in metrics_sum:
                    metrics_sum[k] += mb_metrics[k]
                n_updates += 1

        for k in metrics_sum:
            metrics_sum[k] /= max(1, n_updates)
        self.ppo.metrics.append(metrics_sum)
        self.ppo.buffer.clear()
        self.graph_buffer.clear()
        return metrics_sum

    def _extract_buffer_data(self, n: int) -> dict:
        """从 PPO buffer 提取训练数据。

        Args:
            n: buffer 长度。

        Returns:
            含 combined_arr/actions/old_logprobs/advantages/returns 的字典。
        """
        return {
            "combined_arr": np.array(self.ppo.buffer.obs, dtype=np.float64),
            "actions": np.array(self.ppo.buffer.actions, dtype=np.float64),
            "old_logprobs": np.array(self.ppo.buffer.logprobs, dtype=np.float64),
            "advantages": self.ppo.buffer.advantages,
            "returns": self.ppo.buffer.returns,
        }

    def _slice_minibatch(self, data: dict, idx: np.ndarray) -> GNNMinibatch:
        """从完整数据中切取小批量。

        Args:
            data: 完整训练数据字典。
            idx: 小批量索引。

        Returns:
            GNNMinibatch 数据包。
        """
        return GNNMinibatch(
            combined_obs=data["combined_arr"][idx],
            actions=data["actions"][idx],
            old_logprobs=data["old_logprobs"][idx],
            advantages=data["advantages"][idx],
            returns=data["returns"][idx],
            graph_states=[self.graph_buffer[i] for i in idx],
        )

    def _process_gnn_minibatch(self, mb: GNNMinibatch) -> dict:
        """处理含 GNN 可微路径的小批量更新（加法注入）。

        对每个样本重建 GNN 前向（可微 Tensor），通过加法注入到 obs，
        然后逐样本前向 ActorCritic 并累加可微 loss，使梯度流回 GNN 参数。

        来源: Basso et al., NeurIPS 2025 端到端 GNN+RL 联合训练
        https://mlforsystems.org/assets/papers/neurips2025/paper42.pdf

        Args:
            mb: 小批量数据包。

        Returns:
            小批量指标字典。
        """
        self.ppo.optimizer.zero_grad()
        clip_lo = 1 - self.ppo.config.clip_eps
        clip_hi = 1 + self.ppo.config.clip_eps
        std = np.exp(self.ppo.ac.action_log_std.data)
        ent_const = 0.5 * self.ppo.ac.action_mean.out_features * (1 + math.log(2 * math.pi))
        ent_log_std = np.log(std).sum()

        total_loss = Tensor(0.0)
        policy_losses: list[float] = []
        value_losses: list[float] = []
        entropies: list[float] = []

        for i, gs in enumerate(mb.graph_states):
            loss, pl, vl = self._compute_sample_loss(mb, i, gs, (clip_lo, clip_hi))
            total_loss = total_loss + loss
            policy_losses.append(pl)
            value_losses.append(vl)
            entropies.append(ent_const + ent_log_std)

        total_loss = total_loss * (1.0 / len(mb.graph_states))
        total_loss.backward()
        self.ppo._clip_grads()
        self.ppo.optimizer.step()

        return {
            "loss": float(np.asarray(total_loss.data).flatten()[0]),
            "policy_loss": float(np.mean(policy_losses)),
            "value_loss": float(np.mean(value_losses)),
            "entropy": float(np.mean(entropies)),
        }

    def _compute_sample_loss(
        self,
        mb: GNNMinibatch,
        i: int,
        gs: GNNGraphState,
        clip_range: tuple[float, float],
    ) -> tuple[Tensor, float, float]:
        """计算单样本 GNN+PPO 可微损失。

        重建 GNN 前向（可微 Tensor），通过加法注入到 obs，
        前向 ActorCritic 并计算 PPO 策略损失 + 价值损失。

        Args:
            mb: 小批量数据包。
            i: 样本索引。
            gs: 该样本的图特征快照。
            clip_range: PPO clip 范围 ``(lo, hi)``。

        Returns:
            (loss_tensor, policy_loss_float, value_loss_float) 元组。
        """
        clip_lo, clip_hi = clip_range
        new_gnn_emb = self._encode_graph(gs)
        effective = Tensor(mb.combined_obs[i]) + new_gnn_emb
        mean, value = self.ppo.ac.forward(effective)

        diff = Tensor(mb.actions[i]) - mean.flatten()
        new_lp = -0.5 * (diff * diff).sum()
        ratio_t = (new_lp - Tensor(mb.old_logprobs[i])).exp()
        adv = mb.advantages[i]
        surr1 = ratio_t * adv
        surr2 = min(max(ratio_t.data, clip_lo), clip_hi) * adv
        policy_obj = surr1 if surr1.data <= surr2 else Tensor(0.0)

        v_diff = self._clip_v_diff(Tensor(mb.returns[i]) - value.flatten())
        value_obj = v_diff * v_diff
        loss = -policy_obj + self.ppo.config.vf_coef * value_obj
        pl = -float(np.asarray(surr1.data).flatten()[0])
        vl = float(np.asarray(value_obj.data).flatten()[0])
        return loss, pl, vl

    def _clip_v_diff(self, v_diff: Tensor) -> Tensor:
        """按 PPO clip_vf 裁剪价值差（若配置启用）。"""
        if self.ppo.config.clip_vf <= 0:
            return v_diff
        cv = self.ppo.config.clip_vf
        clipped = min(max(v_diff.data, -cv), cv)
        return Tensor(clipped)

    def save(self, path: str | Path) -> None:
        """保存检查点（PPO 参数 + GNN 参数）。"""
        self.ppo.save(path)
        state = json.loads(Path(path).read_text(encoding="utf-8"))
        state["gnn_params"] = [p.data.tolist() for p in self.state_encoder.parameters()]
        Path(path).write_text(json.dumps(state), encoding="utf-8")

    def load(self, path: str | Path) -> None:
        """加载检查点（PPO 参数 + GNN 参数）。"""
        self.ppo.load(path)
        state = json.loads(Path(path).read_text(encoding="utf-8"))
        if "gnn_params" in state:
            gnn_params = self.state_encoder.parameters()
            for p, data in zip(gnn_params, state["gnn_params"], strict=True):
                p.data = np.array(data, dtype=np.float64)


__all__ = ["GNNPPOAgent", "GNNPPOConfig", "GNNGraphState", "GNNMinibatch"]
