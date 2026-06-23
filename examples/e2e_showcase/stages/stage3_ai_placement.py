"""阶段 3: AI 布局。

使用 Edge-GNN + PPO 对电路执行 AI 布局，加载预训练 checkpoint（若存在），
输出布局坐标与 HPWL（半周长线长）指标。

对应路标: R33（Edge-GNN 状态编码）/ R34（预训练 checkpoint 加载）

HPWL 公式来源:
- Kahng & Lienig, "VLSI Placement", IEEE TCAD 2009
  https://ieeexplore.ieee.org/document/4685534
  HPWL = Σ (|x_i - x_j| + |y_i - y_j|) 对所有连接求和，
  其中 (x_i, y_i) 为器件 i 的中心坐标。HPWL 是电子 EDA 标准布局质量指标，
  值越小表示器件间连线越短，布局质量越好。

AlphaChip 预训练范式来源:
- Mirhoseini et al., "Chip Placement with Deep Reinforcement Learning",
  arXiv 2004.10746, 2020, https://arxiv.org/abs/2004.10746
- Mirhoseini et al., Nature 2021, https://www.nature.com/articles/s41586-021-03544-w
"""

from __future__ import annotations

import logging
from pathlib import Path

from polaris.data.specs import CircuitSpec, DeviceSpec
from polaris.pipeline.integrated import IntegratedPipeline, PipelineConfig

_logger = logging.getLogger("e2e_showcase")

# R34 预训练 checkpoint 候选路径（按优先级排序）
# 来源: R34 路标文档 docs/roundmap/R34.md
_CHECKPOINT_CANDIDATES: list[str] = [
    "checkpoints/polaris_r34_pretrain.pt",
    "checkpoints/r34_pretrain.pt",
]

# ASCII 布局预览网格尺寸
_ASCII_GRID_W = 40
_ASCII_GRID_H = 15

# 器件类型 → ASCII 字符映射
# G=grating_coupler, M=mmi, W=waveguide, P=phase_shifter, D=detector
_DEVICE_GLYPH: dict[str, str] = {
    "grating_coupler": "G",
    "mmi_1x2": "M",
    "mmi_2x2": "M",
    "strip_waveguide": "W",
    "phase_shifter": "P",
    "detector": "D",
}


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
            DeviceSpec("wg1", "strip_waveguide", 100, 0.5),
            DeviceSpec("wg2", "strip_waveguide", 120, 0.5),
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


def _load_checkpoint() -> str | None:
    """尝试加载 R34 预训练 checkpoint。

    按候选路径列表依次检查文件是否存在。若找到则返回路径，否则返回 None
    并记录告警日志（学术诚信规则 18：checkpoint 降级时必须明确告警）。

    Returns:
        checkpoint 文件路径，未找到时返回 None。
    """
    for path in _CHECKPOINT_CANDIDATES:
        if Path(path).exists():
            _logger.info("R34 预训练 checkpoint 加载: %s", path)
            return path
    _logger.warning(
        "R34 预训练 checkpoint 未找到 (%s)，降级为随机贪心布局（非 AI 策略）。"
        "HPWL 仅为随机基线，非 AI 布局结果，不能与 AlphaChip 对标。",
        _CHECKPOINT_CANDIDATES,
    )
    return None


def _compute_hpwl(circuit: CircuitSpec, placements: dict) -> float:
    """计算半周长线长 HPWL（Half-Perimeter Wirelength）。

    HPWL = Σ (|x_i - x_j| + |y_i - y_j|) 对所有连接求和，
    其中 (x_i, y_i) 为器件 i 的中心坐标（placement.x + w/2, placement.y + h/2）。

    来源:
    - Kahng & Lienig, "VLSI Placement", IEEE TCAD 2009,
      https://ieeexplore.ieee.org/document/4685534
    - HPWL 是电子 EDA 标准布局质量指标，值越小布局越好。

    Args:
        circuit: 电路规格（含连接列表）。
        placements: 器件布局结果 {name: {x, y, w, h}}。

    Returns:
        HPWL 值（μm）。
    """
    hpwl = 0.0
    for d1, _p1, d2, _p2 in circuit.connections:
        if d1 not in placements or d2 not in placements:
            continue
        p1 = placements[d1]
        p2 = placements[d2]
        x1 = p1["x"] + p1["w"] / 2
        y1 = p1["y"] + p1["h"] / 2
        x2 = p2["x"] + p2["w"] / 2
        y2 = p2["y"] + p2["h"] / 2
        hpwl += abs(x1 - x2) + abs(y1 - y2)
    return hpwl


