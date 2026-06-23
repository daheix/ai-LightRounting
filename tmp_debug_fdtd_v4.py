"""R2 调试 v4: 测试新 sigma_max 公式（含 dt 补偿）的不同 sigma_ratio。"""
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

EPS_R_SI = 3.476 ** 2  # 12.08


def run_test(name: str, sigma_ratio: float, use_waveguide: bool = False, nx=24, ny=12, nz=16, pml_layers=4, n_steps=600) -> None:
    dx = 0.2e-6
    grid = YeeGrid3D(nx=nx, ny=ny, nz=nz, dx=dx, dy=dx, dz=dx)
    grid.epsilon_r = jnp.full((nx, ny, nz), EPS_R_SI)

    cfl_dt = grid.cfl_timestep(EPS_R_SI)
    dt = 0.3 * float(cfl_dt)

    pml = GedneyPML(grid, n_layers=pml_layers, sigma_ratio=sigma_ratio, eps_r_bg=EPS_R_SI)
    fdtd = DifferentiableFDTD(grid, pml=pml, dt=dt, eps_r_bg=EPS_R_SI)

    ca_arr = np.asarray(fdtd.ca)
    sigma_dt_2eps = (1.0 - ca_arr) / (1.0 + ca_arr)

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
        epsilon_r=eps_r,
        source_pos=source_pos,
        source_freq=source_freq,
        n_steps=n_steps,
        monitor_pos=monitor_pos,
    )
    mon_sig = np.asarray(result["monitor_signal"])
    peak_mon = float(np.max(np.abs(mon_sig)))
    wg_tag = "波导" if use_waveguide else "均匀"
    print(f"  {name}: ratio={sigma_ratio}, {wg_tag}, ca外层={ca_arr[nx//2,ny//2,0]:.3f}, σΔt/2ε={sigma_dt_2eps[nx//2,ny//2,0]:.3f}, peak={peak_mon:.3e}, {'发散' if peak_mon>1e3 or np.isnan(peak_mon) else '稳定'}")


if __name__ == "__main__":
    print("=== 新公式测试（均匀 eps）===")
    run_test("ratio=1", 1.0)
    run_test("ratio=3", 3.0)
    run_test("ratio=5", 5.0)
    run_test("ratio=10", 10.0)

    print("\n=== 新公式测试（波导 eps）===")
    run_test("ratio=3", 3.0, use_waveguide=True)
    run_test("ratio=5", 5.0, use_waveguide=True)
    run_test("ratio=10", 10.0, use_waveguide=True)
