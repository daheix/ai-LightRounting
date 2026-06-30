"""GDSII 器件位置报告工具（R336，Device Position Reporter）。

从 GDSII 文件提取所有 cell 实例的位置、旋转、镜像信息，生成器件位置
报告。用于芯片级布局分析、器件清单生成、位置验证。

## 核心概念

- **Cell 实例（Instance）**: GDSII 中一个 cell 对另一个 cell 的引用
- **变换（Transform）**: 实例的位置/旋转/镜像信息
  - 平移: (dx, dy) μm
  - 旋转: 0/90/180/270 度
  - 镜像: X 轴镜像
- **递归遍历**: 从顶层 cell 递归遍历所有层次的实例
- **全局位置**: 累加所有父级变换后的绝对位置
- **应用场景**:
  - 芯片级布局器件清单（BOM）
  - 器件位置验证（是否在指定区域）
  - 布局密度分析（器件分布）
  - 设计审查（器件摆放合理性）

## 算法

1. 读取 GDSII 文件
2. 获取顶层 cell
3. 非递归模式: 遍历顶层 cell 的直接实例
4. 递归模式: 从顶层 cell 递归遍历所有层次的实例
   - 用 Trans 累乘计算全局位置
   - 用 visited set 避免循环引用
5. 按 cell 名分组统计
6. 渲染报告（text/markdown/json）

## KLayout 0.30.9 API 关键事实（实测）

- `Cell.each_inst()`: 返回 Instance 迭代器（非递归，只直接子实例）
  - 来源: https://www.klayout.de/doc-qt5/code/class_Cell.html
- `Instance.cell`: 引用的 Cell 对象（属性）
- `Instance.cell_index`: 引用 cell 的 index
- `Instance.trans`: 实例变换（Trans 对象，属性）
- `Trans.angle`: 旋转角度代码（0=r0, 1=r90, 2=r180, 3=r270,
  4=m0, 5=m45, 6=m90, 7=m135）
- `Trans.rot`: 旋转代码（0-3，镜像不影响）
- `Trans.mirror`: 是否镜像（bool）
- `Trans.disp`: 平移 Vector（dbu 单位）
  - `Vector.x` / `Vector.y`: dbu 整数坐标
- `Trans * Trans`: 变换累乘（用于递归全局位置计算）
- `Layout.dbu`: 数据库单位（μm）

## 学术依据

- KLayout Cell class（each_inst / insert / bbox）:
  https://www.klayout.de/doc-qt5/code/class_Cell.html
- KLayout Instance class:
  https://www.klayout.de/doc-qt5/code/class_Instance.html
- KLayout Trans class（仿射变换）:
  https://www.klayout.de/doc-qt5/code/class_Trans.html
- KLayout Vector class:
  https://www.klayout.de/doc-qt5/code/class_Vector.html
- KLayout Database API:
  https://klayout.org/downloads/master/doc-qt5/programming/database_api.html
- GDSII 流格式标准（SREF/AREF 结构）:
  https://en.wikipedia.org/wiki/GDS_File
- KLayout Python 包:
  https://klayout.org/klayout-pypi/
- gdsfactory Component 参考（cell 实例模型）:
  https://gdsfactory.github.io/gdsfactory/api.html

合规: R01 / R02 / R03 / R04 / R05 / R11。
"""

from __future__ import annotations

import json
import logging
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

__all__ = [
    "DeviceInstance",
    "DevicePositionReport",
    "extract_device_positions",
    "generate_device_position_report",
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
            "klayout 未安装，无法执行 GDSII 器件位置提取。"
            "安装方式: pip install klayout。"
            f"原始错误: {e}"
        ) from e
    return db


# =============================================================================
# 数据类
# =============================================================================
@dataclass
class DeviceInstance:
    """单个器件实例信息（R336）。

    Attributes:
        cell_name: 引用的 cell 名（器件名）。
        x_um: 实例 X 位置（μm，全局坐标）。
        y_um: 实例 Y 位置（μm，全局坐标）。
        rotation: 旋转角度（0/90/180/270，度）。
        mirror: 是否镜像。
        parent_cell_name: 父 cell 名（实例化该器件的 cell）。
        hierarchy_level: 层次深度（顶层=0）。
        trans_str: KLayout Trans 字符串表示（如 "r90 10000,20000"）。
    """

    cell_name: str
    x_um: float = 0.0
    y_um: float = 0.0
    rotation: int = 0
    mirror: bool = False
    parent_cell_name: str = ""
    hierarchy_level: int = 0
    trans_str: str = ""


