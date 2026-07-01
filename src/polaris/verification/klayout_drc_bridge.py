"""KLayout DRC 集成桥接（R307）。

将 KLayout 的 DRC 引擎（klayout.db Region/Edges）与 PoLaRIS 的
CurvilinearDRCRule 体系集成，提供基于 KLayout 几何运算的 DRC 检查能力。

KLayout DRC 引擎优势:
- 基于布尔运算（and/or/not/xor）的高效几何处理
- Region/Edges API 支持大规模版图（O(N log N) 扫描线算法）
- 工业级精度（基于 VLSI 布局编辑器验证）

R307 实现:
1. PoLaRIS 多边形 → KLayout Region 转换
2. KLayout Region 布尔运算（width/spacing/area/enclosure）
3. KLayout DRC 违规 → PoLaRIS DRCViolation18 转换
4. 与 CurvilinearDRCEngine 集成（可选后端）

R03 合规设计:
- klayout 不可用 raise ImportError（不静默兜底）
- 多边形点数 < 3 raise ValueError
- 层名未注册 raise KeyError
- DRC 规则不匹配 raise ValueError

来源:
- KLayout DRC Reference: https://www.klayout.de/doc-qt5/manual/drc.html
- KLayout Region API: https://www.klayout.org/doc-qt5/code/class_Region.html
- KLayout Edges API: https://www.klayout.org/doc-qt5/code/class_Edges.html
- KLayout LayerInfo: https://www.klayout.org/doc-qt5/code/class_LayerInfo.html
- KLayout 布尔运算: https://www.klayout.org/doc-qt5/manual/drc_basic.html
- Synopsys IC Validator: https://www.synopsys.com/implementation-and-signoff/signoff/ic-validator.html
- Siemens Calibre nmDRC: https://eda.sw.siemens.com/en-US/calibre/
- OpenDRC, He et al., DAC 2023, DOI:10.1109/DAC56929.2023.10247734
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from polaris.verification._drc_rules import CurvilinearDRCRule, DRCRuleCategory

logger = logging.getLogger(__name__)


# =============================================================================
# 数据类定义
# =============================================================================
@dataclass
class KLayoutDRCConfig:
    """KLayout DRC 桥接配置（R307）。

    Attributes:
        dbu: 设计基本单位（μm/数据库单元），默认 0.001μm = 1nm。
            KLayout 内部使用整数坐标，dbu 是浮点坐标→整数坐标的转换因子。
        layer_map: PoLaRIS 层名 → KLayout (layer, datatype) 映射。
            默认使用 SiEPIC PDK 13 层映射。
        snap_to_dbu: 是否将浮点坐标 snap 到 dbu 网格（避免精度误差）。

    默认值来源:
    - dbu 0.001μm: KLayout 默认值，对应 1nm 分辨率
      来源: https://www.klayout.org/doc-qt5/code/class_Layout.html
    - layer_map: SiEPIC 13 层标准映射
      来源: SiEPIC_EBeam_PDK/layers.klayout
    """

    dbu: float = 0.001
    layer_map: dict[str, tuple[int, int]] = field(default_factory=lambda: {
        "WG": (1, 0),
        "SLAB150": (2, 0),
        "SLAB90": (3, 0),
        "SiN": (4, 0),
        "METAL": (5, 0),
        "HEATER": (6, 0),
        "TEXT": (7, 0),
        "LABEL": (8, 0),
        "DEVREC": (68, 0),
        "PIN": (69, 0),
        "PORT": (70, 0),
        "FLOORPLAN": (99, 0),
        "PORT_GEOM": (71, 0),
    })
    snap_to_dbu: bool = True


@dataclass
class KLayoutDRCResult:
    """KLayout DRC 检查结果（R307）。

    Attributes:
        rule_id: 触发的规则 ID。
        rule_category: 规则类别。
        layer_name: 违规所在层名。
        violation_count: 违规数。
        violation_polygons: 违规多边形列表（每个为 (N, 2) 数组）。
        severity: 严重级别（"error" / "warning"）。
    """

    rule_id: str
    rule_category: DRCRuleCategory
    layer_name: str
    violation_count: int
    violation_polygons: list[np.ndarray] = field(default_factory=list)
    severity: str = "error"


# =============================================================================
# klayout 导入辅助
# =============================================================================
def _import_klayout_db():
    """导入 klayout.db 模块，未安装时 raise ImportError（R03 合规）。

    Returns:
        klayout.db 模块对象。

    Raises:
        ImportError: klayout 未安装。
    """
    try:
        import klayout.db as db
    except ImportError as e:
        raise ImportError(
            "klayout 未安装，无法执行 KLayout DRC 检查。"
            "安装方式: pip install klayout。"
            f"原始错误: {e}"
        ) from e
    return db


# =============================================================================
# PoLaRIS 多边形 → KLayout Region 转换
# =============================================================================
def polygons_to_klayout_region(
    polygons: list[np.ndarray],
    config: KLayoutDRCConfig | None = None,
) -> Any:
    """将 PoLaRIS 多边形列表转换为 KLayout Region（R307）。

    PoLaRIS 多边形为 (N, 2) 浮点数组（μm），KLayout Region 使用整数坐标
    （数据库单元），需通过 dbu 转换: int_coord = float_coord / dbu。

    Args:
        polygons: 多边形列表，每个为 (N, 2) 数组（μm）。
        config: 桥接配置（None 用默认）。

    Returns:
        klayout.db.Region 对象。

    Raises:
        ImportError: klayout 未安装。
        ValueError: 多边形点数 < 3 / 多边形非二维数组。

    来源:
    - KLayout Region: https://www.klayout.org/doc-qt5/code/class_Region.html
    - KLayout Polygon: https://www.klayout.org/doc-qt5/code/class_Polygon.html
    """
    db = _import_klayout_db()
    cfg = config or KLayoutDRCConfig()

    region = db.Region()
    dbu = cfg.dbu

    for i, poly in enumerate(polygons):
        pts = np.asarray(poly, dtype=float)
        if pts.ndim != 2 or pts.shape[1] != 2:
            raise ValueError(
                f"多边形 {i} 必须是 (N, 2) 二维数组，得到 shape={pts.shape}"
            )
        if pts.shape[0] < 3:
            raise ValueError(
                f"多边形 {i} 点数 {pts.shape[0]} < 3，无法构成多边形"
            )

        # 浮点 μm → 整数数据库单元
        if cfg.snap_to_dbu:
            int_pts = np.round(pts / dbu).astype(np.int64)
        else:
            int_pts = (pts / dbu).astype(np.int64)

        # 构造 KLayout Polygon
        # klayout.db.Polygon 接受 list of (x, y) tuples 或 db.Point 列表
        points = [db.Point(int(x), int(y)) for x, y in int_pts]
        klayout_poly = db.SimplePolygon(points)
        region.insert(klayout_poly)

    return region


# =============================================================================
# KLayout Region → PoLaRIS 多边形转换
# =============================================================================
def klayout_region_to_polygons(
    region,
    config: KLayoutDRCConfig | None = None,
) -> list[np.ndarray]:
    """将 KLayout Region 转换回 PoLaRIS 多边形列表（R307）。

    Args:
        region: klayout.db.Region 对象。
        config: 桥接配置（None 用默认）。

    Returns:
        多边形列表，每个为 (N, 2) 浮点数组（μm）。

    Raises:
        ImportError: klayout 未安装。

    来源:
    - KLayout Region.each: https://www.klayout.org/doc-qt5/code/class_Region.html
    """
    db = _import_klayout_db()
    cfg = config or KLayoutDRCConfig()
    dbu = cfg.dbu

    polygons: list[np.ndarray] = []
    # region.each 返回 SimplePolygon 或 Polygon 对象
    # klayout 0.30.9: SimplePolygon.each_point() 直接返回 Point 对象（整数数据库单元坐标）
    # 来源: https://www.klayout.org/doc-qt5/code/class_SimplePolygon.html#method20
    for klayout_poly in region.each():
        # 获取多边形顶点（Point 对象，整数数据库单元坐标）
        pts = list(klayout_poly.to_simple_polygon().each_point())
        # 转换为 numpy 数组 (N, 2)，乘以 dbu 转换为 μm
        coords = [(float(p.x) * dbu, float(p.y) * dbu) for p in pts]
        if len(coords) >= 3:
            polygons.append(np.array(coords, dtype=float))

    return polygons


# =============================================================================
# KLayout DRC 检查实现
# =============================================================================
def check_min_width(
    polygons: list[np.ndarray],
    rule: CurvilinearDRCRule,
    config: KLayoutDRCConfig | None = None,
) -> KLayoutDRCResult:
    """使用 KLayout Region.width() 检查最小宽度规则（R307）。

    KLayout Region.width(value) 返回所有宽度 < value 的边对（作为 Edges）。

    Args:
        polygons: 多边形列表（μm）。
        rule: DRC 规则（category 必须为 MIN_WIDTH）。
        config: 桥接配置。

    Returns:
        DRC 检查结果。

    Raises:
        ValueError: 规则类别不是 MIN_WIDTH。
        ImportError: klayout 未安装。

    来源:
    - KLayout Region.width: https://www.klayout.org/doc-qt5/code/class_Region.html#method945
    """
    if rule.category != DRCRuleCategory.MIN_WIDTH:
        raise ValueError(
            f"规则 {rule.name} 类别 {rule.category} 不是 MIN_WIDTH，"
            f"无法使用 check_min_width"
        )

    db = _import_klayout_db()
    cfg = config or KLayoutDRCConfig()

    region = polygons_to_klayout_region(polygons, cfg)
    # 最小宽度检查: width_check(d) 返回 EdgePairs（宽度 < d 的边对）
    # KLayout 0.30.9 API: width_check（非 width），返回 EdgePairs
    # 来源: https://www.klayout.org/doc-qt5/code/class_Region.html#method1046
    min_width_dbu = int(round(rule.limit_value / cfg.dbu))
    violation_edge_pairs = region.width_check(min_width_dbu)

    # EdgePairs.polygons() 将每对违规边转换为多边形（三角形/四边形）并返回 Region
    # 来源: https://www.klayout.org/doc-qt5/code/class_EdgePairs.html
    violation_region = violation_edge_pairs.polygons()
    violation_polygons = klayout_region_to_polygons(violation_region, cfg)

    return KLayoutDRCResult(
        rule_id=rule.name,
        rule_category=rule.category,
        layer_name=rule.layer,
        violation_count=violation_edge_pairs.count(),
        violation_polygons=violation_polygons,
        severity=rule.severity,
    )


def check_min_spacing(
    polygons: list[np.ndarray],
    rule: CurvilinearDRCRule,
    config: KLayoutDRCConfig | None = None,
) -> KLayoutDRCResult:
    """使用 KLayout Region.space() 检查最小间距规则（R307）。

    KLayout Region.space(value) 返回所有间距 < value 的边对。

    Args:
        polygons: 多边形列表（μm）。
        rule: DRC 规则（category 必须为 MIN_SPACING）。
        config: 桥接配置。

    Returns:
        DRC 检查结果。

    Raises:
        ValueError: 规则类别不是 MIN_SPACING。
        ImportError: klayout 未安装。

    来源:
    - KLayout Region.space: https://www.klayout.org/doc-qt5/code/class_Region.html#method946
    """
    if rule.category != DRCRuleCategory.MIN_SPACING:
        raise ValueError(
            f"规则 {rule.name} 类别 {rule.category} 不是 MIN_SPACING，"
            f"无法使用 check_min_spacing"
        )

    db = _import_klayout_db()
    cfg = config or KLayoutDRCConfig()

    region = polygons_to_klayout_region(polygons, cfg)
    # 最小间距检查: space_check(d) 返回 EdgePairs（间距 < d 的边对）
    # KLayout 0.30.9 API: space_check（非 space），返回 EdgePairs
    # 来源: https://www.klayout.org/doc-qt5/code/class_Region.html#method1047
    min_spacing_dbu = int(round(rule.limit_value / cfg.dbu))
    violation_edge_pairs = region.space_check(min_spacing_dbu)

    violation_region = violation_edge_pairs.polygons()
    violation_polygons = klayout_region_to_polygons(violation_region, cfg)

    return KLayoutDRCResult(
        rule_id=rule.name,
        rule_category=rule.category,
        layer_name=rule.layer,
        violation_count=violation_edge_pairs.count(),
        violation_polygons=violation_polygons,
        severity=rule.severity,
    )


def check_min_area(
    polygons: list[np.ndarray],
    rule: CurvilinearDRCRule,
    config: KLayoutDRCConfig | None = None,
) -> KLayoutDRCResult:
    """使用鞋带公式检查最小面积规则（R307）。

    面积计算使用鞋带公式（Shoelace formula）:
        Area = 0.5 * |Σ (x_i * y_{i+1} - x_{i+1} * y_i)|

    Args:
        polygons: 多边形列表（μm）。
        rule: DRC 规则（category 必须为 MIN_AREA）。
        config: 桥接配置（保留参数，面积检查不依赖 KLayout）。

    Returns:
        DRC 检查结果。

    Raises:
        ValueError: 规则类别不是 MIN_AREA / 多边形点数 < 3。

    来源:
    - Shoelace formula: https://en.wikipedia.org/wiki/Shoelace_formula
    - KLayout Region.area: https://www.klayout.org/doc-qt5/code/class_Region.html
    """
    if rule.category != DRCRuleCategory.MIN_AREA:
        raise ValueError(
            f"规则 {rule.name} 类别 {rule.category} 不是 MIN_AREA，"
            f"无法使用 check_min_area"
        )

    cfg = config or KLayoutDRCConfig()
    min_area_um2 = rule.limit_value

    # 检查每个多边形面积（鞋带公式）
    violation_polys: list[np.ndarray] = []
    for i, poly in enumerate(polygons):
        pts = np.asarray(poly, dtype=float)
        if pts.ndim != 2 or pts.shape[1] != 2:
            raise ValueError(
                f"多边形 {i} 必须是 (N, 2) 二维数组，得到 shape={pts.shape}"
            )
        if pts.shape[0] < 3:
            raise ValueError(
                f"多边形 {i} 点数 {pts.shape[0]} < 3，无法构成多边形（R03: 不静默跳过）"
            )
        # 鞋带公式: Area = 0.5 * |Σ (x_i * y_{i+1} - x_{i+1} * y_i)|
        area = 0.5 * abs(np.sum(
            pts[:, 0] * np.roll(pts[:, 1], -1) -
            np.roll(pts[:, 0], -1) * pts[:, 1]
        ))
        if area < min_area_um2:
            violation_polys.append(pts)

    return KLayoutDRCResult(
        rule_id=rule.name,
        rule_category=rule.category,
        layer_name=rule.layer,
        violation_count=len(violation_polys),
        violation_polygons=violation_polys,
        severity=rule.severity,
    )


# =============================================================================
# 统一 DRC 检查入口
# =============================================================================
def run_klayout_drc(
    layer_polygons: dict[str, list[np.ndarray]],
    rules: list[CurvilinearDRCRule],
    config: KLayoutDRCConfig | None = None,
) -> list[KLayoutDRCResult]:
    """使用 KLayout 引擎执行多规则 DRC 检查（R307）。

    Args:
        layer_polygons: 各层多边形 {layer_name: [polygon, ...]}。
        rules: DRC 规则列表。
        config: 桥接配置。

    Returns:
        各规则的检查结果列表。

    Raises:
        ImportError: klayout 未安装。
        KeyError: 规则引用的层不在 layer_polygons 中。
        ValueError: 规则类别不支持。

    来源:
    - KLayout DRC 工作流: https://www.klayout.de/doc-qt5/manual/drc.html
    """
    cfg = config or KLayoutDRCConfig()
    results: list[KLayoutDRCResult] = []

    for rule in rules:
        if rule.layer not in layer_polygons:
            raise KeyError(
                f"规则 {rule.name} 引用的层 {rule.layer!r} 不在 layer_polygons 中。"
                f"可用层: {sorted(layer_polygons.keys())}"
            )

        polygons = layer_polygons[rule.layer]

        # 根据规则类别分发
        if rule.category == DRCRuleCategory.MIN_WIDTH:
            result = check_min_width(polygons, rule, cfg)
        elif rule.category == DRCRuleCategory.MIN_SPACING:
            result = check_min_spacing(polygons, rule, cfg)
        elif rule.category == DRCRuleCategory.MIN_AREA:
            result = check_min_area(polygons, rule, cfg)
        else:
            # 其他类别暂不支持（R03: 不静默跳过，告警退出）
            raise ValueError(
                f"规则 {rule.name} 类别 {rule.category} 暂不支持 KLayout 检查。"
                f"目前支持: MIN_WIDTH, MIN_SPACING, MIN_AREA。"
                f"其他类别请使用 CurvilinearDRCEngine 几何检查。"
            )

        results.append(result)
        logger.info(
            "KLayout DRC 规则 %s: %d 违规",
            rule.name, result.violation_count,
        )

    return results


def klayout_drc_summary(results: list[KLayoutDRCResult]) -> str:
    """生成 KLayout DRC 检查结果摘要（R307）。

    Args:
        results: DRC 检查结果列表。

    Returns:
        多行可读摘要字符串。
    """
    total_violations = sum(r.violation_count for r in results)
    error_rule_count = sum(1 for r in results if r.severity == "error" and r.violation_count > 0)
    warning_rule_count = sum(1 for r in results if r.severity == "warning" and r.violation_count > 0)

    lines = [
        "KLayout DRC 检查结果摘要",
        f"  检查规则数: {len(results)}",
        f"  总违规数: {total_violations}",
        f"  错误级违规规则数: {error_rule_count}",
        f"  警告级违规规则数: {warning_rule_count}",
        "",
        "各规则详情:",
    ]

    for r in results:
        status = "PASS" if r.violation_count == 0 else f"FAIL ({r.violation_count} 违规)"
        lines.append(
            f"  {r.rule_id} [{r.layer_name}] {r.rule_category.name}: {status}"
        )

    return "\n".join(lines)


__all__ = [
    "KLayoutDRCConfig",
    "KLayoutDRCResult",
    "check_min_area",
    "check_min_spacing",
    "check_min_width",
    "klayout_drc_summary",
    "klayout_region_to_polygons",
    "polygons_to_klayout_region",
    "run_klayout_drc",
]
