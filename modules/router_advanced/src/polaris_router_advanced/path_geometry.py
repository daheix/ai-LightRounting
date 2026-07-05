"""波导路径几何工具（SubTask 11.2-11.4）。

提供 S 弯/欧拉弯曲/圆弧弯曲生成、波导间距检查、交叉计数、
等长路径约束、路径长度/损耗计算等几何工具函数。

从 `waveguide_router.py` 拆分而来（规则 7.1：单文件有效行数上限 500）。

来源（R02 学术诚信，≥5 个文献 URL）:
- 欧拉弯曲（clothoid）平滑过渡，曲率线性变化降低弯曲损耗
  来源: Fujisawa et al., Opt. Express 25, 9150 (2017)
  https://opg.optica.org/oe/fulltext.cfm?uri=oe-25-8-9150
- Rizzo et al., Optics Letters 48(2), 215 (2023) 欧拉曲线提升 SOI 器件制造鲁棒性
  https://lightwave.ee.columbia.edu/sites/default/files/content/publications/2022/ol-48-2-215.pdf
- SiEPIC EBeam PDK (波导弯曲规则), https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- gdsfactory euler_bend 实现, https://github.com/gdsfactory/gdsfactory
- Chrostowski & Hochberg, "Silicon Photonics Design", CUP 2015 §5 (弯曲波导),
  https://www.cambridge.org/core/books/photonic-electronics/
- 贝塞尔曲线波导路径, https://en.wikipedia.org/wiki/B%C3%A9zier_curve
"""

from __future__ import annotations

import math


# ---------------------------------------------------------------------------
# SubTask 11.2: S 弯/弯曲路径生成（贝塞尔/欧拉曲线）
# ---------------------------------------------------------------------------
def s_bend(
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    n_points: int = 20,
) -> list[tuple[float, float]]:
    """生成 S 弯路径（贝塞尔曲线，光波导标准方法）。

    用三次贝塞尔曲线连接两点，控制点保证平滑过渡。
    """
    dx = x1 - x0
    # 控制点：水平偏移
    cp1 = (x0 + dx * 0.5, y0)
    cp2 = (x0 + dx * 0.5, y1)
    pts = []
    for i in range(n_points + 1):
        t = i / n_points
        # 三次贝塞尔
        mt = 1 - t
        x = mt**3 * x0 + 3 * mt**2 * t * cp1[0] + 3 * mt * t**2 * cp2[0] + t**3 * x1
        y = mt**3 * y0 + 3 * mt**2 * t * cp1[1] + 3 * mt * t**2 * cp2[1] + t**3 * y1
        pts.append((x, y))
    return pts


def euler_bend(
    radius_um: float,
    angle_deg: float = 90.0,
    n_points: int = 30,
) -> list[tuple[float, float]]:
    """生成欧拉弯曲路径（光波导标准方法，损耗最低）。

    欧拉弯曲（clothoid）曲率从 0 线性增加到 1/R，过渡平滑，
    是低损耗波导弯曲的标准选择。

    弧长公式推导（clothoid 数学定义）:
        曲率 k(s) = s / (R*L)，在 s=L 时 k=1/R
        总转角 θ = ∫₀^L k(s) ds = L²/(2*R*L) = L/(2R)
        求解 L: L = 2*R*θ （θ 为目标转角，弧度）
        对 90° 弯曲 (θ=π/2): L = π*R ≈ 3.14159*R

    来源:
    - Fujisawa et al., Opt. Express 25, 9150 (2017) 首次将 clothoid 曲线
      用于硅波导 90° 弯曲，损耗显著低于圆弧弯曲
      https://opg.optica.org/oe/fulltext.cfm?uri=oe-25-8-9150
    - Rizzo et al., Optics Letters 48(2), 215 (2023) 欧拉曲线提升 SOI 器件
      制造鲁棒性（RAMZI 交错滤波器）
      https://lightwave.ee.columbia.edu/sites/default/files/content/publications/2022/ol-48-2-215.pdf
    - Flexcompute Tidy3D EulerWaveguideBend: clothoid 公式 RL=A², θ=L/(2R)
      https://docs.flexcompute.com/projects/tidy3d/en/v2.9.2/notebooks/EulerWaveguideBend.html
    - Levien "The Euler spiral: a mathematical history" UC Berkeley EECS-2008-111
      https://www2.eecs.berkeley.edu/Pubs/TechRpts/2008/Archive/EECS-2008-111.pdf
    """
    angle = math.radians(angle_deg)
    # 单段 clothoid 弧长: L = 2*R*θ（使 k 从 0 线性增至 1/R 时恰好转过 θ）
    L = 2.0 * radius_um * angle
    pts = []
    s = 0.0
    ds = L / n_points
    x, y = 0.0, 0.0
    theta = 0.0
    for _ in range(n_points + 1):
        # 先记录当前点（保证起点为 (0, 0)），再积分前进一步
        pts.append((x, y))
        # 曲率 k = s / (R * L) 线性增长（clothoid 定义 A² = R*L）
        k = (s / L) / radius_um if L > 0 else 0.0
        theta += k * ds
        x += ds * math.cos(theta)
        y += ds * math.sin(theta)
        s += ds
    return pts


