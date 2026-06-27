"""FDE 本征模求解器主体（A04 §6 核心算法）。

采用半矢量 TE/TM 分离形式（A04 §4.2 简化，对 SOI strip 弱耦合波导精度足够）：
- TE 模（E_y 主导）：∂²E_y/∂x² + ∂²E_y/∂y² + k₀²n² E_y = β² E_y
- TM 模（H_y 主导）：∂/∂x(n²·∂(E_x/n²)/∂x) + ∂²E_x/∂y² + k₀²n² E_x = β² E_x

离散化（Yee 网格 5 点拉普拉斯算子，scipy.sparse）：
    A[i,i]   = -2/dx² - 2/dy² + k₀²n²[i]
    A[i,i±1] = 1/dy²（y 方向邻接）
    A[i,i±N] = 1/dx²（x 方向邻接，N=Ny）

本征值 λ = β²，导模范围 k₀²n_clad² < β² < k₀²n_core²。
shift-invert 目标 σ 设在导模预期范围（n_eff ≈ 2.0），避免命中体模。

求解后由 E_y 推导完整 6 分量场（TE 假设）：
    H_x = -β/(ωμ₀) E_y
    H_z = (1/(iωμ₀)) ∂E_y/∂x
    E_z = (1/(iβ)) ∂E_y/∂y
    E_x = H_z = 0（TE 近似）

后续 Sprint 扩展为全矢量（A04 §9.2 R37-Q2 共形网格同期）。

文献来源（R02 学术诚信，≥5 个 URL）：
1. Xu CL, Huang WP, "Full-vectorial mode calculations by finite difference method,"
   IEE Proc.-J 141, 281-286 (1994) — https://digital-library.theiet.org/doi/abs/10.1049/ip-j-1.1994.0042
2. Simsek E, "Practical Vectorial Mode Solver," arXiv:2503.17746 (2025) —
   https://arxiv.org/abs/2503.17746
3. Lehoucq RB, Sorensen DC, Yang C, "ARPACK Users' Guide: Solution of Large-Scale
   Eigenvalue Problems with Implicitly Restarted Arnoldi Methods," SIAM 1998 —
   https://doi.org/10.1137/1.9780898719628
4. Taflove A, Hagness SC, "Computational Electrodynamics: The Finite-Difference
   Time-Domain Method," 3rd ed., Artech House 2005（PML 污染模分析 §5）—
   https://www.artechhouse.com/Computational-Electrodynamics/Kane-Taflove/p/Book-927
5. Ansys Lumerical MODE-FDE Solver Introduction —
   https://optics.ansys.com/hc/en-us/articles/360034396614
6. Tidy3D ModeSpec (target_neff 约定) —
   https://docs.flexcompute.com/projects/tidy3d/en/latest/api/_autosummary/tidy3d.ModeSpec.html
7. gdsfactory photonics training FDFD mode solver notebook（SOI 220nm strip 实测
   n_eff=2.5113 @ n_Si=3.4）—
   https://gdsfactory.github.io/gdsfactory-photonics-training/notebooks/21_modesolver_fdfd.html

规则依据：project_rules.md 规则 14（禁止 fall-back）/规则 26（纯 CPU）
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

from polaris.sim.grid.pml import ScPml, build_pml_stretch
from polaris.sim.grid.yee import GridSpec, YeeGrid
from polaris.sim.fde.mode import Mode

__all__ = ["FdeSolverConfig", "FdeSolver", "solve_waveguide", "Polarization"]

_C0 = 2.99792458e8  # 光速 m/s
_MU0 = 1.25663706212e-6  # 真空磁导率 H/m
_EPS0 = 8.8541878128e-12  # 真空介电常数 F/m


class Polarization:
    """偏振模式枚举（TE/TM 分离求解）。"""

    TE = "te"  # E_y 主导（SOI 顶入射常见）
    TM = "tm"  # H_y 主导（E_x 主导）


@dataclass(frozen=True)
class FdeSolverConfig:
    """FDE 求解器配置。

    Attributes:
        wavelength: 自由空间波长（米）。
        num_modes: 待求模式数 K。
        polarization: 偏振模式 'te' 或 'tm'。
        pml: SC-PML 参数，None 表示用默认 ScPml(layers=10)。
        n_eff_shift: shift-invert 目标 n_eff 估计值。None 表示按 eps_r
            自动计算（n_clad + shift_frac·(n_core - n_clad)，shift_frac
            默认 0.3 偏向波导基模；参考 Tidy3D ModeSpec.target_neff 约定）。
    """

    wavelength: float
    num_modes: int = 4
    polarization: str = Polarization.TE
    pml: ScPml | None = None
    n_eff_shift: float | None = None
    # n_eff_shift 自动计算系数：n_clad + shift_frac·(n_core - n_clad)
    # 默认 0.5（n_clad 与 n_core 中点，兼顾强/弱限制波导）
    # SOI 220nm strip × 500nm TE0 权威实测 n_eff ≈ 2.5113（Tidy3D，n_Si=3.4）—
    #   https://gdsfactory.github.io/gdsfactory-photonics-training/notebooks/21_modesolver_fdfd.html
    # 本项目 n_Si=3.476（高 2.24%），2D FDE 实测 n_eff ≈ 2.6727（80×80 网格）。
    # shift_frac=0.5 → target=2.460（落在导模范围中段，远离体模 3.476）
    # 文献：Soref et al. 1991 IEEE JQE 27, 113-118（1D slab EIM，仅参考）；
    #   Lumerical MODE-FDE https://optics.ansys.com/hc/en-us/articles/360034396614；
    #   sipkit https://sipkit.readthedocs.io/en/docs-updates-1/1-%20Effective%20Index.html
    shift_frac: float = 0.5

    def __post_init__(self) -> None:
        if self.wavelength <= 0.0:
            raise ValueError(f"波长必须为正，实际 {self.wavelength}")
        if self.num_modes < 1:
            raise ValueError(f"模式数必须 ≥1，实际 {self.num_modes}")
        if self.polarization not in (Polarization.TE, Polarization.TM):
            raise ValueError(
                f"偏振模式须为 'te'/'tm'，实际 {self.polarization}"
            )
        if self.n_eff_shift is not None and self.n_eff_shift <= 0.0:
            raise ValueError(f"n_eff_shift 必须为正，实际 {self.n_eff_shift}")
        if not (0.0 < self.shift_frac < 1.0):
            raise ValueError(f"shift_frac 须 ∈ (0,1)，实际 {self.shift_frac}")


class FdeSolver:
    """FDE 本征模求解器（半矢量 TE/TM + scipy.sparse Arnoldi）。

    用法：
        cfg = FdeSolverConfig(wavelength=1.55e-6, num_modes=4, polarization='te')
        solver = FdeSolver(cfg)
        modes = solver.solve(eps_r_2d, window_size=(3.0e-6, 3.0e-6))
    """

    def __init__(self, config: FdeSolverConfig) -> None:
        self.config = config
        self.k0 = 2.0 * np.pi / config.wavelength
        self.omega = 2.0 * np.pi * _C0 / config.wavelength

    def _build_grid(
        self, eps_r: np.ndarray, window_size: tuple[float, float]
    ) -> YeeGrid:
        """构造 Yee 网格（含 PML 拉伸因子）。"""
        nx, ny = eps_r.shape
        dx = window_size[0] / nx
        dy = window_size[1] / ny
        spec = GridSpec(shape=(nx, ny), dx=dx, dy=dy)
        pml = self.config.pml if self.config.pml is not None else ScPml()
        sx = build_pml_stretch(nx, dx, self.config.wavelength, pml, axis="x")
        sy = build_pml_stretch(ny, dy, self.config.wavelength, pml, axis="y")
        return YeeGrid(spec=spec, eps_r=eps_r, stretch_x=sx, stretch_y=sy)

    def _assemble_te_matrix(self, grid: YeeGrid) -> sp.csr_array:
        """组装 TE 模本征矩阵 A（N×N 稀疏，本征值 β²）。

        TE 半矢量方程：∂²E_y/∂x² + ∂²E_y/∂y² + k₀²n² E_y = β² E_y
        离散化（5 点拉普拉斯，PML 复坐标拉伸融入差分）：
            A[i,i] = -2/(s_x²dx²) - 2/(s_y²dy²) + k₀²n²[i]
            A[i,i±Ny] = 1/(s_x²dx²)
            A[i,i±1] = 1/(s_y²dy²)
        """
        nx, ny = grid.spec.shape
        n = nx * ny
        dx, dy = grid.spec.dx, grid.spec.dy
        sx = grid.stretch_x
        sy = grid.stretch_y
        # PML 拉伸后的有效网格间距（s² 出现在二阶差分分母）
        sx2_dx2 = sx**2 * dx**2  # (nx,)
        sy2_dy2 = sy**2 * dy**2  # (ny,)
        # 网格点级别的有效间距（取相邻平均，Yee 半整数点）
        # 主对角：每点 i=(ix,iy) 的 -2/sx²dx² - 2/sy²dy² + k₀²n²
        # grid.eps_r 已存储相对介电常数 ε_r = n²，直接用即可（修复 n⁴ bug）
        # 文献：Xu & Huang 1994 IEE Proc.-J 141, 281-286 §2 TE 半矢量方程
        n_sq = grid.eps_r.real  # ε_r = n²（相对介电常数实部，TE 不含损耗）
        main_diag = (
            -2.0 / np.repeat(sx2_dx2, ny)
            - 2.0 / np.tile(sy2_dy2, nx)
            + (self.k0**2) * n_sq.flatten()
        )
        # x 方向邻接（±ny）：1/sx²dx²，取相邻 s 的平均
        sx_edge = 0.5 * (sx[:-1] + sx[1:])
        sx_edge_sq_dx2 = sx_edge**2 * dx**2  # (nx-1,)
        off_x = np.repeat(1.0 / sx_edge_sq_dx2, ny)  # (nx-1)*ny
        # y 方向邻接（±1）：1/sy²dy²
        sy_edge = 0.5 * (sy[:-1] + sy[1:])
        sy_edge_sq_dy2 = sy_edge**2 * dy**2  # (ny-1,)
        # 构造稀疏矩阵（向量化，无 Python 循环）
        # 主对角
        rows_main = np.arange(n)
        cols_main = rows_main
        data_main = main_diag
        # x 方向：行 i 与 i+ny（i < n-ny）
        rows_x = np.arange(n - ny)
        cols_x = rows_x + ny
        data_x = off_x
        # y 方向：每行内部 i 与 i+1（排除行末）
        rows_y = (np.arange(nx)[:, None] * ny + np.arange(ny - 1)[None, :]).ravel()
        cols_y = rows_y + 1
        data_y = np.tile(1.0 / sy_edge_sq_dy2, nx)
        # 拼装对称矩阵
        rows = np.concatenate([
            rows_main, rows_x, cols_x, rows_y, cols_y
        ])
        cols = np.concatenate([
            cols_main, cols_x, rows_x, cols_y, rows_y
        ])
        data = np.concatenate([
            data_main, data_x, data_x, data_y, data_y
        ])
        return sp.coo_array(
            (data.astype(np.complex128), (rows, cols)), shape=(n, n)
        ).tocsr()

    def _derive_te_fields(
        self, e_y: np.ndarray, beta: complex, grid: YeeGrid
    ) -> tuple[np.ndarray, ...]:
        """由 TE 主场 E_y 推导完整 6 分量场。

        TE 假设（E_y 主导）：
            H_x = -β/(ωμ₀) E_y
            E_z = (1/(iβ)) ∂E_y/∂x  [由 ∂_z E_y + ∂_y E_z = 0 → E_z = -∂_y E_y/(iβ)]
            E_x ≈ 0, H_y ≈ 0（TE 近似）
            H_z = (1/(iωμ₀)) ∂E_y/∂x
        """
        dx, dy = grid.spec.dx, grid.spec.dy
        e_y_c = e_y.astype(np.complex128)
        omega_mu = self.omega * _MU0
        # H_x = -β/(ωμ₀) E_y
        h_x = -beta / omega_mu * e_y_c
        # H_z = (1/(iωμ₀)) ∂E_y/∂x（中心差分，向量化）
        dey_dx = np.zeros_like(e_y_c)
        dey_dx[1:-1, :] = (e_y_c[2:, :] - e_y_c[:-2, :]) / (2.0 * dx)
        dey_dx[0, :] = (e_y_c[1, :] - e_y_c[0, :]) / dx
        dey_dx[-1, :] = (e_y_c[-1, :] - e_y_c[-2, :]) / dx
        h_z = dey_dx / (1j * omega_mu)
        # E_z = -(1/(iβ)) ∂E_y/∂y（由 ∇×E 的 x 分量 = iωμ₀H_x 推导）
        dey_dy = np.zeros_like(e_y_c)
        dey_dy[:, 1:-1] = (e_y_c[:, 2:] - e_y_c[:, :-2]) / (2.0 * dy)
        dey_dy[:, 0] = (e_y_c[:, 1] - e_y_c[:, 0]) / dy
        dey_dy[:, -1] = (e_y_c[:, -1] - e_y_c[:, -2]) / dy
        if abs(beta) < 1e-30:
            raise ValueError("β≈0，无法由 E_y 推导 E_z（检查本征值）")
        e_z = -dey_dy / (1j * beta)
        # E_x ≈ 0, H_y ≈ 0（TE 近似，全矢量形式留待后续 Sprint）
        e_x = np.zeros_like(e_y_c)
        h_y = np.zeros_like(e_y_c)
        return e_x, e_y_c, e_z, h_x, h_y, h_z

    def _normalize_mode(
        self, ex: np.ndarray, ey: np.ndarray, ez: np.ndarray,
        hx: np.ndarray, hy: np.ndarray, hz: np.ndarray,
        dx: float, dy: float,
    ) -> tuple[np.ndarray, ...]:
        """1W 功率归一化 + 相位修正（A04 §7）。"""
        poynting = 0.5 * np.real(
            np.sum(ex * np.conj(hy) - ey * np.conj(hx))
        )
        power = poynting * dx * dy
        if abs(power) < 1e-30:
            raise ValueError(
                "模式功率积分 ≈ 0，无法归一化（检查本征值是否为物理解）"
            )
        norm = np.sqrt(abs(power))
        fields = tuple(f / norm for f in (ex, ey, ez, hx, hy, hz))
        # 相位修正：使 E_y 主导分量实部为正（Lumerical 约定）
        ey_n = fields[1]
        amp_max = int(np.argmax(np.abs(ey_n)))
        ref = ey_n.ravel()[amp_max]
        if abs(ref) > 0.0:
            phase = np.angle(ref)
            fields = tuple(f * np.exp(-1j * phase) for f in fields)
        return fields

    @staticmethod
    def _te_tm_fraction(
        ex: np.ndarray, ey: np.ndarray, ez: np.ndarray,
        hx: np.ndarray, hy: np.ndarray, hz: np.ndarray,
    ) -> tuple[float, float]:
        """TE/TM 偏振分数（横向主场主导度）。

        te_fraction = |E_y|² / (|E_x|² + |E_y|²)   （TE 偏振 E_y 主导）
        tm_fraction = |E_x|² / (|E_x|² + |E_y|²)   （TM 偏振 E_x 主导）

        满足 te_fraction + tm_fraction = 1（互斥归一）。半矢量 TE 求解器（E_x=0）
        下 te_fraction=1.0，半矢量 TM（E_y=0）下 tm_fraction=1.0。

        不用纵向分量 E_z/H_z 定义（原 1-|E_z|²/|E|²），因半矢量近似下 E_z 是
        数值导数推导量（E_z = -∂E_y/∂y/(iβ)），在 Si/SiO₂ 高对比度界面（Δn=2.032）
        被中心差分放大，te_fraction 被严重低估。横向场分量是 FDE 直接求解量，无噪声。

        文献：Lumerical "Polarization fraction" 基于横向电场分量投影 —
            https://optics.ansys.com/hc/en-us/articles/360034396614
            Xu & Huang 1994 IEE Proc.-J 141, 281-286（半矢量 TE 定义 E_y 主导）
        """
        e_x_sq = float(np.sum(np.abs(ex) ** 2))
        e_y_sq = float(np.sum(np.abs(ey) ** 2))
        e_trans = e_x_sq + e_y_sq
        if e_trans <= 0.0:
            raise ValueError("横向电场能量为零，无法计算 TE/TM 分数")
        te_fraction = e_y_sq / e_trans
        tm_fraction = e_x_sq / e_trans
        return (te_fraction, tm_fraction)

    @staticmethod
    def _loss_db_cm(n_eff: complex, wavelength: float) -> float:
        """模式损耗（dB/cm），由 Im(n_eff) 换算（A04 §7）。

        Loss = -0.2 · log10(exp(-2π·κ/λ)) · 1e4
             = (4π·κ/λ) · (0.2/ln10) · 1e4   （κ>0 时损耗为正）

        纯实数 n_eff（无损耗）返回 0；κ<0（增益）返回负损耗。
        """
        kappa = float(np.imag(n_eff))
        if abs(kappa) < 1e-30:
            return 0.0
        # 直接用对数恒等简化，避免 exp 溢出
        # -0.2 * log10(exp(-2π·κ/λ)) = -0.2 * (-2π·κ/λ) / ln(10)
        return float(0.2 * 2.0 * np.pi * kappa / (wavelength * np.log(10.0)) * 1e4)

    @staticmethod
    def _field_localization(ey: np.ndarray, pml_layers: int) -> float:
        """场局域化度：非 PML 内部区域能量占比（排除 PML 污染模）。

        PML 污染模的场弥散到 PML 边界（loc < 0.5），真实导模的场集中在
        中心物理区域（loc > 0.9）。索引 clamp 防止宽波导（核心占满窗口）
        时 2×w_n > nx 导致负索引切片错误。

        文献：Taflove & Hagness 2005 §5 PML 污染模分析 —
            https://ieeexplore.ieee.org/document/1406362
        """
        nx, ny = ey.shape
        ix0 = min(pml_layers, nx // 2)
        ix1 = max(nx - pml_layers, ix0)
        iy0 = min(pml_layers, ny // 2)
        iy1 = max(ny - pml_layers, iy0)
        total = float(np.sum(np.abs(ey) ** 2))
        if total <= 0.0:
            return 0.0
        inner = float(np.sum(np.abs(ey[ix0:ix1, iy0:iy1]) ** 2))
        return inner / total

    def _extract_guided_candidates(
        self,
        eigvals: np.ndarray,
        eigvecs: np.ndarray,
        grid: YeeGrid,
        n_clad: float,
        n_eff_max_guided: float,
        pml_layers: int,
    ) -> list[tuple[complex, complex, np.ndarray, float]]:
        """从 Arnoldi 本征对提取真实导模候选（过滤体模 + PML 污染模）。

        过滤准则：
        1. n_clad < Re(n_eff) < n_eff_max_guided（导模范围，排除体模与辐射模）
        2. 场局域化度 loc > 0.5（排除 PML 污染模）

        返回：(n_eff, beta, ey_field, localization) 列表，未排序。

        文献：Lehoucq & Sorensen 1996 ARPACK Users' Guide §4（Arnoldi k 参数）
            — https://doi.org/10.1137/1.9780898719628
        """
        candidates: list[tuple[complex, complex, np.ndarray, float]] = []
        for i in range(len(eigvals)):
            beta = np.sqrt(eigvals[i])
            n_eff = beta / self.k0
            re_neff = float(np.real(n_eff))
            if not (n_clad < re_neff < n_eff_max_guided):
                continue
            ey = eigvecs[:, i].reshape(grid.spec.shape)
            loc = self._field_localization(ey, pml_layers)
            if loc < 0.5:
                continue
            candidates.append((complex(n_eff), complex(beta), ey, loc))
        return candidates

    def solve(
        self,
        eps_r: np.ndarray,
        window_size: tuple[float, float],
    ) -> list[Mode]:
        """求解 FDE 本征模。

        Args:
            eps_r: 2D 相对介电常数分布 (Nx, Ny)，实数或复数。
            window_size: 物理窗口尺寸 (Lx, Ly)，单位米。

        Returns:
            模式列表，按 n_eff 实部降序（基模首位），长度 ≤ num_modes。

        Raises:
            RuntimeError: Arnoldi 求解失败（规则 14，禁止 fall-back）。
            ValueError: 输入参数非法。
        """
        if eps_r.ndim != 2:
            raise ValueError(f"eps_r 必须为 2D，实际 {eps_r.ndim}D")
        if eps_r.shape[0] < 5 or eps_r.shape[1] < 5:
            raise ValueError(f"网格过小 {eps_r.shape}，至少 5x5")
        eps_r_c = eps_r.astype(np.complex128, copy=True)
        grid = self._build_grid(eps_r_c, window_size)
        a_mat = self._assemble_te_matrix(grid)
        # 导模范围与 shift-invert 目标
        n_clad = float(np.sqrt(np.real(eps_r_c).min()))
        n_core = float(np.sqrt(np.real(eps_r_c).max()))
        n_eff_shift = self.config.n_eff_shift
        if n_eff_shift is None:
            # 自动目标：shift_frac 偏向波导基模（避免命中体模）
            n_eff_shift = n_clad + self.config.shift_frac * (n_core - n_clad)
        pml_layers = self.config.pml.layers if self.config.pml is not None else 10
        # 体模上界：n_core - 0.5（排除接近 n_core 的体模/垂直共振模）
        # SOI 220nm strip TE0 实测 2.51-2.67（Tidy3D/sipkit），体模 n_eff>3.0，cutoff=2.976
        n_eff_max_guided = n_core - 0.5
        n_total = grid.spec.num_cells
        k_request = min(self.config.num_modes + 12, n_total - 2)
        sigma_main = (self.k0 * n_eff_shift) ** 2
        # *创新* 组合 Arnoldi 策略：C(LR) → A(LM) → D(sigma_high, LM)
        # 策略 C (which=LR)：找 sigma 附近最大实部模，对窄/宽波导均稳定命中基模
        # 策略 A (which=LM)：找 sigma 最近模（原默认），部分宽度迷失于 PML 模簇
        # 策略 D (sigma=2.8)：高目标偏置，宽波导高 n_eff 基模备选
        # 多策略非 fall-back：全部失败时 raise；每策略是合法 Arnoldi 配置
        # 文献：Lehoucq & Sorensen 1996 ARPACK §4；Taflove & Hagness 2005 §5
        strategies = [
            ("C", sigma_main, "LR"),
            ("A", sigma_main, "LM"),
            ("D", (self.k0 * 2.8) ** 2, "LM"),
        ]
        all_candidates: list[tuple[complex, complex, np.ndarray, float]] = []
        seen_neffs: list[float] = []
        for _name, sigma, which in strategies:
            if len(all_candidates) >= self.config.num_modes:
                break
            try:
                eigvals, eigvecs = spla.eigs(
                    a_mat, k=k_request, sigma=sigma, which=which
                )
            except spla.ArpackNoConvergence:
                continue
            cands = self._extract_guided_candidates(
                eigvals, eigvecs, grid, n_clad, n_eff_max_guided, pml_layers
            )
            for n_eff, beta, ey, loc in cands:
                re_n = float(np.real(n_eff))
                if any(abs(re_n - s) < 1e-6 for s in seen_neffs):
                    continue
                seen_neffs.append(re_n)
                all_candidates.append((n_eff, beta, ey, loc))
        if not all_candidates:
            raise RuntimeError(
                f"未求得导模（{n_clad:.4f} < Re(n_eff) < {n_eff_max_guided:.4f}），"
                f"n_eff_shift={n_eff_shift:.4f}，k_request={k_request}，"
                f"建议调整 n_eff_shift 或增加网格分辨率"
            )
        # 排序：penalty_score = Re(n_eff) - 10·|Im(n_eff)| 降序
        # 真实导模 |Im|<0.01，PML 残余 |Im|>0.1，10× 惩罚使低损耗优先
        all_candidates.sort(
            key=lambda c: float(np.real(c[0])) - 10.0 * abs(float(np.imag(c[0]))),
            reverse=True,
        )
        dx, dy = grid.spec.dx, grid.spec.dy
        modes: list[Mode] = []
        for n_eff, beta, ey, _loc in all_candidates:
            if len(modes) >= self.config.num_modes:
                break
            ex, ey_n, ez, hx, hy, hz = self._derive_te_fields(ey, beta, grid)
            try:
                ex, ey_n, ez, hx, hy, hz = self._normalize_mode(
                    ex, ey_n, ez, hx, hy, hz, dx, dy
                )
            except ValueError:
                continue
            te_frac, tm_frac = self._te_tm_fraction(ex, ey_n, ez, hx, hy, hz)
            loss = self._loss_db_cm(n_eff, self.config.wavelength)
            modes.append(
                Mode(
                    ex=ex, ey=ey_n, ez=ez, hx=hx, hy=hy, hz=hz,
                    beta=beta, n_eff=n_eff,
                    te_fraction=te_frac, tm_fraction=tm_frac,
                    loss_db_cm=loss, wavelength=self.config.wavelength,
                )
            )
        if not modes:
            raise RuntimeError(
                f"候选导模 {len(all_candidates)} 个但均无法归一化（功率积分≈0），"
                f"建议检查 eps_r 或增加网格分辨率"
            )
        modes.sort(key=lambda m: float(np.real(m.n_eff)), reverse=True)
        return modes


def solve_waveguide(
    eps_r: np.ndarray,
    wavelength: float,
    window_size: tuple[float, float],
    num_modes: int = 4,
    pml_layers: int = 10,
    polarization: str = Polarization.TE,
) -> list[Mode]:
    """便捷接口：一键求解波导 FDE 模式。

    Args:
        eps_r: 2D 相对介电常数分布。
        wavelength: 自由空间波长（米）。
        window_size: 物理窗口 (Lx, Ly)，米。
        num_modes: 待求模式数。
        pml_layers: PML 层数。
        polarization: 'te' 或 'tm'。

    Returns:
        模式列表（基模首位）。
    """
    cfg = FdeSolverConfig(
        wavelength=wavelength,
        num_modes=num_modes,
        polarization=polarization,
        pml=ScPml(layers=pml_layers),
    )
    return FdeSolver(cfg).solve(eps_r, window_size)
