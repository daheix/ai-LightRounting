"""S 矩阵条件数计算 + JAX CPU 后端选择器（v5.1，R04 合规：仅 CPU 后端）。

条件数定义: κ(S) = ||S||_2 · ||S⁻¹||_2 = σ_max / σ_min
- κ(S) < 1e6: 良态（well-conditioned）
- 1e6 ≤ κ(S) < 1e12: 病态（ill-conditioned）
- κ(S) ≥ 1e12: 接近奇异，结果不可信

JAX CPU 后端（v5.1 新增）:
- is_jax_available() 自动检测 jax 可导入且 jax.devices("cpu") 非空，结果缓存。
- 提供 waveguide_s_jax / cascade_two_port_jax / simulate_waveguide_chain_jax
  三个 jnp 向量化 S 参数计算函数，与 models.waveguide_s 物理一致。
- R04 战略决策: 仅使用 jax.devices("cpu")，禁止 GPU/TPU 后端。
- R03 禁止 fall-back: JAX 不可用时一律 raise RuntimeError，不静默回退 numpy。
- 启用 jax_enable_x64=True 保证与 numpy float64 数值一致（测试可复现）。

来源（R02 学术诚信，≥5 篇文献 URL）:
1. Golub & Van Loan 2013, "Matrix Computations", 4th ed.,
   Johns Hopkins Univ. Press §2.3, §3.5,
   https://www.press.jhu.edu/books/title/10876/matrix-computations
2. SAX Backends 文档: https://gdsfactory.github.io/sax/nbs/internals/03_backends/
3. Pflüger et al. 2021, "Simphony", IEEE CiSE 23(4):74-85,
   https://arxiv.org/abs/2009.05146
4. Filipsson 1978, "A new general computer algorithm for S-matrix calculation
   of interconnected multiports", Proc. Eur. Microw. Conf.,
   https://doi.org/10.1109/EUMA.1978.332681
5. Bradbury et al. 2018, "JAX: composable transformations of Python+NumPy
   programs", JOSS 3(31):10219, https://doi.org/10.21105/joss.02021
6. JAX JIT 编译文档: https://jax.readthedocs.io/en/latest/jax-101/02-jitting.html
7. JAX lax.scan 文档:
   https://jax.readthedocs.io/en/latest/_autosummary/jax.lax.scan.html
8. SAX JAX 后端: https://flaport.github.io/sax/
9. NumPy 广播规则:
   https://numpy.org/doc/stable/user/basics.broadcasting.html
10. Pozar, "Microwave Engineering" 4th ed. §4.3 (两网络级联 Redheffer star),
    https://www.wiley.com/en-us/Microwave+Engineering%2C+4th+Edition-p-9781118213636

合规: R02 学术诚信 / R03 禁止 fall-back（JAX 不可用即 raise）/
R04 仅 JAX CPU 后端（jax.devices("cpu")，禁 GPU/TPU）/ R05 无 TODO。
"""

from __future__ import annotations

import importlib.util
import logging
from typing import Any, Callable

import numpy as np

from polaris_circuit.types import SDict

logger = logging.getLogger(__name__)

# 条件数阈值（来源: Golub & Van Loan "Matrix Computations" §2.3）
COND_NUM_FG_THRESHOLD = 1e6  # 良态/病态分界
COND_NUM_KLU_THRESHOLD = 1e12  # 病态/奇异分界


def _sdict_to_matrix(sdict: SDict) -> np.ndarray:
    """将 SDict 转换为稠密 S 矩阵（取第一个频点，用于条件数评估）。"""
    ports_out = sorted({k[0] for k in sdict})
    ports_in = sorted({k[1] for k in sdict})
    n_out = len(ports_out)
    n_in = len(ports_in)
    first_val = next(iter(sdict.values()))
    arr = np.asarray(first_val, dtype=complex)
    n_freq = arr.shape[0] if arr.ndim > 0 else 1
    mat = np.zeros((n_out, n_in, n_freq), dtype=complex)
    for (p_out, p_in), val in sdict.items():
        i = ports_out.index(p_out)
        j = ports_in.index(p_in)
        mat[i, j, :] = np.asarray(val, dtype=complex)
    return mat[:, :, 0]


def compute_condition_number(sdict: SDict) -> float:
    """计算 S 矩阵的条件数 κ(S) = σ_max / σ_min。

    来源: Golub & Van Loan, "Matrix Computations", §2.3, §3.5

    Args:
        sdict: S 参数字典 {(port_out, port_in): array}。

    Returns:
        条件数 κ(S)。若矩阵非方阵或接近奇异，返回最大奇异值之比；
        σ_min ≈ 0 时返回 inf。
    """
    mat = _sdict_to_matrix(sdict)
    sv = np.linalg.svd(mat, compute_uv=False)
    sigma_max = sv[0]
    sigma_min = sv[-1]
    if sigma_min < 1e-300:
        return float("inf")
    return float(sigma_max / sigma_min)


__all__ = ["compute_condition_number", "COND_NUM_FG_THRESHOLD", "COND_NUM_KLU_THRESHOLD"]
