"""GDS/OASIS 曲线离散化与样条曲线生成（polaris-gds-tools 子模块）。

v5.0 R11 路标任务：GDS/OASIS 导出精度提升（1nm 曲线离散化 + 样条曲线）。

本模块为版图导出提供亚微米级曲线精度保障：将任意参数化曲线函数按
1nm 弧长步长离散化为折线路径，并提供 B-spline（de Boor 算法）与
Catmull-Rom 样条曲线生成，供 GDSII/OASIS PATH 元素写入使用。

=== Input / Process / Output 三段式文档 ===

Input:
- discretize_curve_1nm: 参数化曲线函数 curve_func(t) -> (x, y)，
    参数 t ∈ [start, end]（μm 单位），容差 tol_um（默认 0.001μm = 1nm）。
- bspline_curve: 控制点数组 (N, 2)，阶数 degree（默认 3 三次），采样数 n_points。
- catmull_rom_spline: 控制点数组 (N, 2)，采样数 n_points（过所有控制点的插值样条）。
- discretize_to_gds_path: 参数化曲线函数 + dbu_um（默认 0.001μm = 1nm GDS dbu）。

Process:
- 1nm 弧长离散化: 密集参数采样 → 累积弦长弧长 → 按 tol_um 步长反插值参数 t
    → 重新求值曲线函数，保证相邻点弧长 ≈ 1nm。
- B-spline: clamped uniform 节点向量 + de Boor 递归求值（Piegl & Tiller 1997 §3.5）。
- Catmull-Rom: 4 点分段三次多项式（tension=0.5，过控制点，C¹ 连续）。
- GDS path: 1nm 离散化 → 坐标量化到 dbu 网格（round(x/dbu)*dbu）→ 去连续重复点。

Output:
- discretize_curve_1nm: (N, 2) np.ndarray，N ≈ 弧长/tol_um + 1。
- bspline_curve / catmull_rom_spline: (n_points, 2) np.ndarray。
- discretize_to_gds_path: list[tuple[float, float]]，GDS dbu 量化路径点。

学术依据（R02 学术诚信，所有算法可溯源，均经 WebSearch 验证可访问）:
- de Boor 1978, "A Practical Guide to Splines", Springer（B-spline de Boor 算法）
  https://link.springer.com/book/10.1007/978-1-4612-6332-9
- Catmull & Rom 1974, "A class of local interpolating splines",
  Computer Aided Geometric Design（Catmull-Rom 样条原始论文）
  https://www.sciencedirect.com/science/article/pii/B9780120790500500205
- SEMI P39 OASIS 规范（Open Artwork System Interchange Standard）
  https://en.wikipedia.org/wiki/Open_Artwork_System_Interchange_Standard
- GDSII 1nm dbu 标准（KLayout database unit 文档）
  https://www.klayout.org/doc/manual/database.html
- Farin 2002, "Curves and Surfaces for CAGD", Morgan Kaufmann（CAGD 经典教材）
  https://www.sciencedirect.com/books/book/curves-and-surfaces-for-cagd
- Piegl & Tiller 1997, "The NURBS Book" Springer（de Boor 算法标准实现 §3.5）
  https://link.springer.com/book/10.1007/978-3-642-59223-2

合规: R02 学术诚信 / R03 禁止 fall-back（输入无效 raise，不返回空数组）
/ R04 不参与 GPU（纯 NumPy CPU）/ R05 无 TODO/FIXME
/ 函数≤80行 / 文件≤800行。
"""

from __future__ import annotations

from typing import Callable

import numpy as np

__all__ = [
    "discretize_curve_1nm",
    "bspline_curve",
    "catmull_rom_spline",
    "discretize_to_gds_path",
]

# 默认 1nm 弧长步长（μm）。GDSII/OASIS 流片 1nm dbu 标准（KLayout database unit）。
# 来源: https://www.klayout.org/doc/manual/database.html
DEFAULT_TOL_UM = 0.001

# 默认 GDS dbu（μm），1nm 数据库单位（SEMI P39 OASIS / GDSII 流片标准）。
DEFAULT_DBU_UM = 0.001

# 弧长计算的密集参数采样数（保证累积弦长精度优于 1nm）。
_ARC_SAMPLE_N = 20000


# ---------------------------------------------------------------------------
# 1nm 弧长步长曲线离散化
# ---------------------------------------------------------------------------


