"""polaris-nn 子模块深度测试（v5.0，覆盖全 API）。

测试覆盖（32 个 pytest）:
- Tensor 基础: cat / index_select / scatter_add / matmul_backward / leaky_relu / segment_softmax
- 层: Linear / ReLU / Tanh / LayerNorm / Sequential / Conv2d / MaxPool2d / Dropout / Embedding
- Attention: ScaledDotProductAttention / MultiHeadAttention / TransformerBlock
- 优化器: Adam / AdamConfig
- 数据: generate_dataset / generate_layout / grid_placement / placement_by_method
- Benchmark: load_ariane / load_apollo / load_lidar / run_all_benchmarks / evaluate_benchmark
- 报告: generate_report / generate_grid_report / generate_comparison_report
- 历史: HistoryTracker / TrendAnalysis / save+load

R02 学术诚信（docstring 含 ≥5 文献 URL）:
- PyTorch torch.nn: https://pytorch.org/docs/stable/nn.html
- Vaswani et al., 2017, "Attention Is All You Need", NeurIPS
  https://arxiv.org/abs/1706.03762
- Kingma & Ba, 2015, "Adam", ICLR https://arxiv.org/abs/1412.6980
- TILOS MacroPlacement: https://github.com/TILOS-AI-CAD-Institute/MacroPlacement
- Apollo: https://github.com/ASU-LOPE-Group/Apollo
- LiDAR ISPD'25: https://dl.acm.org/doi/10.1145/3698364.3705355
- pytest 文档: https://docs.pytest.org/

规则依据: R02 学术诚信 / R03 禁止 fall-back / R05 无 TODO / R04 纯 NumPy
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

from polaris_core import Tensor  # noqa: E402
from polaris_nn import (  # noqa: E402
    Adam,
    AdamConfig,
    BenchmarkReport,
    CircuitSpec,
    Conv2d,
    Dropout,
    Embedding,
    HistoryTracker,
    LayerNorm,
    Linear,
    MaxPool2d,
    MultiHeadAttention,
    ReLU,
    ScaledDotProductAttention,
    Sequential,
    STANDARD_DEVICES,
    Tanh,
    TransformerBlock,
    cat,
    evaluate_benchmark,
    generate_comparison_report,
    generate_dataset,
    generate_grid_report,
    generate_layout,
    generate_report,
    grid_placement,
    index_select,
    leaky_relu,
    load_apollo_onoc,
    load_apollo_ptc,
    load_ariane_benchmark,
    load_lidar_benchmark,
    matmul_backward,
    placement_by_method,
    run_all_benchmarks,
    scatter_add,
    segment_softmax,
)


# ===========================================================================
# 1. 可微函数（functional.py）
# ===========================================================================
def test_cat_axis0_and_axis1():
    """cat 沿轴 0 / 轴 1 拼接，前向 shape 正确。"""
    a = Tensor(np.array([[1.0, 2.0], [3.0, 4.0]]), requires_grad=False)
    b = Tensor(np.array([[5.0, 6.0]]), requires_grad=False)
    out0 = cat([a, b], axis=0)
    assert out0.data.shape == (3, 2), f"axis=0 shape 期望 (3,2)，实际 {out0.data.shape}"
    out1 = cat([a, a], axis=1)
    assert out1.data.shape == (2, 4), f"axis=1 shape 期望 (2,4)，实际 {out1.data.shape}"


def test_cat_empty_raises():
    """cat 空列表必须 raise（R03 禁止 fall-back）。"""
    with pytest.raises(ValueError):
        cat([], axis=0)


def test_cat_backward_splits_grad():
    """cat 反向传播按 size 切分梯度回各 tensor。"""
    a = Tensor(np.ones((2, 2)), requires_grad=True)
    b = Tensor(np.ones((1, 2)) * 3.0, requires_grad=True)
    out = cat([a, b], axis=0)
    out.backward(np.ones((3, 2)))
    # a 梯度应全 1（形状 2x2），b 梯度应全 1（形状 1x2）
    assert a.grad is not None and b.grad is not None
    assert a.grad.shape == (2, 2)
    assert b.grad.shape == (1, 2)
    assert np.allclose(a.grad, 1.0)
    assert np.allclose(b.grad, 1.0)


def test_index_select_forward_and_backward():
    """index_select 前向选取行 + 反向散射梯度。"""
    src = Tensor(np.array([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]]), requires_grad=True)
    idx = np.array([0, 2, 2, 1])
    out = index_select(src, idx)
    assert out.data.shape == (4, 2), f"shape 期望 (4,2)，实际 {out.data.shape}"
    # 第 0 行 = src[0], 第 1 行 = src[2]
    assert np.allclose(out.data[0], [1.0, 2.0])
    assert np.allclose(out.data[1], [5.0, 6.0])
    out.backward(np.ones((4, 2)))
    # src.grad[idx] 累加：src[2] 被选 2 次 → grad=2，其余 grad=1
    assert src.grad is not None
    assert np.allclose(src.grad[0], 1.0)
    assert np.allclose(src.grad[2], 2.0)


def test_scatter_add_forward_and_backward():
    """scatter_add 前向聚合 + 反向收集梯度。"""
    src = Tensor(np.array([[1.0, 1.0], [2.0, 2.0], [3.0, 3.0]]), requires_grad=True)
    dsts = np.array([0, 1, 0])  # 边 0→节点0, 边1→节点1, 边2→节点0
    out = scatter_add(src, dsts, n=2)
    assert out.data.shape == (2, 2), f"shape 期望 (2,2)，实际 {out.data.shape}"
    # 节点0 = src[0]+src[2] = [4,4], 节点1 = src[1] = [2,2]
    assert np.allclose(out.data[0], [4.0, 4.0])
    assert np.allclose(out.data[1], [2.0, 2.0])
    out.backward(np.ones((2, 2)))
    # src.grad[i] = out.grad[dsts[i]] = 1
    assert src.grad is not None
    assert np.allclose(src.grad, 1.0)


def test_matmul_backward_2d():
    """matmul_backward 2D 输入梯度公式: dL/dL = g@R^T, dR = L^T@g。"""
    left = Tensor(np.array([[1.0, 2.0], [3.0, 4.0]]), requires_grad=True)
    right = Tensor(np.array([[5.0, 6.0], [7.0, 8.0]]), requires_grad=True)
    g = np.array([[1.0, 1.0], [1.0, 1.0]])
    matmul_backward(left, right, g)
    # dL = g @ right.T = [[12,14],[12,14]]
    expected_left = g @ right.data.T
    expected_right = left.data.T @ g
    assert left.grad is not None and right.grad is not None
    assert np.allclose(left.grad, expected_left)
    assert np.allclose(right.grad, expected_right)


def test_leaky_relu_forward_and_backward():
    """leaky_relu 前向 where(x>0,x,slope*x) + 反向梯度。"""
    x = Tensor(np.array([-2.0, -1.0, 0.0, 1.0, 2.0]), requires_grad=True)
    out = leaky_relu(x, slope=0.1)
    # x<=0 → 0.1*x, x>0 → x
    expected = np.array([-0.2, -0.1, 0.0, 1.0, 2.0])
    assert np.allclose(out.data, expected)
    out.backward(np.ones_like(out.data))
    # 反向: x>0 → 1, else → slope
    expected_grad = np.array([0.1, 0.1, 0.1, 1.0, 1.0])
    assert x.grad is not None
    assert np.allclose(x.grad, expected_grad)


def test_segment_softmax_group_sums_to_one():
    """segment_softmax 每个 dst 组内权重和为 1。"""
    # 3 条边，2 个目标节点: 边 0,1 → 节点0；边 2 → 节点1
    scores = Tensor(np.array([1.0, 2.0, 3.0]), requires_grad=False)
    dsts = np.array([0, 0, 1])
    alpha = segment_softmax(scores, dsts, n=2)
    # 节点0 组: softmax([1,2]) → 和为 1
    assert abs(alpha.data[0] + alpha.data[1] - 1.0) < 1e-9
    # 节点1 组: softmax([3]) → 1.0
    assert abs(alpha.data[2] - 1.0) < 1e-9
    # 所有权重非负
    assert np.all(alpha.data >= 0.0)


# ===========================================================================
# 2. 基础层与容器（layers.py）
# ===========================================================================
def test_linear_forward_shape_and_bias():
    """Linear 前向输出 shape = (batch, out_features)，weight shape = (out, in)。"""
    np.random.seed(0)
    layer = Linear(in_features=4, out_features=6)
    assert layer.weight.data.shape == (6, 4), (
        f"weight shape 期望 (6,4)，实际 {layer.weight.data.shape}"
    )
    assert layer.bias.data.shape == (6,), (
        f"bias shape 期望 (6,)，实际 {layer.bias.data.shape}"
    )
    x = Tensor(np.random.randn(3, 4), requires_grad=False)
    out = layer(x)
    assert out.data.shape == (3, 6), f"输出 shape 期望 (3,6)，实际 {out.data.shape}"


def test_linear_backward_weight_and_bias_grad():
    """Linear 反向: weight.grad / bias.grad 非 None 且非零。"""
    np.random.seed(1)
    layer = Linear(4, 3)
    x = Tensor(np.random.randn(2, 4), requires_grad=False)
    out = layer(x)
    out.backward(np.ones((2, 3)))
    assert layer.weight.grad is not None, "weight.grad 为 None"
    assert np.any(layer.weight.grad != 0.0), "weight.grad 全零"
    assert layer.bias.grad is not None, "bias.grad 为 None"
    assert np.allclose(layer.bias.grad, 2.0), "bias.grad 应为 batch 求和 = 2"


def test_linear_no_bias():
    """Linear(bias=False) 时 bias 为 None。"""
    layer = Linear(4, 3, bias=False)
    assert layer.bias is None


def test_relu_forward_and_backward():
    """ReLU 前向 max(0,x) + 反向梯度只流过正元素。"""
    x = Tensor(np.array([-1.0, 0.0, 2.0]), requires_grad=True)
    out = ReLU()(x)
    assert np.allclose(out.data, [0.0, 0.0, 2.0])
    out.backward(np.ones(3))
    # x=2 → grad=1, x<=0 → grad=0
    assert np.allclose(x.grad, [0.0, 0.0, 1.0])


def test_tanh_forward_and_backward():
    """Tanh 前向 tanh(x) + 反向 1-tanh²。"""
    x = Tensor(np.array([0.0]), requires_grad=True)
    out = Tanh()(x)
    assert abs(out.data[0] - 0.0) < 1e-12
    out.backward(np.ones(1))
    # tanh(0)=0, d/dx tanh = 1-0 = 1
    assert abs(x.grad[0] - 1.0) < 1e-9


def test_layer_norm_forward_zero_mean_unit_var():
    """LayerNorm 前向: 归一化后均值≈0、方差≈1（gamma=1,beta=0 时）。"""
    ln = LayerNorm(normalized_shape=4)
    # gamma=1, beta=0 初始
    x = Tensor(np.array([[1.0, 2.0, 3.0, 4.0]]), requires_grad=False)
    out = ln(x)
    # 归一化后均值≈0, std≈1（eps 影响）
    assert abs(out.data.mean()) < 1e-6
    assert abs(out.data.var() - 1.0) < 1e-3


def test_sequential_forward_chains_layers():
    """Sequential 串联前向: 4→8→1。"""
    np.random.seed(2)
    model = Sequential(Linear(4, 8), ReLU(), Linear(8, 1))
    x = Tensor(np.random.randn(5, 4), requires_grad=False)
    out = model(x)
    assert out.data.shape == (5, 1), f"输出 shape 期望 (5,1)，实际 {out.data.shape}"
    # parameters 收集应含两层 Linear 的 weight+bias
    params = model.parameters()
    assert len(params) == 4, f"参数数期望 4，实际 {len(params)}"


# ===========================================================================
# 3. 优化器（Adam）
# ===========================================================================
def test_adam_config_defaults():
    """AdamConfig 默认 betas=(0.9,0.999), eps=1e-8, weight_decay=0。"""
    cfg = AdamConfig()
    assert cfg.betas == (0.9, 0.999)
    assert cfg.eps == 1e-8
    assert cfg.weight_decay == 0.0


def test_adam_step_reduces_loss():
    """Adam.step() 后 loss 应下降（单步优化）。"""
    np.random.seed(3)
    model = Sequential(Linear(4, 8), ReLU(), Linear(8, 1))
    opt = Adam(model.parameters(), lr=1e-2)
    x = Tensor(np.random.randn(3, 4), requires_grad=False)
    y_true = Tensor(np.array([[1.0], [0.0], [1.0]]), requires_grad=False)

    def loss_fn(m):
        o = m(x)
        d = o - y_true
        return (d * d).sum()

    loss_before = float(loss_fn(model).data.sum())
    opt.zero_grad()
    loss_fn(model).backward()
    opt.step()
    loss_after = float(loss_fn(model).data.sum())
    assert loss_after < loss_before, (
        f"Adam 优化后 loss 应下降，before={loss_before} after={loss_after}"
    )


def test_adam_add_params_extends_buffers():
    """Adam.add_params 追加参数并扩展动量缓冲区 m/v。"""
    p1 = Tensor(np.zeros(3), requires_grad=True)
    opt = Adam([p1], lr=1e-3)
    assert len(opt.params) == 1 and len(opt.m) == 1 and len(opt.v) == 1
    p2 = Tensor(np.zeros(2), requires_grad=True)
    opt.add_params([p2])
    assert len(opt.params) == 2
    assert len(opt.m) == 2 and len(opt.v) == 2


# ===========================================================================
# 4. 卷积/池化/嵌入（conv.py）
# ===========================================================================
def test_conv2d_forward_shape():
    """Conv2d 前向: (1,2,8,8) + k3s1p1 → (1,4,8,8)。"""
    np.random.seed(4)
    x = Tensor(np.random.randn(1, 2, 8, 8), requires_grad=False)
    conv = Conv2d(in_channels=2, out_channels=4, kernel_size=3, stride_padding=(1, 1))
    out = conv(x)
    assert out.data.shape == (1, 4, 8, 8), f"shape 期望 (1,4,8,8)，实际 {out.data.shape}"


def test_conv2d_backward_weight_and_bias_grad():
    """Conv2d 反向: weight.grad / bias.grad 非 None。"""
    np.random.seed(5)
    x = Tensor(np.random.randn(1, 1, 5, 5), requires_grad=False)
    conv = Conv2d(1, 2, kernel_size=3, stride_padding=(1, 0))
    out = conv(x)
    out.backward(np.ones_like(out.data))
    assert conv.weight.grad is not None, "weight.grad 为 None"
    assert conv.bias.grad is not None, "bias.grad 为 None"
    assert np.any(conv.weight.grad != 0.0), "weight.grad 全零"


def test_maxpool2d_forward_shape_and_values():
    """MaxPool2d 前向: 2x2 池化取最大值。"""
    x = Tensor(np.arange(16, dtype=np.float64).reshape(1, 1, 4, 4), requires_grad=False)
    pool = MaxPool2d(kernel_size=2)
    out = pool(x)
    # 4x4 → 2x2，每 2x2 窗口取 max
    assert out.data.shape == (1, 1, 2, 2), f"shape 期望 (1,1,2,2)，实际 {out.data.shape}"
    # 左上 2x2 窗口 = data[0:2,0:2] = [[0,1],[4,5]] → max=5
    # （arange(16).reshape(4,4) 行优先: 第0行[0,1,2,3], 第1行[4,5,6,7]）
    assert abs(out.data[0, 0, 0, 0] - 5.0) < 1e-12
    # 右下 2x2 窗口 = data[2:4,2:4] = [[10,11],[14,15]] → max=15
    assert abs(out.data[0, 0, 1, 1] - 15.0) < 1e-12


def test_dropout_eval_mode_identity():
    """Dropout eval 模式（training=False）输出 == 输入。"""
    drop = Dropout(p=0.5)
    drop.training = False
    x = Tensor(np.ones((4, 4)), requires_grad=False)
    out = drop(x)
    assert np.allclose(out.data, 1.0), "eval 模式应恒等"


def test_dropout_train_mode_zeroes_and_scales():
    """Dropout train 模式: p=0.5 部分置零，非零元按 1/(1-p)=2 缩放。"""
    np.random.seed(6)
    drop = Dropout(p=0.5)
    x = Tensor(np.ones((100,)), requires_grad=False)
    out = drop(x)
    # 非零元应等于 1/(1-0.5) = 2.0，零元为 0
    nonzero = out.data[out.data != 0.0]
    assert np.allclose(nonzero, 2.0), f"非零元应缩放为 2.0，得到 {nonzero}"
    # 应既有零也有非零（100 个样本 p=0.5 统计上必两者皆有）
    assert np.any(out.data == 0.0), "应有部分被置零"
    assert np.any(out.data != 0.0), "应有部分保留"


def test_embedding_forward_lookup():
    """Embedding 前向查表: 输出 = weight[indices]。

    Embedding.forward 对非 Tensor 输入转 int64 索引；Tensor 输入会
    被 Tensor 构造器转 float64 导致索引失败，故传 ndarray int。
    """
    np.random.seed(7)
    emb = Embedding(num_embeddings=5, embedding_dim=3)
    indices = np.array([0, 2, 4], dtype=np.int64)
    out = emb(indices)
    assert out.data.shape == (3, 3), f"shape 期望 (3,3)，实际 {out.data.shape}"
    # 第 0 行应等于 weight[0]
    assert np.allclose(out.data[0], emb.weight.data[0])
    # 第 1 行应等于 weight[2]
    assert np.allclose(out.data[1], emb.weight.data[2])


# ===========================================================================
# 5. Attention / Transformer（attention.py）
# ===========================================================================
def test_scaled_dot_product_attention_shape():
    """ScaledDotProductAttention 前向输出 shape = (seq, d)。"""
    sdp = ScaledDotProductAttention(dropout=0.0)
    q = np.random.randn(4, 8)
    k = np.random.randn(4, 8)
    v = np.random.randn(4, 8)
    out = sdp(q, k, v)
    assert out.shape == (4, 8), f"shape 期望 (4,8)，实际 {out.shape}"
    # 输出有限
    assert np.all(np.isfinite(out))


def test_multi_head_attention_forward_and_backward():
    """MultiHeadAttention 前向 shape + 反向 w_q/w_k/w_v/w_o 有梯度。"""
    np.random.seed(8)
    mha = MultiHeadAttention(embed_dim=8, num_heads=2)
    x = Tensor(np.random.randn(4, 8), requires_grad=False)
    out = mha(x)
    assert out.data.shape == (4, 8), f"shape 期望 (4,8)，实际 {out.data.shape}"
    out.backward(np.ones_like(out.data))
    for attr in ("w_q", "w_k", "w_v", "w_o"):
        layer = getattr(mha, attr)
        assert layer.weight.grad is not None, f"{attr}.weight.grad 为 None"
        assert np.any(layer.weight.grad != 0.0), f"{attr}.weight.grad 全零"


def test_multi_head_attention_invalid_heads_raises():
    """embed_dim 不能被 num_heads 整除时 raise（R03）。"""
    with pytest.raises(ValueError):
        MultiHeadAttention(embed_dim=7, num_heads=2)


def test_transformer_block_forward_and_backward():
    """TransformerBlock 前向 shape + 反向所有参数有梯度。"""
    np.random.seed(9)
    tb = TransformerBlock(embed_dim=8, num_heads=2)
    x = Tensor(np.random.randn(4, 8), requires_grad=True)
    out = tb(x)
    assert out.data.shape == (4, 8), f"shape 期望 (4,8)，实际 {out.data.shape}"
    out.backward(np.ones_like(out.data))
    params = tb.parameters()
    assert len(params) > 0, "TransformerBlock 无可训练参数"
    for i, p in enumerate(params):
        assert p.grad is not None, f"参数 #{i} 梯度为 None"
    # 残差路径梯度流回输入
    assert x.grad is not None, "残差路径梯度未流回 x"
    assert np.any(x.grad != 0.0), "x.grad 全零"


# ===========================================================================
# 6. 数据生成与布局（dataset_generator / benchmark_evaluator）
# ===========================================================================
def test_standard_devices_present():
    """STANDARD_DEVICES 含核心器件类型。"""
    for name in ("mzi", "ring_single", "dc", "mmi1x2", "y_branch", "gc", "heater", "wg_100"):
        assert name in STANDARD_DEVICES, f"STANDARD_DEVICES 缺少 {name}"


def test_generate_layout_returns_dict():
    """generate_layout 返回 {device: {x,y,w,h}}。"""
    circuit = load_ariane_benchmark()
    layout = generate_layout(circuit, seed=42)
    assert isinstance(layout, dict)
    assert len(layout) == len(circuit.devices)
    for item in layout.values():
        for key in ("x", "y", "w", "h"):
            assert key in item, f"layout 项缺少 '{key}'"


def test_generate_dataset_to_tmpdir():
    """generate_dataset 批量生成 JSON 文件到临时目录。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        stats = generate_dataset(tmpdir, n_variations=2)
        assert isinstance(stats, dict)
        assert stats.get("total_variations", 0) > 0, "应生成变体"
        files = list(Path(tmpdir).rglob("*.json"))
        assert len(files) > 0, f"应在 {tmpdir} 下生成 JSON 文件"


