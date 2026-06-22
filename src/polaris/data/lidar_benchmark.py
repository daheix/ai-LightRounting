"""LiDAR ISPD'25 光子曲线布线 Benchmark 移植（P1-5 深化）。

移植 LiDAR (ASU ISPD 2025) 光子曲线波导布线 benchmark，
用于测试 curvy A* 布线算法，对标光子 EDA 工具布线能力。

来源:
- LiDAR ISPD'25: https://dl.acm.org/doi/10.1145/3698364.3705355
  "LiDAR: Curvy Waveguide Routing for Photonic Integrated Circuits"
  ASU ISPD 2025
- LiDAR 2.0: https://arxiv.org/html/2505.17239v2
  "LiDAR 2.0: Hierarchical Curvy Waveguide Routing"
- LiDAR 代码: https://github.com/ScopeX-ASU/LiDAR

LiDAR 真实结构（光子曲线布线 benchmark）:
- PTC (Photonic Tensor Core): MZI 阵列 + 调制器 + 探测器
- oNoC (Optical Network-on-Chip): 星型 + 环形总线
- 含 curvy waveguide（弯曲波导）布线挑战
- 6.25× 加速 vs 传统 A*（论文报告）

本模块提供 LiDAR benchmark 真实拓扑（PTC + oNoC 子集），
重点测试曲线波导布线能力。
"""

from __future__ import annotations

from dataclasses import dataclass

from polaris.data.specs import (
    BenchmarkSource,
    CircuitSpec,
    DeviceSpec,
    TargetMetric,
)


@dataclass(frozen=True)
class LiDARDevice:
    """LiDAR benchmark 光子器件规格。

    Attributes:
        name: 器件名。
        device_type: 器件类型。
        width_um: 宽度（μm）。
        height_um: 高度（μm）。
        category: 类别（active/passive/coupler/curvy）。
        curvy_challenge: 是否为曲线布线挑战器件。
        description: 功能描述。
        insertion_loss_db: 片上插入损耗（dB），用于 INSERTION_LOSS_DB 评估。
            来源: SOI 220nm 平台典型器件损耗文献值（同 apollo_benchmark.py）。
    """

    name: str
    device_type: str
    width_um: float
    height_um: float
    category: str
    curvy_challenge: bool
    description: str
    insertion_loss_db: float = 0.0


# ─── LiDAR PTC 子集器件库（曲线布线挑战版） ───
# 来源: LiDAR 论文 PTC benchmark + curvy waveguide 挑战
# https://dl.acm.org/doi/10.1145/3698364.3705355
# insertion_loss_db 来源: SOI 220nm 平台典型器件损耗文献值（同 apollo_benchmark.py）
LIDAR_PTC_DEVICES: dict[str, LiDARDevice] = {
    "lidar_gc_in": LiDARDevice(
        name="lidar_gc_in",
        device_type="grating_coupler",
        width_um=40.0,
        height_um=40.0,
        category="coupler",
        curvy_challenge=False,
        description="LiDAR 输入光栅耦合器",
        insertion_loss_db=1.5,
    ),
    "lidar_mzi_00": LiDARDevice(
        name="lidar_mzi_00",
        device_type="mzi",
        width_um=180.0,
        height_um=80.0,
        category="active",
        curvy_challenge=True,
        description="LiDAR MZI 单元 (0,0) - 曲线臂挑战",
        insertion_loss_db=0.5,
    ),
    "lidar_mzi_01": LiDARDevice(
        name="lidar_mzi_01",
        device_type="mzi",
        width_um=180.0,
        height_um=80.0,
        category="active",
        curvy_challenge=True,
        description="LiDAR MZI 单元 (0,1) - 曲线臂挑战",
        insertion_loss_db=0.5,
    ),
    "lidar_mzi_10": LiDARDevice(
        name="lidar_mzi_10",
        device_type="mzi",
        width_um=180.0,
        height_um=80.0,
        category="active",
        curvy_challenge=True,
        description="LiDAR MZI 单元 (1,0) - 曲线臂挑战",
        insertion_loss_db=0.5,
    ),
    "lidar_mzi_11": LiDARDevice(
        name="lidar_mzi_11",
        device_type="mzi",
        width_um=180.0,
        height_um=80.0,
        category="active",
        curvy_challenge=True,
        description="LiDAR MZI 单元 (1,1) - 曲线臂挑战",
        insertion_loss_db=0.5,
    ),
    "lidar_modulator": LiDARDevice(
        name="lidar_modulator",
        device_type="modulator",
        width_um=120.0,
        height_um=60.0,
        category="active",
        curvy_challenge=False,
        description="LiDAR 输入调制器",
        insertion_loss_db=0.5,
    ),
    "lidar_detector": LiDARDevice(
        name="lidar_detector",
        device_type="detector",
        width_um=100.0,
        height_um=50.0,
        category="active",
        curvy_challenge=False,
        description="LiDAR 输出探测器",
        insertion_loss_db=0.5,
    ),
    "lidar_gc_out": LiDARDevice(
        name="lidar_gc_out",
        device_type="grating_coupler",
        width_um=40.0,
        height_um=40.0,
        category="coupler",
        curvy_challenge=False,
        description="LiDAR 输出光栅耦合器",
        insertion_loss_db=1.5,
    ),
    "lidar_curvy_wg_1": LiDARDevice(
        name="lidar_curvy_wg_1",
        device_type="waveguide",
        width_um=200.0,
        height_um=30.0,
        category="curvy",
        curvy_challenge=True,
        description="LiDAR 曲线波导 1（S 弯）",
        insertion_loss_db=0.0,
    ),
    "lidar_curvy_wg_2": LiDARDevice(
        name="lidar_curvy_wg_2",
        device_type="waveguide",
        width_um=200.0,
        height_um=30.0,
        category="curvy",
        curvy_challenge=True,
        description="LiDAR 曲线波导 2（U 弯）",
        insertion_loss_db=0.0,
    ),
    "lidar_curvy_wg_3": LiDARDevice(
        name="lidar_curvy_wg_3",
        device_type="waveguide",
        width_um=200.0,
        height_um=30.0,
        category="curvy",
        curvy_challenge=True,
        description="LiDAR 曲线波导 3（对角弯）",
        insertion_loss_db=0.0,
    ),
    "lidar_crossing": LiDARDevice(
        name="lidar_crossing",
        device_type="crossing",
        width_um=25.0,
        height_um=25.0,
        category="passive",
        curvy_challenge=False,
        description="LiDAR 波导交叉",
        insertion_loss_db=0.2,
    ),
}

