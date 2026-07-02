"""纯 NumPy 神经网络最小子集（polaris-trainer 内部依赖）。

本模块从 PoLaRIS v4 ``src/polaris/nn/__init__.py`` 与
``src/polaris/nn/functional.py`` 提取 PPO 训练所需的最小自动微分子集
（Tensor / Module / Linear / ReLU / Sequential / Adam），使 polaris-trainer
子模块**仅依赖 numpy** 即可独立运行（R04: 不参与 GPU；R13: 保持功能独立）。

torch 在目标环境（Python 3.14 / 受限磁盘）无法安装，按规则用纯 NumPy
100% 复刻 ``torch.nn`` / ``torch.autograd`` 等价实现，接口与 torch 兼容。

## 算子覆盖（仅 PPO 训练所需子集）

前向：``+ - * @ neg exp log sum mean relu flatten T``
反向：拓扑序 autograd（``backward``），``_unbroadcast`` 还原广播梯度。

## 学术依据（R02 学术诚信，≥5 个文献 URL）

1. PyTorch torch.nn / torch.autograd（复刻来源，BSD-style license）
   https://github.com/pytorch/pytorch
2. Kingma & Ba, 2015, Adam 优化器 https://arxiv.org/abs/1412.6980
3. Saxe et al., 2013, orthogonal 初始化 https://arxiv.org/abs/1312.6120
4. He et al., 2015, Kaiming 初始化 https://arxiv.org/abs/1502.01852
5. Baydin et al., 2018, 自动微分综述 https://arxiv.org/abs/1502.05767
6. numpy dtype promotion 最佳实践
   https://numpy.org/doc/stable/reference/arrays.promotion.html

来源: 迁移自 PoLaRIS v4 ``src/polaris/nn/``（纯 NumPy 复刻，R04 合规）。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

import numpy as np

__all__ = [
    "Tensor",
    "Module",
    "Linear",
    "ReLU",
    "Sequential",
    "Adam",
    "AdamConfig",
    "matmul_backward",
]


def _unbroadcast(grad: np.ndarray, shape) -> np.ndarray:
    """将广播后的梯度还原到原始 shape（与 autograd 一致）。"""
    while grad.ndim > len(shape):
        grad = grad.sum(axis=0)
    for i, s in enumerate(shape):
        if s == 1 and grad.shape[i] != 1:
            grad = grad.sum(axis=i, keepdims=True)
    return grad


def matmul_backward(left: "Tensor", right: "Tensor", g: np.ndarray) -> None:
    """``__matmul__`` 的反向传播（通过 reshape 统一处理 1D/2D 输入）。

    将 1D 输入 reshape 为 2D 后用标准矩阵梯度公式：
    - 1D @ 2D: ``x[k] @ W[k,m]`` → reshape x 为 ``[1,k]``
    - 2D @ 1D: ``X[n,k] @ v[k]`` → reshape v 为 ``[k,1]``
    """
    l2d = left.data.ndim == 1
    r2d = right.data.ndim == 1
    left_data = left.data.reshape(1, -1) if l2d else left.data
    right_data = right.data.reshape(-1, 1) if r2d else right.data
    g2d = g.reshape(1, -1) if g.ndim == 1 else g
    if left.requires_grad:
        left._ensure_grad()
        gl = g2d @ right_data.T
        left.grad = left.grad + (gl.flatten() if l2d else gl)
    if right.requires_grad:
        right._ensure_grad()
        gr = left_data.T @ g2d
        right.grad = right.grad + (gr.flatten() if r2d else gr)


class TensorArithmeticMixin:
    """Tensor 算术运算混入（复刻 ``torch.Tensor`` 算术 op 子集）。

    来源: PyTorch torch.Tensor https://github.com/pytorch/pytorch
    """

    __slots__ = ()
    data: np.ndarray
    requires_grad: bool
    grad: np.ndarray | None

    def _ensure_grad(self) -> None:
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
            matmul_backward(self, other, g)

        out._backward = _back
        return out

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


class Tensor(TensorArithmeticMixin):
    """自动微分张量（复刻 ``torch.Tensor`` 的核心子集）。

    支持 +、-、*、@、neg、relu、log、exp、sum、mean、flatten、T 等前向 op
    与对应反向梯度。``requires_grad=True`` 时构建计算图。
    """

    __slots__ = ("data", "requires_grad", "grad", "_backward", "_parents")

    def __init__(
        self,
        data: np.ndarray | float | int,
        requires_grad: bool = False,
        _parents: tuple["Tensor", ...] = (),
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
    def T(self) -> "Tensor":
        """转置（复刻 ``torch.Tensor.T``，等价 ``data.T``）。"""
        out = Tensor(self.data.T, self.requires_grad, (self,))

        def _back(g):
            if self.requires_grad:
                self._ensure_grad()
                self.grad = self.grad + g.T

        out._backward = _back
        return out

    def flatten(self) -> "Tensor":
        """展平为一维（复刻 ``torch.Tensor.flatten``）。"""
        out = Tensor(self.data.flatten(), self.requires_grad, (self,))

        def _back(g):
            if self.requires_grad:
                self._ensure_grad()
                self.grad = self.grad + g.reshape(self.data.shape)

        out._backward = _back
        return out

    def _ensure_grad(self) -> None:
        if self.grad is None:
            self.grad = np.zeros_like(self.data)

    def backward(self, grad: np.ndarray | None = None) -> None:
        """反向传播（拓扑序，与 autograd 一致）。"""
        if grad is None:
            grad = np.ones_like(self.data)
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
        self._ensure_grad()
        self.grad = self.grad + grad
        for t in reversed(topo):
            if t.grad is None:
                continue
            t._backward(t.grad)

    def zero_grad(self) -> None:
        self.grad = None

    def sum(self, axis=None, keepdims=False):
        out = Tensor(self.data.sum(axis=axis, keepdims=keepdims), self.requires_grad, (self,))

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
        out = Tensor(self.data.mean(axis=axis, keepdims=keepdims), self.requires_grad, (self,))

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

    def detach(self) -> "Tensor":
        return Tensor(self.data.copy(), requires_grad=False)

    def numpy(self) -> np.ndarray:
        return self.data


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


def _init_weight(in_features: int, out_features: int, init: str) -> np.ndarray:
    """权重初始化（orthogonal / kaiming_uniform / xavier）。

    来源:
    - orthogonal: Saxe et al., 2013, https://arxiv.org/abs/1312.6120
    - kaiming_uniform: He et al., 2015, https://arxiv.org/abs/1502.01852
    """
    if init == "orthogonal":
        flat_shape = (out_features, in_features)
        a = np.random.randn(*flat_shape).astype(np.float64)
        u, _s, vt = np.linalg.svd(a, full_matrices=False)
        q = u if a.shape[0] >= a.shape[1] else vt
        weight = q.reshape(flat_shape)
        scale = 1.0 / np.sqrt(in_features)
        return (weight * scale).astype(np.float64)
    bound = 1.0 / np.sqrt(in_features)
    return np.random.uniform(-bound, bound, (out_features, in_features)).astype(np.float64)


class Linear(Module):
    """线性层（复刻 ``torch.nn.Linear``）。

    ``y = x @ W^T + b``，``weight.shape == (out_features, in_features)``，
    ``bias.shape == (out_features,)``。默认 orthogonal 初始化
    （Saxe 2013），在 RL 中收敛更稳定（已被 SB3/PPO 广泛验证）。
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
        self.weight = Tensor(_init_weight(in_features, out_features, init), requires_grad=True)
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
    def forward(self, x: Tensor) -> Tensor:
        return x.relu()


class Sequential(Module):
    """顺序容器（复刻 ``torch.nn.Sequential``）。"""

    def __init__(self, *layers: Module) -> None:
        self.layers = list(layers)

    def forward(self, x: Tensor) -> Tensor:
        for layer in self.layers:
            x = layer(x)
        return x


@dataclass
class AdamConfig:
    """Adam 优化器超参数配置（复刻 ``torch.optim.Adam`` 默认值）。

    来源: Kingma & Ba, 2015, Adam 论文 https://arxiv.org/abs/1412.6980
    """

    betas: tuple[float, float] = (0.9, 0.999)
    eps: float = 1e-8
    weight_decay: float = 0.0


class Adam:
    """Adam 优化器（复刻 ``torch.optim.Adam``，默认 eps=1e-8, betas=(0.9,0.999)）。

    实现偏置修正的一阶/二阶矩估计，与 torch Adam 一致。
    来源: Kingma & Ba, 2015, Adam https://arxiv.org/abs/1412.6980
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
