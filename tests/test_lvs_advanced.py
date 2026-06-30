"""LVS 进阶功能测试（批次 7-B，R181-R187）。

测试覆盖：
- R181 波导提取增强（直波导/弯曲波导/锥形波导参数提取）
- R182 定向耦合器提取（耦合长度/耦合间距）
- R183 MMI 提取（尺寸/端口数）
- R184 环形谐振器提取（半径/耦合间距）
- R185 连接性提取（悬浮节点检测）
- R186 器件匹配增强（容差比对/多余缺失器件）
- R187 错误报告增强（坐标定位/结构化报告）

来源：
- KLayout LVS: https://www.klayout.org/doc-qt5/manual/lvs.html
- SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- Cadence Pegasus LVS: https://community.cadence.com/cadence_blogs_8/b/di/posts/pegasus-get-your-wings-pegasus-results-viewer--lvs
- Calibre nmLVS: https://eda.sw.siemens.com/en-US/calibre/
- Ansys Lumerical Ring Resonator: https://optics.ansys.com/hc/en-us/articles/360042800213
"""

from __future__ import annotations

from pathlib import Path

import klayout.db as db
import numpy as np
import pytest

from polaris.data.specs import CircuitSpec, DeviceSpec
from polaris.pdk.layer_map import get_layer_tuple
from polaris.sim.lvs import ExtractedNetlist, LVSMismatchType
from polaris.sim.lvs_advanced import (
    ConnectivityReport,
    DeviceMatchResult,
    DirectionalCouplerParams,
    LocatedError,
    MMIParams,
    ParamMismatch,
    RingResonatorParams,
    StructuredErrorReport,
    ToleranceSpec,
    WaveguideParams,
    extract_connectivity,
    extract_directional_couplers,
    extract_mmis,
    extract_ring_resonators,
    extract_waveguide_params,
    generate_structured_error_report,
    match_devices_with_tolerance,
)


# ============================================================
# GDS Fixture 辅助函数
# ============================================================


def _new_layout() -> tuple[db.Layout, db.Cell]:
    """创建新 Layout（dbu=1nm）。"""
    layout = db.Layout()
    layout.dbu = 0.001
    cell = layout.create_cell("TEST")
    return layout, cell


def _wg_layer_idx(layout: db.Layout) -> int:
    """获取 WG 层索引。"""
    wg = get_layer_tuple("WG")
    return layout.layer(db.LayerInfo(wg[0], wg[1]))


def _devrec_layer_idx(layout: db.Layout) -> int:
    """获取 DEVREC 层索引。"""
    dr = get_layer_tuple("DEVREC")
    return layout.layer(db.LayerInfo(dr[0], dr[1]))


def _write_gds(layout: db.Layout, tmp_path: Path, name: str) -> Path:
    """写入 GDS 文件。"""
    gds = tmp_path / name
    layout.write(str(gds))
    return gds


def _insert_rect(
    cell: db.Cell, layer_idx: int, x1: float, y1: float, x2: float, y2: float
) -> None:
    """插入矩形（μm 坐标）。"""
    cell.shapes(layer_idx).insert(db.DPolygon(db.DBox(x1, y1, x2, y2)))


def _insert_polygon(cell: db.Cell, layer_idx: int, pts: list[tuple[float, float]]) -> None:
    """插入多边形（μm 坐标）。"""
    dpoly = db.DPolygon([db.DPoint(float(x), float(y)) for x, y in pts])
    cell.shapes(layer_idx).insert(dpoly)


def _make_bend_pts(
    cx: float, cy: float, radius: float, width: float, n: int = 16
) -> list[tuple[float, float]]:
    """生成四分之一环形弯曲波导顶点（0° → 90°）。"""
    r_in = radius - width / 2
    r_out = radius + width / 2
    pts: list[tuple[float, float]] = []
    for i in range(n + 1):
        a = np.pi / 2 * i / n
        pts.append((cx + r_out * np.cos(a), cy + r_out * np.sin(a)))
    for i in range(n + 1):
        a = np.pi / 2 - np.pi / 2 * i / n
        pts.append((cx + r_in * np.cos(a), cy + r_in * np.sin(a)))
    return pts


