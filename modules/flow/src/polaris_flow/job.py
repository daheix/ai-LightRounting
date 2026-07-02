"""作业（Job）数据结构 + 状态枚举 + 状态机。

对齐商业 EDA 工具的作业管理抽象：
- Luceda IPKISS: 设计流程中的"设计任务"概念，含提交/执行/完成生命周期
- Cadence ADE-XL: 作业队列与状态管理（Queued/Running/Done/Failed）
- Synopsys ICC2: 实现流程中的 job/run 模型
- Ansys Lumerical: 仿真任务的提交与追踪

学术来源:
- IPKISS 设计流程: https://docs.lucedaphotonics.com/
- Cadence ADE-XL 作业管理: https://docs.cadence.com/
- Synopsys ICC2 实现流程: https://www.synopsys.com/
- Ansys Lumerical 仿真任务: https://www.ansys.com/products/photonics

状态机说明:
    QUEUED → RUNNING → COMPLETED
                    ↘ FAILED
    QUEUED/RUNNING → CANCELLED
    COMPLETED/FAILED/CANCELLED 为终态，不可再转换。


## 补充文献（R02 学术诚信补齐）
- Ansys Lumerical 文档: https://optics.ansys.com/hc/en-us
- Lumerical CML Compiler: https://optics.ansys.com/hc/en-us/articles/360057929454-S-parameter-passive-workflow
"""

from __future__ import annotations

import random
import string
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from polaris_flow.recipe import Recipe
    from polaris_flow.stage import StageResult
    from polaris_flow.workspace import Workspace


class JobStatus(StrEnum):
    """作业状态枚举（对齐 Cadence ADE-XL 的作业状态）"""

    QUEUED = "queued"        # 已提交，等待执行
    RUNNING = "running"      # 正在执行
    COMPLETED = "completed"  # 全部阶段成功完成
    FAILED = "failed"        # 执行失败
    CANCELLED = "cancelled"  # 被取消


class JobState:
    """作业状态机，封装合法状态转换规则。

    提供状态转换合法性检查与终态判定，供 Job 类与调度器复用。
    所有非法转换必须直接拒绝（raise），禁止任何 fall-back 静默处理。
    """

    # 合法状态转换映射：当前状态 → 可达状态集合
    TRANSITIONS: dict[JobStatus, frozenset[JobStatus]] = {
        JobStatus.QUEUED: frozenset({JobStatus.RUNNING, JobStatus.CANCELLED}),
        JobStatus.RUNNING: frozenset(
            {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED}
        ),
        JobStatus.COMPLETED: frozenset(),   # 终态
        JobStatus.FAILED: frozenset(),      # 终态
        JobStatus.CANCELLED: frozenset(),   # 终态
    }

    @classmethod
    def can_transition(cls, from_status: JobStatus, to_status: JobStatus) -> bool:
        """检查状态转换是否合法"""
        return to_status in cls.TRANSITIONS.get(from_status, frozenset())

    @classmethod
    def is_terminal(cls, status: JobStatus) -> bool:
        """检查是否为终态（不可再转换）"""
        return len(cls.TRANSITIONS.get(status, frozenset())) == 0

    @classmethod
    def assert_transition(cls, from_status: JobStatus, to_status: JobStatus) -> None:
        """断言状态转换合法，非法则抛出 RuntimeError"""
        if not cls.can_transition(from_status, to_status):
            raise RuntimeError(f"非法状态转换: {from_status} → {to_status}")


@dataclass
class Job:
    """作业数据结构，表示一次完整的 10 阶段流水线执行。

    对齐 Luceda IPKISS 的"设计任务"与 Cadence ADE-XL 的"run"概念：
    一个 Job 绑定一个 Recipe（配方）和一个 Workspace（工作空间），
    按 Recipe.enabled_stages 顺序执行各阶段。
    """

    job_id: str  # 时间戳格式 YYYYMMDD_HHMMSS_<6位随机>
    recipe: Recipe  # 前向引用
    workspace: Workspace  # 前向引用
    status: JobStatus = JobStatus.QUEUED
    stage_results: list[StageResult] = field(default_factory=list)
    submit_time: datetime = field(default_factory=datetime.now)
    start_time: datetime | None = None
    end_time: datetime | None = None
    error: str | None = None
    current_stage: int = 0  # 当前执行到的阶段（0=未开始，1-10=阶段N，10=全部完成）

    def mark_running(self) -> None:
        """状态转换 QUEUED → RUNNING"""
        JobState.assert_transition(self.status, JobStatus.RUNNING)
        self.status = JobStatus.RUNNING
        self.start_time = datetime.now()

    def mark_completed(self) -> None:
        """状态转换 RUNNING → COMPLETED"""
        JobState.assert_transition(self.status, JobStatus.COMPLETED)
        self.status = JobStatus.COMPLETED
        self.end_time = datetime.now()

    def mark_failed(self, error: str) -> None:
        """状态转换 RUNNING → FAILED"""
        JobState.assert_transition(self.status, JobStatus.FAILED)
        self.status = JobStatus.FAILED
        self.error = error
        self.end_time = datetime.now()

    def mark_cancelled(self) -> None:
        """状态转换 → CANCELLED（可从 QUEUED 或 RUNNING 转换）"""
        JobState.assert_transition(self.status, JobStatus.CANCELLED)
        self.status = JobStatus.CANCELLED
        self.end_time = datetime.now()

    @property
    def progress(self) -> str:
        """进度字符串，如 '3/10'"""
        total = len(self.recipe.enabled_stages)
        return f"{self.current_stage}/{total}"

    def to_dict(self) -> dict:
        """序列化为字典（用于 JSON 持久化）"""
        return {
            "job_id": self.job_id,
            "status": self.status.value,
            "submit_time": self.submit_time.isoformat(),
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "current_stage": self.current_stage,
            "progress": self.progress,
            "error": self.error,
            "recipe": self.recipe.to_dict() if hasattr(self.recipe, "to_dict") else None,
        }

    @classmethod
    def generate_job_id(cls) -> str:
        """生成唯一 job_id：YYYYMMDD_HHMMSS_<6位随机>"""
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
        return f"{ts}_{suffix}"
