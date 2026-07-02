"""纯 NumPy 自动微分张量（polaris-core 子模块）。

从 src/polaris/nn/__init__.py 迁移 Tensor 类，作为 polaris-core 的核心数据结构。
纯 NumPy 实现，无 torch 依赖（R04: 不参与 GPU，纯 CPU NumPy）。

复刻 PyTorch autograd 计算图：前向 op 记录父节点，反向沿拓扑序传播梯度。
本模块自包含（_unbroadcast / _matmul_backward 内联），不依赖 polaris.nn.functional。

来源:
- PyTorch autograd: https://pytorch.org/docs/stable/autograd.html
- PyTorch torch.Tensor: https://github.com/pytorch/pytorch （BSD-style license）
- Autograd 反向模式: https://en.wikipedia.org/wiki/Automatic_differentiation#Reverse_accumulation
- NumPy 广播规则: https://numpy.org/doc/stable/user/basics.broadcasting.html
- Baydin et al., 2018, "Automatic Differentiation in Machine Learning: a Comparative Review"
  https://arxiv.org/abs/1502.05767
"""

from __future__ import annotations

from typing import cast

import numpy as np


def _unbroadcast(grad: np.ndarray, shape) -> np.ndarray:
    """将广播后的梯度还原到原始 shape（与 autograd 一致）。

    来源: PyTorch autograd 广播梯度还原
    https://pytorch.org/docs/stable/notes/autograd.html

    Args:
        grad: 广播后的梯度。
        shape: 原始 shape。

    Returns:
        还原后的梯度，shape 与 ``shape`` 一致。
    """
    while grad.ndim > len(shape):
        grad = grad.sum(axis=0)
    for i, s in enumerate(shape):
        if s == 1 and grad.shape[i] != 1:
            grad = grad.sum(axis=i, keepdims=True)
    return grad


def _matmul_backward(left: "Tensor", right: "Tensor", g: np.ndarray) -> None:
    """``__matmul__`` 的反向传播（通过 reshape 统一处理 1D/2D 输入）。

    将 1D 输入 reshape 为 2D 后用标准矩阵梯度公式，避免多分支判断：
    - 1D @ 2D: ``x[k] @ W[k,m]`` → reshape x 为 ``[1,k]``
    - 2D @ 1D: ``X[n,k] @ v[k]`` → reshape v 为 ``[k,1]``

    Args:
        left: ``__matmul__`` 左操作数。
        right: ``__matmul__`` 右操作数。
        g: 上游梯度。
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

    将算术运算符重载从 ``Tensor`` 拆分至此混入，以降低 ``Tensor``
    的方法数（质量门禁：函数/方法数控制）。

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
            _matmul_backward(self, other, g)

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
    reshape、flatten 等前向 op 与对应反向梯度。``requires_grad=True`` 时
    构建计算图，调用 ``backward()`` 沿拓扑序反向传播。

    统一使用 float64 dtype，确保数值精度一致性（NumPy dtype 最佳实践）。
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

    def reshape(self, *shape) -> "Tensor":
        out = Tensor(self.data.reshape(shape), self.requires_grad, (self,))

        def _back(g):
            if self.requires_grad:
                self._ensure_grad()
                self.grad = self.grad + g.reshape(self.data.shape)

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

    def _ensure_grad(self):
        if self.grad is None:
            self.grad = np.zeros_like(self.data)

    def backward(self, grad: np.ndarray | None = None) -> None:
        """反向传播（拓扑序，与 autograd 一致）。

        来源: PyTorch autograd 反向模式
        https://pytorch.org/docs/stable/autograd.html

        Args:
            grad: 上游梯度（默认 ones_like，对标 ``torch.Tensor.backward()`` 无参调用）。
        """
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
            # 跳过 grad 为 None 的节点（requires_grad=False 的中间节点
            # 不参与反向传播，与 autograd 行为一致）。
            if t.grad is None:
                continue
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
        """数值稳定的 softmax（与 torch.nn.functional.softmax 一致）。

        来源: PyTorch softmax 数值稳定实现
        https://pytorch.org/docs/stable/generated/torch.nn.functional.softmax.html
        """
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

    def detach(self) -> "Tensor":
        return Tensor(self.data.copy(), requires_grad=False)

    def numpy(self) -> np.ndarray:
        return self.data


__all__ = ["Tensor", "TensorArithmeticMixin"]
