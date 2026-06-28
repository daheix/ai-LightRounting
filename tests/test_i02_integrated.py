"""I02 集成流程验收测试（IntegratedPipeline）。

覆盖验收标准：
- M1: 端到端工作流（布局→布线→仿真→验证）
- M2: 数据传递正确
- M3: 错误处理正确

学术来源:
- Apollo arXiv 2025: https://arxiv.org/html/2504.18813v1
- LiDAR ISPD'25: https://dl.acm.org/doi/pdf/10.1145/3698364.3705355
- OptoSynthesizer arXiv 2026: https://arxiv.org/pdf/2604.15493v1
- IPKISS SDL 流程: https://academy.lucedaphotonics.com/pdks/cornerstone/cornerstone
- gdsfactory 端到端: https://gdsfactory.github.io/gdsfactory/
"""

from __future__ import annotations

import pytest

from polaris.data.specs import CircuitSpec, DeviceSpec
from polaris.flow.recipe import Recipe
from polaris.flow.stage import StageStatus
from polaris.flow.workspace import Workspace
from polaris.pipeline.curvy_router import _CurvyRouter
from polaris.pipeline.integrated import (
    IntegratedPipeline,
    PipelineConfig,
    PipelineResult,
    _DefaultPlacer,
    _DefaultRouter,
)

# =============================================================================
# 辅助函数
# =============================================================================


def _make_simple_circuit() -> CircuitSpec:
    """构造一个简单的 MZI 风格电路。"""
    return CircuitSpec(
        name="test_mzi",
        devices=[
            DeviceSpec(name="gc1", device_type="grating_coupler", width_um=10.0, height_um=10.0,
                       ports=[("o1", 5.0, 5.0, "E")]),
            DeviceSpec(name="mmi1", device_type="mmi_1x2", width_um=20.0, height_um=10.0,
                       ports=[("o1", 0.0, 5.0, "W"), ("o2", 20.0, 2.5, "E"), ("o3", 20.0, 7.5, "E")]),
            DeviceSpec(name="gc2", device_type="grating_coupler", width_um=10.0, height_um=10.0,
                       ports=[("o1", 5.0, 5.0, "W")]),
        ],
        connections=[
            ("gc1", "o1", "mmi1", "o1"),
            ("mmi1", "o2", "gc2", "o1"),
        ],
        canvas_w=200.0,
        canvas_h=200.0,
    )


def _make_simple_circuit_c() -> CircuitSpec:
    """构造简单电路（用于布线测试）。"""
    return CircuitSpec(
        name="simple",
        devices=[
            DeviceSpec(name="d1", device_type="waveguide", width_um=10.0, height_um=10.0,
                       ports=[("in", 0.0, 5.0, "W"), ("out", 10.0, 5.0, "E")]),
            DeviceSpec(name="d2", device_type="waveguide", width_um=10.0, height_um=10.0,
                       ports=[("in", 0.0, 5.0, "W"), ("out", 10.0, 5.0, "E")]),
        ],
        connections=[
            ("d1", "out", "d2", "in"),
        ],
        canvas_w=200.0,
        canvas_h=200.0,
    )


def _make_recipe_from_circuit(circuit: CircuitSpec) -> Recipe:
    """从电路构造 Recipe。"""
    return Recipe(
        preset_id="test",
        enabled_stages=[2, 3, 4, 5],
        custom_circuit={
            "name": circuit.name,
            "devices": [
                {"name": d.name, "device_type": d.device_type,
                 "width_um": d.width_um, "height_um": d.height_um,
                 "ports": [list(p) for p in d.ports],
                 "params": dict(d.params)}
                for d in circuit.devices
            ],
            "connections": [list(c) for c in circuit.connections],
            "canvas_w": circuit.canvas_w,
            "canvas_h": circuit.canvas_h,
            "optical_wavelength_nm": circuit.optical_wavelength_nm,
        },
    )


# =============================================================================
# M1: 端到端工作流测试（通过 run_as_stages 避免 GDS 导出依赖）
# =============================================================================


