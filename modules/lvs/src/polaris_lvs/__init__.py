"""polaris-lvs 子模块：LVS 网表一致性比对（单一职责，从 polaris-verify 拆分）。

PoLaRIS v5.0 把原 polaris-verify 拆分为 polaris-drc + polaris-lvs 两个独立子模块
（R13 代码清理，禁止多个 vx 文件并存；单一职责："DRC 就是 DRC，LVS 是 LVS"）。
本子模块仅负责 LVS（Layout Versus Schematic），保持原 ``run_lvs`` Python API
名与返回结构不变，便于后续 orchestrator 平滑迁移。

## Input → Process → Output 三段式文档

### Input
- ``circuit: dict`` — polaris-core 风格电路规格
  - 必含字段: ``devices`` (list[dict])、``connections`` (list)
  - 每个 device 含 ``name`` / ``device_type``
  - connections 格式 ``[(dev1, port1, dev2, port2), ...]``
- ``netlist: dict | None`` — 提取网表（版图网表）
  - 格式 ``{devices: [...], connections: [...]}``
  - ``None`` 时用 circuit 自身派生的网表（自比对，验证 API 一致性）

### Process
1. 从 ``circuit`` 提取参考网表（器件名+类型 + 拓扑连接）
2. 若提供 ``netlist`` 参数，将其作为提取网表（版图网表）；
   若 ``netlist=None``，参考网表与自身比对
3. 比对两个网表:
   - 器件集合差集（缺失/多余器件）
   - 器件类型一致性（同名器件类型不匹配）
   - 连接集合差集（缺失/多余连接，连接归一化为有序对去重）

光子电路 LVS 特点:
- 与电子 LVS（MOS/BJT 器件提取）不同，光子 LVS 通过器件实例名 + 类型识别器件
- 通过连接关系（dev1.port1 ↔ dev2.port2）识别网表拓扑
- 来源: KLayout LVS API https://www.klayout.org/doc-qt5/manual/lvs.html

### Output
- ``dict``::

      {
          "is_consistent": bool,       # 是否完全一致
          "n_mismatches": int,         # 不匹配项数
          "mismatches": list[dict],    # 不匹配详情
          "n_devices": int,            # 参考网表器件数
          "n_connections": int,        # 参考网表连接数
      }
  - 每个 mismatch dict: ``{type, message, device_name, net_name}``
  - ``is_consistent=True`` 表示版图与原理图拓扑一致，可签核流片

## 设计原则
- 对外 API 返回 JSON-serializable dict（与 polaris-core 一致）
- 纯 NumPy 实现（R04: 不参与 GPU；禁止 CuPy/CUDA/ROCm）
- 禁止 fall-back（R03）: 校验失败 raise RuntimeError，不返回哨兵值/假数据
- 函数 ≤80 行 / 文件 ≤800 行 / 圈复杂度 ≤15（AGENTS.md 质量门禁）

## 来源（R02 学术诚信，≥5 个文献 URL）
- KLayout LVS API: https://www.klayout.org/doc-qt5/manual/lvs.html
- SiEPIC EBeam PDK DEVREC 标准（器件识别层 layer 68）
  https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- Chrostowski & Hochberg, "Silicon Photonics Design", CUP 2015, p.353
  https://www.cambridge.org/core/search?searchField=isbn&searchTerms=1107007731
- gdsfactory PDK 文档（网表提取）
  https://gdsfactory.github.io/gdsfactory/notebooks/09_pdk_import.html
- Luceda IPKISS（光子电路网表验证）
  https://www.lucedaphotonics.com/en/products/ipkiss
- Calibre nmLVS（工业 LVS 比对算法）
  https://eda.sw.siemens.com/en-US/calibre/
"""

from __future__ import annotations

from polaris_lvs.compare import (
    LVSMismatch,
    LVSMismatchType,
    Netlist,
    compare_netlists,
    extract_netlist,
    run_lvs_check,
)

__version__ = "5.0.0"


def run_lvs(circuit: dict, netlist: dict = None) -> dict:
    """对电路执行 LVS 网表比对，返回结果 dict（Input→Process→Output）。

    Input:
        circuit: polaris-core 风格 circuit dict（含 devices/connections）。
        netlist: 提取网表 dict（含 devices/connections），None 时用 circuit
            自身派生的网表（自比对，验证 API 一致性）。

    Process:
        1. 从 circuit 提取参考网表（器件名+类型 + 拓扑连接）
        2. 与提取网表比对: 器件集合差集 + 器件类型一致性 + 连接集合差集
        3. 连接归一化为有序对去重（消除方向差异）

    Output:
        LVS 结果 dict::

            {
                "is_consistent": bool,       # 是否完全一致（无不匹配）
                "n_mismatches": int,         # 不匹配项数
                "mismatches": list[dict],    # 不匹配详情
                "n_devices": int,            # 参考网表器件数
                "n_connections": int,        # 参考网表连接数
            }
        ``is_consistent=True`` 表示版图与原理图拓扑一致，可签核流片。

    Raises:
        RuntimeError: circuit/netlist 结构非法（R03 禁止 fall-back）。
    """
    return run_lvs_check(circuit, netlist)


__all__ = [
    "run_lvs",
    "Netlist",
    "LVSMismatch",
    "LVSMismatchType",
    "extract_netlist",
    "compare_netlists",
    "run_lvs_check",
    "__version__",
]
