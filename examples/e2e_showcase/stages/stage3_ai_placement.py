"""阶段 3: AI 布局。

使用 Edge-GNN + PPO 对电路执行 AI 布局，加载预训练 checkpoint（若存在），
输出布局坐标与 HPWL（半周长线长）指标。

对应路标: R33（Edge-GNN 状态编码）/ R34（预训练 checkpoint 加载）/ R3（Edge-GNN 前向推理集成）

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

R3 Edge-GNN 集成来源:
- AlphaChip Edge-GNN: Mirhoseini et al., Nature 2021
  边特征消息传递 + GAT 注意力 + GlobalAttention 读出
- polaris.nn.Tensor: 纯 NumPy 自动微分（复刻 PyTorch Tensor 子集）
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import torch

from polaris.data.specs import CircuitSpec, DeviceSpec
from polaris.engine.alphachip_gnn import AlphaChipEdgeGNN, PHOTONIC_EDGE_DIM
from polaris.nn import Tensor
from polaris.trainer.ppo_networks import ActorCritic

_logger = logging.getLogger("e2e_showcase")

# R34 预训练 checkpoint 候选路径（按优先级排序）
# 来源: R34 路标文档 docs/roundmap/R34.md
# 真实预训练 checkpoint（200 万步训练产物，rl_2m 目录）
_CHECKPOINT_CANDIDATES: list[str] = [
    "checkpoints/polaris_r34_pretrain.pt",
    "checkpoints/r34_pretrain.pt",
    "checkpoints/rl_2m/placement_agent.json",
    "checkpoints/rl_place_200/floorplan_final.json",
]

# PPO 策略网络观测维度（电路特征编码）
# 来源: Mirhoseini et al., Nature 2021 (AlphaChip) 状态编码
_OBS_DIM = 8

# R3: Edge-GNN 输出维度（图级嵌入）
# 来源: AlphaChip Edge-GNN GlobalAttention 读出（Mirhoseini et al., Nature 2021）
_GNN_OUT_DIM = 16

# R3: Edge-GNN 隐藏层维度
_GNN_HIDDEN_DIM = 32

# R3: Edge-GNN 消息传递层数
_GNN_NUM_LAYERS = 2

# R3: GNN 节点特征维度（简化版: width_norm, height_norm, type_hash, idx_norm）
_GNN_NODE_FEAT_DIM = 4

# PPO 策略网络动作维度（归一化坐标 x, y）
_ACTION_DIM = 2

# PPO 网络隐藏层维度
_HIDDEN_DIM = 64

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
            _logger.info("R34 预训练 checkpoint 候选: %s", path)
            return path
    _logger.warning(
        "R34 预训练 checkpoint 未找到 (%s)，将使用 Orthogonal 初始化 PPO 网络做前向推理。"
        "HPWL 为未训练网络的布局结果，非预训练模型，不能与 AlphaChip 对标，"
        "但确为 PPO 策略网络前向推理（非纯随机贪心）。",
        _CHECKPOINT_CANDIDATES,
    )
    return None


def _test_checkpoint_loadable(checkpoint_path: str | None) -> bool:
    """测试 checkpoint 权重能否真正加载到 ActorCritic 网络。

    学术诚信规则 18：checkpoint 文件存在不等于权重可加载。
    需实际尝试加载，避免"文件存在但 size mismatch"时误导为预训练模式。

    Args:
        checkpoint_path: checkpoint 路径。

    Returns:
        权重是否真正加载成功。
    """
    if checkpoint_path is None:
        return False
    try:
        agent = ActorCritic(
            obs_dim=_OBS_DIM,
            action_dim=_ACTION_DIM,
            hidden_dim=_HIDDEN_DIM,
        )
        data = torch.load(checkpoint_path, weights_only=False)
        if isinstance(data, dict) and "network" in data:
            agent.load_state_dict(data["network"])
            return True
    except Exception as exc:
        _logger.warning(
            "PPO checkpoint 权重加载测试失败 (%s): %s，"
            "将使用 Orthogonal 初始化网络",
            checkpoint_path,
            exc,
        )
    return False


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


def _encode_circuit_obs(
    circuit: CircuitSpec,
    dev: DeviceSpec,
    idx: int,
    n_dev: int,
) -> np.ndarray:
    """将电路器件特征编码为 PPO 观测向量。

    观测向量维度 = _OBS_DIM = 8，特征如下：
    - [0] 器件索引归一化 idx/(n_dev-1)
    - [1] 器件宽度归一化 dev.width_um/canvas_w
    - [2] 器件高度归一化 dev.height_um/canvas_h
    - [3] 器件总数归一化 n_dev/20
    - [4] 连接数归一化 len(connections)/20
    - [5] 画布宽度归一化 canvas_w/1000
    - [6] 画布高度归一化 canvas_h/1000
    - [7] 器件类型哈希归一化（区分 grating_coupler/mmi/waveguide 等）

    来源: Mirhoseini et al., Nature 2021 (AlphaChip) 状态编码
      https://www.nature.com/articles/s41586-021-03544-w
      AlphaChip 使用 netlist + node features 编码电路状态，
      本实现简化为器件级特征向量（适用于 showcase 演示）。

    Args:
        circuit: 电路规格。
        dev: 当前器件规格。
        idx: 当前器件索引。
        n_dev: 器件总数。

    Returns:
        归一化观测向量 (8,)。
    """
    type_hash = hash(dev.device_type) % 100 / 100.0
    obs = np.array(
        [
            idx / max(n_dev - 1, 1),
            dev.width_um / max(circuit.canvas_w, 1.0),
            dev.height_um / max(circuit.canvas_h, 1.0),
            n_dev / 20.0,
            len(circuit.connections) / 20.0,
            circuit.canvas_w / 1000.0,
            circuit.canvas_h / 1000.0,
            type_hash,
        ],
        dtype=np.float32,
    )
    return obs


def _build_edge_index_from_circuit(
    circuit: CircuitSpec,
    instance_ids: list[str],
) -> np.ndarray:
    """从电路连接构建 GNN 边索引（双向边）。

    将 CircuitSpec.connections 转换为 [2, E] 边索引数组，
    每条连接生成双向边（src→dst 和 dst→src）。

    来源: AlphaChip netlist graph construction
      Mirhoseini et al., Nature 2021

    Args:
        circuit: 电路规格（含连接列表）。
        instance_ids: 器件名称列表（与节点索引对应）。

    Returns:
        边索引数组 [2, E]（每列为 (src_idx, dst_idx)）。
    """
    id_to_idx = {name: i for i, name in enumerate(instance_ids)}
    edges: list[tuple[int, int]] = []
    for d1, _p1, d2, _p2 in circuit.connections:
        if d1 in id_to_idx and d2 in id_to_idx:
            src, dst = id_to_idx[d1], id_to_idx[d2]
            edges.append((src, dst))
            edges.append((dst, src))  # 双向边
    if not edges:
        return np.zeros((2, 0), dtype=np.int64)
    return np.array(edges, dtype=np.int64).T  # [2, E]


def _build_gnn_node_features(
    circuit: CircuitSpec,
    instance_ids: list[str],
) -> np.ndarray:
    """构建 GNN 节点特征矩阵（简化版 4 维）。

    节点特征:
    - [0] 器件宽度归一化 width_um/canvas_w
    - [1] 器件高度归一化 height_um/canvas_h
    - [2] 器件类型哈希归一化（区分 grating_coupler/mmi/waveguide 等）
    - [3] 器件索引归一化 idx/(n_dev-1)

    来源: AlphaChip node features
      Mirhoseini et al., Nature 2021
      简化为器件级几何+类型特征（适用于 showcase 演示）

    Args:
        circuit: 电路规格。
        instance_ids: 器件名称列表。

    Returns:
        节点特征矩阵 [N, 4]。
    """
    n_dev = len(instance_ids)
    feats = np.zeros((n_dev, _GNN_NODE_FEAT_DIM), dtype=np.float64)
    dev_map = {d.name: d for d in circuit.devices}
    for i, name in enumerate(instance_ids):
        dev = dev_map.get(name)
        if dev is not None:
            feats[i, 0] = dev.width_um / max(circuit.canvas_w, 1.0)
            feats[i, 1] = dev.height_um / max(circuit.canvas_h, 1.0)
            feats[i, 2] = hash(dev.device_type) % 100 / 100.0
            feats[i, 3] = i / max(n_dev - 1, 1)
    return feats


def _build_gnn_edge_features(
    circuit: CircuitSpec,
    instance_ids: list[str],
    edge_index: np.ndarray,
    placements: dict | None = None,
) -> np.ndarray:
    """构建 GNN 边特征矩阵（15 维，与 PHOTONIC_EDGE_DIM 对齐）。

    边特征维度（15 维，简化版）:
    - [0] 距离（曼哈顿，μm，若已放置）
    - [1] 带宽需求（端口数代理，默认 1.0）
    - [2] 优先级（默认 1.0）
    - [3-6] 类型 one-hot(4): passive-passive
    - [7-9] 波段 one-hot(3): C-band
    - [10] 折射率差（默认 0.5）
    - [11] 波导损耗（默认 0.3）
    - [12] 串扰系数（默认 0.1）
    - [13] 弯曲半径约束（默认 0.5）
    - [14] net 关系类型（0=光波导）

    来源: AlphaChip edge features + 光电子扩展
      Mirhoseini et al., Nature 2021;
      PHOTONIC_EDGE_DIM 定义于 polaris.engine.alphachip_gnn

    Args:
        circuit: 电路规格。
        instance_ids: 器件名称列表。
        edge_index: 边索引 [2, E]。
        placements: 当前布局（用于距离计算，可选）。

    Returns:
        边特征矩阵 [E, 15]。
    """
    n_edges = edge_index.shape[1]
    feats = np.zeros((n_edges, PHOTONIC_EDGE_DIM), dtype=np.float64)
    for i in range(n_edges):
        src_idx = edge_index[0, i]
        dst_idx = edge_index[1, i]
        src_id = instance_ids[src_idx]
        dst_id = instance_ids[dst_idx]
        # [0] 距离（若已放置）
        if placements and src_id in placements and dst_id in placements:
            p1 = placements[src_id]
            p2 = placements[dst_id]
            x1, y1 = p1["x"] + p1["w"] / 2, p1["y"] + p1["h"] / 2
            x2, y2 = p2["x"] + p2["w"] / 2, p2["y"] + p2["h"] / 2
            feats[i, 0] = abs(x1 - x2) + abs(y1 - y2)
        # [1] 带宽需求
        feats[i, 1] = 1.0
        # [2] 优先级
        feats[i, 2] = 1.0
        # [3-6] 类型 one-hot: passive-passive
        feats[i, 3] = 1.0
        # [7-9] 波段 one-hot: C-band
        feats[i, 7] = 1.0
        # [10] 折射率差
        feats[i, 10] = 0.5
        # [11] 波导损耗
        feats[i, 11] = 0.3
        # [12] 串扰
        feats[i, 12] = 0.1
        # [13] 弯曲半径
        feats[i, 13] = 0.5
        # [14] net 关系类型: 0=光波导
        feats[i, 14] = 0.0
    return feats


def _place_with_ppo_policy(
    circuit: CircuitSpec,
    checkpoint_path: str | None,
) -> dict:
    """使用 PPO ActorCritic 策略网络执行 AI 布局。

    真正调用 PPO 网络前向推理（非纯随机贪心）：
    1. 实例化 ActorCritic 网络（Orthogonal 初始化）
    2. 若 checkpoint 存在且可加载，加载预训练权重
    3. 对每个器件编码观测向量，调用 get_action() 采样归一化坐标
    4. sigmoid 压缩到 [0,1]，映射到画布坐标
    5. 检查重叠，若重叠则贪心错开

    来源:
    - Mirhoseini et al., Nature 2021 (AlphaChip)
      https://www.nature.com/articles/s41586-021-03544-w
    - Engstrom et al., 2020, Implementation Matters in PPO
      https://arxiv.org/abs/2005.12729
    - SB3 ActorCriticPolicy: https://stable-baselines3.readthedocs.io/

    Args:
        circuit: 电路规格。
        checkpoint_path: checkpoint 路径，None 或加载失败时用初始化网络。

    Returns:
        布局结果 {name: {x, y, w, h}}。
    """
    # 实例化 PPO ActorCritic 网络（Orthogonal 初始化）
    agent = ActorCritic(
        obs_dim=_OBS_DIM,
        action_dim=_ACTION_DIM,
        hidden_dim=_HIDDEN_DIM,
    )
    agent.eval()

    weights_loaded = False
    if checkpoint_path is not None:
        try:
            data = torch.load(checkpoint_path, weights_only=False)
            if isinstance(data, dict) and "network" in data:
                agent.load_state_dict(data["network"])
                weights_loaded = True
                _logger.info(
                    "PPO checkpoint 权重加载成功: %s", checkpoint_path
                )
        except Exception as exc:
            _logger.warning(
                "PPO checkpoint 加载失败 (%s): %s，使用 Orthogonal 初始化网络",
                checkpoint_path,
                exc,
            )

    if not weights_loaded:
        _logger.info(
            "使用 Orthogonal 初始化 PPO 网络做前向推理（非预训练，非纯随机贪心）"
        )

    placements: dict[str, dict[str, float]] = {}
    n_dev = len(circuit.devices)
    occupied: list[tuple[float, float, float, float]] = []  # (x, y, w, h)

    for idx, dev in enumerate(circuit.devices):
        obs = _encode_circuit_obs(circuit, dev, idx, n_dev)
        # PPO 网络前向推理，采样动作（归一化坐标偏移）
        action, _logprob, _value = agent.get_action(obs)
        # sigmoid 压缩到 [0, 1]，映射到画布坐标
        coord = 1.0 / (1.0 + np.exp(-action))
        x = float(coord[0]) * (circuit.canvas_w - dev.width_um)
        y = float(coord[1]) * (circuit.canvas_h - dev.height_um)

        # 重叠检测：若与已放置器件重叠，贪心错开
        x, y = _resolve_overlap(
            x, y, dev.width_um, dev.height_um, occupied, circuit
        )

        placements[dev.name] = {
            "x": x,
            "y": y,
            "w": dev.width_um,
            "h": dev.height_um,
        }
        occupied.append((x, y, dev.width_um, dev.height_um))

    return placements


def _resolve_overlap(
    x: float,
    y: float,
    w: float,
    h: float,
    occupied: list[tuple[float, float, float, float]],
    circuit: CircuitSpec,
) -> tuple[float, float]:
    """贪心重叠消解：若与已放置器件重叠，沿网格步进错开。

    来源: 经典 VLSI 布局重叠消解（Kahng & Lienig 2009）
      https://ieeexplore.ieee.org/document/4685534

    Args:
        x: 候选 x 坐标。
        y: 候选 y 坐标。
        w: 器件宽度。
        h: 器件高度。
        occupied: 已放置器件列表 (x, y, w, h)。
        circuit: 电路规格（画布边界）。

    Returns:
        调整后的 (x, y) 坐标。
    """
    step = 5.0  # 错开步长（μm）
    max_tries = 200
    for _try in range(max_tries):
        overlap = False
        for ox, oy, ow, oh in occupied:
            if not (x + w <= ox or ox + ow <= x or y + h <= oy or oy + oh <= y):
                overlap = True
                break
        if not overlap:
            return x, y
        # 沿螺旋方向错开
        x += step
        if x + w > circuit.canvas_w:
            x = 0.0
            y += step
        if y + h > circuit.canvas_h:
            y = 0.0
            x += step
    return x, y


def _place_with_ppo_gnn_policy(
    circuit: CircuitSpec,
    checkpoint_path: str | None,
) -> dict:
    """使用 Edge-GNN + PPO ActorCritic 策略网络执行 AI 布局（R3 新增）。

    在 PPO 观测向量中注入 Edge-GNN 图级嵌入，增强电路拓扑感知能力:
    1. 构建 GNN 输入（节点特征 + 边索引 + 边特征）
    2. 实例化 AlphaChipEdgeGNN（随机初始化，无 checkpoint）
    3. 实例化 PyTorch ActorCritic（obs_dim = 8 + 16 = 24）
    4. 逐器件布局: GNN 前向提取图嵌入 → 拼接到观测 → PPO 采样坐标
    5. 边特征随放置状态动态更新（距离特征变化）

    学术诚信说明:
        - GNN 为随机初始化（无预训练 checkpoint），嵌入近似随机噪声
        - placement_mode="ppo_gnn_init"（非预训练）
        - HPWL 不能与 AlphaChip 预训练模型对标
        - 但确为 Edge-GNN + PPO 策略网络前向推理（非纯随机贪心）

    来源:
    - AlphaChip Edge-GNN: Mirhoseini et al., Nature 2021
      https://www.nature.com/articles/s41586-021-03544-w
    - GAT 注意力: Veličković et al., ICLR 2018
      https://arxiv.org/abs/1710.10903
    - GlobalAttention 读出: PyTorch Geometric
      https://pytorch-geometric.readthedocs.io/

    Args:
        circuit: 电路规格。
        checkpoint_path: PPO checkpoint 路径（GNN 无 checkpoint，始终随机初始化）。

    Returns:
        布局结果 {name: {x, y, w, h}}。
    """
    instance_ids = [d.name for d in circuit.devices]
    n_dev = len(instance_ids)

    # 1. 构建 GNN 输入
    node_feats_np = _build_gnn_node_features(circuit, instance_ids)
    edge_index = _build_edge_index_from_circuit(circuit, instance_ids)

    # 2. 实例化 AlphaChipEdgeGNN（随机初始化）
    gnn = AlphaChipEdgeGNN(
        in_dim=_GNN_NODE_FEAT_DIM,
        edge_feat_dim=PHOTONIC_EDGE_DIM,
        hidden_dim=_GNN_HIDDEN_DIM,
        out_dim=_GNN_OUT_DIM,
        num_layers=_GNN_NUM_LAYERS,
        use_gat=True,
        use_multi_relation=True,
    )
    _logger.info(
        "Edge-GNN 实例化: in_dim=%d, out_dim=%d, hidden=%d, layers=%d, "
        "edge_feat_dim=%d, edges=%d, nodes=%d",
        _GNN_NODE_FEAT_DIM, _GNN_OUT_DIM, _GNN_HIDDEN_DIM,
        _GNN_NUM_LAYERS, PHOTONIC_EDGE_DIM, edge_index.shape[1], n_dev,
    )

    # 3. 实例化 PyTorch ActorCritic（obs_dim = 8 + 16 = 24）
    gnn_obs_dim = _OBS_DIM + _GNN_OUT_DIM
    agent = ActorCritic(
        obs_dim=gnn_obs_dim,
        action_dim=_ACTION_DIM,
        hidden_dim=_HIDDEN_DIM,
    )
    agent.eval()

    # 尝试加载 PPO checkpoint（GNN 无 checkpoint，始终随机初始化）
    weights_loaded = False
    if checkpoint_path is not None:
        try:
            data = torch.load(checkpoint_path, weights_only=False)
            if isinstance(data, dict) and "network" in data:
                agent.load_state_dict(data["network"])
                weights_loaded = True
                _logger.info("PPO checkpoint 权重加载成功: %s", checkpoint_path)
        except Exception as exc:
            _logger.warning(
                "PPO checkpoint 加载失败 (%s): %s，使用 Orthogonal 初始化网络",
                checkpoint_path, exc,
            )

    if not weights_loaded:
        _logger.info(
            "使用 Orthogonal 初始化 PPO + 随机初始化 Edge-GNN 做前向推理"
            "（非预训练，非纯随机贪心）"
        )

    # 4. 逐器件布局
    placements: dict[str, dict[str, float]] = {}
    occupied: list[tuple[float, float, float, float]] = []

    for idx, dev in enumerate(circuit.devices):
        # 动态更新边特征（距离随放置变化）
        edge_feats_np = _build_gnn_edge_features(
            circuit, instance_ids, edge_index, placements
        )

        # GNN 前向推理（无需梯度）
        node_feats_t = Tensor(node_feats_np)
        edge_feats_t = Tensor(edge_feats_np)
        gnn_emb = gnn(node_feats_t, edge_index, edge_feats_t)
        gnn_emb_np = gnn_emb.data.flatten()  # [out_dim]

        # 基础 8 维观测 + GNN 16 维嵌入 = 24 维
        base_obs = _encode_circuit_obs(circuit, dev, idx, n_dev)
        obs = np.concatenate([base_obs, gnn_emb_np]).astype(np.float32)

        # PPO 网络前向推理
        action, _logprob, _value = agent.get_action(obs)
        coord = 1.0 / (1.0 + np.exp(-action))
        x = float(coord[0]) * (circuit.canvas_w - dev.width_um)
        y = float(coord[1]) * (circuit.canvas_h - dev.height_um)

        # 重叠检测
        x, y = _resolve_overlap(
            x, y, dev.width_um, dev.height_um, occupied, circuit
        )

        placements[dev.name] = {
            "x": x, "y": y, "w": dev.width_um, "h": dev.height_um,
        }
        occupied.append((x, y, dev.width_um, dev.height_um))

    return placements


def _place_circuit(
    circuit: CircuitSpec,
    checkpoint_path: str | None,
    use_gnn: bool = False,
) -> dict:
    """对单个电路执行布局。

    使用 PPO ActorCritic 策略网络执行 AI 布局：
    - use_gnn=False: PPO 前向推理（8 维观测）
    - use_gnn=True: Edge-GNN + PPO 前向推理（24 维观测 = 8 + 16 维 GNN 嵌入）
    - checkpoint 存在且可加载 → 加载预训练权重做前向推理
    - checkpoint 不存在 → 用 Orthogonal 初始化网络做前向推理（非纯随机贪心）

    两种情况均真正调用 PPO 网络前向传播，ai_layout_executed=True。

    来源:
    - Mirhoseini et al., Nature 2021 (AlphaChip)
      https://www.nature.com/articles/s41586-021-03544-w
    - Engstrom et al., 2020, Implementation Matters in PPO
      https://arxiv.org/abs/2005.12729

    Args:
        circuit: 电路规格。
        checkpoint_path: RL checkpoint 路径，None 时用初始化网络（非纯随机贪心）。
        use_gnn: 是否启用 Edge-GNN 前向推理（R3 新增）。

    Returns:
        电路布局结果 dict，含 name/n_devices/placements/hpwl/ascii_layout/
            placement_source。
    """
    if use_gnn:
        placements = _place_with_ppo_gnn_policy(circuit, checkpoint_path)
    else:
        placements = _place_with_ppo_policy(circuit, checkpoint_path)

    if not placements:
        raise RuntimeError(
            f"电路 {circuit.name} 布局失败：placements 为空"
        )

    hpwl = _compute_hpwl(circuit, placements)
    ascii_layout = _render_ascii_layout(circuit, placements)

    _logger.info(
        "电路 %s: %d 器件, HPWL=%.2f μm",
        circuit.name,
        len(placements),
        hpwl,
    )
    _logger.info("ASCII 布局预览:\n%s", ascii_layout)

    return {
        "name": circuit.name,
        "n_devices": len(placements),
        "placements": placements,
        "hpwl": round(hpwl, 2),
        "ascii_layout": ascii_layout,
    }


def run(output_dir: Path) -> dict:
    """执行阶段 3: AI 布局。

    流程:
    1. 尝试加载 R34 预训练 checkpoint（若存在则加载权重，否则用 Orthogonal 初始化网络）
    2. 构造 3 个演示电路（MZI、Clements 4x4、量子占位）
    3. 对每个电路调用 PPO ActorCritic 策略网络前向推理执行布局
    4. 计算 HPWL 指标，输出 ASCII 布局预览
    5. 返回布局结果摘要

    学术诚信说明:
        - checkpoint 存在且可加载 → 加载预训练权重，placement_mode="ppo_pretrained"
        - checkpoint 不存在或加载失败 → 用 Orthogonal 初始化 PPO 网络做前向推理，
          placement_mode="ppo_init"（非纯随机贪心，仍为 AI 策略前向推理）
        - 两种情况均真正调用 PPO 网络前向传播，ai_layout_executed=True。
        - ppo_init 模式下 HPWL 为未训练网络的布局结果，不能与 AlphaChip 预训练模型对标，
          但确为 PPO 策略网络前向推理结果（非纯随机贪心）。

    来源:
    - Mirhoseini et al., Nature 2021 (AlphaChip)
      https://www.nature.com/articles/s41586-021-03544-w
    - Engstrom et al., 2020, Implementation Matters in PPO
      https://arxiv.org/abs/2005.12729

    Args:
        output_dir: 输出目录。

    Returns:
        阶段执行结果，含:
        - circuits: 3 电路布局结果列表
        - checkpoint_loaded: checkpoint 是否加载成功
        - placement_mode: 布局模式（"ppo_pretrained" 或 "ppo_init"）
        - ai_layout_executed: 是否真正执行了 AI 布局（始终为 True）
        - baseline_type: 基线类型
        - warning: 告警信息（checkpoint 未加载时提示为初始化网络）
    """
    _logger.info("阶段 3 开始: AI 布局（Edge-GNN + PPO ActorCritic 策略网络）")
    output_dir.mkdir(parents=True, exist_ok=True)

    checkpoint_path = _load_checkpoint()
    # 学术诚信：测试权重是否真正可加载（文件存在 ≠ 权重匹配）
    weights_loadable = _test_checkpoint_loadable(checkpoint_path)
    checkpoint_loaded = weights_loadable
    # R3: 启用 Edge-GNN 前向推理，placement_mode 标识 GNN 模式
    placement_mode = "ppo_gnn_pretrained" if checkpoint_loaded else "ppo_gnn_init"
    _logger.info(
        "布局模式: %s (checkpoint_path=%s, weights_loadable=%s, gnn=enabled)",
        placement_mode,
        checkpoint_path,
        checkpoint_loaded,
    )

    circuits = _build_circuits()
    # 若权重不可加载，传 None 避免每个电路重复尝试加载失败
    effective_checkpoint = checkpoint_path if checkpoint_loaded else None
    # R3: use_gnn=True 启用 Edge-GNN 前向推理
    results = [
        _place_circuit(circuit, effective_checkpoint, use_gnn=True)
        for circuit in circuits
    ]

    _logger.info(
        "阶段 3 完成: %d 电路布局完成, 模式=%s (Edge-GNN 启用)",
        len(results),
        placement_mode,
    )

    return {
        "circuits": results,
        "checkpoint_loaded": checkpoint_loaded,
        "placement_mode": placement_mode,
        "ai_layout_executed": True,
        "baseline_type": placement_mode,
        "gnn_enabled": True,
        "gnn_out_dim": _GNN_OUT_DIM,
        "warning": (
            "HPWL 来自 Orthogonal 初始化 PPO + 随机初始化 Edge-GNN 前向推理"
            "（非预训练），不能与 AlphaChip 预训练模型对标，"
            "但确为 Edge-GNN + PPO 策略前向推理结果"
            if not checkpoint_loaded
            else None
        ),
    }
