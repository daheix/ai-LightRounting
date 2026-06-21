"""pyCopyTorch — torch 纯 NumPy 100% 复刻（规则 3/21）。

复刻 PyTorch 的核心子集：Tensor + autograd + nn.Module + Linear/LayerNorm/ReLU +
Adam 优化器 + Conv2d/MaxPool2d。

原工具: PyTorch https://pytorch.org/ (BSD-3-Clause)
复刻位置: src/polaris/nn/
复刻版本: torch 2.x API 子集

版本历史: 见 VERSION.md
- v1.0.0 (2026-06-21): 100% 复刻完成，14 个对比测试通过

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

__version__ = "1.0.0"

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
    "__version__",
]
