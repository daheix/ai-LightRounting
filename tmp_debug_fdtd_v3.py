"""R2 调试 v3: 测试不同 sigma_ratio，找到能稳定 PML 的配置。"""
from __future__ import annotations

import jax
import jax.numpy as jnp
import numpy as np

from polaris.sim.fdtd_jax_backend import (
    C0,
    EPS0,
    MU0,
    DifferentiableFDTD,
    GedneyPML,
    YeeGrid3D,
)

EPS_R_SI = 3.476 ** 2  # 12.08


def run_test(name: str, sigma_ratio: float, nx=24, ny=12, nz=16, pml_layers=4, n_steps=600) -> None:
    dx = 0.2e-6
    grid = YeeGrid3D(nx=nx, ny=ny, nz=nz, dx=dx, dy=dx, dz=dx)
    grid.epsilon_r = jnp.full((nx, ny, nz), EPS_R_SI)

    cfl_dt = grid.cfl_timestep(EPS_R_SI)
    dt = 0.3 * float(cfl_dt)

    pml = GedneyPML(grid, n_layers=pml_layers, sigma_ratio=sigma_ratio, eps_r_bg=EPS_R_SI)
    fdtd = DifferentiableFDTD(grid, pml=pml, dt=dt, eps_r_bg=EPS_R_SI)

    ca_arr = np.asarray(fdtd.ca)
    # 计算 σΔt/2ε
    sigma_dt_2eps = (1.0 - ca_arr) / (1.0 + ca_arr)
    print(f"\n=== {name}: sigma_ratio={sigma_ratio} ===")
    print(f"  ca 外层: {ca_arr[nx//2, ny//2, 0]:.4f}, σΔt/2ε={sigma_dt_2eps[nx//2, ny//2, 0]:.4f}")

    src_z = pml_layers + 1
    source_pos = (3, ny // 2, src_z)
    monitor_pos = (nx - 4, ny // 2, src_z)
    source_freq = C0 / 1.55e-6

    result = fdtd.run(
        epsilon_r=jnp.full((nx, ny, nz), EPS_R_SI),
        source_pos=source_pos,
        source_freq=source_freq,
        n_steps=n_steps,
        monitor_pos=monitor_pos,
    )
    mon_sig = np.asarray(result["monitor_signal"])
    peak_mon = float(np.max(np.abs(mon_sig)))
    chunks = [float(np.max(np.abs(mon_sig[i * 100:(i + 1) * 100]))) for i in range(6)]
    print(f"  peak: {peak_mon:.3e}, 每100步: {['%.2e' % c for c in chunks]}")
    print(f"  结果: {'发散' if peak_mon > 1e3 or np.isnan(peak_mon) else '稳定'}")


if __name__ == "__main__":
    run_test("A. ratio=1 (当前)", 1.0)
    run_test("B. ratio=10", 10.0)
    run_test("C. ratio=20", 20.0)
    run_test("D. ratio=30", 30.0)
    run_test("E. ratio=50", 50.0)
