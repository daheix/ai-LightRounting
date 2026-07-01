"""S 参数类型定义（双后端支持 numpy/jax，R01 改进）。

S 参数格式与 SAX 一致：
    S = {(port_out, port_in): ndarray, ...}
    例如 waveguide: {("in","in"): 0, ("out","in"): phase, ...}

双后端支持（R01 创新点）:
- numpy 后端：速度快，适合大规模电路仿真
- jax.numpy 后端：支持自动微分（jax.grad）和 GPU 加速
- 默认使用 numpy，可通过 set_backend("jax") 切换

来源:
- SAX 类型系统: https://flaport.github.io/sax/
- JAX 自动微分: https://docs.jax.dev/
- Frostig et al., "Decomposing Reverse-Mode AD", LAFI 2021, arXiv:2105.09469


## 补充文献（R02 学术诚信补齐）
- SAX models: https://flaport.github.io/sax/models/
- NetworkX 文档: https://networkx.org/documentation/stable/
"""

from __future__ import annotations

from typing import Protocol, Union

import numpy as np

# 默认后端为 numpy（兼容现有代码）
_BACKEND = "numpy"

try:
    import jax.numpy as jnp
    from jax import Array as JaxArray

    _HAS_JAX = True
except ImportError:
    jnp = None  # type: ignore[assignment]
    JaxArray = None  # type: ignore[assignment,misc]
    _HAS_JAX = False


# S 参数值类型：支持 numpy.ndarray 和 jax.Array（双后端）
# 来源: SAX SDict 类型 https://flaport.github.io/sax/
SArray = Union[np.ndarray, "JaxArray"] if _HAS_JAX else np.ndarray  # type: ignore[misc]

# S 参数字典：键为 (port_out, port_in) 元组，值为复数数组（频率维度）
SDict = dict[tuple[str, str], SArray]


def set_backend(backend: str) -> None:
    """设置全局后端（numpy 或 jax）。

    Args:
        backend: 后端名称 "numpy" 或 "jax"。

    Raises:
        ValueError: 未知后端或 jax 不可用时告警退出（禁止 fall-back）。
    """
    global _BACKEND
    if backend == "numpy":
        _BACKEND = "numpy"
        return
    if backend == "jax":
        if not _HAS_JAX:
            msg = (
                "jax 后端不可用。请安装 jax: pip install jax jaxlib。"
                "禁止 fall-back 至 numpy（规则 14.1）。"
            )
            raise ValueError(msg)
        _BACKEND = "jax"
        return
    msg = f"未知后端: {backend}，仅支持 'numpy' 或 'jax'"
    raise ValueError(msg)


def get_backend() -> str:
    """获取当前全局后端。

    Returns:
        后端名称 "numpy" 或 "jax"。
    """
    return _BACKEND


def get_xp():
    """获取当前后端的 numpy 兼容模块。

    Returns:
        numpy 或 jax.numpy 模块。

    Raises:
        RuntimeError: jax 后端不可用时告警退出（禁止 fall-back）。
    """
    if _BACKEND == "numpy":
        return np
    if _BACKEND == "jax":
        if not _HAS_JAX:
            msg = "jax 后端不可用，但已设置为全局后端。请安装 jax: pip install jax jaxlib。"
            raise RuntimeError(msg)
        return jnp  # type: ignore[return-value]
    msg = f"未知后端: {_BACKEND}"
    raise RuntimeError(msg)


def asarray(data, dtype=complex):
    """根据当前后端创建数组。

    Args:
        data: 输入数据（list/tuple/ndarray）。
        dtype: 数据类型，默认 complex。

    Returns:
        numpy.ndarray 或 jax.Array。
    """
    xp = get_xp()
    return xp.asarray(data, dtype=dtype)


def zeros_like(data, dtype=complex):
    """根据当前后端创建零数组。

    Args:
        data: 形状参考数组。
        dtype: 数据类型，默认 complex。

    Returns:
        零数组（numpy 或 jax）。
    """
    xp = get_xp()
    return xp.zeros_like(data, dtype=dtype)


def full_like(data, fill_value, dtype=complex):
    """根据当前后端创建填充数组。

    Args:
        data: 形状参考数组。
        fill_value: 填充值。
        dtype: 数据类型，默认 complex。

    Returns:
        填充数组（numpy 或 jax）。
    """
    xp = get_xp()
    return xp.full_like(data, fill_value, dtype=dtype)


class ModelFunc(Protocol):
    """S 参数模型函数协议（与 SAX 一致）。

    模型函数接收波长等参数，返回 S 参数字典。

    双后端兼容: 返回的 SDict 值可为 numpy.ndarray 或 jax.Array，
    取决于全局后端设置（set_backend）。
    """

    def __call__(self, wl: float | np.ndarray = 1.55, **kwargs) -> SDict: ...
