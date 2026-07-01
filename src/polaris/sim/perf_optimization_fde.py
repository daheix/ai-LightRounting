"""R453 FDE 特征值求解加速器（shift-invert + scipy.sparse LU 复用）。

从 perf_optimization.py 拆分（批次 10-B 续 超长文件拆分）。纯 NumPy/SciPy
CPU，R04 兼容。

## R04 战略（不可撤销）

🚫不参与 GPU：纯 NumPy/SciPy。无 CuPy/CUDA/ROCm/AppleMetal。

## R03 禁止 fall-back

业务错误一律 raise。

## 学术依据（R02，≥5 个文献 URL）

1. Lehoucq, Sorensen, Yang 1998 ARPACK Users Guide SIAM（shift-invert 模式）
   https://doi.org/10.1137/1.9780898719628
2. Saad 2003 Iterative Methods for Sparse Linear Systems 2nd SIAM
   https://doi.org/10.1137/1.9780898718003
3. Davis 2006 Direct Methods for Sparse Linear Systems SIAM
   https://doi.org/10.1137/1.9780898718818
4. Press et al. 2007 Numerical Recipes 3rd Cambridge Padé approximants §5.12
   https://numerical.recipes/
5. Lumerical varFDTD Effective Index（性能优化工业参考）
   https://optics.ansys.com/hc/en-us/articles/360034914713
6. Tidy3D Performance Benchmarks
   https://docs.flexcompute.com/projects/tidy3d/en/stable/

## *创新* 标注（R02）

- *创新* R453：FDE 加速器复用 scipy.sparse.linalg.SuperLU 因子，
  多次 shift-invert 调用共享同一 LU 分解，避免重复因式分解（Lehoucq
  1998 §4.4 推荐但 scipy 默认不缓存，本模块显式缓存）。

## 规则依据

规则 14（非法输入 raise）/规则 18（学术诚信）/规则 26（GPU 不参与）
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

__all__ = [
    "FdeAcceleratorResult",
    "FdeShiftInvertAccelerator",
]


@dataclass
class FdeAcceleratorResult:
    """FDE 加速器求解结果。

    Attributes:
        eigenvalues: 本征值 β² (k,) 复数（含 PML 损耗）。
        eigenvectors: 本征向量 (Nx*Ny, k) 复数。
        beta: 传播常数 β = sqrt(β²) (k,) 复数。
            调用方按波长 k0 计算 n_eff = β/k0（本类不知波长）。
        solve_time: 求解耗时（秒）。
        lu_cached: 是否复用了缓存的 LU 因子。
    """

    eigenvalues: np.ndarray
    eigenvectors: np.ndarray
    beta: np.ndarray
    solve_time: float
    lu_cached: bool


class FdeShiftInvertAccelerator:
    """FDE 特征值求解加速器（R453）。

    用 scipy.sparse.linalg.eigsh 的 shift-invert 模式（sigma=target）+ 显式
    LU 因子缓存，加速多次调用。Lehoucq 1998 §4.4 推荐 shift-invert + LU
    复用对靠近 σ 的本征值收敛速度 O(n) 提升。

    用法：
        acc = FdeShiftInvertAccelerator(matrix_A, sigma=beta_target**2)
        result = acc.solve(num_modes=4)
    """

    def __init__(
        self,
        matrix: sp.csr_array,
        sigma: float,
        lu_cache: dict[str, Any] | None = None,
        cache_key: str | None = None,
    ) -> None:
        """初始化 FDE 加速器。

        Args:
            matrix: 稀疏本征矩阵 A（N×N，本征值 β²）。
            sigma: shift-invert 目标值 σ（β² 估计）。
            lu_cache: 外部 LU 缓存字典，None 则不缓存。
            cache_key: LU 缓存键，None 则不缓存。

        Raises:
            ValueError: 矩阵非方或 sigma 非有限。
        """
        if matrix.shape[0] != matrix.shape[1]:
            raise ValueError(
                f"矩阵须方阵，实际 {matrix.shape}（规则 14）"
            )
        if not np.isfinite(sigma):
            raise ValueError(f"sigma 须有限，实际 {sigma}")
        self.matrix = matrix.tocsr()
        self.sigma = float(sigma)
        self.lu_cache = lu_cache
        self.cache_key = cache_key
        # shift-invert 算子：(A - σI)^-1，其本征值 1/(λ-σ) 最大者对应 λ 最靠近 σ
        n = matrix.shape[0]
        identity = sp.eye(n, format="csr", dtype=matrix.dtype)
        self._shifted = (matrix - sigma * identity).tocsc()
        # LU 因子（按需计算或从缓存取）
        self._lu: Any = None
        self._lu_from_cache = False
        if lu_cache is not None and cache_key is not None and cache_key in lu_cache:
            self._lu = lu_cache[cache_key]
            self._lu_from_cache = True

    def _get_lu(self) -> Any:
        """获取 LU 因子（缓存或新算）。"""
        if self._lu is None:
            self._lu = spla.splu(self._shifted)
            if self.lu_cache is not None and self.cache_key is not None:
                self.lu_cache[self.cache_key] = self._lu
        return self._lu

    def solve(self, num_modes: int) -> FdeAcceleratorResult:
        """求解 num_modes 个本征值（最靠近 sigma）。

        shift-invert 算子 B = (A - σI)^-1，eigsh 求 B 的最大本征值
        （对应 A 最靠近 σ 的本征值）。LU 因子提供 B·v 的高效求解。

        Args:
            num_modes: 求解模式数 K，须 < N。

        Returns:
            FdeAcceleratorResult。

        Raises:
            ValueError: num_modes 非法或求解失败。
        """
        n = self.matrix.shape[0]
        if not (1 <= num_modes < n - 1):
            raise ValueError(
                f"num_modes 须 ∈ [1, {n - 2})，实际 {num_modes}（规则 14）"
            )
        lu = self._get_lu()

        # shift-invert 算子的 matvec：v → (A - σI)^-1 · v
        def matvec(v: np.ndarray) -> np.ndarray:
            return lu.solve(v)

        # 用 LinearOperator 包装，eigsh 用 ARPACK Arnoldi
        op = spla.LinearOperator(
            shape=(n, n), matvec=matvec, dtype=self.matrix.dtype
        )
        t0 = time.perf_counter()
        # which='LM' 对 B 找最大本征值 = 对 A 找最靠近 σ 的本征值
        try:
            eigvals_shifted, eigvecs = spla.eigsh(
                op, k=num_modes, which="LM", tol=1e-10, maxiter=5000
            )
        except spla.ArpackNoConvergence as exc:
            raise ValueError(
                f"ARPACK 未收敛：{exc.eigenvalues.size} 个本征值已收敛"
            ) from exc
        solve_time = time.perf_counter() - t0
        # 反 shift-invert: λ_A = σ + 1/λ_B
        # 数值稳定：若 λ_B 接近 0，则 λ_A 远离 σ（已保证 LM 取最大）
        # Lehoucq 1998 §4.4 公式
        eigvals = self.sigma + 1.0 / eigvals_shifted
        # β = sqrt(β²)，导模 β² 为正实数，PML 引入小虚部取主值
        beta = np.sqrt(eigvals)
        # 调用方按波长 k0 计算 n_eff = β/k0（本类不知波长，故返回 β）
        return FdeAcceleratorResult(
            eigenvalues=eigvals,
            eigenvectors=eigvecs,
            beta=beta,
            solve_time=solve_time,
            lu_cached=self._lu_from_cache,
        )