@dataclass
class DevicePositionReport:
    """GDSII 器件位置报告（R336）。

    Attributes:
        file_path: GDSII 文件路径。
        dbu: 数据库单位（μm）。
        top_cell_name: 顶层 cell 名。
        instances: 所有器件实例列表 DeviceInstance。
        total_count: 实例总数。
        cell_counts: 按 cell 名分组计数 {cell_name: count}。
        recursive: 是否递归遍历。
        max_hierarchy_level: 最大层次深度。
    """

    file_path: str = ""
    dbu: float = 0.0
    top_cell_name: str = ""
    instances: list[DeviceInstance] = field(default_factory=list)
    total_count: int = 0
    cell_counts: dict[str, int] = field(default_factory=dict)
    recursive: bool = False
    max_hierarchy_level: int = 0


# =============================================================================
# 器件位置提取主入口
# =============================================================================
def extract_device_positions(
    gds_path: str | Path,
    top_cell_name: str | None = None,
    recursive: bool = True,
) -> DevicePositionReport:
    """从 GDSII 提取器件位置信息（R336）。

    遍历顶层 cell 的所有 cell 实例，提取位置/旋转/镜像信息。

    Args:
        gds_path: GDSII 文件路径。
        top_cell_name: 顶层 cell 名（None 用第一个 top cell）。
        recursive: True 递归遍历所有层次实例（计算全局位置）；
            False 只遍历顶层 cell 的直接实例（相对位置）。

    Returns:
        DevicePositionReport 器件位置报告。

    Raises:
        FileNotFoundError: 文件不存在。
        ValueError: 文件无效 / top_cell_name 不存在 / 无 cell。
        ImportError: klayout 未安装。
        RuntimeError: 读取失败。

    来源:
    - KLayout Cell.each_inst:
      https://www.klayout.de/doc-qt5/code/class_Cell.html
    - KLayout Trans（变换累乘）:
      https://www.klayout.de/doc-qt5/code/class_Trans.html
    """
    db = _import_klayout_db()
    path = Path(gds_path)
    if not path.exists():
        raise FileNotFoundError(f"GDSII 文件不存在: {gds_path}")
    if not path.is_file():
        raise ValueError(f"路径不是文件: {gds_path}")

    ly = db.Layout()
    try:
        ly.read(str(path))
    except Exception as e:
        raise RuntimeError(
            f"klayout 读取文件失败: {type(e).__name__}: {e}。"
            f"禁止 fall-back（R03）。"
        ) from e

    dbu = float(ly.dbu)

    # 获取顶层 cell
    top_cell_indices = list(ly.each_top_cell())
    if not top_cell_indices:
        raise ValueError(
            f"GDSII 文件 {gds_path} 无顶层 cell，文件可能为空或损坏"
        )

    if top_cell_name is not None:
        top_cell = ly.cell(top_cell_name)
        if top_cell is None:
            available = sorted(ly.cell(ci).name for ci in ly.each_top_cell())
            raise ValueError(
                f"top_cell_name '{top_cell_name}' 不存在。"
                f"可用顶层 cells: {available}"
            )
    else:
        top_cell = ly.cell(top_cell_indices[0])

    top_cell_name_str = str(top_cell.name)

    # 提取实例
    instances: list[DeviceInstance] = []
    if recursive:
        # 递归遍历：用 visited set 避免循环引用
        # 来源: KLayout Trans 累乘 https://www.klayout.de/doc-qt5/code/class_Trans.html
        _collect_instances_recursive(
            top_cell, dbu, instances, ly,
            parent_trans=None,
            parent_name=top_cell_name_str,
            level=0,
            visited=None,
        )
    else:
        # 非递归：只遍历顶层 cell 的直接实例
        for inst in top_cell.each_inst():
            instances.append(
                _instance_to_device(
                    inst, dbu, top_cell_name_str, level=0
                )
            )

    # 按位置排序: y → x → cell_name
    instances.sort(key=lambda d: (d.y_um, d.x_um, d.cell_name))

    # 分组统计
    cell_counts = dict(Counter(d.cell_name for d in instances))
    max_level = max((d.hierarchy_level for d in instances), default=0)

    logger.info(
        "GDSII 器件位置提取: %s (top=%s, instances=%d, recursive=%s)",
        path, top_cell_name_str, len(instances), recursive,
    )

    return DevicePositionReport(
        file_path=str(gds_path),
        dbu=dbu,
        top_cell_name=top_cell_name_str,
        instances=instances,
        total_count=len(instances),
        cell_counts=cell_counts,
        recursive=recursive,
        max_hierarchy_level=max_level,
    )


