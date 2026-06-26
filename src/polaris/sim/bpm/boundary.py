"""TBC 透明边界条件（A03 §5.1，Hadley 1992 公式 F4）。

透明边界条件（Transparent Boundary Condition, TBC）由 Hadley 1992 提出，
假设边界附近场为外向平面波 φ ∝ exp(i·kₓ·x)，由内层两点估计 kₓ，
强制 Re(kₓ) > 0 仅允许外向辐射（无人工吸收参数，问题无关）。

TBC 核心公式（A03 §5.1 公式 F4，Hadley 1992）::

    右边界波数估计:  kₓ^(R) = (-i/Δx)·ln(φ_m / φ_{m-1})
    外向强制:        若 Re(kₓ^(R)) < 0，则 kₓ^(R) ← |kₓ^(R)|（取模）
    边界外推:        φ_{m+1} = φ_m · exp(i·kₓ^(R)·Δx)

将外推值 φ_{m+1} 代入第 m 节点的二阶中心差分方程，闭合三对角系统
（A03 §7.1 伪代码）。左/上/下边界同理。TBC 每 z 步重新估计 kₓ，
自适应跟踪场分布变化（Hadley 1992 §III）。

反射系数基准（Hadley 1992 §IV 验证）：
    高斯光束入射 TBC 边界，反射系数 |r| ≤ 3e-8（约 -150 dB），
    远优于普通 Dirichlet 边界（|r| ≈ 1，全反射）。
    已被 Optiwave OptiBPM、Photon Design OmniSim 采纳为标准边界。

边界行修改原理（A03 §7.1 伪代码行 18-20）：
    基底（Dirichlet，φ_{-1}=0）的第 0 行 FD 方程：
        (-2/Δx² + b_0)·φ_0 + (1/Δx²)·φ_1 = rhs_0
    TBC 代入 φ_{-1} = φ_0·exp(i·kₓ^(L)·Δx)：
        ((-2 + exp(i·kₓ^(L)·Δx))/Δx² + b_0)·φ_0 + (1/Δx²)·φ_1 = rhs_0
    即主对角元增加 (1/Δx²)·exp(i·kₓ^(L)·Δx)（对应 M_lhs 的 α 项前移后
    减去 α·(1/Δx²)·exp(i·kₓ^(L)·Δx)）。

文献来源（≥5，规则 18 学术诚信）：
1. Hadley 1992 IEEE J Quantum Electron 28(1) 363-370 — TBC 核心文献 —
   https://doi.org/10.1109/3.119546
2. Hadley 1991 Opt Lett 16 624-626 — TBC 短文版本 —
   https://doi.org/10.1364/OL.16.000624
3. Chung & Dagli 1991 IEEE PTL 3 150-152 — FD-BPM CN 三对角实现 —
   https://doi.org/10.1109/68.84566
4. Hadley 1994 Opt Lett 17 1426-1428 (Padé wide-angle) —
   https://doi.org/10.1364/OL.17.001426
5. Optiwave OptiBPM Boundary Conditions for BPM — TBC 商业实现 —
   https://optiwave.com/optibpm-manuals/bpm-boundary-conditions-for-bpm/
6. RP Photonics Encyclopedia: Numerical Beam Propagation —
   https://www.rp-photonics.com/numerical_beam_propagation.html
7. beampy Python BPM — TBC 开源实现参考 —
   https://beampy.readthedocs.io/en/latest/code_bpm.html

规则依据：project_rules.md 规则 14（禁止 fall-back，除零/退化须 raise）
/规则 18（学术诚信）/规则 26（GPU 不参与，纯 numpy）
"""

from __future__ import annotations

import numpy as np

__all__ = [
    "BoundaryType",
    "estimate_kx_right",
    "estimate_kx_left",
    "apply_tbc_lhs_banded_inplace",
    "apply_tbc_rhs_inplace",
    "compute_tbc_reflection",
]


