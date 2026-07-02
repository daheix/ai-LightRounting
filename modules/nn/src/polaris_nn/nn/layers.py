"""神经网络层与优化器（复刻 ``torch.nn`` 子集）。

从 v4 旧包 ``src/polaris/nn/__init__.py`` 迁移，删除旧包依赖，
``Tensor`` 改为从 ``polaris_core`` 导入（polaris-core 已含完整自动微分）。

本模块含:
- ``Module``: 神经网络模块基类（复刻 ``torch.nn.Module``）
- ``Linear``: 线性层 ``y = x @ W^T + b``（复刻 ``torch.nn.Linear``）
- ``ReLU``/``Tanh``: 激活函数
- ``LayerNorm``: 层归一化（Ba et al., 2016）
- ``Sequential``: 顺序容器（复刻 ``torch.nn.Sequential``）
- ``Adam``/``AdamConfig``: Adam 优化器（Kingma & Ba, 2015）

来源（R02 学术诚信，公式/算法均可溯源）:
- PyTorch torch.nn: https://pytorch.org/docs/stable/nn.html
- PyTorch torch.nn.Linear: https://pytorch.org/docs/stable/generated/torch.nn.Linear
- PyTorch torch.nn.LayerNorm: https://pytorch.org/docs/stable/generated/torch.nn.LayerNorm
- PyTorch torch.optim.Adam: https://pytorch.org/docs/stable/generated/torch.optim.Adam
- Saxe et al., 2013, orthogonal 初始化
  https://arxiv.org/abs/1312.6120
- He et al., 2015, Kaiming uniform 初始化（torch.nn.Linear 默认）
  https://arxiv.org/abs/1502.01852
- Ba et al., 2016, "Layer Normalization"
  https://arxiv.org/abs/1607.06450
- Kingma & Ba, 2015, "Adam: A Method for Stochastic Optimization", ICLR
  https://arxiv.org/abs/1412.6980
- Glorot & Bengio, 2010, "Understanding the difficulty of training deep
  feedforward neural networks", AISTATS
  http://proceedings.mlr.press/v9/glorot10a/glorot10a.pdf
- NumPy dtype promotion: https://numpy.org/doc/stable/reference/arrays.promotion.html
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from polaris_core import Tensor


# ---------------------------------------------------------------------------
# Module（复刻 torch.nn.Module）
# ---------------------------------------------------------------------------
class Module:
    """神经网络模块基类（复刻 ``torch.nn.Module``）。

    来源: PyTorch torch.nn.Module
    https://pytorch.org/docs/stable/generated/torch.nn.Module.html
    """

    def parameters(self) -> list[Tensor]:
        """递归收集所有 requires_grad=True 的 Tensor 参数。"""
        params: list[Tensor] = []
        seen: set[int] = set()

        def collect(obj):
            if isinstance(obj, Tensor):
                if obj.requires_grad and id(obj) not in seen:
                    seen.add(id(obj))
                    params.append(obj)
                return
            if isinstance(obj, Module):
                for v in vars(obj).values():
                    collect(v)
                return
            if isinstance(obj, (list, tuple)):
                for item in obj:
                    collect(item)
                return
            if isinstance(obj, dict):
                for item in obj.values():
                    collect(item)

        collect(self)
        return params

    def zero_grad(self) -> None:
        for p in self.parameters():
            p.grad = None

    def __call__(self, *args, **kwargs):
        return self.forward(*args, **kwargs)

    def forward(self, *args, **kwargs):
        raise NotImplementedError


def _init_weight(in_features: int, out_features: int, init: str) -> np.ndarray:
    """权重初始化（orthogonal / kaiming_uniform / xavier）。

    统一使用 float64 dtype，确保数值精度一致性（NumPy dtype 最佳实践）。

    Args:
        in_features: 输入特征维度。
        out_features: 输出特征维度。
        init: 初始化方法（``"orthogonal"`` / 其他 → kaiming_uniform）。

    Returns:
        权重矩阵 ``[out_features, in_features]``，dtype=float64。

    来源:
    - orthogonal: Saxe et al., 2013, https://arxiv.org/abs/1312.6120
    - kaiming_uniform: He et al., 2015, torch.nn.Linear 默认
      https://arxiv.org/abs/1502.01852
    - NumPy dtype promotion: https://numpy.org/doc/stable/reference/arrays.promotion.html
    """
    if init == "orthogonal":
        flat_shape = (out_features, in_features)
        a = np.random.randn(*flat_shape).astype(np.float64)
        u, s, vt = np.linalg.svd(a, full_matrices=False)
        q = u if a.shape[0] >= a.shape[1] else vt
        weight = q.reshape(flat_shape)
        scale = 1.0 / np.sqrt(in_features)
        return (weight * scale).astype(np.float64)
    bound = 1.0 / np.sqrt(in_features)
    return np.random.uniform(-bound, bound, (out_features, in_features)).astype(np.float64)


class Linear(Module):
    """线性层（复刻 ``torch.nn.Linear``）。

    ``y = x @ W^T + b``，``weight.shape == (out_features, in_features)``，
    ``bias.shape == (out_features,)``。

    初始化默认使用 orthogonal 初始化（来源: Saxe et al., 2013,
    "Exact solutions to the nonlinear dynamics of learning in deep
    linear networks", https://arxiv.org/abs/1312.6120），比 Kaiming
    uniform 在 RL 中收敛更快、更稳定（已被 SB3/PPO 广泛验证）。

    来源:
    - PyTorch torch.nn.Linear: https://pytorch.org/docs/stable/generated/torch.nn.Linear
    - Saxe et al., 2013, orthogonal 初始化: https://arxiv.org/abs/1312.6120
    """

    def __init__(
        self,
        in_features: int,
        out_features: int,
        bias: bool = True,
        init: str = "orthogonal",
    ) -> None:
        self.in_features = in_features
        self.out_features = out_features
        self.weight = Tensor(
            _init_weight(in_features, out_features, init),
            requires_grad=True,
        )
        if bias:
            self.bias = Tensor(np.zeros(out_features), requires_grad=True)
        else:
            self.bias = None

    def forward(self, x: Tensor) -> Tensor:
        out = x @ self.weight.T if isinstance(x, Tensor) else Tensor(x) @ self.weight.T
        if self.bias is not None:
            out = out + self.bias
        return out


class ReLU(Module):
    """ReLU 激活（复刻 ``torch.nn.ReLU``）。

    来源: PyTorch torch.nn.ReLU
    https://pytorch.org/docs/stable/generated/torch.nn.ReLU
    """

    def forward(self, x: Tensor) -> Tensor:
        return x.relu()


class Tanh(Module):
    """Tanh 激活（复刻 ``torch.nn.Tanh``）。

    来源: PyTorch torch.nn.Tanh
    https://pytorch.org/docs/stable/generated/torch.nn.Tanh
    """

    def forward(self, x: Tensor) -> Tensor:
        return x.tanh()


class LayerNorm(Module):
    """层归一化（复刻 ``torch.nn.LayerNorm``）。

    对最后一维归一化：``y = (x - mean) / sqrt(var + eps) * gamma + beta``。

    来源:
    - Ba et al., 2016, "Layer Normalization", https://arxiv.org/abs/1607.06450
    - torch.nn.LayerNorm: https://pytorch.org/docs/stable/generated/torch.nn.LayerNorm.html
    """

    def __init__(self, normalized_shape: int, eps: float = 1e-5) -> None:
        self.normalized_shape = normalized_shape
        self.eps = eps
        self.gamma = Tensor(np.ones(normalized_shape), requires_grad=True)
        self.beta = Tensor(np.zeros(normalized_shape), requires_grad=True)

    def forward(self, x: Tensor) -> Tensor:
        data = x.data if isinstance(x, Tensor) else np.asarray(x, dtype=np.float64)
        mean = data.mean(axis=-1, keepdims=True)
        var = data.var(axis=-1, keepdims=True)
        normed = (data - mean) / np.sqrt(var + self.eps)
        out = Tensor(normed, x.requires_grad if isinstance(x, Tensor) else False, (x,))

        def _back(g):
            if isinstance(x, Tensor) and x.requires_grad:
                x._ensure_grad()
                n = data.shape[-1]
                std_inv = 1.0 / np.sqrt(var + self.eps)
                dx = (
                    std_inv
                    / n
                    * (
                        n * g
                        - g.sum(axis=-1, keepdims=True)
                        - normed * (g * normed).sum(axis=-1, keepdims=True)
                    )
                )
                x.grad = x.grad + dx

        out._backward = _back
        # 应用 gamma + beta（可微）
        return out * self.gamma + self.beta


class Sequential(Module):
    """顺序容器（复刻 ``torch.nn.Sequential``）。

    来源: PyTorch torch.nn.Sequential
    https://pytorch.org/docs/stable/generated/torch.nn.Sequential
    """

    def __init__(self, *layers: Module) -> None:
        self.layers = list(layers)

    def forward(self, x: Tensor) -> Tensor:
        for layer in self.layers:
            x = layer(x)
        return x


# ---------------------------------------------------------------------------
# 优化器（复刻 torch.optim）
# ---------------------------------------------------------------------------
@dataclass
class AdamConfig:
    """Adam 优化器超参数配置（复刻 ``torch.optim.Adam`` 默认值）。

    将 betas/eps/weight_decay 聚合为单一配置对象，以降低
    ``Adam.__init__`` 的参数个数（质量门禁：函数参数上限）。

    来源: Kingma & Ba, 2015, Adam 论文；torch.optim.Adam 默认实现。
    https://arxiv.org/abs/1412.6980
    """

    betas: tuple[float, float] = (0.9, 0.999)
    eps: float = 1e-8
    weight_decay: float = 0.0


class Adam:
    """Adam 优化器（复刻 ``torch.optim.Adam``，默认 eps=1e-8, betas=(0.9,0.999)）。

    实现与 torch Adam 一致：偏置修正的一阶/二阶矩估计。
    来源: Kingma & Ba, 2015, Adam 论文；torch.optim.Adam 实现。
    https://arxiv.org/abs/1412.6980
    """

    def __init__(
        self,
        params: list[Tensor],
        lr: float = 1e-3,
        config: AdamConfig | None = None,
    ) -> None:
        cfg = config or AdamConfig()
        self.params = list(params)
        self.lr = lr
        self.beta1, self.beta2 = cfg.betas
        self.eps = cfg.eps
        self.weight_decay = cfg.weight_decay
        self.m = [np.zeros_like(p.data) for p in self.params]
        self.v = [np.zeros_like(p.data) for p in self.params]
        self.t = 0

    def add_params(self, params: list[Tensor]) -> None:
        """向优化器追加参数（同步扩展动量缓冲区 m/v）。

        Args:
            params: 待追加的可训练参数列表。
        """
        for p in params:
            self.params.append(p)
            self.m.append(np.zeros_like(p.data))
            self.v.append(np.zeros_like(p.data))

    def zero_grad(self) -> None:
        for p in self.params:
            p.grad = None

    def step(self) -> None:
        self.t += 1
        for i, p in enumerate(self.params):
            if p.grad is None:
                continue
            g = p.grad
            if self.weight_decay != 0:
                g = g + self.weight_decay * p.data
            self.m[i] = self.beta1 * self.m[i] + (1 - self.beta1) * g
            self.v[i] = self.beta2 * self.v[i] + (1 - self.beta2) * (g * g)
            m_hat = self.m[i] / (1 - self.beta1**self.t)
            v_hat = self.v[i] / (1 - self.beta2**self.t)
            p.data = p.data - self.lr * m_hat / (np.sqrt(v_hat) + self.eps)


__all__ = [
    "Module",
    "Linear",
    "ReLU",
    "Tanh",
    "LayerNorm",
    "Sequential",
    "Adam",
    "AdamConfig",
]
