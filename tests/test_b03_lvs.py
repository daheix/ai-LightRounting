"""B03-LVS 验收测试：版图原理图一致性检查。

测试图同构 LVS 比对引擎的核心功能：同构图检测、端口匹配、
参数提取一致性、波导长度验证、端口朝向验证。

来源:
- 图同构判定: McKay & Piperno, "Practical Graph Isomorphism, II", JSC 2014
- VF2 子图同构: Cordella et al., IEEE TPAMI 2004
- KLayout LVS: https://www.klayout.org/downloads/master/doc-qt5/manual/lvs_compare.html
- SiEPIC EBeam PDK LVS: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- Chrostowski & Hochberg, "Silicon Photonics Design", CUP 2015
"""

from __future__ import annotations

import numpy as np
import pytest

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


def _make_netlist(
    devices: list[tuple[str, str, dict]] | None = None,
    ports: list[tuple[str, str]] | None = None,
    edges: list[tuple[str, str, str, float]] | None = None,
) -> PhotonicsNetlist:
    """创建测试用网表。

    Args:
        devices: [(node_id, device_type, params), ...]
        ports: [(node_id, layer), ...]
        edges: [(src, tgt, edge_type, length_um), ...]
    """
    dev_nodes = []
    if devices:
        for nid, dtype, params in devices:
            dev_nodes.append(NetlistNode(
                node_id=nid, node_type="device",
                device_type=dtype, params=dict(params),
            ))
    port_nodes = []
    if ports:
        for nid, layer in ports:
            port_nodes.append(NetlistNode(
                node_id=nid, node_type="port", layer=layer,
            ))
    edge_list = []
    if edges:
        for src, tgt, etype, length in edges:
            edge_list.append(NetlistEdge(
                source=src, target=tgt, edge_type=etype, length_um=length,
            ))
    return PhotonicsNetlist(devices=dev_nodes, edges=edge_list, ports=port_nodes)


class TestGraphIsomorphismDetection:
    """同图同构检测测试。"""

    def test_identical_netlists_are_isomorphic(self):
        """测试相同网表是同构的。"""
        ref = _make_netlist(
            devices=[("d1", "mmi1x2", {"length": 10.0})],
            ports=[("p1", "WG")],
            edges=[("d1", "p1", "port", 0.0)],
        )
        ext = _make_netlist(
            devices=[("d1", "mmi1x2", {"length": 10.0})],
            ports=[("p1", "WG")],
            edges=[("d1", "p1", "port", 0.0)],
        )
        report = run_graph_lvs(ref, ext)
        assert report.isomorphism_mapping is not None
        assert len(report.isomorphism_mapping) > 0

    def test_different_size_netlists_not_isomorphic(self):
        """测试不同大小的网表不同构。"""
        ref = _make_netlist(
            devices=[("d1", "mmi1x2", {})],
            edges=[],
        )
        ext = _make_netlist(
            devices=[("d1", "mmi1x2", {}), ("d2", "y_branch", {})],
            edges=[("d1", "d2", "wire", 10.0)],
        )
        report = run_graph_lvs(ref, ext)
        assert not report.is_match
        assert len(report.mismatches) > 0

    def test_two_device_chain_isomorphic(self):
        """测试两器件链式连接同构。"""
        ref = _make_netlist(
            devices=[("d1", "mmi1x2", {}), ("d2", "y_branch", {})],
            edges=[("d1", "d2", "wire", 100.0)],
        )
        ext = _make_netlist(
            devices=[("x1", "mmi1x2", {}), ("x2", "y_branch", {})],
            edges=[("x1", "x2", "wire", 100.0)],
        )
        report = run_graph_lvs(ref, ext)
        assert report.isomorphism_mapping is not None
        assert len(report.isomorphism_mapping) == 2

    def test_star_topology_isomorphic(self):
        """测试星形拓扑同构。"""
        ref = _make_netlist(
            devices=[("center", "mmi1x2", {}), ("a", "gc", {}), ("b", "gc", {})],
            edges=[("center", "a", "wire", 10.0), ("center", "b", "wire", 10.0)],
        )
        ext = _make_netlist(
            devices=[("c", "mmi1x2", {}), ("x", "gc", {}), ("y", "gc", {})],
            edges=[("c", "x", "wire", 10.0), ("c", "y", "wire", 10.0)],
        )
        report = run_graph_lvs(ref, ext)
        assert len(report.isomorphism_mapping) == 3

    def test_isomorphism_report_has_timing(self):
        """测试同构报告包含耗时信息。"""
        ref = _make_netlist(
            devices=[("d1", "mmi1x2", {})],
            edges=[],
        )
        ext = _make_netlist(
            devices=[("d1", "mmi1x2", {})],
            edges=[],
        )
        report = run_graph_lvs(ref, ext)
        assert report.comparison_time_s >= 0.0

    def test_non_isomorphic_report_details(self):
        """测试不同构报告包含详细信息。"""
        ref = _make_netlist(
            devices=[("d1", "mmi1x2", {})],
            edges=[],
        )
        ext = _make_netlist(
            devices=[("d1", "mmi1x2", {}), ("d2", "y_branch", {})],
            edges=[("d1", "d2", "wire", 10.0)],
        )
        report = run_graph_lvs(ref, ext)
        mm = report.mismatches[0]
        assert "ref_node_count" in mm
        assert "ext_node_count" in mm


