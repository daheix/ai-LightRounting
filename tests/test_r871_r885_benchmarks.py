"""R871-R885 基准测试套件 pytest 用例。

验证 12 个基准可执行且结果合理（R03：禁止 fall-back，失败即告警）。

学术依据（R02，≥5 文献 URL）：
- Taflove & Hagness 2005 FDTD https://www.artechhouse.com/
- Harris 2020 NumPy Nature https://doi.org/10.1038/s41586-020-2649-2
- Virtanen 2020 SciPy Nature Methods https://doi.org/10.1038/s41592-019-0686-2
- Lin DREAMPlace TCAD 2020 https://doi.org/10.1109/TCAD.2020.3003146
- LiDAR ISPD'25 https://dl.acm.org/doi/10.1145/3698364.3705355
- Soremekun 2021 ISPD https://doi.org/10.1145/3452144.3462196
- NetworkX isomorphism https://networkx.org/documentation/stable/reference/algorithms/isomorphism.html
"""

from __future__ import annotations

import pytest

from tests.benchmarks import BenchmarkRunner, run_full_suite
from tests.benchmarks.suite import _build_benchmark_registry


@pytest.fixture(scope="module")
def runner() -> BenchmarkRunner:
    """基准执行器实例（模块级共享）。"""
    return BenchmarkRunner()


def test_benchmark_registry_has_at_least_10() -> None:
    """R871-R885 验收：基准套件 ≥10 个。"""
    registry = _build_benchmark_registry()
    assert len(registry) >= 10, f"基准数须 ≥10，实际 {len(registry)}"


def test_benchmark_names_unique() -> None:
    """基准名唯一。"""
    registry = _build_benchmark_registry()
    names = [n for n, _ in registry]
    assert len(names) == len(set(names)), "基准名重复"


@pytest.mark.parametrize("name", [n for n, _ in _build_benchmark_registry()])
def test_each_benchmark_passes(runner: BenchmarkRunner, name: str) -> None:
    """每个基准执行 ok=True（失败即断言失败，不静默兜底）。"""
    case = runner.run_one(name)
    assert case.ok, (
        f"基准 {name} 失败: elapsed={case.elapsed_ms:.3f}ms error={case.error[:300]}"
    )
    assert case.elapsed_ms >= 0.0


def test_full_suite_pass_rate(runner: BenchmarkRunner) -> None:
    """全套基准通过率 100%（R03：不允许失败基准）。"""
    result = runner.run_all()
    assert result.passed == result.summary["total_benchmarks"], (
        f"通过 {result.passed}/{result.summary['total_benchmarks']}，"
        f"失败 {result.failed}："
        + ", ".join(c.name for c in result.cases if not c.ok)
    )


def test_full_suite_speedup_summary(runner: BenchmarkRunner) -> None:
    """加速比汇总：至少有一个基准 speedup > 1.0（向量化生效）。"""
    result = runner.run_all()
    assert result.summary["max_speedup"] > 1.0, (
        f"max_speedup={result.summary['max_speedup']} 须 >1.0"
    )


def test_run_full_suite_facade() -> None:
    """run_full_suite facade 返回合法结果。"""
    result = run_full_suite()
    assert result.summary["total_benchmarks"] >= 10
    assert result.passed >= 1
    assert result.total_ms > 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-ra"])
