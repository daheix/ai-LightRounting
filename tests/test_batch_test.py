"""PoLaRIS 批量测试脚本冒烟测试（Task 13）。

测试 batch_test_1000_circuits.py 的核心功能：
1. 电路索引文件存在且包含 1200 个电路
2. 批量测试脚本的 test_single_circuit 函数可正常执行
3. 取前 3 个电路执行测试，验证返回 TestResult 对象

规则 14.1：禁止 fall-back，测试失败必须告警。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# 将项目根目录加入 sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from scripts.batch_test_1000_circuits import (
    GENERATED_DIR,
    TestResult,
    load_circuit_index,
    test_single_circuit,
)

# =============================================================================
# 测试 1: 电路索引文件存在且包含 1200 个电路
# =============================================================================


def test_circuit_index_exists() -> None:
    """电路索引文件 data/benchmarks/generated/index.json 应存在。"""
    index_path = GENERATED_DIR / "index.json"
    assert index_path.exists(), f"电路索引文件不存在: {index_path}"


def test_circuit_index_contains_1200_circuits() -> None:
    """电路索引应包含 1200 个电路（15 拓扑 × 5 规模 × 4 平台 × 4 种子）。"""
    circuits = load_circuit_index()
    assert len(circuits) == 1200, (
        f"电路索引应包含 1200 个电路，实际 {len(circuits)}"
    )


def test_circuit_index_entries_have_required_fields() -> None:
    """电路索引条目应包含必要字段（path/topology/scale/platform/name）。"""
    circuits = load_circuit_index()
    required_fields = {"path", "topology", "scale", "platform", "name"}
    for i, entry in enumerate(circuits[:10]):  # 抽样前 10 个
        missing = required_fields - set(entry.keys())
        assert not missing, (
            f"索引条目 {i} 缺少字段: {missing}，条目: {entry}"
        )


def test_circuit_index_covers_15_topologies() -> None:
    """电路索引应覆盖 15 种拓扑。"""
    circuits = load_circuit_index()
    topologies = {c["topology"] for c in circuits}
    assert len(topologies) == 15, (
        f"应覆盖 15 种拓扑，实际 {len(topologies)}: {sorted(topologies)}"
    )


def test_circuit_index_covers_5_scales() -> None:
    """电路索引应覆盖 5 种规模（XS/S/M/L/XL）。"""
    circuits = load_circuit_index()
    scales = {c["scale"] for c in circuits}
    expected_scales = {"XS", "S", "M", "L", "XL"}
    assert scales == expected_scales, (
        f"应覆盖 5 种规模 {expected_scales}，实际 {scales}"
    )


def test_circuit_index_covers_4_platforms() -> None:
    """电路索引应覆盖 4 种平台（SOI/SiN/InP/LNOI）。"""
    circuits = load_circuit_index()
    platforms = {c["platform"] for c in circuits}
    expected_platforms = {"SOI", "SiN", "InP", "LNOI"}
    assert platforms == expected_platforms, (
        f"应覆盖 4 种平台 {expected_platforms}，实际 {platforms}"
    )


# =============================================================================
# 测试 2: 批量测试脚本的 test_single_circuit 函数可正常执行
# =============================================================================


def test_test_single_circuit_returns_test_result() -> None:
    """test_single_circuit 应返回 TestResult 对象。"""
    circuits = load_circuit_index()
    # 取第一个电路（mzi_array/XS/SOI/seed=42）
    entry = circuits[0]
    result = test_single_circuit(entry)
    assert isinstance(result, TestResult), (
        f"test_single_circuit 应返回 TestResult，实际 {type(result)}"
    )


def test_test_single_circuit_result_fields_populated() -> None:
    """TestResult 对象的必要字段应被填充。"""
    circuits = load_circuit_index()
    entry = circuits[0]
    result = test_single_circuit(entry)

    # 验证必要字段非默认空值
    assert result.name == entry["name"], "TestResult.name 应与索引条目一致"
    assert result.topology == entry["topology"], "TestResult.topology 应与索引条目一致"
    assert result.scale == entry["scale"], "TestResult.scale 应与索引条目一致"
    assert result.platform == entry["platform"], "TestResult.platform 应与索引条目一致"
    assert result.elapsed_sec >= 0.0, "TestResult.elapsed_sec 应 ≥ 0"


# =============================================================================
# 测试 3: 取前 3 个电路执行测试，验证返回 TestResult 对象
# =============================================================================


@pytest.mark.parametrize("idx", [0, 1, 2])
def test_first_three_circuits_return_test_result(idx: int) -> None:
    """前 3 个电路执行测试应返回 TestResult 对象。"""
    circuits = load_circuit_index()
    assert len(circuits) >= 3, "电路索引应至少有 3 个电路"

    entry = circuits[idx]
    result = test_single_circuit(entry)
    assert isinstance(result, TestResult), (
        f"电路 {idx} ({entry['name']}) 应返回 TestResult，"
        f"实际 {type(result)}"
    )
    # 验证 name 字段一致
    assert result.name == entry["name"], (
        f"电路 {idx}: TestResult.name={result.name} 与索引 name={entry['name']} 不一致"
    )


def test_first_three_circuits_circuit_files_exist() -> None:
    """前 3 个电路的 JSON 文件应实际存在。"""
    circuits = load_circuit_index()
    for i, entry in enumerate(circuits[:3]):
        circuit_path = GENERATED_DIR / entry["path"]
        assert circuit_path.exists(), (
            f"电路 {i} 文件不存在: {circuit_path}"
        )
        # 验证文件可被 JSON 解析
        data = json.loads(circuit_path.read_text(encoding="utf-8"))
        assert "name" in data, f"电路 {i} JSON 缺少 name 字段"
        assert "devices" in data, f"电路 {i} JSON 缺少 devices 字段"
        assert "connections" in data, f"电路 {i} JSON 缺少 connections 字段"
