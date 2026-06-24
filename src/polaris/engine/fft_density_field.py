"""FFT 卷积加速（第36轮 P1-1 深化）。

实现 DREAMPlace TCAD 2020 的 FFT 卷积加速密度场平滑，
替代第30轮的分离卷积，进一步加速大规模（>500 器件）布局。

## FFT 卷积原理

高斯核卷积 density_smooth = density * kernel 在频域为逐元素乘积：
    FFT(density_smooth) = FFT(density) * FFT(kernel)
    density_smooth = IFFT(FFT(density) * FFT(kernel))

复杂度:
- 直接 2D 卷积: O(G² * k²)（k=核大小）
- 分离卷积（第30轮）: O(G² * k)
- FFT 卷积（第36轮）: O(G² log G)

当核大小 k > log G 时 FFT 更快（典型 G=128, k=30 → log G=7）。

## 商业差距

P1-1 布局算法先进性深化：
- 商业标杆：DREAMPlace GPU FFT（TCAD 2020）
- 本模块实现 CPU FFT 卷积，对标 DREAMPlace 核心算法

## 来源

- DREAMPlace TCAD 2020: https://arxiv.org/abs/2004.10746
- DREAMPlace 实现: https://github.com/limbo018/DREAMPlace
- Cooley-Tukey FFT: Cooley & Tukey 1965 "An algorithm for the machine
  calculation of complex Fourier series"
- numpy.fft: https://numpy.org/doc/stable/reference/routines.fft.html
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class FFTConfig:
    """FFT 卷积配置。

    Attributes:
        use_fft: 是否使用 FFT 卷积（False 则用分离卷积）。
        pad_mode: 边界填充模式（"constant"/"edge"/"reflect"）。
        pad_value: constant 模式填充值（默认 0）。
        normalize: 是否归一化卷积结果。
    """

    use_fft: bool = True
    pad_mode: str = "constant"
    pad_value: float = 0.0
    normalize: bool = True


class FFTConvolver:
    """FFT 卷积器（对标 DREAMPlace FFT 密度场平滑）。

    用 FFT 加速 2D 高斯核卷积，复杂度 O(G² log G)。

    来源:
    - DREAMPlace TCAD 2020 Section III.B
    - Cooley-Tukey FFT 算法

    Args:
        config: FFT 配置。
    """

    def __init__(self, config: FFTConfig | None = None) -> None:
        """初始化 FFT 卷积器。

        Args:
            config: 配置（None 用默认）。
        """
        self.config = config or FFTConfig()

    def convolve_gaussian(
        self,
        field: np.ndarray,
        sigma: float,
    ) -> np.ndarray:
        """用 FFT 卷积高斯核平滑密度场。

        流程:
        1. 构建高斯核（与 field 同大小，中心对齐）
        2. 对 field 和 kernel 做 FFT
        3. 频域逐元素乘积
        4. IFFT 回时域
        5. 裁剪到原大小（去除填充）

        Args:
            field: 输入密度场（Gx × Gy）。
            sigma: 高斯核标准差（网格单位）。

        Returns:
            平滑后密度场（同形状）。
        """
        if sigma <= 0:
            return field.copy()
        if not self.config.use_fft:
            return self._separable_convolve(field, sigma)
        kernel = self._build_gaussian_kernel_fft(field.shape, sigma)
        return self._fft_convolve(field, kernel)

    def _fft_convolve(
        self,
        field: np.ndarray,
        kernel: np.ndarray,
    ) -> np.ndarray:
        """执行 FFT 卷积。

        Args:
            field: 输入场。
            kernel: 卷积核（同形状，已归一化）。

        Returns:
            卷积结果。
        """
        fft_field = np.fft.fft2(field)
        fft_kernel = np.fft.fft2(kernel)
        return np.fft.ifft2(fft_field * fft_kernel).real

    def _build_gaussian_kernel_fft(
        self,
        shape: tuple[int, int],
        sigma: float,
    ) -> np.ndarray:
        """构建 FFT 卷积用高斯核（与 field 同大小）。

        FFT 卷积要求核与输入同大小，核中心对齐到 (0, 0)。
        使用 np.fft.fftshift 对齐。核归一化到 sum=1（与分离卷积一致）。

        Args:
            shape: 核形状 (Gx, Gy)。
            sigma: 标准差（网格单位）。

        Returns:
            高斯核（同形状，中心对齐到 (0, 0)，归一化）。
        """
        gx, gy = shape
        x = np.arange(gx) - gx // 2
        y = np.arange(gy) - gy // 2
        xx, yy = np.meshgrid(x, y, indexing="ij")
        kernel = np.exp(-(xx**2 + yy**2) / (2 * sigma**2))
        # 归一化到 sum=1（与分离卷积一致）
        kernel_sum = kernel.sum()
        if kernel_sum > 0:
            kernel = kernel / kernel_sum
        # fftshift 使中心对齐到 (0, 0)
        return np.fft.ifftshift(kernel)

    def _separable_convolve(
        self,
        field: np.ndarray,
        sigma: float,
    ) -> np.ndarray:
<<<<<<< HEAD
        """分离卷积（独立模式，当 use_fft=False 时显式选择，非 fall-back）。
