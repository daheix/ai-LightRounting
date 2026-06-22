"""R07 层次化 DRC 引擎测试。

测试 BVH 加速结构、自适应行分块、层次化 DRC 检查。

来源:
- OpenDRC: He et al., DAC 2023, DOI: 10.1109/DAC56929.2023.10247734
"""

from __future__ import annotations

import numpy as np
import pytest

from polaris.sim.hierarchical_drc import (
    BVH,
    BVHNode,
    DRCViolation,
    HierarchicalDRC,
    RowPartition,
    run_hierarchical_drc,
)
from polaris.sim.klayout_drc import DRCCheckType, DRCRule


def _make_rule(
    name: str = "WG_MIN_WIDTH",
    layer: str = "WG",
    check_type: DRCCheckType = DRCCheckType.WIDTH,
    threshold: float = 3.0,
) -> DRCRule:
    """创建测试用 DRCRule。"""
    return DRCRule(
        name=name,
        layer_name=layer,
        check_type=check_type,
        threshold_um=threshold,
    )


class TestBVH:
    """BVH 加速结构测试。"""

    def test_bvh_build_basic(self):
        """测试 BVH 基本构建。"""
        polygons = [
            np.array([[0, 0], [10, 0], [10, 10], [0, 10]]),
            np.array([[20, 0], [30, 0], [30, 10], [20, 10]]),
            np.array([[0, 20], [10, 20], [10, 30], [0, 30]]),
        ]
        bvh = BVH()
        bvh.build(polygons)
        assert bvh.root is not None

    def test_bvh_build_empty(self):
        """测试空多边形列表构建。"""
        bvh = BVH()
        bvh.build([])
        assert bvh.root is None

    def test_bvh_build_single(self):
        """测试单个多边形构建。"""
        polygons = [np.array([[0, 0], [10, 0], [10, 10], [0, 10]])]
        bvh = BVH()
        bvh.build(polygons)
        assert bvh.root is not None
        assert bvh.root.is_leaf

    def test_bvh_query(self):
        """测试 BVH 查询。"""
        polygons = [
            np.array([[0, 0], [10, 0], [10, 10], [0, 10]]),
            np.array([[20, 0], [30, 0], [30, 10], [20, 10]]),
            np.array([[0, 20], [10, 20], [10, 30], [0, 30]]),
        ]
        bvh = BVH()
        bvh.build(polygons)
        # 查询与 [5, 5, 15, 15] 相交的多边形
        results = bvh.query(np.array([5, 5, 15, 15]))
        assert len(results) >= 1


class TestRowPartition:
    """自适应行分块测试。"""

    def test_row_partition_basic(self):
        """测试基本行分块。"""
        polygons = [
            np.array([[0, 0], [10, 0], [10, 10], [0, 10]]),
            np.array([[0, 20], [10, 20], [10, 30], [0, 30]]),
            np.array([[0, 40], [10, 40], [10, 50], [0, 50]]),
        ]
        partition = RowPartition()
        blocks = partition.partition(polygons)
        assert len(blocks) >= 1

    def test_row_partition_empty(self):
        """测试空多边形分块。"""
        partition = RowPartition()
        blocks = partition.partition([])
        assert len(blocks) == 0

    def test_row_partition_max_rows(self):
        """测试 max_rows 参数。"""
        polygons = [
            np.array([[0, i * 10], [10, i * 10], [10, i * 10 + 5], [0, i * 10 + 5]])
            for i in range(10)
        ]
        partition = RowPartition(max_rows=2)
        blocks = partition.partition(polygons)
        assert len(blocks) >= 1


