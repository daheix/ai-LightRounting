"""图同构 LVS 比对引擎（从 v4 polaris.sim.graph_lvs 迁移）。

基于图同构（Graph Isomorphism）的 LVS 网表比对引擎，替代 KLayout 的回溯匹配，
解决大规模网表回溯爆炸问题。新增光子电路专用 LVS 功能：波导长度验证、端口朝向
验证、器件参数比对。

## 理论依据（R02 学术诚信，≥5 文献 URL）

- 图同构判定: McKay & Piperno, "Practical Graph Isomorphism, II",
  J. Symbolic Computation 2014, DOI: 10.1016/j.jsc.2013.09.003
  https://www.sciencedirect.com/science/article/pii/S0747717113001930
- VF2 子图同构: Cordella et al., IEEE TPAMI 2004, DOI: 10.1109/TPAMI.2004.75
  https://ieeexplore.ieee.org/document/1266305
- KLayout LVS Compare: https://www.klayout.org/downloads/master/doc-qt5/manual/lvs_compare.html
- SiEPIC EBeam PDK LVS: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- Chrostowski & Hochberg, "Silicon Photonics Design: From Devices to Systems",
  Cambridge University Press, 2015, ISBN 978-1-107-08345-6
  https://www.cambridge.org/9781107083456
- NetworkX isomorphism 文档: https://networkx.org/documentation/stable/reference/algorithms/isomorphism.html

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU（纯 networkx）/ R13 不保留 v4 兼容。
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import networkx as nx
from networkx.algorithms.isomorphism import GraphMatcher


@dataclass
class NetlistNode:
    """网表图节点（器件或端口）。

    Attributes:
        node_id: 节点唯一标识。
        node_type: 节点类型（"device" 或 "port"）。
        device_type: 器件类型（如 "mmi1x2"、"y_branch"），端口为空。
        params: 器件参数字典（如 {"radius": 5.0}），端口为空。
        layer: 层名（端口用）。
    """

    node_id: str
    node_type: str  # "device" 或 "port"
    device_type: str = ""
    params: dict = field(default_factory=dict)
    layer: str = ""


@dataclass
class NetlistEdge:
    """网表图边（连接关系）。

    Attributes:
        source: 源节点 ID。
        target: 目标节点 ID。
        edge_type: 边类型（"wire" 波导连接、"port" 端口连接）。
        length_um: 波导长度（μm），仅 wire 类型。
    """

    source: str
    target: str
    edge_type: str = "wire"  # "wire" 或 "port"
    length_um: float = 0.0


@dataclass
class PhotonicsLVSReport:
    """光子电路 LVS 报告（扩展 LVSReport）。

    Attributes:
        is_match: 是否完全匹配。
        mismatches: 不匹配项列表。
        device_type_mismatches: 器件类型不匹配列表。
        param_mismatches: 器件参数不匹配列表。
        waveguide_length_mismatches: 波导长度不匹配列表。
        port_orientation_mismatches: 端口朝向不匹配列表。
        isomorphism_mapping: 图同构映射（如果找到）。
        comparison_time_s: 比对耗时（秒）。
    """

    is_match: bool = False
    mismatches: list = field(default_factory=list)
    device_type_mismatches: list = field(default_factory=list)
    param_mismatches: list = field(default_factory=list)
    waveguide_length_mismatches: list = field(default_factory=list)
    port_orientation_mismatches: list = field(default_factory=list)
    isomorphism_mapping: dict = field(default_factory=dict)
    comparison_time_s: float = 0.0


@dataclass
class PhotonicsNetlist:
    """光子电路网表（扩展 ExtractedNetlist）。

    Attributes:
        devices: 器件节点列表。
        edges: 边列表。
        ports: 端口节点列表。
    """

    devices: list = field(default_factory=list)  # list[NetlistNode]
    edges: list = field(default_factory=list)  # list[NetlistEdge]
    ports: list = field(default_factory=list)  # list[NetlistNode]

    def to_graph(self) -> nx.Graph:
        """转换为 networkx 图。

        节点属性: node_type/device_type/params/layer; 边属性: edge_type/length_um。
        Returns: networkx.Graph
        Raises: ValueError: 网表为空（无器件且无端口）。
        """
        if not self.devices and not self.ports:
            raise ValueError("网表为空（无器件且无端口），无法构建图")
        graph = nx.Graph()
        for node in list(self.devices) + list(self.ports):
            graph.add_node(
                node.node_id,
                node_type=node.node_type,
                device_type=node.device_type,
                params=dict(node.params),
                layer=node.layer,
            )
        for edge in self.edges:
            graph.add_edge(
                edge.source, edge.target, edge_type=edge.edge_type, length_um=edge.length_um
            )
        return graph

    @classmethod
    def from_extracted_netlist(cls, extracted) -> PhotonicsNetlist:
        """从 ExtractedNetlist 或 PolarNetlist 转换（鸭子类型）。

        Args:
            extracted: ExtractedNetlist（devices+connections）或 PolarNetlist
                （instances+connections+ports+params）对象。
        Returns: PhotonicsNetlist
        Raises: TypeError: 不支持的网表类型。
        """
        if hasattr(extracted, "instances") and hasattr(extracted, "ports"):
            params = getattr(extracted, "params", {})
            devices = [
                NetlistNode(
                    node_id=n, node_type="device", device_type=m, params=dict(params.get(n, {}))
                )
                for n, m in extracted.instances.items()
            ]
            edges = [
                NetlistEdge(source=c[0].split(".")[0], target=c[1].split(".")[0])
                for c in extracted.connections
            ]
            ports = [
                NetlistNode(node_id=n, node_type="port", layer=p.split(".")[1])
                for n, p in extracted.ports.items()
            ]
            return cls(devices=devices, edges=edges, ports=ports)
        if hasattr(extracted, "devices") and hasattr(extracted, "connections"):
            devices = [NetlistNode(node_id=n, node_type="device") for n in extracted.devices]
            edges = [NetlistEdge(source=c[0], target=c[1]) for c in extracted.connections]
            return cls(devices=devices, edges=edges, ports=[])
        raise TypeError(f"不支持的网表类型: {type(extracted).__name__}")


class GraphIsomorphismLVSComparer:
    """图同构 LVS 比对引擎。

    用 networkx VF2 算法做图同构比对，替代 KLayout 的回溯匹配。

    理论依据: McKay & Piperno 2014; Cordella et al. 2004 (VF2)。
    复杂度: O(n²) 平均情况（VF2）。
    """

    def __init__(self, tolerance_config: dict | None = None):
        """初始化比对器。

        Args:
            tolerance_config: 容忍度配置，格式
                {"device_type": {"param_name": {"abs": 0.1, "rel": 0.05}}}
        """
        self.tolerance_config: dict = tolerance_config if tolerance_config else {}

    @staticmethod
    def _node_match(n1: dict, n2: dict) -> bool:
        """节点匹配函数（VF2 用），比较 node_type 和 device_type。"""
        return n1.get("node_type") == n2.get("node_type") and (
            n1.get("device_type", "") == n2.get("device_type", "")
        )

    @staticmethod
    def _edge_match(e1: dict, e2: dict) -> bool:
        """边匹配函数（VF2 用），比较 edge_type。"""
        return e1.get("edge_type", "wire") == e2.get("edge_type", "wire")

    def build_graph(self, netlist) -> nx.Graph:
        """将网表构建为 networkx 图。

        Args:
            netlist: ExtractedNetlist 或 PhotonicsNetlist 对象。
        Returns: networkx.Graph
        Raises: ValueError 网表为空; TypeError 不支持的网表类型。
        """
        if isinstance(netlist, PhotonicsNetlist):
            return netlist.to_graph()
        if hasattr(netlist, "devices") or hasattr(netlist, "instances"):
            return PhotonicsNetlist.from_extracted_netlist(netlist).to_graph()
        raise TypeError(f"不支持的网表类型: {type(netlist).__name__}")

    def compare(self, reference_netlist, extracted_netlist) -> PhotonicsLVSReport:
        """图同构比对两个网表。

        算法: 构图 → VF2 同构检验 → 同构则验证类型/参数/波导长度，否则报告差异。

        Args:
            reference_netlist: 参考网表（来自原理图）。
            extracted_netlist: 提取网表（来自版图）。

        Returns:
            PhotonicsLVSReport 比对报告。
        """
        start_time = time.time()
        ref_graph = self.build_graph(reference_netlist)
        ext_graph = self.build_graph(extracted_netlist)
        matcher = GraphMatcher(
            ref_graph, ext_graph, node_match=self._node_match, edge_match=self._edge_match
        )
        report = PhotonicsLVSReport()
        if not matcher.is_isomorphic():
            report.mismatches.append(self._non_iso_mismatch(ref_graph, ext_graph))
            report.comparison_time_s = time.time() - start_time
            return report
        mapping = dict(matcher.mapping)
        report.isomorphism_mapping = mapping
        report.device_type_mismatches = self._verify_device_types(mapping, ref_graph, ext_graph)
        report.param_mismatches = self._verify_params(mapping, ref_graph, ext_graph)
        report.waveguide_length_mismatches = self._verify_waveguide_lengths(
            mapping, ref_graph, ext_graph
        )
        report.port_orientation_mismatches = self._verify_port_orientation(
            mapping, ref_graph, ext_graph
        )
        report.mismatches = (
            report.device_type_mismatches
            + report.param_mismatches
            + report.waveguide_length_mismatches
            + report.port_orientation_mismatches
        )
        report.is_match = len(report.mismatches) == 0
        report.comparison_time_s = time.time() - start_time
        return report

    @staticmethod
    def _non_iso_mismatch(ref_graph: nx.Graph, ext_graph: nx.Graph) -> dict:
        """构造图不同构的不匹配项。"""
        return {
            "type": "graph_not_isomorphic",
            "message": "参考网表与提取网表图不同构",
            "ref_node_count": ref_graph.number_of_nodes(),
            "ext_node_count": ext_graph.number_of_nodes(),
            "ref_edge_count": ref_graph.number_of_edges(),
            "ext_edge_count": ext_graph.number_of_edges(),
        }

    def _verify_device_types(self, mapping: dict, ref_graph: nx.Graph, ext_graph: nx.Graph) -> list:
        """验证器件类型一致性。"""
        mismatches: list = []
        for ref_node, ext_node in mapping.items():
            ref_type = ref_graph.nodes[ref_node].get("device_type", "")
            ext_type = ext_graph.nodes[ext_node].get("device_type", "")
            if ref_type != ext_type:
                mm = {
                    "ref_device": ref_node,
                    "ext_device": ext_node,
                    "ref_type": ref_type,
                    "ext_type": ext_type,
                }
                mismatches.append(mm)
        return mismatches

    def _verify_params(self, mapping: dict, ref_graph: nx.Graph, ext_graph: nx.Graph) -> list:
        """验证器件参数一致性（使用容忍度配置）。

        容忍度公式: |ref - ext| <= abs_tol + rel_tol * |ref|
        来源: KLayout Netter tolerance API
        """
        mismatches: list = []
        for ref_node, ext_node in mapping.items():
            ref_attrs = ref_graph.nodes[ref_node]
            ext_attrs = ext_graph.nodes[ext_node]
            device_tol = self.tolerance_config.get(ref_attrs.get("device_type", ""), {})
            mismatches.extend(
                self._check_params(
                    ref_node,
                    ext_node,
                    ref_attrs.get("params", {}),
                    ext_attrs.get("params", {}),
                    device_tol,
                )
            )
        return mismatches

    @staticmethod
    def _check_params(ref_node, ext_node, ref_params, ext_params, device_tol) -> list:
        """检查单个器件的参数一致性。"""
        mismatches: list = []
        for key in set(ref_params) | set(ext_params):
            ref_val, ext_val = ref_params.get(key), ext_params.get(key)
            if key not in ref_params or key not in ext_params:
                reason = "missing"
            elif not GraphIsomorphismLVSComparer._params_match(
                ref_val, ext_val, device_tol.get(key, {})
            ):
                reason = "mismatch"
            else:
                continue
            mm = {"ref_device": ref_node, "ext_device": ext_node, "param": key, "reason": reason}
            mm.update(ref_value=ref_val, ext_value=ext_val)
            mismatches.append(mm)
        return mismatches

    @staticmethod
    def _params_match(ref_val, ext_val, tol: dict) -> bool:
        """判断两个参数值是否在容忍度范围内匹配。

        公式: |ref - ext| <= abs_tol + rel_tol * |ref|
        来源: KLayout Netter tolerance API
        """
        if not isinstance(ref_val, (int, float)) or not isinstance(ext_val, (int, float)):
            return ref_val == ext_val
        abs_tol = tol.get("abs", 0.0)
        rel_tol = tol.get("rel", 0.0)
        diff = abs(ref_val - ext_val)
        allowed = abs_tol + rel_tol * abs(ref_val)
        return diff <= allowed

    def _verify_waveguide_lengths(
        self, mapping: dict, ref_graph: nx.Graph, ext_graph: nx.Graph, tolerance_um: float = 1.0
    ) -> list:
        """验证波导长度一致性。

        公式: |L_ref - L_ext| <= tolerance_um
        来源: Chrostowski & Hochberg 2015, p.353（波导长度影响 MZI FSR）
        """
        mismatches: list = []
        ext_wires = self._get_wire_edges(ext_graph)
        for ref_src, ref_tgt, ref_len in self._get_wire_edges(ref_graph):
            ext_src, ext_tgt = mapping.get(ref_src), mapping.get(ref_tgt)
            if ext_src is None or ext_tgt is None:
                continue
            ext_len = self._find_edge_length(ext_wires, ext_src, ext_tgt)
            if ext_len is None:
                continue
            diff = abs(ref_len - ext_len)
            if diff > tolerance_um:
                mismatches.append(
                    {
                        "ref_device": f"{ref_src}-{ref_tgt}",
                        "ext_device": f"{ext_src}-{ext_tgt}",
                        "ref_length": ref_len,
                        "ext_length": ext_len,
                        "diff": diff,
                    }
                )
        return mismatches

    @staticmethod
    def _get_wire_edges(graph: nx.Graph) -> list:
        """获取图中所有 wire 类型的边及其长度。"""
        return [
            (u, v, data.get("length_um", 0.0))
            for u, v, data in graph.edges(data=True)
            if data.get("edge_type", "wire") == "wire"
        ]

    @staticmethod
    def _find_edge_length(edges: list, src: str, tgt: str) -> float | None:
        """在边列表中查找指定源/目标的边长度。

        合法：查找失败返回 None，调用方应检查（_verify_wire_lengths 中
        若返回 None 则跳过该边长校验，而非业务错误）。
        """
        for u, v, length in edges:
            if (u == src and v == tgt) or (u == tgt and v == src):
                return length
        return None  # 合法：边列表中无此 (src, tgt) 边，调用方应检查

    def _verify_port_orientation(
        self, mapping: dict, ref_graph: nx.Graph, ext_graph: nx.Graph
    ) -> list:
        """验证端口朝向一致性。

        来源: SiEPIC EBeam PDK 端口朝向标准
        https://github.com/SiEPIC/SiEPIC_EBeam_PDK
        """
        mismatches: list = []
        for ref_node, ext_node in mapping.items():
            ref_attrs = ref_graph.nodes[ref_node]
            if ref_attrs.get("node_type") != "port":
                continue
            ext_attrs = ext_graph.nodes[ext_node]
            ref_orient = self._extract_orientation(ref_attrs)
            ext_orient = self._extract_orientation(ext_attrs)
            if ref_orient != ext_orient:
                mismatches.append(
                    {
                        "ref_port": ref_node,
                        "ext_port": ext_node,
                        "ref_orientation": ref_orient,
                        "ext_orientation": ext_orient,
                    }
                )
        return mismatches

    @staticmethod
    def _extract_orientation(attrs: dict) -> str:
        """从节点属性提取端口朝向（params["orientation"] > layer > ""）。"""
        params = attrs.get("params", {})
        if "orientation" in params:
            return str(params["orientation"])
        return attrs.get("layer", "")


class EquivalenceHints:
    """等价提示集合（对齐 KLayout Netter same_nets/same_circuits/equivalent_pins）。

    来源: KLayout Netter API
    https://klayout.org/downloads/master/doc-qt4/about/lvs_ref_netter.html
    """

    def __init__(self):
        """初始化空提示集合。"""
        self._same_nets: list[tuple[str, str]] = []
        self._same_circuits: list[tuple[str, str]] = []
        self._equivalent_pins: dict[str, list[list[str]]] = {}
        self._tolerances: dict[str, dict[str, dict]] = {}
        self._max_res: float = 0.0
        self._min_caps: float = 0.0

    def same_nets(self, net1: str, net2: str) -> None:
        """声明两个 net 等价。"""
        if not (isinstance(net1, str) and isinstance(net2, str)):
            raise TypeError("same_nets 参数必须为字符串")
        self._same_nets.append((net1, net2))

    def same_circuits(self, circuit1: str, circuit2: str) -> None:
        """声明两个子电路等价。"""
        if not (isinstance(circuit1, str) and isinstance(circuit2, str)):
            raise TypeError("same_circuits 参数必须为字符串")
        self._same_circuits.append((circuit1, circuit2))

    def equivalent_pins(self, circuit: str, pins: list[str]) -> None:
        """声明电路的某些 pin 等价。"""
        if not isinstance(circuit, str):
            raise TypeError("equivalent_pins circuit 参数必须为字符串")
        if not isinstance(pins, list) or not all(isinstance(p, str) for p in pins):
            raise TypeError("equivalent_pins pins 参数必须为字符串列表")
        self._equivalent_pins.setdefault(circuit, []).append(list(pins))

    def tolerance(
        self, device_type: str, param: str, abs_tol: float = 0.0, rel_tol: float = 0.0
    ) -> None:
        """设置器件参数容忍度。"""
        if not (isinstance(device_type, str) and isinstance(param, str)):
            raise TypeError("tolerance device_type/param 参数必须为字符串")
        self._tolerances.setdefault(device_type, {})[param] = {
            "abs": float(abs_tol),
            "rel": float(rel_tol),
        }

    def max_res(self, value: float) -> None:
        """设置最大电阻（等效电阻合并阈值）。"""
        if not isinstance(value, (int, float)):
            raise TypeError("max_res 参数必须为数值")
        self._max_res = float(value)

    def min_caps(self, value: float) -> None:
        """设置最小电容（等效电容合并阈值）。"""
        if not isinstance(value, (int, float)):
            raise TypeError("min_caps 参数必须为数值")
        self._min_caps = float(value)

    def to_tolerance_config(self) -> dict:
        """将容忍度提示转换为 GraphIsomorphismLVSComparer 的 tolerance_config。

        Returns:
            tolerance_config 字典，格式
            {"device_type": {"param_name": {"abs": 0.1, "rel": 0.05}}}
        """
        return {dt: dict(params) for dt, params in self._tolerances.items()}


def _build_matcher(reference_netlist, extracted_netlist):
    """构建图并用 VF2 匹配，返回 (matcher, ref_graph, ext_graph)。

    Args:
        reference_netlist: 参考网表。
        extracted_netlist: 提取网表。

        Returns:
            (matcher, ref_graph, ext_graph) 元组。matcher 为 None 表示图不同构。

    Note:
        合法：matcher 为 None 表示参考/提取网表图不同构（LVS 不匹配），
        调用方应检查 matcher 是否为 None 并据此报告 LVS 失败，而非业务错误。
    """
    comparer = GraphIsomorphismLVSComparer()
    ref_graph = comparer.build_graph(reference_netlist)
    ext_graph = comparer.build_graph(extracted_netlist)
    matcher = GraphMatcher(
        ref_graph,
        ext_graph,
        node_match=GraphIsomorphismLVSComparer._node_match,
        edge_match=GraphIsomorphismLVSComparer._edge_match,
    )
    if not matcher.is_isomorphic():
        # 合法：图不同构 → matcher=None，调用方应检查并报告 LVS 不匹配
        return None, ref_graph, ext_graph
    return matcher, ref_graph, ext_graph


def verify_waveguide_length(
    reference_netlist, extracted_netlist, tolerance_um: float = 1.0
) -> list[dict]:
    """验证波导长度一致性（光子电路专用 LVS）。

    公式: |L_ref - L_ext| <= tolerance_um
    来源: Chrostowski & Hochberg, "Silicon Photonics Design", CUP 2015, p.353
    Args: reference_netlist, extracted_netlist, tolerance_um（μm，默认 1.0）
    Returns: 不匹配列表 [{ref_device, ext_device, ref_length, ext_length, diff}]
    """
    matcher, ref_graph, ext_graph = _build_matcher(reference_netlist, extracted_netlist)
    if matcher is None:
        return [{"type": "graph_not_isomorphic", "message": "无法比对波导长度，图不同构"}]
    comparer = GraphIsomorphismLVSComparer()
    return comparer._verify_waveguide_lengths(
        dict(matcher.mapping), ref_graph, ext_graph, tolerance_um
    )


def verify_port_orientation(reference_netlist, extracted_netlist) -> list[dict]:
    """验证端口朝向一致性（光子电路专用 LVS）。

    来源: SiEPIC EBeam PDK 端口朝向标准
    https://github.com/SiEPIC/SiEPIC_EBeam_PDK

    Args:
        reference_netlist: 参考网表。
        extracted_netlist: 提取网表。

    Returns:
        不匹配列表。
    """
    matcher, ref_graph, ext_graph = _build_matcher(reference_netlist, extracted_netlist)
    if matcher is None:
        return [{"type": "graph_not_isomorphic", "message": "无法比对端口朝向，图不同构"}]
    comparer = GraphIsomorphismLVSComparer()
    return comparer._verify_port_orientation(dict(matcher.mapping), ref_graph, ext_graph)


def run_graph_lvs(
    reference_netlist, extracted_netlist, tolerance_config: dict | None = None
) -> PhotonicsLVSReport:
    """图同构 LVS 统一入口。

    Args:
        reference_netlist: 参考网表。
        extracted_netlist: 提取网表。
        tolerance_config: 容忍度配置。

    Returns:
        PhotonicsLVSReport 比对报告。
    """
    comparer = GraphIsomorphismLVSComparer(tolerance_config=tolerance_config)
    return comparer.compare(reference_netlist, extracted_netlist)


__all__ = [
    "NetlistNode",
    "NetlistEdge",
    "PhotonicsNetlist",
    "PhotonicsLVSReport",
    "GraphIsomorphismLVSComparer",
    "EquivalenceHints",
    "verify_waveguide_length",
    "verify_port_orientation",
    "run_graph_lvs",
]
