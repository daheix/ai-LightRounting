"""AlphaChip Agent 单元测试。

覆盖：
- ``src/polaris/rl/alpha_chip_agent.py``：AlphaChipAgent
  强化学习布局智能体（Edge-GNN + PPO）

来源:
- Mirhoseini 2021 Nature, "A graph placement methodology for fast chip design"
  https://doi.org/10.1038/s41586-021-03544-w
- Mirhoseini 2024 Nature, AlphaChip
  https://doi.org/10.1038/s41586-024-07714-9
- Schulman et al., 2017, PPO https://arxiv.org/abs/1707.06347
"""

from __future__ import annotations

import numpy as np
import pytest

from polaris.rl.alpha_chip_agent import AlphaChipAgent
from polaris.rl.alpha_chip_config import AlphaChipConfig


# ---------------------------------------------------------------------------
# 测试数据
# ---------------------------------------------------------------------------

_SIMPLE_CIRCUIT = {
    "devices": [
        {"id": "d0", "type": "mzi", "width": 50.0, "height": 30.0, "ports": ["p0", "p1"]},
        {"id": "d1", "type": "ring", "width": 40.0, "height": 40.0, "ports": ["p0", "p1"]},
        {"id": "d2", "type": "mmi", "width": 60.0, "height": 20.0, "ports": ["p0", "p1", "p2", "p3"]},
    ],
    "nets": [
        {"src": ["d0", "p1"], "dst": ["d1", "p0"], "type": "waveguide", "target_length": 100.0},
        {"src": ["d1", "p1"], "dst": ["d2", "p0"], "type": "waveguide", "target_length": 100.0},
    ],
}


# ---------------------------------------------------------------------------
# AlphaChipAgent 初始化
# ---------------------------------------------------------------------------


def test_agent_init():
    """Agent 初始化正确。"""
    config = AlphaChipConfig(grid_size=(16, 16))
    agent = AlphaChipAgent(config)
    assert agent.config.grid_size == (16, 16)
    assert agent.encoder is not None
    assert agent.reward is not None
    assert agent.gnn is not None
    assert agent.ppo is not None


def test_agent_default_config():
    """默认配置初始化。"""
    agent = AlphaChipAgent(AlphaChipConfig())
    assert agent.config.grid_size == (32, 32)


# ---------------------------------------------------------------------------
# _build_occupancy_grid
# ---------------------------------------------------------------------------


def test_build_occupancy_grid():
    """占用栅格构建正确。"""
    config = AlphaChipConfig(grid_size=(32, 32))
    agent = AlphaChipAgent(config)
    placement = {"d0": {"x": 0.0, "y": 0.0, "rotation": 0}}
    grid = agent._build_occupancy_grid(placement, _SIMPLE_CIRCUIT)
    assert grid.shape == (32, 32)
    assert grid.dtype == np.float64


def test_build_occupancy_grid_empty():
    """空布局占用栅格全零。"""
    config = AlphaChipConfig(grid_size=(32, 32))
    agent = AlphaChipAgent(config)
    grid = agent._build_occupancy_grid({}, _SIMPLE_CIRCUIT)
    assert grid.sum() == 0.0


# ---------------------------------------------------------------------------
# _build_action_mask
# ---------------------------------------------------------------------------


def test_build_action_mask():
    """动作掩码构建正确。"""
    config = AlphaChipConfig(grid_size=(32, 32))
    agent = AlphaChipAgent(config)
    placement = {"d0": {"x": 0.0, "y": 0.0, "rotation": 0}}
    mask = agent._build_action_mask(placement, _SIMPLE_CIRCUIT)
    assert mask.shape == (32 * 32,)
    assert mask.dtype == np.float64


def test_build_action_mask_unplaced():
    """未放置器件时掩码全 1。"""
    config = AlphaChipConfig(grid_size=(32, 32))
    agent = AlphaChipAgent(config)
    mask = agent._build_action_mask({}, _SIMPLE_CIRCUIT)
    assert np.all(mask == 1.0)


# ---------------------------------------------------------------------------
# _build_state
# ---------------------------------------------------------------------------


def test_build_state():
    """状态构建正确。"""
    config = AlphaChipConfig(grid_size=(32, 32))
    agent = AlphaChipAgent(config)
    placement = {}
    state = agent._build_state(placement, _SIMPLE_CIRCUIT, _SIMPLE_CIRCUIT["devices"][0])
    assert "embedding" in state
    assert "mask" in state
    assert "grid" in state
    assert "graph_emb" in state
    assert "dev_feat" in state


def test_build_state_embedding_shape():
    """状态嵌入维度正确。"""
    config = AlphaChipConfig(grid_size=(32, 32), gnn_hidden=128)
    agent = AlphaChipAgent(config)
    placement = {}
    state = agent._build_state(placement, _SIMPLE_CIRCUIT, _SIMPLE_CIRCUIT["devices"][0])
    # embedding = graph_emb(128) + dev_feat(9) + grid_stats(3) = 140
    assert state["embedding"].shape[0] == 128 + 9 + 3


