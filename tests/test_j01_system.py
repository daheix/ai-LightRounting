"""J01 系统级/分布式验收测试。

覆盖验收标准：
- M1: 分布式任务调度
- M2: 结果聚合
- M3: 错误恢复

学术来源:
- Ray RLlib PPO: https://docs.ray.io/en/latest/rllib/algorithms/ppo.html
- IMPALA: Espeholt et al., 2018, https://arxiv.org/abs/1802.01561
- A3C: Mnih et al., 2016, https://arxiv.org/abs/1602.01783
- AlphaChip: Mirhoseini et al., Nature 2021, https://www.nature.com/articles/s41586-021-03544-w
- Cadence ADE-XL 分布式: https://docs.cadence.com/
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from polaris.system import (
    TaskStatus,
    TaskResult,
    DistributedConfig,
    DistributedTaskScheduler,
)


# =============================================================================
# M1: 分布式任务调度测试
# =============================================================================


class TestDistributedTaskScheduling:
    """分布式任务调度测试。"""

    def test_task_status_enum(self):
        """TaskStatus 枚举值正确。"""
        assert TaskStatus.PENDING == "pending"
        assert TaskStatus.RUNNING == "running"
        assert TaskStatus.COMPLETED == "completed"
        assert TaskStatus.FAILED == "failed"
        assert TaskStatus.CANCELLED == "cancelled"

    def test_task_result_defaults(self):
        """TaskResult 默认值正确。"""
        result = TaskResult(task_id="test_1")
        assert result.task_id == "test_1"
        assert result.status == TaskStatus.PENDING
        assert result.result is None
        assert result.error is None
        assert result.retries == 0

    def test_task_result_duration(self):
        """TaskResult.duration_s 计算正确。"""
        result = TaskResult(task_id="test_1", start_time=100.0, end_time=105.5)
        assert result.duration_s == 5.5

    def test_task_result_duration_none_when_incomplete(self):
        """未完成时 duration_s 返回 None。"""
        result = TaskResult(task_id="test_1")
        assert result.duration_s is None

    def test_distributed_config_defaults(self):
        """DistributedConfig 默认值正确。"""
        cfg = DistributedConfig()
        assert cfg.num_workers == 4
        assert cfg.max_retries == 2
        assert cfg.task_timeout_s == 60.0
        assert cfg.backend == "sequential"

    def test_scheduler_submit_task(self):
        """调度器可提交任务。"""
        scheduler = DistributedTaskScheduler(DistributedConfig(num_workers=2))
        try:
            def simple_task(x):
                return x * 2

            task_id = scheduler.submit("task_1", simple_task, 21)
            assert task_id == "task_1"
            result = scheduler.get_result(task_id)
            assert result is not None
            assert result.status == TaskStatus.COMPLETED
            assert result.result == 42
        finally:
            scheduler.shutdown()

    def test_scheduler_multiple_tasks_sequential(self):
        """顺序后端可处理多个任务。"""
        scheduler = DistributedTaskScheduler(DistributedConfig(num_workers=2))
        try:
            def add(a, b):
                return a + b

            for i in range(5):
                scheduler.submit(f"task_{i}", add, i, i)

            results = scheduler.list_results()
            assert len(results) == 5
            completed = scheduler.list_results(TaskStatus.COMPLETED)
            assert len(completed) == 5

            for i in range(5):
                r = scheduler.get_result(f"task_{i}")
                assert r is not None
                assert r.result == i + i
        finally:
            scheduler.shutdown()

    def test_scheduler_threading_backend(self):
        """线程后端可并行执行任务。"""
        import threading

        cfg = DistributedConfig(num_workers=4, backend="threading")
        scheduler = DistributedTaskScheduler(cfg)
        try:
            counter = {"n": 0}
            lock = threading.Lock()

            def slow_task(x):
                time.sleep(0.1)
                with lock:
                    counter["n"] += 1
                return x * x

            start = time.time()
            for i in range(4):
                scheduler.submit(f"t{i}", slow_task, i)

            done = scheduler.wait_all(timeout=5.0)
            assert done is True
            elapsed = time.time() - start

            assert counter["n"] == 4
            assert elapsed < 1.0
        finally:
            scheduler.shutdown()

    def test_scheduler_get_nonexistent_task(self):
        """获取不存在任务返回 None。"""
        scheduler = DistributedTaskScheduler()
        try:
            assert scheduler.get_result("nonexistent") is None
        finally:
            scheduler.shutdown()


# =============================================================================
# M2: 结果聚合测试
# =============================================================================


class TestResultAggregation:
    """结果聚合测试。"""

    def test_aggregate_results_empty(self):
        """空任务列表聚合。"""
        scheduler = DistributedTaskScheduler()
        try:
            agg = scheduler.aggregate_results()
            assert agg["total_tasks"] == 0
            assert agg["completed"] == 0
            assert agg["failed"] == 0
            assert agg["results"] == {}
        finally:
            scheduler.shutdown()

    def test_aggregate_results_all_completed(self):
        """全部完成的任务聚合。"""
        scheduler = DistributedTaskScheduler()
        try:
            def square(x):
                return x * x

            for i in range(3):
                scheduler.submit(f"t{i}", square, i)

            agg = scheduler.aggregate_results()
            assert agg["total_tasks"] == 3
            assert agg["completed"] == 3
            assert agg["failed"] == 0
            assert len(agg["results"]) == 3
            assert agg["results"]["t0"] == 0
            assert agg["results"]["t1"] == 1
            assert agg["results"]["t2"] == 4
        finally:
            scheduler.shutdown()

    def test_aggregate_results_mixed_status(self):
        """混合状态的任务聚合。"""
        scheduler = DistributedTaskScheduler()
        try:
            def ok_task():
                return "success"

            def fail_task():
                raise ValueError("故意失败")

            scheduler.submit("ok1", ok_task)
            scheduler.submit("fail1", fail_task)
            scheduler.submit("ok2", ok_task)

            agg = scheduler.aggregate_results()
            assert agg["total_tasks"] == 3
            assert agg["completed"] == 2
            assert agg["failed"] == 1
            assert len(agg["results"]) == 2
        finally:
            scheduler.shutdown()

    def test_list_results_with_status_filter(self):
        """按状态过滤任务列表。"""
        scheduler = DistributedTaskScheduler()
        try:
            def ok():
                return 1

            def fail():
                raise RuntimeError("fail")

            scheduler.submit("a", ok)
            scheduler.submit("b", fail)
            scheduler.submit("c", ok)

            completed = scheduler.list_results(TaskStatus.COMPLETED)
            failed = scheduler.list_results(TaskStatus.FAILED)

            assert len(completed) == 2
            assert len(failed) == 1
        finally:
            scheduler.shutdown()


# =============================================================================
# M3: 错误恢复测试
# =============================================================================


class TestErrorRecovery:
    """错误恢复测试。"""

    def test_task_failure_captured(self):
        """任务失败被正确捕获。"""
        scheduler = DistributedTaskScheduler(DistributedConfig(max_retries=0))
        try:
            def failing_task():
                raise ValueError("测试错误")

            scheduler.submit("fail_task", failing_task)
            result = scheduler.get_result("fail_task")
            assert result is not None
            assert result.status == TaskStatus.FAILED
            assert result.error is not None
            assert "测试错误" in result.error
        finally:
            scheduler.shutdown()

    def test_retry_on_failure(self):
        """失败任务自动重试。"""
        call_count = {"n": 0}

        def flaky_task():
            call_count["n"] += 1
            if call_count["n"] < 3:
                raise RuntimeError(f"第 {call_count['n']} 次失败")
            return "success"

        scheduler = DistributedTaskScheduler(DistributedConfig(max_retries=3))
        try:
            scheduler.submit("flaky", flaky_task)
            result = scheduler.get_result("flaky")
            assert result is not None
            assert result.status == TaskStatus.COMPLETED
            assert result.result == "success"
            assert result.retries == 2
            assert call_count["n"] == 3
        finally:
            scheduler.shutdown()

    def test_max_retries_exceeded(self):
        """超过最大重试次数后标记为失败。"""
        call_count = {"n": 0}

        def always_fail():
            call_count["n"] += 1
            raise RuntimeError("总是失败")

        scheduler = DistributedTaskScheduler(DistributedConfig(max_retries=2))
        try:
            scheduler.submit("always_fail", always_fail)
            result = scheduler.get_result("always_fail")
            assert result is not None
            assert result.status == TaskStatus.FAILED
            assert call_count["n"] == 3
        finally:
            scheduler.shutdown()

    def test_retry_backoff(self):
        """重试之间有延迟。"""
        call_times = []

        def failing_task():
            call_times.append(time.time())
            raise RuntimeError("失败")

        scheduler = DistributedTaskScheduler(DistributedConfig(max_retries=2))
        try:
            scheduler.submit("retry_test", failing_task)
            result = scheduler.get_result("retry_test")
            assert result is not None
            assert result.status == TaskStatus.FAILED
            assert len(call_times) == 3
            assert call_times[1] - call_times[0] >= 0.05
        finally:
            scheduler.shutdown()

    def test_wait_all_completes(self):
        """wait_all 等待所有任务完成。"""
        scheduler = DistributedTaskScheduler(
            DistributedConfig(num_workers=2, backend="threading")
        )
        try:
            def quick(x):
                time.sleep(0.05)
                return x

            for i in range(3):
                scheduler.submit(f"w{i}", quick, i)

            done = scheduler.wait_all(timeout=5.0)
            assert done is True

            for i in range(3):
                r = scheduler.get_result(f"w{i}")
                assert r is not None
                assert r.status == TaskStatus.COMPLETED
        finally:
            scheduler.shutdown()

    def test_task_with_kwargs(self):
        """任务支持关键字参数。"""
        scheduler = DistributedTaskScheduler()
        try:
            def greet(name, greeting="Hello"):
                return f"{greeting}, {name}!"

            scheduler.submit("greet1", greet, "World")
            scheduler.submit("greet2", greet, "Alice", greeting="Hi")

            r1 = scheduler.get_result("greet1")
            r2 = scheduler.get_result("greet2")

            assert r1.result == "Hello, World!"
            assert r2.result == "Hi, Alice!"
        finally:
            scheduler.shutdown()
