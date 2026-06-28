"""F02 工艺约束验收测试。

验证最小线宽/间距约束、拐角/倒角、密度填充功能。

文献来源:
- Sigmund, 2007, Morphology-based black and white filters
  https://link.springer.com/article/10.1007/s00158-007-0198-x
- Wang et al., 2011, Projection-based aggregation in topology optimization
  https://onlinelibrary.wiley.com/doi/10.1002/nme.3122
- Lazarov & Sigmund, 2011, Filters in topology optimization
  https://onlinelibrary.wiley.com/doi/10.1002/nme.3120
- Siemens Calibre eqDRC, 2015
  https://blogs.sw.siemens.com/calibre/2015/11/17/design-rule-checking-for-silicon-photonics/
- Krinke et al., ISPD 2024, Curvilinear Photonics Layout
  https://dl.acm.org/doi/pdf/10.1145/3626184.3635289
"""

import numpy as np
import pytest

from polaris.sim.eqdrc import (
    EqDRCEngine,
    EqDRCRule,
    EqDRCViolation,
    FoundryDRCCertifier,
    FoundryDRCRunset,
    _point_segment_distance,
    _polygon_area,
)
from polaris.sim.fabrication_constraints import (
    ConnectivityConstraint,
    ConstraintMetrics,
    DensityFilter,
    DensityPenalty,
    FabricationConfig,
    FabricationConstraints,
    ProjectionConstraint,
)


# ============================================================
# FabricationConfig 配置测试
# ============================================================
class TestFabricationConfig:
    """FabricationConfig 制造约束配置测试。"""

    def test_default_params(self):
        """M1: 默认参数来自公开文献。"""
        cfg = FabricationConfig()
        assert cfg.min_feature_size == 2.0
        assert cfg.density_penalty_weight == 0.05
        assert cfg.projection_strength == 5.0
        assert cfg.filter_sigma == 1.5
        assert cfg.connectivity_threshold == 3

    def test_custom_params(self):
        """M1: 自定义配置参数。"""
        cfg = FabricationConfig(min_feature_size=4.0, density_penalty_weight=0.1)
        assert cfg.min_feature_size == 4.0
        assert cfg.density_penalty_weight == 0.1

    def test_frozen(self):
        """M1: 配置为 frozen dataclass。"""
        cfg = FabricationConfig()
        with pytest.raises(AttributeError):
            cfg.min_feature_size = 5.0


# ============================================================
# DensityPenalty 密度惩罚测试
# ============================================================
class TestDensityPenalty:
    """DensityPenalty 密度惩罚测试。"""

    def test_init_default(self):
        """M1: 默认权重。"""
        dp = DensityPenalty()
        assert dp.weight == 0.05

    def test_binary_density_zero_penalty(self):
        """M1: 二值密度（0或1）惩罚为 0。"""
        dp = DensityPenalty(weight=1.0)
        binary = np.array([[0.0, 1.0], [1.0, 0.0]])
        penalty = dp.compute_penalty(binary)
        assert penalty == pytest.approx(0.0, abs=1e-10)

    def test_gray_density_positive_penalty(self):
        """M2: 灰度密度惩罚 > 0。"""
        dp = DensityPenalty(weight=1.0)
        gray = np.full((10, 10), 0.5)
        penalty = dp.compute_penalty(gray)
        assert penalty > 0.0

    def test_penalty_symmetry(self):
        """M2: ρ 和 1-ρ 惩罚相同。"""
        dp = DensityPenalty(weight=1.0)
        d1 = np.array([0.2, 0.4, 0.6])
        d2 = 1.0 - d1
        p1 = dp.compute_penalty(d1)
        p2 = dp.compute_penalty(d2)
        assert p1 == pytest.approx(p2)

    def test_grayness_metric(self):
        """M2: grayness 指标正确。"""
        dp = DensityPenalty()
        all_gray = np.full((5, 5), 0.5)
        all_binary = np.array([[0.0, 1.0], [1.0, 0.0]])
        assert dp.compute_grayness(all_gray) == pytest.approx(1.0, rel=1e-6)
        assert dp.compute_grayness(all_binary) == pytest.approx(0.0, abs=1e-10)

    def test_gradient_shape(self):
        """M2: 梯度形状正确。"""
        dp = DensityPenalty(weight=1.0)
        density = np.random.rand(5, 5)
        grad = dp.compute_gradient(density)
        assert grad.shape == density.shape

    def test_gradient_at_05(self):
        """M2: 0.5 处梯度为 0（极值点）。"""
        dp = DensityPenalty(weight=1.0)
        density = np.array([0.5])
        grad = dp.compute_gradient(density)
        assert abs(grad[0]) < 1e-10


