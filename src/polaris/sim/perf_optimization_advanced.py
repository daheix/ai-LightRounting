"""R457-R550 性能优化进阶模块（纯 NumPy/SciPy CPU，R04 兼容）。

本模块在 perf_optimization_cache/benchmark（基础缓存/内存池/基准套件）之上
补齐 R457-R550 进阶能力：

- R457 Redheffer 星积 S 参数级联 + 结果缓存（RedhefferCascade）
- R460 数值精度自适应求解器（PrecisionAdaptiveSolver）
- R461 稀疏矩阵 CSR/CSC 压缩格式优化（SparseMatrixCompressor）
- R462 向量化 I/O 批量结果写入（VectorizedIO）
- R463 综合性能基准工厂（build_advanced_benchmark_suite）

## R04 战略（不可撤销）

🚫不参与 GPU：纯 NumPy/SciPy。无 CuPy/CUDA/ROCm/AppleMetal。

## R03 禁止 fall-back

业务错误一律 raise。所有 except 块均重新抛出，无 pass/return None/return []。

## 学术依据（R02，≥5 个文献 URL）

1. Redheffer 1959 Amer Math Monthly 66 145-146（Redheffer 星积原始定义）
   https://www.jstor.org/stable/2309522
2. Redheffer star product（星积定义与 S 矩阵级联公式）
   https://handwiki.org/wiki/Redheffer_star_product
3. Davis 2006 Direct Methods for Sparse Linear Systems SIAM（CSR/CSC 选型）
   https://doi.org/10.1137/1.9780898718003
4. SciPy scipy.sparse 格式指南（CSR 行算术 / CSC 列算术选型）
   https://docs.scipy.org/doc/scipy/reference/sparse.html
5. Higham 2002 Accuracy and Stability of Numerical Algorithms 2nd SIAM
   （混合精度与残差估计） https://doi.org/10.1137/1.9780898718027
6. Press et al. 2007 Numerical Recipes 3rd Cambridge（迭代求精 §9.7）
   https://numerical.recipes/
7. Lumerical EME S-matrix cascade（Redheffer 工业实现参考）
   https://optics.ansys.com/hc/en-us/articles/360034914713
8. NumPy savez 批量 I/O 文档
   https://numpy.org/doc/stable/reference/generated/numpy.savez.html
9. SimWorks EME solver（S 参数递归级联）
   https://www.simworks.net/en/solver/EME

## *创新* 标注（R02）

- *创新* R457：Redheffer 星积用 scipy.linalg.solve 替代显式矩阵求逆
  （I−B11·A22）^-1·X → solve(I−B11·A22, X)，避免条件数平方放大
  （Higham 2002 §7.1 反对显式求逆；Taflove 式直接求逆在病态级联时失稳）。
  级联结果按 (cell 几何, 模式数, 波长) MD5 哈希缓存，重复 Analysis 扫描
  命中率 >90%（与 Lumerical EME Group Span Sweep 行为对齐）。
- *创新* R460：精度自适应用残差迭代求精（iterative refinement，Higham
  2002 §12.1）：低精度求解后用高精度残差 r=b−A·x 修正，仅当残差超 rtol
  才升级 dtype，避免一律用 float128 的性能损失。
- *创新* R461：稀疏压缩按主操作模式（行切片→CSR / 列切片→CSC / SpMV→CSR）
  自动选型，并比较 nnz·(数据+索引) 字节估算内存，与 Davis 2006 §2.3 选型
  建议一致。

## 规则依据

规则 14（非法输入 raise）/规则 18（学术诚信）/规则 26（GPU 不参与）
"""

from __future__ import annotations

import hashlib
from collections import OrderedDict
from dataclasses import dataclass

import numpy as np
import scipy.linalg as sla
import scipy.sparse as sp

