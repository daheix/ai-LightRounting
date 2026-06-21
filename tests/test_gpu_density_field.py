"""GPU 加速密度场网格化测试（P1-1 深化，第45轮）。

对标 DREAMPlace TCAD 2020 GPU 加速密度场测试覆盖。

来源:
- DREAMPlace: https://arxiv.org/abs/2004.10746
"""

from __future__ import annotations

import unittest

import numpy as np

from polaris.engine.gpu_density_field import (
    GPUDensityConfig,
    GPUDensityField,
    create_gpu_density_field,
)


class TestGPUDensityConfig(unittest.TestCase):
    """GPUDensityConfig 测试。"""

    def test_defaults(self) -> None:
        """测试默认值。"""
        cfg = GPUDensityConfig()
        self.assertEqual(cfg.grid_size, 64)
        self.assertEqual(cfg.gaussian_sigma, 10.0)
        self.assertTrue(cfg.use_fft)

    def test_custom(self) -> None:
        """测试自定义配置。"""
        cfg = GPUDensityConfig(grid_size=128, gaussian_sigma=5.0, use_fft=False)
        self.assertEqual(cfg.grid_size, 128)
        self.assertEqual(cfg.gaussian_sigma, 5.0)
        self.assertFalse(cfg.use_fft)


class TestGPUDensityFieldInit(unittest.TestCase):
    """GPUDensityField 初始化测试。"""

    def test_default_init(self) -> None:
        """测试默认初始化。"""
        df = GPUDensityField()
        self.assertEqual(df.grid_size, 64)
        self.assertEqual(df.field.shape, (64, 64))
        # 沙箱无 GPU，应降级到 CPU
        self.assertFalse(df.is_gpu)

    def test_force_cpu(self) -> None:
        """测试强制 CPU 模式。"""
        cfg = GPUDensityConfig(force_cpu=True)
        df = GPUDensityField(cfg)
        self.assertFalse(df.is_gpu)

    def test_custom_grid_size(self) -> None:
        """测试自定义网格大小。"""
        cfg = GPUDensityConfig(grid_size=32)
        df = GPUDensityField(cfg)
        self.assertEqual(df.grid_size, 32)
        self.assertEqual(df.field.shape, (32, 32))


class TestBuild(unittest.TestCase):
    """build 方法测试。"""

    def test_empty_devices(self) -> None:
        """测试空器件列表。"""
        df = GPUDensityField()
        pos = np.zeros((0, 2))
        widths = np.zeros(0)
        heights = np.zeros(0)
        bin_x = np.linspace(0, 1, 65)
        bin_y = np.linspace(0, 1, 65)
        field = df.build(pos, widths, heights, bin_x, bin_y)
        self.assertEqual(field.shape, (64, 64))
        self.assertEqual(field.sum(), 0.0)

    def test_single_device(self) -> None:
        """测试单器件。"""
        df = GPUDensityField()
        pos = np.array([[0.5, 0.5]])
        widths = np.array([0.1])
        heights = np.array([0.1])
        bin_x = np.linspace(0, 1, 65)
        bin_y = np.linspace(0, 1, 65)
        field = df.build(pos, widths, heights, bin_x, bin_y)
        self.assertEqual(field.shape, (64, 64))
        # 应有非零密度
        self.assertGreater(field.sum(), 0)

    def test_multiple_devices(self) -> None:
        """测试多器件。"""
        df = GPUDensityField()
        rng = np.random.default_rng(42)
        n = 50
        pos = rng.random((n, 2))
        widths = rng.random(n) * 0.05
        heights = rng.random(n) * 0.05
        bin_x = np.linspace(0, 1, 65)
        bin_y = np.linspace(0, 1, 65)
        field = df.build(pos, widths, heights, bin_x, bin_y)
        self.assertEqual(field.shape, (64, 64))
        self.assertGreater(field.sum(), 0)

    def test_shape_preservation(self) -> None:
        """测试形状保持。"""
        cfg = GPUDensityConfig(grid_size=32)
        df = GPUDensityField(cfg)
        pos = np.array([[0.5, 0.5]])
        widths = np.array([0.1])
        heights = np.array([0.1])
        bin_x = np.linspace(0, 1, 33)
        bin_y = np.linspace(0, 1, 33)
        field = df.build(pos, widths, heights, bin_x, bin_y)
        self.assertEqual(field.shape, (32, 32))


