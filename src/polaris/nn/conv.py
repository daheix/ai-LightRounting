"""卷积与池化层（复刻 ``torch.nn``，规则 3）。

实现 Conv2d、MaxPool2d、Dropout、Embedding，支持 CNN 拥塞预测
和 Transformer 架构。

来源:
- PyTorch Conv2d: https://pytorch.org/docs/stable/generated/torch.nn.Conv2d
- PyTorch MaxPool2d: https://pytorch.org/docs/stable/generated/torch.nn.MaxPool2d
- PyTorch Dropout: https://pytorch.org/docs/stable/generated/torch.nn.Dropout
- PyTorch Embedding: https://pytorch.org/docs/stable/generated/torch.nn.Embedding
- LeCun et al., 1998, CNN 原始论文
  https://ieeexplore.ieee.org/document/726791
"""

from __future__ import annotations

import numpy as np

from polaris.nn import Module, Tensor, _init_weight


def _pad2d(data: np.ndarray, ph: int, pw: int) -> np.ndarray:
    """零填充 (N, C, H, W) → (N, C, H+2ph, W+2pw)。

    统一使用 float64 dtype，确保数值精度一致性（NumPy dtype 最佳实践）。
    来源: https://numpy.org/doc/stable/reference/arrays.promotion.html

    Args:
        data: 输入张量 (N, C, H, W)。
        ph: 高度方向填充量。
        pw: 宽度方向填充量。

    Returns:
        填充后的张量；ph=pw=0 时原样返回。
    """
    if ph == 0 and pw == 0:
        return data
    n, c, h, w = data.shape
    padded = np.zeros((n, c, h + 2 * ph, w + 2 * pw), dtype=np.float64)
    padded[:, :, ph : ph + h, pw : pw + w] = data
    return padded