def _make_ring_pts(
    cx: float, cy: float, radius: float, width: float, n: int = 32
) -> list[tuple[float, float]]:
    """生成环形谐振器顶点（近全角，留小缝隙）。"""
    r_in = radius - width / 2
    r_out = radius + width / 2
    span = 2 * np.pi * 0.98
    pts: list[tuple[float, float]] = []
    for i in range(n + 1):
        a = span * i / n
        pts.append((cx + r_out * np.cos(a), cy + r_out * np.sin(a)))
    for i in range(n + 1):
        a = span - span * i / n
        pts.append((cx + r_in * np.cos(a), cy + r_in * np.sin(a)))
    return pts


# ============================================================
# R181 波导提取增强测试
# ============================================================


@pytest.fixture
def gds_waveguides(tmp_path: Path) -> Path:
    """生成含直波导/弯曲波导/锥形波导的 GDS。"""
    layout, cell = _new_layout()
    wg_idx = _wg_layer_idx(layout)
    # 直波导 100μm × 0.5μm
    _insert_rect(cell, wg_idx, 0, 0, 100, 0.5)
    # 弯曲波导：四分之一环，半径 5μm，宽 0.5μm，中心 (120, 0)
    _insert_polygon(cell, wg_idx, _make_bend_pts(120, 0, 5, 0.5))
    # 锥形波导：梯形 50μm 长，0.5μm → 2.0μm
    _insert_polygon(
        cell, wg_idx, [(0, 50), (0, 50.5), (50, 52), (50, 50)]
    )
    return _write_gds(layout, tmp_path, "waveguides.gds")


def test_r181_straight_waveguide_extraction(gds_waveguides: Path):
    """R181：直波导宽度/长度提取。"""
    wgs = extract_waveguide_params(gds_waveguides)
    straight = [w for w in wgs if w.wg_type == "straight"]
    assert len(straight) >= 1
    wg = straight[0]
    assert wg.length_um == pytest.approx(100.0, abs=0.1)
    assert wg.width_um == pytest.approx(0.5, abs=0.05)


def test_r181_bend_waveguide_extraction(gds_waveguides: Path):
    """R181：弯曲波导曲率半径/弧长提取。"""
    wgs = extract_waveguide_params(gds_waveguides)
    bends = [w for w in wgs if w.wg_type == "bend"]
    assert len(bends) >= 1
    bend = bends[0]
    assert bend.radius_um == pytest.approx(5.0, abs=0.3)
    assert bend.width_um == pytest.approx(0.5, abs=0.1)
    expected_arc = np.pi * 5.0 / 2
    assert bend.length_um == pytest.approx(expected_arc, abs=0.5)


def test_r181_taper_waveguide_extraction(gds_waveguides: Path):
    """R181：锥形波导两端宽度提取。"""
    wgs = extract_waveguide_params(gds_waveguides)
    tapers = [w for w in wgs if w.wg_type == "taper"]
    assert len(tapers) >= 1
    taper = tapers[0]
    assert taper.length_um == pytest.approx(50.0, abs=0.5)
    widths = sorted([taper.width1_um, taper.width2_um])
    assert widths[0] == pytest.approx(0.5, abs=0.1)
    assert widths[1] == pytest.approx(2.0, abs=0.2)


def test_r181_empty_gds_raises(tmp_path: Path):
    """R181：WG 层为空/缺失时 raise（R03 禁止 fall-back）。"""
    layout, cell = _new_layout()
    gds = _write_gds(layout, tmp_path, "empty.gds")
    with pytest.raises(RuntimeError, match="WG"):
        extract_waveguide_params(gds)


def test_r181_file_not_found():
    """R181：GDS 不存在时 raise FileNotFoundError。"""
    with pytest.raises(FileNotFoundError):
        extract_waveguide_params("/nonexistent/wg.gds")


# ============================================================
# R182 定向耦合器提取测试
# ============================================================


@pytest.fixture
def gds_directional_coupler(tmp_path: Path) -> Path:
    """生成含定向耦合器的 GDS（两根平行波导，gap=0.2μm）。"""
    layout, cell = _new_layout()
    wg_idx = _wg_layer_idx(layout)
    _insert_rect(cell, wg_idx, 0, 0, 20, 0.5)
    _insert_rect(cell, wg_idx, 0, 0.7, 20, 1.2)
    return _write_gds(layout, tmp_path, "dc.gds")


