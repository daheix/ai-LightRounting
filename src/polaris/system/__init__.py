"""J01 系统级/分布式计算模块。

提供分布式任务调度、结果聚合与错误恢复能力，
对标 Ray / Celery / Cadence ADE-XL 分布式作业管理。

学术来源（asyncio 取消机制权威参考）：
- PEP 8 Python 代码风格指南: https://peps.python.org/pep-0008/
- Python asyncio 官方文档 Coroutines and Tasks: https://docs.python.org/3/library/asyncio-task.html
- PEP 492 async/await 语法: https://peps.python.org/pep-0492/
- Real Python Async IO 完整教程: https://realpython.com/async-io-python/
- Python Cookbook 3rd Edition ch12 Concurrency: https://www.oreilly.com/library/view/python-cookbook-3rd/9781449357337/ch12.html
- asyncio Task cancellation 官方章节: https://docs.python.org/3/library/asyncio-task.html#task-cancellation

学术来源（分布式作业管理对标）：
- Ray RLlib: https://docs.ray.io/en/latest/rllib/
- Celery: https://docs.celeryq.dev/
- Cadence ADE-XL 分布式: https://docs.cadence.com/
- IMPALA: Espeholt et al., 2018, https://arxiv.org/abs/1802.01561
- A3C: Mnih et al., 2016, https://arxiv.org/abs/1602.01783

状态机说明:
    PENDING → RUNNING → COMPLETED
                    ↘ FAILED
    PENDING/RUNNING → CANCELLED
    COMPLETED/FAILED/CANCELLED 为终态，不可再转换。

CANCELLED 实现要点（对齐 Python asyncio 官方文档 §Task cancellation）:
- asyncio backend: 调用 asyncio.Task.cancel() 在协程下一次 await 点注入
  CancelledError；协程中 try/except CancelledError 完成资源清理并置位
  CANCELLED 状态后必须 raise 重新抛出，让事件循环正确感知任务已取消。
- CancelledError 自 Python 3.8+ 是 BaseException 子类，禁止用
  ``except Exception`` 捕获（会被静默吞掉，导致任务永不被取消）。
- 同步后端（sequential/threading）采用协作式取消：
  PENDING 状态直接置位 CANCELLED（任务尚未开始，无副作用）；
  RUNNING 状态设置 cancel_requested 标志，由 func 通过
  scheduler.is_cancelled(task_id) 自检决定是否提前退出。
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


class TaskStatus(StrEnum):
    """任务状态枚举。"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskState:
    """任务状态机，封装合法状态转换规则。

    参考 flow/job.py 的 JobState 设计：所有非法转换必须 raise，
    禁止任何 fall-back 静默处理（R03 强制）。
    """

    # 合法状态转换映射：当前状态 → 可达状态集合
    TRANSITIONS: dict[TaskStatus, frozenset[TaskStatus]] = {
        TaskStatus.PENDING: frozenset({TaskStatus.RUNNING, TaskStatus.CANCELLED}),
        TaskStatus.RUNNING: frozenset(
            {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED}
        ),
        TaskStatus.COMPLETED: frozenset(),   # 终态
        TaskStatus.FAILED: frozenset(),      # 终态
        TaskStatus.CANCELLED: frozenset(),   # 终态
    }

    @classmethod
    def can_transition(cls, from_status: TaskStatus, to_status: TaskStatus) -> bool:
        """检查状态转换是否合法"""
        return to_status in cls.TRANSITIONS.get(from_status, frozenset())

    @classmethod
    def is_terminal(cls, status: TaskStatus) -> bool:
        """检查是否为终态（不可再转换）"""
        return len(cls.TRANSITIONS.get(status, frozenset())) == 0

    @classmethod
    def assert_transition(cls, from_status: TaskStatus, to_status: TaskStatus) -> None:
        """断言状态转换合法，非法则抛出 RuntimeError"""
        if not cls.can_transition(from_status, to_status):
            raise RuntimeError(f"非法状态转换: {from_status} → {to_status}")


