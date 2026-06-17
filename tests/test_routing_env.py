"""布线强化学习环境的单元测试（Task 12）。

覆盖 reset 返回有效观测、step 执行动作后状态更新、到达终点获得正奖励、
碰撞获得负奖励、拥塞热力图正确生成、render 不报错。
"""

from __future__ import annotations

import numpy as np
import pytest

from polaris.engine.floorplan_env import Placement
from polaris.engine.netlist import Netlist, NetlistConnection
from polaris.pdk.device import BoundingBox, Device
from polaris.pdk.port import Direction, Port
from polaris.router.routing_env import RoutingEnv


def _pad_device(device_id: str, port_name: str, port_x: float, port_y: float,
                direction: Direction) -> Device:
    """构造一个用于测试的"焊盘"器件（1μm 宽、2μm 高，含单端口）。

    包围盒 (0,-1,1,1) 使其栅格化后覆盖多行，便于碰撞测试。
    """
    return Device(
        device_id=device_id,
        platform="SOI",
        category="passive",
        name="pad",
        ports=[
            Port(
                name=port_name,
                x=port_x,
                y=port_y,
                direction=direction,
                waveguide_type="strip",
                width=0.5,
            )
        ],
        bbox=BoundingBox(xmin=0.0, ymin=-1.0, xmax=1.0, ymax=1.0),
    )


def _make_env(b_x: float = 2.0, max_steps: int = 100) -> RoutingEnv:
    """构造测试环境：器件 A 在 (0,0)，器件 B 在 (b_x,0)，单连接 a.out -> b.in。

    A.out 端口位于 (1,0) 朝东；B.in 端口位于 (b_x,0) 朝西。
    b_x=2 时源与目标相邻（一步可达）；b_x 较大时需多步。
    """
    dev_a = _pad_device("a", "out", 1.0, 0.0, Direction.EAST)
    dev_b = _pad_device("b", "in", 0.0, 0.0, Direction.WEST)
    placements = {
        "a": Placement(instance_id="a", device=dev_a, x=0.0, y=0.0),
        "b": Placement(instance_id="b", device=dev_b, x=b_x, y=0.0),
    }
    net = Netlist(
        name="test",
        connections=[NetlistConnection("a", "out", "b", "in")],
    )
    return RoutingEnv(
        net,
        placements,
        grid_size=1.0,
        min_bend_radius=5.0,
        max_steps=max_steps,
    )


# ---------------------------------------------------------------------------
# reset 返回有效观测
# ---------------------------------------------------------------------------
def test_reset_returns_valid_observation() -> None:
    """reset 应返回符合 observation_space 的观测字典。"""
    env = _make_env()
    obs, info = env.reset(seed=42)

    # 观测键齐全
    assert set(obs.keys()) == {"grid", "congestion", "current_net", "remaining_nets"}
    # 形状与 dtype
    assert obs["grid"].shape == (env.grid_h, env.grid_w)
    assert obs["grid"].dtype == np.float32
    assert obs["congestion"].shape == (env.grid_h, env.grid_w)
    assert obs["congestion"].dtype == np.float32
    assert obs["current_net"].shape == (4,)
    assert obs["current_net"].dtype == np.float32
    # 剩余连接数 = 总连接数（reset 后尚未布线）
    assert obs["remaining_nets"] == 1
    # 观测落在声明空间内
    assert env.observation_space.contains(obs)
    # info 含必要字段
    assert info["num_nets"] == 1
    assert info["net_index"] == 0


def test_reset_grid_shows_obstacle_and_head() -> None:
    """reset 后占用栅格应包含器件障碍与当前头位置。"""
    env = _make_env()
    obs, _ = env.reset()
    # 至少有一个障碍格（器件）与一个头格
    assert obs["grid"].sum() >= 2.0
    # 拥塞图初始为全 0
    assert obs["congestion"].sum() == 0.0


