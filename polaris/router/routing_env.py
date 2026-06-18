"""布线环境（Routing）—— Gymnasium 接口（Task 12）。

逐连接布线动作空间 + 拥塞检测与热力图 + 奖励（损耗/长度/拥塞/DRC 违规）。

方法参考：
- Cheng et al., NeurIPS 2022 生成式布线
  来源: https://openreview.net/pdf?id=uNYqDfPEDD8
- 拥塞热力图：numpy 栅格化 + matplotlib（见 project_rules.md 规则 2.3）
"""

from __future__ import annotations

from dataclasses import dataclass, field

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from polaris.engine.floorplan_env import Placement
from polaris.engine.netlist import Netlist
from polaris.router.waveguide_router import (
    WaveguidePath,
    get_platform_constraints,
    route_connection,
)


@dataclass
class RoutingState:
    """布线状态（已布波导 + 拥塞栅格）。"""

    paths: dict[int, WaveguidePath] = field(default_factory=dict)  # conn_idx -> path
    congestion: np.ndarray = field(default_factory=lambda: np.zeros((1, 1), dtype=np.float32))
    canvas_w: float = 1000.0
    canvas_h: float = 1000.0
    grid_size: float = 5.0

    @property
    def grid_w(self) -> int:
        return int(self.canvas_w / self.grid_size)

    @property
    def grid_h(self) -> int:
        return int(self.canvas_h / self.grid_size)

    def init_congestion(self) -> None:
        self.congestion = np.zeros((self.grid_h, self.grid_w), dtype=np.float32)

    def update_congestion(self, path: WaveguidePath) -> None:
        """将波导路径栅格化累加到拥塞图。"""
        for x, y in path.points:
            gi = min(self.grid_w - 1, max(0, int(x / self.grid_size)))
            gj = min(self.grid_h - 1, max(0, int(y / self.grid_size)))
            self.congestion[gj, gi] += 1.0


@dataclass
class RoutingEnvConfig:
    """布线环境配置（画布尺寸 + 奖励权重）。

    将 ``RoutingEnv.__init__`` 的画布与奖励参数打包为单一配置对象，
    降低构造函数参数个数（规则 4.1：参数上限 7）。

    向后兼容：``RoutingEnv(config=None, **kwargs)`` 中未提供 config 时，
    旧式关键字参数（canvas_w/canvas_h/grid_size/loss_weight 等）会自动
    转发到本 dataclass 构造。
    """

    canvas_w: float = 1000.0
    canvas_h: float = 1000.0
    grid_size: float = 5.0
    loss_weight: float = 1.0
    length_weight: float = 0.001
    congestion_weight: float = 0.1
    drc_penalty: float = 50.0


