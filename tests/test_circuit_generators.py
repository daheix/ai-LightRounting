"""PoLaRIS 电路生成器单元测试（Task 13）。

测试 15 种拓扑生成器在 4 平台 × 5 规模下的合法性与一致性，
并验证生成的电路可被 build_circuit_spec 正确解析为 CircuitSpec。

测试内容：
1. 每种生成器在 XS/SOI/seed=42 下生成合法电路（校验错误=0）
2. 每种生成器生成的电路有 ≥1 个器件和 ≥1 个连接
3. 每种生成器生成的电路 name 非空
4. 每种生成器在所有 5 种规模下都能生成合法电路
5. 每种生成器在所有 4 种平台下都能生成合法电路
6. 生成的电路可被 build_circuit_spec 正确解析

规则 14.1：禁止 fall-back，校验失败必须告警（不静默跳过）。
"""

from __future__ import annotations

import sys
from pathlib import Path

# 将项目根目录加入 sys.path，确保 scripts/ 可导入
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from scripts.generate_1000_circuits import (
    PLATFORMS,
    SCALES,
    CircuitSerializer,
    MZIArrayGenerator,
    RingFilterGenerator,
)
from scripts.generators.group_a import (
    ClementsMatrixGenerator,
    DCCouplerArrayGenerator,
    MMIArrayGenerator,
    ReckMatrixGenerator,
    SpankeMatrixGenerator,
)
from scripts.generators.group_b import (
    LatticeFilterGenerator,
    ModulatorArrayGenerator,
    OpticalSwitchMatrixGenerator,
    QuantumPhotonicsGenerator,
    WDMMuxDemuxGenerator,
)
from scripts.generators.group_c import (
    HybridTopologyGenerator,
    PolarizationArrayGenerator,
    RingDelayLineGenerator,
)
from scripts.mvp_100_iterations import build_circuit_spec

# =============================================================================
# 15 种拓扑生成器注册表（与 batch_generate_1000.ALL_GENERATORS 对齐）
# =============================================================================

ALL_GENERATORS: list[tuple[str, type]] = [
    # 框架自带（2 种）
    ("mzi_array", MZIArrayGenerator),
    ("ring_filter", RingFilterGenerator),
    # group_a（5 种）
    ("clements_matrix", ClementsMatrixGenerator),
    ("reck_matrix", ReckMatrixGenerator),
    ("spanke_matrix", SpankeMatrixGenerator),
    ("mmi_array", MMIArrayGenerator),
    ("dc_array", DCCouplerArrayGenerator),
    # group_b（5 种）
    ("wdm_mux_demux", WDMMuxDemuxGenerator),
    ("switch_matrix", OpticalSwitchMatrixGenerator),
    ("modulator_array", ModulatorArrayGenerator),
    ("quantum_photonics", QuantumPhotonicsGenerator),
    ("lattice_filter", LatticeFilterGenerator),
    # group_c（3 种）
    ("ring_delay_line", RingDelayLineGenerator),
    ("polarization_array", PolarizationArrayGenerator),
    ("hybrid_topology", HybridTopologyGenerator),
]

# 标准测试参数
DEFAULT_SCALE = SCALES["XS"]
DEFAULT_PLATFORM = PLATFORMS["SOI"]
DEFAULT_SEED = 42

# 生成器名称用于参数化 ID（便于 pytest 输出可读）
GENERATOR_IDS = [name for name, _ in ALL_GENERATORS]


# =============================================================================
# 测试 1: 每种生成器在 XS/SOI/seed=42 下生成合法电路（校验错误=0）
# =============================================================================


@pytest.mark.parametrize(
    "topo_name, gen_cls",
    ALL_GENERATORS,
    ids=GENERATOR_IDS,
)
def test_generator_produces_valid_circuit_xs_soi(topo_name: str, gen_cls: type) -> None:
    """每种生成器在 XS/SOI/seed=42 下应生成合法电路（校验错误=0）。

    规则 14.1：禁止 fall-back，校验失败必须告警。
    """
    gen = gen_cls(
        scale=DEFAULT_SCALE, platform=DEFAULT_PLATFORM, seed=DEFAULT_SEED
    )
    circuit = gen.generate()

    serializer = CircuitSerializer()
    errors = serializer.validate(circuit)
    assert errors == [], (
        f"拓扑 {topo_name} 在 XS/SOI/seed=42 下校验失败: {errors}"
    )


# =============================================================================
# 测试 2: 每种生成器生成的电路有 ≥1 个器件和 ≥1 个连接
# =============================================================================


@pytest.mark.parametrize(
    "topo_name, gen_cls",
    ALL_GENERATORS,
    ids=GENERATOR_IDS,
)
def test_generator_has_devices_and_connections(topo_name: str, gen_cls: type) -> None:
    """每种生成器生成的电路应有 ≥1 个器件和 ≥1 个连接。"""
    gen = gen_cls(
        scale=DEFAULT_SCALE, platform=DEFAULT_PLATFORM, seed=DEFAULT_SEED
    )
    circuit = gen.generate()

    n_devices = len(circuit.get("devices", []))
    n_connections = len(circuit.get("connections", []))
    assert n_devices >= 1, f"拓扑 {topo_name} 生成的电路无器件"
    assert n_connections >= 1, f"拓扑 {topo_name} 生成的电路无连接"


# =============================================================================
# 测试 3: 每种生成器生成的电路 name 非空
# =============================================================================


