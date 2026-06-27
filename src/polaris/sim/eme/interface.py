"""EME 界面 S 矩阵构造（A02 §7.3，切向场连续 + 正交投影）。

在 cell A→B 界面，由切向场连续性 + 模式正交投影求解界面 S 矩阵。
两个重叠积分矩阵 M_E（B 的 E 投影到 A 的 H）与 M_H（A 的 E 投影到 B 的 H）
分别对应切向 E 与切向 H 的连续性方程，联立求解得反射/透射矩阵。

公式（已用 Fresnel 单界面验证正确，A02 §7.3）::

    S11 = (M_E - M_H)·(M_E + M_H)^{-1}    （A 侧反射矩阵）
    S21 = 2·(M_E + M_H)^{-1}              （A→B 透射矩阵）
    S12 = S21^T                            （互易性：B→A 透射 = A→B 透射的转置）
    S22 = -S11                             （对称结构：B 侧反射 = -A 侧反射）

Fresnel 验证（单模 n1→n2 界面，平面波极限）::

    S11 = (n1 - n2)/(n1 + n2)         （Fresnel 反射系数 r）
    S21 = 2·sqrt(n1·n2)/(n1 + n2)    （Fresnel 透射系数 t，含功率归一化）

要求两侧模式数相同（M_A = M_B = M），否则 M_E + M_H 非方阵无法求逆。
互易性 S12 = S21^T 来自洛伦兹互易定理（A02 §7.2）。

BlockSMatrix 约定（与 ``polaris.sim.cascade.smatrix.BlockSMatrix`` 一致）::

    [b_left ]   [S11  S12] [a_left ]
    [b_right] = [S21  S22] [a_right]

其中 a_left 为左入射前向波，a_right 为右入射后向波，b_left/b_right 为出射波。

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
6. Photon Design FIMMPROP EME paper（界面 S 矩阵推导） —
   https://photond.com/assets/files/FIMMWAVE/PW03_eme_paper.pdf
7. Oktay & Magden 2024 arXiv:2407.09847 —
   https://arxiv.org/abs/2407.09847

规则依据：project_rules.md 规则 14（禁止 fall-back）/规则 18（学术诚信）
/规则 26（GPU 不参与，纯 NumPy）
"""

from __future__ import annotations

import numpy as np
from scipy.linalg import sqrtm

from polaris.sim.cascade.smatrix import BlockSMatrix
from polaris.sim.eme.overlap import overlap_matrix
from polaris.sim.fde import Mode

__all__ = ["build_interface_smatrix"]


