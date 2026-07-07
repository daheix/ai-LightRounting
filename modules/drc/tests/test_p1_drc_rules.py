"""P1 DRC 7 条规则回归测试（R383，2026-07-07）。

覆盖 4 条跨层规则（SEPARATION/ENCLOSURE/EXTENSION/EXCLUSION）+ 3 条波导级
规则（ANGLE_LIMIT/WAVEGUIDE_TAPER_ANGLE/SINGLEMODE_WIDTH）+ V 参数推导数值
验证 + R05 Bug 修复验证（MW1 1.05→1.0）。

每条规则 1 个 pass 用例 + 1 个 violation 用例 = 14 测试 + 2 验证测试 = 16 测试。

学术依据（R02 学术诚信，≥5 个文献 URL）:
- gdsfactory DRC notebook（check_separation/enclosing）
  http://raw.githubusercontent.com/gdsfactory/gdsfactory-photonics-training/main/notebooks/11_drc.ipynb
- SiEPIC EBeam PDK（VIAC_M1_ENCLOSURE=0.5μm）
  https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- KLayout DRC 文档（separation_check/enclosed_check）
  https://www.klayout.org/doc-qt5/manual/drc_runsets.html
- FluxCore DRC（ANGLE_LIMIT/EXCLUSION）
  https://www.fluxcoredynamics.com/docs/design-rules
- Snyder & Love 1983 §13.5（V 参数 V<2.405 单模条件）
  https://link.springer.com/book/10.1007/978-94-009-6875-2
- Milton & Burns 1987 JLT（绝热锥形）
  https://opg.optica.org/jlt/abstract.cfm?uri=jl-5-8-1079
- Soref 1991 IEEE JQE（SOI 单模条形波导）
  https://doi.org/10.1109/3.84143

合规: R02 学术诚信 / R03 禁止 fall-back（真实几何数据）/ R04 不参与 GPU
      / R05 Bug 必修（MW1 1.05→1.0 回归测试防复发）。
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

# 让测试既能从已安装包导入，也能从源码树导入（CI/开发模式）
_SRC = str(Path(__file__).resolve().parents[1] / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from polaris_drc import DRCEngine  # noqa: E402
from polaris_drc.rules import CheckType, DRCRule  # noqa: E402

# =========================================================================
# 辅助函数：构造最小 circuit + placements
# =========================================================================


def _make_circuit(devices: list[dict],
                  connections: list | None = None,
                  canvas: float = 200.0) -> dict:
    """构造最小合法 circuit dict。"""
    return {
        "name": "test_p1",
        "canvas_w": canvas,
        "canvas_h": canvas,
        "devices": devices,
        "connections": connections or [],
    }


def _dev(name: str, dev_type: str = "waveguide",
         params: dict | None = None,
         ports: list | None = None) -> dict:
    """构造器件 dict。"""
    d = {"name": name, "type": dev_type, "params": params or {}}
    if ports:
        d["ports"] = ports
    return d


def _pl(name: str, x: float, y: float, w: float, h: float) -> dict:
    """构造 placement 条目。"""
    return {name: {"x": x, "y": y, "w": w, "h": h}}


def _run_single_rule(rule: DRCRule, circuit: dict, placements: dict) -> list:
    """用只含单条规则的引擎运行检查。"""
    engine = DRCEngine(rules=[rule], bend_compensate=False)
    return engine.run(circuit, placements)


# =========================================================================
# 1. SEPARATION 跨层最小间距
# =========================================================================


class TestSeparation:
    """SEPARATION: 跨层器件 AABB 间距 < 1.0μm 违规。"""

    def test_pass(self):
        """两层器件间距 2.0μm ≥ 1.0μm，无违规。"""
        rule = DRCRule(name="SEPARATION", check_type=CheckType.SEPARATION,
                       threshold=1.0, severity=0.9,
                       layer_pair="M1_HEATER")
        circuit = _make_circuit([
            _dev("heater", params={"layer": "HEATER"}),
            _dev("metal", params={"layer": "M1"}),
        ])
        placements = {**_pl("heater", 0, 0, 10, 10), **_pl("metal", 12, 0, 10, 10)}
        violations = _run_single_rule(rule, circuit, placements)
        assert violations == []

    def test_violation(self):
        """两层器件间距 0.5μm < 1.0μm，1 个违规。"""
        rule = DRCRule(name="SEPARATION", check_type=CheckType.SEPARATION,
                       threshold=1.0, severity=0.9,
                       layer_pair="M1_HEATER")
        circuit = _make_circuit([
            _dev("heater", params={"layer": "HEATER"}),
            _dev("metal", params={"layer": "M1"}),
        ])
        placements = {**_pl("heater", 0, 0, 10, 10), **_pl("metal", 10.5, 0, 10, 10)}
        violations = _run_single_rule(rule, circuit, placements)
        assert len(violations) == 1
        assert violations[0].rule_name == "SEPARATION"


# =========================================================================
# 2. ENCLOSURE 包围
# =========================================================================


class TestEnclosure:
    """ENCLOSURE: 内层器件被外层包围量 < 0.5μm 违规。"""

    def test_pass(self):
        """VIAC 被 M1 包围 1.0μm ≥ 0.5μm，无违规。"""
        rule = DRCRule(name="ENCLOSURE", check_type=CheckType.ENCLOSURE,
                       threshold=0.5, severity=0.9,
                       layer_pair="M1_HEATER")
        circuit = _make_circuit([
            _dev("viac", params={"layer": "VIAC"}),
            _dev("metal", params={"layer": "M1"}),
        ])
        # VIAC (1,1,8,8) AABB=(1,1,9,9) 在 M1 (0,0,10,10) 内，四边包围量=1μm
        placements = {**_pl("viac", 1, 1, 8, 8), **_pl("metal", 0, 0, 10, 10)}
        violations = _run_single_rule(rule, circuit, placements)
        assert violations == []

    def test_violation(self):
        """VIAC 被 M1 包围 0.2μm < 0.5μm，1 个违规。"""
        rule = DRCRule(name="ENCLOSURE", check_type=CheckType.ENCLOSURE,
                       threshold=0.5, severity=0.9,
                       layer_pair="M1_HEATER")
        circuit = _make_circuit([
            _dev("viac", params={"layer": "VIAC"}),
            _dev("metal", params={"layer": "M1"}),
        ])
        # VIAC (0.2,0.2,9.6,9.6) 在 M1 (0,0,10,10) 内，包围量=0.2μm
        placements = {**_pl("viac", 0.2, 0.2, 9.6, 9.6),
                      **_pl("metal", 0, 0, 10, 10)}
        violations = _run_single_rule(rule, circuit, placements)
        assert len(violations) == 1
        assert violations[0].rule_name == "ENCLOSURE"


# =========================================================================
# 3. EXTENSION 延伸
# =========================================================================


class TestExtension:
    """EXTENSION: 外层延伸超出内层的量 < 0.2μm 违规。"""

    def test_pass(self):
        """metal 延伸超出 contact 1.0μm ≥ 0.2μm，无违规。"""
        rule = DRCRule(name="EXTENSION", check_type=CheckType.EXTENSION,
                       threshold=0.2, severity=0.7,
                       layer_pair="CONTACT")
        circuit = _make_circuit([
            _dev("contact", params={"layer": "CONTACT"}),
            _dev("metal", params={"layer": "METAL1"}),
        ])
        # CONTACT (1,1,8,8) 在 METAL1 (0,0,10,10) 内，延伸量=1μm
        placements = {**_pl("contact", 1, 1, 8, 8),
                      **_pl("metal", 0, 0, 10, 10)}
        violations = _run_single_rule(rule, circuit, placements)
        assert violations == []

    def test_violation(self):
        """metal 延伸超出 contact 0.1μm < 0.2μm，1 个违规。"""
        rule = DRCRule(name="EXTENSION", check_type=CheckType.EXTENSION,
                       threshold=0.2, severity=0.7,
                       layer_pair="CONTACT")
        circuit = _make_circuit([
            _dev("contact", params={"layer": "CONTACT"}),
            _dev("metal", params={"layer": "METAL1"}),
        ])
        # CONTACT (0.1,0.1,9.7,9.7) AABB=(0.1,0.1,9.8,9.8) 在 METAL1 内，延伸量=0.1μm
        placements = {**_pl("contact", 0.1, 0.1, 9.7, 9.7),
                      **_pl("metal", 0, 0, 10, 10)}
        violations = _run_single_rule(rule, circuit, placements)
        assert len(violations) == 1
        assert violations[0].rule_name == "EXTENSION"


# =========================================================================
# 4. EXCLUSION 禁止层重叠
# =========================================================================


class TestExclusion:
    """EXCLUSION: 跨层器件 AABB 重叠违规（零容忍）。"""

    def test_pass(self):
        """两层器件不重叠，无违规。"""
        rule = DRCRule(name="EXCLUSION", check_type=CheckType.EXCLUSION,
                       threshold=0.0, severity=1.0,
                       layer_pair="DEEPTRENCH")
        circuit = _make_circuit([
            _dev("wg", params={"layer": "WG"}),
            _dev("dt", params={"layer": "DEEPTRENCH"}),
        ])
        placements = {**_pl("wg", 0, 0, 10, 10), **_pl("dt", 20, 0, 10, 10)}
        violations = _run_single_rule(rule, circuit, placements)
        assert violations == []

    def test_violation(self):
        """两层器件重叠，1 个违规。"""
        rule = DRCRule(name="EXCLUSION", check_type=CheckType.EXCLUSION,
                       threshold=0.0, severity=1.0,
                       layer_pair="DEEPTRENCH")
        circuit = _make_circuit([
            _dev("wg", params={"layer": "WG"}),
            _dev("dt", params={"layer": "DEEPTRENCH"}),
        ])
        placements = {**_pl("wg", 0, 0, 10, 10), **_pl("dt", 5, 0, 10, 10)}
        violations = _run_single_rule(rule, circuit, placements)
        assert len(violations) == 1
        assert violations[0].rule_name == "EXCLUSION"


# =========================================================================
# 5. ANGLE_LIMIT 路径段角度范围
# =========================================================================


class TestAngleLimit:
    """ANGLE_LIMIT: 路径段内角 ∈ [45°, 135°] 否则违规。"""

    def test_pass(self):
        """路径段内角 90° ∈ [45°, 135°]，无违规。"""
        rule = DRCRule(name="ANGLE_LIMIT", check_type=CheckType.ANGLE_LIMIT,
                       threshold=45.0, severity=0.7, limit_max=135.0)
        circuit = _make_circuit([_dev("wg", params={"path_angle": 90.0})])
        placements = _pl("wg", 0, 0, 10, 1)
        violations = _run_single_rule(rule, circuit, placements)
        assert violations == []

    def test_violation(self):
        """路径段内角 30° < 45°，1 个违规。"""
        rule = DRCRule(name="ANGLE_LIMIT", check_type=CheckType.ANGLE_LIMIT,
                       threshold=45.0, severity=0.7, limit_max=135.0)
        circuit = _make_circuit([_dev("wg", params={"path_angle": 30.0})])
        placements = _pl("wg", 0, 0, 10, 1)
        violations = _run_single_rule(rule, circuit, placements)
        assert len(violations) == 1
        assert violations[0].rule_name == "ANGLE_LIMIT"


# =========================================================================
# 6. WAVEGUIDE_TAPER_ANGLE 锥形过渡角度
# =========================================================================


class TestWaveguideTaperAngle:
    """WAVEGUIDE_TAPER_ANGLE: 锥形半顶角 ≤ 10° 否则违规。"""

    def test_pass(self):
        """锥形 w_in=0.5, w_out=1.0, L=10 → 半顶角 1.43° ≤ 10°，无违规。"""
        rule = DRCRule(name="WAVEGUIDE_TAPER_ANGLE",
                       check_type=CheckType.WAVEGUIDE_TAPER_ANGLE,
                       threshold=10.0, severity=0.8)
        circuit = _make_circuit([_dev("taper", params={
            "width_in_um": 0.5, "width_out_um": 1.0, "length_um": 10.0})])
        placements = _pl("taper", 0, 0, 10, 1)
        violations = _run_single_rule(rule, circuit, placements)
        assert violations == []

    def test_violation(self):
        """锥形 w_in=0.5, w_out=5.0, L=5 → 半顶角 26.57° > 10°，1 个违规。"""
        rule = DRCRule(name="WAVEGUIDE_TAPER_ANGLE",
                       check_type=CheckType.WAVEGUIDE_TAPER_ANGLE,
                       threshold=10.0, severity=0.8)
        circuit = _make_circuit([_dev("taper", params={
            "width_in_um": 0.5, "width_out_um": 5.0, "length_um": 5.0})])
        placements = _pl("taper", 0, 0, 5, 5)
        violations = _run_single_rule(rule, circuit, placements)
        assert len(violations) == 1
        assert violations[0].rule_name == "WAVEGUIDE_TAPER_ANGLE"


# =========================================================================
# 7. SINGLEMODE_WIDTH 单模波导宽度上限
# =========================================================================


class TestSinglemodeWidth:
    """SINGLEMODE_WIDTH: 波导宽度 ≤ 1.0μm 否则违规。"""

    def test_pass(self):
        """波导宽度 0.5μm ≤ 1.0μm，无违规。"""
        rule = DRCRule(name="SINGLEMODE_WIDTH",
                       check_type=CheckType.SINGLEMODE_WIDTH,
                       threshold=1.0, severity=0.8)
        circuit = _make_circuit([_dev("wg", params={"width_um": 0.5})])
        placements = _pl("wg", 0, 0, 10, 0.5)
        violations = _run_single_rule(rule, circuit, placements)
        assert violations == []

    def test_violation(self):
        """波导宽度 1.5μm > 1.0μm，1 个违规。"""
        rule = DRCRule(name="SINGLEMODE_WIDTH",
                       check_type=CheckType.SINGLEMODE_WIDTH,
                       threshold=1.0, severity=0.8)
        circuit = _make_circuit([_dev("wg", params={"width_um": 1.5})])
        placements = _pl("wg", 0, 0, 10, 1.5)
        violations = _run_single_rule(rule, circuit, placements)
        assert len(violations) == 1
        assert violations[0].rule_name == "SINGLEMODE_WIDTH"


# =========================================================================
# 8. V 参数推导数值验证（R05 Bug 修复防复发）
# =========================================================================


class TestVParameterDerivation:
    """V 参数单模条件数学验证（Snyder & Love 1983 §13.5）。

    V 参数 V = (2π/λ) × (W/2) × √(n_core² - n_clad²) < 2.405 严格适用于
    圆对称光纤。对矩形 SOI 波导，块材料 n_Si=3.476 算出 W_max≈0.375μm
    过保守（Grillot 2006 JLT 方形<320nm 单模接近此值），不适用于 220nm×W
    矩形波导。MW1=1.0μm 来自 Soref 1991 IEEE JQE 全矢量数值仿真 + SiEPIC
    EBeam PDK 工程经验，非简单 V 参数推导（R02 学术诚信修正）。
    """

    def test_v_parameter_singlemode_width_max(self):
        """验证 V 参数公式数学正确性（块材料过保守，非 MW1=1.0μm 来源）。

        V 参数（块材料 n_Si=3.476）推导 W_max≈0.375μm，对应方形 SOI
        <320nm 单模（Grillot 2006 JLT）。MW1=1.0μm 来自 Soref 1991 全矢量
        仿真 + SiEPIC PDK 经验，非此 V 参数推导。
        """
        wavelength = 1.55  # μm
        n_core = 3.476  # Si @ 1550nm
        n_clad = 1.444  # SiO2 @ 1550nm
        v_cutoff = 2.405  # LP11 截止（Snyder & Love 1983 §13.5）
        # 块材料 V 参数推导（过保守，仅适用于方形/圆对称）
        w_max_block = 2.0 * v_cutoff * wavelength / (
            2.0 * math.pi * math.sqrt(n_core ** 2 - n_clad ** 2))
        # 数学验证: W_max_block ≈ 0.375μm（非 1.0μm）
        assert 0.36 <= w_max_block <= 0.39, (
            f"V 参数块材料推导 W_max={w_max_block:.4f}μm，应 ≈ 0.375μm")
        # 反向验证: W=1.0μm 时 V 值 > 2.405（块材料过保守）
        v_at_1um = (2.0 * math.pi / wavelength) * (1.0 / 2.0) * math.sqrt(
            n_core ** 2 - n_clad ** 2)
        assert v_at_1um > 2.405, (
            f"W=1.0μm 时 V={v_at_1um:.3f} > 2.405，块材料 V 参数过保守，"
            "MW1=1.0μm 来自 Soref 1991 全矢量仿真（非 V 参数）")

    def test_r05_bugfix_mw1_is_1_0_not_1_05(self):
        """验证 drc_curvilinear_18rules MW1 已修正为 1.0μm（R05 防复发）。

        用 importlib 直接加载模块文件，绕过 polaris_verify_advanced 包
        __init__.py 的 networkx 依赖（graph_lvs），仅测试目标规则文件
        （更精确的单元测试，非 fall-back）。
        """
        import importlib.util
        mod_path = (Path(__file__).resolve().parents[2] /
                    "verify_advanced" / "src" / "polaris_verify_advanced" /
                    "drc_curvilinear_18rules.py")
        spec = importlib.util.spec_from_file_location(
            "drc_curvilinear_18rules_isolated", mod_path)
        assert spec is not None and spec.loader is not None, (
            f"无法加载模块文件: {mod_path}")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        engine = mod.CurvilinearDRCEngine()
        mw1 = [r for r in engine._rules
               if r.name == "MW1_max_width_single_mode"]
        assert len(mw1) == 1, "MW1_max_width_single_mode 规则应存在"
        assert mw1[0].limit_value == 1.0, (
            f"MW1={mw1[0].limit_value}μm，应为 1.0μm（R05 修正，非 1.05μm）")


# =========================================================================
# 9. DEFAULT_DRC_RULES 覆盖率验证（25 条 = 12 基础 + 6 P0 + 7 P1）
# =========================================================================


class TestDefaultRulesCoverage:
    """验证 DEFAULT_DRC_RULES 含 25 条规则（覆盖率 100%）。"""

    def test_default_rules_count_25(self):
        """DEFAULT_DRC_RULES 应含 25 条规则（12+6+7）。"""
        from polaris_drc.rules import DEFAULT_DRC_RULES
        assert len(DEFAULT_DRC_RULES) == 25, (
            f"DEFAULT_DRC_RULES 含 {len(DEFAULT_DRC_RULES)} 条，应为 25 条")

    def test_p1_rules_present(self):
        """7 条 P1 规则均存在于 DEFAULT_DRC_RULES。"""
        from polaris_drc.rules import DEFAULT_DRC_RULES
        names = {r.name for r in DEFAULT_DRC_RULES}
        p1_names = {"SEPARATION", "ENCLOSURE", "EXTENSION", "EXCLUSION",
                    "ANGLE_LIMIT", "WAVEGUIDE_TAPER_ANGLE",
                    "SINGLEMODE_WIDTH"}
        assert p1_names.issubset(names), (
            f"缺失 P1 规则: {p1_names - names}")

    def test_dispatch_covers_all_25(self):
        """_dispatch 应覆盖所有 25 个 CheckType。"""
        from polaris_drc.rules import CheckType
        engine = DRCEngine(bend_compensate=False)
        all_types = {ct for ct in CheckType}
        dispatched = set(engine._dispatch.keys())
        assert all_types == dispatched, (
            f"未 dispatch 的 CheckType: {all_types - dispatched}，"
            f"多余 dispatch: {dispatched - all_types}")
