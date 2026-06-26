"""2D TEz FDTD 主求解器（A09 §10，Yee leapfrog 时间推进）。

集成 Yee 交错网格 + CPML 吸收边界 + TFSF 平面波注入 + Drude ADE 色散
+ DFT 监视器 + S 参数提取，构成完整的 2D 时域有限差分仿真流水线。

leapfrog 时间推进（Yee 1966，二阶精度 O(Δt², Δh²)）：
    H^{n+1/2} = D_a·H^{n-1/2} - D_b·∇×E^n           (+ CPML ψ_h)
    E^{n+1}   = C_a·E^n       + C_b·∇×H^{n+1/2}      (+ CPML ψ_e - cb·J_Drude)

每步顺序（A09 §10）：
    1. update_h_psi → 更新 H^{n+1/2}（含 CPML ψ_h）
    2. apply_tfsf_h_correction → TFSF 边界 H 校正（H 更新后、E 更新前）
    3. update_e_psi → 更新 E^{n+1}（含 CPML ψ_e）
    4. apply_ade_drude → Drude J^{n+1/2}，E^{n+1} -= cb·J
    5. apply_tfsf_e_correction → TFSF 边界 E 校正
    6. inject_dipole → 软源注入
    7. record → DFT 监视器 + 探针时序

稳定性由 YeeGridFdtd 校验 Courant 上限（A09 §4）。CPML σ_max 由 Gedney 1996
公式自动估计（cpml.build_cpml）。TFSF 1D 辅助网格与主网格共享 dx/dt，满足
Schneider 2004 完美 TFSF 条件（网格对齐零泄漏）。

*创新*：求解器将 CPML/TFSF/Drude/Monitor 解耦为可选模块，通过 config 字段开关，
核心 leapfrog 更新向量化（仅时间步循环不可避免），单一 FdtdSolver 支撑
M1~M4 全部验收场景（自由空间脉冲、CPML 反射、金 Drude、S 参数）。
- 底层逻辑：每模块独立 raise 校验，无 fall-back；场更新全 NumPy 向量化。
- 支持理论：Yee 1966 leapfrog 二阶稳定；Taflove 2005 §3-§9 完整理论框架。
- 案例：M1 高斯脉冲（<1e-3）、M2 CPML（≤-60dB）、M3 金 Drude（<2%）、M4 S 参数（<1e-3）。

文献来源（≥5，规则 18 学术诚信）：
1. Yee 1966 IEEE Trans AP 14(3) 302-307（leapfrog 交错网格）—
   https://doi.org/10.1109/TAP.1966.1138693
2. Taflove & Hagness 2005 Computational Electrodynamics §3-§9 —
   https://www.artechhouse.com/Computational-Electrodynamics/Kane-Taflove/p/Book-927
3. Roden & Gedney 2000 CPML —
   https://doi.org/10.1002/1098-2760(20001205)27:5%3C334::AID-MOP14%3E3.0.CO;2-A
4. Moharam 1995 JOSA A 12(5) 1077-1086（RCWA S 参数基准）—
   https://doi.org/10.1364/JOSAA.12.001077
5. Schneider 2004 IEEE Trans AP 52(12) 3280-3287（完美 TFSF）—
   https://doi.org/10.1109/TAP.2004.837541
6. Lumerical FDTD — https://www.lumerical.com/products/fdtd/
7. arXiv:2507.22301 PoLaRIS — https://arxiv.org/abs/2507.22301

规则依据：规则 14（非法输入 raise）/规则 18（学术诚信）/
规则 26（纯 CPU numpy）/§4（向量化，仅时间步循环例外）
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from polaris.sim.fdtd.cpml import (
    CpmlBuffers,
    CpmlCoefficients,
    CpmlConfig,
    build_cpml,
    update_e_psi,
    update_h_psi,
)
from polaris.sim.fdtd.dispersive import DrudeParams, apply_ade_drude
from polaris.sim.fdtd.monitor import DftMonitor, SParamExtractor
from polaris.sim.fdtd.sources import DipoleSource, Waveform, inject_dipole
from polaris.sim.fdtd.tfsf import (
    Incident1D,
    TfsfBox,
    apply_tfsf_e_correction,
    apply_tfsf_h_correction,
)
from polaris.sim.fdtd.yee_grid import YeeGridFdtd

__all__ = [
    "FdtdConfig",
    "FdtdResult",
    "FdtdSolver",
    "solve_fdtd",
]


@dataclass
class FdtdConfig:
    """2D TEz FDTD 仿真配置（A09 §10）。

    Attributes:
        grid: Yee 交错网格（含 ca/cb/da/db 系数与 Courant 校验）。
        n_steps: 时间步数，>0。
        cpml: CPML 参数，None 表示无 PML（外环 PEC）。
        eps_r_bg: 背景相对介电常数（CPML σ_max 估计用），默认 1.0。
        tfsf: TFSF 边界规格，None 表示不使用平面波注入。
        tfsf_waveform: TFSF 入射波形（tfsf 非 None 时必填）。
        drude: Drude 色散参数，None 表示非色散。
        drude_mask: Drude 区域布尔掩码 (Nx, Ny)，None 表示全场色散。
        dipole_sources: 偶极子软源列表。
        monitors: DFT 监视器列表。
        s_param_extractors: S 参数提取器列表。
        probe_point: 探针网格索引 (i, j)，None 不记录时序。
    """

    grid: YeeGridFdtd
    n_steps: int
    cpml: CpmlConfig | None = None
    eps_r_bg: float = 1.0
    tfsf: TfsfBox | None = None
    tfsf_waveform: Waveform | None = None
    drude: DrudeParams | None = None
    drude_mask: np.ndarray | None = None
    dipole_sources: list[DipoleSource] = field(default_factory=list)
    monitors: list[DftMonitor] = field(default_factory=list)
    s_param_extractors: list[SParamExtractor] = field(default_factory=list)
    probe_point: tuple[int, int] | None = None

    def __post_init__(self) -> None:
        if self.n_steps <= 0:
            raise ValueError(f"n_steps 须 >0，实际 {self.n_steps}")
        if self.eps_r_bg <= 0.0:
            raise ValueError(f"eps_r_bg 须 >0，实际 {self.eps_r_bg}")
        if self.tfsf is not None and self.tfsf_waveform is None:
            raise ValueError("tfsf 非 None 时 tfsf_waveform 必填")
        if self.drude is not None and self.drude_mask is not None:
            if self.drude_mask.shape != self.grid.shape:
                raise ValueError(
                    f"drude_mask 形状 {self.drude_mask.shape} "
                    f"与网格 {self.grid.shape} 不匹配"
                )
        nx, ny = self.grid.shape
        for src in self.dipole_sources:
            ix, iy = src.position
            if not (0 <= ix < nx and 0 <= iy < ny):
                raise IndexError(f"偶极子 {src.position} 越界 {self.grid.shape}")
        for mon in self.monitors:
            ix, iy = mon.position
            if not (0 <= ix < nx and 0 <= iy < ny):
                raise IndexError(f"监视器 {mon.position} 越界 {self.grid.shape}")
        if self.probe_point is not None:
            ix, iy = self.probe_point
            if not (0 <= ix < nx and 0 <= iy < ny):
                raise IndexError(
                    f"探针 {self.probe_point} 越界 {self.grid.shape}"
                )


@dataclass
class FdtdResult:
    """FDTD 仿真结果（A09 §10）。

    Attributes:
        e_z, h_x, h_y: 终态场 (Nx, Ny)。
        time_series: 探针点 E_z 时序 (n_steps,)（无探针则为空数组）。
        dft_results: 监视器名 → 复 DFT 谱。
        s_params: S 参数名 → 复 S 值。
    """

    e_z: np.ndarray
    h_x: np.ndarray
    h_y: np.ndarray
    time_series: np.ndarray
    dft_results: dict[str, complex]
    s_params: dict[str, complex]


class FdtdSolver:
    """2D TEz FDTD leapfrog 求解器（A09 §10）。

    构造时预校验配置并构建 CPML（若启用）；run() 执行时间步进。
    """

    def __init__(self, config: FdtdConfig) -> None:
        self._cfg = config
        grid = config.grid
        self._grid = grid
        self._ca = grid.ca_ez
        self._cb = grid.cb_ez
        self._da = grid.da_h
        self._db = grid.db_h
        self._dx = grid.dx
        self._dy = grid.dy
        self._dt = grid.dt
        self._eps_r = grid.eps_r
        # CPML 预构建（依赖 grid.shape/dx/dy/dt）
        if config.cpml is not None:
            self._cx, self._cy, self._buffers = build_cpml(
                grid.shape, grid.dx, grid.dy, grid.dt,
                config.cpml, config.eps_r_bg,
            )
        else:
            self._cx = None
            self._cy = None
            self._buffers = None

    def run(self) -> FdtdResult:
        """执行 n_steps 步 leapfrog 推进，返回 FdtdResult。"""
        cfg = self._cfg
        grid = self._grid
        e_z, h_x, h_y = grid.allocate_fields()
        # TFSF 1D 辅助网格（与主网格同 dx/dt，零泄漏）
        incident: Incident1D | None = None
        if cfg.tfsf is not None:
            incident = Incident1D(grid.shape[0], grid.dx, grid.dt)
        # Drude 极化电流
        j_polar: np.ndarray | None = None
        if cfg.drude is not None:
            j_polar = np.zeros(grid.shape, dtype=np.float64)
            mask = cfg.drude_mask
            if mask is not None and mask.dtype != bool:
                mask = mask.astype(bool)
            self._drude_mask = mask
        else:
            self._drude_mask = None
        # 监视器初始化
        for mon in cfg.monitors:
            mon.configure(grid.dt)
        # 探针时序
        probe = cfg.probe_point
        time_series = np.zeros(cfg.n_steps, dtype=np.float64)
        # 时间步进（唯一不可避免的循环）
        # TFSF 时序（Schneider 2004 完美 TFSF 对齐条件）：
        #   H 校正须用 E_inc^n（与 H^{n+1/2} 用 E^n 更新一致）→ step 之前
        #   E 校正须用 H_inc^{n+1/2}（与 E^{n+1} 用 H^{n+1/2} 更新一致）→ step 之后
        # 若顺序颠倒，H 校正用 E_inc^{n+1} 偏移 1 步，在脉冲前沿产生抵消波，
        # 抵消 TF 区入射场，导致平面波注入失败（M1 相对误差=1.0）。
        for n in range(cfg.n_steps):
            t = n * grid.dt
            self._update_h(e_z, h_x, h_y)
            if cfg.tfsf is not None and incident is not None:
                apply_tfsf_h_correction(
                    h_y, cfg.tfsf, incident, self._db, self._dx
                )
                src_val = float(cfg.tfsf_waveform(t))  # type: ignore[arg-type]
                incident.step(src_val)
            self._update_e(e_z, h_x, h_y, j_polar)
            if cfg.tfsf is not None and incident is not None:
                apply_tfsf_e_correction(
                    e_z, cfg.tfsf, incident, self._cb, self._dx
                )
            for src in cfg.dipole_sources:
                inject_dipole(
                    e_z, src, t, grid.dt, grid.eps_r, grid.dx, grid.dy
                )
            if probe is not None:
                time_series[n] = e_z[probe]
            for mon in cfg.monitors:
                mon.record(float(e_z[mon.position]), n)
        return self._collect_result(e_z, h_x, h_y, time_series)

    def _update_h(
        self,
        e_z: np.ndarray,
        h_x: np.ndarray,
        h_y: np.ndarray,
    ) -> None:
        """更新 H^{n+1/2}（向量化，含 CPML ψ_h 校正，A09 §3.2）。"""
        da, db = self._da, self._db
        dx, dy = self._dx, self._dy
        buf = self._buffers
        if buf is not None:
            update_h_psi(e_z, buf, self._cx, self._cy)  # type: ignore[arg-type]
            de_dy = (e_z[:, 1:] - e_z[:, :-1]) / dy
            h_x[:, :-1] = (
                da[:, :-1] * h_x[:, :-1]
                - db[:, :-1] * (de_dy + buf.psi_h_xy[:, :-1])
            )
            de_dx = (e_z[1:, :] - e_z[:-1, :]) / dx
            h_y[:-1, :] = (
                da[:-1, :] * h_y[:-1, :]
                + db[:-1, :] * (de_dx + buf.psi_h_yx[:-1, :])
            )
        else:
            h_x[:, :-1] = (
                da[:, :-1] * h_x[:, :-1]
                - db[:, :-1] * (e_z[:, 1:] - e_z[:, :-1]) / dy
            )
            h_y[:-1, :] = (
                da[:-1, :] * h_y[:-1, :]
                + db[:-1, :] * (e_z[1:, :] - e_z[:-1, :]) / dx
            )

    def _update_e(
        self,
        e_z: np.ndarray,
        h_x: np.ndarray,
        h_y: np.ndarray,
        j_polar: np.ndarray | None,
    ) -> None:
        """更新 E^{n+1}（向量化，含 CPML ψ_e 与 Drude -cb·J 校正，A09 §3.2/§7）。

        时序（Taflove 2005 §9.3，二阶精度 leapfrog）：
            1. J^{n+1/2} = α·J^{n-1/2} + β·E^n   ← 须用 E^n（旧值），故先于 E 更新
            2. E^{n+1}   = ca·E^n + cb·(∇×H)^{n+1/2} - cb·J^{n+1/2}
        若颠倒顺序（先更新 E 再算 J），J 将错误地使用 E^{n+1}，
        形成 E↔J 隐式反馈环，导致 Drude 介质不响应（M3 反射率≈0）。
        """
        ca, cb = self._ca, self._cb
        dx, dy = self._dx, self._dy
        buf = self._buffers
        if buf is not None:
            update_e_psi(h_x, h_y, buf, self._cx, self._cy)  # type: ignore[arg-type]
        # 1. Drude 极化电流更新（须用 E^n，故在 E_z 更新前；Taflove §9.3）
        #    J^{n+1/2} = α·J^{n-1/2} + β·E^n
        if j_polar is not None and self._cfg.drude is not None:
            apply_ade_drude(
                e_z, j_polar, self._cfg.drude, self._dt, self._drude_mask
            )
        # 2. 旋度 (∇×H)_z = ∂H_y/∂x - ∂H_x/∂y（内部 [1:-1, 1:-1]）
        dhy_dx = (h_y[1:-1, 1:-1] - h_y[:-2, 1:-1]) / dx
        dhx_dy = (h_x[1:-1, 1:-1] - h_x[1:-1, :-2]) / dy
        curl_z = dhy_dx - dhx_dy
        interior = (slice(1, -1), slice(1, -1))
        # 3. E^{n+1} = ca·E^n + cb·curl_z (+ CPML ψ_e - cb·J_Drude)
        e_z[interior] = ca[interior] * e_z[interior] + cb[interior] * curl_z
        if buf is not None:
            e_z[interior] += cb[interior] * (
                buf.psi_e_xz[interior] - buf.psi_e_yz[interior]
            )
        if j_polar is not None and self._cfg.drude is not None:
            # Drude 电场校正：E^{n+1} -= cb·J^{n+1/2}（J 已在 mask 外为 0）
            e_z[interior] -= cb[interior] * j_polar[interior]

    def _collect_result(
        self,
        e_z: np.ndarray,
        h_x: np.ndarray,
        h_y: np.ndarray,
        time_series: np.ndarray,
    ) -> FdtdResult:
        """汇总监视器 DFT 与 S 参数，构造 FdtdResult。"""
        dft: dict[str, complex] = {}
        for mon in self._cfg.monitors:
            key = mon.name if mon.name else f"mon_{mon.position}"
            dft[key] = mon.spectrum
        s_params: dict[str, complex] = {}
        for ext in self._cfg.s_param_extractors:
            s_params[ext.name] = ext.compute()
        return FdtdResult(
            e_z=e_z,
            h_x=h_x,
            h_y=h_y,
            time_series=time_series,
            dft_results=dft,
            s_params=s_params,
        )


def solve_fdtd(config: FdtdConfig) -> FdtdResult:
    """便捷入口：构造求解器并运行（A09 §10）。

    Args:
        config: FDTD 仿真配置。

    Returns:
        FdtdResult 终态场与频域结果。
    """
    return FdtdSolver(config).run()
