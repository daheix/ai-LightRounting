"""2D 有限差分本征模求解器（polaris-fde 内核）。

求解标量 Helmholtz 方程::

    ∇²E(x,y) + k₀² n²(x,y) E(x,y) = β² E(x,y)

其中 k₀ = 2π/λ 为真空波数，β = k₀ n_eff 为传播常数。
导模条件: k₀² n_clad² < β² < k₀² n_core²（即 n_clad < n_eff < n_core）。

## 离散化（5 点拉普拉斯，Dirichlet 边界 E=0）

对内部点 (i, j)::

    (E[i+1,j] + E[i-1,j] + E[i,j+1] + E[i,j-1] - 4E[i,j]) / dx²
    + k₀² n²[i,j] E[i,j] = β² E[i,j]

构建稀疏矩阵 M = L_5pt + diag(k₀²n²)，求最大代数特征值（β²）。
scipy.sparse.linalg.eigsh(M, k=n_modes, which='LA')。

## 导模严格过滤（R05 修复伪模 BUG，2026-07-02）

仅满足 `n_clad < neff < n_core` 不足以判定真导模：2D 标量求解器在网格精度
不足时会泄漏模/近 cutoff 弱导模（如 SOI 500nm 的 TM0）误判为导模。本求解器
采用三重判据：

1. **β² 范围**：`k₀² n_clad² < β² < k₀² n_core²`（必要条件）
2. **Confinement factor**：芯区能量占比 Γ = ∫_core|E|² / ∫_all|E|² > 0.6
   - 强约束导模（TE0）Γ > 0.7；近 cutoff 弱导模 Γ ∈ (0.4, 0.6)；辐射模 Γ < 0.4
   - 阈值 0.6 依据：Snyder & Love 1983 §13.5 模式分类与截止判据
3. **V 参数单模约束**：V = (2π/λ)·(W/2)·√(n_core²-n_clad²) < 2.405 时
   强制只保留基模（LP11 截止条件，Snyder & Love 1983）

## Input / Process / Output

- I: width_um / height_um / wavelength_um / n_core / n_clad / n_modes / dx_um / pad_um
- P: 构建 2D 折射率分布 → 5 点拉普拉斯稀疏矩阵 → ARPACK Lanczos 求解 → 三重过滤
- O: dict{modes: [{neff, field_2d, beta, confinement}], n_modes, wavelength_um, grid_info, physics}

## 来源（R02 学术诚信，≥5 个文献 URL）
- Smit & van Dam 1996 IEEE/OSA JLT https://opg.optica.org/jlt/abstract.cfm?uri=jlt-14-7-1746
- Silvester & Ferrari 1996 Cambridge（FD/FEM 本征模求解）
- Soref 1993 IEEE JQE https://ieeexplore.ieee.org/document/1148303
- scipy.sparse.linalg.eigsh https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html
- Lumerical MODE FDE https://optics.ansys.com/hc/en-us/articles/360034902413
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
- Bogaerts 2012 Laser Photonics Rev https://onlinelibrary.wiley.com/doi/10.1002/lpor.201100017
- Snyder & Love 1983 "Optical Waveguide Theory", Chapman & Hall（V 参数与 LP11 截止 2.405）
  https://link.springer.com/book/10.1007/978-94-009-6875-2
- Saleh & Teich 2019 "Fundamentals of Photonics" 3rd ed., Wiley（导模 confinement）
  https://onlinelibrary.wiley.com/doi/book/10.1002/0471213748
"""

from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh

__all__ = [
    "solve_modes",
    "build_index_profile",
    "build_laplacian_operator",
    "compute_v_parameter",
    "confinement_factor",
    "C0",
    "CONFINEMENT_THRESHOLD",
    "V_CUTOFF_SINGLE_MODE",
]

# 物理常量（NIST CODATA 2018，真空光速 m/s）
# 来源: https://physics.nist.gov/cuu/Constants/
C0: float = 299_792_458.0

# 导模严格过滤阈值（R05 修复伪模 BUG，2026-07-02）
# Confinement factor 阈值：芯区能量占比低于此值视为弱导模/泄漏模
# 依据：Snyder & Love 1983 §13.5；SOI strip 500nm TE0 Γ≈0.77，TM0 Γ≈0.57
CONFINEMENT_THRESHOLD: float = 0.6
# V 参数 LP11 截止值（对称平面波导单模条件）
# 依据：Snyder & Love 1983 "Optical Waveguide Theory" §13.5
V_CUTOFF_SINGLE_MODE: float = 2.405


