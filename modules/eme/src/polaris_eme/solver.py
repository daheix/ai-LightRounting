"""本征模展开（EME）求解器（polaris-eme 内核）。

将光子结构沿传播方向 z 切片为多个均匀段，每段求解本地本征模，
界面用模式匹配（重叠积分）计算透射/反射，段内相位传播，级联 S 矩阵。

## 算法

1. **本征模求解**: 对每段截面（1D slab 波导）求前 K 个本征模
   ∇²E + k₀²n²(x)E = β²E，使用 scipy.sparse.linalg.eigsh
2. **段内传播**: P = diag(exp(j·β_i·L))（前向）/ diag(exp(-j·β_i·L))（后向）
3. **界面模式匹配**（E/H 连续性 + 单模 Galerkin 投影，*创新*）:
   场重叠 P = ∫ E_a · E_b* dx（∫|E|²dx=1 归一化）
   TE 导纳 Y=β/ωμ，反射 r=(β_a-β_b)/(β_a+β_b)（阻抗失配）
   透射 t = 2·β_a/(β_a+β_b)·P（β 匹配 × 场重叠）
   注: 单模近似下场失配功率耦合到高阶模（被忽略），不归为反射
4. **S 矩阵级联**: Redheffer 星积 S_total = S_1 ⊗ P_1 ⊗ S_2 ⊗ ... ⊗ S_N

## Input / Process / Output

- I: sections（list[{width_um, length_um, n_core, n_clad}]）/ wavelength_um / n_modes_per_section
- P: 每段 slab 模式求解 → 重叠积分 → 相位传播 → Redheffer 级联
- O: dict{transmission, transmission_db, reflection, s_matrix, sections_info}

## 来源（R02 学术诚信，≥5 个文献 URL）
- Smit & van Dam 1996 IEEE/OSA JLT https://opg.optica.org/jlt/abstract.cfm?uri=jlt-14-7-1746
- Lumerical EME https://optics.ansys.com/hc/en-us/articles/360034902433
- Bienstman 2001 Ghent PhD https://www.photonics.intec.ugent.be/publications/PhD_Bienstman.pdf
- Sztefanka & Kapon 1993 JLT https://ieeexplore.ieee.org/document/247559
- scipy.sparse.linalg.eigsh https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
- Collin, "Foundations for Microwave Engineering" 2001 §5.1（传输线阻抗反射）
  https://ieeexplore.ieee.org/book/5263073
- Marcuse, "Light Transmission Optics" 1981 §8.5（波导模式匹配 E/H 连续性）
  https://onlinelibrary.wiley.com/doi/book/10.1002/9783527619742
"""

from __future__ import annotations

from typing import Any

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh

__all__ = [
    "solve_eme",
    "solve_slab_modes",
    "compute_overlap_1d",
    "propagate_phase",
    "redheffer_star",
]


# =========================================================================
# 1D Slab 波导本征模求解（EME 内部使用，不依赖 polaris_fde）
# =========================================================================

