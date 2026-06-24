"""R34-R35 路标：Google AlphaChip 强化学习布局对齐模块。

对标 Google DeepMind AlphaChip（强化学习芯片布局），将电子 IC 布局 RL
方法扩展到光子 IC 布局，实现 PoLaRIS 与 AlphaChip 的功能对齐。

## 模块组成

1. ``AlphaChipConfig`` — AlphaChip RL 布局配置
2. ``PhotonicPlacementEncoder`` — 光子布局状态编码器（Edge-based GNN 输入）
3. ``PhotonicPlacementReward`` — 光子布局多目标奖励函数
4. ``AlphaChipAgent`` — AlphaChip 强化学习布局智能体
5. ``AlphaChipTrainer`` — AlphaChip 训练器（REINFORCE + baseline）

## 学术依据

- Google DeepMind AlphaChip:
  https://deepmind.google/discover/blog/alphachip-a-new-approach-to-chip-layout/
- Mirhoseini et al., Nature 2024, "AlphaChip":
  https://doi.org/10.1038/s41586-024-07714-9
- Mirhoseini et al., Nature 2021, "A graph placement methodology for fast chip design"
  DOI: 10.1038/s41586-021-03544-w
- Schulman et al., 2017, PPO: https://arxiv.org/abs/1707.06347
- Gilmer et al., 2017, MPNN（消息传递神经网络）: https://arxiv.org/abs/1704.01212
- DREAMPlace RUDY 拥塞估计: https://arxiv.org/abs/2004.10746
- Sutton & Barto, 2018, "Reinforcement Learning: An Introduction" §13（策略梯度）

## 【创新】光子布局扩展

AlphaChip 原为电子 IC 布局设计，本模块将其扩展到光子 IC 布局：
- 电子 IC 优化目标：线长 / 拥塞 / 面积
- 光子 IC 增加光学约束：波导交叉数 / 弯曲半径违反 / 波导长度均匀性（相位匹配）
- 创新逻辑：光子波导交叉引入插入损耗与串扰，弯曲半径过小引入辐射损耗，
  波导长度不均匀导致相位失配，故需在 AlphaChip 奖励函数中增加光学约束项。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

# 光学约束参数（来源: SiEPIC EBeam PDK 标准值 + LiDAR ISPD'25 光学约束）
_MIN_BEND_RADIUS = 20.0  # 最小弯曲半径（μm），低于此值波导辐射损耗显著
_GRID_CELL_SIZE = 100.0  # 网格单元物理尺寸（μm）
_CANVAS_SIZE = 3200.0  # 画布物理尺寸（μm），对应 32×32 网格

# 器件类型映射（来源: PoLaRIS PDK catalog 标准器件类型）
_DEVICE_TYPES = {"mzi": 0, "ring": 1, "mmi": 2, "coupler": 3}
# 连接类型映射（来源: 光子电路网表标准连接类型）
_NET_TYPES = {"waveguide": 0, "crossing": 1, "bend": 2}


# ---------------------------------------------------------------------------
# 1. AlphaChipConfig — RL 布局配置
# ---------------------------------------------------------------------------


@dataclass
class AlphaChipConfig:
    """AlphaChip RL 布局配置。

    学术依据：Google DeepMind AlphaChip
    URL: https://deepmind.google/discover/blog/alphachip-a-new-approach-to-chip-layout/
    Nature 2024: https://doi.org/10.1038/s41586-024-07714-9

    Mirhoseini 2021 Nature: "A graph placement methodology for fast chip design"
    DOI: 10.1038/s41586-021-03544-w

    Attributes:
        grid_size: 布局网格 (grid_h, grid_w)。
        n_episodes: 训练轮数。
        learning_rate: 学习率。
        gnn_hidden: GNN 隐藏层维度。
        gnn_layers: GNN 层数。
        use_attention: 是否使用注意力机制。
        gamma: 折扣因子（来源: Sutton & Barto 2018 §13 默认值）。
    """

    grid_size: tuple = (32, 32)
    n_episodes: int = 10000
    learning_rate: float = 1e-4
    gnn_hidden: int = 128
    gnn_layers: int = 3
    use_attention: bool = True
    gamma: float = 0.99


# ---------------------------------------------------------------------------
# 2. PhotonicPlacementEncoder — 光子布局状态编码器
# ---------------------------------------------------------------------------


class PhotonicPlacementEncoder:
    """光子布局状态编码器。

    学术依据：AlphaChip 状态编码（Mirhoseini 2024 Nature）
    https://doi.org/10.1038/s41586-024-07714-9

    将光子电路编码为 GNN 可处理的图结构：
    - 节点：器件（BB，bounding box）
    - 边：连接关系（波导）
    - 节点特征：器件类型 / 尺寸 / 端口数 / 长宽比 / 面积
    - 边特征：连接类型 / 目标长度

    【创新】光子电路图编码：
    - 电子 IC 节点特征为标准单元宏参数
    - 光子 IC 节点特征增加端口数（光子器件端口数差异大，MZI 4 端口 vs Ring 2 端口）
    - 边特征增加目标长度（光子波导需相位匹配，目标长度是关键约束）
    """

    # 节点特征维度: type_one_hot(4) + width + height + n_ports + aspect + area = 9
    NODE_FEAT_DIM: int = 9
    # 边特征维度: type_one_hot(3) + target_length = 4
    EDGE_FEAT_DIM: int = 4

    def __init__(self) -> None:
        """初始化编码器。"""
        self.node_feat_dim = self.NODE_FEAT_DIM
        self.edge_feat_dim = self.EDGE_FEAT_DIM

    def encode_circuit(self, circuit: dict) -> dict:
        """编码电路为图结构。

        Args:
            circuit: 电路描述 dict，含 ``devices`` 与 ``nets`` 列表。

        Returns:
            图结构 dict，含 ``node_feats`` [N, F]、``edge_index`` [2, E]、
            ``edge_feats`` [E, Fe]。
        """
        devices = circuit["devices"]
        nets = circuit["nets"]
        # 节点特征
        node_feats = np.array(
            [self.compute_features(d) for d in devices], dtype=np.float64
        )
        if len(devices) == 0:
            node_feats = node_feats.reshape(0, self.node_feat_dim)
        # 设备 id 到索引映射
        id2idx = {d["id"]: i for i, d in enumerate(devices)}
        # 边索引 + 边特征
        srcs: list[int] = []
        dsts: list[int] = []
        edge_feats_list: list[np.ndarray] = []
        for net in nets:
            src_inst = net["src"][0]
            dst_inst = net["dst"][0]
            if src_inst in id2idx and dst_inst in id2idx:
                srcs.append(id2idx[src_inst])
                dsts.append(id2idx[dst_inst])
                edge_feats_list.append(self._compute_edge_features(net))
        if srcs:
            edge_index = np.array([srcs, dsts], dtype=np.int64)
            edge_feats = np.array(edge_feats_list, dtype=np.float64)
        else:
            edge_index = np.zeros((2, 0), dtype=np.int64)
            edge_feats = np.zeros((0, self.edge_feat_dim), dtype=np.float64)
        return {
            "node_feats": node_feats,
            "edge_index": edge_index,
            "edge_feats": edge_feats,
        }

    def encode_placement(self, placement: dict, circuit: dict) -> np.ndarray:
        """编码布局状态为 GNN 输入（节点特征 + 位置信息）。

        Args:
            placement: 布局 dict，{inst_id: {"x", "y", "rotation"}}。
            circuit: 电路描述 dict。

        Returns:
            节点特征矩阵 [N, node_feat_dim + 4]，4 = x, y, rotation, is_placed。
        """
        graph = self.encode_circuit(circuit)
        node_feats = graph["node_feats"]
        n = len(circuit["devices"])
        # 位置特征：x, y, rotation, is_placed
        pos_feats = np.zeros((n, 4), dtype=np.float64)
        for i, dev in enumerate(circuit["devices"]):
            if dev["id"] in placement:
                p = placement[dev["id"]]
                pos_feats[i, 0] = float(p["x"])
                pos_feats[i, 1] = float(p["y"])
                pos_feats[i, 2] = float(p.get("rotation", 0))
                pos_feats[i, 3] = 1.0  # is_placed
        if n == 0:
            return np.zeros((0, self.node_feat_dim + 4), dtype=np.float64)
        return np.concatenate([node_feats, pos_feats], axis=1)

    def compute_features(self, node: dict) -> np.ndarray:
        """计算节点特征。

        特征向量: [type_one_hot(4), width, height, n_ports, aspect_ratio, area]

        Args:
            node: 器件描述 dict。

        Returns:
            节点特征向量 [node_feat_dim]。
        """
        type_oh = np.zeros(4, dtype=np.float64)
        t = _DEVICE_TYPES.get(node.get("type", "mzi"), 0)
        type_oh[t] = 1.0
        w = float(node.get("width", 50.0))
        h = float(node.get("height", 30.0))
        ports = node.get("ports", [])
        n_ports = float(len(ports))
        aspect = w / max(h, 1e-6)
        area = w * h
        return np.concatenate([type_oh, [w, h, n_ports, aspect, area]])

    def _compute_edge_features(self, net: dict) -> np.ndarray:
        """计算边特征。

        特征向量: [type_one_hot(3), target_length]

        Args:
            net: 连接描述 dict。

        Returns:
            边特征向量 [edge_feat_dim]。
        """
        type_oh = np.zeros(3, dtype=np.float64)
        t = _NET_TYPES.get(net.get("type", "waveguide"), 0)
        type_oh[t] = 1.0
        target_length = float(net.get("target_length", 100.0))
        return np.concatenate([type_oh, [target_length]])


# ---------------------------------------------------------------------------
# 3. PhotonicPlacementReward — 光子布局多目标奖励函数
# ---------------------------------------------------------------------------


class PhotonicPlacementReward:
    """光子布局奖励函数。

    【创新】光子布局多目标奖励：
    - 线长（HPWL）：经典 EDA 半周长线长估计
    - 拥塞（RUDY）：DREAMPlace 拥塞估计
    - 交叉数（光学约束）：波导交叉引入插入损耗与串扰
    - 弯曲半径违反（光学约束）：弯曲半径过小引入辐射损耗
    - 波导长度均匀性（光学约束）：相位匹配要求波导长度均匀

    学术依据：
    - AlphaChip 奖励函数（Mirhoseini 2024 Nature）
      https://doi.org/10.1038/s41586-024-07714-9
    - DREAMPlace RUDY: https://arxiv.org/abs/2004.10746
    - LiDAR 光学约束（ISPD'25）
    - SiEPIC EBeam PDK 弯曲半径标准: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
    """

    def __init__(
        self,
        w_wirelength: float = 1.0,
        w_congestion: float = 1.0,
        w_crossing: float = 2.0,
        w_bend: float = 1.5,
        w_uniformity: float = 0.5,
    ) -> None:
        """初始化奖励函数。

        Args:
            w_wirelength: 线长权重。
            w_congestion: 拥塞权重。
            w_crossing: 交叉数权重（光学约束，权重较高）。
            w_bend: 弯曲违反权重（光学约束）。
            w_uniformity: 均匀性权重（光学约束，相位匹配）。
        """
        self.weights = {
            "wirelength": w_wirelength,
            "congestion": w_congestion,
            "crossing": w_crossing,
            "bend": w_bend,
            "uniformity": w_uniformity,
        }

    def compute(self, placement: dict, circuit: dict) -> dict:
        """计算多目标奖励。

        奖励 = -(w_wl·线长 + w_cong·拥塞 + w_cross·交叉数
                 + w_bend·弯曲违反 + w_uni·均匀性)

        Args:
            placement: 布局 dict。
            circuit: 电路描述 dict。

        Returns:
            奖励明细 dict，含 ``reward`` 与各项指标。
        """
        wl = self.compute_wirelength(placement, circuit)
        cong = self.compute_congestion(placement, circuit)
        cross = self.compute_crossing(placement, circuit)
        bend = self.compute_bend_violation(placement, circuit)
        uni = self.compute_uniformity(placement, circuit)
        w = self.weights
        reward = -(
            w["wirelength"] * wl
            + w["congestion"] * cong
            + w["crossing"] * float(cross)
            + w["bend"] * float(bend)
            + w["uniformity"] * uni
        )
        return {
            "reward": float(reward),
            "wirelength": float(wl),
            "congestion": float(cong),
            "crossing": int(cross),
            "bend_violation": int(bend),
            "uniformity": float(uni),
        }

    def compute_wirelength(self, placement: dict, circuit: dict) -> float:
        """计算 HPWL 线长（半周长线长估计）。

        学术依据：经典 EDA 半周长线长估计。
        对每条连接取所有相关端口坐标的 (xmax-xmin)+(ymax-ymin)。

        Args:
            placement: 布局 dict。
            circuit: 电路描述 dict。

        Returns:
            所有连接的 HPWL 总和（μm）。
        """
        port_pos = self._port_positions(placement, circuit)
        total = 0.0
        for net in circuit["nets"]:
            pts: list[tuple[float, float]] = []
            for end in [net["src"], net["dst"]]:
                key = (end[0], end[1])
                if key in port_pos:
                    pts.append(port_pos[key])
            if len(pts) >= 2:
                xs = [p[0] for p in pts]
                ys = [p[1] for p in pts]
                total += (max(xs) - min(xs)) + (max(ys) - min(ys))
        return float(total)

    def compute_congestion(self, placement: dict, circuit: dict) -> float:
        """计算 RUDY 拥塞（Rectangular Uniform wire DensitY）。

        学术依据：DREAMPlace RUDY 拥塞估计
        https://arxiv.org/abs/2004.10746

        对每条连接，在其 bounding box 内均匀分布需求密度，
        累加到拥塞图，返回拥塞图最大值。

        Args:
            placement: 布局 dict。
            circuit: 电路描述 dict。

        Returns:
            拥塞图最大值（无量纲）。
        """
        port_pos = self._port_positions(placement, circuit)
        grid_h, grid_w = 32, 32
        congestion_map = np.zeros((grid_h, grid_w), dtype=np.float64)
        for net in circuit["nets"]:
            pts: list[tuple[float, float]] = []
            for end in [net["src"], net["dst"]]:
                key = (end[0], end[1])
                if key in port_pos:
                    pts.append(port_pos[key])
            if len(pts) < 2:
                continue
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            xmin, xmax = min(xs), max(xs)
            ymin, ymax = min(ys), max(ys)
            gi0 = max(0, int(xmin / _CANVAS_SIZE * grid_w))
            gi1 = min(grid_w, int(np.ceil(xmax / _CANVAS_SIZE * grid_w)) + 1)
            gj0 = max(0, int(ymin / _CANVAS_SIZE * grid_h))
            gj1 = min(grid_h, int(np.ceil(ymax / _CANVAS_SIZE * grid_h)) + 1)
            area = max((gi1 - gi0) * (gj1 - gj0), 1)
            congestion_map[gj0:gj1, gi0:gi1] += 1.0 / area
        return float(congestion_map.max())

    def compute_crossing(self, placement: dict, circuit: dict) -> int:
        """计算波导交叉数（光学约束）。

        【创新】光子波导交叉数约束（超出 Mirhoseini 2024 Nature 范围）

        创新逻辑：
        - 电子 IC 金属线交叉仅引入 RC 延迟与串扰，影响较小
        - 光子波导交叉引入插入损耗（~0.1 dB/交叉）与光学串扰，
          直接降低信噪比与器件性能，需在布局阶段最小化交叉数

        支持理论：
        - 波导交叉插入损耗：SiN/Si 波导交叉典型损耗 0.05-0.3 dB
          （来源: Bogaerts et al., "Silicon nanophotonic waveguide crossings",
          J. Lightwave Technol. 2013, DOI: 10.1109/JLT.2013.2258874）
        - 交叉串扰：交叉点处部分光耦合至正交波导，典型串扰 -30~-40 dB
          （来源: Liu et al., "Ultralow-loss waveguide crossing for SiP",
          Opt. Express 2019, DOI: 10.1364/OE.27.020886）
        - AlphaChip 原始奖励函数（Mirhoseini 2024 Nature）仅含线长/拥塞/面积，
          无光学交叉约束项，本模块扩展为光子 IC 专用

        将每条连接视为线段，检测线段对是否相交（CCW 跨立实验）。

        Args:
            placement: 布局 dict。
            circuit: 电路描述 dict。

        Returns:
            波导交叉数。
        """
        port_pos = self._port_positions(placement, circuit)
        segments: list[list[tuple[float, float]]] = []
        for net in circuit["nets"]:
            pts: list[tuple[float, float]] = []
            for end in [net["src"], net["dst"]]:
                key = (end[0], end[1])
                if key in port_pos:
                    pts.append(port_pos[key])
            if len(pts) == 2:
                segments.append(pts)
        count = 0
        for i in range(len(segments)):
            for j in range(i + 1, len(segments)):
                if self._segments_intersect(segments[i], segments[j]):
                    count += 1
        return count

    def compute_bend_violation(self, placement: dict, circuit: dict) -> int:
        """计算弯曲半径违反数（光学约束）。

        【创新】光子波导弯曲半径约束（超出 Mirhoseini 2024 Nature 范围）

        创新逻辑：
        - 电子 IC 金属线弯曲无物理限制（仅 DRC 间距规则）
        - 光子波导弯曲半径过小（< _MIN_BEND_RADIUS）会引入辐射损耗，
          导致光从波导芯泄漏到包层，降低传输效率
        - 需检测器件间距是否满足最小弯曲半径要求，确保布线可行

        支持理论：
        - 弯曲辐射损耗：当弯曲半径 R < 临界半径 R_c 时，损耗急剧增加
          α_bend ∝ exp(-R/R_c)，R_c = a·n_core²/(2·(n_core²-n_clad²)^(3/2))
          （来源: Marcuse, "Curvature loss formula for optical fibers",
          J. Opt. Soc. Am. 1976, DOI: 10.1364/JOSA.66.000216）
        - SiEPIC EBeam PDK 标准最小弯曲半径 r_min = 5 μm（1.55 μm 波长），
          本模块取保守值 20 μm 以确保辐射损耗 < 0.01 dB/turn
          （来源: SiEPIC EBeam PDK, https://github.com/SiEPIC/SiEPIC_EBeam_PDK）
        - AlphaChip 原始奖励函数无弯曲半径约束项，本模块扩展为光子 IC 专用

        Args:
            placement: 布局 dict。
            circuit: 电路描述 dict。

        Returns:
            弯曲半径违反数（器件对间距不足数）。
        """
        violations = 0
        devices = circuit["devices"]
        for i in range(len(devices)):
            for j in range(i + 1, len(devices)):
                id_i = devices[i]["id"]
                id_j = devices[j]["id"]
                if id_i not in placement or id_j not in placement:
                    continue
                pi = placement[id_i]
                pj = placement[id_j]
                wi = float(devices[i].get("width", 50))
                hi = float(devices[i].get("height", 30))
                wj = float(devices[j].get("width", 50))
                hj = float(devices[j].get("height", 30))
                ci = (pi["x"] + wi / 2, pi["y"] + hi / 2)
                cj = (pj["x"] + wj / 2, pj["y"] + hj / 2)
                dist = float(np.sqrt((ci[0] - cj[0]) ** 2 + (ci[1] - cj[1]) ** 2))
                gap = dist - max(wi, hi) / 2 - max(wj, hj) / 2
                if gap < _MIN_BEND_RADIUS:
                    violations += 1
        return violations

    def compute_uniformity(self, placement: dict, circuit: dict) -> float:
        """计算波导长度均匀性（光学约束，相位匹配）。

        【创新】光子波导长度均匀性约束（超出 Mirhoseini 2024 Nature 范围）

        创新逻辑：
        - 电子 IC 金属线长度差异仅引入 RC 延迟差异，影响较小
        - 光子干涉仪（如 MZI）要求两臂波导长度匹配（相位匹配），
          波导长度不均匀会导致相位失配，直接降低干涉消光比
        - 用变异系数（CV = std/mean）度量波导长度均匀性，CV 越小越均匀

        支持理论：
        - 相位失配：MZI 两臂长度差 ΔL 引入相位差 Δφ = 2π·n_eff·ΔL/λ，
          消光比 ER = 10·log₁₀((1+cos(Δφ))/(1-cos(Δφ)))，
          ΔL = λ/(4·n_eff) 时消光比降为 0 dB（完全失配）
          （来源: Yariv & Yeh, "Photonics: Optical Electronics in Modern
          Communications", Oxford 2007, Ch. 4 干涉仪原理）
        - 相位匹配要求：典型 MZI 要求 ΔL < λ/(100·n_eff) ≈ 15 nm（1.55 μm），
          对应消光比 > 40 dB
          （来源: Reed et al., "Silicon optical modulators",
          Nat. Photonics 2010, DOI: 10.1038/nphoton.2010.179）
        - AlphaChip 原始奖励函数无波导长度均匀性约束项，本模块扩展为光子 IC 专用

        Args:
            placement: 布局 dict。
            circuit: 电路描述 dict。

        Returns:
            波导长度变异系数（越小越均匀，0 表示完全均匀）。
        """
        port_pos = self._port_positions(placement, circuit)
        lengths: list[float] = []
        for net in circuit["nets"]:
            pts: list[tuple[float, float]] = []
            for end in [net["src"], net["dst"]]:
                key = (end[0], end[1])
                if key in port_pos:
                    pts.append(port_pos[key])
            if len(pts) == 2:
                length = float(
                    np.sqrt((pts[0][0] - pts[1][0]) ** 2 + (pts[0][1] - pts[1][1]) ** 2)
                )
                lengths.append(length)
        if len(lengths) < 2:
            return 0.0
        mean_len = float(np.mean(lengths))
        if mean_len < 1e-6:
            return 0.0
        return float(np.std(lengths) / mean_len)

    def _port_positions(
        self, placement: dict, circuit: dict
    ) -> dict[tuple[str, str], tuple[float, float]]:
        """计算所有已放置器件端口的绝对坐标。

        端口均匀分布在器件周长上，考虑旋转（绕器件中心）。

        Args:
            placement: 布局 dict。
            circuit: 电路描述 dict。

        Returns:
            端口坐标 dict，{(inst_id, port_name): (x, y)}。
        """
        positions: dict[tuple[str, str], tuple[float, float]] = {}
        for dev in circuit["devices"]:
            inst_id = dev["id"]
            if inst_id not in placement:
                continue
            p = placement[inst_id]
            x, y, rot = float(p["x"]), float(p["y"]), int(p.get("rotation", 0))
            w = float(dev.get("width", 50))
            h = float(dev.get("height", 30))
            ports = dev.get("ports", [])
            n_ports = len(ports)
            for i, port_name in enumerate(ports):
                px, py = self._compute_port_pos(x, y, w, h, rot, i, n_ports)
                positions[(inst_id, port_name)] = (px, py)
        return positions

    @staticmethod
    def _compute_port_pos(
        x: float,
        y: float,
        w: float,
        h: float,
        rot: int,
        port_idx: int,
        n_ports: int,
    ) -> tuple[float, float]:
        """计算单个端口的绝对坐标。

        端口沿器件周长均匀分布，应用旋转（绕器件中心）。

        Args:
            x: 器件左下角 x。
            y: 器件左下角 y。
            w: 器件宽度。
            h: 器件高度。
            rot: 旋转角度（度，0/90/180/270）。
            port_idx: 端口索引。
            n_ports: 端口总数。

        Returns:
            端口绝对坐标 (px, py)。
        """
        if n_ports == 0:
            return (x + w / 2, y + h / 2)
        perimeter = 2 * (w + h)
        pos_along = (port_idx / n_ports) * perimeter
        # 沿周长计算局部坐标
        if pos_along < w:
            px, py = x + pos_along, y
        elif pos_along < w + h:
            px, py = x + w, y + (pos_along - w)
        elif pos_along < 2 * w + h:
            px, py = x + w - (pos_along - w - h), y + h
        else:
            px, py = x, y + h - (pos_along - 2 * w - h)
        # 应用旋转（绕器件中心）
        if rot != 0:
            cx, cy = x + w / 2, y + h / 2
            angle = float(np.radians(rot))
            dx, dy = px - cx, py - cy
            px = cx + dx * np.cos(angle) - dy * np.sin(angle)
            py = cy + dx * np.sin(angle) + dy * np.cos(angle)
        return (float(px), float(py))

    @staticmethod
    def _segments_intersect(
        s1: list[tuple[float, float]], s2: list[tuple[float, float]]
    ) -> bool:
        """检测两条线段是否相交（CCW 跨立实验）。

        Args:
            s1: 线段 1，[(x1, y1), (x2, y2)]。
            s2: 线段 2，[(x3, y3), (x4, y4)]。

        Returns:
            是否相交。
        """
        (x1, y1), (x2, y2) = s1
        (x3, y3), (x4, y4) = s2

        def _cross(ax: float, ay: float, bx: float, by: float) -> float:
            return ax * by - bx * ay

        d1 = _cross(x4 - x3, y4 - y3, x1 - x3, y1 - y3)
        d2 = _cross(x4 - x3, y4 - y3, x2 - x3, y2 - y3)
        d3 = _cross(x2 - x1, y2 - y1, x3 - x1, y3 - y1)
        d4 = _cross(x2 - x1, y2 - y1, x4 - x1, y4 - y1)
        if ((d1 > 0 and d2 < 0) or (d1 < 0 and d2 > 0)) and (
            (d3 > 0 and d4 < 0) or (d3 < 0 and d4 > 0)
        ):
            return True
        return False


# ---------------------------------------------------------------------------
# 4. AlphaChipAgent — AlphaChip 强化学习布局智能体
# ---------------------------------------------------------------------------


class AlphaChipAgent:
    """AlphaChip 强化学习布局智能体。

    学术依据：
    - Mirhoseini 2021 Nature（图布局方法）
      https://doi.org/10.1038/s41586-021-03544-w
    - Mirhoseini 2024 Nature（AlphaChip 完整论文）
      https://doi.org/10.1038/s41586-024-07714-9
    - Sutton & Barto 2018 §13（策略梯度）

    架构：
    1. Edge-based GNN：学习器件间的空间关系（Gilmer 2017 MPNN）
    2. 策略网络：输出器件放置位置的概率分布
    3. 价值网络：评估布局质量（baseline）
    4. REINFORCE + baseline 训练：策略优化

    【创新】扩展到光子布局：
    - 电子 IC 优化线长 / 拥塞 / 面积
    - 光子 IC 增加光学约束（波导长度 / 弯曲半径 / 交叉数 / 均匀性）
    """

    def __init__(self, config: AlphaChipConfig) -> None:
        """初始化 AlphaChip agent。

        Args:
            config: AlphaChip 配置。
        """
        self.config = config
        self.encoder = PhotonicPlacementEncoder()
        self.reward = PhotonicPlacementReward()
        self.circuit: dict | None = None
        # 构建网络参数
        self.gnn_params = self.build_gnn()
        self.policy_params = self.build_policy_network()
        self.value_params = self.build_value_network()

    def build_gnn(self) -> list[dict]:
        """构建 Edge-based GNN。

        学术依据：Gilmer 2017 ICML（消息传递神经网络）
        https://arxiv.org/abs/1704.01212

        每层消息传递：
            h_i^{l+1} = ReLU(W_self @ h_i + (1/|N|) sum_{j in N(i)} (W_neigh @ h_j + W_edge @ e_{ij}) + b)
            + 残差连接（维度一致时）

        Returns:
            GNN 参数列表，每层含 W_self / W_neigh / W_edge / b。
        """
        cfg = self.config
        hidden = cfg.gnn_hidden
        n_layers = cfg.gnn_layers
        in_dim = self.encoder.node_feat_dim + 4  # + 位置特征
        params: list[dict] = []
        for _ in range(n_layers):
            out_dim = hidden
            scale = np.sqrt(2.0 / max(in_dim, 1))
            params.append(
                {
                    "W_self": np.random.randn(in_dim, out_dim) * scale,
                    "W_neigh": np.random.randn(in_dim, out_dim) * scale,
                    "W_edge": np.random.randn(self.encoder.edge_feat_dim, out_dim)
                    * np.sqrt(2.0 / max(self.encoder.edge_feat_dim, 1)),
                    "b": np.zeros(out_dim),
                }
            )
            in_dim = out_dim
        return params

    def build_policy_network(self) -> dict:
        """构建策略网络（MLP + softmax）。

        输入：图嵌入 + 当前器件特征 + 栅格统计
        输出：grid_h × grid_w 个位置的概率分布

        Returns:
            策略网络参数 dict，含 W1 / b1 / W2 / b2。
        """
        cfg = self.config
        hidden = cfg.gnn_hidden
        in_dim = hidden + self.encoder.node_feat_dim + 3  # graph_emb + dev_feat + grid_stats
        out_dim = cfg.grid_size[0] * cfg.grid_size[1]
        return {
            "W1": np.random.randn(in_dim, hidden) * np.sqrt(2.0 / max(in_dim, 1)),
            "b1": np.zeros(hidden),
            "W2": np.random.randn(hidden, out_dim) * np.sqrt(2.0 / max(hidden, 1)),
            "b2": np.zeros(out_dim),
        }

    def build_value_network(self) -> dict:
        """构建价值网络（MLP，标量输出）。

        输入：同策略网络
        输出：标量价值估计（baseline）

        Returns:
            价值网络参数 dict，含 W1 / b1 / W2 / b2。
        """
        cfg = self.config
        hidden = cfg.gnn_hidden
        in_dim = hidden + self.encoder.node_feat_dim + 3
        return {
            "W1": np.random.randn(in_dim, hidden) * np.sqrt(2.0 / max(in_dim, 1)),
            "b1": np.zeros(hidden),
            "W2": np.random.randn(hidden, 1) * np.sqrt(2.0 / max(hidden, 1)),
            "b2": np.zeros(1),
        }

    def _gnn_forward(
        self,
        node_feats: np.ndarray,
        edge_index: np.ndarray,
        edge_feats: np.ndarray,
        gnn_params: list[dict],
    ) -> np.ndarray:
        """GNN 前向消息传递。

        Args:
            node_feats: 节点特征 [N, in_dim]。
            edge_index: 边索引 [2, E]。
            edge_feats: 边特征 [E, edge_feat_dim]。
            gnn_params: GNN 参数列表。

        Returns:
            节点嵌入 [N, hidden]。
        """
        h = node_feats
        n = h.shape[0]
        for layer in gnn_params:
            out_dim = layer["W_self"].shape[1]
            self_msg = h @ layer["W_self"]  # [N, out_dim]
            neigh_msg = h @ layer["W_neigh"]  # [N, out_dim]
            if edge_index.shape[1] > 0 and n > 0:
                srcs = edge_index[0]
                dsts = edge_index[1]
                edge_contrib = edge_feats @ layer["W_edge"]  # [E, out_dim]
                msg = neigh_msg[srcs] + edge_contrib  # [E, out_dim]
                agg = np.zeros((n, out_dim), dtype=np.float64)
                np.add.at(agg, dsts, msg)
                deg = np.zeros(n, dtype=np.float64)
                np.add.at(deg, dsts, 1.0)
                deg = np.maximum(deg, 1.0)
                agg = agg / deg[:, None]
            else:
                agg = np.zeros((n, out_dim), dtype=np.float64)
            new_h = self_msg + agg + layer["b"]
            # 残差连接（维度一致时）
            if h.shape[1] == out_dim:
                new_h = new_h + h
            h = np.maximum(0.0, new_h)  # ReLU
        return h

    def _policy_forward(self, state_vec: np.ndarray, params: dict) -> np.ndarray:
        """策略网络前向传播。

        Args:
            state_vec: 状态向量 [in_dim]。
            params: 策略网络参数。

        Returns:
            动作概率分布 [out_dim]。
        """
        z1 = state_vec @ params["W1"] + params["b1"]
        h = np.maximum(0.0, z1)
        logits = h @ params["W2"] + params["b2"]
        # 稳定 softmax
        shifted = logits - logits.max()
        exp = np.exp(shifted)
        probs = exp / exp.sum()
        return probs

    def _value_forward(self, state_vec: np.ndarray, params: dict) -> float:
        """价值网络前向传播。

        Args:
            state_vec: 状态向量 [in_dim]。
            params: 价值网络参数。

        Returns:
            价值估计（标量）。
        """
        z1 = state_vec @ params["W1"] + params["b1"]
        h = np.maximum(0.0, z1)
        v = (h @ params["W2"] + params["b2"])[0]
        return float(v)

    def _build_occupancy_grid(self, placement: dict, circuit: dict) -> np.ndarray:
        """构建占用栅格。

        Args:
            placement: 布局 dict。
            circuit: 电路描述 dict。

        Returns:
            占用栅格 [grid_h, grid_w]，1 表示已占用。
        """
        grid_h, grid_w = self.config.grid_size
        grid = np.zeros((grid_h, grid_w), dtype=np.float64)
        for dev in circuit["devices"]:
            if dev["id"] not in placement:
                continue
            p = placement[dev["id"]]
            w = float(dev.get("width", 50))
            h = float(dev.get("height", 30))
            gi0 = max(0, int(p["x"] / _GRID_CELL_SIZE))
            gi1 = min(grid_w, int(np.ceil((p["x"] + w) / _GRID_CELL_SIZE)))
            gj0 = max(0, int(p["y"] / _GRID_CELL_SIZE))
            gj1 = min(grid_h, int(np.ceil((p["y"] + h) / _GRID_CELL_SIZE)))
            grid[gj0:gj1, gi0:gi1] = 1.0
        return grid

    def _build_action_mask(self, placement: dict, circuit: dict) -> np.ndarray:
        """构建动作掩码（屏蔽已占用位置）。

        Args:
            placement: 布局 dict。
            circuit: 电路描述 dict。

        Returns:
            动作掩码 [grid_h * grid_w]，0 表示不可用。
        """
        grid_h, grid_w = self.config.grid_size
        mask = np.ones(grid_h * grid_w, dtype=np.float64)
        for dev in circuit["devices"]:
            if dev["id"] not in placement:
                continue
            p = placement[dev["id"]]
            w = float(dev.get("width", 50))
            h = float(dev.get("height", 30))
            gi0 = max(0, int(p["x"] / _GRID_CELL_SIZE))
            gi1 = min(grid_w, int(np.ceil((p["x"] + w) / _GRID_CELL_SIZE)) + 1)
            gj0 = max(0, int(p["y"] / _GRID_CELL_SIZE))
            gj1 = min(grid_h, int(np.ceil((p["y"] + h) / _GRID_CELL_SIZE)) + 1)
            for r in range(gj0, gj1):
                for c in range(gi0, gi1):
                    mask[r * grid_w + c] = 0.0
        return mask

    def _build_state(
        self, placement: dict, circuit: dict, current_dev: dict
    ) -> dict:
        """构建状态。

        状态包含：
        - GNN 编码的图嵌入（mean pooling）
        - 当前器件特征
        - 占用栅格统计特征

        Args:
            placement: 当前布局 dict。
            circuit: 电路描述 dict。
            current_dev: 当前要放置的器件 dict。

        Returns:
            状态 dict，含 ``embedding``、``mask``、``grid``。
        """
        node_feats = self.encoder.encode_placement(placement, circuit)
        graph = self.encoder.encode_circuit(circuit)
        if node_feats.shape[0] > 0:
            embedding = self._gnn_forward(
                node_feats, graph["edge_index"], graph["edge_feats"], self.gnn_params
            )
            graph_emb = embedding.mean(axis=0)
        else:
            graph_emb = np.zeros(self.config.gnn_hidden, dtype=np.float64)
        dev_feat = self.encoder.compute_features(current_dev)
        grid = self._build_occupancy_grid(placement, circuit)
        grid_stats = np.array(
            [grid.mean(), grid.sum(), grid.std()], dtype=np.float64
        )
        state_vec = np.concatenate([graph_emb, dev_feat, grid_stats])
        mask = self._build_action_mask(placement, circuit)
        return {
            "embedding": state_vec,
            "mask": mask,
            "grid": grid,
            "graph_emb": graph_emb,
            "dev_feat": dev_feat,
        }

    def select_action(self, state: dict) -> tuple:
        """选择动作（器件放置位置）。

        Args:
            state: 状态 dict。

        Returns:
            (action, logprob, value) 元组。action 为网格位置索引，
            logprob 为对数概率，value 为价值估计。
        """
        state_vec = state["embedding"]
        probs = self._policy_forward(state_vec, self.policy_params)
        # 应用动作掩码
        mask = state["mask"]
        probs = probs * mask
        total = probs.sum()
        if total > 1e-10:
            probs = probs / total
        else:
            probs = np.ones_like(probs) / len(probs)
        action = int(np.random.choice(len(probs), p=probs))
        logprob = float(np.log(probs[action] + 1e-10))
        value = self._value_forward(state_vec, self.value_params)
        return action, logprob, value

    def compute_reward(self, placement: dict) -> float:
        """计算奖励。

        光子布局奖励 = -α·线长 - β·拥塞 - γ·交叉数 - δ·弯曲违反 - ε·均匀性

        Args:
            placement: 布局 dict。

        Returns:
            奖励值（标量）。
        """
        assert self.circuit is not None, "agent.circuit 未设置"
        result = self.reward.compute(placement, self.circuit)
        return result["reward"]

    def _policy_backward(self, state: dict, action: int) -> dict:
        """策略网络反向传播（返回 ∇log π(a|s)）。

        Args:
            state: 状态 dict。
            action: 选择的动作。

        Returns:
            参数梯度 dict。
        """
        x = state["embedding"]
        params = self.policy_params
        z1 = x @ params["W1"] + params["b1"]
        h = np.maximum(0.0, z1)
        logits = h @ params["W2"] + params["b2"]
        shifted = logits - logits.max()
        exp = np.exp(shifted)
        probs = exp / exp.sum()
        # ∇logits log π(a|s) = e_a - probs
        e_a = np.zeros_like(probs)
        e_a[action] = 1.0
        dlogits = e_a - probs
        # ∇W2 = outer(h, dlogits)，形状 [hidden, out] 与 W2 一致
        dW2 = np.outer(h, dlogits)
        db2 = dlogits
        # ∇h = W2 @ dlogits，形状 [hidden]
        dh = params["W2"] @ dlogits
        dz1 = dh * (z1 > 0)
        # ∇W1 = outer(x, dz1)，形状 [in, hidden] 与 W1 一致
        dW1 = np.outer(x, dz1)
        db1 = dz1
        return {"W1": dW1, "b1": db1, "W2": dW2, "b2": db2}

    def _value_backward(self, state: dict, target: float) -> dict:
        """价值网络反向传播（返回 ∇L_vf，L = (target - v)^2）。

        Args:
            state: 状态 dict。
            target: 目标值（回报）。

        Returns:
            参数梯度 dict。
        """
        x = state["embedding"]
        params = self.value_params
        z1 = x @ params["W1"] + params["b1"]
        h = np.maximum(0.0, z1)
        v = float((h @ params["W2"] + params["b2"])[0])
        # ∇v L = -2 * (target - v)
        dv = -2.0 * (target - v)
        # ∇W2 = outer(h, [dv])，形状 [hidden, 1] 与 W2 一致
        dW2 = np.outer(h, np.array([dv]))
        db2 = np.array([dv])
        # ∇h = dv * W2[:,0]，形状 [hidden]
        dh = dv * params["W2"][:, 0]
        dz1 = dh * (z1 > 0)
        # ∇W1 = outer(x, dz1)，形状 [in, hidden] 与 W1 一致
        dW1 = np.outer(x, dz1)
        db1 = dz1
        return {"W1": dW1, "b1": db1, "W2": dW2, "b2": db2}

    def train(self, circuit: dict) -> dict:
        """训练 AlphaChip agent。

        Args:
            circuit: 电路描述 dict。

        Returns:
            训练历史 dict。
        """
        trainer = AlphaChipTrainer(self, self.config)
        return trainer.train([circuit], n_epochs=10)

    def place(self, circuit: dict) -> dict:
        """使用训练好的 agent 进行布局。

        Args:
            circuit: 电路描述 dict。

        Returns:
            布局 dict，{inst_id: {"x", "y", "rotation"}}。
        """
        self.circuit = circuit
        placement: dict[str, dict] = {}
        grid_h, grid_w = self.config.grid_size
        for dev in circuit["devices"]:
            state = self._build_state(placement, circuit, dev)
            action, _, _ = self.select_action(state)
            row = action // grid_w
            col = action % grid_w
            placement[dev["id"]] = {
                "x": float(col * _GRID_CELL_SIZE),
                "y": float(row * _GRID_CELL_SIZE),
                "rotation": 0,
            }
        return placement


# ---------------------------------------------------------------------------
# 5. AlphaChipTrainer — AlphaChip 训练器
# ---------------------------------------------------------------------------


class AlphaChipTrainer:
    """AlphaChip 训练器。

    学术依据：PPO 算法（Schulman 2017 arXiv:1707.06347）
    本模块使用简化版 REINFORCE + baseline（Sutton & Barto 2018 §13），
    保持轻量（纯 numpy 实现，不依赖 PyTorch）。

    REINFORCE + baseline 策略梯度：
        ∇J = E[∇log π(a|s) · (R_t - V(s_t))]
    价值回归：
        L_vf = (R_t - V(s_t))²
    """

    def __init__(self, agent: AlphaChipAgent, config: AlphaChipConfig) -> None:
        """初始化训练器。

        Args:
            agent: AlphaChip agent。
            config: AlphaChip 配置。
        """
        self.agent = agent
        self.config = config

    def collect_trajectory(self, circuit: dict) -> dict:
        """收集一条轨迹。

        顺序放置所有器件，记录每步的状态、动作、奖励、对数概率、价值。

        Args:
            circuit: 电路描述 dict。

        Returns:
            轨迹 dict，含 states / actions / rewards / logprobs / values /
            final_reward / placement。
        """
        self.agent.circuit = circuit
        placement: dict[str, dict] = {}
        grid_h, grid_w = self.config.grid_size
        trajectory: dict[str, list] = {
            "states": [],
            "actions": [],
            "rewards": [],
            "logprobs": [],
            "values": [],
        }
        prev_reward = 0.0
        for dev in circuit["devices"]:
            state = self.agent._build_state(placement, circuit, dev)
            action, logprob, value = self.agent.select_action(state)
            row = action // grid_w
            col = action % grid_w
            placement[dev["id"]] = {
                "x": float(col * _GRID_CELL_SIZE),
                "y": float(row * _GRID_CELL_SIZE),
                "rotation": 0,
            }
            # 增量奖励（当前布局总奖励 - 上一步）
            cur_reward = self.agent.compute_reward(placement)
            step_reward = cur_reward - prev_reward
            prev_reward = cur_reward
            trajectory["states"].append(state)
            trajectory["actions"].append(action)
            trajectory["rewards"].append(float(step_reward))
            trajectory["logprobs"].append(logprob)
            trajectory["values"].append(value)
        final_reward = self.agent.compute_reward(placement)
        trajectory["final_reward"] = float(final_reward)
        trajectory["placement"] = placement
        return trajectory

    def update_policy(self, trajectories: list) -> dict:
        """REINFORCE + baseline 策略更新。

        Args:
            trajectories: 轨迹列表。

        Returns:
            训练指标 dict，含 policy_loss / value_loss / n_updates。
        """
        lr = self.config.learning_rate
        gamma = self.config.gamma
        total_policy_loss = 0.0
        total_value_loss = 0.0
        n_updates = 0
        for traj in trajectories:
            rewards = traj["rewards"]
            values = traj["values"]
            actions = traj["actions"]
            states = traj["states"]
            logprobs = traj["logprobs"]
            n = len(rewards)
            if n == 0:
                continue
            # 计算回报（累积奖励，从后往前）
            returns = np.zeros(n, dtype=np.float64)
            g = 0.0
            for t in range(n - 1, -1, -1):
                g = rewards[t] + gamma * g
                returns[t] = g
            # 计算优势
            advantages = returns - np.array(values, dtype=np.float64)
            # 标准化优势
            adv_std = advantages.std()
            if adv_std > 1e-8:
                advantages = (advantages - advantages.mean()) / (adv_std + 1e-8)
            # 策略梯度 + 价值回归更新
            for t in range(n):
                state = states[t]
                action = actions[t]
                advantage = float(advantages[t])
                # 策略梯度上升
                policy_grads = self.agent._policy_backward(state, action)
                for name, grad in policy_grads.items():
                    self.agent.policy_params[name] += lr * advantage * grad
                # 价值回归下降
                value_grads = self.agent._value_backward(state, float(returns[t]))
                for name, grad in value_grads.items():
                    self.agent.value_params[name] -= lr * grad
                total_policy_loss += -logprobs[t] * advantage
                total_value_loss += (float(returns[t]) - values[t]) ** 2
                n_updates += 1
        if n_updates == 0:
            return {"policy_loss": 0.0, "value_loss": 0.0, "n_updates": 0}
        return {
            "policy_loss": float(total_policy_loss / n_updates),
            "value_loss": float(total_value_loss / n_updates),
            "n_updates": n_updates,
        }

    def train(self, circuits: list, n_epochs: int = 100) -> dict:
        """训练 agent。

        Args:
            circuits: 电路列表。
            n_epochs: 训练轮数。

        Returns:
            训练历史 dict，含 epoch / reward / policy_loss / value_loss。
        """
        history: dict[str, list] = {
            "epoch": [],
            "reward": [],
            "policy_loss": [],
            "value_loss": [],
        }
        for epoch in range(n_epochs):
            trajectories = [self.collect_trajectory(c) for c in circuits]
            metrics = self.update_policy(trajectories)
            avg_reward = float(np.mean([t["final_reward"] for t in trajectories]))
            history["epoch"].append(epoch)
            history["reward"].append(avg_reward)
            history["policy_loss"].append(metrics["policy_loss"])
            history["value_loss"].append(metrics["value_loss"])
        return history

    def evaluate(self, circuit: dict) -> dict:
        """评估布局质量。

        Args:
            circuit: 电路描述 dict。

        Returns:
            评估结果 dict，含 placement / reward / 各项指标。
        """
        placement = self.agent.place(circuit)
        reward_result = self.agent.reward.compute(placement, circuit)
        return {
            "placement": placement,
            "reward": reward_result["reward"],
            **reward_result,
        }


__all__ = [
    "AlphaChipConfig",
    "PhotonicPlacementEncoder",
    "PhotonicPlacementReward",
    "AlphaChipAgent",
    "AlphaChipTrainer",
]
