"""Tidy3D 云端 FDTD 仿真后端（从 fdtd_simulator.py 拆分，第69轮 P0-4 修复）。

使用 Tidy3D 的 Python API 构建仿真任务并提交到 Flexcompute 云端求解，
通过 ModeMonitor 提取 S 参数。需要 TIDY3D_API_KEY 环境变量，
无 key 时明确报错（不 fall-back）。

## 合规性

- project_rules.md 规则 2: 直接集成商业工具，不复刻
- project_rules.md 规则 3.2: 无兜底，后端不可用时明确报错
- project_rules.md 规则 11.2: 标注 FDTD API 文档来源
- 差距分析 P0-4: docs/commercial_gap_analysis.md

来源:
- Tidy3D: https://www.flexcompute.com/tidy3d/
- Tidy3D 快速入门: https://docs.flexcompute.com/projects/tidy3d/en/latest/notebooks/GettingStarted.html
- Tidy3D S 参数: https://docs.flexcompute.com/projects/tidy3d/en/latest/notebooks/SParameters.html
- Tidy3D Web API: https://docs.flexcompute.com/projects/tidy3d/en/latest/api/web.html
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

import numpy as np

from polaris.sim.fdtd_simulator import FDTDBackend, FDTDConfig, FDTDResult

if TYPE_CHECKING:
    from polaris.pdk.device import Device

logger = logging.getLogger(__name__)


def _build_tidy3d_source(td, config: FDTDConfig):
    """构建 Tidy3D 点偶极子光源。

    Args:
        td: tidy3d 模块。
        config: FDTD 配置。

    Returns:
        Tidy3D PointDipole 光源对象。
    """
    wl_center = (config.wavelength_start_um + config.wavelength_end_um) / 2
    f_center = td.C_0 / wl_center
    fwidth = 0.1 * f_center
    return td.PointDipole(
        center=(0, 0, 0),
        source_time=td.GaussianPulse(freq0=f_center, fwidth=fwidth),
        polarization="Ez",
    )


def _build_tidy3d_monitors(device: Device, td, wavelengths: np.ndarray) -> list:
    """构建 Tidy3D ModeMonitor 列表用于 S 参数提取。

    在每个端口处放置模式 monitor，记录正向传播的模式振幅。

    Args:
        device: PoLaRIS 器件。
        td: tidy3d 模块。
        wavelengths: 波长数组（μm）。

    Returns:
        Tidy3D ModeMonitor 对象列表。

    来源:
    - Tidy3D ModeMonitor: https://docs.flexcompute.com/projects/tidy3d/en/latest/api/_autosummary/tidy3d.ModeMonitor.html
    """
    monitors: list = []
    if not device.ports:
        return monitors
    freqs = td.C_0 / wavelengths
    for i, port in enumerate(device.ports):
        monitor = td.ModeMonitor(
            center=(float(port.x), float(port.y), 0),
            size=(0, float(port.width if hasattr(port, "width") else 2.0), 0),
            freqs=freqs,
            mode_spec=td.ModeSpec(num_modes=1),
            name=f"port_{i}_{port.name}",
        )
        monitors.append(monitor)
    return monitors


def _build_tidy3d_simulation(
    device: Device,
    config: FDTDConfig,
    td,
) -> tuple:
    """构建 Tidy3D 仿真对象（含 ModeMonitor 用于 S 参数提取）。

    Args:
        device: PoLaRIS 器件。
        config: FDTD 配置。
        td: tidy3d 模块。

    Returns:
        (sim, length_um, wavelengths) 三元组。

    来源:
    - Tidy3D Simulation: https://docs.flexcompute.com/projects/tidy3d/en/latest/api/_autosummary/tidy3d.Simulation.html
    - Tidy3D S 参数教程: https://docs.flexcompute.com/projects/tidy3d/en/latest/notebooks/SParameters.html
    """
    wavelengths = np.linspace(
        config.wavelength_start_um,
        config.wavelength_end_um,
        config.n_wavelengths,
    )
    bbox = device.bbox
    length_um = float(bbox.xmax - bbox.xmin)
    source = _build_tidy3d_source(td, config)
    sim_size = (
        float(bbox.xmax - bbox.xmin) + 2 * config.pml_thickness_um,
        float(bbox.ymax - bbox.ymin) + 2 * config.pml_thickness_um,
        1.0,
    )
    monitors = _build_tidy3d_monitors(device, td, wavelengths)

    sim = td.Simulation(
        size=sim_size,
        sources=[source],
        resolution=int(1.0 / config.grid_resolution_um),
        boundary_spec=td.BoundarySpec.all_sides(boundary=td.PML()),
        run_time=config.simulation_time_fs * 1e-15,
        monitors=monitors,
    )
    logger.info(
        "Tidy3D 仿真对象已构建: size=%s, resolution=%d, run_time=%s, monitors=%d",
        sim.size,
        sim.resolution,
        sim.run_time,
        len(monitors),
    )
    return sim, length_um, wavelengths


def _extract_tidy3d_sparams(
    device: Device,
    wavelengths: np.ndarray,
    length_um: float,
    sim_data,
    td,
) -> tuple[dict, dict]:
    """从 Tidy3D 仿真结果提取 S 参数（真正从 sim_data 提取）。

    通过 ModeMonitor 数据计算端口的模式振幅，然后计算 S 参数。
    S21 = mode_amplitude_out / mode_amplitude_in

    Args:
        device: PoLaRIS 器件。
        wavelengths: 波长数组。
        length_um: 波导长度（μm）。
        sim_data: Tidy3D 仿真结果（SimulationData 对象）。
        td: tidy3d 模块。

    Returns:
        (s_params, transmission_db) 二元组。

    来源:
    - Tidy3D SimulationData: https://docs.flexcompute.com/projects/tidy3d/en/latest/api/_autosummary/tidy3d.SimulationData.html
    - Tidy3D ModeMonitorData: https://docs.flexcompute.com/projects/tidy3d/en/latest/api/_autosummary/tidy3d.ModeMonitorData.html
    - S 参数提取方法: https://docs.flexcompute.com/projects/tidy3d/en/latest/notebooks/SParameters.html
    """
    s_params: dict[tuple[str, str], np.ndarray] = {}
    transmission_db: dict[tuple[str, str], float] = {}

    if not device.ports or len(device.ports) < 2:
        return s_params, transmission_db

    in_port = device.ports[0]
    out_port = device.ports[-1]

    # 从 ModeMonitor 提取模式振幅
    # sim_data[monitor_name].amps.sel(direction="+", mode_index=0)
    # 来源: https://docs.flexcompute.com/projects/tidy3d/en/latest/notebooks/SParameters.html
    in_monitor_name = f"port_0_{in_port.name}"
    out_monitor_name = f"port_{len(device.ports)-1}_{out_port.name}"

    try:
        in_amps = sim_data[in_monitor_name].amps.sel(direction="+", mode_index=0).values
        out_amps = sim_data[out_monitor_name].amps.sel(direction="+", mode_index=0).values
    except (KeyError, AttributeError) as e:
        raise RuntimeError(
            f"从 Tidy3D 仿真结果提取 S 参数失败: {e}。"
            f"monitor_names={in_monitor_name}, {out_monitor_name}。"
            f"可用 monitor: {list(sim_data.monitor_data.keys())}"
        ) from e

    # S21 = out_amps / in_amps（复数振幅比）
    # 避免除零
    s21 = out_amps / (in_amps + 1e-30)
    s_params[(in_port.name, out_port.name)] = s21

    # 传输谱（dB）= 20·log10(|S21|)
    # 来源: Pozar, "Microwave Engineering", 4th ed., Eq. (4.6)
    t_db = 20 * np.log10(np.abs(s21) + 1e-12)
    transmission_db[(in_port.name, out_port.name)] = float(np.mean(t_db))

    return s_params, transmission_db


def run_tidy3d_simulation(device: Device, config: FDTDConfig) -> FDTDResult:
    """Tidy3D 云端 FDTD 仿真后端（商业级）。

    使用 Tidy3D 的 Python API 构建仿真任务并提交到 Flexcompute 云端求解。
    需要 TIDY3D_API_KEY 环境变量，无 key 时明确报错（不 fall-back）。

    若需本地解析 S 参数（非 FDTD），请使用 ANALYTICAL 后端或
    直接调用 _compute_soi_waveguide_sparams 函数。

    来源:
    - Tidy3D 快速入门: https://docs.flexcompute.com/projects/tidy3d/en/latest/notebooks/GettingStarted.html
    - Tidy3D S 参数: https://docs.flexcompute.com/projects/tidy3d/en/latest/notebooks/SParameters.html
    - Tidy3D Web API: https://docs.flexcompute.com/projects/tidy3d/en/latest/api/web.html
    """
    import tidy3d as td

    api_key = os.environ.get("TIDY3D_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Tidy3D 云端求解需要 TIDY3D_API_KEY 环境变量。"
            "获取 API key: https://tidy3d.simulation.cloud/account"
            "若需本地解析 S 参数（非 FDTD），请使用 ANALYTICAL 后端。"
        )

    sim, length_um, wavelengths = _build_tidy3d_simulation(device, config, td)

    # 提交云端求解（真实 API 调用）
    # 来源: https://docs.flexcompute.com/projects/tidy3d/en/latest/api/web.html
    td.web.configure(api_key)
    sim_data = td.web.run(sim, task_name="polaris_fdtd")
    logger.info("Tidy3D 云端求解完成，task_id=%s", sim_data.task_id)

    # 从仿真结果提取 S 参数（真正从 sim_data 提取，非解析模型）
    s_params, transmission_db = _extract_tidy3d_sparams(
        device, wavelengths, length_um, sim_data, td
    )
    # 插入损耗从仿真结果提取，不使用解析模型估算
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
        backend_used=FDTDBackend.TIDY3D,
    )


__all__ = [
    "run_tidy3d_simulation",
]
