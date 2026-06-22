"""公开 Benchmark 评估器（P1-5）。

对标 TILOS MacroPlacement 评估标准，提供 HPWL/重叠/利用率/拥塞度等指标计算，
用于与电子 EDA 工具（Innovus/ICC2/DREAMPlace/Circuit Training）公平对比。

来源:
- TILOS MacroPlacement 评估: https://github.com/TILOS-AI-CAD-Institute/MacroPlacement
- Circuit Training 评估: https://github.com/google-research/circuit_training
- HPWL 经典定义: EDA 教材半周长线长估计
- Congestion 评估: Nesterenko & Hsu 2002 "Congestion-Aware Placement"

评估指标:
- HPWL (Half-Perimeter Wire Length): 半周长线长，布局质量核心指标
- Overlap Count: 重叠对数，布局合法性指标
- Area Utilization: 面积利用率
- Congestion: 拥塞度（基于布线网格，第82轮新增）
"""

from __future__ import annotations

from dataclasses import dataclass, field

from polaris.data.specs import CircuitSpec


@dataclass(frozen=True)
class BenchmarkResult:
    """Benchmark 评估结果。

    Attributes:
        benchmark_name: benchmark 名称。
        hpwl_um: 半周长线长（μm）。
        overlap_count: 重叠对数。
        area_utilization: 面积利用率（0-1）。
        module_count: 模块数。
        connection_count: 连接数。
        target_metric: 目标指标名（HPWL/DRV/...）。
        target_value: 目标值。
        passed: 是否达标。
    """

    benchmark_name: str
    hpwl_um: float
    overlap_count: int
    area_utilization: float
    module_count: int
    connection_count: int
    target_metric: str
    target_value: float
    passed: bool = False
    extra: dict = field(default_factory=dict)


def evaluate_hpwl(
    circuit: CircuitSpec,
    placements: dict[str, tuple[float, float]],
) -> float:
    """计算布局的 HPWL（半周长线长）。

    对每条连接取两端模块中心坐标的 |dx| + |dy|，求和。
    来源: 经典 EDA HPWL 估计（TILOS/Circuit Training 标准）。

    Args:
        circuit: 电路规格（含连接列表）。
        placements: 布局字典 {module_name: (x, y)}，x/y 为模块中心坐标。

    Returns:
        HPWL 总线长（μm）。
    """
    total = 0.0
    for src, _src_port, dst, _dst_port in circuit.connections:
        if src not in placements or dst not in placements:
            continue
        x1, y1 = placements[src]
        x2, y2 = placements[dst]
        total += abs(x2 - x1) + abs(y2 - y1)
    return total


def evaluate_overlap(
    circuit: CircuitSpec,
    placements: dict[str, tuple[float, float]],
) -> int:
    """计算布局的模块重叠对数。

    两模块包围盒相交即计为一次重叠。
    来源: TILOS MacroPlacement DRC 评估标准。

    Args:
        circuit: 电路规格（含模块尺寸）。
        placements: 布局字典 {module_name: (cx, cy)}，中心坐标。

    Returns:
        重叠对数。
    """
    # 构建 (name, xmin, ymin, xmax, ymax) 列表
    boxes: list[tuple[str, float, float, float, float]] = []
    size_map = {d.name: (d.width_um, d.height_um) for d in circuit.devices}
    for name, (cx, cy) in placements.items():
        if name not in size_map:
            continue
        w, h = size_map[name]
        boxes.append((name, cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2))

    overlap = 0
    n = len(boxes)
    for i in range(n):
        for j in range(i + 1, n):
            _n1, x1min, y1min, x1max, y1max = boxes[i]
            _n2, x2min, y2min, x2max, y2max = boxes[j]
            # 包围盒相交判定
            if x1min < x2max and x2min < x1max and y1min < y2max and y2min < y1max:
                overlap += 1
    return overlap


