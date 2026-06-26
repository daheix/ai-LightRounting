"""隔离测试：偶极子源能否在 TF 区传播（排除 TFSF 因素）。"""
import numpy as np
from polaris.sim.fdtd import (
    FdtdConfig, FdtdSolver, GaussianPulse, YeeGridFdtd, courant_dt,
)
from polaris.sim.fdtd.sources import DipoleSource

C0 = 2.99792458e8
LAM = 1.55e-6
F0 = C0 / LAM
dx = dy = 20e-9
nx, ny = 400, 12
dt = courant_dt(dx, dy, cfl=0.49)
grid = YeeGridFdtd((nx, ny), dx, dy, dt, np.ones((nx, ny)))
print(f"ca={grid.ca_ez[100,6]} cb={grid.cb_ez[100,6]:.3e} da={grid.da_h[100,6]} db={grid.db_h[100,6]:.3e}")
tau = 0.3e-14
wf = GaussianPulse(amplitude=1.0, frequency=F0, t0=3 * tau, tau=tau)
src = DipoleSource(position=(4, 6), waveform=wf, current_moment=1.0)
probe = (100, 6)
cfg = FdtdConfig(grid=grid, n_steps=700, dipole_sources=[src], probe_point=probe)
res = FdtdSolver(cfg).run()
jmid = 6
print("=== 偶极子源传播测试（j=mid）===")
for i in [4, 10, 50, 100, 150, 200]:
    print(f"i={i:3d}: E_z={res.e_z[i, jmid]:+.4e}")
ts = res.time_series
pk = np.argmax(np.abs(ts))
print(f"探针(100,6)峰值步={pk} 值={ts[pk]:+.4e}")
print("（若探针有值，说明波能传播，问题在 TFSF；若无值，说明 update 传播有 bug）")
