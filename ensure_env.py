#!/usr/bin/env python3
"""PoLaRIS/ensure_env.py — Python 环境自动检查与恢复（供 AI 工具调用前自动触发）

标准：参照 3dtool 子仓库 ensure_env.py 四文件模式
      标记文件 / CRITICAL_DEPS 列表 / 三重检查 / 自动触发 install.sh

用途：在 Python 进程内检查环境，缺失则调用 ensure_env.sh 自动恢复。
      可被 conftest.py / CLI 入口 / 其他脚本 import 调用。

使用方式：
    # 1. 直接运行（检查并恢复）
    python ensure_env.py

    # 2. 作为模块导入（静默检查）
    from ensure_env import ensure_environment
    if not ensure_environment():
        raise RuntimeError("环境恢复失败")

自动触发条件（任一失败即恢复）：
    1. /tmp/.polaris_installed 标记不存在（沙箱重启后）
    2. 关键依赖导入失败（numpy/scipy/jax/sax/klayout 等）
    3. 开发工具不可用（pytest/ruff）
    4. PoLaRIS 核心模块不可导入（polaris_core）

规则依据：
    R03 禁止 fall-back：失败即 raise，不静默兜底
    R04 不参与 GPU：jax 只检查 CPU 平台
    R11 工作流规范
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_DIR = SCRIPT_DIR
MARK_FILE = Path("/tmp/.polaris_installed")
ENSURE_SH = SCRIPT_DIR / "ensure_env.sh"

# 关键依赖（导入失败则触发恢复）
# 依赖来源：PoLaRIS 33 模块共用核心依赖 + R04 CPU 战略
#   - numpy/scipy/networkx/matplotlib：数值计算与图论
#   - yaml：配置
#   - jax/jaxlib：自动微分（CPU 版，R04 合规）
#   - sax：电路仿真
#   - klayout：版图（模块名 klayout）
#   - gymnasium：强化学习
#   - shapely：几何
#   - pydantic：数据模型
CRITICAL_DEPS = [
    "numpy",
    "scipy",
    "networkx",
    "matplotlib",
    "yaml",          # pyyaml 的导入名
    "jax",
    "jaxlib",
    "sax",
    "klayout",
    "gymnasium",
    "shapely",
    "pydantic",
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
    """检查开发工具是否可用（pytest + ruff）。"""
    try:
        subprocess.run(
            ["python", "-c", "import pytest"],  # noqa: S603, S607
            capture_output=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False
    # ruff 检查（ruff 既是命令也是模块）
    try:
        subprocess.run(
            ["python", "-c", "import ruff"],  # noqa: S603, S607
            capture_output=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False
    return True


def _polaris_ok() -> bool:
    """检查 PoLaRIS 核心模块是否可导入。"""
    try:
        __import__("polaris_core")
    except ImportError:
        return False
    return True


def ensure_environment(verbose: bool = False) -> bool:
    """检查环境，缺失则自动恢复。

    Args:
        verbose: 是否输出详细日志

    Returns:
        True 表示环境正常（已安装或恢复成功），False 表示恢复失败

    规则依据：R03 禁止 fall-back — 恢复失败返回 False，由调用方决定是否 raise
    """
    # 四重检查：标记 + 依赖 + 工具 + PoLaRIS 模块
    if _mark_exists() and _deps_ok() and _tools_ok() and _polaris_ok():
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
