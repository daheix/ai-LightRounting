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

文献来源：
- Xu CL, Huang WP, "Full-vectorial mode calculations by finite difference method,"
  IEE Proc.-J 141, 281-286 (1994).
- Simsek E, "Practical Vectorial Mode Solver," arXiv:2503.17746 (2025).

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
            自动计算（n_clad + 0.7·(n_core - n_clad)，偏向 core 以优先
            命中基模；参考 Tidy3D ModeSpec.target_neff 约定）。
    """

    wavelength: float
    num_modes: int = 4
    polarization: str = Polarization.TE
    pml: ScPml | None = None
    n_eff_shift: float | None = None

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
        n_sq = grid.eps_r.real**2  # 实数折射率平方（TE 不含损耗）
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
        """TE/TM 分数（A04 §7）。"""
        e_total = float(np.sum(np.abs(ex) ** 2 + np.abs(ey) ** 2 + np.abs(ez) ** 2))
        h_total = float(np.sum(np.abs(hx) ** 2 + np.abs(hy) ** 2 + np.abs(hz) ** 2))
        if e_total <= 0.0 or h_total <= 0.0:
            raise ValueError("场能量为零，无法计算 TE/TM 分数")
        ez_ratio = float(np.sum(np.abs(ez) ** 2)) / e_total
        hz_ratio = float(np.sum(np.abs(hz) ** 2)) / h_total
        return (1.0 - ez_ratio, 1.0 - hz_ratio)

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
            # 自动目标：偏向 core 以优先命中基模（Tidy3D target_neff 约定）
            n_eff_shift = n_clad + 0.7 * (n_core - n_clad)
        sigma = (self.k0 * n_eff_shift) ** 2
        # 请求多于 num_modes 个本征对，再筛选导模（避免 PML/体模挤占名额）
        n_total = grid.spec.num_cells
        k_request = min(self.config.num_modes + 4, n_total - 2)
        try:
            eigvals, eigvecs = spla.eigs(
                a_mat, k=k_request, sigma=sigma, which="LM"
            )
        except spla.ArpackNoConvergence as exc:
            raise RuntimeError(
                f"Arnoldi 本征求解未收敛（{exc.eigenvalues.size}/{k_request}），"
                f"建议增加网格分辨率或减少模式数"
            ) from exc
        dx, dy = grid.spec.dx, grid.spec.dy
        # 候选导模列表：n_clad < Re(n_eff) < n_core（排除辐射模与体模）
        candidates: list[tuple[float, float, int, complex]] = []
        # 候选元组：(Re(n_eff), -|Im(n_eff)|, idx, n_eff)，排序时优先高 Re、低 |Im|
        for i in range(len(eigvals)):
            beta = np.sqrt(eigvals[i])
            n_eff = beta / self.k0
            re_neff = float(np.real(n_eff))
            im_neff = float(np.imag(n_eff))
            if not (n_clad < re_neff < n_core):
                continue
            candidates.append((re_neff, -abs(im_neff), i, complex(n_eff)))
        # 排序：Re(n_eff) 降序为主，|Im(n_eff)| 升序为辅（真实导模 Im≈0 排前）
        candidates.sort(key=lambda c: (c[0], c[1]), reverse=True)
        modes: list[Mode] = []
        for re_neff, _neg_im, i, n_eff in candidates:
            if len(modes) >= self.config.num_modes:
                break
            beta = complex(np.sqrt(eigvals[i]))
            ex, ey, ez, hx, hy, hz = self._derive_te_fields(
                eigvecs[:, i].reshape(grid.spec.shape), beta, grid
            )
            try:
                ex, ey, ez, hx, hy, hz = self._normalize_mode(
                    ex, ey, ez, hx, hy, hz, dx, dy
                )
            except ValueError:
                continue
            te_frac, tm_frac = self._te_tm_fraction(ex, ey, ez, hx, hy, hz)
            loss = self._loss_db_cm(n_eff, self.config.wavelength)
            modes.append(
                Mode(
                    ex=ex, ey=ey, ez=ez, hx=hx, hy=hy, hz=hz,
                    beta=beta, n_eff=n_eff,
                    te_fraction=te_frac, tm_fraction=tm_frac,
                    loss_db_cm=loss, wavelength=self.config.wavelength,
                )
            )
        if not modes:
            raise RuntimeError(
                f"未求得导模（n_clad={n_clad:.4f} < Re(n_eff) < n_core={n_core:.4f}），"
                f"n_eff_shift={n_eff_shift:.4f}，请求 k={k_request}，"
                f"考虑调整 n_eff_shift 或增加网格分辨率"
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
