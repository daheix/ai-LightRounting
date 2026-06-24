"""一体化流水线: 网表 → GNN编码 → RL布局 → 布线 → 仿真回馈 → 输出。

串联所有模块为端到端自动布局布线系统，
支持仿真回馈闭环优化。

来源:
- Apollo arXiv 2025: 布线感知布局
  https://arxiv.org/html/2504.18813v1
- LiDAR ISPD'25: 弯曲波导布线
  https://dl.acm.org/doi/pdf/10.1145/3698364.3705355
- OptoSynthesizer arXiv 2026: 端到端 EPDA
  https://arxiv.org/pdf/2604.15493v1
"""

from __future__ import annotations

import json
import logging
import math
from dataclasses import dataclass, field
from pathlib import Path

from polaris.data.specs import CircuitSpec
from polaris.sim.constraint_checker import ConstraintConfig
from polaris.sim.sim_loop import SimLoop, SimLoopConfig

logger = logging.getLogger(__name__)


@dataclass
class PipelineConfig:
    """一体化流水线配置。

    Attributes:
        canvas_w: 画布宽度（μm）。
        canvas_h: 画布高度（μm）。
        grid_size: 栅格大小（μm）。
        max_sim_iterations: 仿真回馈最大迭代次数。
        router_type: 布线器类型（curvy/diagonal/hybrid/opto_electrical）。
        loss_target_db: 目标插入损耗（dB）。
        min_bend_radius_um: 最小弯曲半径（μm）。
        output_dir: 输出目录。
        placement_checkpoint: RL 布局 agent 检查点路径（None 则随机贪心）。
        use_real_simulator: 是否使用真实 S 参数仿真器（False 则查表）。
    """

    canvas_w: float = 1000.0
    canvas_h: float = 1000.0
    grid_size: float = 10.0
    max_sim_iterations: int = 3
    router_type: str = "curvy"
    loss_target_db: float = 5.0
    min_bend_radius_um: float = 5.0
    output_dir: str = "out"
    placement_checkpoint: str | None = None
    use_real_simulator: bool = False


@dataclass
class PipelineResult:
    """一体化流水线结果。

    Attributes:
        success: 是否成功。
        circuit_name: 电路名称。
        n_devices: 器件数。
        n_connections: 连接数。
        placements: 器件布局。
        paths: 布线路径。
        total_loss_db: 总插入损耗。
        n_crossings: 交叉数。
        drc_passed: DRC 是否通过。
        sim_iterations: 仿真迭代次数。
        report_path: 报告路径。
        gds_path: GDS 文件路径（第三波端到端流水线，空字符串表示未导出）。
    """

    success: bool = False
    circuit_name: str = ""
    n_devices: int = 0
    n_connections: int = 0
    placements: dict = field(default_factory=dict)
    paths: dict = field(default_factory=dict)
    total_loss_db: float = 0.0
    n_crossings: int = 0
    drc_passed: bool = False
    sim_iterations: int = 0
    report_path: str = ""
    gds_path: str = ""


# Direction 字母 → Direction 枚举（DeviceSpec.ports 元组第 4 项）
# 器件类型 → 类别映射、转换函数已迁移到 polaris.pipeline._converters
# （第三波端到端流水线，规则 7.2 拆分以控制文件行数 ≤500）


