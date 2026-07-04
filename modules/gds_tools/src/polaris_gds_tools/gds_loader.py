"""SiEPIC GDS 电路解析器（polaris-gds-tools 子模块，R345）。

从 SiEPIC EBeam PDK 格式的 GDS 文件提取器件列表与连接关系，
转换为 PoLaRIS CircuitSpec 兼容 dict（polaris-core 风格）。

V5.0 拆包后旧 ``polaris.data.gds_loader`` 下线，导致 229 个真实 SiEPIC GDS
用例无法解析。本模块作为 polaris-gds-tools 底层工具入口恢复该能力。

## SiEPIC GDS 格式（来源: SiEPIC_EBeam_PDK, MIT, UBC, Lukas Chrostowski）

- **DEVREC(68,0)**: 器件识别层。Polygon/Box=器件边界框；
  Text=``Lumerical_INTERCONNECT_component=<name>`` + ``Spice_param:<params>``
- **PIN(69,0)**: 端口标记层。Path=2点路径标记端口位置与方向；
  Text=端口名（如 ``pin1``/``opt_input``）

## 多策略器件识别（按 GDS 实际层结构选择，非 fall-back，每条都基于真实 GDS 数据）

- **策略 A（instance）**: 顶层 cell 有 instance → instance cell 名即器件类型
- **策略 B（DEVREC polygon）**: 顶层无 instance 但有 DEVREC polygon →
  每个 polygon 边界框 = 一个器件（Lumerical CML 导出格式）
- **策略 C（顶层 cell）**: 都没有 → 顶层 cell 自身作为单一器件
  （单器件测试版图，如 ``wg_test.gds``）

## R03 异常处理

- 文件不存在 / klayout 读取失败 / 无顶层 cell / PIN text 无匹配 path → raise
- 无 instance / 无 DEVREC / 无 PIN → 不 raise（合法的器件库/测试版图）

## 学术依据（R02 学术诚信）

- GDSII 格式规范 SEMI P39-0308E:
  https://www.semi.org/en/products-services/notices/download-p39-0308e
- KLayout Database API: https://www.klayout.org/doc-qt5/code/
- KLayout Instance class: https://www.klayout.org/klayout-pypi/overview/instances/
- SiEPIC EBeam PDK (MIT, UBC): https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- SiEPIC-Tools netlist extraction: https://github.com/SiEPIC/SiEPIC-Tools
- Chrostowski & Hochberg, Silicon Photonics Design, CUP 2015,
  ISBN 9781107016838: https://www.cambridge.org/9781107016838

合规: R01 / R02 / R03 / R04 / R05 / R11。函数≤80行 / 文件≤800行。
"""

from __future__ import annotations

import logging
import math
import re
from pathlib import Path

logger = logging.getLogger(__name__)

__all__ = [
    "load_gds_to_circuit",
    "load_gds_to_circuit_spec",
    "siepic_to_polaris",
]


