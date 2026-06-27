"""阶段（Stage）数据结构 + 10 阶段标准化定义。

对齐商业 EDA 工具的设计流程阶段划分：
- Luceda IPKISS: 四步流程（器件设计 → 线路设计 → 设计验证 → 流片准备）
- Cadence ADE-XL: 测试流程的阶段化执行
- Synopsys ICC2: 实现流程的阶段依赖图
- Ansys Lumerical: 仿真流程的步骤化组织

学术来源:
- IPKISS 四步流程: https://docs.lucedaphotonics.com/
  器件设计 → 线路设计 → 设计验证 → 流片准备
- Cadence ADE-XL 阶段化测试: https://docs.cadence.com/
- Synopsys ICC2 阶段依赖: https://www.synopsys.com/
- Ansys Lumerical 仿真步骤: https://www.ansys.com/products/photonics

10 阶段定义对齐 IPKISS 四步流程:
    阶段 1, 10        → 器件设计（PDK 目录 / 逆向设计）
    阶段 2, 3, 4      → 线路设计（电路规格 / 布局 / 布线）
    阶段 5, 6, 8, 9   → 设计验证（S 参数 / DRC-LVS / 光电协同 / 量子验证）
    阶段 7            → 流片准备（GDS 导出）
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class StageStatus(StrEnum):
    """阶段执行状态枚举"""

    PENDING = "pending"      # 未开始
    RUNNING = "running"      # 执行中
    COMPLETED = "completed"  # 成功完成
    FAILED = "failed"        # 执行失败
    BLOCKED = "blocked"      # 被阻塞（依赖未满足）
    SKIPPED = "skipped"      # 跳过（无执行函数或被禁用）


@dataclass
class StageInput:
    """阶段输入"""

    data: dict[str, Any] = field(default_factory=dict)  # 输入数据


@dataclass
class StageOutput:
    """阶段输出"""

    data: dict[str, Any] = field(default_factory=dict)  # 输出数据
    files: list[str] = field(default_factory=list)  # 输出文件路径列表


@dataclass
class StageResult:
    """阶段执行结果"""

    stage_id: int
    name: str
    status: StageStatus = StageStatus.PENDING
    output: StageOutput = field(default_factory=StageOutput)
    error: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None

    @property
    def duration_s(self) -> float | None:
        """阶段执行耗时（秒），未完成时返回 None"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None


@dataclass
class Stage:
    """阶段定义

    每个 Stage 描述一个流水线阶段的元信息：
    - stage_id: 1-10 的唯一标识
    - name: 人类可读名称（中文）
    - slug: 目录名用的英文标识
    - ipkiss_step: 对应 Luceda IPKISS 流程步骤
    - inputs_spec / outputs_spec: 输入输出键名规范
    - depends_on: 依赖的前置阶段 ID
    - execute_fn: 实际执行函数（由调度器注入）
    """

    stage_id: int  # 1-10
    name: str  # 如 "PDK 器件目录"
    slug: str  # 如 "stage1_pdk"（用于目录名）
    description: str
    ipkiss_step: str  # 对应 Luceda IPKISS 步骤
    inputs_spec: list[str]  # 期望输入键名
    outputs_spec: list[str]  # 期望输出键名
    depends_on: list[int]  # 依赖的阶段 ID
    execute_fn: Callable | None = None  # 执行函数


# 10 个标准化阶段定义（对齐 Luceda IPKISS 四步流程）
STANDARD_STAGES: list[Stage] = [
    Stage(
        1, "PDK 器件目录", "stage1_pdk", "展示平台 PDK 器件目录", "器件设计",
        ["platform"], ["device_catalog"], [], None,
    ),
    Stage(
        2, "电路规格定义", "stage2_circuit", "定义电路规格（器件+连接）", "线路设计",
        ["preset_id"], ["circuit"], [1], None,
    ),
    Stage(
        3, "AI 布局", "stage3_placement", "RL/解析布局算法", "线路设计",
        ["circuit"], ["placements"], [2], None,
    ),
    Stage(
        4, "智能布线", "stage4_routing", "弯曲感知布线", "线路设计",
        ["circuit", "placements"], ["routes"], [3], None,
    ),
    Stage(
        5, "S 参数仿真", "stage5_simulation", "频域 S 参数仿真", "设计验证",
        ["circuit", "placements", "routes"], ["sparams"], [4], None,
    ),
    Stage(
        6, "DRC/LVS 验证", "stage6_drc_lvs", "设计规则检查", "设计验证",
        ["placements", "routes"], ["drc_report"], [4], None,
    ),
    Stage(
        7, "GDS 导出", "stage7_gds", "GDSII 文件导出", "流片准备",
        ["placements", "routes"], ["gds_path"], [4], None,
    ),
    Stage(
        8, "光电协同", "stage8_opto_electrical", "光电联合仿真", "设计验证",
        ["circuit", "placements"], ["opto_electrical"], [3], None,
    ),
    Stage(
        9, "量子光子验证", "stage9_quantum", "量子光子电路验证", "设计验证",
        ["circuit"], ["quantum_report"], [2], None,
    ),
    Stage(
        10, "逆向设计", "stage10_inverse", "伴随逆向设计", "器件设计",
        ["target_spec"], ["inverse_design"], [], None,
    ),
]


def get_stage(stage_id: int) -> Stage:
    """根据 ID 获取阶段定义，未知 ID 抛出 ValueError"""
    for s in STANDARD_STAGES:
        if s.stage_id == stage_id:
            return s
    raise ValueError(f"未知阶段 ID: {stage_id}")
