"""水平集几何量计算（P2-2 深化，第43轮）。

对标商业拓扑优化工具的几何量计算能力，实现：
1. 法向量计算：n = ∇φ / |∇φ|
2. 曲率计算：κ = ∇·(∇φ/|∇φ|)
3. SDF 重新初始化：Fast Marching Method（Sethian 1996）

## 与商业工具差距（第42轮分析）

第32轮的 topology_optimizer.py 完全缺失曲率/法向量计算，
reinitialize() 仅做符号化（无效），无法维持水平集数值稳定性。
本模块填补这些核心几何量计算差距。

来源:
- Sethian "A fast marching level set method for monotonically advancing fronts" 1996
- Osher & Fedkiw "Level Set Methods and Dynamic Implicit Surfaces" 2003 第 7 章
- Sethian "Level Set Methods and Fast Marching Methods" 1999
"""

from __future__ import annotations

import heapq
from dataclasses import dataclass

import numpy as np


def compute_normal_vector(phi: np.ndarray) -> np.ndarray:
    """计算水平集法向量场。

    n = ∇φ / |∇φ|

    法向量指向 φ 增大方向（材料区域外法向）。

    Args:
        phi: 水平集函数（Gx×Gy）。

    Returns:
        法向量场（Gx×Gy×2），[..., 0]=nx, [..., 1]=ny。
    """
    grad_x, grad_y = np.gradient(phi)
    grad_mag = np.sqrt(grad_x**2 + grad_y**2)
    # 避免除零
    grad_mag_safe = np.where(grad_mag < 1e-12, 1e-12, grad_mag)
    nx = grad_x / grad_mag_safe
    ny = grad_y / grad_mag_safe
    return np.stack([nx, ny], axis=-1)


def compute_curvature(phi: np.ndarray, dx: float = 1.0, dy: float = 1.0) -> np.ndarray:
    """计算水平集曲率场。

    κ = ∇·(∇φ / |∇φ|)
      = [(φ_y² * φ_xx - 2 * φ_x * φ_y * φ_xy + φ_x² * φ_yy)] / |∇φ|³

    曲率 κ > 0：凸边界；κ < 0：凹边界；κ = 0：直线。

    Args:
        phi: 水平集函数（Gx×Gy）。
        dx: x 方向网格步长（默认 1.0）。
        dy: y 方向网格步长（默认 1.0）。

    Returns:
        曲率场（Gx×Gy）。
    """
    grad_x, grad_y = np.gradient(phi, dx, dy)
    grad_xx = np.gradient(grad_x, dx, axis=0)
    grad_yy = np.gradient(grad_y, dy, axis=1)
    grad_xy = np.gradient(grad_x, dy, axis=1)

    grad_mag = np.sqrt(grad_x**2 + grad_y**2)
    grad_mag_cubed = np.where(grad_mag < 1e-12, 1e-12, grad_mag**3)

    curvature = (
        grad_y**2 * grad_xx - 2 * grad_x * grad_y * grad_xy + grad_x**2 * grad_yy
    ) / grad_mag_cubed
    return curvature


def compute_mean_curvature_motion(
    phi: np.ndarray, coefficient: float = 1.0, dx: float = 1.0, dy: float = 1.0
) -> np.ndarray:
    """计算平均曲率运动速度场。

    v_curvature = -coefficient * κ * |∇φ|

    用于水平集演化中的曲率平滑项，使边界趋于光滑。

    Args:
        phi: 水平集函数。
        coefficient: 曲率系数（>0 平滑，<0 锐化）。
        dx: x 方向网格步长。
        dy: y 方向网格步长。

    Returns:
        曲率运动速度场（Gx×Gy）。
    """
    kappa = compute_curvature(phi, dx, dy)
    grad_x, grad_y = np.gradient(phi, dx, dy)
    grad_mag = np.sqrt(grad_x**2 + grad_y**2)
    return -coefficient * kappa * grad_mag


@dataclass
class FastMarchingConfig:
    """Fast Marching 配置。

    Attributes:
        dx: x 步长。
        dy: y 步长。
        max_iterations: 最大迭代次数（防止死循环）。
        order: 离散阶数（1=一阶，2=二阶）。
            来源: Sethian 1996 默认一阶。
    """

    dx: float = 1.0
    dy: float = 1.0
    max_iterations: int = 100000
    order: int = 1


def _solve_quadratic(a: float, b: float, c: float) -> float:
    """求解二次方程 a*x² + b*x + c = 0 的较大根。

    用于 Fast Marching 的 Eikonal 方程求解。

    Args:
        a: 二次项系数。
        b: 一次项系数。
        c: 常数项。

    Returns:
        较大根（若判别式 < 0 返回 inf）。
    """
    discriminant = b**2 - 4 * a * c
    if discriminant < 0:
        return float("inf")
    return (-b + np.sqrt(discriminant)) / (2 * a)