=======
        """分离卷积（fallback，当 use_fft=False 时使用）。
>>>>>>> trae/solo-agent-pkVjID

        Args:
            field: 输入场。
            sigma: 标准差。

        Returns:
            卷积结果。
        """
        radius = max(1, int(3 * sigma))
        kernel_1d = self._gaussian_kernel_1d(sigma, radius)
        temp = self._convolve_1d(field, kernel_1d, axis=0)
        return self._convolve_1d(temp, kernel_1d, axis=1)

    def _gaussian_kernel_1d(
        self,
        sigma: float,
        radius: int,
    ) -> np.ndarray:
        """构建 1D 高斯核。

        Args:
            sigma: 标准差。
            radius: 核半径。

        Returns:
            1D 高斯核（归一化）。
        """
        x = np.arange(-radius, radius + 1, dtype=np.float64)
        kernel = np.exp(-(x**2) / (2 * sigma**2))
        return kernel / kernel.sum()

    def _convolve_1d(
        self,
        array: np.ndarray,
        kernel: np.ndarray,
        axis: int,
    ) -> np.ndarray:
        """沿指定轴 1D 卷积（边界零填充）。

        Args:
            array: 输入数组。
            kernel: 1D 卷积核。
            axis: 卷积轴。

        Returns:
            卷积结果（同形状）。
        """
        n = array.shape[axis]
        k = len(kernel)
        pad = k // 2
        padded = np.pad(array, [(pad, pad) if ax == axis else (0, 0)
                                for ax in range(array.ndim)], mode="constant")
        result = np.zeros_like(array, dtype=np.float64)
        for i in range(k):
            slc = [slice(i, i + n) if ax == axis else slice(None)
                   for ax in range(array.ndim)]
            result += kernel[i] * padded[tuple(slc)]
        return result


