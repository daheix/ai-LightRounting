"""polaris-lvs 子模块测试（从 polaris-verify 测试拆分 LVS 部分）。

测试覆盖（≥3 个 pytest，R13 强制自测）:
- test_lvs_self_consistent: 自比对（netlist=None）is_consistent=True
- test_lvs_missing_device_mismatch: 缺失器件 raise mismatch，is_consistent=False
- test_lvs_invalid_circuit_raises: 非法 circuit 缺字段 raise RuntimeError（R03）
- test_lvs_with_netlist_consistent: 提供与 circuit 一致的 netlist，is_consistent=True
- test_lvs_extra_device_mismatch: 提取网表多一个器件，is_consistent=False
- test_lvs_simple_waveguide: 简单波导 LVS 验证（与验证脚本一致）

来源（R02 学术诚信）:
- pytest 文档: https://docs.pytest.org/
- KLayout LVS API: https://www.klayout.org/doc-qt5/manual/lvs.html
- SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- Chrostowski & Hochberg 2015 Silicon Photonics Design
  https://www.cambridge.org/core/books/silicon-photonics-design/
- gdsfactory 网表提取: https://gdsfactory.github.io/gdsfactory/notebooks/09_pdk_import.html
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# 让测试既能从已安装包导入，也能从源码树导入（CI/开发模式）
_SRC = str(Path(__file__).resolve().parents[1] / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import polaris_lvs  # noqa: E402
from polaris_lvs import run_lvs  # noqa: E402


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


def test_lvs_self_consistent():
    """自比对（netlist=None）应 is_consistent=True（验证 API 一致性）。

    当 netlist=None 时，参考网表与自身比对，必然一致。
    """
    circuit = _make_simple_circuit()
    result = run_lvs(circuit)
    for key in ("is_consistent", "n_mismatches", "mismatches",
                "n_devices", "n_connections"):
        assert key in result, f"LVS 结果缺少字段: {key}"
    assert result["is_consistent"] is True, (
        f"自比对应一致，is_consistent={result['is_consistent']}"
    )
    assert result["n_mismatches"] == 0, (
        f"自比对应无不匹配，n_mismatches={result['n_mismatches']}"
    )
    assert result["n_devices"] == 1
    assert result["n_connections"] == 0


def test_lvs_missing_device_mismatch():
    """缺失器件应 raise mismatch，is_consistent=False（n_mismatches>0）。

    构造参考电路含 2 个器件，提取网表只含 1 个器件，应报告 missing_device。
    """
    circuit = {
        "name": "mismatch_test",
        "devices": [
            {"name": "wg1", "device_type": "strip_waveguide",
             "ports": [("in", 0, 0, "west"), ("out", 10, 0, "east")]},
            {"name": "wg2", "device_type": "strip_waveguide",
             "ports": [("in", 0, 0, "west"), ("out", 10, 0, "east")]},
        ],
        "connections": [],
        "canvas_w": 100,
        "canvas_h": 100,
    }
    # 提取网表只含 wg1，缺 wg2
    netlist = {
        "devices": [
            {"name": "wg1", "device_type": "strip_waveguide"},
        ],
        "connections": [],
    }
    result = run_lvs(circuit, netlist)
    assert result["is_consistent"] is False, (
        f"缺失器件应不一致，is_consistent={result['is_consistent']}"
    )
    assert result["n_mismatches"] > 0
    types = {m["type"] for m in result["mismatches"]}
    assert "missing_device" in types, (
        f"应报告 missing_device，实际: {types}"
    )


def test_lvs_invalid_circuit_raises():
    """非法 circuit（缺 connections）应 raise RuntimeError（R03 禁止 fall-back）。"""
    with pytest.raises(RuntimeError, match="circuit|devices|connections"):
        run_lvs({"name": "x", "devices": [], "canvas_w": 100, "canvas_h": 100})


def test_lvs_invalid_netlist_raises():
    """非法 netlist（缺字段）应 raise RuntimeError（R03 禁止 fall-back）。"""
    circuit = _make_simple_circuit()
    with pytest.raises(RuntimeError, match="netlist"):
        run_lvs(circuit, {"devices": []})  # 缺 connections


def test_lvs_with_netlist_consistent():
    """提供与 circuit 一致的 netlist 参数，验证 is_consistent=True。"""
    circuit = {
        "name": "two_dev",
        "devices": [
            {"name": "d1", "device_type": "strip_waveguide",
             "ports": [("in", 0, 0, "west"), ("out", 10, 0, "east")]},
            {"name": "d2", "device_type": "mmi_1x2",
             "ports": [("in", 0, 0, "west")]},
        ],
        "connections": [("d1", "out", "d2", "in")],
        "canvas_w": 100,
        "canvas_h": 100,
    }
    netlist = {
        "devices": [
            {"name": "d1", "device_type": "strip_waveguide"},
            {"name": "d2", "device_type": "mmi_1x2"},
        ],
        "connections": [["d1", "d2"]],
    }
    result = run_lvs(circuit, netlist)
    assert result["is_consistent"] is True
    assert result["n_mismatches"] == 0
    assert result["n_devices"] == 2
    assert result["n_connections"] == 1


def test_lvs_extra_device_mismatch():
    """提取网表多一个器件，is_consistent=False（应报告 extra_device）。"""
    circuit = _make_simple_circuit()
    netlist = {
        "devices": [
            {"name": "wg", "device_type": "strip_waveguide"},
            {"name": "extra_dev", "device_type": "phase_shifter"},
        ],
        "connections": [],
    }
    result = run_lvs(circuit, netlist)
    assert result["is_consistent"] is False
    assert result["n_mismatches"] > 0
    types = {m["type"] for m in result["mismatches"]}
    assert "extra_device" in types, (
        f"应报告 extra_device，实际: {types}"
    )


def test_lvs_simple_waveguide():
    """简单波导 LVS 验证（与任务验证脚本一致）。

    单个 strip_waveguide，自比对 is_consistent=True，n_devices=1。
    """
    circuit = _make_simple_circuit()
    result = run_lvs(circuit)
    assert result["is_consistent"] is True
    assert result["n_devices"] == 1, (
        f"n_devices 应=1，实际 {result['n_devices']}"
    )


def test_lvs_version():
    """验证 polaris-lvs 子模块版本号 5.0.0（与原 polaris-verify 一致）。"""
    assert polaris_lvs.__version__ == "5.0.0"
