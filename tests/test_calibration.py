"""仿真校准模块测试（Task P1）。

覆盖 ``src/polaris/sim/calibration.py`` 的：
- CalibrationConfig / CalibrationItem / CalibrationResult 数据类
- calibrate 主入口（目录不存在 / 空目录 / 多种基准格式）
- _estimate_loss（PICBench / LiDAR / gdsfactory 三种格式）
- _instance_loss（波导长度损耗 + 器件类型查表）
- _cell_loss（关键字匹配）
- 容差检查（pass/fail）

来源:
- LiDAR ISPD'25: https://dl.acm.org/doi/pdf/10.1145/3698364.3705355
- PICBench: https://github.com/PICDA/PICBench
- SiEPIC PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
"""

from __future__ import annotations

import json

import pytest

from polaris.sim.calibration import (
    CalibrationConfig,
    CalibrationItem,
    CalibrationResult,
    _cell_loss,
    _estimate_loss,
    _instance_loss,
    calibrate,
)

# ---------------------------------------------------------------------------
# 数据类
# ---------------------------------------------------------------------------


def test_calibration_config_defaults():
    cfg = CalibrationConfig()
    assert cfg.loss_tolerance_db == 0.5
    assert cfg.benchmark_dir == "data/benchmarks"
    assert cfg.max_calibration_rounds == 5


def test_calibration_item_defaults():
    item = CalibrationItem()
    assert item.circuit_name == ""
    assert item.reference_loss_db == 0.0
    assert item.simulated_loss_db == 0.0
    assert item.error_db == 0.0
    assert item.passed is False


def test_calibration_result_defaults():
    r = CalibrationResult()
    assert r.items == []
    assert r.total_items == 0
    assert r.passed_items == 0
    assert r.max_error_db == 0.0
    assert r.mean_error_db == 0.0
    assert r.all_passed is False


# ---------------------------------------------------------------------------
# calibrate 主入口
# ---------------------------------------------------------------------------


def test_calibrate_nonexistent_dir(tmp_path):
    """目录不存在时应返回空结果且不抛异常。"""
    cfg = CalibrationConfig(benchmark_dir=str(tmp_path / "nonexistent"))
    result = calibrate(cfg)
    assert result.total_items == 0
    assert result.all_passed is False


def test_calibrate_empty_dir(tmp_path):
    """空目录应返回空结果。"""
    cfg = CalibrationConfig(benchmark_dir=str(tmp_path))
    result = calibrate(cfg)
    assert result.total_items == 0


def test_calibrate_skips_index_files(tmp_path):
    """index.json / variant_stats.json / dataset_stats.json 应被跳过。"""
    for name in ("index.json", "variant_stats.json", "dataset_stats.json"):
        (tmp_path / name).write_text(json.dumps({"name": name}), encoding="utf-8")
    cfg = CalibrationConfig(benchmark_dir=str(tmp_path))
    result = calibrate(cfg)
    assert result.total_items == 0


def test_calibrate_picbench_format(tmp_path):
    """PICBench 格式：instances 为 dict，含 component/settings.length。"""
    circuit = {
        "name": "mzi_test",
        "reference_loss_db": 0.5,
        "instances": {
            "wg1": {"component": "waveguide", "settings": {"length": 1000.0}},
            "mzi1": {"component": "mzi", "settings": {}},
        },
    }
    (tmp_path / "mzi.json").write_text(json.dumps(circuit), encoding="utf-8")
    cfg = CalibrationConfig(benchmark_dir=str(tmp_path), loss_tolerance_db=0.5)
    result = calibrate(cfg)
    assert result.total_items == 1
    item = result.items[0]
    assert item.circuit_name == "mzi_test"
    assert item.reference_loss_db == 0.5
    # wg1: 2.0/1e4 * 1000 = 0.2 dB; mzi1: 0.5 dB → 总 0.7 dB
    assert item.simulated_loss_db == pytest.approx(0.7, rel=1e-4)


def test_calibrate_lidar_format(tmp_path):
    """LiDAR 格式：instances 为 dict，含 component/settings。"""
    circuit = {
        "name": "lidar_circuit",
        "reference_loss_db": 0.3,
        "instances": {
            "gc1": {"component": "grating_coupler", "settings": {}},
            "yb1": {"component": "y_branch", "settings": {}},
        },
    }
    (tmp_path / "lidar.json").write_text(json.dumps(circuit), encoding="utf-8")
    cfg = CalibrationConfig(benchmark_dir=str(tmp_path), loss_tolerance_db=1.0)
    result = calibrate(cfg)
    assert result.total_items == 1
    item = result.items[0]
    # gc: 2.5 + yb: 0.3 = 2.8 dB
    assert item.simulated_loss_db == pytest.approx(2.8, rel=1e-4)
    assert item.reference_loss_db == 0.3


