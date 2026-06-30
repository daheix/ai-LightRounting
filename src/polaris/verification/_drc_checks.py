"""DRC 几何规则检查 Mixin（从 drc_curvilinear_18rules.py 拆分，R181-R200）。

包含 ``_DRCGeometricChecksMixin`` 类，提供 18 类曲线感知 DRC 规则的真实
几何检查算法。该 Mixin 由 ``CurvilinearDRCEngine`` 继承，依赖宿主类提供
``self._violations``（list[DRCViolation18]）与 ``self._rules``
（list[CurvilinearDRCRule]）属性。

拆分目的: 降低 ``drc_curvilinear_18rules.py`` 行数（1628 → ≤800），符合
AGENTS.md §8 文件≤800行质量门禁。

学术依据:
- KLayout DRC Reference (曲线感知规则)
  URL: https://klayout.org/downloads/master/doc-qt4/manual/drc_basic.html
- Siemens Calibre nmDRC
  URL: https://eda.sw.siemens.com/en-US/calibre/
- Synopsys OptoDesigner DRC Module（18 类曲线感知规则）
  URL: https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/design-rule-checking-module.html
- OpenDRC, He et al., DAC 2023, DOI:10.1109/DAC56929.2023.10247734
- PDRC, Jiang et al., DAC 2024
  URL: http://www.cse.cuhk.edu.hk/~byu/papers/C219-DAC2024-PDRC.pdf
- imec Curvilinear DRC
  URL: https://www.imec-int.com/en/articles/curvilinear-technology-game-changer-logic-technology-roadmap
- Ericson, Real-Time Collision Detection, MK 2005, Ch.5
- de Berg et al., Computational Geometry, Springer 2008

合规: R02 学术诚信 / R03 禁止 fall-back / R05 Bug 必修 / R04 不参与 GPU。
"""

from __future__ import annotations

from typing import Any

import numpy as np
from numpy.typing import NDArray

from ._drc_geometry import (
    _edge_to_edge_distance,
    _layer_density,
    _polygon_angles,
    _polygon_area,
    _polygon_bbox,
    _polygon_curvature,
    _polygon_end_edges,
    _polygon_extension,
    _polygon_min_enclosure,
    _polygon_min_width,
    _polygon_pair_min_distance,
    _polygon_taper_angle,
)
from ._drc_rules import CurvilinearDRCRule, DRCRuleCategory, DRCViolation18

__all__ = ["_DRCGeometricChecksMixin"]