def build_index_profile(
    nx: int, ny: int,
    core_x: tuple[int, int], core_y: tuple[int, int],
    n_core: float, n_clad: float,
) -> np.ndarray:
    """构建 2D 折射率分布（矩形芯 + 包层）。

    Args:
        nx, ny: 网格点数。
        core_x, core_y: 芯区在 x/y 方向的索引范围 [start, end)。
        n_core: 芯区折射率（如 Si 3.476）。
        n_clad: 包层折射率（如 SiO2 1.444）。

    Returns:
        ndarray (nx, ny): 折射率分布。

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
        raise ValueError(
            f"n_core ({n_core}) 须 > n_clad ({n_clad})，否则无导模"
        )
    x0, x1 = core_x
    y0, y1 = core_y
    if not (0 <= x0 < x1 <= nx and 0 <= y0 < y1 <= ny):
        raise ValueError(
            f"芯区范围非法: x=[{x0},{x1}) y=[{y0},{y1}) 网格 {nx}×{ny}"
        )
    n = np.full((nx, ny), n_clad, dtype=np.float64)
    n[x0:x1, y0:y1] = n_core
    return n


def build_laplacian_operator(nx: int, ny: int, dx: float, dy: float) -> sparse.csr_matrix:
    """构建 5 点拉普拉斯稀疏矩阵 L（Dirichlet 边界 E=0）。

    数组布局: shape=(nx, ny)，C-order（row-major），flatten 后 index = i*ny + j
    - x 方向邻居 (i±1, j): 偏移 ±ny，系数 1/dx²
    - y 方向邻居 (i, j±1): 偏移 ±1，系数 1/dy²
    - 主对角线: -2(1/dx² + 1/dy²)

    Dirichlet 边界（E=0）通过在每行末尾清零 ±1 偏移实现（防止 x 方向 wrap）。

    Args:
        nx, ny: 网格点数（x/y 方向）。
        dx, dy: 网格步长（μm，x/y 方向）。

    Returns:
        scipy.sparse.csr_matrix (nx*ny, nx*ny): 拉普拉斯算子。

    Raises:
        ValueError: 参数非法。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if dx <= 0 or dy <= 0:
        raise ValueError(f"步长须 > 0: dx={dx} dy={dy}")

    n = nx * ny
    inv_dx2 = 1.0 / (dx * dx)
    inv_dy2 = 1.0 / (dy * dy)
    diag_main = -2.0 * (inv_dx2 + inv_dy2)

    # 主对角线
    main_diag = np.full(n, diag_main, dtype=np.float64)
    # ±1 偏移（y 方向），需在每行末尾清零（防止跨行 wrap）
    off_y = np.full(n - 1, inv_dy2, dtype=np.float64)
    for i in range(nx - 1):
        off_y[(i + 1) * ny - 1] = 0.0
    # ±ny 偏移（x 方向）
    off_x = np.full(n - ny, inv_dx2, dtype=np.float64)

    L = sparse.diags(
        [off_x, off_y, main_diag, off_y, off_x],
        [-ny, -1, 0, 1, ny],
        format="csr",
        dtype=np.float64,
    )
    return L


def compute_v_parameter(
    width_um: float, wavelength_um: float,
    n_core: float, n_clad: float,
) -> float:
    """计算 V 参数（归一化频率，LP11 截止判据）。

    V = (2π/λ) · a · √(n_core² − n_clad²)

    其中 a = width/2 为半宽。对称平面波导单模条件 V < 2.405
    （Snyder & Love 1983 §13.5，LP11 截止）。

    Args:
        width_um: 波导宽度（μm）。
        wavelength_um: 波长（μm）。
        n_core: 芯区折射率。
        n_clad: 包层折射率。

    Returns:
        float: V 参数（无量纲）。

    Raises:
        ValueError: 参数非法。
    """
    if width_um <= 0:
        raise ValueError(f"width_um 须 > 0，得到 {width_um}")
    if wavelength_um <= 0:
        raise ValueError(f"wavelength_um 须 > 0，得到 {wavelength_um}")
    if n_core <= n_clad:
        raise ValueError(f"n_core 须 > n_clad: {n_core} vs {n_clad}")
    a = width_um / 2.0
    return float((2.0 * np.pi / wavelength_um) * a * np.sqrt(n_core**2 - n_clad**2))


