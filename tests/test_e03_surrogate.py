"""E03 代理模型验收测试。

验证专家数据集格式、奖励塑形和行为克隆功能。

文献来源:
- Pomerleau, 1989, ALVINN (Behavior Cloning)
  https://papers.nips.cc/paper/95-alvinn-an-autonomous-land-vehicle-in-a-neural-network
- Ross & Bagnell, 2011, DAgger
  https://arxiv.org/abs/1011.0686
- Gao et al., ICLR 2026, Expertise-Enhanced RL
  https://openreview.net/forum?id=yqvNwfxRR6
- Hester et al., 2018, DQfD (Deep Q-learning from Demonstrations)
  https://arxiv.org/abs/1704.03732
- LiDAR ISPD 2025, 弯曲半径约束与交叉惩罚
  https://dl.acm.org/doi/pdf/10.1145/3698364.3705355
"""

import numpy as np

from polaris.trainer.expert_dataset import (
    ACTION_DIM,
    OBS_DIM,
    ExpertDataset,
    _device_type_to_onehot,
    _normalize_placement,
)
from polaris.trainer.reward_shaping import (
    ExpertRewardConfig,
    ExpertRewardInput,
    ExpertRewardResult,
    ExpertRewardShaper,
    _cross2d,
    _lines_cross,
    _port_alignment_score,
    _thermal_penalty,
)


class TestExpertDataset:
    """ExpertDataset 专家数据集测试。"""

    def test_constants(self):
        """M1: 观测/动作维度常量正确。"""
        assert OBS_DIM == 16
        assert ACTION_DIM == 3

    def test_init_empty(self):
        """M1: 空数据集初始化。"""
        ds = ExpertDataset(data_dir="/nonexistent/path")
        assert ds.data_dir is not None
        assert len(ds.obs_list) == 0
        assert len(ds.action_list) == 0
        assert len(ds.meta_list) == 0

    def test_device_type_onehot(self):
        """M1: 器件类型 one-hot 编码。"""
        vec = _device_type_to_onehot("y_branch")
        assert vec.shape == (8,)
        assert np.sum(vec) == 1.0
        assert vec[0] == 1.0

    def test_device_type_unknown(self):
        """M1: 未知器件类型默认 waveguide。"""
        vec = _device_type_to_onehot("unknown_device_xyz")
        assert vec.shape == (8,)
        assert vec[7] == 1.0

    def test_normalize_placement(self):
        """M1: 放置归一化到 [0, 1]。"""
        place = {"x": 500.0, "y": 300.0, "rotation": 90.0}
        norm = _normalize_placement(place, canvas_w=1000.0, canvas_h=1000.0)
        assert norm.shape == (3,)
        assert 0.0 <= norm[0] <= 1.0
        assert 0.0 <= norm[1] <= 1.0
        assert 0.0 <= norm[2] <= 1.0

    def test_normalize_placement_clipped(self):
        """M1: 归一化值被裁剪到 [0, 1]。"""
        place = {"x": 2000.0, "y": -100.0, "rotation": 360.0}
        norm = _normalize_placement(place, canvas_w=1000.0, canvas_h=1000.0)
        assert 0.0 <= norm[0] <= 1.0
        assert 0.0 <= norm[1] <= 1.0
        assert 0.0 <= norm[2] <= 1.0

    def test_load_nonexistent_dir(self):
        """R03: 不存在的数据目录不报错。"""
        ds = ExpertDataset(data_dir="/nonexistent/path_12345")
        ds.load()
        assert len(ds) == 0

    def test_get_all_empty(self):
        """M1: 空数据集 get_all 返回零数组。"""
        ds = ExpertDataset(data_dir="/nonexistent")
        obs, actions = ds.get_all()
        assert obs.shape == (0, OBS_DIM)
        assert actions.shape == (0, ACTION_DIM)

    def test_iter_batches_empty(self):
        """M1: 空数据集 iter_batches 不产生批次。"""
        ds = ExpertDataset(data_dir="/nonexistent")
        batches = list(ds.iter_batches(batch_size=32))
        assert len(batches) == 0

    def test_len_before_load(self):
        """M1: len 触发自动加载。"""
        ds = ExpertDataset(data_dir="/nonexistent")
        n = len(ds)
        assert n == 0


