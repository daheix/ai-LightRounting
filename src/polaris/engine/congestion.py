"""CNN 拥塞预测器（2025 增强）。

将布局栅格化为 2D 图像，CNN 预测拥塞热力图，引导布局 agent
避免高拥塞区域，提升布线成功率。

方法参考（方案检索，见项目规则 1.1）：
- chipfoundryservices 综述: CNN 拥塞预测比详细布线快 1000×
  来源: https://www.chipfoundryservices.com/topic/ml-for-place-and-route
- Google TPU v5 (Nature 2021): edge-based GNN + RL
  来源: https://www.nature.com/articles/s41586-021-03544-w
- ChipletFormer (NeurIPS 2024): Transformer + GNN 融合
  来源: https://mlforsystems.org/assets/papers/neurips2024/paper22.pdf

架构: Conv2d → ReLU → MaxPool2d → Conv2d → ReLU → Linear → sigmoid
输入: (1, grid_h, grid_w) 布局栅格图
输出: (oh, ow) 拥塞概率热力图（oh/ow 由卷积/池化链实际计算得出）

训练参考:
- LeCun et al., 1998, CNN 反向传播与 SGD/Adam 训练
  https://ieeexplore.ieee.org/document/726791
- BCE with logits: PyTorch BCEWithLogitsLoss（数值稳定）
  https://pytorch.org/docs/stable/generated/torch.nn.BCEWithLogitsLoss
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from polaris.nn import Adam, Linear, ReLU, Tensor
from polaris.nn.conv import Conv2d, MaxPool2d


def _conv_out(h: int, k: int, s: int, p: int) -> int:
    """卷积输出尺寸: (h + 2p - k) // s + 1。"""
    return (h + 2 * p - k) // s + 1


def _pool_out(h: int, k: int, s: int) -> int:
    """池化输出尺寸: (h - k) // s + 1。"""
    return (h - k) // s + 1


def _spatial_out(size: int) -> int:
    """计算 conv1→pool→conv2→pool 后的空间尺寸。

    修复原 ``oh = (grid_h - 4) // 4 + 1`` 公式在 floor 除法下与
    实际前向尺寸不一致的 Bug（grid_h=32 时公式得 8，实际为 6，
    导致 fc1 输入维度 1024 与实际 576 不匹配而崩溃）。
    """
    h1 = _conv_out(size, 3, 1, 0)
    h2 = _pool_out(h1, 2, 2)
    h3 = _conv_out(h2, 3, 1, 0)
    return _pool_out(h3, 2, 2)


