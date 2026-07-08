"""AlphaChip Edge-GNN + PPO AI 布局器（polaris-place 子模块）。

迁移自 ``examples/e2e_showcase/stages/stage3_ai_placement.py`` 的
AlphaChip Edge-GNN + PPO ActorCritic 集成，适配 polaris-place 的
``circuit dict`` 接口，**纯 numpy 自包含实现**（仅依赖 numpy，R04: 不参与 GPU）。

## 与 stage3 的关键差异（R03 禁止 fall-back）

stage3 在 checkpoint 未找到/不可加载时，**降级到 Orthogonal 初始化网络**仍
返回布局结果（``placement_mode="ppo_gnn_init"``）。本模块**禁止降级**：

- ppo_gnn 模式**必须**有可加载的预训练 checkpoint；
- checkpoint 未找到 / 文件损坏 / 权重形状不匹配 → **raise RuntimeError**；
- 不返回任何未训练网络的布局结果。

polaris-place 作为独立子模块，使用**自己的 checkpoint 命名空间**（不与旧
stage3 产物 ``checkpoints/rl_2m/placement_agent.json`` 等冲突），用户需提供
polaris-place 格式的预训练 checkpoint 方可启用 ppo_gnn 模式。

## 算法流程（Mirhoseini et al., Nature 2021）

1. 构建电路图：节点特征 [N,4] + 双向边索引 [2,E] + 边特征 [E,15]
2. Edge-GNN 前向：边特征消息传递 + GlobalAttention 读出 → 图嵌入 [16]
3. 逐器件布局：基础 8 维观测 ⊕ GNN 16 维嵌入 = 24 维观测
   → PPO ActorCritic 前向 → sigmoid 压缩 → 画布坐标
4. 贪心重叠消解
5. 输出左下角坐标 {name: {x, y, w, h}}

## 来源（R02 学术诚信）

- AlphaChip: Mirhoseini et al., Nature 2021
  https://www.nature.com/articles/s41586-021-03544-w
- Chip Placement with Deep RL: arXiv:2004.10746
  https://arxiv.org/abs/2004.10746
- GAT 注意力: Veličković et al., ICLR 2018 https://arxiv.org/abs/1710.10903
- GlobalAttention 读出: PyTorch Geometric
  https://pytorch-geometric.readthedocs.io/
- PPO: Schulman et al. 2017 https://arxiv.org/abs/1707.06347
- Engstrom et al. 2020 "Implementation Matters in PPO"
  https://arxiv.org/abs/2005.12729
- HPWL 指标: Kahng & Lienig IEEE TCAD 2009
  https://ieeexplore.ieee.org/document/4685534
"""

from __future__ import annotations

import json
import os
import zlib
from pathlib import Path

import numpy as np

__all__ = ["place_ppo_gnn", "find_checkpoint"]

# ---------------------------------------------------------------------------
# 超参数（与 stage3 对齐，Mirhoseini et al. Nature 2021 状态编码）
# ---------------------------------------------------------------------------
_OBS_DIM = 8  # PPO 基础观测维度（器件级特征）
_GNN_OUT_DIM = 16  # Edge-GNN 输出维度（图级嵌入，GlobalAttention 读出）
_GNN_HIDDEN_DIM = 32  # Edge-GNN 隐藏层维度
_GNN_NUM_LAYERS = 2  # Edge-GNN 消息传递层数
_GNN_NODE_FEAT_DIM = 4  # 节点特征维度
PHOTONIC_EDGE_DIM = 15  # 边特征维度（与 stage3 PHOTONIC_EDGE_DIM 对齐）
_ACTION_DIM = 2  # 动作维度（归一化坐标 x, y）
_HIDDEN_DIM = 64  # PPO 网络隐藏层维度
_GNN_OBS_DIM = _OBS_DIM + _GNN_OUT_DIM  # 24