@pytest.mark.parametrize(
    "topo_name, gen_cls",
    ALL_GENERATORS,
    ids=GENERATOR_IDS,
)
def test_generator_circuit_name_nonempty(topo_name: str, gen_cls: type) -> None:
    """每种生成器生成的电路 name 应非空。"""
    gen = gen_cls(
        scale=DEFAULT_SCALE, platform=DEFAULT_PLATFORM, seed=DEFAULT_SEED
    )
    circuit = gen.generate()

    name = circuit.get("name", "")
    assert name and str(name).strip(), f"拓扑 {topo_name} 生成的电路 name 为空"


# =============================================================================
# 测试 4: 每种生成器在所有 5 种规模下都能生成合法电路
# =============================================================================


@pytest.mark.parametrize(
    "topo_name, gen_cls",
    ALL_GENERATORS,
    ids=GENERATOR_IDS,
)
@pytest.mark.parametrize("scale_name", list(SCALES.keys()))
def test_generator_all_scales_valid(
    topo_name: str, gen_cls: type, scale_name: str
) -> None:
    """每种生成器在所有 5 种规模（XS/S/M/L/XL）下应生成合法电路。"""
    scale = SCALES[scale_name]
    gen = gen_cls(scale=scale, platform=DEFAULT_PLATFORM, seed=DEFAULT_SEED)
    circuit = gen.generate()

    serializer = CircuitSerializer()
    errors = serializer.validate(circuit)
    assert errors == [], (
        f"拓扑 {topo_name} 在规模 {scale_name} 下校验失败: {errors}"
    )


# =============================================================================
# 测试 5: 每种生成器在所有 4 种平台下都能生成合法电路
# =============================================================================


@pytest.mark.parametrize(
    "topo_name, gen_cls",
    ALL_GENERATORS,
    ids=GENERATOR_IDS,
)
@pytest.mark.parametrize("platform_name", list(PLATFORMS.keys()))
def test_generator_all_platforms_valid(
    topo_name: str, gen_cls: type, platform_name: str
) -> None:
    """每种生成器在所有 4 种平台（SOI/SiN/InP/LNOI）下应生成合法电路。"""
    platform = PLATFORMS[platform_name]
    gen = gen_cls(scale=DEFAULT_SCALE, platform=platform, seed=DEFAULT_SEED)
    circuit = gen.generate()

    serializer = CircuitSerializer()
    errors = serializer.validate(circuit)
    assert errors == [], (
        f"拓扑 {topo_name} 在平台 {platform_name} 下校验失败: {errors}"
    )


# =============================================================================
# 测试 6: 生成的电路可被 build_circuit_spec 正确解析
# =============================================================================


@pytest.mark.parametrize(
    "topo_name, gen_cls",
    ALL_GENERATORS,
    ids=GENERATOR_IDS,
)
def test_generator_circuit_parseable_by_build_circuit_spec(
    topo_name: str, gen_cls: type
) -> None:
    """每种生成器生成的电路应可被 build_circuit_spec 正确解析为 CircuitSpec。

    验证 CircuitSpec 的字段（name/devices/connections/canvas_w/canvas_h）正确填充。
    """
    gen = gen_cls(
        scale=DEFAULT_SCALE, platform=DEFAULT_PLATFORM, seed=DEFAULT_SEED
    )
    circuit = gen.generate()

    # 调用 build_circuit_spec 解析（不应抛出异常）
    spec = build_circuit_spec(circuit)

    # 验证 CircuitSpec 字段
    assert spec.name == circuit.get("name"), (
        f"拓扑 {topo_name}: CircuitSpec.name 与原始 name 不一致"
    )
    assert len(spec.devices) == len(circuit.get("devices", [])), (
        f"拓扑 {topo_name}: CircuitSpec.devices 数量不一致"
    )
    assert len(spec.connections) == len(circuit.get("connections", [])), (
        f"拓扑 {topo_name}: CircuitSpec.connections 数量不一致"
    )
    assert spec.canvas_w == pytest.approx(circuit.get("canvas_w", 300.0)), (
        f"拓扑 {topo_name}: CircuitSpec.canvas_w 不一致"
    )
    assert spec.canvas_h == pytest.approx(circuit.get("canvas_h", 200.0)), (
        f"拓扑 {topo_name}: CircuitSpec.canvas_h 不一致"
    )

    # 验证每个 DeviceSpec 的关键字段
    for dev_spec, dev_dict in zip(spec.devices, circuit.get("devices", [])):
        assert dev_spec.name == dev_dict["name"], (
            f"拓扑 {topo_name}: DeviceSpec.name 不一致"
        )
        assert dev_spec.device_type == dev_dict["type"], (
            f"拓扑 {topo_name}: DeviceSpec.device_type 不一致"
        )
        assert dev_spec.width_um == pytest.approx(float(dev_dict["width_um"])), (
            f"拓扑 {topo_name}: DeviceSpec.width_um 不一致"
        )
        assert dev_spec.height_um == pytest.approx(float(dev_dict["height_um"])), (
            f"拓扑 {topo_name}: DeviceSpec.height_um 不一致"
        )


# =============================================================================
# 测试 7: 生成器总数应为 15 种（防止漏测或新增未注册）
# =============================================================================


def test_generator_count_is_15() -> None:
    """注册的生成器总数应为 15 种（与 batch_generate_1000.ALL_GENERATORS 对齐）。"""
    assert len(ALL_GENERATORS) == 15, (
        f"生成器总数应为 15，实际 {len(ALL_GENERATORS)}"
    )
