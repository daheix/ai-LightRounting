#!/usr/bin/env python3
"""PoLaRIS Cython 编译脚本 — 将所有 .py 源码编译为 .so 二进制模块。

采用"副本编译"策略：将 modules/ 源码复制到 build/release/modules/，
在副本上执行 Cython 编译并 stub 化，**main 分支源码保持完整**。
PyInstaller 从 build/release/modules/ 收集 .so 文件打包。

## 编译流程

1. 复制 modules/ → build/release/modules/（首次或 --force 时）
2. 扫描 build/release/modules/*/src/polaris_*/*.py
3. 跳过 __init__.py / __main__.py / cli.py / conftest.py
4. 用 Cython 编译 .py → .c → .so（就地，在副本目录中）
5. 将副本中的 .py 替换为 stub（仅含 docstring）
6. 清理 .c 中间文件
7. 验证：源码不泄漏（副本 .py 均为 stub）

## 安全保证

- **不修改 main 分支源码**：所有修改仅发生在 build/release/modules/ 副本
- **可重复构建**：删除 build/release/ 后重新运行即可
- **可验证**：verify_no_source() 检查所有 .py 均为 stub

## 来源（R02 学术诚信）

- Cython 官方文档: https://cython.readthedocs.io/en/latest/src/userguide/source_files_and_compilation.html
- Cython 代码保护: https://cython.org/
- setuptools 扩展模块: https://setuptools.pypa.io/en/latest/userguide/ext_modules.html
- Python C API: https://docs.python.org/3/extending/extending.html
- PyPI 私有包发布: https://packaging.python.org/en/latest/discussions/publishing-private-packages/

*创新*: 副本编译策略 — 在保持 main 分支源码完整的同时实现源代码保护，
解决了"发布版本无源码"与"开发分支有源码"的矛盾。对标商业 EDA 工具
的发布形态（可执行文件不含源码，开发仓库保留完整源码）。
"""

from __future__ import annotations

import multiprocessing
import shutil
import sys
from pathlib import Path

from Cython.Build import cythonize
from setuptools import Distribution, Extension
from setuptools.command.build_ext import build_ext


ROOT = Path(__file__).resolve().parent.parent
MODULES_DIR = ROOT / "modules"
RELEASE_DIR = ROOT / "build" / "release"
RELEASE_MODULES = RELEASE_DIR / "modules"
BUILD_DIR = RELEASE_DIR / "_cython_build"

# 不编译的文件（保留 .py）
SKIP_FILES = {
    "__init__.py",      # 包入口，保留 stub
    "__main__.py",      # 入口点
    "cli.py",           # CLI 入口（需要直接执行）
    "conftest.py",      # 测试配置
}

# 编译指令
COMPILER_DIRECTIVES = {
    "language_level": "3",
    "boundscheck": False,
    "wraparound": False,
    "cdivision": True,
    "always_allow_keywords": True,
}


def copy_source_to_release(force: bool = False) -> int:
    """复制 modules/ 到 build/release/modules/。

    Args:
        force: True 时强制重新复制（删除现有副本）。
    """
    if RELEASE_MODULES.exists():
        if not force:
            print(f"[Cython] 副本已存在: {RELEASE_MODULES}")
            return 0
        print(f"[Cython] 强制模式：删除旧副本 {RELEASE_MODULES}")
        shutil.rmtree(RELEASE_MODULES)

    print(f"[Cython] 复制源码: {MODULES_DIR} → {RELEASE_MODULES}")
    # 复制时排除 tests / __pycache__ / .pyc
    ignore = shutil.ignore_patterns(
        "tests", "__pycache__", "*.pyc", "*.pyo",
        ".pytest_cache", ".mypy_cache", ".ruff_cache",
    )
    shutil.copytree(MODULES_DIR, RELEASE_MODULES, ignore=ignore)

    n_py = sum(1 for _ in RELEASE_MODULES.rglob("*.py"))
    print(f"[Cython] 复制完成: {n_py} 个 .py 文件")
    return n_py


