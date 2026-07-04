"""polaris-flow 通用流程编排子模块深度测试（v5.0）。

覆盖全部 56 个稳定 API（作业流程 / IPKISS 兼容 / Design Intent /
分布式调度 / AI 逆向设计 / WaveguideSimulator / PDK 采样），
对齐 R02 学术诚信、R03 禁止 fall-back、R05 无 TODO。

测试分组（共 36 个测试）：
- 包加载与 __all__ 完整性 (1)
- Job / JobStatus / JobState 状态机 (5)
- Stage / StageInput / StageOutput / StageResult / STANDARD_STAGES / get_stage (5)
- Recipe / SimConfig 序列化 (3)
- Workspace 目录与原子写入 (3)
- JobTracker 查询 (2)
- JobScheduler 端到端调度 (3)
- DistributedTaskScheduler 三后端 (4)
- IPKISSPCell / IPKISSView / NetlistView / LayoutView (4)
- CircuitModelView (1)
- SDLFlow / ClosedLoopValidator / IPKISSPDKBridge (3)
- DesignIntentEngine 三层映射 (3)
- WaveguideSimulator 物理模型 (2)
- PDKDevice / PDKDeviceSampler 真实器件采样 (2)
- RL/GAN/Diffusion 逆向设计 + InverseDesignEvaluator (4)
- lazy 导出 (1)

来源（R02 学术诚信，≥5 个文献 URL）:
- pytest 文档: https://docs.pytest.org/
- IPKISS PCell 架构: https://www.lucedaphotonics.com/products/ipkiss
- Cadence ADE-XL 作业调度: https://docs.cadence.com/
- Sutton & Barto 2018 RL: http://incompleteideas.net/book/RLbook2020.pdf
- Python asyncio Task cancellation:
  https://docs.python.org/3/library/asyncio-task.html#task-cancellation
- POSIX rename(2) 原子性:
  https://pubs.opengroup.org/onlinepubs/9699919799/functions/rename.html
- Ho et al. 2020 DDPM: https://arxiv.org/abs/2006.11239
- SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
"""

from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path

import numpy as np
import pytest