class CongestionCNN:
    """CNN 拥塞预测器（3 层 CNN + 2 层 FC）。

    输入: 布局栅格图 (1, H, W)，1=器件占据，0=空
    输出: 拥塞概率热力图 (oh, ow)

    来源:
    - chipfoundryservices: CNN 拥塞预测
      https://www.chipfoundryservices.com/topic/ml-for-place-and-route
    """

    def __init__(self, grid_h: int = 32, grid_w: int = 32) -> None:
        self.grid_h = grid_h
        self.grid_w = grid_w
        oh = _spatial_out(grid_h)
        ow = _spatial_out(grid_w)
        self.conv1 = Conv2d(1, 8, 3, stride_padding=(1, 0))
        self.conv2 = Conv2d(8, 16, 3, stride_padding=(1, 0))
        self.pool = MaxPool2d(2)
        self.relu = ReLU()
        flat_dim = 16 * oh * ow
        self.fc1 = Linear(flat_dim, 64)
        self.fc2 = Linear(64, oh * ow)
        self.oh = oh
        self.ow = ow

    def forward_logits(self, grid: np.ndarray) -> Tensor:
        """前向返回 logits 张量（含计算图，用于训练反向传播）。

        Args:
            grid: 布局栅格图，支持 (H,W)/(C,H,W)/(N,C,H,W)。

        Returns:
            logits 张量 (N, oh*ow)。
        """
        data = np.asarray(grid, dtype=np.float64)
        if data.ndim == 2:
            data = data[np.newaxis, np.newaxis]
        elif data.ndim == 3:
            data = data[np.newaxis]
        x = Tensor(data)
        x = self.relu(self.conv1(x))
        x = self.pool(x)
        x = self.relu(self.conv2(x))
        x = self.pool(x)
        n = x.data.shape[0]
        flat = x.reshape(n, -1)
        return self.fc2(self.relu(self.fc1(flat)))

    def forward(self, grid: np.ndarray) -> np.ndarray:
        """前向推理：栅格图 → 拥塞热力图 (oh, ow)。"""
        logits = self.forward_logits(grid)
        return 1.0 / (1.0 + np.exp(-logits.data.reshape(self.oh, self.ow)))

    def parameters(self) -> list[Tensor]:
        """返回所有可训练参数。"""
        params = self.conv1.parameters() + self.conv2.parameters()
        params += self.fc1.parameters() + self.fc2.parameters()
        return params

    def train(
        self,
        grids: np.ndarray,
        labels: np.ndarray,
        config: CNNTrainConfig | None = None,
    ) -> list[float]:
        """训练 CNN（BCE with logits + Adam + mini-batch）。

        Args:
            grids: 训练输入 (N, 1, H, W)。
            labels: 拥塞标签 (N, oh*ow)，值域 [0,1]。
            config: 训练超参数，None 用默认值。

        Returns:
            每个 epoch 的平均损失列表。

        来源:
        - LeCun et al., 1998, CNN 训练
          https://ieeexplore.ieee.org/document/726791
        """
        cfg = config or CNNTrainConfig()
        optimizer = Adam(self.parameters(), lr=cfg.lr)
        x_all = np.asarray(grids, dtype=np.float64)
        y_all = np.asarray(labels, dtype=np.float64)
        n = x_all.shape[0]
        history: list[float] = []
        for _ in range(cfg.epochs):
            perm = np.random.permutation(n)
            epoch_loss = 0.0
            n_batches = 0
            for start in range(0, n, cfg.batch_size):
                idx = perm[start : start + cfg.batch_size]
                optimizer.zero_grad()
                logits = self.forward_logits(x_all[idx])
                y_flat = y_all[idx].reshape(y_all[idx].shape[0], -1)
                loss = _bce_with_logits_loss(logits, y_flat)
                loss.backward()
                optimizer.step()
                epoch_loss += float(loss.data)
                n_batches += 1
            history.append(epoch_loss / max(1, n_batches))
        return history


@dataclass
class CNNTrainConfig:
    """CNN 训练超参数配置。

    来源: LeCun 1998 CNN 训练; Kingma & Ba 2015 Adam。
    """

    epochs: int = 10
    batch_size: int = 8
    lr: float = 1e-3


def _bce_with_logits_loss(z: Tensor, y: np.ndarray) -> Tensor:
    """BCE with logits 损失（数值稳定，含自定义反向）。

    L = mean(max(z,0) - z*y + log(1+exp(-|z|)))
    dL/dz = (sigmoid(z) - y) / N

    来源: PyTorch BCEWithLogitsLoss
    https://pytorch.org/docs/stable/generated/torch.nn.BCEWithLogitsLoss
    """
    z_data = z.data
    loss_val = float(
        np.mean(np.maximum(z_data, 0) - z_data * y + np.log1p(np.exp(-np.abs(z_data))))
    )
    out = Tensor(np.array(loss_val), z.requires_grad, (z,))
    n = z_data.size

    def _back(g: np.ndarray) -> None:
        if z.requires_grad:
            z._ensure_grad()
            sig = 1.0 / (1.0 + np.exp(-z_data))
            z.grad = z.grad + g * (sig - y) / n

    out._backward = _back
    return out


