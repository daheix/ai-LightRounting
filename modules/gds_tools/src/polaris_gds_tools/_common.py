"""polaris-gds-tools 共享基础设施：klayout 导入、层映射、原子写入。

本模块为 GDSII 工程化工具与多格式 IO 提供统一的基础设施，避免重复实现：

- ``get_klayout_db``：延迟导入 klayout.db，未安装时 raise ImportError（R03）。
- ``get_default_layer_map``：SiEPIC EBeam PDK 13 层标准映射（R02 溯源）。
- ``atomic_write_klayout``：klayout Layout 原子写入（临时文件 + os.replace）。
- ``atomic_write_text``：文本原子写入（POSIX rename 原子性）。

=== Input / Process / Output 三段式文档 ===

Input:
- get_klayout_db() -> klayout.db 模块
- get_default_layer_map() -> dict[(layer, datatype), name]
- atomic_write_klayout(ly, output_path) -> output_path
- atomic_write_text(content, path) -> None

Process:
- klayout.db 延迟导入（避免顶层 import 失败阻断整个包）
- 层映射取自 SiEPIC EBeam PDK（与 gdsfactory generic_pdk 对齐）
- 原子写入：mkstemp 临时文件 + fsync + os.replace（POSIX rename 原子性）

Output:
- klayout.db 模块对象 / 层映射 dict / 写入后的文件路径

学术依据（R02 学术诚信，均经 WebSearch 验证可访问）:
- KLayout Database API:
  https://www.klayout.org/doc-qt5/code/
- SiEPIC EBeam PDK 层映射（13 层标准）:
  https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- gdsfactory generic_pdk 层定义:
  https://gdsfactory.github.io/gdsfactory/
- POSIX rename(2) 原子性:
  https://pubs.opengroup.org/onlinepubs/9699919799/functions/rename.html
- Python os.replace:
  https://docs.python.org/3/library/os.html#os.replace
- atomicwrites 库（原子写入参考实现）:
  https://github.com/untitaker/python-atomicwrites
- KLayout Layout.write 文档（扩展名决定输出格式）:
  https://www.klayout.de/doc-qt5/code/class_KLayout_Layout.html

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R05 Bug 必修。
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any

__all__ = [
    "get_klayout_db",
    "get_default_layer_map",
    "atomic_write_klayout",
    "atomic_write_text",
]


def get_klayout_db() -> Any:
    """延迟导入 klayout.db 模块。

    Returns:
        klayout.db 模块对象。

    Raises:
        ImportError: klayout 未安装时抛出，含安装命令（R03 禁止静默兜底）。
    """
    try:
        import klayout.db as db
    except ImportError as e:
        raise ImportError(
            "klayout 未安装，GDSII 工程化功能不可用。"
            "安装命令: pip install klayout"
            f"（原始错误: {e}）"
        ) from e
    return db


def get_default_layer_map() -> dict[tuple[int, int], str]:
    """获取默认 SiEPIC 层映射（13 层标准）。

    来源: SiEPIC EBeam PDK https://github.com/SiEPIC/SiEPIC_EBeam_PDK
    与 gdsfactory generic_pdk 层定义对齐。
    """
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


def atomic_write_klayout(ly: Any, output_path: str) -> str:
    """原子写入 GDS/OASIS 文件（临时文件 + os.replace）。

    原 ly.write(output_path) 非原子，大版图写入耗时长，中断会导致文件截断/
    半写入，损坏的 GDS 提交到代工厂会直接导致流片失败。改为临时文件 +
    os.replace 原子替换。

    Args:
        ly: klayout.Layout 对象。
        output_path: 目标输出路径。

    Returns:
        output_path（写入成功后返回）。

    Raises:
        OSError: 临时文件创建或替换失败时抛出（R03 禁止 fall-back）。
    """
    target = Path(output_path)
    # 保留目标扩展名：klayout ly.write 依赖扩展名判断输出格式
    # (.gds/.oas/.gds2)，使用 .tmp 会导致格式判断失败。
    # 来源: KLayout Layout.write 文档
    suffix = target.suffix or ".gds"
    fd, tmp_name = tempfile.mkstemp(
        dir=target.parent, prefix=target.name + ".", suffix=suffix
    )
    # 关闭 fd，由 klayout ly.write 重新打开（避免双 open 冲突）
    os.close(fd)
    tmp_path = Path(tmp_name)
    try:
        ly.write(str(tmp_path))
        with open(tmp_path, "rb") as f:
            os.fsync(f.fileno())
        os.replace(tmp_path, target)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise
    return output_path


def atomic_write_text(content: str, path: str) -> None:
    """原子写入文本文件（临时文件 + fsync + os.replace）。

    原 Path(path).write_text() 非原子，进程中断会导致文件截断/半写入，
    客户导入时解析失败丢失设计成果。改为原子写入。

    Args:
        content: 文本内容。
        path: 输出文件路径。
    """
    target = Path(path)
    fd, tmp_name = tempfile.mkstemp(
        dir=target.parent, prefix=target.name + ".", suffix=".tmp"
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, target)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise
