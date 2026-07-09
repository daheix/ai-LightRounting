"""公开 Benchmark 评估器（P1-5）。

对标 TILOS MacroPlacement 评估标准，提供 HPWL/重叠/利用率/拥塞度等指标计算，
用于与电子 EDA 工具（Innovus/ICC2/DREAMPlace/Circuit Training）公平对比。

R03 异常处理设计: 缺失 placements 坐标或 circuit.devices 中无对应模块时
raise KeyError，禁止静默跳过（会导致 HPWL/重叠/拥塞度/插入损耗/DRV 计算不准）。

来源:
- TILOS MacroPlacement 评估: https://github.com/TILOS-AI-Institute/MacroPlacement
- Circuit Training 评估: https://github.com/google-research/circuit_training
- DREAMPlace: https://github.com/limbo018/DREAMPlace
- HPWL 经典定义: EDA 教材半周长线长估计
- Congestion 评估: Nesterenko & Hsu 2002 "Congestion-Aware Placement"
- Insertion Loss: 光子电路插入损耗 = 波导损耗 + 器件损耗

异常处理文献:
- Python 异常处理: https://docs.python.org/3/tutorial/errors.html
- PEP 8 异常设计: https://peps.python.org/pep-0008/#exception-handling

评估指标:
- HPWL (Half-Perimeter Wire Length): 半周长线长，布局质量核心指标
- Overlap Count: 重叠对数，布局合法性指标
- Area Utilization: 面积利用率
- Congestion: 拥塞度（基于布线网格，第82轮新增）
- Insertion Loss: 光子插入损耗（dB，第90轮新增）
- DRV: 设计规则违规数（重叠+间距+边界，第94轮新增）
"""

from __future__ import annotations

from dataclasses import dataclass, field

from polaris_nn.data.specs import CircuitSpec


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
            # R03: 缺失布局坐标，禁止静默跳过（会导致 HPWL 计算不准）
            raise KeyError(
                f"HPWL 评估: 连接 {src}→{dst} 的模块缺失 placements "
                f"(src_in={src in placements}, dst_in={dst in placements})"
            )
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
            # R03: placements 中的模块不在 circuit.devices 中，禁止静默跳过
            raise KeyError(
                f"重叠评估: placements 中的模块 '{name}' 不在 circuit.devices 中"
            )
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
            # R03: 缺失布局坐标，禁止静默跳过（会导致拥塞度计算不准）
            raise KeyError(
                f"拥塞度评估: 连接 {src}→{dst} 的模块缺失 placements "
                f"(src_in={src in placements}, dst_in={dst in placements})"
            )
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
          https://github.com/TILOS-AI-Institute/MacroPlacement
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


# 默认波导损耗（dB/cm），用于 INSERTION_LOSS_DB 评估
# R05 Bug 修复 v4.0-SOI-LOSS-P1（第2轮迭代发现）:
# 原注释"SOI 220nm 平台典型值 1.0 dB/cm"误导（实为 GF_Fotonix/Tower 特定值，
# 非 SOI 平台典型），且与项目 7 处 3.0 dB/cm 不一致。统一为 3.0 dB/cm
# （Soref 1993 + SiEPIC EBeam PDK 上界）。
# 规则: R02 学术诚信 / R05 Bug 必修
# 文献:
# - Soref et al. 1993 IEEE Proc. 41(9) 1182-1183
#   https://ieeexplore.ieee.org/document/1148303
# - Vlasov & McNab 2004 Opt. Express 12(8) 1622-1631
#   https://www.opticsexpress.org/abstract.cfm?uri=oe-12-8-1622
# - SiEPIC EBeam PDK https://github.com/SiEPIC/SiEPIC_EBeam_PDK
_DEFAULT_WAVEGUIDE_LOSS_DB_CM = 3.0