class _DefaultPlacer:
    """默认布局器。

    支持两种独立模式（非 fallback，按需选择）：
    1. RL 模式：加载训练好的 PPOAgentDiscrete，用 RL 策略布局
    2. 随机贪心模式：固定种子随机布局（独立接口，用于基线对比/无 checkpoint 场景）

    RL 模式来源:
    - Schulman et al., 2017, PPO https://arxiv.org/abs/1707.06347
    - Google Nature 2021: https://www.nature.com/articles/s41586-021-03544-w
    """

    def __init__(self, checkpoint_path: str | None = None, mode: str = "auto") -> None:
        """初始化布局器。

        Args:
            checkpoint_path: PPOAgent 检查点路径。None 时使用随机贪心。
            mode: 布局模式，"rl" 强制 RL，"random" 强制随机贪心，
                  "auto" 自动选择（有 checkpoint 用 RL，否则用随机）。
        """
        self.checkpoint_path = checkpoint_path
        self._mode = mode
        self._agent = None
        self._obs_dim = 0
        self._n_actions = 0
        if mode == "random":
            return  # 强制随机模式，不加载 agent
        if checkpoint_path:
            self._try_load_agent(checkpoint_path)

    def _try_load_agent(self, path: str) -> None:
        """加载 RL agent。

        修复（违规 1）：原实现在检查点不存在或加载异常时静默切换为随机贪心
        模式（fall-back）。现改为加载失败时 raise RuntimeError，由调用方决定
        是否显式选择 random 模式（mode="random"）。若调用方想用随机模式，
        应显式传入 mode="random"，而不是在加载失败时静默降级。
        """
        from pathlib import Path

        from polaris.trainer.ppo_buffers import AgentSpec, PPOConfig
        from polaris.trainer.ppo_torch import PPOAgentDiscrete

        ckpt = Path(path)
        if not ckpt.exists():
            raise RuntimeError(
                f"RL agent 检查点不存在: {path}。"
                f"若需使用随机贪心布局，请显式传入 mode='random'。"
            )

        # 动态推断 obs_dim 和 n_actions
        from polaris.engine.floorplan_env import FloorplanEnv, FloorplanEnvConfig
        from polaris.engine.netlist import load_netlist

        net, devices, _ = load_netlist("data/benchmarks/mzi.json")
        env = FloorplanEnv(
            net,
            devices,
            config=FloorplanEnvConfig(canvas_w=200.0, canvas_h=200.0, grid_size=20.0),
        )
        obs, _ = env.reset()
        self._obs_dim = len(obs) if hasattr(obs, "__len__") else 1
        self._n_actions = 400  # MultiDiscrete([10,10,4]) = 400

        spec = AgentSpec(obs_dim=self._obs_dim, n_actions=self._n_actions, hidden_dim=128)
        cfg = PPOConfig(lr=3e-4, n_epochs=4, batch_size=64)
        try:
            self._agent = PPOAgentDiscrete.load(str(ckpt), cfg, spec)
        except Exception as e:
            raise RuntimeError(
                f"RL agent 加载失败: {e}。"
                f"若需使用随机贪心布局，请显式传入 mode='random'。"
            ) from e
        logger.info("RL agent 加载成功: %s (obs_dim=%d)", path, self._obs_dim)

    def place(self, circuit: CircuitSpec, feedback=None) -> dict:
        """放置器件。

        Args:
            circuit: 电路规格。
            feedback: 仿真反馈（可选，用于迭代优化）。

        Returns:
            布局结果 dict {name: {x, y, w, h}}。
        """
        if self._agent is not None:
            return self._place_with_rl(circuit)
        return self._place_random(circuit)

    def _place_with_rl(self, circuit: CircuitSpec) -> dict:
        """用 RL 策略布局。"""
        from polaris.engine.floorplan_env import FloorplanEnv, FloorplanEnvConfig
        from polaris.engine.netlist import Connection, Netlist

        # 构造 Netlist（从 CircuitSpec）
        connections = [
            Connection(src_instance=d1, src_port=p1, dst_instance=d2, dst_port=p2)
            for d1, p1, d2, p2 in circuit.connections
        ]
        net = Netlist(devices=circuit.devices, connections=connections)
        env = FloorplanEnv(
            net,
            circuit.devices,
            config=FloorplanEnvConfig(
                canvas_w=circuit.canvas_w,
                canvas_h=circuit.canvas_h,
                grid_size=20.0,
            ),
        )
        obs, _ = env.reset()
        placements = {}
        done = False
        while not done:
            action, _, _ = self._agent.get_action(obs)
            obs, reward, done, truncated, info = env.step(action)
            if truncated:
                done = True
        # 从 env.state 提取布局结果
        for inst_id, pl in env.state.placements.items():
            placements[inst_id] = {
                "x": pl.x,
                "y": pl.y,
                "w": pl.device.width_um,
                "h": pl.device.height_um,
            }
        return placements

    def _place_random(self, circuit: CircuitSpec) -> dict:
        """随机贪心布局（独立模式，用于基线对比/无 checkpoint 场景）。

        修复: 原实现用固定 margin=50，小画布（200×200）上大器件（30×20）必然重叠。
        现改为网格布局：将画布划分为 N×N 网格，每个器件占一格，保证不重叠。
        """
        import random

        rng = random.Random(42)
        placements = {}
        n_dev = len(circuit.devices)
        if n_dev == 0:
            return placements

        # 网格布局：计算行列数（尽量方形）
        n_cols = int(math.ceil(math.sqrt(n_dev)))
        n_rows = int(math.ceil(n_dev / n_cols))

        # 每格尺寸（含间距）
        cell_w = circuit.canvas_w / n_cols
        cell_h = circuit.canvas_h / n_rows
        min_spacing = 5.0  # 器件间最小间距 μm

        for idx, dev in enumerate(circuit.devices):
            row = idx // n_cols
            col = idx % n_cols
            # 器件在格内随机偏移（保留 spacing）
            avail_w = max(cell_w - dev.width_um - min_spacing, 0)
            avail_h = max(cell_h - dev.height_um - min_spacing, 0)
            offset_x = rng.uniform(0, avail_w) if avail_w > 0 else 0.0
            offset_y = rng.uniform(0, avail_h) if avail_h > 0 else 0.0
            x = col * cell_w + min_spacing / 2 + offset_x
            y = row * cell_h + min_spacing / 2 + offset_y
            placements[dev.name] = {"x": x, "y": y, "w": dev.width_um, "h": dev.height_um}
        return placements


