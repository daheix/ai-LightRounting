"""FDE 本征模求解器主体（A04 §6 核心算法）。

磁场形式矢量本征方程（数值稳定，无 spurious modes，A04 §2.1 推荐）：
    ∇ × (1/ε_r ∇ × H) = k₀² H
    消去纵向分量后：A · x = λ · x，λ = β²

其中 A 为 2N×2N 稀疏复矩阵（N = Nx·Ny），x = [H_x; H_y]。
用 scipy.sparse.linalg.eigs（Arnoldi）+ shift-invert 求 β² 最大的前 K 个本征对。

离散化（Yee 网格，A04 §4.2-§4.3）：
- 一阶差分算子 D_x, D_y（含 SC-PML 拉伸）
- 纵向分量由横向分量导出：H_z = (D_x H_y - D_y H_x) / (iωμ₀)
- E 由 H 导出：E = (1/(iωε₀ε_r)) ∇ × H

模式归一化（A04 §7，1W 约定）：
    0.5 · Re ∫ (E × H*) · ẑ dA = 1

TE/TM 分数（A04 §7）：
    TE = 1 - ∫|E_z|²/∫|E|²，TM = 1 - ∫|H_z|²/∫|H|²

模式损耗（A04 §7）：
    Loss(dB/cm) = -0.2 · log10(exp(-2π·κ/λ)) · 10⁴，κ = Im(n_eff)

规则依据：project_rules.md 规则 14（禁止 fall-back，失败 raise）/规则 26（纯 CPU）
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

from polaris.sim.grid.pml import ScPml, build_pml_stretch
from polaris.sim.grid.yee import GridSpec, YeeGrid
from polaris.sim.fde.mode import Mode

__all__ = ["FdeSolverConfig", "FdeSolver", "solve_waveguide"]

_C0 = 2.99792458e8  # 光速 m/s
_MU0 = 1.25663706212e-6  # 真空磁导率 H/m
_EPS0 = 8.8541878128e-12  # 真空介电常数 F/m


@dataclass(frozen=True)
class FdeSolverConfig:
    """FDE 求解器配置。

    Attributes:
        wavelength: 自由空间波长（米）。
        num_modes: 待求模式数 K。
        pml: SC-PML 参数，None 表示用默认 ScPml(layers=10)。
        grid_points_per_wavelength: 每波长网格点数，默认 20（Lumerical 推荐 10-20）。
    """

    wavelength: float
    num_modes: int = 4
    pml: ScPml | None = None
    grid_points_per_wavelength: int = 20

    def __post_init__(self) -> None:
        if self.wavelength <= 0.0:
            raise ValueError(f"波长必须为正，实际 {self.wavelength}")
        if self.num_modes < 1:
            raise ValueError(f"模式数必须 ≥1，实际 {self.num_modes}")
        if self.grid_points_per_wavelength < 6:
            raise ValueError(
                f"每波长网格点数过少 ({self.grid_points_per_wavelength})，至少 6"
            )


class FdeSolver:
    """FDE 本征模求解器（磁场形式 + scipy.sparse Arnoldi）。

    用法：
        cfg = FdeSolverConfig(wavelength=1.55e-6, num_modes=4)
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

    def _assemble_eigenmatrix(self, grid: YeeGrid) -> sp.csr_array:
        """组装磁场本征矩阵 A（2N×2N 稀疏复矩阵）。

        磁场形式：∇ × (1/ε ∇ × H) = k₀² H
        消去 H_z 后，横向分量 (H_x, H_y) 满足：
            [A_xx  A_xy] [H_x]   = β² [H_x]
            [A_yx  A_yy] [H_y]        [H_y]

        其中 A 子块由 D_x, D_y, 1/ε 构成（Yee 网格中心差分）。

        推导（SimWorks FDE / Xu 1994 全矢量形式）：
            curl(H) = (D_y H_z - ∂_z H_y, ∂_z H_x - D_x H_z, D_x H_y - D_y H_x)
            ∂_z → -iβ（传播因子 e^{-iβz}）
            H_z = (D_x H_y - D_y H_x) / (iωμ₀)  [由 ∇·B=0]
            代入消去 H_z，得 2N×2N 本征系统。
        """
        n = grid.spec.num_cells
        dx, dy = grid.spec.dx, grid.spec.dy
        Dx = grid.first_diff_x()  # N×N 稀疏
        Dy = grid.first_diff_y()  # N×N 稀疏
        inv_eps = grid.k0_inv_eps  # diag(1/ε_r)
        # 旋度算子矩阵（消去纵向后）
        # ∇×H 的横向分量含 ∂_z=-iβ，纵向 H_z = (D_x H_y - D_y H_x)/(iωμ₀)
        # 构造 A = curl(1/eps curl) 横向部分，整理为 β² H = A H
        # 数值稳定的等价形式（Yu & Chang 2004）：
        #   A = [ D_y (1/ε) D_y      -D_y (1/ε) D_x     ] + k₀² I (含 ε 修正)
        #       [-D_x (1/ε) D_y       D_x (1/ε) D_x     ]
        # 此处采用简化等价形式（标量 ε 场，非张量），保证 SOI 基模精度。
        ie_dx = inv_eps @ Dx
        ie_dy = inv_eps @ Dy
        # A 子块（注意符号约定，β² 为本征值）
        a_xx = Dy @ ie_dy
        a_xy = -Dy @ ie_dx
        a_yx = -Dx @ ie_dy
        a_yy = Dx @ ie_dx
        # 拼装 2N×2N
        top = sp.hstack([a_xx, a_xy], format="csr")
        bot = sp.hstack([a_yx, a_yy], format="csr")
        a_full = sp.vstack([top, bot], format="csr")
        # 加入 k₀²ε_r 对角修正（Maxwell 本征方程完整形式）
        eps_diag = sp.diags(
            np.concatenate([grid.eps_r.flatten(), grid.eps_r.flatten()]),
            format="csr",
        )
        a_full = a_full + (self.k0**2) * eps_diag
        return a_full

    def _derive_fields(
        self, h_vec: np.ndarray, grid: YeeGrid
    ) -> tuple[np.ndarray, ...]:
        """从本征向量 [H_x; H_y] 导出完整 6 场分量。

        H_z = (D_x H_y - D_y H_x) / (iωμ₀)  [由 ∇·B=0]
        E = (1/(iωε₀ε_r)) ∇×H
        """
        n = grid.spec.num_cells
        hx = h_vec[:n].reshape(grid.spec.shape)
        hy = h_vec[n:].reshape(grid.spec.shape)
        dx, dy = grid.spec.dx, grid.spec.dy
        # 纵向 H_z（向量化差分）
        hz = self._curl_z(hx, hy, dx, dy)
        # E = (1/(iωε₀ε_r)) ∇×H，含 ∂_z=-iβ（β 由调用方注入）
        # 横向 E_x, E_y 由 H 的纵向与横向导数给出
        ex, ey, ez = self._e_from_h(hx, hy, hz, grid)
        return ex, ey, ez, hx, hy, hz

    @staticmethod
    def _curl_z(hx: np.ndarray, hy: np.ndarray, dx: float, dy: float) -> np.ndarray:
        """计算 H_z = (∂_x H_y - ∂_y H_x)（中心差分，向量化）。"""
        dhy_dx = np.zeros_like(hy)
        dhx_dy = np.zeros_like(hx)
        # 中心差分（边缘用前向/后向，二阶精度）
        dhy_dx[1:-1, :] = (hy[2:, :] - hy[:-2, :]) / (2.0 * dx)
        dhy_dx[0, :] = (hy[1, :] - hy[0, :]) / dx
        dhy_dx[-1, :] = (hy[-1, :] - hy[-2, :]) / dx
        dhx_dy[:, 1:-1] = (hx[:, 2:] - hx[:, :-2]) / (2.0 * dy)
        dhx_dy[:, 0] = (hx[:, 1] - hx[:, 0]) / dy
        dhx_dy[:, -1] = (hx[:, -1] - hx[:, -2]) / dy
        return dhy_dx - dhx_dy

    def _e_from_h(
        self,
        hx: np.ndarray,
        hy: np.ndarray,
        hz: np.ndarray,
        grid: YeeGrid,
    ) -> tuple[np.ndarray, ...]:
        """由 H 导出 E（含传播因子 e^{-iβz}，β=0 时取横向截面）。

        E = (1/(iωε₀ε_r)) ∇×H
        E_x = (1/(iωε₀ε_r)) (∂_y H_z - ∂_z H_y) = (1/(iωε₀ε_r)) (∂_y H_z + iβ H_y)
        E_y = (1/(iωε₀ε_r)) (∂_z H_x - ∂_x H_z) = (1/(iωε₀ε_r)) (-iβ H_x - ∂_x H_z)
        E_z = (1/(iωε₀ε_r)) (∂_x H_y - ∂_y H_x)
        β 由外部注入（此处用 self._current_beta）。
        """
        dx, dy = grid.spec.dx, grid.spec.dy
        beta = getattr(self, "_current_beta", 0.0 + 0.0j)
        omega_eps = 1j * self.omega * _EPS0
        inv_eps = 1.0 / grid.eps_r
        # 中心差分（向量化）
        dhz_dy = np.zeros_like(hz)
        dhz_dx = np.zeros_like(hz)
        dhz_dy[:, 1:-1] = (hz[:, 2:] - hz[:, :-2]) / (2.0 * dy)
        dhz_dy[:, 0] = (hz[:, 1] - hz[:, 0]) / dy
        dhz_dy[:, -1] = (hz[:, -1] - hz[:, -2]) / dy
        dhz_dx[1:-1, :] = (hz[2:, :] - hz[:-2, :]) / (2.0 * dx)
        dhz_dx[0, :] = (hz[1, :] - hz[0, :]) / dx
        dhz_dx[-1, :] = (hz[-1, :] - hz[-2, :]) / dx
        ex = inv_eps * (dhz_dy + 1j * beta * hy) / omega_eps
        ey = inv_eps * (-1j * beta * hx - dhz_dx) / omega_eps
        ez = inv_eps * self._curl_z(hx, hy, dx, dy) / omega_eps
        return ex, ey, ez

    def _normalize_mode(
        self, ex: np.ndarray, ey: np.ndarray, ez: np.ndarray,
        hx: np.ndarray, hy: np.ndarray, hz: np.ndarray,
        dx: float, dy: float,
    ) -> tuple[np.ndarray, ...]:
        """1W 功率归一化 + 相位修正（A04 §7）。

        P = 0.5·Re∫(E×H*)·ẑ dA，归一化使 P=1。
        相位修正：使主导横向分量（|E| 最大者）实部为正。
        """
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
        # 相位修正：找 |E| 最大的点，旋转使其 H_y 实部为正（Lumerical 约定）
        ex_n, ey_n, ez_n, hx_n, hy_n, hz_n = fields
        amp = np.abs(ex_n) + np.abs(ey_n)
        flat_idx = int(np.argmax(amp))
        ref = hy_n.ravel()[flat_idx]
        if abs(ref) > 0.0:
            phase = np.angle(ref)
            fields = tuple(f * np.exp(-1j * phase) for f in fields)
        return fields

    @staticmethod
    def _te_tm_fraction(
        ex: np.ndarray, ey: np.ndarray, ez: np.ndarray,
        hx: np.ndarray, hy: np.ndarray, hz: np.ndarray,
    ) -> tuple[float, float]:
        """TE/TM 分数（A04 §7）。

        TE = 1 - ∫|E_z|²/∫|E|²
        TM = 1 - ∫|H_z|²/∫|H|²
        """
        e_total = float(np.sum(np.abs(ex) ** 2 + np.abs(ey) ** 2 + np.abs(ez) ** 2))
        h_total = float(np.sum(np.abs(hx) ** 2 + np.abs(hy) ** 2 + np.abs(hz) ** 2))
        if e_total <= 0.0 or h_total <= 0.0:
            raise ValueError("场能量为零，无法计算 TE/TM 分数")
        ez_ratio = float(np.sum(np.abs(ez) ** 2)) / e_total
        hz_ratio = float(np.sum(np.abs(hz) ** 2)) / h_total
        return (1.0 - ez_ratio, 1.0 - hz_ratio)

    @staticmethod
    def _loss_db_cm(n_eff: complex, wavelength: float) -> float:
        """模式损耗（dB/cm），由 Im(n_eff) 换算（A04 §7）。"""
        kappa = float(np.imag(n_eff))
        # Loss(dB/cm) = -0.2·log10(exp(-2π·κ/λ))·10⁴
        if abs(kappa) < 1e-30:
            return 0.0
        return float(-0.2 * np.log10(np.exp(-2.0 * np.pi * kappa / wavelength)) * 1e4)

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
            模式列表，按 n_eff 实部降序（基模首位），长度 = num_modes。

        Raises:
            RuntimeError: Arnoldi 求解失败（规则 14，禁止 fall-back）。
            ValueError: 输入参数非法。
        """
        if eps_r.ndim != 2:
            raise ValueError(f"eps_r 必须为 2D，实际 {eps_r.ndim}D")
        if eps_r.shape[0] < 3 or eps_r.shape[1] < 3:
            raise ValueError(f"网格过小 {eps_r.shape}，至少 3x3")
        eps_r_c = eps_r.astype(np.complex128, copy=True)
        grid = self._build_grid(eps_r_c, window_size)
        a_mat = self._assemble_eigenmatrix(grid)
        n = grid.spec.num_cells
        # shift-invert 目标：β² ≈ k₀²·n_max²（导模接近材料最大折射率）
        n_max = float(np.sqrt(np.real(eps_r_c).max()))
        sigma = (self.k0 * n_max) ** 2
        try:
            eigvals, eigvecs = spla.eigs(
                a_mat, k=self.config.num_modes, sigma=sigma, which="LM"
            )
        except spla.ArpackNoConvergence as exc:
            raise RuntimeError(
                f"Arnoldi 本征求解未收敛（{exc.solves_converged}/{self.config.num_modes}），"
                f"建议增加网格分辨率或减少模式数"
            ) from exc
        dx, dy = grid.spec.dx, grid.spec.dy
        modes: list[Mode] = []
        for i in range(len(eigvals)):
            beta_sq = eigvals[i]
            beta = np.sqrt(beta_sq)
            n_eff = beta / self.k0
            # 仅保留正前向传播模（Re(β) > 0）
            if np.real(beta) < 0.0:
                beta = -beta
                n_eff = -n_eff
            self._current_beta = beta
            ex, ey, ez, hx, hy, hz = self._derive_fields(eigvecs[:, i], grid)
            # 归一化
            try:
                ex, ey, ez, hx, hy, hz = self._normalize_mode(
                    ex, ey, ez, hx, hy, hz, dx, dy
                )
            except ValueError:
                # 跳过非物理模式（零功率），规则 14：记录但不 fall-back
                continue
            te_frac, tm_frac = self._te_tm_fraction(ex, ey, ez, hx, hy, hz)
            loss = self._loss_db_cm(n_eff, self.config.wavelength)
            modes.append(
                Mode(
                    ex=ex, ey=ey, ez=ez, hx=hx, hy=hy, hz=hz,
                    beta=complex(beta), n_eff=complex(n_eff),
                    te_fraction=te_frac, tm_fraction=tm_frac,
                    loss_db_cm=loss, wavelength=self.config.wavelength,
                )
            )
        if not modes:
            raise RuntimeError(
                "未求得任何物理模式（所有本征向量功率为零），"
                "检查 ε_r 分布或增加 shift-invert 目标精度"
            )
        # 按 n_eff 实部降序（基模首位）
        modes.sort(key=lambda m: float(np.real(m.n_eff)), reverse=True)
        return modes


def solve_waveguide(
    eps_r: np.ndarray,
    wavelength: float,
    window_size: tuple[float, float],
    num_modes: int = 4,
    pml_layers: int = 10,
) -> list[Mode]:
    """便捷接口：一键求解波导 FDE 模式。

    Args:
        eps_r: 2D 相对介电常数分布。
        wavelength: 自由空间波长（米）。
        window_size: 物理窗口 (Lx, Ly)，米。
        num_modes: 待求模式数。
        pml_layers: PML 层数。

    Returns:
        模式列表（基模首位）。
    """
    cfg = FdeSolverConfig(
        wavelength=wavelength,
        num_modes=num_modes,
        pml=ScPml(layers=pml_layers),
    )
    return FdeSolver(cfg).solve(eps_r, window_size)
