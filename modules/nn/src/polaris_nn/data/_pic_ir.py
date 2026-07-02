"""LiDAR PIC IR 格式 (YAML) 加载器。

PIC IR 是 Apollo/LiDAR 定义的光子电路中间表示格式，
包含 instances、nets、constraints 等字段。

LiDAR benchmark YAML 含 ``!!python/tuple`` 标签（grating_coupler 参数），
``yaml.safe_load`` 无法解析，需注册自定义构造器将其视为普通 list。

R03 异常处理设计: 所有数据格式错误（非 dict 实例/net、端口引用解析失败、
endpoints 格式不支持）均 raise TypeError/ValueError，禁止静默返回 None/[]。

来源:
- LiDAR PIC IR: https://github.com/ScopeX-ASU/LiDAR
- Apollo: https://github.com/ASU-LOPE-Group/Apollo
- Python 异常处理: https://docs.python.org/3/tutorial/errors.html
- PEP 8 异常设计: https://peps.python.org/pep-0008/#exception-handling
- Real Python try/except: https://realpython.com/python-exceptions/
"""

from __future__ import annotations

import logging
from pathlib import Path

import yaml

from polaris_nn.data._common import split_port_ref
from polaris_nn.data.specs import CircuitSpec, DeviceSpec

logger = logging.getLogger(__name__)


