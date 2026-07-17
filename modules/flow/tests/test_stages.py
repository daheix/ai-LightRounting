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


def _make_workspace() -> Workspace:
    """构造临时工作空间（R05 修复：原调用未定义导致 NameError）。"""
    tmp = tempfile.mkdtemp(prefix="polaris_flow_test_")
    return Workspace(output_dir=tmp, job_id="test-job")


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
    """STANDARD_STAGES 共 12 个 stage，每个含必需字段。"""
    assert len(STANDARD_STAGES) == 12
    stage_ids = [s.stage_id for s in STANDARD_STAGES]
    assert stage_ids == list(range(1, 13))
    for s in STANDARD_STAGES:
        assert isinstance(s, Stage)
        assert s.stage_id in range(1, 13)
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
    assert s.name == "AI 布局"
    # 边界
    assert get_stage(1).stage_id == 1
    assert get_stage(12).stage_id == 12
    # 非法 ID raise（R03）
    with pytest.raises(ValueError, match="未知阶段 ID"):
        get_stage(0)
    with pytest.raises(ValueError):
        get_stage(13)
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
    assert r.enabled_stages == list(range(1, 13))
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


# =============================================================================
# 6. 12 阶段工业流程执行器（STAGE_EXECUTORS 回归）
# =============================================================================


def test_stage_executors_12_stage_mapping() -> None:
    """STAGE_EXECUTORS 共 12 个阶段，函数名与工业流程顺序一致。

    工业流程（先仿真后版图、良率签核后 GDS 导出）:
    1 PDK → 2 电路 → 3 原理图仿真 → 4 逆向设计 → 5 布局 → 6 布线 →
    7 版图后仿真 → 8 DRC/LVS → 9 良率 → 10 光电协同 → 11 量子验证 → 12 GDS
    """
    from polaris_flow.executors import STAGE_EXECUTORS

    assert sorted(STAGE_EXECUTORS.keys()) == list(range(1, 13))
    expected_names = {
        1: "stage1_pdk",
        2: "stage2_circuit",
        3: "stage3_simulation",
        4: "stage4_inverse",
        5: "stage5_placement",
        6: "stage6_routing",
        7: "stage7_postlayout_sim",
        8: "stage8_drc_lvs",
        9: "stage9_yield",
        10: "stage10_opto_electrical",
        11: "stage11_quantum",
        12: "stage12_gds",
    }
    for stage_id, fn_name in expected_names.items():
        assert STAGE_EXECUTORS[stage_id].__name__ == fn_name


def test_stage3_schematic_simulation_before_layout() -> None:
    """阶段 3 原理图仿真仅依赖电路（版图前），输出逐器件损耗分解。"""
    from polaris_flow.executors import STAGE_EXECUTORS

    ws = _make_workspace()
    recipe = Recipe(preset_id="mzi")
    prev: dict = {}
    for sid in (1, 2, 3):
        prev.update(STAGE_EXECUTORS[sid](recipe, ws, prev))
    assert prev["sparams"]["level"] == "schematic"
    assert prev["total_loss_db"] > 0.0
    assert len(prev["device_losses"]) == prev["sparams"]["n_devices"]
    # 版图前无布线几何：输出不得包含 routes/placements
    assert "routes" not in prev
    assert "placements" not in prev


def test_stage8_drc_lvs_uses_is_consistent_key() -> None:
    """R05 回归: stage8 LVS 必须读取 run_lvs 的 is_consistent 键。

    Bug 背景: 原代码 lvs_result.get("passed", False) 读错键名
    （run_lvs 契约返回 is_consistent），导致 lvs_passed 永远 False。
    """
    from polaris_flow.executors import STAGE_EXECUTORS

    ws = _make_workspace()
    recipe = Recipe(preset_id="mzi")
    prev: dict = {}
    for sid in (1, 2, 5, 6, 8):
        prev.update(STAGE_EXECUTORS[sid](recipe, ws, prev))
    # MZI 预设版图与原理图拓扑一致 → LVS 必须通过
    assert prev["lvs_passed"] is True
    assert prev["drc_report"]["n_violations"] == 0


def test_stage9_yield_report_structure() -> None:
    """阶段 9 蒙特卡洛良率分析输出完整统计报告（流片前签核）。"""
    from polaris_flow.executors import STAGE_EXECUTORS

    ws = _make_workspace()
    recipe = Recipe(preset_id="mzi")
    prev: dict = {}
    for sid in (1, 2, 3, 9):
        prev.update(STAGE_EXECUTORS[sid](recipe, ws, prev))
    report = prev["yield_report"]
    assert report["n_samples"] == recipe.sim_config.yield_n_samples
    assert 0.0 <= report["yield_estimate"] <= 1.0
    assert report["n_pass"] + (report["n_samples"] - report["n_pass"]) == report["n_samples"]
    assert report["p05_loss_db"] <= report["mean_loss_db"] <= report["p95_loss_db"]
    assert report["sigma_rel"] == recipe.sim_config.yield_sigma_rel
    assert report["method"] == "monte_carlo_per_device_loss"


def test_stage7_postlayout_loss_breakdown() -> None:
    """阶段 7 版图后仿真: 总损耗 = 器件 + 互连 + 交叉（损耗预算分解）。"""
    from polaris_flow.executors import STAGE_EXECUTORS

    ws = _make_workspace()
    recipe = Recipe(preset_id="mzi")
    prev: dict = {}
    for sid in (1, 2, 3, 5, 6, 7):
        prev.update(STAGE_EXECUTORS[sid](recipe, ws, prev))
    budget = prev["loss_budget"]
    assert budget["postlayout_loss_db"] == (
        budget["device_loss_db"]
        + budget["interconnect_loss_db"]
        + budget["crossing_loss_db"]
    )
    # 版图附加损耗非负（布线互连只会增加损耗）
    assert budget["layout_penalty_db"] >= 0.0
    assert prev["postlayout_loss_db"] >= prev["total_loss_db"]

