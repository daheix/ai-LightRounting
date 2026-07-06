"""PoLaRIS AI 布局子模块（polaris-place）。

提供稳定的 Python API（place_circuit/compute_hpwl/render_ascii_layout），
支持两种布局模式:

- ``"analytical"``: DREAMPlace 风格解析法布局（log-sum-exp 平滑 HPWL +
  密度惩罚 + Adam + FFDH 合法化），稳定可用，默认模式。
- ``"ppo_gnn"``: AlphaChip Edge-GNN + PPO ActorCritic AI 布局，
  需预训练 checkpoint，无 checkpoint 时 raise（R03 禁止 fall-back）。

## 模块拆分（R11 质量门禁：单文件 ≤800 行）

``analytical.py`` 原 1480 行已按功能拆分为 5 个文件:
- ``analytical.py``: 主入口（FFDH 调度 + AnalyticalConfig + Adam 优化器）
- ``metrics.py``: HPWL/密度梯度/Tarjan SCC/拓扑深度
- ``legalize.py``: FFDH 合法化 + 1D 最近合法位置搜索 + 共享常量
- ``align.py``: 端口对齐后处理（_align_d2_global + _align_ports）
- ``residual.py``: 残余违规成对双向修复（_residual_pair_fix 已拆子函数）

向后兼容: ``from polaris_place.analytical import X`` 仍可用（analytical.py
re-export 所有内部函数），新代码推荐 ``from polaris_place.metrics import X``
直接从子模块导入。

设计原则:
- 对外 API 返回 JSON-serializable dict（与 polaris-core 一致）
- 纯 NumPy 实现（R04: 不参与 GPU）
- 禁止 fall-back（R03）: ppo_gnn 无 checkpoint raise，不返回未训练结果
- 输出坐标约定: ``{name: {x, y, w, h}}``，``x, y`` 为器件**左下角**坐标 (μm)
  （与 modules/_c_abi/polaris_types.h 中 polaris_placement_t 一致）

来源（R02 学术诚信）:
- DREAMPlace DAC 2019: https://cseweb.ucsd.edu/classes/fa23/cse248-a/papers/placement/dreamplace.pdf
- DREAMPlace TCAD 2020: https://arxiv.org/abs/2004.10746
- AlphaChip: Mirhoseini et al., Nature 2021
  https://www.nature.com/articles/s41586-021-03544-w
- HPWL 指标: Kahng & Lienig IEEE TCAD 2009
  https://ieeexplore.ieee.org/document/4685534
- GDSFactory 组件库: https://gdsfactory.github.io/gdsfactory/
- TILOS MacroPlacement: https://github.com/TILOS-AI-Institute/MacroPlacement
"""

from __future__ import annotations

# 显式导入子模块，使其成为 polaris_place 包属性
# （polaris_place.metrics / polaris_place.align 等可直接访问）
from polaris_place import align, legalize, metrics, residual  # noqa: F401
from polaris_place.analytical import AnalyticalConfig, place_analytical
from polaris_place.ppo_gnn import place_ppo_gnn

__version__ = "5.1.0"

# 器件类型 → ASCII 字符映射（G=grating_coupler, M=mmi, W=waveguide, P=phase_shifter, D=detector）
_DEVICE_GLYPH: dict[str, str] = {
    "grating_coupler": "G",
    "mmi_1x2": "M",
    "mmi_2x2": "M",
    "strip_waveguide": "W",
    "phase_shifter": "P",
    "detector": "D",
}


def _validate_circuit(circuit: dict) -> None:
    """校验 circuit dict 结构完整性（R03: 失败 raise）。

    Args:
        circuit: 待校验 circuit dict。

    Raises:
        RuntimeError: circuit 非 dict / 缺必要字段 / 画布尺寸非正。
    """
    if not isinstance(circuit, dict):
        raise RuntimeError(
            f"circuit 必须是 dict，得到 {type(circuit).__name__}"
        )
    for key in ("name", "devices", "connections", "canvas_w", "canvas_h"):
        if key not in circuit:
            raise RuntimeError(f"circuit 缺少必要字段: {key}")
    if circuit["canvas_w"] <= 0 or circuit["canvas_h"] <= 0:
        raise RuntimeError(
            f"画布尺寸必须为正: canvas_w={circuit['canvas_w']}, "
            f"canvas_h={circuit['canvas_h']}（R03 禁止 fall-back）"
        )


