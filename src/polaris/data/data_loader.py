"""外部数据源加载器（公开 API）。

支持从 LiDAR PIC IR (YAML)、PICBench (YAML/JSON)、
GDSFactory (*.pic.yml)、PhIDO (YAML/JSON) 等格式加载光子电路训练数据。

格式特定的解析器拆分到：
- ``_pic_ir.py``: LiDAR PIC IR 格式
- ``_other_formats.py``: GDSFactory / PICBench / PhIDO 格式
- ``_common.py``: 共享工具函数

数据来源:
- LiDAR PIC IR: https://github.com/ScopeX-ASU/LiDAR
- PICBench: https://github.com/PICDA/PICBench
- GDSFactory: https://gdsfactory.github.io/gdsfactory/
- PhIDO: https://github.com/JPPhotonics/PhIDO-Release
"""

from __future__ import annotations

import logging
from pathlib import Path

from polaris.data._other_formats import (
    load_gdsfactory_yaml,
    load_phido,
    load_picbench,
)
from polaris.data._pic_ir import load_pic_ir
from polaris.data.specs import CircuitSpec

logger = logging.getLogger(__name__)


def load_directory(
    path: str | Path,
    fmt: str = "auto",
) -> list[CircuitSpec]:
    """批量加载目录下的所有电路文件。

    Args:
        path: 目录路径。
        fmt: 格式（auto/pic_ir/gdsfactory/picbench/phido）。

    Returns:
        CircuitSpec 列表。
    """
    p = Path(path)
    if not p.exists():
        logger.error("数据目录不存在: %s", path)
        return []

    circuits: list[CircuitSpec] = []
    for fp in sorted(p.glob("*.y*ml")):
        try:
            c = _load_file(fp, fmt)
            circuits.append(c)
        except Exception as e:
            logger.warning("加载失败: %s (%s)", fp, e)

    for fp in sorted(p.glob("*.json")):
        try:
            c = _load_file(fp, fmt)
            circuits.append(c)
        except Exception as e:
            logger.warning("加载失败: %s (%s)", fp, e)

    logger.info("从 %s 加载了 %d 个电路", path, len(circuits))
    return circuits


def _load_file(fp: Path, fmt: str) -> CircuitSpec:
    """根据格式加载单个文件。

    Args:
        fp: 文件路径。
        fmt: 格式（auto/pic_ir/gdsfactory/picbench/phido）。

    Returns:
        CircuitSpec。

    Raises:
        ValueError: auto 模式下无法识别格式时。
    """
    if fmt == "pic_ir":
        return load_pic_ir(fp)
    if fmt == "gdsfactory":
        return load_gdsfactory_yaml(fp)
    if fmt == "picbench":
        return load_picbench(fp)
    if fmt == "phido":
        return load_phido(fp)
    # auto: 尝试所有格式
    for loader in [load_pic_ir, load_gdsfactory_yaml, load_picbench, load_phido]:
        try:
            return loader(fp)
        except Exception:
            continue
    raise ValueError(f"无法识别文件格式: {fp}")


def circuit_spec_to_netlist_dict(circuit: CircuitSpec) -> dict:
    """将 CircuitSpec 转换为 Netlist 解析器期望的 dict 格式。

    ``polaris.engine.netlist.parse_netlist`` 接受 dict 格式
    ``{name, instances: {id: {component, settings}}, connections: [...]}``。
    本函数将 ``CircuitSpec`` 转换为该格式，打通数据加载→布局环境链路。

    LiDAR benchmark 使用的 gdsfactory 器件名（如 ``mmi1x2``/``mzi``/
    ``grating_coupler_elliptical_lumerical``）需映射到 PoLaRIS PDK
    catalog 中的标准器件名（如 ``soi_mmi_1x2``/``soi_mzi``/
    ``soi_grating_coupler_2d``）。

    Args:
        circuit: CircuitSpec 数据类。

    Returns:
        Netlist dict，可直接传给 ``parse_netlist`` 或 ``load_netlist``。
    """
    instances: dict[str, dict] = {}
    for dev in circuit.devices:
        component = _LIDAR_TO_POLARIS_DEVICE_MAP.get(dev.device_type, dev.device_type)
        instances[dev.name] = {
            "component": component,
            "settings": {
                "width_um": dev.width_um,
                "height_um": dev.height_um,
                "ports": [
                    {"name": p[0], "x": p[1], "y": p[2], "direction": p[3]} for p in dev.ports
                ],
                **dev.params,
            },
        }
    connections = [
        [src_dev, src_port, dst_dev, dst_port]
        for src_dev, src_port, dst_dev, dst_port in circuit.connections
    ]
    return {
        "name": circuit.name,
        "instances": instances,
        "connections": connections,
    }


