"""R08 路标测试：图同构 LVS 比对引擎。

测试 GraphIsomorphismLVSComparer、PhotonicsNetlist、EquivalenceHints、
verify_waveguide_length、verify_port_orientation、run_graph_lvs。
"""

from __future__ import annotations

import ast

import numpy as np
import pytest

from polaris.sim import graph_lvs as _glvs
from polaris.sim.graph_lvs import (
    EquivalenceHints,
    GraphIsomorphismLVSComparer,
    NetlistEdge,
    NetlistNode,
    PhotonicsLVSReport,
    PhotonicsNetlist,
    run_graph_lvs,
    verify_port_orientation,
    verify_waveguide_length,
)


def _make_matching_netlist() -> PhotonicsNetlist:
    """创建两个同构的网表用于测试。"""
    # 两个器件 + 一个端口，通过波导连接
    devices = [
        NetlistNode(node_id="d1", node_type="device", device_type="mmi1x2", params={"length": 10.0}),
        NetlistNode(node_id="d2", node_type="device", device_type="y_branch", params={"length": 5.0}),
    ]
    ports = [NetlistNode(node_id="p1", node_type="port", layer="WG")]
    edges = [
        NetlistEdge(source="d1", target="d2", edge_type="wire", length_um=100.0),
        NetlistEdge(source="d1", target="p1", edge_type="port"),
    ]
    return PhotonicsNetlist(devices=devices, edges=edges, ports=ports)


def _make_matching_netlist_2() -> PhotonicsNetlist:
    """创建第二个同构网表（节点 ID 不同但结构相同）。"""
    devices = [
        NetlistNode(node_id="d1", node_type="device", device_type="mmi1x2", params={"length": 10.0}),
        NetlistNode(node_id="d2", node_type="device", device_type="y_branch", params={"length": 5.0}),
    ]
    ports = [NetlistNode(node_id="p1", node_type="port", layer="WG")]
    edges = [
        NetlistEdge(source="d1", target="d2", edge_type="wire", length_um=100.0),
        NetlistEdge(source="d1", target="p1", edge_type="port"),
    ]
    return PhotonicsNetlist(devices=devices, edges=edges, ports=ports)


def _make_mismatched_netlist() -> PhotonicsNetlist:
    """创建不同构网表（多一个器件）。"""
    devices = [
        NetlistNode(node_id="d1", node_type="device", device_type="mmi1x2", params={"length": 10.0}),
        NetlistNode(node_id="d2", node_type="device", device_type="y_branch", params={"length": 5.0}),
        NetlistNode(node_id="d3", node_type="device", device_type="dc", params={"length": 8.0}),
    ]
    ports = [NetlistNode(node_id="p1", node_type="port", layer="WG")]
    edges = [
        NetlistEdge(source="d1", target="d2", edge_type="wire", length_um=100.0),
        NetlistEdge(source="d2", target="d3", edge_type="wire", length_um=50.0),
        NetlistEdge(source="d1", target="p1", edge_type="port"),
    ]
    return PhotonicsNetlist(devices=devices, edges=edges, ports=ports)


def _make_netlist_with(wire_length: float, d1_length: float = 10.0) -> PhotonicsNetlist:
    """构造与 _make_matching_netlist 同构、但波导长度/器件参数可调的网表。"""
    devices = [
        NetlistNode(node_id="d1", node_type="device", device_type="mmi1x2", params={"length": d1_length}),
        NetlistNode(node_id="d2", node_type="device", device_type="y_branch", params={"length": 5.0}),
    ]
    ports = [NetlistNode(node_id="p1", node_type="port", layer="WG")]
    edges = [
        NetlistEdge(source="d1", target="d2", edge_type="wire", length_um=wire_length),
        NetlistEdge(source="d1", target="p1", edge_type="port"),
    ]
    return PhotonicsNetlist(devices=devices, edges=edges, ports=ports)


def _make_orient_netlist(orientation: str) -> PhotonicsNetlist:
    """构造带端口朝向的单器件网表。"""
    return PhotonicsNetlist(
        devices=[NetlistNode(node_id="d1", node_type="device", device_type="mmi1x2")],
        ports=[
            NetlistNode(
                node_id="p1", node_type="port", params={"orientation": orientation}, layer="WG"
            )
        ],
        edges=[NetlistEdge(source="d1", target="p1", edge_type="port")],
    )


