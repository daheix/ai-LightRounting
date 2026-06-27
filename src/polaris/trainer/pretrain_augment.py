"""R34: AlphaChip 预训练-微调范式 — 数据增强。

从 pretrain.py 拆分（facade 模式，保持外部 import 路径不变）。

对预训练样本施加水平镜像 + 旋转，扩充数据集 4 倍。
增强方式：原图 + 水平镜像 + 90° 旋转 + 180° 旋转。

纯 NumPy/CPU 实现（🚫不参与 GPU，R04 战略决策）。

来源:
- GraphCL (You et al., NeurIPS 2020) 图对比学习数据增强
  https://arxiv.org/abs/2010.13902
- 图像数据增强标准做法（翻转/旋转）
- Mirhoseini et al., Nature 2021, AlphaChip 预训练范式
  https://www.nature.com/articles/s41586-021-03544-w
- Circuit Training Pre-training Guide
  https://github.com/google-research/circuit_training/blob/main/docs/PRETRAINING.md
- Goldie et al., arXiv 2024, 预训练必要性辩护
  https://arxiv.org/abs/2411.10053
"""

from __future__ import annotations

from polaris.trainer.pretrain_dataset import PretrainSample

# =============================================================================
# 数据增强（R34.md §7.1: 镜像/旋转 4× 扩充）
# =============================================================================


class DataAugmentor:
    """数据增强器（镜像/旋转 4× 扩充）。

    对预训练样本施加水平镜像 + 旋转，扩充数据集 4 倍。
    增强方式：原图 + 水平镜像 + 90° 旋转 + 180° 旋转。

    来源:
    - GraphCL (You et al., NeurIPS 2020) 图对比学习数据增强
      https://arxiv.org/abs/2010.13902
    - 图像数据增强标准做法（翻转/旋转）
    """

    def __init__(self, canvas_w: float = 1000.0, canvas_h: float = 1000.0) -> None:
        """初始化数据增强器。

        Args:
            canvas_w: 画布宽度（μm）。
            canvas_h: 画布高度（μm）。
        """
        self.canvas_w = canvas_w
        self.canvas_h = canvas_h

    def augment(self, sample: PretrainSample) -> list[PretrainSample]:
        """对样本施加 4× 数据增强。

        Args:
            sample: 原始样本。

        Returns:
            4 个增强样本（含原图）。
        """
        original = self._copy_sample(sample, suffix="orig")
        hflip = self._horizontal_flip(sample)
        rot90 = self._rotate(sample, 90)
        rot180 = self._rotate(sample, 180)
        return [original, hflip, rot90, rot180]

    def _copy_sample(self, sample: PretrainSample, suffix: str) -> PretrainSample:
        """复制样本（附加后缀）。"""
        return PretrainSample(
            circuit_name=f"{sample.circuit_name}_{suffix}",
            platform=sample.platform,
            n_devices=sample.n_devices,
            node_feats=sample.node_feats.copy(),
            edge_index=sample.edge_index.copy(),
            edge_feats=sample.edge_feats.copy(),
            placements={k: dict(v) for k, v in sample.placements.items()},
            circuit_type=sample.circuit_type,
            variant_id=sample.variant_id,
        )

    def _horizontal_flip(self, sample: PretrainSample) -> PretrainSample:
        """水平镜像：x → canvas_w - x。

        Args:
            sample: 原始样本。

        Returns:
            镜像后的样本。
        """
        flipped = self._copy_sample(sample, "hflip")
        for _dev_name, place in flipped.placements.items():
            place["x"] = self.canvas_w - place.get("x", 0)
        # 边特征中的距离保持不变（镜像不改变距离）
        return flipped

    def _rotate(self, sample: PretrainSample, angle_deg: int) -> PretrainSample:
        """旋转 90/180/270 度。

        Args:
            sample: 原始样本。
            angle_deg: 旋转角度（90/180/270）。

        Returns:
            旋转后的样本。

        Raises:
            ValueError: 角度不在 0/90/180/270 中。
        """
        if angle_deg not in (0, 90, 180, 270):
            raise ValueError(f"仅支持 0/90/180/270 度旋转，得到 {angle_deg}")
        rotated = self._copy_sample(sample, f"rot{angle_deg}")
        if angle_deg == 0:
            return rotated
        for _dev_name, place in rotated.placements.items():
            x, y = place.get("x", 0), place.get("y", 0)
            if angle_deg == 90:
                new_x, new_y = -y, x
            elif angle_deg == 180:
                new_x, new_y = -x, -y
            else:  # 270
                new_x, new_y = y, -x
            # 平移到正坐标
            place["x"] = new_x + self.canvas_w / 2
            place["y"] = new_y + self.canvas_h / 2
        return rotated


__all__ = [
    "DataAugmentor",
]