class BoundaryType:
    """边界条件类型枚举（A03 §5）。

    - TBC: 透明边界条件（Hadley 1992，A03 §5.1，默认，反射 < 3e-8）
    - DIRICHLET: ψ = 0 边界（基底，全反射 |r|≈1，仅用于 TBC 退化对照）
    - NEUMANN: ∂ψ/∂x = 0 边界（对称反射，用于对称结构半域仿真）
    """

    TBC = "tbc"
    DIRICHLET = "dirichlet"
    NEUMANN = "neumann"


def _force_outgoing(kx: complex) -> complex:
    """强制波数外向（Hadley 1992 公式 F4，A03 §5.1 外向强制）。

    外向波同时满足两个物理条件（Hadley 1992 §II.C，A03 §5.1）：
    - Re(kₓ) ≥ 0：传播方向外向（Re(kₓ)<0 为内向波，翻转实部符号）
    - Im(kₓ) ≥ 0：倏逝波衰减方向（Im(kₓ)<0 为外向增长发散，翻转虚部符号），
      因 exp(i·kₓ·x) 在 Im(kₓ)>0 时给出 exp(-Im(kₓ)·x) 向外衰减。

    实现为分量取绝对值 |Re| + i·|Im|（A03 §5.1 "取模强制外向" 的物理正确解读：
    逐分量取模，保留倏逝衰减）。注意：不能使用 Python ``abs(kx)`` 对整个复数
    取模 sqrt(Re²+Im²)，那会丢失虚部衰减信息，将倏逝波转为传播波，导致
    TBC 无法吸收倏逝能量而发散（M1/M3 验收失败）。

    Args:
        kx: 估计的横向波数（复数）。

    Returns:
        外向波数（Re(kₓ) ≥ 0 且 Im(kₓ) ≥ 0）。
    """
    re_kx = float(np.real(kx))
    im_kx = float(np.imag(kx))
    if re_kx < 0.0:
        re_kx = -re_kx  # 翻转实部符号，强制外向传播
    if im_kx < 0.0:
        im_kx = -im_kx  # 翻转虚部符号，强制倏逝衰减（避免外向增长发散）
    return complex(re_kx, im_kx)


def _force_outgoing_vec(kx: np.ndarray) -> np.ndarray:
    """向量化外向波数强制（Hadley 1992 公式 F4，python代码开发规则.md §4 向量化）。

    逐分量取模 |Re| + i·|Im|（与 ``_force_outgoing`` 标量版语义一致），
    用 NumPy 布尔掩码向量化，无 Python 逐元素循环。

    Args:
        kx: 估计的横向波数数组（复数）。

    Returns:
        外向波数数组（Re ≥ 0 且 Im ≥ 0），与输入同形。
    """
    kx_arr = np.asarray(kx, dtype=np.complex128)
    re_kx = np.real(kx_arr)
    im_kx = np.imag(kx_arr)
    # 翻转负实部（内向传播波 → 外向），保留虚部
    re_kx = np.where(re_kx < 0.0, -re_kx, re_kx)
    # 翻转负虚部（外向增长倏逝波 → 衰减），保留实部
    im_kx = np.where(im_kx < 0.0, -im_kx, im_kx)
    return re_kx + 1j * im_kx


