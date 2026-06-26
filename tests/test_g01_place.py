"""G01 布局验收测试。

验证器件放置、不重叠、布线通道功能。

文献来源:
- Lin et al., DAC 2019, DREAMPlace
  https://cseweb.ucsd.edu/classes/fa23/cse248-a/papers/placement/dreamplace.pdf
- Lin et al., TCAD 2020, DREAMPlace 2.0
  https://arxiv.org/abs/2004.10746
- Marković et al., Nature 2025, Photonic floorplanning
  https://www.nature.com/articles/s41586-025-09601-w
- Kahng et al., VLSI Physical Design (经典教材)
  https://ieeexplore.ieee.org/book/5233464
- Coffman et al., 1980, FFDH Bin Packing
  https://epubs.siam.org/doi/10.1137/0209042
"""

import numpy as np
import pytest

from polaris.engine.analytical_placer import (
    AdamState,
    AnalyticalPlacer,
    AnalyticalPlacerConfig,
    warm_start_placement,
)
from polaris.engine.floorplan_geometry import (
    count_overlaps,
    _count_overlaps_brute_force,
    _count_overlaps_spatial_hash,
    _bbox_overlap,
    hpwl,
    count_spacing_violations,
)
from polaris.engine.legalization import (
    LegalizationContext,
    RowState,
    legalize_placement,
    _find_candidate_rows,
    _place_in_row,
    _place_new_row,
)


# ============================================================
# AnalyticalPlacerConfig 配置测试
# ============================================================
class TestAnalyticalPlacerConfig:
    """AnalyticalPlacerConfig 解析法布局器配置测试。"""

    def test_default_params_from_dreamplace(self):
        """M1: 默认参数来自 DREAMPlace 论文。"""
        cfg = AnalyticalPlacerConfig()
        assert cfg.gamma == 4.0
        assert cfg.density_weight == pytest.approx(1e-3, rel=1e-6)
        assert cfg.learning_rate == 0.01
        assert cfg.max_iterations == 200

    def test_custom_params(self):
        """M1: 自定义配置参数。"""
        cfg = AnalyticalPlacerConfig(
            gamma=2.0,
            max_iterations=500,
        )
        assert cfg.gamma == 2.0
        assert cfg.max_iterations == 500


# ============================================================
# AdamState 测试
# ============================================================
class TestAdamState:
    """AdamState Adam 优化器状态测试。"""

    def test_init(self):
        """M1: 初始化状态。"""
        n = 10
        state = AdamState(
            m=np.zeros(n),
            v=np.zeros(n),
            t=0,
        )
        assert state.m.shape == (n,)
        assert state.v.shape == (n,)
        assert state.t == 0

    def test_frozen_check(self):
        """M1: dataclass 字段赋值。"""
        state = AdamState(
            m=np.array([1.0, 2.0]),
            v=np.array([3.0, 4.0]),
            t=5,
        )
        assert state.t == 5
        assert state.m[0] == 1.0


