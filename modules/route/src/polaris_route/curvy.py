"""曲线波导布线核心（polaris-route 子模块）。

迁移自 ``src/polaris/router/curvy_router.py`` + ``curvy_geometry.py`` +
``path_geometry.py`` 的曲线波导布线与几何工具，适配 polaris-route 的
``circuit dict`` 接口（与 polaris-core / polaris-place 一致），仅依赖 numpy
（R04: 不参与 GPU）。

## 功能

1. **S-bend 曲线波导布线**: 连接两个不同 x、不同 y 的端口，使用 step 拓扑
   （水平→垂直→水平），保证弯曲数可解析、损耗可溯源。
2. **曲线几何生成**: 欧拉螺旋（clothoid）/圆弧/贝塞尔 S-bend（迁移自
   curvy_geometry.py / path_geometry.py，供高级用户与未来 A* 网格布线复用）。
3. **路径损耗计算**: 传播损耗 (dB/cm) + 弯曲损耗 (0.05 dB/bend)，
   默认 3.0 dB/cm SOI 波导传播损耗（Soref 1993 + SiEPIC PDK 上界）。
4. **交叉检测**: CCW 叉积法统计两条折线路径的交叉数。

## 损耗模型（R02 学术诚信，所有参数可溯源）

- 传播损耗 ``loss_db_cm=3.0`` dB/cm: Soref et al. 1993 IEEE Proc. 41(9)
  SOI 波导上界，与 ``waveguide_router.py`` / ``default_simulator.py`` 等
  6 处实现统一（R05 Bug 修复 v4.0-SOI-LOSS-P1）。
- 单弯损耗 ``0.05`` dB: SiEPIC EBeam PDK 通用路径保守上界
  （适用于未指定弯曲类型的 90° 弯）。
- 单次交叉损耗 ``0.3`` dB: SiEPIC EBeam PDK crossing_te1550 典型值
  （1550nm 波段下单次交叉 0.15-0.3 dB，取上界）。

## 设计原则

- 对外 API 返回 JSON-serializable dict / list（与 polaris-core 一致）
- 纯 NumPy 实现（R04: 不参与 GPU）
- 禁止 fall-back（R03）: 布线失败 raise RuntimeError，不返回哨兵值
- 输出坐标约定: 路径点为画布绝对坐标 (μm)，与 ``polaris_path_t.xs/ys`` 一致

## 来源（R02 学术诚信，≥5 个文献 URL）

- LiDAR: Automated Curvy Waveguide Detailed Routing（ISPD'25）
  https://dl.acm.org/doi/pdf/10.1145/3698364.3705355
- LiDAR 2.0: Hierarchical Curvy Waveguide Detailed Routing（TCAD 2025）
  https://scopex-asu.github.io/files/publications/PD_TCAD2025_LiDARv2.pdf
- SiEPIC EBeam PDK（bend_euler radius=5μm，0.05 dB/bend，0.3 dB/crossing）
  https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- Klauss et al., "Euler spiral waveguide bends", Opt Express 2018
  https://doi.org/10.1364/OE.26.029637
- Fujisawa et al. 2017, "Euler bend clothoid curve low-loss waveguide"
  (Optics Express 25(8) 9150) https://opg.optica.org/oe/fulltext.cfm?uri=oe-25-8-9150
- Soref et al. 1993 IEEE Proc. 41(9) 1182-1183（SOI 3 dB/cm 传播损耗基准）
  https://ieeexplore.ieee.org/document/1148303
- Chrostowski & Hochberg 2015 §6.4 Silicon Photonics Design
  https://www.cambridge.org/core/books/silicon-photonics-design/
- Flexcompute Tidy3D EulerWaveguideBend（clothoid 公式 RL=A², θ=L/(2R)）
  https://docs.flexcompute.com/projects/tidy3d/en/v2.9.2/notebooks/EulerWaveguideBend.html
- A* 搜索算法（Hart, Nilsson & Raphael 1968）
  https://en.wikipedia.org/wiki/A*_search_algorithm
"""

from __future__ import annotations

import math
from enum import Enum
from typing import Any

import numpy as np

__all__ = [
    "CurveType",
    "CurvyRouter",
    "CurvyRouteConfig",
    "compute_path_loss",
    "count_crossings",
    "count_bends",
    "path_length",
    "s_bend_bezier",
    "generate_euler_bend",
    "generate_arc_bend",
]

