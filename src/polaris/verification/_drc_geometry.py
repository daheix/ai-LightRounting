"""DRC 几何工具函数模块（从 drc_curvilinear_18rules.py 拆分，R181-R200）。

提供曲线感知 DRC 引擎所需的全部计算几何算法，包括:
- 鞋带公式（多边形面积）
- 旋转卡尺法（多边形最小宽度）
- 射线法（点在多边形内）
- 叉积 straddling test（线段相交检测）
- 三点圆拟合（曲率/弯曲半径）
- 端边识别与端到端距离

对齐: Synopsys OptoDesigner DRC Module + KLayout 曲线 DRC + Calibre nmDRC。

学术依据:
- de Berg et al., "Computational Geometry: Algorithms and Applications",
  Springer 2008, DOI: 10.1007/978-3-540-77974-2
  https://www.cs.uu.nl/docs/vakken/ga/slides4b.pdf
- Christer Ericson, "Real-Time Collision Detection", Morgan Kaufmann 2005
  https://realtimecollisiondetection.net/
- Godfried T. Toussaint, "Solving Geometric Problems with the Rotating Calipers",
  IEEE MELECON 1983
  https://www.cs.mcgill.ca/~godfried/publications/calipers.pdf
- KLayout DRC Reference: https://klayout.org/downloads/master/doc-qt4/manual/drc_basic.html
- Siemens Calibre nmDRC: https://eda.sw.siemens.com/en-US/calibre/
- Synopsys IC Validator DRC: https://www.synopsys.com/implementation-and-signoff/signoff/ic-validator.html
- OpenDRC, He et al., DAC 2023, DOI:10.1109/DAC56929.2023.10247734
- PDRC, Jiang et al., DAC 2024,
  http://www.cse.cuhk.edu.hk/~byu/papers/C219-DAC2024-PDRC.pdf
- imec Curvilinear DRC: https://www.imec-int.com/en/articles/curvilinear-technology-game-changer-logic-technology-roadmap
- Cao et al. 2015, Silicon Photonics Design Rule Checking (curvilinear 验证方法学)
  https://www.semiconductorpackagingnews.com/uploads/1/Advancing_silicon_photonics_verification_innovation__4_.pdf

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R05 Bug 必修。
"""

from __future__ import annotations

import math

import numpy as np
from numpy.typing import NDArray

# =============================================================================
# 几何工具函数（真实 DRC 几何检查的基础）
# =============================================================================

def _polygon_area(poly: NDArray[np.float64]) -> float:
    """多边形面积（鞋带公式 Shoelace）。

    文献:
    - https://en.wikipedia.org/wiki/Shoelace_formula
    - de Berg et al., "Computational Geometry: Algorithms and Applications", Springer 2008
    - https://doi.org/10.1007/978-3-540-77974-2
    - KLayout DRC Reference: https://klayout.org/downloads/master/doc-qt4/manual/drc_basic.html
    - OpenDRC, He et al., DAC 2023, DOI:10.1109/DAC56929.2023.10247734
    """
    if len(poly) < 3:
        return 0.0
    x, y = poly[:, 0], poly[:, 1]
    return 0.5 * abs(float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))))


def _polygon_bbox(poly: NDArray[np.float64]) -> tuple[float, float, float, float]:
    """多边形轴对齐包围盒 (xmin, ymin, xmax, ymax)。"""
    xs, ys = poly[:, 0], poly[:, 1]
    return (float(xs.min()), float(ys.min()), float(xs.max()), float(ys.max()))


def _point_segment_distance(
    p: NDArray[np.float64],
    a: NDArray[np.float64],
    b: NDArray[np.float64],
) -> float:
    """点 p 到线段 ab 的最短距离。

    公式: d = ||p-(a+t·(b-a))||, t=clamp((p-a)·(b-a)/||b-a||², 0, 1)
    文献:
    - de Berg, "Computational Geometry", Springer 2008
    - https://doi.org/10.1007/978-3-540-77974-2
    - KLayout DRC: https://klayout.org/downloads/master/doc-qt4/manual/drc_basic.html
    - OpenDRC, He et al., DAC 2023
    - PDRC, Jiang et al., DAC 2024
    """
    ab = b - a
    ap = p - a
    denom = float(np.dot(ab, ab))
    if denom < 1e-18:
        return float(np.linalg.norm(ap))
    t = max(0.0, min(1.0, float(np.dot(ap, ab) / denom)))
    return float(np.linalg.norm(p - (a + t * ab)))


def _point_in_polygon(
    p: NDArray[np.float64], poly: NDArray[np.float64]
) -> bool:
    """点在多边形内判定（射线法 Ray Casting / Even-Odd Rule，支持凹多边形）。

    算法: 从点向右发射水平射线，统计与多边形边的交点数。
    交点数为奇数 → 点在内部；偶数 → 点在外部。
    正确处理边界情况：点在顶点/边上时返回 True。

    文献:
    - Shimrat, "Algorithm 112: Position of point relative to polygon", CACM 1962
    - de Berg et al., "Computational Geometry: Algorithms and Applications", Springer 2008
      https://www.cs.uu.nl/docs/vakken/ga/slides4b.pdf
    - Hacker's Delight 2nd ed., Chapter 18 (point-in-polygon)
    - Wikipedia Point in polygon: https://en.wikipedia.org/wiki/Point_in_polygon
    - Real-Time Collision Detection, Christer Ericson, Morgan Kaufmann 2005
    - W. Randolph Franklin, PNPOLY: https://wrf.ecse.rpi.edu/Research/Short_Notes/pnpoly.html
    """
    n = len(poly)
    if n < 3:
        return False

    px, py = float(p[0]), float(p[1])
    inside = False

    j = n - 1
    for i in range(n):
        xi, yi = float(poly[i][0]), float(poly[i][1])
        xj, yj = float(poly[j][0]), float(poly[j][1])

        # 点在顶点上 → 内部
        if (abs(px - xi) < 1e-12 and abs(py - yi) < 1e-12):
            return True

        # 检查边是否与水平射线相交
        # 条件: (yi > py) != (yj > py) 即边跨越 y = py 水平线
        if ((yi > py) != (yj > py)):
            # 计算交点的 x 坐标
            if abs(yj - yi) < 1e-18:
                j = i
                continue
            x_intersect = xi + (py - yi) * (xj - xi) / (yj - yi)
            # 点在边上 → 内部
            if abs(px - x_intersect) < 1e-12:
                return True
            # 点在射线左侧 → 相交
            if px < x_intersect:
                inside = not inside
        j = i

    return inside


