"""TFSF 诊断：检查 TF 区 E_z 与 1D 入射场 e_inc 的实际关系。"""
import numpy as np
from polaris.sim.fdtd import (
    CpmlConfig, FdtdConfig, FdtdSolver, GaussianPulse, Incident1D,
    TfsfBox, YeeGridFdtd, courant_dt,
)

C0 = 2.99792458e8
LAM = 1.55e-6
F0 = C0 / LAM
dx = dy = 20e-9
nx, ny = 400, 12
dt = courant_dt(dx, dy, cfl=0.49)
grid = YeeGridFdtd((nx, ny), dx, dy, dt, np.ones((nx, ny)))
tau = 0.3e-14
wf = GaussianPulse(amplitude=1.0, frequency=F0, t0=3 * tau, tau=tau)
tfsf = TfsfBox(i0=4, i1=320, j0=1, j1=ny - 2)
n_steps = 700
# 加探针在 TF 区中部
probe = (160, ny // 2)
cfg = FdtdConfig(grid=grid, n_steps=n_steps, tfsf=tfsf, tfsf_waveform=wf,
                 probe_point=probe)
res = FdtdSolver(cfg).run()

# 独立 1D 参考
inc = Incident1D(nx, dx, dt)
for n in range(n_steps):
    inc.step(float(wf(n * dt)))

jmid = ny // 2
print("=== 终态场采样（TF 区中部，j=mid）===")
print(f"网格: nx={nx} ny={ny} dx={dx*1e9:.1f}nm dt={dt:.3e}s n_steps={n_steps}")
print(f"TF 区: i0={tfsf.i0} i1={tfsf.i1}")
print(f"脉冲: tau={tau:.2e} t0={3*tau:.2e} F0={F0:.3e}")
print()
# 检查几个 i 点
for i in [4, 10, 50, 100, 150, 160, 200, 250, 300]:
    ez = res.e_z[i, jmid]
    ei = inc.e_inc[i]
    hi = inc.h_inc[i]
    print(f"i={i:3d}: E_z={ez:+.4e}  E_inc={ei:+.4e}  H_inc={hi:+.4e}  "
          f"Ez/Einc={ez/(ei+1e-30):+.3f}")

print()
print("=== 探针时序（前 30 步与峰值附近）===")
ts = res.time_series
peak_idx = np.argmax(np.abs(ts))
print(f"探针峰值步: {peak_idx}, 峰值: {ts[peak_idx]:+.4e}")
for n in list(range(min(10, n_steps))) + [peak_idx-1, peak_idx, peak_idx+1]:
    if 0 <= n < n_steps:
        print(f"  n={n:3d}: E_z[probe]={ts[n]:+.4e}")

print()
# 检查 E_z 沿 x 的剖面（脉冲应在哪？）
print("=== E_z 沿 x 剖面（j=mid，找峰值位置）===")
prof = res.e_z[:, jmid]
i_peak = np.argmax(np.abs(prof))
print(f"E_z 峰值在 i={i_peak}, 值={prof[i_peak]:+.4e}")
ei_peak = np.argmax(np.abs(inc.e_inc))
print(f"E_inc 峰值在 i={ei_peak}, 值={inc.e_inc[ei_peak]:+.4e}")
# 检查是否整体反号
mask = np.abs(inc.e_inc) > 0.1 * np.max(np.abs(inc.e_inc))
if mask.sum() > 0:
    ratio = res.e_z[mask, jmid] / (inc.e_inc[mask] + 1e-30)
    print(f"TF 区 E_z/E_inc 比值: 均值={np.mean(ratio):+.3f} 中位={np.median(ratio):+.3f}")
