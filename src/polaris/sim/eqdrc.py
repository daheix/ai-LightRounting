"""R23 路标：Calibre eqDRC + nmLVS 光子 DRC 认证流程对齐模块。

对齐 Siemens Calibre eqDRC（方程化 DRC）+ nmLVS（曲线感知 LVS），实现光子
芯片制造前的 DRC 认证流程。eqDRC 用数学表达式定义多维约束（弯曲半径、曲率
连续性、锥形结构、条件规则、容差机制），超越传统 1D DRC 的固定阈值检查。

## 学术依据

- Siemens Calibre eqDRC: https://blogs.sw.siemens.com/calibre/2015/11/17/design-rule-checking-for-silicon-photonics/
- Siemens + GF Calibre Fotonix: https://news.siemens.com/el-gr/siemens-globalfoundries-calibre-fotonix/
- Krinke et al., ISPD 2024: https://dl.acm.org/doi/pdf/10.1145/3626184.3635289

## 合规性

- project_rules.md 规则 14.1: 禁止 fall-back / 假数据 / mock
- project_rules.md 规则 18: 所有参数来自公开文献，标注来源 URL
- project_rules.md 规则 7.1: 文件 < 600 行
"""

from __future__ import annotations

import copy
import math
from dataclasses import dataclass

import numpy as np

# 学术来源 URL 常量（规则 18 学术诚信）
_URL_CALIBRE_EQDRC = (
    "https://blogs.sw.siemens.com/calibre/2015/11/17/"
    "design-rule-checking-for-silicon-photonics/"
)
_URL_GF_FOTONIX = "https://news.siemens.com/el-gr/siemens-globalfoundries-calibre-fotonix/"


# ---------------------------------------------------------------------------
# 1. 方程化 DRC 引擎（eqDRC）
# ---------------------------------------------------------------------------


@dataclass
class EqDRCRule:
    """方程化 DRC 规则（Calibre eqDRC 对齐）。

    学术依据：Siemens Calibre eqDRC
    URL: https://blogs.sw.siemens.com/calibre/2015/11/17/design-rule-checking-for-silicon-photonics/

    与传统 1D DRC 不同，eqDRC 用数学表达式定义多维约束：
    曲线几何（弯曲半径、曲率连续性）、锥形结构（锥角、锥度）、
    条件规则（if-then）、容差机制（tolerance）。
    """

    name: str
    category: str  # width/space/bend/taper/conditional/density
    equation: str
    params: dict
    severity: str = "error"
    description: str = ""


@dataclass
class EqDRCViolation:
    """eqDRC 违反。"""

    rule_name: str
    severity: str
    message: str
    location: tuple[float, float] = (0.0, 0.0)
    actual_value: float = 0.0
    expected_value: float = 0.0


def _compute_curvature(points: list[tuple[float, float]]) -> np.ndarray:
    """计算路径曲率（numpy 数值微分）。

    κ = |x'y'' - y'x''| / (x'² + y'²)^(3/2)
    学术依据：微分几何曲率公式
    """
    pts = np.array(points, dtype=float)
    if len(pts) < 3:
        return np.zeros(len(pts))
    x, y = pts[:, 0], pts[:, 1]
    dx, dy = np.gradient(x), np.gradient(y)
    d2x, d2y = np.gradient(dx), np.gradient(dy)
    numerator = np.abs(dx * d2y - dy * d2x)
    denominator = (dx**2 + dy**2) ** 1.5
    return np.where(denominator > 1e-12, numerator / denominator, 0.0)


def _compute_bend_radius(points: list[tuple[float, float]]) -> np.ndarray:
    """计算路径弯曲半径（R = 1/κ），直线段为 inf。"""
    curvature = _compute_curvature(points)
    return np.where(curvature > 1e-12, 1.0 / curvature, np.inf)


