"""PoLaRIS 神经网络与数据 benchmark 子模块（polaris-nn）。

== IPO 三段式说明 ==

I（Input，输入）:
    - ``polaris_core.Tensor``: 自动微分张量基类（已在 polaris-core 实现）。
    - ``polaris_core.specs``: CircuitSpec/DeviceSpec/BenchmarkSource/TargetMetric。
    - NumPy ndarray: 纯 NumPy 计算（R04: 不参与 GPU）。

P（Process，处理）:
    - nn 子包: torch.nn 风格的层与优化器（Linear/Conv2d/Attention/
      TransformerBlock/Adam），全部基于 polaris_core.Tensor 自动微分。
    - data 子包: 光子 EDA benchmark（TILOS/Apollo/LiDAR）+ 数据集生成
      + GDS/YAML 加载器 + 评估器 + 报告生成器 + 历史趋势追踪。

O（Output，输出）:
    - nn 层实例: ``Linear``/``Conv2d``/``MultiHeadAttention`` 等。
    - CircuitSpec: 加载的 benchmark 电路规格。
    - BenchmarkResult/BenchmarkReport: 评估结果与报告。
    - 训练数据集: ``generate_dataset()`` 生成的 CircuitSpec 列表。

== 迁移来源 ==

从 v4 旧包 ``src/polaris/nn/``（4 文件）和 ``src/polaris/data/``（17 文件）
迁移，删除旧包依赖（``polaris.data.`` → ``polaris_nn.data.``），
``Tensor`` 统一从 ``polaris_core`` 导入（polaris-core 已含完整自动微分），
``CircuitSpec/DeviceSpec`` 也从 ``polaris_core`` re-export（避免类型分裂）。

== R02 学术诚信（≥5 文献 URL） ==

1. PyTorch torch.nn: https://pytorch.org/docs/stable/nn.html
2. Vaswani et al., 2017, "Attention Is All You Need", NeurIPS
   https://arxiv.org/abs/1706.03762
3. Kingma & Ba, 2015, "Adam: A Method for Stochastic Optimization", ICLR
   https://arxiv.org/abs/1412.6980
4. TILOS MacroPlacement: https://github.com/TILOS-AI-CAD-Institute/MacroPlacement
5. Apollo PTC/oNoC 光子 benchmark: https://github.com/ASU-LOPE-Group/Apollo
6. LiDAR ISPD'25: https://dl.acm.org/doi/10.1145/3698364.3705355
7. DREAMPlace: https://arxiv.org/abs/2004.10746
8. SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK

== 规则依据 ==

- R02 学术诚信: ≥5 文献 URL，所有参数/公式可溯源
- R03 禁止 fall-back: 失败即 raise，无静默兜底
- R04 不参与 GPU: 纯 NumPy/SciPy 实现
- R05 无 TODO/FIXME/HACK 残留
- R13 不保留 v4 兼容: 只保留最新代码
"""

from __future__ import annotations

# nn 子包（神经网络层与优化器）
from polaris_nn.nn import (
    Adam,
    AdamConfig,
    Conv2d,
    Dropout,
    Embedding,
    LayerNorm,
    Linear,
    MaxPool2d,
    Module,
    MultiHeadAttention,
    ReLU,
    ScaledDotProductAttention,
    Sequential,
    Tanh,
    Tensor,
    TransformerBlock,
    cat,
    index_select,
    leaky_relu,
    matmul_backward,
    scatter_add,
    segment_softmax,
)

# data 子包（specs + loaders + evaluators + reports）
from polaris_nn.data.apollo_benchmark import (
    load_apollo_onoc_benchmark,
    load_apollo_ptc_benchmark,
)
from polaris_nn.data.benchmark_evaluator import (
    BenchmarkResult,
    evaluate_benchmark,
    grid_placement,
    placement_by_method,
)
from polaris_nn.data.benchmark_history import (
    BenchmarkHistory,
    HistoryEntry,
    HistoryTracker,
    TrendAnalysis,
)
from polaris_nn.data.benchmark_report import (
    BenchmarkReport,
    ComparisonReport,
    generate_comparison_report,
    generate_grid_report,
    generate_report,
    run_all_benchmarks,
)
from polaris_nn.data.data_loader import (
    load_apollo_onoc,
    load_apollo_ptc,
    load_lidar_benchmark,
    load_tilos_ariane,
)
from polaris_nn.data.dataset_generator import generate_dataset, generate_layout
from polaris_nn.data.lidar_benchmark import (
    load_lidar_onoc_benchmark,
    load_lidar_ptc_benchmark,
)
from polaris_nn.data.specs import (
    BenchmarkSource,
    CircuitSpec,
    DeviceSpec,
    TargetMetric,
)
from polaris_nn.data.standard_devices import STANDARD_DEVICES
from polaris_nn.data.tilos_benchmark import load_ariane_benchmark

__version__ = "5.0.0"

__all__ = [
    "__version__",
    # ── Tensor（re-export from polaris_core） ──
    "Tensor",
    # ── nn: 基础层与容器 ──
    "Module",
    "Linear",
    "ReLU",
    "LayerNorm",
    "Tanh",
    "Sequential",
    # ── nn: 优化器 ──
    "Adam",
    "AdamConfig",
    # ── nn: 卷积/池化/嵌入 ──
    "Conv2d",
    "MaxPool2d",
    "Dropout",
    "Embedding",
    # ── nn: Attention / Transformer ──
    "ScaledDotProductAttention",
    "MultiHeadAttention",
    "TransformerBlock",
    # ── nn: 可微函数 ──
    "cat",
    "scatter_add",
    "index_select",
    "matmul_backward",
    "leaky_relu",
    "segment_softmax",
    # ── data: specs（re-export from polaris_core） ──
    "BenchmarkSource",
    "TargetMetric",
    "DeviceSpec",
    "CircuitSpec",
    # ── data: 标准器件 ──
    "STANDARD_DEVICES",
    # ── data: benchmark loaders ──
    "load_ariane_benchmark",
    "load_tilos_ariane",
    "load_apollo_ptc",
    "load_apollo_ptc_benchmark",
    "load_apollo_onoc",
    "load_apollo_onoc_benchmark",
    "load_lidar_benchmark",
    "load_lidar_ptc_benchmark",
    "load_lidar_onoc_benchmark",
    # ── data: 评估器 ──
    "BenchmarkResult",
    "evaluate_benchmark",
    "grid_placement",
    "placement_by_method",
    # ── data: 报告 ──
    "BenchmarkReport",
    "ComparisonReport",
    "generate_report",
    "generate_grid_report",
    "generate_comparison_report",
    "run_all_benchmarks",
    # ── data: 历史趋势 ──
    "BenchmarkHistory",
    "HistoryEntry",
    "HistoryTracker",
    "TrendAnalysis",
    # ── data: 数据集生成 ──
    "generate_dataset",
    "generate_layout",
]