# ---------------------------------------------------------------------------
# step 执行动作后状态更新
# ---------------------------------------------------------------------------
def test_step_updates_state() -> None:
    """step 后头位置应更新、观测变化（使用多步场景避免立即终止）。"""
    env = _make_env(b_x=5.0)  # 目标较远，需多步
    obs, _ = env.reset()
    head_before = obs["current_net"].copy()  # (头col, 头row, 目标col, 目标row)

    # 向右一步（朝目标方向）
    obs2, reward, terminated, truncated, info = env.step(3)  # RIGHT

    # 头列应 +1
    assert obs2["current_net"][0] == head_before[0] + 1
    assert obs2["current_net"][1] == head_before[1]  # 行不变
    # 目标不变
    assert obs2["current_net"][2] == head_before[2]
    assert obs2["current_net"][3] == head_before[3]
    # 未到达终点
    assert not terminated
    assert not truncated
    # 基础步惩罚为负
    assert reward < 0.0
    # info 的 total_steps 更新
    assert info["total_steps"] == 1


def test_step_invalid_action_returns_collision_penalty() -> None:
    """非法动作应返回碰撞量级的负奖励且不推进连接。"""
    env = _make_env()
    env.reset()
    _, reward, terminated, _, _ = env.step(99)
    assert reward <= -env.COLLISION_PENALTY
    assert not terminated


# ---------------------------------------------------------------------------
# 到达终点获得正奖励
# ---------------------------------------------------------------------------
def test_reaching_target_gives_positive_reward() -> None:
    """到达终点应获得正奖励（+10 抵消步惩罚，且全部布完有 bonus）。"""
    env = _make_env(b_x=2.0)  # 源与目标相邻，一步可达
    env.reset()
    # 向右一步即到达目标
    obs, reward, terminated, truncated, info = env.step(3)  # RIGHT

    assert terminated  # 唯一连接完成 -> episode 终止
    assert not truncated
    assert reward > 0.0  # +10（到达）+ bonus（全部布完）- 1（步）> 0
    assert info["successes"] == 1
    assert info["remaining_nets"] == 0
    # 完成后占用栅格应包含已布线路径
    assert obs["grid"].sum() >= 2.0


# ---------------------------------------------------------------------------
# 碰撞获得负奖励
# ---------------------------------------------------------------------------
def test_collision_gives_negative_reward() -> None:
    """撞向器件障碍应获得碰撞量级的负奖励，且头不动。"""
    env = _make_env(b_x=2.0)
    obs, _ = env.reset()
    head_before = obs["current_net"].copy()

    # 向左一步：撞入器件 A 包围盒（障碍）-> 碰撞
    obs2, reward, terminated, _, info = env.step(2)  # LEFT

    assert reward <= -env.COLLISION_PENALTY  # -5（碰撞）-1（步）<= -5
    assert not terminated
    # 头未移动（碰撞不前进）
    assert info["head"][1] == head_before[0]  # 头列不变
    assert info["head"][0] == head_before[1]  # 头行不变


def test_out_of_bounds_collision() -> None:
    """持续向上走至越界应触发碰撞惩罚（不经过目标）。"""
    env = _make_env(b_x=5.0)
    env.reset()
    # 持续向上（北）走：列不变，不会经过右侧目标，最终越上界
    collided = False
    for _ in range(env.grid_h + 2):
        _, reward, terminated, _, _ = env.step(0)  # UP
        if terminated:
            break
        if reward <= -env.COLLISION_PENALTY:
            collided = True
            break
    assert collided, "应在越界时触发碰撞惩罚"


# ---------------------------------------------------------------------------
# 拥塞热力图正确生成
# ---------------------------------------------------------------------------
def test_congestion_map_after_routing() -> None:
    """布线一条连接后拥塞热力图应在路径格上为 >=1。"""
    env = _make_env(b_x=2.0)
    env.reset()
    env.step(3)  # 完成唯一连接

    cong = env.get_congestion_map()
    assert cong.shape == (env.grid_h, env.grid_w)
    # 路径占两格 -> 拥塞总和 >= 2
    assert cong.sum() >= 2.0
    # 至少存在一个 >=1 的格
    assert (cong >= 1.0).any()
    # 最大拥塞为 1（仅一条路径）
    assert cong.max() == pytest.approx(1.0)


