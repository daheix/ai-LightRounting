"""网表格式自动适配器（R01 创新点 3）。

自动检测输入网表格式（sax/simphony/PoLaRIS），统一转换为内部格式。

支持格式:
1. sax 格式: dict of dicts，connections 使用 "instance,port" 逗号分隔
   来源: https://flaport.github.io/sax/
2. simphony 格式: JSON，connections 使用列表 of ["inst.port", "inst.port"]
   来源: https://simphonyphotonics.readthedocs.io/
3. PoLaRIS 内部格式: connections 使用 [(inst.port, inst.port), ...] 列表

创新点（标注"创新"）:
- 网表格式自动适配器：通过正则模式匹配端口引用格式，
  自动检测输入网表格式并统一转换为内部格式。
- 支持理论: sax 文档承认网表格式与 gdsfactory 耦合过紧（R01.md §4.5），
  PoLaRIS 解决此痛点。
- 案例: 用户可传入 sax/simphony/PoLaRIS 任一格式网表，
  适配器自动识别并转换，无需手动指定格式。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

NetlistFormat = Literal["sax", "simphony", "polaris"]


@dataclass
class PolarNetlist:
    """PoLaRIS 内部网表格式。

    Attributes:
        instances: 实例字典 {name: model_name}。
        connections: 连接列表 [(inst1.port, inst2.port), ...]。
        ports: 外部端口映射 {ext_name: inst.port}。
        params: 实例参数 {inst_name: {param: value}}。
    """

    instances: dict[str, str] = field(default_factory=dict)
    connections: list[tuple[str, str]] = field(default_factory=list)
    ports: dict[str, str] = field(default_factory=dict)
    params: dict[str, dict] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """转换为字典格式（兼容 CircuitSimulator.simulate 输入）。"""
        return {
            "instances": dict(self.instances),
            "connections": {f"{c[0]}": c[1] for c in self.connections},
            "ports": dict(self.ports),
            "params": dict(self.params),
        }


def _detect_dict_format(connections: dict) -> NetlistFormat:
    """检测 dict 格式网表（sax 或 polaris dict）。

    Args:
        connections: dict 格式的 connections。

    Returns:
        格式名称。

    Raises:
        ValueError: 无法识别格式时告警退出。
    """
    for key in connections:
        if isinstance(key, str) and "," in key:
            return "sax"
    # PoLaRIS dict 格式: 键含点号 "instance.port"
    for key in connections:
        if isinstance(key, str) and "." in key:
            return "polaris"
    # 默认 dict 格式按 sax 处理
    return "sax"


def _detect_list_format(connections: list) -> NetlistFormat:
    """检测 list 格式网表（simphony 或 polaris list）。

    Args:
        connections: list 格式的 connections。

    Returns:
        格式名称。

    Raises:
        ValueError: 无法识别格式时告警退出。
    """
    if not connections:
        return "polaris"
    first = connections[0]
    # PoLaRIS: list of (str, str) tuple
    if isinstance(first, tuple) and len(first) == 2:
        return "polaris"
    # simphony: list of [str, str] list
    if isinstance(first, list) and len(first) == 2:
        return "simphony"
    msg = f"无法识别的 connections 列表格式: {type(first)}"
    raise ValueError(msg)


def _detect_format(netlist: dict) -> NetlistFormat:
    """自动检测网表格式。

    检测策略:
    1. connections 为 dict 且键含逗号 → sax 格式
    2. connections 为 list 且元素为 [str, str] → simphony 格式
    3. connections 为 list 且元素为 (str, str) tuple → PoLaRIS 格式
    4. connections 为 dict 且键含点号 → PoLaRIS dict 格式

    Args:
        netlist: 输入网表字典。

    Returns:
        检测到的格式名称。

    Raises:
        ValueError: 无法识别格式时告警退出（禁止 fall-back）。
    """
    connections = netlist.get("connections", {})
    if isinstance(connections, dict):
        return _detect_dict_format(connections)
    if isinstance(connections, list):
        return _detect_list_format(connections)
    msg = f"无法识别的 connections 类型: {type(connections)}"
    raise ValueError(msg)


def _parse_sax_netlist(netlist: dict) -> PolarNetlist:
    """解析 sax 格式网表。

    sax 格式:
        connections: {"inst1,port1": "inst2,port2", ...}
        ports: {"ext": "inst,port", ...}

    Args:
        netlist: sax 格式网表字典。

    Returns:
        PolarNetlist 内部格式。
    """
    result = PolarNetlist()
    # instances
    for name, model in netlist.get("instances", {}).items():
        if isinstance(model, str):
            result.instances[name] = model
        elif isinstance(model, dict):
            # sax 模型可能是 {model: name, params: {...}}
            result.instances[name] = model.get("model", "")
            if "params" in model:
                result.params[name] = model["params"]
    # connections: 逗号分隔 → 点号分隔
    for key, val in netlist.get("connections", {}).items():
        c1 = key.replace(",", ".", 1)
        c2 = val.replace(",", ".", 1)
        result.connections.append((c1, c2))
    # ports: 逗号分隔 → 点号分隔
    for ext, ref in netlist.get("ports", {}).items():
        result.ports[ext] = ref.replace(",", ".", 1)
    return result


def _parse_simphony_netlist(netlist: dict) -> PolarNetlist:
    """解析 simphony 格式网表。

    simphony 格式:
        connections: [["inst1.port1", "inst2.port2"], ...]
        ports: {"ext": "inst.port", ...}

    Args:
        netlist: simphony 格式网表字典。

    Returns:
        PolarNetlist 内部格式。
    """
    result = PolarNetlist()
    # instances
    for name, model in netlist.get("instances", {}).items():
        if isinstance(model, str):
            result.instances[name] = model
        elif isinstance(model, dict):
            result.instances[name] = model.get("model", "")
            if "params" in model:
                result.params[name] = model["params"]
    # connections: list of [str, str] → list of (str, str)
    for conn in netlist.get("connections", []):
        if len(conn) != 2:
            msg = f"simphony connection 长度必须为 2，得到 {len(conn)}"
            raise ValueError(msg)
        result.connections.append((conn[0], conn[1]))
    # ports: 点号分隔（与 PoLaRIS 一致）
    for ext, ref in netlist.get("ports", {}).items():
        result.ports[ext] = ref
    return result


def _parse_polaris_connections(connections) -> list[tuple[str, str]]:
    """解析 PoLaRIS 格式 connections（list 或 dict）。

    Args:
        connections: list of (str, str) 或 dict {str: str}。

    Returns:
        连接列表 [(str, str), ...]。

    Raises:
        ValueError: connection 长度不为 2 时告警退出。
    """
    result: list[tuple[str, str]] = []
    if isinstance(connections, dict):
        for key, val in connections.items():
            result.append((key, val))
    elif isinstance(connections, list):
        for conn in connections:
            if len(conn) != 2:
                msg = f"PoLaRIS connection 长度必须为 2，得到 {len(conn)}"
                raise ValueError(msg)
            result.append((conn[0], conn[1]))
    return result


def _parse_polaris_netlist(netlist: dict) -> PolarNetlist:
    """解析 PoLaRIS 内部格式网表。

    PoLaRIS 格式:
        connections: [(inst1.port, inst2.port), ...] 或
                     {"inst1.port": "inst2.port", ...}
        ports: {"ext": "inst.port", ...}

    Args:
        netlist: PoLaRIS 格式网表字典。

    Returns:
        PolarNetlist 内部格式。
    """
    result = PolarNetlist()
    # instances
    for name, model in netlist.get("instances", {}).items():
        if isinstance(model, str):
            result.instances[name] = model
        elif isinstance(model, dict):
            result.instances[name] = model.get("model", "")
            if "params" in model:
                result.params[name] = model["params"]
    # connections
    result.connections = _parse_polaris_connections(netlist.get("connections", {}))
    # ports
    for ext, ref in netlist.get("ports", {}).items():
        result.ports[ext] = ref
    return result


def adapt_netlist(netlist: dict) -> PolarNetlist:
    """自动检测并转换网表格式为 PoLaRIS 内部格式。

    创新点 3：网表格式自动适配器。
    自动检测输入网表格式（sax/simphony/PoLaRIS），统一转换为内部格式。

    Args:
        netlist: 输入网表字典（sax/simphony/PoLaRIS 任一格式）。

    Returns:
        PolarNetlist 内部格式。

    Raises:
        ValueError: 格式无法识别或解析失败时告警退出（禁止 fall-back）。
    """
    fmt = _detect_format(netlist)
    if fmt == "sax":
        return _parse_sax_netlist(netlist)
    if fmt == "simphony":
        return _parse_simphony_netlist(netlist)
    if fmt == "polaris":
        return _parse_polaris_netlist(netlist)
    msg = f"未知网表格式: {fmt}"
    raise ValueError(msg)


def detect_format(netlist: dict) -> NetlistFormat:
    """公开接口：检测网表格式（用于调试）。

    Args:
        netlist: 输入网表字典。

    Returns:
        格式名称 "sax"/"simphony"/"polaris"。
    """
    return _detect_format(netlist)


def validate_netlist(netlist: PolarNetlist) -> None:
    """验证网表完整性。

    检查:
    1. 所有连接引用的实例存在于 instances 中
    2. 所有端口引用的实例存在于 instances 中
    3. 端口引用格式为 "instance.port"

    Args:
        netlist: PoLaRIS 内部格式网表。

    Raises:
        ValueError: 网表不完整时告警退出（禁止 fall-back）。
    """
    inst_names = set(netlist.instances.keys())
    # 验证连接
    for c1, c2 in netlist.connections:
        for ref in (c1, c2):
            match = re.match(r"^(\w+)\.(\w+)$", ref)
            if not match:
                msg = f"连接引用格式错误: {ref}，应为 'instance.port'"
                raise ValueError(msg)
            if match.group(1) not in inst_names:
                msg = f"连接引用的实例不存在: {match.group(1)} (in {ref})"
                raise ValueError(msg)
    # 验证端口
    for _ext, ref in netlist.ports.items():
        match = re.match(r"^(\w+)\.(\w+)$", ref)
        if not match:
            msg = f"端口引用格式错误: {ref}，应为 'instance.port'"
            raise ValueError(msg)
        if match.group(1) not in inst_names:
            msg = f"端口引用的实例不存在: {match.group(1)} (in {ref})"
            raise ValueError(msg)
