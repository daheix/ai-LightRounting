#!/usr/bin/env python3
"""学术诚信基线扫描脚本"""
import ast
import os
import re
from pathlib import Path

POLARIS_DIR = Path("/workspace/src/polaris")

# 文献引用模式
CITATION_PATTERNS = [
    re.compile(r'https?://[^\s\)\]]+', re.IGNORECASE),
    re.compile(r'doi:\s*10\.\d{4,9}/[-._;()/:A-Z0-9]+', re.IGNORECASE),
    re.compile(r'10\.\d{4,9}/[-._;()/:A-Z0-9]+'),
    re.compile(r'arXiv:\s*\d{4}\.\d{4,5}', re.IGNORECASE),
    re.compile(r'arxiv\.org/(?:abs|pdf)/\d{4}\.\d{4,5}', re.IGNORECASE),
    re.compile(r'ISBN(?:-13|-10)?:?\s*[\d-]+', re.IGNORECASE),
]

def extract_module_docstring(filepath):
    """提取模块级 docstring"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            source = f.read()
        tree = ast.parse(source)
        return ast.get_docstring(tree) or ""
    except Exception as e:
        return f"ERROR: {e}"

def extract_class_docstrings(filepath):
    """提取类级 docstring"""
    docstrings = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            source = f.read()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                doc = ast.get_docstring(node)
                if doc:
                    docstrings.append(doc)
    except Exception:
        pass
    return docstrings

def extract_function_docstrings(filepath):
    """提取函数级 docstring"""
    docstrings = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            source = f.read()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                doc = ast.get_docstring(node)
                if doc:
                    docstrings.append(doc)
    except Exception:
        pass
    return docstrings

def count_citations(docstring):
    """统计 docstring 中的文献引用数量"""
    if not docstring:
        return 0, []
    all_matches = []
    for pattern in CITATION_PATTERNS:
        matches = pattern.findall(docstring)
        all_matches.extend(matches)
    return len(all_matches), all_matches

def get_subpackages():
    """获取所有一级子包"""
    subpackages = []
    for item in sorted(POLARIS_DIR.iterdir()):
        if item.is_dir() and not item.name.startswith('_') and not item.name.startswith('.'):
            has_py_files = any(item.glob('*.py'))
            if has_py_files:
                subpackages.append(item.name)
    return subpackages

def analyze_module(filepath, rel_path):
    """分析单个模块"""
    module_doc = extract_module_docstring(filepath)
    module_citation_count, module_citations = count_citations(module_doc)
    
    class_docs = extract_class_docstrings(filepath)
    class_citation_count = 0
    class_citations = []
    for doc in class_docs:
        cnt, cits = count_citations(doc)
        class_citation_count += cnt
        class_citations.extend(cits)
    
    func_docs = extract_function_docstrings(filepath)
    func_citation_count = 0
    func_citations = []
    for doc in func_docs:
        cnt, cits = count_citations(doc)
        func_citation_count += cnt
        func_citations.extend(cits)
    
    total_citations = module_citation_count + class_citation_count + func_citation_count
    all_citations = module_citations + class_citations + func_citations
    
    has_docstring = bool(module_doc) or len(class_docs) > 0 or len(func_docs) > 0
    
    return {
        'path': rel_path,
        'has_docstring': has_docstring,
        'module_citation_count': module_citation_count,
        'class_citation_count': class_citation_count,
        'function_citation_count': func_citation_count,
        'total_citations': total_citations,
        'citations': all_citations[:10],
    }

def analyze_subpackage(pkg_name):
    """分析一个子包"""
    pkg_dir = POLARIS_DIR / pkg_name
    results = []
    
    init_file = pkg_dir / '__init__.py'
    if init_file.exists():
        results.append(analyze_module(init_file, f"{pkg_name}/__init__.py"))
    
    for py_file in sorted(pkg_dir.glob("*.py")):
        if py_file.name == '__init__.py':
            continue
        rel_path = f"{pkg_name}/{py_file.name}"
        results.append(analyze_module(py_file, rel_path))
    
    for subdir in sorted(pkg_dir.iterdir()):
        if subdir.is_dir() and not subdir.name.startswith('_') and not subdir.name.startswith('.'):
            sub_init = subdir / '__init__.py'
            if sub_init.exists():
                for py_file in sorted(subdir.glob("*.py")):
                    rel_path = f"{pkg_name}/{subdir.name}/{py_file.name}"
                    results.append(analyze_module(py_file, rel_path))
    
    return results

def check_gpu_backend():
    """检查 gpu_backend.py 是否按 R04 战略正确禁用"""
    gpu_file = POLARIS_DIR / 'engine' / 'gpu_backend.py'
    gpu_density_file = POLARIS_DIR / 'engine' / 'gpu_density_field.py'
    fdtd_gpu_file = POLARIS_DIR / 'sim' / 'fdtd_gpu_engine.py'
    
    results = {}
    
    for name, fpath in [
        ('engine/gpu_backend.py', gpu_file),
        ('engine/gpu_density_field.py', gpu_density_file),
        ('sim/fdtd_gpu_engine.py', fdtd_gpu_file),
    ]:
        info = {'exists': fpath.exists()}
        if fpath.exists():
            with open(fpath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            info['lines'] = len(content.splitlines())
            
            disabled_patterns = [
                r'raise.*NotImplementedError',
                r'raise.*DisabledError',
                r'#\s*DISABLED',
                r'R04',
                r'not available',
                r'CPU only',
                r'GPU.*disabled',
                r'GPU.*not available',
                r'stub',
                r'placeholder',
            ]
            
            found_patterns = []
            for pat in disabled_patterns:
                if re.search(pat, content, re.IGNORECASE):
                    found_patterns.append(pat)
            
            info['disabled_indicators'] = found_patterns
            info['is_disabled'] = len(found_patterns) > 0
            
            docstring = extract_module_docstring(fpath)
            info['has_docstring'] = bool(docstring)
            if docstring:
                info['docstring_preview'] = docstring[:200]
        
        results[name] = info
    
    return results

def main():
    print("=" * 80)
    print("PoLaRIS 学术诚信基线扫描报告")
    print("=" * 80)
    print()
    
    subpackages = get_subpackages()
    print(f"【1】22 个子包名称（共 {len(subpackages)} 个）：")
    print("-" * 80)
    for i, pkg in enumerate(subpackages, 1):
        print(f"  {i:2d}. {pkg}")
    print()
    
    print("【2】各子包文献引用统计：")
    print("-" * 80)
    
    all_module_results = []
    pkg_summary = {}
    
    for pkg in subpackages:
        modules = analyze_subpackage(pkg)
        all_module_results.extend(modules)
        
        total_modules = len(modules)
        modules_with_doc = sum(1 for m in modules if m['has_docstring'])
        total_citations = sum(m['total_citations'] for m in modules)
        avg_citations = total_citations / total_modules if total_modules > 0 else 0
        
        pkg_summary[pkg] = {
            'total_modules': total_modules,
            'modules_with_doc': modules_with_doc,
            'total_citations': total_citations,
            'avg_citations': avg_citations,
        }
        
        print(f"\n  ▸ {pkg}:")
        print(f"    模块数: {total_modules}, 有docstring模块数: {modules_with_doc}")
        print(f"    总引用数: {total_citations}, 平均引用数: {avg_citations:.2f}")
        
        if modules:
            print(f"    各模块引用数:")
            for m in modules:
                status = "✓" if m['has_docstring'] else "✗"
                print(f"      [{status}] {m['path']}: {m['total_citations']} 引用")
    
    print()
    print("【3】引用数 < 5 的模块清单：")
    print("-" * 80)
    
    low_citation_modules = [m for m in all_module_results if m['total_citations'] < 5]
    zero_citation_modules = [m for m in all_module_results if m['total_citations'] == 0]
    no_docstring_modules = [m for m in all_module_results if not m['has_docstring']]
    
    print(f"\n  引用数 < 5 的模块总数: {len(low_citation_modules)} / {len(all_module_results)}")
    print(f"  引用数 = 0 的模块总数: {len(zero_citation_modules)} / {len(all_module_results)}")
    print(f"  无 docstring 的模块总数: {len(no_docstring_modules)} / {len(all_module_results)}")
    
    print(f"\n  引用数 = 0 的模块清单:")
    for m in sorted(zero_citation_modules, key=lambda x: x['path']):
        print(f"    - {m['path']}")
    
    print(f"\n  引用数 1-4 的模块清单:")
    for m in sorted(low_citation_modules, key=lambda x: x['path']):
        if 1 <= m['total_citations'] <= 4:
            print(f"    - {m['path']}: {m['total_citations']} 引用")
    
    print()
    print("【4】GPU 后端 R04 禁用状态检查：")
    print("-" * 80)
    
    gpu_results = check_gpu_backend()
    for name, info in gpu_results.items():
        print(f"\n  ▸ {name}:")
        print(f"    文件存在: {info['exists']}")
        if info['exists']:
            print(f"    代码行数: {info['lines']}")
            print(f"    有 docstring: {info['has_docstring']}")
            print(f"    禁用指示器: {info['disabled_indicators']}")
            print(f"    是否已禁用: {'是' if info['is_disabled'] else '否'}")
            if 'docstring_preview' in info:
                print(f"    Docstring 预览: {info['docstring_preview']}")
    
    print()
    print("=" * 80)
    print("扫描完成")
    print("=" * 80)
    
    return {
        'subpackages': subpackages,
        'pkg_summary': pkg_summary,
        'all_modules': all_module_results,
        'low_citation_modules': low_citation_modules,
        'zero_citation_modules': zero_citation_modules,
        'no_docstring_modules': no_docstring_modules,
        'gpu_results': gpu_results,
    }

if __name__ == '__main__':
    main()