def test_calibrate_gdsfactory_list_format(tmp_path):
    """gdsfactory 格式：instances 为 list。"""
    circuit = {
        "name": "gds_circuit",
        "reference_loss_db": 0.4,
        "instances": [
            {"component": "mmi", "settings": {}},
            {"component": "dc", "settings": {}},
        ],
    }
    (tmp_path / "gds.json").write_text(json.dumps(circuit), encoding="utf-8")
    cfg = CalibrationConfig(benchmark_dir=str(tmp_path), loss_tolerance_db=1.0)
    result = calibrate(cfg)
    assert result.total_items == 1
    item = result.items[0]
    # mmi: 0.3 + dc: 0.2 = 0.5 dB
    assert item.simulated_loss_db == pytest.approx(0.5, rel=1e-4)


def test_calibrate_total_loss_db_fallback(tmp_path):
    """无 reference_loss_db 时应回退到 total_loss_db。"""
    circuit = {
        "name": "fallback_test",
        "total_loss_db": 1.0,
        "instances": {"wg1": {"component": "waveguide", "settings": {"length": 500.0}}},
    }
    (tmp_path / "fallback.json").write_text(json.dumps(circuit), encoding="utf-8")
    cfg = CalibrationConfig(benchmark_dir=str(tmp_path), loss_tolerance_db=0.5)
    result = calibrate(cfg)
    item = result.items[0]
    assert item.reference_loss_db == 1.0
    # wg1: 2.0/1e4 * 500 = 0.1 dB
    assert item.simulated_loss_db == pytest.approx(0.1, rel=1e-4)


def test_calibrate_pass_tolerance(tmp_path):
    """误差在容差内应 passed=True。"""
    circuit = {
        "name": "pass_circuit",
        "reference_loss_db": 0.5,
        "instances": {"wg1": {"component": "waveguide", "settings": {"length": 2500.0}}},
    }
    (tmp_path / "pass.json").write_text(json.dumps(circuit), encoding="utf-8")
    # wg1: 2.0/1e4 * 2500 = 0.5 dB, error=0
    cfg = CalibrationConfig(benchmark_dir=str(tmp_path), loss_tolerance_db=0.5)
    result = calibrate(cfg)
    assert result.items[0].passed is True
    assert result.all_passed is True
    assert result.passed_items == 1


def test_calibrate_fail_tolerance(tmp_path):
    """误差超出容差应 passed=False。"""
    circuit = {
        "name": "fail_circuit",
        "reference_loss_db": 0.0,
        "instances": {"gc1": {"component": "grating_coupler", "settings": {}}},
    }
    (tmp_path / "fail.json").write_text(json.dumps(circuit), encoding="utf-8")
    # gc: 2.5 dB, error=2.5 > 0.5
    cfg = CalibrationConfig(benchmark_dir=str(tmp_path), loss_tolerance_db=0.5)
    result = calibrate(cfg)
    assert result.items[0].passed is False
    assert result.all_passed is False
    assert result.passed_items == 0


def test_calibrate_multiple_circuits_summary(tmp_path):
    """多个电路应正确汇总 total/passed/max_error/mean_error。"""
    # 电路 1: 通过
    c1 = {
        "name": "c1",
        "reference_loss_db": 0.5,
        "instances": {"wg1": {"component": "waveguide", "settings": {"length": 2500.0}}},
    }
    # 电路 2: 失败
    c2 = {
        "name": "c2",
        "reference_loss_db": 0.0,
        "instances": {"gc1": {"component": "grating_coupler", "settings": {}}},
    }
    (tmp_path / "c1.json").write_text(json.dumps(c1), encoding="utf-8")
    (tmp_path / "c2.json").write_text(json.dumps(c2), encoding="utf-8")
    cfg = CalibrationConfig(benchmark_dir=str(tmp_path), loss_tolerance_db=0.5)
    result = calibrate(cfg)
    assert result.total_items == 2
    assert result.passed_items == 1
    assert result.all_passed is False
    # c1 error=0, c2 error=2.5 → max=2.5, mean=1.25
    assert result.max_error_db == pytest.approx(2.5, rel=1e-4)
    assert result.mean_error_db == pytest.approx(1.25, rel=1e-4)


def test_calibrate_invalid_json_skipped(tmp_path):
    """无效 JSON 文件应被跳过。"""
    (tmp_path / "bad.json").write_text("not a json", encoding="utf-8")
    cfg = CalibrationConfig(benchmark_dir=str(tmp_path))
    result = calibrate(cfg)
    assert result.total_items == 0


def test_calibrate_uses_filename_stem_when_no_name(tmp_path):
    """无 name 字段时使用文件名 stem。"""
    circuit = {
        "reference_loss_db": 0.0,
        "instances": {},
    }
    (tmp_path / "no_name_circuit.json").write_text(json.dumps(circuit), encoding="utf-8")
    cfg = CalibrationConfig(benchmark_dir=str(tmp_path))
    result = calibrate(cfg)
    assert result.total_items == 1
    assert result.items[0].circuit_name == "no_name_circuit"