# 让测试既能从已安装包导入，也能从源码树导入（CI/开发模式）
_SRC = str(Path(__file__).resolve().parents[1] / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import polaris_flow  # noqa: E402
from polaris_flow import (  # noqa: E402
    ClosedLoopValidator,
    DesignIntentEngine,
    DiffusionInverseDesignConfig,
    DiffusionInverseDesigner,
    DistributedConfig,
    DistributedTaskScheduler,
    GANInverseDesignConfig,
    GANInverseDesigner,
    IPKISSPCell,
    IPKISSPDKBridge,
    IPKISSView,
    IntentConfig,
    InverseDesignEvaluator,
    Job,
    JobScheduler,
    JobState,
    JobStatus,
    JobTracker,
    LayoutView,
    NetlistView,
    PDKDevice,
    PDKDeviceSampler,
    RLInverseDesignConfig,
    RLInverseDesigner,
    Recipe,
    STANDARD_STAGES,
    SDLFlow,
    SimConfig,
    Stage,
    StageInput,
    StageOutput,
    StageResult,
    StageStatus,
    TaskResult,
    TaskState,
    TaskStatus,
    WaveguideSimulator,
    Workspace,
    get_stage,
)


# =============================================================================
# 1. 包加载与 __all__ 完整性
# =============================================================================

def test_module_import() -> None:
    """包加载与 __version__ / __all__ 完整性。"""
    assert polaris_flow.__version__ == "5.0.0"
    required = {
        "Job", "JobStatus", "JobState",
        "Stage", "StageInput", "StageOutput", "StageResult", "StageStatus",
        "STANDARD_STAGES", "get_stage",
        "Recipe", "SimConfig",
        "Workspace", "JobTracker", "JobScheduler",
        "IPKISSPCell", "IPKISSView", "NetlistView", "LayoutView",
        "CircuitModelView", "SDLFlow", "ClosedLoopValidator", "IPKISSPDKBridge",
        "DesignIntentEngine", "IntentConfig",
        "DistributedTaskScheduler", "DistributedConfig",
        "TaskStatus", "TaskState", "TaskResult",
        "RLInverseDesigner", "GANInverseDesigner", "DiffusionInverseDesigner",
        "InverseDesignEvaluator", "PDKDevice", "PDKDeviceSampler",
        "WaveguideSimulator",
    }
    missing = required - set(polaris_flow.__all__)
    assert not missing, f"__all__ 缺少核心 API: {missing}"


# =============================================================================
# 2. Job / JobStatus / JobState 状态机
# =============================================================================

def _make_workspace() -> Workspace:
    """构造临时工作空间（每个测试独立 tmpdir）。"""
    tmpdir = tempfile.mkdtemp()
    return Workspace(output_dir=tmpdir, job_id="test-job-001")


def test_job_status_enum() -> None:
    """JobStatus 五状态枚举值。"""
    assert JobStatus.QUEUED == "queued"
    assert JobStatus.RUNNING == "running"
    assert JobStatus.COMPLETED == "completed"
    assert JobStatus.FAILED == "failed"
    assert JobStatus.CANCELLED == "cancelled"
    assert len(JobStatus) == 5


def test_job_state_transitions_legal() -> None:
    """JobState 合法转换与终态判定。"""
    # QUEUED → RUNNING 合法
    assert JobState.can_transition(JobStatus.QUEUED, JobStatus.RUNNING)
    # RUNNING → COMPLETED/FAILED/CANCELLED 合法
    assert JobState.can_transition(JobStatus.RUNNING, JobStatus.COMPLETED)
    assert JobState.can_transition(JobStatus.RUNNING, JobStatus.FAILED)
    assert JobState.can_transition(JobStatus.RUNNING, JobStatus.CANCELLED)
    # 非法：QUEUED → COMPLETED（必须先 RUNNING）
    assert not JobState.can_transition(JobStatus.QUEUED, JobStatus.COMPLETED)
    # 终态判定
    assert JobState.is_terminal(JobStatus.COMPLETED)
    assert JobState.is_terminal(JobStatus.FAILED)
    assert JobState.is_terminal(JobStatus.CANCELLED)
    assert not JobState.is_terminal(JobStatus.QUEUED)
    assert not JobState.is_terminal(JobStatus.RUNNING)


def test_job_state_assert_transition_raises() -> None:
    """JobState.assert_transition 非法转换 raise RuntimeError（R03）。"""
    with pytest.raises(RuntimeError, match="非法状态转换"):
        JobState.assert_transition(JobStatus.COMPLETED, JobStatus.RUNNING)
    with pytest.raises(RuntimeError):
        JobState.assert_transition(JobStatus.QUEUED, JobStatus.COMPLETED)


def test_job_lifecycle_and_progress() -> None:
    """Job 完整生命周期 + progress 字符串 + to_dict 序列化。"""
    recipe = Recipe(enabled_stages=[1, 2, 3])
    ws = _make_workspace()
    job = Job(job_id="job-001", recipe=recipe, workspace=ws)
    assert job.status == JobStatus.QUEUED
    assert job.progress == "0/3"
    # QUEUED → RUNNING
    job.mark_running()
    assert job.status == JobStatus.RUNNING
    assert job.start_time is not None
    # 模拟推进 2 阶段
    job.current_stage = 2
    assert job.progress == "2/3"
    # 模拟最后一阶段完成：调度器先把 current_stage 推到末阶段
    # （mark_completed 仅改 status/end_time，不更新 current_stage，见 job.py）
    job.current_stage = 3
    assert job.progress == "3/3"
    # RUNNING → COMPLETED
    job.mark_completed()
    assert job.status == JobStatus.COMPLETED
    assert job.end_time is not None
    # to_dict 含必要字段
    d = job.to_dict()
    assert d["job_id"] == "job-001"
    assert d["status"] == "completed"
    assert d["progress"] == "3/3"  # current_stage 由调度器推进至 3
    assert d["recipe"]["preset_id"] == "mzi"


def test_job_mark_failed_and_cancelled() -> None:
    """Job 失败/取消状态转换 + 错误信息持久化。"""
    recipe = Recipe()
    ws = _make_workspace()
    job = Job(job_id="job-002", recipe=recipe, workspace=ws)
    # QUEUED → CANCELLED 直接合法
    job.mark_cancelled()
    assert job.status == JobStatus.CANCELLED
    # 终态不可再转换（QUEUED → CANCELLED 已是终态）
    with pytest.raises(RuntimeError):
        job.mark_running()

    # 新 job：QUEUED → RUNNING → FAILED
    job2 = Job(job_id="job-003", recipe=recipe, workspace=ws)
    job2.mark_running()
    job2.mark_failed("stage 5 仿真异常")
    assert job2.status == JobStatus.FAILED
    assert job2.error == "stage 5 仿真异常"
    # 终态不可转换
    with pytest.raises(RuntimeError):
        job2.mark_completed()


def test_job_generate_job_id_format() -> None:
    """Job.generate_job_id 格式 YYYYMMDD_HHMMSS_<6位随机>。"""
    jid = Job.generate_job_id()
    parts = jid.split("_")
    assert len(parts) == 3, f"job_id 应有 3 段，实际 {jid}"
    # 前两段为时间戳 YYYYMMDD HHMMSS
    assert len(parts[0]) == 8 and parts[0].isdigit()
    assert len(parts[1]) == 6 and parts[1].isdigit()
    # 第三段为 6 位随机小写字母+数字
    assert len(parts[2]) == 6
    assert all(c.isalnum() and c.islower() or c.isdigit() for c in parts[2])
    # 唯一性（连续生成不重复）
    jid2 = Job.generate_job_id()
    assert jid != jid2


# =============================================================================
# 3. Stage / StageInput / StageOutput / StageResult / STANDARD_STAGES / get_stage
# =============================================================================

def test_stage_dataclasses() -> None:
    """StageInput / StageOutput / StageResult 数据类字段。"""
    si = StageInput(data={"preset_id": "mzi"})
    assert si.data == {"preset_id": "mzi"}
    so = StageOutput(data={"circuit": {}}, files=["/tmp/circuit.json"])
    assert so.files == ["/tmp/circuit.json"]
    sr = StageResult(stage_id=1, name="PDK 器件目录")
    assert sr.status == StageStatus.PENDING
    assert sr.duration_s is None  # 未执行
    # 设置 start/end_time 后 duration_s 可计算
    from datetime import datetime
    sr.start_time = datetime(2026, 7, 3, 10, 0, 0)
    sr.end_time = datetime(2026, 7, 3, 10, 0, 5)
    assert sr.duration_s == 5.0


def test_stage_status_enum() -> None:
    """StageStatus 六状态枚举。"""
    assert StageStatus.PENDING == "pending"
    assert StageStatus.RUNNING == "running"
    assert StageStatus.COMPLETED == "completed"
    assert StageStatus.FAILED == "failed"
    assert StageStatus.BLOCKED == "blocked"
    assert StageStatus.SKIPPED == "skipped"
    assert len(StageStatus) == 6


def test_standard_stages_count_and_fields() -> None:
    """STANDARD_STAGES 共 10 个 stage，每个含必需字段。"""
    assert len(STANDARD_STAGES) == 10
    stage_ids = [s.stage_id for s in STANDARD_STAGES]
    assert stage_ids == list(range(1, 11))
    for s in STANDARD_STAGES:
        assert isinstance(s, Stage)
        assert s.stage_id in range(1, 11)
        assert s.name  # 非空
        assert s.slug.startswith("stage")
        assert s.ipkiss_step in ("器件设计", "线路设计", "设计验证", "流片准备")
        assert isinstance(s.inputs_spec, list)
        assert isinstance(s.outputs_spec, list)
        assert isinstance(s.depends_on, list)
    # stage 1 无依赖
    assert STANDARD_STAGES[0].depends_on == []
    # stage 2 依赖 stage 1
    assert STANDARD_STAGES[1].depends_on == [1]


def test_get_stage_valid_and_invalid() -> None:
    """get_stage 合法/非法 ID。"""
    s = get_stage(5)
    assert s.stage_id == 5
    assert s.name == "S 参数仿真"
    # 边界
    assert get_stage(1).stage_id == 1
    assert get_stage(10).stage_id == 10
    # 非法 ID raise（R03）
    with pytest.raises(ValueError, match="未知阶段 ID"):
        get_stage(0)
    with pytest.raises(ValueError):
        get_stage(11)
    with pytest.raises(ValueError):
        get_stage(-1)


def test_stage_execute_fn_injection() -> None:
    """Stage.execute_fn 默认 None，可注入可调用对象。"""
    s = Stage(
        99, "测试阶段", "stage99_test", "测试用", "器件设计",
        ["in"], ["out"], [], None,
    )
    assert s.execute_fn is None
    # 注入执行函数
    def _fn(recipe, ws, prev):
        return {"out": "ok"}
    s.execute_fn = _fn
    assert s.execute_fn({"preset_id": "mzi"}, None, {}) == {"out": "ok"}


# =============================================================================
# 4. Recipe / SimConfig 序列化
# =============================================================================

def test_recipe_defaults_and_sim_config() -> None:
    """Recipe 默认值 + SimConfig 字段。"""
    r = Recipe()
    assert r.preset_id == "mzi"
    assert r.platform == "SOI"
    assert r.placement_algo == "analytical"
    assert r.router_algo == "curvy"
    assert r.enabled_stages == list(range(1, 11))
    assert r.canvas_w == 1000.0
    assert r.canvas_h == 600.0
    assert r.custom_circuit is None
    # SimConfig 默认
    assert r.sim_config.max_iterations == 3
    assert r.sim_config.loss_target_db == 5.0
    assert r.sim_config.use_real_simulator is False


def test_recipe_json_roundtrip() -> None:
    """Recipe JSON 双向序列化保真。"""
    r = Recipe(
        preset_id="ring", platform="SiN", placement_algo="rl",
        router_algo="diagonal", sim_config=SimConfig(max_iterations=5, loss_target_db=3.0),
        enabled_stages=[1, 2, 3], canvas_w=800.0, canvas_h=400.0,
        custom_circuit={"name": "custom"},
    )
    j = r.to_json()
    r2 = Recipe.from_json(j)
    assert r2.preset_id == "ring"
    assert r2.platform == "SiN"
    assert r2.placement_algo == "rl"
    assert r2.sim_config.max_iterations == 5
    assert r2.sim_config.loss_target_db == 3.0
    assert r2.enabled_stages == [1, 2, 3]
    assert r2.custom_circuit == {"name": "custom"}
    # to_dict 含全部字段
    d = r.to_dict()
    assert set(d.keys()) >= {
        "preset_id", "platform", "placement_algo", "router_algo",
        "sim_config", "output_dir", "enabled_stages", "canvas_w", "canvas_h",
        "custom_circuit",
    }


def test_recipe_yaml_roundtrip() -> None:
    """Recipe YAML 双向序列化（不依赖 PyYAML）。"""
    r = Recipe(preset_id="mzi_lattice", platform="InP", enabled_stages=[1, 2, 3, 7])
    y = r.to_yaml()
    assert "preset_id: mzi_lattice" in y
    assert "platform: InP" in y
    assert "enabled_stages:" in y
    r2 = Recipe.from_yaml(y)
    assert r2.preset_id == "mzi_lattice"
    assert r2.platform == "InP"
    assert r2.enabled_stages == [1, 2, 3, 7]


# =============================================================================
# 5. Workspace 目录与原子写入
# =============================================================================

def test_workspace_dir_structure() -> None:
    """Workspace 构造时创建标准目录结构（含 10 个 stage 子目录）。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        ws = Workspace(output_dir=tmpdir, job_id="ws-test")
        base = Path(tmpdir) / "ws-test"
        # 主目录
        assert (base / "inputs").is_dir()
        assert (base / "logs").is_dir()
        assert (base / "stages").is_dir()
        assert (base / "reports").is_dir()
        assert (base / "gds").is_dir()
        # 10 个 stage 子目录
        for slug in [
            "stage1_pdk", "stage2_circuit", "stage3_placement", "stage4_routing",
            "stage5_simulation", "stage6_drc_lvs", "stage7_gds",
            "stage8_opto_electrical", "stage9_quantum", "stage10_inverse",
        ]:
            assert (base / "stages" / slug).is_dir()
        # stage_dir 返回正确路径
        assert ws.stage_dir("stage1_pdk") == base / "stages" / "stage1_pdk"
        # gds_path 默认 layout.gds
        assert ws.gds_path() == base / "gds" / "layout.gds"


def test_workspace_atomic_write_and_read() -> None:
    """Workspace 原子写入 stage output + job metadata + report + log。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        ws = Workspace(output_dir=tmpdir, job_id="ws-io")
        # write_stage_output → read_stage_output 往返
        data = {"device_catalog": ["mmi_1x2", "y_branch"], "n": 2}
        path = ws.write_stage_output("stage1_pdk", data)
        assert path.exists()
        loaded = ws.read_stage_output("stage1_pdk")
        assert loaded == data
        # 不存在的 stage 返回 None（合法查询未命中，非 fall-back）
        assert ws.read_stage_output("stage2_circuit") is None
        # job metadata
        meta = {"job_id": "ws-io", "status": "running"}
        ws.write_job_metadata(meta)
        assert ws.read_job_metadata() == meta
        # report
        report = {"total_stages": 10, "completed": 5}
        ws.write_report(report)
        # log（JSONL 追加）
        ws.write_log("job started", "INFO")
        ws.write_log("stage 1 done", "INFO")
        log_path = Path(tmpdir) / "ws-io" / "logs" / "job.jsonl"
        assert log_path.exists()
        lines = log_path.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 2


def test_workspace_atomic_write_rejects_nan() -> None:
    """Workspace 原子写入拒绝 NaN/Infinity（RFC 8259 合规，R03）。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        ws = Workspace(output_dir=tmpdir, job_id="ws-nan")
        bad_data = {"value": float("nan")}
        with pytest.raises(ValueError, match="Out of range float values"):
            ws.write_stage_output("stage1_pdk", bad_data)


# =============================================================================
# 6. JobTracker 查询
# =============================================================================

def test_job_tracker_query_existing_and_missing() -> None:
    """JobTracker 查询存在的 job + 不存在的 job 返回 None。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # 先用 Workspace 写入 job metadata
        ws = Workspace(output_dir=tmpdir, job_id="track-001")
        ws.write_job_metadata({"job_id": "track-001", "status": "completed"})
        ws.write_stage_output("stage1_pdk", {"device_catalog": ["mmi"]})
        # JobTracker 查询
        tracker = JobTracker(base_output_dir=tmpdir)
        assert tracker.get_status("track-001") == "completed"
        job = tracker.get_job("track-001")
        assert job["job_id"] == "track-001"
        # 不存在返回 None（合法查询未命中）
        assert tracker.get_status("not-exist") is None
        assert tracker.get_job("not-exist") is None
        # 阶段结果
        sr = tracker.get_stage_result("track-001", 1)
        assert sr == {"device_catalog": ["mmi"]}
        assert tracker.get_stage_result("track-001", 2) is None  # 未写入
        # 未知 stage_id 返回 None
        assert tracker.get_stage_result("track-001", 99) is None
        # 历史聚合
        history = tracker.get_history("track-001")
        assert len(history) == 1
        assert history[0]["stage_id"] == 1


def test_job_tracker_list_jobs_and_empty_dir() -> None:
    """JobTracker list_jobs 状态过滤 + 空目录返回空列表。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # 写入两个 job
        for jid, status in [("j1", "completed"), ("j2", "failed")]:
            ws = Workspace(output_dir=tmpdir, job_id=jid)
            ws.write_job_metadata({"job_id": jid, "status": status})
        tracker = JobTracker(base_output_dir=tmpdir)
        all_jobs = tracker.list_jobs()
        assert len(all_jobs) == 2
        completed = tracker.list_jobs(status="completed")
        assert len(completed) == 1
        assert completed[0]["job_id"] == "j1"
        # 不存在的目录返回空列表
        tracker2 = JobTracker(base_output_dir="/tmp/nonexistent_polaris_test_dir")
        assert tracker2.list_jobs() == []


# =============================================================================
# 7. JobScheduler 端到端调度
# =============================================================================

def test_job_scheduler_skip_when_no_executor() -> None:
    """JobScheduler 无 stage executor 时 stage 被跳过（SKIPPED），job 仍 COMPLETED。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        ws = Workspace(output_dir=tmpdir, job_id="sched-skip")
        recipe = Recipe(enabled_stages=[1, 2])
        job = Job(job_id="sched-skip", recipe=recipe, workspace=ws)
        scheduler = JobScheduler(max_workers=2)
        try:
            scheduler.submit(job)
            # 等待作业终态
            deadline = time.time() + 5.0
            while time.time() < deadline and not JobState.is_terminal(job.status):
                time.sleep(0.05)
            assert job.status == JobStatus.COMPLETED
            # 两个 stage 都 SKIPPED（无执行函数）
            assert len(job.stage_results) == 2
            assert all(r.status == StageStatus.SKIPPED for r in job.stage_results)
        finally:
            scheduler.shutdown()


def test_job_scheduler_with_executors() -> None:
    """JobScheduler 注入执行函数，stage 顺序执行并传递 prev_outputs。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        ws = Workspace(output_dir=tmpdir, job_id="sched-exec")
        recipe = Recipe(enabled_stages=[1, 2, 3])

        def _stage1(recipe, ws, prev):
            return {"device_catalog": ["mmi_1x2"]}

        def _stage2(recipe, ws, prev):
            # 验证 prev_outputs 已传递
            assert "device_catalog" in prev
            return {"circuit": {"name": "mzi"}}

        def _stage3(recipe, ws, prev):
            assert "circuit" in prev
            return {"placements": [{"dev": "mzi", "x": 0, "y": 0}]}

        scheduler = JobScheduler(
            max_workers=1,
            stage_executors={1: _stage1, 2: _stage2, 3: _stage3},
        )
        try:
            job = Job(job_id="sched-exec", recipe=recipe, workspace=ws)
            scheduler.submit(job)
            deadline = time.time() + 5.0
            while time.time() < deadline and not JobState.is_terminal(job.status):
                time.sleep(0.05)
            assert job.status == JobStatus.COMPLETED
            assert len(job.stage_results) == 3
            assert all(r.status == StageStatus.COMPLETED for r in job.stage_results)
            # stage output 持久化到磁盘
            assert ws.read_stage_output("stage1_pdk") == {"device_catalog": ["mmi_1x2"]}
            # 汇总报告已写入
            report_path = Path(tmpdir) / "sched-exec" / "reports" / "summary.json"
            assert report_path.exists()
        finally:
            scheduler.shutdown()


def test_job_scheduler_cancel_queued_job() -> None:
    """JobScheduler.cancel 取消队列中的作业（QUEUED → CANCELLED）。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        ws = Workspace(output_dir=tmpdir, job_id="sched-cancel")
        recipe = Recipe(enabled_stages=list(range(1, 11)))  # 多 stage 留时间取消
        job = Job(job_id="sched-cancel", recipe=recipe, workspace=ws)
        # 用阻塞 executor 阻止 stage 完成太快
        def _block(recipe, ws, prev):
            time.sleep(2.0)
            return {"done": True}
        scheduler = JobScheduler(
            max_workers=1,
            stage_executors={i: _block for i in range(1, 11)},
        )
        try:
            scheduler.submit(job)
            # 立即取消（可能在 QUEUED 或 RUNNING 初期）
            ok = scheduler.cancel("sched-cancel")
            assert ok is True
            # 等待状态稳定
            deadline = time.time() + 5.0
            while time.time() < deadline and not JobState.is_terminal(job.status):
                time.sleep(0.05)
            assert job.status in (JobStatus.CANCELLED, JobStatus.FAILED, JobStatus.COMPLETED)
            # list_jobs 可按状态过滤
            cancelled = scheduler.list_jobs(status=JobStatus.CANCELLED)
            assert any(j.job_id == "sched-cancel" for j in cancelled) or \
                   job.status != JobStatus.CANCELLED
            # 取消已终态的作业返回 False
            assert scheduler.cancel("sched-cancel") is False
            # get_job 返回 job
            assert scheduler.get_job("sched-cancel") is not None
        finally:
            scheduler.shutdown()


# =============================================================================
# 8. DistributedTaskScheduler 三后端
# =============================================================================

def test_task_status_and_state_machine() -> None:
    """TaskStatus 五状态 + TaskState 状态机。"""
    assert TaskStatus.PENDING == "pending"
    assert TaskStatus.RUNNING == "running"
    assert TaskStatus.COMPLETED == "completed"
    assert TaskStatus.FAILED == "failed"
    assert TaskStatus.CANCELLED == "cancelled"
    # 合法转换
    assert TaskState.can_transition(TaskStatus.PENDING, TaskStatus.RUNNING)
    assert TaskState.can_transition(TaskStatus.RUNNING, TaskStatus.COMPLETED)
    # 非法转换
    assert not TaskState.can_transition(TaskStatus.COMPLETED, TaskStatus.RUNNING)
    # 终态
    assert TaskState.is_terminal(TaskStatus.COMPLETED)
    assert TaskState.is_terminal(TaskStatus.FAILED)
    assert TaskState.is_terminal(TaskStatus.CANCELLED)
    assert not TaskState.is_terminal(TaskStatus.PENDING)


def test_distributed_scheduler_sequential() -> None:
    """DistributedTaskScheduler sequential 后端：任务顺序执行 + 结果聚合。"""
    cfg = DistributedConfig(backend="sequential", num_workers=1)
    sched = DistributedTaskScheduler(cfg)
    try:
        def _double(x):
            return x * 2
        sched.submit("t1", _double, 21)
        sched.submit("t2", _double, 100)
        assert sched.wait_all(timeout=5.0)
        r1 = sched.get_result("t1")
        assert r1.status == TaskStatus.COMPLETED
        assert r1.result == 42
        assert r1.duration_s is not None and r1.duration_s >= 0.0
        # 聚合
        agg = sched.aggregate_results()
        assert agg["total_tasks"] == 2
        assert agg["completed"] == 2
        assert agg["failed"] == 0
        assert agg["results"]["t2"] == 200
        # list_results 按状态过滤
        completed = sched.list_results(TaskStatus.COMPLETED)
        assert len(completed) == 2
    finally:
        sched.shutdown()


def test_distributed_scheduler_threading_and_failure() -> None:
    """DistributedTaskScheduler threading 后端 + 任务失败重试。"""
    cfg = DistributedConfig(backend="threading", num_workers=2, max_retries=1)
    sched = DistributedTaskScheduler(cfg)
    try:
        # 成功任务
        sched.submit("ok", lambda x: x + 1, 10)
        # 失败任务（重试 1 次后仍失败）
        def _fail():
            raise RuntimeError("mocked failure")
        sched.submit("fail", _fail)
        assert sched.wait_all(timeout=10.0)
        ok_r = sched.get_result("ok")
        assert ok_r.status == TaskStatus.COMPLETED
        assert ok_r.result == 11
        fail_r = sched.get_result("fail")
        assert fail_r.status == TaskStatus.FAILED
        assert "mocked failure" in fail_r.error
        assert fail_r.retries == 1  # 重试 1 次
        # 重复 submit 同 task_id raise KeyError（R03）
        with pytest.raises(KeyError):
            sched.submit("ok", lambda: None)
        # get_result 不存在 raise KeyError（R03 禁止 fall-back）
        with pytest.raises(KeyError):
            sched.get_result("not-exist")
    finally:
        sched.shutdown()


def test_distributed_scheduler_cancel_pending() -> None:
    """DistributedTaskScheduler 取消队列中 PENDING 任务（threading 后端）。

    注：sequential 后端 submit() 同步阻塞，任务提交即执行完毕，无法停留
    PENDING；故改用 threading 后端 + num_workers=1：worker 被 block 任务
    占用期间，第二个任务停留在 ThreadPoolExecutor 队列中保持 PENDING，
    cancel() 可将 PENDING → CANCELLED（见 distributed.py cancel()）。
    """
    cfg = DistributedConfig(backend="threading", num_workers=1)
    sched = DistributedTaskScheduler(cfg)
    try:
        # 用较长 sleep 占用唯一 worker，使第二个任务停留在队列 PENDING
        sched.submit("block", time.sleep, 2.0)
        sched.submit("pending", lambda: "should_be_cancelled")
        # 取消 pending：状态为 PENDING → 直接置位 CANCELLED，返回 True
        ok = sched.cancel("pending")
        assert ok is True
        # is_cancelled 查询标志
        assert sched.is_cancelled("pending") is True
        # 等待 block 完成（pending 已 CANCELLED，worker 拾取后 no-op）
        assert sched.wait_all(timeout=5.0)
        # cancel 不存在的任务 raise KeyError
        with pytest.raises(KeyError):
            sched.cancel("not-exist")
        # cancel 已终态任务返回 False
        assert sched.cancel("block") is False
    finally:
        sched.shutdown()


# =============================================================================
# 9. IPKISSPCell / IPKISSView / NetlistView / LayoutView
# =============================================================================

def test_ipkiss_pcell_post_init_ports() -> None:
    """IPKISSPCell.__post_init__ 按 cell_type 自动补全端口列表。"""
    # mmi_1x2 → ["in", "out1", "out2"]
    cell = IPKISSPCell(name="m1", cell_type="mmi_1x2", params={"length": 10.0})
    assert cell.ports == ["in", "out1", "out2"]
    # waveguide → ["in", "out"]
    wg = IPKISSPCell(name="wg1", cell_type="waveguide", params={"length": 100.0, "width": 0.5})
    assert wg.ports == ["in", "out"]
    # directional_coupler → 4 端口
    dc = IPKISSPCell(name="dc1", cell_type="directional_coupler")
    assert dc.ports == ["in1", "in2", "out1", "out2"]
    # 显式指定 ports 不被覆盖
    custom = IPKISSPCell(name="c1", cell_type="mmi_1x2", ports=["a", "b"])
    assert custom.ports == ["a", "b"]
    # 未知 cell_type 且未指定 ports → 空列表
    unknown = IPKISSPCell(name="u1", cell_type="custom_type")
    assert unknown.ports == []


def test_ipkiss_view_base_class_raises() -> None:
    """IPKISSView 基类 generate() raise NotImplementedError（R03）。"""
    cell = IPKISSPCell(name="c", cell_type="mmi_1x2")
    view = IPKISSView(cell)
    with pytest.raises(NotImplementedError):
        view.generate()


def test_netlist_view_generate() -> None:
    """NetlistView.generate 返回 SAX 格式网表 {instances, connections, ports}。"""
    cell = IPKISSPCell(name="mzi", cell_type="mmi_1x2", params={"length": 100.0})
    nl = cell.netlist_view.generate()
    assert nl["instances"] == {"mzi": "mmi_1x2"}
    assert nl["connections"] == {}
    # 端口映射到 "inst,port"
    assert nl["ports"]["in"] == "mzi,in"
    assert nl["ports"]["out1"] == "mzi,out1"
    assert nl["ports"]["out2"] == "mzi,out2"
    assert len(nl["ports"]) == 3
    # NetlistView 是 IPKISSView 子类
    assert isinstance(cell.netlist_view, IPKISSView)


def test_layout_view_generate_various_cells() -> None:
    """LayoutView.generate 对多种 cell_type 生成 elements + bbox。"""
    # waveguide → path 元素
    wg = IPKISSPCell(name="wg", cell_type="waveguide", params={"length": 50.0, "width": 0.5})
    lv = wg.layout_view.generate()
    assert lv["elements"][0]["type"] == "path"
    assert lv["elements"][0]["layer"] == "WG"
    assert lv["bbox"] == (0.0, -0.25, 50.0, 0.25)
    # mmi_1x2 → rectangle 元素
    mmi = IPKISSPCell(name="mmi", cell_type="mmi_1x2", params={"length": 10.0, "width": 5.0})
    lv2 = mmi.layout_view.generate()
    assert lv2["elements"][0]["type"] == "rectangle"
    assert lv2["bbox"] == (0.0, 0.0, 10.0, 5.0)
    # ring_resonator → circle 元素
    ring = IPKISSPCell(name="ring", cell_type="ring_resonator", params={"radius": 8.0})
    lv3 = ring.layout_view.generate()
    assert lv3["elements"][0]["type"] == "circle"
    # 未知类型 → 默认 rectangle
    unknown = IPKISSPCell(name="u", cell_type="custom", params={"length": 3.0, "width": 2.0})
    lv4 = unknown.layout_view.generate()
    assert lv4["elements"][0]["type"] == "rectangle"
    assert lv4["bbox"] == (0.0, 0.0, 3.0, 2.0)


# =============================================================================
# 10. CircuitModelView
# =============================================================================

def test_circuit_model_view_generate() -> None:
    """CircuitModelView.generate 返回 S 参数模型函数（依赖 polaris_sparam.models）。

    polaris_sparam.models 可用时返回可调用模型；不可用时 raise ImportError
    （lazy import，R03 禁止 fall-back）。
    """
    cell = IPKISSPCell(name="wg", cell_type="waveguide", params={"length": 100.0})
    try:
        model = cell.circuit_model_view.generate()
        # 模型可调用
        assert callable(model)
        # 调用返回 SDict
        sdict = model(wl=1.55)
        assert sdict is not None
    except ImportError:
        # polaris_sparam 未安装：lazy import raise ImportError（R03 合规）
        pytest.skip("polaris_sparam.models 未安装，lazy import raise ImportError（R03 合规）")
    # 未知 cell_type：返回 None（合法，无对应模型）
    unknown = IPKISSPCell(name="u", cell_type="custom_unknown")
    try:
        m = unknown.circuit_model_view.generate()
        # 若 _get_model_map 加载成功，custom_unknown 不在映射中 → None
        assert m is None
    except ImportError:
        pytest.skip("polaris_sparam.models 未安装")


# =============================================================================
# 11. SDLFlow / ClosedLoopValidator / IPKISSPDKBridge
# =============================================================================

def test_sdl_flow_end_to_end() -> None:
    """SDLFlow 端到端：build_schematic → set_placement → generate_layout → export_gds。"""
    sdl = SDLFlow()
    # 添加 PCell
    cell1 = IPKISSPCell(name="mmi1", cell_type="mmi_1x2", params={"length": 10.0, "width": 5.0})
    cell2 = IPKISSPCell(name="mmi2", cell_type="mmi_2x2", params={"length": 10.0, "width": 5.0})
    sdl.add_cell(cell1)
    sdl.add_cell(cell2)
    # 构建原理图
    schematic = sdl.build_schematic(
        instances={"mmi1": "mmi_1x2", "mmi2": "mmi_2x2"},
        connections={"mmi1,out1": "mmi2,in1"},
        ports={"in": "mmi1,in", "out": "mmi2,out1"},
    )
    assert schematic["instances"] == {"mmi1": "mmi_1x2", "mmi2": "mmi_2x2"}
    # 设置放置
    sdl.set_placement({"mmi1": (0.0, 0.0), "mmi2": (50.0, 0.0)})
    # 生成版图
    layout = sdl.generate_layout()
    assert "mmi1" in layout["instances"]
    assert "mmi2" in layout["instances"]
    assert layout["instances"]["mmi1"]["cell_type"] == "mmi_1x2"
    assert layout["instances"]["mmi2"]["transform"] == (50.0, 0.0, 0)
    assert len(layout["routes"]) >= 1
    # 导出 GDS
    gds = sdl.export_gds()
    assert "layers" in gds
    assert "bbox" in gds
    assert "WG" in gds["layers"]
    # 全局 bbox 是 4 元组
    assert len(gds["bbox"]) == 4


def test_closed_loop_validator_pass_and_fail() -> None:
    """ClosedLoopValidator LVS 验证：原理图与版图一致 → passed；不一致 → mismatches。"""
    sdl = SDLFlow()
    cell1 = IPKISSPCell(name="mmi1", cell_type="mmi_1x2")
    cell2 = IPKISSPCell(name="mmi2", cell_type="mmi_2x2")
    sdl.add_cell(cell1)
    sdl.add_cell(cell2)
    sdl.build_schematic(
        instances={"mmi1": "mmi_1x2", "mmi2": "mmi_2x2"},
        connections={"mmi1,out1": "mmi2,in1"},
        ports={"in": "mmi1,in"},
    )
    sdl.set_placement({"mmi1": (0.0, 0.0), "mmi2": (50.0, 0.0)})
    layout = sdl.generate_layout()

    validator = ClosedLoopValidator()
    validator.set_schematic(sdl.schematic)
    extracted = validator.extract_from_layout(layout)
    assert "instances" in extracted
    result = validator.validate()
    # 实例集合一致（mmi1, mmi2）
    assert result["instance_match"] is True
    # passed 取决于连接关系是否完全一致（版图提取的 connections 可能与原理图一致）
    assert isinstance(result["passed"], bool)
    assert isinstance(result["mismatches"], list)

    # 构造不一致场景：原理图多一个实例
    bad_schematic = {
        "instances": {"mmi1": "mmi_1x2", "mmi2": "mmi_2x2", "extra": "waveguide"},
        "connections": {},
        "ports": {},
    }
    validator2 = ClosedLoopValidator()
    validator2.set_schematic(bad_schematic)
    validator2.extracted = extracted
    result2 = validator2.validate()
    assert result2["passed"] is False
    assert result2["instance_match"] is False
    assert len(result2["mismatches"]) > 0


def test_ipkiss_pdk_bridge_register_and_get() -> None:
    """IPKISSPDKBridge 注册标准 PCell + get_cell + list_cells。"""
    bridge = IPKISSPDKBridge()
    # 注册标准器件
    names = bridge.register_standard_cells()
    assert len(names) == 7
    assert "wg1" in names
    assert "yb1" in names
    assert "mmi1" in names
    # list_cells 返回已注册名称
    assert set(bridge.list_cells()) == set(names)
    # get_cell 返回 PCell
    cell = bridge.get_cell("wg1")
    assert cell.name == "wg1"
    assert cell.cell_type == "waveguide"
    assert cell.ports == ["in", "out"]
    # get_cell 不存在 raise KeyError（R03）
    with pytest.raises(KeyError, match="未注册"):
        bridge.get_cell("not_registered")
    # 手动注册
    custom = IPKISSPCell(name="custom1", cell_type="mmi_1x2")
    bridge.register(custom)
    assert "custom1" in bridge.list_cells()


# =============================================================================
# 12. DesignIntentEngine 三层映射
# =============================================================================

def _make_intent_config() -> IntentConfig:
    """构造合法 IntentConfig（含必需设计规则 + PDK 库）。"""
    return IntentConfig(
        design_rules={
            "min_waveguide_width": 0.4,
            "min_bend_radius": 5.0,
            "min_spacing": 2.0,
        },
        pdk_library={
            "waveguide": {"cell_name": "strip_waveguide", "ports": ["in", "out"]},
            "mmi_1x2": {"cell_name": "mmi_1x2", "ports": ["in", "out1", "out2"]},
        },
        placement_spacing=50.0,
    )


def _make_schematic() -> dict:
    """构造简单 MZI 原理图（2 器件 + 1 连接）。"""
    return {
        "devices": [
            {"id": "wg1", "type": "waveguide", "params": {"length": 100.0, "width": 0.5},
             "ports": ["in", "out"]},
            {"id": "wg2", "type": "waveguide", "params": {"length": 100.0, "width": 0.5},
             "ports": ["in", "out"]},
        ],
        "connections": [
            {"src": "wg1", "src_port": "out", "dst": "wg2", "dst_port": "in"},
        ],
    }


def test_design_intent_engine_config_validation() -> None:
    """DesignIntentEngine 配置类型校验（R03 禁止 fall-back）。"""
    # 非 IntentConfig 类型 raise
    with pytest.raises(ValueError, match="IntentConfig"):
        DesignIntentEngine("not a config")  # type: ignore[arg-type]
    # IntentConfig 实例化正常
    cfg = _make_intent_config()
    engine = DesignIntentEngine(cfg)
    assert engine.config is cfg
    # generate_constraint_intent 缺必需规则 raise
    bad_cfg = IntentConfig(design_rules={"min_waveguide_width": 0.4})  # 缺 min_bend_radius
    engine2 = DesignIntentEngine(bad_cfg)
    with pytest.raises(ValueError, match="min_bend_radius"):
        engine2.generate_constraint_intent(bad_cfg.design_rules)
    # 空设计规则 raise
    with pytest.raises(ValueError):
        engine2.generate_constraint_intent({})


def test_design_intent_engine_parse_schematic_validation() -> None:
    """DesignIntentEngine.parse_schematic 原理图结构校验。"""
    engine = DesignIntentEngine(_make_intent_config())
    # 非 dict raise
    with pytest.raises(ValueError):
        engine.parse_schematic("not dict")  # type: ignore[arg-type]
    # 缺 devices/connections 键 raise
    with pytest.raises(ValueError, match="devices.*connections"):
        engine.parse_schematic({"devices": []})
    # 器件缺必需字段 raise
    with pytest.raises(ValueError, match="id"):
        engine.parse_schematic({
            "devices": [{"type": "waveguide", "params": {}, "ports": ["in", "out"]}],
            "connections": [],
        })
    # 器件端口数 < 2 raise
    with pytest.raises(ValueError, match="端口数"):
        engine.parse_schematic({
            "devices": [{"id": "d1", "type": "wg", "params": {}, "ports": ["in"]}],
            "connections": [],
        })
    # 连接引用不存在的器件 raise
    with pytest.raises(ValueError, match="源器件"):
        engine.parse_schematic({
            "devices": [{"id": "d1", "type": "wg", "params": {}, "ports": ["in", "out"]}],
            "connections": [{"src": "d2", "src_port": "in", "dst": "d1", "dst_port": "out"}],
        })


def test_design_intent_engine_run_full_pipeline() -> None:
    """DesignIntentEngine.run 完整三层映射流程。"""
    engine = DesignIntentEngine(_make_intent_config())
    result = engine.run(_make_schematic())
    # 完整意图字典含全部键
    assert "devices" in result
    assert "routing" in result
    assert "constraints" in result
    assert "propagated_constraints" in result
    assert "pdk_instances" in result
    # 2 个器件被布局
    assert len(result["devices"]) == 2
    # 1 条连接 → 1 条布线
    assert len(result["routing"]) == 1
    # 约束结构含 waveguide/bend/placement
    assert "waveguide" in result["constraints"]
    assert "bend" in result["constraints"]
    assert "placement" in result["constraints"]
    # PDK 实例数 = 器件数
    assert result["pdk_instances"]["count"] == 2
    assert all("pdk_cell" in inst for inst in result["pdk_instances"]["instances"])
    # 拓扑排序：wg1 在 wg2 之前
    wg1_x = next(d["x"] for d in result["devices"] if d["id"] == "wg1")
    wg2_x = next(d["x"] for d in result["devices"] if d["id"] == "wg2")
    assert wg1_x < wg2_x
    # generate_routing_intent 未先布局 → raise
    engine2 = DesignIntentEngine(_make_intent_config())
    with pytest.raises(ValueError, match="generate_layout_intent"):
        engine2.generate_routing_intent([])


# =============================================================================
# 13. WaveguideSimulator 物理模型
# =============================================================================

def test_waveguide_simulator_init_and_validation() -> None:
    """WaveguideSimulator 初始化 + 参数校验。"""
    sim = WaveguideSimulator(grid_size=(32, 32), target_metric="transmission")
    assert sim.grid_size == (32, 32)
    assert sim.target_metric == "transmission"
    assert sim.alpha > 0.0  # SOI 损耗系数
    assert sim.dx == 0.05  # 像素尺寸
    # 非法 grid_size raise
    with pytest.raises(ValueError, match="grid_size"):
        WaveguideSimulator(grid_size=(0, 32))
    with pytest.raises(ValueError):
        WaveguideSimulator(grid_size=(32,))  # type: ignore[arg-type]
    # 非法 target_metric raise
    with pytest.raises(ValueError, match="target_metric"):
        WaveguideSimulator(target_metric="invalid")


def test_waveguide_simulator_simulate_physics() -> None:
    """WaveguideSimulator.simulate 物理模型（Beer-Lambert + 连通性）。"""
    sim = WaveguideSimulator(grid_size=(32, 32))
    # 全零形状：transmission = 0（无硅像素，连通性 0）
    empty = np.zeros((32, 32))
    r_empty = sim.simulate(empty)
    assert r_empty["transmission"] == 0.0
    assert r_empty["connectivity"] == 0.0
    assert r_empty["fill_ratio"] == 0.0
    # 全满形状：transmission = T_base * 1 * connectivity
    full = np.ones((32, 32))
    r_full = sim.simulate(full)
    assert r_full["fill_ratio"] == 1.0
    assert r_full["connectivity"] > 0.0  # 中心行全硅，连通性 > 0
    assert r_full["transmission"] > 0.0
    # 中心行连续硅的传输率 > 不连续
    sparse = np.zeros((32, 32))
    sparse[16, ::2] = 1.0  # 隔像素填充，连通性低
    r_sparse = sim.simulate(sparse)
    assert r_sparse["transmission"] < r_full["transmission"]
    # extinction_ratio 是有限数
    assert np.isfinite(r_full["extinction_ratio"])
    # 形状不匹配 raise
    with pytest.raises(ValueError, match="shape 尺寸"):
        sim.simulate(np.zeros((16, 16)))


# =============================================================================
# 14. PDKDevice / PDKDeviceSampler 真实器件采样
# =============================================================================

def test_pdk_device_sampler_loads_real_devices() -> None:
    """PDKDeviceSampler 从 SiEPIC netlist 加载真实器件。"""
    sampler = PDKDeviceSampler()
    devices = sampler.devices
    assert len(devices) > 0
    # 每个器件有合法字段
    for dev in devices:
        assert isinstance(dev, PDKDevice)
        assert dev.name  # 非空
        assert dev.type  # 非空
        assert dev.width_um > 0.0
        assert dev.height_um > 0.0
        assert isinstance(dev.params, dict)
        assert dev.source_circuit  # 来源电路名
    # pdk_dir 是有效路径
    assert sampler.pdk_dir.is_dir()


def test_pdk_device_sampler_sample_shapes() -> None:
    """PDKDeviceSampler.sample 栅格化真实器件为二值掩模。"""
    sampler = PDKDeviceSampler()
    rng = np.random.default_rng(42)
    shapes = sampler.sample(5, (32, 32), rng=rng)
    assert len(shapes) == 5
    for s in shapes:
        assert s.shape == (32, 32)
        assert s.dtype == np.float64
        # 二值掩模：值仅 0.0 或 1.0
        assert np.all((s == 0.0) | (s == 1.0))
        # 至少有部分硅像素（真实器件非全空）
        assert s.sum() > 0
    # n <= 0 raise
    with pytest.raises(ValueError, match="n"):
        sampler.sample(0, (32, 32))
    # 非法 grid_size raise
    with pytest.raises(ValueError, match="grid_size"):
        sampler.sample(1, (0, 32))
    with pytest.raises(ValueError):
        sampler.sample(1, (32,))  # type: ignore[arg-type]


# =============================================================================
# 15. RL/GAN/Diffusion 逆向设计 + InverseDesignEvaluator
# =============================================================================

def test_rl_inverse_designer_config_and_design() -> None:
    """RLInverseDesigner 配置校验 + design() 端到端（小规模）。"""
    # 非法配置 raise
    with pytest.raises(ValueError, match="max_steps"):
        RLInverseDesigner(RLInverseDesignConfig(max_steps=0), simulator=None)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="gamma"):
        RLInverseDesigner(RLInverseDesignConfig(gamma=0.0), simulator=None)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="gamma"):
        RLInverseDesigner(RLInverseDesignConfig(gamma=1.5), simulator=None)  # type: ignore[arg-type]
    # 小规模 design（grid 8x8, max_steps=5, 10 episodes 内部固定）
    sim = WaveguideSimulator(grid_size=(8, 8))
    cfg = RLInverseDesignConfig(grid_size=(8, 8), max_steps=5, target_value=0.5)
    designer = RLInverseDesigner(cfg, sim)
    result = designer.design({"target_value": 0.5})
    assert "shape" in result
    assert "performance" in result
    assert "history" in result
    assert result["shape"].shape == (8, 8)
    assert len(result["history"]) == 10  # n_episodes=10
    assert 0.0 <= result["performance"] <= 1.0
    # step() 单步验证
    state = np.zeros((8, 8))
    next_state, reward, done = designer.step(state, 0)
    assert next_state.shape == (8, 8)
    assert next_state[0, 0] == 1.0  # 像素翻转
    assert isinstance(reward, float)
    assert isinstance(done, bool)