def discretize_curve_1nm(
    curve_func: Callable[[float], tuple[float, float]],
    start: float,
    end: float,
    tol_um: float = DEFAULT_TOL_UM,
) -> np.ndarray:
    """按 1nm 弧长步长离散化任意参数化曲线函数。

    算法: 密集参数采样 → 累积弦长弧长 → 按 tol_um 步长反插值参数 t → 重新求值。
    保证相邻输出点的弧长 ≈ tol_um（默认 1nm）。

    Args:
        curve_func: 参数化曲线函数 t -> (x, y)，单位 μm。
        start: 参数 t 起点。
        end: 参数 t 终点（必须 > start）。
        tol_um: 弧长步长容差（μm），默认 0.001μm = 1nm。

    Returns:
        (N, 2) np.ndarray，N ≈ 总弧长 / tol_um + 1。

    Raises:
        RuntimeError: 输入无效（R03 禁止 fall-back，不返回空数组）。
    """
    if not callable(curve_func):
        raise RuntimeError(
            f"curve_func 必须可调用: {type(curve_func)}（R03 禁止 fall-back）"
        )
    if end <= start:
        raise RuntimeError(
            f"end({end}) 必须 > start({start})（R03 禁止 fall-back）"
        )
    if tol_um <= 0:
        raise RuntimeError(
            f"tol_um 必须为正: {tol_um}（R03 禁止 fall-back）"
        )

    # 1. 密集参数采样求值
    t_sample = np.linspace(start, end, _ARC_SAMPLE_N)
    pts = np.array([curve_func(t) for t in t_sample], dtype=float)
    if pts.ndim != 2 or pts.shape[1] != 2:
        raise RuntimeError(
            f"curve_func 必须返回 (x, y) 二元组，得到 shape={pts.shape}"
            f"（R03 禁止 fall-back）"
        )

    # 2. 累积弦长弧长（NumPy 向量化）
    diffs = np.diff(pts, axis=0)
    seg_len = np.sqrt(np.einsum("ij,ij->i", diffs, diffs))
    cum_len = np.concatenate([[0.0], np.cumsum(seg_len)])
    total_len = float(cum_len[-1])
    if total_len <= 0.0:
        raise RuntimeError(
            f"曲线总弧长为 0，无法离散化（R03 禁止 fall-back）"
        )

    # 3. 按 tol_um 弧长步长反插值参数 t
    n_steps = int(np.ceil(total_len / tol_um)) + 1
    target_lens = np.linspace(0.0, total_len, n_steps)
    t_out = np.interp(target_lens, cum_len, t_sample)

    # 4. 重新求值曲线函数得到等弧长采样点
    result = np.array([curve_func(float(t)) for t in t_out], dtype=float)
    return result


# ---------------------------------------------------------------------------
# B-spline 样条曲线（de Boor 算法）
# ---------------------------------------------------------------------------


def _clamped_uniform_knots(n_ctrl: int, degree: int) -> np.ndarray:
    """生成 clamped uniform 节点向量（B-spline 标准节点向量）。

    节点向量长度 = n_ctrl + degree + 1，前后各 degree+1 个为 0/1（clamped），
    中间均匀分布。来源: Piegl & Tiller 1997 §3.2 The NURBS Book。

    Args:
        n_ctrl: 控制点数。
        degree: B-spline 阶数。

    Returns:
        节点向量 (n_ctrl + degree + 1,) np.ndarray。
    """
    n_knots = n_ctrl + degree + 1
    knots = np.zeros(n_knots, dtype=float)
    n_internal = n_ctrl - degree - 1
    if n_internal > 0:
        internal = np.linspace(0.0, 1.0, n_internal + 2)[1:-1]
        knots[degree + 1:degree + 1 + n_internal] = internal
    knots[n_ctrl:] = 1.0
    return knots


def _de_boor(
    k: int, x: float, t: np.ndarray, c: np.ndarray, p: int
) -> np.ndarray:
    """de Boor 算法在参数 x 处求值 B-spline 曲线单点。

    标准 de Boor 递归（Piegl & Tiller 1997 §3.5 The NURBS Book 算法 A2.4）。

    Args:
        k: x 所在节点区间索引（t[k] <= x < t[k+1]）。
        x: 参数值。
        t: 节点向量。
        c: 控制点 (n_ctrl, dim)。
        p: 阶数。

    Returns:
        曲线在 x 处的点 (dim,) np.ndarray。
    """
    d = np.array([c[j + k - p] for j in range(p + 1)], dtype=float)
    for r in range(1, p + 1):
        for j in range(p, r - 1, -1):
            denom = float(t[j + 1 + k - r] - t[j + k - p])
            if denom == 0.0:
                raise RuntimeError(
                    f"de Boor 节点重复导致除零（R03 禁止 fall-back）"
                )
            alpha = (x - t[j + k - p]) / denom
            d[j] = (1.0 - alpha) * d[j - 1] + alpha * d[j]
    return d[p]


