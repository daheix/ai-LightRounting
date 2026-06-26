"""DDM ↔ HEAT 电热耦合接口（A08-DDM §电热耦合，SubTask 2.5.2）。

R01 方案检索记录（规则 1，动手前必做）：
- 关键词：Caughey Thomas mobility temperature silicon / Joule heating
  semiconductor drift diffusion / DDM HEAT electrothermal coupling
- 采用方案：
  (1) 焦耳热：分载流子 Q = J_n²/(q·μ_n·n) + J_p²/(q·μ_p·p)（Lundstrom
      2000 §3，每一载流子流的欧姆耗散之和），与 heat/coupling.py:ddm_to_heat
      的总电流形式 Q = |J|²/σ 在纯漂移极限下等价。
  (2) 温度→迁移率：晶格散射极限 μ(T) = μ_0·(T_0/T)^1.5（Caughey-Thomas
      1977；Sze 2006 §2，μ∝T^-3/2 来自声学声子散射）。
- 来源：Caughey-Thomas 1977；Sze 2006；Lundstrom 2000；Incropera。

物理公式（学术诚信，规则 18）：

焦耳热（Incropera §3.6 体积热源；Lundstrom 2000 §3）：
    Q = J·E = J²/σ   [W/m³]
分载流子形式（电子与空穴各自欧姆耗散之和）：
    J_n = q·μ_n·n·E + q·D_n·∇n（漂移+扩散）
    J_p = q·μ_p·p·E - q·D_p·∇p
    Q = J_n²/(q·μ_n·n) + J_p²/(q·μ_p·p)
其中 D = μ·V_T（Einstein 关系）。该热源注入 HeatConfig.q_arr 实现自热
（DDM→HEAT 单向，已由 A07 heat/coupling.py:ddm_to_heat 提供总电流形式
入口；本模块提供从 DdmResult 与 DdmConfig 计算分载流子焦耳热的接口）。

Caughey-Thomas 迁移率温度模型（Caughey-Thomas 1977；Sze 2006 §2）：
完整模型含晶格散射、杂质散射与高场饱和：
    μ_L(N,T) = μ_min + (μ_L(T) - μ_min)/(1+(N/N_ref)^α)
其中晶格散射极限（纯材料，低掺杂）：
    μ_L(T) = μ_0·(T_0/T)^1.5
指数 1.5 来自声学声子散射的形变势理论（Bardeen-Shockley 1950）。
本模块实现晶格散射温度修正（任务 spec 指定 μ(T)=μ_0·(T_0/T)^1.5），
用于 HEAT→DDM 耦合：温度场修正迁移率，反馈到 DDM 连续性方程。

*创新* 双向耦合闭环：
- DDM→HEAT：ddm_to_heat_joule 产出焦耳热 Q 场，注入 HeatConfig.q_arr。
- HEAT→DDM：heat_to_ddm_mobility 由温度场修正 μ_n/μ_p，反馈到 DdmConfig。
解耦接口契约使两方向可独立验证与替换（单一职责，与 heat/coupling.py
风格一致）。底层逻辑：电热耦合是弱耦合（时间尺度分离），分载流子
焦耳热比总电流形式 Q=J²/σ 更精确刻画自热分布（Lundstrom 2000）。

文献来源（≥5，规则 18 学术诚信）：
1. Caughey & Thomas 1977 Proc IEEE 55(12):2192-2193 "Carrier Mobilities
   in Silicon Empirically Related to Doping and Field" —
   https://doi.org/10.1109/PROC.1967.6060
2. Sze & Ng 2006 "Physics of Semiconductor Devices" 3rd ed Wiley
   §2 μ∝T^-3/2 晶格散射 — https://www.wiley.com/en-us/9780471143239
3. Lundstrom 2000 "Fundamentals of Carrier Transport" Cambridge
   §3 焦耳热与欧姆耗散 —
   https://www.cambridge.org/core/books/fundamentals-of-carrier-transport/
4. Incropera & DeWitt "Fundamentals of Heat and Mass Transfer"
   §3.6 体积热源 Joule 热 —
   https://www.wiley.com/en-us/Fundamentals+of+Heat+and+Mass+Transfer
5. Selberherr 1984 "Analysis and Simulation of Semiconductor Devices"
   §2 漂移扩散电流密度 —
   https://link.springer.com/book/10.1007/978-3-7091-8753-2
6. Bardeen & Shockley 1950 Phys Rev 80:72-80 "Deformation Potentials
   and Mobilities in Non-Polar Crystals"（声学声子散射 T^-1.5 理论）—
   https://doi.org/10.1103/PhysRev.80.72
7. COMSOL Semiconductor Module "Caughey-Thomas Mobility" —
   https://doc.comsol.com/5.6/doc/com.comsol.help.models.semicond.caughey_thomas_mobility/

规则依据：project_rules.md 规则 14（禁止 fall-back，失败 raise）
/规则 18（学术诚信）/规则 26（GPU 不参与，纯 numpy/scipy CPU）。
"""

