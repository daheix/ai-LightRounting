"""制造可行性约束（第35轮 P2-2 深化）。

实现拓扑优化的制造约束，对标 Tidy3D/Lumerical 制造可行性模块：
1. **密度惩罚**：惩罚中间密度（0-1 之间的灰度），促进二值化
2. **投影约束**：使用 sigmoid/tanh 投影将密度推向 0 或 1
3. **最小特征尺寸约束**：滤波 + 投影实现最小特征尺寸
4. **连通性约束**：检测并惩罚孤立区域

## 商业差距

P2-2 拓扑优化深化：
- 商业标杆：Tidy3D topology optimization 制造约束
- 本模块实现制造可行性约束，避免生成不可制造的结构

## 来源

- Sigmund 2007 "Morphology-based black and white filters..."
  https://link.springer.com/article/10.1007/s00158-007-0198-x
- Wang et al. 2011 "Projection-based aggregation in topology optimization"
  https://onlinelibrary.wiley.com/doi/10.1002/nme.3122
- Lazarov & Sigmund 2011 "Filters in topology optimization"
  https://onlinelibrary.wiley.com/doi/10.1002/nme.3120
- Tidy3D topology optimization: https://docs.flexcompute.com/projects/tidy3d/en/latest/
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class FabricationConfig:
    """制造约束配置。

    Attributes:
        min_feature_size: 最小特征尺寸（网格单位）。
            来源: DRC 制造约束，典型值 2-5 网格单位。
        density_penalty_weight: 密度惩罚权重。
            来源: Sigmund 2007，典型值 0.01-0.1。
        projection_strength: 投影强度（β）。
            来源: Wang 2011，典型值 1-20。
        filter_sigma: 密度滤波核标准差。
            来源: Lazarov & Sigmund 2011，典型值 1-3。
        connectivity_threshold: 连通性检测阈值。
        max_iterations: 约束迭代次数。
    """

    min_feature_size: float = 2.0
    density_penalty_weight: float = 0.05
    projection_strength: float = 5.0
    filter_sigma: float = 1.5
    connectivity_threshold: int = 3
    max_iterations: int = 10


@dataclass
class ConstraintMetrics:
    """约束指标。

    Attributes:
        density_penalty: 密度惩罚值（越低越好）。
        grayness: 灰度值（0=完全二值化，1=完全灰度）。
        min_feature_violation: 最小特征尺寸违反数。
        connectivity_violation: 连通性违反数。
        total_violation: 总违反量。
    """

    density_penalty: float = 0.0
    grayness: float = 0.0
    min_feature_violation: int = 0
    connectivity_violation: int = 0

    @property
    def total_violation(self) -> float:
        """总违反量。"""
        return (
            self.density_penalty
            + self.min_feature_violation * 0.1
            + self.connectivity_violation * 0.1
        )


class DensityPenalty:
    """密度惩罚（促进二值化）。

    惩罚中间密度（0-1 之间的灰度），促进设计变量趋向 0 或 1。

    惩罚函数: P(ρ) = 4 * ρ * (1 - ρ)
    - ρ=0 → P=0（背景，无惩罚）
    - ρ=1 → P=0（材料，无惩罚）
    - ρ=0.5 → P=1（最大惩罚）

    来源: Sigmund 2007 "Morphology-based black and white filters"

    Args:
        weight: 惩罚权重。
    """

    def __init__(self, weight: float = 0.05) -> None:
        """初始化密度惩罚。

        Args:
            weight: 惩罚权重。
        """
        self.weight = weight

    def compute_penalty(self, density: np.ndarray) -> float:
        """计算密度惩罚值。

        Args:
            density: 密度分布（0-1）。

        Returns:
            惩罚值（越大表示灰度越多）。
        """
        return float(self.weight * np.sum(4.0 * density * (1.0 - density)))

    def compute_gradient(self, density: np.ndarray) -> np.ndarray:
        """计算密度惩罚梯度。

        dP/dρ = weight * 4 * (1 - 2ρ)

        Args:
            density: 密度分布。

        Returns:
            梯度（与 density 同形状）。
        """
        return self.weight * 4.0 * (1.0 - 2.0 * density)

    def compute_grayness(self, density: np.ndarray) -> float:
        """计算灰度值（0=完全二值化，1=完全灰度）。

        Args:
            density: 密度分布。

        Returns:
            灰度值（0-1）。
        """
        return float(np.mean(4.0 * density * (1.0 - density)))


class ProjectionConstraint:
    """投影约束（sigmoid/tanh 投影）。

    使用 sigmoid 函数将密度推向 0 或 1，实现二值化。

    投影函数: ρ_proj = sigmoid(β * (ρ - 0.5))
    - β→∞: 完全二值化（阶跃函数）
    - β=0: 无投影（ρ_proj=0.5）

    来源: Wang et al. 2011 "Projection-based aggregation"

    Args:
        strength: 投影强度 β。
    """

    def __init__(self, strength: float = 5.0) -> None:
        """初始化投影约束。

        Args:
            strength: 投影强度 β。
        """
        self.beta = strength

    def project(self, density: np.ndarray) -> np.ndarray:
        """应用投影约束。

        Args:
            density: 输入密度（0-1）。

        Returns:
            投影后密度（更接近 0 或 1）。
        """
        return _sigmoid(self.beta * (density - 0.5))

    def compute_gradient(self, density: np.ndarray) -> np.ndarray:
        """计算投影梯度。

        dρ_proj/dρ = β * sigmoid'(β*(ρ-0.5))
                   = β * sigmoid * (1 - sigmoid)

        Args:
            density: 输入密度。

        Returns:
            梯度（与 density 同形状）。
        """
        projected = self.project(density)
        return self.beta * projected * (1.0 - projected)


class DensityFilter:
    """密度滤波（最小特征尺寸约束）。

    使用高斯滤波平滑密度分布，实现最小特征尺寸约束。
    滤波后的小于 min_feature_size 的特征被平滑掉。

    来源: Lazarov & Sigmund 2011 "Filters in topology optimization"

    Args:
        sigma: 滤波核标准差（网格单位）。
    """

    def __init__(self, sigma: float = 1.5) -> None:
        """初始化密度滤波。

        Args:
            sigma: 滤波核标准差。
        """
        self.sigma = sigma

    def filter(self, density: np.ndarray) -> np.ndarray:
        """应用高斯滤波。

        Args:
            density: 输入密度。

        Returns:
            滤波后密度。
        """
        if self.sigma <= 0:
            return density.copy()
        kernel = _gaussian_kernel_2d_extended(self.sigma)
        return _convolve_2d_extended(density, kernel)

    def compute_gradient(self, density: np.ndarray) -> np.ndarray:
        """计算滤波梯度（线性，梯度=滤波核卷积）。

        Args:
            density: 输入密度。

        Returns:
            梯度（与 density 同形状）。
        """
        return self.filter(density)


class ConnectivityConstraint:
    """连通性约束（检测孤立区域）。

    检测密度分布中的孤立区域，惩罚不连通的设计。

    来源: Tidy3D topology optimization connectivity

    Args:
        threshold: 连通性检测阈值（网格单位）。
    """

    def __init__(self, threshold: int = 3) -> None:
        """初始化连通性约束。

        Args:
            threshold: 连通性检测阈值。
        """
        self.threshold = threshold

    def count_isolated_regions(self, density: np.ndarray) -> int:
        """统计孤立区域数量。

        Args:
            density: 密度分布（二值化后）。

        Returns:
            孤立区域数量。
        """
        binary = (density > 0.5).astype(np.int32)
        if binary.size == 0 or binary.sum() == 0:
            return 0
        visited = np.zeros_like(binary, dtype=bool)
        regions = 0
        for i in range(binary.shape[0]):
            for j in range(binary.shape[1]):
                if binary[i, j] == 1 and not visited[i, j]:
                    self._flood_fill(binary, visited, i, j)
                    regions += 1
        # 主区域 = 最大连通区域，孤立区域 = regions - 1
        return max(0, regions - 1)

    def _flood_fill(
        self,
        binary: np.ndarray,
        visited: np.ndarray,
        start_i: int,
        start_j: int,
    ) -> None:
        """洪水填充标记连通区域。

        Args:
            binary: 二值化数组。
            visited: 访问标记数组。
            start_i: 起始行。
            start_j: 起始列。
        """
        stack = [(start_i, start_j)]
        while stack:
            i, j = stack.pop()
            if i < 0 or i >= binary.shape[0]:
                continue
            if j < 0 or j >= binary.shape[1]:
                continue
            if visited[i, j] or binary[i, j] == 0:
                continue
            visited[i, j] = True
            stack.extend([(i + 1, j), (i - 1, j), (i, j + 1), (i, j - 1)])

    def compute_violation(self, density: np.ndarray) -> int:
        """计算连通性违反数。

        Args:
            density: 密度分布。

        Returns:
            孤立区域数量。
        """
        return self.count_isolated_regions(density)


class FabricationConstraints:
    """制造约束集合（密度惩罚 + 投影 + 滤波 + 连通性）。

    对标 Tidy3D/Lumerical 制造可行性模块，集成所有制造约束。

    来源:
    - Sigmund 2007 密度惩罚
    - Wang 2011 投影约束
    - Lazarov & Sigmund 2011 密度滤波
    - Tidy3D 制造约束

    Args:
        config: 制造约束配置。
    """

    def __init__(self, config: FabricationConfig | None = None) -> None:
        """初始化制造约束集合。

        Args:
            config: 配置（None 用默认）。
        """
        self.config = config or FabricationConfig()
        self.density_penalty = DensityPenalty(self.config.density_penalty_weight)
        self.projection = ProjectionConstraint(self.config.projection_strength)
        self.density_filter = DensityFilter(self.config.filter_sigma)
        self.connectivity = ConnectivityConstraint(self.config.connectivity_threshold)

    def apply_constraints(self, density: np.ndarray) -> np.ndarray:
        """应用所有制造约束。

        流程:
        1. 密度滤波（最小特征尺寸）
        2. 投影约束（二值化）
        3. 裁剪到 [0, 1]

        Args:
            density: 输入密度。

        Returns:
            约束后密度。
        """
        filtered = self.density_filter.filter(density)
        projected = self.projection.project(filtered)
        return np.clip(projected, 0.0, 1.0)

    def compute_total_penalty(self, density: np.ndarray) -> float:
        """计算总惩罚值。

        Args:
            density: 密度分布。

        Returns:
            总惩罚值。
        """
        return self.density_penalty.compute_penalty(density)

    def compute_total_gradient(self, density: np.ndarray) -> np.ndarray:
        """计算总惩罚梯度。

        Args:
            density: 密度分布。

        Returns:
            总梯度。
        """
        return self.density_penalty.compute_gradient(density)

    def evaluate(self, density: np.ndarray) -> ConstraintMetrics:
        """评估所有约束指标。

        Args:
            density: 密度分布。

        Returns:
            约束指标。
        """
        return ConstraintMetrics(
            density_penalty=self.density_penalty.compute_penalty(density),
            grayness=self.density_penalty.compute_grayness(density),
            min_feature_violation=self._count_min_feature_violations(density),
            connectivity_violation=self.connectivity.compute_violation(density),
        )

    def _count_min_feature_violations(self, density: np.ndarray) -> int:
        """统计最小特征尺寸违反数。

        检测小于 min_feature_size 的孤立材料区域。

        Args:
            density: 密度分布。

        Returns:
            违反数。
        """
        binary = (density > 0.5).astype(np.int32)
        violations = 0
        min_size = int(self.config.min_feature_size)
        visited = np.zeros_like(binary, dtype=bool)
        for i in range(binary.shape[0]):
            for j in range(binary.shape[1]):
                if binary[i, j] == 1 and not visited[i, j]:
                    region_size = self._flood_fill_count(binary, visited, i, j)
                    if region_size < min_size:
                        violations += 1
        return violations

    def _flood_fill_count(
        self,
        binary: np.ndarray,
        visited: np.ndarray,
        start_i: int,
        start_j: int,
    ) -> int:
        """洪水填充统计连通区域大小。

        Args:
            binary: 二值化数组。
            visited: 访问标记数组。
            start_i: 起始行。
            start_j: 起始列。

        Returns:
            区域大小。
        """
        count = 0
        stack = [(start_i, start_j)]
        while stack:
            i, j = stack.pop()
            if i < 0 or i >= binary.shape[0]:
                continue
            if j < 0 or j >= binary.shape[1]:
                continue
            if visited[i, j] or binary[i, j] == 0:
                continue
            visited[i, j] = True
            count += 1
            stack.extend([(i + 1, j), (i - 1, j), (i, j + 1), (i, j - 1)])
        return count


def _sigmoid(x: np.ndarray) -> np.ndarray:
    """数值稳定的 sigmoid 函数。

    Args:
        x: 输入数组。

    Returns:
        sigmoid 值（0-1）。
    """
    return np.where(
        x >= 0,
        1.0 / (1.0 + np.exp(-np.clip(x, -500, 500))),
        np.exp(np.clip(x, -500, 500))
        / (1.0 + np.exp(np.clip(x, -500, 500))),
    )


def _gaussian_kernel_2d_extended(sigma: float) -> np.ndarray:
    """构建 2D 高斯核（自适应大小）。

    核大小 = 2 * ceil(3 * sigma) + 1

    Args:
        sigma: 标准差。

    Returns:
        2D 高斯核（归一化）。
    """
    if sigma <= 0:
        return np.array([[1.0]])
    radius = max(1, int(np.ceil(3 * sigma)))
    x = np.arange(-radius, radius + 1, dtype=np.float64)
    xx, yy = np.meshgrid(x, x, indexing="ij")
    kernel = np.exp(-(xx**2 + yy**2) / (2 * sigma**2))
    kernel /= kernel.sum()
    return kernel


def _convolve_2d_extended(array: np.ndarray, kernel: np.ndarray) -> np.ndarray:
    """2D 卷积（边界 edge 填充，自适应核大小）。

    Args:
        array: 输入数组。
        kernel: 卷积核。

    Returns:
        卷积结果（同形状）。
    """
    if kernel.size == 1:
        return array * kernel[0, 0]
    k_size = kernel.shape[0]
    pad = k_size // 2
    padded = np.pad(array, pad, mode="edge")
    result = np.zeros_like(array, dtype=np.float64)
    for i in range(k_size):
        for j in range(k_size):
            result += kernel[i, j] * padded[i : i + array.shape[0], j : j + array.shape[1]]
    return result


def create_fabrication_constraints(
    config: FabricationConfig | None = None,
) -> FabricationConstraints:
    """创建制造约束集合工厂函数。

    Args:
        config: 配置（None 用默认）。

    Returns:
        FabricationConstraints 实例。
    """
    return FabricationConstraints(config=config)


__all__ = [
    "FabricationConfig",
    "ConstraintMetrics",
    "DensityPenalty",
    "ProjectionConstraint",
    "DensityFilter",
    "ConnectivityConstraint",
    "FabricationConstraints",
    "create_fabrication_constraints",
]
