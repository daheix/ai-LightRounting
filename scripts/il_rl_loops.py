"""IL 流水线 RL 循环（从 train_il_pipeline.py 拆分，规则 7.2）。

包含 BC→RL 微调的训练循环：
- ``_run_real_rl_loop``: 真实 FloorplanEnv + PPO（孤岛#2 打通）
- ``_run_gnn_rl_loop``: GNN-PPO 联合训练（孤岛#1 打通，Basso 2025 范式）
- 辅助函数: obs 展平/动作映射/权重迁移/benchmark 选择

来源:
- Basso et al., NeurIPS 2025, R-GCN routing-aware floorplanning RL
  https://mlforsystems.org/assets/papers/neurips2025/paper42.pdf
- Schulman et al., 2017, PPO https://arxiv.org/abs/1707.06347
- LiDAR Benchmark: https://github.com/ScopeX-ASU/LiDAR (MIT, ISPD 2025)
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import torch

from polaris.data.data_loader import circuit_spec_to_netlist_dict, load_pic_ir
from polaris.data.variant_generator import CurriculumLevel
from polaris.engine.floorplan_env import FloorplanEnv, FloorplanEnvConfig
from polaris.engine.gnn import EncoderConfig, StateEncoder
from polaris.engine.netlist import load_netlist
from polaris.trainer.gnn_ppo import GNNGraphState, GNNPPOAgent, GNNPPOConfig
from polaris.trainer.ppo import PPOConfig as NumpyPPOConfig
from polaris.trainer.ppo import Transition as NumpyTransition
from polaris.trainer.ppo_buffers import PPOConfig
from polaris.trainer.ppo_torch import PPOAgent, Transition

logger = logging.getLogger("il_pipeline")

# LiDAR benchmark 目录（roadmap 2.1.2 引入公开 benchmark）
LIDAR_BENCHMARK_DIR = Path(__file__).resolve().parent.parent / "data" / "benchmarks" / "lidar"


def _select_lidar_benchmark(level: CurriculumLevel) -> str | None:
    """按课程级别选择合适规模的 LiDAR benchmark。

    Args:
        level: 课程级别（small/medium/large/xlarge）。

    Returns:
        benchmark YAML 路径，无匹配返回 None。
    """
    candidates = [
        ("toy_example/toy_example.gp.yml", 6),
        ("mrr_weight_bank_4x4/mrr_weight_bank_4x4.yml", 31),
        ("clements_8x8/clements_8x8.yml", 52),
        ("multiportmmi_8x8/multiportmmi_8x8.yml", 82),
        ("mrr_weight_bank_8x8/mrr_weight_bank_8x8.yml", 95),
        ("clements_16x16/clements_16x16.yml", 168),
        ("multiportmmi_16x16/multiportmmi_16x16.yml", 162),
        ("mrr_weight_bank_16x16/mrr_weight_bank_16x16.yml", 319),
        ("multiportmmi_32x32/multiportmmi_32x32.yml", 318),
    ]
    for rel_path, n_dev in candidates:
        if level.n_devices_min <= n_dev <= level.n_devices_max:
            full = LIDAR_BENCHMARK_DIR / rel_path
            if full.exists():
                return str(full)
    for rel_path, n_dev in candidates:
        if n_dev >= level.n_devices_min:
            full = LIDAR_BENCHMARK_DIR / rel_path
            if full.exists():
                return str(full)
    return None


def _flatten_obs(obs: dict) -> np.ndarray:
    """将 FloorplanEnv 的 dict 观测展平为向量（供 PPO 使用）。"""
    parts = []
    for v in obs.values():
        arr = np.asarray(v, dtype=np.float32).flatten()
        parts.append(arr)
    return np.concatenate(parts)


def _continuous_to_discrete(action: np.ndarray, action_space) -> np.ndarray:
    """将 PPO 连续动作映射到 MultiDiscrete 离散动作空间。

    PPO 输出连续动作（3 维），FloorplanEnv 期望 MultiDiscrete([grid_w, grid_h, 4])。
    用 sigmoid 归一化到 [0,1] 再缩放到各维度范围。

    Args:
        action: PPO 连续动作向量。
        action_space: Gymnasium MultiDiscrete 动作空间。

    Returns:
        离散动作向量。
    """
    n = action_space.shape[0]
    norm = 1.0 / (1.0 + np.exp(-action[:n]))
    discrete = np.zeros(n, dtype=np.int64)
    for i in range(n):
        dim_size = int(action_space.nvec[i])
        discrete[i] = int(norm[i] * dim_size) % dim_size
    return discrete


def _sync_agent_weights(src: PPOAgent, dst: PPOAgent) -> None:
    """将 src agent 的权重同步到 dst（维度匹配的层）。

    BC 预训练 agent 与 RL agent 维度不同，仅同步匹配的层（如价值头）。
    维度不匹配的层跳过（保留 dst 原值）。

    Args:
        src: 源 agent（RL 微调后）。
        dst: 目标 agent（BC 预训练，供下一阶段）。
    """
    src_params = list(src.ac.parameters())
    dst_params = list(dst.ac.parameters())
    for sp, dp in zip(src_params, dst_params, strict=False):
        if sp.shape == dp.shape:
            dp.data = sp.data.clone()


def run_real_rl_loop(
    agent: PPOAgent,
    benchmark_path: str,
    n_episodes: int,
    seed: int,
) -> float:
    """真实 RL 训练循环（FloorplanEnv + PPO rollout/update）。

    在 LiDAR benchmark 上跑真实布局环境，打通 BC→真实 RL 链路。

    **维度对齐说明**：BC 预训练用器件级固定 obs_dim=16，而 FloorplanEnv
    的 obs 是全局特征（occupancy grid + port_positions），维度随器件数变化。
    当前实现：RL 微调阶段创建新 agent（obs_dim 匹配环境），BC 权重迁移
    留待 roadmap 中期目标（架构对齐后实现）。

    Args:
        agent: PPOAgent（BC 预训练权重，当前未迁移到 RL agent）。
        benchmark_path: LiDAR benchmark YAML 路径。
        n_episodes: 轮次数。
        seed: 随机种子。

    Returns:
        平均奖励。
    """
    np.random.seed(seed)
    torch.manual_seed(seed)
    circuit = load_pic_ir(benchmark_path)
    nl_dict = circuit_spec_to_netlist_dict(circuit)
    net, devices, _ = load_netlist(nl_dict)
    n_dev = len(devices)
    grid_size = max(20.0, min(50.0, circuit.canvas_w / 30.0))
    env = FloorplanEnv(
        net,
        devices,
        canvas_w=circuit.canvas_w,
        canvas_h=circuit.canvas_h,
        grid_size=grid_size,
    )
    obs, _ = env.reset()
    obs_dim = _flatten_obs(obs).shape[0]
    action_dim = int(np.prod(env.action_space.shape))
    rl_agent = _create_rl_agent(agent, obs_dim, action_dim)
    rewards = _run_ppo_rollout(rl_agent, env, n_episodes, n_dev)
    _sync_agent_weights(rl_agent, agent)
    return float(np.mean(rewards)) if rewards else 0.0


def _create_rl_agent(
    bc_agent: PPOAgent,
    obs_dim: int,
    action_dim: int,
) -> PPOAgent:
    """创建 RL agent（obs_dim 匹配真实环境）。"""
    return PPOAgent(
        obs_dim=obs_dim,
        action_dim=action_dim,
        config=PPOConfig(lr=bc_agent.config.lr),
        hidden_dim=bc_agent.obs_dim,
    )


def _run_ppo_rollout(
    rl_agent: PPOAgent,
    env: FloorplanEnv,
    n_episodes: int,
    n_dev: int,
) -> list[float]:
    """PPO rollout + update 循环，返回每 episode 的奖励列表。"""
    rewards: list[float] = []
    rollout_steps = min(64, n_dev)
    for _ep in range(n_episodes):
        obs, _ = env.reset()
        ep_reward = 0.0
        for _step in range(rollout_steps):
            obs_vec = _flatten_obs(obs)
            action, logprob, value = rl_agent.get_action(obs_vec)
            discrete_action = _continuous_to_discrete(action, env.action_space)
            obs, reward, terminated, truncated, _info = env.step(discrete_action)
            ep_reward += reward
            rl_agent.store(Transition(obs_vec, action, reward, logprob, value, terminated))
            if len(rl_agent.buffer) >= 32:
                rl_agent.update(last_value=0.0)
            if terminated or truncated:
                break
        rewards.append(ep_reward)
    return rewards


def run_gnn_rl_loop(
    agent: PPOAgent,
    benchmark_path: str,
    n_episodes: int,
    cfg,
) -> float:
    """GNN-PPO RL 训练循环（孤岛#1 打通）。

    用 ``GNNPPOAgent``（StateEncoder + PPO 联合训练）在真实 ``FloorplanEnv``
    上做 RL 微调，GNN 编码图特征并通过加法注入 obs，梯度从 PPO loss 流回
    GNN 参数（Basso et al. NeurIPS 2025 端到端范式）。

    来源: Basso et al., NeurIPS 2025, R-GCN routing-aware floorplanning RL
      https://mlforsystems.org/assets/papers/neurips2025/paper42.pdf

    Args:
        agent: BC 预训练的 PPOAgent（PyTorch，权重部分迁移到 GNN-PPO）。
        benchmark_path: LiDAR benchmark YAML 路径。
        n_episodes: 轮次数。
        cfg: 流水线配置（含 use_gnn/gnn_out_dim）。

    Returns:
        平均奖励。
    """
    np.random.seed(cfg.seed)
    torch.manual_seed(cfg.seed)
    circuit = load_pic_ir(benchmark_path)
    nl_dict = circuit_spec_to_netlist_dict(circuit)
    net, devices, _ = load_netlist(nl_dict)
    n_dev = len(devices)
    grid_size = max(20.0, min(50.0, circuit.canvas_w / 30.0))
    grid_w = max(1, int(circuit.canvas_w / grid_size))
    enc = _build_state_encoder(grid_w, cfg.hidden_dim, cfg.gnn_out_dim)
    env = FloorplanEnv(
        net,
        devices,
        config=FloorplanEnvConfig(
            canvas_w=circuit.canvas_w,
            canvas_h=circuit.canvas_h,
            grid_size=grid_size,
            state_encoder=enc,
        ),
    )
    gnn_agent = _build_gnn_agent(enc, env, cfg)
    _transfer_bc_to_gnn(agent, gnn_agent)
    rewards = _run_gnn_rollout(gnn_agent, env, n_episodes, n_dev, cfg.gnn_out_dim)
    return float(np.mean(rewards)) if rewards else 0.0


def _build_state_encoder(grid_w: int, hidden_dim: int, gnn_out_dim: int) -> StateEncoder:
    """创建 StateEncoder（node_feat_dim=6: w/h/area/placed/ports/cat）。"""
    return StateEncoder(
        node_feat_dim=6,
        grid_size=grid_w,
        config=EncoderConfig(hidden_dim=hidden_dim, out_dim=gnn_out_dim),
    )


def _build_gnn_agent(enc: StateEncoder, env: FloorplanEnv, cfg) -> GNNPPOAgent:
    """创建 GNNPPOAgent。"""
    action_dim = int(np.prod(env.action_space.shape))
    return GNNPPOAgent(
        state_encoder=enc,
        config=GNNPPOConfig(
            obs_dim=cfg.gnn_out_dim,
            action_dim=action_dim,
            gnn_out_dim=cfg.gnn_out_dim,
            ppo_config=NumpyPPOConfig(lr=cfg.lr, batch_size=32, n_epochs=2),
            hidden_dim=cfg.hidden_dim,
        ),
    )


def _run_gnn_rollout(
    gnn_agent: GNNPPOAgent,
    env: FloorplanEnv,
    n_episodes: int,
    n_dev: int,
    gnn_out_dim: int,
) -> list[float]:
    """GNN-PPO rollout + update 循环，返回每 episode 的奖励列表。"""
    rewards: list[float] = []
    rollout_steps = min(64, n_dev)
    for _ep in range(n_episodes):
        obs, _ = env.reset()
        ep_reward = 0.0
        for _step in range(rollout_steps):
            obs_vec, graph_state = _extract_gnn_obs(obs, gnn_out_dim)
            action, logprob, value = gnn_agent.get_action(obs_vec, graph_state)
            discrete_action = _continuous_to_discrete(action, env.action_space)
            obs, reward, terminated, truncated, _info = env.step(discrete_action)
            ep_reward += reward
            gnn_agent.store(
                NumpyTransition(obs_vec, action, reward, logprob, value, terminated),
                graph_state,
            )
            if len(gnn_agent.ppo.buffer) >= 32:
                gnn_agent.update(last_value=0.0)
            if terminated or truncated:
                break
        rewards.append(ep_reward)
    return rewards


def _extract_gnn_obs(obs: dict, gnn_out_dim: int) -> tuple[np.ndarray, GNNGraphState]:
    """从 FloorplanEnv obs 提取 GNN-PPO 所需的 obs_vec 和 graph_state。

    当 ``state_encoder`` 启用时，FloorplanEnv obs 含：
    - ``gnn_embedding``: GNN 前向输出（detached numpy，dim=gnn_out_dim）
    - ``graph_features``: 原始图特征 dict（node_feats/edge_index/grid_feat）

    Args:
        obs: FloorplanEnv 的 dict 观测。
        gnn_out_dim: GNN 输出维度（用于 obs_vec 维度校验）。

    Returns:
        (obs_vec, graph_state) 元组。
    """
    obs_vec = np.asarray(obs["gnn_embedding"], dtype=np.float64).flatten()
    if obs_vec.shape[0] != gnn_out_dim:
        obs_vec = np.resize(obs_vec, gnn_out_dim)
    gf = obs["graph_features"]
    graph_state = GNNGraphState(
        node_feats=gf["node_feats"],
        edge_index=gf["edge_index"],
        grid_feat=gf["grid_feat"],
    )
    return obs_vec, graph_state


def _transfer_bc_to_gnn(bc_agent: PPOAgent, gnn_agent: GNNPPOAgent) -> None:
    """将 BC 预训练权重迁移到 GNN-PPO（仅维度匹配的层）。

    BC 用 PyTorch PPOAgent（obs_dim=16），GNN-PPO 用 NumPy PPOAgent
    （obs_dim=gnn_out_dim）。shared encoder 第一层维度不匹配无法迁移，
    但 action_mean/value_head（hidden_dim→action_dim/1）可迁移。

    Args:
        bc_agent: BC 预训练的 PyTorch PPOAgent。
        gnn_agent: 待初始化的 GNN-PPO 智能体。
    """
    bc_params = {
        name: param.detach().cpu().numpy() for name, param in bc_agent.ac.named_parameters()
    }
    gnn_ac = gnn_agent.ppo.ac
    transfer_map = {
        "action_mean.weight": "action_mean",
        "action_mean.bias": "action_mean",
        "value_head.weight": "value_head",
        "value_head.bias": "value_head",
    }
    for bc_name, layer_attr in transfer_map.items():
        _transfer_param(bc_params, bc_name, gnn_ac, layer_attr)
    logger.info("BC→GNN-PPO 权重迁移完成（action_mean/value_head 匹配层）")


def _transfer_param(
    bc_params: dict,
    bc_name: str,
    gnn_ac,
    layer_attr: str,
) -> None:
    """迁移单个参数（维度匹配时）。"""
    if bc_name not in bc_params:
        return
    bc_w = bc_params[bc_name]
    parts = bc_name.split(".")
    layer = getattr(gnn_ac, layer_attr, None)
    if layer is None:
        return
    gnn_w = getattr(layer, parts[1], None)
    if gnn_w is not None and gnn_w.data.shape == bc_w.shape:
        gnn_w.data = bc_w.copy()
