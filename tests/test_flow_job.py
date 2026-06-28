"""商业级作业流程表达系统（polaris.flow）完整测试套件。

覆盖：
- Job / JobState / JobStatus 状态机
- Stage / STANDARD_STAGES / StageResult
- Recipe / SimConfig 序列化
- Workspace 目录结构与读写
- JobScheduler 队列调度与并行执行
- JobTracker 只读查询
- STAGE_EXECUTORS 10 阶段执行函数
- IntegratedPipeline.run_as_stages / run 向后兼容
- Web API /api/jobs 端点（真实 HTTP 服务器）

约束：
- 使用 pytest + tmp_path，不污染工作区
- Web API 测试启动真实 HTTPServer（threading），测试完成后关闭
- 禁止 fall-back：测试失败时不降低断言标准
"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

import pytest

from polaris.flow.executors import (
    STAGE_EXECUTORS,
    stage1_pdk,
    stage2_circuit,
    stage3_placement,
    stage4_routing,
    stage5_simulation,
    stage6_drc_lvs,
)

# === polaris.flow API ===
from polaris.flow.job import Job, JobState, JobStatus
from polaris.flow.recipe import Recipe, SimConfig
from polaris.flow.scheduler import JobScheduler
from polaris.flow.stage import (
    STANDARD_STAGES,
    StageResult,
    StageStatus,
    get_stage,
)
from polaris.flow.tracker import JobTracker
from polaris.flow.workspace import Workspace

# === IntegratedPipeline ===
from polaris.pipeline.integrated import IntegratedPipeline, PipelineResult

# === Web Server ===
from polaris.web.server import WebServer

# =============================================================================
# 辅助函数
# =============================================================================


def _make_job(tmp_path: Path, job_id: str = "test_job_001", recipe: Recipe | None = None) -> Job:
    """构造一个绑定临时工作空间的 Job。"""
    recipe = recipe or Recipe()
    ws = Workspace(str(tmp_path), job_id)
    return Job(job_id=job_id, recipe=recipe, workspace=ws)


def _wait_for_status(job: Job, target: JobStatus, timeout: float = 30.0) -> bool:
    """轮询作业状态，直到达到目标状态或超时。"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if job.status == target:
            return True
        if job.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
            return job.status == target
        time.sleep(0.2)
    return job.status == target


# =============================================================================
# TestJob
# =============================================================================


class TestJob:
    """Job 数据结构与状态机测试。"""

    def test_job_creation(self, tmp_path):
        """创建 Job，验证 job_id 格式、status=QUEUED、submit_time 非空。"""
        job = _make_job(tmp_path, "test_001")
        assert job.job_id == "test_001"
        assert job.status == JobStatus.QUEUED
        assert job.submit_time is not None
        assert isinstance(job.submit_time, datetime)

    def test_job_status_transitions(self, tmp_path):
        """测试 QUEUED→RUNNING→COMPLETED 状态转换。"""
        job = _make_job(tmp_path)
        assert job.status == JobStatus.QUEUED
        job.mark_running()
        assert job.status == JobStatus.RUNNING
        assert job.start_time is not None
        job.mark_completed()
        assert job.status == JobStatus.COMPLETED
        assert job.end_time is not None

    def test_job_failed_transition(self, tmp_path):
        """测试 QUEUED→RUNNING→FAILED 状态转换。"""
        job = _make_job(tmp_path)
        job.mark_running()
        job.mark_failed("模拟失败原因")
        assert job.status == JobStatus.FAILED
        assert job.error == "模拟失败原因"
        assert job.end_time is not None

    def test_job_cancelled_transition(self, tmp_path):
        """测试 QUEUED→CANCELLED 和 RUNNING→CANCELLED。"""
        # QUEUED → CANCELLED
        job1 = _make_job(tmp_path, "cancel_queued")
        job1.mark_cancelled()
        assert job1.status == JobStatus.CANCELLED
        assert job1.end_time is not None

        # RUNNING → CANCELLED
        job2 = _make_job(tmp_path, "cancel_running")
        job2.mark_running()
        job2.mark_cancelled()
        assert job2.status == JobStatus.CANCELLED

    def test_job_illegal_transition(self, tmp_path):
        """测试非法转换（COMPLETED→RUNNING）抛出 RuntimeError。"""
        job = _make_job(tmp_path)
        job.mark_running()
        job.mark_completed()
        with pytest.raises(RuntimeError, match="非法状态转换"):
            job.mark_running()

    def test_job_progress(self, tmp_path):
        """测试 progress 属性返回 'N/M' 格式。"""
        recipe = Recipe(enabled_stages=[1, 2, 3])
        job = _make_job(tmp_path, recipe=recipe)
        assert job.progress == "0/3"
        job.current_stage = 2
        assert job.progress == "2/3"
        job.current_stage = 3
        assert job.progress == "3/3"

    def test_job_to_dict(self, tmp_path):
        """测试 to_dict 序列化。"""
        recipe = Recipe(preset_id="mzi")
        job = _make_job(tmp_path, "dict_001", recipe=recipe)
        d = job.to_dict()
        assert d["job_id"] == "dict_001"
        assert d["status"] == "queued"
        assert d["submit_time"] is not None
        assert d["start_time"] is None
        assert d["end_time"] is None
        assert d["current_stage"] == 0
        assert d["progress"] == "0/10"
        assert d["error"] is None
        assert d["recipe"] is not None
        assert d["recipe"]["preset_id"] == "mzi"

    def test_job_generate_job_id(self):
        """测试 generate_job_id 生成唯一 ID，格式为 YYYYMMDD_HHMMSS_<6位随机>。"""
        id1 = Job.generate_job_id()
        id2 = Job.generate_job_id()
        assert id1 != id2  # 唯一性（6 位随机后缀几乎不可能碰撞）
        # 格式校验：YYYYMMDD_HHMMSS_<6位>
        m = re.match(r"^(\d{8})_(\d{6})_([a-z0-9]{6})$", id1)
        assert m is not None, f"job_id 格式不正确: {id1}"
        assert len(m.group(1)) == 8  # YYYYMMDD
        assert len(m.group(2)) == 6  # HHMMSS
        assert len(m.group(3)) == 6  # 6 位随机