# ============================================================
# ProjectionConstraint 投影约束测试
# ============================================================
class TestProjectionConstraint:
    """ProjectionConstraint 投影约束测试。"""

    def test_init_default(self):
        """M1: 默认投影强度。"""
        pc = ProjectionConstraint()
        assert pc.beta == 5.0

    def test_binary_unchanged(self):
        """M1: 二值值投影后接近 0 或 1。"""
        pc = ProjectionConstraint(strength=10.0)
        density = np.array([0.0, 1.0])
        result = pc.project(density)
        assert result[0] < 0.1
        assert result[1] > 0.9

    def test_gray_pushed_to_binary(self):
        """M2: 高强度下灰度值被推向二值。"""
        pc = ProjectionConstraint(strength=50.0)
        gray = np.array([0.4, 0.6])
        result = pc.project(gray)
        assert result[0] < 0.1
        assert result[1] > 0.9

    def test_high_strength_more_binarization(self):
        """M2: 强度越大，二值化越强。"""
        density = np.array([0.4, 0.6])
        pc_low = ProjectionConstraint(strength=1.0)
        pc_high = ProjectionConstraint(strength=20.0)
        result_low = pc_low.project(density)
        result_high = pc_high.project(density)
        spread_low = abs(result_high[0] - result_high[1])
        spread_high = abs(result_low[0] - result_low[1])
        assert spread_low > spread_high

    def test_output_range(self):
        """M1: 输出在 (0, 1) 范围内。"""
        pc = ProjectionConstraint(strength=5.0)
        density = np.random.rand(10)
        result = pc.project(density)
        assert np.all(result > 0.0)
        assert np.all(result < 1.0)

    def test_gradient_shape(self):
        """M2: 梯度形状正确。"""
        pc = ProjectionConstraint(strength=5.0)
        density = np.random.rand(5, 5)
        grad = pc.compute_gradient(density)
        assert grad.shape == density.shape


# ============================================================
# DensityFilter 密度滤波测试
# ============================================================
class TestDensityFilter:
    """DensityFilter 密度滤波测试。"""

    def test_init_default(self):
        """M1: 默认 sigma。"""
        df = DensityFilter()
        assert df.sigma == 1.5

    def test_uniform_unchanged(self):
        """M1: 均匀密度滤波后基本不变。"""
        df = DensityFilter(sigma=2.0)
        uniform = np.ones((10, 10)) * 0.5
        filtered = df.filter(uniform)
        assert np.allclose(filtered, 0.5, atol=1e-3)

    def test_filter_smooths(self):
        """M2: 滤波平滑边缘。"""
        df = DensityFilter(sigma=2.0)
        sharp = np.zeros((10, 10))
        sharp[3:7, 3:7] = 1.0
        filtered = df.filter(sharp)
        assert filtered.min() >= 0.0
        assert filtered.max() <= 1.0
        assert filtered[0, 0] > 0.0 or filtered[5, 5] < 1.0

    def test_sigma_zero_identity(self):
        """M2: sigma=0 近似恒等映射。"""
        df = DensityFilter(sigma=0.0)
        density = np.random.rand(10, 10)
        filtered = df.filter(density)
        assert np.allclose(filtered, density, atol=1e-6)

    def test_output_shape(self):
        """M1: 输出形状与输入一致。"""
        df = DensityFilter(sigma=1.0)
        for shape in [(5, 5), (10, 20), (3, 3)]:
            density = np.random.rand(*shape)
            filtered = df.filter(density)
            assert filtered.shape == shape


# ============================================================
# ConnectivityConstraint 连通性约束测试
# ============================================================
class TestConnectivityConstraint:
    """ConnectivityConstraint 连通性约束测试。"""

    def test_init_default(self):
        """M1: 默认阈值。"""
        cc = ConnectivityConstraint()
        assert cc.threshold == 3

    def test_single_connected_region(self):
        """M1: 单连通区域无孤立区域。"""
        cc = ConnectivityConstraint(threshold=3)
        density = np.zeros((10, 10))
        density[2:8, 2:8] = 1.0
        result = cc.count_isolated_regions(density)
        assert result == 0

    def test_small_island_detected(self):
        """M2: 小岛被检测为孤立区域。"""
        cc = ConnectivityConstraint(threshold=10)
        density = np.zeros((20, 20))
        density[2:8, 2:8] = 1.0
        density[15:17, 15:17] = 1.0
        result = cc.count_isolated_regions(density)
        assert result >= 1

    def test_empty_density_zero(self):
        """M1: 空密度无孤立区域。"""
        cc = ConnectivityConstraint(threshold=3)
        density = np.zeros((10, 10))
        result = cc.count_isolated_regions(density)
        assert result == 0

    def test_check_connectivity_method(self):
        """M1: count_isolated_regions 方法存在。"""
        cc = ConnectivityConstraint()
        assert hasattr(cc, 'count_isolated_regions')
        density = np.zeros((5, 5))
        density[1:4, 1:4] = 1.0
        result = cc.count_isolated_regions(density)
        assert isinstance(result, int)


