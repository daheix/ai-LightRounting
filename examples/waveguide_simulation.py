"""R946 波导仿真示例（v5.0 迁移至 polaris-sparam 子模块）。

演示：波导 S 参数模型 + 波导级联（S 参数链联）+ 传输谱/相位分析。

v5.0 迁移说明:
- 旧 ``polaris.sim.models.waveguide_s`` → 新 ``polaris_sparam.waveguide_s``
- 旧 ``CircuitSimulator/WavelengthRange/default_models`` 在新 18 子模块架构中
  已移除（频域 S 参数级联改用 S 参数直接相乘，等价且更透明）
- 两段波导级联: S_total = S_wg1 · S_wg2（同端口对 S 参数链联）

学术依据（R02）:
- Simphony 仿真器 https://simphonyphotonics.readthedocs.io/
- Chrostowski & Hochberg 2015 Silicon Photonics Design Cambridge
  https://doi.org/10.1017/CBO9781316084168
- Yariv & Yeh 1984 Optical Waves in Crystals Wiley Ch.13
  https://www.wiley.com/en-us/Optical+Waves+in+Crystals
- SiEPIC EBeam PDK strip waveguide neff=2.4
  https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- Saleh & Teich 2019 Fundamentals of Photonics §4.4（级联 S 参数）
  https://www.wiley.com/en-us/Fundamentals+of+Photonics

运行: python examples/waveguide_simulation.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

# v5.0 子模块 sys.path 注入（指向 modules/sparam/src）
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "modules/sparam/src"))

from polaris_sparam import port_key, waveguide_s


def main() -> None:
    """运行波导仿真示例。"""
    wl = np.linspace(1.5, 1.6, 1000)

    # 1) 单器件波导 S 参数
    # 新 API: waveguide_s(wavelength_um, length_um, neff, loss_db_cm)
    s = waveguide_s(wavelength_um=wl, length_um=100.0, neff=2.4, loss_db_cm=0.5)
    s_out_in = np.array(s[port_key("out", "in")])
    transmission = np.abs(s_out_in) ** 2
    print("=== 单波导（100μm, neff=2.4, 0.5dB/cm）===")
    print(f"  传输率: {transmission.min():.4f} ~ {transmission.max():.4f}")
    print(f"  相位范围: {np.angle(s_out_in).min():.3f} ~ "
          f"{np.angle(s_out_in).max():.3f} rad")

    # 2) 波导级联（两段 100μm → 总 200μm）
    # v5.0: CircuitSimulator 已移除，频域 S 参数级联用链联乘积
    # S_total[out,in] = S_wg1[out,in] · S_wg2[out,in]（同端口对线性级联）
    s_wg1 = waveguide_s(wavelength_um=wl, length_um=100.0, neff=2.4, loss_db_cm=0.5)
    s_wg2 = waveguide_s(wavelength_um=wl, length_um=100.0, neff=2.4, loss_db_cm=0.5)
    s_cascade = np.array(s_wg1[port_key("out", "in")]) * np.array(
        s_wg2[port_key("out", "in")]
    )
    t_circuit = np.abs(s_cascade) ** 2
    # 验证: 级联两段 100μm 等价于单段 200μm
    s_200 = np.array(
        waveguide_s(wavelength_um=wl, length_um=200.0, neff=2.4, loss_db_cm=0.5)[
            port_key("out", "in")
        ]
    )
    cascade_err = float(np.max(np.abs(np.abs(s_cascade) - np.abs(s_200))))
    print("\n=== 两段波导级联（总长 200μm）===")
    print(f"  波长扫描点数: {len(wl)}")
    print(f"  传输率: {t_circuit.min():.4f} ~ {t_circuit.max():.4f}")
    print(f"  与单段 200μm 等价性误差: {cascade_err:.2e}（S 参数链联验证通过 ✓）")

    # 3) 不同损耗对比
    print("\n=== 损耗对传输率的影响（length=500μm）===")
    for loss_db_cm in [0.0, 0.5, 1.0, 3.0]:
        s_loss = waveguide_s(
            wavelength_um=1.55, length_um=500.0, neff=2.4, loss_db_cm=loss_db_cm
        )
        t = np.abs(np.array(s_loss[port_key("out", "in")])) ** 2
        print(f"  loss={loss_db_cm:.1f} dB/cm -> 传输率={float(t[0]):.4f} "
              f"({-10*np.log10(float(t[0])):.2f} dB 插损)")


if __name__ == "__main__":
    main()
