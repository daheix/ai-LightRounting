#!/usr/bin/env python3
"""3dtool/ensure_env.py — Python 环境自动检查与恢复（供 AI 工具调用前自动触发）

用途：在 Python 进程内检查环境，缺失则调用 ensure_env.sh 自动恢复。
      可被 conftest.py / CLI 入口 / 其他脚本 import 调用。

使用方式：
    # 1. 直接运行（检查并恢复）
    python 3dtool/ensure_env.py

    # 2. 作为模块导入（静默检查）
    from ensure_env import ensure_environment
    if not ensure_environment():
        raise RuntimeError("环境恢复失败")

自动触发条件：
    1. /tmp/.3dtool_installed 标记不存在（沙箱重启后）
    2. 关键依赖导入失败
    3. 开发工具不可用
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_DIR = SCRIPT_DIR.parent
MARK_FILE = Path("/tmp/.3dtool_installed")
ENSURE_SH = SCRIPT_DIR / "ensure_env.sh"

# 关键依赖（导入失败则触发恢复）
CRITICAL_DEPS = [
    "lark",
    "pydantic",
    "shapely",
    "scipy",
    "rtree",
    "openpyxl",
    "reportlab",
    "olefile",
    "unlzw3",
]


def _mark_exists() -> bool:
    """检查标记文件是否存在且非空。"""
    return MARK_FILE.is_file() and MARK_FILE.stat().st_size > 0


def _deps_ok() -> bool:
    """检查关键依赖是否可导入。"""
    for mod in CRITICAL_DEPS:
        try:
            __import__(mod)
        except ImportError:
            return False
    return True


def _tools_ok() -> bool:
    """检查开发工具是否可用。"""
    try:
        subprocess.run(
            ["python", "-c", "import pytest, ruff"],  # noqa: S603, S607
            capture_output=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False
    return True


def ensure_environment(verbose: bool = False) -> bool:
    """检查环境，缺失则自动恢复。

    Args:
        verbose: 是否输出详细日志

    Returns:
        True 表示环境正常（已安装或恢复成功），False 表示恢复失败
    """
    # 三重检查：标记 + 依赖 + 工具
    if _mark_exists() and _deps_ok() and _tools_ok():
        if verbose:
            print(f"[ensure_env] 环境正常（标记: {MARK_FILE.read_text().strip()}）")
        return True

    if verbose:
        print("[ensure_env] 环境缺失，自动执行 ensure_env.sh ...")

    if not ENSURE_SH.is_file():
        print(f"[ensure_env][ERROR] ensure_env.sh 不存在: {ENSURE_SH}", file=sys.stderr)
        return False

    result = subprocess.run(  # noqa: S603
        ["bash", str(ENSURE_SH)],
        cwd=str(REPO_DIR),
        capture_output=not verbose,
        text=True,
    )
    if result.returncode != 0:
        print(f"[ensure_env][ERROR] ensure_env.sh 失败 (exit={result.returncode})", file=sys.stderr)
        if not verbose:
            print(result.stdout, file=sys.stdout)
            print(result.stderr, file=sys.stderr)
        return False

    if verbose:
        print("[ensure_env] 环境已自动恢复")
    return True


def main() -> int:
    """命令行入口。"""
    verbose = "-v" in sys.argv or "--verbose" in sys.argv
    return 0 if ensure_environment(verbose=verbose) else 1


if __name__ == "__main__":
    sys.exit(main())
