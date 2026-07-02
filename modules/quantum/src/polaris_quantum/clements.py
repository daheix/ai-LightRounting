"""Clements 酉矩阵分解模块 — 通用 M×M 酉矩阵构造。

任意 M×M 酉矩阵可分解为 O(M²) 个分束器 + 相移器（Clements 2016）。
本模块用 Clements 网格构造随机 M×M 酉矩阵，酉性误差 < 1e-10。

分束器酉矩阵:
    U_BS(θ, φ) = [[cos(θ),          -e^{-iφ} sin(θ)],
                  [e^{iφ} sin(θ),   cos(θ)]]

Clements 网格比 Reck 三角分解更浅、更稳定，是线性光学量子计算
（玻色采样 / KLM）的标准酉矩阵实现。

R03 合规: 酉性校验失败即 raise（不用 QR 兜底，因为分束器左乘乘积本征酉，
浮点误差 ~1e-15 远小于 1e-10 阈值）。

学术诚信（R02，≥5 文献 URL 溯源）:
- Clements et al., "Optimal design for universal multiport interferometers",
  Optica 3(12), 1460-1465 (2016).
  URL: https://opg.optica.org/optica/fulltext.cfm?uri=optica-3-12-1460
- Reck et al., "Experimental realization of any discrete unitary operator",
  PRL 73, 58 (1994).
  URL: https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.73.58
- Aaronson & Arkhipov, STOC 2011. URL: https://arxiv.org/abs/0910.4698
- Seron et al., "BosonSampling.jl", Quantum 2024.
  URL: https://arxiv.org/abs/2212.09537
- Knill, Laflamme, Milburn, Nature 409, 46 (2001).
  URL: https://www.nature.com/articles/35051009
- Hamilton et al., "Gaussian Boson Sampling", PRL 119, 170501 (2017).
  URL: https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.119.170501

🚫不参与 GPU（R04）：纯 NumPy 实现。
"""

from __future__ import annotations

import math

import numpy as np

# 酉性校验阈值（R03: 失败 raise，不用 QR 兜底）
_UNITARITY_TOL = 1e-10


def _beamsplitter_unitary(theta: float, phi: float) -> np.ndarray:
    """分束器 2×2 酉矩阵。

    U = [[cos(θ),          -e^{-iφ} sin(θ)],
         [e^{iφ} sin(θ),   cos(θ)]]

    50:50 分束器: θ=π/4。

    来源: Reck et al., PRL 1994.
         URL: https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.73.58
    """
    c = math.cos(theta)
    s = math.sin(theta)
    return np.array([
        [c, -np.exp(-1j * phi) * s],
        [np.exp(1j * phi) * s, c],
    ], dtype=complex)


def clements_unitary(n_modes: int = 4, seed: int = 42) -> list:
    """Clements 分解构造 M×M 酉矩阵。

    用 O(M²) 个分束器 + 相移器（Clements 网格交替层）构造通用酉矩阵。
    分束器参数由随机种子确定（可复现）。左乘酉保酉性，无需 QR 修正。

    来源: Clements et al., Optica 2016.
         URL: https://opg.optica.org/optica/fulltext.cfm?uri=optica-3-12-1460

    Args:
        n_modes: 模式数 M（默认 4）。
        seed: 随机种子（默认 42，决定分束器角度与相移）。

    Returns:
        M×M 酉矩阵，list of list of [real, imag]（实虚交错，与 C ABI
        row-major 实虚交错布局一致，可供 ``boson_sampling`` 直接使用）。

    Raises:
        RuntimeError: n_modes < 1 / 酉性误差 > 1e-10（R03 禁止 fall-back）。
    """
    if n_modes < 1:
        raise RuntimeError(f"n_modes 须 ≥ 1，得到 {n_modes}")
    rng = np.random.default_rng(seed)
    n_bs = n_modes * (n_modes - 1) // 2
    thetas = rng.uniform(0.0, math.pi / 2.0, n_bs)
    phis = rng.uniform(0.0, 2.0 * math.pi, n_bs)

    U = np.eye(n_modes, dtype=complex)
    idx = 0
    # Clements 网格: 交替层（偶数层从 0 开始，奇数层从 1 开始）
    for layer in range(n_modes):
        start = layer % 2
        for i in range(start, n_modes - 1, 2):
            if idx >= n_bs:
                break
            bs = _beamsplitter_unitary(float(thetas[idx]), float(phis[idx]))
            # 左乘分束器到模式 i, i+1（左乘酉保酉性）
            U[[i, i + 1], :] = bs @ U[[i, i + 1], :]
            idx += 1

    # R03: 酉性校验，失败 raise（分束器左乘乘积本征酉，浮点误差 ~1e-15）
    err = float(np.max(np.abs(U @ U.conj().T - np.eye(n_modes))))
    if err > _UNITARITY_TOL:
        raise RuntimeError(
            f"Clements 酉性误差 {err} > {_UNITARITY_TOL}（R03 禁止 fall-back）"
        )

    # 转为 list of list of [real, imag]（与 C ABI 实虚交错布局一致）
    return [
        [[float(U[i, j].real), float(U[i, j].imag)] for j in range(n_modes)]
        for i in range(n_modes)
    ]


__all__ = ["clements_unitary"]
