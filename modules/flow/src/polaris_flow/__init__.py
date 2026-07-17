"""PoLaRIS 通用流程编排子模块（polaris-flow）。

从 v4 旧包 ``polaris.flow``（16 文件）+ ``polaris.pipeline``（4 文件）+
``polaris.system``（DistributedTaskScheduler）+ ``polaris.ai``（3 文件）
迁移而来，提供商业级作业流程编排、IPKISS 兼容流程、Design Intent 引擎、
分布式任务调度、AI 逆向设计与训练流水线能力。

## IPO 三段式说明

### I（Inputs）
- 电路规格 ``CircuitSpec``/``DeviceSpec``（来自 ``polaris-core``）
- 作业配置 ``Recipe`` / ``SimConfig`` / ``IntentConfig`` / ``DistributedConfig``
- IPKISS PCell 参数字典 / AI 逆向设计配置

### P（Process）
1. 作业流程：``Job`` → ``Stage``（9 个标准 stage）→ ``JobScheduler`` 调度 →
   ``JobTracker`` 追踪 → ``Workspace`` 持久化
2. IPKISS 兼容：``IPKISSPCell`` → 多视图（Netlist/Layout/CircuitModel）→
   ``SDLFlow`` 闭环 → ``ClosedLoopValidator`` 验证
3. Design Intent：原理图 → 布局/布线/约束意图 → PDK 器件实例（三层映射）
4. 分布式调度：``DistributedTaskScheduler`` 支持 sequential/threading/asyncio
   三后端，CANCELLED 状态严格走真实取消流程
5. AI 逆向设计：RL/GAN/Diffusion 三路并行，PDKDeviceSampler 真实器件采样
6. 训练流水线：基准数据 → 变体生成 → PPO 训练 → 仿真校验闭环

### O（Outputs）
- ``Job``/``StageResult``（含 status/duration/result/error）
- ``Workspace`` 持久化目录（含 metadata.json）
- IPKISS 多视图产物（SAX 网表 / GDS 几何 / S 参数模型）
- ``TaskResult``（分布式任务结果，含 status/result/error/retries）
- ``TrainingResult``（训练日志 + 检查点路径 + 校准结果）

## 稳定 API

### 作业流程系统
- ``Job`` / ``JobStatus`` / ``JobState``：作业与状态机
- ``Stage`` / ``StageInput`` / ``StageOutput`` / ``StageResult`` / ``StageStatus``
- ``STANDARD_STAGES`` / ``get_stage``：12 个标准 stage（工业光电子设计流程）
- ``Recipe`` / ``SimConfig``：作业配方
- ``Workspace`` / ``JobTracker`` / ``JobScheduler``：工作区与调度

### IPKISS 兼容流程
- ``IPKISSPCell`` / ``IPKISSView`` / ``NetlistView`` / ``LayoutView`` / ``CircuitModelView``
- ``SDLFlow`` / ``ClosedLoopValidator`` / ``IPKISSPDKBridge``

### Design Intent 流程
- ``DesignIntentFlowEngine`` / ``IntentConfig``

### 分布式任务调度
- ``DistributedTaskScheduler`` / ``DistributedConfig``
- ``TaskStatus`` / ``TaskState`` / ``TaskResult``

### AI 逆向设计
- ``RLInverseDesigner`` / ``RLInverseDesignConfig``
- ``GANInverseDesigner`` / ``GANInverseDesignConfig``
- ``DiffusionInverseDesigner`` / ``DiffusionInverseDesignConfig``
- ``InverseDesignEvaluator`` / ``PDKDevice`` / ``PDKDeviceSampler`` / ``WaveguideSimulator``

### 训练流水线（依赖 polaris-core，lazy 导出）
- ``TrainingPipeline`` / ``TrainingConfig`` / ``TrainingResult``

## 设计原则

- R03 禁止 fall-back：失败即 raise，无 return None/[] 假数据
- R04 不参与 GPU：纯 NumPy/SciPy 实现
- R05 无 TODO/FIXME 残留
- R13 不保留 v4 兼容：内部 import 全部改为 ``polaris_flow.*``
- 跨子模块依赖（polaris.sim/engine/router/eval/pdk/trainer）采用 lazy import，
  运行时按需加载，缺失则 raise ImportError（符合 R03）

## 来源（R02 学术诚信，≥5 个文献 URL）

- IPKISS/Luceda PCell + View 架构:
  https://www.lucedaphotonics.com/products/ipkiss
- Cadence ADE-XL 作业队列与资源调度:
  https://docs.cadence.com/
- Synopsys OptoDesigner Design Intent:
  https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner.html
- Mingaleev et al., "Rapid virtual prototyping of complex photonic integrated
  circuits using layout-aware schematic-driven design methodology",
  Proc. SPIE 10107, 1010708 (2017), doi:10.1117/12.2252001:
  https://doi.org/10.1117/12.2252001
- Sutton & Barto 2018, Reinforcement Learning（REINFORCE 策略梯度）:
  http://incompleteideas.net/book/RLbook2020.pdf
- Liu et al., "Generative model for the inverse design of photonic nanodevices",
  Nanophotonics 2024, DOI: 10.1515/nanoph-2023-0683:
  https://doi.org/10.1515/nanoph-2023-0683
- Liu et al., "PDN: A Diffusion Model for Photonic Device Inverse Design",
  arXiv:2407.03028: https://arxiv.org/abs/2407.03028
- PEP 492 async/await 语法（asyncio 后端取消机制）:
  https://peps.python.org/pep-0492/
- Python asyncio Task cancellation（CANCELLED 状态实现）:
  https://docs.python.org/3/library/asyncio-task.html#task-cancellation
- Ray RLlib 分布式作业管理对标:
  https://docs.ray.io/en/latest/rllib/
- IMPALA: Espeholt et al., 2018, arXiv:1802.01561:
  https://arxiv.org/abs/1802.01561
- SiEPIC EBeam PDK（真实器件数据源）:
  https://github.com/SiEPIC/SiEPIC_EBeam_PDK
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

# === 作业流程系统（无外部依赖，纯 stdlib）===
from polaris_flow.distributed import (
    DistributedConfig,
    DistributedTaskScheduler,
    TaskResult,
    TaskState,
    TaskStatus,
)
from polaris_flow.job import Job, JobState, JobStatus
from polaris_flow.recipe import Recipe, SimConfig
from polaris_flow.scheduler import JobScheduler
from polaris_flow.stage import (
    STANDARD_STAGES,
    Stage,
    StageInput,
    StageOutput,
    StageResult,
    StageStatus,
    get_stage,
)
from polaris_flow.tracker import JobTracker
from polaris_flow.workspace import Workspace

# === Design Intent 流程（无外部依赖）===
from polaris_flow.design_intent import DesignIntentEngine, IntentConfig

# === IPKISS 兼容流程（polaris.sim.models 为 lazy import）===
from polaris_flow.ipkiss_flow import (
    CircuitModelView,
    ClosedLoopValidator,
    IPKISSPCell,
    IPKISSPDKBridge,
    IPKISSView,
    LayoutView,
    NetlistView,
    SDLFlow,
)

# === AI 逆向设计（同包内依赖）===
from polaris_flow.inverse_design import (
    DiffusionInverseDesignConfig,
    DiffusionInverseDesigner,
    GANInverseDesignConfig,
    GANInverseDesigner,
    InverseDesignEvaluator,
    RLInverseDesignConfig,
    RLInverseDesigner,
)
from polaris_flow.pdk_device_sampler import PDKDevice, PDKDeviceSampler
from polaris_flow.waveguide_simulator import WaveguideSimulator

__version__ = "5.0.0"

# 依赖 polaris-core 的模块通过 __getattr__ lazy 导出（polaris-core 未安装时
# 仅在显式访问时 raise ImportError，不影响核心 API 使用）
_LAZY_EXPORTS: dict[str, str] = {
    # 训练流水线（依赖 polaris-core.specs + polaris.trainer/sim/pipeline）
    "TrainingPipeline": "polaris_flow.training",
    "TrainingConfig": "polaris_flow.training",
    "TrainingResult": "polaris_flow.training",
    # stage executors（间接依赖 polaris-core via stage_serializers）
    "STAGE_EXECUTORS": "polaris_flow.executors",
}


def __getattr__(name: str) -> Any:
    """Lazy 导出依赖 polaris-core 的 API（R03: 缺失则 raise ImportError）。"""
    module_path = _LAZY_EXPORTS.get(name)
    if module_path is None:
        raise AttributeError(f"module 'polaris_flow' has no attribute {name!r}")
    import importlib

    module = importlib.import_module(module_path)
    if not hasattr(module, name):
        raise AttributeError(
            f"module {module_path!r} has no attribute {name!r}"
        )
    return getattr(module, name)


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
    # Design Intent 流程
    "DesignIntentEngine",
    "IntentConfig",
    # 分布式任务调度
    "DistributedTaskScheduler",
    "DistributedConfig",
    "TaskStatus",
    "TaskState",
    "TaskResult",
    # AI 逆向设计
    "RLInverseDesigner",
    "RLInverseDesignConfig",
    "GANInverseDesigner",
    "GANInverseDesignConfig",
    "DiffusionInverseDesigner",
    "DiffusionInverseDesignConfig",
    "InverseDesignEvaluator",
    "PDKDevice",
    "PDKDeviceSampler",
    "WaveguideSimulator",
    # 训练流水线（lazy 导出，依赖 polaris-core）
    "TrainingPipeline",
    "TrainingConfig",
    "TrainingResult",
    # stage executors（lazy 导出，依赖 polaris-core）
    "STAGE_EXECUTORS",
    "__version__",
]