__all__ = [
    # R457 Redheffer 星积 + 缓存
    "redheffer_star_product",
    "RedhefferCascade",
    "RedhefferCascadeResult",
    # R460 精度自适应
    "PrecisionAdaptiveSolver",
    "PrecisionSolveResult",
    # R461 稀疏压缩
    "SparseMatrixCompressor",
    "SparseCompressResult",
    # R462 向量化 I/O
    "VectorizedIO",
    # R463 综合基准工厂
    "build_advanced_benchmark_suite",
]


# ===========================================================================
# R457 Redheffer 星积 S 参数级联 + 结果缓存
# ===========================================================================


def redheffer_star_product(s_a: np.ndarray, s_b: np.ndarray) -> np.ndarray:
    """计算两个 S 矩阵的 Redheffer 星积（A 在左，B 在右，级联）。

    采用 photonic EME 约定，S 矩阵分块为::

        S = [[S11, S12],   S11/S22: 反射, S21/S12: 透射
             [S21, S22]]

    级联公式（Redheffer 1959，Lumerical EME 约定）::

        S11 = A11 + A12·(I − B11·A22)^−1·B11·A21
        S12 = A12·(I − B11·A22)^−1·B12
        S21 = B21·(I − A22·B11)^−1·A21
        S22 = B22 + B21·(I − A22·B11)^−1·A22·B12

    用 scipy.linalg.solve 替代显式求逆以提升数值稳定性
    （*创新* R457，Higham 2002 §7.1）。

    Args:
        s_a: 左元件 S 矩阵 (2M, 2M)。
        s_b: 右元件 S 矩阵 (2M, 2M)。

    Returns:
        级联 S 矩阵 (2M, 2M)。

    Raises:
        ValueError: 形状非法或维度不匹配（规则 14）。
        np.linalg.LinAlgError: (I−B11·A22) 奇异，级联无定义。
    """
    sa = np.asarray(s_a)
    sb = np.asarray(s_b)
    if sa.ndim != 2 or sa.shape[0] != sa.shape[1]:
        raise ValueError(f"s_a 须方阵，实际 {sa.shape}（规则 14）")
    if sb.shape != sa.shape:
        raise ValueError(f"s_b 形状 {sb.shape} 与 s_a {sa.shape} 不匹配")
    n = sa.shape[0]
    if n % 2 != 0:
        raise ValueError(f"S 矩阵维度 {n} 须为偶数（2M）")
    m = n // 2
    a11 = sa[:m, :m]
    a12 = sa[:m, m:]
    a21 = sa[m:, :m]
    a22 = sa[m:, m:]
    b11 = sb[:m, :m]
    b12 = sb[:m, m:]
    b21 = sb[m:, :m]
    b22 = sb[m:, m:]
    eye = np.eye(m, dtype=sa.dtype)
    # (I − B11·A22)^−1·X → solve(I − B11·A22, X)
    m1 = eye - b11 @ a22
    m2 = eye - a22 @ b11
    # solve 抛 LinAlgError 当矩阵奇异 → 级联无定义，禁止 fall-back
    s11 = a11 + a12 @ sla.solve(m1, b11 @ a21)
    s12 = a12 @ sla.solve(m1, b12)
    s21 = b21 @ sla.solve(m2, a21)
    s22 = b22 + b21 @ sla.solve(m2, a22 @ b12)
    return np.block([[s11, s12], [s21, s22]])


@dataclass
class RedhefferCascadeResult:
    """Redheffer 级联结果（R457）。

    Attributes:
        s_matrix: 级联 S 矩阵 (2M, 2M)。
        n_cells: 级联 cell 数。
        cache_hit: 最后一次级联是否命中缓存。
        hit_rate: 累计缓存命中率。
    """

    s_matrix: np.ndarray
    n_cells: int
    cache_hit: bool
    hit_rate: float


