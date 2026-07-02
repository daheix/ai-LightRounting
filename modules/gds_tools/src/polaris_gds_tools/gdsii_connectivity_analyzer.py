"""GDSII 几何连通分量分析器（R319，Geometric Connectivity Analyzer）。

从 GDSII 文件提取几何连通分量（geometric connected components），
不依赖器件/Pin 抽象，纯基于多边形几何接触/重叠关系。

## 与 _lvs_nets.py 的区别

- _lvs_nets.py: 基于 Pin/Device 抽象的 net 提取（LVS 用途，需要器件识别）
- 本模块: 纯几何连通分量（DRC/pre-LVS 用途，仅需多边形几何）

## 核心概念

- **同层连通分量**: 同一 GDSII 层中，通过接触/重叠连接的多边形集合
  （KLayout Region.merge 后每个输出多边形即一个分量）
- **跨层连通分量**: 通过层间接续规则（如 METAL-VIA-METAL）连接的同层分量集合
  （需用户显式指定层间连接规则）
- **孤立多边形**: 不与任何其他多边形连通的单个多边形（潜在设计错误）

## 算法

1. **同层连通分量提取**:
   - 用 KLayout Region.merge() 合并接触/重叠的多边形
   - 合并后每个输出多边形 = 一个同层连通分量
   - 时间复杂度 O(n log n)（KLayout 内部使用扫描线算法）
2. **跨层连通分量提取**:
   - 用户指定层对连接规则（如 [(WG, METAL)] 表示 WG-METAL 通过重叠连通）
   - 用并查集（Union-Find）合并接触的同层分量
   - 时间复杂度 O(m α(n))，m=跨层接触对数，α=反 Ackermann 函数

## 学术依据

- KLayout Region.merge: 几何连通分量提取
  URL: https://www.klayout.org/doc-qt5/code/class_Region.html
- 并查集（Union-Find）: Tarjan, "Efficiency of a Good But Not Linear Set
  Union Algorithm", JACM 1975, DOI: 10.1145/321879.321884
- Calibre nmLVS 网络提取:
  https://www.siemens.com/en-us/products/ic/ic-custom/verification/calibre-nmlvs/
- SiEPIC EBeam PDK（光子学 LVS 标准）:
  https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- scipy.sparse.csgraph.connected_components（备选实现）:
  https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.csgraph.connected_components.html
- Shapely STRtree 空间索引（备选实现）:
  https://shapely.readthedocs.io/en/stable/strtree.html
- 光子学 LVS open/short 检测:
  https://klayout.org/downloads/master/doc-qt5/manual/lvs_compare.html

合规: R01 / R02 / R03 / R04 / R05 / R11。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from polaris_gds_tools._common import get_default_layer_map as _get_default_layer_map

logger = logging.getLogger(__name__)

__all__ = [
    "ConnectedComponent",
    "ConnectivityReport",
    "LayerConnectivityResult",
    "analyze_cross_layer_connectivity",
    "analyze_layer_connectivity",
    "generate_connectivity_report",
    "list_isolated_polygons",
]


# =============================================================================
# 内部 KLayout 导入
# =============================================================================
def _import_klayout_db():
    """导入 klayout.db，未安装 raise ImportError（R03）。"""
    try:
        import klayout.db as db
    except ImportError as e:
        raise ImportError(
            "klayout 未安装，无法执行 GDSII 几何连通分量分析。"
            "安装方式: pip install klayout。"
            f"原始错误: {e}"
        ) from e
    return db


# =============================================================================
# 数据类
# =============================================================================
@dataclass
class ConnectedComponent:
    """几何连通分量（R319）。

    表示一组通过几何接触/重叠连接的多边形。

    Attributes:
        component_id: 分量 ID（从 0 开始递增）。
        layer_name: 所属层名（如 'WG'）。
        polygon_count: 分量包含的多边形数。
        area_um2: 分量总面积（μm²）。
        bbox: 分量包围盒 (xmin, ymin, xmax, ymax)（μm）。
        polygon_indices: 分量包含的多边形索引列表（在原始多边形列表中的位置）。
    """

    component_id: int
    layer_name: str
    polygon_count: int
    area_um2: float
    bbox: tuple[float, float, float, float]
    polygon_indices: list[int] = field(default_factory=list)


@dataclass
class LayerConnectivityResult:
    """单层连通分量分析结果（R319）。

    Attributes:
        layer_name: 层名。
        total_polygons: 该层总多边形数。
        components: 连通分量列表。
        isolated_count: 孤立多边形数（多边形数为 1 的分量数）。
        largest_component_size: 最大分量含多边形数。
    """

    layer_name: str
    total_polygons: int = 0
    components: list[ConnectedComponent] = field(default_factory=list)
    isolated_count: int = 0
    largest_component_size: int = 0


@dataclass
class ConnectivityReport:
    """GDSII 几何连通分量分析报告（R319）。

    Attributes:
        file_path: GDSII 文件路径。
        top_cell_name: 顶层 cell 名。
        dbu: 数据库单位（米）。
        layer_results: 各层连通分量分析结果列表。
        total_components: 总连通分量数。
        total_isolated: 总孤立多边形数。
    """

    file_path: str
    top_cell_name: str = ""
    dbu: float = 0.0
    layer_results: list[LayerConnectivityResult] = field(default_factory=list)
    total_components: int = 0
    total_isolated: int = 0


# =============================================================================
# 同层连通分量分析
# =============================================================================
def analyze_layer_connectivity(
    gds_path: str | Path,
    layer_map: dict[tuple[int, int], str] | None = None,
    top_cell_name: str | None = None,
    layers_to_analyze: list[str] | None = None,
) -> ConnectivityReport:
    """分析 GDSII 文件各层的几何连通分量（R319）。

    对每个 GDSII 层，用 KLayout Region.merge() 合并接触/重叠的多边形，
    合并后的每个多边形即一个同层连通分量。

    Args:
        gds_path: GDSII 文件路径。
        layer_map: 层映射（None 用 SiEPIC 标准）。
        top_cell_name: 顶层 cell 名（None 用第一个 top cell）。
        layers_to_analyze: 要分析的层名列表（None 分析所有层）。

    Returns:
        ConnectivityReport 分析报告。

    Raises:
        FileNotFoundError: GDSII 文件不存在。
        ValueError: GDSII 无效 / top_cell_name 不存在。
        ImportError: klayout 未安装。

    来源:
    - KLayout Region.merge: https://www.klayout.org/doc-qt5/code/class_Region.html
    - KLayout Layout.read: https://www.klayout.org/doc-qt5/code/class_Layout.html
    """
    db = _import_klayout_db()
    path = Path(gds_path)
    if not path.exists():
        raise FileNotFoundError(f"GDSII 文件不存在: {gds_path}")
    if not path.is_file():
        raise ValueError(f"路径不是文件: {gds_path}")
    if layer_map is None:
        layer_map = _get_default_layer_map()
    ly, dbu, top_cell = _read_connectivity_layout(db, path, gds_path, top_cell_name)
    layer_results, total_components, total_isolated = _analyze_all_layers(
        db, ly, top_cell, dbu, layer_map, layers_to_analyze
    )
    return ConnectivityReport(
        file_path=str(gds_path), top_cell_name=top_cell.name, dbu=dbu,
        layer_results=layer_results, total_components=total_components,
        total_isolated=total_isolated,
    )


def _read_connectivity_layout(db, path, gds_path, top_cell_name) -> tuple:
    """读取 GDSII 并定位顶层 cell（R319 内部辅助，R03 禁止 fall-back）。

    Returns:
        (ly, dbu, top_cell)。
    """
    ly = db.Layout()
    try:
        ly.read(str(path))
    except Exception as e:
        raise RuntimeError(
            f"klayout 读取 GDSII 失败: {type(e).__name__}: {e}。禁止 fall-back（R03）。"
        ) from e
    dbu = float(ly.dbu)
    top_cell = _get_top_cell(ly, top_cell_name, gds_path)
    return ly, dbu, top_cell


def _analyze_all_layers(
    db, ly, top_cell, dbu, layer_map, layers_to_analyze
) -> tuple:
    """遍历所有层分析同层连通分量（R319 内部辅助）。

    Returns:
        (layer_results, total_components, total_isolated)。

    来源: KLayout Region.merge https://www.klayout.org/doc-qt5/code/class_Region.html
    """
    layer_results: list[LayerConnectivityResult] = []
    total_components = total_isolated = 0
    for li in ly.layer_indices():
        info = ly.get_info(li)
        gds_layer = int(info.layer)
        gds_datatype = int(info.datatype)
        layer_name = layer_map.get(
            (gds_layer, gds_datatype), f"LAYER_{gds_layer}_{gds_datatype}",
        )
        if layers_to_analyze is not None and layer_name not in layers_to_analyze:
            continue
        original_region = db.Region(top_cell.begin_shapes_rec(li))
        original_count = sum(1 for _ in original_region.each())
        if original_count == 0:
            continue
        merged_region = original_region.dup()
        merged_region.merge()
        components, isolated_count, largest_size = _build_layer_components(
            db, dbu, merged_region, original_region, layer_name
        )
        layer_results.append(LayerConnectivityResult(
            layer_name=layer_name, total_polygons=original_count,
            components=components, isolated_count=isolated_count,
            largest_component_size=largest_size,
        ))
        total_components += len(components)
        total_isolated += isolated_count
    return layer_results, total_components, total_isolated


def _build_layer_components(
    db, dbu, merged_region, original_region, layer_name
) -> tuple:
    """构建单层的连通分量列表（R319 内部辅助）。

    Returns:
        (components, isolated_count, largest_size)。
    """
    components: list[ConnectedComponent] = []
    comp_id = 0
    isolated_count = 0
    largest_size = 0
    for merged_poly in merged_region.each():
        single_region = db.Region()
        single_region.insert(merged_poly)
        area_um2 = int(single_region.area()) * dbu * dbu
        bbox_dbu = merged_poly.bbox()
        bbox = (
            float(bbox_dbu.left) * dbu, float(bbox_dbu.bottom) * dbu,
            float(bbox_dbu.right) * dbu, float(bbox_dbu.top) * dbu,
        )
        polygon_indices = _find_component_polygons(original_region, merged_poly, db, dbu)
        poly_count = len(polygon_indices) if polygon_indices else 1
        if poly_count == 1:
            isolated_count += 1
        if poly_count > largest_size:
            largest_size = poly_count
        components.append(ConnectedComponent(
            component_id=comp_id, layer_name=layer_name,
            polygon_count=poly_count, area_um2=area_um2, bbox=bbox,
            polygon_indices=polygon_indices,
        ))
        comp_id += 1
    return components, isolated_count, largest_size


def _find_component_polygons(
    original_region,
    merged_poly,
    db,
    dbu: float,
) -> list[int]:
    """找出原始 Region 中被合并到指定合并多边形的所有原始多边形索引（R319 内部函数）。

    用每个原始多边形与合并多边形做交集，若有非空交集则属于该分量。

    Args:
        original_region: 原始（未合并）Region。
        merged_poly: 合并后的单个多边形（Polygon 对象）。
        db: klayout.db 模块。
        dbu: 数据库单位（米）。

    Returns:
        原始多边形索引列表。

    来源:
    - KLayout Region & 运算: https://www.klayout.org/doc-qt5/code/class_Region.html
    """
    # 用合并多边形构造 Region
    merged_region = db.Region()
    merged_region.insert(merged_poly)

    indices: list[int] = []
    for idx, orig_poly in enumerate(original_region.each()):
        # 用交集判断原始多边形是否属于该分量
        orig_region = db.Region()
        orig_region.insert(orig_poly)
        intersection = orig_region.dup()
        intersection &= merged_region
        if not intersection.is_empty():
            indices.append(idx)
    return indices


def _get_top_cell(ly, top_cell_name: str | None, gds_path):
    """获取顶层 cell（R319 内部函数）。

    Args:
        ly: klayout.db.Layout 对象。
        top_cell_name: 指定的顶层 cell 名（None 用第一个）。
        gds_path: GDSII 文件路径（用于错误信息）。

    Returns:
        klayout.db.Cell 顶层 cell。

    Raises:
        ValueError: top_cell_name 不存在或 GDSII 无顶层 cell。
    """
    if top_cell_name is not None:
        # KLayout Layout.cell(name) 接受 str 或 int
        top_cell = ly.cell(top_cell_name)
        if top_cell is None:
            available = [ly.cell(ci).name for ci in ly.each_top_cell()]
            raise ValueError(
                f"top_cell_name '{top_cell_name}' 不存在。"
                f"可用顶层 cells: {available}"
            )
        return top_cell

    top_cells = [ly.cell(ci) for ci in ly.each_top_cell()]
    if not top_cells:
        raise ValueError(
            f"GDSII 文件 {gds_path} 无顶层 cell，文件可能为空"
        )
    return top_cells[0]


# =============================================================================
# 跨层连通分量分析
# =============================================================================
def analyze_cross_layer_connectivity(
    gds_path: str | Path,
    layer_pairs: list[tuple[str, str]],
    layer_map: dict[tuple[int, int], str] | None = None,
    top_cell_name: str | None = None,
) -> dict[str, list[set[str]]]:
    """分析 GDSII 文件跨层连通分量（R319）。

    用户指定层对连接规则（如 [('WG', 'METAL')] 表示 WG-METAL 通过重叠连通），
    用并查集合并接触的同层分量。

    Args:
        gds_path: GDSII 文件路径。
        layer_pairs: 层对连接规则列表（每对表示两层通过重叠连通）。
        layer_map: 层映射（None 用 SiEPIC 标准）。
        top_cell_name: 顶层 cell 名。

    Returns:
        跨层连通分量字典 {layer_name: [set_of_component_ids]}。
        每个集合表示一组跨层连通的同层分量 ID。

    Raises:
        FileNotFoundError: GDSII 文件不存在。
        ValueError: GDSII 无效 / layer_pair 中层名不存在。
        ImportError: klayout 未安装。

    来源:
    - 并查集 Union-Find: Tarjan JACM 1975, DOI: 10.1145/321879.321884
    """
    if not layer_pairs:
        raise ValueError("layer_pairs 不能为空")
    db = _import_klayout_db()
    path = Path(gds_path)
    if not path.exists():
        raise FileNotFoundError(f"GDSII 文件不存在: {gds_path}")
    if not path.is_file():
        raise ValueError(f"路径不是文件: {gds_path}")
    if layer_map is None:
        layer_map = _get_default_layer_map()
    report, available_layers = _validate_and_get_layer_report(
        gds_path, layer_pairs, layer_map, top_cell_name
    )
    parent, rank, find, union = _init_cross_layer_union_find(report)
    ly, _, top_cell = _read_connectivity_layout(db, path, gds_path, top_cell_name)
    layer_to_indices = _build_layer_to_indices(ly, layer_map, available_layers)
    _find_cross_layer_touching(
        db, top_cell, layer_to_indices, layer_pairs, report, union
    )
    return _group_cross_layer_results(report, parent, find)


def _validate_and_get_layer_report(gds_path, layer_pairs, layer_map, top_cell_name) -> tuple:
    """校验层对并获取同层连通报告（R319 内部辅助，R03 禁止 fall-back）。

    Returns:
        (report, available_layers)。

    Raises:
        ValueError: 层对中层名不存在。
    """
    layer_names_in_pairs = set()
    for a, b in layer_pairs:
        layer_names_in_pairs.add(a)
        layer_names_in_pairs.add(b)
    report = analyze_layer_connectivity(
        gds_path, layer_map=layer_map, top_cell_name=top_cell_name,
        layers_to_analyze=list(layer_names_in_pairs),
    )
    available_layers = {r.layer_name for r in report.layer_results}
    for a, b in layer_pairs:
        for name in (a, b):
            if name not in available_layers:
                raise ValueError(
                    f"层对 ({a}, {b}) 中的层 '{name}' 不在 GDSII 文件中。"
                    f"可用层: {available_layers}"
                )
    return report, available_layers


def _init_cross_layer_union_find(report) -> tuple:
    """初始化并查集（R319 内部辅助）。

    来源: Tarjan JACM 1975, DOI: 10.1145/321879.321884（路径压缩+按秩合并）。

    Returns:
        (parent, rank, find_func, union_func)。
    """
    parent: dict[tuple[str, int], tuple[str, int]] = {}
    rank: dict[tuple[str, int], int] = {}
    for layer_result in report.layer_results:
        for comp in layer_result.components:
            node = (layer_result.layer_name, comp.component_id)
            parent[node] = node
            rank[node] = 0

    def find(x) -> tuple[str, int]:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x, y) -> None:
        rx, ry = find(x), find(y)
        if rx == ry:
            return
        if rank[rx] < rank[ry]:
            rx, ry = ry, rx
        parent[ry] = rx
        if rank[rx] == rank[ry]:
            rank[rx] += 1

    return parent, rank, find, union


def _build_layer_to_indices(ly, layer_map, available_layers) -> dict[str, int]:
    """构建层名→layer_index 映射（R319 内部辅助）。"""
    layer_to_indices: dict[str, int] = {}
    for li in ly.layer_indices():
        info = ly.get_info(li)
        layer_name = layer_map.get(
            (int(info.layer), int(info.datatype)),
            f"LAYER_{int(info.layer)}_{int(info.datatype)}",
        )
        if layer_name in available_layers:
            layer_to_indices[layer_name] = li
    return layer_to_indices


def _find_cross_layer_touching(db, top_cell, layer_to_indices, layer_pairs, report, union) -> None:
    """对每个层对找出接触的同层分量对并 union（R319 内部辅助）。

    来源: KLayout Region & 运算 https://www.klayout.org/doc-qt5/code/class_Region.html
    """
    for layer_a, layer_b in layer_pairs:
        li_a = layer_to_indices[layer_a]
        li_b = layer_to_indices[layer_b]
        region_a = db.Region(top_cell.begin_shapes_rec(li_a))
        region_b = db.Region(top_cell.begin_shapes_rec(li_b))
        result_a = report.layer_results[[r.layer_name for r in report.layer_results].index(layer_a)]
        result_b = report.layer_results[[r.layer_name for r in report.layer_results].index(layer_b)]
        polys_a = list(region_a.each())
        polys_b = list(region_b.each())
        for comp_a in result_a.components:
            region_comp_a = db.Region()
            for idx in comp_a.polygon_indices:
                if idx < len(polys_a):
                    region_comp_a.insert(polys_a[idx])
            for comp_b in result_b.components:
                region_comp_b = db.Region()
                for idx in comp_b.polygon_indices:
                    if idx < len(polys_b):
                        region_comp_b.insert(polys_b[idx])
                intersection = region_comp_a.dup()
                intersection &= region_comp_b
                if not intersection.is_empty():
                    union((layer_a, comp_a.component_id), (layer_b, comp_b.component_id))


def _group_cross_layer_results(report, parent, find) -> dict[str, list[set[int]]]:
    """按并查集 find 结果分组并转换为结果字典（R319 内部辅助）。"""
    groups: dict[tuple[str, int], list[tuple[str, int]]] = {}
    for node in parent:
        root = find(node)
        groups.setdefault(root, []).append(node)
    result: dict[str, list[set[int]]] = {r.layer_name: [] for r in report.layer_results}
    for group_nodes in groups.values():
        by_layer: dict[str, set[int]] = {}
        for layer_name, comp_id in group_nodes:
            by_layer.setdefault(layer_name, set()).add(comp_id)
        for layer_name, comp_ids in by_layer.items():
            result[layer_name].append(comp_ids)
    return result


# =============================================================================
# 孤立多边形列表
# =============================================================================
def list_isolated_polygons(
    gds_path: str | Path,
    layer_map: dict[tuple[int, int], str] | None = None,
    top_cell_name: str | None = None,
    layers_to_analyze: list[str] | None = None,
) -> list[ConnectedComponent]:
    """列出 GDSII 文件中的孤立多边形（R319）。

    孤立多边形是不与任何其他多边形连通的单个多边形（潜在设计错误）。

    Args:
        gds_path: GDSII 文件路径。
        layer_map: 层映射（None 用 SiEPIC 标准）。
        top_cell_name: 顶层 cell 名。
        layers_to_analyze: 要分析的层名列表（None 分析所有层）。

    Returns:
        孤立多边形分量列表。

    Raises:
        FileNotFoundError: GDSII 文件不存在。
        ValueError: GDSII 无效。
        ImportError: klayout 未安装。
    """
    report = analyze_layer_connectivity(
        gds_path, layer_map=layer_map, top_cell_name=top_cell_name,
        layers_to_analyze=layers_to_analyze,
    )
    isolated: list[ConnectedComponent] = []
    for layer_result in report.layer_results:
        for comp in layer_result.components:
            if comp.polygon_count == 1:
                isolated.append(comp)
    return isolated


# =============================================================================
# 报告生成
# =============================================================================
def generate_connectivity_report(
    gds_path: str | Path,
    layer_map: dict[tuple[int, int], str] | None = None,
    top_cell_name: str | None = None,
    output_format: str = "text",
) -> str:
    """生成 GDSII 几何连通分量分析报告（R319）。

    Args:
        gds_path: GDSII 文件路径。
        layer_map: 层映射（None 用 SiEPIC 标准）。
        top_cell_name: 顶层 cell 名。
        output_format: 输出格式（'text' / 'markdown'）。

    Returns:
        报告字符串。

    Raises:
        FileNotFoundError: GDSII 文件不存在。
        ValueError: 不支持的格式 / GDSII 无效。
        ImportError: klayout 未安装。

    来源:
    - CommonMark: https://spec.commonmark.org/
    """
    report = analyze_layer_connectivity(
        gds_path, layer_map=layer_map, top_cell_name=top_cell_name,
    )
    fmt = output_format.lower()
    if fmt == "text":
        return _render_text_report(report)
    if fmt == "markdown":
        return _render_markdown_report(report)
    raise ValueError(
        f"不支持的 output_format: {output_format}。"
        f"支持: text / markdown。"
    )


def _render_text_report(report: ConnectivityReport) -> str:
    """渲染纯文本报告。"""
    lines: list[str] = []
    lines.append("=" * 60)
    lines.append("GDSII 几何连通分量分析报告")
    lines.append("=" * 60)
    lines.append(f"文件: {report.file_path}")
    lines.append(f"顶层 cell: {report.top_cell_name}")
    lines.append(f"dbu: {report.dbu} m")
    lines.append(f"总连通分量数: {report.total_components}")
    lines.append(f"总孤立多边形数: {report.total_isolated}")
    lines.append("")
    lines.append("-" * 60)
    lines.append("各层详情:")
    lines.append("-" * 60)
    for lr in report.layer_results:
        lines.append(
            f"  层 {lr.layer_name}: "
            f"多边形 {lr.total_polygons}, "
            f"分量 {len(lr.components)}, "
            f"孤立 {lr.isolated_count}, "
            f"最大分量 {lr.largest_component_size} 多边形"
        )
        for comp in lr.components:
            x_min, y_min, x_max, y_max = comp.bbox
            lines.append(
                f"    分量 #{comp.component_id}: "
                f"{comp.polygon_count} 多边形, "
                f"面积 {comp.area_um2:.4f} μm², "
                f"包围盒 [{x_min:.2f}, {y_min:.2f}]-"
                f"[{x_max:.2f}, {y_max:.2f}]"
            )
    lines.append("=" * 60)
    return "\n".join(lines)


def _render_markdown_report(report: ConnectivityReport) -> str:
    """渲染 Markdown 报告。"""
    lines: list[str] = []
    lines.append("# GDSII 几何连通分量分析报告")
    lines.append("")
    lines.append(f"**文件**: `{report.file_path}`")
    lines.append(f"**顶层 cell**: {report.top_cell_name}")
    lines.append(f"**dbu**: {report.dbu} m")
    lines.append(f"**总连通分量数**: {report.total_components}")
    lines.append(f"**总孤立多边形数**: {report.total_isolated}")
    lines.append("")
    lines.append("## 各层详情")
    lines.append("")
    lines.append(
        "| 层名 | 总多边形 | 连通分量 | 孤立多边形 | 最大分量 |"
    )
    lines.append(
        "|------|----------|----------|------------|----------|"
    )
    for lr in report.layer_results:
        lines.append(
            f"| {lr.layer_name} | {lr.total_polygons} | "
            f"{len(lr.components)} | {lr.isolated_count} | "
            f"{lr.largest_component_size} |"
        )
    lines.append("")
    lines.append("## 分量详情")
    lines.append("")
    for lr in report.layer_results:
        lines.append(f"### 层 {lr.layer_name}")
        lines.append("")
        lines.append(
            "| 分量 ID | 多边形数 | 面积(μm²) | 包围盒 |"
        )
        lines.append(
            "|---------|----------|-----------|--------|"
        )
        for comp in lr.components:
            x_min, y_min, x_max, y_max = comp.bbox
            bbox = (
                f"[{x_min:.1f},{y_min:.1f}]-"
                f"[{x_max:.1f},{y_max:.1f}]"
            )
            lines.append(
                f"| {comp.component_id} | {comp.polygon_count} | "
                f"{comp.area_um2:.4f} | {bbox} |"
            )
        lines.append("")
    return "\n".join(lines)
