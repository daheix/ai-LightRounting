"""netlist_adapter.py 测试（R01 步骤 8）。

测试内容:
1. sax 网表格式解析
2. simphony 网表格式解析
3. PoLaRIS 内部网表格式解析
4. 自动格式检测
5. 网表验证

来源:
- R01 路标: /workspace/docs/roundmap/R01.md
- SAX 网表格式: https://flaport.github.io/sax/
- Simphony 网表格式: https://simphonyphotonics.readthedocs.io/
"""

from __future__ import annotations

import pytest

from polaris.sim.netlist_adapter import (
    PolarNetlist,
    adapt_netlist,
    detect_format,
    validate_netlist,
)


class TestFormatDetection:
    """测试网表格式自动检测（R01 创新点 3）。"""

    def test_detect_sax_format(self):
        """检测 sax 格式（connections 键含逗号）。"""
        netlist = {
            "instances": {"wg1": "waveguide"},
            "connections": {"wg1,out": "wg2,in"},
            "ports": {"in": "wg1,in", "out": "wg2,out"},
        }
        assert detect_format(netlist) == "sax"

    def test_detect_simphony_format(self):
        """检测 simphony 格式（connections 为 list of [str, str]）。"""
        netlist = {
            "instances": {"wg1": "waveguide"},
            "connections": [["wg1.out", "wg2.in"]],
            "ports": {"in": "wg1.in", "out": "wg2.out"},
        }
        assert detect_format(netlist) == "simphony"

    def test_detect_polaris_format(self):
        """检测 PoLaRIS 格式（connections 为 list of (str, str)）。"""
        netlist = {
            "instances": {"wg1": "waveguide"},
            "connections": [("wg1.out", "wg2.in")],
            "ports": {"in": "wg1.in", "out": "wg2.out"},
        }
        assert detect_format(netlist) == "polaris"

    def test_detect_empty_connections(self):
        """空 connections 应识别为 polaris 格式。"""
        netlist = {"instances": {}, "connections": [], "ports": {}}
        assert detect_format(netlist) == "polaris"


class TestSaxNetlistParsing:
    """测试 sax 网表解析。"""

    def test_parse_sax_connections(self):
        """sax 逗号分隔应转为点号分隔。"""
        netlist = {
            "instances": {"wg1": "waveguide", "wg2": "waveguide"},
            "connections": {"wg1,out": "wg2,in"},
            "ports": {"in": "wg1,in", "out": "wg2,out"},
        }
        result = adapt_netlist(netlist)
        assert ("wg1.out", "wg2.in") in result.connections
        assert result.ports["in"] == "wg1.in"
        assert result.ports["out"] == "wg2.out"

    def test_parse_sax_instances(self):
        """sax instances 解析。"""
        netlist = {
            "instances": {"wg1": "waveguide", "dc1": "directional_coupler"},
            "connections": {},
            "ports": {},
        }
        result = adapt_netlist(netlist)
        assert result.instances["wg1"] == "waveguide"
        assert result.instances["dc1"] == "directional_coupler"


class TestSimphonyNetlistParsing:
    """测试 simphony 网表解析。"""

    def test_parse_simphony_connections(self):
        """simphony list 格式应转为 tuple。"""
        netlist = {
            "instances": {"wg1": "waveguide", "wg2": "waveguide"},
            "connections": [["wg1.out", "wg2.in"]],
            "ports": {"in": "wg1.in", "out": "wg2.out"},
        }
        result = adapt_netlist(netlist)
        assert ("wg1.out", "wg2.in") in result.connections

    def test_parse_simphony_invalid_connection_raises(self):
        """simphony connection 长度不为 2 应 raise ValueError。"""
        netlist = {
            "instances": {},
            "connections": [["a", "b", "c"]],
            "ports": {},
        }
        # 长度不为 2 的 list 会被检测阶段或解析阶段拒绝
        with pytest.raises(ValueError):
            adapt_netlist(netlist)


class TestPolarisNetlistParsing:
    """测试 PoLaRIS 内部网表解析。"""

    def test_parse_polaris_list_connections(self):
        """PoLaRIS list 格式解析。"""
        netlist = {
            "instances": {"wg1": "waveguide"},
            "connections": [("wg1.out", "wg2.in")],
            "ports": {"in": "wg1.in"},
        }
        result = adapt_netlist(netlist)
        assert ("wg1.out", "wg2.in") in result.connections

    def test_parse_polaris_dict_connections(self):
        """PoLaRIS dict 格式解析。"""
        netlist = {
            "instances": {"wg1": "waveguide"},
            "connections": {"wg1.out": "wg2.in"},
            "ports": {"in": "wg1.in"},
        }
        result = adapt_netlist(netlist)
        assert ("wg1.out", "wg2.in") in result.connections

    def test_to_dict(self):
        """PolarNetlist.to_dict 应返回兼容 CircuitSimulator 的格式。"""
        nl = PolarNetlist(
            instances={"wg1": "waveguide"},
            connections=[("wg1.out", "wg2.in")],
            ports={"in": "wg1.in"},
        )
        d = nl.to_dict()
        assert "instances" in d
        assert "connections" in d
        assert "ports" in d
        assert d["instances"]["wg1"] == "waveguide"