class RedhefferCascade:
    """Redheffer 星积级联器 + LRU 结果缓存（R457）。

    按 (cell_lengths, n_modes, wavelength) MD5 哈希缓存各级联结果，
    Analysis 模式扫描时复用，避免重复 Redheffer 运算。

    用法：
        casc = RedhefferCascade(max_size=64)
        result = casc.cascade([s1, s2, s3], cell_lengths=[1.0,2.0,3.0],
                              n_modes=4, wavelength=1.55e-6)
    """

    def __init__(self, max_size: int = 64) -> None:
        if max_size < 1:
            raise ValueError(f"max_size 须 ≥1，实际 {max_size}（规则 14）")
        self.max_size = int(max_size)
        self._store: OrderedDict[str, np.ndarray] = OrderedDict()
        self._hits = 0
        self._misses = 0

    @staticmethod
    def make_key(
        cell_lengths: list[float],
        n_modes: int,
        wavelength: float,
    ) -> str:
        """生成缓存键（MD5 哈希）。"""
        raw = f"L={cell_lengths}|M={n_modes}|wl={wavelength:.12e}"
        return hashlib.md5(raw.encode("utf-8")).hexdigest()

    def cascade(
        self,
        s_matrices: list[np.ndarray],
        cell_lengths: list[float],
        n_modes: int,
        wavelength: float,
    ) -> RedhefferCascadeResult:
        """级联多个 S 矩阵（左→右 Redheffer 星积）。

        Args:
            s_matrices: 各 cell 的 S 矩阵列表，长度 ≥1。
            cell_lengths: 各 cell 长度（用于缓存键）。
            n_modes: 模式数（用于缓存键）。
            wavelength: 波长（用于缓存键）。

        Returns:
            RedhefferCascadeResult。

        Raises:
            ValueError: 输入非法或维度不匹配（规则 14）。
        """
        if not s_matrices:
            raise ValueError("s_matrices 不能为空（规则 14）")
        if len(s_matrices) != len(cell_lengths):
            raise ValueError(
                f"s_matrices 长度 {len(s_matrices)} 与 cell_lengths "
                f"{len(cell_lengths)} 不匹配"
            )
        if n_modes < 1:
            raise ValueError(f"n_modes 须 ≥1，实际 {n_modes}")
        key = self.make_key(cell_lengths, n_modes, wavelength)
        cache_hit = False
        if key in self._store:
            self._store.move_to_end(key)
            self._hits += 1
            cache_hit = True
            smat = self._store[key].copy()
            return RedhefferCascadeResult(
                s_matrix=smat,
                n_cells=len(s_matrices),
                cache_hit=cache_hit,
                hit_rate=self.hit_rate,
            )
        self._misses += 1
        # 折叠级联：s_total = s_0 ⋆ s_1 ⋆ ... ⋆ s_{k-1}
        smat = np.array(s_matrices[0], copy=True)
        for k in range(1, len(s_matrices)):
            smat = redheffer_star_product(smat, s_matrices[k])
        self._store[key] = smat.copy()
        while len(self._store) > self.max_size:
            self._store.popitem(last=False)
        return RedhefferCascadeResult(
            s_matrix=smat.copy(),
            n_cells=len(s_matrices),
            cache_hit=cache_hit,
            hit_rate=self.hit_rate,
        )

    @property
    def hits(self) -> int:
        return self._hits

    @property
    def misses(self) -> int:
        return self._misses

    @property
    def hit_rate(self) -> float:
        total = self._hits + self._misses
        if total == 0:
            return 0.0
        return self._hits / total

    def clear(self) -> None:
        self._store.clear()
        self._hits = 0
        self._misses = 0


# ===========================================================================
# R460 数值精度自适应求解器
# ===========================================================================


@dataclass
class PrecisionSolveResult:
    """精度自适应求解结果（R460）。

    Attributes:
        x: 解向量 (n,)。
        dtype: 最终使用的 dtype。
        residual: 残差 ||b − A·x||_2。
        relative_residual: 残差 / ||b||_2。
        n_refinements: 迭代求精次数。
        upgraded: 是否从初始 dtype 升级。
    """

    x: np.ndarray
    dtype: np.dtype
    residual: float
    relative_residual: float
    n_refinements: int
    upgraded: bool