class TestSmoothGaussian(unittest.TestCase):
    """smooth_gaussian 方法测试。"""

    def test_zero_sigma_no_change(self) -> None:
        """测试零 sigma 不平滑。"""
        df = GPUDensityField()
        df.field = np.zeros((64, 64))
        df.field[32, 32] = 1.0
        original = df.field.copy()
        result = df.smooth_gaussian(sigma=0)
        np.testing.assert_array_equal(result, original)

    def test_fft_smooth(self) -> None:
        """测试 FFT 平滑。"""
        cfg = GPUDensityConfig(use_fft=True)
        df = GPUDensityField(cfg)
        df.field = np.zeros((64, 64))
        df.field[32, 32] = 1.0
        result = df.smooth_gaussian(sigma=3.0)
        # 平滑后峰值应降低
        self.assertLess(result.max(), 1.0)
        # 总密度应基本保持
        self.assertAlmostEqual(result.sum(), 1.0, places=2)

    def test_separable_smooth(self) -> None:
        """测试分离卷积平滑。"""
        cfg = GPUDensityConfig(use_fft=False)
        df = GPUDensityField(cfg)
        df.field = np.zeros((64, 64))
        df.field[32, 32] = 1.0
        result = df.smooth_gaussian(sigma=3.0)
        self.assertLess(result.max(), 1.0)


class TestGradientAt(unittest.TestCase):
    """gradient_at 方法测试。"""

    def test_empty_query(self) -> None:
        """测试空查询。"""
        df = GPUDensityField()
        result = df.gradient_at(np.zeros((0, 2)))
        self.assertEqual(result.shape, (0, 2))

    def test_single_query(self) -> None:
        """测试单点查询。"""
        df = GPUDensityField()
        df.field = np.zeros((64, 64))
        df.field[32, 32] = 1.0
        result = df.gradient_at(np.array([[0.5, 0.5]]))
        self.assertEqual(result.shape, (1, 2))

    def test_multiple_queries(self) -> None:
        """测试多点查询。"""
        df = GPUDensityField()
        df.field = np.zeros((64, 64))
        df.field[32, 32] = 1.0
        pos = np.array([[0.5, 0.5], [0.3, 0.7], [0.8, 0.2]])
        result = df.gradient_at(pos)
        self.assertEqual(result.shape, (3, 2))

    def test_gradient_direction(self) -> None:
        """测试梯度方向。

        线性密度场（x 方向递增），梯度 x 应为正。
        """
        df = GPUDensityField()
        # 创建 x 方向线性递增的密度场
        for i in range(64):
            df.field[:, i] = float(i) / 63.0
        # 在非中心点查询（避免恰好在网格中心梯度为 0）
        result = df.gradient_at(np.array([[0.3, 0.5]]))
        self.assertGreater(result[0, 0], 0)


class TestDensityMetrics(unittest.TestCase):
    """密度指标测试。"""

    def test_total_density(self) -> None:
        """测试总密度。"""
        df = GPUDensityField()
        df.field = np.ones((64, 64)) * 0.5
        self.assertAlmostEqual(df.total_density(), 0.5 * 64 * 64)

    def test_max_density(self) -> None:
        """测试最大密度。"""
        df = GPUDensityField()
        df.field = np.zeros((64, 64))
        df.field[0, 0] = 2.0
        self.assertAlmostEqual(df.max_density(), 2.0)


class TestFactoryFunction(unittest.TestCase):
    """工厂函数测试。"""

    def test_create_default(self) -> None:
        """测试默认创建。"""
        df = create_gpu_density_field()
        self.assertEqual(df.grid_size, 64)

    def test_create_custom(self) -> None:
        """测试自定义创建。"""
        df = create_gpu_density_field(grid_size=32, sigma=5.0, use_fft=False)
        self.assertEqual(df.grid_size, 32)


