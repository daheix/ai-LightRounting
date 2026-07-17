"""2D 任意截面本征模展开（EME）求解器（polaris-eme）。

将 2D 任意截面波导沿传播方向 z 切片为多个均匀段，每段调用
``polaris_fde.solve_modes`` 求解本地 2D 本征模（5 点拉普拉斯 + ARPACK），
界面用 2D 重叠积分计算透射/反射，段内相位传播，Redheffer 星积级联多段 S 矩阵。

## 算法

1. **每段 2D 本征模求解**: ``polaris_fde.solve_modes`` → neff / beta / field_2d
2. **公共网格重采样**: 各段窗口随 width/height 变化 → 以波导芯中心对齐，
   用 ``scipy.interpolate.RegularGridInterpolator`` 插值到公共网格（最大窗口 +
   最细 dx）。Dirichlet 边界 E=0 → 窗外填 0（``fill_value=0``）。
3. **场功率归一化**: FDE 默认 max=1 归一化，重归一化为 ∫∫|E|² dxdy = 1
   （Snyder & Love 1983 模式正交归一化）。
4. **段内传播**: P = exp(j·β·L)（复用 ``polaris_eme.solver.propagate_phase``）。
5. **界面模式匹配**（E/H 连续性 + 单模 Galerkin 投影，*创新*，同 1D EME）:
   场重叠 P = ∫∫ E_a · E_b* dxdy（功率归一化后 |P| ≤ 1）
   TE 导纳 Y=β/ωμ，反射 r=(β_a−β_b)/(β_a+β_b)（阻抗失配）
   透射 t_ab = 2·β_a/(β_a+β_b)·P（β 匹配 × 场重叠）
   来源: Collin 2001 §5.1 传输线反射 / Marcuse 1981 §8.5 波导模式匹配。
6. **S 矩阵级联**: Redheffer 星积 S_total = S_prop_0 ⊗ S_iface_0 ⊗ S_prop_1 ⊗ ...

## Input / Process / Output

- I: sections（list[{width_um, height_um, length_um, n_core, n_clad}]）
     / wavelength_um / n_modes_per_section / dx_um / dy_um / pad_um
- P: 每段 2D FDE 模式求解 → 公共网格重采样 → 功率归一化 → 2D 重叠积分
     → 相位传播 → Redheffer 级联
- O: dict{s_matrix, modes_per_section, wavelength_um, transmission, reflection}

## 来源（R02 学术诚信，≥5 个文献 URL）
- Bienstman 2001 PhD §2.3（2D EME 模式匹配 + Redheffer 星积）
  https://www.photonics.intec.ugent.be/download/phd_bienstman.pdf
- Smit & van Dam 1996 IEEE/OSA JLT 14(7) 1746（模式展开理论）
  https://doi.org/10.1109/50.511954
- Lumerical EME 2D 文档
  https://optics.ansys.com/hc/en-us/articles/360034902413
- Snyder & Love 1983 "Optical Waveguide Theory"（模式正交性 ∫∫E_a·E_b*dA=δ_ab）
  https://link.springer.com/book/10.1007/978-94-009-6875-2
- Collin 2001 "Foundations for Microwave Engineering" §5.1（传输线阻抗反射）
  https://ieeexplore.ieee.org/book/5263073
- Marcuse 1981 "Light Transmission Optics" §8.5（波导模式匹配 E/H 连续性）
  https://onlinelibrary.wiley.com/doi/book/10.1002/9783527619742
- scipy.interpolate.RegularGridInterpolator
  https://docs.scipy.org/doc/scipy/reference/generated/scipy.interpolate.RegularGridInterpolator.html
- polaris_fde.solve_modes（5 点拉普拉斯 + ARPACK，本模块复用其 2D 模场）
"""

from __future__ import annotations

from typing import Any

import numpy as np
from scipy.interpolate import RegularGridInterpolator

from polaris_eme.solver import propagate_phase, redheffer_star

__all__ = ["solve_eme_2d", "mode_overlap_2d"]


# =========================================================================
# 2D 重叠积分（mode_overlap_2d）
# =========================================================================

def _extract_field_2d(mode: Any) -> np.ndarray:
    """从 mode 提取 2D 模场数组（接受 ndarray / list / dict）。

    dict 形式取 ``field_2d`` 键（与 ``polaris_fde.solve_modes`` 输出一致）。
    """
    if isinstance(mode, dict):
        if "field_2d" not in mode:
            raise KeyError("mode dict 缺少 'field_2d' 字段（R03 禁止 fall-back）")
        return np.asarray(mode["field_2d"], dtype=complex)
    return np.asarray(mode, dtype=complex)