class _FakeExtracted:
    """鸭子类型 ExtractedNetlist（devices + connections）。"""

    def __init__(self) -> None:
        self.devices = ["d1", "d2"]
        self.connections = [("d1", "d2")]


class TestNetlistNode:
    def test_netlist_node_creation(self) -> None:
        node = NetlistNode(node_id="d1", node_type="device", device_type="mmi1x2",
                           params={"length": 10.0}, layer="WG")
        assert node.node_id == "d1"
        assert node.node_type == "device"
        assert node.device_type == "mmi1x2"
        assert node.params == {"length": 10.0}
        assert node.layer == "WG"

    def test_netlist_node_defaults(self) -> None:
        node = NetlistNode(node_id="p1", node_type="port")
        assert node.device_type == ""
        assert node.params == {}
        assert node.layer == ""


class TestNetlistEdge:
    def test_netlist_edge_creation(self) -> None:
        edge = NetlistEdge(source="d1", target="d2", edge_type="wire", length_um=100.0)
        assert edge.source == "d1"
        assert edge.target == "d2"
        assert edge.edge_type == "wire"
        assert edge.length_um == 100.0

    def test_netlist_edge_defaults(self) -> None:
        edge = NetlistEdge(source="d1", target="d2")
        assert edge.edge_type == "wire"
        assert edge.length_um == 0.0


class TestPhotonicsNetlist:
    def test_photonics_netlist_creation(self) -> None:
        netlist = _make_matching_netlist()
        assert len(netlist.devices) == 2
        assert len(netlist.edges) == 2
        assert len(netlist.ports) == 1

    def test_photonics_netlist_to_graph(self) -> None:
        graph = _make_matching_netlist().to_graph()
        assert graph.number_of_nodes() == 3
        assert graph.number_of_edges() == 2

    def test_photonics_netlist_from_extracted(self) -> None:
        netlist = PhotonicsNetlist.from_extracted_netlist(_FakeExtracted())
        assert len(netlist.devices) == 2
        assert len(netlist.edges) == 1
        assert netlist.devices[0].node_id == "d1"
        assert netlist.devices[0].node_type == "device"
        assert netlist.edges[0].source == "d1"
        assert netlist.edges[0].target == "d2"


class TestGraphIsomorphismLVSComparer:
    def test_comparer_init(self) -> None:
        comparer = GraphIsomorphismLVSComparer()
        assert comparer.tolerance_config == {}

    def test_comparer_init_with_config(self) -> None:
        config = {"mmi1x2": {"length": {"abs": 0.1, "rel": 0.0}}}
        comparer = GraphIsomorphismLVSComparer(tolerance_config=config)
        assert comparer.tolerance_config == config

    def test_build_graph(self) -> None:
        graph = GraphIsomorphismLVSComparer().build_graph(_make_matching_netlist())
        assert graph.number_of_nodes() == 3
        assert graph.number_of_edges() == 2

    def test_build_graph_empty_raises(self) -> None:
        empty = PhotonicsNetlist(devices=[], edges=[], ports=[])
        with pytest.raises(ValueError):
            GraphIsomorphismLVSComparer().build_graph(empty)

    def test_compare_matching(self) -> None:
        report = GraphIsomorphismLVSComparer().compare(_make_matching_netlist(), _make_matching_netlist_2())
        assert report.is_match
        assert report.mismatches == []

    def test_compare_not_matching(self) -> None:
        report = GraphIsomorphismLVSComparer().compare(_make_matching_netlist(), _make_mismatched_netlist())
        assert not report.is_match
        assert len(report.mismatches) == 1
        assert report.mismatches[0]["type"] == "graph_not_isomorphic"

    def test_compare_with_param_tolerance(self) -> None:
        ref = _make_matching_netlist()
        ext = _make_netlist_with(wire_length=100.0, d1_length=10.05)
        config = {"mmi1x2": {"length": {"abs": 0.1, "rel": 0.0}}}
        report = run_graph_lvs(ref, ext, tolerance_config=config)
        assert report.is_match

    def test_compare_waveguide_length_mismatch(self) -> None:
        ref = _make_matching_netlist()
        ext = _make_netlist_with(wire_length=105.0)
        report = run_graph_lvs(ref, ext)
        assert not report.is_match
        assert len(report.waveguide_length_mismatches) == 1
        assert np.isclose(report.waveguide_length_mismatches[0]["diff"], 5.0)