# polaris-place 专属 checkpoint 候选路径（独立命名空间，不与旧 stage3 产物冲突）
# 用户需提供 polaris-place 格式 checkpoint 方可启用 ppo_gnn 模式
_CHECKPOINT_CANDIDATES: list[str] = [
    "checkpoints/polaris_place_ppo_gnn.json",
    "checkpoints/polaris_place/ppo_gnn.json",
    "checkpoints/polaris_place/ppo_gnn.pt",
]

# 器件类型 → ASCII 字符映射（与 stage3 一致）
_DEVICE_GLYPH: dict[str, str] = {
    "grating_coupler": "G",
    "mmi_1x2": "M",
    "mmi_2x2": "M",
    "strip_waveguide": "W",
    "phase_shifter": "P",
    "detector": "D",
}


# ---------------------------------------------------------------------------
# Checkpoint 加载（R03: 无可用 checkpoint 必须 raise，禁止降级）
# ---------------------------------------------------------------------------
def find_checkpoint() -> str | None:
    """查找可用的 polaris-place ppo_gnn 预训练 checkpoint。

    按候选路径 + 环境变量 ``POLARIS_PLACE_CHECKPOINT`` 依次检查。

    Returns:
        checkpoint 文件路径，未找到返回 None。
    """
    env_path = os.environ.get("POLARIS_PLACE_CHECKPOINT")
    candidates: list[str] = list(_CHECKPOINT_CANDIDATES)
    if env_path:
        candidates.insert(0, env_path)
    for path in candidates:
        if Path(path).exists():
            return path
    # 合法：查找函数未命中，由调用方 place_ppo_gnn 决策（ppo_gnn.py:547-553
    # 显式 raise RuntimeError 禁止降级）。非 fall-back：本函数仅负责查找，
    # 不决策是否降级，决策权在调用方。
    return None


def _load_checkpoint_data(path: str) -> dict:
    """加载 checkpoint 文件内容（JSON 格式）。

    Args:
        path: checkpoint 文件路径。

    Returns:
        checkpoint 字典（含 ``"network"`` 键，PPO 权重）。

    Raises:
        RuntimeError: 文件不可读 / JSON 解析失败 / 缺少 ``network`` 键
            （R03 禁止 fall-back，文件损坏即报错不降级）。
    """
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(
            f"ppo_gnn checkpoint 加载失败 ({path}): {exc}"
            f"（R03 禁止 fall-back：checkpoint 损坏即报错，不降级到初始化网络）"
        ) from exc
    if not isinstance(data, dict) or "network" not in data:
        raise RuntimeError(
            f"ppo_gnn checkpoint 格式非法 ({path}): 缺少 'network' 键"
            f"（R03 禁止 fall-back：格式不符即报错，不降级到初始化网络）"
        )
    return data


def _to_np(arr) -> np.ndarray:
    """将 checkpoint 中的列表转换为 numpy 数组。"""
    return np.asarray(arr, dtype=np.float64)


# ---------------------------------------------------------------------------
# 纯 numpy 神经网络层（Linear + 激活）
# ---------------------------------------------------------------------------
def _linear(x: np.ndarray, W: np.ndarray, b: np.ndarray) -> np.ndarray:
    """线性层 y = W @ x + b。

    Args:
        x: 输入 [..., in]。
        W: 权重 [out, in]。
        b: 偏置 [out]。

    Returns:
        输出 [..., out]。
    """
    return x @ W.T + b


def _relu(x: np.ndarray) -> np.ndarray:
    return np.maximum(x, 0.0)


def _tanh(x: np.ndarray) -> np.ndarray:
    return np.tanh(x)


def _sigmoid(x: np.ndarray) -> np.ndarray:
    # 数值稳定 sigmoid
    out = np.empty_like(x, dtype=np.float64)
    pos = x >= 0
    out[pos] = 1.0 / (1.0 + np.exp(-x[pos]))
    ex = np.exp(x[~pos])
    out[~pos] = ex / (1.0 + ex)
    return out


