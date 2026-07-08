"""PoLaRIS Web Server - 辅助工具模块（polaris-gui 子模块）。

从 ``web_server.py`` 拆分而来，包含全局变量与 scheduler/tracker 获取函数。

来源:
- Python http.server: https://docs.python.org/3/library/http.server.html
- Python threading（双重检查锁定） https://docs.python.org/3/library/threading.html
- Double-checked locking pattern
  https://en.wikipedia.org/wiki/Double-checked_locking
- DREAMPlace (布局布线深度学习, 对标作业队列)
  https://arxiv.org/abs/2004.10746
- TILOS MacroPlacement benchmark
  https://github.com/TILOS-AI-CAD-Institute/MacroPlacement
- Apollo (ASU 布局布线 RL) https://github.com/ASU-LOPE-Group/Apollo

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU。
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from polaris_flow.scheduler import JobScheduler
    from polaris_flow.tracker import JobTracker

logger = logging.getLogger(__name__)

_STATIC_DIR = Path(__file__).parent / "static"

# Showcase 后台任务锁（保护 _showcase_state 全局状态）
_showcase_lock = threading.Lock()

# 全局作业锁（保护 scheduler/tracker 单例的原子操作）
_global_lock = threading.Lock()


def _get_scheduler() -> JobScheduler:
    """获取全局作业调度器（懒初始化，线程安全）。

    首次调用时创建 JobScheduler 实例，注入标准 10 阶段执行函数，
    后续调用复用同一实例。对齐 Cadence ADE-XL 的全局作业队列模型。

    R05 Bug 修复 v4.0-WEB-LOCK: 加 _global_lock 双重检查锁定，
    防止 ThreadingHTTPServer 下多线程并发创建多个 scheduler 实例。
    文献: Python threading.Lock https://docs.python.org/3/library/threading.html#lock-objects
    文献: Double-checked locking https://en.wikipedia.org/wiki/Double-checked_locking
    """
    global _global_scheduler
    if _global_scheduler is None:
        with _global_lock:
            # 双重检查锁定：进入锁后再检查一次，防止多线程同时通过第一次检查
            if _global_scheduler is None:
                from polaris_flow.executors import STAGE_EXECUTORS
                from polaris_flow.scheduler import JobScheduler

                _global_scheduler = JobScheduler(
                    max_workers=4, stage_executors=STAGE_EXECUTORS
                )
    return _global_scheduler


def _get_tracker() -> JobTracker:
    """获取全局作业追踪器（懒初始化，线程安全）。

    首次调用时创建 JobTracker 实例，扫描 out/jobs 目录，
    后续调用复用同一实例。

    R05 Bug 修复 v4.0-WEB-LOCK: 加 _global_lock 双重检查锁定。
    """
    global _global_tracker
    if _global_tracker is None:
        with _global_lock:
            if _global_tracker is None:
                from polaris_flow.tracker import JobTracker

                _global_tracker = JobTracker(base_output_dir="out/jobs")
    return _global_tracker