from __future__ import annotations

import numpy as np

from polaris.sim.ddm.scharfetter_gummel import (
    MU_N_SI,
    MU_P_SI,
    Q_E,
    T_DEFAULT,
)
from polaris.sim.ddm.solver import DdmConfig, DdmResult

__all__ = [
    "ddm_to_heat_joule",
    "heat_to_ddm_mobility",
    "LATTICE_SCATTERING_EXPONENT",
]

# Caughey-Thomas 晶格散射温度指数（Sze 2006 §2；Bardeen-Shockley 1950
# 声学声子形变势理论 μ ∝ T^-3/2，即指数 1.5）。
LATTICE_SCATTERING_EXPONENT: float = 1.5


def ddm_to_heat_joule(result: DdmResult, config: DdmConfig) -> np.ndarray:
    """从 DdmResult 计算分载流子焦耳热 Q = J_n²/(q·μ_n·n) + J_p²/(q·μ_p·p)。

    分载流子欧姆耗散（Lundstrom 2000 §3）：每一载流子流的焦耳热
    Q_c = J_c²/σ_c = J_c²/(q·μ_c·c)，总焦耳热 = Q_n + Q_p。
    与 heat/coupling.py:ddm_to_heat 的 Q=|J|²/σ 总电流形式在纯漂移
    （无扩散）极限下等价；本接口保留扩散电流贡献，更精确刻画自热分布。

    J_n/J_p 由 DdmResult 的电场 E=-∇φ 与浓度梯度 ∇n/∇p 重新计算
    （DdmResult 仅存总电流分量，未分载流子存档）：
        J_n = q·μ_n·n·E + q·D_n·∇n
        J_p = q·μ_p·p·E - q·D_p·∇p（空穴扩散项取负，对应反向电流）

    Args:
        result: DDM 求解结果（须含 electron_density, hole_density,
            e_field_x, e_field_y 字段，由 DdmSolver/GummelSolver 产出）。
        config: DDM 配置（须含 mobility_n, mobility_p, dx, dy, vt, n_i）。

    Returns:
        体积焦耳热密度 (nx, ny) [W/m³]，全为非负有限值。

    Raises:
        ValueError: 输入形状不匹配或产生非有限值（R03 禁止 fall-back）。
    """
    n = result.electron_density
    p = result.hole_density
    if n.shape != p.shape:
        raise ValueError(f"n 形状 {n.shape} ≠ p 形状 {p.shape}")
    if not np.all(np.isfinite(n)) or np.any(n < 0.0):
        raise ValueError("electron_density 须全为非负有限值")
    if not np.all(np.isfinite(p)) or np.any(p < 0.0):
        raise ValueError("hole_density 须全为非负有限值")

    ex = result.e_field_x
    ey = result.e_field_y
    if ex.shape != n.shape or ey.shape != n.shape:
        raise ValueError("e_field 分量形状与载流子浓度不一致")

    dx, dy = config.dx, config.dy
    vt = config.vt
    D_n = config.mobility_n * vt  # Einstein 扩散系数
    D_p = config.mobility_p * vt

    # 浓度梯度（1D 该方向置零，edge_order=1 保证边界一阶精度）
    nx, ny = n.shape
    dn_dx = np.gradient(n, dx, axis=0, edge_order=1) if nx >= 2 else np.zeros_like(n)
    dn_dy = np.gradient(n, dy, axis=1, edge_order=1) if ny >= 2 else np.zeros_like(n)
    dp_dx = np.gradient(p, dx, axis=0, edge_order=1) if nx >= 2 else np.zeros_like(p)
    dp_dy = np.gradient(p, dy, axis=1, edge_order=1) if ny >= 2 else np.zeros_like(p)

    # 分载流子电流密度分量（Selberherr 1984 §2）
    jn_x = Q_E * config.mobility_n * n * ex + Q_E * D_n * dn_dx
    jn_y = Q_E * config.mobility_n * n * ey + Q_E * D_n * dn_dy
    jp_x = Q_E * config.mobility_p * p * ex - Q_E * D_p * dp_dx
    jp_y = Q_E * config.mobility_p * p * ey - Q_E * D_p * dp_dy

    jn_sq = jn_x**2 + jn_y**2
    jp_sq = jp_x**2 + jp_y**2
    # 下界防除零：n,p 永远 > 0（本征热激发），取 max(c, n_i)
    n_eff = np.maximum(n, config.n_i)
    p_eff = np.maximum(p, config.n_i)
    q_joule = jn_sq / (Q_E * config.mobility_n * n_eff) + jp_sq / (Q_E * config.mobility_p * p_eff)
    if not np.all(np.isfinite(q_joule)) or np.any(q_joule < 0.0):
        raise ValueError("焦耳热计算产生非有限或负值（输入非法）")
    return q_joule


