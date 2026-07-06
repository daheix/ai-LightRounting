"""DRC P0 波导级规则 Mixin（polaris-drc 子模块，引擎层）。

从 ``engine.py`` 拆分（R11 质量门禁：单文件 ≤800 行），保持
``DRCEngine`` 类的公开 API 完全一致。本模块以 Mixin 形式提供 6 条
P0 波导级规则检查方法，由 ``DRCEngine`` 继承:

- BEND_RADIUS_MIN: 波导弯曲半径最小值
- WAVEGUIDE_WIDTH_MATCH: 连接两端波导宽度匹配
- MIN_NOTCH: 两器件平行边窄颈
- WAVEGUIDE_MANHATTAN: 波导首末段 Manhattan
- ENCLOSED_AREA_MIN: 连接图环封闭面积
- CROSSING_ANGULAR: 波导交叉角度

仅依赖 numpy（R04: 不参与 GPU）。

## 来源（R02 学术诚信，≥5 个文献 URL）
- SiEPIC EBeam PDK DRC runset（bend_radius=5μm, crossing 90°）
  https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- SiEPIC-Tools Verification（Mismatched pin widths / Manhattan / Radius）
  https://github-wiki-see.page/m/SiEPIC/SiEPIC-Tools/wiki/SiEPIC-Tools-Menu-descriptions
- LiDAR 2.0: Zhou et al. arXiv:2505.17239v1, ISPD 2025（Bend Radius/Crossing）
  https://arxiv.org/html/2505.17239v1
- FluxCore DRC 文档（MIN_NOTCH=100nm, MIN_BEND_RADIUS=5-10μm）
  https://www.fluxcoredynamics.com/docs/design-rules
- KLayout DRC 文档（width_check/space_check/area_check/notch）
  https://www.klayout.org/doc-qt5/manual/drc_runsets.html
- Chrostowski & Hochberg, "Silicon Photonics Design", CUP 2015 §4.3
  https://www.cambridge.org/core/books/silicon-photonics-design/
- Berg et al. 2014, "Computational Geometry", Springer（AABB 相交/距离）
  https://doi.org/10.1007/978-3-540-77974-2
"""

from __future__ import annotations

from polaris_drc.checks import (
    aabb,
    aabb_center,
    aabb_distance,
    aabb_orientation,
    aabb_overlap,
    build_device_map,
    detect_connection_cycles,
    device_waveguide_width,
    find_port,
    is_waveguide_device,
    merge_aabb,
    port_abs,
)
from polaris_drc.rules import (
    DRCRule,
    DRCViolation,
    VALID_DIRECTIONS,
    normalize_direction,
)

__all__ = ["WaveguideRulesMixin"]


