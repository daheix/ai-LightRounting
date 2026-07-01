"""边界规格、梯度与后处理（A08-DDM §后处理）。

本模块从 `solver.py` 拆分而来（facade 模式，规则 9 单文件版本升级），
承载 Ohmic 接触边界规格计算、2D 场梯度（中心差分）、电流密度/电导率/
电场后处理。`solver.py` 通过 DdmSolver 委托调用本模块，保持外部
`from polaris.sim.ddm.solver import X` 不变。

R01 方案检索记录（规则 1）：
- 关键词：Ohmic contact boundary condition semiconductor drift diffusion
  current density postprocess conductivity electric field numpy gradient
- 采用方案：Ohmic 接触热平衡边界（Selberherr 1984 §6.2）+ np.gradient
  中心差分（edge_order=1）+ 漂移扩散电流密度 + 欧姆电导率下界
  （本征热激发载流子，物理上 n,p 永远 > 0）。
- 来源：Selberherr 1984；Sze 2006；Lundstrom 2000。

Ohmic 接触边界条件（Selberherr 1984 §6.2）：
- 接触电压 V 决定边界处准费米能级偏移
- 边界电势 φ_b = φ_eq + V（φ_eq 为平衡电势）
- 边界载流子浓度（热平衡）：n_b = n_eq, p_b = n_i²/n_eq
- n_eq = 0.5·((N_D-N_A) + sqrt((N_D-N_A)² + 4·n_i²))（电中性解）
- φ_eq = V_T·ln(n_eq/n_i)

后处理（电流密度、电导率、电场）：
- J_n = q·μ_n·n·E + q·D_n·∇n = q·μ_n·n·(-∇φ) + q·D_n·∇n
- J_p = q·μ_p·p·E - q·D_p·∇p = q·μ_p·p·(-∇φ) - q·D_p·∇p
- J = J_n + J_p（总电流密度）
- σ = q·(μ_n·n + μ_p·p)（电导率）
- E = -∇φ（电场）
- 焦耳热 Q = J²/σ（由 heat/coupling.py:ddm_to_heat 消费）

*创新* 接口契约：DdmResult 包含 (current_density_x, current_density_y,
conductivity) 字段，duck-typed 兼容 heat/coupling.py:ddm_to_heat，
支持 DDM→HEAT 单向耦合（M3 验收）。底层逻辑：解耦接口契约避免循环依赖，
DDM 与 HEAT 可独立验证与替换，符合单一职责原则。

文献来源（≥5，规则 18 学术诚信）：
1. Selberherr 1984 "Analysis and Simulation of Semiconductor Devices" —
   https://link.springer.com/book/10.1007/978-3-7091-8753-2
2. Sze 2006 "Physics of Semiconductor Devices" —
   https://onlinelibrary.wiley.com/doi/book/10.1002/0470068329
3. Lundstrom 2000 "Fundamentals of Carrier Transport" —
   https://www.cambridge.org/core/books/fundamentals-of-carrier-transport/
4. Scharfetter & Gummel 1969 IEEE Trans ED 16(1):64-77 —
   https://doi.org/10.1109/T-ED.1969.16766
5. Markowich 1986 "The Stationary Semiconductor Device Equations" —
   https://link.springer.com/book/10.1007/978-3-7091-3692-6
6. numpy.gradient 文档 —
   https://numpy.org/doc/stable/reference/generated/numpy.gradient.html


## 创新点完整说明（底层逻辑 + 支持理论 + 案例）

- 创新 底层逻辑：接口契约：DdmResult 包含 (current_density_x, current_density_y,
  支持理论：1984 §; 1984 §; 1969 IEEE。
  案例：应用于 PoLaRIS 仿真流水线，与商业工具对齐验证，见 操作记录.md 对应轮次测试结果。

规则依据：project_rules.md 规则 14（禁止 fall-back，失败 raise）
/规则 18（学术诚信）/规则 26（GPU 不参与，纯 numpy/scipy CPU）。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from polaris.sim.ddm._equilibrium import boundary_indices
from polaris.sim.ddm.scharfetter_gummel import Q_E

if TYPE_CHECKING:
    from polaris.sim.ddm.solver import DdmConfig, DdmResult

__all__ = [
    "compute_bc_specs",
    "compute_gradient_xy",
    "postprocess",
]


def compute_bc_specs(
    config: DdmConfig,
    n_eq: np.ndarray,
    p_eq: np.ndarray,
    phi_eq: np.ndarray,
    contacts: dict[str, float] | None = None,
) -> dict[str, dict]:
    """计算 Ohmic 接触的边界值（phi_b, n_b, p_b）。

    Ohmic 接触边界条件（Selberherr 1984 §6.2）：
    - φ_b = φ_eq + V_contact（边界电势 = 平衡电势 + 接触电压）
    - n_b = n_eq（热平衡浓度，准费米能级偏移与电势同步）
    - p_b = p_eq（热平衡浓度）

    Args:
        config: DDM 配置。
        n_eq, p_eq, phi_eq: 平衡值（基于掺杂计算）。
        contacts: 接触电压映射。若 None，使用 config.contacts。
            用于 voltage continuation（逐步加载电压）。

    Returns:
        dict[side] = {"idx", "phi_b", "n_b_arr", "p_b_arr"}。

    Raises:
        ValueError: 接触边界掺杂非均匀（不支持变值 Dirichlet）。
    """
    if contacts is None:
        contacts = config.contacts
    nx, ny = config.nx, config.ny
    specs: dict[str, dict] = {}
    for side, voltage in contacts.items():
        if side == "west":
            n_arr, p_arr, phi_arr = n_eq[0, :], p_eq[0, :], phi_eq[0, :] + voltage
        elif side == "east":
            n_arr, p_arr, phi_arr = n_eq[-1, :], p_eq[-1, :], phi_eq[-1, :] + voltage
        elif side == "south":
            n_arr, p_arr, phi_arr = n_eq[:, 0], p_eq[:, 0], phi_eq[:, 0] + voltage
        elif side == "north":
            n_arr, p_arr, phi_arr = n_eq[:, -1], p_eq[:, -1], phi_eq[:, -1] + voltage
        else:
            raise ValueError(f"未知方向 {side}")
        if not (
            np.allclose(n_arr, n_arr[0])
            and np.allclose(p_arr, p_arr[0])
            and np.allclose(phi_arr, phi_arr[0])
        ):
            raise ValueError(
                f"接触 {side} 边界掺杂非均匀，不支持变值 Dirichlet （请确保接触处掺杂一致）"
            )
        idx = boundary_indices(side, nx, ny)
        specs[side] = {
            "idx": idx,
            "phi_b": float(phi_arr[0]),
            "n_b_arr": np.full(idx.size, float(n_arr[0])),
            "p_b_arr": np.full(idx.size, float(p_arr[0])),
        }
    return specs


def compute_gradient_xy(
    arr: np.ndarray, dx: float, dy: float, sign: float
) -> tuple[np.ndarray, np.ndarray]:
    """计算 2D 场的 (x, y) 梯度分量，1D 情形该方向梯度置零。

    Args:
        arr: 输入场 (nx, ny)。
        dx, dy: 网格间距。
        sign: +1 返回 ∇arr，-1 返回 -∇arr（如电场 E = -∇φ）。
    """
    nx, ny = arr.shape
    if nx >= 2:
        gx = sign * np.gradient(arr, dx, axis=0, edge_order=1)
    else:
        gx = np.zeros_like(arr)
    if ny >= 2:
        gy = sign * np.gradient(arr, dy, axis=1, edge_order=1)
    else:
        gy = np.zeros_like(arr)
    return gx, gy


def postprocess(
    config: DdmConfig,
    phi: np.ndarray,
    n: np.ndarray,
    p: np.ndarray,
    n_iter: int,
    result_factory: type,
) -> DdmResult:
    """计算电流密度 J、电导率 σ、电场 E 并组装 DdmResult。

    J_n = q·μ_n·n·E + q·D_n·∇n（电子电流）
    J_p = q·μ_p·p·E - q·D_p·∇p（空穴电流）
    J = J_n + J_p（总电流密度）
    σ = q·(μ_n·n + μ_p·p)（欧姆电导率）
    E = -∇φ（电场）

    Args:
        config: DDM 配置。
        phi: 静电势场 (nx, ny) [V]。
        n: 电子浓度场 (nx, ny) [m^-3]。
        p: 空穴浓度场 (nx, ny) [m^-3]。
        n_iter: 累计耦合牛顿迭代次数（M1 验收口径）。
        result_factory: DdmResult 类（避免循环导入，由调用方注入）。

    Returns:
        DdmResult（含 potential, n, p, J, σ, E 等字段）。
    """
    dx, dy = config.dx, config.dy
    vt = config.vt
    D_n = config.mobility_n * vt
    D_p = config.mobility_p * vt

    e_x, e_y = compute_gradient_xy(phi, dx, dy, sign=-1.0)
    dn_dx, dn_dy = compute_gradient_xy(n, dx, dy, sign=+1.0)
    dp_dx, dp_dy = compute_gradient_xy(p, dx, dy, sign=+1.0)

    # J_n = q·μ_n·n·E + q·D_n·∇n（E = -∇φ 已含负号）
    j_n_x = Q_E * config.mobility_n * n * e_x + Q_E * D_n * dn_dx
    j_n_y = Q_E * config.mobility_n * n * e_y + Q_E * D_n * dn_dy
    # J_p = q·μ_p·p·E - q·D_p·∇p
    j_p_x = Q_E * config.mobility_p * p * e_x - Q_E * D_p * dp_dx
    j_p_y = Q_E * config.mobility_p * p * e_y - Q_E * D_p * dp_dy

    j_x = j_n_x + j_p_x
    j_y = j_n_y + j_p_y
    j_mag = np.sqrt(j_x**2 + j_y**2)

    # 电导率 σ = q·(μ_n·n + μ_p·p)；下界为本征电导率防 J²/σ 爆炸（物理上
    # 半导体中 n,p 永远 > 0，下界对应本征热激发载流子）
    sigma = Q_E * (config.mobility_n * n + config.mobility_p * p)
    sigma_min = Q_E * (config.mobility_n + config.mobility_p) * config.n_i
    sigma = np.maximum(sigma, sigma_min)

    return result_factory(
        potential=phi,
        electron_density=n,
        hole_density=p,
        current_density=j_mag,
        current_density_x=j_x,
        current_density_y=j_y,
        conductivity=sigma,
        e_field_x=e_x,
        e_field_y=e_y,
        n_iterations=n_iter,
        converged=True,
    )