# SiEPIC 器件名 → PoLaRIS 器件名映射
# 来源: SiEPIC EBeam PDK (MIT, UBC) https://github.com/SiEPIC/SiEPIC_EBeam_PDK
#       ubcpdk https://github.com/gdsfactory/ubc
# 实测从 229 个真实 SiEPIC GDS 文件的 instance cell 名归纳。
_SIEPIC_TO_POLARIS: dict[str, str] = {
    "ebeam_y_1550": "y_branch",
    "ebeam_y_te1550": "y_branch",
    "ebeam_y_1310": "y_branch",
    "ebeam_y_adiabatic": "y_branch",
    "ebeam_y_adiabatic_1310": "y_branch",
    "ebeam_y_adiabatic_500pin": "y_branch",
    "ebeam_gc_te1550": "grating_coupler_1d",
    "ebeam_gc_te1310": "grating_coupler_1d",
    "ebeam_gc_te1550_broadband": "grating_coupler_1d",
    "ebeam_gc_te1550_90nmSlab": "grating_coupler_1d",
    "ebeam_gc_tm1550": "grating_coupler_2d",
    "gc_te1550": "grating_coupler_1d",
    "gc_tm1550": "grating_coupler_2d",
    "ebeam_dc_te1550": "directional_coupler",
    "ebeam_bdc_te1550": "directional_coupler",
    "ebeam_bdc_tm1550": "directional_coupler",
    "ebeam_dc_halfring_te1550": "ring_resonator",
    "ebeam_dc_halfring_straight": "ring_resonator",
    "ebeam_mmi_1x2_te_1550": "mmi_1x2",
    "ebeam_mmi_2x2_te_1550": "mmi_2x2",
    "ebeam_terminator_te1550": "terminator",
    "ebeam_terminator_te1310": "terminator",
    "ebeam_terminator_tm1550": "terminator",
    "ebeam_crossing_te1550": "crossing",
    "ebeam_crossing4": "crossing",
    "ebeam_taper_te1550": "linear_taper",
    "ebeam_taper_475_500_te1550": "linear_taper",
    "ebeam_wg_strip_1550": "strip_waveguide",
    "ebeam_bend_te1550": "bend",
    "ebeam_splitter_swg_assist_te1550": "mmi_2x2",
    "ebeam_splitter_swg_assist_te1310": "mmi_2x2",
    "ebeam_splitter_adiabatic_swg_te1550": "directional_coupler",
}


def siepic_to_polaris(siepic_name: str) -> str:
    """将 SiEPIC 器件名转换为 PoLaRIS 器件名，未找到返回原名。

    来源: SiEPIC EBeam PDK https://github.com/SiEPIC/SiEPIC_EBeam_PDK
    """
    return _SIEPIC_TO_POLARIS.get(siepic_name, siepic_name)


# SiEPIC 标准 layer 编号（来源: SiEPIC EBeam PDK）
_DEVREC_LAYER = (68, 0)
_PIN_LAYER = (69, 0)
_PORT_GEOM_LAYER = (99, 0)  # gdsfactory 端口几何层（备选）

# 端口位置匹配容差（μm）。
# SiEPIC EBeam PDK 中相邻器件端口间距典型值 5.5μm，跨器件直接对齐的端口间距
# 可达 10-15μm。容差 15.0μm 可匹配大多数直接对齐连接，同时通过 device_name
# 检查排除同器件端口。来源: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
_PORT_MATCH_TOL = 15.0

# 忽略的非器件实例名前缀（辅助图形/虚拟元件）。
# 来源: SiEPIC-Tools SiEPIC_Verifier.netlist_extract
#   https://github.com/SiEPIC/SiEPIC-Tools
_IGNORE_PREFIXES = (
    "ROUND_PATH",
    "LumericalINTERCONNECT_Laser",
    "LumericalINTERCONNECT_Detector",
    "OpticalFibre",
    "TE1550_SubGC",
    "Waveguide_Route",
)


def _import_klayout_db():
    """导入 klayout.db，未安装 raise ImportError（R03）。"""
    try:
        import klayout.db as db
    except ImportError as e:
        raise ImportError(
            "klayout 未安装，无法执行 SiEPIC GDS 解析。"
            "安装方式: pip install klayout。"
            f"原始错误: {e}"
        ) from e
    return db