class _DRCGeometricChecksMixin:
    """DRC 18 类几何检查 Mixin（R181-R200 从主引擎拆分）。

    宿主类需提供:
    - ``self._violations: list[DRCViolation18]``
    - ``self._rules: list[CurvilinearDRCRule]``

    本 Mixin 提供 18 类 ``_check_*_geo`` 真实几何检查方法 + 公共入口
    ``run_geometric_checks`` / ``_apply_single_rule`` / 包围盒辅助方法。
    """

    # ----- 包围盒与密度区域辅助 -----

    def _compute_global_bbox(
        self,
        polygons_by_layer: dict[str, list[NDArray[np.float64]]],
    ) -> tuple[float, float, float, float]:
        """计算所有图层多边形的全局包围盒。"""
        all_xmin = all_ymin = float("inf")
        all_xmax = all_ymax = float("-inf")
        for polys in polygons_by_layer.values():
            for poly in polys:
                if len(poly) < 3:
                    continue
                xmin, ymin, xmax, ymax = _polygon_bbox(poly)
                all_xmin = min(all_xmin, xmin)
                all_ymin = min(all_ymin, ymin)
                all_xmax = max(all_xmax, xmax)
                all_ymax = max(all_ymax, ymax)
        return all_xmin, all_ymin, all_xmax, all_ymax

    def _determine_density_region(
        self,
        density_region: tuple[float, float, float, float] | None,
        bbox: tuple[float, float, float, float],
    ) -> tuple[float, float, float, float]:
        """确定密度计算区域。"""
        if density_region is not None:
            return density_region
        all_xmin, all_ymin, all_xmax, all_ymax = bbox
        if all_xmin == float("inf"):
            return (0.0, 0.0, 100.0, 100.0)
        return (all_xmin, all_ymin, all_xmax, all_ymax)

    # ----- 公共入口 -----

    def _apply_single_rule(
        self,
        rule: CurvilinearDRCRule,
        polygons_by_layer: dict[str, list[NDArray[np.float64]]],
        enclosure_pairs: dict[str, str],
        density_region: tuple[float, float, float, float],
        net_assignments: dict[str, list[int]] | None,
    ) -> None:
        """应用单条 DRC 规则检查。"""
        layer = rule.layer
        polys = polygons_by_layer.get(layer, [])
        cat = rule.category
        val = rule.limit_value

        if not polys and cat not in {
            DRCRuleCategory.MIN_ENCLOSURE,
            DRCRuleCategory.MIN_EXTENSION,
        }:
            return

        if cat == DRCRuleCategory.MIN_WIDTH:
            self._check_min_width_geo(polys, rule, val)
        elif cat == DRCRuleCategory.MAX_WIDTH:
            self._check_max_width_geo(polys, rule, val)
        elif cat == DRCRuleCategory.MIN_WIDTH_CURVE:
            self._check_min_curve_width_geo(polys, rule, val)
        elif cat == DRCRuleCategory.MIN_SPACING:
            self._check_min_spacing_geo(polys, rule, val)
        elif cat == DRCRuleCategory.MIN_SPACING_SAME_NET:
            net_ids = net_assignments.get(layer) if net_assignments else None
            self._check_min_spacing_same_net_geo(polys, net_ids, rule, val)
        elif cat == DRCRuleCategory.MIN_SPACING_DENSITY:
            self._check_density_spacing_geo(polys, rule, val, density_region)
        elif cat == DRCRuleCategory.MIN_END_TO_END:
            self._check_end_to_end_geo(polys, rule, val)
        elif cat == DRCRuleCategory.MIN_ENCLOSURE:
            outer_layer = enclosure_pairs.get(layer, "")
            outer_polys = polygons_by_layer.get(outer_layer, [])
            if outer_polys:
                self._check_min_enclosure_geo(polys, outer_polys, rule, val)
        elif cat == DRCRuleCategory.MIN_EXTENSION:
            inner_layer = enclosure_pairs.get(layer, "")
            inner_polys = polygons_by_layer.get(inner_layer, [])
            if inner_polys:
                self._check_min_extension_geo(inner_polys, polys, rule, val)
        elif cat == DRCRuleCategory.MIN_AREA:
            self._check_min_area_geo(polys, rule, val)
        elif cat == DRCRuleCategory.MAX_AREA:
            self._check_max_area_geo(polys, rule, val)
        elif cat == DRCRuleCategory.MIN_DENSITY:
            self._check_min_density_geo(polys, rule, val, density_region)
        elif cat == DRCRuleCategory.MAX_ANGLE:
            self._check_max_angle_geo(polys, rule, val)
        elif cat == DRCRuleCategory.MIN_ANGLE:
            self._check_min_angle_geo(polys, rule, val)
        elif cat == DRCRuleCategory.ACUTE_ANGLE:
            self._check_acute_angle_geo(polys, rule, val)
        elif cat == DRCRuleCategory.MIN_BEND_RADIUS:
            self._check_min_bend_radius_geo(polys, rule, val)
        elif cat == DRCRuleCategory.MAX_CURVATURE:
            self._check_max_curvature_geo(polys, rule, val)
        elif cat == DRCRuleCategory.TAPER_ANGLE:
            self._check_taper_angle_geo(polys, rule, val)

    def run_geometric_checks(
        self,
        polygons_by_layer: dict[str, list[NDArray[np.float64]]],
        enclosure_pairs: dict[str, str] | None = None,
        density_region: tuple[float, float, float, float] | None = None,
        net_assignments: dict[str, list[int]] | None = None,
    ) -> list[DRCViolation18]:
        """基于真实多边形几何的 DRC 检查（18 类规则完整几何实现）。

        这是 VER-1 修复的核心：从预计算值读取 → 真实几何运算。
        支持: 宽度/间距/面积/角度/曲率/弯曲半径/锥形角度/包围/密度 等全部 18 类。

        Args:
            polygons_by_layer: {layer_name: [polygon_ndarray, ...]}，每个多边形为 (N,2) 数组
            enclosure_pairs: {inner_layer: outer_layer} 包围检查配对，如 {"contact": "metal1"}
            density_region: 密度计算区域 (xmin, ymin, xmax, ymax)，None 时用整体包围盒
            net_assignments: {layer_name: [net_id, ...]} 同网络间距(S2)所需的网络分配，
                每个图层的列表索引对应多边形索引。若 S2 规则存在但未提供，将 raise ValueError。

        Returns:
            DRC 违规列表

        学术依据:
        - KLayout DRC Reference: https://klayout.org/downloads/master/doc-qt4/manual/drc_basic.html
        - Siemens Calibre nmDRC: https://eda.sw.siemens.com/en-US/calibre/
        - Synopsys OptoDesigner DRC: https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/design-rule-checking-module.html
        - OpenDRC, He et al., DAC 2023, DOI:10.1109/DAC56929.2023.10247734
        - PDRC, Jiang et al., DAC 2024, http://www.cse.cuhk.edu.hk/~byu/papers/C219-DAC2024-PDRC.pdf
        - imec Curvilinear DRC: https://www.imec-int.com/en/articles/curvilinear-technology-game-changer-logic-technology-roadmap
        """
        self._violations: list[DRCViolation18] = []
        enclosure_pairs = enclosure_pairs or {}

        bbox = self._compute_global_bbox(polygons_by_layer)
        density_region = self._determine_density_region(density_region, bbox)

        for rule in self._rules:
            self._apply_single_rule(
                rule, polygons_by_layer, enclosure_pairs,
                density_region, net_assignments,
            )

        return self._violations

    # ----- 宽度类 (3) -----

    def _check_min_width_geo(
        self, polys: list[NDArray[np.float64]],
        rule: CurvilinearDRCRule, limit: float,
    ) -> None:
        for i, poly in enumerate(polys):
            if len(poly) < 3:
                continue
            w = _polygon_min_width(poly)
            if w > 0 and w < limit:
                cx, cy = float(poly[:, 0].mean()), float(poly[:, 1].mean())
                self._violations.append(DRCViolation18(
                    rule_name=rule.name, category=rule.category.value,
                    layer=rule.layer, severity=rule.severity,
                    message=f"多边形 {i} 最小宽度 {w:.3f}μm < {limit}μm",
                    location_um=(cx, cy), measured_value=w, limit_value=limit,
                ))

    def _check_max_width_geo(
        self, polys: list[NDArray[np.float64]],
        rule: CurvilinearDRCRule, limit: float,
    ) -> None:
        for i, poly in enumerate(polys):
            if len(poly) < 3:
                continue
            w = _polygon_min_width(poly)
            if w > limit:
                cx, cy = float(poly[:, 0].mean()), float(poly[:, 1].mean())
                self._violations.append(DRCViolation18(
                    rule_name=rule.name, category=rule.category.value,
                    layer=rule.layer, severity=rule.severity,
                    message=f"多边形 {i} 宽度 {w:.3f}μm > {limit}μm",
                    location_um=(cx, cy), measured_value=w, limit_value=limit,
                ))

    def _check_min_curve_width_geo(
        self, polys: list[NDArray[np.float64]],
        rule: CurvilinearDRCRule, limit: float,
    ) -> None:
        for i, poly in enumerate(polys):
            if len(poly) < 6:
                continue
            r_min, _ = _polygon_curvature(poly)
            if r_min < float("inf") and r_min > 0:
                w = _polygon_min_width(poly)
                if w > 0 and w < limit:
                    cx, cy = float(poly[:, 0].mean()), float(poly[:, 1].mean())
                    self._violations.append(DRCViolation18(
                        rule_name=rule.name, category=rule.category.value,
                        layer=rule.layer, severity=rule.severity,
                        message=f"曲线段 {i} 最小宽度 {w:.3f}μm < {limit}μm",
                        location_um=(cx, cy), measured_value=w, limit_value=limit,
                    ))

    # ----- 间距类 (4) -----

    def _check_min_spacing_geo(
        self, polys: list[NDArray[np.float64]],
        rule: CurvilinearDRCRule, limit: float,
    ) -> None:
        n = len(polys)
        for i in range(n):
            for j in range(i + 1, n):
                if len(polys[i]) < 3 or len(polys[j]) < 3:
                    continue
                s = _polygon_pair_min_distance(polys[i], polys[j])
                if s < limit:
                    cxi = float(polys[i][:, 0].mean())
                    cyi = float(polys[i][:, 1].mean())
                    self._violations.append(DRCViolation18(
                        rule_name=rule.name, category=rule.category.value,
                        layer=rule.layer, severity=rule.severity,
                        message=f"多边形 {i}-{j} 间距 {s:.3f}μm < {limit}μm",
                        location_um=(cxi, cyi), measured_value=s, limit_value=limit,
                    ))

    def _check_min_spacing_same_net_geo(
        self, polys: list[NDArray[np.float64]],
        net_ids: list[int] | None,
        rule: CurvilinearDRCRule, limit: float,
    ) -> None:
        """同网络间距检查（S2 独立算法，R121-R180 完善）。

        仅检查属于同一网络的多边形对间距。与 S1（MIN_SPACING）不同：
        S1 检查所有多边形对，S2 仅检查 net_id 相同的对。

        典型应用：同一光路径上的波导段间距需大于阈值以避免耦合；
        不同网络的波导间距由 S1 检查。

        算法:
        1. 若 net_ids 为 None，raise ValueError（R03 禁止 fall-back）
        2. 遍历同 net_id 的多边形对
        3. 跳过相连（距离=0）的多边形对
        4. 若间距 < limit，标记违规

        文献:
        - KLayout DRC space same_net option:
          https://klayout.org/downloads/master/doc-qt4/about/drc_ref_global.html
        - Calibre nmDRC same-net spacing:
          https://eda.sw.siemens.com/en-US/calibre/
        - Synopsys IC Validator same-net spacing
        - OpenDRC, He et al., DAC 2023
        - PDRC, Jiang et al., DAC 2024
        """
        if net_ids is None:
            raise ValueError(
                f"S2 同网络间距规则 '{rule.name}' 需要 net_ids 参数，"
                f"但传入 None。请在 run_geometric_checks 中提供 net_assignments。"
            )
        if len(net_ids) != len(polys):
            raise ValueError(
                f"net_ids 长度 {len(net_ids)} ≠ 多边形数 {len(polys)}"
            )

        n = len(polys)
        for i in range(n):
            for j in range(i + 1, n):
                if net_ids[i] != net_ids[j]:
                    continue  # 不同网络，由 S1 检查
                if len(polys[i]) < 3 or len(polys[j]) < 3:
                    continue
                s = _polygon_pair_min_distance(polys[i], polys[j])
                if s == 0.0:
                    continue  # 相连（同网络允许连接）
                if s < limit:
                    cxi = float(polys[i][:, 0].mean())
                    cyi = float(polys[i][:, 1].mean())
                    self._violations.append(DRCViolation18(
                        rule_name=rule.name, category=rule.category.value,
                        layer=rule.layer, severity=rule.severity,
                        message=f"同网络多边形 {i}-{j} 间距 {s:.3f}μm < {limit}μm",
                        location_um=(cxi, cyi), measured_value=s, limit_value=limit,
                    ))

    def _check_density_spacing_geo(
        self, polys: list[NDArray[np.float64]],
        rule: CurvilinearDRCRule, limit: float,
        region: tuple[float, float, float, float],
    ) -> None:
        density = _layer_density(polys, region)
        if density > 0.3:
            self._check_min_spacing_geo(polys, rule, limit)

    def _check_end_to_end_geo(
        self, polys: list[NDArray[np.float64]],
        rule: CurvilinearDRCRule, limit: float,
    ) -> None:
        """端到端间距检查（S4 独立算法，R121-R180 完善）。

        仅检查多边形端边（最短边）之间的距离，而非全部边对。用于波导
        耦合器等场景：两条波导端部面对面，需保证端到端最小间距。

        算法:
        1. 对每个多边形，识别端边（最短 ``max_edges`` 条边）
        2. 对每对多边形，计算端边间最短距离
        3. 若距离 < limit，标记违规

        文献:
        - Calibre nmDRC EXTernal end-to-end spacing
          https://eda.sw.siemens.com/en-US/calibre/
        - KLayout DRC separation (sep) check
          https://klayout.org/downloads/master/doc-qt4/about/drc_ref_global.html
        - Ericson, Real-Time Collision Detection, MK 2005, Ch.5
        - de Berg et al., Computational Geometry, Springer 2008
        - OpenDRC, He et al., DAC 2023
        """
        n = len(polys)
        if n < 2:
            return
        # 预计算每个多边形的端边
        end_edges_list: list[list[tuple[NDArray[np.float64], NDArray[np.float64]]]] = []
        for poly in polys:
            if len(poly) < 3:
                end_edges_list.append([])
            else:
                end_edges_list.append(_polygon_end_edges(poly))

        for i in range(n):
            if not end_edges_list[i]:
                continue
            for j in range(i + 1, n):
                if not end_edges_list[j]:
                    continue
                # 计算端边间最短距离
                min_d = float("inf")
                for a1, a2 in end_edges_list[i]:
                    for b1, b2 in end_edges_list[j]:
                        d = _edge_to_edge_distance(a1, a2, b1, b2)
                        if d < min_d:
                            min_d = d
                if min_d < limit:
                    cxi = float(polys[i][:, 0].mean())
                    cyi = float(polys[i][:, 1].mean())
                    self._violations.append(DRCViolation18(
                        rule_name=rule.name, category=rule.category.value,
                        layer=rule.layer, severity=rule.severity,
                        message=f"多边形 {i}-{j} 端到端间距 {min_d:.3f}μm < {limit}μm",
                        location_um=(cxi, cyi), measured_value=min_d, limit_value=limit,
                    ))

    # ----- 包围类 (2) -----

    def _check_min_enclosure_geo(
        self, inner_polys: list[NDArray[np.float64]],
        outer_polys: list[NDArray[np.float64]],
        rule: CurvilinearDRCRule, limit: float,
    ) -> None:
        for i, inner in enumerate(inner_polys):
            if len(inner) < 3:
                continue
            min_enc = float("inf")
            fully_enclosed = False
            for outer in outer_polys:
                if len(outer) < 3:
                    continue
                enc = _polygon_min_enclosure(inner, outer)
                if enc >= 0:
                    fully_enclosed = True
                    if enc < min_enc:
                        min_enc = enc
            cx, cy = float(inner[:, 0].mean()), float(inner[:, 1].mean())
            if not fully_enclosed:
                self._violations.append(DRCViolation18(
                    rule_name=rule.name, category=rule.category.value,
                    layer=rule.layer, severity=rule.severity,
                    message=f"内多边形 {i} 未被外多边形完全包围",
                    location_um=(cx, cy), measured_value=-1.0, limit_value=limit,
                ))
            elif min_enc < float("inf") and min_enc < limit:
                self._violations.append(DRCViolation18(
                    rule_name=rule.name, category=rule.category.value,
                    layer=rule.layer, severity=rule.severity,
                    message=f"内多边形 {i} 包围距离 {min_enc:.3f}μm < {limit}μm",
                    location_um=(cx, cy), measured_value=min_enc, limit_value=limit,
                ))

    def _check_min_extension_geo(
        self, inner_polys: list[NDArray[np.float64]],
        outer_polys: list[NDArray[np.float64]],
        rule: CurvilinearDRCRule, limit: float,
    ) -> None:
        """延伸检查（E2 独立算法，R121-R180 完善）。

        延伸检查 ≠ 包围检查。包围（E1）验证 inner 在 outer 内部且有边距；
        延伸（E2）验证 inner 超出 outer 向外延伸至少 limit。即 outer 应被
        inner 完全包含，且 outer 顶点到 inner 边的最小距离 ≥ limit。

        典型应用：金属层（inner）应延伸超出接触孔（outer）边缘至少 0.2μm，
        确保金属完全覆盖接触孔并有工艺余量。

        算法: 对每个 inner-outer 对，调用 ``_polygon_extension(inner, outer)``
        （等价于 ``_polygon_min_enclosure(outer, inner)``）。返回 -1 表示
        outer 未被 inner 包含（延伸不满足）；返回 ≥0 为实际延伸量。

        文献:
        - Calibre nmDRC ENClosure (ENC) 延伸语义:
          "检查 input_layer1 是否延伸超出 input_layer2"
          https://eda.sw.siemens.com/en-US/calibre/
        - KLayout DRC enclosing (反向用于延伸):
          https://klayout.org/downloads/master/doc-qt4/about/drc_ref_global.html
        - Synopsys IC Validator DRC extension check
        - OpenDRC, He et al., DAC 2023
        - PDRC, Jiang et al., DAC 2024
        """
        for i, inner in enumerate(inner_polys):
            if len(inner) < 3:
                continue
            max_ext = -1.0
            for outer in outer_polys:
                if len(outer) < 3:
                    continue
                # E2 延伸: outer（被检查层，如 metal1）应延伸超出 inner（配对层，如 contact）
                # _polygon_extension(outer, inner) = _polygon_min_enclosure(inner, outer)
                # = 检查 inner 是否在 outer 内部（即 outer 延伸超出 inner）
                ext = _polygon_extension(outer, inner)
                if ext > max_ext:
                    max_ext = ext
            cx, cy = float(inner[:, 0].mean()), float(inner[:, 1].mean())
            if max_ext < 0:
                self._violations.append(DRCViolation18(
                    rule_name=rule.name, category=rule.category.value,
                    layer=rule.layer, severity=rule.severity,
                    message=f"内多边形 {i} 未完全延伸超出外多边形",
                    location_um=(cx, cy), measured_value=-1.0, limit_value=limit,
                ))
            elif max_ext < limit:
                self._violations.append(DRCViolation18(
                    rule_name=rule.name, category=rule.category.value,
                    layer=rule.layer, severity=rule.severity,
                    message=f"内多边形 {i} 延伸量 {max_ext:.3f}μm < {limit}μm",
                    location_um=(cx, cy), measured_value=max_ext, limit_value=limit,
                ))

    # ----- 面积类 (3) -----

    def _check_min_area_geo(
        self, polys: list[NDArray[np.float64]],
        rule: CurvilinearDRCRule, limit: float,
    ) -> None:
        for i, poly in enumerate(polys):
            if len(poly) < 3:
                continue
            a = _polygon_area(poly)
            if a < limit:
                cx, cy = float(poly[:, 0].mean()), float(poly[:, 1].mean())
                self._violations.append(DRCViolation18(
                    rule_name=rule.name, category=rule.category.value,
                    layer=rule.layer, severity=rule.severity,
                    message=f"多边形 {i} 面积 {a:.1f}μm² < {limit}μm²",
                    location_um=(cx, cy), measured_value=a, limit_value=limit,
                ))

    def _check_max_area_geo(
        self, polys: list[NDArray[np.float64]],
        rule: CurvilinearDRCRule, limit: float,
    ) -> None:
        for i, poly in enumerate(polys):
            if len(poly) < 3:
                continue
            a = _polygon_area(poly)
            if a > limit:
                cx, cy = float(poly[:, 0].mean()), float(poly[:, 1].mean())
                self._violations.append(DRCViolation18(
                    rule_name=rule.name, category=rule.category.value,
                    layer=rule.layer, severity=rule.severity,
                    message=f"多边形 {i} 面积 {a:.1f}μm² > {limit}μm²",
                    location_um=(cx, cy), measured_value=a, limit_value=limit,
                ))

    def _check_min_density_geo(
        self, polys: list[NDArray[np.float64]],
        rule: CurvilinearDRCRule, limit: float,
        region: tuple[float, float, float, float],
    ) -> None:
        d = _layer_density(polys, region)
        if d < limit:
            cx = (region[0] + region[2]) / 2
            cy = (region[1] + region[3]) / 2
            self._violations.append(DRCViolation18(
                rule_name=rule.name, category=rule.category.value,
                layer=rule.layer, severity=rule.severity,
                message=f"密度 {d:.1%} < {limit:.1%}",
                location_um=(cx, cy), measured_value=d, limit_value=limit,
            ))

    # ----- 角度类 (3) -----

    def _check_max_angle_geo(
        self, polys: list[NDArray[np.float64]],
        rule: CurvilinearDRCRule, limit: float,
    ) -> None:
        for i, poly in enumerate(polys):
            if len(poly) < 3:
                continue
            angles = _polygon_angles(poly)
            max_ang = float(np.max(angles))
            if max_ang > limit:
                cx, cy = float(poly[:, 0].mean()), float(poly[:, 1].mean())
                self._violations.append(DRCViolation18(
                    rule_name=rule.name, category=rule.category.value,
                    layer=rule.layer, severity=rule.severity,
                    message=f"多边形 {i} 最大拐角 {max_ang:.1f}° > {limit}°",
                    location_um=(cx, cy), measured_value=max_ang, limit_value=limit,
                ))

    def _check_min_angle_geo(
        self, polys: list[NDArray[np.float64]],
        rule: CurvilinearDRCRule, limit: float,
    ) -> None:
        for i, poly in enumerate(polys):
            if len(poly) < 3:
                continue
            angles = _polygon_angles(poly)
            min_ang = float(np.min(angles))
            if min_ang < limit:
                cx, cy = float(poly[:, 0].mean()), float(poly[:, 1].mean())
                self._violations.append(DRCViolation18(
                    rule_name=rule.name, category=rule.category.value,
                    layer=rule.layer, severity=rule.severity,
                    message=f"多边形 {i} 最小拐角 {min_ang:.1f}° < {limit}°",
                    location_um=(cx, cy), measured_value=min_ang, limit_value=limit,
                ))

    def _check_acute_angle_geo(
        self, polys: list[NDArray[np.float64]],
        rule: CurvilinearDRCRule, limit: float,
    ) -> None:
        self._check_min_angle_geo(polys, rule, limit)

    # ----- 曲线类 (3) -----

    def _check_min_bend_radius_geo(
        self, polys: list[NDArray[np.float64]],
        rule: CurvilinearDRCRule, limit: float,
    ) -> None:
        for i, poly in enumerate(polys):
            if len(poly) < 6:
                continue
            r_min, _ = _polygon_curvature(poly)
            if r_min < float("inf") and r_min < limit:
                cx, cy = float(poly[:, 0].mean()), float(poly[:, 1].mean())
                self._violations.append(DRCViolation18(
                    rule_name=rule.name, category=rule.category.value,
                    layer=rule.layer, severity=rule.severity,
                    message=f"曲线 {i} 最小弯曲半径 {r_min:.2f}μm < {limit}μm",
                    location_um=(cx, cy), measured_value=r_min, limit_value=limit,
                ))

    def _check_max_curvature_geo(
        self, polys: list[NDArray[np.float64]],
        rule: CurvilinearDRCRule, limit: float,
    ) -> None:
        for i, poly in enumerate(polys):
            if len(poly) < 6:
                continue
            _, k_max = _polygon_curvature(poly)
            if k_max > limit:
                cx, cy = float(poly[:, 0].mean()), float(poly[:, 1].mean())
                self._violations.append(DRCViolation18(
                    rule_name=rule.name, category=rule.category.value,
                    layer=rule.layer, severity=rule.severity,
                    message=f"曲线 {i} 最大曲率 {k_max:.3f} 1/μm > {limit} 1/μm",
                    location_um=(cx, cy), measured_value=k_max, limit_value=limit,
                ))

    def _check_taper_angle_geo(
        self, polys: list[NDArray[np.float64]],
        rule: CurvilinearDRCRule, limit: float,
    ) -> None:
        for i, poly in enumerate(polys):
            if len(poly) < 4:
                continue
            ta = _polygon_taper_angle(poly)
            if ta > limit:
                cx, cy = float(poly[:, 0].mean()), float(poly[:, 1].mean())
                self._violations.append(DRCViolation18(
                    rule_name=rule.name, category=rule.category.value,
                    layer=rule.layer, severity=rule.severity,
                    message=f"锥形 {i} 张角 {ta:.1f}° > {limit}°",
                    location_um=(cx, cy), measured_value=ta, limit_value=limit,
                ))
