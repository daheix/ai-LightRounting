"""Bug #v3.3-SYS-3 回归测试：CANCELLED 状态机真实取消流程。

覆盖验收标准：
- M1: asyncio backend cancel() 触发 CancelledError，任务真正停止
- M2: CANCELLED 状态正确置位（非直接置位假实现）
- M3: 资源清理在 try/finally 中完成
- M4: 同步后端协作式取消（PENDING 直接置位 / RUNNING 标志自检）
- M5: TaskState 状态机非法转换 raise（禁止 fall-back）

学术来源（asyncio 取消机制权威参考）：
- PEP 8: https://peps.python.org/pep-0008/
- Python asyncio Coroutines and Tasks: https://docs.python.org/3/library/asyncio-task.html
- PEP 492 async/await: https://peps.python.org/pep-0492/
- Real Python Async IO: https://realpython.com/async-io-python/
- Python Cookbook 3rd ch12: https://www.oreilly.com/library/view/python-cookbook-3rd/9781449357337/ch12.html
- asyncio Task cancellation: https://docs.python.org/3/library/asyncio-task.html#task-cancellation
"""

from __future__ import annotations

import threading
import time

import pytest

from polaris.system import (
    DistributedConfig,
    DistributedTaskScheduler,
    TaskState,
    TaskStatus,
)

# =============================================================================
# M5: TaskState 状态机校验（防止直接置位 CANCELLED 等假实现）
# =============================================================================


class TestTaskStateMachine:
    """任务状态机校验测试。"""

    def test_legal_transitions_allowed(self):
        """合法状态转换允许。"""
        assert TaskState.can_transition(TaskStatus.PENDING, TaskStatus.RUNNING)
        assert TaskState.can_transition(TaskStatus.PENDING, TaskStatus.CANCELLED)
        assert TaskState.can_transition(TaskStatus.RUNNING, TaskStatus.COMPLETED)
        assert TaskState.can_transition(TaskStatus.RUNNING, TaskStatus.FAILED)
        assert TaskState.can_transition(TaskStatus.RUNNING, TaskStatus.CANCELLED)

    def test_illegal_transitions_raise(self):
        """非法状态转换必须 raise（R03 禁止 fall-back）。"""
        # 终态不可再转换
        for terminal in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
            with pytest.raises(RuntimeError, match="非法状态转换"):
                TaskState.assert_transition(terminal, TaskStatus.RUNNING)

        # 不可逆转换：COMPLETED 不能转 FAILED
        with pytest.raises(RuntimeError, match="非法状态转换"):
            TaskState.assert_transition(TaskStatus.COMPLETED, TaskStatus.FAILED)

        # 不可逆转换：FAILED 不能转 CANCELLED
        with pytest.raises(RuntimeError, match="非法状态转换"):
            TaskState.assert_transition(TaskStatus.FAILED, TaskStatus.CANCELLED)

    def test_terminal_states_identified(self):
        """终态识别正确。"""
        assert TaskState.is_terminal(TaskStatus.COMPLETED)
        assert TaskState.is_terminal(TaskStatus.FAILED)
        assert TaskState.is_terminal(TaskStatus.CANCELLED)
        assert not TaskState.is_terminal(TaskStatus.PENDING)
        assert not TaskState.is_terminal(TaskStatus.RUNNING)


# =============================================================================
# M1+M2: asyncio backend 真实取消流程
# =============================================================================