@pytest.fixture
def gds_two_isolated_wgs(tmp_path: Path) -> Path:
    """生成两根远离的波导（不构成 DC）。"""
    layout, cell = _new_layout()
    wg_idx = _wg_layer_idx(layout)
    _insert_rect(cell, wg_idx, 0, 0, 20, 0.5)
    _insert_rect(cell, wg_idx, 0, 10, 20, 10.5)
    return _write_gds(layout, tmp_path, "isolated.gds")


def test_r182_dc_extraction(gds_directional_coupler: Path):
    """R182：定向耦合器耦合长度/间距提取。"""
    dcs = extract_directional_couplers(gds_directional_coupler)
    assert len(dcs) >= 1
    dc = dcs[0]
    assert dc.coupling_length_um == pytest.approx(20.0, abs=0.5)
    assert dc.coupling_gap_um == pytest.approx(0.2, abs=0.05)
    assert dc.width_um == pytest.approx(0.5, abs=0.1)


def test_r182_no_dc_when_far(gds_two_isolated_wgs: Path):
    """R182：波导远离时不识别为 DC。"""
    dcs = extract_directional_couplers(gds_two_isolated_wgs)
    assert len(dcs) == 0


def test_r182_dc_multiple_pairs(tmp_path: Path):
    """R182：多对平行波导各自识别为 DC。"""
    layout, cell = _new_layout()
    wg_idx = _wg_layer_idx(layout)
    # 第一对
    _insert_rect(cell, wg_idx, 0, 0, 15, 0.5)
    _insert_rect(cell, wg_idx, 0, 0.8, 15, 1.3)
    # 第二对
    _insert_rect(cell, wg_idx, 0, 20, 15, 20.5)
    _insert_rect(cell, wg_idx, 0, 20.8, 15, 21.3)
    gds = _write_gds(layout, tmp_path, "multi_dc.gds")
    dcs = extract_directional_couplers(gds)
    assert len(dcs) >= 2


def test_r182_dc_file_not_found():
    """R182：文件不存在 raise。"""
    with pytest.raises(FileNotFoundError):
        extract_directional_couplers("/nonexistent/dc.gds")


# ============================================================
# R183 MMI 提取测试
# ============================================================


@pytest.fixture
def gds_mmi_1x2(tmp_path: Path) -> Path:
    """生成含 1x2 MMI 的 GDS（宽区 + 1 输入 + 2 输出）。"""
    layout, cell = _new_layout()
    wg_idx = _wg_layer_idx(layout)
    # 多模区 6μm × 3μm
    _insert_rect(cell, wg_idx, 0, 0, 6, 3)
    # 输入波导
    _insert_rect(cell, wg_idx, -5, 1.25, 0, 1.75)
    # 输出波导 1
    _insert_rect(cell, wg_idx, 6, 0.25, 11, 0.75)
    # 输出波导 2
    _insert_rect(cell, wg_idx, 6, 2.25, 11, 2.75)
    return _write_gds(layout, tmp_path, "mmi.gds")


@pytest.fixture
def gds_no_mmi(tmp_path: Path) -> Path:
    """生成无 MMI 的 GDS（只有窄波导）。"""
    layout, cell = _new_layout()
    wg_idx = _wg_layer_idx(layout)
    _insert_rect(cell, wg_idx, 0, 0, 50, 0.5)
    return _write_gds(layout, tmp_path, "no_mmi.gds")


def test_r183_mmi_extraction(gds_mmi_1x2: Path):
    """R183：MMI 尺寸/端口数提取。"""
    mmis = extract_mmis(gds_mmi_1x2)
    assert len(mmis) >= 1
    mmi = mmis[0]
    assert mmi.width_um == pytest.approx(3.0, abs=0.2)
    assert mmi.length_um == pytest.approx(6.0, abs=0.2)
    assert mmi.input_port_count == 1
    assert mmi.output_port_count == 2


def test_r183_no_mmi_when_only_narrow(gds_no_mmi: Path):
    """R183：只有窄波导时不识别为 MMI。"""
    mmis = extract_mmis(gds_no_mmi)
    assert len(mmis) == 0