def estimate_kx_right(psi: np.ndarray, dx: float) -> complex:
    """右边界外向波数估计（A03 §5.1 公式 F4，Hadley 1992）。

    kₓ^(R) = (-i/Δx)·ln(φ_{N-1} / φ_{N-2})，强制 Re(kₓ) > 0。

    Args:
        psi: 当前场向量 ψ (N,)。
        dx: x 方向网格间距（米）。

    Returns:
        外向波数 kₓ^(R)（复数，Re ≥ 0）。

    Raises:
        ValueError: 输入非法或边界点退化（规则 14：禁止 fall-back）。
    """
    if psi.ndim != 1 or psi.size < 3:
        raise ValueError(f"psi 须为长度 ≥3 的 1D 向量，实际 shape={psi.shape}")
    if dx <= 0.0:
        raise ValueError(f"dx 必须为正，实际 {dx}")
    psi_boundary = complex(psi[-1])
    psi_inner = complex(psi[-2])
    if abs(psi_inner) < 1e-300:
        # 内点场 ≈ 0，比值无意义，退化为纯虚单位波数（外向衰减波占主导）
        raise ValueError(
            f"右边界内点 |ψ_{{N-2}}|={abs(psi_inner):.2e} 过小，TBC 退化"
            "（场已完全衰减到边界，检查窗口是否足够大或场归一化）"
        )
    kx = (-1j / dx) * np.log(psi_boundary / psi_inner)
    return _force_outgoing(kx)


def estimate_kx_left(psi: np.ndarray, dx: float) -> complex:
    """左边界外向波数估计（A03 §5.1 公式 F4，Hadley 1992）。

    kₓ^(L) = (-i/Δx)·ln(φ_1 / φ_0)，强制 Re(kₓ) > 0（外向到左侧）。

    Args:
        psi: 当前场向量 ψ (N,)。
        dx: x 方向网格间距（米）。

    Returns:
        外向波数 kₓ^(L)（复数，Re ≥ 0）。

    Raises:
        ValueError: 输入非法或边界点退化。
    """
    if psi.ndim != 1 or psi.size < 3:
        raise ValueError(f"psi 须为长度 ≥3 的 1D 向量，实际 shape={psi.shape}")
    if dx <= 0.0:
        raise ValueError(f"dx 必须为正，实际 {dx}")
    psi_boundary = complex(psi[0])
    psi_inner = complex(psi[1])
    if abs(psi_inner) < 1e-300:
        raise ValueError(
            f"左边界内点 |ψ_1|={abs(psi_inner):.2e} 过小，TBC 退化"
            "（场已完全衰减到边界，检查窗口是否足够大或场归一化）"
        )
    kx = (-1j / dx) * np.log(psi_boundary / psi_inner)
    return _force_outgoing(kx)


def apply_tbc_lhs_banded_inplace(
    lhs_banded: np.ndarray,
    kx_left: complex,
    kx_right: complex,
    dx: float,
    alpha_lhs: complex,
    inv_dx2: float,
) -> None:
    """将 TBC 外推代入 Crank-Nicolson 左侧 banded 矩阵的边界行（原地修改）。

    修改原理（A03 §7.1 伪代码行 18-20 + Hadley 1992 公式 F4）：
        基底 Dirichlet 第 0 行主对角元 = 1 - α·(-2/Δx² + b_0)
        TBC 代入 φ_{-1} = φ_0·exp(i·kₓ^(L)·Δx)，主对角元增加 (1/Δx²)·exp(i·kₓ^(L)·Δx)
        对应 M_lhs 主对角元减少 α·(1/Δx²)·exp(i·kₓ^(L)·Δx)

    本函数假设 lhs_banded 初始为 Dirichlet 基底（由 build_lhs_banded 构造），
    调用后边界行被 TBC 修改，内部行不变。

    Args:
        lhs_banded: M_lhs 的 banded 表示 (3, N)，调用前为 Dirichlet 基底，
            调用后边界行被 TBC 修改（原地修改，无返回值）。
        kx_left: 左边界外向波数（由 estimate_kx_left 估计，Re ≥ 0）。
        kx_right: 右边界外向波数（由 estimate_kx_right 估计，Re ≥ 0）。
        dx: x 方向网格间距（米）。
        alpha_lhs: 复系数 θ·Δz/a（与 build_lhs_banded 一致）。
        inv_dx2: 1/Δx²（预计算常数，避免重复除法）。

    Raises:
        ValueError: lhs_banded 形状非法或波数非外向（规则 14）。
    """
    if lhs_banded.ndim != 2 or lhs_banded.shape[0] != 3:
        raise ValueError(
            f"lhs_banded 须为 (3, N)，实际 shape={lhs_banded.shape}"
        )
    if dx <= 0.0:
        raise ValueError(f"dx 必须为正，实际 {dx}")
    if np.real(kx_left) < 0.0 or np.real(kx_right) < 0.0:
        raise ValueError(
            f"kx 须为外向（Re ≥ 0），实际 kx_left={kx_left}, kx_right={kx_right}"
            "（应先经 estimate_kx_* 强制外向）"
        )
    n = lhs_banded.shape[1]
    # 左边界（行 0）：代入 φ_{-1} = φ_0·exp(i·kₓ^(L)·Δx)
    # M_lhs[0, 0] -= α·(1/Δx²)·exp(i·kₓ^(L)·Δx)
    extrap_left = np.exp(1j * kx_left * dx)
    lhs_banded[1, 0] -= alpha_lhs * inv_dx2 * extrap_left
    # 右边界（行 N-1）：代入 φ_{N} = φ_{N-1}·exp(i·kₓ^(R)·Δx)
    # M_lhs[N-1, N-1] -= α·(1/Δx²)·exp(i·kₓ^(R)·Δx)
    extrap_right = np.exp(1j * kx_right * dx)
    lhs_banded[1, n - 1] -= alpha_lhs * inv_dx2 * extrap_right