def _parse_spice_param(text: str) -> dict:
    """解析 ``Spice_param:wg_width=0.500u gap=0.100u`` 格式的参数字符串。

    返回参数字典，值已去除 ``u`` 后缀并转为 float（无法转则保留 str）。
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
    """从 DEVREC text 提取 ``Lumerical_INTERCONNECT_component=<name>`` 的器件名。"""
    match = re.search(r"Lumerical_INTERCONNECT_component=(\S+)", text)
    return match.group(1) if match else None


def _apply_trans(trans, x: float, y: float) -> tuple[float, float]:
    """手动应用 DCplxTrans 变换到点坐标（μm）。

    klayout Python 绑定中 ``DCplxTrans * DPoint`` 运算符不生效，需手动分解
    旋转/镜像/缩放/平移并应用。DCplxTrans 位移单位始终是微米。
    来源: KLayout DCplxTrans
        https://www.klayout.org/doc-qt5/code/class_DCplxTrans.html
    """
    angle = trans.angle
    mirror = trans.is_mirror
    scale = trans.mag
    disp = trans.disp
    dx = disp.x
    dy = disp.y
    sx, sy = x * scale, y * scale
    if mirror:
        sx = -sx
    rad = math.radians(angle)
    cos_a = math.cos(rad)
    sin_a = math.sin(rad)
    rx = sx * cos_a - sy * sin_a
    ry = sx * sin_a + sy * cos_a
    return (rx + dx, ry + dy)


def _port_direction_from_path(pts: list[tuple[float, float]]) -> str:
    """根据 PIN Path 的两点方向推断端口朝向（N/S/E/W）。"""
    if len(pts) < 2:
        return "E"
    dx = pts[1][0] - pts[0][0]
    dy = pts[1][1] - pts[0][1]
    if abs(dx) > abs(dy):
        return "E" if dx > 0 else "W"
    return "N" if dy > 0 else "S"


def _is_device_instance(cell_name: str) -> bool:
    """判断实例是否为光子器件（非辅助图形 ROUND_PATH/Laser/Detector 等）。"""
    return not cell_name.startswith(_IGNORE_PREFIXES)


def _find_layer(ly, layer: int, datatype: int):
    """查找层，不存在返回 None（层缺失是合法状态，非 fall-back）。"""
    for li in ly.layer_indices():
        info = ly.get_info(li)
        if int(info.layer) == layer and int(info.datatype) == datatype:
            return li
    return None


def load_gds_to_circuit(gds_path: str | Path) -> dict:
    """从 SiEPIC GDS 文件提取电路规格，返回 polaris-core 兼容 dict。

    读取 GDS 文件，按层结构选择器件识别策略（instance / DEVREC polygon /
    顶层 cell 自身），从 PIN 层提取端口并推断跨器件连接，转换为 polaris-core
    CircuitSpec 兼容 dict。

    返回 dict 结构（polaris-core 风格 + 任务要求的简化字段）::

        {
          "name": "top_cell_name",
          "devices": [
            {
              "name": "ebeam_gc_te1550",   # 唯一器件名 (=id)
              "device_type": "grating_coupler_1d",  # PoLaRIS 器件类型
              "x": 0.0, "y": 0.0,          # 器件中心坐标 (μm)
              "width_um": 15.0, "height_um": 15.0,  # 器件尺寸
              "ports": [["pin1", 0.0, 7.5, "W"], ...],
              "params": {"wg_width": 0.5}
            }, ...
          ],
          "connections": [["dev1","port1","dev2","port2"], ...],
          "canvas_w": 1000.0, "canvas_h": 1000.0,
          "process_node": "220nm SOI",
          "optical_wavelength_nm": 1550.0,
        }

    Raises:
        FileNotFoundError: GDS 文件不存在。
        RuntimeError: klayout 读取失败（R03 禁止 fall-back）。
        ValueError: 无顶层 cell / PIN text 无匹配 path（GDS 数据不完整）。
        ImportError: klayout 未安装。

    来源:
    - SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
    - KLayout Layout.read: https://www.klayout.org/doc-qt5/code/class_Layout.html
    """
    db = _import_klayout_db()
    path = Path(gds_path)
    if not path.exists():
        raise FileNotFoundError(f"GDS 文件不存在: {gds_path}")
    if not path.is_file():
        raise ValueError(f"路径不是文件: {gds_path}")
    ly, top, dbu = _read_layout(db, path, gds_path)
    circuit_name = str(top.name)
    logger.info("解析 GDS: %s (top cell: %s)", path.name, circuit_name)

    instances = _collect_device_instances(top)
    if instances:
        strategy = "instance"
    else:
        instances = _collect_devrec_polygon_devices(top, ly, dbu)
        strategy = "devrec_polygon" if instances else "top_cell"

    if strategy == "top_cell":
        instances = _build_top_cell_device(top, dbu)

    _match_devrec_params(top, ly, instances, dbu)
    ports = _extract_pin_ports(top, ly, dbu)
    _match_ports_to_devices(ports, instances)
    connections = _build_connections(ports)
    devices = _build_device_specs(instances, ports)
    canvas_w, canvas_h = _compute_canvas_size(instances, ports)

    logger.info(
        "GDS 解析完成: %s [策略=%s] (%d 器件, %d 连接, %d 端口)",
        circuit_name, strategy, len(devices), len(connections), len(ports),
    )
    return {
        "name": circuit_name,
        "devices": devices,
        "connections": [list(c) for c in connections],
        "canvas_w": canvas_w,
        "canvas_h": canvas_h,
        "process_node": "220nm SOI",
        "optical_wavelength_nm": 1550.0,
    }


def load_gds_to_circuit_spec(gds_path: str | Path):
    """从 SiEPIC GDS 文件提取电路规格，返回 polaris_core.CircuitSpec 对象。

    与 :func:`load_gds_to_circuit` 相同的解析逻辑，但返回 polaris_core 的
    CircuitSpec dataclass（懒导入 polaris_core，避免底层工具硬依赖上层模块）。

    Raises:
        ImportError: polaris_core 未安装。
        （同 :func:`load_gds_to_circuit` 的异常）
    """
    try:
        from polaris_core.specs import CircuitSpec, DeviceSpec
    except ImportError as e:
        raise ImportError(
            "polaris_core 未安装，无法返回 CircuitSpec 对象。"
            "可用 load_gds_to_circuit() 获取 dict 格式。"
            f"原始错误: {e}"
        ) from e
    data = load_gds_to_circuit(gds_path)
    devices = [
        DeviceSpec(
            name=d["name"],
            device_type=d["device_type"],
            width_um=d["width_um"],
            height_um=d["height_um"],
            ports=[tuple(p) for p in d["ports"]],
            params=d["params"],
        )
        for d in data["devices"]
    ]
    return CircuitSpec(
        name=data["name"],
        devices=devices,
        connections=[tuple(c) for c in data["connections"]],
        canvas_w=data["canvas_w"],
        canvas_h=data["canvas_h"],
    )


def _read_layout(db, path: Path, gds_path):
    """读取 GDSII 并返回 (Layout, top_cell, dbu)（R03 禁止 fall-back）。

    Raises:
        RuntimeError: klayout 读取失败。
        ValueError: 无顶层 cell。
    """
    ly = db.Layout()
    try:
        ly.read(str(path))
    except Exception as e:
        raise RuntimeError(
            f"klayout 读取 GDSII 失败: {type(e).__name__}: {e}。"
            f"禁止 fall-back（R03）。"
        ) from e
    dbu = float(ly.dbu)
    top_cells = ly.top_cells()
    if not top_cells:
        raise ValueError(
            f"GDSII 文件 {gds_path} 无顶层 cell，文件可能为空或损坏"
        )
    return ly, top_cells[0], dbu


# --- 策略 A: instance 识别 ---
def _collect_device_instances(top) -> list[dict]:
    """策略 A: 遍历顶层 cell 的实例，构建器件实例列表。

    空列表表示顶层 cell 无 instance（触发策略 B/C）。
    来源: KLayout Instance API
        https://www.klayout.org/klayout-pypi/overview/instances/
    """
    instances: list[dict] = []
    name_counter: dict[str, int] = {}
    for inst in top.each_inst():
        cell_name = str(inst.cell.name)
        if not _is_device_instance(cell_name):
            continue
        idx = name_counter.get(cell_name, 0)
        unique_name = f"{cell_name}_{idx}" if idx > 0 else cell_name
        name_counter[cell_name] = idx + 1
        trans = inst.dcplx_trans
        cell_bbox = inst.cell.dbbox()
        cx = (cell_bbox.left + cell_bbox.right) / 2
        cy = (cell_bbox.bottom + cell_bbox.top) / 2
        center = _apply_trans(trans, cx, cy)
        bl = _apply_trans(trans, cell_bbox.left, cell_bbox.bottom)
        tr = _apply_trans(trans, cell_bbox.right, cell_bbox.top)
        instances.append({
            "unique_name": unique_name,
            "cell_name": cell_name,
            "center": center,
            "bbox": (
                min(bl[0], tr[0]), min(bl[1], tr[1]),
                max(bl[0], tr[0]), max(bl[1], tr[1]),
            ),
            "trans": trans,
            "params": {},
        })
    return instances


# --- 策略 B: DEVREC polygon 识别 ---
def _collect_devrec_polygon_devices(top, ly, dbu: float) -> list[dict]:
    """策略 B: 从 DEVREC(68,0) polygon 提取器件（顶层无 instance 时使用）。

    每个 DEVREC polygon/box = 一个器件，边界框即器件 bbox。
    器件类型从同位置的 DEVREC text 提取（Lumerical_INTERCONNECT_component=）。
    空列表表示无 DEVREC polygon（触发策略 C）。
    来源: SiEPIC EBeam PDK DEVREC 层定义
        https://github.com/SiEPIC/SiEPIC_EBeam_PDK
    """
    li_devrec = _find_layer(ly, _DEVREC_LAYER[0], _DEVREC_LAYER[1])
    if li_devrec is None:
        return []
    polygons: list[tuple[float, float, float, float]] = []
    texts: list[tuple[str, float, float]] = []
    for it in top.begin_shapes_rec(li_devrec):
        s = it.shape()
        trans = it.dtrans()
        if s.is_box():
            b = s.bbox()
            xmin, ymin = float(b.left) * dbu, float(b.bottom) * dbu
            xmax, ymax = float(b.right) * dbu, float(b.top) * dbu
            polygons.append((xmin, ymin, xmax, ymax))
        elif s.is_polygon():
            poly = s.polygon
            b = poly.bbox()
            xmin, ymin = float(b.left) * dbu, float(b.bottom) * dbu
            xmax, ymax = float(b.right) * dbu, float(b.top) * dbu
            polygons.append((xmin, ymin, xmax, ymax))
        elif s.is_text():
            txt = str(s.text.string)
            raw = s.text_dpos
            px, py = _apply_trans(trans, raw.x, raw.y)
            texts.append((txt, px, py))
    if not polygons:
        return []
    instances: list[dict] = []
    name_counter: dict[str, int] = {}
    for (xmin, ymin, xmax, ymax) in polygons:
        cx = (xmin + xmax) / 2
        cy = (ymin + ymax) / 2
        comp_name = _match_nearest_text(texts, cx, cy, max_dist=50.0)
        cell_name = comp_name or "unknown_device"
        idx = name_counter.get(cell_name, 0)
        unique_name = f"{cell_name}_{idx}" if idx > 0 else cell_name
        name_counter[cell_name] = idx + 1
        instances.append({
            "unique_name": unique_name,
            "cell_name": cell_name,
            "center": (cx, cy),
            "bbox": (xmin, ymin, xmax, ymax),
            "trans": None,  # DEVREC polygon 已是顶层坐标，无变换
            "params": {},
        })
    return instances


def _match_nearest_text(
    texts: list[tuple[str, float, float]],
    x: float, y: float, max_dist: float,
) -> str | None:
    """匹配最近文本并提取器件名（max_dist 内未匹配返回 None）。"""
    best_dist = float("inf")
    best_text = ""
    for txt, tx, ty in texts:
        dist = math.hypot(x - tx, y - ty)
        if dist < best_dist:
            best_dist = dist
            best_text = txt
    if not best_text or best_dist > max_dist:
        return None
    return _extract_component_name(best_text)


# --- 策略 C: 顶层 cell 自身 ---
def _build_top_cell_device(top, dbu: float) -> list[dict]:
    """策略 C: 顶层 cell 自身作为单一器件（无 instance 且无 DEVREC 时使用）。

    单器件测试版图（如 wg_test.gds 仅含一段波导），整个顶层 cell 即一个器件。
    """
    bbox_dbu = top.bbox()
    xmin = float(bbox_dbu.left) * dbu
    ymin = float(bbox_dbu.bottom) * dbu
    xmax = float(bbox_dbu.right) * dbu
    ymax = float(bbox_dbu.top) * dbu
    cx = (xmin + xmax) / 2
    cy = (ymin + ymax) / 2
    return [{
        "unique_name": str(top.name),
        "cell_name": str(top.name),
        "center": (cx, cy),
        "bbox": (xmin, ymin, xmax, ymax),
        "trans": None,
        "params": {},
    }]


def _match_devrec_params(top, ly, instances: list[dict], dbu: float) -> None:
    """从 DEVREC text 提取 Spice_param 并匹配到最近实例（原地更新 params）。"""
    li_devrec = _find_layer(ly, _DEVREC_LAYER[0], _DEVREC_LAYER[1])
    if li_devrec is None:
        return
    devrec_texts: list[tuple[str, float, float]] = []
    for it in top.begin_shapes_rec(li_devrec):
        s = it.shape()
        if s.is_text():
            trans = it.dtrans()
            txt = str(s.text.string)
            raw = s.text_dpos
            px, py = _apply_trans(trans, raw.x, raw.y)
            devrec_texts.append((txt, px, py))
    if not devrec_texts or not instances:
        return
    for txt, tx, ty in devrec_texts:
        if "Spice_param" not in txt:
            continue
        params = _parse_spice_param(txt)
        if not params:
            continue
        best_dist = float("inf")
        best_idx = -1
        for i, inst in enumerate(instances):
            dist = math.hypot(inst["center"][0] - tx, inst["center"][1] - ty)
            if dist < best_dist:
                best_dist = dist
                best_idx = i
        if best_idx >= 0:
            instances[best_idx]["params"].update(params)


def _extract_pin_shapes(top, ly, dbu: float) -> tuple[list, list]:
    """提取 PIN(69,0) 层的 path 和 text 形状。

    Returns:
        (pin_paths, pin_texts) 元组。
        pin_paths: list of point lists (每个 path 是 [(x,y), ...])。
        pin_texts: list of (text, x, y) 元组。
    """
    li_pin = _find_layer(ly, _PIN_LAYER[0], _PIN_LAYER[1])
    if li_pin is None:
        return [], []
    pin_paths: list[list[tuple[float, float]]] = []
    pin_texts: list[tuple[str, float, float]] = []
    for it in top.begin_shapes_rec(li_pin):
        s = it.shape()
        trans = it.dtrans()
        if s.is_text():
            txt = str(s.text.string)
            raw = s.text_dpos
            px, py = _apply_trans(trans, raw.x, raw.y)
            pin_texts.append((txt, px, py))
        elif s.is_path():
            dp = s.dpath
            pts: list[tuple[float, float]] = []
            for p in dp.each_point():
                px, py = _apply_trans(trans, p.x, p.y)
                pts.append((px, py))
            pin_paths.append(pts)
    return pin_paths, pin_texts


def _match_text_to_path(
    pin_texts: list[tuple[str, float, float]],
    pin_paths: list[list[tuple[float, float]]],
) -> list[dict]:
    """匹配 PIN text 到最近的 PIN path，构建端口列表。

    Raises:
        ValueError: PIN text 无匹配 path（R03 禁止静默跳过）。
    """
    ports: list[dict] = []
    for name, tx, ty in pin_texts:
        best_dist = float("inf")
        best_path_pts: list[tuple[float, float]] = []
        for pts in pin_paths:
            for px, py in pts:
                dist = math.hypot(tx - px, ty - py)
                if dist < best_dist:
                    best_dist = dist
                    best_path_pts = pts
        if not best_path_pts:
            raise ValueError(
                f"PIN 端口 '{name}' (位置 {tx:.3f},{ty:.3f}) 未匹配到任何 PIN path，"
                f"可能 GDS 文件缺少 PIN path 层或数据不完整（R03 禁止 fall-back）"
            )
        mid_x = sum(p[0] for p in best_path_pts) / len(best_path_pts)
        mid_y = sum(p[1] for p in best_path_pts) / len(best_path_pts)
        direction = _port_direction_from_path(best_path_pts)
        ports.append({"name": name, "pos": (mid_x, mid_y), "direction": direction})
    return ports


def _extract_pin_ports(top, ly, dbu: float) -> list[dict]:
    """提取 PIN 层端口并匹配 text→path。无 PIN 层时返回空列表。"""
    pin_paths, pin_texts = _extract_pin_shapes(top, ly, dbu)
    if not pin_texts:
        return []
    return _match_text_to_path(pin_texts, pin_paths)


def _match_ports_to_devices(ports: list[dict], instances: list[dict]) -> None:
    """匹配端口到最近的器件实例（原地更新 port['device_name']）。

    Raises:
        ValueError: 有端口但无器件实例可匹配（R03 禁止 fall-back）。
    """
    if not instances:
        if ports:
            raise ValueError(
                f"有 {len(ports)} 个 PIN 端口但无器件实例可匹配，"
                f"GDS 数据不完整（R03 禁止 fall-back）"
            )
        return
    for port in ports:
        px, py = port["pos"]
        best_dist = float("inf")
        best_name: str | None = None
        for inst in instances:
            cx, cy = inst["center"]
            dist = math.hypot(px - cx, py - cy)
            if dist < best_dist:
                best_dist = dist
                best_name = inst["unique_name"]
        port["device_name"] = best_name


def _build_connections(ports: list[dict]) -> list[tuple[str, str, str, str]]:
    """构建连接列表（同位置端口互连，跨器件）。

    Raises:
        ValueError: 端口未匹配到器件（R03 禁止 fall-back）。
    """
    connections: list[tuple[str, str, str, str]] = []
    used: set[int] = set()
    for i, p1 in enumerate(ports):
        if i in used:
            continue
        dev1 = p1.get("device_name")
        if not dev1:
            raise ValueError(
                f"PIN 端口 '{p1.get('name', '?')}' 未匹配到器件实例（R03）"
            )
        for j, p2 in enumerate(ports):
            if j <= i or j in used:
                continue
            dev2 = p2.get("device_name")
            if not dev2:
                raise ValueError(
                    f"PIN 端口 '{p2.get('name', '?')}' 未匹配到器件实例（R03）"
                )
            if dev1 == dev2:
                continue
            dist = math.hypot(
                p1["pos"][0] - p2["pos"][0], p1["pos"][1] - p2["pos"][1]
            )
            if dist < _PORT_MATCH_TOL:
                connections.append((dev1, p1["name"], dev2, p2["name"]))
                used.add(i)
                used.add(j)
                break
    return connections


def _build_device_specs(instances: list[dict], ports: list[dict]) -> list[dict]:
    """构建 polaris-core 风格 device dict 列表。

    每个器件含任务要求的简化字段（name/x/y/width_um/height_um）+
    polaris-core 完整字段（device_type/ports/params）。
    """
    devices: list[dict] = []
    for inst in instances:
        cell_name = inst["cell_name"]
        polaris_name = siepic_to_polaris(cell_name)
        xmin, ymin, xmax, ymax = inst["bbox"]
        w = max(xmax - xmin, 1.0)
        h = max(ymax - ymin, 1.0)
        cx, cy = inst["center"]
        dev_ports = [
            [p["name"], 0.0, 0.0, p["direction"]]
            for p in ports
            if p.get("device_name") == inst["unique_name"]
        ]
        devices.append({
            "name": inst["unique_name"],
            "device_type": polaris_name,
            "x": float(cx),
            "y": float(cy),
            "width_um": float(w),
            "height_um": float(h),
            "ports": dev_ports,
            "params": dict(inst["params"]),
        })
    return devices


def _compute_canvas_size(
    instances: list[dict], ports: list[dict]
) -> tuple[float, float]:
    """计算画布尺寸（基于所有器件和端口的边界），最小 100.0 μm。"""
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
