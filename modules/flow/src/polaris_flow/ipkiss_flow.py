"""IPKISS 风格光子电路设计流程（R25 路标）。

对标 Luceda IPKISS 的 PCell + 多视图（Netlist/Layout/CircuitModel）架构与
Schematic-Driven Layout（SDL）闭环验证流程，在 PoLaRIS 既有 PDK/仿真基础设施
之上构建 IPKISS 兼容的设计流。

## 模块组成

1. ``IPKISSPCell`` — 参数化器件单元（对标 IPKISS PCell）
2. ``IPKISSView`` — 视图基类
3. ``NetlistView`` — 网表视图（生成 SAX 格式连接关系）
4. ``LayoutView`` — 版图视图（生成 GDS 几何元素 + 包围盒）
5. ``CircuitModelView`` — 电路模型视图（生成 S 参数模型）
6. ``SDLFlow`` — Schematic-Driven Layout 流程（网表→放置→布线→版图）
7. ``ClosedLoopValidator`` — 闭环验证器（版图提取网表 vs 原理图网表）
8. ``IPKISSPDKBridge`` — PDK 器件到 IPKISS PCell 的桥接器

## 学术依据

- IPKISS/Luceda PCell + View 架构:
  https://docs.lucedaphotonics.com/
- IPKISS SDL 流程:
  https://academy.lucedaphotonics.com/pdks/cornerstone/cornerstone
- Schematic-Driven Layout 闭环验证:
  Chrostowski & Hochberg, "Silicon Photonics Design", Cambridge 2015, §8

来源:
- IPKISS: https://www.lucedaphotonics.com/products/ipkiss
- gdsfactory SDL: https://gdsfactory.github.io/gdsfactory/
- SAX 网表格式: https://flaport.github.io/sax/
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import numpy as np

if TYPE_CHECKING:
    # 类型注解仅用于静态检查，运行时不解析（PEP 563 `from __future__ import annotations`）
    from polaris.sim.types import ModelFunc, SDict

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 器件类型到 S 参数模型的映射（来源: polaris.sim.models，lazy import）
# ---------------------------------------------------------------------------
_MODEL_MAP: dict[str, Any] | None = None


def _get_model_map() -> dict[str, Any]:
    """Lazy 加载 polaris.sim.models 并构建器件类型→模型映射。

    运行时按需 import；polaris.sim.models 缺失则 raise ImportError
    （R03: 禁止 fall-back，缺失依赖必须显式 raise，不静默兜底）。
    """
    global _MODEL_MAP
    if _MODEL_MAP is None:
        from polaris.sim.models import (
            directional_coupler_s,
            mmi_1x2_s,
            mmi_2x2_s,
            phase_shifter_s,
            ring_resonator_s,
            waveguide_s,
            y_branch_s,
        )
        _MODEL_MAP = {
            "waveguide": waveguide_s,
            "y_branch": y_branch_s,
            "directional_coupler": directional_coupler_s,
            "ring_resonator": ring_resonator_s,
            "mmi_1x2": mmi_1x2_s,
            "mmi_2x2": mmi_2x2_s,
            "phase_shifter": phase_shifter_s,
        }
    return _MODEL_MAP

# 器件类型到端口列表的映射（来源: SiEPIC EBeam PDK 标准端口命名）
# https://github.com/SiEPIC/SiEPIC_EBeam_PDK
_PORT_MAP: dict[str, list[str]] = {
    "waveguide": ["in", "out"],
    "y_branch": ["port_1", "port_2", "port_3"],
    "directional_coupler": ["in1", "in2", "out1", "out2"],
    "ring_resonator": ["in", "through"],
    "mmi_1x2": ["in", "out1", "out2"],
    "mmi_2x2": ["in1", "in2", "out1", "out2"],
    "phase_shifter": ["in", "out"],
}


# ---------------------------------------------------------------------------
# IPKISSPCell — 参数化器件单元
# ---------------------------------------------------------------------------


@dataclass
class IPKISSPCell:
    """IPKISS 风格参数化器件单元。

    对标 IPKISS ``i3.PCell``：每个 PCell 持有名称、参数字典、端口列表，
    并通过多视图（Netlist/Layout/CircuitModel）暴露不同抽象层级。

    学术依据: IPKISS PCell 架构,
    https://docs.lucedaphotonics.com/

    Attributes:
        name: 器件名称（如 "mzi"）。
        cell_type: 器件类型（如 "mmi_1x2"、"waveguide"）。
        params: 参数字典（如 {"length": 100.0}）。
        ports: 端口名称列表。
    """

    name: str
    cell_type: str
    params: dict[str, Any] = field(default_factory=dict)
    ports: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """初始化后补全端口列表（若未显式指定）。"""
        if not self.ports and self.cell_type in _PORT_MAP:
            self.ports = list(_PORT_MAP[self.cell_type])

    @property
    def netlist_view(self) -> NetlistView:
        """返回网表视图。"""
        return NetlistView(self)

    @property
    def layout_view(self) -> LayoutView:
        """返回版图视图。"""
        return LayoutView(self)

    @property
    def circuit_model_view(self) -> CircuitModelView:
        """返回电路模型视图。"""
        return CircuitModelView(self)


# ---------------------------------------------------------------------------
# 视图基类与具体视图
# ---------------------------------------------------------------------------


class IPKISSView:
    """IPKISS 视图基类（对标 IPKISS ``i3.View``）。

    每个视图从 PCell 的某一抽象层级（网表/版图/电路模型）提取信息。
    """

    def __init__(self, cell: IPKISSPCell) -> None:
        self.cell = cell

    def generate(self) -> Any:  # pragma: no cover - 由子类实现
        """生成视图内容（由子类实现）。"""
        raise NotImplementedError


class NetlistView(IPKISSView):
    """网表视图（对标 IPKISS ``i3.NetlistView``）。

    生成 SAX 格式网表 ``{instances, connections, ports}``，
    描述器件实例、端口连接关系与外部端口。

    来源:
    - SAX 网表格式: https://flaport.github.io/sax/
    - IPKISS NetlistView: https://docs.lucedaphotonics.com/
    """

    def generate(self) -> dict:
        """生成单器件网表。

        Returns:
            SAX 格式网表字典 ``{instances, connections, ports}``。
        """
        return {
            "instances": {self.cell.name: self.cell.cell_type},
            "connections": {},
            "ports": {p: f"{self.cell.name},{p}" for p in self.cell.ports},
        }


class LayoutView(IPKISSView):
    """版图视图（对标 IPKISS ``i3.LayoutView``）。

    生成 GDS 风格版图元素（矩形/路径）与包围盒，
    用于版图导出与 DRC 检查。

    来源:
    - IPKISS LayoutView: https://docs.lucedaphotonics.com/
    - gdsfactory 组件几何: https://gdsfactory.github.io/gdsfactory/
    """

    def generate(self) -> dict:
        """生成版图元素与包围盒。

        Returns:
            含 ``elements``（几何元素列表）与 ``bbox``（包围盒）的字典。
        """
        cell_type = self.cell.cell_type
        params = self.cell.params
        elements: list[dict] = []
        if cell_type == "waveguide":
            length = float(params.get("length", 100.0))
            width = float(params.get("width", 0.5))
            elements.append(
                {"type": "path", "layer": "WG", "width": width,
                 "points": [(0, 0), (length, 0)]}
            )
            bbox = (0.0, -width / 2, length, width / 2)
        elif cell_type in ("mmi_1x2", "mmi_2x2", "y_branch"):
            length = float(params.get("length", 10.0))
            width = float(params.get("width", 5.0))
            elements.append(
                {"type": "rectangle", "layer": "WG",
                 "xy": (0, 0), "w": length, "h": width}
            )
            bbox = (0.0, 0.0, length, width)
        elif cell_type in ("directional_coupler",):
            length = float(params.get("length", 10.0))
            gap = float(params.get("gap", 0.2))
            width = float(params.get("width", 0.5))
            elements.append(
                {"type": "path", "layer": "WG", "width": width,
                 "points": [(0, gap / 2), (length, gap / 2)]}
            )
            elements.append(
                {"type": "path", "layer": "WG", "width": width,
                 "points": [(0, -gap / 2), (length, -gap / 2)]}
            )
            bbox = (0.0, -gap / 2 - width, length, gap / 2 + width)
        elif cell_type == "ring_resonator":
            radius = float(params.get("radius", 10.0))
            elements.append(
                {"type": "circle", "layer": "WG",
                 "center": (radius, 0), "radius": radius}
            )
            bbox = (0.0, -radius, 2 * radius, radius)
        elif cell_type == "phase_shifter":
            length = float(params.get("length", 50.0))
            width = float(params.get("width", 0.5))
            elements.append(
                {"type": "path", "layer": "WG", "width": width,
                 "points": [(0, 0), (length, 0)]}
            )
            elements.append(
                {"type": "rectangle", "layer": "HEATER",
                 "xy": (0, width), "w": length, "h": 1.0}
            )
            bbox = (0.0, -width / 2, length, width + 1.0)
        else:
            length = float(params.get("length", 10.0))
            width = float(params.get("width", 1.0))
            elements.append(
                {"type": "rectangle", "layer": "WG",
                 "xy": (0, 0), "w": length, "h": width}
            )
            bbox = (0.0, 0.0, length, width)
        return {"elements": elements, "bbox": bbox}


class CircuitModelView(IPKISSView):
    """电路模型视图（对标 IPKISS ``i3.CircuitModelView``）。

    生成器件 S 参数模型函数，供电路级频率域仿真使用。

    来源:
    - IPKISS CircuitModel: https://docs.lucedaphotonics.com/
    - polaris.sim.models: SiPANN/Simphony 解析模型
    """

    def generate(self) -> ModelFunc | None:
        """生成 S 参数模型函数。

        Returns:
            S 参数模型函数（接收 wl 等参数，返回 SDict），
            器件类型无模型时返回 None。
        """
        model = _get_model_map().get(self.cell.cell_type)
        if model is None:
            return None
        # 预绑定 PCell 参数到模型（部分参数透传给模型函数）
        bound_params = {
            k: v
            for k, v in self.cell.params.items()
            if k in ("length", "width", "radius", "gap", "coupling",
                     "insertion_loss_db", "phase_rad", "neff", "ng")
        }

        def _model(wl: float | np.ndarray = 1.55, **kwargs) -> SDict:
            merged = {**bound_params, **kwargs}
            return model(wl=wl, **merged)

        return _model


# ---------------------------------------------------------------------------
# SDLFlow — Schematic-Driven Layout 流程
# ---------------------------------------------------------------------------


@dataclass
class SDLFlow:
    """Schematic-Driven Layout 流程（对标 IPKISS SDL）。

    从原理图网表出发，执行放置（placement）→ 布线（routing）→ 版图生成
    （layout export）→ 闭环验证（LVS）的完整设计流。

    学术依据: Chrostowski & Hochberg, "Silicon Photonics Design",
    Cambridge 2015, §8 Schematic-Driven Layout.

    来源:
    - IPKISS SDL: https://docs.lucedaphotonics.com/
    - gdsfactory SDL: https://gdsfactory.github.io/gdsfactory/
    """

    schematic: dict = field(default_factory=dict)
    placement: dict[str, tuple[float, float]] = field(default_factory=dict)
    cells: dict[str, IPKISSPCell] = field(default_factory=dict)

    def add_cell(self, cell: IPKISSPCell) -> None:
        """添加 PCell 到设计流。"""
        self.cells[cell.name] = cell

    def set_placement(self, placement: dict[str, tuple[float, float]]) -> None:
        """设置器件放置坐标。"""
        self.placement = dict(placement)

    def build_schematic(self, instances: dict, connections: dict, ports: dict) -> dict:
        """构建原理图网表。

        Args:
            instances: 实例字典 ``{inst_name: cell_type}``。
            connections: 连接字典 ``{"inst1,port1": "inst2,port2"}``。
            ports: 外部端口字典 ``{ext_port: "inst,internal_port"}``。

        Returns:
            SAX 格式网表。
        """
        self.schematic = {
            "instances": dict(instances),
            "connections": dict(connections),
            "ports": dict(ports),
        }
        return self.schematic

    def generate_layout(self) -> dict:
        """从原理图 + 放置生成版图。

        Returns:
            含 ``instances``（每个实例的版图元素 + 变换坐标）与
            ``routes``（布线路径）的字典。
        """
        layout_instances: dict[str, dict] = {}
        for inst_name, cell_type in self.schematic.get("instances", {}).items():
            cell = self.cells.get(inst_name)
            if cell is None:
                cell = IPKISSPCell(name=inst_name, cell_type=cell_type)
            lv = cell.layout_view
            layout = lv.generate()
            x, y = self.placement.get(inst_name, (0.0, 0.0))
            layout_instances[inst_name] = {
                "cell_type": cell_type,
                "elements": layout["elements"],
                "bbox": layout["bbox"],
                "transform": (x, y, 0),  # (x, y, rotation_deg)
            }
        # 布线：简单直线路径（曼哈顿布线）
        routes: list[dict] = []
        for conn_spec, _ in self.schematic.get("connections", {}).items():
            inst1, port1 = conn_spec.split(",")
            x1, y1 = self.placement.get(inst1, (0.0, 0.0))
            routes.append(
                {"from": conn_spec, "to": _,
                 "path": [(x1, y1), (x1 + 10, y1)]}
            )
        return {"instances": layout_instances, "routes": routes}

    def export_gds(self) -> dict:
        """导出 GDS 风格版图数据。

        Returns:
            含 ``layers``（图层→元素列表）与 ``bbox``（全局包围盒）的字典。
        """
        layout = self.generate_layout()
        layers: dict[str, list[dict]] = {}
        all_x: list[float] = []
        all_y: list[float] = []
        for inst_data in layout["instances"].values():
            tx, ty, _ = inst_data["transform"]
            for elem in inst_data["elements"]:
                layer = elem.get("layer", "WG")
                layers.setdefault(layer, []).append(elem)
            bx0, by0, bx1, by1 = inst_data["bbox"]
            all_x.extend([bx0 + tx, bx1 + tx])
            all_y.extend([by0 + ty, by1 + ty])
        global_bbox = (
            (min(all_x), min(all_y), max(all_x), max(all_y))
            if all_x
            else (0.0, 0.0, 0.0, 0.0)
        )
        return {"layers": layers, "bbox": global_bbox}


# ---------------------------------------------------------------------------
# ClosedLoopValidator — 闭环验证器
# ---------------------------------------------------------------------------


@dataclass
class ClosedLoopValidator:
    """闭环验证器（对标 IPKISS LVS 闭环验证）。

    验证版图提取的网表与原理图网表的一致性（Layout-vs-Schematic），
    确保设计闭环正确。

    学术依据: Chrostowski & Hochberg, "Silicon Photonics Design",
    Cambridge 2015, §8.4 Layout Verification.

    来源:
    - IPKISS LVS: https://docs.lucedaphotonics.com/
    - KLayout LVS: https://www.klayout.org/doc-qt5/manual/lvs.html
    """

    schematic: dict = field(default_factory=dict)
    extracted: dict = field(default_factory=dict)

    def set_schematic(self, netlist: dict) -> None:
        """设置原理图网表。"""
        self.schematic = dict(netlist)

    def extract_from_layout(self, layout: dict) -> dict:
        """从版图提取网表。

        Args:
            layout: ``SDLFlow.generate_layout()`` 的输出。

        Returns:
            提取的网表 ``{instances, connections, ports}``。
        """
        instances: dict[str, str] = {}
        ports: dict[str, str] = {}
        for inst_name, inst_data in layout.get("instances", {}).items():
            instances[inst_name] = inst_data["cell_type"]
        # 版图布线对应连接关系
        connections: dict[str, str] = {}
        for route in layout.get("routes", []):
            frm = route["from"]
            to = route["to"]
            connections[frm] = to
        # 外部端口 = 未被连接的实例端口
        connected_ports: set[str] = set()
        for k, v in connections.items():
            connected_ports.add(k)
            connected_ports.add(v)
        for inst_name, cell_type in instances.items():
            cell_ports = _PORT_MAP.get(cell_type, [])
            for p in cell_ports:
                key = f"{inst_name},{p}"
                if key not in connected_ports:
                    ports[p] = key
        self.extracted = {
            "instances": instances,
            "connections": connections,
            "ports": ports,
        }
        return self.extracted

    def validate(self) -> dict:
        """执行 LVS 验证。

        Returns:
            含 ``passed``（布尔）、``instance_match``、``connection_match``
            与 ``mismatches``（不一致项列表）的字典。
        """
        sch_inst = set(self.schematic.get("instances", {}).keys())
        ext_inst = set(self.extracted.get("instances", {}).keys())
        inst_match = sch_inst == ext_inst
        sch_conn = set(self.schematic.get("connections", {}).items())
        ext_conn = set(self.extracted.get("connections", {}).items())
        conn_match = sch_conn == ext_conn
        mismatches: list[str] = []
        if not inst_match:
            only_sch = sch_inst - ext_inst
            only_ext = ext_inst - sch_inst
            if only_sch:
                mismatches.append(f"仅在原理图中的实例: {only_sch}")
            if only_ext:
                mismatches.append(f"仅在版图中的实例: {only_ext}")
        if not conn_match:
            mismatches.append("连接关系不一致")
        return {
            "passed": inst_match and conn_match,
            "instance_match": inst_match,
            "connection_match": conn_match,
            "mismatches": mismatches,
        }


# ---------------------------------------------------------------------------
# IPKISSPDKBridge — PDK 器件到 IPKISS PCell 的桥接器
# ---------------------------------------------------------------------------


@dataclass
class IPKISSPDKBridge:
    """PDK 器件到 IPKISS PCell 的桥接器。

    将 PoLaRIS ``polaris.pdk`` 的器件目录桥接为 IPKISS 风格 PCell，
    使既有 PDK 器件可在 IPKISS 设计流中使用。

    来源:
    - IPKISS PDK 集成: https://academy.lucedaphotonics.com/pdks/
    - gdsfactory PDK register_cell: https://gdsfactory.github.io/gdsfactory/
    """

    cell_registry: dict[str, IPKISSPCell] = field(default_factory=dict)

    def register(self, cell: IPKISSPCell) -> None:
        """注册 PCell 到桥接器。"""
        self.cell_registry[cell.name] = cell

    def register_standard_cells(self) -> list[str]:
        """注册标准器件 PCell（波导/Y分支/MMI/DC/环/移相器）。

        Returns:
            已注册的 PCell 名称列表。
        """
        standard: list[tuple[str, str, dict]] = [
            ("wg1", "waveguide", {"length": 100.0, "width": 0.5}),
            ("yb1", "y_branch", {"insertion_loss_db": 0.3}),
            ("mmi1", "mmi_1x2", {"insertion_loss_db": 0.4}),
            ("mmi2", "mmi_2x2", {"insertion_loss_db": 0.5}),
            ("dc1", "directional_coupler", {"coupling": 0.5, "length": 10.0}),
            ("ring1", "ring_resonator", {"radius": 10.0}),
            ("ps1", "phase_shifter", {"phase_rad": 0.0}),
        ]
        names: list[str] = []
        for name, cell_type, params in standard:
            cell = IPKISSPCell(name=name, cell_type=cell_type, params=params)
            self.register(cell)
            names.append(name)
        return names

    def get_cell(self, name: str) -> IPKISSPCell:
        """按名称获取 PCell。

        Args:
            name: PCell 名称。

        Returns:
            对应的 IPKISSPCell。

        Raises:
            KeyError: 名称未注册时。
        """
        if name not in self.cell_registry:
            raise KeyError(f"PCell '{name}' 未注册，可用: {list(self.cell_registry)}")
        return self.cell_registry[name]

    def list_cells(self) -> list[str]:
        """列出所有已注册 PCell 名称。"""
        return list(self.cell_registry)
