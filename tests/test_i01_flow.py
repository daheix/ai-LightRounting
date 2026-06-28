"""I01 流程编排验收测试（Job/Stage/Scheduler）。

覆盖验收标准：
- M1: Job/Stage 状态机正确（pending→running→done/failed）
- M2: Scheduler 调度正确（依赖顺序、并行度）
- M3: 执行器（顺序/并行）正确

学术来源:
- Cadence ADE-XL 作业管理: https://docs.cadence.com/
- Synopsys ICC2 实现流程: https://www.synopsys.com/
- IPKISS 设计流程: https://docs.lucedaphotonics.com/
- Ansys Lumerical 仿真任务: https://www.ansys.com/products/photonics
- DREAMPlace 调度: https://arxiv.org/abs/2004.10746
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from polaris.flow.job import Job, JobState, JobStatus
from polaris.flow.recipe import Recipe, SimConfig
from polaris.flow.scheduler import JobScheduler
from polaris.flow.stage import (
    STANDARD_STAGES,
    StageInput,
    StageOutput,
    StageResult,
    StageStatus,
    get_stage,
)
from polaris.flow.tracker import JobTracker
from polaris.flow.workspace import Workspace

# =============================================================================
# 辅助函数
# =============================================================================


def _make_job(tmp_path: Path, job_id: str = "test_job_001", enabled_stages: list[int] | None = None) -> Job:
    """构造一个绑定临时工作空间的 Job。"""
    recipe = Recipe()
    if enabled_stages is not None:
        recipe.enabled_stages = enabled_stages
    ws = Workspace(str(tmp_path), job_id)
    return Job(job_id=job_id, recipe=recipe, workspace=ws)


def _wait_for_status(job: Job, target: JobStatus, timeout: float = 10.0) -> bool:
    """轮询作业状态，直到达到目标状态或超时。"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if job.status == target:
            return True
        time.sleep(0.05)
    return False


# =============================================================================
# M1: Job/Stage 状态机测试
# =============================================================================


class TestJobStateMachine:
    """Job 状态机正确性测试。"""

    def test_initial_status_is_queued(self, tmp_path):
        """初始状态应为 QUEUED。"""
        job = _make_job(tmp_path)
        assert job.status == JobStatus.QUEUED

    def test_queued_to_running_transition(self, tmp_path):
        """QUEUED → RUNNING 转换合法。"""
        job = _make_job(tmp_path)
        job.mark_running()
        assert job.status == JobStatus.RUNNING
        assert job.start_time is not None

    def test_running_to_completed_transition(self, tmp_path):
        """RUNNING → COMPLETED 转换合法。"""
        job = _make_job(tmp_path)
        job.mark_running()
        job.mark_completed()
        assert job.status == JobStatus.COMPLETED
        assert job.end_time is not None

    def test_running_to_failed_transition(self, tmp_path):
        """RUNNING → FAILED 转换合法。"""
        job = _make_job(tmp_path)
        job.mark_running()
        job.mark_failed("测试错误")
        assert job.status == JobStatus.FAILED
        assert job.error == "测试错误"
        assert job.end_time is not None

    def test_queued_to_cancelled_transition(self, tmp_path):
        """QUEUED → CANCELLED 转换合法。"""
        job = _make_job(tmp_path)
        job.mark_cancelled()
        assert job.status == JobStatus.CANCELLED

    def test_running_to_cancelled_transition(self, tmp_path):
        """RUNNING → CANCELLED 转换合法。"""
        job = _make_job(tmp_path)
        job.mark_running()
        job.mark_cancelled()
        assert job.status == JobStatus.CANCELLED

    def test_invalid_transition_raises(self, tmp_path):
        """非法状态转换应抛出 RuntimeError。"""
        job = _make_job(tmp_path)
        with pytest.raises(RuntimeError, match="非法状态转换"):
            job.mark_completed()

    def test_terminal_state_cannot_transition(self, tmp_path):
        """终态不可再转换。"""
        job = _make_job(tmp_path)
        job.mark_running()
        job.mark_completed()
        assert JobState.is_terminal(job.status)
        with pytest.raises(RuntimeError):
            job.mark_failed("再试一次")

    def test_job_state_can_transition_method(self):
        """JobState.can_transition 方法正确性。"""
        assert JobState.can_transition(JobStatus.QUEUED, JobStatus.RUNNING)
        assert JobState.can_transition(JobStatus.RUNNING, JobStatus.COMPLETED)
        assert JobState.can_transition(JobStatus.RUNNING, JobStatus.FAILED)
        assert not JobState.can_transition(JobStatus.COMPLETED, JobStatus.RUNNING)
        assert not JobState.can_transition(JobStatus.FAILED, JobStatus.COMPLETED)

    def test_job_progress_property(self, tmp_path):
        """progress 属性返回正确格式。"""
        job = _make_job(tmp_path)
        assert job.progress == "0/10"
        job.current_stage = 3
        assert job.progress == "3/10"

    def test_job_to_dict(self, tmp_path):
        """to_dict 序列化包含必要字段。"""
        job = _make_job(tmp_path)
        d = job.to_dict()
        assert "job_id" in d
        assert "status" in d
        assert "progress" in d
        assert "current_stage" in d

    def test_job_id_generation(self):
        """generate_job_id 生成唯一 ID。"""
        id1 = Job.generate_job_id()
        id2 = Job.generate_job_id()
        assert id1 != id2
        assert len(id1) > 10


