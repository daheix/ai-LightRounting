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
from typing import TYPE_CHECKING

from polaris.data.specs import CircuitSpec
from polaris.pipeline.curvy_router import _CurvyRouter
from polaris.pipeline.default_simulator import _DefaultSimulator
from polaris.sim.constraint_checker import ConstraintConfig
from polaris.sim.sim_loop import SimLoop, SimLoopConfig

if TYPE_CHECKING:
    from polaris.flow.recipe import Recipe
    from polaris.flow.workspace import Workspace

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

        修复 P0-1: 原网格布局在大器件小画布场景产生重叠（器件尺寸 > 格子尺寸时
        溢出到相邻格子）。现增加: 1) 重叠检测 2) 合法化（推开重叠器件到最近空闲位置）
        3) 画布空间不足时扩大画布（×2.0）重新布局, 最多 5 次。

        来源: DREAMPlace 合法化（TCAD 2020 §III.C）
          https://arxiv.org/abs/1904.03522
        """
        import random

        rng = random.Random(42)
        n_dev = len(circuit.devices)
        if n_dev == 0:
            return {}

        canvas_w = circuit.canvas_w
        canvas_h = circuit.canvas_h
        # 最多扩大 5 次 (×2.0), 每次面积 ×4, 5 次后面积 ×1024
        # 足以容纳任何合理电路 (50 器件 × 30×20μm = 30000μm², 5 次后画布 ×1024 倍)
        for attempt in range(5):
            placements = _grid_place(circuit.devices, canvas_w, canvas_h, rng)
            # 合法化迭代: 多次扫描消除级联重叠 (单次无法解决 A 推 B 又撞 C 的情况)
            for _ in range(3):
                placements = _legalize_overlaps(placements, canvas_w, canvas_h)
                if not _has_overlap(placements):
                    break
            if not _has_overlap(placements):
                return placements
            # 仍有重叠 → 扩大画布重试 (×2.0, 比 ×1.5 更快达到足够空间)
            canvas_w *= 2.0
            canvas_h *= 2.0
            logger.warning(
                "P0-1: 画布空间不足，扩大至 %.1f×%.1f μm 重试 (attempt %d/5)",
                canvas_w, canvas_h, attempt + 1,
            )
        logger.warning(
            "P0-1: 经过 5 次画布扩大仍有重叠，返回最后布局（%d 器件）", n_dev,
        )
        return placements


# P0-1 布局合法化辅助函数
# 来源: DREAMPlace 合法化（TCAD 2020 §III.C）https://arxiv.org/abs/1904.03522
_MIN_PLACE_SPACING_UM = 5.0  # 器件间最小间距 μm


def _grid_place(devices, canvas_w: float, canvas_h: float, rng) -> dict:
    """网格布局：将画布划分为 N×N 网格，每个器件占一格。

    修复: 当格子尺寸 < 器件尺寸时, 器件居中放置 (不随机偏移, 避免溢出重叠)。
    """
    n_dev = len(devices)
    n_cols = int(math.ceil(math.sqrt(n_dev)))
    n_rows = int(math.ceil(n_dev / n_cols))
    cell_w = canvas_w / n_cols
    cell_h = canvas_h / n_rows
    placements = {}
    for idx, dev in enumerate(devices):
        row = idx // n_cols
        col = idx % n_cols
        # 格子足够大: 随机偏移; 格子过小: 居中放置 (避免溢出)
        avail_w = max(cell_w - dev.width_um - _MIN_PLACE_SPACING_UM, 0)
        avail_h = max(cell_h - dev.height_um - _MIN_PLACE_SPACING_UM, 0)
        if avail_w > 0 and avail_h > 0:
            offset_x = rng.uniform(0, avail_w)
            offset_y = rng.uniform(0, avail_h)
        else:
            # 格子过小: 器件居中放置 (可能仍有重叠, 由 _legalize_overlaps 处理)
            offset_x = max((cell_w - dev.width_um) / 2, 0)
            offset_y = max((cell_h - dev.height_um) / 2, 0)
        x = col * cell_w + _MIN_PLACE_SPACING_UM / 2 + offset_x
        y = row * cell_h + _MIN_PLACE_SPACING_UM / 2 + offset_y
        placements[dev.name] = {"x": x, "y": y, "w": dev.width_um, "h": dev.height_um}
    return placements


def _rects_overlap(p1: dict, p2: dict) -> bool:
    """检查两矩形是否重叠（严格重叠，共享边界不算）。"""
    return not (
        p1["x"] + p1["w"] <= p2["x"]
        or p2["x"] + p2["w"] <= p1["x"]
        or p1["y"] + p1["h"] <= p2["y"]
        or p2["y"] + p2["h"] <= p1["y"]
    )


def _has_overlap(placements: dict) -> bool:
    """检测布局中是否存在任意重叠。"""
    items = list(placements.values())
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            if _rects_overlap(items[i], items[j]):
                return True
    return False


def _legalize_overlaps(placements: dict, canvas_w: float, canvas_h: float) -> dict:
    """合法化布局：消除重叠（推开重叠器件到最近空闲位置）。

    遍历所有器件对，对重叠器件沿 x/y 方向搜索最近空闲位置。
    来源: DREAMPlace 合法化（TCAD 2020 §III.C）
      https://arxiv.org/abs/1904.03522
    """
    names = list(placements.keys())
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            p1 = placements[names[i]]
            p2 = placements[names[j]]
            if _rects_overlap(p1, p2):
                # 将 p2 推开到最近空闲位置
                new_p2 = _find_nearest_free(
                    p2, placements, canvas_w, canvas_h, exclude=names[j]
                )
                placements[names[j]] = new_p2
    return placements


def _find_nearest_free(
    p: dict,
    placements: dict,
    canvas_w: float,
    canvas_h: float,
    exclude: str,
) -> dict:
    """沿 +x/+y/-x/-y 方向搜索最近空闲位置。

    Args:
        p: 待移动器件的布局 {x, y, w, h}。
        placements: 所有器件布局（用于碰撞检测）。
        canvas_w: 画布宽度。
        canvas_h: 画布高度。
        exclude: 排除的器件名（即待移动器件自身）。

    Returns:
        移动后的布局 dict；找不到空闲位置时返回原位置（由上层扩大画布重试）。
    """
    step = _MIN_PLACE_SPACING_UM
    # 4 个搜索方向: +x, +y, -x, -y
    for dx, dy in ((1, 0), (0, 1), (-1, 0), (0, -1)):
        new_p = dict(p)
        for _ in range(200):  # 最多搜索 200 步
            new_p["x"] += dx * step
            new_p["y"] += dy * step
            # 边界检查
            if new_p["x"] < 0 or new_p["y"] < 0:
                break
            if new_p["x"] + new_p["w"] > canvas_w or new_p["y"] + new_p["h"] > canvas_h:
                break
            # 检查是否与其他器件重叠
            clash = False
            for name, other in placements.items():
                if name == exclude:
                    continue
                if _rects_overlap(new_p, other):
                    clash = True
                    break
            if not clash:
                return new_p
    return p  # 找不到空闲位置，返回原位置（由上层扩大画布重试）


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

    def run_as_stages(
        self,
        recipe: Recipe,
        workspace: Workspace,
    ) -> list[StageResult]:
        """阶段化执行流水线（供 JobScheduler 调用）。

        按 Recipe 中启用的阶段列表顺序执行，每阶段输出持久化到 Workspace。
        保留同步 run() 方法向后兼容。

        Args:
            recipe: 作业配方。
            workspace: 工作空间。

        Returns:
            阶段结果列表。

        Raises:
            Exception: 阶段执行失败时向上抛出（禁止 fall-back）。
        """
        from datetime import datetime

        from polaris.flow.executors import STAGE_EXECUTORS
        from polaris.flow.stage import StageResult, StageStatus, get_stage

        results: list[StageResult] = []
        prev_outputs: dict = {}

        for stage_id in recipe.enabled_stages:
            stage = get_stage(stage_id)
            result = StageResult(
                stage_id=stage_id,
                name=stage.name,
                status=StageStatus.RUNNING,
                start_time=datetime.now(),
            )
            try:
                execute_fn = STAGE_EXECUTORS.get(stage_id)
                if execute_fn is None:
                    # 无执行函数视为跳过（非 fall-back，明确告警）
                    result.status = StageStatus.SKIPPED
                    result.error = f"阶段 {stage_id} 无执行函数"
                else:
                    output_data = execute_fn(recipe, workspace, prev_outputs)
                    result.output.data = output_data
                    result.status = StageStatus.COMPLETED
                    workspace.write_stage_output(stage.slug, output_data)
                    prev_outputs.update(output_data)
            except Exception as e:
                # 阶段失败：记录状态后向上抛出，禁止 fall-back
                result.status = StageStatus.FAILED
                result.error = str(e)
                result.end_time = datetime.now()
                results.append(result)
                raise
            result.end_time = datetime.now()
            results.append(result)

        return results

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
