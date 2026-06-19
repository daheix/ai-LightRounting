"""专家知识奖励塑形测试（Task P1）。

覆盖 ``src/polaris/trainer/reward_shaping.py`` 的：
- ExpertRewardConfig / ExpertRewardInput / ExpertRewardResult 数据类
- ExpertRewardShaper.compute 主入口
- _port_alignment_score（端口对齐评分）
- _bend_violation_penalty（弯曲违规惩罚）
- _crossing_penalty_estimate + _lines_cross + _cross2d（交叉检测）
- _thermal_penalty（热串扰惩罚）
- 加权求和符号与权重正确性

来源:
- ICLR'26 Expertise-Enhanced RL: https://openreview.net/forum?id=yqvNwfxRR6
- LiDAR ISPD'25: https://dl.acm.org/doi/pdf/10.1145/3698364.3705355
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from polaris.trainer.reward_shaping import (
    ExpertRewardConfig,
    ExpertRewardInput,
    ExpertRewardResult,
    ExpertRewardShaper,
    _bend_violation_penalty,
    _cross2d,
    _crossing_penalty_estimate,
    _lines_cross,
    _port_alignment_score,
    _thermal_penalty,
)

# ---------------------------------------------------------------------------
# 数据类
# ---------------------------------------------------------------------------


def test_expert_reward_config_defaults():
    cfg = ExpertRewardConfig()
    assert cfg.port_alignment_weight == 0.3
    assert cfg.bend_violation_weight == 0.5
    assert cfg.crossing_weight == 0.2
    assert cfg.congestion_weight == 0.2
    assert cfg.thermal_weight == 0.1
    assert cfg.min_bend_radius_um == 5.0
    assert cfg.min_spacing_um == 1.0


def test_expert_reward_input_construction():
    inp = ExpertRewardInput(
        device_positions={"a": (0.0, 0.0)},
        connections=[("a", "p1", "a", "p2")],
    )
    assert inp.congestion_map is None
    assert inp.thermal_sources is None
    assert inp.thermal_sensitive is None


def test_expert_reward_result_defaults():
    r = ExpertRewardResult()
    assert r.total_expert_reward == 0.0
    assert r.port_alignment_reward == 0.0
    assert r.bend_penalty == 0.0
    assert r.crossing_penalty == 0.0
    assert r.congestion_penalty == 0.0
    assert r.thermal_penalty == 0.0


# ---------------------------------------------------------------------------
# _port_alignment_score
# ---------------------------------------------------------------------------


def test_port_alignment_empty_connections():
    """无连接时应返回 1.0（默认最佳）。"""
    score = _port_alignment_score({"a": (0.0, 0.0)}, [])
    assert score == 1.0


def test_port_alignment_horizontal():
    """水平对齐的连接评分应为 1.0。"""
    positions = {"a": (0.0, 0.0), "b": (10.0, 0.0)}
    connections = [("a", "p1", "b", "p2")]
    score = _port_alignment_score(positions, connections)
    assert score == pytest.approx(1.0)


def test_port_alignment_vertical():
    """垂直对齐的连接评分应为 1.0。"""
    positions = {"a": (0.0, 0.0), "b": (0.0, 10.0)}
    connections = [("a", "p1", "b", "p2")]
    score = _port_alignment_score(positions, connections)
    assert score == pytest.approx(1.0)


def test_port_alignment_diagonal():
    """45 度对角连接评分应为 0.7071（1/√2）。"""
    positions = {"a": (0.0, 0.0), "b": (10.0, 10.0)}
    connections = [("a", "p1", "b", "p2")]
    score = _port_alignment_score(positions, connections)
    assert score == pytest.approx(math.sqrt(2) / 2, rel=1e-4)


def test_port_alignment_same_position():
    """两器件同位置时应返回 1.0（避免除零）。"""
    positions = {"a": (5.0, 5.0), "b": (5.0, 5.0)}
    connections = [("a", "p1", "b", "p2")]
    score = _port_alignment_score(positions, connections)
    assert score == 1.0


def test_port_alignment_missing_device():
    """连接中含未知器件时应跳过该连接。"""
    positions = {"a": (0.0, 0.0)}
    connections = [("a", "p1", "b", "p2")]  # b 不存在
    score = _port_alignment_score(positions, connections)
    # 跳过后 alignment_sum=0, 但分母仍是 len(connections)=1
    assert score == 0.0


# ---------------------------------------------------------------------------
# _bend_violation_penalty
# ---------------------------------------------------------------------------


def test_bend_violation_empty_connections():
    assert _bend_violation_penalty({"a": (0.0, 0.0)}, [], 5.0) == 0.0


def test_bend_violation_aligned_no_violation():
    """水平/垂直对齐无需转弯，惩罚为 0。"""
    positions = {"a": (0.0, 0.0), "b": (100.0, 0.0)}
    connections = [("a", "p1", "b", "p2")]
    pen = _bend_violation_penalty(positions, connections, min_bend_radius=5.0)
    assert pen == 0.0


def test_bend_violation_short_diagonal_triggers():
    """短对角连接（短边 < π/2 * R）应触发惩罚。"""
    positions = {"a": (0.0, 0.0), "b": (1.0, 1.0)}
    connections = [("a", "p1", "b", "p2")]
    pen = _bend_violation_penalty(positions, connections, min_bend_radius=5.0)
    # min_side=1.0, required=π/2*5≈7.85, 1<7.85 → 违规
    assert pen == 1.0


def test_bend_violation_long_diagonal_no_violation():
    """长对角连接（短边 > π/2 * R）不应触发惩罚。"""
    positions = {"a": (0.0, 0.0), "b": (100.0, 100.0)}
    connections = [("a", "p1", "b", "p2")]
    pen = _bend_violation_penalty(positions, connections, min_bend_radius=5.0)
    # min_side=100, required≈7.85, 100>7.85 → 无违规
    assert pen == 0.0


# ---------------------------------------------------------------------------
# _lines_cross / _cross2d / _crossing_penalty_estimate
# ---------------------------------------------------------------------------


def test_cross2d_basic():
    """叉积基本计算。"""
    # (1,0) × (0,1) = 1*1 - 0*0 = 1
    assert _cross2d((0.0, 0.0), (1.0, 0.0), (0.0, 1.0)) == 1.0
    # (0,1) × (1,0) = 0*0 - 1*1 = -1
    assert _cross2d((0.0, 0.0), (0.0, 1.0), (1.0, 0.0)) == -1.0


def test_lines_cross_intersecting():
    """两条相交线段应返回 True。"""
    seg1 = ((0.0, 0.0), (10.0, 10.0))
    seg2 = ((0.0, 10.0), (10.0, 0.0))
    assert _lines_cross(seg1, seg2) is True


def test_lines_cross_parallel():
    """平行线段应返回 False。"""
    seg1 = ((0.0, 0.0), (10.0, 0.0))
    seg2 = ((0.0, 5.0), (10.0, 5.0))
    assert _lines_cross(seg1, seg2) is False


def test_lines_cross_disjoint():
    """不相交的线段应返回 False。"""
    seg1 = ((0.0, 0.0), (1.0, 1.0))
    seg2 = ((5.0, 5.0), (6.0, 6.0))
    assert _lines_cross(seg1, seg2) is False


def test_crossing_penalty_empty():
    """无连接时惩罚为 0。"""
    assert _crossing_penalty_estimate({"a": (0.0, 0.0)}, []) == 0.0


def test_crossing_penalty_single_connection():
    """单条连接无法交叉，惩罚为 0。"""
    positions = {"a": (0.0, 0.0), "b": (10.0, 10.0)}
    connections = [("a", "p1", "b", "p2")]
    assert _crossing_penalty_estimate(positions, connections) == 0.0


def test_crossing_penalty_two_crossing_connections():
    """两条相交连接应产生非零惩罚。"""
    positions = {
        "a": (0.0, 0.0),
        "b": (10.0, 10.0),
        "c": (0.0, 10.0),
        "d": (10.0, 0.0),
    }
    connections = [
        ("a", "p1", "b", "p2"),
        ("c", "p1", "d", "p2"),
    ]
    pen = _crossing_penalty_estimate(positions, connections)
    # 1 交叉 / 1 最大对 = 1.0
    assert pen == pytest.approx(1.0)


def test_crossing_penalty_two_non_crossing_connections():
    """两条不相交的连接惩罚为 0。"""
    positions = {
        "a": (0.0, 0.0),
        "b": (10.0, 0.0),
        "c": (0.0, 10.0),
        "d": (10.0, 10.0),
    }
    connections = [
        ("a", "p1", "b", "p2"),
        ("c", "p1", "d", "p2"),
    ]
    pen = _crossing_penalty_estimate(positions, connections)
    assert pen == 0.0


# ---------------------------------------------------------------------------
# _thermal_penalty
# ---------------------------------------------------------------------------


def test_thermal_penalty_no_sources():
    """无热源时惩罚为 0。"""
    positions = {"a": (0.0, 0.0), "b": (10.0, 0.0)}
    assert _thermal_penalty(positions, set(), {"b"}) == 0.0


def test_thermal_penalty_no_sensitive():
    """无热敏感器件时惩罚为 0。"""
    positions = {"a": (0.0, 0.0), "b": (10.0, 0.0)}
    assert _thermal_penalty(positions, {"a"}, set()) == 0.0


def test_thermal_penalty_close_violation():
    """热源与热敏感器件距离 < safe_distance 应触发惩罚。"""
    positions = {"heater": (0.0, 0.0), "ring": (10.0, 0.0)}
    pen = _thermal_penalty(
        positions,
        {"heater"},
        {"ring"},
        safe_distance_um=100.0,
    )
    # 距离=10 < 100 → 违规
    assert pen == 1.0


def test_thermal_penalty_far_no_violation():
    """热源与热敏感器件距离 >= safe_distance 不应触发惩罚。"""
    positions = {"heater": (0.0, 0.0), "ring": (200.0, 0.0)}
    pen = _thermal_penalty(
        positions,
        {"heater"},
        {"ring"},
        safe_distance_um=100.0,
    )
    assert pen == 0.0


# ---------------------------------------------------------------------------
# ExpertRewardShaper.compute
# ---------------------------------------------------------------------------


def test_shaper_compute_basic():
    """compute 应返回包含所有分量的 ExpertRewardResult。"""
    shaper = ExpertRewardShaper()
    inp = ExpertRewardInput(
        device_positions={"a": (0.0, 0.0), "b": (100.0, 0.0)},
        connections=[("a", "p1", "b", "p2")],
    )
    result = shaper.compute(inp)
    assert isinstance(result, ExpertRewardResult)
    # 水平对齐 → port_alignment_reward=1.0
    assert result.port_alignment_reward == pytest.approx(1.0)
    # 对齐 → 无弯曲违规
    assert result.bend_penalty == 0.0
    # 单连接 → 无交叉
    assert result.crossing_penalty == 0.0
    # 无拥塞图 → 拥塞惩罚为 0
    assert result.congestion_penalty == 0.0
    # 无热源 → 热惩罚为 0
    assert result.thermal_penalty == 0.0
    # total = 0.3*1 - 0.5*0 - 0.2*0 - 0.2*0 - 0.1*0 = 0.3
    assert result.total_expert_reward == pytest.approx(0.3)


def test_shaper_compute_with_congestion():
    """提供 congestion_map 时拥塞惩罚应为均值。"""
    shaper = ExpertRewardShaper()
    cong_map = np.array([[0.5, 0.5], [0.5, 0.5]])
    inp = ExpertRewardInput(
        device_positions={"a": (0.0, 0.0), "b": (100.0, 0.0)},
        connections=[("a", "p1", "b", "p2")],
        congestion_map=cong_map,
    )
    result = shaper.compute(inp)
    assert result.congestion_penalty == pytest.approx(0.5)
    # total = 0.3*1 - 0.2*0.5 = 0.2
    assert result.total_expert_reward == pytest.approx(0.2)


def test_shaper_compute_with_thermal():
    """提供热源+热敏感时应计算热惩罚。"""
    shaper = ExpertRewardShaper()
    inp = ExpertRewardInput(
        device_positions={"heater": (0.0, 0.0), "ring": (10.0, 0.0)},
        connections=[],
        thermal_sources={"heater"},
        thermal_sensitive={"ring"},
    )
    result = shaper.compute(inp)
    # 距离=10 < 100 → 热惩罚=1.0
    assert result.thermal_penalty == 1.0
    # 无连接 → port_alignment=1.0, bend=0, cross=0, cong=0
    # total = 0.3*1 - 0.1*1 = 0.2
    assert result.total_expert_reward == pytest.approx(0.2)


def test_shaper_compute_all_penalties():
    """所有惩罚同时存在时 total 应正确加权。"""
    cfg = ExpertRewardConfig(
        port_alignment_weight=0.3,
        bend_violation_weight=0.5,
        crossing_weight=0.2,
        congestion_weight=0.2,
        thermal_weight=0.1,
        min_bend_radius_um=5.0,
    )
    shaper = ExpertRewardShaper(cfg)
    # 构造一个所有惩罚都触发的场景
    positions = {
        "a": (0.0, 0.0),
        "b": (1.0, 1.0),  # 短对角 → 弯曲违规
        "c": (0.0, 1.0),
        "d": (1.0, 0.0),
        "heater": (0.0, 0.0),
        "ring": (1.0, 0.0),
    }
    connections = [
        ("a", "p1", "b", "p2"),  # 与 c-d 交叉
        ("c", "p1", "d", "p2"),
    ]
    cong_map = np.array([[0.8]])
    inp = ExpertRewardInput(
        device_positions=positions,
        connections=connections,
        congestion_map=cong_map,
        thermal_sources={"heater"},
        thermal_sensitive={"ring"},
    )
    result = shaper.compute(inp)
    # 各分量应非零（除可能的对齐）
    assert result.bend_penalty > 0
    assert result.crossing_penalty > 0
    assert result.congestion_penalty == pytest.approx(0.8)
    assert result.thermal_penalty > 0
    # total = 0.3*port - 0.5*bend - 0.2*cross - 0.2*0.8 - 0.1*thermal
    expected = (
        cfg.port_alignment_weight * result.port_alignment_reward
        - cfg.bend_violation_weight * result.bend_penalty
        - cfg.crossing_weight * result.crossing_penalty
        - cfg.congestion_weight * result.congestion_penalty
        - cfg.thermal_weight * result.thermal_penalty
    )
    assert result.total_expert_reward == pytest.approx(expected)


def test_shaper_compute_custom_config():
    """自定义配置应被使用。"""
    cfg = ExpertRewardConfig(
        port_alignment_weight=1.0,
        bend_violation_weight=0.0,
        crossing_weight=0.0,
        congestion_weight=0.0,
        thermal_weight=0.0,
    )
    shaper = ExpertRewardShaper(cfg)
    inp = ExpertRewardInput(
        device_positions={"a": (0.0, 0.0), "b": (100.0, 0.0)},
        connections=[("a", "p1", "b", "p2")],
    )
    result = shaper.compute(inp)
    # total = 1.0 * 1.0 = 1.0
    assert result.total_expert_reward == pytest.approx(1.0)
