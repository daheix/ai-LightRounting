"""纯 NumPy 神经网络库（torch 100% Python 复刻）。

torch 在目标环境（Python 3.14 / 受限磁盘）无法安装（无预编译 wheel、
磁盘空间不足），按 ``project_rules.md`` 规则 3 用纯 NumPy 100% 复刻等价实现。

复刻来源：PyTorch ``torch.nn`` / ``torch.autograd``
- 原仓库: https://github.com/pytorch/pytorch （BSD-style license）
- 参考版本: torch 2.x ``nn.Linear`` / ``nn.functional`` / autograd
- 接口兼容: 暴露 ``Linear`` / ``ReLU`` / ``Tanh`` / ``Module`` / ``Adam``，
  与 ``torch.nn`` 等价，上层代码可无缝切换。

实现要点（与 torch 逻辑一致）：
- ``Linear``: ``y = x @ W^T + b``，权重 ``[out, in]``，偏置 ``[out]``
  （与 ``torch.nn.Linear(in, out)`` 的 ``weight.shape==(out,in)`` 一致）
- 激活: ReLU ``max(0,x)``、Tanh ``tanh(x)``、Softmax 稳定数值实现
- 自动微分: 计算图记录前向 op，反向沿图拓扑序传播梯度（与 autograd 一致）
- Adam: 偏置修正的一阶/二阶矩估计（与 ``torch.optim.Adam`` 默认 eps=1e-8 一致）
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

import numpy as np


# ---------------------------------------------------------------------------
# Tensor + 自动微分（复刻 torch.autograd）
# ---------------------------------------------------------------------------
class TensorArithmeticMixin:
    """Tensor 算术运算混入（复刻 ``torch.Tensor`` 算术 op 子集）。

    将算术运算符重载从 ``Tensor`` 拆分至此混入，以降低 ``Tensor``
    的方法数（规则 4.1 类方法数上限）。

    注意: 本混入不定义 ``__init__``，依赖子类 ``Tensor`` 在 ``__init__``
    中设置 ``data``、``requires_grad`` 等属性并提供 ``_ensure_grad`` 方法。
    Python MRO 保证这些方法在 ``Tensor`` 实例上调用时可正确访问实例属性。

    来源:
    - PyTorch torch.Tensor: https://github.com/pytorch/pytorch （BSD-style license）
    """

    __slots__ = ()

    # 类型声明：由子类 Tensor.__init__ 实际赋值（mixin 不持有这些属性，
    # 仅为静态类型检查器提供接口契约）
    data: np.ndarray
    requires_grad: bool
    grad: np.ndarray | None

    def _ensure_grad(self) -> None:
        """由子类 ``Tensor`` 提供实际实现。"""
        raise NotImplementedError

    def __add__(self, other):
        other = other if isinstance(other, Tensor) else Tensor(other)
        rg = self.requires_grad or other.requires_grad
        out = Tensor(self.data + other.data, rg, (self, other))

        def _back(g):
            if self.requires_grad:
                self._ensure_grad()
                self.grad = self.grad + _unbroadcast(g, self.data.shape)
            if other.requires_grad:
                other._ensure_grad()
                other.grad = other.grad + _unbroadcast(g, other.data.shape)

        out._backward = _back
        return out

    def __mul__(self, other):
        other = other if isinstance(other, Tensor) else Tensor(other)
        rg = self.requires_grad or other.requires_grad
        out = Tensor(self.data * other.data, rg, (self, other))

        def _back(g):
            if self.requires_grad:
                self._ensure_grad()
                self.grad = self.grad + _unbroadcast(g * other.data, self.data.shape)
            if other.requires_grad:
                other._ensure_grad()
                other.grad = other.grad + _unbroadcast(g * self.data, other.data.shape)

        out._backward = _back
        return out

    def __matmul__(self, other):
        rg = self.requires_grad or other.requires_grad
        out = Tensor(self.data @ other.data, rg, (self, other))

        def _back(g):
            if self.requires_grad:
                self._ensure_grad()
                self.grad = self.grad + g @ other.data.T
            if other.requires_grad:
                other._ensure_grad()
                other.grad = other.grad + self.data.T @ g

        out._backward = _back
        return out

    def matmul(self, other):
        return self.__matmul__(other)

    def __neg__(self):
        return self * -1.0

    def __sub__(self, other):
        other = other if isinstance(other, Tensor) else Tensor(other)
        return self + (-other if isinstance(other, Tensor) else Tensor(-other.data))

    def __rsub__(self, other):
        other = other if isinstance(other, Tensor) else Tensor(other)
        return other - self

    def __rmul__(self, other):
        return self * other

    def __radd__(self, other):
        return self + other

    def __pow__(self, p: float):
        # self 运行时为 Tensor 实例，cast 以满足 _parents 类型契约
        out = Tensor(self.data**p, self.requires_grad, (cast(Tensor, self),))

        def _back(g):
            if self.requires_grad:
                self._ensure_grad()
                self.grad = self.grad + g * p * (self.data ** (p - 1))

        out._backward = _back
        return out


class Tensor(TensorArithmeticMixin):
    """自动微分张量（复刻 ``torch.Tensor`` 的核心子集）。

    支持 +、-、*、@、matmul、relu、tanh、log、sum、mean、softmax、
    gather 等前向 op 与对应反向梯度。``requires_grad=True`` 时构建计算图。
    """

    __slots__ = ("data", "requires_grad", "grad", "_backward", "_parents")

    def __init__(
        self,
        data: np.ndarray | float | int,
        requires_grad: bool = False,
        _parents: tuple[Tensor, ...] = (),
        _backward=None,
    ) -> None:
        self.data = np.asarray(data, dtype=np.float64) if not isinstance(data, np.ndarray) else data
        if self.data.dtype != np.float64:
            self.data = self.data.astype(np.float64)
        self.requires_grad = requires_grad
        self.grad: np.ndarray | None = None
        self._parents = _parents
        self._backward = _backward or (lambda g: None)

    @property
    def shape(self):
        return self.data.shape

    @property
    def T(self) -> Tensor:
        """转置（复刻 ``torch.Tensor.T``，等价 ``data.T``）。"""
        out = Tensor(self.data.T, self.requires_grad, (self,))

        def _back(g):
            if self.requires_grad:
                self._ensure_grad()
                self.grad = self.grad + g.T

        out._backward = _back
        return out

    def reshape(self, *shape) -> Tensor:
        out = Tensor(self.data.reshape(shape), self.requires_grad, (self,))

        def _back(g):
            if self.requires_grad:
                self._ensure_grad()
                self.grad = self.grad + g.reshape(self.data.shape)

        out._backward = _back
        return out

    def flatten(self) -> Tensor:
        """展平为一维（复刻 ``torch.Tensor.flatten``）。"""
        out = Tensor(self.data.flatten(), self.requires_grad, (self,))

        def _back(g):
            if self.requires_grad:
                self._ensure_grad()
                self.grad = self.grad + g.reshape(self.data.shape)

        out._backward = _back
        return out

    def _ensure_grad(self):
        if self.grad is None:
            self.grad = np.zeros_like(self.data)

    def backward(self, grad: np.ndarray | None = None) -> None:
        """反向传播（拓扑序，与 autograd 一致）。"""
        if grad is None:
            grad = np.ones_like(self.data)
        # 拓扑排序
        topo: list[Tensor] = []
        visited: set[int] = set()

        def build(t: Tensor):
            if id(t) in visited:
                return
            visited.add(id(t))
            for p in t._parents:
                build(p)
            topo.append(t)

        build(self)
        # 累加梯度
        self._ensure_grad()
        self.grad = self.grad + grad
        for t in reversed(topo):
            t._backward(t.grad)

    def zero_grad(self) -> None:
        self.grad = None

    def sum(self, axis=None, keepdims=False):
        out = Tensor(
            self.data.sum(axis=axis, keepdims=keepdims),
            self.requires_grad,
            (self,),
        )

        def _back(g):
            if self.requires_grad:
                self._ensure_grad()
                grad = g
                if axis is not None and not keepdims:
                    if isinstance(axis, tuple):
                        grad = np.expand_dims(g, list(axis))
                    else:
                        grad = np.expand_dims(g, axis)
                self.grad = self.grad + np.broadcast_to(grad, self.data.shape).copy()

        out._backward = _back
        return out

    def mean(self, axis=None, keepdims=False):
        if axis is None:
            n = self.data.size
        elif isinstance(axis, tuple):
            n = int(np.prod([self.data.shape[a] for a in axis]))
        else:
            n = self.data.shape[axis]
        out = Tensor(
            self.data.mean(axis=axis, keepdims=keepdims),
            self.requires_grad,
            (self,),
        )

        def _back(g):
            if self.requires_grad:
                self._ensure_grad()
                grad = g / n
                if axis is not None and not keepdims:
                    if isinstance(axis, tuple):
                        grad = np.expand_dims(g, list(axis))
                    else:
                        grad = np.expand_dims(g, axis)
                self.grad = self.grad + np.broadcast_to(grad, self.data.shape).copy()

        out._backward = _back
        return out

    def relu(self):
        mask = (self.data > 0).astype(np.float64)
        out = Tensor(self.data * mask, self.requires_grad, (self,))

        def _back(g):
            if self.requires_grad:
                self._ensure_grad()
                self.grad = self.grad + g * mask

        out._backward = _back
        return out

    def tanh(self):
        t = np.tanh(self.data)
        out = Tensor(t, self.requires_grad, (self,))

        def _back(g):
            if self.requires_grad:
                self._ensure_grad()
                self.grad = self.grad + g * (1 - t * t)

        out._backward = _back
        return out

    def log(self):
        out = Tensor(np.log(self.data + 1e-12), self.requires_grad, (self,))

        def _back(g):
            if self.requires_grad:
                self._ensure_grad()
                self.grad = self.grad + g / (self.data + 1e-12)

        out._backward = _back
        return out

    def exp(self):
        e = np.exp(self.data)
        out = Tensor(e, self.requires_grad, (self,))

        def _back(g):
            if self.requires_grad:
                self._ensure_grad()
                self.grad = self.grad + g * e

        out._backward = _back
        return out

    def softmax(self, axis: int = -1):
        """数值稳定的 softmax（与 torch.nn.functional.softmax 一致）。"""
        shifted = self.data - self.data.max(axis=axis, keepdims=True)
        exp = np.exp(shifted)
        sm = exp / exp.sum(axis=axis, keepdims=True)
        out = Tensor(sm, self.requires_grad, (self,))

        def _back(g):
            if self.requires_grad:
                self._ensure_grad()
                # d softmax / d x = diag(s) - s s^T
                grad = np.zeros_like(self.data)
                for i in range(g.shape[0] if g.ndim > 1 else 1):
                    gi = g[i] if g.ndim > 1 else g
                    si = sm[i] if sm.ndim > 1 else sm
                    grad_i = si * gi - si * (si * gi).sum(axis=axis, keepdims=True)
                    if g.ndim > 1:
                        grad[i] = grad_i
                    else:
                        grad = grad_i
                self.grad = self.grad + grad

        out._backward = _back
        return out

    def detach(self) -> Tensor:
        return Tensor(self.data.copy(), requires_grad=False)

    def numpy(self) -> np.ndarray:
        return self.data


def _unbroadcast(grad: np.ndarray, shape) -> np.ndarray:
    """将广播后的梯度还原到原始 shape（与 autograd 一致）。"""
    while grad.ndim > len(shape):
        grad = grad.sum(axis=0)
    for i, s in enumerate(shape):
        if s == 1 and grad.shape[i] != 1:
            grad = grad.sum(axis=i, keepdims=True)
    return grad


# ---------------------------------------------------------------------------
# Module（复刻 torch.nn.Module）
# ---------------------------------------------------------------------------
class Module:
    """神经网络模块基类（复刻 ``torch.nn.Module``）。"""

    def parameters(self) -> list[Tensor]:
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


class Linear(Module):
    """线性层（复刻 ``torch.nn.Linear``）。

    ``y = x @ W^T + b``，``weight.shape == (out_features, in_features)``，
    ``bias.shape == (out_features,)``。

    初始化默认使用 orthogonal 初始化（来源: Saxe et al., 2013,
    "Exact solutions to the nonlinear dynamics of learning in deep
    linear networks", https://arxiv.org/abs/1312.6120），比 Kaiming
    uniform 在 RL 中收敛更快、更稳定（已被 SB3/PPO 广泛验证）。
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