def test_grid_placement_no_overlap():
    """grid_placement 返回布局且 evaluate 后 overlap_count == 0。"""
    circuit = load_ariane_benchmark()
    placements = grid_placement(circuit)
    assert len(placements) == len(circuit.devices)
    result = evaluate_benchmark(circuit, placements)
    assert result.overlap_count == 0, f"grid 布局应无重叠，实际 {result.overlap_count}"


def test_placement_by_method_grid():
    """placement_by_method('grid') 返回布局字典。"""
    circuit = load_ariane_benchmark()
    placements = placement_by_method(circuit, "grid")
    assert isinstance(placements, dict)
    assert len(placements) == len(circuit.devices)


def test_placement_by_method_analytical_raises():
    """placement_by_method('analytical') raise RuntimeError（polaris-nn 无引擎，R03）。"""
    circuit = load_ariane_benchmark()
    with pytest.raises(RuntimeError):
        placement_by_method(circuit, "analytical")


def test_placement_by_method_unknown_raises():
    """placement_by_method 未知方法 raise ValueError。"""
    circuit = load_ariane_benchmark()
    with pytest.raises(ValueError):
        placement_by_method(circuit, "unknown_method")


# ===========================================================================
# 7. Benchmark loaders + 评估 + 报告
# ===========================================================================
def test_load_ariane_benchmark_returns_circuit():
    """load_ariane_benchmark 返回 CircuitSpec，含 17 模块 + 25 连接。"""
    circuit = load_ariane_benchmark()
    assert isinstance(circuit, CircuitSpec)
    assert len(circuit.devices) == 17, f"Ariane 模块数期望 17，实际 {len(circuit.devices)}"
    assert len(circuit.connections) == 25, f"Ariane 连接数期望 25，实际 {len(circuit.connections)}"


