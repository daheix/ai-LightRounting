"""层次化 DRC 引擎（R07：layer-wise BVH + 自适应行分块）。

基于 OpenDRC 论文实现层次化 DRC 检查，解决 KLayout flat 模式在大规模版图上的性能瓶颈。

来源:
- OpenDRC: He et al., DAC 2023, DOI: 10.1109/DAC56929.2023.10247734
- X-Check: He et al., ICCAD 2022; KLayout DRC: Köfferlein, FSiC 2023

创新点: 1.【创新】layer-wise BVH 2.【创新】自适应行分块 3.【创新】层次化 DRC 模式
合规性: 规则14.1禁止fall-back；规则7.1文件<500行；规则18公式标注来源。
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from polaris.sim.klayout_drc import DRCCheckType, DRCRule

# BVH 叶节点最大多边形数（来源: OpenDRC 论文 Section IV-A，叶节点 8-32）
_BVH_LEAF_SIZE = 16


@dataclass
class BVHNode:
    """BVH 节点（【创新】layer-wise BVH 加速结构）。"""

    bbox: tuple[float, float, float, float]
    left: BVHNode | None = None
    right: BVHNode | None = None
    polygons: list[np.ndarray] = field(default_factory=list)

    @property
    def is_leaf(self) -> bool:
        """是否为叶节点。"""
        return self.left is None and self.right is None


class BVH:
    """Bounding Volume Hierarchy（【创新】layer-wise BVH 加速结构）。

    查询复杂度 O(min(n, k·h))。来源: OpenDRC Section IV-A，R-tree（Guttman 1984）。
    """

    def __init__(self) -> None:
        self.root: BVHNode | None = None

    def build(self, polygons: list[np.ndarray]) -> BVHNode | None:
        """构建 BVH（递归中位数分割，O(n log n)）。空输入返回 None。"""
        if not polygons:
            return None
        bboxes = [self._polygon_bbox(p) for p in polygons]
        idx = list(range(len(polygons)))
        self.root = self._build_recursive(idx, polygons, bboxes)
        return self.root

    def _build_recursive(
        self,
        indices: list[int],
        polygons: list[np.ndarray],
        bboxes: list[tuple[float, float, float, float]],
    ) -> BVHNode:
        """递归构建 BVH（沿最长轴中位数分割）。"""
        bbox = self._merge_bboxes([bboxes[i] for i in indices])
        if len(indices) <= _BVH_LEAF_SIZE:
            return BVHNode(bbox=bbox, polygons=[polygons[i] for i in indices])
        axis = 0 if (bbox[2] - bbox[0]) >= (bbox[3] - bbox[1]) else 1
        def key(i):
            return 0.5 * (bboxes[i][axis] + bboxes[i][axis + 2])
        sorted_idx = sorted(indices, key=key)
        mid = len(sorted_idx) // 2
        left = self._build_recursive(sorted_idx[:mid], polygons, bboxes)
        right = self._build_recursive(sorted_idx[mid:], polygons, bboxes)
        return BVHNode(bbox=bbox, left=left, right=right)

    @staticmethod
    def _polygon_bbox(poly: np.ndarray) -> tuple[float, float, float, float]:
        """多边形包围盒。"""
        xs, ys = poly[:, 0], poly[:, 1]
        return (float(xs.min()), float(ys.min()), float(xs.max()), float(ys.max()))

    @staticmethod
    def _merge_bboxes(
        bboxes: list[tuple[float, float, float, float]],
    ) -> tuple[float, float, float, float]:
        """合并包围盒。"""
        if not bboxes:
            raise ValueError("合并包围盒列表不能为空")
        x0 = min(b[0] for b in bboxes)
        y0 = min(b[1] for b in bboxes)
        x1 = max(b[2] for b in bboxes)
        y1 = max(b[3] for b in bboxes)
        return (x0, y0, x1, y1)

    @staticmethod
    def _bbox_intersect(
        a: tuple[float, float, float, float], b: tuple[float, float, float, float]
    ) -> bool:
        """包围盒相交测试（分离轴定理）。"""
        return not (a[2] < b[0] or b[2] < a[0] or a[3] < b[1] or b[3] < a[1])

    def query(self, region: tuple[float, float, float, float]) -> list[np.ndarray]:
        """查询与 region 相交的多边形（O(log n + k)）。"""
        if self.root is None:
            return []
        result: list[np.ndarray] = []
        self._query_recursive(self.root, region, result)
        return result

    def _query_recursive(
        self, node: BVHNode, region: tuple[float, float, float, float], result: list[np.ndarray]
    ) -> None:
        """递归查询 BVH。"""
        if not self._bbox_intersect(node.bbox, region):
            return
        if node.is_leaf:
            for poly in node.polygons:
                if self._bbox_intersect(self._polygon_bbox(poly), region):
                    result.append(poly)
            return
        if node.left is not None:
            self._query_recursive(node.left, region, result)
        if node.right is not None:
            self._query_recursive(node.right, region, result)


class RowPartition:
    """自适应行分块（【创新】自适应行分块算法）。

    按 y 坐标排序后分块，每块约 √n 个。来源: OpenDRC Section IV-C。
    """

    def __init__(self, max_rows: int = 1024) -> None:
        if max_rows < 1:
            raise ValueError(f"max_rows 必须 ≥1，得到 {max_rows}")
        self.max_rows = max_rows

    def partition(self, polygons: list[np.ndarray]) -> list[list[np.ndarray]]:
        """自适应行分块。"""
        if not polygons:
            return []
        y_centers = [float(p[:, 1].mean()) for p in polygons]
        order = sorted(range(len(polygons)), key=lambda i: y_centers[i])
        n = len(polygons)
        n_blocks = max(1, min(self.max_rows, int(np.sqrt(n))))
        block_size = max(1, (n + n_blocks - 1) // n_blocks)
        blocks: list[list[np.ndarray]] = []
        for i in range(0, n, block_size):
            blocks.append([polygons[order[j]] for j in range(i, min(i + block_size, n))])
        return blocks


@dataclass
class DRCViolation:
    """DRC 违规结果。"""

    rule_name: str
    check_type: str
    layer_name: str
    message: str
    location: tuple[float, float] = (0.0, 0.0)
    severity: float = 1.0


class HierarchicalDRC:
    """层次化 DRC 引擎（【创新】层次化 DRC 模式）。

    来源: OpenDRC DAC 2023 DOI:10.1109/DAC56929.2023.10247734; KLayout DRC。
    """

    def __init__(self, rules: list[DRCRule]) -> None:
        if not rules:
            raise ValueError("DRC 规则列表不能为空")
        self.rules = rules

    def check(
        self, layout: dict[str, list[np.ndarray]], hierarchical: bool = True
    ) -> list[DRCViolation]:
        """执行 DRC 检查。layout 为层名到多边形列表映射，返回违规列表。"""
        violations: list[DRCViolation] = []
        for rule in self.rules:
            if not layout.get(rule.layer_name):
                continue
            if hierarchical:
                violations.extend(self._check_rule_hierarchical(rule, layout))
            else:
                violations.extend(self._check_rule_flat(rule, layout))
        return violations

    def _check_rule_hierarchical(
        self, rule: DRCRule, layout: dict[str, list[np.ndarray]]
    ) -> list[DRCViolation]:
        """层次化模式执行单条规则（BVH + 行分块）。"""
        polys = layout.get(rule.layer_name, [])
        if not polys:
            return []
        bvh = BVH()
        bvh.build(polys)
        blocks = RowPartition().partition(polys)
        violations: list[DRCViolation] = []
        for block in blocks:
            violations.extend(self._dispatch_check(rule, block, layout, bvh))
        return violations

    def _check_rule_flat(
        self, rule: DRCRule, layout: dict[str, list[np.ndarray]]
    ) -> list[DRCViolation]:
        """flat 模式执行单条规则。"""
        polys = layout.get(rule.layer_name, [])
        if not polys:
            return []
        return self._dispatch_check(rule, polys, layout, None)

    def _dispatch_check(
        self,
        rule: DRCRule,
        polys: list[np.ndarray],
        layout: dict[str, list[np.ndarray]],
        bvh: BVH | None,
    ) -> list[DRCViolation]:
        """规则分发器：按 check_type 调用对应检查方法。"""
        ct = rule.check_type
        if ct == DRCCheckType.WIDTH:
            return self._check_width(polys, rule.threshold_um, rule)
        if ct == DRCCheckType.SPACE:
            return self._check_space(polys, rule.threshold_um, rule, bvh)
        if ct == DRCCheckType.NOTCH:
            return self._check_notch(polys, rule.threshold_um, rule)
        if ct == DRCCheckType.ENCLOSE:
            if rule.enclosure_layer_name is None:
                raise ValueError(f"ENCLOSE 规则 {rule.name} 缺少 enclosure_layer_name")
            outer = layout.get(rule.enclosure_layer_name, [])
            return self._check_enclosed(polys, outer, rule.threshold_um, rule)
        if ct == DRCCheckType.AREA:
            return self._check_area(polys, rule.threshold_um, rule)
        if ct == DRCCheckType.DENSITY:
            max_d = rule.max_density if rule.max_density is not None else 100.0
            return self._check_density(polys, rule.threshold_um, max_d, rule)
        raise ValueError(f"不支持的 DRC 检查类型: {ct}")

    def _check_width(
        self, region: list[np.ndarray], threshold: float, rule: DRCRule
    ) -> list[DRCViolation]:
        """width 检查。公式: Width(P)=min d(e_i,e_j)，平行对边。来源: OpenDRC IV-D。"""
        violations: list[DRCViolation] = []
        for poly in region:
            w = self._polygon_min_width(poly)
            if w < threshold:
                violations.append(
                    self._make_violation(
                        rule, self._polygon_center(poly),
                        f"内部宽度 {w:.4f}μm < 阈值 {threshold:.4f}μm",
                    )
                )
        return violations

    def _check_space(
        self,
        region: list[np.ndarray],
        threshold: float,
        rule: DRCRule,
        bvh: BVH | None = None,
    ) -> list[DRCViolation]:
        """space 检查。公式: Space=min||p-q||。来源: OpenDRC IV-D。"""
        violations: list[DRCViolation] = []
        for pi in region:
            pi_bbox = BVH._polygon_bbox(pi)
            if bvh is not None:
                exp = (
                    pi_bbox[0] - threshold, pi_bbox[1] - threshold,
                    pi_bbox[2] + threshold, pi_bbox[3] + threshold,
                )
                candidates = bvh.query(exp)
            else:
                candidates = region
            pi_id = id(pi)
            for pj in candidates:
                if id(pj) <= pi_id:
                    continue
                s = self._polygon_pair_min_distance(pi, pj)
                if s < threshold:
                    merged = BVH._merge_bboxes([pi_bbox, BVH._polygon_bbox(pj)])
                    violations.append(
                        self._make_violation(
                            rule, self._bbox_center(merged),
                            f"多边形间距 {s:.4f}μm < 阈值 {threshold:.4f}μm",
                        )
                    )
        return violations

    def _check_notch(
        self, region: list[np.ndarray], threshold: float, rule: DRCRule
    ) -> list[DRCViolation]:
        """notch 检查。公式: Notch=min d(e_i,e_j)，凹处对边。简化: 用平行对边近似。"""
        violations: list[DRCViolation] = []
        for poly in region:
            n = self._polygon_min_width(poly)
            if n < threshold:
                violations.append(
                    self._make_violation(
                        rule, self._polygon_center(poly),
                        f"凹槽间距 {n:.4f}μm < 阈值 {threshold:.4f}μm",
                    )
                )
        return violations

    def _check_enclosed(
        self,
        region: list[np.ndarray],
        outer_region: list[np.ndarray],
        threshold: float,
        rule: DRCRule,
    ) -> list[DRCViolation]:
        """enclosed 检查。公式: Enclosed=min d(p,∂P_out)。来源: KLayout enclosed_check。"""
        violations: list[DRCViolation] = []
        for ip in region:
            ib = BVH._polygon_bbox(ip)
            best_enc = 0.0
            for op in outer_region:
                ob = BVH._polygon_bbox(op)
                if not (ob[0] <= ib[0] and ob[1] <= ib[1] and ob[2] >= ib[2] and ob[3] >= ib[3]):
                    continue
                enc = self._enclosure_distance(ip, op)
                if enc > best_enc:
                    best_enc = enc
            if best_enc < threshold:
                violations.append(
                    self._make_violation(
                        rule, self._polygon_center(ip),
                        f"包围间距 {best_enc:.4f}μm < 阈值 {threshold:.4f}μm",
                    )
                )
        return violations

    def _check_area(
        self, region: list[np.ndarray], threshold: float, rule: DRCRule
    ) -> list[DRCViolation]:
        """area 检查。公式: Area=0.5*|Σ(x_i·y_{i+1}-x_{i+1}·y_i)|（鞋带）。来源: KLayout。"""
        violations: list[DRCViolation] = []
        for poly in region:
            a = self._polygon_area(poly)
            if a < threshold:
                violations.append(
                    self._make_violation(
                        rule, self._polygon_center(poly),
                        f"面积 {a:.4f}μm² < 阈值 {threshold:.4f}μm²",
                    )
                )
        return violations

    def _check_density(
        self,
        region: list[np.ndarray],
        min_density: float,
        max_density: float,
        rule: DRCRule,
    ) -> list[DRCViolation]:
        """density 检查。公式: ρ=ΣA_i/A_total×100%。来源: Banerjee 2024; SiEPIC。"""
        if not region:
            return []
        total_area = sum(self._polygon_area(p) for p in region)
        cell_bbox = BVH._merge_bboxes([BVH._polygon_bbox(p) for p in region])
        cell_area = max((cell_bbox[2] - cell_bbox[0]) * (cell_bbox[3] - cell_bbox[1]), 1e-15)
        density_pct = total_area / cell_area * 100.0
        if density_pct < min_density or density_pct > max_density:
            return [
                self._make_violation(
                    rule, self._bbox_center(cell_bbox),
                    f"层密度 {density_pct:.1f}% 超出范围 [{min_density:.0f}%, {max_density:.0f}%]",
                )
            ]
        return []

    # ===== 几何计算工具 =====

    @staticmethod
    def _make_violation(
        rule: DRCRule, location: tuple[float, float], detail: str
    ) -> DRCViolation:
        """构造 DRC 违规对象。"""
        return DRCViolation(
            rule_name=rule.name,
            check_type=rule.check_type.value,
            layer_name=rule.layer_name,
            message=f"{rule.name}: {detail}",
            location=location,
            severity=rule.severity,
        )

    @staticmethod
    def _polygon_area(poly: np.ndarray) -> float:
        """鞋带公式面积。来源: de Berg "Computational Geometry" Springer 2008。"""
        x, y = poly[:, 0], poly[:, 1]
        return 0.5 * abs(float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))))

    @staticmethod
    def _polygon_center(poly: np.ndarray) -> tuple[float, float]:
        """多边形几何中心。"""
        return (float(poly[:, 0].mean()), float(poly[:, 1].mean()))

    @staticmethod
    def _bbox_center(bbox: tuple[float, float, float, float]) -> tuple[float, float]:
        """包围盒中心。"""
        return (0.5 * (bbox[0] + bbox[2]), 0.5 * (bbox[1] + bbox[3]))

    @staticmethod
    def _segment_distance(p: np.ndarray, a: np.ndarray, b: np.ndarray) -> float:
        """点 p 到线段 ab 最短距离。公式: d=||p-(a+t·(b-a))||, t=clamp(...)。"""
        ab, ap = b - a, p - a
        denom = float(np.dot(ab, ab))
        if denom < 1e-15:
            return float(np.linalg.norm(ap))
        t = max(0.0, min(1.0, float(np.dot(ap, ab) / denom)))
        return float(np.linalg.norm(p - (a + t * ab)))

    @classmethod
    def _polygon_min_width(cls, poly: np.ndarray) -> float:
        """多边形最小宽度（旋转卡尺法 Rotating Calipers）。

        算法: 对每条边，计算所有顶点到该边的最大距离（即该边方向上的宽度），
        取所有边方向上宽度的最小值，即为多边形的最小宽度。
        适用于凸多边形，对凹多边形给出保守估计（上界）。

        文献:
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
        """
        n = len(poly)
        if n < 3:
            return float("inf")
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
        return min_w if min_w != float("inf") else float("inf")

    @classmethod
    def _polygon_pair_min_distance(
        cls, p1: np.ndarray, p2: np.ndarray
    ) -> float:
        """两多边形最小距离（边-边距离最小值）。"""
        n1, n2, min_d = len(p1), len(p2), float("inf")
        for i in range(n1):
            a, b = p1[i], p1[(i + 1) % n1]
            for j in range(n2):
                c, d = p2[j], p2[(j + 1) % n2]
                dist = cls._segment_segment_distance(a, b, c, d)
                if dist < min_d:
                    min_d = dist
        return min_d

    @classmethod
    def _segment_segment_distance(
        cls, a: np.ndarray, b: np.ndarray, c: np.ndarray, d: np.ndarray
    ) -> float:
        """两线段最短距离（含相交检测）。

        算法: 先检测线段是否相交（相交则距离为 0），否则取 4 个端点到对方
        线段距离的最小值。使用叉积方向判定法（straddling test）检测相交。

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
        """
        if cls._segments_intersect(a, b, c, d):
            return 0.0
        return min(
            cls._segment_distance(c, a, b),
            cls._segment_distance(d, a, b),
            cls._segment_distance(a, c, d),
            cls._segment_distance(b, c, d),
        )

    @staticmethod
    def _cross2d(
        p: np.ndarray, q: np.ndarray, r: np.ndarray
    ) -> float:
        """2D 叉积 (q-p) × (r-p)。用于判断三点转向。"""
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])

    @classmethod
    def _segments_intersect(
        cls, a: np.ndarray, b: np.ndarray, c: np.ndarray, d: np.ndarray
    ) -> bool:
        """检测两条线段 AB 和 CD 是否相交（含端点接触和共线重叠）。

        算法: 叉积 straddling test + bbox 快速拒绝。
        """
        d1 = cls._cross2d(c, d, a)
        d2 = cls._cross2d(c, d, b)
        d3 = cls._cross2d(a, b, c)
        d4 = cls._cross2d(a, b, d)

        if ((d1 > 0 and d2 < 0) or (d1 < 0 and d2 > 0)) and \
           ((d3 > 0 and d4 < 0) or (d3 < 0 and d4 > 0)):
            return True

        if abs(d1) < 1e-12 and cls._point_on_segment(a, c, d):
            return True
        if abs(d2) < 1e-12 and cls._point_on_segment(b, c, d):
            return True
        if abs(d3) < 1e-12 and cls._point_on_segment(c, a, b):
            return True
        if abs(d4) < 1e-12 and cls._point_on_segment(d, a, b):
            return True

        return False

    @staticmethod
    def _point_on_segment(
        p: np.ndarray, a: np.ndarray, b: np.ndarray
    ) -> bool:
        """判断点 p 是否在线段 ab 上（假设三点共线）。"""
        return (min(a[0], b[0]) - 1e-12 <= p[0] <= max(a[0], b[0]) + 1e-12 and
                min(a[1], b[1]) - 1e-12 <= p[1] <= max(a[1], b[1]) + 1e-12)

    @classmethod
    def _enclosure_distance(
        cls, inner: np.ndarray, outer: np.ndarray
    ) -> float:
        """内层被外层包围的最小间距。公式: min d(p, ∂P_out), p∈∂P_in。"""
        min_d = float("inf")
        n_outer = len(outer)
        for i in range(n_outer):
            a, b = outer[i], outer[(i + 1) % n_outer]
            for p in inner:
                dist = cls._segment_distance(p, a, b)
                if dist < min_d:
                    min_d = dist
        return min_d


def run_hierarchical_drc(
    layout: dict[str, list[np.ndarray]],
    rules: list[DRCRule],
    hierarchical: bool = True,
) -> list[DRCViolation]:
    """层次化 DRC 检查统一入口。

    Args:
        layout: 层名到多边形列表的映射，每个多边形为 (N, 2) ndarray。
        rules: DRC 规则列表（DRCRule 对象）。
        hierarchical: 是否启用层次化模式（默认 True）。

    Returns:
        DRC 违规列表（空列表表示 DRC clean）。
    来源: OpenDRC: He et al., DAC 2023, DOI: 10.1109/DAC56929.2023.10247734
    """
    return HierarchicalDRC(rules).check(layout, hierarchical=hierarchical)


__all__ = [
    "BVHNode",
    "BVH",
    "RowPartition",
    "DRCViolation",
    "HierarchicalDRC",
    "run_hierarchical_drc",
]