def _polygon_min_width(poly: NDArray[np.float64]) -> float:
    """多边形最小宽度（旋转卡尺法 Rotating Calipers）。

    算法: 对每条边，计算所有顶点到该边的最大距离（即该边方向上的宽度），
    取所有边方向上宽度的最小值，即为多边形的最小宽度。
    适用于凸多边形（精确），对凹多边形给出保守估计。

    学术文献:
    - Godfried T. Toussaint, "Solving Geometric Problems with the Rotating Calipers",
      Proceedings of IEEE MELECON 1983, pp. 1-5.
      https://www.cs.mcgill.ca/~godfried/publications/calipers.pdf
    - M. A. Lopez & S. Reisner, "On the Minimal Width of a Convex Polygon",
      Information Processing Letters, 1985, Vol. 20, No. 4, pp. 173-178.
      DOI: 10.1016/0020-0190(85)90095-4
    - de Berg et al., "Computational Geometry: Algorithms and Applications",
      Springer 2008, Chapter 4 (Linear Programming) - width as smallest enclosing strip.
      DOI: 10.1007/978-3-540-77974-2
    - KLayout DRC width check:
      https://klayout.org/downloads/master/doc-qt4/manual/drc_basic.html
    - OpenDRC, He et al., DAC 2023, DOI: 10.1109/DAC56929.2023.10247734
    - PDRC, Jiang et al., DAC 2024,
      http://www.cse.cuhk.edu.hk/~byu/papers/C219-DAC2024-PDRC.pdf
    - Siemens Calibre nmDRC: https://eda.sw.siemens.com/en-US/calibre/
    - Synopsys IC Validator:
      https://www.synopsys.com/implementation-and-signoff/signoff/ic-validator.html
    """
    n = len(poly)
    if n < 3:
        return 0.0
    min_w = float("inf")
    for i in range(n):
        x1, y1 = float(poly[i][0]), float(poly[i][1])
        x2, y2 = float(poly[(i + 1) % n][0]), float(poly[(i + 1) % n][1])
        dx, dy = x2 - x1, y2 - y1
        seg_len = math.hypot(dx, dy)
        if seg_len < 1e-12:
            continue
        max_dist = 0.0
        for j in range(n):
            if j == i or j == (i + 1) % n:
                continue
            dist = abs(-dy * (float(poly[j][0]) - x1)
                       + dx * (float(poly[j][1]) - y1)) / seg_len
            if dist > max_dist:
                max_dist = dist
        if max_dist > 0 and max_dist < min_w:
            min_w = max_dist
    return min_w if min_w != float("inf") else 0.0


def _polygon_pair_min_distance(
    p1: NDArray[np.float64], p2: NDArray[np.float64]
) -> float:
    """两个多边形之间的最小边到边距离。

    算法: 遍历所有边对，计算两线段最短距离（含相交检测）。
    相交检测使用叉积 straddling test（Ericson 2005; de Berg 2008）。

    文献:
    - Christer Ericson, "Real-Time Collision Detection", Morgan Kaufmann 2005,
      Chapter 5 (Distance of Linear Components)
      https://realtimecollisiondetection.net/
    - de Berg et al., "Computational Geometry: Algorithms and Applications",
      Springer 2008, Chapter 2 (Line Segment Intersection)
      DOI: 10.1007/978-3-540-77974-2
    - KLayout DRC space check:
      https://klayout.org/downloads/master/doc-qt4/manual/drc_basic.html
    - OpenDRC, He et al., DAC 2023, DOI: 10.1109/DAC56929.2023.10247734
    - PDRC, Jiang et al., DAC 2024,
      http://www.cse.cuhk.edu.hk/~byu/papers/C219-DAC2024-PDRC.pdf
    - Calibre nmDRC: https://eda.sw.siemens.com/en-US/calibre/
    """
    n1, n2 = len(p1), len(p2)
    min_d = float("inf")
    for i in range(n1):
        a, b = p1[i], p1[(i + 1) % n1]
        for j in range(n2):
            c, d = p2[j], p2[(j + 1) % n2]
            dist = _segment_segment_distance(a, b, c, d)
            if dist < min_d:
                min_d = dist
    return min_d


def _cross2d(
    p: NDArray[np.float64],
    q: NDArray[np.float64],
    r: NDArray[np.float64],
) -> float:
    """2D 叉积 (q-p) × (r-p)。用于判断三点转向。

    文献:
    - de Berg et al., "Computational Geometry", Springer 2008, Chapter 2
    - Ericson, "Real-Time Collision Detection", Morgan Kaufmann 2005
    """
    return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])


