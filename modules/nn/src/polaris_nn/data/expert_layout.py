"""SiEPIC GDS 专家布局与布线提取器 — 为模仿学习提供专家示范数据。

从真实 SiEPIC EBeam PDK GDS 文件提取：
1. 专家布局：每个器件的 (x, y, rotation, mirror) 绝对坐标
2. 专家布线：Waveguide 层 (1,0) 的波导路径点序列

这些数据作为行为克隆（Behavior Cloning）的"教师信号"，
让 PPO 从真实工程师设计的版图中学习初始策略。

来源:
- SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK (MIT, UBC, Lukas Chrostowski)
- SiEPIC EBeam PDK Examples: https://github.com/SiEPIC/SiEPIC_EBeam_PDK/tree/master/Examples
- klayout Instance class: https://www.klayout.org/klayout-pypi/overview/instances/
- 模仿学习理论: Pomerleau 1989, "ALVINN: An Autonomous Land Vehicle in a Neural Network"
- 模仿学习综述: Gavenski et al., "A Survey of Imitation Learning Methods",
  ACM PACMMECS 2024, https://arxiv.org/abs/2404.19456
- Pomerleau 1989, "ALVINN: An Autonomous Land Vehicle in a Neural Network",
  NeurIPS 1989, https://papers.nips.cc/paper/95-alvinn-an-autonomous-land-vehicle-in-a-neural-network
"""

from __future__ import annotations

import logging
from pathlib import Path

from polaris_nn.data.gds_loader import (
    _apply_trans,
    _build_connections,
    _build_device_specs,
    _collect_device_instances,
    _compute_canvas_size,
    _extract_pin_ports,
    _load_klayout_layout,
    _match_devrec_params,
    _match_ports_to_devices,
)
from polaris_nn.data.specs import CircuitSpec

logger = logging.getLogger(__name__)

# 波导几何层（SiEPIC EBeam PDK 中波导绘制在 layer 1, datatype 0）
_WG_LAYER = (1, 0)


def extract_expert_placements(instances: list[dict]) -> dict[str, dict]:
    """从器件实例列表提取专家布局坐标（用于模仿学习标签）。

    每个器件的专家布局包含：
    - ``x``, ``y``: 器件中心坐标（μm）
    - ``rotation``: 旋转角度（度，0/90/180/270）
    - ``mirror``: 是否镜像
    - ``bbox``: 边界框 (xmin, ymin, xmax, ymax)
    - ``width``, ``height``: 器件宽高（μm）

    Args:
        instances: ``_collect_device_instances`` 返回的器件实例列表。

    Returns:
        布局字典 {device_unique_name: {x, y, rotation, mirror, bbox, width, height}}。
    """
    placements: dict[str, dict] = {}
    for inst in instances:
        trans = inst["trans"]
        cx, cy = inst["center"]
        xmin, ymin, xmax, ymax = inst["bbox"]
        placements[inst["unique_name"]] = {
            "x": float(cx),
            "y": float(cy),
            "rotation": float(trans.angle),
            "mirror": bool(trans.is_mirror),
            "bbox": [float(xmin), float(ymin), float(xmax), float(ymax)],
            "width": float(xmax - xmin),
            "height": float(ymax - ymin),
        }
    return placements


def extract_waveguide_paths(top, ly, dbu: float) -> list[list[tuple[float, float]]]:
    """从 Waveguide 层 (1,0) 提取波导路径点序列（专家布线轨迹）。

    SiEPIC EBeam PDK 中波导绘制在 layer 1, datatype 0，使用 Path/Polygon 几何。
    本函数提取所有 Path 和 Polygon 的顶点序列，作为专家布线轨迹。

    来源:
    - SiEPIC EBeam PDK layer table: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
    - openEBL submission guide: Si layer 1/0 为 Fabricated 层

    Args:
        top: klayout 顶层 cell。
        ly: klayout Layout。
        dbu: 数据库单位。

    Returns:
        波导路径列表，每条路径是 [(x1,y1), (x2,y2), ...] 点序列（μm）。
    """
    wg_layer = ly.layer(_WG_LAYER[0], _WG_LAYER[1])
    paths: list[list[tuple[float, float]]] = []
    for it in top.begin_shapes_rec(wg_layer):
        s = it.shape()
        trans = it.dtrans()
        if s.is_path():
            dp = s.dpath
            pts: list[tuple[float, float]] = []
            for p in dp.each_point():
                px, py = _apply_trans(trans, p.x, p.y, dbu=dbu)
                pts.append((px, py))
            if len(pts) >= 2:
                paths.append(pts)
        elif s.is_polygon():
            dpoly = s.dpolygon
            pts = []
            for p in dpoly.each_point_hull():
                px, py = _apply_trans(trans, p.x, p.y, dbu=dbu)
                pts.append((px, py))
            if len(pts) >= 2:
                paths.append(pts)
    return paths


def _parse_circuit_from_gds(gds_path: Path) -> tuple[CircuitSpec, list[dict]]:
    """解析 GDS 提取电路规格与器件实例（复用 gds_loader 的 8 步流程）。

    Args:
        gds_path: GDS 文件路径。

    Returns:
        (circuit, instances) 元组。
    """
    ly, top, dbu = _load_klayout_layout(gds_path)
    circuit_name = top.name
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
    return circuit, instances


def load_gds_to_circuit_with_layout(
    gds_path: str | Path,
) -> tuple[CircuitSpec, dict[str, dict], list[list[tuple[float, float]]]]:
    """从 SiEPIC GDS 提取电路规格 + 专家布局 + 专家布线（用于模仿学习）。

    在 ``load_gds_to_circuit`` 基础上额外提取：
    1. 专家布局：每个器件的 (x, y, rotation, mirror) 坐标
    2. 专家布线：Waveguide 层的波导路径点序列

    这是模仿学习（Behavior Cloning）的核心数据接口，提取真实工程师
    在 SiEPIC EBeam PDK 中设计的版图作为"专家示范"。

    Args:
        gds_path: GDS 文件路径。

    Returns:
        (circuit, placements, routes) 三元组：
        - circuit: CircuitSpec 对象（网表）
        - placements: {device_name: {x, y, rotation, mirror, bbox, width, height}}
        - routes: [[(x1,y1), (x2,y2), ...], ...] 波导路径点序列列表

    来源:
    - SiEPIC EBeam PDK Examples: https://github.com/SiEPIC/SiEPIC_EBeam_PDK/tree/master/Examples
    - 模仿学习理论: Pomerleau 1989, "ALVINN: An Autonomous Land Vehicle in a Neural Network"
    """
    gds_path = Path(gds_path)
    logger.info("解析 GDS（含专家布局）: %s", gds_path.name)

    circuit, instances = _parse_circuit_from_gds(gds_path)
    placements = extract_expert_placements(instances)

    # 提取专家布线（需重新加载 klayout 对象以访问 layer）
    ly, top, dbu = _load_klayout_layout(gds_path)
    routes = extract_waveguide_paths(top, ly, dbu)

    logger.info(
        "GDS 解析完成（含专家布局）: %s (%d 器件, %d 连接, %d 布局, %d 波导路径)",
        circuit.name,
        len(circuit.devices),
        len(circuit.connections),
        len(placements),
        len(routes),
    )
    return circuit, placements, routes


__all__ = [
    "extract_expert_placements",
    "extract_waveguide_paths",
    "load_gds_to_circuit_with_layout",
]