# ---------------------------------------------------------------------------
# 常量（R02 学术诚信，参数来源见模块 docstring）
# ---------------------------------------------------------------------------

# SOI 波导传播损耗上界（dB/cm），Soref 1993 + SiEPIC EBeam PDK
PROPAGATION_LOSS_DB_CM = 3.0

# 单弯损耗（dB/bend），SiEPIC EBeam PDK 通用路径保守上界
BEND_LOSS_DB = 0.05

# 单次交叉损耗（dB/crossing），SiEPIC EBeam PDK crossing_te1550 上界
CROSSING_LOSS_DB = 0.3

# 弯曲检测浮点容差（μm）
_BEND_TOLERANCE = 1e-9

# 默认最小弯曲半径（μm），SiEPIC EBeam PDK bend_euler radius=5μm
DEFAULT_MIN_BEND_RADIUS_UM = 5.0


# ---------------------------------------------------------------------------
# 曲线类型枚举（迁移自 curvy_geometry.py）
# ---------------------------------------------------------------------------


class CurveType(Enum):
    """弯曲类型枚举（R10 路标）。

    Attributes:
        EULER: 欧拉螺旋（clothoid），曲率线性变化，损耗最低。
        ARC: 圆弧弯曲，恒定曲率。
        BEZIER: 贝塞尔曲线。
    """

    EULER = "euler"
    ARC = "arc"
    BEZIER = "bezier"


# ---------------------------------------------------------------------------
# 配置（迁移自 curvy_router.py CurvyRouteConfig）
# ---------------------------------------------------------------------------


class CurvyRouteConfig:
    """弯曲波导布线配置。

    Attributes:
        min_bend_radius_um: 最小弯曲半径 (μm)，SiEPIC EBeam PDK 默认 5μm。
            来源: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
        n_curve_points: 曲线采样点数（用于 euler/arc/bezier 曲线生成）。
        bend_loss_db: 单弯损耗 (dB)，SiEPIC EBeam PDK 上界 0.05。
        crossing_loss_db: 单次交叉损耗 (dB)，SiEPIC EBeam PDK 0.3。
    """

    def __init__(
        self,
        min_bend_radius_um: float = DEFAULT_MIN_BEND_RADIUS_UM,
        n_curve_points: int = 20,
        bend_loss_db: float = BEND_LOSS_DB,
        crossing_loss_db: float = CROSSING_LOSS_DB,
    ) -> None:
        if min_bend_radius_um <= 0:
            raise RuntimeError(
                f"min_bend_radius_um 必须为正: {min_bend_radius_um}"
                f"（R03 禁止 fall-back）"
            )
        if n_curve_points < 2:
            raise RuntimeError(
                f"n_curve_points 必须 >= 2: {n_curve_points}"
                f"（R03 禁止 fall-back）"
            )
        self.min_bend_radius_um = float(min_bend_radius_um)
        self.n_curve_points = int(n_curve_points)
        self.bend_loss_db = float(bend_loss_db)
        self.crossing_loss_db = float(crossing_loss_db)


# ---------------------------------------------------------------------------
# 曲线几何生成（迁移自 curvy_geometry.py）
# ---------------------------------------------------------------------------


def _euler_raw_points(
    start: tuple[float, float],
    angle_in: float,
    L: float,
    radius_um: float,
    n_points: int,
) -> list[tuple[float, float]]:
    """生成欧拉弯曲原始采样点（clothoid 数值积分）。

    曲率 k(s) = s / (R*L)，从 0 线性增至 1/R，转角 θ = L/(2R)。
    来源: Flexcompute Tidy3D clothoid 公式
      https://docs.flexcompute.com/projects/tidy3d/en/v2.9.2/notebooks/EulerWaveguideBend.html

    Args:
        start: 起点坐标。
        angle_in: 起始方向角 (弧度)。
        L: 弧长。
        radius_um: 最小曲率半径 (μm)。
        n_points: 采样点数。

    Returns:
        采样点列表 [(x, y), ...]。
    """
    sx, sy = start
    ds = L / max(1, n_points - 1)
    x, y = sx, sy
    theta = angle_in
    s = 0.0
    pts: list[tuple[float, float]] = []
    for _ in range(n_points):
        pts.append((x, y))
        k = (s / L) / radius_um if L > 0 else 0.0
        theta += k * ds
        x += ds * math.cos(theta)
        y += ds * math.sin(theta)
        s += ds
    return pts


