"""版图渲染与导出测试（Task 16）。"""

from __future__ import annotations

import math
import os

import numpy as np
import pytest

from polaris.engine.floorplan_env import FloorplanEnv
from polaris.engine.netlist import load_netlist
from polaris.eval.layout_render import (
    DRCReport,
    RenderOptions,
    _check_bend_radius,
    export_gds,
    export_oasis,
    render_congestion_heatmap,
    render_layout,
    run_drc,
)
from polaris.router.routing_env import RoutingEnv
from polaris.router.waveguide_router import WaveguidePath

YAML_NETLIST = """
instances:
  wg1: {component: strip_waveguide, platform: SOI}
  mmi1: {component: mmi_1x2, platform: SOI}
connections:
  - [wg1, out, mmi1, in]
"""


@pytest.fixture
def layout_setup():
    net, devices, _ = load_netlist(YAML_NETLIST)
    env = FloorplanEnv(net, devices, canvas_w=300, canvas_h=300, grid_size=10)
    env.reset()
    for _ in range(len(devices)):
        env.step([5, 5, 0])
    r_env = RoutingEnv(net, env.state.placements, canvas_w=300, canvas_h=300, grid_size=5)
    r_env.reset()
    for _ in range(len(net.connections)):
        r_env.step(np.zeros(3, dtype=np.float32))
    return env.state.placements, r_env.state.paths, r_env.congestion_heatmap()


def test_render_layout(layout_setup, tmp_path):
    placements, paths, cong = layout_setup
    opts = RenderOptions(save_path=str(tmp_path / "layout.png"))
    r = render_layout(placements, paths, cong, options=opts)
    assert r.fig is not None
    assert (tmp_path / "layout.png").exists()


def test_render_congestion_heatmap(layout_setup, tmp_path):
    _, _, cong = layout_setup
    r = render_congestion_heatmap(cong, save_path=str(tmp_path / "cong.png"))
    assert r.fig is not None
    assert (tmp_path / "cong.png").exists()


def test_export_gds(layout_setup, tmp_path):
    placements, paths, _ = layout_setup
    gds_path = export_gds(placements, paths, str(tmp_path / "layout.gds"))
    assert os.path.exists(gds_path)
    assert os.path.getsize(gds_path) > 0


def test_export_oasis(layout_setup, tmp_path):
    placements, paths, _ = layout_setup
    oasis_path = export_oasis(placements, paths, str(tmp_path / "layout.oas"))
    assert os.path.exists(oasis_path)
    assert os.path.getsize(oasis_path) > 0


def test_run_drc_pass(layout_setup):
    placements, paths, _ = layout_setup
    report = run_drc(placements, paths)
    assert isinstance(report, DRCReport)


def test_drc_report_passed_property():
    report = DRCReport()
    assert report.passed
    assert report.total_violations == 0
    report.overlap_violations = 1
    assert not report.passed
    assert report.total_violations == 1


# ---------------------------------------------------------------------------
# P0-D 回归测试：_check_bend_radius 三点圆弧半径公式
# 修复前 bug: 原算法用"段长 < min_bend_radius"判断，物理错误
# 修复后: R = |P1P2|·|P2P3|·|P1P3| / (4·三角形面积)
# 学术依据: Fujisawa 2017 Photonics / Soref 1993 IEEE Proc.
# ---------------------------------------------------------------------------


class TestP0DBendRadius:
    """P0-D 回归测试：弯曲半径算法正确性。"""

    def test_collinear_points_no_violation(self):
        """共线三点 R=∞，无弯曲，不应报违规。"""
        wp = WaveguidePath(points=[(0.0, 0.0), (5.0, 0.0), (10.0, 0.0)])
        paths = {0: wp}
        violations, details = _check_bend_radius(paths, min_bend_radius_um=5.0)
        assert violations == 0
        assert len(details) == 0

    def test_gentle_bend_no_violation(self):
        """缓和弯曲（大半径）不应报违规。

        三点构成大圆弧：P1=(0,0), P2=(10,0), P3=(20,1)
        R = abc/(4S)，应远大于 5μm。
        """
        wp = WaveguidePath(points=[(0.0, 0.0), (10.0, 0.0), (20.0, 1.0)])
        paths = {0: wp}
        violations, _ = _check_bend_radius(paths, min_bend_radius_um=5.0)
        assert violations == 0, "缓和弯曲不应报违规"

    def test_sharp_bend_violation(self):
        """尖锐弯曲（小半径）应报违规。

        三点构成锐角：P1=(0,0), P2=(1,0), P3=(1.1, 0.1)
        R 极小，应 < 5μm 触发违规。
        """
        wp = WaveguidePath(points=[(0.0, 0.0), (1.0, 0.0), (1.1, 0.1)])
        paths = {0: wp}
        violations, details = _check_bend_radius(paths, min_bend_radius_um=5.0)
        assert violations == 1, "尖锐弯曲应报 1 个违规"
        assert len(details) == 1
        # 详情应含 R= 数值（修复前错误地报告"段长"）
        assert "R=" in details[0]

    def test_known_radius_circle(self):
        """已知半径圆弧验证公式正确性。

        构造半径 R=10 的圆上三点，验证计算半径 ≈ 10。
        圆心 (0,0)，三点角度 -30°, 0°, +30°：
        P1=(10·cos(-30°), 10·sin(-30°)) = (8.660, -5.0)
        P2=(10, 0)
        P3=(10·cos(30°), 10·sin(30°)) = (8.660, 5.0)
        """
        r_known = 10.0
        p1 = (r_known * math.cos(math.radians(-30)), r_known * math.sin(math.radians(-30)))
        p2 = (r_known * math.cos(math.radians(0)), r_known * math.sin(math.radians(0)))
        p3 = (r_known * math.cos(math.radians(30)), r_known * math.sin(math.radians(30)))
        wp = WaveguidePath(points=[p1, p2, p3])
        paths = {0: wp}
        # 验证计算半径 ≈ 10：min_bend=8 应通过，min_bend=12 应违规
        violations_pass, _ = _check_bend_radius(paths, min_bend_radius_um=8.0)
        assert violations_pass == 0, "R=10 应大于 8，无违规"
        violations_fail, _ = _check_bend_radius(paths, min_bend_radius_um=12.0)
        assert violations_fail == 1, "R=10 应小于 12，触发违规"

    def test_old_bug_segment_length_not_used(self):
        """回归测试：旧 bug 用段长判断，会误报长段直线为违规。

        旧 bug: 直线段长 10μm < min_bend=5 不报，但若 min_bend=15 会误报。
        新实现: 直线（共线）R=∞，永远不报违规。
        """
        wp = WaveguidePath(points=[(0.0, 0.0), (10.0, 0.0), (20.0, 0.0)])
        paths = {0: wp}
        # 旧 bug: 段长 10 < 15 会误报；新实现: 共线 R=∞，不报
        violations, _ = _check_bend_radius(paths, min_bend_radius_um=15.0)
        assert violations == 0, "共线直线 R=∞，不应报违规（旧 bug 会误报）"

    def test_multiple_bends(self):
        """多弯曲路径应正确累计违规数（2 条路径各 1 个尖锐弯曲）。"""
        wp1 = WaveguidePath(points=[(0.0, 0.0), (1.0, 0.0), (1.1, 0.1)])
        wp2 = WaveguidePath(points=[(0.0, 0.0), (1.0, 0.0), (1.1, 0.1)])
        paths = {0: wp1, 1: wp2}
        violations, details = _check_bend_radius(paths, min_bend_radius_um=5.0)
        assert violations == 2, "应检测到 2 个尖锐弯曲"
        assert len(details) == 2
