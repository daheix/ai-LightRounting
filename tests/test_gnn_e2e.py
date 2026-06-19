"""GNN 端到端联合训练验证测试（M3.1）。

验证 ``GNNPPOAgent`` 的完整训练循环：``get_action → store → update``，
GNN embedding 可微性（梯度流回 StateEncoder 参数），检查点保存/加载，
以及在小型电路（3-4 器件）上运行 5 个 episode 不崩溃。

来源:
- Basso et al., NeurIPS 2025, routing-aware floorplanning RL
  https://mlforsystems.org/assets/papers/neurips2025/paper42.pdf
- Schulman et al., 2017, PPO https://arxiv.org/abs/1707.06347
"""

from __future__ import annotations

import json

import numpy as np

from polaris.engine.gnn import EncoderConfig, StateEncoder
from polaris.engine.netlist import load_netlist
from polaris.nn import Tensor
from polaris.trainer.gnn_ppo import GNNGraphState, GNNPPOAgent, GNNPPOConfig
from polaris.trainer.ppo import PPOConfig, Transition

YAML_NETLIST = """
name: gnn_e2e_test
instances:
  wg1: {component: strip_waveguide, platform: SOI}
  mmi1: {component: mmi_1x2, platform: SOI}
  wg2: {component: strip_waveguide, platform: SOI}
connections:
  - [wg1, out, mmi1, in]
  - [mmi1, out0, wg2, in]
"""


def _make_graph_state(
    n_nodes: int = 3,
    node_feat_dim: int = 6,
    grid_h: int = 4,
    grid_w: int = 4,
) -> GNNGraphState:
    """构造测试用图特征快照。

    Args:
        n_nodes: 节点数。
        node_feat_dim: 节点特征维度。
        grid_h: 栅格高度。
        grid_w: 栅格宽度。

    Returns:
        GNNGraphState 实例。
    """
    rng = np.random.RandomState(42)
    node_feats = rng.randn(n_nodes, node_feat_dim)
    edge_index = np.array([[0, 1, 1, 2], [1, 0, 2, 1]])
    grid_feat = rng.rand(grid_h, grid_w)
    return GNNGraphState(node_feats=node_feats, edge_index=edge_index, grid_feat=grid_feat)


def _build_agent(
    obs_dim: int = 16,
    action_dim: int = 4,
    hidden_dim: int = 16,
) -> GNNPPOAgent:
    """构造测试用 GNN-PPO 智能体。

    Args:
        obs_dim: 观测维度（须等于 gnn_out_dim）。
        action_dim: 动作维度。
        hidden_dim: 隐藏层维度。

    Returns:
        GNNPPOAgent 实例。
    """
    enc = StateEncoder(
        node_feat_dim=6,
        grid_size=4,
        config=EncoderConfig(hidden_dim=hidden_dim, out_dim=obs_dim),
    )
    return GNNPPOAgent(
        state_encoder=enc,
        config=GNNPPOConfig(
            obs_dim=obs_dim,
            action_dim=action_dim,
            gnn_out_dim=obs_dim,
            ppo_config=PPOConfig(lr=0.01, batch_size=4, n_epochs=2),
            hidden_dim=hidden_dim,
        ),
    )


def test_full_training_cycle_get_action_store_update():
    """验证完整训练循环：get_action → store → update 不崩溃且返回有效指标。

    来源: Basso et al., NeurIPS 2025 端到端 GNN+RL 联合训练
    https://mlforsystems.org/assets/papers/neurips2025/paper42.pdf
    """
    np.random.seed(0)
    agent = _build_agent(obs_dim=16, action_dim=4)
    n_steps = 8

    for _ in range(n_steps):
        gs = _make_graph_state()
        obs_vec = np.random.randn(16).astype(np.float64)
        action, logprob, value = agent.get_action(obs_vec, gs)
        assert action.shape == (4,), f"动作形状错误: {action.shape}"
        assert isinstance(logprob, float)
        assert isinstance(value, float)
        agent.store(Transition(obs_vec, action, 1.0, logprob, value, False), gs)

    assert len(agent.ppo.buffer) == n_steps
    metrics = agent.update(last_value=0.0)
    assert "loss" in metrics
    assert "policy_loss" in metrics
    assert "value_loss" in metrics
    assert "entropy" in metrics
    assert len(agent.ppo.buffer) == 0, "update 后 buffer 应清空"


def test_gnn_embeddings_differentiable():
    """验证 GNN embedding 可微：梯度从 loss 流回 StateEncoder 参数。

    构造可微 loss = sum(gnn_emb)，反向传播后断言 GNN 参数收到非零梯度。
    """
    enc = StateEncoder(
        node_feat_dim=6,
        grid_size=4,
        config=EncoderConfig(hidden_dim=16, out_dim=16),
    )
    gs = _make_graph_state()
    node_feats = Tensor(gs.node_feats)
    grid_feat = Tensor(gs.grid_feat)

    embedding = enc(node_feats, gs.edge_index, grid_feat)
    assert embedding.data.shape == (16,), f"embedding 形状错误: {embedding.data.shape}"

    loss = embedding.sum()
    loss.backward()

    params_with_grad = 0
    total_params = 0
    for p in enc.parameters():
        total_params += 1
        if p.grad is not None and np.any(np.abs(p.grad) > 0):
            params_with_grad += 1
    assert params_with_grad > 0, f"无 GNN 参数收到非零梯度（{params_with_grad}/{total_params}）"