# =============================================================================
# Stage 状态与结构测试
# =============================================================================


class TestStageStructure:
    """Stage 数据结构与标准阶段定义测试。"""

    def test_standard_stages_count(self):
        """标准阶段应为 10 个。"""
        assert len(STANDARD_STAGES) == 10

    def test_get_stage_valid_id(self):
        """get_stage 可获取有效阶段。"""
        s = get_stage(1)
        assert s.stage_id == 1
        assert s.name == "PDK 器件目录"

    def test_get_stage_invalid_id_raises(self):
        """get_stage 无效 ID 抛 ValueError。"""
        with pytest.raises(ValueError, match="未知阶段 ID"):
            get_stage(999)

    def test_stage_dependencies(self):
        """阶段依赖关系正确。"""
        s2 = get_stage(2)
        assert 1 in s2.depends_on
        s3 = get_stage(3)
        assert 2 in s3.depends_on
        s4 = get_stage(4)
        assert 3 in s4.depends_on

    def test_stage_input_output_dataclass(self):
        """StageInput/StageOutput 数据类正确。"""
        si = StageInput(data={"key": "value"})
        assert si.data["key"] == "value"
        so = StageOutput(data={"out": 123}, files=["a.gds"])
        assert so.data["out"] == 123
        assert len(so.files) == 1

    def test_stage_result_duration(self):
        """StageResult.duration_s 计算耗时。"""
        from datetime import datetime, timedelta

        start = datetime.now()
        end = start + timedelta(seconds=5)
        r = StageResult(
            stage_id=1,
            name="test",
            status=StageStatus.COMPLETED,
            start_time=start,
            end_time=end,
        )
        assert r.duration_s is not None
        assert r.duration_s >= 4.9

    def test_stage_result_duration_none_when_incomplete(self):
        """未完成时 duration_s 返回 None。"""
        r = StageResult(stage_id=1, name="test", status=StageStatus.RUNNING)
        assert r.duration_s is None


# =============================================================================
# M2: Scheduler 调度测试
# =============================================================================