class TestEndToEndWorkflow:
    """端到端工作流（布局→布线→仿真→验证）测试。"""

    def test_run_as_stages_with_custom_circuit(self, tmp_path):
        """Pipeline 阶段化执行自定义电路。"""
        circuit = _make_simple_circuit()
        cfg = PipelineConfig(
            canvas_w=200.0,
            canvas_h=200.0,
            output_dir=str(tmp_path),
            max_sim_iterations=1,
        )
        pipeline = IntegratedPipeline(cfg)
        recipe = _make_recipe_from_circuit(circuit)
        ws = Workspace(str(tmp_path), "stages_test_1")
        results = pipeline.run_as_stages(recipe, ws)
        assert isinstance(results, list)
        assert len(results) == 4
        assert all(r.status == StageStatus.COMPLETED for r in results)

    def test_run_as_stages_default_demo(self, tmp_path):
        """Pipeline 阶段化执行默认演示电路（使用自定义电路演示）。"""
        circuit = _make_simple_circuit()
        cfg = PipelineConfig(
            canvas_w=200.0,
            canvas_h=200.0,
            output_dir=str(tmp_path),
            max_sim_iterations=1,
        )
        pipeline = IntegratedPipeline(cfg)
        recipe = _make_recipe_from_circuit(circuit)
        ws = Workspace(str(tmp_path), "stages_demo_1")
        results = pipeline.run_as_stages(recipe, ws)
        assert isinstance(results, list)
        assert len(results) == 4

    def test_stages_order(self, tmp_path):
        """阶段按顺序执行：布局→布线→仿真→验证。"""
        circuit = _make_simple_circuit()
        cfg = PipelineConfig(
            canvas_w=200.0,
            canvas_h=200.0,
            output_dir=str(tmp_path),
            max_sim_iterations=1,
        )
        pipeline = IntegratedPipeline(cfg)
        recipe = _make_recipe_from_circuit(circuit)
        ws = Workspace(str(tmp_path), "stages_order_1")
        results = pipeline.run_as_stages(recipe, ws)
        stage_ids = [r.stage_id for r in results]
        assert stage_ids == [2, 3, 4, 5]

    def test_run_as_stages_creates_workspace_files(self, tmp_path):
        """阶段化执行在 workspace 中创建文件。"""
        circuit = _make_simple_circuit()
        cfg = PipelineConfig(
            canvas_w=200.0,
            canvas_h=200.0,
            output_dir=str(tmp_path),
            max_sim_iterations=1,
        )
        pipeline = IntegratedPipeline(cfg)
        recipe = _make_recipe_from_circuit(circuit)
        ws = Workspace(str(tmp_path), "stages_files_1")
        pipeline.run_as_stages(recipe, ws)
        assert ws.base_path.exists()
        stage_dir = ws.base_path / "stages"
        assert stage_dir.exists()

    def test_stage_outputs_persisted(self, tmp_path):
        """每阶段输出持久化到 workspace。"""
        circuit = _make_simple_circuit()
        cfg = PipelineConfig(
            canvas_w=200.0,
            canvas_h=200.0,
            output_dir=str(tmp_path),
            max_sim_iterations=1,
        )
        pipeline = IntegratedPipeline(cfg)
        recipe = _make_recipe_from_circuit(circuit)
        ws = Workspace(str(tmp_path), "stages_persist_1")
        pipeline.run_as_stages(recipe, ws)
        placement_out = ws.read_stage_output("stage3_placement")
        assert placement_out is not None
        assert "placements" in placement_out

    def test_curvy_router_used_in_stages(self, tmp_path):
        """阶段化执行使用弯曲布线器。"""
        circuit = _make_simple_circuit()
        cfg = PipelineConfig(
            canvas_w=200.0,
            canvas_h=200.0,
            output_dir=str(tmp_path),
            max_sim_iterations=1,
            router_type="curvy",
        )
        pipeline = IntegratedPipeline(cfg)
        recipe = _make_recipe_from_circuit(circuit)
        ws = Workspace(str(tmp_path), "stages_curvy_1")
        results = pipeline.run_as_stages(recipe, ws)
        assert results[1].stage_id == 3
        assert results[1].status == StageStatus.COMPLETED

    def test_sim_stage_returns_sparams(self, tmp_path):
        """仿真阶段返回 S 参数结果。"""
        circuit = _make_simple_circuit()
        cfg = PipelineConfig(
            canvas_w=200.0,
            canvas_h=200.0,
            output_dir=str(tmp_path),
            max_sim_iterations=2,
        )
        pipeline = IntegratedPipeline(cfg)
        recipe = _make_recipe_from_circuit(circuit)
        ws = Workspace(str(tmp_path), "stages_sim_1")
        pipeline.run_as_stages(recipe, ws)
        sim_result = ws.read_stage_output("stage5_simulation")
        assert sim_result is not None
        assert "sparams" in sim_result
        assert "total_loss_db" in sim_result


# =============================================================================
# M2: 数据传递测试
# =============================================================================