def place_circuit(circuit: dict, mode: str = "analytical") -> dict:
    """对电路执行布局，返回布局结果 dict。

    Args:
        circuit: polaris-core 风格 circuit dict（含 name/devices/connections/
            canvas_w/canvas_h）。
        mode: 布局模式:
            - ``"analytical"``: 解析法布局（默认，稳定可用）
            - ``"ppo_gnn"``: AlphaChip Edge-GNN + PPO AI 布局（需 checkpoint）

    Returns:
        布局结果 dict::

            {
                "placements": {name: {"x":, "y":, "w":, "h":}},  # 左下角坐标
                "hpwl": float,           # 半周长线长 (μm)
                "placement_mode": str,   # "analytical" 或 "ppo_gnn"
                "checkpoint_loaded": bool,
            }

    Raises:
        RuntimeError: mode 非法 / circuit 结构非法 / ppo_gnn 无 checkpoint
            或 checkpoint 损坏（R03 禁止 fall-back）。
    """
    _validate_circuit(circuit)

    if mode == "analytical":
        placements = place_analytical(circuit)
        checkpoint_loaded = False
        placement_mode = "analytical"
    elif mode == "ppo_gnn":
        # R03: 无 checkpoint 即 raise（place_ppo_gnn 内部处理）
        placements, checkpoint_loaded = place_ppo_gnn(circuit)
        placement_mode = "ppo_gnn"
    else:
        raise RuntimeError(
            f"不支持的布局模式: {mode}（可选: 'analytical' / 'ppo_gnn'）"
        )

    hpwl = compute_hpwl(circuit, placements)
    return {
        "placements": placements,
        "hpwl": float(hpwl),
        "placement_mode": placement_mode,
        "checkpoint_loaded": bool(checkpoint_loaded),
    }


def compute_hpwl(circuit: dict, placements: dict) -> float:
    """计算半周长线长 HPWL（Half-Perimeter Wirelength）。

    HPWL = Σ (|x_i - x_j| + |y_i - y_j|) 对所有连接求和，
    其中 (x_i, y_i) 为器件 i 的**中心**坐标
    (placement.x + w/2, placement.y + h/2)。

    来源: Kahng & Lienig "VLSI Placement" IEEE TCAD 2009,
      https://ieeexplore.ieee.org/document/4685534
    HPWL 是电子 EDA 标准布局质量指标，值越小布局越好。

    Args:
        circuit: polaris-core 风格 circuit dict（含 connections）。
        placements: 器件布局结果 {name: {x, y, w, h}}。

    Returns:
        HPWL 值 (μm)。
    """
    hpwl = 0.0
    for conn in circuit.get("connections", []):
        d1, _p1, d2, _p2 = conn
        if d1 not in placements or d2 not in placements:
            continue
        p1 = placements[d1]
        p2 = placements[d2]
        x1 = p1["x"] + p1["w"] / 2.0
        y1 = p1["y"] + p1["h"] / 2.0
        x2 = p2["x"] + p2["w"] / 2.0
        y2 = p2["y"] + p2["h"] / 2.0
        hpwl += abs(x1 - x2) + abs(y1 - y2)
    return float(hpwl)


def render_ascii_layout(
    circuit: dict,
    placements: dict,
    grid_w: int = 40,
    grid_h: int = 15,
) -> str:
    """渲染 ASCII 布局预览。

    将画布坐标映射到 ``grid_w × grid_h`` 字符网格，每个器件用其类型对应的
    字符表示，空位置用 ``.`` 表示。

    器件字符映射: G=grating_coupler, M=mmi, W=waveguide, P=phase_shifter,
    D=detector, ?=未知类型。

    Args:
        circuit: polaris-core 风格 circuit dict（含画布尺寸与 devices）。
        placements: 器件布局结果 {name: {x, y, w, h}}。
        grid_w: 网格宽度（字符数，默认 40）。
        grid_h: 网格高度（字符数，默认 15）。

    Returns:
        ASCII 布局预览字符串（含标题与图例）。

    Raises:
        RuntimeError: 画布尺寸非正（R03 禁止 fall-back）。
    """
    canvas_w = float(circuit["canvas_w"])
    canvas_h = float(circuit["canvas_h"])
    if canvas_w <= 0 or canvas_h <= 0:
        raise RuntimeError(
            f"画布尺寸必须为正: canvas_w={canvas_w}, canvas_h={canvas_h}"
            f"（R03 禁止 fall-back）"
        )
    grid: list[list[str]] = [
        ["." for _ in range(grid_w)] for _ in range(grid_h)
    ]
    for dev in circuit.get("devices", []):
        name = dev["name"]
        if name not in placements:
            continue
        pl = placements[name]
        cx = pl["x"] + pl["w"] / 2.0
        cy = pl["y"] + pl["h"] / 2.0
        gx = int(cx / canvas_w * grid_w)
        gy = int(cy / canvas_h * grid_h)
        gx = max(0, min(grid_w - 1, gx))
        gy = max(0, min(grid_h - 1, gy))
        glyph = _DEVICE_GLYPH.get(dev["device_type"], "?")
        grid[gy][gx] = glyph
    lines = ["".join(row) for row in grid]
    legend = "G=grating_coupler  M=mmi  W=waveguide  P=phase_shifter  D=detector"
    return (
        f"{circuit['name']} 布局预览 ({canvas_w}x{canvas_h} μm):\n"
        + "\n".join(lines)
        + "\n" + legend
    )


__all__ = [
    "place_circuit",
    "compute_hpwl",
    "render_ascii_layout",
    "AnalyticalConfig",
    "place_analytical",
    "place_ppo_gnn",
    "__version__",
]
