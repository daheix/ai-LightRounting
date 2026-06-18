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
输出: (grid_h//4, grid_w//4) 拥塞概率热力图
"""

from __future__ import annotations

import numpy as np

from polaris.nn import Linear, ReLU, Tensor
from polaris.nn.conv import Conv2d, MaxPool2d


class CongestionCNN:
    """CNN 拥塞预测器（3 层 CNN + 2 层 FC）。

    输入: 布局栅格图 (1, H, W)，1=器件占据，0=空
    输出: 拥塞概率热力图 (H//4, W//4)

    来源:
    - chipfoundryservices: CNN 拥塞预测
      https://www.chipfoundryservices.com/topic/ml-for-place-and-route
    """

    def __init__(self, grid_h: int = 32, grid_w: int = 32) -> None:
        self.grid_h = grid_h
        self.grid_w = grid_w
        oh = (grid_h - 4) // 4 + 1
        ow = (grid_w - 4) // 4 + 1
        self.conv1 = Conv2d(1, 8, 3, stride_padding=(1, 0))
        self.conv2 = Conv2d(8, 16, 3, stride_padding=(1, 0))
        self.pool = MaxPool2d(2)
        self.relu = ReLU()
        flat_dim = 16 * oh * ow
        self.fc1 = Linear(flat_dim, 64)
        self.fc2 = Linear(64, oh * ow)
        self.oh = oh
        self.ow = ow

    def forward(self, grid: np.ndarray) -> np.ndarray:
        """前向推理：栅格图 → 拥塞热力图。"""
        if grid.ndim == 2:
            grid = grid[np.newaxis, np.newaxis]
        elif grid.ndim == 3:
            grid = grid[np.newaxis]
        x = Tensor(grid)
        x = self.relu(self.conv1(x))
        x = self.pool(x)
        x = self.relu(self.conv2(x))
        x = self.pool(x)
        flat = Tensor(x.data.reshape(x.data.shape[0], -1))
        out = self.fc2(self.relu(self.fc1(flat)))
        return 1.0 / (1.0 + np.exp(-out.data.reshape(self.oh, self.ow)))

    def parameters(self) -> list[Tensor]:
        """返回所有可训练参数。"""
        params = self.conv1.parameters() + self.conv2.parameters()
        params += self.fc1.parameters() + self.fc2.parameters()
        return params


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


__all__ = ["CongestionCNN", "grid_from_devices"]