class Conv2d(Module):
    """2D 卷积层（复刻 ``torch.nn.Conv2d``）。

    输入: ``(N, C_in, H, W)``，输出: ``(N, C_out, H_out, W_out)``。
    使用 im2col + 矩阵乘法实现，与 PyTorch 逻辑一致。

    来源:
    - PyTorch Conv2d: https://pytorch.org/docs/stable/generated/torch.nn.Conv2d
    - im2col 算法: Chellapilla et al., 2006, "High Performance Convolutional
      Neural Networks for Document Processing"
    """

    def __init__(
        self,
        in_channels: int,
        out_channels: int,
        kernel_size: int | tuple[int, int] = 3,
        stride_padding: tuple[int | tuple, int | tuple] = (1, 0),
    ) -> None:
        """初始化。stride_padding = (stride, padding)。"""
        stride, padding = stride_padding
        kh, kw = (kernel_size, kernel_size) if isinstance(kernel_size, int) else kernel_size
        self.in_channels = in_channels
        self.out_channels = out_channels
        self.kernel_size = (kh, kw)
        sh, sw = (stride, stride) if isinstance(stride, int) else stride
        self.stride = (sh, sw)
        ph, pw = (padding, padding) if isinstance(padding, int) else padding
        self.padding = (ph, pw)
        fan_in = in_channels * kh * kw
        # 初始化为 (out_channels, in_channels*kh*kw) 再 reshape
        w_flat = _init_weight(fan_in, out_channels, "orthogonal")
        self.weight = Tensor(
            w_flat.reshape(out_channels, in_channels, kh, kw),
            requires_grad=True,
        )
        self.bias = Tensor(np.zeros(out_channels), requires_grad=True)

    def _im2col(self, data: np.ndarray, oh: int, ow: int) -> np.ndarray:
        """im2col: (N, C, H, W) → (N, C*kh*kw, oh*ow)。

        统一使用 float64 dtype，确保数值精度一致性。
        来源: Chellapilla et al., 2006, 高性能卷积 im2col 算法。
        """
        kh, kw = self.kernel_size
        sh, sw = self.stride
        n, c, _, _ = data.shape
        cols = np.zeros((n, c * kh * kw, oh * ow), dtype=np.float64)
        for i in range(oh):
            for j in range(ow):
                patch = data[:, :, i * sh : i * sh + kh, j * sw : j * sw + kw]
                cols[:, :, i * ow + j] = patch.reshape(n, -1)
        return cols

    def _col2im(self, cols: np.ndarray, oh: int, ow: int) -> np.ndarray:
        """col2im: (N, C*kh*kw, oh*ow) → (N, C, hp, wp)。逆 im2col，累加重叠区域。

        统一使用 float64 dtype，确保数值精度一致性。
        """
        kh, kw = self.kernel_size
        sh, sw = self.stride
        n = cols.shape[0]
        c = cols.shape[1] // (kh * kw)
        hp = (oh - 1) * sh + kh
        wp = (ow - 1) * sw + kw
        dx = np.zeros((n, c, hp, wp), dtype=np.float64)
        for i in range(oh):
            for j in range(ow):
                dpatch = cols[:, :, i * ow + j].reshape(n, c, kh, kw)
                dx[:, :, i * sh : i * sh + kh, j * sw : j * sw + kw] += dpatch
        return dx

    def forward(self, x: Tensor) -> Tensor:
        """前向：im2col + 矩阵乘法，注册反向传播。

        来源: PyTorch Conv2d autograd
        https://pytorch.org/docs/stable/generated/torch.nn.Conv2d
        """
        data = x.data if isinstance(x, Tensor) else np.asarray(x, dtype=np.float64)
        if data.ndim == 3:
            data = data[np.newaxis]
        n, c, h, w = data.shape
        kh, kw = self.kernel_size
        sh, sw = self.stride
        ph, pw = self.padding
        padded = _pad2d(data, ph, pw)
        hp, wp = padded.shape[2], padded.shape[3]
        oh = (hp - kh) // sh + 1
        ow = (wp - kw) // sw + 1
        cols = self._im2col(padded, oh, ow)
        w_mat = self.weight.data.reshape(self.out_channels, -1)
        out = np.einsum("oc,nck->nok", w_mat, cols)
        out += self.bias.data[:, np.newaxis]
        out = out.reshape(n, self.out_channels, oh, ow)
        rg = self.weight.requires_grad or self.bias.requires_grad
        parents = ()
        if isinstance(x, Tensor):
            rg = rg or x.requires_grad
            parents = (x,)
        out_t = Tensor(out, rg, parents)
        ctx = (cols, w_mat, n, oh, ow, ph, pw, h, w)
        out_t._backward = self._make_conv_backward(ctx, x)
        return out_t

    def _make_conv_backward(self, ctx: tuple, x: Tensor):
        """构建卷积反向闭包（dW/db/dx）。

        反向传播参考 PyTorch Conv2d autograd:
        - dW = sum_b grad_b @ cols_b^T  (对 batch 累加)
        - db = sum over (N, oh*ow)
        - dx = col2im(W^T @ grad)
        """
        cols, w_mat, n, oh, ow, ph, pw, h, w = ctx

        def _back(g: np.ndarray) -> None:
            g2 = g.reshape(n, self.out_channels, oh * ow)
            if self.bias.requires_grad:
                self.bias._ensure_grad()
                self.bias.grad = self.bias.grad + g2.sum(axis=(0, 2))
            if self.weight.requires_grad:
                self.weight._ensure_grad()
                dw = np.einsum("nok,nck->oc", g2, cols)
                self.weight.grad = self.weight.grad + dw.reshape(self.weight.data.shape)
            if isinstance(x, Tensor) and x.requires_grad:
                x._ensure_grad()
                dcols = np.einsum("oc,nok->nck", w_mat, g2)
                dx_padded = self._col2im(dcols, oh, ow)
                dx = dx_padded[:, :, ph : ph + h, pw : pw + w] if (ph or pw) else dx_padded
                x.grad = x.grad + dx

        return _back

    def parameters(self) -> list[Tensor]:
        return [self.weight, self.bias]