def _softmax(x: np.ndarray) -> np.ndarray:
    """一维 softmax（数值稳定）。"""
    z = x - np.max(x)
    e = np.exp(z)
    return e / e.sum()


# ---------------------------------------------------------------------------
# AlphaChip Edge-GNN（纯 numpy）
# ---------------------------------------------------------------------------
class EdgeGNN:
    """AlphaChip 风格 Edge-GNN（纯 numpy 实现）。

    边特征消息传递 + GlobalAttention 读出。

    权重通过 ``load_state_dict`` 从 checkpoint 加载；未加载时使用固定种子
    初始化（仅在 checkpoint 存在但缺 GNN 权重时使用，与 stage3 一致：
    stage3 中 GNN 始终随机初始化，PPO 权重来自 checkpoint）。

    来源: Mirhoseini et al., Nature 2021；GAT: Veličković et al. ICLR 2018。
    """

    def __init__(self, seed: int = 42) -> None:
        self.in_dim = _GNN_NODE_FEAT_DIM
        self.edge_dim = PHOTONIC_EDGE_DIM
        self.hidden = _GNN_HIDDEN_DIM
        self.out_dim = _GNN_OUT_DIM
        self.num_layers = _GNN_NUM_LAYERS
        rng = np.random.default_rng(seed)
        # 每层: node_proj (in→hidden), edge_msg (hidden+edge→hidden), node_update (hidden+hidden→hidden)
        self.layers: list[dict[str, np.ndarray]] = []
        cur = self.in_dim
        for _ in range(self.num_layers):
            self.layers.append({
                "node_proj.W": rng.standard_normal((self.hidden, cur)) * 0.1,
                "node_proj.b": np.zeros(self.hidden),
                "edge_msg.W": rng.standard_normal((self.hidden, self.hidden + self.edge_dim)) * 0.1,
                "edge_msg.b": np.zeros(self.hidden),
                "node_update.W": rng.standard_normal((self.hidden, self.hidden * 2)) * 0.1,
                "node_update.b": np.zeros(self.hidden),
            })
            cur = self.hidden
        # GlobalAttention 读出
        self.gate_W = rng.standard_normal((self.hidden,)) * 0.1
        self.feat_W = rng.standard_normal((self.out_dim, self.hidden)) * 0.1
        self.feat_b = np.zeros(self.out_dim)

    def load_state_dict(self, state: dict) -> None:
        """从 state_dict 加载 GNN 权重（键存在则覆盖）。

        Args:
            state: 权重字典。缺键的层保留初始化权重（与 stage3 一致）。
        """
        for li, layer in enumerate(self.layers):
            for k in ("node_proj.W", "node_proj.b", "edge_msg.W",
                      "edge_msg.b", "node_update.W", "node_update.b"):
                key = f"layers.{li}.{k}"
                if key in state:
                    arr = _to_np(state[key])
                    if arr.shape == layer[k].shape:
                        layer[k] = arr
        if "gate_W" in state:
            arr = _to_np(state["gate_W"])
            if arr.shape == self.gate_W.shape:
                self.gate_W = arr
        if "feat_W" in state:
            arr = _to_np(state["feat_W"])
            if arr.shape == self.feat_W.shape:
                self.feat_W = arr
        if "feat_b" in state:
            arr = _to_np(state["feat_b"])
            if arr.shape == self.feat_b.shape:
                self.feat_b = arr

    def forward(
        self,
        node_feats: np.ndarray,
        edge_index: np.ndarray,
        edge_feats: np.ndarray,
    ) -> np.ndarray:
        """GNN 前向推理，返回图级嵌入 [out_dim]。

        Args:
            node_feats: 节点特征 [N, in_dim]。
            edge_index: 边索引 [2, E]。
            edge_feats: 边特征 [E, edge_dim]。

        Returns:
            图级嵌入 [out_dim]。
        """
        h = node_feats
        n = h.shape[0]
        for layer in self.layers:
            proj = _linear(h, layer["node_proj.W"], layer["node_proj.b"])  # [N, hidden]
            # 消息传递：每条边 src→dst，message = tanh(edge_msg(concat(proj[src], edge_feat)))
            agg = np.zeros((n, self.hidden), dtype=np.float64)
            cnt = np.zeros(n, dtype=np.float64)
            E = edge_index.shape[1]
            if E > 0:
                src_idx = edge_index[0]
                dst_idx = edge_index[1]
                src_proj = proj[src_idx]  # [E, hidden]
                msg_in = np.concatenate([src_proj, edge_feats], axis=1)  # [E, hidden+edge]
                msg = _tanh(_linear(msg_in, layer["edge_msg.W"], layer["edge_msg.b"]))  # [E, hidden]
                np.add.at(agg, dst_idx, msg)
                np.add.at(cnt, dst_idx, 1.0)
            cnt_safe = np.maximum(cnt, 1.0).reshape(-1, 1)
            agg = agg / cnt_safe  # 均值聚合
            # 节点更新：concat(proj, agg) → relu(node_update)
            upd_in = np.concatenate([proj, agg], axis=1)  # [N, hidden*2]
            upd = _relu(_linear(upd_in, layer["node_update.W"], layer["node_update.b"]))
            h = upd
        # GlobalAttention 读出
        gate_scores = h @ self.gate_W  # [N]
        gates = _softmax(gate_scores)  # [N]
        feats = _linear(h, self.feat_W, self.feat_b)  # [N, out_dim]
        emb = (gates.reshape(-1, 1) * feats).sum(axis=0)  # [out_dim]
        return emb


