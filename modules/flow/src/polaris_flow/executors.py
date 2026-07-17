"""PoLaRIS 标准化流水线阶段执行函数（12 个阶段，工业光电子设计流程）。

本模块为 **facade**：实际实现已按职责拆分到 7 个子模块，本文件仅做
re-export，保持外部 ``from polaris_flow.executors import X`` 路径不变。

## 12 阶段工业光电子设计流程（对齐 Luceda/Synopsys/Ansys 商业工具链）

| 序号 | 阶段 | 工业对应环节 |
|------|------|-------------|
| 1 | ``stage1_pdk`` | PDK 器件目录加载 |
| 2 | ``stage2_circuit`` | 电路规格构建（原理图捕获） |
| 3 | ``stage3_simulation`` | 原理图级电路仿真（紧凑模型，版图前） |
| 4 | ``stage4_inverse`` | AI 逆向设计（器件设计优化，版图前） |
| 5 | ``stage5_placement`` | 器件布局 |
| 6 | ``stage6_routing`` | 波导布线 |
| 7 | ``stage7_postlayout_sim`` | 版图后仿真（含布线寄生） |
| 8 | ``stage8_drc_lvs`` | DRC/LVS 物理验证 |
| 9 | ``stage9_yield`` | 蒙特卡洛良率分析（流片前签核） |
| 10 | ``stage10_opto_electrical`` | 光电协同仿真 |
| 11 | ``stage11_quantum`` | 量子光子验证（应用层） |
| 12 | ``stage12_gds`` | GDS 版图导出（流片交付最后一步） |

工业流程依据（先仿真后版图、验证全过后才导出 GDS）:
- Luceda IPKISS: schematic capture → circuit simulation → layout →
  post-layout verification → tape-out
  https://docs.lucedaphotonics.com/
- Synopsys OptoCompiler: 原理图仿真先于物理实现，良率/corner 分析
  为流片前签核环节
  https://www.synopsys.com/photonic-solutions.html
- AIM Photonics PDK 设计流程教程（器件仿真→电路仿真→版图→DRC→流片）
  https://www.aimphotonics.com/

## 拆分结构（R09 单文件版本升级）

| 子模块 | 阶段 | 职责 |
|--------|------|------|
| ``stage_serializers`` | — | CircuitSpec/DeviceSpec 序列化与依赖输入校验 |
| ``stage_input`` | 1-2 | PDK 器件目录加载 + 电路规格构建 |
| ``stage_verification`` | 3, 7-8 | 原理图仿真 + 版图后仿真 + DRC/LVS |
| ``stage_advanced`` | 4, 11 | AI 逆向设计 + 量子光子验证 |
| ``stage_physical`` | 5-6 | 器件布局 + 波导布线 |
| ``stage_yield`` | 9 | 蒙特卡洛良率分析 |
| ``stage_output`` | 10, 12 | 光电协同仿真 + GDS 版图导出 |

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
- Bogaerts et al. 2018 OFC, 版图感知良率预测
  https://fib.intec.ugent.be/download/pub_4125.pdf
- Metropolis & Ulam 1949, 蒙特卡洛方法
  https://doi.org/10.1080/01621459.1949.10483310

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
    stage4_inverse,
    stage11_quantum,
)
from polaris_flow.stage_input import (  # noqa: F401
    stage1_pdk,
    stage2_circuit,
)
from polaris_flow.stage_output import (  # noqa: F401
    stage10_opto_electrical,
    stage12_gds,
)
from polaris_flow.stage_physical import (  # noqa: F401
    stage5_placement,
    stage6_routing,
)
from polaris_flow.stage_serializers import (  # noqa: F401
    _circuit_from_dict,
    _circuit_to_dict,
    _device_spec_from_dict,
    _device_spec_to_dict,
    _require_input,
)
from polaris_flow.stage_verification import (  # noqa: F401
    stage3_simulation,
    stage7_postlayout_sim,
    stage8_drc_lvs,
)
from polaris_flow.stage_yield import (  # noqa: F401
    stage9_yield,
)

# =============================================================================
# STAGE_EXECUTORS 字典（12 阶段工业流程）
# =============================================================================


STAGE_EXECUTORS: dict[int, callable] = {
    1: stage1_pdk,
    2: stage2_circuit,
    3: stage3_simulation,
    4: stage4_inverse,
    5: stage5_placement,
    6: stage6_routing,
    7: stage7_postlayout_sim,
    8: stage8_drc_lvs,
    9: stage9_yield,
    10: stage10_opto_electrical,
    11: stage11_quantum,
    12: stage12_gds,
}


__all__ = [
    "STAGE_EXECUTORS",
    "stage1_pdk",
    "stage2_circuit",
    "stage3_simulation",
    "stage4_inverse",
    "stage5_placement",
    "stage6_routing",
    "stage7_postlayout_sim",
    "stage8_drc_lvs",
    "stage9_yield",
    "stage10_opto_electrical",
    "stage11_quantum",
    "stage12_gds",
]
