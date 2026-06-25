"""EME 传播 S 矩阵构造（A02 §7.4，均匀段相位累积）。

均匀波导段内无反射（截面 z 不变），仅各模式相位累积::

    P = diag(exp(i·β_m·L))
    S = [[0, P], [P, 0]]   （S11=0, S12=P, S21=P, S22=0）

对消逝波（Im(β) > 0），|P| = exp(-Im(β)·L) < 1，天然衰减无溢出
（C03 §7.2 数值稳定性，与 ``polaris.sim.cascade.smatrix.build_propagation_s``
公式一致，区别在于 EME 直接取 FDE 模式的 β 向量，无需 LayerModes 包装）。

BlockSMatrix 约定（与 ``polaris.sim.cascade.smatrix.BlockSMatrix`` 一致）::

    [b_left ]   [S11  S12] [a_left ]   [0  P] [a_left ]
    [b_right] = [S21  S22] [a_right] = [P  0] [a_right]

Analysis 模式优势（A02 §6 阶段二，Lumerical EME Propagate）：
    cell 长度 L 可任意扫描，仅需重算 P = diag(exp(i·β·L)) 并级联，
    无需重算本地模（模式求解结果缓存）。本函数仅做相位计算，毫秒级响应。

文献来源（≥5，规则 18 学术诚信）：
1. Gallagher & Felici 2003 SPIE 4987, 69-82（EME Pros and Cons）—
   https://doi.org/10.1117/12.478061
2. Ansys Lumerical MODE-EME solver introduction —
   https://optics.ansys.com/hc/en-us/articles/360034396614
3. SimWorks Eigenmode Expansion (EME) Solver —
   https://www.emsimworks.com/en/solver/EME
4. EMEpy — Open-source eigenmode expansion solver in Python —
   https://emepy.readthedocs.io/en/stable/index.html
5. Liu & Fan 2012 S4 CPC 183, 2233 —
   https://web.stanford.edu/group/fan/S4/
6. Photon Design FIMMPROP EME paper —
   https://photond.com/assets/files/FIMMWAVE/PW03_eme_paper.pdf
7. Oktay & Magden 2024 arXiv:2407.09847 —
   https://arxiv.org/abs/2407.09847

规则依据：project_rules.md 规则 14（禁止 fall-back）/规则 18（学术诚信）
/规则 26（GPU 不参与，纯 NumPy）
"""

from __future__ import annotations

import numpy as np

from polaris.sim.cascade.smatrix import BlockSMatrix

__all__ = ["build_propagation_smatrix"]


def build_propagation_smatrix(betas: np.ndarray, length: float) -> BlockSMatrix:
    """构造均匀段传播 S 矩阵（A02 §7.4）。

    P = diag(exp(i·β_m·L))，BlockSMatrix(zeros, P, P, zeros)。

    对消逝波（Im(β) > 0），|P| = exp(-Im(β)·L) < 1，天然衰减无溢出
    （C03 §7.2 数值稳定性）。

    Args:
        betas: 传播常数向量 (M,)（复数，虚部为损耗；来自 FDE Mode.beta）。
        length: 段长度 L（米）。

    Returns:
        2M×2M 传播 S 矩阵（S11=0, S12=P, S21=P, S22=0）。

    Raises:
        ValueError: 长度非负校验失败、beta 非 1D 或为空（规则 14：禁止 fall-back）。
    """
    if length < 0.0:
        raise ValueError(f"传播段长度必须非负，实际 {length}")
    betas = np.asarray(betas, dtype=np.complex128)
    if betas.ndim != 1:
        raise ValueError(f"beta 必须为 1D 向量，实际 {betas.ndim}D")
    if betas.size == 0:
        raise ValueError("beta 向量不能为空（规则 14：禁止 fall-back）")

    # 相位累积 P = diag(exp(i·β·L))，向量化计算（无 Python 循环）
    phase = np.exp(1j * betas * length)
    m = betas.size
    z_mat = np.zeros((m, m), dtype=np.complex128)
    p_diag = np.diag(phase)
    # S11=0 (无左反射), S12=P (右→左透射), S21=P (左→右透射), S22=0 (无右反射)
    return BlockSMatrix(z_mat, p_diag, p_diag, z_mat)
