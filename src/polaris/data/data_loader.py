"""外部数据源加载器（公开 API）。

支持从 LiDAR PIC IR (YAML)、PICBench (YAML/JSON)、
GDSFactory (*.pic.yml)、PhIDO (YAML/JSON) 等格式加载光子电路训练数据。

格式特定的解析器拆分到：
- ``_pic_ir.py``: LiDAR PIC IR 格式
- ``_other_formats.py``: GDSFactory / PICBench / PhIDO 格式
- ``_common.py``: 共享工具函数

R03 异常处理设计: 失败即 raise，禁止静默 fall-back。auto 模式逐个尝试
所有 loader 但记录每个 loader 的失败原因，全部失败时 raise 汇总错误；
批量加载目录时单文件失败即 raise（不跳过），确保数据完整性。

数据来源:
- LiDAR PIC IR: https://github.com/ScopeX-ASU/LiDAR
- PICBench: https://github.com/PICDA/PICBench
- GDSFactory: https://gdsfactory.github.io/gdsfactory/
- PhIDO: https://github.com/JPPhotonics/PhIDO-Release

异常处理最佳实践文献:
- Python 官方异常处理指南: https://docs.python.org/3/tutorial/errors.html
- PEP 8 异常设计: https://peps.python.org/pep-0008/#exception-handling
- Real Python 异常处理: https://realpython.com/python-exceptions/
- Google Python 风格指南异常: https://google.github.io/styleguide/pyguide.html#exceptions
"""

from __future__ import annotations

import logging
from pathlib import Path

import yaml

