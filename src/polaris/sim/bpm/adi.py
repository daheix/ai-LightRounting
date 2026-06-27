"""2D ADI 分裂步进（A03 §4.3 公式 F3，Peaceman & Rachford 1955）。

2D 横向（x, y）时，直接 Crank-Nicolson 产生五对角系统（O(N²) 求解成本）。
采用交替方向隐式（Alternating Direction Implicit, ADI）分裂：将一步 Δz 拆为
两个半步，x、y 方向分别隐式求解，每半步仍为三对角系统（A03 §4.3）。

ADI 半步公式（A03 §4.3 公式 F3，Peaceman & Rachford 1955）::

    半步 1（x 隐式）:
        ψ^{n+1/2} = [I - Δz/(2a)·Ax]⁻¹·[I + Δz/(2a)·Ay]·ψ^n
    半步 2（y 隐式）:
        ψ^{n+1}   = [I - Δz/(2a)·Ay]⁻¹·[I + Δz/(2a)·Ax]·ψ^{n+1/2}

其中 Ax 为 x 方向三对角算子（沿行作用），Ay 为 y 方向三对角算子（沿列作用），
a = 2i·k₀·n_ref（SVEA 抛物方程系数，A03 §3.2 公式 F1）。

ADI 总复杂度 O(Nx·Ny)（两次三对角求解），二阶时间精度（与 Crank-Nicolson 等价），
无条件稳定（Peaceman & Rachford 1955 定理）。是 2D-BPM 的标准方案。

向量化策略（python代码开发规则.md §4）：
- 算子构造（lhs_banded 数组）：NumPy 切片一次性构造，无 Python 循环
- 模板应用（Ax @ ψ, Ay @ ψ）：NumPy 切片向量化，禁止逐元素循环
- 三对角求解：scipy.linalg.solve_banded 沿行/列循环调用（A03 §8.3 明确允许：
  "每半步沿行/列循环调 solve_banded，NumPy 切片向量化构造右端"，
  每次调用为 BLAS 后端的 O(N) Thomas 算法，非 Python 逐元素循环）
- 1D n（n(x) 沿 y 均匀）时 x 隐式半步可批处理（单次 solve_banded 多 RHS）

TBC 边界（A03 §5.1，2D 推广）：
- x 隐式半步：左/右边界（i=0, i=Nx-1）逐行估计 kₓ，向量化修改 lhs_x 边界行
- y 隐式半步：上/下边界（j=0, j=Ny-1）逐列估计 k_y，向量化修改 lhs_y 边界行

文献来源（≥5，规则 18 学术诚信）：
1. Hadley 1992 IEEE J Quantum Electron 28(1) 363-370 — TBC + 2D-BPM —
   https://doi.org/10.1109/3.119546
2. Hadley 1991 Opt Lett 16 624-626 — TBC 短文版本 —
   https://doi.org/10.1364/OL.16.000624
3. Chung & Dagli 1991 IEEE PTL 3 150-152 — FD-BPM ADI 实现 —
   https://doi.org/10.1109/68.84566
4. Hadley 1994 Opt Lett 17 1426-1428 (Padé wide-angle) —
   https://doi.org/10.1364/OL.17.001426
5. Optiwave OptiBPM Boundary Conditions —
   https://optiwave.com/optibpm-manuals/bpm-boundary-conditions-for-bpm/
6. RP Photonics Encyclopedia: Numerical Beam Propagation —
   https://www.rp-photonics.com/numerical_beam_propagation.html
7. beampy Python BPM — 2D ADI 开源参考实现 —
   https://beampy.readthedocs.io/en/latest/code_bpm.html

规则依据：project_rules.md 规则 14（禁止 fall-back）/规则 18（学术诚信）
/规则 26（GPU 不参与，纯 numpy+scipy.linalg.solve_banded）
/python代码开发规则.md §4（向量化模板 + A03 §8.3 允许的 solve_banded 行/列循环）
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import scipy.linalg

from polaris.sim.bpm.boundary import BoundaryType, _force_outgoing_vec
from polaris.sim.bpm.operators import (
    Polarization,
)

__all__ = [
    "AdiStepper2D",
    "adi_propagate_2d",
]

# 默认 ADI 权重 θ=0.5（与 Crank-Nicolson 等价，二阶时间精度，A03 §4.3）
DEFAULT_THETA = 0.5


def _apply_x_stencil(psi: np.ndarray, main_x: np.ndarray, off_x: float) -> np.ndarray:
    """沿 x 轴应用 Ax 模板（向量化，无 Python 循环）。

    (Ax @ ψ)[j, i] = main_x[j,i]·ψ[j,i] + off_x·(ψ[j,i-1] + ψ[j,i+1])
    边界（Dirichlet 基底）：无外侧邻点，仅内侧邻点贡献。

    Args:
        psi: 场 (Ny, Nx)。
        main_x: Ax 主对角 (Ny, Nx)，含 -2/Δx² + b 项。
        off_x: 1/Δx²（标量）。

    Returns:
        Ax @ ψ，形状 (Ny, Nx)。
    """
    result = main_x * psi
    # 内部节点：off_x·(ψ[:, i-1] + ψ[:, i+1])（向量化切片）
    result[:, 1:-1] += off_x * (psi[:, :-2] + psi[:, 2:])
    # 左边界（i=0，Dirichlet 基底无 i=-1 邻点）：仅 +off_x·ψ[:, 1]
    if psi.shape[1] >= 2:
        result[:, 0] += off_x * psi[:, 1]
        result[:, -1] += off_x * psi[:, -2]
    return result


def _apply_y_stencil(psi: np.ndarray, main_y: np.ndarray, off_y: float) -> np.ndarray:
    """沿 y 轴应用 Ay 模板（向量化，无 Python 循环）。

    (Ay @ ψ)[j, i] = main_y[j,i]·ψ[j,i] + off_y·(ψ[j-1,i] + ψ[j+1,i])
    边界（Dirichlet 基底）：无外侧邻点，仅内侧邻点贡献。

    Args:
        psi: 场 (Ny, Nx)。
        main_y: Ay 主对角 (Ny, Nx)，含 -2/Δy² + b 项。
        off_y: 1/Δy²（标量）。

    Returns:
        Ay @ ψ，形状 (Ny, Nx)。
    """
    result = main_y * psi
    # 内部节点：off_y·(ψ[j-1, :] + ψ[j+1, :])（向量化切片）
    result[1:-1, :] += off_y * (psi[:-2, :] + psi[2:, :])
    # 上边界（j=0，Dirichlet 基底无 j=-1 邻点）：仅 +off_y·ψ[1, :]
    if psi.shape[0] >= 2:
        result[0, :] += off_y * psi[1, :]
        result[-1, :] += off_y * psi[-2, :]
    return result


def _estimate_kx_boundaries_2d(psi_2d: np.ndarray, dx: float) -> tuple[np.ndarray, np.ndarray]:
    """2D 场逐行估计左/右边界外向波数 kₓ（A03 §5.1 公式 F4，向量化）。

    Args:
        psi_2d: 2D 场 (Ny, Nx)。
        dx: x 方向网格间距。

    Returns:
        (kx_left, kx_right): 各为 (Ny,) 复数数组，Re ≥ 0（外向强制）。

    Raises:
        ValueError: 边界内点退化（行场过小，规则 14）。
    """
    if psi_2d.ndim != 2:
        raise ValueError(f"psi_2d 须为 2D，实际 {psi_2d.ndim}D")
    if dx <= 0.0:
        raise ValueError(f"dx 必须为正，实际 {dx}")
    # 左边界：kₓ^(L) = (-i/Δx)·ln(ψ[:, 0] / ψ[:, 1])
    psi_left_bnd = psi_2d[:, 0]
    psi_left_in = psi_2d[:, 1]
    psi_right_bnd = psi_2d[:, -1]
    psi_right_in = psi_2d[:, -2]
    # 退化检测（逐行，向量化）：内点场过小则 TBC 退化
    if np.any(np.abs(psi_left_in) < 1e-300) or np.any(np.abs(psi_right_in) < 1e-300):
        raise ValueError("TBC 退化：边界内点场过小（场已完全衰减到边界，检查窗口大小或场归一化）")
    kx_left = (-1j / dx) * np.log(psi_left_bnd / psi_left_in)
    kx_right = (-1j / dx) * np.log(psi_right_bnd / psi_right_in)
    # 外向强制：逐分量取模 |Re|+i·|Im|（Hadley 1992 公式 F4，保留倏逝衰减，
    # 禁止用 np.abs 对整个复数取模，详见 boundary._force_outgoing_vec）
    kx_left = _force_outgoing_vec(kx_left)
    kx_right = _force_outgoing_vec(kx_right)
    return kx_left, kx_right


def _estimate_ky_boundaries_2d(psi_2d: np.ndarray, dy: float) -> tuple[np.ndarray, np.ndarray]:
    """2D 场逐列估计上/下边界外向波数 k_y（A03 §5.1 公式 F4，向量化）。

    Args:
        psi_2d: 2D 场 (Ny, Nx)。
        dy: y 方向网格间距。

    Returns:
        (ky_top, ky_bottom): 各为 (Nx,) 复数数组，Re ≥ 0（外向强制）。

    Raises:
        ValueError: 边界内点退化。
    """
    if psi_2d.ndim != 2:
        raise ValueError(f"psi_2d 须为 2D，实际 {psi_2d.ndim}D")
    if dy <= 0.0:
        raise ValueError(f"dy 必须为正，实际 {dy}")
    # 上边界：k_y^(T) = (-i/Δy)·ln(ψ[0, :] / ψ[1, :])
    psi_top_bnd = psi_2d[0, :]
    psi_top_in = psi_2d[1, :]
    psi_bot_bnd = psi_2d[-1, :]
    psi_bot_in = psi_2d[-2, :]
    if np.any(np.abs(psi_top_in) < 1e-300) or np.any(np.abs(psi_bot_in) < 1e-300):
        raise ValueError("TBC 退化：边界内点场过小（场已完全衰减到边界，检查窗口大小或场归一化）")
    ky_top = (-1j / dy) * np.log(psi_top_bnd / psi_top_in)
    ky_bottom = (-1j / dy) * np.log(psi_bot_bnd / psi_bot_in)
    # 外向强制：逐分量取模（Hadley 1992 公式 F4，保留倏逝衰减）
    ky_top = _force_outgoing_vec(ky_top)
    ky_bottom = _force_outgoing_vec(ky_bottom)
    return ky_top, ky_bottom


def _apply_tbc_2d_x_inplace(
    lhs_x_arr: np.ndarray,
    kx_left: np.ndarray,
    kx_right: np.ndarray,
    dx: float,
    alpha_lhs: complex,
    inv_dx2: float,
) -> None:
    """2D TBC 沿 x 方向修改 lhs_x_arr 左/右边界行（原地，向量化）。

    对每行 j 的 lhs_x[j]（形状 (3, Nx)），修改边界主对角元：
        lhs_x[j, 1, 0]   -= α·(1/Δx²)·exp(i·kₓ_left[j]·Δx)
        lhs_x[j, 1, Nx-1] -= α·(1/Δx²)·exp(i·kₓ_right[j]·Δx)

    向量化（NumPy 广播，无 Python 循环）。

    Args:
        lhs_x_arr: per-row lhs_x 数组 (Ny, 3, Nx)，调用前为 Dirichlet 基底。
        kx_left: 左边界外向波数 (Ny,)，Re ≥ 0。
        kx_right: 右边界外向波数 (Ny,)，Re ≥ 0。
        dx: x 方向网格间距。
        alpha_lhs: 复系数 θ·Δz/a。
        inv_dx2: 1/Δx²（预计算）。
    """
    extrap_left = np.exp(1j * kx_left * dx)  # (Ny,)
    extrap_right = np.exp(1j * kx_right * dx)  # (Ny,)
    # 向量化修改边界主对角元（NumPy 广播 over Ny）
    lhs_x_arr[:, 1, 0] -= alpha_lhs * inv_dx2 * extrap_left
    lhs_x_arr[:, 1, -1] -= alpha_lhs * inv_dx2 * extrap_right


def _apply_tbc_2d_y_inplace(
    lhs_y_arr: np.ndarray,
    ky_top: np.ndarray,
    ky_bottom: np.ndarray,
    dy: float,
    alpha_lhs: complex,
    inv_dy2: float,
) -> None:
    """2D TBC 沿 y 方向修改 lhs_y_arr 上/下边界行（原地，向量化）。

    对每列 i 的 lhs_y[i]（形状 (3, Ny)），修改边界主对角元：
        lhs_y[i, 1, 0]   -= α·(1/Δy²)·exp(i·k_y_top[i]·Δy)
        lhs_y[i, 1, Ny-1] -= α·(1/Δy²)·exp(i·k_y_bottom[i]·Δy)

    Args:
        lhs_y_arr: per-col lhs_y 数组 (Nx, 3, Ny)，调用前为 Dirichlet 基底。
        ky_top: 上边界外向波数 (Nx,)，Re ≥ 0。
        ky_bottom: 下边界外向波数 (Nx,)，Re ≥ 0。
        dy: y 方向网格间距。
        alpha_lhs: 复系数 θ·Δz/a。
        inv_dy2: 1/Δy²（预计算）。
    """
    extrap_top = np.exp(1j * ky_top * dy)  # (Nx,)
    extrap_bottom = np.exp(1j * ky_bottom * dy)  # (Nx,)
    lhs_y_arr[:, 1, 0] -= alpha_lhs * inv_dy2 * extrap_top
    lhs_y_arr[:, 1, -1] -= alpha_lhs * inv_dy2 * extrap_bottom


def _apply_tbc_2d_x_rhs_inplace(
    rhs: np.ndarray,
    psi: np.ndarray,
    kx_left: np.ndarray,
    kx_right: np.ndarray,
    dx: float,
    alpha_rhs: complex,
    inv_dx2: float,
) -> None:
    """2D TBC 沿 x 方向修改 rhs 左/右边界项（原地，向量化，Bug 5 修复）。

    对每行 j，右端向量的左/右边界项增加 Ax 显式算子的 TBC 外推贡献：
        rhs[j, 0]   += α_rhs·(1/Δx²)·exp(i·kₓ_left[j]·Δx)·ψ[j, 0]
        rhs[j, -1]  += α_rhs·(1/Δx²)·exp(i·kₓ_right[j]·Δx)·ψ[j, -1]

    与 ``_apply_tbc_2d_x_inplace``（LHS）对称，用于 ADI 半步中 Ax 出现在显式
    算子（RHS）时的 TBC 修改。

    Args:
        rhs: 右端场 (Ny, Nx)，调用前为 Dirichlet 基底，原地修改。
        psi: 当前场 (Ny, Nx)，用于提取边界节点值。
        kx_left: 左边界外向波数 (Ny,)，Re ≥ 0。
        kx_right: 右边界外向波数 (Ny,)，Re ≥ 0。
        dx: x 方向网格间距。
        alpha_rhs: 复系数 (1-θ)·Δz/a。
        inv_dx2: 1/Δx²（预计算）。
    """
    extrap_left = np.exp(1j * kx_left * dx)  # (Ny,)
    extrap_right = np.exp(1j * kx_right * dx)  # (Ny,)
    rhs[:, 0] += alpha_rhs * inv_dx2 * extrap_left * psi[:, 0]
    rhs[:, -1] += alpha_rhs * inv_dx2 * extrap_right * psi[:, -1]


def _apply_tbc_2d_y_rhs_inplace(
    rhs: np.ndarray,
    psi: np.ndarray,
    ky_top: np.ndarray,
    ky_bottom: np.ndarray,
    dy: float,
    alpha_rhs: complex,
    inv_dy2: float,
) -> None:
    """2D TBC 沿 y 方向修改 rhs 上/下边界项（原地，向量化，Bug 5 修复）。

    对每列 i，右端向量的上/下边界项增加 Ay 显式算子的 TBC 外推贡献：
        rhs[0, i]   += α_rhs·(1/Δy²)·exp(i·k_y_top[i]·Δy)·ψ[0, i]
        rhs[-1, i]  += α_rhs·(1/Δy²)·exp(i·k_y_bottom[i]·Δy)·ψ[-1, i]

    与 ``_apply_tbc_2d_y_inplace``（LHS）对称，用于 ADI 半步中 Ay 出现在显式
    算子（RHS）时的 TBC 修改。

    Args:
        rhs: 右端场 (Ny, Nx)，调用前为 Dirichlet 基底，原地修改。
        psi: 当前场 (Ny, Nx)，用于提取边界节点值。
        ky_top: 上边界外向波数 (Nx,)，Re ≥ 0。
        ky_bottom: 下边界外向波数 (Nx,)，Re ≥ 0。
        dy: y 方向网格间距。
        alpha_rhs: 复系数 (1-θ)·Δz/a。
        inv_dy2: 1/Δy²（预计算）。
    """
    extrap_top = np.exp(1j * ky_top * dy)  # (Nx,)
    extrap_bottom = np.exp(1j * ky_bottom * dy)  # (Nx,)
    rhs[0, :] += alpha_rhs * inv_dy2 * extrap_top * psi[0, :]
    rhs[-1, :] += alpha_rhs * inv_dy2 * extrap_bottom * psi[-1, :]


@dataclass
class AdiStepper2D:
    """2D ADI 步进器（A03 §4.3 公式 F3，Peaceman & Rachford 1955）。

    预构造 lhs_x_base（per-row Dirichlet 基底）与 lhs_y_base（per-col 基底），
    z 步进中复用（A03 §8.3 性能策略）。TBC 模式每步 copy 基底 + 修改边界。

    Attributes:
        lhs_x_base: per-row M_lhs = I - α_lhs·Ax 基底 (Ny, 3, Nx) 复数。
        lhs_y_base: per-col M_lhs = I - α_lhs·Ay 基底 (Nx, 3, Ny) 复数。
        main_x: Ax 主对角 (Ny, Nx)，含 -2/Δx² + b。
        main_y: Ay 主对角 (Ny, Nx)，含 -2/Δy² + b。
        off_x: 1/Δx²。
        off_y: 1/Δy²。
        alpha_lhs: 复系数 θ·Δz/a。
        alpha_rhs: 复系数 (1-θ)·Δz/a。
        dx, dy: 网格间距。
        boundary: 边界类型。
        n_uniform_in_y: n 是否沿 y 均匀（1D n）→ x 隐式半步可批处理。
    """

    lhs_x_base: np.ndarray
    lhs_y_base: np.ndarray
    main_x: np.ndarray
    main_y: np.ndarray
    off_x: float
    off_y: float
    alpha_lhs: complex
    alpha_rhs: complex
    dx: float
    dy: float
    boundary: str = BoundaryType.TBC
    n_uniform_in_y: bool = False

    def __post_init__(self) -> None:
        if self.lhs_x_base.ndim != 3 or self.lhs_x_base.shape[1] != 3:
            raise ValueError(f"lhs_x_base 须为 (Ny, 3, Nx)，实际 shape={self.lhs_x_base.shape}")
        if self.lhs_y_base.ndim != 3 or self.lhs_y_base.shape[1] != 3:
            raise ValueError(f"lhs_y_base 须为 (Nx, 3, Ny)，实际 shape={self.lhs_y_base.shape}")
        if self.dx <= 0.0 or self.dy <= 0.0:
            raise ValueError(f"dx/dy 必须为正，实际 dx={self.dx}, dy={self.dy}")
        if self.boundary not in (
            BoundaryType.TBC,
            BoundaryType.DIRICHLET,
            BoundaryType.NEUMANN,
        ):
            raise ValueError(f"boundary 须为 'tbc'/'dirichlet'/'neumann'，实际 {self.boundary!r}")

    @staticmethod
    def _validate_from_grid_inputs(
        n_arr_c: np.ndarray, dz: float, a_coef: complex, theta: float
    ) -> None:
        """校验 from_grid 输入参数。

        Args:
            n_arr_c: 已复数化的折射率数组。
            dz: z 方向步长（米）。
            a_coef: SVEA 系数 a = 2i·k₀·n_ref。
            theta: CN 权重。

        Raises:
            ValueError: 输入非法（规则 14）。
        """
        if dz <= 0.0:
            raise ValueError(f"dz 必须为正，实际 {dz}")
        if abs(a_coef) < 1e-300:
            raise ValueError(f"a_coef 过小 |a|={abs(a_coef):.2e}")
        if not 0.0 <= theta <= 1.0:
            raise ValueError(f"theta 须 ∈ [0, 1]，实际 {theta}")
        # 统一为 2D (Ny, Nx)。1D n_arr (Nx,) 沿 y 均匀时由调用方（adi_propagate_2d）
        # 展开为 2D (Ny, Nx) 后传入；直接传 1D 会因 Ny=1 导致 lhs_y_base 次对角
        # 切片 [:, 0, 1:] 为空，广播后全零，丢失 y 方向拉普拉斯耦合（M1 发散）。
        if n_arr_c.ndim == 1:
            raise ValueError(
                "from_grid 须传入 2D n_arr (Ny, Nx)；1D n_arr (Nx,) 请先由 "
                "adi_propagate_2d 自动展开为 (Ny, Nx)，或调用方自行 np.broadcast_to 展开"
                "（规则 14：禁止 fall-back 构造残缺算子）"
            )
        if n_arr_c.ndim != 2:
            raise ValueError(f"n_arr 须为 2D (Ny, Nx)，实际 {n_arr_c.ndim}D")
        ny, nx = n_arr_c.shape
        if nx < 3:
            raise ValueError(f"n_arr x 维度须 ≥3，实际 {nx}")
        if ny < 3:
            raise ValueError(f"n_arr y 维度须 ≥3，实际 {ny}")

    @staticmethod
    def _compute_main_diagonals(
        n_2d: np.ndarray, k0: float, n_ref: float, dx: float, dy: float
    ) -> tuple[np.ndarray, np.ndarray, float, float, np.ndarray]:
        """计算 Ax/Ay 主对角与折射率项。

        折射率项 b[j, i] = k₀²·(n² - n_ref²)（向量化）。
        Ax 主对角：-2/Δx² + b；Ay 主对角：-2/Δy² + b。

        Args:
            n_2d: 2D 折射率 (Ny, Nx) complex128。
            k0: 真空波数。
            n_ref: 参考折射率。
            dx, dy: x/y 方向网格间距（米）。

        Returns:
            (main_x, main_y, off_x, off_y, b_field):
                main_x/main_y: Ax/Ay 主对角 (Ny, Nx)。
                off_x/off_y: 1/Δx², 1/Δy²。
                b_field: 折射率项 (Ny, Nx)。
        """
        b_field = k0 * k0 * (n_2d * n_2d - n_ref * n_ref)
        off_x = 1.0 / (dx * dx)
        off_y = 1.0 / (dy * dy)
        main_x = -2.0 * off_x + b_field
        main_y = -2.0 * off_y + b_field
        return main_x, main_y, off_x, off_y, b_field

    @staticmethod
    def _build_lhs_x_base(
        main_x: np.ndarray, nx: int, alpha_lhs: complex, off_x: float
    ) -> np.ndarray:
        """构造 per-row lhs_x_base (Ny, 3, Nx)，Dirichlet 基底。

        TM 形式下次/上对角非均匀（含调和平均），此处按 TE 处理次对角为常数 off_x
        （TM 2D 严格实现留待后续 Sprint，当前 TE/Scalar 已覆盖 A03 弱导主场景）。

        Args:
            main_x: Ax 主对角 (Ny, Nx)，含 -2/Δx² + b。
            nx: x 方向网格数。
            alpha_lhs: 复系数 θ·Δz/a。
            off_x: 1/Δx²（标量）。

        Returns:
            lhs_x_base (Ny, 3, Nx) complex128。
        """
        lhs_x_base = np.zeros((main_x.shape[0], 3, nx), dtype=np.complex128)
        lhs_x_base[:, 0, 1:] = -alpha_lhs * off_x  # 上次对角（广播 over Ny）
        lhs_x_base[:, 1, :] = 1.0 - alpha_lhs * main_x  # 主对角
        lhs_x_base[:, 2, :-1] = -alpha_lhs * off_x  # 下次对角（广播 over Ny）
        return lhs_x_base

    @staticmethod
    def _build_lhs_y_base(
        main_y: np.ndarray, alpha_lhs: complex, off_y: float
    ) -> np.ndarray:
        """构造 per-col lhs_y_base (Nx, 3, Ny)，Dirichlet 基底。

        注意维度转置：per-col 算子沿 y 作用，主对角为 main_y[:, i] 即 main_y.T[i, :]。

        Args:
            main_y: Ay 主对角 (Ny, Nx)，含 -2/Δy² + b。
            alpha_lhs: 复系数 θ·Δz/a。
            off_y: 1/Δy²（标量）。

        Returns:
            lhs_y_base (Nx, 3, Ny) complex128。
        """
        nx = main_y.shape[1]
        lhs_y_base = np.zeros((nx, 3, main_y.shape[0]), dtype=np.complex128)
        lhs_y_base[:, 0, 1:] = -alpha_lhs * off_y  # 上次对角（广播 over Nx）
        lhs_y_base[:, 1, :] = 1.0 - alpha_lhs * main_y.T  # 主对角 (Nx, Ny)
        lhs_y_base[:, 2, :-1] = -alpha_lhs * off_y  # 下次对角
        return lhs_y_base

    @classmethod
    def from_grid(
        cls,
        n_arr: np.ndarray,
        dx: float,
        dy: float,
        dz: float,
        a_coef: complex,
        k0: float,
        n_ref: float,
        theta: float = DEFAULT_THETA,
        polarization: str = Polarization.TE,
        boundary: str = BoundaryType.TBC,
    ) -> AdiStepper2D:
        """由 2D 折射率网格构造 ADI 步进器（预计算基底 + 模板）。

        Args:
            n_arr: 折射率分布，2D (Ny, Nx)，Ny/Nx 均 ≥3。
                沿 y 均匀的 1D n_arr (Nx,) 请先用 adi_propagate_2d（自动展开）
                或调用方自行 np.broadcast_to 展开为 (Ny, Nx) 后传入。
            dx, dy: x/y 方向网格间距（米）。
            dz: z 方向步长（米）。
            a_coef: SVEA 系数 a = 2i·k₀·n_ref。
            k0: 真空波数。
            n_ref: 参考折射率。
            theta: CN 权重（默认 0.5）。
            polarization: 偏振模式 'te'/'tm'/'scalar'。
            boundary: 边界类型。

        Returns:
            AdiStepper2D 实例。

        Raises:
            ValueError: 输入非法（规则 14）。
        """
        n_arr_c = np.asarray(n_arr, dtype=np.complex128)
        cls._validate_from_grid_inputs(n_arr_c, dz, a_coef, theta)
        n_2d = n_arr_c
        nx = n_2d.shape[1]
        main_x, main_y, off_x, off_y, _b_field = cls._compute_main_diagonals(
            n_2d, k0, n_ref, dx, dy
        )
        alpha_lhs = theta * dz / a_coef
        alpha_rhs = (1.0 - theta) * dz / a_coef
        lhs_x_base = cls._build_lhs_x_base(main_x, nx, alpha_lhs, off_x)
        lhs_y_base = cls._build_lhs_y_base(main_y, alpha_lhs, off_y)
        return cls(
            lhs_x_base=lhs_x_base, lhs_y_base=lhs_y_base,
            main_x=main_x, main_y=main_y, off_x=off_x, off_y=off_y,
            alpha_lhs=alpha_lhs, alpha_rhs=alpha_rhs,
            dx=dx, dy=dy, boundary=boundary, n_uniform_in_y=False,
        )

    def step(self, psi: np.ndarray) -> np.ndarray:
        """单步 ADI 推进 ψ^n → ψ^{n+1}（A03 §4.3 公式 F3，两个半步）。

        Args:
            psi: 当前场 ψ^n (Ny, Nx)。

        Returns:
            下一步场 ψ^{n+1} (Ny, Nx)。

        Raises:
            RuntimeError: 三对角求解失败（规则 14）。
            ValueError: 形状不匹配或 TBC 退化。
        """
        psi_c = np.asarray(psi, dtype=np.complex128)
        if psi_c.ndim != 2:
            raise ValueError(f"psi 须为 2D (Ny, Nx)，实际 {psi_c.ndim}D")
        ny, nx = psi_c.shape
        if (nx,) != (self.lhs_x_base.shape[2],):
            raise ValueError(f"psi x 维度 {nx} 与 lhs_x_base {self.lhs_x_base.shape[2]} 不匹配")

        # === 半步 1（x 隐式）: ψ^{n+1/2} = [I - α_lhs·Ax]⁻¹·[I + α_rhs·Ay]·ψ^n ===
        # 右端：rhs1 = ψ + α_rhs·(Ay @ ψ)（向量化模板）
        rhs1 = psi_c + self.alpha_rhs * _apply_y_stencil(psi_c, self.main_y, self.off_y)

        # 左侧矩阵准备
        if self.boundary == BoundaryType.TBC:
            lhs_x = self.lhs_x_base.copy()
            # 调整 lhs_x 维度匹配实际 psi 的 ny（n_uniform_in_y 时 lhs_x_base 可能是 (1, 3, Nx)）
            if lhs_x.shape[0] != ny:
                lhs_x = np.broadcast_to(lhs_x, (ny, 3, nx)).copy()
            # 2D TBC 沿 x（LHS）：逐行估计 kₓ，向量化修改左/右边界
            kx_left, kx_right = _estimate_kx_boundaries_2d(psi_c, self.dx)
            _apply_tbc_2d_x_inplace(lhs_x, kx_left, kx_right, self.dx, self.alpha_lhs, self.off_x)
            # RHS TBC 修改（Bug 5 修复）：rhs1 显式算子为 Ay，须对 y 边界（上/下）TBC，
            # 使基底与 LHS 一致（否则边界行 Dirichlet 基底导致反射）
            ky_top, ky_bottom = _estimate_ky_boundaries_2d(psi_c, self.dy)
            _apply_tbc_2d_y_rhs_inplace(
                rhs1, psi_c, ky_top, ky_bottom, self.dy, self.alpha_rhs, self.off_y
            )
        else:
            lhs_x = self.lhs_x_base
            if lhs_x.shape[0] != ny:
                lhs_x = np.broadcast_to(lhs_x, (ny, 3, nx))

        # 三对角求解（沿行循环，A03 §8.3 允许的 solve_banded 行循环）
        psi_half = np.empty((ny, nx), dtype=np.complex128)
        for j in range(ny):
            try:
                psi_half[j] = scipy.linalg.solve_banded((1, 1), lhs_x[j], rhs1[j])
            except np.linalg.LinAlgError as exc:
                raise RuntimeError(f"ADI x 隐式半步行 {j} 求解失败：{exc}") from exc

        # === 半步 2（y 隐式）: ψ^{n+1} = [I - α_lhs·Ay]⁻¹·[I + α_rhs·Ax]·ψ^{n+1/2} ===
        rhs2 = psi_half + self.alpha_rhs * _apply_x_stencil(psi_half, self.main_x, self.off_x)

        if self.boundary == BoundaryType.TBC:
            lhs_y = self.lhs_y_base.copy()
            # n 沿 y 均匀时 lhs_y_base 为 (Nx, 3, 1)，需广播到实际 (Nx, 3, Ny) 才能逐列求解
            if lhs_y.shape[2] != ny:
                lhs_y = np.broadcast_to(lhs_y, (nx, 3, ny)).copy()
            # 2D TBC 沿 y（LHS）：逐列估计 k_y，向量化修改上/下边界
            ky_top, ky_bottom = _estimate_ky_boundaries_2d(psi_half, self.dy)
            _apply_tbc_2d_y_inplace(lhs_y, ky_top, ky_bottom, self.dy, self.alpha_lhs, self.off_y)
            # RHS TBC 修改（Bug 5 修复）：rhs2 显式算子为 Ax，须对 x 边界（左/右）TBC，
            # 使基底与 LHS 一致（否则边界行 Dirichlet 基底导致反射）
            kx_left, kx_right = _estimate_kx_boundaries_2d(psi_half, self.dx)
            _apply_tbc_2d_x_rhs_inplace(
                rhs2, psi_half, kx_left, kx_right, self.dx, self.alpha_rhs, self.off_x
            )
        else:
            lhs_y = self.lhs_y_base
            # n 沿 y 均匀时广播到实际 Ny（read-only 视图，solve_banded 仅读取）
            if lhs_y.shape[2] != ny:
                lhs_y = np.broadcast_to(lhs_y, (nx, 3, ny))

        psi_next = np.empty((ny, nx), dtype=np.complex128)
        for i in range(nx):
            try:
                psi_next[:, i] = scipy.linalg.solve_banded((1, 1), lhs_y[i], rhs2[:, i])
            except np.linalg.LinAlgError as exc:
                raise RuntimeError(f"ADI y 隐式半步列 {i} 求解失败：{exc}") from exc
        return psi_next


def _validate_adi_propagate_inputs(
    psi_init: np.ndarray, nz: int, store_interval: int
) -> np.ndarray:
    """校验 adi_propagate_2d 输入并返回复数化 psi_init。

    Args:
        psi_init: 初始场 ψ(z=0) (Ny, Nx)，复数。
        nz: z 方向步数。
        store_interval: 快照存储间隔。

    Returns:
        psi_init_c: 复数化的初始场 (Ny, Nx) complex128。

    Raises:
        ValueError: 输入非法（规则 14）。
    """
    psi_init_c = np.asarray(psi_init, dtype=np.complex128)
    if psi_init_c.ndim != 2:
        raise ValueError(f"psi_init 须为 2D，实际 {psi_init_c.ndim}D")
    if nz < 1:
        raise ValueError(f"nz 须 ≥1，实际 {nz}")
    if store_interval < 1:
        raise ValueError(f"store_interval 须 ≥1，实际 {store_interval}")
    return psi_init_c


def _broadcast_n_arr_2d(n_arr: np.ndarray, ny: int, nx: int) -> np.ndarray:
    """将 n_arr 统一为 2D (Ny, Nx)（沿 y 均匀时展开）。

    1D n_arr (Nx,) 沿 y 均匀时展开为 2D (Ny, Nx)，使 from_grid 构造的
    lhs_y_base (Nx, 3, Ny) 含正确的次对角耦合（1/Δy²·∂²/∂y²）。
    若保留 Ny=1 基底再广播，次对角切片 [:, 0, 1:] 为空，广播后全零，
    丢失 y 方向拉普拉斯耦合导致发散（M1 失败）。

    Args:
        n_arr: 折射率分布，1D (Nx,) 或 2D (Ny, Nx)。
        ny, nx: psi_init 的形状。

    Returns:
        2D n_arr (Ny, Nx)。

    Raises:
        ValueError: 形状不匹配或维度非法（规则 14）。
    """
    n_arr_c = np.asarray(n_arr, dtype=np.complex128)
    if n_arr_c.ndim == 1:
        if n_arr_c.shape[0] != nx:
            raise ValueError(
                f"1D n_arr 长度 {n_arr_c.shape[0]} 与 psi_init x 维度 {nx} 不匹配（规则 14）"
            )
        return np.broadcast_to(n_arr_c, (ny, nx)).copy()
    if n_arr_c.ndim == 2:
        if n_arr_c.shape != (ny, nx):
            raise ValueError(
                f"2D n_arr 形状 {n_arr_c.shape} 与 psi_init {(ny, nx)} 不匹配（规则 14）"
            )
        return n_arr_c
    raise ValueError(f"n_arr 须为 1D 或 2D，实际 {n_arr_c.ndim}D（规则 14）")


def _init_snapshots(
    psi_init_c: np.ndarray, nz: int, store_interval: int
) -> tuple[np.ndarray, np.ndarray]:
    """初始化快照数组与 z 坐标数组。

    Args:
        psi_init_c: 复数化初始场 (Ny, Nx)。
        nz: z 方向步数。
        store_interval: 快照存储间隔。

    Returns:
        (snapshots, z_coords): snapshots (N_snapshots, Ny, Nx) complex128,
        z_coords (N_snapshots,) float64。snapshots[0]=psi_init_c, z_coords[0]=0.0。
    """
    ny, nx = psi_init_c.shape
    n_snapshots = nz // store_interval + 1
    snapshots = np.empty((n_snapshots, ny, nx), dtype=np.complex128)
    z_coords = np.empty(n_snapshots, dtype=np.float64)
    snapshots[0] = psi_init_c
    z_coords[0] = 0.0
    return snapshots, z_coords


def _run_adi_propagate_loop(
    stepper: AdiStepper2D,
    psi_init_c: np.ndarray,
    nz: int,
    dz: float,
    store_interval: int,
    snapshots: np.ndarray,
    z_coords: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """执行 z 步进主循环并填充快照数组。

    Args:
        stepper: 已构造的 ADI 步进器。
        psi_init_c: 复数化初始场 (Ny, Nx)。
        nz: z 方向步数。
        dz: z 方向步长（米）。
        store_interval: 快照存储间隔。
        snapshots: 预分配快照数组（snapshots[0] 已填）。
        z_coords: 预分配 z 坐标数组（z_coords[0]=0.0 已填）。

    Returns:
        (snapshots, z_coords): 截断至实际写入长度的快照与坐标。
    """
    n_snapshots = snapshots.shape[0]
    psi = psi_init_c.copy()
    snap_idx = 1
    # z 步进主循环（python代码开发规则.md §4 唯一允许循环）
    for n in range(nz):
        psi = stepper.step(psi)
        z_now = (n + 1) * dz
        if (n + 1) % store_interval == 0:
            if snap_idx >= n_snapshots:
                break
            snapshots[snap_idx] = psi
            z_coords[snap_idx] = z_now
            snap_idx += 1
    if snap_idx < n_snapshots:
        snapshots[snap_idx] = psi
        z_coords[snap_idx] = nz * dz
        snap_idx += 1
    return snapshots[:snap_idx], z_coords[:snap_idx]


def adi_propagate_2d(
    psi_init: np.ndarray,
    n_arr: np.ndarray,
    dx: float,
    dy: float,
    dz: float,
    nz: int,
    a_coef: complex,
    k0: float,
    n_ref: float,
    theta: float = DEFAULT_THETA,
    polarization: str = Polarization.TE,
    boundary: str = BoundaryType.TBC,
    store_interval: int = 1,
) -> tuple[np.ndarray, np.ndarray]:
    """2D ADI 主循环（A03 §7.2 伪代码）。

    Args:
        psi_init: 初始场 ψ(z=0) (Ny, Nx)，复数。
        n_arr: 折射率分布，1D (Nx,) 沿 y 均匀，或 2D (Ny, Nx)。
        dx, dy: x/y 方向网格间距（米）。
        dz: z 方向步长（米）。
        nz: z 方向步数。
        a_coef: SVEA 系数 a = 2i·k₀·n_ref。
        k0: 真空波数。
        n_ref: 参考折射率。
        theta: CN 权重（默认 0.5）。
        polarization: 偏振模式。
        boundary: 边界类型。
        store_interval: 快照存储间隔。

    Returns:
        (snapshots, z_coords):
            snapshots: (N_snapshots, Ny, Nx) 复数场快照。
            z_coords: (N_snapshots,) z 坐标（米）。

    Raises:
        ValueError: 输入非法（规则 14）。
        RuntimeError: 求解发散或 TBC 退化。

    算法复杂度：O(nz · (Nx·Ny))（每步两次三对角求解循环 + 向量化模板）。
    """
    psi_init_c = _validate_adi_propagate_inputs(psi_init, nz, store_interval)
    ny, nx = psi_init_c.shape
    n_arr_use = _broadcast_n_arr_2d(n_arr, ny, nx)
    stepper = AdiStepper2D.from_grid(
        n_arr=n_arr_use, dx=dx, dy=dy, dz=dz, a_coef=a_coef, k0=k0, n_ref=n_ref,
        theta=theta, polarization=polarization, boundary=boundary,
    )
    snapshots, z_coords = _init_snapshots(psi_init_c, nz, store_interval)
    return _run_adi_propagate_loop(
        stepper, psi_init_c, nz, dz, store_interval, snapshots, z_coords
    )