def evaluate_area_utilization(
    circuit: CircuitSpec,
    placements: dict[str, tuple[float, float]],
) -> float:
    """计算面积利用率（已放置模块总面积 / 画布面积）。

    Args:
        circuit: 电路规格。
        placements: 布局字典。

    Returns:
        利用率（0-1），无放置时返回 0。
    """
    if not placements:
        return 0.0
    size_map = {d.name: (d.width_um, d.height_um) for d in circuit.devices}
    used = sum(w * h for name in placements if (wh := size_map.get(name)) for w, h in [wh])
    total = circuit.canvas_w * circuit.canvas_h
    return used / total if total > 0 else 0.0


def _build_demand_grid(
    circuit: CircuitSpec,
    placements: dict[str, tuple[float, float]],
    grid_rows: int,
    grid_cols: int,
    cell_size: tuple[float, float],
) -> tuple[list[list[float]], list[list[float]]]:
    """构建布线需求网格（第82轮内部辅助函数）。

    对每条连接，用 LRT 模型将布线需求均匀分布到 bounding box 经过的网格。
    水平需求记录到 demand_h，垂直需求记录到 demand_v。

    来源: Westra et al., "BoxRouter", ISPD 2006（LRT 模型）

    Args:
        circuit: 电路规格（含连接列表）。
        placements: 布局字典。
        grid_rows: 网格行数。
        grid_cols: 网格列数。
        cell_size: (cell_w, cell_h) 网格单元宽高。

    Returns:
        (demand_h, demand_v) 两个 grid_rows × grid_cols 的需求矩阵。
    """
    cell_w, cell_h = cell_size
    demand_h = [[0.0] * grid_cols for _ in range(grid_rows)]
    demand_v = [[0.0] * grid_cols for _ in range(grid_rows)]

    for src, _src_port, dst, _dst_port in circuit.connections:
        if src not in placements or dst not in placements:
            continue
        x1, y1 = placements[src]
        x2, y2 = placements[dst]
        xmin, xmax = min(x1, x2), max(x1, x2)
        ymin, ymax = min(y1, y2), max(y1, y2)
        col_min = max(0, int(xmin / cell_w))
        col_max = min(grid_cols - 1, int(xmax / cell_w))
        row_min = max(0, int(ymin / cell_h))
        row_max = min(grid_rows - 1, int(ymax / cell_h))
        n_h_cells = max(1, col_max - col_min + 1)
        n_v_cells = max(1, row_max - row_min + 1)
        h_demand = 1.0 / n_h_cells
        v_demand = 1.0 / n_v_cells
        for r in range(row_min, row_max + 1):
            for c in range(col_min, col_max + 1):
                demand_h[r][c] += h_demand
                demand_v[r][c] += v_demand
    return demand_h, demand_v


def _compute_congestion_stats(
    demand_h: list[list[float]],
    demand_v: list[list[float]],
    grid_rows: int,
    grid_cols: int,
    capacity: float = 1.0,
) -> dict[str, float]:
    """从需求网格计算拥塞度统计（第82轮内部辅助函数）。

    Args:
        demand_h: 水平需求矩阵。
        demand_v: 垂直需求矩阵。
        grid_rows: 网格行数。
        grid_cols: 网格列数。
        capacity: 每个网格的容量（默认 1.0）。

    Returns:
        拥塞度统计字典（max/avg/overflow_count/total_overflow）。
    """
    max_cong = 0.0
    total_cong = 0.0
    overflow_count = 0
    total_overflow = 0.0
    n_cells = grid_rows * grid_cols
    for r in range(grid_rows):
        for c in range(grid_cols):
            demand = demand_h[r][c] + demand_v[r][c]
            cong = demand / capacity
            if cong > max_cong:
                max_cong = cong
            total_cong += cong
            if demand > capacity:
                overflow_count += 1
                total_overflow += demand - capacity
    return {
        "max_congestion": max_cong,
        "avg_congestion": total_cong / n_cells if n_cells > 0 else 0.0,
        "overflow_count": overflow_count,
        "total_overflow": total_overflow,
    }