def test_load_apollo_ptc_and_onoc():
    """load_apollo_ptc / load_apollo_onoc 返回 CircuitSpec。"""
    ptc = load_apollo_ptc()
    onoc = load_apollo_onoc()
    assert isinstance(ptc, CircuitSpec) and isinstance(onoc, CircuitSpec)
    assert len(ptc.devices) > 0
    assert len(onoc.devices) > 0


def test_load_lidar_benchmark():
    """load_lidar_benchmark 返回 CircuitSpec。"""
    lidar = load_lidar_benchmark()
    assert isinstance(lidar, CircuitSpec)
    assert len(lidar.devices) > 0


def test_evaluate_benchmark_returns_result():
    """evaluate_benchmark 返回 BenchmarkResult，含全部指标字段。"""
    circuit = load_ariane_benchmark()
    placements = grid_placement(circuit)
    result = evaluate_benchmark(circuit, placements)
    assert hasattr(result, "hpwl_um")
    assert hasattr(result, "overlap_count")
    assert hasattr(result, "area_utilization")
    assert hasattr(result, "passed")
    assert result.hpwl_um > 0, "HPWL 应 > 0"


def test_generate_report_returns_benchmark_report():
    """generate_report 返回 BenchmarkReport。"""
    circuit = load_ariane_benchmark()
    placements = grid_placement(circuit)
    report = generate_report(circuit, placements, placement_method="grid")
    assert isinstance(report, BenchmarkReport)
    assert report.placement_method == "grid"
    assert report.module_count == len(circuit.devices)


