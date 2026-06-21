"""P0-2 规模扩展（第11轮）测试：空间哈希优化 + Placement 缓存 + 障碍缓存。

验证三项优化在 500 器件规模下的正确性与性能：
1. _count_spacing_violations 空间哈希 vs 暴力结果一致
2. Placement.bbox_abs/port_positions 缓存正确
3. RoutingEnv._collect_obstacles 缓存正确
4. 500 器件端到端可跑通

来源:
- 空间哈希: OpenROAD/R-tree 简化版
- 规模目标: PoLaRIS v1.0 MVP 500 器件（commercial_gap_analysis.md P0-2）
"""

from __future__ import annotations

import numpy as np

from polaris.engine.floorplan_env import (
    Placement,
    _count_spacing_violations,
    _count_spacing_violations_brute_force,
)
from polaris.pdk.catalog import build_default_catalog

# =============================================================================
# 1. 空间哈希间距检测正确性
# =============================================================================


class TestSpacingViolationsSpatialHash:
    """验证空间哈希优化与暴力检测结果完全一致。"""

    def test_small_scale_uses_brute_force(self):
        """<50 器件时走暴力路径。"""
        cat = build_default_catalog()
        dev = cat.get("strip_waveguide", platform="SOI")
        placements = [
            Placement(f"d{i}", dev, x=i * 3.0, y=0.0) for i in range(10)
        ]
        # 间距 3μm < 5μm，相邻器件应违规
        result = _count_spacing_violations(placements, min_spacing=5.0)
        brute = _count_spacing_violations_brute_force(placements, 5.0)
        assert result == brute
        assert result >= 1

    def test_large_scale_uses_spatial_hash(self):
        """>=50 器件时走空间哈希路径。"""
        cat = build_default_catalog()
        dev = cat.get("strip_waveguide", platform="SOI")
        # 50 个器件，间距 3μm < 5μm
        placements = [
            Placement(f"d{i}", dev, x=i * 3.0, y=0.0) for i in range(50)
        ]
        result = _count_spacing_violations(placements, min_spacing=5.0)
        brute = _count_spacing_violations_brute_force(placements, 5.0)
        assert result == brute, f"空间哈希 {result} != 暴力 {brute}"

    def test_no_violations_large_scale(self):
        """大规模无违规时返回 0。"""
        cat = build_default_catalog()
        dev = cat.get("strip_waveguide", platform="SOI")
        # 间距 100μm >> 5μm
        placements = [
            Placement(f"d{i}", dev, x=i * 100.0, y=0.0) for i in range(60)
        ]
        result = _count_spacing_violations(placements, min_spacing=5.0)
        assert result == 0

    def test_all_violations_large_scale(self):
        """大规模全部违规时计数正确。"""
        cat = build_default_catalog()
        dev = cat.get("strip_waveguide", platform="SOI")
        # 全部重叠在原点
        placements = [Placement(f"d{i}", dev, x=0.0, y=0.0) for i in range(60)]
        result = _count_spacing_violations(placements, min_spacing=5.0)
        brute = _count_spacing_violations_brute_force(placements, 5.0)
        # C(60,2) = 1770 对全部违规
        assert result == brute == 1770

    def test_2d_grid_placement_consistency(self):
        """2D 网格布局下空间哈希与暴力一致。"""
        cat = build_default_catalog()
        dev = cat.get("strip_waveguide", platform="SOI")
        placements = []
        idx = 0
        for i in range(8):
            for j in range(8):
                placements.append(
                    Placement(f"d{idx}", dev, x=i * 4.0, y=j * 4.0)
                )
                idx += 1
        # 64 器件，间距 4μm < 5μm
        result = _count_spacing_violations(placements, min_spacing=5.0)
        brute = _count_spacing_violations_brute_force(placements, 5.0)
        assert result == brute

    def test_random_placement_consistency(self):
        """随机布局下空间哈希与暴力一致（100 器件）。"""
        cat = build_default_catalog()
        dev = cat.get("strip_waveguide", platform="SOI")
        rng = np.random.default_rng(42)
        placements = []
        for i in range(100):
            x = float(rng.uniform(0, 2000))
            y = float(rng.uniform(0, 2000))
            placements.append(Placement(f"d{i}", dev, x=x, y=y))
        result = _count_spacing_violations(placements, min_spacing=5.0)
        brute = _count_spacing_violations_brute_force(placements, 5.0)
        assert result == brute, f"随机布局不一致: 空间哈希 {result} != 暴力 {brute}"


# =============================================================================
# 2. Placement 缓存正确性
# =============================================================================


