"""PDK 版本兼容性检测器（R316）。

扩展 R09 的 check_gdsfactory_version_compatibility，提供完整的多维度版本
兼容性检测：PDK 版本/Python 版本/上游依赖/KLayout 版本/NumPy 版本。

R316 实现:
- CompatibilityCheck: 单项检测结果
- CompatibilityReport: 完整兼容性报告
- check_python_compatibility: Python 版本兼容性（3.10-3.13 推荐）
- check_klayout_compatibility: KLayout 版本兼容性（≥0.28 推荐）
- check_numpy_compatibility: NumPy 版本兼容性（≥1.24 推荐）
- check_pdk_version_compatibility: PDK YAML 版本字段兼容性
- run_full_compatibility_check: 端到端兼容性检测
- format_compatibility_report: 渲染报告（text/markdown）

R03 合规:
- 未安装的依赖 raise ImportError（不静默跳过该项检测）
- 版本字符串解析失败 raise ValueError
- 不支持的格式 raise ValueError

R02 学术诚信:
- 版本兼容性矩阵参考 gdsfactory/SiEPIC/KLayout/NumPy 官方文档
- Python 3.14 兼容性问题引用 gdsfactory pydantic 锁定问题

来源:
- gdsfactory: https://gdsfactory.github.io/gdsfactory/
- gdsfactory pydantic 锁定: https://github.com/gdsfactory/gdsfactory/issues
- SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- KLayout: https://www.klayout.de/
- KLayout Python API: https://www.klayout.org/doc-qt5/code/
- NumPy: https://numpy.org/doc/stable/
- SemVer: https://semver.org/
- Python sys.version_info: https://docs.python.org/3/library/sys.html
- Python packaging.version: https://packaging.pypa.io/en/stable/version.html

合规: R01 / R02 / R03 / R04 / R05 / R11。
"""

from __future__ import annotations

import logging
import re
import sys
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

__all__ = [
    "CompatibilityCheck",
    "CompatibilityLevel",
    "CompatibilityReport",
    "check_klayout_compatibility",
    "check_numpy_compatibility",
    "check_pdk_version_compatibility",
    "check_python_compatibility",
    "format_compatibility_report",
    "run_full_compatibility_check",
]


class CompatibilityLevel(str, Enum):
    """兼容性级别（R316）。

    来源: 借鉴 SemVer 兼容性矩阵
    https://semver.org/
    """

    OK = "ok"  # 完全兼容
    WARNING = "warning"  # 兼容但有警告
    ERROR = "error"  # 不兼容


@dataclass
class CompatibilityCheck:
    """单项兼容性检测结果（R316）。

    Attributes:
        name: 检测项名称（如 'python_version'）。
        level: 兼容性级别（OK/WARNING/ERROR）。
        current_version: 当前版本字符串。
        required_version: 要求版本字符串（None 表示无特定要求）。
        message: 检测结果描述（中文）。
        recommended_action: 建议操作（中文）。
    """

    name: str
    level: CompatibilityLevel
    current_version: str
    required_version: str | None = None
    message: str = ""
    recommended_action: str = ""


@dataclass
class CompatibilityReport:
    """完整兼容性报告（R316）。

    Attributes:
        checks: 各项检测结果列表。
        overall_level: 总体级别（取最严重级别）。
        passed: 是否通过（无 ERROR 级别）。
        timestamp: 报告时间戳（由调用方注入，便于测试）。
    """

    checks: list[CompatibilityCheck] = field(default_factory=list)
    overall_level: CompatibilityLevel = CompatibilityLevel.OK
    passed: bool = True
    timestamp: float = 0.0


# =============================================================================
# 版本字符串解析
# =============================================================================
def _parse_version(version_str: str) -> tuple[int, ...]:
    """解析版本字符串为整数元组（R316）。

    支持: "3.14.4" → (3, 14, 4)
          "1.26.0" → (1, 26, 0)
          "0.30.9" → (0, 30, 9)

    Args:
        version_str: 版本字符串（major.minor[.patch]）。

    Returns:
        整数元组。

    Raises:
        ValueError: 版本字符串格式无效。

    来源:
    - SemVer: https://semver.org/
    - Python packaging.version: https://packaging.pypa.io/en/stable/version.html
    """
    # 移除前导 'v' 和后缀（如 'v1.0.0rc1' → '1.0.0'）
    cleaned = re.sub(r"^v", "", version_str.strip())
    # 仅保留数字部分
    match = re.match(r"^(\d+)(\.\d+)*", cleaned)
    if not match:
        raise ValueError(
            f"版本字符串格式无效: {version_str!r}。"
            f"期望格式: major.minor[.patch]（如 '3.14.4'）。"
        )
    parts = match.group(0).split(".")
    return tuple(int(p) for p in parts)