# ---------------------------------------------------------------------------
# select_action
# ---------------------------------------------------------------------------


def test_select_action_returns_tuple():
    """select_action 返回正确格式。"""
    config = AlphaChipConfig(grid_size=(32, 32))
    agent = AlphaChipAgent(config)
    placement = {}
    state = agent._build_state(placement, _SIMPLE_CIRCUIT, _SIMPLE_CIRCUIT["devices"][0])
    action, logprob, value = agent.select_action(state)
    assert isinstance(action, int)
    assert isinstance(logprob, float)
    assert isinstance(value, float)


def test_select_action_valid_grid_index():
    """选择的动作是有效网格索引。"""
    config = AlphaChipConfig(grid_size=(32, 32))
    agent = AlphaChipAgent(config)
    placement = {}
    state = agent._build_state(placement, _SIMPLE_CIRCUIT, _SIMPLE_CIRCUIT["devices"][0])
    action, _, _ = agent.select_action(state)
    assert 0 <= action < 32 * 32


# ---------------------------------------------------------------------------
# _quantize_action
# ---------------------------------------------------------------------------


def test_quantize_action_in_bounds():
    """量化动作在网格范围内。"""
    config = AlphaChipConfig(grid_size=(32, 32))
    agent = AlphaChipAgent(config)
    mask = np.ones(32 * 32, dtype=np.float64)
    action_cont = np.array([0.5, 0.5], dtype=np.float64)  # sigmoid(0) = 0.5
    action = agent._quantize_action(action_cont, mask)
    assert 0 <= action < 32 * 32


# ---------------------------------------------------------------------------
# _nearest_available
# ---------------------------------------------------------------------------


def test_nearest_available_finds_open_spot():
    """nearest_available 找到最近可用位置。"""
    config = AlphaChipConfig(grid_size=(4, 4))
    agent = AlphaChipAgent(config)
    mask = np.ones(16, dtype=np.float64)
    mask[5] = 0.0  # 位置 5 被占用
    # 从位置 4 开始搜索，最近可用应该是 3 或 6
    result = agent._nearest_available(4, mask)
    assert result in (3, 6)


def test_nearest_available_r03_raises():
    """R03 合规：所有位置占用时抛出 ValueError。"""
    config = AlphaChipConfig(grid_size=(2, 2))
    agent = AlphaChipAgent(config)
    mask = np.zeros(4, dtype=np.float64)  # 所有位置都被占用
    with pytest.raises(ValueError, match="R03 禁止 fall-back"):
        agent._nearest_available(0, mask)


# ---------------------------------------------------------------------------
# compute_reward
# ---------------------------------------------------------------------------


def test_compute_reward():
    """奖励计算正确。"""
    config = AlphaChipConfig(grid_size=(32, 32))
    agent = AlphaChipAgent(config)
    agent.circuit = _SIMPLE_CIRCUIT
    placement = {
        "d0": {"x": 0.0, "y": 0.0, "rotation": 0},
        "d1": {"x": 100.0, "y": 0.0, "rotation": 0},
        "d2": {"x": 200.0, "y": 0.0, "rotation": 0},
    }
    reward = agent.compute_reward(placement)
    assert isinstance(reward, float)


def test_compute_reward_requires_circuit():
    """未设置 circuit 时应抛出错误。"""
    config = AlphaChipConfig(grid_size=(32, 32))
    agent = AlphaChipAgent(config)
    with pytest.raises(AssertionError):
        agent.compute_reward({})


# ---------------------------------------------------------------------------
# place
# ---------------------------------------------------------------------------


def test_place_returns_valid_placement():
    """place 返回有效布局。"""
    config = AlphaChipConfig(grid_size=(32, 32))
    agent = AlphaChipAgent(config)
    placement = agent.place(_SIMPLE_CIRCUIT)
    assert isinstance(placement, dict)
    assert len(placement) == 3  # 3 个器件


def test_place_all_devices_placed():
    """place 放置所有器件。"""
    config = AlphaChipConfig(grid_size=(32, 32))
    agent = AlphaChipAgent(config)
    placement = agent.place(_SIMPLE_CIRCUIT)
    for dev in _SIMPLE_CIRCUIT["devices"]:
        assert dev["id"] in placement


def test_place_coordinates_valid():
    """布局坐标在画布范围内。"""
    config = AlphaChipConfig(grid_size=(32, 32))
    agent = AlphaChipAgent(config)
    placement = agent.place(_SIMPLE_CIRCUIT)
    for dev_id, pos in placement.items():
        assert 0 <= pos["x"] <= 3200.0  # _CANVAS_SIZE = 3200.0
        assert 0 <= pos["y"] <= 3200.0
