"""阶段 4: 智能布线。

对布局结果执行智能布线，使用 PoLaRIS v5.0 polaris-route 子模块的曲线波导
（curvy router），输出波导路径、总插入损耗、交叉数与弯曲数。

对应路标: R17（弹性连接器）/ R19（曲线波导）

PoLaRIS v5.0 迁移说明:
    旧 v4 使用 IntegratedPipeline（内含布局+布线）。v5.0 已将布线能力封装为
    polaris-route 子模块的稳定 API ``route_circuit(circuit, placements)``，
    需先调用 polaris-place ``place_circuit`` 获取布局，再执行布线。
    本 stage 改用 place_circuit + route_circuit 两步调用。

弯曲数计算来源:
- LiDAR ISPD 2025, curvy-aware routing
  https://dl.acm.org/doi/10.1145/3698364.3705355
  弯曲数 = 路径点序列中方向改变的次数（相邻线段方向不同则计为一次弯曲）。

曲线波导来源:
- Klauss et al., "Euler spiral waveguide bends",
  Opt Express 2018, https://doi.org/10.1364/OE.26.029637
- LiDAR 2.0 TCAD 2025: https://arxiv.org/html/2505.17239v2

损耗模型来源:
- SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
  传播损耗 SOI 3.0 dB/cm，单弯损耗 0.05 dB，单次交叉损耗 0.3 dB。
- Soref et al. 1993 IEEE Proc. 41(9) 1182-1183（SOI 3 dB/cm）
  https://ieeexplore.ieee.org/document/1148303
- Chrostowski & Hochberg 2015 §3.3 Silicon Photonics Design
  https://www.cambridge.org/core/search?searchField=isbn&searchTerms=1107007731
"""

from __future__ import annotations

import logging
from pathlib import Path

from polaris_core import CircuitSpec, DeviceSpec, circuit_to_dict
from polaris_place import place_circuit
from polaris_route import route_circuit

_logger = logging.getLogger("e2e_showcase")

# ASCII 布线预览网格尺寸
_ASCII_GRID_W = 40
_ASCII_GRID_H = 15


def _mzi_circuit() -> CircuitSpec:
    """构造 MZI 干涉仪电路规格（含端口，供布线使用）。

    5 器件：1 光栅耦合器 + 2 MMI + 2 波导臂，构成马赫-曾德干涉仪。

    Returns:
        MZI 电路规格。
    """
    return CircuitSpec(
        name="MZI",
        canvas_w=500,
        canvas_h=300,
        devices=[
            DeviceSpec("gc1", "grating_coupler", 10, 10,
                       ports=[("in", 0, 5, "west"), ("out", 10, 5, "east")]),
            DeviceSpec("mmi1", "mmi_1x2", 20, 10,
                       ports=[("in", 0, 5, "west"), ("out0", 20, 2.5, "east"),
                              ("out1", 20, 7.5, "east")]),
            DeviceSpec("wg1", "strip_waveguide", 100, 0.5,
                       ports=[("in", 0, 0.25, "west"), ("out", 100, 0.25, "east")]),
            DeviceSpec("wg2", "strip_waveguide", 120, 0.5,
                       ports=[("in", 0, 0.25, "west"), ("out", 120, 0.25, "east")]),
            DeviceSpec("mmi2", "mmi_2x2", 20, 10,
                       ports=[("in0", 0, 2.5, "west"), ("in1", 0, 7.5, "west"),
                              ("out0", 20, 2.5, "east"), ("out1", 20, 7.5, "east")]),
        ],
        connections=[
            ("gc1", "out", "mmi1", "in"),
            ("mmi1", "out0", "wg1", "in"),
            ("mmi1", "out1", "wg2", "in"),
            ("wg1", "out", "mmi2", "in0"),
            ("wg2", "out", "mmi2", "in1"),
        ],
    )


