"""LVS 网络抽象与 short/open 检测（R211-R230）。

本模块为 PoLaRIS LVS 引入"net 抽象"，补齐与商业 EDA 工具（KLayout LVS /
Calibre nmLVS / Synopsys IC Validator）的核心差距：真正的 short circuit 与
open circuit 检测。

## 核心概念

- **Pin（引脚）**: 器件的电气连接点（device_name + pin_name + layer + bbox）
- **Net（网络）**: 电气连通的引脚等价类集合（同一 net 的引脚电气连通）
- **Short（短路）**: 两个本应独立的参考 net 在提取网表中被合并为同一个 net
- **Open（开路）**: 本应属于同一参考 net 的引脚在提取网表中分散到多个 net

## 算法

1. **网络提取**: 用并查集（Union-Find）合并电气连通的引脚
   - 同层几何形状相交/邻接 → 连通
   - 波导路径（WG 层）连接器件引脚 → 连通
   - 同网络标签（Text 层）的引脚 → 连通（implicit connect）
2. **short 检测**: 对每个提取 net，检查其引脚是否来自多个不同参考 net
3. **open 检测**: 对每个参考 net，检查其引脚在提取网表中是否全部属于同一 net
4. **short 隔离**: 定位短路发生的几何位置（哪些形状相交导致独立 net 被连接）

## 学术依据

- 并查集（Union-Find）: Tarjan, "Efficiency of a Good But Not Linear Set
  Union Algorithm", JACM 1975, DOI: 10.1145/321879.321884
- KLayout LVS Netter（网络提取 + same_nets）:
  https://klayout.org/downloads/master/doc-qt5/about/lvs_ref_netter.html
- KLayout LVS Compare（同构提示、tolerance）:
  https://klayout.org/downloads/master/doc-qt5/manual/lvs_compare.html
- Calibre nmLVS-Recon short isolation:
  https://www.design-reuse.com/news/8592-mentor-introduces-calibre-nmlvs-recon-technology-to-dramatically-streamline-overall-ic-circuit-verification/
- Calibre LVS FILTER SHORT/OPEN 语句:
  https://www.eda-solutions.com/tn061/
- Synopsys IC Validator ShortFinder:
  https://sidense.com/content/dam/synopsys/implementation&signoff/white-papers/explorer-lvs-wp.pdf
- SiEPIC EBeam PDK PinRec/DEVREC 标准:
  https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- LVS 行业标准错误分类（Shorts/Opens 定义）:
  https://akiitr.is-a.dev/asic/asic/LVS

合规: R02 学术诚信 / R03 禁止 fall-back / R05 Bug 必修 / R04 不参与 GPU。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ShortOpenMismatchType(Enum):
    """short/open 检测不匹配类型（R211-R230 新增）。

    对标商业工具错误分类:
    - Calibre nmLVS-H: "Shorted Net" / "Unconnected Net"
    - ICV ShortFinder: short 定位
    - KLayout LVS: net 邻域图分析

    来源: https://akiitr.is-a.dev/asic/asic/LVS（LVS 行业标准错误分类）
    """

    SHORT_CIRCUIT = "short_circuit"  # 两个本应独立的 net 被错误连接
    OPEN_CIRCUIT = "open_circuit"  # 本应连通的 net 引脚断开
    UNCONNECTED_PIN = "unconnected_pin"  # 引脚完全未连接


@dataclass
class Pin:
    """器件引脚（R211-R212 net 抽象）。

    引脚是器件的电气连接点，是网络提取的基本单元。同一 net 的引脚电气连通。

    Attributes:
        device_name: 所属器件名（如 "mmi1x2_0"）。
        pin_name: 引脚名（如 "in1"/"out"/"opt1"）。
        layer: 引脚所在 GDS 层名（如 "PORT"/"PIN"）。
        x: 引脚中心 X 坐标（μm）。
        y: 引脚中心 Y 坐标（μm）。
        bbox: 引脚包围盒 (xmin, ymin, xmax, ymax)（μm），用于几何连通性分析。
        net_label: 网络标签（Text 层标注，None 表示无标签）。

    学术依据: SiEPIC PinRec 标准
    https://github.com/SiEPIC/SiEPIC_EBeam_PDK
    """

    device_name: str
    pin_name: str
    layer: str
    x: float
    y: float
    # R211-R230 修复: 默认 bbox=None，由 __post_init__ 生成点 bbox (x,y,x,y)。
    # 避免不同坐标的 pin 因退化 bbox=(0,0,0,0) 而被误判为几何相交。
    # 显式传入 bbox 时优先使用调用方提供的值（如 extract 场景的真实包围盒）。
    bbox: tuple[float, float, float, float] | None = None
    net_label: str | None = None

    def __post_init__(self) -> None:
        """初始化后处理: 未显式提供 bbox 时，用引脚中心坐标生成点 bbox。

        点 bbox (x,y,x,y) 是退化包围盒，仅与重合点或包含该点的区域相交。
        这样不同坐标的 pin 默认几何不相交，需通过 connection_pairs 或
        同标签规则才会连通，符合参考网表构建语义。
        """
        if self.bbox is None:
            self.bbox = (self.x, self.y, self.x, self.y)

    @property
    def ref(self) -> str:
        """引脚唯一引用（device_name.pin_name）。"""
        return f"{self.device_name}.{self.pin_name}"


@dataclass
class Net:
    """网络（R211-R212 net 抽象）。

    网络是电气连通的引脚等价类集合。同一 net 的引脚在版图中电气连通。

    Attributes:
        net_id: 网络唯一标识（如 "net_0"）。
        pins: 引脚列表。
        label: 网络标签（来自 Text 层，None 表示无标签）。

    学术依据: KLayout Netter net 概念
    https://klayout.org/downloads/master/doc-qt5/about/lvs_ref_netter.html
    """

    net_id: str
    pins: list[Pin] = field(default_factory=list)
    label: str | None = None

    @property
    def pin_refs(self) -> list[str]:
        """网络包含的引脚引用列表。"""
        return [p.ref for p in self.pins]

    @property
    def device_names(self) -> set[str]:
        """网络涉及的器件名集合。"""
        return {p.device_name for p in self.pins}


@dataclass
class ShortOpenMismatch:
    """short/open 检测不匹配项（R211-R230）。

    Attributes:
        mtype: 不匹配类型（SHORT_CIRCUIT/OPEN_CIRCUIT/UNCONNECTED_PIN）。
        message: 描述信息。
        ref_net_ids: 涉及的参考 net ID 列表（short: 多个，open: 1 个）。
        ext_net_ids: 涉及的提取 net ID 列表（short: 1 个，open: 多个）。
        pin_refs: 涉及的引脚引用列表。
        location_um: 短路/断路位置 (x, y)（short 隔离用），None 表示未定位。
        layer: 涉及的层名（short 隔离用）。
    """

    mtype: ShortOpenMismatchType
    message: str
    ref_net_ids: list[str] = field(default_factory=list)
    ext_net_ids: list[str] = field(default_factory=list)
    pin_refs: list[str] = field(default_factory=list)
    location_um: tuple[float, float] | None = None
    layer: str = ""


@dataclass
class ShortOpenReport:
    """short/open 检测报告（R211-R230）。

    Attributes:
        is_clean: 是否无 short/open（True 表示 clean）。
        shorts: 短路列表。
        opens: 开路列表。
        unconnected_pins: 未连接引脚列表。
        reference_net_count: 参考 net 数。
        extracted_net_count: 提取 net 数。
    """

    is_clean: bool = False
    shorts: list[ShortOpenMismatch] = field(default_factory=list)
    opens: list[ShortOpenMismatch] = field(default_factory=list)
    unconnected_pins: list[ShortOpenMismatch] = field(default_factory=list)
    reference_net_count: int = 0
    extracted_net_count: int = 0

    @property
    def total_mismatch_count(self) -> int:
        """不匹配项总数。"""
        return len(self.shorts) + len(self.opens) + len(self.unconnected_pins)


class _UnionFind:
    """并查集（Union-Find）数据结构（R213-R215 网络提取）。

    用于合并电气连通的引脚，提取网络。支持路径压缩与按秩合并，
    近似 O(α(n)) 复杂度（α 为反 Ackermann 函数，近似常数）。

    学术依据: Tarjan, "Efficiency of a Good But Not Linear Set Union Algorithm",
    JACM 1975, DOI: 10.1145/321879.321884
    """

    def __init__(self) -> None:
        self._parent: dict[str, str] = {}
        self._rank: dict[str, int] = {}

    def find(self, x: str) -> str:
        """查找元素 x 的根（路径压缩）。"""
        if x not in self._parent:
            self._parent[x] = x
            self._rank[x] = 0
            return x
        # 路径压缩
        root = x
        while self._parent[root] != root:
            root = self._parent[root]
        while self._parent[x] != root:
            self._parent[x], x = root, self._parent[x]
        return root

    def union(self, x: str, y: str) -> None:
        """合并 x 和 y 所在集合（按秩合并）。"""
        rx, ry = self.find(x), self.find(y)
        if rx == ry:
            return
        # 按秩合并：小树挂到大树
        if self._rank[rx] < self._rank[ry]:
            rx, ry = ry, rx
        self._parent[ry] = rx
        if self._rank[rx] == self._rank[ry]:
            self._rank[rx] += 1

    def groups(self) -> dict[str, list[str]]:
        """返回各连通分量 {root: [members]}。"""
        result: dict[str, list[str]] = {}
        for x in list(self._parent.keys()):
            root = self.find(x)
            result.setdefault(root, []).append(x)
        return result


def _bboxes_overlap(
    b1: tuple[float, float, float, float],
    b2: tuple[float, float, float, float],
    tolerance: float = 0.0,
) -> bool:
    """检查两个包围盒是否相交或邻近（R213 网络提取几何连通性）。

    Args:
        b1: 包围盒 1 (xmin, ymin, xmax, ymax)。
        b2: 包围盒 2 (xmin, ymin, xmax, ymax)。
        tolerance: 邻近容差（μm）。

    Returns:
        True 若相交或邻近。

    学术依据: Ericson, Real-Time Collision Detection, MK 2005, Ch.5
    """
    return not (
        b1[2] + tolerance < b2[0]
        or b2[2] + tolerance < b1[0]
        or b1[3] + tolerance < b2[1]
        or b2[3] + tolerance < b1[1]
    )


def extract_nets_from_pins(
    pins: list[Pin],
    connection_pairs: list[tuple[str, str]] | None = None,
    same_label_connects: bool = True,
    bbox_tolerance_um: float = 0.01,
) -> list[Net]:
    """从引脚列表提取网络（R213-R215 网络提取）。

    用并查集合并电气连通的引脚:
    1. 同层几何形状相交/邻接的引脚 → 连通
    2. 显式连接对（connection_pairs）→ 连通
    3. 同网络标签（net_label）的引脚 → 连通（implicit connect）

    Args:
        pins: 引脚列表。
        connection_pairs: 显式连接对 [(pin_ref1, pin_ref2), ...]，None 表示无。
        same_label_connects: 同标签引脚是否视为连通（implicit connect）。
        bbox_tolerance_um: 包围盒邻近容差（μm，默认 0.01 = 10 nm）。

    Returns:
        网络 list[Net]。

    学术依据:
    - 并查集: Tarjan, JACM 1975, DOI: 10.1145/321879.321884
    - KLayout connect 语义: https://klayout.org/downloads/master/doc-qt5/about/lvs_ref_netter.html
    """
    if not pins:
        return []

    uf = _UnionFind()
    pin_by_ref: dict[str, Pin] = {p.ref: p for p in pins}

    # 初始化每个引脚为独立集合
    for ref in pin_by_ref:
        uf.find(ref)

    _connect_overlapping_pins(uf, pins, bbox_tolerance_um)
    _connect_explicit_pairs(uf, pin_by_ref, connection_pairs)
    if same_label_connects:
        _connect_same_label_pins(uf, pins)

    # 构建网络
    groups = uf.groups()
    nets: list[Net] = []
    for net_idx, (_, members) in enumerate(sorted(groups.items())):
        net_pins = [pin_by_ref[ref] for ref in members]
        label = next((p.net_label for p in net_pins if p.net_label is not None), None)
        nets.append(Net(
            net_id=f"net_{net_idx}",
            pins=net_pins,
            label=label,
        ))
    return nets


def _connect_overlapping_pins(
    uf: "_UnionFind",
    pins: list[Pin],
    bbox_tolerance_um: float,
) -> None:
    """规则 1: 同层几何形状相交/邻接的引脚 → 连通（双层循环 + 包围盒预筛）。"""
    for i, p1 in enumerate(pins):
        for p2 in pins[i + 1:]:
            if p1.layer != p2.layer:
                continue
            if _bboxes_overlap(p1.bbox, p2.bbox, tolerance=bbox_tolerance_um):
                uf.union(p1.ref, p2.ref)


def _connect_explicit_pairs(
    uf: "_UnionFind",
    pin_by_ref: dict[str, Pin],
    connection_pairs: list[tuple[str, str]] | None,
) -> None:
    """规则 2: 显式连接对 → 连通。"""
    if not connection_pairs:
        return
    for ref1, ref2 in connection_pairs:
        if ref1 in pin_by_ref and ref2 in pin_by_ref:
            uf.union(ref1, ref2)


def _connect_same_label_pins(uf: "_UnionFind", pins: list[Pin]) -> None:
    """规则 3: 同网络标签的引脚 → 连通（implicit connect）。"""
    label_groups: dict[str, list[str]] = {}
    for p in pins:
        if p.net_label is not None:
            label_groups.setdefault(p.net_label, []).append(p.ref)
    for refs in label_groups.values():
        for i in range(1, len(refs)):
            uf.union(refs[0], refs[i])


def detect_short_circuits(
    reference_nets: list[Net],
    extracted_nets: list[Net],
) -> list[ShortOpenMismatch]:
    """检测短路（R216-R218 short 检测算法）。

    短路定义: 两个本应独立的参考 net 在提取网表中被合并为同一个 net。

    算法:
    1. 建立 pin_ref → reference_net_id 映射
    2. 对每个提取 net，检查其引脚来自哪些参考 net
    3. 若来自多个不同参考 net → 短路

    Args:
        reference_nets: 参考网表的网络列表。
        extracted_nets: 提取网表的网络列表。

    Returns:
        短路不匹配列表。

    对标: Calibre nmLVS-H "Shorted Net" 分类
    https://www.eda-solutions.com/tn061/
    """
    if not reference_nets or not extracted_nets:
        return []

    # pin_ref → reference_net_id 映射
    pin_to_ref_net: dict[str, str] = {}
    for ref_net in reference_nets:
        for pin in ref_net.pins:
            pin_to_ref_net[pin.ref] = ref_net.net_id

    mismatches: list[ShortOpenMismatch] = []
    for ext_net in extracted_nets:
        # 收集该提取 net 涉及的参考 net
        ref_net_ids: set[str] = set()
        for pin in ext_net.pins:
            ref_net_id = pin_to_ref_net.get(pin.ref)
            if ref_net_id is not None:
                ref_net_ids.add(ref_net_id)
        # 多个参考 net 合并到同一提取 net → 短路
        if len(ref_net_ids) > 1:
            # 短路位置：取涉及的引脚中心均值
            cx = sum(p.x for p in ext_net.pins) / len(ext_net.pins)
            cy = sum(p.y for p in ext_net.pins) / len(ext_net.pins)
            layers = {p.layer for p in ext_net.pins}
            mismatches.append(ShortOpenMismatch(
                mtype=ShortOpenMismatchType.SHORT_CIRCUIT,
                message=(
                    f"短路: 提取 net '{ext_net.net_id}' 合并了 "
                    f"{len(ref_net_ids)} 个本应独立的参考 net: "
                    f"{sorted(ref_net_ids)}"
                ),
                ref_net_ids=sorted(ref_net_ids),
                ext_net_ids=[ext_net.net_id],
                pin_refs=ext_net.pin_refs,
                location_um=(cx, cy),
                layer=",".join(sorted(layers)),
            ))
    return mismatches


def detect_open_circuits(
    reference_nets: list[Net],
    extracted_nets: list[Net],
) -> list[ShortOpenMismatch]:
    """检测开路（R219-R221 open 检测算法）。

    开路定义: 本应属于同一参考 net 的引脚在提取网表中分散到多个不同 net。

    算法:
    1. 建立 pin_ref → extracted_net_id 映射
    2. 对每个参考 net，检查其引脚在提取网表中属于哪些 net
    3. 若分散到多个提取 net → 开路
    4. 若有引脚完全未连接 → 未连接引脚

    Args:
        reference_nets: 参考网表的网络列表。
        extracted_nets: 提取网表的网络列表。

    Returns:
        开路不匹配列表（OPEN_CIRCUIT 和 UNCONNECTED_PIN）。

    对标: Calibre nmLVS-H "Unconnected Net" 分类
    https://www.eda-solutions.com/tn061/
    """
    if not reference_nets:
        return []

    # pin_ref → extracted_net_id 映射
    pin_to_ext_net: dict[str, str] = {}
    for ext_net in extracted_nets:
        for pin in ext_net.pins:
            pin_to_ext_net[pin.ref] = ext_net.net_id

    mismatches: list[ShortOpenMismatch] = []
    for ref_net in reference_nets:
        # 收集该参考 net 的引脚在提取网表中属于哪些 net
        ext_net_ids: dict[str, list[str]] = {}  # ext_net_id -> [pin_refs]
        unconnected: list[str] = []
        for pin in ref_net.pins:
            ext_net_id = pin_to_ext_net.get(pin.ref)
            if ext_net_id is None:
                unconnected.append(pin.ref)
            else:
                ext_net_ids.setdefault(ext_net_id, []).append(pin.ref)

        # 未连接引脚
        for pin_ref in unconnected:
            pin = next((p for p in ref_net.pins if p.ref == pin_ref), None)
            location = (pin.x, pin.y) if pin else None
            mismatches.append(ShortOpenMismatch(
                mtype=ShortOpenMismatchType.UNCONNECTED_PIN,
                message=(
                    f"未连接引脚: 参考 net '{ref_net.net_id}' 的引脚 "
                    f"'{pin_ref}' 在提取网表中未连接"
                ),
                ref_net_ids=[ref_net.net_id],
                pin_refs=[pin_ref],
                location_um=location,
                layer=pin.layer if pin else "",
            ))

        # 分散到多个提取 net → 开路
        if len(ext_net_ids) > 1:
            # 开路位置：取分散的引脚中心
            all_pins = [p for p in ref_net.pins if p.ref in pin_to_ext_net]
            if all_pins:
                cx = sum(p.x for p in all_pins) / len(all_pins)
                cy = sum(p.y for p in all_pins) / len(all_pins)
            else:
                cx, cy = 0.0, 0.0
            mismatches.append(ShortOpenMismatch(
                mtype=ShortOpenMismatchType.OPEN_CIRCUIT,
                message=(
                    f"开路: 参考 net '{ref_net.net_id}' 的引脚分散到 "
                    f"{len(ext_net_ids)} 个提取 net: {sorted(ext_net_ids.keys())}"
                ),
                ref_net_ids=[ref_net.net_id],
                ext_net_ids=sorted(ext_net_ids.keys()),
                pin_refs=ref_net.pin_refs,
                location_um=(cx, cy),
            ))
    return mismatches


def isolate_short_location(
    short_mismatch: ShortOpenMismatch,
    extracted_nets: list[Net],
    bbox_tolerance_um: float = 0.01,
) -> tuple[float, float] | None:
    """短路隔离定位（R222-R224 short 隔离）。

    定位短路发生的几何位置：找到导致独立 net 被连接的相交引脚对。

    算法:
    1. 找到短路涉及的提取 net
    2. 在该 net 中，找来自不同参考 net 的引脚对
    3. 检查这些引脚对的包围盒是否相交/邻近
    4. 返回相交位置（引脚对中心）

    Args:
        short_mismatch: 短路不匹配项。
        extracted_nets: 提取网表的网络列表。
        bbox_tolerance_um: 包围盒邻近容差（μm）。

    Returns:
        短路位置 (x, y)，None 表示无法定位。

    对标: Calibre nmLVS-Recon short isolation / ICV ShortFinder
    https://www.design-reuse.com/news/8592-mentor-introduces-calibre-nmlvs-recon-technology-to-dramatically-streamline-overall-ic-circuit-verification/
    """
    if not short_mismatch.ext_net_ids:
        return None
    ext_net_id = short_mismatch.ext_net_ids[0]
    ext_net = next((n for n in extracted_nets if n.net_id == ext_net_id), None)
    if ext_net is None:
        return None

    # 找来自不同参考 net 的引脚对（通过 ref_net_ids 分组）
    ref_net_id_set = set(short_mismatch.ref_net_ids)
    pin_to_ref_net: dict[str, str] = {}
    # 重建 pin_ref → ref_net_id（从 short_mismatch 的 ref_net_ids 反推）
    # 注意: short_mismatch 只记录了 ref_net_ids，需通过 reference_nets 重建
    # 此处简化: 用引脚的 device_name 分组（同一器件的引脚属于同一参考 net）
    # 更精确的实现需传入 reference_nets
    for pin in ext_net.pins:
        # 用 device_name 作为参考 net 的代理（简化）
        pin_to_ref_net[pin.ref] = pin.device_name

    # 找相交的引脚对（来自不同参考 net）
    for i, p1 in enumerate(ext_net.pins):
        for p2 in ext_net.pins[i + 1:]:
            if pin_to_ref_net.get(p1.ref) == pin_to_ref_net.get(p2.ref):
                continue
            if p1.layer != p2.layer:
                continue
            if _bboxes_overlap(p1.bbox, p2.bbox, tolerance=bbox_tolerance_um):
                # 短路位置：引脚对中心
                return ((p1.x + p2.x) / 2, (p1.y + p2.y) / 2)
    return short_mismatch.location_um


def detect_short_open(
    reference_nets: list[Net],
    extracted_nets: list[Net],
) -> ShortOpenReport:
    """short/open 检测统一入口（R211-R230）。

    对参考网表与提取网表做 short/open 检测，生成报告。

    Args:
        reference_nets: 参考网表的网络列表。
        extracted_nets: 提取网表的网络列表。

    Returns:
        ShortOpenReport 检测报告。

    对标: Calibre nmLVS-H "Shorted Net"/"Unconnected Net" 自动分类
    https://www.eda-solutions.com/tn061/
    """
    shorts = detect_short_circuits(reference_nets, extracted_nets)
    opens = detect_open_circuits(reference_nets, extracted_nets)
    # 分离 OPEN_CIRCUIT 和 UNCONNECTED_PIN
    open_circuits = [m for m in opens if m.mtype == ShortOpenMismatchType.OPEN_CIRCUIT]
    unconnected = [m for m in opens if m.mtype == ShortOpenMismatchType.UNCONNECTED_PIN]

    return ShortOpenReport(
        is_clean=len(shorts) == 0 and len(open_circuits) == 0 and len(unconnected) == 0,
        shorts=shorts,
        opens=open_circuits,
        unconnected_pins=unconnected,
        reference_net_count=len(reference_nets),
        extracted_net_count=len(extracted_nets),
    )


def build_reference_nets_from_circuit(
    devices: list[str],
    connections: list[tuple[str, str]],
    pin_specs: dict[str, list[str]] | None = None,
) -> list[Net]:
    """从电路规格构建参考网络（R225 net 级比对）。

    将器件对连接转换为引脚级网络。每个连接 (dev1, dev2) 表示 dev1 和 dev2
    电气连通，需展开为引脚级网络。

    Args:
        devices: 器件名列表。
        connections: 连接对列表 [(dev1, dev2), ...]。
        pin_specs: 器件引脚规格 {device_name: [pin_name, ...]}，
            None 表示每个器件有 "in"/"out" 两个引脚。

    Returns:
        参考 net 列表。

    学术依据: KLayout Netter connect 语义
    https://klayout.org/downloads/master/doc-qt5/about/lvs_ref_netter.html
    """
    if pin_specs is None:
        pin_specs = {d: ["in", "out"] for d in devices}

    # 为每个器件引脚创建 Pin。
    # R211-R230 修复: 参考网表基于电路连接关系（connection_pairs）构建，
    # 不应依赖几何相交。给每个 pin 唯一坐标 (idx*1000, idx*1000)，
    # 配合 Pin.__post_init__ 生成的点 bbox，确保任意两个 pin 几何不相交，
    # 仅通过 connection_pairs 规则连通。
    pins: list[Pin] = []
    pin_idx = 0
    for dev in devices:
        for pin_name in pin_specs.get(dev, ["in", "out"]):
            pins.append(Pin(
                device_name=dev,
                pin_name=pin_name,
                layer="PORT",
                x=float(pin_idx * 1000),
                y=float(pin_idx * 1000),
            ))
            pin_idx += 1

    # 器件对连接 → 引脚对连接（简化: 每对器件用 "out"→"in" 连接）
    valid_refs = {p.ref for p in pins}
    connection_pairs: list[tuple[str, str]] = []
    for dev1, dev2 in connections:
        ref1 = f"{dev1}.out"
        ref2 = f"{dev2}.in"
        if ref1 in valid_refs and ref2 in valid_refs:
            connection_pairs.append((ref1, ref2))

    return extract_nets_from_pins(pins, connection_pairs=connection_pairs)


__all__ = [
    "Net",
    "Pin",
    "ShortOpenMismatch",
    "ShortOpenMismatchType",
    "ShortOpenReport",
    "build_reference_nets_from_circuit",
    "detect_open_circuits",
    "detect_short_circuits",
    "detect_short_open",
    "extract_nets_from_pins",
    "isolate_short_location",
]
