"""R121-R180: DRC 3 个独立算法回归测试（S2/S4/E2）。

验证 R121-R180 完善的 3 个简化规则独立算法正确性：
1. S2 (MIN_SPACING_SAME_NET): 同网络间距检查
2. S4 (MIN_END_TO_END): 端到端间距检查
3. E2 (MIN_EXTENSION): 延伸检查

R05 要求：Bug 修复/功能完善须附回归测试。

文献依据:
- Calibre nmDRC ENC/EXT/INT: https://eda.sw.siemens.com/en-US/calibre/
- KLayout DRC Reference: https://klayout.org/downloads/master/doc-qt4/manual/drc_basic.html
- OpenDRC, He et al., DAC 2023, DOI:10.1109/DAC56929.2023.10247734
"""

from __future__ import annotations

import numpy as np
import pytest

from polaris.verification.drc_curvilinear_18rules import (
    CurvilinearDRCEngine,
    DRCRuleCategory,
    _edge_to_edge_distance,
    _polygon_end_edges,
    _polygon_extension,
)


# =============================================================================
# 几何辅助函数测试
# =============================================================================

class TestPolygonEndEdges:
    """_polygon_end_edges 端边识别测试。"""

    def test_rectangle_returns_two_shortest_edges(self):
        """矩形应返回 2 条最短边（端边）。"""
        # 10μm 长 × 0.5μm 宽矩形波导
        rect = np.array([[0, 0], [10, 0], [10, 0.5], [0, 0.5]], dtype=float)
        edges = _polygon_end_edges(rect, max_edges=2)
        assert len(edges) == 2
        # 端边长度应为 0.5（宽边），不是 10（长边）
        for a, b in edges:
            length = float(np.linalg.norm(b - a))
            assert length == pytest.approx(0.5), f"端边长度应为 0.5，得到 {length}"

    def test_square_returns_equal_edges(self):
        """正方形所有边等长，返回最短的 max_edges 条。"""
        square = np.array([[0, 0], [1, 0], [1, 1], [0, 1]], dtype=float)
        edges = _polygon_end_edges(square, max_edges=2)
        assert len(edges) == 2
        for a, b in edges:
            length = float(np.linalg.norm(b - a))
            assert length == pytest.approx(1.0)

    def test_degenerate_polygon_returns_empty(self):
        """退化多边形（<3 顶点）返回空列表。"""
        degenerate = np.array([[0, 0], [1, 1]], dtype=float)
        assert _polygon_end_edges(degenerate) == []


class TestEdgeToEdgeDistance:
    """_edge_to_edge_distance 线段间距测试。"""

    def test_parallel_segments_distance(self):
        """平行线段间距 = 垂直距离。"""
        a1, a2 = np.array([0, 0]), np.array([10, 0])
        b1, b2 = np.array([0, 2]), np.array([10, 2])
        d = _edge_to_edge_distance(a1, a2, b1, b2)
        assert d == pytest.approx(2.0)

    def test_intersecting_segments_zero_distance(self):
        """相交线段距离 = 0。"""
        a1, a2 = np.array([0, 0]), np.array([10, 10])
        b1, b2 = np.array([0, 10]), np.array([10, 0])
        d = _edge_to_edge_distance(a1, a2, b1, b2)
        assert d == pytest.approx(0.0)

    def test_perpendicular_segments(self):
        """垂直线段间距。"""
        a1, a2 = np.array([0, 0]), np.array([0, 5])
        b1, b2 = np.array([3, 0]), np.array([3, 5])
        d = _edge_to_edge_distance(a1, a2, b1, b2)
        assert d == pytest.approx(3.0)


class TestPolygonExtension:
    """_polygon_extension 延伸距离测试。"""

    def test_inner_fully_contains_outer(self):
        """inner 完全包含 outer 时，延伸 = outer 顶点到 inner 边的最小距离。"""
        # inner: 10×10 大矩形
        inner = np.array([[0, 0], [10, 0], [10, 10], [0, 10]], dtype=float)
        # outer: 6×6 小矩形，居中
        outer = np.array([[2, 2], [8, 2], [8, 8], [2, 8]], dtype=float)
        ext = _polygon_extension(inner, outer)
        # outer 顶点到 inner 边的最小距离 = 2
        assert ext == pytest.approx(2.0)

    def test_inner_does_not_contain_outer(self):
        """inner 未完全包含 outer 时，返回 -1。"""
        # inner: 4×4 小矩形
        inner = np.array([[0, 0], [4, 0], [4, 4], [0, 4]], dtype=float)
        # outer: 6×6 大矩形
        outer = np.array([[0, 0], [6, 0], [6, 6], [0, 6]], dtype=float)
        ext = _polygon_extension(inner, outer)
        assert ext == -1.0

    def test_coincident_polygons_zero_extension(self):
        """重合多边形延伸 = 0。"""
        poly = np.array([[0, 0], [5, 0], [5, 5], [0, 5]], dtype=float)
        ext = _polygon_extension(poly, poly)
        assert ext == pytest.approx(0.0)


