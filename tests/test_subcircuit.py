"""simphony 兼容 API 测试（R02 步骤 1）。

测试 Term/Connector/Subcircuit 类的功能和 simphony 风格 API。

来源:
- R02 路标: /workspace/docs/roundmap/R02.md
- simphony API: https://simphonyphotonics.readthedocs.io/
"""

from __future__ import annotations

import pytest

from polaris.sim.models import waveguide_s
from polaris.sim.subcircuit import Connector, Subcircuit, Term


class TestTerm:
    """Term 类测试。"""

    def test_term_creation(self):
        """Term 创建和属性。"""
        term = Term(name="in", instance="wg1")
        assert term.name == "in"
        assert term.instance == "wg1"

    def test_term_to_ref(self):
        """Term.to_ref() 返回 'instance.port' 格式。"""
        term = Term(name="out", instance="wg2")
        assert term.to_ref() == "wg2.out"


class TestConnector:
    """Connector 类测试。"""

    def test_connector_creation(self):
        """Connector 创建和属性。"""
        term1 = Term(name="out", instance="wg1")
        term2 = Term(name="in", instance="wg2")
        connector = Connector(term1, term2)
        assert connector.term1 is term1
        assert connector.term2 is term2

    def test_connector_to_connection(self):
        """Connector.to_connection() 返回连接元组。"""
        term1 = Term(name="out", instance="wg1")
        term2 = Term(name="in", instance="wg2")
        connector = Connector(term1, term2)
        assert connector.to_connection() == ("wg1.out", "wg2.in")


class TestSubcircuit:
    """Subcircuit 类测试。"""

    def test_add_component(self):
        """添加组件。"""
        sub = Subcircuit("mzi")
        sub.add_component(waveguide_s, "wg1")
        assert "wg1" in sub.components
        assert sub.components["wg1"] is waveguide_s

    def test_add_duplicate_component_raises(self):
        """重复添加同名实例应 raise ValueError。"""
        sub = Subcircuit("mzi")
        sub.add_component(waveguide_s, "wg1")
        with pytest.raises(ValueError, match="实例名 'wg1' 已存在"):
            sub.add_component(waveguide_s, "wg1")

    def test_connect(self):
        """连接两个实例端口。"""
        sub = Subcircuit("mzi")
        sub.add_component(waveguide_s, "wg1")
        sub.add_component(waveguide_s, "wg2")
        sub.connect("wg1", "out", "wg2", "in")
        assert len(sub.connections) == 1
        conn = sub.connections[0]
        assert conn.to_connection() == ("wg1.out", "wg2.in")

    def test_connect_nonexistent_instance_raises(self):
        """连接不存在的实例应 raise ValueError。"""
        sub = Subcircuit("mzi")
        sub.add_component(waveguide_s, "wg1")
        with pytest.raises(ValueError, match="实例 'wg2' 不存在"):
            sub.connect("wg1", "out", "wg2", "in")

    def test_add_terminal(self):
        """添加外部端子。"""
        sub = Subcircuit("mzi")
        sub.add_component(waveguide_s, "wg1")
        sub.add_terminal("in", "wg1", "in")
        assert "in" in sub.terminals
        assert sub.terminals["in"].name == "in"
        assert sub.terminals["in"].instance == "wg1"

    def test_add_duplicate_terminal_raises(self):
        """重复添加同名端子应 raise ValueError。"""
        sub = Subcircuit("mzi")
        sub.add_component(waveguide_s, "wg1")
        sub.add_terminal("in", "wg1", "in")
        with pytest.raises(ValueError, match="端子名 'in' 已存在"):
            sub.add_terminal("in", "wg1", "out")

    def test_add_terminal_nonexistent_instance_raises(self):
        """为不存在的实例添加端子应 raise ValueError。"""
        sub = Subcircuit("mzi")
        with pytest.raises(ValueError, match="实例 'wg1' 不存在"):
            sub.add_terminal("in", "wg1", "in")

    def test_to_netlist(self):
        """转换为网表格式。"""
        sub = Subcircuit("mzi")
        sub.add_component(waveguide_s, "wg1")
        sub.add_component(waveguide_s, "wg2")
        sub.connect("wg1", "out", "wg2", "in")
        sub.add_terminal("in", "wg1", "in")
        sub.add_terminal("out", "wg2", "out")
        netlist = sub.to_netlist()
        assert "instances" in netlist
        assert "connections" in netlist
        assert "ports" in netlist
        assert netlist["instances"]["wg1"] == "waveguide_s"
        assert netlist["instances"]["wg2"] == "waveguide_s"
        assert ("wg1.out", "wg2.in") in netlist["connections"]
        assert netlist["ports"]["in"] == "wg1.in"
        assert netlist["ports"]["out"] == "wg2.out"

    def test_to_sax_netlist(self):
        """转换为 SAX 网表（含模型函数）。"""
        sub = Subcircuit("mzi")
        sub.add_component(waveguide_s, "wg1")
        sub.add_component(waveguide_s, "wg2")
        sub.connect("wg1", "out", "wg2", "in")
        sub.add_terminal("in", "wg1", "in")
        sub.add_terminal("out", "wg2", "out")
        netlist = sub.to_sax_netlist()
        assert netlist["instances"]["wg1"] is waveguide_s
        assert netlist["instances"]["wg2"] is waveguide_s
        assert ("wg1.out", "wg2.in") in netlist["connections"]
        assert netlist["ports"]["in"] == "wg1.in"
        assert netlist["ports"]["out"] == "wg2.out"

    def test_mzi_circuit_construction(self):
        """构建 MZI 电路（simphony 风格）。"""
        sub = Subcircuit("mzi")
        # 两个波导作为 MZI 两臂
        sub.add_component(waveguide_s, "wg1")
        sub.add_component(waveguide_s, "wg2")
        # 连接两臂
        sub.connect("wg1", "out", "wg2", "in")
        # 外部端子
        sub.add_terminal("in", "wg1", "in")
        sub.add_terminal("out", "wg2", "out")
        netlist = sub.to_netlist()
        # 验证网表结构
        assert len(netlist["instances"]) == 2
        assert len(netlist["connections"]) == 1
        assert len(netlist["ports"]) == 2

    def test_simphony_api_compatibility(self):
        """simphony 风格 API 兼容性测试。

        参考 simphony 文档示例:
        sub = Subcircuit("mzi")
        sub.add_component(waveguide_s, "wg1")
        sub.add_component(waveguide_s, "wg2")
        sub.connect("wg1", "out", "wg2", "in")
        sub.add_terminal("in", "wg1", "in")
        sub.add_terminal("out", "wg2", "out")
        """
        sub = Subcircuit("mzi")
        # 按照任务描述中的 simphony 风格 API 构建
        sub.add_component(waveguide_s, "wg1")
        sub.add_component(waveguide_s, "wg2")
        sub.connect("wg1", "out", "wg2", "in")
        sub.add_terminal("in", "wg1", "in")
        sub.add_terminal("out", "wg2", "out")
        # 验证可转换为网表
        netlist = sub.to_netlist()
        assert netlist is not None
        assert isinstance(netlist, dict)