def test_generate_grid_report():
    """generate_grid_report 用 grid 布局生成报告。"""
    circuit = load_ariane_benchmark()
    report = generate_grid_report(circuit)
    assert isinstance(report, BenchmarkReport)
    assert report.placement_method == "grid"


def test_generate_comparison_report_stats():
    """generate_comparison_report 汇总多报告统计。"""
    circuit = load_ariane_benchmark()
    placements = grid_placement(circuit)
    r1 = generate_report(circuit, placements)
    # 手动构造第二个报告（不同 HPWL）
    r2 = BenchmarkReport(
        benchmark_name="test2", benchmark_source="CUSTOM", placement_method="grid",
        hpwl_um=1000.0, overlap_count=0, area_utilization=0.3, module_count=5,
        connection_count=4, target_metric="hpwl", target_value=100000.0, passed=True,
        process_node="NanGate45",
    )
    comp = generate_comparison_report([r1, r2])
    assert comp.total_benchmarks == 2
    assert comp.passed_count >= 1
    assert comp.avg_hpwl_um > 0


def test_run_all_benchmarks_returns_comparison():
    """run_all_benchmarks 返回 ComparisonReport，含 4 个 benchmark。"""
    comp = run_all_benchmarks(placement_method="grid")
    assert comp.total_benchmarks == 4, (
        f"benchmark 数期望 4（TILOS+Apollo PTC+oNoC+LiDAR），实际 {comp.total_benchmarks}"
    )
    assert len(comp.reports) == 4
    # 每个报告应有非负 HPWL
    for r in comp.reports:
        assert r.hpwl_um >= 0