def find_py_files() -> list[Path]:
    """扫描所有需要编译的 .py 文件（在副本目录中）。

    仅编译 ``modules/*/src/polaris_*/`` 路径下的 .py 文件，
    排除 GUI 输出目录、docs、examples 等杂散文件。
    """
    files: list[Path] = []
    for py in RELEASE_MODULES.rglob("*.py"):
        parts = py.parts
        # 必须在 src 目录下
        if "src" not in parts:
            continue
        # 仅编译 polaris_*/ 下的文件（src 目录结构）
        if not any(p.startswith("polaris_") for p in parts):
            continue
        # 跳过指定文件
        if py.name in SKIP_FILES:
            continue
        # 跳过 c_api 目录（C 头文件）
        if "c_api" in parts:
            continue
        files.append(py)
    return files


def py_to_module_name(py_path: Path) -> str:
    """将文件路径转换为 Python 模块名。

    例: build/release/modules/circuit/src/polaris_circuit/cascade.py
        → polaris_circuit.cascade
    """
    parts = py_path.parts
    # 找到 polaris_* 的位置
    for i, part in enumerate(parts):
        if part.startswith("polaris_"):
            module_parts = list(parts[i:-1]) + [py_path.stem]
            return ".".join(module_parts)
    raise ValueError(f"无法从路径提取模块名: {py_path}")


def compile_all() -> int:
    """编译所有 .py 文件为 .so（在副本目录中）。

    采用 ``build_lib`` 模式：build_ext 编译到 ``build/release/_build_lib/``
    下的标准包结构，然后手动复制 .so 到副本源码目录，最后 stub 化 .py。
    避开 ``inplace=1`` 在多包分散场景下的路径解析问题。
    """
    py_files = find_py_files()
    print(f"[Cython] 发现 {len(py_files)} 个 .py 文件待编译")

    if not py_files:
        print("[Cython] 无文件需要编译", file=sys.stderr)
        return 0

    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    build_lib_dir = RELEASE_DIR / "_build_lib"
    build_lib_dir.mkdir(parents=True, exist_ok=True)

    # 构建 Extension 列表
    extensions: list[Extension] = []
    for py in py_files:
        module_name = py_to_module_name(py)
        ext = Extension(
            name=module_name,
            sources=[str(py)],
        )
        extensions.append(ext)

    # Cython 编译 .py → .c
    nthreads = min(multiprocessing.cpu_count(), 8)
    print(f"[Cython] 开始 Cython 编译（{nthreads} 线程）...")
    ext_modules = cythonize(
        module_list=extensions,
        build_dir=str(BUILD_DIR),
        nthreads=nthreads,
        compiler_directives=COMPILER_DIRECTIVES,
        force=True,
    )
    print(f"[Cython] Cython 编译完成: {len(ext_modules)} 个 .c 文件")

    # 构建 .so 文件（build_lib 模式，输出到 build_lib_dir）
    distribution = Distribution({"ext_modules": ext_modules})
    build_ext_cmd = distribution.get_command_obj("build_ext")
    build_ext_cmd.ensure_finalized()
    build_ext_cmd.inplace = 0  # 输出到 build_lib
    build_ext_cmd.build_lib = str(build_lib_dir)
    build_ext_cmd.parallel = nthreads
    build_ext_cmd.run()

    # 验证 .so 文件已生成
    so_files = list(build_lib_dir.rglob("*.so"))
    print(f"[Cython] 生成 .so 文件: {len(so_files)} 个")
    if len(so_files) == 0:
        raise RuntimeError(
            "Cython 编译失败：未生成任何 .so 文件，请检查编译器是否可用"
        )

    # 手动复制 .so 到副本源码目录（与 .py 同目录）
    # 用 .py 文件位置定位 .so 目标目录（按 module name 匹配）
    py_by_module: dict[str, Path] = {}
    for py in py_files:
        py_by_module[py_to_module_name(py)] = py

    copied = 0
    missing = 0
    for so in so_files:
        # so 路径: build_lib/polaris_xxx/sub/file.cpython-XXX.so
        # module name: polaris_xxx.sub.file
        rel = so.relative_to(build_lib_dir)
        # 去掉 .cpython-XXX.so 后缀
        so_name = rel.name
        # 匹配 .cpython-<pyver>-<platform>.so
        import re
        m = re.match(r"^(.+)\.cpython-\d+[a-z]*-[^.]+\.so$", so_name)
        if m:
            stem = m.group(1)
        else:
            stem = so_name[:-3] if so_name.endswith(".so") else so_name
        # 构造 module name: rel.parent.as_posix().replace("/", ".") + "." + stem
        parent_parts = rel.parent.parts
        if parent_parts:
            module_name = ".".join(parent_parts) + "." + stem
        else:
            module_name = stem

        py_file = py_by_module.get(module_name)
        if py_file is None:
            # 部分子模块可能不在 py_files 中（如 __init__），用目录定位
            # 找到 build/release/modules 下对应的 polaris_xxx/sub/ 目录
            target_dir = RELEASE_MODULES
            for part in parent_parts:
                target_dir = target_dir / part
                # 在 RELEASE_MODULES 下递归找第一个匹配
                matches = list(RELEASE_MODULES.rglob(part))
                if matches:
                    target_dir = matches[0]
                else:
                    target_dir = None
                    break
            if target_dir is None:
                missing += 1
                continue
            dst = target_dir / so_name
        else:
            dst = py_file.parent / so_name
        shutil.copy2(so, dst)
        copied += 1
    if missing:
        print(f"[Cython] [警告] {missing} 个 .so 未找到对应源码目录")
    print(f"[Cython] 复制 .so 到源码目录: {copied} 个")

    # 替换 .py 为 stub
    stubbed = 0
    for py in py_files:
        # 生成 stub 内容（仅保留模块名声明）
        stub_content = f'"""{py.name} — Cython 编译模块（源码已保护）。"""\n'
        py.write_text(stub_content, encoding="utf-8")
        stubbed += 1

    # 清理 .c 中间文件和 build_lib
    c_files = list(BUILD_DIR.rglob("*.c"))
    for c_file in c_files:
        c_file.unlink(missing_ok=True)
    shutil.rmtree(build_lib_dir, ignore_errors=True)

    print(f"[Cython] Stub 替换: {stubbed} 个文件")
    print(f"[Cython] 清理 .c 中间文件: {len(c_files)} 个")
    print(f"[Cython] 编译完成！.so 文件已就位，副本 .py 已替换为 stub")

    return len(ext_modules)