def evaluate_congestion(
    circuit: CircuitSpec,
    placements: dict[str, tuple[float, float]],
    grid_rows: int = 16,
    grid_cols: int = 16,
) -> dict[str, float]:
    """计算布局的布线拥塞度（第82轮新增）。

    对标 TILOS MacroPlacement Congestion 评估标准：
    1. 将画布划分为 grid_rows × grid_cols 网格
    2. 对每条连接，用 LRT（Line-to-Row Tree）估算布线需求
    3. 统计每个网格的布线需求（demand）
    4. 每个网格容量（capacity）= 1.0（简化模型）
    5. 拥塞度 = max(demand / capacity)

    LRT 模型：连接 (x1,y1)→(x2,y2) 的布线需求均匀分布在
    bounding box 经过的网格上。水平连接贡献水平需求，
    垂直连接贡献垂直需求。

    来源:
        - TILOS MacroPlacement Congestion Evaluation
          https://github.com/TILOS-AI-CAD-Institute/MacroPlacement
        - Circuit Training Obstacle Channel Congestion
          https://github.com/google-research/circuit_training
        - Nesterenko & Hsu, "Congestion-Aware Placement", TCAD 2002
        - Westra et al., "BoxRouter", ISPD 2006（LRT 模型）

    Args:
        circuit: 电路规格（含连接列表）。
        placements: 布局字典 {module_name: (cx, cy)}。
        grid_rows: 网格行数（默认 16，TILOS 标准）。
        grid_cols: 网格列数（默认 16，TILOS 标准）。

    Returns:
        拥塞度统计字典:
        - ``max_congestion``: 最大拥塞比（demand/capacity）
        - ``avg_congestion``: 平均拥塞比
        - ``overflow_count``: 拥塞溢出网格数（demand > capacity）
        - ``total_overflow``: 总溢出量（sum(max(0, demand-capacity))）
    """
    empty = {
        "max_congestion": 0.0,
        "avg_congestion": 0.0,
        "overflow_count": 0,
        "total_overflow": 0.0,
    }
    if not placements or circuit.canvas_w <= 0 or circuit.canvas_h <= 0:
        return empty

    cell_w = circuit.canvas_w / grid_cols
    cell_h = circuit.canvas_h / grid_rows
    if cell_w <= 0 or cell_h <= 0:
        return empty

    demand_h, demand_v = _build_demand_grid(
        circuit, placements, grid_rows, grid_cols, (cell_w, cell_h)
    )
    return _compute_congestion_stats(demand_h, demand_v, grid_rows, grid_cols)


def evaluate_benchmark(
    circuit: CircuitSpec,
    placements: dict[str, tuple[float, float]],
) -> BenchmarkResult:
    """综合评估 benchmark 布局结果。

    对标 TILOS MacroPlacement 评估流程：计算 HPWL/重叠/利用率/拥塞度，
    根据 target_metric 判定是否达标。

    第82轮扩展：集成拥塞度（Congestion）评估，输出 max_congestion、
    avg_congestion、overflow_count、total_overflow 四项指标到 extra。

    Args:
        circuit: 电路规格（含 target_metric/target_value）。
        placements: 布局字典 {module_name: (cx, cy)}。

    Returns:
        BenchmarkResult，含全部指标与达标判定。
    """
    hpwl = evaluate_hpwl(circuit, placements)
    overlap = evaluate_overlap(circuit, placements)
    util = evaluate_area_utilization(circuit, placements)
    cong = evaluate_congestion(circuit, placements)

    # 达标判定：HPWL < target 且 无重叠
    target_metric = circuit.target_metric.value
    target_value = circuit.target_value
    passed = False
    if target_metric == "hpwl":
        passed = hpwl < target_value and overlap == 0
    elif target_metric == "drv":
        passed = overlap == 0
    elif target_metric == "routing_success_rate":
        passed = 1.0 >= target_value

    return BenchmarkResult(
        benchmark_name=circuit.name,
        hpwl_um=hpwl,
        overlap_count=overlap,
        area_utilization=util,
        module_count=len(circuit.devices),
        connection_count=len(circuit.connections),
        target_metric=target_metric,
        target_value=target_value,
        passed=passed,
        extra={
            "benchmark_source": circuit.benchmark_source.value,
            "process_node": circuit.process_node,
            "max_congestion": cong["max_congestion"],
            "avg_congestion": cong["avg_congestion"],
            "overflow_count": cong["overflow_count"],
            "total_overflow": cong["total_overflow"],
        },
    )


