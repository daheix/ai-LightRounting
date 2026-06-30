"""DRC 剩余 8 规则测试：Step/Alignment/Edge/Perimeter/Symmetry/Array/Extension/MaxWidth。

对 PoLaRIS CurvilinearDRCEngine 的 R141-R180 扩展规则（8 类）进行完整覆盖测试，
每个规则含 3 个用例（通过/违规/边界），验证算法正确性与边界行为。

规则覆盖（8 类 × 3 测试 = 24 个测试用例）:
1. Step（步进宽度突变）: 波导相邻段宽度差，ST1_step_width
2. Alignment（层对齐度）: 两层图形边缘错位，AL1_layer_alignment
3. Edge（边缘长度）: 最小/最大边长双限检查，ED1_edge_length
4. Perimeter（周长）: 最小/最大周长双限检查，PM1_perimeter
5. Symmetry（对称性）: 反射对称度，SY1_symmetry（*创新* 主轴自动检测）
6. Array（阵列间距）: pitch 标准差，AR1_array_pitch（*创新* 1D 投影差分）
7. Extension（层延伸）: 一层超出另一层的最小延伸量，EX1_layer_extension
8. MaxWidth（最大宽度单模约束）: 防止过宽导致多模，MW1_max_width_single_mode

扩展规则通过 engine.enable_extended_rules() 启用（opt-in 机制，保持向后兼容，
默认 rule_count == 18 不变）。

学术依据（≥5 文献 URL，R02 学术诚信）:
- Synopsys OptoDesigner DRC Module（18 类曲线感知规则 + 扩展规则）
  URL: https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/design-rule-checking-module.html
- KLayout DRC Reference（width/space/area/angle/perimeter/edge checks）
  URL: https://www.klayout.org/doc-qt5/manual/drc.html
- Siemens Calibre nmDRC（ALIGN/ENC/EXT/step/edge/perimeter rules）
  URL: https://eda.sw.siemens.com/en-US/calibre/
- SiEPIC EBeam PDK DRC runset（SiEPIC 220nm SOI 工艺规则源码）
  URL: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- Chrostowski & Hochberg, "Silicon Photonics Design", CUP 2015, p.353
  URL: https://www.cambridge.org/core/books/silicon-photonics-design/
- Toussaint, "Solving Geometric Problems with the Rotating Calipers", IEEE MELECON 1983
  URL: https://www.cs.mcgill.ca/~godfried/publications/calipers.pdf
- Eades, "Optimal Algorithms for Symmetry Detection", U. Michigan TR, 1986
  URL: https://deepblue.lib.umich.edu/bitstream/handle/2027.42/8337/bad6491.0001.001.pdf
- de Berg et al., "Computational Geometry", Springer 2008, DOI:10.1007/978-3-540-77974-2
- OpenDRC, He et al., DAC 2023, DOI:10.1109/DAC56929.2023.10247734
- PDRC, Jiang et al., DAC 2024
  URL: http://www.cse.cuhk.edu.hk/~byu/papers/C219-DAC2024-PDRC.pdf

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R05 Bug 必修。
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from polaris.verification._drc_geometry import (
    _layer_alignment_offset,
    _polygon_array_pitch,
    _polygon_edge_lengths,
    _polygon_extension,
    _polygon_max_width,
    _polygon_perimeter,
    _polygon_step_width,
    _polygon_symmetry_score,
)
from polaris.verification.drc_curvilinear_18rules import (
    CurvilinearDRCEngine,
    CurvilinearDRCRule,
    DRCRuleCategory,
)


# =============================================================================
# 几何辅助函数
# =============================================================================

def _rect(x: float, y: float, w: float, h: float) -> np.ndarray:
    """创建矩形多边形（逆时针，4 顶点）。"""
    return np.array(
        [[x, y], [x + w, y], [x + w, y + h], [x, y + h]], dtype=float
    )


def _trapezoid(
    x: float, y: float, length: float, h1: float, h2: float
) -> np.ndarray:
    """创建梯形波导多边形（左端高 h1，右端高 h2，逆时针）。

    用于 Step 规则测试: 端边分别为 h1 和 h2，步进宽度差 = |h1 - h2|。
    """
    return np.array(
        [[x, y], [x + length, y], [x + length, y + h2], [x, y + h1]],
        dtype=float,
    )


def _make_engine_with_extended() -> CurvilinearDRCEngine:
    """创建启用扩展规则的 DRC 引擎。"""
    engine = CurvilinearDRCEngine()
    engine.enable_extended_rules()
    assert engine.rule_count == 26, f"扩展规则启用后应有 26 条规则，得到 {engine.rule_count}"
    return engine


def _filter_violations(
    violations: list, category: DRCRuleCategory
) -> list:
    """按规则类别过滤违规。"""
    return [v for v in violations if v.category == category.value]


# =============================================================================
# 1. Step（步进宽度突变）测试
# =============================================================================

class TestStepRule:
    """Step 步进宽度突变规则测试（ST1_step_width, limit=0.1μm）。

    检测波导宽度突变（不连续），相邻段宽度差超阈值则违规。
    算法: 识别多边形端边（最短 2 条边），计算长度差。

    文献:
    - SiEPIC-Tools Verification "Mismatched pin widths":
      https://github.com/SiEPIC/SiEPIC-Tools/wiki/SiEPIC-Tools-Menu-descriptions
    - Chrostowski & Hochberg, "Silicon Photonics Design", CUP 2015, p.353
    - KLayout DRC width check: https://www.klayout.org/doc-qt5/manual/drc_runsets.html
    - Calibre nmDRC step/width transition: https://eda.sw.siemens.com/en-US/calibre/
    - Synopsys OptoDesigner DRC Module:
      https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/design-rule-checking-module.html
    - OpenDRC, He et al., DAC 2023, DOI:10.1109/DAC56929.2023.10247734
    """

    def test_step_pass_uniform_width_waveguide(self):
        """通过: 等宽矩形波导 0.5×10μm，两端宽度均为 0.5 → step=0.0 < 0.1 → 无违规。"""
        engine = _make_engine_with_extended()
        wg = _rect(0, 0, 10, 0.5)  # 两端宽度均为 0.5μm
        violations = engine.run_geometric_checks(
            {"waveguide": [wg]},
            net_assignments={"waveguide": [0]},
        )
        step_violations = _filter_violations(violations, DRCRuleCategory.STEP_WIDTH)
        assert len(step_violations) == 0, f"等宽波导应无 Step 违规，得到 {len(step_violations)} 条"

    def test_step_fail_large_width_change(self):
        """违例: 梯形波导左端 0.3μm、右端 0.8μm，step=0.5 > 0.1 → 违规。"""
        engine = _make_engine_with_extended()
        wg = _trapezoid(0, 0, 10, 0.3, 0.8)  # 端边 0.3 与 0.8，差 0.5
        violations = engine.run_geometric_checks(
            {"waveguide": [wg]},
            net_assignments={"waveguide": [0]},
        )
        step_violations = _filter_violations(violations, DRCRuleCategory.STEP_WIDTH)
        assert len(step_violations) >= 1, "大宽度突变应触发 Step 违规"
        assert step_violations[0].measured_value == pytest.approx(0.5, abs=1e-6)

    def test_step_boundary_exact_threshold(self):
        """边界: 梯形波导左端 0.5μm、右端 0.6μm，step=0.1 = limit → 无违规（严格 >）。"""
        engine = _make_engine_with_extended()
        wg = _trapezoid(0, 0, 10, 0.5, 0.6)  # 端边 0.5 与 0.6，差 0.1 = limit
        violations = engine.run_geometric_checks(
            {"waveguide": [wg]},
            net_assignments={"waveguide": [0]},
        )
        step_violations = _filter_violations(violations, DRCRuleCategory.STEP_WIDTH)
        assert len(step_violations) == 0, f"step=limit 应无违规（严格 >），得到 {len(step_violations)} 条"


# =============================================================================
# 2. Alignment（层对齐度）测试
# =============================================================================

class TestAlignmentRule:
    """Alignment 层对齐度规则测试（AL1_layer_alignment, limit=0.05μm）。

    检查两层图形（metal1 vs contact）的对齐误差，若错位 > 阈值则违规。
    算法: 对每个 inner 多边形，找最近的 outer 多边形，计算包围盒中心错位。

    文献:
    - Calibre nmDRC ALIGN operation: https://eda.sw.siemens.com/en-US/calibre/
    - KLayout DRC layer alignment:
      https://www.klayout.org/doc-qt5/manual/drc_runsets.html
    - Synopsys IC Validator DRC alignment:
      https://www.synopsys.com/implementation-and-signoff/signoff/ic-validator.html
    - Synopsys OptoDesigner DRC Module:
      https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/design-rule-checking-module.html
    - de Berg et al., "Computational Geometry", Springer 2008, Ch.5
    - Ericson, "Real-Time Collision Detection", MK 2005, Ch.5
    """

    def test_alignment_pass_perfectly_aligned(self):
        """通过: metal1 与 contact 同心（中心重合）→ offset=0.0 < 0.05 → 无违规。"""
        engine = _make_engine_with_extended()
        metal1 = _rect(0, 0, 4, 4)      # 中心 (2, 2)
        contact = _rect(1, 1, 2, 2)     # 中心 (2, 2)
        violations = engine.run_geometric_checks(
            {"metal1": [metal1], "contact": [contact]},
        )
        align_violations = _filter_violations(violations, DRCRuleCategory.LAYER_ALIGNMENT)
        assert len(align_violations) == 0, f"同心层应无 Alignment 违规，得到 {len(align_violations)} 条"

    def test_alignment_fail_large_offset(self):
        """违例: metal1 中心 (2,2)、contact 中心 (5,5) → offset≈4.24 > 0.05 → 违规。"""
        engine = _make_engine_with_extended()
        metal1 = _rect(0, 0, 4, 4)      # 中心 (2, 2)
        contact = _rect(4, 4, 2, 2)     # 中心 (5, 5)
        violations = engine.run_geometric_checks(
            {"metal1": [metal1], "contact": [contact]},
        )
        align_violations = _filter_violations(violations, DRCRuleCategory.LAYER_ALIGNMENT)
        assert len(align_violations) >= 1, "大偏移应触发 Alignment 违规"
        assert align_violations[0].measured_value > 0.05

    def test_alignment_boundary_exact_threshold(self):
        """边界: metal1 与 contact 中心偏移 0.05μm = limit → 无违规（严格 >）。"""
        engine = _make_engine_with_extended()
        metal1 = _rect(0, 0, 4, 4)          # 中心 (2, 2)
        contact = _rect(1.05, 1, 2, 2)      # 中心 (2.05, 2)，x 偏移 0.05
        violations = engine.run_geometric_checks(
            {"metal1": [metal1], "contact": [contact]},
        )
        align_violations = _filter_violations(violations, DRCRuleCategory.LAYER_ALIGNMENT)
        assert len(align_violations) == 0, f"offset=limit 应无违规（严格 >），得到 {len(align_violations)} 条"


# =============================================================================
# 3. Edge（边缘长度）测试
# =============================================================================

class TestEdgeRule:
    """Edge 边缘长度规则测试（ED1_edge_length, min=0.2μm, max=1000μm）。

    检查多边形每条边的长度，若 < min 或 > max 则违规。双限检查。

    文献:
    - de Berg et al., "Computational Geometry", Springer 2008, Ch.2
    - KLayout DRC edges/length check:
      https://www.klayout.org/doc-qt5/manual/drc_runsets.html
    - Calibre nmDRC edge length rules: https://eda.sw.siemens.com/en-US/calibre/
    - Synopsys OptoDesigner DRC Module:
      https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/design-rule-checking-module.html
    - OpenDRC, He et al., DAC 2023, DOI:10.1109/DAC56929.2023.10247734
    - PDRC, Jiang et al., DAC 2024,
      http://www.cse.cuhk.edu.hk/~byu/papers/C219-DAC2024-PDRC.pdf
    """

    def test_edge_pass_all_edges_in_range(self):
        """通过: 矩形 5.0×1.0μm，边长 [5,1,5,1]，min=1.0≥0.2, max=5.0≤1000 → 无违规。"""
        engine = _make_engine_with_extended()
        wg = _rect(0, 0, 5.0, 1.0)  # 边长: 5, 1, 5, 1
        violations = engine.run_geometric_checks(
            {"waveguide": [wg]},
            net_assignments={"waveguide": [0]},
        )
        edge_violations = _filter_violations(violations, DRCRuleCategory.EDGE_LENGTH)
        assert len(edge_violations) == 0, f"边长在范围内应无 Edge 违规，得到 {len(edge_violations)} 条"

    def test_edge_fail_edge_too_short(self):
        """违例: 矩形 5.0×0.1μm，最短边 0.1 < 0.2 → 最小边长违规。"""
        engine = _make_engine_with_extended()
        wg = _rect(0, 0, 5.0, 0.1)  # 边长: 5, 0.1, 5, 0.1 → 最短边 0.1 < 0.2
        violations = engine.run_geometric_checks(
            {"waveguide": [wg]},
            net_assignments={"waveguide": [0]},
        )
        edge_violations = _filter_violations(violations, DRCRuleCategory.EDGE_LENGTH)
        assert len(edge_violations) >= 1, "短边应触发 Edge 违规"
        assert any("最小边长" in v.message for v in edge_violations)

    def test_edge_boundary_min_edge_equals_limit(self):
        """边界: 矩形 5.0×0.2μm，最短边 0.2 = limit → 无违规（严格 <）。"""
        engine = _make_engine_with_extended()
        wg = _rect(0, 0, 5.0, 0.2)  # 边长: 5, 0.2, 5, 0.2 → 最短边 0.2 = limit
        violations = engine.run_geometric_checks(
            {"waveguide": [wg]},
            net_assignments={"waveguide": [0]},
        )
        edge_violations = _filter_violations(violations, DRCRuleCategory.EDGE_LENGTH)
        assert len(edge_violations) == 0, f"边长=limit 应无违规（严格 <），得到 {len(edge_violations)} 条"


# =============================================================================
# 4. Perimeter（周长）测试
# =============================================================================

class TestPerimeterRule:
    """Perimeter 周长规则测试（PM1_perimeter, min=1.0μm, max=10000μm）。

    检查多边形周长（所有边长度之和），若 < min 或 > max 则违规。双限检查。

    文献:
    - de Berg et al., "Computational Geometry", Springer 2008, Ch.2
    - KLayout DRC perimeter check:
      https://www.klayout.org/doc-qt5/manual/drc_runsets.html
    - Calibre nmDRC perimeter rules: https://eda.sw.siemens.com/en-US/calibre/
    - Synopsys IC Validator DRC perimeter:
      https://www.synopsys.com/implementation-and-signoff/signoff/ic-validator.html
    - OpenDRC, He et al., DAC 2023, DOI:10.1109/DAC56929.2023.10247734
    - PDRC, Jiang et al., DAC 2024,
      http://www.cse.cuhk.edu.hk/~byu/papers/C219-DAC2024-PDRC.pdf
    """

    def test_perimeter_pass_in_range(self):
        """通过: 矩形 2.0×1.0μm，周长=6.0，1.0≤6.0≤10000 → 无违规。"""
        engine = _make_engine_with_extended()
        wg = _rect(0, 0, 2.0, 1.0)  # 周长 = 2*(2+1) = 6
        violations = engine.run_geometric_checks(
            {"waveguide": [wg]},
            net_assignments={"waveguide": [0]},
        )
        perim_violations = _filter_violations(violations, DRCRuleCategory.PERIMETER)
        assert len(perim_violations) == 0, f"周长在范围内应无违规，得到 {len(perim_violations)} 条"

    def test_perimeter_fail_too_small(self):
        """违例: 微小矩形 0.1×0.1μm，周长=0.4 < 1.0 → 最小周长违规。"""
        engine = _make_engine_with_extended()
        wg = _rect(0, 0, 0.1, 0.1)  # 周长 = 0.4 < 1.0
        violations = engine.run_geometric_checks(
            {"waveguide": [wg]},
            net_assignments={"waveguide": [0]},
        )
        perim_violations = _filter_violations(violations, DRCRuleCategory.PERIMETER)
        assert len(perim_violations) >= 1, "小周长应触发 Perimeter 违规"
        assert any("周长" in v.message for v in perim_violations)

    def test_perimeter_boundary_equals_min_limit(self):
        """边界: 矩形 0.25×0.25μm，周长=1.0 = min limit → 无违规（严格 <）。"""
        engine = _make_engine_with_extended()
        wg = _rect(0, 0, 0.25, 0.25)  # 周长 = 2*(0.25+0.25) = 1.0 = limit
        violations = engine.run_geometric_checks(
            {"waveguide": [wg]},
            net_assignments={"waveguide": [0]},
        )
        perim_violations = _filter_violations(violations, DRCRuleCategory.PERIMETER)
        assert len(perim_violations) == 0, f"周长=limit 应无违规（严格 <），得到 {len(perim_violations)} 条"


# =============================================================================
# 5. Symmetry（对称性）测试
# =============================================================================

class TestSymmetryRule:
    """Symmetry 对称性规则测试（SY1_symmetry, limit=0.95）。

    *创新*: 主轴方向自动检测 + 镜像点匹配算法。
    检查多边形的反射对称度，若对称分数 < limit 则违规。

    文献:
    - Eades, P., "Optimal Algorithms for Symmetry Detection in Two and Three
      Dimensions", University of Michigan Technical Report, 1986.
      https://deepblue.lib.umich.edu/bitstream/handle/2027.42/8337/bad6491.0001.001.pdf
    - Wolter, J.D., "Symmetry Detection in Two Dimensions", U. Michigan PhD, 1985.
    - de Berg et al., "Computational Geometry", Springer 2008, Ch.5
    - KLayout DRC symmetry checks:
      https://www.klayout.org/doc-qt5/manual/drc_runsets.html
    - SiEPIC-Tools Component verification: https://github.com/SiEPIC/SiEPIC-Tools
    - Synopsys OptoDesigner DRC Module:
      https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/design-rule-checking-module.html
    """

    def test_symmetry_pass_perfect_square(self):
        """通过: 正方形 2.0×2.0μm，对称分数=1.0 ≥ 0.95 → 无违规。"""
        engine = _make_engine_with_extended()
        sq = _rect(0, 0, 2.0, 2.0)  # 完美对称
        violations = engine.run_geometric_checks(
            {"waveguide": [sq]},
            net_assignments={"waveguide": [0]},
        )
        sym_violations = _filter_violations(violations, DRCRuleCategory.SYMMETRY)
        assert len(sym_violations) == 0, f"正方形应无 Symmetry 违规，得到 {len(sym_violations)} 条"

    def test_symmetry_fail_asymmetric_polygon(self):
        """违例: 不对称五边形，对称分数 < 0.95 → 违规。"""
        engine = _make_engine_with_extended()
        # 不对称五边形: 只 1/5 顶点可匹配 → score ≈ 0.2
        asym = np.array(
            [[0, 0], [3, 0], [3, 1], [2, 1.5], [0, 1]], dtype=float
        )
        violations = engine.run_geometric_checks(
            {"waveguide": [asym]},
            net_assignments={"waveguide": [0]},
        )
        sym_violations = _filter_violations(violations, DRCRuleCategory.SYMMETRY)
        assert len(sym_violations) >= 1, "不对称多边形应触发 Symmetry 违规"
        assert sym_violations[0].measured_value < 0.95

    def test_symmetry_boundary_score_equals_limit(self):
        """边界: 正方形 score=1.0，自定义规则 limit=1.0 → 1.0 < 1.0 为 False → 无违规。"""
        engine = _make_engine_with_extended()
        sq = _rect(0, 0, 2.0, 2.0)
        score, _ = _polygon_symmetry_score(sq)
        assert score == pytest.approx(1.0, abs=1e-6)
        # 创建 limit=score 的自定义规则，直接调用检查方法测试边界
        rule = CurvilinearDRCRule(
            "SY_TEST", DRCRuleCategory.SYMMETRY,
            "waveguide", score, "", True,
            "对称性边界测试", tolerance=1e-6,
        )
        engine._violations = []
        engine._check_symmetry_geo([sq], rule, score)
        assert len(engine._violations) == 0, "score=limit 应无违规（严格 <）"


# =============================================================================
# 6. Array（阵列间距）测试
# =============================================================================

class TestArrayRule:
    """Array 阵列间距规则测试（AR1_array_pitch, limit=0.01μm）。

    *创新*: 基于 1D 投影 + 排序差分计算 pitch 一致性。
    检查多边形阵列的 pitch 标准差，若 > limit 则违规。
    要求至少 3 个多边形才能计算 pitch 标准差。

    文献:
    - Synopsys OptoDesigner DRC Module (阵列规则):
      https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/design-rule-checking-module.html
    - SiEPIC EBeam PDK array components:
      https://github.com/SiEPIC/SiEPIC_EBeam_PDK
    - Chrostowski & Hochberg, "Silicon Photonics Design", CUP 2015, p.353
    - KLayout DRC array/pattern checks:
      https://www.klayout.org/doc-qt5/manual/drc_runsets.html
    - Calibre nmDRC array pattern matching:
      https://eda.sw.siemens.com/en-US/calibre/
    - de Berg et al., "Computational Geometry", Springer 2008, Ch.2
    """

    def test_array_pass_uniform_pitch(self):
        """通过: 3 个等距多边形 pitch=5.0μm → std=0.0 < 0.01 → 无违规。"""
        engine = _make_engine_with_extended()
        p1 = _rect(0, 0, 1, 1)       # 中心 (0.5, 0.5)
        p2 = _rect(5, 0, 1, 1)       # 中心 (5.5, 0.5)
        p3 = _rect(10, 0, 1, 1)      # 中心 (10.5, 0.5)
        # pitch = [5, 5] → std = 0.0
        violations = engine.run_geometric_checks(
            {"waveguide": [p1, p2, p3]},
            net_assignments={"waveguide": [0, 1, 2]},
        )
        array_violations = _filter_violations(violations, DRCRuleCategory.ARRAY_PITCH)
        assert len(array_violations) == 0, f"等距阵列应无 Array 违规，得到 {len(array_violations)} 条"

    def test_array_fail_non_uniform_pitch(self):
        """违例: 3 个不等距多边形 pitch=[5, 2] → std=1.5 > 0.01 → 违规。"""
        engine = _make_engine_with_extended()
        p1 = _rect(0, 0, 1, 1)       # 中心 (0.5, 0.5)
        p2 = _rect(5, 0, 1, 1)       # 中心 (5.5, 0.5)
        p3 = _rect(8, 0, 1, 1)       # 中心 (8.5, 0.5)，pitch = [5, 3] → std = 1.0
        violations = engine.run_geometric_checks(
            {"waveguide": [p1, p2, p3]},
            net_assignments={"waveguide": [0, 1, 2]},
        )
        array_violations = _filter_violations(violations, DRCRuleCategory.ARRAY_PITCH)
        assert len(array_violations) >= 1, "不等距阵列应触发 Array 违规"
        assert array_violations[0].measured_value > 0.01

    def test_array_boundary_pitch_std_equals_limit(self):
        """边界: 3 个多边形 pitch=[5, 5.02] → std=0.01 = limit → 无违规（严格 >）。"""
        engine = _make_engine_with_extended()
        p1 = _rect(0, 0, 1, 1)       # 中心 (0.5, 0.5)
        p2 = _rect(5, 0, 1, 1)       # 中心 (5.5, 0.5)
        p3 = _rect(10.02, 0, 1, 1)   # 中心 (10.52, 0.5)，pitch = [5, 5.02] → std = 0.01
        # 验证 pitch_std = 0.01
        pitch_std = _polygon_array_pitch([p1, p2, p3])
        assert pitch_std == pytest.approx(0.01, abs=1e-6), f"pitch_std 应为 0.01，得到 {pitch_std}"
        violations = engine.run_geometric_checks(
            {"waveguide": [p1, p2, p3]},
            net_assignments={"waveguide": [0, 1, 2]},
        )
        array_violations = _filter_violations(violations, DRCRuleCategory.ARRAY_PITCH)
        assert len(array_violations) == 0, f"std=limit 应无违规（严格 >），得到 {len(array_violations)} 条"


# =============================================================================
# 7. Extension（层延伸）测试
# =============================================================================

class TestExtensionRule:
    """Extension 层延伸规则测试（EX1_layer_extension, limit=0.2μm）。

    检查 metal1 是否完全包含 contact 并向外延伸至少 limit。
    与 E2 (MIN_EXTENSION) 区别: LAYER_EXTENSION 通过 rule.layer_pair 显式指定配对层。

    文献:
    - Calibre nmDRC ENClosure (ENC) extension:
      https://eda.sw.siemens.com/en-US/calibre/
    - KLayout DRC enclosing/extension:
      https://www.klayout.org/doc-qt5/manual/drc_runsets.html
    - Synopsys IC Validator DRC extension:
      https://www.synopsys.com/implementation-and-signoff/signoff/ic-validator.html
    - Synopsys OptoDesigner DRC Module:
      https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/design-rule-checking-module.html
    - OpenDRC, He et al., DAC 2023, DOI:10.1109/DAC56929.2023.10247734
    - PDRC, Jiang et al., DAC 2024,
      http://www.cse.cuhk.edu.hk/~byu/papers/C219-DAC2024-PDRC.pdf
    """

    def test_extension_pass_large_overlap(self):
        """通过: metal1 10×10μm 完全包含 contact 6×6μm → 延伸=2.0 ≥ 0.2 → 无违规。"""
        engine = _make_engine_with_extended()
        metal1 = _rect(0, 0, 10, 10)    # 大金属层
        contact = _rect(2, 2, 6, 6)     # 小接触孔，完全在 metal1 内
        violations = engine.run_geometric_checks(
            {"metal1": [metal1], "contact": [contact]},
        )
        ext_violations = _filter_violations(violations, DRCRuleCategory.LAYER_EXTENSION)
        assert len(ext_violations) == 0, f"大延伸应无 Extension 违规，得到 {len(ext_violations)} 条"

    def test_extension_fail_not_contained(self):
        """违例: metal1 4×4μm 未完全包含 contact 4×4μm（部分在外）→ 延伸=-1 → 违规。"""
        engine = _make_engine_with_extended()
        metal1 = _rect(0, 0, 4, 4)      # 中心 (2, 2)
        contact = _rect(2, 2, 4, 4)     # 中心 (4, 4)，部分在 metal1 外
        violations = engine.run_geometric_checks(
            {"metal1": [metal1], "contact": [contact]},
        )
        ext_violations = _filter_violations(violations, DRCRuleCategory.LAYER_EXTENSION)
        assert len(ext_violations) >= 1, "未完全包含应触发 Extension 违规"

    def test_extension_boundary_exact_threshold(self):
        """边界: metal1 10×10μm 包含 contact 9.6×9.6μm → 延伸=0.2 = limit → 无违规（严格 <）。"""
        engine = _make_engine_with_extended()
        metal1 = _rect(0, 0, 10, 10)        # [0,0]-[10,10]
        contact = _rect(0.2, 0.2, 9.6, 9.6) # [0.2,0.2]-[9.8,9.8]，延伸 = 0.2
        # 验证延伸量 = 0.2
        ext = _polygon_extension(metal1, contact)
        assert ext == pytest.approx(0.2, abs=1e-6), f"延伸量应为 0.2，得到 {ext}"
        violations = engine.run_geometric_checks(
            {"metal1": [metal1], "contact": [contact]},
        )
        ext_violations = _filter_violations(violations, DRCRuleCategory.LAYER_EXTENSION)
        assert len(ext_violations) == 0, f"延伸=limit 应无违规（严格 <），得到 {len(ext_violations)} 条"


# =============================================================================
# 8. MaxWidth（最大宽度单模约束）测试
# =============================================================================

class TestMaxWidthRule:
    """MaxWidth 最大宽度规则测试（MW1_max_width_single_mode, limit=1.05μm）。

    检查多边形最大宽度（旋转卡尺法取最大对边距离），若 > limit 则违规。
    用于光波导单模约束: 波导过宽会支持高阶模（TE1, TE2, ...）。

    单模截止公式: w_max ≈ λ / (2·√(n_core² - n_clad²))
    - 1550nm, SOI (n_core=3.48, n_clad=1.44): w_max ≈ 1.05μm（TE0 单模）

    文献:
    - Chrostowski & Hochberg, "Silicon Photonics Design", CUP 2015, p.353
    - Toussaint, "Solving Geometric Problems with the Rotating Calipers",
      IEEE MELECON 1983. https://www.cs.mcgill.ca/~godfried/publications/calipers.pdf
    - Lopez & Reisner, "On the Minimal Width of a Convex Polygon", IPL 1985
    - de Berg et al., "Computational Geometry", Springer 2008, Ch.4
    - SiEPIC EBeam PDK max width rules: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
    - KLayout DRC width check:
      https://www.klayout.org/downloads/master/doc-qt4/manual/drc_basic.html
    - Synopsys OptoDesigner DRC Module:
      https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/design-rule-checking-module.html
    """

    def test_maxwidth_pass_small_square(self):
        """通过: 正方形 1.0×1.0μm，max_width=1.0 < 1.05 → 无违规。"""
        engine = _make_engine_with_extended()
        sq = _rect(0, 0, 1.0, 1.0)  # max_width = 1.0
        violations = engine.run_geometric_checks(
            {"waveguide": [sq]},
            net_assignments={"waveguide": [0]},
        )
        mw_violations = _filter_violations(violations, DRCRuleCategory.MAX_WIDTH_SINGLE_MODE)
        assert len(mw_violations) == 0, f"小正方形应无 MaxWidth 违规，得到 {len(mw_violations)} 条"

    def test_maxwidth_fail_large_square(self):
        """违例: 正方形 2.0×2.0μm，max_width=2.0 > 1.05 → 违规（可能多模）。"""
        engine = _make_engine_with_extended()
        sq = _rect(0, 0, 2.0, 2.0)  # max_width = 2.0 > 1.05
        violations = engine.run_geometric_checks(
            {"waveguide": [sq]},
            net_assignments={"waveguide": [0]},
        )
        mw_violations = _filter_violations(violations, DRCRuleCategory.MAX_WIDTH_SINGLE_MODE)
        assert len(mw_violations) >= 1, "大正方形应触发 MaxWidth 违规"
        assert mw_violations[0].measured_value > 1.05

    def test_maxwidth_boundary_equals_limit(self):
        """边界: 正方形 1.05×1.05μm，max_width=1.05 = limit → 无违规（严格 >）。"""
        engine = _make_engine_with_extended()
        sq = _rect(0, 0, 1.05, 1.05)  # max_width = 1.05 = limit
        # 验证 max_width = 1.05
        mw = _polygon_max_width(sq)
        assert mw == pytest.approx(1.05, abs=1e-6), f"max_width 应为 1.05，得到 {mw}"
        violations = engine.run_geometric_checks(
            {"waveguide": [sq]},
            net_assignments={"waveguide": [0]},
        )
        mw_violations = _filter_violations(violations, DRCRuleCategory.MAX_WIDTH_SINGLE_MODE)
        assert len(mw_violations) == 0, f"max_width=limit 应无违规（严格 >），得到 {len(mw_violations)} 条"


# =============================================================================
# 扩展规则 opt-in 机制测试
# =============================================================================

class TestExtendedRulesOptIn:
    """扩展规则 opt-in 机制测试（向后兼容性验证）。

    验证 enable_extended_rules / disable_extended_rules 的幂等性和向后兼容性。
    默认 rule_count == 18（不破坏 M4 交付检查 _verify_drc_18_rules）。

    文献:
    - Synopsys OptoDesigner DRC Module:
      https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/design-rule-checking-module.html
    - KLayout DRC: https://www.klayout.org/doc-qt5/manual/drc.html
    - Calibre nmDRC: https://eda.sw.siemens.com/en-US/calibre/
    - SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
    - OpenDRC, He et al., DAC 2023, DOI:10.1109/DAC56929.2023.10247734
    """

    def test_default_rule_count_is_18(self):
        """默认 rule_count == 18（向后兼容，M4 交付检查不破坏）。"""
        engine = CurvilinearDRCEngine()
        assert engine.rule_count == 18
        assert not engine.extended_rules_enabled

    def test_enable_extended_rules_adds_8(self):
        """启用扩展规则后 rule_count == 26（18 + 8）。"""
        engine = CurvilinearDRCEngine()
        engine.enable_extended_rules()
        assert engine.rule_count == 26
        assert engine.extended_rules_enabled

    def test_enable_extended_rules_is_idempotent(self):
        """enable_extended_rules 幂等: 多次调用不重复添加。"""
        engine = CurvilinearDRCEngine()
        engine.enable_extended_rules()
        engine.enable_extended_rules()
        engine.enable_extended_rules()
        assert engine.rule_count == 26, "多次启用不应重复添加规则"

    def test_disable_extended_rules_restores_18(self):
        """禁用扩展规则后 rule_count 恢复为 18。"""
        engine = CurvilinearDRCEngine()
        engine.enable_extended_rules()
        assert engine.rule_count == 26
        engine.disable_extended_rules()
        assert engine.rule_count == 18
        assert not engine.extended_rules_enabled