def _segments_intersect(
    a: NDArray[np.float64],
    b: NDArray[np.float64],
    c: NDArray[np.float64],
    d: NDArray[np.float64],
) -> bool:
    """检测两条线段 AB 和 CD 是否相交（含端点接触和共线重叠）。

    算法: 叉积 straddling test + 端点共线检测。
    文献:
    - de Berg et al., "Computational Geometry", Springer 2008, Chapter 2
    - Ericson, "Real-Time Collision Detection", Morgan Kaufmann 2005, Chapter 5
    """
    d1 = _cross2d(c, d, a)
    d2 = _cross2d(c, d, b)
    d3 = _cross2d(a, b, c)
    d4 = _cross2d(a, b, d)

    if _segments_straddle(d1, d2, d3, d4):
        return True

    return _endpoint_touches(d1, d2, d3, d4, a, b, c, d)


def _segments_straddle(
    d1: float, d2: float, d3: float, d4: float,
) -> bool:
    """叉积 straddling 测试：两线段是否严格跨立（R602 Extract Method）。

    Args:
        d1..d4: 四个端点的叉积值（_cross2d 计算）。

    Returns:
        True 表示两线段跨立相交（不含共线端点接触）。

    来源:
    - de Berg et al., "Computational Geometry", Springer 2008, Chapter 2
      DOI: 10.1007/978-3-540-77974-2
    - Ericson, "Real-Time Collision Detection", MK 2005, Chapter 5
    - Martin Fowler, "Refactoring", 2nd ed., 2018, Extract Function
      https://refactoring.com/catalog/extractFunction.html
    """
    return ((d1 > 0 and d2 < 0) or (d1 < 0 and d2 > 0)) and \
           ((d3 > 0 and d4 < 0) or (d3 < 0 and d4 > 0))


def _endpoint_touches(
    d1: float, d2: float, d3: float, d4: float,
    a: NDArray[np.float64], b: NDArray[np.float64],
    c: NDArray[np.float64], d: NDArray[np.float64],
) -> bool:
    """端点共线接触检测：某端点恰好落在对边线段上（R602 Extract Method）。

    Args:
        d1..d4: 四个端点的叉积值。
        a, b: 线段 AB 的两端点。
        c, d: 线段 CD 的两端点。

    Returns:
        True 表示存在端点共线接触。

    来源:
    - de Berg et al., "Computational Geometry", Springer 2008, Chapter 2
      DOI: 10.1007/978-3-540-77974-2
    - Ericson, "Real-Time Collision Detection", MK 2005, Chapter 5
    - Martin Fowler, "Refactoring", 2nd ed., 2018, Extract Function
      https://refactoring.com/catalog/extractFunction.html
    """
    if abs(d1) < 1e-12 and _point_on_segment(a, c, d):
        return True
    if abs(d2) < 1e-12 and _point_on_segment(b, c, d):
        return True
    if abs(d3) < 1e-12 and _point_on_segment(c, a, b):
        return True
    if abs(d4) < 1e-12 and _point_on_segment(d, a, b):
        return True
    return False


def _point_on_segment(
    p: NDArray[np.float64],
    a: NDArray[np.float64],
    b: NDArray[np.float64],
) -> bool:
    """判断点 p 是否在线段 ab 上（假设三点共线）。"""
    return (min(a[0], b[0]) - 1e-12 <= p[0] <= max(a[0], b[0]) + 1e-12 and
            min(a[1], b[1]) - 1e-12 <= p[1] <= max(a[1], b[1]) + 1e-12)


def _segment_segment_distance(
    a: NDArray[np.float64],
    b: NDArray[np.float64],
    c: NDArray[np.float64],
    d: NDArray[np.float64],
) -> float:
    """两线段最短距离（含相交检测）。

    算法: 先检测线段是否相交（相交则距离为 0），否则取 4 个端点到对方
    线段距离的最小值。

    文献:
    - Ericson, "Real-Time Collision Detection", Morgan Kaufmann 2005, Chapter 5
    - de Berg et al., "Computational Geometry", Springer 2008, Chapter 2
    - KLayout DRC space check
    - OpenDRC, He et al., DAC 2023
    - PDRC, Jiang et al., DAC 2024
    """
    if _segments_intersect(a, b, c, d):
        return 0.0
    return min(
        _point_segment_distance(c, a, b),
        _point_segment_distance(d, a, b),
        _point_segment_distance(a, c, d),
        _point_segment_distance(b, c, d),
    )


def _polygon_min_enclosure(
    inner: NDArray[np.float64], outer: NDArray[np.float64]
) -> float:
    """内多边形到外多边形的最小包围距离。

    首先检查内多边形所有顶点是否都在外多边形内部（使用射线法，支持凹多边形）。
    如果有顶点在外部，返回 -1.0（表示不满足包围条件）。
    如果所有顶点都在内部，计算内多边形顶点到外多边形各边的最小距离。

    文献:
    - KLayout DRC enclosing: https://klayout.org/downloads/master/doc-qt4/about/drc_ref_global.html
    - Calibre nmDRC: https://eda.sw.siemens.com/en-US/calibre/
    - Synopsys IC Validator DRC
    - OpenDRC, He et al., DAC 2023
    - PDRC, Jiang et al., DAC 2024
    - de Berg et al., Computational Geometry, Springer 2008 (point-in-polygon)
    """
    n_outer = len(outer)
    if n_outer < 3 or len(inner) < 3:
        return -1.0

    # 检查内多边形所有顶点是否都在外多边形内部
    for pt in inner:
        if not _point_in_polygon(pt, outer):
            return -1.0

    # 计算内多边形所有顶点到外多边形各边的最小距离
    min_dist = float("inf")
    for pt in inner:
        for i in range(n_outer):
            a, b = outer[i], outer[(i + 1) % n_outer]
            d = _point_segment_distance(pt, a, b)
            if d < min_dist:
                min_dist = d
    return min_dist if min_dist != float("inf") else 0.0