class TestNetlistValidation:
    """测试网表验证。"""

    def test_valid_netlist_passes(self):
        """有效网表应通过验证。"""
        nl = PolarNetlist(
            instances={"wg1": "waveguide", "wg2": "waveguide"},
            connections=[("wg1.out", "wg2.in")],
            ports={"in": "wg1.in", "out": "wg2.out"},
        )
        validate_netlist(nl)  # 不应 raise

    def test_invalid_connection_reference_raises(self):
        """连接引用不存在的实例应 raise ValueError。"""
        nl = PolarNetlist(
            instances={"wg1": "waveguide"},
            connections=[("wg1.out", "wg2.in")],  # wg2 不存在
            ports={},
        )
        with pytest.raises(ValueError, match="连接引用的实例不存在"):
            validate_netlist(nl)

    def test_invalid_port_reference_raises(self):
        """端口引用不存在的实例应 raise ValueError。"""
        nl = PolarNetlist(
            instances={"wg1": "waveguide"},
            connections=[],
            ports={"in": "wg2.in"},  # wg2 不存在
        )
        with pytest.raises(ValueError, match="端口引用的实例不存在"):
            validate_netlist(nl)

    def test_invalid_connection_format_raises(self):
        """连接引用格式错误应 raise ValueError。"""
        nl = PolarNetlist(
            instances={"wg1": "waveguide"},
            connections=[("invalid_format", "wg1.in")],  # 无点号
            ports={},
        )
        with pytest.raises(ValueError, match="连接引用格式错误"):
            validate_netlist(nl)


class TestCrossFormatCompatibility:
    """测试跨格式兼容性（R01 创新点 3）。"""

    def test_sax_to_polaris_roundtrip(self):
        """sax 格式转换为 PoLaRIS 后应保持语义一致。"""
        sax_netlist = {
            "instances": {"wg1": "waveguide", "wg2": "waveguide"},
            "connections": {"wg1,out": "wg2,in"},
            "ports": {"in": "wg1,in", "out": "wg2,out"},
        }
        polaris_nl = adapt_netlist(sax_netlist)
        # 验证转换结果
        assert polaris_nl.instances == {"wg1": "waveguide", "wg2": "waveguide"}
        assert ("wg1.out", "wg2.in") in polaris_nl.connections
        assert polaris_nl.ports == {"in": "wg1.in", "out": "wg2.out"}

    def test_simphony_to_polaris_roundtrip(self):
        """simphony 格式转换为 PoLaRIS 后应保持语义一致。"""
        simphony_netlist = {
            "instances": {"wg1": "waveguide", "wg2": "waveguide"},
            "connections": [["wg1.out", "wg2.in"]],
            "ports": {"in": "wg1.in", "out": "wg2.out"},
        }
        polaris_nl = adapt_netlist(simphony_netlist)
        assert ("wg1.out", "wg2.in") in polaris_nl.connections
        assert polaris_nl.ports["in"] == "wg1.in"

    def test_three_formats_same_semantics(self):
        """三种格式表达相同电路应产生相同 PoLaRIS 内部格式。"""
        # sax 格式
        sax = {
            "instances": {"a": "wg", "b": "wg"},
            "connections": {"a,out": "b,in"},
            "ports": {"in": "a,in", "out": "b,out"},
        }
        # simphony 格式
        simphony = {
            "instances": {"a": "wg", "b": "wg"},
            "connections": [["a.out", "b.in"]],
            "ports": {"in": "a.in", "out": "b.out"},
        }
        # PoLaRIS 格式
        polaris = {
            "instances": {"a": "wg", "b": "wg"},
            "connections": [("a.out", "b.in")],
            "ports": {"in": "a.in", "out": "b.out"},
        }
        r1 = adapt_netlist(sax)
        r2 = adapt_netlist(simphony)
        r3 = adapt_netlist(polaris)
        # 三者应产生相同的内部表示
        assert r1.instances == r2.instances == r3.instances
        assert r1.connections == r2.connections == r3.connections
        assert r1.ports == r2.ports == r3.ports
