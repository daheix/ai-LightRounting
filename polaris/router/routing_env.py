"""波导布线强化学习环境（Task 12）。

逐连接（net-by-net）波导布线：智能体在栅格化画布上为每条连接导航一条
曼哈顿路径，奖励综合路径长度、弯曲数、交叉数、碰撞与总损耗。环境维护
2D 拥塞热力图，每提交一条路径即在对应网格累加计数。

方法参考（已检索核实，禁止假数据）：
- Gymnasium 自定义环境（GridWorld 范式：Dict 观测 + Discrete(4) 动作）
  来源: https://gymnasium.farama.org/v1.2.0/introduction/create_custom_env/
- NeurIPS 2022 Cheng et al. 策略梯度联合布局布线
  来源: https://openreview.net/pdf?id=uNYqDfPEDD8
- 经典 Lee/Maze 网格布线（逐连接扩展 + 拥塞计数）
  来源: C. Y. Lee, "An Algorithm for Path Connections and Its Applications,"
  IRE Trans. Electronic Computers, EC-10(3):346-365, 1961
- 弯曲半径/间距约束参考 spec.md（SOI 2-6μm / 间距 1μm）

坐标系约定（与 floorplan_env 一致）：标准数学坐标系，y 轴朝上。
栅格 array[row, col] 中 row 对应 y（向北递增），col 对应 x（向东递增）。
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from polaris.engine.floorplan_env import Placement
from polaris.engine.netlist import Netlist

# 动作 -> (d_row, d_col) 增量；row 对应 y（北为 +），col 对应 x（东为 +）
_ACTION_DELTAS: dict[int, tuple[int, int]] = {
    0: (1, 0),   # UP / 北
    1: (-1, 0),  # DOWN / 南
    2: (0, -1),  # LEFT / 西
    3: (0, 1),   # RIGHT / 东
}


@dataclass
class _RoutingState:
    """布线内部状态（栅格 + 拥塞 + 已提交路径）。"""

    obstacle: np.ndarray  # (H, W) 设备占用（静态障碍，0/1）
    routed: np.ndarray  # (H, W) 已布线路径占用（0/1）
    congestion: np.ndarray  # (H, W) 拥塞计数（每格被多少条路径经过）
    paths: list[list[tuple[int, int]]] = field(default_factory=list)
    successes: int = 0
    failures: int = 0


class RoutingEnv(gym.Env):
    """波导布线强化学习环境（逐连接布线）。

    智能体依次为网表中的每条连接导航一条网格路径：每步在四方向
   （上/下/左/右）中选择一个，移动当前连接的"头"（head）从源端口
    走向目标端口。到达目标后提交路径并切换到下一条连接，直至全部
    布完或超时。

    观测空间（``Dict``）::

        {
          "grid":          Box(0, 1, (H, W)),        # 占用栅格（障碍+已布线+当前轨迹）
          "congestion":    Box(0, inf, (H, W)),      # 拥塞热力图（每格路径计数）
          "current_net":   Box(0, inf, (4,)),        # (头col, 头row, 目标col, 目标row)
          "remaining_nets": Discrete(N+1),           # 剩余连接数
        }

    动作空间：``Discrete(4)`` —— 0:上 1:下 2:左 3:右（网格步进）。

    奖励函数（Task 12 规格）：
        - 每步 -1（鼓励最短路径）
        - 到达终点 +10
        - 碰撞/违规 -5（越界、撞器件、撞自身轨迹）
        - 弯曲 -0.5（方向改变）
        - 交叉 -1（进入已被先前路径占用的格）
        - 全部布完：bonus 基于总长度（越短奖励越高）

    Args:
        netlist: 解析后的网表（取其 ``connections``）。
        placements: ``instance_id -> Placement`` 映射；也接受
            ``FloorplanState``（自动取其 ``.placements``）。
        grid_size: 栅格分辨率（μm）。
        min_bend_radius: 最小弯曲半径（μm，用于画布边距与约束）。
        min_spacing: 最小波导间距（μm，用于拥塞阈值）。
        max_steps: 单条连接的最大步数预算。
    """

    metadata = {"render_modes": ["human", "rgb_array"]}

    # 奖励权重（来自 Task 12 规格）
    STEP_PENALTY: float = 1.0  # 每步 -1
    REACH_REWARD: float = 10.0  # 到达终点 +10
    COLLISION_PENALTY: float = 5.0  # 碰撞/违规 -5
    BEND_PENALTY: float = 0.5  # 弯曲 -0.5
    CROSSING_PENALTY: float = 1.0  # 交叉 -1
    ALL_DONE_BASE: float = 20.0  # 全部布完基础奖励
    LENGTH_BONUS_WEIGHT: float = 0.01  # 总长度对 bonus 的扣减系数
    DEFAULT_LOSS_DB_CM: float = 2.0  # 默认传播损耗（SOI strip，dB/cm）

    def __init__(
        self,
        netlist: Netlist,
        placements,
        grid_size: float = 1.0,
        min_bend_radius: float = 5.0,
        min_spacing: float = 1.0,
        max_steps: int = 1000,
    ) -> None:
        super().__init__()
        if grid_size <= 0:
            raise ValueError("grid_size 须为正数")
        if max_steps <= 0:
            raise ValueError("max_steps 须为正数")
        # 兼容传入 FloorplanState（含 .placements 字典）
        if hasattr(placements, "placements"):
            placements = placements.placements
        if not placements:
            raise ValueError("placements 不能为空")

        self.netlist = netlist
        self.placements: dict[str, Placement] = dict(placements)
        self.grid_size = float(grid_size)
        self.min_bend_radius = float(min_bend_radius)
        self.min_spacing = float(min_spacing)
        self.max_steps = int(max_steps)

        # 画布范围：所有已放置器件包围盒 + 边距（容纳弯曲半径）
        bboxes = [pl.bbox_abs() for pl in self.placements.values()]
        xmin = min(b[0] for b in bboxes)
        ymin = min(b[1] for b in bboxes)
        xmax = max(b[2] for b in bboxes)
        ymax = max(b[3] for b in bboxes)
        margin = max(self.min_bend_radius, 5.0 * self.grid_size)
        self.origin_x = xmin - margin
        self.origin_y = ymin - margin
        self.canvas_w = (xmax - xmin) + 2.0 * margin
        self.canvas_h = (ymax - ymin) + 2.0 * margin
        self.grid_w = max(1, int(math.ceil(self.canvas_w / self.grid_size)))
        self.grid_h = max(1, int(math.ceil(self.canvas_h / self.grid_size)))

        # 构建连接端点列表（栅格坐标 (src_row, src_col, dst_row, dst_col)）
        self.nets: list[tuple[int, int, int, int]] = []
        for conn in netlist.connections:
            src = self._port_grid(conn.src_instance, conn.src_port)
            dst = self._port_grid(conn.dst_instance, conn.dst_port)
            if src is None or dst is None:
                continue
            self.nets.append((src[0], src[1], dst[0], dst[1]))
        if not self.nets:
            raise ValueError("网表中无可布线连接（端口均未放置或缺失）")

        # 静态障碍栅格（器件占用）
        self._base_obstacle = self._build_obstacle_grid()

        # 动作空间：4 方向
        self.action_space = spaces.Discrete(4)
        # 观测空间
        self.observation_space = spaces.Dict({
            "grid": spaces.Box(
                low=0.0, high=1.0, shape=(self.grid_h, self.grid_w), dtype=np.float32
            ),
            "congestion": spaces.Box(
                low=0.0, high=np.inf, shape=(self.grid_h, self.grid_w), dtype=np.float32
            ),
            "current_net": spaces.Box(low=0.0, high=np.inf, shape=(4,), dtype=np.float32),
            "remaining_nets": spaces.Discrete(len(self.nets) + 1),
        })

        # 运行时状态（reset 后填充）
        self._state: _RoutingState | None = None
        self._net_idx = 0
        self._head: tuple[int, int] = (0, 0)  # (row, col)
        self._target: tuple[int, int] = (0, 0)
        self._trail: list[tuple[int, int]] = []
        self._prev_dir: int | None = None
        self._net_step = 0
        self._total_steps = 0
        self._total_length = 0.0

    # ------------------------------------------------------------------
    # 坐标转换
    # ------------------------------------------------------------------
    def _to_grid(self, x: float, y: float) -> tuple[int, int]:
        """画布坐标 (μm) -> 栅格 (row, col)，并裁剪到画布内。"""
        col = int(round((x - self.origin_x) / self.grid_size))
        row = int(round((y - self.origin_y) / self.grid_size))
        col = max(0, min(self.grid_w - 1, col))
        row = max(0, min(self.grid_h - 1, row))
        return row, col

    def _port_grid(self, inst_id: str, port_name: str) -> tuple[int, int] | None:
        """取器件端口的栅格坐标；器件或端口缺失时返回 None。"""
        pl = self.placements.get(inst_id)
        if pl is None:
            return None
        ports = pl.port_positions()
        if port_name not in ports:
            return None
        px, py = ports[port_name]
        return self._to_grid(px, py)

    def _build_obstacle_grid(self) -> np.ndarray:
        """构建静态障碍栅格（器件包围盒占用）。"""
        grid = np.zeros((self.grid_h, self.grid_w), dtype=np.float32)
        for pl in self.placements.values():
            xmin, ymin, xmax, ymax = pl.bbox_abs()
            c0 = int(math.floor((xmin - self.origin_x) / self.grid_size))
            c1 = int(math.ceil((xmax - self.origin_x) / self.grid_size))
            r0 = int(math.floor((ymin - self.origin_y) / self.grid_size))
            r1 = int(math.ceil((ymax - self.origin_y) / self.grid_size))
            r0 = max(0, r0)
            r1 = min(self.grid_h, r1)
            c0 = max(0, c0)
            c1 = min(self.grid_w, c1)
            if r0 < r1 and c0 < c1:
                grid[r0:r1, c0:c1] = 1.0
        return grid

    # ------------------------------------------------------------------
    # Gymnasium 接口
    # ------------------------------------------------------------------
    def reset(self, *, seed: int | None = None, options: dict | None = None):
        """重置环境，返回第一个待布线连接的观测。"""
        super().reset(seed=seed)
        self._state = _RoutingState(
            obstacle=self._base_obstacle.copy(),
            routed=np.zeros((self.grid_h, self.grid_w), dtype=np.float32),
            congestion=np.zeros((self.grid_h, self.grid_w), dtype=np.float32),
        )
        self._net_idx = 0
        self._total_steps = 0
        self._total_length = 0.0
        self._setup_current_net()
        return self._obs(), self._info()

    def _setup_current_net(self) -> None:
        """初始化当前连接的头位置、目标与轨迹（跳过退化连接）。"""
        while self._net_idx < len(self.nets):
            sr, sc, dr, dc = self.nets[self._net_idx]
            assert self._state is not None
            # 清除起止格障碍（端口可能落在器件包围盒内，便于起止）
            self._state.obstacle[sr, sc] = 0.0
            self._state.obstacle[dr, dc] = 0.0
            self._head = (sr, sc)
            self._target = (dr, dc)
            self._trail = [(sr, sc)]
            self._prev_dir = None
            self._net_step = 0
            # 退化连接（起止同格）：直接提交单格路径并跳到下一条
            if (sr, sc) == (dr, dc):
                self._commit_path()
                self._net_idx += 1
                continue
            return
        # 已无待布线连接

    def _commit_path(self) -> None:
        """提交当前轨迹到已布线栅格与拥塞图。"""
        assert self._state is not None
        for r, c in self._trail:
            self._state.routed[r, c] = 1.0
            self._state.congestion[r, c] += 1.0
        self._state.paths.append(list(self._trail))
        self._state.successes += 1
        # 路径长度近似为 (格数-1) * grid_size（曼哈顿步进）
        self._total_length += (len(self._trail) - 1) * self.grid_size

    def step(self, action):
        """执行一步布线动作，返回 (observation, reward, terminated, truncated, info)。"""
        if self._net_idx >= len(self.nets):
            return self._obs(), 0.0, True, False, self._info()

        action = int(action)
        if action not in _ACTION_DELTAS:
            return self._obs(), -self.COLLISION_PENALTY, False, False, self._info()

        dr, dc = _ACTION_DELTAS[action]
        hr, hc = self._head
        nr, nc = hr + dr, hc + dc
        reward = -self.STEP_PENALTY  # 每步基础惩罚

        # 碰撞检测：越界 / 静态障碍 / 自身轨迹（防回环）
        collision = False
        if not (0 <= nr < self.grid_h and 0 <= nc < self.grid_w):
            collision = True
        elif self._state is not None and self._state.obstacle[nr, nc] > 0:
            collision = True
        elif (nr, nc) in self._trail:
            collision = True

        if collision:
            # 碰撞：头不动，仅消耗一步并惩罚
            reward -= self.COLLISION_PENALTY
        else:
            assert self._state is not None
            # 交叉惩罚：进入已被先前路径占用的格
            if self._state.routed[nr, nc] > 0:
                reward -= self.CROSSING_PENALTY
            # 弯曲惩罚：方向改变
            if self._prev_dir is not None and self._prev_dir != action:
                reward -= self.BEND_PENALTY
            self._head = (nr, nc)
            self._trail.append((nr, nc))
            self._prev_dir = action

        self._net_step += 1
        self._total_steps += 1

        terminated = False
        truncated = False

        # 到达终点：提交路径并切换下一条连接
        if self._head == self._target:
            reward += self.REACH_REWARD
            self._commit_path()
            self._net_idx += 1
            if self._net_idx >= len(self.nets):
                # 全部布完：基于总长度的 bonus（越短奖励越高）
                bonus = max(
                    0.0,
                    self.ALL_DONE_BASE - self.LENGTH_BONUS_WEIGHT * self._total_length,
                )
                reward += bonus
                terminated = True
            else:
                self._setup_current_net()
        elif self._net_step >= self.max_steps:
            # 当前连接超时失败：惩罚并跳到下一条
            reward -= self.COLLISION_PENALTY
            assert self._state is not None
            self._state.failures += 1
            self._net_idx += 1
            if self._net_idx >= len(self.nets):
                terminated = True
            else:
                self._setup_current_net()

        # 总步数硬上限（保证 episode 一定终止）
        if self._total_steps >= self.max_steps * (len(self.nets) + 1):
            truncated = True

        return self._obs(), float(reward), terminated, truncated, self._info()

    # ------------------------------------------------------------------
    # 观测 / 信息
    # ------------------------------------------------------------------
    def _obs(self) -> dict:
        """构建观测字典。"""
        assert self._state is not None
        # 占用栅格 = 障碍 ∪ 已布线 ∪ 当前轨迹（含头）
        grid = np.maximum(self._state.obstacle, self._state.routed)
        trail_mask = np.zeros_like(grid)
        for r, c in self._trail:
            if 0 <= r < self.grid_h and 0 <= c < self.grid_w:
                trail_mask[r, c] = 1.0
        grid = np.maximum(grid, trail_mask).astype(np.float32)
        hr, hc = self._head
        tr, tc = self._target
        # current_net = (头col, 头row, 目标col, 目标row)
        current_net = np.array([hc, hr, tc, tr], dtype=np.float32)
        remaining = max(0, len(self.nets) - self._net_idx)
        return {
            "grid": grid,
            "congestion": self._state.congestion.astype(np.float32),
            "current_net": current_net,
            "remaining_nets": int(remaining),
        }

    def _info(self) -> dict:
        """构建辅助信息字典。"""
        return {
            "net_index": self._net_idx,
            "num_nets": len(self.nets),
            "remaining_nets": max(0, len(self.nets) - self._net_idx),
            "net_step": self._net_step,
            "total_steps": self._total_steps,
            "head": self._head,
            "target": self._target,
            "total_length": self._total_length,
            "total_loss_db": self._total_length * 1e-4 * self.DEFAULT_LOSS_DB_CM,
            "successes": self._state.successes if self._state is not None else 0,
            "failures": self._state.failures if self._state is not None else 0,
        }

    # ------------------------------------------------------------------
    # 拥塞热力图 / 渲染
    # ------------------------------------------------------------------
    def get_congestion_map(self) -> np.ndarray:
        """返回拥塞热力图（2D 栅格，每格=布线密度/路径计数）。"""
        if self._state is None:
            return np.zeros((self.grid_h, self.grid_w), dtype=np.float32)
        return self._state.congestion.astype(np.float32)

    def render(self, mode: str = "human"):
        """渲染当前布线状态（matplotlib 栅格图）。

        Args:
            mode: ``"human"`` 返回 matplotlib Figure；``"rgb_array"``
                返回 (H, W, 3) numpy 数组。

        Returns:
            matplotlib Figure 或 RGB 数组。
        """
        import matplotlib.pyplot as plt

        assert self._state is not None
        disp = np.zeros((self.grid_h, self.grid_w), dtype=np.float32)
        disp[self._state.obstacle > 0] = 0.3  # 障碍（器件）灰
        disp[self._state.routed > 0] = 0.6  # 已布线
        for r, c in self._trail:
            if 0 <= r < self.grid_h and 0 <= c < self.grid_w:
                disp[r, c] = 0.8  # 当前轨迹
        hr, hc = self._head
        tr, tc = self._target
        if 0 <= hr < self.grid_h and 0 <= hc < self.grid_w:
            disp[hr, hc] = 1.0  # 头
        # 目标若与头不同则单独标记（用次高值，避免与头冲突）
        if (tr, tc) != (hr, hc) and 0 <= tr < self.grid_h and 0 <= tc < self.grid_w:
            disp[tr, tc] = 0.95

        fig, ax = plt.subplots()
        ax.imshow(disp, origin="lower", cmap="viridis")
        ax.set_title("RoutingEnv state (yellow=head, purple=obstacle)")
        ax.set_xlabel("col (x)")
        ax.set_ylabel("row (y)")
        if mode == "rgb_array":
            fig.canvas.draw()
            arr = np.asarray(fig.canvas.buffer_rgba())
            plt.close(fig)
            return arr[:, :, :3]
        return fig


__all__ = ["RoutingEnv"]