class TestEquivalenceHints:
    def test_same_nets(self) -> None:
        hints = EquivalenceHints()
        hints.same_nets("n1", "n2")
        assert ("n1", "n2") in hints._same_nets

    def test_same_circuits(self) -> None:
        hints = EquivalenceHints()
        hints.same_circuits("c1", "c2")
        assert ("c1", "c2") in hints._same_circuits

    def test_equivalent_pins(self) -> None:
        hints = EquivalenceHints()
        hints.equivalent_pins("mmi1x2", ["in", "out"])
        assert hints._equivalent_pins["mmi1x2"] == [["in", "out"]]

    def test_tolerance(self) -> None:
        hints = EquivalenceHints()
        hints.tolerance("mmi1x2", "length", abs_tol=0.1, rel_tol=0.05)
        assert hints.to_tolerance_config() == {"mmi1x2": {"length": {"abs": 0.1, "rel": 0.05}}}

    def test_max_res_min_caps(self) -> None:
        hints = EquivalenceHints()
        hints.max_res(1.5)
        hints.min_caps(0.5)
        assert hints._max_res == 1.5
        assert hints._min_caps == 0.5


class TestVerifyWaveguideLength:
    def test_verify_waveguide_length_match(self) -> None:
        ref = _make_matching_netlist()
        ext = _make_netlist_with(wire_length=100.5)
        mismatches = verify_waveguide_length(ref, ext, tolerance_um=1.0)
        assert mismatches == []

    def test_verify_waveguide_length_mismatch(self) -> None:
        ref = _make_matching_netlist()
        ext = _make_netlist_with(wire_length=105.0)
        mismatches = verify_waveguide_length(ref, ext, tolerance_um=1.0)
        assert len(mismatches) == 1
        assert np.isclose(mismatches[0]["diff"], 5.0)


class TestVerifyPortOrientation:
    def test_verify_port_orientation_match(self) -> None:
        mismatches = verify_port_orientation(_make_orient_netlist("E"), _make_orient_netlist("E"))
        assert mismatches == []

    def test_verify_port_orientation_mismatch(self) -> None:
        mismatches = verify_port_orientation(_make_orient_netlist("E"), _make_orient_netlist("N"))
        assert len(mismatches) == 1
        assert mismatches[0]["ref_orientation"] == "E"
        assert mismatches[0]["ext_orientation"] == "N"


class TestRunGraphLVS:
    def test_run_graph_lvs_match(self) -> None:
        report = run_graph_lvs(_make_matching_netlist(), _make_matching_netlist_2())
        assert report.is_match

    def test_run_graph_lvs_not_match(self) -> None:
        report = run_graph_lvs(_make_matching_netlist(), _make_mismatched_netlist())
        assert not report.is_match


class TestR08Integration:
    def test_no_fallback_in_graph_lvs(self) -> None:
        with open(_glvs.__file__, encoding="utf-8") as f:
            tree = ast.parse(f.read())
        for node in ast.walk(tree):
            if not isinstance(node, ast.ExceptHandler):
                continue
            body = node.body
            if len(body) == 1 and isinstance(body[0], ast.Pass):
                pytest.fail("graph_lvs.py 存在 except: pass fall-back")
            if len(body) == 1 and isinstance(body[0], ast.Return):
                value = body[0].value
                if value is None or (isinstance(value, ast.Constant) and value.value is None):
                    pytest.fail("graph_lvs.py 存在 except: return None fall-back")

    def test_all_public_api_exported(self) -> None:
        for name in _glvs.__all__:
            assert hasattr(_glvs, name), f"{name} 未在 graph_lvs 模块中导出"

    def test_photonics_lvs_report_is_dataclass(self) -> None:
        assert hasattr(PhotonicsLVSReport, "__dataclass_fields__")
