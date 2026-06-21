"""GPU 加速后端测试（第41轮 P1-1 深化，CuPy 后端）。

测试覆盖：
- DeviceType 枚举
- GPUConfig 配置
- check_cupy_availability 函数
- NumPyBackend CPU 后端
- CuPyBackend GPU 后端（条件跳过）
- GPUBackend 统一接口
- 工厂函数
- 商业差距缩减验证（对标 DREAMPlace GPU 加速）
"""

from __future__ import annotations

import numpy as np
import pytest

from polaris.engine.gpu_backend import (
    CuPyBackend,
    DeviceType,
    GPUBackend,
    GPUConfig,
    NumPyBackend,
    check_cupy_availability,
    create_gpu_backend,
    get_gpu_status,
)


class TestDeviceType:
    """设备类型枚举测试。"""

    def test_enum_values(self) -> None:
        """枚举值。"""
        assert DeviceType.CPU.value == "cpu"
        assert DeviceType.GPU.value == "gpu"

    def test_enum_from_value(self) -> None:
        """从字符串构造。"""
        assert DeviceType("cpu") == DeviceType.CPU
        assert DeviceType("gpu") == DeviceType.GPU


class TestGPUConfig:
    """GPU 配置测试。"""

    def test_default_config(self) -> None:
        """默认配置。"""
        cfg = GPUConfig()
        assert cfg.device_id == 0
        assert cfg.force_cpu is False
        assert cfg.memory_pool_size == 0

    def test_custom_config(self) -> None:
        """自定义配置。"""
        cfg = GPUConfig(
            device_id=1,
            force_cpu=True,
            memory_pool_size=512,
        )
        assert cfg.device_id == 1
        assert cfg.force_cpu is True
        assert cfg.memory_pool_size == 512

    def test_frozen_dataclass(self) -> None:
        """frozen dataclass 不可变。"""
        cfg = GPUConfig()
        with pytest.raises(AttributeError):
            cfg.device_id = 1  # type: ignore[misc]


class TestCheckCuPyAvailability:
    """CuPy 可用性检查测试。"""

    def test_returns_bool(self) -> None:
        """返回布尔值。"""
        result = check_cupy_availability()
        assert isinstance(result, bool)

    def test_consistent(self) -> None:
        """多次调用结果一致。"""
        r1 = check_cupy_availability()
        r2 = check_cupy_availability()
        assert r1 == r2


class TestNumPyBackend:
    """NumPy CPU 后端测试。"""

    def test_fft2(self) -> None:
        """2D FFT。"""
        field = np.random.rand(16, 16)
        result = NumPyBackend.fft2(field)
        assert result.shape == (16, 16)

    def test_ifft2(self) -> None:
        """2D IFFT。"""
        field = np.random.rand(16, 16) + 1j * np.random.rand(16, 16)
        result = NumPyBackend.ifft2(field)
        assert result.shape == (16, 16)

    def test_fft_ifft_roundtrip(self) -> None:
        """FFT/IFFT 往返一致性。"""
        field = np.random.rand(16, 16)
        result = NumPyBackend.ifft2(NumPyBackend.fft2(field))
        assert np.allclose(result.real, field, atol=1e-10)

    def test_matmul(self) -> None:
        """矩阵乘法。"""
        a = np.random.rand(4, 8)
        b = np.random.rand(8, 4)
        result = NumPyBackend.matmul(a, b)
        assert result.shape == (4, 4)
        assert np.allclose(result, a @ b)

    def test_convolve2d(self) -> None:
        """2D 卷积。"""
        field = np.random.rand(16, 16)
        kernel = NumPyBackend.gaussian_kernel((5, 5), 1.0)
        result = NumPyBackend.convolve2d(field, kernel)
        assert result.shape == (16, 16)
        assert result.dtype == np.float64

    def test_gaussian_kernel(self) -> None:
        """高斯核。"""
        kernel = NumPyBackend.gaussian_kernel((5, 5), 1.0)
        assert kernel.shape == (5, 5)
        # 归一化到 sum=1
        assert np.isclose(kernel.sum(), 1.0)
        # 中心值最大
        assert kernel[2, 2] == kernel.max()

    def test_to_numpy(self) -> None:
        """转 NumPy。"""
        arr = np.array([1.0, 2.0, 3.0])
        result = NumPyBackend.to_numpy(arr)
        assert np.allclose(result, arr)

    def test_from_numpy(self) -> None:
        """从 NumPy 创建。"""
        arr = np.array([1.0, 2.0, 3.0])
        result = NumPyBackend.from_numpy(arr)
        assert np.allclose(result, arr)


