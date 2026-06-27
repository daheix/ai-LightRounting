"""R34: AlphaChip 预训练-微调范式 — 预训练数据集构建。

从 pretrain.py 拆分（facade 模式，保持外部 import 路径不变）。

复刻 AlphaChip 预训练数据集构建流程：按 platform × circuit_template × variant_id
组合生成 100+ 电路变体，注入平台物理参数并构建图特征供 GNN 预训练。

纯 NumPy/CPU 实现（🚫不参与 GPU，R04 战略决策）。

来源:
- Mirhoseini et al., Nature 2021, AlphaChip 预训练数据集
  https://www.nature.com/articles/s41586-021-03544-w
- Circuit Training Pre-training Guide
  https://github.com/google-research/circuit_training/blob/main/docs/PRETRAINING.md
- Goldie et al., arXiv 2024, 预训练必要性辩护
  https://arxiv.org/abs/2411.10053
- SiEPIC EBeam PDK (SOI 平台参数)
  https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- Ligentec TriPleX (SiN 平台参数)
  https://www.ligentec.com/
- HyperLight (LNOI 平台参数)
  https://www.hyperlightcorp.com/
- InP 平台参数
  https://pattern-project.eu/technology/material-platforms/inp-platform/
"""

from __future__ import annotations

import logging
import math
import random
from dataclasses import dataclass

import numpy as np

from polaris.data.specs import CircuitSpec, DeviceSpec
from polaris.data.variant_generator import (
    _scale_mzi_lattice,
    _scale_random_circuit,
    _scale_splitter_tree,
    _scale_switch_chain,
)
from polaris.trainer.pretrain_constants import (
    ALL_PLATFORMS,
    CIRCUIT_TEMPLATES,
    PLATFORM_PHYSICAL_PARAMS,
    PLATFORM_SOI,
)

logger = logging.getLogger(__name__)


# =============================================================================
# 预训练样本数据类
# =============================================================================


@dataclass
class PretrainSample:
    """单个预训练样本（电路 + 平台 + 图特征）。

    Attributes:
        circuit_name: 电路名称。
        platform: 工艺平台（SOI/SiN/InP/LNOI）。
        n_devices: 器件数。
        node_feats: 节点特征矩阵 [N, node_feat_dim]。
        edge_index: 边索引 [2, E]。
        edge_feats: 边特征矩阵 [E, edge_feat_dim]。
        placements: 放置位置 {device_name: {"x", "y", "w", "h"}}。
        circuit_type: 电路模板类型。
        variant_id: 变体编号。
    """

    circuit_name: str
    platform: str
    n_devices: int
    node_feats: np.ndarray
    edge_index: np.ndarray
    edge_feats: np.ndarray
    placements: dict
    circuit_type: str = "random"
    variant_id: int = 0


# =============================================================================
# 预训练数据集构建（R34.md §7.1: 100+ 电路变体 + 四平台覆盖）
# =============================================================================