class _DefaultRouter:
    """默认布线器（A*网格布线 + 动态 grid_size）。

    grid_size 自动选择：根据画布尺寸与器件数计算最优分辨率，
    支持大规模电路（500-1000 器件，5000×5000 μm 画布）。
    来源: LiDAR ISPD 2025 + DREAMPlace DAC 2019 + Ada-Routing ICCAD 2025
    """

    def route(self, circuit: CircuitSpec, placements: dict) -> dict:
        """布线连接。

        修复（违规 3）：原实现在 ``grid_path`` 为空时静默跳过该连接（fall-back）。
        现改为收集所有未布线连接，若存在未布线连接则记录 warning 日志明确
        列出失败连接（非静默跳过），让调用方知晓布线不完整。全部连接布线
        成功时正常返回。
        """
        from polaris.router.waveguide_router import (
            GridRouter,
            RouterConstraints,
            auto_grid_size,
        )

        grid_size = auto_grid_size(
            canvas_w=circuit.canvas_w,
            canvas_h=circuit.canvas_h,
            platform="SOI",
            min_bend_radius_um=5.0,
        )
        grid_w = int(circuit.canvas_w / grid_size)
        grid_h = int(circuit.canvas_h / grid_size)
        cons = RouterConstraints(min_bend_radius_um=5.0, min_spacing_um=1.0)
        router = GridRouter(grid_w, grid_h, grid_size, cons)
        paths = {}
        unrouted: list[str] = []
        for d1, p1, d2, p2 in circuit.connections:
            if d1 in placements and d2 in placements:
                pos1 = placements[d1]
                pos2 = placements[d2]
                sg = (int(pos1["x"] / grid_size), int(pos1["y"] / grid_size))
                eg = (int(pos2["x"] / grid_size), int(pos2["y"] / grid_size))
                grid_path = router.route(sg, eg)
                if grid_path:
                    pts = [(g[0] * grid_size, g[1] * grid_size) for g in grid_path]
                    paths[f"{d1}_{p1}_{d2}_{p2}"] = pts
                else:
                    unrouted.append(f"{d1}_{p1}_{d2}_{p2}")
            else:
                unrouted.append(f"{d1}_{p1}_{d2}_{p2}")
        if unrouted:
            logger.warning(
                "A* 网格布线存在 %d 条未布线连接: %s",
                len(unrouted),
                unrouted,
            )
        return paths


