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

参考文献：
[1] Nagel L W. SPICE2: A computer program to simulate semiconductor circuits[R]. University of California, Berkeley, Electronics Research Laboratory, 1975. https://www2.eecs.berkeley.edu/Pubs/TechRpts/1975/9602.html
[2] Rubin S M. Computer aids for VLSI design[M]. Addison-Wesley, 1987. https://www.rulabinsky.com/cavd/text/chapc.html
[3] Si2. OpenAccess: An open source EDA database[C]//ASP-DAC. 2006: 434-437. https://cecs.uci.edu/~papers/aspdac06/pdf/p434_4D-1.pdf
[4] EURICH. EDIF tutorial[C]//Design Automation Conference (DAC). 1986. https://www.cs.york.ac.uk/rts/docs/DAC-1964-2006/PAPERS/1986/DAC86_327.PDF
[5] Sharma A, et al. PhIDO: A domain-specific language for photonic circuit design[J]. arXiv preprint arXiv:2508.14123, 2025. https://arxiv.org/html/2508.14123v1/
[6] YAML 1.2.1 Specification. YAML Organization, 2009. https://yaml.org/spec/1.2.1/
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


def _load_raw(data: str | Path | dict) -> dict:
    """加载原始网表数据为字典（支持 dict / 文件路径 / YAML-JSON 字符串）。

    Args:
        data: YAML/JSON 字符串、文件路径或已解析的字典。

    Returns:
        解析后的字典。

    Raises:
        ValueError: 当解析结果不是映射（dict）结构时。
    """
    if isinstance(data, dict):
        raw = data
    elif isinstance(data, Path):
        text = data.read_text(encoding="utf-8")
        raw = yaml.safe_load(text)
    else:
        # 字符串：先判断是否为文件路径（短字符串且无换行符），
        # 否则视为 YAML/JSON 内容。避免 Path(多行字符串) 触发 OSError。
        if "\n" not in data and len(data) < 4096:
            p = Path(data)
            if p.exists():
                text = p.read_text(encoding="utf-8")
                raw = yaml.safe_load(text)
                if not isinstance(raw, dict):
                    raise ValueError("网表须为映射（dict）结构")
                return raw
        raw = yaml.safe_load(str(data))
    if not isinstance(raw, dict):
        raise ValueError("网表须为映射（dict）结构")
    return raw


def _parse_instance(inst_id: str, info: str | dict) -> NetlistInstance:
    """解析单个器件实例（支持字符串简写或字典详写）。

    Args:
        inst_id: 实例标识。
        info: 器件信息（字符串视为 component 名，或含 component/platform/settings 的字典）。

    Returns:
        ``NetlistInstance``。
    """
    if isinstance(info, str):
        component, platform = info, None
        settings: dict = {}
    else:
        component = info.get("component") or info.get("name")
        platform = info.get("platform")
        settings = info.get("settings") or {}
    return NetlistInstance(
        instance_id=inst_id,
        component=component,
        platform=platform,
        settings=settings,
    )


def _parse_list_connection(
    conn: list | tuple,
) -> tuple[str, str, str, str, dict]:
    """解析列表/元组格式连接 ``[src, sport, dst, dport, constraints?]``。

    Args:
        conn: 长度 >= 4 的连接列表。

    Returns:
        ``(src, sport, dst, dport, extra)`` 五元组。

    Raises:
        ValueError: 当连接元素不足 4 个时。
    """
    if len(conn) >= 4:
        src, sport, dst, dport = conn[:4]
        extra = conn[4] if len(conn) > 4 and isinstance(conn[4], dict) else {}
    else:
        raise ValueError(f"连接格式错误（需 4 元素）: {conn}")
    return src, sport, dst, dport, extra


def _parse_dict_connection(conn: dict) -> tuple[str, str, str, str, dict]:
    """解析字典格式连接（支持 src/source、dst/destination/target 等别名）。

    Args:
        conn: 含连接字段的字典。

    Returns:
        ``(src, sport, dst, dport, extra)`` 五元组。
    """
    src = conn.get("src") or conn.get("source")
    sport = conn.get("src_port") or conn.get("source_port")
    dst = conn.get("dst") or conn.get("destination") or conn.get("target")
    dport = conn.get("dst_port") or conn.get("destination_port") or conn.get("target_port")
    extra = conn.get("constraints") or {}
    return src, sport, dst, dport, extra