def _compare_versions(v1: tuple[int, ...], v2: tuple[int, ...]) -> int:
    """比较两个版本元组。

    Returns: -1 if v1 < v2, 0 if v1 == v2, 1 if v1 > v2。
    """
    # 补齐到相同长度
    max_len = max(len(v1), len(v2))
    v1_pad = v1 + (0,) * (max_len - len(v1))
    v2_pad = v2 + (0,) * (max_len - len(v2))
    if v1_pad < v2_pad:
        return -1
    if v1_pad > v2_pad:
        return 1
    return 0


# =============================================================================
# 各维度兼容性检测
# =============================================================================
def check_python_compatibility() -> CompatibilityCheck:
    """检测 Python 版本兼容性（R316）。

    PoLaRIS 推荐 Python 3.10-3.13（gdsfactory 兼容性最佳）。
    Python 3.14 因 gdsfactory pydantic 锁定问题标记为 WARNING。

    Returns:
        CompatibilityCheck 检测结果。

    来源:
    - gdsfactory pydantic 锁定: https://github.com/gdsfactory/gdsfactory/issues
    - Python sys.version_info: https://docs.python.org/3/library/sys.html
    """
    py_version = (
        f"{sys.version_info.major}.{sys.version_info.minor}."
        f"{sys.version_info.micro}"
    )
    py_tuple = (sys.version_info.major, sys.version_info.minor)

    # 推荐 3.10-3.13
    if (3, 10) <= py_tuple <= (3, 13):
        return CompatibilityCheck(
            name="python_version",
            level=CompatibilityLevel.OK,
            current_version=py_version,
            required_version="3.10-3.13",
            message=f"Python {py_version} 在推荐范围内",
            recommended_action="无需操作",
        )
    if py_tuple >= (3, 14):
        return CompatibilityCheck(
            name="python_version",
            level=CompatibilityLevel.WARNING,
            current_version=py_version,
            required_version="3.10-3.13",
            message=(
                f"Python {py_version} 超出推荐范围，"
                f"gdsfactory 可能因 pydantic 锁定不可用"
            ),
            recommended_action=(
                "建议使用 Python 3.10-3.13 环境（推荐）。"
                "来源: https://gdsfactory.github.io/gdsfactory/"
            ),
        )
    # Python < 3.10
    return CompatibilityCheck(
        name="python_version",
        level=CompatibilityLevel.ERROR,
        current_version=py_version,
        required_version="3.10-3.13",
        message=(
            f"Python {py_version} 低于最低要求 3.10，"
            f"PoLaRIS 不支持"
        ),
        recommended_action="升级 Python 到 3.10 或更高版本",
    )


def check_klayout_compatibility() -> CompatibilityCheck:
    """检测 KLayout 版本兼容性（R316）。

    PoLaRIS 推荐 KLayout ≥ 0.28（Python API 稳定版本）。

    Returns:
        CompatibilityCheck 检测结果。

    Raises:
        ImportError: klayout 未安装。

    来源:
    - KLayout: https://www.klayout.de/
    - KLayout Python API: https://www.klayout.org/doc-qt5/code/
    """
    try:
        import klayout  # type: ignore[import-not-found]
    except ImportError as e:
        raise ImportError(
            "klayout 未安装，无法检测版本兼容性。"
            "安装方式: pip install klayout。"
            f"原始错误: {e}"
        ) from e
    kl_version = getattr(klayout, "__version__", "0.0.0")
    try:
        kl_tuple = _parse_version(kl_version)
    except ValueError as e:
        raise ValueError(
            f"klayout 版本字符串解析失败: {kl_version!r}: {e}"
        ) from e
    required = (0, 28)
    cmp = _compare_versions(kl_tuple[:2], required)
    if cmp >= 0:
        return CompatibilityCheck(
            name="klayout_version",
            level=CompatibilityLevel.OK,
            current_version=kl_version,
            required_version=">=0.28",
            message=f"KLayout {kl_version} 满足最低要求 0.28",
            recommended_action="无需操作",
        )
    return CompatibilityCheck(
        name="klayout_version",
        level=CompatibilityLevel.WARNING,
        current_version=kl_version,
        required_version=">=0.28",
        message=(
            f"KLayout {kl_version} 低于推荐版本 0.28，"
            f"Python API 可能不稳定"
        ),
        recommended_action="升级 KLayout 到 0.28 或更高版本",
    )


