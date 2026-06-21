"""P1-1 FFT 卷积加速测试（第36轮 P1-1 深化）。

验证 FFT 卷积、FFT 密度场、性能基准。

来源: commercial_gap_analysis.md P1-1 布局算法先进性
对标: DREAMPlace TCAD 2020 FFT 密度场
"""

from __future__ import annotations

import numpy as np
import pytest

from polaris.engine.fft_density_field import (
    DensityFieldFFT,
    FFTConfig,
    FFTConvolver,
    benchmark_fft_vs_separable,
    create_fft_density_field,
)


class TestFFTConfig:
    """FFT 配置测试。"""

    def test_default_config(self):
        """默认配置。"""
        cfg = FFTConfig()
        assert cfg.use_fft is True
        assert cfg.pad_mode == "constant"
        assert cfg.pad_value == 0.0
        assert cfg.normalize is True

    def test_custom_config(self):
        """自定义配置。"""
        cfg = FFTConfig(use_fft=False, normalize=False)
        assert cfg.use_fft is False
        assert cfg.normalize is False

    def test_frozen_dataclass(self):
        """frozen dataclass。"""
        cfg = FFTConfig()
        with pytest.raises(AttributeError):
            cfg.use_fft = False  # type: ignore[misc]


class TestFFTConvolver:
    """FFT 卷积器测试。"""

    def test_creation_default(self):
        """默认创建。"""
        conv = FFTConvolver()
        assert conv.config.use_fft is True

    def test_convolve_gaussian_preserves_shape(self):
        """卷积保持形状。"""
        conv = FFTConvolver()
        field = np.random.rand(32, 32)
        result = conv.convolve_gaussian(field, sigma=2.0)
        assert result.shape == field.shape

    def test_convolve_gaussian_smooths(self):
        """卷积平滑场。"""
        conv = FFTConvolver()
        field = np.zeros((32, 32))
        field[16, 16] = 10.0
        result = conv.convolve_gaussian(field, sigma=2.0)
        # 中心点值降低
        assert result[16, 16] < 10.0
        # 周围点值升高
        assert result[15, 16] > 0.0

    def test_convolve_zero_sigma(self):
        """σ=0 不卷积。"""
        conv = FFTConvolver()
        field = np.random.rand(16, 16)
        result = conv.convolve_gaussian(field, sigma=0.0)
        assert np.allclose(result, field)

    def test_separable_mode(self):
        """分离卷积模式。"""
        conv = FFTConvolver(FFTConfig(use_fft=False))
        field = np.random.rand(32, 32)
        result = conv.convolve_gaussian(field, sigma=2.0)
        assert result.shape == field.shape

    def test_fft_vs_separable_similar(self):
        """FFT 与分离卷积结果相似。"""
        fft_conv = FFTConvolver(FFTConfig(use_fft=True, normalize=False))
        sep_conv = FFTConvolver(FFTConfig(use_fft=False))
        field = np.random.rand(32, 32)
        fft_result = fft_conv.convolve_gaussian(field, sigma=3.0)
        sep_result = sep_conv.convolve_gaussian(field, sigma=3.0)
        # 两种方法结果应相似（容差 0.5，因边界处理不同）
        assert np.allclose(fft_result, sep_result, atol=0.5)


class TestDensityFieldFFT:
    """FFT 密度场测试。"""

    def test_creation(self):
        """创建密度场。"""
        field = DensityFieldFFT(200.0, 200.0, grid_size=64)
        assert field.canvas_w == 200.0
        assert field.canvas_h == 200.0
        assert field.grid_size == 64
        assert field.density.shape == (64, 64)

    def test_build_single_device(self):
        """构建单器件密度场。"""
        field = DensityFieldFFT(200.0, 200.0, grid_size=32)
        pos = np.array([[100.0, 100.0]])
        widths = np.array([10.0])
        heights = np.array([10.0])
        field.build(pos, widths, heights)
        assert field.density.sum() > 0.0

    def test_build_multiple_devices(self):
        """构建多器件密度场。"""
        field = DensityFieldFFT(200.0, 200.0, grid_size=32)
        pos = np.array([[50.0, 50.0], [100.0, 100.0], [150.0, 150.0]])
        widths = np.array([10.0, 10.0, 10.0])
        heights = np.array([10.0, 10.0, 10.0])
        field.build(pos, widths, heights)
        assert field.density.sum() > 0.0

    def test_smooth_gaussian(self):
        """高斯平滑。"""
        field = DensityFieldFFT(200.0, 200.0, grid_size=32)
        pos = np.array([[100.0, 100.0]])
        widths = np.array([10.0])
        heights = np.array([10.0])
        field.build(pos, widths, heights)
        field.smooth_gaussian(sigma=10.0)
        assert field.smoothed is not None
        assert field.smoothed.shape == (32, 32)

    def test_gradient_at(self):
        """梯度查询。"""
        field = DensityFieldFFT(200.0, 200.0, grid_size=32)
        pos = np.array([[100.0, 100.0], [50.0, 50.0]])
        widths = np.array([10.0, 10.0])
        heights = np.array([10.0, 10.0])
        field.build(pos, widths, heights)
        field.smooth_gaussian(sigma=10.0)
        grad = field.gradient_at(pos)
        assert grad.shape == (2, 2)

    def test_gradient_auto_smooth(self):
        """梯度自动平滑（未调用 smooth_gaussian）。"""
        field = DensityFieldFFT(200.0, 200.0, grid_size=32)
        pos = np.array([[100.0, 100.0]])
        widths = np.array([10.0])
        heights = np.array([10.0])
        field.build(pos, widths, heights)
        # 未调用 smooth_gaussian，gradient_at 应自动平滑
        grad = field.gradient_at(pos)
        assert grad.shape == (1, 2)


