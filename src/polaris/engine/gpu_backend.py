"""GPU 加速后端（第41轮 P1-1 深化，CuPy 后端）。

实现 GPU 加速后端用于布局布线计算，对标 DREAMPlace GPU 加速
与 AlphaChip TPU 加速。

## 架构

- ``GPUBackend``：统一 GPU 后端接口（CPU/GPU 双模式设计）
- ``CuPyBackend``：CuPy GPU 后端（FFT/矩阵运算/密度场）
- ``NumPyBackend``：NumPy CPU 后端（独立模式，非 fall-back）

## 设计原则

CPU/GPU 双模式是性能优化设计（计算结果相同，仅速度不同），
非功能降级。用户可通过 ``force_cpu=True`` 显式选择 CPU 模式，
或通过 ``device_type`` 属性查看当前使用的设备。
这与 MEEP→Analytical 的功能降级 fall-back 本质不同。

## 商业差距

P1-1 布局算法先进性深化：
- 商业标杆：DREAMPlace GPU 40× 加速，AlphaChip TPU 加速
- 本模块提供 CuPy GPU 后端，CPU/GPU 双模式设计

## 来源

- DREAMPlace: Lin et al., TCAD 2020,
  https://doi.org/10.1109/TCAD.2020.2976921
- CuPy: Okuta et al., 2017, https://cupy.dev/
- AlphaChip: Mirhoseini et al., Nature 2021,
  https://www.nature.com/articles/s41586-021-03544-w
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

import numpy as np


class DeviceType(Enum):
    """计算设备类型。

    Attributes:
        CPU: CPU 设备（NumPy 后端）。
        GPU: GPU 设备（CuPy 后端）。
    """

    CPU = "cpu"
    GPU = "gpu"


def check_cupy_availability() -> bool:
    """检查 CuPy 是否可用。

    Returns:
        True 如果 CuPy 可用且 GPU 可访问。
    """
    try:
        import cupy  # type: ignore[import-not-found]

        _ = cupy.cuda.Device(0).compute_capability
        return True
    except Exception:
        return False


@dataclass(frozen=True)
class GPUConfig:
    """GPU 配置。

    Attributes:
        device_id: GPU 设备 ID。
        force_cpu: 强制使用 CPU（即使 GPU 可用）。
        memory_pool_size: CuPy 内存池大小（MB，0 表示自动）。
    """

    device_id: int = 0
    force_cpu: bool = False
    memory_pool_size: int = 0


class NumPyBackend:
    """NumPy CPU 后端。

    提供 FFT、矩阵运算、密度场计算等操作的 NumPy 实现。
    """

    @staticmethod
    def fft2(array: np.ndarray) -> np.ndarray:
        """2D FFT。"""
        return np.fft.fft2(array)

    @staticmethod
    def ifft2(array: np.ndarray) -> np.ndarray:
        """2D IFFT。"""
        return np.fft.ifft2(array)

    @staticmethod
    def matmul(a: np.ndarray, b: np.ndarray) -> np.ndarray:
        """矩阵乘法。"""
        return np.matmul(a, b)

    @staticmethod
    def convolve2d(
        field: np.ndarray,
        kernel: np.ndarray,
    ) -> np.ndarray:
        """2D 卷积（FFT 加速）。"""
        fft_field = np.fft.fft2(field)
        fft_kernel = np.fft.fft2(
            kernel, s=field.shape
        )
        return np.fft.ifft2(fft_field * fft_kernel).real

    @staticmethod
    def gaussian_kernel(
        shape: tuple[int, int],
        sigma: float,
    ) -> np.ndarray:
        """高斯核。"""
        rows, cols = shape
        cy, cx = (rows - 1) / 2, (cols - 1) / 2
        yy, xx = np.mgrid[0:rows, 0:cols]
        kernel = np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * sigma ** 2))
        return kernel / kernel.sum()

    @staticmethod
    def to_numpy(array: np.ndarray) -> np.ndarray:
        """转 NumPy 数组（CPU 后端直接返回）。"""
        return np.asarray(array)

    @staticmethod
    def from_numpy(array: np.ndarray) -> np.ndarray:
        """从 NumPy 数组创建（CPU 后端直接返回）。"""
        return np.asarray(array)


class CuPyBackend:
    """CuPy GPU 后端。

    提供 FFT、矩阵运算、密度场计算等操作的 CuPy 实现。
    需要 CuPy 和 CUDA GPU。

    对标 DREAMPlace GPU 加速。
    """

    def __init__(self, config: GPUConfig | None = None) -> None:
        """初始化 CuPy 后端。

        Args:
            config: GPU 配置。
        """
        self.config = config or GPUConfig()
        try:
            import cupy  # type: ignore[import-not-found]

            self._cupy = cupy
            self._device = cupy.cuda.Device(self.config.device_id)
        except ImportError as e:
            raise RuntimeError(
                "CuPy 未安装，无法使用 GPU 后端"
            ) from e

    def fft2(self, array: Any) -> Any:
        """2D FFT。"""
        with self._device:
            return self._cupy.fft.fft2(array)

    def ifft2(self, array: Any) -> Any:
        """2D IFFT。"""
        with self._device:
            return self._cupy.fft.ifft2(array)

    def matmul(self, a: Any, b: Any) -> Any:
        """矩阵乘法。"""
        with self._device:
            return self._cupy.matmul(a, b)

    def convolve2d(
        self,
        field: Any,
        kernel: Any,
    ) -> Any:
        """2D 卷积（FFT 加速）。"""
        with self._device:
            fft_field = self._cupy.fft.fft2(field)
            fft_kernel = self._cupy.fft.fft2(
                kernel, s=field.shape
            )
            return self._cupy.fft.ifft2(fft_field * fft_kernel).real

    def gaussian_kernel(
        self,
        shape: tuple[int, int],
        sigma: float,
    ) -> Any:
        """高斯核。"""
        with self._device:
            rows, cols = shape
            cy, cx = (rows - 1) / 2, (cols - 1) / 2
            yy, xx = self._cupy.mgrid[0:rows, 0:cols]
            kernel = self._cupy.exp(
                -((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * sigma ** 2)
            )
            return kernel / kernel.sum()

    def to_numpy(self, array: Any) -> np.ndarray:
        """转 NumPy 数组（从 GPU 拷贝到 CPU）。"""
        if isinstance(array, self._cupy.ndarray):
            return self._cupy.asnumpy(array)
        return np.asarray(array)

    def from_numpy(self, array: np.ndarray) -> Any:
        """从 NumPy 数组创建（从 CPU 拷贝到 GPU）。"""
        return self._cupy.asarray(array)


class GPUBackend:
    """统一 GPU 后端接口。

    CPU/GPU 双模式设计（非 fall-back，计算结果相同，仅速度不同）。
    可用时使用 GPU，否则使用 CPU。用户可通过 ``force_cpu=True`` 显式选择 CPU。
    对标 DREAMPlace 自动 GPU/CPU 切换。

    来源:
        DREAMPlace: Lin et al., TCAD 2020,
        https://doi.org/10.1109/TCAD.2020.2976921
    """

    def __init__(self, config: GPUConfig | None = None) -> None:
        """初始化 GPU 后端。

        Args:
            config: GPU 配置。
        """
        self.config = config or GPUConfig()
        self._cupy_available = check_cupy_availability()
        if (
            self._cupy_available
            and not self.config.force_cpu
        ):
            self._backend: Any = CuPyBackend(self.config)
            self._device_type = DeviceType.GPU
        else:
            self._backend = NumPyBackend()
            self._device_type = DeviceType.CPU

    @property
    def device_type(self) -> DeviceType:
        """当前设备类型。"""
        return self._device_type

    @property
    def is_gpu(self) -> bool:
        """是否使用 GPU。"""
        return self._device_type == DeviceType.GPU

    def fft2(self, array: Any) -> Any:
        """2D FFT。"""
        return self._backend.fft2(array)

    def ifft2(self, array: Any) -> Any:
        """2D IFFT。"""
        return self._backend.ifft2(array)

    def matmul(self, a: Any, b: Any) -> Any:
        """矩阵乘法。"""
        return self._backend.matmul(a, b)

    def convolve2d(
        self,
        field: Any,
        kernel: Any,
    ) -> Any:
        """2D 卷积（FFT 加速）。"""
        return self._backend.convolve2d(field, kernel)

    def gaussian_kernel(
        self,
        shape: tuple[int, int],
        sigma: float,
    ) -> Any:
        """高斯核。"""
        return self._backend.gaussian_kernel(shape, sigma)

    def to_numpy(self, array: Any) -> np.ndarray:
        """转 NumPy 数组。"""
        return self._backend.to_numpy(array)

    def from_numpy(self, array: np.ndarray) -> Any:
        """从 NumPy 数组创建。"""
        return self._backend.from_numpy(array)

    def benchmark(
        self,
        size: int = 256,
        iterations: int = 10,
    ) -> dict[str, float]:
        """基准测试。

        Args:
            size: 矩阵大小。
            iterations: 迭代次数。

        Returns:
            性能指标字典 {operation: 平均耗时秒}。
        """
        import time

        results: dict[str, float] = {}
        field = np.random.rand(size, size).astype(np.float64)
        kernel = self.gaussian_kernel((size, size), 5.0)
        field_dev = self.from_numpy(field)
        kernel_dev = self.from_numpy(self.to_numpy(kernel))

        # FFT2
        start = time.time()
        for _ in range(iterations):
            _ = self.fft2(field_dev)
        results["fft2"] = (time.time() - start) / iterations

        # IFFT2
        start = time.time()
        for _ in range(iterations):
            _ = self.ifft2(field_dev)
        results["ifft2"] = (time.time() - start) / iterations

        # Convolve2D
        start = time.time()
        for _ in range(iterations):
            _ = self.convolve2d(field_dev, kernel_dev)
        results["convolve2d"] = (time.time() - start) / iterations

        # Matmul
        mat_a = self.from_numpy(np.random.rand(size, size))
        mat_b = self.from_numpy(np.random.rand(size, size))
        start = time.time()
        for _ in range(iterations):
            _ = self.matmul(mat_a, mat_b)
        results["matmul"] = (time.time() - start) / iterations

        return results


def create_gpu_backend(
    config: GPUConfig | None = None,
) -> GPUBackend:
    """工厂函数：创建 GPU 后端。

    自动检测 CuPy 可用性，可用时使用 GPU，否则降级为 CPU。
    """
    return GPUBackend(config)


def get_gpu_status() -> dict[str, Any]:
    """获取 GPU 状态信息。

    Returns:
        状态字典 {cupy_available, device_type, device_count}。
    """
    cupy_available = check_cupy_availability()
    device_count = 0
    if cupy_available:
        try:
            import cupy  # type: ignore[import-not-found]

            device_count = cupy.cuda.runtime.getDeviceCount()
        except Exception:
            device_count = 0
    return {
        "cupy_available": cupy_available,
        "device_count": device_count,
        "device_type": DeviceType.GPU if cupy_available else DeviceType.CPU,
    }
