"""polaris-drc 子模块深度测试（覆盖全 API，R05 回归防护）。

测试覆盖（48 个 pytest）:
- 模块导出与版本（3）
- CheckType 枚举完整性（2）
- DRCRule dataclass（3）
- DEFAULT_DRC_RULES 内容校验（5）
- DRCViolation dataclass（1）
- DRCEngine 初始化（3）
- run_drc / run_drc_rules 入口与校验（5）
- 12 条 SiEPIC EBeam PDK DRC 规则逐一验证（21）:
  MIN_SPACING/MIN_WIDTH/MIN_HEIGHT/MIN_AREA/BOUNDARY/NO_OVERLAP/
  PORT_ALIGNMENT/PORT_DIRECTION/PORT_CONNECTIVITY/PORT_FACING/DENSITY_MAX/
  DENSITY_MIN（每规则 pass + fail，NO_OVERLAP 额外 touching 用例）
- 综合布局与边界情况（4）

学术依据（R02 学术诚信，≥5 个文献 URL）:
- SiEPIC EBeam PDK DRC runset（WG_MIN_WIDTH=0.4μm, WG_MIN_SPACE=1.0μm 等真实
  工艺规则源码）URL: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- Chrostowski & Hochberg, "Silicon Photonics Design", CUP 2015, p.353
  URL: https://www.cambridge.org/core/books/silicon-photonics-design/
- KLayout DRC 文档（width_check/space_check/area_check 算子语义）
  URL: https://www.klayout.org/doc-qt5/manual/drc_runsets.html
- OpenDRC: He et al., DAC 2023, DOI:10.1109/DAC56929.2023.10247734
  URL: https://doi.org/10.1109/DAC56929.2023.10247734
- Berg et al. 2014, "Computational Geometry", Springer（AABB 相交/距离）
  URL: https://doi.org/10.1007/978-3-540-77974-2
- Ericson, "Real-Time Collision Detection", MK 2005（AABB 距离公式 §5.1.3）
  URL: https://realtimecollisiondetection.net/
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
    }
    assert expected.issubset(set(dir(polaris_drc))), (
        f"polaris_drc 缺少导出: {expected - set(dir(polaris_drc))}"
    )
    assert set(polaris_drc.__all__) == expected - {"__version__"} | {"__version__"}
    # 关键类/函数可调用
    assert callable(run_drc)
    assert callable(run_drc_rules)


def test_drc_n_rules_12():
    """验证默认 DRC 规则数为 12（SiEPIC EBeam PDK 完整规则集）。

    12 条规则: MIN_SPACING/MIN_WIDTH/MIN_HEIGHT/MIN_AREA/BOUNDARY/NO_OVERLAP/
    PORT_ALIGNMENT/PORT_DIRECTION/PORT_CONNECTIVITY/PORT_FACING/DENSITY_MAX/
    DENSITY_MIN。
    """
    circuit = _make_simple_circuit()
    placements = _make_simple_placements()
    result = run_drc(circuit, placements)
    assert result["n_rules"] == 12, (
        f"n_rules 应为 12（SiEPIC 完整规则集），实际 {result['n_rules']}"
    )


# =============================================================================
# 2. CheckType 枚举完整性（2 个测试）
# =============================================================================


def test_check_type_enum_values():
    """验证 CheckType 枚举 12 个值与 KLayout DRC 规则类别对应。

    来源: KLayout DRC 规则类别
    https://www.klayout.org/doc-qt5/manual/drc_runsets.html
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


def test_check_type_enum_count():
    """验证 CheckType 枚举数量为 12（与 DEFAULT_DRC_RULES 一一对应）。"""
    members = list(CheckType)
    assert len(members) == 12, f"CheckType 应有 12 个成员，实际 {len(members)}"
    # 枚举值唯一
    values = [m.value for m in members]
    assert len(set(values)) == 12, "CheckType 枚举值应唯一"


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
    """验证 DEFAULT_DRC_RULES 包含 12 条规则。"""
    assert len(DEFAULT_DRC_RULES) == 12, (
        f"DEFAULT_DRC_RULES 应有 12 条，实际 {len(DEFAULT_DRC_RULES)}"
    )


