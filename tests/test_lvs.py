"""LVS（Layout Versus Schematic）基础实现测试（第3轮 P0-1）。

测试覆盖:
- LVSMismatchType/LVSMismatch/LVSReport dataclass
- ExtractedNetlist dataclass
- extract_netlist_from_gds: 从 GDS 提取网表
- circuit_spec_to_netlist: CircuitSpec → 参考网表
- compare_netlists: 网表比对
- run_lvs: 顶层 LVS 函数

来源:
- KLayout LVS API: https://www.klayout.org/doc-qt5/manual/lvs.html
- SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
"""

from __future__ import annotations

from pathlib import Path

import klayout.db as db
import pytest

from polaris.data.specs import CircuitSpec, DeviceSpec
from polaris.pdk.layer_map import get_layer_tuple
from polaris.sim.lvs import (
    ExtractedNetlist,
    LVSMismatch,
    LVSMismatchType,
    LVSReport,
    circuit_spec_to_netlist,
    compare_netlists,
    extract_netlist_from_gds,
    run_lvs,
)

# -- dataclass 测试 --


def test_lvs_mismatch_type_enum():
    """测试 LVSMismatchType 枚举完整性。"""
    assert LVSMismatchType.MISSING_DEVICE.value == "missing_device"
    assert LVSMismatchType.EXTRA_DEVICE.value == "extra_device"
    assert LVSMismatchType.DEVICE_TYPE_MISMATCH.value == "device_type_mismatch"
    assert LVSMismatchType.MISSING_CONNECTION.value == "missing_connection"
    assert LVSMismatchType.EXTRA_CONNECTION.value == "extra_connection"
    assert LVSMismatchType.PORT_MISMATCH.value == "port_mismatch"


def test_lvs_mismatch_dataclass():
    """测试 LVSMismatch dataclass。"""
    mismatch = LVSMismatch(
        mtype=LVSMismatchType.MISSING_DEVICE,
        message="测试缺失器件",
        device_name="wg1",
    )
    assert mismatch.mtype == LVSMismatchType.MISSING_DEVICE
    assert mismatch.message == "测试缺失器件"
    assert mismatch.device_name == "wg1"
    assert mismatch.net_name == ""


def test_lvs_report_dataclass():
    """测试 LVSReport dataclass。"""
    report = LVSReport()
    assert not report.is_match
    assert report.mismatch_count == 0
    assert report.reference_device_count == 0


def test_lvs_report_with_mismatches():
    """测试 LVSReport 含不匹配项。"""
    report = LVSReport(
        is_match=False,
        mismatches=[
            LVSMismatch(mtype=LVSMismatchType.MISSING_DEVICE, message="缺失"),
            LVSMismatch(mtype=LVSMismatchType.EXTRA_DEVICE, message="多余"),
        ],
        reference_device_count=5,
        extracted_device_count=4,
    )
    assert not report.is_match
    assert report.mismatch_count == 2


def test_extracted_netlist_dataclass():
    """测试 ExtractedNetlist dataclass。"""
    netlist = ExtractedNetlist(
        devices=["wg1", "mzi1"],
        connections=[("wg1", "mzi1")],
    )
    assert len(netlist.devices) == 2
    assert len(netlist.connections) == 1


# -- circuit_spec_to_netlist 测试 --


def test_circuit_spec_to_netlist_empty():
    """测试空 CircuitSpec 转换。"""
    circuit = CircuitSpec(name="empty")
    netlist = circuit_spec_to_netlist(circuit)
    assert len(netlist.devices) == 0
    assert len(netlist.connections) == 0


def test_circuit_spec_to_netlist_with_devices():
    """测试含器件的 CircuitSpec 转换。"""
    circuit = CircuitSpec(
        name="test",
        devices=[
            DeviceSpec(name="wg1", device_type="waveguide"),
            DeviceSpec(name="mzi1", device_type="mzi"),
        ],
        connections=[("wg1", "out", "mzi1", "in")],
    )
    netlist = circuit_spec_to_netlist(circuit)
    assert netlist.devices == ["wg1", "mzi1"]
    assert netlist.connections == [("wg1", "mzi1")]


