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

纯 Python 标准库实现（R04: 不参与 GPU）。

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
  https://www.cambridge.org/core/search?searchField=isbn&searchTerms=1107007731
- Berg et al. 2014, "Computational Geometry", Springer（AABB 相交/距离）
  https://doi.org/10.1007/978-3-540-77974-2
"""

from __future__ import annotations

import math

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
    VALID_DIRECTIONS,
    DRCRule,
    DRCViolation,
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
              https://www.cambridge.org/core/search?searchField=isbn&searchTerms=1107007731
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

        宽度取自 device_waveguide_width (params.width_um → params.wg_width
        → params.waveguide_width → 波导类器件 placement.h)。
        tolerance=rule.threshold（默认 0.0μm，即完全匹配）。

        浮点噪声处理 (R05 Bug 修复):
            GDS 几何提取产生的浮点误差 (如 14.999999999999998 vs 15.0)
            会在 threshold=0.0 时触发假阳性。使用 math.isclose(rel_tol=1e-9,
            abs_tol=1e-9) 作为一级匹配判定，仅当 not isclose 且 delta > tol
            时才计为违规。1e-9μm = 1fm 远低于任何物理意义 (典型波导 500nm)。

        来源（R02）:
            - SiEPIC Verification "Mismatched pin widths"
              https://github-wiki-see.page/m/SiEPIC/SiEPIC-Tools/wiki/SiEPIC-Tools-Menu-descriptions
            - SiEPIC EBeam PDK https://github.com/SiEPIC/SiEPIC_EBeam_PDK
            - Chrostowski & Hochberg 2015 §4.3（模式失配损耗）
              https://www.cambridge.org/core/search?searchField=isbn&searchTerms=1107007731
            - IEEE 754 浮点比较最佳实践 (math.isclose, PEP 485)
              https://peps.python.org/pep-0485/
            - gdsfactory wg_width 参数约定
              https://gdsfactory.github.io/gdsfactory/
        """
        import math

        tol = rule.threshold
        device_map = build_device_map(circuit)
        violations: list[DRCViolation] = []
        for conn in circuit.get("connections", []):
            d1, p1, d2, p2 = conn
            w1 = device_waveguide_width(device_map.get(d1, {}), placements.get(d1, {}))
            w2 = device_waveguide_width(device_map.get(d2, {}), placements.get(d2, {}))
            if w1 is None or w2 is None:
                continue  # 任一端宽度未声明，跳过（非 fall-back）
            delta = abs(w1 - w2)
            # 一级判定: math.isclose 吸收浮点噪声 (1e-9μm=1fm，无物理意义)
            # 二级判定: 显式阈值 (rule.threshold)
            if (not math.isclose(w1, w2, rel_tol=1e-9, abs_tol=1e-9)
                    and delta > tol):
                port1 = find_port(device_map.get(d1, {}), p1)
                loc = port_abs(placements[d1], port1) if port1 else (0.0, 0.0)
                violations.append(DRCViolation(
                    rule_name=rule.name,
                    severity=rule.severity,
                    message=(f"{rule.name}: 连接 {d1}.{p1}(w={w1:.4f}μm)→"
                             f"{d2}.{p2}(w={w2:.4f}μm) 宽度不匹配 "
                             f"Δ={delta:.4f}μm > 容差 {tol:.4f}μm"),
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

    # ===== P1 波导级规则（3 条，2026-07-07 R383 新增，覆盖率 88%→100%） =====

    def _check_angle_limit(self, rule: DRCRule, circuit: dict,
                           placements: dict) -> list[DRCViolation]:
        """ANGLE_LIMIT: 路径段内角 ∈ [threshold, limit_max] 否则违规。

        从 device.params.path_angle 读取路径段内角（度）。未声明 path_angle
        的器件跳过（合法：非波导路径器件无角度约束，非 fall-back）。

        来源（R02）:
            - FluxCore ANGLE_LIMIT [45°, 135°]
              https://www.fluxcoredynamics.com/docs/design-rules
            - KLayout with_angle(min, max)
              https://www.klayout.org/doc-qt5/manual/drc.html
        """
        thr_min = rule.threshold
        thr_max = rule.limit_max if rule.limit_max is not None else 135.0
        violations: list[DRCViolation] = []
        for dev in circuit.get("devices", []):
            params = dev.get("params", {}) or {}
            angle = params.get("path_angle")
            if angle is None:
                continue  # 未声明角度，跳过（非 fall-back）
            angle = float(angle)
            nm = dev.get("name", "")
            if angle < thr_min or angle > thr_max:
                pl = placements.get(nm, {"x": 0.0, "y": 0.0})
                loc = (float(pl.get("x", 0.0)), float(pl.get("y", 0.0)))
                violations.append(DRCViolation(
                    rule_name=rule.name, severity=rule.severity,
                    message=(f"{rule.name}: 器件 {nm} 路径段内角 {angle:.1f}° "
                             f"超出范围 [{thr_min:.0f}°, {thr_max:.0f}°]"),
                    device_name=nm, location=loc,
                ))
        return violations

    def _check_waveguide_taper_angle(self, rule: DRCRule, circuit: dict,
                                     placements: dict
                                     ) -> list[DRCViolation]:
        """WAVEGUIDE_TAPER_ANGLE: 锥形波导半顶角 ≤ threshold 否则违规。

        从 device.params 读取 width_in_um / width_out_um / length_um，
        计算半顶角 θ=atan(Δwidth/2/L)（度）。未声明锥形参数的器件跳过。
        length ≤ 0 raise RuntimeError（R03 禁止 fall-back）。

        来源（R02）:
            - Milton & Burns 1987 JLT 绝热锥形条件
              https://opg.optica.org/jlt/abstract.cfm?uri=jl-5-8-1079
            - drc_curvilinear_18rules CV3_taper_angle=10°
            - R02 注: 10° 是工程保守上限，非严格绝热条件
              （严格条件 θ << λ/(2π W_beat)）
        """
        thr = rule.threshold
        violations: list[DRCViolation] = []
        for dev in circuit.get("devices", []):
            params = dev.get("params", {}) or {}
            w_in = params.get("width_in_um")
            w_out = params.get("width_out_um")
            length = params.get("length_um")
            if w_in is None or w_out is None or length is None:
                continue  # 未声明锥形参数，跳过（非 fall-back）
            w_in = float(w_in)
            w_out = float(w_out)
            length = float(length)
            if length <= 0:
                raise RuntimeError(
                    f"{rule.name}: 器件 {dev.get('name', '')} 锥形长度 "
                    f"{length} ≤ 0 非法（R03 禁止 fall-back）"
                )
            nm = dev.get("name", "")
            half_angle = math.degrees(
                math.atan(abs(w_out - w_in) / 2.0 / length)
            )
            if half_angle > thr:
                pl = placements.get(nm, {"x": 0.0, "y": 0.0})
                loc = (float(pl.get("x", 0.0)), float(pl.get("y", 0.0)))
                violations.append(DRCViolation(
                    rule_name=rule.name, severity=rule.severity,
                    message=(f"{rule.name}: 器件 {nm} 锥形半顶角 "
                             f"{half_angle:.2f}° > {thr}° (w_in={w_in}μm, "
                             f"w_out={w_out}μm, L={length}μm)"),
                    device_name=nm, location=loc,
                ))
        return violations

    def _check_singlemode_width(self, rule: DRCRule, circuit: dict,
                                placements: dict) -> list[DRCViolation]:
        """SINGLEMODE_WIDTH: 波导宽度 ≤ threshold 否则违规。

        从 device.params.width_um 读取波导宽度。未声明 width_um 的器件跳过
        （合法：非波导器件无宽度约束，非 fall-back）。

        来源（R02）:
            - Snyder & Love 1983 §13.5 V 参数单模条件 V<2.405
              https://link.springer.com/book/10.1007/978-94-009-6875-2
            - Soref 1991 IEEE JQE SOI 单模条形波导
              https://doi.org/10.1109/3.84143
            - R05 修正: 原 MW1=1.05μm 无文献支撑，修正为 1.0μm
              （V 参数严格推导值 W_max=2×2.405×1.55/(2π×√(3.476²-1.444²))≈1.00μm）
        """
        thr = rule.threshold
        violations: list[DRCViolation] = []
        for dev in circuit.get("devices", []):
            params = dev.get("params", {}) or {}
            width = params.get("width_um")
            if width is None:
                # R390 修复：原注释声明兼容 width_um/wg_width/waveguide_width 三个字段名，
                # 但代码漏掉 waveguide_width（与 checks.py:320-325 不一致）
                width = params.get("wg_width")
            if width is None:
                width = params.get("waveguide_width")
            if width is None:
                continue  # 未声明波导宽度，跳过（非 fall-back）
            width = float(width)
            nm = dev.get("name", "")
            if width > thr:
                pl = placements.get(nm, {"x": 0.0, "y": 0.0})
                loc = (float(pl.get("x", 0.0)), float(pl.get("y", 0.0)))
                violations.append(DRCViolation(
                    rule_name=rule.name, severity=rule.severity,
                    message=(f"{rule.name}: 器件 {nm} 波导宽度 {width:.4f}μm > "
                             f"单模上限 {thr}μm (V 参数 V<2.405, Snyder & "
                             f"Love 1983)"),
                    device_name=nm, location=loc,
                ))
        return violations
