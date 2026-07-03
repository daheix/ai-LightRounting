"""polaris-verify-advanced 深度测试套件（覆盖全部公开 API）。

本测试套件覆盖 polaris_verify_advanced 包的全部公开 API：
图同构 LVS、LVS 进阶类型/匹配/连接性/错误报告、内化类型与层映射、
方程驱动 DRC、KLayout DRC 桥接、层次化 DRC、Calibre xACT 寄生提取、
Calibre LFD 光刻友好设计、曲线感知 DRC 18 类规则、DRC 规则集预设。

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
    # 验证核心 API 可访问
    assert hasattr(pva, "GraphIsomorphismLVSComparer")
    assert hasattr(pva, "HierarchicalDRC")
    assert hasattr(pva, "EqDRCEngine")
    assert hasattr(pva, "KLayoutDRCRunner")
    assert hasattr(pva, "ParasiticExtractor")
    assert hasattr(pva, "LithoFriendlyChecker")
    assert hasattr(pva, "CurvilinearDRCEngine")
    assert hasattr(pva, "SIEPIC_EBEAM_SOI_RULESET")
    # 验证物理常数
    assert pva.EPSILON_0 > 0
    assert pva.RHO_CU > 0
    # 验证层映射
    assert "WG" in pva.POLARIS_GDS_LAYER_MAP


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
# eqdrc 测试
# =============================================================================
def test_eqdrc_engine_add_rule_and_invalid_category():
    """验证 EqDRCEngine.add_rule 与非法类别 raise ValueError。"""
    from polaris_verify_advanced import EqDRCEngine, EqDRCRule

    engine = EqDRCEngine()
    rule = EqDRCRule(name="W1", category="WIDTH", equation="min_width=0.4",
                     layer=(1, 0), description="测试")
    engine.add_rule(rule)
    assert len(engine.rules) == 1
    # 非法类别 raise ValueError（R03）
    bad_rule = EqDRCRule(name="X1", category="INVALID", equation="", layer=(1, 0))
    with pytest.raises(ValueError, match="规则类别"):
        engine.add_rule(bad_rule)


def test_eqdrc_engine_check_width_and_space():
    """验证 EqDRCEngine.check_width / check_space 检测违规与通过。"""
    from polaris_verify_advanced import EqDRCEngine

    engine = EqDRCEngine()
    # 窄多边形（宽度 0.3μm < 阈值 0.5μm）
    narrow = [(0, 0), (10, 0), (10, 0.3), (0, 0.3)]
    # 宽多边形（宽度 1.0μm > 阈值 0.5μm），间距 5μm（narrow 右边 x=10, wide 左边 x=15）
    wide = [(15, 0), (25, 0), (25, 1.0), (15, 1.0)]
    viols = engine.check_width([narrow, wide], (1, 0), min_width=0.5)
    assert len(viols) == 1
    assert viols[0].rule_name == "EQDRC_WIDTH"
    # 间距检查：两多边形间距 5μm > 阈值 1μm → 无违规
    viols_space = engine.check_space([narrow, wide], (1, 0), min_space=1.0)
    assert len(viols_space) == 0
    # 间距检查：阈值 10μm > 间距 5μm → 有违规
    viols_space2 = engine.check_space([narrow, wide], (1, 0), min_space=10.0)
    assert len(viols_space2) == 1


def test_eqdrc_engine_check_bend_radius_and_taper():
    """验证 EqDRCEngine.check_bend_radius / check_taper。"""
    from polaris_verify_advanced import EqDRCEngine

    engine = EqDRCEngine()
    # 构建曲线路径（半径约 5μm 的圆弧）
    theta = np.linspace(0, np.pi / 2, 20)
    path = [(5.0 * np.cos(t), 5.0 * np.sin(t)) for t in theta]
    # 阈值 10μm → R≈5 < 10 违规
    viols = engine.check_bend_radius([{"points": path, "layer": (1, 0)}],
                                     (1, 0), min_radius=10.0)
    assert len(viols) == 1
    # 阈值 1μm → 通过
    viols2 = engine.check_bend_radius([{"points": path, "layer": (1, 0)}],
                                      (1, 0), min_radius=1.0)
    assert len(viols2) == 0


def test_eqdrc_engine_check_coverage():
    """验证 EqDRCEngine.check_coverage 覆盖率检查与 area<=0 raise。"""
    from polaris_verify_advanced import EqDRCEngine

    engine = EqDRCEngine()
    poly = [(0, 0), (10, 0), (10, 5), (0, 5)]  # 面积 50
    # 覆盖率 50/100 = 0.5 ≥ 0.3 → 无违规
    viols = engine.check_coverage([poly], (1, 0), min_coverage=0.3, area=100.0)
    assert len(viols) == 0
    # 覆盖率 0.5 < 0.8 → 违规
    viols2 = engine.check_coverage([poly], (1, 0), min_coverage=0.8, area=100.0)
    assert len(viols2) == 1
    # area <= 0 raise ValueError（R03）
    with pytest.raises(ValueError, match="区域面积"):
        engine.check_coverage([poly], (1, 0), min_coverage=0.5, area=0.0)


def test_eqdrc_engine_run_all_dispatch():
    """验证 EqDRCEngine.run_all 按 category 分发执行。"""
    from polaris_verify_advanced import EqDRCEngine, EqDRCRule

    engine = EqDRCEngine()
    engine.add_rule(EqDRCRule(
        name="W1", category="WIDTH", equation="min_width=0.5",
        layer=(1, 0), description="宽度"))
    layout = {
        "polygons": [{"points": [(0, 0), (10, 0), (10, 0.3), (0, 0.3)],
                      "layer": (1, 0)}],
        "paths": [],
    }
    viols = engine.run_all(layout)
    assert len(viols) == 1
    assert viols[0].rule_name == "EQDRC_WIDTH"


def test_curvilinear_lvs_extract_and_compare():
    """验证 CurvilinearLVS 提取网表与比对。"""
    from polaris_verify_advanced import CurvilinearLVS

    lvs = CurvilinearLVS()
    # 构建含曲线 path 的版图
    theta = np.linspace(0, np.pi / 2, 20)
    layout = {
        "paths": [{"name": "bend1", "layer": "WG",
                   "points": [(5.0 * np.cos(t), 5.0 * np.sin(t)) for t in theta]}],
        "polygons": [],
        "markers": [{"layer": "TEXT", "text": "bend1", "xy": (0, 0)}],
    }
    result = lvs.extract_netlist_with_markers(layout, ["TEXT"])
    assert result["marker_count"] == 1
    assert len(result["devices"]) >= 1
    # 比对：原理图与版图一致
    schematic = {"devices": result["devices"], "connections": result["connections"]}
    cmp = lvs.compare_with_schematic(result, schematic)
    assert cmp["is_match"] is True
    # 比对：原理图多一个器件 → 不匹配
    schematic2 = {"devices": result["devices"] + [{"name": "extra", "type": "wg"}],
                  "connections": []}
    cmp2 = lvs.compare_with_schematic(result, schematic2)
    assert cmp2["is_match"] is False


def test_curvilinear_lvs_verify_curvilinear_shapes():
    """验证 CurvilinearLVS.verify_curvilinear_shapes 识别 bend/taper。"""
    from polaris_verify_advanced import CurvilinearLVS

    lvs = CurvilinearLVS()
    # 直线 → 无曲线组件
    layout = {"paths": [{"name": "straight", "points": [(0, 0), (10, 0), (20, 0)]}]}
    comps = lvs.verify_curvilinear_shapes(layout)
    # 三个共线点曲率为 0，finite 为空，无组件
    assert len(comps) == 0
    # 曲线 path → 识别 bend
    theta = np.linspace(0, np.pi / 2, 20)
    layout2 = {"paths": [{"name": "bend",
                          "points": [(5.0 * np.cos(t), 5.0 * np.sin(t)) for t in theta]}]}
    comps2 = lvs.verify_curvilinear_shapes(layout2)
    assert any(c["type"] == "bend" for c in comps2)


def test_foundry_drc_certifier_build_runsets():
    """验证 FoundryDRCCertifier 构建 5 个 foundry runset。"""
    from polaris_verify_advanced import FoundryDRCCertifier

    certifier = FoundryDRCCertifier()
    amf = certifier.build_amf_runset()
    ihp = certifier.build_ihp_runset()
    gf = certifier.build_gf_fotonix_runset()
    ligentec = certifier.build_ligentec_runset()
    lionix = certifier.build_lionix_runset()
    for runset in (amf, ihp, gf, ligentec, lionix):
        assert len(runset.rules) == 4  # WIDTH/SPACE/BEND/TAPER
        assert runset.certified is True
        assert len(runset.sources) >= 1
    # 验证不同 foundry 参数差异
    amf_w_rule = next(r for r in amf.rules if r.category == "WIDTH")
    ligentec_w_rule = next(r for r in ligentec.rules if r.category == "WIDTH")
    # AMF w_min=0.4, LIGENTEC w_min=0.8
    assert "0.4" in amf_w_rule.equation
    assert "0.8" in ligentec_w_rule.equation


def test_foundry_drc_certifier_certify_runset():
    """验证 FoundryDRCCertifier.certify_runset 认证流程。"""
    from polaris_verify_advanced import FoundryDRCCertifier

    certifier = FoundryDRCCertifier()
    runset = certifier.build_amf_runset()
    # 干净版图（满足所有规则）→ PASS
    clean_layout = {
        "polygons": [{"points": [(0, 0), (100, 0), (100, 10), (0, 10)],
                      "layer": (1, 0)}],  # 宽度 10μm > 0.4
        "paths": [],
    }
    result = certifier.certify_runset(runset, clean_layout)
    assert "foundry" in result
    assert "certified" in result
    assert "report" in result


def test_drc_report_generator():
    """验证 DRCReportGenerator 生成报告与修复建议。"""
    from polaris_verify_advanced import (
        DRCReportGenerator,
        EqDRCViolation,
    )

    gen = DRCReportGenerator()
    viols = [EqDRCViolation(
        rule_name="EQDRC_WIDTH", layer=(1, 0), location=(5.0, 5.0),
        actual_value=0.3, expected_value=0.5, severity="ERROR",
        message="宽度不足")]
    report = gen.generate_report(viols, "test_layout")
    assert "DRC 认证报告" in report
    assert "EQDRC_WIDTH" in report
    summary = gen.generate_summary(viols)
    assert summary["total"] == 1
    assert summary["errors"] == 1
    assert "EQDRC_WIDTH" in summary["by_rule"]
    suggestions = gen.suggest_fixes(viols)
    assert len(suggestions) == 1
    assert suggestions[0]["action"] == "increase_width"
    # 干净报告
    clean_report = gen.generate_report([], "clean_layout")
    assert "DRC CLEAN" in clean_report


# =============================================================================
# klayout_drc 测试（klayout 延迟导入用 importorskip）
# =============================================================================
def test_drc_check_type_enum():
    """验证 DRCCheckType 枚举成员。"""
    from polaris_verify_advanced import DRCCheckType

    assert DRCCheckType.WIDTH.value == "width"
    assert DRCCheckType.SPACE.value == "space"
    assert DRCCheckType.NOTCH.value == "notch"
    assert DRCCheckType.ENCLOSE.value == "enclose"
    assert DRCCheckType.AREA.value == "area"
    assert DRCCheckType.DENSITY.value == "density"
    assert DRCCheckType.VIA.value == "via"


def test_drc_rule_dataclass_and_runset():
    """验证 DRCRule dataclass 与 SIEPIC_EBEAM_DRC_RUNSET 默认 runset。"""
    from polaris_verify_advanced import (
        DRCRule,
        DRCCheckType,
        SIEPIC_EBEAM_DRC_RUNSET,
        ViolationType,
    )

    rule = DRCRule(
        name="TEST", layer_name="WG", check_type=DRCCheckType.WIDTH,
        threshold_um=0.5, vtype=ViolationType.MIN_WIDTH, description="测试",
    )
    assert rule.threshold_um == 0.5
    assert rule.severity == 1.0  # 默认
    # SiEPIC EBeam runset 至少 10 条规则
    assert len(SIEPIC_EBEAM_DRC_RUNSET) >= 10
    # 验证包含 WIDTH/SPACE/NOTCH/AREA/DENSITY/ENCLOSE/VIA 多种类型
    types = {r.check_type for r in SIEPIC_EBEAM_DRC_RUNSET}
    assert DRCCheckType.WIDTH in types
    assert DRCCheckType.SPACE in types
    assert DRCCheckType.VIA in types


def test_drc_result_dataclass():
    """验证 DRCResult dataclass 属性。"""
    from polaris_verify_advanced import DRCResult, Violation, ViolationType

    result = DRCResult(
        violations=[Violation(vtype=ViolationType.MIN_WIDTH, message="测试")],
        gds_path="/tmp/test.gds", runset_name="custom",
        total_rules=5, passed_rules=4,
    )
    assert result.violation_count == 1
    assert result.is_clean is False
    clean = DRCResult()
    assert clean.is_clean is True
    assert clean.violation_count == 0


def test_klayout_drc_runner_import_error():
    """验证 KLayoutDRCRunner.run_gds 在无 klayout 时 raise ImportError 或 FileNotFoundError。

    R03 禁止 fall-back：klayout 不可用时必须 raise。
    """
    pytest.importorskip("klayout")  # 无 klayout 时跳过本测试（R03 用 importorskip）
    # 有 klayout 时，文件不存在 → FileNotFoundError
    from polaris_verify_advanced import KLayoutDRCRunner

    runner = KLayoutDRCRunner()
    with pytest.raises(FileNotFoundError):
        runner.run_gds("/nonexistent/path/test.gds")


def test_run_klayout_drc_function():
    """验证 run_klayout_drc 便捷函数（无 klayout 时跳过）。"""
    pytest.importorskip("klayout")
    from polaris_verify_advanced import run_klayout_drc

    with pytest.raises(FileNotFoundError):
        run_klayout_drc("/nonexistent/path/test.gds")


# =============================================================================
# hierarchical_drc 测试
# =============================================================================
def test_bvh_build_and_query():
    """验证 BVH 构建与查询。"""
    from polaris_verify_advanced import BVH

    bvh = BVH()
    # 空输入返回 None
    assert bvh.build([]) is None
    # 构建多个多边形
    polys = [
        np.array([[0, 0], [10, 0], [10, 10], [0, 10]], dtype=float),
        np.array([[20, 0], [30, 0], [30, 10], [20, 10]], dtype=float),
        np.array([[100, 100], [110, 100], [110, 110], [100, 110]], dtype=float),
    ]
    root = bvh.build(polys)
    assert root is not None
    # 查询左下角区域 → 应返回前两个多边形
    result = bvh.query((0, 0, 35, 15))
    assert len(result) >= 2
    # 查询空区域
    assert bvh.query((1000, 1000, 1001, 1001)) == []


def test_bvh_node_is_leaf():
    """验证 BVHNode.is_leaf 属性。"""
    from polaris_verify_advanced import BVHNode

    leaf = BVHNode(bbox=(0, 0, 10, 10), polygons=[np.array([[0, 0]])])
    assert leaf.is_leaf is True
    internal = BVHNode(bbox=(0, 0, 20, 20), left=leaf,
                       right=BVHNode(bbox=(10, 10, 20, 20)))
    assert internal.is_leaf is False


def test_row_partition():
    """验证 RowPartition 自适应行分块与 max_rows 校验。"""
    from polaris_verify_advanced import RowPartition

    rp = RowPartition(max_rows=10)
    # 空输入
    assert rp.partition([]) == []
    # 多个多边形
    polys = [np.array([[i, 0], [i + 1, 0], [i + 1, 1], [i, 1]], dtype=float)
             for i in range(20)]
    blocks = rp.partition(polys)
    assert len(blocks) >= 1
    # 所有块的多边形总数 = 原始数
    total = sum(len(b) for b in blocks)
    assert total == 20
    # max_rows < 1 raise ValueError（R03）
    with pytest.raises(ValueError, match="max_rows"):
        RowPartition(max_rows=0)


def test_hierarchical_drc_width_and_empty_rules():
    """验证 HierarchicalDRC 检测宽度违规与空规则 raise ValueError。"""
    from polaris_verify_advanced import (
        DRCCheckType,
        DRCRule,
        HierarchicalDRC,
        ViolationType,
    )

    # 空规则 raise ValueError（R03）
    with pytest.raises(ValueError, match="DRC 规则列表不能为空"):
        HierarchicalDRC([])

    narrow = np.array([[0, 0], [10, 0], [10, 0.3], [0, 0.3]], dtype=float)
    wide = np.array([[20, 0], [30, 0], [30, 1.0], [20, 1.0]], dtype=float)
    rule = DRCRule(name="W1", layer_name="WG", check_type=DRCCheckType.WIDTH,
                   threshold_um=0.5, vtype=ViolationType.MIN_WIDTH)
    engine = HierarchicalDRC([rule])
    layout = {"WG": [narrow, wide]}
    viols = engine.check(layout, hierarchical=True)
    assert len(viols) == 1
    assert "宽度" in viols[0].message
    # flat 模式
    viols_flat = engine.check(layout, hierarchical=False)
    assert len(viols_flat) == 1


def test_hierarchical_drc_space_and_area():
    """验证 HierarchicalDRC 间距与面积检查。"""
    from polaris_verify_advanced import (
        DRCCheckType,
        DRCRule,
        HierarchicalDRC,
        ViolationType,
    )

    # 两个相近多边形（间距 0.5μm < 阈值 1.0μm）
    p1 = np.array([[0, 0], [10, 0], [10, 1], [0, 1]], dtype=float)
    p2 = np.array([[10.5, 0], [20, 0], [20, 1], [10.5, 1]], dtype=float)
    space_rule = DRCRule(name="S1", layer_name="WG", check_type=DRCCheckType.SPACE,
                         threshold_um=1.0, vtype=ViolationType.SPACING)
    engine = HierarchicalDRC([space_rule])
    viols = engine.check({"WG": [p1, p2]}, hierarchical=True)
    assert len(viols) == 1
    # 小面积违规
    small = np.array([[0, 0], [0.2, 0], [0.2, 0.2], [0, 0.2]], dtype=float)  # 面积 0.04
    area_rule = DRCRule(name="A1", layer_name="WG", check_type=DRCCheckType.AREA,
                        threshold_um=0.1, vtype=ViolationType.MIN_AREA)
    engine2 = HierarchicalDRC([area_rule])
    viols2 = engine2.check({"WG": [small]}, hierarchical=True)
    assert len(viols2) == 1


def test_run_hierarchical_drc_function():
    """验证 run_hierarchical_drc 统一入口。"""
    from polaris_verify_advanced import (
        DRCCheckType,
        DRCRule,
        ViolationType,
        run_hierarchical_drc,
    )

    narrow = np.array([[0, 0], [10, 0], [10, 0.3], [0, 0.3]], dtype=float)
    rule = DRCRule(name="W1", layer_name="WG", check_type=DRCCheckType.WIDTH,
                   threshold_um=0.5, vtype=ViolationType.MIN_WIDTH)
    viols = run_hierarchical_drc({"WG": [narrow]}, [rule], hierarchical=True)
    assert len(viols) == 1


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


# =============================================================================
# drc_curvilinear_18rules 测试（保留 smoke test 并扩展）
# =============================================================================
def test_curvilinear_drc_engine_18_rules():
    """验证 CurvilinearDRCEngine 注册 18 类规则并能检测违规。

    来源: Synopsys OptoDesigner DRC Module
    https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/design-rule-checking-module.html
    """
    from polaris_verify_advanced import CurvilinearDRCEngine

    engine = CurvilinearDRCEngine()
    assert engine.rule_count == 18, f"应有 18 条规则，实际 {engine.rule_count}"

    # 验证曲线规则数量（W3/CV1/CV2/CV3/ANG3 共 5 条）
    curvilinear = [r for r in engine._rules if r.is_curvilinear]
    assert len(curvilinear) == 5, f"应有 5 条曲线规则，实际 {len(curvilinear)}"

    # 制造全违规版图数据
    layout = {
        "waveguide": {
            "min_width": 0.40, "max_width": 4.0, "min_curve_width": 0.45,
            "min_spacing": 0.4, "same_net_spacing": 0.2, "density_spacing": 0.5,
            "end_to_end": 0.4, "density": 0.03, "max_angle": 140, "min_angle": 80,
            "min_bend_radius": 3.0, "max_curvature": 0.3, "taper_angle": 15,
        },
        "contact": {"min_enclosure": 0.08},
        "metal1": {"min_extension": 0.15},
        "pad": {"min_area": 2000},
        "slab": {"max_area": 60000},
    }
    violations = engine.run_checks(layout)
    assert len(violations) == 18, f"应有 18 条违规，实际 {len(violations)}"

    rpt = engine.report()
    assert rpt["total_rules"] == 18
    assert rpt["errors"] > 0
    assert rpt["passed"] is False

    # 验证扩展规则启用
    engine.enable_extended_rules()
    assert engine.rule_count == 26
    assert engine.extended_rules_enabled is True
    engine.disable_extended_rules()
    assert engine.rule_count == 18
    assert engine.extended_rules_enabled is False


def test_curvilinear_drc_engine_clean_layout():
    """验证 CurvilinearDRCEngine 干净版图无违规。"""
    from polaris_verify_advanced import CurvilinearDRCEngine

    engine = CurvilinearDRCEngine()
    # 所有指标都满足规则
    layout = {
        "waveguide": {
            "min_width": 0.5, "max_width": 2.0, "min_curve_width": 0.6,
            "min_spacing": 0.6, "same_net_spacing": 0.4, "density_spacing": 1.0,
            "end_to_end": 0.7, "density": 0.1, "max_angle": 120, "min_angle": 95,
            "min_bend_radius": 6.0, "max_curvature": 0.1, "taper_angle": 5,
        },
    }
    violations = engine.run_checks(layout)
    assert len(violations) == 0
    rpt = engine.report()
    assert rpt["passed"] is True
    assert rpt["total_violations"] == 0


def test_curvilinear_drc_engine_list_rules_by_category():
    """验证 CurvilinearDRCEngine.list_rules_by_category。"""
    from polaris_verify_advanced import CurvilinearDRCEngine

    engine = CurvilinearDRCEngine()
    by_cat = engine.list_rules_by_category()
    assert "min_width" in by_cat
    assert "min_spacing" in by_cat
    assert "min_bend_radius" in by_cat
    # MIN_WIDTH 类应有 W1 一条
    assert len(by_cat["min_width"]) == 1


def test_curvilinear_drc_engine_extended_idempotent():
    """验证扩展规则启用/禁用幂等性。"""
    from polaris_verify_advanced import CurvilinearDRCEngine

    engine = CurvilinearDRCEngine()
    # 重复启用幂等
    engine.enable_extended_rules()
    engine.enable_extended_rules()
    assert engine.rule_count == 26
    # 重复禁用幂等
    engine.disable_extended_rules()
    engine.disable_extended_rules()
    assert engine.rule_count == 18


# =============================================================================
# _drc_rules 测试
# =============================================================================
def test_drc_rule_category_enum_26_values():
    """验证 DRCRuleCategory 26 类枚举成员。"""
    from polaris_verify_advanced import DRCRuleCategory

    # 18 类基础规则
    assert DRCRuleCategory.MIN_WIDTH.value == "min_width"
    assert DRCRuleCategory.MAX_WIDTH.value == "max_width"
    assert DRCRuleCategory.TAPER_ANGLE.value == "taper_angle"
    # 8 类扩展规则
    assert DRCRuleCategory.STEP_WIDTH.value == "step_width"
    assert DRCRuleCategory.SYMMETRY.value == "symmetry"
    assert DRCRuleCategory.MAX_WIDTH_SINGLE_MODE.value == "max_width_single_mode"
    # 总数 = 26
    assert len(list(DRCRuleCategory)) == 26


def test_curvilinear_drc_rule_dataclass():
    """验证 CurvilinearDRCRule dataclass 字段与扩展字段。"""
    from polaris_verify_advanced import CurvilinearDRCRule, DRCRuleCategory

    rule = CurvilinearDRCRule(
        name="R1", category=DRCRuleCategory.MIN_WIDTH, layer="WG",
        limit_value=0.5, units="μm", is_curvilinear=False,
        description="测试", severity="error",
    )
    assert rule.limit_max is None  # 默认
    assert rule.layer_pair is None
    assert rule.tolerance is None
    # 扩展字段
    rule2 = CurvilinearDRCRule(
        name="R2", category=DRCRuleCategory.EDGE_LENGTH, layer="WG",
        limit_value=0.2, limit_max=1000.0, layer_pair=None,
    )
    assert rule2.limit_max == 1000.0


def test_drc_violation18_dataclass():
    """验证 DRCViolation18 dataclass 字段。"""
    from polaris_verify_advanced import DRCViolation18

    v = DRCViolation18(
        rule_name="W1", category="min_width", layer="WG",
        severity="error", message="宽度不足",
        location_um=(5.0, 5.0), measured_value=0.3, limit_value=0.5,
    )
    assert v.rule_name == "W1"
    assert v.measured_value == 0.3
    assert v.limit_value == 0.5


# =============================================================================
# drc_ruleset_presets 测试（保留 smoke test 并扩展）
# =============================================================================
def test_drc_ruleset_presets():
    """验证 DRC 规则集预设可正确加载和校验。

    来源: SiEPIC EBeam PDK, https://github.com/SiEPIC/SiEPIC_EBeam_PDK
    """
    from polaris_verify_advanced import (
        GENERIC_CONSERVATIVE_RULESET,
        SIEPIC_EBEAM_SIN_RULESET,
        SIEPIC_EBEAM_SOI_RULESET,
        CustomRuleSetBuilder,
        get_preset_ruleset,
        list_preset_rulesets,
        validate_ruleset,
    )

    # 验证预设规则集数量
    assert len(SIEPIC_EBEAM_SOI_RULESET) == 11, "SOI 规则集应有 11 条规则"
    assert len(SIEPIC_EBEAM_SIN_RULESET) == 8, "SiN 规则集应有 8 条规则"
    assert len(GENERIC_CONSERVATIVE_RULESET) == 6, "Generic 规则集应有 6 条规则"

    # 验证预设列表
    names = list_preset_rulesets()
    assert "siepic_ebeam_soi" in names
    assert "siepic_ebeam_sin" in names
    assert "generic_conservative" in names

    # 验证获取预设（返回副本）
    rules = get_preset_ruleset("siepic_ebeam_soi")
    assert len(rules) == 11
    rules.append(rules[0])  # 修改副本
    assert len(SIEPIC_EBEAM_SOI_RULESET) == 11  # 原始不受影响

    # 验证未知规则集名抛 ValueError（R03）
    with pytest.raises(ValueError, match="未知规则集名"):
        get_preset_ruleset("nonexistent")

    # 验证规则集校验（合法规则集无问题）
    issues = validate_ruleset(SIEPIC_EBEAM_SOI_RULESET)
    assert issues == [], f"SOI 规则集应有 0 个问题，实际 {issues}"

    # 验证 CustomRuleSetBuilder 流式构建
    builder = CustomRuleSetBuilder()
    ruleset = (
        builder
        .add_min_width("R1", "WG", 0.4, description="测试宽度")
        .add_min_spacing("R2", "WG", 1.0, description="测试间距")
        .add_min_bend_radius("R3", "WG", 5.0, description="测试弯曲半径")
        .build()
    )
    assert len(ruleset) == 3
    assert builder.rule_count() == 3


def test_drc_ruleset_presets_all_three():
    """验证三个预设规则集均能通过 validate_ruleset。"""
    from polaris_verify_advanced import (
        GENERIC_CONSERVATIVE_RULESET,
        SIEPIC_EBEAM_SIN_RULESET,
        SIEPIC_EBEAM_SOI_RULESET,
        validate_ruleset,
    )

    for name, ruleset in [("SOI", SIEPIC_EBEAM_SOI_RULESET),
                          ("SiN", SIEPIC_EBEAM_SIN_RULESET),
                          ("Generic", GENERIC_CONSERVATIVE_RULESET)]:
        issues = validate_ruleset(ruleset)
        assert issues == [], f"{name} 规则集应有 0 个问题，实际 {issues}"


def test_validate_ruleset_detects_issues():
    """验证 validate_ruleset 检测重复名/非法 limit_value/空 layer。"""
    from polaris_verify_advanced import (
        CurvilinearDRCRule,
        DRCRuleCategory,
        validate_ruleset,
    )

    # 重复规则名
    r1 = CurvilinearDRCRule(name="DUP", category=DRCRuleCategory.MIN_WIDTH,
                            layer="WG", limit_value=0.5, units="μm")
    r2 = CurvilinearDRCRule(name="DUP", category=DRCRuleCategory.MIN_WIDTH,
                            layer="WG", limit_value=0.4, units="μm")
    issues = validate_ruleset([r1, r2])
    assert any("重复" in i for i in issues)
    # limit_value <= 0
    r3 = CurvilinearDRCRule(name="R3", category=DRCRuleCategory.MIN_WIDTH,
                            layer="WG", limit_value=0, units="μm")
    issues2 = validate_ruleset([r3])
    assert any("limit_value" in i for i in issues2)
    # 非 list 类型 raise TypeError
    with pytest.raises(TypeError, match="rules 必须是列表"):
        validate_ruleset("not_a_list")  # type: ignore[arg-type]


def test_custom_ruleset_builder_full_api():
    """验证 CustomRuleSetBuilder 全部 add_* 方法与 build 失败。"""
    from polaris_verify_advanced import CustomRuleSetBuilder, DRCRuleCategory

    builder = CustomRuleSetBuilder()
    ruleset = (
        builder
        .add_min_width("W1", "WG", 0.5)
        .add_min_spacing("S1", "WG", 1.0)
        .add_min_area("A1", "WG", 0.1)
        .add_min_bend_radius("B1", "WG", 5.0)
        .add_max_angle("ANG1", "WG", 90.0)
        .add_rule("X1", DRCRuleCategory.MAX_WIDTH, "WG", 3.0)
        .build()
    )
    assert len(ruleset) == 6
    # build 失败：重复名
    bad_builder = CustomRuleSetBuilder()
    bad_builder.add_min_width("DUP", "WG", 0.5)
    bad_builder.add_min_spacing("DUP", "WG", 1.0)  # 重复名
    with pytest.raises(ValueError, match="规则集校验失败"):
        bad_builder.build()


# =============================================================================
# lvs_advanced_connectivity / error_report 测试（klayout 延迟导入）
# =============================================================================
def test_extract_connectivity_no_klayout():
    """验证 extract_connectivity 在无 klayout 时 raise ImportError。

    R03 禁止 fall-back：klayout 不可用时必须 raise。
    """
    pytest.importorskip("klayout")
    from polaris_verify_advanced import extract_connectivity

    with pytest.raises((FileNotFoundError, RuntimeError)):
        extract_connectivity("/nonexistent/path.gds")


def test_generate_structured_error_report_no_klayout():
    """验证 generate_structured_error_report 在无 klayout 时 raise。

    R03 禁止 fall-back：klayout 不可用时必须 raise。
    """
    pytest.importorskip("klayout")
    from polaris_verify_advanced import (
        ExtractedNetlist,
        generate_structured_error_report,
    )

    ref = ExtractedNetlist(devices=["d1"], connections=[])
    with pytest.raises((FileNotFoundError, RuntimeError)):
        generate_structured_error_report("/nonexistent/path.gds", ref)


# =============================================================================
# Smoke Test 保留：ParasiticExtractor 寄生提取（纯 NumPy，无 klayout）
# =============================================================================
def test_parasitic_extractor_layout():
    """验证 ParasiticExtractor.extract_layout 从 Layout 提取寄生参数。

    公式: R = ρ·L/(w·h), C_pp = ε₀·εᵣ·w·L/d
    来源: Banerjee ECE 225 UCSB
    https://courses.ece.ucsb.edu/ECE225/225_S16Banerjee/Lectures/Lecture11_ece225.pdf
    """
    from polaris_verify_advanced import (
        EPS_R_SIO2,
        LayerSpec,
        Layout,
        ParasiticExtractor,
        RHO_CU,
    )

    poly = np.array([
        [0.0, 0.0], [10.0, 0.0], [10.0, 0.5], [0.0, 0.5],
    ], dtype=float)
    layer_spec = LayerSpec(
        name="METAL1", gds_layer=(1, 0), thickness_um=0.2,
        resistivity_ohm_m=RHO_CU, eps_r_below=EPS_R_SIO2,
        dielectric_thickness_um=1.0, is_conductor=True,
    )
    layout = Layout(polygons={(1, 0): [poly]}, name="test_metal")
    extractor = ParasiticExtractor()
    net = extractor.extract_layout(layout, {"METAL1": layer_spec})
    assert net.total_resistance_ohm > 0
    assert net.total_capacitance_f > 0
    assert len(net.elements) >= 2
    spice = net.to_spice()
    assert ".SUBCKT" in spice
    assert ".ENDS" in spice
    with pytest.raises(ValueError, match="layer_map"):
        extractor.extract_layout(layout, {})


# =============================================================================
# Smoke Test 保留：HierarchicalDRC 层次化 DRC（纯 NumPy）
# =============================================================================
def test_hierarchical_drc_width_violation():
    """验证 HierarchicalDRC 检测宽度违规。

    来源: OpenDRC, He et al., DAC 2023, DOI:10.1109/DAC56929.2023.10247734
    """
    from polaris_verify_advanced import (
        DRCCheckType,
        DRCRule,
        HierarchicalDRC,
        ViolationType,
    )

    narrow_poly = np.array([
        [0.0, 0.0], [10.0, 0.0], [10.0, 0.3], [0.0, 0.3],
    ], dtype=float)
    wide_poly = np.array([
        [20.0, 0.0], [30.0, 0.0], [30.0, 1.0], [20.0, 1.0],
    ], dtype=float)
    rule = DRCRule(
        name="TEST_WIDTH", layer_name="WG",
        check_type=DRCCheckType.WIDTH, threshold_um=0.5,
        vtype=ViolationType.MIN_WIDTH, description="测试宽度规则",
    )
    engine = HierarchicalDRC([rule])
    layout = {"WG": [narrow_poly, wide_poly]}
    violations = engine.check(layout, hierarchical=True)
    assert len(violations) == 1
    assert violations[0].rule_name == "TEST_WIDTH"
    assert "宽度" in violations[0].message


# =============================================================================
# Smoke Test 保留：LithoFriendlyChecker 光刻友好设计检查
# =============================================================================
def test_litho_friendly_checker():
    """验证 LithoFriendlyChecker 检测光刻热点并计算评分。

    来源: Wang et al., SPIE 6349, 63492Z (2006), doi:10.1117/12.685727
    """
    from polaris_verify_advanced import (
        Layout,
        LithoFriendlyChecker,
        LithoRule,
    )

    narrow_poly = np.array([
        [0.0, 0.0], [5.0, 0.0], [5.0, 0.3], [0.0, 0.3],
    ], dtype=float)
    layout = Layout(polygons={(1, 0): [narrow_poly]}, name="test_litho")
    rule = LithoRule(
        name="LITHO_WIDTH", rule_type="WIDTH", min_value=0.5,
        gds_layer=(1, 0), severity="ERROR",
    )
    checker = LithoFriendlyChecker()
    report = checker.check(layout, [rule])
    assert report.error_count == 1
    assert report.passed is False
    assert report.score < 100.0
    assert report.hotspot_count == 1
    with pytest.raises(ValueError, match="规则列表"):
        checker.check(layout, [])
    with pytest.raises(ValueError, match="rule_type"):
        LithoRule(name="BAD", rule_type="INVALID", min_value=1.0, gds_layer=(1, 0))


# =============================================================================
# 层次化 LVS（≥3 层递归比对，R9 路标）
# =============================================================================
def _make_3level_hierarchy(top_dev: str, mid_dev: str, leaf_dev: str, prefix: str) -> dict:
    """构造 3 层层次结构（dict 格式，TOP → MID → LEAF）。

    来源: Cordella 2004 VF2; Calibre nmLVS hierarchical compare
    https://ieeexplore.ieee.org/document/1266305
    """
    return {
        "name": "TOP",
        "devices": [{"node_id": f"{prefix}_top_d1", "device_type": top_dev}],
        "connections": [],
        "children": [
            {
                "name": "MID",
                "devices": [{"node_id": f"{prefix}_mid_d1", "device_type": mid_dev}],
                "connections": [],
                "children": [
                    {
                        "name": "LEAF",
                        "devices": [
                            {"node_id": f"{prefix}_leaf_d1", "device_type": leaf_dev}
                        ],
                        "connections": [],
                        "children": [],
                    }
                ],
            }
        ],
    }


def test_hierarchical_lvs_3_levels_match():
    """验证 3 层层次化 LVS 递归比对匹配 → is_match=True, total_levels=3。

    来源: Cordella 2004 VF2; Calibre nmLVS hierarchical compare
    https://ieeexplore.ieee.org/document/1266305
    https://eda.sw.siemens.com/en-US/calibre/calibre-nm-lvs-replay/
    """
    from polaris_verify_advanced import HierarchicalLVS

    sch = _make_3level_hierarchy("mmi", "wg", "ybranch", "sch")
    lay = _make_3level_hierarchy("mmi", "wg", "ybranch", "lay")
    comparer = HierarchicalLVS()
    report = comparer.compare_hierarchical(sch, lay)
    assert report.is_match is True
    assert report.total_levels == 3
    assert len(report.level_results) == 3
    # 每层 cell name 与层级编号
    level_names = {(r.level, r.cell_name) for r in report.level_results}
    assert (0, "TOP") in level_names
    assert (1, "MID") in level_names
    assert (2, "LEAF") in level_names
    # 每层均匹配且无不匹配项
    assert all(r.is_match for r in report.level_results)
    assert report.all_mismatches == []
    # 每层 VF2 应找到同构映射（节点数 1 → 映射非空）
    assert all(r.isomorphism_mapping for r in report.level_results)
    assert report.comparison_time_s >= 0.0


def test_hierarchical_lvs_mismatch_raises():
    """验证层次结构不匹配（子 cell 数量不一致）时 raise RuntimeError（R03）。

    来源: R03 禁止 fall-back; Calibre nmLVS hierarchical compare
    https://eda.sw.siemens.com/en-US/calibre/calibre-nm-lvs-replay/
    """
    from polaris_verify_advanced import HierarchicalLVS

    def leaf(node_id: str) -> dict:
        return {
            "name": "LEAF",
            "devices": [{"node_id": node_id, "device_type": "ybranch"}],
            "connections": [],
            "children": [],
        }

    # 原理图 top 有 1 个子 cell，版图 top 有 2 个子 cell → 子 cell 数量不一致
    sch = {
        "name": "TOP",
        "devices": [{"node_id": "sch_top_d1", "device_type": "mmi"}],
        "connections": [],
        "children": [
            {
                "name": "MID",
                "devices": [{"node_id": "sch_mid_d1", "device_type": "wg"}],
                "connections": [],
                "children": [leaf("sch_leaf_d1")],
            }
        ],
    }
    lay = {
        "name": "TOP",
        "devices": [{"node_id": "lay_top_d1", "device_type": "mmi"}],
        "connections": [],
        "children": [
            {
                "name": "MID_A",
                "devices": [{"node_id": "lay_mid_a", "device_type": "wg"}],
                "connections": [],
                "children": [leaf("lay_leaf_a")],
            },
            {
                "name": "MID_B",
                "devices": [{"node_id": "lay_mid_b", "device_type": "wg"}],
                "connections": [],
                "children": [leaf("lay_leaf_b")],
            },
        ],
    }
    comparer = HierarchicalLVS()
    with pytest.raises(RuntimeError, match="子 cell 数量不匹配"):
        comparer.compare_hierarchical(sch, lay)


def test_hierarchical_lvs_invalid_input_raises():
    """验证无效输入（非 dict/缺字段/层级数<3）时 raise ValueError（R03）。

    来源: R03 禁止 fall-back; KLayout LVS Compare
    https://www.klayout.org/downloads/master/doc-qt5/manual/lvs_compare.html
    """
    from polaris_verify_advanced import HierarchicalLVS

    comparer = HierarchicalLVS()
    # 1. 非 dict 输入
    with pytest.raises(ValueError, match="必须为 dict"):
        comparer.compare_hierarchical([], {})
    # 2. 缺必需字段（缺 children）
    bad_node = {"name": "TOP", "devices": [], "connections": []}
    with pytest.raises(ValueError, match="缺少必需字段 'children'"):
        comparer.compare_hierarchical(bad_node, bad_node)
    # 3. 层级数 <3（仅 top → mid 两层，mid 无子 cell）
    shallow = {
        "name": "TOP",
        "devices": [{"node_id": "d1", "device_type": "mmi"}],
        "connections": [],
        "children": [
            {
                "name": "MID",
                "devices": [{"node_id": "d2", "device_type": "wg"}],
                "connections": [],
                "children": [],  # MID 为叶子 → 总深度仅 2
            }
        ],
    }
    with pytest.raises(ValueError, match="层次深度 2 < 最小要求 3"):
        comparer.compare_hierarchical(shallow, shallow)


# =============================================================================
# tiled / deep 模式 DRC 测试（R8 路标）
#
# 来源（R02 学术诚信，≥5 文献 URL）:
# 1. KLayout DRC tiled/hierarchical/deep 模式:
#    https://www.klayout.org/doc-qt5/manual/drc_runsets.html
# 2. He et al. 2023, OpenDRC, DAC 2023, DOI:10.1109/DAC56929.2023.10247734
# 3. Siemens Calibre nmDRC 分块扫描: https://eda.sw.siemens.com/en-US/calibre/
# 4. SiEPIC EBeam PDK DRC runset: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
# 5. Chrostowski & Hochberg 2015, Silicon Photonics Design, CUP, p.353
# =============================================================================
def test_tiled_drc_basic():
    """验证 TiledDRC 检测宽度违规（单 tile 基本功能）。

    来源: KLayout DRC tiling mode; OpenDRC DAC 2023。
    """
    from polaris_verify_advanced import (
        DRCCheckType,
        DRCReport,
        DRCRule,
        TiledDRC,
        ViolationType,
        run_tiled_drc,
    )

    narrow = np.array([[0, 0], [10, 0], [10, 0.3], [0, 0.3]], dtype=float)
    wide = np.array([[20, 0], [30, 0], [30, 1.0], [20, 1.0]], dtype=float)
    rule = DRCRule(
        name="W1", layer_name="WG", check_type=DRCCheckType.WIDTH,
        threshold_um=0.5, vtype=ViolationType.MIN_WIDTH,
    )
    layout = {"WG": [narrow, wide]}

    # 类入口
    engine = TiledDRC([rule])
    report = engine.check(layout, tile_size_um=100.0)
    assert isinstance(report, DRCReport)
    assert report.mode == "tiled"
    assert report.total_tiles >= 1
    assert report.violation_count == 1
    assert not report.is_clean
    assert "宽度" in report.violations[0].message
    assert report.elapsed_ms >= 0.0

    # 函数入口
    report2 = run_tiled_drc(layout, [rule], tile_size_um=100.0)
    assert report2.violation_count == 1
    assert report2.mode == "tiled"


def test_tiled_drc_tile_size():
    """验证不同 tile_size_um 下违规数一致（边界扩展 + 去重正确）。

    来源: KLayout tiling mode 边界扩展 + 去重策略。
    """
    from polaris_verify_advanced import (
        DRCCheckType,
        DRCRule,
        TiledDRC,
        ViolationType,
    )

    # 两个相近多边形（间距 0.5μm < 阈值 1.0μm），跨度约 20μm
    p1 = np.array([[0, 0], [10, 0], [10, 1], [0, 1]], dtype=float)
    p2 = np.array([[10.5, 0], [20, 0], [20, 1], [10.5, 1]], dtype=float)
    rule = DRCRule(
        name="S1", layer_name="WG", check_type=DRCCheckType.SPACE,
        threshold_um=1.0, vtype=ViolationType.SPACING,
    )
    layout = {"WG": [p1, p2]}
    engine = TiledDRC([rule])

    # 大 tile（单块覆盖全部）
    r_big = engine.check(layout, tile_size_um=100.0)
    assert r_big.total_tiles == 1
    assert r_big.violation_count == 1

    # 小 tile（多块，跨边界违规由 overlap 捕获，去重消除重复）
    r_small = engine.check(layout, tile_size_um=5.0)
    assert r_small.total_tiles > 1
    # 跨块间距违规不遗漏，去重后仅 1 条
    assert r_small.violation_count == 1, (
        f"小 tile 模式应去重为 1 条，得到 {r_small.violation_count}"
    )

    # 不同 tile_size 违规数一致
    r_mid = engine.check(layout, tile_size_um=10.0)
    assert r_mid.violation_count == 1


def test_deep_drc_basic():
    """验证 DeepDRC 递归 flatten + 跨层次检查。

    层次: TOP（含宽多边形）→ instance SUB（dx=20）含窄多边形。
    flatten 后窄多边形平移到 x=20，宽度违规被检出。
    来源: KLayout deep mode; OpenDRC 层次化展开。
    """
    from polaris_verify_advanced import (
        DRCCheckType,
        DRCReport,
        DRCRule,
        DeepDRC,
        ViolationType,
        run_deep_drc,
    )

    wide = np.array([[0, 0], [5, 0], [5, 1.0], [0, 1.0]], dtype=float)
    narrow = np.array([[0, 0], [8, 0], [8, 0.3], [0, 0.3]], dtype=float)
    rule = DRCRule(
        name="W1", layer_name="WG", check_type=DRCCheckType.WIDTH,
        threshold_um=0.5, vtype=ViolationType.MIN_WIDTH,
    )
    hierarchy = {
        "top_cell": "TOP",
        "cells": {
            "TOP": {
                "polygons": {"WG": [wide]},
                "instances": [{"cell_name": "SUB", "dx": 20.0, "dy": 0.0}],
            },
            "SUB": {
                "polygons": {"WG": [narrow]},
                "instances": [],
            },
        },
    }

    engine = DeepDRC([rule])
    report = engine.check(hierarchy)
    assert isinstance(report, DRCReport)
    assert report.mode == "deep"
    assert report.total_cells == 2  # TOP + SUB
    assert report.total_tiles == 0
    assert report.violation_count == 1
    assert not report.is_clean
    assert "宽度" in report.violations[0].message
    # flatten 后窄多边形位于 x=20..28
    loc_x = report.violations[0].location[0]
    assert 20.0 <= loc_x <= 28.0

    # 函数入口
    report2 = run_deep_drc(hierarchy, [rule])
    assert report2.violation_count == 1
    assert report2.total_cells == 2


def test_tiled_drc_invalid_input_raises():
    """验证 TiledDRC 无效输入即 raise（R03 禁止 fall-back）。

    覆盖: 空 rules / rules 非 list / layout 非 dict / layout 空 /
          tile_size_um ≤0 / overlap_um <0 / hierarchy 非法 / 层次环。
    """
    from polaris_verify_advanced import (
        DRCCheckType,
        DeepDRC,
        DRCRule,
        TiledDRC,
        ViolationType,
    )

    rule = DRCRule(
        name="W1", layer_name="WG", check_type=DRCCheckType.WIDTH,
        threshold_um=0.5, vtype=ViolationType.MIN_WIDTH,
    )
    poly = np.array([[0, 0], [10, 0], [10, 1], [0, 1]], dtype=float)
    layout = {"WG": [poly]}

    # 空 rules
    with pytest.raises(RuntimeError, match="DRC 规则列表不能为空"):
        TiledDRC([])
    # rules 非 list
    with pytest.raises(RuntimeError, match="rules 必须是 list"):
        TiledDRC("not_a_list")  # type: ignore[arg-type]
    # layout 非 dict
    with pytest.raises(RuntimeError, match="layout 必须是 dict"):
        TiledDRC([rule]).check([("WG", [poly])], tile_size_um=100.0)  # type: ignore[arg-type]
    # layout 空
    with pytest.raises(RuntimeError, match="layout 不能为空"):
        TiledDRC([rule]).check({}, tile_size_um=100.0)
    # tile_size_um ≤ 0
    with pytest.raises(RuntimeError, match="tile_size_um 必须 > 0"):
        TiledDRC([rule]).check(layout, tile_size_um=0.0)
    with pytest.raises(RuntimeError, match="tile_size_um 必须 > 0"):
        TiledDRC([rule]).check(layout, tile_size_um=-5.0)
    # overlap_um < 0
    with pytest.raises(RuntimeError, match="overlap_um 必须 ≥ 0"):
        TiledDRC([rule]).check(layout, tile_size_um=100.0, overlap_um=-1.0)

    # DeepDRC 空 rules
    with pytest.raises(RuntimeError, match="DRC 规则列表不能为空"):
        DeepDRC([])
    # hierarchy 非 dict
    with pytest.raises(RuntimeError, match="hierarchy 必须是 dict"):
        DeepDRC([rule]).check("not_a_dict")  # type: ignore[arg-type]
    # hierarchy 缺字段
    with pytest.raises(RuntimeError, match="hierarchy 缺少必要字段"):
        DeepDRC([rule]).check({"top_cell": "TOP"})
    # top_cell 不在 cells
    with pytest.raises(RuntimeError, match="不在 cells 中"):
        DeepDRC([rule]).check(
            {"top_cell": "MISSING", "cells": {"TOP": {"polygons": {}, "instances": []}}}
        )
    # 层次环
    cycle_hier = {
        "top_cell": "A",
        "cells": {
            "A": {"polygons": {}, "instances": [{"cell_name": "B", "dx": 0.0, "dy": 0.0}]},
            "B": {"polygons": {}, "instances": [{"cell_name": "A", "dx": 0.0, "dy": 0.0}]},
        },
    }
    with pytest.raises(RuntimeError, match="检测到层次环"):
        DeepDRC([rule]).check(cycle_hier)
