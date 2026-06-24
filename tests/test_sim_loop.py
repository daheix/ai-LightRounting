"""SimLoop 与 IntegratedPipeline 端到端测试。

验证仿真回馈闭环与一体化流水线的完整运行路径，
覆盖之前零测试的 SimLoop.run() / IntegratedPipeline.run()。

来源:
- Apollo arXiv 2025: 布线感知布局反馈
  https://arxiv.org/html/2504.18813v1
"""

from __future__ import annotations

from pathlib import Path

from polaris.data.specs import CircuitSpec, DeviceSpec
from polaris.pipeline.integrated import (
    IntegratedPipeline,
    PipelineConfig,
    PipelineResult,
)
from polaris.sim.constraint_checker import (
    CheckContext,
    ConstraintChecker,
    ConstraintConfig,
)
from polaris.sim.feedback_adapter import FeedbackAdapter, FeedbackResult
from polaris.sim.sim_loop import (
    SimLoop,
    SimLoopConfig,
    SimLoopResult,
)


def _make_circuit() -> CircuitSpec:
    """构造最小测试电路（2 器件 1 连接）。"""
    devs = [
        DeviceSpec(
            name="wg1",
            device_type="waveguide",
            width_um=10,
            height_um=10,
            params={"length": 100},
        ),
        DeviceSpec(
            name="mzi1",
            device_type="mzi",
            width_um=20,
            height_um=20,
        ),
    ]
    conns = [("wg1", "out", "mzi1", "in")]
    return CircuitSpec(
        name="test_simloop",
        canvas_w=200,
        canvas_h=200,
        devices=devs,
        connections=conns,
    )


class _StubPlacer:
    """桩布局器：返回固定布局。

    器件间距 >= 120μm 以满足热安全距离 100μm（SiEPIC EBeam PDK）。
    """

    def place(self, circuit: CircuitSpec, feedback=None) -> dict:
        return {
            dev.name: {"x": 10.0 + i * 120, "y": 10.0, "w": dev.width_um, "h": dev.height_um}
            for i, dev in enumerate(circuit.devices)
        }


class _StubRouter:
    """桩布线器：返回直线路径。"""

    def route(self, circuit: CircuitSpec, placements: dict) -> dict:
        paths = {}
        for d1, p1, d2, p2 in circuit.connections:
            if d1 in placements and d2 in placements:
                x1, y1 = placements[d1]["x"], placements[d1]["y"]
                x2, y2 = placements[d2]["x"], placements[d2]["y"]
                paths[f"{d1}_{p1}_{d2}_{p2}"] = [(x1, y1), (x2, y2)]
        return paths


class _StubSimulator:
    """桩仿真器：返回固定损耗。"""

    def simulate(self, circuit: CircuitSpec, placements: dict, paths: dict) -> dict:
        return {"total_loss_db": 2.0, "n_crossings": 0}


class TestSimLoop:
    """SimLoop 闭环测试。"""

    def test_run_success(self):
        """SimLoop.run 应在无违规时返回 success=True。"""
        cfg = SimLoopConfig(max_iterations=2, loss_target_db=10.0)
        loop = SimLoop(_StubPlacer(), _StubRouter(), _StubSimulator(), cfg)
        result = loop.run(_make_circuit())
        assert isinstance(result, SimLoopResult)
        assert result.success is True
        assert result.iterations == 1
        assert result.total_loss_db == 2.0
        assert result.n_crossings == 0
        assert len(result.placements) == 2
        assert len(result.paths) == 1
        assert result.violations == []

    def test_run_with_loss_violation(self):
        """损耗超标时应返回 success=False 且含 INSERTION_LOSS 违规。"""
        cfg = SimLoopConfig(
            max_iterations=2,
            constraint_config=ConstraintConfig(max_insertion_loss_db=1.0),
        )
        loop = SimLoop(_StubPlacer(), _StubRouter(), _StubSimulator(), cfg)
        result = loop.run(_make_circuit())
        assert result.success is False
        assert result.iterations == 2
        assert len(result.violations) > 0
        assert any(v.vtype.name == "INSERTION_LOSS" for v in result.violations)
        assert len(result.feedback_history) == 2

    def test_run_max_iterations(self):
        """达到最大迭代次数应停止并返回 success=False。"""
        cfg = SimLoopConfig(
            max_iterations=3,
            constraint_config=ConstraintConfig(max_insertion_loss_db=0.1),
        )
        loop = SimLoop(_StubPlacer(), _StubRouter(), _StubSimulator(), cfg)
        result = loop.run(_make_circuit())
        assert result.success is False
        assert result.iterations == 3
        assert len(result.feedback_history) == 3

    def test_check_constraints_uses_check_context(self):
        """_check_constraints 应正确构造 CheckContext 调用 check API。"""
        cfg = SimLoopConfig()
        loop = SimLoop(_StubPlacer(), _StubRouter(), _StubSimulator(), cfg)
        placements = {"d1": {"x": 0, "y": 0, "w": 10, "h": 10}}
        routes = {"n1": [(0, 0), (10, 10)]}
        sim_result = {"total_loss_db": 5.0, "n_crossings": 2}
        violations = loop._check_constraints(_make_circuit(), placements, routes, sim_result)
        assert isinstance(violations, list)


