"""作业调度器（JobScheduler）+ FIFO 队列 + worker 池。

对齐商业 EDA 工具的作业调度模型：
- Luceda IPKISS: 设计任务的顺序与并行执行
- Cadence ADE-XL: 作业队列 + 资源调度 + 并行 worker（核心对齐对象）
- Synopsys ICC2: 实现流程的分布式调度
- Ansys Lumerical: 仿真任务的并发执行

学术来源:
- IPKISS 任务调度: https://docs.lucedaphotonics.com/
- Cadence ADE-XL 作业队列与 worker 池: https://docs.cadence.com/
- Synopsys ICC2 分布式调度: https://www.synopsys.com/
- Ansys Lumerical 并发执行: https://www.ansys.com/products/photonics
- Apache Airflow, 工作流编排系统: https://airflow.apache.org/
- Slurm, 高性能计算作业调度器: https://slurm.schedmd.com/

调度模型:
    submit(job) → FIFO 队列 → dispatcher 线程 → ThreadPoolExecutor worker 池
    每个 worker 按 Recipe.enabled_stages 顺序执行各阶段，
    阶段间通过 prev_outputs 字典传递数据。
    任何阶段失败则整个作业失败（禁止 fall-back 跳过失败阶段）。
"""

from __future__ import annotations

import logging
import queue
import threading
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime

from polaris.flow.job import Job, JobStatus
from polaris.flow.recipe import Recipe
from polaris.flow.stage import StageResult, StageStatus, get_stage
from polaris.flow.workspace import Workspace

logger = logging.getLogger(__name__)

# 阶段执行函数类型：接收 (recipe, workspace, prev_outputs) 返回输出字典
StageExecuteFn = Callable[[Recipe, Workspace, dict], dict]