class WaveguideRulesMixin:
    """P0 波导级 DRC 规则 Mixin（6 条，2026-07-05 新增）。

    由 ``DRCEngine`` 继承，提供以下检查方法:
        - ``_check_bend_radius_min``: BEND_RADIUS_MIN
        - ``_check_waveguide_width_match``: WAVEGUIDE_WIDTH_MATCH
        - ``_check_min_notch``: MIN_NOTCH
        - ``_check_waveguide_manhattan``: WAVEGUIDE_MANHATTAN
        - ``_check_enclosed_area_min``: ENCLOSED_AREA_MIN
        - ``_check_crossing_angular``: CROSSING_ANGULAR

    Mixin 假设宿主类提供 ``self.bend_compensate`` 属性（bool）。
    """

    def _check_bend_radius_min(self, rule: DRCRule, circuit: dict,
                               placements: dict) -> list[DRCViolation]:
        """BEND_RADIUS_MIN: 波导弯曲半径 < threshold 视为违规。

        检查 device.params.bend_radius_um 字段，未声明则跳过（直段无弯曲）。
        非 fall-back: 仅检查显式声明的弯曲半径，不伪造默认值。

        来源（R02）:
            - SiEPIC EBeam PDK bend_radius=5μm
              https://github.com/SiEPIC/SiEPIC_EBeam_PDK
            - IMEC iSiPP50G 5μm（Ring Modulator）
              https://www.imec-int.com/sites/default/files/imported/Photonic%2520integrated%2520circuit_EN_v4_MPW_yi_0.pdf
            - LiDAR 2.0 II-B2 5-10μm https://arxiv.org/html/2505.17239v1
            - FluxCore 5-10μm
              https://www.fluxcoredynamics.com/docs/design-rules
            - Chrostowski & Hochberg 2015 §4.3（弯曲损耗）
              https://www.cambridge.org/core/books/silicon-photonics-design/
        """
        thr = rule.threshold
        violations: list[DRCViolation] = []
        for dev in circuit.get("devices", []):
            params = dev.get("params", {}) or {}
            radius = params.get("bend_radius_um")
            if radius is None:
                continue  # 直段/无弯曲声明，跳过（非 fall-back）
            radius = float(radius)
            if radius < thr:
                nm = dev.get("name", "")
                pl = placements.get(nm, {"x": 0.0, "y": 0.0, "w": 0.0, "h": 0.0})
                violations.append(DRCViolation(
                    rule_name=rule.name,
                    severity=rule.severity,
                    message=(f"{rule.name}: 器件 {nm} 弯曲半径 {radius:.4f}μm "
                             f"< 阈值 {thr:.4f}μm"),
                    device_name=nm,
                    location=aabb_center(aabb(pl)),
                ))
        return violations

    def _check_waveguide_width_match(self, rule: DRCRule, circuit: dict,
                                     placements: dict) -> list[DRCViolation]:
        """WAVEGUIDE_WIDTH_MATCH: 连接两端波导宽度必须匹配。

        宽度取自 device.params.width_um → device.width_um → placements.h
        （水平波导宽度 = h，与 SiEPIC strip_waveguide 一致）。
        tolerance=rule.threshold（默认 0.0μm，即完全匹配）。

        来源（R02）:
            - SiEPIC Verification "Mismatched pin widths"
              https://github-wiki-see.page/m/SiEPIC/SiEPIC-Tools/wiki/SiEPIC-Tools-Menu-descriptions
            - SiEPIC EBeam PDK https://github.com/SiEPIC/SiEPIC_EBeam_PDK
            - Chrostowski & Hochberg 2015 §4.3（模式失配损耗）
        """
        tol = rule.threshold
        device_map = build_device_map(circuit)
        violations: list[DRCViolation] = []
        for conn in circuit.get("connections", []):
            d1, p1, d2, p2 = conn
            w1 = device_waveguide_width(device_map.get(d1, {}), placements.get(d1, {}))
            w2 = device_waveguide_width(device_map.get(d2, {}), placements.get(d2, {}))
            if w1 is None or w2 is None:
                continue  # 任一端宽度未声明，跳过（非 fall-back）
            if abs(w1 - w2) > tol:
                port1 = find_port(device_map.get(d1, {}), p1)
                loc = port_abs(placements[d1], port1) if port1 else (0.0, 0.0)
                violations.append(DRCViolation(
                    rule_name=rule.name,
                    severity=rule.severity,
                    message=(f"{rule.name}: 连接 {d1}.{p1}(w={w1:.4f}μm)→"
                             f"{d2}.{p2}(w={w2:.4f}μm) 宽度不匹配 "
                             f"Δ={abs(w1 - w2):.4f}μm > 容差 {tol:.4f}μm"),
                    device_name=d1,
                    location=loc,
                ))
        return violations

    def _check_min_notch(self, rule: DRCRule, circuit: dict,
                         placements: dict) -> list[DRCViolation]:
        """MIN_NOTCH: 两器件平行边间隙 < threshold 视为窄颈违规。

        检查两无连接器件 AABB 平行边间隙 (0, threshold) 的窄颈。
        touching (gap=0) 由 NO_OVERLAP 处理；间距 ≥ threshold 合法。
        来源（R02）:
            - KLayout notch() https://www.klayout.org/doc-qt5/manual/drc_runsets.html
            - FluxCore MIN_NOTCH=100nm
              https://www.fluxcoredynamics.com/docs/design-rules
            - Berg "Computational Geometry" Springer 2014 AABB 距离
              https://doi.org/10.1007/978-3-540-77974-2
        """
        thr = rule.threshold
        names = list(placements.keys())
        boxes = {nm: aabb(placements[nm]) for nm in names}
        connected_pairs: set[tuple[str, str]] = set()
        for conn in circuit.get("connections", []):
            if len(conn) >= 4:
                d1, d2 = str(conn[0]), str(conn[2])
                connected_pairs.add((d1, d2))
                connected_pairs.add((d2, d1))
        violations: list[DRCViolation] = []
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                ni, nj = names[i], names[j]
                if (ni, nj) in connected_pairs:
                    continue  # 连接器件对由 MIN_SPACING 处理
                # aabb_distance 返回 0 表示重叠/touching，>0 表示间距
                gap = aabb_distance(boxes[ni], boxes[nj])
                if 0.0 < gap < thr:
                    loc = aabb_center(merge_aabb(boxes[ni], boxes[nj]))
                    violations.append(DRCViolation(
                        rule_name=rule.name,
                        severity=rule.severity,
                        message=(f"{rule.name}: 器件 {ni} 与 {nj} 平行边窄颈 "
                                 f"gap={gap:.4f}μm < 阈值 {thr:.4f}μm"),
                        device_name=ni,
                        location=loc,
                    ))
        return violations

    def _check_waveguide_manhattan(self, rule: DRCRule, circuit: dict,
                                   placements: dict) -> list[DRCViolation]:
        """WAVEGUIDE_MANHATTAN: 波导器件首末段必须 Manhattan（轴对齐）。

        检查波导器件（device_type 含 waveguide/wg/bend）的端口方向 ∈
        {north, south, east, west}。非法方向由 PORT_DIRECTION 主报，
        本规则聚焦波导器件的首末段 Manhattan 约束。

        来源（R02）:
            - SiEPIC Verification "首末段必须 Manhattan"
              https://github-wiki-see.page/m/SiEPIC/SiEPIC-Tools/wiki/SiEPIC-Tools-Menu-descriptions
            - SiEPIC EBeam PDK https://github.com/SiEPIC/SiEPIC_EBeam_PDK
            - Chrostowski & Hochberg 2015 §4.3（Manhattan 路由减小弯曲损耗）
        """
        violations: list[DRCViolation] = []
        for dev in circuit.get("devices", []):
            dt = str(dev.get("device_type", "")).lower()
            if not is_waveguide_device(dt):
                continue  # 非波导器件跳过（本规则仅约束波导首末段）
            nm = dev.get("name", "")
            for port in dev.get("ports", []):
                if len(port) < 4:
                    continue  # 缺方向字段由 PORT_DIRECTION 主报
                direction = normalize_direction(str(port[3]))
                if direction not in VALID_DIRECTIONS:
                    pl = placements.get(nm, {"x": 0.0, "y": 0.0, "w": 0.0, "h": 0.0})
                    violations.append(DRCViolation(
                        rule_name=rule.name,
                        severity=rule.severity,
                        message=(f"{rule.name}: 波导 {nm} 端口 {port[0]} "
                                 f"方向 {direction} 非 Manhattan"),
                        device_name=nm,
                        location=aabb_center(aabb(pl)),
                    ))
        return violations

    def _check_enclosed_area_min(self, rule: DRCRule, circuit: dict,
                                 placements: dict) -> list[DRCViolation]:
        """ENCLOSED_AREA_MIN: 连接图环形成的封闭区域面积 < threshold 违规。

        检测连接图中的最小环（4 器件矩形环），用 AABB 包围盒面积近似
        封闭区域面积。< 0.01μm² 视为孤立小洞。
        来源（R02）:
            - KLayout area_check（内孔检测）
              https://www.klayout.org/doc-qt5/manual/drc_runsets.html
            - Berg "Computational Geometry" Springer 2014（多边形面积）
              https://doi.org/10.1007/978-3-540-77974-2
            - SiEPIC EBeam PDK（避免孤立小洞）
              https://github.com/SiEPIC/SiEPIC_EBeam_PDK
        """
        thr = rule.threshold
        cycles = detect_connection_cycles(circuit)
        violations: list[DRCViolation] = []
        for cycle in cycles:
            boxes = [aabb(placements[name]) for name in cycle if name in placements]
            if len(boxes) < 3:
                continue
            merged = boxes[0]
            for b in boxes[1:]:
                merged = merge_aabb(merged, b)
            area = (merged[2] - merged[0]) * (merged[3] - merged[1])
            if area < thr:
                violations.append(DRCViolation(
                    rule_name=rule.name,
                    severity=rule.severity,
                    message=(f"{rule.name}: 环 {'→'.join(cycle)} 封闭面积 "
                             f"{area:.4f}μm² < 阈值 {thr:.4f}μm²"),
                    device_name=cycle[0],
                    location=aabb_center(merged),
                ))
        return violations

    def _check_crossing_angular(self, rule: DRCRule, circuit: dict,
                                placements: dict) -> list[DRCViolation]:
        """CROSSING_ANGULAR: 两波导 AABB 重叠且方向非垂直视为违规。

        检查两无连接波导器件 AABB 重叠且同为水平/同为垂直（非 90° 交叉）。
        水平 (w ≥ h) × 垂直 (h > w) = 90° 合法；其他组合违规。
        来源（R02）:
            - LiDAR 2.0 II-B3 arXiv:2505.17239v1（90° 交叉最优）
              https://arxiv.org/html/2505.17239v1
            - SiEPIC EBeam PDK（crossing 器件 90° 设计）
              https://github.com/SiEPIC/SiEPIC_EBeam_PDK
            - Berg "Computational Geometry" Springer 2014（AABB 相交）
              https://doi.org/10.1007/978-3-540-77974-2
        """
        names = list(placements.keys())
        boxes = {nm: aabb(placements[nm]) for nm in names}
        orients = {nm: aabb_orientation(placements[nm]) for nm in names}
        connected_pairs: set[tuple[str, str]] = set()
        for conn in circuit.get("connections", []):
            if len(conn) >= 4:
                d1, d2 = str(conn[0]), str(conn[2])
                connected_pairs.add((d1, d2))
                connected_pairs.add((d2, d1))
        violations: list[DRCViolation] = []
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                ni, nj = names[i], names[j]
                if (ni, nj) in connected_pairs:
                    continue  # 连接器件由 NO_OVERLAP 处理
                if not aabb_overlap(boxes[ni], boxes[nj]):
                    continue  # 不交叉
                oi, oj = orients[ni], orients[nj]
                if oi == "h" and oj == "v":
                    continue  # 水平×垂直 = 90° 合法
                if oi == "v" and oj == "h":
                    continue  # 垂直×水平 = 90° 合法
                loc = aabb_center(merge_aabb(boxes[ni], boxes[nj]))
                violations.append(DRCViolation(
                    rule_name=rule.name,
                    severity=rule.severity,
                    message=(f"{rule.name}: 波导 {ni}({oi}) 与 {nj}({oj}) "
                             f"交叉非 90°（{oi}×{oj}）"),
                    device_name=ni,
                    location=loc,
                ))
        return violations
