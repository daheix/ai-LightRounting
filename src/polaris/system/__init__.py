"""J01 系统级/分布式计算模块。

提供分布式任务调度、结果聚合与错误恢复能力，
对标 Ray / Celery / Cadence ADE-XL 分布式作业管理。

学术来源:
- Ray RLlib: https://docs.ray.io/en/latest/rllib/
- Celery: https://docs.celeryq.dev/
- Cadence ADE-XL 分布式: https://docs.cadence.com/
- IMPALA: Espeholt et al., 2018, https://arxiv.org/abs/1802.01561
- A3C: Mnih et al., 2016, https://arxiv.org/abs/1602.01783
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """任务状态枚举。"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


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

    @property
    def duration_s(self) -> float | None:
        """执行耗时（秒）。"""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None


@dataclass
class DistributedConfig:
    """分布式配置。"""

    num_workers: int = 4
    max_retries: int = 2
    task_timeout_s: float = 60.0
    backend: str = "sequential"


class DistributedTaskScheduler:
    """分布式任务调度器。

    支持顺序后端与线程后端，提供任务提交、结果聚合与错误恢复。
    """

    def __init__(self, config: DistributedConfig | None = None) -> None:
        self.config = config or DistributedConfig()
        self._tasks: dict[str, TaskResult] = {}
        self._lock = threading.Lock()
        self._shutdown = False
        self._executor = None
        if self.config.backend == "threading":
            from concurrent.futures import ThreadPoolExecutor
            self._executor = ThreadPoolExecutor(max_workers=self.config.num_workers)

    def submit(self, task_id: str, func: Callable, *args, **kwargs) -> str:
        """提交任务。

        Args:
            task_id: 任务唯一标识。
            func: 执行函数。
            *args, **kwargs: 函数参数。

        Returns:
            task_id。
        """
        result = TaskResult(task_id=task_id, status=TaskStatus.PENDING)
        with self._lock:
            self._tasks[task_id] = result

        if self._executor is not None:
            future = self._executor.submit(
                self._execute_task, task_id, func, *args, **kwargs
            )
            result._future = future
        else:
            self._execute_task(task_id, func, *args, **kwargs)

        return task_id

    def _execute_task(self, task_id: str, func: Callable, *args, **kwargs) -> None:
        """执行单个任务（含重试逻辑）。"""
        result = self._tasks.get(task_id)
        if result is None:
            return

        for attempt in range(self.config.max_retries + 1):
            try:
                with self._lock:
                    result.status = TaskStatus.RUNNING
                    result.start_time = time.time()
                    result.retries = attempt

                logger.info("任务 %s 开始执行（第 %d 次尝试）", task_id, attempt + 1)
                output = func(*args, **kwargs)

                with self._lock:
                    result.result = output
                    result.status = TaskStatus.COMPLETED
                    result.end_time = time.time()

                logger.info("任务 %s 完成", task_id)
                return

            except Exception as e:
                logger.warning("任务 %s 失败（第 %d 次尝试）: %s", task_id, attempt + 1, e)
                if attempt < self.config.max_retries:
                    time.sleep(0.1 * (attempt + 1))
                    continue
                with self._lock:
                    result.status = TaskStatus.FAILED
                    result.error = str(e)
                    result.end_time = time.time()

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
            "results": {r.task_id: r.result for r in completed},
        }
        return aggregated

    def wait_all(self, timeout: float = 30.0) -> bool:
        """等待所有任务完成。"""
        deadline = time.time() + timeout
        while time.time() < deadline:
            with self._lock:
                all_done = all(
                    r.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED)
                    for r in self._tasks.values()
                )
            if all_done:
                return True
            time.sleep(0.05)
        return False

    def shutdown(self) -> None:
        """关闭调度器。"""
        self._shutdown = True
        if self._executor is not None:
            self._executor.shutdown(wait=False)


__all__ = [
    "TaskStatus",
    "TaskResult",
    "DistributedConfig",
    "DistributedTaskScheduler",
]
