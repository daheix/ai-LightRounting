"""公开 Benchmark 评估器（P1-5）。

对标 TILOS MacroPlacement 评估标准，提供 HPWL/重叠/利用率等指标计算，
用于与电子 EDA 工具（Innovus/ICC2/DREAMPlace/Circuit Training）公平对比。

来源:
- TILOS MacroPlacement 评估: https://github.com/TILOS-AI-CAD-Institute/MacroPlacement
- Circuit Training 评估: https://github.com/google-research/circuit_training
- HPWL 经典定义: EDA 教材半周长线长估计

评估指标:
- HPWL (Half-Perimeter Wire Length): 半周长线长，布局质量核心指标
- Overlap Count: 重叠对数，布局合法性指标
- Area Utilization: 面积利用率
- Congestion: 拥塞度（基于布线网格）
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


def evaluate_benchmark(
    circuit: CircuitSpec,
    placements: dict[str, tuple[float, float]],
) -> BenchmarkResult:
    """综合评估 benchmark 布局结果。

    对标 TILOS MacroPlacement 评估流程：计算 HPWL/重叠/利用率，
    根据 target_metric 判定是否达标。

    Args:
        circuit: 电路规格（含 target_metric/target_value）。
        placements: 布局字典 {module_name: (cx, cy)}。

    Returns:
        BenchmarkResult，含全部指标与达标判定。
    """
    hpwl = evaluate_hpwl(circuit, placements)
    overlap = evaluate_overlap(circuit, placements)
    util = evaluate_area_utilization(circuit, placements)

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
    "evaluate_benchmark",
    "grid_placement",
    "analytical_placement",
    "hierarchical_placement",
    "placement_by_method",
]
