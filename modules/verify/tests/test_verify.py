"""polaris-verify 子模块测试。

测试覆盖:
- test_drc_mzi: 5 器件 MZI 布局 DRC，验证 n_rules>=11, pass_rate>0
- test_lvs_mzi: 5 器件 5 连接 MZI LVS，验证 is_consistent=True, n_mismatches=0
- test_drc_violations: 故意制造重叠，验证 n_violations>0
- test_lvs_with_netlist: 提供 netlist 参数比对，验证一致性判定
- test_drc_invalid_input: 非法 circuit/placements raise RuntimeError
- test_lvs_mismatch: 故意制造器件差异，验证 n_mismatches>0

来源（R02 学术诚信）:
- pytest 文档: https://docs.pytest.org/
- SiEPIC EBeam PDK DRC runset: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- KLayout DRC 文档: https://www.klayout.org/doc-qt5/manual/drc_runsets.html
- KLayout LVS API: https://www.klayout.org/doc-qt5/manual/lvs.html
- Chrostowski & Hochberg 2015 Silicon Photonics Design
  https://www.cambridge.org/core/books/silicon-photonics-design/
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# 让测试既能从已安装包导入，也能从源码树导入（CI/开发模式）
_SRC = str(Path(__file__).resolve().parents[1] / "src")
_CORE_SRC = str(Path(__file__).resolve().parents[2] / "core" / "src")
_PLACE_SRC = str(Path(__file__).resolve().parents[2] / "place" / "src")
for _p in (_SRC, _CORE_SRC, _PLACE_SRC):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import polaris_verify  # noqa: E402
from polaris_core import make_circuit, make_device  # noqa: E402
from polaris_place import place_circuit  # noqa: E402
from polaris_verify import run_drc, run_lvs  # noqa: E402


def _make_mzi_circuit() -> dict:
    """构造 5 器件 MZI 电路（与验证脚本一致）。

    1 光栅耦合器 + 2 MMI + 2 波导臂，构成马赫-曾德干涉仪。
    """
    gc = make_device(
        "gc1", "grating_coupler", 20, 20,
        ports=[("in", 0, 10, "west"), ("out", 20, 10, "east")],
    )
    mmi = make_device(
        "mmi1", "mmi_1x2", 20, 5,
        ports=[("in", 0, 2.5, "west"), ("out1", 20, 1.5, "east"),
               ("out2", 20, 3.5, "east")],
    )
    wg1 = make_device(
        "wg1", "strip_waveguide", 100, 0.5,
        ports=[("in", 0, 0.25, "west"), ("out", 100, 0.25, "east")],
    )
    wg2 = make_device(
        "wg2", "strip_waveguide", 120, 0.5,
        ports=[("in", 0, 0.25, "west"), ("out", 120, 0.25, "east")],
    )
    mmi2 = make_device(
        "mmi2", "mmi_2x2", 20, 5,
        ports=[("in1", 0, 1.5, "west"), ("in2", 0, 3.5, "west"),
               ("out1", 20, 1.5, "east"), ("out2", 20, 3.5, "east")],
    )
    return make_circuit(
        "MZI",
        [gc, mmi, wg1, wg2, mmi2],
        [
            ("gc1", "out", "mmi1", "in"),
            ("mmi1", "out1", "wg1", "in"),
            ("mmi1", "out2", "wg2", "in"),
            ("wg1", "out", "mmi2", "in1"),
            ("wg2", "out", "mmi2", "in2"),
        ],
        canvas_w=500,
        canvas_h=300,
    )


def test_drc_mzi():
    """5 器件 MZI 布局 DRC: n_rules>=11, pass_rate>0, 字段完整。

    验证:
    - 返回 dict 含全部必要字段（n_rules/n_violations/n_passed/pass_rate/violations）
    - n_rules >= 11（默认 12 条 SiEPIC PDK 规则）
    - pass_rate > 0（合法布局至少部分规则通过）
    - 每个 violation 含 rule_name/severity/message/device_name/location
    """
    circuit = _make_mzi_circuit()
    placements = place_circuit(circuit, mode="analytical")
    result = run_drc(circuit, placements["placements"])

    # 必要字段
    for key in ("n_rules", "n_violations", "n_passed", "pass_rate", "violations"):
        assert key in result, f"DRC 结果缺少字段: {key}"

    assert result["n_rules"] >= 11, (
        f"n_rules 应 >= 11，实际 {result['n_rules']}"
    )
    assert result["pass_rate"] > 0.0, (
        f"pass_rate 应 > 0（合法布局至少部分规则通过），实际 {result['pass_rate']}"
    )
    # n_passed + 有违规的规则数 = n_rules
    violated_rules = {v["rule_name"] for v in result["violations"]}
    assert result["n_passed"] + len(violated_rules) == result["n_rules"]

    # 验证 violation 结构
    for v in result["violations"]:
        for field in ("rule_name", "severity", "message", "device_name", "location"):
            assert field in v, f"violation 缺少字段: {field}"
        assert isinstance(v["location"], list) and len(v["location"]) == 2


def test_lvs_mzi():
    """5 器件 5 连接 MZI LVS: is_consistent=True, n_mismatches=0。

    自比对（netlist=None）必然一致，验证 extract_netlist + compare_netlists API。
    """
    circuit = _make_mzi_circuit()
    result = run_lvs(circuit)

    for key in ("is_consistent", "n_mismatches", "mismatches",
                "n_devices", "n_connections"):
        assert key in result, f"LVS 结果缺少字段: {key}"

    assert result["is_consistent"] is True, (
        f"MZI 自比对应一致，is_consistent={result['is_consistent']}"
    )
    assert result["n_mismatches"] == 0, (
        f"MZI 自比对应无不匹配，n_mismatches={result['n_mismatches']}"
    )
    assert result["n_devices"] == 5, f"n_devices 应=5，实际 {result['n_devices']}"
    assert result["n_connections"] == 5, (
        f"n_connections 应=5，实际 {result['n_connections']}"
    )
    assert result["mismatches"] == []


def test_drc_violations():
    """故意制造器件重叠，验证 n_violations>0（NO_OVERLAP 规则触发）。

    构造两个完全重叠的器件布局，DRC 应报告 NO_OVERLAP 与 MIN_SPACING 违规。
    """
    gc = make_device(
        "gc1", "grating_coupler", 20, 20,
        ports=[("in", 0, 10, "west"), ("out", 20, 10, "east")],
    )
    mmi = make_device(
        "mmi1", "mmi_1x2", 20, 5,
        ports=[("in", 0, 2.5, "west"), ("out1", 20, 1.5, "east")],
    )
    circuit = make_circuit(
        "Overlap", [gc, mmi],
        [("gc1", "out", "mmi1", "in")],
        canvas_w=500, canvas_h=300,
    )
    # 故意让两器件完全重叠（同位置同尺寸区域）
    placements = {
        "gc1": {"x": 100.0, "y": 100.0, "w": 20.0, "h": 20.0},
        "mmi1": {"x": 100.0, "y": 100.0, "w": 20.0, "h": 5.0},  # 与 gc1 重叠
    }
    result = run_drc(circuit, placements)

    assert result["n_violations"] > 0, (
        f"重叠布局应触发违规，n_violations={result['n_violations']}"
    )
    # 应包含 NO_OVERLAP 违规
    rule_names = {v["rule_name"] for v in result["violations"]}
    assert "NO_OVERLAP" in rule_names, (
        f"重叠应触发 NO_OVERLAP 规则，实际触发规则: {rule_names}"
    )


def test_lvs_with_netlist_consistent():
    """提供与 circuit 一致的 netlist 参数，验证 is_consistent=True。"""
    circuit = _make_mzi_circuit()
    # 构造与 circuit 一致的提取网表
    netlist = {
        "devices": [
            {"name": "gc1", "device_type": "grating_coupler"},
            {"name": "mmi1", "device_type": "mmi_1x2"},
            {"name": "wg1", "device_type": "strip_waveguide"},
            {"name": "wg2", "device_type": "strip_waveguide"},
            {"name": "mmi2", "device_type": "mmi_2x2"},
        ],
        "connections": [
            ["gc1", "mmi1"],
            ["mmi1", "wg1"],
            ["mmi1", "wg2"],
            ["wg1", "mmi2"],
            ["wg2", "mmi2"],
        ],
    }
    result = run_lvs(circuit, netlist)
    assert result["is_consistent"] is True
    assert result["n_mismatches"] == 0


def test_lvs_mismatch():
    """故意制造器件差异（多一个器件），验证 n_mismatches>0, is_consistent=False。"""
    circuit = _make_mzi_circuit()
    # 提取网表多一个器件 extra_dev，少一个器件 wg2
    netlist = {
        "devices": [
            {"name": "gc1", "device_type": "grating_coupler"},
            {"name": "mmi1", "device_type": "mmi_1x2"},
            {"name": "wg1", "device_type": "strip_waveguide"},
            {"name": "mmi2", "device_type": "mmi_2x2"},
            {"name": "extra_dev", "device_type": "phase_shifter"},
        ],
        "connections": [
            ["gc1", "mmi1"],
            ["mmi1", "wg1"],
            ["wg1", "mmi2"],
        ],
    }
    result = run_lvs(circuit, netlist)
    assert result["is_consistent"] is False
    assert result["n_mismatches"] > 0
    # 应包含缺失器件（wg2）与多余器件（extra_dev）以及连接差异
    types = {m["type"] for m in result["mismatches"]}
    assert "missing_device" in types
    assert "extra_device" in types


def test_drc_invalid_circuit():
    """非法 circuit（缺字段）应 raise RuntimeError（R03 禁止 fall-back）。"""
    placements = {"gc1": {"x": 0.0, "y": 0.0, "w": 10.0, "h": 10.0}}
    with pytest.raises(RuntimeError, match="circuit"):
        run_drc({}, placements)


def test_drc_invalid_placements():
    """非法 placements（器件缺字段）应 raise RuntimeError。"""
    circuit = _make_mzi_circuit()
    with pytest.raises(RuntimeError, match="placements"):
        run_drc(circuit, {"gc1": {"x": 0.0}})  # 缺 y/w/h


def test_drc_empty_placements():
    """空 placements 应 raise RuntimeError（R03 禁止 fall-back）。"""
    circuit = _make_mzi_circuit()
    with pytest.raises(RuntimeError, match="placements"):
        run_drc(circuit, {})


def test_lvs_invalid_circuit():
    """非法 circuit（缺 connections）应 raise RuntimeError。"""
    with pytest.raises(RuntimeError, match="circuit|devices|connections"):
        run_lvs({"name": "x", "devices": [], "canvas_w": 100, "canvas_h": 100})


def test_verify_version():
    """验证子模块版本号为 5.0.0（与 8 子模块统一版本对齐）。"""
    assert polaris_verify.__version__ == "5.0.0"
