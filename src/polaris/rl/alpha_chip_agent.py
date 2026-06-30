"""R34-R35 路标：AlphaChip 强化学习布局智能体。

本模块从 ``alpha_chip.py`` 拆分而来（facade 模式），提供
``AlphaChipAgent``，实现基于 Edge-GNN + PPO 的光子 IC 布局智能体。
外部 import 路径保持不变（``from polaris.rl.alpha_chip import
AlphaChipAgent``）。

## 学术依据

- Google DeepMind AlphaChip:
  https://deepmind.google/discover/blog/alphachip-a-new-approach-to-chip-layout/
- Mirhoseini et al., Nature 2024, "AlphaChip":
  https://doi.org/10.1038/s41586-024-07714-9
- Mirhoseini et al., Nature 2021, "A graph placement methodology for fast
  chip design" DOI: 10.1038/s41586-021-03544-w
- Schulman et al., 2017, PPO: https://arxiv.org/abs/1707.06347
- Gilmer et al., 2017, MPNN: https://arxiv.org/abs/1704.01212
- Sutton & Barto, 2018, "Reinforcement Learning: An Introduction" §13

## 【创新】扩展到光子布局

AlphaChip 原为电子 IC 布局设计，本模块将其扩展到光子 IC 布局：
- 电子 IC 优化线长 / 拥塞 / 面积
- 光子 IC 增加光学约束（波导长度 / 弯曲半径 / 交叉数 / 均匀性）

## 架构统一（D05 Task 10）

复用 PoLaRIS 已有成熟实现，禁止自实现简化版（规则 R09 单文件版本升级、
R03 禁止 fall-back）：
- 图编码器：复用 ``polaris.engine.alphachip_gnn.AlphaChipEdgeGNN``
  （AlphaChip Edge-GNN + 多关系边变换 + GAT + GlobalAttention 读出），
  替代旧版自实现简化版 numpy GNN。
- 策略/价值训练：复用 ``polaris.trainer.ppo_torch.PPOAgent``（PPO clip + GAE），
  替代旧版自实现简化版 REINFORCE + baseline。
- 连续动作（归一化 x,y）经量化映射到离散网格位置，保留 ``select_action``
  返回网格索引的外部接口。

## 来源

- 拆分自: ``src/polaris/rl/alpha_chip.py``（原文件 1096 行 → 拆分后 ≤800 行）
- 路标: R34-R35
- 架构统一: D05 Task 10
"""

from __future__ import annotations

import numpy as np

# D05 架构统一：复用 engine 与 trainer 已有成熟实现（禁止自实现简化版）
from polaris.engine.alphachip_gnn import AlphaChipEdgeGNN
from polaris.nn import Tensor
from polaris.rl.alpha_chip_config import _GRID_CELL_SIZE, AlphaChipConfig
from polaris.rl.alpha_chip_encoder import PhotonicPlacementEncoder
from polaris.rl.alpha_chip_reward import PhotonicPlacementReward
from polaris.rl.alpha_chip_trainer import AlphaChipTrainer
from polaris.trainer.ppo_buffers import PPOConfig
from polaris.trainer.ppo_torch import PPOAgent


