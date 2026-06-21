"""KLayout DRC runset 适配层测试（第2轮 P0-1）。

测试覆盖:
- DRCRule/DRCResult dataclass
- SIEPIC_EBEAM_DRC_RUNSET 默认 runset 完整性
- KLayoutDRCRunner.run_gds 对真实 GDS 文件的 DRC 检查
- run_klayout_drc 便捷函数
- 各 DRCCheckType（WIDTH/SPACE/NOTCH/AREA）

来源:
- KLayout DRC API: https://www.klayout.org/doc-qt5/manual/drc_runsets.html
- SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
"""

from __future__ import annotations

from pathlib import Path

import klayout.db as db
import pytest

from polaris.pdk.layer_map import get_layer_tuple
from polaris.sim.constraint_checker import ViolationType
from polaris.sim.klayout_drc import (
    SIEPIC_EBEAM_DRC_RUNSET,
    DRCCheckType,
    DRCResult,
    DRCRule,
    KLayoutDRCRunner,
    run_klayout_drc,
)

# -- dataclass 测试 --


def test_drc_rule_dataclass():
    """测试 DRCRule dataclass。"""
    rule = DRCRule(
        name="TEST_WIDTH",
        layer_name="WG",
        check_type=DRCCheckType.WIDTH,
        threshold_um=0.5,
        vtype=ViolationType.MIN_WIDTH,
        description="测试规则",
    )
    assert rule.name == "TEST_WIDTH"
    assert rule.layer_name == "WG"
    assert rule.check_type == DRCCheckType.WIDTH
    assert rule.threshold_um == 0.5
    assert rule.enclosure_layer_name is None


def test_drc_result_dataclass():
    """测试 DRCResult dataclass。"""
    result = DRCResult()
    assert result.violation_count == 0
    assert result.is_clean
    result.violations.append(
        type(
            "V",
            (),
            {"vtype": ViolationType.MIN_WIDTH},
        )()
    )
    assert result.violation_count == 1
    assert not result.is_clean


def test_drc_result_with_violations():
    """测试 DRCResult 含违规。"""
    from polaris.sim.constraint_checker import Violation

    result = DRCResult(
        violations=[Violation(vtype=ViolationType.MIN_WIDTH)],
        total_rules=8,
        passed_rules=7,
    )
    assert result.violation_count == 1
    assert not result.is_clean
    assert result.passed_rules == 7


# -- 默认 runset 测试 --


def test_siepic_ebeam_runset_completeness():
    """测试 SiEPIC EBeam 默认 runset 完整性。"""
    assert len(SIEPIC_EBEAM_DRC_RUNSET) >= 8
    # 每条规则必须有 name/layer/check_type/threshold
    for rule in SIEPIC_EBEAM_DRC_RUNSET:
        assert rule.name, f"规则缺少 name: {rule}"
        assert rule.layer_name in ("WG", "DEEPTRENCH", "SLAB150", "GE"), (
            f"未知层: {rule.layer_name}"
        )
        assert rule.threshold_um > 0, f"阈值无效: {rule}"
        assert rule.description, f"缺少描述: {rule}"


def test_siepic_runset_has_width_and_space():
    """测试 SiEPIC runset 包含 WIDTH 和 SPACE 检查。"""
    check_types = {r.check_type for r in SIEPIC_EBEAM_DRC_RUNSET}
    assert DRCCheckType.WIDTH in check_types
    assert DRCCheckType.SPACE in check_types
    assert DRCCheckType.NOTCH in check_types
    assert DRCCheckType.AREA in check_types


def test_siepic_runset_wg_min_width_04():
    """测试 SiEPIC WG 层最小宽度为 0.4μm（工艺极限）。"""
    wg_width_rules = [
        r
        for r in SIEPIC_EBEAM_DRC_RUNSET
        if r.layer_name == "WG" and r.check_type == DRCCheckType.WIDTH
    ]
    assert len(wg_width_rules) == 1
    assert wg_width_rules[0].threshold_um == 0.4


# -- GDS 文件 DRC 检查测试 --


@pytest.fixture
def clean_gds(tmp_path: Path) -> Path:
    """生成 DRC clean 的 GDS 文件（宽波导，大间距）。"""
    gds_path = tmp_path / "clean.gds"
    layout = db.Layout()
    layout.dbu = 0.001
    cell = layout.create_cell("CLEAN")
    wg_layer = get_layer_tuple("WG")
    layer_idx = layout.layer(db.LayerInfo(wg_layer[0], wg_layer[1]))
    # 画一个 2μm 宽、100μm 长的波导（远大于 0.4μm 最小宽度）
    rect = db.DBox(0, 0, 100, 2.0)
    cell.shapes(layer_idx).insert(db.DPolygon(rect))
    layout.write(str(gds_path))
    return gds_path


@pytest.fixture
def violation_gds(tmp_path: Path) -> Path:
    """生成有 DRC 违规的 GDS 文件（窄波导 0.2μm < 0.4μm）。"""
    gds_path = tmp_path / "violation.gds"
    layout = db.Layout()
    layout.dbu = 0.001
    cell = layout.create_cell("VIOLATION")
    wg_layer = get_layer_tuple("WG")
    layer_idx = layout.layer(db.LayerInfo(wg_layer[0], wg_layer[1]))
    # 画一个 0.2μm 宽的波导（< 0.4μm 最小宽度）
    rect = db.DBox(0, 0, 100, 0.2)
    cell.shapes(layer_idx).insert(db.DPolygon(rect))
    layout.write(str(gds_path))
    return gds_path