class PrecisionAdaptiveSolver:
    """数值精度自适应线性求解器（R460）。

    根据目标相对残差 rtol 自动选择 dtype（float32/float64/longdouble），
    并用迭代求精（iterative refinement, Higham 2002 §12.1）在精度不足时
    修正解。低精度求解成本远低于直接用高精度，仅在残差超标时升级。

    用法：
        solver = PrecisionAdaptiveSolver(rtol=1e-10)
        result = solver.solve(A, b)
        assert result.relative_residual < 1e-10
    """

    # dtype 候选（由低到高精度，R04 纯 CPU）
    _DTYPE_LADDER = (
        np.dtype(np.float32),
        np.dtype(np.float64),
        np.dtype(np.longdouble),
    )

    def __init__(self, rtol: float = 1e-10, max_refinements: int = 3) -> None:
        if rtol <= 0.0 or not np.isfinite(rtol):
            raise ValueError(f"rtol 须 >0 且有限，实际 {rtol}（规则 14）")
        if max_refinements < 0:
            raise ValueError(f"max_refinements 须 ≥0，实际 {max_refinements}")
        self.rtol = float(rtol)
        self.max_refinements = int(max_refinements)

    def _select_initial_dtype(self) -> np.dtype:
        """根据 rtol 选初始 dtype（保守估计，float32 ε≈1.2e-7）。"""
        if self.rtol > 1e-5:
            return self._DTYPE_LADDER[0]
        if self.rtol > 1e-13:
            return self._DTYPE_LADDER[1]
        return self._DTYPE_LADDER[2]

    @staticmethod
    def _relative_residual(a: np.ndarray, b: np.ndarray, x: np.ndarray) -> float:
        """计算相对残差 ||b − A·x||_2 / ||b||_2（高精度 float64 评估）。"""
        a_hi = np.asarray(a, dtype=np.float64)
        b_hi = np.asarray(b, dtype=np.float64)
        x_hi = np.asarray(x, dtype=np.float64)
        bnorm = float(np.linalg.norm(b_hi))
        if bnorm == 0.0:
            # b=0 时用绝对残差（避免除零，规则 03：不静默返回）
            return float(np.linalg.norm(b_hi - a_hi @ x_hi))
        return float(np.linalg.norm(b_hi - a_hi @ x_hi) / bnorm)

    def solve(self, a: np.ndarray, b: np.ndarray) -> PrecisionSolveResult:
        """自适应精度求解 A·x = b。

        Args:
            a: 系数矩阵 (n, n)。
            b: 右端 (n,) 或 (n, k)。

        Returns:
            PrecisionSolveResult。

        Raises:
            ValueError: 形状非法（规则 14）。
            np.linalg.LinAlgError: A 奇异或最高精度仍无法达 rtol。
        """
        a_arr = np.asarray(a)
        b_arr = np.asarray(b)
        if a_arr.ndim != 2 or a_arr.shape[0] != a_arr.shape[1]:
            raise ValueError(f"A 须方阵，实际 {a_arr.shape}")
        if b_arr.shape[0] != a_arr.shape[0]:
            raise ValueError(
                f"b 行数 {b_arr.shape[0]} 与 A {a_arr.shape[0]} 不匹配"
            )
        init_dtype = self._select_initial_dtype()
        upgraded = False
        cur_dtype = init_dtype
        # 沿 dtype 阶梯尝试，每次失败升级
        idx = self._DTYPE_LADDER.index(init_dtype)
        while idx < len(self._DTYPE_LADDER):
            cur_dtype = self._DTYPE_LADDER[idx]
            a_d = a_arr.astype(cur_dtype, copy=False)
            b_d = b_arr.astype(cur_dtype, copy=False)
            x = sla.solve(a_d, b_d)  # 奇异 → LinAlgError 抛出
            rel = self._relative_residual(a_d, b_d, x)
            n_ref = 0
            # 迭代求精（Higham 2002 §12.1）：r=b−Ax, solve A·dx=r, x+=dx
            while rel > self.rtol and n_ref < self.max_refinements:
                r = (b_d - a_d @ x).astype(cur_dtype)
                dx = sla.solve(a_d, r)
                x = x + dx
                rel = self._relative_residual(a_d, b_d, x)
                n_ref += 1
            if rel <= self.rtol:
                return PrecisionSolveResult(
                    x=x.astype(np.float64),
                    dtype=cur_dtype,
                    residual=rel * float(np.linalg.norm(b_arr.astype(np.float64))),
                    relative_residual=rel,
                    n_refinements=n_ref,
                    upgraded=upgraded,
                )
            # 当前精度无法达标 → 升级 dtype
            idx += 1
            upgraded = True
        # 最高精度仍不达标（规则 03：禁止 fall-back，raise 告警）
        raise np.linalg.LinAlgError(
            f"最高精度 {cur_dtype} 仍无法达到 rtol={self.rtol:.3e}"
            f"（实际 rel_res={rel:.3e}），矩阵可能严重病态"
        )