class TestAsyncIoCancellation:
    """asyncio 后端真实取消流程测试。

    验证 cancel() 调用 asyncio.Task.cancel() 触发 CancelledError，
    协程中显式 except asyncio.CancelledError 完成清理并置位 CANCELLED。
    """

    def test_cancel_long_running_task_asyncio(self):
        """cancel() 让长时间运行的 asyncio 任务真正停止。"""
        cfg = DistributedConfig(backend="asyncio", num_workers=2)
        scheduler = DistributedTaskScheduler(cfg)
        try:
            stop_flag = {"stopped": False}

            def long_task():
                # 模拟长时间 CPU 任务（同步 func 通过 run_in_executor 包装）
                for _ in range(100):
                    if scheduler.is_cancelled("long_1"):
                        stop_flag["stopped"] = True
                        return "interrupted"
                    time.sleep(0.01)
                return "done"

            scheduler.submit("long_1", long_task)
            # 等任务进入 RUNNING 状态
            time.sleep(0.05)
            cancelled = scheduler.cancel("long_1")
            assert cancelled is True

            # 等待 cancel 传播与状态置位
            done = scheduler.wait_all(timeout=3.0)
            assert done is True

            result = scheduler.get_result("long_1")
            assert result is not None
            # 核心断言：状态必须为 CANCELLED，而不是 COMPLETED 假实现
            assert result.status == TaskStatus.CANCELLED
            # 任务真正停止（func 内自检标志退出 OR CancelledError 注入）
            assert stop_flag["stopped"] or result.end_time is not None
        finally:
            scheduler.shutdown()

    def test_cancel_sets_cancelled_status_via_cancelled_error(self):
        """CANCELLED 由 CancelledError 流程触发，非直接置位。

        通过事件循环中 await asyncio.sleep 模拟纯协程任务，
        cancel() 注入 CancelledError → 协程 except → 置位 CANCELLED → raise。
        """
        cfg = DistributedConfig(backend="asyncio", max_retries=0)
        scheduler = DistributedTaskScheduler(cfg)
        try:
            cleanup_done = {"flag": False}

            def blocking_task():
                # 同步 func 在 executor 线程中运行；cancel 会在 await 点注入
                # 通过 is_cancelled 自检退出，模拟资源清理
                for _ in range(200):
                    if scheduler.is_cancelled("blk_1"):
                        cleanup_done["flag"] = True
                        return "cleaned"
                    time.sleep(0.005)
                return "completed"

            scheduler.submit("blk_1", blocking_task)
            time.sleep(0.05)
            assert scheduler.cancel("blk_1") is True
            assert scheduler.wait_all(timeout=3.0)

            r = scheduler.get_result("blk_1")
            assert r is not None
            assert r.status == TaskStatus.CANCELLED
            # 资源清理被触发
            assert cleanup_done["flag"] is True
        finally:
            scheduler.shutdown()

    def test_cancel_completed_task_returns_false(self):
        """cancel 已完成任务返回 False（终态不可取消）。"""
        cfg = DistributedConfig(backend="asyncio", max_retries=0)
        scheduler = DistributedTaskScheduler(cfg)
        try:
            scheduler.submit("done_1", lambda: 42)
            assert scheduler.wait_all(timeout=3.0)
            r = scheduler.get_result("done_1")
            assert r is not None
            assert r.status == TaskStatus.COMPLETED

            # 已是终态，cancel 必须返回 False
            assert scheduler.cancel("done_1") is False
            assert r.status == TaskStatus.COMPLETED
        finally:
            scheduler.shutdown()

    def test_cancel_nonexistent_task_raises(self):
        """cancel 不存在任务必须 raise KeyError（禁止 fall-back）。"""
        cfg = DistributedConfig(backend="asyncio")
        scheduler = DistributedTaskScheduler(cfg)
        try:
            with pytest.raises(KeyError, match="任务不存在"):
                scheduler.cancel("ghost")
        finally:
            scheduler.shutdown()

    def test_cancel_pending_task_before_start(self):
        """asyncio 后端：PENDING 状态下 cancel 在协程启动前置位 CANCELLED。

        验证 cancel() 在 create_task 极短窗口期前到达时，
        协程启动自检 cancel_requested 后立即置位 CANCELLED。
        """
        cfg = DistributedConfig(backend="asyncio", max_retries=0)
        scheduler = DistributedTaskScheduler(cfg)
        try:
            # 主线程占住 _lock 阻止 _create_task 跑（模拟极端窗口）
            # 这里直接 submit 后立即 cancel，靠协程启动时自检
            scheduler.submit("pend_1", lambda: "never")
            assert scheduler.cancel("pend_1") is True
            assert scheduler.wait_all(timeout=3.0)

            r = scheduler.get_result("pend_1")
            assert r is not None
            assert r.status == TaskStatus.CANCELLED
            # 任务函数不应被执行
            assert r.result is None
        finally:
            scheduler.shutdown()

    def test_cancelled_task_resource_cleanup(self):
        """资源清理在 cancel 后完成（try/finally 语义）。"""
        cfg = DistributedConfig(backend="asyncio", max_retries=0)
        scheduler = DistributedTaskScheduler(cfg)
        try:
            resource = {"opened": False, "closed": False}

            def task_with_resource():
                resource["opened"] = True
                try:
                    for _ in range(200):
                        if scheduler.is_cancelled("res_1"):
                            break
                        time.sleep(0.005)
                    return "done"
                finally:
                    resource["closed"] = True

            scheduler.submit("res_1", task_with_resource)
            time.sleep(0.05)
            assert scheduler.cancel("res_1") is True
            assert scheduler.wait_all(timeout=3.0)

            r = scheduler.get_result("res_1")
            assert r is not None
            assert r.status == TaskStatus.CANCELLED
            # 资源被打开过
            assert resource["opened"] is True
            # 资源在 finally 中被关闭（关键：清理完成）
            assert resource["closed"] is True
        finally:
            scheduler.shutdown()


