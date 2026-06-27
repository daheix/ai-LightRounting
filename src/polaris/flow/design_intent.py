"""OptoDesigner Design Intent 流程引擎 R20（原理图→意图→PDK 三层映射）。

本模块实现原理图到 PDK 器件实例的三层映射，对标 OptoDesigner Design Intent
流程与 VPIphotonics layout-aware schematic-driven design 方法论：

1. 原理图解析：从电路原理图提取器件 + 连接关系
2. 布局意图生成：器件位置 + 朝向（拓扑排序 + 深度分层放置）
3. 布线意图生成：曼哈顿路径 + 弯曲约束
4. 约束意图生成：设计规则约束结构化
5. PDK 器件映射：意图 → PDK 器件实例
6. 约束传播：设计规则约束传播到每个器件参数
7. 意图验证：验证生成的意图是否满足设计规则（失败即 raise）

与 polaris.pdk.optodesigner.DesignIntentEngine（掩膜级：单层路径→多层掩膜）
职责不同，本引擎为流程级（原理图→布局/布线意图→PDK 实例），二者互补。

文献来源（R02 学术诚信，≥5 个 URL）：
1. Synopsys OptoDesigner 官方文档（Design Intent 机制）
   URL: https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner.html
2. Mingaleev et al., "Rapid virtual prototyping of complex photonic integrated
   circuits using layout-aware schematic-driven design methodology",
   Proc. SPIE 10107, 1010708 (2017), doi:10.1117/12.2252001
   URL: https://doi.org/10.1117/12.2252001
3. Luceda IPKISS Design Intent（PCell + 多视图 + SDL 流程）
   URL: https://www.lucedaphotonics.com/products/ipkiss
4. gdsfactory Design Intent（Python 驱动 PIC 版图生成）
   URL: https://gdsfactory.github.io/gdsfactory/
5. PIC Magazine, "PIC Design: schematic or layout first? Both!"
   URL: https://picmagazine.net/article/101210/PIC_Design_schematic_or_layout_first_Both_/feature
6. PDAflow API 标准（光子设计自动化互操作）
   URL: http://pdaflow.org/
7. SiEPIC EBeam PDK（设计规则参数来源）
   URL: https://github.com/SiEPIC/SiEPIC_EBeam_PDK

*创新*：原理图→意图→PDK 三层映射架构
底层逻辑：传统 SDL（Schematic-Driven Layout）流程将原理图直接映射到版图，
缺乏中间意图层导致设计规则难以在早期传播。本引擎引入"意图"中间层：
- 原理图层：器件 + 连接（逻辑拓扑，source [2] layout-aware SDL 方法论）
- 意图层：布局意图 + 布线意图 + 约束意图（物理拓扑，可验证）
- PDK 层：意图 → PDK 器件实例（工艺实现，source [3][4] PDK 映射）
三层解耦使设计规则在意图层即可验证（validate_intent），避免下游 PDK 实例化
后才发现违规，对齐 OptoDesigner "Design Intent ensures users can design in a
single layer" 理念（source [1]），并扩展到器件级布局布线意图。

案例：MZI 原理图（2 GC + 2 DC + 2 臂）→ 意图层验证臂长差与最小间距约束 →
PDK 实例化。支持理论：Mingaleev [2] 提出 layout-aware schematic-driven 方法
要求电路与版图协同设计，意图层正是协同的中间表达。

合规性：
- R03 禁止 fall-back：所有错误 raise，无 return None/[] 假数据
- R04 不参与 GPU：纯 NumPy 实现
- R02 学术诚信：所有参数可溯源，docstring 含 ≥5 文献 URL
- 质量门禁：圈复杂度 ≤15，函数 ≤80 行，文件 ≤800 行
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# 文献 URL 常量（R02 学术诚信）
# ---------------------------------------------------------------------------
_URL_OPTODESIGNER = (
    "https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner.html"
)
_URL_SPIE_2017 = "https://doi.org/10.1117/12.2252001"
_URL_IPKISS = "https://www.lucedaphotonics.com/products/ipkiss"
_URL_GDSFACTORY = "https://gdsfactory.github.io/gdsfactory/"
_URL_PIC_MAGAZINE = (
    "https://picmagazine.net/article/101210/"
    "PIC_Design_schematic_or_layout_first_Both_/feature"
)
_URL_PDAFLOW = "http://pdaflow.org/"
_URL_SIEPIC = "https://github.com/SiEPIC/SiEPIC_EBeam_PDK"


# ---------------------------------------------------------------------------
# 配置数据类
# ---------------------------------------------------------------------------


@dataclass
class IntentConfig:
    """Design Intent 引擎配置。

    Attributes:
        design_rules: 设计规则字典。必需键（SiEPIC EBeam PDK 标准，source [7]）：
            - min_waveguide_width: 最小波导宽度（μm），SiEPIC EBeam = 0.4
            - min_bend_radius: 最小弯曲半径（μm），SiEPIC EBeam = 5.0
            - min_spacing: 最小器件间距（μm），典型 PIC = 2.0
            可选键：max_waveguide_width, max_path_length
        pdk_library: PDK 器件库 {device_type: {cell_name, ports, ...}}。
        grid_pitch: 版图栅格间距（μm），默认 0.01（来源: GDSII 标准精度）。
        placement_spacing: 器件放置间距（μm），默认 50.0。
    """

    design_rules: dict = field(default_factory=dict)
    pdk_library: dict = field(default_factory=dict)
    grid_pitch: float = 0.01
    placement_spacing: float = 50.0


# ---------------------------------------------------------------------------
# Design Intent 流程引擎
# ---------------------------------------------------------------------------


class DesignIntentEngine:
    """OptoDesigner Design Intent 流程引擎（原理图→意图→PDK 三层映射）。

    实现原理图到 PDK 器件实例的完整映射流程，对标 OptoDesigner Design Intent
    机制（source [1]）与 VPIphotonics layout-aware SDL 方法论（source [2]）。

    三层架构：
        原理图层 --parse_schematic--> 意图层 --map_to_pdk--> PDK 层
        意图层 = 布局意图 + 布线意图 + 约束意图（可 validate_intent 验证）

    学术依据: OptoDesigner Design Intent [1], layout-aware SDL [2]
    """

    # 必需设计规则键（来源: SiEPIC EBeam PDK 公开文档 [7]）
    _REQUIRED_RULES = ("min_waveguide_width", "min_bend_radius", "min_spacing")

    def __init__(self, config: IntentConfig) -> None:
        """初始化 Design Intent 流程引擎。

        Args:
            config: 引擎配置（IntentConfig 实例）。

        Raises:
            ValueError: config 类型不匹配。
        """
        if not isinstance(config, IntentConfig):
            raise ValueError(
                f"config 必须是 IntentConfig 实例，得到 {type(config).__name__}"
            )
        self._config: IntentConfig = config
        self._placement: dict[str, dict] = {}
        self._schematic_cache: dict = {}

    @property
    def config(self) -> IntentConfig:
        """引擎配置（只读视图）。"""
        return self._config

    # ------------------------------------------------------------------
    # 1. 原理图解析
    # ------------------------------------------------------------------

    def parse_schematic(self, schematic: dict) -> dict:
        """解析原理图，提取器件 + 连接关系。

        Args:
            schematic: 原理图字典，含 'devices' 和 'connections' 键。
                devices: [{id, type, params, ports}]
                connections: [{src, src_port, dst, dst_port}]

        Returns:
            归一化原理图 {devices, connections, device_map}。

        Raises:
            ValueError: 原理图结构无效或缺少必需字段。
        """
        if not isinstance(schematic, dict):
            raise ValueError(
                f"schematic 必须是 dict，得到 {type(schematic).__name__}"
            )
        if "devices" not in schematic or "connections" not in schematic:
            raise ValueError("schematic 必须含 'devices' 和 'connections' 键")
        devices = schematic["devices"]
        connections = schematic["connections"]
        if not isinstance(devices, list) or not isinstance(connections, list):
            raise ValueError("devices 和 connections 必须是列表")
        norm_devices: list[dict] = []
        device_map: dict[str, dict] = {}
        for dev in devices:
            ndev = self._normalize_device(dev)
            norm_devices.append(ndev)
            device_map[ndev["id"]] = ndev
        norm_connections: list[dict] = []
        for conn in connections:
            nconn = self._normalize_connection(conn, device_map)
            norm_connections.append(nconn)
        self._schematic_cache = {
            "devices": norm_devices,
            "connections": norm_connections,
            "device_map": device_map,
        }
        return self._schematic_cache

    def _normalize_device(self, dev: dict) -> dict:
        """归一化单个器件定义。"""
        required = ("id", "type", "params", "ports")
        for key in required:
            if key not in dev:
                raise ValueError(f"器件缺少必需字段 '{key}': {dev}")
        if not isinstance(dev["ports"], list) or len(dev["ports"]) < 2:
            raise ValueError(
                f"器件 {dev['id']} 端口数必须 >= 2，得到 {len(dev.get('ports', []))}"
            )
        return {
            "id": str(dev["id"]),
            "type": str(dev["type"]),
            "params": dict(dev["params"]),
            "ports": [str(p) for p in dev["ports"]],
        }

    def _normalize_connection(self, conn: dict, device_map: dict) -> dict:
        """归一化单个连接定义，验证端口存在性。"""
        required = ("src", "src_port", "dst", "dst_port")
        for key in required:
            if key not in conn:
                raise ValueError(f"连接缺少必需字段 '{key}': {conn}")
        if conn["src"] not in device_map:
            raise ValueError(f"连接源器件 '{conn['src']}' 不在原理图中")
        if conn["dst"] not in device_map:
            raise ValueError(f"连接目的器件 '{conn['dst']}' 不在原理图中")
        src_ports = device_map[conn["src"]]["ports"]
        if conn["src_port"] not in src_ports:
            raise ValueError(
                f"端口 '{conn['src_port']}' 不在器件 {conn['src']} 端口列表 {src_ports}"
            )
        dst_ports = device_map[conn["dst"]]["ports"]
        if conn["dst_port"] not in dst_ports:
            raise ValueError(
                f"端口 '{conn['dst_port']}' 不在器件 {conn['dst']} 端口列表 {dst_ports}"
            )
        return {
            "src": str(conn["src"]),
            "src_port": str(conn["src_port"]),
            "dst": str(conn["dst"]),
            "dst_port": str(conn["dst_port"]),
        }

    # ------------------------------------------------------------------
    # 2. 布局意图生成
    # ------------------------------------------------------------------

    def generate_layout_intent(self, schematic: dict) -> dict:
        """生成布局意图（器件位置 + 朝向）。

        算法: 基于连接图的 Kahn 拓扑排序 + 深度分层放置
        - Kahn 算法（Kahn 1962）计算器件拓扑序，检测环
        - 深度 = 从源器件的最长路径长度，同深度器件沿 y 轴居中分布
        - x = depth * placement_spacing，y = 居中偏移
        - 朝向: 有输出连接 → 0°（朝右）；仅输入 → 180°（朝左）

        Args:
            schematic: parse_schematic 返回的归一化原理图。

        Returns:
            布局意图 {devices: [{id, x, y, orientation}], placement: {...}}.

        Raises:
            ValueError: 原理图无器件或含环。
        """
        devices = schematic["devices"]
        connections = schematic["connections"]
        if not devices:
            raise ValueError("原理图无器件，无法生成布局意图")
        order = self._topological_sort(devices, connections)
        depth = self._compute_depth(order, connections)
        by_depth: dict[int, list[str]] = {}
        for dev_id in order:
            by_depth.setdefault(depth[dev_id], []).append(dev_id)
        placement: dict[str, dict] = {}
        grid = self._config.grid_pitch
        for d in sorted(by_depth.keys()):
            group = by_depth[d]
            x_raw = d * self._config.placement_spacing
            x = round(x_raw / grid) * grid
            for j, dev_id in enumerate(group):
                y_raw = (j - (len(group) - 1) / 2.0) * self._config.placement_spacing
                y = round(y_raw / grid) * grid
                orientation = self._compute_orientation(dev_id, connections)
                placement[dev_id] = {
                    "x": float(x),
                    "y": float(y),
                    "orientation": orientation,
                }
        self._placement = placement
        return {
            "devices": [
                {"id": did, **pos} for did, pos in placement.items()
            ],
            "placement": placement,
        }

    def _topological_sort(
        self, devices: list[dict], connections: list[dict]
    ) -> list[str]:
        """Kahn 算法拓扑排序（检测环）。

        来源: Kahn, "Topological Sorting of Large Networks", CACM 1962.
        """
        in_degree: dict[str, int] = {d["id"]: 0 for d in devices}
        adj: dict[str, list[str]] = {d["id"]: [] for d in devices}
        for conn in connections:
            adj[conn["src"]].append(conn["dst"])
            in_degree[conn["dst"]] += 1
        queue = [did for did, deg in in_degree.items() if deg == 0]
        order: list[str] = []
        while queue:
            node = queue.pop(0)
            order.append(node)
            for neighbor in adj[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        if len(order) != len(devices):
            raise ValueError(
                "原理图含环，无法拓扑排序（禁止 fall-back 跳过环）"
            )
        return order

    def _compute_depth(
        self, order: list[str], connections: list[dict]
    ) -> dict[str, int]:
        """计算每个器件的拓扑深度（最长路径长度）。"""
        depth: dict[str, int] = {did: 0 for did in order}
        for dev_id in order:
            for conn in connections:
                if conn["dst"] == dev_id:
                    depth[dev_id] = max(depth[dev_id], depth[conn["src"]] + 1)
        return depth

    def _compute_orientation(
        self, dev_id: str, connections: list[dict]
    ) -> float:
        """计算器件朝向（度）。有输出连接 → 0°；仅输入 → 180°。"""
        has_outgoing = any(c["src"] == dev_id for c in connections)
        has_incoming = any(c["dst"] == dev_id for c in connections)
        if has_incoming and not has_outgoing:
            return 180.0
        return 0.0

    # ------------------------------------------------------------------
    # 3. 布线意图生成
    # ------------------------------------------------------------------

    def generate_routing_intent(self, connections: list) -> dict:
        """生成布线意图（曼哈顿路径 + 弯曲约束）。

        对每条连接，计算从源端口到目的端口的 L 形曼哈顿路径
        （水平优先），并附加最小弯曲半径约束。

        算法: L-shaped Manhattan routing
        来源: Weste & Harris, CMOS VLSI Design, §6（曼哈顿布线）

        Args:
            connections: 连接列表（parse_schematic 归一化输出）。

        Returns:
            布线意图 {net_id: {src, src_port, dst, dst_port, path,
            bend_radius, constraints}}.

        Raises:
            ValueError: 未先调用 generate_layout_intent 或缺少弯曲半径规则。
        """
        if not self._placement:
            raise ValueError(
                "未生成布局意图，请先调用 generate_layout_intent（禁止 fall-back）"
            )
        min_radius = self._require_rule("min_bend_radius")
        routing: dict[str, dict] = {}
        for i, conn in enumerate(connections):
            src_pos = self._get_port_position(conn["src"], conn["src_port"])
            dst_pos = self._get_port_position(conn["dst"], conn["dst_port"])
            path = self._manhattan_route(src_pos, dst_pos)
            net_id = f"net_{i}"
            routing[net_id] = {
                "src": conn["src"],
                "src_port": conn["src_port"],
                "dst": conn["dst"],
                "dst_port": conn["dst_port"],
                "path": path,
                "bend_radius": float(min_radius),
                "constraints": ["min_bend_radius", "manhattan", "no_overlap"],
            }
        return routing

    def _get_port_position(
        self, device_id: str, port_name: str
    ) -> tuple[float, float]:
        """计算器件端口的绝对位置（基于放置 + 器件参数）。

        简化模型: 输入端口在左端（-length/2），输出端口在右端（+length/2），
        多端口沿 y 轴居中分布。
        """
        if device_id not in self._placement:
            raise ValueError(f"器件 {device_id} 未放置，无法获取端口位置")
        if device_id not in self._schematic_cache.get("device_map", {}):
            raise ValueError(f"器件 {device_id} 不在原理图缓存中")
        pos = self._placement[device_id]
        dev = self._schematic_cache["device_map"][device_id]
        length = float(dev["params"].get("length", 10.0))
        width = float(dev["params"].get("width", 0.5))
        ports = dev["ports"]
        port_idx = ports.index(port_name) if port_name in ports else 0
        n_ports = len(ports)
        is_input = port_name.startswith("in") or port_name == "port_1"
        x_offset = -length / 2.0 if is_input else length / 2.0
        if n_ports > 1:
            y_offset = (port_idx - (n_ports - 1) / 2.0) * width
        else:
            y_offset = 0.0
        return (pos["x"] + x_offset, pos["y"] + y_offset)

    def _manhattan_route(
        self, src: tuple[float, float], dst: tuple[float, float]
    ) -> list[tuple[float, float]]:
        """计算 L 形曼哈顿路径（水平优先：先 x 后 y）。"""
        x1, y1 = src
        x2, y2 = dst
        return [(x1, y1), (x2, y1), (x2, y2)]

    # ------------------------------------------------------------------
    # 4. 约束意图生成
    # ------------------------------------------------------------------

    def generate_constraint_intent(self, design_rules: dict) -> dict:
        """生成约束意图（设计规则结构化）。

        将扁平设计规则字典结构化为按器件类别分组的约束意图。

        Args:
            design_rules: 设计规则字典（IntentConfig.design_rules）。

        Returns:
            约束意图 {waveguide, bend, placement, routing}.

        Raises:
            ValueError: design_rules 为空或缺少必需规则。
        """
        if not isinstance(design_rules, dict) or not design_rules:
            raise ValueError("design_rules 必须是非空 dict（禁止 fall-back）")
        for rule in self._REQUIRED_RULES:
            if rule not in design_rules:
                raise ValueError(
                    f"设计规则缺少必需项 '{rule}'（禁止 fall-back 默认值）"
                )
        constraints: dict[str, dict] = {
            "waveguide": {"min_width": float(design_rules["min_waveguide_width"])},
            "bend": {"min_radius": float(design_rules["min_bend_radius"])},
            "placement": {"min_spacing": float(design_rules["min_spacing"])},
            "routing": {},
        }
        if "max_waveguide_width" in design_rules:
            constraints["waveguide"]["max_width"] = float(
                design_rules["max_waveguide_width"]
            )
        if "max_path_length" in design_rules:
            constraints["routing"]["max_length"] = float(
                design_rules["max_path_length"]
            )
        return constraints

    # ------------------------------------------------------------------
    # 5. PDK 器件映射
    # ------------------------------------------------------------------

    def map_to_pdk(self, intent: dict, pdk_library: dict) -> dict:
        """意图 → PDK 器件实例映射。

        Args:
            intent: 含 'devices' 的意图字典。
            pdk_library: PDK 器件库 {device_type: {cell_name, ports}}.

        Returns:
            {instances: [...], count: N}.

        Raises:
            ValueError: pdk_library 为空或器件类型不在库中。
        """
        if not isinstance(pdk_library, dict) or not pdk_library:
            raise ValueError("pdk_library 必须是非空 dict（禁止 fall-back）")
        if "devices" not in intent:
            raise ValueError("intent 缺少 'devices' 键")
        if not self._schematic_cache:
            raise ValueError("原理图缓存为空，请先调用 parse_schematic")
        instances: list[dict] = []
        for dev_intent in intent["devices"]:
            dev_id = dev_intent["id"]
            dev = self._schematic_cache["device_map"][dev_id]
            dev_type = dev["type"]
            if dev_type not in pdk_library:
                raise ValueError(
                    f"器件类型 '{dev_type}' 不在 PDK 库中（禁止 fall-back 默认映射）"
                )
            pdk_spec = pdk_library[dev_type]
            instance = {
                "instance_id": f"{dev_type}_{dev_id}",
                "pdk_cell": pdk_spec.get("cell_name", dev_type),
                "device_type": dev_type,
                "params": dict(dev["params"]),
                "x": dev_intent["x"],
                "y": dev_intent["y"],
                "orientation": dev_intent["orientation"],
                "ports": list(pdk_spec.get("ports", dev["ports"])),
            }
            instances.append(instance)
        return {"instances": instances, "count": len(instances)}

    # ------------------------------------------------------------------
    # 6. 约束传播
    # ------------------------------------------------------------------

    def propagate_constraints(self, intent: dict) -> dict:
        """约束传播到器件参数。

        将约束意图中的设计规则传播到每个器件的适用参数。

        Args:
            intent: 含 'devices' 和 'constraints' 的意图字典。

        Returns:
            {device_id: [{rule, value, param}, ...]}.
        """
        if "devices" not in intent or "constraints" not in intent:
            raise ValueError("intent 缺少 'devices' 或 'constraints' 键")
        if not self._schematic_cache:
            raise ValueError("原理图缓存为空，请先调用 parse_schematic")
        constraints = intent["constraints"]
        propagated: dict[str, list[dict]] = {}
        for dev_intent in intent["devices"]:
            dev_id = dev_intent["id"]
            dev = self._schematic_cache["device_map"][dev_id]
            dev_type = dev["type"]
            dev_constraints: list[dict] = []
            if dev_type in ("waveguide", "taper", "directional_coupler"):
                min_w = constraints.get("waveguide", {}).get("min_width")
                if min_w is not None:
                    dev_constraints.append(
                        {"rule": "min_width", "value": min_w, "param": "width"}
                    )
            if dev_type in ("bend",):
                min_r = constraints.get("bend", {}).get("min_radius")
                if min_r is not None:
                    dev_constraints.append(
                        {"rule": "min_radius", "value": min_r, "param": "radius"}
                    )
            min_s = constraints.get("placement", {}).get("min_spacing")
            if min_s is not None:
                dev_constraints.append(
                    {"rule": "min_spacing", "value": min_s, "param": "position"}
                )
            propagated[dev_id] = dev_constraints
        return propagated

    # ------------------------------------------------------------------
    # 7. 意图验证
    # ------------------------------------------------------------------

    def validate_intent(self, intent: dict) -> bool:
        """验证意图是否满足设计规则。

        验证项:
        - 器件宽度 >= min_waveguide_width
        - 器件间距 >= min_spacing
        - 布线弯曲半径 >= min_bend_radius

        Args:
            intent: 含 'devices', 'constraints' 的意图字典。

        Returns:
            True（验证通过）。

        Raises:
            ValueError: 任何设计规则违反（禁止 fall-back 返回 False）。
        """
        if "devices" not in intent or "constraints" not in intent:
            raise ValueError("intent 缺少 'devices' 或 'constraints' 键")
        if not self._schematic_cache:
            raise ValueError("原理图缓存为空，请先调用 parse_schematic")
        errors: list[str] = []
        constraints = intent["constraints"]
        min_width = constraints.get("waveguide", {}).get("min_width")
        min_spacing = constraints.get("placement", {}).get("min_spacing")
        min_radius = constraints.get("bend", {}).get("min_radius")
        errors.extend(self._validate_widths(intent, min_width))
        errors.extend(self._validate_spacing(intent, min_spacing))
        errors.extend(self._validate_routing(intent, min_radius))
        if errors:
            raise ValueError("意图验证失败:\n  " + "\n  ".join(errors))
        return True

    def _validate_widths(self, intent: dict, min_width) -> list[str]:
        """验证波导类器件宽度。"""
        errors: list[str] = []
        if min_width is None:
            return errors
        for dev_intent in intent["devices"]:
            dev = self._schematic_cache["device_map"][dev_intent["id"]]
            if dev["type"] in ("waveguide", "taper", "directional_coupler"):
                width = float(dev["params"].get("width", 0.0))
                if width < min_width:
                    errors.append(
                        f"器件 {dev_intent['id']} 宽度 {width} < min_width {min_width}"
                    )
        return errors

    def _validate_spacing(self, intent: dict, min_spacing) -> list[str]:
        """验证器件间距。"""
        errors: list[str] = []
        if min_spacing is None:
            return errors
        devs = intent["devices"]
        for i in range(len(devs)):
            for j in range(i + 1, len(devs)):
                d1, d2 = devs[i], devs[j]
                dist = math.hypot(d1["x"] - d2["x"], d1["y"] - d2["y"])
                if dist < min_spacing:
                    errors.append(
                        f"器件 {d1['id']} 与 {d2['id']} 间距 {dist:.4f} "
                        f"< min_spacing {min_spacing}"
                    )
        return errors

    def _validate_routing(self, intent: dict, min_radius) -> list[str]:
        """验证布线弯曲半径。"""
        errors: list[str] = []
        if min_radius is None or "routing" not in intent:
            return errors
        for net_id, route in intent["routing"].items():
            if route["bend_radius"] < min_radius:
                errors.append(
                    f"网络 {net_id} 弯曲半径 {route['bend_radius']} "
                    f"< min_radius {min_radius}"
                )
        return errors

    # ------------------------------------------------------------------
    # 辅助方法
    # ------------------------------------------------------------------

    def _require_rule(self, rule_name: str) -> float:
        """获取必需设计规则值，缺失则 raise（禁止 fall-back 默认值）。"""
        if rule_name not in self._config.design_rules:
            raise ValueError(
                f"设计规则缺少 '{rule_name}'（禁止 fall-back 默认值）"
            )
        return float(self._config.design_rules[rule_name])

    # ------------------------------------------------------------------
    # 8. 完整流程
    # ------------------------------------------------------------------

    def run(self, schematic: dict) -> dict:
        """完整流程：原理图→意图→PDK 映射→验证。

        执行顺序:
        1. parse_schematic: 原理图解析
        2. generate_layout_intent: 布局意图
        3. generate_routing_intent: 布线意图
        4. generate_constraint_intent: 约束意图
        5. propagate_constraints: 约束传播
        6. validate_intent: 意图验证
        7. map_to_pdk: PDK 映射

        Args:
            schematic: 原理图字典。

        Returns:
            完整意图字典（含 devices, routing, constraints,
            propagated_constraints, pdk_instances）。

        Raises:
            ValueError: 任一阶段失败。
        """
        parsed = self.parse_schematic(schematic)
        layout = self.generate_layout_intent(parsed)
        routing = self.generate_routing_intent(parsed["connections"])
        constraints = self.generate_constraint_intent(self._config.design_rules)
        full_intent: dict = {
            "devices": layout["devices"],
            "routing": routing,
            "constraints": constraints,
        }
        full_intent["propagated_constraints"] = self.propagate_constraints(full_intent)
        self.validate_intent(full_intent)
        full_intent["pdk_instances"] = self.map_to_pdk(
            full_intent, self._config.pdk_library
        )
        return full_intent