def mode_overlap_2d(
    mode_a: Any, mode_b: Any, dx_um: float, dy_um: float,
) -> complex:
    """计算两个 2D 模场的重叠积分 ∫∫ E_a · E_b* dx dy。

    用于 2D EME 界面模式匹配，计算透射系数（Sztefanka 1993 / Marcuse 1981）。
    输入场应已功率归一化（∫∫|E|² dxdy = 1），此时 |overlap| ≤ 1。

    Args:
        mode_a, mode_b: 2D 模场（ndarray / list，或含 ``field_2d`` 的 dict）。
        dx_um: x 方向网格步长（μm）。
        dy_um: y 方向网格步长（μm）。

    Returns:
        complex: 重叠积分值。

    Raises:
        ValueError: 形状不匹配或参数非法（R03 禁止 fall-back）。
    """
    fa = _extract_field_2d(mode_a)
    fb = _extract_field_2d(mode_b)
    if fa.shape != fb.shape:
        raise ValueError(
            f"2D 模场形状不匹配: {fa.shape} vs {fb.shape}"
        )
    if fa.ndim != 2:
        raise ValueError(f"模场须 2D，得到 {fa.ndim}D")
    if dx_um <= 0:
        raise ValueError(f"dx_um 须 > 0，得到 {dx_um}")
    if dy_um <= 0:
        raise ValueError(f"dy_um 须 > 0，得到 {dy_um}")
    overlap = np.sum(fa * np.conj(fb)) * dx_um * dy_um
    return complex(overlap)


# =========================================================================
# 参数校验
# =========================================================================

def _validate_eme_2d_sections(
    sections: list, wavelength_um: float, n_modes_per_section: int,
    dx_um: float, dy_um: float, pad_um: float,
) -> list:
    """校验 solve_eme_2d 入参并解析每段为标准 dict（R03 禁止 fall-back）。"""
    if not sections:
        raise ValueError("sections 不能为空（R03 禁止 fall-back）")
    if wavelength_um <= 0:
        raise ValueError(f"wavelength_um 须 > 0，得到 {wavelength_um}")
    if n_modes_per_section < 1:
        raise ValueError(
            f"n_modes_per_section 须 >= 1，得到 {n_modes_per_section}"
        )
    if dx_um <= 0:
        raise ValueError(f"dx_um 须 > 0，得到 {dx_um}")
    if dy_um <= 0:
        raise ValueError(f"dy_um 须 > 0，得到 {dy_um}")
    if pad_um <= 0:
        raise ValueError(f"pad_um 须 > 0，得到 {pad_um}")
    parsed: list[dict[str, Any]] = []
    for idx, sec in enumerate(sections):
        if not isinstance(sec, dict):
            raise ValueError(f"段 {idx} 须 dict，得到 {type(sec)}")
        for key in ("width_um", "height_um", "length_um", "n_core", "n_clad"):
            if key not in sec:
                raise ValueError(f"段 {idx} 缺少必需字段 '{key}'")
        if sec["length_um"] < 0:
            raise ValueError(
                f"段 {idx} length_um 须 >= 0，得到 {sec['length_um']}"
            )
        parsed.append({
            "width_um": float(sec["width_um"]),
            "height_um": float(sec["height_um"]),
            "length_um": float(sec["length_um"]),
            "n_core": float(sec["n_core"]),
            "n_clad": float(sec["n_clad"]),
        })
    return parsed


# =========================================================================
# 每段 2D 本征模求解（委托 polaris_fde.solve_modes）
# =========================================================================

def _solve_section_modes_2d(
    parsed: list, wavelength_um: float, n_modes_per_section: int,
    dx_um: float, dy_um: float, pad_um: float,
) -> list:
    """每段调用 polaris_fde.solve_modes 求基模 + 段内相位传播。

    各段使用各自的 width/height 求解；公共网格对齐在 _resample 阶段处理。
    """
    from polaris_fde import solve_modes  # 延迟导入，避免循环依赖

    section_data: list[dict[str, Any]] = []
    for idx, sec in enumerate(parsed):
        modes_result = solve_modes(
            width_um=sec["width_um"],
            height_um=sec["height_um"],
            wavelength_um=wavelength_um,
            n_core=sec["n_core"],
            n_clad=sec["n_clad"],
            n_modes=n_modes_per_section,
            dx_um=min(dx_um, dy_um),  # FDE 用单一 dx；取较细者保证分辨率
            pad_um=pad_um,
        )
        if modes_result["n_modes"] < 1:
            raise RuntimeError(f"段 {idx} 无导模（R03 禁止 fall-back）")
        mode = modes_result["modes"][0]  # 基模
        beta = float(mode["beta"])
        section_data.append({
            "width_um": sec["width_um"],
            "height_um": sec["height_um"],
            "length_um": sec["length_um"],
            "n_core": sec["n_core"],
            "n_clad": sec["n_clad"],
            "mode": mode,
            "grid_info": modes_result["grid_info"],
            "propagation_phase": propagate_phase(beta, sec["length_um"]),
        })
    return section_data


