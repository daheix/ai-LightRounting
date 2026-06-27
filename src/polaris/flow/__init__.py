"""商业级作业流程表达系统（polaris.flow）。

本模块对齐商业 EDA 工具的作业流程表达方式：
- Luceda IPKISS: PCell + 多视图架构 + Schematic-Driven Layout 闭环
- Cadence ADE-XL: 作业队列 + 资源调度 + 并行 worker 模型
- Synopsys ICC2: 实现流程的阶段依赖图
- Ansys Lumerical: 仿真任务的提交与追踪

学术来源:
- IPKISS: https://www.lucedaphotonics.com/products/ipkiss
- Cadence ADE-XL: https://docs.cadence.com/
- Synopsys ICC2: https://www.synopsys.com/
- Ansys Lumerical: https://www.ansys.com/products/photonics

公开 API 分为两部分:
1. 作业流程系统（Job/Stage/Recipe/Workspace/Tracker/Scheduler）
2. IPKISS 兼容流程（PCell/View/SDLFlow，来自 ipkiss_flow 模块）
"""

# === 作业流程系统 API ===
# === Design Intent 流程 API（来自 design_intent 模块，R20）===
from polaris.flow.design_intent import (
    DesignIntentEngine as DesignIntentFlowEngine,
)
from polaris.flow.design_intent import (
    IntentConfig,
)

# === IPKISS 兼容流程 API（来自 ipkiss_flow 模块）===
from polaris.flow.ipkiss_flow import (
    CircuitModelView,
    ClosedLoopValidator,
    IPKISSPCell,
    IPKISSPDKBridge,
    IPKISSView,
    LayoutView,
    NetlistView,
    SDLFlow,
)
from polaris.flow.job import Job, JobState, JobStatus
from polaris.flow.recipe import Recipe, SimConfig
from polaris.flow.scheduler import JobScheduler
from polaris.flow.stage import (
    STANDARD_STAGES,
    Stage,
    StageInput,
    StageOutput,
    StageResult,
    StageStatus,
    get_stage,
)
from polaris.flow.tracker import JobTracker
from polaris.flow.workspace import Workspace

__all__ = [
    # 作业流程系统
    "Job",
    "JobStatus",
    "JobState",
    "Stage",
    "StageInput",
    "StageOutput",
    "StageResult",
    "StageStatus",
    "STANDARD_STAGES",
    "get_stage",
    "Recipe",
    "SimConfig",
    "Workspace",
    "JobTracker",
    "JobScheduler",
    # IPKISS 兼容流程
    "IPKISSPCell",
    "IPKISSView",
    "NetlistView",
    "LayoutView",
    "CircuitModelView",
    "SDLFlow",
    "ClosedLoopValidator",
    "IPKISSPDKBridge",
    # Design Intent 流程（R20）
    "DesignIntentFlowEngine",
    "IntentConfig",
]