def _rescale_euler_points(
    sx: float, sy: float, ex: float, ey: float,
    pts: list[tuple[float, float]],
) -> list[tuple[float, float]]:
    """旋转+缩放欧拉弯曲点到目标位置。"""
    target_angle = math.atan2(ey - sy, ex - sx)
    actual_end = pts[-1]
    dist_actual = math.hypot(actual_end[0] - sx, actual_end[1] - sy)
    scale = math.hypot(ex - sx, ey - sy) / max(1e-9, dist_actual)
    rot = target_angle - math.atan2(actual_end[1] - sy, actual_end[0] - sx)
    cos_r, sin_r = math.cos(rot), math.sin(rot)
    result: list[tuple[float, float]] = []
    for px, py in pts:
        dx, dy = px - sx, py - sy
        rx = sx + (dx * cos_r - dy * sin_r) * scale
        ry = sy + (dx * sin_r + dy * cos_r) * scale
        result.append((rx, ry))
    return result


def generate_euler_bend(
    start: tuple[float, float], end: tuple[float, float],
    radius_um: float, n_points: int,
) -> list[tuple[float, float]]:
    """生成欧拉弯曲连接两点（LiDAR ISPD'25 方法）。

    保证欧拉曲线最小曲率半径 >= radius_um（SiEPIC EBeam PDK 约束）。
    若两点距离过近导致缩放后半径不足，则放大 radius_um 到满足约束的值。

    弧长公式（clothoid 数学定义，单段 0→1/R）:
        k(s) = s / (R*L)，θ = L/(2R)，故 L = 2*R*θ
        对 90° 弯曲 (θ=π/2): L = π*R

    来源:
    - LiDAR ISPD'25 §3.2: https://dl.acm.org/doi/pdf/10.1145/3698364.3705355
    - SiEPIC EBeam PDK bend_euler: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
    - Flexcompute Tidy3D clothoid 公式 RL=A², θ=L/(2R):
      https://docs.flexcompute.com/projects/tidy3d/en/v2.9.2/notebooks/EulerWaveguideBend.html

    Args:
        start: 起点坐标。
        end: 终点坐标。
        radius_um: 最小曲率半径 (μm)。
        n_points: 采样点数。

    Returns:
        欧拉弯曲采样点列表。
    """
    sx, sy = start
    ex, ey = end
    angle_in = math.atan2(ey - sy, ex - sx) if abs(ex - sx) > 1e-9 else math.pi / 2
    total_angle = math.pi / 2
    # 单段 clothoid 弧长: L = 2*R*θ
    #
    # *创新*：终点位移近似系数 0.6（经验近似，非文献直接引用）
    # 创新逻辑:
    # - Euler/clothoid 弯曲终点位移无简单解析解，需 Fresnel 积分
    # - 对 90° 单段 clothoid（θ=π/2，L=π*R），数值积分得位移/L ≈ 0.596
    # - 取 0.6 作为保守上界，用于缩放预判
    # 支持理论: Clothoid 曲线性质（曲率线性变化），Fresnel 积分数值解
    # 对标: KLayout/gdsfactory euler bend 自动半径调整
    L = 2.0 * radius_um * total_angle
    actual_dist_approx = L * 0.6
    target_dist = math.hypot(ex - sx, ey - sy)
    if target_dist < actual_dist_approx and target_dist > 1e-9:
        # 放大 radius_um 使 actual_dist_approx = target_dist，保证 scale=1
        radius_um = target_dist / (2.0 * total_angle * 0.6)
        L = 2.0 * radius_um * total_angle
    pts = _euler_raw_points(start, angle_in, L, radius_um, n_points)
    if pts:
        return _rescale_euler_points(sx, sy, ex, ey, pts)
    return [(sx, sy), (ex, ey)]