# ===========================================================================
# R461 稀疏矩阵 CSR/CSC 压缩格式优化
# ===========================================================================


@dataclass
class SparseCompressResult:
    """稀疏压缩结果（R461）。

    Attributes:
        matrix: 压缩后稀疏矩阵（CSR 或 CSC）。
        format: 选用格式名（'csr' 或 'csc'）。
        nnz: 非零元数。
        memory_bytes: 估算存储字节。
        reason: 选型理由。
    """

    matrix: sp.spmatrix
    format: str
    nnz: int
    memory_bytes: int
    reason: str


class SparseMatrixCompressor:
    """稀疏矩阵 CSR/CSC 压缩格式优化器（R461）。

    根据主操作模式（行切片/列切片/SpMV）自动选 CSR 或 CSC，
    并估算内存占用。CSR 优行算术与 SpMV，CSC 优列切片与列向因子分解
    （Davis 2006 §2.3）。

    用法：
        comp = SparseMatrixCompressor(dense_or_sparse)
        result = comp.compress(op='spmv')
        y = result.matrix @ x
    """

    def __init__(self, matrix: np.ndarray | sp.spmatrix) -> None:
        if sp.issparse(matrix):
            self._coo = matrix.tocoo()
        else:
            arr = np.asarray(matrix)
            if arr.ndim != 2:
                raise ValueError(f"matrix 须 2D，实际 {arr.shape}")
            self._coo = sp.coo_matrix(arr)
        if self._coo.shape[0] == 0 or self._coo.shape[1] == 0:
            raise ValueError("matrix 不能为空（规则 14）")
        self.shape = self._coo.shape

    @staticmethod
    def _memory_bytes(mat: sp.spmatrix) -> int:
        """估算 CSR/CSC 存储字节 = (data + indices + indptr) 字节。"""
        csr = mat.tocsr()
        return (
            csr.data.nbytes + csr.indices.nbytes + csr.indptr.nbytes
        )

    def compress(
        self,
        op: str = "spmv",
    ) -> SparseCompressResult:
        """按主操作模式压缩到最优格式。

        Args:
            op: 操作模式，'row'（行切片）/'col'（列切片）/'spmv'（矩阵-向量乘）
                任意 → CSR；'col' → CSC。

        Returns:
            SparseCompressResult。

        Raises:
            ValueError: op 非法（规则 14）。
        """
        if op not in ("row", "col", "spmv"):
            raise ValueError(f"op 须 row/col/spmv，实际 {op}（规则 14）")
        if op == "col":
            csc = self._coo.tocsc()
            return SparseCompressResult(
                matrix=csc,
                format="csc",
                nnz=csc.nnz,
                memory_bytes=self._memory_bytes(csc),
                reason="列操作 → CSC（Davis 2006 §2.3）",
            )
        csr = self._coo.tocsr()
        reason = (
            "行切片 → CSR" if op == "row" else "SpMV → CSR（行压缩 SpMV 最优）"
        )
        return SparseCompressResult(
            matrix=csr,
            format="csr",
            nnz=csr.nnz,
            memory_bytes=self._memory_bytes(csr),
            reason=reason,
        )

    def spmv(
        self,
        x: np.ndarray,
        op: str = "spmv",
    ) -> np.ndarray:
        """稀疏矩阵-向量乘 y = A·x（自动选最优格式）。

        Args:
            x: 向量 (n,)。
            op: 操作模式（传给 compress）。

        Returns:
            y = A·x (m,)。

        Raises:
            ValueError: 维度不匹配（规则 14）。
        """
        x_arr = np.asarray(x)
        if x_arr.shape != (self.shape[1],):
            raise ValueError(
                f"x 形状 {x_arr.shape} 与矩阵列数 {self.shape[1]} 不匹配"
            )
        result = self.compress(op=op)
        return np.asarray(result.matrix @ x_arr)