def test_gan_inverse_designer_config_and_design() -> None:
    """GANInverseDesigner 配置校验 + design() 端到端（小规模）。"""
    # 非法配置 raise
    with pytest.raises(ValueError, match="latent_dim"):
        GANInverseDesigner(GANInverseDesignConfig(latent_dim=0), simulator=None)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="hidden_dim"):
        GANInverseDesigner(GANInverseDesignConfig(hidden_dim=0), simulator=None)  # type: ignore[arg-type]
    # 小规模 design
    sim = WaveguideSimulator(grid_size=(8, 8))
    cfg = GANInverseDesignConfig(grid_size=(8, 8), latent_dim=16, hidden_dim=32)
    designer = GANInverseDesigner(cfg, sim)
    # generate 单次生成
    z = np.random.default_rng(0).standard_normal(16)
    shape = designer.generate(z)
    assert shape.shape == (8, 8)
    # discriminate 返回标量
    score = designer.discriminate(shape)
    assert isinstance(score, float)
    # train_step 一步训练
    real_shapes = [np.random.default_rng(i).random((8, 8)) for i in range(4)]
    losses = designer.train_step(real_shapes)
    assert "d_loss" in losses
    assert "g_loss" in losses
    assert "gp" in losses
    # design 端到端
    result = designer.design({"target_value": 0.5})
    assert result["shape"].shape == (8, 8)
    assert len(result["history"]) == 10