def arc_bend(
    radius_um: float,
    angle_deg: float = 90.0,
    n_points: int = 20,
) -> list[tuple[float, float]]:
    """生成圆弧弯曲路径（标准方法）。"""
    angle = math.radians(angle_deg)
    pts = []
    for i in range(n_points + 1):
        t = i / n_points
        a = angle * t
        x = radius_um * math.sin(a)
        y = radius_um * (1 - math.cos(a))
        pts.append((x, y))
    return pts


# ---------------------------------------------------------------------------
# SubTask 11.3: 波导间距约束检查 + 交叉最小化
# ---------------------------------------------------------------------------
def check_min_spacing(
    path1: list[tuple[float, float]],
    path2: list[tuple[float, float]],
    min_spacing_um: float,
) -> bool:
    """检查两条波导路径间最小间距是否满足。"""
    for p1 in path1:
        for p2 in path2:
            if math.hypot(p1[0] - p2[0], p1[1] - p2[1]) < min_spacing_um:
                return False
    return True


def count_crossings(
    path1: list[tuple[float, float]],
    path2: list[tuple[float, float]],
) -> int:
    """统计两条折线路径的交叉数（线段相交检测）。"""
    count = 0
    for i in range(len(path1) - 1):
        a1, a2 = path1[i], path1[i + 1]
        for j in range(len(path2) - 1):
            b1, b2 = path2[j], path2[j + 1]
            if _segments_intersect(a1, a2, b1, b2):
                count += 1
    return count


def _segments_intersect(
    p1: tuple[float, float],
    p2: tuple[float, float],
    p3: tuple[float, float],
    p4: tuple[float, float],
) -> bool:
    """检测两线段是否相交（CCW 叉积法）。"""
    d1 = _cross(p3, p4, p1)
    d2 = _cross(p3, p4, p2)
    d3 = _cross(p1, p2, p3)
    d4 = _cross(p1, p2, p4)
    if ((d1 > 0 and d2 < 0) or (d1 < 0 and d2 > 0)) and (
        (d3 > 0 and d4 < 0) or (d3 < 0 and d4 > 0)
    ):
        return True
    return False


def _cross(
    o: tuple[float, float],
    a: tuple[float, float],
    b: tuple[float, float],
) -> float:
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


