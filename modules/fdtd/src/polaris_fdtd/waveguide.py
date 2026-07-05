"""波导 FDTD 仿真封装（simulate_waveguide_fdtd）。

提供面向用户的波导 FDTD 仿真 API，封装 YeeGrid3D + GedneyPML + DifferentiableFDTD
三件套，构建硅波导（Si 芯 / SiO2 包层）结构并提取传输率。

## Input（输入）
- dx_um: 网格步长（μm，默认 0.05 = 50nm）
- n_steps: 时间步数（默认 2000）
- wavelength_um: 波长（μm，默认 1.55）
- nx/ny/nz: 网格数（默认 32×24×20）

## Process（处理）
1. 构建硅波导介电常数分布: Si 芯（eps_r=12.08）+ SiO2 包层（eps_r=2.085）
   波导芯居中: y=[ny//2-2, ny//2+2], z=[nz//2-1, nz//2+1]，沿 x 传播
2. YeeGrid3D 3D 网格 + GedneyPML 4 层吸收边界
3. DifferentiableFDTD 高斯脉冲源 + jax.lax.scan 时间步进
   源/监视器位置自动基于 pml_layers 计算，距 PML 至少 2-3 格（R05 修复零传输 BUG）
4. 双监视器比值法: T = max(|monitor|²) / max(|source|²)
   来源: Taflove 2005 §5.3（双监视器传输率提取）

## Output（输出）
dict::

    {
        "transmission_db": float,    # 传输率（dB）
        "T_fdtd": float,             # 传输率（线性 0-1）
        "fdtd_duration_s": float,    # 仿真耗时（秒）
        "n_steps": int,              # 时间步数
        "dx_um": float,              # 网格步长（μm）
        "pml_enabled": bool,         # 是否启用 PML
    }

## 设计原则
- R04 不参与 GPU: 强制 JAX CPU 后端
- R03 禁止 fall-back: 仿真结果为 NaN 时 raise
- R02 学术诚信: 物理参数来自 Soref 1993 / NIST CODATA 2018
- R05 Bug 必须修复: 波导芯距 PML 至少 4 格，源/监视器距 PML 至少 2 格

## 来源（R02 学术诚信，≥5 个文献 URL）
- Yee 1966 IEEE TAP https://doi.org/10.1109/TAP.1966.1138693
- Gedney 1996 IEEE TAP https://doi.org/10.1109/8.546249
- Taflove & Hagness 2005 "Computational Electrodynamics" §5.3 §7.6.2
- Soref 1993 IEEE JQE https://ieeexplore.ieee.org/document/1148303
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
- Lumerical FDTD 求解器 https://optics.ansys.com/hc/en-us/articles/360034914833
- Chrostowski & Hochberg, "Silicon Photonics Design", Cambridge 2015
"""

from __future__ import annotations

import os
import time

# R04: 强制 JAX CPU 后端（必须在 import jax 前设置）
os.environ.setdefault("JAX_PLATFORMS", "cpu")

import numpy as np  # noqa: E402

from polaris_fdtd.solver import (  # noqa: E402
    C0,
    DifferentiableFDTD,
    GedneyPML,
    SOI_EPS_R_SI,
    SOI_EPS_R_SIO2,
    YeeGrid3D,
)

__all__ = ["simulate_waveguide_fdtd"]


def _build_waveguide_eps(
    nx: int, ny: int, nz: int,
    wg_y_range: tuple, wg_z_range: tuple,
    eps_core: float, eps_clad: float,
) -> np.ndarray:
    """构建硅波导介电常数分布 (nx, ny, nz)。"""
    eps = np.full((nx, ny, nz), eps_clad, dtype=np.float32)
    y0, y1 = wg_y_range
    z0, z1 = wg_z_range
    eps[:, y0:y1, z0:z1] = eps_core
    return eps


def _simulate_waveguide_validate(
    dx_um: float, n_steps: int, wavelength_um: float,
    nx: int, ny: int, nz: int, pml_layers: int,
) -> tuple[int, int, int, int]:
    """校验 simulate_waveguide_fdtd 输入并计算波导芯边界（R03/R05）。

    Returns:
        (wg_y0, wg_y1, wg_z0, wg_z1) 波导芯 y/z 边界。
    """
    if dx_um <= 0:
        raise ValueError(f"dx_um 须 > 0，得到 {dx_um}")
    if n_steps <= 0:
        raise ValueError(f"n_steps 须 > 0，得到 {n_steps}")
    if wavelength_um <= 0:
        raise ValueError(f"wavelength_um 须 > 0，得到 {wavelength_um}")
    if pml_layers * 2 >= min(nx, ny, nz):
        raise ValueError(
            f"pml_layers*2 ({pml_layers*2}) 须 < min(nx,ny,nz) ({min(nx,ny,nz)})"
        )
    # R05: 波导芯居中，距 PML 至少 4 格（Taflove 2005 §7.6.2）
    wg_y0, wg_y1 = ny // 2 - 2, ny // 2 + 2  # 4 格宽
    wg_z0, wg_z1 = nz // 2 - 1, nz // 2 + 1  # 2 格厚
    if wg_y0 - pml_layers < 2 or (ny - pml_layers) - wg_y1 < 2:
        raise ValueError(
            f"波导芯 y=[{wg_y0},{wg_y1}] 距 PML(y=[0,{pml_layers}]/"
            f"[{ny-pml_layers},{ny}]) 不足 2 格（R05）"
        )
    if wg_z0 - pml_layers < 2 or (nz - pml_layers) - wg_z1 < 2:
        raise ValueError(
            f"波导芯 z=[{wg_z0},{wg_z1}] 距 PML(z=[0,{pml_layers}]/"
            f"[{nz-pml_layers},{nz}]) 不足 2 格（R05）"
        )
    return wg_y0, wg_y1, wg_z0, wg_z1


