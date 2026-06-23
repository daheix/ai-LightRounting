"""R2 调试 v5: 测试 stage10 实际配置（NZ=8, PML=2）+ 新公式。"""
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


def run_test(name: str, nx, ny, nz, pml_layers, sigma_ratio, use_waveguide, n_steps=600):
    dx = 0.2e-6
    grid = YeeGrid3D(nx=nx, ny=ny, nz=nz, dx=dx, dy=dx, dz=dx)
    grid.epsilon_r = jnp.full((nx, ny, nz), EPS_R_SI)
    cfl_dt = grid.cfl_timestep(EPS_R_SI)
    dt = 0.3 * float(cfl_dt)

    pml = GedneyPML(grid, n_layers=pml_layers, sigma_ratio=sigma_ratio, eps_r_bg=EPS_R_SI)
    fdtd = DifferentiableFDTD(grid, pml=pml, dt=dt, eps_r_bg=EPS_R_SI)
    ca_arr = np.asarray(fdtd.ca)

    if use_waveguide:
        y_coords = jnp.arange(ny, dtype=jnp.float32)
        center = ny / 2.0
        soft_mask = jax.nn.sigmoid((2.0 - jnp.abs(y_coords - center)) / 0.5)
        delta = 0.50 * EPS_R_SI
        eps_r = EPS_R_SI + delta * soft_mask[None, :, None]
        eps_r = jnp.broadcast_to(eps_r, (nx, ny, nz))
    else:
        eps_r = jnp.full((nx, ny, nz), EPS_R_SI)

    src_z = pml_layers + 1
    source_pos = (3, ny // 2, src_z)
    monitor_pos = (nx - 4, ny // 2, src_z)
    source_freq = C0 / 1.55e-6

    result = fdtd.run(
        epsilon_r=eps_r, source_pos=source_pos, source_freq=source_freq,
        n_steps=n_steps, monitor_pos=monitor_pos,
    )
    mon_sig = np.asarray(result["monitor_signal"])
    peak = float(np.max(np.abs(mon_sig)))
    wg = "波导" if use_waveguide else "均匀"
    stable = "稳定" if peak < 1e3 and not np.isnan(peak) else "发散"
    print(f"  {name}: {nx}x{ny}x{nz} PML={pml_layers} ratio={sigma_ratio} {wg} | ca={ca_arr[nx//2,ny//2,0]:.3f} peak={peak:.3e} {stable}")


if __name__ == "__main__":
    print("=== stage10 配置 NZ=8, PML=2 ===")
    run_test("A", 24, 12, 8, 2, 1.0, False)
    run_test("B", 24, 12, 8, 2, 1.0, True)
    run_test("C", 24, 12, 8, 2, 3.0, True)

    print("\n=== 大网格 NZ=16, PML=4 ===")
    run_test("D", 24, 12, 16, 4, 1.0, True)
    run_test("E", 24, 12, 16, 4, 3.0, True)
