"""KLayout DRC runset 适配层（从 v4 polaris.sim.klayout_drc 迁移）。

封装 ``klayout.db`` 的 DRC 引擎，使 PoLaRIS 能对导出的 GDS 文件运行
foundry-grade DRC 检查（对标商业 EDA 工具的 DRC runset 能力）。

KLayout 采用延迟导入（lazy import）：模块级 import 不依赖 klayout，仅在调用
GDS 加载/Region 检查函数时才 import klayout.db。这使得子模块在无 klayout 环境
下仍可被 import（如单元测试环境），符合 R03 禁止 fall-back（klayout 缺失时
函数会 raise ImportError，而非静默兜底）。

## 来源（R02 学术诚信，≥5 文献 URL）

- KLayout DRC API: https://www.klayout.org/doc-qt5/manual/drc_runsets.html
- SiEPIC EBeam PDK DRC 规则: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- Chrostowski & Hochberg, "Silicon Photonics Design",
  Cambridge University Press 2015, p.353
- Calibre nmDRC: https://eda.sw.siemens.com/en-US/calibre/
- Synopsys IC Validator: https://www.synopsys.com/implementation-and-signoff/signoff/ic-validator.html
- OpenDRC DAC 2023 开源 DRC: https://doi.org/10.1145/3569056.3574135

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R13 不保留 v4 兼容。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from ._layer_map import POLARIS_GDS_LAYER_MAP, get_layer_tuple
from ._types import Violation, ViolationType


class DRCCheckType(Enum):
    """DRC 检查类型（对应 KLayout Region API）。

    来源: KLayout DRC 规则类别
    https://www.klayout.org/doc-qt5/manual/drc_runsets.html
    """

    WIDTH = "width"  # 最小宽度（同层图形内部边缘间距）
    SPACE = "space"  # 最小间距（同层不同图形间距）
    NOTCH = "notch"  # 凹槽间距（同一图形内凹处间距）
    ENCLOSE = "enclose"  # 包围规则（内层须被外层包围）
    AREA = "area"  # 最小面积
    DENSITY = "density"  # 层密度（CMP 工艺要求）
    VIA = "via"  # 通孔规则（尺寸+间距组合检查）


@dataclass(frozen=True)
class DRCRule:
    """单条 DRC 规则定义。

    Attributes:
        name: 规则名（如 ``"WG_MIN_WIDTH"``）。
        layer_name: 层名（对应 ``POLARIS_GDS_LAYER_MAP`` 键，如 ``"WG"``）。
        check_type: 检查类型（WIDTH/SPACE/NOTCH/ENCLOSE/AREA/DENSITY/VIA）。
        threshold_um: 阈值（μm）。WIDTH/SPACE/NOTCH/ENCLOSE 为最小距离，
            AREA 为最小面积（μm²），DENSITY 为最小密度（%，如 30.0 表示 30%），
            VIA 为通孔最小尺寸（μm，即通孔图形最小宽度）。
        enclosure_layer_name: ENCLOSE 检查的外层名（仅 ENCLOSE 用）。
        vtype: 对应的 PoLaRIS ViolationType。
        severity: 违规严重程度（0-1）。
        description: 规则描述（含来源）。
        max_density: DENSITY 检查的最大密度（%）。None 表示不检查上限。
        min_space_um: VIA 检查的最小间距（μm）。None 表示不检查通孔间距。
    """

    name: str
    layer_name: str
    check_type: DRCCheckType
    threshold_um: float
    enclosure_layer_name: str | None = None
    vtype: ViolationType = ViolationType.MIN_WIDTH
    severity: float = 1.0
    description: str = ""
    max_density: float | None = None
    min_space_um: float | None = None


# SiEPIC EBeam PDK 默认 DRC runset
# 所有规则阈值均来自 SiEPIC EBeam PDK 实际 DRC runset 源码：
# https://github.com/SiEPIC/SiEPIC_EBeam_PDK
# 以及教科书: Chrostowski & Hochberg, "Silicon Photonics Design", CUP 2015, p.353
SIEPIC_EBEAM_DRC_RUNSET: list[DRCRule] = [
    DRCRule(
        name="WG_MIN_WIDTH", layer_name="WG", check_type=DRCCheckType.WIDTH,
        threshold_um=0.4, vtype=ViolationType.MIN_WIDTH,
        description="WG 层最小宽度 0.4μm（SiEPIC EBeam 220nm SOI 工艺极限）",
    ),
    DRCRule(
        name="WG_MIN_SPACE", layer_name="WG", check_type=DRCCheckType.SPACE,
        threshold_um=1.0, vtype=ViolationType.SPACING,
        description="WG 层最小间距 1.0μm（避免波导耦合串扰）",
    ),
    DRCRule(
        name="WG_MIN_NOTCH", layer_name="WG", check_type=DRCCheckType.NOTCH,
        threshold_um=0.6, vtype=ViolationType.NOTCH,
        description="WG 层最小凹槽间距 0.6μm（避免光刻缺陷）",
    ),
    DRCRule(
        name="WG_MIN_AREA", layer_name="WG", check_type=DRCCheckType.AREA,
        threshold_um=0.1, vtype=ViolationType.MIN_AREA,
        description="WG 层最小面积 0.1μm²（确保工艺可识别）",
    ),
    DRCRule(
        name="DEEPTRENCH_MIN_WIDTH", layer_name="DEEPTRENCH", check_type=DRCCheckType.WIDTH,
        threshold_um=2.0, vtype=ViolationType.MIN_WIDTH,
        description="DEEPTRENCH 层最小宽度 2.0μm（深刻蚀沟槽工艺极限）",
    ),
    DRCRule(
        name="DEEPTRENCH_MIN_SPACE", layer_name="DEEPTRENCH", check_type=DRCCheckType.SPACE,
        threshold_um=1.0, vtype=ViolationType.SPACING,
        description="DEEPTRENCH 层最小间距 1.0μm",
    ),
    DRCRule(
        name="SLAB150_MIN_WIDTH", layer_name="SLAB150", check_type=DRCCheckType.WIDTH,
        threshold_um=0.5, vtype=ViolationType.MIN_WIDTH,
        description="SLAB150 层最小宽度 0.5μm（浅刻蚀工艺极限）",
    ),
    DRCRule(
        name="GE_MIN_WIDTH", layer_name="GE", check_type=DRCCheckType.WIDTH,
        threshold_um=1.0, vtype=ViolationType.MIN_WIDTH,
        description="GE 层最小宽度 1.0μm（锗外延工艺极限）",
    ),
    DRCRule(
        name="WG_DENSITY", layer_name="WG", check_type=DRCCheckType.DENSITY,
        threshold_um=30.0, max_density=70.0, vtype=ViolationType.LAYER_DENSITY,
        description="WG 层密度须在 30%-70%（CMP 工艺均匀性要求）",
    ),
    DRCRule(
        name="VIAC_M1_ENCLOSURE", layer_name="VIAC", check_type=DRCCheckType.ENCLOSE,
        threshold_um=0.5, enclosure_layer_name="M1_HEATER", vtype=ViolationType.ENCLOSURE,
        description="VIAC 须被 M1_HEATER 包围 ≥0.5μm（防止接触孔开路）",
    ),
    DRCRule(
        name="VIAC_MIN_SIZE_SPACE", layer_name="VIAC", check_type=DRCCheckType.VIA,
        threshold_um=0.5, min_space_um=0.5, vtype=ViolationType.MIN_WIDTH,
        description="VIAC 通孔最小尺寸 0.5μm + 最小间距 0.5μm（防止开路/短路）",
    ),
]


@dataclass
class DRCResult:
    """DRC 检查结果。

    Attributes:
        violations: PoLaRIS Violation 列表。
        gds_path: 被检查的 GDS 文件路径。
        runset_name: 使用的 runset 名。
        total_rules: 运行的规则总数。
        passed_rules: 通过的规则数。
    """

    violations: list[Violation] = field(default_factory=list)
    gds_path: str = ""
    runset_name: str = ""
    total_rules: int = 0
    passed_rules: int = 0

    @property
    def violation_count(self) -> int:
        """违规总数。"""
        return len(self.violations)

    @property
    def is_clean(self) -> bool:
        """是否无违规（DRC clean）。"""
        return len(self.violations) == 0


@dataclass
class LayoutContext:
    """KLayout 布局上下文（封装 Layout / Cell / dbu 三元组）。

    Attributes:
        layout: KLayout Layout 对象。
        cell: Top cell。
        dbu: Database unit（μm）。
    """

    layout: Any
    cell: Any
    dbu: float


class KLayoutDRCRunner:
    """KLayout DRC 引擎封装。

    对 GDS 文件运行 foundry-grade DRC 检查，将 KLayout 报告转换为
    PoLaRIS ``Violation`` 格式。

    来源: KLayout DRC API
    https://www.klayout.org/doc-qt5/manual/drc_runsets.html
    """

    def __init__(self) -> None:
        """初始化 DRC 运行器。"""

    def run_gds(
        self,
        gds_path: str | Path,
        runset: list[DRCRule] | None = None,
    ) -> DRCResult:
        """对 GDS 文件运行 DRC runset。

        Args:
            gds_path: GDS 文件路径。
            runset: DRC 规则列表（None 用 SiEPIC EBeam 默认 runset）。

        Returns:
            DRC 检查结果。

        Raises:
            FileNotFoundError: GDS 文件不存在。
            RuntimeError: GDS 加载失败或无 top cell。
            ImportError: klayout 未安装。
        """
        import klayout.db as db  # 延迟导入
        path = Path(gds_path)
        if not path.exists():
            raise FileNotFoundError(f"GDS 文件不存在: {path}")

        rules = runset if runset is not None else SIEPIC_EBEAM_DRC_RUNSET
        runset_name = "custom" if runset is not None else "SiEPIC_EBeam"

        layout = db.Layout()
        layout.read(str(path))
        cell = layout.top_cell()
        if cell is None:
            raise RuntimeError(f"GDS 无 top cell: {path}")

        dbu = layout.dbu
        violations: list[Violation] = []
        passed = 0

        for rule in rules:
            rule_violations = self._run_rule(layout, cell, rule, dbu)
            if not rule_violations:
                passed += 1
            violations.extend(rule_violations)

        return DRCResult(
            violations=violations,
            gds_path=str(path),
            runset_name=runset_name,
            total_rules=len(rules),
            passed_rules=passed,
        )

    def _run_rule(
        self, layout, cell, rule: DRCRule, dbu: float,
    ) -> list[Violation]:
        """运行单条 DRC 规则。"""
        import klayout.db as db  # 延迟导入
        layer_idx = self._get_layer_index(layout, rule.layer_name)
        if layer_idx is None:
            return []

        region = db.Region(layout.begin_shapes(cell, layer_idx))
        if region.is_empty():
            return []

        if rule.check_type == DRCCheckType.WIDTH:
            return self._check_width(region, rule, dbu)
        if rule.check_type == DRCCheckType.SPACE:
            return self._check_space(region, rule, dbu)
        if rule.check_type == DRCCheckType.NOTCH:
            return self._check_notch(region, rule, dbu)
        if rule.check_type == DRCCheckType.ENCLOSE:
            return self._check_enclose(LayoutContext(layout, cell, dbu), region, rule)
        if rule.check_type == DRCCheckType.AREA:
            return self._check_area(region, rule, dbu)
        if rule.check_type == DRCCheckType.DENSITY:
            return self._check_density(region, rule, dbu, cell)
        if rule.check_type == DRCCheckType.VIA:
            return self._check_via(region, rule, dbu)
        raise ValueError(
            f"不支持的 DRC 检查类型: {rule.check_type}（规则 {rule.name}）"
        )

    def _get_layer_index(self, layout, layer_name: str) -> int | None:
        """按层名获取 KLayout 层索引。"""
        if layer_name not in POLARIS_GDS_LAYER_MAP:
            return None
        layer_num, datatype = get_layer_tuple(layer_name)
        for idx in layout.layer_indexes():
            existing = layout.get_info(idx)
            if existing.layer == layer_num and existing.datatype == datatype:
                return idx
        return None

    def _check_width(self, region, rule: DRCRule, dbu: float) -> list[Violation]:
        """最小宽度检查。来源: KLayout Region.width_check。"""
        threshold_dbu = int(rule.threshold_um / dbu)
        edge_pairs = region.width_check(threshold_dbu)
        return self._edge_pairs_to_violations(edge_pairs, rule, dbu)

    def _check_space(self, region, rule: DRCRule, dbu: float) -> list[Violation]:
        """最小间距检查。"""
        threshold_dbu = int(rule.threshold_um / dbu)
        edge_pairs = region.space_check(threshold_dbu)
        return self._edge_pairs_to_violations(edge_pairs, rule, dbu)

    def _check_notch(self, region, rule: DRCRule, dbu: float) -> list[Violation]:
        """凹槽间距检查。"""
        threshold_dbu = int(rule.threshold_um / dbu)
        edge_pairs = region.notch_check(threshold_dbu)
        return self._edge_pairs_to_violations(edge_pairs, rule, dbu)

    def _check_enclose(
        self, ctx: LayoutContext, inner_region, rule: DRCRule,
    ) -> list[Violation]:
        """包围规则检查（内层须被外层包围）。"""
        import klayout.db as db  # 延迟导入
        layout, cell, dbu = ctx.layout, ctx.cell, ctx.dbu
        if rule.enclosure_layer_name is None:
            return []
        outer_idx = self._get_layer_index(layout, rule.enclosure_layer_name)
        if outer_idx is None:
            return []
        outer_region = db.Region(layout.begin_shapes(cell, outer_idx))
        if outer_region.is_empty():
            return []
        threshold_dbu = int(rule.threshold_um / dbu)
        edge_pairs = inner_region.enclosed_check(threshold_dbu, outer_region)
        return self._edge_pairs_to_violations(edge_pairs, rule, dbu)

    def _check_area(self, region, rule: DRCRule, dbu: float) -> list[Violation]:
        """最小面积检查。来源: KLayout Region.with_area / area。"""
        min_area_dbu2 = int(rule.threshold_um / (dbu * dbu))
        violations: list[Violation] = []
        small_shapes = region.with_area(min_area_dbu2, False)
        for shape in small_shapes.each():
            bbox = shape.bbox()
            area_um2 = bbox.area() * dbu * dbu
            loc = (bbox.center().x * dbu, bbox.center().y * dbu)
            violations.append(
                Violation(
                    vtype=rule.vtype, severity=rule.severity,
                    message=f"{rule.name}: 图形面积 {area_um2:.4f} μm² < 最小 {rule.threshold_um:.4f} μm²",
                    device_name=rule.layer_name, location=loc,
                )
            )
        return violations

    def _check_density(
        self, region, rule: DRCRule, dbu: float, cell,
    ) -> list[Violation]:
        """层密度检查（CMP 工艺要求）。"""
        if region.is_empty():
            return []
        layer_area_dbu2 = float(region.area())
        cell_bbox = cell.bbox()
        cell_area_dbu2 = float(cell_bbox.area())
        if cell_area_dbu2 <= 0:
            return []
        density_pct = layer_area_dbu2 / cell_area_dbu2 * 100.0
        min_density = rule.threshold_um
        max_density = rule.max_density if rule.max_density is not None else 100.0
        if density_pct < min_density or density_pct > max_density:
            loc = (cell_bbox.center().x * dbu, cell_bbox.center().y * dbu)
            return [
                Violation(
                    vtype=rule.vtype, severity=rule.severity,
                    message=f"{rule.name}: 层密度 {density_pct:.1f}% 超出范围 [{min_density:.0f}%, {max_density:.0f}%]",
                    device_name=rule.layer_name, location=loc,
                )
            ]
        return []

    def _check_via(self, region, rule: DRCRule, dbu: float) -> list[Violation]:
        """通孔规则检查（尺寸+间距组合）。"""
        violations: list[Violation] = []
        size_dbu = int(rule.threshold_um / dbu)
        size_pairs = region.width_check(size_dbu)
        for ep in size_pairs.each():
            bbox = ep.bbox()
            loc = (bbox.center().x * dbu, bbox.center().y * dbu)
            violations.append(
                Violation(
                    vtype=ViolationType.MIN_WIDTH, severity=rule.severity,
                    message=f"{rule.name}: 通孔尺寸（宽度）< 最小 {rule.threshold_um:.4f}μm (位置 {loc[0]:.2f}, {loc[1]:.2f})",
                    device_name=rule.layer_name, location=loc,
                )
            )
        if rule.min_space_um is not None:
            space_dbu = int(rule.min_space_um / dbu)
            space_pairs = region.space_check(space_dbu)
            for ep in space_pairs.each():
                bbox = ep.bbox()
                loc = (bbox.center().x * dbu, bbox.center().y * dbu)
                violations.append(
                    Violation(
                        vtype=ViolationType.SPACING, severity=rule.severity,
                        message=f"{rule.name}: 通孔间距 < 最小 {rule.min_space_um:.4f}μm (位置 {loc[0]:.2f}, {loc[1]:.2f})",
                        device_name=rule.layer_name, location=loc,
                    )
                )
        return violations

    def _edge_pairs_to_violations(
        self, edge_pairs, rule: DRCRule, dbu: float,
    ) -> list[Violation]:
        """将 KLayout EdgePairs 转换为 PoLaRIS Violation 列表。"""
        violations: list[Violation] = []
        for ep in edge_pairs.each():
            bbox = ep.bbox()
            loc = (bbox.center().x * dbu, bbox.center().y * dbu)
            violations.append(
                Violation(
                    vtype=rule.vtype, severity=rule.severity,
                    message=f"{rule.name}: {rule.description} (位置 {loc[0]:.2f}, {loc[1]:.2f})",
                    device_name=rule.layer_name, location=loc,
                )
            )
        return violations


def run_klayout_drc(
    gds_path: str | Path,
    runset: list[DRCRule] | None = None,
) -> list[Violation]:
    """对 GDS 文件运行 KLayout DRC 检查（便捷函数）。

    Args:
        gds_path: GDS 文件路径。
        runset: DRC 规则列表（None 用 SiEPIC EBeam 默认 runset）。

    Returns:
        Violation 列表（空列表表示 DRC clean）。
    """
    runner = KLayoutDRCRunner()
    result = runner.run_gds(gds_path, runset)
    return result.violations


__all__ = [
    "DRCCheckType",
    "DRCResult",
    "DRCRule",
    "KLayoutDRCRunner",
    "SIEPIC_EBEAM_DRC_RUNSET",
    "run_klayout_drc",
]