# ===========================================================================
# 8. 历史趋势追踪（benchmark_history.py）
# ===========================================================================
def _make_report(name: str, hpwl: float, passed: bool = True) -> BenchmarkReport:
    """构造测试用 BenchmarkReport。"""
    return BenchmarkReport(
        benchmark_name=name, benchmark_source="CUSTOM", placement_method="grid",
        hpwl_um=hpwl, overlap_count=0, area_utilization=0.4, module_count=10,
        connection_count=9, target_metric="hpwl", target_value=100000.0, passed=passed,
        process_node="NanGate45",
    )


def test_history_tracker_add_and_list():
    """HistoryTracker.add_record + list_benchmarks。"""
    tracker = HistoryTracker()
    tracker.add_record(_make_report("bm_a", 100.0))
    tracker.add_record(_make_report("bm_b", 200.0))
    assert sorted(tracker.list_benchmarks()) == ["bm_a", "bm_b"]


def test_history_tracker_analyze_trend_improving():
    """HistoryTracker.analyze_trend: HPWL 递减 → trend_direction=improving。"""
    tracker = HistoryTracker()
    # 三次评估 HPWL 递减: 100 → 80 → 60
    tracker.add_record(_make_report("bm_x", 100.0))
    tracker.add_record(_make_report("bm_x", 80.0))
    tracker.add_record(_make_report("bm_x", 60.0))
    trend = tracker.analyze_trend("bm_x")
    assert trend is not None
    assert trend.entry_count == 3
    assert trend.first_hpwl_um == 100.0
    assert trend.last_hpwl_um == 60.0
    assert trend.best_hpwl_um == 60.0
    assert trend.improvement_vs_first > 0, "HPWL 递减 → 改进幅度 > 0"
    assert trend.trend_direction == "improving"


