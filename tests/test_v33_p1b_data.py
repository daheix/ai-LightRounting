"""P1-B R03 fall-back 修复回归测试（data 子包）。

测试 data 子包中所有 R03 fall-back 修复点：
- 每个 fall-back 修复点 raise 正确异常（R03: 失败即 raise）
- 正常功能不被破坏（回归测试）
- 合法 return None/[] 保留验证（查找失败/空输入等合法场景）

文献:
- Python 异常处理: https://docs.python.org/3/tutorial/errors.html
- PEP 8 异常设计: https://peps.python.org/pep-0008/#exception-handling
- pytest 异常测试: https://docs.pytest.org/en/stable/how-to/raise.html
- Real Python try/except: https://realpython.com/python-exceptions/
- Google Python 风格指南: https://google.github.io/styleguide/pyguide.html#exceptions
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from polaris.data._other_formats import (
    _extract_conn_pair,
    _extract_gdsfactory_conn_pair,
    load_gdsfactory_yaml,
    load_phido,
    load_picbench,
)
from polaris.data._pic_ir import (
    _infer_pic_ir_ports,
    _parse_pic_ir_endpoints,
    _parse_pic_ir_instances,
    _parse_pic_ir_nets,
    _parse_pic_ir_nets_list,
    load_pic_ir,
)
from polaris.data.benchmark_evaluator import (
    evaluate_benchmark,
    evaluate_congestion,
    evaluate_drv,
    evaluate_hpwl,
    evaluate_insertion_loss,
    evaluate_overlap,
    grid_placement,
)
from polaris.data.benchmark_history import HistoryTracker
from polaris.data.data_loader import (
    _load_file,
    load_apollo_onoc,
    load_apollo_ptc,
    load_directory,
    load_lidar_benchmark,
    load_tilos_ariane,
)
from polaris.data.specs import CircuitSpec, DeviceSpec
from polaris.data.variant_generator import _find_device_key

# =============================================================================
# 辅助函数
# =============================================================================


def _make_device(name: str, dtype: str = "mzi") -> DeviceSpec:
    """构造测试用 DeviceSpec（含标准 o1/o2 端口）。"""
    return DeviceSpec(
        name=name,
        device_type=dtype,
        width_um=10.0,
        height_um=10.0,
        ports=[("o1", 0.0, 5.0, "E"), ("o2", 10.0, 5.0, "W")],
    )


def _make_circuit(n: int = 2) -> CircuitSpec:
    """构造测试用 CircuitSpec（n 个器件链式连接）。"""
    devs = [_make_device(f"d{i}") for i in range(n)]
    conns = [(f"d{i}", "o2", f"d{i + 1}", "o1") for i in range(n - 1)]
    return CircuitSpec(
        name="test", devices=devs, connections=conns, canvas_w=500.0, canvas_h=500.0
    )


def _write_yaml(path: Path, data: object) -> Path:
    """写 YAML 文件并返回路径。"""
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    return path


# =============================================================================
# data_loader.py fall-back 修复测试
# =============================================================================


class TestDataLoaderFallback:
    """data_loader.py 的 R03 fall-back 修复测试。"""

    def test_load_directory_missing_dir_raises(self, tmp_path):
        """load_directory 目录不存在 raise FileNotFoundError（非静默返回空）。"""
        with pytest.raises(FileNotFoundError, match="数据目录不存在"):
            load_directory(tmp_path / "nonexistent")

    def test_load_directory_bad_file_raises(self, tmp_path):
        """load_directory 单文件解析失败 raise（R03: 不 continue 跳过）。"""
        (tmp_path / "bad.yaml").write_text("12345", encoding="utf-8")
        with pytest.raises(ValueError, match="数据文件加载失败"):
            load_directory(tmp_path)

    def test_load_file_auto_all_fail_raises(self, tmp_path):
        """_load_file auto 模式全部 loader 失败 raise 汇总错误。"""
        bad = tmp_path / "unknown.txt"
        bad.write_text("12345", encoding="utf-8")
        with pytest.raises(ValueError, match="所有加载器均失败"):
            _load_file(bad, "auto")

    def test_load_tilos_ariane_missing_path_raises(self, tmp_path):
        """load_tilos_ariane path 不存在 raise FileNotFoundError（非静默用默认）。"""
        with pytest.raises(FileNotFoundError, match="TILOS Ariane benchmark 文件不存在"):
            load_tilos_ariane(tmp_path / "nonexistent.yaml")

    def test_load_apollo_ptc_missing_path_raises(self, tmp_path):
        """load_apollo_ptc path 不存在 raise FileNotFoundError。"""
        with pytest.raises(FileNotFoundError, match="Apollo PTC benchmark 文件不存在"):
            load_apollo_ptc(tmp_path / "nonexistent.yaml")

    def test_load_apollo_onoc_missing_path_raises(self, tmp_path):
        """load_apollo_onoc path 不存在 raise FileNotFoundError。"""
        with pytest.raises(FileNotFoundError, match="Apollo oNoC benchmark 文件不存在"):
            load_apollo_onoc(tmp_path / "nonexistent.yaml")

    def test_load_lidar_benchmark_missing_path_raises(self, tmp_path):
        """load_lidar_benchmark path 不存在 raise FileNotFoundError。"""
        with pytest.raises(FileNotFoundError, match="LiDAR benchmark 文件不存在"):
            load_lidar_benchmark(tmp_path / "nonexistent.yaml")


# =============================================================================
# _other_formats.py fall-back 修复测试
# =============================================================================


class TestOtherFormatsFallback:
    """_other_formats.py 的 R03 fall-back 修复测试。"""

    def test_load_gdsfactory_non_dict_instance_raises(self, tmp_path):
        """load_gdsfactory_yaml 非 dict 实例 raise TypeError（不 continue）。"""
        fp = _write_yaml(tmp_path / "bad.yml", {"instances": {"bad": "not_a_dict"}})
        with pytest.raises(TypeError, match="GDSFactory 实例 'bad' 必须为 dict"):
            load_gdsfactory_yaml(fp)

    def test_extract_gdsfactory_conn_pair_unsupported_raises(self):
        """_extract_gdsfactory_conn_pair 不支持格式 raise TypeError（不返回 None）。"""
        with pytest.raises(TypeError, match="不支持的 GDSFactory 连接对象格式"):
            _extract_gdsfactory_conn_pair(12345)

    def test_parse_gdsfactory_routes_non_dict_route_raises(self, tmp_path):
        """_parse_gdsfactory_routes_field 非 dict route raise TypeError。"""
        fp = _write_yaml(tmp_path / "bad.yml", {"routes": {"r1": "not_a_dict"}})
        with pytest.raises(TypeError, match="GDSFactory route 'r1' 必须为 dict"):
            load_gdsfactory_yaml(fp)

    def test_parse_picbench_non_dict_instance_raises(self, tmp_path):
        """_parse_picbench_instances 非 dict 实例 raise TypeError。"""
        fp = _write_yaml(
            tmp_path / "bad.yml",
            {"data": {"netlist": {"instances": ["not_a_dict"]}}},
        )
        with pytest.raises(TypeError, match="PICBench 实例必须为 dict"):
            load_picbench(fp)

    def test_extract_conn_pair_unsupported_raises(self):
        """_extract_conn_pair 不支持格式 raise TypeError（不返回 None）。"""
        with pytest.raises(TypeError, match="不支持的连接对象格式"):
            _extract_conn_pair(12345)

    def test_extract_conn_pair_short_list_raises(self):
        """_extract_conn_pair list 长度不足 2 raise ValueError。"""
        with pytest.raises(ValueError, match="长度不足 2"):
            _extract_conn_pair(["only_one"])

    def test_parse_picbench_components_non_dict_raises(self, tmp_path):
        """_parse_picbench_components_section 非 dict 组件 raise TypeError。"""
        fp = _write_yaml(tmp_path / "bad.yml", {"components": ["not_a_dict"]})
        with pytest.raises(TypeError, match="PICBench 组件必须为 dict"):
            load_picbench(fp)

    def test_load_phido_non_dict_conn_raises(self, tmp_path):
        """load_phido 非 dict 连接 raise TypeError（不 continue）。"""
        fp = _write_yaml(
            tmp_path / "bad.yml",
            {"instances": [], "connections": ["not_a_dict"]},
        )
        with pytest.raises(TypeError, match="PhIDO 连接必须为 dict"):
            load_phido(fp)


# =============================================================================
# _pic_ir.py fall-back 修复测试
# =============================================================================


class TestPicIrFallback:
    """_pic_ir.py 的 R03 fall-back 修复测试。"""

    def test_parse_pic_ir_nets_invalid_type_raises(self):
        """_parse_pic_ir_nets 非 dict/list nets raise TypeError（不返回空列表）。"""
        with pytest.raises(TypeError, match="PIC IR nets 字段必须为 dict 或 list"):
            _parse_pic_ir_nets({"nets": "invalid_string"})

    def test_parse_pic_ir_endpoints_unsupported_raises(self):
        """_parse_pic_ir_endpoints 不支持格式 raise TypeError（不返回 None）。"""
        with pytest.raises(TypeError, match="PIC IR net endpoints 必须为"):
            _parse_pic_ir_endpoints(12345)

    def test_parse_pic_ir_endpoints_empty_ref_raises(self):
        """_parse_pic_ir_endpoints 端口引用解析失败 raise ValueError（不返回 None）。"""
        with pytest.raises(ValueError, match="端口引用解析失败"):
            _parse_pic_ir_endpoints(["", ""])

    def test_parse_pic_ir_nets_list_non_dict_raises(self):
        """_parse_pic_ir_nets_list 非 dict net raise TypeError（不 continue）。"""
        with pytest.raises(TypeError, match="PIC IR nets.*必须为 dict"):
            _parse_pic_ir_nets_list(["not_a_dict"])

    def test_parse_pic_ir_instances_non_dict_raises(self):
        """_parse_pic_ir_instances 非 dict 实例 raise TypeError（不 continue）。"""
        with pytest.raises(TypeError, match="PIC IR 实例 'bad' 必须为 dict"):
            _parse_pic_ir_instances({"bad": "not_a_dict"})


# =============================================================================
# benchmark_evaluator.py fall-back 修复测试
# =============================================================================


class TestBenchmarkEvaluatorFallback:
    """benchmark_evaluator.py 的 R03 fall-back 修复测试。"""

    def test_evaluate_hpwl_missing_placement_raises(self):
        """evaluate_hpwl 缺失 placement raise KeyError（不 continue 跳过）。"""
        circuit = _make_circuit(2)
        with pytest.raises(KeyError, match="HPWL 评估"):
            evaluate_hpwl(circuit, {"d0": (0.0, 0.0)})

    def test_evaluate_overlap_unknown_module_raises(self):
        """evaluate_overlap 模块不在 devices raise KeyError（不 continue）。"""
        circuit = _make_circuit(2)
        with pytest.raises(KeyError, match="重叠评估"):
            evaluate_overlap(circuit, {"d0": (0.0, 0.0), "unknown": (10.0, 10.0)})

    def test_evaluate_congestion_missing_placement_raises(self):
        """evaluate_congestion 缺失 placement raise KeyError（不 continue）。"""
        circuit = _make_circuit(2)
        with pytest.raises(KeyError, match="拥塞度评估"):
            evaluate_congestion(circuit, {"d0": (0.0, 0.0)})

    def test_evaluate_insertion_loss_missing_placement_raises(self):
        """evaluate_insertion_loss 缺失 placement raise KeyError（不 continue）。"""
        circuit = _make_circuit(2)
        with pytest.raises(KeyError, match="插入损耗评估"):
            evaluate_insertion_loss(circuit, {"d0": (0.0, 0.0)})

    def test_evaluate_drv_unknown_module_raises(self):
        """evaluate_drv 模块不在 devices raise KeyError（不 continue）。"""
        circuit = _make_circuit(2)
        with pytest.raises(KeyError, match="DRV 评估"):
            evaluate_drv(circuit, {"d0": (0.0, 0.0), "unknown": (10.0, 10.0)})


# =============================================================================
# gds_loader.py fall-back 修复测试（内部函数，无需 klayout）
# =============================================================================


class TestGdsLoaderFallback:
    """gds_loader.py 的 R03 fall-back 修复测试。"""

    def test_match_text_to_path_no_path_raises(self):
        """_match_text_to_path 无匹配 path raise ValueError（不 continue）。"""
        from polaris.data.gds_loader import _match_text_to_path

        pin_texts = [("pin1", 0.0, 0.0)]
        with pytest.raises(ValueError, match="未匹配到任何 PIN path"):
            _match_text_to_path(pin_texts, [])

    def test_build_connections_no_device_name_raises(self):
        """_build_connections 端口无 device_name raise ValueError（不 continue）。"""
        from polaris.data.gds_loader import _build_connections

        ports = [{"name": "pin1", "pos": (0.0, 0.0), "direction": "E"}]
        with pytest.raises(ValueError, match="未匹配到器件实例"):
            _build_connections(ports)


# =============================================================================
# 合法 return None/[] 保留验证（非 fall-back，不应改）
# =============================================================================


class TestLegalReturns:
    """合法 return None/[] 保留验证（查找失败/空输入等合法场景）。"""

    def test_infer_pic_ir_ports_unknown_returns_empty(self):
        """_infer_pic_ir_ports 未知器件返回空列表（合法查找失败，非 fall-back）。"""
        assert _infer_pic_ir_ports("unknown_device", 10.0, 10.0) == []

    def test_find_device_key_not_found_returns_none(self):
        """_find_device_key 未找到返回 None（合法查找失败，非 fall-back）。"""
        dev = DeviceSpec(name="x", device_type="nonexistent_type")
        assert _find_device_key(dev) is None

    def test_analyze_trend_no_history_returns_none(self):
        """analyze_trend 无记录返回 None（合法空数据，非 fall-back）。"""
        tracker = HistoryTracker()
        assert tracker.analyze_trend("nonexistent") is None

    def test_grid_placement_empty_returns_empty(self):
        """grid_placement 无器件返回空字典（合法空输入，非 fall-back）。"""
        circuit = CircuitSpec(name="empty", devices=[], connections=[])
        assert grid_placement(circuit) == {}


# =============================================================================
# 正常功能回归测试（确保修复不破坏正常功能）
# =============================================================================


class TestNormalRegression:
    """正常功能回归测试。"""

    def test_load_gdsfactory_yaml_normal(self, tmp_path):
        """load_gdsfactory_yaml 正常加载（回归）。"""
        fp = _write_yaml(
            tmp_path / "ok.yml",
            {"name": "test", "instances": {"mzi1": {"component": "mzi"}}},
        )
        circuit = load_gdsfactory_yaml(fp)
        assert circuit.name == "test"
        assert len(circuit.devices) == 1
        assert circuit.devices[0].device_type == "mzi"

    def test_load_picbench_normal(self, tmp_path):
        """load_picbench 正常加载（回归）。"""
        fp = _write_yaml(
            tmp_path / "pb.yml",
            {"name": "pb_test", "data": {"netlist": {"instances": {"d1": "mzi"}}}},
        )
        circuit = load_picbench(fp)
        assert circuit.name == "pb_test"
        assert len(circuit.devices) == 1

    def test_load_phido_normal(self, tmp_path):
        """load_phido 正常加载（回归）。"""
        fp = _write_yaml(
            tmp_path / "ph.yml",
            {"name": "phido_test", "instances": [{"name": "d1", "component": "mzi"}]},
        )
        circuit = load_phido(fp)
        assert circuit.name == "phido_test"
        assert len(circuit.devices) == 1

    def test_load_pic_ir_normal(self, tmp_path):
        """load_pic_ir 正常加载（回归）。"""
        fp = _write_yaml(
            tmp_path / "pic.yml",
            {
                "name": "pic_test",
                "instances": {"d1": {"component": "mzi", "width": 10.0, "height": 10.0}},
                "nets": {"net1": ["d1,o1", "d1,o2"]},
            },
        )
        circuit = load_pic_ir(fp)
        assert circuit.name == "pic_test"
        assert len(circuit.devices) == 1
        assert len(circuit.connections) == 1

    def test_evaluate_hpwl_normal(self):
        """evaluate_hpwl 正常计算（回归）。"""
        circuit = _make_circuit(2)
        hpwl = evaluate_hpwl(circuit, {"d0": (0.0, 0.0), "d1": (10.0, 20.0)})
        assert hpwl == 30.0

    def test_evaluate_overlap_normal(self):
        """evaluate_overlap 正常计算（回归）。"""
        circuit = _make_circuit(2)
        overlap = evaluate_overlap(circuit, {"d0": (0.0, 0.0), "d1": (100.0, 100.0)})
        assert overlap == 0

    def test_evaluate_benchmark_normal(self):
        """evaluate_benchmark 正常评估（回归）。"""
        circuit = _make_circuit(2)
        result = evaluate_benchmark(circuit, {"d0": (50.0, 50.0), "d1": (100.0, 100.0)})
        assert result.benchmark_name == "test"
        assert result.hpwl_um == 100.0

    def test_load_directory_normal(self, tmp_path):
        """load_directory 正常加载多个文件（回归）。"""
        _write_yaml(tmp_path / "c1.yml", {"name": "c1", "instances": {"d1": {"component": "mzi"}}})
        circuits = load_directory(tmp_path)
        assert len(circuits) == 1
        assert circuits[0].name == "c1"

    def test_load_tilos_ariane_default(self):
        """load_tilos_ariane 不传 path 返回默认拓扑（回归）。"""
        circuit = load_tilos_ariane()
        assert len(circuit.devices) > 0