# =============================================================================
# S2 同网络间距检查测试
# =============================================================================

class TestS2SameNetSpacing:
    """S2 (MIN_SPACING_SAME_NET) 独立算法测试。"""

    def test_same_net_close_polygons_violation(self):
        """同网络多边形间距 < limit → S2 违规。"""
        engine = CurvilinearDRCEngine()
        # 两条波导在同网络上，间距 0.1μm < 0.3μm S2 阈值
        wg1 = np.array([[0, 0], [10, 0], [10, 1], [0, 1]], dtype=float)
        wg2 = np.array([[0, 1.1], [10, 1.1], [10, 2.1], [0, 2.1]], dtype=float)
        violations = engine.run_geometric_checks(
            {"waveguide": [wg1, wg2]},
            net_assignments={"waveguide": [0, 0]},  # 同网络
        )
        s2_violations = [
            v for v in violations
            if v.category == DRCRuleCategory.MIN_SPACING_SAME_NET.value
        ]
        assert len(s2_violations) >= 1, "同网络间距 0.1μm < 0.3μm 应触发 S2 违规"
        assert s2_violations[0].measured_value < 0.3

    def test_different_net_no_s2_violation(self):
        """不同网络多边形 → 无 S2 违规（由 S1 检查）。"""
        engine = CurvilinearDRCEngine()
        wg1 = np.array([[0, 0], [10, 0], [10, 1], [0, 1]], dtype=float)
        wg2 = np.array([[0, 1.1], [10, 1.1], [10, 2.1], [0, 2.1]], dtype=float)
        violations = engine.run_geometric_checks(
            {"waveguide": [wg1, wg2]},
            net_assignments={"waveguide": [0, 1]},  # 不同网络
        )
        s2_violations = [
            v for v in violations
            if v.category == DRCRuleCategory.MIN_SPACING_SAME_NET.value
        ]
        assert len(s2_violations) == 0, "不同网络不应触发 S2 违规"

    def test_missing_net_assignments_raises(self):
        """S2 规则存在但未提供 net_assignments → raise ValueError（R03）。"""
        engine = CurvilinearDRCEngine()
        wg1 = np.array([[0, 0], [10, 0], [10, 1], [0, 1]], dtype=float)
        with pytest.raises(ValueError, match="net_ids"):
            engine.run_geometric_checks({"waveguide": [wg1]})

    def test_same_net_connected_polygons_no_violation(self):
        """同网络相连多边形（距离=0）→ 无 S2 违规（允许连接）。"""
        engine = CurvilinearDRCEngine()
        # 两条波导首尾相连
        wg1 = np.array([[0, 0], [5, 0], [5, 1], [0, 1]], dtype=float)
        wg2 = np.array([[5, 0], [10, 0], [10, 1], [5, 1]], dtype=float)
        violations = engine.run_geometric_checks(
            {"waveguide": [wg1, wg2]},
            net_assignments={"waveguide": [0, 0]},  # 同网络相连
        )
        s2_violations = [
            v for v in violations
            if v.category == DRCRuleCategory.MIN_SPACING_SAME_NET.value
        ]
        assert len(s2_violations) == 0, "同网络相连多边形不应触发 S2 违规"


# =============================================================================
# S4 端到端间距检查测试
# =============================================================================

