"""布线环境（Routing）—— Gymnasium 接口（Task 12）。

逐连接布线动作空间 + 拥塞检测与热力图 + 奖励（损耗/长度/拥塞/DRC 违规）。

方法参考：
- Cheng et al., NeurIPS 2022 生成式布线
  来源: https://openreview.net/pdf?id=uNYqDfPEDD8
- 拥塞热力图：numpy 栅格化 + matplotlib（见 project_rules.md 规则 2.3）
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from polaris.engine.floorplan_env import Placement
from polaris.engine.netlist import Netlist
from polaris.router.global_router import (
    CanvasSize,
    GlobalRouter,
    GlobalRouterConfig,
)
from polaris.router.waveguide_router import (
    WaveguidePath,
    get_platform_constraints,
    route_connection,
)

logger = logging.getLogger(__name__)


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

    Attributes:
        canvas_w: 画布宽度（μm）。
        canvas_h: 画布高度（μm）。
        grid_size: 栅格分辨率（μm）。
        loss_weight: 损耗奖励权重。
        length_weight: 长度奖励权重。
        congestion_weight: 拥塞惩罚权重。
        drc_penalty: DRC 违规惩罚。
        reward_clip_max: Reward clipping 上限。
        use_global_router: 是否启用全局布线层（P1-2，第6轮）。
            启用后 reset() 时先跑 GlobalRouter 生成全局路径与拥塞预估，
            将全局拥塞图作为额外观测通道 ``global_congestion`` 注入 obs。
            来源: Cadence Innovus 全局-详细分层布线
            https://community.cadence.com/cadence_blogs_8/b/di/posts/unlocking-ppa-with-innovus-what-s-new-and-how-to-unleash-it
        global_router_gcell_size_um: 全局布线 GCell 边长（μm），仅
            use_global_router=True 时生效。
    """

    canvas_w: float = 1000.0
    canvas_h: float = 1000.0
    grid_size: float = 5.0
    # RL 奖励权重（经验调参值，来源: LiDAR ISPD'25 RL routing
    # https://arxiv.org/abs/2504.18813 + PPO reward clipping 最佳实践 SB3）
    loss_weight: float = 1.0
    length_weight: float = 0.001
    congestion_weight: float = 0.1
    drc_penalty: float = 10.0
    # Reward clipping 上限（第二波训练收敛修复）：单步 reward 限制在
    # [-reward_clip_max, 0] 范围，防止异常长路径或累积 DRC 违规产生
    # -1000~-9000 的灾难值摧毁价值函数（历史 progress.json 显示极端值）。
    # 来源: PPO reward clipping 最佳实践，参考 SB3 RewardWrapper
    reward_clip_max: float = 20.0
    # P1-2 全局布线层（第6轮）
    use_global_router: bool = False
    global_router_gcell_size_um: float = 50.0


@dataclass
class _RouteParams:
    """单连接布线参数打包（降低 ``_try_route`` 参数个数，规则 7.1）。

    将 ``step()`` 收集的 6 个布线参数（起止坐标、平台、偏移、障碍）打包为
    单一对象传给 ``_try_route``，使函数参数个数从 7 降到 2（self + params）。
    """

    start: tuple[float, float]
    end: tuple[float, float]
    platform: str
    dx: float
    dy: float
    obstacles: list