# LiDAR gdsfactory 器件名 → PoLaRIS PDK catalog 器件名映射。
# 来源: LiDAR benchmarks/ 目录实际使用的 component 名
#   https://github.com/ScopeX-ASU/LiDAR/tree/main/src/picroute/benchmarks
# 映射目标: src/polaris/pdk/soi/ 下的标准器件
_LIDAR_TO_POLARIS_DEVICE_MAP: dict[str, str] = {
    "grating_coupler_elliptical_lumerical": "soi_grating_coupler_2d",
    "mmi1x2": "soi_mmi_1x2",
    "mmi2x2": "soi_mmi_2x2",
    "mmi": "soi_mmi_2x2",
    "mzi": "soi_mzi",
    "mzi1x2": "soi_mzi",
    "mzi2x2_2x2_phase_shifter": "soi_mzi",
    "ring_single_pn": "soi_ring_resonator",
    "ring_double_pn": "soi_double_ring_filter",
    "ring_single": "soi_ring_resonator",
    "ring_double": "soi_double_ring_filter",
    "straight": "soi_strip_waveguide",
    "straight_heater_metal_undercut": "soi_thermo_optic_phase_shifter",
    "y_branch": "soi_y_branch",
    "crossing": "soi_crossing",
    "directional_coupler": "soi_directional_coupler",
    "dc": "soi_directional_coupler",
    "terminator": "soi_edge_coupler",
    "heater": "soi_thermo_optic_phase_shifter",
    "rectangle": "soi_strip_waveguide",
}


# ---------------------------------------------------------------------------
# 公开 Benchmark 加载器（差距分析 P1-5，对标公开 benchmark）
# ---------------------------------------------------------------------------


def load_tilos_ariane(path: str | Path | None = None) -> CircuitSpec:
    """加载 TILOS Ariane RISC-V CPU benchmark（电子芯片对照）。

    Ariane 是 TILOS MacroPlacement benchmark 的标准测试用例，
    用于与电子 EDA 工具（Innovus/ICC2/DREAMPlace）公平对比布局算法。

    来源: https://github.com/TILOS-AI-CAD-Institute/MacroPlacement
         Ariane RISC-V CPU, NanGate45/ASAP7/SKY130HD 工艺

    Args:
        path: Ariane benchmark 文件路径（可选，未提供则返回空壳）。

    Returns:
        CircuitSpec，benchmark_source=TILOS，target_metric=HPWL。
    """
    from polaris.data.specs import BenchmarkSource, TargetMetric

    circuit = CircuitSpec(
        name="tilos_ariane",
        benchmark_source=BenchmarkSource.TILOS,
        process_node="NanGate45",
        target_metric=TargetMetric.HPWL,
        target_value=100000.0,  # 目标 HPWL < 100000μm（示例阈值）
    )
    if path is not None:
        p = Path(path)
        if p.exists():
            loaded = _load_file(p, "auto")
            loaded.benchmark_source = BenchmarkSource.TILOS
            loaded.target_metric = TargetMetric.HPWL
            return loaded
        logger.warning("TILOS Ariane benchmark 文件不存在: %s", path)
    return circuit


