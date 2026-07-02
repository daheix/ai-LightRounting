"""PoLaRIS 标准化流水线阶段执行函数（10 个阶段）。

本模块为 **facade**：实际实现已按职责拆分到 6 个子模块，本文件仅做
re-export，保持外部 ``from polaris_flow.executors import X`` 路径不变。

## 拆分结构（R09 单文件版本升级）

| 子模块 | 阶段 | 职责 |
|--------|------|------|
| ``stage_serializers`` | — | CircuitSpec/DeviceSpec 序列化与依赖输入校验 |
| ``stage_input`` | 1-2 | PDK 器件目录加载 + 电路规格构建 |
| ``stage_physical`` | 3-4 | 器件布局 + 波导布线 |
| ``stage_verification`` | 5-6 | S 参数仿真 + DRC/LVS 约束检查 |
| ``stage_output`` | 7-8 | GDS 版图导出 + 光电协同仿真 |
| ``stage_advanced`` | 9-10 | 量子光子验证 + AI 逆向设计 |

## 10 个标准化阶段

1. ``stage1_pdk`` — PDK 器件目录加载
2. ``stage2_circuit`` — 电路规格构建
3. ``stage3_placement`` — 器件布局
4. ``stage4_routing`` — 波导布线
5. ``stage5_simulation`` — S 参数仿真
6. ``stage6_drc_lvs`` — DRC/LVS 约束检查
7. ``stage7_gds`` — GDS 版图导出
8. ``stage8_opto_electrical`` — 光电协同仿真
9. ``stage9_quantum`` — 量子光子验证
10. ``stage10_inverse`` — AI 逆向设计

每个阶段函数签名统一为 ``stageN_xxx(recipe, workspace, prev_outputs) -> dict``，
由 JobScheduler 按 ``recipe.enabled_stages`` 顺序调用。阶段间通过
``prev_outputs`` 字典传递数据，不依赖全局状态或副作用。

## 学术来源

- IPKISS Schematic-Driven Layout 流程
  https://docs.lucedaphotonics.com/
- gdsfactory 端到端流水线
  https://gdsfactory.github.io/gdsfactory/
- SiEPIC EBeam PDK 设计规则
  https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- DREAMPlace 解析法布局 (DAC 2019/TCAD 2020)
  https://arxiv.org/abs/2004.10746
- Apollo arXiv 2025: 布线感知布局
  https://arxiv.org/html/2504.18813v1
- LiDAR ISPD'25: 弯曲波导布线
  https://dl.acm.org/doi/pdf/10.1145/3698364.3705355
- Hong, Ou, Mandel, PRL 1987, HOM 干涉
  https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.59.2044
- Clements et al., Optica 2016, Clements 量子网络
  https://opg.optica.org/optica/fulltext.cfm?uri=optica-3-12-1460
- Lalau-Keraly 2013 OE, adjoint shape optimization
  https://doi.org/10.1364/OE.21.0021693
- Piggott 2017 Nature Photonics, 逆向设计
  https://doi.org/10.1038/nphoton.2017.126

## 设计约束

1. 所有阶段输出必须是可 JSON 序列化的（dict/list/str/int/float/bool）
2. CircuitSpec 对象须序列化为 dict 再传递
3. 禁止 fall-back 设计（R03）：错误时 raise 异常，不返回假数据
4. 依赖输入缺失时 raise ValueError 告警
"""

from __future__ import annotations

# Facade re-export：实际实现见各 stage_* 子模块。
# noqa: F401 表示这些符号仅用于 re-export，本模块内不直接使用。
from polaris_flow.stage_advanced import (  # noqa: F401
    stage9_quantum,
    stage10_inverse,
)
from polaris_flow.stage_input import (  # noqa: F401
    stage1_pdk,
    stage2_circuit,
)
from polaris_flow.stage_output import (  # noqa: F401
    stage7_gds,
    stage8_opto_electrical,
)
from polaris_flow.stage_physical import (  # noqa: F401
    stage3_placement,
    stage4_routing,
)
from polaris_flow.stage_serializers import (  # noqa: F401
    _circuit_from_dict,
    _circuit_to_dict,
    _device_spec_from_dict,
    _device_spec_to_dict,
    _require_input,
)
from polaris_flow.stage_verification import (  # noqa: F401
    stage5_simulation,
    stage6_drc_lvs,
)

# =============================================================================
# STAGE_EXECUTORS 字典
# =============================================================================


STAGE_EXECUTORS: dict[int, callable] = {
    1: stage1_pdk,
    2: stage2_circuit,
    3: stage3_placement,
    4: stage4_routing,
    5: stage5_simulation,
    6: stage6_drc_lvs,
    7: stage7_gds,
    8: stage8_opto_electrical,
    9: stage9_quantum,
    10: stage10_inverse,
}


__all__ = [
    "STAGE_EXECUTORS",
    "stage1_pdk",
    "stage2_circuit",
    "stage3_placement",
    "stage4_routing",
    "stage5_simulation",
    "stage6_drc_lvs",
    "stage7_gds",
    "stage8_opto_electrical",
    "stage9_quantum",
    "stage10_inverse",
]