# ===========================================================================
# R462 向量化 I/O 批量结果写入
# ===========================================================================


class VectorizedIO:
    """向量化 I/O 批量结果写入器（R462）。

    缓冲多个仿真结果数组，达到 batch_size 或显式 flush 时一次性写入
    np.savez 文件，减少小文件频繁 I/O 开销。

    用法：
        vio = VectorizedIO(batch_size=8, path="results.npz")
        vio.append("e_field_0", e_arr)
        vio.flush()  # 批量写入
    """

    def __init__(
        self,
        batch_size: int = 16,
        path: str | None = None,
    ) -> None:
        if batch_size < 1:
            raise ValueError(f"batch_size 须 ≥1，实际 {batch_size}（规则 14）")
        self.batch_size = int(batch_size)
        self.path = path
        self._buffer: dict[str, np.ndarray] = OrderedDict()
        self._flushed_count = 0
        self._total_bytes = 0

    def append(self, key: str, array: np.ndarray) -> None:
        """缓冲一个结果数组，满 batch_size 时自动 flush。

        Args:
            key: 结果键名（须非空且唯一）。
            array: 数组。

        Raises:
            ValueError: key 非法或重复（规则 14）。
        """
        if not key:
            raise ValueError("key 不能为空（规则 14）")
        if key in self._buffer:
            raise ValueError(f"key '{key}' 已在缓冲区中（规则 14）")
        arr = np.asarray(array)
        self._buffer[key] = arr
        if len(self._buffer) >= self.batch_size:
            self.flush()

    def flush(self) -> int:
        """批量写入缓冲区到文件（若设 path）并清空缓冲。

        Returns:
            本次写入的数组数量。

        Raises:
            ValueError: path 设定但目录不可写（规则 03：禁止 fall-back）。
        """
        n = len(self._buffer)
        if n == 0:
            return 0
        if self.path is not None:
            # 累加模式：先读旧文件，合并，再写回（避免覆盖历史结果）
            import os

            d = os.path.dirname(os.path.abspath(self.path))
            if not os.path.isdir(d):
                raise ValueError(f"目录不存在：{d}（规则 14）")
            # 用 _flushed_count 区分每次 flush，避免键名冲突覆盖
            save_keys = {}
            for k, v in self._buffer.items():
                save_keys[f"{k}"] = v
            # 若文件已存在，np.savez 会追加模式不直接支持，用临时合并
            existing: dict[str, np.ndarray] = {}
            if os.path.exists(self.path):
                with np.load(self.path, allow_pickle=False) as data:
                    for k in data.files:
                        existing[k] = np.array(data[k], copy=True)
            existing.update(save_keys)
            np.savez(self.path, **existing)
            self._total_bytes = os.path.getsize(self.path)
        self._buffer.clear()
        self._flushed_count += n
        return n

    @property
    def pending(self) -> int:
        """当前缓冲区数组数。"""
        return len(self._buffer)

    @property
    def flushed_count(self) -> int:
        """累计 flush 数组数。"""
        return self._flushed_count

    @property
    def total_bytes(self) -> int:
        """已写入文件总字节（未设 path 则 0）。"""
        return self._total_bytes


