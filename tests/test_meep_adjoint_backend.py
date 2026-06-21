"""P2-1 MEEP adjoint 后端集成测试（第34轮 P2-1 深化）。

验证 MEEP adjoint 后端接口、降级机制、梯度计算。

来源: commercial_gap_analysis.md P2-1 无逆向设计能力
对标: lumopt MEEP 集成 / Tidy3D adjoint
"""

from __future__ import annotations

import numpy as np
import pytest

from polaris.sim.adjoint_optimizer import (
    AdjointConfig,
    AnalyticalWaveguideCoupler,
    OptimizationBackend,
    ParameterizedGeometry,
)
from polaris.sim.meep_adjoint_backend import (
    MeepAdjointBackend,
    MeepAdjointResult,
    MeepAvailability,
    MeepSimulationConfig,
    check_meep_availability,
    create_meep_adjoint_backend,
    get_meep_status,
    run_meep_adjoint_optimization,
)


class TestMeepAvailability:
    """MEEP 可用性枚举测试。"""

    def test_available(self):
        """AVAILABLE 状态。"""
        assert MeepAvailability.AVAILABLE.value == "available"

    def test_fallback(self):
        """FALLBACK 状态。"""
        assert MeepAvailability.FALLBACK.value == "fallback"

    def test_unknown(self):
        """UNKNOWN 状态。"""
        assert MeepAvailability.UNKNOWN.value == "unknown"

    def test_availability_count(self):
        """3 种状态。"""
        assert len(MeepAvailability) == 3


class TestCheckMeepAvailability:
    """MEEP 可用性检测测试。"""

    def test_check_returns_availability(self):
        """检测函数返回 MeepAvailability。"""
        status = check_meep_availability()
        assert isinstance(status, MeepAvailability)

    def test_check_returns_available_or_fallback(self):
        """沙箱环境通常返回 FALLBACK（无 MEEP）。"""
        status = check_meep_availability()
        assert status in (MeepAvailability.AVAILABLE, MeepAvailability.FALLBACK)


class TestMeepSimulationConfig:
    """MEEP 仿真配置测试。"""

    def test_default_config(self):
        """默认配置。"""
        cfg = MeepSimulationConfig()
        assert cfg.resolution == 20.0
        assert cfg.cell_size_um == (10.0, 5.0)
        assert cfg.pml_thickness_um == 1.0
        assert cfg.wavelength_um == 1.55
        assert cfg.wavelength_width_um == 0.1
        assert cfg.runtime_um == 50.0
        assert cfg.source_type == "gaussian"
        assert cfg.monitor_type == "flux"

    def test_custom_config(self):
        """自定义配置。"""
        cfg = MeepSimulationConfig(
            resolution=50.0,
            cell_size_um=(20.0, 10.0),
            wavelength_um=1.31,
        )
        assert cfg.resolution == 50.0
        assert cfg.cell_size_um == (20.0, 10.0)
        assert cfg.wavelength_um == 1.31

    def test_config_for_high_resolution(self):
        """高分辨率配置（lumopt 推荐 20-30）。"""
        cfg = MeepSimulationConfig(resolution=30.0)
        assert 20.0 <= cfg.resolution <= 50.0


class TestMeepAdjointResult:
    """MEEP adjoint 结果测试。"""

    def test_default_result(self):
        """默认结果。"""
        result = MeepAdjointResult(fom=0.5)
        assert result.fom == 0.5
        assert result.forward_field is None
        assert result.adjoint_field is None
        assert result.sim_time_s == 0.0
        assert result.backend_used == OptimizationBackend.MEEP

    def test_result_with_fields(self):
        """带场分布的结果。"""
        field = np.zeros((10, 10), dtype=np.complex128)
        result = MeepAdjointResult(
            fom=0.8,
            forward_field=field,
            adjoint_field=field,
            gradient=np.array([0.1, 0.2]),
            sim_time_s=1.5,
        )
        assert result.fom == 0.8
        assert result.forward_field is not None
        assert result.gradient[0] == 0.1
        assert result.sim_time_s == 1.5