# ============================================================
# ConstraintMetrics 约束指标测试
# ============================================================
class TestConstraintMetrics:
    """ConstraintMetrics 约束指标测试。"""

    def test_default_zero(self):
        """M1: 默认值全为 0。"""
        cm = ConstraintMetrics()
        assert cm.density_penalty == 0.0
        assert cm.grayness == 0.0
        assert cm.min_feature_violation == 0
        assert cm.connectivity_violation == 0
        assert cm.total_violation == 0.0

    def test_total_violation_computation(self):
        """M2: total_violation 计算正确。"""
        cm = ConstraintMetrics(
            density_penalty=1.0,
            min_feature_violation=5,
            connectivity_violation=3,
        )
        expected = 1.0 + 5 * 0.1 + 3 * 0.1
        assert cm.total_violation == pytest.approx(expected)


# ============================================================
# FabricationConstraints 集成测试
# ============================================================
class TestFabricationConstraints:
    """FabricationConstraints 制造约束集成测试。"""

    def test_init_default(self):
        """M1: 默认初始化成功。"""
        fc = FabricationConstraints()
        assert isinstance(fc.config, FabricationConfig)
        assert isinstance(fc.density_penalty, DensityPenalty)
        assert isinstance(fc.projection, ProjectionConstraint)
        assert isinstance(fc.density_filter, DensityFilter)
        assert isinstance(fc.connectivity, ConnectivityConstraint)

    def test_init_with_config(self):
        """M1: 自定义配置初始化。"""
        cfg = FabricationConfig(projection_strength=10.0)
        fc = FabricationConstraints(config=cfg)
        assert fc.projection.beta == 10.0

    def test_apply_constraints_output_range(self):
        """M1: 约束输出在 [0, 1] 范围内。"""
        fc = FabricationConstraints()
        density = np.random.rand(20, 20)
        result = fc.apply_constraints(density)
        assert result.shape == density.shape
        assert result.min() >= 0.0
        assert result.max() <= 1.0

    def test_evaluate_returns_metrics(self):
        """M1: evaluate 返回 ConstraintMetrics。"""
        fc = FabricationConstraints()
        density = np.random.rand(10, 10)
        metrics = fc.evaluate(density)
        assert isinstance(metrics, ConstraintMetrics)
        assert metrics.grayness >= 0.0
        assert metrics.grayness <= 1.0

    def test_total_penalty_non_negative(self):
        """M2: 总惩罚非负。"""
        fc = FabricationConstraints()
        density = np.random.rand(10, 10)
        penalty = fc.compute_total_penalty(density)
        assert penalty >= 0.0

    def test_gradient_shape(self):
        """M2: 梯度形状与输入一致。"""
        fc = FabricationConstraints()
        density = np.random.rand(8, 8)
        grad = fc.compute_total_gradient(density)
        assert grad.shape == density.shape


# ============================================================
# eqDRC 方程化 DRC 测试
# ============================================================
class TestEqDRCRule:
    """EqDRCRule 方程化 DRC 规则测试。"""

    def test_init_minimal(self):
        """M1: 最小初始化。"""
        rule = EqDRCRule(
            name="WIDTH_RULE",
            category="WIDTH",
            equation="width >= 0.4",
            layer=(1, 0),
        )
        assert rule.name == "WIDTH_RULE"
        assert rule.category == "WIDTH"
        assert rule.tolerance == 0.0

    def test_init_full(self):
        """M1: 完整初始化。"""
        rule = EqDRCRule(
            name="BEND_RADIUS",
            category="BEND",
            equation="R >= 5.0",
            layer=(2, 1),
            tolerance=0.05,
            description="Min bend radius 5um",
            sources=["https://example.com"],
        )
        assert rule.tolerance == 0.05
        assert rule.description == "Min bend radius 5um"
        assert len(rule.sources) == 1


class TestEqDRCViolation:
    """EqDRCViolation eqDRC 违反项测试。"""

    def test_init(self):
        """M1: 初始化。"""
        v = EqDRCViolation(
            rule_name="WIDTH",
            layer=(1, 0),
            location=(10.0, 20.0),
            actual_value=0.3,
            expected_value=0.4,
            severity="ERROR",
            message="Width too small",
        )
        assert v.actual_value < v.expected_value
        assert v.severity == "ERROR"


