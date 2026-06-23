"""R2 调试 v6: 测试增大 NX 让源/监视器远离 x-PML，提升 FoM 信号强度。"""
from __future__ import annotations

import jax
import jax.numpy as jnp
import numpy as np

from polaris.sim.fdtd_jax_backend import (
    C0,
    DifferentiableFDTD,
    GedneyPML,
    YeeGrid3D,
)

EPS_R_SI = 3.476 ** 2


def run_test(name: str, nx, ny, nz, pml_layers, n_steps=600):
    dx = 0.2e-6
    grid = YeeGrid3D(nx=nx, ny=ny, nz=nz, dx=dx, dy=dx, dz=dx)
    grid.epsilon_r = jnp.full((nx, ny, nz), EPS_R_SI)
    cfl_dt = grid.cfl_timestep(EPS_R_SI)
    dt = 0.3 * float(cfl_dt)

    pml = GedneyPML(grid, n_layers=pml_layers, eps_r_bg=EPS_R_SI)
    fdtd = DifferentiableFDTD(grid, pml=pml, dt=dt, eps_r_bg=EPS_R_SI)

    # 波导 epsilon_r
    y_coords = jnp.arange(ny, dtype=jnp.float32)
    center = ny / 2.0
    soft_mask = jax.nn.sigmoid((2.0 - jnp.abs(y_coords - center)) / 0.5)
    delta = 0.50 * EPS_R_SI
    eps_r = EPS_R_SI + delta * soft_mask[None, :, None]
    eps_r = jnp.broadcast_to(eps_r, (nx, ny, nz))

    src_z = pml_layers + 1
    src_x = pml_layers + 4  # 距 PML 4 像素
    mon_x = nx - pml_layers - 4  # 距 PML 4 像素
    source_pos = (src_x, ny // 2, src_z)
    monitor_pos = (mon_x, ny // 2, src_z)
    source_freq = C0 / 1.55e-6

    result = fdtd.run(
        epsilon_r=eps_r, source_pos=source_pos, source_freq=source_freq,
        n_steps=n_steps, monitor_pos=monitor_pos,
    )
    mon_sig = np.asarray(result["monitor_signal"])
    peak = float(np.max(np.abs(mon_sig)))
    dist = (mon_x - src_x) * dx * 1e6  # 源到监视器距离 (μm)
    print(f"  {name}: {nx}x{ny}x{nz} PML={pml_layers} | src_x={src_x} mon_x={mon_x} 距离={dist:.1f}μm | peak={peak:.3e}")


if __name__ == "__main__":
    run_test("A. NX=24 (当前)", 24, 12, 8, 2)
    run_test("B. NX=32", 32, 12, 8, 2)
    run_test("C. NX=48", 48, 12, 8, 2)
    run_test("D. NX=64", 64, 12, 8, 2)