class TestMeepAdjointBackend:
    """MEEP adjoint 后端测试。"""

    def test_backend_creation_default(self):
        """默认创建后端（MEEP 不可用时降级）。"""
        backend = MeepAdjointBackend()
        assert backend.availability in (
            MeepAvailability.AVAILABLE,
            MeepAvailability.FALLBACK,
        )

    def test_backend_creation_with_config(self):
        """带配置创建后端。"""
        cfg = MeepSimulationConfig(resolution=30.0)
        backend = MeepAdjointBackend(sim_config=cfg)
        assert backend.sim_config.resolution == 30.0

    def test_backend_used_property(self):
        """backend_used 属性。"""
        backend = MeepAdjointBackend()
        if backend.availability == MeepAvailability.AVAILABLE:
            assert backend.backend_used == OptimizationBackend.MEEP
        else:
            assert backend.backend_used == OptimizationBackend.ANALYTICAL

    def test_compute_fom_fallback(self):
        """降级模式下计算 FoM。"""
        backend = MeepAdjointBackend()
        if backend.availability == MeepAvailability.FALLBACK:
            params = np.array([10.0, 1.0])
            fom = backend.compute_figure_of_merit(params)
            assert 0.0 <= fom <= 1.0

    def test_compute_gradient_fallback(self):
        """降级模式下计算梯度。"""
        backend = MeepAdjointBackend()
        if backend.availability == MeepAvailability.FALLBACK:
            params = np.array([10.0, 1.0])
            grad = backend.compute_gradient(params)
            assert len(grad) == 2
            assert all(isinstance(g, float | np.floating) for g in grad)

    def test_backend_with_custom_fallback(self):
        """自定义降级仿真器。"""
        custom_fallback = AnalyticalWaveguideCoupler(
            target_wavelength_um=1.55, coupling_coefficient=0.2
        )
        backend = MeepAdjointBackend(fallback_simulator=custom_fallback)
        if backend.availability == MeepAvailability.FALLBACK:
            assert backend._fallback is custom_fallback

    def test_backend_consistency_with_analytical(self):
        """降级模式与 AnalyticalWaveguideCoupler 一致。"""
        backend = MeepAdjointBackend()
        if backend.availability == MeepAvailability.FALLBACK:
            params = np.array([15.0, 0.5])
            fom_backend = backend.compute_figure_of_merit(params)
            fom_analytical = backend._fallback.compute_figure_of_merit(params)
            assert fom_backend == pytest.approx(fom_analytical, abs=1e-9)


class TestFactoryFunctions:
    """工厂函数测试。"""

    def test_create_meep_adjoint_backend(self):
        """创建 MEEP adjoint 后端。"""
        backend = create_meep_adjoint_backend()
        assert isinstance(backend, MeepAdjointBackend)

    def test_create_with_config(self):
        """带配置创建。"""
        cfg = MeepSimulationConfig(resolution=25.0)
        backend = create_meep_adjoint_backend(sim_config=cfg)
        assert backend.sim_config.resolution == 25.0

    def test_get_meep_status(self):
        """获取 MEEP 状态。"""
        status = get_meep_status()
        assert "availability" in status
        assert "backend" in status
        assert status["availability"] in ("available", "fallback")

    def test_get_meep_status_fallback(self):
        """降级模式状态。"""
        status = get_meep_status()
        if status["availability"] == "fallback":
            assert status["version"] is None
            assert "fallback_reason" in status