# =========================================================================
# 公共网格构造 + 重采样 + 功率归一化
# =========================================================================

def _build_common_grid(section_data: list, dx_um: float, dy_um: float) -> dict:
    """构造公共网格（最大窗口 + 最细步长），坐标以波导芯中心对齐。"""
    max_wx = max(sd["grid_info"]["window_x_um"] for sd in section_data)
    max_wy = max(sd["grid_info"]["window_y_um"] for sd in section_data)
    nx_c = int(round(max_wx / dx_um))
    ny_c = int(round(max_wy / dy_um))
    if nx_c < 5 or ny_c < 5:
        raise RuntimeError(
            f"公共网格过小 {nx_c}×{ny_c}（R03 禁止 fall-back）"
        )
    # 以芯中心为原点：x ∈ [−Wx/2, Wx/2]
    x_c = (np.arange(nx_c) - (nx_c - 1) / 2.0) * dx_um
    y_c = (np.arange(ny_c) - (ny_c - 1) / 2.0) * dy_um
    return {"nx": nx_c, "ny": ny_c, "dx": dx_um, "dy": dy_um,
            "x": x_c, "y": y_c}


def _resample_field_2d(
    field_2d: np.ndarray, grid_info: dict, common: dict,
) -> np.ndarray:
    """将单段 2D 模场重采样到公共网格（芯中心对齐，窗外填 0）。

    RegularGridInterpolator 接受规则网格 (x_points, y_points) + values (nx, ny)，
    在查询点 (x, y) 处线性插值。Dirichlet 边界 E=0 → fill_value=0。
    """
    nx, ny = field_2d.shape
    dx = float(grid_info["dx_um"])
    dy = float(grid_info["dy_um"])
    core_x = grid_info["core_x"]
    core_y = grid_info["core_y"]
    # 以波导芯中心为原点的物理坐标
    cx = (core_x[0] + core_x[1]) / 2.0 * dx
    cy = (core_y[0] + core_y[1]) / 2.0 * dy
    x_sec = (np.arange(nx) * dx) - cx
    y_sec = (np.arange(ny) * dy) - cy
    interp = RegularGridInterpolator(
        (x_sec, y_sec), field_2d,
        bounds_error=False, fill_value=0.0,
    )
    xx, yy = np.meshgrid(common["x"], common["y"], indexing="ij")
    return interp(np.column_stack([xx.ravel(), yy.ravel()])).reshape(
        common["nx"], common["ny"]
    )


def _normalize_power_2d(field: np.ndarray, dx: float, dy: float) -> np.ndarray:
    """功率归一化 ∫∫|E|² dxdy = 1（Snyder & Love 1983 模式正交归一化）。"""
    norm = float(np.sqrt(np.sum(np.abs(field) ** 2) * dx * dy))
    if norm <= 0:
        raise RuntimeError("模场功率为 0，无法归一化（R03 禁止 fall-back）")
    return field / norm


# =========================================================================
# 界面模式匹配 + S 矩阵级联
# =========================================================================

def _build_eme_2d_interfaces(
    section_data: list, common: dict,
) -> list:
    """2D 界面模式匹配（E/H 连续性 + 单模 Galerkin 投影，*创新*）。

    各段模场先重采样到公共网格并功率归一化，再计算 2D 重叠积分 P。
    反射/透射系数同 1D EME（Collin 2001 §5.1 / Marcuse 1981 §8.5）。
    """
    dx, dy = common["dx"], common["dy"]
    # 预处理：每段模场重采样 + 功率归一化
    norm_fields: list[np.ndarray] = []
    for sd in section_data:
        field = np.asarray(sd["mode"]["field_2d"], dtype=np.float64)
        field_c = _resample_field_2d(field, sd["grid_info"], common)
        norm_fields.append(_normalize_power_2d(field_c, dx, dy))
    interfaces: list[np.ndarray] = []
    for i in range(len(section_data) - 1):
        p_overlap = mode_overlap_2d(norm_fields[i], norm_fields[i + 1], dx, dy)
        beta_a = float(section_data[i]["mode"]["beta"])
        beta_b = float(section_data[i + 1]["mode"]["beta"])
        sum_b = beta_a + beta_b
        if abs(sum_b) < 1e-30:
            raise RuntimeError(
                f"段 {i}/{i+1} β_a+β_b ≈ 0，界面匹配奇异（R03 禁止 fall-back）"
            )
        r_left = (beta_a - beta_b) / sum_b
        r_right = -r_left
        t_ab = 2.0 * beta_a / sum_b * p_overlap
        t_ba = 2.0 * beta_b / sum_b * p_overlap
        S = np.array([[r_left, t_ba], [t_ab, r_right]], dtype=complex)
        interfaces.append(S)
    return interfaces


