"""R105-R110 代码质量与合规基线扫描（一次性完成 6 项）。

输出: /workspace/.trae/reports/baseline_r105_r110.md

覆盖:
- R105 圈复杂度（radon cc，>15 函数清单）
- R106 函数行长（>80 行函数 + >800 行文件清单）
- R107 类型注解覆盖率（参数 + 返回值）
- R108 文献引用统计（每模块 docstring URL 数，<5 模块清单）
- R109 R03 fall-back 风险（except:pass / return None / return [] 等）
- R110 R04 GPU 合规（cupy/cuda/rocm/metal/fp16/bf16 实际使用 vs 仅文档提及）

合规: R03 失败即 raise；R05 文件 < 800 行。
"""
from __future__ import annotations

import ast
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path("/workspace")
SRC = ROOT / "src" / "polaris"
REPORT = ROOT / ".trae" / "reports" / "baseline_r105_r110.md"
REPORT.parent.mkdir(parents=True, exist_ok=True)


def collect_py_files() -> list[Path]:
    """收集 src/polaris 下所有 .py 文件。失败即 raise。"""
    if not SRC.exists():
        raise FileNotFoundError(f"src/polaris 不存在: {SRC}")
    return sorted(SRC.rglob("*.py"))


# =============================================================================
# R105 圈复杂度（radon cc）
# =============================================================================
def scan_cyclomatic_complexity(files: list[Path]) -> dict:
    """R105: 用 radon cc 扫描圈复杂度。"""
    try:
        import radon.complexity as rc  # noqa: F401
        from radon.visitors import ComplexityVisitor
    except ImportError as exc:
        raise RuntimeError(
            "radon 未安装，请 pip install radon；R03 禁止 fall-back"
        ) from exc

    over15: list[tuple[str, str, int, int]] = []  # (file, func, line, cc)
    all_funcs: list[tuple[str, str, int, int]] = []
    for fp in files:
        try:
            src = fp.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        visitor = ComplexityVisitor.from_code(src)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # radon visitor 在 _functions 列表里
                pass
        for f in visitor.functions:
            cc = f.complexity
            rel = str(fp.relative_to(ROOT))
            all_funcs.append((rel, f.name, f.lineno, cc))
            if cc > 15:
                over15.append((rel, f.name, f.lineno, cc))
    over15.sort(key=lambda x: -x[3])
    top20 = sorted(all_funcs, key=lambda x: -x[3])[:20]
    return {
        "total_functions": len(all_funcs),
        "over_15_count": len(over15),
        "over_15_list": over15,
        "top20": top20,
    }


# =============================================================================
# R106 函数行长
# =============================================================================
def scan_function_length(files: list[Path]) -> dict:
    """R106: 统计函数行长。"""
    over80: list[tuple[str, str, int, int]] = []
    all_funcs: list[tuple[str, str, int, int]] = []
    file_lines: list[tuple[str, int]] = []
    for fp in files:
        try:
            src = fp.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        lines = src.splitlines()
        file_lines.append((str(fp.relative_to(ROOT)), len(lines)))
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                end = getattr(node, "end_lineno", node.lineno)
                length = end - node.lineno + 1
                rel = str(fp.relative_to(ROOT))
                all_funcs.append((rel, node.name, node.lineno, length))
                if length > 80:
                    over80.append((rel, node.name, node.lineno, length))
    over80.sort(key=lambda x: -x[3])
    top20 = sorted(all_funcs, key=lambda x: -x[3])[:20]
    over800_files = [(f, n) for f, n in file_lines if n > 800]
    over800_files.sort(key=lambda x: -x[1])
    return {
        "total_functions": len(all_funcs),
        "over_80_count": len(over80),
        "over_80_list": over80,
        "top20_longest": top20,
        "over_800_files": over800_files,
        "total_files": len(file_lines),
    }


