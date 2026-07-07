"""DRC P1 跨层规则 Mixin（polaris-drc 子模块，引擎层）。

R383（2026-07-07）新增 4 条 P1 跨层 DRC 规则，由 ``DRCEngine`` 继承:

- SEPARATION: 跨层最小间距（HEATER↔M1，gdsfactory 1.0μm）
- ENCLOSURE: 包围（VIAC 被 M1_HEATER 包围，SiEPIC 0.5μm）
- EXTENSION: 延伸（metal1 延伸超出 contact，0.2μm）
- EXCLUSION: 禁止层重叠（跨层零容忍，FluxCore）

纯 Python 标准库实现（R04: 不参与 GPU）。

## 数据模型约定

器件层信息从 ``device.params.layer`` 或 ``device.get("layer")`` 读取。
未声明 layer 的器件跳过跨层检查（合法物理含义：未声明层=无跨层约束，
非业务错误，R03 例外）。声明了 layer 的器件参与跨层规则检查。

## 来源（R02 学术诚信，≥5 个文献 URL）
- gdsfactory photonics-training DRC notebook（check_separation/enclosing）
  http://raw.githubusercontent.com/gdsfactory/gdsfactory-photonics-training/main/notebooks/11_drc.ipynb
- SiEPIC EBeam PDK DRC runset（VIAC_M1_ENCLOSURE=0.5μm）
  https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- KLayout DRC 文档（separation_check/enclosed_check/布尔交集）
  https://www.klayout.org/doc-qt5/manual/drc_runsets.html
- FluxCore DRC 文档（EXCLUSION 禁止层重叠）
  https://www.fluxcoredynamics.com/docs/design-rules
- Synopsys OptoDesigner DRC Module（EX1_layer_extension=0.2μm）
  https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/design-rule-checking-module.html
- Berg et al. 2014, "Computational Geometry", Springer（AABB 包含判定）
  https://doi.org/10.1007/978-3-540-77974-2
- Ericson, "Real-Time Collision Detection", MK 2005（AABB 距离 §5.1.3）
  https://realtimecollisiondetection.net/

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R05 Bug 必修。
"""

from __future__ import annotations

from polaris_drc.checks import aabb, aabb_distance, aabb_overlap, build_device_map
from polaris_drc.rules import DRCRule, DRCViolation

__all__ = ["CrossLayerRulesMixin"]


def _device_layer(dev: dict) -> str | None:
    """读取器件层名（device.params.layer 或 device.layer）。

    返回 None 表示器件未声明层（跳过跨层检查，合法非 fall-back）。
    """
    params = dev.get("params", {}) or {}
    layer = params.get("layer")
    if layer is None:
        layer = dev.get("layer")
    return str(layer) if layer is not None else None


def _aabb_contains(outer: tuple[float, float, float, float],
                   inner: tuple[float, float, float, float]) -> bool:
    """判断 outer AABB 是否完全包含 inner AABB（含边界）。

    来源: Berg "Computational Geometry" Springer §2.1 区间包含判定。
    """
    return (outer[0] <= inner[0] and outer[1] <= inner[1]
            and outer[2] >= inner[2] and outer[3] >= inner[3])


def _enclosure_margin(outer: tuple[float, float, float, float],
                      inner: tuple[float, float, float, float]) -> float:
    """计算包围量：inner 边缘到 outer 边缘的最小距离（inner 在 outer 内时为正）。

    几何含义: outer 超出 inner 的最小余量。ENCLOSURE/EXTENSION 共用此量。
    若 inner 不在 outer 内，返回 -1（不适用）。
    """
    if not _aabb_contains(outer, inner):
        return -1.0
    left = inner[0] - outer[0]
    bottom = inner[1] - outer[1]
    right = outer[2] - inner[2]
    top = outer[3] - inner[3]
    return min(left, bottom, right, top)