def check_numpy_compatibility() -> CompatibilityCheck:
    """检测 NumPy 版本兼容性（R316）。

    PoLaRIS 推荐 NumPy ≥ 1.24（R04 CPU-only 实现，避免 GPU 依赖）。

    Returns:
        CompatibilityCheck 检测结果。

    Raises:
        ImportError: numpy 未安装。

    来源:
    - NumPy: https://numpy.org/doc/stable/
    - R04 不参与 GPU: 项目规则
    """
    try:
        import numpy as np
    except ImportError as e:
        raise ImportError(
            "numpy 未安装，无法检测版本兼容性。"
            "numpy 为必装依赖。"
            f"原始错误: {e}"
        ) from e
    np_version = np.__version__
    try:
        np_tuple = _parse_version(np_version)
    except ValueError as e:
        raise ValueError(
            f"numpy 版本字符串解析失败: {np_version!r}: {e}"
        ) from e
    required = (1, 24)
    cmp = _compare_versions(np_tuple[:2], required)
    if cmp >= 0:
        return CompatibilityCheck(
            name="numpy_version",
            level=CompatibilityLevel.OK,
            current_version=np_version,
            required_version=">=1.24",
            message=f"NumPy {np_version} 满足最低要求 1.24",
            recommended_action="无需操作",
        )
    return CompatibilityCheck(
        name="numpy_version",
        level=CompatibilityLevel.ERROR,
        current_version=np_version,
        required_version=">=1.24",
        message=(
            f"NumPy {np_version} 低于最低要求 1.24，"
            f"PoLaRIS 可能不稳定"
        ),
        recommended_action="升级 NumPy 到 1.24 或更高版本",
    )


def check_pdk_version_compatibility(
    pdk_yaml_path: str | Any,
    supported_versions: list[str] | None = None,
) -> CompatibilityCheck:
    """检测 PDK YAML 版本字段兼容性（R316）。

    检查 PDK YAML 文件的 version 字段是否在支持列表中。

    Args:
        pdk_yaml_path: PDK YAML 文件路径，或已解析的 dict。
        supported_versions: 支持的版本列表（None 用默认 ['1.0.0']）。

    Returns:
        CompatibilityCheck 检测结果。

    Raises:
        FileNotFoundError: YAML 文件不存在。
        ValueError: YAML 无 version 字段 / 版本字符串无效。
        ImportError: yaml 未安装。

    来源:
    - PDK YAML schema: R309 yaml_pdk_config.py
    - SemVer: https://semver.org/
    """
    if supported_versions is None:
        supported_versions = ["1.0.0"]

    # 接受路径或 dict
    if isinstance(pdk_yaml_path, dict):
        data = pdk_yaml_path
    else:
        try:
            import yaml
        except ImportError as e:
            raise ImportError(
                f"yaml 未安装，无法解析 PDK YAML: {e}"
            ) from e
        from pathlib import Path

        path = Path(pdk_yaml_path)
        if not path.exists():
            raise FileNotFoundError(f"PDK YAML 文件不存在: {pdk_yaml_path}")
        with path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not isinstance(data, dict):
            raise ValueError(
                f"PDK YAML 顶层不是 dict: {type(data).__name__}"
            )

    if "version" not in data:
        raise ValueError(
            "PDK YAML 缺少 version 字段，必须包含版本号"
        )
    pdk_version = str(data["version"])
    try:
        _parse_version(pdk_version)  # 验证格式
    except ValueError as e:
        raise ValueError(
            f"PDK YAML version 字段无效: {pdk_version!r}: {e}"
        ) from e

    if pdk_version in supported_versions:
        return CompatibilityCheck(
            name="pdk_version",
            level=CompatibilityLevel.OK,
            current_version=pdk_version,
            required_version=f"in {supported_versions}",
            message=f"PDK 版本 {pdk_version} 在支持列表中",
            recommended_action="无需操作",
        )
    return CompatibilityCheck(
        name="pdk_version",
        level=CompatibilityLevel.WARNING,
        current_version=pdk_version,
        required_version=f"in {supported_versions}",
        message=(
            f"PDK 版本 {pdk_version} 不在支持列表 "
            f"{supported_versions} 中，可能存在兼容性问题"
        ),
        recommended_action=(
            "检查 PDK YAML 版本字段，或扩展 supported_versions 列表"
        ),
    )