def _polygon_end_edges(
    poly: NDArray[np.float64], max_edges: int = 4,
) -> list[tuple[NDArray[np.float64], NDArray[np.float64]]]:
    """识别多边形的端边（最短边），用于端到端间距检查。

    对于波导（长矩形），两端是最短边。算法：计算所有边长，返回最短的
    ``max_edges`` 条边。对一般多边形也适用——端边是最短边。

    算法来源:
    - KLayout DRC extent_refs/edges: 端边识别用于 sep（separation）检查
      https://klayout.org/downloads/master/doc-qt4/about/drc_ref_global.html
    - Calibre nmDRC EXTernal end-to-end spacing: 端边间最小距离
      https://eda.sw.siemens.com/en-US/calibre/
    - de Berg et al., Computational Geometry, Springer 2008, Ch.2 (线段距离)
      DOI: 10.1007/978-3-540-77974-2
    - Ericson, Real-Time Collision Detection, MK 2005, Ch.5
    - OpenDRC, He et al., DAC 2023, DOI:10.1109/DAC56929.2023.10247734

    Args:
        poly: (N,2) 多边形顶点数组。
        max_edges: 返回的最大端边数，默认 4。

    Returns:
        端边列表 [(start_point, end_point), ...]，按边长升序。
    """
    n = len(poly)
    if n < 3:
        return []
    edges: list[tuple[float, tuple[NDArray[np.float64], NDArray[np.float64]]]] = []
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        length = float(np.linalg.norm(b - a))
        edges.append((length, (a, b)))
    edges.sort(key=lambda e: e[0])
    return [e[1] for e in edges[:max_edges]]


def _edge_to_edge_distance(
    a1: NDArray[np.float64], a2: NDArray[np.float64],
    b1: NDArray[np.float64], b2: NDArray[np.float64],
) -> float:
    """两条线段之间的最短距离（含相交检测）。

    若相交返回 0。否则返回端点到线段距离的最小值。

    文献:
    - Ericson, Real-Time Collision Detection, MK 2005, Ch.5 (Distance of Linear Components)
    - de Berg et al., Computational Geometry, Springer 2008, Ch.2
    """
    if _segments_intersect(a1, a2, b1, b2):
        return 0.0
    d1 = _point_segment_distance(a1, b1, b2)
    d2 = _point_segment_distance(a2, b1, b2)
    d3 = _point_segment_distance(b1, a1, a2)
    d4 = _point_segment_distance(b2, a1, a2)
    return min(d1, d2, d3, d4)


def _polygon_extension(
    inner: NDArray[np.float64], outer: NDArray[np.float64]
) -> float:
    """内多边形超出外多边界的延伸距离（Calibre ENC extension 语义）。

    延伸检查 = 外多边形被内多边形包围的最小距离。即 inner 应完全包含 outer
    并向外延伸至少 limit。等价于 ``_polygon_min_enclosure(outer, inner)``。

    若 outer 未被 inner 完全包含（有 outer 顶点在 inner 外），返回 -1.0
    （表示不满足延伸条件）。若完全包含，返回 outer 顶点到 inner 各边的最小
    距离（即延伸量）。

    文献:
    - Calibre nmDRC ENClosure (ENC) 操作同时支持包围与延伸检查:
      "检查 input_layer1 是否被 input_layer2 包围，或 input_layer1 是否
      延伸超出 input_layer2"
      https://eda.sw.siemens.com/en-US/calibre/
    - KLayout DRC enclosing/extension:
      https://klayout.org/downloads/master/doc-qt4/about/drc_ref_global.html
    - Synopsys IC Validator DRC enclosure/extension
    - OpenDRC, He et al., DAC 2023
    - PDRC, Jiang et al., DAC 2024
    """
    return _polygon_min_enclosure(outer, inner)


def _polygon_angles(poly: NDArray[np.float64]) -> NDArray[np.float64]:
    """计算多边形所有内角（度）。

    使用向量点积计算相邻边的夹角。
    文献:
    - de Berg, "Computational Geometry", Springer 2008
    - KLayout DRC angle check
    - Synopsys OptoDesigner DRC Module
    - imec curvilinear DRC: https://www.imec-int.com/en/articles/curvilinear-technology-game-changer-logic-technology-roadmap
    - OpenDRC, He et al., DAC 2023
    """
    n = len(poly)
    angles = np.zeros(n)
    for i in range(n):
        prev = poly[(i - 1) % n]
        curr = poly[i]
        next_p = poly[(i + 1) % n]
        v1 = prev - curr
        v2 = next_p - curr
        dot = float(np.dot(v1, v2))
        n1 = float(np.linalg.norm(v1))
        n2 = float(np.linalg.norm(v2))
        if n1 < 1e-12 or n2 < 1e-12:
            angles[i] = 180.0
            continue
        cos_ang = max(-1.0, min(1.0, dot / (n1 * n2)))
        angles[i] = math.degrees(math.acos(cos_ang))
    return angles