# -- compare_netlists 测试 --


def test_compare_netlists_match():
    """测试完全匹配的网表比对。"""
    reference = ExtractedNetlist(devices=["wg1", "mzi1"], connections=[("wg1", "mzi1")])
    extracted = ExtractedNetlist(devices=["wg1", "mzi1"], connections=[("wg1", "mzi1")])
    report = compare_netlists(reference, extracted)
    assert report.is_match
    assert report.mismatch_count == 0


def test_compare_netlists_missing_device():
    """测试缺失器件的网表比对。"""
    reference = ExtractedNetlist(devices=["wg1", "mzi1", "ring1"])
    extracted = ExtractedNetlist(devices=["wg1", "mzi1"])
    report = compare_netlists(reference, extracted)
    assert not report.is_match
    missing = [m for m in report.mismatches if m.mtype == LVSMismatchType.MISSING_DEVICE]
    assert len(missing) == 1
    assert missing[0].device_name == "ring1"


def test_compare_netlists_extra_device():
    """测试多余器件的网表比对。"""
    reference = ExtractedNetlist(devices=["wg1"])
    extracted = ExtractedNetlist(devices=["wg1", "extra1"])
    report = compare_netlists(reference, extracted)
    assert not report.is_match
    extra = [m for m in report.mismatches if m.mtype == LVSMismatchType.EXTRA_DEVICE]
    assert len(extra) == 1
    assert extra[0].device_name == "extra1"


def test_compare_netlists_missing_connection():
    """测试缺失连接的网表比对。"""
    reference = ExtractedNetlist(
        devices=["wg1", "mzi1", "ring1"],
        connections=[("wg1", "mzi1"), ("mzi1", "ring1")],
    )
    extracted = ExtractedNetlist(
        devices=["wg1", "mzi1", "ring1"],
        connections=[("wg1", "mzi1")],
    )
    report = compare_netlists(reference, extracted)
    assert not report.is_match
    missing = [m for m in report.mismatches if m.mtype == LVSMismatchType.MISSING_CONNECTION]
    assert len(missing) == 1


def test_compare_netlists_extra_connection():
    """测试多余连接的网表比对。"""
    reference = ExtractedNetlist(
        devices=["wg1", "mzi1"],
        connections=[("wg1", "mzi1")],
    )
    extracted = ExtractedNetlist(
        devices=["wg1", "mzi1"],
        connections=[("wg1", "mzi1"), ("mzi1", "wg1")],
    )
    report = compare_netlists(reference, extracted)
    assert not report.is_match
    extra = [m for m in report.mismatches if m.mtype == LVSMismatchType.EXTRA_CONNECTION]
    assert len(extra) == 1


# -- extract_netlist_from_gds 测试 --


@pytest.fixture
def gds_with_devrec(tmp_path: Path) -> Path:
    """生成含 DEVREC 层的 GDS 文件。"""
    gds_path = tmp_path / "lvs_test.gds"
    layout = db.Layout()
    layout.dbu = 0.001
    cell = layout.create_cell("LVS_TEST")
    # 画 DEVREC 层（layer 68）标记器件
    devrec_layer = get_layer_tuple("DEVREC")
    devrec_idx = layout.layer(db.LayerInfo(devrec_layer[0], devrec_layer[1]))
    # 两个器件区域
    cell.shapes(devrec_idx).insert(db.DPolygon(db.DBox(0, 0, 10, 10)))
    cell.shapes(devrec_idx).insert(db.DPolygon(db.DBox(20, 0, 30, 10)))
    # 画 WG 层连接
    wg_layer = get_layer_tuple("WG")
    wg_idx = layout.layer(db.LayerInfo(wg_layer[0], wg_layer[1]))
    cell.shapes(wg_idx).insert(db.DPolygon(db.DBox(10, 4, 20, 6)))
    layout.write(str(gds_path))
    return gds_path


