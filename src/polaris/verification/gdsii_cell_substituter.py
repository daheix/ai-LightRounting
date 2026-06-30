"""GDSII 器件替换工具（R338，Cell Instance Substituter）。

替换 GDSII 文件中 cell 实例的引用，把引用旧 cell 的实例改为引用新 cell。
用于 PDK 版本升级、器件替换、工艺迁移。

## 核心概念

- **Cell 实例替换**: 把 cell 中引用 cell_A 的实例改为引用 cell_B
- **保留变换**: 实例的位置、旋转、镜像、数组属性保持不变
- **典型用途**:
  - PDK 版本升级: 把 v1_mzi 实例替换为 v2_mzi
  - 器件替换: 把 broken_device 替换为 fixed_device
  - 工艺迁移: 把 old_pdk_bend 替换为 new_pdk_bend

## KLayout 0.30.9 API 关键事实（R338 冒烟测试实测）

- `Cell.each_inst()`: 返回 Instance 迭代器
- `Instance.cell_index`: 引用的 cell index（int，属性）
- `Instance.cell`: 引用的 Cell 对象（属性）
- `Instance.trans`: 实例变换（Trans 对象，属性）
- `Instance.is_regular_array()`: 是否是规则数组（方法，非 is_array）
- `Instance.na` / `Instance.nb`: 数组维度（int，属性）
- `Instance.a` / `Instance.b`: 数组向量（Vector，属性）
- `Instance.prop_id`: 属性 ID（int，属性）
- `Instance.parent_cell`: 父 Cell 对象（属性）
- `Cell.clear_insts()`: 清空所有实例
- `Cell.insert(CellInstArray)`: 插入实例
- `db.CellInstArray(cell_index, trans)`: 普通实例
- `db.CellInstArray(cell_index, trans, a, b, na, nb)`: 数组实例
- `Layout.cell(name)`: 按名取 Cell（不存在返回 None）
- `Cell.cell_index()`: 返回 int cell index
- `Layout.each_cell()`: 返回 Cell 对象迭代器
- `Layout.write(path)`: 写出整个 layout

## 算法

1. 读取 GDSII
2. 验证 substitutions 中所有新 cell 名存在
3. 构建 cell_index 替换映射（old_ci → new_ci）
4. 对每个目标 cell（top_cell_name 指定或所有 cell）:
   a. 遍历 each_inst()，收集实例信息:
      - cell_index, trans, is_regular_array, a, b, na, nb, prop_id
   b. clear_insts() 清空所有实例
   c. 重新插入实例，对需要替换的用新 cell_index
5. 写出 GDSII

## 保留属性

实例的 prop_id 属性通过 `Instance.set_property(key, value)` 重建。
为简化实现，本工具保留 prop_id 但不保留自定义属性键值对（GDSII 文件
通常无实例属性）。如需保留自定义属性，可扩展 `_collect_instance_info`。

## 学术依据

- KLayout Instance class:
  https://www.klayout.org/doc-qt5/code/class_Instance.html
- KLayout Cell class:
  https://www.klayout.org/doc-qt5/code/class_Cell.html
- KLayout CellInstArray:
  https://www.klayout.org/doc-qt5/code/class_CellInstArray.html
- KLayout Database API:
  https://klayout.org/downloads/master/doc-qt5/programming/database_api.html
- GDSII 格式: https://en.wikipedia.org/wiki/GDS_File
- SiEPIC EBeam PDK 器件替换:
  https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- Calibre LVS 器件匹配:
  https://www.mentor.com/products/ic_nanometer_design/calibre-lvs
- KLayout PCell 替换:
  https://klayout.org/doc-qt5/about/layer_map.html

合规: R01 / R02 / R03 / R04 / R05 / R11。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

__all__ = [
    "SubstitutionRecord",
    "SubstituteReport",
    "substitute_cell_instances",
    "generate_substitute_report",
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
            "klayout 未安装，无法执行 GDSII 器件替换。"
            "安装方式: pip install klayout。"
            f"原始错误: {e}"
        ) from e
    return db


# =============================================================================
# 数据类
# =============================================================================
@dataclass
class SubstitutionRecord:
    """单次替换记录（R338）。

    Attributes:
        parent_cell_name: 父 cell 名（实例所在 cell）。
        old_cell_name: 旧 cell 名（被替换的）。
        new_cell_name: 新 cell 名（替换为）。
        instance_count: 替换的实例数。
        is_array: 是否为数组实例。
    """

    parent_cell_name: str
    old_cell_name: str
    new_cell_name: str
    instance_count: int
    is_array: bool


@dataclass
class SubstituteReport:
    """GDSII 器件替换报告（R338）。

    Attributes:
        input_path: 输入 GDSII 文件路径。
        output_path: 输出 GDSII 文件路径。
        substitutions_requested: 用户请求的替换映射（old → new）。
        substitutions_applied: 实际应用的替换记录列表。
        total_instances_replaced: 总替换实例数。
        cells_affected: 受影响的 cell 名列表。
        dbu: 数据库单位（μm）。
        top_cell_names: 顶层 cell 名列表。
    """

    input_path: str = ""
    output_path: str = ""
    substitutions_requested: dict[str, str] = field(default_factory=dict)
    substitutions_applied: list[SubstitutionRecord] = field(default_factory=list)
    total_instances_replaced: int = 0
    cells_affected: list[str] = field(default_factory=list)
    dbu: float = 0.0
    top_cell_names: list[str] = field(default_factory=list)


# =============================================================================
# 内部辅助函数
# =============================================================================
def _collect_instance_info(inst) -> dict:
    """收集 Instance 的可重建属性（R338 内部函数）。

    保存的属性:
    - cell_index: int
    - trans: Trans 对象
    - is_array: bool（is_regular_array）
    - a, b: Vector（仅数组）
    - na, nb: int（仅数组）
    - prop_id: int

    Args:
        inst: KLayout Instance 对象。

    Returns:
        属性字典。

    来源:
    - KLayout Instance:
      https://www.klayout.org/doc-qt5/code/class_Instance.html
    """
    is_array = bool(inst.is_regular_array())
    info = {
        "cell_index": int(inst.cell_index),
        "trans": inst.trans,
        "is_array": is_array,
        "prop_id": int(inst.prop_id),
    }
    if is_array:
        info["a"] = inst.a
        info["b"] = inst.b
        info["na"] = int(inst.na)
        info["nb"] = int(inst.nb)
    return info


def _rebuild_instance(db_module, cell, info: dict, new_cell_index: int):
    """根据保存的属性重建实例并插入到 cell（R338 内部函数）。

    Args:
        db_module: klayout.db 模块。
        cell: 目标 Cell 对象。
        info: _collect_instance_info 返回的属性字典。
        new_cell_index: 新的 cell index（可能是原值或替换值）。

    Returns:
        新创建的 Instance 对象。
    """
    trans = info["trans"]
    if info["is_array"]:
        arr = db_module.CellInstArray(
            new_cell_index, trans,
            info["a"], info["b"],
            info["na"], info["nb"],
        )
    else:
        arr = db_module.CellInstArray(new_cell_index, trans)
    new_inst = cell.insert(arr)
    # 保留 prop_id（非 0 时设置）
    if info["prop_id"] != 0:
        new_inst.prop_id = info["prop_id"]
    return new_inst


def _cell_contains_child(ly, parent_ci: int, target_ci: int,
                          visited: set[int] | None = None) -> bool:
    """检测 parent_ci 的子树中是否包含 target_ci（R338 内部函数）。

    递归遍历 parent_ci 的所有子 cell（通过实例引用），检测 target_ci
    是否在子树中。用 visited 集合避免循环引用导致的无限递归。

    Args:
        ly: KLayout Layout 对象。
        parent_ci: 起始 cell index。
        target_ci: 目标 cell index。
        visited: 已访问 cell index 集合（防循环）。

    Returns:
        True 若 target_ci 在 parent_ci 的子树中。

    来源:
    - KLayout Cell.each_child_cell:
      https://www.klayout.org/doc-qt5/code/class_Cell.html
    """
    if visited is None:
        visited = set()
    if parent_ci in visited:
        return False
    visited.add(parent_ci)
    parent_cell = ly.cell(parent_ci)
    if parent_cell is None:
        return False
    for child_ci in parent_cell.each_child_cell():
        child_ci = int(child_ci)
        if child_ci == target_ci:
            return True
        if _cell_contains_child(ly, child_ci, target_ci, visited):
            return True
    return False


def _would_create_cycle(ly, old_ci: int, new_ci: int) -> bool:
    """检测替换 old_ci → new_ci 是否会创建循环引用（R338 内部函数）。

    替换后，所有引用 old_ci 的实例改为引用 new_ci。如果 new_ci 的子树中
    包含 old_ci，则替换后 new_ci 会通过 old_ci→new_ci 引用自己，形成循环。

    Args:
        ly: KLayout Layout 对象。
        old_ci: 旧 cell index。
        new_ci: 新 cell index。

    Returns:
        True 若替换会创建循环引用。
    """
    if old_ci == new_ci:
        return False  # 无变化
    return _cell_contains_child(ly, new_ci, old_ci)


# =============================================================================
# 替换主入口
# =============================================================================
def substitute_cell_instances(
    input_path: str | Path,
    output_path: str | Path,
    substitutions: dict[str, str],
    top_cell_name: str | None = None,
) -> SubstituteReport:
    """替换 GDSII 中 cell 实例的引用（R338）。

    把引用旧 cell 的实例改为引用新 cell，保留实例的位置、旋转、镜像、
    数组属性。

    Args:
        input_path: 输入 GDSII 文件路径。
        output_path: 输出 GDSII 文件路径。
        substitutions: 替换映射 {old_cell_name: new_cell_name}。
            key: 旧 cell 名（要被替换的）。
            value: 新 cell 名（替换为）。
        top_cell_name: 指定在哪个 cell 内替换实例（None=所有 cell）。
            指定后只替换该 cell 的实例，其他 cell 不变。

    Returns:
        SubstituteReport 替换报告。

    Raises:
        FileNotFoundError: 输入文件不存在。
        ValueError: 文件无效 / substitutions 为空 / substitutions 含不存在的
            cell 名 / top_cell_name 不存在 / 无 cell。
        ImportError: klayout 未安装。
        RuntimeError: 读取或写出失败。

    来源:
    - KLayout Instance:
      https://www.klayout.org/doc-qt5/code/class_Instance.html
    - KLayout Cell.clear_insts:
      https://www.klayout.org/doc-qt5/code/class_Cell.html
    """
    db = _import_klayout_db()
    in_path = Path(input_path)
    out_path = Path(output_path)

    if not in_path.exists():
        raise FileNotFoundError(f"输入 GDSII 文件不存在: {input_path}")
    if not in_path.is_file():
        raise ValueError(f"输入路径不是文件: {input_path}")
    if not substitutions:
        raise ValueError(
            "substitutions 不能为空。禁止 fall-back（R03）。"
        )

    # 读取 GDSII
    ly = db.Layout()
    try:
        ly.read(str(in_path))
    except Exception as e:
        raise RuntimeError(
            f"klayout 读取文件失败: {type(e).__name__}: {e}。"
            f"禁止 fall-back（R03）。"
        ) from e

    dbu = float(ly.dbu)
    top_cell_names_list = sorted(
        ly.cell(ci).name for ci in ly.each_top_cell()
    )

    # 验证 substitutions 中的 cell 名都存在
    cell_index_map: dict[str, int] = {}  # name → cell_index
    for old_name, new_name in substitutions.items():
        if old_name not in cell_index_map:
            old_cell = ly.cell(old_name)
            if old_cell is None:
                raise ValueError(
                    f"substitutions 中旧 cell 名 '{old_name}' 不存在。"
                    f"禁止 fall-back（R03）。"
                )
            cell_index_map[old_name] = int(old_cell.cell_index())
        if new_name not in cell_index_map:
            new_cell = ly.cell(new_name)
            if new_cell is None:
                raise ValueError(
                    f"substitutions 中新 cell 名 '{new_name}' 不存在。"
                    f"禁止 fall-back（R03）。"
                )
            cell_index_map[new_name] = int(new_cell.cell_index())

    # 构建 cell_index 替换映射
    ci_substitution_map: dict[int, int] = {}
    for old_name, new_name in substitutions.items():
        old_ci = cell_index_map[old_name]
        new_ci = cell_index_map[new_name]
        # 检测循环引用：替换后 new_ci 不能引用自己
        if _would_create_cycle(ly, old_ci, new_ci):
            raise ValueError(
                f"替换 '{old_name}' → '{new_name}' 会创建循环引用："
                f"'{new_name}' 的子树中已包含 '{old_name}'，"
                f"替换后 '{new_name}' 会引用自己。"
                f"禁止 fall-back（R03）。"
            )
        ci_substitution_map[old_ci] = new_ci

    # 确定要处理的 cell 列表
    if top_cell_name is not None:
        target_cell = ly.cell(top_cell_name)
        if target_cell is None:
            raise ValueError(
                f"top_cell_name '{top_cell_name}' 不存在。"
                f"可用顶层 cells: {top_cell_names_list}"
            )
        cells_to_process = [target_cell]
    else:
        cells_to_process = list(ly.each_cell())

    if not cells_to_process:
        raise ValueError(
            f"GDSII 文件 {input_path} 无任何 cell，文件可能为空或损坏"
        )

    # 执行替换
    substitutions_applied: list[SubstitutionRecord] = []
    total_instances_replaced = 0
    cells_affected: list[str] = []

    # 按 (parent_cell, old_name, new_name, is_array) 分组记录
    record_map: dict[tuple[str, str, str, bool], int] = {}

    # 第一遍：收集所有 cell 的实例信息（避免在 clear_insts 后遍历
    # 其他 cell 触发 KLayout 内部拓扑排序错误）
    # cell_infos: list of (cell_name, instances_info, has_replacement)
    cell_infos: list[tuple[str, list[dict], bool]] = []
    for cell in cells_to_process:
        instances_info: list[dict] = []
        for inst in cell.each_inst():
            instances_info.append(_collect_instance_info(inst))

        if not instances_info:
            continue

        has_replacement = any(
            info["cell_index"] in ci_substitution_map
            for info in instances_info
        )
        if has_replacement:
            cell_infos.append((cell.name, instances_info, True))
        # 不需要替换的 cell 不记录，保持原样

    # 第二遍：对需要替换的 cell 执行 clear + 重建
    for cell_name, instances_info, _ in cell_infos:
        cell = ly.cell(cell_name)
        if cell is None:
            continue
        cells_affected.append(cell_name)
        # 清空所有实例
        cell.clear_insts()
        # 重新插入，应用替换
        for info in instances_info:
            old_ci = info["cell_index"]
            if old_ci in ci_substitution_map:
                new_ci = ci_substitution_map[old_ci]
                old_name = ly.cell(old_ci).name
                new_name = ly.cell(new_ci).name
                _rebuild_instance(db, cell, info, new_ci)
                total_instances_replaced += 1
                key = (cell_name, old_name, new_name, info["is_array"])
                record_map[key] = record_map.get(key, 0) + 1
            else:
                # 不需要替换，原样重建
                _rebuild_instance(db, cell, info, old_ci)

    # 构建 SubstitutionRecord 列表
    for (parent_name, old_name, new_name, is_array), count in record_map.items():
        substitutions_applied.append(SubstitutionRecord(
            parent_cell_name=parent_name,
            old_cell_name=old_name,
            new_cell_name=new_name,
            instance_count=count,
            is_array=is_array,
        ))

    # 排序（按 parent_cell_name, old_cell_name, new_cell_name）
    substitutions_applied.sort(
        key=lambda r: (r.parent_cell_name, r.old_cell_name, r.new_cell_name)
    )

    # 写出
    try:
        ly.write(str(out_path))
    except Exception as e:
        raise RuntimeError(
            f"klayout 写出文件失败: {type(e).__name__}: {e}。"
            f"禁止 fall-back（R03）。"
        ) from e

    logger.info(
        "GDSII 器件替换: %s → %s (substitutions=%d, instances=%d, cells=%d)",
        in_path, out_path, len(substitutions),
        total_instances_replaced, len(cells_affected),
    )

    return SubstituteReport(
        input_path=str(input_path),
        output_path=str(output_path),
        substitutions_requested=dict(substitutions),
        substitutions_applied=substitutions_applied,
        total_instances_replaced=total_instances_replaced,
        cells_affected=sorted(cells_affected),
        dbu=dbu,
        top_cell_names=top_cell_names_list,
    )


# =============================================================================
# 报告生成
# =============================================================================
def generate_substitute_report(
    input_path: str | Path,
    output_path: str | Path,
    substitutions: dict[str, str],
    top_cell_name: str | None = None,
    output_format: str = "text",
) -> str:
    """替换 GDSII 器件并生成报告字符串（R338）。

    Args:
        input_path: 输入 GDSII 文件路径。
        output_path: 输出 GDSII 文件路径。
        substitutions: 替换映射 {old_cell_name: new_cell_name}。
        top_cell_name: 指定在哪个 cell 内替换（None=所有 cell）。
        output_format: 输出格式（'text' / 'markdown' / 'json'）。

    Returns:
        报告字符串。

    Raises:
        ValueError: 不支持的格式 / substitutions 为空。
        FileNotFoundError: 输入文件不存在。
        ImportError: klayout 未安装。

    来源:
    - CommonMark: https://spec.commonmark.org/
    - JSON: https://www.json.org/
    """
    report = substitute_cell_instances(
        input_path, output_path, substitutions, top_cell_name=top_cell_name,
    )
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
def _render_text_report(report: SubstituteReport) -> str:
    """渲染纯文本报告（R338 内部函数）。"""
    lines: list[str] = []
    lines.append("=" * 60)
    lines.append("GDSII 器件替换报告")
    lines.append("=" * 60)
    lines.append(f"输入文件: {report.input_path}")
    lines.append(f"输出文件: {report.output_path}")
    lines.append(f"dbu: {report.dbu} μm")
    lines.append(f"顶层 cell: {report.top_cell_names}")
    lines.append("")
    lines.append("-" * 60)
    lines.append("替换统计")
    lines.append("-" * 60)
    lines.append(f"请求替换数: {len(report.substitutions_requested)}")
    lines.append(f"实际替换实例数: {report.total_instances_replaced}")
    lines.append(f"受影响 cell 数: {len(report.cells_affected)}")
    lines.append(f"受影响 cell: {report.cells_affected}")
    lines.append("")
    lines.append("-" * 60)
    lines.append("请求的替换映射")
    lines.append("-" * 60)
    for old, new in report.substitutions_requested.items():
        lines.append(f"  {old} → {new}")
    lines.append("")
    lines.append("-" * 60)
    lines.append("应用的替换记录")
    lines.append("-" * 60)
    if not report.substitutions_applied:
        lines.append("  （无替换记录）")
    else:
        for rec in report.substitutions_applied:
            arr_tag = " [数组]" if rec.is_array else ""
            lines.append(
                f"  {rec.parent_cell_name}: {rec.old_cell_name} → "
                f"{rec.new_cell_name} × {rec.instance_count}{arr_tag}"
            )
    return "\n".join(lines)


def _render_markdown_report(report: SubstituteReport) -> str:
    """渲染 Markdown 报告（R338 内部函数）。"""
    lines: list[str] = []
    lines.append("# GDSII 器件替换报告")
    lines.append("")
    lines.append("## 基本信息")
    lines.append("")
    lines.append(f"- **输入文件**: `{report.input_path}`")
    lines.append(f"- **输出文件**: `{report.output_path}`")
    lines.append(f"- **dbu**: {report.dbu} μm")
    lines.append(f"- **顶层 cell**: {report.top_cell_names}")
    lines.append("")
    lines.append("## 替换统计")
    lines.append("")
    lines.append("| 指标 | 值 |")
    lines.append("|------|----|")
    lines.append(f"| 请求替换数 | {len(report.substitutions_requested)} |")
    lines.append(f"| 实际替换实例数 | {report.total_instances_replaced} |")
    lines.append(f"| 受影响 cell 数 | {len(report.cells_affected)} |")
    lines.append("")
    lines.append("## 请求的替换映射")
    lines.append("")
    lines.append("| 旧 cell | 新 cell |")
    lines.append("|---------|---------|")
    for old, new in report.substitutions_requested.items():
        lines.append(f"| {old} | {new} |")
    lines.append("")
    lines.append("## 应用的替换记录")
    lines.append("")
    if not report.substitutions_applied:
        lines.append("（无替换记录）")
    else:
        lines.append("| 父 cell | 旧 cell | 新 cell | 实例数 | 数组 |")
        lines.append("|---------|---------|---------|--------|------|")
        for rec in report.substitutions_applied:
            arr_tag = "是" if rec.is_array else "否"
            lines.append(
                f"| {rec.parent_cell_name} | {rec.old_cell_name} | "
                f"{rec.new_cell_name} | {rec.instance_count} | {arr_tag} |"
            )
    return "\n".join(lines)


def _render_json_report(report: SubstituteReport) -> str:
    """渲染 JSON 报告（R338 内部函数）。"""
    import json
    data = {
        "input_path": report.input_path,
        "output_path": report.output_path,
        "dbu": report.dbu,
        "top_cell_names": report.top_cell_names,
        "substitutions_requested": report.substitutions_requested,
        "total_instances_replaced": report.total_instances_replaced,
        "cells_affected": report.cells_affected,
        "substitutions_applied": [
            {
                "parent_cell_name": r.parent_cell_name,
                "old_cell_name": r.old_cell_name,
                "new_cell_name": r.new_cell_name,
                "instance_count": r.instance_count,
                "is_array": r.is_array,
            }
            for r in report.substitutions_applied
        ],
    }
    return json.dumps(data, indent=2, ensure_ascii=False)