class TestCommercialGapReduction(unittest.TestCase):
    """商业差距缩减测试（对标 DREAMPlace）。"""

    def test_fft_vs_separable_consistency(self) -> None:
        """测试 FFT 与分离卷积结果一致性。

        对标 DREAMPlace 的 FFT 加速正确性。
        """
        rng = np.random.default_rng(42)
        field_data = rng.random((32, 32))

        # FFT 版
        df_fft = GPUDensityField(GPUDensityConfig(grid_size=32, use_fft=True))
        df_fft.field = field_data.copy()
        result_fft = df_fft.smooth_gaussian(sigma=3.0)

        # 分离卷积版
        df_sep = GPUDensityField(GPUDensityConfig(grid_size=32, use_fft=False))
        df_sep.field = field_data.copy()
        result_sep = df_sep.smooth_gaussian(sigma=3.0)

        # 两者应基本一致（允许 FFT 数值误差）
        np.testing.assert_array_almost_equal(result_fft, result_sep, decimal=1)

    def test_vectorized_build_correctness(self) -> None:
        """测试向量化 build 正确性。

        对标 DREAMPlace 的双线性插值面积分布。
        """
        df = GPUDensityField(GPUDensityConfig(grid_size=16))
        pos = np.array([[0.5, 0.5], [0.25, 0.75]])
        widths = np.array([0.1, 0.2])
        heights = np.array([0.1, 0.2])
        bin_x = np.linspace(0, 1, 17)
        bin_y = np.linspace(0, 1, 17)
        field = df.build(pos, widths, heights, bin_x, bin_y)

        # 总密度应等于总面积 / bin 面积
        total_area = (0.1 * 0.1) + (0.2 * 0.2)
        bin_area = (1.0 / 16) ** 2
        expected_total = total_area / bin_area
        self.assertAlmostEqual(field.sum(), expected_total, places=5)

    def test_gpu_cpu_fallback(self) -> None:
        """测试 GPU/CPU 自动降级。

        对标 DREAMPlace 的 GPU/CPU 双模式。
        """
        # 沙箱无 GPU，应自动降级到 CPU
        df = GPUDensityField()
        self.assertFalse(df.is_gpu)
        # 应能正常工作
        pos = np.array([[0.5, 0.5]])
        widths = np.array([0.1])
        heights = np.array([0.1])
        bin_x = np.linspace(0, 1, 65)
        bin_y = np.linspace(0, 1, 65)
        field = df.build(pos, widths, heights, bin_x, bin_y)
        self.assertGreater(field.sum(), 0)

    def test_large_scale_build(self) -> None:
        """测试大规模器件布局。

        对标 DREAMPlace 的 1000 器件规模。
        """
        df = GPUDensityField(GPUDensityConfig(grid_size=128))
        rng = np.random.default_rng(42)
        n = 1000
        pos = rng.random((n, 2))
        widths = rng.random(n) * 0.02
        heights = rng.random(n) * 0.02
        bin_x = np.linspace(0, 1, 129)
        bin_y = np.linspace(0, 1, 129)
        field = df.build(pos, widths, heights, bin_x, bin_y)
        self.assertEqual(field.shape, (128, 128))
        self.assertGreater(field.sum(), 0)

    def test_full_pipeline(self) -> None:
        """测试完整流水线：build → smooth → gradient。

        对标 DREAMPlace 的完整密度场管线。
        """
        df = GPUDensityField(GPUDensityConfig(grid_size=64, use_fft=True))
        rng = np.random.default_rng(42)
        n = 100
        pos = rng.random((n, 2))
        widths = rng.random(n) * 0.05
        heights = rng.random(n) * 0.05
        bin_x = np.linspace(0, 1, 65)
        bin_y = np.linspace(0, 1, 65)

        # 1. build
        field = df.build(pos, widths, heights, bin_x, bin_y)
        self.assertGreater(field.sum(), 0)

        # 2. smooth
        smoothed = df.smooth_gaussian(sigma=5.0)
        self.assertEqual(smoothed.shape, (64, 64))

        # 3. gradient
        grads = df.gradient_at(pos)
        self.assertEqual(grads.shape, (100, 2))

        # 应全部有限
        self.assertTrue(np.all(np.isfinite(grads)))

    def test_benchmark(self) -> None:
        """测试基准测试功能。

        对标 DREAMPlace 的性能基准。
        """
        df = GPUDensityField(GPUDensityConfig(grid_size=32))
        result = df.benchmark(n_devices=50)
        self.assertIn("build_time", result)
        self.assertIn("smooth_time", result)
        self.assertIn("gradient_time", result)
        self.assertIn("total_time", result)
        self.assertGreater(result["total_time"], 0)
        self.assertFalse(result["is_gpu"])  # 沙箱无 GPU


if __name__ == "__main__":
    unittest.main()
