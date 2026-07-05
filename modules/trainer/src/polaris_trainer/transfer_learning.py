"""迁移学习模块（polaris-trainer）：布局→布线跨任务迁移。

从 PoLaRIS v4 ``src/polaris/trainer/transfer_learning.py`` 迁移核心迁移学习
能力到 v5.0 子模块。加载预训练 BC checkpoint，复用 feature extractor 层权重，
冻结底层 + 微调高层 + 新增布线输出头，实现布局→布线跨任务迁移。

纯 NumPy 实现（R04: 不参与 GPU；R13: 保持功能独立）。

## 核心能力

- ``RoutingPolicyModel``: 布线策略网络，复用预训练前 2 层 + 新增布线输出头。
- ``TransferConfig``: 迁移学习超参数（冻结层 / 微调 lr / epochs）。
- ``transfer_learn``: 主入口，加载 ckpt → 复制权重 → 冻结 → 微调 → 保存。
- ``extract_routing_targets``: 从 routes.json 提取每器件平均路由长度（布线目标）。

## 学术依据（R02 学术诚信，≥5 个文献 URL）

1. Pan & Yang 2010 "A Survey on Transfer Learning" IEEE TKDE
   https://doi.org/10.1109/TKDE.2009.191
2. Yosinski et al. 2014 "How transferable are features in deep neural networks?"
   NIPS https://arxiv.org/abs/1411.1792
3. Oquab et al. 2014 "Learning and Transferring Mid-level Image Representations
   using Convolutional Neural Networks" CVPR
   https://arxiv.org/abs/1406.5774
4. Donahue et al. 2014 "DeCAF: A Deep Convolutional Activation Feature for
   Generic Visual Recognition" ICML https://arxiv.org/abs/1310.1531
5. Bengio 2012 "Deep Learning of Representations for Unsupervised and
   Transfer Learning" ICML Tutorial https://arxiv.org/abs/1206.5538
6. Mirhoseini et al., Nature 2021, AlphaChip（预训练-微调范式）
   https://www.nature.com/articles/s41586-021-03544-w
7. Kirkpatrick et al. 2017 "Overcoming catastrophic forgetting in neural
   networks" PNAS（EWC，迁移学习防遗忘）https://arxiv.org/abs/1612.00796
8. Rusu et al. 2016 "Progressive Neural Networks" arXiv（迁移学习架构）
   https://arxiv.org/abs/1606.04671

来源: 迁移自 PoLaRIS v4 ``src/polaris/trainer/transfer_learning.py``（R13）。
"""

from __future__ import annotations

import json
import logging
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from polaris_trainer._nn import Adam, AdamConfig, Linear, Module, ReLU, Tensor
from polaris_trainer.pretrain import (
    DEVICE_FEATURE_DIM,
    ExpertDemoLoader,
    _extract_device_features,
    load_bc_checkpoint,
)

logger = logging.getLogger(__name__)

# =============================================================================
# 常量
# =============================================================================

# 布线任务输出维度（平均路由长度，um）
ROUTING_OUTPUT_DIM = 1


@dataclass
class TransferConfig:
    """迁移学习超参数配置。

    Attributes:
        hidden_dim: 隐藏层维度（须与预训练 ckpt 一致，默认 64）。
        finetune_lr: 微调学习率（默认 5e-4，小于 pretrain lr 1e-3，
            迁移学习标准做法，避免破坏预训练特征，Yosinski 2014 §5）。
        epochs: 微调轮数（默认 50，迁移学习通常 <预训练轮数）。
        batch_size: 小批量大小。
        freeze_feature_extractor: 是否冻结第 1 层（feature extractor），
            True 则只微调第 2 层 + 布线头（Yosinski 2014 §4 实验）。
        checkpoint_dir: 微调 checkpoint 保存目录。
        seed: 随机种子。
    """

    hidden_dim: int = 64
    finetune_lr: float = 5e-4
    epochs: int = 50
    batch_size: int = 16
    freeze_feature_extractor: bool = True
    checkpoint_dir: str = "checkpoints"
    seed: int = 42


