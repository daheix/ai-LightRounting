"""布局/布线环境测试（Task 9/12）。"""

from __future__ import annotations

import numpy as np
import pytest

from polaris.engine.floorplan_env import (
    FloorplanEnv,
    FloorplanEnvConfig,
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


def test_spacing_violations_in_reward():
    """F3 DRV 消除：间距违规应纳入 reward 惩罚。"""
    from polaris.pdk.catalog import build_default_catalog

    cat = build_default_catalog()
    dev = cat.get("strip_waveguide", platform="SOI")
    state = FloorplanState()
    # 两个器件间距 < min_spacing_um（5.0）
    state.placements["a"] = Placement("a", dev, 0, 0)
    state.placements["b"] = Placement("b", dev, 1, 0)  # 间距 1μm < 5μm
    from polaris.engine.floorplan_env import _count_spacing_violations

    placed = list(state.placements.values())
    violations = _count_spacing_violations(placed, min_spacing=5.0)
    assert violations >= 1


def test_spacing_no_violations():
    """F3 DRV 消除：间距足够时无违规。"""
    from polaris.engine.floorplan_env import _count_spacing_violations
    from polaris.pdk.catalog import build_default_catalog

    cat = build_default_catalog()
    dev = cat.get("strip_waveguide", platform="SOI")
    state = FloorplanState()
    state.placements["a"] = Placement("a", dev, 0, 0)
    state.placements["b"] = Placement("b", dev, 100, 100)  # 间距远 > 5μm
    placed = list(state.placements.values())
    violations = _count_spacing_violations(placed, min_spacing=5.0)
    assert violations == 0


def test_floorplan_config_spacing_params():
    """F3 DRV 消除：FloorplanEnvConfig 含间距惩罚参数。"""
    cfg = FloorplanEnvConfig()
    assert cfg.spacing_penalty > 0
    assert cfg.min_spacing_um > 0


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


def test_routing_reward_clipping(env_setup):
    """reward clipping 应限制单步 reward 下限，防止异常值摧毁价值函数。

    第二波训练收敛修复：历史 progress.json 显示布线 reward 出现 -9000
    灾难值，导致价值函数 vloss=14-15 无法收敛。reward clipping 将单步
    reward 限制在 [-reward_clip_max, 0] 范围。
    """
    from polaris.router.routing_env import RoutingEnvConfig
    from polaris.router.waveguide_router import WaveguidePath

    net, devices, env = env_setup
    env.reset()
    for _ in range(len(devices)):
        env.step([5, 5, 0])
    # 使用小 clip_max 验证 clipping 生效
    cfg = RoutingEnvConfig(canvas_w=300, canvas_h=300, grid_size=5, reward_clip_max=5.0)
    r_env = RoutingEnv(net, env.state.placements, config=cfg)
    r_env.reset()
    assert r_env.reward_clip_max == 5.0
    # 构造一个高损耗的路径（模拟异常长路径或高 DRC 违规）
    # loss_db=100, length=10000 → 原始 reward = -(1*100 + 0.001*10000) = -110
    # clipping 后应为 -5.0
    wp = WaveguidePath(points=[(0, 0), (100, 0)], length_um=10000.0, loss_db=100.0)
    reward = r_env._reward(wp)
    assert reward == -5.0, f"reward 应被 clip 到 -5.0，实际 {reward}"


def test_routing_reward_clip_default(env_setup):
    """默认 reward_clip_max=20.0，正常布线 reward 不受影响。"""
    net, devices, env = env_setup
    env.reset()
    for _ in range(len(devices)):
        env.step([5, 5, 0])
    r_env = RoutingEnv(net, env.state.placements, canvas_w=300, canvas_h=300, grid_size=5)
    r_env.reset()
    assert r_env.reward_clip_max == 20.0
    # 正常布线 reward 应在 [-20, 0] 范围内，不受 clipping 影响
    obs, reward, term, _, _ = r_env.step(np.zeros(3, dtype=np.float32))
    assert -20.0 <= reward <= 0.0, f"reward {reward} 应在 [-20, 0] 范围"
