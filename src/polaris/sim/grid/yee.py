"""Yee 网格共享组件（FDE/FDFD/2.5D-FDTD/FDTD 共用底座）。

按 A04-FDE 算法文档 §4.1 实现 Yee 1966 交错网格：
- 电场分量位于棱中点（E_x 在 (i+1/2, j, k), E_y 在 (i, j+1/2, k), ...）
- 磁场分量位于面中心（H_x 在 (i, j+1/2, k+1/2), ...）
- 该排列保证 Maxwell 旋度方程中心差分自然满足散度条件 ∇·D=0

文献来源（≥5，规则 R02 学术诚信）：
1. Yee K, "Numerical solution of initial boundary value problems
   involving Maxwell's equations in isotropic media," IEEE Trans.
   Antennas Propag. 14, 302-307 (1966) —
   https://doi.org/10.1109/TAP.1966.1138693
2. Taflove A, Hagness SC, "Computational Electrodynamics: The
   Finite-Difference Time-Domain Method," 3rd ed., Artech House (2005)
   — https://doi.org/10.1002/0471654507.erfme149
3. Taflove A, "Application of the finite-difference time-domain method
   to sinusoidal steady-state electromagnetic-penetration problems,"
   IEEE Trans. Electromagn. Compat. 22, 191-202 (1980) —
   https://doi.org/10.1109/TEMC.1980.303825
4. Weiland T, "A discretization method for the solution of Maxwell's
   equations for six-component fields," Electron. Commun. (AEÜ) 31,
   116-120 (1977) —
   https://elib-international.org/aeue/aufuehrung/archiv/1977/Heft_3/
5. Yu W, Chang A, "Yee-mesh-based finite difference eigenmode solver
   with PML absorbing boundary conditions," OSA Opt. Express (2004)
   — https://doi.org/10.1364/OPEX.12.003237
6. Shin W, Fan S, "Choice of the perfectly matched layer boundary
   condition for frequency-domain Maxwell's equations solvers,"
   J. Comput. Phys. 231, 3406-3431 (2012) —
   https://doi.org/10.1016/j.jcp.2012.01.013

规则依据：project_rules.md 规则 26（GPU 不参与，纯 CPU scipy.sparse）
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import scipy.sparse as sp

__all__ = ["YeeGrid", "GridSpec"]


@dataclass(frozen=True)
class GridSpec:
    """矩形 Yee 网格规格（2D 横截面，z 不变）。

    Attributes:
        shape: (Nx, Ny) 网格点数。
        dx: x 方向网格间距（米）。
        dy: y 方向网格间距（米）。
        origin: 网格原点 (x0, y0)，单位米。
    """

    shape: tuple[int, int]
    dx: float
    dy: float
    origin: tuple[float, float] = (0.0, 0.0)

    def __post_init__(self) -> None:
        if len(self.shape) != 2:
            raise ValueError(f"GridSpec.shape 必须为 2D，实际为 {len(self.shape)}D")
        if self.shape[0] < 3 or self.shape[1] < 3:
            raise ValueError(f"网格点数过小 ({self.shape})，至少 3x3")
        if self.dx <= 0.0 or self.dy <= 0.0:
            raise ValueError(f"网格间距必须为正，实际 dx={self.dx}, dy={self.dy}")

    @property
    def num_cells(self) -> int:
        """总网格点数 Nx*Ny。"""
        return self.shape[0] * self.shape[1]

    @property
    def extent(self) -> tuple[float, float]:
        """物理窗口尺寸 (Lx, Ly)，单位米。"""
        nx, ny = self.shape
        return (nx * self.dx, ny * self.dy)

    def x_coords(self) -> np.ndarray:
        """x 方向网格坐标（米），含原点偏移。"""
        return self.origin[0] + np.arange(self.shape[0]) * self.dx

    def y_coords(self) -> np.ndarray:
        """y 方向网格坐标（米），含原点偏移。"""
        return self.origin[1] + np.arange(self.shape[1]) * self.dy


@dataclass
class YeeGrid:
    """2D Yee 网格（z 不变截面），FDE/FDFD/2.5D-FDTD 共享。

    电场主网格点位于 (i, j)，磁场交错位于半整数点。
    本类提供一阶/二阶差分算子构造（scipy.sparse CSR），含可选 PML 复坐标拉伸。

    Attributes:
        spec: 网格规格 GridSpec。
        eps_r: 相对介电常数分布 (Nx, Ny)，复数（支持损耗）。
        stretch_x: x 方向 PML 复坐标拉伸因子 (Nx,)，无 PML 区域为 1.0。
        stretch_y: y 方向 PML 复坐标拉伸因子 (Ny,)，无 PML 区域为 1.0。
    """

    spec: GridSpec
    eps_r: np.ndarray
    stretch_x: np.ndarray | None = None
    stretch_y: np.ndarray | None = None

    def __post_init__(self) -> None:
        if self.eps_r.shape != self.spec.shape:
            raise ValueError(
                f"eps_r 形状 {self.eps_r.shape} 与网格规格 {self.spec.shape} 不匹配"
            )
        if self.eps_r.dtype != np.complex128:
            self.eps_r = self.eps_r.astype(np.complex128)
        nx, ny = self.spec.shape
        if self.stretch_x is None:
            self.stretch_x = np.ones(nx, dtype=np.complex128)
        if self.stretch_y is None:
            self.stretch_y = np.ones(ny, dtype=np.complex128)
        if len(self.stretch_x) != nx:
            raise ValueError(f"stretch_x 长度 {len(self.stretch_x)} != Nx {nx}")
        if len(self.stretch_y) != ny:
            raise ValueError(f"stretch_y 长度 {len(self.stretch_y)} != Ny {ny}")

    @property
    def k0_inv_eps(self) -> sp.csr_array:
        """1/ε_r 的对角稀疏矩阵（共形网格未启用时为简单对角）。

        复杂度：O(N) 构造，O(1) 矩阵向量乘。
        """
        return sp.diags(1.0 / self.eps_r.flatten(), format="csr")

    def first_diff_x(self) -> sp.csr_array:
        """x 方向一阶前向差分算子 D_x（含 PML 拉伸）。

        D_x[i,j] = (δ_{i+1,j} - δ_{i,j}) / (s_x * dx)

        其中 s_x 为 PML 复坐标拉伸因子（界面取平均）。
        复杂度：O(N) 非零元（每行 2 个），CSR 格式。
        边界处理：末行用后向差分（Neumann 零通量）。
        """
        nx, ny = self.spec.shape
        n = nx * ny
        dx = self.spec.dx
        sx = self.stretch_x
        # 界面拉伸因子取相邻平均值（Yee 半整数点）
        sx_edge = 0.5 * (sx[:-1] + sx[1:])  # (nx-1,) 边的拉伸
        inv_dx_eff = 1.0 / (sx_edge * dx)  # (nx-1,)
        # 行索引：前 (n-ny) 行有前向差分，末 ny 行用后向差分
        row_fwd = np.arange(n - ny)
        col_fwd = row_fwd + ny
        row_bwd = np.arange(n - ny, n)
        col_bwd = row_bwd - ny
        # 重复 ny 次的 inv_dx_eff（沿 y 方向不变）
        data_fwd = np.repeat(inv_dx_eff, ny)
        data_bwd = -np.repeat(sx_edge[-1:] if len(sx_edge) > 0 else np.array([1.0 / dx]), ny)
        # 构造 COO 再转 CSR
        rows = np.concatenate([row_fwd, row_fwd, row_bwd, row_bwd])
        cols = np.concatenate([row_fwd, col_fwd, row_bwd, col_bwd])
        data = np.concatenate([-data_fwd, data_fwd, -data_bwd, data_bwd])
        return sp.coo_array((data, (rows, cols)), shape=(n, n)).tocsr()

    def first_diff_y(self) -> sp.csr_array:
        """y 方向一阶前向差分算子 D_y（含 PML 拉伸）。

        D_y[i,j] = (δ_{i,j+1} - δ_{i,j}) / (s_y * dy)
        边界处理：每行末列用后向差分（Neumann 零通量）。
        复杂度：O(N) 非零元，向量化构造（无 Python 循环）。
        """
        nx, ny = self.spec.shape
        n = nx * ny
        dy = self.spec.dy
        sy = self.stretch_y
        sy_edge = 0.5 * (sy[:-1] + sy[1:])  # (ny-1,)
        inv_dy_eff = 1.0 / (sy_edge * dy)  # (ny-1,)
        # 向量化：每个 x 行的前 ny-1 个前向差分点
        # 行索引：base + arange(ny-1)，base = ix*ny
        row_fwd = (np.arange(nx)[:, None] * ny + np.arange(ny - 1)[None, :]).ravel()
        col_fwd = row_fwd + 1
        data_fwd = np.tile(inv_dy_eff, nx)  # (nx*(ny-1),)
        # 后向：每行末列
        row_bwd = (np.arange(nx) + 1) * ny - 1
        col_bwd = row_bwd - 1
        data_bwd = -np.full(nx, inv_dy_eff[-1] if len(inv_dy_eff) > 0 else -1.0 / dy)
        rows = np.concatenate([row_fwd, row_fwd, row_bwd, row_bwd])
        cols = np.concatenate([row_fwd, col_fwd, row_bwd, col_bwd])
        data = np.concatenate([-data_fwd, data_fwd, -data_bwd, data_bwd])
        return sp.coo_array((data, (rows, cols)), shape=(n, n)).tocsr()

    def field_at(self, field: np.ndarray, ix: int, iy: int) -> complex:
        """读取场值（带边界保护，规则 14 禁止 fall-back，越界即 raise）。"""
        nx, ny = self.spec.shape
        if not (0 <= ix < nx and 0 <= iy < ny):
            raise IndexError(f"网格索引越界 ({ix},{iy})，网格形状 {self.spec.shape}")
        return complex(field[ix, iy])

    def __repr__(self) -> str:
        return (
            f"YeeGrid(shape={self.spec.shape}, dx={self.spec.dx:.3e}m, "
            f"dy={self.spec.dy:.3e}m, eps_max={np.abs(self.eps_r).max():.4f})"
        )