def test_r183_mmi_2x2(tmp_path: Path):
    """R183：2x2 MMI 端口数提取。"""
    layout, cell = _new_layout()
    wg_idx = _wg_layer_idx(layout)
    # 多模区 8μm × 4μm
    _insert_rect(cell, wg_idx, 0, 0, 8, 4)
    # 2 输入
    _insert_rect(cell, wg_idx, -5, 0.75, 0, 1.25)
    _insert_rect(cell, wg_idx, -5, 2.75, 0, 3.25)
    # 2 输出
    _insert_rect(cell, wg_idx, 8, 0.75, 13, 1.25)
    _insert_rect(cell, wg_idx, 8, 2.75, 13, 3.25)
    gds = _write_gds(layout, tmp_path, "mmi_2x2.gds")
    mmis = extract_mmis(gds)
    assert len(mmis) >= 1
    mmi = mmis[0]
    assert mmi.input_port_count == 2
    assert mmi.output_port_count == 2


def test_r183_mmi_file_not_found():
    """R183：文件不存在 raise。"""
    with pytest.raises(FileNotFoundError):
        extract_mmis("/nonexistent/mmi.gds")


# ============================================================
# R184 环形谐振器提取测试
# ============================================================


@pytest.fixture
def gds_ring_resonator(tmp_path: Path) -> Path:
    """生成含环形谐振器 + 总线波导的 GDS。"""
    layout, cell = _new_layout()
    wg_idx = _wg_layer_idx(layout)
    # 环：中心 (30, 30)，半径 10μm，宽 0.5μm
    _insert_polygon(cell, wg_idx, _make_ring_pts(30, 30, 10, 0.5))
    # 总线波导：在环下方，gap ≈ 0.75μm
    # 环外沿底部 = 30 - 10.25 = 19.75，总线顶部 = 19.0，gap = 0.75
    _insert_rect(cell, wg_idx, 10, 18.5, 50, 19.0)
    return _write_gds(layout, tmp_path, "ring.gds")


@pytest.fixture
def gds_no_ring(tmp_path: Path) -> Path:
    """生成无环形的 GDS（只有直波导）。"""
    layout, cell = _new_layout()
    wg_idx = _wg_layer_idx(layout)
    _insert_rect(cell, wg_idx, 0, 0, 50, 0.5)
    return _write_gds(layout, tmp_path, "no_ring.gds")


def test_r184_ring_radius_extraction(gds_ring_resonator: Path):
    """R184：环形谐振器半径提取。"""
    rings = extract_ring_resonators(gds_ring_resonator)
    assert len(rings) >= 1
    ring = rings[0]
    assert ring.radius_um == pytest.approx(10.0, abs=0.5)
    assert ring.width_um == pytest.approx(0.5, abs=0.2)


def test_r184_ring_coupling_gap(gds_ring_resonator: Path):
    """R184：环形谐振器耦合间距提取。"""
    rings = extract_ring_resonators(gds_ring_resonator)
    assert len(rings) >= 1
    ring = rings[0]
    assert ring.coupling_gap_um == pytest.approx(0.75, abs=0.3)
    assert ring.bus_waveguide_name != ""


def test_r184_no_ring_when_only_straight(gds_no_ring: Path):
    """R184：只有直波导时不识别为环形。"""
    rings = extract_ring_resonators(gds_no_ring)
    assert len(rings) == 0


def test_r184_ring_file_not_found():
    """R184：文件不存在 raise。"""
    with pytest.raises(FileNotFoundError):
        extract_ring_resonators("/nonexistent/ring.gds")


# ============================================================
# R185 连接性提取测试
# ============================================================


@pytest.fixture
def gds_connected(tmp_path: Path) -> Path:
    """生成 3 个器件全连接的 GDS（无悬浮）。"""
    layout, cell = _new_layout()
    dr_idx = _devrec_layer_idx(layout)
    wg_idx = _wg_layer_idx(layout)
    _insert_rect(cell, dr_idx, 0, 0, 10, 10)
    _insert_rect(cell, dr_idx, 30, 0, 40, 10)
    _insert_rect(cell, dr_idx, 60, 0, 70, 10)
    _insert_rect(cell, wg_idx, 8, 4, 32, 6)
    _insert_rect(cell, wg_idx, 38, 4, 62, 6)
    return _write_gds(layout, tmp_path, "connected.gds")


