"""DRC 剩余 4 规则测试：Via / Area / Angle / End-of-Line。

对 PoLaRIS DRC 模块的 4 个核心规则进行完整覆盖测试，每个规则含 3 个通过
用例 + 3 个违例用例，验证算法正确性与边界行为。

规则覆盖:
1. Via（通孔规则）: 检查通孔尺寸（最小宽度）+ 间距，HierarchicalDRC._check_via
2. Area（面积规则）: 检查图形最小面积（鞋带公式），HierarchicalDRC._check_area
3. Angle（角度规则）: 检查图形拐角最大/最小角度，CurvilinearDRCEngine._check_*_angle_geo
4. End-of-Line（线端间距规则）: 检查波导端面间距，CurvilinearDRCEngine._check_end_to_end_geo

学术依据（≥5 文献 URL，R02 学术诚信）:
- SiEPIC EBeam PDK DRC runset（VIAC via/area/angle/eol 规则源码）
  URL: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- Chrostowski & Hochberg, "Silicon Photonics Design", Cambridge University Press 2015, p.353
  URL: https://www.cambridge.org/core/books/silicon-photonics-design/
- KLayout DRC Reference（width/space/area/angle/separation checks）
  URL: https://www.klayout.org/doc-qt5/manual/drc_runsets.html
- Siemens Calibre nmDRC（via/area/angle/EXTernal end-to-end rules）
  URL: https://eda.sw.siemens.com/en-US/calibre/
- Synopsys OptoDesigner DRC Module（18 类曲线感知规则）
  URL: https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/design-rule-checking-module.html
- OpenDRC, He et al., DAC 2023, DOI: 10.1109/DAC56929.2023.10247734
- PDRC, Jiang et al., DAC 2024
  URL: http://www.cse.cuhk.edu.hk/~byu/papers/C219-DAC2024-PDRC.pdf
- de Berg et al., "Computational Geometry: Algorithms and Applications", Springer 2008
  DOI: 10.1007/978-3-540-77974-2
- Ericson, "Real-Time Collision Detection", Morgan Kaufmann 2005, Ch.5
  URL: https://realtimecollisiondetection.net/
- Toussaint, "Solving Geometric Problems with the Rotating Calipers", IEEE MELECON 1983
  URL: https://www.cs.mcgill.ca/~godfried/publications/calipers.pdf

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R05 Bug 必修。
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from polaris.sim.hierarchical_drc import HierarchicalDRC
from polaris.sim.klayout_drc import DRCCheckType, DRCRule
from polaris.verification.drc_curvilinear_18rules import (
    CurvilinearDRCEngine,
    CurvilinearDRCRule,
    DRCRuleCategory,
)


# =============================================================================
# 几何辅助函数
# =============================================================================

def _rect(x: float, y: float, w: float, h: float) -> np.ndarray:
    """创建矩形多边形（逆时针）。"""
    return np.array([[x, y], [x + w, y], [x + w, y + h], [x, y + h]], dtype=float)


def _regular_polygon(n: int, r: float = 2.0) -> np.ndarray:
    """创建正 n 边形（半径 r，逆时针）。

    正 n 边形内角 = (n-2)*180/n 度。
    来源: de Berg, "Computational Geometry", Springer 2008。
    """
    return np.array(
        [[r * math.cos(2 * math.pi * k / n), r * math.sin(2 * math.pi * k / n)]
         for k in range(n)],
        dtype=float,
    )


def _make_via_rule(
    name: str = "VIA_TEST",
    layer: str = "VIAC",
    min_size: float = 0.5,
    min_space: float | None = 0.5,
) -> DRCRule:
    """创建 VIA 测试规则。"""
    return DRCRule(
        name=name,
        layer_name=layer,
        check_type=DRCCheckType.VIA,
        threshold_um=min_size,
        min_space_um=min_space,
    )


def _make_area_rule(
    name: str = "AREA_TEST",
    layer: str = "WG",
    min_area: float = 1.0,
) -> DRCRule:
    """创建 AREA 测试规则。"""
    return DRCRule(
        name=name,
        layer_name=layer,
        check_type=DRCCheckType.AREA,
        threshold_um=min_area,
    )


def _make_curve_rule(
    name: str,
    category: DRCRuleCategory,
    limit: float,
    layer: str = "waveguide",
    units: str = "μm",
) -> CurvilinearDRCRule:
    """创建 CurvilinearDRC 测试规则。"""
    return CurvilinearDRCRule(name, category, layer, limit, units)


# =============================================================================
# 1. Via（通孔规则）测试
# =============================================================================

class TestViaRule:
    """Via 通孔规则测试（尺寸+间距组合检查）。

    Via 检查 = 通孔最小尺寸（旋转卡尺法最小宽度）+ 通孔最小间距（边到边距离）。
    通孔（Via）连接不同金属层，最小尺寸保证光刻分辨率可识别，最小间距避免
    刻蚀后桥接短路。

    文献:
    - SiEPIC EBeam PDK via rules (VIAC min size/space):
      https://github.com/SiEPIC/SiEPIC_EBeam_PDK
    - Chrostowski & Hochberg, "Silicon Photonics Design", CUP 2015, p.353
    - KLayout DRC width_check/space_check:
      https://www.klayout.org/doc-qt5/manual/drc_runsets.html
    - Calibre nmDRC via rules: https://eda.sw.siemens.com/en-US/calibre/
    - Synopsys IC Validator: https://www.synopsys.com/implementation-and-signoff/signoff/ic-validator.html
    - Toussaint, "Rotating Calipers", IEEE MELECON 1983
      https://www.cs.mcgill.ca/~godfried/publications/calipers.pdf
    """

    def test_via_pass_single_large_via(self):
        """通过1: 单个大通孔 1.0×1.0μm，尺寸>0.5μm → 无违规。"""
        rule = _make_via_rule(min_size=0.5, min_space=0.5)
        drc = HierarchicalDRC([rule])
        via = _rect(0, 0, 1.0, 1.0)  # 1.0×1.0 通孔
        violations = drc.check({"VIAC": [via]}, hierarchical=False)
        assert len(violations) == 0, f"大通孔应无违规，得到 {len(violations)} 条"

    def test_via_pass_two_large_via_wide_spacing(self):
        """通过2: 两个大通孔 1.0×1.0μm，间距 2.0μm > 0.5μm → 无违规。"""
        rule = _make_via_rule(min_size=0.5, min_space=0.5)
        drc = HierarchicalDRC([rule])
        via1 = _rect(0, 0, 1.0, 1.0)
        via2 = _rect(3.0, 0, 1.0, 1.0)  # 间距 2.0μm
        violations = drc.check({"VIAC": [via1, via2]}, hierarchical=False)
        assert len(violations) == 0, f"远间距通孔应无违规，得到 {len(violations)} 条"

    def test_via_pass_via_at_threshold(self):
        """通过3: 两个 0.6×0.6μm 通孔，间距 0.6μm > 0.5μm（边界）→ 无违规。"""
        rule = _make_via_rule(min_size=0.5, min_space=0.5)
        drc = HierarchicalDRC([rule])
        via1 = _rect(0, 0, 0.6, 0.6)
        via2 = _rect(1.2, 0, 0.6, 0.6)  # 间距 0.6μm > 0.5μm
        violations = drc.check({"VIAC": [via1, via2]}, hierarchical=False)
        assert len(violations) == 0, f"边界尺寸/间距应无违规，得到 {len(violations)} 条"

    def test_via_fail_small_via_size(self):
        """违例1: 小通孔 0.3×0.3μm，尺寸 0.3μm < 0.5μm → 尺寸违规。"""
        rule = _make_via_rule(min_size=0.5, min_space=0.5)
        drc = HierarchicalDRC([rule])
        via = _rect(0, 0, 0.3, 0.3)  # 0.3μm 通孔 < 0.5μm
        violations = drc.check({"VIAC": [via]}, hierarchical=False)
        assert len(violations) >= 1, "小通孔应触发尺寸违规"
        assert any("通孔尺寸" in v.message or "宽度" in v.message for v in violations)

    def test_via_fail_close_spacing(self):
        """违例2: 两个 0.6×0.6μm 通孔，间距 0.1μm < 0.5μm → 间距违规。"""
        rule = _make_via_rule(min_size=0.5, min_space=0.5)
        drc = HierarchicalDRC([rule])
        via1 = _rect(0, 0, 0.6, 0.6)  # 尺寸 0.6 > 0.5 通过
        via2 = _rect(0.7, 0, 0.6, 0.6)  # 间距 0.1μm < 0.5μm
        violations = drc.check({"VIAC": [via1, via2]}, hierarchical=False)
        spacing_violations = [v for v in violations if "通孔间距" in v.message]
        assert len(spacing_violations) >= 1, "近间距通孔应触发间距违规"

    def test_via_fail_size_only_no_space(self):
        """违例3: 小通孔 0.4×0.4μm，min_space=None（仅检尺寸）→ 尺寸违规。"""
        rule = _make_via_rule(min_size=0.5, min_space=None)
        drc = HierarchicalDRC([rule])
        via = _rect(0, 0, 0.4, 0.4)  # 0.4μm < 0.5μm
        violations = drc.check({"VIAC": [via]}, hierarchical=False)
        assert len(violations) >= 1, "小通孔应触发尺寸违规"
        assert all("通孔间距" not in v.message for v in violations), \
            "min_space=None 时不应有间距违规"


# =============================================================================
# 2. Area（面积规则）测试
# =============================================================================

class TestAreaRule:
    """Area 面积规则测试（鞋带公式 Shoelace）。

    面积检查: 多边形面积（鞋带公式）< 阈值 → 违规。
    公式: Area = 0.5 * |Σ(x_i·y_{i+1} - x_{i+1}·y_i)|

    文献:
    - 鞋带公式 Shoelace formula: https://en.wikipedia.org/wiki/Shoelace_formula
    - de Berg et al., "Computational Geometry", Springer 2008, DOI:10.1007/978-3-540-77974-2
    - KLayout DRC area check: https://www.klayout.org/doc-qt5/manual/drc_runsets.html
    - Calibre nmDRC area rules: https://eda.sw.siemens.com/en-US/calibre/
    - OpenDRC, He et al., DAC 2023, DOI:10.1109/DAC56929.2023.10247734
    - PDRC, Jiang et al., DAC 2024, http://www.cse.cuhk.edu.hk/~byu/papers/C219-DAC2024-PDRC.pdf
    - SiEPIC EBeam PDK area rules: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
    """

    def test_area_pass_large_rectangle(self):
        """通过1: 大矩形 10×5=50μm² > 1.0μm² → 无违规。"""
        rule = _make_area_rule(min_area=1.0)
        drc = HierarchicalDRC([rule])
        rect = _rect(0, 0, 10, 5)  # 面积 50μm²
        violations = drc.check({"WG": [rect]}, hierarchical=False)
        assert len(violations) == 0, f"大矩形应无违规，得到 {len(violations)} 条"

    def test_area_pass_square_above_threshold(self):
        """通过2: 正方形 5×5=25μm² > 10μm² → 无违规。"""
        rule = _make_area_rule(min_area=10.0)
        drc = HierarchicalDRC([rule])
        square = _rect(0, 0, 5, 5)  # 面积 25μm²
        violations = drc.check({"WG": [square]}, hierarchical=False)
        assert len(violations) == 0, f"正方形应无违规，得到 {len(violations)} 条"

    def test_area_pass_at_threshold(self):
        """通过3: 矩形 2×2=4μm² > 1.0μm² → 无违规。"""
        rule = _make_area_rule(min_area=1.0)
        drc = HierarchicalDRC([rule])
        rect = _rect(0, 0, 2, 2)  # 面积 4μm²
        violations = drc.check({"WG": [rect]}, hierarchical=False)
        assert len(violations) == 0, f"矩形应无违规，得到 {len(violations)} 条"

    def test_area_fail_tiny_square(self):
        """违例1: 小正方形 1×1=1μm² < 10μm² → 违规。"""
        rule = _make_area_rule(min_area=10.0)
        drc = HierarchicalDRC([rule])
        square = _rect(0, 0, 1, 1)  # 面积 1μm² < 10μm²
        violations = drc.check({"WG": [square]}, hierarchical=False)
        assert len(violations) >= 1, "小正方形应触发面积违规"
        assert any("面积" in v.message for v in violations)

    def test_area_fail_small_rectangle(self):
        """违例2: 小矩形 2×2=4μm² < 10μm² → 违规。"""
        rule = _make_area_rule(min_area=10.0)
        drc = HierarchicalDRC([rule])
        rect = _rect(0, 0, 2, 2)  # 面积 4μm² < 10μm²
        violations = drc.check({"WG": [rect]}, hierarchical=False)
        assert len(violations) >= 1, "小矩形应触发面积违规"

    def test_area_fail_minimal_area(self):
        """违例3: 极小矩形 0.1×0.1=0.01μm² < 1.0μm² → 违规。"""
        rule = _make_area_rule(min_area=1.0)
        drc = HierarchicalDRC([rule])
        rect = _rect(0, 0, 0.1, 0.1)  # 面积 0.01μm² < 1.0μm²
        violations = drc.check({"WG": [rect]}, hierarchical=False)
        assert len(violations) >= 1, "极小矩形应触发面积违规"


# =============================================================================
# 3. Angle（角度规则）测试
# =============================================================================

class TestAngleRule:
    """Angle 角度规则测试（最大拐角 + 最小拐角）。

    角度检查: 多边形内角（向量点积 acos）> MAX_ANGLE 或 < MIN_ANGLE → 违规。
    公式: θ = acos((v1·v2)/(|v1|·|v2|))，v1=prev-curr, v2=next-curr

    文献:
    - de Berg et al., "Computational Geometry", Springer 2008, Ch.2 (角度计算)
      DOI: 10.1007/978-3-540-77974-2
    - KLayout DRC angle check: https://www.klayout.org/doc-qt5/manual/drc_runsets.html
    - Synopsys OptoDesigner DRC Module（角度规则）:
      https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/design-rule-checking-module.html
    - imec curvilinear DRC: https://www.imec-int.com/en/articles/curvilinear-technology-game-changer-logic-technology-roadmap
    - Calibre nmDRC angle rules: https://eda.sw.siemens.com/en-US/calibre/
    - OpenDRC, He et al., DAC 2023, DOI:10.1109/DAC56929.2023.10247734
    - PDRC, Jiang et al., DAC 2024, http://www.cse.cuhk.edu.hk/~byu/papers/C219-DAC2024-PDRC.pdf
    """

    def _run_angle_check(
        self, polys: list[np.ndarray], category: DRCRuleCategory, limit: float
    ) -> list:
        """运行单个角度规则检查，返回违规列表。"""
        engine = CurvilinearDRCEngine()
        engine._violations = []
        rule = _make_curve_rule("TEST_ANGLE", category, limit, units="°")
        if category == DRCRuleCategory.MAX_ANGLE:
            engine._check_max_angle_geo(polys, rule, limit)
        elif category == DRCRuleCategory.MIN_ANGLE:
            engine._check_min_angle_geo(polys, rule, limit)
        else:
            raise ValueError(f"不支持的角度类别: {category}")
        return list(engine._violations)

    def test_angle_pass_square(self):
        """通过1: 正方形（4×90°）→ max=90<135 通过，min=90 不<90 通过。"""
        square = _rect(0, 0, 4, 4)  # 4 个 90° 内角
        # MAX_ANGLE 135°: max=90 < 135 → 无违规
        max_violations = self._run_angle_check([square], DRCRuleCategory.MAX_ANGLE, 135.0)
        assert len(max_violations) == 0, f"正方形 max_angle 应无违规，得到 {len(max_violations)}"
        # MIN_ANGLE 90°: min=90 不 < 90 → 无违规
        min_violations = self._run_angle_check([square], DRCRuleCategory.MIN_ANGLE, 90.0)
        assert len(min_violations) == 0, f"正方形 min_angle 应无违规，得到 {len(min_violations)}"

    def test_angle_pass_regular_hexagon(self):
        """通过2: 正六边形（6×120°）→ max=120<135 通过。"""
        hexagon = _regular_polygon(6, r=2.0)  # 6 个 120° 内角
        angles = np.round(_polygon_angles_public(hexagon), 1)
        assert all(a == pytest.approx(120.0, abs=0.5) for a in angles)
        # MAX_ANGLE 135°: max=120 < 135 → 无违规
        max_violations = self._run_angle_check([hexagon], DRCRuleCategory.MAX_ANGLE, 135.0)
        assert len(max_violations) == 0, f"正六边形 max_angle 应无违规，得到 {len(max_violations)}"

    def test_angle_pass_regular_pentagon(self):
        """通过3: 正五边形（5×108°）→ max=108<135 通过，min=108>90 通过。"""
        pentagon = _regular_polygon(5, r=2.0)  # 5 个 108° 内角
        angles = np.round(_polygon_angles_public(pentagon), 1)
        assert all(a == pytest.approx(108.0, abs=0.5) for a in angles)
        # MAX_ANGLE 135°: max=108 < 135 → 无违规
        max_violations = self._run_angle_check([pentagon], DRCRuleCategory.MAX_ANGLE, 135.0)
        assert len(max_violations) == 0, f"正五边形 max_angle 应无违规"
        # MIN_ANGLE 90°: min=108 > 90 → 无违规
        min_violations = self._run_angle_check([pentagon], DRCRuleCategory.MIN_ANGLE, 90.0)
        assert len(min_violations) == 0, f"正五边形 min_angle 应无违规"

    def test_angle_fail_obtuse_triangle_max(self):
        """违例1: 钝角三角形（14°+14°+152°）→ max=152>135 违规。"""
        # 钝角三角形：底边 4，顶点 (2, 0.5)
        obtuse_tri = np.array([[0, 0], [4, 0], [2, 0.5]], dtype=float)
        angles = np.round(_polygon_angles_public(obtuse_tri), 1)
        assert angles.max() > 135.0, f"钝角三角形最大角应>135°，得到 {angles.max()}"
        # MAX_ANGLE 135°: max≈152 > 135 → 违规
        max_violations = self._run_angle_check([obtuse_tri], DRCRuleCategory.MAX_ANGLE, 135.0)
        assert len(max_violations) >= 1, "钝角三角形应触发 max_angle 违规"

    def test_angle_fail_equilateral_min(self):
        """违例2: 等边三角形（3×60°）→ min=60<90 违规。"""
        h = 4.0 * math.sqrt(3) / 2
        eq_tri = np.array([[0, 0], [4, 0], [2, h]], dtype=float)  # 3 个 60° 内角
        angles = np.round(_polygon_angles_public(eq_tri), 1)
        assert all(a == pytest.approx(60.0, abs=0.5) for a in angles)
        # MIN_ANGLE 90°: min=60 < 90 → 违规
        min_violations = self._run_angle_check([eq_tri], DRCRuleCategory.MIN_ANGLE, 90.0)
        assert len(min_violations) >= 1, "等边三角形应触发 min_angle 违规"

    def test_angle_fail_acute_triangle_both(self):
        """违例3: 锐角三角形（11°+11°+158°）→ max>135 且 min<90 双违规。"""
        # 极扁三角形：底边 4，顶点 (2, 0.4)
        acute_tri = np.array([[0, 0], [4, 0], [2, 0.4]], dtype=float)
        angles = np.round(_polygon_angles_public(acute_tri), 1)
        assert angles.max() > 135.0 and angles.min() < 90.0
        # MAX_ANGLE 135°: max≈158 > 135 → 违规
        max_violations = self._run_angle_check([acute_tri], DRCRuleCategory.MAX_ANGLE, 135.0)
        assert len(max_violations) >= 1, "锐角三角形应触发 max_angle 违规"
        # MIN_ANGLE 90°: min≈11 < 90 → 违规
        min_violations = self._run_angle_check([acute_tri], DRCRuleCategory.MIN_ANGLE, 90.0)
        assert len(min_violations) >= 1, "锐角三角形应触发 min_angle 违规"


# =============================================================================
# 4. End-of-Line（线端间距规则）测试
# =============================================================================

class TestEndOfLineRule:
    """End-of-Line 线端间距规则测试（端边识别 + 边到边距离）。

    EOL 检查: 识别每个多边形的端边（最短边），计算多边形对端边间最短距离，
    若 < 阈值 → 违规。用于波导耦合器等场景：两条波导端部面对面需保证最小间距。

    文献:
    - Calibre nmDRC EXTernal end-to-end spacing: https://eda.sw.siemens.com/en-US/calibre/
    - KLayout DRC separation (sep) check:
      https://www.klayout.org/doc-qt5/manual/drc_runsets.html
    - Ericson, "Real-Time Collision Detection", MK 2005, Ch.5
      https://realtimecollisiondetection.net/
    - de Berg et al., "Computational Geometry", Springer 2008, Ch.2 (线段距离)
      DOI: 10.1007/978-3-540-77974-2
    - OpenDRC, He et al., DAC 2023, DOI:10.1109/DAC56929.2023.10247734
    - PDRC, Jiang et al., DAC 2024, http://www.cse.cuhk.edu.hk/~byu/papers/C219-DAC2024-PDRC.pdf
    - SiEPIC EBeam PDK end-to-end rules: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
    """

    def _run_eol_check(
        self, polys: list[np.ndarray], limit: float = 0.6
    ) -> list:
        """运行 EOL 端到端间距检查，返回违规列表。"""
        engine = CurvilinearDRCEngine()
        engine._violations = []
        rule = _make_curve_rule("TEST_EOL", DRCRuleCategory.MIN_END_TO_END, limit)
        engine._check_end_to_end_geo(polys, rule, limit)
        return list(engine._violations)

    def test_eol_pass_wide_gap(self):
        """通过1: 两条波导端部间距 2.0μm > 0.6μm → 无违规。"""
        # 两条水平波导 5×0.5，端部面对面，间距 2.0μm
        wg1 = _rect(0, 0, 5, 0.5)
        wg2 = _rect(7.0, 0, 5, 0.5)  # 间距 2.0μm
        violations = self._run_eol_check([wg1, wg2], limit=0.6)
        assert len(violations) == 0, f"远间距端面应无违规，得到 {len(violations)} 条"

    def test_eol_pass_single_polygon(self):
        """通过2: 单条波导 → 无违规（端到端需 ≥2 多边形）。"""
        wg = _rect(0, 0, 5, 0.5)
        violations = self._run_eol_check([wg], limit=0.6)
        assert len(violations) == 0, f"单条波导应无违规，得到 {len(violations)} 条"

    def test_eol_pass_moderate_gap(self):
        """通过3: 两条波导端部间距 1.0μm > 0.6μm → 无违规。"""
        wg1 = _rect(0, 0, 5, 0.5)
        wg2 = _rect(6.0, 0, 5, 0.5)  # 间距 1.0μm > 0.6μm
        violations = self._run_eol_check([wg1, wg2], limit=0.6)
        assert len(violations) == 0, f"中等间距端面应无违规，得到 {len(violations)} 条"

    def test_eol_fail_close_end_to_end(self):
        """违例1: 两条波导端部间距 0.1μm < 0.6μm → 违规。"""
        wg1 = _rect(0, 0, 5, 0.5)
        wg2 = _rect(5.1, 0, 5, 0.5)  # 间距 0.1μm < 0.6μm
        violations = self._run_eol_check([wg1, wg2], limit=0.6)
        assert len(violations) >= 1, "近端面应触发 EOL 违规"
        assert any("端到端" in v.message for v in violations)

    def test_eol_fail_moderate_close(self):
        """违例2: 两条波导端部间距 0.3μm < 0.6μm → 违规。"""
        wg1 = _rect(0, 0, 5, 0.5)
        wg2 = _rect(5.3, 0, 5, 0.5)  # 间距 0.3μm < 0.6μm
        violations = self._run_eol_check([wg1, wg2], limit=0.6)
        assert len(violations) >= 1, "中等近端面应触发 EOL 违规"

    def test_eol_fail_just_below_threshold(self):
        """违例3: 两条波导端部间距 0.5μm < 0.6μm（边界下）→ 违规。"""
        wg1 = _rect(0, 0, 5, 0.5)
        wg2 = _rect(5.5, 0, 5, 0.5)  # 间距 0.5μm < 0.6μm
        violations = self._run_eol_check([wg1, wg2], limit=0.6)
        assert len(violations) >= 1, "边界下端面应触发 EOL 违规"


# =============================================================================
# 辅助：公开 _polygon_angles 供测试断言验证
# =============================================================================

def _polygon_angles_public(poly: np.ndarray) -> np.ndarray:
    """封装 _polygon_angles 供测试验证角度值。

    来源: polaris.verification._drc_geometry._polygon_angles
    """
    from polaris.verification._drc_geometry import _polygon_angles
    return _polygon_angles(poly)
