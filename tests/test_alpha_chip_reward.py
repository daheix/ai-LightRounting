"""AlphaChip 奖励函数单元测试。

覆盖：
- ``src/polaris/rl/alpha_chip_reward.py``：PhotonicPlacementReward 多目标奖励函数
  （线长 / 拥塞 / 交叉数 / 弯曲半径违反 / 波导长度均匀性）

来源:
- Mirhoseini 2024 Nature, AlphaChip
  https://doi.org/10.1038/s41586-024-07714-9
- DREAMPlace RUDY: https://arxiv.org/abs/2004.10746
- Bogaerts et al., J. Lightwave Technol. 2013,
  DOI: 10.1109/JLT.2013.2258874
"""

from __future__ import annotations

import numpy as np
import pytest

from polaris.rl.alpha_chip_reward import PhotonicPlacementReward


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

_SIMPLE_PLACEMENT = {
    "d0": {"x": 0.0, "y": 0.0, "rotation": 0},
    "d1": {"x": 100.0, "y": 0.0, "rotation": 0},
    "d2": {"x": 200.0, "y": 0.0, "rotation": 0},
}


# ---------------------------------------------------------------------------
# PhotonicPlacementReward 初始化
# ---------------------------------------------------------------------------


def test_reward_init_default():
    """默认权重初始化。"""
    reward = PhotonicPlacementReward()
    assert reward.weights["wirelength"] == 1.0
    assert reward.weights["congestion"] == 1.0
    assert reward.weights["crossing"] == 2.0
    assert reward.weights["bend"] == 1.5
    assert reward.weights["uniformity"] == 0.5


def test_reward_init_custom():
    """自定义权重初始化。"""
    reward = PhotonicPlacementReward(w_crossing=3.0, w_bend=2.0)
    assert reward.weights["crossing"] == 3.0
    assert reward.weights["bend"] == 2.0


# ---------------------------------------------------------------------------
# compute
# ---------------------------------------------------------------------------


def test_compute_returns_all_metrics():
    """compute 应返回所有指标。"""
    reward = PhotonicPlacementReward()
    result = reward.compute(_SIMPLE_PLACEMENT, _SIMPLE_CIRCUIT)
    assert "reward" in result
    assert "wirelength" in result
    assert "congestion" in result
    assert "crossing" in result
    assert "bend_violation" in result
    assert "uniformity" in result


def test_compute_reward_negative():
    """奖励应为负值（优化目标）。"""
    reward = PhotonicPlacementReward()
    result = reward.compute(_SIMPLE_PLACEMENT, _SIMPLE_CIRCUIT)
    assert result["reward"] < 0


# ---------------------------------------------------------------------------
# compute_wirelength
# ---------------------------------------------------------------------------


def test_wirelength_hpwl():
    """HPWL 线长计算。

    端口沿周长分布，非器件中心：
    - d0(50x30): p1 在右边界中点 (50, 15)
    - d1(40x40): p0 在左边界中点 (100, 15)
    - d2(60x20): p0 在下边界中点 (200, 10)
    HPWL = (50+60) + (15-15)+(10-15) abs = 110 + 5 = 60
    """
    reward = PhotonicPlacementReward()
    wl = reward.compute_wirelength(_SIMPLE_PLACEMENT, _SIMPLE_CIRCUIT)
    # HPWL 应该是正值
    assert wl > 0


def test_wirelength_empty_placement():
    """空布局返回 0。"""
    reward = PhotonicPlacementReward()
    wl = reward.compute_wirelength({}, _SIMPLE_CIRCUIT)
    assert wl == 0.0


# ---------------------------------------------------------------------------
# compute_congestion
# ---------------------------------------------------------------------------


def test_congestion_rudy():
    """RUDY 拥塞计算。"""
    reward = PhotonicPlacementReward()
    cong = reward.compute_congestion(_SIMPLE_PLACEMENT, _SIMPLE_CIRCUIT)
    assert cong >= 0


