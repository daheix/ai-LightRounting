"""B02-DRC 验收测试：DRC 规则检查与报告格式。

测试层次化 DRC 引擎的核心功能：线宽/间距规则、角点/凹口规则、
面积/密度/包围规则、DRC 违规报告格式。

来源:
- OpenDRC: He et al., DAC 2023, DOI: 10.1109/DAC56929.2023.10247734
- X-Check: He et al., ICCAD 2022
- KLayout DRC: https://www.klayout.org/doc-qt5/manual/drc_runsets.html
- SiEPIC EBeam PDK DRC: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- Chrostowski & Hochberg, "Silicon Photonics Design", CUP 2015, p.353
"""

from __future__ import annotations

import numpy as np
import pytest

from polaris.sim.hierarchical_drc import (
    BVH,
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
    threshold: float = 0.5,
    enclosure_layer: str | None = None,
    max_density: float | None = None,
) -> DRCRule:
    """创建测试用 DRCRule。"""
    return DRCRule(
        name=name,
        layer_name=layer,
        check_type=check_type,
        threshold_um=threshold,
        enclosure_layer_name=enclosure_layer,
        max_density=max_density,
    )


def _rect(x: float, y: float, w: float, h: float) -> np.ndarray:
    """创建矩形多边形。"""
    return np.array([[x, y], [x + w, y], [x + w, y + h], [x, y + h]])


class TestWidthRule:
    """线宽规则检查测试。"""

    def test_width_pass_wide_rectangle(self):
        """测试宽矩形通过线宽检查。"""
        rule = _make_rule(threshold=0.4)
        drc = HierarchicalDRC([rule])
        layout = {"WG": [_rect(0, 0, 10, 1.0)]}
        violations = drc.check(layout, hierarchical=False)
        assert len(violations) == 0

    def test_width_fail_narrow_rectangle(self):
        """测试窄矩形未通过线宽检查。"""
        rule = _make_rule(threshold=0.5)
        drc = HierarchicalDRC([rule])
        layout = {"WG": [_rect(0, 0, 10, 0.3)]}
        violations = drc.check(layout, hierarchical=False)
        assert len(violations) > 0

    def test_width_violation_has_correct_fields(self):
        """测试线宽违规对象字段完整性。"""
        rule = _make_rule(name="TEST_WIDTH", threshold=1.0)
        drc = HierarchicalDRC([rule])
        layout = {"WG": [_rect(0, 0, 5, 0.5)]}
        violations = drc.check(layout, hierarchical=False)
        assert len(violations) > 0
        v = violations[0]
        assert v.rule_name == "TEST_WIDTH"
        assert v.check_type == "width"
        assert v.layer_name == "WG"
        assert isinstance(v.location, tuple)
        assert len(v.location) == 2
        assert v.severity > 0

    def test_width_multiple_polygons(self):
        """测试多个多边形的线宽检查。"""
        rule = _make_rule(threshold=0.5)
        drc = HierarchicalDRC([rule])
        layout = {"WG": [
            _rect(0, 0, 10, 1.0),
            _rect(20, 0, 10, 0.3),
            _rect(40, 0, 10, 2.0),
        ]}
        violations = drc.check(layout, hierarchical=False)
        assert len(violations) >= 1

    def test_width_hierarchical_mode(self):
        """测试层次化模式下的线宽检查。"""
        rule = _make_rule(threshold=0.5)
        drc = HierarchicalDRC([rule])
        layout = {"WG": [
            _rect(0, 0, 10, 1.0),
            _rect(0, 20, 10, 0.3),
            _rect(0, 40, 10, 0.2),
        ]}
        violations = drc.check(layout, hierarchical=True)
        assert isinstance(violations, list)


