"""2D Yee leapfrog 时间步进（A06-VarFDTD §3，复用 A09-FDTD YeeGrid）。

VarFDTD 在 EIM 折叠后的 2D 等效折射率平面上执行标准 2D FDTD 时间步进。
本模块复用 A09-FDTD 的 YeeGridFdtd（已含 ca/cb/da/db 更新系数与 Courant 校验），
仅提供 VarFDTD 特定的轻量封装：
- build_2d_grid：从 n_eff_arr 构造 2D Yee 网格（eps_r = n_eff²）；
- step_leapfrog：单步 leapfrog 推进（H 半步 → E 半步），可选叠加 CPML/TFSF 校正；
- te/z 与 tm/z 共享同一更新公式（Yee 1966 标准形式），仅偏振分量不同。

== Yee 交错网格（与 A09 §3 一致）==
    E_z[i, j]    位于 (i·dx,     j·dy)
    H_x[i, j]    位于 (i·dx,     (j+0.5)·dy)  —— j∈[0, ny-2] 物理有效
    H_y[i, j]    位于 ((i+0.5)·dx, j·dy)        —— i∈[0, nx-2] 物理有效

== leapfrog 更新（Taflove 2005 §3.7，二阶精度 O(Δt², Δh²)）==
    H^{n+1/2} = D_a·H^{n-1/2} - D_b·∇×E^n           (+ CPML ψ_h)
    E^{n+1}   = C_a·E^n       + C_b·∇×H^{n+1/2}      (+ CPML ψ_e)

Courant-Friedrichs-Lewy 稳定性（2D）：
    Δt ≤ 1/(c·√(1/Δx² + 1/Δy²))
工程取 0.99 倍上限（与 A09 一致）。

== VarFDTD 物理诠释（A06 §3）==
- EIM 折叠后 2D 平面的"等效光速"为 c/n_eff(x, y)；
- 因此 eps_r(x, y) = n_eff(x, y)²，包含波导色散与材料色散信息；
- 标准 leapfrog 在该平面上推进，等效于求解 3D 麦克斯韦方程的近似解
  （仅在水平方向全波求解，垂直方向已通过 EIM 折叠）。

*创新*：复用 A09-FDTD 的 YeeGridFdtd 与 build_update_coefficients，
避免重复实现更新系数公式；本模块仅添加"从 n_eff_arr 构造 eps_r 网格"
与"单步 leapfrog 函数"，与 A09-FDTD solver 解耦但共享底座。
- 底层逻辑：n_eff_arr → eps_r_arr = n_eff² → 标准 YeeGridFdtd；
  单步 leapfrog 直接调用 A09 的 cpml.update_h_psi/update_e_psi。
- 支持理论：Yee 1966 证明 2D leapfrog 二阶稳定；
  Hammer-Ivanova 2008 / Snyder-Love 1983 证明 EIM+2D FDTD 等价 3D FDTD（弱耦合假设）。
- 案例：SOI 环透射谱、Y 分支、波导光栅等 2.5D 仿真。

== 检索记录（R01 方案检索）==
- 关键词："varFDTD effective index method Lumerical"
- 关键词："effective index method waveguide 2D FDTD reduction"
- 关键词："Yee 1966 leapfrog 2D TEz"
- 采用方案：复用 A09-FDTD YeeGridFdtd + 单步 leapfrog 函数
- 来源：Ansys varFDTD 文档、Yee 1966、Taflove 2005、Lumerical

文献来源（≥5，规则 18 学术诚信）：
1. Yee 1966 IEEE Trans AP 14(3) 302-307 —
   https://doi.org/10.1109/TAP.1966.1138693
2. Taflove & Hagness 2005 Computational Electrodynamics §3 —
   https://www.artechhouse.com/Computational-Electrodynamics/Kane-Taflove/p/Book-927
3. Hammer MPB & Ivanova EV, "Effective index approximation for
   photonic crystal slabs," JOSA B 36(7) (2009)... 原始 Hammer-Ivanova 变分法
   参考 Ansys Optics varFDTD solver introduction —
   https://optics.ansys.com/hc/en-us/articles/360034917213
4. Snyder AW & Love JD, "Optical Waveguide Theory" (1983) — reciprocity-based
   varFDTD approach（参考 Ansys varFDTD 文档）—
   https://www.springer.com/gp/book/9780412099504
5. Chang 1980 IEEE Trans MTT 28(8) 889 (EIM) —
   https://doi.org/10.1109/TMTT.1980.1130551
6. Soref 1991 IEEE JQE 27(8) 1971 —
   https://doi.org/10.1109/3.84143
7. Lumerical varFDTD — https://www.lumerical.com/products/varfdtd/

规则依据：规则 14（非法输入 raise，无 fall-back）/规则 18（学术诚信）/
规则 26（纯 CPU numpy）/规则 9（单文件版本，复用 A09 不重写）
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from polaris_multiphysics.varfdtd.cpml import (
    CpmlBuffers,
    CpmlCoefficients,
    update_e_psi,
    update_h_psi,
)
from polaris_multiphysics.varfdtd.yee_grid import YeeGridFdtd, courant_dt

__all__ = [
    "Yee2DFields",
    "build_2d_grid",
    "step_leapfrog",
    "build_eps_from_neff",
]


@dataclass
class Yee2DFields:
    """2D Yee 场容器（A06 §3）。

    Attributes:
        e_z: 电场 E_z (Nx, Ny)，float64。
        h_x: 磁场 H_x (Nx, Ny)，float64（边界半步位置保持 0）。
        h_y: 磁场 H_y (Nx, Ny)，float64。
    """

    e_z: np.ndarray
    h_x: np.ndarray
    h_y: np.ndarray

    @classmethod
    def zeros(cls, shape: tuple[int, int]) -> Yee2DFields:
        """分配全零场（与 YeeGridFdtd.allocate_fields 一致）。"""
        z = np.zeros(shape, dtype=np.float64)
        return cls(e_z=z.copy(), h_x=z.copy(), h_y=z.copy())

    def check_nan(self, name: str = "fields") -> None:
        """NaN/Inf 检查（A06 §M2 稳定性验收，规则 14 失败 raise）。"""
        for fname, arr in (("e_z", self.e_z), ("h_x", self.h_x), ("h_y", self.h_y)):
            if not np.all(np.isfinite(arr)):
                raise FloatingPointError(
                    f"{name}.{fname} 含 NaN/Inf（leapfrog 不稳定），建议减小 dt 或检查源/材料参数"
                )


def build_eps_from_neff(n_eff_arr: np.ndarray) -> np.ndarray:
    """从有效折射率数组构造 2D 相对介电常数分布（A06 §3）。

    eps_r = n_eff²（EIM 折叠后的等效介电常数，包含波导+材料色散）。

    Args:
        n_eff_arr: (Nx, Ny) 有效折射率分布，>0。

    Returns:
        (Nx, Ny) 相对介电常数，>0。

    Raises:
        ValueError: n_eff_arr 含非正值（规则 14）。
    """
    arr = np.asarray(n_eff_arr, dtype=np.float64)
    if arr.ndim != 2:
        raise ValueError(f"n_eff_arr 须 2D，实际 {arr.ndim}D")
    if np.any(arr <= 0.0):
        raise ValueError("n_eff_arr 所有元素须 >0（折射率非物理零或负）")
    return arr * arr


def build_2d_grid(
    n_eff_arr: np.ndarray,
    dx: float,
    dy: float,
    dt: float | None = None,
    cfl: float = 0.99,
) -> YeeGridFdtd:
    """从 n_eff_arr 构造 2D Yee 网格（A06 §3）。

    Args:
        n_eff_arr: (Nx, Ny) 有效折射率分布，>0。
        dx, dy: 网格间距（米），>0。
        dt: 时间步（秒），None 则按 Courant 上限×cfl 自动计算。
        cfl: Courant 数，dt=None 时使用，∈ (0, 1]。

    Returns:
        YeeGridFdtd 实例（含 ca/cb/da/db 预计算系数，已校验 Courant）。

    Raises:
        ValueError: 输入非法（规则 14）。
    """
    eps_r = build_eps_from_neff(n_eff_arr)
    nx, ny = eps_r.shape
    if nx < 5 or ny < 5:
        raise ValueError(f"网格过小 {(nx, ny)}，至少 5x5 以容纳 PML+源")
    if dt is None:
        dt = courant_dt(dx, dy, cfl=cfl)
    return YeeGridFdtd(
        shape=(nx, ny),
        dx=dx,
        dy=dy,
        dt=dt,
        eps_r=eps_r,
    )


def step_leapfrog(
    grid: YeeGridFdtd,
    fields: Yee2DFields,
    cpml_buffers: CpmlBuffers | None = None,
    cx: CpmlCoefficients | None = None,
    cy: CpmlCoefficients | None = None,
) -> None:
    """单步 leapfrog 推进（A06 §3，向量化）。

    顺序（与 A09-FDTD solver 一致）：
        1. update_h_psi → 更新 H^{n+1/2}（含 CPML ψ_h）
        2. update_e_psi → 更新 E^{n+1}（含 CPML ψ_e）

    注：TFSF 校正与源注入由调用者（VarFdtdSolver）在 step_leapfrog 前后施加，
    保持本函数单一职责。

    Args:
        grid: YeeGridFdtd（提供 ca/cb/da/db/dx/dy）。
        fields: Yee2DFields（原地修改 h_x/h_y/e_z）。
        cpml_buffers: CPML 辅助变量缓冲区，None 表示无 PML。
        cx, cy: CPML x/y 方向系数，cpml_buffers 非 None 时必填。
    """
    e_z = fields.e_z
    h_x = fields.h_x
    h_y = fields.h_y
    ca, cb = grid.ca_ez, grid.cb_ez
    da, db = grid.da_h, grid.db_h
    dx, dy = grid.dx, grid.dy
    has_pml = cpml_buffers is not None
    if has_pml and (cx is None or cy is None):
        raise ValueError("cpml_buffers 非 None 时 cx/cy 必填")
    # 1. H^{n+1/2} 更新（向量化）
    if cpml_buffers is not None:
        update_h_psi(e_z, cpml_buffers, cx, cy)  # type: ignore[arg-type]
        de_dy = (e_z[:, 1:] - e_z[:, :-1]) / dy
        h_x[:, :-1] = da[:, :-1] * h_x[:, :-1] - db[:, :-1] * (
            de_dy + cpml_buffers.psi_h_xy[:, :-1]
        )
        de_dx = (e_z[1:, :] - e_z[:-1, :]) / dx
        h_y[:-1, :] = da[:-1, :] * h_y[:-1, :] + db[:-1, :] * (
            de_dx + cpml_buffers.psi_h_yx[:-1, :]
        )
    else:
        h_x[:, :-1] = da[:, :-1] * h_x[:, :-1] - db[:, :-1] * (e_z[:, 1:] - e_z[:, :-1]) / dy
        h_y[:-1, :] = da[:-1, :] * h_y[:-1, :] + db[:-1, :] * (e_z[1:, :] - e_z[:-1, :]) / dx
    # 2. E^{n+1} 更新（内部 [1:-1, 1:-1]）
    if cpml_buffers is not None:
        update_e_psi(h_x, h_y, cpml_buffers, cx, cy)  # type: ignore[arg-type]
    dhy_dx = (h_y[1:-1, 1:-1] - h_y[:-2, 1:-1]) / dx
    dhx_dy = (h_x[1:-1, 1:-1] - h_x[1:-1, :-2]) / dy
    curl_z = dhy_dx - dhx_dy
    interior = (slice(1, -1), slice(1, -1))
    e_z[interior] = ca[interior] * e_z[interior] + cb[interior] * curl_z
    if cpml_buffers is not None:
        e_z[interior] += cb[interior] * (
            cpml_buffers.psi_e_xz[interior] - cpml_buffers.psi_e_yz[interior]
        )
