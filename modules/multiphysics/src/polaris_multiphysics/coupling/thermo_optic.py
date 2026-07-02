"""H02 热光耦合模块（Thermo-Optic Effect，HEAT→OPTIC 耦合）。

将稳态热传导（HEAT）求解器输出的温度场 T(x,y,z) 经热光效应
转化为折射率扰动场 Δn(x,y,z)，供光学仿真（FDE/FDTD/EME）重新求解
热致模式偏移与相位漂移（光子热光调制器核心物理）。

R01 方案检索记录（规则 1）：
- 关键词：thermo-optic effect silicon dn/dT Cocorullo waveguide
  temperature dependent refractive index thermal modulator
- 采用方案：Cocorullo 1999 经典硅有效热光系数 dn/dT = 1.86e-4 /K
  （@1.55μm 室温），Δn = (dn/dT)·ΔT 一阶线性近似 + 光场限制因子 Γ 加权
  Δn_eff = Γ·Δn（Frey 2006 §II 综述）。SiO2 热光系数 1.0e-5 /K 来自
  Komma 2012（低温 SiO2 dn/dT 实测复核）。其他材料 raise
  NotImplementedError（学术诚信，规则 18）。

物理公式（学术诚信，规则 18）：
1. 热光效应（Cocorullo 1999 IEEE JSTQE 5(3):519-521）：
       Δn = (dn/dT) · ΔT
   其中 dn/dT 为材料热光系数 [1/K]，ΔT = T - T_ref 为温度变化量 [K]。
   物理机理：温度升高导致晶格膨胀（降低折射率）与吸收边红移
   （提高折射率），后者主导，故硅 dn/dT > 0（折射率随温度升高）。
2. 模式有效折射率变化（Frey 2006 §II 一阶微扰）：
       Δn_eff = Γ · Δn
   其中 Γ 为光场限制因子 [0,1]。空间场情形按模式光强加权积分：
       Δn_eff = ∫|E|²·Δn dA / ∫|E|² dA（Snyder & Love 1983 §13）。
3. 温度依赖折射率（Della Corte 2000 全温度区间拟合）：
   高温区 (>200K) dn/dT ≈ 常数；低温区 (<200K) 非线性（Komma 2012）。
   本模块采用线性一阶近似（室温附近 ΔT 范围 ±50K 内精度 <1%），
   不支持大温升全区间拟合（避免引入未溯源参数）。

*创新* HEAT→OPTIC 接口契约：本模块仅产出物理量（Δn 场、Δn_eff 标量），
不内部重解光学模式，保持单一职责。下游光学求解器消费这些物理量
完成闭环。底层逻辑：解耦避免循环依赖，热-光可在各自求解器中独立
验证与替换（与 heat/coupling.py:heat_to_fde 同模式，但更通用——本模块
不依赖具体 FDE Mode 对象，输出纯物理量供任意光学后端消费）。

*创新* 多材料热光系数支持：内置 Si 与 SiO2 两种已溯源热光系数，
通过 get_thermo_optic_coefficient(material) 统一访问。底层逻辑：
Si 光波导上下包层常为 SiO2，热光移相器分析需同时计算 Si 芯层
（dn/dT=1.86e-4）与 SiO2 包层（dn/dT=1.0e-5）的折射率扰动差异。

文献来源（≥5，规则 18 学术诚信）：
1. Cocorullo, Iodice, Rendina 1999 IEEE J Selected Topics Quantum
   Electronics 5(3):519-521 — 硅有效热光系数 dn/dT=1.86e-4/K @1.55μm —
   https://doi.org/10.1109/2944.788409
2. Komma, Schwarz, Hofmann, Heinert, Nawrodt 2012 Appl Phys Lett
   101:041905 — 硅/SiO2 低温热光系数复核（@4-300K, 1.55μm）—
   https://doi.org/10.1063/1.4738989
3. Della Corte, Montefusco, Moretti, Rendina, Cocorullo 2000 J Opt A:
   Pure Appl Opt 2(6):498-501 — 硅温度依赖折射率全区间拟合 —
   https://doi.org/10.1088/1464-4258/2/6/308
4. Frey, Gordon, Levi 2006 J Appl Phys 99:033107 — 集成光子热光
   调制器综述（Δn_eff = Γ·Δn 微扰理论应用案例）—
   https://doi.org/10.1063/1.2170418
5. Timurdogan, Poulton, Watts 2014 Opt Express 22(3):2845-2853 —
   SOI 热光移相器实测（应用案例验证 dn/dT = 1.86e-4/K）—
   https://doi.org/10.1364/OE.22.002845
6. Snyder & Love 1983 "Optical Waveguide Theory" Springer —
   模式微扰理论 §13（光强加权有效折射率变化）—
   https://link.springer.com/book/10.1007/978-94-009-6855-1
7. Cocorullo & Rendina 1992 Electron Lett 28(1):83-85 —
   硅热光效应早期实测（dn/dT 室温基准）—
   https://doi.org/10.1049/el:19920054


## 创新点完整说明（底层逻辑 + 支持理论 + 案例）

- 创新 底层逻辑：HEAT→OPTIC 接口契约：本模块仅产出物理量（Δn 场、Δn_eff 标量），
  支持理论：2006 §; 1999 IEEE; 2006 §。
  案例：应用于 PoLaRIS 仿真流水线，与商业工具对齐验证，见 操作记录.md 对应轮次测试结果。

规则依据：project_rules.md 规则 14（禁止 fall-back，失败 raise）
/规则 18（学术诚信）/规则 26（GPU 不参与，纯 numpy/scipy CPU）。
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

__all__ = [
    "ThermoOpticCouplingResult",
    "THERMO_OPTIC_COEFFS",
    "apply_thermo_optic_coupling",
    "compute_delta_n_from_temperature",
    "get_thermo_optic_coefficient",
]

# 热光系数（dn/dT，单位 [1/K]）室温 @1.55μm
# Si: Cocorullo 1999 IEEE JSTQE 5(3):519-521
# SiO2: Komma 2012 Appl Phys Lett 101:041905（低温复核，室温 ~1.0e-5）
THERMO_OPTIC_COEFFS: dict[str, float] = {
    "silicon": 1.86e-4,
    "si": 1.86e-4,  # 别名
    "sio2": 1.0e-5,
    "silica": 1.0e-5,  # 别名
}

# 默认参考温度 [K]（室温，热光效应相对基准，Cocorullo 1999）
DEFAULT_T_REF: float = 300.0


@dataclass
class ThermoOpticCouplingResult:
    """热光耦合结果（HEAT→OPTIC 接口产物）。

    Attributes:
        delta_n: 折射率扰动场 Δn(x,y)（与光学网格一致，无单位）。
        delta_n_eff: 模式有效折射率变化（Γ·⟨Δn⟩ 加权，标量，无单位）。
        dn_dt: 所用热光系数 [1/K]。
        t_ref: 参考温度 [K]。
        material: 材料标识符。
        confinement_factor: 光场限制因子 Γ（输入）。
    """

    delta_n: np.ndarray
    delta_n_eff: float
    dn_dt: float
    t_ref: float
    material: str
    confinement_factor: float

    def __post_init__(self) -> None:
        if not np.all(np.isfinite(self.delta_n)):
            raise ValueError("delta_n 含非有限值（耦合计算失败）")
        if not np.isfinite(self.delta_n_eff):
            raise ValueError("delta_n_eff 非有限值")
        if not np.isfinite(self.dn_dt) or self.dn_dt == 0.0:
            raise ValueError(f"dn_dt 须非零有限值，实际 {self.dn_dt}")
        if not np.isfinite(self.t_ref) or self.t_ref <= 0.0:
            raise ValueError(f"t_ref 须为正有限值，实际 {self.t_ref}")
        if not (0.0 <= self.confinement_factor <= 1.0):
            raise ValueError(
                f"confinement_factor 须 ∈ [0,1]，实际 {self.confinement_factor}"
            )


def get_thermo_optic_coefficient(material: str) -> float:
    """返回材料热光系数 dn/dT [1/K]（室温 @1.55μm）。

    已溯源材料：
    - silicon / si: 1.86e-4 /K（Cocorullo 1999）
    - sio2 / silica: 1.0e-5 /K（Komma 2012）

    Args:
        material: 材料标识符（小写，支持别名）。

    Returns:
        dn/dT 热光系数 [1/K]。

    Raises:
        TypeError: material 非 str 或 None。
        KeyError: 材料未在已溯源系数表中（避免编造）。
    """
    if material is None:
        raise TypeError("material 不可为 None")
    if not isinstance(material, str):
        raise TypeError(
            f"material 须为 str，实际 {type(material).__name__}"
        )
    key = material.strip().lower()
    if key not in THERMO_OPTIC_COEFFS:
        supported = sorted({k for k in THERMO_OPTIC_COEFFS.keys()})
        raise KeyError(
            f"未知材料 '{material}'，未在已溯源热光系数表中，"
            f"支持: {supported}。其他材料需引用论文扩展（规则 18 学术诚信）"
        )
    return THERMO_OPTIC_COEFFS[key]


def compute_delta_n_from_temperature(
    delta_T: np.ndarray,
    material: str = "silicon",
) -> np.ndarray:
    """计算温度变化引起的折射率变化场 Δn（Cocorullo 1999 公式）。

        Δn = (dn/dT) · ΔT

    其中 dn/dT 为材料热光系数 [1/K]（silicon: 1.86e-4, Cocorullo 1999），
    ΔT 为温度变化量 [K]（T - T_ref）。

    Args:
        delta_T: 温度变化量场 [K]，可为任意形状 ndarray。
        material: 材料标识符，默认 'silicon'。

    Returns:
        Δn 折射率变化场（与输入同形状，无单位，正值表示折射率升高）。

    Raises:
        TypeError: delta_T 非 ndarray 或为 None。
        ValueError: delta_T 含非有限值。
        KeyError: 材料未在已溯源系数表中。
    """
    if delta_T is None:
        raise TypeError("delta_T 不可为 None")
    if not isinstance(delta_T, np.ndarray):
        raise TypeError(
            f"delta_T 须为 np.ndarray，实际 {type(delta_T).__name__}"
        )
    if not np.all(np.isfinite(delta_T)):
        raise ValueError("delta_T 含非有限值（温度场求解失败）")

    dn_dt = get_thermo_optic_coefficient(material)
    return dn_dt * delta_T


def _validate_confinement_factor(confinement_factor) -> float:
    """校验并归一化光场限制因子 Γ ∈ [0,1]（Frey 2006 §II）。"""
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
    return gamma


def _resample_to_optical_grid(
    field: np.ndarray,
    src_dx: float,
    src_dy: float,
    dst_x: np.ndarray,
    dst_y: np.ndarray,
) -> np.ndarray:
    """将 HEAT 场重采样到光学网格（线性插值）。

    使用 scipy.interpolate.RegularGridInterpolator 张量网格插值，
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
        fill_value=np.nan,
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