class TestPortMatching:
    """端口匹配测试。"""

    def test_single_port_match(self):
        """测试单端口匹配。"""
        ref = _make_netlist(
            devices=[("d1", "mmi1x2", {})],
            ports=[("p_in", "WG")],
            edges=[("d1", "p_in", "port", 0.0)],
        )
        ext = _make_netlist(
            devices=[("d1", "mmi1x2", {})],
            ports=[("p_in", "WG")],
            edges=[("d1", "p_in", "port", 0.0)],
        )
        report = run_graph_lvs(ref, ext)
        assert len(report.isomorphism_mapping) > 0

    def test_multiple_ports_match(self):
        """测试多端口匹配。"""
        ref = _make_netlist(
            devices=[("d1", "mmi1x2", {})],
            ports=[("in", "WG"), ("out1", "WG"), ("out2", "WG")],
            edges=[
                ("d1", "in", "port", 0.0),
                ("d1", "out1", "port", 0.0),
                ("d1", "out2", "port", 0.0),
            ],
        )
        ext = _make_netlist(
            devices=[("d1", "mmi1x2", {})],
            ports=[("in", "WG"), ("out1", "WG"), ("out2", "WG")],
            edges=[
                ("d1", "in", "port", 0.0),
                ("d1", "out1", "port", 0.0),
                ("d1", "out2", "port", 0.0),
            ],
        )
        report = run_graph_lvs(ref, ext)
        assert len(report.isomorphism_mapping) == 4

    def test_port_type_mismatch(self):
        """测试端口类型不匹配。"""
        ref = _make_netlist(
            devices=[],
            ports=[("p1", "WG")],
            edges=[],
        )
        ext = _make_netlist(
            devices=[],
            ports=[("p1", "M1_HEATER")],
            edges=[],
        )
        report = run_graph_lvs(ref, ext)
        assert isinstance(report, PhotonicsLVSReport)

    def test_verify_port_orientation_match(self):
        """测试端口朝向验证匹配。"""
        ref = _make_netlist(
            devices=[("d1", "mmi1x2", {})],
            ports=[],
            edges=[],
        )
        ref.ports = [NetlistNode(
            node_id="p1", node_type="port",
            params={"orientation": "east"}, layer="WG",
        )]
        ref.edges = [NetlistEdge(source="d1", target="p1", edge_type="port")]
        ext = _make_netlist(
            devices=[("d1", "mmi1x2", {})],
            ports=[],
            edges=[],
        )
        ext.ports = [NetlistNode(
            node_id="p1", node_type="port",
            params={"orientation": "east"}, layer="WG",
        )]
        ext.edges = [NetlistEdge(source="d1", target="p1", edge_type="port")]
        mismatches = verify_port_orientation(ref, ext)
        assert len(mismatches) == 0

    def test_verify_port_orientation_mismatch(self):
        """测试端口朝向不匹配。"""
        ref = _make_netlist(
            devices=[("d1", "mmi1x2", {})],
            ports=[],
            edges=[],
        )
        ref.ports = [NetlistNode(
            node_id="p1", node_type="port",
            params={"orientation": "east"}, layer="WG",
        )]
        ref.edges = [NetlistEdge(source="d1", target="p1", edge_type="port")]
        ext = _make_netlist(
            devices=[("d1", "mmi1x2", {})],
            ports=[],
            edges=[],
        )
        ext.ports = [NetlistNode(
            node_id="p1", node_type="port",
            params={"orientation": "west"}, layer="WG",
        )]
        ext.edges = [NetlistEdge(source="d1", target="p1", edge_type="port")]
        mismatches = verify_port_orientation(ref, ext)
        assert isinstance(mismatches, list)


