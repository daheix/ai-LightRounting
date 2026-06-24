"""仿真回馈闭环 (SimLoop)。

将布局、布线、S参数仿真、约束检查、反馈调整串联为闭环，
自动迭代优化直到满足所有约束或达到最大迭代次数。

来源:
- Apollo arXiv 2025: 布线感知布局反馈
  https://arxiv.org/html/2504.18813v1
- LiDAR ISPD'25: 弯曲半径约束 + 交叉惩罚
  https://dl.acm.org/doi/pdf/10.1145/3698364.3705355
- OptoSynthesizer arXiv 2026: 端到端 EPDA 流程
  https://arxiv.org/pdf/2604.15493v1

核心流程:
1. 布局 → 2. 布线 → 3. S参数仿真 → 4. 约束检查 → 5. 反馈调整 → 回到1
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field

from polaris.sim.constraint_checker import (
    CheckContext,
    ConstraintChecker,
    ConstraintConfig,
    Violation,
)
from polaris.sim.feedback_adapter import FeedbackAdapter, FeedbackResult

logger = logging.getLogger(__name__)


@dataclass
class SimLoopConfig:
    """仿真回馈闭环配置。

    Attributes:
        max_iterations: 最大迭代次数。
        constraint_config: 约束检查配置。
        sim_frequency: 仿真频率（每N步仿真一次）。
        loss_target_db: 目标插入损耗（dB）。
    """

    max_iterations: int = 3
    constraint_config: ConstraintConfig | None = None
    sim_frequency: int = 1
    loss_target_db: float = 5.0


@dataclass
class SimLoopResult:
    """仿真回馈闭环结果。

    Attributes:
        success: 是否成功（无约束违规）。
        placements: 最终器件布局。
        paths: 最终布线路径。
        total_loss_db: 总插入损耗（dB）。
        n_crossings: 交叉数。
        violations: 最终违规列表。
        iterations: 实际迭代次数。
        feedback_history: 每轮反馈记录。
    """

    success: bool = False
    placements: dict = field(default_factory=dict)
    paths: dict = field(default_factory=dict)
    total_loss_db: float = 0.0
    n_crossings: int = 0
    violations: list[Violation] = field(default_factory=list)
    iterations: int = 0
    feedback_history: list[FeedbackResult] = field(default_factory=list)


@dataclass
class _IterState:
    """单次迭代状态（内部用）。"""

    placements: dict
    routes: dict
    sim_result: dict
    violations: list[Violation]


class SimLoop:
    """仿真回馈闭环。

    串联: 布局 → 布线 → S参数仿真 → 约束检查 → 反馈调整 → 迭代

    来源:
    - Apollo arXiv 2025: https://arxiv.org/html/2504.18813v1
    """

    def __init__(
        self,
        placer,
        router,
        simulator,
        config: SimLoopConfig | None = None,
    ) -> None:
        self.placer = placer
        self.router = router
        self.simulator = simulator
        self.config = config or SimLoopConfig()
        cons_cfg = self.config.constraint_config or ConstraintConfig()
        self.checker = ConstraintChecker(cons_cfg)
        self.adapter = FeedbackAdapter()

    def run(
        self,
        circuit,
        feedback: FeedbackResult | None = None,
    ) -> SimLoopResult:
        """执行仿真回馈闭环。

        Args:
            circuit: 电路规格。
            feedback: 上一轮反馈（可选，用于迭代优化）。

        Returns:
            SimLoopResult。
        """
        cfg = self.config
        history: list[FeedbackResult] = []

        for iteration in range(cfg.max_iterations):
            logger.info("SimLoop 迭代 %d/%d", iteration + 1, cfg.max_iterations)

            placements, routes, sim_result = self._run_one_step(circuit, feedback)
            violations = self._check_constraints(circuit, placements, routes, sim_result)
            state = _IterState(placements, routes, sim_result, violations)
            fb = self.adapter.adapt(violations)
            history.append(fb)

            self._log_iteration(iteration, violations, sim_result)

            if not violations:
                return self._make_result(True, state, iteration + 1, history)
            feedback = fb

        logger.warning(
            "SimLoop 达到最大迭代 %d，仍有 %d 违规",
            cfg.max_iterations,
            len(violations),
        )
        return self._make_result(False, state, cfg.max_iterations, history)

    def _run_one_step(self, circuit, feedback):
        """执行单步: 布局 → 布线 → 仿真。"""
        placements = self.placer.place(circuit, feedback)
        routes = self.router.route(circuit, placements)
        sim_result = self.simulator.simulate(circuit, placements, routes)
        return placements, routes, sim_result

    def _check_constraints(self, circuit, placements, routes, sim_result):
        """执行约束检查。

        P0-3 修复: 填充 CheckContext 的全部可用字段，确保 16 项 DRC 检查
        均能获取所需输入。字段来源:
        - waveguide_widths: SOI 平台默认 0.5μm（SiEPIC EBeam PDK）
        - waveguide_lengths: 从 routes 计算 path 累积长度
        - device_areas: 从 placements 计算 w×h
        - port_connections: 从 circuit.connections 提取
        - canvas_w/canvas_h: 从 circuit 提取
        - pin_pairs: 从 circuit 器件端口方向提取

        来源:
        - SiEPIC EBeam PDK strip waveguide 宽度 500nm
          https://github.com/SiEPIC/SiEPIC_EBeam_PDK
        """
        # 波导宽度: SOI 平台默认 0.5μm
        # 来源: SiEPIC EBeam PDK strip waveguide 宽度 500nm
        # https://github.com/SiEPIC/SiEPIC_EBeam_PDK
        _SOI_WAVEGUIDE_WIDTH_UM = 0.5
        waveguide_widths = {nid: _SOI_WAVEGUIDE_WIDTH_UM for nid in routes} or None

        # 波导长度: 从 path 点序列计算累积长度
        waveguide_lengths: dict[str, float] = {}
        for nid, pts in routes.items():
            if len(pts) < 2:
                waveguide_lengths[nid] = 0.0
            else:
                waveguide_lengths[nid] = sum(
                    math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1])
                    for i in range(len(pts) - 1)
                )
        waveguide_lengths = waveguide_lengths or None

        # 器件面积: w × h
        device_areas = {
            name: pl.get("w", 0.0) * pl.get("h", 0.0)
            for name, pl in placements.items()
        } or None

        # 端口连接状态: 从 circuit.connections 提取（已连接端口标记为 True）
        port_connections: dict[str, bool] = {}
        for d1, p1, d2, p2 in circuit.connections:
            port_connections[f"{d1}.{p1}"] = True
            port_connections[f"{d2}.{p2}"] = True
        port_connections = port_connections or None

        # 端口方向对: 从 circuit 器件端口提取方向，用于 pin_match 检查
        # 来源: SiEPIC EBeam PDK 端口方向约定
        # https://github.com/SiEPIC/SiEPIC_EBeam_PDK
        dev_port_dirs: dict[str, dict[str, str]] = {}
        for dev in circuit.devices:
            dev_port_dirs[dev.name] = {p[0]: p[3] for p in dev.ports}
        pin_pairs: dict[str, tuple[str, str]] = {}
        for d1, p1, d2, p2 in circuit.connections:
            dir1 = dev_port_dirs.get(d1, {}).get(p1, "")
            dir2 = dev_port_dirs.get(d2, {}).get(p2, "")
            pin_pairs[f"{d1}_{p1}_{d2}_{p2}"] = (dir1, dir2)
        pin_pairs = pin_pairs or None

        ctx = CheckContext(
            total_loss_db=sim_result.get("total_loss_db", 0.0),
            n_crossings=sim_result.get("n_crossings", 0),
            waveguide_widths=waveguide_widths,
            waveguide_lengths=waveguide_lengths,
            device_areas=device_areas,
            port_connections=port_connections,
            canvas_w=circuit.canvas_w,
            canvas_h=circuit.canvas_h,
            pin_pairs=pin_pairs,
        )
        return self.checker.check(placements=placements, paths=routes, context=ctx)

    @staticmethod
    def _log_iteration(iteration, violations, sim_result):
        """记录迭代日志。"""
        logger.info(
            "  迭代 %d: %d 违规, 损耗 %.2f dB, %s",
            iteration + 1,
            len(violations),
            sim_result.get("total_loss_db", 0.0),
            "通过" if not violations else "需调整",
        )

    @staticmethod
    def _make_result(
        success: bool,
        state: _IterState,
        iterations: int,
        history: list[FeedbackResult],
    ) -> SimLoopResult:
        """构造 SimLoopResult。"""
        return SimLoopResult(
            success=success,
            placements=state.placements,
            paths=state.routes,
            total_loss_db=state.sim_result.get("total_loss_db", 0.0),
            n_crossings=state.sim_result.get("n_crossings", 0),
            violations=state.violations,
            iterations=iterations,
            feedback_history=history,
        )


__all__ = [
    "SimLoop",
    "SimLoopConfig",
    "SimLoopResult",
]