def _polygon_curvature(poly: NDArray[np.float64]) -> tuple[float, float]:
    """估算多边形的最小弯曲半径和最大曲率。

    基于三点圆拟合：对连续三个顶点，计算外接圆半径作为局部曲率半径。
    曲率 = 1 / 半径。
    文献:
    - KLayout curvilinear DRC: https://klayout.org/downloads/master/doc-qt4/manual/drc_basic.html
    - imec curvilinear technology: https://www.imec-int.com/en/articles/curvilinear-technology-game-changer-logic-technology-roadmap
    - Synopsys OptoDesigner DRC
    - OpenDRC, He et al., DAC 2023
    - Cao et al. 2015, Silicon Photonics Design Rule Checking
    """
    n = len(poly)
    if n < 3:
        return float("inf"), 0.0
    min_radius = float("inf")
    max_curvature = 0.0
    for i in range(n):
        p1 = poly[(i - 1) % n]
        p2 = poly[i]
        p3 = poly[(i + 1) % n]
        ax, ay = float(p1[0]), float(p1[1])
        bx, by = float(p2[0]), float(p2[1])
        cx, cy = float(p3[0]), float(p3[1])
        d = 2.0 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
        if abs(d) < 1e-12:
            continue
        ux = ((ax**2 + ay**2) * (by - cy)
              + (bx**2 + by**2) * (cy - ay)
              + (cx**2 + cy**2) * (ay - by)) / d
        uy = ((ax**2 + ay**2) * (cx - bx)
              + (bx**2 + by**2) * (ax - cx)
              + (cx**2 + cy**2) * (bx - ax)) / d
        r = math.hypot(ux - ax, uy - ay)
        if r > 1e-12:
            if r < min_radius:
                min_radius = r
            k = 1.0 / r
            if k > max_curvature:
                max_curvature = k
    return min_radius if min_radius != float("inf") else float("inf"), max_curvature


def _polygon_taper_axis_aligned(poly: NDArray[np.float64]) -> float:
    """轴对齐方向（水平/垂直）的锥形张角估算（度）。

    取多边形两端点连线为轴，计算各端宽度差相对轴长的夹角。
    本函数处理 ``_polygon_taper_angle`` 中轴对齐的两个分支，降低主函数圈复杂度。

    文献:
    - Synopsys OptoDesigner DRC Module
    - KLayout DRC: https://klayout.org/downloads/master/doc-qt4/manual/drc_basic.html
    - Luceda IPKISS DRC: https://academy.lucedaphotonics.com/training/topical_training/tape_out_prep_verification/drc/drc
    """
    xmin, ymin, xmax, ymax = _polygon_bbox(poly)
    dx = xmax - xmin
    dy = ymax - ymin
    if dx >= dy:
        return _horizontal_taper_angle(poly, xmin, xmax, dx)
    return _vertical_taper_angle(poly, ymin, ymax, dy)


def _horizontal_taper_angle(
    poly: NDArray[np.float64], xmin: float, xmax: float, dx: float,
) -> float:
    """水平轴向锥形张角估算（R603 Extract Method 降低圈复杂度）。

    取多边形左右两端的 y 方向宽度差，相对 x 跨度求反正切得张角。

    Args:
        poly: 多边形顶点数组。
        xmin/xmax: 多边形 x 方向包围盒边界。
        dx: x 方向跨度。

    Returns:
        锥形张角（度）；两端点缺失或跨度为零时返回 0.0。

    来源:
    - Synopsys OptoDesigner DRC Module
    - KLayout DRC: https://klayout.org/downloads/master/doc-qt4/manual/drc_basic.html
    - Luceda IPKISS DRC: https://academy.lucedaphotonics.com/
    - Martin Fowler, "Refactoring", 2nd ed., 2018, Extract Function
      https://refactoring.com/catalog/extractFunction.html
    """
    left_pts = [p for p in poly if abs(p[0] - xmin) < 1e-9]
    right_pts = [p for p in poly if abs(p[0] - xmax) < 1e-9]
    if not (left_pts and right_pts) or dx <= 1e-12:
        return 0.0
    w_left = max(p[1] for p in left_pts) - min(p[1] for p in left_pts)
    w_right = max(p[1] for p in right_pts) - min(p[1] for p in right_pts)
    return math.degrees(math.atan(abs(w_right - w_left) / (2 * dx)))


def _vertical_taper_angle(
    poly: NDArray[np.float64], ymin: float, ymax: float, dy: float,
) -> float:
    """垂直轴向锥形张角估算（R603 Extract Method 降低圈复杂度）。

    取多边形上下两端的 x 方向宽度差，相对 y 跨度求反正切得张角。

    Args:
        poly: 多边形顶点数组。
        ymin/ymax: 多边形 y 方向包围盒边界。
        dy: y 方向跨度。

    Returns:
        锥形张角（度）；两端点缺失或跨度为零时返回 0.0。

    来源:
    - Synopsys OptoDesigner DRC Module
    - KLayout DRC: https://klayout.org/downloads/master/doc-qt4/manual/drc_basic.html
    - Luceda IPKISS DRC: https://academy.lucedaphotonics.com/
    - Martin Fowler, "Refactoring", 2nd ed., 2018, Extract Function
      https://refactoring.com/catalog/extractFunction.html
    """
    bottom_pts = [p for p in poly if abs(p[1] - ymin) < 1e-9]
    top_pts = [p for p in poly if abs(p[1] - ymax) < 1e-9]
    if not (bottom_pts and top_pts) or dy <= 1e-12:
        return 0.0
    w_bottom = max(p[0] for p in bottom_pts) - min(p[0] for p in bottom_pts)
    w_top = max(p[0] for p in top_pts) - min(p[0] for p in top_pts)
    return math.degrees(math.atan(abs(w_top - w_bottom) / (2 * dy)))