class PretrainDataset:
    """预训练数据集（100+ 电路变体，覆盖 SOI/SiN/InP/LNOI 四平台）。

    复刻 AlphaChip 预训练数据集构建流程：收集多个 netlist，标注平台物理参数，
    生成图特征供 GNN 预训练。

    来源:
    - Mirhoseini et al., Nature 2021, AlphaChip 预训练数据集
      https://www.nature.com/articles/s41586-021-03544-w
    - Circuit Training Pre-training Guide
      https://github.com/google-research/circuit_training/blob/main/docs/PRETRAINING.md

    Attributes:
        samples: 预训练样本列表。
        platforms: 覆盖的平台列表。
        n_per_platform: 每个平台的变体数。
    """

    def __init__(
        self,
        n_per_platform: int = 25,
        platforms: tuple[str, ...] = ALL_PLATFORMS,
        seed: int = 42,
    ) -> None:
        """初始化预训练数据集。

        Args:
            n_per_platform: 每个平台的变体数（默认 25，4 平台共 100 变体）。
            platforms: 覆盖的平台列表（默认四平台）。
            seed: 随机种子（可复现）。
        """
        self.n_per_platform = n_per_platform
        self.platforms = platforms
        self.seed = seed
        self.samples: list[PretrainSample] = []

    def generate(self) -> list[PretrainSample]:
        """生成预训练数据集。

        按 platform × circuit_template × variant_id 组合生成变体，
        每个变体注入平台物理参数并构建图特征。

        Returns:
            预训练样本列表。
        """
        self.samples = []
        rng = random.Random(self.seed)
        for platform in self.platforms:
            if platform not in PLATFORM_PHYSICAL_PARAMS:
                raise ValueError(f"未知平台: {platform}，支持: {ALL_PLATFORMS}")
            for variant_id in range(self.n_per_platform):
                template = CIRCUIT_TEMPLATES[variant_id % len(CIRCUIT_TEMPLATES)]
                sample = self._build_one_sample(platform, template, variant_id, rng)
                self.samples.append(sample)
        logger.info(
            "预训练数据集生成完成: %d 平台 × %d 变体 = %d 样本",
            len(self.platforms),
            self.n_per_platform,
            len(self.samples),
        )
        return self.samples

    def _build_one_sample(
        self,
        platform: str,
        template: str,
        variant_id: int,
        rng: random.Random,
    ) -> PretrainSample:
        """构建单个预训练样本。

        Args:
            platform: 工艺平台。
            template: 电路模板类型。
            variant_id: 变体编号。
            rng: 随机数生成器。

        Returns:
            预训练样本。
        """
        seed = rng.randint(0, 2**31 - 1)
        n_devices = self._sample_n_devices(variant_id, rng)
        circuit = self._build_circuit(template, n_devices, seed)
        circuit.name = f"{platform}_{template}_v{variant_id}"
        circuit.process_node = platform
        # 注入平台物理参数到电路
        self._inject_platform_params(circuit, platform)
        # 生成放置布局
        placements = self._generate_placements(circuit, seed)
        # 构建图特征
        node_feats = self._build_node_features(circuit, placements)
        edge_index = self._build_edge_index(circuit)
        edge_feats = self._build_edge_features(circuit, placements, edge_index, platform)
        return PretrainSample(
            circuit_name=circuit.name,
            platform=platform,
            n_devices=len(circuit.devices),
            node_feats=node_feats,
            edge_index=edge_index,
            edge_feats=edge_feats,
            placements=placements,
            circuit_type=template,
            variant_id=variant_id,
        )

    def _sample_n_devices(self, variant_id: int, rng: random.Random) -> int:
        """采样器件数（5-100，覆盖 R34.md §7.1 要求）。"""
        # 按变体 ID 分档：5/10/20/50/100 节点（课程学习友好）
        levels = [5, 10, 20, 50, 100]
        base = levels[variant_id % len(levels)]
        # 随机扰动 ±20%
        jitter = rng.randint(-max(1, base // 5), max(1, base // 5))
        return max(5, base + jitter)

    def _build_circuit(self, template: str, n_devices: int, seed: int) -> CircuitSpec:
        """根据模板构建电路。

        Args:
            template: 电路模板类型。
            n_devices: 目标器件数。
            seed: 随机种子。

        Returns:
            电路规格。
        """
        if template == "mzi_lattice":
            # mzi_lattice 器件数 = 2*stages + 2（gc_in + gc_out + stages*(dc+wg)）
            stages = max(1, (n_devices - 2) // 2)
            return _scale_mzi_lattice(stages)
        if template == "splitter_tree":
            # splitter_tree 总器件数 ≈ 2^(levels+1)，限制 levels 使器件数在 [5, n_devices]
            # levels=2 → 10 器件（最小满足 §7.1 的 5 节点要求）
            levels = max(2, int(math.log2(max(4, n_devices // 2))))
            return _scale_splitter_tree(levels)
        if template == "switch_chain":
            return _scale_switch_chain(max(1, n_devices - 2))
        if template == "random":
            return _scale_random_circuit(n_devices, seed=seed)
        raise ValueError(f"未知电路模板: {template}，支持: {CIRCUIT_TEMPLATES}")

    def _inject_platform_params(self, circuit: CircuitSpec, platform: str) -> None:
        """将平台物理参数注入电路器件的 params 字典。

        Args:
            circuit: 电路规格（原地修改）。
            platform: 工艺平台。
        """
        params = PLATFORM_PHYSICAL_PARAMS[platform]
        for dev in circuit.devices:
            dev.params["platform"] = platform
            dev.params["n_eff"] = params["n_eff"]
            dev.params["waveguide_loss_db_cm"] = params["waveguide_loss_db_cm"]
            dev.params["min_bend_radius_um"] = params["min_bend_radius_um"]
            dev.params["wavelength_nm"] = params["wavelength_nm"]

    def _generate_placements(self, circuit: CircuitSpec, seed: int) -> dict:
        """生成放置布局（复用 dataset_generator.generate_layout）。

        Args:
            circuit: 电路规格。
            seed: 随机种子。

        Returns:
            放置布局字典 {device_name: {"x", "y", "w", "h"}}。
        """
        from polaris.data.dataset_generator import generate_layout

        return generate_layout(circuit, seed=seed)

    def _build_node_features(
        self,
        circuit: CircuitSpec,
        placements: dict,
    ) -> np.ndarray:
        """构建节点特征矩阵。

        特征: [width_norm, height_norm, area_norm, n_ports_norm, placed_flag,
               platform_id_onehot(4), category_id]
        维度: 5 + 4 + 1 = 10

        Args:
            circuit: 电路规格。
            placements: 放置布局。

        Returns:
            节点特征矩阵 [N, 10]。
        """
        platform_idx = ALL_PLATFORMS.index(circuit.process_node or PLATFORM_SOI)
        platform_onehot = np.zeros(len(ALL_PLATFORMS), dtype=np.float64)
        platform_onehot[platform_idx] = 1.0
        cat_map = {"passive": 0, "active": 1, "source": 2, "detector": 3}
        feats = []
        canvas_w = max(circuit.canvas_w, 1.0)
        canvas_h = max(circuit.canvas_h, 1.0)
        for dev in circuit.devices:
            w = dev.width_um / canvas_w
            h = dev.height_um / canvas_h
            area = (dev.width_um * dev.height_um) / (canvas_w * canvas_h)
            n_ports = len(dev.ports) / 20.0
            placed = 1.0 if dev.name in placements else 0.0
            cat = cat_map.get(self._infer_category(dev), 0)
            feat = np.concatenate(
                [
                    np.array([w, h, area, n_ports, placed], dtype=np.float64),
                    platform_onehot,
                    np.array([cat], dtype=np.float64),
                ]
            )
            feats.append(feat)
        return np.stack(feats) if feats else np.zeros((0, 10), dtype=np.float64)

    def _infer_category(self, dev: DeviceSpec) -> str:
        """根据器件类型推断类别。"""
        dt = dev.device_type.lower()
        if "gc" in dt or "grating" in dt:
            return "source"
        if "detector" in dt or "pd" in dt:
            return "detector"
        if "heater" in dt or "modulator" in dt:
            return "active"
        return "passive"

    def _build_edge_index(self, circuit: CircuitSpec) -> np.ndarray:
        """构建边索引 [2, E]（无向图双向边）。

        Args:
            circuit: 电路规格。

        Returns:
            边索引数组 [2, E]。
        """
        name_to_idx = {d.name: i for i, d in enumerate(circuit.devices)}
        edges = []
        for dev1, _port1, dev2, _port2 in circuit.connections:
            if dev1 in name_to_idx and dev2 in name_to_idx:
                i, j = name_to_idx[dev1], name_to_idx[dev2]
                edges.append([i, j])
                edges.append([j, i])
        if not edges:
            return np.zeros((2, 0), dtype=np.int64)
        return np.array(edges).T

    def _build_edge_features(
        self,
        circuit: CircuitSpec,
        placements: dict,
        edge_index: np.ndarray,
        platform: str,
    ) -> np.ndarray:
        """构建边特征矩阵。

        特征: [distance_norm, n_eff_diff, loss_db_cm, wavelength_band_onehot(3),
               net_relation_onehot(3)]
        维度: 1 + 1 + 1 + 3 + 3 = 9

        Args:
            circuit: 电路规格。
            placements: 放置布局。
            edge_index: 边索引 [2, E]。
            platform: 工艺平台。

        Returns:
            边特征矩阵 [E, 9]。
        """
        n_edges = edge_index.shape[1]
        params = PLATFORM_PHYSICAL_PARAMS[platform]
        # C-band onehot（简化：所有平台用 C-band）
        band_onehot = np.array([1.0, 0.0, 0.0], dtype=np.float64)  # C-band
        feats = np.zeros((n_edges, 9), dtype=np.float64)
        for i in range(n_edges):
            src_idx, dst_idx = edge_index[0, i], edge_index[1, i]
            src_dev = circuit.devices[src_idx]
            dst_dev = circuit.devices[dst_idx]
            # 距离
            src_place = placements.get(src_dev.name, {"x": 0, "y": 0})
            dst_place = placements.get(dst_dev.name, {"x": 0, "y": 0})
            dx = src_place.get("x", 0) - dst_place.get("x", 0)
            dy = src_place.get("y", 0) - dst_place.get("y", 0)
            dist = math.sqrt(dx * dx + dy * dy)
            dist_norm = dist / max(circuit.canvas_w, 1.0)
            # 折射率差（同平台为 0）
            n_eff_diff = 0.0
            # 损耗
            loss = params["waveguide_loss_db_cm"] * dist_norm * 10.0  # 转换为 dB
            # net 关系（简化：均为光波导）
            relation_onehot = np.array([1.0, 0.0, 0.0], dtype=np.float64)
            feats[i] = np.concatenate(
                [
                    np.array([dist_norm, n_eff_diff, loss], dtype=np.float64),
                    band_onehot,
                    relation_onehot,
                ]
            )
        return feats

    def __len__(self) -> int:
        return len(self.samples)

    def get_by_platform(self, platform: str) -> list[PretrainSample]:
        """按平台筛选样本。

        Args:
            platform: 工艺平台。

        Returns:
            该平台的样本列表。
        """
        return [s for s in self.samples if s.platform == platform]


__all__ = [
    "PretrainDataset",
    "PretrainSample",
]
