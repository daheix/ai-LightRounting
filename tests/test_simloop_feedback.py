"""SimLoop 反馈接入 RL reward shaping 测试（M3.3）。

验证 SimLoop 仿真反馈（违规、损耗）能被反馈到 FloorplanEnv 奖励塑形：
1. SimLoop 运行 1 轮迭代后生成 FeedbackResult
2. 反馈包含约束违规与损耗指标
3. 反馈可转化为 ExpertRewardInput 注入 RL 奖励

来源:
- Apollo arXiv 2025: 布线感知布局反馈
  https://arxiv.org/html/2504.18813v1
- ICLR'26 专家RL: 领域知识注入
  https://openreview.net/forum?id=yqvNwfxRR6
"""

from __future__ import annotations

import math

from polaris.data.specs import CircuitSpec, DeviceSpec
from polaris.sim.constraint_checker import ConstraintConfig, Violation, ViolationType
from polaris.sim.feedback_adapter import FeedbackAdapter, FeedbackResult
from polaris.sim.sim_loop import SimLoop, SimLoopConfig
from polaris.trainer.reward_shaping import (
    ExpertRewardInput,
    ExpertRewardShaper,
)


def _make_circuit() -> CircuitSpec:
    """构造测试电路（3 器件 2 连接，含热源与热敏感器件）。"""
    return CircuitSpec(
        name="simloop_feedback_test",
        devices=[
            DeviceSpec(name="heater1", device_type="heater", width_um=20, height_um=20),
            DeviceSpec(name="ring1", device_type="ring", width_um=15, height_um=15),
            DeviceSpec(name="gc1", device_type="grating_coupler", width_um=10, height_um=10),
        ],
        connections=[
            ("gc1", "o1", "ring1", "o1"),
            ("ring1", "o2", "gc1", "o2"),
        ],
        canvas_w=200,
        canvas_h=200,
    )


