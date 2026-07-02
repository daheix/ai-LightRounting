"""polaris-flow 通用流程编排子模块 smoke test。

测试覆盖（≥3 个 smoke test，R13 强制自测）：
- test_module_import: 包加载与 __version__ / __all__ 完整性
- test_core_job_flow_api: 作业流程核心 API（Job/Stage/Recipe/Workspace/Scheduler/Tracker）
- test_distributed_scheduler: DistributedTaskScheduler sequential 后端
- test_ipkiss_pcell_multiview: IPKISS PCell + NetlistView 多视图
- test_design_intent_engine: DesignIntentEngine 配置与验证
- test_ai_inverse_design_api: AI 逆向设计 API 可访问性
- test_lazy_export_raises_on_missing_core: lazy 导出在 polaris-core 缺失时 raise

来源（R02 学术诚信）:
- pytest 文档: https://docs.pytest.org/
- IPKISS PCell 架构: https://www.lucedaphotonics.com/products/ipkiss
- Cadence ADE-XL 作业调度: https://docs.cadence.com/
- Sutton & Barto 2018 RL: http://incompleteideas.net/book/RLbook2020.pdf
- Python asyncio Task cancellation:
  https://docs.python.org/3/library/asyncio-task.html#task-cancellation
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# 让测试既能从已安装包导入，也能从源码树导入（CI/开发模式）
_SRC = str(Path(__file__).resolve().parents[1] / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import polaris_flow  # noqa: E402


def test_module_import() -> None:
    """smoke test 1: 包加载与 __version__ / __all__ 完整性。"""
    assert polaris_flow.__version__ == "5.0.0"
    # 核心作业流程 API 必须在 __all__ 中
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


def test_core_job_flow_api() -> None:
    """smoke test 2: 作业流程核心 API 实例化与基本功能。"""
    # Recipe 实例化（全部字段有默认值）
    recipe = polaris_flow.Recipe()
    assert recipe.preset_id == "mzi"
    assert recipe.platform == "SOI"

    # Workspace 实例化（需要 output_dir + job_id）
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        ws = polaris_flow.Workspace(output_dir=tmpdir, job_id="test-job-001")
        assert ws.output_dir == tmpdir
        assert ws.job_id == "test-job-001"

        # Job 实例化（需要 job_id + recipe + workspace）
        job = polaris_flow.Job(
            job_id="test-job-001",
            recipe=recipe,
            workspace=ws,
        )
        assert job.job_id == "test-job-001"
        assert job.status == polaris_flow.JobStatus.QUEUED
        # 状态转换 QUEUED → RUNNING
        job.mark_running()
        assert job.status == polaris_flow.JobStatus.RUNNING

    # Stage 标准 stage 查询（STANDARD_STAGES 有 10 个 stage）
    assert len(polaris_flow.STANDARD_STAGES) == 10
    first_stage = polaris_flow.STANDARD_STAGES[0]
    assert first_stage.stage_id == 1
    # get_stage(stage_id) 返回 Stage
    stage = polaris_flow.get_stage(1)
    assert stage is not None
    assert stage.stage_id == 1


def test_distributed_scheduler() -> None:
    """smoke test 3: DistributedTaskScheduler sequential 后端基本功能。"""
    config = polaris_flow.DistributedConfig(backend="sequential", num_workers=1)
    scheduler = polaris_flow.DistributedTaskScheduler(config)
    try:
        # 提交一个简单任务
        def _task(x: int) -> int:
            return x * 2

        scheduler.submit("task-1", _task, 21)
        # 等待完成
        assert scheduler.wait_all(timeout=5.0)
        result = scheduler.get_result("task-1")
        assert result.status == polaris_flow.TaskStatus.COMPLETED
        assert result.result == 42
        # 聚合结果
        agg = scheduler.aggregate_results()
        assert agg["total_tasks"] == 1
        assert agg["completed"] == 1
    finally:
        scheduler.shutdown()


def test_ipkiss_pcell_multiview() -> None:
    """smoke test 4: IPKISS PCell + NetlistView 多视图。"""
    cell = polaris_flow.IPKISSPCell(
        name="mzi",
        cell_type="mmi_1x2",
        params={"length": 100.0},
    )
    # __post_init__ 应补全端口（mmi_1x2 → ["in", "out1", "out2"]）
    assert cell.ports == ["in", "out1", "out2"]

    # NetlistView 生成 SAX 格式网表
    netlist_view = cell.netlist_view
    netlist = netlist_view.generate()
    assert netlist["instances"] == {"mzi": "mmi_1x2"}
    assert "in" in netlist["ports"]
    assert netlist["ports"]["in"] == "mzi,in"


def test_design_intent_engine() -> None:
    """smoke test 5: DesignIntentEngine 配置实例化。"""
    config = polaris_flow.IntentConfig()
    assert config is not None
    # 引擎实例化（不执行 design，仅验证类可构造）
    engine = polaris_flow.DesignIntentEngine(config)
    assert engine is not None


def test_ai_inverse_design_api() -> None:
    """smoke test 6: AI 逆向设计 API 可访问性与配置实例化。"""
    # 配置类实例化
    rl_cfg = polaris_flow.RLInverseDesignConfig()
    gan_cfg = polaris_flow.GANInverseDesignConfig()
    diff_cfg = polaris_flow.DiffusionInverseDesignConfig()
    assert rl_cfg is not None
    assert gan_cfg is not None
    assert diff_cfg is not None

    # WaveguideSimulator 实例化
    sim = polaris_flow.WaveguideSimulator()
    assert sim is not None

    # PDKDeviceSampler 实例化
    sampler = polaris_flow.PDKDeviceSampler()
    assert sampler is not None


def test_lazy_export_raises_on_missing_core() -> None:
    """smoke test 7: lazy 导出在 polaris-core 缺失时 raise（R03 禁止 fall-back）。

    polaris-core 未安装时，访问 TrainingPipeline 应 raise ImportError
    （而非返回 None 或假数据）。
    """
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
