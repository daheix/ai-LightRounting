"""S 参数类型定义。

S 参数格式与 SAX 一致：
    S = {(port_out, port_in): np.ndarray, ...}
    例如 waveguide: {("in","in"): 0, ("out","in"): phase, ...}

来源:
- SAX 类型系统: https://flaport.github.io/sax/
"""

from __future__ import annotations

from typing import Protocol

import numpy as np

# S 参数字典：键为 (port_out, port_in) 元组，值为复数数组（频率维度）
SDict = dict[tuple[str, str], np.ndarray]


class ModelFunc(Protocol):
    """S 参数模型函数协议（与 SAX 一致）。

    模型函数接收波长等参数，返回 S 参数字典。
    """

    def __call__(self, wl: float | np.ndarray = 1.55, **kwargs) -> SDict: ...