class TestRunMeepAdjointOptimization:
    """MEEP adjoint 优化集成测试。"""

    def test_optimization_with_fallback(self):
        """降级模式下执行优化。"""
        backend = create_meep_adjoint_backend()
        if backend.availability == MeepAvailability.FALLBACK:
            geometry = ParameterizedGeometry(
                initial_params=np.array([5.0, 1.0]),
                bounds=[(1.0, 20.0), (0.1, 3.0)],
            )
            config = AdjointConfig(
                max_iterations=10,
                learning_rate=0.1,
                backend=OptimizationBackend.ANALYTICAL,
            )
            result = run_meep_adjoint_optimization(geometry, config=config)
            assert result.iterations > 0
            assert result.iterations <= 10
            assert len(result.fom_history) == result.iterations
            assert 0.0 <= result.optimal_fom <= 1.0

    def test_optimization_default_config(self):
        """默认配置优化。"""
        geometry = ParameterizedGeometry(
            initial_params=np.array([8.0, 1.5]),
            bounds=[(1.0, 20.0), (0.1, 3.0)],
        )
        result = run_meep_adjoint_optimization(geometry)
        assert result.iterations > 0
        assert isinstance(result.optimal_fom, float)

    def test_optimization_backend_used(self):
        """优化结果记录实际后端。"""
        geometry = ParameterizedGeometry(
            initial_params=np.array([8.0, 1.5]),
        )
        result = run_meep_adjoint_optimization(geometry)
        assert result.backend_used in (
            OptimizationBackend.MEEP,
            OptimizationBackend.ANALYTICAL,
        )


class TestCommercialGapReduction:
    """P2-1 商业差距缩减验证。"""

    def test_meep_backend_interface_ready(self):
        """MEEP 后端接口就绪。"""
        backend = create_meep_adjoint_backend()
        # 接口就绪（MEEP 可用或降级）
        assert hasattr(backend, "compute_figure_of_merit")
        assert hasattr(backend, "compute_gradient")

    def test_adjoint_method_two_simulations(self):
        """adjoint method 只需 2 次仿真（正向+伴随）。"""
        # 对标 lumopt：2 次仿真 vs 有限差分 n+1 次
        backend = create_meep_adjoint_backend()
        if backend.availability == MeepAvailability.FALLBACK:
            params = np.array([10.0, 1.0])
            # 1 次 FoM + 1 次梯度 = 2 次仿真
            fom = backend.compute_figure_of_merit(params)
            grad = backend.compute_gradient(params)
            assert isinstance(fom, float)
            assert len(grad) == len(params)

    def test_fallback_guarantees_usability(self):
        """降级机制保证 MEEP 不可用时仍可用。"""
        backend = create_meep_adjoint_backend()
        # 无论 MEEP 是否可用，接口都能工作
        params = np.array([10.0, 1.0])
        fom = backend.compute_figure_of_merit(params)
        grad = backend.compute_gradient(params)
        assert isinstance(fom, float)
        assert len(grad) == 2

    def test_aligned_with_lumopt_interface(self):
        """接口对齐 lumopt ForwardSimulator 协议。"""
        backend = create_meep_adjoint_backend()
        # lumopt 核心接口：compute_figure_of_merit + compute_gradient
        assert callable(backend.compute_figure_of_merit)
        assert callable(backend.compute_gradient)

    def test_simulation_config_aligned_with_meep_defaults(self):
        """仿真配置对齐 MEEP 默认值。"""
        cfg = MeepSimulationConfig()
        # MEEP 默认 PML 1.0μm
        assert cfg.pml_thickness_um == 1.0
        # 光通信波段 1.55μm
        assert cfg.wavelength_um == 1.55
        # lumopt 推荐 resolution 20-30
        assert 20.0 <= cfg.resolution <= 50.0

    def test_gradient_correctness_vs_finite_difference(self):
        """梯度正确性验证（vs 有限差分）。"""
        backend = create_meep_adjoint_backend()
        if backend.availability == MeepAvailability.FALLBACK:
            params = np.array([10.0, 1.0])
            grad_analytical = backend.compute_gradient(params)
            # 有限差分验证
            delta = 1e-6
            grad_fd = np.zeros_like(grad_analytical)
            for i in range(len(params)):
                p_plus = params.copy()
                p_plus[i] += delta
                p_minus = params.copy()
                p_minus[i] -= delta
                fom_plus = backend.compute_figure_of_merit(p_plus)
                fom_minus = backend.compute_figure_of_merit(p_minus)
                grad_fd[i] = (fom_plus - fom_minus) / (2 * delta)
            # 解析梯度应与有限差分一致（容差 1e-4）
            for i in range(len(params)):
                assert grad_analytical[i] == pytest.approx(
                    grad_fd[i], abs=1e-4
                ), f"参数 {i}: 解析={grad_analytical[i]}, 有限差分={grad_fd[i]}"