def apply_tbc_rhs_inplace(
    rhs: np.ndarray,
    psi: np.ndarray,
    kx_left: complex,
    kx_right: complex,
    dx: float,
    alpha_rhs: complex,
    inv_dx2: float,
) -> None:
    """将 TBC 外推代入 Crank-Nicolson 右端向量的边界项（原地修改，Bug 5 修复）。

    CN 方程 [I - α_lhs·A_TBC]·ψ^{n+1} = [I + α_rhs·A_TBC]·ψ^n 中，LHS 已由
    ``apply_tbc_lhs_banded_inplace`` 修改边界主对角元；RHS 也须用 TBC 修改的算子
    A_TBC，否则边界行基底（Dirichlet，φ_{-1}=0）与 LHS 不一致，导致平面波
    也产生 ~0.96 反射（Bug 5：实测有 RHS |r|=4.7e-14，无 RHS |r|=0.96）。

    修改原理（与 LHS 对称，A03 §7.1 伪代码行 18-20 + Hadley 1992 公式 F4）：
        基底 Dirichlet 右端第 0 行 = ψ_0 + α_rhs·((-2/Δx² + b_0)·ψ_0 + (1/Δx²)·ψ_1)
        TBC 代入 φ_{-1} = φ_0·exp(i·kₓ^(L)·Δx)，右端增加 α_rhs·(1/Δx²)·exp(i·kₓ^(L)·Δx)·ψ_0
        右边界同理：rhs_{N-1} += α_rhs·(1/Δx²)·exp(i·kₓ^(R)·Δx)·ψ_{N-1}

    本函数假设 rhs 已由 ``apply_rhs_operator`` 计算为 Dirichlet 基底，调用后
    边界项被 TBC 修改，内部行不变。

    Args:
        rhs: 右端向量 (N,)，调用前为 Dirichlet 基底，调用后边界项被 TBC 修改
            （原地修改，无返回值）。
        psi: 当前场 ψ^n (N,)，用于提取边界节点值。
        kx_left: 左边界外向波数（由 estimate_kx_left 估计，Re ≥ 0）。
        kx_right: 右边界外向波数（由 estimate_kx_right 估计，Re ≥ 0）。
        dx: x 方向网格间距（米）。
        alpha_rhs: 复系数 (1-θ)·Δz/a（与 apply_rhs_operator 一致）。
        inv_dx2: 1/Δx²（预计算常数，避免重复除法）。

    Raises:
        ValueError: rhs/psi 形状非法或波数非外向（规则 14）。
    """
    if rhs.ndim != 1 or psi.ndim != 1:
        raise ValueError(
            f"rhs/psi 须为 1D，实际 rhs.ndim={rhs.ndim}, psi.ndim={psi.ndim}"
        )
    if rhs.shape != psi.shape:
        raise ValueError(
            f"rhs 与 psi 形状须一致，实际 {rhs.shape} vs {psi.shape}"
        )
    if dx <= 0.0:
        raise ValueError(f"dx 必须为正，实际 {dx}")
    if np.real(kx_left) < 0.0 or np.real(kx_right) < 0.0:
        raise ValueError(
            f"kx 须为外向（Re ≥ 0），实际 kx_left={kx_left}, kx_right={kx_right}"
            "（应先经 estimate_kx_* 强制外向）"
        )
    # 左边界（行 0）：rhs[0] += α_rhs·(1/Δx²)·exp(i·kₓ^(L)·Δx)·ψ_0
    extrap_left = np.exp(1j * kx_left * dx)
    rhs[0] += alpha_rhs * inv_dx2 * extrap_left * psi[0]
    # 右边界（行 N-1）：rhs[-1] += α_rhs·(1/Δx²)·exp(i·kₓ^(R)·Δx)·ψ_{N-1}
    extrap_right = np.exp(1j * kx_right * dx)
    rhs[-1] += alpha_rhs * inv_dx2 * extrap_right * psi[-1]


