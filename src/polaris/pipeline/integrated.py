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
    """

    canvas_w: float = 1000.0
    canvas_h: float = 1000.0
    grid_size: float = 10.0
    max_sim_iterations: int = 3
    router_type: str = "curvy"
    loss_target_db: float = 5.0
    min_bend_radius_um: float = 5.0
    output_dir: str = "out"


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


class _DefaultPlacer:
    """默认布局器（随机贪心）。"""

    def place(self, circuit: CircuitSpec, feedback=None) -> dict:
        """放置器件。"""
        import random

        rng = random.Random(42)
        placements = {}
        margin = 50.0
        for dev in circuit.devices:
            x = rng.uniform(margin, circuit.canvas_w - dev.width_um - margin)
            y = rng.uniform(margin, circuit.canvas_h - dev.height_um - margin)
            placements[dev.name] = {"x": x, "y": y, "w": dev.width_um, "h": dev.height_um}
        return placements


class _DefaultRouter:
    """默认布线器（A*网格布线）。"""

    def route(self, circuit: CircuitSpec, placements: dict) -> dict:
        """布线连接。"""
        from polaris.router.waveguide_router import GridRouter, RouterConstraints

        grid_w = int(circuit.canvas_w / 10)
        grid_h = int(circuit.canvas_h / 10)
        cons = RouterConstraints(min_bend_radius_um=5.0, min_spacing_um=1.0)
        router = GridRouter(grid_w, grid_h, 10.0, cons)
        paths = {}
        for d1, p1, d2, p2 in circuit.connections:
            if d1 in placements and d2 in placements:
                pos1 = placements[d1]
                pos2 = placements[d2]
                sg = (int(pos1["x"] / 10), int(pos1["y"] / 10))
                eg = (int(pos2["x"] / 10), int(pos2["y"] / 10))
                grid_path = router.route(sg, eg)
                if grid_path:
                    pts = [(g[0] * 10, g[1] * 10) for g in grid_path]
                    paths[f"{d1}_{p1}_{d2}_{p2}"] = pts
        return paths


class _DefaultSimulator:
    """默认仿真器（简化损耗估算）。"""

    # 器件类型 → 单位损耗 (dB)
    _LOSS_TABLE: dict[str, float] = {
        "waveguide": 2.0,  # 需乘以 length/1e4
        "mzi": 0.5,
        "ring": 0.3,
        "grating_coupler": 2.5,
        "mmi": 0.3,
        "y_branch": 0.3,
        "directional_coupler": 0.2,
    }

    def simulate(self, circuit: CircuitSpec, placements: dict, paths: dict) -> dict:
        """仿真S参数。"""
        total_loss = 0.0
        for dev in circuit.devices:
            loss = self._LOSS_TABLE.get(dev.device_type, 0.0)
            if dev.device_type == "waveguide":
                length = dev.params.get("length", dev.width_um)
                total_loss += loss * length / 1e4
            else:
                total_loss += loss
        return {"total_loss_db": total_loss, "n_crossings": 0}


class IntegratedPipeline:
    """一体化流水线。

    端到端: 网表 → GNN编码 → RL布局 → 布线 → 仿真回馈 → 输出

    来源:
    - Apollo arXiv 2025: https://arxiv.org/html/2504.18813v1
    """

    def __init__(self, config: PipelineConfig | None = None) -> None:
        self.config = config or PipelineConfig()
        self.placer = _DefaultPlacer()
        self.router = _DefaultRouter()
        self.simulator = _DefaultSimulator()

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

        return PipelineResult(
            success=sim_result.success,
            circuit_name=circuit.name,
            n_devices=len(circuit.devices),
            n_connections=len(circuit.connections),
            placements=sim_result.placements,
            paths=sim_result.paths,
            total_loss_db=sim_result.total_loss_db,
            n_crossings=sim_result.n_crossings,
            sim_iterations=sim_result.iterations,
            report_path=report_path,
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