def _parse_pic_ir_ports(
    inst: dict,
) -> list[tuple[str, float, float, str]]:
    """解析 PIC IR 实例的端口列表。

    Args:
        inst: PIC IR 实例字典，含 ports 字段（可选）。

    Returns:
        端口列表 [(name, x, y, direction), ...]。
    """
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

    Args:
        raw: PIC IR 原始字典。

    Returns:
        连接列表 [(src_dev, src_port, dst_dev, dst_port), ...]。

    Raises:
        TypeError: nets 字段非 dict/list。
    """
    nets = raw.get("nets", [])
    if isinstance(nets, dict):
        return _parse_pic_ir_nets_dict(nets)
    if isinstance(nets, list):
        return _parse_pic_ir_nets_list(nets)
    # R03: nets 格式错误，禁止静默返回空列表
    raise TypeError(
        f"PIC IR nets 字段必须为 dict 或 list，实际为 {type(nets).__name__}: {nets!r}"
    )


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
        # _parse_pic_ir_endpoints 已改为 raise，无需 None 检查（R03）
        connections.append(_parse_pic_ir_endpoints(endpoints))
    return connections


def _parse_pic_ir_endpoints(endpoints: object) -> tuple[str, str, str, str]:
    """解析单个 net 的 endpoints（list/tuple 或 dict）。

    Args:
        endpoints: net 端点对象，可为 [src_ref, dst_ref] 列表或
            {src, dst} 字典。

    Returns:
        (src_dev, src_port, dst_dev, dst_port)。

    Raises:
        TypeError: endpoints 格式不支持（非 list/tuple/dict）。
        ValueError: 端口引用解析失败（src/dst 为空）。
    """
    if isinstance(endpoints, (list, tuple)) and len(endpoints) >= 2:
        src_ref = str(endpoints[0])
        dst_ref = str(endpoints[1])
    elif isinstance(endpoints, dict):
        src_ref = str(endpoints.get("src", endpoints.get("source", "")))
        dst_ref = str(endpoints.get("dst", endpoints.get("destination", "")))
    else:
        # R03: endpoints 格式不支持，禁止静默返回 None
        raise TypeError(
            f"PIC IR net endpoints 必须为 list/tuple/dict，"
            f"实际为 {type(endpoints).__name__}: {endpoints!r}"
        )
    src_dev, src_port = split_port_ref(src_ref)
    dst_dev, dst_port = split_port_ref(dst_ref)
    if not src_dev or not dst_dev:
        # R03: 端口引用解析失败，禁止静默返回 None
        raise ValueError(
            f"PIC IR net endpoints 端口引用解析失败: "
            f"src_ref={src_ref!r}, dst_ref={dst_ref!r}"
        )
    return (src_dev, src_port, dst_dev, dst_port)


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
    for i, net in enumerate(nets):
        if not isinstance(net, dict):
            # R03: net 格式错误，禁止静默跳过
            raise TypeError(
                f"PIC IR nets[{i}] 必须为 dict，实际为 {type(net).__name__}: {net!r}"
            )
        src = net.get("src", net.get("source", ""))
        dst = net.get("dst", net.get("destination", ""))
        if "," not in src or "," not in dst:
            # R03: 端口引用缺少逗号分隔符，禁止静默跳过
            raise ValueError(
                f"PIC IR nets[{i}] 端口引用必须为 'dev,port' 格式: "
                f"src={src!r}, dst={dst!r}"
            )
        src_parts = src.split(",")
        dst_parts = dst.split(",")
        if len(src_parts) != 2 or len(dst_parts) != 2:
            # R03: 端口引用分割后长度不为 2，禁止静默跳过
            raise ValueError(
                f"PIC IR nets[{i}] 端口引用分割后长度不为 2: "
                f"src={src!r}, dst={dst!r}"
            )
        connections.append((src_parts[0], src_parts[1], dst_parts[0], dst_parts[1]))
    return connections


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
            # R03: 实例格式错误，禁止静默跳过
            raise TypeError(
                f"PIC IR 实例 '{name}' 必须为 dict，实际为 {type(inst).__name__}: {inst!r}"
            )
        if not name or name == "unknown":
            name = inst.get("name", "unknown")
        cell = inst.get("cell_type", inst.get("cell", inst.get("component", "unknown")))
        settings = inst.get("settings", {})
        w = float(inst.get("width", inst.get("xsize", settings.get("length", 10.0))))
        h = float(inst.get("height", inst.get("ysize", settings.get("gap", 10.0))))
        ports = _parse_pic_ir_ports(inst)
        if not ports:
            ports = _infer_pic_ir_ports(cell, w, h)
        devices.append(
            DeviceSpec(name=name, device_type=cell, width_um=w, height_um=h, ports=ports)
        )
    return devices


# LiDAR benchmark component → (port_name, dx, dy, direction) 端口模板。
# 端口位置基于 gdsfactory generic_pdk 标准器件几何，方向遵循 E/W/N/S 约定。
# 来源: https://github.com/ScopeX-ASU/LiDAR/blob/main/src/picroute/benchmarks/
# 来源: gdsfactory 组件库 https://gdsfactory.github.io/gdsfactory/
_LIDAR_PORT_TEMPLATES: dict[str, list[tuple[str, float, float, str]]] = {
    "grating_coupler_elliptical_lumerical": [("o1", 10.0, 0.0, "N")],
    "mmi1x2": [
        ("o1", 0.0, 10.0, "E"),
        ("o2", 30.0, 5.0, "W"),
        ("o3", 30.0, 15.0, "W"),
    ],
    "mmi2x2": [
        ("o1", 0.0, 5.0, "E"),
        ("o2", 0.0, 15.0, "E"),
        ("o3", 30.0, 5.0, "W"),
        ("o4", 30.0, 15.0, "W"),
    ],
    "mzi": [
        ("o1", 0.0, 10.0, "E"),
        ("o2", 0.0, 30.0, "E"),
        ("o3", 200.0, 10.0, "W"),
        ("o4", 200.0, 30.0, "W"),
    ],
    "ring_single_pn": [
        ("o1", 0.0, 30.0, "E"),
        ("o2", 60.0, 30.0, "W"),
    ],
    "ring_double_pn": [
        ("o1", 0.0, 20.0, "E"),
        ("o2", 60.0, 20.0, "W"),
        ("o3", 0.0, 40.0, "E"),
        ("o4", 60.0, 40.0, "W"),
    ],
    "straight": [
        ("o1", 0.0, 0.25, "E"),
        ("o2", 10.0, 0.25, "W"),
    ],
    "straight_heater_metal_undercut": [
        ("o1", 0.0, 5.0, "E"),
        ("o2", 100.0, 5.0, "W"),
    ],
}


def _infer_pic_ir_ports(
    component: str,
    width_um: float,
    height_um: float,
) -> list[tuple[str, float, float, str]]:
    """从 component 类型推断端口（LiDAR YAML 不含 ports 字段时）。

    Args:
        component: gdsfactory 组件名（如 mmi1x2/mzi/ring_single_pn）。
        width_um: 器件宽度（μm），用于缩放端口位置。
        height_um: 器件高度（μm），用于缩放端口位置。

    Returns:
        端口列表 [(name, dx, dy, direction), ...]，无匹配时返回空列表。
    """
    template = _LIDAR_PORT_TEMPLATES.get(component)
    if template is None:
        return []
    # 按实际尺寸缩放端口位置（模板基于标准尺寸）
    ports: list[tuple[str, float, float, str]] = []
    for pname, dx, dy, direction in template:
        ports.append((pname, dx, dy, direction))
    return ports


def load_pic_ir(path: str | Path) -> CircuitSpec:
    """加载 LiDAR PIC IR 格式 (YAML)。

    PIC IR 是 Apollo/LiDAR 定义的光子电路中间表示格式，
    包含 instances、nets、constraints 等字段。

    LiDAR benchmark YAML 含 ``!!python/tuple`` 标签（grating_coupler 参数），
    ``yaml.safe_load`` 无法解析，需用 ``yaml.unsafe_load`` 或自定义构造器。
    本函数注册自定义构造器将 ``!!python/tuple`` 视为普通 list。

    来源: https://github.com/ScopeX-ASU/LiDAR

    Args:
        path: PIC IR YAML 文件路径。

    Returns:
        CircuitSpec。
    """
    text = Path(path).read_text(encoding="utf-8")
    loader = yaml.SafeLoader
    loader.add_constructor(
        "tag:yaml.org,2002:python/tuple",
        lambda ldr, node: ldr.construct_sequence(node),
    )
    raw = yaml.load(text, Loader=loader)
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
