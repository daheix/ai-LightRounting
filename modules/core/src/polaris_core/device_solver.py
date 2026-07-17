"""统一器件级求解器调度（polaris-core）。

为光子器件提供单一入口，根据几何特征自动选择最合适的器件级求解器
（EME 1D/2D / FDE / RCWA / varFDTD / BPM / FDTD），或由用户显式指定方法。
各求解器委托对应子模块，本模块仅做调度与结果归一化，不重复实现物理。

## 自动选择策略（_select_method）

| 几何特征 | 求解器 | 依据 |
|---------|--------|------|
| 1D slab 波导（sections 无 height_um） | EME 1D | 模式匹配高效 |
| 2D 任意截面波导（sections 含 height_um） | EME 2D | 任意截面模式展开 |
| 周期性结构 / 光栅（is_periodic 或 type=grating） | RCWA | 周期结构严格耦合波 |
| 大型 3D 传播（type=propagation_2_5d） | varFDTD | EIM 2.5D 折叠 |
| 光束传播（type=beam_propagation） | BPM | 抛物波动方程 |
| 全 3D 精确（type=full_3d） | FDTD | Yee 全波 |
| 模式分析（type=mode_analysis） | FDE | 本征模求解 |

## 几何（geometry dict）schema

```
{
  "type": "waveguide"|"taper"|"grating"|"mode_analysis"|
          "propagation_2_5d"|"beam_propagation"|"full_3d",  # 默认 "waveguide"
  "is_periodic": bool,            # 默认 False（True → RCWA）
  "sections": [...],              # EME 段列表
  "layers": [...],                # RCWA 层列表（dict 或 GratingLayer）
  "rcwa_config": {...},           # 可选 RCWA 配置覆盖
  "n_eff_arr": ndarray,           # varFDTD 等效折射率分布（可选）
  "n_core": float, "n_clad": float,
  "width_um": float, "height_um": float, "length_um": float,
  "period_um": float,             # RCWA 周期
}
```

## Input / Process / Output

- I: geometry(dict) + DeviceSolverConfig(method/wavelength_um/网格参数)
- P: _select_method → 委托对应 _solve_* → 归一化 DeviceSolverResult
- O: DeviceSolverResult(s_matrix, modes, field_profile, solver_used, metadata)

## 来源（R02 学术诚信，≥5 个文献 URL）
- Bienstman 2001 PhD §2.3（2D EME 模式匹配）
  https://www.photonics.intec.ugent.be/download/phd_bienstman.pdf
- Smit & van Dam 1996 JLT（模式展开理论）
  https://doi.org/10.1109/50.511954
- Lumerical EME 2D 文档
  https://optics.ansys.com/hc/en-us/articles/360034902413
- Yee 1966 IEEE TAP（FDTD）
  https://doi.org/10.1109/TAP.1966.1138693
- Chang 1980 IEEE TMTT（varFDTD EIM）
  https://doi.org/10.1109/TMTT.1980.1130198
- Moharam 1995 JOSA A（RCWA ETM）
  https://doi.org/10.1364/JOSAA.12.001077
- Feit & Fleck 1978 Appl. Opt.（BPM）
  https://opg.optica.org/ao/abstract.cfm?uri=ao-17-24-3990
- Lumerical 求解器选择指南
  https://optics.ansys.com/hc/en-us/articles/360034902433
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

__all__ = [
    "DeviceSolverConfig",
    "DeviceSolverResult",
    "DeviceLevelSolver",
    "solve_device",
    "VALID_METHODS",
]

# 合法求解方法
VALID_METHODS = ("auto", "eme", "fde", "rcwa", "varfdtd", "bpm", "fdtd")

# 默认物理参数（Soref 1993 SOI，R02 可溯源）
# https://ieeexplore.ieee.org/document/1148303
DEFAULT_N_CORE = 3.476  # Si @ 1.55μm
DEFAULT_N_CLAD = 1.444  # SiO2 @ 1.55μm


@dataclass
class DeviceSolverConfig:
    """器件级求解器配置。

    Attributes:
        method: 求解方法（auto/eme/fde/rcwa/varfdtd/bpm/fdtd）。
        wavelength_um: 真空波长（μm）。
        dx_um: x 方向网格步长（μm）。
        dy_um: y 方向网格步长（μm）。
        dz_um: z 方向网格步长（μm，BPM/varFDTD 传播方向）。
        pad_um: 包层 padding（μm，每侧）。
        n_modes: 求解模式数（EME/FDE）。
        n_steps_fdtd: FDTD 时间步数。
        n_steps_varfdtd: varFDTD 时间步数。
        n_harmonics_rcwa: RCWA 傅里叶截断阶数。
    """

    method: str = "auto"
    wavelength_um: float = 1.55
    dx_um: float = 0.02
    dy_um: float = 0.02
    dz_um: float = 0.1
    pad_um: float = 1.0
    n_modes: int = 4
    n_steps_fdtd: int = 200
    n_steps_varfdtd: int = 50
    n_harmonics_rcwa: int = 5

    def __post_init__(self) -> None:
        if self.method not in VALID_METHODS:
            raise ValueError(
                f"method 须 ∈ {VALID_METHODS}，得到 '{self.method}'（R03）"
            )
        if self.wavelength_um <= 0:
            raise ValueError(f"wavelength_um 须 > 0，得到 {self.wavelength_um}")


@dataclass
class DeviceSolverResult:
    """器件级求解器统一结果。

    Attributes:
        s_matrix: 2×2 复 S 矩阵 [[S11,S12],[S21,S22]]，无 S 矩阵的求解器为 None。
        modes: 模式信息列表（每项含 neff/beta 等）。
        field_profile: 终态场分布（ndarray），无场分布时为 None。
        solver_used: 实际使用的求解器名。
        metadata: 求解器特定元数据（transmission/reflection/neff 等）。
    """

    s_matrix: np.ndarray | None
    modes: list = field(default_factory=list)
    field_profile: np.ndarray | None = None
    solver_used: str = ""
    metadata: dict = field(default_factory=dict)


class DeviceLevelSolver:
    """统一器件级求解器调度器。

    根据几何特征自动选择求解器，或由 ``DeviceSolverConfig.method`` 显式指定。
    各 ``_solve_*`` 方法委托对应子模块，仅做调度与结果归一化。
    """

    def __init__(self, config: DeviceSolverConfig | None = None) -> None:
        self.config = config or DeviceSolverConfig()

    def solve(self, geometry: dict, config: DeviceSolverConfig | None = None) -> DeviceSolverResult:
        """求解器件，返回统一 DeviceSolverResult。

        Args:
            geometry: 器件几何描述 dict（见模块 docstring schema）。
            config: 可选配置覆盖（None 用实例 config）。

        Returns:
            DeviceSolverResult。

        Raises:
            ValueError: 几何非法或方法不支持（R03 禁止 fall-back）。
        """
        cfg = config or self.config
        if not isinstance(geometry, dict):
            raise ValueError(f"geometry 须 dict，得到 {type(geometry).__name__}")
        method = cfg.method
        if method == "auto":
            method = self._select_method(geometry)
        handler = self._dispatch(method)
        return handler(geometry, cfg)

    def _dispatch(self, method: str):
        """方法名 → 委托函数映射。"""
        mapping = {
            "eme": self._solve_eme,
            "fde": self._solve_fde,
            "rcwa": self._solve_rcwa,
            "varfdtd": self._solve_varfdtd,
            "bpm": self._solve_bpm,
            "fdtd": self._solve_fdtd,
        }
        if method not in mapping:
            raise ValueError(
                f"不支持的求解方法 '{method}'，须 ∈ {VALID_METHODS}（R03）"
            )
        return mapping[method]

    def _select_method(self, geometry: dict) -> str:
        """自动选择最合适求解器（依据几何特征）。"""
        gtype = geometry.get("type", "waveguide")
        if geometry.get("is_periodic") or gtype == "grating":
            return "rcwa"
        if gtype == "mode_analysis":
            return "fde"
        if gtype == "propagation_2_5d":
            return "varfdtd"
        if gtype == "beam_propagation":
            return "bpm"
        if gtype == "full_3d":
            return "fdtd"
        # waveguide / taper → EME（1D 或 2D 由 _solve_eme 内部判定）
        return "eme"

    # =====================================================================
    # EME（1D slab / 2D 任意截面）
    # =====================================================================

    def _solve_eme(self, geometry: dict, cfg: DeviceSolverConfig) -> DeviceSolverResult:
        """委托 EME 求解器。sections 段含 height_um → EME 2D，否则 EME 1D。"""
        sections = geometry.get("sections")
        if not sections:
            raise ValueError("EME 须 geometry['sections'] 非空（R03）")
        if isinstance(sections[0], dict) and "height_um" in sections[0]:
            return self._solve_eme_2d(sections, cfg)
        return self._solve_eme_1d(sections, cfg)

    def _solve_eme_1d(self, sections, cfg) -> DeviceSolverResult:
        """1D slab EME 委托 polaris_eme.solve_eme。"""
        from polaris_eme import solve_eme

        result = solve_eme(
            sections=sections,
            wavelength_um=cfg.wavelength_um,
            n_modes_per_section=cfg.n_modes,
            dx_um=cfg.dx_um,
            pad_um=cfg.pad_um,
        )
        s_mat = np.array(result["s_matrix"], dtype=complex)
        return DeviceSolverResult(
            s_matrix=s_mat,
            modes=result["sections_info"],
            field_profile=None,
            solver_used="eme",
            metadata={
                "transmission": result["transmission"],
                "reflection": result["reflection"],
                "transmission_db": result["transmission_db"],
                "n_sections": result["n_sections"],
                "eme_dim": "1d",
            },
        )

    def _solve_eme_2d(self, sections, cfg) -> DeviceSolverResult:
        """2D 任意截面 EME 委托 polaris_eme.solve_eme_2d。"""
        from polaris_eme import solve_eme_2d

        result = solve_eme_2d(
            sections=sections,
            wavelength_um=cfg.wavelength_um,
            n_modes_per_section=cfg.n_modes,
            dx_um=cfg.dx_um,
            dy_um=cfg.dy_um,
            pad_um=cfg.pad_um,
        )
        s_mat = np.array(result["s_matrix"], dtype=complex)
        return DeviceSolverResult(
            s_matrix=s_mat,
            modes=result["modes_per_section"],
            field_profile=None,
            solver_used="eme",
            metadata={
                "transmission": result["transmission"],
                "reflection": result["reflection"],
                "n_sections": result["n_sections"],
                "eme_dim": "2d",
            },
        )

    # =====================================================================
    # FDE（2D 模式分析）
    # =====================================================================

    def _solve_fde(self, geometry: dict, cfg: DeviceSolverConfig) -> DeviceSolverResult:
        """委托 polaris_fde.solve_modes 求解 2D 本征模。"""
        from polaris_fde import solve_modes

        n_core = geometry.get("n_core", DEFAULT_N_CORE)
        n_clad = geometry.get("n_clad", DEFAULT_N_CLAD)
        width_um = geometry.get("width_um")
        height_um = geometry.get("height_um")
        if width_um is None or height_um is None:
            raise ValueError("FDE 须 geometry['width_um']/['height_um']（R03）")
        result = solve_modes(
            width_um=float(width_um), height_um=float(height_um),
            wavelength_um=cfg.wavelength_um, n_core=n_core, n_clad=n_clad,
            n_modes=cfg.n_modes, dx_um=cfg.dx_um, pad_um=cfg.pad_um,
        )
        field = None
        if result["modes"]:
            field = np.array(result["modes"][0]["field_2d"], dtype=float)
        return DeviceSolverResult(
            s_matrix=None,
            modes=result["modes"],
            field_profile=field,
            solver_used="fde",
            metadata={
                "n_modes": result["n_modes"],
                "grid_info": result["grid_info"],
                "physics": result["physics"],
            },
        )

    # =====================================================================
    # RCWA（1D/2D 周期光栅）
    # =====================================================================

    def _solve_rcwa(self, geometry: dict, cfg: DeviceSolverConfig) -> DeviceSolverResult:
        """委托 polaris_multiphysics.rcwa.solve_rcwa_1d/2d。

        geometry['layers'] 可为 GratingLayer1D/2D 实例或 dict
        {thickness(m), eps_r_period(ndarray)}。
        """
        from polaris_multiphysics.rcwa import (
            GratingLayer1D, GratingLayer2D, RcwaConfig1D, RcwaConfig2D,
            solve_rcwa_1d, solve_rcwa_2d,
        )

        layers_raw = geometry.get("layers")
        if not layers_raw:
            raise ValueError("RCWA 须 geometry['layers'] 非空（R03）")
        layers = [
            self._build_rcwa_layer(l, GratingLayer1D, GratingLayer2D)
            for l in layers_raw
        ]
        rcwa_cfg = geometry.get("rcwa_config", {})
        wl_m = cfg.wavelength_um * 1e-6
        period_um = geometry.get("period_um", 1.0)
        if isinstance(layers[0], GratingLayer2D):
            cfg_obj = RcwaConfig2D(
                wavelength=wl_m, period_x=period_um * 1e-6,
                period_y=rcwa_cfg.get("period_y_um", period_um) * 1e-6,
                n_harmonics_x=rcwa_cfg.get("n_harmonics_x", cfg.n_harmonics_rcwa),
                n_harmonics_y=rcwa_cfg.get("n_harmonics_y", cfg.n_harmonics_rcwa),
                n_inc=rcwa_cfg.get("n_inc", 1.0), n_sub=rcwa_cfg.get("n_sub", 1.0),
            )
            result = solve_rcwa_2d(layers, cfg_obj)
        else:
            cfg_obj = RcwaConfig1D(
                wavelength=wl_m, period=period_um * 1e-6,
                n_harmonics=rcwa_cfg.get("n_harmonics", cfg.n_harmonics_rcwa),
                n_inc=rcwa_cfg.get("n_inc", 1.0), n_sub=rcwa_cfg.get("n_sub", 1.0),
                polarization=rcwa_cfg.get("polarization", "te"),
            )
            result = solve_rcwa_1d(layers, cfg_obj)
        return self._build_rcwa_result(result)

    @staticmethod
    def _build_rcwa_layer(layer, cls1d, cls2d):
        """dict 或 GratingLayer → GratingLayer 实例（按 eps_r 维度选 1D/2D）。"""
        if isinstance(layer, (cls1d, cls2d)):
            return layer
        if not isinstance(layer, dict):
            raise ValueError(f"RCWA layer 须 dict 或 GratingLayer，得到 {type(layer)}")
        eps = np.asarray(layer["eps_r_period"], dtype=np.float64)
        if eps.ndim == 1:
            return cls1d(thickness=float(layer["thickness"]), eps_r_period=eps)
        return cls2d(thickness=float(layer["thickness"]), eps_r_period=eps)

    @staticmethod
    def _build_rcwa_result(result) -> DeviceSolverResult:
        """从 RCWA 结果构造 DeviceSolverResult（0 阶 r/t 振幅 → 2×2 S 矩阵）。"""
        r_eff = np.asarray(result.reflection_eff)
        t_eff = np.asarray(result.transmission_eff)
        center = r_eff.size // 2  # 0 阶衍射（正入射中央级）
        r0 = float(r_eff[center])
        t0 = float(t_eff[center])
        # 0 阶振幅（能量效率开方，正入射相位近似实数）
        # 对称结构正入射：S12≈S21, S22≈S11（互易性，Liu & Fan 2012）
        s_mat = np.array(
            [[np.sqrt(max(r0, 0.0)), np.sqrt(max(t0, 0.0))],
             [np.sqrt(max(t0, 0.0)), np.sqrt(max(r0, 0.0))]],
            dtype=complex,
        )
        return DeviceSolverResult(
            s_matrix=s_mat,
            modes=[],
            field_profile=None,
            solver_used="rcwa",
            metadata={
                "reflection_eff_0th": r0,
                "transmission_eff_0th": t0,
                "energy_sum": float(result.energy_sum),
                "iterations": int(result.iterations),
            },
        )

    # =====================================================================
    # varFDTD（2.5D 有效折射率法）
    # =====================================================================

    def _solve_varfdtd(self, geometry: dict, cfg: DeviceSolverConfig) -> DeviceSolverResult:
        """委托 polaris_multiphysics.varfdtd.solve_varfdtd。

        n_eff_arr 取 geometry['n_eff_arr']，或由 width/height/n_core/n_clad
        构造矩形 EIM 分布（芯区 n_core、包层 n_clad 的粗略 EIM 近似）。
        """
        from polaris_multiphysics.varfdtd import VarFdtdConfig, solve_varfdtd

        n_eff_arr = self._build_neff_arr(geometry, cfg)
        wl_m = cfg.wavelength_um * 1e-6
        var_cfg = VarFdtdConfig(
            wavelength=wl_m,
            dx=cfg.dx_um * 1e-6,
            dy=cfg.dy_um * 1e-6,
            n_eff_arr=n_eff_arr,
            n_steps=cfg.n_steps_varfdtd,
        )
        result = solve_varfdtd(var_cfg)
        s_params = dict(result.s_params) if result.s_params else {}
        s_mat = None
        if "S21" in s_params and "S11" in s_params:
            s21 = complex(s_params["S21"])
            s11 = complex(s_params["S11"])
            s_mat = np.array([[s11, s21], [s21, s11]], dtype=complex)
        return DeviceSolverResult(
            s_matrix=s_mat,
            modes=[],
            field_profile=np.asarray(result.e_z),
            solver_used="varfdtd",
            metadata={
                "s_params": {k: complex(v) for k, v in s_params.items()},
                "energy_history": np.asarray(result.energy_history).tolist(),
                "n_steps": cfg.n_steps_varfdtd,
            },
        )

    @staticmethod
    def _build_neff_arr(geometry: dict, cfg: DeviceSolverConfig) -> np.ndarray:
        """构造 2D n_eff 分布。优先用 geometry['n_eff_arr']，否则矩形近似。"""
        if "n_eff_arr" in geometry:
            return np.asarray(geometry["n_eff_arr"], dtype=np.float64)
        n_core = geometry.get("n_core", DEFAULT_N_CORE)
        n_clad = geometry.get("n_clad", DEFAULT_N_CLAD)
        width_um = geometry.get("width_um", 2.0)
        height_um = geometry.get("height_um", 2.0)
        # 粗略 EIM：芯区有效折射率 ≈ n_core（保守上界），包层 n_clad
        nx = max(int(round((width_um + 2 * cfg.pad_um) / cfg.dx_um)), 10)
        ny = max(int(round((height_um + 2 * cfg.pad_um) / cfg.dy_um)), 10)
        n_eff = np.full((nx, ny), n_clad, dtype=np.float64)
        cx0, cx1 = nx // 2 - max(int(round(width_um / cfg.dx_um / 2)), 1), \
            nx // 2 + max(int(round(width_um / cfg.dx_um / 2)), 1)
        cy0, cy1 = ny // 2 - max(int(round(height_um / cfg.dy_um / 2)), 1), \
            ny // 2 + max(int(round(height_um / cfg.dy_um / 2)), 1)
        n_eff[cx0:cx1, cy0:cy1] = n_core
        return n_eff

    # =====================================================================
    # BPM（光束传播法）
    # =====================================================================

    def _solve_bpm(self, geometry: dict, cfg: DeviceSolverConfig) -> DeviceSolverResult:
        """委托 polaris_bpm.solve_bpm。"""
        from polaris_bpm import solve_bpm

        n_core = geometry.get("n_core", DEFAULT_N_CORE)
        n_clad = geometry.get("n_clad", DEFAULT_N_CLAD)
        width_um = geometry.get("width_um", 0.5)
        length_um = geometry.get("length_um", 50.0)
        result = solve_bpm(
            width_um=float(width_um), length_um=float(length_um),
            wavelength_um=cfg.wavelength_um, n_core=n_core, n_clad=n_clad,
            dz_um=cfg.dz_um, dx_um=cfg.dx_um, pad_um=cfg.pad_um,
        )
        field_z = result.get("field_z")
        field_profile = None
        if field_z:
            field_profile = np.array(field_z[-1], dtype=complex)
        t_db = float(result.get("transmission_db", 0.0))
        t_lin = float(10.0 ** (t_db / 20.0))
        s_mat = np.array([[0.0 + 0.0j, t_lin], [t_lin, 0.0 + 0.0j]], dtype=complex)
        return DeviceSolverResult(
            s_matrix=s_mat,
            modes=[],
            field_profile=field_profile,
            solver_used="bpm",
            metadata={
                "transmission_db": t_db,
                "n_steps": int(result.get("n_steps", 0)),
                "grid_info": result.get("grid_info", {}),
            },
        )

    # =====================================================================
    # FDTD（3D 全波时域有限差分）
    # =====================================================================

    def _solve_fdtd(self, geometry: dict, cfg: DeviceSolverConfig) -> DeviceSolverResult:
        """委托 polaris_fdtd.simulate_waveguide_fdtd。"""
        from polaris_fdtd import simulate_waveguide_fdtd

        nx = int(geometry.get("nx", 32))
        ny = int(geometry.get("ny", 24))
        nz = int(geometry.get("nz", 20))
        pml_layers = int(geometry.get("pml_layers", 4))
        result = simulate_waveguide_fdtd(
            dx_um=cfg.dx_um,
            n_steps=cfg.n_steps_fdtd,
            wavelength_um=cfg.wavelength_um,
            nx=nx, ny=ny, nz=nz, pml_layers=pml_layers,
        )
        t_fdtd = float(result["T_fdtd"])
        r_fdtd = float(np.sqrt(max(1.0 - t_fdtd * t_fdtd, 0.0)))
        s_mat = np.array([[r_fdtd, t_fdtd], [t_fdtd, r_fdtd]], dtype=complex)
        return DeviceSolverResult(
            s_matrix=s_mat,
            modes=[],
            field_profile=None,
            solver_used="fdtd",
            metadata={
                "transmission_db": float(result["transmission_db"]),
                "T_fdtd": t_fdtd,
                "fdtd_duration_s": float(result["fdtd_duration_s"]),
                "n_steps": int(result["n_steps"]),
                "pml_enabled": bool(result["pml_enabled"]),
            },
        )


def solve_device(
    geometry: dict, wavelength_um: float = 1.55, method: str = "auto",
) -> DeviceSolverResult:
    """便捷入口: 求解器件，自动或显式选择求解器。

    Args:
        geometry: 器件几何描述 dict（见模块 docstring schema）。
        wavelength_um: 真空波长（μm）。
        method: 求解方法（auto/eme/fde/rcwa/varfdtd/bpm/fdtd）。

    Returns:
        DeviceSolverResult。

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。

    来源:
        - Lumerical 求解器选择指南
        - Bienstman 2001 / Smit 1996 / Yee 1966 / Chang 1980 / Moharam 1995
    """
    config = DeviceSolverConfig(method=method, wavelength_um=wavelength_um)
    solver = DeviceLevelSolver(config)
    return solver.solve(geometry)