@dataclass
class TaskResult:
    """任务执行结果。"""

    task_id: str
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: str | None = None
    worker_id: int | None = None
    start_time: float | None = None
    end_time: float | None = None
    retries: int = 0
    cancel_requested: bool = False  # 取消请求标志（同步后端协作式取消）

    @property
    def duration_s(self) -> float | None:
        """执行耗时（秒）。"""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None


@dataclass
class DistributedConfig:
    """分布式配置。

    backend 取值:
    - ``sequential``: 同步顺序执行（默认）
    - ``threading``: ThreadPoolExecutor 多线程并行
    - ``asyncio``: 事件循环 + asyncio.Task，支持真实取消流程
    """

    num_workers: int = 4
    max_retries: int = 2
    task_timeout_s: float = 60.0
    backend: str = "sequential"


class DistributedTaskScheduler:
    """分布式任务调度器。

    支持三种后端，CANCELLED 状态严格走真实取消流程（无假数据 fall-back）：

    - ``sequential``: 同步顺序执行
    - ``threading``:  ThreadPoolExecutor 多线程并行
    - ``asyncio``:    事件循环线程 + asyncio.Task，cancel() 调用
                       asyncio.Task.cancel() 触发 CancelledError，
                       协程中显式 except asyncio.CancelledError 完成清理
                       并置位 CANCELLED 后必须 raise 重新抛出
    """

    def __init__(self, config: DistributedConfig | None = None) -> None:
        self.config = config or DistributedConfig()
        self._tasks: dict[str, TaskResult] = {}
        self._lock = threading.Lock()
        self._shutdown = False
        self._executor = None
        # asyncio 后端状态
        self._loop: asyncio.AbstractEventLoop | None = None
        self._loop_thread: threading.Thread | None = None
        self._async_tasks: dict[str, asyncio.Task] = {}

        backend = self.config.backend
        if backend == "threading":
            from concurrent.futures import ThreadPoolExecutor
            self._executor = ThreadPoolExecutor(max_workers=self.config.num_workers)
        elif backend == "asyncio":
            self._loop = asyncio.new_event_loop()
            self._loop_thread = threading.Thread(
                target=self._loop.run_forever,
                daemon=True,
                name="polaris-scheduler-loop",
            )
            self._loop_thread.start()
        elif backend != "sequential":
            raise ValueError(f"未知后端: {backend}")

    def submit(self, task_id: str, func: Callable, *args, **kwargs) -> str:
        """提交任务。

        Args:
            task_id: 任务唯一标识。
            func: 执行函数。
            *args, **kwargs: 函数参数。

        Returns:
            task_id。

        Raises:
            KeyError: 任务 ID 已存在。
        """
        result = TaskResult(task_id=task_id, status=TaskStatus.PENDING)
        with self._lock:
            if task_id in self._tasks:
                raise KeyError(f"任务 ID 已存在: {task_id}")
            self._tasks[task_id] = result

        if self._loop is not None:
            self._submit_async(task_id, func, *args, **kwargs)
        elif self._executor is not None:
            future = self._executor.submit(
                self._execute_task_sync, task_id, func, *args, **kwargs
            )
            result._future = future  # type: ignore[attr-defined]
        else:
            self._execute_task_sync(task_id, func, *args, **kwargs)

        return task_id

    def _submit_async(self, task_id: str, func: Callable, *args, **kwargs) -> None:
        """在事件循环线程中创建 asyncio.Task（线程安全调度）。"""
        assert self._loop is not None  # 仅在 asyncio 后端调用
        coro = self._execute_task_async(task_id, func, *args, **kwargs)

        def _create_task() -> None:
            assert self._loop is not None
            t = self._loop.create_task(coro)
            with self._lock:
                self._async_tasks[task_id] = t

        # call_soon_threadsafe 保证从其它线程安全调度到事件循环线程
        self._loop.call_soon_threadsafe(_create_task)

    async def _execute_task_async(
        self, task_id: str, func: Callable, *args, **kwargs
    ) -> None:
        """asyncio 后端任务执行协程（含重试 + 真实取消流程）。

        CancelledError 是 BaseException 子类（Python 3.8+），
        显式 ``except asyncio.CancelledError`` 捕获完成清理后必须 raise，
        让事件循环感知取消完成。禁止用 ``except Exception`` 捕获。
        """
        result = self._tasks.get(task_id)
        if result is None:
            raise KeyError(f"任务不存在: {task_id}")

        # 处理 cancel() 在 create_task 之前到达的窗口期
        if result.cancel_requested:
            self._mark_cancelled(result)
            raise asyncio.CancelledError()

        loop = asyncio.get_running_loop()
        self._mark_running(result)
        for attempt in range(self.config.max_retries + 1):
            with self._lock:
                result.retries = attempt
            try:
                # 同步 func 通过 run_in_executor 在线程中执行；
                # 若 cancel() 已调用，下一次 await 点会注入 CancelledError
                output = await loop.run_in_executor(
                    None, lambda: func(*args, **kwargs)
                )
                # 执行结束但期间收到取消请求：仍按取消处理
                if result.cancel_requested:
                    self._mark_cancelled(result)
                    raise asyncio.CancelledError()
                self._mark_completed(result, output)
                return
            except asyncio.CancelledError:
                # 真实取消流程：cancel() → CancelledError → 置位 → raise
                self._mark_cancelled(result)
                raise  # 必须 re-raise，让事件循环知道任务已取消
            except Exception as e:
                if not self._handle_failure(result, e, attempt):
                    return
                await asyncio.sleep(0.1 * (attempt + 1))
                continue

    def _execute_task_sync(self, task_id: str, func: Callable, *args, **kwargs) -> None:
        """同步后端任务执行（含重试 + 协作式取消检查）。

        同步 func 无法被外部中断；协作式取消通过 cancel_requested 标志：
        - 任务启动前检查标志，若已取消则直接置位 CANCELLED
        - 每次重试前检查标志
        - 任务执行后检查标志，若已取消则保持 CANCELLED 不标记 COMPLETED
        """
        result = self._tasks.get(task_id)
        if result is None:
            raise KeyError(f"任务不存在: {task_id}")

        # 启动前检查取消标志（PENDING → CANCELLED）
        if result.cancel_requested:
            self._mark_cancelled(result)
            return

        self._mark_running(result)
        for attempt in range(self.config.max_retries + 1):
            if result.cancel_requested:
                self._mark_cancelled(result)
                return
            with self._lock:
                result.retries = attempt
            try:
                output = func(*args, **kwargs)
                if result.cancel_requested:
                    self._mark_cancelled(result)
                    return
                self._mark_completed(result, output)
                return
            except Exception as e:
                if not self._handle_failure(result, e, attempt):
                    return
                time.sleep(0.1 * (attempt + 1))
                continue

    def _mark_running(self, result: TaskResult) -> None:
        """状态转换 PENDING → RUNNING。"""
        with self._lock:
            TaskState.assert_transition(result.status, TaskStatus.RUNNING)
            result.status = TaskStatus.RUNNING
            result.start_time = time.time()
            result.retries = 0
        logger.info("任务 %s 开始执行", result.task_id)

    def _mark_completed(self, result: TaskResult, output: Any) -> None:
        """状态转换 RUNNING → COMPLETED。"""
        with self._lock:
            TaskState.assert_transition(result.status, TaskStatus.COMPLETED)
            result.result = output
            result.status = TaskStatus.COMPLETED
            result.end_time = time.time()
        logger.info("任务 %s 完成", result.task_id)

    def _mark_cancelled(self, result: TaskResult) -> None:
        """状态转换 → CANCELLED（可从 PENDING 或 RUNNING 转换）。"""
        with self._lock:
            if result.status == TaskStatus.CANCELLED:
                return
            TaskState.assert_transition(result.status, TaskStatus.CANCELLED)
            result.status = TaskStatus.CANCELLED
            result.end_time = time.time()
        logger.warning("任务 %s 已取消", result.task_id)

    def _handle_failure(
        self, result: TaskResult, e: Exception, attempt: int
    ) -> bool:
        """处理失败：可重试返回 True（状态保持 RUNNING）；耗尽重试置位 FAILED 返回 False。"""
        logger.warning(
            "任务 %s 失败（第 %d 次尝试）: %s", result.task_id, attempt + 1, e
        )
        if attempt < self.config.max_retries:
            return True
        with self._lock:
            TaskState.assert_transition(result.status, TaskStatus.FAILED)
            result.status = TaskStatus.FAILED
            result.error = str(e)
            result.end_time = time.time()
        return False

    def cancel(self, task_id: str) -> bool:
        """取消任务（真实取消流程，禁止假数据 fall-back）。

        - asyncio 后端：调用 ``asyncio.Task.cancel()`` 在协程下一次 await
          点注入 CancelledError；协程中显式 except 并置位 CANCELLED 后
          必须重新 raise
        - 同步后端：协作式取消
          * PENDING 状态：直接置位 CANCELLED（任务尚未开始，无副作用）
          * RUNNING 状态：设置 cancel_requested 标志，由 func 通过
            ``is_cancelled(task_id)`` 自检决定是否提前退出

        Args:
            task_id: 任务 ID。

        Returns:
            True 表示取消请求已发出；False 表示任务已终态无法取消。

        Raises:
            KeyError: 任务不存在。
        """
        with self._lock:
            result = self._tasks.get(task_id)
            if result is None:
                raise KeyError(f"任务不存在: {task_id}")
            if TaskState.is_terminal(result.status):
                return False
            result.cancel_requested = True

        # asyncio 后端：触发真实 CancelledError
        if self._loop is not None:
            with self._lock:
                async_task = self._async_tasks.get(task_id)
            if async_task is not None and not async_task.done():
                # 必须从事件循环线程调用 cancel（线程安全）
                self._loop.call_soon_threadsafe(async_task.cancel)
                return True
            # asyncio.Task 尚未创建（极短窗口）：协程启动时自检标志置位
            return True

        # 同步后端：PENDING 直接置位 CANCELLED；RUNNING 等待协程自检标志
        with self._lock:
            if result.status == TaskStatus.PENDING:
                TaskState.assert_transition(result.status, TaskStatus.CANCELLED)
                result.status = TaskStatus.CANCELLED
                result.end_time = time.time()
        return True

    def is_cancelled(self, task_id: str) -> bool:
        """查询任务取消标志（供同步 func 协作式自检）。

        Args:
            task_id: 任务 ID。

        Returns:
            True 表示已收到取消请求。

        Raises:
            KeyError: 任务不存在。
        """
        with self._lock:
            result = self._tasks.get(task_id)
            if result is None:
                raise KeyError(f"任务不存在: {task_id}")
            return result.cancel_requested

    def get_result(self, task_id: str) -> TaskResult | None:
        """获取任务结果。"""
        with self._lock:
            return self._tasks.get(task_id)

    def list_results(self, status: TaskStatus | None = None) -> list[TaskResult]:
        """列出所有任务结果。"""
        with self._lock:
            results = list(self._tasks.values())
        if status is not None:
            results = [r for r in results if r.status == status]
        return results

    def aggregate_results(self) -> dict:
        """聚合所有已完成任务的结果。"""
        completed = self.list_results(TaskStatus.COMPLETED)
        aggregated = {
            "total_tasks": len(self._tasks),
            "completed": len(completed),
            "failed": len(self.list_results(TaskStatus.FAILED)),
            "cancelled": len(self.list_results(TaskStatus.CANCELLED)),
            "results": {r.task_id: r.result for r in completed},
        }
        return aggregated

    def wait_all(self, timeout: float = 30.0) -> bool:
        """等待所有任务进入终态（COMPLETED/FAILED/CANCELLED）。"""
        deadline = time.time() + timeout
        while time.time() < deadline:
            with self._lock:
                all_done = all(
                    TaskState.is_terminal(r.status) for r in self._tasks.values()
                )
            if all_done:
                return True
            time.sleep(0.05)
        return False

    def shutdown(self) -> None:
        """关闭调度器（含 asyncio 事件循环与线程池）。"""
        self._shutdown = True
        if self._executor is not None:
            self._executor.shutdown(wait=False)
        if self._loop is not None:
            self._loop.call_soon_threadsafe(self._loop.stop)
            if self._loop_thread is not None:
                self._loop_thread.join(timeout=2.0)
            self._loop.close()


__all__ = [
    "TaskStatus",
    "TaskState",
    "TaskResult",
    "DistributedConfig",
    "DistributedTaskScheduler",
]
