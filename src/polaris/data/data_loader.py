"""外部数据源加载器。

支持从 LiDAR PIC IR (YAML)、PICBench (YAML/Python)、
GDSFactory (*.pic.yml) 等格式加载光子电路训练数据。

数据来源:
- LiDAR PIC IR: https://github.com/ScopeX-ASU/LiDAR
- PICBench: https://github.com/PICDA/PICBench
- GDSFactory: https://gdsfactory.github.io/gdsfactory/
- PhIDO: https://github.com/JPPhotonics/PhIDO-Release
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import yaml

from polaris.data.specs import CircuitSpec, DeviceSpec

logger = logging.getLogger(__name__)


def _parse_pic_ir_ports(
    inst: dict,
) -> list[tuple[str, float, float, str]]:
    """解析 PIC IR 实例的端口列表。"""
    ports: list[tuple[str, float, float, str]] = []
    for p in inst.get("ports", []):
        pname = p.get("name", "o1")
        px = float(p.get("x", 0.0))
        py = float(p.get("y", 0.0))
        pdir = p.get("direction", "E")
        ports.append((pname, px, py, pdir))
    return ports


def _parse_pic_ir_nets(
    raw: dict,
) -> list[tuple[str, str, str, str]]:
    """解析 PIC IR 网络连接列表。

    LiDAR PIC IR 的 nets 字段有两种可能结构：
    - dict: {net_name: [src_port_ref, dst_port_ref]}（实际基准文件格式）
    - list: [{src, dst}, ...]（早期格式兼容）
    """
    nets = raw.get("nets", [])
    if isinstance(nets, dict):
        return _parse_pic_ir_nets_dict(nets)
    if isinstance(nets, list):
        return _parse_pic_ir_nets_list(nets)
    return []


def _parse_pic_ir_nets_dict(
    nets: dict,
) -> list[tuple[str, str, str, str]]:
    """解析 PIC IR nets 字段为 dict 格式的连接。

    Args:
        nets: {net_name: endpoints} 字典，endpoints 可为 list/tuple 或 dict。

    Returns:
        连接列表 [(src_dev, src_port, dst_dev, dst_port), ...]。
    """
    connections: list[tuple[str, str, str, str]] = []
    for _net_name, endpoints in nets.items():
        conn = _parse_pic_ir_endpoints(endpoints)
        if conn is not None:
            connections.append(conn)
    return connections


def _parse_pic_ir_endpoints(endpoints: object) -> tuple[str, str, str, str] | None:
    """解析单个 net 的 endpoints（list/tuple 或 dict）。

    Args:
        endpoints: net 端点对象，可为 [src_ref, dst_ref] 列表或
            {src, dst} 字典。

    Returns:
        (src_dev, src_port, dst_dev, dst_port) 或 None（解析失败）。
    """
    if isinstance(endpoints, (list, tuple)) and len(endpoints) >= 2:
        src_ref = str(endpoints[0])
        dst_ref = str(endpoints[1])
    elif isinstance(endpoints, dict):
        src_ref = str(endpoints.get("src", endpoints.get("source", "")))
        dst_ref = str(endpoints.get("dst", endpoints.get("destination", "")))
    else:
        return None
    src_dev, src_port = _split_port_ref(src_ref)
    dst_dev, dst_port = _split_port_ref(dst_ref)
    if src_dev and dst_dev:
        return (src_dev, src_port, dst_dev, dst_port)
    return None


def _parse_pic_ir_nets_list(
    nets: list,
) -> list[tuple[str, str, str, str]]:
    """解析 PIC IR nets 字段为 list 格式的连接。

    Args:
        nets: [{src, dst}, ...] 列表，src/dst 可为 "dev,port" 字符串。

    Returns:
        连接列表 [(src_dev, src_port, dst_dev, dst_port), ...]。
    """
    connections: list[tuple[str, str, str, str]] = []
    for net in nets:
        if not isinstance(net, dict):
            continue
        src = net.get("src", net.get("source", ""))
        dst = net.get("dst", net.get("destination", ""))
        if "," in src and "," in dst:
            src_parts = src.split(",")
            dst_parts = dst.split(",")
            if len(src_parts) == 2 and len(dst_parts) == 2:
                connections.append((src_parts[0], src_parts[1], dst_parts[0], dst_parts[1]))
    return connections


def load_pic_ir(path: str | Path) -> CircuitSpec:
    """加载 LiDAR PIC IR 格式 (YAML)。

    PIC IR 是 Apollo/LiDAR 定义的光子电路中间表示格式，
    包含 instances、nets、constraints 等字段。

    来源: https://github.com/ScopeX-ASU/LiDAR

    Args:
        path: PIC IR YAML 文件路径。

    Returns:
        CircuitSpec。
    """
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    devices = _parse_pic_ir_instances(raw.get("instances", {}))
    connections = _parse_pic_ir_nets(raw)
    canvas = raw.get("canvas", raw.get("die", {}))
    cw = float(canvas.get("width", canvas.get("xsize", 1000.0)))
    ch = float(canvas.get("height", canvas.get("ysize", 1000.0)))
    return CircuitSpec(
        name=raw.get("name", Path(path).stem),
        devices=devices,
        connections=connections,
        canvas_w=cw,
        canvas_h=ch,
    )


def _parse_pic_ir_instances(instances: dict | list) -> list[DeviceSpec]:
    """解析 PIC IR instances 字段（dict 或 list）。

    Args:
        instances: instances 字段，可为 {name: inst_dict} 或 [inst_dict, ...]。

    Returns:
        DeviceSpec 列表。
    """
    if isinstance(instances, dict):
        items = instances.items()
    else:
        items = [(inst.get("name", "unknown"), inst) for inst in instances]

    devices: list[DeviceSpec] = []
    for name, inst in items:
        if not isinstance(inst, dict):
            continue
        if not name or name == "unknown":
            name = inst.get("name", "unknown")
        cell = inst.get("cell_type", inst.get("cell", inst.get("component", "unknown")))
        settings = inst.get("settings", {})
        w = float(inst.get("width", inst.get("xsize", settings.get("length", 10.0))))
        h = float(inst.get("height", inst.get("ysize", settings.get("gap", 10.0))))
        ports = _parse_pic_ir_ports(inst)
        devices.append(
            DeviceSpec(name=name, device_type=cell, width_um=w, height_um=h, ports=ports)
        )
    return devices


def load_gdsfactory_yaml(path: str | Path) -> CircuitSpec:
    """加载 GDSFactory *.pic.yml 格式。

    GDSFactory YAML 网表格式包含 instances、placements、
    connections、routes、ports 等字段。

    来源: https://gdsfactory.github.io/gdsfactory/

    Args:
        path: GDSFactory YAML 文件路径。

    Returns:
        CircuitSpec。
    """
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    devices: list[DeviceSpec] = []
    connections: list[tuple[str, str, str, str]] = []

    for name, inst in raw.get("instances", {}).items():
        if not isinstance(inst, dict):
            continue
        component = inst.get("component", "unknown")
        settings = inst.get("settings", {})
        w = float(settings.get("length", settings.get("width", 10.0)))
        h = float(settings.get("gap", 10.0))
        devices.append(DeviceSpec(name=name, device_type=component, width_um=w, height_um=h))

    connections = _parse_gdsfactory_connections(raw)

    return CircuitSpec(
        name=raw.get("name", Path(path).stem),
        devices=devices,
        connections=connections,
    )


def load_picbench(path: str | Path) -> CircuitSpec:
    """加载 PICBench 格式 (YAML/JSON)。

    PICBench 是 HKUST(GZ) 定义的光子电路设计基准，
    包含自然语言描述和仿真就绪网表。

    来源: https://github.com/PICDA/PICBench

    Args:
        path: PICBench YAML/JSON 文件路径。

    Returns:
        CircuitSpec。
    """
    p = Path(path)
    if p.suffix == ".json":
        raw = json.loads(p.read_text(encoding="utf-8"))
    else:
        raw = yaml.safe_load(p.read_text(encoding="utf-8"))

    data_section = raw.get("data", {})
    if isinstance(data_section, dict) and "netlist" in data_section:
        devices, connections = _parse_picbench_netlist_section(data_section)
    else:
        devices, connections = _parse_picbench_components_section(raw)

    return CircuitSpec(
        name=raw.get("name", raw.get("id", p.stem)),
        devices=devices,
        connections=connections,
    )


def _parse_picbench_netlist_section(
    data_section: dict,
) -> tuple[list[DeviceSpec], list[tuple[str, str, str, str]]]:
    """解析 PICBench data.netlist 嵌套结构。

    Args:
        data_section: PICBench data 字段（含 netlist 键）。

    Returns:
        (devices, connections) 元组。
    """
    netlist = data_section.get("netlist", {})
    devices = _parse_picbench_instances(netlist.get("instances", {}))
    connections = _parse_picbench_conns(netlist.get("connections", {}))
    return devices, connections


def _parse_picbench_instances(
    instances: dict | list,
) -> list[DeviceSpec]:
    """解析 PICBench instances 字段（dict 或 list）。

    Args:
        instances: instances 字段，可为 {name: comp_ref} 或 [inst_dict, ...]。

    Returns:
        DeviceSpec 列表。
    """
    devices: list[DeviceSpec] = []
    if isinstance(instances, dict):
        for name, comp_ref in instances.items():
            ctype = comp_ref if isinstance(comp_ref, str) else str(comp_ref)
            devices.append(DeviceSpec(name=name, device_type=ctype, width_um=10.0, height_um=10.0))
    elif isinstance(instances, list):
        for inst in instances:
            if not isinstance(inst, dict):
                continue
            name = inst.get("name", "unknown")
            ctype = inst.get("type", inst.get("component", "unknown"))
            devices.append(DeviceSpec(name=name, device_type=ctype, width_um=10.0, height_um=10.0))
    return devices


def _parse_picbench_conns(
    conns: dict | list,
) -> list[tuple[str, str, str, str]]:
    """解析 PICBench connections 字段（dict 或 list）。

    Args:
        conns: connections 字段，可为 {src_ref: dst_ref} 或 [conn_dict, ...]。

    Returns:
        连接列表 [(src_dev, src_port, dst_dev, dst_port), ...]。
    """
    connections: list[tuple[str, str, str, str]] = []
    if isinstance(conns, dict):
        for src_ref, dst_ref in conns.items():
            src_dev, src_port = _split_port_ref(str(src_ref))
            dst_dev, dst_port = _split_port_ref(str(dst_ref))
            if src_dev and dst_dev:
                connections.append((src_dev, src_port, dst_dev, dst_port))
    elif isinstance(conns, list):
        for conn in conns:
            pair = _extract_conn_pair(conn)
            if pair is None:
                continue
            src, dst = pair
            src_dev, src_port = _split_port_ref(str(src))
            dst_dev, dst_port = _split_port_ref(str(dst))
            if src_dev and dst_dev:
                connections.append((src_dev, src_port, dst_dev, dst_port))
    return connections


def _extract_conn_pair(conn: object) -> tuple[str, str] | None:
    """从单个连接对象提取 (src, dst) 对。

    Args:
        conn: 连接对象，可为 dict、list/tuple。

    Returns:
        (src, dst) 字符串对，或 None（无法解析）。
    """
    if isinstance(conn, dict):
        src = conn.get("source", conn.get("src", ""))
        dst = conn.get("destination", conn.get("dst", ""))
        return str(src), str(dst)
    if isinstance(conn, (list, tuple)) and len(conn) >= 2:
        return str(conn[0]), str(conn[1])
    return None


def _parse_picbench_components_section(
    raw: dict,
) -> tuple[list[DeviceSpec], list[tuple[str, str, str, str]]]:
    """解析 PICBench 顶层 components/connections 结构（无 data.netlist 嵌套）。

    Args:
        raw: PICBench 原始字典。

    Returns:
        (devices, connections) 元组。
    """
    devices: list[DeviceSpec] = []
    for comp in raw.get("components", raw.get("devices", [])):
        if not isinstance(comp, dict):
            continue
        name = comp.get("name", "unknown")
        ctype = comp.get("type", comp.get("component", "unknown"))
        w = float(comp.get("width", comp.get("xsize", 10.0)))
        h = float(comp.get("height", comp.get("ysize", 10.0)))
        devices.append(DeviceSpec(name=name, device_type=ctype, width_um=w, height_um=h))

    connections: list[tuple[str, str, str, str]] = []
    for conn in raw.get("connections", raw.get("nets", [])):
        pair = _extract_conn_pair(conn)
        if pair is None:
            continue
        src, dst = pair
        src_dev, src_port = _split_port_ref(str(src))
        dst_dev, dst_port = _split_port_ref(str(dst))
        if src_dev and dst_dev:
            connections.append((src_dev, src_port, dst_dev, dst_port))
    return devices, connections


def load_phido(path: str | Path) -> CircuitSpec:
    """加载 PhIDO 格式 (YAML/JSON)。

    PhIDO 是 U of Toronto/GDSFactory/MIT 定义的
    光子设计自动化测试基准。

    来源: https://github.com/JPPhotonics/PhIDO-Release

    Args:
        path: PhIDO YAML/JSON 文件路径。

    Returns:
        CircuitSpec。
    """
    p = Path(path)
    if p.suffix == ".json":
        raw = json.loads(p.read_text(encoding="utf-8"))
    else:
        raw = yaml.safe_load(p.read_text(encoding="utf-8"))

    devices: list[DeviceSpec] = []
    connections: list[tuple[str, str, str, str]] = []

    for inst in raw.get("instances", raw.get("components", [])):
        if isinstance(inst, dict):
            name = inst.get("name", "unknown")
            ctype = inst.get("component", inst.get("type", "unknown"))
            w = float(inst.get("width", inst.get("xsize", 10.0)))
            h = float(inst.get("height", inst.get("ysize", 10.0)))
            devices.append(DeviceSpec(name=name, device_type=ctype, width_um=w, height_um=h))

    for conn in raw.get("connections", raw.get("nets", [])):
        if isinstance(conn, dict):
            src = conn.get("source", conn.get("src", ""))
            dst = conn.get("destination", conn.get("dst", ""))
        else:
            continue
        src_dev, src_port = _split_port_ref(str(src))
        dst_dev, dst_port = _split_port_ref(str(dst))
        if src_dev and dst_dev:
            connections.append((src_dev, src_port, dst_dev, dst_port))

    return CircuitSpec(
        name=raw.get("name", raw.get("design_id", p.stem)),
        devices=devices,
        connections=connections,
    )


def _split_port_ref(ref: str) -> tuple[str, str]:
    """拆分端口引用 'device,port' → (device, port)。"""
    if "," in ref:
        parts = ref.split(",", 1)
        return parts[0].strip(), parts[1].strip()
    if ":" in ref:
        parts = ref.split(":", 1)
        return parts[0].strip(), parts[1].strip()
    return ref.strip(), "o1"


def _parse_gdsfactory_connections(
    raw: dict,
) -> list[tuple[str, str, str, str]]:
    """解析 GDSFactory 连接。

    GDSFactory 连接有三种可能结构：
    - dict: {"src_dev,src_port": "dst_dev,dst_port"}（实际基准文件格式）
    - list[dict]: [{source, destination}, ...]
    - list[str]: ["src,dst", ...]

    另外路由信息在 routes.optical.links（dict 格式）。
    """
    connections = _parse_gdsfactory_conns_field(raw.get("connections", []))
    connections.extend(_parse_gdsfactory_routes_field(raw.get("routes", {})))
    return connections


def _parse_gdsfactory_conns_field(
    raw_conns: dict | list,
) -> list[tuple[str, str, str, str]]:
    """解析 GDSFactory connections 字段。

    Args:
        raw_conns: connections 字段，可为 dict 或 list。

    Returns:
        连接列表 [(src_dev, src_port, dst_dev, dst_port), ...]。
    """
    connections: list[tuple[str, str, str, str]] = []
    if isinstance(raw_conns, dict):
        for src_ref, dst_ref in raw_conns.items():
            src_dev, src_port = _split_port_ref(str(src_ref))
            dst_dev, dst_port = _split_port_ref(str(dst_ref))
            if src_dev and dst_dev:
                connections.append((src_dev, src_port, dst_dev, dst_port))
    elif isinstance(raw_conns, list):
        for conn in raw_conns:
            pair = _extract_gdsfactory_conn_pair(conn)
            if pair is None:
                continue
            src, dst = pair
            src_dev, src_port = _split_port_ref(str(src))
            dst_dev, dst_port = _split_port_ref(str(dst))
            if src_dev and dst_dev:
                connections.append((src_dev, src_port, dst_dev, dst_port))
    return connections


def _extract_gdsfactory_conn_pair(conn: object) -> tuple[str, str] | None:
    """从单个 GDSFactory 连接对象提取 (src, dst) 对。

    Args:
        conn: 连接对象，可为 dict 或 "src,dst" 字符串。

    Returns:
        (src, dst) 字符串对，或 None（无法解析）。
    """
    if isinstance(conn, dict):
        src = conn.get("source", conn.get("src", ""))
        dst = conn.get("destination", conn.get("dst", ""))
        return str(src), str(dst)
    if isinstance(conn, str):
        parts = conn.split(",")
        src = parts[0] if len(parts) >= 1 else ""
        dst = parts[1] if len(parts) >= 2 else ""
        return src, dst
    return None


def _parse_gdsfactory_routes_field(
    routes: dict,
) -> list[tuple[str, str, str, str]]:
    """解析 GDSFactory routes.optical.links 字段。

    Args:
        routes: routes 字段，期望为 {route_name: {links: {src: dst}}}。

    Returns:
        连接列表 [(src_dev, src_port, dst_dev, dst_port), ...]。
    """
    connections: list[tuple[str, str, str, str]] = []
    if not isinstance(routes, dict):
        return connections
    for route_data in routes.values():
        if not isinstance(route_data, dict):
            continue
        links = route_data.get("links", {})
        if not isinstance(links, dict):
            continue
        for src_ref, dst_ref in links.items():
            src_dev, src_port = _split_port_ref(str(src_ref))
            dst_dev, dst_port = _split_port_ref(str(dst_ref))
            if src_dev and dst_dev:
                conn = (src_dev, src_port, dst_dev, dst_port)
                if conn not in connections:
                    connections.append(conn)
    return connections


def load_directory(
    path: str | Path,
    fmt: str = "auto",
) -> list[CircuitSpec]:
    """批量加载目录下的所有电路文件。

    Args:
        path: 目录路径。
        fmt: 格式（auto/pic_ir/gdsfactory/picbench/phido）。

    Returns:
        CircuitSpec 列表。
    """
    p = Path(path)
    if not p.exists():
        logger.error("数据目录不存在: %s", path)
        return []

    circuits: list[CircuitSpec] = []
    for fp in sorted(p.glob("*.y*ml")):
        try:
            c = _load_file(fp, fmt)
            circuits.append(c)
        except Exception as e:
            logger.warning("加载失败: %s (%s)", fp, e)

    for fp in sorted(p.glob("*.json")):
        try:
            c = _load_file(fp, fmt)
            circuits.append(c)
        except Exception as e:
            logger.warning("加载失败: %s (%s)", fp, e)

    logger.info("从 %s 加载了 %d 个电路", path, len(circuits))
    return circuits


def _load_file(fp: Path, fmt: str) -> CircuitSpec:
    """根据格式加载单个文件。"""
    if fmt == "pic_ir":
        return load_pic_ir(fp)
    if fmt == "gdsfactory":
        return load_gdsfactory_yaml(fp)
    if fmt == "picbench":
        return load_picbench(fp)
    if fmt == "phido":
        return load_phido(fp)
    # auto: 尝试所有格式
    for loader in [load_pic_ir, load_gdsfactory_yaml, load_picbench, load_phido]:
        try:
            return loader(fp)
        except Exception:
            continue
    raise ValueError(f"无法识别文件格式: {fp}")


__all__ = [
    "load_pic_ir",
    "load_gdsfactory_yaml",
    "load_picbench",
    "load_phido",
    "load_directory",
]