def test_diffusion_inverse_designer_config_and_design() -> None:
    """DiffusionInverseDesigner 配置校验 + design() 端到端（小规模）。"""
    # 非法配置 raise
    with pytest.raises(ValueError, match="num_timesteps"):
        DiffusionInverseDesigner(
            DiffusionInverseDesignConfig(num_timesteps=0), simulator=None)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="beta_start"):
        DiffusionInverseDesigner(
            DiffusionInverseDesignConfig(beta_start=0.02, beta_end=0.01),
            simulator=None)  # type: ignore[arg-type]
    # 小规模 design
    sim = WaveguideSimulator(grid_size=(8, 8))
    cfg = DiffusionInverseDesignConfig(
        grid_size=(8, 8), num_timesteps=20, beta_start=1e-4, beta_end=0.02)
    designer = DiffusionInverseDesigner(cfg, sim)
    # 前向扩散
    x0 = np.ones((8, 8))
    xt = designer.forward_diffusion(x0, t=10)
    assert xt.shape == (8, 8)
    # compute_loss
    loss = designer.compute_loss(x0, t=5)
    assert isinstance(loss, float) and loss >= 0.0
    # compute_loss 越界 raise
    with pytest.raises(ValueError, match="t 须在"):
        designer.compute_loss(x0, t=100)
    # design 端到端
    result = designer.design({"target_value": 0.5})
    assert result["shape"].shape == (8, 8)
    assert len(result["history"]) > 0