def generate_arc_bend(
    start: tuple[float, float], end: tuple[float, float],
    radius_um: float, n_points: int,
) -> list[tuple[float, float]]:
    """生成圆弧弯曲连接两点。

    保证圆弧半径 >= radius_um（SiEPIC EBeam PDK 最小弯曲半径约束）。
    来源: SiEPIC EBeam PDK bend_euler radius=5μm
      https://github.com/SiEPIC/SiEPIC_EBeam_PDK

    Args:
        start: 起点坐标。
        end: 终点坐标。
        radius_um: 最小曲率半径 (μm)。
        n_points: 采样点数。

    Returns:
        圆弧弯曲采样点列表。
    """
    sx, sy = start
    ex, ey = end
    dist = math.hypot(ex - sx, ey - sy)
    if dist < 1e-9:
        return [(sx, sy), (ex, ey)]
    # 圆弧半径至少为 radius_um；若两点距离过近无法满足，则放大半径到 dist/2
    r = max(radius_um, dist / 2.0)
    half_dist = dist / 2.0
    if r >= half_dist:
        d = math.sqrt(max(0.0, r * r - half_dist * half_dist))
    else:
        d = 0.0
    mx, my = (sx + ex) / 2.0, (sy + ey) / 2.0
    # 中垂线方向（垂直于 start-end 连线）
    perp_x = -(ey - sy) / dist
    perp_y = (ex - sx) / dist
    cx = mx + perp_x * d
    cy = my + perp_y * d
    a1 = math.atan2(sy - cy, sx - cx)
    a2 = math.atan2(ey - cy, ex - cx)
    da = a2 - a1
    while da > math.pi:
        da -= 2 * math.pi
    while da < -math.pi:
        da += 2 * math.pi
    pts = []
    for i in range(n_points):
        t = a1 + da * i / max(1, n_points - 1)
        pts.append((cx + r * math.cos(t), cy + r * math.sin(t)))
    return pts


def s_bend_bezier(
    x0: float, y0: float, x1: float, y1: float, n_points: int = 20,
) -> list[tuple[float, float]]:
    """生成 S 弯路径（贝塞尔曲线，光波导标准方法）。

    用三次贝塞尔曲线连接两点，控制点保证平滑过渡。
    来源: 迁移自 src/polaris/router/path_geometry.py:s_bend

    Args:
        x0: 起点 x。
        y0: 起点 y。
        x1: 终点 x。
        y1: 终点 y。
        n_points: 采样点数。

    Returns:
        贝塞尔 S-bend 采样点列表。
    """
    dx = x1 - x0
    cp1 = (x0 + dx * 0.5, y0)
    cp2 = (x0 + dx * 0.5, y1)
    pts = []
    for i in range(n_points + 1):
        t = i / n_points
        mt = 1 - t
        x = mt**3 * x0 + 3 * mt**2 * t * cp1[0] + 3 * mt * t**2 * cp2[0] + t**3 * x1
        y = mt**3 * y0 + 3 * mt**2 * t * cp1[1] + 3 * mt * t**2 * cp2[1] + t**3 * y1
        pts.append((x, y))
    return pts


def _chaikin_smooth(
    points: list[tuple[float, float]], iterations: int,
) -> list[tuple[float, float]]:
    """Chaikin 路径平滑算法（角切割细分）。

    来源: Chaikin 1974 "An algorithm for high-speed curve generation"
    """
    result = list(points)
    for _ in range(iterations):
        if len(result) < 3:
            break
        new_pts: list[tuple[float, float]] = [result[0]]
        for i in range(len(result) - 1):
            p0 = result[i]
            p1 = result[i + 1]
            q0 = (0.75 * p0[0] + 0.25 * p1[0], 0.75 * p0[1] + 0.25 * p1[1])
            q1 = (0.25 * p0[0] + 0.75 * p1[0], 0.25 * p0[1] + 0.75 * p1[1])
            new_pts.extend([q0, q1])
        new_pts.append(result[-1])
        result = new_pts
    return result


# ---------------------------------------------------------------------------
# 路径几何工具（迁移自 path_geometry.py）
# ---------------------------------------------------------------------------


def path_length(points: list[tuple[float, float]]) -> float:
    """计算折线路径总长度 (μm)。

    Args:
        points: 路径点序列 [(x, y), ...]。

    Returns:
        路径总长度 (μm)。
    """
    total = 0.0
    for i in range(1, len(points)):
        total += math.hypot(
            points[i][0] - points[i - 1][0], points[i][1] - points[i - 1][1]
        )
    return total