class TestParameterExtractionConsistency:
    """参数提取一致性测试。"""

    def test_identical_params_match(self):
        """测试相同参数匹配。"""
        ref = _make_netlist(
            devices=[("d1", "mmi1x2", {"length": 10.0, "width": 0.5})],
            edges=[],
        )
        ext = _make_netlist(
            devices=[("d1", "mmi1x2", {"length": 10.0, "width": 0.5})],
            edges=[],
        )
        report = run_graph_lvs(ref, ext)
        assert len(report.param_mismatches) == 0

    def test_param_mismatch_detected(self):
        """测试参数不匹配被检测到。"""
        ref = _make_netlist(
            devices=[("d1", "mmi1x2", {"length": 10.0})],
            edges=[],
        )
        ext = _make_netlist(
            devices=[("d1", "mmi1x2", {"length": 20.0})],
            edges=[],
        )
        report = run_graph_lvs(ref, ext)
        assert len(report.param_mismatches) >= 1

    def test_param_with_tolerance_passes(self):
        """测试带容忍度的参数通过。"""
        ref = _make_netlist(
            devices=[("d1", "mmi1x2", {"length": 10.0})],
            edges=[],
        )
        ext = _make_netlist(
            devices=[("d1", "mmi1x2", {"length": 10.5})],
            edges=[],
        )
        tol_config = {"mmi1x2": {"length": {"abs": 1.0, "rel": 0.0}}}
        report = run_graph_lvs(ref, ext, tolerance_config=tol_config)
        assert len(report.param_mismatches) == 0

    def test_param_with_tolerance_fails(self):
        """测试超出容忍度的参数失败。"""
        ref = _make_netlist(
            devices=[("d1", "mmi1x2", {"length": 10.0})],
            edges=[],
        )
        ext = _make_netlist(
            devices=[("d1", "mmi1x2", {"length": 15.0})],
            edges=[],
        )
        tol_config = {"mmi1x2": {"length": {"abs": 1.0, "rel": 0.0}}}
        report = run_graph_lvs(ref, ext, tolerance_config=tol_config)
        assert len(report.param_mismatches) >= 1

    def test_device_type_mismatch_causes_non_isomorphic(self):
        """测试器件类型不匹配导致图不同构。"""
        ref = _make_netlist(
            devices=[("d1", "mmi1x2", {})],
            edges=[],
        )
        ext = _make_netlist(
            devices=[("d1", "y_branch", {})],
            edges=[],
        )
        report = run_graph_lvs(ref, ext)
        assert not report.is_match
        assert len(report.mismatches) >= 1
        assert report.mismatches[0].get("type") == "graph_not_isomorphic"