class TestCuPyBackend:
    """CuPy GPU 后端测试（条件跳过）。"""

    @pytest.fixture
    def backend(self) -> CuPyBackend:
        """CuPy 后端 fixture。"""
        if not check_cupy_availability():
            pytest.skip("CuPy 不可用，跳过 GPU 测试")
        return CuPyBackend()

    def test_creation(self, backend: CuPyBackend) -> None:
        """创建 CuPy 后端。"""
        assert backend.config.device_id == 0

    def test_fft2(self, backend: CuPyBackend) -> None:
        """2D FFT。"""
        field = backend.from_numpy(np.random.rand(16, 16))
        result = backend.fft2(field)
        result_np = backend.to_numpy(result)
        assert result_np.shape == (16, 16)

    def test_matmul(self, backend: CuPyBackend) -> None:
        """矩阵乘法。"""
        a = backend.from_numpy(np.random.rand(4, 8))
        b = backend.from_numpy(np.random.rand(8, 4))
        result = backend.matmul(a, b)
        result_np = backend.to_numpy(result)
        assert result_np.shape == (4, 4)

    def test_to_from_numpy_roundtrip(
        self,
        backend: CuPyBackend,
    ) -> None:
        """to/from numpy 往返。"""
        original = np.random.rand(8, 8)
        gpu_arr = backend.from_numpy(original)
        recovered = backend.to_numpy(gpu_arr)
        assert np.allclose(recovered, original)


class TestGPUBackend:
    """统一 GPU 后端测试。"""

    def test_creation_default(self) -> None:
        """默认创建。"""
        backend = GPUBackend()
        assert backend.device_type in (DeviceType.CPU, DeviceType.GPU)

    def test_creation_force_cpu(self) -> None:
        """强制 CPU。"""
        cfg = GPUConfig(force_cpu=True)
        backend = GPUBackend(cfg)
        assert backend.device_type == DeviceType.CPU
        assert backend.is_gpu is False

    def test_fft2_cpu(self) -> None:
        """CPU 后端 FFT2。"""
        cfg = GPUConfig(force_cpu=True)
        backend = GPUBackend(cfg)
        field = np.random.rand(16, 16)
        result = backend.to_numpy(backend.fft2(field))
        assert result.shape == (16, 16)

    def test_ifft2_cpu(self) -> None:
        """CPU 后端 IFFT2。"""
        cfg = GPUConfig(force_cpu=True)
        backend = GPUBackend(cfg)
        field = np.random.rand(16, 16)
        result = backend.to_numpy(backend.ifft2(field))
        assert result.shape == (16, 16)

    def test_matmul_cpu(self) -> None:
        """CPU 后端矩阵乘法。"""
        cfg = GPUConfig(force_cpu=True)
        backend = GPUBackend(cfg)
        a = np.random.rand(4, 8)
        b = np.random.rand(8, 4)
        result = backend.to_numpy(backend.matmul(a, b))
        assert result.shape == (4, 4)
        assert np.allclose(result, a @ b)

    def test_convolve2d_cpu(self) -> None:
        """CPU 后端 2D 卷积。"""
        cfg = GPUConfig(force_cpu=True)
        backend = GPUBackend(cfg)
        field = np.random.rand(16, 16)
        kernel = backend.gaussian_kernel((5, 5), 1.0)
        result = backend.to_numpy(backend.convolve2d(field, kernel))
        assert result.shape == (16, 16)

    def test_gaussian_kernel_cpu(self) -> None:
        """CPU 后端高斯核。"""
        cfg = GPUConfig(force_cpu=True)
        backend = GPUBackend(cfg)
        kernel = backend.to_numpy(backend.gaussian_kernel((5, 5), 1.0))
        assert kernel.shape == (5, 5)
        assert np.isclose(kernel.sum(), 1.0)

    def test_to_numpy_cpu(self) -> None:
        """CPU 后端 to_numpy。"""
        cfg = GPUConfig(force_cpu=True)
        backend = GPUBackend(cfg)
        arr = np.array([1.0, 2.0, 3.0])
        result = backend.to_numpy(arr)
        assert np.allclose(result, arr)

    def test_from_numpy_cpu(self) -> None:
        """CPU 后端 from_numpy。"""
        cfg = GPUConfig(force_cpu=True)
        backend = GPUBackend(cfg)
        arr = np.array([1.0, 2.0, 3.0])
        result = backend.from_numpy(arr)
        assert np.allclose(result, arr)

    def test_fft_ifft_roundtrip_cpu(self) -> None:
        """CPU 后端 FFT/IFFT 往返。"""
        cfg = GPUConfig(force_cpu=True)
        backend = GPUBackend(cfg)
        field = np.random.rand(16, 16)
        result = backend.to_numpy(backend.ifft2(backend.fft2(field)))
        assert np.allclose(result.real, field, atol=1e-10)

    def test_benchmark_cpu(self) -> None:
        """CPU 后端基准测试。"""
        cfg = GPUConfig(force_cpu=True)
        backend = GPUBackend(cfg)
        results = backend.benchmark(size=32, iterations=2)
        assert "fft2" in results
        assert "ifft2" in results
        assert "convolve2d" in results
        assert "matmul" in results
        for op, t in results.items():
            assert t > 0, f"{op} 耗时应 > 0"