class TestPlacementCache:
    """验证 Placement.bbox_abs/port_positions 缓存正确。"""

    def test_bbox_abs_cached(self):
        """bbox_abs 多次调用返回相同结果且使用缓存。"""
        cat = build_default_catalog()
        dev = cat.get("strip_waveguide", platform="SOI")
        pl = Placement("a", dev, x=10.0, y=20.0, rotation=90)
        bbox1 = pl.bbox_abs()
        bbox2 = pl.bbox_abs()
        assert bbox1 == bbox2
        assert "bbox" in pl._cache

    def test_port_positions_cached(self):
        """port_positions 多次调用返回相同结果且使用缓存。"""
        cat = build_default_catalog()
        dev = cat.get("strip_waveguide", platform="SOI")
        pl = Placement("a", dev, x=10.0, y=20.0)
        ports1 = pl.port_positions()
        ports2 = pl.port_positions()
        assert ports1 == ports2
        assert "ports" in pl._cache

    def test_bbox_abs_correctness(self):
        """缓存值与无缓存计算一致。"""
        cat = build_default_catalog()
        dev = cat.get("strip_waveguide", platform="SOI")
        pl = Placement("a", dev, x=10.0, y=20.0, rotation=0)
        # 无缓存计算
        w = dev.bbox.xmax - dev.bbox.xmin
        h = dev.bbox.ymax - dev.bbox.ymin
        expected = (10.0, 20.0, 10.0 + w, 20.0 + h)
        assert pl.bbox_abs() == expected

    def test_rotation_affects_bbox(self):
        """不同旋转角度的 Placement 缓存独立。"""
        cat = build_default_catalog()
        dev = cat.get("strip_waveguide", platform="SOI")
        pl0 = Placement("a", dev, x=0.0, y=0.0, rotation=0)
        pl90 = Placement("b", dev, x=0.0, y=0.0, rotation=90)
        # 旋转 90 度后宽高互换（如果器件非正方形）
        pl0.bbox_abs()
        pl90.bbox_abs()
        # 两个 Placement 的缓存独立
        assert "bbox" in pl0._cache
        assert "bbox" in pl90._cache

    def test_cache_not_in_repr(self):
        """_cache 不出现在 repr 中（repr=False）。"""
        cat = build_default_catalog()
        dev = cat.get("strip_waveguide", platform="SOI")
        pl = Placement("a", dev, x=0.0, y=0.0)
        pl.bbox_abs()  # 触发缓存
        r = repr(pl)
        assert "_cache" not in r

    def test_cache_not_in_eq(self):
        """_cache 不影响相等性比较（compare=False）。"""
        cat = build_default_catalog()
        dev = cat.get("strip_waveguide", platform="SOI")
        pl1 = Placement("a", dev, x=0.0, y=0.0)
        pl2 = Placement("a", dev, x=0.0, y=0.0)
        pl1.bbox_abs()  # pl1 有缓存，pl2 无
        assert pl1 == pl2


# =============================================================================
# 3. RoutingEnv 障碍缓存正确性
# =============================================================================


