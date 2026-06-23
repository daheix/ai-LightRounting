"""R2 调试: 逐步排查 stage10 FDTD 发散原因。

测试矩阵:
1. 无 PML + 均匀 epsilon_r（基线，应和 stage5 一样稳定）
2. 无 PML + 空间变化 epsilon_r（波导）
3. 有 PML + 均匀 epsilon_r
4. 有 PML + 空间变化 epsilon_r（波导）
"""
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
NX, NY, NZ = 24, 12, 8
DX = 0.2e-6
N_STEPS = 600
PML_LAYERS = 2


def make_grid(eps_r_val: float) -> YeeGrid3D:
    grid = YeeGrid3D(nx=NX, ny=NY, nz=NZ, dx=DX, dy=DX, dz=DX)
    grid.epsilon_r = jnp.full((NX, NY, NZ), eps_r_val)
    return grid


def make_waveguide_eps(width_param: float = 2.0) -> jnp.ndarray:
    """波导 epsilon_r: 硅背景 + 50% 调制（与 stage10 一致）。"""
    y_coords = jnp.arange(NY, dtype=jnp.float32)
    center = NY / 2.0
    softness = 0.5
    dist = jnp.abs(y_coords - center)
    soft_mask = jax.nn.sigmoid((width_param - dist) / softness)
    delta = 0.50 * EPS_R_SI
    eps_r = EPS_R_SI + delta * soft_mask[None, :, None]
    return jnp.broadcast_to(eps_r, (NX, NY, NZ))


def run_test(name: str, use_pml: bool, use_waveguide: bool) -> None:
    print(f"\n=== 测试: {name} ===")
    grid = make_grid(EPS_R_SI)
    cfl_dt = grid.cfl_timestep(EPS_R_SI)
    dt = 0.3 * float(cfl_dt)

    if use_waveguide:
        eps_r = make_waveguide_eps(2.0)
    else:
        eps_r = jnp.full((NX, NY, NZ), EPS_R_SI)

    if use_pml:
        pml = GedneyPML(grid, n_layers=PML_LAYERS, eps_r_bg=EPS_R_SI)
        fdtd = DifferentiableFDTD(grid, pml=pml, dt=dt, eps_r_bg=EPS_R_SI)
    else:
        fdtd = DifferentiableFDTD(grid, pml=None, dt=dt, eps_r_bg=EPS_R_SI)

    source_pos = (3, NY // 2, 3)
    monitor_pos = (NX - 4, NY // 2, 3)
    source_freq = C0 / 1.55e-6

    result = fdtd.run(
        epsilon_r=eps_r,
        source_pos=source_pos,
        source_freq=source_freq,
        n_steps=N_STEPS,
        monitor_pos=monitor_pos,
    )
    mon_sig = np.asarray(result["monitor_signal"])
    Ex = np.asarray(result["Ex"])

    peak_mon = float(np.max(np.abs(mon_sig)))
    max_Ex = float(np.max(np.abs(Ex)))
    # 检查每 100 步的 monitor_signal
    print(f"  monitor peak: {peak_mon:.6e}")
    print(f"  Ex max: {max_Ex:.6e}")
    print(f"  monitor 每 100 步: {[f'{float(np.max(np.abs(mon_sig[i*100:(i+1)*100]))):.3e}' for i in range(6)]}")
    print(f"  是否发散: {'是' if peak_mon > 1e6 else '否'}")


if __name__ == "__main__":
    run_test("1. 无PML + 均匀eps", use_pml=False, use_waveguide=False)
    run_test("2. 无PML + 波导eps", use_pml=False, use_waveguide=True)
    run_test("3. 有PML + 均匀eps", use_pml=True, use_waveguide=False)
    run_test("4. 有PML + 波导eps", use_pml=True, use_waveguide=True)