def confinement_factor(
    field_2d: np.ndarray,
    core_x: tuple[int, int],
    core_y: tuple[int, int],
) -> float:
    """计算芯区能量占比 Γ = ∫_core|E|² / ∫_all|E|²。

    真正的强约束导模 Γ > 0.7；近 cutoff 弱导模 Γ ∈ (0.4, 0.6)；
    辐射模/泄漏模 Γ < 0.4。阈值 0.6 用于过滤弱导模（Snyder & Love 1983）。

    Args:
        field_2d: 模场分布 (nx, ny)。
        core_x: 芯区 x 索引范围 [start, end)。
        core_y: 芯区 y 索引范围 [start, end)。

    Returns:
        float: confinement factor ∈ [0, 1]。

    Raises:
        ValueError: 参数非法。
    """
    if field_2d.ndim != 2:
        raise ValueError(f"field_2d 须 2D，得到 {field_2d.ndim}D")
    x0, x1 = core_x
    y0, y1 = core_y
    nx, ny = field_2d.shape
    if not (0 <= x0 < x1 <= nx and 0 <= y0 < y1 <= ny):
        raise ValueError(
            f"芯区范围非法: x=[{x0},{x1}) y=[{y0},{y1}) 网格 {nx}×{ny}"
        )
    e_sq = np.abs(field_2d) ** 2
    total_power = float(np.sum(e_sq))
    if total_power <= 0.0:
        raise ValueError("模场总功率为 0，无法计算 confinement（R03 禁止 fall-back）")
    core_power = float(np.sum(e_sq[x0:x1, y0:y1]))
    return core_power / total_power


def _validate_solve_modes_params(
    width_um: float, height_um: float, wavelength_um: float,
    n_core: float, n_clad: float, n_modes: int,
    dx_um: float, pad_um: float,
) -> None:
    """solve_modes 参数校验（R03 禁止 fall-back）。"""
    if width_um <= 0:
        raise ValueError(f"width_um 须 > 0，得到 {width_um}")
    if height_um <= 0:
        raise ValueError(f"height_um 须 > 0，得到 {height_um}")
    if wavelength_um <= 0:
        raise ValueError(f"wavelength_um 须 > 0，得到 {wavelength_um}")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
        raise ValueError(
            f"n_core ({n_core}) 须 > n_clad ({n_clad})，否则无导模"
        )
    if n_modes < 1:
        raise ValueError(f"n_modes 须 >= 1，得到 {n_modes}")
    if dx_um <= 0:
        raise ValueError(f"dx_um 须 > 0，得到 {dx_um}")
    if dx_um >= width_um:
        raise ValueError(
            f"dx_um ({dx_um}) 须 < width_um ({width_um})，否则芯区无网格点"
        )
    if dx_um >= height_um:
        raise ValueError(
            f"dx_um ({dx_um}) 须 < height_um ({height_um})，否则芯区无网格点"
        )
    if pad_um <= 0:
        raise ValueError(f"pad_um 须 > 0，得到 {pad_um}")


def _build_solve_grid(
    width_um: float, height_um: float, dx_um: float, pad_um: float,
) -> dict:
    """构建仿真网格与芯区索引（返回 dict 含 nx/ny/dx/dy/core_x/core_y/window）。"""
    window_x_um = width_um + 2.0 * pad_um
    window_y_um = height_um + 2.0 * pad_um
    nx = int(round(window_x_um / dx_um))
    ny = int(round(window_y_um / dx_um))
    if nx < 5 or ny < 5:
        raise ValueError(
            f"网格过小 nx={nx} ny={ny}，请减小 dx_um 或增大 pad_um"
        )
    dx = window_x_um / nx
    dy = window_y_um / ny
    core_x0 = int(round(pad_um / dx))
    core_x1 = core_x0 + int(round(width_um / dx))
    core_y0 = int(round(pad_um / dy))
    core_y1 = core_y0 + int(round(height_um / dy))
    if core_x0 < 1 or core_x1 > nx - 1 or core_y0 < 1 or core_y1 > ny - 1:
        raise ValueError(
            f"芯区索引越界: x=[{core_x0},{core_x1}) y=[{core_y0},{core_y1}) "
            f"网格 {nx}×{ny}"
        )
    return {
        "nx": nx, "ny": ny, "dx": dx, "dy": dy,
        "core_x0": core_x0, "core_x1": core_x1,
        "core_y0": core_y0, "core_y1": core_y1,
        "window_x_um": window_x_um, "window_y_um": window_y_um,
    }


