"""PoLaRIS 基准测试套件包（R871-R885）。

提供可复用的性能基准，覆盖仿真（FDTD/FDE）、验证（DRC/LVS）、
寄生提取、布线、密度场及性能调优原语。

所有基准使用真实计算内核（R03：禁止 fall-back / 假数据）。
"""

from tests.benchmarks.suite import (
    BenchmarkCase,
    BenchmarkRunner,
    BenchmarkSuiteResult,
    run_full_suite,
)

__all__ = [
    "BenchmarkCase",
    "BenchmarkRunner",
    "BenchmarkSuiteResult",
    "run_full_suite",
]