class RoutingEnv(gym.Env):
    """布线环境（Gymnasium 接口）。

    动作空间：``Box`` —— 对当前连接选择布线参数（grid_offset_x, grid_offset_y,
    detour_factor），用于在 A* 基线上微调路径。
    观测空间：拥塞热力图 + 当前连接端口坐标。
    奖励：-(损耗 + 长度*权重 + 拥塞惩罚 + DRC 违规惩罚)。
    """

    metadata = {"render_modes": []}

    def _init_action_observation_spaces(self, config: RoutingEnvConfig) -> None:
        """初始化动作空间和观测空间。

        Args:
            config: 路由环境配置。
        """
        # 动作：路径偏移 (dx, dy, detour) ∈ [-1,1]^3
        self.action_space = spaces.Box(low=-1.0, high=1.0, shape=(3,), dtype=np.float32)
        # 观测空间：基础 + 可选全局拥塞通道
        obs_spaces = {
            "congestion": spaces.Box(
                low=0, high=1e6, shape=(self.grid_h, self.grid_w), dtype=np.float32
            ),
            "ports": spaces.Box(low=0, high=1e6, shape=(4,), dtype=np.float32),
            "step": spaces.Box(
                low=0, high=max(1, len(self.connections)), shape=(1,), dtype=np.float32
            ),
        }
        if self.use_global_router:
            # 全局拥塞图通道（GCell 网格大小，与详细栅格不同）
            gw = max(1, int(config.canvas_w / self.global_router_gcell_size_um))
            gh = max(1, int(config.canvas_h / self.global_router_gcell_size_um))
            obs_spaces["global_congestion"] = spaces.Box(
                low=-1e6, high=1e6, shape=(gh, gw), dtype=np.float32
            )
        self.observation_space = spaces.Dict(obs_spaces)

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
        self.reward_clip_max = config.reward_clip_max
        self.use_global_router = config.use_global_router
        self.global_router_gcell_size_um = config.global_router_gcell_size_um

        self.state = RoutingState(
            canvas_w=config.canvas_w, canvas_h=config.canvas_h, grid_size=config.grid_size
        )
        self.grid_w = self.state.grid_w
        self.grid_h = self.state.grid_h
        self._conn_idx = 0
        # 全局布线结果（use_global_router=True 时在 reset 中填充）
        self._global_routes: list = []
        self._global_congestion: np.ndarray | None = None
        # P0-2 规模扩展（第11轮）：缓存所有器件的 bbox_abs()，避免每连接
        # 重复计算旋转/平移。placements 在 episode 期间不变，reset 时刷新。
        self._obstacle_bboxes: list[tuple[float, float, float, float]] = []
        self._obstacle_inst_ids: list[str] = []
        self._init_action_observation_spaces(config)

    def reset(self, *, seed: int | None = None, options: dict | None = None):
        super().reset(seed=seed)
        self.state = RoutingState(
            canvas_w=self.state.canvas_w,
            canvas_h=self.state.canvas_h,
            grid_size=self.state.grid_size,
        )
        self.state.init_congestion()
        self._conn_idx = 0
        # P0-2 规模扩展（第11轮）：刷新障碍 bbox 缓存。
        # placements 在 episode 期间不变，缓存后 _collect_obstacles() 从
        # O(N) 降为 O(N) 一次（reset 时）+ O(1) 每连接（仅过滤起终点）。
        self._obstacle_bboxes = [pl.bbox_abs() for pl in self.placements.values()]
        self._obstacle_inst_ids = list(self.placements.keys())
        # P1-2 全局布线层（第6轮）：reset 时先跑 GlobalRouter 生成全局路径
        # 与拥塞预估，对齐 Cadence Innovus 全局-详细分层布线架构。
        # 来源: https://community.cadence.com/cadence_blogs_8/b/di/posts/unlocking-ppa-with-innovus-what-s-new-and-how-to-unleash-it
        if self.use_global_router:
            self._run_global_routing()
        return self._obs(), {"step": 0}

    def _run_global_routing(self) -> None:
        """执行全局布线并存储结果与拥塞图。

        在 reset() 中调用，生成全局路径 ``self._global_routes`` 和
        GCell 级拥塞图 ``self._global_congestion``。后者作为额外观测
        通道注入 obs，让 RL agent 感知全局拥塞分布。
        """
        gr_config = GlobalRouterConfig(gcell_size_um=self.global_router_gcell_size_um)
        router = GlobalRouter(
            net=self.net,
            placements=self.placements,
            canvas=CanvasSize(width=self.state.canvas_w, height=self.state.canvas_h),
            config=gr_config,
        )
        self._global_routes = router.route()
        self._global_congestion = router.congestion_map().astype(np.float32)

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
            ports = np.array(
                [
                    start[0] / self.state.canvas_w,
                    start[1] / self.state.canvas_h,
                    end[0] / self.state.canvas_w,
                    end[1] / self.state.canvas_h,
                ],
                dtype=np.float32,
            )
        else:
            ports = np.zeros(4, dtype=np.float32)
        obs = {
            "congestion": self.state.congestion.copy() / max(1.0, self.state.congestion.max()),
            "ports": ports,
            "step": np.array([self._conn_idx], dtype=np.float32),
        }
        # P1-2 全局布线层（第6轮）：注入 GCell 级全局拥塞图作为额外观测通道
        if self.use_global_router:
            if self._global_congestion is None:
                # 防御性填充：未跑全局布线时填零（不应发生，reset 已调用）
                # 记录警告以便追踪问题，不作为正常路径
                import logging
                logging.getLogger(__name__).warning(
                    "全局拥塞图为 None，使用零填充。这不应发生（reset 应已初始化）。"
                )
                gw = max(1, int(self.state.canvas_w / self.global_router_gcell_size_um))
                gh = max(1, int(self.state.canvas_h / self.global_router_gcell_size_um))
                obs["global_congestion"] = np.zeros((gh, gw), dtype=np.float32)
            else:
                obs["global_congestion"] = self._global_congestion.copy()
        return obs

    def step(self, action):
        if self._conn_idx >= len(self.connections):
            return self._obs(), 0.0, True, False, {}
        action = np.asarray(action, dtype=np.float32)
        start, end, platform = self._current_ports()
        cons = get_platform_constraints(platform)
        dx = float(action[0]) * cons["min_bend_radius_um"]
        dy = float(action[1]) * cons["min_bend_radius_um"]
        detour = float(action[2])
        obstacles = self._collect_obstacles()
        if detour > 0.1:
            _add_detour_obstacles(
                obstacles,
                start=(start[0] + dx, start[1] + dy),
                end=end,
                detour_factor=detour,
                grid_size=self.state.grid_size,
            )
        reward = self._try_route(
            _RouteParams(start=start, end=end, platform=platform, dx=dx, dy=dy, obstacles=obstacles)
        )
        # P1-2 优化（第8轮）：在 _conn_idx 自增前获取当前连接的全局 waypoints，
        # 供上层调用者（训练脚本/评估脚本）利用全局路径引导详细布线。
        global_waypoints = self._current_global_waypoints() if self.use_global_router else None
        self._conn_idx += 1
        terminated = self._conn_idx >= len(self.connections)
        info = {"step": self._conn_idx}
        if self.use_global_router:
            info["global_waypoints"] = global_waypoints
        return self._obs(), reward, terminated, False, info

    def _current_global_waypoints(self) -> list[tuple[float, float]]:
        """返回当前连接的全局布线 waypoints（μm 坐标）。

        P1-2 优化（第8轮）：从 ``self._global_routes`` 中检索当前连接的
        全局路径，返回其 waypoints 供详细布线引导。

        来源: Cadence Innovus 全局-详细分层布线
        https://community.cadence.com/cadence_blogs_8/b/di/posts/unlocking-ppa-with-innovus-what-s-new-and-how-to-unleash-it

        Returns:
            waypoints 列表（μm 坐标），无全局路径时返回空列表。
        """
        if not self._global_routes:
            return []
        for gr in self._global_routes:
            if gr.conn_idx == self._conn_idx:
                return list(gr.waypoints)
        return []

    def _try_route(self, params: _RouteParams) -> float:
        """执行单连接布线，返回 reward。失败时返回适度惩罚。"""
        try:
            wp = route_connection(
                start=(params.start[0] + params.dx, params.start[1] + params.dy),
                end=params.end,
                platform=params.platform,
                grid_size=self.state.grid_size,
                canvas_w=self.state.canvas_w,
                canvas_h=self.state.canvas_h,
                obstacles=params.obstacles,
            )
            self.state.paths[self._conn_idx] = wp
            self.state.update_congestion(wp)
            return self._reward(wp)
        except (ValueError, IndexError, RuntimeError) as exc:
            # A*找不到路径或越界等异常 → 适度惩罚（非 -1000 灾难值）
            logger.warning(
                "连接 %d 布线失败: %s (start=%s, end=%s)",
                self._conn_idx,
                exc,
                params.start,
                params.end,
            )
            return -(self.loss_weight * 10.0 + self.drc_penalty * 0.1)

    def _collect_obstacles(self) -> list:
        """收集当前连接的布线障碍（已放置器件，排除起终点器件）。

        P0-2 规模扩展（第11轮）：从 reset() 时缓存的 bbox 列表中过滤起终点，
        避免每连接重复计算 bbox_abs()（旋转+平移）。500 器件 × 500 连接
        从 25 万次 bbox 计算降为 500 次（reset 时一次性计算）。
        """
        conn = self.connections[self._conn_idx]
        src, dst = conn.src_instance, conn.dst_instance
        obstacles: list = []
        for inst_id, bbox in zip(self._obstacle_inst_ids, self._obstacle_bboxes):
            if inst_id == src or inst_id == dst:
                continue
            obstacles.append(bbox)
        return obstacles

    def _reward(self, wp: WaveguidePath) -> float:
        """奖励 = -(损耗*权重 + 长度*权重 + 拥塞惩罚 + DRC 惩罚)。

        DRC 惩罚检查弯曲半径是否过小（急转弯），而非方向变化数。
        波导本身需要弯曲，方向变化是合法的；只有弯曲半径小于工艺
        最小值才是 DRC 违规。

        第二波训练收敛修复：添加 reward clipping，限制单步 reward 在
        [-reward_clip_max, 0] 范围，防止异常长路径或累积 DRC 违规
        产生灾难值摧毁价值函数。
        """
        loss = wp.loss_db
        length = wp.length_um
        # 拥塞：路径经过的栅格最大占用
        max_cong = float(self.state.congestion.max()) if self.state.congestion.size else 0.0
        congestion_pen = self.congestion_weight * max_cong
        # DRC：检查弯曲半径是否过小（三点圆弧半径估计）
        # 从平台约束读取 min_radius（SOI=5/SiN=50/InP=100/LNOI=30 μm）
        _, _, platform = self._current_ports()
        min_radius = get_platform_constraints(platform)["min_bend_radius_um"]
        drc_violations = _count_bend_radius_violations(wp.points, min_radius=min_radius)
        drc_pen = self.drc_penalty * drc_violations * 0.01
        reward = -(self.loss_weight * loss + self.length_weight * length + congestion_pen + drc_pen)
        # Reward clipping：限制单步 reward 下限，防止异常值摧毁价值函数
        reward = max(-self.reward_clip_max, reward)
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