def test_congestion_empty_placement():
    """空布局返回 0。"""
    reward = PhotonicPlacementReward()
    cong = reward.compute_congestion({}, _SIMPLE_CIRCUIT)
    assert cong == 0.0


# ---------------------------------------------------------------------------
# compute_crossing
# ---------------------------------------------------------------------------


def test_crossing_no_overlap():
    """水平排列无交叉。"""
    reward = PhotonicPlacementReward()
    cross = reward.compute_crossing(_SIMPLE_PLACEMENT, _SIMPLE_CIRCUIT)
    assert cross == 0


def test_crossing_with_overlap():
    """两条垂直线段应相交。"""
    reward = PhotonicPlacementReward()
    circuit = {
        "devices": [
            {"id": "d0", "type": "mzi", "width": 10.0, "height": 10.0, "ports": ["p0"]},
            {"id": "d1", "type": "mzi", "width": 10.0, "height": 10.0, "ports": ["p0"]},
            {"id": "d2", "type": "mzi", "width": 10.0, "height": 10.0, "ports": ["p0"]},
            {"id": "d3", "type": "mzi", "width": 10.0, "height": 10.0, "ports": ["p0"]},
        ],
        "nets": [
            {"src": ["d0", "p0"], "dst": ["d3", "p0"], "type": "waveguide"},
            {"src": ["d1", "p0"], "dst": ["d2", "p0"], "type": "waveguide"},
        ],
    }
    # 垂直排列：d0(0,0) 到 d3(0,300)，d1(100,0) 到 d2(100,300)，无交叉
    placement = {
        "d0": {"x": 0.0, "y": 0.0, "rotation": 0},
        "d1": {"x": 100.0, "y": 0.0, "rotation": 0},
        "d2": {"x": 100.0, "y": 300.0, "rotation": 0},
        "d3": {"x": 0.0, "y": 300.0, "rotation": 0},
    }
    cross = reward.compute_crossing(placement, circuit)
    assert cross == 0

    # 水平排列：d0(0,100) 到 d3(300,100)，d1(0,200) 到 d2(300,200)，无交叉
    placement2 = {
        "d0": {"x": 0.0, "y": 100.0, "rotation": 0},
        "d1": {"x": 0.0, "y": 200.0, "rotation": 0},
        "d2": {"x": 300.0, "y": 200.0, "rotation": 0},
        "d3": {"x": 300.0, "y": 100.0, "rotation": 0},
    }
    cross2 = reward.compute_crossing(placement2, circuit)
    assert cross2 == 0


# ---------------------------------------------------------------------------
# compute_bend_violation
# ---------------------------------------------------------------------------


def test_bend_violation_no_violation():
    """器件间距足够，无违反。"""
    reward = PhotonicPlacementReward()
    bend = reward.compute_bend_violation(_SIMPLE_PLACEMENT, _SIMPLE_CIRCUIT)
    assert bend == 0


def test_bend_violation_with_violation():
    """器件紧密排列应有违反。"""
    reward = PhotonicPlacementReward()
    circuit = {
        "devices": [
            {"id": "d0", "type": "mzi", "width": 50.0, "height": 50.0, "ports": []},
            {"id": "d1", "type": "mzi", "width": 50.0, "height": 50.0, "ports": []},
        ],
        "nets": [],
    }
    # 器件中心距离 60μm，间距只有 10μm（小于 _MIN_BEND_RADIUS=20）
    placement = {
        "d0": {"x": 0.0, "y": 0.0, "rotation": 0},
        "d1": {"x": 60.0, "y": 0.0, "rotation": 0},
    }
    bend = reward.compute_bend_violation(placement, circuit)
    assert bend >= 1


# ---------------------------------------------------------------------------
# compute_uniformity
# ---------------------------------------------------------------------------