def evaluate_insertion_loss(
    circuit: CircuitSpec,
    placements: dict[str, tuple[float, float]],
    waveguide_loss_db_cm: float = _DEFAULT_WAVEGUIDE_LOSS_DB_CM,
) -> float:
    """计算光子电路总插入损耗（dB）。

    总插入损耗 = 波导传输损耗 + 器件插入损耗

    公式来源: 光子集成电路设计标准（Lumerical/Luceda 评估方法）
    - 波导损耗 = 波导长度(μm) × 波导损耗系数(dB/cm) / 10000
    - 器件损耗 = sum(device.params["insertion_loss_db"])

    波导长度用连接两端模块的曼哈顿距离近似（与 HPWL 相同的估计方法）。

    Args:
        circuit: 电路规格（含连接列表和器件参数）。
        placements: 布局字典 {module_name: (x, y)}。
        waveguide_loss_db_cm: 波导损耗系数（dB/cm），默认 3.0（SOI 上界，Soref 1993 + SiEPIC PDK）。

    Returns:
        总插入损耗（dB）。
    """
    # 1. 波导传输损耗
    waveguide_loss = 0.0
    for src, _src_port, dst, _dst_port in circuit.connections:
        if src not in placements or dst not in placements:
            # R03: 缺失布局坐标，禁止静默跳过（会导致插入损耗计算不准）
            raise KeyError(
                f"插入损耗评估: 连接 {src}→{dst} 的模块缺失 placements "
                f"(src_in={src in placements}, dst_in={dst in placements})"
            )
        x1, y1 = placements[src]
        x2, y2 = placements[dst]
        length_um = abs(x2 - x1) + abs(y2 - y1)
        waveguide_loss += length_um * waveguide_loss_db_cm / 10000.0  # μm → cm

    # 2. 器件插入损耗
    device_loss = 0.0
    for dev in circuit.devices:
        if "insertion_loss_db" in dev.params:
            device_loss += float(dev.params["insertion_loss_db"])

    return waveguide_loss + device_loss


def _build_drv_boxes_and_boundary(
    circuit: CircuitSpec,
    placements: dict[str, tuple[float, float]],
) -> tuple[list[tuple[str, float, float, float, float]], int]:
    """构建 DRV 评估用的包围盒列表并检测边界违规（Extract Method）。

    Args:
        circuit: 电路规格（含模块尺寸和画布尺寸）。
        placements: 布局字典。

    Returns:
        (boxes, boundary_violations)。boxes 为 (name, xmin, ymin, xmax, ymax) 列表。

    Raises:
        KeyError: placements 中的模块不在 circuit.devices 中（R03）。
    """
    size_map = {d.name: (d.width_um, d.height_um) for d in circuit.devices}
    boundary_violations = 0
    boxes: list[tuple[str, float, float, float, float]] = []
    for name, (cx, cy) in placements.items():
        if name not in size_map:
            # R03: placements 中的模块不在 circuit.devices 中，禁止静默跳过
            raise KeyError(
                f"DRV 评估: placements 中的模块 '{name}' 不在 circuit.devices 中"
            )
        w, h = size_map[name]
        xmin = cx - w / 2
        ymin = cy - h / 2
        xmax = cx + w / 2
        ymax = cy + h / 2
        boxes.append((name, xmin, ymin, xmax, ymax))
        # 边界违规：模块超出画布
        if xmin < 0 or ymin < 0 or xmax > circuit.canvas_w or ymax > circuit.canvas_h:
            boundary_violations += 1
    return boxes, boundary_violations


def _count_overlap_and_spacing(
    boxes: list[tuple[str, float, float, float, float]],
    min_spacing_um: float,
) -> tuple[int, int]:
    """统计重叠违规与间距违规数（Extract Method）。

    Args:
        boxes: (name, xmin, ymin, xmax, ymax) 包围盒列表。
        min_spacing_um: 最小间距（μm），<=0 时仅检测重叠。

    Returns:
        (overlap_violations, spacing_violations)。间距违规不含重叠对。
    """
    overlap_violations = 0
    spacing_violations = 0
    n = len(boxes)
    for i in range(n):
        for j in range(i + 1, n):
            _n1, x1min, y1min, x1max, y1max = boxes[i]
            _n2, x2min, y2min, x2max, y2max = boxes[j]
            # 重叠判定：包围盒相交
            if x1min < x2max and x2min < x1max and y1min < y2max and y2min < y1max:
                overlap_violations += 1
                continue
            # 间距违规判定：间距 < min_spacing_um（仅在非重叠时检查）
            if min_spacing_um <= 0:
                continue
            dx = max(0, max(x1min, x2min) - min(x1max, x2max))
            dy = max(0, max(y1min, y2min) - min(y1max, y2max))
            dist = (dx * dx + dy * dy) ** 0.5
            if dist < min_spacing_um:
                spacing_violations += 1
    return overlap_violations, spacing_violations