class TestJobScheduler:
    """JobScheduler 调度正确性测试。"""

    def test_scheduler_submit_job(self, tmp_path):
        """提交作业后可查询。"""
        scheduler = JobScheduler(max_workers=2)
        try:
            job = _make_job(tmp_path, "sched_test_1")
            job_id = scheduler.submit(job)
            assert job_id == "sched_test_1"
            retrieved = scheduler.get_job(job_id)
            assert retrieved is not None
            assert retrieved.job_id == job_id
        finally:
            scheduler.shutdown()

    def test_scheduler_list_jobs(self, tmp_path):
        """list_jobs 可列出所有作业。"""
        scheduler = JobScheduler(max_workers=2)
        try:
            job1 = _make_job(tmp_path, "list_test_1")
            job2 = _make_job(tmp_path, "list_test_2")
            scheduler.submit(job1)
            scheduler.submit(job2)
            time.sleep(0.2)
            jobs = scheduler.list_jobs()
            assert len(jobs) >= 2
        finally:
            scheduler.shutdown()

    def test_scheduler_cancel_completed_job_returns_false(self, tmp_path):
        """取消已完成作业返回 False。"""
        def fast_executor(recipe, workspace, prev_outputs):
            return {"done": True}

        scheduler = JobScheduler(
            max_workers=2,
            stage_executors={1: fast_executor},
        )
        try:
            job = _make_job(tmp_path, "cancel_test_1", enabled_stages=[1])
            scheduler.submit(job)
            assert _wait_for_status(job, JobStatus.COMPLETED, timeout=5.0)
            result = scheduler.cancel(job.job_id)
            assert result is False
            assert job.status == JobStatus.COMPLETED
        finally:
            scheduler.shutdown()

    def test_scheduler_cancel_nonexistent_returns_false(self, tmp_path):
        """取消不存在作业返回 False。"""
        scheduler = JobScheduler(max_workers=2)
        try:
            assert scheduler.cancel("nonexistent") is False
        finally:
            scheduler.shutdown()

    def test_scheduler_executes_stages_with_executor(self, tmp_path):
        """调度器可执行有执行函数的阶段。"""
        call_count = {"n": 0}

        def dummy_executor(recipe, workspace, prev_outputs):
            call_count["n"] += 1
            return {"stage_result": call_count["n"]}

        scheduler = JobScheduler(
            max_workers=2,
            stage_executors={1: dummy_executor},
        )
        try:
            job = _make_job(tmp_path, "exec_test_1", enabled_stages=[1])
            scheduler.submit(job)
            assert _wait_for_status(job, JobStatus.COMPLETED, timeout=5.0)
            assert call_count["n"] == 1
            assert len(job.stage_results) == 1
            assert job.stage_results[0].status == StageStatus.COMPLETED
        finally:
            scheduler.shutdown()

    def test_scheduler_skips_stages_without_executor(self, tmp_path):
        """无执行函数的阶段被标记为 SKIPPED。"""
        scheduler = JobScheduler(max_workers=2, stage_executors={})
        try:
            job = _make_job(tmp_path, "skip_test_1", enabled_stages=[1, 2])
            scheduler.submit(job)
            assert _wait_for_status(job, JobStatus.COMPLETED, timeout=5.0)
            skipped = [r for r in job.stage_results if r.status == StageStatus.SKIPPED]
            assert len(skipped) == 2
        finally:
            scheduler.shutdown()

    def test_scheduler_stage_failure_marks_job_failed(self, tmp_path):
        """阶段失败时整个作业标记为 FAILED。"""
        def failing_executor(recipe, workspace, prev_outputs):
            raise ValueError("故意失败")

        scheduler = JobScheduler(
            max_workers=2,
            stage_executors={1: failing_executor},
        )
        try:
            job = _make_job(tmp_path, "fail_test_1", enabled_stages=[1])
            scheduler.submit(job)
            assert _wait_for_status(job, JobStatus.FAILED, timeout=5.0)
            assert job.error is not None
            assert "失败" in job.error
        finally:
            scheduler.shutdown()

    def test_scheduler_parallel_execution(self, tmp_path):
        """支持并行执行多个作业。"""
        import threading

        completed = {"count": 0}
        lock = threading.Lock()

        def slow_executor(recipe, workspace, prev_outputs):
            time.sleep(0.3)
            with lock:
                completed["count"] += 1
            return {"done": True}

        scheduler = JobScheduler(
            max_workers=4,
            stage_executors={1: slow_executor},
        )
        try:
            jobs = []
            start = time.time()
            for i in range(4):
                job = _make_job(tmp_path, f"parallel_{i}", enabled_stages=[1])
                jobs.append(job)
                scheduler.submit(job)

            for job in jobs:
                assert _wait_for_status(job, JobStatus.COMPLETED, timeout=5.0)

            elapsed = time.time() - start
            assert completed["count"] == 4
            assert elapsed < 1.5
        finally:
            scheduler.shutdown()

    def test_scheduler_generates_report(self, tmp_path):
        """作业完成后生成汇总报告。"""
        def ok_executor(recipe, workspace, prev_outputs):
            return {"ok": True}

        scheduler = JobScheduler(
            max_workers=2,
            stage_executors={1: ok_executor},
        )
        try:
            job = _make_job(tmp_path, "report_test_1", enabled_stages=[1])
            scheduler.submit(job)
            assert _wait_for_status(job, JobStatus.COMPLETED, timeout=5.0)
            report_path = tmp_path / "report_test_1" / "reports" / "summary.json"
            assert report_path.exists()
        finally:
            scheduler.shutdown()


# =============================================================================
# M3: Workspace + Tracker 测试
# =============================================================================


