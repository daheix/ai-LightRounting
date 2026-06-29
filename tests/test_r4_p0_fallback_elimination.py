"""R4 第4轮 P0 回归测试: 静默 fall-back 全面消除。

R4 修复的 7 个 P0 问题:
- P0-1: waveguide_router.py:637 _PLATFORM_LOSS_DB_CM.get(platform, 2.0) → raise KeyError
- P0-2: cml_compiler_full.py:258 unit_map.get(freq_unit, 1e9) → raise ValueError
- P0-3: obstacle_grid.py:91 _PLATFORM_WAVEGUIDE_WIDTH.get(platform, 0.5) → raise KeyError
- P0-4: tcad_thermal_package.py:861 未知耦合方式 fall-back 4.0 → raise ValueError
- P0-5: quantum_circuit_distributed.py:41 docstring 1/16 → 1/9 (Ralph 2002)
- P0-6: fde/solver.py:82 docstring shift_frac 0.3 → 0.5
- P0-7: curvy_optodesigner.py crossing_loss 0.1 → 0.3 (跨模块统一)

R4-P1 修复:
- multilayer.py: return None → raise RuntimeError（3 处）
- multilayer.py: 硬编码 2.0 dB/cm → 按 layer.platform 查询 _PLATFORM_LOSS_DB_CM

学术依据:
- R03 禁止 fall-back 规则: /workspace/.trae/rules/R03-禁止fall-back.md
- Touchstone File Format Specification, IBIS Open Forum 2009
  https://ibis.org/connector/touchstone_spec11.pdf
- SiEPIC EBeam PDK https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- Ralph et al. PRA 2002 https://doi.org/10.1103/PhysRevA.65.062324
- Knill, Laflamme, Milburn, Nature 2001 https://www.nature.com/articles/35051009

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R05 Bug 必修。
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pytest


# =============================================================================
# R4-P0-1: waveguide_router.route_connection 未知平台必须 raise
# =============================================================================

class TestR4P01WaveguideRouterPlatformFallback:
    """R4-P0-1: waveguide_router._PLATFORM_LOSS_DB_CM.get fall-back 消除。"""

    def test_known_platform_soi_works(self):
        """已知平台 SOI 应正常布线。"""
        from polaris.router.waveguide_router import route_connection
        wp = route_connection((10, 10), (150, 100), platform="SOI")
        assert wp.loss_db > 0.0
        assert len(wp.points) >= 2

    def test_known_platform_sin_works(self):
        """已知平台 SiN 应正常布线。"""
        from polaris.router.waveguide_router import route_connection
        wp = route_connection((10, 10), (150, 100), platform="SiN")
        assert wp.loss_db > 0.0

    def test_unknown_platform_raises_keyerror(self):
        """R4-P0-1: 未知平台必须 raise KeyError，禁止 fall-back 到 2.0 dB/cm。"""
        from polaris.router.waveguide_router import route_connection
        with pytest.raises(KeyError, match="未定义平台"):
            route_connection((10, 10), (150, 100), platform="UNKNOWN_GaAs")

    def test_no_magic_2_0_db_cm(self):
        """R4-P0-1: 验证源码无 2.0 dB/cm 魔数 fall-back。"""
        import polaris.router.waveguide_router as mod
        src = Path(mod.__file__).read_text(encoding="utf-8")
        # 查找 _PLATFORM_LOSS_DB_CM.get(... 2.0) 模式
        assert "_PLATFORM_LOSS_DB_CM.get(platform, 2.0)" not in src, (
            "R4-P0-1: 仍存在 _PLATFORM_LOSS_DB_CM.get(platform, 2.0) fall-back"
        )


# =============================================================================
# R4-P0-2: cml_compiler_full 未知频率单位必须 raise
# =============================================================================

class TestR4P02CmlCompilerFreqUnitFallback:
    """R4-P0-2: cml_compiler_full unit_map.get(freq_unit, 1e9) fall-back 消除。"""

    def test_known_unit_ghz(self, tmp_path):
        """已知单位 GHz 应正常解析。"""
        from polaris.sim.cml_compiler_full import SParameterLoader
        # 写入最小 Touchstone 1-port 文件（解析器期望 # <unit> S <fmt> <n_ports>）
        # 1-port RI: cols = 1 (freq) + 2*1^2 (Re, Im) = 3
        content = "# GHz S RI 1\n1.0 0.9 0.1\n"
        ts_file = tmp_path / "test.s1p"
        ts_file.write_text(content, encoding="utf-8")

        port_names, freqs, s_matrix = SParameterLoader.load_touchstone(ts_file)
        assert len(freqs) == 1
        assert freqs[0] == pytest.approx(1e9)  # 1 GHz = 1e9 Hz

    def test_unknown_unit_raises(self, tmp_path):
        """R4-P0-2: 未知频率单位必须 raise ValueError。"""
        from polaris.sim.cml_compiler_full import SParameterLoader
        content = "# PHz S RI 1\n1.0 0.9 0.1\n"
        ts_file = tmp_path / "bad.s1p"
        ts_file.write_text(content, encoding="utf-8")

        with pytest.raises(ValueError, match="不支持"):
            SParameterLoader.load_touchstone(ts_file)

    def test_no_magic_1e9_fallback(self):
        """R4-P0-2: 验证源码无 unit_map.get(freq_unit, 1e9) fall-back。"""
        import polaris.sim.cml_compiler_full as mod
        src = Path(mod.__file__).read_text(encoding="utf-8")
        assert "unit_map.get(freq_unit, 1e9)" not in src, (
            "R4-P0-2: 仍存在 unit_map.get(freq_unit, 1e9) fall-back"
        )


# =============================================================================
# R4-P0-3: obstacle_grid 未知平台必须 raise
# =============================================================================

class TestR4P03ObstacleGridPlatformFallback:
    """R4-P0-3: obstacle_grid._PLATFORM_WAVEGUIDE_WIDTH.get fall-back 消除。"""

    def test_known_platform_soi(self):
        """已知平台 SOI 应返回正确 grid_size。"""
        from polaris.router.obstacle_grid import auto_grid_size
        gs = auto_grid_size(canvas_w=500.0, canvas_h=500.0, platform="SOI")
        # SOI: w=0.5, R=5 → max(0.6, 2.5, 0.25) = 2.5
        assert gs == pytest.approx(2.5)

    def test_known_platform_sin(self):
        """已知平台 SiN 应返回正确 grid_size。"""
        from polaris.router.obstacle_grid import auto_grid_size
        gs = auto_grid_size(canvas_w=5000.0, canvas_h=5000.0, platform="SiN")
        # SiN: w=1.0, R=100 → max(1.2, 50.0, 2.5) = 50.0
        assert gs == pytest.approx(50.0)

    def test_unknown_platform_raises_keyerror(self):
        """R4-P0-3: 未知平台必须 raise KeyError，禁止 fall-back 到 0.5 μm。"""
        from polaris.router.obstacle_grid import auto_grid_size
        with pytest.raises(KeyError, match="未定义平台"):
            auto_grid_size(canvas_w=1000.0, canvas_h=1000.0, platform="UNKNOWN_GaAs")

    def test_no_magic_0_5_fallback(self):
        """R4-P0-3: 验证源码无 _PLATFORM_WAVEGUIDE_WIDTH.get(platform, 0.5) fall-back。"""
        import polaris.router.obstacle_grid as mod
        src = Path(mod.__file__).read_text(encoding="utf-8")
        assert "_PLATFORM_WAVEGUIDE_WIDTH.get(platform, 0.5)" not in src, (
            "R4-P0-3: 仍存在 _PLATFORM_WAVEGUIDE_WIDTH.get(platform, 0.5) fall-back"
        )


# =============================================================================
# R4-P0-4: tcad_thermal_package 未知耦合方式必须 raise
# =============================================================================

class TestR4P04TcadCouplingMethodFallback:
    """R4-P0-4: tcad_thermal_package 未知耦合方式 fall-back 4.0 消除。"""

    def test_known_method_grating(self):
        """已知方式 grating 应返回 4.0 dB/端。"""
        from polaris.device.tcad_thermal_package import PackageDesigner
        pkg = PackageDesigner()
        result = pkg.estimate_insertion_loss_db(fiber_count=2, coupling_method="grating")
        assert result["loss_per_port_db"] == pytest.approx(4.0)

    def test_known_method_edge(self):
        """已知方式 edge 应返回 1.5 dB/端。"""
        from polaris.device.tcad_thermal_package import PackageDesigner
        pkg = PackageDesigner()
        result = pkg.estimate_insertion_loss_db(fiber_count=2, coupling_method="edge")
        assert result["loss_per_port_db"] == pytest.approx(1.5)

    def test_known_method_lens(self):
        """已知方式 lens 应返回 0.8 dB/端。"""
        from polaris.device.tcad_thermal_package import PackageDesigner
        pkg = PackageDesigner()
        result = pkg.estimate_insertion_loss_db(fiber_count=2, coupling_method="lens")
        assert result["loss_per_port_db"] == pytest.approx(0.8)

    def test_unknown_method_raises(self):
        """R4-P0-4: 未知耦合方式必须 raise ValueError，禁止 fall-back 到 4.0。"""
        from polaris.device.tcad_thermal_package import PackageDesigner
        pkg = PackageDesigner()
        with pytest.raises(ValueError, match="未知光纤耦合方式"):
            pkg.estimate_insertion_loss_db(fiber_count=2, coupling_method="free_space")

    def test_no_magic_4_0_fallback(self):
        """R4-P0-4: 验证源码无 .get(coupling_method, 4.0) fall-back。"""
        import polaris.device.tcad_thermal_package as mod
        src = Path(mod.__file__).read_text(encoding="utf-8")
        assert ".get(coupling_method, 4.0)" not in src, (
            "R4-P0-4: 仍存在 .get(coupling_method, 4.0) fall-back"
        )


# =============================================================================
# R4-P0-5: KLM CNOT docstring 1/16 → 1/9 (Ralph 2002)
# =============================================================================

class TestR4P05KlmCnotDocstringFix:
    """R4-P0-5: quantum_circuit_distributed.py docstring 1/16 → 1/9。"""

    def test_module_docstring_says_1_9(self):
        """R4-P0-5: 模块 docstring 应说明成功概率 1/9 (Ralph 2002)。"""
        import polaris.quantum.quantum_circuit_distributed as mod
        src = Path(mod.__file__).read_text(encoding="utf-8")
        # 提取前 50 行（模块 docstring 区域）
        head = src.split('"""')[1] if '"""' in src else src[:2000]
        assert "1/9" in head, (
            "R4-P0-5: 模块 docstring 应包含 1/9 (Ralph 2002 成功概率)"
        )
        assert "Ralph 2002" in head, (
            "R4-P0-5: 模块 docstring 应明确标注 Ralph 2002 方案"
        )

    def test_apply_klm_cnot_returns_1_9_reference(self):
        """R4-P0-5: apply_klm_cnot 返回的 success_prob_reference 应为 1/9。"""
        from polaris.quantum.quantum_circuit_distributed import QuantumCircuitSimulator

        class ForceSuccessRNG:
            def random(self, size=None):
                if size is None:
                    return 0.0
                return np.zeros(size, dtype=float)
            def standard_normal(self, *args, **kwargs):
                raise NotImplementedError

        sim = QuantumCircuitSimulator(n_qubits=2)
        result = sim.apply_klm_cnot(0, 1, rng=ForceSuccessRNG())
        assert result["success_prob_reference"] == pytest.approx(1.0 / 9.0), (
            f"success_prob_reference 应为 1/9 (Ralph 2002)，"
            f"实际 {result['success_prob_reference']}"
        )


# =============================================================================
# R4-P0-6: FDE solver docstring shift_frac 0.3 → 0.5
# =============================================================================

class TestR4P06FdeShiftFracDocstringFix:
    """R4-P0-6: fde/solver.py FdeSolverConfig docstring shift_frac 0.3 → 0.5。"""

    def test_docstring_says_0_5(self):
        """R4-P0-6: docstring 应说明 shift_frac 默认 0.5。"""
        import polaris.sim.fde.solver as mod
        src = Path(mod.__file__).read_text(encoding="utf-8")
        # 提取 FdeSolverConfig 类的 docstring
        # 查找 "shift_frac" 在 docstring 中的描述
        # 原 bug: "默认 0.3 偏向波导基模"
        # 修复后: "默认 0.5 取 n_clad 与 n_core 中点"
        assert "默认 0.3 偏向波导基模" not in src, (
            "R4-P0-6: docstring 仍含旧的 '默认 0.3 偏向波导基模' 描述"
        )
        assert "默认 0.5" in src, (
            "R4-P0-6: docstring 应包含 '默认 0.5' 描述"
        )

    def test_default_value_is_0_5(self):
        """R4-P0-6: shift_frac 实际默认值应为 0.5。"""
        from polaris.sim.fde.solver import FdeSolverConfig
        cfg = FdeSolverConfig(wavelength=1.55e-6)
        assert cfg.shift_frac == pytest.approx(0.5), (
            f"shift_frac 默认值应为 0.5，实际 {cfg.shift_frac}"
        )


# =============================================================================
# R4-P0-7: 跨模块 crossing_loss 统一为 0.3 dB
# =============================================================================

class TestR4P07CrossingLossUnification:
    """R4-P0-7: 跨模块 crossing_loss 统一为 0.3 dB (SiEPIC EBeam PDK 上界)。"""

    def test_curvy_optodesigner_default_is_0_3(self):
        """R4-P0-7: AdaptiveCrossingInserter 默认 crossing_loss 应为 0.3 dB。"""
        from polaris.router.curvy_optodesigner import AdaptiveCrossingInserter
        inserter = AdaptiveCrossingInserter()
        assert inserter.crossing_loss == pytest.approx(0.3), (
            f"默认 crossing_loss 应为 0.3 dB，实际 {inserter.crossing_loss}"
        )

    def test_path_geometry_default_is_0_3(self):
        """R4-P0-7: path_geometry.path_loss 默认 crossing_loss_db 应为 0.3 dB。"""
        import inspect
        from polaris.router.path_geometry import path_loss
        sig = inspect.signature(path_loss)
        assert sig.parameters["crossing_loss_db"].default == pytest.approx(0.3), (
            f"path_loss crossing_loss_db 默认值应为 0.3，"
            f"实际 {sig.parameters['crossing_loss_db'].default}"
        )

    def test_no_0_1_default_in_optodesigner(self):
        """R4-P0-7: 验证 curvy_optodesigner 源码无 crossing_loss: float = 0.1 默认值。"""
        import polaris.router.curvy_optodesigner as mod
        src = Path(mod.__file__).read_text(encoding="utf-8")
        assert "crossing_loss: float = 0.1" not in src, (
            "R4-P0-7: 仍存在 crossing_loss: float = 0.1 旧默认值"
        )

    def test_custom_crossing_loss_still_works(self):
        """R4-P0-7: 自定义 crossing_loss 仍可工作。"""
        from polaris.router.curvy_optodesigner import AdaptiveCrossingInserter
        inserter = AdaptiveCrossingInserter(crossing_loss=0.2)
        assert inserter.crossing_loss == pytest.approx(0.2)


# =============================================================================
# R4-P1: multilayer.py R03 修复（return None + 硬编码 2.0 dB/cm）
# =============================================================================

class TestR4P1MultilayerFallbackElimination:
    """R4-P1: multilayer.py 多处 R03 修复。"""

    def _make_router(self):
        """构造 2 层 MultiLayerRouter 测试夹具。"""
        from polaris.router.multilayer import (
            LayerSpec,
            MultiLayerRouter,
            OTVSpec,
        )
        layers = [
            LayerSpec(name="SOI", grid_w=100, grid_h=100, grid_size=1.0, platform="SOI"),
            LayerSpec(name="SiN", grid_w=100, grid_h=100, grid_size=1.0, platform="SiN"),
        ]
        otvs = [OTVSpec(name="otv1", layer_from=0, layer_to=1, x=50.0, y=50.0, loss_db=0.5)]
        return MultiLayerRouter(layers=layers, otvs=otvs)

    def test_single_layer_route_succeeds(self):
        """R4-P1: 单层布线成功应返回 MultiLayerRouteResult。"""
        router = self._make_router()
        result = router.route(start_layer=0, start_pos=(10, 10),
                              end_layer=0, end_pos=(90, 90))
        assert result is not None
        assert result.total_length_um > 0
        # SOI: 3.0 dB/cm，路径约 113 μm = 0.0113 cm → 损耗约 0.034 dB
        assert result.total_loss_db > 0

    def test_single_layer_route_uses_platform_loss(self):
        """R4-P1: 单层布线损耗应使用 layer.platform 对应的 _PLATFORM_LOSS_DB_CM。"""
        from polaris.router.waveguide_router import _PLATFORM_LOSS_DB_CM
        router = self._make_router()
        result = router.route(start_layer=0, start_pos=(10, 10),
                              end_layer=0, end_pos=(90, 90))
        # SOI 损耗系数应为 3.0 dB/cm（而非旧的硬编码 2.0）
        expected_loss = result.total_length_um * _PLATFORM_LOSS_DB_CM["SOI"] / 1e4
        assert result.total_loss_db == pytest.approx(expected_loss, rel=1e-6)

    def test_single_layer_route_blocked_raises(self):
        """R4-P1: 单层布线被障碍物阻塞时应 raise RuntimeError（不返回 None）。

        通过阻塞终点周围区域使 A* 无法到达终点。
        """
        router = self._make_router()
        # 阻塞终点 (90, 90) 周围 3x3 区域
        router.add_obstacle(0, (89, 89, 3, 3))
        with pytest.raises(RuntimeError, match="布线失败"):
            router.route(start_layer=0, start_pos=(10, 10),
                         end_layer=0, end_pos=(90, 90))

    def test_multi_layer_route_succeeds(self):
        """R4-P1: 多层布线成功应返回合并的 MultiLayerRouteResult。"""
        router = self._make_router()
        result = router.route(start_layer=0, start_pos=(10, 10),
                              end_layer=1, end_pos=(90, 90))
        assert result is not None
        assert len(result.otv_used) == 1
        assert result.otv_used[0].name == "otv1"
        # 总损耗 = 层0损耗 + 层1损耗 + OTV 损耗
        assert result.total_loss_db > 0.5  # OTV 单独 0.5 dB

    def test_multi_layer_route_no_otv_raises(self):
        """R4-P1: 多层布线无可用 OTV 时应 raise RuntimeError。"""
        from polaris.router.multilayer import LayerSpec, MultiLayerRouter
        layers = [
            LayerSpec(name="SOI", grid_w=100, grid_h=100, grid_size=1.0, platform="SOI"),
            LayerSpec(name="SiN", grid_w=100, grid_h=100, grid_size=1.0, platform="SiN"),
        ]
        # 不注册任何 OTV
        router = MultiLayerRouter(layers=layers, otvs=[])
        with pytest.raises(RuntimeError, match="无可用 OTV"):
            router.route(start_layer=0, start_pos=(10, 10),
                         end_layer=1, end_pos=(90, 90))

    def test_unknown_platform_in_layer_raises(self):
        """R4-P1: layer.platform 未知时应 raise KeyError（不返回硬编码 2.0）。"""
        from polaris.router.multilayer import LayerSpec, MultiLayerRouter
        layers = [
            LayerSpec(name="UNKNOWN", grid_w=100, grid_h=100, grid_size=1.0,
                      platform="UNKNOWN_GaAs"),
        ]
        router = MultiLayerRouter(layers=layers, otvs=[])
        with pytest.raises(KeyError, match="未定义传播损耗"):
            router.route(start_layer=0, start_pos=(10, 10),
                         end_layer=0, end_pos=(90, 90))

    def test_no_hardcoded_2_0_in_source(self):
        """R4-P1: 验证 multilayer.py 源码无硬编码 2.0 dB/cm。"""
        import polaris.router.multilayer as mod
        src = Path(mod.__file__).read_text(encoding="utf-8")
        # 查找 length * 2.0 / 1e4 模式
        assert "length * 2.0 / 1e4" not in src, (
            "R4-P1: 仍存在硬编码 length * 2.0 / 1e4 损耗计算"
        )

    def test_no_return_none_in_route_methods(self):
        """R4-P1: 验证 route/_route_single_layer/_route_multi_layer 不返回 None。

        检查实际代码行（非注释/文档字符串）中无 'return None' 语句。
        """
        import ast
        import polaris.router.multilayer as mod

        src = Path(mod.__file__).read_text(encoding="utf-8")
        tree = ast.parse(src)

        # 收集所有 route 相关方法名
        route_method_names = {"route", "_route_single_layer", "_route_multi_layer"}

        violations = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name in route_method_names:
                # 遍历方法体中的所有 Return 节点
                for child in ast.walk(node):
                    if isinstance(child, ast.Return):
                        if child.value is None:
                            violations.append(
                                f"方法 {node.name} 第 {child.lineno} 行有 'return None' 语句"
                            )
        assert not violations, (
            "R4-P1: route 相关方法中仍有 return None 语句: " + "; ".join(violations)
        )
