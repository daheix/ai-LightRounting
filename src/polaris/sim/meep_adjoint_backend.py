"""MEEP Adjoint 后端集成（第34轮 P2-1 深化，第51轮删除 fall-back）。

实现 MEEP adjoint method 后端，对标 lumopt 的 MEEP 集成。
MEEP 不可时直接报错退出（不降级，不 fall-back）。
若需解析模型，请直接使用 AnalyticalWaveguideCoupler（独立接口，非 fall-back）。

## MEEP Adjoint Method 原理

1. **正向仿真**：注入光源 → 计算 FoM = ∫ |E|² * monitor(x) dx
2. **伴随仿真**：注入伴随场 λ(x) = dFoM/dE* → 计算 dFoM/dε
3. **梯度计算**：dFoM/dθ = Re[∫ E_forward * E_adjoint * dε/dθ dx]
4. **参数更新**：Adam/L-BFGS 优化

## 商业差距

P2-1 逆向设计深化：
- 商业标杆：lumopt（MEEP adjoint 开源）/ Tidy3D adjoint（商业云）
- 本模块实现 MEEP adjoint 后端接口，对标 lumopt 核心能力

## 来源

- MEEP adjoint tutorial: https://meep.readthedocs.io/en/latest/Python_Tutorials/Adjoint/
- lumopt: https://github.com/chriskeraly/lumopt
- Jensen & Fan 2021 "Adjoint optimization of photonics devices"
  https://www.nature.com/articles/s41377-021-00679-4
- MEEP: https://meep.readthedocs.io/
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import numpy as np

from polaris.sim.adjoint_optimizer import (
    AdjointConfig,
    OptimizationBackend,
    OptimizationResult,
    ParameterizedGeometry,
    run_adjoint_optimization,
)


class MeepAvailability(Enum):
    """MEEP 可用性状态。

    Attributes:
        AVAILABLE: MEEP 已安装，可用真实 FDTD 仿真。
        UNKNOWN: 未检测。
    """

    AVAILABLE = "available"
    UNKNOWN = "unknown"


def check_meep_availability() -> MeepAvailability:
    """检测 MEEP 是否可用。

    Returns:
        MEEP 可用性状态。
    """
    try:
        import meep  # type: ignore[import-not-found]  # noqa: F401

        return MeepAvailability.AVAILABLE
    except ImportError:
        return MeepAvailability.UNKNOWN


@dataclass
class MeepSimulationConfig:
    """MEEP 仿真配置。

    Attributes:
        resolution: 空间分辨率（像素/μm）。
            来源: MEEP 默认 10-50，lumopt 推荐 20-30。
        cell_size_um: 仿真区域大小 (sx, sy) μm。
        pml_thickness_um: PML 边界厚度 μm。
            来源: MEEP 默认 1.0μm。
        wavelength_um: 中心波长 μm。
            来源: 光通信波段 1.55μm。
        wavelength_width_um: 波长带宽 μm（用于宽带仿真）。
        runtime_um: 仿真运行时间 μm（光程时间）。
        source_type: 光源类型（"gaussian"/"continuous"）。
        monitor_type: 监视器类型（"flux"/"field"）。
    """

    resolution: float = 20.0
    cell_size_um: tuple[float, float] = (10.0, 5.0)
    pml_thickness_um: float = 1.0
    wavelength_um: float = 1.55
    wavelength_width_um: float = 0.1
    runtime_um: float = 50.0
    source_type: str = "gaussian"
    monitor_type: str = "flux"


@dataclass
class MeepAdjointResult:
    """MEEP adjoint 单次仿真结果。

    Attributes:
        fom: 目标函数值。
        forward_field: 正向场分布（2D 复数数组）。
        adjoint_field: 伴随场分布（2D 复数数组）。
        gradient: 梯度数组。
        sim_time_s: 仿真耗时（秒）。
        backend_used: 实际使用的后端。
    """

    fom: float
    forward_field: np.ndarray | None = None
    adjoint_field: np.ndarray | None = None
    gradient: np.ndarray = field(default_factory=lambda: np.array([]))
    sim_time_s: float = 0.0
    backend_used: OptimizationBackend = OptimizationBackend.MEEP


class MeepAdjointBackend:
    """MEEP adjoint 后端（对标 lumopt MEEP 集成）。

    实现 ForwardSimulator 协议，提供：
    1. `compute_figure_of_merit(params)` → FoM
    2. `compute_gradient(params)` → 梯度（adjoint method）

    MEEP 不可用时直接 raise ImportError（不降级，不 fall-back）。
    若需解析模型，请直接使用 AnalyticalWaveguideCoupler 独立接口。

    来源:
    - MEEP adjoint: https://meep.readthedocs.io/en/latest/Python_Tutorials/Adjoint/
    - lumopt: https://github.com/chriskeraly/lumopt
    """

    def __init__(
        self,
        sim_config: MeepSimulationConfig | None = None,
    ) -> None:
        """初始化 MEEP adjoint 后端。

        Args:
            sim_config: MEEP 仿真配置（None 用默认）。

        Raises:
            ImportError: MEEP 未安装时直接报错（不降级）。
        """
        self.sim_config = sim_config or MeepSimulationConfig()
        self.availability = check_meep_availability()
        self._meep = None
        self._init_backend()

    def _init_backend(self) -> None:
        """初始化后端（MEEP 不可用时 raise ImportError）。"""
        if self.availability == MeepAvailability.AVAILABLE:
            try:
                import meep  # type: ignore[import-not-found]

                self._meep = meep
            except ImportError as e:
                raise ImportError(
                    "MEEP 后端不可用：未安装 meep。"
                    "安装方式: conda install -c conda-forge meep"
                    "（MEEP 仅支持 Python 3.10-3.13，不支持 Python 3.14）。"
                    "来源: https://meep.readthedocs.io/en/latest/Installation/"
                    "若需解析模型，请直接使用 AnalyticalWaveguideCoupler。"
                ) from e
        else:
            raise ImportError(
                "MEEP 后端不可用：未安装 meep。"
                "安装方式: conda install -c conda-forge meep"
                "（MEEP 仅支持 Python 3.10-3.13，不支持 Python 3.14）。"
                "来源: https://meep.readthedocs.io/en/latest/Installation/"
                "若需解析模型，请直接使用 AnalyticalWaveguideCoupler。"
            )

    @property
    def backend_used(self) -> OptimizationBackend:
        """实际使用的后端。"""
        return OptimizationBackend.MEEP

    def compute_figure_of_merit(self, params: np.ndarray) -> float:
        """计算目标函数值。

        运行 MEEP FDTD 正向仿真，计算 monitor 处的 FoM。

        Args:
            params: 设计参数。

        Returns:
            FoM 值。
        """
        return self._meep_forward_fom(params)

    def compute_gradient(self, params: np.ndarray) -> np.ndarray:
        """计算梯度（adjoint method）。

        1. 正向仿真获取 E_forward
        2. 伴随仿真获取 E_adjoint
        3. 梯度 = Re[E_forward * E_adjoint * dε/dθ]

        Args:
            params: 设计参数。

        Returns:
            梯度数组。
        """
        return self._meep_adjoint_gradient(params)

    def _meep_forward_fom(self, params: np.ndarray) -> float:
        """MEEP 正向仿真计算 FoM（真实 FDTD）。

        流程:
        1. 创建仿真区域（cell + PML）
        2. 根据参数构建器件几何（permittivity 分布）
        3. 添加光源（高斯源）
        4. 运行 FDTD 仿真
        5. 在 monitor 处计算 FoM（通量/场强）

        Args:
            params: 设计参数。

        Returns:
            FoM 值。
        """
        meep = self._meep
        cfg = self.sim_config
        cell = meep.Vector3(*cfg.cell_size_um)
        pml_layers = meep.PML(cfg.pml_thickness_um)
        sources = self._build_meep_sources(meep, cfg)
        geometry = self._build_meep_geometry(meep, params, cfg)
        sim = meep.Simulation(
            cell_size=cell,
            boundary_layers=[pml_layers],
            geometry=geometry,
            sources=sources,
            resolution=cfg.resolution,
        )
        sim.run(until=cfg.runtime_um)
        return self._compute_meep_fom(sim, meep, cfg)

    def _meep_adjoint_gradient(self, params: np.ndarray) -> np.ndarray:
        """MEEP 伴随仿真计算梯度。

        流程:
        1. 正向仿真获取 E_forward(x, y)
        2. 伴随仿真（注入伴随场）获取 E_adjoint(x, y)
        3. 对每个参数 θ_i:
           dF/dθ_i = Re[∫ E_forward * E_adjoint * dε/dθ_i dx]

        Args:
            params: 设计参数。

        Returns:
            梯度数组。
        """
        meep = self._meep
        cfg = self.sim_config
        forward_field = self._get_meep_field(meep, params, cfg, adjoint=False)
        adjoint_field = self._get_meep_field(meep, params, cfg, adjoint=True)
        gradient = np.zeros(len(params))
        for i in range(len(params)):
            deps_dtheta = self._compute_deps_dtheta(params, i, cfg)
            gradient[i] = float(
                np.real(np.sum(forward_field * adjoint_field * deps_dtheta))
            )
        return gradient

    def _build_meep_sources(self, meep, cfg: MeepSimulationConfig) -> list:
        """构建 MEEP 光源列表。"""
        src_x = -cfg.cell_size_um[0] / 2 + cfg.pml_thickness_um
        src_pt = meep.Vector3(src_x, 0)
        if cfg.source_type == "gaussian":
            source = meep.Source(
                src=meep.GaussianSource(
                    wavelength=cfg.wavelength_um,
                    width=cfg.wavelength_width_um,
                ),
                center=src_pt,
                size=meep.Vector3(0, cfg.cell_size_um[1]),
                component=meep.Ez,
            )
        else:
            source = meep.Source(
                src=meep.ContinuousSource(wavelength=cfg.wavelength_um),
                center=src_pt,
                size=meep.Vector3(0, cfg.cell_size_um[1]),
                component=meep.Ez,
            )
        return [source]

    def _build_meep_geometry(self, meep, params, cfg: MeepSimulationConfig) -> list:
        """根据参数构建 MEEP 几何（permittivity 分布）。

        简化模型：将参数映射为矩形波导几何。
        实际应用中可支持任意参数化（多边形/贝塞尔/水平集）。

        来源:
        - 硅介电常数 ε=12.0: n_Si=3.48 @ 1.55μm, ε=n²≈12.1
          Saleh & Teich, "Fundamentals of Photonics", Table 7.1
        - 波导高度 0.5μm: 简化模型默认值（SOI 典型 220nm，此处放宽用于仿真稳定性）
        """
        n_params = len(params)
        geometry = []
        # 默认波导宽度 0.5μm（参数不足时的默认值，非功能降级）
        DEFAULT_WG_WIDTH_UM = 0.5
        # 波导高度 0.5μm（简化模型，SOI 典型 220nm）
        WAVEGUIDE_HEIGHT_UM = 0.5
        # 硅介电常数 ε=12.0（n_Si=3.48, ε=n²≈12.1, Saleh & Teich Table 7.1）
        SILICON_PERMITTIVITY = 12.0
        for i in range(n_params // 2):
            x_center = float(params[2 * i])
            if 2 * i + 1 < n_params:
                width = float(params[2 * i + 1])
            else:
                width = DEFAULT_WG_WIDTH_UM
            geometry.append(
                meep.Block(
                    size=meep.Vector3(width, WAVEGUIDE_HEIGHT_UM),
                    center=meep.Vector3(x_center, 0),
                    material=meep.Medium(epsilon=SILICON_PERMITTIVITY),
                )
            )
        return geometry

    def _compute_meep_fom(self, sim, meep, cfg: MeepSimulationConfig) -> float:
        """从 MEEP 仿真结果计算 FoM（monitor 通量）。"""
        monitor_x = cfg.cell_size_um[0] / 2 - cfg.pml_thickness_um
        monitor_pt = meep.Vector3(monitor_x, 0)
        if cfg.monitor_type == "flux":
            flux = sim.get_fluxes(
                meep.FluxRegion(
                    center=monitor_pt,
                    size=meep.Vector3(0, cfg.cell_size_um[1]),
                )
            )
            return float(np.sum(flux)) if flux else 0.0
        field = sim.get_array(
            center=monitor_pt,
            size=meep.Vector3(0, cfg.cell_size_um[1]),
            component=meep.Ez,
        )
        return float(np.sum(np.abs(field) ** 2))

    def _get_meep_field(
        self,
        meep,
        params: np.ndarray,
        cfg: MeepSimulationConfig,
        adjoint: bool,
    ) -> np.ndarray:
        """获取 MEEP 场分布（正向或伴随）。

        Args:
            meep: MEEP 模块。
            params: 设计参数。
            cfg: 仿真配置。
            adjoint: True=伴随场，False=正向场。

        Returns:
            2D 复数场分布数组。
        """
        cell = meep.Vector3(*cfg.cell_size_um)
        pml_layers = meep.PML(cfg.pml_thickness_um)
        sources = self._build_meep_sources(meep, cfg)
        if adjoint:
            sources = self._build_adjoint_sources(meep, cfg)
        geometry = self._build_meep_geometry(meep, params, cfg)
        sim = meep.Simulation(
            cell_size=cell,
            boundary_layers=[pml_layers],
            geometry=geometry,
            sources=sources,
            resolution=cfg.resolution,
        )
        sim.run(until=cfg.runtime_um)
        return self._extract_field(sim, meep, cfg)

    def _build_adjoint_sources(self, meep, cfg: MeepSimulationConfig) -> list:
        """构建伴随光源（从 monitor 位置反向注入）。"""
        adj_x = cfg.cell_size_um[0] / 2 - cfg.pml_thickness_um
        adj_pt = meep.Vector3(adj_x, 0)
        source = meep.Source(
            src=meep.GaussianSource(
                wavelength=cfg.wavelength_um,
                width=cfg.wavelength_width_um,
            ),
            center=adj_pt,
            size=meep.Vector3(0, cfg.cell_size_um[1]),
            component=meep.Ez,
        )
        return [source]

    def _extract_field(self, sim, meep, cfg: MeepSimulationConfig) -> np.ndarray:
        """从仿真结果提取 2D 场分布。"""
        field = sim.get_array(
            center=meep.Vector3(),
            size=meep.Vector3(*cfg.cell_size_um),
            component=meep.Ez,
        )
        return np.asarray(field, dtype=np.complex128)

    def _compute_deps_dtheta(
        self,
        params: np.ndarray,
        param_idx: int,
        cfg: MeepSimulationConfig,
    ) -> np.ndarray:
        """计算 dε/dθ_i（permittivity 对参数的导数）。

        使用有限差分近似：dε/dθ ≈ [ε(θ+δ) - ε(θ-δ)] / (2δ)

        Args:
            params: 当前参数。
            param_idx: 参数索引。
            cfg: 仿真配置。

        Returns:
            dε/dθ_i 的 2D 分布。
        """
        # 有限差分步长 1e-4（lumopt 默认 1e-4~1e-3，平衡精度与数值稳定性）
        # 来源: lumopt 文档 https://lumopt.readthedocs.io/
        delta = 1e-4
        eps_plus = self._compute_permittivity(params, param_idx, +delta, cfg)
        eps_minus = self._compute_permittivity(params, param_idx, -delta, cfg)
        return (eps_plus - eps_minus) / (2 * delta)

    def _compute_permittivity(
        self,
        params: np.ndarray,
        param_idx: int,
        delta: float,
        cfg: MeepSimulationConfig,
    ) -> np.ndarray:
        """计算扰动后的 permittivity 分布。

        来源:
        - 硅介电常数 ε=12.0: n_Si=3.48, ε=n²≈12.1
          Saleh & Teich, "Fundamentals of Photonics", Table 7.1
        - 波导半高 0.25μm: 简化模型（SOI 典型 220nm 半高 110nm）
        """
        perturbed = params.copy()
        perturbed[param_idx] += delta
        nx = int(cfg.cell_size_um[0] * cfg.resolution)
        ny = int(cfg.cell_size_um[1] * cfg.resolution)
        # 背景介电常数 1.0（空气/真空）
        eps = np.ones((nx, ny))
        # 硅介电常数 12.0（n_Si=3.48, ε=n²≈12.1, Saleh & Teich Table 7.1）
        SILICON_PERMITTIVITY = 12.0
        # 波导半高 0.25μm（简化模型，SOI 典型 220nm 半高 110nm）
        WAVEGUIDE_HALF_HEIGHT_UM = 0.25
        # 默认波导宽度 0.5μm
        DEFAULT_WG_WIDTH_UM = 0.5
        n_params = len(perturbed)
        for i in range(n_params // 2):
            x_center = float(perturbed[2 * i])
            if 2 * i + 1 < n_params:
                width = float(perturbed[2 * i + 1])
            else:
                width = DEFAULT_WG_WIDTH_UM
            x_min = int((x_center - width / 2 + cfg.cell_size_um[0] / 2) * cfg.resolution)
            x_max = int((x_center + width / 2 + cfg.cell_size_um[0] / 2) * cfg.resolution)
            y_min = int((cfg.cell_size_um[1] / 2 - WAVEGUIDE_HALF_HEIGHT_UM) * cfg.resolution)
            y_max = int((cfg.cell_size_um[1] / 2 + WAVEGUIDE_HALF_HEIGHT_UM) * cfg.resolution)
            x_min = max(0, min(nx, x_min))
            x_max = max(0, min(nx, x_max))
            y_min = max(0, min(ny, y_min))
            y_max = max(0, min(ny, y_max))
            eps[x_min:x_max, y_min:y_max] = SILICON_PERMITTIVITY
        return eps


def create_meep_adjoint_backend(
    sim_config: MeepSimulationConfig | None = None,
) -> MeepAdjointBackend:
    """创建 MEEP adjoint 后端工厂函数。

    Args:
        sim_config: 仿真配置（None 用默认）。

    Returns:
        MeepAdjointBackend 实例。

    Raises:
        ImportError: MEEP 未安装时直接报错（不降级）。
    """
    return MeepAdjointBackend(sim_config=sim_config)


def run_meep_adjoint_optimization(
    geometry: ParameterizedGeometry,
    config: AdjointConfig | None = None,
    sim_config: MeepSimulationConfig | None = None,
) -> OptimizationResult:
    """便捷函数：使用 MEEP 后端执行 adjoint 优化。

    Args:
        geometry: 参数化几何。
        config: 优化配置（None 用默认）。
        sim_config: MEEP 仿真配置（None 用默认）。

    Returns:
        OptimizationResult。
    """
    backend = create_meep_adjoint_backend(sim_config=sim_config)
    if config is None:
        config = AdjointConfig(backend=backend.backend_used)
    else:
        config.backend = backend.backend_used
    return run_adjoint_optimization(geometry, backend, config)


def get_meep_status() -> dict[str, Any]:
    """获取 MEEP 状态信息。

    Returns:
        状态字典，含 availability、version、backend 等。
    """
    availability = check_meep_availability()
    status: dict[str, Any] = {
        "availability": availability.value,
        "backend": (
            OptimizationBackend.MEEP.value
            if availability == MeepAvailability.AVAILABLE
            else None
        ),
    }
    if availability == MeepAvailability.AVAILABLE:
        try:
            import meep  # type: ignore[import-not-found]

            status["version"] = getattr(meep, "__version__", "unknown")
        except (ImportError, AttributeError):
            status["version"] = "unknown"
    else:
        status["version"] = None
    return status


__all__ = [
    "MeepAdjointBackend",
    "MeepAdjointResult",
    "MeepAvailability",
    "MeepSimulationConfig",
    "check_meep_availability",
    "create_meep_adjoint_backend",
    "get_meep_status",
    "run_meep_adjoint_optimization",
]
