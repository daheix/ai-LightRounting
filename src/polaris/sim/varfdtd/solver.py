"""VarFDTD 主求解器（A06 §4，编排 EIM + 2D Yee leapfrog + CPML + TFSF）。

VarFDTD（Variational FDTD / 2.5D FDTD）通过有效折射率法（EIM）将 3D 波导结构
折叠为 2D 等效折射率分布，再在该 2D 平面上执行标准 FDTD leapfrog，
以 2D FDTD 的计算成本近似获得 3D FDTD 的精度（Lumerical MODE varFDTD 方案）。

== 算法流水线（A06 §4）==
    1. EIM 折叠（effective_index.compute_effective_index）：
         n_y(x, y) → n_eff(x, y)（2D 等效折射率分布）；
         对于 VarFDTD，n_eff_arr 由调用者提供（已包含 y 方向 EIM 折叠结果）。
    2. 构造 2D Yee 网格（yee_2d.build_2d_grid）：
         eps_r = n_eff² → YeeGridFdtd（ca/cb/da/db 预计算，Courant 校验）；
    3. 时间步进循环（唯一不可避免的主循环）：
         for n in range(n_steps):
             step_leapfrog(grid, fields, cpml_buffers, cx, cy)   # H/E 半步更新
             apply_tfsf_h_correction(...)                        # TFSF H 校正
             apply_tfsf_e_correction(...)                        # TFSF E 校正
             inject_source(...)                                    # 软源注入
             monitor.record(...)                                   # DFT 在线累加
             fields.check_nan()                                    # 稳定性检查
    4. S 参数提取（monitor.SParamExtractor.compute）：
         S21 = DFT_out / DFT_in，S11 = DFT_refl / DFT_in。

== 假设与局限（与 Lumerical varFDTD 一致）==
- 不同 slab 模式间耦合可忽略（弱耦合假设，SOI 平面波导适用）；
- 单偏振（TE 或 TM，由 EIM 时的 polarization 决定）；
- 等效折射率分布需预先计算（本求解器不重新执行 EIM，n_eff_arr 直接由调用者传入）。

== M2/M3 验收 ==
- M2 稳定性：高斯脉冲传播 500 步无 NaN/Inf（fields.check_nan raise）；
- M3 S 参数：直波导 S21 相位 = exp(i·n_eff·k0·L)，对比误差 ≤5%。
  M3 通过将源置于波导入射端口，监视器置于输出端口，
  提取 S21 = DFT_out/DFT_in 的复值，与解析相位 exp(i·n_eff·k0·L) 对比。

*创新*：与 A09-FDTD solver 解耦但共享底座——VarFdtdSolver 复用 A09 的
CPML（cpml.build_cpml）、TFSF（tfsf.apply_tfsf_*_correction）、源
（sources.GaussianPulse/DipoleSource/inject_dipole）、监视器
（monitor.DftMonitor/SParamExtractor），仅通过 yee_2d.step_leapfrog
执行 EIM 折叠后的 2D 时间步进。这样 VarFDTD 与 3D FDTD 共用相同的物理常数、
更新系数与边界处理，避免重复实现与潜在不一致。
- 底层逻辑：n_eff_arr → eps_r → YeeGridFdtd → 标准 leapfrog；
  CPML/TFSF/源/监视器全部沿用 A09，行为与 3D FDTD 一致。
- 支持理论：Lumerical varFDTD solver（Ansys Optics 文档）证明 EIM+2D FDTD
  在弱耦合假设下与 3D FDTD 偏差 <5%；Hammer-Ivanova 2008 / Snyder-Love
  1983 提供变分法理论基础（reciprocity 与变分两种实现路径）。
- 案例：SOI 直波导 S21 相位扫描、Y 分支透射谱、环谐振器 FSR 提取。

== 检索记录（R01 方案检索）==
- 关键词："varFDTD effective index method Lumerical"
- 关键词："effective index method waveguide 2D FDTD reduction"
- 关键词："Lumerical varFDTD 2.5D time domain simulation"
- 采用方案：复用 A09-FDTD 底座（YeeGridFdtd/CPML/TFSF/sources/monitor），
  仅添加 EIM 折叠 + 2D 时间步进编排
- 来源：Ansys Optics varFDTD、Lumerical、Yee 1966、Taflove 2005、Chang 1980

文献来源（≥5，规则 18 学术诚信）：
1. Chang 1980 IEEE Trans MTT 28(8) 889（EIM）—
   https://doi.org/10.1109/TMTT.1980.1130551
2. Lumerical varFDTD — https://www.lumerical.com/products/varfdtd/
3. Marcatili 1969 Bell Syst Tech J 48(7) 2071（条形波导近似）—
   https://doi.org/10.1002/j.1538-7305.1969.tb01161.x
4. Kumar et al. 1985 IEEE JQE 21(1)（EIM 修正）—
   https://doi.org/10.1109/JQE.1985.1072717
5. Yee 1966 IEEE Trans AP 14(3) 302-307（leapfrog 交错网格）—
   https://doi.org/10.1109/TAP.1966.1138693
6. Taflove & Hagness 2005 Computational Electrodynamics —
   https://www.artechhouse.com/Computational-Electrodynamics/Kane-Taflove/p/Book-927
7. Soref 1991 IEEE JQE 27(8) 1971（SOI 波导）—
   https://doi.org/10.1109/3.84143

规则依据：规则 14（非法输入 raise，无 fall-back）/规则 18（学术诚信）/
规则 26（纯 CPU numpy）/规则 9（单文件版本，复用 A09 不重写）/
§4（向量化，仅时间步主循环例外）
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from polaris.sim.fdtd.cpml import CpmlConfig, build_cpml
from polaris.sim.fdtd.monitor import DftMonitor, SParamExtractor
from polaris.sim.fdtd.sources import DipoleSource, Waveform, inject_dipole
from polaris.sim.fdtd.tfsf import (
    Incident1D,
    TfsfBox,
    apply_tfsf_e_correction,
    apply_tfsf_h_correction,
)
from polaris.sim.fdtd.yee_grid import YeeGridFdtd, courant_dt
from polaris.sim.varfdtd.yee_2d import (
    Yee2DFields,
    build_eps_from_neff,
    step_leapfrog,
)

__all__ = [
    "VarFdtdConfig",
    "VarFdtdResult",
    "VarFdtdSolver",
    "solve_varfdtd",
]


@dataclass
class VarFdtdConfig:
    """VarFDTD 2.5D 仿真配置（A06 §4）。

    Attributes:
        wavelength: 自由空间波长（米），>0。用于 DFT 监视频率与 TFSF 默认频率。
        dx, dy: 网格间距（米），>0。
        dt: 时间步（秒），None 则按 Courant 上限×cfl 自动计算。
        cfl: Courant 数，dt=None 时使用，∈ (0, 1]，默认 0.99。
        n_eff_arr: EIM 折叠后的 2D 等效折射率分布 (Nx, Ny)，>0。
            由 effective_index.compute_effective_index 提供或外部预计算。
        n_steps: 时间步数，>0。
        source: 软源（DipoleSource）注入，None 表示无源（用于 TFSF 主导场景）。
        sources: 多源列表（线源/模式源模拟，可选；与 source 同时生效，去重处理）。
        monitors: DFT 监视器列表（在线累加）。
        s_param_extractors: S 参数提取器列表（双监视器比值）。
        tfsf_box: TFSF 边界规格，None 表示不使用平面波注入。
        tfsf_waveform: TFSF 入射波形（tfsf_box 非 None 时必填）。
        pml_config: CPML 参数，None 表示无 PML（外环 PEC）。
        eps_r_bg: 背景相对介电常数（CPML σ_max 估计用），默认取 min(n_eff²)。
        probe_point: 探针网格索引 (i, j)，None 不记录时序。
        check_nan_steps: NaN 检查间隔步数，默认 50（每 50 步检查一次稳定性）。
    """

    wavelength: float
    dx: float
    dy: float
    n_eff_arr: np.ndarray
    n_steps: int
    dt: float | None = None
    cfl: float = 0.99
    source: DipoleSource | None = None
    sources: list[DipoleSource] = field(default_factory=list)
    monitors: list[DftMonitor] = field(default_factory=list)
    s_param_extractors: list[SParamExtractor] = field(default_factory=list)
    tfsf_box: TfsfBox | None = None
    tfsf_waveform: Waveform | None = None
    pml_config: CpmlConfig | None = None
    eps_r_bg: float | None = None
    probe_point: tuple[int, int] | None = None
    check_nan_steps: int = 50

    def __post_init__(self) -> None:
        self._validate_scalars()
        eps_r = build_eps_from_neff(self.n_eff_arr)
        self._eps_r = eps_r
        self._validate_grid_and_bg(eps_r)
        self._validate_tfsf()
        self._validate_positions(eps_r.shape)

    def _validate_scalars(self) -> None:
        """校验标量参数（波长/网格/步数/CFL/NaN 检查间隔）。"""
        if self.wavelength <= 0.0:
            raise ValueError(f"wavelength 须 >0，实际 {self.wavelength}")
        if self.dx <= 0.0:
            raise ValueError(f"dx 须 >0，实际 {self.dx}")
        if self.dy <= 0.0:
            raise ValueError(f"dy 须 >0，实际 {self.dy}")
        if self.n_steps <= 0:
            raise ValueError(f"n_steps 须 >0，实际 {self.n_steps}")
        if not (0.0 < self.cfl <= 1.0):
            raise ValueError(f"cfl 须 ∈ (0, 1]，实际 {self.cfl}")
        if self.check_nan_steps <= 0:
            raise ValueError(f"check_nan_steps 须 >0，实际 {self.check_nan_steps}")

    def _validate_grid_and_bg(self, eps_r: np.ndarray) -> None:
        """校验网格尺寸与背景介电常数（eps_r_bg 缺省取 min(eps_r)）。"""
        nx, ny = eps_r.shape
        if nx < 5 or ny < 5:
            raise ValueError(f"n_eff_arr 网格过小 {(nx, ny)}，至少 5x5")
        if self.eps_r_bg is None:
            self.eps_r_bg = float(eps_r.min())
        if self.eps_r_bg <= 0.0:
            raise ValueError(f"eps_r_bg 须 >0，实际 {self.eps_r_bg}")

    def _validate_tfsf(self) -> None:
        """校验 TFSF 边界与波形联合约束。"""
        if self.tfsf_box is not None and self.tfsf_waveform is None:
            raise ValueError("tfsf_box 非 None 时 tfsf_waveform 必填")

    def _validate_positions(self, shape: tuple[int, int]) -> None:
        """校验监视器、探针、软源位置是否在网格范围内。"""
        nx, ny = shape
        for mon in self.monitors:
            self._check_position_in_bounds(mon.position, nx, ny, "监视器")
        if self.probe_point is not None:
            self._check_position_in_bounds(self.probe_point, nx, ny, "探针")
        if self.source is not None:
            self._check_position_in_bounds(self.source.position, nx, ny, "软源")
        for src in self.sources:
            self._check_position_in_bounds(src.position, nx, ny, "软源")

    @staticmethod
    def _check_position_in_bounds(
        position: tuple[int, int], nx: int, ny: int, label: str
    ) -> None:
        """单点越界检查，越界则 raise IndexError。"""
        ix, iy = position
        if not (0 <= ix < nx and 0 <= iy < ny):
            raise IndexError(f"{label} {position} 越界 {(nx, ny)}")


@dataclass
class VarFdtdResult:
    """VarFDTD 仿真结果（A06 §4）。

    Attributes:
        e_z, h_x, h_y: 终态场 (Nx, Ny)。
        fields_time: 探针点 E_z 时序 (n_steps,)（无探针则为空数组）。
        s_params: S 参数名 → 复 S 值（M3 验收用）。
        dft_results: 监视器名 → 复 DFT 谱。
        energy_history: 全场能量 ∫|E|²+|H|² 历史 (n_steps//sample_step,)，
            默认每 50 步采样一次（A06 §M2 稳定性追踪）。
        n_eff_used: 仿真中实际使用的 2D n_eff 分布（供后续分析）。
    """

    e_z: np.ndarray
    h_x: np.ndarray
    h_y: np.ndarray
    fields_time: np.ndarray
    s_params: dict[str, complex]
    dft_results: dict[str, complex]
    energy_history: np.ndarray
    n_eff_used: np.ndarray


class VarFdtdSolver:
    """VarFDTD 2.5D 求解器（A06 §4）。

    构造时预校验配置、构建 YeeGridFdtd 与 CPML（若启用）；run() 执行时间步进。
    """

    def __init__(self, config: VarFdtdConfig) -> None:
        self._cfg = config
        # 时间步：优先用 config.dt，否则按 CFL 自动计算
        dt = (
            config.dt if config.dt is not None else courant_dt(config.dx, config.dy, cfl=config.cfl)
        )
        self._dt = dt
        # 2D Yee 网格（EIM 折叠后的等效 eps_r）
        self._grid = YeeGridFdtd(
            shape=config._eps_r.shape,
            dx=config.dx,
            dy=config.dy,
            dt=dt,
            eps_r=config._eps_r,
        )
        # CPML 预构建
        if config.pml_config is not None:
            self._cx, self._cy, self._buffers = build_cpml(
                self._grid.shape,
                self._grid.dx,
                self._grid.dy,
                dt,
                config.pml_config,
                config.eps_r_bg,  # type: ignore[arg-type]
            )
        else:
            self._cx = None
            self._cy = None
            self._buffers = None

    @property
    def grid(self) -> YeeGridFdtd:
        """底层 2D Yee 网格（供外部诊断）。"""
        return self._grid

    @property
    def dt(self) -> float:
        """实际时间步（秒）。"""
        return self._dt

    def run(self) -> VarFdtdResult:
        """执行 n_steps 步 leapfrog 推进，返回 VarFdtdResult。"""
        cfg = self._cfg
        grid = self._grid
        fields = Yee2DFields.zeros(grid.shape)
        # TFSF 1D 辅助网格（Schneider 2004 完美 TFSF 对齐）
        incident: Incident1D | None = None
        if cfg.tfsf_box is not None:
            incident = Incident1D(grid.shape[0], grid.dx, self._dt)
        # 监视器初始化
        for mon in cfg.monitors:
            mon.configure(self._dt)
        # 探针时序 + 能量历史
        probe = cfg.probe_point
        time_series = np.zeros(cfg.n_steps, dtype=np.float64)
        sample_step = max(1, cfg.check_nan_steps)
        n_energy = cfg.n_steps // sample_step + 1
        energy_history = np.zeros(n_energy, dtype=np.float64)
        e_idx = 0
        # 时间步进主循环（唯一不可避免）
        for n in range(cfg.n_steps):
            t = n * self._dt
            self._step(fields, t, incident)
            if probe is not None:
                time_series[n] = fields.e_z[probe]
            for mon in cfg.monitors:
                mon.record(float(fields.e_z[mon.position]), n)
            if n % sample_step == 0 and e_idx < n_energy:
                energy_history[e_idx] = self._compute_energy(fields)
                e_idx += 1
            # 周期性 NaN 检查（M2 稳定性验收，规则 14）
            if n % sample_step == 0:
                fields.check_nan("VarFDTD")
        energy_history = energy_history[:e_idx]
        return self._collect_result(fields, time_series, energy_history)

    def _step(
        self,
        fields: Yee2DFields,
        t: float,
        incident: Incident1D | None,
    ) -> None:
        """单步完整 leapfrog + TFSF + 软源（与 A09-FDTD solver 同序）。"""
        cfg = self._cfg
        grid = self._grid
        # 1. leapfrog H/E 半步更新（含 CPML ψ）
        step_leapfrog(grid, fields, self._buffers, self._cx, self._cy)
        # 2. TFSF H 校正（H 更新后、E 更新前）
        if cfg.tfsf_box is not None and incident is not None:
            apply_tfsf_h_correction(fields.h_y, cfg.tfsf_box, incident, grid.db_h, grid.dx)
            src_val = float(cfg.tfsf_waveform(t))  # type: ignore[arg-type]
            incident.step(src_val)
            apply_tfsf_e_correction(fields.e_z, cfg.tfsf_box, incident, grid.cb_ez, grid.dx)
        # 3. 软源注入（Taflove 2005 §5.5）—— 单源 + 多源列表合并处理
        if cfg.source is not None:
            inject_dipole(fields.e_z, cfg.source, t, self._dt, grid.eps_r, grid.dx, grid.dy)
        for src in cfg.sources:
            inject_dipole(fields.e_z, src, t, self._dt, grid.eps_r, grid.dx, grid.dy)

    @staticmethod
    def _compute_energy(fields: Yee2DFields) -> float:
        """全场能量 ∫(|E|² + |H|²) dA（无单位因子，仅稳定性追踪用）。"""
        return float(
            np.sum(fields.e_z * fields.e_z)
            + np.sum(fields.h_x * fields.h_x)
            + np.sum(fields.h_y * fields.h_y)
        )

    def _collect_result(
        self,
        fields: Yee2DFields,
        time_series: np.ndarray,
        energy_history: np.ndarray,
    ) -> VarFdtdResult:
        """汇总 DFT/S 参数与终态场，构造 VarFdtdResult。"""
        dft: dict[str, complex] = {}
        for mon in self._cfg.monitors:
            key = mon.name if mon.name else f"mon_{mon.position}"
            dft[key] = mon.spectrum
        s_params: dict[str, complex] = {}
        for ext in self._cfg.s_param_extractors:
            s_params[ext.name] = ext.compute()
        return VarFdtdResult(
            e_z=fields.e_z,
            h_x=fields.h_x,
            h_y=fields.h_y,
            fields_time=time_series,
            s_params=s_params,
            dft_results=dft,
            energy_history=energy_history,
            n_eff_used=np.asarray(self._cfg.n_eff_arr, dtype=np.float64),
        )


def solve_varfdtd(config: VarFdtdConfig) -> VarFdtdResult:
    """便捷入口：构造求解器并运行（A06 §4）。

    Args:
        config: VarFDTD 仿真配置。

    Returns:
        VarFdtdResult 终态场与频域结果（含 S 参数、能量历史）。
    """
    return VarFdtdSolver(config).run()