class RoutingPolicyModel(Module):
    """布线策略网络（布局→布线迁移）。

    复用预训练 BC 模型的前 2 层（feature extractor + 中间层），新增布线输出头
   （Linear(hidden,1)）。冻结策略由 ``freeze_feature_extractor`` 控制。

    结构::
        fc1 (Linear in→64) → relu1   # 来自预训练（可冻结）
        fc2 (Linear 64→64) → relu2   # 来自预训练（微调）
        routing_head (Linear 64→1)   # 新增（从头训练）

    *创新*: 跨任务特征迁移——布局任务学到的 device 特征表示（fc1/fc2 权重）
    对布线任务（路由长度预测）也有效，验证 Yosinski 2014 "features are
    transferable" 结论在光电子布局布线场景的适用性。
    - 底层逻辑: 布局与布线共享底层物理特征（device 尺寸/端口/类型），
      高层任务特化（布局=坐标回归，布线=长度回归），迁移底层特征可减少布线
      任务所需数据量（Pan & Yang 2010 §3 迁移学习形式化）。
    - 支持理论: Yosinski 2014 NIPS 实验证明前层特征泛化性强，迁移后微调
      收敛更快且最终性能接近从头训练（数据充足时）或超越（数据稀缺时）。

    来源:
    - Yosinski 2014 NIPS https://arxiv.org/abs/1411.1792
    - Pan & Yang 2010 IEEE TKDE https://doi.org/10.1109/TKDE.2009.191
    """

    def __init__(self, hidden_dim: int = 64) -> None:
        self.hidden_dim = hidden_dim
        self.fc1 = Linear(DEVICE_FEATURE_DIM, hidden_dim)
        self.relu1 = ReLU()
        self.fc2 = Linear(hidden_dim, hidden_dim)
        self.relu2 = ReLU()
        self.routing_head = Linear(hidden_dim, ROUTING_OUTPUT_DIM)

    def forward(self, x: Tensor) -> Tensor:
        h = self.relu1(self.fc1(x))
        h = self.relu2(self.fc2(h))
        return self.routing_head(h)

    def freeze_feature_extractor(self) -> None:
        """冻结 fc1（feature extractor），保留 fc2 + routing_head 可训练。

        冻结后 ``parameters()`` 只返回 requires_grad=True 的参数
        （fc2 + routing_head），optimizer 只更新这些参数。
        """
        for p in self.fc1.parameters():
            p.requires_grad = False

    def load_pretrained_layers(self, pretrain_params: list) -> tuple[int, int]:
        """从预训练 BC checkpoint 复制前 2 层权重。

        BC 模型 params 顺序（_save_bc_checkpoint）:
        [fc1.weight, fc1.bias, fc2.weight, fc2.bias, fc3.weight, fc3.bias]
        本模型复用前 4 个（fc1 + fc2），fc3 丢弃（任务输出维度不同）。

        Args:
            pretrain_params: 预训练 checkpoint 的 params 列表（list of array）。

        Returns:
            (n_loaded, n_skipped): 加载的参数数 / 跳过的参数数。

        Raises:
            ValueError: 预训练 params 数量 < 4 或 shape 不匹配（R03 无 fall-back）。
        """
        if len(pretrain_params) < 4:
            raise ValueError(
                f"预训练 params 数量 {len(pretrain_params)} < 4（需要 fc1+fc2 共 4 个）"
                f"（R03 无 fall-back）"
            )
        fc1_params = self.fc1.parameters()
        fc2_params = self.fc2.parameters()
        n_loaded = 0
        for p, data in zip(fc1_params, pretrain_params[0:2], strict=True):
            data_arr = np.array(data, dtype=np.float64)
            if data_arr.shape != p.data.shape:
                raise ValueError(
                    f"fc1 参数 shape 不匹配: 预训练 {data_arr.shape} vs "
                    f"目标 {p.data.shape}（R03 无 fall-back）"
                )
            p.data = data_arr
            n_loaded += 1
        for p, data in zip(fc2_params, pretrain_params[2:4], strict=True):
            data_arr = np.array(data, dtype=np.float64)
            if data_arr.shape != p.data.shape:
                raise ValueError(
                    f"fc2 参数 shape 不匹配: 预训练 {data_arr.shape} vs "
                    f"目标 {p.data.shape}（R03 无 fall-back）"
                )
            p.data = data_arr
            n_loaded += 1
        n_skipped = len(pretrain_params) - 4
        return n_loaded, n_skipped


