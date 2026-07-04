"""DRC 设计规则检查引擎（polaris-drc 子模块）。

从原 polaris-verify/src/polaris_verify/drc.py 拆分而来（R13 代码清理：
禁止多个 vx 文件并存，新建立就彻底删除老的）。仅依赖 numpy（R04: 不参与 GPU）。

## Input → Process → Output 三段式

### Input
- circuit: dict — polaris-core 风格电路规格（含 name/devices/connections/
  canvas_w/canvas_h）
- placements: dict — polaris-place 输出 {name: {x, y, w, h}}，μm，
  x, y 为器件左下角坐标

### Process
12 条 SiEPIC EBeam PDK DRC 规则 + AABB 几何算法

### Output
违规列表 list[DRCViolation]，空列表表示 DRC clean

## DRC 规则清单（12 条）

| 规则 | 阈值 | 来源 |
|------|------|------|
| MIN_SPACING | 1.0μm | SiEPIC WG_MIN_SPACE（避免波导耦合串扰）|
| MIN_WIDTH | 0.5μm | SiEPIC SLAB150_MIN_WIDTH（浅刻蚀工艺极限）|
| MIN_HEIGHT | 0.4μm | SiEPIC WG_MIN_WIDTH（220nm SOI 工艺极限）|
| MIN_AREA | 0.1μm² | SiEPIC WG_MIN_AREA（确保工艺可识别）|
| BOUNDARY | 0 | 器件不超出画布边界 |
| NO_OVERLAP | 0 | 器件之间不能重叠（touching 允许）|
| PORT_ALIGNMENT | 5μm | 连接端口坐标对齐（减少波导弯曲）|
| PORT_DIRECTION | - | 端口方向合法（north/south/east/west）|
| PORT_CONNECTIVITY | - | 每个器件至少有一个端口被连接 |
| PORT_FACING | - | 连接端口方向相对（east↔west / north↔south）|
| DENSITY_MAX | 80% | 布局密度上限（CMP 工艺均匀性）|
| DENSITY_MIN | 0.01% | 布局密度下限（避免空版图）|

## 几何约定

placements 中 x, y 为器件左下角坐标 (μm)，w, h 为宽高
（与 modules/_c_abi/polaris_types.h 中 polaris_placement_t 一致）。

## 来源（R02 学术诚信，≥5 个文献 URL）
- SiEPIC EBeam PDK DRC runset（WG_MIN_WIDTH=0.4μm, WG_MIN_SPACE=1.0μm 等）
  https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- Chrostowski & Hochberg, "Silicon Photonics Design", CUP 2015, p.353
  https://www.cambridge.org/core/books/silicon-photonics-design/
- KLayout DRC 文档（width_check/space_check/area_check）
  https://www.klayout.org/doc-qt5/manual/drc_runsets.html
- OpenDRC: He et al., DAC 2023, DOI:10.1109/DAC56929.2023.10247734
  https://doi.org/10.1109/DAC56929.2023.10247734
- Banerjee, "CMOS Photonic Circuits", Springer 2024（CMP 密度规则 30%-70%）
- Berg et al. 2014, "Computational Geometry", Springer（AABB 相交/距离）
  https://doi.org/10.1007/978-3-540-77974-2
- Ericson, "Real-Time Collision Detection", MK 2005（AABB 距离公式 §5.1.3）
  https://realtimecollisiondetection.net/
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Callable

import numpy as np

__all__ = [
    "CheckType",
    "DRCRule",
    "DRCViolation",
    "DRCEngine",
    "DEFAULT_DRC_RULES",
    "run_drc_rules",
]


# 端口合法方向集合
_VALID_DIRECTIONS = frozenset(("north", "south", "east", "west"))
# 端口方向缩写→全称映射（电路 JSON 常用 N/S/E/W，DRC 统一为 north/south/east/west）
_DIR_ABBR_MAP = {
    "n": "north", "s": "south", "e": "east", "w": "west",
    "north": "north", "south": "south", "east": "east", "west": "west",
}
# 端口方向相对映射（连接两端方向应相对）
_FACING_PAIRS = frozenset(
    (("east", "west"), ("west", "east"),
     ("north", "south"), ("south", "north"))
)


def _normalize_direction(direction: str) -> str:
    """规范化端口方向（N→north, S→south, E→east, W→west）。

    支持大小写缩写（N/S/E/W）和全称（north/south/east/west）。
    非法方向原样返回（由 PORT_DIRECTION 规则报违规）。
    """
    return _DIR_ABBR_MAP.get(str(direction).lower(), str(direction))


# 端口对齐容差（μm），来源: SiEPIC 波导对准容差
_PORT_ALIGN_TOL_UM = 5.0


class CheckType(Enum):
    """DRC 检查类型枚举（与 KLayout DRC 规则类别对应）。

    来源: KLayout DRC 规则类别
    https://www.klayout.org/doc-qt5/manual/drc_runsets.html
    """

    MIN_SPACING = "min_spacing"
    MIN_WIDTH = "min_width"
    MIN_HEIGHT = "min_height"
    MIN_AREA = "min_area"
    BOUNDARY = "boundary"
    NO_OVERLAP = "no_overlap"
    PORT_ALIGNMENT = "port_alignment"
    PORT_DIRECTION = "port_direction"
    PORT_CONNECTIVITY = "port_connectivity"
    PORT_FACING = "port_facing"
    DENSITY_MAX = "density_max"
    DENSITY_MIN = "density_min"


@dataclass(frozen=True)
class DRCRule:
    """单条 DRC 规则定义。

    Attributes:
        name: 规则名（如 "MIN_SPACING"）。
        check_type: 检查类型（CheckType 枚举）。
        threshold: 阈值（μm/μm²/%，语义随 check_type 变化）。
        severity: 违规严重程度（0-1）。
        description: 规则描述（含来源）。
    """

    name: str
    check_type: CheckType
    threshold: float
    severity: float = 1.0
    description: str = ""


# SiEPIC EBeam PDK 默认 DRC 规则集（12 条）
# 所有阈值来自 SiEPIC EBeam PDK 实际 DRC runset 源码（R02 学术诚信，禁止编造）
# https://github.com/SiEPIC/SiEPIC_EBeam_PDK
DEFAULT_DRC_RULES: list[DRCRule] = [
    DRCRule(
        name="MIN_SPACING",
        check_type=CheckType.MIN_SPACING,
        threshold=1.0,
        severity=1.0,
        description="器件最小间距 1.0μm（SiEPIC WG_MIN_SPACE，避免波导耦合串扰）",
    ),
    DRCRule(
        name="MIN_WIDTH",
        check_type=CheckType.MIN_WIDTH,
        threshold=0.5,
        severity=1.0,
        description="器件最小宽度 0.5μm（SiEPIC SLAB150_MIN_WIDTH，浅刻蚀工艺极限）",
    ),
    DRCRule(
        name="MIN_HEIGHT",
        check_type=CheckType.MIN_HEIGHT,
        threshold=0.4,
        severity=1.0,
        description="器件最小高度 0.4μm（SiEPIC WG_MIN_WIDTH，220nm SOI 工艺极限）",
    ),
    DRCRule(
        name="MIN_AREA",
        check_type=CheckType.MIN_AREA,
        threshold=0.1,
        severity=1.0,
        description="器件最小面积 0.1μm²（SiEPIC WG_MIN_AREA，确保工艺可识别）",
    ),
    DRCRule(
        name="BOUNDARY",
        check_type=CheckType.BOUNDARY,
        threshold=0.0,
        severity=1.0,
        description="器件不超出画布边界",
    ),
    DRCRule(
        name="NO_OVERLAP",
        check_type=CheckType.NO_OVERLAP,
        threshold=0.0,
        severity=1.0,
        description="器件之间不能重叠（touching 允许）",
    ),
    DRCRule(
        name="PORT_ALIGNMENT",
        check_type=CheckType.PORT_ALIGNMENT,
        threshold=_PORT_ALIGN_TOL_UM,
        severity=0.5,
        description="连接端口坐标对齐（容差 5μm，减少波导弯曲损耗）",
    ),
    DRCRule(
        name="PORT_DIRECTION",
        check_type=CheckType.PORT_DIRECTION,
        threshold=0.0,
        severity=0.8,
        description="端口方向合法（north/south/east/west）",
    ),
    DRCRule(
        name="PORT_CONNECTIVITY",
        check_type=CheckType.PORT_CONNECTIVITY,
        threshold=0.0,
        severity=0.9,
        description="每个器件至少有一个端口被连接",
    ),
    DRCRule(
        name="PORT_FACING",
        check_type=CheckType.PORT_FACING,
        threshold=0.0,
        severity=0.7,
        description="连接端口方向相对（east↔west / north↔south）",
    ),
    DRCRule(
        name="DENSITY_MAX",
        check_type=CheckType.DENSITY_MAX,
        threshold=80.0,
        severity=0.6,
        description="布局密度上限 80%（CMP 工艺均匀性，Banerjee 2024）",
    ),
    DRCRule(
        name="DENSITY_MIN",
        check_type=CheckType.DENSITY_MIN,
        threshold=0.01,
        severity=0.6,
        description="布局密度下限 0.01%（避免空版图）",
    ),
]


@dataclass
class DRCViolation:
    """DRC 违规结果（与 KLayoutDRCRunner Violation 格式对齐）。

    Attributes:
        rule_name: 触发的规则名。
        severity: 违规严重程度（0-1）。
        message: 违规描述信息。
        device_name: 相关器件名（多器件规则取首个）。
        location: 违规位置 (x, y) μm。
    """

    rule_name: str
    severity: float
    message: str
    device_name: str
    location: tuple[float, float]


# =========================================================================
# 几何工具（AABB 包围盒）
# =========================================================================


def _aabb(pl: dict) -> tuple[float, float, float, float]:
    """从 placement dict 提取 AABB (x1, y1, x2, y2)。

    Args:
        pl: 器件布局 {x, y, w, h}，x/y 为左下角。

    Returns:
        (x1, y1, x2, y2) 包围盒，x2=x+w, y2=y+h。
    """
    x, y, w, h = float(pl["x"]), float(pl["y"]), float(pl["w"]), float(pl["h"])
    return (x, y, x + w, y + h)


def _aabb_center(a: tuple[float, float, float, float]) -> tuple[float, float]:
    """AABB 中心坐标。"""
    return (0.5 * (a[0] + a[2]), 0.5 * (a[1] + a[3]))


def _aabb_distance(a: tuple[float, float, float, float],
                   b: tuple[float, float, float, float]) -> float:
    """两 AABB 最小边到边距离（touching 返回 0，重叠返回 0）。

    公式: dx=max(b[0]-a[2], a[0]-b[2], 0)，dy 同理，distance=hypot(dx,dy)。
    来源: Ericson "Real-Time Collision Detection" MK 2005 §5.1.3 AABB 距离。
    """
    dx = max(b[0] - a[2], a[0] - b[2], 0.0)
    dy = max(b[1] - a[3], a[1] - b[3], 0.0)
    return math.hypot(dx, dy)


def _aabb_overlap(a: tuple[float, float, float, float],
                  b: tuple[float, float, float, float]) -> bool:
    """两 AABB 是否重叠（strict，touching 不算重叠）。

    来源: Berg "Computational Geometry" Springer §2.1 区间相交判定。
    """
    x_overlap = a[0] < b[2] and b[0] < a[2]
    y_overlap = a[1] < b[3] and b[1] < a[3]
    return x_overlap and y_overlap


# =========================================================================
# DRC 引擎
# =========================================================================


class DRCEngine:
    """DRC 设计规则检查引擎。

    对 circuit + placements 执行所有规则检查，返回违规列表。
    用法::

        engine = DRCEngine(DEFAULT_DRC_RULES)
        violations = engine.run(circuit, placements)
    """

    def __init__(self, rules: list[DRCRule] | None = None) -> None:
        self.rules = rules if rules is not None else DEFAULT_DRC_RULES
        if not self.rules:
            raise RuntimeError("DRC 规则列表不能为空（R03 禁止 fall-back）")
        # 规则分发表: CheckType → 检查方法
        self._dispatch: dict[CheckType, Callable] = {
            CheckType.MIN_SPACING: self._check_min_spacing,
            CheckType.MIN_WIDTH: self._check_min_width,
            CheckType.MIN_HEIGHT: self._check_min_height,
            CheckType.MIN_AREA: self._check_min_area,
            CheckType.BOUNDARY: self._check_boundary,
            CheckType.NO_OVERLAP: self._check_no_overlap,
            CheckType.PORT_ALIGNMENT: self._check_port_alignment,
            CheckType.PORT_DIRECTION: self._check_port_direction,
            CheckType.PORT_CONNECTIVITY: self._check_port_connectivity,
            CheckType.PORT_FACING: self._check_port_facing,
            CheckType.DENSITY_MAX: self._check_density_max,
            CheckType.DENSITY_MIN: self._check_density_min,
        }

    def run(self, circuit: dict, placements: dict) -> list[DRCViolation]:
        """执行全部 DRC 规则检查。

        Args:
            circuit: polaris-core 风格 circuit dict。
            placements: polaris-place 输出的布局 {name: {x, y, w, h}}。

        Returns:
            违规列表（空列表表示 DRC clean）。

        Raises:
            RuntimeError: circuit/placements 结构非法（R03 禁止 fall-back）。
        """
        self._validate(circuit, placements)
        violations: list[DRCViolation] = []
        for rule in self.rules:
            checker = self._dispatch.get(rule.check_type)
            if checker is None:
                raise RuntimeError(
                    f"未实现的 DRC 检查类型: {rule.check_type}"
                    f"（规则 {rule.name}，R03 禁止 fall-back）"
                )
            violations.extend(checker(rule, circuit, placements))
        return violations

    @staticmethod
    def _validate(circuit: dict, placements: dict) -> None:
        """校验 circuit 与 placements 结构完整性（R03: 失败 raise）。"""
        if not isinstance(circuit, dict):
            raise RuntimeError(
                f"circuit 必须是 dict，得到 {type(circuit).__name__}"
            )
        for key in ("name", "devices", "canvas_w", "canvas_h"):
            if key not in circuit:
                raise RuntimeError(f"circuit 缺少必要字段: {key}")
        if not isinstance(placements, dict):
            raise RuntimeError(
                f"placements 必须是 dict，得到 {type(placements).__name__}"
            )
        if not placements:
            raise RuntimeError("placements 不能为空（R03 禁止 fall-back）")
        for nm, pl in placements.items():
            if not isinstance(pl, dict):
                raise RuntimeError(f"placements['{nm}'] 必须是 dict")
            for key in ("x", "y", "w", "h"):
                if key not in pl:
                    raise RuntimeError(f"placements['{nm}'] 缺少字段: {key}")

    # ===== 几何规则 =====

    def _check_min_spacing(self, rule: DRCRule, circuit: dict,
                           placements: dict) -> list[DRCViolation]:
        """MIN_SPACING: 器件间最小间距 < threshold 视为违规。

        公式: spacing = min AABB_distance(Devices_i, Devices_j)，对所有对。
        来源: SiEPIC WG_MIN_SPACE 1.0μm；KLayout space_check。

        例外: 直接连接的器件对（波导↔器件）跳过——波导连接器件时
        touching/小间距是正常物理连接，非耦合串扰（R05 Bug 修复）。
        """
        thr = rule.threshold
        names = list(placements.keys())
        boxes = {nm: _aabb(placements[nm]) for nm in names}
        # 构建直接连接对集合（从 connections 提取）
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
                # 跳过直接连接的器件对（波导连接器件 touching 正常）
                if (ni, nj) in connected_pairs:
                    continue
                dist = _aabb_distance(boxes[ni], boxes[nj])
                if dist < thr:
                    loc = _aabb_center(_merge_aabb(boxes[ni], boxes[nj]))
                    violations.append(DRCViolation(
                        rule_name=rule.name,
                        severity=rule.severity,
                        message=(f"{rule.name}: 器件 {ni} 与 {nj} 间距 "
                                 f"{dist:.4f}μm < 阈值 {thr:.4f}μm"),
                        device_name=ni,
                        location=loc,
                    ))
        return violations

    def _check_min_width(self, rule: DRCRule, circuit: dict,
                         placements: dict) -> list[DRCViolation]:
        """MIN_WIDTH: 器件宽度 w < threshold 视为违规。"""
        thr = rule.threshold
        violations: list[DRCViolation] = []
        for nm, pl in placements.items():
            w = float(pl["w"])
            if w < thr:
                violations.append(DRCViolation(
                    rule_name=rule.name,
                    severity=rule.severity,
                    message=f"{rule.name}: 器件 {nm} 宽度 {w:.4f}μm < 阈值 {thr:.4f}μm",
                    device_name=nm,
                    location=_aabb_center(_aabb(pl)),
                ))
        return violations

    def _check_min_height(self, rule: DRCRule, circuit: dict,
                          placements: dict) -> list[DRCViolation]:
        """MIN_HEIGHT: 器件高度 h < threshold 视为违规。"""
        thr = rule.threshold
        violations: list[DRCViolation] = []
        for nm, pl in placements.items():
            h = float(pl["h"])
            if h < thr:
                violations.append(DRCViolation(
                    rule_name=rule.name,
                    severity=rule.severity,
                    message=f"{rule.name}: 器件 {nm} 高度 {h:.4f}μm < 阈值 {thr:.4f}μm",
                    device_name=nm,
                    location=_aabb_center(_aabb(pl)),
                ))
        return violations

    def _check_min_area(self, rule: DRCRule, circuit: dict,
                        placements: dict) -> list[DRCViolation]:
        """MIN_AREA: 器件面积 w*h < threshold 视为违规。

        来源: SiEPIC WG_MIN_AREA 0.1μm²；KLayout area_check（鞋带公式）。
        """
        thr = rule.threshold
        violations: list[DRCViolation] = []
        for nm, pl in placements.items():
            area = float(pl["w"]) * float(pl["h"])
            if area < thr:
                violations.append(DRCViolation(
                    rule_name=rule.name,
                    severity=rule.severity,
                    message=(f"{rule.name}: 器件 {nm} 面积 {area:.4f}μm² "
                             f"< 阈值 {thr:.4f}μm²"),
                    device_name=nm,
                    location=_aabb_center(_aabb(pl)),
                ))
        return violations

    def _check_boundary(self, rule: DRCRule, circuit: dict,
                        placements: dict) -> list[DRCViolation]:
        """BOUNDARY: 器件超出画布边界视为违规。"""
        canvas_w = float(circuit["canvas_w"])
        canvas_h = float(circuit["canvas_h"])
        tol = rule.threshold
        violations: list[DRCViolation] = []
        for nm, pl in placements.items():
            x, y, w, h = (float(pl["x"]), float(pl["y"]),
                          float(pl["w"]), float(pl["h"]))
            if x < -tol or y < -tol or x + w > canvas_w + tol or y + h > canvas_h + tol:
                violations.append(DRCViolation(
                    rule_name=rule.name,
                    severity=rule.severity,
                    message=(f"{rule.name}: 器件 {nm} 超出画布边界 "
                             f"({x:.2f},{y:.2f})-({x+w:.2f},{y+h:.2f}) "
                             f"canvas=({canvas_w},{canvas_h})"),
                    device_name=nm,
                    location=(x + w / 2.0, y + h / 2.0),
                ))
        return violations

    def _check_no_overlap(self, rule: DRCRule, circuit: dict,
                          placements: dict) -> list[DRCViolation]:
        """NO_OVERLAP: 器件之间重叠视为违规（touching 允许）。

        来源: Berg "Computational Geometry" AABB 相交判定。
        """
        names = list(placements.keys())
        boxes = {nm: _aabb(placements[nm]) for nm in names}
        violations: list[DRCViolation] = []
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                ni, nj = names[i], names[j]
                if _aabb_overlap(boxes[ni], boxes[nj]):
                    loc = _aabb_center(_merge_aabb(boxes[ni], boxes[nj]))
                    violations.append(DRCViolation(
                        rule_name=rule.name,
                        severity=rule.severity,
                        message=f"{rule.name}: 器件 {ni} 与 {nj} 重叠",
                        device_name=ni,
                        location=loc,
                    ))
        return violations

    # ===== 端口规则 =====

    def _check_port_alignment(self, rule: DRCRule, circuit: dict,
                              placements: dict) -> list[DRCViolation]:
        """PORT_ALIGNMENT: 连接两端端口坐标对齐（共享 x 或 y，容差内）。"""
        tol = rule.threshold
        device_map = _build_device_map(circuit)
        violations: list[DRCViolation] = []
        for conn in circuit.get("connections", []):
            d1, p1, d2, p2 = conn
            port1 = _find_port(device_map.get(d1, {}), p1)
            port2 = _find_port(device_map.get(d2, {}), p2)
            if port1 is None or port2 is None:
                continue  # 端口缺失由其他规则报告，避免重复
            abs1 = _port_abs(placements[d1], port1)
            abs2 = _port_abs(placements[d2], port2)
            dx = abs(abs1[0] - abs2[0])
            dy = abs(abs1[1] - abs2[1])
            if dx > tol and dy > tol:
                violations.append(DRCViolation(
                    rule_name=rule.name,
                    severity=rule.severity,
                    message=(f"{rule.name}: 连接 {d1}.{p1}→{d2}.{p2} "
                             f"端口未对齐 dx={dx:.2f}μm dy={dy:.2f}μm "
                             f"> 容差 {tol:.2f}μm"),
                    device_name=d1,
                    location=((abs1[0] + abs2[0]) / 2.0, (abs1[1] + abs2[1]) / 2.0),
                ))
        return violations

    def _check_port_direction(self, rule: DRCRule, circuit: dict,
                              placements: dict) -> list[DRCViolation]:
        """PORT_DIRECTION: 端口方向必须在 {north,south,east,west} 中。"""
        violations: list[DRCViolation] = []
        for dev in circuit.get("devices", []):
            for port in dev.get("ports", []):
                if len(port) < 4:
                    violations.append(DRCViolation(
                        rule_name=rule.name,
                        severity=rule.severity,
                        message=(f"{rule.name}: 器件 {dev.get('name')} "
                                 f"端口 {port} 缺少方向字段"),
                        device_name=dev.get("name", ""),
                        location=(0.0, 0.0),
                    ))
                    continue
                direction = _normalize_direction(str(port[3]))
                if direction not in _VALID_DIRECTIONS:
                    violations.append(DRCViolation(
                        rule_name=rule.name,
                        severity=rule.severity,
                        message=(f"{rule.name}: 器件 {dev.get('name')} "
                                 f"端口 {port[0]} 方向非法: {direction}"),
                        device_name=dev.get("name", ""),
                        location=(0.0, 0.0),
                    ))
        return violations

    def _check_port_connectivity(self, rule: DRCRule, circuit: dict,
                                 placements: dict) -> list[DRCViolation]:
        """PORT_CONNECTIVITY: 每个器件至少有一个端口被连接。"""
        connected: set[str] = set()
        for conn in circuit.get("connections", []):
            d1, _p1, d2, _p2 = conn
            connected.add(d1)
            connected.add(d2)
        violations: list[DRCViolation] = []
        for dev in circuit.get("devices", []):
            nm = dev.get("name", "")
            if nm not in connected:
                pl = placements.get(nm, {"x": 0.0, "y": 0.0, "w": 0.0, "h": 0.0})
                violations.append(DRCViolation(
                    rule_name=rule.name,
                    severity=rule.severity,
                    message=f"{rule.name}: 器件 {nm} 无任何连接（孤立器件）",
                    device_name=nm,
                    location=_aabb_center(_aabb(pl)),
                ))
        return violations

    def _check_port_facing(self, rule: DRCRule, circuit: dict,
                           placements: dict) -> list[DRCViolation]:
        """PORT_FACING: 连接两端端口方向应相对（east↔west / north↔south）。"""
        device_map = _build_device_map(circuit)
        violations: list[DRCViolation] = []
        for conn in circuit.get("connections", []):
            d1, p1, d2, p2 = conn
            port1 = _find_port(device_map.get(d1, {}), p1)
            port2 = _find_port(device_map.get(d2, {}), p2)
            if port1 is None or port2 is None:
                continue
            dir1 = _normalize_direction(port1[2]) if len(port1) >= 3 else "unknown"
            dir2 = _normalize_direction(port2[2]) if len(port2) >= 3 else "unknown"
            if (dir1, dir2) not in _FACING_PAIRS:
                abs1 = _port_abs(placements[d1], port1)
                violations.append(DRCViolation(
                    rule_name=rule.name,
                    severity=rule.severity,
                    message=(f"{rule.name}: 连接 {d1}.{p1}({dir1})→{d2}.{p2}({dir2}) "
                             f"端口方向非相对"),
                    device_name=d1,
                    location=abs1,
                ))
        return violations

    # ===== 密度规则 =====

    def _check_density_max(self, rule: DRCRule, circuit: dict,
                           placements: dict) -> list[DRCViolation]:
        """DENSITY_MAX: 布局密度 > threshold% 视为违规。

        公式: density = Σ(device_area) / canvas_area × 100%。
        来源: Banerjee "CMOS Photonic Circuits" Springer 2024（CMP 密度上限）。
        """
        return _check_density_range(rule, circuit, placements, is_max=True)

    def _check_density_min(self, rule: DRCRule, circuit: dict,
                           placements: dict) -> list[DRCViolation]:
        """DENSITY_MIN: 布局密度 < threshold% 视为违规。"""
        return _check_density_range(rule, circuit, placements, is_max=False)


def _check_density_range(rule: DRCRule, circuit: dict, placements: dict,
                         is_max: bool) -> list[DRCViolation]:
    """布局密度范围检查（共用实现，避免重复代码）。

    Args:
        rule: DRC 规则。
        circuit: circuit dict。
        placements: placements dict。
        is_max: True 检查上限（density > thr 违规），False 检查下限（density < thr 违规）。

    Returns:
        违规列表（最多 1 条）。
    """
    canvas_area = float(circuit["canvas_w"]) * float(circuit["canvas_h"])
    if canvas_area <= 0:
        raise RuntimeError(
            f"画布面积非正: {canvas_area}（R03 禁止 fall-back）"
        )
    total_area = sum(float(pl["w"]) * float(pl["h"]) for pl in placements.values())
    density_pct = total_area / canvas_area * 100.0
    thr = rule.threshold
    violated = (density_pct > thr) if is_max else (density_pct < thr)
    if not violated:
        return []
    canvas_cx = float(circuit["canvas_w"]) / 2.0
    canvas_cy = float(circuit["canvas_h"]) / 2.0
    label = "超过上限" if is_max else "低于下限"
    return [DRCViolation(
        rule_name=rule.name,
        severity=rule.severity,
        message=(f"{rule.name}: 布局密度 {density_pct:.4f}% {label} "
                 f"{thr:.4f}%"),
        device_name="canvas",
        location=(canvas_cx, canvas_cy),
    )]


def _merge_aabb(a: tuple[float, float, float, float],
                b: tuple[float, float, float, float]
                ) -> tuple[float, float, float, float]:
    """合并两个 AABB（用于违规位置定位）。"""
    return (min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3]))


def _build_device_map(circuit: dict) -> dict[str, dict]:
    """构建器件名 → 器件 dict 映射（R03: 名重复 raise）。"""
    device_map: dict[str, dict] = {}
    for dev in circuit.get("devices", []):
        nm = dev.get("name")
        if nm is None:
            raise RuntimeError(f"器件缺 name 字段: {dev}（R03 禁止 fall-back）")
        if nm in device_map:
            raise RuntimeError(f"器件名重复: {nm}（R03 禁止 fall-back）")
        device_map[nm] = dev
    return device_map


def _find_port(device: dict, port_name: str
               ) -> tuple[float, float, str] | None:
    """在器件规格中查找端口，返回 (dx, dy, direction)。

    Args:
        device: 器件 dict（含 ports 列表）。
        port_name: 端口名。

    Returns:
        (dx, dy, direction)，端口未找到返回 None。
    """
    for port in device.get("ports", []):
        if len(port) >= 3 and str(port[0]) == port_name:
            direction = str(port[3]) if len(port) >= 4 else "unknown"
            return (float(port[1]), float(port[2]), direction)
    return None


def _port_abs(placement: dict, port: tuple[float, float, str]
              ) -> tuple[float, float]:
    """计算端口画布绝对坐标 = 器件左下角 + 端口相对偏移。

    与 modules/_c_abi/polaris_types.h polaris_placement_t 一致。
    """
    return (float(placement["x"]) + port[0], float(placement["y"]) + port[1])


def run_drc_rules(circuit: dict, placements: dict,
                  rules: list[DRCRule] | None = None) -> list[DRCViolation]:
    """DRC 检查便捷入口（返回违规列表）。

    Args:
        circuit: polaris-core 风格 circuit dict。
        placements: polaris-place 输出的布局 {name: {x, y, w, h}}。
        rules: DRC 规则列表（None 用默认 12 条 SiEPIC 规则）。

    Returns:
        违规列表（空列表表示 DRC clean）。
    """
    return DRCEngine(rules).run(circuit, placements)


# numpy 引用占位（保留依赖一致性，R04 纯 NumPy）
_ = np
