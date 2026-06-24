"""KLayout DRC runset 适配层（第2轮 P0-1）。

封装 ``klayout.db`` 的 DRC 引擎，使 PoLaRIS 能对导出的 GDS 文件运行
foundry-grade DRC 检查（对标商业 EDA 工具的 DRC runset 能力）。

## 为什么需要这一层

第1轮已将 PoLaRIS 的纯 Python DRC 检查从 8 项扩展到 16 项，但这些检查
只针对 PoLaRIS 内部数据结构（placements dict / paths dict），无法对真实
GDS 文件运行 foundry 认证的 DRC runset。foundry 不接受未经认证 DRC 的 GDS，
这阻断 tape-out 流程。

本模块封装 KLayout 的 ``Region.width_check`` / ``space_check`` /
``notch_check`` / ``enclosed_check`` API，提供与 PoLaRIS ``Violation``
格式兼容的 DRC 报告，使 PoLaRIS 具备工业级 DRC 能力。

## 来源

- KLayout DRC API: https://www.klayout.org/doc-qt5/manual/drc_runsets.html
- SiEPIC EBeam PDK DRC 规则: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- Chrostowski & Hochberg, "Silicon Photonics Design",
  Cambridge University Press 2015, p.353

## 合规性

- project_rules.md 规则 3.2/5.3: klayout 0.30.9 已装，直接 import，无兜底
- project_rules.md 规则 4.1: klayout 活跃维护，直接集成，不复刻
- project_rules.md 规则 7.1: 文件 < 500 行
- project_rules.md 规则 11.2: 标注 KLayout DRC API 文档来源
- project_rules.md 规则 18: 所有 layer 编号/DRC 阈值来自开源仓库实际源码
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

import klayout.db as db

from polaris.pdk.layer_map import POLARIS_GDS_LAYER_MAP, get_layer_tuple
from polaris.sim.constraint_checker import Violation, ViolationType


class DRCCheckType(Enum):
    """DRC 检查类型（对应 KLayout Region API）。

    来源: KLayout DRC 规则类别
    https://www.klayout.org/doc-qt5/manual/drc_runsets.html
<<<<<<< HEAD

    第85轮扩展: 添加 DENSITY 检查类型（CMP 工艺密度规则）。
    来源: Banerjee, "CMOS Photonic Circuits", Springer 2024，
    CMP 工艺要求层密度在 30%-70% 范围内，避免化学机械抛光不均匀。
=======
>>>>>>> trae/solo-agent-pkVjID
    """

    WIDTH = "width"  # 最小宽度（同层图形内部边缘间距）
    SPACE = "space"  # 最小间距（同层不同图形间距）
    NOTCH = "notch"  # 凹槽间距（同一图形内凹处间距）
    ENCLOSE = "enclose"  # 包围规则（内层须被外层包围）
    AREA = "area"  # 最小面积
<<<<<<< HEAD
    DENSITY = "density"  # 层密度（CMP 工艺要求，第85轮新增）
=======
>>>>>>> trae/solo-agent-pkVjID


@dataclass(frozen=True)
class DRCRule:
    """单条 DRC 规则定义。

    Attributes:
        name: 规则名（如 ``"WG_MIN_WIDTH"``）。
        layer_name: 层名（对应 ``POLARIS_GDS_LAYER_MAP`` 键，如 ``"WG"``）。
<<<<<<< HEAD
        check_type: 检查类型（WIDTH/SPACE/NOTCH/ENCLOSE/AREA/DENSITY）。
        threshold_um: 阈值（μm）。WIDTH/SPACE/NOTCH/ENCLOSE 为最小距离，
            AREA 为最小面积（μm²），DENSITY 为最小密度（%，如 30.0 表示 30%）。
=======
        check_type: 检查类型（WIDTH/SPACE/NOTCH/ENCLOSE/AREA）。
        threshold_um: 阈值（μm）。WIDTH/SPACE/NOTCH/ENCLOSE 为最小距离，
            AREA 为最小面积（μm²）。
>>>>>>> trae/solo-agent-pkVjID
        enclosure_layer_name: ENCLOSE 检查的外层名（仅 ENCLOSE 用）。
        vtype: 对应的 PoLaRIS ViolationType。
        severity: 违规严重程度（0-1）。
        description: 规则描述（含来源）。
