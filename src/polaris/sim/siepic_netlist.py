"""SiEPIC JSON 网表解析器（R02 步骤 5）。

解析 SiEPIC-Tools KLayout 导出的 JSON 网表格式，自动转换为 PoLaRIS
内部网表格式，可直接传给 CircuitSimulator.simulate() 进行仿真。

SiEPIC JSON 格式（实际格式，基于 /workspace/data/benchmarks/siepic_netlists/）:
    {
      "name": "MZI1",
      "platform": "SOI",
      "devices": [
        {"name": "wg1", "type": "waveguide", "ports": [...], "params": {...}},
        ...
      ],
      "connections": [
        ["device1", "pin1", "device2", "pin2"],
        ...
      ]
    }

来源:
- SiEPIC-Tools: https://github.com/SiEPIC/SiEPIC-Tools
- SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- R02.md §6.3 创新点 3: SiEPIC JSON 网表自动解析


## 补充文献（R02 学术诚信补齐）
- Chrostowski & Hochberg, "Silicon Photonics Design", CUP 2015, ISBN 978-1-107-08345-6: https://www.cambridge.org/9781107083456
- gdsfactory PDK 文档: https://gdsfactory.github.io/gdsfactory/notebooks/09_pdk_import.html
- Luceda IPKISS: https://www.lucedaphotonics.com/en/products/ipkiss
"""

from __future__ import annotations

import json
from pathlib import Path

from polaris.sim.models import (
    crossing_s,
    directional_coupler_s,
    grating_coupler_s,
    mmi_1x2_s,
    mmi_2x2_s,
    ring_resonator_s,
    terminator_s,
    waveguide_s,
    y_branch_s,
)
from polaris.sim.models_extended import half_ring_s, taper_s
from polaris.sim.types import ModelFunc

# SiEPIC 器件类型到 PoLaRIS 模型的映射表
# 来源: SiEPIC EBeam PDK 器件清单
# https://github.com/SiEPIC/SiEPIC_EBeam_PDK
SIEPIC_TYPE_MAP: dict[str, ModelFunc] = {
    "waveguide": waveguide_s,
    "waveguide_bump$1": waveguide_s,  # 波导凸起变体，本质是波导
    "y_branch": y_branch_s,
    "directional_coupler": directional_coupler_s,
    "DirectionalCoupler_SeriesRings$1": directional_coupler_s,  # 串联环定向耦合器
    "ring_resonator": ring_resonator_s,
    "ebeam_dc_halfring_straight": ring_resonator_s,  # 半环定向耦合器
    "ebeam_dc_halfring_straight$1": ring_resonator_s,  # 半环定向耦合器变体
    "half_ring": half_ring_s,
    "mmi_1x2": mmi_1x2_s,
    "mmi_2x2": mmi_2x2_s,
    "grating_coupler": grating_coupler_s,
    "grating_coupler_1d": grating_coupler_s,
    "crossing": crossing_s,
    "ebeam_crossing4": crossing_s,
    "terminator": terminator_s,
    "taper": taper_s,
}

# SiEPIC 端口名到 PoLaRIS 标准端口名的映射
# 来源: SiEPIC EBeam PDK 端口命名规范
SIEPIC_PORT_MAP: dict[str, dict[str, str]] = {
    "waveguide": {"pin1": "in", "pin2": "out"},
    "y_branch": {"pin1": "port_1", "pin2": "port_2", "pin3": "port_3"},
    "directional_coupler": {
        "pin1": "in1",
        "pin2": "in2",
        "pin3": "out1",
        "pin4": "out2",
    },
    "ring_resonator": {
        "pin1": "in",
        "pin2": "through",
        "pin3": "drop",
        "pin4": "add",
    },
    "half_ring": {"pin1": "in", "pin2": "through"},
    "mmi_1x2": {"pin1": "in", "pin2": "out1", "pin3": "out2"},
    "mmi_2x2": {"pin1": "in1", "pin2": "in2", "pin3": "out1", "pin4": "out2"},
    "grating_coupler": {"pin1": "fiber", "pin2": "waveguide"},
    "grating_coupler_1d": {"pin1": "fiber", "pin2": "waveguide"},
    "crossing": {"pin1": "in1", "pin2": "in2", "pin3": "out1", "pin4": "out2"},
    "ebeam_crossing4": {"pin1": "in1", "pin2": "in2", "pin3": "out1", "pin4": "out2"},
    "terminator": {"pin1": "in"},
    "taper": {"pin1": "in", "pin2": "out"},
}


def _map_port(device_type: str, pin: str) -> str:
    """将 SiEPIC 端口名映射为 PoLaRIS 标准端口名。

    Args:
        device_type: SiEPIC 器件类型。
        pin: SiEPIC 端口名（如 "pin1"）。

    Returns:
        PoLaRIS 标准端口名（如 "in"），未映射时返回原值。
    """
    port_map = SIEPIC_PORT_MAP.get(device_type, {})
    return port_map.get(pin, pin)


def _map_device_type(siepic_type: str) -> str:
    """将 SiEPIC 器件类型映射为 PoLaRIS 模型名。

    Args:
        siepic_type: SiEPIC 器件类型名。

    Returns:
        PoLaRIS 模型名，未映射时返回原值。

    Raises:
        KeyError: 器件类型未在映射表中时告警退出（禁止 fall-back）。
    """
    if siepic_type in SIEPIC_TYPE_MAP:
        return siepic_type
    # 未知类型告警退出（禁止 fall-back，规则 14.1）
    msg = (
        f"未知 SiEPIC 器件类型 '{siepic_type}'，"
        f"请在 SIEPIC_TYPE_MAP 中添加映射。禁止 fall-back（规则 14.1）。"
    )
    raise KeyError(msg)


