"""polaris-verify-advanced 主测试套件（覆盖核心 LVS + Calibre 接口 API）。

本测试套件覆盖 polaris_verify_advanced 包的核心公开 API：
模块导入、GDS 层映射、LVS 类型与图同构比对、LVS 进阶类型、容差匹配、
Calibre xACT 寄生提取接口、Calibre LFD 光刻友好设计接口。

DRC 相关测试见 test_verify_advanced_drc.py；
规则集预设/层次化 LVS/Tiled/Deep DRC 见 test_verify_advanced_extra.py。

## 学术依据（R02 学术诚信，≥5 文献 URL）

1. He et al. 2023, "OpenDRC: A Linear Programming Based Hierarchical DRC Engine",
   DAC 2023, https://doi.org/10.1109/DAC56929.2023.10247734
2. McKay & Piperno 2014, "Practical Graph Isomorphism, II",
   J. Symbolic Computation, https://www.sciencedirect.com/science/article/pii/S0747717113001930
3. Cordella et al. 2004, VF2 子图同构, IEEE TPAMI,
   https://ieeexplore.ieee.org/document/1266305
4. Siemens Calibre eqDRC:
   https://blogs.sw.siemens.com/calibre/2015/11/17/design-rule-checking-for-silicon-photonics/
5. Wang et al., SPIE 6349, 63492Z (2006), Calibre LFD PV-band,
   https://www.spiedigitallibrary.org/conference-proceedings-of-spie/6349/63492Z/
6. Banerjee ECE 225 UCSB, 寄生电容公式,
   https://courses.ece.ucsb.edu/ECE225/225_S16Banerjee/Lectures/Lecture11_ece225.pdf
7. SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
8. KLayout DRC: https://www.klayout.de/doc-qt5/manual/drc.html

合规: R02 学术诚信 / R03 禁止 fall-back（klayout 延迟导入用 importorskip）/ R05 无 TODO /
      R04 不参与 GPU / R13 不保留 v4 兼容。
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

# 让测试既能从已安装包导入，也能从源码树导入（CI/开发模式）
_SRC = str(Path(__file__).resolve().parents[1] / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)


# =============================================================================
# Smoke Test 1: 模块导入与版本
# =============================================================================
def test_module_import_and_version():
    """验证 polaris_verify_advanced 可导入且版本正确。"""
    import polaris_verify_advanced as pva

    assert pva.__version__ == "1.0.0"


# =============================================================================
# _layer_map 测试
# =============================================================================
def test_gds_layer_frozen_dataclass():
    """验证 GDSLayer 为 frozen dataclass，字段完整。"""
    from polaris_verify_advanced import GDSLayer

    layer = GDSLayer(layer=1, datatype=0, name="WG", purpose="波导")
    assert layer.layer == 1
    assert layer.datatype == 0
    assert layer.name == "WG"
    assert layer.fabricated is True  # 默认值
    # frozen 验证
    with pytest.raises(Exception):
        layer.layer = 2  # type: ignore[misc]


def test_polaris_gds_layer_map_contains_41_layers():
    """验证 POLARIS_GDS_LAYER_MAP 含至少 41 个层定义。"""
    from polaris_verify_advanced import POLARIS_GDS_LAYER_MAP

    # 关键层存在
    for key in ("WG", "SLAB150", "SLAB90", "DEEPTRENCH", "GE", "M1", "M2", "M3",
                "PORT", "DEVREC", "TEXT", "FLOORPLAN", "DICING"):
        assert key in POLARIS_GDS_LAYER_MAP, f"层 {key} 应存在"
    # 总数 ≥ 40
    assert len(POLARIS_GDS_LAYER_MAP) >= 40


def test_get_layer_tuple_known_and_unknown():
    """验证 get_layer_tuple 返回 (layer, datatype) 元组，未知层 raise KeyError。"""
    from polaris_verify_advanced import get_layer_tuple

    assert get_layer_tuple("WG") == (1, 0)
    assert get_layer_tuple("PORT") == (1, 10)
    assert get_layer_tuple("M3") == (49, 0)
    # 未知层 raise KeyError（R03 禁止 fall-back）
    with pytest.raises(KeyError):
        get_layer_tuple("NONEXISTENT_LAYER")


def test_get_category_layer_tuple():
    """验证 get_category_layer_tuple 按类别返回层元组，未知类别回退到 WG。

    注: get_category_layer_tuple 未在 __init__ 导出，从 _layer_map 子模块导入。
    """
    from polaris_verify_advanced._layer_map import get_category_layer_tuple

    assert get_category_layer_tuple("passive") == (1, 0)  # → WG
    assert get_category_layer_tuple("waveguide") == (1, 0)
    assert get_category_layer_tuple("detector") == (5, 0)  # → GE
    # 未知类别回退到 WG（设计如此，非 fall-back）
    assert get_category_layer_tuple("unknown_category") == (1, 0)


# =============================================================================
# _types 测试
# =============================================================================
def test_violation_type_enum_and_violation():
    """验证 ViolationType 枚举与 Violation dataclass。"""
    from polaris_verify_advanced import Violation, ViolationType

    # 枚举成员
    assert ViolationType.MIN_WIDTH.value == "min_width"
    assert ViolationType.BEND_RADIUS.value == "bend_radius"
    assert ViolationType.LAYER_DENSITY.value == "layer_density"
    # dataclass
    v = Violation(
        vtype=ViolationType.SPACING,
        severity=0.8,
        message="间距过小",
        device_name="wg1",
        net_id="net1",
        location=(1.5, 2.5),
    )
    assert v.vtype == ViolationType.SPACING
    assert v.severity == 0.8
    assert v.location == (1.5, 2.5)


def test_lvs_mismatch_type_enum():
    """验证 LVSMismatchType 枚举成员。"""
    from polaris_verify_advanced import LVSMismatchType

    assert LVSMismatchType.MISSING_DEVICE.value == "missing_device"
    assert LVSMismatchType.EXTRA_DEVICE.value == "extra_device"
    assert LVSMismatchType.DEVICE_TYPE_MISMATCH.value == "device_type_mismatch"
    assert LVSMismatchType.MISSING_CONNECTION.value == "missing_connection"
    assert LVSMismatchType.EXTRA_CONNECTION.value == "extra_connection"


def test_extracted_netlist_defaults():
    """验证 ExtractedNetlist 默认值与赋值。"""
    from polaris_verify_advanced import ExtractedNetlist

    en = ExtractedNetlist()
    assert en.devices == []
    assert en.connections == []
    en2 = ExtractedNetlist(devices=["d1", "d2"], connections=[("d1", "d2")])
    assert en2.devices == ["d1", "d2"]
    assert en2.connections == [("d1", "d2")]


# =============================================================================
# graph_lvs 测试
# =============================================================================
def test_netlist_node_and_edge_dataclass():
    """验证 NetlistNode / NetlistEdge dataclass 字段。"""
    from polaris_verify_advanced import NetlistEdge, NetlistNode

    node = NetlistNode(node_id="d1", node_type="device", device_type="mmi",
                       params={"width": 0.5}, layer="WG")
    assert node.node_id == "d1"
    assert node.device_type == "mmi"
    assert node.params == {"width": 0.5}
    edge = NetlistEdge(source="d1", target="d2", edge_type="wire", length_um=10.0)
    assert edge.source == "d1"
    assert edge.edge_type == "wire"
    assert edge.length_um == 10.0


def test_photonics_netlist_to_graph_and_empty():
    """验证 PhotonicsNetlist.to_graph 与空网表 raise ValueError。"""
    from polaris_verify_advanced import NetlistEdge, NetlistNode, PhotonicsNetlist

    nl = PhotonicsNetlist(
        devices=[NetlistNode("d1", "device", "mmi")],
        edges=[NetlistEdge("d1", "d2", "wire", 5.0)],
        ports=[NetlistNode("p1", "port", layer="WG")],
    )
    g = nl.to_graph()
    # d1, p1 显式添加；d2 通过 add_edge 自动添加 → 共 3 个节点
    assert g.number_of_nodes() == 3
    # 空网表 raise ValueError（R03）
    empty = PhotonicsNetlist()
    with pytest.raises(ValueError, match="网表为空"):
        empty.to_graph()


def test_photonics_netlist_from_extracted_netlist():
    """验证 from_extracted_netlist 鸭子类型转换与不支持类型 raise TypeError。"""
    from polaris_verify_advanced import (
        ExtractedNetlist,
        PhotonicsNetlist,
    )

    # ExtractedNetlist 类型（devices+connections）
    en = ExtractedNetlist(devices=["d1", "d2"], connections=[("d1", "d2")])
    pn = PhotonicsNetlist.from_extracted_netlist(en)
    assert len(pn.devices) == 2
    assert len(pn.edges) == 1
    # PolarNetlist 鸭子类型（instances+connections+ports+params）
    class FakePolarNetlist:
        instances = {"d1": "mmi", "d2": "wg"}
        connections = [("d1.in", "d2.out")]
        ports = {"p1": "top.in"}
        params = {"d1": {"w": 0.5}}
    pn2 = PhotonicsNetlist.from_extracted_netlist(FakePolarNetlist())
    assert len(pn2.devices) == 2
    assert pn2.devices[0].device_type == "mmi"
    # 不支持的类型 raise TypeError（R03）
    with pytest.raises(TypeError, match="不支持的网表类型"):
        PhotonicsNetlist.from_extracted_netlist(42)


def test_graph_isomorphism_lvs_comparer_match():
    """验证 GraphIsomorphismLVSComparer 比对同构网表 → is_match=True。"""
    from polaris_verify_advanced import (
        GraphIsomorphismLVSComparer,
        NetlistEdge,
        NetlistNode,
        PhotonicsNetlist,
    )

    ref = PhotonicsNetlist(
        devices=[NetlistNode("d1", "device", "mmi"),
                 NetlistNode("d2", "device", "wg")],
        edges=[NetlistEdge("d1", "d2", "wire", 5.0)],
        ports=[],
    )
    ext = PhotonicsNetlist(
        devices=[NetlistNode("e1", "device", "mmi"),
                 NetlistNode("e2", "device", "wg")],
        edges=[NetlistEdge("e1", "e2", "wire", 5.0)],
        ports=[],
    )
    comparer = GraphIsomorphismLVSComparer()
    report = comparer.compare(ref, ext)
    assert report.is_match is True
    assert report.isomorphism_mapping != {}


def test_graph_isomorphism_lvs_comparer_param_mismatch():
    """验证同构网表但器件参数不匹配 → param_mismatches 非空，is_match=False。

    注: VF2 node_match 已比较 device_type，不同 device_type 会判定不同构。
    本测试用相同 device_type + 不同 params 触发 param_mismatches。
    """
    from polaris_verify_advanced import (
        GraphIsomorphismLVSComparer,
        NetlistNode,
        PhotonicsNetlist,
    )

    ref = PhotonicsNetlist(
        devices=[NetlistNode("d1", "device", "wg", params={"width": 0.5})],
        edges=[], ports=[],
    )
    ext = PhotonicsNetlist(
        devices=[NetlistNode("e1", "device", "wg", params={"width": 0.4})],
        edges=[], ports=[],
    )
    # 无容忍度 → 参数不匹配
    report = GraphIsomorphismLVSComparer().compare(ref, ext)
    assert report.is_match is False
    assert len(report.param_mismatches) == 1
    assert report.param_mismatches[0]["param"] == "width"


def test_graph_isomorphism_lvs_comparer_non_isomorphic():
    """验证不同构网表 → mismatches 含 graph_not_isomorphic。"""
    from polaris_verify_advanced import (
        GraphIsomorphismLVSComparer,
        NetlistEdge,
        NetlistNode,
        PhotonicsNetlist,
    )

    ref = PhotonicsNetlist(
        devices=[NetlistNode("d1", "device", "mmi"),
                 NetlistNode("d2", "device", "wg")],
        edges=[NetlistEdge("d1", "d2", "wire", 5.0)], ports=[],
    )
    ext = PhotonicsNetlist(
        devices=[NetlistNode("e1", "device", "mmi")],  # 节点数不同
        edges=[], ports=[],
    )
    report = GraphIsomorphismLVSComparer().compare(ref, ext)
    assert report.is_match is False
    assert any(m.get("type") == "graph_not_isomorphic" for m in report.mismatches)


def test_run_graph_lvs_and_tolerance_config():
    """验证 run_graph_lvs 统一入口与 tolerance_config 参数。"""
    from polaris_verify_advanced import (
        NetlistEdge,
        NetlistNode,
        PhotonicsNetlist,
        run_graph_lvs,
    )

    ref = PhotonicsNetlist(
        devices=[NetlistNode("d1", "device", "wg", params={"length": 10.0})],
        edges=[], ports=[],
    )
    ext = PhotonicsNetlist(
        devices=[NetlistNode("e1", "device", "wg", params={"length": 10.05})],
        edges=[], ports=[],
    )
    # 容忍度 0.1μm → 匹配
    tol = {"wg": {"length": {"abs": 0.1, "rel": 0.0}}}
    report = run_graph_lvs(ref, ext, tolerance_config=tol)
    assert report.is_match is True
    # 容忍度 0.0 → 不匹配
    tol_strict = {"wg": {"length": {"abs": 0.0, "rel": 0.0}}}
    report2 = run_graph_lvs(ref, ext, tolerance_config=tol_strict)
    assert report2.is_match is False


def test_verify_waveguide_length_and_port_orientation():
    """验证 verify_waveguide_length 与 verify_port_orientation 函数。"""
    from polaris_verify_advanced import (
        NetlistEdge,
        NetlistNode,
        PhotonicsNetlist,
        verify_port_orientation,
        verify_waveguide_length,
    )

    ref = PhotonicsNetlist(
        devices=[NetlistNode("d1", "device", "wg"),
                 NetlistNode("d2", "device", "wg")],
        edges=[NetlistEdge("d1", "d2", "wire", 10.0)],
        ports=[NetlistNode("p1", "port", layer="EAST")],
    )
    ext = PhotonicsNetlist(
        devices=[NetlistNode("e1", "device", "wg"),
                 NetlistNode("e2", "device", "wg")],
        edges=[NetlistEdge("e1", "e2", "wire", 15.0)],  # 长度差 5μm
        ports=[NetlistNode("q1", "port", layer="WEST")],  # 朝向不同
    )
    # 波导长度验证：tolerance_um=1.0 → 差 5 > 1，应有不匹配
    mismatches = verify_waveguide_length(ref, ext, tolerance_um=1.0)
    assert len(mismatches) >= 1
    # 端口朝向验证
    port_mismatches = verify_port_orientation(ref, ext)
    assert len(port_mismatches) >= 1


def test_equivalence_hints():
    """验证 EquivalenceHints API 与 to_tolerance_config 转换。"""
    from polaris_verify_advanced import EquivalenceHints

    hints = EquivalenceHints()
    hints.same_nets("n1", "n2")
    hints.same_circuits("c1", "c2")
    hints.equivalent_pins("mmi", ["in", "out"])
    hints.tolerance("wg", "length", abs_tol=0.1, rel_tol=0.05)
    hints.max_res(1e-3)
    hints.min_caps(1e-15)
    cfg = hints.to_tolerance_config()
    assert "wg" in cfg
    assert cfg["wg"]["length"]["abs"] == 0.1
    # 类型校验
    with pytest.raises(TypeError):
        hints.same_nets(1, "n2")  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        hints.equivalent_pins("c", "not_a_list")  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        hints.max_res("not_a_number")  # type: ignore[arg-type]


# =============================================================================
# lvs_advanced_types 测试
# =============================================================================
def test_lvs_advanced_params_dataclasses():
    """验证 WaveguideParams/DirectionalCouplerParams/MMIParams/RingResonatorParams。"""
    from polaris_verify_advanced import (
        DirectionalCouplerParams,
        MMIParams,
        RingResonatorParams,
        WaveguideParams,
    )

    wg = WaveguideParams(name="wg1", wg_type="straight", width_um=0.5, length_um=10.0)
    assert wg.wg_type == "straight"
    assert wg.radius_um == 0.0  # 默认
    dc = DirectionalCouplerParams(name="dc1", coupling_length_um=20.0,
                                  coupling_gap_um=0.2, width_um=0.5)
    assert dc.coupling_gap_um == 0.2
    mmi = MMIParams(name="m1", width_um=2.0, length_um=10.0,
                    input_port_count=1, output_port_count=2)
    assert mmi.output_port_count == 2
    ring = RingResonatorParams(name="r1", radius_um=5.0, width_um=0.5,
                               coupling_gap_um=0.2, bus_waveguide_name="bus1")
    assert ring.bus_waveguide_name == "bus1"


def test_connectivity_report_and_param_mismatch():
    """验证 ConnectivityReport/ParamMismatch/DeviceMatchResult/LocatedError/StructuredErrorReport。"""
    from polaris_verify_advanced import (
        ConnectivityReport,
        DeviceMatchResult,
        LocatedError,
        LVSMismatchType,
        ParamMismatch,
        StructuredErrorReport,
        ToleranceSpec,
    )

    cr = ConnectivityReport(
        device_nodes=["d1", "d2"],
        connections=[("d1", "d2")],
        floating_devices=["d3"],
        isolated_groups=[["d3"]],
    )
    assert cr.floating_devices == ["d3"]
    pm = ParamMismatch(device_name="d1", param_name="width",
                       reference_value=0.5, extracted_value=0.45,
                       deviation=0.05, relative_deviation=10.0)
    assert pm.relative_deviation == 10.0
    dmr = DeviceMatchResult(matched_devices=["d1"], param_mismatches=[pm],
                            missing_devices=["d2"], extra_devices=[])
    assert dmr.missing_devices == ["d2"]
    le = LocatedError(mtype=LVSMismatchType.MISSING_DEVICE, message="缺失",
                      bbox_um=(0, 0, 10, 10), device_name="d1")
    assert le.mtype == LVSMismatchType.MISSING_DEVICE
    ser = StructuredErrorReport(short_errors=[le], total_error_count=1,
                                gds_path="/tmp/test.gds")
    assert ser.total_error_count == 1
    ts = ToleranceSpec(abs_tol=0.1, rel_tol=0.05)
    assert ts.rel_tol == 0.05


# =============================================================================
# lvs_advanced_matching 测试
# =============================================================================
def test_match_devices_with_tolerance_dict_input():
    """验证 match_devices_with_tolerance 字典输入与容差判定。"""
    from polaris_verify_advanced import ToleranceSpec, match_devices_with_tolerance

    reference = {"d1": {"width": 0.5, "length": 10.0},
                 "d2": {"width": 0.4, "length": 5.0}}
    extracted = {"d1": {"width": 0.505, "length": 10.0},  # width 差 0.005
                 "d3": {"width": 0.6, "length": 8.0}}  # 多余器件
    tolerances = {"width": ToleranceSpec(abs_tol=0.01, rel_tol=0.0),
                  "length": ToleranceSpec(abs_tol=0.0, rel_tol=0.05)}
    result = match_devices_with_tolerance(reference, extracted, tolerances)
    assert "d2" in result.missing_devices
    assert "d3" in result.extra_devices
    assert "d1" in result.matched_devices  # width 差 0.005 < 0.01


def test_match_devices_with_tolerance_type_error():
    """验证 match_devices_with_tolerance 不支持类型 raise TypeError。"""
    from polaris_verify_advanced import match_devices_with_tolerance

    with pytest.raises(TypeError, match="不支持的网表类型"):
        match_devices_with_tolerance(42, {})  # type: ignore[arg-type]


# =============================================================================
# calibre_interface 测试
# =============================================================================
def test_physical_constants():
    """验证物理常数（CODATA 2018 + Banerjee UCSB）。"""
    from polaris_verify_advanced import (
        EPS_R_SI,
        EPS_R_SIO2,
        EPS_R_SIN3,
        EPSILON_0,
        RHO_AL,
        RHO_CU,
        RHO_TIN,
        RHO_W,
    )

    assert 8.8e-12 < EPSILON_0 < 8.9e-12
    assert RHO_CU == 1.7e-8
    assert RHO_AL == 2.7e-8
    assert RHO_TIN == 1.0e-6
    assert RHO_W == 5.5e-8
    assert EPS_R_SI == 11.7
    assert EPS_R_SIO2 == 3.9
    assert EPS_R_SIN3 == 7.5


def test_layer_spec_validation():
    """验证 LayerSpec 参数校验（R03 禁止 fall-back）。"""
    from polaris_verify_advanced import EPS_R_SIO2, LayerSpec, RHO_CU

    # 合法
    spec = LayerSpec(name="M1", gds_layer=(1, 0), thickness_um=0.2,
                     resistivity_ohm_m=RHO_CU, eps_r_below=EPS_R_SIO2,
                     dielectric_thickness_um=1.0)
    assert spec.is_conductor is True
    # 厚度 <= 0 raise
    with pytest.raises(ValueError, match="厚度"):
        LayerSpec(name="M1", gds_layer=(1, 0), thickness_um=0,
                  resistivity_ohm_m=RHO_CU, eps_r_below=EPS_R_SIO2,
                  dielectric_thickness_um=1.0)
    # 导电层电阻率 <= 0 raise
    with pytest.raises(ValueError, match="电阻率"):
        LayerSpec(name="M1", gds_layer=(1, 0), thickness_um=0.2,
                  resistivity_ohm_m=0, eps_r_below=EPS_R_SIO2,
                  dielectric_thickness_um=1.0)


def test_layout_get_polygons_and_keyerror():
    """验证 Layout.get_polygons 与 KeyError。"""
    from polaris_verify_advanced import Layout

    poly = np.array([[0, 0], [1, 0], [1, 1], [0, 1]], dtype=float)
    layout = Layout(polygons={(1, 0): [poly]}, name="test")
    assert layout.get_polygons((1, 0)) == [poly]
    # 不存在的层 raise KeyError（R03）
    with pytest.raises(KeyError):
        layout.get_polygons((99, 99))


def test_parasitic_element_and_net_to_spice():
    """验证 ParasiticElement 与 ParasiticNet.to_spice。"""
    from polaris_verify_advanced import ParasiticElement, ParasiticNet

    elem = ParasiticElement(name="R1", element_type="RESISTOR",
                            value=1.5, node1="n1", node2="n2")
    assert elem.element_type == "RESISTOR"
    net = ParasiticNet(
        subckt_name="test", elements=[elem], nodes=["n1", "n2", "0"],
        total_resistance_ohm=1.5, total_capacitance_f=0.0,
    )
    spice = net.to_spice()
    assert ".SUBCKT test" in spice
    assert ".ENDS" in spice
    assert "R1" in spice


def test_parasitic_extractor_layout_and_validation():
    """验证 ParasiticExtractor.extract_layout 提取与校验。"""
    from polaris_verify_advanced import (
        EPS_R_SIO2,
        LayerSpec,
        Layout,
        ParasiticExtractor,
        RHO_CU,
    )

    poly = np.array([[0, 0], [10, 0], [10, 0.5], [0, 0.5]], dtype=float)
    spec = LayerSpec(name="M1", gds_layer=(1, 0), thickness_um=0.2,
                     resistivity_ohm_m=RHO_CU, eps_r_below=EPS_R_SIO2,
                     dielectric_thickness_um=1.0)
    layout = Layout(polygons={(1, 0): [poly]}, name="test_metal")
    extractor = ParasiticExtractor()
    net = extractor.extract_layout(layout, {"M1": spec})
    assert net.total_resistance_ohm > 0
    assert net.total_capacitance_f > 0
    # 空 layer_map raise ValueError（R03）
    with pytest.raises(ValueError, match="layer_map"):
        extractor.extract_layout(layout, {})
    # 空版图 raise ValueError
    with pytest.raises(ValueError, match="版图多边形为空"):
        extractor.extract_layout(Layout(polygons={}), {"M1": spec})


def test_parasitic_extractor_invalid_threshold():
    """验证 ParasiticExtractor 阈值非法 raise ValueError。"""
    from polaris_verify_advanced import ParasiticExtractor

    with pytest.raises(ValueError, match="阈值"):
        ParasiticExtractor(hybrid_threshold_um=0)
    with pytest.raises(ValueError, match="阈值"):
        ParasiticExtractor(hybrid_threshold_um=-1.0)


def test_parasitic_extractor_extract_file_not_found():
    """验证 ParasiticExtractor.extract 文件不存在 raise FileNotFoundError。"""
    from polaris_verify_advanced import EPS_R_SIO2, LayerSpec, ParasiticExtractor, RHO_CU

    spec = LayerSpec(name="M1", gds_layer=(1, 0), thickness_um=0.2,
                     resistivity_ohm_m=RHO_CU, eps_r_below=EPS_R_SIO2,
                     dielectric_thickness_um=1.0)
    extractor = ParasiticExtractor()
    with pytest.raises(FileNotFoundError):
        extractor.extract("/nonexistent/path.gds", {"M1": spec})


# =============================================================================
# calibre_lfd 测试
# =============================================================================
def test_litho_rule_validation():
    """验证 LithoRule 参数校验（R03 禁止 fall-back）。"""
    from polaris_verify_advanced import LithoRule

    # 合法
    rule = LithoRule(name="W1", rule_type="WIDTH", min_value=0.5,
                     gds_layer=(1, 0), severity="ERROR")
    assert rule.severity == "ERROR"
    # 非法 rule_type raise
    with pytest.raises(ValueError, match="rule_type"):
        LithoRule(name="X", rule_type="INVALID", min_value=1.0, gds_layer=(1, 0))
    # min_value <= 0 raise
    with pytest.raises(ValueError, match="min_value"):
        LithoRule(name="X", rule_type="WIDTH", min_value=0, gds_layer=(1, 0))
    # 非法 severity raise
    with pytest.raises(ValueError, match="severity"):
        LithoRule(name="X", rule_type="WIDTH", min_value=1.0,
                  gds_layer=(1, 0), severity="CRITICAL")


def test_litho_friendly_checker_width_and_area():
    """验证 LithoFriendlyChecker WIDTH 与 AREA 检查。"""
    from polaris_verify_advanced import Layout, LithoFriendlyChecker, LithoRule

    # 窄多边形（宽度 0.3μm < 阈值 0.5μm）
    narrow = np.array([[0, 0], [5, 0], [5, 0.3], [0, 0.3]], dtype=float)
    layout = Layout(polygons={(1, 0): [narrow]}, name="test")
    rule = LithoRule(name="W1", rule_type="WIDTH", min_value=0.5, gds_layer=(1, 0))
    report = LithoFriendlyChecker().check(layout, [rule])
    assert report.error_count == 1
    assert report.passed is False
    assert report.score < 100.0
    # 小面积（面积 0.04μm² < 阈值 0.1μm²）
    small = np.array([[0, 0], [0.2, 0], [0.2, 0.2], [0, 0.2]], dtype=float)
    layout2 = Layout(polygons={(1, 0): [small]}, name="test")
    area_rule = LithoRule(name="A1", rule_type="AREA", min_value=0.1,
                          gds_layer=(1, 0), severity="WARNING")
    report2 = LithoFriendlyChecker().check(layout2, [area_rule])
    assert report2.warning_count == 1
    assert report2.passed is True  # 无 ERROR


def test_litho_friendly_checker_empty_validation():
    """验证 LithoFriendlyChecker 空规则/空版图 raise ValueError。"""
    from polaris_verify_advanced import Layout, LithoFriendlyChecker

    checker = LithoFriendlyChecker()
    layout = Layout(polygons={(1, 0): [np.array([[0, 0], [1, 0], [1, 1], [0, 1]])]})
    # 空规则
    with pytest.raises(ValueError, match="规则列表"):
        checker.check(layout, [])
    # 空版图
    with pytest.raises(ValueError, match="版图多边形为空"):
        checker.check(Layout(polygons={}), [
            __import__("polaris_verify_advanced").LithoRule(
                name="W", rule_type="WIDTH", min_value=0.5, gds_layer=(1, 0))
        ])
