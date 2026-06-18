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
        "connections": [
            {"src": "wg1", "src_port": "out", "dst": "wg2", "dst_port": "in"}
        ],
    }
    net = parse_netlist(data)
    assert len(net.connections) == 1
    assert net.connections[0].src_instance == "wg1"