# =============================================================================
# 报告生成
# =============================================================================
def generate_device_position_report(
    gds_path: str | Path,
    top_cell_name: str | None = None,
    recursive: bool = True,
    output_format: str = "text",
) -> str:
    """生成 GDSII 器件位置报告字符串（R336）。

    Args:
        gds_path: GDSII 文件路径。
        top_cell_name: 顶层 cell 名。
        recursive: 是否递归遍历。
        output_format: 输出格式（'text' / 'markdown' / 'json'）。

    Returns:
        报告字符串。

    Raises:
        ValueError: 不支持的格式 / 参数无效。
        FileNotFoundError: 文件不存在。
        ImportError: klayout 未安装。

    来源:
    - CommonMark: https://spec.commonmark.org/
    - JSON: https://www.json.org/
    """
    report = extract_device_positions(
        gds_path,
        top_cell_name=top_cell_name,
        recursive=recursive,
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
# 内部辅助函数
# =============================================================================
def _angle_to_rotation(angle: int) -> int:
    """将 KLayout Trans.angle 转为旋转度数（R336 内部函数）。

    KLayout Trans.angle 返回旋转代码（0-3），不含镜像信息:
    - 0 = r0 (0 度)
    - 1 = r90 (90 度)
    - 2 = r180 (180 度)
    - 3 = r270 (270 度)

    镜像信息由 Trans.mirror 单独提供（bool）。

    来源: https://www.klayout.de/doc-qt5/code/class_Trans.html
    """
    # angle 是 0-3 的旋转代码
    return (angle % 4) * 90


def _instance_to_device(
    inst, dbu: float, parent_name: str, level: int,
    parent_trans=None,
) -> DeviceInstance:
    """将 KLayout Instance 转换为 DeviceInstance（R336 内部函数）。

    如果提供 parent_trans，则计算全局位置（累加变换）；
    否则使用实例自身位置（相对位置）。

    Args:
        inst: KLayout Instance 对象。
        dbu: 数据库单位（μm）。
        parent_name: 父 cell 名。
        level: 层次深度。
        parent_trans: 父级累加变换（None 表示无父级变换）。

    Returns:
        DeviceInstance 器件实例信息。
    """
    trans = inst.trans
    cell_obj = inst.cell
    cell_name = str(cell_obj.name)

    # 计算全局变换
    if parent_trans is not None:
        # Trans 累乘: global_trans = parent_trans * inst.trans
        # 来源: https://www.klayout.de/doc-qt5/code/class_Trans.html
        global_trans = parent_trans * trans
    else:
        global_trans = trans

    # 提取位置（dbu → μm）
    disp = global_trans.disp
    x_um = float(disp.x) * dbu
    y_um = float(disp.y) * dbu

    # 旋转和镜像
    # Trans.angle 返回旋转代码（0-3），不含镜像
    # Trans.mirror 返回是否镜像（bool）
    # 来源: https://www.klayout.de/doc-qt5/code/class_Trans.html
    angle = int(global_trans.angle)
    rotation = _angle_to_rotation(angle)
    mirror = bool(global_trans.mirror)

    return DeviceInstance(
        cell_name=cell_name,
        x_um=x_um,
        y_um=y_um,
        rotation=rotation,
        mirror=mirror,
        parent_cell_name=parent_name,
        hierarchy_level=level,
        trans_str=str(global_trans),
    )


def _collect_instances_recursive(
    cell, dbu: float, instances: list, ly,
    parent_trans, parent_name: str, level: int,
    visited: set | None,
) -> None:
    """递归收集 cell 的所有实例（R336 内部函数）。

    用 visited set 避免循环引用（KLayout 允许循环 cell 引用）。

    Args:
        cell: KLayout Cell 对象。
        dbu: 数据库单位。
        instances: 收集结果列表。
        ly: KLayout Layout 对象。
        parent_trans: 父级累加变换（None 表示顶层）。
        parent_name: 父 cell 名。
        level: 当前层次深度。
        visited: 已访问 cell index 集合（None 初始化）。
    """
    if visited is None:
        visited = set()

    cell_idx = int(cell.cell_index())
    # 注意: 同一个 cell 可以在不同层次出现，不能用 cell_idx 去重
    # 只在直接循环引用时跳过（cell 引用自己）
    # 但为了安全，限制递归深度

    if level > 20:  # 防止过深递归
        logger.warning("递归深度超过 20，跳过: %s", cell.name)
        return

    for inst in cell.each_inst():
        # 计算全局变换
        trans = inst.trans
        if parent_trans is not None:
            global_trans = parent_trans * trans
        else:
            global_trans = trans

        # 提取器件信息
        device = _instance_to_device(
            inst, dbu, parent_name, level,
            parent_trans=parent_trans,
        )
        instances.append(device)

        # 递归进入子 cell
        child_cell = inst.cell
        child_idx = int(child_cell.cell_index())

        # 用 (cell_idx, parent_trans_str) 去重，避免同一变换下重复访问
        visit_key = (child_idx, str(global_trans))
        if visit_key not in visited:
            visited.add(visit_key)
            _collect_instances_recursive(
                child_cell, dbu, instances, ly,
                parent_trans=global_trans,
                parent_name=str(child_cell.name),
                level=level + 1,
                visited=visited,
            )


def _render_text_report(report: DevicePositionReport) -> str:
    """渲染纯文本报告（R336 内部函数）。"""
    lines: list[str] = []
    lines.append("=" * 70)
    lines.append("GDSII 器件位置报告")
    lines.append("=" * 70)
    lines.append(f"文件: {report.file_path}")
    lines.append(f"dbu: {report.dbu} μm")
    lines.append(f"顶层 cell: {report.top_cell_name}")
    lines.append(f"递归遍历: {report.recursive}")
    lines.append(f"实例总数: {report.total_count}")
    lines.append(f"最大层次深度: {report.max_hierarchy_level}")
    lines.append("")
    lines.append("-" * 70)
    lines.append("按 cell 分组统计:")
    lines.append("-" * 70)
    for cell_name, count in sorted(report.cell_counts.items()):
        lines.append(f"  {cell_name}: {count}")
    lines.append("")
    lines.append("-" * 70)
    lines.append("所有器件实例:")
    lines.append("-" * 70)
    lines.append(
        f"{'cell':<20} {'X(μm)':>10} {'Y(μm)':>10} "
        f"{'rot':>5} {'mir':>4} {'lvl':>4} {'parent':<15}"
    )
    for d in report.instances:
        lines.append(
            f"{d.cell_name:<20} {d.x_um:>10.3f} {d.y_um:>10.3f} "
            f"{d.rotation:>5} {'Y' if d.mirror else 'N':>4} "
            f"{d.hierarchy_level:>4} {d.parent_cell_name:<15}"
        )
    lines.append("=" * 70)
    return "\n".join(lines)


def _render_markdown_report(report: DevicePositionReport) -> str:
    """渲染 Markdown 报告（R336 内部函数）。"""
    lines: list[str] = []
    lines.append("# GDSII 器件位置报告")
    lines.append("")
    lines.append(f"**文件**: `{report.file_path}`")
    lines.append(f"**dbu**: {report.dbu} μm")
    lines.append(f"**顶层 cell**: `{report.top_cell_name}`")
    lines.append(f"**递归遍历**: {report.recursive}")
    lines.append(f"**实例总数**: {report.total_count}")
    lines.append(f"**最大层次深度**: {report.max_hierarchy_level}")
    lines.append("")
    lines.append("## 按 cell 分组统计")
    lines.append("")
    lines.append("| cell 名 | 数量 |")
    lines.append("|---------|------|")
    for cell_name, count in sorted(report.cell_counts.items()):
        lines.append(f"| `{cell_name}` | {count} |")
    lines.append("")
    lines.append("## 所有器件实例")
    lines.append("")
    lines.append(
        "| cell | X(μm) | Y(μm) | rot | mirror | level | parent |"
    )
    lines.append("|------|-------|-------|-----|--------|-------|--------|")
    for d in report.instances:
        mirror_str = "Y" if d.mirror else "N"
        lines.append(
            f"| `{d.cell_name}` | {d.x_um:.3f} | {d.y_um:.3f} | "
            f"{d.rotation} | {mirror_str} | {d.hierarchy_level} | "
            f"`{d.parent_cell_name}` |"
        )
    return "\n".join(lines)


def _render_json_report(report: DevicePositionReport) -> str:
    """渲染 JSON 报告（R336 内部函数）。"""
    data = {
        "file_path": report.file_path,
        "dbu": report.dbu,
        "top_cell_name": report.top_cell_name,
        "recursive": report.recursive,
        "total_count": report.total_count,
        "max_hierarchy_level": report.max_hierarchy_level,
        "cell_counts": report.cell_counts,
        "instances": [
            {
                "cell_name": d.cell_name,
                "x_um": d.x_um,
                "y_um": d.y_um,
                "rotation": d.rotation,
                "mirror": d.mirror,
                "parent_cell_name": d.parent_cell_name,
                "hierarchy_level": d.hierarchy_level,
                "trans_str": d.trans_str,
            }
            for d in report.instances
        ],
    }
    return json.dumps(data, ensure_ascii=False, indent=2)