def _load_siepic_json(path: str | Path) -> dict:
    """加载并校验 SiEPIC JSON 根节点结构。

    Args:
        path: JSON 文件路径。

    Returns:
        解析后的 JSON 字典。

    Raises:
        FileNotFoundError: 文件不存在。
        ValueError: JSON 根节点非字典或缺少 'devices' 字段。
    """
    path = Path(path)
    if not path.exists():
        msg = f"SiEPIC 网表文件不存在: {path}"
        raise FileNotFoundError(msg)
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        msg = f"SiEPIC JSON 根节点必须是字典，得到 {type(data).__name__}"
        raise ValueError(msg)
    if "devices" not in data:
        msg = "SiEPIC JSON 缺少 'devices' 字段"
        raise ValueError(msg)
    return data


def _parse_siepic_devices(
    devices_data: list,
) -> tuple[dict[str, str], dict[str, str], dict[str, set[str]]]:
    """解析 SiEPIC 器件列表。

    Returns:
        (instances, device_types, device_ports) 三元组。
        - instances: {name: model_name}
        - device_types: {name: siepic_type}
        - device_ports: {name: set(pin)}
    """
    instances: dict[str, str] = {}
    device_types: dict[str, str] = {}
    device_ports: dict[str, set[str]] = {}
    for device in devices_data:
        name = device["name"]
        dev_type = device["type"]
        instances[name] = _map_device_type(dev_type)
        device_types[name] = dev_type
        ports = set()
        for port_entry in device.get("ports", []):
            if isinstance(port_entry, list) and len(port_entry) > 0:
                ports.add(port_entry[0])
        device_ports[name] = ports
    return instances, device_types, device_ports


def _parse_siepic_connections(
    connections_data: list,
    device_types: dict[str, str],
) -> tuple[list[tuple[str, str]], set[str]]:
    """解析 SiEPIC 连接列表并映射端口名。

    Returns:
        (connections, connected_ports) 二元组。
        - connections: [(inst1.port1, inst2.port2), ...]
        - connected_ports: 已连接端口引用集合 {dev.pin}。
    """
    connections: list[tuple[str, str]] = []
    connected_ports: set[str] = set()
    for conn in connections_data:
        if len(conn) != 4:
            msg = f"连接格式错误，期望 [dev1, pin1, dev2, pin2]，得到 {conn}"
            raise ValueError(msg)
        dev1, pin1, dev2, pin2 = conn
        port1 = _map_port(device_types[dev1], pin1)
        port2 = _map_port(device_types[dev2], pin2)
        connections.append((f"{dev1}.{port1}", f"{dev2}.{port2}"))
        connected_ports.add(f"{dev1}.{pin1}")
        connected_ports.add(f"{dev2}.{pin2}")
    return connections, connected_ports


def _identify_external_ports(
    device_types: dict[str, str],
    device_ports: dict[str, set[str]],
    connected_ports: set[str],
) -> dict[str, str]:
    """识别未连接的外部端口。

    Returns:
        {external_name: instance.port} 外部端口字典。
    """
    ports: dict[str, str] = {}
    ext_idx = 0
    for dev_name, dev_type in device_types.items():
        for pin in device_ports[dev_name]:
            ref = f"{dev_name}.{pin}"
            if ref not in connected_ports:
                port_name = _map_port(dev_type, pin)
                ports[f"ext_{ext_idx}"] = f"{dev_name}.{port_name}"
                ext_idx += 1
    return ports


def parse_siepic_json(path: str | Path) -> dict:
    """解析 SiEPIC JSON 网表文件。

    读取 SiEPIC-Tools KLayout 导出的 JSON 格式网表，转换为 PoLaRIS
    内部网表格式。

    Args:
        path: JSON 文件路径。

    Returns:
        PoLaRIS 网表字典 {instances, connections, ports, meta}:
        - instances: {instance_name: model_name}
        - connections: [(inst1.port1, inst2.port2), ...]
        - ports: {external_name: instance.port}（外部端口，未连接的端口）
        - meta: 元数据 {name, platform, source}

    Raises:
        FileNotFoundError: 文件不存在时告警退出。
        KeyError: 器件类型未映射时告警退出（禁止 fall-back）。
        ValueError: JSON 格式错误时告警退出。
    """
    data = _load_siepic_json(path)
    instances, device_types, device_ports = _parse_siepic_devices(data["devices"])
    connections, connected_ports = _parse_siepic_connections(
        data.get("connections", []), device_types
    )
    ports = _identify_external_ports(device_types, device_ports, connected_ports)
    meta = {
        "name": data.get("name", "unknown"),
        "platform": data.get("platform", "SOI"),
        "source": data.get("source", ""),
    }
    return {
        "instances": instances,
        "connections": connections,
        "ports": ports,
        "meta": meta,
    }


def parse_siepic_json_with_models(path: str | Path) -> dict:
    """解析 SiEPIC JSON 网表并返回带模型函数的网表。

    与 parse_siepic_json 不同，此函数返回的 instances 直接包含模型函数，
    可用于 CircuitSimulator 直接仿真。

    Args:
        path: JSON 文件路径。

    Returns:
        SAX 网表 {instances: {name: ModelFunc}, connections, ports, meta}。
    """
    netlist = parse_siepic_json(path)
    instances = {
        name: SIEPIC_TYPE_MAP[model_name]
        for name, model_name in netlist["instances"].items()
    }
    return {
        "instances": instances,
        "connections": netlist["connections"],
        "ports": netlist["ports"],
        "meta": netlist["meta"],
    }
