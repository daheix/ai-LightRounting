"""GDSFactory / PICBench / PhIDO 格式加载器。

支持三种外部数据格式：
- GDSFactory (*.pic.yml): https://gdsfactory.github.io/gdsfactory/
- PICBench (YAML/JSON): https://github.com/PICDA/PICBench
- PhIDO (YAML/JSON): https://github.com/JPPhotonics/PhIDO-Release

R03 异常处理设计: 所有数据格式错误（非 dict 实例/连接、无法解析的对象）
均 raise TypeError/ValueError，禁止静默跳过或返回 None，确保数据完整性。

异常处理最佳实践文献:
- Python 官方异常处理: https://docs.python.org/3/tutorial/errors.html
- PEP 8 异常设计: https://peps.python.org/pep-0008/#exception-handling
- Real Python try/except: https://realpython.com/python-exceptions/
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import yaml

from polaris_nn.data._common import split_port_ref
from polaris_nn.data.specs import CircuitSpec, DeviceSpec

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# GDSFactory
# ---------------------------------------------------------------------------


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
            # R03: 实例格式错误，禁止静默跳过
            raise TypeError(
                f"GDSFactory 实例 '{name}' 必须为 dict，"
                f"实际为 {type(inst).__name__}: {inst!r}"
            )
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
            src_dev, src_port = split_port_ref(str(src_ref))
            dst_dev, dst_port = split_port_ref(str(dst_ref))
            if src_dev and dst_dev:
                connections.append((src_dev, src_port, dst_dev, dst_port))
    elif isinstance(raw_conns, list):
        for conn in raw_conns:
            # _extract_gdsfactory_conn_pair 已改为 raise，无需 None 检查（R03）
            src, dst = _extract_gdsfactory_conn_pair(conn)
            src_dev, src_port = split_port_ref(str(src))
            dst_dev, dst_port = split_port_ref(str(dst))
            if src_dev and dst_dev:
                connections.append((src_dev, src_port, dst_dev, dst_port))
    return connections


def _extract_gdsfactory_conn_pair(conn: object) -> tuple[str, str]:
    """从单个 GDSFactory 连接对象提取 (src, dst) 对。

    Args:
        conn: 连接对象，可为 dict 或 "src,dst" 字符串。

    Returns:
        (src, dst) 字符串对。

    Raises:
        TypeError: 连接对象格式不支持（非 dict/str）。
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
    # R03: 不支持的连接对象格式，禁止静默返回 None
    raise TypeError(
        f"不支持的 GDSFactory 连接对象格式: 期望 dict/str，"
        f"实际为 {type(conn).__name__}: {conn!r}"
    )


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
    for route_name, route_data in routes.items():
        if not isinstance(route_data, dict):
            # R03: route 格式错误，禁止静默跳过
            raise TypeError(
                f"GDSFactory route '{route_name}' 必须为 dict，"
                f"实际为 {type(route_data).__name__}: {route_data!r}"
            )
        links = route_data.get("links", {})
        if not isinstance(links, dict):
            # R03: links 格式错误，禁止静默跳过
            raise TypeError(
                f"GDSFactory route '{route_name}' 的 links 必须为 dict，"
                f"实际为 {type(links).__name__}: {links!r}"
            )
        for src_ref, dst_ref in links.items():
            src_dev, src_port = split_port_ref(str(src_ref))
            dst_dev, dst_port = split_port_ref(str(dst_ref))
            if src_dev and dst_dev:
                conn = (src_dev, src_port, dst_dev, dst_port)
                if conn not in connections:
                    connections.append(conn)
    return connections


# ---------------------------------------------------------------------------
# PICBench
# ---------------------------------------------------------------------------


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
                # R03: 实例格式错误，禁止静默跳过
                raise TypeError(
                    f"PICBench 实例必须为 dict，实际为 {type(inst).__name__}: {inst!r}"
                )
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
            src_dev, src_port = split_port_ref(str(src_ref))
            dst_dev, dst_port = split_port_ref(str(dst_ref))
            if src_dev and dst_dev:
                connections.append((src_dev, src_port, dst_dev, dst_port))
    elif isinstance(conns, list):
        for conn in conns:
            # _extract_conn_pair 已改为 raise，无需 None 检查（R03）
            src, dst = _extract_conn_pair(conn)
            src_dev, src_port = split_port_ref(str(src))
            dst_dev, dst_port = split_port_ref(str(dst))
            if src_dev and dst_dev:
                connections.append((src_dev, src_port, dst_dev, dst_port))
    return connections


def _extract_conn_pair(conn: object) -> tuple[str, str]:
    """从单个连接对象提取 (src, dst) 对。

    Args:
        conn: 连接对象，可为 dict、list/tuple。

    Returns:
        (src, dst) 字符串对。

    Raises:
        TypeError: 连接对象格式不支持（非 dict/list/tuple）。
        ValueError: list/tuple 长度不足 2。
    """
    if isinstance(conn, dict):
        src = conn.get("source", conn.get("src", ""))
        dst = conn.get("destination", conn.get("dst", ""))
        return str(src), str(dst)
    if isinstance(conn, (list, tuple)):
        if len(conn) < 2:
            raise ValueError(
                f"连接 list/tuple 长度不足 2: {conn!r}"
            )
        return str(conn[0]), str(conn[1])
    # R03: 不支持的连接对象格式，禁止静默返回 None
    raise TypeError(
        f"不支持的连接对象格式: 期望 dict/list/tuple，"
        f"实际为 {type(conn).__name__}: {conn!r}"
    )


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
            # R03: 组件格式错误，禁止静默跳过
            raise TypeError(
                f"PICBench 组件必须为 dict，实际为 {type(comp).__name__}: {comp!r}"
            )
        name = comp.get("name", "unknown")
        ctype = comp.get("type", comp.get("component", "unknown"))
        w = float(comp.get("width", comp.get("xsize", 10.0)))
        h = float(comp.get("height", comp.get("ysize", 10.0)))
        devices.append(DeviceSpec(name=name, device_type=ctype, width_um=w, height_um=h))

    connections: list[tuple[str, str, str, str]] = []
    for conn in raw.get("connections", raw.get("nets", [])):
        # _extract_conn_pair 已改为 raise，无需 None 检查（R03）
        src, dst = _extract_conn_pair(conn)
        src_dev, src_port = split_port_ref(str(src))
        dst_dev, dst_port = split_port_ref(str(dst))
        if src_dev and dst_dev:
            connections.append((src_dev, src_port, dst_dev, dst_port))
    return devices, connections


# ---------------------------------------------------------------------------
# PhIDO
# ---------------------------------------------------------------------------


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
        if not isinstance(conn, dict):
            # R03: 连接格式错误，禁止静默跳过
            raise TypeError(
                f"PhIDO 连接必须为 dict，实际为 {type(conn).__name__}: {conn!r}"
            )
        src = conn.get("source", conn.get("src", ""))
        dst = conn.get("destination", conn.get("dst", ""))
        src_dev, src_port = split_port_ref(str(src))
        dst_dev, dst_port = split_port_ref(str(dst))
        if src_dev and dst_dev:
            connections.append((src_dev, src_port, dst_dev, dst_port))

    return CircuitSpec(
        name=raw.get("name", raw.get("design_id", p.stem)),
        devices=devices,
        connections=connections,
    )