class _OverlapPlacer:
    """桩布局器：器件重叠放置以触发 OVERLAP/SPACING 违规。"""

    def place(self, circuit: CircuitSpec, feedback=None) -> dict:
        return {
            dev.name: {"x": 10.0, "y": 10.0, "w": dev.width_um, "h": dev.height_um}
            for dev in circuit.devices
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


class _HighLossSimulator:
    """桩仿真器：返回高损耗以触发 INSERTION_LOSS 违规。"""

    def simulate(self, circuit: CircuitSpec, placements: dict, paths: dict) -> dict:
        return {"total_loss_db": 15.0, "n_crossings": 0}


class TestSimLoopFeedbackGeneration:
    """SimLoop 反馈生成测试。"""

    def test_one_iteration_generates_feedback(self):
        """SimLoop 运行 1 轮迭代后应生成 FeedbackResult。"""
        cfg = SimLoopConfig(
            max_iterations=1,
            constraint_config=ConstraintConfig(max_insertion_loss_db=1.0),
        )
        loop = SimLoop(_OverlapPlacer(), _StubRouter(), _HighLossSimulator(), cfg)
        result = loop.run(_make_circuit())
        assert result.iterations == 1
        assert len(result.feedback_history) == 1
        fb = result.feedback_history[0]
        assert isinstance(fb, FeedbackResult)
        assert fb.should_retry is True

    def test_feedback_contains_violations(self):
        """反馈应包含约束违规（OVERLAP/SPACING/INSERTION_LOSS）。"""
        cfg = SimLoopConfig(
            max_iterations=1,
            constraint_config=ConstraintConfig(
                max_insertion_loss_db=1.0,
                min_spacing_um=5.0,
            ),
        )
        loop = SimLoop(_OverlapPlacer(), _StubRouter(), _HighLossSimulator(), cfg)
        result = loop.run(_make_circuit())
        vtypes = {v.vtype for v in result.violations}
        assert ViolationType.OVERLAP in vtypes or ViolationType.SPACING in vtypes, (
            f"应含 OVERLAP 或 SPACING 违规，实际 {vtypes}"
        )
        assert ViolationType.INSERTION_LOSS in vtypes, f"应含 INSERTION_LOSS 违规，实际 {vtypes}"

    def test_feedback_contains_loss_metric(self):
        """反馈应含损耗指标（total_loss_db > 0）。"""
        cfg = SimLoopConfig(
            max_iterations=1,
            constraint_config=ConstraintConfig(max_insertion_loss_db=1.0),
        )
        loop = SimLoop(_OverlapPlacer(), _StubRouter(), _HighLossSimulator(), cfg)
        result = loop.run(_make_circuit())
        assert result.total_loss_db > 0.0, f"损耗应 > 0，实际 {result.total_loss_db}"
        assert result.total_loss_db == 15.0

    def test_feedback_has_placement_hints(self):
        """FeedbackResult 应含布局调整建议（由违规转化而来）。"""
        cfg = SimLoopConfig(
            max_iterations=1,
            constraint_config=ConstraintConfig(
                max_insertion_loss_db=1.0,
                min_spacing_um=5.0,
            ),
        )
        loop = SimLoop(_OverlapPlacer(), _StubRouter(), _HighLossSimulator(), cfg)
        result = loop.run(_make_circuit())
        fb = result.feedback_history[0]
        assert len(fb.placement_hints) > 0, "应至少有 1 条布局调整建议"


class TestFeedbackToRewardShaping:
    """SimLoop 反馈接入 RL 奖励塑形测试。"""

    def test_feedback_to_expert_reward_input(self):
        """SimLoop 反馈可转化为 ExpertRewardInput 注入 RL 奖励。

        验证反馈闭环：SimLoop 违规 → 器件位置 → ExpertRewardInput →
        ExpertRewardShaper.compute() → 专家奖励。
        """
        cfg = SimLoopConfig(
            max_iterations=1,
            constraint_config=ConstraintConfig(max_insertion_loss_db=1.0),
        )
        loop = SimLoop(_OverlapPlacer(), _StubRouter(), _HighLossSimulator(), cfg)
        circuit = _make_circuit()
        result = loop.run(circuit)

        device_positions = {name: (pl["x"], pl["y"]) for name, pl in result.placements.items()}
        connections = [(d1, p1, d2, p2) for d1, p1, d2, p2 in circuit.connections]
        reward_input = ExpertRewardInput(
            device_positions=device_positions,
            connections=connections,
            thermal_sources={"heater1"},
            thermal_sensitive={"ring1"},
        )
        shaper = ExpertRewardShaper()
        reward_result = shaper.compute(reward_input)
        assert reward_result.thermal_penalty > 0.0, "热源与热敏感器件重叠应触发热惩罚"
        assert math.isfinite(reward_result.total_expert_reward)

    def test_feedback_adapter_directly(self):
        """FeedbackAdapter 应将违规转化为布局/布线调整建议。"""
        adapter = FeedbackAdapter()
        violations = [
            Violation(
                vtype=ViolationType.OVERLAP,
                severity=1.0,
                message="器件重叠",
                device_name="heater1-ring1",
            ),
            Violation(
                vtype=ViolationType.INSERTION_LOSS,
                severity=0.8,
                message="损耗超标",
            ),
        ]
        fb = adapter.adapt(violations)
        assert isinstance(fb, FeedbackResult)
        assert fb.should_retry is True
        assert len(fb.placement_hints) >= 1, "应至少有 1 条布局建议"

    def test_feedback_reward_correlation(self):
        """违规越多，专家奖励应越低（负相关）。"""
        circuit = _make_circuit()
        connections = [(d1, p1, d2, p2) for d1, p1, d2, p2 in circuit.connections]
        shaper = ExpertRewardShaper()
        good_positions = {
            "heater1": (0.0, 0.0),
            "ring1": (200.0, 0.0),
            "gc1": (100.0, 100.0),
        }
        good_input = ExpertRewardInput(
            device_positions=good_positions,
            connections=connections,
            thermal_sources={"heater1"},
            thermal_sensitive={"ring1"},
        )
        good_reward = shaper.compute(good_input).total_expert_reward
        bad_positions = {
            "heater1": (10.0, 10.0),
            "ring1": (10.0, 10.0),
            "gc1": (10.0, 10.0),
        }
        bad_input = ExpertRewardInput(
            device_positions=bad_positions,
            connections=connections,
            thermal_sources={"heater1"},
            thermal_sensitive={"ring1"},
        )
        bad_reward = shaper.compute(bad_input).total_expert_reward
        assert bad_reward < good_reward, (
            f"重叠布局奖励 {bad_reward} 应小于分散布局奖励 {good_reward}"
        )
        assert math.isfinite(good_reward) and math.isfinite(bad_reward)
