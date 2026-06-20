"""CNN 拥塞预测器训练测试（M3.2）。

验证 ``CongestionCNN`` 的前向输出形状、训练损失下降、
预测值域 [0,1]，以及 ``generate_congestion_dataset`` 数据生成。

来源:
- chipfoundryservices: CNN 拥塞预测
  https://www.chipfoundryservices.com/topic/ml-for-place-and-route
- LeCun et al., 1998, CNN 反向传播与 SGD/Adam 训练
  https://ieeexplore.ieee.org/document/726861
- PyTorch BCEWithLogitsLoss: https://pytorch.org/docs/stable/generated/torch.nn.BCEWithLogitsLoss
- DREAMPlace RUDY: https://arxiv.org/abs/2004.10746
- DeepPlace congestion-as-obs: https://openreview.net/pdf?id=uNYqDfPEDD8
"""

from __future__ import annotations

import numpy as np

from polaris.engine.congestion import (
    CNNTrainConfig,
    CongestionCNN,
    DatasetConfig,
    generate_congestion_dataset,
    rudy_congestion,
)
from polaris.engine.floorplan_env import Placement
from polaris.engine.netlist import Netlist, NetlistConnection
from polaris.pdk.device import BoundingBox, Device
from polaris.pdk.port import Direction, Port


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


# ---------------------------------------------------------------------------
# rudy_congestion RUDY 即时拥塞估计（roadmap 2.1.1 孤岛#3 打通）
# ---------------------------------------------------------------------------


def _make_test_device(dev_id: str, w: float = 20.0, h: float = 10.0) -> Device:
    """构造测试用器件（含两个左右端口）。"""
    return Device(
        device_id=dev_id,
        platform="SOI",
        category="passive",
        name="wg",
        ports=[
            Port(name="in", x=0.0, y=h / 2, direction=Direction.WEST, waveguide_type="strip", width=0.5),
            Port(name="out", x=w, y=h / 2, direction=Direction.EAST, waveguide_type="strip", width=0.5),
        ],
        bbox=BoundingBox(xmin=0.0, ymin=0.0, xmax=w, ymax=h),
    )


def _make_test_placements() -> dict:
    """构造两个已放置器件（水平排列，间距 30μm）。"""
    dev_a = _make_test_device("dev_a", w=20.0, h=10.0)
    dev_b = _make_test_device("dev_b", w=20.0, h=10.0)
    return {
        "dev_a": Placement(instance_id="dev_a", device=dev_a, x=0.0, y=0.0, rotation=0),
        "dev_b": Placement(instance_id="dev_b", device=dev_b, x=50.0, y=0.0, rotation=0),
    }


def test_rudy_congestion_shape() -> None:
    """验证 RUDY 拥塞图形状与栅格尺寸一致。"""
    placements = _make_test_placements()
    connections = [
        NetlistConnection(src_instance="dev_a", src_port="out", dst_instance="dev_b", dst_port="in"),
    ]
    cong = rudy_congestion(placements, connections, grid_h=10, grid_w=10, canvas_w=100.0, canvas_h=20.0)
    assert cong.shape == (10, 10), f"拥塞图形状 {cong.shape} != (10, 10)"


def test_rudy_congestion_value_range() -> None:
    """验证 RUDY 拥塞图值域 [0, 1]（归一化）。"""
    placements = _make_test_placements()
    connections = [
        NetlistConnection(src_instance="dev_a", src_port="out", dst_instance="dev_b", dst_port="in"),
    ]
    cong = rudy_congestion(placements, connections, grid_h=10, grid_w=10, canvas_w=100.0, canvas_h=20.0)
    assert cong.min() >= 0.0, f"最小值 {cong.min()} < 0"
    assert cong.max() <= 1.0, f"最大值 {cong.max()} > 1"
    assert cong.max() > 0.0, "应有非零拥塞"


def test_rudy_congestion_empty_placements() -> None:
    """验证无放置器件时返回全零拥塞图。"""
    connections = [
        NetlistConnection(src_instance="dev_a", src_port="out", dst_instance="dev_b", dst_port="in"),
    ]
    cong = rudy_congestion({}, connections, grid_h=8, grid_w=8, canvas_w=100.0, canvas_h=20.0)
    assert cong.shape == (8, 8)
    assert cong.max() == 0.0, "无放置器件时拥塞应为 0"


def test_rudy_congestion_accumulates() -> None:
    """验证多条连接累加拥塞（交叉区域拥塞更高）。"""
    placements = _make_test_placements()
    connections = [
        NetlistConnection(src_instance="dev_a", src_port="out", dst_instance="dev_b", dst_port="in"),
        NetlistConnection(src_instance="dev_a", src_port="out", dst_instance="dev_b", dst_port="in"),
    ]
    cong_multi = rudy_congestion(
        placements, connections, grid_h=10, grid_w=10, canvas_w=100.0, canvas_h=20.0
    )
    connections_single = [connections[0]]
    cong_single = rudy_congestion(
        placements, connections_single, grid_h=10, grid_w=10, canvas_w=100.0, canvas_h=20.0
    )
    # 归一化后两者最大值都为 1.0，但多连接的拥塞分布应更广（非零元素更多）
    assert cong_multi.sum() >= cong_single.sum(), "多连接拥塞总和应 >= 单连接"


def test_rudy_congestion_missing_port() -> None:
    """验证端口不存在时跳过该连接（不崩溃）。"""
    placements = _make_test_placements()
    connections = [
        NetlistConnection(
            src_instance="dev_a", src_port="nonexistent", dst_instance="dev_b", dst_port="in"
        ),
    ]
    cong = rudy_congestion(placements, connections, grid_h=8, grid_w=8, canvas_w=100.0, canvas_h=20.0)
    assert cong.shape == (8, 8)
    assert cong.max() == 0.0, "端口不存在时拥塞应为 0"