def _parse_connection(conn) -> NetlistConnection:
    """解析单条连接（支持列表/元组或字典格式）。

    Args:
        conn: 连接定义（列表/元组或字典）。

    Returns:
        ``NetlistConnection``。

    Raises:
        ValueError: 当连接格式不支持或字段缺失时。
    """
    if isinstance(conn, (list, tuple)):
        src, sport, dst, dport, extra = _parse_list_connection(conn)
    elif isinstance(conn, dict):
        src, sport, dst, dport, extra = _parse_dict_connection(conn)
    else:
        raise ValueError(f"连接格式不支持: {conn}")
    if not all([src, sport, dst, dport]):
        raise ValueError(f"连接字段缺失: {conn}")
    return NetlistConnection(
        src_instance=str(src),
        src_port=str(sport),
        dst_instance=str(dst),
        dst_port=str(dport),
        constraints=extra or {},
    )


def parse_netlist(data: str | Path | dict) -> Netlist:
    """解析网表（YAML/JSON 字符串、文件路径或字典）。

    Args:
        data: YAML/JSON 字符串、文件路径或已解析的字典。

    Returns:
        解析后的 ``Netlist``。
    """
    raw = _load_raw(data)
    net = Netlist(name=raw.get("name", "untitled"))

    # 解析器件实例
    for inst_id, info in (raw.get("instances") or {}).items():
        net.instances.append(_parse_instance(inst_id, info))

    # 解析连接（支持 [src, sport, dst, dport] 或 {src, src_port, dst, dst_port}）
    for conn in raw.get("connections") or []:
        net.connections.append(_parse_connection(conn))

    return net


def instantiate_devices(
    net: Netlist,
    catalog: DeviceCatalog | None = None,
) -> dict[str, Device]:
    """将网表实例实例化为 ``Device`` 对象（通过 catalog 检索器件模板）。

    当实例 ``settings`` 含 ``ports`` 字段时，用其覆盖 catalog 模板端口，
    以支持 LiDAR 等外部 benchmark 的端口命名约定（如 ``o1/o2`` 而非
    ``in/out1``），确保连接能正确解析（规则 16 Bug 修复）。

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
        ports = _resolve_ports(dev, inst.settings)
        # 用实例 id 覆盖 device_id 以区分同类型多实例
        # P1-3 修复（第7轮）：传递 process_node，避免从 catalog 模板实例化后
        # 丢失工艺节点信息。来源: docs/commercial_gap_analysis.md P1-3
        dev = Device(
            device_id=inst.instance_id,
            platform=dev.platform,
            category=dev.category,
            name=dev.name,
            ports=ports,
            bbox=dev.bbox,
            params={**dev.params, **inst.settings},
            source=dev.source,
            constraints=dev.constraints,
            process_node=dev.process_node,
        )
        devices[inst.instance_id] = dev
    return devices


def _resolve_ports(dev: Device, settings: dict) -> list:
    """从 settings 解析端口列表，无则用 catalog 模板端口。

    Args:
        dev: catalog 模板器件。
        settings: 实例配置（可能含 ``ports`` 字段覆盖模板端口）。

    Returns:
        ``Port`` 列表。
    """
    raw_ports = settings.get("ports") if settings else None
    if not raw_ports:
        return dev.ports
    from polaris.pdk.port import Port

    resolved = []
    for p in raw_ports:
        if isinstance(p, Port):
            resolved.append(p)
        elif isinstance(p, dict):
            direction = _parse_direction(p.get("direction", "E"))
            resolved.append(
                Port(
                    name=str(p["name"]),
                    x=float(p.get("x", 0.0)),
                    y=float(p.get("y", 0.0)),
                    direction=direction,
                    waveguide_type=str(p.get("waveguide_type", "strip")),
                    width=float(p.get("width", 0.5)),
                )
            )
    return resolved if resolved else dev.ports


def _parse_direction(val):
    """解析端口朝向（支持字符串首字母 N/S/E/W 或 Direction 枚举）。"""
    from polaris.pdk.port import Direction

    if isinstance(val, Direction):
        return val
    s = str(val).strip().upper()[:1]
    mapping = {"N": Direction.NORTH, "S": Direction.SOUTH, "E": Direction.EAST, "W": Direction.WEST}
    return mapping.get(s, Direction.EAST)


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