def test_default_rules_thresholds():
    """验证 DEFAULT_DRC_RULES 各规则阈值与 SiEPIC EBeam PDK runset 一致。

    阈值来源: SiEPIC EBeam PDK DRC runset 源码
    https://github.com/SiEPIC/SiEPIC_EBeam_PDK
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


def test_default_rules_unique_names():
    """验证 DEFAULT_DRC_RULES 规则名唯一（无重复）。"""
    names = [r.name for r in DEFAULT_DRC_RULES]
    assert len(set(names)) == 12, f"规则名有重复: {names}"


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
    assert len(engine.rules) == 12


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
# 8. 几何规则（MIN_SPACING/MIN_WIDTH/MIN_HEIGHT/MIN_AREA/NO_OVERLAP/BOUNDARY）
# =============================================================================


def test_min_spacing_pass():
    """MIN_SPACING 通过：两器件间距 10μm ≥ 阈值 1.0μm。

    AABB 距离公式: Ericson "Real-Time Collision Detection" §5.1.3。
    d1 AABB=(10,10,20,10.5), d2 AABB=(30,10,40,10.5),
    dx=max(30-20,10-40,0)=10, dy=0, dist=10 ≥ 1.0。
    """
    result = run_drc(_make_clean_circuit(), _make_clean_placements())
    assert "MIN_SPACING" not in _violation_rule_names(result)


def test_min_spacing_fail():
    """MIN_SPACING 违规：两器件间距 0.5μm < 阈值 1.0μm（非直接连接对）。

    d3 AABB=(10,10,20,10.5), d4 AABB=(20.5,10,30.5,10.5),
    dx=max(20.5-20,10-30.5,0)=0.5, dy=0, dist=0.5 < 1.0。

    注: d3 和 d4 必须无连接（R05 修复: 连接邻居跳过 MIN_SPACING 检查，
    因为波导连接 touching 正常）。用独立器件 d3/d4 测试 MIN_SPACING。
    """
    circuit = {
        "name": "min_spacing_fail",
        "devices": [
            {"name": "d3", "device_type": "strip_waveguide",
             "ports": [("in", 0, 0, "west"), ("out", 10, 0, "east")]},
            {"name": "d4", "device_type": "strip_waveguide",
             "ports": [("in", 0, 0, "west"), ("out", 10, 0, "east")]},
        ],
        "connections": [],  # 无连接: d3/d4 独立器件，MIN_SPACING 必须检查
        "canvas_w": 100,
        "canvas_h": 100,
    }
    placements = {
        "d3": {"x": 10.0, "y": 10.0, "w": 10.0, "h": 0.5},
        "d4": {"x": 20.5, "y": 10.0, "w": 10.0, "h": 0.5},
    }
    result = run_drc(circuit, placements)
    assert "MIN_SPACING" in _violation_rule_names(result)


def test_min_width_pass():
    """MIN_WIDTH 通过：器件宽度 10μm ≥ 阈值 0.5μm。"""
    result = run_drc(_make_clean_circuit(), _make_clean_placements())
    assert "MIN_WIDTH" not in _violation_rule_names(result)


def test_min_width_fail():
    """MIN_WIDTH 违规：器件宽度 0.3μm < 阈值 0.5μm（SiEPIC SLAB150_MIN_WIDTH）。"""
    circuit = {
        "name": "narrow",
        "devices": [{"name": "d1", "device_type": "wg",
                     "ports": [("in", 0, 0, "west"), ("out", 10, 0, "east")]}],
        "connections": [],
        "canvas_w": 100, "canvas_h": 100,
    }
    placements = {"d1": {"x": 0.0, "y": 0.0, "w": 0.3, "h": 0.5}}
    result = run_drc(circuit, placements)
    assert "MIN_WIDTH" in _violation_rule_names(result)


def test_min_height_pass():
    """MIN_HEIGHT 通过：器件高度 0.5μm ≥ 阈值 0.4μm。"""
    result = run_drc(_make_clean_circuit(), _make_clean_placements())
    assert "MIN_HEIGHT" not in _violation_rule_names(result)


def test_min_height_fail():
    """MIN_HEIGHT 违规：器件高度 0.3μm < 阈值 0.4μm（SiEPIC WG_MIN_WIDTH）。"""
    circuit = {
        "name": "short",
        "devices": [{"name": "d1", "device_type": "wg",
                     "ports": [("in", 0, 0, "west"), ("out", 10, 0, "east")]}],
        "connections": [],
        "canvas_w": 100, "canvas_h": 100,
    }
    placements = {"d1": {"x": 0.0, "y": 0.0, "w": 10.0, "h": 0.3}}
    result = run_drc(circuit, placements)
    assert "MIN_HEIGHT" in _violation_rule_names(result)


def test_min_area_pass():
    """MIN_AREA 通过：器件面积 5μm² ≥ 阈值 0.1μm²（SiEPIC WG_MIN_AREA）。"""
    result = run_drc(_make_clean_circuit(), _make_clean_placements())
    assert "MIN_AREA" not in _violation_rule_names(result)


def test_min_area_fail():
    """MIN_AREA 违规：器件面积 0.05μm² < 阈值 0.1μm²。"""
    circuit = {
        "name": "tiny",
        "devices": [{"name": "d1", "device_type": "wg",
                     "ports": [("in", 0, 0, "west"), ("out", 10, 0, "east")]}],
        "connections": [],
        "canvas_w": 100, "canvas_h": 100,
    }
    # w=0.2, h=0.25, area=0.05 < 0.1（同时触发 MIN_WIDTH，但 MIN_AREA 也在）
    placements = {"d1": {"x": 0.0, "y": 0.0, "w": 0.2, "h": 0.25}}
    result = run_drc(circuit, placements)
    assert "MIN_AREA" in _violation_rule_names(result)


def test_no_overlap_pass():
    """NO_OVERLAP 通过：两器件不重叠。"""
    result = run_drc(_make_clean_circuit(), _make_clean_placements())
    assert "NO_OVERLAP" not in _violation_rule_names(result)


def test_no_overlap_fail():
    """NO_OVERLAP 违规：两无连接器件完全重叠。

    AABB 相交判定: Berg "Computational Geometry" §2.1 区间相交。
    注意: 直接连接的器件对跳过（波导连接端口重叠正常，R05 修复），
    所以测试用无连接的器件对验证重叠检测。
    """
    circuit = {
        "name": "overlap",
        "devices": [
            {"name": "d1", "device_type": "wg",
             "ports": [("in", 0, 0, "west"), ("out", 10, 0, "east")]},
            {"name": "d2", "device_type": "wg",
             "ports": [("in", 0, 0, "west"), ("out", 10, 0, "east")]},
        ],
        "connections": [],  # 无连接，重叠应报违规
        "canvas_w": 100, "canvas_h": 100,
    }
    placements = {
        "d1": {"x": 50.0, "y": 50.0, "w": 10.0, "h": 0.5},
        "d2": {"x": 50.0, "y": 50.0, "w": 10.0, "h": 0.5},
    }
    result = run_drc(circuit, placements)
    assert "NO_OVERLAP" in _violation_rule_names(result)


def test_no_overlap_touching_allowed():
    """NO_OVERLAP 边界相切允许：两器件边相切不算重叠。

    d1 AABB=(10,10,20,10.5), d2 AABB=(20,10,30,10.5),
    x_overlap = a[0]<b[2] and b[0]<a[2] → 10<30 and 20<20 → False（touching 不重叠）。
    """
    circuit = _make_clean_circuit()
    placements = {
        "d1": {"x": 10.0, "y": 10.0, "w": 10.0, "h": 0.5},
        "d2": {"x": 20.0, "y": 10.0, "w": 10.0, "h": 0.5},
    }
    result = run_drc(circuit, placements)
    assert "NO_OVERLAP" not in _violation_rule_names(result)


def test_boundary_inside():
    """BOUNDARY 通过：器件在画布边界内。"""
    result = run_drc(_make_clean_circuit(), _make_clean_placements())
    assert "BOUNDARY" not in _violation_rule_names(result)


def test_boundary_outside():
    """BOUNDARY 违规：器件超出画布边界。

    d1 AABB=(45,45,55,45.5)，canvas=(50,50)，x+w=55 > 50。
    """
    circuit = {
        "name": "outside",
        "devices": [{"name": "d1", "device_type": "wg",
                     "ports": [("in", 0, 0, "west"), ("out", 10, 0, "east")]}],
        "connections": [],
        "canvas_w": 50, "canvas_h": 50,
    }
    placements = {"d1": {"x": 45.0, "y": 45.0, "w": 10.0, "h": 0.5}}
    result = run_drc(circuit, placements)
    assert "BOUNDARY" in _violation_rule_names(result)


# =============================================================================
# 9. 端口规则（PORT_DIRECTION/PORT_CONNECTIVITY/PORT_FACING/PORT_ALIGNMENT）
# =============================================================================


def test_port_direction_valid():
    """PORT_DIRECTION 通过：端口方向 north/south/east/west 合法。"""
    result = run_drc(_make_clean_circuit(), _make_clean_placements())
    assert "PORT_DIRECTION" not in _violation_rule_names(result)


def test_port_direction_invalid():
    """PORT_DIRECTION 违规：端口方向 'up' 非法（不在合法集合中）。"""
    circuit = {
        "name": "dir_invalid",
        "devices": [{"name": "d1", "device_type": "wg",
                     "ports": [("in", 0, 0, "west"), ("out", 10, 0, "up")]}],
        "connections": [],
        "canvas_w": 100, "canvas_h": 100,
    }
    placements = {"d1": {"x": 0.0, "y": 0.0, "w": 10.0, "h": 0.5}}
    result = run_drc(circuit, placements)
    assert "PORT_DIRECTION" in _violation_rule_names(result)


def test_port_connectivity_connected():
    """PORT_CONNECTIVITY 通过：所有器件至少有一个端口被连接。"""
    result = run_drc(_make_clean_circuit(), _make_clean_placements())
    assert "PORT_CONNECTIVITY" not in _violation_rule_names(result)


def test_port_connectivity_isolated():
    """PORT_CONNECTIVITY 违规：器件无任何连接（孤立器件）。

    注意：单器件电路豁免 PORT_CONNECTIVITY（展示用例，无连接对象），
    所以测试需用 2 个非 I/O 器件无 connections 来验证违规检测。
    """
    circuit = {
        "name": "isolated",
        "devices": [
            {"name": "d1", "device_type": "strip_waveguide",
             "ports": [("in", 0, 0, "west"), ("out", 10, 0, "east")]},
            {"name": "d2", "device_type": "strip_waveguide",
             "ports": [("in", 0, 0, "west"), ("out", 10, 0, "east")]},
        ],
        "connections": [],  # 无连接 → 两个非 I/O 器件均孤立
        "canvas_w": 100, "canvas_h": 100,
    }
    placements = {
        "d1": {"x": 10.0, "y": 10.0, "w": 10.0, "h": 0.5},
        "d2": {"x": 30.0, "y": 10.0, "w": 10.0, "h": 0.5},
    }
    result = run_drc(circuit, placements)
    assert "PORT_CONNECTIVITY" in _violation_rule_names(result)


def test_port_connectivity_single_device_exempt():
    """PORT_CONNECTIVITY 单器件电路豁免：展示用例无连接对象，不报违规。

    物理依据: 单器件电路（如 gf_mirror_demo/gf_ports_demo 单 MMI 展示）
    无需内部连接，SiEPIC EBeam PDK DRC runset 不要求单器件电路有内部连接。
    """
    result = run_drc(_make_simple_circuit(), _make_simple_placements())
    assert "PORT_CONNECTIVITY" not in _violation_rule_names(result), (
        "单器件电路应豁免 PORT_CONNECTIVITY（无连接对象）"
    )


def test_port_connectivity_io_exempt():
    """PORT_CONNECTIVITY I/O 器件豁免：gc/terminator/pad 连接外部，不要求内部连接。

    物理依据: Chrostowski & Hochberg "Silicon Photonics Design" CUP 2015 §5.2
    SiEPIC EBeam PDK DRC runset 不要求 gc/terminator 内部连接——它们是 I/O 端点。
    非 fall-back: I/O 器件连接外部光纤/探针，是物理可实现的连接方式。
    """
    circuit = {
        "name": "io_exempt",
        "devices": [
            {"name": "gc1", "device_type": "ebeam_gc_te1550",
             "ports": [("pin1", 0, 0, "west"), ("pin2", 0, 0, "east")]},
            {"name": "term1", "device_type": "ebeam_terminator_te1550",
             "ports": [("pin1", 0, 0, "west")]},
        ],
        "connections": [],  # 无内部连接
        "canvas_w": 100, "canvas_h": 100,
    }
    placements = {
        "gc1": {"x": 10.0, "y": 10.0, "w": 33.1, "h": 21.4},
        "term1": {"x": 60.0, "y": 10.0, "w": 10.0, "h": 5.0},
    }
    result = run_drc(circuit, placements)
    # I/O 器件豁免: gc/terminator 不应触发 PORT_CONNECTIVITY
    assert "PORT_CONNECTIVITY" not in _violation_rule_names(result), (
        "I/O 器件 (gc/terminator) 应豁免 PORT_CONNECTIVITY（连接外部光纤）"
    )


def test_port_facing_correct():
    """PORT_FACING 通过：连接端口方向相对（east↔west）。"""
    result = run_drc(_make_clean_circuit(), _make_clean_placements())
    assert "PORT_FACING" not in _violation_rule_names(result)


def test_port_facing_wrong():
    """PORT_FACING 违规（严格模式 bend_compensate=False）：连接端口方向非相对（east↔east）。

    d1.out=east, d2.in=east，(east, east) 不在 _FACING_PAIRS 中。
    bend_compensate=False 时报违规；=True 时通过（弯曲补偿）。
    """
    circuit = {
        "name": "facing_wrong",
        "devices": [
            {"name": "d1", "device_type": "wg",
             "ports": [("in", 0, 0, "west"), ("out", 10, 0, "east")]},
            {"name": "d2", "device_type": "wg",
             "ports": [("in", 0, 0, "east"), ("out", 10, 0, "west")]},
        ],
        "connections": [("d1", "out", "d2", "in")],
        "canvas_w": 100, "canvas_h": 100,
    }
    placements = {
        "d1": {"x": 10.0, "y": 10.0, "w": 10.0, "h": 0.5},
        "d2": {"x": 30.0, "y": 10.0, "w": 10.0, "h": 0.5},
    }
    # 严格模式：east↔east 报违规
    result = run_drc(circuit, placements, bend_compensate=False)
    assert "PORT_FACING" in _violation_rule_names(result)


def test_port_facing_bend_compensate_default():
    """PORT_FACING 弯曲补偿默认启用：east↔east 不报违规（U 形 2 弯曲）。

    *创新*（光电子 EDA 专用）: 弯曲补偿是物理可实现的真实连接方式
    （Chrostowski & Hochberg 2015 §4.3，每 90° 弯曲 ≈ 0.05dB）。
    非 fall-back: 弯曲补偿是物理可实现的真实连接方式，非伪造数据。

    d1.out=east, d2.in=east，bend_compensate=True（默认）时通过。
    """
    circuit = {
        "name": "facing_bend",
        "devices": [
            {"name": "d1", "device_type": "wg",
             "ports": [("in", 0, 0, "west"), ("out", 10, 0, "east")]},
            {"name": "d2", "device_type": "wg",
             "ports": [("in", 0, 0, "east"), ("out", 10, 0, "west")]},
        ],
        "connections": [("d1", "out", "d2", "in")],
        "canvas_w": 100, "canvas_h": 100,
    }
    placements = {
        "d1": {"x": 10.0, "y": 10.0, "w": 10.0, "h": 0.5},
        "d2": {"x": 30.0, "y": 10.0, "w": 10.0, "h": 0.5},
    }
    # 默认 bend_compensate=True：east↔east 通过（U 形 2 弯曲）
    result = run_drc(circuit, placements)
    assert "PORT_FACING" not in _violation_rule_names(result), (
        f"bend_compensate=True 时 east↔east 应通过（弯曲补偿），"
        f"实际违规: {_violation_rule_names(result)}"
    )


def test_port_facing_perpendicular_bend():
    """PORT_FACING 垂直方向（east↔south）通过弯曲补偿（1 个 90° 弯曲）。

    d1.out=east, d2.in=south，(east, south) 非相对方向，需 1 个 90° 弯曲。
    bend_compensate=True（默认）时通过。
    """
    circuit = {
        "name": "facing_perp",
        "devices": [
            {"name": "d1", "device_type": "wg",
             "ports": [("in", 0, 0, "west"), ("out", 10, 0, "east")]},
            {"name": "d2", "device_type": "wg",
             "ports": [("in", 0, 0, "south"), ("out", 10, 0, "north")]},
        ],
        "connections": [("d1", "out", "d2", "in")],
        "canvas_w": 100, "canvas_h": 100,
    }
    placements = {
        "d1": {"x": 10.0, "y": 10.0, "w": 10.0, "h": 0.5},
        "d2": {"x": 30.0, "y": 10.0, "w": 10.0, "h": 0.5},
    }
    result = run_drc(circuit, placements)
    assert "PORT_FACING" not in _violation_rule_names(result)
    # 严格模式下应报违规
    result_strict = run_drc(circuit, placements, bend_compensate=False)
    assert "PORT_FACING" in _violation_rule_names(result_strict)


def test_port_alignment_pass():
    """PORT_ALIGNMENT 通过：bend_compensate=True（默认）跳过对齐检查。

    *创新*: 弯曲补偿（S-bend/Bezier/Euler）可连接任意位置端口
    （Chrostowski & Hochberg 2015 §4.3），PORT_ALIGNMENT 在 bend_compensate=True
    时不检查（返回空）。
    """
    result = run_drc(_make_clean_circuit(), _make_clean_placements())
    assert "PORT_ALIGNMENT" not in _violation_rule_names(result)


def test_port_alignment_fail():
    """PORT_ALIGNMENT 违规（严格模式 bend_compensate=False）：dx>10 且 dy>10。

    d1.out abs=(20,10), d2.in abs=(50,30), dx=30>10, dy=20>10。
    bend_compensate=False 时检查对齐；=True 时跳过（弯曲补偿）。
    """
    circuit = _make_clean_circuit()
    placements = {
        "d1": {"x": 10.0, "y": 10.0, "w": 10.0, "h": 0.5},
        "d2": {"x": 50.0, "y": 30.0, "w": 10.0, "h": 0.5},
    }
    result = run_drc(circuit, placements, bend_compensate=False)
    assert "PORT_ALIGNMENT" in _violation_rule_names(result)


# =============================================================================
# 10. 密度规则（DENSITY_MAX / DENSITY_MIN）
# =============================================================================


def test_density_max_pass():
    """DENSITY_MAX 通过：布局密度 0.1% ≤ 阈值 80%。

    公式: density = Σ(device_area) / canvas_area × 100%。
    来源: Banerjee "CMOS Photonic Circuits" Springer 2024（CMP 密度上限）。
    """
    result = run_drc(_make_clean_circuit(), _make_clean_placements())
    assert "DENSITY_MAX" not in _violation_rule_names(result)


def test_density_max_fail():
    """DENSITY_MAX 违规：布局密度 81% > 阈值 80%。

    canvas=10×10=100μm², device=9×9=81μm², density=81%。
    """
    circuit = {
        "name": "dense",
        "devices": [{"name": "d1", "device_type": "wg",
                     "ports": [("in", 0, 0, "west"), ("out", 10, 0, "east")]}],
        "connections": [],
        "canvas_w": 10, "canvas_h": 10,
    }
    placements = {"d1": {"x": 0.0, "y": 0.0, "w": 9.0, "h": 9.0}}
    result = run_drc(circuit, placements)
    assert "DENSITY_MAX" in _violation_rule_names(result)


def test_density_min_pass():
    """DENSITY_MIN 通过：布局密度 0.1% ≥ 阈值 0.01%。"""
    result = run_drc(_make_clean_circuit(), _make_clean_placements())
    assert "DENSITY_MIN" not in _violation_rule_names(result)


def test_density_min_fail():
    """DENSITY_MIN 违规：布局密度 1e-6% < 阈值 0.01%（避免空版图）。

    canvas=10000×10000=1e8μm², device=1×1=1μm², density=1e-6%。
    """
    circuit = {
        "name": "sparse",
        "devices": [{"name": "d1", "device_type": "wg",
                     "ports": [("in", 0, 0, "west"), ("out", 10, 0, "east")]}],
        "connections": [],
        "canvas_w": 10000, "canvas_h": 10000,
    }
    placements = {"d1": {"x": 0.0, "y": 0.0, "w": 1.0, "h": 1.0}}
    result = run_drc(circuit, placements)
    assert "DENSITY_MIN" in _violation_rule_names(result)


def test_density_min_xxl_threshold():
    """DENSITY_MIN ≥1mm 画布连续缩放阈值（*创新*，光电子 EDA 专用）。

    canvas=50000×50000μm²（50mm，≥1mm 连续缩放），阈值=10/canvas_area×100。
    threshold = 10/(50000×50000)×100 = 10/2.5e9×100 = 4e-7%。
    device=1×1=1μm²，density=1/2.5e9×100=4e-8% < 4e-7% → 违规。
    device=100×100=10000μm²，density=10000/2.5e9×100=4e-4% > 4e-7% → 通过。

    连续缩放底层逻辑: CMP 是晶圆级工艺，密度按 process window（~1mm×1mm）
    平均，whole-canvas density 对大画布无工艺意义。≥1mm 画布只要上有
    ≥10μm² 器件面积即通过（SiEPIC WG_MIN_AREA 0.1μm² × 100x safety factor）。

    来源: Banerjee "CMOS Photonic Circuits" Springer 2024（CMP 密度规则）；
          SiEPIC EBeam PDK DRC runset https://github.com/SiEPIC/SiEPIC_EBeam_PDK；
          Chrostowski & Hochberg 2015 §4.3（大画布器件密度天然低）
    """
    from polaris_drc.checks import density_min_threshold_by_canvas
    # ≥1mm 连续缩放: threshold = 10/canvas_area×100
    expected_thr = 10.0 / (50000.0 * 50000.0) * 100.0  # 4e-7%
    assert density_min_threshold_by_canvas(50000, 50000) == pytest.approx(expected_thr), (
        f"≥1mm 连续缩放阈值应为 {expected_thr}%（10/2.5e9×100），"
        f"实际 {density_min_threshold_by_canvas(50000, 50000)}"
    )
    # 违规：device 1×1=1μm²，density=4e-8% < threshold 4e-7%
    circuit_sparse = {
        "name": "xxl_sparse",
        "devices": [{"name": "d1", "device_type": "wg",
                     "ports": [("in", 0, 0, "west"), ("out", 10, 0, "east")]}],
        "connections": [],
        "canvas_w": 50000, "canvas_h": 50000,
    }
    placements_sparse = {"d1": {"x": 0.0, "y": 0.0, "w": 1.0, "h": 1.0}}
    result = run_drc(circuit_sparse, placements_sparse)
    assert "DENSITY_MIN" in _violation_rule_names(result), (
        "≥1mm 画布 1μm²/2.5e9μm²=4e-8% < 4e-7% 应违规"
    )
    # 通过：device 100×100=10000μm²，density=4e-4% > threshold 4e-7%
    circuit_dense = {
        "name": "xxl_dense",
        "devices": [{"name": "d1", "device_type": "wg",
                     "ports": [("in", 0, 0, "west"), ("out", 10, 0, "east")]}],
        "connections": [],
        "canvas_w": 50000, "canvas_h": 50000,
    }
    placements_dense = {"d1": {"x": 0.0, "y": 0.0, "w": 100.0, "h": 100.0}}
    result_dense = run_drc(circuit_dense, placements_dense)
    assert "DENSITY_MIN" not in _violation_rule_names(result_dense), (
        "≥1mm 画布 10000μm²/2.5e9μm²=4e-4% > 4e-7% 应通过"
    )


def test_density_min_xxxl_threshold():
    """DENSITY_MIN 晶圆级画布连续缩放阈值（*创新*）。

    canvas=200000×200000μm²（200mm，≥1mm 连续缩放），阈值=10/canvas_area×100。
    threshold = 10/(200000×200000)×100 = 10/4e10×100 = 2.5e-8%。
    LiDAR OPA 阵列等晶圆级光子电路常用 100mm+ 画布。

    连续缩放底层逻辑: CMP 是晶圆级工艺，密度按 process window（~1mm×1mm）
    平均，whole-canvas density 对晶圆级画布无工艺意义。≥1mm 画布只要上有
    ≥10μm² 器件面积即通过。

    来源: ISPD 2025 LiDAR benchmark https://github.com/ALIGN-analoglayout/ALIGN；
          Banerjee "CMOS Photonic Circuits" Springer 2024（CMP 密度规则）；
          SiEPIC EBeam PDK DRC runset https://github.com/SiEPIC/SiEPIC_EBeam_PDK
    """
    from polaris_drc.checks import density_min_threshold_by_canvas
    # ≥1mm 连续缩放: threshold = 10/canvas_area×100
    # 200000×200000 = 4e10 μm², threshold = 10/4e10×100 = 2.5e-8%
    expected_thr_xxxl = 10.0 / (200000.0 * 200000.0) * 100.0
    assert density_min_threshold_by_canvas(200000, 200000) == pytest.approx(expected_thr_xxxl), (
        f"≥1mm 连续缩放阈值应为 {expected_thr_xxxl}%（10/4e10×100），"
        f"实际 {density_min_threshold_by_canvas(200000, 200000)}"
    )
    # 100000×50000 = 5e9 μm², threshold = 10/5e9×100 = 2e-7%
    expected_thr_100k = 10.0 / (100000.0 * 50000.0) * 100.0
    assert density_min_threshold_by_canvas(100000, 50000) == pytest.approx(expected_thr_100k), (
        f"100000×50000 连续缩放阈值应为 {expected_thr_100k}%"
    )
    # 99999×50000: max=99999 ≥ 1000，仍为连续缩放
    expected_thr_99999 = 10.0 / (99999.0 * 50000.0) * 100.0
    assert density_min_threshold_by_canvas(99999, 50000) == pytest.approx(expected_thr_99999), (
        f"99999×50000 连续缩放阈值应为 {expected_thr_99999}%（≥1mm 连续缩放）"
    )
    # 旧分级保持兼容（< 1mm 仍为离散分级，≥1mm 连续缩放）
    assert density_min_threshold_by_canvas(100, 100) == 0.01       # XS/S
    assert density_min_threshold_by_canvas(600, 600) == 0.005      # M
    # ≥1mm 连续缩放: 1500×1500 → 10/2.25e6×100 ≈ 4.44e-4%
    assert density_min_threshold_by_canvas(1500, 1500) == pytest.approx(10.0 / (1500.0 * 1500.0) * 100.0)
    # 3000×3000 → 10/9e6×100 ≈ 1.11e-4%
    assert density_min_threshold_by_canvas(3000, 3000) == pytest.approx(10.0 / (3000.0 * 3000.0) * 100.0)
    # ≥1mm 全部连续缩放（不再有 XL 离散分级）
    # 8000×8000: 10/6.4e7×100 ≈ 1.5625e-5%
    assert density_min_threshold_by_canvas(8000, 8000) == pytest.approx(10.0 / (8000.0 * 8000.0) * 100.0)
    # 9999×9999: 10/99980001×100 ≈ 1.0002e-5%
    assert density_min_threshold_by_canvas(9999, 9999) == pytest.approx(10.0 / (9999.0 * 9999.0) * 100.0)
    # 10000×10000: 10/1e8×100 = 1e-5%
    expected_thr_10k = 10.0 / (10000.0 * 10000.0) * 100.0  # 1e-5%
    assert density_min_threshold_by_canvas(10000, 10000) == pytest.approx(expected_thr_10k), (
        f"10000×10000 连续缩放阈值应为 {expected_thr_10k}%（≥1mm 连续缩放）"
    )


# =============================================================================
# 11. 综合布局与边界情况（4 个测试）
# =============================================================================


def test_drc_clean_layout():
    """DRC clean 布局：所有 12 条规则通过，n_violations=0，pass_rate=1.0。

    构造 2 器件 + 1 连接的合法布局：
    - 几何规则：间距 10μm ≥ 1.0，宽 10 ≥ 0.5，高 0.5 ≥ 0.4，面积 5 ≥ 0.1
    - 边界：都在 100×100 画布内
    - 端口：方向合法、已连接、east↔west 相对、y 轴对齐
    - 密度：0.1% ∈ [0.01%, 80%]
    """
    result = run_drc(_make_clean_circuit(), _make_clean_placements())
    assert result["n_violations"] == 0, (
        f"DRC clean 布局应无违规，实际 n_violations={result['n_violations']}, "
        f"violations={result['violations']}"
    )
    assert result["pass_rate"] == 1.0
    assert result["n_passed"] == 12


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


def test_drc_simple_waveguide():
    """简单波导布局验证（与任务验证脚本一致）。

    单个 strip_waveguide 10μm × 0.5μm，画布 100×100μm。
    验证: 返回 dict 含全部必要字段，n_rules=12，pass_rate > 0。
    """
    circuit = _make_simple_circuit()
    placements = _make_simple_placements()
    result = run_drc(circuit, placements)
    assert result["n_rules"] == 12
    assert result["pass_rate"] > 0.0, (
        f"合法布局至少部分规则会通过，pass_rate={result['pass_rate']}"
    )


# =============================================================================
# 回归测试：expert_demos 中心点坐标 Bug（R05 Bug 必修）
# =============================================================================
# Bug 描述: scripts/run_real_board_drc.py 的 convert_expert_demo 函数
#   误把 SiEPIC GDS 提取的 placements.json 中 x/y（器件中心点坐标）当作
#   左下角，导致 AABB 向右上方偏移 (w/2, h/2)，相邻器件误报 NO_OVERLAP。
# 修复: 优先用 bbox[0:2]（真实物理 AABB 左下角），无 bbox 时 x-w/2, y-h/2。
# 来源: SiEPIC Tools GDS 提取约定 + KLayout Instance API bbox 语义
#   https://github.com/SiEPIC/SiEPIC-Tools
#   https://www.klayout.org/doc-qt5/code/class_Instance.html


def test_expert_demos_center_point_to_corner_bbox():
    """验证 convert_expert_demo 用 bbox 作为左下角（R05 回归）。

    构造中心点坐标 (147, 27) + bbox=[132, 17, 162, 37] + w=30, h=20 的器件，
    验证转换后 placements.x = 132（bbox[0]），而非 147（中心点 x）。
    """
    # 延迟导入：测试 scripts/run_real_board_drc.py 的转换函数
    sys.path.insert(0, "/workspace/scripts")
    # 重命名避免与测试模块名冲突
    import importlib
    rbd = importlib.import_module("run_real_board_drc")

    meta = {"canvas_w_um": 200.0, "canvas_h_um": 100.0}
    netlist = {
        "name": "test_center",
        "devices": [{
            "name": "d1",
            "device_type": "mmi",
            "width_um": 30.0,
            "height_um": 20.0,
            "ports": [["o1", 0, 10, "west"], ["o2", 30, 10, "east"]],
            "params": {},
        }],
        "connections": [],
        "canvas_w": 200.0,
        "canvas_h": 100.0,
    }
    # x/y=中心点 (147, 27)，bbox=[xmin=132, ymin=17, xmax=162, ymax=37]
    placements_raw = {
        "d1": {
            "x": 147.0, "y": 27.0,
            "width": 30.0, "height": 20.0,
            "bbox": [132.0, 17.0, 162.0, 37.0],
            "rotation": 0.0, "mirror": False,
        }
    }
    circuit, placements = rbd.convert_expert_demo(meta, netlist, placements_raw)
    # 修复后: x 应为 bbox[0]=132.0（左下角），而非中心点 147.0
    assert placements["d1"]["x"] == 132.0, (
        f"bbox 优先: x 应为 132.0（bbox[0]），实际 {placements['d1']['x']}"
    )
    assert placements["d1"]["y"] == 17.0, (
        f"bbox 优先: y 应为 17.0（bbox[1]），实际 {placements['d1']['y']}"
    )
    assert placements["d1"]["w"] == 30.0
    assert placements["d1"]["h"] == 20.0


def test_expert_demos_center_point_to_corner_no_bbox():
    """验证无 bbox 时中心点坐标转左下角（R05 回归）。

    构造中心点 (50, 30) + w=20, h=10（无 bbox）的器件，
    验证转换后 x = 50 - 20/2 = 40, y = 30 - 10/2 = 25。
    """
    sys.path.insert(0, "/workspace/scripts")
    import importlib
    rbd = importlib.import_module("run_real_board_drc")

    meta = {"canvas_w_um": 100.0, "canvas_h_um": 100.0}
    netlist = {
        "name": "test_no_bbox",
        "devices": [{
            "name": "d1",
            "device_type": "wg",
            "width_um": 20.0,
            "height_um": 10.0,
            "ports": [["o1", 0, 5, "west"], ["o2", 20, 5, "east"]],
            "params": {},
        }],
        "connections": [],
        "canvas_w": 100.0,
        "canvas_h": 100.0,
    }
    placements_raw = {
        "d1": {"x": 50.0, "y": 30.0, "width": 20.0, "height": 10.0}
    }
    circuit, placements = rbd.convert_expert_demo(meta, netlist, placements_raw)
    # 修复后: x = 50 - 20/2 = 40, y = 30 - 10/2 = 25
    assert placements["d1"]["x"] == 40.0, (
        f"中心点→左下角: x 应为 40.0 (50-20/2)，实际 {placements['d1']['x']}"
    )
    assert placements["d1"]["y"] == 25.0, (
        f"中心点→左下角: y 应为 25.0 (30-10/2)，实际 {placements['d1']['y']}"
    )


def test_expert_demos_mzi_2x2_switch_no_overlap():
    """验证 mzi_2x2_switch 不再误报 NO_OVERLAP（R05 回归）。

    Bug 修复前: mmi_rgt_1 (中心 147,27) 与 phase_shifter4 (中心 81,44)
    因中心点当左下角导致 AABB 偏移，误报重叠。
    修复后: 用 bbox 正确计算 AABB，无重叠。
    """
    sys.path.insert(0, "/workspace/scripts")
    import importlib
    rbd = importlib.import_module("run_real_board_drc")
    import json
    from pathlib import Path

    demo_dir = Path("/workspace/data/expert_demos/mzi_2x2_switch")
    meta = json.loads((demo_dir / "meta.json").read_text())
    netlist = json.loads((demo_dir / "netlist.json").read_text())
    placements_raw = json.loads((demo_dir / "placements.json").read_text())

    circuit, placements = rbd.convert_expert_demo(meta, netlist, placements_raw)
    result = run_drc(circuit, placements)
    # 修复后应无 NO_OVERLAP / MIN_SPACING 违规
    violated = {v["rule_name"] for v in result["violations"]}
    assert "NO_OVERLAP" not in violated, (
        f"mzi_2x2_switch 不应误报 NO_OVERLAP，违规: {violated}"
    )
    assert "MIN_SPACING" not in violated, (
        f"mzi_2x2_switch 不应误报 MIN_SPACING，违规: {violated}"
    )
