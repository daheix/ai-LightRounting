"""R946 波导仿真示例。

演示：波导 S 参数模型 + 波导级联电路仿真 + 传输谱/相位分析。

学术依据（R02）：
- Simphony 仿真器 https://simphonyphotonics.readthedocs.io/
- Chrostowski & Hochberg 2015 Silicon Photonics Design Cambridge
  https://doi.org/10.1017/CBO9781316084168
- Yariv & Yeh 1984 Optical Waves in Crystals Wiley Ch.13

运行: PYTHONPATH=src python examples/waveguide_simulation.py
"""

from __future__ import annotations

import numpy as np

from polaris.sim.models import waveguide_s
from polaris.sim.simulator import CircuitSimulator, WavelengthRange, default_models


def main() -> None:
    """运行波导仿真示例。"""
    wl = np.linspace(1.5, 1.6, 1000)

    # 1) 单器件波导 S 参数
    s = waveguide_s(wl=wl, length=100.0, neff=2.4, loss_db_cm=0.5)
    transmission = np.abs(s[("in", "out")]) ** 2
    print("=== 单波导（100μm, neff=2.4, 0.5dB/cm）===")
    print(f"  传输率: {transmission.min():.4f} ~ {transmission.max():.4f}")
    print(f"  相位范围: {np.angle(s[('in','out')]).min():.3f} ~ "
          f"{np.angle(s[('in','out')]).max():.3f} rad")

    # 2) 波导级联电路仿真
    sim = CircuitSimulator(models=default_models())
    netlist = {
        "instances": {"wg1": "waveguide", "wg2": "waveguide"},
        "connections": {"wg1.out": "wg2.in"},
        "ports": {"in": "wg1.in", "out": "wg2.out"},
    }
    wl_sweep, s_circuit = sim.sweep_wavelength(
        netlist, wl_range=WavelengthRange(1.5, 1.6, 1000)
    )
    t_circuit = np.abs(s_circuit[("in", "out")]) ** 2
    print("\n=== 两段波导级联（总长 200μm）===")
    print(f"  波长扫描点数: {len(wl_sweep)}")
    print(f"  传输率: {t_circuit.min():.4f} ~ {t_circuit.max():.4f}")

    # 3) 不同损耗对比
    print("\n=== 损耗对传输率的影响（length=500μm）===")
    for loss_db_cm in [0.0, 0.5, 1.0, 3.0]:
        s_loss = waveguide_s(wl=1.55, length=500.0, neff=2.4, loss_db_cm=loss_db_cm)
        t = np.abs(s_loss[("in", "out")]) ** 2
        print(f"  loss={loss_db_cm:.1f} dB/cm -> 传输率={float(t):.4f} "
              f"({-10*np.log10(float(t)):.2f} dB 插损)")


if __name__ == "__main__":
    main()