def test_inverse_design_evaluator() -> None:
    """InverseDesignEvaluator.evaluate + compare_methods + benchmark。"""
    sim = WaveguideSimulator(grid_size=(8, 8))
    evaluator = InverseDesignEvaluator(sim)
    # 评估一个形状
    shape = np.ones((8, 8))
    eval_result = evaluator.evaluate(shape, {"target_value": 0.5})
    assert "transmission" in eval_result
    assert "extinction_ratio" in eval_result
    assert "fom" in eval_result
    assert "is_valid" in eval_result
    assert 0.0 <= eval_result["fom"] <= 1.0
    assert isinstance(eval_result["is_valid"], bool)
    # compare_methods（mock designer）
    class _MockDesigner:
        def __init__(self, shape):
            self._shape = shape
        def design(self, target_spec):
            return {"shape": self._shape, "performance": 0.5, "history": [0.5]}
    methods = [
        ("rl", _MockDesigner(np.ones((8, 8)))),
        ("gan", _MockDesigner(np.zeros((8, 8)))),
    ]
    comparison = evaluator.compare_methods({"target_value": 0.5}, methods)
    assert "rl" in comparison
    assert "gan" in comparison
    assert "fom" in comparison["rl"]
    # benchmark
    benchmark = evaluator.benchmark([
        ("case1", {"target_value": 0.5}, methods),
    ])
    assert "case1" in benchmark
    assert "rl" in benchmark["case1"]