@pytest.fixture
def spacing_violation_gds(tmp_path: Path) -> Path:
    """生成有间距违规的 GDS 文件（两波导间距 0.5μm < 1.0μm）。"""
    gds_path = tmp_path / "spacing_violation.gds"
    layout = db.Layout()
    layout.dbu = 0.001
    cell = layout.create_cell("SPACING_VIOLATION")
    wg_layer = get_layer_tuple("WG")
    layer_idx = layout.layer(db.LayerInfo(wg_layer[0], wg_layer[1]))
    # 两个波导，间距 0.5μm（< 1.0μm 最小间距）
    cell.shapes(layer_idx).insert(db.DPolygon(db.DBox(0, 0, 100, 1.0)))
    cell.shapes(layer_idx).insert(db.DPolygon(db.DBox(0, 1.5, 100, 2.5)))
    layout.write(str(gds_path))
    return gds_path


def test_run_gds_clean(clean_gds: Path):
    """测试 DRC clean 的 GDS 文件。"""
    runner = KLayoutDRCRunner()
    result = runner.run_gds(clean_gds)
    assert result.is_clean, f"期望 DRC clean，但有 {result.violation_count} 个违规"
    assert result.total_rules == len(SIEPIC_EBEAM_DRC_RUNSET)
    assert result.passed_rules >= 1  # 至少 WG_WIDTH 通过


def test_run_gds_width_violation(violation_gds: Path):
    """测试检测到宽度违规。"""
    runner = KLayoutDRCRunner()
    result = runner.run_gds(violation_gds)
    assert not result.is_clean
    # 应有 MIN_WIDTH 类型违规
    width_violations = [v for v in result.violations if v.vtype == ViolationType.MIN_WIDTH]
    assert len(width_violations) > 0, "期望检测到 MIN_WIDTH 违规"
    # 验证违规有位置信息
    for v in width_violations:
        assert v.location is not None
        assert "WG_MIN_WIDTH" in v.message


def test_run_gds_spacing_violation(spacing_violation_gds: Path):
    """测试检测到间距违规。"""
    runner = KLayoutDRCRunner()
    result = runner.run_gds(spacing_violation_gds)
    assert not result.is_clean
    # 应有 SPACING 类型违规
    spacing_violations = [v for v in result.violations if v.vtype == ViolationType.SPACING]
    assert len(spacing_violations) > 0, "期望检测到 SPACING 违规"


def test_run_gds_file_not_found():
    """测试 GDS 文件不存在时抛出 FileNotFoundError。"""
    runner = KLayoutDRCRunner()
    with pytest.raises(FileNotFoundError):
        runner.run_gds("/nonexistent/path.gds")


def test_run_gds_custom_runset(clean_gds: Path):
    """测试使用自定义 runset。"""
    custom_rule = DRCRule(
        name="CUSTOM_WG_WIDTH",
        layer_name="WG",
        check_type=DRCCheckType.WIDTH,
        threshold_um=0.3,
        vtype=ViolationType.MIN_WIDTH,
        description="自定义宽度规则",
    )
    runner = KLayoutDRCRunner()
    result = runner.run_gds(clean_gds, [custom_rule])
    assert result.runset_name == "custom"
    assert result.total_rules == 1
    # 2μm 波导 > 0.3μm，应 clean
    assert result.is_clean


def test_run_gds_strict_runset(clean_gds: Path):
    """测试严格 runset（阈值高于实际宽度，应报违规）。"""
    strict_rule = DRCRule(
        name="STRICT_WG_WIDTH",
        layer_name="WG",
        check_type=DRCCheckType.WIDTH,
        threshold_um=3.0,  # > 2.0μm 实际宽度
        vtype=ViolationType.MIN_WIDTH,
        description="严格宽度规则",
    )
    runner = KLayoutDRCRunner()
    result = runner.run_gds(clean_gds, [strict_rule])
    assert not result.is_clean
    assert result.violation_count > 0


def test_run_klayout_drc_convenience_function(clean_gds: Path):
    """测试 run_klayout_drc 便捷函数。"""
    violations = run_klayout_drc(clean_gds)
    assert isinstance(violations, list)
    # clean GDS 应无违规
    assert len(violations) == 0


def test_run_klayout_drc_with_violation(violation_gds: Path):
    """测试 run_klayout_drc 便捷函数检测违规。"""
    violations = run_klayout_drc(violation_gds)
    assert len(violations) > 0
    assert any(v.vtype == ViolationType.MIN_WIDTH for v in violations)


def test_layer_not_in_gds_skipped(clean_gds: Path):
    """测试 GDS 中不存在的层被跳过（非违规）。"""
    # SiEPIC runset 包含 DEEPTRENCH/SLAB150/GE 层，但 clean_gds 只有 WG
    runner = KLayoutDRCRunner()
    result = runner.run_gds(clean_gds)
    # 不存在的层不应产生违规
    assert result.is_clean


def test_violation_has_location(violation_gds: Path):
    """测试违规记录包含位置信息。"""
    runner = KLayoutDRCRunner()
    result = runner.run_gds(violation_gds)
    for v in result.violations:
        assert v.location is not None
        assert len(v.location) == 2
        # 位置应在 GDS 坐标范围内
        assert -1000 < v.location[0] < 1000
        assert -1000 < v.location[1] < 1000
