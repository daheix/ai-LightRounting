"""逐步追踪 TFSF 注入与传播（前 30 步 + 脉冲到达 i0 时）。"""
import numpy as np
from polaris.sim.fdtd import (
    GaussianPulse, Incident1D, TfsfBox, YeeGridFdtd, courant_dt,
    apply_tfsf_h_correction, apply_tfsf_e_correction,
)

C0 = 2.99792458e8
LAM = 1.55e-6
F0 = C0 / LAM
dx = dy = 20e-9
nx, ny = 400, 12
dt = courant_dt(dx, dy, cfl=0.49)
eps = np.ones((nx, ny))
grid = YeeGridFdtd((nx, ny), dx, dy, dt, eps)
tau = 0.3e-14
wf = GaussianPulse(amplitude=1.0, frequency=F0, t0=3 * tau, tau=tau)
tfsf = TfsfBox(i0=4, i1=320, j0=1, j1=ny - 2)
jmid = ny // 2

ca, cb = grid.ca_ez, grid.cb_ez
da, db = grid.da_h, grid.db_h
e_z = np.zeros((nx, ny))
h_x = np.zeros((nx, ny))
h_y = np.zeros((nx, ny))
incident = Incident1D(nx, dx, dt)

print(f"cb={cb[0,0]:.3e} db={db[0,0]:.3e} dx={dx:.3e} cfl1d={C0*dt/dx:.4f}")
print(f"{'n':>3} {'Einc4':>11} {'Ez4':>11} {'Einc5':>11} {'Ez5':>11} {'Einc10':>11} {'Ez10':>11} {'Einc50':>11} {'Ez50':>11}")

N = 120
for n in range(N):
    t = n * dt
    # update_h
    h_x[:, :-1] = da[:, :-1] * h_x[:, :-1] - db[:, :-1] * (e_z[:, 1:] - e_z[:, :-1]) / dy
    h_y[:-1, :] = da[:-1, :] * h_y[:-1, :] + db[:-1, :] * (e_z[1:, :] - e_z[:-1, :]) / dx
    # H 校正 (step 前)
    apply_tfsf_h_correction(h_y, tfsf, incident, db, dx)
    # incident.step
    incident.step(float(wf(t)))
    # update_e (内部)
    dhy_dx = (h_y[1:-1, 1:-1] - h_y[:-2, 1:-1]) / dx
    dhx_dy = (h_x[1:-1, 1:-1] - h_x[1:-1, :-2]) / dy
    curl_z = dhy_dx - dhx_dy
    e_z[1:-1, 1:-1] = ca[1:-1, 1:-1] * e_z[1:-1, 1:-1] + cb[1:-1, 1:-1] * curl_z
    # E 校正 (step 后)
    apply_tfsf_e_correction(e_z, tfsf, incident, cb, dx)
    if n in (4, 10, 20, 30, 50, 80, 100, 119):
        print(f"{n:3d} {incident.e_inc[4]:+11.4e} {e_z[4,jmid]:+11.4e} "
              f"{incident.e_inc[5]:+11.4e} {e_z[5,jmid]:+11.4e} "
              f"{incident.e_inc[10]:+11.4e} {e_z[10,jmid]:+11.4e} "
              f"{incident.e_inc[50]:+11.4e} {e_z[50,jmid]:+11.4e}")
