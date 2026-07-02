"""SiEPIC GDS 电路解析器 — 从真实 GDS 文件提取网表。

读取 SiEPIC EBeam PDK 格式的 GDS 文件，提取器件与连接信息，
转换为 PoLaRIS CircuitSpec。

专家布局/布线提取（用于模仿学习）见 :mod:`polaris_nn.data.expert_layout`。

SiEPIC GDS 格式（来源: SiEPIC_EBeam_PDK, MIT, UBC）:
- DEVREC layer (68,0): 器件识别层
  - Polygon: 器件边界框
  - Text: ``Lumerical_INTERCONNECT_component=<name>`` + ``Spice_param:<params>``
- PIN layer (69,0): 端口标记层
  - Path: 2 点路径标记端口位置与方向
  - Text: 端口名（如 ``pin1``/``pin2``/``opt_input``/``opt_output``）

来源:
- SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK (MIT, UBC, Lukas Chrostowski)
- SiEPIC netlist extraction: https://github.com/SiEPIC/SiEPIC-Tools
- klayout.db API: https://www.klayout.de/doc-qt5/code/class_LayerInfo.html
- klayout Instance class: https://www.klayout.org/klayout-pypi/overview/instances/

R03 异常处理设计: PIN text 无匹配 path 或端口未匹配到器件时 raise ValueError，
禁止静默跳过（GDS 数据不完整时必须告警）。

异常处理文献:
- Python 异常处理: https://docs.python.org/3/tutorial/errors.html
- PEP 8 异常设计: https://peps.python.org/pep-0008/#exception-handling
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from polaris_nn.data.specs import CircuitSpec, DeviceSpec

logger = logging.getLogger(__name__)

# ─── SiEPIC 真实器件名 → PoLaRIS 器件名映射（内联，避免依赖完整 polaris 包） ───
# 来源: SiEPIC EBeam PDK (MIT, UBC) https://github.com/SiEPIC/SiEPIC_EBeam_PDK
#       ubcpdk https://github.com/gdsfactory/ubc
# polaris-nn 子模块自包含，不再 import polaris.pdk.siepic_mapping。
_SIEPIC_TO_POLARIS: dict[str, str] = {
    "ebeam_y_1550": "y_branch",
    "ebeam_y_te1550": "y_branch",
    "ebeam_gc_te1550": "grating_coupler_1d",
    "gc_te1550": "grating_coupler_1d",
    "ebeam_gc_tm1550": "grating_coupler_2d",
    "gc_tm1550": "grating_coupler_2d",
    "ebeam_dc_te1550": "directional_coupler",
    "ebeam_bdc_te1550": "directional_coupler",
    "ebeam_dc_halfring_te1550": "ring_resonator",
    "ebeam_dc_halfring_straight": "ring_resonator",
    "ebeam_mmi_1x2_te_1550": "mmi_1x2",
    "ebeam_mmi_2x2_te_1550": "mmi_2x2",
    "ebeam_terminator_te1550": "terminator",
    "ebeam_crossing_te1550": "crossing",
    "ebeam_taper_te1550": "linear_taper",
    "ebeam_taper_475_500_te1550": "linear_taper",
    "ebeam_wg_strip_1550": "strip_waveguide",
    "ebeam_bend_te1550": "bend",
}


def siepic_to_polaris(siepic_name: str) -> str | None:
    """将 SiEPIC 真实器件名转换为 PoLaRIS 器件名（内联版）。

    Args:
        siepic_name: SiEPIC 器件名（如 ``ebeam_y_1550``）。

    Returns:
        PoLaRIS 器件名（如 ``y_branch``），未找到返回 None。

    来源: SiEPIC EBeam PDK https://github.com/SiEPIC/SiEPIC_EBeam_PDK
    """
    return _SIEPIC_TO_POLARIS.get(siepic_name)

# SiEPIC 标准 layer 编号
_DEVREC_LAYER = (68, 0)
_PIN_LAYER = (69, 0)

# 端口位置匹配容差（μm）
# SiEPIC EBeam PDK 中相邻器件端口间距典型值 5.5μm（如 y_branch 的 pin2/pin3），
# 但跨器件直接对齐的端口间距可达 10-15μm（如 DC 与波导的连接）。
# 容差 15.0μm 可匹配大多数直接对齐连接，同时通过 device_name 检查排除同器件端口。
# 来源: SiEPIC EBeam PDK 器件尺寸 https://github.com/SiEPIC/SiEPIC_EBeam_PDK
_PORT_MATCH_TOL = 15.0

# 忽略的非器件实例名前缀
_IGNORE_PREFIXES = (
    "ROUND_PATH",
    "LumericalINTERCONNECT_Laser",
    "LumericalINTERCONNECT_Detector",
    "OpticalFibre",
    "TE1550_SubGC",
    "Waveguide_Route",
)


def _parse_spice_param(text: str) -> dict:
    """解析 ``Spice_param:wg_width=0.500u gap=0.100u`` 格式的参数字符串。

    Args:
        text: Spice_param 文本（含或不含 ``Spice_param:`` 前缀）。

    Returns:
        参数字典，值已去除 ``u`` 后缀并转为 float。
    """
    if "Spice_param:" in text:
        text = text.split("Spice_param:", 1)[1]
    elif "Spice_param=" in text:
        text = text.split("Spice_param=", 1)[1]
    params: dict[str, float | str] = {}
    for token in text.strip().split():
        if "=" in token:
            k, v = token.split("=", 1)
            v_clean = v.rstrip("u")
            try:
                params[k] = float(v_clean)
            except ValueError:
                params[k] = v_clean
    return params


def _extract_component_name(text: str) -> str | None:
    """从 DEVREC 文本中提取 ``Lumerical_INTERCONNECT_component=<name>`` 的器件名。

    Args:
        text: DEVREC 文本标签内容。

    Returns:
        器件名（如 ``ebeam_y_1550``），未找到返回 None。
    """
    match = re.search(r"Lumerical_INTERCONNECT_component=(\S+)", text)
    return match.group(1) if match else None


def _port_direction_from_path(pts: list[tuple[float, float]]) -> str:
    """根据 PIN Path 的两点方向推断端口朝向。

    Args:
        pts: Path 的两个端点 [(x1,y1), (x2,y2)]。

    Returns:
        方向字母: ``"N"``/``"S"``/``"E"``/``"W"``。
    """
    if len(pts) < 2:
        return "E"
    dx = pts[1][0] - pts[0][0]
    dy = pts[1][1] - pts[0][1]
    if abs(dx) > abs(dy):
        return "E" if dx > 0 else "W"
    return "N" if dy > 0 else "S"


def _is_device_instance(cell_name: str) -> bool:
    """判断实例是否为光子器件（非辅助图形）。

    Args:
        cell_name: 实例 cell 名称。

    Returns:
        True 如果是器件实例（非 ROUND_PATH/Laser/Detector 等辅助图形）。
    """
    return not cell_name.startswith(_IGNORE_PREFIXES)


def _apply_trans(trans, x: float, y: float, dbu: float = 1.0) -> tuple[float, float]:
    """手动应用 DCplxTrans 变换到点坐标。

    klayout Python 绑定中 ``DCplxTrans * DPoint`` 运算符不生效，
    需手动分解旋转/镜像/缩放/平移并应用。

    注意: ``DCplxTrans`` 的位移单位始终是微米（D = double micrometers），
    无论来自 ``inst.cplx_trans`` 还是 ``RecursiveShapeIterator.dtrans()``。
    ``dbu`` 参数保留仅为向后兼容，不再使用。

    Args:
        trans: ``klayout.db.DCplxTrans`` 变换对象。
        x: 点 x 坐标（μm）。
        y: 点 y 坐标（μm）。
        dbu: 已废弃，保留仅为向后兼容。

    Returns:
        变换后的 (x, y) 坐标元组。
    """
    # 分解变换：angle (度) + mirror + scale + disp
    angle = trans.angle  # 旋转角度（度）
    mirror = trans.is_mirror  # 是否镜像
    scale = trans.mag  # 缩放因子
    disp = trans.disp  # 平移向量 (DPoint)，单位微米
    dx = disp.x
    dy = disp.y
    # 应用缩放
    sx, sy = x * scale, y * scale
    # 应用镜像
    if mirror:
        sx = -sx
    # 应用旋转（角度转弧度）
    import math

    rad = math.radians(angle)
    cos_a = math.cos(rad)
    sin_a = math.sin(rad)
    rx = sx * cos_a - sy * sin_a
    ry = sx * sin_a + sy * cos_a
    # 应用平移
    return (rx + dx, ry + dy)


def _collect_device_instances(top, dbu: float) -> list[dict]:
    """步骤 1: 遍历顶层 cell 的实例，构建器件实例列表。

    Args:
        top: klayout 顶层 cell。
        dbu: 数据库单位（μm/dbu）。

    Returns:
        器件实例字典列表，每个含 unique_name/cell_name/center/bbox/trans/params。
    """
    instances: list[dict] = []
    name_counter: dict[str, int] = {}
    for inst in top.each_inst():
        cell_name = inst.cell.name
        if not _is_device_instance(cell_name):
            continue
        idx = name_counter.get(cell_name, 0)
        unique_name = f"{cell_name}_{idx}" if idx > 0 else cell_name
        name_counter[cell_name] = idx + 1
        # 用 dcplx_trans（DCplxTrans，微米单位）而非 cplx_trans（ICplxTrans，dbu 单位）
        # 来源: klayout Instance API https://www.klayout.org/klayout-pypi/overview/instances/
        trans = inst.dcplx_trans
        cell_bbox = inst.cell.dbbox()
        cx = (cell_bbox.left + cell_bbox.right) / 2
        cy = (cell_bbox.bottom + cell_bbox.top) / 2
        center = _apply_trans(trans, cx, cy)
        bl = _apply_trans(trans, cell_bbox.left, cell_bbox.bottom)
        tr = _apply_trans(trans, cell_bbox.right, cell_bbox.top)
        instances.append(
            {
                "unique_name": unique_name,
                "cell_name": cell_name,
                "center": center,
                "bbox": (
                    min(bl[0], tr[0]),
                    min(bl[1], tr[1]),
                    max(bl[0], tr[0]),
                    max(bl[1], tr[1]),
                ),
                "trans": trans,
                "params": {},
            }
        )
    return instances


def _match_devrec_params(top, ly, instances: list[dict], dbu: float) -> None:
    """步骤 2: 从 DEVREC text 提取 Spice_param 并匹配到最近实例。

    Args:
        top: klayout 顶层 cell。
        ly: klayout Layout。
        instances: 器件实例列表（原地更新 params 字段）。
        dbu: 数据库单位。
    """
    devrec_layer = ly.layer(_DEVREC_LAYER[0], _DEVREC_LAYER[1])
    devrec_texts: list[tuple[str, float, float]] = []
    for it in top.begin_shapes_rec(devrec_layer):
        s = it.shape()
        if s.is_text():
            trans = it.dtrans()
            txt = s.text.string
            raw = s.text_dpos
            px, py = _apply_trans(trans, raw.x, raw.y, dbu=dbu)
            devrec_texts.append((txt, px, py))

    for txt, tx, ty in devrec_texts:
        if "Spice_param" not in txt:
            continue
        params = _parse_spice_param(txt)
        best_dist = float("inf")
        best_idx = -1
        for i, inst in enumerate(instances):
            dist = ((inst["center"][0] - tx) ** 2 + (inst["center"][1] - ty) ** 2) ** 0.5
            if dist < best_dist:
                best_dist = dist
                best_idx = i
        if best_idx >= 0 and params:
            instances[best_idx]["params"].update(params)


def _extract_pin_shapes(top, ly, dbu: float) -> tuple[list, list]:
    """步骤 3a: 提取 PIN 层的 path 和 text 形状。

    Args:
        top: klayout 顶层 cell。
        ly: klayout Layout。
        dbu: 数据库单位。

    Returns:
        (pin_paths, pin_texts) 元组。
        pin_paths: list of point lists (每个 path 是 [(x,y), ...])。
        pin_texts: list of (text, x, y) 元组。
    """
    pin_layer = ly.layer(_PIN_LAYER[0], _PIN_LAYER[1])
    pin_paths: list[list[tuple[float, float]]] = []
    pin_texts: list[tuple[str, float, float]] = []
    for it in top.begin_shapes_rec(pin_layer):
        s = it.shape()
        trans = it.dtrans()
        if s.is_text():
            txt = s.text.string
            raw = s.text_dpos
            px, py = _apply_trans(trans, raw.x, raw.y, dbu=dbu)
            pin_texts.append((txt, px, py))
        elif s.is_path():
            dp = s.dpath
            pts: list[tuple[float, float]] = []
            for p in dp.each_point():
                px, py = _apply_trans(trans, p.x, p.y, dbu=dbu)
                pts.append((px, py))
            pin_paths.append(pts)
    return pin_paths, pin_texts


def _match_text_to_path(
    pin_texts: list[tuple[str, float, float]],
    pin_paths: list[list[tuple[float, float]]],
) -> list[dict]:
    """步骤 4: 匹配 PIN text 到最近的 PIN path，构建端口列表。

    Args:
        pin_texts: (text, x, y) 元组列表。
        pin_paths: point 列表的列表。

    Returns:
        端口字典列表，每个含 name/pos/direction。
    """
    ports: list[dict] = []
    for name, tx, ty in pin_texts:
        best_dist = float("inf")
        best_path_pts: list[tuple[float, float]] = []
        for pts in pin_paths:
            for px, py in pts:
                dist = ((tx - px) ** 2 + (ty - py) ** 2) ** 0.5
                if dist < best_dist:
                    best_dist = dist
                    best_path_pts = pts
        if not best_path_pts:
            # R03: PIN text 无匹配 path，禁止静默跳过（GDS 数据不完整）
            raise ValueError(
                f"PIN 端口 '{name}' (位置 {tx},{ty}) 未匹配到任何 PIN path，"
                f"可能 GDS 文件缺少 PIN path 层或数据不完整"
            )
        mid_x = sum(p[0] for p in best_path_pts) / len(best_path_pts)
        mid_y = sum(p[1] for p in best_path_pts) / len(best_path_pts)
        direction = _port_direction_from_path(best_path_pts)
        ports.append(
            {
                "name": name,
                "pos": (mid_x, mid_y),
                "direction": direction,
            }
        )
    return ports


def _extract_pin_ports(top, ly, dbu: float) -> list[dict]:
    """步骤 3+4+5: 提取 PIN 层端口并匹配 text→path。

    Args:
        top: klayout 顶层 cell。
        ly: klayout Layout。
        dbu: 数据库单位。

    Returns:
        端口字典列表，每个含 name/pos/direction。
    """
    pin_paths, pin_texts = _extract_pin_shapes(top, ly, dbu)
    return _match_text_to_path(pin_texts, pin_paths)


def _match_ports_to_devices(ports: list[dict], instances: list[dict]) -> None:
    """步骤 6: 匹配端口到最近的器件实例（原地更新 port['device_name']）。

    Args:
        ports: 端口列表。
        instances: 器件实例列表。
    """
    for port in ports:
        px, py = port["pos"]
        best_dist = float("inf")
        best_name: str | None = None
        for inst in instances:
            cx, cy = inst["center"]
            dist = ((px - cx) ** 2 + (py - cy) ** 2) ** 0.5
            if dist < best_dist:
                best_dist = dist
                best_name = inst["unique_name"]
        port["device_name"] = best_name


def _build_connections(ports: list[dict]) -> list[tuple[str, str, str, str]]:
    """步骤 7: 构建连接列表（同位置端口互连）。

    Args:
        ports: 端口列表（需已匹配 device_name）。

    Returns:
        连接元组列表 (dev1, port1, dev2, port2)。
    """
    connections: list[tuple[str, str, str, str]] = []
    used: set[int] = set()
    for i, p1 in enumerate(ports):
        if i in used:
            continue
        if not p1.get("device_name"):
            # R03: 端口未匹配到器件，禁止静默跳过（GDS 数据不完整）
            raise ValueError(
                f"PIN 端口 '{p1.get('name', '?')}' 未匹配到器件实例"
            )
        for j, p2 in enumerate(ports):
            if j <= i or j in used:
                continue
            if not p2.get("device_name"):
                # R03: 端口未匹配到器件，禁止静默跳过
                raise ValueError(
                    f"PIN 端口 '{p2.get('name', '?')}' 未匹配到器件实例"
                )
            if p1["device_name"] == p2["device_name"]:
                continue
            dist = ((p1["pos"][0] - p2["pos"][0]) ** 2 + (p1["pos"][1] - p2["pos"][1]) ** 2) ** 0.5
            if dist < _PORT_MATCH_TOL:
                connections.append((p1["device_name"], p1["name"], p2["device_name"], p2["name"]))
                used.add(i)
                used.add(j)
                break
    return connections


def _build_device_specs(instances: list[dict], ports: list[dict]) -> list[DeviceSpec]:
    """步骤 8a: 构建 DeviceSpec 列表。

    Args:
        instances: 器件实例列表。
        ports: 端口列表（需已匹配 device_name）。

    Returns:
        DeviceSpec 对象列表。
    """
    devices: list[DeviceSpec] = []
    for inst in instances:
        cell_name = inst["cell_name"]
        polaris_name = siepic_to_polaris(cell_name) or cell_name
        xmin, ymin, xmax, ymax = inst["bbox"]
        w = max(xmax - xmin, 1.0)
        h = max(ymax - ymin, 1.0)
        dev_ports = [
            (p["name"], 0.0, 0.0, p["direction"])
            for p in ports
            if p.get("device_name") == inst["unique_name"]
        ]
        devices.append(
            DeviceSpec(
                name=inst["unique_name"],
                device_type=polaris_name,
                width_um=w,
                height_um=h,
                ports=dev_ports,
                params=inst["params"],
            )
        )
    return devices


def _compute_canvas_size(instances: list[dict], ports: list[dict]) -> tuple[float, float]:
    """步骤 8b: 计算画布尺寸（基于所有器件和端口的边界）。

    Args:
        instances: 器件实例列表。
        ports: 端口列表。

    Returns:
        (canvas_w, canvas_h) 单位 μm。
    """
    all_x: list[float] = []
    all_y: list[float] = []
    for inst in instances:
        xmin, ymin, xmax, ymax = inst["bbox"]
        all_x.extend([xmin, xmax])
        all_y.extend([ymin, ymax])
    for p in ports:
        all_x.append(p["pos"][0])
        all_y.append(p["pos"][1])
    if all_x and all_y:
        canvas_w = max(all_x) - min(all_x) + 50.0
        canvas_h = max(all_y) - min(all_y) + 50.0
    else:
        canvas_w = canvas_h = 500.0
    return max(canvas_w, 100.0), max(canvas_h, 100.0)


def _load_klayout_layout(gds_path: Path):
    """加载 GDS 文件并返回 (Layout, top_cell, dbu)。

    Args:
        gds_path: GDS 文件路径。

    Returns:
        (ly, top, dbu) 元组。

    Raises:
        FileNotFoundError: GDS 文件不存在。
    """
    import klayout.db as db

    if not gds_path.exists():
        raise FileNotFoundError(f"GDS 文件不存在: {gds_path}")

    ly = db.Layout()
    ly.read(str(gds_path))
    top = ly.top_cells()[0]
    return ly, top, ly.dbu


def load_gds_to_circuit(gds_path: str | Path) -> CircuitSpec:
    """从 SiEPIC GDS 文件提取电路规格。

    读取 GDS 文件，解析实例、DEVREC 和 PIN 层，提取器件与连接信息，
    转换为 PoLaRIS CircuitSpec。每个器件实例获得唯一名称（如 ``ebeam_gc_te1550_0``）。

    Args:
        gds_path: GDS 文件路径。

    Returns:
        CircuitSpec 对象，含器件列表与连接列表。
    """
    gds_path = Path(gds_path)
    ly, top, dbu = _load_klayout_layout(gds_path)
    circuit_name = top.name

    logger.info("解析 GDS: %s (top cell: %s)", gds_path.name, circuit_name)

    # 步骤 1-8: 调用拆分后的子函数（规则 7.2 单一职责）
    instances = _collect_device_instances(top, dbu)
    _match_devrec_params(top, ly, instances, dbu)
    ports = _extract_pin_ports(top, ly, dbu)
    _match_ports_to_devices(ports, instances)
    connections = _build_connections(ports)
    devices = _build_device_specs(instances, ports)
    canvas_w, canvas_h = _compute_canvas_size(instances, ports)

    circuit = CircuitSpec(
        name=circuit_name,
        devices=devices,
        connections=connections,
        canvas_w=canvas_w,
        canvas_h=canvas_h,
    )

    logger.info(
        "GDS 解析完成: %s (%d 器件, %d 连接, %d 端口)",
        circuit_name,
        len(circuit.devices),
        len(circuit.connections),
        len(ports),
    )
    return circuit


__all__ = ["load_gds_to_circuit"]