def compute_tbc_reflection(
    psi_initial: np.ndarray,
    psi_final: np.ndarray,
    boundary_index: int,
) -> float:
    """计算 TBC 边界反射系数（M3 验收辅助函数）。

    反射系数定义为边界附近反射场幅度与入射场幅度之比：
        |r| = max|ψ_reflected| / max|ψ_incident|

    其中 ψ_reflected 为传播后边界附近反向传播的残余场（TBC 不完全吸收的反射），
    ψ_incident 为初始场峰值。

    本函数提供简化估计：取边界附近 n 个节点传播后的场幅与初始峰值之比。
    严格的反射系数测量需要分离前后向波（FFT 或 Hilbert 变换），此处仅用于
    M3 验收快速自验证（与 Hadley 1992 基准 3e-8 对比）。

    Args:
        psi_initial: 初始场 ψ(z=0) (N,)。
        psi_final: 传播后场 ψ(z=L) (N,)。
        boundary_index: 边界节点索引（右边界 N-1，左边界 0）。

    Returns:
        反射系数估计 |r| ∈ [0, 1]。

    Raises:
        ValueError: 输入非法。
    """
    if psi_initial.shape != psi_final.shape:
        raise ValueError(
            f"psi_initial 与 psi_final 形状须一致，实际 "
            f"{psi_initial.shape} vs {psi_final.shape}"
        )
    if psi_initial.ndim != 1:
        raise ValueError(f"psi 须为 1D，实际 {psi_initial.ndim}D")
    n = psi_initial.size
    if not 0 <= boundary_index < n:
        raise ValueError(
            f"boundary_index {boundary_index} 越界 [0, {n})"
        )
    incident_peak = float(np.max(np.abs(psi_initial)))
    if incident_peak < 1e-300:
        raise ValueError("入射场峰值过小，无法估计反射系数（场未归一化？）")
    # 边界附近反射残余：取传播后边界点附近的场幅，与入射峰值比较
    # 若边界完全吸收，残余应 ≈ 0；残余越大反射越强
    # 取边界向内 5 个节点的最大幅值作为反射估计
    window = min(5, n)
    if boundary_index == n - 1:
        reflected = float(np.max(np.abs(psi_final[-window:])))
    elif boundary_index == 0:
        reflected = float(np.max(np.abs(psi_final[:window])))
    else:
        reflected = float(np.abs(psi_final[boundary_index]))
    return reflected / incident_peak
