"""诊断 n_modes 扫描（简化版，避免大网格卡住）。"""
import sys
sys.path.insert(0, "/workspace/src")
import numpy as np
from polaris.sim.eme_backend import EMEConfig, FIMMPROPBackend

_N_SI = 3.476
_N_SIO2 = 1.444
_WL = 1.55e-6
_W = 0.5e-6
_H = 0.22e-6

print("=" * 70)
print("诊断 A: n_modes 扫描对 energy_sum 的影响 (test_run_taper)")
print("=" * 70)
for n_modes in [1, 2, 3, 4, 5]:
    backend = FIMMPROPBackend(EMEConfig(
        n_modes=n_modes, wavelength=_WL, dx=5e-8, dy=5e-8,
        window_size=(3.0e-6, 2.5e-6), pml_layers=8, polarization="te",
    ))
    backend.build_taper(length=20.0e-6, w_in=_W, w_out=0.8e-6,
                        height=_H, n_core=_N_SI, n_clad=_N_SIO2, n_steps=5)
    try:
        result = backend.run()
        print(f"  n_modes={n_modes}: energy_sum={result['energy_sum']:.6f}  "
              f"|T|={np.abs(result['transmission'][0]):.4f}  "
              f"|R|={np.abs(result['reflection'][0]):.4f}", flush=True)
    except Exception as e:
        print(f"  n_modes={n_modes}: 失败 {type(e).__name__}: {e}", flush=True)

print("\n" + "=" * 70)
print("诊断 B: n_modes 扫描对 energy_sum 的影响 (test_build_mmi_and_crossing)")
print("=" * 70)
for n_modes in [1, 2, 3, 4, 5, 6]:
    backend2 = FIMMPROPBackend(EMEConfig(
        n_modes=n_modes, wavelength=_WL, dx=5e-8, dy=5e-8,
        window_size=(3.0e-6, 2.5e-6), pml_layers=8, polarization="te",
    ))
    backend2.build_crossing(
        length=10.0e-6, width_port=_W, width_wide=1.5e-6,
        height=_H, n_core=_N_SI, n_clad=_N_SIO2, n_steps=2,
    )
    try:
        result2 = backend2.run()
        print(f"  n_modes={n_modes}: energy_sum={result2['energy_sum']:.6f}  "
              f"|T|={np.abs(result2['transmission'][0]):.4f}  "
              f"|R|={np.abs(result2['reflection'][0]):.4f}", flush=True)
    except Exception as e:
        print(f"  n_modes={n_modes}: 失败 {type(e).__name__}: {e}", flush=True)
print("\n完成", flush=True)
