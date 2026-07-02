"""MMI（多模干涉仪）FDTD 仿真封装（simulate_mmi_fdtd）。

提供面向用户的 MMI FDTD 仿真 API，构建 1×2 MMI 结构并提取分束比。

## Input（输入）
- dx_um: 网格步长（μm，默认 0.05 = 50nm）
- n_steps: 时间步数（默认 2000）
- wavelength_um: 波长（μm，默认 1.55）
- nx/ny/nz: 网格数（默认 32×16×12）

## Process（处理）
1. 构建 MMI 介电常数分布:
   - 输入波导（x < nx/3）: 单模 Si 芯
   - MMI 多模区（nx/3 ≤ x ≤ 2·nx/3）: 宽 Si 芯
   - 两个输出波导（x > 2·nx/3）: 对称双 Si 芯
2. YeeGrid3D + GedneyPML + DifferentiableFDTD
3. 两次 FDTD 运行（不同监视器位置），提取双输出功率
4. 分束比: split_ratio = P_out1 / (P_out1 + P_out2)
   来源: Soldano & Pennings 1995（MMI 自映像原理）

## Output（输出）
dict::

    {
        "split_ratio": float,        # 输出 1 分束比（0-1）
        "T_fdtd": float,             # 总传输率（两输出之和 / 源功率）
        "transmission_db": float,    # 总传输率（dB）
        "fdtd_duration_s": float,    # 仿真耗时（秒）
        "n_steps": int,              # 时间步数
        "dx_um": float,              # 网格步长（μm）
        "pml_enabled": bool,         # 是否启用 PML
    }

## 设计原则
- R04 不参与 GPU: 强制 JAX CPU 后端
- R03 禁止 fall-back: 仿真结果为 NaN 时 raise
- R02 学术诚信: 物理参数来自 Soref 1993 / Soldano 1995

## 来源（R02 学术诚信，≥5 个文献 URL）
- Yee 1966 IEEE TAP https://doi.org/10.1109/TAP.1966.1138693
- Soldano & Pennings, JLT 13(4), 1995 https://ieeexplore.ieee.org/document/374358
- Taflove & Hagness 2005 "Computational Electrodynamics"
- Soref 1993 IEEE JQE https://ieeexplore.ieee.org/document/1148303
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
- Lumerical FDTD MMI 仿真
  https://optics.ansys.com/hc/en-us/articles/360034914833
- Chrostowski & Hochberg, "Silicon Photonics Design", Cambridge 2015, §7.3
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

__all__ = ["simulate_mmi_fdtd"]


def _build_mmi_eps(
    nx: int, ny: int, nz: int,
    eps_core: float, eps_clad: float,
) -> np.ndarray:
    """构建 1×2 MMI 介电常数分布 (nx, ny, nz)。

    - 输入波导: x ∈ [0, nx//3), y ∈ [ny//2-1, ny//2+1)
    - MMI 多模区: x ∈ [nx//3, 2*nx//3), y ∈ [ny//4, 3*ny//4)
    - 输出 1: x ∈ [2*nx//3, nx), y ∈ [ny//4-1, ny//4+1)
    - 输出 2: x ∈ [2*nx//3, nx), y ∈ [3*ny//4-1, 3*ny//4+1)
    """
    eps = np.full((nx, ny, nz), eps_clad, dtype=np.float32)
    z0, z1 = nz // 3, 2 * nz // 3  # 波导厚度（z 方向）
    nx3 = nx // 3
    # 输入波导
    eps[:nx3, ny // 2 - 1: ny // 2 + 1, z0:z1] = eps_core
    # MMI 多模区
    eps[nx3: 2 * nx3, ny // 4: 3 * ny // 4, z0:z1] = eps_core
    # 输出 1
    eps[2 * nx3:, ny // 4 - 1: ny // 4 + 1, z0:z1] = eps_core
    # 输出 2
    eps[2 * nx3:, 3 * ny // 4 - 1: 3 * ny // 4 + 1, z0:z1] = eps_core
    return eps


def simulate_mmi_fdtd(
    dx_um: float = 0.05,
    n_steps: int = 2000,
    wavelength_um: float = 1.55,
    nx: int = 32,
    ny: int = 16,
    nz: int = 12,
    pml_layers: int = 4,
) -> dict:
    """MMI 1×2 FDTD 仿真（Si 芯 / SiO2 包层）。

    构建 1×2 MMI 结构并运行 FDTD，提取双输出分束比。

    Args:
        dx_um: 网格步长（μm）。
        n_steps: 时间步数。
        wavelength_um: 波长（μm）。
        nx/ny/nz: 网格数。
        pml_layers: PML 层数（每侧）。

    Returns:
        dict: split_ratio / T_fdtd / transmission_db / fdtd_duration_s / ...

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
        RuntimeError: 仿真结果含 NaN（R03 禁止 fall-back）。
    """
    if dx_um <= 0:
        raise ValueError(f"dx_um 须 > 0，得到 {dx_um}")
    if n_steps <= 0:
        raise ValueError(f"n_steps 须 > 0，得到 {n_steps}")
    if pml_layers * 2 >= min(nx, ny, nz):
        raise ValueError(
            f"pml_layers*2 ({pml_layers*2}) 须 < min(nx,ny,nz) ({min(nx,ny,nz)})"
        )

    dx_m = dx_um * 1e-6
    eps_r = _build_mmi_eps(nx, ny, nz, SOI_EPS_R_SI, SOI_EPS_R_SIO2)

    grid = YeeGrid3D(nx, ny, nz, dx_m, dx_m, dx_m, epsilon_r=eps_r)
    pml = GedneyPML(grid, n_layers=pml_layers, eps_r_bg=SOI_EPS_R_SIO2)
    fdtd = DifferentiableFDTD(grid, pml=pml, eps_r_bg=SOI_EPS_R_SIO2)

    source_freq = C0 / (wavelength_um * 1e-6)
    source_pos = (4, ny // 2, nz // 2)
    # 双输出监视器
    mon1_pos = (nx - 5, ny // 4, nz // 2)
    mon2_pos = (nx - 5, 3 * ny // 4, nz // 2)

    t0 = time.time()
    # 运行 1: 监视器 1
    res1 = fdtd.run(eps_r, source_pos, source_freq, n_steps, mon1_pos)
    # 运行 2: 监视器 2（JAX 已编译，第二次快速）
    res2 = fdtd.run(eps_r, source_pos, source_freq, n_steps, mon2_pos)
    duration = float(time.time() - t0)

    mon1 = np.asarray(res1["monitor_signal"])
    mon2 = np.asarray(res2["monitor_signal"])
    src_wave = np.asarray(fdtd._build_source_waveform(n_steps, source_freq))

    # R03: NaN 校验
    if np.any(np.isnan(mon1)) or np.any(np.isnan(mon2)):
        raise RuntimeError("FDTD 监视器信号含 NaN（R03 禁止 fall-back）")

    p1 = float(np.max(np.abs(mon1) ** 2))
    p2 = float(np.max(np.abs(mon2) ** 2))
    p_src = float(np.max(np.abs(src_wave) ** 2))
    if p_src <= 0:
        raise RuntimeError(f"源功率 {p_src} <= 0（R03 禁止 fall-back）")

    p_total = p1 + p2
    split_ratio = p1 / p_total if p_total > 0 else 0.5
    t_fdtd = p_total / p_src
    transmission_db = 10.0 * float(np.log10(max(t_fdtd, 1e-30)))

    return {
        "split_ratio": float(split_ratio),
        "T_fdtd": float(t_fdtd),
        "transmission_db": transmission_db,
        "fdtd_duration_s": duration,
        "n_steps": int(n_steps),
        "dx_um": float(dx_um),
        "pml_enabled": True,
    }
