"""专家示范数据集加载器（Behavior Cloning 用）。

从 ``data/expert_demos/`` 加载 SiEPIC 真实 GDS 提取的专家布局三元组
(netlist + placements + routes)，转换为 (obs, action) 对供 BC 预训练使用。

观测格式（扁平向量，与 PPOAgent 兼容）:
- 当前器件特征 [type_onehot(8), width_norm, height_norm, n_ports_norm]
- 已放置器件摘要 [n_placed_norm, bbox_xmin_norm, bbox_ymin_norm, bbox_xmax_norm, bbox_ymax_norm]
- 共 8 + 2 + 1 + 5 = 16 维（固定）

动作格式（连续，与 PPOAgent 连续动作兼容）:
- [x_norm, y_norm, rot_norm] ∈ [0, 1]
- x_norm = x / canvas_w, y_norm = y / canvas_h, rot_norm = rotation / 270

来源:
- SiEPIC_EBeam_PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK (MIT, UBC)
- Behavior Cloning: Pomerleau, "ALVINN: An Autonomous Land Vehicle in a Neural Network",
  NeurIPS 1989, https://papers.nips.cc/paper/95-alvinn-an-autonomous-land-vehicle-in-a-neural-network
- DAgger: Ross et al., "A Reduction of Imitation Learning to No-Regret Online Learning",
  AISTATS 2011, https://arxiv.org/abs/1011.0686


## 补充文献（R02 学术诚信补齐）
- Chrostowski & Hochberg, "Silicon Photonics Design", CUP 2015, ISBN 978-1-107-08345-6: https://www.cambridge.org/9781107083456
- gdsfactory PDK 文档: https://gdsfactory.github.io/gdsfactory/notebooks/09_pdk_import.html
- Luceda IPKISS: https://www.lucedaphotonics.com/en/products/ipkiss
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)


# 器件类型 one-hot 编码（8 类，覆盖 SiEPIC PDK 主要器件）
_DEVICE_TYPES = (
    "y_branch",
    "mzi",
    "ring",
    "dc",
    "mmi",
    "grating_coupler",
    "crossing",
    "waveguide",
)
_TYPE_TO_IDX = {t: i for i, t in enumerate(_DEVICE_TYPES)}

# 观测维度（固定）：8(type onehot) + 2(width, height) + 1(n_ports) + 5(placed summary) = 16
OBS_DIM = 16
# 动作维度（x_norm, y_norm, rot_norm）
ACTION_DIM = 3


def _device_type_to_onehot(device_type: str) -> np.ndarray:
    """将器件类型转为 one-hot 编码（8 维）。"""
    vec = np.zeros(len(_DEVICE_TYPES), dtype=np.float32)
    # 模糊匹配：包含关键词即归类
    key = device_type.lower()
    matched = False
    for t in _DEVICE_TYPES:
        if t in key:
            vec[_TYPE_TO_IDX[t]] = 1.0
            matched = True
            break
    if not matched:
        # 未知类型默认归到 waveguide
        vec[_TYPE_TO_IDX["waveguide"]] = 1.0
    return vec


def _normalize_placement(
    place: dict,
    canvas_w: float,
    canvas_h: float,
) -> np.ndarray:
    """将专家放置 (x, y, rotation) 归一化为 [0, 1] 动作向量。"""
    x_norm = float(place["x"]) / canvas_w if canvas_w > 0 else 0.0
    y_norm = float(place["y"]) / canvas_h if canvas_h > 0 else 0.0
    rot_norm = float(place["rotation"]) / 270.0 if place.get("rotation", 0) else 0.0
    # 裁剪到 [0, 1]
    x_norm = float(np.clip(x_norm, 0.0, 1.0))
    y_norm = float(np.clip(y_norm, 0.0, 1.0))
    rot_norm = float(np.clip(rot_norm, 0.0, 1.0))
    return np.array([x_norm, y_norm, rot_norm], dtype=np.float32)


def _build_obs(
    device: dict,
    placed_summary: dict,
    canvas_w: float,
    canvas_h: float,
) -> np.ndarray:
    """构建单个放置步的观测向量（15 维）。

    Args:
        device: 当前待放置器件 dict（含 device_type/width_um/height_um/ports）。
        placed_summary: 已放置器件摘要 {n_placed, bbox}。
        canvas_w: 画布宽度 (μm)。
        canvas_h: 画布高度 (μm)。

    Returns:
        15 维观测向量。
    """
    type_onehot = _device_type_to_onehot(device.get("device_type", "waveguide"))
    width_norm = float(device.get("width_um", 10.0)) / max(canvas_w, 1.0)
    height_norm = float(device.get("height_um", 10.0)) / max(canvas_h, 1.0)
    n_ports = len(device.get("ports", []))
    n_ports_norm = float(n_ports) / 20.0  # 归一化（SiEPIC 器件端口数 2-40）

    # 已放置器件摘要
    n_placed = placed_summary.get("n_placed", 0)
    n_placed_norm = float(n_placed) / 20.0
    bbox = placed_summary.get("bbox") or [0.0, 0.0, 0.0, 0.0]
    bbox_xmin_norm = float(bbox[0]) / max(canvas_w, 1.0)
    bbox_ymin_norm = float(bbox[1]) / max(canvas_h, 1.0)
    bbox_xmax_norm = float(bbox[2]) / max(canvas_w, 1.0)
    bbox_ymax_norm = float(bbox[3]) / max(canvas_h, 1.0)

    obs = np.concatenate(
        [
            type_onehot,  # 8
            np.array([width_norm, height_norm], dtype=np.float32),  # 2
            np.array([n_ports_norm], dtype=np.float32),  # 1
            np.array(
                [n_placed_norm, bbox_xmin_norm, bbox_ymin_norm, bbox_xmax_norm, bbox_ymax_norm],
                dtype=np.float32,
            ),  # 5
        ]
    )
    return obs.astype(np.float32)


def _update_placed_summary(
    summary: dict,
    place: dict,
) -> dict:
    """根据新放置的器件更新已放置器件摘要。"""
    n_placed = summary.get("n_placed", 0) + 1
    bbox = summary.get("bbox", None)
    place_bbox = place.get("bbox", [place["x"], place["y"], place["x"], place["y"]])
    if bbox is None:
        new_bbox = list(place_bbox[:4])
    else:
        new_bbox = [
            min(bbox[0], place_bbox[0]),
            min(bbox[1], place_bbox[1]),
            max(bbox[2], place_bbox[2]),
            max(bbox[3], place_bbox[3]),
        ]
    return {"n_placed": n_placed, "bbox": new_bbox}


class ExpertDataset:
    """专家示范数据集（Behavior Cloning 用）。

    从 ``data/expert_demos/`` 加载真实 SiEPIC GDS 提取的专家布局，
    转换为 (obs, action) 对供 BC 预训练。

    来源:
    - SiEPIC_EBeam_PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK (MIT, UBC)
    - BC 方法: Pomerleau, NeurIPS 1989, ALVINN
      https://papers.nips.cc/paper/95-alvinn-an-autonomous-land-vehicle-in-a-neural-network

    Attributes:
        data_dir: 专家示范数据目录。
        obs_list: 观测向量列表 [N, OBS_DIM]。
        action_list: 动作向量列表 [N, ACTION_DIM]。
        meta_list: 每条样本的元信息（来源 GDS 名、步索引）。
    """

    def __init__(self, data_dir: str | Path = "data/expert_demos") -> None:
        self.data_dir = Path(data_dir)
        self.obs_list: list[np.ndarray] = []
        self.action_list: list[np.ndarray] = []
        self.meta_list: list[dict] = []
        self._loaded = False

    def load(self) -> None:
        """加载所有专家示范数据。"""
        if self._loaded:
            return
        if not self.data_dir.exists():
            logger.warning("专家示范目录不存在: %s", self.data_dir)
            self._loaded = True
            return

        index_path = self.data_dir / "index.json"
        if index_path.exists():
            index = json.loads(index_path.read_text(encoding="utf-8"))
            record_names = [r["name"] for r in index.get("records", [])]
        else:
            record_names = [d.name for d in self.data_dir.iterdir() if d.is_dir()]

        total_samples = 0
        for name in record_names:
            sample_dir = self.data_dir / name
            if not sample_dir.exists():
                continue
            n = self._load_one(sample_dir, name)
            total_samples += n

        logger.info(
            "专家示范加载完成: %d 个 GDS, %d 条 (obs, action) 对",
            len(record_names),
            total_samples,
        )
        self._loaded = True

    def _load_one(self, sample_dir: Path, name: str) -> int:
        """加载单个专家示范 GDS 的数据。"""
        netlist_path = sample_dir / "netlist.json"
        placements_path = sample_dir / "placements.json"
        if not netlist_path.exists() or not placements_path.exists():
            return 0

        netlist = json.loads(netlist_path.read_text(encoding="utf-8"))
        placements = json.loads(placements_path.read_text(encoding="utf-8"))

        canvas_w = float(netlist.get("canvas_w", 1000.0))
        canvas_h = float(netlist.get("canvas_h", 1000.0))
        devices = netlist.get("devices", [])
        if not devices:
            return 0

        # 按器件名顺序构建放置序列
        placed_summary: dict = {"n_placed": 0, "bbox": None}
        n_samples = 0
        for dev in devices:
            dev_name = dev.get("name", "")
            if dev_name not in placements:
                continue
            place = placements[dev_name]
            obs = _build_obs(dev, placed_summary, canvas_w, canvas_h)
            action = _normalize_placement(place, canvas_w, canvas_h)
            self.obs_list.append(obs)
            self.action_list.append(action)
            self.meta_list.append({"source": name, "device": dev_name, "step": n_samples})
            placed_summary = _update_placed_summary(placed_summary, place)
            n_samples += 1
        return n_samples

    def __len__(self) -> int:
        if not self._loaded:
            self.load()
        return len(self.obs_list)

    def get_all(self) -> tuple[np.ndarray, np.ndarray]:
        """返回全部 (obs, action) 数据。

        Returns:
            (obs_array [N, OBS_DIM], action_array [N, ACTION_DIM])。
        """
        if not self._loaded:
            self.load()
        if not self.obs_list:
            return (
                np.zeros((0, OBS_DIM), dtype=np.float32),
                np.zeros((0, ACTION_DIM), dtype=np.float32),
            )
        return (
            np.stack(self.obs_list),
            np.stack(self.action_list),
        )

    def iter_batches(
        self,
        batch_size: int = 32,
        shuffle: bool = True,
        seed: int | None = None,
    ):
        """迭代批量数据。

        Args:
            batch_size: 批量大小。
            shuffle: 是否打乱顺序。
            seed: 随机种子（可复现）。

        Yields:
            (obs_batch [B, OBS_DIM], action_batch [B, ACTION_DIM])。
        """
        if not self._loaded:
            self.load()
        n = len(self.obs_list)
        if n == 0:
            return
        indices = np.arange(n)
        if shuffle:
            rng = np.random.default_rng(seed)
            rng.shuffle(indices)
        for start in range(0, n, batch_size):
            end = min(start + batch_size, n)
            idx = indices[start:end]
            obs_batch = np.stack([self.obs_list[i] for i in idx])
            action_batch = np.stack([self.action_list[i] for i in idx])
            yield obs_batch, action_batch


__all__ = [
    "ACTION_DIM",
    "OBS_DIM",
    "ExpertDataset",
]
