"""R34-R35 路标：光子布局状态编码器。

本模块从 ``alpha_chip.py`` 拆分而来（facade 模式），提供
``PhotonicPlacementEncoder``，将光子电路编码为 GNN 可处理的图结构。
外部 import 路径保持不变（``from polaris.rl.alpha_chip import
PhotonicPlacementEncoder``）。

## 学术依据

- AlphaChip 状态编码（Mirhoseini 2024 Nature）
  https://doi.org/10.1038/s41586-024-07714-9
- Mirhoseini et al., Nature 2021, "A graph placement methodology for fast
  chip design" DOI: 10.1038/s41586-021-03544-w
- Gilmer et al., 2017, MPNN（消息传递神经网络）:
  https://arxiv.org/abs/1704.01212
- SiEPIC EBeam PDK 标准器件类型:
  https://github.com/SiEPIC/SiEPIC_EBeam_PDK

## 【创新】光子电路图编码

AlphaChip 原为电子 IC 布局设计，本模块将其扩展到光子 IC 布局：
- 电子 IC 节点特征为标准单元宏参数
- 光子 IC 节点特征增加端口数（光子器件端口数差异大，MZI 4 端口 vs Ring 2 端口）
- 边特征增加目标长度（光子波导需相位匹配，目标长度是关键约束）

## 来源

- 拆分自: ``src/polaris/rl/alpha_chip.py``（原文件 1096 行 → 拆分后 ≤800 行）
- 路标: R34-R35
- 架构统一: D05 Task 10


## 补充文献（R02 学术诚信补齐）
- Chrostowski & Hochberg, "Silicon Photonics Design", CUP 2015, ISBN 978-1-107-08345-6: https://www.cambridge.org/9781107083456
- gdsfactory PDK 文档: https://gdsfactory.github.io/gdsfactory/notebooks/09_pdk_import.html
- Luceda IPKISS: https://www.lucedaphotonics.com/en/products/ipkiss
"""

from __future__ import annotations

import numpy as np

from polaris.rl.alpha_chip_config import _DEVICE_TYPES, _NET_TYPES


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


__all__ = ["PhotonicPlacementEncoder"]
