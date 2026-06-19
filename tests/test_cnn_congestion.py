"""CNN 拥塞预测器训练测试（M3.2）。

验证 ``CongestionCNN`` 的前向输出形状、训练损失下降、
预测值域 [0,1]，以及 ``generate_congestion_dataset`` 数据生成。

来源:
- chipfoundryservices: CNN 拥塞预测
  https://www.chipfoundryservices.com/topic/ml-for-place-and-route
- LeCun et al., 1998, CNN 反向传播与 SGD/Adam 训练
  https://ieeexplore.ieee.org/document/726791
- PyTorch BCEWithLogitsLoss: https://pytorch.org/docs/stable/generated/torch.nn.BCEWithLogitsLoss
"""

from __future__ import annotations

import numpy as np

from polaris.engine.congestion import (
    CNNTrainConfig,
    CongestionCNN,
    DatasetConfig,
    generate_congestion_dataset,
)


def _make_cnn(grid_h: int = 16, grid_w: int = 16) -> CongestionCNN:
    """构造测试用 CNN 拥塞预测器。

    Args:
        grid_h: 栅格高度。
        grid_w: 栅格宽度。

    Returns:
        CongestionCNN 实例。
    """
    return CongestionCNN(grid_h=grid_h, grid_w=grid_w)


def test_generate_congestion_dataset_valid():
    """验证 generate_congestion_dataset 生成有效训练数据。

    数据形状应为 grids (N,1,H,W) 与 labels (N, oh*ow)，
    且标签值域在 [0,1]。
    """
    cfg = DatasetConfig(
        grid_h=16,
        grid_w=16,
        n_devices=4,
        n_connections=3,
        seed=42,
    )
    grids, labels = generate_congestion_dataset(n_samples=4, config=cfg)
    assert grids.shape == (4, 1, 16, 16), f"grids 形状错误: {grids.shape}"
    cnn = _make_cnn(16, 16)
    expected_label_dim = cnn.oh * cnn.ow
    assert labels.shape == (4, expected_label_dim), f"labels 形状错误: {labels.shape}"
    assert labels.min() >= 0.0, f"标签最小值 {labels.min()} < 0"
    assert labels.max() <= 1.0, f"标签最大值 {labels.max()} > 1"
    assert np.any(grids > 0), "grids 应有非零（占据）栅格"


def test_forward_output_shape():
    """验证 CongestionCNN.forward 输出形状为 (oh, ow)。"""
    cnn = _make_cnn(16, 16)
    grid = np.zeros((16, 16))
    grid[2:5, 3:7] = 1.0
    out = cnn.forward(grid)
    assert out.shape == (cnn.oh, cnn.ow), f"输出形状 {out.shape} != ({cnn.oh}, {cnn.ow})"


def test_forward_logits_shape():
    """验证 forward_logits 输出形状为 (N, oh*ow)。"""
    cnn = _make_cnn(16, 16)
    grid = np.zeros((2, 1, 16, 16))
    grid[0, 0, 2:5, 3:7] = 1.0
    grid[1, 0, 8:11, 10:14] = 1.0
    logits = cnn.forward_logits(grid)
    assert logits.data.shape == (2, cnn.oh * cnn.ow), (
        f"logits 形状 {logits.data.shape} != (2, {cnn.oh * cnn.ow})"
    )


def test_training_loss_decreases():
    """验证训练循环运行且损失下降（3 epoch 后 loss < 初始 loss）。

    来源: LeCun et al., 1998, CNN 训练
    https://ieeexplore.ieee.org/document/726791
    """
    np.random.seed(0)
    cfg = DatasetConfig(
        grid_h=16,
        grid_w=16,
        n_devices=4,
        n_connections=3,
        seed=123,
    )
    grids, labels = generate_congestion_dataset(n_samples=8, config=cfg)
    cnn = _make_cnn(16, 16)
    train_cfg = CNNTrainConfig(epochs=3, batch_size=4, lr=1e-2)
    history = cnn.train(grids, labels, config=train_cfg)
    assert len(history) == 3, f"应有 3 个 epoch 的损失记录，实际 {len(history)}"
    assert history[0] > 0, f"初始损失应 > 0，实际 {history[0]}"
    assert history[-1] < history[0], f"训练后损失 {history[-1]} 应小于初始损失 {history[0]}"


def test_predicted_congestion_in_unit_range():
    """验证预测拥塞图值域在 [0,1]（sigmoid 输出）。"""
    cnn = _make_cnn(16, 16)
    grids = np.random.RandomState(7).randint(0, 2, size=(3, 1, 16, 16)).astype(np.float64)
    for g in grids:
        out = cnn.forward(g)
        assert out.min() >= 0.0, f"预测最小值 {out.min()} < 0"
        assert out.max() <= 1.0, f"预测最大值 {out.max()} > 1"