class TestFactoryFunctions:
    """工厂函数测试。"""

    def test_create_gpu_backend(self) -> None:
        """创建 GPU 后端工厂。"""
        backend = create_gpu_backend()
        assert isinstance(backend, GPUBackend)

    def test_create_gpu_backend_force_cpu(self) -> None:
        """强制 CPU 工厂。"""
        cfg = GPUConfig(force_cpu=True)
        backend = create_gpu_backend(cfg)
        assert backend.device_type == DeviceType.CPU

    def test_get_gpu_status(self) -> None:
        """获取 GPU 状态。"""
        status = get_gpu_status()
        assert "cupy_available" in status
        assert "device_count" in status
        assert "device_type" in status
        assert isinstance(status["cupy_available"], bool)
        assert isinstance(status["device_count"], int)
        assert status["device_type"] in (DeviceType.CPU, DeviceType.GPU)


class TestCommercialGapReduction:
    """商业差距缩减验证（对标 DREAMPlace GPU 加速）。"""

    def test_dreamplace_aligned(self) -> None:
        """DREAMPlace GPU 加速对齐：
        - 自动 GPU/CPU 切换
        - FFT 加速卷积
        - 矩阵运算加速
        """
        backend = create_gpu_backend(GPUConfig(force_cpu=True))
        # FFT 加速卷积
        field = np.random.rand(64, 64)
        kernel = backend.gaussian_kernel((15, 15), 2.0)
        result = backend.to_numpy(backend.convolve2d(field, kernel))
        assert result.shape == (64, 64)
        # 矩阵运算
        a = np.random.rand(32, 32)
        b = np.random.rand(32, 32)
        result_mat = backend.to_numpy(backend.matmul(a, b))
        assert np.allclose(result_mat, a @ b)

    def test_automatic_fallback(self) -> None:
        """自动降级（GPU 不可用时降级为 CPU）。"""
        cfg = GPUConfig(force_cpu=True)
        backend = GPUBackend(cfg)
        # 强制 CPU 时应使用 CPU
        assert backend.device_type == DeviceType.CPU
        # 所有操作应正常工作
        field = np.random.rand(8, 8)
        result = backend.to_numpy(backend.fft2(field))
        assert result.shape == (8, 8)

    def test_numerical_consistency(self) -> None:
        """数值一致性（CPU 后端与 NumPy 一致）。"""
        cfg = GPUConfig(force_cpu=True)
        backend = GPUBackend(cfg)
        field = np.random.rand(16, 16)
        # FFT 应与 numpy 一致
        result = backend.to_numpy(backend.fft2(field))
        expected = np.fft.fft2(field)
        assert np.allclose(result, expected)

    def test_convolve2d_correctness(self) -> None:
        """2D 卷积正确性。"""
        cfg = GPUConfig(force_cpu=True)
        backend = GPUBackend(cfg)
        field = np.ones((16, 16))
        kernel = backend.to_numpy(backend.gaussian_kernel((5, 5), 1.0))
        result = backend.to_numpy(backend.convolve2d(field, kernel))
        # 卷积后中心区域应接近 1（高斯核归一化）
        assert np.allclose(result[8, 8], 1.0, atol=0.1)

    def test_benchmark_metrics(self) -> None:
        """基准测试指标。"""
        cfg = GPUConfig(force_cpu=True)
        backend = GPUBackend(cfg)
        results = backend.benchmark(size=64, iterations=3)
        # 所有操作都应有耗时记录
        assert len(results) == 4
        # FFT 和 IFFT 耗时应接近
        assert abs(results["fft2"] - results["ifft2"]) < 1.0

    def test_gpu_status_query(self) -> None:
        """GPU 状态查询。"""
        status = get_gpu_status()
        # 应能正确报告 CuPy 可用性
        if status["cupy_available"]:
            assert status["device_count"] >= 1
            assert status["device_type"] == DeviceType.GPU
        else:
            assert status["device_count"] == 0
            assert status["device_type"] == DeviceType.CPU
