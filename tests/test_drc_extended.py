"""DRC 约束检查器测试（覆盖新增 8 项 DRC 检查）。

测试覆盖:
- check_waveguide_length: 最小/最大波导长度
- check_min_area: 最小器件面积
- check_port_connectivity: 端口连接性
- check_layer_density: 层密度
- check_thermal: 热串扰
- check_crosstalk: 串扰
- ConstraintChecker.check 综合检查（含可选 DRC）
- Device.process_node 字段（P1-3）
- CircuitSpec.benchmark_source 字段（P1-5）

来源:
- SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- 差距分析 P0-1/P1-3/P1-5
"""

from __future__ import annotations

from polaris.data.specs import BenchmarkSource, CircuitSpec, DeviceSpec, TargetMetric
from polaris.pdk.catalog import DeviceCatalog
from polaris.pdk.device import Device
from polaris.sim.constraint_checker import (
    CheckContext,
    ConstraintChecker,
    ViolationType,
    check_crosstalk,
    check_layer_density,
    check_min_area,
    check_port_connectivity,
    check_thermal,
    check_waveguide_length,
)


def test_check_waveguide_length_min():
    """测试最小波导长度检查。"""
    lengths = {"net1": 1.0, "net2": 5.0}  # net1 < min 2.0
    violations = check_waveguide_length(lengths, min_length=2.0, max_length=10000.0)
    assert len(violations) == 1
    assert violations[0].vtype == ViolationType.MIN_LENGTH
    assert violations[0].net_id == "net1"


def test_check_waveguide_length_max():
    """测试最大波导长度检查。"""
    lengths = {"net1": 15000.0, "net2": 100.0}  # net1 > max 10000
    violations = check_waveguide_length(lengths, min_length=2.0, max_length=10000.0)
    assert len(violations) == 1
    assert violations[0].vtype == ViolationType.MAX_LENGTH
    assert violations[0].net_id == "net1"


def test_check_waveguide_length_ok():
    """测试波导长度合规。"""
    lengths = {"net1": 50.0, "net2": 100.0}
    violations = check_waveguide_length(lengths, min_length=2.0, max_length=10000.0)
    assert len(violations) == 0


def test_check_minarea_violation():
    """测试最小面积检查。"""
    areas = {"dev1": 0.05, "dev2": 1.0}  # dev1 < min 0.1
    violations = check_min_area(areas, min_area=0.1)
    assert len(violations) == 1
    assert violations[0].vtype == ViolationType.MIN_AREA
    assert violations[0].device_name == "dev1"


def test_check_port_connectivity():
    """测试端口连接性检查。"""
    connections = {"dev1::port1": True, "dev1::port2": False}
    violations = check_port_connectivity(connections)
    assert len(violations) == 1
    assert violations[0].vtype == ViolationType.PORT_CONNECTIVITY
    assert "dev1::port2" not in violations[0].message or "port2" in violations[0].message


def test_check_layer_density():
    """测试层密度检查。"""
    densities = {"WG": 0.9, "M1": 0.5}  # WG > max 0.85
    violations = check_layer_density(densities, max_density=0.85)
    assert len(violations) == 1
    assert violations[0].vtype == ViolationType.LAYER_DENSITY
    assert violations[0].device_name == "WG"


def test_check_thermal():
    """测试热串扰检查。"""
    placements = {
        "heater1": {"x": 0, "y": 0, "w": 10, "h": 10},
        "ring1": {"x": 15, "y": 0, "w": 10, "h": 10},  # gap=5 < safe 100
    }
    violations = check_thermal(placements, safe_distance=100.0)
    assert len(violations) >= 1
    assert all(v.vtype == ViolationType.THERMAL for v in violations)


def test_check_crosstalk():
    """测试串扰检查。"""
    paths = {
        "net1": [(0, 0), (0, 100)],  # 垂直波导
        "net2": [(1, 0), (1, 100)],  # 平行间距 1μm < safe 2μm
    }
    violations = check_crosstalk({}, paths, max_crosstalk_db=-20.0)
    assert len(violations) >= 1
    assert all(v.vtype == ViolationType.CROSSTALK for v in violations)


