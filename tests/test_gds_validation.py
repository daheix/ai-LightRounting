"""GDS 导出与 DRC 验证测试（Task 16 增强 + 止血7）。

现有 ``tests/test_render.py`` 的 GDS 测试仅断言文件存在且非空，
本测试模块补充以下验证：
- GDS 可被 klayout.db 重新读取（cell 数量、layer 数量）
- 器件类别到 GDS layer 的映射正确（止血7：真实 foundry layer 编号）
  - passive/active → WG (1,0)
  - source → SOURCE (110,0)
  - detector → GE (5,0)
  - 器件包围盒同时画到 DEVREC (68,0)
  - 端口画到 PORT (1,10)
  - 波导画到 WG (1,0)
- DRC 在无重叠/间距/弯曲半径违规时通过
- DRC 能检测重叠、间距不足、弯曲半径不足
- 纯 Python 几何运算（_boxes_intersect/_boxes_distance）正确性

klayout 为可选依赖（规则 5.3）：缺失时 GDS 相关测试用
``pytest.importorskip("klayout")`` 跳过；DRC 与纯 Python 几何测试不依赖 klayout。

工具来源:
- klayout Python: https://www.klayout.de/ （GDSII 读写 + DRC）
- SiEPIC EBeam PDK (MIT): https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- ubcpdk (MIT): https://github.com/gdsfactory/ubc/blob/main/ubcpdk/tech.py
"""

from __future__ import annotations

import pytest

from polaris.engine.floorplan_env import Placement
from polaris.eval.layout_render import (
    _boxes_distance,
    _boxes_intersect,
    export_gds,
    run_drc,
)
from polaris.pdk import BoundingBox, Device, Direction, Port
from polaris.router.waveguide_router import WaveguidePath


# ---------------------------------------------------------------------------
# 测试夹具与辅助构造
# ---------------------------------------------------------------------------
def _make_device(device_id: str, category: str, w: float = 5.0, h: float = 5.0) -> Device:
    """构造测试用器件（指定类别与尺寸，含 in/out 端口）。

    Args:
        device_id: 器件唯一标识。
        category: 器件类别（passive/active/source/detector）。
        w: 器件宽度（μm）。
        h: 器件高度（μm）。

    Returns:
        测试用 ``Device`` 实例。
    """
    return Device(
        device_id=device_id,
        platform="SOI",
        category=category,
        name=f"test_{category}",
        ports=[
            Port(
                name="in",
                x=0.0,
                y=h / 2,
                direction=Direction.WEST,
                waveguide_type="strip",
                width=0.5,
            ),
            Port(
                name="out",
                x=w,
                y=h / 2,
                direction=Direction.EAST,
                waveguide_type="strip",
                width=0.5,
            ),
        ],
        bbox=BoundingBox(xmin=0.0, ymin=0.0, xmax=w, ymax=h),
    )


def _make_placement(
    inst_id: str, category: str, x: float, y: float, w: float = 5.0, h: float = 5.0
) -> Placement:
    """构造测试用放置结果（指定类别与左下角位置）。"""
    dev = _make_device(inst_id, category, w, h)
    return Placement(instance_id=inst_id, device=dev, x=x, y=y, rotation=0)


@pytest.fixture
def klayout_db():
    """提供 klayout.db 模块，缺失时跳过依赖它的测试（规则 5.3）。"""
    pytest.importorskip("klayout")
    import klayout.db as db

    return db