class TestDataFlow:
    """数据传递正确性测试。"""

    def test_default_placer_returns_correct_format(self):
        """布局器输出格式正确。"""
        circuit = _make_simple_circuit()
        placer = _DefaultPlacer(mode="random")
        placements = placer.place(circuit)
        assert isinstance(placements, dict)
        assert len(placements) == len(circuit.devices)
        for _name, pl in placements.items():
            assert isinstance(pl["x"], float)
            assert isinstance(pl["y"], float)
            assert isinstance(pl["w"], float)
            assert isinstance(pl["h"], float)

    def test_default_router_returns_correct_format(self):
        """布线器输出格式正确。"""
        circuit = _make_simple_circuit_c()
        placer = _DefaultPlacer(mode="random")
        placements = placer.place(circuit)
        router = _DefaultRouter()
        paths = router.route(circuit, placements)
        assert isinstance(paths, dict)
        for _key, path in paths.items():
            assert isinstance(path, list)
            assert len(path) >= 2
            for point in path:
                assert len(point) == 2

    def test_curvy_router_returns_correct_format(self):
        """弯曲布线器输出格式正确。"""
        circuit = _make_simple_circuit_c()
        placer = _DefaultPlacer(mode="random")
        placements = placer.place(circuit)
        router = _CurvyRouter(curve_type="euler")
        paths = router.route(circuit, placements)
        assert isinstance(paths, dict)
        for _key, path in paths.items():
            assert isinstance(path, list)
            assert len(path) >= 2

    def test_placements_within_canvas(self):
        """布局结果在画布范围内。"""
        circuit = _make_simple_circuit()
        placer = _DefaultPlacer(mode="random")
        placements = placer.place(circuit)
        for _name, pl in placements.items():
            assert pl["x"] >= 0
            assert pl["y"] >= 0
            assert pl["x"] + pl["w"] <= circuit.canvas_w + 1e-6
            assert pl["y"] + pl["h"] <= circuit.canvas_h + 1e-6

    def test_stage_data_passed_through(self, tmp_path):
        """阶段间数据正确传递。"""
        circuit = _make_simple_circuit()
        cfg = PipelineConfig(
            canvas_w=200.0,
            canvas_h=200.0,
            output_dir=str(tmp_path),
            max_sim_iterations=1,
        )
        pipeline = IntegratedPipeline(cfg)
        recipe = _make_recipe_from_circuit(circuit)
        ws = Workspace(str(tmp_path), "stages_data_1")
        pipeline.run_as_stages(recipe, ws)

        placement_out = ws.read_stage_output("stage3_placement")
        route_out = ws.read_stage_output("stage4_routing")

        assert placement_out is not None
        assert route_out is not None
        assert "placements" in placement_out
        assert "routes" in route_out

    def test_pipeline_result_dataclass_fields(self):
        """PipelineResult 包含所有必要字段。"""
        result = PipelineResult(
            success=True,
            circuit_name="test",
            n_devices=3,
            n_connections=2,
            placements={"d1": {"x": 0.0, "y": 0.0, "w": 10.0, "h": 10.0}},
            paths={"conn": [(0.0, 0.0), (10.0, 0.0)]},
            total_loss_db=0.5,
            drc_passed=True,
        )
        assert result.success is True
        assert result.circuit_name == "test"
        assert result.n_devices == 3
        assert result.total_loss_db == 0.5


# =============================================================================
# M3: 错误处理测试
# =============================================================================


class TestErrorHandling:
    """错误处理正确性测试。"""

    def test_empty_circuit_raises_value_error(self, tmp_path):
        """空电路布局阶段抛出 ValueError（符合 R03 无 fall-back 规范）。"""
        circuit = CircuitSpec(
            name="empty",
            devices=[],
            connections=[],
            canvas_w=200.0,
            canvas_h=200.0,
        )
        cfg = PipelineConfig(
            canvas_w=200.0,
            canvas_h=200.0,
            output_dir=str(tmp_path),
            max_sim_iterations=1,
        )
        pipeline = IntegratedPipeline(cfg)
        recipe = _make_recipe_from_circuit(circuit)
        ws = Workspace(str(tmp_path), "empty_circuit_1")
        with pytest.raises(ValueError, match="无器件可布局"):
            pipeline.run_as_stages(recipe, ws)

    def test_placer_empty_circuit_returns_empty(self):
        """布局器处理空电路返回空字典。"""
        circuit = CircuitSpec(
            name="empty",
            devices=[],
            connections=[],
            canvas_w=200.0,
            canvas_h=200.0,
        )
        placer = _DefaultPlacer(mode="random")
        placements = placer.place(circuit)
        assert placements == {}

    def test_router_no_connections_returns_empty(self):
        """布线器处理无连接电路返回空字典。"""
        circuit = CircuitSpec(
            name="no_conn",
            devices=[
                DeviceSpec(name="d1", device_type="waveguide", width_um=10.0, height_um=10.0),
            ],
            connections=[],
            canvas_w=200.0,
            canvas_h=200.0,
        )
        placer = _DefaultPlacer(mode="random")
        placements = placer.place(circuit)
        router = _DefaultRouter()
        paths = router.route(circuit, placements)
        assert paths == {}

    def test_pipeline_config_default_values(self):
        """PipelineConfig 默认值正确。"""
        cfg = PipelineConfig()
        assert cfg.canvas_w == 1000.0
        assert cfg.canvas_h == 1000.0
        assert cfg.max_sim_iterations == 3
        assert cfg.router_type == "curvy"
        assert cfg.loss_target_db == 5.0

    def test_pipeline_result_default_values(self):
        """PipelineResult 默认值正确。"""
        result = PipelineResult()
        assert result.success is False
        assert result.n_devices == 0
        assert result.n_connections == 0
        assert result.total_loss_db == 0.0
        assert result.drc_passed is False

    def test_run_as_stages_invalid_stage_raises(self, tmp_path):
        """无效阶段 ID 触发异常。"""
        cfg = PipelineConfig()
        pipeline = IntegratedPipeline(cfg)
        recipe = Recipe(
            preset_id="test",
            enabled_stages=[999],
        )
        ws = Workspace(str(tmp_path), "invalid_stage_1")
        with pytest.raises(ValueError):
            pipeline.run_as_stages(recipe, ws)