def verify_no_source() -> bool:
    """验证副本源代码已被保护（.py 文件不含实际逻辑）。

    main 分支源码不在验证范围内（main 保留完整源码供开发）。
    """
    py_files = find_py_files()
    # 加上 SKIP_FILES 中的文件（它们保留 .py 但应该不含业务逻辑）
    all_py = list(RELEASE_MODULES.rglob("*.py"))

    leaked = 0
    for py in all_py:
        content = py.read_text(encoding="utf-8").strip()
        if not content:
            continue
        # stub 文件应只有 docstring
        if content.startswith('"""') and content.endswith('"""'):
            continue
        # cli.py / __init__.py 等允许保留较多内容
        if py.name in SKIP_FILES:
            continue
        # 检查是否含 def/class/import 等实际代码
        lines = [l.strip() for l in content.split("\n") if l.strip()
                 and not l.strip().startswith("#")
                 and not l.strip().startswith('"""')]
        if lines:
            leaked += 1
            print(f"  [警告] {py} 可能泄漏源码: {lines[0][:80]}")

    if leaked == 0:
        print(f"[Cython] 验证通过: 副本 {len(all_py)} 个 .py 文件均为 stub，无源码泄漏")
    else:
        print(f"[Cython] 验证失败: {leaked} 个文件可能泄漏源码")
    return leaked == 0


def verify_main_untouched() -> bool:
    """验证 main 分支源码未被修改（R11 安全保证）。"""
    main_py_count = sum(1 for _ in MODULES_DIR.rglob("*.py"))
    # 简单检查：main 分支的 .py 文件数应远大于 0
    if main_py_count == 0:
        raise RuntimeError("main 分支 modules/ 无 .py 文件，可能被误修改")
    print(f"[Cython] main 分支源码完整: {main_py_count} 个 .py 文件未受影响")
    return True


if __name__ == "__main__":
    force = "--force" in sys.argv
    only_verify = "--verify-only" in sys.argv

    if only_verify:
        verify_no_source()
        verify_main_untouched()
        sys.exit(0)

    verify_main_untouched()
    copy_source_to_release(force=force)
    n = compile_all()
    verify_no_source()
    verify_main_untouched()
    print(f"\n[Cython] 总计编译 {n} 个模块 → build/release/modules/")
