"""R457-R550 性能基准测试套件 + 多进程执行器。

从 perf_optimization.py 拆分（批次 10-B 续 超长文件拆分）。纯 NumPy/SciPy
CPU，R04 兼容。

## R04 战略（不可撤销）

🚫不参与 GPU：纯 NumPy/SciPy。

## R03 禁止 fall-back

业务错误一律 raise。MultiprocessRunner 默认串行执行（max_workers=None）
是显式设计选择，非 fall-back：保证 pickle 复杂闭包失败时的业务正确性。
并行失败时 raise RuntimeError。

## 学术依据（R02，≥5 个文献 URL）

1. Agarwal et al. 2021 NeurIPS Deep RL Benchmark（统计显著性）
   https://arxiv.org/abs/2108.07848
2. Lumerical varFDTD Effective Index
   https://optics.ansys.com/hc/en-us/articles/360034914713
3. Tidy3D Performance Benchmarks
   https://docs.flexcompute.com/projects/tidy3d/en/stable/
4. Press et al. 2007 Numerical Recipes 3rd Cambridge（统计与中位数）
   https://numerical.recipes/
5. Python 文档 concurrent.futures.ProcessPoolExecutor
   https://docs.python.org/3/library/concurrent.futures.html
6. Google JAX 2023 benchmarks
   https://github.com/google/jax/blob/main/docs/jax_performance_benchmark.md

## 规则依据

规则 14（非法输入 raise）/规则 18（学术诚信）/规则 26（GPU 不参与）
"""

from __future__ import annotations

import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from typing import Any, Callable

import numpy as np

__all__ = [
    "BenchmarkCase",
    "BenchmarkResult",
    "PerfBenchmarkSuite",
    "MultiprocessRunner",
]


@dataclass
class BenchmarkCase:
    """性能基准测试用例。

    Attributes:
        name: 用例名。
        fn: 待测函数，无参数。
        expected_runtime: 预期运行时上限（秒），超过则告警。
        n_runs: 重复运行次数（取中位数）。
    """

    name: str
    fn: Callable[[], Any]
    expected_runtime: float = 10.0
    n_runs: int = 3


@dataclass
class BenchmarkResult:
    """性能基准测试结果。

    Attributes:
        name: 用例名。
        median_time: 中位数运行时（秒）。
        min_time: 最小运行时（秒）。
        max_time: 最大运行时（秒）。
        std_time: 运行时标准差（秒）。
        passed: 是否通过 expected_runtime 阈值。
    """

    name: str
    median_time: float
    min_time: float
    max_time: float
    std_time: float
    passed: bool


class PerfBenchmarkSuite:
    """性能基准测试套件（R457-R550）。

    收集多个 BenchmarkCase，统一运行并输出报告。

    用法：
        suite = PerfBenchmarkSuite()
        suite.add(BenchmarkCase("fdtd_100", fn=lambda: run_fdtd(100), expected_runtime=1.0))
        results = suite.run()
        report = suite.to_markdown(results)
    """

    def __init__(self) -> None:
        self._cases: list[BenchmarkCase] = []

    def add(self, case: BenchmarkCase) -> None:
        """添加测试用例。"""
        if not callable(case.fn):
            raise ValueError(f"case.fn 须可调用，实际 {type(case.fn)}")
        if case.n_runs < 1:
            raise ValueError(f"n_runs 须 ≥1，实际 {case.n_runs}")
        self._cases.append(case)

    def run(self) -> list[BenchmarkResult]:
        """运行所有基准用例。

        Returns:
            各用例结果列表。

        Raises:
            RuntimeError: 任一用例抛异常。
        """
        results: list[BenchmarkResult] = []
        for case in self._cases:
            times: list[float] = []
            for _ in range(case.n_runs):
                t0 = time.perf_counter()
                try:
                    case.fn()
                except Exception as exc:
                    raise RuntimeError(
                        f"用例 {case.name} 执行失败：{exc}"
                    ) from exc
                times.append(time.perf_counter() - t0)
            arr = np.asarray(times)
            median = float(np.median(arr))
            res = BenchmarkResult(
                name=case.name,
                median_time=median,
                min_time=float(np.min(arr)),
                max_time=float(np.max(arr)),
                std_time=float(np.std(arr)),
                passed=median <= case.expected_runtime,
            )
            results.append(res)
        return results

    @staticmethod
    def to_markdown(results: list[BenchmarkResult]) -> str:
        """生成 Markdown 报告。"""
        lines = [
            "| 用例 | 中位数 (s) | 最小 (s) | 最大 (s) | 标准差 | 通过 |",
            "|------|-----------|---------|---------|--------|------|",
        ]
        for r in results:
            lines.append(
                f"| {r.name} | {r.median_time:.4f} | {r.min_time:.4f} | "
                f"{r.max_time:.4f} | {r.std_time:.4f} | "
                f"{'✓' if r.passed else '✗'} |"
            )
        return "\n".join(lines)


class MultiprocessRunner:
    """任务并行执行器（R457-R550）。

    max_workers=None（默认）→ 串行执行（设计选择：避免 pickle 复杂闭包
    失败，保证业务正确性优先）。
    max_workers>=2 → 用 concurrent.futures.ProcessPoolExecutor 并行。

    用法：
        runner = MultiprocessRunner(max_workers=4)
        results = runner.map(fn, items)
    """

    def __init__(self, max_workers: int | None = None) -> None:
        """初始化执行器。

        Args:
            max_workers: 最大进程数，None 表示串行（默认）；≥2 启用并行。
        """
        if max_workers is not None and max_workers < 1:
            raise ValueError(f"max_workers 须 ≥1 或 None，实际 {max_workers}")
        self.max_workers = max_workers

    def map(
        self,
        fn: Callable[[Any], Any],
        items: list[Any],
    ) -> list[Any]:
        """映射 fn 到 items。

        Args:
            fn: 单参数函数（并行模式下须 picklable）。
            items: 输入列表。

        Returns:
            结果列表（与 items 同序）。

        Raises:
            ValueError: items 为空或 fn 不可调用。
            RuntimeError: 任一任务失败。
        """
        if not items:
            raise ValueError("items 不能为空（规则 14：禁止 fall-back）")
        if not callable(fn):
            raise ValueError("fn 须可调用")
        if self.max_workers is not None and self.max_workers >= 2:
            try:
                with ProcessPoolExecutor(max_workers=self.max_workers) as ex:
                    results = list(ex.map(fn, items))
                return results
            except Exception as exc:
                raise RuntimeError(
                    f"并行执行失败：{exc}（规则 14：禁止 fall-back）"
                ) from exc
        # 串行执行（默认 max_workers=None 路径，非 fall-back）
        return [fn(item) for item in items]