def test_history_tracker_save_and_load():
    """HistoryTracker.save + load 往返一致。"""
    tracker = HistoryTracker()
    tracker.add_record(_make_report("bm_y", 100.0), commit_hash="abc123", notes="v1")
    tracker.add_record(_make_report("bm_y", 90.0), commit_hash="def456", notes="v2")
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "history.json"
        tracker.save(path)
        assert path.exists()
        tracker2 = HistoryTracker()
        tracker2.load(path)
        assert "bm_y" in tracker2.list_benchmarks()
        trend = tracker2.analyze_trend("bm_y")
        assert trend is not None
        assert trend.entry_count == 2


def test_history_tracker_regression_detection():
    """HistoryTracker 检测回归: 最近 HPWL 相对最佳恶化 > 阈值。"""
    tracker = HistoryTracker(regression_threshold=5.0)
    tracker.add_record(_make_report("bm_z", 100.0))
    tracker.add_record(_make_report("bm_z", 80.0))   # 最佳
    tracker.add_record(_make_report("bm_z", 120.0))  # 恶化 50% > 5%
    trend = tracker.analyze_trend("bm_z")
    assert trend is not None
    assert trend.regression_detected is True


def test_history_tracker_empty_trend_returns_none():
    """无记录时 analyze_trend 返回 None。"""
    tracker = HistoryTracker()
    assert tracker.analyze_trend("nonexistent") is None