class _CurvyRouter:
    """弯曲感知布线器（LiDAR ISPD'25 curvy-aware routing）。

    在 A* 网格路径基础上，用欧拉/圆弧曲线替换直角弯，输出平滑弯曲波导路径。
    相比 _DefaultRouter 的折线输出，弯曲波导损耗更低、更符合光子工艺实际。

    来源:
    - LiDAR ISPD'25: https://dl.acm.org/doi/10.1145/3698364.3705355
    - LiDAR 2.0 TCAD 2025: https://arxiv.org/html/2505.17239v2
    """

    def __init__(self, curve_type: str = "euler") -> None:
        """初始化弯曲布线器。

        Args:
            curve_type: 弯曲类型（"euler"/"arc"/"bezier"）。
        """
        self.curve_type = curve_type

    def route(self, circuit: CircuitSpec, placements: dict) -> dict:
        """顺序网格布线 + 已布线路径作为障碍物避免交叉。

        修复: 原实现每条连接独立 A* 寻路 + 曲线替换，不考虑已布线路径，
        导致大量交叉；曲线替换还会向外偏移产生新的交叉和弯曲半径违规。
        现改为顺序网格布线策略：每条连接布线后，将其路径转换为障碍物（窄带），
        阻止后续连接穿过，从而避免交叉。网格折线路径本身满足约束检查器
        （下采样 + 宏观转弯点检测跳过短路径直角弯）。

        来源: LiDAR ISPD'25 §3.3 Sequential Routing
          https://dl.acm.org/doi/pdf/10.1145/3698364.3705355

        修复（违规 2）：原实现在布线失败时静默跳过（fall-back）。现改为
        收集所有未布线连接，若存在未布线连接则记录 warning 日志明确列出
        失败连接（非静默跳过），让调用方知晓布线不完整。全部连接布线
        成功时正常返回。
        """
        from polaris.router.waveguide_router import (
            GridRouter,
            RouterConstraints,
            get_platform_constraints,
        )

        cons = get_platform_constraints("SOI")
        # grid_size = min_bend_radius_um，确保网格直角弯半径 >= min_bend_radius
        # （直角弯半径 = grid_size，需 >= min_bend_radius_um 才满足约束）
        grid_size = cons["min_bend_radius_um"]
        grid_w = int(circuit.canvas_w / grid_size)
        grid_h = int(circuit.canvas_h / grid_size)
        # 障碍物列表：已布线路径的窄带障碍物（半宽 = grid_size*0.5）
        obstacles: list[tuple[float, float, float, float]] = []
        paths = {}
        unrouted: list[str] = []
        for d1, p1, d2, p2 in circuit.connections:
            if d1 in placements and d2 in placements:
                pos1 = placements[d1]
                pos2 = placements[d2]
                start = (pos1["x"] + pos1["w"] / 2, pos1["y"] + pos1["h"] / 2)
                end = (pos2["x"] + pos2["w"] / 2, pos2["y"] + pos2["h"] / 2)
                # 每条连接创建带累积障碍物的 GridRouter
                router = GridRouter(
                    grid_w, grid_h, grid_size,
                    RouterConstraints(
                        min_bend_radius_um=cons["min_bend_radius_um"],
                        min_spacing_um=cons["min_spacing_um"],
                    ),
                )
                for box in obstacles:
                    router.add_obstacle_box(*box)
                sg = (int(start[0] / grid_size), int(start[1] / grid_size))
                eg = (int(end[0] / grid_size), int(end[1] / grid_size))
                grid_path = router.route(sg, eg)
                if grid_path:
                    pts = [(g[0] * grid_size, g[1] * grid_size) for g in grid_path]
                    # 起终点对齐到精确坐标
                    if pts:
                        pts[0] = start
                        pts[-1] = end
                    paths[f"{d1}_{p1}_{d2}_{p2}"] = pts
                    # 将已布线路径下采样后转换为障碍物
                    # 半宽 = grid_size*0.6，确保覆盖网格间隙阻止交叉
                    sampled_pts = _downsample_path_for_obstacle(pts, grid_size)
                    obstacles.extend(
                        _path_to_obstacles(sampled_pts, grid_size * 0.6)
                    )
                else:
                    unrouted.append(f"{d1}_{p1}_{d2}_{p2}")
                    logger.warning(
                        "网格布线失败 %s_%s_%s_%s: 无法找到可行路径",
                        d1, p1, d2, p2,
                    )
            else:
                unrouted.append(f"{d1}_{p1}_{d2}_{p2}")
        if unrouted:
            logger.warning(
                "顺序网格布线存在 %d 条未布线连接: %s",
                len(unrouted),
                unrouted,
            )
        return paths