# =============================================================================
# TestJobState
# =============================================================================


class TestJobState:
    """JobState 状态机规则测试。"""

    def test_state_transitions(self):
        """测试合法转换返回 True，非法转换返回 False。"""
        # 合法转换
        assert JobState.can_transition(JobStatus.QUEUED, JobStatus.RUNNING) is True
        assert JobState.can_transition(JobStatus.QUEUED, JobStatus.CANCELLED) is True
        assert JobState.can_transition(JobStatus.RUNNING, JobStatus.COMPLETED) is True
        assert JobState.can_transition(JobStatus.RUNNING, JobStatus.FAILED) is True
        assert JobState.can_transition(JobStatus.RUNNING, JobStatus.CANCELLED) is True
        # 非法转换
        assert JobState.can_transition(JobStatus.COMPLETED, JobStatus.RUNNING) is False
        assert JobState.can_transition(JobStatus.FAILED, JobStatus.RUNNING) is False
        assert JobState.can_transition(JobStatus.CANCELLED, JobStatus.RUNNING) is False
        assert JobState.can_transition(JobStatus.QUEUED, JobStatus.COMPLETED) is False
        assert JobState.can_transition(JobStatus.COMPLETED, JobStatus.FAILED) is False

    def test_state_is_terminal(self):
        """测试 COMPLETED/FAILED/CANCELLED 是终态。"""
        assert JobState.is_terminal(JobStatus.COMPLETED) is True
        assert JobState.is_terminal(JobStatus.FAILED) is True
        assert JobState.is_terminal(JobStatus.CANCELLED) is True
        assert JobState.is_terminal(JobStatus.QUEUED) is False
        assert JobState.is_terminal(JobStatus.RUNNING) is False

    def test_state_assert_transition(self):
        """测试 assert_transition 合法时不抛异常，非法时抛 RuntimeError。"""
        # 合法转换不抛异常
        JobState.assert_transition(JobStatus.QUEUED, JobStatus.RUNNING)
        JobState.assert_transition(JobStatus.RUNNING, JobStatus.COMPLETED)
        JobState.assert_transition(JobStatus.RUNNING, JobStatus.FAILED)
        # 非法转换抛 RuntimeError
        with pytest.raises(RuntimeError):
            JobState.assert_transition(JobStatus.COMPLETED, JobStatus.RUNNING)
        with pytest.raises(RuntimeError):
            JobState.assert_transition(JobStatus.FAILED, JobStatus.RUNNING)
        with pytest.raises(RuntimeError):
            JobState.assert_transition(JobStatus.CANCELLED, JobStatus.RUNNING)


# =============================================================================
# TestStage
# =============================================================================