def solve_slab_modes(
    width_um: float,
    wavelength_um: float,
    n_core: float,
    n_clad: float,
    n_modes: int = 4,
    dx_um: float = 0.01,
    pad_um: float = 1.0,
    window_um: float | None = None,
) -> dict:
    """1D slab 波导本征模求解器。

    求解标量 Helmholtz 方程 d²E/dx² + k₀²n²(x)E = β²E（1D 截面）。

    Args:
        width_um: 波导芯宽度（μm）。
        wavelength_um: 波长（μm）。
        n_core: 芯区折射率。
        n_clad: 包层折射率。
        n_modes: 求解模式数。
        dx_um: 网格步长（μm）。
        pad_um: 包层 padding（μm，每侧）。当 window_um 给定时被忽略。
        window_um: 可选，显式指定仿真窗口宽度（μm）。
            用于 EME 多段级联时保证各段网格一致。

    Returns:
        dict: {modes: [{neff, beta, field_1d}], n_modes, grid_info}

    Raises:
        ValueError: 参数非法（R03）。
        RuntimeError: 求解失败（R03）。
    """
    if width_um <= 0:
        raise ValueError(f"width_um 须 > 0，得到 {width_um}")
    if wavelength_um <= 0:
        raise ValueError(f"wavelength_um 须 > 0，得到 {wavelength_um}")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
        raise ValueError(f"n_core ({n_core}) 须 > n_clad ({n_clad})")
    if n_modes < 1:
        raise ValueError(f"n_modes 须 >= 1，得到 {n_modes}")
    if dx_um <= 0:
        raise ValueError(f"dx_um 须 > 0，得到 {dx_um}")
    if dx_um >= width_um:
        raise ValueError(f"dx_um ({dx_um}) 须 < width_um ({width_um})")

    if window_um is None:
        if pad_um <= 0:
            raise ValueError(f"pad_um 须 > 0，得到 {pad_um}")
        win_um = width_um + 2.0 * pad_um
    else:
        if window_um <= width_um:
            raise ValueError(
                f"window_um ({window_um}) 须 > width_um ({width_um})"
            )
        win_um = float(window_um)

    nx = int(round(win_um / dx_um))
    if nx < 5:
        raise ValueError(f"网格过小 nx={nx}，请减小 dx_um 或增大 pad_um")
    dx = win_um / nx

    # 芯区索引（居中放置）
    core_x0 = int(round((win_um - width_um) / 2.0 / dx))
    core_x1 = core_x0 + int(round(width_um / dx))
    if core_x0 < 1 or core_x1 > nx - 1:
        raise ValueError(
            f"芯区索引越界: x=[{core_x0},{core_x1}) 网格 {nx}"
        )

    # 1D 折射率分布
    n_profile = np.full(nx, n_clad, dtype=np.float64)
    n_profile[core_x0:core_x1] = n_core

    # 1D Laplacian（3 点差分，Dirichlet 边界）
    inv_dx2 = 1.0 / (dx * dx)
    main_diag = -2.0 * inv_dx2 * np.ones(nx, dtype=np.float64)
    off_diag = inv_dx2 * np.ones(nx - 1, dtype=np.float64)
    L = sparse.diags(
        [off_diag, main_diag, off_diag],
        [-1, 0, 1],
        format="csr",
        dtype=np.float64,
    )

    # Helmholtz 算子: M = L + diag(k₀² n²)
    k0 = 2.0 * np.pi / wavelength_um
    k0_sq = k0 * k0
    M = L + sparse.diags(k0_sq * n_profile ** 2, 0, format="csr")

    # 求最大代数特征值（导模 β²）
    k_solve = min(n_modes + 2, nx - 2)
    if k_solve < 1:
        raise ValueError(f"网格点数 {nx} 过小，无法求解 {n_modes} 个模式")
    sigma = k0_sq * n_core * n_core * 0.95
    try:
        beta_sq, fields = eigsh(M, k=k_solve, sigma=sigma, which="LM")
    except Exception as e:
        raise RuntimeError(
            f"slab 模式 eigsh 求解失败: {e}（R03 禁止 fall-back）"
        ) from e

    if np.any(np.isnan(beta_sq)) or np.any(np.isnan(fields)):
        raise RuntimeError("特征值/特征向量含 NaN（R03）")

    # 过滤导模 + 功率归一化
    beta_sq = np.real(beta_sq)
    cladding_line = k0_sq * n_clad * n_clad
    core_line = k0_sq * n_core * n_core

    guided: list[dict[str, Any]] = []
    for i in range(len(beta_sq)):
        b2 = float(beta_sq[i])
        if b2 > cladding_line and b2 < core_line:
            beta = float(np.sqrt(b2))
            neff = beta / k0
            field = np.real(fields[:, i])
            # 功率归一化: ∫|E|² dx = 1
            norm = float(np.sqrt(np.sum(np.abs(field) ** 2) * dx))
            if norm > 0:
                field = field / norm
            guided.append({
                "neff": neff,
                "beta": beta,
                "field_1d": field.tolist(),
            })

    if not guided:
        raise RuntimeError(
            f"未找到 slab 导模（R03 禁止 fall-back）"
        )

    guided.sort(key=lambda m: -m["neff"])
    guided = guided[:n_modes]

    return {
        "modes": guided,
        "n_modes": len(guided),
        "grid_info": {
            "nx": nx,
            "dx_um": float(dx),
            "window_um": float(win_um),
            "core_x": [core_x0, core_x1],
        },
    }


# =========================================================================
# 模式匹配（重叠积分）
# =========================================================================