# ---------------------------------------------------------------------------
# _estimate_loss / _instance_loss / _cell_loss
# ---------------------------------------------------------------------------


def test_estimate_loss_no_instances():
    """无 instances 字段时应返回 0。"""
    assert _estimate_loss({"name": "empty"}) == 0.0


def test_estimate_loss_nested_netlist():
    """data.netlist.instances 嵌套结构应能解析。"""
    data = {
        "data": {
            "netlist": {
                "instances": {"wg1": {"component": "waveguide", "settings": {"length": 1000.0}}},
            }
        }
    }
    loss = _estimate_loss(data)
    assert loss == pytest.approx(0.2, rel=1e-4)


def test_estimate_loss_dict_format():
    """dict 格式 instances。"""
    data = {
        "instances": {
            "wg1": {"component": "waveguide", "settings": {"length": 5000.0}},
        }
    }
    # 2.0/1e4 * 5000 = 1.0 dB
    assert _estimate_loss(data) == pytest.approx(1.0, rel=1e-4)


def test_estimate_loss_list_format():
    """list 格式 instances。"""
    data = {
        "instances": [
            {"component": "mmi", "settings": {}},
            {"component": "dc", "settings": {}},
        ]
    }
    # mmi: 0.3 + dc: 0.2 = 0.5
    assert _estimate_loss(data) == pytest.approx(0.5, rel=1e-4)


def test_instance_loss_string_cell():
    """instance 为字符串时应按器件类型查表。"""
    assert _instance_loss("grating_coupler") == 2.5
    assert _instance_loss("mmi1x2") == 0.3


def test_instance_loss_with_length():
    """含 length 参数的波导应按长度计算损耗。"""
    inst = {"component": "waveguide", "settings": {"length": 1000.0}}
    # 2.0/1e4 * 1000 = 0.2
    assert _instance_loss(inst) == pytest.approx(0.2, rel=1e-4)


def test_instance_loss_zero_length():
    """length=0 时应回退到器件类型查表。"""
    inst = {"component": "waveguide", "settings": {"length": 0}}
    # length=0 不满足 length > 0，回退到 _cell_loss("waveguide")=0.1
    assert _instance_loss(inst) == 0.1


def test_instance_loss_negative_length():
    """length<0 时应回退到器件类型查表。"""
    inst = {"component": "waveguide", "settings": {"length": -100.0}}
    assert _instance_loss(inst) == 0.1


def test_instance_loss_non_dict():
    """非 dict/str 实例应返回 0。"""
    assert _instance_loss(42) == 0.0
    assert _instance_loss(None) == 0.0


def test_cell_loss_keywords():
    """器件类型关键字匹配。"""
    assert _cell_loss("waveguide") == 0.1
    assert _cell_loss("wg") == 0.1
    assert _cell_loss("mzi") == 0.5
    assert _cell_loss("ring") == 0.3
    assert _cell_loss("mrr") == 0.3
    assert _cell_loss("dc") == 0.2
    assert _cell_loss("coupler") == 0.2
    assert _cell_loss("mmi") == 0.3
    assert _cell_loss("gc") == 2.5
    assert _cell_loss("grating_coupler") == 2.5
    assert _cell_loss("yb") == 0.3
    assert _cell_loss("y_branch") == 0.3
    assert _cell_loss("crossing") == 0.05
    assert _cell_loss("straight_heater") == 0.2
    assert _cell_loss("phase_shifter") == 0.2
    assert _cell_loss("heater") == 0.2
    assert _cell_loss("rectangle") == 0.0


def test_cell_loss_case_insensitive():
    """器件类型匹配应大小写不敏感。"""
    assert _cell_loss("Waveguide") == 0.1
    assert _cell_loss("MMI") == 0.3
    assert _cell_loss("GC") == 2.5


def test_cell_loss_unknown_default():
    """未知器件类型应返回默认损耗 0.2。"""
    assert _cell_loss("unknown_device") == 0.2
    assert _cell_loss("") == 0.2


def test_cell_loss_non_string():
    """非字符串输入应返回默认损耗。"""
    assert _cell_loss(None) == 0.2
    assert _cell_loss(42) == 0.2


# ---------------------------------------------------------------------------
# 波导损耗系数
# ---------------------------------------------------------------------------


def test_waveguide_loss_per_um():
    """波导损耗系数应为 2.0 dB/cm = 2.0e-4 dB/μm。"""
    # 10000 μm = 1 cm → 2.0 dB
    inst = {"component": "waveguide", "settings": {"length": 10000.0}}
    loss = _instance_loss(inst)
    assert loss == pytest.approx(2.0, rel=1e-4)
