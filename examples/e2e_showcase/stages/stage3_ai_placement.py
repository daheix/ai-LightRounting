"""阶段 3: AI 布局。

使用 PoLaRIS v5.0 polaris-place 子模块对电路执行布局，
输出布局坐标与 HPWL（半周长线长）指标。

对应路标: R33（Edge-GNN 状态编码）/ R34（预训练 checkpoint 加载）/ R3（Edge-GNN 前向推理集成）

PoLaRIS v5.0 迁移说明:
    旧 v4 在本 stage 自实现 PPO ActorCritic + Edge-GNN 前向推理（~900 行）。
    v5.0 已将布局能力封装为 polaris-place 子模块的稳定 API ``place_circuit``，
    支持 ``"analytical"``（DREAMPlace 风格解析法布局，默认稳定）与
    ``"ppo_gnn"``（AlphaChip Edge-GNN + PPO，需预训练 checkpoint）两种模式。
    本 stage 改用 ``place_circuit`` 子模块 API，删除全部自实现 PPO/GNN 代码。

HPWL 公式来源:
- Kahng & Lienig, "VLSI Placement", IEEE TCAD 2009
  https://ieeexplore.ieee.org/document/4685534
  HPWL = Σ (|x_i - x_j| + |y_i - y_j|) 对所有连接求和，
  其中 (x_i, y_i) 为器件 i 的中心坐标。HPWL 是电子 EDA 标准布局质量指标，
  值越小表示器件间连线越短，布局质量越好。

布局算法来源:
- DREAMPlace DAC 2019: https://cseweb.ucsd.edu/classes/fa23/cse248-a/papers/placement/dreamplace.pdf
- DREAMPlace TCAD 2020: https://arxiv.org/abs/2004.10746
- AlphaChip: Mirhoseini et al., Nature 2021
  https://www.nature.com/articles/s41586-021-03544-w
- TILOS MacroPlacement: https://github.com/TILOS-AI-Institute/MacroPlacement
"""

from __future__ import annotations

import logging
from pathlib import Path

from polaris_core import CircuitSpec, DeviceSpec, circuit_to_dict
from polaris_place import place_circuit, render_ascii_layout

_logger = logging.getLogger("e2e_showcase")

# ASCII 布局预览网格尺寸
_ASCII_GRID_W = 40
_ASCII_GRID_H = 15


def _mzi_circuit() -> CircuitSpec:
    """构造 MZI 干涉仪电路规格。

    5 器件：1 光栅耦合器 + 2 MMI + 2 波导臂，构成马赫-曾德干涉仪。

    Returns:
        MZI 电路规格。
    """
    return CircuitSpec(
        name="MZI",
        canvas_w=500,
        canvas_h=300,
        devices=[
            DeviceSpec("gc1", "grating_coupler", 10, 10),
            DeviceSpec("mmi1", "mmi_1x2", 20, 10),
            DeviceSpec(
                "wg1", "strip_waveguide", 100, 0.5,
                params={"length": 100.0},
            ),
            DeviceSpec(
                "wg2", "strip_waveguide", 120, 0.5,
                params={"length": 120.0},
            ),
            DeviceSpec("mmi2", "mmi_2x2", 20, 10),
        ],
        connections=[
            ("gc1", "out", "mmi1", "in"),
            ("mmi1", "out0", "wg1", "in"),
            ("mmi1", "out1", "wg2", "in"),
            ("wg1", "out", "mmi2", "in0"),
            ("wg2", "out", "mmi2", "in1"),
        ],
    )


def _clements_4x4_circuit() -> CircuitSpec:
    """构造 Clements 4x4 光矩阵电路规格。

    6 分束器 + 4 相移器，构成 Clements 三角形拓扑（简化版）。

    来源:
    - Clements et al., "Optimal design for universal multiport interferometers",
      Optica 2016, https://doi.org/10.1364/OPTICA.3.001460

    Returns:
        Clements 4x4 电路规格。
    """
    devices: list[DeviceSpec] = []
    for i in range(6):
        devices.append(DeviceSpec(f"bs{i + 1}", "mmi_2x2", 20, 10))
    for i in range(4):
        devices.append(DeviceSpec(f"ps{i + 1}", "phase_shifter", 10, 5))
    connections = [
        ("bs1", "out0", "ps1", "in"),
        ("ps1", "out", "bs3", "in0"),
        ("bs1", "out1", "bs2", "in0"),
        ("bs2", "out0", "ps2", "in"),
        ("ps2", "out", "bs4", "in0"),
        ("bs3", "out1", "bs4", "in1"),
        ("bs4", "out0", "ps3", "in"),
        ("bs2", "out1", "bs5", "in0"),
        ("bs3", "out0", "bs5", "in1"),
        ("bs5", "out0", "ps4", "in"),
    ]
    return CircuitSpec(
        name="Clements4x4",
        canvas_w=800,
        canvas_h=600,
        devices=devices,
        connections=connections,
    )