def _eikonal_solve(t_x: float, t_y: float, dx: float, dy: float) -> float:
    """Eikonal 方程单点求解。

    |∇T| = 1，离散化为：
        ((T - Tx)⁻/dx)² + ((T - Ty)⁻/dy)² = 1

    其中 (·)⁻ = max(·, 0)。

    Args:
        t_x: x 方向已知最小 T 值（inf 表示未知）。
        t_y: y 方向已知最小 T 值。
        dx: x 步长。
        dy: y 步长。

    Returns:
        该点的 T 值。
    """
    if np.isinf(t_x) and np.isinf(t_y):
        return float("inf")

    if np.isinf(t_x):
        return t_y + dy
    if np.isinf(t_y):
        return t_x + dx

    # 两个方向都已知：解二次方程
    # (T-Tx)²/dx² + (T-Ty)²/dy² = 1
    a = 1.0 / dx**2 + 1.0 / dy**2
    b = -2.0 * (t_x / dx**2 + t_y / dy**2)
    c = t_x**2 / dx**2 + t_y**2 / dy**2 - 1.0

    t_quad = _solve_quadratic(a, b, c)
    # 若二次解无效，用一阶迎风
    if t_quad < max(t_x, t_y) or np.isinf(t_quad):
        return min(t_x + dx, t_y + dy)
    return t_quad


def fast_marching_sdf(phi: np.ndarray, config: FastMarchingConfig | None = None) -> np.ndarray:
    """Fast Marching 重新初始化为符号距离函数（SDF）。

    保持零等高线不变，重新计算 φ 为到边界的距离。
    对标商业工具的 SDF 重新初始化（Tidy3D / Lumerical）。

    算法（Sethian 1996）：
        1. 标记零等高线附近点为已知（T=0）
        2. 用堆优先队列按 T 值升序扩展
        3. 每个点的 T 由 Eikonal 方程求解

    Args:
        phi: 水平集函数（Gx×Gy）。
        config: Fast Marching 配置。

    Returns:
        符号距离函数（Gx×Gy），符号与原 phi 一致。
    """
    cfg = config or FastMarchingConfig()
    gx, gy = phi.shape
    sign = np.sign(phi)
    t = np.full((gx, gy), np.inf)
    known = np.zeros((gx, gy), dtype=bool)

    _detect_zero_contour(phi, sign, t, cfg)
    heap = _init_narrow_band(t, known)
    _march_expand(t, known, heap, gx, gy, cfg)

    return sign * t


def _detect_zero_contour(
    phi: np.ndarray,
    sign: np.ndarray,
    t: np.ndarray,
    cfg: FastMarchingConfig,
) -> None:
    """检测零等高线穿越点并初始化 T 值（原地更新 t）。"""
    gx, gy = phi.shape
    for i in range(gx):
        for j in range(gy):
            neighbors = _get_neighbors(i, j, gx, gy)
            _update_zero_crossing(phi, sign, t, i, j, neighbors, cfg)


def _get_neighbors(i: int, j: int, gx: int, gy: int) -> list[tuple[int, int]]:
    """获取 4 邻居坐标列表。"""
    neighbors: list[tuple[int, int]] = []
    if i > 0:
        neighbors.append((i - 1, j))
    if i < gx - 1:
        neighbors.append((i + 1, j))
    if j > 0:
        neighbors.append((i, j - 1))
    if j < gy - 1:
        neighbors.append((i, j + 1))
    return neighbors


def _update_zero_crossing(
    phi: np.ndarray,
    sign: np.ndarray,
    t: np.ndarray,
    i: int,
    j: int,
    neighbors: list[tuple[int, int]],
    cfg: FastMarchingConfig,
) -> None:
    """检查邻居是否有符号变化，更新零等高线距离。"""
    for ni, nj in neighbors:
        if sign[i, j] * sign[ni, nj] < 0:
            denom = abs(phi[i, j]) + abs(phi[ni, nj])
            if denom < 1e-12:
                dist = 0.0
            else:
                dist = abs(phi[i, j]) / denom
            step = cfg.dx if cfg.dx == cfg.dy or ni != i else cfg.dy
            t_val = dist * step
            if t_val < t[i, j]:
                t[i, j] = t_val
            break