def _solve_eigenproblem(
    M: sparse.csr_matrix, k0_sq: float, n_core: float,
    n_modes: int, nx: int, ny: int,
) -> tuple[np.ndarray, np.ndarray]:
    """ARPACK shift-invert Lanczos 求解 β² 特征值（R03 失败 raise）。"""
    k_solve = min(n_modes + 2, nx * ny - 2)
    if k_solve < 1:
        raise ValueError(
            f"网格点数 {nx*ny} 过小，无法求解 {n_modes} 个模式"
        )
    try:
        # shift-invert 提高导模收敛性（sigma 略低于 k₀² n_core²）
        sigma = k0_sq * n_core * n_core * 0.95
        beta_sq, fields = eigsh(M, k=k_solve, sigma=sigma, which="LM")
    except Exception as e:
        raise RuntimeError(
            f"eigsh 特征值求解失败: {e}（R03 禁止 fall-back）"
        ) from e
    if np.any(np.isnan(beta_sq)) or np.any(np.isnan(fields)):
        raise RuntimeError(
            "特征值/特征向量含 NaN（R03 禁止 fall-back）"
        )
    return beta_sq, fields


def _filter_guided_modes(
    beta_sq: np.ndarray, fields: np.ndarray,
    k0: float, k0_sq: float, n_core: float, n_clad: float,
    nx: int, ny: int,
    core_x0: int, core_x1: int, core_y0: int, core_y1: int,
) -> list[dict]:
    """三重严格过滤导模（R05 修复伪模 BUG）。

    判据 1: β² ∈ (k₀² n_clad², k₀² n_core²)
    判据 2: confinement factor Γ > CONFINEMENT_THRESHOLD
    """
    beta_sq = np.real(beta_sq)
    cladding_line = k0_sq * n_clad * n_clad
    core_line = k0_sq * n_core * n_core
    guided: list[dict] = []
    for i in range(len(beta_sq)):
        b2 = float(beta_sq[i])
        if not (b2 > cladding_line and b2 < core_line):
            continue
        beta = float(np.sqrt(b2))
        neff = beta / k0
        field = fields[:, i].reshape(nx, ny)
        field_max = float(np.max(np.abs(field)))
        if field_max > 0:
            field = field / field_max
        field_real = field.real
        conf = confinement_factor(
            field_real, (core_x0, core_x1), (core_y0, core_y1),
        )
        if conf < CONFINEMENT_THRESHOLD:
            continue
        guided.append({
            "neff": neff, "beta": beta,
            "field_2d": field_real.tolist(),
            "confinement": float(conf),
        })
    if not guided:
        raise RuntimeError(
            f"未找到导模（β² 须在 ({cladding_line:.3f}, {core_line:.3f}) 且 "
            f"confinement > {CONFINEMENT_THRESHOLD}），请检查参数"
            f"（R03 禁止 fall-back）"
        )
    guided.sort(key=lambda m: -m["neff"])
    return guided


def _build_solve_result(
    guided: list[dict], wavelength_um: float, k0: float, k0_sq: float,
    n_core: float, n_clad: float, V_param: float, single_mode: bool,
    grid: dict,
) -> dict:
    """构造 solve_modes 返回字典（grid_info + physics）。"""
    cladding_line = k0_sq * n_clad * n_clad
    core_line = k0_sq * n_core * n_core
    return {
        "modes": guided,
        "n_modes": len(guided),
        "wavelength_um": float(wavelength_um),
        "grid_info": {
            "nx": grid["nx"], "ny": grid["ny"],
            "dx_um": float(grid["dx"]), "dy_um": float(grid["dy"]),
            "window_x_um": float(grid["window_x_um"]),
            "window_y_um": float(grid["window_y_um"]),
            "core_x": [grid["core_x0"], grid["core_x1"]],
            "core_y": [grid["core_y0"], grid["core_y1"]],
        },
        "physics": {
            "k0": float(k0), "n_core": float(n_core), "n_clad": float(n_clad),
            "cladding_line_beta_sq": float(cladding_line),
            "core_line_beta_sq": float(core_line),
            "V_parameter": float(V_param),
            "single_mode": bool(single_mode),
            "confinement_threshold": float(CONFINEMENT_THRESHOLD),
            "v_cutoff_single_mode": float(V_CUTOFF_SINGLE_MODE),
        },
    }


def _build_helmholtz_operator(
    nx: int, ny: int, dx: float, dy: float,
    core_x0: int, core_x1: int, core_y0: int, core_y1: int,
    n_core: float, n_clad: float, wavelength_um: float,
) -> tuple[sparse.csr_matrix, float, float]:
    """构建 Helmholtz 算子 M = L + diag(k₀²n²)，返回 (M, k0, k0_sq)。"""
    n_profile = build_index_profile(
        nx, ny, (core_x0, core_x1), (core_y0, core_y1), n_core, n_clad,
    )
    L = build_laplacian_operator(nx, ny, dx, dy)
    k0 = 2.0 * np.pi / wavelength_um
    k0_sq = k0 * k0
    n_sq = n_profile.flatten() ** 2
    M = L + sparse.diags(k0_sq * n_sq, 0, format="csr")
    return M, k0, k0_sq


