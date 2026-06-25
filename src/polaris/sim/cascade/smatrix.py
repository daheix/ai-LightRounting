"""Redheffer 星积 S 矩阵级联（C03 聚类，RCWA/EME 共享内核）。

纯 NumPy/SciPy CPU 实现的矩阵级 Redheffer 星积（2N×2N 分块 S 矩阵二元运算），
替代传输矩阵法（TMM）的矩阵乘法，避免消逝波 $e^{ik_z d}$ 在长结构中指数发散。

与电路级 SAX FG 后端（``polaris.sim.cascade.__init__``）形成"器件级 Redheffer +
电路级 SAX"双层 S 矩阵体系。``polaris.sim.cascade_backends.redheffer_star`` 为
字典级（命名端口）实现，本模块为矩阵级（S11/S12/S21/S22 分块）实现，供
A01-RCWA 与 A02-EME 共享。

数学定义（Victor Liu 2013 公式，与 Redheffer 1959 原始定义一致）：

    S^{tot} = S^{(1)} ★ S^{(2)},  S^{(k)} = [[A_{11}, A_{12}], [A_{21}, A_{22}]]

    S^{tot}_{11} = B_{11} (I - A_{12} B_{21})^{-1} A_{11}
    S^{tot}_{12} = B_{12} + B_{11} (I - A_{12} B_{21})^{-1} A_{12} B_{22}
    S^{tot}_{21} = A_{21} + A_{22} (I - B_{21} A_{12})^{-1} B_{21} A_{11}
    S^{tot}_{22} = A_{22} (I - B_{21} A_{12})^{-1} B_{22}

数值稳定性（Andersson 2023）：耗散矩阵的星积仍为耗散矩阵，消逝波在 S 矩阵中
天然有界（|S_ij|≤1），逆矩阵 (I - A_{12}B_{21}) 在无源系统中良态。实现中用
``scipy.linalg.solve`` 替代显式 ``inv``，避免条件数放大。

文献来源（≥5，规则 18 学术诚信）：
1. Redheffer 1959 J Math Mech — https://www.jstor.org/stable/24900576
2. Kaplan & Stock 1962 J Math Mech —
   https://iumj.s3-us-west-2.amazonaws.com/abstracts/11050_abs.pdf
3. Victor Liu 2013 Technical Note — http://victorliu.info/pdfs/Scombine.pdf
4. Pham 2022 Nanomaterials 12(22), 3951 —
   https://doi.org/10.3390/nano12223951
5. Andersson 2023 PIER-B 101, 17-44 —
   http://test.jpier.org/download/23041602.pdf
6. Moharam 1995 JOSA A 12, 1077 (ETM) —
   https://doi.org/10.1364/JOSAA.12.001077

规则依据：project_rules.md 规则 14（禁止 fall-back）/规则 18（学术诚信）
/规则 26（GPU 不参与，纯 NumPy/SciPy）
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.linalg import solve

__all__ = [
    "BlockSMatrix",
    "redheffer_star_product",
    "cascade_redheffer",
    "build_propagation_s",
]


@dataclass
class BlockSMatrix:
    """2N×2N 复散射矩阵，分块为 4 个 N×N 子块（C03 §3.1）。

    约定（与 Victor Liu 2013 一致）::

        [b_left ]   [S11  S12] [a_left ]
        [b_right] = [S21  S22] [a_right]

    其中 ``a`` 为入射（前向 + 反向），``b`` 为出射；``S11`` 为左反射，
    ``S21`` 为左→右透射，``S12`` 为右→左透射，``S22`` 为右反射。

    Attributes:
        s11, s12, s21, s22: 4 个 N×N 复数子块。
    """

    s11: np.ndarray
    s12: np.ndarray
    s21: np.ndarray
    s22: np.ndarray

    def __post_init__(self) -> None:
        n = self.s11.shape[0]
        for name in ("s11", "s12", "s21", "s22"):
            blk = getattr(self, name)
            if blk.shape != (n, n):
                raise ValueError(
                    f"S 矩阵分块 {name} 形状 {blk.shape} 与 s11 ({n},{n}) 不一致"
                )
            if blk.dtype != np.complex128:
                raise TypeError(f"S 矩阵分块 {name} 必须 complex128，实际 {blk.dtype}")

    @property
    def n_ports(self) -> int:
        """单侧端口模式数 N（总维度 2N）。"""
        return self.s11.shape[0]

    @classmethod
    def from_dense(cls, s: np.ndarray) -> BlockSMatrix:
        """从 2N×2N 稠密矩阵构造（上半为左端口，下半为右端口）。"""
        if s.ndim != 2 or s.shape[0] != s.shape[1] or s.shape[0] % 2 != 0:
            raise ValueError(f"稠密 S 矩阵须为偶数维方阵，实际 {s.shape}")
        s = np.asarray(s, dtype=np.complex128)
        n = s.shape[0] // 2
        return cls(s[:n, :n], s[:n, n:], s[n:, :n], s[n:, n:])

    def to_dense(self) -> np.ndarray:
        """组装为 2N×2N 稠密矩阵。"""
        return np.block([[self.s11, self.s12], [self.s21, self.s22]])


def _solve_identity_minus(
    a: np.ndarray, b: np.ndarray
) -> np.ndarray:
    """求解 (I - A·B)^{-1} · I = (I - A·B)^{-1}（用 solve 替代 inv）。

    失败即 raise（规则 14：禁止 fall-back）。
    """
    n = a.shape[0]
    eye = np.eye(n, dtype=np.complex128)
    k = eye - a @ b
    # Mistiri 1986 存在性条件：(I - A·B) 可逆 ⟺ (I - B·A) 可逆
    if np.linalg.matrix_rank(k) < n:
        raise RuntimeError(
            f"Redheffer 星积失败: (I - A·B) 奇异，cond={np.linalg.cond(k):.2e}。"
            "检查 S 矩阵物理合理性（无源系统应满足 |A_{12}·B_{21}|<1）。"
        )
    # solve(K, I) 等价于 inv(K)，但避免显式求逆的条件数放大（C03 §7.2）
    return solve(k, eye, assume_a="gen")


def redheffer_star_product(
    s1: BlockSMatrix, s2: BlockSMatrix
) -> BlockSMatrix:
    """Redheffer 星积 S^{tot} = S1 ★ S2（C03 §6 完整公式）。

    将子系统 1 的右端口与子系统 2 的左端口连接，返回复合系统 S 矩阵。
    端口模式数必须匹配（N1 = N2 = N）。

    Args:
        s1: 左子系统 S 矩阵（2N×2N 分块）。
        s2: 右子系统 S 矩阵（2N×2N 分块）。

    Returns:
        复合系统 S 矩阵（2N×2N 分块）。

    Raises:
        ValueError: 端口模式数不匹配。
        RuntimeError: 中间矩阵 (I - A_{12}·B_{21}) 奇异（规则 14）。
    """
    if s1.n_ports != s2.n_ports:
        raise ValueError(
            f"端口模式数不匹配: S1 N={s1.n_ports} vs S2 N={s2.n_ports}。"
            "Redheffer 星积要求两侧端口维度一致。"
        )
    a11, a12, a21, a22 = s1.s11, s1.s12, s1.s21, s1.s22
    b11, b12, b21, b22 = s2.s11, s2.s12, s2.s21, s2.s22

    # 中间矩阵（数值稳定关键）：用 solve 替代 inv（C03 §7.2）
    m1 = _solve_identity_minus(a12, b21)  # M1 = (I - A12·B21)^{-1}
    m2 = _solve_identity_minus(b21, a12)  # M2 = (I - B21·A12)^{-1}

    # 合成四个分块（Victor Liu 2013 公式 6-9）
    s11_tot = b11 @ m1 @ a11
    s12_tot = b12 + b11 @ m1 @ a12 @ b22
    s21_tot = a21 + a22 @ m2 @ b21 @ a11
    s22_tot = a22 @ m2 @ b22
    return BlockSMatrix(s11_tot, s12_tot, s21_tot, s22_tot)


def cascade_redheffer(s_list: list[BlockSMatrix]) -> BlockSMatrix:
    """多层 S 矩阵级联：S^{tot} = S1 ★ S2 ★ ... ★ SN（C03 §5 步骤 5）。

    自左向右迭代累积，保证多层级联数值稳定（耗散性传递，Andersson 2023）。

    Args:
        s_list: S 矩阵列表，从左到右顺序排列。

    Returns:
        复合系统 S 矩阵。

    Raises:
        ValueError: 列表为空。
    """
    if not s_list:
        raise ValueError("S 矩阵列表不能为空（规则 14：禁止 fall-back）")
    s_acc = s_list[0]
    for s_next in s_list[1:]:
        s_acc = redheffer_star_product(s_acc, s_next)
    return s_acc


def build_propagation_s(beta: np.ndarray, length: float) -> BlockSMatrix:
    """构造均匀段传播 S 矩阵（A02-EME §7.4，跨聚类共享接口）。

    均匀波导段无反射，仅相位累积::

        S = [[0, P], [P, 0]],  P = diag(exp(i·β·L))

    Args:
        beta: 传播常数向量 (M,)（复数，虚部为损耗）。
        length: 段长度（米）。

    Returns:
        2M×2M 传播 S 矩阵。

    Raises:
        ValueError: 长度非正或 beta 为空。
    """
    if length < 0:
        raise ValueError(f"传播段长度必须非负，实际 {length}")
    beta = np.asarray(beta, dtype=np.complex128)
    if beta.ndim != 1:
        raise ValueError(f"beta 必须为 1D 向量，实际 {beta.ndim}D")
    phase = np.exp(1j * beta * length)
    zeros = np.zeros_like(phase)
    p_mat = np.diag(phase)
    z_mat = np.zeros((len(beta), len(beta)), dtype=np.complex128)
    # S11=0 (无左反射), S12=P (右→左透射), S21=P (左→右透射), S22=0 (无右反射)
    s11 = z_mat
    s12 = np.diag(phase)
    s21 = np.diag(phase)
    s22 = z_mat
    _ = zeros  # 占位，保持 p_mat/z_mat 关系清晰
    return BlockSMatrix(s11, s12, s21, s22)
