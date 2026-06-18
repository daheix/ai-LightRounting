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

    def forward(self, x: Tensor) -> Tensor:
        """前向：im2col + 矩阵乘法。"""
        data = x.data if isinstance(x, Tensor) else np.asarray(x, dtype=np.float64)
        if data.ndim == 3:
            data = data[np.newaxis]
        n, c, h, w = data.shape
        kh, kw = self.kernel_size
        sh, sw = self.stride
        ph, pw = self.padding
        # padding
        if ph > 0 or pw > 0:
            padded = np.zeros((n, c, h + 2 * ph, w + 2 * pw))
            padded[:, :, ph : ph + h, pw : pw + w] = data
            data = padded
        _, _, hp, wp = data.shape
        oh = (hp - kh) // sh + 1
        ow = (wp - kw) // sw + 1
        # im2col: (N, C*kh*kw, oh*ow)
        cols = np.zeros((n, c * kh * kw, oh * ow))
        for i in range(oh):
            for j in range(ow):
                patch = data[:, :, i * sh : i * sh + kh, j * sw : j * sw + kw]
                cols[:, :, i * ow + j] = patch.reshape(n, -1)
        # 矩阵乘法: (out, C*kh*kw) @ (N, C*kh*kw, oh*ow) -> (N, out, oh*ow)
        w_mat = self.weight.data.reshape(self.out_channels, -1)  # (out, C*kh*kw)
        # 对每个样本做矩阵乘法
        out = np.zeros((n, self.out_channels, oh * ow))
        for b in range(n):
            out[b] = w_mat @ cols[b]
        out += self.bias.data[:, np.newaxis]  # (out, 1) broadcast
        out = out.reshape(n, self.out_channels, oh, ow)
        return Tensor(out, x.requires_grad if isinstance(x, Tensor) else False, (x,))

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
        """前向：滑动窗口取最大值。"""
        data = x.data if isinstance(x, Tensor) else np.asarray(x, dtype=np.float64)
        if data.ndim == 3:
            data = data[np.newaxis]
        n, c, h, w = data.shape
        kh, kw = self.kernel_size
        sh, sw = self.stride
        oh = (h - kh) // sh + 1
        ow = (w - kw) // sw + 1
        out = np.zeros((n, c, oh, ow))
        for i in range(oh):
            for j in range(ow):
                region = data[:, :, i * sh : i * sh + kh, j * sw : j * sw + kw]
                out[:, :, i, j] = region.reshape(n, c, -1).max(axis=-1)
        return Tensor(out, x.requires_grad if isinstance(x, Tensor) else False, (x,))


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
