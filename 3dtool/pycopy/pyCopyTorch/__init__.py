"""pyCopyTorch — torch 纯 NumPy 100% 复刻（规则 3）。

复刻 PyTorch 的核心子集：Tensor + autograd + nn.Module + Linear/LayerNorm/ReLU +
Adam 优化器 + Conv2d/MaxPool2d。

原工具: PyTorch https://pytorch.org/ (BSD-3-Clause)
复刻位置: src/polaris/nn/
复刻版本: torch 2.x API 子集

来源:
- PyTorch autograd: https://pytorch.org/docs/stable/autograd.html
- PyTorch nn: https://pytorch.org/docs/stable/nn.html
"""

from polaris.nn import (
    Adam,
    AdamConfig,
    Conv2d,
    Dropout,
    Embedding,
    LayerNorm,
    Linear,
    MaxPool2d,
    Module,
    ReLU,
    Sequential,
    Tanh,
    Tensor,
)

__all__ = [
    "Tensor",
    "Module",
    "Linear",
    "LayerNorm",
    "ReLU",
    "Tanh",
    "Sequential",
    "Adam",
    "AdamConfig",
    "Conv2d",
    "MaxPool2d",
    "Dropout",
    "Embedding",
]
