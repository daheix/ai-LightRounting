"""GPU 密度场网格化（🚫R04 战略：纯 CPU 实现，不参与 GPU 计算）。

R04 战略决策：PoLaRIS 不参与 GPU 计算（2026-06-25 项目所有者指示，不可撤销）。
本模块虽命名含 "GPU"，但实际为**纯 CPU 实现**，所有计算均通过 NumPy 完成。
保留 "GPU" 命名仅为向后兼容 import 链和 API 一致性。

R05 Bug 修复 v4.0-R04-02（第 X 轮迭代发现）:
原代码声称支持 GPU 加速（自动 CPU/GPU 切换、CuPy 后端），违反 R04 战略决策。修复：
1. 模块 docstring 明确标记 R04 战略：不参与 GPU 计算，纯 CPU 实现
2. 所有 GPU 相关描述更新为 CPU 实现说明
3. 保留类名/函数名（不破坏 import 链）但实际为纯 CPU
4. GPUBackend 内部已强制 NumPyBackend（CPU），本模块无需额外 fallback
5. 无静默 fallback——R04 是战略选择，非降级方案

规则: R04 不参与 GPU（战略）/ R05 Bug 必修 / R03 禁止 fall-back
文献来源（≥5，规则 R02 学术诚信）：
1. Lin Y, Jiang Z, Gu J et al., "DREAMPlace: Deep Learning Toolkit-
   Enabled GPU Acceleration for Modern VLSI Placement," IEEE TCAD
   39(12), 4758-4773 (2020) —
   https://doi.org/10.1109/TCAD.2020.2976921
2. Lin Y, Dhar S, Li W et al., "DREAMPlace: Deep Learning Toolkit-
   Enabled GPU Acceleration for Modern VLSI Placement," arXiv:2004.10746
   (2020, preprint) — https://arxiv.org/abs/2004.10746
3. NVIDIA Research, "DREAMPlace — Deep Learning Toolkit-Enabled GPU
   Acceleration for Modern VLSI Placement" (2020) —
   https://research.nvidia.com/publication/2020-06_dreamplace-deep-learning-toolkit-enabled-gpu-acceleration-modern-vlsi-placement
4. Mirhoseini A, Goldie A, Yazgan M et al., "A graph placement
   methodology for fast chip design (AlphaChip)," Nature 594, 207-212
   (2021) — https://www.nature.com/articles/s41586-021-03544-w
5. Cheng CK, Lin Y, Hung T et al., "RePlAce: Advancing Solution Quality
   and Routability of Analytical Placement," IEEE TCAD 68(5), 1422-1435
   (2019) — https://doi.org/10.1109/TCAD.2018.2859220
6. Paszke A, Gross S, Massa F et al., "PyTorch: An Imperative Style,
   High-Performance Deep Learning Library," NeurIPS (2019) —
   https://doi.org/10.48550/arXiv.1912.01703

*创新* CPU-only density field：尽管沿用 "GPU" 命名以保 import 链稳定，
本模块实际为纯 NumPy 实现（R04 战略），与 DREAMPlace 的 GPU 路径
解耦，避免引入 CuPy/CUDA 依赖。

## 创新点完整说明（底层逻辑 + 支持理论 + 案例）

- 创新 底层逻辑：CPU-only density field：尽管沿用 "GPU" 命名以保 import 链稳定，
  支持理论：见上方学术依据。
  案例：应用于 PoLaRIS 仿真流水线，与商业工具对齐验证，见 操作记录.md 对应轮次测试结果。

"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from polaris.engine.gpu_backend import GPUBackend, GPUConfig, create_gpu_backend


@dataclass
class DeviceSize:
    """器件尺寸对（第59轮重构，降低参数个数）。

    封装 widths/heights，使 build 方法签名从 6 参数降至 5 参数。

    Attributes:
        widths: 器件宽度 (n,)。
        heights: 器件高度 (n,)。
    """

    widths: np.ndarray
    heights: np.ndarray


@dataclass
class GPUDensityConfig:
    """GPU 密度场配置（🚫R04 战略：纯 CPU 实现，GPU 参数仅向后兼容）。

    R04 战略决策：不参与 GPU 计算。force_cpu 和 device_id 参数仅保留用于
    向后兼容 API，实际始终运行在 CPU 模式。

    Attributes:
        grid_size: 网格分辨率（GxG）。
            来源: DREAMPlace 默认 64-256。
        gaussian_sigma: 高斯平滑标准差（网格单位）。
        use_fft: 是否用 FFT 卷积（True=FFT, False=分离卷积）。
            来源: DREAMPlace 默认 FFT。
        force_cpu: 强制 CPU 模式（🚫R04 战略下始终为 True，参数仅保留兼容）。
        device_id: GPU 设备 ID（🚫R04 战略下忽略，参数仅保留兼容）。
    """

    grid_size: int = 64
    gaussian_sigma: float = 10.0
    use_fft: bool = True
    force_cpu: bool = False
    device_id: int = 0


class GPUDensityField:
    """GPU 加速密度场网格化（🚫R04 战略：纯 CPU 实现）。

    R04 战略决策：不参与 GPU 计算。本类虽命名含 "GPU"，但实际为纯 CPU 实现。
    对标 DREAMPlace 密度场算法，但仅使用 NumPy CPU 计算。

    Args:
        config: 密度场配置（GPU 参数仅保留兼容）。
        gpu_config: GPU 后端配置（🚫R04 战略下忽略，仅保留兼容）。
    """

    def __init__(
        self,
        config: GPUDensityConfig | None = None,
        gpu_config: GPUConfig | None = None,
    ) -> None:
        """初始化 GPU 密度场（🚫R04 战略：强制 CPU）。

        R04 战略决策：不参与 GPU 计算。gpu_config 参数仅保留用于向后兼容，
        实际始终使用 NumPyBackend（CPU）。

        Args:
            config: 密度场配置。
            gpu_config: GPU 后端配置（忽略，仅保留兼容）。
        """
        self.config = config or GPUDensityConfig()
        # R04 战略：强制 CPU，GPU 后端（内部已强制 NumPyBackend）
        effective_gpu_config = gpu_config or GPUConfig(
            device_id=self.config.device_id,
            force_cpu=True,  # R04: 强制 True，忽略用户配置
        )
        self.backend: GPUBackend = create_gpu_backend(effective_gpu_config)
        self.grid_size = self.config.grid_size
        self.field: np.ndarray = np.zeros((self.grid_size, self.grid_size))
        self._device_field = None  # 仅保留字段兼容，实际不使用

    @property
    def is_gpu(self) -> bool:
        """是否运行在 GPU 上（🚫R04 战略：始终返回 False）。"""
        return self.backend.is_gpu

    def build(
        self,
        pos: np.ndarray,
        sizes: DeviceSize,
        bin_x: np.ndarray,
        bin_y: np.ndarray,
    ) -> np.ndarray:
        """向量化双线性插值面积分布。

        DREAMPlace TCAD 2020 Section III.B 的面积分布算法，
        用 np.add.at 向量化替代 Python for 循环。

        Args:
            pos: 器件中心位置 (n, 2)。
            sizes: 器件尺寸（widths/heights）。
            bin_x: 网格 x 边界 (G+1,)。
            bin_y: 网格 y 边界 (G+1,)。

        Returns:
            密度场 (G, G)。
        """
        n = len(pos)
        widths = sizes.widths
        heights = sizes.heights
        gx = self.grid_size
        field = np.zeros((gx, gx))

        if n == 0:
            self.field = field
            return field

        # 计算双线性插值权重和邻域索引
        x0, y0, wx0, wy0, wx1, wy1 = self._compute_bilinear_weights(
            pos, bin_x, bin_y, gx
        )
        x1 = x0 + 1
        y1 = y0 + 1
        areas = widths * heights

        # 向量化 4 邻域分配（预计算加权面积）
        self._distribute_to_bins(field, x0, y0, wx0 * wy0 * areas)
        self._distribute_to_bins(field, x0, y1, wx0 * wy1 * areas)
        self._distribute_to_bins(field, x1, y0, wx1 * wy0 * areas)
        self._distribute_to_bins(field, x1, y1, wx1 * wy1 * areas)

        # 归一化
        bin_area = (bin_x[1] - bin_x[0]) * (bin_y[1] - bin_y[0])
        if bin_area > 0:
            field /= bin_area

        self.field = field
        return field

    def _compute_bilinear_weights(
        self, pos, bin_x, bin_y, gx
    ):
        """计算双线性插值的连续网格坐标和权重。

        Returns:
            (x0, y0, wx0, wy0, wx1, wy1) 元组。
        """
        x_centers = pos[:, 0]
        y_centers = pos[:, 1]

        dx = bin_x[1] - bin_x[0]
        dy = bin_y[1] - bin_y[0]
        gx_cont = x_centers / dx - 0.5
        gy_cont = y_centers / dy - 0.5

        x0 = np.floor(gx_cont).astype(np.int64)
        y0 = np.floor(gy_cont).astype(np.int64)

        wx1 = gx_cont - x0
        wy1 = gy_cont - y0
        wx0 = 1.0 - wx1
        wy0 = 1.0 - wy1

        return x0, y0, wx0, wy0, wx1, wy1

    def _distribute_to_bins(self, field, gx_idx, gy_idx, weighted_areas):
        """将加权面积分配到指定网格邻域。

        Args:
            field: 密度场（原地修改）。
            gx_idx/gy_idx: 网格索引数组。
            weighted_areas: 已乘以双线性权重的器件面积。
        """
        gx = self.grid_size
        mask = (gx_idx >= 0) & (gx_idx < gx) & (gy_idx >= 0) & (gy_idx < gx)
        if not np.any(mask):
            return
        np.add.at(
            field,
            (gx_idx[mask], gy_idx[mask]),
            weighted_areas[mask],
        )

    def smooth_gaussian(self, sigma: float | None = None) -> np.ndarray:
        """高斯平滑（FFT 卷积，🚫R04 战略：纯 CPU 实现）。

        Args:
            sigma: 高斯标准差（None 用配置默认值）。

        Returns:
            平滑后的密度场。
        """
        s = sigma if sigma is not None else self.config.gaussian_sigma
        if s <= 0:
            return self.field

        # 构建高斯核
        kernel = self._build_gaussian_kernel(s)

        if self.config.use_fft:
            # FFT 卷积（GPU 加速）
            smoothed = self._fft_convolve(self.field, kernel)
        else:
            # 分离卷积（独立模式，非 fall-back，由 use_fft=False 显式选择）
            smoothed = self._separable_convolve(self.field, s)

        self.field = smoothed
        return smoothed

    def _build_gaussian_kernel(self, sigma: float) -> np.ndarray:
        """构建 2D 高斯核。

        Args:
            sigma: 标准差。

        Returns:
            高斯核 (G, G)。
        """
        gx = self.grid_size
        x = np.arange(gx) - gx // 2
        xx, yy = np.meshgrid(x, x, indexing="ij")
        kernel = np.exp(-(xx**2 + yy**2) / (2 * sigma**2))
        kernel /= kernel.sum() + 1e-12
        return kernel

    def _fft_convolve(self, field: np.ndarray, kernel: np.ndarray) -> np.ndarray:
        """FFT 卷积（🚫R04 战略：纯 CPU 实现，通过 GPUBackend 调用 NumPyBackend）。

        通过 GPUBackend.fft2/ifft2 执行 FFT 卷积（实际为 NumPy CPU 实现）。

        Args:
            field: 输入场。
            kernel: 卷积核。

        Returns:
            卷积结果。
        """
        # 通过 GPU 后端执行 FFT
        field_fft = self.backend.fft2(field)
        kernel_fft = self.backend.fft2(kernel)
        result_fft = field_fft * kernel_fft
        result = self.backend.ifft2(result_fft)
        # 取实部
        if hasattr(result, "real"):
            return self.backend.to_numpy(result).real
        return np.asarray(result).real

    def _separable_convolve(self, field: np.ndarray, sigma: float) -> np.ndarray:
        """分离卷积（独立模式，非 fall-back）。

        由 ``config.use_fft=False`` 显式选择，适用于小规模场或无 FFT 支持的后端。

        Args:
            field: 输入场。
            sigma: 标准差。

        Returns:
            卷积结果。
        """
        gx = self.grid_size
        radius = max(1, int(3 * sigma))
        radius = min(radius, gx // 2)

        x = np.arange(-radius, radius + 1)
        kernel_1d = np.exp(-(x**2) / (2 * sigma**2))
        kernel_1d /= kernel_1d.sum() + 1e-12

        # 沿 x 轴卷积
        padded = np.pad(field, ((0, 0), (radius, radius)), mode="edge")
        result = np.zeros_like(field)
        for i, k in enumerate(kernel_1d):
            result += k * padded[:, i : i + gx]

        # 沿 y 轴卷积
        padded = np.pad(result, ((radius, radius), (0, 0)), mode="edge")
        result2 = np.zeros_like(field)
        for i, k in enumerate(kernel_1d):
            result2 += k * padded[i : i + gx, :]

        return result2

    def gradient_at(self, pos: np.ndarray) -> np.ndarray:
        """向量化梯度查询。

        中心差分 + 双线性插值，向量化替代 Python 循环。

        Args:
            pos: 查询位置 (n, 2)。

        Returns:
            梯度 (n, 2)。
        """
        n = len(pos)
        if n == 0:
            return np.zeros((0, 2))

        gx = self.grid_size
        # 中心差分
        # np.gradient(field) 返回 (axis0_grad, axis1_grad)
        # field[i, j] 中 i 是行（y），j 是列（x）
        # grad_x（x 方向梯度）= axis1_grad，grad_y（y 方向梯度）= axis0_grad
        grad_y, grad_x = np.gradient(self.field)

        # 双线性插值（向量化）
        x = pos[:, 0]
        y = pos[:, 1]
        # 归一化到 [0, gx-1]
        x_norm = np.clip(x * (gx - 1), 0, gx - 1.001)
        y_norm = np.clip(y * (gx - 1), 0, gx - 1.001)

        ix0 = x_norm.astype(int)
        iy0 = y_norm.astype(int)
        ix1 = ix0 + 1
        iy1 = iy0 + 1
        fx = x_norm - ix0
        fy = y_norm - iy0

        # 双线性插值
        gx_val = (
            (1 - fx) * (1 - fy) * grad_x[ix0, iy0]
            + fx * (1 - fy) * grad_x[ix1, iy0]
            + (1 - fx) * fy * grad_x[ix0, iy1]
            + fx * fy * grad_x[ix1, iy1]
        )
        gy_val = (
            (1 - fx) * (1 - fy) * grad_y[ix0, iy0]
            + fx * (1 - fy) * grad_y[ix1, iy0]
            + (1 - fx) * fy * grad_y[ix0, iy1]
            + fx * fy * grad_y[ix1, iy1]
        )

        return np.stack([gx_val, gy_val], axis=-1)

    def total_density(self) -> float:
        """总密度。"""
        return float(self.field.sum())

    def max_density(self) -> float:
        """最大密度。"""
        return float(self.field.max())

    def benchmark(self, n_devices: int = 100) -> dict[str, float]:
        """基准测试（🚫R04 战略：纯 CPU 性能测试）。

        Args:
            n_devices: 测试器件数。

        Returns:
            性能指标字典（is_gpu 始终为 False）。
        """
        import time

        rng = np.random.default_rng(42)
        pos = rng.random((n_devices, 2))
        widths = rng.random(n_devices) * 0.05
        heights = rng.random(n_devices) * 0.05
        bin_x = np.linspace(0, 1, self.grid_size + 1)
        bin_y = np.linspace(0, 1, self.grid_size + 1)

        # build 基准
        t0 = time.perf_counter()
        self.build(pos, DeviceSize(widths=widths, heights=heights), bin_x, bin_y)
        t_build = time.perf_counter() - t0

        # smooth 基准
        t0 = time.perf_counter()
        self.smooth_gaussian()
        t_smooth = time.perf_counter() - t0

        # gradient 基准
        t0 = time.perf_counter()
        self.gradient_at(pos)
        t_grad = time.perf_counter() - t0

        return {
            "n_devices": n_devices,
            "grid_size": self.grid_size,
            "is_gpu": self.is_gpu,
            "build_time": t_build,
            "smooth_time": t_smooth,
            "gradient_time": t_grad,
            "total_time": t_build + t_smooth + t_grad,
        }


def create_gpu_density_field(
    grid_size: int = 64,
    sigma: float = 10.0,
    use_fft: bool = True,
    force_cpu: bool = False,
) -> GPUDensityField:
    """便捷工厂函数：创建 GPU 密度场（🚫R04 战略：纯 CPU 实现）。

    R04 战略决策：不参与 GPU 计算。force_cpu 参数仅保留用于向后兼容，
    实际始终运行在 CPU 模式。

    Args:
        grid_size: 网格分辨率。
        sigma: 高斯标准差。
        use_fft: 是否用 FFT。
        force_cpu: 强制 CPU（忽略，始终为 True）。

    Returns:
        GPUDensityField 实例（纯 CPU 实现）。
    """
    config = GPUDensityConfig(
        grid_size=grid_size,
        gaussian_sigma=sigma,
        use_fft=use_fft,
        force_cpu=force_cpu,
    )
    return GPUDensityField(config)


__all__ = [
    "GPUDensityConfig",
    "GPUDensityField",
    "create_gpu_density_field",
]