class TestExpertRewardConfig:
    """ExpertRewardConfig 奖励配置测试。"""

    def test_default_weights(self):
        """M1: 默认权重来自 ICLR'26 论文。"""
        cfg = ExpertRewardConfig()
        assert cfg.port_alignment_weight == 0.3
        assert cfg.bend_violation_weight == 0.5
        assert cfg.crossing_weight == 0.2
        assert cfg.congestion_weight == 0.2
        assert cfg.thermal_weight == 0.1

    def test_default_geometry(self):
        """M1: 默认几何参数来自 SiEPIC PDK。"""
        cfg = ExpertRewardConfig()
        assert cfg.min_bend_radius_um == 5.0
        assert cfg.min_spacing_um == 1.0

    def test_custom_config(self):
        """M1: 自定义配置参数。"""
        cfg = ExpertRewardConfig(port_alignment_weight=0.5, min_bend_radius_um=10.0)
        assert cfg.port_alignment_weight == 0.5
        assert cfg.min_bend_radius_um == 10.0


class TestPortAlignment:
    """端口对齐评分测试。"""

    def test_perfect_horizontal_alignment(self):
        """M2: 水平对齐得分为 1。"""
        positions = {"d1": (0.0, 0.0), "d2": (100.0, 0.0)}
        connections = [("d1", "p1", "d2", "p2")]
        score = _port_alignment_score(positions, connections)
        assert score == 1.0

    def test_perfect_vertical_alignment(self):
        """M2: 垂直对齐得分为 1。"""
        positions = {"d1": (0.0, 0.0), "d2": (0.0, 100.0)}
        connections = [("d1", "p1", "d2", "p2")]
        score = _port_alignment_score(positions, connections)
        assert score == 1.0

    def test_diagonal_alignment(self):
        """M2: 45度对角线对齐得分为 ~0.707。"""
        positions = {"d1": (0.0, 0.0), "d2": (100.0, 100.0)}
        connections = [("d1", "p1", "d2", "p2")]
        score = _port_alignment_score(positions, connections)
        assert 0.7 < score < 0.72

    def test_empty_connections(self):
        """M2: 空连接得分为 1。"""
        score = _port_alignment_score({}, [])
        assert score == 1.0

    def test_missing_device(self):
        """M2: 缺失器件时跳过该连接，得分按总连接数平均。"""
        positions = {"d1": (0.0, 0.0)}
        connections = [("d1", "p1", "d_missing", "p2")]
        score = _port_alignment_score(positions, connections)
        assert score == 0.0


class TestLineCrossing:
    """线段交叉检测测试。"""

    def test_crossing_lines(self):
        """M2: 交叉线段返回 True。"""
        seg1 = ((0.0, 0.0), (10.0, 10.0))
        seg2 = ((0.0, 10.0), (10.0, 0.0))
        assert _lines_cross(seg1, seg2)

    def test_non_crossing_parallel(self):
        """M2: 平行线段返回 False。"""
        seg1 = ((0.0, 0.0), (10.0, 0.0))
        seg2 = ((0.0, 5.0), (10.0, 5.0))
        assert not _lines_cross(seg1, seg2)

    def test_non_crossing_disjoint(self):
        """M2: 不相交线段返回 False。"""
        seg1 = ((0.0, 0.0), (5.0, 5.0))
        seg2 = ((10.0, 10.0), (15.0, 15.0))
        assert not _lines_cross(seg1, seg2)

    def test_cross2d_sign(self):
        """M2: cross2d 返回正确符号。"""
        o = (0.0, 0.0)
        a = (1.0, 0.0)
        b = (0.0, 1.0)
        assert _cross2d(o, a, b) > 0
        assert _cross2d(o, b, a) < 0


class TestThermalPenalty:
    """热串扰惩罚测试。"""

    def test_no_sources(self):
        """M2: 无热源时惩罚为 0。"""
        positions = {"d1": (0.0, 0.0), "d2": (10.0, 10.0)}
        penalty = _thermal_penalty(positions, set(), {"d2"})
        assert penalty == 0.0

    def test_no_sensitive(self):
        """M2: 热敏感器件时惩罚为 0。"""
        positions = {"d1": (0.0, 0.0), "d2": (10.0, 10.0)}
        penalty = _thermal_penalty(positions, {"d1"}, set())
        assert penalty == 0.0

    def test_close_thermal_violation(self):
        """M2: 近距离热串扰惩罚为 1。"""
        positions = {"src": (0.0, 0.0), "sens": (10.0, 0.0)}
        penalty = _thermal_penalty(positions, {"src"}, {"sens"}, safe_distance_um=100.0)
        assert penalty == 1.0

    def test_far_thermal_safe(self):
        """M2: 远距离无热串扰惩罚为 0。"""
        positions = {"src": (0.0, 0.0), "sens": (200.0, 0.0)}
        penalty = _thermal_penalty(positions, {"src"}, {"sens"}, safe_distance_um=100.0)
        assert penalty == 0.0