def _clements_4x4_circuit() -> CircuitSpec:
    """构造 Clements 4x4 光矩阵电路规格（含端口，供布线使用）。

    6 分束器 + 4 相移器，构成 Clements 三角形拓扑（简化版）。

    来源:
    - Clements et al., "Optimal design for universal multiport interferometers",
      Optica 2016, https://doi.org/10.1364/OPTICA.3.001460

    Returns:
        Clements 4x4 电路规格。
    """
    devices: list[DeviceSpec] = []
    for i in range(6):
        devices.append(DeviceSpec(
            f"bs{i + 1}", "mmi_2x2", 20, 10,
            ports=[("in0", 0, 2.5, "west"), ("in1", 0, 7.5, "west"),
                   ("out0", 20, 2.5, "east"), ("out1", 20, 7.5, "east")],
        ))
    for i in range(4):
        devices.append(DeviceSpec(
            f"ps{i + 1}", "phase_shifter", 10, 5,
            ports=[("in", 0, 2.5, "west"), ("out", 10, 2.5, "east")],
        ))
    connections = [
        ("bs1", "out0", "ps1", "in"),
        ("ps1", "out", "bs3", "in0"),
        ("bs1", "out1", "bs2", "in0"),
        ("bs2", "out0", "ps2", "in"),
        ("ps2", "out", "bs4", "in0"),
        ("bs3", "out1", "bs4", "in1"),
        ("bs4", "out0", "ps3", "in"),
        ("bs2", "out1", "bs5", "in0"),
        ("bs3", "out0", "bs5", "in1"),
        ("bs5", "out0", "ps4", "in"),
    ]
    return CircuitSpec(
        name="Clements4x4",
        canvas_w=800,
        canvas_h=600,
        devices=devices,
        connections=connections,
    )


def _quantum_placeholder_circuit() -> CircuitSpec:
    """构造量子玻色采样占位电路规格（含端口，供布线使用）。

    4 器件占位（实际量子电路在 stage9 处理）：
    2 光栅耦合器（光源）+ 1 分束器 + 1 探测器。

    Returns:
        量子玻色采样占位电路规格。
    """
    return CircuitSpec(
        name="QuantumBosonSampling",
        canvas_w=400,
        canvas_h=300,
        devices=[
            DeviceSpec("src1", "grating_coupler", 10, 10,
                       ports=[("out", 10, 5, "east")]),
            DeviceSpec("src2", "grating_coupler", 10, 10,
                       ports=[("out", 10, 5, "east")]),
            DeviceSpec("bs1", "mmi_2x2", 20, 10,
                       ports=[("in0", 0, 2.5, "west"), ("in1", 0, 7.5, "west"),
                              ("out0", 20, 2.5, "east"), ("out1", 20, 7.5, "east")]),
            DeviceSpec("det1", "detector", 10, 10,
                       ports=[("in", 0, 5, "west")]),
        ],
        connections=[
            ("src1", "out", "bs1", "in0"),
            ("src2", "out", "bs1", "in1"),
            ("bs1", "out0", "det1", "in"),
        ],
    )


def _build_circuits() -> list[CircuitSpec]:
    """构造 3 个演示电路规格。

    Returns:
        电路规格列表（MZI、Clements 4x4、量子占位）。
    """
    return [
        _mzi_circuit(),
        _clements_4x4_circuit(),
        _quantum_placeholder_circuit(),
    ]


