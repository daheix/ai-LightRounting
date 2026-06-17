"""版图渲染与导出测试（Task 16）。"""

from __future__ import annotations

import os

import numpy as np
import pytest

from polaris.engine.floorplan_env import FloorplanEnv
from polaris.engine.netlist import load_netlist
from polaris.eval.layout_render import (
    DRCReport,
    export_gds,
    export_oasis,
    render_congestion_heatmap,
    render_layout,
    run_drc,
)
from polaris.router.routing_env import RoutingEnv


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
    r = render_layout(placements, paths, cong, save_path=str(tmp_path / "layout.png"))
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
