"""阶段 4: 智能布线。

对布局结果执行智能布线，使用弹性连接器与曲线波导（curvy router），
输出波导路径、总插入损耗、交叉数与弯曲数。

对应路标: R17（弹性连接器）/ R19（曲线波导）

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
"""

from __future__ import annotations

import logging
from pathlib import Path

from polaris.data.specs import CircuitSpec, DeviceSpec
from polaris.pipeline.integrated import IntegratedPipeline, PipelineConfig
from polaris.router.path_geometry import count_crossings

_logger = logging.getLogger("e2e_showcase")

# ASCII 布线预览网格尺寸
_ASCII_GRID_W = 40
_ASCII_GRID_H = 15

# 弯曲检测浮点容差
_BEND_TOLERANCE = 1e-9


def _mzi_circuit() -> CircuitSpec:
    """构造 MZI 干涉仪电路规格。

    5 器件：1 光栅耦合器 + 2 MMI + 2 波导臂，构成马赫-曾德干涉仪。

    Returns:
        MZI 电路规格。
    """
    return CircuitSpec(
        name="MZI",
        canvas_w=500,
        canvas_h=300,
        devices=[
            DeviceSpec("gc1", "grating_coupler", 10, 10),
            DeviceSpec("mmi1", "mmi_1x2", 20, 10),
            DeviceSpec(
                "wg1", "strip_waveguide", 100, 0.5,
                params={"length": 100.0},
            ),
            DeviceSpec(
                "wg2", "strip_waveguide", 120, 0.5,
                params={"length": 120.0},
            ),
            DeviceSpec("mmi2", "mmi_2x2", 20, 10),
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
    """构造 Clements 4x4 光矩阵电路规格。

    6 分束器 + 4 相移器，构成 Clements 三角形拓扑（简化版）。

    来源:
    - Clements et al., "Optimal design for universal multiport interferometers",
      Optica 2016, https://doi.org/10.1364/OPTICA.3.001460

    Returns:
        Clements 4x4 电路规格。
    """
    devices: list[DeviceSpec] = []
    for i in range(6):
        devices.append(DeviceSpec(f"bs{i + 1}", "mmi_2x2", 20, 10))
    for i in range(4):
        devices.append(DeviceSpec(f"ps{i + 1}", "phase_shifter", 10, 5))
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
    """构造量子玻色采样占位电路规格。

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
            DeviceSpec("src1", "grating_coupler", 10, 10),
            DeviceSpec("src2", "grating_coupler", 10, 10),
            DeviceSpec("bs1", "mmi_2x2", 20, 10),
            DeviceSpec("det1", "photodetector", 10, 10),
        ],
        connections=[
            ("src1", "out", "bs1", "in0"),
            ("src2", "out", "bs1", "in1"),
            ("bs1", "out0", "det1", "in"),
        ],
    )


def _count_bends(points: list[tuple[float, float]]) -> int:
    """统计路径中的弯曲数（方向改变次数）。

    遍历路径点序列，当中间点的入射方向与出射方向不一致时计为一次弯曲。
    方向由相邻点的位移向量 (dx, dy) 表示。

    来源:
    - LiDAR ISPD 2025, curvy-aware routing
      https://dl.acm.org/doi/10.1145/3698364.3705355
    - 与 polaris.router.path_geometry.path_loss 中的弯曲检测逻辑一致。

    Args:
        points: 路径点序列 [(x, y), ...]。

    Returns:
        弯曲数。
    """
    if len(points) < 3:
        return 0
    bends = 0
    for i in range(1, len(points) - 1):
        dx1 = points[i][0] - points[i - 1][0]
        dy1 = points[i][1] - points[i - 1][1]
        dx2 = points[i + 1][0] - points[i][0]
        dy2 = points[i + 1][1] - points[i][1]
        if abs(dx1 - dx2) > _BEND_TOLERANCE or abs(dy1 - dy2) > _BEND_TOLERANCE:
            bends += 1
    return bends


def _count_total_crossings(paths: dict) -> int:
    """统计所有路径之间的交叉数。

    对所有路径对调用 count_crossings（线段相交检测），累加交叉数。

    来源:
    - polaris.router.path_geometry.count_crossings（CCW 叉积法）
    - SiEPIC EBeam PDK: 单次波导交叉损耗 0.3 dB

    Args:
        paths: 路径字典 {conn_key: [(x, y), ...]}。

    Returns:
        总交叉数。
    """
    path_list = list(paths.values())
    total = 0
    for i in range(len(path_list)):
        for j in range(i + 1, len(path_list)):
            total += count_crossings(path_list[i], path_list[j])
    return total


def _render_ascii_routing(
    paths: dict,
    canvas_w: float,
    canvas_h: float,
    circuit_name: str,
) -> str:
    """渲染路径几何 ASCII 预览。

    将画布坐标映射到 _ASCII_GRID_W × _ASCII_GRID_H 字符网格，
    用字符表示布线路径：
    - `-` = 水平线段
    - `|` = 垂直线段
    - `*` = 弯曲点（方向改变处）
    - `O` = 起止点
    - `.` = 空位置

    Args:
        paths: 路径字典 {conn_key: [(x, y), ...]}。
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

    for points in paths.values():
        if len(points) < 2:
            continue
        # 起止点标记为 O
        gx0, gy0 = _to_grid(points[0][0], points[0][1])
        gx1, gy1 = _to_grid(points[-1][0], points[-1][1])
        grid[gy0][gx0] = "O"
        grid[gy1][gx1] = "O"

        # 遍历中间点，标记线段和弯曲
        for i in range(1, len(points) - 1):
            gx_prev, gy_prev = _to_grid(points[i - 1][0], points[i - 1][1])
            gx_cur, gy_cur = _to_grid(points[i][0], points[i][1])
            gx_next, gy_next = _to_grid(points[i + 1][0], points[i + 1][1])

            # 标记当前点为弯曲或直线段
            dx1 = gx_cur - gx_prev
            dy1 = gy_cur - gy_prev
            dx2 = gx_next - gx_cur
            dy2 = gy_next - gy_cur
            is_bend = dx1 != dx2 or dy1 != dy2

            if is_bend:
                grid[gy_cur][gx_cur] = "*"
            elif dx1 != 0:
                grid[gy_cur][gx_cur] = "-"
            elif dy1 != 0:
                grid[gy_cur][gx_cur] = "|"

            # 填充 prev → cur 之间的线段
            _fill_segment(grid, gx_prev, gy_prev, gx_cur, gy_cur)

        # 填充最后一段 cur → end
        gx_prev, gy_prev = _to_grid(points[-2][0], points[-2][1])
        _fill_segment(grid, gx_prev, gy_prev, gx1, gy1)

    lines = ["".join(row) for row in grid]
    legend = "-=水平  |=垂直  *=弯曲  O=起止  .=空"
    return (
        f"{circuit_name} 布线预览 ({canvas_w}x{canvas_h} μm):\n"
        + "\n".join(lines)
        + "\n"
        + legend
    )


def _fill_segment(
    grid: list[list[str]],
    gx0: int,
    gy0: int,
    gx1: int,
    gy1: int,
) -> None:
    """在网格上填充两点之间的线段字符。

    用 Bresenham 思路沿主轴逐步填充，不覆盖已有的 O/* 标记。

    Args:
        grid: 字符网格（原地修改）。
        gx0: 起点网格 x。
        gy0: 起点网格 y。
        gx1: 终点网格 x。
        gy1: 终点网格 y。
    """
    dx = abs(gx1 - gx0)
    dy = abs(gy1 - gy0)
    sx = 1 if gx0 < gx1 else -1
    sy = 1 if gy0 < gy1 else -1
    x, y = gx0, gy0
    if dx >= dy:
        err = dx / 2.0
        while x != gx1:
            if grid[y][x] == ".":
                grid[y][x] = "-" if dx > 0 else "|"
            err -= dy
            if err < 0:
                y += sy
                err += dx
            x += sx
    else:
        err = dy / 2.0
        while y != gy1:
            if grid[y][x] == ".":
                grid[y][x] = "|" if dy > 0 else "-"
            err -= dx
            if err < 0:
                x += sx
                err += dy
            y += sy


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


def _route_circuit(circuit: CircuitSpec) -> dict:
    """对单个电路执行智能布线。

    使用 IntegratedPipeline（router_type="curvy"）执行布线，
    统计路径数、总损耗、交叉数、弯曲数，并渲染 ASCII 预览。

    Args:
        circuit: 电路规格。

    Returns:
        电路布线结果 dict，含 name/n_paths/total_loss_db/n_crossings/n_bends/ascii_routing。
    """
    config = PipelineConfig(
        canvas_w=circuit.canvas_w,
        canvas_h=circuit.canvas_h,
        router_type="curvy",
    )
    pipeline = IntegratedPipeline(config=config)
    result = pipeline.run(circuit)

    if not result.paths:
        raise RuntimeError(
            f"电路 {circuit.name} 布线失败：paths 为空"
        )

    # 统计弯曲数（所有路径的弯曲数之和）
    n_bends = sum(_count_bends(pts) for pts in result.paths.values())

    # 统计交叉数（所有路径对之间的交叉数之和）
    n_crossings = _count_total_crossings(result.paths)

    ascii_routing = _render_ascii_routing(
        result.paths,
        circuit.canvas_w,
        circuit.canvas_h,
        circuit.name,
    )

    _logger.info(
        "电路 %s: %d 路径, 损耗=%.2f dB, 交叉=%d, 弯曲=%d",
        circuit.name,
        len(result.paths),
        result.total_loss_db,
        n_crossings,
        n_bends,
    )
    _logger.info("ASCII 布线预览:\n%s", ascii_routing)

    return {
        "name": circuit.name,
        "n_paths": len(result.paths),
        "total_loss_db": round(result.total_loss_db, 2),
        "n_crossings": n_crossings,
        "n_bends": n_bends,
        "ascii_routing": ascii_routing,
    }


def run(output_dir: Path) -> dict:
    """执行阶段 4: 智能布线。

    流程:
    1. 构造 3 个演示电路（MZI、Clements 4x4、量子占位）
    2. 对每个电路执行 curvy 布线（弹性连接器 + Euler 曲线波导）
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
    _logger.info("阶段 4 开始: 智能布线")
    output_dir.mkdir(parents=True, exist_ok=True)

    circuits = _build_circuits()
    results = [_route_circuit(circuit) for circuit in circuits]

    _logger.info(
        "阶段 4 完成: %d 电路布线完成, router_type=curvy",
        len(results),
    )

    return {
        "circuits": results,
        "router_type": "curvy",
    }