def _cascade_eme_2d_s_matrix(
    section_data: list, interfaces: list,
) -> np.ndarray:
    """Redheffer 星积级联: S_total = S_prop_0 ⊗ S_iface_0 ⊗ S_prop_1 ⊗ ..."""
    if len(section_data) == 1:
        P = section_data[0]["propagation_phase"]
        return np.array([[0.0 + 0.0j, P], [P, 0.0 + 0.0j]], dtype=complex)
    P0 = section_data[0]["propagation_phase"]
    S_total = np.array([[0.0 + 0.0j, P0], [P0, 0.0 + 0.0j]], dtype=complex)
    for i in range(len(interfaces)):
        S_total = redheffer_star(S_total, interfaces[i])
        if i + 1 < len(section_data):
            P_next = section_data[i + 1]["propagation_phase"]
            S_prop = np.array(
                [[0.0 + 0.0j, P_next], [P_next, 0.0 + 0.0j]], dtype=complex
            )
            S_total = redheffer_star(S_total, S_prop)
    return S_total


# =========================================================================
# 主 2D EME 求解器
# =========================================================================

def solve_eme_2d(
    sections: list[dict],
    wavelength_um: float = 1.55,
    n_modes_per_section: int = 2,
    dx_um: float = 0.02,
    dy_um: float = 0.02,
    pad_um: float = 1.0,
) -> dict:
    """2D 任意截面 EME 求解器: 多段均匀 2D 波导级联。

    每段截面为 2D 任意截面波导（width×height 可变），沿 z 传播。
    每段调用 ``polaris_fde.solve_modes`` 求基模，公共网格对齐 + 功率归一化
    后做 2D 重叠积分界面匹配，Redheffer 星积级联。

    Args:
        sections: 段列表，每段 dict{width_um, height_um, length_um, n_core, n_clad}。
        wavelength_um: 波长（μm）。
        n_modes_per_section: 每段求解的模式数（仅取基模做单模级联）。
        dx_um: x 方向网格步长（μm）。
        dy_um: y 方向网格步长（μm）。
        pad_um: 包层 padding（μm，每侧）。

    Returns:
        dict: {s_matrix, modes_per_section, wavelength_um, transmission,
               reflection, n_sections}

    Raises:
        ValueError: 参数非法（R03）。
        RuntimeError: 求解失败（R03）。

    来源:
        - Bienstman 2001 PhD（2D EME + Redheffer 星积）
        - Smit & van Dam 1996 JLT（模式展开理论）
        - Lumerical EME 2D 文档
        - Snyder & Love 1983（模式正交归一化）
    """
    parsed = _validate_eme_2d_sections(
        sections, wavelength_um, n_modes_per_section, dx_um, dy_um, pad_um,
    )
    section_data = _solve_section_modes_2d(
        parsed, wavelength_um, n_modes_per_section, dx_um, dy_um, pad_um,
    )
    common = _build_common_grid(section_data, dx_um, dy_um)
    interfaces = _build_eme_2d_interfaces(section_data, common)
    S_total = _cascade_eme_2d_s_matrix(section_data, interfaces)
    transmission = complex(S_total[1, 0])  # S21: 左→右透射
    reflection = complex(S_total[0, 0])    # S11: 左侧反射
    return {
        "s_matrix": S_total.tolist(),
        "modes_per_section": [
            {
                "index": i,
                "width_um": sd["width_um"],
                "height_um": sd["height_um"],
                "length_um": sd["length_um"],
                "n_core": sd["n_core"],
                "n_clad": sd["n_clad"],
                "neff": sd["mode"]["neff"],
                "beta": sd["mode"]["beta"],
                "confinement": sd["mode"].get("confinement"),
                "propagation_phase": sd["propagation_phase"],
            }
            for i, sd in enumerate(section_data)
        ],
        "wavelength_um": float(wavelength_um),
        "transmission": transmission,
        "reflection": reflection,
        "n_sections": len(section_data),
    }