class _DefaultSimulator:
    """默认仿真器。

    支持两种独立模式（非 fallback，按需选择）：
    1. 真实 S 参数仿真：调用 polaris.sim.simulator.CircuitSimulator
    2. 查表估算：基于器件类型损耗查表的快速估算（独立接口，用于快速可行性筛查）

    仿真来源:
    - simphony: https://simphonyphotonics.readthedocs.io/
    - sax: https://flaport.github.io/sax/
    - 查表损耗值来源: SiEPIC EBeam PDK (https://github.com/SiEPIC/SiEPIC_EBeam_PDK)
    """

    # 器件类型 → 单位损耗 (dB)
    # 来源: SiEPIC EBeam PDK (https://github.com/SiEPIC/SiEPIC_EBeam_PDK)
    # 波导类器件按 dB/cm × length(μm)/1e4 计算，其余为固定插损。
    _LOSS_TABLE: dict[str, float] = {
        "waveguide": 3.0,  # SOI strip waveguide 3.0 dB/cm，需乘以 length/1e4
        "straight": 3.0,  # 直波导（gdsfactory/LiDAR 命名），同 waveguide
        "strip_waveguide": 3.0,  # PoLaRIS PDK 标准波导名，同 waveguide
        "waveguide_bump$1": 3.0,  # SiEPIC 波导弯曲，同 waveguide
        "mzi": 1.0,  # MZI 插损 1.0 dB
        "ring": 0.3,  # 环谐振器插损 0.3 dB
        "ring_resonator": 0.3,  # 环谐振器（SiEPIC 命名），同 ring
        "grating_coupler": 1.9,  # GC 耦合损耗 1.9 dB
        "grating_coupler_1d": 1.9,  # SiEPIC ebeam_gc_te1550，同 grating_coupler
        "mmi": 0.4,  # MMI 1x2/2x2 插损 0.4 dB
        "mmi_1x2": 0.4,  # MMI 1x2（gdsfactory 命名），同 mmi
        "mmi_2x2": 0.4,  # MMI 2x2（gdsfactory 命名），同 mmi
        "y_branch": 0.3,  # Y 分支插损 0.3 dB
        "directional_coupler": 0.2,  # DC 插损 0.2 dB
        "ebeam_dc_halfring_straight$1": 0.2,  # SiEPIC 半环 DC，同 directional_coupler
        "DirectionalCoupler_SeriesRings$1": 0.2,  # SiEPIC 串联环 DC，同 directional_coupler
        "crossing": 0.2,  # 波导交叉插损 0.2 dB
        "ebeam_crossing4": 0.2,  # SiEPIC ebeam_crossing4，同 crossing
        "terminator": 0.1,  # 终端吸收器插损 0.1 dB
        "phase_shifter": 0.5,  # 热光移相器插损 0.5 dB
        "thermo_optic_phase_shifter": 0.5,  # PoLaRIS PDK 标准移相器名，同 phase_shifter
        "heater": 0.5,  # 加热器（同 phase_shifter）
        "ge_photodetector": 0.5,  # Ge 光电探测器耦合损耗 0.5 dB
        "avalanche_photodetector": 0.5,  # 雪崩光电探测器耦合损耗 0.5 dB
        "mzm_modulator": 4.0,  # MZM 调制器插损 4.0 dB（含分束+合束）
        "mrm_modulator": 0.5,  # MRM 调制器环耦合损耗 0.5 dB
        "thermo_optic_tuned_ring_modulator": 0.5,  # 热光环调制器，同 mrm_modulator
        "thermo_optic_switch": 1.0,  # 热光开关插损 1.0 dB
    }

    # 波导类器件类型集合（按长度计算损耗，需 length/wg_length 参数）
    _WAVEGUIDE_TYPES: frozenset[str] = frozenset(
        {"waveguide", "straight", "strip_waveguide", "waveguide_bump$1"}
    )

    def __init__(self, mode: str = "table") -> None:
        """初始化仿真器。

        Args:
            mode: 仿真模式，"real" 使用真实 S 参数仿真器，
                  "table" 使用查表估算（默认，快速）。
        """
        self._mode = mode
        self._sim = None
        if mode == "real":
            self._init_real_simulator()

    def _init_real_simulator(self) -> None:
        """初始化真实 S 参数仿真器。"""
        try:
            from polaris.sim.simulator import CircuitSimulator

            self._sim = CircuitSimulator()
            logger.info("真实 S 参数仿真器初始化成功")
        except Exception as e:
            raise RuntimeError(f"真实仿真器初始化失败: {e}") from e

    def simulate(self, circuit: CircuitSpec, placements: dict, paths: dict) -> dict:
        """仿真 S 参数（按初始化模式选择）。"""
        if self._mode == "real" and self._sim is not None:
            return self._simulate_real(circuit, placements, paths)
        return self._simulate_table(circuit, placements, paths)

    def _simulate_real(self, circuit: CircuitSpec, placements: dict, paths: dict) -> dict:
        """真实 S 参数级联仿真。"""
        result = self._sim.simulate(circuit)
        return {
            "total_loss_db": float(result.get("total_loss_db", 0.0)),
            "n_crossings": int(result.get("n_crossings", 0)),
        }

    def _simulate_table(self, circuit: CircuitSpec, placements: dict, paths: dict) -> dict:
        """查表估算损耗（独立接口，用于快速可行性筛查）。

        修复（违规 6/7/8）：
        - 违规 6：未知器件类型不再默认返回 0.0，改为 raise KeyError。
        - 违规 7：波导长度参数缺失不再用宽度代替，改为 raise ValueError。
        - 违规 8：n_crossings 不再固定返回 0，改为基于 paths 几何实际
          计算交叉数（线段相交检测）。

        来源: SiEPIC EBeam PDK (https://github.com/SiEPIC/SiEPIC_EBeam_PDK)
        """
        total_loss = 0.0
        for dev in circuit.devices:
            if dev.device_type not in self._LOSS_TABLE:
                raise KeyError(
                    f"器件类型 '{dev.device_type}' 不在损耗表中，"
                    f"已知类型: {sorted(self._LOSS_TABLE.keys())}。"
                    f"请在 _LOSS_TABLE 中补充该器件类型的损耗值。"
                )
            loss = self._LOSS_TABLE[dev.device_type]
            if dev.device_type in self._WAVEGUIDE_TYPES:
                # 波导类器件按长度计算损耗，支持 length/wg_length/length_um 参数名
                # length_um 为 SiEPIC/gdsfactory 标准命名
                length = dev.params.get(
                    "length", dev.params.get("wg_length", dev.params.get("length_um"))
                )
                if length is None:
                    raise ValueError(
                        f"波导器件 '{dev.name}'（类型 '{dev.device_type}'）"
                        f"缺少 length 参数，无法计算波导损耗。"
                        f"请在器件 params 中提供 length/length_um（μm）。"
                    )
                total_loss += loss * length / 1e4
            else:
                total_loss += loss
        n_crossings = _count_path_crossings(paths)
        return {"total_loss_db": total_loss, "n_crossings": n_crossings}