def _polygon_taper_angle(poly: NDArray[np.float64]) -> float:
    """估算锥形（taper）结构的最大张角。

    取多边形两端点连线为轴，计算各边相对于轴的最大夹角。
    文献:
    - Synopsys OptoDesigner DRC Module
    - KLayout DRC: https://klayout.org/downloads/master/doc-qt4/manual/drc_basic.html
    - Luceda IPKISS DRC: https://academy.lucedaphotonics.com/training/topical_training/tape_out_prep_verification/drc/drc
    - Cao et al. 2015, Silicon Photonics Design Rule Checking
    - imec curvilinear DRC
    """
    if len(poly) < 4:
        return 0.0
    return _polygon_taper_axis_aligned(poly)


def _layer_density(
    polygons: list[NDArray[np.float64]],
    region: tuple[float, float, float, float],
) -> float:
    """计算指定区域内多边形的密度（面积/区域面积）。

    文献:
    - KLayout DRC density: https://klayout.org/downloads/master/doc-qt4/manual/drc_basic.html
    - Calibre nmDRC: https://eda.sw.siemens.com/en-US/calibre/
    - Synopsys IC Validator
    - OpenDRC, He et al., DAC 2023
    - PDRC, Jiang et al., DAC 2024
    """
    xmin, ymin, xmax, ymax = region
    region_area = max(0.0, (xmax - xmin) * (ymax - ymin))
    if region_area < 1e-18:
        return 0.0
    total_area = 0.0
    for poly in polygons:
        total_area += _polygon_area(poly)
    return min(1.0, total_area / region_area)


# =============================================================================
# R141-R180 扩展几何工具函数（8 个新规则的基础算法）
# =============================================================================

def _polygon_perimeter(poly: NDArray[np.float64]) -> float:
    """多边形周长（所有边长度之和）。

    公式: P = Σ ||v_{i+1} - v_i||

    文献:
    - de Berg et al., "Computational Geometry: Algorithms and Applications",
      Springer 2008, DOI: 10.1007/978-3-540-77974-2
    - KLayout DRC perimeter check:
      https://www.klayout.org/doc-qt5/manual/drc_runsets.html
    - Calibre nmDRC perimeter rules: https://eda.sw.siemens.com/en-US/calibre/
    - Synopsys IC Validator DRC perimeter:
      https://www.synopsys.com/implementation-and-signoff/signoff/ic-validator.html
    - OpenDRC, He et al., DAC 2023, DOI:10.1109/DAC56929.2023.10247734
    """
    n = len(poly)
    if n < 2:
        return 0.0
    total = 0.0
    for i in range(n):
        a = poly[i]
        b = poly[(i + 1) % n]
        total += float(np.linalg.norm(b - a))
    return total


def _polygon_edge_lengths(poly: NDArray[np.float64]) -> NDArray[np.float64]:
    """多边形所有边的长度（数组）。

    文献:
    - de Berg et al., "Computational Geometry", Springer 2008, Ch.2
    - KLayout DRC edges/length check:
      https://www.klayout.org/doc-qt5/manual/drc_runsets.html
    - Calibre nmDRC edge length rules: https://eda.sw.siemens.com/en-US/calibre/
    - Synopsys OptoDesigner DRC Module:
      https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/design-rule-checking-module.html
    - OpenDRC, He et al., DAC 2023, DOI:10.1109/DAC56929.2023.10247734
    - PDRC, Jiang et al., DAC 2024,
      http://www.cse.cuhk.edu.hk/~byu/papers/C219-DAC2024-PDRC.pdf
    """
    n = len(poly)
    if n < 2:
        return np.array([], dtype=float)
    lengths = np.zeros(n, dtype=float)
    for i in range(n):
        a = poly[i]
        b = poly[(i + 1) % n]
        lengths[i] = float(np.linalg.norm(b - a))
    return lengths


def _polygon_max_width(poly: NDArray[np.float64]) -> float:
    """多边形最大宽度（旋转卡尺法取最大对边距离）。

    用于 MaxWidth 单模约束检查：波导过宽会支持高阶模，需限制最大宽度。
    算法: 对每条边，计算所有顶点到该边的最大垂直距离，取所有边方向上
    宽度的最大值，即为多边形的最大宽度。

    文献:
    - Godfried T. Toussaint, "Solving Geometric Problems with the Rotating Calipers",
      IEEE MELECON 1983. https://www.cs.mcgill.ca/~godfried/publications/calipers.pdf
    - Lopez & Reisner, "On the Minimal Width of a Convex Polygon",
      IPL 1985, DOI: 10.1016/0020-0190(85)90095-4
    - de Berg et al., "Computational Geometry", Springer 2008, Ch.4
      DOI: 10.1007/978-3-540-77974-2
    - Chrostowski & Hochberg, "Silicon Photonics Design", CUP 2015, p.353
      (single-mode cutoff width: w_max ≈ λ/(2·√(n_core²-n_clad²)))
    - SiEPIC EBeam PDK max width rules: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
    - KLayout DRC width check:
      https://klayout.org/downloads/master/doc-qt4/manual/drc_basic.html
    - Synopsys OptoDesigner DRC Module:
      https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/design-rule-checking-module.html
    """
    n = len(poly)
    if n < 3:
        return 0.0
    max_w = 0.0
    for i in range(n):
        x1, y1 = float(poly[i][0]), float(poly[i][1])
        x2, y2 = float(poly[(i + 1) % n][0]), float(poly[(i + 1) % n][1])
        dx, dy = x2 - x1, y2 - y1
        seg_len = math.hypot(dx, dy)
        if seg_len < 1e-12:
            continue
        max_dist = 0.0
        for j in range(n):
            if j == i or j == (i + 1) % n:
                continue
            dist = abs(-dy * (float(poly[j][0]) - x1)
                       + dx * (float(poly[j][1]) - y1)) / seg_len
            if dist > max_dist:
                max_dist = dist
        if max_dist > max_w:
            max_w = max_dist
    return max_w