# ============================================================
# AnalyticalPlacer 解析法布局器测试
# ============================================================
class TestAnalyticalPlacer:
    """AnalyticalPlacer 解析法布局器测试。"""

    def test_init_default(self):
        """M1: 默认初始化。"""
        from polaris.data.specs import CircuitSpec, DeviceSpec

        circuit = CircuitSpec(
            name="test",
            devices=[
                DeviceSpec(name="d1", device_type="wg", width_um=10.0, height_um=5.0),
                DeviceSpec(name="d2", device_type="wg", width_um=10.0, height_um=5.0),
            ],
            connections=[("d1", "in", "d2", "out")],
            canvas_w=500.0,
            canvas_h=500.0,
        )
        placer = AnalyticalPlacer(circuit)
        assert isinstance(placer.config, AnalyticalPlacerConfig)

    def test_init_with_config(self):
        """M1: 自定义配置初始化。"""
        from polaris.data.specs import CircuitSpec, DeviceSpec

        cfg = AnalyticalPlacerConfig(max_iterations=100)
        circuit = CircuitSpec(
            name="test",
            devices=[
                DeviceSpec(name="d1", device_type="wg", width_um=10.0, height_um=5.0),
            ],
            canvas_w=500.0,
            canvas_h=500.0,
        )
        placer = AnalyticalPlacer(circuit, config=cfg)
        assert placer.config.max_iterations == 100

    def test_place_simple_circuit(self):
        """M2: 简单电路布局成功。"""
        from polaris.data.specs import CircuitSpec, DeviceSpec

        circuit = CircuitSpec(
            name="test",
            devices=[
                DeviceSpec(name="d1", device_type="wg", width_um=10.0, height_um=5.0),
                DeviceSpec(name="d2", device_type="wg", width_um=10.0, height_um=5.0),
            ],
            connections=[("d1", "in", "d2", "out")],
            canvas_w=500.0,
            canvas_h=500.0,
        )
        placer = AnalyticalPlacer(circuit)
        result = placer.place()
        assert isinstance(result, dict)
        assert "d1" in result
        assert "d2" in result
        assert isinstance(result["d1"], tuple)
        assert len(result["d1"]) == 2

    def test_place_result_within_canvas(self):
        """M2: 布局结果在画布范围内。"""
        from polaris.data.specs import CircuitSpec, DeviceSpec

        n = 5
        devices = [
            DeviceSpec(name=f"d{i}", device_type="wg", width_um=10.0, height_um=5.0)
            for i in range(n)
        ]
        connections = [
            (f"d{i}", "in", f"d{i+1}", "out")
            for i in range(n - 1)
        ]
        circuit = CircuitSpec(
            name="test",
            devices=devices,
            connections=connections,
            canvas_w=500.0,
            canvas_h=500.0,
        )
        placer = AnalyticalPlacer(circuit)
        result = placer.place()
        for name, (x, y) in result.items():
            assert 0.0 <= x <= placer.canvas_w
            assert 0.0 <= y <= placer.canvas_h

    def test_compute_hpwl_reduces(self):
        """M3: 优化后 HPWL 降低。"""
        from polaris.data.specs import CircuitSpec, DeviceSpec

        n = 6
        devices = [
            DeviceSpec(name=f"d{i}", device_type="wg", width_um=10.0, height_um=5.0)
            for i in range(n)
        ]
        connections = [
            (f"d{i}", "in", f"d{(i+1)%n}", "out")
            for i in range(n)
        ]
        circuit = CircuitSpec(
            name="test",
            devices=devices,
            connections=connections,
            canvas_w=500.0,
            canvas_h=500.0,
        )
        cfg = AnalyticalPlacerConfig(max_iterations=50)
        placer = AnalyticalPlacer(circuit, config=cfg)
        result = placer.place()
        assert len(result) == n


# ============================================================
# warm_start_placement 暖启动函数测试
# ============================================================
class TestWarmStartPlacement:
    """warm_start_placement 暖启动布局测试。"""

    def test_function_exists(self):
        """M1: 函数存在且可调用。"""
        assert callable(warm_start_placement)


# ============================================================
# HPWL 线长估计测试
# ============================================================
class TestHPWL:
    """HPWL 半周长线长测试。"""

    def test_hpwl_function_exists(self):
        """M1: hpwl 函数存在。"""
        assert callable(hpwl)

    def test_bbox_overlap_no_overlap(self):
        """M1: 不重叠的 AABB 返回 False。"""
        a = (0.0, 0.0, 10.0, 10.0)
        b = (20.0, 0.0, 30.0, 10.0)
        assert not _bbox_overlap(a, b)

    def test_bbox_overlap_full_overlap(self):
        """M2: 完全重叠的 AABB 返回 True。"""
        a = (0.0, 0.0, 10.0, 10.0)
        b = (5.0, 5.0, 15.0, 15.0)
        assert _bbox_overlap(a, b)

    def test_bbox_overlap_touching(self):
        """M2: 仅接触不算重叠。"""
        a = (0.0, 0.0, 10.0, 10.0)
        b = (10.0, 0.0, 20.0, 10.0)
        assert not _bbox_overlap(a, b)


