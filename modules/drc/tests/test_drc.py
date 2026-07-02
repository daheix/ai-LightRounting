"""polaris-drc 子模块测试（从 polaris-verify 测试拆分 DRC 部分）。

测试覆盖（≥3 个 pytest，R13 强制自测）:
- test_drc_n_rules_12: 验证默认 DRC 规则数 = 12（SiEPIC EBeam PDK 完整规则集）
- test_drc_pass_rate_range: 验证 pass_rate ∈ [0, 1]（合法物理范围）
- test_drc_invalid_circuit_raises: 非法 circuit 缺字段 raise RuntimeError（R03）
- test_drc_invalid_placements_raises: 非法 placements 缺字段 raise RuntimeError
- test_drc_empty_placements_raises: 空 placements raise RuntimeError
- test_drc_violations_overlap: 故意制造重叠，验证 NO_OVERLAP 规则触发
- test_drc_simple_waveguide: 简单波导布局验证（与验证脚本一致）

来源（R02 学术诚信）:
- pytest 文档: https://docs.pytest.org/
- SiEPIC EBeam PDK DRC runset: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- KLayout DRC 文档: https://www.klayout.org/doc-qt5/manual/drc_runsets.html
- Chrostowski & Hochberg 2015 Silicon Photonics Design
  https://www.cambridge.org/core/books/silicon-photonics-design/
- Ericson "Real-Time Collision Detection" §5.1.3 AABB 距离
  https://realtimecollisiondetection.net/
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
from polaris_drc import run_drc  # noqa: E402


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


def test_drc_pass_rate_range():
    """验证 pass_rate ∈ [0, 1]（合法物理范围）。

    pass_rate = n_passed / n_rules，n_rules=12，n_passed ∈ [0, 12]，
    所以 pass_rate ∈ [0, 1]。
    """
    circuit = _make_simple_circuit()
    placements = _make_simple_placements()
    result = run_drc(circuit, placements)
    assert 0.0 <= result["pass_rate"] <= 1.0, (
        f"pass_rate 应 ∈ [0, 1]，实际 {result['pass_rate']}"
    )
    # n_passed + 违规规则数 = n_rules
    violated_rules = {v["rule_name"] for v in result["violations"]}
    assert result["n_passed"] + len(violated_rules) == result["n_rules"]


def test_drc_invalid_circuit_raises():
    """非法 circuit（缺字段）应 raise RuntimeError（R03 禁止 fall-back）。"""
    placements = {"wg": {"x": 0.0, "y": 0.0, "w": 10.0, "h": 0.5}}
    with pytest.raises(RuntimeError, match="circuit"):
        run_drc({}, placements)  # 缺 name/devices/canvas_w/canvas_h


def test_drc_invalid_placements_raises():
    """非法 placements（器件缺字段）应 raise RuntimeError。"""
    circuit = _make_simple_circuit()
    with pytest.raises(RuntimeError, match="placements"):
        run_drc(circuit, {"wg": {"x": 0.0}})  # 缺 y/w/h


def test_drc_empty_placements_raises():
    """空 placements 应 raise RuntimeError（R03 禁止 fall-back）。"""
    circuit = _make_simple_circuit()
    with pytest.raises(RuntimeError, match="placements"):
        run_drc(circuit, {})


def test_drc_violations_overlap():
    """故意制造器件重叠，验证 NO_OVERLAP 规则触发（n_violations>0）。

    构造两个完全重叠的器件布局，DRC 应报告 NO_OVERLAP 与 MIN_SPACING 违规。
    """
    circuit = {
        "name": "overlap",
        "devices": [
            {"name": "d1", "device_type": "strip_waveguide",
             "ports": [("in", 0, 0, "west"), ("out", 10, 0, "east")]},
            {"name": "d2", "device_type": "strip_waveguide",
             "ports": [("in", 0, 0, "west"), ("out", 10, 0, "east")]},
        ],
        "connections": [],
        "canvas_w": 100,
        "canvas_h": 100,
    }
    # 两个器件完全重叠（同位置同尺寸区域）
    placements = {
        "d1": {"x": 50.0, "y": 50.0, "w": 10.0, "h": 0.5},
        "d2": {"x": 50.0, "y": 50.0, "w": 10.0, "h": 0.5},
    }
    result = run_drc(circuit, placements)
    assert result["n_violations"] > 0, (
        f"重叠布局应触发违规，n_violations={result['n_violations']}"
    )
    rule_names = {v["rule_name"] for v in result["violations"]}
    assert "NO_OVERLAP" in rule_names, (
        f"重叠应触发 NO_OVERLAP 规则，实际触发: {rule_names}"
    )


def test_drc_simple_waveguide():
    """简单波导布局验证（与任务验证脚本一致）。

    单个 strip_waveguide 10μm × 0.5μm，画布 100×100μm。
    验证:
    - 返回 dict 含全部必要字段
    - n_rules=12
    - pass_rate > 0
    - violation 结构完整
    """
    circuit = _make_simple_circuit()
    placements = _make_simple_placements()
    result = run_drc(circuit, placements)

    # 必要字段
    for key in ("n_rules", "n_violations", "n_passed", "pass_rate", "violations"):
        assert key in result, f"DRC 结果缺少字段: {key}"

    assert result["n_rules"] == 12
    assert result["pass_rate"] > 0.0, (
        f"合法布局至少部分规则通过，pass_rate={result['pass_rate']}"
    )
    # 验证 violation 结构
    for v in result["violations"]:
        for field in ("rule_name", "severity", "message", "device_name", "location"):
            assert field in v, f"violation 缺少字段: {field}"
        assert isinstance(v["location"], list) and len(v["location"]) == 2


def test_drc_version():
    """验证 polaris-drc 子模块版本号 5.0.0（与原 polaris-verify 一致）。"""
    assert polaris_drc.__version__ == "5.0.0"