class MaxPool2d(Module):
    """2D 最大池化层（复刻 ``torch.nn.MaxPool2d``）。

    来源: PyTorch MaxPool2d
    https://pytorch.org/docs/stable/generated/torch.nn.MaxPool2d
    """

    def __init__(
        self,
        kernel_size: int | tuple[int, int] = 2,
        stride: int | tuple[int, int] | None = None,
    ) -> None:
        ks = (kernel_size, kernel_size) if isinstance(kernel_size, int) else kernel_size
        self.kernel_size = ks
        if stride is None:
            self.stride = ks
        elif isinstance(stride, int):
            self.stride = (stride, stride)
        else:
            self.stride = stride

    def forward(self, x: Tensor) -> Tensor:
        """前向：滑动窗口取最大值，记录 argmax 用于反向路由。

        统一使用 float64 dtype，确保数值精度一致性。
        来源: PyTorch MaxPool2d
        https://pytorch.org/docs/stable/generated/torch.nn.MaxPool2d
        """
        data = x.data if isinstance(x, Tensor) else np.asarray(x, dtype=np.float64)
        if data.ndim == 3:
            data = data[np.newaxis]
        n, c, h, w = data.shape
        kh, kw = self.kernel_size
        sh, sw = self.stride
        oh = (h - kh) // sh + 1
        ow = (w - kw) // sw + 1
        out = np.zeros((n, c, oh, ow), dtype=np.float64)
        argmax = np.zeros((n, c, oh, ow), dtype=np.intp)
        for i in range(oh):
            for j in range(ow):
                region = data[:, :, i * sh : i * sh + kh, j * sw : j * sw + kw]
                flat = region.reshape(n, c, -1)
                out[:, :, i, j] = flat.max(axis=-1)
                argmax[:, :, i, j] = flat.argmax(axis=-1)
        rg = x.requires_grad if isinstance(x, Tensor) else False
        parents = (x,) if isinstance(x, Tensor) else ()
        out_t = Tensor(out, rg, parents)
        ctx = (argmax, n, c, oh, ow, kh, kw, sh, sw, data)
        out_t._backward = self._make_pool_backward(ctx, x)
        return out_t

    def _make_pool_backward(self, ctx: tuple, x: Tensor):
        """构建池化反向闭包：梯度路由到前向 max 位置（与 PyTorch 一致）。"""
        argmax, n, c, oh, ow, kh, kw, sh, sw, data = ctx

        def _back(g: np.ndarray) -> None:
            if not (isinstance(x, Tensor) and x.requires_grad):
                return
            x._ensure_grad()
            dx = np.zeros_like(data)
            b_idx, c_idx = np.meshgrid(np.arange(n), np.arange(c), indexing="ij")
            for i in range(oh):
                for j in range(ow):
                    idx = argmax[:, :, i, j]
                    di = idx // kw
                    dj = idx % kw
                    np.add.at(dx, (b_idx, c_idx, i * sh + di, j * sw + dj), g[:, :, i, j])
            x.grad = x.grad + dx

        return _back


class Dropout(Module):
    """Dropout 正则化层（复刻 ``torch.nn.Dropout``）。

    训练时以概率 p 随机置零，推理时不变。

    来源:
    - Srivastava et al., 2014, "Dropout: A Simple Way to Prevent
      Overfitting of Neural Networks", JMLR
      https://jmlr.org/papers/v15/srivastava14a.html
    """

    def __init__(self, p: float = 0.5) -> None:
        self.p = p
        self.training = True

    def forward(self, x: Tensor) -> Tensor:
        """前向：训练时随机置零并缩放。"""
        data = x.data if isinstance(x, Tensor) else np.asarray(x, dtype=np.float64)
        if not self.training or self.p == 0:
            return Tensor(data, x.requires_grad if isinstance(x, Tensor) else False, (x,))
        mask = (np.random.rand(*data.shape) > self.p).astype(np.float64)
        out = data * mask / (1.0 - self.p)
        return Tensor(out, x.requires_grad if isinstance(x, Tensor) else False, (x,))


class Embedding(Module):
    """嵌入层（复刻 ``torch.nn.Embedding``）。

    将离散索引映射为稠密向量，用于类别特征编码。

    来源: PyTorch Embedding
    https://pytorch.org/docs/stable/generated/torch.nn.Embedding
    """

    def __init__(self, num_embeddings: int, embedding_dim: int) -> None:
        self.num_embeddings = num_embeddings
        self.embedding_dim = embedding_dim
        self.weight = Tensor(
            np.random.randn(num_embeddings, embedding_dim) * 0.01,
            requires_grad=True,
        )

    def forward(self, x: Tensor) -> Tensor:
        """前向：查表。输入为整数索引张量。"""
        indices = x.data if isinstance(x, Tensor) else np.asarray(x, dtype=np.int64)
        out = self.weight.data[indices]
        return Tensor(out, self.weight.requires_grad, (x,))

    def parameters(self) -> list[Tensor]:
        return [self.weight]


__all__ = ["Conv2d", "MaxPool2d", "Dropout", "Embedding"]