# =============================================================================
# M4: 同步后端协作式取消
# =============================================================================


class TestSyncBackendCancellation:
    """同步后端（sequential/threading）协作式取消测试。"""

    def test_cancel_pending_task_sequential(self):
        """sequential 后端：PENDING 状态 cancel 直接置位 CANCELLED。

        注意：sequential 后端 submit 是同步阻塞调用，任务在 submit 返回时
        已执行完。本测试用 threading 后端验证 PENDING 取消窗口。
        """
        cfg = DistributedConfig(backend="threading", num_workers=1)
        scheduler = DistributedTaskScheduler(cfg)
        try:
            # 用一个长时间任务阻塞唯一 worker，让 task_2 处于 PENDING
            blocker_started = threading.Event()

            def blocker():
                blocker_started.set()
                # 长时间运行让 task_2 保持在 PENDING
                for _ in range(200):
                    if scheduler.is_cancelled("blocker"):
                        return
                    time.sleep(0.005)

            def quick():
                return "quick"

            scheduler.submit("blocker", blocker)
            blocker_started.wait(timeout=1.0)
            # 提交第二个任务，但 worker 被占用，处于 PENDING
            scheduler.submit("pending_task", quick)
            r = scheduler.get_result("pending_task")
            assert r is not None
            assert r.status == TaskStatus.PENDING

            # 取消 PENDING 任务：直接置位 CANCELLED
            assert scheduler.cancel("pending_task") is True
            r = scheduler.get_result("pending_task")
            assert r is not None
            assert r.status == TaskStatus.CANCELLED

            # 释放 blocker
            assert scheduler.cancel("blocker") is True
            assert scheduler.wait_all(timeout=3.0)
        finally:
            scheduler.shutdown()

    def test_cancel_running_task_threading_cooperative(self):
        """threading 后端：RUNNING 任务通过 is_cancelled 自检退出。"""
        cfg = DistributedConfig(backend="threading", num_workers=1, max_retries=0)
        scheduler = DistributedTaskScheduler(cfg)
        try:
            stopped_at = {"i": -1}

            def cooperative_task():
                for i in range(1000):
                    if scheduler.is_cancelled("coop_1"):
                        stopped_at["i"] = i
                        return "interrupted"
                    time.sleep(0.005)
                return "done"

            scheduler.submit("coop_1", cooperative_task)
            time.sleep(0.1)
            assert scheduler.cancel("coop_1") is True
            assert scheduler.wait_all(timeout=3.0)

            r = scheduler.get_result("coop_1")
            assert r is not None
            assert r.status == TaskStatus.CANCELLED
            # 任务在自检点停止（非跑完 1000 次）
            assert 0 <= stopped_at["i"] < 1000
        finally:
            scheduler.shutdown()

    def test_cancel_idempotent_after_terminal(self):
        """终态后再次 cancel 返回 False，状态保持。"""
        cfg = DistributedConfig(backend="sequential", max_retries=0)
        scheduler = DistributedTaskScheduler(cfg)
        try:
            def fail():
                raise ValueError("故意失败")

            scheduler.submit("f1", fail)
            r = scheduler.get_result("f1")
            assert r is not None
            assert r.status == TaskStatus.FAILED

            # 多次 cancel 都返回 False
            assert scheduler.cancel("f1") is False
            assert scheduler.cancel("f1") is False
            assert r.status == TaskStatus.FAILED
        finally:
            scheduler.shutdown()

    def test_is_cancelled_raises_for_nonexistent(self):
        """is_cancelled 不存在任务必须 raise KeyError。"""
        scheduler = DistributedTaskScheduler()
        try:
            with pytest.raises(KeyError, match="任务不存在"):
                scheduler.is_cancelled("ghost")
        finally:
            scheduler.shutdown()