class CrossLayerRulesMixin:
    """P1 跨层 DRC 规则 Mixin（4 条，2026-07-07 R383 新增）。

    由 ``DRCEngine`` 继承，提供以下检查方法:
        - ``_check_separation``: SEPARATION 跨层最小间距
        - ``_check_enclosure``: ENCLOSURE 包围
        - ``_check_extension``: EXTENSION 延伸
        - ``_check_exclusion``: EXCLUSION 禁止层重叠

    Mixin 假设宿主类提供 ``self.bend_compensate`` 属性（bool，与 WaveguideRulesMixin 一致）。
    """

    def _check_separation(self, rule: DRCRule, circuit: dict,
                          placements: dict) -> list[DRCViolation]:
        """SEPARATION: 跨层最小间距 < threshold 视为违规。

        遍历所有声明了 layer 的器件对 (a, b)，若 a.layer != b.layer 且
        AABB 间距 < threshold（且不重叠），报违规。重叠由 EXCLUSION 处理。

        来源（R02）:
            - gdsfactory HEATER-M1=1.0μm
              http://raw.githubusercontent.com/gdsfactory/gdsfactory-photonics-training/main/notebooks/11_drc.ipynb
            - KLayout separation_check
              https://www.klayout.org/doc-qt5/manual/drc_runsets.html
        """
        thr = rule.threshold
        violations: list[DRCViolation] = []
        device_map = build_device_map(circuit)
        # 收集声明了 layer 的器件
        layered: list[tuple[str, str, tuple[float, float, float, float]]] = []
        for nm, dev in device_map.items():
            layer = _device_layer(dev)
            if layer is None:
                continue
            pl = placements.get(nm)
            if pl is None:
                continue
            layered.append((nm, layer, aabb(pl)))
        # 两两检查跨层间距
        n = len(layered)
        for i in range(n):
            nm_a, layer_a, box_a = layered[i]
            for j in range(i + 1, n):
                nm_b, layer_b, box_b = layered[j]
                if layer_a == layer_b:
                    continue  # 同层不检查 SEPARATION（由 MIN_SPACING 处理）
                if aabb_overlap(box_a, box_b):
                    continue  # 重叠由 EXCLUSION 处理
                dist = aabb_distance(box_a, box_b)
                if dist < thr:
                    cx = 0.5 * (box_a[0] + box_a[2] + box_b[0] + box_b[2]) * 0.5
                    cy = 0.5 * (box_a[1] + box_a[3] + box_b[1] + box_b[3]) * 0.5
                    violations.append(DRCViolation(
                        rule_name=rule.name, severity=rule.severity,
                        message=(f"{rule.name}: 跨层器件 {nm_a}({layer_a}) 与 "
                                 f"{nm_b}({layer_b}) 间距 {dist:.4f}μm < "
                                 f"{thr}μm"),
                        device_name=nm_a, location=(cx, cy),
                    ))
        return violations

    def _check_enclosure(self, rule: DRCRule, circuit: dict,
                         placements: dict) -> list[DRCViolation]:
        """ENCLOSURE: 内层器件被外层器件包围量 < threshold 视为违规。

        遍历所有声明了 layer 的器件对 (inner, outer)，若 inner AABB 完全在
        outer AABB 内且包围量 < threshold，报违规。inner.layer != outer.layer。

        来源（R02）:
            - SiEPIC EBeam PDK VIAC_M1_ENCLOSURE=0.5μm
              https://github.com/SiEPIC/SiEPIC_EBeam_PDK
            - KLayout enclosed_check
              https://www.klayout.org/doc-qt5/manual/drc_runsets.html
        """
        thr = rule.threshold
        violations: list[DRCViolation] = []
        device_map = build_device_map(circuit)
        layered: list[tuple[str, str, tuple[float, float, float, float]]] = []
        for nm, dev in device_map.items():
            layer = _device_layer(dev)
            if layer is None:
                continue
            pl = placements.get(nm)
            if pl is None:
                continue
            layered.append((nm, layer, aabb(pl)))
        n = len(layered)
        for i in range(n):
            nm_inner, layer_inner, box_inner = layered[i]
            for j in range(n):
                if i == j:
                    continue
                nm_outer, layer_outer, box_outer = layered[j]
                if layer_inner == layer_outer:
                    continue  # 同层不检查 ENCLOSURE
                margin = _enclosure_margin(box_outer, box_inner)
                if margin < 0:
                    continue  # inner 不在 outer 内，不适用
                if margin < thr:
                    cx = 0.5 * (box_inner[0] + box_inner[2])
                    cy = 0.5 * (box_inner[1] + box_inner[3])
                    violations.append(DRCViolation(
                        rule_name=rule.name, severity=rule.severity,
                        message=(f"{rule.name}: 内层 {nm_inner}({layer_inner}) "
                                 f"被 {nm_outer}({layer_outer}) 包围量 "
                                 f"{margin:.4f}μm < {thr}μm"),
                        device_name=nm_inner, location=(cx, cy),
                    ))
        return violations

    def _check_extension(self, rule: DRCRule, circuit: dict,
                         placements: dict) -> list[DRCViolation]:
        """EXTENSION: 外层器件延伸超出内层器件的量 < threshold 视为违规。

        几何上与 ENCLOSURE 相同（外层超出内层的最小余量），但规则语义为
        "外层必须延伸超出内层 ≥ threshold"。遍历所有声明了 layer 的器件对
        (inner, outer)，若 inner 在 outer 内且延伸量 < threshold，报违规。

        来源（R02）:
            - Synopsys OptoDesigner EX1_layer_extension=0.2μm
              https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/design-rule-checking-module.html
            - KLayout enclosing_check
              https://www.klayout.org/doc-qt5/manual/drc_runsets.html
        """
        thr = rule.threshold
        violations: list[DRCViolation] = []
        device_map = build_device_map(circuit)
        layered: list[tuple[str, str, tuple[float, float, float, float]]] = []
        for nm, dev in device_map.items():
            layer = _device_layer(dev)
            if layer is None:
                continue
            pl = placements.get(nm)
            if pl is None:
                continue
            layered.append((nm, layer, aabb(pl)))
        n = len(layered)
        for i in range(n):
            nm_inner, layer_inner, box_inner = layered[i]
            for j in range(n):
                if i == j:
                    continue
                nm_outer, layer_outer, box_outer = layered[j]
                if layer_inner == layer_outer:
                    continue  # 同层不检查 EXTENSION
                margin = _enclosure_margin(box_outer, box_inner)
                if margin < 0:
                    continue  # inner 不在 outer 内，不适用
                if margin < thr:
                    cx = 0.5 * (box_outer[0] + box_outer[2])
                    cy = 0.5 * (box_outer[1] + box_outer[3])
                    violations.append(DRCViolation(
                        rule_name=rule.name, severity=rule.severity,
                        message=(f"{rule.name}: 外层 {nm_outer}({layer_outer}) "
                                 f"延伸超出内层 {nm_inner}({layer_inner}) 的量 "
                                 f"{margin:.4f}μm < {thr}μm"),
                        device_name=nm_outer, location=(cx, cy),
                    ))
        return violations

    def _check_exclusion(self, rule: DRCRule, circuit: dict,
                         placements: dict) -> list[DRCViolation]:
        """EXCLUSION: 跨层器件 AABB 重叠视为违规（零容忍）。

        遍历所有声明了 layer 的器件对 (a, b)，若 a.layer != b.layer 且
        AABB 重叠（strict，touching 不算），报违规。

        来源（R02）:
            - FluxCore EXCLUSION 禁止层重叠
              https://www.fluxcoredynamics.com/docs/design-rules
            - KLayout Region 布尔交集
              https://www.klayout.org/doc-qt5/manual/drc_runsets.html
        """
        violations: list[DRCViolation] = []
        device_map = build_device_map(circuit)
        layered: list[tuple[str, str, tuple[float, float, float, float]]] = []
        for nm, dev in device_map.items():
            layer = _device_layer(dev)
            if layer is None:
                continue
            pl = placements.get(nm)
            if pl is None:
                continue
            layered.append((nm, layer, aabb(pl)))
        n = len(layered)
        for i in range(n):
            nm_a, layer_a, box_a = layered[i]
            for j in range(i + 1, n):
                nm_b, layer_b, box_b = layered[j]
                if layer_a == layer_b:
                    continue  # 同层不检查 EXCLUSION（由 NO_OVERLAP 处理）
                if aabb_overlap(box_a, box_b):
                    cx = 0.5 * (max(box_a[0], box_b[0]) + min(box_a[2], box_b[2]))
                    cy = 0.5 * (max(box_a[1], box_b[1]) + min(box_a[3], box_b[3]))
                    violations.append(DRCViolation(
                        rule_name=rule.name, severity=rule.severity,
                        message=(f"{rule.name}: 跨层器件 {nm_a}({layer_a}) 与 "
                                 f"{nm_b}({layer_b}) 重叠（禁止跨层重叠）"),
                        device_name=nm_a, location=(cx, cy),
                    ))
        return violations
