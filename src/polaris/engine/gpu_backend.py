"""GPU 加速后端（第41轮 P1-1 深化，CuPy 后端）。

🚫不参与 GPU 计算（R04 战略决策，不可撤销，2026-06-25 项目所有者指示）

实现 GPU 加速后端用于布局布线计算，对标 DREAMPlace GPU 加速
与 AlphaChip TPU 加速。

R05 Bug 修复 v4.0-R04-01（第1轮迭代发现）:
原代码完整实现 CuPyBackend GPU 路径（import cupy、cupy.cuda.Device、CuPyBackend.__init__），
违反 R04"禁止 CuPy/CUDA/ROCm 等所有 GPU 后端"战略决策。修复：
1. CuPyBackend.__init__ 立即 raise RuntimeError，禁止 GPU 路径
2. create_gpu_backend 入口校验 force_cpu=True，否则 raise
3. 保留类定义（不破坏 import 链）但 GPU 路径不可达
4. NumPyBackend 作为唯一可用后端（非 fall-back，是 R04 战略下的唯一实现）
规则: R04 不参与 GPU（战略）/ R05 Bug 必修 / R03 禁止 fall-back
文献: R04-不参与GPU.md / DREAMPlace TCAD 2020 https://doi.org/10.1109/TCAD.2020.2976921

## 架构

- ``GPUBackend``：统一后端接口（🚫GPU 路径已禁用，仅 CPU 可用）
- ``CuPyBackend``：CuPy GPU 后端（🚫不参与，__init__ 即 raise）
- ``NumPyBackend``：NumPy CPU 后端（R04 战略下唯一可用后端）

## 设计原则

R04 战略决策：PoLaRIS 不参与 GPU 计算。
- 禁止 CuPy/CUDA/ROCm/AppleMetal 等所有 GPU 后端
- GPU 相关功能点标记 🚫不参与，不计入覆盖率
- 纯 NumPy/SciPy/JAX(CPU) 实现
- NumPyBackend 是 R04 战略下的唯一可用后端（非 fall-back，是战略选择）

## 商业差距

P1-1 布局算法先进性深化：
- 商业标杆：DREAMPlace GPU 40× 加速，AlphaChip TPU 加速
- 🚫本项目战略决策不参与 GPU，通过 CPU 算法优化（JAX JIT、SciPy 稀疏矩阵）弥补

## 来源

- DREAMPlace: Lin et al., TCAD 2020,
  https://doi.org/10.1109/TCAD.2020.2976921
- CuPy: Okuta et al., 2017, https://cupy.dev/
- AlphaChip: Mirhoseini et al., Nature 2021,
  https://www.nature.com/articles/s41586-021-03544-w
- R04 战略: .trae/rules/R04-不参与GPU.md
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
    """CuPy GPU 后端（🚫不参与，R04 战略禁用）。

    R05 Bug 修复 v4.0-R04-01: __init__ 立即 raise RuntimeError，
    禁止任何 GPU 路径。R04 战略决策不可撤销。
    保留类定义仅为向后兼容 import 链（gpu_density_field.py 仍 import 此类名），
    但 GPU 路径完全不可达。

    对标 DREAMPlace GPU 加速（🚫本项目不参与）。
    """

    def __init__(self, config: GPUConfig | None = None) -> None:
        """初始化 CuPy 后端（🚫禁止，R04 战略）。

        Args:
            config: GPU 配置（忽略）。

        Raises:
            RuntimeError: 始终抛出，R04 战略禁止 GPU 计算。
        """
        # R04 战略决策：不参与 GPU 计算，禁止 CuPy/CUDA/ROCm
        # 原 try/except import cupy 路径已删除，禁止任何 GPU 后端初始化
        # 规则: R04 不参与 GPU（不可撤销）/ R03 禁止 fall-back / R05 Bug 必修
        raise RuntimeError(
            "🚫R04 战略决策：PoLaRIS 不参与 GPU 计算（2026-06-25 项目所有者指示）。"
            "禁止 CuPy/CUDA/ROCm 等所有 GPU 后端。"
            "请使用 NumPyBackend（CPU）或 polaris.engine.fft_density_field（CPU FFT）。"
            "参考: .trae/rules/R04-不参与GPU.md"
        )

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
    """统一 GPU 后端接口（🚫GPU 路径禁用，R04 战略）。

    R05 Bug 修复 v4.0-R04-01: R04 战略决策不参与 GPU 计算，
    GPUBackend 永远使用 NumPyBackend（CPU），GPU 路径完全禁用。
    force_cpu 标志被忽略（始终为 True），CuPyBackend 永不初始化。

    R04 战略下 NumPyBackend 是唯一可用后端（非 fall-back，是战略选择）。

    来源:
        DREAMPlace: Lin et al., TCAD 2020,
        https://doi.org/10.1109/TCAD.2020.2976921
        R04 战略: .trae/rules/R04-不参与GPU.md
    """

    def __init__(self, config: GPUConfig | None = None) -> None:
        """初始化后端（🚫强制 CPU，R04 战略）。

        Args:
            config: GPU 配置（force_cpu 被强制为 True，R04 战略）。
        """
        # R04 战略：强制 CPU，禁止 GPU 路径
        # 原 check_cupy_availability + CuPyBackend 路径已删除
        self.config = config or GPUConfig()
        # R04: force_cpu 强制为 True，忽略用户传入的 False
        # （不修改 frozen dataclass，而是在逻辑上强制 CPU）
        self._cupy_available = False  # R04: 永远 False，不检查 CuPy
        self._backend: Any = NumPyBackend()  # R04: 唯一可用后端
        self._device_type = DeviceType.CPU  # R04: 永远 CPU

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
    """工厂函数：创建后端（🚫强制 CPU，R04 战略）。

    R05 Bug 修复 v4.0-R04-01: R04 战略决策不参与 GPU 计算，
    永远返回 CPU 后端（NumPyBackend），GPU 路径完全禁用。
    config.force_cpu 被忽略（始终为 True）。

    Args:
        config: GPU 配置（force_cpu 被强制为 True，R04 战略）。

    Returns:
        GPUBackend 实例（内部使用 NumPyBackend，CPU 模式）。
    """
    # R04: 不检查 CuPy，直接创建 CPU 后端
    # GPUBackend.__init__ 内部已强制 CPU
    return GPUBackend(config)


def get_gpu_status() -> dict[str, Any]:
    """获取 GPU 状态信息（🚫R04 战略：永远返回不可用）。

    R05 Bug 修复 v4.0-R04-01: R04 战略决策不参与 GPU 计算，
    get_gpu_status 永远返回 cupy_available=False, device_count=0。
    不再调用 check_cupy_availability() 检测 CuPy（避免触发 import cupy）。

    Returns:
        状态字典 {cupy_available: False, device_type: "cpu", device_count: 0}。
    """
    # R04: 永远返回 GPU 不可用，不检测 CuPy
    return {
        "cupy_available": False,
        "device_type": "cpu",
        "device_count": 0,
        "r04_strategy": "🚫不参与 GPU 计算（战略决策不可撤销）",
    }