def _find_span(x: float, t: np.ndarray, n_ctrl: int, p: int) -> int:
    """定位参数 x 所在的节点区间索引 k（t[k] <= x < t[k+1]）。

    clamped B-spline 末端处理: x == 1.0 时返回 n_ctrl - 1。
    来源: Piegl & Tiller 1997 §3.1 FindSpan 算法。

    Args:
        x: 参数值 ∈ [0, 1]。
        t: 节点向量。
        n_ctrl: 控制点数。
        p: 阶数。

    Returns:
        节点区间索引 k。
    """
    if x >= t[n_ctrl]:
        return n_ctrl - 1
    if x <= t[p]:
        return p
    low, high = p, n_ctrl
    mid = (low + high) // 2
    while x < t[mid] or x >= t[mid + 1]:
        if x < t[mid]:
            high = mid
        else:
            low = mid
        mid = (low + high) // 2
    return mid


def bspline_curve(
    points: np.ndarray,
    degree: int = 3,
    n_points: int = 100,
) -> np.ndarray:
    """B-spline 样条曲线（de Boor 算法）。

    使用 clamped uniform 节点向量，曲线首末端点经过首末控制点。
    算法来源: de Boor 1978 / Piegl & Tiller 1997 The NURBS Book §3.5。

    Args:
        points: 控制点数组 (N, 2)，N 必须 > degree。
        degree: B-spline 阶数（默认 3 三次）。
        n_points: 采样点数（默认 100）。

    Returns:
        (n_points, 2) np.ndarray 采样曲线点。

    Raises:
        RuntimeError: 输入无效（R03 禁止 fall-back）。
    """
    ctrl = np.asarray(points, dtype=float)
    if ctrl.ndim != 2 or ctrl.shape[1] != 2:
        raise RuntimeError(
            f"points 必须为 (N, 2) 数组，得到 shape={ctrl.shape}"
            f"（R03 禁止 fall-back）"
        )
    n_ctrl = ctrl.shape[0]
    if n_ctrl < 2:
        raise RuntimeError(
            f"控制点数必须 >= 2: {n_ctrl}（R03 禁止 fall-back）"
        )
    if degree < 1 or degree >= n_ctrl:
        raise RuntimeError(
            f"degree 须满足 1 <= degree < n_ctrl({n_ctrl}): degree={degree}"
            f"（R03 禁止 fall-back）"
        )
    if n_points < 2:
        raise RuntimeError(
            f"n_points 必须 >= 2: {n_points}（R03 禁止 fall-back）"
        )

    knots = _clamped_uniform_knots(n_ctrl, degree)
    t_eval = np.linspace(0.0, 1.0, n_points)
    result = np.empty((n_points, 2), dtype=float)
    for i, x in enumerate(t_eval):
        k = _find_span(float(x), knots, n_ctrl, degree)
        result[i] = _de_boor(k, float(x), knots, ctrl, degree)
    return result


# ---------------------------------------------------------------------------
# Catmull-Rom 样条曲线
# ---------------------------------------------------------------------------


def _catmull_rom_segment(
    p0: np.ndarray, p1: np.ndarray, p2: np.ndarray, p3: np.ndarray,
    t: float,
) -> np.ndarray:
    """Catmull-Rom 单段三次多项式求值（tension=0.5，过 p1/p2）。

    标准公式来源: Catmull & Rom 1974。对 t ∈ [0, 1] 在 p1→p2 段求值。

    Args:
        p0/p1/p2/p3: 4 个控制点（dim,）。
        t: 段内参数 ∈ [0, 1]。

    Returns:
        段内点 (dim,) np.ndarray。
    """
    t2 = t * t
    t3 = t2 * t
    return 0.5 * (
        (2.0 * p1)
        + (-p0 + p2) * t
        + (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3) * t2
        + (-p0 + 3.0 * p1 - 3.0 * p2 + p3) * t3
    )