class RoutingEnv(gym.Env):
    """布线环境（Gymnasium 接口）。

    动作空间：``Box`` —— 对当前连接选择布线参数（grid_offset_x, grid_offset_y,
    detour_factor），用于在 A* 基线上微调路径。
    观测空间：拥塞热力图 + 当前连接端口坐标。
    奖励：-(损耗 + 长度*权重 + 拥塞惩罚 + DRC 违规惩罚)。
    """

    metadata = {"render_modes": []}

    def __init__(
        self,
        net: Netlist,
        placements: dict[str, Placement],
        config: RoutingEnvConfig | None = None,
        **kwargs: float,
    ) -> None:
        super().__init__()
        # 向后兼容：未提供 config 时，从旧式关键字参数构建配置
        if config is None:
            config = RoutingEnvConfig(**kwargs)
        self.net = net
        self.placements = placements
        self.connections = net.connections
        self.loss_weight = config.loss_weight
        self.length_weight = config.length_weight
        self.congestion_weight = config.congestion_weight
        self.drc_penalty = config.drc_penalty

        self.state = RoutingState(
            canvas_w=config.canvas_w, canvas_h=config.canvas_h, grid_size=config.grid_size
        )
        self.grid_w = self.state.grid_w
        self.grid_h = self.state.grid_h
        self._conn_idx = 0

        # 动作：路径偏移 (dx, dy, detour) ∈ [-1,1]^3
        self.action_space = spaces.Box(low=-1.0, high=1.0, shape=(3,), dtype=np.float32)
        self.observation_space = spaces.Dict(
            {
                "congestion": spaces.Box(
                    low=0, high=1e6, shape=(self.grid_h, self.grid_w), dtype=np.float32
                ),
                "ports": spaces.Box(low=0, high=1e6, shape=(4,), dtype=np.float32),
                "step": spaces.Box(
                    low=0, high=max(1, len(self.connections)), shape=(1,), dtype=np.float32
                ),
            }
        )

    def reset(self, *, seed: int | None = None, options: dict | None = None):
        super().reset(seed=seed)
        self.state = RoutingState(
            canvas_w=self.state.canvas_w,
            canvas_h=self.state.canvas_h,
            grid_size=self.state.grid_size,
        )
        self.state.init_congestion()
        self._conn_idx = 0
        return self._obs(), {"step": 0}

    def _current_ports(self) -> tuple[tuple[float, float], tuple[float, float], str]:
        """返回当前连接的起止端口坐标与平台。"""
        conn = self.connections[self._conn_idx]
        src_pl = self.placements.get(conn.src_instance)
        dst_pl = self.placements.get(conn.dst_instance)
        start = (0.0, 0.0)
        end = (0.0, 0.0)
        platform = "SOI"
        if src_pl:
            ports = src_pl.port_positions()
            if conn.src_port in ports:
                start = ports[conn.src_port]
            platform = src_pl.device.platform
        if dst_pl:
            ports = dst_pl.port_positions()
            if conn.dst_port in ports:
                end = ports[conn.dst_port]
        return start, end, platform

    def _obs(self) -> dict:
        if self._conn_idx < len(self.connections):
            start, end, _ = self._current_ports()
            ports = np.array([start[0], start[1], end[0], end[1]], dtype=np.float32)
        else:
            ports = np.zeros(4, dtype=np.float32)
        return {
            "congestion": self.state.congestion.copy(),
            "ports": ports,
            "step": np.array([self._conn_idx], dtype=np.float32),
        }

    def step(self, action):
        if self._conn_idx >= len(self.connections):
            return self._obs(), 0.0, True, False, {}
        action = np.asarray(action, dtype=np.float32)
        start, end, platform = self._current_ports()
        cons = get_platform_constraints(platform)
        # 动作微调：偏移终点附近的中间路径点
        dx = float(action[0]) * cons["min_bend_radius_um"]
        dy = float(action[1]) * cons["min_bend_radius_um"]
        # 障碍：已放置器件（除起终点器件）
        obstacles = []
        for inst_id, pl in self.placements.items():
            if inst_id in (
                self.connections[self._conn_idx].src_instance,
                self.connections[self._conn_idx].dst_instance,
            ):
                continue
            obstacles.append(pl.bbox_abs())
        # 布线（捕获A*失败，给大惩罚）
        try:
            wp = route_connection(
                start=(start[0] + dx, start[1] + dy),
                end=end,
                platform=platform,
                grid_size=self.state.grid_size,
                canvas_w=self.state.canvas_w,
                canvas_h=self.state.canvas_h,
                obstacles=obstacles,
            )
            self.state.paths[self._conn_idx] = wp
            self.state.update_congestion(wp)
            reward = self._reward(wp)
        except Exception:
            # A*找不到路径或越界等异常 → 大惩罚，跳过此连接
            reward = -1000.0
        self._conn_idx += 1
        terminated = self._conn_idx >= len(self.connections)
        return self._obs(), reward, terminated, False, {"step": self._conn_idx}

    def _reward(self, wp: WaveguidePath) -> float:
        """奖励 = -(损耗*权重 + 长度*权重 + 拥塞惩罚 + DRC 惩罚)。"""
        loss = wp.loss_db
        length = wp.length_um
        # 拥塞：路径经过的栅格最大占用
        max_cong = float(self.state.congestion.max()) if self.state.congestion.size else 0.0
        congestion_pen = self.congestion_weight * max_cong
        # DRC：弯曲半径/间距违规（简化为路径方向变化数过多）
        drc_violations = 0
        if len(wp.points) > 3:
            for i in range(1, len(wp.points) - 1):
                dx1 = wp.points[i][0] - wp.points[i - 1][0]
                dy1 = wp.points[i][1] - wp.points[i - 1][1]
                dx2 = wp.points[i + 1][0] - wp.points[i][0]
                dy2 = wp.points[i + 1][1] - wp.points[i][1]
                if abs(dx1 - dx2) > 1e-9 or abs(dy1 - dy2) > 1e-9:
                    drc_violations += 1
        drc_pen = self.drc_penalty * drc_violations * 0.01
        reward = -(self.loss_weight * loss + self.length_weight * length + congestion_pen + drc_pen)
        return float(reward)

    def congestion_heatmap(self) -> np.ndarray:
        """返回拥塞热力图（栅格化）。"""
        return self.state.congestion.copy()

    def total_metrics(self) -> dict:
        """汇总布线指标。"""
        total_loss = sum(wp.loss_db for wp in self.state.paths.values())
        total_length = sum(wp.length_um for wp in self.state.paths.values())
        max_cong = float(self.state.congestion.max()) if self.state.congestion.size else 0.0
        return {
            "total_loss_db": total_loss,
            "total_length_um": total_length,
            "max_congestion": max_cong,
            "num_routed": len(self.state.paths),
            "num_connections": len(self.connections),
        }