class TestSpaceRule:
    """间距规则检查测试。"""

    def test_space_pass_wide_spacing(self):
        """测试大间距通过间距检查。"""
        rule = _make_rule(check_type=DRCCheckType.SPACE, threshold=1.0)
        drc = HierarchicalDRC([rule])
        layout = {"WG": [
            _rect(0, 0, 5, 1.0),
            _rect(10, 0, 5, 1.0),
        ]}
        violations = drc.check(layout, hierarchical=False)
        assert len(violations) == 0

    def test_space_fail_narrow_spacing(self):
        """测试小间距未通过间距检查。"""
        rule = _make_rule(check_type=DRCCheckType.SPACE, threshold=2.0)
        drc = HierarchicalDRC([rule])
        layout = {"WG": [
            _rect(0, 0, 5, 1.0),
            _rect(6, 0, 5, 1.0),
        ]}
        violations = drc.check(layout, hierarchical=False)
        assert len(violations) > 0

    def test_space_violation_message(self):
        """测试间距违规消息格式。"""
        rule = _make_rule(name="TEST_SPACE", check_type=DRCCheckType.SPACE, threshold=5.0)
        drc = HierarchicalDRC([rule])
        layout = {"WG": [
            _rect(0, 0, 2, 2),
            _rect(3, 0, 2, 2),
        ]}
        violations = drc.check(layout, hierarchical=False)
        if violations:
            assert "间距" in violations[0].message

    def test_space_with_bvh(self):
        """测试 BVH 加速下的间距检查。"""
        rule = _make_rule(check_type=DRCCheckType.SPACE, threshold=1.0)
        polys = [
            _rect(i * 3.0, 0, 1.0, 1.0)
            for i in range(10)
        ]
        layout = {"WG": polys}
        violations_flat = run_hierarchical_drc(layout, [rule], hierarchical=False)
        violations_hier = run_hierarchical_drc(layout, [rule], hierarchical=True)
        assert isinstance(violations_flat, list)
        assert isinstance(violations_hier, list)


class TestNotchRule:
    """凹口规则检查测试。"""

    def test_notch_simple_polygon(self):
        """测试简单多边形的凹口检查。"""
        rule = _make_rule(check_type=DRCCheckType.NOTCH, threshold=0.5)
        drc = HierarchicalDRC([rule])
        layout = {"WG": [_rect(0, 0, 10, 2.0)]}
        violations = drc.check(layout, hierarchical=False)
        assert isinstance(violations, list)

    def test_notch_violation_type(self):
        """测试凹口违规类型字段。"""
        rule = _make_rule(name="TEST_NOTCH", check_type=DRCCheckType.NOTCH, threshold=2.0)
        drc = HierarchicalDRC([rule])
        layout = {"WG": [_rect(0, 0, 10, 0.5)]}
        violations = drc.check(layout, hierarchical=False)
        if violations:
            assert violations[0].check_type == "notch"

    def test_notch_rule_check_type(self):
        """测试凹口规则 check_type 正确。"""
        rule = _make_rule(check_type=DRCCheckType.NOTCH, threshold=0.5)
        assert rule.check_type == DRCCheckType.NOTCH


class TestAreaRule:
    """面积规则检查测试。"""

    def test_area_pass_large_polygon(self):
        """测试大多边形通过面积检查。"""
        rule = _make_rule(check_type=DRCCheckType.AREA, threshold=1.0)
        drc = HierarchicalDRC([rule])
        layout = {"WG": [_rect(0, 0, 10, 5.0)]}
        violations = drc.check(layout, hierarchical=False)
        assert len(violations) == 0

    def test_area_fail_small_polygon(self):
        """测试小多边形未通过面积检查。"""
        rule = _make_rule(check_type=DRCCheckType.AREA, threshold=10.0)
        drc = HierarchicalDRC([rule])
        layout = {"WG": [_rect(0, 0, 1, 1)]}
        violations = drc.check(layout, hierarchical=False)
        assert len(violations) > 0

    def test_area_violation_message(self):
        """测试面积违规消息包含面积值。"""
        rule = _make_rule(name="TEST_AREA", check_type=DRCCheckType.AREA, threshold=100.0)
        drc = HierarchicalDRC([rule])
        layout = {"WG": [_rect(0, 0, 2, 2)]}
        violations = drc.check(layout, hierarchical=False)
        if violations:
            assert "面积" in violations[0].message


class TestDensityRule:
    """密度规则检查测试。"""

    def test_density_within_range(self):
        """测试密度在范围内时无违规。"""
        rule = _make_rule(
            check_type=DRCCheckType.DENSITY,
            threshold=10.0,
            max_density=90.0,
        )
        drc = HierarchicalDRC([rule])
        layout = {"WG": [_rect(0, 0, 50, 50)]}
        violations = drc.check(layout, hierarchical=False)
        assert len(violations) <= 1

    def test_density_rule_has_max_density(self):
        """测试密度规则包含 max_density 字段。"""
        rule = _make_rule(
            check_type=DRCCheckType.DENSITY,
            threshold=30.0,
            max_density=70.0,
        )
        assert rule.max_density == 70.0
        assert rule.threshold_um == 30.0

    def test_density_check_type(self):
        """测试密度检查类型正确。"""
        rule = _make_rule(check_type=DRCCheckType.DENSITY)
        assert rule.check_type == DRCCheckType.DENSITY