def grid_from_devices(
    devices: list[dict],
    grid_h: int,
    grid_w: int,
    canvas_w: float,
    canvas_h: float,
) -> np.ndarray:
    """将器件位置栅格化为 2D 占据图。

    Args:
        devices: 器件列表，每个含 x/y/w/h。
        grid_h: 栅格高度。
        grid_w: 栅格宽度。
        canvas_w: 画布宽度（μm）。
        canvas_h: 画布高度（μm）。

    Returns:
        占据图 (1, grid_h, grid_w)，1=占据，0=空。
    """
    grid = np.zeros((1, grid_h, grid_w))
    for d in devices:
        x, y = d.get("x", 0), d.get("y", 0)
        w, h = d.get("w", 10), d.get("h", 10)
        gx0 = int(x / canvas_w * grid_w)
        gy0 = int(y / canvas_h * grid_h)
        gx1 = int((x + w) / canvas_w * grid_w) + 1
        gy1 = int((y + h) / canvas_h * grid_h) + 1
        gx0, gx1 = max(0, gx0), min(grid_w, gx1)
        gy0, gy1 = max(0, gy0), min(grid_h, gy1)
        grid[0, gy0:gy1, gx0:gx1] = 1.0
    return grid


@dataclass
class DatasetConfig:
    """拥塞数据集生成配置。"""

    grid_h: int = 32
    grid_w: int = 32
    n_devices: int = 8
    n_connections: int = 6
    seed: int | None = None