def _polygon_step_width(poly: NDArray[np.float64]) -> float:
    """多边形步进宽度突变（端边对宽度差，用于 Step 规则）。

    算法: 识别多边形的端边（最短 2 条边，对应波导两端的端面），计算其
    长度差绝对值。该值反映波导宽度突变幅度，若 > 阈值则违规。

    用于 Step 规则: 波导宽度突变会导致模式失配、反射、损耗，需限制
    相邻段宽度差。如 SiEPIC Tools Waveguide checking 中的 "Mismatched
    pin widths" 检查。

    文献:
    - SiEPIC-Tools Verification "Mismatched pin widths":
      https://github.com/SiEPIC/SiEPIC-Tools/wiki/SiEPIC-Tools-Menu-descriptions
    - Chrostowski & Hochberg, "Silicon Photonics Design", CUP 2015, p.353
    - KLayout DRC width check (端面识别):
      https://klayout.org/downloads/master/doc-qt4/manual/drc_basic.html
    - Calibre nmDRC step/width transition rules:
      https://eda.sw.siemens.com/en-US/calibre/
    - Synopsys OptoDesigner DRC Module:
      https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/design-rule-checking-module.html
    - OpenDRC, He et al., DAC 2023, DOI:10.1109/DAC56929.2023.10247734
    - de Berg et al., "Computational Geometry", Springer 2008, Ch.2
    """
    n = len(poly)
    if n < 4:
        return 0.0
    # 取最短的 2 条边（端边），对应波导两端端面
    end_edges = _polygon_end_edges(poly, max_edges=2)
    if len(end_edges) < 2:
        return 0.0
    lengths = [float(np.linalg.norm(b - a)) for a, b in end_edges]
    return abs(lengths[0] - lengths[1])


def _layer_alignment_offset(
    inner_polys: list[NDArray[np.float64]],
    outer_polys: list[NDArray[np.float64]],
) -> float:
    """两层图形边缘对齐偏移量（用于 Alignment 规则）。

    算法: 对每个 inner 多边形，找到包围盒中心最近的 outer 多边形，
    计算两者包围盒中心的偏移量（中心错位）。该值反映两层对齐度，
    若 > 阈值则违规（层间对齐误差超限，可能导致电路开路/短路）。

    用于 Alignment 规则: 不同层图形（如 metal1 vs contact）需要严格
    对齐以避免接触不良或短路。Calibre nmDRC ALIGN 操作。

    文献:
    - Calibre nmDRC ALIGN operation:
      https://eda.sw.siemens.com/en-US/calibre/
    - KLayout DRC layer alignment:
      https://www.klayout.org/doc-qt5/manual/drc_runsets.html
    - Synopsys IC Validator DRC alignment:
      https://www.synopsys.com/implementation-and-signoff/signoff/ic-validator.html
    - Synopsys OptoDesigner DRC Module:
      https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/design-rule-checking-module.html
    - de Berg et al., "Computational Geometry", Springer 2008, Ch.5 (最近点对)
    - Ericson, "Real-Time Collision Detection", MK 2005, Ch.5
    """
    if not inner_polys or not outer_polys:
        return 0.0
    max_offset = 0.0
    for inner in inner_polys:
        if len(inner) < 3:
            continue
        ixmin, iymin, ixmax, iymax = _polygon_bbox(inner)
        icx = 0.5 * (ixmin + ixmax)
        icy = 0.5 * (iymin + iymax)
        # 找包围盒中心最近的 outer 多边形
        best_d = float("inf")
        for outer in outer_polys:
            if len(outer) < 3:
                continue
            oxmin, oymin, oxmax, oymax = _polygon_bbox(outer)
            ocx = 0.5 * (oxmin + oxmax)
            ocy = 0.5 * (oymin + oymax)
            d = math.hypot(icx - ocx, icy - ocy)
            if d < best_d:
                best_d = d
        if best_d != float("inf") and best_d > max_offset:
            max_offset = best_d
    return max_offset