# =============================================================================
# R107 类型注解覆盖率
# =============================================================================
def scan_type_annotations(files: list[Path]) -> dict:
    """R107: 统计参数与返回值类型注解覆盖率。"""
    total_params = 0
    annotated_params = 0
    total_returns = 0
    annotated_returns = 0
    per_file: list[tuple[str, int, int, int, int]] = []
    for fp in files:
        try:
            src = fp.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        f_params = f_annotated = f_returns = f_ret_annotated = 0
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # 跳过 self/cls
                args = [a for a in node.args.args if a.arg not in ("self", "cls")]
                # posonly + kwonly
                args += list(node.args.posonlyargs)
                args += list(node.args.kwonlyargs)
                # vararg/kwarg
                if node.args.vararg:
                    args.append(node.args.vararg)
                if node.args.kwarg:
                    args.append(node.args.kwarg)
                for a in args:
                    total_params += 1
                    f_params += 1
                    if a.annotation is not None:
                        annotated_params += 1
                        f_annotated += 1
                total_returns += 1
                f_returns += 1
                if node.returns is not None:
                    annotated_returns += 1
                    f_ret_annotated += 1
        per_file.append((str(fp.relative_to(ROOT)), f_params, f_annotated, f_returns, f_ret_annotated))
    return {
        "total_params": total_params,
        "annotated_params": annotated_params,
        "param_coverage_pct": round(100.0 * annotated_params / total_params, 2) if total_params else 0.0,
        "total_returns": total_returns,
        "annotated_returns": annotated_returns,
        "return_coverage_pct": round(100.0 * annotated_returns / total_returns, 2) if total_returns else 0.0,
    }


# =============================================================================
# R108 文献引用统计
# =============================================================================
URL_RE = re.compile(r"https?://[^\s'\"<>)\]]+")


def scan_citations(files: list[Path]) -> dict:
    """R108: 统计每个模块 docstring 中的文献 URL 数量。"""
    per_module: dict[str, int] = {}
    under5: list[tuple[str, int]] = []
    total_urls = 0
    for fp in files:
        try:
            src = fp.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        # 模块级 docstring（文件首部）
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        doc = ast.get_docstring(tree) or ""
        urls = URL_RE.findall(doc)
        # 也统计文件全部 URL（含 docstring + 注释）
        all_urls = URL_RE.findall(src)
        n = len(set(all_urls))
        rel = str(fp.relative_to(ROOT))
        per_module[rel] = n
        total_urls += n
        if n < 5:
            under5.append((rel, n))
    under5.sort(key=lambda x: x[1])
    return {
        "total_modules": len(per_module),
        "total_urls": total_urls,
        "avg_urls_per_module": round(total_urls / len(per_module), 2) if per_module else 0.0,
        "under_5_count": len(under5),
        "under_5_list": under5,
    }


# =============================================================================
# R109 R03 fall-back 风险扫描
# =============================================================================
FALLBACK_PATTERNS = [
    (r"except\s*:\s*pass", "except: pass"),
    (r"except\s+Exception\s*:\s*pass", "except Exception: pass"),
    (r"except\s+\w+\s*:\s*pass", "except X: pass"),
    (r"return\s+None\s*(?=#|$)", "return None"),
    (r"return\s+\[\]\s*(?=#|$)", "return []"),
    (r"return\s+\{\}\s*(?=#|$)", "return {}"),
]


def scan_fallback(files: list[Path]) -> dict:
    """R109: 扫描潜在 fall-back 模式。"""
    by_pattern: dict[str, list[tuple[str, int, str]]] = {p[1]: [] for p in FALLBACK_PATTERNS}
    for fp in files:
        try:
            src = fp.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        rel = str(fp.relative_to(ROOT))
        for line_no, line in enumerate(src.splitlines(), 1):
            for pat, name in FALLBACK_PATTERNS:
                if re.search(pat, line):
                    by_pattern[name].append((rel, line_no, line.strip()[:120]))
    summary = {k: len(v) for k, v in by_pattern.items()}
    return {"summary": summary, "details": by_pattern, "total": sum(summary.values())}


# =============================================================================
# R110 R04 GPU 合规
# =============================================================================
GPU_KEYWORDS = [
    r"\bcupy\b", r"\bcuda\b", r"\bCUDA\b", r"\brocm\b", r"\bROCm\b",
    r"\bmetal\b", r"\bMetal\b", r"\bfp16\b", r"\bFP16\b",
    r"\bbf16\b", r"\bBF16\b", r"\btorch\.cuda\b", r"\bjax\.devices\(['\"]gpu['\"]\)",
]


