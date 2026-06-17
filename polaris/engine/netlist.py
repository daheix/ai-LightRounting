"""网表解析与连接图构建（Task 8）。

将用户提供的网表（JSON/YAML）解析为器件实例列表 + 连接边列表，
并构建 networkx 图（节点=器件，边=连接，属性=端口/约束）。

网表格式参考光子电路网表惯例：
- gdsfactory 的 netlist（YAML，instances + connections + ports）
  来源: https://gdsfactory.github.io/gdsfactory/
- IPKISS/Luceda 的 netlist（S 参数电路图）
  来源: https://academy.lucedaphotonics.com/

网表结构示例（YAML）::

    instances:
      wg1:
        component: strip_waveguide
        platform: SOI
        settings: {length_um: 20.0}
      mmi1:
        component: mmi_1x2
        platform: SOI
    connections:
      - [wg1, out, mmi1, in]
      - [mmi1, out0, wg2, in]
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import networkx as nx
import yaml

from polaris.pdk.catalog import DeviceCatalog, build_default_catalog
from polaris.pdk.device import Device


@dataclass
class NetlistConnection:
    """网表中的一条连接（端口到端口）。"""

    src_instance: str
    src_port: str
    dst_instance: str
    dst_port: str
    constraints: dict = field(default_factory=dict)


@dataclass
class NetlistInstance:
    """网表中的一个器件实例。"""

    instance_id: str
    component: str
    platform: str | None = None
    settings: dict = field(default_factory=dict)


@dataclass
class Netlist:
    """解析后的网表（器件实例 + 连接边）。"""

    instances: list[NetlistInstance] = field(default_factory=list)
    connections: list[NetlistConnection] = field(default_factory=list)
    name: str = "untitled"

    @property
    def instance_ids(self) -> list[str]:
        return [i.instance_id for i in self.instances]


def parse_netlist(data: str | Path | dict) -> Netlist:
    """解析网表（YAML/JSON 字符串、文件路径或字典）。

    Args:
        data: YAML/JSON 字符串、文件路径或已解析的字典。

    Returns:
        解析后的 ``Netlist``。
    """
    if isinstance(data, dict):
        raw = data
    else:
        p = Path(data)
        text = p.read_text(encoding="utf-8") if p.exists() else str(data)
        raw = yaml.safe_load(text)
    if not isinstance(raw, dict):
        raise ValueError("网表须为映射（dict）结构")

    net = Netlist(name=raw.get("name", "untitled"))

    # 解析器件实例
    for inst_id, info in (raw.get("instances") or {}).items():
        if isinstance(info, str):
            component, platform = info, None
            settings: dict = {}
        else:
            component = info.get("component") or info.get("name")
            platform = info.get("platform")
            settings = info.get("settings") or {}
        net.instances.append(
            NetlistInstance(
                instance_id=inst_id,
                component=component,
                platform=platform,
                settings=settings,
            )
        )

    # 解析连接（支持 [src, sport, dst, dport] 或 {src, src_port, dst, dst_port}）
    for conn in (raw.get("connections") or []):
        if isinstance(conn, (list, tuple)):
            if len(conn) >= 4:
                src, sport, dst, dport = conn[:4]
                extra = conn[4] if len(conn) > 4 and isinstance(conn[4], dict) else {}
            else:
                raise ValueError(f"连接格式错误（需 4 元素）: {conn}")
        elif isinstance(conn, dict):
            src = conn.get("src") or conn.get("source")
            sport = conn.get("src_port") or conn.get("source_port")
            dst = conn.get("dst") or conn.get("destination") or conn.get("target")
            dport = conn.get("dst_port") or conn.get("destination_port") or conn.get("target_port")
            extra = conn.get("constraints") or {}
        else:
            raise ValueError(f"连接格式不支持: {conn}")
        if not all([src, sport, dst, dport]):
            raise ValueError(f"连接字段缺失: {conn}")
        net.connections.append(
            NetlistConnection(
                src_instance=str(src),
                src_port=str(sport),
                dst_instance=str(dst),
                dst_port=str(dport),
                constraints=extra or {},
            )
        )

    return net


def instantiate_devices(
    net: Netlist,
    catalog: DeviceCatalog | None = None,
) -> dict[str, Device]:
    """将网表实例实例化为 ``Device`` 对象（通过 catalog 检索器件模板）。

    Args:
        net: 解析后的网表。
        catalog: 器件注册表（默认使用全部内置平台）。

    Returns:
        ``instance_id -> Device`` 映射。
    """
    if catalog is None:
        catalog = build_default_catalog()
    devices: dict[str, Device] = {}
    for inst in net.instances:
        dev = catalog.get(inst.component, platform=inst.platform)
        # 用实例 id 覆盖 device_id 以区分同类型多实例
        dev = Device(
            device_id=inst.instance_id,
            platform=dev.platform,
            category=dev.category,
            name=dev.name,
            ports=dev.ports,
            bbox=dev.bbox,
            params={**dev.params, **inst.settings},
            source=dev.source,
            constraints=dev.constraints,
        )
        devices[inst.instance_id] = dev
    return devices


def build_graph(net: Netlist, devices: dict[str, Device]) -> nx.Graph:
    """构建 networkx 图（节点=器件，边=连接，属性=端口/约束）。

    节点属性：``device``（Device 对象）、``platform``、``category``、``footprint``。
    边属性：``src_port``、``dst_port``、``constraints``。

    Args:
        net: 解析后的网表。
        devices: ``instantiate_devices`` 返回的实例映射。

    Returns:
        ``networkx.Graph``。
    """
    g = nx.Graph()
    for inst_id, dev in devices.items():
        w, h = dev.footprint()
        g.add_node(
            inst_id,
            device=dev,
            platform=dev.platform,
            category=dev.category,
            footprint=(w, h),
        )
    for conn in net.connections:
        if conn.src_instance not in devices or conn.dst_instance not in devices:
            raise ValueError(
                f"连接引用了未实例化的器件: {conn.src_instance} 或 {conn.dst_instance}"
            )
        g.add_edge(
            conn.src_instance,
            conn.dst_instance,
            src_port=conn.src_port,
            dst_port=conn.dst_port,
            constraints=conn.constraints,
        )
    return g


def load_netlist(data: str | Path | dict) -> tuple[Netlist, dict[str, Device], nx.Graph]:
    """一站式加载：解析网表 → 实例化器件 → 构建图。"""
    net = parse_netlist(data)
    devices = instantiate_devices(net)
    graph = build_graph(net, devices)
    return net, devices, graph