def _count_bend_radius_violations(
    points: list[tuple[float, float]],
    min_radius: float = 5.0,
) -> int:
    """统计路径中弯曲半径过小的转弯数。

    用三点圆弧半径估计：对每个中间点 p1，由 (p0, p1, p2) 估算弯曲半径，
    若半径 < 工艺最小值则计为违规。

    来源: 三点圆弧半径公式 R = |v1||v2||v1-v2| / (2|v1×v2|)
           与 polaris.sim.constraint_checker._estimate_bend_radius 一致
    工艺最小值来源: polaris.router.waveguide_router.PLATFORM_CONSTRAINTS
           SOI=5.0μm / SiN=100.0μm / InP=250.0μm / LNOI=80.0μm
           来源: SiEPIC EBeam PDK 与各 foundry 工艺手册
           https://github.com/SiEPIC/SiEPIC_EBeam_PDK

    Args:
        points: 路径点序列。
        min_radius: 工艺最小弯曲半径 (μm)，默认 5.0（SOI）。

    Returns:
        弯曲半径违规数。
    """
    if len(points) < 3:
        return 0
    violations = 0
    for i in range(1, len(points) - 1):
        p0, p1, p2 = points[i - 1], points[i], points[i + 1]
        v1 = (p1[0] - p0[0], p1[1] - p0[1])
        v2 = (p2[0] - p1[0], p2[1] - p1[1])
        cross = abs(v1[0] * v2[1] - v1[1] * v2[0])
        if cross < 1e-9:
            continue  # 直线，无弯曲
        l1 = math.hypot(*v1)
        l2 = math.hypot(*v2)
        l3 = math.hypot(v2[0] - v1[0], v2[1] - v1[1])
        radius = l1 * l2 * l3 / (2.0 * cross)
        if 0 < radius < min_radius:
            violations += 1
    return violations


def _add_detour_obstacles(
    obstacles: list,
    start: tuple[float, float],
    end: tuple[float, float],
    detour_factor: float,
    grid_size: float,
) -> None:
    """根据 detour 因子在直线最短路径附近添加虚拟障碍，鼓励 A* 绕行。

    detour_factor 越大，虚拟障碍覆盖的直线段比例越高。

    Args:
        obstacles: 障碍列表（原地修改）。
        start: 起点。
        end: 终点。
        detour_factor: 绕行因子 [0, 1]。
        grid_size: 栅格尺寸。
    """
    # 在直线段中点附近添加一个小障碍，迫使 A* 绕行
    mid_x = (start[0] + end[0]) / 2.0
    mid_y = (start[1] + end[1]) / 2.0
    # 障碍尺寸随 detour_factor 增大
    size = grid_size * (1 + int(detour_factor * 5))
    obstacles.append((mid_x - size, mid_y - size, mid_x + size, mid_y + size))
