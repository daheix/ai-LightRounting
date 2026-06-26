"""Yee 网格交错排列与 FDTD 更新系数（A09 §3-§4）。

实现 Yee 1966 交错网格的 2D TEz 形式：
- 电场 E_z 位于网格节点 (i, j)
- 磁场 H_x 位于 (i, j+1/2) —— 半步长 y 错位
- 磁场 H_y 位于 (i+1/2, j) —— 半步长 x 错位

E/H 半步长错位使 Maxwell 旋度方程的中心差分天然落在被求场位置，
二阶精度 O(Δh²)，且离散 Gauss 定律 ∇·(∇×·) ≡ 0 自动满足
（避免非物理电荷积累）。该布局是 FDE/FDFD/FDTD/2.5D-FDTD 共同底座。

E/H leapfrog 时间推进（A09 §3.2，半步错位中心差分）：
    H^{n+1/2} = D_a · H^{n-1/2} - D_b · ∇×E^n
    E^{n+1}   = C_a · E^n       + C_b · ∇×H^{n+1/2}

更新系数（Taflove 2005 §3.7）：
    D_a = (1 - σ_m Δt/(2μ)) / (1 + σ_m Δt/(2μ))，D_b = (Δt/μ)/(1 + σ_m Δt/(2μ))
    C_a = (1 - σ Δt/(2ε))  / (1 + σ Δt/(2ε))， C_b = (Δt/ε)/(1 + σ Δt/(2ε))
其中 ε = ε_0 ε_r，μ = μ_0 μ_r。

Courant-Friedrichs-Lewy 稳定性（A09 §4）：
    3D: Δt ≤ 1/(c·√(1/Δx² + 1/Δy² + 1/Δz²))
    2D: Δt ≤ 1/(c·√(1/Δx² + 1/Δy²))
工程取 0.99 倍 CFL 上限保留稳定裕度（A09 §4）。

文献来源（≥5，规则 18 学术诚信）：
1. Yee 1966 IEEE Trans AP 14(3) 302-307 —
   https://doi.org/10.1109/TAP.1966.1138693
2. Taflove & Hagness, "Computational Electrodynamics," 3rd ed., Artech House
   (2005) — https://www.artechhouse.com/Computational-Electrodynamics/Kane-Taflove/p/Book-927
3. Shin & Fan 2012 J Comput Phys 231 3406-3431 —
   https://doi.org/10.1016/j.jcp.2011.12.037
4. Gedney 1996 IEEE Trans AP 44(12) 1630-1639 —
   https://doi.org/10.1109/8.546242
5. Lumerical FDTD Learning —
   https://optics.ansys.com/hc/en-us/categories/360001366534
6. MEEP FDTD Python Tutorials —
   https://meep.readthedocs.io/en/latest/Python_Tutorials/
7. Roden & Gedney 2000 MPML —
   https://doi.org/10.1002/1099-1207(20000612)12:3<284::AID-MMPS5>3.0.CO;2-K

规则依据：规则 14（非法输入 raise，无 fall-back）/规则 18（学术诚信）/
规则 26（纯 CPU numpy）/§4（向量化，无循环）
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

__all__ = ["YeeGridFdtd", "courant_dt", "build_update_coefficients"]

# 物理常数（SI 单位）
_C0 = 2.99792458e8  # 真空光速 m/s
_EPS0 = 8.8541878128e-12  # 真空介电常数 F/m
_MU0 = 1.25663706212e-6  # 真空磁导率 H/m


def courant_dt(
    dx: float,
    dy: float,
    dz: float | None = None,
    cfl: float = 0.99,
) -> float:
    """计算 Courant-Friedrichs-Lewy 时间步上限（A09 §4）。

    3D：Δt ≤ 1/(c·√(1/Δx² + 1/Δy² + 1/Δz²))
    2D：Δt ≤ 1/(c·√(1/Δx² + 1/Δy²))（dz=None）

    Args:
        dx: x 方向网格间距（米），必须 >0。
        dy: y 方向网格间距（米），必须 >0。
        dz: z 方向网格间距（米），None 表示 2D。
        cfl: Courant 数（安全余量系数），取值 (0, 1]，默认 0.99。

    Returns:
        时间步 Δt（秒）。

    Raises:
        ValueError: 网格间距或 cfl 非法（规则 14）。
    """
    if dx <= 0.0:
        raise ValueError(f"dx 必须为正，实际 {dx}")
    if dy <= 0.0:
        raise ValueError(f"dy 必须为正，实际 {dy}")
    if dz is not None and dz <= 0.0:
        raise ValueError(f"dz 必须为正，实际 {dz}")
    if not (0.0 < cfl <= 1.0):
        raise ValueError(f"cfl 须 ∈ (0, 1]，实际 {cfl}")
    inv_sq = 1.0 / (dx * dx) + 1.0 / (dy * dy)
    if dz is not None:
        inv_sq += 1.0 / (dz * dz)
    dt_max = 1.0 / (_C0 * np.sqrt(inv_sq))
    return cfl * dt_max


@dataclass
class YeeGridFdtd:
    """2D TEz Yee 交错网格 + 预计算更新系数。

    场分量布局（半步错位）：
        E_z[i, j]    位于 (i·dx,     j·dy)
        H_x[i, j]    位于 (i·dx,     (j+0.5)·dy)  —— 仅 j∈[0, ny-2] 物理有效
        H_y[i, j]    位于 ((i+0.5)·dx, j·dy)       —— 仅 i∈[0, nx-2] 物理有效

    数组均存为 (nx, ny)，越界半步位置（H_x[:, -1]、H_y[-1, :]）保持 0
    （自然边界，由 PEC/PMC/PML 在求解器中覆盖）。

    更新公式（向量化，§4 禁止循环）：
        H_x[:, :-1] = D_a·H_x[:, :-1] - D_b·(E_z[:, 1:] - E_z[:, :-1])/dy
        H_y[:-1, :] = D_a·H_y[:-1, :] + D_b·(E_z[1:, :] - E_z[:-1, :])/dx
        E_z[1:-1, 1:-1] = C_a·E_z + C_b·((H_y[1:-1]-H_y[:-2])/dx
                                            - (H_x[:, 1:-1]-H_x[:, :-2])/dy)

    Attributes:
        shape: 网格形状 (Nx, Ny)。
        dx, dy: 网格间距（米）。
        dt: 时间步（秒），由 courant_dt 计算。
        eps_r: 相对介电常数分布 (Nx, Ny)，>0。
        sigma: 电导率 σ (S/m) (Nx, Ny)，默认全 0（无损耗）。
        sigma_m: 磁导率 σ_m (S/m) (Nx, Ny)，默认全 0。
        mu_r: 相对磁导率分布 (Nx, Ny)，默认全 1。
        ca_ez, cb_ez: 电场更新系数 C_a, C_b (Nx, Ny)。
        da_h, db_h: 磁场更新系数 D_a, D_b (Nx, Ny)（H_x/H_y 共享）。
    """

    shape: tuple[int, int]
    dx: float
    dy: float
    dt: float
    eps_r: np.ndarray
    sigma: np.ndarray | None = None
    sigma_m: np.ndarray | None = None
    mu_r: np.ndarray | None = None
    # 预计算系数（__post_init__ 填充）
    ca_ez: np.ndarray = field(init=False)
    cb_ez: np.ndarray = field(init=False)
    da_h: np.ndarray = field(init=False)
    db_h: np.ndarray = field(init=False)

    def __post_init__(self) -> None:
        nx, ny = self.shape
        if nx < 5 or ny < 5:
            raise ValueError(f"网格过小 {self.shape}，至少 5x5 以容纳 PML+总场")
        if self.dx <= 0.0 or self.dy <= 0.0:
            raise ValueError(f"网格间距必须为正，dx={self.dx}, dy={self.dy}")
        if self.dt <= 0.0:
            raise ValueError(f"时间步必须为正，dt={self.dt}")
        # Courant 上限校验（A09 §4，规则 14 失败 raise）
        dt_max = courant_dt(self.dx, self.dy, cfl=1.0)
        if self.dt > dt_max * (1.0 + 1e-9):
            raise ValueError(f"dt={self.dt:.3e} 超过 Courant 上限 {dt_max:.3e}，leapfrog 不稳定")
        eps_r = np.asarray(self.eps_r, dtype=np.float64)
        if eps_r.shape != (nx, ny):
            raise ValueError(f"eps_r 形状 {eps_r.shape} 与网格 {self.shape} 不匹配")
        if np.any(eps_r <= 0.0):
            raise ValueError("eps_r 必须严格为正（介质折射率平方）")
        self.eps_r = eps_r
        # 默认材料参数
        self.sigma = self._broadcast(self.sigma, "sigma", 0.0)
        self.sigma_m = self._broadcast(self.sigma_m, "sigma_m", 0.0)
        self.mu_r = self._broadcast(self.mu_r, "mu_r", 1.0)
        if np.any(self.mu_r <= 0.0):
            raise ValueError("mu_r 必须严格为正")
        if np.any(self.sigma < 0.0) or np.any(self.sigma_m < 0.0):
            raise ValueError("sigma/sigma_m 必须非负（无源介质）")
        # 预计算更新系数（Taflove 2005 §3.7，向量化无循环）
        eps = _EPS0 * self.eps_r  # 绝对介电常数
        mu = _MU0 * self.mu_r  # 绝对磁导率
        # C_a = (1 - σΔt/(2ε)) / (1 + σΔt/(2ε))，C_b = (Δt/ε)/(1 + σΔt/(2ε))
        loss_e = self.sigma * self.dt / (2.0 * eps)
        self.ca_ez = (1.0 - loss_e) / (1.0 + loss_e)
        self.cb_ez = (self.dt / eps) / (1.0 + loss_e)
        # D_a = (1 - σ_mΔt/(2μ)) / (1 + σ_mΔt/(2μ))，D_b = (Δt/μ)/(1 + σ_mΔt/(2μ))
        loss_h = self.sigma_m * self.dt / (2.0 * mu)
        self.da_h = (1.0 - loss_h) / (1.0 + loss_h)
        self.db_h = (self.dt / mu) / (1.0 + loss_h)

    def _broadcast(self, arr: np.ndarray | None, name: str, default: float) -> np.ndarray:
        """将 None 或标量广播为 (nx, ny) 数组，校验形状。"""
        nx, ny = self.shape
        if arr is None:
            return np.full((nx, ny), default, dtype=np.float64)
        arr = np.asarray(arr, dtype=np.float64)
        if arr.shape != (nx, ny):
            raise ValueError(f"{name} 形状 {arr.shape} 与网格 {self.shape} 不匹配")
        return arr

    def allocate_fields(self) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """分配 E_z, H_x, H_y 三个场数组（全零，float64）。

        Returns:
            (e_z, h_x, h_y)，形状均为 (Nx, Ny)。
        """
        z = np.zeros(self.shape, dtype=np.float64)
        return z.copy(), z.copy(), z.copy()

    @property
    def cfl_number(self) -> float:
        """实际 Courant 数 S = c·Δt/Δh（Δh 取最小网格）。"""
        dh = min(self.dx, self.dy)
        return _C0 * self.dt / dh

    def __repr__(self) -> str:
        return (
            f"YeeGridFdtd(shape={self.shape}, dx={self.dx:.3e}m, "
            f"dt={self.dt:.3e}s, CFL={self.cfl_number:.4f}, "
            f"eps_max={self.eps_r.max():.4f})"
        )


def build_update_coefficients(
    eps_r: np.ndarray,
    sigma: np.ndarray | None,
    sigma_m: np.ndarray | None,
    mu_r: np.ndarray | None,
    dt: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """从材料分布计算 leapfrog 更新系数（不校验 Courant，供 solver/CPML 复用）。

    本函数仅计算材料相关系数 C_a/C_b/D_a/D_b，不构造完整 YeeGridFdtd，
    因此不涉及 dx/dy 与 Courant 上限（由调用方在构造网格时保证）。

    Args:
        eps_r: 相对介电常数 (Nx, Ny)，必须 >0。
        sigma: 电导率 (Nx, Ny) 或 None（视为 0）。
        sigma_m: 磁导率 (Nx, Ny) 或 None（视为 0）。
        mu_r: 相对磁导率 (Nx, Ny) 或 None（视为 1）。
        dt: 时间步（秒），必须 >0。

    Returns:
        (ca_ez, cb_ez, da_h, db_h) 四个数组，形状均同 eps_r。

    Raises:
        ValueError: eps_r/mu_r 非正或 sigma 负（规则 14）。
    """
    if dt <= 0.0:
        raise ValueError(f"dt 必须为正，实际 {dt}")
    eps_r_arr = np.asarray(eps_r, dtype=np.float64)
    if eps_r_arr.ndim != 2:
        raise ValueError(f"eps_r 必须 2D，实际 {eps_r_arr.ndim}D")
    nx, ny = eps_r_arr.shape
    if np.any(eps_r_arr <= 0.0):
        raise ValueError("eps_r 必须严格为正")
    sig = _to_array(sigma, (nx, ny), 0.0, "sigma")
    sig_m = _to_array(sigma_m, (nx, ny), 0.0, "sigma_m")
    mu = _to_array(mu_r, (nx, ny), 1.0, "mu_r")
    if np.any(mu <= 0.0):
        raise ValueError("mu_r 必须严格为正")
    if np.any(sig < 0.0) or np.any(sig_m < 0.0):
        raise ValueError("sigma/sigma_m 必须非负")
    eps = _EPS0 * eps_r_arr
    mu_abs = _MU0 * mu
    loss_e = sig * dt / (2.0 * eps)
    ca_ez = (1.0 - loss_e) / (1.0 + loss_e)
    cb_ez = (dt / eps) / (1.0 + loss_e)
    loss_h = sig_m * dt / (2.0 * mu_abs)
    da_h = (1.0 - loss_h) / (1.0 + loss_h)
    db_h = (dt / mu_abs) / (1.0 + loss_h)
    return ca_ez, cb_ez, da_h, db_h


def _to_array(
    arr: np.ndarray | None, shape: tuple[int, int], default: float, name: str
) -> np.ndarray:
    """广播 None/标量为指定形状数组并校验。"""
    if arr is None:
        return np.full(shape, default, dtype=np.float64)
    out = np.asarray(arr, dtype=np.float64)
    if out.shape != shape:
        raise ValueError(f"{name} 形状 {out.shape} 与期望 {shape} 不匹配")
    return out
