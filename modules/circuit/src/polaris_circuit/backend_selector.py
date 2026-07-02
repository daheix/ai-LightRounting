"""S 矩阵条件数计算（数值稳定性诊断，纯 numpy）。

条件数定义: κ(S) = ||S||_2 · ||S⁻¹||_2 = σ_max / σ_min
- κ(S) < 1e6: 良态（well-conditioned）
- 1e6 ≤ κ(S) < 1e12: 病态（ill-conditioned）
- κ(S) ≥ 1e12: 接近奇异，结果不可信

来源:
- Golub & Van Loan 2013, "Matrix Computations", 4th ed.,
  Johns Hopkins Univ. Press §2.3, §3.5,
  https://www.press.jhu.edu/books/title/10876/matrix-computations
- SAX Backends 文档: https://gdsfactory.github.io/sax/nbs/internals/03_backends/
- Pflüger et al. 2021, "Simphony", IEEE CiSE 23(4):74-85,
  https://arxiv.org/abs/2009.05146

合规: R02 学术诚信 / R03 禁止 fall-back / R04 纯 NumPy / R05 无 TODO。
"""

from __future__ import annotations

import logging

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