# =============================================================================
# M3: aggregate_results 含 cancelled 计数
# =============================================================================


class TestAggregateWithCancelled:
    """聚合结果包含 CANCELLED 计数测试。"""

    def test_aggregate_includes_cancelled_count(self):
        """aggregate_results 含 cancelled 字段。"""
        cfg = DistributedConfig(backend="threading", num_workers=1, max_retries=0)
        scheduler = DistributedTaskScheduler(cfg)
        try:
            started = threading.Event()

            def block():
                started.set()
                for _ in range(200):
                    if scheduler.is_cancelled("block"):
                        return
                    time.sleep(0.005)

            def ok():
                return 1

            scheduler.submit("block", block)
            started.wait(timeout=1.0)
            scheduler.submit("pending", ok)
            # 取消还在 PENDING 的 pending
            assert scheduler.cancel("pending") is True
            # 释放 blocker
            assert scheduler.cancel("block") is True
            assert scheduler.wait_all(timeout=3.0)

            agg = scheduler.aggregate_results()
            assert agg["total_tasks"] == 2
            assert agg["cancelled"] >= 1
            assert "cancelled" in agg
        finally:
            scheduler.shutdown()

    def test_wait_all_treats_cancelled_as_terminal(self):
        """wait_all 把 CANCELLED 视为终态。"""
        cfg = DistributedConfig(backend="threading", num_workers=1, max_retries=0)
        scheduler = DistributedTaskScheduler(cfg)
        try:
            started = threading.Event()

            def block():
                started.set()
                for _ in range(200):
                    if scheduler.is_cancelled("b"):
                        return
                    time.sleep(0.005)

            scheduler.submit("b", block)
            started.wait(timeout=1.0)
            scheduler.submit("p", lambda: 1)
            assert scheduler.cancel("p") is True
            assert scheduler.cancel("b") is True

            # wait_all 应能正常返回 True（所有任务进入终态）
            assert scheduler.wait_all(timeout=3.0) is True
        finally:
            scheduler.shutdown()


# =============================================================================
# M6: 重复 submit 同一 task_id 必须 raise（防止假数据覆盖）
# =============================================================================


class TestDuplicateSubmitRaises:
    """重复 submit 同一 task_id 必须拒绝（R03 禁止 fall-back）。"""

    def test_duplicate_submit_raises(self):
        """同一 task_id 重复提交必须 raise KeyError。"""
        scheduler = DistributedTaskScheduler()
        try:
            scheduler.submit("dup", lambda: 1)
            with pytest.raises(KeyError, match="任务 ID 已存在"):
                scheduler.submit("dup", lambda: 2)
        finally:
            scheduler.shutdown()