def evaluate_drv(
    circuit: CircuitSpec,
    placements: dict[str, tuple[float, float]],
    min_spacing_um: float = 0.0,
) -> dict[str, int]:
    """计算设计规则违规数（DRV）。

    对标 TILOS MacroPlacement DRV 评估标准与商业 EDA 工具（Innovus/ICC2）的
    DRV 计数方法，包含三类违规：

    1. **重叠违规（overlap_violations）**: 两模块包围盒相交
    2. **间距违规（spacing_violations）**: 两模块间距 < min_spacing_um
       （min_spacing_um=0 时退化为仅检测重叠）
    3. **边界违规（boundary_violations）**: 模块超出画布边界

    来源:
        - TILOS MacroPlacement DRV Evaluation
          https://github.com/TILOS-AI-Institute/MacroPlacement
        - Cadence Innovus DRV 计数（spacing/width/area/short）
        - DREAMPlace Overlap/Boundary 违规检测
        - Fowler, "Refactoring" 2nd ed., 2018, Extract Method
          https://martinfowler.com/books/refactoring.html

    Args:
        circuit: 电路规格（含模块尺寸和画布尺寸）。
        placements: 布局字典 {module_name: (cx, cy)}，中心坐标。
        min_spacing_um: 最小间距（μm），默认 0（仅检测重叠）。

    Returns:
        DRV 统计字典:
        - ``overlap_violations``: 重叠违规数
        - ``spacing_violations``: 间距违规数（不含重叠）
        - ``boundary_violations``: 边界违规数
        - ``total``: 总 DRV 数
    """
    # 1. 构建 boxes 并检测边界违规
    boxes, boundary_violations = _build_drv_boxes_and_boundary(circuit, placements)

    # 2. 重叠与间距违规检测
    overlap_violations, spacing_violations = _count_overlap_and_spacing(
        boxes, min_spacing_um
    )

    return {
        "overlap_violations": overlap_violations,
        "spacing_violations": spacing_violations,
        "boundary_violations": boundary_violations,
        "total": overlap_violations + spacing_violations + boundary_violations,
    }


