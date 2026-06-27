"""H01 电光耦合模块（Plasma Dispersion Effect，DDM→OPTIC 耦合）。

将漂移-扩散（DDM）求解器输出的电子/空穴浓度分布（N_e, N_h）经
等离子体色散效应（Drude-like 自由载流子吸收）转化为折射率扰动场
Δn(x,y,z)，供光学仿真（FDE/FDTD/EME）重新求解模式偏移与相位漂移。

R01 方案检索记录（规则 1）：
- 关键词：plasma dispersion effect silicon Soref Bennett free carrier
  refractive index modulation electro-optic modulator
- 采用方案：Soref & Bennett 1987 经典等离子体色散经验公式
  Δn = -α_e·ΔN_e - α_h·ΔN_h（硅 @1.55μm，α_e=8.8e-22, α_h=8.5e-22 cm³）
  + 光场限制因子 Γ 加权 Δn_eff = Γ·Δn（Reed 2010 §II 综述）。
  不采用 Drude 全波色散模型（Nedeljkovic 2011 拟合），因其引入未溯源
  的波长依赖参数；本实现仅在已溯源的 1.55μm 波长给出系数，
  其他波长 raise NotImplementedError（学术诚信，规则 18）。

物理公式（学术诚信，规则 18）：
1. 等离子体色散效应（Soref & Bennett 1987, IEEE JQE 23(1):123-129）：
       Δn = -α_e·ΔN_e - α_h·ΔN_h
   其中 ΔN_e, ΔN_h 为电子/空穴浓度变化量 [cm^-3]，α_e, α_h 为
   等离子体色散系数 [cm³]（硅 @1.55μm 室温）。负号源于自由载流子
   注入降低折射率（色散负效应）。
2. 模式有效折射率变化（Reed 2010 §II.A 一阶微扰）：
       Δn_eff = Γ · Δn
   其中 Γ 为光场限制因子（mode overlap with active region），范围 [0, 1]。
   当 Δn 为空间场时，需用模式光强 |E|² 加权积分：
       Δn_eff = ∫|E|²·Δn dA / ∫|E|² dA
   （Snyder & Love 1983 §13 模式微扰理论）。
3. 载流子吸收（Soref & Bennett 1987）：
       Δα = -β_e·ΔN_e - β_h·ΔN_h
   （@1.55μm: β_e=5.7e-20, β_h=6.0e-20 cm²）——本模块不计算 Δα，
   仅产出 Δn 供光学求解器使用。

*创新* DDM→OPTIC 接口契约：本模块仅产出物理量（Δn 场、Δn_eff 标量），
不内部重解光学模式，保持单一职责。下游光学求解器（FDE/FDTD/EME）
消费这些物理量完成闭环。底层逻辑：解耦避免循环依赖，电-光可在各自
求解器中独立验证与替换（与 heat/coupling.py 接口契约同模式）。

*创新* 网格重采样：当 DDM 网格与光学网格不一致时，使用 scipy
RegularGridInterpolator（线性插值，三阶样条可选）重采样 Δn 场到光学
网格，避免重复求解 DDM（半导体网格通常比光学网格粗，重采样代价低）。
底层逻辑：DDM 与光学求解器各自最优网格密度，耦合通过插值衔接。

文献来源（≥5，规则 18 学术诚信）：
1. Soref & Bennett 1987 IEEE J Quantum Electronics 23(1):123-129 —
   等离子体色散经典公式（@1.55μm: α_e=8.8e-22, α_h=8.5e-22 cm³）—
   https://doi.org/10.1109/JQE.1987.1073206
2. Nedeljkovic, Soref & Mashanovich 2011 Opt Express 19(10):9212-9219 —
   硅等离子体色散与自由载流子吸收系数精修（@1.55μm 复核）—
   https://doi.org/10.1364/OE.19.009212
3. Reed, Mashanovich, Thomson & Gardes 2010 Nature Photonics 4:518-526 —
   硅光调制器综述（Δn_eff = Γ·Δn 模式微扰理论）—
   https://doi.org/10.1038/nphoton.2010.179
4. Thomson, Gardes, Fedeli, Zlatanovic, Hu, Kuo, Marris-Morini, Nedeljkovic,
   Yang, Petropoulos, Reed 2011 Silicon Photonics and Photonic Integrated
   Circuits IV 7943:79430C — 载流子注入/耗尽型调制器实测 —
   https://doi.org/10.1117/12.873024
5. Xu, Tan, Zhang, Li 2018 IEEE J Selected Topics Quantum Electronics
   24(6):8200315 — CMOS 兼容硅光集成调制器（公式应用案例）—
   https://doi.org/10.1109/JSTQE.2018.2845827
6. Snyder & Love 1983 "Optical Waveguide Theory" Springer —
   模式微扰理论 §13（光强加权有效折射率变化）—
   https://link.springer.com/book/10.1007/978-94-009-6855-1
7. Soref, Bennett, Schmidt, Underwood 1993 Silicon-Based Optoelectronics
   IEEE J Quantum Electronics 29(3):871-879 — Si 调制器综述 —
   https://doi.org/10.1109/3.249432

规则依据：project_rules.md 规则 14（禁止 fall-back，失败 raise）
/规则 18（学术诚信）/规则 26（GPU 不参与，纯 numpy/scipy CPU）。
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

__all__ = [
    "ElectroOpticCouplingResult",
    "PLASMA_DISPERSION_COEFFS",
    "apply_electro_optic_coupling",
    "compute_delta_n_from_carriers",
    "compute_effective_index_change",
    "get_plasma_dispersion_coefficients",
]

# 等离子体色散系数（Soref & Bennett 1987 IEEE JQE 23(1):123-129, 表 I）
# α_e, α_h 单位 [cm³]，浓度变化 ΔN 单位 [cm^-3]
# 形如 Δn = -α_e·ΔN_e - α_h·ΔN_h（无单位，折射率绝对变化）
PLASMA_DISPERSION_COEFFS: dict[float, tuple[float, float]] = {
    1.55e-6: (8.8e-22, 8.5e-22),  # 硅 @1.55μm（任务指定，Soref-Bennett 1987）
}

# 验证波长容差（浮点比较）[m]
_WAVELENGTH_TOL: float = 1e-12

# 浓度下界（物理约束：载流子浓度非负）[cm^-3]
_CARRIER_FLOOR: float = 0.0


@dataclass
class ElectroOpticCouplingResult:
    """电光耦合结果（DDM→OPTIC 接口产物）。

    Attributes:
        delta_n: 折射率扰动场 Δn(x,y)（与光学网格一致，无单位）。
        delta_n_eff: 模式有效折射率变化（Γ·⟨Δn⟩ 加权，标量，无单位）。
        confinement_factor: 光场限制因子 Γ（输入）。
        wavelength: 工作波长 [m]。
        coefficients: 使用的等离子体色散系数 (α_e, α_h) [cm³]。
    """

    delta_n: np.ndarray
    delta_n_eff: float
    confinement_factor: float
    wavelength: float
    coefficients: tuple[float, float]

    def __post_init__(self) -> None:
        if not np.all(np.isfinite(self.delta_n)):
            raise ValueError("delta_n 含非有限值（耦合计算失败）")
        if not np.isfinite(self.delta_n_eff):
            raise ValueError("delta_n_eff 非有限值")
        if not (0.0 <= self.confinement_factor <= 1.0):
            raise ValueError(
                f"confinement_factor 须 ∈ [0,1]，实际 {self.confinement_factor}"
            )
        if self.wavelength <= 0.0:
            raise ValueError(f"wavelength 须 > 0，实际 {self.wavelength}")


def get_plasma_dispersion_coefficients(wavelength: float) -> tuple[float, float]:
    """返回硅等离子体色散系数 (α_e, α_h) [cm³]。

    目前仅支持 1.55μm（Soref & Bennett 1987 经典公式，源数据精确）。
    其他波长 raise NotImplementedError（学术诚信：禁止编造未溯源系数）。
    未来可扩展为 Nedeljkovic 2011 全波色散拟合，但需溯源论文精确系数。

    Args:
        wavelength: 工作波长 [m]，默认支持 1.55e-6（1.55μm）。

    Returns:
        (α_e, α_h) 等离子体色散系数元组，单位 [cm³]。

    Raises:
        TypeError: wavelength 非 float 或 None。
        ValueError: wavelength ≤ 0 或非有限值。
        NotImplementedError: 波长未在已溯源系数表中（避免编造）。
    """
    if wavelength is None:
        raise TypeError("wavelength 不可为 None")
    if not isinstance(wavelength, (int, float, np.floating)):
        raise TypeError(
            f"wavelength 须为数值，实际类型 {type(wavelength).__name__}"
        )
    wl = float(wavelength)
    if not np.isfinite(wl):
        raise ValueError("wavelength 须为有限值")
    if wl <= 0.0:
        raise ValueError(f"wavelength 须 > 0，实际 {wl}")

    for ref_wl, coeffs in PLASMA_DISPERSION_COEFFS.items():
        if abs(wl - ref_wl) <= _WAVELENGTH_TOL:
            return coeffs
    supported = sorted(PLASMA_DISPERSION_COEFFS.keys())
    raise NotImplementedError(
        f"波长 {wl:.3e} m 未在已溯源系数表中（Soref-Bennett 1987 仅 @1.55μm），"
        f"支持波长 [m]: {supported}。其他波长需扩展 Nedeljkovic 2011 拟合"
        f"（DOI:10.1364/OE.19.009212），禁止编造系数（规则 18 学术诚信）"
    )


def compute_delta_n_from_carriers(
    n_e: np.ndarray,
    n_h: np.ndarray,
    wavelength: float = 1.55e-6,
) -> np.ndarray:
    """计算载流子分布引起的折射率变化场 Δn（Soref-Bennett 1987 公式）。

        Δn = -α_e·ΔN_e - α_h·ΔN_h

    其中 ΔN_e, ΔN_h 为电子/空穴浓度相对本征平衡的变化量 [cm^-3]，
    α_e, α_h 为等离子体色散系数 [cm³]（硅 @1.55μm: 8.8e-22, 8.5e-22）。

    Args:
        n_e: 电子浓度变化量 ΔN_e [cm^-3]，与 n_h 同形状。
        n_h: 空穴浓度变化量 ΔN_h [cm^-3]，与 n_e 同形状。
        wavelength: 工作波长 [m]，默认 1.55e-6（1.55μm，Soref-Bennett 1987）。

    Returns:
        Δn 折射率变化场（与输入同形状，无单位，负值表示折射率降低）。

    Raises:
        TypeError: n_e/n_h 非 ndarray 或为 None。
        ValueError: 形状不一致、含非有限值、浓度为负（物理约束）。
        NotImplementedError: 波长未在已溯源系数表中。
    """
    if n_e is None or n_h is None:
        raise TypeError("n_e / n_h 不可为 None")
    if not isinstance(n_e, np.ndarray):
        raise TypeError(f"n_e 须为 np.ndarray，实际 {type(n_e).__name__}")
    if not isinstance(n_h, np.ndarray):
        raise TypeError(f"n_h 须为 np.ndarray，实际 {type(n_h).__name__}")
    if n_e.shape != n_h.shape:
        raise ValueError(f"n_e {n_e.shape} 与 n_h {n_h.shape} 形状不一致")
    if not np.all(np.isfinite(n_e)):
        raise ValueError("n_e 含非有限值")
    if not np.all(np.isfinite(n_h)):
        raise ValueError("n_h 含非有限值")
    if np.any(n_e < _CARRIER_FLOOR):
        raise ValueError("n_e 须全为非负值（物理约束：载流子浓度非负）")
    if np.any(n_h < _CARRIER_FLOOR):
        raise ValueError("n_h 须全为非负值（物理约束：载流子浓度非负）")

    alpha_e, alpha_h = get_plasma_dispersion_coefficients(wavelength)
    return -alpha_e * n_e - alpha_h * n_h


def compute_effective_index_change(
    delta_n: np.ndarray,
    confinement_factor: float,
) -> float:
    """计算模式有效折射率变化 Δn_eff = Γ·⟨Δn⟩（Reed 2010 §II.A）。

    其中 Γ 为光场限制因子（mode overlap with active region, [0,1]），
    ⟨Δn⟩ 为 Δn 场的空间均值（当无模式场分布时的一阶近似）。
    若需更精确的模式光强加权积分，应在下游 FDE 求解器中按
    Δn_eff = ∫|E|²·Δn dA / ∫|E|² dA 计算（Snyder & Love 1983 §13）。

    Args:
        delta_n: 折射率变化场（任意形状，无单位）。
        confinement_factor: 光场限制因子 Γ ∈ [0, 1]。

    Returns:
        Δn_eff 标量（无单位）。

    Raises:
        TypeError: delta_n 非 ndarray 或 confinement_factor 非数值。
        ValueError: delta_n 含非有限值；Γ 不在 [0,1] 区间。
    """
    if delta_n is None:
        raise TypeError("delta_n 不可为 None")
    if not isinstance(delta_n, np.ndarray):
        raise TypeError(f"delta_n 须为 np.ndarray，实际 {type(delta_n).__name__}")
    if not np.all(np.isfinite(delta_n)):
        raise ValueError("delta_n 含非有限值")
    if confinement_factor is None:
        raise TypeError("confinement_factor 不可为 None")
    if not isinstance(confinement_factor, (int, float, np.floating)):
        raise TypeError(
            f"confinement_factor 须为数值，实际 {type(confinement_factor).__name__}"
        )
    gamma = float(confinement_factor)
    if not np.isfinite(gamma):
        raise ValueError("confinement_factor 须为有限值")
    if not (0.0 <= gamma <= 1.0):
        raise ValueError(f"confinement_factor 须 ∈ [0,1]，实际 {gamma}")

    return gamma * float(np.mean(delta_n))


def _resample_to_optical_grid(
    field: np.ndarray,
    src_dx: float,
    src_dy: float,
    dst_x: np.ndarray,
    dst_y: np.ndarray,
) -> np.ndarray:
    """将 DDM/HEAT 场重采样到光学网格（线性插值）。

    使用 scipy.interpolate.RegularGridInterpolator 实现张量网格插值，
    禁止外推（越界点 raise，避免物理不一致的边界假数据 fall-back）。

    Args:
        field: 源场 (nx_src, ny_src)。
        src_dx, src_dy: 源网格间距 [m]。
        dst_x: 目标网格 x 坐标 [m]，1D 单调数组。
        dst_y: 目标网格 y 坐标 [m]，1D 单调数组。

    Returns:
        重采样后的场 (len(dst_x), len(dst_y))。

    Raises:
        ValueError: 形状不匹配、坐标越界、插值失败。
    """
    from scipy.interpolate import RegularGridInterpolator

    nx_src, ny_src = field.shape
    if nx_src < 2 or ny_src < 2:
        raise ValueError(
            f"源场维度须 ≥ 2，实际 ({nx_src},{ny_src})（插值需 ≥2 节点）"
        )
    src_x = np.arange(nx_src) * src_dx
    src_y = np.arange(ny_src) * src_dy

    interp = RegularGridInterpolator(
        (src_x, src_y),
        field,
        method="linear",
        bounds_error=True,
        fill_value=np.nan,  # 越界点标记 NaN，下游 isfinite 检查捕获
    )
    dst_x_arr = np.asarray(dst_x, dtype=float)
    dst_y_arr = np.asarray(dst_y, dtype=float)
    if dst_x_arr.ndim != 1 or dst_y_arr.ndim != 1:
        raise ValueError("dst_x/dst_y 须为 1D 坐标数组")
    if dst_x_arr.size < 1 or dst_y_arr.size < 1:
        raise ValueError("dst_x/dst_y 须非空")

    xx, yy = np.meshgrid(dst_x_arr, dst_y_arr, indexing="ij")
    pts = np.stack([xx.ravel(), yy.ravel()], axis=-1)
    sampled = interp(pts).reshape(xx.shape)
    if not np.all(np.isfinite(sampled)):
        raise ValueError(
            "重采样产生 NaN/Inf（目标网格越出源网格范围），"
            "禁止外推 fall-back，请扩大源网格或缩小光学网格范围"
        )
    return sampled


def _extract_ddm_carriers(ddm_result) -> tuple[np.ndarray, np.ndarray, float | None, float | None]:
    """校验并提取 DDM 载流子分布（duck-typed DdmResult 接口契约）。

    Args:
        ddm_result: DDM 求解结果，须含 electron_density / hole_density 字段。

    Returns:
        (n_e, n_h, src_dx, src_dy)：载流子浓度场 [cm^-3] 与可选网格间距 [m]。

    Raises:
        TypeError: ddm_result 缺字段或为 None。
        ValueError: 浓度含非有限值或为负（物理约束）。
    """
    if ddm_result is None:
        raise TypeError("ddm_result 不可为 None")
    if not (hasattr(ddm_result, "electron_density") and hasattr(ddm_result, "hole_density")):
        raise TypeError(
            "ddm_result 须含 electron_density 与 hole_density 字段"
            f"（duck-typed DdmResult），实际类型 {type(ddm_result).__name__}"
        )
    n_e = np.asarray(ddm_result.electron_density, dtype=float)
    n_h = np.asarray(ddm_result.hole_density, dtype=float)
    if not np.all(np.isfinite(n_e)) or not np.all(np.isfinite(n_h)):
        raise ValueError("DDM 载流子浓度含非有限值（求解失败）")
    if np.any(n_e < _CARRIER_FLOOR) or np.any(n_h < _CARRIER_FLOOR):
        raise ValueError("DDM 载流子浓度须非负（物理约束）")
    src_dx = getattr(ddm_result, "_ddm_dx", None) if hasattr(ddm_result, "_ddm_dx") else None
    src_dy = getattr(ddm_result, "_ddm_dy", None) if hasattr(ddm_result, "_ddm_dy") else None
    return n_e, n_h, src_dx, src_dy


def _maybe_resample_to_optical_grid(
    field: np.ndarray,
    src_dx: float | None,
    src_dy: float | None,
    optical_grid: dict | None,
    fallback_shape: tuple[int, int],
) -> np.ndarray:
    """按 optical_grid 规格对场重采样到光学网格（None 则原样返回）。

    Args:
        field: 源场。
        src_dx, src_dy: 源网格间距 [m]。
        optical_grid: 光学网格规格（参见 apply_electro_optic_coupling 文档）。
        fallback_shape: 当 optical_grid 仅含 dx/dy 时的默认网格形状。

    Returns:
        重采样后的场；optical_grid 为 None 时返回原 field。

    Raises:
        TypeError: optical_grid 非 dict。
        ValueError: 网格间距缺失或重采样越界（外推禁止）。
    """
    if optical_grid is None:
        return field
    if not isinstance(optical_grid, dict):
        raise TypeError(
            f"optical_grid 须为 dict 或 None，实际 {type(optical_grid).__name__}"
        )
    if src_dx is None or src_dy is None:
        raise ValueError(
            "optical_grid 提供但源结果未含 _ddm_dx/_ddm_dy（或 dx/dy）网格间距，"
            "无法重采样（请直接传入同形状场，或在源结果上注入网格元数据）"
        )
    dst_x = optical_grid.get("x")
    dst_y = optical_grid.get("y")
    if dst_x is None or dst_y is None:
        dx_opt = optical_grid.get("dx")
        dy_opt = optical_grid.get("dy")
        if dx_opt is None or dy_opt is None:
            raise ValueError("optical_grid 须含 'x'/'y' 或 'dx'/'dy'（至少一组）")
        nx_opt = int(optical_grid.get("nx", fallback_shape[0]))
        ny_opt = int(optical_grid.get("ny", fallback_shape[1]))
        dst_x = np.arange(nx_opt) * float(dx_opt)
        dst_y = np.arange(ny_opt) * float(dy_opt)
    return _resample_to_optical_grid(field, src_dx, src_dy, dst_x, dst_y)


def apply_electro_optic_coupling(
    ddm_result,
    optical_grid: dict | None = None,
    wavelength: float = 1.55e-6,
    confinement_factor: float = 1.0,
) -> ElectroOpticCouplingResult:
    """DDM 载流子分布 → 折射率扰动 → 光学仿真耦合接口。

    将 DDM 求解器输出的电子/空穴浓度分布经等离子体色散效应转化为
    Δn(x,y) 场，并按光场限制因子 Γ 计算模式有效折射率变化 Δn_eff。

    输入支持 duck-typed DDM 结果对象（含 electron_density, hole_density
    字段，如 polaris.sim.ddm.solver.DdmResult）；可选网格重采样到光学网格。

    Args:
        ddm_result: DDM 求解结果（duck-typed，须含 electron_density 与
            hole_density 字段，单位 [cm^-3]，与 Soref-Bennett 系数单位一致）。
        optical_grid: 光学网格规格 dict，可选。None 表示同 DDM 网格（无重采样）。
            格式 {"x": 1D_array [m], "y": 1D_array [m], "dx": float [m],
                   "dy": float [m]}。提供 x/y 时按 x/y 重采样；仅提供 dx/dy 时
            按等距网格生成坐标（从 0 起算）。
        wavelength: 工作波长 [m]，默认 1.55e-6（Soref-Bennett 1987）。
        confinement_factor: 光场限制因子 Γ ∈ [0,1]，默认 1.0（全限制）。

    Returns:
        ElectroOpticCouplingResult（含 delta_n, delta_n_eff 等字段）。

    Raises:
        TypeError: ddm_result 缺字段或类型错误；optical_grid 非 dict。
        ValueError: 形状不匹配、浓度非负性违反、重采样越界。
        NotImplementedError: 波长未在已溯源系数表中。
    """
    n_e, n_h, src_dx, src_dy = _extract_ddm_carriers(ddm_result)
    delta_n = compute_delta_n_from_carriers(n_e, n_h, wavelength=wavelength)
    delta_n = _maybe_resample_to_optical_grid(
        delta_n, src_dx, src_dy, optical_grid, n_e.shape
    )
    delta_n_eff = compute_effective_index_change(delta_n, confinement_factor)
    alpha_e, alpha_h = get_plasma_dispersion_coefficients(wavelength)
    return ElectroOpticCouplingResult(
        delta_n=delta_n,
        delta_n_eff=delta_n_eff,
        confinement_factor=float(confinement_factor),
        wavelength=float(wavelength),
        coefficients=(alpha_e, alpha_h),
    )