def generate_congestion_dataset(
    n_samples: int,
    config: DatasetConfig | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """生成拥塞预测训练数据集（A* 布线标签）。

    用 GridRouter A* 布线器对随机布局布线，累积路径栅格作为真实
    拥塞标签，下采样到 CNN 输出分辨率后归一化到 [0,1]。

    Args:
        n_samples: 样本数。
        config: 数据集生成配置，None 用默认值。

    Returns:
        (grids, labels): grids (N,1,H,W)，labels (N, oh*ow)。
    """
    cfg = config or DatasetConfig()
    rng = np.random.default_rng(cfg.seed)
    grids = np.zeros((n_samples, 1, cfg.grid_h, cfg.grid_w))
    cnn = CongestionCNN(cfg.grid_h, cfg.grid_w)
    labels = np.zeros((n_samples, cnn.oh * cnn.ow))
    for s in range(n_samples):
        devices = _random_devices(rng, cfg.n_devices, cfg.grid_h, cfg.grid_w)
        grids[s] = grid_from_devices(
            devices, cfg.grid_h, cfg.grid_w, float(cfg.grid_w), float(cfg.grid_h)
        )
        cong = _route_congestion(devices, cfg.n_connections, cfg.grid_h, cfg.grid_w, rng)
        labels[s] = _downsample_congestion(cong, cnn.oh, cnn.ow).flatten()
    return grids, labels


def _random_devices(
    rng: np.random.Generator,
    n_devices: int,
    grid_h: int,
    grid_w: int,
) -> list[dict]:
    """生成随机器件布局（网格坐标）。"""
    devices: list[dict] = []
    for _ in range(n_devices):
        dw = int(rng.integers(2, 5))
        dh = int(rng.integers(2, 5))
        dx = int(rng.integers(0, max(1, grid_w - dw)))
        dy = int(rng.integers(0, max(1, grid_h - dh)))
        devices.append({"x": dx, "y": dy, "w": dw, "h": dh})
    return devices


def _route_congestion(
    devices: list[dict],
    n_connections: int,
    grid_h: int,
    grid_w: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """用 A* 布线生成拥塞图（路径栅格累积，归一化到 [0,1]）。

    来源: GridRouter A* 布线器（polaris.router.waveguide_router）。
    """
    from polaris.router.waveguide_router import GridRouter, RouterConstraints

    router = GridRouter(grid_w, grid_h, 1.0, RouterConstraints())
    centers: list[tuple[int, int]] = []
    for d in devices:
        router.add_obstacle(int(d["x"]), int(d["y"]), int(d["w"]), int(d["h"]))
        gx = max(0, min(grid_w - 1, int(d["x"] + d["w"] / 2)))
        gy = max(0, min(grid_h - 1, int(d["y"] + d["h"] / 2)))
        centers.append((gx, gy))
    cong = np.zeros((grid_h, grid_w))
    blocked: set[tuple[int, int]] = set()
    for _ in range(n_connections):
        if len(centers) < 2:
            break
        i, j = rng.choice(len(centers), size=2, replace=False)
        path = router.route(centers[int(i)], centers[int(j)], blocked)
        if path:
            for px, py in path:
                if 0 <= px < grid_w and 0 <= py < grid_h:
                    cong[py, px] += 1.0
                blocked.add((px, py))
    mx = cong.max()
    return cong / mx if mx > 0 else cong


def _downsample_congestion(cong: np.ndarray, oh: int, ow: int) -> np.ndarray:
    """将拥塞图下采样到 (oh, ow)，块均值。"""
    h, w = cong.shape
    out = np.zeros((oh, ow))
    for i in range(oh):
        h0 = i * h // oh
        h1 = (i + 1) * h // oh
        for j in range(ow):
            w0 = j * w // ow
            w1 = (j + 1) * w // ow
            block = cong[h0:h1, w0:w1]
            out[i, j] = block.mean() if block.size > 0 else 0.0
    return out


def rudy_congestion(
    placements: dict,
    connections: list,
    grid_h: int,
    grid_w: int,
    canvas_w: float,
    canvas_h: float,
) -> np.ndarray:
    """RUDY (Rectangular Uniform wire DensitY) 即时拥塞估计。

    对每条连接的 bounding box 均匀分配 1 单位布线需求，累加到栅格。
    比详细布线快 1000×，是业界 RL 布局 obs 通道的标准做法。

    来源:
    - DREAMPlace (DAC 2020) RUDY 工业标准实现
      https://arxiv.org/abs/2004.10746
    - DeepPlace (NeurIPS 2021 ML-CAD) congestion map 作为 obs 通道
      https://openreview.net/pdf?id=uNYqDfPEDD8

    Args:
        placements: ``{instance_id: Placement}`` 字典（已放置器件）。
        connections: ``NetlistConnection`` 列表。
        grid_h: 栅格高度。
        grid_w: 栅格宽度。
        canvas_w: 画布宽度（μm）。
        canvas_h: 画布高度（μm）。

    Returns:
        归一化拥塞图 ``[grid_h, grid_w]``，值域 [0, 1]。
    """
    cong = np.zeros((grid_h, grid_w), dtype=np.float32)
    for conn in connections:
        src_pl = placements.get(conn.src_instance)
        dst_pl = placements.get(conn.dst_instance)
        if src_pl is None or dst_pl is None:
            continue
        src_port = src_pl.port_positions().get(conn.src_port)
        dst_port = dst_pl.port_positions().get(conn.dst_port)
        if src_port is None or dst_port is None:
            continue
        x0, y0 = src_port
        x1, y1 = dst_port
        xmin, xmax = min(x0, x1), max(x0, x1)
        ymin, ymax = min(y0, y1), max(y0, y1)
        gi0 = max(0, int(xmin / canvas_w * grid_w))
        gi1 = min(grid_w, int(xmax / canvas_w * grid_w) + 1)
        gj0 = max(0, int(ymin / canvas_h * grid_h))
        gj1 = min(grid_h, int(ymax / canvas_h * grid_h) + 1)
        if gi1 <= gi0 or gj1 <= gj0:
            continue
        cong[gj0:gj1, gi0:gi1] += 1.0
    mx = cong.max()
    return cong / mx if mx > 0 else cong


__all__ = [
    "CongestionCNN",
    "CongestionPredictor",
    "CNNTrainConfig",
    "DatasetConfig",
    "grid_from_devices",
    "generate_congestion_dataset",
    "rudy_congestion",
]


# ---------------------------------------------------------------------------
# 命名兼容别名（便于上层统一以 ``CongestionPredictor`` 名称访问）
# ---------------------------------------------------------------------------
# 历史代码与文档中曾以 ``CongestionPredictor`` 作为拥塞预测器统一入口名称，
# 实际实现为 ``CongestionCNN``（3 层 CNN + 2 层 FC）。此处提供别名以保持
# 向后兼容，避免上层调用方在重构后出现 ImportError。
CongestionPredictor = CongestionCNN
"""拥塞预测器统一别名（指向 CongestionCNN）。

上层代码可通过 ``from polaris.engine.congestion import CongestionPredictor``
访问，与文档/接口约定保持一致。
"""