# ---------------------------------------------------------------------------
# GDS 往返读取验证（依赖 klayout）
# ---------------------------------------------------------------------------
def test_gds_can_be_reloaded(klayout_db, tmp_path) -> None:
    """导出 GDS 后应能被 klayout.db 重新读取，且含至少 1 个 cell 与多个 layer。"""
    placements = {
        "d1": _make_placement("d1", "passive", 0.0, 0.0),
        "d2": _make_placement("d2", "passive", 20.0, 0.0),
    }
    paths = {0: WaveguidePath(points=[(5.0, 2.5), (20.0, 2.5)], length_um=15.0)}
    gds_path = export_gds(placements, paths, str(tmp_path / "layout.gds"))

    ly = klayout_db.Layout()
    ly.read(gds_path)
    top_cells = list(ly.top_cells())
    assert len(top_cells) >= 1, "GDS 应至少含 1 个 top cell"
    layer_infos = list(ly.layer_infos())
    # 止血7 真实 foundry layer：WG(1/0) + DEVREC(68/0) + PORT(1/10) 至少 3 层
    assert len(layer_infos) >= 3, f"GDS 应至少含 3 个 layer，实际 {len(layer_infos)}"
    tc = ly.top_cell()
    assert tc is not None
    assert tc.name == "TOP"


def test_gds_layer_mapping(klayout_db, tmp_path) -> None:
    """器件类别应映射到真实 foundry GDS layer（止血7）。

    - passive/active → WG (1,0)
    - source → SOURCE (110,0)
    - detector → GE (5,0)
    - 所有器件包围盒同时画到 DEVREC (68,0)
    - 端口画到 PORT (1,10)
    """
    placements = {
        "p1": _make_placement("p1", "passive", 0.0, 0.0),
        "a1": _make_placement("a1", "active", 20.0, 0.0),
        "s1": _make_placement("s1", "source", 40.0, 0.0),
        "de1": _make_placement("de1", "detector", 60.0, 0.0),
    }
    gds_path = export_gds(placements, None, str(tmp_path / "layers.gds"))

    ly = klayout_db.Layout()
    ly.read(gds_path)
    tc = ly.top_cell()
    # 真实 foundry layer 映射（止血7，借鉴 SiEPIC/ubcpdk/gdsfactory）
    expected = {
        "WG (passive/active)": (1, 0),
        "SOURCE": (110, 0),
        "GE (detector)": (5, 0),
        "DEVREC": (68, 0),
        "PORT": (1, 10),
    }
    for label, (g, d) in expected.items():
        idx = ly.find_layer(klayout_db.LayerInfo(g, d))
        assert idx is not None, f"layer {g}/{d}（{label}）未在 GDS 中找到"
        cnt = tc.shapes(idx).size()
        assert cnt >= 1, f"layer {g}/{d}（{label}）上应有至少 1 个 shape，实际 {cnt}"


def test_gds_has_waveguide_layer(klayout_db, tmp_path) -> None:
    """波导路径应绘制在 WG layer (1,0) 上（止血7：与器件同层）。"""
    placements = {"d1": _make_placement("d1", "passive", 0.0, 0.0)}
    paths = {0: WaveguidePath(points=[(5.0, 2.5), (20.0, 2.5)], length_um=15.0)}
    gds_path = export_gds(placements, paths, str(tmp_path / "wg.gds"))

    ly = klayout_db.Layout()
    ly.read(gds_path)
    tc = ly.top_cell()
    # 止血7：波导画在 WG (1,0) 层（与器件同层，SiEPIC 标准）
    idx = ly.find_layer(klayout_db.LayerInfo(1, 0))
    assert idx is not None, "波导 layer 1/0 (WG) 未在 GDS 中找到"
    cnt = tc.shapes(idx).size()
    assert cnt >= 1, f"波导 layer 1/0 (WG) 上应有至少 1 个 shape，实际 {cnt}"


# ---------------------------------------------------------------------------
# DRC 验证（纯 Python，不依赖 klayout）
# ---------------------------------------------------------------------------
def test_drc_with_no_overlaps() -> None:
    """无重叠且间距充足时 DRC 应通过。"""
    placements = {
        "d1": _make_placement("d1", "passive", 0.0, 0.0, w=5.0, h=5.0),
        "d2": _make_placement("d2", "passive", 20.0, 0.0, w=5.0, h=5.0),
    }
    report = run_drc(placements, None, min_spacing_um=1.0, min_bend_radius_um=5.0)
    assert report.passed
    assert report.overlap_violations == 0
    assert report.spacing_violations == 0
    assert report.min_bend_radius_violations == 0