<<<<<<< HEAD
        max_density: DENSITY 检查的最大密度（%，第85轮新增）。
            仅 DENSITY 检查使用，None 表示不检查上限。
=======
>>>>>>> trae/solo-agent-pkVjID
    """

    name: str
    layer_name: str
    check_type: DRCCheckType
    threshold_um: float
    enclosure_layer_name: str | None = None
    vtype: ViolationType = ViolationType.MIN_WIDTH
    severity: float = 1.0
    description: str = ""
<<<<<<< HEAD
    max_density: float | None = None  # 第85轮新增，DENSITY 检查上限
=======
>>>>>>> trae/solo-agent-pkVjID


# SiEPIC EBeam PDK 默认 DRC runset
#
# 所有规则阈值均来自 SiEPIC EBeam PDK 实际 DRC runset 源码：
# https://github.com/SiEPIC/SiEPIC_EBeam_PDK
# 以及教科书: Chrostowski & Hochberg, "Silicon Photonics Design",
# Cambridge University Press 2015, p.353
#
# 学术诚信（规则 18）: 阈值来自开源仓库实际源码，禁止编造
SIEPIC_EBEAM_DRC_RUNSET: list[DRCRule] = [
    DRCRule(
        name="WG_MIN_WIDTH",
        layer_name="WG",
        check_type=DRCCheckType.WIDTH,
        threshold_um=0.4,
        vtype=ViolationType.MIN_WIDTH,
        description="WG 层最小宽度 0.4μm（SiEPIC EBeam 220nm SOI 工艺极限）",
    ),
    DRCRule(
        name="WG_MIN_SPACE",
        layer_name="WG",
        check_type=DRCCheckType.SPACE,
        threshold_um=1.0,
        vtype=ViolationType.SPACING,
        description="WG 层最小间距 1.0μm（避免波导耦合串扰）",
    ),
    DRCRule(
        name="WG_MIN_NOTCH",
        layer_name="WG",
        check_type=DRCCheckType.NOTCH,
        threshold_um=0.6,
        vtype=ViolationType.NOTCH,
        description="WG 层最小凹槽间距 0.6μm（避免光刻缺陷）",
    ),
    DRCRule(
        name="WG_MIN_AREA",
        layer_name="WG",
        check_type=DRCCheckType.AREA,
        threshold_um=0.1,
        vtype=ViolationType.MIN_AREA,
        description="WG 层最小面积 0.1μm²（确保工艺可识别）",
    ),
    DRCRule(
        name="DEEPTRENCH_MIN_WIDTH",
        layer_name="DEEPTRENCH",
        check_type=DRCCheckType.WIDTH,
        threshold_um=2.0,
        vtype=ViolationType.MIN_WIDTH,
        description="DEEPTRENCH 层最小宽度 2.0μm（深刻蚀沟槽工艺极限）",
    ),
    DRCRule(
        name="DEEPTRENCH_MIN_SPACE",
        layer_name="DEEPTRENCH",
        check_type=DRCCheckType.SPACE,
        threshold_um=1.0,
        vtype=ViolationType.SPACING,
        description="DEEPTRENCH 层最小间距 1.0μm",
    ),
    DRCRule(
        name="SLAB150_MIN_WIDTH",
        layer_name="SLAB150",
        check_type=DRCCheckType.WIDTH,
        threshold_um=0.5,
        vtype=ViolationType.MIN_WIDTH,
        description="SLAB150 层最小宽度 0.5μm（浅刻蚀工艺极限）",
    ),
    DRCRule(
        name="GE_MIN_WIDTH",
        layer_name="GE",
        check_type=DRCCheckType.WIDTH,
        threshold_um=1.0,
        vtype=ViolationType.MIN_WIDTH,
        description="GE 层最小宽度 1.0μm（锗外延工艺极限）",
    ),
<<<<<<< HEAD
    # 第85轮新增：DENSITY 检查（CMP 工艺密度规则）
    # 来源: Banerjee, "CMOS Photonic Circuits", Springer 2024
    # CMP 工艺要求层密度在 30%-70% 范围内，避免化学机械抛光不均匀
    DRCRule(
        name="WG_DENSITY",
        layer_name="WG",
        check_type=DRCCheckType.DENSITY,
        threshold_um=30.0,  # 最小密度 30%
        max_density=70.0,  # 最大密度 70%
        vtype=ViolationType.LAYER_DENSITY,
        description="WG 层密度须在 30%-70%（CMP 工艺均匀性要求）",
    ),
    # 第87轮新增：VIA ENCLOSURE 检查（VIAC 须被 M1_HEATER 包围）
    # 来源: SiEPIC EBeam PDK 规格表，Chrostowski & Hochberg "Silicon Photonics Design" CUP 2015
    DRCRule(
        name="VIAC_M1_ENCLOSURE",
        layer_name="VIAC",
        check_type=DRCCheckType.ENCLOSE,
        threshold_um=0.5,
        enclosure_layer_name="M1_HEATER",
        vtype=ViolationType.ENCLOSEMENT,
        description="VIAC 须被 M1_HEATER 包围 ≥0.5μm（防止接触孔开路）",
    ),
=======
>>>>>>> trae/solo-agent-pkVjID
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
    """KLayout 布局上下文（降低 _check_enclose 参数个数，规则 4.1）。

    封装 DRC 检查所需的 Layout / Cell / dbu 三元组。

    Attributes:
        layout: KLayout Layout 对象。
        cell: Top cell。
        dbu: Database unit（μm）。
    """

    layout: db.Layout
    cell: db.Cell
    dbu: float


class KLayoutDRCRunner:
    """KLayout DRC 引擎封装。

    对 GDS 文件运行 foundry-grade DRC 检查，将 KLayout 报告转换为
    PoLaRIS ``Violation`` 格式。

    用法::

        runner = KLayoutDRCRunner()
        result = runner.run_gds("layout.gds", SIEPIC_EBEAM_DRC_RUNSET)
        if not result.is_clean:
            for v in result.violations:
                print(f"[{v.vtype.value}] {v.message}")

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
        """
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

        dbu = layout.dbu  # DBU 单位（μm），通常 0.001
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
        self,
        layout: db.Layout,
        cell: db.Cell,
        rule: DRCRule,
        dbu: float,
    ) -> list[Violation]:
        """运行单条 DRC 规则。

        Args:
            layout: KLayout Layout 对象。
            cell: Top cell。
            rule: DRC 规则。
            dbu: Database unit（μm）。

        Returns:
            违规列表。
        """
        layer_idx = self._get_layer_index(layout, rule.layer_name)
        if layer_idx is None:
            return []  # 层不存在，跳过（非违规）

        region = db.Region(layout.begin_shapes(cell, layer_idx))
        if region.is_empty():
            return []  # 层无图形，跳过

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
<<<<<<< HEAD
        if rule.check_type == DRCCheckType.DENSITY:
            return self._check_density(region, rule, dbu, cell)
=======
>>>>>>> trae/solo-agent-pkVjID
        return []

    def _get_layer_index(self, layout: db.Layout, layer_name: str) -> int | None:
        """按层名获取 KLayout 层索引。

        Args:
            layout: KLayout Layout 对象。
            layer_name: 层名（如 ``"WG"``）。

        Returns:
            层索引，层不存在返回 None。
        """
        if layer_name not in POLARIS_GDS_LAYER_MAP:
            return None
        layer_num, datatype = get_layer_tuple(layer_name)
        info = db.LayerInfo(layer_num, datatype)
        # 如果 GDS 中已有该层，返回现有索引；否则返回 None
        for idx in layout.layer_indexes():
            existing = layout.get_info(idx)
            if existing.layer == layer_num and existing.datatype == datatype:
                return idx
        # 层定义存在但 GDS 中无该层
        _ = info  # 保留用于未来注册
        return None

    def _check_width(self, region: db.Region, rule: DRCRule, dbu: float) -> list[Violation]:
        """最小宽度检查。

        来源: KLayout Region.width_check
        https://www.klayout.org/doc-qt5/manual/drc_runsets.html
        """
        threshold_dbu = int(rule.threshold_um / dbu)
        edge_pairs = region.width_check(threshold_dbu)
        return self._edge_pairs_to_violations(edge_pairs, rule, dbu)

    def _check_space(self, region: db.Region, rule: DRCRule, dbu: float) -> list[Violation]:
        """最小间距检查。"""
        threshold_dbu = int(rule.threshold_um / dbu)
        edge_pairs = region.space_check(threshold_dbu)
        return self._edge_pairs_to_violations(edge_pairs, rule, dbu)

    def _check_notch(self, region: db.Region, rule: DRCRule, dbu: float) -> list[Violation]:
        """凹槽间距检查。"""
        threshold_dbu = int(rule.threshold_um / dbu)
        edge_pairs = region.notch_check(threshold_dbu)
        return self._edge_pairs_to_violations(edge_pairs, rule, dbu)

    def _check_enclose(
        self,
        ctx: LayoutContext,
        inner_region: db.Region,
        rule: DRCRule,
    ) -> list[Violation]:
        """包围规则检查（内层须被外层包围）。

        Args:
            ctx: KLayout 布局上下文（layout / cell / dbu）。
            inner_region: 内层 Region。
            rule: DRC 规则（enclosure_layer_name 指定外层）。
        """
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

    def _check_area(self, region: db.Region, rule: DRCRule, dbu: float) -> list[Violation]:
        """最小面积检查。

        来源: KLayout Region.with_area / area
        https://www.klayout.org/doc-qt5/manual/drc_runsets.html
        """
        min_area_dbu2 = int(rule.threshold_um / (dbu * dbu))
        violations: list[Violation] = []
        # with_area(area, inverse=False) 返回面积 < area 的图形
        small_shapes = region.with_area(min_area_dbu2, False)
        for shape in small_shapes.each():
            bbox = shape.bbox()
            area_um2 = bbox.area() * dbu * dbu
            loc = (bbox.center().x * dbu, bbox.center().y * dbu)
            violations.append(
                Violation(
                    vtype=rule.vtype,
                    severity=rule.severity,
                    message=(
                        f"{rule.name}: 图形面积 {area_um2:.4f} μm² < "
                        f"最小 {rule.threshold_um:.4f} μm²"
                    ),
                    device_name=rule.layer_name,
                    location=loc,
                )
            )
        return violations

<<<<<<< HEAD
    def _check_density(
        self,
        region: db.Region,
        rule: DRCRule,
        dbu: float,
        cell: db.Cell,
    ) -> list[Violation]:
        """层密度检查（第85轮新增，CMP 工艺要求）。

        计算层图形面积占 cell 总面积的比例，检查是否在 min/max 范围内。
        CMP 工艺要求层密度通常在 30%-70%，避免化学机械抛光不均匀。

        来源:
            - KLayout Region.area / cell.bbox
            - Banerjee, "CMOS Photonic Circuits", Springer 2024
            - SiEPIC density rules

        Args:
            region: 层 Region。
            rule: DRC 规则（threshold_um=min_density%, max_density=max_density%）。
            dbu: Database unit（μm）。
            cell: Top cell（用于计算总面积）。

        Returns:
            违规列表（密度超出范围时返回 1 条违规）。
        """
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
                    vtype=rule.vtype,
                    severity=rule.severity,
                    message=(
                        f"{rule.name}: 层密度 {density_pct:.1f}% 超出范围 "
                        f"[{min_density:.0f}%, {max_density:.0f}%]"
                    ),
                    device_name=rule.layer_name,
                    location=loc,
                )
            ]
        return []

=======
>>>>>>> trae/solo-agent-pkVjID
    def _edge_pairs_to_violations(
        self,
        edge_pairs: db.EdgePairs,
        rule: DRCRule,
        dbu: float,
    ) -> list[Violation]:
        """将 KLayout EdgePairs 转换为 PoLaRIS Violation 列表。

        Args:
            edge_pairs: KLayout EdgePairs 对象。
            rule: DRC 规则。
            dbu: Database unit（μm）。

        Returns:
            Violation 列表。
        """
        violations: list[Violation] = []
        for ep in edge_pairs.each():
            bbox = ep.bbox()
            loc = (bbox.center().x * dbu, bbox.center().y * dbu)
            violations.append(
                Violation(
                    vtype=rule.vtype,
                    severity=rule.severity,
                    message=(f"{rule.name}: {rule.description} (位置 {loc[0]:.2f}, {loc[1]:.2f})"),
                    device_name=rule.layer_name,
                    location=loc,
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

    来源: KLayout DRC API
    https://www.klayout.org/doc-qt5/manual/drc_runsets.html
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