# =============================================================================
# 端到端检测
# =============================================================================
def run_full_compatibility_check(
    pdk_yaml_path: str | Any | None = None,
    timestamp: float = 0.0,
) -> CompatibilityReport:
    """运行完整兼容性检测（R316）。

    Args:
        pdk_yaml_path: PDK YAML 文件路径或 dict（None 跳过 PDK 版本检测）。
        timestamp: 报告时间戳（由调用方注入，便于测试）。

    Returns:
        CompatibilityReport 完整报告。

    来源:
    - 端到端检测模式: Fowler 2002 PoEAA
    """
    checks: list[CompatibilityCheck] = []

    # Python 版本（必检）
    checks.append(check_python_compatibility())

    # NumPy 版本（必装依赖）
    try:
        checks.append(check_numpy_compatibility())
    except ImportError as e:
        raise ImportError(
            f"numpy 检测失败（必装依赖）: {e}"
        ) from e

    # KLayout 版本（可选依赖，未安装时跳过但记录 WARNING）
    try:
        checks.append(check_klayout_compatibility())
    except ImportError:
        checks.append(
            CompatibilityCheck(
                name="klayout_version",
                level=CompatibilityLevel.WARNING,
                current_version="未安装",
                required_version=">=0.28",
                message="klayout 未安装，DRC/GDSII 功能不可用",
                recommended_action="安装 klayout: pip install klayout",
            )
        )

    # PDK YAML 版本（可选）
    if pdk_yaml_path is not None:
        checks.append(check_pdk_version_compatibility(pdk_yaml_path))

    # 计算总体级别
    levels = [c.level for c in checks]
    if CompatibilityLevel.ERROR in levels:
        overall = CompatibilityLevel.ERROR
    elif CompatibilityLevel.WARNING in levels:
        overall = CompatibilityLevel.WARNING
    else:
        overall = CompatibilityLevel.OK

    return CompatibilityReport(
        checks=checks,
        overall_level=overall,
        passed=(overall != CompatibilityLevel.ERROR),
        timestamp=timestamp,
    )


# =============================================================================
# 报告渲染
# =============================================================================
def format_compatibility_report(
    report: CompatibilityReport,
    output_format: str = "text",
) -> str:
    """渲染兼容性报告（R316）。

    Args:
        report: 兼容性报告。
        output_format: 输出格式（'text' / 'markdown'）。

    Returns:
        报告字符串。

    Raises:
        TypeError: report 不是 CompatibilityReport。
        ValueError: output_format 不支持。

    来源:
    - CommonMark: https://spec.commonmark.org/
    """
    if not isinstance(report, CompatibilityReport):
        raise TypeError(
            f"report 必须是 CompatibilityReport，"
            f"得到 {type(report).__name__}"
        )
    fmt = output_format.lower()
    if fmt == "text":
        return _render_text(report)
    if fmt == "markdown":
        return _render_markdown(report)
    raise ValueError(
        f"不支持的 output_format: {output_format}。"
        f"支持: text / markdown。"
    )


def _render_text(report: CompatibilityReport) -> str:
    """渲染纯文本报告。"""
    lines: list[str] = []
    lines.append("=" * 60)
    lines.append("PoLaRIS 兼容性检测报告")
    lines.append("=" * 60)
    lines.append(f"总体级别: {report.overall_level.value.upper()}")
    lines.append(f"是否通过: {'是' if report.passed else '否'}")
    lines.append(f"检测项数: {len(report.checks)}")
    lines.append("")
    for c in report.checks:
        lines.append(f"[{c.level.value.upper()}] {c.name}")
        lines.append(f"  当前版本: {c.current_version}")
        if c.required_version:
            lines.append(f"  要求版本: {c.required_version}")
        lines.append(f"  说明: {c.message}")
        if c.recommended_action:
            lines.append(f"  建议: {c.recommended_action}")
        lines.append("")
    lines.append("=" * 60)
    return "\n".join(lines)


def _render_markdown(report: CompatibilityReport) -> str:
    """渲染 Markdown 报告。"""
    lines: list[str] = []
    lines.append("# PoLaRIS 兼容性检测报告")
    lines.append("")
    lines.append(f"**总体级别**: {report.overall_level.value.upper()}")
    lines.append(f"**是否通过**: {'是' if report.passed else '否'}")
    lines.append(f"**检测项数**: {len(report.checks)}")
    lines.append("")
    lines.append("## 检测详情")
    lines.append("")
    lines.append("| 级别 | 检测项 | 当前版本 | 要求版本 | 说明 |")
    lines.append("|------|--------|----------|----------|------|")
    for c in report.checks:
        req = c.required_version or "-"
        msg = c.message.replace("|", "\\|")
        lines.append(
            f"| {c.level.value.upper()} | {c.name} | "
            f"{c.current_version} | {req} | {msg} |"
        )
    lines.append("")
    return "\n".join(lines)