def test_constraint_checker_with_optional_drc():
    """测试 ConstraintChecker 综合检查含可选 DRC。"""
    placements = {
        "dev1": {"x": 0, "y": 0, "w": 20, "h": 20},
        "dev2": {"x": 50, "y": 50, "w": 20, "h": 20},
    }
    paths = {"net1": [(10, 10), (50, 50)]}
    context = CheckContext(
        waveguide_widths={"net1": 0.5},
        waveguide_lengths={"net1": 50.0},
        device_areas={"dev1": 400.0},
        port_connections={"dev1::in": True},
        layer_densities={"WG": 0.5},
    )
    checker = ConstraintChecker()
    violations = checker.check(placements, paths, context)
    # 应无违规（所有值都在阈值内）
    assert len(violations) == 0


def test_constraint_checker_min_width_violation():
    """测试 ConstraintChecker 检测最小宽度违规。"""
    context = CheckContext(waveguide_widths={"net1": 0.3})  # < min 0.4
    checker = ConstraintChecker()
    violations = checker.check({}, {}, context)
    assert any(v.vtype == ViolationType.MIN_WIDTH for v in violations)


def test_device_process_node_field():
    """测试 Device.process_node 字段（P1-3）。"""
    from polaris.pdk.device import BoundingBox

    dev = Device(
        device_id="test",
        platform="SOI",
        category="passive",
        name="waveguide",
        ports=[],
        bbox=BoundingBox(0, 0, 10, 1),
        process_node="220nm SOI",
    )
    assert dev.process_node == "220nm SOI"


def test_device_process_node_default_none():
    """测试 Device.process_node 默认为 None。"""
    from polaris.pdk.device import BoundingBox

    dev = Device(
        device_id="test",
        platform="SOI",
        category="passive",
        name="waveguide",
        ports=[],
        bbox=BoundingBox(0, 0, 10, 1),
    )
    assert dev.process_node is None


def test_catalog_auto_fill_process_node():
    """测试 DeviceCatalog 自动填充 process_node（P1-3）。"""
    catalog = DeviceCatalog()
    catalog.register_all_builtin()
    soi_devices = [d for d in catalog.list_devices() if d.platform == "SOI"]
    assert len(soi_devices) > 0
    # 所有 SOI 器件应有 process_node
    for dev in soi_devices:
        assert dev.process_node == "220nm SOI", f"{dev.name} 缺少 process_node"


def test_circuit_spec_benchmark_source():
    """测试 CircuitSpec.benchmark_source 字段（P1-5）。"""
    circuit = CircuitSpec(
        name="test",
        benchmark_source=BenchmarkSource.TILOS,
        process_node="NanGate45",
        target_metric=TargetMetric.HPWL,
        target_value=100000.0,
    )
    assert circuit.benchmark_source == BenchmarkSource.TILOS
    assert circuit.process_node == "NanGate45"
    assert circuit.target_metric == TargetMetric.HPWL


def test_device_spec_process_node():
    """测试 DeviceSpec.process_node 字段（P1-3）。"""
    dev = DeviceSpec(name="wg", device_type="waveguide", process_node="220nm SOI")
    assert dev.process_node == "220nm SOI"


def test_load_tilos_ariane():
    """测试 TILOS Ariane benchmark 加载器（P1-5）。"""
    from polaris.data.data_loader import load_tilos_ariane

    circuit = load_tilos_ariane()
    assert circuit.benchmark_source == BenchmarkSource.TILOS
    assert circuit.name == "tilos_ariane"
    assert circuit.target_metric == TargetMetric.HPWL


def test_load_apollo_ptc():
    """测试 Apollo PTC benchmark 加载器（P1-5）。"""
    from polaris.data.data_loader import load_apollo_ptc

    circuit = load_apollo_ptc()
    assert circuit.benchmark_source == BenchmarkSource.APOLLO
    assert circuit.name == "apollo_ptc"
    assert circuit.target_metric == TargetMetric.INSERTION_LOSS_DB


def test_load_apollo_onoc():
    """测试 Apollo oNoC benchmark 加载器（P1-5）。"""
    from polaris.data.data_loader import load_apollo_onoc

    circuit = load_apollo_onoc()
    assert circuit.benchmark_source == BenchmarkSource.APOLLO
    assert circuit.name == "apollo_onoc"
    assert circuit.target_metric == TargetMetric.ROUTING_SUCCESS_RATE


def test_load_lidar_benchmark():
    """测试 LiDAR benchmark 加载器（P1-5）。"""
    from polaris.data.data_loader import load_lidar_benchmark

    circuit = load_lidar_benchmark()
    assert circuit.benchmark_source == BenchmarkSource.LIDAR
    # 第25轮深化：load_lidar_benchmark 返回真实 PTC 拓扑（lidar_ptc）
    assert circuit.name == "lidar_ptc"