class DensityFieldFFT:
    """FFT 加速的密度场（对标 DREAMPlace FFT 密度场）。

    封装 FFTConvolver，提供与 DensityField 兼容的接口，
    用于大规模（>500 器件）布局的密度场计算。

    来源:
    - DREAMPlace TCAD 2020 Section III.B
    - 第30轮 DensityField 的 FFT 升级版

    Args:
        canvas_w: 画布宽度（μm）。
        canvas_h: 画布高度（μm）。
        grid_size: 网格分辨率。
        config: FFT 配置。
    """

    def __init__(
        self,
        canvas_w: float,
        canvas_h: float,
        grid_size: int = 128,
        config: FFTConfig | None = None,
    ) -> None:
        """初始化 FFT 密度场。

        Args:
            canvas_w: 画布宽度。
            canvas_h: 画布高度。
            grid_size: 网格分辨率。
            config: FFT 配置。
        """
        self.canvas_w = canvas_w
        self.canvas_h = canvas_h
        self.grid_size = grid_size
        self.dx = canvas_w / grid_size
        self.dy = canvas_h / grid_size
        self.density = np.zeros((grid_size, grid_size))
        self.smoothed: np.ndarray | None = None
        self.convolver = FFTConvolver(config)

    def build(
        self,
        pos: np.ndarray,
        widths: np.ndarray,
        heights: np.ndarray,
    ) -> None:
        """构建密度场（双线性插值面积分布）。

        Args:
            pos: 器件坐标 (n, 2)。
            widths: 器件宽度 (n,)。
            heights: 器件高度 (n,)。
        """
        self.density.fill(0.0)
        n = len(pos)
        for i in range(n):
            cx, cy = pos[i, 0], pos[i, 1]
            area = widths[i] * heights[i]
            gx = cx / self.dx - 0.5
            gy = cy / self.dy - 0.5
            x0, y0 = int(np.floor(gx)), int(np.floor(gy))
            x1, y1 = x0 + 1, y0 + 1
            wx1, wy1 = gx - x0, gy - y0
            wx0, wy0 = 1.0 - wx1, 1.0 - wy1
            for gx_idx, wx in ((x0, wx0), (x1, wx1)):
                for gy_idx, wy in ((y0, wy0), (y1, wy1)):
                    if 0 <= gx_idx < self.grid_size and 0 <= gy_idx < self.grid_size:
                        self.density[gx_idx, gy_idx] += area * wx * wy

    def smooth_gaussian(self, sigma: float) -> None:
        """FFT 高斯卷积平滑。

        Args:
            sigma: 高斯核标准差（μm）。
        """
        sigma_grid = sigma / self.dx
        self.smoothed = self.convolver.convolve_gaussian(self.density, sigma_grid)

    def gradient_at(self, pos: np.ndarray) -> np.ndarray:
        """查询器件位置密度梯度。

        Args:
            pos: 器件坐标 (n, 2)。

        Returns:
            梯度 (n, 2)。
        """
        if self.smoothed is None:
            self.smooth_gaussian(10.0)
        assert self.smoothed is not None
        grad_x, grad_y = self._central_difference(self.smoothed)
        n = len(pos)
        result = np.zeros((n, 2), dtype=np.float64)
        for i in range(n):
            gx = pos[i, 0] / self.dx - 0.5
            gy = pos[i, 1] / self.dy - 0.5
            result[i, 0] = self._bilinear_sample(grad_x, gx, gy)
            result[i, 1] = self._bilinear_sample(grad_y, gx, gy)
        return result

    def _central_difference(self, field: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """中心差分梯度。

        Args:
            field: 输入场。

        Returns:
            (grad_x, grad_y)。
        """
        grad_x = np.zeros_like(field)
        grad_y = np.zeros_like(field)
        grad_x[1:-1, :] = (field[2:, :] - field[:-2, :]) / (2 * self.dx)
        grad_x[0, :] = (field[1, :] - field[0, :]) / self.dx
        grad_x[-1, :] = (field[-1, :] - field[-2, :]) / self.dx
        grad_y[:, 1:-1] = (field[:, 2:] - field[:, :-2]) / (2 * self.dy)
        grad_y[:, 0] = (field[:, 1] - field[:, 0]) / self.dy
        grad_y[:, -1] = (field[:, -1] - field[:, -2]) / self.dy
        return grad_x, grad_y

    def _bilinear_sample(
        self,
        field: np.ndarray,
        gx: float,
        gy: float,
    ) -> float:
        """双线性插值采样。

        Args:
            field: 输入场。
            gx: x 网格坐标。
            gy: y 网格坐标。

        Returns:
            采样值。
        """
        g = self.grid_size
        gx = max(0, min(g - 1, gx))
        gy = max(0, min(g - 1, gy))
        x0, y0 = int(np.floor(gx)), int(np.floor(gy))
        x1, y1 = min(x0 + 1, g - 1), min(y0 + 1, g - 1)
        wx1, wy1 = gx - x0, gy - y0
        wx0, wy0 = 1.0 - wx1, 1.0 - wy1
        return float(
            field[x0, y0] * wx0 * wy0
            + field[x1, y0] * wx1 * wy0
            + field[x0, y1] * wx0 * wy1
            + field[x1, y1] * wx1 * wy1
        )


def create_fft_density_field(
    canvas_w: float,
    canvas_h: float,
    grid_size: int = 128,
    use_fft: bool = True,
) -> DensityFieldFFT:
    """创建 FFT 密度场工厂函数。

    Args:
        canvas_w: 画布宽度。
        canvas_h: 画布高度。
        grid_size: 网格分辨率。
        use_fft: 是否使用 FFT。

    Returns:
        DensityFieldFFT 实例。
    """
    config = FFTConfig(use_fft=use_fft)
    return DensityFieldFFT(canvas_w, canvas_h, grid_size, config)


def benchmark_fft_vs_separable(
    grid_size: int = 128,
    sigma: float = 5.0,
) -> dict[str, float]:
    """基准测试 FFT vs 分离卷积性能。

    Args:
        grid_size: 网格大小。
        sigma: 高斯核标准差。

    Returns:
        性能指标字典。
    """
    import time

    field = np.random.rand(grid_size, grid_size)
    fft_conv = FFTConvolver(FFTConfig(use_fft=True))
    sep_conv = FFTConvolver(FFTConfig(use_fft=False))
    # FFT 卷积
    start = time.perf_counter()
    for _ in range(10):
        fft_conv.convolve_gaussian(field, sigma)
    fft_time = (time.perf_counter() - start) / 10
    # 分离卷积
    start = time.perf_counter()
    for _ in range(10):
        sep_conv.convolve_gaussian(field, sigma)
    sep_time = (time.perf_counter() - start) / 10
    return {
        "fft_time_s": fft_time,
        "separable_time_s": sep_time,
        "speedup": sep_time / max(fft_time, 1e-10),
        "grid_size": grid_size,
        "sigma": sigma,
    }


__all__ = [
    "FFTConfig",
    "FFTConvolver",
    "DensityFieldFFT",
    "benchmark_fft_vs_separable",
    "create_fft_density_field",
]