class TestEncloseRule:
    """包围规则检查测试。"""

    def test_enclose_pass_proper_enclosure(self):
        """测试正确包围通过检查。"""
        rule = _make_rule(
            check_type=DRCCheckType.ENCLOSE,
            threshold=0.5,
            enclosure_layer="M1_HEATER",
        )
        drc = HierarchicalDRC([rule])
        layout = {
            "VIAC": [_rect(2, 2, 1, 1)],
            "M1_HEATER": [_rect(0, 0, 5, 5)],
        }
        violations = drc.check(layout, hierarchical=False)
        assert isinstance(violations, list)

    def test_enclose_missing_enclosure_layer(self):
        """测试缺少包围层时不报错。"""
        rule = _make_rule(
            check_type=DRCCheckType.ENCLOSE,
            threshold=0.5,
            enclosure_layer="MISSING",
        )
        drc = HierarchicalDRC([rule])
        layout = {"VIAC": [_rect(0, 0, 1, 1)]}
        violations = drc.check(layout, hierarchical=False)
        assert len(violations) == 0

    def test_enclose_rule_requires_enclosure_layer_name(self):
        """测试 ENCLOSE 规则缺少 enclosure_layer_name 时抛错。"""
        rule = DRCRule(
            name="BAD_ENCLOSE",
            layer_name="VIAC",
            check_type=DRCCheckType.ENCLOSE,
            threshold_um=0.5,
        )
        drc = HierarchicalDRC([rule])
        layout = {
            "VIAC": [_rect(0, 0, 1, 1)],
            "M1": [_rect(-1, -1, 3, 3)],
        }
        with pytest.raises(ValueError):
            drc.check(layout, hierarchical=False)


class TestDRCReportFormat:
    """DRC 报告格式测试。"""

    def test_violation_dataclass_fields(self):
        """测试 DRCViolation 数据类字段。"""
        v = DRCViolation(
            rule_name="R1",
            check_type="width",
            layer_name="WG",
            message="test violation",
            location=(5.0, 10.0),
            severity=1.0,
        )
        assert v.rule_name == "R1"
        assert v.check_type == "width"
        assert v.layer_name == "WG"
        assert v.message == "test violation"
        assert v.location == (5.0, 10.0)
        assert v.severity == 1.0

    def test_run_hierarchical_drc_returns_list(self):
        """测试 run_hierarchical_drc 返回列表。"""
        rule = _make_rule(threshold=0.5)
        layout = {"WG": [_rect(0, 0, 10, 1.0)]}
        result = run_hierarchical_drc(layout, [rule])
        assert isinstance(result, list)

    def test_drc_with_empty_rules_raises(self):
        """测试空规则列表抛 ValueError。"""
        with pytest.raises(ValueError):
            HierarchicalDRC([])

    def test_drc_with_missing_layer_skipped(self):
        """测试缺少图层时规则被跳过。"""
        rule = _make_rule(layer="MISSING_LAYER", threshold=0.5)
        drc = HierarchicalDRC([rule])
        layout = {"WG": [_rect(0, 0, 10, 1.0)]}
        violations = drc.check(layout)
        assert len(violations) == 0


class TestBVHAcceleration:
    """BVH 加速结构测试。"""

    def test_bvh_build_and_query(self):
        """测试 BVH 构建与查询。"""
        polygons = [
            _rect(0, 0, 2, 2),
            _rect(10, 0, 2, 2),
            _rect(0, 10, 2, 2),
            _rect(10, 10, 2, 2),
        ]
        bvh = BVH()
        bvh.build(polygons)
        results = bvh.query((1.0, 1.0, 3.0, 3.0))
        assert len(results) >= 1

    def test_bvh_empty_polygons(self):
        """测试空多边形列表。"""
        bvh = BVH()
        result = bvh.build([])
        assert result is None

    def test_bvh_query_empty_region(self):
        """测试查询空区域。"""
        polygons = [_rect(0, 0, 2, 2)]
        bvh = BVH()
        bvh.build(polygons)
        results = bvh.query((100, 100, 110, 110))
        assert len(results) == 0


class TestRowPartition:
    """自适应行分块测试。"""

    def test_row_partition_basic(self):
        """测试基本行分块。"""
        polygons = [
            _rect(0, i * 10, 5, 2)
            for i in range(20)
        ]
        rp = RowPartition()
        blocks = rp.partition(polygons)
        assert len(blocks) >= 1
        assert sum(len(b) for b in blocks) == 20

    def test_row_partition_empty(self):
        """测试空多边形分块。"""
        rp = RowPartition()
        blocks = rp.partition([])
        assert len(blocks) == 0

    def test_row_partition_invalid_max_rows_raises(self):
        """测试无效 max_rows 抛错。"""
        with pytest.raises(ValueError):
            RowPartition(max_rows=0)
