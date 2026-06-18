"""布局/布线环境测试（Task 9/12）。"""

from __future__ import annotations

import numpy as np
import pytest

from polaris.engine.floorplan_env import (
    FloorplanEnv,
    FloorplanState,
    Placement,
    count_overlaps,
    hpwl,
)
from polaris.engine.netlist import load_netlist
from polaris.router.routing_env import RoutingEnv

YAML_NETLIST = """
instances:
  wg1: {component: strip_waveguide, platform: SOI}
  mmi1: {component: mmi_1x2, platform: SOI}
  wg2: {component: strip_waveguide, platform: SOI}
connections:
  - [wg1, out, mmi1, in]
  - [mmi1, out0, wg2, in]
"""


@pytest.fixture
def env_setup():
    net, devices, _ = load_netlist(YAML_NETLIST)
    env = FloorplanEnv(net, devices, canvas_w=300, canvas_h=300, grid_size=10)
    return net, devices, env


def test_floorplan_reset(env_setup):
    net, devices, env = env_setup
    obs, info = env.reset()
    assert "occupancy" in obs
    assert "port_positions" in obs
    assert obs["occupancy"].shape == (env.grid_h, env.grid_w)


def test_floorplan_step(env_setup):
    net, devices, env = env_setup
    env.reset()
    obs, reward, term, trunc, info = env.step([5, 5, 0])
    assert isinstance(reward, float)
    assert len(env.state.placements) == 1


def test_floorplan_full_episode(env_setup):
    net, devices, env = env_setup
    env.reset()
    total = 0.0
    for i in range(len(devices)):
        obs, r, term, _, _ = env.step([5 + i * 10, 5, 0])
        total += r
        if term:
            break
    assert len(env.state.placements) == len(devices)


def test_hpwl_zero_when_unplaced(env_setup):
    net, devices, env = env_setup
    state = FloorplanState()
    assert hpwl(net, state) == 0.0


def test_count_overlaps():
    from polaris.pdk.catalog import build_default_catalog

    cat = build_default_catalog()
    dev = cat.get("strip_waveguide", platform="SOI")
    state = FloorplanState()
    state.placements["a"] = Placement("a", dev, 0, 0)
    state.placements["b"] = Placement("b", dev, 5, 0)  # 重叠
    assert count_overlaps(state) == 1


def test_routing_env_reset(env_setup):
    net, devices, env = env_setup
    env.reset()
    for _ in range(len(devices)):
        env.step([5, 5, 0])
    r_env = RoutingEnv(net, env.state.placements, canvas_w=300, canvas_h=300, grid_size=5)
    obs, info = r_env.reset()
    assert "congestion" in obs
    assert "ports" in obs


def test_routing_env_step(env_setup):
    net, devices, env = env_setup
    env.reset()
    for _ in range(len(devices)):
        env.step([5, 5, 0])
    r_env = RoutingEnv(net, env.state.placements, canvas_w=300, canvas_h=300, grid_size=5)
    r_env.reset()
    obs, reward, term, _, _ = r_env.step(np.zeros(3, dtype=np.float32))
    assert isinstance(reward, float)


def test_routing_metrics(env_setup):
    net, devices, env = env_setup
    env.reset()
    for _ in range(len(devices)):
        env.step([5, 5, 0])
    r_env = RoutingEnv(net, env.state.placements, canvas_w=300, canvas_h=300, grid_size=5)
    r_env.reset()
    for _ in range(len(net.connections)):
        r_env.step(np.zeros(3, dtype=np.float32))
    metrics = r_env.total_metrics()
    assert "total_loss_db" in metrics
    assert "total_length_um" in metrics
    assert metrics["num_routed"] == len(net.connections)
