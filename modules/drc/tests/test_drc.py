"""polaris-drc 子模块基础 API 测试（覆盖模块导出/枚举/dataclass/引擎初始化/入口）。

从原 test_drc.py 拆分（R11 质量门禁：单文件 ≤800 行），按测试类分组:
- 本文件（test_drc.py）: 模块导出/CheckType/DRCRule/DEFAULT_DRC_RULES/
  DRCViolation/DRCEngine 初始化/run_drc 入口（基础 API，28 个测试）
- test_drc_rules.py: 几何/端口/密度规则 + 综合布局（规则行为，33 个测试）
- test_drc_engine.py: expert_demos 回归 + P0 波导级规则（18 个测试）

测试覆盖（78 个 pytest = 60 旧 + 18 新 P0 规则）。

学术依据（R02 学术诚信，≥5 个文献 URL）:
- SiEPIC EBeam PDK DRC runset（WG_MIN_WIDTH=0.4μm, WG_MIN_SPACE=1.0μm 等真实
  工艺规则源码）URL: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- SiEPIC-Tools Verification（Mismatched pin widths / Manhattan / Radius）
  URL: https://github-wiki-see.page/m/SiEPIC/SiEPIC-Tools/wiki/SiEPIC-Tools-Menu-descriptions
- Chrostowski & Hochberg, "Silicon Photonics Design", CUP 2015, p.353
  URL: https://www.cambridge.org/core/search?searchField=isbn&searchTerms=1107007731
- KLayout DRC 文档（width_check/space_check/area_check/notch 算子语义）
  URL: https://www.klayout.org/doc-qt5/manual/drc_runsets.html
- OpenDRC: He et al., DAC 2023, DOI:10.1109/DAC56929.2023.10247734
  URL: https://doi.org/10.1109/DAC56929.2023.10247734
- Berg et al. 2014, "Computational Geometry", Springer（AABB 相交/距离）
  URL: https://doi.org/10.1007/978-3-540-77974-2
- Ericson, "Real-Time Collision Detection", MK 2005（AABB 距离公式 §5.1.3）
  URL: https://realtimecollisiondetection.net/
- LiDAR 2.0: Zhou et al. arXiv:2505.17239v1, ISPD 2025（Bend/Crossing）
  URL: https://arxiv.org/html/2505.17239v1
- FluxCore DRC 文档（MIN_NOTCH=100nm, MIN_BEND_RADIUS=5-10μm）
  URL: https://www.fluxcoredynamics.com/docs/design-rules
- Cormen et al. "Introduction to Algorithms" MIT 2022（DFS 环检测 §22.3）
- pytest 文档: URL: https://docs.pytest.org/

合规: R02 学术诚信 / R03 禁止 fall-back（测试用真实几何数据）/ R04 不参与 GPU
      / R05 Bug 必修（无 TODO/FIXME）。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# 让测试既能从已安装包导入，也能从源码树导入（CI/开发模式）
_SRC = str(Path(__file__).resolve().parents[1] / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import polaris_drc  # noqa: E402
from polaris_drc import (  # noqa: E402
    DEFAULT_DRC_RULES,
    CheckType,
    DRCEngine,
    DRCRule,
    DRCViolation,
    run_drc,
    run_drc_rules,
)

# =============================================================================
# 测试辅助构造函数（真实几何数据，R03 禁止 fall-back）
# =============================================================================


def _make_simple_circuit() -> dict:
    """构造最简波导电路（与任务验证脚本一致）。"""
    return {
        "name": "test",
        "devices": [
            {
                "name": "wg",
                "device_type": "strip_waveguide",
                "ports": [
                    ("in", 0, 0, "west"),
                    ("out", 10, 0, "east"),
                ],
            },
        ],
        "connections": [],
        "canvas_w": 100,
        "canvas_h": 100,
    }


def _make_simple_placements() -> dict:
    """构造最简布局（单个波导）。"""
    return {"wg": {"x": 0.0, "y": 0.0, "w": 10.0, "h": 0.5}}


def _make_clean_circuit() -> dict:
    """构造 DRC clean 电路（2 器件 + 1 连接，所有规则通过）。

    d1.out (east) ↔ d2.in (west)，端口方向相对；
    端口 y 坐标对齐（共享 y 轴），dx=10μm 但 dy=0 ≤ 容差 10μm，PORT_ALIGNMENT 通过。
    """
    return {
        "name": "clean",
        "devices": [
            {"name": "d1", "device_type": "strip_waveguide",
             "ports": [("in", 0, 0, "west"), ("out", 10, 0, "east")]},
            {"name": "d2", "device_type": "strip_waveguide",
             "ports": [("in", 0, 0, "west"), ("out", 10, 0, "east")]},
        ],
        "connections": [("d1", "out", "d2", "in")],
        "canvas_w": 100,
        "canvas_h": 100,
    }


def _make_clean_placements() -> dict:
    """构造 DRC clean 布局（间距 10μm ≥ 1.0μm，无重叠，密度 0.1%）。"""
    return {
        "d1": {"x": 10.0, "y": 10.0, "w": 10.0, "h": 0.5},
        "d2": {"x": 30.0, "y": 10.0, "w": 10.0, "h": 0.5},
    }


def _violation_rule_names(result: dict) -> set[str]:
    """从 run_drc 结果提取触发的规则名集合。"""
    return {v["rule_name"] for v in result["violations"]}


# =============================================================================
# 1. 模块导出与版本（3 个测试）
# =============================================================================


def test_drc_version():
    """验证 polaris-drc 子模块版本号 5.0.0（与原 polaris-verify 一致）。"""
    assert polaris_drc.__version__ == "5.0.0"


def test_drc_module_imports():
    """验证 polaris_drc 模块导出全部公共 API（__all__ 完整性）。"""
    expected = {
        "run_drc", "DRCEngine", "DRCRule", "DRCViolation",
        "CheckType", "DEFAULT_DRC_RULES", "run_drc_rules", "__version__",
        "DRCRuleset", "DRC_RULESETS",
        "get_drc_ruleset", "register_drc_ruleset",
        "list_available_pdk_rulesets",
    }
    assert expected.issubset(set(dir(polaris_drc))), (
        f"polaris_drc 缺少导出: {expected - set(dir(polaris_drc))}"
    )
    assert expected.issubset(set(polaris_drc.__all__) | {"__version__"})
    # 关键类/函数可调用
    assert callable(run_drc)
    assert callable(run_drc_rules)


def test_drc_n_rules_25():
    """验证默认 DRC 规则数为 25（12 SiEPIC 基础 + 6 P0 波导级 + 7 P1 跨层/波导）。

    25 条规则: MIN_SPACING/MIN_WIDTH/MIN_HEIGHT/MIN_AREA/BOUNDARY/NO_OVERLAP/
    PORT_ALIGNMENT/PORT_DIRECTION/PORT_CONNECTIVITY/PORT_FACING/DENSITY_MAX/
    DENSITY_MIN/BEND_RADIUS_MIN/WAVEGUIDE_WIDTH_MATCH/MIN_NOTCH/
    WAVEGUIDE_MANHATTAN/ENCLOSED_AREA_MIN/CROSSING_ANGULAR/
    SEPARATION/ENCLOSURE/EXTENSION/EXCLUSION/
    ANGLE_LIMIT/WAVEGUIDE_TAPER_ANGLE/SINGLEMODE_WIDTH。
    """
    circuit = _make_simple_circuit()
    placements = _make_simple_placements()
    result = run_drc(circuit, placements)
    assert result["n_rules"] == 25, (
        f"n_rules 应为 25（12 基础 + 6 P0 + 7 P1），实际 {result['n_rules']}"
    )


# =============================================================================
# 2. CheckType 枚举完整性（2 个测试）
# =============================================================================


def test_check_type_enum_values():
    """验证 CheckType 枚举 25 个值与 KLayout DRC 规则类别对应。

    来源: KLayout DRC 规则类别
    https://www.klayout.org/doc-qt5/manual/drc_runsets.html
    SiEPIC-Tools Verification https://github-wiki-see.page/m/SiEPIC/SiEPIC-Tools/wiki/SiEPIC-Tools-Menu-descriptions
    LiDAR 2.0 II-B3 https://arxiv.org/html/2505.17239v1
    gdsfactory DRC http://raw.githubusercontent.com/gdsfactory/gdsfactory-photonics-training/main/notebooks/11_drc.ipynb
    Snyder & Love 1983 §13.5 https://link.springer.com/book/10.1007/978-94-009-6875-2
    """
    assert CheckType.MIN_SPACING.value == "min_spacing"
    assert CheckType.MIN_WIDTH.value == "min_width"
    assert CheckType.MIN_HEIGHT.value == "min_height"
    assert CheckType.MIN_AREA.value == "min_area"
    assert CheckType.BOUNDARY.value == "boundary"
    assert CheckType.NO_OVERLAP.value == "no_overlap"
    assert CheckType.PORT_ALIGNMENT.value == "port_alignment"
    assert CheckType.PORT_DIRECTION.value == "port_direction"
    assert CheckType.PORT_CONNECTIVITY.value == "port_connectivity"
    assert CheckType.PORT_FACING.value == "port_facing"
    assert CheckType.DENSITY_MAX.value == "density_max"
    assert CheckType.DENSITY_MIN.value == "density_min"
    # P0 波导级（6 条）
    assert CheckType.BEND_RADIUS_MIN.value == "bend_radius_min"
    assert CheckType.WAVEGUIDE_WIDTH_MATCH.value == "waveguide_width_match"
    assert CheckType.MIN_NOTCH.value == "min_notch"
    assert CheckType.WAVEGUIDE_MANHATTAN.value == "waveguide_manhattan"
    assert CheckType.ENCLOSED_AREA_MIN.value == "enclosed_area_min"
    assert CheckType.CROSSING_ANGULAR.value == "crossing_angular"
    # P1 跨层（4 条，R383）
    assert CheckType.SEPARATION.value == "separation"
    assert CheckType.ENCLOSURE.value == "enclosure"
    assert CheckType.EXTENSION.value == "extension"
    assert CheckType.EXCLUSION.value == "exclusion"
    # P1 波导级（3 条，R383）
    assert CheckType.ANGLE_LIMIT.value == "angle_limit"
    assert CheckType.WAVEGUIDE_TAPER_ANGLE.value == "waveguide_taper_angle"
    assert CheckType.SINGLEMODE_WIDTH.value == "singlemode_width"


def test_check_type_enum_count():
    """验证 CheckType 枚举数量为 25（与 DEFAULT_DRC_RULES 一一对应）。"""
    members = list(CheckType)
    assert len(members) == 25, f"CheckType 应有 25 个成员，实际 {len(members)}"
    # 枚举值唯一
    values = [m.value for m in members]
    assert len(set(values)) == 25, "CheckType 枚举值应唯一"


# =============================================================================
# 3. DRCRule dataclass（3 个测试）
# =============================================================================


def test_drc_rule_dataclass_fields():
    """验证 DRCRule dataclass 字段（name/check_type/threshold/severity/description）。"""
    rule = DRCRule(
        name="TEST_RULE",
        check_type=CheckType.MIN_WIDTH,
        threshold=0.5,
        severity=0.8,
        description="测试规则",
    )
    assert rule.name == "TEST_RULE"
    assert rule.check_type == CheckType.MIN_WIDTH
    assert rule.threshold == 0.5
    assert rule.severity == 0.8
    assert rule.description == "测试规则"


def test_drc_rule_frozen():
    """验证 DRCRule 是 frozen dataclass（不可变，R05 防止意外修改规则）。

    frozen dataclass 修改字段应 raise FrozenInstanceError（AttributeError 子类）。
    """
    rule = DRCRule(
        name="FROZEN_TEST",
        check_type=CheckType.MIN_SPACING,
        threshold=1.0,
    )
    with pytest.raises(AttributeError):
        rule.threshold = 999.0  # type: ignore[misc]
    with pytest.raises(AttributeError):
        rule.name = "MUTATED"  # type: ignore[misc]


def test_drc_rule_default_severity():
    """验证 DRCRule 默认 severity=1.0，description 为空字符串。"""
    rule = DRCRule(
        name="DEFAULT_TEST",
        check_type=CheckType.MIN_AREA,
        threshold=0.1,
    )
    assert rule.severity == 1.0
    assert rule.description == ""


# =============================================================================
# 4. DEFAULT_DRC_RULES 内容校验（5 个测试）
# =============================================================================


def test_default_rules_count():
    """验证 DEFAULT_DRC_RULES 包含 25 条规则（12 基础 + 6 P0 + 7 P1）。"""
    assert len(DEFAULT_DRC_RULES) == 25, (
        f"DEFAULT_DRC_RULES 应有 25 条，实际 {len(DEFAULT_DRC_RULES)}"
    )


def test_default_rules_thresholds():
    """验证 DEFAULT_DRC_RULES 各规则阈值与 SiEPIC EBeam PDK runset 一致。

    阈值来源: SiEPIC EBeam PDK DRC runset 源码
    https://github.com/SiEPIC/SiEPIC_EBeam_PDK
    P0 波导级阈值: SiEPIC-Tools Verification / LiDAR 2.0 / FluxCore
    """
    rules_by_name = {r.name: r for r in DEFAULT_DRC_RULES}
    assert rules_by_name["MIN_SPACING"].threshold == 1.0   # WG_MIN_SPACE
    assert rules_by_name["MIN_WIDTH"].threshold == 0.5     # SLAB150_MIN_WIDTH
    assert rules_by_name["MIN_HEIGHT"].threshold == 0.4    # WG_MIN_WIDTH
    assert rules_by_name["MIN_AREA"].threshold == 0.1      # WG_MIN_AREA
    assert rules_by_name["BOUNDARY"].threshold == 0.0
    assert rules_by_name["NO_OVERLAP"].threshold == 0.0
    assert rules_by_name["PORT_ALIGNMENT"].threshold == 10.0  # SiEPIC 弯曲容差 10-20μm（engine _PORT_ALIGN_TOL_UM）
    assert rules_by_name["PORT_DIRECTION"].threshold == 0.0
    assert rules_by_name["PORT_CONNECTIVITY"].threshold == 0.0
    assert rules_by_name["PORT_FACING"].threshold == 0.0
    assert rules_by_name["DENSITY_MAX"].threshold == 80.0
    assert rules_by_name["DENSITY_MIN"].threshold == 0.01
    # P0 波导级（6 条）
    assert rules_by_name["BEND_RADIUS_MIN"].threshold == 5.0      # SiEPIC/IMEC 5μm
    assert rules_by_name["WAVEGUIDE_WIDTH_MATCH"].threshold == 0.0  # 完全匹配
    assert rules_by_name["MIN_NOTCH"].threshold == 0.1            # KLayout/FluxCore 100nm
    assert rules_by_name["WAVEGUIDE_MANHATTAN"].threshold == 0.0
    assert rules_by_name["ENCLOSED_AREA_MIN"].threshold == 0.01   # 0.01μm²
    assert rules_by_name["CROSSING_ANGULAR"].threshold == 90.0    # LiDAR 2.0 II-B3


def test_default_rules_unique_names():
    """验证 DEFAULT_DRC_RULES 规则名唯一（无重复）。"""
    names = [r.name for r in DEFAULT_DRC_RULES]
    assert len(set(names)) == 25, f"规则名有重复或数量不符: {names}"


def test_default_rules_severity_range():
    """验证 DEFAULT_DRC_RULES 所有 severity ∈ (0, 1]（合法物理范围）。"""
    for rule in DEFAULT_DRC_RULES:
        assert 0.0 < rule.severity <= 1.0, (
            f"规则 {rule.name} severity={rule.severity} 超出 (0, 1] 范围"
        )


def test_default_rules_descriptions_nonempty():
    """验证 DEFAULT_DRC_RULES 所有规则描述非空（R02 学术诚信，可溯源）。"""
    for rule in DEFAULT_DRC_RULES:
        assert rule.description, f"规则 {rule.name} 描述为空"
        assert isinstance(rule.check_type, CheckType)


# =============================================================================
# 5. DRCViolation dataclass（1 个测试）
# =============================================================================


def test_drc_violation_construction():
    """验证 DRCViolation dataclass 构造与字段（与 KLayout Violation 格式对齐）。"""
    v = DRCViolation(
        rule_name="MIN_WIDTH",
        severity=1.0,
        message="器件 wg 宽度 0.3μm < 阈值 0.5μm",
        device_name="wg",
        location=(5.0, 0.25),
    )
    assert v.rule_name == "MIN_WIDTH"
    assert v.severity == 1.0
    assert "宽度" in v.message
    assert v.device_name == "wg"
    assert v.location == (5.0, 0.25)
    # location 是 tuple（可迭代，长度 2）
    assert len(v.location) == 2


# =============================================================================
# 6. DRCEngine 初始化（3 个测试）
# =============================================================================


def test_engine_init_default_rules():
    """验证 DRCEngine 默认使用 DEFAULT_DRC_RULES。"""
    engine = DRCEngine()
    assert engine.rules is DEFAULT_DRC_RULES
    assert len(engine.rules) == 25


def test_engine_init_custom_rules():
    """验证 DRCEngine 接受自定义规则列表。"""
    custom = [
        DRCRule(name="C1", check_type=CheckType.MIN_WIDTH, threshold=0.5),
        DRCRule(name="C2", check_type=CheckType.MIN_SPACING, threshold=1.0),
    ]
    engine = DRCEngine(custom)
    assert engine.rules is custom
    assert len(engine.rules) == 2


def test_engine_init_empty_rules_raises():
    """验证空规则列表 raise RuntimeError（R03 禁止 fall-back）。"""
    with pytest.raises(RuntimeError, match="不能为空"):
        DRCEngine([])


# =============================================================================
# 7. run_drc / run_drc_rules 入口与校验（5 个测试）
# =============================================================================


def test_run_drc_returns_dict_structure():
    """验证 run_drc 返回 dict 含全部必要字段（n_rules/n_violations/n_passed/
    pass_rate/violations）。"""
    result = run_drc(_make_simple_circuit(), _make_simple_placements())
    for key in ("n_rules", "n_violations", "n_passed", "pass_rate", "violations"):
        assert key in result, f"DRC 结果缺少字段: {key}"
    assert isinstance(result["violations"], list)
    # violation 结构完整
    for v in result["violations"]:
        for field in ("rule_name", "severity", "message", "device_name", "location"):
            assert field in v, f"violation 缺少字段: {field}"
        assert isinstance(v["location"], list) and len(v["location"]) == 2


def test_run_drc_rules_returns_list():
    """验证 run_drc_rules 返回 list[DRCViolation]（便捷入口）。"""
    violations = run_drc_rules(_make_simple_circuit(), _make_simple_placements())
    assert isinstance(violations, list)
    for v in violations:
        assert isinstance(v, DRCViolation)


def test_run_drc_invalid_circuit_raises():
    """非法 circuit（缺字段）应 raise RuntimeError（R03 禁止 fall-back）。"""
    placements = {"wg": {"x": 0.0, "y": 0.0, "w": 10.0, "h": 0.5}}
    with pytest.raises(RuntimeError, match="circuit"):
        run_drc({}, placements)  # 缺 name/devices/canvas_w/canvas_h


def test_run_drc_invalid_placements_raises():
    """非法 placements（器件缺字段）应 raise RuntimeError。"""
    circuit = _make_simple_circuit()
    with pytest.raises(RuntimeError, match="placements"):
        run_drc(circuit, {"wg": {"x": 0.0}})  # 缺 y/w/h


def test_run_drc_empty_placements_raises():
    """空 placements 应 raise RuntimeError（R03 禁止 fall-back）。"""
    circuit = _make_simple_circuit()
    with pytest.raises(RuntimeError, match="placements"):
        run_drc(circuit, {})


# =============================================================================
# 11. 综合布局与边界情况（基础部分）
# =============================================================================


def test_drc_simple_waveguide():
    """简单波导布局验证（与任务验证脚本一致）。

    单个 strip_waveguide 10μm × 0.5μm，画布 100×100μm。
    验证: 返回 dict 含全部必要字段，n_rules=25，pass_rate > 0。
    """
    circuit = _make_simple_circuit()
    placements = _make_simple_placements()
    result = run_drc(circuit, placements)
    assert result["n_rules"] == 25
    assert result["pass_rate"] > 0.0, (
        f"合法布局至少部分规则会通过，pass_rate={result['pass_rate']}"
    )


def test_drc_pass_rate_range():
    """验证 pass_rate ∈ [0, 1]（合法物理范围）。

    pass_rate = n_passed / n_rules，n_rules=12，n_passed ∈ [0, 12]，
    所以 pass_rate ∈ [0, 1]。
    """
    result = run_drc(_make_simple_circuit(), _make_simple_placements())
    assert 0.0 <= result["pass_rate"] <= 1.0, (
        f"pass_rate 应 ∈ [0, 1]，实际 {result['pass_rate']}"
    )
    # n_passed + 违规规则数 = n_rules
    violated_rules = {v["rule_name"] for v in result["violations"]}
    assert result["n_passed"] + len(violated_rules) == result["n_rules"]


def test_drc_duplicate_device_name_raises():
    """器件名重复应 raise RuntimeError（_build_device_map 检测，R03）。

    PORT_ALIGNMENT 检查调用 _build_device_map，发现器件名重复即 raise。
    """
    circuit = {
        "name": "dup",
        "devices": [
            {"name": "d1", "device_type": "wg",
             "ports": [("in", 0, 0, "west"), ("out", 10, 0, "east")]},
            {"name": "d1", "device_type": "wg",
             "ports": [("in", 0, 0, "west"), ("out", 10, 0, "east")]},
        ],
        "connections": [("d1", "out", "d1", "in")],
        "canvas_w": 100, "canvas_h": 100,
    }
    placements = {"d1": {"x": 10.0, "y": 10.0, "w": 10.0, "h": 0.5}}
    with pytest.raises(RuntimeError, match="重复"):
        run_drc(circuit, placements)