def compute_overlap_1d(
    field_a: np.ndarray | list,
    field_b: np.ndarray | list,
    dx: float,
) -> complex:
    """计算两个 1D 模场的重叠积分 ∫ E_a · E_b* dx。

    用于 EME 界面模式匹配，计算透射系数。

    Args:
        field_a, field_b: 1D 模场数组（已功率归一化）。
        dx: 网格步长（μm）。

    Returns:
        complex: 重叠积分值。

    Raises:
        ValueError: 长度不匹配或参数非法。
    """
    fa = np.asarray(field_a, dtype=np.float64)
    fb = np.asarray(field_b, dtype=np.float64)
    if fa.shape != fb.shape:
        raise ValueError(
            f"模场形状不匹配: {fa.shape} vs {fb.shape}"
        )
    if dx <= 0:
        raise ValueError(f"dx 须 > 0，得到 {dx}")
    # 重叠积分（实数场，conj 无影响，但保留通用形式）
    overlap = float(np.sum(fa * np.conj(fb)) * dx)
    return complex(overlap)


def propagate_phase(beta: float, length_um: float) -> complex:
    """计算单模相位传播因子 exp(j·β·L)。

    Args:
        beta: 传播常数（μm⁻¹）。
        length_um: 传播长度（μm）。

    Returns:
        complex: 相位因子。

    Raises:
        ValueError: 参数非法。
    """
    if length_um < 0:
        raise ValueError(f"length_um 须 >= 0，得到 {length_um}")
    return complex(np.exp(1j * beta * length_um))


# =========================================================================
# Redheffer 星积（S 矩阵级联）
# =========================================================================

def redheffer_star(
    S1: np.ndarray, S2: np.ndarray,
) -> np.ndarray:
    """Redheffer 星积: 级联两个 S 矩阵。

    S = S1 ⊗ S2，用于 EME 多段级联。
    S 矩阵布局（2×2 分块）::
        S = [[S11, S12],   # S11=反射(左), S12=透射(右→左)
             [S21, S22]]   # S21=透射(左→右), S22=反射(右)

    来源: Redheffer 1962 + Bienstman 2001 §2.3。

    Args:
        S1, S2: 2×2 复数 S 矩阵。

    Returns:
        np.ndarray: 级联后的 2×2 S 矩阵。

    Raises:
        ValueError: 形状不匹配。
    """
    S1 = np.asarray(S1, dtype=complex)
    S2 = np.asarray(S2, dtype=complex)
    if S1.shape != (2, 2) or S2.shape != (2, 2):
        raise ValueError(
            f"S 矩阵须 2×2，得到 {S1.shape} 和 {S2.shape}"
        )
    # Redheffer 星积公式（Bienstman 2001 PhD Eq. 2.18，2×2 标量块）
    # S 矩阵布局: [[S11=左反射, S12=右→左透射],
    #             [S21=左→右透射, S22=右反射]]
    # 级联 S = S1 ⊗ S2:
    #   denom = 1 - S1[1,1] * S2[0,0]  (右反射×左反射的多次反射级数)
    #   S11 = S1[0,0] + S1[0,1] * S2[0,0] * S1[1,0] / denom
    #   S12 = S1[0,1] * S2[0,1] / denom
    #   S21 = S2[1,0] * S1[1,0] / denom
    #   S22 = S2[1,1] + S2[1,0] * S1[1,1] * S2[0,1] / denom
    I = 1.0 + 0.0j
    denom = I - S1[1, 1] * S2[0, 0]
    if abs(denom) < 1e-30:
        raise RuntimeError(
            f"Redheffer 分母为零（S1[1,1]·S2[0,0]={S1[1,1]*S2[0,0]}），"
            f"级联奇异（R03 禁止 fall-back）"
        )
    s11 = S1[0, 0] + S1[0, 1] * S2[0, 0] * S1[1, 0] / denom
    s12 = S1[0, 1] * S2[0, 1] / denom
    s21 = S2[1, 0] * S1[1, 0] / denom
    s22 = S2[1, 1] + S2[1, 0] * S1[1, 1] * S2[0, 1] / denom
    return np.array([[s11, s12], [s21, s22]], dtype=complex)


# =========================================================================
# 主 EME 求解器
# =========================================================================