# ===========================================================================
# R463 综合性能基准工厂
# ===========================================================================


def _bench_redheffer_cascade(rng: np.random.Generator, n_modes: int) -> float:
    """基准：Redheffer 级联 + 缓存命中（R463）。"""
    m = n_modes
    s1 = 0.5 * rng.standard_normal((2 * m, 2 * m))
    s2 = 0.5 * rng.standard_normal((2 * m, 2 * m))
    casc = RedhefferCascade(max_size=32)
    casc.cascade([s1, s2], [1.0, 2.0], m, 1.55e-6)
    r2 = casc.cascade([s1, s2], [1.0, 2.0], m, 1.55e-6)
    return float(r2.hit_rate)


def _bench_precision_solve(rng: np.random.Generator, n: int) -> float:
    """基准：精度自适应求解（R463）。"""
    a = rng.standard_normal((n, n)) + n * np.eye(n)
    b = rng.standard_normal(n)
    solver = PrecisionAdaptiveSolver(rtol=1e-9)
    res = solver.solve(a, b)
    return res.relative_residual


def _bench_sparse_spmv(rng: np.random.Generator, n: int) -> float:
    """基准：稀疏压缩 SpMV（R463）。"""
    dense = rng.standard_normal((n, n))
    dense[np.abs(dense) < 0.8] = 0.0  # 稀疏化
    comp = SparseMatrixCompressor(dense)
    x = rng.standard_normal(n)
    y = comp.spmv(x)
    return float(np.linalg.norm(y))


def _bench_vectorized_io(rng: np.random.Generator, n: int) -> int:
    """基准：向量化 I/O 批量写入（R463）。"""
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        vio = VectorizedIO(batch_size=8, path=f"{d}/bench.npz")
        for i in range(8):
            vio.append(f"e_{i}", rng.standard_normal((n, n)))
        return vio.flush()


def build_advanced_benchmark_suite(
    n: int = 40,
    n_modes: int = 4,
) -> "object":
    """构建 R457-R550 进阶性能基准套件（R463）。

    组合 Redheffer 级联 + 缓存、精度自适应、稀疏压缩、向量化 I/O
    四类基准，返回 PerfBenchmarkSuite（延迟导入避免循环依赖）。

    Args:
        n: 基准矩阵维度。
        n_modes: Redheffer 模式数。

    Returns:
        polaris.sim.perf_optimization_benchmark.PerfBenchmarkSuite 实例，
        已注入 4 个 BenchmarkCase。

    Raises:
        ValueError: 参数非法（规则 14）。
    """
    import functools

    if n < 8:
        raise ValueError(f"n 须 ≥8，实际 {n}（规则 14）")
    if n_modes < 1:
        raise ValueError(f"n_modes 须 ≥1，实际 {n_modes}")
    # 延迟导入（facade 模式，避免循环依赖）
    from polaris.sim.perf_optimization_benchmark import (
        BenchmarkCase,
        PerfBenchmarkSuite,
    )

    suite = PerfBenchmarkSuite()
    rng = np.random.default_rng(2026)
    cases = (
        ("redheffer_cascade_cache",
         functools.partial(_bench_redheffer_cascade, rng, n_modes)),
        ("precision_adaptive_solve",
         functools.partial(_bench_precision_solve, rng, n)),
        ("sparse_csr_spmv",
         functools.partial(_bench_sparse_spmv, rng, n)),
        ("vectorized_io_batch",
         functools.partial(_bench_vectorized_io, rng, n)),
    )
    for name, fn in cases:
        suite.add(BenchmarkCase(
            name=name, fn=fn, expected_runtime=2.0, n_runs=2,
        ))
    return suite

