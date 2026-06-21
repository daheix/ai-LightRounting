"""网表解析与图构建测试（Task 8）。"""

from __future__ import annotations

import pytest

from polaris.engine.netlist import (
    build_graph,
    instantiate_devices,
    load_netlist,
    parse_netlist,
)

YAML_NETLIST = """
name: test
instances:
  wg1:
    component: strip_waveguide
    platform: SOI
  mmi1:
    component: mmi_1x2
    platform: SOI
  wg2:
    component: strip_waveguide
    platform: SOI
connections:
  - [wg1, out, mmi1, in]
  - [mmi1, out0, wg2, in]
"""


def test_parse_netlist_instances():
    net = parse_netlist(YAML_NETLIST)
    assert net.name == "test"
    assert len(net.instances) == 3
    assert net.instances[0].instance_id == "wg1"
    assert net.instances[0].component == "strip_waveguide"


def test_parse_netlist_connections():
    net = parse_netlist(YAML_NETLIST)
    assert len(net.connections) == 2
    assert net.connections[0].src_instance == "wg1"
    assert net.connections[0].src_port == "out"
    assert net.connections[0].dst_instance == "mmi1"
    assert net.connections[0].dst_port == "in"


def test_parse_netlist_from_dict():
    data = {
        "instances": {"d1": {"component": "mmi_1x2", "platform": "SOI"}},
        "connections": [],
    }
    net = parse_netlist(data)
    assert len(net.instances) == 1


def test_instantiate_devices():
    net = parse_netlist(YAML_NETLIST)
    devices = instantiate_devices(net)
    assert set(devices.keys()) == {"wg1", "mmi1", "wg2"}
    assert devices["wg1"].name == "strip_waveguide"


def test_instantiate_devices_preserves_process_node():
    """P1-3 修复（第7轮）：instantiate_devices 应保留 catalog 模板的 process_node。

    来源: docs/commercial_gap_analysis.md P1-3
    修复前：instantiate_devices 重建 Device 时未传递 process_node，导致
           从 catalog 模板实例化后丢失工艺节点信息。
    """
    net = parse_netlist(YAML_NETLIST)
    devices = instantiate_devices(net)
    # SOI 平台默认工艺节点 = "220nm SOI"（catalog 自动填充）
    assert devices["wg1"].process_node == "220nm SOI"
    assert devices["mmi1"].process_node == "220nm SOI"
    assert devices["wg2"].process_node == "220nm SOI"


def test_instantiate_devices_process_node_multi_platform():
    """P1-3：多平台实例化后 process_node 正确（SiN/InP/LNOI）。

    网表 component 字段对应器件的 name（非 device_id），
    catalog.get(component, platform=...) 按 平台::name 检索。
    """
    yaml_multi = """
name: multi
instances:
  wg_soi:
    component: strip_waveguide
    platform: SOI
  wg_sin:
    component: sin_waveguide_strip
    platform: SiN
  wg_inp:
    component: inp_waveguide
    platform: InP
  wg_lnoi:
    component: lnoi_waveguide
    platform: LNOI
connections: []
"""
    net = parse_netlist(yaml_multi)
    devices = instantiate_devices(net)
    assert devices["wg_soi"].process_node == "220nm SOI"
    assert devices["wg_sin"].process_node == "SiN TriPleX"
    assert devices["wg_inp"].process_node == "InP generic"
    assert devices["wg_lnoi"].process_node == "LNOI X-cut"


def test_instantiate_with_settings():
    data = {
        "instances": {
            "wg1": {
                "component": "strip_waveguide",
                "platform": "SOI",
                "settings": {"length_um": 50.0},
            }
        },
        "connections": [],
    }
    net = parse_netlist(data)
    devices = instantiate_devices(net)
    assert devices["wg1"].params["length_um"] == 50.0


def test_build_graph():
    net = parse_netlist(YAML_NETLIST)
    devices = instantiate_devices(net)
    g = build_graph(net, devices)
    assert len(g.nodes) == 3
    assert len(g.edges) == 2
    assert "device" in g.nodes["wg1"]


def test_load_netlist_full():
    net, devices, g = load_netlist(YAML_NETLIST)
    assert len(net.instances) == 3
    assert len(devices) == 3
    assert len(g.nodes) == 3


def test_parse_invalid_connection_raises():
    data = {
        "instances": {"d1": {"component": "mmi_1x2", "platform": "SOI"}},
        "connections": [["only", "two"]],
    }
    with pytest.raises(ValueError):
        parse_netlist(data)


def test_parse_dict_connection_format():
    data = {
        "instances": {
            "wg1": {"component": "strip_waveguide", "platform": "SOI"},
            "wg2": {"component": "strip_waveguide", "platform": "SOI"},
        },
        "connections": [{"src": "wg1", "src_port": "out", "dst": "wg2", "dst_port": "in"}],
    }
    net = parse_netlist(data)
    assert len(net.connections) == 1
    assert net.connections[0].src_instance == "wg1"
