"""PoLaRIS 核心规格数据类（polaris-core 子模块）。

从 src/polaris/data/specs.py 迁移，作为 polaris-core 内部使用的数据结构。
对外稳定 API（make_device/make_circuit）返回 JSON-serializable dict，不暴露
dataclass，避免内部对象泄漏（稳定 API 原则）。

设计原则:
- dataclass 仅内部使用（构建/校验）
- 对外 API 用 dict（JSON-serializable，可跨语言传递）
- 禁止 fall-back（R03）：构造失败 raise

来源:
- GDSFactory 组件库: https://gdsfactory.github.io/gdsfactory/
- TILOS MacroPlacement benchmark: https://github.com/TILOS-AI-CAD-Institute/MacroPlacement
- Apollo PTC/oNoC 光子 benchmark: https://github.com/ASU-LOPE-Group/Apollo
- LiDAR ISPD'25 benchmark: https://dl.acm.org/doi/pdf/10.1145/3698364.3705355
- SiEPIC PDK 设计规则: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class BenchmarkSource(Enum):
    """Benchmark 来源标识（差距分析 P1-5，对标公开 benchmark）。

    来源:
    - TILOS: https://github.com/TILOS-AI-CAD-Institute/MacroPlacement
    - Apollo: https://github.com/ASU-LOPE-Group/Apollo
    - LiDAR: https://dl.acm.org/doi/pdf/10.1145/3698364.3705355
    - CUSTOM: PoLaRIS 自有 benchmark
    """

    TILOS = "tilos"  # TILOS Ariane/MemPool/NVDLA（电子芯片对照）
    APOLLO = "apollo"  # Apollo PTC/oNoC（光子芯片对照）
    LIDAR = "lidar"  # LiDAR ISPD'25（光子曲线布线对照）
    CUSTOM = "custom"  # PoLaRIS 自有 benchmark


class TargetMetric(Enum):
    """Benchmark 评估指标（对标商业 EDA PPA 评估）。

    来源:
    - HPWL: 半周长线长，电子 EDA 标准布局指标
    - DRV: 设计规则违规数，DRC 质量指标
    - ROUTING_SUCCESS_RATE: 布线成功率
    - INSERTION_LOSS_DB: 光子特有指标，总插入损耗
    """

    HPWL = "hpwl"  # 半周长线长（μm）
    DRV = "drv"  # 设计规则违规数
    ROUTING_SUCCESS_RATE = "routing_success_rate"  # 布线成功率（0-1）
    INSERTION_LOSS_DB = "insertion_loss_db"  # 插入损耗（dB）


@dataclass
class DeviceSpec:
    """器件规格（内部 dataclass，对外 API 用 dict）。

    Attributes:
        name: 器件名称。
        device_type: 器件类型（mzi/ring/dc/mmi/heater/gc/wg/y_branch等）。
        width_um: 器件宽度（μm）。
        height_um: 器件高度（μm）。
        ports: 端口列表 [(name, dx, dy, direction), ...]。
        params: 器件参数。
        process_node: 工艺节点（如 "220nm SOI"，对齐 P1-3）。
    """

    name: str
    device_type: str
    width_um: float = 10.0
    height_um: float = 10.0
    ports: list[tuple[str, float, float, str]] = field(default_factory=list)
    params: dict = field(default_factory=dict)
    process_node: str | None = None


@dataclass
class CircuitSpec:
    """电路规格（内部 dataclass，对外 API 用 dict）。

    Attributes:
        name: 电路名称。
        devices: 器件列表。
        connections: 连接列表 [(dev1, port1, dev2, port2), ...]。
        canvas_w: 画布宽度（μm）。
        canvas_h: 画布高度（μm）。
        benchmark_source: Benchmark 来源（TILOS/Apollo/LiDAR/CUSTOM，P1-5）。
        process_node: 工艺节点（如 "220nm SOI"，P1-3）。
        optical_wavelength_nm: 工作波长（nm，如 1550）。
        target_metric: 评估指标（HPWL/DRV/ROUTING_SUCCESS_RATE/INSERTION_LOSS_DB）。
        target_value: 目标值（与 target_metric 配合，如 HPWL < 10000μm）。
    """

    name: str
    devices: list[DeviceSpec] = field(default_factory=list)
    connections: list[tuple[str, str, str, str]] = field(default_factory=list)
    canvas_w: float = 1000.0
    canvas_h: float = 1000.0
    benchmark_source: BenchmarkSource = BenchmarkSource.CUSTOM
    process_node: str | None = None
    optical_wavelength_nm: float = 1550.0
    target_metric: TargetMetric = TargetMetric.ROUTING_SUCCESS_RATE
    target_value: float = 1.0


__all__ = ["BenchmarkSource", "TargetMetric", "DeviceSpec", "CircuitSpec"]