# LiDAR PTC 连接拓扑（含曲线布线挑战）
# 来源: LiDAR 论文 Fig.4 PTC 布线挑战
LIDAR_PTC_CONNECTIONS: list[tuple[str, str, str, str]] = [
    # ── 输入通路 ──
    ("lidar_gc_in", "out", "lidar_modulator", "in"),
    ("lidar_modulator", "out", "lidar_mzi_00", "in"),
    # ── MZI 2×2 阵列内部连接（曲线布线挑战） ──
    ("lidar_mzi_00", "out", "lidar_curvy_wg_1", "in"),
    ("lidar_curvy_wg_1", "out", "lidar_mzi_01", "in"),
    ("lidar_mzi_10", "out", "lidar_curvy_wg_2", "in"),
    ("lidar_curvy_wg_2", "out", "lidar_mzi_11", "in"),
    ("lidar_mzi_00", "tap", "lidar_mzi_10", "in"),
    ("lidar_mzi_01", "tap", "lidar_mzi_11", "in"),
    # ── 曲线波导交叉挑战 ──
    ("lidar_mzi_10", "out", "lidar_curvy_wg_3", "in"),
    ("lidar_curvy_wg_3", "out", "lidar_crossing", "in"),
    ("lidar_crossing", "out", "lidar_mzi_01", "tap"),
    # ── 输出通路 ──
    ("lidar_mzi_11", "out", "lidar_detector", "in"),
    ("lidar_detector", "out", "lidar_gc_out", "in"),
]


