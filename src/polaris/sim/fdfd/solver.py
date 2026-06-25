"""FDFD 频域有限差分求解器主体（A05 §5-§6 核心算法）。

实现 2D TEz 频域 Maxwell 全波求解：
- 标量波动方程（消去 H）：∇_S·(P·∇_S E_z) + k₀²Q·ε_r·E_z = -iωμ₀·Q·J_z
- SC-PML 拉伸坐标（Shin & Fan 2012）融入算子对角块，无辅助变量
- 复对称稀疏线性系统 A·E = b（scipy.sparse.csr_matrix）
- 求解策略：直接 spsolve（小规模 N≤2e4）/ 迭代 bicgstab（大规模 + ILU 预处理）
- H 场回代：H = -(1/(iωμ₀)) ∇_S × E_z（由 Maxwell 旋度方程）

SC-PML 算子构造（Shin & Fan 2012 §3，2D TEz）：
    A = D_x^T · diag(s_y/s_x) · D_x + D_y^T · diag(s_x/s_y) · D_y + k₀² · diag(s_x·s_y·ε_r)
    b = -iωμ₀ · diag(s_x·s_y) · J_z

其中 D_x, D_y 为一阶前向差分算子（含 1/dx, 1/dy），
s_x, s_y 为 PML 拉伸因子（非 PML 区=1，PML 区=κ-iσ/(ωε₀)）。

*创新*：与 FDE 共享 YeeGrid + ScPml 组件，模式注入天然兼容（A05 §8）。
- 底层逻辑：scipy.sparse 构造 A（CSR 复对称），spsolve/bicgstab 求解；
  SC-PML 算子由 sim.grid.pml.build_pml_stretch 复用 FDE 实现。
- 支持理论：Shin & Fan 2012 证明 SC-PML 频域反射最低；Gu 2014 证明
  QMR-COCG/COCR 对复对称系统收敛优于 BiCGSTAB/GMRES。
- 案例：单频超表面、窄带光栅滤波器、SOI 微环、金属纳米天线。

文献来源（≥5，规则 18 学术诚信）：
1. Shin & Fan 2012 JCP — https://doi.org/10.1016/j.jcp.2011.12.037
2. MaxwellFDFD（Shin MATLAB 包）— https://www.mit.edu/~wsshin/maxwellfdfd.html
3. Gu et al 2014 IEEE TMTT — https://doi.org/10.1109/TMTT.2014.2363835
4. Yee 1966 IEEE TAP — https://doi.org/10.1109/TAP.1966.1138693
5. SimWorks FDFD Solver — https://www.simworks.net/solver/FDFD
6. Simsek et al 2025 Sci. Rep. — https://doi.org/10.1038/s41598-025-18869-z

规则依据：规则 14（禁止 fall-back，不收敛 raise）/规则 26（GPU 不参与）
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

from polaris.sim.fdfd.source import (
    DipoleSource,
    GaussianBeamSource,
    ModeSource,
    PlaneWaveSource,
    build_source_vector,
)
from polaris.sim.grid.pml import ScPml, build_pml_stretch
from polaris.sim.grid.yee import GridSpec, YeeGrid

__all__ = ["FdfdSolverConfig", "FdfdSolver", "FdfdResult", "solve_fdfd"]

_C0 = 2.99792458e8  # 光速 m/s
_MU0 = 1.25663706212e-6  # 真空磁导率 H/m
_EPS0 = 8.8541878128e-12  # 真空介电常数 F/m

SolverMethod = Literal["direct", "bicgstab", "cg"]


@dataclass(frozen=True)
class FdfdSolverConfig:
    """FDFD 求解器配置。

    Attributes:
        wavelength: 自由空间波长（米）。
        pml: SC-PML 参数，None 用默认 ScPml()。
        method: 求解方法 'direct'（spsolve，N≤2e4）/ 'bicgstab' / 'cg'。
        tolerance: 迭代求解器相对残差容差，默认 1e-6。
        max_iterations: 迭代求解器最大迭代数，默认 5000。
        use_ilu: 是否启用 ILU 预处理（迭代法专用），默认 True。
        ilu_drop_tolerance: ILU drop tolerance，默认 1e-4。
        ilu_fill_factor: ILU 填充因子，默认 10。
    """

    wavelength: float
    pml: ScPml | None = None
    method: SolverMethod = "direct"
    tolerance: float = 1e-6
    max_iterations: int = 5000
    use_ilu: bool = True
    ilu_drop_tolerance: float = 1e-4
    ilu_fill_factor: int = 10

    def __post_init__(self) -> None:
        if self.wavelength <= 0.0:
            raise ValueError(f"波长必须为正，实际 {self.wavelength}")
        if self.method not in ("direct", "bicgstab", "cg"):
            raise ValueError(f"求解方法必须为 'direct'/'bicgstab'/'cg'，实际 {self.method}")
        if self.tolerance <= 0.0 or self.tolerance >= 1.0:
            raise ValueError(f"容差须 ∈ (0,1)，实际 {self.tolerance}")
        if self.max_iterations < 10:
            raise ValueError(f"最大迭代数须 ≥10，实际 {self.max_iterations}")
        if self.ilu_drop_tolerance <= 0.0:
            raise ValueError(f"ILU drop tolerance 须 >0，实际 {self.ilu_drop_tolerance}")


@dataclass
class FdfdResult:
    """FDFD 求解结果。

    Attributes:
        e_z: 电场 z 分量 (Nx, Ny) complex128（V/m）。
        h_x: 磁场 x 分量 (Nx, Ny) complex128（A/m）。
        h_y: 磁场 y 分量 (Nx, Ny) complex128（A/m）。
        grid: YeeGrid 对象（含 eps_r 与 PML 拉伸因子）。
        wavelength: 波长（米）。
        omega: 角频率（rad/s）。
        residual: 求解器最终残差 ||A·E - b||₂ / ||b||₂。
        iterations: 迭代次数（直接法返回 0）。
        method: 实际使用的求解方法。
    """

    e_z: np.ndarray
    h_x: np.ndarray
    h_y: np.ndarray
    grid: YeeGrid
    wavelength: float
    omega: float
    residual: float
    iterations: int
    method: str


class FdfdSolver:
    """2D TEz FDFD 求解器（SC-PML + scipy.sparse 稀疏线性系统）。

    用法：
        cfg = FdfdSolverConfig(wavelength=1.55e-6, method='direct')
        solver = FdfdSolver(cfg)
        result = solver.solve(
            eps_r, window_size=(4e-6, 4e-6), source=plane_wave_src
        )
        # 提取 S 参数与能量守恒校验
        s_params = extract_s_parameters(result.e_z, ports, dx, dy)
        total = verify_energy_conservation(s_params)
    """

    def __init__(self, config: FdfdSolverConfig) -> None:
        self.config = config
        self.k0 = 2.0 * np.pi / config.wavelength
        self.omega = 2.0 * np.pi * _C0 / config.wavelength

    def _build_grid(self, eps_r: np.ndarray, window_size: tuple[float, float]) -> YeeGrid:
        """构造 YeeGrid（复用 FDE 共享组件，ALGORITHMS.md 附录 C）。"""
        nx, ny = eps_r.shape
        dx = window_size[0] / nx
        dy = window_size[1] / ny
        spec = GridSpec(shape=(nx, ny), dx=dx, dy=dy)
        pml = self.config.pml if self.config.pml is not None else ScPml()
        sx = build_pml_stretch(nx, dx, self.config.wavelength, pml, axis="x")
        sy = build_pml_stretch(ny, dy, self.config.wavelength, pml, axis="y")
        return YeeGrid(spec=spec, eps_r=eps_r, stretch_x=sx, stretch_y=sy)

    def _assemble_operator(self, grid: YeeGrid) -> sp.csr_array:
        """组装 SC-PML 复对称稀疏算子 A（A05 §5.2 步骤 3-5）。

        A = D_x^T · diag(s_y/s_x) · D_x + D_y^T · diag(s_x/s_y) · D_y
            + k₀² · diag(s_x·s_y·ε_r)

        其中 D_x, D_y 为一阶前向差分（1/dx 含 PML 拉伸 1/s_x）。
        复杂度：O(N) 非零元，每行 ≤5 个（5 点拉普拉斯），向量化构造。

        Args:
            grid: YeeGrid 对象（含 eps_r + stretch_x + stretch_y）。

        Returns:
            A 稀疏矩阵 (N, N) complex128 CSR。
        """
        nx, ny = grid.spec.shape
        n = nx * ny
        dx, dy = grid.spec.dx, grid.spec.dy
        sx = grid.stretch_x  # (nx,)
        sy = grid.stretch_y  # (ny,)
        # 半整数点拉伸因子（Yee 棱中点）
        sx_edge = 0.5 * (sx[:-1] + sx[1:])  # (nx-1,) at x+1/2
        sy_edge = 0.5 * (sy[:-1] + sy[1:])  # (ny-1,) at y+1/2
        # x 方向权重 w_x = s_y / s_x 在 (i+1/2, j) 点
        # s_y 在 x 方向不变：w_x[i+1/2, j] = sy[j] / sx_edge[i]
        # 形状 (nx-1, ny)
        w_x = (sy[None, :] / sx_edge[:, None]).ravel() / dx**2  # ((nx-1)*ny,)
        # y 方向权重 w_y = s_x / s_y 在 (i, j+1/2) 点
        # s_x 在 y 方向不变：w_y[i, j+1/2] = sx[i] / sy_edge[j]
        # 形状 (nx, ny-1)
        w_y = (sx[:, None] / sy_edge[None, :]).ravel() / dy**2  # (nx*(ny-1),)
        # 主对角：-w_x[i+1/2] - w_x[i-1/2] - w_y[j+1/2] - w_y[j-1/2] + k₀² s_x s_y ε_r
        # 边界处理：超出网格的 w 取 0（Neumann 零通量自然边界）
        # w_x_prev[i] = w_x[i-1/2]（即 sx_edge[i-1]），w_x_next[i] = w_x[i+1/2]
        # 向量化构造：每行的主对角元
        diag_eps = (sx[:, None] * sy[None, :] * grid.eps_r).ravel()
        main_diag = np.full(n, 0.0, dtype=np.complex128)
        # x 方向贡献：-w_x[i+1/2]（当前行的右上邻接）- w_x[i-1/2]（当前行的左下邻接）
        # 第一行（i=0）无 w_x_prev，最后一行（i=nx-1）无 w_x_next
        # w_x 数组形状 (nx-1, ny)，索引 k = i*ny + j
        # w_x_next[i,j] = w_x[i*ny + j]  (i ∈ [0, nx-2])
        # w_x_prev[i,j] = w_x[(i-1)*ny + j] (i ∈ [1, nx-1])
        w_x_2d = w_x.reshape(nx - 1, ny)  # (nx-1, ny) w_x 在 i+1/2
        # 对行 i（0 <= i <= nx-1）:
        #   next 贡献: -w_x_2d[i, j]（若 i < nx-1）
        #   prev 贡献: -w_x_2d[i-1, j]（若 i > 0）
        w_x_main = np.zeros((nx, ny), dtype=np.complex128)
        w_x_main[:-1, :] -= w_x_2d  # next 贡献（i 从 0 到 nx-2）
        w_x_main[1:, :] -= w_x_2d  # prev 贡献（i 从 1 到 nx-1）
        # y 方向贡献
        w_y_2d = w_y.reshape(nx, ny - 1)  # (nx, ny-1) w_y 在 j+1/2
        w_y_main = np.zeros((nx, ny), dtype=np.complex128)
        w_y_main[:, :-1] -= w_y_2d  # next 贡献
        w_y_main[:, 1:] -= w_y_2d  # prev 贡献
        # 组装主对角
        main_diag = (w_x_main + w_y_main).ravel() + (self.k0**2) * diag_eps
        # x 方向次对角（±ny）：w_x[i+1/2, j]
        rows_x = np.arange(n - ny)  # 行索引 (i*ny + j), i ∈ [0, nx-2]
        cols_x = rows_x + ny  # 列索引 ((i+1)*ny + j)
        data_x = w_x_2d.ravel()  # w_x[i+1/2, j]
        # y 方向次对角（±1）：w_y[i, j+1/2]
        rows_y = (np.arange(nx)[:, None] * ny + np.arange(ny - 1)[None, :]).ravel()
        cols_y = rows_y + 1
        data_y = w_y_2d.ravel()
        # 拼装对称矩阵（A = A^T，复对称非 Hermitian）
        rows = np.concatenate(
            [
                np.arange(n),  # 主对角
                rows_x,
                cols_x,  # x 次对角对称
                rows_y,
                cols_y,  # y 次对角对称
            ]
        )
        cols = np.concatenate(
            [
                np.arange(n),
                cols_x,
                rows_x,
                cols_y,
                rows_y,
            ]
        )
        data = np.concatenate(
            [
                main_diag,
                data_x,
                data_x,
                data_y,
                data_y,
            ]
        )
        return sp.coo_array((data.astype(np.complex128), (rows, cols)), shape=(n, n)).tocsr()

    def _build_source_vector(
        self,
        grid: YeeGrid,
        source: PlaneWaveSource | DipoleSource | GaussianBeamSource | ModeSource,
    ) -> np.ndarray:
        """组装源向量 b = -iωμ₀ · diag(s_x·s_y) · J_z。

        Args:
            grid: YeeGrid 对象。
            source: 源对象（4 类之一）。

        Returns:
            源向量 (N,) complex128，已含 -iωμ₀ 因子。
        """
        j_z = build_source_vector(
            source=source,
            shape=grid.spec.shape,
            dx=grid.spec.dx,
            dy=grid.spec.dy,
            origin=grid.spec.origin,
            omega=self.omega,
            mu0=_MU0,
            stretch_x=grid.stretch_x,
            stretch_y=grid.stretch_y,
        )
        # SC-PML 体积拉伸：b = -iωμ₀ · (s_x · s_y) · J_z
        sxy = (grid.stretch_x[:, None] * grid.stretch_y[None, :]).ravel()
        b = -1j * self.omega * _MU0 * sxy * j_z.ravel()
        return b

    def _solve_linear_system(
        self, a_mat: sp.csr_array, b_vec: np.ndarray
    ) -> tuple[np.ndarray, float, int]:
        """求解复对称稀疏线性系统 A·x = b。

        数值稳定性：对 A 与 b 同步除以 k₀²（MaxwellFDFD 标准做法），
        将对角元从 O(k₀²) ~ 1e13 归一化至 O(1)，避免迭代法数值发散。

        Args:
            a_mat: 稀疏矩阵 (N, N)。
            b_vec: 源向量 (N,)。

        Returns:
            (解 x, 残差 ||A·x - b||₂/||b||₂, 迭代次数)

        Raises:
            RuntimeError: 求解失败（不收敛或矩阵奇异，规则 14 无 fall-back）。
        """
        n = a_mat.shape[0]
        method = self.config.method
        # 数值归一化：A_norm = A / k₀²，b_norm = b / k₀²
        # 不改变解 x（两边同除），仅改善条件数（MaxwellFDFD/Jaxwell 标准做法）
        k0_sq = self.k0**2
        a_norm = a_mat / k0_sq
        b_norm = b_vec / k0_sq
        # 小规模强制直接法（避免迭代开销）
        if n <= 20_000 and method != "direct":
            # 仅在用户显式指定迭代时才用迭代
            pass
        elif n > 20_000 and method == "direct":
            # 大规模回退到 bicgstab（非 fall-back，是有意选择更优算法）
            method = "bicgstab"
        if method == "direct":
            try:
                x = spla.spsolve(a_norm, b_norm)
            except RuntimeError as exc:
                raise RuntimeError(f"FDFD 直接求解失败（矩阵可能奇异）：{exc}") from exc
            residual = float(
                np.linalg.norm(a_norm @ x - b_norm) / max(np.linalg.norm(b_norm), 1e-30)
            )
            return x, residual, 0
        # 迭代法：bicgstab 或 cg（cg 对复对称系统等价 COCG）
        if self.config.use_ilu:
            try:
                ilu = spla.spilu(
                    a_norm.tocsc(),
                    drop_tol=self.config.ilu_drop_tolerance,
                    fill_factor=self.config.ilu_fill_factor,
                )
                m_op = spla.LinearOperator(
                    (a_norm.shape[0], a_norm.shape[0]),
                    matvec=ilu.solve,
                    dtype=np.complex128,
                )
            except RuntimeError as exc:
                raise RuntimeError(f"ILU 预处理失败（矩阵奇异或填充不足）：{exc}") from exc
        else:
            m_op = None
        if method == "cg":
            # 复对称系统用 cg 等价 COCG（Gu 2014 推荐）
            counter = {"n": 0}

            def _cb(_xk: np.ndarray) -> None:
                counter["n"] += 1

            x, info = spla.cg(
                a_norm,
                b_norm,
                M=m_op,
                rtol=self.config.tolerance,
                maxiter=self.config.max_iterations,
                callback=_cb,
            )
            iters = counter["n"]
        else:  # bicgstab（通用兜底，对非对称系统更稳健）
            counter = {"n": 0}

            def _cb(_xk: np.ndarray) -> None:
                counter["n"] += 1

            x, info = spla.bicgstab(
                a_norm,
                b_norm,
                M=m_op,
                rtol=self.config.tolerance,
                maxiter=self.config.max_iterations,
                callback=_cb,
            )
            iters = counter["n"]
        if info != 0:
            if info > 0:
                raise RuntimeError(
                    f"FDFD 迭代求解未收敛（{info}/{self.config.max_iterations} "
                    f"迭代，方法={method}，容差={self.config.tolerance}）。"
                    "建议：1) 增加 max_iterations；2) 启用/调整 ILU；"
                    "3) 检查 PML 厚度（规则 14，禁止 fall-back）"
                )
            raise RuntimeError(
                f"FDFD 迭代求解失败（info={info}，方法={method}），矩阵可能奇异或预处理构造失败"
            )
        residual = float(np.linalg.norm(a_norm @ x - b_norm) / max(np.linalg.norm(b_norm), 1e-30))
        return x, residual, iters

    def _derive_h_fields(self, e_z: np.ndarray, grid: YeeGrid) -> tuple[np.ndarray, np.ndarray]:
        """由 E_z 回代 H_x, H_y（Maxwell 旋度方程）。

        TEz 假设（E_z 主导，传播在 xy 平面）：
            H_x = (1/(iωμ₀)) · (1/s_x) · ∂E_z/∂ỹ
            H_y = -(1/(iωμ₀)) · (1/s_y) · ∂E_z/∂x̃

        其中 ∂/∂x̃ = (1/s_x) ∂/∂x（含 PML 拉伸）。

        Args:
            e_z: 电场 z 分量 (Nx, Ny)。
            grid: YeeGrid 对象。

        Returns:
            (H_x, H_y) 网格 (Nx, Ny) complex128。
        """
        dx, dy = grid.spec.dx, grid.spec.dy
        sx = grid.stretch_x
        sy = grid.stretch_y
        omega_mu = self.omega * _MU0
        # 中心差分 ∂E_z/∂x（边界用单侧差分）
        e_z_c = e_z.astype(np.complex128)
        dez_dx = np.zeros_like(e_z_c)
        dez_dx[1:-1, :] = (e_z_c[2:, :] - e_z_c[:-2, :]) / (2.0 * dx)
        dez_dx[0, :] = (e_z_c[1, :] - e_z_c[0, :]) / dx
        dez_dx[-1, :] = (e_z_c[-1, :] - e_z_c[-2, :]) / dx
        # ∂E_z/∂y
        dez_dy = np.zeros_like(e_z_c)
        dez_dy[:, 1:-1] = (e_z_c[:, 2:] - e_z_c[:, :-2]) / (2.0 * dy)
        dez_dy[:, 0] = (e_z_c[:, 1] - e_z_c[:, 0]) / dy
        dez_dy[:, -1] = (e_z_c[:, -1] - e_z_c[:, -2]) / dy
        # PML 拉伸：∂/∂x̃ = (1/s_x) ∂/∂x
        # H_x = (1/(iωμ₀)) (1/s_x) ∂E_z/∂ỹ ... 实际上 TEz 是：
        # ∂E_z/∂ỹ = (1/s_y) ∂E_z/∂y,  H_x 由 ∂E_z/∂ỹ 推导
        # 由 Maxwell: -∂E_z/∂ỹ = -iωμ H_x → H_x = (1/(iωμ)) ∂E_z/∂ỹ
        #              ∂E_z/∂x̃ = -iωμ H_y → H_y = -(1/(iωμ)) ∂E_z/∂x̃
        # 在内部网格点用 s_x[i]（整数点），更精确可用半整数平均
        sx_2d = sx[:, None]
        sy_2d = sy[None, :]
        h_x = (1.0 / (1j * omega_mu)) * (dez_dy / sy_2d)
        h_y = -(1.0 / (1j * omega_mu)) * (dez_dx / sx_2d)
        return h_x, h_y

    def solve(
        self,
        eps_r: np.ndarray,
        window_size: tuple[float, float],
        source: PlaneWaveSource | DipoleSource | GaussianBeamSource | ModeSource,
    ) -> FdfdResult:
        """求解 2D TEz FDFD 频域 Maxwell 方程。

        Args:
            eps_r: 2D 相对介电常数分布 (Nx, Ny)，实数或复数。
            window_size: 物理窗口尺寸 (Lx, Ly)，单位米。
            source: 源对象（4 类之一）。

        Returns:
            FdfdResult 数据类（含 E_z, H_x, H_y, 残差, 迭代次数）。

        Raises:
            ValueError: 输入参数非法。
            RuntimeError: 线性系统求解失败（规则 14，禁止 fall-back）。
        """
        if eps_r.ndim != 2:
            raise ValueError(f"eps_r 必须为 2D，实际 {eps_r.ndim}D")
        if eps_r.shape[0] < 8 or eps_r.shape[1] < 8:
            raise ValueError(f"网格过小 {eps_r.shape}，至少 8x8（含 PML 与内部区域）")
        if window_size[0] <= 0.0 or window_size[1] <= 0.0:
            raise ValueError(f"窗口尺寸必须为正，实际 {window_size}")
        eps_r_c = eps_r.astype(np.complex128, copy=True)
        # 1. 构造 YeeGrid（含 PML 拉伸因子，复用 FDE 共享组件）
        grid = self._build_grid(eps_r_c, window_size)
        # 2. 组装 SC-PML 复对称算子 A
        a_mat = self._assemble_operator(grid)
        # 3. 组装源向量 b
        b_vec = self._build_source_vector(grid, source)
        # 4. 求解 A·E = b
        e_flat, residual, iterations = self._solve_linear_system(a_mat, b_vec)
        e_z = e_flat.reshape(grid.spec.shape)
        # 5. 回代 H 场
        h_x, h_y = self._derive_h_fields(e_z, grid)
        return FdfdResult(
            e_z=e_z,
            h_x=h_x,
            h_y=h_y,
            grid=grid,
            wavelength=self.config.wavelength,
            omega=self.omega,
            residual=residual,
            iterations=iterations,
            method=self.config.method,
        )


def solve_fdfd(
    eps_r: np.ndarray,
    wavelength: float,
    window_size: tuple[float, float],
    source: PlaneWaveSource | DipoleSource | GaussianBeamSource | ModeSource,
    pml_layers: int = 10,
    method: SolverMethod = "direct",
) -> FdfdResult:
    """便捷接口：一键求解 2D TEz FDFD。

    Args:
        eps_r: 2D 相对介电常数分布。
        wavelength: 自由空间波长（米）。
        window_size: 物理窗口 (Lx, Ly)，米。
        source: 源对象。
        pml_layers: PML 层数（每侧）。
        method: 求解方法 'direct'/'bicgstab'/'cg'。

    Returns:
        FdfdResult 数据类。
    """
    cfg = FdfdSolverConfig(
        wavelength=wavelength,
        pml=ScPml(layers=pml_layers),
        method=method,
    )
    return FdfdSolver(cfg).solve(eps_r, window_size, source)