@pytest.fixture
def gds_empty(tmp_path: Path) -> Path:
    """生成空 GDS 文件（无 DEVREC 层）。"""
    gds_path = tmp_path / "empty.gds"
    layout = db.Layout()
    layout.dbu = 0.001
    layout.create_cell("EMPTY")
    layout.write(str(gds_path))
    return gds_path


def test_extract_netlist_from_gds_with_devrec(gds_with_devrec: Path):
    """测试从含 DEVREC 的 GDS 提取网表。"""
    netlist = extract_netlist_from_gds(gds_with_devrec)
    assert len(netlist.devices) == 2  # 两个 DEVREC 区域
    # 有 WG 层，应有连接
    assert len(netlist.connections) >= 1


def test_extract_netlist_from_gds_empty(gds_empty: Path):
    """测试从空 GDS 提取网表。"""
    netlist = extract_netlist_from_gds(gds_empty)
    assert len(netlist.devices) == 0
    assert len(netlist.connections) == 0


def test_extract_netlist_file_not_found():
    """测试 GDS 文件不存在时抛出 FileNotFoundError。"""
    with pytest.raises(FileNotFoundError):
        extract_netlist_from_gds("/nonexistent/path.gds")


# -- run_lvs 测试 --


def test_run_lvs_match(gds_with_devrec: Path):
    """测试 LVS 完全匹配（参考网表与 GDS 一致）。"""
    # 构造与 GDS 一致的参考电路
    circuit = CircuitSpec(
        name="lvs_test",
        devices=[
            DeviceSpec(name="device_0", device_type="waveguide"),
            DeviceSpec(name="device_1", device_type="waveguide"),
        ],
    )
    report = run_lvs(gds_with_devrec, circuit)
    # 器件应匹配（device_0, device_1）
    assert report.reference_device_count == 2
    assert report.extracted_device_count == 2


def test_run_lvs_missing_device(gds_with_devrec: Path):
    """测试 LVS 检测到缺失器件。"""
    # 参考电路有 3 个器件，但 GDS 只有 2 个
    circuit = CircuitSpec(
        name="lvs_test",
        devices=[
            DeviceSpec(name="device_0", device_type="waveguide"),
            DeviceSpec(name="device_1", device_type="waveguide"),
            DeviceSpec(name="device_2", device_type="ring"),  # GDS 中不存在
        ],
    )
    report = run_lvs(gds_with_devrec, circuit)
    assert not report.is_match
    missing = [m for m in report.mismatches if m.mtype == LVSMismatchType.MISSING_DEVICE]
    assert len(missing) == 1
    assert missing[0].device_name == "device_2"


def test_run_lvs_extra_device(gds_with_devrec: Path):
    """测试 LVS 检测到多余器件。"""
    # 参考电路只有 1 个器件，但 GDS 有 2 个
    circuit = CircuitSpec(
        name="lvs_test",
        devices=[DeviceSpec(name="device_0", device_type="waveguide")],
    )
    report = run_lvs(gds_with_devrec, circuit)
    assert not report.is_match
    extra = [m for m in report.mismatches if m.mtype == LVSMismatchType.EXTRA_DEVICE]
    assert len(extra) == 1
    assert extra[0].device_name == "device_1"


def test_run_lvs_empty_gds(gds_empty: Path):
    """测试对空 GDS 运行 LVS。"""
    circuit = CircuitSpec(
        name="empty",
        devices=[DeviceSpec(name="wg1", device_type="waveguide")],
    )
    report = run_lvs(gds_empty, circuit)
    assert not report.is_match
    # 参考有 1 个器件，GDS 提取 0 个
    assert report.reference_device_count == 1
    assert report.extracted_device_count == 0
