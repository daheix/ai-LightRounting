"""诊断 EME run() 实际求解时各段的 n_eff，定位功率爆炸根因。

build_taper 用中点宽度法生成 5 段，每段调用 FDE 求解。
打印每段实际求解的 n_eff，看哪一段导致 exp(+iβL) 指数增长。
"""
from __future__ import annotations

import numpy as np

from polaris.sim.eme_backend import EMEConfig, FIMMPROPBackend


def main():
    cfg = EMEConfig(
        n_modes=1,
        wavelength=1.55e-6,
        dx=5e-8,
        dy=5e-8,
        window_size=(3.0e-6, 2.5e-6),
        pml_layers=8,
        polarization="te",
    )
    print(f"EMEConfig: dx={cfg.dx*1e9:.2f}nm, dy={cfg.dy*1e9:.2f}nm, "
          f"window={cfg.window_size[0]*1e6:.1f}x{cfg.window_size[1]*1e6:.1f}um, "
          f"pml={cfg.pml_layers}, n_modes={cfg.n_modes}")
    backend = FIMMPROPBackend(cfg)
    backend.build_taper(
        length=20.0e-6, w_in=0.5e-6, w_out=0.8e-6,
        height=0.22e-6, n_core=3.476, n_clad=1.444,
        n_steps=5,
    )
    print(f"\n=== build_taper 5 段 ===")
    for sec in backend._sections:
        print(f"  section_id={sec.section_id}, label={sec.label}, "
              f"length={sec.length*1e6:.2f}um, eps_shape={sec.eps_r.shape}")

    print(f"\n=== 各段 FDE 求解 n_eff ===")
    for sec in backend._sections:
        result = backend.solve_modes(sec.section_id)
        n_eff = result["n_eff"][0]
        te = result["te_fraction"][0]
        re = float(np.real(n_eff))
        im = float(np.imag(n_eff))
        # 计算传播因子 |exp(i*beta*L)|
        beta = result["beta"][0]
        prop = np.exp(1j * complex(beta) * sec.length)
        print(f"  {sec.label}: n_eff={re:.6f}{im:+.6e}j, te_frac={te:.4f}, "
              f"|exp(i*beta*L)|={float(np.abs(prop)):.4e}")

    print(f"\n=== 执行 EME run() ===")
    try:
        result = backend.run()
        print(f"  energy_sum = {result['energy_sum']:.6e}")
        print(f"  reflection = {result['reflection']}")
        print(f"  transmission = {result['transmission']}")
    except Exception as e:
        print(f"  run() 失败: {type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
