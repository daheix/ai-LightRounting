"""P2-1 MEEP adjoint 后端集成测试（第34轮 P2-1 深化，第51轮删除 fall-back）。

验证 MEEP adjoint 后端接口、ImportError 报错机制、梯度计算。
MEEP 不可用时直接 raise ImportError（不降级，不 fall-back）。
若需解析模型，请直接使用 AnalyticalWaveguideCoupler 独立接口。

来源: commercial_gap_analysis.md P2-1 无逆向设计能力
对标: lumopt MEEP 集成 / Tidy3D adjoint
"""

from __future__ import annotations

import numpy as np
import pytest

from polaris.sim.shape_adjoint_optimizer import (
    ShapeAdjointConfig,
    AnalyticalWaveguideCoupler,
    OptimizationBackend,
    ShapeOptimizationResult,
    ParameterizedGeometry,
    run_adjoint_optimization,
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


def meep_is_available() -> bool:
    """检测 MEEP 是否可用（沙箱环境通常不可用）。"""
    return check_meep_availability() == MeepAvailability.AVAILABLE


class TestMeepAvailability:
    """MEEP 可用性枚举测试（第51轮：删除 FALLBACK，仅 2 种状态）。"""

    def test_available(self):
        """AVAILABLE 状态。"""
        assert MeepAvailability.AVAILABLE.value == "available"

    def test_unknown(self):
        """UNKNOWN 状态。"""
        assert MeepAvailability.UNKNOWN.value == "unknown"

    def test_availability_count(self):
        """2 种状态（第51轮删除 FALLBACK）。"""
        assert len(MeepAvailability) == 2

    def test_no_fallback_value(self):
        """第51轮：FALLBACK 已删除，不存在降级状态。"""
        assert not hasattr(MeepAvailability, "FALLBACK")


class TestCheckMeepAvailability:
    """MEEP 可用性检测测试。"""

    def test_check_returns_availability(self):
        """检测函数返回 MeepAvailability。"""
        status = check_meep_availability()
        assert isinstance(status, MeepAvailability)

    def test_check_returns_available_or_unknown(self):
        """沙箱环境通常返回 UNKNOWN（无 MEEP，不降级）。"""
        status = check_meep_availability()
        assert status in (MeepAvailability.AVAILABLE, MeepAvailability.UNKNOWN)


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


class TestMeepAdjointBackendNoFallback:
    """第51轮：MEEP 不可用时直接 raise ImportError（不降级）。"""

    def test_backend_creation_raises_without_meep(self):
        """MEEP 不可用时 MeepAdjointBackend() 直接 raise ImportError。"""
        if meep_is_available():
            pytest.skip("MEEP 已安装，跳过不可用测试")
        with pytest.raises(ImportError, match="MEEP 后端不可用"):
            MeepAdjointBackend()

    def test_backend_creation_no_fallback_param(self):
        """第51轮：__init__ 不再接受 fallback_simulator 参数。"""
        import inspect

        sig = inspect.signature(MeepAdjointBackend.__init__)
        assert "fallback_simulator" not in sig.parameters

    def test_create_meep_adjoint_backend_raises_without_meep(self):
        """工厂函数 MEEP 不可用时也 raise ImportError。"""
        if meep_is_available():
            pytest.skip("MEEP 已安装，跳过不可用测试")
        with pytest.raises(ImportError, match="MEEP 后端不可用"):
            create_meep_adjoint_backend()

    def test_no_fallback_attribute(self):
        """第51轮：MeepAdjointBackend 不再有 _fallback 属性。

        MEEP 可用时实例化成功，验证无 _fallback 属性。
        """
        if not meep_is_available():
            pytest.skip("MEEP 未安装，跳过可用测试")
        backend = MeepAdjointBackend()
        assert not hasattr(backend, "_fallback")

    def test_backend_used_always_meep(self):
        """第51轮：backend_used 始终为 MEEP（不降级为 ANALYTICAL）。"""
        if not meep_is_available():
            pytest.skip("MEEP 未安装，跳过可用测试")
        backend = MeepAdjointBackend()
        assert backend.backend_used == OptimizationBackend.MEEP


class TestFactoryFunctions:
    """工厂函数测试。"""

    def test_create_meep_adjoint_backend_raises_without_meep(self):
        """MEEP 不可时工厂函数 raise ImportError。"""
        if meep_is_available():
            pytest.skip("MEEP 已安装，跳过不可用测试")
        with pytest.raises(ImportError):
            create_meep_adjoint_backend()

    def test_get_meep_status_no_fallback_reason(self):
        """第51轮：状态字典不再包含 fallback_reason 字段。"""
        status = get_meep_status()
        assert "availability" in status
        assert "backend" in status
        assert "fallback_reason" not in status
        assert status["availability"] in ("available", "unknown")

    def test_get_meep_status_unknown(self):
        """MEEP 不可用时状态为 unknown（非 fallback）。"""
        status = get_meep_status()
        if status["availability"] == "unknown":
            assert status["version"] is None
            assert status["backend"] is None


class TestRunMeepAdjointOptimization:
    """MEEP adjoint 优化集成测试。"""

    def test_optimization_raises_without_meep(self):
        """MEEP 不可时 run_meep_adjoint_optimization raise ImportError。"""
        if meep_is_available():
            pytest.skip("MEEP 已安装，跳过不可用测试")
        geometry = ParameterizedGeometry(
            initial_params=np.array([5.0, 1.0]),
            bounds=[(1.0, 20.0), (0.1, 3.0)],
        )
        with pytest.raises(ImportError, match="MEEP 后端不可用"):
            run_meep_adjoint_optimization(geometry)


class TestAnalyticalBackendIsIndependent:
    """第51轮：AnalyticalWaveguideCoupler 是独立接口，非 fall-back。"""

    def test_analytical_backend_works_independently(self):
        """AnalyticalWaveguideCoupler 可独立使用，无需 MEEP。"""
        backend = AnalyticalWaveguideCoupler(
            target_wavelength_um=1.55, coupling_coefficient=0.2
        )
        params = np.array([10.0, 1.0])
        fom = backend.compute_figure_of_merit(params)
        grad = backend.compute_gradient(params)
        assert isinstance(fom, float)
        assert len(grad) == 2

    def test_analytical_optimization_via_run_adjoint(self):
        """解析优化通过 run_adjoint_optimization 独立调用（非 MEEP 后端）。"""
        geometry = ParameterizedGeometry(
            initial_params=np.array([8.0, 1.5]),
            bounds=[(1.0, 20.0), (0.1, 3.0)],
        )
        backend = AnalyticalWaveguideCoupler()
        config = ShapeAdjointConfig(
            max_iterations=5,
            learning_rate=0.1,
            backend=OptimizationBackend.ANALYTICAL,
        )
        result = run_adjoint_optimization(geometry, backend, config)
        assert isinstance(result, ShapeOptimizationResult)
        assert result.iterations > 0
        assert isinstance(result.optimal_fom, float)


class TestCommercialGapReduction:
    """P2-1 商业差距缩减验证。"""

    def test_meep_backend_interface_ready(self):
        """MEEP 后端接口就绪（接口定义存在，MEEP 可用时实例化）。"""
        assert hasattr(MeepAdjointBackend, "compute_figure_of_merit")
        assert hasattr(MeepAdjointBackend, "compute_gradient")

    def test_aligned_with_lumopt_interface(self):
        """接口对齐 lumopt ForwardSimulator 协议。"""
        assert callable(MeepAdjointBackend.compute_figure_of_merit)
        assert callable(MeepAdjointBackend.compute_gradient)

    def test_simulation_config_aligned_with_meep_defaults(self):
        """仿真配置对齐 MEEP 默认值。"""
        cfg = MeepSimulationConfig()
        # MEEP 默认 PML 1.0μm
        assert cfg.pml_thickness_um == 1.0
        # 光通信波段 1.55μm
        assert cfg.wavelength_um == 1.55
        # lumopt 推荐 resolution 20-30
        assert 20.0 <= cfg.resolution <= 50.0

    def test_analytical_gradient_correctness_vs_finite_difference(self):
        """解析梯度正确性验证（vs 有限差分，独立接口）。"""
        backend = AnalyticalWaveguideCoupler()
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