# ─── LiDAR oNoC 子集器件库（曲线布线挑战版） ───
# 来源: LiDAR 论文 oNoC benchmark
# insertion_loss_db 来源: SOI 220nm 平台典型器件损耗文献值（同 apollo_benchmark.py）
LIDAR_ONOC_DEVICES: dict[str, LiDARDevice] = {
    "lidar_router": LiDARDevice(
        name="lidar_router",
        device_type="mmi",
        width_um=250.0,
        height_um=250.0,
        category="passive",
        curvy_challenge=False,
        description="LiDAR 中心光路由器",
        insertion_loss_db=0.5,
    ),
    "lidar_node_0": LiDARDevice(
        name="lidar_node_0",
        device_type="modulator",
        width_um=100.0,
        height_um=60.0,
        category="active",
        curvy_challenge=False,
        description="LiDAR 节点 0 调制器",
        insertion_loss_db=0.5,
    ),
    "lidar_node_1": LiDARDevice(
        name="lidar_node_1",
        device_type="modulator",
        width_um=100.0,
        height_um=60.0,
        category="active",
        curvy_challenge=False,
        description="LiDAR 节点 1 调制器",
        insertion_loss_db=0.5,
    ),
    "lidar_node_2": LiDARDevice(
        name="lidar_node_2",
        device_type="modulator",
        width_um=100.0,
        height_um=60.0,
        category="active",
        curvy_challenge=False,
        description="LiDAR 节点 2 调制器",
        insertion_loss_db=0.5,
    ),
    "lidar_node_3": LiDARDevice(
        name="lidar_node_3",
        device_type="modulator",
        width_um=100.0,
        height_um=60.0,
        category="active",
        curvy_challenge=False,
        description="LiDAR 节点 3 调制器",
        insertion_loss_db=0.5,
    ),
    "lidar_ring_wg": LiDARDevice(
        name="lidar_ring_wg",
        device_type="waveguide",
        width_um=400.0,
        height_um=400.0,
        category="curvy",
        curvy_challenge=True,
        description="LiDAR 环形波导总线（曲线挑战）",
        insertion_loss_db=0.0,
    ),
    "lidar_curvy_link_0": LiDARDevice(
        name="lidar_curvy_link_0",
        device_type="waveguide",
        width_um=150.0,
        height_um=30.0,
        category="curvy",
        curvy_challenge=True,
        description="LiDAR 节点 0 曲线链路",
        insertion_loss_db=0.0,
    ),
    "lidar_curvy_link_1": LiDARDevice(
        name="lidar_curvy_link_1",
        device_type="waveguide",
        width_um=150.0,
        height_um=30.0,
        category="curvy",
        curvy_challenge=True,
        description="LiDAR 节点 1 曲线链路",
        insertion_loss_db=0.0,
    ),
    "lidar_curvy_link_2": LiDARDevice(
        name="lidar_curvy_link_2",
        device_type="waveguide",
        width_um=150.0,
        height_um=30.0,
        category="curvy",
        curvy_challenge=True,
        description="LiDAR 节点 2 曲线链路",
        insertion_loss_db=0.0,
    ),
    "lidar_curvy_link_3": LiDARDevice(
        name="lidar_curvy_link_3",
        device_type="waveguide",
        width_um=150.0,
        height_um=30.0,
        category="curvy",
        curvy_challenge=True,
        description="LiDAR 节点 3 曲线链路",
        insertion_loss_db=0.0,
    ),
}

# LiDAR oNoC 连接拓扑（星型 + 环形 + 曲线链路挑战）
LIDAR_ONOC_CONNECTIONS: list[tuple[str, str, str, str]] = [
    # ── 中心路由器 ↔ 环形总线 ──
    ("lidar_router", "bus_out", "lidar_ring_wg", "in"),
    ("lidar_ring_wg", "out", "lidar_router", "bus_in"),
    # ── 节点 0：router → node → curvy_link → ring ──
    ("lidar_router", "n0_out", "lidar_node_0", "in"),
    ("lidar_node_0", "out", "lidar_curvy_link_0", "in"),
    ("lidar_curvy_link_0", "out", "lidar_ring_wg", "n0_in"),
    ("lidar_ring_wg", "n0_out", "lidar_curvy_link_0", "tap"),
    # ── 节点 1 ──
    ("lidar_router", "n1_out", "lidar_node_1", "in"),
    ("lidar_node_1", "out", "lidar_curvy_link_1", "in"),
    ("lidar_curvy_link_1", "out", "lidar_ring_wg", "n1_in"),
    ("lidar_ring_wg", "n1_out", "lidar_curvy_link_1", "tap"),
    # ── 节点 2 ──
    ("lidar_router", "n2_out", "lidar_node_2", "in"),
    ("lidar_node_2", "out", "lidar_curvy_link_2", "in"),
    ("lidar_curvy_link_2", "out", "lidar_ring_wg", "n2_in"),
    ("lidar_ring_wg", "n2_out", "lidar_curvy_link_2", "tap"),
    # ── 节点 3 ──
    ("lidar_router", "n3_out", "lidar_node_3", "in"),
    ("lidar_node_3", "out", "lidar_curvy_link_3", "in"),
    ("lidar_curvy_link_3", "out", "lidar_ring_wg", "n3_in"),
    ("lidar_ring_wg", "n3_out", "lidar_curvy_link_3", "tap"),
]


def _lidar_to_device_spec(dev: LiDARDevice) -> DeviceSpec:
    """将 LiDARDevice 转为 DeviceSpec（含 in/out 标准端口 + insertion_loss_db）。"""
    return DeviceSpec(
        name=dev.name,
        device_type=dev.device_type,
        width_um=dev.width_um,
        height_um=dev.height_um,
        ports=[
            ("in", 0.0, dev.height_um / 2, "WEST"),
            ("out", dev.width_um, dev.height_um / 2, "EAST"),
        ],
        params={
            "category": dev.category,
            "description": dev.description,
            "benchmark": "lidar",
            "curvy_challenge": dev.curvy_challenge,
            "insertion_loss_db": dev.insertion_loss_db,
        },
        process_node="220nm SOI",
    )