class AlphaChipAgent:
    """AlphaChip 强化学习布局智能体。

    学术依据：
    - Mirhoseini 2021 Nature（图布局方法）
      https://doi.org/10.1038/s41586-021-03544-w
    - Mirhoseini 2024 Nature（AlphaChip 完整论文）
      https://doi.org/10.1038/s41586-024-07714-9
    - Sutton & Barto 2018 §13（策略梯度）

    架构：
    1. Edge-based GNN：学习器件间的空间关系（Gilmer 2017 MPNN）
    2. 策略网络：输出器件放置位置的概率分布
    3. 价值网络：评估布局质量（baseline）
    4. REINFORCE + baseline 训练：策略优化

    【创新】扩展到光子布局：
    - 电子 IC 优化线长 / 拥塞 / 面积
    - 光子 IC 增加光学约束（波导长度 / 弯曲半径 / 交叉数 / 均匀性）
    """

    def __init__(self, config: AlphaChipConfig) -> None:
        """初始化 AlphaChip agent。

        Args:
            config: AlphaChip 配置。
        """
        self.config = config
        self.encoder = PhotonicPlacementEncoder()
        self.reward = PhotonicPlacementReward()
        self.circuit: dict | None = None
        # D05 架构统一：复用 AlphaChipEdgeGNN（替代自实现简化版 GNN）
        # in_dim = 节点特征(9) + 位置特征(4) = 13
        in_dim = self.encoder.node_feat_dim + 4
        self.gnn = AlphaChipEdgeGNN(
            in_dim=in_dim,
            edge_feat_dim=self.encoder.edge_feat_dim,
            hidden_dim=config.gnn_hidden,
            out_dim=config.gnn_hidden,
            num_layers=config.gnn_layers,
            use_gat=config.use_attention,
            use_multi_relation=True,
        )
        # D05 架构统一：复用 PPOAgent（替代自实现简化版 REINFORCE）
        # PPO 在连续动作空间优化，动作 = 归一化 (x, y)，
        # select_action 内部量化到离散网格位置（保留外部接口）。
        obs_dim = config.gnn_hidden + self.encoder.node_feat_dim + 3
        self.ppo = PPOAgent(
            obs_dim=obs_dim,
            action_dim=2,
            config=PPOConfig(lr=config.learning_rate),
            hidden_dim=config.gnn_hidden,
        )
        self._last_continuous_action: np.ndarray | None = None

    def _build_occupancy_grid(self, placement: dict, circuit: dict) -> np.ndarray:
        """构建占用栅格。

        Args:
            placement: 布局 dict。
            circuit: 电路描述 dict。

        Returns:
            占用栅格 [grid_h, grid_w]，1 表示已占用。
        """
        grid_h, grid_w = self.config.grid_size
        grid = np.zeros((grid_h, grid_w), dtype=np.float64)
        for dev in circuit["devices"]:
            if dev["id"] not in placement:
                continue
            p = placement[dev["id"]]
            w = float(dev.get("width", 50))
            h = float(dev.get("height", 30))
            gi0 = max(0, int(p["x"] / _GRID_CELL_SIZE))
            gi1 = min(grid_w, int(np.ceil((p["x"] + w) / _GRID_CELL_SIZE)))
            gj0 = max(0, int(p["y"] / _GRID_CELL_SIZE))
            gj1 = min(grid_h, int(np.ceil((p["y"] + h) / _GRID_CELL_SIZE)))
            grid[gj0:gj1, gi0:gi1] = 1.0
        return grid

    def _build_action_mask(self, placement: dict, circuit: dict) -> np.ndarray:
        """构建动作掩码（屏蔽已占用位置）。

        Args:
            placement: 布局 dict。
            circuit: 电路描述 dict。

        Returns:
            动作掩码 [grid_h * grid_w]，0 表示不可用。
        """
        grid_h, grid_w = self.config.grid_size
        mask = np.ones(grid_h * grid_w, dtype=np.float64)
        for dev in circuit["devices"]:
            if dev["id"] not in placement:
                continue
            p = placement[dev["id"]]
            w = float(dev.get("width", 50))
            h = float(dev.get("height", 30))
            gi0 = max(0, int(p["x"] / _GRID_CELL_SIZE))
            gi1 = min(grid_w, int(np.ceil((p["x"] + w) / _GRID_CELL_SIZE)))
            gj0 = max(0, int(p["y"] / _GRID_CELL_SIZE))
            gj1 = min(grid_h, int(np.ceil((p["y"] + h) / _GRID_CELL_SIZE)))
            for r in range(gj0, gj1):
                for c in range(gi0, gi1):
                    mask[r * grid_w + c] = 0.0
        return mask

    def _build_state(
        self, placement: dict, circuit: dict, current_dev: dict
    ) -> dict:
        """构建状态。

        状态包含：
        - GNN 编码的图嵌入（mean pooling）
        - 当前器件特征
        - 占用栅格统计特征

        Args:
            placement: 当前布局 dict。
            circuit: 电路描述 dict。
            current_dev: 当前要放置的器件 dict。

        Returns:
            状态 dict，含 ``embedding``、``mask``、``grid``。
        """
        node_feats = self.encoder.encode_placement(placement, circuit)
        graph = self.encoder.encode_circuit(circuit)
        if node_feats.shape[0] > 0:
            # D05: 复用 AlphaChipEdgeGNN（GlobalAttention 读出图级嵌入）
            node_feats_t = Tensor(node_feats)
            edge_feats_t = Tensor(graph["edge_feats"])
            graph_emb_t = self.gnn(node_feats_t, graph["edge_index"], edge_feats_t)
            graph_emb = np.asarray(graph_emb_t.data).ravel()
        else:
            graph_emb = np.zeros(self.config.gnn_hidden, dtype=np.float64)
        dev_feat = self.encoder.compute_features(current_dev)
        grid = self._build_occupancy_grid(placement, circuit)
        grid_stats = np.array(
            [grid.mean(), grid.sum(), grid.std()], dtype=np.float64
        )
        state_vec = np.concatenate([graph_emb, dev_feat, grid_stats])
        mask = self._build_action_mask(placement, circuit)
        return {
            "embedding": state_vec,
            "mask": mask,
            "grid": grid,
            "graph_emb": graph_emb,
            "dev_feat": dev_feat,
        }

    def select_action(self, state: dict) -> tuple:
        """选择动作（器件放置位置）。

        D05: 复用 PPOAgent 在连续动作空间采样（归一化 x,y），
        量化映射到离散网格位置索引（保留外部接口）。

        Args:
            state: 状态 dict。

        Returns:
            (action, logprob, value) 元组。action 为网格位置索引，
            logprob 为连续动作对数概率，value 为价值估计。
        """
        action_cont, logprob, value = self._select_continuous_action(state)
        action = self._quantize_action(action_cont, state["mask"])
        self._last_continuous_action = np.asarray(action_cont, dtype=np.float64)
        return action, float(logprob), float(value)

    def _select_continuous_action(self, state: dict) -> tuple:
        """连续动作采样（D05: 复用 PPOAgent.get_action）。

        Args:
            state: 状态 dict。

        Returns:
            (action_cont, logprob, value)，action_cont 为 [2] 连续动作。
        """
        state_vec = np.asarray(state["embedding"], dtype=np.float64)
        action_cont, logprob, value = self.ppo.get_action(state_vec)
        return np.asarray(action_cont, dtype=np.float64), float(logprob), float(value)

    def _quantize_action(self, action_cont: np.ndarray, mask: np.ndarray) -> int:
        """将连续动作量化到离散网格位置。

        连续动作经 sigmoid 压缩到 [0,1]，映射到 (row, col)，
        action = row * grid_w + col。被掩码的位置就近偏移到最近可用位置。

        Args:
            action_cont: 连续动作 [2]。
            mask: 动作掩码 [grid_h * grid_w]，0 表示不可用。

        Returns:
            网格位置索引。
        """
        grid_h, grid_w = self.config.grid_size
        norm = 1.0 / (1.0 + np.exp(-np.asarray(action_cont, dtype=np.float64)))
        row = int(np.clip(norm[0] * grid_h, 0, grid_h - 1))
        col = int(np.clip(norm[1] * grid_w, 0, grid_w - 1))
        action = row * grid_w + col
        if mask[action] <= 0.0:
            action = self._nearest_available(action, mask)
        return int(action)

    @staticmethod
    def _nearest_available(action: int, mask: np.ndarray) -> int:
        """就近搜索可用网格位置（掩码屏蔽时）。

        R03 合规：当所有位置都被占用时，抛出 ValueError 而非 fall-back。

        Args:
            action: 原始网格索引。
            mask: 动作掩码。

        Returns:
            最近可用网格索引。

        Raises:
            ValueError: 所有位置都被占用（R03 无 fall-back）。
        """
        n = len(mask)
        for radius in range(1, n):
            for delta in (-radius, radius):
                idx = action + delta
                if 0 <= idx < n and mask[idx] > 0.0:
                    return int(idx)
        # R03 合规：所有位置都被占用时抛出错误，而非 fall-back 返回可能不合适的位置
        raise ValueError(
            f"所有网格位置均被占用，无法找到可用位置进行器件放置"
            f"（R03 禁止 fall-back）"
        )

    def compute_reward(self, placement: dict) -> float:
        """计算奖励。

        光子布局奖励 = -α·线长 - β·拥塞 - γ·交叉数 - δ·弯曲违反 - ε·均匀性

        Args:
            placement: 布局 dict。

        Returns:
            奖励值（标量）。
        """
        assert self.circuit is not None, "agent.circuit 未设置"
        result = self.reward.compute(placement, self.circuit)
        return result["reward"]

    def train(self, circuit: dict) -> dict:
        """训练 AlphaChip agent。

        Args:
            circuit: 电路描述 dict。

        Returns:
            训练历史 dict。
        """
        trainer = AlphaChipTrainer(self, self.config)
        return trainer.train([circuit], n_epochs=10)

    def place(self, circuit: dict) -> dict:
        """使用训练好的 agent 进行布局。

        Args:
            circuit: 电路描述 dict。

        Returns:
            布局 dict，{inst_id: {"x", "y", "rotation"}}。
        """
        self.circuit = circuit
        placement: dict[str, dict] = {}
        grid_h, grid_w = self.config.grid_size
        for dev in circuit["devices"]:
            state = self._build_state(placement, circuit, dev)
            action, _, _ = self.select_action(state)
            row = action // grid_w
            col = action % grid_w
            placement[dev["id"]] = {
                "x": float(col * _GRID_CELL_SIZE),
                "y": float(row * _GRID_CELL_SIZE),
                "rotation": 0,
            }
        return placement


__all__ = ["AlphaChipAgent"]