class TestWorkspaceAndTracker:
    """工作空间与作业追踪器测试。"""

    def test_workspace_creates_directory_structure(self, tmp_path):
        """Workspace 创建标准目录结构。"""
        Workspace(str(tmp_path), "ws_test_1")
        base = tmp_path / "ws_test_1"
        assert (base / "inputs").is_dir()
        assert (base / "logs").is_dir()
        assert (base / "stages").is_dir()
        assert (base / "reports").is_dir()
        assert (base / "gds").is_dir()
        assert (base / "stages" / "stage1_pdk").is_dir()
        assert (base / "stages" / "stage2_circuit").is_dir()

    def test_workspace_write_read_stage_output(self, tmp_path):
        """阶段输出的写入与读取。"""
        ws = Workspace(str(tmp_path), "ws_test_2")
        data = {"key1": "value1", "key2": 123}
        ws.write_stage_output("stage1_pdk", data)
        read_back = ws.read_stage_output("stage1_pdk")
        assert read_back == data

    def test_workspace_read_nonexistent_stage_returns_none(self, tmp_path):
        """读取不存在的阶段输出返回 None。"""
        ws = Workspace(str(tmp_path), "ws_test_3")
        assert ws.read_stage_output("nonexistent") is None

    def test_workspace_job_metadata(self, tmp_path):
        """作业元数据的写入与读取。"""
        ws = Workspace(str(tmp_path), "ws_test_4")
        meta = {"job_id": "test", "status": "running"}
        ws.write_job_metadata(meta)
        read_back = ws.read_job_metadata()
        assert read_back is not None
        assert read_back["job_id"] == "test"

    def test_workspace_write_log(self, tmp_path):
        """日志写入功能。"""
        ws = Workspace(str(tmp_path), "ws_test_5")
        ws.write_log("测试日志消息", "INFO")
        log_path = tmp_path / "ws_test_5" / "logs" / "job.jsonl"
        assert log_path.exists()
        content = log_path.read_text(encoding="utf-8")
        assert "测试日志消息" in content

    def test_workspace_gds_path(self, tmp_path):
        """GDS 路径正确。"""
        ws = Workspace(str(tmp_path), "ws_test_6")
        gds_path = ws.gds_path("test.gds")
        assert gds_path.name == "test.gds"
        assert "gds" in str(gds_path)

    def test_job_tracker_get_status(self, tmp_path):
        """JobTracker 可查询作业状态。"""
        ws = Workspace(str(tmp_path), "tracker_test_1")
        ws.write_job_metadata({"job_id": "tracker_test_1", "status": "completed"})
        tracker = JobTracker(base_output_dir=str(tmp_path))
        status = tracker.get_status("tracker_test_1")
        assert status == "completed"

    def test_job_tracker_get_job(self, tmp_path):
        """JobTracker 可查询作业详情。"""
        ws = Workspace(str(tmp_path), "tracker_test_2")
        meta = {"job_id": "tracker_test_2", "status": "running", "progress": "3/10"}
        ws.write_job_metadata(meta)
        tracker = JobTracker(base_output_dir=str(tmp_path))
        job = tracker.get_job("tracker_test_2")
        assert job is not None
        assert job["progress"] == "3/10"

    def test_job_tracker_list_jobs(self, tmp_path):
        """JobTracker 可列出作业。"""
        for i in range(3):
            ws = Workspace(str(tmp_path), f"list_{i}")
            ws.write_job_metadata({"job_id": f"list_{i}", "status": "completed"})
        tracker = JobTracker(base_output_dir=str(tmp_path))
        jobs = tracker.list_jobs()
        assert len(jobs) >= 3

    def test_job_tracker_get_stage_result(self, tmp_path):
        """JobTracker 可查询阶段结果。"""
        ws = Workspace(str(tmp_path), "tracker_test_3")
        stage_data = {"devices": 10, "status": "ok"}
        ws.write_stage_output("stage1_pdk", stage_data)
        ws.write_job_metadata({"job_id": "tracker_test_3", "status": "completed"})
        tracker = JobTracker(base_output_dir=str(tmp_path))
        result = tracker.get_stage_result("tracker_test_3", 1)
        assert result is not None
        assert result["devices"] == 10


# =============================================================================
# Recipe 序列化测试
# =============================================================================


class TestRecipeSerialization:
    """Recipe + SimConfig 序列化测试。"""

    def test_recipe_default_values(self):
        """Recipe 默认值正确。"""
        r = Recipe()
        assert r.preset_id == "mzi"
        assert r.platform == "SOI"
        assert len(r.enabled_stages) == 10

    def test_recipe_to_dict_and_back(self):
        """Recipe 字典序列化往返。"""
        r = Recipe(preset_id="ring", platform="SiN", canvas_w=500.0)
        d = r.to_dict()
        r2 = Recipe.from_dict(d)
        assert r2.preset_id == "ring"
        assert r2.platform == "SiN"
        assert r2.canvas_w == 500.0

    def test_recipe_json_serialization(self):
        """Recipe JSON 序列化往返。"""
        r = Recipe(preset_id="mzi_lattice")
        json_str = r.to_json()
        r2 = Recipe.from_json(json_str)
        assert r2.preset_id == "mzi_lattice"

    def test_recipe_yaml_serialization(self):
        """Recipe YAML 序列化往返。"""
        r = Recipe(preset_id="ring", placement_algo="rl")
        yaml_str = r.to_yaml()
        r2 = Recipe.from_yaml(yaml_str)
        assert r2.preset_id == "ring"

    def test_sim_config_defaults(self):
        """SimConfig 默认值正确。"""
        sc = SimConfig()
        assert sc.max_iterations == 3
        assert sc.loss_target_db == 5.0
        assert sc.use_real_simulator is False