def build_interface_smatrix(
    modes_a: list[Mode],
    modes_b: list[Mode],
    dx: float,
    dy: float,
) -> BlockSMatrix:
    """构造界面 S 矩阵（A02 §7.3，切向场连续 + 正交投影 + 能量守恒归一化）。

    在 cell A→B 界面，由重叠积分矩阵 M_E, M_H 求解反射/透射矩阵::

        S11 = (M_E - M_H)·(M_E + M_H)^{-1}    （A 侧反射）
        S21 = 2·(M_E + M_H)^{-1}              （A→B 透射）
        S12 = S21^T                            （互易性，B→A 透射）
        S22 = -S11                             （对称结构，B 侧反射）

    随后执行**能量守恒归一化**（对标 Lumerical EME "Energy Conservation" /
    Max-Optics "Energy Conservation" 选项）：模式集不完备（有限模式截断）时，
    界面 S 矩阵非严格酉（|S11|²+|S21|²≠1），归一化强制功率守恒。

    归一化公式（对称形式，保持互易性 S12=S21^T）::

        G = sqrtm( (S11†·S11 + S21†·S21 + S12†·S12 + S22†·S22) / 2 )
        S_ij ← G^{-1}·S_ij    （四个分块统一左乘 G^{-1}）

    标量（M=1）下 G = sqrt(|S11|²+|S21|²)，归一化后严格 |S11|²+|S21|²=1。
    多模下 G 为 Hermitian 正定矩阵（功率增益矩阵的对称平均），G^{-1} 为 Hermitian，
    保持互易性；归一化后 S†S 的对称平均 = I（近似功率守恒，标量下严格）。

    要求两侧模式数相同（M_A = M_B = M），否则 M_E + M_H 非方阵无法求逆。

    Fresnel 验证（单模 n1→n2 界面）：
        S11 = (n1-n2)/(n1+n2)（Fresnel r），S21 = 2·sqrt(n1·n2)/(n1+n2)。
        归一化前已严格功率守恒（|r|²+|t|²=1），G=1，归一化不变。

    正交归一验证（同模式集 modes_a == modes_b）：
        M_E = M_H = I → S11 = 0, S21 = I（M1 验收点），G=I，归一化不变。

    Args:
        modes_a: cell A 的本地本征模列表（来自 FDE，已功率归一化）。
        modes_b: cell B 的本地本征模列表（来自 FDE，已功率归一化）。
        dx: x 方向网格间距（米）。
        dy: y 方向网格间距（米）。

    Returns:
        界面 BlockSMatrix（2M×2M 分块，M = len(modes_a) = len(modes_b)），
        已做能量守恒归一化。

    Raises:
        ValueError: 两侧模式数不匹配（规则 14：禁止 fall-back）。
        RuntimeError: (M_E + M_H) 奇异或归一化矩阵 G 奇异（规则 14）。
    """
    # 构造重叠积分矩阵（向量化，A02 §7.2）
    m_e, m_h = overlap_matrix(modes_a, modes_b, dx, dy)
    m_a, m_b = m_e.shape
    if m_a != m_b:
        raise ValueError(
            f"界面两侧模式数不匹配: M_A={m_a} vs M_B={m_b}。"
            "界面 S 矩阵要求两侧模式数一致（M_E + M_H 须为方阵方可求逆）。"
        )

    # (M_E + M_H) 求逆（一次性计算，复用于 S11 与 S21，避免重复求逆）
    m_sum = m_e + m_h
    m_diff = m_e - m_h
    # 检查可逆性（规则 14：奇异即 raise，禁止 fall-back）
    rank = np.linalg.matrix_rank(m_sum)
    if rank < m_a:
        raise RuntimeError(
            f"界面 S 矩阵 (M_E + M_H) 奇异，rank={rank}/{m_a}。"
            "检查模式正交性或界面物理合理性（介电常数对比度过大或模式简并）。"
        )
    inv_sum = np.linalg.inv(m_sum)

    # 界面 S 矩阵四个分块（A02 §7.3 公式）
    s11 = m_diff @ inv_sum
    s21 = 2.0 * inv_sum
    s12 = s21.T  # 互易性（洛伦兹互易定理）
    s22 = -s11  # 对称结构

    # 能量守恒归一化（对标 Lumerical "Energy Conservation" / Max-Optics
    # "Energy Conservation"）。模式集不完备时界面 S 矩阵非酉（功率增益≠1），
    # 归一化强制功率守恒。标量下严格 |S11|²+|S21|²=1；多模下对称平均酉化，
    # 保持互易性 S12=S21^T（G Hermitian → G^{-1} Hermitian）。
    # 文献：Max-Optics EME Analysis "Energy Conservation: Set the norm of
    #   Page S-matrix to 1" —
    #   https://kb.max-optics.com/docs/tutorial/Maxoptics_GUI/8Analysis/
    #   Lumerical EME Propagate（energy conservation 选项）—
    #   https://optics.ansys.com/hc/en-us/articles/360034396614
    g_avg = sqrtm(
        0.5
        * (
            s11.conj().T @ s11
            + s21.conj().T @ s21
            + s12.conj().T @ s12
            + s22.conj().T @ s22
        )
    )
    # Hermitian 正定矩阵 sqrtm 数值上可能带微小虚部，取实部清洗
    if np.iscomplexobj(g_avg):
        g_imag = float(np.max(np.abs(np.imag(g_avg))))
        if g_imag > 1e-9:
            raise RuntimeError(
                f"能量守恒归一化 G 矩阵非 Hermitian（虚部 {g_imag:.2e}），"
                "检查界面 S 矩阵物理合理性（规则 14）。"
            )
        g_avg = np.real(g_avg).astype(np.complex128)
    # 检查 G 可逆（奇异即 raise，规则 14）
    g_rank = np.linalg.matrix_rank(g_avg)
    if g_rank < m_a:
        raise RuntimeError(
            f"能量守恒归一化 G 矩阵奇异，rank={g_rank}/{m_a}。"
            "检查界面 S 矩阵是否退化（规则 14：禁止 fall-back）。"
        )
    # G^{-1}·S_ij（统一左乘，保持互易性：G^{-1} Hermitian → S12=G^{-1}·S21^T=(G^{-1}·S21)^T）
    g_inv = np.linalg.inv(g_avg)
    s11 = g_inv @ s11
    s12 = g_inv @ s12
    s21 = g_inv @ s21
    s22 = g_inv @ s22
    return BlockSMatrix(s11, s12, s21, s22)