# ---------------------------------------------------------------------------
# SubTask 11.4: 等长路径约束
# ---------------------------------------------------------------------------
def equalize_length(
    path: list[tuple[float, float]],
    target_length_um: float,
    detour_step: float = 1.0,
) -> list[tuple[float, float]]:
    """通过添加蛇形绕行使路径达到目标长度（等长约束）。

    用于 MZI 臂、差分对长度匹配。在路径末端添加 U 形绕行。
    """
    current = path_length(path)
    if current >= target_length_um:
        return path
    deficit = target_length_um - current
    # 添加蛇形绕行：每个 U 形增加约 2*detour_step 长度
    last = path[-1]
    second_last = path[-2] if len(path) >= 2 else (last[0] - 1, last[1])
    # 绕行方向垂直于最后一段
    dx = last[0] - second_last[0]
    dy = last[1] - second_last[1]
    # 垂直方向
    perp_x = -dy
    perp_y = dx
    norm = math.hypot(perp_x, perp_y)
    if norm < 1e-9:
        perp_x, perp_y = 0.0, detour_step
        norm = detour_step
    perp_x = perp_x / norm * detour_step
    perp_y = perp_y / norm * detour_step
    new_pts = list(path)
    n_u = max(1, math.ceil(deficit / (2 * detour_step)))
    for _ in range(n_u):
        new_pts.append((last[0] + perp_x, last[1] + perp_y))
        new_pts.append((last[0], last[1]))
    return new_pts


def path_length(path: list[tuple[float, float]]) -> float:
    """计算折线路径总长度。"""
    total = 0.0
    for i in range(1, len(path)):
        total += math.hypot(path[i][0] - path[i - 1][0], path[i][1] - path[i - 1][1])
    return total


def path_loss(
    path: list[tuple[float, float]],
    loss_db_cm: float,
    bend_loss_db: float = 0.05,
    crossing_loss_db: float = 0.3,
    num_crossings: int = 0,
) -> float:
    """计算波导路径损耗（传播损耗 + 弯曲损耗 + 交叉损耗）。

    默认损耗值来源（SiEPIC EBeam PDK 真实测量值）:
    - bend_loss_db=0.05: **保守上界**，适用于未指定弯曲类型的通用路径
      （可能含 90° 直角弯/小半径弧形弯）。SiEPIC EBeam PDK 在 1550nm 波段下
      各类弯曲单弯损耗范围 0.005-0.05 dB，本函数取上界 0.05 dB 作为默认值，
      确保预估损耗不低于实际损耗（商业交付的保守设计原则）。
      来源: SiEPIC_EBeam_PDK, Lukas Chrostowski et al., UBC, MIT 协议
      https://github.com/SiEPIC/SiEPIC_EBeam_PDK
      文献: Chrostowski & Hochberg 2015 §3.3 Silicon Photonics Design
      https://www.cambridge.org/core/books/silicon-photonics-design/

      **注**: 若路径明确使用欧拉弯曲（clothoid, 曲率线性变化），单弯损耗
      典型值仅 0.005-0.015 dB（远低于上界），应使用 ``curvy_router.py``
      中的 euler 弯曲专用计算（0.015 dB），不要套用本函数默认值。

    - crossing_loss_db=0.3: 波导交叉损耗，SiEPIC EBeam PDK 中 crossing_te1550
      在 1550nm 波段下单次交叉损耗典型值 0.15-0.3 dB
      来源: 同上 SiEPIC_EBeam_PDK

    Args:
        path: 折线路径点序列。
        loss_db_cm: 传播损耗系数 (dB/cm)。
        bend_loss_db: 单弯损耗 (dB)，默认 0.05（SiEPIC EBeam PDK 上界，保守估计）。
        crossing_loss_db: 单次交叉损耗 (dB)，默认 0.3（SiEPIC EBeam PDK）。
        num_crossings: 交叉数。

    Returns:
        总损耗 (dB)。
    """
    length_um = path_length(path)
    propagation = loss_db_cm * length_um / 1e4  # cm = 1e4 μm
    # 估算弯曲数（方向变化点）
    num_bends = 0
    for i in range(1, len(path) - 1):
        dx1 = path[i][0] - path[i - 1][0]
        dy1 = path[i][1] - path[i - 1][1]
        dx2 = path[i + 1][0] - path[i][0]
        dy2 = path[i + 1][1] - path[i][1]
        # 方向变化则计为弯曲
        if abs(dx1 - dx2) > 1e-9 or abs(dy1 - dy2) > 1e-9:
            num_bends += 1
    return propagation + num_bends * bend_loss_db + num_crossings * crossing_loss_db
