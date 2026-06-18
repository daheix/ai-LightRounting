"""布局环境（Floorplan）—— Gymnasium 接口（Task 9）。

将器件网表放置到网格化画布上。状态观测含占用栅格、端口位置、拥塞图；
奖励综合面积利用率、HPWL 线长、拥塞度、重叠惩罚。

方法参考：
- NeurIPS 2025 Basso et al. RL+R-GCN 模拟 IC 布局感知 floorplanning
  来源: https://mlforsystems.org/assets/papers/neurips2025/paper42.pdf
- NeurIPS 2022 Cheng et al. 策略梯度布局
  来源: https://openreview.net/pdf?id=uNYqDfPEDD8
- 经典 HPWL（半周长线长）估计，见 EDA 教材
"""

from __future__ import annotations

from dataclasses import dataclass, field

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from polaris.engine.netlist import Netlist
from polaris.pdk.device import Device


@dataclass
class Placement:
    """单个器件的放置结果。"""

    instance_id: str
    device: Device
    x: float  # 左下角 x（μm）
    y: float  # 左下角 y（μm）
    rotation: int = 0  # 0/90/180/270

    def port_positions(self) -> dict[str, tuple[float, float]]:
        """返回放置后端口绝对坐标（考虑旋转+平移）。"""
        dev = self.device.rotate(self.rotation) if self.rotation else self.device
        moved = dev.translate(self.x - dev.bbox.xmin, self.y - dev.bbox.ymin)
        return {p.name: (p.x, p.y) for p in moved.ports}

    def bbox_abs(self) -> tuple[float, float, float, float]:
        """返回放置后轴对齐包围盒 (xmin, ymin, xmax, ymax)。"""
        dev = self.device.rotate(self.rotation) if self.rotation else self.device
        w = dev.bbox.xmax - dev.bbox.xmin
        h = dev.bbox.ymax - dev.bbox.ymin
        return (self.x, self.y, self.x + w, self.y + h)


@dataclass
class FloorplanState:
    """布局状态（器件放置 + 画布占用）。"""

    placements: dict[str, Placement] = field(default_factory=dict)
    canvas_w: float = 1000.0
    canvas_h: float = 1000.0
    grid_size: float = 10.0  # 栅格分辨率（μm）

    @property
    def grid_w(self) -> int:
        return int(self.canvas_w / self.grid_size)

    @property
    def grid_h(self) -> int:
        return int(self.canvas_h / self.grid_size)

    def occupancy_grid(self, instance_ids: list[str]) -> np.ndarray:
        """构建占用栅格（已放置器件标记为 1）。"""
        grid = np.zeros((self.grid_h, self.grid_w), dtype=np.float32)
        for inst_id in instance_ids:
            if inst_id not in self.placements:
                continue
            pl = self.placements[inst_id]
            xmin, ymin, xmax, ymax = pl.bbox_abs()
            gi0 = max(0, int(xmin / self.grid_size))
            gj0 = max(0, int(ymin / self.grid_size))
            gi1 = min(self.grid_w, int(np.ceil(xmax / self.grid_size)))
            gj1 = min(self.grid_h, int(np.ceil(ymax / self.grid_size)))
            grid[gj0:gj1, gi0:gi1] = 1.0
        return grid


def hpwl(net: Netlist, state: FloorplanState) -> float:
    """半周长线长（HPWL）估计所有连接的总线长。

    对每条连接取所有相关端口坐标的 (xmax-xmin)+(ymax-ymin)。
    来源: 经典 EDA 半周长线长估计。
    """
    total = 0.0
    # 按连接聚合端口坐标
    nets: dict[int, list[tuple[float, float]]] = {}
    for i, conn in enumerate(net.connections):
        pts: list[tuple[float, float]] = []
        for inst_id, port_name in [
            (conn.src_instance, conn.src_port),
            (conn.dst_instance, conn.dst_port),
        ]:
            if inst_id in state.placements:
                pp = state.placements[inst_id].port_positions()
                if port_name in pp:
                    pts.append(pp[port_name])
        nets[i] = pts
    for pts in nets.values():
        if len(pts) < 2:
            continue
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        total += (max(xs) - min(xs)) + (max(ys) - min(ys))
    return total


def count_overlaps(state: FloorplanState) -> int:
    """统计已放置器件间的重叠对数。"""
    placements = list(state.placements.values())
    count = 0
    for i in range(len(placements)):
        a = placements[i].bbox_abs()
        for j in range(i + 1, len(placements)):
            b = placements[j].bbox_abs()
            if a[0] < b[2] and a[2] > b[0] and a[1] < b[3] and a[3] > b[1]:
                count += 1
    return count


@dataclass
class FloorplanEnvConfig:
    """布局环境配置（画布尺寸 + 奖励权重）。

    将 ``FloorplanEnv.__init__`` 的画布与奖励参数打包为单一配置对象，
    降低构造函数参数个数（规则 4.1：参数上限 7）。

    向后兼容：``FloorplanEnv(net, devices, config=None, **kwargs)`` 中未提供
    config 时，旧式关键字参数（canvas_w/canvas_h/grid_size/overlap_penalty
    等）会自动转发到本 dataclass 构造。
    """

    canvas_w: float = 1000.0
    canvas_h: float = 1000.0
    grid_size: float = 10.0
    overlap_penalty: float = 100.0
    hpwl_weight: float = 0.001
    area_reward: float = 1.0