def test_save_load_checkpoint(tmp_path):
    """验证 GNN+PPO 检查点保存/加载：参数一致。

    来源: PPO 断点续训 https://arxiv.org/abs/1707.06347
    """
    agent = _build_agent(obs_dim=16, action_dim=4)
    gs = _make_graph_state()
    obs_vec = np.random.randn(16).astype(np.float64)
    action, logprob, value = agent.get_action(obs_vec, gs)
    agent.store(Transition(obs_vec, action, 1.0, logprob, value, False), gs)
    agent.update(last_value=0.0)

    ckpt_path = tmp_path / "gnn_ppo_ckpt.json"
    agent.save(ckpt_path)
    assert ckpt_path.exists(), "检查点文件应存在"

    state = json.loads(ckpt_path.read_text(encoding="utf-8"))
    assert "gnn_params" in state, "检查点应含 gnn_params 字段"
    assert "params" in state, "检查点应含 PPO params 字段"

    ppo_before = [p.data.copy() for p in agent.ppo.ac.parameters()]
    gnn_before = [p.data.copy() for p in agent.state_encoder.parameters()]

    agent2 = _build_agent(obs_dim=16, action_dim=4)
    agent2.load(ckpt_path)

    ppo_after = [p.data.copy() for p in agent2.ppo.ac.parameters()]
    gnn_after = [p.data.copy() for p in agent2.state_encoder.parameters()]

    for b, a in zip(ppo_before, ppo_after, strict=True):
        assert np.allclose(b, a, atol=1e-9), "PPO 参数加载后不一致"
    for b, a in zip(gnn_before, gnn_after, strict=True):
        assert np.allclose(b, a, atol=1e-9), "GNN 参数加载后不一致"


def test_small_circuit_no_crash():
    """在小型电路（3 器件）上运行 GNN-PPO 智能体不崩溃。

    使用真实网表加载 → FloorplanEnv 构建 graph_features → GNN-PPO 采样动作。
    """
    from polaris.engine.floorplan_env import FloorplanEnv, FloorplanEnvConfig

    net, devices, _ = load_netlist(YAML_NETLIST)
    assert len(devices) == 3, f"测试电路应有 3 个器件，实际 {len(devices)}"

    canvas_w = 200.0
    canvas_h = 200.0
    env_grid_size = 20.0
    grid_w = int(canvas_w / env_grid_size)
    gnn_out_dim = 16
    enc = StateEncoder(
        node_feat_dim=6,
        grid_size=grid_w,
        config=EncoderConfig(hidden_dim=16, out_dim=gnn_out_dim),
    )
    agent = GNNPPOAgent(
        state_encoder=enc,
        config=GNNPPOConfig(
            obs_dim=gnn_out_dim,
            action_dim=3,
            gnn_out_dim=gnn_out_dim,
            ppo_config=PPOConfig(lr=0.01, batch_size=4, n_epochs=2),
            hidden_dim=16,
        ),
    )
    env = FloorplanEnv(
        net,
        devices,
        config=FloorplanEnvConfig(
            canvas_w=canvas_w,
            canvas_h=canvas_h,
            grid_size=env_grid_size,
            state_encoder=enc,
        ),
    )
    obs, _ = env.reset()
    assert "graph_features" in obs, "启用 state_encoder 后 obs 应含 graph_features"

    gf = obs["graph_features"]
    gs = GNNGraphState(
        node_feats=gf["node_feats"],
        edge_index=gf["edge_index"],
        grid_feat=gf["grid_feat"],
    )
    obs_vec = np.random.randn(gnn_out_dim).astype(np.float64)
    action, _, _ = agent.get_action(obs_vec, gs)
    assert action.shape == (3,), f"动作形状错误: {action.shape}"


def test_five_episodes_minimum():
    """运行 5 个 episode 的完整训练循环，验证不崩溃且指标合理。

    每个 episode：reset → rollout（get_action + store）→ update。
    """
    np.random.seed(42)
    agent = _build_agent(obs_dim=16, action_dim=4)
    n_episodes = 5
    n_steps_per_ep = 6
    episode_rewards = []

    for ep in range(n_episodes):
        ep_reward = 0.0
        for _ in range(n_steps_per_ep):
            gs = _make_graph_state()
            obs_vec = np.random.randn(16).astype(np.float64)
            action, logprob, value = agent.get_action(obs_vec, gs)
            reward = float(np.random.RandomState(ep).rand())
            ep_reward += reward
            agent.store(Transition(obs_vec, action, reward, logprob, value, False), gs)
        metrics = agent.update(last_value=0.0)
        episode_rewards.append(ep_reward)
        assert "loss" in metrics, f"episode {ep} 未返回 loss 指标"

    assert len(episode_rewards) == n_episodes, "应完成 5 个 episode"
    assert all(isinstance(r, float) for r in episode_rewards)