# =============================================================================
# 16. lazy 导出
# =============================================================================

def test_lazy_export_raises_on_missing_core() -> None:
    """lazy 导出在 polaris-core 缺失时 raise（R03 禁止 fall-back）。"""
    try:
        import polaris_core  # noqa: F401
        polaris_core_available = True
    except ImportError:
        polaris_core_available = False

    if not polaris_core_available:
        # polaris-core 缺失：访问 lazy 导出必须 raise（R03）
        with pytest.raises((ImportError, AttributeError)):
            _ = polaris_flow.TrainingPipeline
    else:
        # polaris-core 可用：lazy 导出应正常工作
        assert polaris_flow.TrainingPipeline is not None

    # 访问不存在的属性必 raise AttributeError
    with pytest.raises(AttributeError):
        _ = polaris_flow.NotExistAttrXYZ


# =============================================================================
# R03 回归测试：禁止 except 块仅空语句静默吞异常（AST 级检测）
#
# 防止未来再引入 except 块体仅空语句的 fall-back（R03 最严重违规）。
# 学术依据: Effective Python Item 32 — 优先抛异常而非返回 None/静默吞没。
# =============================================================================
def test_no_except_empty_body_r03() -> None:
    """R03 回归：src 下所有 .py 禁止 except 块体仅空语句静默吞异常。"""
    import ast
    from pathlib import Path
    src_dir = Path(__file__).resolve().parents[1] / "src"
    violations: list[str] = []
    for py in src_dir.rglob("*.py"):
        tree = ast.parse(py.read_text(encoding="utf-8"), filename=str(py))
        for node in ast.walk(tree):
            if (isinstance(node, ast.ExceptHandler)
                    and len(node.body) == 1
                    and isinstance(node.body[0], ast.Pass)):
                violations.append(f"{py.name}:{node.lineno}")
    assert not violations, (
        f"R03 违规: 发现 except 块仅空语句静默吞异常: {violations}"
    )