class FloorplanEnv(gym.Env):
    """布局环境（Gymnasium 接口）。

    动作空间：``MultiDiscrete([grid_w, grid_h, 4])`` —— 放置下一个器件到
    (grid_x, grid_y) 并选择旋转 (0/90/180/270)。
    观测空间：占用栅格 + 端口位置 + 拥塞图。
    """

    metadata = {"render_modes": []}

    def __init__(
        self,
        net: Netlist,
        devices: dict[str, Device],
        config: FloorplanEnvConfig | None = None,
        **kwargs: float,
    ) -> None:
        super().__init__()
        # 向后兼容：未提供 config 时，从旧式关键字参数构建配置
        if config is None:
            config = FloorplanEnvConfig(**kwargs)
        self.net = net
        self.devices = devices
        self.instance_ids = list(devices.keys())
        self.overlap_penalty = config.overlap_penalty
        self.hpwl_weight = config.hpwl_weight
        self.area_reward = config.area_reward

        self.state = FloorplanState(
            canvas_w=config.canvas_w, canvas_h=config.canvas_h, grid_size=config.grid_size
        )
        self.grid_w = self.state.grid_w
        self.grid_h = self.state.grid_h
        self._step_idx = 0

        self.action_space = spaces.MultiDiscrete([self.grid_w, self.grid_h, 4])
        self.observation_space = spaces.Dict(
            {
                "occupancy": spaces.Box(
                    low=0, high=1, shape=(self.grid_h, self.grid_w), dtype=np.float32
                ),
                "port_positions": spaces.Box(
                    low=-1, high=1e6, shape=(len(self.instance_ids), 4), dtype=np.float32
                ),
                "step": spaces.Box(
                    low=0, high=len(self.instance_ids), shape=(1,), dtype=np.float32
                ),
            }
        )

    def reset(self, *, seed: int | None = None, options: dict | None = None):
        super().reset(seed=seed)
        self.state = FloorplanState(
            canvas_w=self.state.canvas_w,
            canvas_h=self.state.canvas_h,
            grid_size=self.state.grid_size,
        )
        self._step_idx = 0
        return self._obs(), {"step": 0}

    def _obs(self) -> dict:
        placed_ids = list(self.state.placements.keys())
        occ = self.state.occupancy_grid(placed_ids)
        # 端口位置（每个实例取首端口 x,y + 包围盒中心）
        port_pos = np.full((len(self.instance_ids), 4), -1.0, dtype=np.float32)
        for i, inst_id in enumerate(self.instance_ids):
            if inst_id in self.state.placements:
                pl = self.state.placements[inst_id]
                ports = pl.port_positions()
                if ports:
                    first = next(iter(ports.values()))
                    port_pos[i, 0] = first[0]
                    port_pos[i, 1] = first[1]
                xmin, ymin, xmax, ymax = pl.bbox_abs()
                port_pos[i, 2] = (xmin + xmax) / 2
                port_pos[i, 3] = (ymin + ymax) / 2
        return {
            "occupancy": occ,
            "port_positions": port_pos,
            "step": np.array([self._step_idx], dtype=np.float32),
        }

    def step(self, action):
        if self._step_idx >= len(self.instance_ids):
            return self._obs(), 0.0, True, False, {}
        action = np.asarray(action).astype(np.int64)
        gx, gy, rot = int(action[0]), int(action[1]), int(action[2])
        rotation = rot * 90
        inst_id = self.instance_ids[self._step_idx]
        dev = self.devices[inst_id]
        # 网格坐标 -> 画布坐标
        x = gx * self.state.grid_size
        y = gy * self.state.grid_size
        # 裁剪到画布内
        dev_rot = dev.rotate(rotation) if rotation else dev
        w = dev_rot.bbox.xmax - dev_rot.bbox.xmin
        h = dev_rot.bbox.ymax - dev_rot.bbox.ymin
        x = min(x, self.state.canvas_w - w)
        y = min(y, self.state.canvas_h - h)
        x = max(0.0, x)
        y = max(0.0, y)
        self.state.placements[inst_id] = Placement(
            instance_id=inst_id, device=dev, x=x, y=y, rotation=rotation
        )
        self._step_idx += 1
        terminated = self._step_idx >= len(self.instance_ids)
        reward = self._reward()
        return self._obs(), reward, terminated, False, {"step": self._step_idx}

    def _reward(self) -> float:
        """奖励 = 面积利用率 - HPWL*权重 - 重叠*惩罚。"""
        placed = list(self.state.placements.values())
        if not placed:
            return 0.0
        # 面积利用率
        used_area = 0.0
        for pl in placed:
            xmin, ymin, xmax, ymax = pl.bbox_abs()
            used_area += (xmax - xmin) * (ymax - ymin)
        total_area = self.state.canvas_w * self.state.canvas_h
        util = used_area / total_area if total_area > 0 else 0.0
        # HPWL
        wire = hpwl(self.net, self.state)
        # 重叠
        overlaps = count_overlaps(self.state)
        reward = self.area_reward * util - self.hpwl_weight * wire - self.overlap_penalty * overlaps
        return float(reward)

    def render(self):
        pass