def test_congestion_map_accumulates_across_nets() -> None:
    """两条共享格的连接布线后，共享格拥塞应 >=2。"""
    # 构造两连接：a.out->b.in 与 a.out->c.in（共享起点附近格）
    dev_a = _pad_device("a", "out", 1.0, 0.0, Direction.EAST)
    dev_b = _pad_device("b", "in", 0.0, 0.0, Direction.WEST)
    dev_c = _pad_device("c", "in", 0.0, 0.0, Direction.WEST)
    placements = {
        "a": Placement("a", dev_a, x=0.0, y=0.0),
        "b": Placement("b", dev_b, x=2.0, y=0.0),
        "c": Placement("c", dev_c, x=3.0, y=0.0),
    }
    net = Netlist(
        name="test",
        connections=[
            NetlistConnection("a", "out", "b", "in"),
            NetlistConnection("a", "out", "c", "in"),
        ],
    )
    env = RoutingEnv(net, placements, grid_size=1.0, min_bend_radius=5.0)
    env.reset()
    # 第一条：右一步到 b
    env.step(3)
    # 第二条：右两步到 c（经过 b 起点格 -> 交叉）
    env.step(3)
    obs, _, _, _, _ = env.step(3)

    cong = env.get_congestion_map()
    # 两条路径有重叠格时最大拥塞 >= 2
    assert cong.max() >= 2.0
    assert obs["remaining_nets"] == 0


# ---------------------------------------------------------------------------
# render 不报错
# ---------------------------------------------------------------------------
def test_render_does_not_raise() -> None:
    """render 不应抛出异常。"""
    env = _make_env()
    env.reset()
    # human 模式返回 Figure
    fig = env.render()
    assert fig is not None
    # rgb_array 模式返回 (H, W, 3) 数组
    arr = env.render(mode="rgb_array")
    assert arr is not None
    assert arr.ndim == 3
    assert arr.shape[2] == 3


def test_get_congestion_map_before_reset() -> None:
    """reset 前调用 get_congestion_map 应返回全 0 数组（不报错）。"""
    env = _make_env()
    cong = env.get_congestion_map()
    assert cong.shape == (env.grid_h, env.grid_w)
    assert cong.sum() == 0.0


# ---------------------------------------------------------------------------
# 环境约束与构造校验
# ---------------------------------------------------------------------------
def test_empty_placements_raises() -> None:
    """空 placements 应抛出 ValueError。"""
    net = Netlist(name="empty", connections=[])
    with pytest.raises(ValueError):
        RoutingEnv(net, {})


def test_no_routable_connections_raises() -> None:
    """无可布线连接（端口缺失）应抛出 ValueError。"""
    dev = _pad_device("a", "out", 1.0, 0.0, Direction.EAST)
    placements = {"a": Placement("a", dev, x=0.0, y=0.0)}
    net = Netlist(
        name="bad",
        connections=[NetlistConnection("a", "out", "missing", "in")],
    )
    with pytest.raises(ValueError):
        RoutingEnv(net, placements)


def test_invalid_grid_size_raises() -> None:
    """非正 grid_size 应抛出 ValueError。"""
    env = _make_env()
    net = env.netlist
    placements = env.placements
    with pytest.raises(ValueError):
        RoutingEnv(net, placements, grid_size=0.0)


def test_accepts_floorplan_state() -> None:
    """RoutingEnv 应接受 FloorplanState（含 .placements）。"""
    from polaris.engine.floorplan_env import FloorplanState

    dev_a = _pad_device("a", "out", 1.0, 0.0, Direction.EAST)
    dev_b = _pad_device("b", "in", 0.0, 0.0, Direction.WEST)
    state = FloorplanState(canvas_w=20.0, canvas_h=20.0, grid_size=1.0)
    state.placements = {
        "a": Placement("a", dev_a, x=0.0, y=0.0),
        "b": Placement("b", dev_b, x=2.0, y=0.0),
    }
    net = Netlist(name="t", connections=[NetlistConnection("a", "out", "b", "in")])
    env = RoutingEnv(net, state, grid_size=1.0)
    obs, _ = env.reset()
    assert env.observation_space.contains(obs)