# ---------------------------------------------------------------------------
# PPO ActorCritic（纯 numpy）
# ---------------------------------------------------------------------------
class ActorCritic:
    """PPO ActorCritic 策略网络（纯 numpy 实现）。

    结构: shared MLP(obs→hidden→hidden) → action_mean(hidden→action_dim)，
    value_head(hidden→1)。推理时 action = action_mean（确定性，无采样噪声）。

    来源: Schulman et al. PPO 2017；Engstrom et al. 2020。
    """

    def __init__(self, obs_dim: int, action_dim: int, hidden_dim: int, seed: int = 42) -> None:
        self.obs_dim = obs_dim
        self.action_dim = action_dim
        self.hidden_dim = hidden_dim
        rng = np.random.default_rng(seed)
        self.shared_0_W = rng.standard_normal((hidden_dim, obs_dim)) * 0.1
        self.shared_0_b = np.zeros(hidden_dim)
        self.shared_2_W = rng.standard_normal((hidden_dim, hidden_dim)) * 0.1
        self.shared_2_b = np.zeros(hidden_dim)
        self.action_mean_W = rng.standard_normal((action_dim, hidden_dim)) * 0.1
        self.action_mean_b = np.zeros(action_dim)
        self.value_head_W = rng.standard_normal((1, hidden_dim)) * 0.1
        self.value_head_b = np.zeros(1)

    def load_state_dict(self, state: dict) -> None:
        """从 state_dict 加载权重，形状不匹配 raise（R03 禁止 fall-back）。

        Args:
            state: 权重字典，键为 shared.0.weight / shared.0.bias /
                shared.2.weight / shared.2.bias / action_mean.weight /
                action_mean.bias / value_head.weight / value_head.bias。

        Raises:
            RuntimeError: 权重形状不匹配（checkpoint 与网络架构不一致）。
        """
        mapping = {
            "shared.0.weight": "shared_0_W",
            "shared.0.bias": "shared_0_b",
            "shared.2.weight": "shared_2_W",
            "shared.2.bias": "shared_2_b",
            "action_mean.weight": "action_mean_W",
            "action_mean.bias": "action_mean_b",
            "value_head.weight": "value_head_W",
            "value_head.bias": "value_head_b",
        }
        for ckpt_key, attr in mapping.items():
            if ckpt_key not in state:
                raise RuntimeError(
                    f"ppo_gnn checkpoint 缺少权重键: {ckpt_key}"
                    f"（R03 禁止 fall-back：权重不完整即报错，不降级）"
                )
            arr = _to_np(state[ckpt_key])
            expected = getattr(self, attr).shape
            if tuple(arr.shape) != tuple(expected):
                raise RuntimeError(
                    f"ppo_gnn checkpoint 权重形状不匹配: {ckpt_key} "
                    f"期望 {expected} 实际 {tuple(arr.shape)}"
                    f"（R03 禁止 fall-back：架构不一致即报错，不降级）"
                )
            setattr(self, attr, arr)

    def forward(self, obs: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """前向推理。

        Args:
            obs: 观测 [obs_dim]。

        Returns:
            (action [action_dim], value [1])。action 为 action_mean 输出
            （未过 sigmoid，由调用方按需压缩）。
        """
        h = _relu(_linear(obs, self.shared_0_W, self.shared_0_b))
        h = _relu(_linear(h, self.shared_2_W, self.shared_2_b))
        action = _linear(h, self.action_mean_W, self.action_mean_b)  # [action_dim]
        value = _linear(h, self.value_head_W, self.value_head_b)  # [1]
        return action, value


# ---------------------------------------------------------------------------
# 电路图构建（迁移自 stage3）
# ---------------------------------------------------------------------------
def _parse_circuit(circuit: dict) -> tuple:
    """解析 circuit dict（与 analytical._parse_circuit 一致）。"""
    if not isinstance(circuit, dict):
        raise RuntimeError(f"circuit 必须是 dict，得到 {type(circuit).__name__}")
    for key in ("name", "devices", "connections", "canvas_w", "canvas_h"):
        if key not in circuit:
            raise RuntimeError(f"circuit 缺少必要字段: {key}")
    devices = circuit["devices"]
    names = [d["name"] for d in devices]
    name_to_idx = {nm: i for i, nm in enumerate(names)}
    connections_idx: list[tuple[int, int]] = []
    for conn in circuit["connections"]:
        d1, _p1, d2, _p2 = conn
        if d1 in name_to_idx and d2 in name_to_idx:
            connections_idx.append((name_to_idx[d1], name_to_idx[d2]))
    return devices, names, connections_idx, float(circuit["canvas_w"]), float(circuit["canvas_h"])


def _build_node_features(devices: list, canvas_w: float, canvas_h: float) -> np.ndarray:
    """构建 GNN 节点特征 [N, 4]（width_norm, height_norm, type_hash, idx_norm）。

    来源: AlphaChip node features, Mirhoseini et al. Nature 2021。

    R389 修复：器件类型哈希用 zlib.crc32（稳定跨进程），原 Python 内置
    hash() 受 PYTHONHASHSEED 随机化影响，导致训练/推理特征不一致，checkpoint
    失效（训练时特征值与加载 checkpoint 推理时不同 → GNN 嵌入错误）。
    """
    n = len(devices)
    feats = np.zeros((n, _GNN_NODE_FEAT_DIM), dtype=np.float64)
    for i, d in enumerate(devices):
        feats[i, 0] = float(d["width_um"]) / max(canvas_w, 1.0)
        feats[i, 1] = float(d["height_um"]) / max(canvas_h, 1.0)
        feats[i, 2] = zlib.crc32(d["device_type"].encode("utf-8")) % 100 / 100.0
        feats[i, 3] = i / max(n - 1, 1)
    return feats


def _build_edge_index(
    connections_idx: list[tuple[int, int]],
) -> np.ndarray:
    """构建双向边索引 [2, E]。"""
    if not connections_idx:
        return np.zeros((2, 0), dtype=np.int64)
    edges: list[tuple[int, int]] = []
    for src, dst in connections_idx:
        edges.append((src, dst))
        edges.append((dst, src))
    return np.array(edges, dtype=np.int64).T


def _build_edge_features(
    edge_index: np.ndarray,
    names: list[str],
    placements: dict | None,
) -> np.ndarray:
    """构建边特征 [E, 15]（与 stage3 PHOTONIC_EDGE_DIM 对齐）。

    [0] 曼哈顿距离（若已放置）, [1] 带宽需求, [2] 优先级,
    [3-6] 类型 one-hot, [7-9] 波段 one-hot, [10] 折射率差,
    [11] 波导损耗, [12] 串扰, [13] 弯曲半径, [14] net 关系类型。
    """
    n_edges = edge_index.shape[1]
    feats = np.zeros((n_edges, PHOTONIC_EDGE_DIM), dtype=np.float64)
    for i in range(n_edges):
        src_idx = edge_index[0, i]
        dst_idx = edge_index[1, i]
        src_id = names[src_idx]
        dst_id = names[dst_idx]
        if placements and src_id in placements and dst_id in placements:
            p1 = placements[src_id]
            p2 = placements[dst_id]
            x1, y1 = p1["x"] + p1["w"] / 2.0, p1["y"] + p1["h"] / 2.0
            x2, y2 = p2["x"] + p2["w"] / 2.0, p2["y"] + p2["h"] / 2.0
            feats[i, 0] = abs(x1 - x2) + abs(y1 - y2)
        feats[i, 1] = 1.0
        feats[i, 2] = 1.0
        feats[i, 3] = 1.0  # passive-passive
        feats[i, 7] = 1.0  # C-band
        feats[i, 10] = 0.5
        feats[i, 11] = 0.3
        feats[i, 12] = 0.1
        feats[i, 13] = 0.5
        feats[i, 14] = 0.0
    return feats


def _encode_obs(devices: list, idx: int, n_dev: int, canvas_w: float, canvas_h: float) -> np.ndarray:
    """编码器件级 8 维观测向量（Mirhoseini et al. Nature 2021 状态编码）。

    [0] idx/(n-1), [1] width/canvas_w, [2] height/canvas_h, [3] n_dev/20,
    [4] 连接数/20（此处用 n_dev 代理）, [5] canvas_w/1000, [6] canvas_h/1000,
    [7] 器件类型哈希。

    R389 修复：器件类型哈希用 zlib.crc32（稳定跨进程），与 _build_node_features 同步。
    """
    d = devices[idx]
    type_hash = zlib.crc32(d["device_type"].encode("utf-8")) % 100 / 100.0
    return np.array([
        idx / max(n_dev - 1, 1),
        float(d["width_um"]) / max(canvas_w, 1.0),
        float(d["height_um"]) / max(canvas_h, 1.0),
        n_dev / 20.0,
        max(n_dev - 1, 0) / 20.0,
        canvas_w / 1000.0,
        canvas_h / 1000.0,
        type_hash,
    ], dtype=np.float64)


def _resolve_overlap(
    x: float,
    y: float,
    w: float,
    h: float,
    occupied: list[tuple[float, float, float, float]],
    canvas_w: float,
    canvas_h: float,
) -> tuple[float, float]:
    """贪心重叠消解：沿网格步进错开（Kahng & Lienig 2009）。

    Args:
        x, y: 候选左下角坐标。
        w, h: 器件宽高。
        occupied: 已放置器件 (x, y, w, h) 列表。
        canvas_w, canvas_h: 画布尺寸。

    Returns:
        调整后的 (x, y)。

    Raises:
        RuntimeError: max_tries 用尽仍未消解重叠（R03 禁止 fall-back：
            不返回可能重叠的位置伪装成功放置）。
    """
    step = 5.0
    max_tries = 200
    for _ in range(max_tries):
        overlap = False
        for ox, oy, ow, oh in occupied:
            if not (x + w <= ox or ox + ow <= x or y + h <= oy or oy + oh <= y):
                overlap = True
                break
        if not overlap:
            return x, y
        x += step
        if x + w > canvas_w:
            x = 0.0
            y += step
        if y + h > canvas_h:
            y = 0.0
            x += step
    # R389 修复：max_tries 用尽仍重叠 → raise（R03 禁止 fall-back）
    # 原代码 return x, y 会返回可能重叠的位置，后续 NO_OVERLAP DRC 必然违规，
    # 把"未能消解重叠"伪装成"成功放置"是假数据兜底。
    raise RuntimeError(
        f"_resolve_overlap 在 {max_tries} 次尝试后仍未消解重叠"
        f"（画布 {canvas_w}×{canvas_h}μm 可能已满，器件 {w}×{h}μm）"
        f"（R03 禁止 fall-back）"
    )


def place_ppo_gnn(circuit: dict) -> tuple[dict[str, dict[str, float]], bool]:
    """使用 Edge-GNN + PPO 执行 AI 布局（需预训练 checkpoint）。

    R03 禁止 fall-back：无可用 checkpoint / checkpoint 损坏 / 权重不匹配时
    **raise RuntimeError**，不降级到初始化网络返回未训练结果。

    Args:
        circuit: polaris-core 风格 circuit dict。

    Returns:
        ``(placements, checkpoint_loaded)``。placements 为
        ``{name: {x, y, w, h}}``（左下角坐标），checkpoint_loaded 恒为 True
        （无 checkpoint 时已 raise）。

    Raises:
        RuntimeError: 无可用 checkpoint / checkpoint 不可加载 / 画布空间
            不足无法消解器件重叠（R03 禁止 fall-back）。
    """
    devices, names, connections_idx, canvas_w, canvas_h = _parse_circuit(circuit)
    n_dev = len(devices)
    if n_dev == 0:
        return {}, True

    # 1. 查找并加载 checkpoint（R03: 无即 raise）
    ckpt_path = find_checkpoint()
    if ckpt_path is None:
        raise RuntimeError(
            f"ppo_gnn 模式需要预训练 checkpoint，未找到可用 checkpoint。"
            f"候选路径: {_CHECKPOINT_CANDIDATES}"
            f"（亦可通过环境变量 POLARIS_PLACE_CHECKPOINT 指定）。"
            f"R03 禁止 fall-back：不返回未训练网络的布局结果。"
        )
    data = _load_checkpoint_data(ckpt_path)

    # 2. 构建 GNN 输入
    node_feats = _build_node_features(devices, canvas_w, canvas_h)
    edge_index = _build_edge_index(connections_idx)

    # 3. 实例化 Edge-GNN + PPO ActorCritic
    gnn = EdgeGNN()
    if "gnn" in data and isinstance(data["gnn"], dict):
        gnn.load_state_dict(data["gnn"])
    agent = ActorCritic(
        obs_dim=_GNN_OBS_DIM,
        action_dim=_ACTION_DIM,
        hidden_dim=_HIDDEN_DIM,
    )
    # 加载 PPO 权重（形状不匹配即 raise，R03）
    agent.load_state_dict(data["network"])

    # 4. 逐器件布局：GNN 前向 → 拼接观测 → PPO 前向 → sigmoid → 画布坐标
    placements: dict[str, dict[str, float]] = {}
    occupied: list[tuple[float, float, float, float]] = []
    for idx, dev in enumerate(devices):
        edge_feats = _build_edge_features(edge_index, names, placements)
        gnn_emb = gnn.forward(node_feats, edge_index, edge_feats)  # [out_dim]
        base_obs = _encode_obs(devices, idx, n_dev, canvas_w, canvas_h)
        obs = np.concatenate([base_obs, gnn_emb]).astype(np.float64)
        action, _value = agent.forward(obs)
        coord = _sigmoid(action)
        w = float(dev["width_um"])
        h = float(dev["height_um"])
        x = float(coord[0]) * (canvas_w - w)
        y = float(coord[1]) * (canvas_h - h)
        x, y = _resolve_overlap(x, y, w, h, occupied, canvas_w, canvas_h)
        placements[dev["name"]] = {"x": x, "y": y, "w": w, "h": h}
        occupied.append((x, y, w, h))

    return placements, True