@pytest.fixture
def gds_floating(tmp_path: Path) -> Path:
    """生成含悬浮器件的 GDS。"""
    layout, cell = _new_layout()
    dr_idx = _devrec_layer_idx(layout)
    wg_idx = _wg_layer_idx(layout)
    _insert_rect(cell, dr_idx, 0, 0, 10, 10)
    _insert_rect(cell, dr_idx, 30, 0, 40, 10)
    _insert_rect(cell, dr_idx, 100, 100, 110, 110)  # 悬浮
    _insert_rect(cell, wg_idx, 8, 4, 32, 6)
    return _write_gds(layout, tmp_path, "floating.gds")


def test_r185_connected_no_floating(gds_connected: Path):
    """R185：全连接电路无悬浮器件。"""
    report = extract_connectivity(gds_connected)
    assert len(report.device_nodes) == 3
    assert len(report.floating_devices) == 0
    assert len(report.connections) >= 2


def test_r185_floating_device_detected(gds_floating: Path):
    """R185：悬浮器件检测。"""
    report = extract_connectivity(gds_floating)
    assert len(report.device_nodes) == 3
    assert len(report.floating_devices) == 1
    assert "device_2" in report.floating_devices


def test_r185_isolated_group_detected(gds_floating: Path):
    """R185：孤立子图检测。"""
    report = extract_connectivity(gds_floating)
    assert len(report.isolated_groups) >= 1
    isolated = report.isolated_groups[0]
    assert "device_2" in isolated


def test_r185_devrec_empty_raises(tmp_path: Path):
    """R185：DEVREC 层为空/缺失时 raise（R03 禁止 fall-back）。"""
    layout, cell = _new_layout()
    gds = _write_gds(layout, tmp_path, "empty.gds")
    with pytest.raises(RuntimeError, match="DEVREC"):
        extract_connectivity(gds)


# ============================================================
# R186 器件匹配增强测试
# ============================================================


def test_r186_exact_match():
    """R186：参数完全一致时匹配成功。"""
    ref = {"wg1": {"length": 100.0, "width": 0.5}, "dc1": {"gap": 0.2}}
    ext = {"wg1": {"length": 100.0, "width": 0.5}, "dc1": {"gap": 0.2}}
    result = match_devices_with_tolerance(ref, ext)
    assert "wg1" in result.matched_devices
    assert "dc1" in result.matched_devices
    assert len(result.param_mismatches) == 0


def test_r186_param_mismatch_detected():
    """R186：参数偏差超容差时检测到。"""
    ref = {"wg1": {"length": 100.0}}
    ext = {"wg1": {"length": 105.0}}
    tols = {"length": ToleranceSpec(abs_tol=0.0, rel_tol=0.01)}
    result = match_devices_with_tolerance(ref, ext, tols)
    assert len(result.param_mismatches) == 1
    pm = result.param_mismatches[0]
    assert pm.device_name == "wg1"
    assert pm.param_name == "length"
    assert pm.deviation == pytest.approx(5.0, abs=0.01)
    assert pm.relative_deviation == pytest.approx(5.0, abs=0.1)


def test_r186_tolerance_allows_small_deviation():
    """R186：小偏差在容差范围内不报错。"""
    ref = {"wg1": {"length": 100.0}}
    ext = {"wg1": {"length": 100.4}}
    tols = {"length": ToleranceSpec(abs_tol=0.0, rel_tol=0.01)}
    result = match_devices_with_tolerance(ref, ext, tols)
    assert len(result.param_mismatches) == 0
    assert "wg1" in result.matched_devices


def test_r186_missing_extra_devices():
    """R186：缺失/多余器件检测。"""
    ref = {"wg1": {"length": 100.0}, "ring1": {"radius": 5.0}}
    ext = {"wg1": {"length": 100.0}, "extra1": {"length": 50.0}}
    result = match_devices_with_tolerance(ref, ext)
    assert "ring1" in result.missing_devices
    assert "extra1" in result.extra_devices


def test_r186_abs_tol_combined():
    """R186：绝对+相对容差组合（KLayout 公式）。"""
    ref = {"dc1": {"gap": 0.200}}
    ext = {"dc1": {"gap": 0.205}}
    tols = {"gap": ToleranceSpec(abs_tol=0.01, rel_tol=0.0)}
    result = match_devices_with_tolerance(ref, ext, tols)
    assert len(result.param_mismatches) == 0


# ============================================================
# R187 错误报告增强测试
# ============================================================


