#!/usr/bin/env python3
"""PoLaRIS PyInstaller 入口点 — 单文件可执行程序的启动脚本。

本文件作为 PyInstaller 打包的入口点，被编译进单文件可执行程序 `polaris`。
所有实际逻辑位于 `polaris_orchestrator.cli.main()`，已被 Cython 预编译为
.so 二进制模块，源代码不随可执行程序分发。

## 设计原则

- 入口点极简：仅做 sys.path 修补 + 委托调用
- 不含任何业务逻辑（业务逻辑全部在 .so 中）
- 错误码透传：main() 返回的 int 直接作为进程退出码

## 退出码定义

- 0: 成功
- 1: EDA 流水线有 stage 失败 / 未指定子命令
- 2: FileNotFoundError（电路/配置文件不存在）
- 3: ValueError（参数错误）
- 4: RuntimeError（运行时错误）
- 5: 其他未预期错误

## 来源（R02 学术诚信）

- PyInstaller 入口点文档: https://pyinstaller.org/en/stable/spec-files.html
- Python sys.exit 文档: https://docs.python.org/3/library/sys.html#sys.exit
- setuptools 入口点模式: https://packaging.python.org/en/latest/specifications/entry-points/

*创新*: 入口点与业务逻辑完全分离，配合 Cython 编译实现"入口可见、
逻辑不可见"的源代码保护模式，对标商业 EDA 工具的发布形态。
"""

from __future__ import annotations

import sys


def _setup_path() -> None:
    """PyInstaller 单文件模式下修补 sys.path。

    PyInstaller --onefile 模式在运行时将打包内容解压到临时目录
    ``sys._MEIPASS``，需要将该目录加入 sys.path 以便导入 .so 模块。
    在非 PyInstaller 环境（开发模式）下此函数为 no-op。
    """
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass and meipass not in sys.path:
        sys.path.insert(0, meipass)


def main() -> int:
    """入口主函数。"""
    _setup_path()
    # 延迟导入：确保 sys.path 修补完成后再加载 .so 模块
    from polaris_orchestrator.cli import main as cli_main
    return cli_main()


if __name__ == "__main__":
    sys.exit(main())