class TestRoutingEnvObstacleCache:
    """验证 RoutingEnv._collect_obstacles 使用缓存后结果正确。"""

    def test_obstacle_cache_populated_on_reset(self):
        """reset() 后障碍缓存被填充。"""
        from polaris.engine.netlist import Netlist, NetlistConnection, NetlistInstance
        from polaris.pdk.device import BoundingBox, Device
        from polaris.pdk.port import Port
        from polaris.router.routing_env import RoutingEnv, RoutingEnvConfig

        # 构造最小网表
        dev = Device(
            device_id="wg",
            platform="SOI",
            category="waveguide",
            name="strip_waveguide",
            ports=[
                Port("in", 0, 5, "WEST", "strip", 0.5),
                Port("out", 10, 5, "EAST", "strip", 0.5),
            ],
            bbox=BoundingBox(0, 0, 10, 10),
        )
        net = Netlist(
            instances=[
                NetlistInstance("a", "strip_waveguide", "SOI"),
                NetlistInstance("b", "strip_waveguide", "SOI"),
                NetlistInstance("c", "strip_waveguide", "SOI"),
            ],
            connections=[
                NetlistConnection("a", "out", "b", "in"),
                NetlistConnection("b", "out", "c", "in"),
            ],
        )
        placements = {
            "a": Placement("a", dev, x=0.0, y=0.0),
            "b": Placement("b", dev, x=50.0, y=0.0),
            "c": Placement("c", dev, x=100.0, y=0.0),
        }
        cfg = RoutingEnvConfig(canvas_w=500, canvas_h=500, grid_size=5.0)
        env = RoutingEnv(net, placements, config=cfg)
        env.reset()
        assert len(env._obstacle_bboxes) == 3
        assert len(env._obstacle_inst_ids) == 3

    def test_collect_obstacles_excludes_endpoints(self):
        """_collect_obstacles 排除起终点器件。"""
        from polaris.engine.netlist import Netlist, NetlistConnection, NetlistInstance
        from polaris.pdk.device import BoundingBox, Device
        from polaris.pdk.port import Port
        from polaris.router.routing_env import RoutingEnv, RoutingEnvConfig

        dev = Device(
            device_id="wg",
            platform="SOI",
            category="waveguide",
            name="strip_waveguide",
            ports=[
                Port("in", 0, 5, "WEST", "strip", 0.5),
                Port("out", 10, 5, "EAST", "strip", 0.5),
            ],
            bbox=BoundingBox(0, 0, 10, 10),
        )
        net = Netlist(
            instances=[
                NetlistInstance("a", "strip_waveguide", "SOI"),
                NetlistInstance("b", "strip_waveguide", "SOI"),
                NetlistInstance("c", "strip_waveguide", "SOI"),
                NetlistInstance("d", "strip_waveguide", "SOI"),
            ],
            connections=[
                NetlistConnection("a", "out", "b", "in"),
                NetlistConnection("b", "out", "c", "in"),
            ],
        )
        placements = {
            "a": Placement("a", dev, x=0.0, y=0.0),
            "b": Placement("b", dev, x=50.0, y=0.0),
            "c": Placement("c", dev, x=100.0, y=0.0),
            "d": Placement("d", dev, x=150.0, y=0.0),
        }
        cfg = RoutingEnvConfig(canvas_w=500, canvas_h=500, grid_size=5.0)
        env = RoutingEnv(net, placements, config=cfg)
        env.reset()
        # 第0连接 a→b，排除 a 和 b，剩余 c 和 d
        obstacles = env._collect_obstacles()
        assert len(obstacles) == 2

    def test_obstacle_cache_values_match_bbox_abs(self):
        """缓存的 bbox 值与直接调用 bbox_abs() 一致。"""
        from polaris.engine.netlist import Netlist, NetlistInstance
        from polaris.pdk.device import BoundingBox, Device
        from polaris.pdk.port import Port
        from polaris.router.routing_env import RoutingEnv, RoutingEnvConfig

        dev = Device(
            device_id="wg",
            platform="SOI",
            category="waveguide",
            name="strip_waveguide",
            ports=[
                Port("in", 0, 5, "WEST", "strip", 0.5),
                Port("out", 10, 5, "EAST", "strip", 0.5),
            ],
            bbox=BoundingBox(0, 0, 10, 10),
        )
        net = Netlist(
            instances=[NetlistInstance("a", "strip_waveguide", "SOI")],
            connections=[],
        )
        placements = {"a": Placement("a", dev, x=30.0, y=40.0)}
        cfg = RoutingEnvConfig(canvas_w=500, canvas_h=500, grid_size=5.0)
        env = RoutingEnv(net, placements, config=cfg)
        env.reset()
        assert env._obstacle_bboxes[0] == placements["a"].bbox_abs()


# =============================================================================
# 4. 500 器件规模端到端
# =============================================================================


class TestScale500Devices:
    """验证 500 器件规模下优化后的性能与正确性。"""

    def test_spacing_violations_500_devices(self):
        """500 器件间距检测在合理时间内完成。"""
        cat = build_default_catalog()
        dev = cat.get("strip_waveguide", platform="SOI")
        # 500 器件网格布局，间距 3μm < 5μm
        placements = []
        idx = 0
        for i in range(25):
            for j in range(20):
                placements.append(
                    Placement(f"d{idx}", dev, x=i * 3.0, y=j * 3.0)
                )
                idx += 1
        assert len(placements) == 500
        # 空间哈希应与暴力一致
        result = _count_spacing_violations(placements, min_spacing=5.0)
        brute = _count_spacing_violations_brute_force(placements, 5.0)
        assert result == brute

    def test_spacing_violations_500_random(self):
        """500 器件随机布局下空间哈希与暴力一致。"""
        cat = build_default_catalog()
        dev = cat.get("strip_waveguide", platform="SOI")
        rng = np.random.default_rng(123)
        placements = []
        for i in range(500):
            x = float(rng.uniform(0, 5000))
            y = float(rng.uniform(0, 5000))
            placements.append(Placement(f"d{i}", dev, x=x, y=y))
        result = _count_spacing_violations(placements, min_spacing=5.0)
        brute = _count_spacing_violations_brute_force(placements, 5.0)
        assert result == brute, f"500 器件随机布局不一致: {result} != {brute}"

    def test_placement_cache_500_devices(self):
        """500 器件 Placement 缓存正常工作。"""
        cat = build_default_catalog()
        dev = cat.get("strip_waveguide", platform="SOI")
        placements = [
            Placement(f"d{i}", dev, x=i * 10.0, y=0.0) for i in range(500)
        ]
        # 第一次调用计算并缓存
        bboxes1 = [pl.bbox_abs() for pl in placements]
        # 第二次调用从缓存读取
        bboxes2 = [pl.bbox_abs() for pl in placements]
        assert bboxes1 == bboxes2
        # 所有缓存都已填充
        assert all("bbox" in pl._cache for pl in placements)