def evaluate_benchmark(
    circuit: CircuitSpec,
    placements: dict[str, tuple[float, float]],
) -> BenchmarkResult:
    """综合评估 benchmark 布局结果。

    对标 TILOS MacroPlacement 评估流程：计算 HPWL/重叠/利用率/拥塞度/插入损耗，
    根据 target_metric 判定是否达标。

    第82轮扩展：集成拥塞度（Congestion）评估，输出 max_congestion、
    avg_congestion、overflow_count、total_overflow 四项指标到 extra。

    第90轮扩展：集成插入损耗（Insertion Loss）评估，修复 insertion_loss_db
    达标判定（Apollo benchmark 不再静默失败）。

    第94轮扩展：集成 DRV 评估，使用真正的 DRV 计数（重叠+间距+边界），
    替代原先仅检测重叠的简化判定。DRV target_value 表示允许的最大违规数。

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
    insertion_loss = evaluate_insertion_loss(circuit, placements)
    drv = evaluate_drv(circuit, placements)

    # 达标判定：根据 target_metric 判定是否达标
    target_metric = circuit.target_metric.value
    target_value = circuit.target_value
    passed = False
    if target_metric == "hpwl":
        passed = hpwl < target_value and drv["total"] == 0
    elif target_metric == "drv":
        # DRV 达标：总违规数 <= target_value（target_value=0 表示零违规）
        passed = drv["total"] <= target_value
    elif target_metric == "routing_success_rate":
        # 布线成功率：DRV=0 时视为可布线（布局合法是布线成功的前提）
        passed = drv["total"] == 0
    elif target_metric == "insertion_loss_db":
        # 插入损耗达标：总损耗 < target_value 且无 DRV 违规
        passed = insertion_loss < target_value and drv["total"] == 0

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
            "insertion_loss_db": insertion_loss,
            "drv_total": drv["total"],
            "drv_overlap": drv["overlap_violations"],
            "drv_spacing": drv["spacing_violations"],
            "drv_boundary": drv["boundary_violations"],
        },
    )


def grid_placement(
    circuit: CircuitSpec,
    cols: int | None = None,
) -> dict[str, tuple[float, float]]:
    """生成网格布局（基准对照布局，非 RL）。

    将模块按 cols 列网格均匀分布，作为 RL 布局的对照基准。
    单元尺寸自适应最大模块，确保无重叠且零边界违规。

    修复: 当最大模块尺寸 × 1.1 > 画布分割尺寸时，原实现 cell_w 会超过
    canvas_w/cols，导致器件超出画布边界（DRV boundary 违规）。
    现改为: 计算能容纳所有模块（含 10% 间距余量）的最小画布尺寸，
    若原画布不够则自适应扩大，确保所有模块严格在画布内。

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
    # 最大模块尺寸
    max_w = max((d.width_um for d in circuit.devices), default=1.0)
    max_h = max((d.height_um for d in circuit.devices), default=1.0)
    # 能容纳所有模块（含 10% 间距余量）的最小画布尺寸
    min_canvas_w = cols * max_w * 1.1
    min_canvas_h = rows * max_h * 1.1
    # 自适应扩大画布: 若原画布不够则直接修改 circuit 画布尺寸
    # （CircuitSpec 非 frozen，可修改；确保 evaluate_drv 等下游评估
    #   使用与布局一致的画布尺寸，避免边界违规误报）
    if circuit.canvas_w < min_canvas_w:
        circuit.canvas_w = min_canvas_w
    if circuit.canvas_h < min_canvas_h:
        circuit.canvas_h = min_canvas_h
    # 单元尺寸: 严格按扩大后的画布分割（确保不超出画布）
    cell_w = circuit.canvas_w / cols
    cell_h = circuit.canvas_h / rows
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

    polaris-nn 子模块不含布局引擎（AnalyticalPlacer 在 polaris 完整包的
    ``polaris.engine.analytical_placer`` 中）。本函数仅作为占位 API 保留，
    调用时显式 raise RuntimeError，禁止静默 fall-back（R03）。

    用户需在 polaris 完整包中调用 ``AnalyticalPlacer(circuit).place()``。

    来源: DREAMPlace DAC 2019/TCAD 2020, arxiv:2004.10746

    Args:
        circuit: 电路规格。

    Raises:
        RuntimeError: polaris-nn 子模块不带 analytical 布局引擎。
    """
    raise RuntimeError(
        "analytical_placement 需要 polaris 完整包的 AnalyticalPlacer "
        "（polaris.engine.analytical_placer），polaris-nn 子模块不含布局引擎。"
        " 请安装完整 polaris 包后直接调用 AnalyticalPlacer(circuit).place()。"
    )


def hierarchical_placement(circuit: CircuitSpec) -> dict[str, tuple[float, float]]:
    """分块布局（谱聚类 + 块内解析法，第76轮 P1-5 扩展）。

    polaris-nn 子模块不含布局引擎（HierarchicalPlacer 在 polaris 完整包的
    ``polaris.engine.hierarchical_placer`` 中）。本函数仅作为占位 API 保留，
    调用时显式 raise RuntimeError，禁止静默 fall-back（R03）。

    用户需在 polaris 完整包中调用 ``HierarchicalPlacer(circuit).place()``。

    来源: Shi & Malik 2000 Normalized Cuts, DREAMPlace TCAD 2020

    Args:
        circuit: 电路规格。

    Raises:
        RuntimeError: polaris-nn 子模块不带 hierarchical 布局引擎。
    """
    raise RuntimeError(
        "hierarchical_placement 需要 polaris 完整包的 HierarchicalPlacer "
        "（polaris.engine.hierarchical_placer），polaris-nn 子模块不含布局引擎。"
        " 请安装完整 polaris 包后直接调用 HierarchicalPlacer(circuit).place()。"
    )


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
    "evaluate_insertion_loss",
    "evaluate_drv",
    "evaluate_benchmark",
    "grid_placement",
    "analytical_placement",
    "hierarchical_placement",
    "placement_by_method",
]