class TestS4EndToEndSpacing:
    """S4 (MIN_END_TO_END) 独立算法测试。"""

    def test_end_to_end_close_violation(self):
        """两条波导端部面对面间距 < limit → S4 违规。"""
        engine = CurvilinearDRCEngine()
        # 两条水平波导，端部面对面，间距 0.1μm < 0.6μm S4 阈值
        wg1 = np.array([[0, 0], [5, 0], [5, 0.5], [0, 0.5]], dtype=float)
        wg2 = np.array([[5.1, 0], [10, 0], [10, 0.5], [5.1, 0.5]], dtype=float)
        violations = engine.run_geometric_checks(
            {"waveguide": [wg1, wg2]},
            net_assignments={"waveguide": [0, 1]},
        )
        s4_violations = [
            v for v in violations
            if v.category == DRCRuleCategory.MIN_END_TO_END.value
        ]
        assert len(s4_violations) >= 1, "端到端间距 0.1μm < 0.6μm 应触发 S4 违规"
        assert s4_violations[0].measured_value < 0.6

    def test_end_to_end_far_no_violation(self):
        """两条波导端部间距 > limit → 无 S4 违规。"""
        engine = CurvilinearDRCEngine()
        # 两条水平波导，端部间距 2.0μm > 0.6μm S4 阈值
        wg1 = np.array([[0, 0], [5, 0], [5, 0.5], [0, 0.5]], dtype=float)
        wg2 = np.array([[7, 0], [12, 0], [12, 0.5], [7, 0.5]], dtype=float)
        violations = engine.run_geometric_checks(
            {"waveguide": [wg1, wg2]},
            net_assignments={"waveguide": [0, 1]},
        )
        s4_violations = [
            v for v in violations
            if v.category == DRCRuleCategory.MIN_END_TO_END.value
        ]
        assert len(s4_violations) == 0, "端到端间距 2.0μm > 0.6μm 不应触发 S4 违规"

    def test_single_polygon_no_s4_violation(self):
        """单条波导 → 无 S4 违规（需 ≥2 多边形）。"""
        engine = CurvilinearDRCEngine()
        wg = np.array([[0, 0], [10, 0], [10, 0.5], [0, 0.5]], dtype=float)
        violations = engine.run_geometric_checks(
            {"waveguide": [wg]},
            net_assignments={"waveguide": [0]},
        )
        s4_violations = [
            v for v in violations
            if v.category == DRCRuleCategory.MIN_END_TO_END.value
        ]
        assert len(s4_violations) == 0


# =============================================================================
# E2 延伸检查测试
# =============================================================================

class TestE2Extension:
    """E2 (MIN_EXTENSION) 独立算法测试。"""

    def test_sufficient_extension_no_violation(self):
        """inner 充分延伸超出 outer → 无 E2 违规。"""
        engine = CurvilinearDRCEngine()
        # metal1 (inner) 10×10, contact (outer) 6×6 居中
        # 延伸量 = 2.0μm > 0.2μm E2 阈值
        metal = np.array([[0, 0], [10, 0], [10, 10], [0, 10]], dtype=float)
        contact = np.array([[2, 2], [8, 2], [8, 8], [2, 8]], dtype=float)
        violations = engine.run_geometric_checks(
            {"metal1": [metal], "contact": [contact]},
            enclosure_pairs={"metal1": "contact"},
            net_assignments={"metal1": [0], "contact": [0]},
        )
        e2_violations = [
            v for v in violations
            if v.category == DRCRuleCategory.MIN_EXTENSION.value
        ]
        assert len(e2_violations) == 0, "延伸 2.0μm > 0.2μm 不应触发 E2 违规"

    def test_insufficient_extension_violation(self):
        """inner 延伸不足 → E2 违规。"""
        engine = CurvilinearDRCEngine()
        # metal1 (inner) 6.2×6.2, contact (outer) 6×6 居中
        # 延伸量 = 0.1μm < 0.2μm E2 阈值
        metal = np.array([[0, 0], [6.2, 0], [6.2, 6.2], [0, 6.2]], dtype=float)
        contact = np.array([[0.1, 0.1], [6.1, 0.1], [6.1, 6.1], [0.1, 6.1]], dtype=float)
        violations = engine.run_geometric_checks(
            {"metal1": [metal], "contact": [contact]},
            enclosure_pairs={"metal1": "contact"},
            net_assignments={"metal1": [0], "contact": [0]},
        )
        e2_violations = [
            v for v in violations
            if v.category == DRCRuleCategory.MIN_EXTENSION.value
        ]
        assert len(e2_violations) >= 1, "延伸 0.1μm < 0.2μm 应触发 E2 违规"
        assert e2_violations[0].measured_value < 0.2

    def test_no_extension_violation(self):
        """inner 未延伸超出 outer → E2 违规（延伸量 = -1）。"""
        engine = CurvilinearDRCEngine()
        # metal1 (inner) 4×4 小, contact (outer) 6×6 大
        # inner 未包含 outer，延伸 = -1
        metal = np.array([[1, 1], [5, 1], [5, 5], [1, 5]], dtype=float)
        contact = np.array([[0, 0], [6, 0], [6, 6], [0, 6]], dtype=float)
        violations = engine.run_geometric_checks(
            {"metal1": [metal], "contact": [contact]},
            enclosure_pairs={"metal1": "contact"},
            net_assignments={"metal1": [0], "contact": [0]},
        )
        e2_violations = [
            v for v in violations
            if v.category == DRCRuleCategory.MIN_EXTENSION.value
        ]
        assert len(e2_violations) >= 1, "inner 未包含 outer 应触发 E2 违规"
        assert e2_violations[0].measured_value < 0  # -1 表示未包含
