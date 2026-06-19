"""GNN 端到端 PPO 训练验证测试。

验证梯度从 PPO 策略/价值损失流回 StateEncoder 的 GNN 参数，
确保端到端联合训练真正生效。
"""

from __future__ import annotations

import numpy as np

from polaris.engine.gnn import EncoderConfig, StateEncoder
from polaris.nn import Tensor
from polaris.trainer.gnn_ppo import GNNGraphState, GNNPPOAgent, GNNPPOConfig
from polaris.trainer.ppo import PPOConfig, Transition


def _make_graph_state(n_nodes: int = 3, node_feat_dim: int = 6, grid_h: int = 4, grid_w: int = 4):
    """构造测试用图特征快照。"""
    rng = np.random.RandomState(42)
    node_feats = rng.randn(n_nodes, node_feat_dim)
    edge_index = np.array([[0, 1, 1, 2], [1, 0, 2, 1]])
    grid_feat = rng.rand(grid_h, grid_w)
    return GNNGraphState(node_feats=node_feats, edge_index=edge_index, grid_feat=grid_feat)


def test_gnn_params_in_optimizer():
    """GNN 参数应被纳入 PPO 优化器。"""
    enc = StateEncoder(
        node_feat_dim=6,
        grid_size=4,
        config=EncoderConfig(hidden_dim=16, out_dim=16),
    )
    gnn_param_count = len(enc.parameters())
    assert gnn_param_count > 0, "StateEncoder 应有可训练参数"

    agent = GNNPPOAgent(
        state_encoder=enc,
        config=GNNPPOConfig(
            obs_dim=16,
            action_dim=4,
            gnn_out_dim=16,
            ppo_config=PPOConfig(lr=0.01, batch_size=4, n_epochs=2),
            hidden_dim=16,
        ),
    )
    optimizer_params = len(agent.ppo.optimizer.params)
    ppo_param_count = len(agent.ppo.ac.parameters())
    assert optimizer_params == ppo_param_count + gnn_param_count, (
        f"优化器参数数 {optimizer_params} 应等于 PPO({ppo_param_count}) + GNN({gnn_param_count})"
    )


def test_gnn_params_updated_after_update():
    """PPO update 后 GNN 参数应被更新（梯度流回 GNN）。"""
    np.random.seed(123)
    enc = StateEncoder(
        node_feat_dim=6,
        grid_size=4,
        config=EncoderConfig(hidden_dim=16, out_dim=16),
    )
    agent = GNNPPOAgent(
        state_encoder=enc,
        config=GNNPPOConfig(
            obs_dim=16,
            action_dim=4,
            gnn_out_dim=16,
            ppo_config=PPOConfig(lr=0.1, batch_size=8, n_epochs=3),
            hidden_dim=16,
        ),
    )

    gnn_params_before = [p.data.copy() for p in enc.parameters()]

    for _ in range(8):
        gs = _make_graph_state()
        obs_vec = np.random.randn(16).astype(np.float64)
        action, lp, val = agent.get_action(obs_vec, gs)
        agent.store(Transition(obs_vec, action, 1.0, lp, val, False), gs)

    metrics = agent.update(last_value=0.0)

    gnn_params_after = [p.data.copy() for p in enc.parameters()]
    updated_count = sum(
        1
        for b, a in zip(gnn_params_before, gnn_params_after, strict=True)
        if not np.allclose(b, a, atol=1e-8)
    )
    total_count = len(gnn_params_after)
    assert updated_count > 0, (
        f"GNN 参数未被更新（{updated_count}/{total_count} 参数变化），"
        f"梯度未流回 StateEncoder。metrics={metrics}"
    )


def test_gnn_gradient_chain_unit():
    """单元测试：验证 cat + scatter_add + index_select 的梯度链完整。"""
    from polaris.nn import cat, index_select, scatter_add

    # 测试 cat 梯度
    a = Tensor(np.array([1.0, 2.0]), requires_grad=True)
    b = Tensor(np.array([3.0, 4.0]), requires_grad=True)
    c = cat([a, b])
    loss_c = c.sum()
    loss_c.backward()
    assert a.grad is not None and np.allclose(a.grad, [1.0, 1.0]), f"cat 梯度错误: {a.grad}"
    assert b.grad is not None and np.allclose(b.grad, [1.0, 1.0]), f"cat 梯度错误: {b.grad}"

    # 测试 index_select 梯度
    src = Tensor(np.array([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]]), requires_grad=True)
    idx = np.array([0, 2, 0])
    sel = index_select(src, idx)
    loss_s = sel.sum()
    loss_s.backward()
    expected = np.array([[2.0, 2.0], [0.0, 0.0], [1.0, 1.0]])
    assert np.allclose(src.grad, expected), f"index_select 梯度错误: {src.grad}"

    # 测试 scatter_add 梯度
    src2 = Tensor(np.array([[1.0, 2.0], [3.0, 4.0]]), requires_grad=True)
    dsts = np.array([0, 1])
    agg = scatter_add(src2, dsts, 3)
    loss_a = agg.sum()
    loss_a.backward()
    assert np.allclose(src2.grad, [[1.0, 1.0], [1.0, 1.0]]), f"scatter_add 梯度错误: {src2.grad}"


def test_state_encoder_gradient_flow():
    """StateEncoder 前向 + 反向：梯度应流回 GNN 和 grid_proj 参数。"""
    enc = StateEncoder(
        node_feat_dim=6,
        grid_size=4,
        config=EncoderConfig(hidden_dim=16, out_dim=16),
    )
    node_feats = Tensor(np.random.randn(3, 6))
    edges = np.array([[0, 1, 1, 2], [1, 0, 2, 1]])
    grid = Tensor(np.random.rand(4, 4))

    out = enc(node_feats, edges, grid)
    loss = out.sum()
    loss.backward()

    params_with_grad = sum(
        1 for p in enc.parameters() if p.grad is not None and np.any(p.grad != 0)
    )
    total_params = len(enc.parameters())
    assert params_with_grad == total_params, (
        f"只有 {params_with_grad}/{total_params} 个参数收到非零梯度"
    )