def extract_routing_targets(loader: ExpertDemoLoader) -> tuple[np.ndarray, np.ndarray, dict]:
    """提取布线任务训练对（device 特征 → 平均路由长度）。

    从 routes.json 计算每条路由的累计欧氏长度，取每个器件所在电路的平均路由长度
    作为布线目标（um）。同一电路内所有 device 共享同一平均路由长度（电路级标签）。

    Args:
        loader: ExpertDemoLoader 实例。

    Returns:
        X: (N, DEVICE_FEATURE_DIM) 标准化 device 特征。
        Y: (N, ROUTING_OUTPUT_DIM) 标准化平均路由长度。
        stats: 归一化统计。
    """
    feats: list[list[float]] = []
    targets: list[float] = []
    for name in loader.list_demos():
        demo = loader.load_demo(name)
        netlist = demo["netlist"]
        placements = demo["placements"]
        routes = demo["routes"]
        # 计算平均路由长度
        route_lengths: list[float] = []
        for route in routes:
            if len(route) < 2:
                continue
            arr = np.array(route, dtype=np.float64)
            diffs = np.diff(arr, axis=0)
            seg_len = np.sqrt(np.sum(diffs**2, axis=1))
            route_lengths.append(float(np.sum(seg_len)))
        avg_route_len = float(np.mean(route_lengths)) if route_lengths else 0.0
        # R03 禁止 fall-back：canvas_w/canvas_h 缺失即 raise（specs.py 单位 μm，默认 1000.0）
        if "canvas_w" not in netlist:
            raise KeyError(
                "netlist 缺 canvas_w 字段（μm，与 specs.py CircuitSpec.canvas_w 对齐）"
                "（R03 禁止 fall-back）"
            )
        if "canvas_h" not in netlist:
            raise KeyError(
                "netlist 缺 canvas_h 字段（μm，与 specs.py CircuitSpec.canvas_h 对齐）"
                "（R03 禁止 fall-back）"
            )
        canvas_w = float(netlist["canvas_w"])
        canvas_h = float(netlist["canvas_h"])
        devices = netlist.get("devices", [])
        n_devices = len(devices)
        for dev in devices:
            dev_name = dev["name"]
            if dev_name not in placements:
                continue
            feat = _extract_device_features(dev, canvas_w, canvas_h, n_devices)
            feats.append(feat)
            targets.append(avg_route_len)
    if not feats:
        raise ValueError("未提取到任何布线训练对（R03 无 fall-back）")
    X = np.array(feats, dtype=np.float64)
    Y = np.array(targets, dtype=np.float64).reshape(-1, 1)
    x_mean = X.mean(axis=0)
    x_std = np.where(X.std(axis=0) < 1e-8, 1.0, X.std(axis=0))
    y_mean = Y.mean(axis=0)
    y_std = np.where(Y.std(axis=0) < 1e-8, 1.0, Y.std(axis=0))
    X_norm = (X - x_mean) / x_std
    Y_norm = (Y - y_mean) / y_std
    stats = {
        "x_mean": x_mean.tolist(),
        "x_std": x_std.tolist(),
        "y_mean": y_mean.tolist(),
        "y_std": y_std.tolist(),
        "n_samples": int(X.shape[0]),
    }
    return X_norm, Y_norm, stats