def _render_ascii_layout(circuit: CircuitSpec, placements: dict) -> str:
    """渲染 ASCII 布局预览。

    将画布坐标映射到 _ASCII_GRID_W × _ASCII_GRID_H 字符网格，
    每个器件用其类型对应的字符表示，空位置用 '.' 表示。

    器件字符映射:
    - G = grating_coupler（光栅耦合器）
    - M = mmi（多模干涉耦合器）
    - W = waveguide（波导）
    - P = phase_shifter（相移器）
    - D = detector（探测器）
    - ? = 未知器件类型

    Args:
        circuit: 电路规格（含画布尺寸）。
        placements: 器件布局结果。

    Returns:
        ASCII 布局预览字符串。
    """
    grid: list[list[str]] = [
        ["." for _ in range(_ASCII_GRID_W)] for _ in range(_ASCII_GRID_H)
    ]

    for dev in circuit.devices:
        if dev.name not in placements:
            continue
        pl = placements[dev.name]
        # 器件中心坐标 → 网格坐标
        cx = pl["x"] + pl["w"] / 2
        cy = pl["y"] + pl["h"] / 2
        gx = int(cx / circuit.canvas_w * _ASCII_GRID_W)
        gy = int(cy / circuit.canvas_h * _ASCII_GRID_H)
        gx = max(0, min(_ASCII_GRID_W - 1, gx))
        gy = max(0, min(_ASCII_GRID_H - 1, gy))
        glyph = _DEVICE_GLYPH.get(dev.device_type, "?")
        grid[gy][gx] = glyph

    lines = ["".join(row) for row in grid]
    legend = "G=grating_coupler  M=mmi  W=waveguide  P=phase_shifter  D=detector"
    return f"{circuit.name} 布局预览 ({circuit.canvas_w}x{circuit.canvas_h} μm):\n" + "\n".join(
        lines
    ) + "\n" + legend


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


def _place_circuit(
    circuit: CircuitSpec,
    checkpoint_path: str | None,
) -> dict:
    """对单个电路执行布局。

    使用 IntegratedPipeline 执行布局（含仿真回馈闭环），
    计算 HPWL 指标并渲染 ASCII 预览。

    Args:
        circuit: 电路规格。
        checkpoint_path: RL checkpoint 路径，None 时用随机贪心布局（非 AI 策略）。

    Returns:
        电路布局结果 dict，含 name/n_devices/placements/hpwl/ascii_layout。
    """
    config = PipelineConfig(
        canvas_w=circuit.canvas_w,
        canvas_h=circuit.canvas_h,
        placement_checkpoint=checkpoint_path,
    )
    pipeline = IntegratedPipeline(config=config)
    result = pipeline.run(circuit)

    if not result.placements:
        raise RuntimeError(
            f"电路 {circuit.name} 布局失败：placements 为空"
        )

    hpwl = _compute_hpwl(circuit, result.placements)
    ascii_layout = _render_ascii_layout(circuit, result.placements)

    _logger.info(
        "电路 %s: %d 器件, HPWL=%.2f μm",
        circuit.name,
        result.n_devices,
        hpwl,
    )
    _logger.info("ASCII 布局预览:\n%s", ascii_layout)

    return {
        "name": circuit.name,
        "n_devices": result.n_devices,
        "placements": result.placements,
        "hpwl": round(hpwl, 2),
        "ascii_layout": ascii_layout,
    }


def run(output_dir: Path) -> dict:
    """执行阶段 3: AI 布局。

    流程:
    1. 尝试加载 R34 预训练 checkpoint（若不存在则降级为随机贪心布局并告警）
    2. 构造 3 个演示电路（MZI、Clements 4x4、量子占位）
    3. 对每个电路执行布局，计算 HPWL 指标
    4. 输出 ASCII 布局预览
    5. 返回布局结果摘要

    学术诚信说明:
        - checkpoint 不存在时，IntegratedPipeline 内部调用 _place_random
          （随机贪心布局，固定种子 42），此时 HPWL 仅为随机基线，
          非 Edge-GNN+PPO 的 AI 布局结果，不能与 AlphaChip 对标。
        - placement_mode 如实标注为 "random_greedy"，ai_layout_executed=False。

    Args:
        output_dir: 输出目录。

    Returns:
        阶段执行结果，含:
        - circuits: 3 电路布局结果列表
        - checkpoint_loaded: checkpoint 是否加载成功
        - placement_mode: 布局模式（"rl" 或 "random_greedy"）
        - ai_layout_executed: 是否真正执行了 AI 布局（checkpoint 加载成功才为 True）
        - baseline_type: 基线类型（"rl" 或 "random_greedy"）
        - warning: 降级告警信息（checkpoint 未加载时非 None）
    """
    _logger.info("阶段 3 开始: AI 布局")
    output_dir.mkdir(parents=True, exist_ok=True)

    checkpoint_path = _load_checkpoint()
    checkpoint_loaded = checkpoint_path is not None
    placement_mode = "rl" if checkpoint_loaded else "random_greedy"
    _logger.info(
        "布局模式: %s (checkpoint_loaded=%s)",
        placement_mode,
        checkpoint_loaded,
    )

    circuits = _build_circuits()
    results = [
        _place_circuit(circuit, checkpoint_path) for circuit in circuits
    ]

    _logger.info(
        "阶段 3 完成: %d 电路布局完成, 模式=%s",
        len(results),
        placement_mode,
    )

    return {
        "circuits": results,
        "checkpoint_loaded": checkpoint_loaded,
        "placement_mode": placement_mode,
        "ai_layout_executed": checkpoint_loaded,
        "baseline_type": placement_mode,
        "warning": (
            "HPWL 来自随机贪心布局，非 AI 结果，不能与 AlphaChip 对标"
            if not checkpoint_loaded
            else None
        ),
    }
