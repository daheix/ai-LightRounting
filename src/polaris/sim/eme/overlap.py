"""EME 模式重叠积分矩阵（A02 §7.2，Gallagher & Felici 2003）。

构造双向重叠积分矩阵 (M_E, M_H)，供界面 S 矩阵求解使用。

数学定义（A02 §7.2，与 Lumerical EME / SimWorks EME 公式一致）::

    M_E[m,n] = 0.5·∫(e_n^B × h_m^{A*})·ẑ dA   （B 的 E 投影到 A 的 H）
    M_H[m,n] = 0.5·∫(e_m^A × h_n^{B*})·ẑ dA   （A 的 E 投影到 B 的 H）

其中 (E × H*)·ẑ = E_x·H_y* - E_y·H_x* 为坡印廷矢量 z 分量（功率流方向）。
两个矩阵不同（M_E ≠ M_H），分别用于界面 S 矩阵的两个方程（切向 E 与切向 H 连续）。

离散实现（向量化，python代码开发规则.md §4 禁止 Python 循环）::

    M_E[k, n] = 0.5·Σ(e_b_ex[n]·conj(h_a_hy[k]) - e_b_ey[n]·conj(h_a_hx[k]))·dx·dy
    M_H[m, n] = 0.5·Σ(e_a_ex[m]·conj(h_b_hy[n]) - e_a_ey[m]·conj(h_b_hx[n]))·dx·dy

向量化策略：将模式列表的场分量堆叠为 3D 数组 (M, Nx, Ny)，再用 ``numpy.einsum``
一次性计算所有模式对的重叠积分，避免 Python 双重循环（性能提升 100×+）。

正交归一性验证（A02 §7.1，功率归一化模式）：
    当 modes_a == modes_b（同一组正交归一模式）时，M_E = M_H = I（单位矩阵）。
    由此可得界面 S11 = (I - I)·inv(I + I) = 0，S21 = 2·inv(2I) = I（M1 验收点）。

文献来源（≥5，规则 18 学术诚信）：
1. Gallagher & Felici 2003 SPIE 4987, 69-82（EME Pros and Cons）—
   https://doi.org/10.1117/12.478061
2. Ansys Lumerical MODE-EME solver introduction —
   https://optics.ansys.com/hc/en-us/articles/360034396614
3. SimWorks Eigenmode Expansion (EME) Solver —
   https://www.emsimworks.com/en/solver/EME
4. EMEpy — Open-source eigenmode expansion solver in Python（BYUCamachoLab）—
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

from polaris.sim.fde import Mode

__all__ = ["overlap_matrix"]


def _stack_field(modes: list[Mode], field: str) -> np.ndarray:
    """将模式列表的指定场分量堆叠为 3D 复数数组 (M, Nx, Ny)。

    Args:
        modes: 模式列表（长度 M）。
        field: 场分量名（'ex'/'ey'/'ez'/'hx'/'hy'/'hz'）。

    Returns:
        3D complex128 数组 (M, Nx, Ny)，M = len(modes)。
    """
    return np.stack(
        [np.asarray(getattr(m, field), dtype=np.complex128) for m in modes],
        axis=0,
    )


def overlap_matrix(
    modes_a: list[Mode],
    modes_b: list[Mode],
    dx: float,
    dy: float,
) -> tuple[np.ndarray, np.ndarray]:
    """构造双向重叠积分矩阵 (M_E, M_H)（A02 §7.2）。

    M_E[m,n] = 0.5·∫(e_n^B × h_m^{A*})·ẑ dA   （B 的 E 投影到 A 的 H）
    M_H[m,n] = 0.5·∫(e_m^A × h_n^{B*})·ẑ dA   （A 的 E 投影到 B 的 H）

    向量化实现（python代码开发规则.md §4，禁止 Python 循环）：
        用 ``numpy.einsum`` 一次性计算所有模式对的重叠积分，性能远超双 for 循环。

    Args:
        modes_a: cell A 的本地本征模列表（来自 FDE，已按 1W 功率归一化）。
        modes_b: cell B 的本地本征模列表（来自 FDE，已按 1W 功率归一化）。
        dx: x 方向网格间距（米）。
        dy: y 方向网格间距（米）。

    Returns:
        (M_E, M_H): 两个复数矩阵，形状均为 (M_A, M_B)，
            M_A = len(modes_a)，M_B = len(modes_b)。

    Raises:
        ValueError: 模式列表为空、网格间距非正、或两侧网格形状不一致
            （规则 14：禁止 fall-back）。
    """
    if not modes_a or not modes_b:
        raise ValueError("模式列表不能为空（规则 14：禁止 fall-back）")
    if dx <= 0.0 or dy <= 0.0:
        raise ValueError(f"网格间距必须为正，实际 dx={dx}, dy={dy}")

    # 堆叠场分量为 3D 数组 (M, Nx, Ny) —— 数据准备，非数值运算
    e_a_ex = _stack_field(modes_a, "ex")
    e_a_ey = _stack_field(modes_a, "ey")
    h_a_hx = _stack_field(modes_a, "hx")
    h_a_hy = _stack_field(modes_a, "hy")
    e_b_ex = _stack_field(modes_b, "ex")
    e_b_ey = _stack_field(modes_b, "ey")
    h_b_hx = _stack_field(modes_b, "hx")
    h_b_hy = _stack_field(modes_b, "hy")

    # 校验两侧网格形状一致（重叠积分要求同一横向网格）
    shape_a = e_a_ex.shape[1:]
    shape_b = e_b_ex.shape[1:]
    if shape_a != shape_b:
        raise ValueError(
            f"模式网格形状不一致: A={shape_a} vs B={shape_b}，"
            "无法计算重叠积分（要求两侧 FDE 网格相同）。"
        )

    # 向量化重叠积分（einsum，禁止 Python 循环，python代码开发规则.md §4）
    # M_E[k, n] = 0.5·Σ_xy(e_b_ex[n,·]·conj(h_a_hy[k,·]) - e_b_ey[n,·]·conj(h_a_hx[k,·]))·dx·dy
    # einsum('nxy,kxy->kn', A, B) = Σ_xy A[n,x,y]·B[k,x,y]  →  输出形状 (M_A, M_B)
    m_e_term1 = np.einsum("nxy,kxy->kn", e_b_ex, np.conj(h_a_hy))
    m_e_term2 = np.einsum("nxy,kxy->kn", e_b_ey, np.conj(h_a_hx))
    m_e = 0.5 * (m_e_term1 - m_e_term2) * dx * dy

    # M_H[m, n] = 0.5·Σ_xy(e_a_ex[m,·]·conj(h_b_hy[n,·]) - e_a_ey[m,·]·conj(h_b_hx[n,·]))·dx·dy
    # einsum('mxy,nxy->mn', A, B) = Σ_xy A[m,x,y]·B[n,x,y]  →  输出形状 (M_A, M_B)
    m_h_term1 = np.einsum("mxy,nxy->mn", e_a_ex, np.conj(h_b_hy))
    m_h_term2 = np.einsum("mxy,nxy->mn", e_a_ey, np.conj(h_b_hx))
    m_h = 0.5 * (m_h_term1 - m_h_term2) * dx * dy

    return m_e, m_h
