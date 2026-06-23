"""R2 调试 v2: 测试不同 PML 层数和网格尺寸，找到稳定配置。"""
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


def run_test(name: str, nx: int, ny: int, nz: int, pml_layers: int, n_steps: int = 600) -> None:
    print(f"\n=== {name}: {nx}x{ny}x{nz}, PML={pml_layers}, steps={n_steps} ===")
    dx = 0.2e-6
    grid = YeeGrid3D(nx=nx, ny=ny, nz=nz, dx=dx, dy=dx, dz=dx)
    grid.epsilon_r = jnp.full((nx, ny, nz), EPS_R_SI)

    cfl_dt = grid.cfl_timestep(EPS_R_SI)
    dt = 0.3 * float(cfl_dt)

    if pml_layers > 0:
        pml = GedneyPML(grid, n_layers=pml_layers, eps_r_bg=EPS_R_SI)
        fdtd = DifferentiableFDTD(grid, pml=pml, dt=dt, eps_r_bg=EPS_R_SI)
        # 打印 PML 系数
        ca_arr = np.asarray(fdtd.ca)
        cb_arr = np.asarray(fdtd.cb)
        print(f"  ca 范围: [{ca_arr.min():.4f}, {ca_arr.max():.4f}]")
        print(f"  cb 范围: [{cb_arr.min():.4e}, {cb_arr.max():.4e}]")
        # PML 外层 ca
        print(f"  PML 外层 ca (z=0): {ca_arr[nx//2, ny//2, 0]:.4f}")
        print(f"  PML 内层 ca (z={pml_layers-1}): {ca_arr[nx//2, ny//2, pml_layers-1]:.4f}")
    else:
        fdtd = DifferentiableFDTD(grid, pml=None, dt=dt, eps_r_bg=EPS_R_SI)

    # 源/监视器在非 PML 区域
    src_z = pml_layers + 1
    mon_z = pml_layers + 1
    source_pos = (3, ny // 2, src_z)
    monitor_pos = (nx - 4, ny // 2, mon_z)
    source_freq = C0 / 1.55e-6

    result = fdtd.run(
        epsilon_r=jnp.full((nx, ny, nz), EPS_R_SI),
        source_pos=source_pos,
        source_freq=source_freq,
        n_steps=n_steps,
        monitor_pos=monitor_pos,
    )
    mon_sig = np.asarray(result["monitor_signal"])
    Ex = np.asarray(result["Ex"])

    peak_mon = float(np.max(np.abs(mon_sig)))
    max_Ex = float(np.max(np.abs(Ex)))
    chunks = [float(np.max(np.abs(mon_sig[i * (n_steps // 6):(i + 1) * (n_steps // 6)]))) for i in range(6)]
    print(f"  monitor peak: {peak_mon:.6e}, Ex max: {max_Ex:.6e}")
    print(f"  每 1/6 步: {['%.3e' % c for c in chunks]}")
    print(f"  结果: {'发散' if peak_mon > 1e6 or np.isnan(peak_mon) else '稳定'}")


if __name__ == "__main__":
    # 测试不同 PML 配置
    run_test("A. 无PML (基线)", 24, 12, 8, 0)
    run_test("B. PML=2, NZ=8", 24, 12, 8, 2)
    run_test("C. PML=4, NZ=16", 24, 12, 16, 4)
    run_test("D. PML=4, NZ=16, steps=400", 24, 12, 16, 4, n_steps=400)