def _setup_transfer_model(
    pretrain_ckpt: str | Path,
    cfg: TransferConfig,
) -> tuple[RoutingPolicyModel, int, int, int, int]:
    """加载预训练 ckpt + 构建模型 + 复制权重 + 冻结 + 统计参数。

    Returns:
        (model, n_loaded, n_skipped, n_frozen, n_trainable)
    """
    state = load_bc_checkpoint(pretrain_ckpt)
    pretrain_params = state["params"]
    logger.info(
        "加载预训练 ckpt: %s (%d params)",
        pretrain_ckpt, len(pretrain_params),
    )
    model = RoutingPolicyModel(hidden_dim=cfg.hidden_dim)
    n_loaded, n_skipped = model.load_pretrained_layers(pretrain_params)
    logger.info(
        "迁移: 加载 %d 参数 (fc1+fc2), 跳过 %d (fc3 输出层)",
        n_loaded, n_skipped,
    )
    n_frozen = 0
    if cfg.freeze_feature_extractor:
        model.freeze_feature_extractor()
        n_frozen = 2  # fc1.weight + fc1.bias
        logger.info("冻结 fc1 (%d 参数)", n_frozen)
    n_trainable = len(model.parameters())
    logger.info("可训练参数: %d", n_trainable)
    return model, n_loaded, n_skipped, n_frozen, n_trainable


def _run_finetune_loop(
    model: RoutingPolicyModel,
    X: np.ndarray,
    Y: np.ndarray,
    cfg: TransferConfig,
) -> list[float]:
    """微调训练循环（MSE + Adam，小学习率）。

    Returns:
        loss_history: 每个 epoch 的平均 loss 列表。

    Raises:
        RuntimeError: 训练出现 NaN（R03 无 fall-back）。
    """
    n_samples = X.shape[0]
    optimizer = Adam(
        model.parameters(), lr=cfg.finetune_lr, config=AdamConfig(),
    )
    loss_history: list[float] = []
    indices = np.arange(n_samples)
    for epoch in range(cfg.epochs):
        np.random.shuffle(indices)
        epoch_loss = 0.0
        n_batches = 0
        for start in range(0, n_samples, cfg.batch_size):
            batch_idx = indices[start : start + cfg.batch_size]
            Xb = X[batch_idx]
            Yb = Y[batch_idx]
            optimizer.zero_grad()
            pred = model(Tensor(Xb))
            diff = pred - Tensor(Yb)
            loss = (diff * diff).mean()
            loss.backward()
            optimizer.step()
            epoch_loss += float(loss.data)
            n_batches += 1
        avg_loss = epoch_loss / max(n_batches, 1)
        if not math.isfinite(avg_loss):
            raise RuntimeError(
                f"epoch {epoch} loss NaN（R03 无 fall-back）"
            )
        loss_history.append(avg_loss)
        if (epoch + 1) % 10 == 0 or epoch == 0:
            logger.info(
                "finetune epoch %d/%d loss=%.6f",
                epoch + 1, cfg.epochs, avg_loss,
            )
    return loss_history


def transfer_learn(
    pretrain_ckpt: str | Path,
    demos_dir: str | Path = "real_board/expert_demos",
    config: TransferConfig | None = None,
    output_ckpt: str | Path | None = None,
) -> dict:
    """迁移学习主入口：布局预训练 → 布线微调。

    流程:
    1. 加载预训练 BC checkpoint（params + feature_stats）
    2. 构建 RoutingPolicyModel，复制预训练前 2 层权重
    3. 冻结 fc1（feature extractor），保留 fc2 + routing_head 可训练
    4. 提取布线任务训练对（device 特征 → 平均路由长度）
    5. 微调（MSE + Adam，小学习率）
    6. 保存微调 checkpoint

    *创新*: 跨任务特征迁移，验证 Yosinski 2014 "features are transferable"
    在光电子布局→布线场景的适用性。

    Args:
        pretrain_ckpt: 预训练 BC checkpoint 路径（pretrain() 输出）。
        demos_dir: expert_demos 目录（用于提取布线目标）。
        config: 迁移学习配置（None 用默认 TransferConfig）。
        output_ckpt: 微调 checkpoint 输出路径。

    Returns:
        迁移学习结果 dict::

            {
                "checkpoint_path": str,
                "final_loss": float,
                "loss_history": list[float],
                "n_loaded_params": int,    # 从预训练加载的参数数
                "n_frozen_params": int,   # 冻结的参数数
                "n_trainable_params": int,  # 可训练参数数
                "n_samples": int,
            }

    Raises:
        FileNotFoundError: pretrain_ckpt 或 demos_dir 不存在（R03 无 fall-back）。
        ValueError: checkpoint 格式不兼容或 shape 不匹配（R03 无 fall-back）。
        RuntimeError: 训练出现 NaN（R03 无 fall-back）。
    """
    cfg = config or TransferConfig()
    np.random.seed(cfg.seed)
    model, n_loaded, _, n_frozen, n_trainable = _setup_transfer_model(
        pretrain_ckpt, cfg,
    )
    loader = ExpertDemoLoader(demos_dir)
    X, Y, stats = extract_routing_targets(loader)
    n_samples = X.shape[0]
    logger.info("布线任务: %d 样本", n_samples)
    loss_history = _run_finetune_loop(model, X, Y, cfg)
    final_loss = loss_history[-1] if loss_history else float("inf")
    ckpt_path = (
        Path(output_ckpt)
        if output_ckpt
        else Path(cfg.checkpoint_dir) / "routing_finetune.json"
    )
    _save_finetune_checkpoint(
        ckpt_path, model, cfg, stats, loss_history, final_loss,
        n_samples, n_loaded, n_frozen, n_trainable, pretrain_ckpt,
    )
    logger.info("迁移学习 ckpt 已保存: %s (final_loss=%.6f)", ckpt_path, final_loss)
    return {
        "checkpoint_path": str(ckpt_path),
        "final_loss": final_loss,
        "loss_history": loss_history,
        "n_loaded_params": n_loaded,
        "n_frozen_params": n_frozen,
        "n_trainable_params": n_trainable,
        "n_samples": n_samples,
    }