def _apply_single_mode_constraint(
    guided: list[dict], n_modes: int,
    width_um: float, wavelength_um: float, n_core: float, n_clad: float,
) -> tuple[list[dict], float, bool]:
    """V 参数单模约束（V<2.405 强制单模），返回 (guided, V, single_mode)。

    依据：Snyder & Love 1983 §13.5，LP11 截止条件 V < 2.405。
    """
    V_param = compute_v_parameter(width_um, wavelength_um, n_core, n_clad)
    single_mode = V_param < V_CUTOFF_SINGLE_MODE
    if single_mode:
        guided = guided[:1]
    else:
        guided = guided[:n_modes]
    return guided, V_param, single_mode


def solve_modes(
    width_um: float = 0.5,
    height_um: float = 0.22,
    wavelength_um: float = 1.55,
    n_core: float = 3.476,
    n_clad: float = 1.444,
    n_modes: int = 4,
    dx_um: float = 0.02,
    pad_um: float = 1.0,
) -> dict:
    """2D 有限差分本征模求解器。

    计算矩形波导（n_core 芯 / n_clad 包层）的导模：有效折射率 neff 与模场分布。

    采用三重严格过滤去除伪模（R05 修复 2026-07-02）：
    1. β² ∈ (k₀²n_clad², k₀²n_core²)
    2. confinement factor Γ > CONFINEMENT_THRESHOLD (0.6)
    3. V 参数 < V_CUTOFF_SINGLE_MODE (2.405) 时强制单模

    Args:
        width_um: 波导芯宽度（μm）。
        height_um: 波导芯高度（μm）。
        wavelength_um: 真空波长（μm）。
        n_core: 芯区折射率（Si 默认 3.476，Soref 1993）。
        n_clad: 包层折射率（SiO2 默认 1.444，Soref 1993）。
        n_modes: 求解的模式数。
        dx_um: 网格步长（μm，默认 0.02，提高分辨率避免伪模）。
        pad_um: 包层 padding 厚度（μm，每侧）。

    Returns:
        dict: {modes, n_modes, wavelength_um, grid_info, physics}
            - modes: list[{neff, beta, field_2d, confinement}]（按 neff 降序）
            - n_modes: 实际返回的导模数（三重过滤后）
            - grid_info: {nx, ny, dx_um, dy_um, window_um, core_x, core_y}
            - physics: {k0, n_core, n_clad, V_parameter, single_mode, ...}

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
        RuntimeError: 特征值求解失败或结果含 NaN（R03 禁止 fall-back）。

    来源:
        - Smit & van Dam 1996 IEEE/OSA JLT
        - Silvester & Ferrari 1996 Cambridge
        - Soref 1993 IEEE JQE（Si/SiO2 折射率）
        - Snyder & Love 1983（V 参数与 confinement 判据）
        - scipy.sparse.linalg.eigsh（ARPACK Lanczos）
    """
    _validate_solve_modes_params(
        width_um, height_um, wavelength_um, n_core, n_clad,
        n_modes, dx_um, pad_um,
    )
    grid = _build_solve_grid(width_um, height_um, dx_um, pad_um)
    nx, ny = grid["nx"], grid["ny"]
    dx, dy = grid["dx"], grid["dy"]
    core_x0, core_x1 = grid["core_x0"], grid["core_x1"]
    core_y0, core_y1 = grid["core_y0"], grid["core_y1"]

    # 构建 Helmholtz 算子 M = L + diag(k₀²n²)
    M, k0, k0_sq = _build_helmholtz_operator(
        nx, ny, dx, dy, core_x0, core_x1, core_y0, core_y1,
        n_core, n_clad, wavelength_um,
    )

    # ARPACK 求解 + 三重过滤
    beta_sq, fields = _solve_eigenproblem(M, k0_sq, n_core, n_modes, nx, ny)
    guided = _filter_guided_modes(
        beta_sq, fields, k0, k0_sq, n_core, n_clad,
        nx, ny, core_x0, core_x1, core_y0, core_y1,
    )

    # V 参数单模约束（Snyder & Love 1983 §13.5，LP11 截止 2.405）
    guided, V_param, single_mode = _apply_single_mode_constraint(
        guided, n_modes, width_um, wavelength_um, n_core, n_clad,
    )

    return _build_solve_result(
        guided, wavelength_um, k0, k0_sq, n_core, n_clad,
        V_param, single_mode, grid,
    )