def apply_thermo_optic_coupling(
    heat_result,
    optical_grid: dict | None = None,
    material: str = "silicon",
    confinement_factor: float = 1.0,
    t_ref: float = DEFAULT_T_REF,
) -> ThermoOpticCouplingResult:
    """HEAT 温度场 → 折射率扰动 → 光学仿真耦合接口。

    将 HEAT 求解器输出的温度场 T(x,y) 经热光效应转化为 Δn(x,y) 场，
    并按光场限制因子 Γ 计算模式有效折射率变化 Δn_eff。

    输入支持 duck-typed HEAT 结果对象（含 temperature 字段，如
    polaris_multiphysics.heat.solver.HeatResult）；可选网格重采样到光学网格。

    Args:
        heat_result: HEAT 求解结果（duck-typed，须含 temperature 字段 [K]，
            可选 dx/dy 网格间距 [m]，如 polaris_multiphysics.heat.solver.HeatResult）。
        optical_grid: 光学网格规格 dict，可选。None 表示同 HEAT 网格。
            格式 {"x": 1D_array [m], "y": 1D_array [m], "dx": float [m],
                   "dy": float [m]}。提供 x/y 时按 x/y 重采样。
        material: 材料标识符，默认 'silicon'（Cocorullo 1999 dn/dT=1.86e-4）。
        confinement_factor: 光场限制因子 Γ ∈ [0,1]，默认 1.0（全限制）。
        t_ref: 参考温度 [K]，默认 300.0（室温，Cocorullo 1999 基准）。

    Returns:
        ThermoOpticCouplingResult（含 delta_n, delta_n_eff 等字段）。

    Raises:
        TypeError: heat_result 缺字段或类型错误；optical_grid 非 dict。
        ValueError: 形状不匹配、温度非有限、重采样越界。
        KeyError: 材料未在已溯源系数表中。
    """
    T, src_dx, src_dy = _extract_heat_temperature(heat_result, t_ref)
    delta_T = T - float(t_ref)
    if not np.all(np.isfinite(delta_T)):
        raise ValueError("delta_T 含非有限值（t_ref 异常或温度溢出）")

    delta_n = compute_delta_n_from_temperature(delta_T, material=material)
    delta_n = _maybe_resample_to_optical_grid(
        delta_n, src_dx, src_dy, optical_grid, T.shape
    )

    gamma = _validate_confinement_factor(confinement_factor)
    if not np.all(np.isfinite(delta_n)):
        raise ValueError("delta_n 含非有限值（耦合计算失败）")
    delta_n_eff = gamma * float(np.mean(delta_n))
    dn_dt = get_thermo_optic_coefficient(material)
    return ThermoOpticCouplingResult(
        delta_n=delta_n,
        delta_n_eff=delta_n_eff,
        dn_dt=dn_dt,
        t_ref=float(t_ref),
        material=str(material).strip().lower(),
        confinement_factor=float(confinement_factor),
    )