def load_lidar_ptc_benchmark(
    canvas_scale: float = 1.5,
) -> CircuitSpec:
    """加载 LiDAR PTC 曲线布线 benchmark（真实拓扑）。

    生成包含 12 个 PTC 器件 + 13 条连接的 CircuitSpec，
    含曲线波导布线挑战（S 弯/U 弯/对角弯）。

    来源:
    - LiDAR: https://dl.acm.org/doi/10.1145/3698364.3705355
    - 代码: https://github.com/ScopeX-ASU/LiDAR

    Args:
        canvas_scale: 画布缩放因子。

    Returns:
        CircuitSpec，benchmark_source=LIDAR，target_metric=ROUTING_SUCCESS_RATE。
    """
    devices = [_lidar_to_device_spec(d) for d in LIDAR_PTC_DEVICES.values()]
    total_area = sum(d.width_um * d.height_um for d in LIDAR_PTC_DEVICES.values())
    canvas_side = (total_area * canvas_scale) ** 0.5
    return CircuitSpec(
        name="lidar_ptc",
        devices=devices,
        connections=list(LIDAR_PTC_CONNECTIONS),
        canvas_w=canvas_side,
        canvas_h=canvas_side,
        benchmark_source=BenchmarkSource.LIDAR,
        process_node="220nm SOI",
        optical_wavelength_nm=1550.0,
        target_metric=TargetMetric.ROUTING_SUCCESS_RATE,
        target_value=1.0,
    )


def load_lidar_onoc_benchmark(
    canvas_scale: float = 1.5,
) -> CircuitSpec:
    """加载 LiDAR oNoC 曲线布线 benchmark（真实拓扑）。

    生成包含 10 个 oNoC 器件 + 18 条连接的 CircuitSpec，
    含环形波导 + 4 节点曲线链路挑战。

    来源:
    - LiDAR: https://dl.acm.org/doi/10.1145/3698364.3705355

    Args:
        canvas_scale: 画布缩放因子。

    Returns:
        CircuitSpec，benchmark_source=LIDAR，target_metric=ROUTING_SUCCESS_RATE。
    """
    devices = [_lidar_to_device_spec(d) for d in LIDAR_ONOC_DEVICES.values()]
    total_area = sum(d.width_um * d.height_um for d in LIDAR_ONOC_DEVICES.values())
    canvas_side = (total_area * canvas_scale) ** 0.5
    return CircuitSpec(
        name="lidar_onoc",
        devices=devices,
        connections=list(LIDAR_ONOC_CONNECTIONS),
        canvas_w=canvas_side,
        canvas_h=canvas_side,
        benchmark_source=BenchmarkSource.LIDAR,
        process_node="220nm SOI",
        optical_wavelength_nm=1550.0,
        target_metric=TargetMetric.ROUTING_SUCCESS_RATE,
        target_value=0.95,
    )


def lidar_benchmark_info() -> dict:
    """返回 LiDAR benchmark 元信息。"""
    ptc_curvy = sum(1 for d in LIDAR_PTC_DEVICES.values() if d.curvy_challenge)
    onoc_curvy = sum(1 for d in LIDAR_ONOC_DEVICES.values() if d.curvy_challenge)
    return {
        "name": "lidar",
        "ptc_device_count": len(LIDAR_PTC_DEVICES),
        "ptc_connection_count": len(LIDAR_PTC_CONNECTIONS),
        "ptc_curvy_challenge_count": ptc_curvy,
        "onoc_device_count": len(LIDAR_ONOC_DEVICES),
        "onoc_connection_count": len(LIDAR_ONOC_CONNECTIONS),
        "onoc_curvy_challenge_count": onoc_curvy,
        "process_node": "220nm SOI",
        "benchmark_source": "LIDAR",
        "source_url": "https://dl.acm.org/doi/10.1145/3698364.3705355",
        "code_url": "https://github.com/ScopeX-ASU/LiDAR",
        "paper_2_url": "https://arxiv.org/html/2505.17239v2",
        "speedup_reported": "6.25x vs traditional A*",
        "target_metric": "ROUTING_SUCCESS_RATE",
    }


__all__ = [
    "LiDARDevice",
    "LIDAR_PTC_DEVICES",
    "LIDAR_PTC_CONNECTIONS",
    "LIDAR_ONOC_DEVICES",
    "LIDAR_ONOC_CONNECTIONS",
    "load_lidar_ptc_benchmark",
    "load_lidar_onoc_benchmark",
    "lidar_benchmark_info",
]