def test_drc_detects_overlaps() -> None:
    """器件重叠时 DRC 应检测到 overlap 违规。"""
    placements = {
        "d1": _make_placement("d1", "passive", 0.0, 0.0, w=5.0, h=5.0),
        # d2 与 d1 在 x∈[2,5] 区间重叠
        "d2": _make_placement("d2", "passive", 2.0, 0.0, w=5.0, h=5.0),
    }
    report = run_drc(placements, None, min_spacing_um=1.0)
    assert report.overlap_violations >= 1
    assert not report.passed


def test_drc_detects_spacing_violation() -> None:
    """器件间距不足（但不重叠）时 DRC 应检测到 spacing 违规。"""
    # d1=[0,0,5,5], d2=[6,0,11,5], 间距=1.0μm < min_spacing=2.0μm
    placements = {
        "d1": _make_placement("d1", "passive", 0.0, 0.0, w=5.0, h=5.0),
        "d2": _make_placement("d2", "passive", 6.0, 0.0, w=5.0, h=5.0),
    }
    report = run_drc(placements, None, min_spacing_um=2.0)
    assert report.overlap_violations == 0
    assert report.spacing_violations >= 1
    assert not report.passed


def test_drc_detects_bend_radius_violation() -> None:
    """波导转弯前直行段短于最小弯曲半径时 DRC 应检测到违规。"""
    placements = {"d1": _make_placement("d1", "passive", 0.0, 0.0)}
    # 路径 (0,0)->(2,0)->(2,5)：在 (2,0) 转弯，前段长 2.0μm < 5.0μm
    paths = {0: WaveguidePath(points=[(0.0, 0.0), (2.0, 0.0), (2.0, 5.0)], length_um=7.0)}
    report = run_drc(placements, paths, min_bend_radius_um=5.0)
    assert report.min_bend_radius_violations >= 1
    assert not report.passed


# ---------------------------------------------------------------------------
# 纯 Python 几何运算验证（不依赖 klayout）
# ---------------------------------------------------------------------------
def test_boxes_intersect_pure_python() -> None:
    """_boxes_intersect 应正确判断轴对齐矩形相交（含边界接触）。"""
    # 部分重叠
    assert _boxes_intersect((0, 0, 5, 5), (3, 3, 8, 8))
    # 完全相同
    assert _boxes_intersect((0, 0, 5, 5), (0, 0, 5, 5))
    # 边界接触（相交，含边界）
    assert _boxes_intersect((0, 0, 5, 5), (5, 0, 10, 5))
    # 一个包含另一个
    assert _boxes_intersect((0, 0, 10, 10), (2, 2, 5, 5))
    # 完全分离
    assert not _boxes_intersect((0, 0, 5, 5), (10, 0, 15, 5))
    # 仅 y 方向分离
    assert not _boxes_intersect((0, 0, 5, 5), (0, 10, 5, 15))


def test_boxes_distance_pure_python() -> None:
    """_boxes_distance 应正确计算轴对齐矩形间最短距离（相交时为 0）。"""
    # 重叠 → 0
    assert _boxes_distance((0, 0, 5, 5), (3, 3, 8, 8)) == 0.0
    # 完全相同 → 0
    assert _boxes_distance((0, 0, 5, 5), (0, 0, 5, 5)) == 0.0
    # 边界接触 → 0
    assert _boxes_distance((0, 0, 5, 5), (5, 0, 10, 5)) == 0.0
    # 水平间距：a=[0,0,5,5], b=[8,0,13,5], gap=3
    assert _boxes_distance((0, 0, 5, 5), (8, 0, 13, 5)) == pytest.approx(3.0)
    # 对角间距：a=[0,0,5,5], b=[8,8,13,13], dx=3, dy=3, dist=sqrt(18)
    assert _boxes_distance((0, 0, 5, 5), (8, 8, 13, 13)) == pytest.approx((3.0**2 + 3.0**2) ** 0.5)