class TestEqDRCEngine:
    """EqDRCEngine 方程化 DRC 引擎测试。"""

    def test_init_empty(self):
        """M1: 初始空规则集。"""
        engine = EqDRCEngine()
        assert len(engine.rules) == 0

    def test_add_rule_valid(self):
        """M1: 添加合法规则。"""
        engine = EqDRCEngine()
        rule = EqDRCRule(
            name="R1", category="WIDTH",
            equation="w >= 0.4", layer=(1, 0),
        )
        engine.add_rule(rule)
        assert len(engine.rules) == 1

    def test_add_rule_invalid_category_raises(self):
        """R03: 非法类别抛出异常。"""
        engine = EqDRCEngine()
        rule = EqDRCRule(
            name="R1", category="INVALID",
            equation="w >= 0.4", layer=(1, 0),
        )
        with pytest.raises(ValueError):
            engine.add_rule(rule)

    def test_check_width_pass(self):
        """M2: 宽度检查通过。"""
        engine = EqDRCEngine()
        polygon = [(0.0, 0.0), (10.0, 0.0), (10.0, 1.0), (0.0, 1.0)]
        violations = engine.check_width([polygon], layer=(1, 0), min_width=0.5)
        assert len(violations) == 0

    def test_check_width_fail(self):
        """M2: 宽度检查失败。"""
        engine = EqDRCEngine()
        polygon = [(0.0, 0.0), (10.0, 0.0), (10.0, 0.1), (0.0, 0.1)]
        violations = engine.check_width([polygon], layer=(1, 0), min_width=0.5)
        assert len(violations) == 1
        assert violations[0].severity == "ERROR"

    def test_check_width_tolerance(self):
        """M2: 容差放宽约束。"""
        engine = EqDRCEngine()
        polygon = [(0.0, 0.0), (10.0, 0.0), (10.0, 0.3), (0.0, 0.3)]
        violations_no_tol = engine.check_width(
            [polygon], layer=(1, 0), min_width=0.4, tolerance=0.0
        )
        violations_with_tol = engine.check_width(
            [polygon], layer=(1, 0), min_width=0.4, tolerance=0.2
        )
        assert len(violations_no_tol) == 1
        assert len(violations_with_tol) == 0

    def test_check_space_pass(self):
        """M2: 间距检查通过。"""
        engine = EqDRCEngine()
        p1 = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
        p2 = [(3.0, 0.0), (4.0, 0.0), (4.0, 1.0), (3.0, 1.0)]
        violations = engine.check_space([p1, p2], layer=(1, 0), min_space=1.0)
        assert len(violations) == 0

    def test_check_space_fail(self):
        """M2: 间距检查失败。"""
        engine = EqDRCEngine()
        p1 = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
        p2 = [(1.5, 0.0), (2.5, 0.0), (2.5, 1.0), (1.5, 1.0)]
        violations = engine.check_space([p1, p2], layer=(1, 0), min_space=1.0)
        assert len(violations) == 1

    def test_polygon_area(self):
        """M1: 多边形面积计算正确。"""
        square = [(0.0, 0.0), (2.0, 0.0), (2.0, 2.0), (0.0, 2.0)]
        assert _polygon_area(square) == pytest.approx(4.0)

    def test_point_segment_distance(self):
        """M1: 点到线段距离计算。"""
        a = (0.0, 0.0)
        b = (10.0, 0.0)
        p = (5.0, 3.0)
        d = _point_segment_distance(p, a, b)
        assert d == pytest.approx(3.0)


# ============================================================
# FoundryDRCRunset 代工厂规则集测试
# ============================================================
class TestFoundryDRCRunset:
    """FoundryDRCRunset 代工厂 DRC 规则集测试。"""

    def test_init(self):
        """M1: 初始化规则集。"""
        runset = FoundryDRCRunset(
            foundry_name="IHP",
            process_node="250nm",
            rules=[],
            certified=False,
            sources=["https://example.com"],
        )
        assert runset.foundry_name == "IHP"
        assert runset.process_node == "250nm"
        assert isinstance(runset.rules, list)
        assert runset.certified is False


# ============================================================
# FoundryDRCCertifier 代工厂 DRC 认证测试
# ============================================================
class TestFoundryDRCCertifier:
    """FoundryDRCCertifier 代工厂 DRC 认证测试。"""

    def test_init_default(self):
        """M1: 默认初始化。"""
        certifier = FoundryDRCCertifier()
        assert isinstance(certifier, FoundryDRCCertifier)

    def test_certify_runset(self):
        """M2: 认证 DRC runset。"""
        certifier = FoundryDRCCertifier()
        runset = FoundryDRCRunset(
            foundry_name="Test",
            process_node="Test",
            rules=[],
            certified=False,
            sources=[],
        )
        test_layout = {"waveguide": [], "devices": []}
        result = certifier.certify_runset(runset, test_layout)
        assert "foundry" in result
        assert "certified" in result
        assert "violation_count" in result
        assert "report" in result
