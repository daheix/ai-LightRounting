"""S 参数类型定义（纯 numpy 后端，R04 合规）。

S 参数格式与 SAX 一致:
    S = {(port_out, port_in): ndarray, ...}
    例如 waveguide: {("in","in"): 0, ("out","in"): phase, ...}

来源（R02 学术诚信，≥5 篇文献 URL）:
1. SAX 类型系统: https://flaport.github.io/sax/
2. Pflüger et al. 2021, "Simphony: A Python-based simulator and S-parameter
   library for photonic integrated circuits", IEEE CiSE 23(4):74-85,
   https://arxiv.org/abs/2009.05146
3. Filipsson 1978, "A new general computer algorithm for S-matrix calculation
   of interconnected multiports", Proc. Eur. Microw. Conf.,
   https://doi.org/10.1109/EUMA.1978.332681
4. Golub & Van Loan 2013, "Matrix Computations", 4th ed., §2.3,
   https://www.press.jhu.edu/books/title/10876/matrix-computations
5. Chrostowski & Hochberg 2015, "Silicon Photonics Design", Cambridge,
   https://www.cambridge.org/core/search?searchField=isbn&searchTerms=1107007731
6. gdsfactory sax 文档: https://gdsfactory.github.io/sax/

合规: R02 学术诚信 / R03 禁止 fall-back / R04 纯 NumPy/SciPy（不引入 JAX，
保留纯 numpy 单后端以降低子模块耦合）/ R05 无 TODO。
"""

from __future__ import annotations

from typing import Protocol

import numpy as np

# S 参数值类型：复数 ndarray（频率维度）
SArray = np.ndarray

# S 参数字典：键为 (port_out, port_in) 元组，值为复数数组（频率维度）
SDict = dict[tuple[str, str], SArray]


class ModelFunc(Protocol):
    """S 参数模型函数协议（与 SAX 一致）。

    模型函数接收波长等参数，返回 S 参数字典。
    """

    def __call__(self, wl: float | np.ndarray = 1.55, **kwargs) -> SDict: ...


__all__ = ["SDict", "SArray", "ModelFunc"]