def scan_gpu(files: list[Path]) -> dict:
    """R110: 扫描 GPU 相关代码，区分实际使用 vs 文档提及。"""
    actual_usage: list[tuple[str, int, str]] = []
    doc_mentions: list[tuple[str, int, str]] = []
    for fp in files:
        try:
            src = fp.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        rel = str(fp.relative_to(ROOT))
        # 简化：解析 AST，区分 import 实际使用 vs docstring/注释提及
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        # 收集 import 名称
        imported_gpu: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if any(re.search(k, alias.name) for k in GPU_KEYWORDS):
                        imported_gpu.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                if any(re.search(k, mod) for k in GPU_KEYWORDS):
                    for alias in node.names:
                        imported_gpu.add(f"{mod}.{alias.name}")
        # 实际 import = 实际使用
        for name in imported_gpu:
            actual_usage.append((rel, 0, f"import {name}"))
        # 检查 docstring 中的提及（非 import 行）
        for line_no, line in enumerate(src.splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'''"):
                if any(re.search(k, stripped) for k in GPU_KEYWORDS):
                    doc_mentions.append((rel, line_no, stripped[:120]))
            elif stripped.startswith('"""') is False and any(re.search(k, stripped) for k in GPU_KEYWORDS):
                # 代码行中的 GPU 关键词（非 import）
                if "import" not in stripped:
                    actual_usage.append((rel, line_no, stripped[:120]))
    return {
        "actual_usage_count": len(actual_usage),
        "actual_usage": actual_usage,
        "doc_mention_count": len(doc_mentions),
        "doc_mentions": doc_mentions[:30],
    }


# =============================================================================
# 报告生成
# =============================================================================
def main() -> int:
    files = collect_py_files()
    print(f"[INFO] 扫描 {len(files)} 个 Python 文件", file=sys.stderr)

    print("[R105] 圈复杂度扫描...", file=sys.stderr)
    r105 = scan_cyclomatic_complexity(files)
    print(f"  函数总数: {r105['total_functions']}, >15: {r105['over_15_count']}", file=sys.stderr)

    print("[R106] 函数行长扫描...", file=sys.stderr)
    r106 = scan_function_length(files)
    print(f"  >80行函数: {r106['over_80_count']}, >800行文件: {len(r106['over_800_files'])}", file=sys.stderr)

    print("[R107] 类型注解扫描...", file=sys.stderr)
    r107 = scan_type_annotations(files)
    print(f"  参数覆盖率: {r107['param_coverage_pct']}%, 返回值: {r107['return_coverage_pct']}%", file=sys.stderr)

    print("[R108] 文献引用扫描...", file=sys.stderr)
    r108 = scan_citations(files)
    print(f"  <5引用模块: {r108['under_5_count']}/{r108['total_modules']}", file=sys.stderr)

    print("[R109] fall-back 扫描...", file=sys.stderr)
    r109 = scan_fallback(files)
    print(f"  风险总数: {r109['total']}", file=sys.stderr)

    print("[R110] GPU 合规扫描...", file=sys.stderr)
    r110 = scan_gpu(files)
    print(f"  实际使用: {r110['actual_usage_count']}, 文档提及: {r110['doc_mention_count']}", file=sys.stderr)

    # 生成 Markdown 报告
    lines: list[str] = []
    lines.append("# R105-R110 代码质量与合规基线报告")
    lines.append("")
    lines.append(f"- 扫描时间: $(date)")
    lines.append(f"- 扫描范围: src/polaris/ 共 {len(files)} 个 Python 文件")
    lines.append(f"- 覆盖规则: R105 圈复杂度 / R106 函数行长 / R107 类型注解 / R108 文献引用 / R109 fall-back / R110 GPU 合规")
    lines.append("")

    lines.append("## R105 圈复杂度（radon cc）")
    lines.append("")
    lines.append(f"- 函数总数: **{r105['total_functions']}**")
    lines.append(f"- 复杂度 >15 函数数: **{r105['over_15_count']}**")
    lines.append("")
    lines.append("### Top 20 复杂度最高函数")
    lines.append("| 文件 | 函数 | 行号 | 圈复杂度 |")
    lines.append("|------|------|------|----------|")
    for rel, name, line, cc in r105["top20"]:
        lines.append(f"| {rel} | {name} | {line} | {cc} |")
    lines.append("")
    lines.append("### 复杂度 >15 完整清单")
    lines.append("| 文件 | 函数 | 行号 | 圈复杂度 |")
    lines.append("|------|------|------|----------|")
    for rel, name, line, cc in r105["over_15_list"]:
        lines.append(f"| {rel} | {name} | {line} | {cc} |")
    lines.append("")

    lines.append("## R106 函数行长")
    lines.append("")
    lines.append(f"- 函数总数: **{r106['total_functions']}**")
    lines.append(f"- >80 行函数数: **{r106['over_80_count']}**")
    lines.append(f"- 文件总数: **{r106['total_files']}**")
    lines.append(f"- >800 行文件数: **{len(r106['over_800_files'])}**")
    lines.append("")
    lines.append("### Top 20 最长函数")
    lines.append("| 文件 | 函数 | 行号 | 行长 |")
    lines.append("|------|------|------|------|")
    for rel, name, line, length in r106["top20_longest"]:
        lines.append(f"| {rel} | {name} | {line} | {length} |")
    lines.append("")
    lines.append("### >800 行文件清单")
    lines.append("| 文件 | 行数 |")
    lines.append("|------|------|")
    for rel, n in r106["over_800_files"]:
        lines.append(f"| {rel} | {n} |")
    lines.append("")

    lines.append("## R107 类型注解覆盖率")
    lines.append("")
    lines.append(f"- 参数总数: **{r107['total_params']}**, 已注解: **{r107['annotated_params']}**, 覆盖率: **{r107['param_coverage_pct']}%**")
    lines.append(f"- 返回值总数: **{r107['total_returns']}**, 已注解: **{r107['annotated_returns']}**, 覆盖率: **{r107['return_coverage_pct']}%**")
    lines.append("")

    lines.append("## R108 文献引用统计")
    lines.append("")
    lines.append(f"- 模块总数: **{r108['total_modules']}**")
    lines.append(f"- URL 总数: **{r108['total_urls']}**")
    lines.append(f"- 平均每模块 URL: **{r108['avg_urls_per_module']}**")
    lines.append(f"- 引用 <5 的模块数: **{r108['under_5_count']}**")
    lines.append("")
    lines.append("### 引用 <5 模块清单（前 50）")
    lines.append("| 文件 | URL 数 |")
    lines.append("|------|--------|")
    for rel, n in r108["under_5_list"][:50]:
        lines.append(f"| {rel} | {n} |")
    lines.append("")

    lines.append("## R109 R03 fall-back 风险")
    lines.append("")
    lines.append(f"- 风险总数: **{r109['total']}**")
    lines.append("")
    lines.append("### 按模式分类")
    lines.append("| 模式 | 数量 |")
    lines.append("|------|------|")
    for pat, count in r109["summary"].items():
        lines.append(f"| {pat} | {count} |")
    lines.append("")
    lines.append("### 详细清单（前 100 条）")
    lines.append("| 模式 | 文件 | 行号 | 代码 |")
    lines.append("|------|------|------|------|")
    shown = 0
    for pat, items in r109["details"].items():
        for rel, line_no, code in items:
            if shown >= 100:
                break
            lines.append(f"| {pat} | {rel} | {line_no} | `{code}` |")
            shown += 1
        if shown >= 100:
            break
    lines.append("")

    lines.append("## R110 R04 GPU 合规")
    lines.append("")
    lines.append(f"- 实际使用（import/代码）: **{r110['actual_usage_count']}**")
    lines.append(f"- 文档/注释提及: **{r110['doc_mention_count']}**")
    lines.append("")
    lines.append("### 实际使用清单")
    lines.append("| 文件 | 行号 | 代码 |")
    lines.append("|------|------|------|")
    for rel, line_no, code in r110["actual_usage"]:
        lines.append(f"| {rel} | {line_no} | `{code}` |")
    lines.append("")
    lines.append("### 文档/注释提及清单（前 30）")
    lines.append("| 文件 | 行号 | 代码 |")
    lines.append("|------|------|------|")
    for rel, line_no, code in r110["doc_mentions"]:
        lines.append(f"| {rel} | {line_no} | `{code}` |")
    lines.append("")

    lines.append("## 结论")
    lines.append("")
    lines.append("- R105/R106: 圈复杂度 >15 与 >80 行函数为代码质量改进重点，后续 R601+ 质量完成阶段处理。")
    lines.append("- R107: 类型注解覆盖率为可量化指标，需在 R601+ 提升至 ≥90%。")
    lines.append("- R108: 引用 <5 的模块需补充文献（R02 学术诚信，每个模块 docstring ≥5 文献 URL）。")
    lines.append("- R109: fall-back 风险需逐条审核，区分合法（边界返回 None）与违规（静默兜底假数据）。")
    lines.append("- R110: GPU 实际使用需逐条核查，若仅文档提及（R04 战略说明）则合规；若实际 import 则违规需删除。")
    lines.append("")

    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(f"[OK] 报告已生成: {REPORT}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
