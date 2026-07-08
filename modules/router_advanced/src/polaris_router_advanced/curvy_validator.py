"""R21 路标：DRV-free 版图验证模块（从 curvy_router.py 拆分）。

实现 LiDAR ISPD'25 §4 的 DRV-free（零设计规则违反）版图验证：
- 弯曲半径检查（三点外接圆半径公式）
- 波导间距检查（线段对最小距离）

## 学术依据

- LiDAR: Automated Curvy Waveguide Detailed Routing（ISPD'25）§4
  URL: https://dl.acm.org/doi/pdf/10.1145/3698364.3705355
- LiDAR 2.0: Hierarchical Curvy Waveguide Detailed Routing（TCAD 2025）
  URL: https://scopex-asu.github.io/files/publications/PD_TCAD2025_LiDARv2.pdf
- 三点外接圆半径公式（R = |v1|*|v2|*|v1+v2| / (2*|v1×v2|)，第三边 = p3-p1 = v1+v2）
  来源: LiDAR ISPD'25 §3.2（R389 修正第三边向量：原 |v1-v2| 无几何意义，应为 |v1+v2|）
- SiEPIC EBeam PDK 设计规则（最小弯曲半径/波导间距）
  URL: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
  (SOI 平台 min_bend_radius=5μm, min_spacing=1μm 默认值依据)
- Chrostowski, "Silicon Photonics Design", Cambridge 2015
  https://www.cambridge.org/core/search?searchField=isbn&searchTerms=1107007731
  (§6.3 弯曲半径约束、§6.4 损耗系数，光子版图 DRC 验证理论)
- KLayout DRC 引擎（开源光子版图设计规则检查）
  https://www.klayout.de/doc_manual/drc.html
  (波导间距检查、弯曲半径检查 DRC 实现参考)

## 合规性

- project_rules.md 规则 14.1: 禁止 fall-back / 假数据 / mock
- project_rules.md 规则 18: 所有参数来自公开文献，标注来源 URL
- project_rules.md 规则 7.1: 文件 < 600 行
- R21 路标: docs/roundmap/R21.md
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np


class DRVFreeValidator:
    """DRV-free 版图验证器（零设计规则违反）。

    学术依据：LiDAR ISPD'25 §4（DRV-free 验证）
    URL: https://dl.acm.org/doi/pdf/10.1145/3698364.3705355
    """

    def __init__(self, min_bend_radius: float, min_spacing: float) -> None:
        """初始化 DRV-free 验证器。

        Args:
            min_bend_radius: 最小弯曲半径（μm）。
            min_spacing: 最小波导间距（μm）。

        Raises:
            ValueError: 参数非正。
        """
        if min_bend_radius <= 0:
            raise ValueError(
                f"min_bend_radius 必须 > 0，得到 {min_bend_radius}"
            )
        if min_spacing <= 0:
            raise ValueError(f"min_spacing 必须 > 0，得到 {min_spacing}")
        self.min_bend_radius = min_bend_radius
        self.min_spacing = min_spacing

    def validate(
        self, paths: list[list[tuple[float, float]]]
    ) -> dict[str, Any]:
        """验证版图是否 DRV-free。

        Args:
            paths: 路径列表。

        Returns:
            {is_drv_free: bool, violations: list, bend_violations: int, spacing_violations: int}
        """
        bend_violations = self.check_bend_radius(paths)
        spacing_violations = self.check_spacing(paths)
        all_violations = bend_violations + spacing_violations
        return {
            "is_drv_free": len(all_violations) == 0,
            "violations": all_violations,
            "bend_violations": len(bend_violations),
            "spacing_violations": len(spacing_violations),
        }

    def check_bend_radius(
        self, paths: list[list[tuple[float, float]]]
    ) -> list[dict[str, Any]]:
        """检查所有弯曲半径。

        Args:
            paths: 路径列表。

        Returns:
            违反列表 [{path_idx, point_idx, radius, min_required}, ...]。
        """
        violations: list[dict[str, Any]] = []
        for pi, path in enumerate(paths):
            if len(path) < 3:
                continue
            for k in range(1, len(path) - 1):
                p1, p2, p3 = path[k - 1], path[k], path[k + 1]
                v1 = np.array([p2[0] - p1[0], p2[1] - p1[1]], dtype=float)
                v2 = np.array([p3[0] - p2[0], p3[1] - p2[1]], dtype=float)
                cross = abs(v1[0] * v2[1] - v1[1] * v2[0])
                if cross < 1e-12:
                    continue  # 共线
                # R389 修复：三点外接圆半径公式第三边应为 p3-p1 = v1+v2
                # 原代码 v3 = v1 - v2（无几何意义），导致半径估算偏小约 55%，
                # DRV 验证器误报弯曲半径违规。与 curvy_astar_core.py:373 同步修复。
                # 数学验证: p1=(0,0), p2=(1,0), p3=(2,1):
                #   v1=(1,0), v2=(1,1), v3=v1+v2=(2,1), |v3|=√5
                #   正确 R = 1·√2·√5 / (2·1) = √10/2 ≈ 1.581
                #   bug R = 1·√2·|v1-v2|=|(0,-1)|=1 → R = √2·1/(2·1) = 0.707
                v3 = v1 + v2  # 第三边 p3-p1 = (p3-p2)+(p2-p1) = v2+v1
                r = (
                    float(np.hypot(*v1)) * float(np.hypot(*v2))
                    * float(np.hypot(*v3)) / (2.0 * cross)
                )
                if r < self.min_bend_radius:
                    violations.append({
                        "path_idx": pi,
                        "point_idx": k,
                        "radius": round(r, 6),
                        "min_required": self.min_bend_radius,
                    })
        return violations

    def check_spacing(
        self, paths: list[list[tuple[float, float]]]
    ) -> list[dict[str, Any]]:
        """检查波导间距。

        对每对路径，检查所有路径段对之间的最小距离。

        Args:
            paths: 路径列表。

        Returns:
            违反列表 [{path_i, path_j, seg_i, seg_j, distance, min_required}, ...]。
        """
        violations: list[dict[str, Any]] = []
        for i in range(len(paths)):
            for j in range(i + 1, len(paths)):
                pi = paths[i]
                pj = paths[j]
                for si in range(len(pi) - 1):
                    for sj in range(len(pj) - 1):
                        d = self._segment_distance(
                            pi[si], pi[si + 1], pj[sj], pj[sj + 1]
                        )
                        if d < self.min_spacing:
                            violations.append({
                                "path_i": i,
                                "path_j": j,
                                "seg_i": si,
                                "seg_j": sj,
                                "distance": round(d, 6),
                                "min_required": self.min_spacing,
                            })
        return violations

    def _segment_distance(
        self,
        a: tuple[float, float],
        b: tuple[float, float],
        c: tuple[float, float],
        d: tuple[float, float],
    ) -> float:
        """计算两线段最小距离。"""
        # 简化：采样线段上的点，取最小点-线段距离
        min_d = float("inf")
        n_samples = 10
        for t in np.linspace(0.0, 1.0, n_samples):
            px = a[0] + t * (b[0] - a[0])
            py = a[1] + t * (b[1] - a[1])
            d1 = self._point_segment_distance((px, py), c, d)
            min_d = min(min_d, d1)
        for t in np.linspace(0.0, 1.0, n_samples):
            px = c[0] + t * (d[0] - c[0])
            py = c[1] + t * (d[1] - c[1])
            d1 = self._point_segment_distance((px, py), a, b)
            min_d = min(min_d, d1)
        return min_d

    def _point_segment_distance(
        self,
        p: tuple[float, float],
        a: tuple[float, float],
        b: tuple[float, float],
    ) -> float:
        """点 p 到线段 ab 的距离。"""
        abx = b[0] - a[0]
        aby = b[1] - a[1]
        apx = p[0] - a[0]
        apy = p[1] - a[1]
        ab_sq = abx * abx + aby * aby
        if ab_sq < 1e-12:
            return math.hypot(apx, apy)
        t = (apx * abx + apy * aby) / ab_sq
        t = max(0.0, min(1.0, t))
        cx = a[0] + t * abx
        cy = a[1] + t * aby
        return math.hypot(p[0] - cx, p[1] - cy)
