"""TFSF 总场/散射场边界（A09 §8，Taflove 2005 §5.5）。

总场/散射场（Total-Field / Scattered-Field）边界将计算域分为：
- 总场区（TF）：入射场 + 散射场，散射体置于此区。
- 散射场区（SF）：仅散射场，用于提取散射/吸收特性。

边界处通过 ±入射场校正保证更新方程自洽（Huygens 等效面，Merewether 1971）：
- TF 节点更新依赖 SF 邻居时，给该邻居 +入射场（补齐缺失的入射分量）。
- SF 节点更新依赖 TF 邻居时，给该邻居 −入射场（剔除入射分量）。

入射场由 1D 辅助 FDTD 网格产生（Schneider 2004，网格对齐传播无泄漏）：
1D 网格沿入射方向以与 2D 主网格相同的 Δt、Δx 推进 leapfrog，
得到 E_inc、H_inc 序列，数值色散与 2D 网格精确一致，理论上零泄漏。

本实现限定（A09 §8）：2D TEz，平面波沿 +x 传播（E_z / H_y 偏振），
TFSF 矩形边界 TF 区 i∈[i0, i1]、j∈[j0, j1]，校正仅在 x=i0 与 x=i1 两条边
（+x 平面波无 y 方向场分量，y 边界无需校正）。

校正公式（完成标准 leapfrog 更新后追加，向量化）：
    H_y[i0-1, :] -= (db_h/dx) · E_inc[i0]       # SF 节点剔除入射 E
    H_y[i1,   :] += (db_h/dx) · E_inc[i1+1]     # TF 节点补齐入射 E
    E_z[i0,   :] -= (cb_ez/dx) · H_inc[i0-1]    # TF 左边界：旋度用散射场 H，偏大，减入射 H 校正
    E_z[i1+1, :] += (cb_ez/dx) · H_inc[i1]      # SF 右边界：旋度用总场 H，偏小，加入射 H 校正

*创新*：Incident1D 复用与 2D 网格相同的 Yee 半步错位与 ca/cb 系数，
保证 1D 与 2D 数值色散逐点一致（Schneider 2004 "perfect TFSF" 条件）。
- 底层逻辑：1D 网格 E_inc[i] 与 2D E_z[i] 同位（i·dx），H_inc[i] 与 H_y[i] 同位。
- 支持理论：Schneider 2004 证明网格对齐时 1D 辅助网格给出零泄漏 TFSF。
- 案例：自由空间平面波注入、SOI 波导入射、金属柱体散射。

文献来源（≥5，规则 18 学术诚信）：
1. Taflove & Hagness 2005 Computational Electrodynamics §5.5（TFSF 边界）—
   https://www.artechhouse.com/Computational-Electrodynamics/Kane-Taflove/p/Book-927
2. Schneider 2004 IEEE Trans AP 52(12) 3280-3287（完美 TFSF + 1D 辅助网格）—
   https://doi.org/10.1109/TAP.2004.837541
3. Merewether 1971 IEEE Trans Nucl Sci 18(6) 9-13（Huygens 等效面）—
   https://doi.org/10.1109/TNS.1971.4325954
4. Umashankar & Taflove 1982 IEEE Trans EMC 24(4) 397-405（TFSF 平面波注入）—
   https://doi.org/10.1109/TEMC.1982.304064
5. Yee 1966 IEEE Trans AP 14(3) 302-307 —
   https://doi.org/10.1109/TAP.1966.1138693
6. MEEP FDTD TFSF — https://meep.readthedocs.io/en/latest/Python_Tutorials/
7. arXiv:2507.22301 PoLaRIS — https://arxiv.org/abs/2507.22301

规则依据：规则 14（非法输入 raise）/规则 18（学术诚信）/
规则 26（纯 CPU numpy）/§4（向量化）
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

__all__ = [
    "TfsfBox",
    "Incident1D",
    "apply_tfsf_correction",
    "apply_tfsf_h_correction",
    "apply_tfsf_e_correction",
]

# 物理常数（SI 单位）
_EPS0 = 8.8541878128e-12  # 真空介电常数 F/m
_MU0 = 1.25663706212e-6  # 真空磁导率 H/m
_C0 = 2.99792458e8  # 真空光速 m/s


@dataclass(frozen=True)
class TfsfBox:
    """2D TEz TFSF 矩形边界（沿 +x 入射，A09 §8）。

    Attributes:
        i0, i1: TF 区 x 索引范围 [i0, i1]（含端点）。
        j0, j1: TF 区 y 索引范围 [j0, j1]（含端点）。
    """

    i0: int
    i1: int
    j0: int
    j1: int

    def __post_init__(self) -> None:
        if self.i0 < 1:
            raise ValueError(f"i0 须 ≥1（左侧需留 SF 区），实际 {self.i0}")
        if self.j0 < 1:
            raise ValueError(f"j0 须 ≥1，实际 {self.j0}")
        if self.i1 <= self.i0:
            raise ValueError(f"i1({self.i1}) 须 > i0({self.i0})")
        if self.j1 <= self.j0:
            raise ValueError(f"j1({self.j1}) 须 > j0({self.j0})")


@dataclass
class Incident1D:
    """1D 辅助 FDTD 入射场（沿 +x 传播，TEz 的 E_z / H_y 分量）。

    使用与 2D 主网格相同的 dx、dt 推进 leapfrog，保证数值色散一致
    （Schneider 2004 完美 TFSF 条件）。源在 i=1 软注入，沿 +x 传播。
    真空背景（ε_r=1），CFL 自然满足（dt 由 2D 网格保证 ≤ dx/c）。

    场位定义（与 2D Yee 网格一致）：
        E_inc[i]  位于 i·dx      （与 2D E_z[i, j] 同位）
        H_inc[i]  位于 (i+0.5)·dx （与 2D H_y[i, j] 同位）

    Attributes:
        nx: 1D 网格点数，须 ≥ i1+2（提供 E_inc[i1+1]）。
        dx: 网格间距（米），与 2D 网格 dx 相同。
        dt: 时间步（秒），与 2D 主网格相同。
        ca, cb: 1D leapfrog 系数（真空，cb = dt/ε_0）。
        da, db: 1D leapfrog 系数（真空，db = dt/μ_0）。
        e_inc: 入射电场 E_z (nx,)。
        h_inc: 入射磁场 H_y (nx,)（半步错位）。
    """

    nx: int
    dx: float
    dt: float
    ca: float = field(init=False)
    cb: float = field(init=False)
    da: float = field(init=False)
    db: float = field(init=False)
    e_inc: np.ndarray = field(init=False)
    h_inc: np.ndarray = field(init=False)

    def __post_init__(self) -> None:
        if self.nx < 3:
            raise ValueError(f"1D 网格点数须 ≥3，实际 {self.nx}")
        if self.dx <= 0.0:
            raise ValueError(f"dx 须 >0，实际 {self.dx}")
        if self.dt <= 0.0:
            raise ValueError(f"dt 须 >0，实际 {self.dt}")
        # CFL 校验（真空 1D：dt ≤ dx/c）
        dt_max = self.dx / _C0
        if self.dt > dt_max * (1.0 + 1e-12):
            raise ValueError(
                f"dt={self.dt:.3e} 超过 1D CFL 上限 {dt_max:.3e}"
            )
        # 真空 leapfrog 系数（σ=0）
        self.ca = 1.0
        self.cb = self.dt / _EPS0
        self.da = 1.0
        self.db = self.dt / _MU0
        self.e_inc = np.zeros(self.nx, dtype=np.float64)
        self.h_inc = np.zeros(self.nx, dtype=np.float64)

    def step(self, source_value: float) -> None:
        """推进 1D 辅助网格一个 leapfrog 步（硬源 i=0，仅向 +x 辐射）。

        顺序：先置硬源 E_inc[0]=g(t)，再更新 H（依赖含源的 E），再更新 E。
        硬源（赋值而非叠加）使 i=0 成为强制边界，入射波只向 +x 传播，
        避免 −x 分量在 i=0 PEC 墙反射污染入射场（Taflove 2005 §5.5.1）。
        1D 网格无散射体，硬源不会引入误差。

        Args:
            source_value: 当前时刻波形 g(t)（V/m 量纲振幅）。
        """
        # 1. 硬源（强制 E_inc[0]，仅 +x 辐射）
        self.e_inc[0] = source_value
        # 2. H_inc[i] += db * (E_inc[i+1] - E_inc[i]) / dx, i ∈ [0, nx-2]
        self.h_inc[:-1] += self.db * (
            self.e_inc[1:] - self.e_inc[:-1]
        ) / self.dx
        # 3. E_inc[i] += cb * (H_inc[i] - H_inc[i-1]) / dx, i ∈ [1, nx-1]
        self.e_inc[1:] += self.cb * (
            self.h_inc[1:] - self.h_inc[:-1]
        ) / self.dx


def _check_incident_extent(tfsf: TfsfBox, incident: Incident1D) -> None:
    """校验 1D 入射网格覆盖 TFSF 所需索引（规则 14，失败 raise）。"""
    if tfsf.i1 + 1 >= incident.nx:
        raise IndexError(
            f"Incident1D.nx={incident.nx} 不足，需 ≥ i1+2={tfsf.i1 + 2}"
        )
    if tfsf.i0 - 1 < 0:
        raise IndexError(f"i0-1={tfsf.i0 - 1} 越界，i0 须 ≥1")


def apply_tfsf_h_correction(
    h_y: np.ndarray,
    tfsf: TfsfBox,
    incident: Incident1D,
    db_h: np.ndarray,
    dx: float,
) -> None:
    """TFSF 磁场校正（H 更新后、E 更新前施加，A09 §8 / Taflove §5.5）。

    校正 H_y 在 TF/SF 边界 x=i0-1 与 x=i1：
        H_y[i0-1, j0:j1+1] -= (db_h/dx) · E_inc[i0]    # SF 剔除入射 E
        H_y[i1,   j0:j1+1] += (db_h/dx) · E_inc[i1+1]  # TF 补齐入射 E

    Args:
        h_y: 磁场 H_y (Nx, Ny)，原地修改。
        tfsf: TFSF 边界规格。
        incident: 1D 入射场（提供 E_inc）。
        db_h: 磁场更新系数 D_b (Nx, Ny)。
        dx: x 方向网格间距（米）。
    """
    _check_incident_extent(tfsf, incident)
    j_sl = slice(tfsf.j0, tfsf.j1 + 1)
    inv_dx = 1.0 / dx
    h_y[tfsf.i0 - 1, j_sl] -= (
        db_h[tfsf.i0 - 1, j_sl] * inv_dx * incident.e_inc[tfsf.i0]
    )
    h_y[tfsf.i1, j_sl] += (
        db_h[tfsf.i1, j_sl] * inv_dx * incident.e_inc[tfsf.i1 + 1]
    )


def apply_tfsf_e_correction(
    e_z: np.ndarray,
    tfsf: TfsfBox,
    incident: Incident1D,
    cb_ez: np.ndarray,
    dx: float,
) -> None:
    """TFSF 电场校正（E 更新后、源注入前施加，A09 §8 / Taflove §5.5）。

    校正 E_z 在 TF/SF 边界 x=i0 与 x=i1+1：
        E_z[i0,   j0:j1+1] -= (cb_ez/dx) · H_inc[i0-1]   # TF 补齐缺失的入射 H
        E_z[i1+1, j0:j1+1] += (cb_ez/dx) · H_inc[i1]     # SF 剔除多余的入射 H

    符号推导（无散射体守恒性校验）：E_z[i0] 左邻 H_y[i0-1] 经 H 校正后为
    散射场（缺入射 H_inc[i0-1]），旋度 (H_y[i0]-H_y[i0-1])/dx 漏掉 -H_inc[i0-1]/dx，
    故 E_z[i0] 须减去 cb·H_inc[i0-1]/dx；E_z[i1+1] 左邻 H_y[i1] 为总场（含入射），
    SF 节点须剔除，故加上 cb·H_inc[i1]/dx。

    Args:
        e_z: 电场 E_z (Nx, Ny)，原地修改。
        tfsf: TFSF 边界规格。
        incident: 1D 入射场（提供 H_inc）。
        cb_ez: 电场更新系数 C_b (Nx, Ny)。
        dx: x 方向网格间距（米）。
    """
    _check_incident_extent(tfsf, incident)
    j_sl = slice(tfsf.j0, tfsf.j1 + 1)
    inv_dx = 1.0 / dx
    # TF 左边界：标准 leapfrog 用了散射场 H_y[i0-1]（缺入射 H_inc[i0-1]），
    # 须减去 cb·H_inc[i0-1]/dx 补齐总场旋度。
    e_z[tfsf.i0, j_sl] -= (
        cb_ez[tfsf.i0, j_sl] * inv_dx * incident.h_inc[tfsf.i0 - 1]
    )
    # SF 右边界：标准 leapfrog 用了总场 H_y[i1]（含入射 H_inc[i1]），
    # 须加上 cb·H_inc[i1]/dx 剔除入射分量还原散射场旋度。
    e_z[tfsf.i1 + 1, j_sl] += (
        cb_ez[tfsf.i1 + 1, j_sl] * inv_dx * incident.h_inc[tfsf.i1]
    )


def apply_tfsf_correction(
    e_z: np.ndarray,
    h_x: np.ndarray,
    h_y: np.ndarray,
    tfsf: TfsfBox,
    incident: Incident1D,
    cb_ez: np.ndarray,
    db_h: np.ndarray,
    dx: float,
) -> None:
    """TFSF 组合便捷校正（H+E 顺序施加，公开 API）。

    依次调用 apply_tfsf_h_correction 与 apply_tfsf_e_correction。
    适用于单步完整 leapfrog 后一次性施加的简化场景；
    高精度场景（求解器）应分别调用上述两函数，置于 H/E 更新之间。

    Args:
        e_z, h_x, h_y: 2D 场数组 (Nx, Ny)，原地修改（h_x 不变，+x 波无耦合）。
        tfsf: TFSF 边界规格。
        incident: 1D 入射场。
        cb_ez: 电场更新系数 C_b (Nx, Ny)。
        db_h: 磁场更新系数 D_b (Nx, Ny)。
        dx: x 方向网格间距（米）。
    """
    apply_tfsf_h_correction(h_y, tfsf, incident, db_h, dx)
    apply_tfsf_e_correction(e_z, tfsf, incident, cb_ez, dx)
