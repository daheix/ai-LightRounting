"""SiEPIC JSON 网表解析器测试（R02 步骤 5）。

测试内容:
1. SiEPIC JSON 网表解析
2. 器件类型映射
3. 端口名映射
4. 全部 7 个基准网表解析验证

来源:
- R02 路标: /workspace/docs/roundmap/R02.md
- SiEPIC-Tools: https://github.com/SiEPIC/SiEPIC-Tools
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from polaris.sim.siepic_netlist import (
    SIEPIC_PORT_MAP,
    SIEPIC_TYPE_MAP,
    parse_siepic_json,
    parse_siepic_json_with_models,
)

# SiEPIC 网表基准目录
SIEPIC_DIR = Path(__file__).parent.parent / "data" / "benchmarks" / "siepic_netlists"


class TestSiepicNetlistParser:
    """SiEPIC JSON 网表解析器测试。"""

    def test_parse_mzi1(self):
        """解析 MZI1.json 网表。"""
        netlist = parse_siepic_json(SIEPIC_DIR / "MZI1.json")
        assert "instances" in netlist
        assert "connections" in netlist
        assert "ports" in netlist
        assert "meta" in netlist
        # MZI1 应包含 y_branch 和 grating_coupler
        assert len(netlist["instances"]) > 0
        # 验证元数据
        assert netlist["meta"]["name"] == "MZI1"
        assert netlist["meta"]["platform"] == "SOI"

    def test_parse_ring_resonator(self):
        """解析 RingResonator.json 网表。"""
        netlist = parse_siepic_json(SIEPIC_DIR / "RingResonator.json")
        assert len(netlist["instances"]) > 0
        # 应包含 ring_resonator 类型器件
        has_ring = any(
            model_name == "ring_resonator"
            for model_name in netlist["instances"].values()
        )
        assert has_ring, "RingResonator 网表应包含 ring_resonator 器件"

    def test_parse_simple_mzi(self):
        """解析 Simple_MZI.json 网表。"""
        netlist = parse_siepic_json(SIEPIC_DIR / "Simple_MZI.json")
        assert len(netlist["instances"]) > 0

    def test_parse_crossings(self):
        """解析 Crossings.json 网表。"""
        netlist = parse_siepic_json(SIEPIC_DIR / "Crossings.json")
        assert len(netlist["instances"]) > 0
        # 应包含 crossing 类型器件
        has_crossing = any(
            model_name in ("crossing", "ebeam_crossing4")
            for model_name in netlist["instances"].values()
        )
        assert has_crossing, "Crossings 网表应包含 crossing 器件"

    def test_parse_mzi_bdc(self):
        """解析 MZI_bdc_500microns.json 网表。"""
        netlist = parse_siepic_json(SIEPIC_DIR / "MZI_bdc_500microns.json")
        assert len(netlist["instances"]) > 0

    def test_parse_ring_series(self):
        """解析 Ring_series.json 网表。"""
        netlist = parse_siepic_json(SIEPIC_DIR / "Ring_series.json")
        assert len(netlist["instances"]) > 0

    def test_parse_mzi_adjustable_splitter(self):
        """解析 mzi_adjustable_splitter.json 网表。"""
        netlist = parse_siepic_json(SIEPIC_DIR / "mzi_adjustable_splitter.json")
        assert len(netlist["instances"]) > 0

    def test_parse_all_benchmark_netlists(self):
        """解析全部 7 个基准网表。"""
        netlist_files = list(SIEPIC_DIR.glob("*.json"))
        assert len(netlist_files) >= 7, f"应至少有 7 个网表文件，得到 {len(netlist_files)}"
        for netlist_file in netlist_files:
            netlist = parse_siepic_json(netlist_file)
            assert "instances" in netlist
            assert "connections" in netlist
            assert "meta" in netlist

    def test_nonexistent_file_raises(self):
        """不存在的文件应 raise FileNotFoundError。"""
        with pytest.raises(FileNotFoundError, match="SiEPIC 网表文件不存在"):
            parse_siepic_json(SIEPIC_DIR / "nonexistent.json")

    def test_invalid_json_raises(self, tmp_path):
        """无效 JSON 应 raise ValueError。"""
        invalid_file = tmp_path / "invalid.json"
        invalid_file.write_text("not a json")
        with pytest.raises(json.JSONDecodeError):
            parse_siepic_json(invalid_file)

    def test_missing_devices_field_raises(self, tmp_path):
        """缺少 devices 字段应 raise ValueError。"""
        invalid_file = tmp_path / "no_devices.json"
        invalid_file.write_text('{"name": "test"}')
        with pytest.raises(ValueError, match="缺少 'devices' 字段"):
            parse_siepic_json(invalid_file)


class TestSiepicTypeMap:
    """SiEPIC 器件类型映射测试。"""

    def test_type_map_contains_common_types(self):
        """类型映射表应包含常见 SiEPIC 器件类型。"""
        expected_types = [
            "waveguide",
            "y_branch",
            "directional_coupler",
            "ring_resonator",
            "grating_coupler",
            "grating_coupler_1d",
            "crossing",
            "ebeam_crossing4",
            "terminator",
            "taper",
        ]
        for dev_type in expected_types:
            assert dev_type in SIEPIC_TYPE_MAP, f"类型映射缺少 {dev_type}"

    def test_port_map_contains_common_types(self):
        """端口映射表应包含常见 SiEPIC 器件类型。"""
        expected_types = [
            "waveguide",
            "y_branch",
            "directional_coupler",
            "ring_resonator",
        ]
        for dev_type in expected_types:
            assert dev_type in SIEPIC_PORT_MAP, f"端口映射缺少 {dev_type}"


class TestParseWithModels:
    """parse_siepic_json_with_models 测试。"""

    def test_parse_with_models_mzi1(self):
        """解析 MZI1.json 并返回带模型函数的网表。"""
        netlist = parse_siepic_json_with_models(SIEPIC_DIR / "MZI1.json")
        assert "instances" in netlist
        # instances 应包含可调用的模型函数
        for name, model in netlist["instances"].items():
            assert callable(model), f"实例 {name} 的模型不是可调用对象"

    def test_parse_with_models_returns_meta(self):
        """parse_siepic_json_with_models 返回元数据。"""
        netlist = parse_siepic_json_with_models(SIEPIC_DIR / "MZI1.json")
        assert "meta" in netlist
        assert netlist["meta"]["name"] == "MZI1"