def catmull_rom_spline(
    points: np.ndarray,
    n_points: int = 100,
) -> np.ndarray:
    """Catmull-Rom 样条曲线（过所有控制点的插值样条，C¹ 连续）。

    使用端点镜像（phantom 控制点）保证曲线经过首末控制点。
    算法来源: Catmull & Rom 1974 / Farin 2002 CAGD §5.4。

    Args:
        points: 控制点数组 (N, 2)，N 必须 >= 2。
        n_points: 采样点数（默认 100）。

    Returns:
        (n_points, 2) np.ndarray 采样曲线点。

    Raises:
        RuntimeError: 输入无效（R03 禁止 fall-back）。
    """
    ctrl = np.asarray(points, dtype=float)
    if ctrl.ndim != 2 or ctrl.shape[1] != 2:
        raise RuntimeError(
            f"points 必须为 (N, 2) 数组，得到 shape={ctrl.shape}"
            f"（R03 禁止 fall-back）"
        )
    n_ctrl = ctrl.shape[0]
    if n_ctrl < 2:
        raise RuntimeError(
            f"控制点数必须 >= 2: {n_ctrl}（R03 禁止 fall-back）"
        )
    if n_points < 2:
        raise RuntimeError(
            f"n_points 必须 >= 2: {n_points}（R03 禁止 fall-back）"
        )

    # 端点镜像（phantom 点）：保证曲线过首末控制点
    p0_ext = 2.0 * ctrl[0] - ctrl[1]
    p_last_ext = 2.0 * ctrl[-1] - ctrl[-2]
    ext = np.vstack([p0_ext, ctrl, p_last_ext])

    n_seg = n_ctrl - 1
    pts_per_seg = max(1, n_points // n_seg)
    out: list[np.ndarray] = []
    for i in range(n_seg):
        a, b, c, d = ext[i], ext[i + 1], ext[i + 2], ext[i + 3]
        seg_t = np.linspace(0.0, 1.0, pts_per_seg, endpoint=(i == n_seg - 1))
        for t in seg_t:
            out.append(_catmull_rom_segment(a, b, c, d, float(t)))

    result = np.array(out, dtype=float)
    # 保证恰好返回 n_points 个点（重采样）
    if result.shape[0] != n_points:
        idx = np.linspace(0, result.shape[0] - 1, n_points).astype(int)
        result = result[idx]
    return result


# ---------------------------------------------------------------------------
# 1nm dbu 精度 GDS 路径点
# ---------------------------------------------------------------------------


def discretize_to_gds_path(
    curve_func: Callable[[float], tuple[float, float]],
    start: float,
    end: float,
    dbu_um: float = DEFAULT_DBU_UM,
) -> list[tuple[float, float]]:
    """1nm dbu 精度 GDS/OASIS 路径点。

    按 dbu_um（默认 1nm）弧长步长离散化曲线，并将坐标量化到 dbu 网格，
    去除连续重复点（GDSII PATH 元素不允许连续相同坐标）。

    来源: SEMI P39 OASIS / GDSII 1nm dbu 标准
      https://en.wikipedia.org/wiki/Open_Artwork_System_Interchange_Standard
      https://www.klayout.org/doc/manual/database.html

    Args:
        curve_func: 参数化曲线函数 t -> (x, y)，单位 μm。
        start: 参数 t 起点。
        end: 参数 t 终点（必须 > start）。
        dbu_um: GDS 数据库单位（μm），默认 0.001μm = 1nm。

    Returns:
        list[tuple[float, float]]，dbu 量化后的路径点。

    Raises:
        RuntimeError: 输入无效（R03 禁止 fall-back）。
    """
    if dbu_um <= 0:
        raise RuntimeError(
            f"dbu_um 必须为正: {dbu_um}（R03 禁止 fall-back）"
        )

    # 复用 1nm 弧长离散化（步长 = dbu）
    pts = discretize_curve_1nm(curve_func, start, end, tol_um=dbu_um)

    # 量化到 dbu 网格: round(x / dbu) * dbu
    quantized = np.round(pts / dbu_um).astype(np.int64) * dbu_um

    # 去除连续重复点（GDSII PATH 不允许）
    result: list[tuple[float, float]] = []
    prev = None
    for x, y in quantized:
        key = (float(x), float(y))
        if key != prev:
            result.append(key)
            prev = key
    if len(result) < 2:
        raise RuntimeError(
            f"dbu 量化后路径点数 < 2: {len(result)}（R03 禁止 fall-back）"
        )
    return result