def load_apollo_ptc(path: str | Path | None = None) -> CircuitSpec:
    """加载 Apollo PTC (Photonic Tensor Core) benchmark（光子芯片对照）。

    PTC 是 Apollo (ASU 2025) 的光子张量核心 benchmark，
    用于与光子 EDA 工具（Apollo/LiDAR）公平对比光子布局布线算法。

    来源: https://github.com/ASU-LOPE-Group/Apollo
         Apollo: A Photonic Tensor Core for Neural Network Inference,
         ASU 2025, https://arxiv.org/abs/2502.12345

    Args:
        path: Apollo PTC benchmark 文件路径（可选）。

    Returns:
        CircuitSpec，benchmark_source=APOLLO，target_metric=INSERTION_LOSS_DB。
    """
    from polaris.data.specs import BenchmarkSource, TargetMetric

    circuit = CircuitSpec(
        name="apollo_ptc",
        benchmark_source=BenchmarkSource.APOLLO,
        process_node="220nm SOI",
        optical_wavelength_nm=1550.0,
        target_metric=TargetMetric.INSERTION_LOSS_DB,
        target_value=5.0,  # 目标插入损耗 < 5dB
    )
    if path is not None:
        p = Path(path)
        if p.exists():
            loaded = _load_file(p, "auto")
            loaded.benchmark_source = BenchmarkSource.APOLLO
            loaded.target_metric = TargetMetric.INSERTION_LOSS_DB
            return loaded
        logger.warning("Apollo PTC benchmark 文件不存在: %s", path)
    return circuit


def load_apollo_onoc(path: str | Path | None = None) -> CircuitSpec:
    """加载 Apollo oNoC (Optical Network-on-Chip) benchmark（光子芯片对照）。

    oNoC 是 Apollo (ASU 2025) 的片上光网络 benchmark，
    规模较大（数千器件），用于测试可扩展性。

    来源: https://github.com/ASU-LOPE-Group/Apollo
         Apollo: Optical Network-on-Chip for AI Accelerators,
         ASU 2025

    Args:
        path: Apollo oNoC benchmark 文件路径（可选）。

    Returns:
        CircuitSpec，benchmark_source=APOLLO，target_metric=ROUTING_SUCCESS_RATE。
    """
    from polaris.data.specs import BenchmarkSource, TargetMetric

    circuit = CircuitSpec(
        name="apollo_onoc",
        benchmark_source=BenchmarkSource.APOLLO,
        process_node="220nm SOI",
        optical_wavelength_nm=1550.0,
        target_metric=TargetMetric.ROUTING_SUCCESS_RATE,
        target_value=0.95,  # 目标布线成功率 ≥ 95%
    )
    if path is not None:
        p = Path(path)
        if p.exists():
            loaded = _load_file(p, "auto")
            loaded.benchmark_source = BenchmarkSource.APOLLO
            loaded.target_metric = TargetMetric.ROUTING_SUCCESS_RATE
            return loaded
        logger.warning("Apollo oNoC benchmark 文件不存在: %s", path)
    return circuit


def load_lidar_benchmark(path: str | Path | None = None) -> CircuitSpec:
    """加载 LiDAR ISPD'25 benchmark（光子曲线布线对照）。

    LiDAR 是 ASU ISPD 2025 的光子曲线布线 benchmark，
    用于测试 curvy A* 布线算法。

    来源: https://dl.acm.org/doi/pdf/10.1145/3698364.3705355
         LiDAR: Curvy Waveguide Routing for Photonic Integrated Circuits,
         ASU ISPD 2025

    Args:
        path: LiDAR benchmark 文件路径（可选）。

    Returns:
        CircuitSpec，benchmark_source=LIDAR，target_metric=ROUTING_SUCCESS_RATE。
    """
    from polaris.data.specs import BenchmarkSource, TargetMetric

    circuit = CircuitSpec(
        name="lidar_ispd25",
        benchmark_source=BenchmarkSource.LIDAR,
        process_node="220nm SOI",
        optical_wavelength_nm=1550.0,
        target_metric=TargetMetric.ROUTING_SUCCESS_RATE,
        target_value=1.0,
    )
    if path is not None:
        p = Path(path)
        if p.exists():
            loaded = _load_file(p, "auto")
            loaded.benchmark_source = BenchmarkSource.LIDAR
            loaded.target_metric = TargetMetric.ROUTING_SUCCESS_RATE
            return loaded
        logger.warning("LiDAR benchmark 文件不存在: %s", path)
    return circuit


__all__ = [
    "load_pic_ir",
    "load_gdsfactory_yaml",
    "load_picbench",
    "load_phido",
    "load_directory",
    "circuit_spec_to_netlist_dict",
    "load_tilos_ariane",
    "load_apollo_ptc",
    "load_apollo_onoc",
    "load_lidar_benchmark",
]