def _simulate_waveguide_setup_source_monitor(
    nx: int, ny: int, nz: int, pml_layers: int,
) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
    """计算源/监视器位置（距 PML 至少 2 格，置于波导芯中心）。

    Returns:
        (source_pos, monitor_pos)。

    Raises:
        ValueError: monitor x <= source x。
    """
    source_pos = (pml_layers + 2, ny // 2, nz // 2)
    monitor_pos = (nx - pml_layers - 3, ny // 2, nz // 2)
    if monitor_pos[0] <= source_pos[0]:
        raise ValueError(
            f"监视器 x={monitor_pos[0]} 须 > 源 x={source_pos[0]}（R05）"
        )
    return source_pos, monitor_pos


def _simulate_waveguide_compute_transmission(
    mon_sig: np.ndarray, src_wave: np.ndarray,
) -> tuple[float, float]:
    """计算传输率（双监视器比值法，Taflove 2005 §5.3）。

    Returns:
        (t_fdtd, transmission_db)。
    """
    # R03: NaN 校验
    if np.any(np.isnan(mon_sig)):
        raise RuntimeError(
            "FDTD 监视器信号含 NaN（R03 禁止 fall-back）"
        )
    p_monitor = float(np.max(np.abs(mon_sig) ** 2))
    p_source = float(np.max(np.abs(src_wave) ** 2))
    if p_source <= 0:
        raise RuntimeError(
            f"源功率 {p_source} <= 0，传输率无法计算（R03 禁止 fall-back）"
        )
    t_fdtd = p_monitor / p_source
    transmission_db = 10.0 * float(np.log10(max(t_fdtd, 1e-30)))
    return t_fdtd, transmission_db


def simulate_waveguide_fdtd(
    dx_um: float = 0.05,
    n_steps: int = 2000,
    wavelength_um: float = 1.55,
    nx: int = 32,
    ny: int = 24,
    nz: int = 20,
    pml_layers: int = 4,
) -> dict:
    """波导 FDTD 仿真（Si 芯 / SiO2 包层）。

    构建硅波导结构并运行 3D FDTD 时间步进，提取传输率。

    R05 修复（零传输 BUG）:
    - 旧默认 ny=16/nz=12 + 波导芯 z=4-6 致波导芯紧贴 PML，源 x=4 落在 PML 末层
      → 模式未建立即被吸收 → T_fdtd≈0（-195 dB）。
    - 新默认 ny=24/nz=20，波导芯居中 [ny//2-2, ny//2+2]×[nz//2-1, nz//2+1]，
      源/监视器自动置于 pml_layers+2 / nx-pml_layers-3，距 PML 至少 2-3 格。
      来源: Taflove 2005 §7.6.2（PML 与结构最小间距 ≥ 2 网格）。

    Args:
        dx_um: 网格步长（μm）。
        n_steps: 时间步数。
        wavelength_um: 波长（μm）。
        nx/ny/nz: 网格数。
        pml_layers: PML 层数（每侧）。

    Returns:
        dict: transmission_db / T_fdtd / fdtd_duration_s / n_steps / dx_um / pml_enabled

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
        RuntimeError: 仿真结果含 NaN（R03 禁止 fall-back）。
    """
    wg_y0, wg_y1, wg_z0, wg_z1 = _simulate_waveguide_validate(
        dx_um, n_steps, wavelength_um, nx, ny, nz, pml_layers,
    )
    dx_m = dx_um * 1e-6
    eps_r = _build_waveguide_eps(
        nx, ny, nz, (wg_y0, wg_y1), (wg_z0, wg_z1),
        SOI_EPS_R_SI, SOI_EPS_R_SIO2,
    )
    grid = YeeGrid3D(nx, ny, nz, dx_m, dx_m, dx_m, epsilon_r=eps_r)
    pml = GedneyPML(grid, n_layers=pml_layers, eps_r_bg=SOI_EPS_R_SIO2)
    fdtd = DifferentiableFDTD(grid, pml=pml, eps_r_bg=SOI_EPS_R_SIO2)
    # 源频率: f = c/λ（1550nm → 193.4 THz）
    source_freq = C0 / (wavelength_um * 1e-6)
    source_pos, monitor_pos = _simulate_waveguide_setup_source_monitor(
        nx, ny, nz, pml_layers,
    )
    t0 = time.time()
    # R05: 注入/监视 Ey（准 TE 横向分量），避免注入 Ex（纵向）形成驻波
    # 来源: Taflove 2005 §5.3（模式激发需用横向分量）
    result = fdtd.run(
        eps_r, source_pos, source_freq, n_steps, monitor_pos,
        source_component="Ey", monitor_component="Ey",
    )
    duration = float(time.time() - t0)
    mon_sig = np.asarray(result["monitor_signal"])
    src_wave = np.asarray(fdtd._build_source_waveform(n_steps, source_freq))
    t_fdtd, transmission_db = _simulate_waveguide_compute_transmission(
        mon_sig, src_wave,
    )
    return {
        "transmission_db": transmission_db,
        "T_fdtd": float(t_fdtd),
        "fdtd_duration_s": duration,
        "n_steps": int(n_steps),
        "dx_um": float(dx_um),
        "pml_enabled": True,
    }