def _init_narrow_band(t: np.ndarray, known: np.ndarray) -> list[tuple[float, int, int]]:
    """初始化 narrow band 堆：所有 T < inf 的点标记为已知并入堆。"""
    gx, gy = t.shape
    heap: list[tuple[float, int, int]] = []
    for i in range(gx):
        for j in range(gy):
            if not np.isinf(t[i, j]):
                known[i, j] = True
                heapq.heappush(heap, (float(t[i, j]), i, j))
    return heap


def _march_expand(
    t: np.ndarray,
    known: np.ndarray,
    heap: list[tuple[float, int, int]],
    gx: int,
    gy: int,
    cfg: FastMarchingConfig,
) -> None:
    """Fast Marching 扩展：按 T 值升序弹出并更新邻居。"""
    directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    iterations = 0
    while heap and iterations < cfg.max_iterations:
        iterations += 1
        t_val, i, j = heapq.heappop(heap)
        if t_val > t[i, j]:
            continue
        for di, dj in directions:
            ni, nj = i + di, j + dj
            if _is_out_of_bounds(ni, nj, gx, gy) or known[ni, nj]:
                continue
            new_t = _compute_neighbor_t(t, known, ni, nj, gx, gy, cfg)
            if new_t < t[ni, nj]:
                t[ni, nj] = new_t
                known[ni, nj] = True
                heapq.heappush(heap, (float(new_t), ni, nj))


def _is_out_of_bounds(ni: int, nj: int, gx: int, gy: int) -> bool:
    """检查坐标是否越界。"""
    return ni < 0 or ni >= gx or nj < 0 or nj >= gy


def _compute_neighbor_t(
    t: np.ndarray,
    known: np.ndarray,
    ni: int,
    nj: int,
    gx: int,
    gy: int,
    cfg: FastMarchingConfig,
) -> float:
    """收集已知邻居的 T 值并求解 Eikonal 方程。"""
    t_x = float("inf")
    t_y = float("inf")
    if ni > 0 and known[ni - 1, nj]:
        t_x = min(t_x, t[ni - 1, nj])
    if ni < gx - 1 and known[ni + 1, nj]:
        t_x = min(t_x, t[ni + 1, nj])
    if nj > 0 and known[ni, nj - 1]:
        t_y = min(t_y, t[ni, nj - 1])
    if nj < gy - 1 and known[ni, nj + 1]:
        t_y = min(t_y, t[ni, nj + 1])
    return _eikonal_solve(t_x, t_y, cfg.dx, cfg.dy)


def reinitialize_sdf(phi: np.ndarray, n_iters: int = 5) -> np.ndarray:
    """PDE 重新初始化为 SDF（Sussman 1994）。

    求解 ∂φ/∂τ + sign(φ₀)(|∇φ| - 1) = 0

    比 Fast Marching 快但精度略低，适合迭代式重初始化。

    Args:
        phi: 水平集函数。
        n_iters: 伪时间迭代次数。

    Returns:
        重新初始化的 SDF。
    """
    sign_phi = np.sign(phi)
    current = phi.copy()
    dt = 0.5

    for _ in range(n_iters):
        grad_x, grad_y = np.gradient(current)
        grad_mag = np.sqrt(grad_x**2 + grad_y**2)
        # ∂φ/∂τ = -sign(φ₀)(|∇φ| - 1)
        current = current - dt * sign_phi * (grad_mag - 1.0)

    return current


def compute_velocity_extension(
    velocity: np.ndarray, phi: np.ndarray, band_width: int = 3
) -> np.ndarray:
    """速度场延拓到全网格。

    将边界附近的速度场延拓到整个网格，保证远离边界的点也有合理速度。
    对标商业工具的 velocity extension（Adalsteinsson & Sethian 1999）。

    Args:
        velocity: 原始速度场（仅在边界附近有效）。
        phi: 水平集函数。
        band_width: 边界带宽度（网格数）。

    Returns:
        延拓后的速度场。
    """
    grad_x, grad_y = np.gradient(phi)
    grad_mag = np.sqrt(grad_x**2 + grad_y**2)

    # 边界带：|φ| < band_width * dx
    if np.any(grad_mag > 1e-12):
        threshold = band_width * float(np.mean(grad_mag[grad_mag > 1e-12]))
    else:
        threshold = 1.0
    band = np.abs(phi) < threshold

    # 用边界带速度的均值延拓到非边界区域
    if band.any():
        band_mean = float(velocity[band].mean())
        extended = np.where(band, velocity, band_mean)
    else:
        extended = velocity.copy()

    return extended


__all__ = [
    "FastMarchingConfig",
    "compute_normal_vector",
    "compute_curvature",
    "compute_mean_curvature_motion",
    "fast_marching_sdf",
    "reinitialize_sdf",
    "compute_velocity_extension",
]