class JobScheduler:
    """作业调度器

    对齐 Cadence ADE-XL 的作业队列 + 资源调度 + 并行 worker 模型。

    - submit(): 将作业放入 FIFO 队列
    - dispatcher 线程: 从队列取作业，分配给 worker 池
    - worker 线程: 按 Recipe.enabled_stages 顺序执行各阶段
    - cancel(): 取消队列中或运行中的作业
    """

    def __init__(
        self,
        max_workers: int = 4,
        stage_executors: dict[int, StageExecuteFn] | None = None,
    ):
        self.max_workers = max_workers
        self.stage_executors: dict[int, StageExecuteFn] = stage_executors or {}
        self._queue: queue.Queue[Job] = queue.Queue()
        self._jobs: dict[str, Job] = {}
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._running_futures: dict[str, Future] = {}
        self._lock = threading.Lock()
        self._shutdown = False
        # 启动调度线程
        self._dispatcher_thread = threading.Thread(target=self._dispatch_loop, daemon=True)
        self._dispatcher_thread.start()

    def submit(self, job: Job) -> str:
        """提交作业到队列"""
        with self._lock:
            self._jobs[job.job_id] = job
        self._queue.put(job)
        job.workspace.write_log(f"作业 {job.job_id} 已提交到队列")
        logger.info("作业 %s 已提交", job.job_id)
        return job.job_id

    def cancel(self, job_id: str) -> bool:
        """取消作业"""
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return False
            if job.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
                return False
            job.mark_cancelled()
            job.workspace.write_log(f"作业 {job_id} 已取消", "WARNING")
            # 取消正在执行的 future
            future = self._running_futures.pop(job_id, None)
            if future:
                future.cancel()
        logger.info("作业 %s 已取消", job_id)
        return True

    def get_job(self, job_id: str) -> Job | None:
        """获取作业"""
        with self._lock:
            return self._jobs.get(job_id)

    def list_jobs(self, status: JobStatus | None = None) -> list[Job]:
        """列出作业"""
        with self._lock:
            jobs = list(self._jobs.values())
        if status is not None:
            jobs = [j for j in jobs if j.status == status]
        return jobs

    def shutdown(self) -> None:
        """关闭调度器"""
        self._shutdown = True
        self._executor.shutdown(wait=False)

    def _dispatch_loop(self) -> None:
        """调度循环：从队列取作业分配给 worker"""
        while not self._shutdown:
            try:
                job = self._queue.get(timeout=0.5)
            except queue.Empty:
                continue
            with self._lock:
                if job.status == JobStatus.CANCELLED:
                    continue
            future = self._executor.submit(self._execute_job, job)
            with self._lock:
                self._running_futures[job.job_id] = future

    def _execute_single_stage(
        self, job: Job, stage_id: int, prev_outputs: dict,
    ) -> bool:
        """执行单个阶段。

        Args:
            job: 作业对象。
            stage_id: 阶段 ID。
            prev_outputs: 之前阶段输出字典（成功时会被原地更新）。

        Returns:
            True 表示阶段成功完成或正常跳过；False 表示阶段失败（已标记作业 FAILED）。
        """
        stage = get_stage(stage_id)
        result = StageResult(
            stage_id=stage_id,
            name=stage.name,
            status=StageStatus.RUNNING,
            start_time=datetime.now(),
        )
        try:
            execute_fn = self.stage_executors.get(stage_id)
            if execute_fn is None:
                result.status = StageStatus.SKIPPED
                result.error = f"阶段 {stage_id} 无执行函数，跳过"
                job.workspace.write_log(
                    f"阶段 {stage_id} ({stage.name}) 无执行函数，跳过",
                    "WARNING",
                )
            else:
                output_data = execute_fn(job.recipe, job.workspace, prev_outputs)
                result.output.data = output_data
                result.status = StageStatus.COMPLETED
                result.end_time = datetime.now()
                # 持久化阶段输出
                job.workspace.write_stage_output(stage.slug, output_data)
                prev_outputs.update(output_data)
                job.workspace.write_log(f"阶段 {stage_id} ({stage.name}) 完成")

            job.stage_results.append(result)
            job.current_stage = stage_id
            job.workspace.write_job_metadata(job.to_dict())
            return True
        except Exception as e:
            result.status = StageStatus.FAILED
            result.error = str(e)
            result.end_time = datetime.now()
            job.stage_results.append(result)
            job.mark_failed(f"阶段 {stage_id} ({stage.name}) 失败: {e}")
            job.workspace.write_log(f"阶段 {stage_id} 失败: {e}", "ERROR")
            job.workspace.write_job_metadata(job.to_dict())
            logger.exception("作业 %s 阶段 %d 失败", job.job_id, stage_id)
            return False

    def _execute_job(self, job: Job) -> None:
        """执行作业（worker 线程中运行）

        按 Recipe.enabled_stages 顺序执行各阶段，阶段间通过 prev_outputs 传递数据。
        任何阶段失败则整个作业标记为 FAILED 并终止。
        """
        try:
            job.mark_running()
            job.workspace.write_job_metadata(job.to_dict())
            job.workspace.write_log(f"作业 {job.job_id} 开始执行")

            prev_outputs: dict = {}
            for stage_id in job.recipe.enabled_stages:
                # 检查是否已取消
                if job.status == JobStatus.CANCELLED:
                    job.workspace.write_log(
                        f"作业 {job.job_id} 在阶段 {stage_id} 前被取消", "WARNING"
                    )
                    return
                if not self._execute_single_stage(job, stage_id, prev_outputs):
                    return

            job.current_stage = len(job.recipe.enabled_stages)
            job.mark_completed()
            job.workspace.write_log(f"作业 {job.job_id} 全部完成")
            job.workspace.write_job_metadata(job.to_dict())
            # 写入汇总报告
            report = self._generate_report(job)
            job.workspace.write_report(report)
            logger.info("作业 %s 完成", job.job_id)
        except Exception as e:
            # 作业执行异常（如状态转换失败）：记录错误并持久化当前状态
            logger.exception("作业 %s 执行异常", job.job_id)
            try:
                if job.status == JobStatus.RUNNING:
                    job.mark_failed(str(e))
                job.workspace.write_log(f"作业执行异常: {e}", "ERROR")
                job.workspace.write_job_metadata(job.to_dict())
            except RuntimeError as re:
                # 状态转换失败时记录但不静默吞没
                logger.error(
                    "作业 %s 状态转换失败，当前状态 %s: %s",
                    job.job_id,
                    job.status,
                    re,
                )

    @staticmethod
    def _generate_report(job: Job) -> dict:
        """生成汇总报告"""
        return {
            "job_id": job.job_id,
            "status": job.status.value,
            "total_stages": len(job.recipe.enabled_stages),
            "completed_stages": sum(
                1 for r in job.stage_results if r.status == StageStatus.COMPLETED
            ),
            "failed_stages": sum(1 for r in job.stage_results if r.status == StageStatus.FAILED),
            "skipped_stages": sum(1 for r in job.stage_results if r.status == StageStatus.SKIPPED),
            "submit_time": job.submit_time.isoformat(),
            "start_time": job.start_time.isoformat() if job.start_time else None,
            "end_time": job.end_time.isoformat() if job.end_time else None,
            "stage_summaries": [
                {
                    "stage_id": r.stage_id,
                    "name": r.name,
                    "status": r.status.value,
                    "duration_s": r.duration_s,
                    "error": r.error,
                }
                for r in job.stage_results
            ],
        }