class TestExpertRewardShaper:
    """ExpertRewardShaper 奖励塑形器测试。"""

    def test_init_default(self):
        """M1: 默认初始化成功。"""
        shaper = ExpertRewardShaper()
        assert isinstance(shaper.config, ExpertRewardConfig)

    def test_compute_returns_result(self):
        """M1: compute 返回 ExpertRewardResult。"""
        shaper = ExpertRewardShaper()
        positions = {"d1": (0.0, 0.0), "d2": (100.0, 0.0)}
        connections = [("d1", "p1", "d2", "p2")]
        reward_input = ExpertRewardInput(
            device_positions=positions,
            connections=connections,
        )
        result = shaper.compute(reward_input)
        assert isinstance(result, ExpertRewardResult)
        assert isinstance(result.total_expert_reward, float)

    def test_compute_all_components(self):
        """M2: 所有奖励分量都被计算。"""
        shaper = ExpertRewardShaper()
        positions = {"d1": (0.0, 0.0), "d2": (50.0, 50.0), "d3": (100.0, 0.0)}
        connections = [
            ("d1", "p1", "d2", "p2"),
            ("d2", "p1", "d3", "p2"),
        ]
        congestion = np.random.rand(10, 10)
        reward_input = ExpertRewardInput(
            device_positions=positions,
            connections=connections,
            congestion_map=congestion,
            thermal_sources={"d1"},
            thermal_sensitive={"d3"},
        )
        result = shaper.compute(reward_input)
        assert result.port_alignment_reward >= 0.0
        assert result.bend_penalty >= 0.0
        assert result.crossing_penalty >= 0.0
        assert result.congestion_penalty >= 0.0
        assert result.thermal_penalty >= 0.0

    def test_reward_result_fields(self):
        """M1: ExpertRewardResult 包含所有字段。"""
        result = ExpertRewardResult(
            total_expert_reward=0.5,
            port_alignment_reward=0.8,
            bend_penalty=0.2,
            crossing_penalty=0.1,
            congestion_penalty=0.3,
            thermal_penalty=0.0,
        )
        assert result.total_expert_reward == 0.5
        assert result.port_alignment_reward == 0.8
        assert result.bend_penalty == 0.2


class TestExpertRewardInput:
    """ExpertRewardInput 输入测试。"""

    def test_minimal_input(self):
        """M1: 最小输入（仅位置和连接）。"""
        ri = ExpertRewardInput(
            device_positions={"d1": (0.0, 0.0)},
            connections=[],
        )
        assert ri.congestion_map is None
        assert ri.thermal_sources is None
        assert ri.thermal_sensitive is None

    def test_full_input(self):
        """M1: 完整输入（含拥塞和热信息）。"""
        ri = ExpertRewardInput(
            device_positions={"d1": (0.0, 0.0)},
            connections=[],
            congestion_map=np.zeros((5, 5)),
            thermal_sources={"d1"},
            thermal_sensitive=set(),
        )
        assert ri.congestion_map is not None
        assert ri.thermal_sources == {"d1"}


class TestRewardShapingIntegration:
    """奖励塑形集成测试。"""

    def test_better_alignment_higher_reward(self):
        """M2: 对齐更好的布局获得更高奖励。"""
        shaper = ExpertRewardShaper()
        positions_good = {"d1": (0.0, 0.0), "d2": (100.0, 0.0)}
        positions_bad = {"d1": (0.0, 0.0), "d2": (100.0, 100.0)}
        connections = [("d1", "p1", "d2", "p2")]

        reward_good = shaper.compute(ExpertRewardInput(positions_good, connections)).total_expert_reward
        reward_bad = shaper.compute(ExpertRewardInput(positions_bad, connections)).total_expert_reward
        assert reward_good > reward_bad

    def test_more_crossings_lower_reward(self):
        """M2: 交叉更多的布局获得更低奖励。"""
        shaper = ExpertRewardShaper()
        positions = {
            "d1": (0.0, 0.0), "d2": (100.0, 100.0),
            "d3": (0.0, 100.0), "d4": (100.0, 0.0),
        }
        connections_cross = [("d1", "p1", "d2", "p2"), ("d3", "p1", "d4", "p2")]
        connections_nocross = [("d1", "p1", "d4", "p2"), ("d2", "p1", "d3", "p2")]

        reward_cross = shaper.compute(ExpertRewardInput(positions, connections_cross)).total_expert_reward
        reward_nocross = shaper.compute(ExpertRewardInput(positions, connections_nocross)).total_expert_reward
        assert reward_nocross >= reward_cross
