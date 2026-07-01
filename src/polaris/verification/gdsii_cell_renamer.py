"""GDSII 器件重命名工具（R339，Cell Renamer）。

批量重命名 GDSII 文件中的 cell，用于 PDK 命名规范化、版本升级、
前缀/后缀添加等场景。

## 核心概念

- **Cell 重命名**: 修改 cell 的名字，KLayout 自动更新所有实例引用
- **典型用途**:
  - PDK 命名规范化: 把 mzi_v1 重命名为 MZI_1550nm
  - 版本升级: 把 bend_old 重命名为 bend_v2
  - 前缀/后缀添加: 给所有 cell 加项目前缀
  - 命名冲突解决: 把冲突的 cell 重命名为唯一名

## KLayout 0.30.9 API 关键事实（R339 冒烟测试实测）

- `Layout.rename_cell(cell_index, new_name)`: 重命名 cell
  - cell_index: int
  - new_name: str
  - 重命名后所有实例引用自动更新
  - 重命名持久化到 GDSII 文件
- `Layout.cell(name)`: 按名取 Cell（不存在返回 None）
- `Cell.cell_index()`: 返回 int cell index
- `Cell.name`: cell 名（str，属性）
- `Layout.each_cell()`: 返回 Cell 对象迭代器
- `Layout.write(path)`: 写出整个 layout

## 算法

1. 读取 GDSII
2. 验证 rename_map:
   - 每个 old_name 必须存在
   - 每个 new_name 不能与现有 cell 名冲突（除非 new_name == old_name）
   - 检测循环重命名（A→B, B→A）
3. 对每个 (old_name → new_name) 调用 rename_cell
4. 写出 GDSII

## 循环重命名检测

如果 rename_map 中存在 A→B 且 B→A，会导致冲突。
检测方法：构建有向图，检测是否有循环。

## 学术依据

- KLayout Layout class:
  https://www.klayout.org/doc-qt5/code/class_Layout.html
- KLayout Cell class:
  https://www.klayout.org/doc-qt5/code/class_Cell.html
- KLayout Database API:
  https://klayout.org/downloads/master/doc-qt5/programming/database_api.html
- GDSII 格式: https://en.wikipedia.org/wiki/GDS_File
- SiEPIC EBeam PDK 命名规范:
  https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- Calibre LVS 命名匹配:
  https://www.mentor.com/products/ic_nanometer_design/calibre-lvs
- KLayout Cell rename:
  https://www.klayout.org/doc-qt5/code/class_Layout.html#method915
- gdsfactory Component rename:
  https://gdsfactory.github.io/gdsfactory/

合规: R01 / R02 / R03 / R04 / R05 / R11。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

__all__ = [
    "RenameRecord",
    "RenameReport",
    "rename_cells",
    "generate_rename_report",
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
            "klayout 未安装，无法执行 GDSII 器件重命名。"
            "安装方式: pip install klayout。"
            f"原始错误: {e}"
        ) from e
    return db


# =============================================================================
# 数据类
# =============================================================================
@dataclass
class RenameRecord:
    """单次重命名记录（R339）。

    Attributes:
        old_name: 旧 cell 名。
        new_name: 新 cell 名。
    """

    old_name: str
    new_name: str


@dataclass
class RenameReport:
    """GDSII 器件重命名报告（R339）。

    Attributes:
        input_path: 输入 GDSII 文件路径。
        output_path: 输出 GDSII 文件路径。
        renames_requested: 用户请求的重命名映射（old → new）。
        renames_applied: 实际应用的重命名记录列表。
        total_renamed: 总重命名数。
        original_cell_names: 重命名前的 cell 名列表。
        final_cell_names: 重命名后的 cell 名列表。
        dbu: 数据库单位（μm）。
    """

    input_path: str = ""
    output_path: str = ""
    renames_requested: dict[str, str] = field(default_factory=dict)
    renames_applied: list[RenameRecord] = field(default_factory=list)
    total_renamed: int = 0
    original_cell_names: list[str] = field(default_factory=list)
    final_cell_names: list[str] = field(default_factory=list)
    dbu: float = 0.0


# =============================================================================
# 内部辅助函数
# =============================================================================
def _detect_cycle(rename_map: dict[str, str]) -> list[str] | None:
    """检测重命名映射中的循环（R339 内部函数）。

    用 DFS 检测有向图中的循环。例如 {A→B, B→A} 会检测到循环 [A, B, A]。

    Args:
        rename_map: 重命名映射 {old_name: new_name}。

    Returns:
        循环路径列表（如 [A, B, A]），无循环返回 None。

    来源:
    - DFS 循环检测: Cormen et al., "Introduction to Algorithms", MIT Press 2009
    """
    # 构建图：只考虑 new_name 也是 rename_map 的 key 的情况
    visited: set[str] = set()
    rec_stack: set[str] = set()
    path: list[str] = []

    def dfs(node: str) -> list[str] | None:
        if node in rec_stack:
            # 找到循环，返回循环路径
            cycle_start = path.index(node)
            return path[cycle_start:] + [node]
        if node in visited:
            return None
        visited.add(node)
        rec_stack.add(node)
        path.append(node)
        # 如果 node 的 new_name 也是 rename_map 的 key，继续 DFS
        if node in rename_map:
            next_node = rename_map[node]
            result = dfs(next_node)
            if result is not None:
                return result
        path.pop()
        rec_stack.remove(node)
        return None

    for old_name in rename_map:
        if old_name not in visited:
            result = dfs(old_name)
            if result is not None:
                return result
    return None


# =============================================================================
# 重命名主入口
# =============================================================================
def rename_cells(
    input_path: str | Path,
    output_path: str | Path,
    rename_map: dict[str, str],
) -> RenameReport:
    """批量重命名 GDSII 中的 cell（R339）。

    用 KLayout `Layout.rename_cell` 重命名 cell，所有实例引用自动更新。

    Args:
        input_path: 输入 GDSII 文件路径。
        output_path: 输出 GDSII 文件路径。
        rename_map: 重命名映射 {old_name: new_name}。
            key: 旧 cell 名（要被重命名的）。
            value: 新 cell 名（重命名为）。

    Returns:
        RenameReport 重命名报告。

    Raises:
        FileNotFoundError: 输入文件不存在。
        ValueError: 文件无效 / rename_map 为空 / old_name 不存在 /
            new_name 与现有 cell 冲突 / 检测到循环重命名 / 无 cell。
        ImportError: klayout 未安装。
        RuntimeError: 读取或写出失败。

    来源:
    - KLayout Layout.rename_cell:
      https://www.klayout.org/doc-qt5/code/class_Layout.html
    """
    db = _import_klayout_db()
    in_path, out_path = _validate_rename_params(input_path, output_path, rename_map)
    ly, dbu, original_cell_names = _read_rename_layout(db, in_path, input_path)
    existing_names = set(original_cell_names)
    cycle_check_map = _validate_rename_map_entries(
        rename_map, existing_names, original_cell_names
    )
    _check_rename_cycle(cycle_check_map)
    _check_new_name_conflicts(cycle_check_map, existing_names)
    renames_applied = _execute_cell_renames(ly, cycle_check_map)
    final_cell_names = sorted(c.name for c in ly.each_cell())
    _write_renamed_gdsii(ly, out_path, output_path)
    logger.info(
        "GDSII 器件重命名: %s → %s (renames=%d, cells_before=%d, cells_after=%d)",
        in_path, out_path, len(renames_applied),
        len(original_cell_names), len(final_cell_names),
    )
    return RenameReport(
        input_path=str(input_path),
        output_path=str(output_path),
        renames_requested=dict(rename_map),
        renames_applied=renames_applied,
        total_renamed=len(renames_applied),
        original_cell_names=original_cell_names,
        final_cell_names=final_cell_names,
        dbu=dbu,
    )


def _validate_rename_params(input_path, output_path, rename_map) -> tuple:
    """校验 rename_cells 入参（R339 内部辅助，R03 禁止 fall-back）。

    Returns:
        (in_path, out_path) Path 对象。
    """
    in_path = Path(input_path)
    out_path = Path(output_path)
    if not in_path.exists():
        raise FileNotFoundError(f"输入 GDSII 文件不存在: {input_path}")
    if not in_path.is_file():
        raise ValueError(f"输入路径不是文件: {input_path}")
    if not rename_map:
        raise ValueError(
            "rename_map 不能为空。禁止 fall-back（R03）。"
        )
    return in_path, out_path


def _read_rename_layout(db, in_path, input_path) -> tuple:
    """读取 GDSII 文件并返回 layout/dbu/cell 名（R339 内部辅助，R03 禁止 fall-back）。

    Returns:
        (ly, dbu, original_cell_names)。

    来源: KLayout Layout.read https://www.klayout.org/doc-qt5/code/class_Layout.html
    """
    ly = db.Layout()
    try:
        ly.read(str(in_path))
    except Exception as e:
        raise RuntimeError(
            f"klayout 读取文件失败: {type(e).__name__}: {e}。"
            f"禁止 fall-back（R03）。"
        ) from e
    dbu = float(ly.dbu)
    original_cell_names = sorted(c.name for c in ly.each_cell())
    return ly, dbu, original_cell_names


def _validate_rename_map_entries(
    rename_map, existing_names, original_cell_names,
) -> dict:
    """校验 rename_map 键值并构建 cycle_check_map（R339 内部辅助，R03 禁止 fall-back）。

    Returns:
        cycle_check_map（仅含 old != new 且 old 存在的条目）。
    """
    for old_name, new_name in rename_map.items():
        if not isinstance(old_name, str) or not old_name:
            raise ValueError(
                f"rename_map 的 key 必须是非空字符串，得到 {old_name!r}。"
                f"禁止 fall-back（R03）。"
            )
        if not isinstance(new_name, str) or not new_name:
            raise ValueError(
                f"rename_map 的 value 必须是非空字符串，得到 {new_name!r}。"
                f"禁止 fall-back（R03）。"
            )
        if old_name == new_name:
            continue
        if old_name not in existing_names:
            raise ValueError(
                f"rename_map 中旧 cell 名 '{old_name}' 不存在。"
                f"可用 cell: {original_cell_names[:10]}"
                f"{'...' if len(original_cell_names) > 10 else ''}。"
                f"禁止 fall-back（R03）。"
            )
    return {
        old: new for old, new in rename_map.items()
        if old != new and old in existing_names
    }


def _check_rename_cycle(cycle_check_map) -> None:
    """检测循环重命名（R339 内部辅助，R03 禁止 fall-back）。

    来源: DFS 循环检测 Cormen et al., "Introduction to Algorithms", MIT Press 2009
    """
    cycle = _detect_cycle(cycle_check_map)
    if cycle is not None:
        raise ValueError(
            f"检测到循环重命名: {' → '.join(cycle)}。"
            f"请确保重命名映射不形成循环。"
            f"禁止 fall-back（R03）。"
        )


def _check_new_name_conflicts(cycle_check_map, existing_names) -> None:
    """检查 new_name 冲突（R339 内部辅助，R03 禁止 fall-back）。

    new_name 不能与"不被重命名的现有 cell"冲突，但可以与"将被重命名的现有 cell"
    冲突（链式重命名）。例如 {A→B, B→C} 中 A→B 的 B 是现有 cell，但 B 会被重命名
    为 C，所以 OK；但 {A→B} 中 B 是现有 cell 且不被重命名，则冲突。
    """
    names_being_renamed = set(cycle_check_map.keys())
    for old_name, new_name in cycle_check_map.items():
        if new_name in existing_names and new_name not in names_being_renamed:
            raise ValueError(
                f"重命名 '{old_name}' → '{new_name}' 冲突："
                f"'{new_name}' 已存在且不被重命名。"
                f"禁止 fall-back（R03）。"
            )


def _execute_cell_renames(ly, cycle_check_map) -> list:
    """按拓扑顺序执行重命名并返回应用记录（R339 内部辅助）。

    链式重命名（A→B, B→C）需拓扑顺序：先 B→C，再 A→B，避免 A→B 时 B 已存在的冲突。
    KLayout rename_cell 重命名后旧名查不到，新名可查。

    Returns:
        renames_applied: list[RenameRecord]。
    """
    ordered_renames = _topological_sort_renames(cycle_check_map)
    renames_applied: list[RenameRecord] = []
    for old_name in ordered_renames:
        new_name = cycle_check_map[old_name]
        cell = ly.cell(old_name)
        if cell is None:
            # 可能已被链式重命名让出，跳过
            continue
        ci = int(cell.cell_index())
        ly.rename_cell(ci, new_name)
        renames_applied.append(RenameRecord(old_name=old_name, new_name=new_name))
    return renames_applied


def _write_renamed_gdsii(ly, out_path, output_path) -> None:
    """写出重命名后的 GDSII（R339 内部辅助，R03 禁止 fall-back）。

    来源: KLayout Layout.write https://www.klayout.org/doc-qt5/code/class_Layout.html
    """
    try:
        ly.write(str(out_path))
    except Exception as e:
        raise RuntimeError(
            f"klayout 写出文件失败: {type(e).__name__}: {e}。"
            f"禁止 fall-back（R03）。"
        ) from e


def _topological_sort_renames(rename_map: dict[str, str]) -> list[str]:
    """对链式重命名做拓扑排序（R339 内部函数）。

    对于 {A→B, B→C}，拓扑顺序是 [B, A]（先 B→C，再 A→B）。
    这样避免 A→B 时 B 已存在的冲突。

    Args:
        rename_map: 重命名映射（已过滤 old==new）。

    Returns:
        拓扑排序后的 old_name 列表。

    Raises:
        ValueError: 检测到循环（理论上 _detect_cycle 已检测，这里是防御性检查）。
    """
    # 构建依赖图: A→B 依赖 B（如果 B 也在 rename_map 中）
    # 即 A 必须在 B 之后执行
    # 拓扑顺序: 没有依赖的先执行
    deps: dict[str, set[str]] = {old: set() for old in rename_map}
    for old, new in rename_map.items():
        if new in rename_map and new != old:
            # old 依赖 new（new 必须先执行）
            deps[old].add(new)

    # Kahn 算法拓扑排序
    in_degree: dict[str, int] = {old: len(d) for old, d in deps.items()}
    queue: list[str] = [old for old, deg in in_degree.items() if deg == 0]
    result: list[str] = []
    while queue:
        node = queue.pop(0)
        result.append(node)
        # 减少依赖 node 的节点的入度
        for other_old, other_deps in deps.items():
            if node in other_deps:
                in_degree[other_old] -= 1
                if in_degree[other_old] == 0:
                    queue.append(other_old)

    if len(result) != len(rename_map):
        # 理论上 _detect_cycle 已经检测过循环，这里不应该触发
        raise ValueError(
            "重命名映射存在循环依赖（内部错误，应该已被检测）。"
            "禁止 fall-back（R03）。"
        )

    return result


# =============================================================================
# 报告生成
# =============================================================================
def generate_rename_report(
    input_path: str | Path,
    output_path: str | Path,
    rename_map: dict[str, str],
    output_format: str = "text",
) -> str:
    """重命名 GDSII 器件并生成报告字符串（R339）。

    Args:
        input_path: 输入 GDSII 文件路径。
        output_path: 输出 GDSII 文件路径。
        rename_map: 重命名映射 {old_name: new_name}。
        output_format: 输出格式（'text' / 'markdown' / 'json'）。

    Returns:
        报告字符串。

    Raises:
        ValueError: 不支持的格式 / rename_map 为空。
        FileNotFoundError: 输入文件不存在。
        ImportError: klayout 未安装。

    来源:
    - CommonMark: https://spec.commonmark.org/
    - JSON: https://www.json.org/
    """
    report = rename_cells(input_path, output_path, rename_map)
    fmt = output_format.lower()
    if fmt == "text":
        return _render_text_report(report)
    if fmt == "markdown":
        return _render_markdown_report(report)
    if fmt == "json":
        return _render_json_report(report)
    raise ValueError(
        f"不支持的 output_format: {output_format}。"
        f"支持: text / markdown / json。"
    )


# =============================================================================
# 内部渲染函数
# =============================================================================
def _render_text_report(report: RenameReport) -> str:
    """渲染纯文本报告（R339 内部函数）。"""
    lines: list[str] = []
    lines.append("=" * 60)
    lines.append("GDSII 器件重命名报告")
    lines.append("=" * 60)
    lines.append(f"输入文件: {report.input_path}")
    lines.append(f"输出文件: {report.output_path}")
    lines.append(f"dbu: {report.dbu} μm")
    lines.append("")
    lines.append("-" * 60)
    lines.append("重命名统计")
    lines.append("-" * 60)
    lines.append(f"请求重命名数: {len(report.renames_requested)}")
    lines.append(f"实际重命名数: {report.total_renamed}")
    lines.append(f"重命名前 cell 数: {len(report.original_cell_names)}")
    lines.append(f"重命名后 cell 数: {len(report.final_cell_names)}")
    lines.append("")
    lines.append("-" * 60)
    lines.append("重命名记录")
    lines.append("-" * 60)
    if not report.renames_applied:
        lines.append("  （无重命名记录）")
    else:
        for rec in report.renames_applied:
            lines.append(f"  {rec.old_name} → {rec.new_name}")
    lines.append("")
    lines.append("-" * 60)
    lines.append("重命名前 cell 列表")
    lines.append("-" * 60)
    for name in report.original_cell_names:
        lines.append(f"  {name}")
    lines.append("")
    lines.append("-" * 60)
    lines.append("重命名后 cell 列表")
    lines.append("-" * 60)
    for name in report.final_cell_names:
        lines.append(f"  {name}")
    return "\n".join(lines)


def _render_markdown_report(report: RenameReport) -> str:
    """渲染 Markdown 报告（R339 内部函数）。"""
    lines: list[str] = []
    lines.append("# GDSII 器件重命名报告")
    lines.append("")
    lines.append("## 基本信息")
    lines.append("")
    lines.append(f"- **输入文件**: `{report.input_path}`")
    lines.append(f"- **输出文件**: `{report.output_path}`")
    lines.append(f"- **dbu**: {report.dbu} μm")
    lines.append("")
    lines.append("## 重命名统计")
    lines.append("")
    lines.append("| 指标 | 值 |")
    lines.append("|------|----|")
    lines.append(f"| 请求重命名数 | {len(report.renames_requested)} |")
    lines.append(f"| 实际重命名数 | {report.total_renamed} |")
    lines.append(f"| 重命名前 cell 数 | {len(report.original_cell_names)} |")
    lines.append(f"| 重命名后 cell 数 | {len(report.final_cell_names)} |")
    lines.append("")
    lines.append("## 重命名记录")
    lines.append("")
    if not report.renames_applied:
        lines.append("（无重命名记录）")
    else:
        lines.append("| 旧 cell 名 | 新 cell 名 |")
        lines.append("|-----------|-----------|")
        for rec in report.renames_applied:
            lines.append(f"| {rec.old_name} | {rec.new_name} |")
    lines.append("")
    lines.append("## 重命名前 cell 列表")
    lines.append("")
    for name in report.original_cell_names:
        lines.append(f"- {name}")
    lines.append("")
    lines.append("## 重命名后 cell 列表")
    lines.append("")
    for name in report.final_cell_names:
        lines.append(f"- {name}")
    return "\n".join(lines)


def _render_json_report(report: RenameReport) -> str:
    """渲染 JSON 报告（R339 内部函数）。"""
    import json
    data = {
        "input_path": report.input_path,
        "output_path": report.output_path,
        "dbu": report.dbu,
        "renames_requested": report.renames_requested,
        "total_renamed": report.total_renamed,
        "renames_applied": [
            {"old_name": r.old_name, "new_name": r.new_name}
            for r in report.renames_applied
        ],
        "original_cell_names": report.original_cell_names,
        "final_cell_names": report.final_cell_names,
    }
    return json.dumps(data, indent=2, ensure_ascii=False)