def _count_path_crossings(paths: dict) -> int:
    """基于路径几何计算交叉数（违规 8 修复）。

    遍历所有不同连接的线段对，检测是否相交（不含共享端点，不含同一路径内的相邻线段）。
    使用方向叉积（CCW）判断线段相交，复杂度 O(n^2 * m^2)，
    其中 n 为连接数，m 为单条路径线段数。对典型 PIC 规模（<100 连接）可接受。

    来源: 计算几何经典线段相交算法（Bentley-Ottmann 简化版）。
    """
    # 按路径分组存储线段，避免同一路径内的线段自相交误报
    path_segs: list[tuple[str, tuple[float, float], tuple[float, float]]] = []
    for net_id, pts in paths.items():
        if len(pts) < 2:
            continue
        for i in range(len(pts) - 1):
            p1 = (float(pts[i][0]), float(pts[i][1]))
            p2 = (float(pts[i + 1][0]), float(pts[i + 1][1]))
            path_segs.append((net_id, p1, p2))

    def _cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    def _segments_intersect(p1, p2, p3, p4):
        """检测线段 p1p2 与 p3p4 是否真相交（不含共享端点）。"""
        d1 = _cross(p3, p4, p1)
        d2 = _cross(p3, p4, p2)
        d3 = _cross(p1, p2, p3)
        d4 = _cross(p1, p2, p4)
        if ((d1 > 0 and d2 < 0) or (d1 < 0 and d2 > 0)) and (
            (d3 > 0 and d4 < 0) or (d3 < 0 and d4 > 0)
        ):
            return True
        return False

    crossings = 0
    n = len(path_segs)
    for i in range(n):
        for j in range(i + 1, n):
            # 跳过同一路径内的线段对（避免自相交误报）
            if path_segs[i][0] == path_segs[j][0]:
                continue
            _, p1, p2 = path_segs[i]
            _, p3, p4 = path_segs[j]
            if _segments_intersect(p1, p2, p3, p4):
                crossings += 1
    return crossings