@pytest.fixture
def gds_two_devices_overlap(tmp_path: Path) -> Path:
    """生成两器件包围盒相交（短路）的 GDS。"""
    layout, cell = _new_layout()
    dr_idx = _devrec_layer_idx(layout)
    _insert_rect(cell, dr_idx, 0, 0, 20, 20)
    _insert_rect(cell, dr_idx, 10, 10, 30, 30)
    return _write_gds(layout, tmp_path, "short.gds")


@pytest.fixture
def gds_one_device_with_floating(tmp_path: Path) -> Path:
    """生成含悬浮器件（开路）的 GDS：device_0 与 device_1 连接，device_2 悬浮。"""
    layout, cell = _new_layout()
    dr_idx = _devrec_layer_idx(layout)
    wg_idx = _wg_layer_idx(layout)
    _insert_rect(cell, dr_idx, 0, 0, 10, 10)
    _insert_rect(cell, dr_idx, 30, 0, 40, 10)
    _insert_rect(cell, dr_idx, 100, 100, 110, 110)  # 悬浮
    _insert_rect(cell, wg_idx, 8, 4, 32, 6)  # 连接 device_0 与 device_1
    return _write_gds(layout, tmp_path, "open.gds")


def test_r187_missing_device_located(tmp_path: Path):
    """R187：缺失器件在错误报告中定位。"""
    layout, cell = _new_layout()
    dr_idx = _devrec_layer_idx(layout)
    _insert_rect(cell, dr_idx, 0, 0, 10, 10)
    gds = _write_gds(layout, tmp_path, "missing.gds")
    ref = ExtractedNetlist(devices=["device_0", "missing_dev"], connections=[])
    report = generate_structured_error_report(gds, ref)
    assert report.total_error_count >= 1
    missing_errs = [
        e for e in report.device_errors if e.mtype == LVSMismatchType.MISSING_DEVICE
    ]
    assert len(missing_errs) == 1
    assert missing_errs[0].device_name == "missing_dev"


def test_r187_short_detected_with_coordinates(gds_two_devices_overlap: Path):
    """R187：短路检测并定位到坐标。"""
    ref = ExtractedNetlist(devices=["device_0", "device_1"], connections=[])
    report = generate_structured_error_report(gds_two_devices_overlap, ref)
    assert len(report.short_errors) >= 1
    short = report.short_errors[0]
    assert short.bbox_um != (0.0, 0.0, 0.0, 0.0)
    assert short.bbox_um[0] == pytest.approx(10.0, abs=0.1)
    assert short.bbox_um[1] == pytest.approx(10.0, abs=0.1)


def test_r187_open_floating_detected(gds_one_device_with_floating: Path):
    """R187：开路（悬浮器件）检测。"""
    ref = ExtractedNetlist(devices=["device_0", "device_1", "device_2"], connections=[])
    report = generate_structured_error_report(gds_one_device_with_floating, ref)
    assert len(report.open_errors) >= 1
    open_err = report.open_errors[0]
    assert "device_2" in open_err.message
    assert open_err.bbox_um[0] == pytest.approx(100.0, abs=0.1)


def test_r187_clean_report_no_errors(tmp_path: Path):
    """R187：无错误时报告 clean（两器件用波导连接，无悬浮/短路）。"""
    layout, cell = _new_layout()
    dr_idx = _devrec_layer_idx(layout)
    wg_idx = _wg_layer_idx(layout)
    _insert_rect(cell, dr_idx, 0, 0, 10, 10)
    _insert_rect(cell, dr_idx, 30, 0, 40, 10)
    _insert_rect(cell, wg_idx, 8, 4, 32, 6)  # 连接两器件，避免悬浮
    gds = _write_gds(layout, tmp_path, "clean.gds")
    ref = ExtractedNetlist(devices=["device_0", "device_1"], connections=[])
    report = generate_structured_error_report(gds, ref)
    assert len(report.short_errors) == 0
    assert report.total_error_count == 0


def test_r187_structured_report_dataclass():
    """R187：结构化报告数据类完整性。"""
    report = StructuredErrorReport()
    assert report.total_error_count == 0
    assert len(report.short_errors) == 0
    err = LocatedError(
        mtype=LVSMismatchType.EXTRA_CONNECTION,
        message="测试短路",
        bbox_um=(1.0, 2.0, 3.0, 4.0),
    )
    report.short_errors.append(err)
    assert report.short_errors[0].bbox_um == (1.0, 2.0, 3.0, 4.0)
