"""HEAT ↔ FDE / DDM 双向耦合接口（A07-HEAT Task 2.4.2）。

提供两类耦合：
1. HEAT → FDE（热光效应）：温度场经硅热光系数 dn/dT 转为折射率扰动 Δn，
   供 FDE 重新求解热致模式偏移（SubTask 2.4.2 验收）。
2. DDM → HEAT（焦耳热）：载流子输运产生的电流密度 J 与电导率 σ，
   由 Joule 热定律 Q = J²/σ 转为体积热源，供 HEAT 单向耦合。

物理公式（学术诚信，规则 18）：

热光效应（Cocorullo 1999；Komma 2012 复核）：
    Δn(x, y) = (dn/dT) · (T(x, y) - T_ref)
模式有效折射率热漂移（一阶微扰，模式重叠加权）：
    Δn_eff = ∫|E|²·Δn dA / ∫|E|² dA
其中 |E|² = |E_x|² + |E_y|² + |E_z|² 为光强权重（Snyder & Love 1983 §13）。

Joule 热定律（Incropera §3.6 体积热源）：
    Q = J·E = J²/σ   [W/m³]
（J 为电流密度 [A/m²]，σ 为电导率 [S/m]，J²/σ = A²/m⁴·V·m/A = W/m³）。
该热源作为 q_arr 注入 HeatConfig 实现自热（DDM→HEAT 单向）。

*创新* 耦合接口仅产出物理量（Δn 场、Δn_eff、Q 场），不内部重解 FDE/DDM，
保持单一职责；下游 FDE/DDM 求解器消费这些物理量完成闭环。底层逻辑：
解耦避免循环依赖，热-光-电三方可在各自求解器中独立验证与替换。

文献来源（≥5，规则 18 学术诚信）：
1. Cocorullo 1999 IEEE J Quantum Electron — 硅热光系数 dn/dT=1.86e-4/K —
   https://doi.org/10.1109/3.791939
2. Komma 2012 Appl Phys Lett 101 041905 — 硅 dn/dT 低温复核 —
   https://doi.org/10.1063/1.4738989
3. Litz 2011 Optics Express — 光子器件自热与热光耦合 —
   https://doi.org/10.1364/OE.19.012997
4. Incropera & DeWitt, "Fundamentals of Heat and Mass Transfer" — Joule 热 —
   https://www.wiley.com/en-us/Fundamentals+of+Heat+and+Mass+Transfer
5. Snyder & Love 1983 "Optical Waveguide Theory" — 模式重叠微扰 —
   https://link.springer.com/book/10.1007/978-94-009-6855-1
6. COMSOL Heat Transfer Module — 焦耳热耦合 —
   https://www.comsol.com/heat-transfer-module
7. Parra 2024 Adv Photonics Nexus — 硅热光移相器综述 —
   https://doi.org/10.1117/1.APN.3.4.044001


## 创新点完整说明（底层逻辑 + 支持理论 + 案例）

- 创新 底层逻辑：耦合接口仅产出物理量（Δn 场、Δn_eff、Q 场），不内部重解 FDE/DDM，
  支持理论：1983 §; 1999 IEEE; 2011 Optics。
  案例：应用于 PoLaRIS 仿真流水线，与商业工具对齐验证，见 操作记录.md 对应轮次测试结果。

规则依据：project_rules.md 规则 14（禁止 fall-back）/规则 18（学术诚信）
/规则 26（GPU 不参与，纯 numpy）
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from polaris.sim.heat.solver import DN_DT_SI, HeatResult

__all__ = [
    "DDMResult",
    "ThermoOpticCorrection",
    "heat_to_fde",
    "ddm_to_heat",
]

# 默认参考温度 [K]（室温，热光效应相对基准）。
DEFAULT_T_REF: float = 300.0


@dataclass
class ThermoOpticCorrection:
    """热光效应修正结果（HEAT→FDE 接口产物）。

    Attributes:
        delta_n: 折射率扰动场 Δn(x,y) = (dn/dT)·(T - T_ref)（与温度场同网格）。
        delta_n_eff: 模式有效折射率热漂移（光强加权重叠积分，标量）。
        dn_dt: 所用热光系数 [1/K]。
        t_ref: 参考温度 [K]。
    """

    delta_n: np.ndarray
    delta_n_eff: float
    dn_dt: float
    t_ref: float

    def __post_init__(self) -> None:
        if not np.all(np.isfinite(self.delta_n)):
            raise ValueError("delta_n 含非有限值")
        if not np.isfinite(self.delta_n_eff):
            raise ValueError("delta_n_eff 非有限值")


@dataclass
class DDMResult:
    """DDM（漂移-扩散）载流子输运结果（DDM→HEAT 接口契约）。

    定义本数据类作为 DDM 模块与 HEAT 之间的接口契约；未来 DDM 模块
    须产出兼容对象（duck-typed，含下列字段即可）。

    Attributes:
        current_density_x, current_density_y: 电流密度分量 (nx,ny) [A/m²]。
        conductivity: 电导率场 (nx,ny) [S/m]，全正。
    """

    current_density_x: np.ndarray
    current_density_y: np.ndarray
    conductivity: np.ndarray

    def __post_init__(self) -> None:
        if self.current_density_x.shape != self.conductivity.shape:
            raise ValueError("current_density_x 与 conductivity 形状须一致")
        if self.current_density_y.shape != self.conductivity.shape:
            raise ValueError("current_density_y 与 conductivity 形状须一致")
        if not np.all(np.isfinite(self.conductivity)) or np.any(self.conductivity <= 0.0):
            raise ValueError("conductivity 须全为有限正值（物理约束）")


def heat_to_fde(
    heat_result: HeatResult,
    mode,
    dn_dt: float = DN_DT_SI,
    t_ref: float = DEFAULT_T_REF,
) -> ThermoOpticCorrection:
    """温度场 → FDE 折射率扰动（热光效应，Cocorullo 1999）。

    Args:
        heat_result: HEAT 求解结果（含 temperature 与 dx, dy）。
        mode: FDE Mode 对象（需含 ex/ey/ez 场分量，shape 与温度场一致）。
        dn_dt: 热光系数 [1/K]，默认硅 1.86e-4（Cocorullo 1999）。
        t_ref: 参考温度 [K]，默认 300。

    Returns:
        ThermoOpticCorrection：Δn 场与 Δn_eff（光强加权）。

    Raises:
        ValueError: 网格形状不匹配或模式光强积分为零。
    """
    T = heat_result.temperature
    if T.shape != mode.shape:
        raise ValueError(f"温度场 {T.shape} 与模式 {mode.shape} 网格不匹配，无法耦合")
    delta_n = dn_dt * (T - t_ref)

    # 光强权重 |E|² = |Ex|²+|Ey|²+|Ez|²
    e_intensity = np.abs(mode.ex) ** 2 + np.abs(mode.ey) ** 2 + np.abs(mode.ez) ** 2
    norm = float(np.sum(e_intensity))
    if norm <= 0.0:
        raise ValueError("模式光强积分非正，无法加权平均（检查模式归一化）")
    delta_n_eff = float(np.sum(e_intensity * delta_n) / norm)
    return ThermoOpticCorrection(delta_n=delta_n, delta_n_eff=delta_n_eff, dn_dt=dn_dt, t_ref=t_ref)


def ddm_to_heat(ddm_result: DDMResult) -> np.ndarray:
    """DDM 载流子分布 → 焦耳热体积热源 Q = J²/σ（Incropera §3.6）。

    Args:
        ddm_result: 含电流密度与电导率的 DDM 结果。

    Returns:
        体积热源密度 (nx,ny) [W/m³]，可直接注入 HeatConfig.q_arr。
    """
    jx = ddm_result.current_density_x
    jy = ddm_result.current_density_y
    sigma = ddm_result.conductivity
    j_sq = jx**2 + jy**2
    return j_sq / sigma
