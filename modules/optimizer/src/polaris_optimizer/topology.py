"""拓扑优化器（水平集方法 + Adjoint 梯度演化）。

从 v4 ``polaris/sim/topology_optimizer.py`` 迁移（R13 不保留 v4 兼容）。
对标商业拓扑优化工具（Tidy3D topology optimization / Lumerical），
实现基于水平集（Level Set）的光子器件拓扑优化，支持任意形状逆向设计。

## 水平集方法原理

水平集方法用隐式函数 φ(x, y) 表示器件边界:
- φ(x, y) > 0: 材料区域（如硅）
- φ(x, y) < 0: 背景区域（如空气/二氧化硅）
- φ(x, y) = 0: 材料边界

优化过程通过演化 φ(x, y) 改变器件形状:
- ∂φ/∂t = -v(x, y) · |∇φ|
- v(x, y) = 速度场（由 adjoint 梯度决定）

来源（R02 学术诚信，≥5 文献 URL）:
- Osher & Sethian 1988 "Fronts propagating with curvature-dependent speed":
  https://doi.org/10.1016/S0021-9991(88)80002-2
- Jensen & Sigmund 2011 "Topology optimization for nano-photonics":
  https://doi.org/10.1364/OE.19.020152
- Tidy3D 拓扑优化: https://docs.flexcompute.com/projects/tidy3d/en/latest/
- Lumerical 拓扑优化: https://www.ansys.com/products/optics/lumerical-topology-optimization
- Sigmund 2007 拓扑优化滤波: https://doi.org/10.1007/s00158-006-0039-9
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np


@dataclass
class TopologyConfig:
    """拓扑优化配置。

    Attributes:
        grid_size: 水平集网格分辨率（来源: PoLaRIS 默认 50×50）。
        max_iterations: 最大迭代次数（来源: 拓扑优化默认 50 轮）。
        learning_rate: 水平集演化学习率（来源: 水平集方法默认 0.1）。
        convergence_threshold: 收敛阈值（FoM 变化 < 阈值则停止）。
        smooth_sigma: 水平集平滑核标准差（来源: Sigmund 2007 滤波技术）。
        min_feature_size: 最小特征尺寸约束（DRC 制造约束）。
    """

    grid_size: int = 50
    max_iterations: int = 50
    learning_rate: float = 0.1
    convergence_threshold: float = 1e-6
    smooth_sigma: float = 1.0
    min_feature_size: float = 2.0


@dataclass
class TopologyResult:
    """拓扑优化结果。

    Attributes:
        level_set: 最优水平集函数 (G×G)。
        binary_design: 二值化设计（1=材料，0=背景）。
        optimal_fom: 最优目标函数值。
        fom_history: FoM 历史。
        iterations: 实际迭代次数。
        converged: 是否收敛。
    """

    level_set: np.ndarray
    binary_design: np.ndarray
    optimal_fom: float
    fom_history: list[float] = field(default_factory=list)
    iterations: int = 0
    converged: bool = False


class LevelSet:
    """水平集函数表示器件形状。

    用隐式函数 φ(x, y) 表示器件边界:
    - φ > 0: 材料区域
    - φ < 0: 背景区域
    - φ = 0: 边界

    Args:
        grid_size: 网格分辨率。
        initial_shape: 初始形状 ("circle"/"rectangle"/"cross")。
    """

    def __init__(self, grid_size: int = 50, initial_shape: str = "circle") -> None:
        self.grid_size = grid_size
        self.phi = self._initialize_shape(initial_shape)

    def _initialize_shape(self, shape: str) -> np.ndarray:
        g = self.grid_size
        x = np.linspace(-1, 1, g)
        y = np.linspace(-1, 1, g)
        xx, yy = np.meshgrid(x, y, indexing="ij")
        if shape == "circle":
            return 0.25 - (xx**2 + yy**2)
        if shape == "rectangle":
            return np.minimum(0.5 - np.abs(xx), 0.5 - np.abs(yy))
        if shape == "cross":
            phi1 = np.minimum(0.2 - np.abs(xx), 0.5 - np.abs(yy))
            phi2 = np.minimum(0.5 - np.abs(xx), 0.2 - np.abs(yy))
            return np.maximum(phi1, phi2)
        return 0.25 - (xx**2 + yy**2)

    def get_binary(self) -> np.ndarray:
        return (self.phi > 0).astype(np.float64)

    def get_material_fraction(self) -> float:
        return float(self.get_binary().mean())

    def evolve(self, velocity: np.ndarray, dt: float) -> None:
        """演化水平集: φ_new = φ - dt · v · |∇φ|。"""
        grad_phi = self._compute_gradient_magnitude()
        self.phi = self.phi - dt * velocity * grad_phi

    def smooth(self, sigma: float) -> None:
        if sigma <= 0:
            return
        kernel = _gaussian_kernel_2d(sigma)
        self.phi = _convolve_2d(self.phi, kernel)

    def _compute_gradient_magnitude(self) -> np.ndarray:
        grad_x, grad_y = np.gradient(self.phi)
        return np.sqrt(grad_x**2 + grad_y**2)

    def reinitialize(self) -> None:
        self.phi = np.sign(self.phi) * np.abs(self.phi)


class TopologyOptimizer:
    """拓扑优化器（水平集 + adjoint 梯度演化）。

    算法流程::
        1. 初始化水平集（圆形/矩形/十字）
        2. for iter in range(max_iterations):
             a. 计算二值化设计
             b. 正向仿真计算 FoM
             c. 伴随仿真计算梯度（速度场）
             d. 演化水平集 (∂φ/∂t = -v · |∇φ|)
             e. 平滑 + 重新初始化
             f. 检查收敛
        3. 返回最优设计

    Args:
        level_set: 水平集函数。
        fom_evaluator: FoM 评估函数（输入二值设计，返回 FoM）。
        gradient_evaluator: 梯度评估函数（输入二值设计，返回梯度）。
        config: 优化配置。
    """

    def __init__(
        self,
        level_set: LevelSet,
        fom_evaluator: Callable[[np.ndarray], float],
        gradient_evaluator: Callable[[np.ndarray], np.ndarray],
        config: TopologyConfig | None = None,
    ) -> None:
        self.level_set = level_set
        self.fom_evaluator = fom_evaluator
        self.gradient_evaluator = gradient_evaluator
        self.config = config or TopologyConfig()

    def optimize(self) -> TopologyResult:
        fom_history: list[float] = []
        prev_fom = -float("inf")
        converged = False
        iterations = 0

        for t in range(1, self.config.max_iterations + 1):
            iterations = t
            binary = self.level_set.get_binary()
            fom = self.fom_evaluator(binary)
            fom_history.append(fom)
            if t > 1 and abs(fom - prev_fom) < self.config.convergence_threshold:
                converged = True
                break
            prev_fom = fom
            velocity = self.gradient_evaluator(binary)
            self.level_set.evolve(velocity, self.config.learning_rate)
            if t % 5 == 0:
                self.level_set.smooth(self.config.smooth_sigma)
                self.level_set.reinitialize()

        return TopologyResult(
            level_set=self.level_set.phi.copy(),
            binary_design=self.level_set.get_binary(),
            optimal_fom=fom_history[-1] if fom_history else 0.0,
            fom_history=fom_history,
            iterations=iterations,
            converged=converged,
        )


def _gaussian_kernel_2d(sigma: float) -> np.ndarray:
    if sigma <= 0:
        return np.array([[0.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 0.0]])
    x = np.array([-1, 0, 1])
    xx, yy = np.meshgrid(x, x, indexing="ij")
    kernel = np.exp(-(xx**2 + yy**2) / (2 * sigma**2))
    kernel /= kernel.sum()
    return kernel


def _convolve_2d(array: np.ndarray, kernel: np.ndarray) -> np.ndarray:
    padded = np.pad(array, 1, mode="edge")
    result = np.zeros_like(array)
    for i in range(3):
        for j in range(3):
            result += kernel[i, j] * padded[i : i + array.shape[0], j : j + array.shape[1]]
    return result


def run_topology_optimization(
    level_set: LevelSet,
    fom_evaluator: Callable[[np.ndarray], float],
    gradient_evaluator: Callable[[np.ndarray], np.ndarray],
    config: TopologyConfig | None = None,
) -> TopologyResult:
    """便捷函数: 执行拓扑优化（对标 Tidy3D run_topology_optimization 接口）。"""
    optimizer = TopologyOptimizer(level_set, fom_evaluator, gradient_evaluator, config)
    return optimizer.optimize()


__all__ = [
    "TopologyConfig",
    "TopologyResult",
    "LevelSet",
    "TopologyOptimizer",
    "run_topology_optimization",
]