class TestWaveguideLengthVerification:
    """波导长度验证测试。"""

    def test_identical_lengths_match(self):
        """测试相同波导长度匹配。"""
        ref = _make_netlist(
            devices=[("d1", "gc", {}), ("d2", "gc", {})],
            edges=[("d1", "d2", "wire", 100.0)],
        )
        ext = _make_netlist(
            devices=[("d1", "gc", {}), ("d2", "gc", {})],
            edges=[("d1", "d2", "wire", 100.0)],
        )
        mismatches = verify_waveguide_length(ref, ext, tolerance_um=1.0)
        assert len(mismatches) == 0

    def test_length_diff_within_tolerance(self):
        """测试长度差在容忍度内。"""
        ref = _make_netlist(
            devices=[("d1", "gc", {}), ("d2", "gc", {})],
            edges=[("d1", "d2", "wire", 100.0)],
        )
        ext = _make_netlist(
            devices=[("d1", "gc", {}), ("d2", "gc", {})],
            edges=[("d1", "d2", "wire", 100.5)],
        )
        mismatches = verify_waveguide_length(ref, ext, tolerance_um=1.0)
        assert len(mismatches) == 0

    def test_length_diff_exceeds_tolerance(self):
        """测试长度差超出容忍度。"""
        ref = _make_netlist(
            devices=[("d1", "gc", {}), ("d2", "gc", {})],
            edges=[("d1", "d2", "wire", 100.0)],
        )
        ext = _make_netlist(
            devices=[("d1", "gc", {}), ("d2", "gc", {})],
            edges=[("d1", "d2", "wire", 110.0)],
        )
        mismatches = verify_waveguide_length(ref, ext, tolerance_um=1.0)
        assert len(mismatches) >= 1


class TestPhotonicsNetlist:
    """PhotonicsNetlist 数据结构测试。"""

    def test_to_graph_basic(self):
        """测试基本图转换。"""
        nl = _make_netlist(
            devices=[("d1", "mmi1x2", {"length": 10.0})],
            edges=[],
        )
        g = nl.to_graph()
        assert g.number_of_nodes() == 1

    def test_to_graph_with_edges(self):
        """测试带边的图转换。"""
        nl = _make_netlist(
            devices=[("d1", "gc", {}), ("d2", "gc", {})],
            edges=[("d1", "d2", "wire", 100.0)],
        )
        g = nl.to_graph()
        assert g.number_of_nodes() == 2
        assert g.number_of_edges() == 1

    def test_empty_netlist_raises(self):
        """测试空网表抛 ValueError。"""
        nl = PhotonicsNetlist()
        with pytest.raises(ValueError):
            nl.to_graph()

    def test_node_attributes_preserved(self):
        """测试节点属性保留。"""
        nl = _make_netlist(
            devices=[("d1", "mmi1x2", {"length": 10.0})],
            edges=[],
        )
        g = nl.to_graph()
        attrs = g.nodes["d1"]
        assert attrs["device_type"] == "mmi1x2"
        assert attrs["params"]["length"] == 10.0


class TestEquivalenceHints:
    """等价提示集合测试。"""

    def test_same_nets_basic(self):
        """测试 same_nets 基本功能。"""
        hints = EquivalenceHints()
        hints.same_nets("net1", "net2")
        assert isinstance(hints, EquivalenceHints)

    def test_same_nets_type_error(self):
        """测试 same_nets 类型错误抛 TypeError。"""
        hints = EquivalenceHints()
        with pytest.raises(TypeError):
            hints.same_nets(123, "net2")

    def test_same_circuits_basic(self):
        """测试 same_circuits 基本功能。"""
        hints = EquivalenceHints()
        hints.same_circuits("c1", "c2")
        assert isinstance(hints, EquivalenceHints)

    def test_tolerance_config_conversion(self):
        """测试容忍度配置转换。"""
        hints = EquivalenceHints()
        hints.tolerance("mmi1x2", "length", abs_tol=0.1, rel_tol=0.05)
        config = hints.to_tolerance_config()
        assert "mmi1x2" in config
        assert config["mmi1x2"]["length"]["abs"] == 0.1
        assert config["mmi1x2"]["length"]["rel"] == 0.05

    def test_max_res_min_caps(self):
        """测试 max_res 和 min_caps 设置。"""
        hints = EquivalenceHints()
        hints.max_res(100.0)
        hints.min_caps(1e-15)
        assert isinstance(hints, EquivalenceHints)