def _quantum_placeholder_circuit() -> CircuitSpec:
    """构造量子玻色采样占位电路规格。

    4 器件占位（实际量子电路在 stage9 处理）：
    2 光栅耦合器（光源）+ 1 分束器 + 1 探测器。

    Returns:
        量子玻色采样占位电路规格。
    """
    return CircuitSpec(
        name="QuantumBosonSampling",
        canvas_w=400,
        canvas_h=300,
        devices=[
            DeviceSpec("src1", "grating_coupler", 10, 10),
            DeviceSpec("src2", "grating_coupler", 10, 10),
            DeviceSpec("bs1", "mmi_2x2", 20, 10),
            DeviceSpec("det1", "detector", 10, 10),
        ],
        connections=[
            ("src1", "out", "bs1", "in0"),
            ("src2", "out", "bs1", "in1"),
            ("bs1", "out0", "det1", "in"),
        ],
    )


def _build_circuits() -> list[CircuitSpec]:
    """构造 3 个演示电路规格。

    Returns:
        电路规格列表（MZI、Clements 4x4、量子占位）。
    """
    return [
        _mzi_circuit(),
        _clements_4x4_circuit(),
        _quantum_placeholder_circuit(),
    ]


def _place_one_circuit(circuit: CircuitSpec) -> dict:
    """对单个电路执行布局（调用 polaris-place 子模块 API）。

    使用 ``place_circuit`` 解析法布局（DREAMPlace 风格：log-sum-exp 平滑
    HPWL + 密度惩罚 + Adam + FFDH 合法化），计算 HPWL 指标并渲染 ASCII 预览。

    来源:
    - DREAMPlace DAC 2019
      https://cseweb.ucsd.edu/classes/fa23/cse248-a/papers/placement/dreamplace.pdf
    - Kahng & Lienig, IEEE TCAD 2009
      https://ieeexplore.ieee.org/document/4685534

    Args:
        circuit: 电路规格（CircuitSpec，内部转为 dict 供子模块使用）。

    Returns:
        电路布局结果 dict，含 name/n_devices/placements/hpwl/ascii_layout/
        placement_mode/checkpoint_loaded。

    Raises:
        RuntimeError: 布局失败（R03 禁止 fall-back）。
    """
    circuit_dict = circuit_to_dict(circuit)
    result = place_circuit(circuit_dict, mode="analytical")
    placements = result["placements"]
    if not placements:
        raise RuntimeError(
            f"电路 {circuit.name} 布局失败：placements 为空"
        )

    hpwl = result["hpwl"]
    ascii_layout = render_ascii_layout(
        circuit_dict, placements, grid_w=_ASCII_GRID_W, grid_h=_ASCII_GRID_H
    )

    _logger.info(
        "电路 %s: %d 器件, HPWL=%.2f μm, 模式=%s",
        circuit.name,
        len(placements),
        hpwl,
        result["placement_mode"],
    )
    _logger.info("ASCII 布局预览:\n%s", ascii_layout)

    return {
        "name": circuit.name,
        "n_devices": len(placements),
        "placements": placements,
        "hpwl": round(hpwl, 2),
        "ascii_layout": ascii_layout,
        "placement_mode": result["placement_mode"],
        "checkpoint_loaded": result["checkpoint_loaded"],
    }


def run(output_dir: Path) -> dict:
    """执行阶段 3: AI 布局。

    流程:
    1. 构造 3 个演示电路（MZI、Clements 4x4、量子占位）
    2. 对每个电路调用 polaris-place ``place_circuit``（DREAMPlace 风格解析法布局）
    3. 计算 HPWL 指标，输出 ASCII 布局预览
    4. 返回布局结果摘要

    学术诚信说明:
        - 布局模式为 ``"analytical"``（DREAMPlace 风格解析法布局，稳定可用）。
        - ``"ppo_gnn"``（AlphaChip Edge-GNN + PPO）需预训练 checkpoint，
          showcase 默认不依赖 checkpoint，使用解析法保证可复现。
        - HPWL 为解析法布局结果，可与 DREAMPlace 公开 benchmark 对标。

    来源:
    - DREAMPlace DAC 2019
      https://cseweb.ucsd.edu/classes/fa23/cse248-a/papers/placement/dreamplace.pdf
    - DREAMPlace TCAD 2020: https://arxiv.org/abs/2004.10746
    - Kahng & Lienig, IEEE TCAD 2009
      https://ieeexplore.ieee.org/document/4685534
    - AlphaChip: Mirhoseini et al., Nature 2021
      https://www.nature.com/articles/s41586-021-03544-w
    - TILOS MacroPlacement: https://github.com/TILOS-AI-Institute/MacroPlacement

    Args:
        output_dir: 输出目录。

    Returns:
        阶段执行结果，含:
        - circuits: 3 电路布局结果列表
        - placement_mode: 布局模式（"analytical"）
        - ai_layout_executed: 是否真正执行了布局（始终为 True）
        - baseline_type: 基线类型
    """
    _logger.info("阶段 3 开始: AI 布局（polaris-place 解析法布局）")
    output_dir.mkdir(parents=True, exist_ok=True)

    circuits = _build_circuits()
    results = [_place_one_circuit(circuit) for circuit in circuits]

    placement_mode = "analytical"
    _logger.info(
        "阶段 3 完成: %d 电路布局完成, 模式=%s",
        len(results),
        placement_mode,
    )

    return {
        "circuits": results,
        "placement_mode": placement_mode,
        "ai_layout_executed": True,
        "baseline_type": placement_mode,
    }
