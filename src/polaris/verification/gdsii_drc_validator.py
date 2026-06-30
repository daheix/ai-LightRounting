"""GDSII 文件直接 DRC 验证工具（R312）。

整合 R301（GDSII 读取）与 R307（KLayout DRC 桥接），提供端到端的
GDSII 文件 DRC 验证能力：直接读取 GDSII → 按层提取多边形 → KLayout DRC 检查。

R312 实现:
1. extract_polygons_from_gdsii(gds_path, layer_map) -> dict[str, list[np.ndarray]]
   从 GDSII 文件按层提取多边形
2. run_drc_on_gdsii(gds_path, rules, config, layer_map) -> list[KLayoutDRCResult]
   端到端 GDSII → DRC 检查
3. drc_summary_from_gdsii(gds_path, rules, config) -> dict
   生成 DRC 检查汇总报告

R03 合规:
- 文件不存在 raise FileNotFoundError
- GDSII 读取失败 raise RuntimeError
- 文件无顶层 cell raise ValueError
- DRC 规则引用未定义层 raise KeyError

R02 学术诚信:
- 所有 KLayout API 用法附带官方文档 URL
- SiEPIC 标准层映射附带 SiEPIC PDK URL

来源:
- KLayout Layout.read: https://www.klayout.org/doc-qt5/code/class_Layout.html
- KLayout LayerInfo: https://www.klayout.org/doc-qt5/code/class_LayerInfo.html
- KLayout Region: https://www.klayout.org/doc-qt5/code/class_Region.html
- KLayout Cell.shapes: https://www.klayout.org/doc-qt5/code/class_Cell.html
- GDSII 格式: https://en.wikipedia.org/wiki/GDS_File
- SiEPIC EBeam PDK 层映射: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- gdsfactory write_gds: https://gdsfactory.github.io/gdsfactory/api.html
- KLayout DRC Reference: https://www.klayout.de/doc-qt5/manual/drc.html
- OpenROAD DRC Engine: https://openroad.readthedocs.io/en/latest/main/src/drt/README.html

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R05 Bug 必修。
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import numpy as np

from polaris.verification._drc_rules import CurvilinearDRCRule
from polaris.verification.klayout_drc_bridge import (
    KLayoutDRCConfig,
    KLayoutDRCResult,
    klayout_region_to_polygons,
    run_klayout_drc,
)

logger = logging.getLogger(__name__)

__all__ = [
    "drc_summary_from_gdsii",
    "extract_polygons_from_gdsii",
    "run_drc_on_gdsii",
]


# =============================================================================
# GDSII 多边形提取
# =============================================================================
def _import_klayout_db():
    """导入 klayout.db，未安装 raise ImportError（R03）。"""
    try:
        import klayout.db as db
    except ImportError as e:
        raise ImportError(
            "klayout 未安装，无法执行 GDSII DRC 验证。"
            "安装方式: pip install klayout。"
            f"原始错误: {e}"
        ) from e
    return db


def _get_default_layer_map() -> dict[tuple[int, int], str]:
    """获取默认 SiEPIC 层映射（R312）。"""
    # SiEPIC EBeam PDK 13 层标准映射
    # 来源: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
    return {
        (1, 0): "WG",
        (2, 0): "SLAB150",
        (3, 0): "SLAB90",
        (4, 0): "SiN",
        (5, 0): "METAL",
        (6, 0): "HEATER",
        (10, 0): "TEXT",
        (11, 0): "LABEL",
        (68, 0): "DEVREC",
        (69, 0): "PIN",
        (70, 0): "PORT",
        (80, 0): "FLOORPLAN",
        (99, 0): "PORT_GEOM",
    }


def extract_polygons_from_gdsii(
    gds_path: str | Path,
    layer_map: dict[tuple[int, int], str] | None = None,
    top_cell_name: str | None = None,
) -> dict[str, list[np.ndarray]]:
    """从 GDSII 文件按层提取多边形（R312）。

    使用 KLayout 读取 GDSII 文件，递归展平所有子 cell 的多边形，
    按 layer_map 映射到 PoLaRIS 层名。

    Args:
        gds_path: GDSII 文件路径。
        layer_map: {(gds_layer, gds_datatype): polaris_name} 映射。
            None 用 SiEPIC 标准层映射。
        top_cell_name: 顶层 cell 名（None 用第一个 top cell）。

    Returns:
        {layer_name: [polygon, ...]} 字典，每个多边形为 (N, 2) 浮点数组（μm）。

    Raises:
        FileNotFoundError: 文件不存在。
        ValueError: 文件无效或 top_cell_name 不存在。
        RuntimeError: klayout 读取失败。
        ImportError: klayout 未安装。

    来源:
    - KLayout Layout.read: https://www.klayout.org/doc-qt5/code/class_Layout.html
    - KLayout Region: https://www.klayout.org/doc-qt5/code/class_Region.html
    """
    db = _import_klayout_db()
    path = Path(gds_path)
    if not path.exists():
        raise FileNotFoundError(f"GDSII 文件不存在: {gds_path}")
    if not path.is_file():
        raise ValueError(f"路径不是文件: {gds_path}")

    if layer_map is None:
        layer_map = _get_default_layer_map()

    ly = db.Layout()
    try:
        ly.read(str(path))
    except Exception as e:
        raise RuntimeError(
            f"klayout 读取 GDSII 失败: {type(e).__name__}: {e}。"
            f"禁止 fall-back（R03）。"
        ) from e

    dbu = float(ly.dbu)

    # 选择顶层 cell
    if top_cell_name is not None:
        top_cell = ly.cell(top_cell_name)
        if top_cell is None:
            available = [ly.cell(ci).name for ci in ly.each_top_cell()]
            raise ValueError(
                f"top_cell_name '{top_cell_name}' 不存在。"
                f"可用顶层 cells: {available}"
            )
    else:
        top_cells = [ly.cell(ci) for ci in ly.each_top_cell()]
        if not top_cells:
            raise ValueError(
                f"GDSII 文件 {gds_path} 无顶层 cell，文件可能为空"
            )
        top_cell = top_cells[0]

    # 按层提取多边形（递归展平所有子 cell）
    # KLayout 0.30.9 API: Cell.begin_shapes_rec(layer_index) 返回
    # RecursiveShapeIterator，遍历该层所有形状（含子 cell）。
    # db.Region(iterator) 用迭代器构造 Region，自动合并重叠/接触的多边形。
    # 来源: https://www.klayout.org/doc-qt5/code/class_Cell.html#method20
    result: dict[str, list[np.ndarray]] = {}
    for li in ly.layer_indices():
        info = ly.get_info(li)
        gds_layer = int(info.layer)
        gds_datatype = int(info.datatype)
        polaris_name = layer_map.get(
            (gds_layer, gds_datatype),
            f"LAYER_{gds_layer}_{gds_datatype}",
        )
        # 用 Region 收集所有多边形（自动合并重叠/接触的多边形）
        region = db.Region(top_cell.begin_shapes_rec(li))
        # 转换为 PoLaRIS 多边形（μm）
        polygons: list[np.ndarray] = []
        # KLayout 0.30.9: SimplePolygon.each_point() 直接返回 Point 对象
        for klayout_poly in region.each():
            pts = list(klayout_poly.to_simple_polygon().each_point())
            coords = [(float(p.x) * dbu, float(p.y) * dbu) for p in pts]
            if len(coords) >= 3:
                polygons.append(np.array(coords, dtype=float))
        if polygons:
            result[polaris_name] = polygons
    return result


# =============================================================================
# GDSII DRC 端到端验证
# =============================================================================
def run_drc_on_gdsii(
    gds_path: str | Path,
    rules: list[CurvilinearDRCRule],
    config: KLayoutDRCConfig | None = None,
    layer_map: dict[tuple[int, int], str] | None = None,
    top_cell_name: str | None = None,
) -> list[KLayoutDRCResult]:
    """对 GDSII 文件执行 DRC 检查（R312）。

    端到端流程: GDSII 文件 → 按层提取多边形 → KLayout DRC 检查。

    Args:
        gds_path: GDSII 文件路径。
        rules: DRC 规则列表。
        config: KLayout DRC 配置（None 用默认）。
        layer_map: 层映射（None 用 SiEPIC 标准）。
        top_cell_name: 顶层 cell 名（None 用第一个 top cell）。

    Returns:
        各规则的检查结果列表。

    Raises:
        FileNotFoundError: GDSII 文件不存在。
        ValueError: GDSII 无效 / 规则引用未定义层。
        ImportError: klayout 未安装。

    来源:
    - KLayout DRC Reference: https://www.klayout.de/doc-qt5/manual/drc.html
    - run_klayout_drc: polaris.verification.klayout_drc_bridge.run_klayout_drc
    """
    layer_polygons = extract_polygons_from_gdsii(
        gds_path, layer_map=layer_map, top_cell_name=top_cell_name
    )
    cfg = config or KLayoutDRCConfig()
    return run_klayout_drc(layer_polygons, rules, cfg)


# =============================================================================
# DRC 汇总报告
# =============================================================================
def drc_summary_from_gdsii(
    gds_path: str | Path,
    rules: list[CurvilinearDRCRule],
    config: KLayoutDRCConfig | None = None,
    layer_map: dict[tuple[int, int], str] | None = None,
    top_cell_name: str | None = None,
) -> dict[str, Any]:
    """生成 GDSII 文件的 DRC 汇总报告（R312）。

    Args:
        gds_path: GDSII 文件路径。
        rules: DRC 规则列表。
        config: KLayout DRC 配置。
        layer_map: 层映射。
        top_cell_name: 顶层 cell 名。

    Returns:
        汇总报告字典:
        - file_path: GDSII 文件路径
        - total_rules: 规则总数
        - total_violations: 违规总数
        - errors: 错误数
        - warnings: 警告数
        - passed: 是否通过（errors == 0）
        - violations_by_layer: 按层统计违规
        - violations_by_rule: 按规则统计违规
        - layers_extracted: 提取的层列表
        - polygon_count_by_layer: 各层多边形数

    Raises:
        同 run_drc_on_gdsii。

    来源:
    - KLayout DRC Reference: https://www.klayout.de/doc-qt5/manual/drc.html
    """
    results = run_drc_on_gdsii(
        gds_path, rules, config=config,
        layer_map=layer_map, top_cell_name=top_cell_name,
    )
    layer_polygons = extract_polygons_from_gdsii(
        gds_path, layer_map=layer_map, top_cell_name=top_cell_name
    )
    total_violations = sum(r.violation_count for r in results)
    errors = sum(r.violation_count for r in results if r.severity == "error")
    warnings = sum(r.violation_count for r in results if r.severity == "warning")
    violations_by_layer: dict[str, int] = {}
    violations_by_rule: dict[str, int] = {}
    for r in results:
        violations_by_layer[r.layer_name] = (
            violations_by_layer.get(r.layer_name, 0) + r.violation_count
        )
        violations_by_rule[r.rule_id] = r.violation_count
    polygon_count_by_layer: dict[str, int] = {
        layer: len(polys) for layer, polys in layer_polygons.items()
    }
    return {
        "file_path": str(gds_path),
        "total_rules": len(rules),
        "total_violations": total_violations,
        "errors": errors,
        "warnings": warnings,
        "passed": errors == 0,
        "violations_by_layer": violations_by_layer,
        "violations_by_rule": violations_by_rule,
        "layers_extracted": sorted(layer_polygons.keys()),
        "polygon_count_by_layer": polygon_count_by_layer,
    }
