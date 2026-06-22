"""MEEP FDTD 仿真后端（从 fdtd_simulator.py 拆分，第69轮 P0-4 修复）。

真正调用 MEEP Python API 构建器件几何、设置光源、运行 FDTD 仿真、
通过通量 monitor 提取 S 参数。MEEP 不可用时由 fdtd_simulator._select_fdtd_backend
抛出 ImportError，本模块不 fall-back。

## 合规性

- project_rules.md 规则 2: 直接集成开源工具，不复刻
- project_rules.md 规则 3.2: 无兜底，后端不可用时明确报错
- project_rules.md 规则 11.2: 标注 FDTD API 文档来源
- 差距分析 P0-4: docs/commercial_gap_analysis.md

来源:
- MEEP: https://meep.readthedocs.io/
- MEEP Basics: https://meep.readthedocs.io/en/latest/Python_Tutorials/Basics/
- MEEP S 参数: https://meep.readthedocs.io/en/latest/Python_Tutorials/Guided_Modes/
- MEEP Transmission Spectrum: https://meep.readthedocs.io/en/latest/Python_Tutorials/Basics/#transmission-spectrum-around-a-waveguide-bend
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import numpy as np

from polaris.sim.fdtd_simulator import FDTDBackend, FDTDConfig, FDTDResult

if TYPE_CHECKING:
    from polaris.pdk.device import Device


def _build_meep_geometry(device: Device, meep) -> list:
    """根据 Device 几何构建 MEEP 几何对象列表。

    Args:
        device: PoLaRIS 器件。
        meep: meep 模块。

    Returns:
        MEEP Block 几何对象列表。

    来源:
    - MEEP Block: https://meep.readthedocs.io/en/latest/Python_User_Interface/#block
    - 硅介电常数 ε=12.0: n_Si=3.48 @ 1.55μm, ε=n²≈12.1
      (Saleh & Teich, "Fundamentals of Photonics", Table 7.1)
    """
    bbox = device.bbox
    center_x = float((bbox.xmin + bbox.xmax) / 2)
    center_y = float((bbox.ymin + bbox.ymax) / 2)
    size_x = float(bbox.xmax - bbox.xmin)
    size_y = float(bbox.ymax - bbox.ymin)
    # 硅波导 Block（2D 仿真，z 方向无限）
    return [
        meep.Block(
            center=meep.Vector3(center_x, center_y),
            size=meep.Vector3(size_x, size_y, 0),
            material=meep.Medium(epsilon=12.0),
        )
    ]


def _build_meep_sources(device: Device, meep, config: FDTDConfig) -> list:
    """构建 MEEP 光源列表。

    在输入端口处放置高斯面光源，激励波导模式。

    Args:
        device: PoLaRIS 器件。
        meep: meep 模块。
        config: FDTD 配置。

    Returns:
        MEEP Source 对象列表。

    来源:
    - MEEP Source: https://meep.readthedocs.io/en/latest/Python_User_Interface/#source
    - MEEP GaussianSource: https://meep.readthedocs.io/en/latest/Python_User_Interface/#gaussiansource
    """
    if not device.ports:
        return []
    in_port = device.ports[0]
    wl_center = (config.wavelength_start_um + config.wavelength_end_um) / 2
    wl_width = (config.wavelength_end_um - config.wavelength_start_um) / 2 or 0.1 * wl_center
    source = meep.Source(
        src=meep.GaussianSource(wavelength=wl_center, width=wl_width),
        center=meep.Vector3(float(in_port.x), float(in_port.y)),
        size=meep.Vector3(0, float(in_port.width if hasattr(in_port, "width") else 2.0)),
        component=meep.Ez,
    )
    return [source]


def _build_meep_flux_monitors(device: Device, meep, config: FDTDConfig) -> tuple:
    """构建 MEEP 通量 monitor（输入/输出端口处）。

    Args:
        device: PoLaRIS 器件。
        meep: meep 模块。
        config: FDTD 配置。

    Returns:
        (monitors, wl_center, wl_width) 三元组。

    来源:
    - MEEP Flux Spectrum: https://meep.readthedocs.io/en/latest/Python_Tutorials/Basics/#transmission-spectrum-around-a-waveguide-bend
    """
    monitors: dict[str, object] = {}
    wl_center = (config.wavelength_start_um + config.wavelength_end_um) / 2
    wl_width = (config.wavelength_end_um - config.wavelength_start_um) / 2 or 0.1 * wl_center
    for port in device.ports:
        # 每个端口放置一个通量 monitor
        monitors[port.name] = meep.FluxRegion(
            center=meep.Vector3(float(port.x), float(port.y)),
            size=meep.Vector3(0, float(port.width if hasattr(port, "width") else 2.0)),
            direction=meep.X if port.x != 0 else meep.Y,
        )
    return monitors, wl_center, wl_width


def _extract_meep_sparams(
    sim,
    device: Device,
    flux_objects: dict,
) -> tuple[dict, dict]:
    """从 MEEP 仿真结果提取 S 参数（通过通量 monitor）。

    S21 = sqrt(flux_out / flux_in)（振幅传输比）

    Args:
        sim: MEEP Simulation 对象（已运行）。
        device: PoLaRIS 器件。
        flux_objects: 端口名 → flux 对象字典。

    Returns:
        (s_params, transmission_db) 二元组。

    来源:
    - https://meep.readthedocs.io/en/latest/Python_Tutorials/Basics/#transmission-spectrum-around-a-waveguide-bend
    - Pozar, "Microwave Engineering", 4th ed., Eq. (4.6)
    """
    s_params: dict[tuple[str, str], np.ndarray] = {}
    transmission_db: dict[tuple[str, str], float] = {}

    if device.ports and len(device.ports) >= 2:
        in_port = device.ports[0]
        out_port = device.ports[-1]
        flux_in = sim.get_flux_data(flux_objects[in_port.name])
        flux_out = sim.get_flux_data(flux_objects[out_port.name])
        # S21 = sqrt(flux_out / flux_in)（振幅传输比）
        # 避免除零
        s21_amplitude = np.sqrt(
            np.maximum(flux_out / (flux_in + 1e-30), 0.0)
        ).astype(complex)
        s_params[(in_port.name, out_port.name)] = s21_amplitude
        # 传输谱（dB）= 10·log10(|S21|²) = 20·log10(|S21|)
        # 来源: Pozar, "Microwave Engineering", 4th ed., Eq. (4.6)
        t_db = 20 * np.log10(np.abs(s21_amplitude) + 1e-12)
        transmission_db[(in_port.name, out_port.name)] = float(np.mean(t_db))

    return s_params, transmission_db


def _build_meep_simulation(device: Device, config: FDTDConfig, meep) -> tuple:
    """构建 MEEP Simulation 对象并添加通量 monitor。

    Args:
        device: PoLaRIS 器件。
        config: FDTD 配置。
        meep: meep 模块。

    Returns:
        (sim, flux_objects, wavelengths) 三元组。

    来源:
    - MEEP Simulation: https://meep.readthedocs.io/en/latest/Python_User_Interface/#simulation
    """
    wavelengths = np.linspace(
        config.wavelength_start_um,
        config.wavelength_end_um,
        config.n_wavelengths,
    )
    bbox = device.bbox
    cell_size = meep.Vector3(
        float(bbox.xmax - bbox.xmin) + 2 * config.pml_thickness_um,
        float(bbox.ymax - bbox.ymin) + 2 * config.pml_thickness_um,
    )
    pml_layers = meep.PML(config.pml_thickness_um)
    geometry = _build_meep_geometry(device, meep)
    sources = _build_meep_sources(device, meep, config)
    resolution = int(1.0 / config.grid_resolution_um)

    sim = meep.Simulation(
        cell_size=cell_size,
        boundary_layers=[pml_layers],
        geometry=geometry,
        sources=sources,
        resolution=resolution,
    )

    # 添加通量 monitor（输入/输出端口）
    monitors, wl_center, wl_width = _build_meep_flux_monitors(device, meep, config)
    flux_objects: dict[str, object] = {}
    for name, region in monitors.items():
        flux_objects[name] = sim.add_flux(
            wl_center, wl_width, config.n_wavelengths, region
        )
    return sim, flux_objects, wavelengths


def run_meep_simulation(device: Device, config: FDTDConfig) -> FDTDResult:
    """MEEP FDTD 仿真后端（真正调用 MEEP API）。

    使用 MEEP 的 Python API 构建器件几何、设置光源、运行 FDTD 仿真、
    通过通量 monitor 提取 S 参数。

    MEEP 不可用时由 _select_fdtd_backend 抛出 ImportError，本函数不 fall-back。
    若需解析 S 参数（非 FDTD），请使用 ANALYTICAL 后端。

    来源:
    - MEEP Basics: https://meep.readthedocs.io/en/latest/Python_Tutorials/Basics/
    - MEEP S 参数: https://meep.readthedocs.io/en/latest/Python_Tutorials/Guided_Modes/
    - MEEP Transmission Spectrum: https://meep.readthedocs.io/en/latest/Python_Tutorials/Basics/#transmission-spectrum-around-a-waveguide-bend
    """
    import meep

    sim, flux_objects, wavelengths = _build_meep_simulation(device, config, meep)

    # 运行 FDTD 仿真
    # 来源: https://meep.readthedocs.io/en/latest/Python_User_Interface/#simulation-run
    t_start = time.time()
    sim.run(until_after_sources=meep.stop_when_fields_decayed(
        dt=50, c=meep.Ez, pt=meep.Vector3(), decay_by=1e-6
    ))
    sim_time = time.time() - t_start

    # 从通量 monitor 提取 S 参数
    s_params, transmission_db = _extract_meep_sparams(sim, device, flux_objects)

    # 中心波长插入损耗（从仿真结果提取）
    il_db = float(
        transmission_db.get(
            (device.ports[0].name, device.ports[-1].name), 0.0
        )
    ) if device.ports and len(device.ports) >= 2 else 0.0

    return FDTDResult(
        wavelengths_um=wavelengths,
        s_params=s_params,
        transmission_db=transmission_db,
        insertion_loss_db=il_db,
        backend_used=FDTDBackend.MEEP,
        simulation_time_s=sim_time,
    )


__all__ = [
    "run_meep_simulation",
]
