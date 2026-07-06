"""PoLaRIS 数据 benchmark 子包（polaris-nn/data）。

提供光子 EDA benchmark（TILOS/Apollo/LiDAR）、数据集生成、GDS/YAML 加载器、
评估器、报告生成器、历史趋势追踪等功能。

== 子模块结构 ==

- ``specs``: CircuitSpec/DeviceSpec/BenchmarkSource/TargetMetric（re-export from polaris_core）
- ``standard_devices``: 标准器件库（MZI/ring/dc/mmi/heater/gc/wg/y_branch）
- ``tilos_benchmark``: TILOS Ariane benchmark（电子芯片对照）
- ``apollo_benchmark``: Apollo PTC/oNoC benchmark（光子芯片对照）
- ``lidar_benchmark``: LiDAR ISPD'25 曲线布线 benchmark
- ``data_loader``: 统一加载器（GDS/YAML/PICBench/PhIDO + benchmark 入口）
- ``gds_loader``: SiEPIC GDS 网表提取
- ``expert_layout``: 专家布局/布线提取（模仿学习用）
- ``dataset_generator``: 训练数据集生成
- ``variant_generator``: 数据集变体生成
- ``benchmark_evaluator``: HPWL/重叠/利用率/拥塞/插入损耗/DRV 评估
- ``benchmark_report``: Markdown/JSON 评估报告生成
- ``benchmark_history``: 历史趋势追踪与回归检测

== 来源（R02 学术诚信，≥5 文献 URL） ==

1. TILOS MacroPlacement: https://github.com/TILOS-AI-Institute/MacroPlacement
2. Apollo PTC/oNoC: https://github.com/ASU-LOPE-Group/Apollo
3. LiDAR ISPD'25: https://dl.acm.org/doi/10.1145/3698364.3705355
4. SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
5. GDSFactory: https://gdsfactory.github.io/gdsfactory/
6. CircuitNet: https://github.com/circuitnet/CircuitNet
7. DREAMPlace: https://arxiv.org/abs/2004.10746
8. gdsfactory ubcpdk: https://github.com/gdsfactory/ubc
"""

from __future__ import annotations

# specs（re-export from polaris_core，避免类型分裂）
from polaris_nn.data.specs import (
    BenchmarkSource,
    CircuitSpec,
    DeviceSpec,
    TargetMetric,
)

# 标准器件
from polaris_nn.data.standard_devices import STANDARD_DEVICES

# benchmark loaders
from polaris_nn.data.apollo_benchmark import (
    load_apollo_onoc_benchmark,
    load_apollo_ptc_benchmark,
)
from polaris_nn.data.lidar_benchmark import (
    load_lidar_onoc_benchmark,
    load_lidar_ptc_benchmark,
)
from polaris_nn.data.tilos_benchmark import load_ariane_benchmark

# 统一加载器
from polaris_nn.data.data_loader import (
    load_apollo_onoc,
    load_apollo_ptc,
    load_lidar_benchmark,
    load_tilos_ariane,
)

# 评估器
from polaris_nn.data.benchmark_evaluator import (
    BenchmarkResult,
    evaluate_benchmark,
    grid_placement,
    placement_by_method,
)

# 报告
from polaris_nn.data.benchmark_report import (
    BenchmarkReport,
    ComparisonReport,
    generate_comparison_report,
    generate_grid_report,
    generate_report,
    run_all_benchmarks,
)

# 历史趋势
from polaris_nn.data.benchmark_history import (
    BenchmarkHistory,
    HistoryEntry,
    HistoryTracker,
    TrendAnalysis,
)

# 数据集生成
from polaris_nn.data.dataset_generator import generate_dataset, generate_layout

__all__ = [
    # specs
    "BenchmarkSource",
    "TargetMetric",
    "DeviceSpec",
    "CircuitSpec",
    # 标准器件
    "STANDARD_DEVICES",
    # benchmark loaders
    "load_ariane_benchmark",
    "load_tilos_ariane",
    "load_apollo_ptc",
    "load_apollo_ptc_benchmark",
    "load_apollo_onoc",
    "load_apollo_onoc_benchmark",
    "load_lidar_benchmark",
    "load_lidar_ptc_benchmark",
    "load_lidar_onoc_benchmark",
    # 评估器
    "BenchmarkResult",
    "evaluate_benchmark",
    "grid_placement",
    "placement_by_method",
    # 报告
    "BenchmarkReport",
    "ComparisonReport",
    "generate_report",
    "generate_grid_report",
    "generate_comparison_report",
    "run_all_benchmarks",
    # 历史趋势
    "BenchmarkHistory",
    "HistoryEntry",
    "HistoryTracker",
    "TrendAnalysis",
    # 数据集生成
    "generate_dataset",
    "generate_layout",
]