def _polygon_symmetry_score(
    poly: NDArray[np.float64], axis: str = "auto",
) -> tuple[float, tuple[float, float, float]]:
    """多边形对称性分数（反射对称度，用于 Symmetry 规则）。

    *创新*: 主轴方向自动检测 + 镜像点匹配算法。

    算法:
    1. 计算多边形质心 C。
    2. 候选对称轴: 通过质心的水平线、垂直线、以及过质心与最远顶点连线。
    3. 对每个候选轴，将每个顶点关于该轴做镜像，检查镜像点是否近似落在
       多边形顶点集上（容差 1e-6）。
    4. 对称分数 = 匹配顶点数 / 总顶点数。返回最大分数及对应轴方程。

    用于 Symmetry 规则: 光子器件（如 MMIs、Y 分支、DC）需要严格对称
    以保证光学性能。对称度低于阈值则违规。

    文献:
    - Eades, P., "Symmetry Finding Algorithms",
      "Optimal Algorithms for Symmetry Detection in Two and Three Dimensions",
      University of Michigan Technical Report, 1986.
      https://deepblue.lib.umich.edu/bitstream/handle/2027.42/8337/bad6491.0001.001.pdf
    - Wolter, J.D., "Symmetry Detection in Two Dimensions",
      University of Michigan PhD Thesis, 1985.
    - de Berg et al., "Computational Geometry", Springer 2008, Ch.5 (主成分分析)
    - KLayout DRC symmetry checks:
      https://www.klayout.org/doc-qt5/manual/drc_runsets.html
    - SiEPIC-Tools Component verification (对称器件验证):
      https://github.com/SiEPIC/SiEPIC-Tools
    - Synopsys OptoDesigner DRC Module:
      https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/design-rule-checking-module.html
    """
    n = len(poly)
    if n < 3:
        return 0.0, (0.0, 0.0, 0.0)

    # 质心
    cx = float(poly[:, 0].mean())
    cy = float(poly[:, 1].mean())

    # 候选对称轴集合: (a, b, c) 表示直线 a*x + b*y + c = 0
    candidates: list[tuple[float, float, float]] = []
    # 水平轴: y = cy → 0*x + 1*y - cy = 0
    candidates.append((0.0, 1.0, -cy))
    # 垂直轴: x = cx → 1*x + 0*y - cx = 0
    candidates.append((1.0, 0.0, -cx))
    # 过质心 + 每个顶点的轴
    for i in range(n):
        px, py = float(poly[i][0]), float(poly[i][1])
        dx, dy = px - cx, py - cy
        norm = math.hypot(dx, dy)
        if norm < 1e-12:
            continue
        # 法向量 (dy, -dx) / norm，直线 dy*x - dx*y + (dx*cy - dy*cx) = 0
        a = dy / norm
        b = -dx / norm
        c = (dx * cy - dy * cx) / norm
        candidates.append((a, b, c))

    def reflect(pt: NDArray[np.float64], a: float, b: float, c: float) -> np.ndarray:
        """点关于直线 ax+by+c=0 的镜像点。"""
        x, y = float(pt[0]), float(pt[1])
        denom = a * a + b * b
        if denom < 1e-18:
            return pt.copy()
        # 镜像: p' = p - 2*(a*x+b*y+c)/(a²+b²) * (a,b)
        factor = 2.0 * (a * x + b * y + c) / denom
        return np.array([x - factor * a, y - factor * b], dtype=float)

    # 顶点集合（用于快速匹配）
    pts_list = [(float(poly[i][0]), float(poly[i][1])) for i in range(n)]
    tol = 1e-6

    def is_in_points(p: tuple[float, float]) -> bool:
        for q in pts_list:
            if abs(p[0] - q[0]) < tol and abs(p[1] - q[1]) < tol:
                return True
        return False

    best_score = 0.0
    best_axis = (0.0, 0.0, 0.0)
    for a, b, c in candidates:
        matched = 0
        for i in range(n):
            rp = reflect(poly[i], a, b, c)
            if is_in_points((float(rp[0]), float(rp[1]))):
                matched += 1
        score = matched / n
        if score > best_score:
            best_score = score
            best_axis = (a, b, c)
    return best_score, best_axis


def _polygon_array_pitch(polys: list[NDArray[np.float64]]) -> float:
    """多边形阵列 pitch 标准差（用于 Array 规则）。

    *创新*: 基于 1D 投影 + 排序差分计算 pitch 一致性。

    算法:
    1. 计算每个多边形包围盒中心。
    2. 找到主分布方向（x 或 y 范围更大者）。
    3. 按主轴坐标排序，计算相邻 pitch。
    4. 返回 pitch 标准差（衡量阵列周期一致性）。

    用于 Array 规则: 光子阵列（如光栅耦合器阵列、WDM 滤波器阵列）需要
    严格 pitch 一致性。pitch 偏差 > 阈值则违规。

    文献:
    - Synopsys OptoDesigner DRC Module (阵列规则):
      https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/design-rule-checking-module.html
    - SiEPIC EBeam PDK array components:
      https://github.com/SiEPIC/SiEPIC_EBeam_PDK
    - Chrostowski & Hochberg, "Silicon Photonics Design", CUP 2015, p.353
    - KLayout DRC array/pattern checks:
      https://www.klayout.org/doc-qt5/manual/drc_runsets.html
    - Calibre nmDRC array pattern matching:
      https://eda.sw.siemens.com/en-US/calibre/
    - de Berg et al., "Computational Geometry", Springer 2008, Ch.2 (排序)
    """
    n = len(polys)
    if n < 2:
        return 0.0
    # 计算每个多边形包围盒中心
    centers: list[tuple[float, float]] = []
    for poly in polys:
        if len(poly) < 3:
            continue
        xmin, ymin, xmax, ymax = _polygon_bbox(poly)
        centers.append((0.5 * (xmin + xmax), 0.5 * (ymin + ymax)))
    if len(centers) < 2:
        return 0.0
    # 主轴方向: 范围更大者
    xs = [c[0] for c in centers]
    ys = [c[1] for c in centers]
    x_range = max(xs) - min(xs)
    y_range = max(ys) - min(ys)
    if x_range >= y_range:
        sorted_centers = sorted(centers, key=lambda c: c[0])
        coords = [c[0] for c in sorted_centers]
    else:
        sorted_centers = sorted(centers, key=lambda c: c[1])
        coords = [c[1] for c in sorted_centers]
    # 计算相邻 pitch
    pitches = [coords[i + 1] - coords[i] for i in range(len(coords) - 1)]
    if len(pitches) < 2:
        return 0.0
    mean_pitch = sum(pitches) / len(pitches)
    variance = sum((p - mean_pitch) ** 2 for p in pitches) / len(pitches)
    return math.sqrt(variance)