class TestIntegratedPipeline:
    """IntegratedPipeline 端到端测试。"""

    def test_run_success(self, tmp_path):
        """IntegratedPipeline.run 应完成端到端流程并输出报告。"""
        cfg = PipelineConfig(
            canvas_w=200,
            canvas_h=200,
            max_sim_iterations=2,
            loss_target_db=10.0,
            output_dir=str(tmp_path),
        )
        pipe = IntegratedPipeline(cfg)
        result = pipe.run(_make_circuit())
        assert isinstance(result, PipelineResult)
        assert result.circuit_name == "test_simloop"
        assert result.n_devices == 2
        assert result.n_connections == 1
        assert len(result.placements) == 2
        assert len(result.paths) == 1
        assert result.report_path
        assert Path(result.report_path).exists()
        # 报告内容
        import json

        report = json.loads(Path(result.report_path).read_text())
        assert report["circuit"] == "test_simloop"
        assert report["n_devices"] == 2

    def test_run_with_strict_loss(self, tmp_path):
        """严格损耗阈值时应触发迭代并最终返回 success=False。"""
        cfg = PipelineConfig(
            canvas_w=200,
            canvas_h=200,
            max_sim_iterations=2,
            loss_target_db=0.01,
            output_dir=str(tmp_path),
        )
        pipe = IntegratedPipeline(cfg)
        result = pipe.run(_make_circuit())
        assert result.success is False
        assert result.sim_iterations == 2
        assert Path(result.report_path).exists()

    def test_default_placer_router_simulator(self):
        """默认 placer/router/simulator 应正确初始化。"""
        pipe = IntegratedPipeline()
        assert pipe.placer is not None
        assert pipe.router is not None
        assert pipe.simulator is not None


class TestCheckContextIntegration:
    """CheckContext 与 ConstraintChecker 集成测试。"""

    def test_check_with_context(self):
        """check 应正确接受 CheckContext 并检查损耗/交叉。"""
        checker = ConstraintChecker(ConstraintConfig(max_insertion_loss_db=1.0, max_crossings=2))
        ctx = CheckContext(total_loss_db=5.0, n_crossings=5)
        violations = checker.check(placements={}, paths={}, context=ctx)
        assert any(v.vtype.name == "INSERTION_LOSS" for v in violations)
        assert any(v.vtype.name == "CROSSING" for v in violations)

    def test_check_passed_with_context(self):
        """check_passed 应返回 True 当无违规。"""
        checker = ConstraintChecker(ConstraintConfig(max_insertion_loss_db=10.0))
        ctx = CheckContext(total_loss_db=2.0, n_crossings=0)
        assert checker.check_passed(placements={}, paths={}, context=ctx) is True


class TestFeedbackAdapter:
    """FeedbackAdapter 测试（SimLoop 依赖）。"""

    def test_adapt_no_violations(self):
        """无违规时应返回空反馈。"""
        adapter = FeedbackAdapter()
        result = adapter.adapt([])
        assert isinstance(result, FeedbackResult)
        assert result.placement_hints == []

    def test_adapt_with_violations(self):
        """有违规时应生成反馈建议。"""
        from polaris.sim.constraint_checker import Violation, ViolationType

        adapter = FeedbackAdapter()
        violations = [
            Violation(
                vtype=ViolationType.SPACING,
                severity=0.5,
                message="间距不足",
                device_name="d1-d2",
            )
        ]
        result = adapter.adapt(violations)
        assert isinstance(result, FeedbackResult)