def _path_to_obstacles(
    pts: list[tuple[float, float]],
    half_width: float,
) -> list[tuple[float, float, float, float]]:
    """将布线路径转换为窄带障碍物列表。

    沿路径每段生成一个矩形障碍物（宽度 = 2 * half_width），
    用于阻止后续连接与该路径交叉（LiDAR ISPD'25 顺序布线障碍物策略）。

    来源: LiDAR ISPD'25 §3.3 Sequential Routing
      https://dl.acm.org/doi/pdf/10.1145/3698364.3705355

    Args:
        pts: 路径点列表 [(x, y), ...]。
        half_width: 障碍物半宽（μm），通常 = min_spacing。

    Returns:
        障碍物列表 [(xmin, ymin, xmax, ymax), ...]。
    """
    if len(pts) < 2:
        return []
    obstacles: list[tuple[float, float, float, float]] = []
    for i in range(len(pts) - 1):
        x1, y1 = float(pts[i][0]), float(pts[i][1])
        x2, y2 = float(pts[i + 1][0]), float(pts[i + 1][1])
        xmin = min(x1, x2) - half_width
        ymin = min(y1, y2) - half_width
        xmax = max(x1, x2) + half_width
        ymax = max(y1, y2) + half_width
        obstacles.append((xmin, ymin, xmax, ymax))
    return obstacles


def _downsample_path_for_obstacle(
    pts: list[tuple[float, float]],
    min_segment: float,
) -> list[tuple[float, float]]:
    """下采样路径用于生成障碍物，减少障碍物数量避免阻塞通道。

    合并距离过近的相邻点，保留路径宏观结构。

    Args:
        pts: 原始路径点列表。
        min_segment: 最小段长（μm），短于此值的相邻点合并。

    Returns:
        下采样后的路径点列表。
    """
    if len(pts) < 3:
        return list(pts)
    import math as _math
    result: list[tuple[float, float]] = [pts[0]]
    for i in range(1, len(pts)):
        dx = pts[i][0] - result[-1][0]
        dy = pts[i][1] - result[-1][1]
        if _math.hypot(dx, dy) >= min_segment:
            result.append(pts[i])
    if result[-1] != pts[-1]:
        result.append(pts[-1])
    return result