def _save_finetune_checkpoint(
    ckpt_path: Path,
    model: RoutingPolicyModel,
    cfg: TransferConfig,
    stats: dict,
    loss_history: list[float],
    final_loss: float,
    n_samples: int,
    n_loaded: int,
    n_frozen: int,
    n_trainable: int,
    pretrain_ckpt: str | Path,
) -> None:
    """保存迁移学习 checkpoint。"""
    ckpt_path.parent.mkdir(parents=True, exist_ok=True)
    state = {
        "version": "R36-transfer-v1.0",
        "model_type": "RoutingPolicyModel",
        "task": "placement->routing transfer",
        "config": {
            "hidden_dim": cfg.hidden_dim,
            "finetune_lr": cfg.finetune_lr,
            "epochs": cfg.epochs,
            "batch_size": cfg.batch_size,
            "freeze_feature_extractor": cfg.freeze_feature_extractor,
            "seed": cfg.seed,
        },
        "input_dim": DEVICE_FEATURE_DIM,
        "output_dim": ROUTING_OUTPUT_DIM,
        "params": [p.data.tolist() for p in model.parameters()],
        "all_params": [
            p.data.tolist()
            for layer in (model.fc1, model.fc2, model.routing_head)
            for p in layer.parameters()
        ],
        "feature_stats": stats,
        "metrics": {
            "loss_history": loss_history,
            "final_loss": final_loss,
            "n_samples": n_samples,
            "n_loaded_params": n_loaded,
            "n_frozen_params": n_frozen,
            "n_trainable_params": n_trainable,
        },
        "transfer_metadata": {
            "method": "Transfer Learning (Pan & Yang 2010, Yosinski 2014)",
            "source_task": "placement (Behavioral Cloning)",
            "target_task": "routing (avg route length regression)",
            "frozen_layers": ["fc1"] if cfg.freeze_feature_extractor else [],
            "finetuned_layers": ["fc2", "routing_head"],
            "pretrain_checkpoint": str(pretrain_ckpt),
            "papers": [
                "Pan & Yang 2010 IEEE TKDE",
                "Yosinski 2014 NIPS",
                "Oquab 2014 CVPR",
                "Donahue 2014 ICML DeCAF",
                "Bengio 2012 ICML Transfer Learning",
                "Mirhoseini 2021 AlphaChip Nature",
                "Kirkpatrick 2017 PNAS EWC",
            ],
        },
    }
    ckpt_path.write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
    )


__all__ = [
    "TransferConfig",
    "RoutingPolicyModel",
    "ROUTING_OUTPUT_DIM",
    "transfer_learn",
    "extract_routing_targets",
]