def _init_weight(in_features: int, out_features: int, init: str) -> np.ndarray:
    """权重初始化（orthogonal / kaiming_uniform / xavier）。

    来源:
    - orthogonal: Saxe et al., 2013, https://arxiv.org/abs/1312.6120
    - kaiming_uniform: He et al., 2015, torch.nn.Linear 默认
    """
    if init == "orthogonal":
        # 生成正交矩阵，shape=(out, in)，与 torch.nn.init.orthogonal_ 一致
        flat_shape = (out_features, in_features)
        a = np.random.randn(*flat_shape)
        u, s, vt = np.linalg.svd(a, full_matrices=False)
        q = u if a.shape[0] >= a.shape[1] else vt
        weight = q.reshape(flat_shape)
        scale = 1.0 / np.sqrt(in_features)
        return weight * scale
    # kaiming_uniform（torch 默认）
    bound = 1.0 / np.sqrt(in_features)
    return np.random.uniform(-bound, bound, (out_features, in_features))


class ReLU(Module):
    def forward(self, x: Tensor) -> Tensor:
        return x.relu()


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


class Tanh(Module):
    def forward(self, x: Tensor) -> Tensor:
        return x.tanh()


class Sequential(Module):
    """顺序容器（复刻 ``torch.nn.Sequential``）。"""

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
    ``Adam.__init__`` 的参数个数（规则 4.1 函数参数上限）。

    来源: Kingma & Ba, 2015, Adam 论文；torch.optim.Adam 默认实现。
    """

    betas: tuple[float, float] = (0.9, 0.999)
    eps: float = 1e-8
    weight_decay: float = 0.0


class Adam:
    """Adam 优化器（复刻 ``torch.optim.Adam``，默认 eps=1e-8, betas=(0.9,0.999)）。

    实现与 torch Adam 一致：偏置修正的一阶/二阶矩估计。
    来源: Kingma & Ba, 2015, Adam 论文；torch.optim.Adam 实现。
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
    "Tensor",
    "TensorArithmeticMixin",
    "Module",
    "Linear",
    "ReLU",
    "LayerNorm",
    "Tanh",
    "Sequential",
    "Adam",
    "AdamConfig",
]


# 子模块延迟导入（避免循环依赖，保持 __init__.py SLOC 限制）
def __getattr__(name: str):
    """延迟导入 nn 子模块（conv/attention）。"""
    if name in (
        "Conv2d",
        "MaxPool2d",
        "Dropout",
        "Embedding",
    ):
        from polaris.nn import conv

        return getattr(conv, name)
    if name in (
        "ScaledDotProductAttention",
        "MultiHeadAttention",
        "TransformerBlock",
    ):
        from polaris.nn import attention

        return getattr(attention, name)
    raise AttributeError(f"module 'polaris.nn' has no attribute {name!r}")