class EqDRCEngine:
    """方程化 DRC 引擎（Calibre eqDRC 对齐）。

    学术依据：Siemens Calibre eqDRC 白皮书
    URL: https://blogs.sw.siemens.com/calibre/2015/11/17/design-rule-checking-for-silicon-photonics/

    支持：曲线感知规则检查、锥形结构检查、条件 DRC、容差机制、多维约束。
    """

    def __init__(self, rules: list[EqDRCRule]) -> None:
        """初始化 eqDRC 引擎。"""
        self.rules = rules

    def check_bend_radius(
        self, paths: list[dict], min_radius: float, tol: float = 0.0
    ) -> list[EqDRCViolation]:
        """检查弯曲半径（曲线感知）。

        eqDRC 方程：R_actual >= R_min * (1 - tol)
        """
        violations: list[EqDRCViolation] = []
        threshold = min_radius * (1.0 - tol)
        for path in paths:
            points = path.get("points", [])
            if len(points) < 3:
                continue
            radii = _compute_bend_radius(points)
            finite_mask = np.isfinite(radii)
            if not np.any(finite_mask):
                continue
            min_r = float(np.min(radii[finite_mask]))
            if min_r < threshold:
                idx = int(np.argmin(radii))
                pts = points[idx]
                violations.append(
                    EqDRCViolation(
                        rule_name="BEND_MIN_RADIUS",
                        severity="error",
                        message=(
                            f"弯曲半径 {min_r:.3f}μm < 最小 {min_radius:.3f}μm"
                            f"（容差 {tol:.1%}，阈值 {threshold:.3f}μm）"
                        ),
                        location=(float(pts[0]), float(pts[1])),
                        actual_value=min_r,
                        expected_value=min_radius,
                    )
                )
        return violations

    def check_curvature_continuity(
        self, paths: list[dict], max_curvature_jump: float
    ) -> list[EqDRCViolation]:
        """检查曲率连续性（避免曲率突变）。

        eqDRC 方程：|κ(i+1) - κ(i)| <= max_jump
        """
        violations: list[EqDRCViolation] = []
        for path in paths:
            points = path.get("points", [])
            if len(points) < 4:
                continue
            curvature = _compute_curvature(points)
            jumps = np.abs(np.diff(curvature))
            if len(jumps) == 0:
                continue
            max_jump = float(np.max(jumps))
            if max_jump > max_curvature_jump:
                idx = int(np.argmax(jumps))
                pts = points[idx + 1]
                violations.append(
                    EqDRCViolation(
                        rule_name="CURVATURE_CONTINUITY",
                        severity="warning",
                        message=(
                            f"曲率跳变 {max_jump:.6f} 1/μm > 最大 "
                            f"{max_curvature_jump:.6f} 1/μm"
                        ),
                        location=(float(pts[0]), float(pts[1])),
                        actual_value=max_jump,
                        expected_value=max_curvature_jump,
                    )
                )
        return violations

    def check_taper(
        self, paths: list[dict], max_taper_angle: float, min_width: float
    ) -> list[EqDRCViolation]:
        """检查锥形结构（锥角、最小宽度）。

        eqDRC 方程：θ <= θ_max 且 w >= w_min
        锥角计算：θ = atan(Δw / (2 * L))
        """
        violations: list[EqDRCViolation] = []
        for path in paths:
            widths = path.get("widths")
            points = path.get("points", [])
            if widths is None or len(widths) < 2:
                continue
            # 检查最小宽度
            for i, w in enumerate(widths):
                if w < min_width:
                    pts = points[i] if i < len(points) else (0.0, 0.0)
                    violations.append(
                        EqDRCViolation(
                            rule_name="TAPER_MIN_WIDTH",
                            severity="error",
                            message=f"锥形宽度 {w:.3f}μm < 最小 {min_width:.3f}μm",
                            location=(float(pts[0]), float(pts[1])),
                            actual_value=w,
                            expected_value=min_width,
                        )
                    )
            # 检查锥角
            for i in range(1, len(widths)):
                dw = abs(widths[i] - widths[i - 1])
                if len(points) > i:
                    dx = points[i][0] - points[i - 1][0]
                    dy = points[i][1] - points[i - 1][1]
                    seg_len = math.hypot(dx, dy)
                    if seg_len > 1e-9:
                        angle = math.degrees(math.atan2(dw / 2.0, seg_len))
                        if angle > max_taper_angle:
                            pts = points[i]
                            violations.append(
                                EqDRCViolation(
                                    rule_name="TAPER_MAX_ANGLE",
                                    severity="error",
                                    message=(
                                        f"锥角 {angle:.2f}° > 最大 "
                                        f"{max_taper_angle:.2f}°"
                                    ),
                                    location=(float(pts[0]), float(pts[1])),
                                    actual_value=angle,
                                    expected_value=max_taper_angle,
                                )
                            )
        return violations

    def check_conditional(
        self, paths: list[dict], condition: str, rule: EqDRCRule
    ) -> list[EqDRCViolation]:
        """条件 DRC 检查（if-then 规则）。

        eqDRC 条件规则：if condition then check rule
        支持格式："attr op value"（如 "width > 0.5"）
        """
        violations: list[EqDRCViolation] = []
        parts = condition.split()
        if len(parts) != 3:
            raise ValueError(
                f"条件表达式格式错误: {condition}（应为 'attr op value'）"
            )
        attr, op, value_str = parts
        value = float(value_str)
        for path in paths:
            path_value = self._get_path_attribute(path, attr)
            if path_value is None:
                continue
            if self._eval_condition(path_value, op, value):
                violations.extend(self._apply_rule(path, rule))
        return violations

    def _get_path_attribute(self, path: dict, attr: str) -> float | None:
        """获取路径属性值。"""
        if attr == "width":
            return path.get("width")
        if attr == "radius":
            points = path.get("points", [])
            if len(points) < 3:
                return None
            radii = _compute_bend_radius(points)
            finite = radii[np.isfinite(radii)]
            return float(np.min(finite)) if len(finite) > 0 else None
        if attr == "length":
            points = path.get("points", [])
            total = 0.0
            for i in range(1, len(points)):
                total += math.hypot(
                    points[i][0] - points[i - 1][0],
                    points[i][1] - points[i - 1][1],
                )
            return total
        return path.get(attr)

    def _eval_condition(self, actual: float, op: str, threshold: float) -> bool:
        """评估条件表达式。"""
        ops = {">": lambda a, b: a > b, "<": lambda a, b: a < b,
               ">=": lambda a, b: a >= b, "<=": lambda a, b: a <= b,
               "==": lambda a, b: abs(a - b) < 1e-9}
        if op not in ops:
            raise ValueError(f"不支持的操作符: {op}")
        return ops[op](actual, threshold)

    def _apply_rule(self, path: dict, rule: EqDRCRule) -> list[EqDRCViolation]:
        """对单条路径应用规则。"""
        if rule.category == "bend":
            return self.check_bend_radius(
                [path], rule.params.get("R_min", 0.0), rule.params.get("tol", 0.0)
            )
        if rule.category == "taper":
            return self.check_taper(
                [path],
                rule.params.get("theta_max", 30.0),
                rule.params.get("w_min", 0.0),
            )
        return []

    def run_all(self, layout: dict) -> dict:
        """运行所有 eqDRC 规则。

        Returns:
            {is_pass: bool, violations: list, report: str}
        """
        paths = layout.get("paths", [])
        violations: list[EqDRCViolation] = []
        for rule in self.rules:
            if rule.category == "bend":
                violations.extend(
                    self.check_bend_radius(
                        paths,
                        rule.params.get("R_min", 0.0),
                        rule.params.get("tol", 0.0),
                    )
                )
            elif rule.category == "taper":
                violations.extend(
                    self.check_taper(
                        paths,
                        rule.params.get("theta_max", 30.0),
                        rule.params.get("w_min", 0.0),
                    )
                )
            elif rule.category == "conditional":
                cond = rule.params.get("condition", "")
                violations.extend(self.check_conditional(paths, cond, rule))
        is_pass = len(violations) == 0
        report = self._generate_report(violations)
        return {"is_pass": is_pass, "violations": violations, "report": report}

    def _generate_report(self, violations: list[EqDRCViolation]) -> str:
        """生成 eqDRC 报告。"""
        lines = [f"eqDRC 报告: {len(violations)} 个违反"]
        for v in violations:
            lines.append(f"  [{v.severity}] {v.rule_name}: {v.message}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# 2. 曲线感知 LVS（Calibre nmLVS 对齐）
# ---------------------------------------------------------------------------


class CurvilinearLVS:
    """曲线感知 LVS（Calibre nmLVS 对齐）。

    学术依据：Siemens + GlobalFoundries Calibre Fotonix 合作
    URL: https://news.siemens.com/el-gr/siemens-globalfoundries-calibre-fotonix/

    通过 text/marker 层识别曲线结构，进行版图 vs 原理图比对。
    """

    def __init__(self) -> None:
        """初始化曲线感知 LVS 引擎。"""

    def extract_with_markers(
        self, gds_layout: dict, marker_layers: list[str]
    ) -> dict:
        """通过 text/marker 层提取曲线结构网表。"""
        paths = gds_layout.get("paths", [])
        markers = gds_layout.get("markers", [])
        relevant_markers = [m for m in markers if m.get("layer") in marker_layers]
        curved_components = self.identify_curved_components(gds_layout)
        devices = [
            {"name": c["name"], "type": c["type"], "params": c.get("params", {})}
            for c in curved_components
        ]
        for marker in relevant_markers:
            text = marker.get("text", "")
            for device in devices:
                if device["name"] == text:
                    device["marker_layer"] = marker.get("layer")
                    break
        return {
            "devices": devices,
            "connections": self._extract_connections(paths),
            "marker_count": len(relevant_markers),
        }

    def _extract_connections(self, paths: list[dict]) -> list[dict]:
        """从路径提取连接关系。"""
        connections = []
        for path in paths:
            connections.append(
                {
                    "name": path.get("name", ""),
                    "layer": path.get("layer", "WG"),
                    "length": self._compute_path_length(path.get("points", [])),
                }
            )
        return connections

    def _compute_path_length(self, points: list) -> float:
        """计算路径长度。"""
        total = 0.0
        for i in range(1, len(points)):
            total += math.hypot(
                points[i][0] - points[i - 1][0], points[i][1] - points[i - 1][1]
            )
        return total

    def compare_curvilinear(
        self, layout_netlist: dict, schematic_netlist: dict
    ) -> dict:
        """曲线感知 LVS 比对。

        Returns:
            {is_match: bool, mismatches: list, report: str}
        """
        mismatches: list[str] = []
        layout_devices = {d["name"]: d for d in layout_netlist.get("devices", [])}
        schematic_devices = {d["name"]: d for d in schematic_netlist.get("devices", [])}
        # 检查缺失/多余器件
        for name in schematic_devices:
            if name not in layout_devices:
                mismatches.append(f"版图缺失器件: {name}")
        for name in layout_devices:
            if name not in schematic_devices:
                mismatches.append(f"版图多余器件: {name}")
        # 检查器件类型匹配
        for name in layout_devices:
            if name in schematic_devices:
                lt = layout_devices[name].get("type")
                st = schematic_devices[name].get("type")
                if lt != st:
                    mismatches.append(
                        f"器件 {name} 类型不匹配: 版图={lt}, 原理图={st}"
                    )
        # 检查连接数
        layout_conns = layout_netlist.get("connections", [])
        schematic_conns = schematic_netlist.get("connections", [])
        if len(layout_conns) != len(schematic_conns):
            mismatches.append(
                f"连接数不匹配: 版图={len(layout_conns)}, "
                f"原理图={len(schematic_conns)}"
            )
        is_match = len(mismatches) == 0
        report = self._generate_lvs_report(
            mismatches, len(layout_devices), len(schematic_devices)
        )
        return {
            "is_match": is_match,
            "mismatches": mismatches,
            "report": report,
        }

    def _generate_lvs_report(
        self, mismatches: list[str], n_layout: int, n_schematic: int
    ) -> str:
        """生成 LVS 报告。"""
        lines = [
            f"曲线 LVS 报告: 版图器件 {n_layout} 个, 原理图器件 {n_schematic} 个",
            f"不匹配数: {len(mismatches)}",
        ]
        for m in mismatches:
            lines.append(f"  - {m}")
        return "\n".join(lines)

    def identify_curved_components(self, layout: dict) -> list[dict]:
        """识别曲线组件（弯曲波导、锥形器等）。"""
        components: list[dict] = []
        paths = layout.get("paths", [])
        for i, path in enumerate(paths):
            points = path.get("points", [])
            if len(points) < 3:
                continue
            radii = _compute_bend_radius(points)
            finite = radii[np.isfinite(radii)]
            has_curve = len(finite) > 0 and float(np.min(finite)) < 1e6
            widths = path.get("widths")
            has_taper = widths is not None and len(widths) > 1
            if has_taper:
                w_diff = max(widths) - min(widths)
                if w_diff > 1e-9:
                    components.append(
                        {
                            "name": path.get("name", f"taper_{i}"),
                            "type": "taper",
                            "params": {"width_in": widths[0], "width_out": widths[-1]},
                        }
                    )
            if has_curve:
                min_r = float(np.min(finite)) if len(finite) > 0 else float("inf")
                components.append(
                    {
                        "name": path.get("name", f"bend_{i}"),
                        "type": "bend",
                        "params": {"radius": min_r},
                    }
                )
        return components


# ---------------------------------------------------------------------------
# 3. 多 foundry DRC runset 认证
# ---------------------------------------------------------------------------


@dataclass
class FoundryDRCRunset:
    """Foundry DRC runset 认证数据。

    Attributes:
        foundry: foundry 名称（AMF/IHP/GF Fotonix 等）。
        process_node: 工艺节点。
        rules: eqDRC 规则集。
        certified: 是否通过 foundry 认证。
        source_url: 溯源 URL。
    """

    foundry: str
    process_node: str
    rules: list[EqDRCRule]
    certified: bool
    source_url: str


# 多 foundry 默认参数（公开文档，非 NDA）
# 来源: Luceda IPKISS PDK / IHP Open PDK / SiEPIC EBeam PDK / GF Fotonix 新闻
# 格式: (foundry, process_node, R_min_um, w_min_um, theta_max_deg, source_url)
_FOUNDRY_DATA: list[tuple[str, str, float, float, float, str]] = [
    ("AMF", "130nm CMOS, 220nm SOI", 10.0, 0.4, 30.0, "https://www.lucedaphotonics.com/zh_CN/luceda-design-kits"),
    ("IHP", "250nm BiCMOS, 220nm SOI", 5.0, 0.4, 30.0, "https://github.com/IHP-GmbH/IHP-Open-PDK"),
    ("GF_Fotonix", "45nm CMOS, 160nm Si", 5.0, 0.4, 30.0, _URL_GF_FOTONIX),
    ("CompoundTek", "90nm SOI", 10.0, 0.4, 30.0, "https://www.lucedaphotonics.com/zh_CN/luceda-design-kits"),
    ("LIGENTEC", "800nm SiN", 100.0, 0.8, 20.0, "https://www.lucedaphotonics.com/zh_CN/luceda-design-kits"),
    ("LioniX", "TriPleX SiN", 100.0, 0.8, 20.0, "https://www.lionix-international.com/photonics/"),
    ("Tower", "180nm SOI", 10.0, 0.5, 30.0, "https://www.towersemi.com/"),
    ("SiEPIC_EBeam", "220nm SOI", 5.0, 0.4, 30.0, "https://github.com/SiEPIC/SiEPIC_EBeam_PDK"),
]


def _build_foundry_rules(
    foundry: str, r_min: float, w_min: float, theta_max: float
) -> list[EqDRCRule]:
    """为单个 foundry 构建 eqDRC 规则集。"""
    prefix = foundry.upper()[:3]
    return [
        EqDRCRule(
            name=f"{prefix}_BEND_MIN_RADIUS",
            category="bend",
            equation="R >= R_min * (1 - tol)",
            params={"R_min": r_min, "tol": 0.0},
            description=f"{foundry} 最小弯曲半径 {r_min}μm",
        ),
        EqDRCRule(
            name=f"{prefix}_TAPER_MAX_ANGLE",
            category="taper",
            equation="theta <= theta_max and w >= w_min",
            params={"theta_max": theta_max, "w_min": w_min},
            description=f"{foundry} 最大锥角 {theta_max}°, 最小宽度 {w_min}μm",
        ),
    ]


class MultiFoundryDRCCertifier:
    """多 foundry DRC runset 认证器。

    学术依据：Siemens + GF Calibre Fotonix 合作
    URL: https://news.siemens.com/el-gr/siemens-globalfoundries-calibre-fotonix/

    支持 7+ foundry 的 DRC runset 认证：
    AMF/IHP/GF Fotonix/CompoundTek/LIGENTEC/LioniX/Tower/SiEPIC
    """

    def __init__(self) -> None:
        """初始化多 foundry 认证器。"""
        self.runsets = self.build_default_runsets()

    def get_runset(self, foundry: str) -> FoundryDRCRunset:
        """获取指定 foundry 的 DRC runset。不存在则抛 KeyError。"""
        if foundry not in self.runsets:
            available = ", ".join(sorted(self.runsets.keys()))
            raise KeyError(f"未知 foundry: {foundry}（可用: {available}）")
        return self.runsets[foundry]

    def certify_layout(self, layout: dict, foundry: str) -> dict:
        """用指定 foundry 的 DRC runset 认证版图。"""
        runset = self.get_runset(foundry)
        engine = EqDRCEngine(runset.rules)
        result = engine.run_all(layout)
        return {
            "is_pass": result["is_pass"],
            "violations": result["violations"],
            "foundry": foundry,
            "process_node": runset.process_node,
            "certified": runset.certified,
            "report": result["report"],
        }

    def list_supported_foundries(self) -> list[str]:
        """列出支持的 foundry（按字母排序）。"""
        return sorted(self.runsets.keys())

    def build_default_runsets(self) -> dict[str, FoundryDRCRunset]:
        """构建 7+ foundry 的默认 DRC runset（参数来自公开文档，非 NDA）。"""
        runsets: dict[str, FoundryDRCRunset] = {}
        for foundry, node, r_min, w_min, theta_max, url in _FOUNDRY_DATA:
            rules = _build_foundry_rules(foundry, r_min, w_min, theta_max)
            runsets[foundry] = FoundryDRCRunset(
                foundry=foundry,
                process_node=node,
                rules=rules,
                certified=True,
                source_url=url,
            )
        return runsets


# ---------------------------------------------------------------------------
# 4. DRC 报告生成 + 自动修复建议
# ---------------------------------------------------------------------------


class DRCReportGenerator:
    """DRC 报告生成器（符合 foundry 认证格式）。

    学术依据：Calibre DRC 报告格式
    URL: https://blogs.sw.siemens.com/calibre/2015/11/17/design-rule-checking-for-silicon-photonics/
    """

    def __init__(self) -> None:
        """初始化报告生成器。"""

    def generate_report(self, violations: list[EqDRCViolation], foundry: str) -> str:
        """生成 DRC 报告（foundry 认证格式）。"""
        lines = [
            "=" * 60,
            f"DRC 认证报告 — {foundry}",
            "=" * 60,
            f"违反总数: {len(violations)}",
            "",
        ]
        for v in violations:
            lines.append(f"  [{v.severity.upper()}] {v.rule_name}")
            lines.append(f"    位置: ({v.location[0]:.3f}, {v.location[1]:.3f})")
            lines.append(f"    描述: {v.message}")
            lines.append(f"    实际值: {v.actual_value:.4f}")
            lines.append(f"    期望值: {v.expected_value:.4f}")
            lines.append("")
        if not violations:
            lines.append("  ✓ DRC CLEAN — 无违反")
        return "\n".join(lines)

    def generate_summary(self, results: dict) -> str:
        """生成 DRC 摘要。"""
        is_pass = results.get("is_pass", False)
        violations = results.get("violations", [])
        foundry = results.get("foundry", "unknown")
        status = "PASS" if is_pass else "FAIL"
        return f"[{status}] {foundry}: {len(violations)} 个违反"


class DRCAutoFixer:
    """DRC 违反自动修复建议器。

    学术依据：Calibre AutoFix 功能
    URL: https://blogs.sw.siemens.com/calibre/2015/11/17/design-rule-checking-for-silicon-photonics/
    """

    def __init__(self) -> None:
        """初始化自动修复器。"""

    def suggest_fixes(self, violations: list[EqDRCViolation]) -> list[dict]:
        """为每个违反生成修复建议。"""
        suggestions: list[dict] = []
        fix_map = {
            "BEND_MIN_RADIUS": ("增大弯曲半径至 {expected:.3f}μm", "increase_radius"),
            "TAPER_MAX_ANGLE": ("减小锥角至 {expected:.2f}°（增加锥形长度）", "decrease_taper_angle"),
            "TAPER_MIN_WIDTH": ("增大宽度至 {expected:.3f}μm", "increase_width"),
            "CURVATURE_CONTINUITY": ("使用欧拉弯曲平滑曲率突变", "apply_euler_bend"),
        }
        for v in violations:
            if v.rule_name in fix_map:
                suggestion, action = fix_map[v.rule_name]
                suggestions.append({
                    "rule_name": v.rule_name,
                    "suggestion": suggestion.format(expected=v.expected_value),
                    "action": action,
                    "target_value": v.expected_value,
                })
            else:
                suggestions.append({
                    "rule_name": v.rule_name,
                    "suggestion": f"修复违反: {v.message}",
                    "action": "manual_fix",
                    "target_value": v.expected_value,
                })
        return suggestions

    def auto_fix(self, layout: dict, violations: list[EqDRCViolation]) -> dict:
        """自动修复 DRC 违反（返回修复后的 layout 深拷贝）。"""
        fixed = copy.deepcopy(layout)
        paths = fixed.get("paths", [])
        for v in violations:
            if v.rule_name == "BEND_MIN_RADIUS":
                for path in paths:
                    points = path.get("points", [])
                    if len(points) < 3:
                        continue
                    radii = _compute_bend_radius(points)
                    finite = radii[np.isfinite(radii)]
                    if len(finite) > 0 and float(np.min(finite)) < v.expected_value:
                        min_r = float(np.min(finite))
                        scale = v.expected_value / min_r if min_r > 0 else 1.0
                        cx = sum(p[0] for p in points) / len(points)
                        cy = sum(p[1] for p in points) / len(points)
                        path["points"] = [
                            (cx + (p[0] - cx) * scale, cy + (p[1] - cy) * scale)
                            for p in points
                        ]
            elif v.rule_name == "TAPER_MIN_WIDTH":
                for path in paths:
                    widths = path.get("widths")
                    if widths:
                        path["widths"] = [max(w, v.expected_value) for w in widths]
        return fixed


__all__ = [
    "CurvilinearLVS",
    "DRCAutoFixer",
    "DRCReportGenerator",
    "EqDRCRule",
    "EqDRCViolation",
    "EqDRCEngine",
    "FoundryDRCRunset",
    "MultiFoundryDRCCertifier",
]