def solve_eme(
    sections: list[dict],
    wavelength_um: float = 1.55,
    n_modes_per_section: int = 2,
    dx_um: float = 0.01,
    pad_um: float = 1.0,
) -> dict:
    """EME 求解器: 多段均匀波导级联。

    每段截面为 1D slab 波导（宽度可变），沿 z 传播。
    段内相位传播，界面模式匹配，Redheffer 星积级联。

    Args:
        sections: 段列表，每段 dict{width_um, length_um, n_core, n_clad}。
        wavelength_um: 波长（μm）。
        n_modes_per_section: 每段求解的模式数（仅取基模做单模级联）。
        dx_um: 横向网格步长（μm）。
        pad_um: 包层 padding（μm）。

    Returns:
        dict: {transmission, transmission_db, reflection, s_matrix, sections_info}

    Raises:
        ValueError: 参数非法（R03）。
        RuntimeError: 求解失败（R03）。

    来源:
        - Smit & van Dam 1996 IEEE/OSA JLT
        - Bienstman 2001 PhD（Redheffer 星积）
        - Lumerical EME 文档
    """
    if not sections:
        raise ValueError("sections 不能为空（R03 禁止 fall-back）")
    if wavelength_um <= 0:
        raise ValueError(f"wavelength_um 须 > 0，得到 {wavelength_um}")
    if n_modes_per_section < 1:
        raise ValueError(f"n_modes_per_section 须 >= 1，得到 {n_modes_per_section}")
    if dx_um <= 0:
        raise ValueError(f"dx_um 须 > 0，得到 {dx_um}")
    if pad_um <= 0:
        raise ValueError(f"pad_um 须 > 0，得到 {pad_um}")

    # 解析每段参数
    parsed: list[dict[str, Any]] = []
    for idx, sec in enumerate(sections):
        if not isinstance(sec, dict):
            raise ValueError(f"段 {idx} 须 dict，得到 {type(sec)}")
        for key in ("width_um", "length_um", "n_core", "n_clad"):
            if key not in sec:
                raise ValueError(f"段 {idx} 缺少必需字段 '{key}'")
        if sec["length_um"] < 0:
            raise ValueError(f"段 {idx} length_um 须 >= 0，得到 {sec['length_um']}")
        parsed.append({
            "width_um": float(sec["width_um"]),
            "length_um": float(sec["length_um"]),
            "n_core": float(sec["n_core"]),
            "n_clad": float(sec["n_clad"]),
        })

    # 1. 每段求解 slab 本征模（仅取基模做单模级联）
    # 计算公共窗口宽度（取最大宽度 + 2*pad），保证各段网格一致
    max_width_um = max(sec["width_um"] for sec in parsed)
    common_window_um = max_width_um + 2.0 * pad_um

    section_data: list[dict[str, Any]] = []
    for idx, sec in enumerate(parsed):
        modes_result = solve_slab_modes(
            width_um=sec["width_um"],
            wavelength_um=wavelength_um,
            n_core=sec["n_core"],
            n_clad=sec["n_clad"],
            n_modes=n_modes_per_section,
            dx_um=dx_um,
            window_um=common_window_um,  # 强制统一窗口
        )
        if modes_result["n_modes"] < 1:
            raise RuntimeError(
                f"段 {idx} 无导模（R03 禁止 fall-back）"
            )
        section_data.append({
            "width_um": sec["width_um"],
            "length_um": sec["length_um"],
            "n_core": sec["n_core"],
            "n_clad": sec["n_clad"],
            "mode": modes_result["modes"][0],  # 基模
            "grid_info": modes_result["grid_info"],
        })

    # 2. 段内传播相位（单模）
    for sd in section_data:
        beta = sd["mode"]["beta"]
        sd["propagation_phase"] = propagate_phase(beta, sd["length_um"])

    # 3. 界面模式匹配（E/H 连续性 + 单模 Galerkin 投影）
    # *创新*: 由 Maxwell 界面连续性方程严格推导单模反射/透射系数，
    #   底层逻辑: E_y 与 H_x 在 z=0 连续，单模近似下分别投影到 E_a/E_b，
    #   消去透射振幅后反射仅由 TE 导纳失配决定（场失配功率耦合到高阶模，不归反射）。
    # 推导:
    #   E 连续: (a_in+a_ref)·E_a = b_trans·E_b  →  投影 E_a: a_in+a_ref = b_trans·P
    #   H 连续: β_a·(a_in-a_ref)·E_a = β_b·b_trans·E_b  →  投影 E_a: β_a·(a_in-a_ref)=β_b·b_trans·P
    #   消去 b_trans·P: β_a·(a_in-a_ref) = β_b·(a_in+a_ref)
    #   → r = a_ref/a_in = (β_a-β_b)/(β_a+β_b)  (TE 导纳 Y=β/ωμ 阻抗失配反射)
    #   → t_ab = b_trans/a_in = 2·β_a/(β_a+β_b)·P  (含 β 匹配 + 场重叠)
    # 旧实现 |r|²=1-|t|² 错误地把场失配全部归为反射 → |R| 高估（R05 Bug）。
    # 参考: Collin 2001 §5.1 传输线反射 / Marcuse 1981 §8.5 波导模式匹配。
    interfaces: list[np.ndarray] = []
    for i in range(len(section_data) - 1):
        mode_a = section_data[i]["mode"]
        mode_b = section_data[i + 1]["mode"]
        fa = np.asarray(mode_a["field_1d"], dtype=np.float64)
        fb = np.asarray(mode_b["field_1d"], dtype=np.float64)
        if fa.shape != fb.shape:
            raise RuntimeError(
                f"段 {i}/{i+1} 模场形状不匹配 {fa.shape} vs {fb.shape} "
                f"（请确保 dx_um/pad_um 一致，R03 禁止 fall-back）"
            )
        dx = section_data[i]["grid_info"]["dx_um"]
        # 场重叠积分 P = ∫E_a·E_b dx（∫|E|²dx=1 归一化）
        P_overlap = compute_overlap_1d(fa, fb, dx)
        beta_a = float(mode_a["beta"])
        beta_b = float(mode_b["beta"])
        # 反射: TE 导纳 Y=β/ωμ，r=(Y_a-Y_b)/(Y_a+Y_b)=(β_a-β_b)/(β_a+β_b)
        r_left = (beta_a - beta_b) / (beta_a + beta_b)
        r_right = -r_left
        # 透射: t = 2·Y_a/(Y_a+Y_b)·P（β 匹配 × 场重叠）
        t_ab = 2.0 * beta_a / (beta_a + beta_b) * P_overlap
        t_ba = 2.0 * beta_b / (beta_a + beta_b) * P_overlap
        # 单模 S 矩阵: [[S11=左反射, S12=右→左透射],[S21=左→右透射, S22=右反射]]
        S = np.array([
            [r_left, t_ba],
            [t_ab, r_right],
        ], dtype=complex)
        interfaces.append(S)

    # 4. Redheffer 级联
    # 总 S = S_interface_0 ⊗ P_1 ⊗ S_interface_1 ⊗ P_2 ⊗ ... ⊗ S_interface_{N-2}
    # 其中 P_i 是段 i 的传播矩阵 [[0, exp(j*beta*L)], [exp(j*beta*L), 0]]（透射）
    # 简化: 段内纯相位，等价于 S = [[0, P], [P, 0]]（无反射）
    if len(section_data) == 1:
        # 单段: 只有传播，无界面
        P = section_data[0]["propagation_phase"]
        S_total = np.array([
            [0.0 + 0.0j, P],
            [P, 0.0 + 0.0j],
        ], dtype=complex)
    else:
        # 第一段传播矩阵
        P0 = section_data[0]["propagation_phase"]
        S_total = np.array([
            [0.0 + 0.0j, P0],
            [P0, 0.0 + 0.0j],
        ], dtype=complex)
        # 级联: S_total = S_total ⊗ S_interface_0 ⊗ P_1 ⊗ S_interface_1 ⊗ ...
        for i in range(len(interfaces)):
            # 级联界面 i
            S_total = redheffer_star(S_total, interfaces[i])
            # 级联段 i+1 的传播
            if i + 1 < len(section_data):
                P_next = section_data[i + 1]["propagation_phase"]
                S_prop = np.array([
                    [0.0 + 0.0j, P_next],
                    [P_next, 0.0 + 0.0j],
                ], dtype=complex)
                S_total = redheffer_star(S_total, S_prop)

    # 5. 提取结果
    transmission = complex(S_total[1, 0])  # S21: 左→右透射
    reflection = complex(S_total[0, 0])    # S11: 左侧反射
    t_abs = abs(transmission)
    transmission_db = 20.0 * float(np.log10(max(t_abs, 1e-30)))

    return {
        "transmission": transmission,
        "transmission_db": transmission_db,
        "reflection": reflection,
        "s_matrix": S_total.tolist(),
        "n_sections": len(section_data),
        "wavelength_um": float(wavelength_um),
        "sections_info": [
            {
                "index": i,
                "width_um": sd["width_um"],
                "length_um": sd["length_um"],
                "n_core": sd["n_core"],
                "n_clad": sd["n_clad"],
                "neff": sd["mode"]["neff"],
                "beta": sd["mode"]["beta"],
                "propagation_phase": sd["propagation_phase"],
            }
            for i, sd in enumerate(section_data)
        ],
    }