class TestHierarchicalDRC:
    """层次化 DRC 引擎测试。"""

    def test_drc_engine_init(self):
        """测试 DRC 引擎初始化。"""
        rules = [_make_rule()]
        engine = HierarchicalDRC(rules)
        assert engine is not None

    def test_drc_engine_empty_rules_raises(self):
        """测试空规则列表 raise。"""
        with pytest.raises(ValueError, match="DRC 规则列表不能为空"):
            HierarchicalDRC([])

    def test_drc_width_check(self):
        """测试 width 检查。"""
        # 创建一个窄多边形（宽度 2μm）
        polygons = {"WG": [np.array([[0, 0], [2, 0], [2, 10], [0, 10]])]}
        rules = [_make_rule(threshold=3.0)]
        engine = HierarchicalDRC(rules)
        violations = engine.check(polygons)
        # 宽度 2 < 3，应有违规
        assert len(violations) > 0

    def test_drc_space_check(self):
        """测试 space 检查。"""
        # 创建两个相近的多边形（间距 1μm）
        polygons = {
            "WG": [
                np.array([[0, 0], [10, 0], [10, 10], [0, 10]]),
                np.array([[11, 0], [21, 0], [21, 10], [11, 10]]),
            ]
        }
        rules = [_make_rule(
            name="WG_MIN_SPACE", check_type=DRCCheckType.SPACE, threshold=2.0
        )]
        engine = HierarchicalDRC(rules)
        violations = engine.check(polygons)
        # 间距 1 < 2，应有违规
        assert len(violations) > 0

    def test_drc_area_check(self):
        """测试 area 检查。"""
        # 创建小面积多边形（面积 4μm²）
        polygons = {"WG": [np.array([[0, 0], [2, 0], [2, 2], [0, 2]])]}
        rules = [_make_rule(
            name="WG_MIN_AREA", check_type=DRCCheckType.AREA, threshold=10.0
        )]
        engine = HierarchicalDRC(rules)
        violations = engine.check(polygons)
        # 面积 4 < 10，应有违规
        assert len(violations) > 0

    def test_drc_no_violation(self):
        """测试无违规场景。"""
        # 创建合规多边形（宽度 10μm）
        polygons = {"WG": [np.array([[0, 0], [10, 0], [10, 10], [0, 10]])]}
        rules = [_make_rule(threshold=3.0)]
        engine = HierarchicalDRC(rules)
        violations = engine.check(polygons)
        # 宽度 10 > 3，应无违规
        assert len(violations) == 0

    def test_drc_density_check(self):
        """测试 density 检查。"""
        # 创建低密度版图
        polygons = {"WG": [np.array([[0, 0], [1, 0], [1, 1], [0, 1]])]}
        rules = [_make_rule(
            name="WG_MIN_DENSITY", check_type=DRCCheckType.DENSITY, threshold=30.0
        )]
        engine = HierarchicalDRC(rules)
        violations = engine.check(polygons)
        # 密度很低，应有违规
        assert len(violations) > 0


class TestRunHierarchicalDRC:
    """统一入口函数测试。"""

    def test_run_hierarchical_drc_basic(self):
        """测试统一入口函数。"""
        polygons = {"WG": [np.array([[0, 0], [2, 0], [2, 10], [0, 10]])]}
        rules = [_make_rule(threshold=3.0)]
        violations = run_hierarchical_drc(polygons, rules)
        assert isinstance(violations, list)
        assert len(violations) > 0

    def test_run_hierarchical_drc_empty_layout(self):
        """测试空版图。"""
        rules = [_make_rule(threshold=3.0)]
        violations = run_hierarchical_drc({}, rules)
        assert violations == []


class TestR07Integration:
    """R07 集成测试。"""

    def test_no_fallback_in_hierarchical_drc(self):
        """验证 hierarchical_drc.py 无 fall-back 兜底（AST 检查）。"""
        import ast

        with open("src/polaris/sim/hierarchical_drc.py") as f:
            source = f.read()
        tree = ast.parse(source)

        fallback_count = 0
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                for child in ast.walk(node):
                    if isinstance(child, ast.Pass):
                        fallback_count += 1

        assert fallback_count == 0, (
            f"发现 {fallback_count} 个 except:pass fall-back，违反规则 14.1"
        )

    def test_drc_violation_is_dataclass(self):
        """验证 DRCViolation 是 dataclass。"""
        from dataclasses import is_dataclass

        assert is_dataclass(DRCViolation)

    def test_bvh_node_is_dataclass(self):
        """验证 BVHNode 是 dataclass。"""
        from dataclasses import is_dataclass

        assert is_dataclass(BVHNode)
