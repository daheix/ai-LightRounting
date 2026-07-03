"""层次化 LVS 递归比对引擎（PoLaRIS v5.0 R9 路标）。

递归处理 top → mid → leaf cell 层次，每层独立做 VF2 图同构比对，
再向上合并结果，实现 ≥3 层层次化 LVS 递归比对。复用 graph_lvs.py 的
GraphIsomorphismLVSComparer（VF2 算法）做单层比对。

## IPO 三段式文档

### Input（输入）
- schematic_hierarchy: dict，原理图层次结构，每层含
  name/devices/connections/children 四字段
- layout_hierarchy: dict，版图层次结构，同上
- 每层 devices: list[NetlistNode] 或 list[dict]（含
  node_id/node_type/device_type/params/layer）
- 每层 connections: list[NetlistEdge] 或 list[tuple/list]
  （[(src, tgt), (src, tgt, length), ...]）
- tolerance_config: 单层器件参数容忍度配置（透传给单层比对器）

### Process（处理）
- 校验输入层次结构（字段完整、层级深度 ≥3）
- 递归遍历 top → mid → leaf cell
- 子 cell 按 name 一一配对，配对失败即 raise RuntimeError
- 每层用 VF2 图同构比对（networkx GraphMatcher，复用 graph_lvs.py）
- 同层两边 devices 均为空 → 跳过 VF2（纯层次化 cell）
- 同层仅一边 devices 为空 → raise RuntimeError（结构不匹配，R03）
- 将各层 LevelMatchResult 累积到 HierarchicalLVSReport

### Output（输出）
- HierarchicalLVSReport: 含 is_match/total_levels/level_results/
  all_mismatches/comparison_time_s

## 理论依据（R02 学术诚信，≥5 文献 URL）

1. KLayout LVS Compare 文档（hierarchical compare 概念）
   https://www.klayout.org/downloads/master/doc-qt5/manual/lvs_compare.html
2. Siemens Calibre nmLVS hierarchical compare（层次化 LVS 工业实现）
   https://eda.sw.siemens.com/en-US/calibre/calibre-nm-lvs-replay/
3. Cordella et al. 2004, "A (sub)graph isomorphism algorithm for matching
   large graphs", IEEE TPAMI 26(10):1367-1372, DOI: 10.1109/TPAMI.2004.75
   https://ieeexplore.ieee.org/document/1266305
4. McKay & Piperno 2014, "Practical Graph Isomorphism, II",
   J. Symbolic Computation 60:94-112, DOI: 10.1016/j.jsc.2013.09.003
   https://www.sciencedirect.com/science/article/pii/S0747717113001930
5. Lavagno et al. (Eds.) 2021, "Electronic Design Automation for IC
   Systems Handbook", Springer/CRC, ISBN 978-1-4398-3562-2
   （层次化 LVS 概念，Chapter on Layout vs. Schematic）
   https://link.springer.com/referencework/10.1007/978-1-4614-5190-3
6. NetworkX GraphMatcher 文档（VF2 实现接口）
   https://networkx.org/documentation/stable/reference/algorithms/isomorphism.html

合规: R02 学术诚信 / R03 禁止 fall-back（结构不匹配即 raise）/
      R04 不参与 GPU（纯 networkx）/ R05 无 TODO / R13 不保留 v4 兼容。
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from .graph_lvs import (
    GraphIsomorphismLVSComparer,
    NetlistEdge,
    NetlistNode,
    PhotonicsNetlist,
)

# 至少 3 层（top/mid/leaf），来源: 任务 R9 路标要求 ≥3 层层次化 LVS
_MIN_HIERARCHY_LEVELS = 3
# 层次节点必需字段
_REQUIRED_FIELDS = ("name", "devices", "connections", "children")


@dataclass
class LevelMatchResult:
    """单层 LVS 比对结果。

    Attributes:
        level: 层级编号（0=top, 1=mid, 2=leaf, ...）。
        cell_name: 该层 cell 名称。
        is_match: 该层 VF2 图同构比对是否匹配。
        mismatches: 该层不匹配项列表（透传 PhotonicsLVSReport.mismatches）。
        isomorphism_mapping: 该层图同构映射（ref_node → ext_node）。
    """

    level: int
    cell_name: str
    is_match: bool
    mismatches: list = field(default_factory=list)
    isomorphism_mapping: dict = field(default_factory=dict)


@dataclass
class HierarchicalLVSReport:
    """层次化 LVS 完整报告。

    Attributes:
        is_match: 全层次是否完全匹配（所有层均 is_match=True）。
        total_levels: 总层级数（最大深度）。
        level_results: 每层比对结果列表 [LevelMatchResult]。
        all_mismatches: 所有不匹配项汇总（所有层 mismatches 合并）。
        comparison_time_s: 比对耗时（秒）。
    """

    is_match: bool = False
    total_levels: int = 0
    level_results: list = field(default_factory=list)  # list[LevelMatchResult]
    all_mismatches: list = field(default_factory=list)
    comparison_time_s: float = 0.0


class HierarchicalLVS:
    """层次化 LVS 递归比对引擎。

    递归处理 top → mid → leaf cell 层次，每层独立做 VF2 图同构比对，
    再向上合并结果。复用 GraphIsomorphismLVSComparer 做单层比对。

    理论依据: Cordella 2004 (VF2); McKay & Piperno 2014; Calibre nmLVS
    hierarchical compare; KLayout LVS Compare; Springer EDA Handbook。

    错误处理（R03 禁止 fall-back）:
    - 输入无效（缺字段/非 dict/层级数 <3）→ raise ValueError
    - 层次结构不匹配（children 数量/name 不一致/单边 devices 为空）
      → raise RuntimeError
    """

    def __init__(self, tolerance_config: dict | None = None):
        """初始化层次化 LVS 比对器。

        Args:
            tolerance_config: 单层器件参数容忍度配置，格式
                {"device_type": {"param_name": {"abs": 0.1, "rel": 0.05}}}，
                透传给 GraphIsomorphismLVSComparer。
        """
        self._comparer = GraphIsomorphismLVSComparer(
            tolerance_config=tolerance_config if tolerance_config else {}
        )

    def compare_hierarchical(
        self, schematic_hierarchy: dict, layout_hierarchy: dict
    ) -> HierarchicalLVSReport:
        """主入口：递归比对原理图与版图的层次结构。

        Args:
            schematic_hierarchy: 原理图层次结构 dict，含
                name/devices/connections/children。
            layout_hierarchy: 版图层次结构 dict，同上。

        Returns:
            HierarchicalLVSReport 完整报告。

        Raises:
            ValueError: 输入无效（缺字段、非 dict、层级数 <3）。
            RuntimeError: 层次结构不匹配（children 数量/name 不一致、
                单边 devices 为空）。
        """
        start_time = time.time()
        self._validate_node(schematic_hierarchy, "schematic_hierarchy")
        self._validate_node(layout_hierarchy, "layout_hierarchy")
        sch_depth = self._compute_depth(schematic_hierarchy)
        lay_depth = self._compute_depth(layout_hierarchy)
        if sch_depth < _MIN_HIERARCHY_LEVELS:
            raise ValueError(
                f"原理图层次深度 {sch_depth} < 最小要求 {_MIN_HIERARCHY_LEVELS}"
            )
        if lay_depth < _MIN_HIERARCHY_LEVELS:
            raise ValueError(
                f"版图层次深度 {lay_depth} < 最小要求 {_MIN_HIERARCHY_LEVELS}"
            )
        report = HierarchicalLVSReport(total_levels=sch_depth)
        self._compare_recursive(schematic_hierarchy, layout_hierarchy, 0, report)
        report.is_match = all(r.is_match for r in report.level_results)
        report.comparison_time_s = time.time() - start_time
        return report

    @staticmethod
    def _validate_node(node: Any, label: str) -> None:
        """校验层次节点结构（dict 含必需字段且类型正确）。

        Args:
            node: 待校验节点。
            label: 节点标签（错误信息用）。

        Raises:
            ValueError: 非 dict、缺字段或字段类型错误。
        """
        if not isinstance(node, dict):
            raise ValueError(
                f"{label} 必须为 dict，实际类型 {type(node).__name__}"
            )
        for fld in _REQUIRED_FIELDS:
            if fld not in node:
                raise ValueError(f"{label} 缺少必需字段 '{fld}'")
        if not isinstance(node["name"], str) or not node["name"]:
            raise ValueError(f"{label}.name 必须为非空字符串")
        if not isinstance(node["children"], list):
            raise ValueError(f"{label}.children 必须为列表")
        if not isinstance(node["devices"], list):
            raise ValueError(f"{label}.devices 必须为列表")
        if not isinstance(node["connections"], list):
            raise ValueError(f"{label}.connections 必须为列表")
        for child in node["children"]:
            HierarchicalLVS._validate_node(child, f"{label}.children[]")

    @staticmethod
    def _compute_depth(node: dict) -> int:
        """计算层次结构最大深度（递归）。

        Args:
            node: 层次节点 dict（已通过 _validate_node 校验）。

        Returns:
            深度（叶子节点返回 1，每深入一层 +1）。
        """
        children = node.get("children", [])
        if not children:
            return 1
        return 1 + max(HierarchicalLVS._compute_depth(c) for c in children)

    def _compare_recursive(
        self,
        sch_node: dict,
        lay_node: dict,
        level: int,
        report: HierarchicalLVSReport,
    ) -> None:
        """递归比对单层及其子层。

        Args:
            sch_node: 原理图当前层节点。
            lay_node: 版图当前层节点。
            level: 当前层级编号。
            report: 累积报告。

        Raises:
            RuntimeError: cell name 不匹配、子 cell 数量不一致或
                子 cell name 无法一一配对。
        """
        if sch_node["name"] != lay_node["name"]:
            raise RuntimeError(
                f"第 {level} 层 cell name 不匹配: "
                f"原理图='{sch_node['name']}' 版图='{lay_node['name']}'"
            )
        level_result = self._compare_single_level(sch_node, lay_node, level)
        report.level_results.append(level_result)
        report.all_mismatches.extend(level_result.mismatches)
        sch_children = sch_node["children"]
        lay_children = lay_node["children"]
        if len(sch_children) != len(lay_children):
            raise RuntimeError(
                f"cell '{sch_node['name']}' 子 cell 数量不匹配: "
                f"原理图={len(sch_children)} 版图={len(lay_children)}"
            )
        paired = self._pair_children_by_name(
            sch_children, lay_children, sch_node["name"]
        )
        for sch_child, lay_child in paired:
            self._compare_recursive(sch_child, lay_child, level + 1, report)

    @staticmethod
    def _pair_children_by_name(
        sch_children: list, lay_children: list, parent_name: str
    ) -> list:
        """按 name 一一配对子 cell。

        Args:
            sch_children: 原理图子 cell 列表。
            lay_children: 版图子 cell 列表。
            parent_name: 父 cell 名称（错误信息用）。

        Returns:
            配对列表 [(sch_child, lay_child), ...]，顺序按原理图 children。

        Raises:
            RuntimeError: 子 cell name 无法一一对应（缺失或多余）。
        """
        lay_by_name: dict = {c["name"]: c for c in lay_children}
        paired: list = []
        for sch_child in sch_children:
            name = sch_child["name"]
            if name not in lay_by_name:
                raise RuntimeError(
                    f"父 cell '{parent_name}' 下: 原理图子 cell '{name}' "
                    f"在版图中无对应"
                )
            paired.append((sch_child, lay_by_name.pop(name)))
        if lay_by_name:
            extra = ", ".join(sorted(lay_by_name.keys()))
            raise RuntimeError(
                f"父 cell '{parent_name}' 下: 版图多余子 cell: {extra}"
            )
        return paired

    def _compare_single_level(
        self, sch_node: dict, lay_node: dict, level: int
    ) -> LevelMatchResult:
        """比对单层 cell（VF2 图同构）。

        策略（R03 禁止 fall-back）:
        - 两边 devices 均为空 → 跳过 VF2，该层 is_match=True
          （纯层次化 cell，结构已由 _compare_recursive 校验）
        - 仅一边 devices 为空 → raise RuntimeError（结构不匹配）
        - 两边均非空 → 用 GraphIsomorphismLVSComparer 做 VF2 图同构比对

        Args:
            sch_node: 原理图当前层节点。
            lay_node: 版图当前层节点。
            level: 当前层级编号。

        Returns:
            LevelMatchResult 该层比对结果。

        Raises:
            RuntimeError: 单边 devices 为空（结构不匹配）。
        """
        sch_devices = sch_node["devices"]
        lay_devices = lay_node["devices"]
        cell_name = sch_node["name"]
        if not sch_devices and not lay_devices:
            return LevelMatchResult(
                level=level, cell_name=cell_name, is_match=True
            )
        if not sch_devices or not lay_devices:
            raise RuntimeError(
                f"cell '{cell_name}' 器件数量不匹配（单边为空）: "
                f"原理图={len(sch_devices)} 版图={len(lay_devices)}"
            )
        sch_netlist = self._build_netlist(sch_node)
        lay_netlist = self._build_netlist(lay_node)
        sub_report = self._comparer.compare(sch_netlist, lay_netlist)
        return LevelMatchResult(
            level=level,
            cell_name=cell_name,
            is_match=sub_report.is_match,
            mismatches=list(sub_report.mismatches),
            isomorphism_mapping=dict(sub_report.isomorphism_mapping),
        )

    @staticmethod
    def _build_netlist(node: dict) -> PhotonicsNetlist:
        """从层次节点构建 PhotonicsNetlist。

        支持两种 devices 格式:
        - NetlistNode 对象列表
        - dict 列表（含 node_id/node_type/device_type/params/layer）

        支持两种 connections 格式:
        - NetlistEdge 对象列表
        - tuple/list 列表 [(src, tgt), (src, tgt, length), ...]

        Args:
            node: 层次节点 dict（已校验）。

        Returns:
            PhotonicsNetlist 网表对象（devices/edges/ports）。
        """
        devices = [HierarchicalLVS._coerce_device(d) for d in node["devices"]]
        edges = [HierarchicalLVS._coerce_edge(e) for e in node["connections"]]
        ports = [d for d in devices if d.node_type == "port"]
        return PhotonicsNetlist(devices=devices, edges=edges, ports=ports)

    @staticmethod
    def _coerce_device(item: Any) -> NetlistNode:
        """将 device 项统一转换为 NetlistNode。

        Args:
            item: NetlistNode 对象 或 dict。

        Returns:
            NetlistNode 对象。

        Raises:
            ValueError: 格式不支持或 dict 缺 node_id 字段。
        """
        if isinstance(item, NetlistNode):
            return item
        if isinstance(item, dict):
            if "node_id" not in item:
                raise ValueError(f"device dict 缺少 'node_id' 字段: {item}")
            return NetlistNode(
                node_id=item["node_id"],
                node_type=item.get("node_type", "device"),
                device_type=item.get("device_type", ""),
                params=dict(item.get("params", {})),
                layer=item.get("layer", ""),
            )
        raise ValueError(f"不支持的 device 格式: {type(item).__name__}")

    @staticmethod
    def _coerce_edge(item: Any) -> NetlistEdge:
        """将 connection 项统一转换为 NetlistEdge。

        Args:
            item: NetlistEdge 对象 或 tuple/list。

        Returns:
            NetlistEdge 对象。

        Raises:
            ValueError: 格式不支持或元组长度不足 2。
        """
        if isinstance(item, NetlistEdge):
            return item
        if isinstance(item, (tuple, list)):
            if len(item) < 2:
                raise ValueError(f"connection 元组长度不足 2: {item}")
            src, tgt = str(item[0]), str(item[1])
            length = float(item[2]) if len(item) >= 3 else 0.0
            return NetlistEdge(source=src, target=tgt, length_um=length)
        raise ValueError(f"不支持的 connection 格式: {type(item).__name__}")


def run_hierarchical_lvs(
    schematic_hierarchy: dict,
    layout_hierarchy: dict,
    tolerance_config: dict | None = None,
) -> HierarchicalLVSReport:
    """层次化 LVS 统一入口。

    Args:
        schematic_hierarchy: 原理图层次结构 dict。
        layout_hierarchy: 版图层次结构 dict。
        tolerance_config: 单层器件参数容忍度配置。

    Returns:
        HierarchicalLVSReport 完整报告。

    Raises:
        ValueError: 输入无效（缺字段/层级数 <3）。
        RuntimeError: 层次结构不匹配（children/name 不一致）。
    """
    comparer = HierarchicalLVS(tolerance_config=tolerance_config)
    return comparer.compare_hierarchical(schematic_hierarchy, layout_hierarchy)


__all__ = [
    "HierarchicalLVS",
    "HierarchicalLVSReport",
    "LevelMatchResult",
    "run_hierarchical_lvs",
]