class TestStage:
    """Stage 数据结构与 STANDARD_STAGES 测试。"""

    def test_standard_stages_count(self):
        """验证 STANDARD_STAGES 有 10 个阶段。"""
        assert len(STANDARD_STAGES) == 10

    def test_standard_stages_ids(self):
        """验证阶段 ID 为 1-10。"""
        ids = [s.stage_id for s in STANDARD_STAGES]
        assert ids == [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

    def test_get_stage_valid(self):
        """测试 get_stage(1) 返回正确阶段。"""
        stage = get_stage(1)
        assert stage.stage_id == 1
        assert stage.name == "PDK 器件目录"
        assert stage.slug == "stage1_pdk"
        assert stage.ipkiss_step == "器件设计"

    def test_get_stage_invalid(self):
        """测试 get_stage(99) 抛出 ValueError。"""
        with pytest.raises(ValueError, match="未知阶段 ID"):
            get_stage(99)

    def test_stage_fields(self):
        """验证 Stage 有 stage_id, name, slug, description, ipkiss_step,
        inputs_spec, outputs_spec, depends_on 字段。"""
        stage = get_stage(1)
        assert hasattr(stage, "stage_id")
        assert hasattr(stage, "name")
        assert hasattr(stage, "slug")
        assert hasattr(stage, "description")
        assert hasattr(stage, "ipkiss_step")
        assert hasattr(stage, "inputs_spec")
        assert hasattr(stage, "outputs_spec")
        assert hasattr(stage, "depends_on")
        # 验证字段类型
        assert isinstance(stage.stage_id, int)
        assert isinstance(stage.name, str)
        assert isinstance(stage.slug, str)
        assert isinstance(stage.description, str)
        assert isinstance(stage.ipkiss_step, str)
        assert isinstance(stage.inputs_spec, list)
        assert isinstance(stage.outputs_spec, list)
        assert isinstance(stage.depends_on, list)

    def test_stage_result_duration(self):
        """测试 StageResult.duration_s 计算正确。"""
        start = datetime(2024, 1, 1, 12, 0, 0)
        end = datetime(2024, 1, 1, 12, 0, 5)
        result = StageResult(
            stage_id=1, name="test", start_time=start, end_time=end
        )
        assert result.duration_s == 5.0
        # 未完成时返回 None
        result2 = StageResult(stage_id=2, name="test2")
        assert result2.duration_s is None


# =============================================================================
# TestRecipe
# =============================================================================


class TestRecipe:
    """Recipe 配方与 SimConfig 序列化测试。"""

    def test_recipe_default(self):
        """测试默认值（preset_id=mzi, platform=SOI, enabled_stages=[1..10]）。"""
        recipe = Recipe()
        assert recipe.preset_id == "mzi"
        assert recipe.platform == "SOI"
        assert recipe.placement_algo == "analytical"
        assert recipe.router_algo == "curvy"
        assert recipe.enabled_stages == [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        assert recipe.canvas_w == 1000.0
        assert recipe.canvas_h == 600.0
        assert recipe.custom_circuit is None

    def test_recipe_to_dict(self):
        """测试 to_dict 返回正确字典。"""
        recipe = Recipe(preset_id="ring", platform="SiN")
        d = recipe.to_dict()
        assert d["preset_id"] == "ring"
        assert d["platform"] == "SiN"
        assert d["enabled_stages"] == [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        assert "sim_config" in d
        assert d["sim_config"]["max_iterations"] == 3
        assert d["sim_config"]["loss_target_db"] == 5.0
        assert d["sim_config"]["use_real_simulator"] is False

    def test_recipe_to_json_from_json(self):
        """测试 JSON 序列化/反序列化往返。"""
        recipe = Recipe(
            preset_id="ring",
            platform="SiN",
            placement_algo="rl",
            router_algo="diagonal",
            enabled_stages=[1, 2, 3],
        )
        json_str = recipe.to_json()
        assert isinstance(json_str, str)
        recipe2 = Recipe.from_json(json_str)
        assert recipe2.preset_id == "ring"
        assert recipe2.platform == "SiN"
        assert recipe2.placement_algo == "rl"
        assert recipe2.router_algo == "diagonal"
        assert recipe2.enabled_stages == [1, 2, 3]

    def test_recipe_to_yaml_from_yaml(self):
        """测试 YAML 序列化/反序列化往返。"""
        recipe = Recipe(
            preset_id="ring",
            platform="SiN",
            enabled_stages=[1, 2, 3],
        )
        yaml_str = recipe.to_yaml()
        assert isinstance(yaml_str, str)
        recipe2 = Recipe.from_yaml(yaml_str)
        assert recipe2.preset_id == "ring"
        assert recipe2.platform == "SiN"
        assert recipe2.enabled_stages == [1, 2, 3]

    def test_recipe_custom_stages(self):
        """测试 enabled_stages=[1,2,3] 自定义阶段。"""
        recipe = Recipe(enabled_stages=[1, 2, 3])
        assert recipe.enabled_stages == [1, 2, 3]
        assert len(recipe.enabled_stages) == 3

    def test_recipe_sim_config(self):
        """测试 SimConfig 默认值和自定义值。"""
        # 默认值
        sim_config = SimConfig()
        assert sim_config.max_iterations == 3
        assert sim_config.loss_target_db == 5.0
        assert sim_config.use_real_simulator is False
        # 自定义值
        sim_config2 = SimConfig(
            max_iterations=10,
            loss_target_db=3.0,
            use_real_simulator=True,
        )
        assert sim_config2.max_iterations == 10
        assert sim_config2.loss_target_db == 3.0
        assert sim_config2.use_real_simulator is True
        # Recipe 中嵌入 SimConfig
        recipe = Recipe(sim_config=sim_config2)
        assert recipe.sim_config.max_iterations == 10
        assert recipe.sim_config.loss_target_db == 3.0


# =============================================================================
# TestWorkspace
# =============================================================================


class TestWorkspace:
    """Workspace 目录结构与读写测试。"""

    _STAGE_SLUGS = [
        "stage1_pdk", "stage2_circuit", "stage3_placement", "stage4_routing",
        "stage5_simulation", "stage6_drc_lvs", "stage7_gds",
        "stage8_opto_electrical", "stage9_quantum", "stage10_inverse",
    ]

    def test_workspace_init(self, tmp_path):
        """测试目录结构创建（inputs/logs/stages/reports/gds + 10 阶段子目录）。"""
        Workspace(str(tmp_path), "ws_job_001")
        base = tmp_path / "ws_job_001"
        # 主目录
        assert (base / "inputs").is_dir()
        assert (base / "logs").is_dir()
        assert (base / "stages").is_dir()
        assert (base / "reports").is_dir()
        assert (base / "gds").is_dir()
        # 10 个阶段子目录
        for slug in self._STAGE_SLUGS:
            assert (base / "stages" / slug).is_dir(), f"阶段目录 {slug} 未创建"

    def test_workspace_stage_dir(self, tmp_path):
        """测试 stage_dir 返回正确路径。"""
        ws = Workspace(str(tmp_path), "ws_job_002")
        path = ws.stage_dir("stage1_pdk")
        assert path == tmp_path / "ws_job_002" / "stages" / "stage1_pdk"

    def test_workspace_write_read_stage_output(self, tmp_path):
        """测试写入和读取阶段输出。"""
        ws = Workspace(str(tmp_path), "ws_job_003")
        data = {"device_catalog": [{"name": "mmi_2x2"}], "n_devices": 1}
        path = ws.write_stage_output("stage1_pdk", data)
        assert path.exists()
        read_back = ws.read_stage_output("stage1_pdk")
        assert read_back == data
        # 读取不存在的阶段输出返回 None
        assert ws.read_stage_output("stage2_circuit") is None

    def test_workspace_write_read_job_metadata(self, tmp_path):
        """测试写入和读取作业元数据。"""
        ws = Workspace(str(tmp_path), "ws_job_004")
        meta = {
            "job_id": "ws_job_004",
            "status": "completed",
            "current_stage": 10,
            "progress": "10/10",
        }
        path = ws.write_job_metadata(meta)
        assert path.exists()
        read_back = ws.read_job_metadata()
        assert read_back == meta

    def test_workspace_write_log(self, tmp_path):
        """测试日志写入（JSONL 格式）。"""
        ws = Workspace(str(tmp_path), "ws_job_005")
        ws.write_log("作业开始执行")
        ws.write_log("阶段 1 完成", "INFO")
        ws.write_log("阶段 2 失败", "ERROR")
        log_path = tmp_path / "ws_job_005" / "logs" / "job.jsonl"
        assert log_path.exists()
        content = log_path.read_text(encoding="utf-8")
        lines = [line for line in content.strip().split("\n") if line]
        assert len(lines) == 3
        for line in lines:
            entry = json.loads(line)
            assert "timestamp" in entry
            assert "level" in entry
            assert "message" in entry
        assert json.loads(lines[0])["message"] == "作业开始执行"
        assert json.loads(lines[2])["level"] == "ERROR"

    def test_workspace_write_report(self, tmp_path):
        """测试报告写入。"""
        ws = Workspace(str(tmp_path), "ws_job_006")
        report = {
            "job_id": "ws_job_006",
            "status": "completed",
            "total_stages": 10,
            "completed_stages": 10,
        }
        path = ws.write_report(report)
        assert path.exists()
        assert path == tmp_path / "ws_job_006" / "reports" / "summary.json"
        read_back = json.loads(path.read_text(encoding="utf-8"))
        assert read_back == report

    def test_workspace_gds_path(self, tmp_path):
        """测试 GDS 路径。"""
        ws = Workspace(str(tmp_path), "ws_job_007")
        # 默认文件名
        assert ws.gds_path() == tmp_path / "ws_job_007" / "gds" / "layout.gds"
        # 自定义文件名
        assert ws.gds_path("custom.gds") == tmp_path / "ws_job_007" / "gds" / "custom.gds"


# =============================================================================
# TestJobScheduler
# =============================================================================


class TestJobScheduler:
    """JobScheduler 队列调度与并行执行测试。"""

    @staticmethod
    def _mock_executor(recipe, workspace, prev_outputs):
        """快速 mock 执行函数。"""
        return {"status": "ok", "mock": True}

    @staticmethod
    def _slow_executor(recipe, workspace, prev_outputs):
        """慢速 mock 执行函数（用于取消测试）。"""
        time.sleep(5)
        return {"status": "ok"}

    @staticmethod
    def _failing_executor(recipe, workspace, prev_outputs):
        """失败 mock 执行函数。"""
        raise RuntimeError("模拟阶段执行失败")

    def test_scheduler_submit(self, tmp_path):
        """测试提交作业返回 job_id，状态为 QUEUED。"""
        scheduler = JobScheduler(
            max_workers=1,
            stage_executors={1: self._mock_executor},
        )
        try:
            recipe = Recipe(enabled_stages=[1], output_dir=str(tmp_path))
            job_id = Job.generate_job_id()
            ws = Workspace(str(tmp_path), job_id)
            job = Job(job_id=job_id, recipe=recipe, workspace=ws)
            returned_id = scheduler.submit(job)
            assert returned_id == job_id
            # 提交后状态可能是 QUEUED（未调度）或 RUNNING/COMPLETED（已调度）
            assert job.status in (
                JobStatus.QUEUED, JobStatus.RUNNING, JobStatus.COMPLETED,
            )
        finally:
            scheduler.shutdown()

    def test_scheduler_execute_simple(self, tmp_path):
        """测试简单作业执行（用 mock 执行函数）。"""
        scheduler = JobScheduler(
            max_workers=1,
            stage_executors={1: self._mock_executor, 2: self._mock_executor},
        )
        try:
            recipe = Recipe(enabled_stages=[1, 2], output_dir=str(tmp_path))
            job_id = Job.generate_job_id()
            ws = Workspace(str(tmp_path), job_id)
            job = Job(job_id=job_id, recipe=recipe, workspace=ws)
            scheduler.submit(job)
            assert _wait_for_status(job, JobStatus.COMPLETED, timeout=10)
            assert job.status == JobStatus.COMPLETED
            assert len(job.stage_results) == 2
            for r in job.stage_results:
                assert r.status == StageStatus.COMPLETED
            assert job.current_stage == 2
        finally:
            scheduler.shutdown()

    def test_scheduler_cancel(self, tmp_path):
        """测试取消作业。"""
        scheduler = JobScheduler(
            max_workers=1,
            stage_executors={1: self._slow_executor},
        )
        try:
            recipe = Recipe(enabled_stages=[1], output_dir=str(tmp_path))
            job_id = Job.generate_job_id()
            ws = Workspace(str(tmp_path), job_id)
            job = Job(job_id=job_id, recipe=recipe, workspace=ws)
            scheduler.submit(job)
            # 等待作业开始运行
            time.sleep(0.5)
            assert scheduler.cancel(job_id) is True
            assert job.status == JobStatus.CANCELLED
        finally:
            scheduler.shutdown()

    def test_scheduler_list_jobs(self, tmp_path):
        """测试列出作业。"""
        scheduler = JobScheduler(
            max_workers=1,
            stage_executors={1: self._mock_executor},
        )
        try:
            recipe = Recipe(enabled_stages=[1], output_dir=str(tmp_path))
            job_id = Job.generate_job_id()
            ws = Workspace(str(tmp_path), job_id)
            job = Job(job_id=job_id, recipe=recipe, workspace=ws)
            scheduler.submit(job)
            jobs = scheduler.list_jobs()
            assert len(jobs) >= 1
            assert job in jobs
            # 按状态过滤
            _wait_for_status(job, JobStatus.COMPLETED, timeout=10)
            completed = scheduler.list_jobs(status=JobStatus.COMPLETED)
            assert job in completed
        finally:
            scheduler.shutdown()

    def test_scheduler_parallel(self, tmp_path):
        """测试并行执行多个作业。"""
        scheduler = JobScheduler(
            max_workers=4,
            stage_executors={1: self._mock_executor},
        )
        try:
            jobs = []
            for _ in range(4):
                recipe = Recipe(enabled_stages=[1], output_dir=str(tmp_path))
                job_id = Job.generate_job_id()
                ws = Workspace(str(tmp_path), job_id)
                job = Job(job_id=job_id, recipe=recipe, workspace=ws)
                scheduler.submit(job)
                jobs.append(job)
            # 等待所有作业完成
            for job in jobs:
                assert _wait_for_status(job, JobStatus.COMPLETED, timeout=15)
            for job in jobs:
                assert job.status == JobStatus.COMPLETED
        finally:
            scheduler.shutdown()

    def test_scheduler_failed_job(self, tmp_path):
        """测试失败作业记录错误信息。"""
        scheduler = JobScheduler(
            max_workers=1,
            stage_executors={1: self._failing_executor},
        )
        try:
            recipe = Recipe(enabled_stages=[1], output_dir=str(tmp_path))
            job_id = Job.generate_job_id()
            ws = Workspace(str(tmp_path), job_id)
            job = Job(job_id=job_id, recipe=recipe, workspace=ws)
            scheduler.submit(job)
            assert _wait_for_status(job, JobStatus.FAILED, timeout=10)
            assert job.status == JobStatus.FAILED
            assert job.error is not None
            assert "模拟阶段执行失败" in job.error
            # 验证阶段结果记录了失败
            assert len(job.stage_results) == 1
            assert job.stage_results[0].status == StageStatus.FAILED
        finally:
            scheduler.shutdown()


# =============================================================================
# TestJobTracker
# =============================================================================


class TestJobTracker:
    """JobTracker 只读查询测试。"""

    @staticmethod
    def _create_job_dir(tmp_path: Path, job_id: str, status: str = "completed"):
        """在临时目录下创建一个作业的工作空间并写入元数据。"""
        ws = Workspace(str(tmp_path), job_id)
        meta = {
            "job_id": job_id,
            "status": status,
            "current_stage": 10,
            "progress": "10/10",
            "submit_time": "2024-01-01T12:00:00",
        }
        ws.write_job_metadata(meta)
        return ws

    def test_tracker_get_status(self, tmp_path):
        """测试状态查询。"""
        self._create_job_dir(tmp_path, "track_001", "completed")
        tracker = JobTracker(base_output_dir=str(tmp_path))
        assert tracker.get_status("track_001") == "completed"

    def test_tracker_get_job(self, tmp_path):
        """测试作业详情查询。"""
        self._create_job_dir(tmp_path, "track_002", "running")
        tracker = JobTracker(base_output_dir=str(tmp_path))
        job = tracker.get_job("track_002")
        assert job is not None
        assert job["job_id"] == "track_002"
        assert job["status"] == "running"

    def test_tracker_list_jobs(self, tmp_path):
        """测试作业列表。"""
        self._create_job_dir(tmp_path, "track_003", "completed")
        self._create_job_dir(tmp_path, "track_004", "failed")
        tracker = JobTracker(base_output_dir=str(tmp_path))
        jobs = tracker.list_jobs()
        assert len(jobs) == 2
        # 按状态过滤
        completed = tracker.list_jobs(status="completed")
        assert len(completed) == 1
        assert completed[0]["job_id"] == "track_003"

    def test_tracker_get_stage_result(self, tmp_path):
        """测试阶段结果查询。"""
        ws = self._create_job_dir(tmp_path, "track_005", "completed")
        ws.write_stage_output("stage1_pdk", {"device_catalog": [], "n_devices": 0})
        tracker = JobTracker(base_output_dir=str(tmp_path))
        result = tracker.get_stage_result("track_005", 1)
        assert result is not None
        assert result["n_devices"] == 0
        # 查询不存在的阶段返回 None
        assert tracker.get_stage_result("track_005", 2) is None
        # 查询无效阶段 ID 返回 None
        assert tracker.get_stage_result("track_005", 99) is None

    def test_tracker_get_history(self, tmp_path):
        """测试历史记录查询。"""
        ws = self._create_job_dir(tmp_path, "track_006", "completed")
        ws.write_stage_output("stage1_pdk", {"n_devices": 1})
        ws.write_stage_output("stage2_circuit", {"n_devices": 2})
        tracker = JobTracker(base_output_dir=str(tmp_path))
        history = tracker.get_history("track_006")
        assert len(history) == 2
        assert history[0]["stage_id"] == 1
        assert history[1]["stage_id"] == 2

    def test_tracker_nonexistent_job(self, tmp_path):
        """测试查询不存在的作业返回 None。"""
        tracker = JobTracker(base_output_dir=str(tmp_path))
        assert tracker.get_status("nonexistent") is None
        assert tracker.get_job("nonexistent") is None
        assert tracker.get_stage_result("nonexistent", 1) is None
        assert tracker.get_history("nonexistent") == []
        # 不存在的目录返回空列表
        assert tracker.list_jobs() == []


# =============================================================================
# TestStageExecutors
# =============================================================================


class TestStageExecutors:
    """STAGE_EXECUTORS 10 阶段执行函数测试。"""

    def test_stage1_pdk(self, tmp_path):
        """测试 PDK 阶段执行。"""
        recipe = Recipe(platform="SOI")
        ws = Workspace(str(tmp_path), "exec_001")
        result = stage1_pdk(recipe, ws, {})
        assert "device_catalog" in result
        assert result["platform"] == "SOI"
        assert result["n_devices"] > 0
        assert isinstance(result["device_catalog"], list)

    def test_stage2_circuit(self, tmp_path):
        """测试电路规格阶段。"""
        recipe = Recipe(preset_id="mzi")
        ws = Workspace(str(tmp_path), "exec_002")
        result = stage2_circuit(recipe, ws, {})
        assert "circuit" in result
        assert result["n_devices"] > 0
        assert result["n_connections"] > 0
        assert "name" in result["circuit"]

    def test_stage3_placement(self, tmp_path):
        """测试布局阶段。"""
        recipe = Recipe(preset_id="mzi", placement_algo="analytical")
        ws = Workspace(str(tmp_path), "exec_003")
        # 先执行 stage2 获取 circuit
        prev = stage2_circuit(recipe, ws, {})
        result = stage3_placement(recipe, ws, prev)
        assert "placements" in result
        assert result["n_placed"] > 0
        for _name, pl in result["placements"].items():
            assert "x" in pl
            assert "y" in pl
            assert "w" in pl
            assert "h" in pl

    def test_stage4_routing(self, tmp_path):
        """测试布线阶段。"""
        recipe = Recipe(
            preset_id="mzi",
            placement_algo="analytical",
            router_algo="curvy",
        )
        ws = Workspace(str(tmp_path), "exec_004")
        prev = stage2_circuit(recipe, ws, {})
        prev.update(stage3_placement(recipe, ws, prev))
        result = stage4_routing(recipe, ws, prev)
        assert "routes" in result
        assert result["n_paths"] > 0
        assert result["total_length_um"] >= 0

    def test_stage5_simulation(self, tmp_path):
        """测试仿真阶段。"""
        recipe = Recipe(
            preset_id="mzi",
            placement_algo="analytical",
            router_algo="curvy",
        )
        ws = Workspace(str(tmp_path), "exec_005")
        prev = stage2_circuit(recipe, ws, {})
        prev.update(stage3_placement(recipe, ws, prev))
        prev.update(stage4_routing(recipe, ws, prev))
        result = stage5_simulation(recipe, ws, prev)
        assert "sparams" in result
        assert "total_loss_db" in result
        assert "n_crossings" in result
        assert isinstance(result["total_loss_db"], float)
        assert isinstance(result["n_crossings"], int)

    def test_stage6_drc_lvs(self, tmp_path):
        """测试 DRC 阶段。"""
        recipe = Recipe(
            preset_id="mzi",
            placement_algo="analytical",
            router_algo="curvy",
        )
        ws = Workspace(str(tmp_path), "exec_006")
        prev = stage2_circuit(recipe, ws, {})
        prev.update(stage3_placement(recipe, ws, prev))
        prev.update(stage4_routing(recipe, ws, prev))
        result = stage6_drc_lvs(recipe, ws, prev)
        assert "drc_report" in result
        assert "lvs_passed" in result
        assert "violations" in result["drc_report"]
        assert "n_violations" in result["drc_report"]
        assert "passed" in result["drc_report"]

    def test_stage_full_pipeline(self, tmp_path):
        """测试完整流水线（阶段 1-5 顺序执行）。"""
        recipe = Recipe(
            preset_id="mzi",
            platform="SOI",
            placement_algo="analytical",
            router_algo="curvy",
            enabled_stages=[1, 2, 3, 4, 5],
        )
        ws = Workspace(str(tmp_path), "exec_full")
        prev_outputs: dict = {}
        for stage_id in recipe.enabled_stages:
            execute_fn = STAGE_EXECUTORS[stage_id]
            output = execute_fn(recipe, ws, prev_outputs)
            prev_outputs.update(output)
            ws.write_stage_output(get_stage(stage_id).slug, output)
        # 验证最终输出包含所有阶段的关键产物
        assert "device_catalog" in prev_outputs
        assert "circuit" in prev_outputs
        assert "placements" in prev_outputs
        assert "routes" in prev_outputs
        assert "sparams" in prev_outputs
        assert "total_loss_db" in prev_outputs
        # 验证工作空间持久化
        for stage_id in recipe.enabled_stages:
            slug = get_stage(stage_id).slug
            read_back = ws.read_stage_output(slug)
            assert read_back is not None, f"阶段 {stage_id} 输出未持久化"


# =============================================================================
# TestIntegratedPipelineRunAsStages
# =============================================================================


class TestIntegratedPipelineRunAsStages:
    """IntegratedPipeline.run_as_stages 与 run 向后兼容测试。"""

    def test_run_as_stages(self, tmp_path):
        """测试 IntegratedPipeline.run_as_stages 方法。"""
        recipe = Recipe(
            preset_id="mzi",
            platform="SOI",
            placement_algo="analytical",
            router_algo="curvy",
            enabled_stages=[1, 2, 3, 4, 5],
            output_dir=str(tmp_path),
        )
        ws = Workspace(str(tmp_path), "pipeline_stages")
        pipeline = IntegratedPipeline()
        results = pipeline.run_as_stages(recipe, ws)
        assert len(results) == 5
        for r in results:
            assert r.status == StageStatus.COMPLETED
            assert r.duration_s is not None
        # 验证工作空间持久化
        for stage_id in recipe.enabled_stages:
            slug = get_stage(stage_id).slug
            assert ws.read_stage_output(slug) is not None

    def test_run_backward_compatible(self, tmp_path):
        """测试 run() 方法仍然向后兼容。"""
        pipeline = IntegratedPipeline()
        result = pipeline.run()
        # run() 返回 PipelineResult 对象
        assert isinstance(result, PipelineResult)
        assert result.circuit_name != ""
        assert result.n_devices > 0
        assert result.n_connections > 0
        # 流水线应能完成（GDS 导出应成功，klayout 已安装）
        assert result.gds_path != ""
        assert os.path.exists(result.gds_path)


# =============================================================================
# TestWebAPIJobs
# =============================================================================


class TestWebAPIJobs:
    """Web API /api/jobs 端点测试（真实 HTTP 服务器）。"""

    @pytest.fixture
    def web_env(self, tmp_path, monkeypatch):
        """Web API 测试环境：临时目录 + mock 调度器 + HTTP 服务器。

        - chdir 到 tmp_path，确保 out/jobs 在临时目录下
        - 重置全局调度器和追踪器
        - 注入 mock 执行函数（快速完成，不依赖真实 PDK）

        注意：手动 chdir（不用 monkeypatch.chdir），以便在清理时
        先等待所有 worker 线程完成，再恢复工作目录。否则取消的作业
        在工作目录恢复后仍可能尝试写入文件，导致 FileNotFoundError。
        """
        import polaris.web.server as server_module

        # 手动 chdir（fixture 清理时控制恢复时机）
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        # 重置全局调度器和追踪器
        monkeypatch.setattr(server_module, "_global_scheduler", None)
        monkeypatch.setattr(server_module, "_global_tracker", None)

        # 创建使用 mock 执行函数的调度器
        def fast_executor(recipe, workspace, prev_outputs):
            return {"status": "ok", "mock": True, "stage_executed": True}

        scheduler = JobScheduler(
            max_workers=2,
            stage_executors={i: fast_executor for i in range(1, 11)},
        )
        monkeypatch.setattr(server_module, "_global_scheduler", scheduler)

        # 启动 HTTP 服务器（后台线程）
        port = 8890
        server = WebServer(host="127.0.0.1", port=port)
        server.start(blocking=False)
        time.sleep(0.5)  # 等待服务器就绪

        yield {
            "server": server,
            "scheduler": scheduler,
            "url": f"http://127.0.0.1:{port}",
        }

        # 清理：先停止服务器，再等待调度器所有 worker 完成，最后恢复工作目录
        server.stop()
        scheduler.shutdown()
        # 等待所有 worker 线程完成，避免工作目录恢复后写入失败
        scheduler._executor.shutdown(wait=True)
        os.chdir(original_cwd)

    @staticmethod
    def _wait_job_completed(url: str, job_id: str, timeout: float = 30.0) -> dict:
        """轮询作业状态直到完成或超时。

        作业元数据（job.json）在 worker 开始执行后写入磁盘，
        提交后立即查询可能返回 404，需要重试。
        """
        deadline = time.time() + timeout
        data: dict = {"status": "unknown"}
        while time.time() < deadline:
            try:
                resp = urllib.request.urlopen(f"{url}/api/jobs/{job_id}/status")
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("status") in ("completed", "failed", "cancelled"):
                    return data
            except urllib.error.HTTPError:
                # 404 表示 job.json 还未写入磁盘，继续等待
                pass
            time.sleep(0.3)
        return data

    def test_post_jobs(self, web_env):
        """测试 POST /api/jobs 提交作业。"""
        url = web_env["url"]
        body = json.dumps({
            "preset_id": "mzi",
            "platform": "SOI",
            "enabled_stages": [1, 2],
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{url}/api/jobs",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        resp = urllib.request.urlopen(req)
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert "job_id" in data
        assert data["status"] == "queued"
        assert data["job_id"]  # 非空

    def test_get_jobs(self, web_env):
        """测试 GET /api/jobs 列出作业。"""
        url = web_env["url"]
        # 先提交一个作业
        body = json.dumps({
            "preset_id": "mzi",
            "enabled_stages": [1],
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{url}/api/jobs",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        resp = urllib.request.urlopen(req)
        job_id = json.loads(resp.read().decode("utf-8"))["job_id"]
        # 等待作业元数据写入磁盘（作业开始执行后才会写 job.json）
        self._wait_job_completed(url, job_id, timeout=10)
        # 列出作业
        resp = urllib.request.urlopen(f"{url}/api/jobs")
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert "jobs" in data
        assert len(data["jobs"]) >= 1
        job_ids = [j["job_id"] for j in data["jobs"]]
        assert job_id in job_ids

    def test_get_job_detail(self, web_env):
        """测试 GET /api/jobs/{job_id} 查询作业详情。"""
        url = web_env["url"]
        # 提交作业
        body = json.dumps({
            "preset_id": "mzi",
            "enabled_stages": [1],
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{url}/api/jobs",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        resp = urllib.request.urlopen(req)
        job_id = json.loads(resp.read().decode("utf-8"))["job_id"]
        # 等待作业完成（元数据写入磁盘）
        self._wait_job_completed(url, job_id, timeout=10)
        # 查询详情
        resp = urllib.request.urlopen(f"{url}/api/jobs/{job_id}")
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["job_id"] == job_id
        assert "status" in data

    def test_get_job_status(self, web_env):
        """测试 GET /api/jobs/{job_id}/status 查询作业状态。"""
        url = web_env["url"]
        # 提交作业
        body = json.dumps({
            "preset_id": "mzi",
            "enabled_stages": [1],
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{url}/api/jobs",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        resp = urllib.request.urlopen(req)
        job_id = json.loads(resp.read().decode("utf-8"))["job_id"]
        # 等待作业元数据写入磁盘（作业开始执行后才会写 job.json）
        self._wait_job_completed(url, job_id, timeout=10)
        # 查询状态
        resp = urllib.request.urlopen(f"{url}/api/jobs/{job_id}/status")
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["job_id"] == job_id
        assert "status" in data
        assert "progress" in data

    def test_post_job_cancel(self, web_env, monkeypatch):
        """测试 POST /api/jobs/{job_id}/cancel 取消作业。"""
        import threading

        import polaris.web.server as server_module
        url = web_env["url"]

        # 用 Event 实现可释放的阻塞执行函数
        # cancel 后 worker 仍阻塞在 execute_fn 中，需要在 finally 中释放
        cancel_event = threading.Event()

        def blocking_executor(recipe, workspace, prev_outputs):
            # 阻塞直到被释放或超时（防止死锁）
            cancel_event.wait(timeout=10)
            return {"status": "ok"}

        blocking_scheduler = JobScheduler(
            max_workers=1,
            stage_executors={i: blocking_executor for i in range(1, 11)},
        )
        monkeypatch.setattr(server_module, "_global_scheduler", blocking_scheduler)

        try:
            # 提交作业
            body = json.dumps({
                "preset_id": "mzi",
                "enabled_stages": [1],
            }).encode("utf-8")
            req = urllib.request.Request(
                f"{url}/api/jobs",
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            resp = urllib.request.urlopen(req)
            job_id = json.loads(resp.read().decode("utf-8"))["job_id"]
            # 等待作业开始运行（worker 进入 blocking_executor）
            time.sleep(0.5)
            # 取消作业
            cancel_req = urllib.request.Request(
                f"{url}/api/jobs/{job_id}/cancel",
                method="POST",
            )
            resp = urllib.request.urlopen(cancel_req)
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert data["status"] == "cancelled"
        finally:
            # 释放阻塞的执行函数，等待 worker 完成
            # 必须在 fixture 恢复工作目录之前完成，否则 worker 写入文件会失败
            cancel_event.set()
            blocking_scheduler._executor.shutdown(wait=True)
            blocking_scheduler._shutdown = True

    def test_get_job_stage(self, web_env):
        """测试 GET /api/jobs/{job_id}/stages/{stage_id} 查询阶段输出。"""
        url = web_env["url"]
        # 提交作业
        body = json.dumps({
            "preset_id": "mzi",
            "enabled_stages": [1, 2],
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{url}/api/jobs",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        resp = urllib.request.urlopen(req)
        job_id = json.loads(resp.read().decode("utf-8"))["job_id"]
        # 等待作业完成
        self._wait_job_completed(url, job_id, timeout=15)
        # 查询阶段 1 输出
        resp = urllib.request.urlopen(f"{url}/api/jobs/{job_id}/stages/1")
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert "status" in data  # mock executor 返回 {"status": "ok", ...}

    def test_get_job_report(self, web_env):
        """测试 GET /api/jobs/{job_id}/report 查询作业汇总报告。"""
        url = web_env["url"]
        # 提交作业
        body = json.dumps({
            "preset_id": "mzi",
            "enabled_stages": [1, 2],
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{url}/api/jobs",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        resp = urllib.request.urlopen(req)
        job_id = json.loads(resp.read().decode("utf-8"))["job_id"]
        # 等待作业完成（报告在作业完成后写入）
        self._wait_job_completed(url, job_id, timeout=15)
        # 查询报告
        resp = urllib.request.urlopen(f"{url}/api/jobs/{job_id}/report")
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["job_id"] == job_id
        assert "status" in data
        assert "total_stages" in data
        assert "stage_summaries" in data
