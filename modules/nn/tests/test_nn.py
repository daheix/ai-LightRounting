"""polaris-nn 子模块 smoke test。

测试覆盖:
- nn: Linear/ReLU/Sequential/Adam 前向+反向+优化步进
- nn: ScaledDotProductAttention/MultiHeadAttention 前向
- nn: Conv2d 前向（im2col）
- data: TILOS/Apollo/LiDAR benchmark loaders 返回 CircuitSpec
- data: evaluate_benchmark + grid_placement 返回 BenchmarkResult
- data: generate_layout 返回布局 dict

来源:
- pytest 文档: https://docs.pytest.org/
- PyTorch autograd 梯度校验: https://pytorch.org/docs/stable/autograd.html
- TILOS MacroPlacement: https://github.com/TILOS-AI-CAD-Institute/MacroPlacement
- Apollo: https://github.com/ASU-LOPE-Group/Apollo
- LiDAR ISPD'25: https://dl.acm.org/doi/10.1145/3698364.3705355
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import numpy as np
import pytest

# 让测试既能从已安装包导入，也能从源码树导入（CI/开发模式）
# polaris-nn 自身 src + 依赖 polaris-core src
_NN_SRC = str(Path(__file__).resolve().parents[1] / "src")
_CORE_SRC = str(Path(__file__).resolve().parents[2] / "core" / "src")
for _p in (_NN_SRC, _CORE_SRC):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from polaris_core import Tensor
from polaris_nn import (
    Adam,
    AdamConfig,
    CircuitSpec,
    Conv2d,
    Linear,
    MultiHeadAttention,
    ReLU,
    ScaledDotProductAttention,
    Sequential,
    evaluate_benchmark,
    generate_dataset,
    generate_layout,
    grid_placement,
    load_apollo_ptc_benchmark,
    load_lidar_ptc_benchmark,
    load_tilos_ariane,
)


# ─── nn smoke tests ───

def test_nn_linear_sequential_adam():
    """Linear + ReLU + Sequential + Adam 前向/反向/优化 smoke test。

    验证:
    - Linear 前向输出 shape 正确
    - Sequential 容器串联前向
    - 反向传播后参数 grad 非空
    - Adam.step() 更新参数（loss 下降）
    """
    np.random.seed(42)
    # 2 层 MLP: 4 → 8 → 1
    model = Sequential(
        Linear(4, 8),
        ReLU(),
        Linear(8, 1),
    )
    opt = Adam(model.parameters(), lr=1e-2, config=AdamConfig())

    x = Tensor(np.random.randn(3, 4), requires_grad=False)
    y_true = Tensor(np.array([[1.0], [0.0], [1.0]]), requires_grad=False)

    # 前向 + MSE loss
    out = model(x)
    assert out.data.shape == (3, 1), f"输出 shape 应为 (3,1)，实际 {out.data.shape}"
    diff = out - y_true
    loss = (diff * diff).sum() * (0.5 / 3)

    # 反向
    loss.backward()
    params = model.parameters()
    assert all(p.grad is not None for p in params), "所有参数应有梯度"

    # 优化前记录 loss，优化一步后 loss 应下降
    loss_before = float(loss.data.sum())
    opt.step()
    opt.zero_grad()

    out2 = model(x)
    diff2 = out2 - y_true
    loss2 = (diff2 * diff2).sum() * (0.5 / 3)
    loss_after = float(loss2.data.sum())
    assert loss_after < loss_before, (
        f"Adam 优化一步后 loss 应下降，before={loss_before} after={loss_after}"
    )


def test_nn_attention():
    """ScaledDotProductAttention + MultiHeadAttention 前向 smoke test。

    验证:
    - ScaledDotProductAttention 前向输出 shape 正确
    - MultiHeadAttention 前向输出 shape 正确
    - MultiHeadAttention 反向传播 w_q/w_k/w_v/w_o 有梯度
    """
    np.random.seed(0)
    seq_len, embed_dim, num_heads = 4, 8, 2

    # ScaledDotProductAttention（numpy 工具实现）
    sdp = ScaledDotProductAttention(dropout=0.0)
    q = np.random.randn(seq_len, embed_dim)
    k = np.random.randn(seq_len, embed_dim)
    v = np.random.randn(seq_len, embed_dim)
    out = sdp(q, k, v)
    assert out.shape == (seq_len, embed_dim), (
        f"SDP 输出 shape 应为 ({seq_len},{embed_dim})，实际 {out.shape}"
    )

    # MultiHeadAttention（可微）
    mha = MultiHeadAttention(embed_dim, num_heads)
    x = Tensor(np.random.randn(seq_len, embed_dim), requires_grad=False)
    out_t = mha(x)
    assert out_t.data.shape == (seq_len, embed_dim), (
        f"MHA 输出 shape 应为 ({seq_len},{embed_dim})，实际 {out_t.data.shape}"
    )

    # 反向：w_q/w_k/w_v/w_o 应有梯度
    out_t.backward(np.ones_like(out_t.data))
    assert mha.w_q.weight.grad is not None, "w_q 应有梯度"
    assert mha.w_k.weight.grad is not None, "w_k 应有梯度"
    assert mha.w_v.weight.grad is not None, "w_v 应有梯度"
    assert mha.w_o.weight.grad is not None, "w_o 应有梯度"


def test_nn_conv2d():
    """Conv2d 前向 smoke test（im2col 实现）。

    验证:
    - Conv2d 前向输出 shape 正确
    - 输出通道数 == out_channels
    """
    np.random.seed(7)
    # 输入 (N=1, C=2, H=8, W=8)
    x = Tensor(np.random.randn(1, 2, 8, 8), requires_grad=False)
    conv = Conv2d(in_channels=2, out_channels=4, kernel_size=3, stride_padding=(1, 1))
    out = conv(x)
    # padding=1, stride=1, kernel=3 → H_out = H = 8
    assert out.data.shape == (1, 4, 8, 8), (
        f"Conv2d 输出 shape 应为 (1,4,8,8)，实际 {out.data.shape}"
    )


# ─── data smoke tests ───

def test_data_benchmark_loaders():
    """TILOS/Apollo/LiDAR benchmark loaders 返回 CircuitSpec smoke test。

    验证:
    - load_tilos_ariane() 返回 CircuitSpec，含 devices/connections
    - load_apollo_ptc_benchmark() 返回 CircuitSpec
    - load_lidar_ptc_benchmark() 返回 CircuitSpec
    """
    ariane = load_tilos_ariane()
    assert isinstance(ariane, CircuitSpec), (
        f"load_tilos_ariane 应返回 CircuitSpec，实际 {type(ariane).__name__}"
    )
    assert len(ariane.devices) > 0, "Ariane benchmark 应含器件"
    assert len(ariane.connections) > 0, "Ariane benchmark 应含连接"

    apollo_ptc = load_apollo_ptc_benchmark()
    assert isinstance(apollo_ptc, CircuitSpec), (
        f"load_apollo_ptc_benchmark 应返回 CircuitSpec，实际 {type(apollo_ptc).__name__}"
    )
    assert len(apollo_ptc.devices) > 0, "Apollo PTC benchmark 应含器件"

    lidar_ptc = load_lidar_ptc_benchmark()
    assert isinstance(lidar_ptc, CircuitSpec), (
        f"load_lidar_ptc_benchmark 应返回 CircuitSpec，实际 {type(lidar_ptc).__name__}"
    )
    assert len(lidar_ptc.devices) > 0, "LiDAR PTC benchmark 应含器件"


def test_data_benchmark_evaluator():
    """evaluate_benchmark + grid_placement smoke test。

    验证:
    - grid_placement 返回 {device_name: (cx, cy)} 字典
    - evaluate_benchmark 返回 BenchmarkResult，含 hpwl_um/overlap_count 字段
    - TILOS Ariane benchmark 的 grid 布局评估达标（overlap_count == 0）
    """
    circuit = load_tilos_ariane()
    placements = grid_placement(circuit)
    assert isinstance(placements, dict), "grid_placement 应返回 dict"
    assert len(placements) == len(circuit.devices), (
        f"placements 数 ({len(placements)}) 应等于 devices 数 ({len(circuit.devices)})"
    )
    for name, (cx, cy) in placements.items():
        assert isinstance(cx, float) and isinstance(cy, float), (
            f"placement[{name}] 坐标应为 float tuple，实际 ({type(cx).__name__},{type(cy).__name__})"
        )

    result = evaluate_benchmark(circuit, placements)
    assert hasattr(result, "hpwl_um"), "BenchmarkResult 应有 hpwl_um 字段"
    assert hasattr(result, "overlap_count"), "BenchmarkResult 应有 overlap_count 字段"
    assert result.overlap_count == 0, (
        f"grid 布局应无重叠，实际 overlap_count={result.overlap_count}"
    )


def test_data_dataset_generator():
    """generate_layout smoke test。

    验证:
    - generate_layout 返回 dict，键为器件名
    - 每个 layout 项含 x/y/w/h 字段
    """
    circuit = load_apollo_ptc_benchmark()
    layout = generate_layout(circuit, seed=42)
    assert isinstance(layout, dict), "generate_layout 应返回 dict"
    assert len(layout) == len(circuit.devices), (
        f"layout 项数 ({len(layout)}) 应等于 devices 数 ({len(circuit.devices)})"
    )
    for name, item in layout.items():
        assert isinstance(item, dict), f"layout[{name}] 应为 dict"
        for key in ("x", "y", "w", "h"):
            assert key in item, f"layout[{name}] 应含 '{key}' 字段"


def test_data_generate_dataset_to_tmpdir():
    """generate_dataset 批量生成数据集到临时目录 smoke test。

    验证:
    - generate_dataset 返回 dict，含 'circuits' 或统计字段
    - 临时目录下生成 JSON 文件
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        result = generate_dataset(tmpdir, n_variations=2)
        assert isinstance(result, dict), "generate_dataset 应返回 dict"
        # 检查临时目录下有文件生成
        files = list(Path(tmpdir).rglob("*.json"))
        assert len(files) > 0, (
            f"generate_dataset 应在 {tmpdir} 下生成 JSON 文件，实际无文件"
        )