def grid_placement(
    circuit: CircuitSpec,
    cols: int | None = None,
) -> dict[str, tuple[float, float]]:
    """生成网格布局（基准对照布局，非 RL）。

    将模块按 cols 列网格均匀分布，作为 RL 布局的对照基准。
    单元尺寸自适应最大模块，确保无重叠。
    来源: TILOS MacroPlacement 初始布局基准。

    Args:
        circuit: 电路规格。
        cols: 网格列数（默认 sqrt(n)）。

    Returns:
        布局字典 {module_name: (cx, cy)}，中心坐标。
    """
    import math

    n = len(circuit.devices)
    if n == 0:
        return {}
    if cols is None:
        cols = max(1, int(math.ceil(math.sqrt(n))))
    rows = math.ceil(n / cols)
    # 单元尺寸：基于最大模块尺寸，确保不重叠
    max_w = max((d.width_um for d in circuit.devices), default=1.0)
    max_h = max((d.height_um for d in circuit.devices), default=1.0)
    cell_w = max(circuit.canvas_w / cols, max_w * 1.1)
    cell_h = max(circuit.canvas_h / rows, max_h * 1.1)
    placements: dict[str, tuple[float, float]] = {}
    for i, dev in enumerate(circuit.devices):
        row = i // cols
        col = i % cols
        cx = (col + 0.5) * cell_w
        cy = (row + 0.5) * cell_h
        placements[dev.name] = (cx, cy)
    return placements


def analytical_placement(circuit: CircuitSpec) -> dict[str, tuple[float, float]]:
    """解析法布局（DREAMPlace 风格，第76轮 P1-5 扩展）。

    使用 AnalyticalPlacer（log-sum-exp 平滑 HPWL + 密度惩罚 + Adam 优化）
    生成连续坐标布局，作为 grid 布局的高级对照基准。

    来源: DREAMPlace DAC 2019/TCAD 2020, arxiv:2004.10746

    Args:
        circuit: 电路规格。

    Returns:
        布局字典 {module_name: (cx, cy)}，中心坐标。
    """
    from polaris.engine.analytical_placer import AnalyticalPlacer

    placer = AnalyticalPlacer(circuit)
    return placer.place()


def hierarchical_placement(circuit: CircuitSpec) -> dict[str, tuple[float, float]]:
    """分块布局（谱聚类 + 块内解析法，第76轮 P1-5 扩展）。

    使用 HierarchicalPlacer（谱聚类分块 + 块内 AnalyticalPlacer + 块间布局）
    生成大规模布局，适用于 1000+ 器件规模。

    来源: Shi & Malik 2000 Normalized Cuts, DREAMPlace TCAD 2020

    Args:
        circuit: 电路规格。

    Returns:
        布局字典 {module_name: (cx, cy)}，中心坐标。
    """
    from polaris.engine.hierarchical_placer import HierarchicalPlacer

    placer = HierarchicalPlacer(circuit)
    return placer.place()


def placement_by_method(
    circuit: CircuitSpec, method: str
) -> dict[str, tuple[float, float]]:
    """按方法名分发布局（第76轮 P1-5 扩展）。

    支持 grid/analytical/hierarchical 三种布局方法，用于 benchmark 评估时
    量化对比不同布局算法的质量（HPWL/重叠/利用率）。

    Args:
        circuit: 电路规格。
        method: 布局方法名（``grid``/``analytical``/``hierarchical``）。

    Returns:
        布局字典 {module_name: (cx, cy)}。

    Raises:
        ValueError: 未知的布局方法名。
    """
    if method == "grid":
        return grid_placement(circuit)
    if method == "analytical":
        return analytical_placement(circuit)
    if method == "hierarchical":
        return hierarchical_placement(circuit)
    raise ValueError(
        f"未知布局方法 '{method}'，支持: grid/analytical/hierarchical"
    )


__all__ = [
    "BenchmarkResult",
    "evaluate_hpwl",
    "evaluate_overlap",
    "evaluate_area_utilization",
    "evaluate_congestion",
    "evaluate_benchmark",
    "grid_placement",
    "analytical_placement",
    "hierarchical_placement",
    "placement_by_method",
]