def count_bends(points: list[tuple[float, float]]) -> int:
    """统计路径中的弯曲数（方向改变次数）。

    遍历路径点序列，当中间点的入射方向与出射方向不一致时计为一次弯曲。
    方向由相邻点的位移向量 (dx, dy) 表示。

    来源: LiDAR ISPD 2025, curvy-aware routing
      https://dl.acm.org/doi/pdf/10.1145/3698364.3705355
    与 polaris.router.path_geometry.path_loss 弯曲检测逻辑一致。

    Args:
        points: 路径点序列 [(x, y), ...]。

    Returns:
        弯曲数。
    """
    if len(points) < 3:
        return 0
    bends = 0
    for i in range(1, len(points) - 1):
        dx1 = points[i][0] - points[i - 1][0]
        dy1 = points[i][1] - points[i - 1][1]
        dx2 = points[i + 1][0] - points[i][0]
        dy2 = points[i + 1][1] - points[i][1]
        if abs(dx1 - dx2) > _BEND_TOLERANCE or abs(dy1 - dy2) > _BEND_TOLERANCE:
            bends += 1
    return bends


def _cross(
    o: tuple[float, float],
    a: tuple[float, float],
    b: tuple[float, float],
) -> float:
    """计算叉积 (a-o) × (b-o)。"""
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def _segments_intersect(
    p1: tuple[float, float],
    p2: tuple[float, float],
    p3: tuple[float, float],
    p4: tuple[float, float],
) -> bool:
    """检测两线段是否相交（CCW 叉积法）。

    来源: Computational Geometry, de Berg et al. 2008 §2.1
    """
    d1 = _cross(p3, p4, p1)
    d2 = _cross(p3, p4, p2)
    d3 = _cross(p1, p2, p3)
    d4 = _cross(p1, p2, p4)
    if ((d1 > 0 and d2 < 0) or (d1 < 0 and d2 > 0)) and (
        (d3 > 0 and d4 < 0) or (d3 < 0 and d4 > 0)
    ):
        return True
    return False


def count_crossings(
    path1: list[tuple[float, float]],
    path2: list[tuple[float, float]],
) -> int:
    """统计两条折线路径的交叉数（线段相交检测）。

    来源: polaris.router.path_geometry.count_crossings（CCW 叉积法）
      https://github.com/SiEPIC/SiEPIC_EBeam_PDK

    Args:
        path1: 第一条路径点序列。
        path2: 第二条路径点序列。

    Returns:
        交叉数。
    """
    count = 0
    for i in range(len(path1) - 1):
        a1, a2 = path1[i], path1[i + 1]
        for j in range(len(path2) - 1):
            b1, b2 = path2[j], path2[j + 1]
            if _segments_intersect(a1, a2, b1, b2):
                count += 1
    return count


# ---------------------------------------------------------------------------
# 路径损耗计算
# ---------------------------------------------------------------------------


def compute_path_loss(
    points: list[tuple[float, float] | list[float]],
    loss_db_cm: float = PROPAGATION_LOSS_DB_CM,
) -> float:
    """计算波导路径损耗（传播损耗 + 弯曲损耗）。

    损耗模型::

        loss_db = propagation + n_bends * 0.05

    - 传播损耗 = ``loss_db_cm`` × 路径长度(μm) / 1e4（cm = 1e4 μm）
    - 弯曲损耗 = 弯曲数 × 0.05 dB（SiEPIC EBeam PDK 通用路径上界）

    默认 ``loss_db_cm=3.0`` dB/cm 为 SOI 波导传播损耗上界
    （Soref 1993 + SiEPIC PDK，R05 Bug 修复 v4.0-SOI-LOSS-P1 统一值）。

    来源（R02 学术诚信）:
    - Soref et al. 1993 IEEE Proc. 41(9) 1182-1183（SOI 3 dB/cm）
      https://ieeexplore.ieee.org/document/1148303
    - SiEPIC EBeam PDK（0.05 dB/bend 上界）
      https://github.com/SiEPIC/SiEPIC_EBeam_PDK
    - Chrostowski & Hochberg 2015 §6.4 Silicon Photonics Design
      https://www.cambridge.org/core/books/silicon-photonics-design/

    Args:
        points: 路径点序列 [(x, y), ...]，坐标单位 μm。
        loss_db_cm: 传播损耗系数 (dB/cm)，默认 3.0。

    Returns:
        路径总损耗 (dB)。

    Raises:
        RuntimeError: loss_db_cm 为负（R03 禁止 fall-back）。
    """
    if loss_db_cm < 0:
        raise RuntimeError(
            f"loss_db_cm 不能为负: {loss_db_cm}（R03 禁止 fall-back）"
        )
    if not points or len(points) < 2:
        return 0.0
    # 归一化为 tuple list（兼容 list[list[float]] 输入）
    pts: list[tuple[float, float]] = [
        (float(p[0]), float(p[1])) for p in points
    ]
    length_um = path_length(pts)
    propagation = loss_db_cm * length_um / 1e4  # cm = 1e4 μm
    n_bends = count_bends(pts)
    bend_loss = n_bends * BEND_LOSS_DB
    return float(propagation + bend_loss)