def _render_ascii_routing(
    paths: list[dict],
    canvas_w: float,
    canvas_h: float,
    circuit_name: str,
) -> str:
    """渲染路径几何 ASCII 预览。

    将画布坐标映射到 _ASCII_GRID_W × _ASCII_GRID_H 字符网格，
    用字符表示布线路径起止点。

    Args:
        paths: 路径列表（每项含 points 字段）。
        canvas_w: 画布宽度（μm）。
        canvas_h: 画布高度（μm）。
        circuit_name: 电路名称。

    Returns:
        ASCII 布线预览字符串。
    """
    grid: list[list[str]] = [
        ["." for _ in range(_ASCII_GRID_W)] for _ in range(_ASCII_GRID_H)
    ]

    def _to_grid(x: float, y: float) -> tuple[int, int]:
        gx = int(x / canvas_w * _ASCII_GRID_W)
        gy = int(y / canvas_h * _ASCII_GRID_H)
        return (
            max(0, min(_ASCII_GRID_W - 1, gx)),
            max(0, min(_ASCII_GRID_H - 1, gy)),
        )

    for path in paths:
        points = path.get("points", [])
        if len(points) < 2:
            continue
        for pt in points:
            gx, gy = _to_grid(pt[0], pt[1])
            if grid[gy][gx] == ".":
                grid[gy][gx] = "#"
        # 起止点标记为 O
        gx0, gy0 = _to_grid(points[0][0], points[0][1])
        gx1, gy1 = _to_grid(points[-1][0], points[-1][1])
        grid[gy0][gx0] = "O"
        grid[gy1][gx1] = "O"

    lines = ["".join(row) for row in grid]
    legend = "#=路径  O=起止  .=空"
    return (
        f"{circuit_name} 布线预览 ({canvas_w}x{canvas_h} μm):\n"
        + "\n".join(lines)
        + "\n"
        + legend
    )


def _route_one_circuit(circuit: CircuitSpec) -> dict:
    """对单个电路执行智能布线（先布局再布线）。

    使用 polaris-place ``place_circuit`` 获取布局，再用 polaris-route
    ``route_circuit`` 执行曲线波导布线，统计路径数、总损耗、交叉数、弯曲数。

    来源:
    - LiDAR ISPD 2025 curvy-aware routing
      https://dl.acm.org/doi/10.1145/3698364.3705355
    - Klauss et al., Opt Express 2018（Euler spiral bends）
      https://doi.org/10.1364/OE.26.029637

    Args:
        circuit: 电路规格（含端口）。

    Returns:
        电路布线结果 dict，含 name/n_paths/total_loss_db/n_crossings/
        n_bends/ascii_routing。

    Raises:
        RuntimeError: 布局或布线失败（R03 禁止 fall-back）。
    """
    circuit_dict = circuit_to_dict(circuit)
    # 先布局（解析法），再布线
    placement_result = place_circuit(circuit_dict, mode="analytical")
    placements = placement_result["placements"]

    route_result = route_circuit(circuit_dict, placements, mode="curvy")
    paths = route_result["paths"]
    if not paths:
        raise RuntimeError(
            f"电路 {circuit.name} 布线失败：paths 为空"
        )

    ascii_routing = _render_ascii_routing(
        paths,
        circuit.canvas_w,
        circuit.canvas_h,
        circuit.name,
    )

    _logger.info(
        "电路 %s: %d 路径, 损耗=%.2f dB, 交叉=%d, 弯曲=%d",
        circuit.name,
        len(paths),
        route_result["total_loss_db"],
        route_result["n_crossings"],
        route_result["n_bends"],
    )
    _logger.info("ASCII 布线预览:\n%s", ascii_routing)

    return {
        "name": circuit.name,
        "n_paths": len(paths),
        "total_loss_db": round(route_result["total_loss_db"], 2),
        "n_crossings": route_result["n_crossings"],
        "n_bends": route_result["n_bends"],
        "ascii_routing": ascii_routing,
    }


def run(output_dir: Path) -> dict:
    """执行阶段 4: 智能布线。

    流程:
    1. 构造 3 个演示电路（MZI、Clements 4x4、量子占位）
    2. 对每个电路先布局（polaris-place）再布线（polaris-route curvy）
    3. 统计总插入损耗、交叉数、弯曲数
    4. 输出路径几何 ASCII 预览
    5. 返回布线结果摘要

    Args:
        output_dir: 输出目录。

    Returns:
        阶段执行结果，含:
        - circuits: 3 电路布线结果列表
        - router_type: 布线器类型（"curvy"）
    """
    _logger.info("阶段 4 开始: 智能布线（polaris-place + polaris-route）")
    output_dir.mkdir(parents=True, exist_ok=True)

    circuits = _build_circuits()
    results = [_route_one_circuit(circuit) for circuit in circuits]

    _logger.info(
        "阶段 4 完成: %d 电路布线完成, router_type=curvy",
        len(results),
    )

    return {
        "circuits": results,
        "router_type": "curvy",
    }