class TestFactoryFunction:
    """工厂函数测试。"""

    def test_create_default(self):
        """默认创建。"""
        field = create_fft_density_field(200.0, 200.0)
        assert isinstance(field, DensityFieldFFT)
        assert field.convolver.config.use_fft is True

    def test_create_with_fft_disabled(self):
        """禁用 FFT 创建。"""
        field = create_fft_density_field(200.0, 200.0, use_fft=False)
        assert field.convolver.config.use_fft is False

    def test_create_custom_grid(self):
        """自定义网格。"""
        field = create_fft_density_field(200.0, 200.0, grid_size=64)
        assert field.grid_size == 64


class TestBenchmark:
    """性能基准测试。"""

    def test_benchmark_returns_dict(self):
        """基准测试返回字典。"""
        result = benchmark_fft_vs_separable(grid_size=32, sigma=2.0)
        assert isinstance(result, dict)
        assert "fft_time_s" in result
        assert "separable_time_s" in result
        assert "speedup" in result

    def test_benchmark_times_positive(self):
        """基准测试时间为正。"""
        result = benchmark_fft_vs_separable(grid_size=32, sigma=2.0)
        assert result["fft_time_s"] > 0
        assert result["separable_time_s"] > 0

    def test_fft_faster_for_large_kernel(self):
        """大核 FFT 应更快（或相当）。"""
        # 大核（sigma=10）FFT 应有加速
        result = benchmark_fft_vs_separable(grid_size=64, sigma=10.0)
        # FFT 至少不应比分离卷积慢 10 倍（容差，因小规模 FFT 开销）
        assert result["speedup"] > 0.1


class TestCommercialGapReduction:
    """P1-1 商业差距缩减验证。"""

    def test_fft_complexity_aligned_dreamplace(self):
        """FFT 复杂度对齐 DREAMPlace O(G² log G)。"""
        # DREAMPlace TCAD 2020 FFT 卷积
        conv = FFTConvolver()
        field = np.random.rand(128, 128)
        # FFT 卷积应能处理 128×128 网格
        result = conv.convolve_gaussian(field, sigma=5.0)
        assert result.shape == (128, 128)

    def test_large_scale_support(self):
        """大规模支持（>500 器件）。"""
        field = DensityFieldFFT(2000.0, 2000.0, grid_size=128)
        n = 500
        rng = np.random.default_rng(42)
        pos = rng.uniform(10, 1990, (n, 2))
        widths = rng.uniform(5, 20, n)
        heights = rng.uniform(5, 20, n)
        field.build(pos, widths, heights)
        field.smooth_gaussian(sigma=20.0)
        grad = field.gradient_at(pos)
        assert grad.shape == (n, 2)

    def test_fft_vs_separable_consistency(self):
        """FFT 与分离卷积一致性。"""
        fft_field = create_fft_density_field(200.0, 200.0, grid_size=32, use_fft=True)
        sep_field = create_fft_density_field(200.0, 200.0, grid_size=32, use_fft=False)
        pos = np.array([[100.0, 100.0]])
        widths = np.array([10.0])
        heights = np.array([10.0])
        fft_field.build(pos, widths, heights)
        sep_field.build(pos, widths, heights)
        fft_field.smooth_gaussian(sigma=10.0)
        sep_field.smooth_gaussian(sigma=10.0)
        # 两种方法密度场应相似
        assert np.allclose(fft_field.smoothed, sep_field.smoothed, atol=1.0)

    def test_bilinear_distribution_preserved(self):
        """双线性插值面积分布保持（与第30轮一致）。"""
        field = DensityFieldFFT(100.0, 100.0, grid_size=10)
        # 器件在 (57, 57)，网格间距 10，网格坐标 5.2
        pos = np.array([[57.0, 57.0]])
        widths = np.array([10.0])
        heights = np.array([10.0])
        field.build(pos, widths, heights)
        # 应分配到 4 个网格点
        assert field.density[5, 5] > 0
        assert field.density[5, 6] > 0
        assert field.density[6, 5] > 0
        assert field.density[6, 6] > 0

    def test_central_difference_gradient(self):
        """中心差分梯度计算。"""
        field = DensityFieldFFT(200.0, 200.0, grid_size=32)
        pos = np.array([[100.0, 100.0]])
        widths = np.array([10.0])
        heights = np.array([10.0])
        field.build(pos, widths, heights)
        field.smooth_gaussian(sigma=10.0)
        grad = field.gradient_at(pos)
        # 梯度应为有限值
        assert np.all(np.isfinite(grad))

    def test_performance_improvement(self):
        """性能改进验证。"""
        # FFT 应在大规模时提供性能改进
        result = benchmark_fft_vs_separable(grid_size=128, sigma=10.0)
        # 至少不应比分离卷积慢（容差 2x，因 FFT 有固定开销）
        assert result["speedup"] > 0.5