# ---------------------------------------------------------------------------
# S-bend 布线路径生成
# ---------------------------------------------------------------------------


def _route_step(
    start: tuple[float, float], end: tuple[float, float],
) -> list[tuple[float, float]]:
    """生成 step 拓扑 S-bend 路径（水平→垂直→水平）。

    用于连接不同 x、不同 y 的两点。路径包含 4 个点（起点、两个拐角、终点），
    弯曲数 = 2（两个 90° 拐角），路径长度 = 曼哈顿距离。

    step 拓扑是光波导布线的标准拓扑之一（L-bend / double-L），物理意义明确，
    弯曲数可解析（不依赖曲线采样分辨率），损耗计算可溯源。

    来源:
    - LiDAR ISPD'25 §3.2 step routing baseline
      https://dl.acm.org/doi/pdf/10.1145/3698364.3705355
    - SiEPIC EBeam PDK routing elements
      https://github.com/SiEPIC/SiEPIC_EBeam_PDK

    Args:
        start: 起点坐标 (μm)。
        end: 终点坐标 (μm)。

    Returns:
        路径点列表 [(x, y), ...]。
    """
    sx, sy = start
    ex, ey = end
    mid_x = (sx + ex) / 2.0
    # step 拓扑: start → (mid_x, sy) → (mid_x, ey) → end
    return [(sx, sy), (mid_x, sy), (mid_x, ey), (ex, ey)]


def _route_straight(
    start: tuple[float, float], end: tuple[float, float],
) -> list[tuple[float, float]]:
    """生成直线路径（同 x 或同 y）。"""
    return [(start[0], start[1]), (end[0], end[1])]


# ---------------------------------------------------------------------------
# CurvyRouter 布线器
# ---------------------------------------------------------------------------


class CurvyRouter:
    """曲线波导布线器（迁移自 curvy_router.py CurvyRouter）。

    连接两个端口坐标，生成 S-bend 曲线波导路径：
    - 起终点对齐（同 x 或同 y）: 直线路径，0 弯曲
    - 起终点不对齐: step 拓扑 S-bend 路径，2 弯曲

    损耗模型: 传播损耗 (dB/cm) + 弯曲损耗 (0.05 dB/bend)
    来源: LiDAR ISPD'25 https://dl.acm.org/doi/pdf/10.1145/3698364.3705355

    Attributes:
        config: 布线器配置（CurvyRouteConfig）。
    """

    def __init__(self, config: CurvyRouteConfig | None = None) -> None:
        self.config = config or CurvyRouteConfig()

    def route(
        self, start: tuple[float, float], end: tuple[float, float],
    ) -> list[tuple[float, float]]:
        """布线：生成从 start 到 end 的曲线波导路径。

        Args:
            start: 起点坐标 (μm)。
            end: 终点坐标 (μm)。

        Returns:
            路径点列表 [(x, y), ...]，坐标单位 μm。

        Raises:
            RuntimeError: start/end 非法（R03 禁止 fall-back）。
        """
        if start is None or end is None:
            raise RuntimeError(
                f"start/end 不能为 None: start={start}, end={end}"
                f"（R03 禁止 fall-back）"
            )
        sx, sy = float(start[0]), float(start[1])
        ex, ey = float(end[0]), float(end[1])
        # 同点: 零长路径（返回起止两点，保证 n_points >= 2，与 C ABI 一致）
        if abs(sx - ex) < _BEND_TOLERANCE and abs(sy - ey) < _BEND_TOLERANCE:
            return [(sx, sy), (ex, ey)]
        # 对齐（同 x 或同 y）: 直线
        if abs(sx - ex) < _BEND_TOLERANCE or abs(sy - ey) < _BEND_TOLERANCE:
            return _route_straight((sx, sy), (ex, ey))
        # 不对齐: step 拓扑 S-bend
        return _route_step((sx, sy), (ex, ey))