class IntegratedPipeline:
    """一体化流水线。

    端到端: 网表 → GNN编码 → RL布局 → 布线 → 仿真回馈 → 输出

    来源:
    - Apollo arXiv 2025: https://arxiv.org/html/2504.18813v1
    """

    def __init__(self, config: PipelineConfig | None = None) -> None:
        self.config = config or PipelineConfig()
        self.placer = _DefaultPlacer(checkpoint_path=self.config.placement_checkpoint)
        self.router = self._make_router(self.config.router_type)
        sim_mode = "real" if self.config.use_real_simulator else "table"
        self.simulator = _DefaultSimulator(mode=sim_mode)

    @staticmethod
    def _make_router(router_type: str):
        """根据 router_type 创建布线器。

        Args:
            router_type: 布线器类型（curvy/diagonal/hybrid/default）。

        Returns:
            布线器实例（实现 route(circuit, placements) -> dict 接口）。
        """
        if router_type == "curvy":
            return _CurvyRouter(curve_type="euler")
        return _DefaultRouter()

    def run(self, circuit: CircuitSpec | None = None) -> PipelineResult:
        """执行一体化流水线。

        Args:
            circuit: 电路规格。None 时使用内置默认 MZI 电路（方便快速演示与无参调用）。

        Returns:
            PipelineResult。
        """
        if circuit is None:
            circuit = _default_demo_circuit()
        cfg = self.config
        logger.info(
            "一体化流水线启动: %s (%d 器件, %d 连接)",
            circuit.name,
            len(circuit.devices),
            len(circuit.connections),
        )

        sim_result = self._run_sim_loop(circuit, cfg)
        report_path = self._write_report(circuit, cfg, sim_result)
        gds_path, drc_passed = self._export_layout(circuit, sim_result, cfg)

        return PipelineResult(
            success=sim_result.success,
            circuit_name=circuit.name,
            n_devices=len(circuit.devices),
            n_connections=len(circuit.connections),
            placements=sim_result.placements,
            paths=sim_result.paths,
            total_loss_db=sim_result.total_loss_db,
            n_crossings=sim_result.n_crossings,
            drc_passed=drc_passed,
            sim_iterations=sim_result.iterations,
            report_path=report_path,
            gds_path=gds_path,
        )

    def _run_sim_loop(self, circuit: CircuitSpec, cfg: PipelineConfig):
        """执行仿真回馈闭环。"""
        sim_cfg = SimLoopConfig(
            max_iterations=cfg.max_sim_iterations,
            constraint_config=ConstraintConfig(
                min_bend_radius_um=cfg.min_bend_radius_um,
                max_insertion_loss_db=cfg.loss_target_db,
            ),
        )
        loop = SimLoop(self.placer, self.router, self.simulator, sim_cfg)
        return loop.run(circuit)

    @staticmethod
    def _write_report(
        circuit: CircuitSpec,
        cfg: PipelineConfig,
        result,
    ) -> str:
        """输出报告文件。"""
        out = Path(cfg.output_dir)
        out.mkdir(parents=True, exist_ok=True)
        report_path = str(out / f"{circuit.name}_report.json")
        report = {
            "circuit": circuit.name,
            "n_devices": len(circuit.devices),
            "success": result.success,
            "total_loss_db": result.total_loss_db,
            "n_crossings": result.n_crossings,
            "iterations": result.iterations,
            "violations": len(result.violations),
        }
        Path(report_path).write_text(json.dumps(report, indent=2), encoding="utf-8")
        return report_path

    def _export_layout(self, circuit: CircuitSpec, result, cfg: PipelineConfig) -> tuple[str, bool]:
        """导出 GDS + DRC（第三波端到端流水线）。

        将 SimLoop 的 dict 布局/路径转换为 Placement/WaveguidePath 对象，
        调用 export_gds 导出 SiEPIC 格式 GDS，并运行 DRC 检查。

        Args:
            circuit: 电路规格。
            result: SimLoop 结果。
            cfg: 流水线配置。

        Returns:
            (GDS 文件路径, DRC 是否通过)。GDS 导出失败时路径为空。
        """
        from polaris.eval.layout_render import export_gds, run_drc
        from polaris.pipeline._converters import convert_to_paths, convert_to_placements

        placements = convert_to_placements(circuit, result.placements)
        paths = convert_to_paths(result.paths)
        out = Path(cfg.output_dir)
        out.mkdir(parents=True, exist_ok=True)
        gds_path = str(out / f"{circuit.name}.gds")
        export_gds(placements, paths, gds_path)
        drc_report = run_drc(placements, paths)
        logger.info("GDS 导出: %s (DRC: %s)", gds_path, "通过" if drc_report.passed else "失败")
        return gds_path, drc_report.passed


__all__ = [
    "IntegratedPipeline",
    "PipelineConfig",
    "PipelineResult",
]


def _default_demo_circuit() -> CircuitSpec:
    """内置默认演示电路（MZI 风格，3 器件 2 连接）。

    用于 ``IntegratedPipeline.run()`` 无参调用时提供快速演示，
    避免第三方用户必须构造 CircuitSpec 才能体验流水线。
    """
    from polaris.data.specs import DeviceSpec

    return CircuitSpec(
        name="demo_mzi",
        devices=[
            DeviceSpec(name="gc1", device_type="grating_coupler", width_um=10.0, height_um=10.0),
            DeviceSpec(name="mmi1", device_type="mmi_1x2", width_um=20.0, height_um=10.0),
            DeviceSpec(name="gc2", device_type="grating_coupler", width_um=10.0, height_um=10.0),
        ],
        connections=[
            ("gc1", "o1", "mmi1", "o1"),
            ("mmi1", "o2", "gc2", "o1"),
        ],
        canvas_w=200.0,
        canvas_h=200.0,
    )
