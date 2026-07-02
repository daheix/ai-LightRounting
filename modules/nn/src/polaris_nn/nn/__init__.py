"""polaris-nn 神经网络子包。

从 v4 旧包 ``src/polaris/nn/``（4 文件）迁移，删除旧包依赖，
统一从 ``polaris_core`` 导入 ``Tensor`` 基类（polaris-core 已含完整
自动微分实现），本子包只保留 nn 层与优化器实现。

迁移要点:
- ``Tensor`` 类已在 polaris-core 实现（含 reshape/flatten/softmax/exp
  等全部前向+反向），本子包不再重复，统一从 ``polaris_core`` 导入。
- ``Module``/``Linear``/``ReLU``/``LayerNorm``/``Tanh``/``Sequential``/
  ``Adam``/``AdamConfig`` 拆分至 ``layers.py``（控制单文件行数 ≤ 500）。
- ``Conv2d``/``MaxPool2d``/``Dropout``/``Embedding`` 在 ``conv.py``。
- ``ScaledDotProductAttention``/``MultiHeadAttention``/``TransformerBlock``
  在 ``attention.py``。
- ``cat``/``scatter_add``/``index_select``/``matmul_backward``/
  ``leaky_relu``/``segment_softmax`` 在 ``functional.py``。

来源（R02 学术诚信）:
- PyTorch torch.nn: https://pytorch.org/docs/stable/nn.html
- Vaswani et al., 2017, "Attention Is All You Need", NeurIPS
  https://arxiv.org/abs/1706.03762
- Kingma & Ba, 2015, "Adam: A Method for Stochastic Optimization", ICLR
  https://arxiv.org/abs/1412.6980
- Saxe et al., 2013, orthogonal 初始化
  https://arxiv.org/abs/1312.6120
- Ba et al., 2016, "Layer Normalization"
  https://arxiv.org/abs/1607.06450
- LeCun et al., 1998, CNN 原始论文
  https://ieeexplore.ieee.org/document/726791
"""

from __future__ import annotations

from polaris_core import Tensor

from polaris_nn.nn.attention import (
    MultiHeadAttention,
    ScaledDotProductAttention,
    TransformerBlock,
)
from polaris_nn.nn.conv import Conv2d, Dropout, Embedding, MaxPool2d
from polaris_nn.nn.functional import (
    cat,
    index_select,
    leaky_relu,
    matmul_backward,
    scatter_add,
    segment_softmax,
)
from polaris_nn.nn.layers import (
    Adam,
    AdamConfig,
    LayerNorm,
    Linear,
    Module,
    ReLU,
    Sequential,
    Tanh,
)

__all__ = [
    # Tensor（re-export from polaris_core，便于上层 nn 代码无需切换 import）
    "Tensor",
    # 基础层与容器
    "Module",
    "Linear",
    "ReLU",
    "LayerNorm",
    "Tanh",
    "Sequential",
    # 优化器
    "Adam",
    "AdamConfig",
    # 卷积/池化/嵌入
    "Conv2d",
    "MaxPool2d",
    "Dropout",
    "Embedding",
    # Attention / Transformer
    "ScaledDotProductAttention",
    "MultiHeadAttention",
    "TransformerBlock",
    # 可微函数
    "cat",
    "scatter_add",
    "index_select",
    "matmul_backward",
    "leaky_relu",
    "segment_softmax",
]