from polaris.data._other_formats import (
    load_gdsfactory_yaml,
    load_phido,
    load_picbench,
)
from polaris.data._pic_ir import load_pic_ir
from polaris.data.specs import CircuitSpec, DeviceSpec

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

    Raises:
        FileNotFoundError: 数据目录不存在时（修复违规 9，不再返回空列表）。
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(
            f"数据目录不存在: {path}。请检查路径是否正确。"
        )

    circuits: list[CircuitSpec] = []
    # 收集 yaml 与 json 文件（R03: 单个文件失败应 raise 而非 continue 跳过）
    files = sorted(p.glob("*.y*ml")) + sorted(p.glob("*.json"))
    for fp in files:
        try:
            circuits.append(_load_file(fp, fmt))
        except (ValueError, KeyError, TypeError, OSError, yaml.YAMLError) as e:
            # R03: 失败即 raise，禁止静默跳过单个文件（含 I/O 错误与解析错误）
            raise ValueError(
                f"数据文件加载失败: {fp}: {type(e).__name__}: {e}"
            ) from e

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
    # auto: 逐个尝试所有格式，全部失败则 raise 并汇总各 loader 失败原因
    # （R03: 无静默 fall-back；记录每个 loader 的失败原因供诊断）
    errors: list[str] = []
    for loader_name, loader in [
        ("pic_ir", load_pic_ir),
        ("gdsfactory", load_gdsfactory_yaml),
        ("picbench", load_picbench),
        ("phido", load_phido),
    ]:
        try:
            return loader(fp)
        except (ValueError, KeyError, TypeError, AttributeError, OSError, yaml.YAMLError) as e:
            errors.append(f"{loader_name}: {type(e).__name__}: {e}")
    raise ValueError(
        f"无法识别文件格式: {fp}。所有加载器均失败: {'; '.join(errors)}"
    )


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

    默认返回真实 Ariane 模块拓扑（17 模块 + 25 连接，P1-5 第23轮），
    若提供 path 则从文件加载并覆盖 benchmark_source。

    来源: https://github.com/TILOS-AI-CAD-Institute/MacroPlacement
         Ariane RISC-V CPU, NanGate45/ASAP7/SKY130HD 工艺
         CPU 源码: https://github.com/openhwgroup/cva6

    Args:
        path: Ariane benchmark 文件路径（可选，未提供则用真实拓扑生成）。

    Returns:
        CircuitSpec，benchmark_source=TILOS，target_metric=HPWL。
    """
    from polaris.data.specs import BenchmarkSource, TargetMetric
    from polaris.data.tilos_benchmark import load_ariane_benchmark

    # 默认：返回真实 Ariane 模块拓扑（第23轮 P1-5 深化）
    circuit = load_ariane_benchmark()
    if path is not None:
        p = Path(path)
        if not p.exists():
            # R03: 用户指定 path 但文件不存在，禁止静默 fall-back 到默认拓扑
            raise FileNotFoundError(
                f"TILOS Ariane benchmark 文件不存在: {path}。"
                f"请检查路径，或不传 path 参数以使用内置默认拓扑。"
            )
        loaded = _load_file(p, "auto")
        loaded.benchmark_source = BenchmarkSource.TILOS
        loaded.target_metric = TargetMetric.HPWL
        return loaded
    return circuit


def load_apollo_ptc(path: str | Path | None = None) -> CircuitSpec:
    """加载 Apollo PTC (Photonic Tensor Core) benchmark（光子芯片对照）。

    PTC 是 Apollo (ASU 2025) 的光子张量核心 benchmark，
    用于与光子 EDA 工具（Apollo/LiDAR）公平对比光子布局布线算法。

    默认返回真实 PTC 拓扑（12 器件 + 13 连接，P1-5 第24轮深化），
    若提供 path 则从文件加载并覆盖 benchmark_source。

    来源: https://github.com/ASU-LOPE-Group/Apollo
         Apollo: A Photonic Tensor Core for Neural Network Inference,
         ASU 2025, https://arxiv.org/abs/2504.18813

    Args:
        path: Apollo PTC benchmark 文件路径（可选）。

    Returns:
        CircuitSpec，benchmark_source=APOLLO，target_metric=INSERTION_LOSS_DB。
    """
    from polaris.data.apollo_benchmark import load_apollo_ptc_benchmark
    from polaris.data.specs import BenchmarkSource, TargetMetric

    circuit = load_apollo_ptc_benchmark()
    if path is not None:
        p = Path(path)
        if not p.exists():
            # R03: 用户指定 path 但文件不存在，禁止静默 fall-back 到默认拓扑
            raise FileNotFoundError(
                f"Apollo PTC benchmark 文件不存在: {path}。"
                f"请检查路径，或不传 path 参数以使用内置默认拓扑。"
            )
        loaded = _load_file(p, "auto")
        loaded.benchmark_source = BenchmarkSource.APOLLO
        loaded.target_metric = TargetMetric.INSERTION_LOSS_DB
        return loaded
    return circuit


def load_apollo_onoc(path: str | Path | None = None) -> CircuitSpec:
    """加载 Apollo oNoC (Optical Network-on-Chip) benchmark（光子芯片对照）。

    oNoC 是 Apollo (ASU 2025) 的片上光网络 benchmark，
    规模较大（数千器件），用于测试可扩展性。

    默认返回真实 oNoC 拓扑（14 器件 + 21 连接，P1-5 第24轮深化），
    若提供 path 则从文件加载并覆盖 benchmark_source。

    来源: https://github.com/ASU-LOPE-Group/Apollo
         Apollo: Optical Network-on-Chip for AI Accelerators,
         ASU 2025

    Args:
        path: Apollo oNoC benchmark 文件路径（可选）。

    Returns:
        CircuitSpec，benchmark_source=APOLLO，target_metric=ROUTING_SUCCESS_RATE。
    """
    from polaris.data.apollo_benchmark import load_apollo_onoc_benchmark
    from polaris.data.specs import BenchmarkSource, TargetMetric

    circuit = load_apollo_onoc_benchmark()
    if path is not None:
        p = Path(path)
        if not p.exists():
            # R03: 用户指定 path 但文件不存在，禁止静默 fall-back 到默认拓扑
            raise FileNotFoundError(
                f"Apollo oNoC benchmark 文件不存在: {path}。"
                f"请检查路径，或不传 path 参数以使用内置默认拓扑。"
            )
        loaded = _load_file(p, "auto")
        loaded.benchmark_source = BenchmarkSource.APOLLO
        loaded.target_metric = TargetMetric.ROUTING_SUCCESS_RATE
        return loaded
    return circuit


def load_lidar_benchmark(path: str | Path | None = None) -> CircuitSpec:
    """加载 LiDAR ISPD'25 benchmark（光子曲线布线对照）。

    LiDAR 是 ASU ISPD 2025 的光子曲线布线 benchmark，
    用于测试 curvy A* 布线算法。

    默认返回真实 LiDAR PTC 拓扑（12 器件 + 13 连接，P1-5 第25轮深化），
    若提供 path 则从文件加载并覆盖 benchmark_source。

    来源: https://dl.acm.org/doi/pdf/10.1145/3698364.3705355
         LiDAR: Curvy Waveguide Routing for Photonic Integrated Circuits,
         ASU ISPD 2025
         代码: https://github.com/ScopeX-ASU/LiDAR

    Args:
        path: LiDAR benchmark 文件路径（可选）。

    Returns:
        CircuitSpec，benchmark_source=LIDAR，target_metric=ROUTING_SUCCESS_RATE。
    """
    from polaris.data.lidar_benchmark import load_lidar_ptc_benchmark
    from polaris.data.specs import BenchmarkSource, TargetMetric

    circuit = load_lidar_ptc_benchmark()
    if path is not None:
        p = Path(path)
        if not p.exists():
            # R03: 用户指定 path 但文件不存在，禁止静默 fall-back 到默认拓扑
            raise FileNotFoundError(
                f"LiDAR benchmark 文件不存在: {path}。"
                f"请检查路径，或不传 path 参数以使用内置默认拓扑。"
            )
        loaded = _load_file(p, "auto")
        loaded.benchmark_source = BenchmarkSource.LIDAR
        loaded.target_metric = TargetMetric.ROUTING_SUCCESS_RATE
        return loaded
    return circuit


def generate_synthetic_benchmark(
    benchmark_type: str,
    num_devices: int = 10,
) -> CircuitSpec:
    """生成合成 benchmark 电路（P1-5，第9轮）。

    当无法获取真实 benchmark 数据（需 NDA 或 GitHub 下载）时，
    生成合成电路用于 CI 回归测试与算法验证。合成电路模拟真实
    benchmark 的拓扑结构，但规模较小（默认 10 器件）。

    支持的 benchmark 类型：
    - ``tilos_ariane``：电子芯片网格布局（模拟 RISC-V CPU 模块）
    - ``apollo_ptc``：光子 MZI 阵列（模拟张量核心矩阵乘法器）
    - ``apollo_onoc``：光子星型网络（模拟片上光网络）
    - ``lidar``：光子链式布线（模拟曲线波导布线）

    来源:
    - TILOS Ariane: https://github.com/TILOS-AI-CAD-Institute/MacroPlacement
    - Apollo PTC/oNoC: https://github.com/ASU-LOPE-Group/Apollo
    - LiDAR ISPD'25: https://dl.acm.org/doi/pdf/10.1145/3698364.3705355

    Args:
        benchmark_type: benchmark 类型（tilos_ariane/apollo_ptc/apollo_onoc/lidar）。
        num_devices: 合成器件数量（默认 10）。

    Returns:
        合成 CircuitSpec，含器件与连接。

    Raises:
        ValueError: 不支持的 benchmark 类型。
    """
    generators = {
        "tilos_ariane": _gen_tilos_ariane,
        "apollo_ptc": _gen_apollo_ptc,
        "apollo_onoc": _gen_apollo_onoc,
        "lidar": _gen_lidar,
    }
    if benchmark_type not in generators:
        raise ValueError(
            f"不支持的 benchmark 类型: {benchmark_type}，支持: {list(generators.keys())}"
        )
    return generators[benchmark_type](num_devices)


def _make_device_spec(
    name: str,
    device_type: str,
    width: float = 10.0,
    height: float = 10.0,
) -> DeviceSpec:
    """构造合成 DeviceSpec（含标准 in/out 端口）。

    device_type 会通过 ``_LIDAR_TO_POLARIS_DEVICE_MAP`` 映射到 catalog
    中的标准器件名，确保 ``circuit_spec_to_netlist_dict`` 转换后能被
    ``instantiate_devices`` 正确实例化。
    """
    # 映射到 catalog 中的标准器件名（与 circuit_spec_to_netlist_dict 一致）
    catalog_name = _LIDAR_TO_POLARIS_DEVICE_MAP.get(device_type, device_type)
    return DeviceSpec(
        name=name,
        device_type=catalog_name,
        width_um=width,
        height_um=height,
        ports=[
            ("in", 0.0, height / 2, "WEST"),
            ("out", width, height / 2, "EAST"),
        ],
    )


def _gen_tilos_ariane(num_devices: int) -> CircuitSpec:
    """生成 TILOS Ariane 合成 benchmark（电子芯片网格布局）。

    模拟 RISC-V CPU 模块的网格状连接拓扑。
    """
    from polaris.data.specs import BenchmarkSource, TargetMetric

    devices = [
        _make_device_spec(f"mod_{i}", "straight", width=20.0, height=20.0)
        for i in range(num_devices)
    ]
    # 网格连接：mod_i.out → mod_{i+1}.in
    connections = [(f"mod_{i}", "out", f"mod_{i + 1}", "in") for i in range(num_devices - 1)]
    return CircuitSpec(
        name="tilos_ariane_synthetic",
        devices=devices,
        connections=connections,
        canvas_w=1000.0,
        canvas_h=1000.0,
        benchmark_source=BenchmarkSource.TILOS,
        process_node="NanGate45",
        target_metric=TargetMetric.HPWL,
        target_value=100000.0,
    )


def _gen_apollo_ptc(num_devices: int) -> CircuitSpec:
    """生成 Apollo PTC 合成 benchmark（光子 MZI 阵列）。

    模拟光子张量核心的 MZI 矩阵乘法器拓扑。
    """
    from polaris.data.specs import BenchmarkSource, TargetMetric

    devices = [
        _make_device_spec(f"mzi_{i}", "mzi", width=15.0, height=10.0) for i in range(num_devices)
    ]
    # MZI 阵列连接：mzi_i.out → mzi_{i+2}.in（交叉连接模拟矩阵乘法）
    connections = [(f"mzi_{i}", "out", f"mzi_{i + 2}", "in") for i in range(num_devices - 2)]
    return CircuitSpec(
        name="apollo_ptc_synthetic",
        devices=devices,
        connections=connections,
        canvas_w=800.0,
        canvas_h=600.0,
        benchmark_source=BenchmarkSource.APOLLO,
        process_node="220nm SOI",
        optical_wavelength_nm=1550.0,
        target_metric=TargetMetric.INSERTION_LOSS_DB,
        target_value=5.0,
    )


def _gen_apollo_onoc(num_devices: int) -> CircuitSpec:
    """生成 Apollo oNoC 合成 benchmark（光子星型网络）。

    模拟片上光网络的星型拓扑（中心路由器 + 叶节点）。
    """
    from polaris.data.specs import BenchmarkSource, TargetMetric

    # 中心路由器 + 叶节点
    devices = [_make_device_spec("router_0", "mmi", width=30.0, height=30.0)]
    devices.extend(
        _make_device_spec(f"node_{i}", "straight", width=10.0, height=10.0)
        for i in range(1, num_devices)
    )
    # 星型连接：router_0.out → node_i.in
    connections = [("router_0", "out", f"node_{i}", "in") for i in range(1, num_devices)]
    return CircuitSpec(
        name="apollo_onoc_synthetic",
        devices=devices,
        connections=connections,
        canvas_w=1200.0,
        canvas_h=1200.0,
        benchmark_source=BenchmarkSource.APOLLO,
        process_node="220nm SOI",
        optical_wavelength_nm=1550.0,
        target_metric=TargetMetric.ROUTING_SUCCESS_RATE,
        target_value=0.95,
    )


def _gen_lidar(num_devices: int) -> CircuitSpec:
    """生成 LiDAR 合成 benchmark（光子链式布线）。

    模拟 LiDAR ISPD'25 的链式波导布线拓扑。
    """
    from polaris.data.specs import BenchmarkSource, TargetMetric

    devices = [
        _make_device_spec(f"wg_{i}", "straight", width=10.0, height=5.0) for i in range(num_devices)
    ]
    # 链式连接：wg_i.out → wg_{i+1}.in
    connections = [(f"wg_{i}", "out", f"wg_{i + 1}", "in") for i in range(num_devices - 1)]
    return CircuitSpec(
        name="lidar_ispd25_synthetic",
        devices=devices,
        connections=connections,
        canvas_w=500.0,
        canvas_h=500.0,
        benchmark_source=BenchmarkSource.LIDAR,
        process_node="220nm SOI",
        optical_wavelength_nm=1550.0,
        target_metric=TargetMetric.ROUTING_SUCCESS_RATE,
        target_value=1.0,
    )


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
    "generate_synthetic_benchmark",
]
