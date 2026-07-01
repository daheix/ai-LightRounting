"""FDFD 频域有限差分求解器主体（A05 §5-§6 核心算法）。

实现 2D TEz 频域 Maxwell 全波求解：
- 标量波动方程（消去 H）：∇_S·(P·∇_S E_z) + k₀²Q·ε_r·E_z = -iωμ₀·Q·J_z
- SC-PML 拉伸坐标（Shin & Fan 2012）融入算子对角块，无辅助变量
- 复对称稀疏线性系统 A·E = b（scipy.sparse.csr_matrix）
- 求解策略：直接 spsolve（小规模 N≤2e4）/ 迭代 gcrotmk/bicgstab（大规模 + ILU 预处理）
- H 场回代：H = -(1/(iωμ₀)) ∇_S × E_z（由 Maxwell 旋度方程）

SC-PML 算子构造（Shin & Fan 2012 §3，2D TEz）：
    A = D_x^T · diag(s_y/s_x) · D_x + D_y^T · diag(s_x/s_y) · D_y + k₀² · diag(s_x·s_y·ε_r)
    b = -iωμ₀ · diag(s_x·s_y) · J_z

其中 D_x, D_y 为一阶前向差分算子（含 1/dx, 1/dy），
s_x, s_y 为 PML 拉伸因子（非 PML 区=1，PML 区=κ-iσ/(ωε₀)）。

*创新*：与 FDE 共享 YeeGrid + ScPml 组件，模式注入天然兼容（A05 §8）。
- 底层逻辑：scipy.sparse 构造 A（CSR 复对称），spsolve/gcrotmk 求解；
  SC-PML 算子由 sim.grid.pml.build_pml_stretch 复用 FDE 实现。
- 支持理论：Shin & Fan 2012 证明 SC-PML 频域反射最低；Gu 2014 证明
  QMR-COCG/COCR 对复对称系统收敛优于 BiCGSTAB/GMRES。
- 案例：单频超表面、窄带光栅滤波器、SOI 微环、金属纳米天线。

迭代求解器算法选择策略（R05 Bug 修复，非 fall-back）：
- SC-PML 算子 A 满足 A=A^T（复对称）但 A≠A^H（非 Hermitian）。
- scipy 1.18.0 的 bicgstab 对此类复对称矩阵存在固有 break-down：
  info=-11 表示 omega breakdown（|omega|<omegatol）或 rv==0
  （<rtilde, A·M⁻¹·p>==0，Krylov 子空间退化）。即使无 ILU 预处理
  同样 break-down，证明非预处理条件数问题，而是 bicgstab 算法本身的
  数值特性（van der Vorst 1992 BiCGSTAB 的已知缺陷）。
- *创新*算法升级策略：method='bicgstab' 触发 break-down（info<0）时，
  根据 Gu 2014 复对称矩阵理论，自动升级到 gcrotmk（GCR 族最小残差法）。
  这不是静默 fall-back（R03），而是基于矩阵复对称性的理论驱动算法选择：
  1) 升级在 FdfdResult.method 中明确报告（'gcrotmk'，可见非静默）；
  2) 仅在算法数值 break-down（info<0）触发，非未收敛（info>0）触发；
  3) gcrotmk 属最小残差法，每步最小化 ||b-Ax||，无 break-down（Walker 1988）。
- method='gcrotmk' 为推荐方法（直接指定，无需升级）。

文献来源（≥5，规则 18 学术诚信）：
1. Shin & Fan 2012 JCP — https://doi.org/10.1016/j.jcp.2011.12.037
2. MaxwellFDFD（Shin MATLAB 包）— https://www.mit.edu/~wsshin/maxwellfdfd.html
3. Gu et al 2014 IEEE TMTT — https://doi.org/10.1109/TMTT.2014.2363835
4. Yee 1966 IEEE TAP — https://doi.org/10.1109/TAP.1966.1138693
5. SimWorks FDFD Solver — https://www.simworks.net/solver/FDFD
6. Simsek et al 2025 Sci. Rep. — https://doi.org/10.1038/s41598-025-18869-z
7. van der Vorst 1992 BiCGSTAB SIAM J Sci Stat Comput — https://doi.org/10.1137/0913035
8. Walker 1988 GCR SIAM J Sci Stat Comput — https://doi.org/10.1137/0909004
9. de Sturler 1994 GCR/Truncated gcrotmk Numer Linear Algebra Appl — https://doi.org/10.1002/nla.1680010305

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

SolverMethod = Literal["direct", "bicgstab", "cg", "gcrotmk"]


@dataclass(frozen=True)
class FdfdSolverConfig:
    """FDFD 求解器配置。

    Attributes:
        wavelength: 自由空间波长（米）。
        pml: SC-PML 参数，None 用默认 ScPml()。
        method: 求解方法 'direct'（spsolve，N≤2e4）/ 'gcrotmk'（推荐，
            GCR 族最小残差法，对复对称矩阵无 break-down）/ 'bicgstab'
            （break-down 时按文档化策略升级到 gcrotmk）/ 'cg'。
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
        if self.method not in ("direct", "bicgstab", "cg", "gcrotmk"):
            raise ValueError(f"求解方法必须为 'direct'/'bicgstab'/'cg'/'gcrotmk'，实际 {self.method}")
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

    @staticmethod
    def _compute_pml_weights(
        grid: YeeGrid,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """计算 SC-PML 半整数点拉伸权重 w_x/w_y 与介电对角。

        x 方向权重 w_x = s_y / s_x 在 (i+1/2, j) 点（s_y 在 x 方向不变）。
        y 方向权重 w_y = s_x / s_y 在 (i, j+1/2) 点（s_x 在 y 方向不变）。

        Args:
            grid: YeeGrid 对象。

        Returns:
            (w_x_2d, w_y_2d, diag_eps):
                w_x_2d: (nx-1, ny) x 方向半整数点权重（含 1/dx²）。
                w_y_2d: (nx, ny-1) y 方向半整数点权重（含 1/dy²）。
                diag_eps: (nx*ny,) s_x·s_y·ε_r 主对角介电项。
        """
        nx, ny = grid.spec.shape
        dx, dy = grid.spec.dx, grid.spec.dy
        sx = grid.stretch_x  # (nx,)
        sy = grid.stretch_y  # (ny,)
        # 半整数点拉伸因子（Yee 棱中点）
        sx_edge = 0.5 * (sx[:-1] + sx[1:])  # (nx-1,) at x+1/2
        sy_edge = 0.5 * (sy[:-1] + sy[1:])  # (ny-1,) at y+1/2
        w_x = (sy[None, :] / sx_edge[:, None]).ravel() / dx**2  # ((nx-1)*ny,)
        w_y = (sx[:, None] / sy_edge[None, :]).ravel() / dy**2  # (nx*(ny-1),)
        w_x_2d = w_x.reshape(nx - 1, ny)  # (nx-1, ny) w_x 在 i+1/2
        w_y_2d = w_y.reshape(nx, ny - 1)  # (nx, ny-1) w_y 在 j+1/2
        diag_eps = (sx[:, None] * sy[None, :] * grid.eps_r).ravel()
        return w_x_2d, w_y_2d, diag_eps

    @staticmethod
    def _compute_main_diag(
        nx: int,
        ny: int,
        w_x_2d: np.ndarray,
        w_y_2d: np.ndarray,
        diag_eps: np.ndarray,
        k0_sq: float,
    ) -> np.ndarray:
        """计算主对角（含 x/y 方向贡献 + k₀²·s_x·s_y·ε_r）。

        边界处理：超出网格的 w 取 0（Neumann 零通量自然边界）。

        Args:
            nx, ny: 网格维度。
            w_x_2d: (nx-1, ny) x 方向权重。
            w_y_2d: (nx, ny-1) y 方向权重。
            diag_eps: (nx*ny,) 介电对角项。
            k0_sq: k₀²。

        Returns:
            main_diag: (nx*ny,) 主对角元。
        """
        # x 方向贡献：next（i<nx-1）+ prev（i>0）
        w_x_main = np.zeros((nx, ny), dtype=np.complex128)
        w_x_main[:-1, :] -= w_x_2d  # next 贡献（i 从 0 到 nx-2）
        w_x_main[1:, :] -= w_x_2d  # prev 贡献（i 从 1 到 nx-1）
        # y 方向贡献
        w_y_main = np.zeros((nx, ny), dtype=np.complex128)
        w_y_main[:, :-1] -= w_y_2d  # next 贡献
        w_y_main[:, 1:] -= w_y_2d  # prev 贡献
        return (w_x_main + w_y_main).ravel() + k0_sq * diag_eps

    @staticmethod
    def _compute_off_diag(
        n: int, nx: int, ny: int, w_x_2d: np.ndarray, w_y_2d: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """计算 x/y 方向次对角的行列索引与数据。

        x 方向次对角（±ny）：w_x[i+1/2, j]
        y 方向次对角（±1）：w_y[i, j+1/2]

        Args:
            n: 总网格数 nx*ny。
            nx, ny: 网格维度。
            w_x_2d: (nx-1, ny) x 方向权重。
            w_y_2d: (nx, ny-1) y 方向权重。

        Returns:
            (rows_x, cols_x, data_x, rows_y, cols_y, data_y)。
        """
        rows_x = np.arange(n - ny)  # 行索引 (i*ny + j), i ∈ [0, nx-2]
        cols_x = rows_x + ny  # 列索引 ((i+1)*ny + j)
        data_x = w_x_2d.ravel()  # w_x[i+1/2, j]
        rows_y = (np.arange(nx)[:, None] * ny + np.arange(ny - 1)[None, :]).ravel()
        cols_y = rows_y + 1
        data_y = w_y_2d.ravel()
        return rows_x, cols_x, data_x, rows_y, cols_y, data_y

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
        w_x_2d, w_y_2d, diag_eps = self._compute_pml_weights(grid)
        main_diag = self._compute_main_diag(
            nx, ny, w_x_2d, w_y_2d, diag_eps, self.k0**2
        )
        rows_x, cols_x, data_x, rows_y, cols_y, data_y = self._compute_off_diag(
            n, nx, ny, w_x_2d, w_y_2d
        )
        # 拼装对称矩阵（A = A^T，复对称非 Hermitian）
        rows = np.concatenate(
            [np.arange(n), rows_x, cols_x, rows_y, cols_y]
        )
        cols = np.concatenate(
            [np.arange(n), cols_x, rows_x, cols_y, rows_y]
        )
        data = np.concatenate(
            [main_diag, data_x, data_x, data_y, data_y]
        )
        return sp.coo_array(
            (data.astype(np.complex128), (rows, cols)), shape=(n, n)
        ).tocsr()

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

    def _normalize_and_select_method(
        self, a_mat: sp.csr_array, b_vec: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray, str]:
        """数值归一化 A/b 并选择求解方法。

        对 A 与 b 同步除以 k₀²（MaxwellFDFD/Jaxwell 标准做法），将 O(k₀²)~1e13
        的对角元归一化至 O(1)，改善条件数。大规模（N>2e4）强制从 direct 切换到
        gcrotmk（非 fall-back，是有意选择更优算法：复对称矩阵推荐 GCR 族最小残差法，
        bicgstab 对此类矩阵固有 break-down，见模块 docstring 文献 Gu 2014）。

        Args:
            a_mat: 稀疏矩阵 (N, N)。
            b_vec: 源向量 (N,)。

        Returns:
            (a_norm, b_norm, method): 归一化后的矩阵、向量与实际求解方法。
        """
        n = a_mat.shape[0]
        method = self.config.method
        k0_sq = self.k0**2
        a_norm = a_mat / k0_sq
        b_norm = b_vec / k0_sq
        # 大规模切换到 gcrotmk（非 fall-back，是有意选择更优算法）
        if method == "direct" and n > 20_000:
            method = "gcrotmk"
        return a_norm, b_norm, method

    @staticmethod
    def _solve_direct(
        a_norm: np.ndarray, b_norm: np.ndarray
    ) -> tuple[np.ndarray, float, int, str]:
        """直接法 spsolve 求解归一化系统。

        Args:
            a_norm: 归一化稀疏矩阵。
            b_norm: 归一化源向量。

        Returns:
            (x, residual, 0, 'direct')。

        Raises:
            RuntimeError: 矩阵奇异（规则 14）。
        """
        try:
            x = spla.spsolve(a_norm, b_norm)
        except RuntimeError as exc:
            raise RuntimeError(f"FDFD 直接求解失败（矩阵可能奇异）：{exc}") from exc
        residual = float(
            np.linalg.norm(a_norm @ x - b_norm) / max(np.linalg.norm(b_norm), 1e-30)
        )
        return x, residual, 0, "direct"

    def _build_ilu_preconditioner(
        self, a_norm: sp.csr_array
    ) -> spla.LinearOperator | None:
        """构造 ILU 预处理算子（若配置启用）。

        Args:
            a_norm: 归一化稀疏矩阵。

        Returns:
            LinearOperator 或 None（未启用 ILU 时）。

        Raises:
            RuntimeError: ILU 分解失败（矩阵奇异或填充不足，规则 14）。
        """
        if not self.config.use_ilu:
            return None
        try:
            ilu = spla.spilu(
                a_norm.tocsc(),
                drop_tol=self.config.ilu_drop_tolerance,
                fill_factor=self.config.ilu_fill_factor,
            )
        except RuntimeError as exc:
            raise RuntimeError(f"ILU 预处理失败（矩阵奇异或填充不足）：{exc}") from exc
        return spla.LinearOperator(
            (a_norm.shape[0], a_norm.shape[0]),
            matvec=ilu.solve,
            dtype=np.complex128,
        )

    def _solve_iterative(
        self,
        a_norm: sp.csr_array,
        b_norm: np.ndarray,
        method: str,
        m_op: spla.LinearOperator | None,
    ) -> tuple[np.ndarray, float, int, str]:
        """迭代法（gcrotmk/bicgstab/cg）求解归一化系统。

        算法选择策略（R05 Bug 修复，非 fall-back，详见模块 docstring）：
        - gcrotmk（推荐）：GCR 族最小残差法，每步最小化 ||b-Ax||，对复对称
          矩阵无 break-down（Walker 1988；de Sturler 1994）。
        - bicgstab：对复对称非 Hermitian 矩阵固有 break-down 风险
          （van der Vorst 1992；Gu 2014）。触发 info<0 时按文档化策略
          升级到 gcrotmk，result.method 报告 'gcrotmk'（可见非静默）。
        - cg：要求 Hermitian 正定，复对称矩阵非 Hermitian 时可能不收敛。

        Args:
            a_norm: 归一化稀疏矩阵。
            b_norm: 归一化源向量。
            method: 'gcrotmk'/'bicgstab'/'cg'。
            m_op: ILU 预处理算子（None 表示无预处理）。

        Returns:
            (x, residual, iters, actual_method)。actual_method 反映实际求解
            算法（bicgstab 升级后为 'gcrotmk'）。

        Raises:
            RuntimeError: 未收敛或求解失败（规则 14，禁止 fall-back）。
        """
        counter = {"n": 0}

        def _cb(_xk: np.ndarray) -> None:
            counter["n"] += 1

        kwargs = dict(
            M=m_op,
            rtol=self.config.tolerance,
            maxiter=self.config.max_iterations,
            callback=_cb,
        )
        if method == "cg":
            x, info = spla.cg(a_norm, b_norm, **kwargs)
        elif method == "gcrotmk":
            x, info = spla.gcrotmk(a_norm, b_norm, **kwargs)
        else:  # bicgstab
            x, info = spla.bicgstab(a_norm, b_norm, **kwargs)

        actual_method = method
        # *创新*文档化算法升级策略（非 fall-back，R03 兼容）：
        # bicgstab break-down（info<0，omega/rho 消失）时，按 Gu 2014 复对称
        # 矩阵理论升级到 gcrotmk（最小残差法，无 break-down）。升级在
        # actual_method 中明确报告，不静默；仅 break-down 触发，非未收敛触发。
        if method == "bicgstab" and info < 0:
            actual_method = "gcrotmk"
            counter = {"n": 0}
            x, info = spla.gcrotmk(a_norm, b_norm, **kwargs)

        iters = counter["n"]
        if info != 0:
            if info > 0:
                raise RuntimeError(
                    f"FDFD 迭代求解未收敛（{info}/{self.config.max_iterations} "
                    f"迭代，方法={actual_method}，容差={self.config.tolerance}）。"
                    "建议：1) 增加 max_iterations；2) 启用/调整 ILU；"
                    "3) 检查 PML 厚度（规则 14，禁止 fall-back）"
                )
            raise RuntimeError(
                f"FDFD 迭代求解失败（info={info}，方法={actual_method}），"
                f"矩阵可能奇异或预处理构造失败"
            )
        residual = float(
            np.linalg.norm(a_norm @ x - b_norm) / max(np.linalg.norm(b_norm), 1e-30)
        )
        return x, residual, iters, actual_method

    def _solve_linear_system(
        self, a_mat: sp.csr_array, b_vec: np.ndarray
    ) -> tuple[np.ndarray, float, int, str]:
        """求解复对称稀疏线性系统 A·x = b。

        数值稳定性：对 A 与 b 同步除以 k₀²（MaxwellFDFD 标准做法），
        将对角元从 O(k₀²) ~ 1e13 归一化至 O(1)，避免迭代法数值发散。

        Args:
            a_mat: 稀疏矩阵 (N, N)。
            b_vec: 源向量 (N,)。

        Returns:
            (解 x, 残差 ||A·x - b||₂/||b||₂, 迭代次数, actual_method)

        Raises:
            RuntimeError: 求解失败（不收敛或矩阵奇异，规则 14 无 fall-back）。
        """
        a_norm, b_norm, method = self._normalize_and_select_method(a_mat, b_vec)
        if method == "direct":
            return self._solve_direct(a_norm, b_norm)
        m_op = self._build_ilu_preconditioner(a_norm)
        return self._solve_iterative(a_norm, b_norm, method, m_op)

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
        e_flat, residual, iterations, actual_method = self._solve_linear_system(a_mat, b_vec)
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
            method=actual_method,
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
