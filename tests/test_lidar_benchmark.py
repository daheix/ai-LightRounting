"""LiDAR Benchmark 量化评估脚本测试（阶段 D）。

测试 scripts/lidar_benchmark.py 的核心功能：
- benchmark 加载
- 布局/布线执行
- 指标计算（重叠数/HPWL/路由成功率）
- 报告生成

来源:
- LiDAR: Zhou et al., ISPD 2025, https://arxiv.org/abs/2410.01260
- PoLaRIS roadmap: docs/industry_alignment_roadmap.md 第 2.3.3 节
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import pytest  # noqa: E402
from lidar_benchmark import (  # noqa: E402
    LIDAR_BENCHMARK_DIR,
    TARGET_ROUTING_SUCCESS_RATE,
    BenchmarkMetrics,
    _compute_hpwl,
    _count_overlaps,
    _load_benchmark,
    _run_placement,
    _run_routing,
    generate_report,
    run_single_benchmark,
)


def test_load_benchmark_toy_example() -> None:
    """测试加载 toy_example benchmark。"""
    circuit = _load_benchmark("toy_example", "toy_example/toy_example.gp.yml")
    assert len(circuit.devices) == 6
    assert len(circuit.connections) == 2


def test_load_benchmark_not_found() -> None:
    """测试加载不存在的 benchmark 抛出 FileNotFoundError。"""
    with pytest.raises(FileNotFoundError):
        _load_benchmark("nonexistent", "nonexistent/nonexistent.yml")


def test_run_placement_returns_valid_dict() -> None:
    """测试布局返回有效 placements dict。"""
    circuit = _load_benchmark("toy_example", "toy_example/toy_example.gp.yml")
    from polaris.data.data_loader import circuit_spec_to_netlist_dict
    from polaris.engine.netlist import parse_netlist

    net = parse_netlist(circuit_spec_to_netlist_dict(circuit))
    placements = _run_placement(net, circuit)
    assert len(placements) == len(circuit.devices)
    for _dev_name, pos in placements.items():
        assert "x" in pos and "y" in pos
        assert "w" in pos and "h" in pos
        assert pos["x"] >= 0 and pos["y"] >= 0


def test_count_overlaps_no_overlap() -> None:
    """测试无重叠时返回 0。"""
    placements = {
        "a": {"x": 0, "y": 0, "w": 10, "h": 10},
        "b": {"x": 20, "y": 20, "w": 10, "h": 10},
    }
    assert _count_overlaps(placements) == 0


def test_count_overlaps_with_overlap() -> None:
    """测试有重叠时返回正确数量。"""
    placements = {
        "a": {"x": 0, "y": 0, "w": 10, "h": 10},
        "b": {"x": 5, "y": 5, "w": 10, "h": 10},  # 与 a 重叠
    }
    assert _count_overlaps(placements) == 1


def test_count_overlaps_three_devices() -> None:
    """测试三个器件两两重叠返回 3。"""
    placements = {
        "a": {"x": 0, "y": 0, "w": 10, "h": 10},
        "b": {"x": 5, "y": 5, "w": 10, "h": 10},  # 与 a 重叠
        "c": {"x": 7, "y": 7, "w": 10, "h": 10},  # 与 a、b 重叠
    }
    assert _count_overlaps(placements) == 3


def test_compute_hpwl() -> None:
    """测试 HPWL 计算。"""
    from polaris.data.specs import CircuitSpec, DeviceSpec

    circuit = CircuitSpec(
        name="test",
        canvas_w=1000.0,
        canvas_h=1000.0,
        devices=[
            DeviceSpec(name="a", device_type="wg", width_um=10, height_um=10),
            DeviceSpec(name="b", device_type="wg", width_um=10, height_um=10),
        ],
        connections=[("a", "o1", "b", "o1")],
    )
    placements = {
        "a": {"x": 0, "y": 0, "w": 10, "h": 10},
        "b": {"x": 100, "y": 100, "w": 10, "h": 10},
    }
    # 中心点: a=(5,5), b=(105,105), HPWL = |105-5| + |105-5| = 200
    hpwl = _compute_hpwl(circuit, placements)
    assert hpwl == pytest.approx(200.0, abs=0.01)


def test_run_routing_toy_example() -> None:
    """测试 toy_example 布线返回非空路径。"""
    circuit = _load_benchmark("toy_example", "toy_example/toy_example.gp.yml")
    from polaris.data.data_loader import circuit_spec_to_netlist_dict
    from polaris.engine.netlist import parse_netlist

    net = parse_netlist(circuit_spec_to_netlist_dict(circuit))
    placements = _run_placement(net, circuit)
    paths, total_length = _run_routing(circuit, placements)
    assert len(paths) > 0
    assert total_length > 0


def test_run_single_benchmark_toy_example() -> None:
    """测试运行 toy_example benchmark 返回完整指标。"""
    metrics = run_single_benchmark("toy_example", "toy_example/toy_example.gp.yml")
    assert metrics.name == "toy_example"
    assert metrics.n_devices == 6
    assert metrics.n_connections == 2
    assert metrics.n_routed == 2
    assert metrics.routing_success_rate == 1.0
    assert metrics.total_wire_length_um > 0
    assert metrics.runtime_seconds > 0


def test_run_single_benchmark_meets_routing_target() -> None:
    """测试 toy_example 路由成功率达标 (≥95%)。"""
    metrics = run_single_benchmark("toy_example", "toy_example/toy_example.gp.yml")
    assert metrics.routing_success_rate >= TARGET_ROUTING_SUCCESS_RATE


def test_generate_report_with_metrics() -> None:
    """测试报告生成包含正确字段。"""
    metrics_list = [
        BenchmarkMetrics(
            name="test1",
            n_devices=10,
            n_connections=5,
            n_routed=5,
            routing_success_rate=1.0,
            total_wire_length_um=100.0,
            n_drc_violations=0,
            runtime_seconds=1.0,
        ),
        BenchmarkMetrics(
            name="test2",
            n_devices=20,
            n_connections=10,
            n_routed=9,
            routing_success_rate=0.9,
            total_wire_length_um=200.0,
            n_drc_violations=1,
            runtime_seconds=2.0,
        ),
    ]
    report = generate_report(metrics_list)
    assert report.total_benchmarks == 2
    assert len(report.metrics) == 2
    assert "avg_routing_success_rate" in report.summary
    assert "total_drv" in report.summary
    assert report.summary["total_drv"] == 1


def test_generate_report_writes_file(tmp_path: Path) -> None:
    """测试报告写入 JSON 文件。"""
    metrics_list = [
        BenchmarkMetrics(name="test", n_devices=5, n_connections=2, n_routed=2),
    ]
    output_file = tmp_path / "report.json"
    generate_report(metrics_list, output_path=output_file)
    assert output_file.exists()
    data = json.loads(output_file.read_text(encoding="utf-8"))
    assert data["total_benchmarks"] == 1
    assert len(data["metrics"]) == 1


def test_generate_report_empty_list() -> None:
    """测试空指标列表生成报告不报错。"""
    report = generate_report([])
    assert report.total_benchmarks == 0
    assert report.summary == {}


def test_lidar_benchmark_dir_exists() -> None:
    """测试 LiDAR benchmark 目录存在。"""
    assert LIDAR_BENCHMARK_DIR.exists(), f"LiDAR benchmark 目录不存在: {LIDAR_BENCHMARK_DIR}"