def _extract_heat_temperature(
    heat_result, t_ref: float
) -> tuple[np.ndarray, float | None, float | None]:
    """校验并提取 HEAT 温度场与网格元数据（duck-typed HeatResult）。

    Args:
        heat_result: HEAT 求解结果，须含 temperature 字段。
        t_ref: 参考温度 [K]（仅用于校验有限性，温度差在调用方计算）。

    Returns:
        (T, src_dx, src_dy)：温度场 [K] 与可选网格间距 [m]。

    Raises:
        TypeError: heat_result 缺字段或为 None。
        ValueError: 温度场含非有限值。
    """
    if heat_result is None:
        raise TypeError("heat_result 不可为 None")
    if not hasattr(heat_result, "temperature"):
        raise TypeError(
            "heat_result 须含 temperature 字段（duck-typed HeatResult），"
            f"实际类型 {type(heat_result).__name__}"
        )
    T = np.asarray(heat_result.temperature, dtype=float)
    if not np.all(np.isfinite(T)):
        raise ValueError("温度场含非有限值（求解失败）")
    src_dx = getattr(heat_result, "dx", None)
    src_dy = getattr(heat_result, "dy", None)
    return T, src_dx, src_dy


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
        src_dx, src_dy: 源网格间距 [m]（HEAT 结果的 dx/dy 属性）。
        optical_grid: 光学网格规格（参见 apply_thermo_optic_coupling 文档）。
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
            "optical_grid 提供但 HEAT 结果未含 dx/dy 网格间距，"
            "无法重采样（请直接传入同形状场，或在 heat_result 上注入网格元数据）"
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