def heat_to_ddm_mobility(
    temperature: np.ndarray | float,
    mu_n0: float = MU_N_SI,
    mu_p0: float = MU_P_SI,
    t0: float = T_DEFAULT,
) -> tuple[np.ndarray | float, np.ndarray | float]:
    """温度→迁移率修正 μ(T) = μ_0·(T_0/T)^1.5（Caughey-Thomas 晶格散射）。

    晶格散射极限（Caughey-Thomas 1977；Sze 2006 §2）：声学声子散射使
    迁移率随温度升高而下降，μ ∝ T^-3/2（指数 1.5，Bardeen-Shockley 1950
    形变势理论）。用于 HEAT→DDM 耦合：温度场修正迁移率反馈到 DdmConfig。

    Args:
        temperature: 温度场 [K]（标量或 ndarray）。
        mu_n0, mu_p0: 参考温度 t0 处的电子/空穴迁移率 [m²/(V·s)]，
            默认硅 300K 值（μ_n0=0.135, μ_p0=0.048）。
        t0: 参考温度 [K]，默认 300。

    Returns:
        (mu_n, mu_p)：温度 T 处的电子/空穴迁移率（标量输入返回标量，
        数组输入返回数组）。

    Raises:
        ValueError: 温度/迁移率/参考温度非正或非有限（R03 禁止 fall-back）。
    """
    T_arr = np.asarray(temperature, dtype=float)
    if not np.all(np.isfinite(T_arr)) or np.any(T_arr <= 0.0):
        raise ValueError("temperature 须全为正有限值（热力学温度物理约束）")
    if mu_n0 <= 0.0 or mu_p0 <= 0.0:
        raise ValueError(f"mu_n0/mu_p0 须 >0，实际 mu_n0={mu_n0} mu_p0={mu_p0}")
    if t0 <= 0.0:
        raise ValueError(f"t0 须 >0，实际 {t0}")
    factor = (t0 / T_arr) ** LATTICE_SCATTERING_EXPONENT
    mu_n = mu_n0 * factor
    mu_p = mu_p0 * factor
    # 标量输入返回 Python float（保持调用方类型期望）
    if T_arr.ndim == 0:
        return float(mu_n), float(mu_p)
    return mu_n, mu_p