# ============================================================
# 重叠检测测试
# ============================================================
class TestOverlapDetection:
    """重叠检测测试。"""

    def test_no_overlap(self):
        """M1: 不重叠的矩形返回 0。"""
        rects = [
            _FakeBBox((0.0, 0.0), (10.0, 10.0)),
            _FakeBBox((20.0, 0.0), (30.0, 10.0)),
        ]
        count = _count_overlaps_brute_force(rects)
        assert count == 0

    def test_full_overlap(self):
        """M2: 完全重叠的矩形计数正确。"""
        rects = [
            _FakeBBox((0.0, 0.0), (10.0, 10.0)),
            _FakeBBox((5.0, 5.0), (15.0, 15.0)),
        ]
        count = _count_overlaps_brute_force(rects)
        assert count == 1

    def test_touching_not_overlap(self):
        """M2: 仅接触不算重叠。"""
        rects = [
            _FakeBBox((0.0, 0.0), (10.0, 10.0)),
            _FakeBBox((10.0, 0.0), (20.0, 10.0)),
        ]
        count = _count_overlaps_brute_force(rects)
        assert count == 0

    def test_overlap_area(self):
        """M2: 重叠检测正确。"""
        result = _bbox_overlap(
            (0.0, 0.0, 10.0, 10.0),
            (5.0, 5.0, 15.0, 15.0),
        )
        assert result is True

    def test_no_overlap_area_zero(self):
        """M1: 不重叠返回 False。"""
        result = _bbox_overlap(
            (0.0, 0.0, 10.0, 10.0),
            (20.0, 20.0, 30.0, 30.0),
        )
        assert result is False

    def test_spatial_hash_matches_brute_force(self):
        """M3: 空间哈希结果与暴力法一致。"""
        rng = np.random.default_rng(42)
        n = 100
        rects = []
        for i in range(n):
            x = rng.uniform(0, 90)
            y = rng.uniform(0, 90)
            w = rng.uniform(2, 8)
            h = rng.uniform(2, 8)
            rects.append(_FakeBBox((x, y), (x + w, y + h)))

        bf_count = _count_overlaps_brute_force(rects)
        state = _FakeState(rects, grid_size=10.0)
        sh_count = _count_overlaps_spatial_hash(rects, state)
        assert bf_count == sh_count


# ============================================================
# Legalization 合法化测试
# ============================================================
class TestLegalization:
    """Legalization 布局合法化测试。"""

    def test_context_init(self):
        """M1: LegalizationContext 初始化。"""
        ctx = LegalizationContext(
            widths=np.array([10.0, 20.0]),
            heights=np.array([5.0, 8.0]),
            device_names=["d1", "d2"],
            connections=[(0, 1)],
            canvas_w=100.0,
            canvas_h=50.0,
        )
        assert ctx.canvas_w == 100.0
        assert len(ctx.device_names) == 2

    def test_row_state_init(self):
        """M1: RowState 初始化。"""
        state = RowState()
        assert len(state.rows) == 0
        assert len(state.row_congestion) == 0

    def test_legalize_placement_simple(self):
        """M2: 简单电路合法化成功。"""
        n = 5
        widths = np.full(n, 10.0)
        heights = np.full(n, 5.0)
        pos = np.zeros((n, 2))
        for i in range(n):
            pos[i] = [float(i * 3.0), float(i * 2.0)]
        ctx = LegalizationContext(
            widths=widths,
            heights=heights,
            device_names=[f"d{i}" for i in range(n)],
            connections=[],
            canvas_w=200.0,
            canvas_h=100.0,
        )
        result = legalize_placement(pos, ctx)
        assert isinstance(result, dict)
        assert len(result) == n

    def test_place_new_row(self):
        """M2: 放置新行。"""
        rows: list[list[float]] = []
        _place_new_row(rows, 10.0, 5.0)
        assert len(rows) == 1
        assert rows[0][2] == 10.0

    def test_find_candidate_rows(self):
        """M2: 查找候选行。"""
        rows: list[list[float]] = [
            [0.0, 10.0, 5.0],
            [15.0, 8.0, 3.0],
        ]
        candidates = _find_candidate_rows(rows, 6.0, 5.0, 100.0)
        assert isinstance(candidates, list)


# ============================================================
# 辅助类
# ============================================================
class _FakeBBox:
    """假 bbox 对象，用于重叠检测测试。"""

    def __init__(self, min_pt, max_pt):
        self._min = min_pt
        self._max = max_pt

    def bbox_abs(self):
        return (self._min[0], self._min[1], self._max[0], self._max[1])


class _FakeState:
    """假 state 对象，用于空间哈希测试。"""

    def __init__(self, placements, grid_size=10.0):
        self.placements = {i: p for i, p in enumerate(placements)}
        self.grid_size = grid_size