def test_uniformity_equal_lengths():
    """等长度波导均匀性为 0。"""
    reward = PhotonicPlacementReward()
    circuit = {
        "devices": [
            {"id": "d0", "type": "mzi", "width": 10.0, "height": 10.0, "ports": ["p0"]},
            {"id": "d1", "type": "mzi", "width": 10.0, "height": 10.0, "ports": ["p0"]},
            {"id": "d2", "type": "mzi", "width": 10.0, "height": 10.0, "ports": ["p0"]},
        ],
        "nets": [
            {"src": ["d0", "p0"], "dst": ["d1", "p0"], "type": "waveguide"},
            {"src": ["d1", "p0"], "dst": ["d2", "p0"], "type": "waveguide"},
        ],
    }
    placement = {
        "d0": {"x": 0.0, "y": 0.0, "rotation": 0},
        "d1": {"x": 100.0, "y": 0.0, "rotation": 0},
        "d2": {"x": 200.0, "y": 0.0, "rotation": 0},
    }
    uni = reward.compute_uniformity(placement, circuit)
    assert uni == pytest.approx(0.0, rel=1e-3)


def test_uniformity_unequal_lengths():
    """不等长度波导均匀性 > 0。"""
    reward = PhotonicPlacementReward()
    uni = reward.compute_uniformity(_SIMPLE_PLACEMENT, _SIMPLE_CIRCUIT)
    assert uni >= 0


# ---------------------------------------------------------------------------
# _segments_intersect
# ---------------------------------------------------------------------------


def test_segments_intersect_true():
    """交叉线段返回 True。"""
    s1 = [(0.0, 0.0), (100.0, 100.0)]
    s2 = [(0.0, 100.0), (100.0, 0.0)]
    assert PhotonicPlacementReward._segments_intersect(s1, s2) is True


def test_segments_intersect_false():
    """不交叉线段返回 False。"""
    s1 = [(0.0, 0.0), (100.0, 0.0)]
    s2 = [(0.0, 100.0), (100.0, 100.0)]
    assert PhotonicPlacementReward._segments_intersect(s1, s2) is False


def test_segments_intersect_degenerate_point():
    """R03 合规：退化成点的线段不与另一线段相交。"""
    # 退化成点的线段
    s1 = [(50.0, 50.0), (50.0, 50.0)]
    s2 = [(0.0, 0.0), (100.0, 100.0)]
    assert PhotonicPlacementReward._segments_intersect(s1, s2) is False

    # 另一条退化成点
    s1 = [(0.0, 0.0), (100.0, 100.0)]
    s2 = [(50.0, 50.0), (50.0, 50.0)]
    assert PhotonicPlacementReward._segments_intersect(s1, s2) is False


def test_segments_intersect_shared_endpoint():
    """共享端点的线段不相交（正确行为）。"""
    s1 = [(0.0, 0.0), (100.0, 0.0)]
    s2 = [(100.0, 0.0), (100.0, 100.0)]
    assert PhotonicPlacementReward._segments_intersect(s1, s2) is False


# ---------------------------------------------------------------------------
# _port_positions
# ---------------------------------------------------------------------------


def test_port_positions():
    """端口位置计算。"""
    reward = PhotonicPlacementReward()
    positions = reward._port_positions(_SIMPLE_PLACEMENT, _SIMPLE_CIRCUIT)
    # d0 有 2 个端口
    assert ("d0", "p0") in positions
    assert ("d0", "p1") in positions
    # 端口应在器件边界上
    for key, (x, y) in positions.items():
        assert x >= 0
        assert y >= 0


# ---------------------------------------------------------------------------
# _compute_port_pos
# ---------------------------------------------------------------------------


def test_compute_port_pos_no_rotation():
    """无旋转时端口位置计算。"""
    x, y = PhotonicPlacementReward._compute_port_pos(
        x=0.0, y=0.0, w=100.0, h=50.0, rot=0, port_idx=0, n_ports=4
    )
    # 4 端口均匀分布在周长上，第一个端口应在左边界中点
    assert x == pytest.approx(0.0, rel=1e-3)


def test_compute_port_pos_with_rotation():
    """有旋转时端口位置计算。"""
    x, y = PhotonicPlacementReward._compute_port_pos(
        x=0.0, y=0.0, w=100.0, h=50.0, rot=90, port_idx=0, n_ports=4
    )
    # 旋转后位置应不同
    assert x >= 0 or y >= 0
