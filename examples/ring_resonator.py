"""R948 环谐振器示例（v5.0 迁移至 polaris-sparam 子模块）。

演示：全通型单总线环谐振器的谐振谱（Lorentzian 谐振模型）。

传输函数: T = (t - a·e^{iφ}) / (1 - t·a·e^{iφ})
- t: 直通振幅 = √(1 - coupling)
- a: 环内单圈振幅衰减 = 10^(-loss_db_cm·L/1e4/20)
- φ: 环周相位 = β·2π·R = 2π·neff·2π·R/λ

v5.0 迁移说明:
- 旧 ``polaris.sim.models.ring_resonator_s`` → 新 ``polaris_sparam.ring_resonator_s``
- 新 API 参数名带 _um 后缀: wavelength_um / radius_um
- 新 API 返回 dict 用 port_key() str key（非 tuple key）

学术依据（R02）:
- Yariv 1997 Optical Electronics in Modern Communications §10.5
  https://doi.org/10.1093/oso/9780195106266.001.0001
- SiPANN ring_resonator https://sipann.readthedocs.io/en/latest/models.html
- Bogaerts et al. 2012 Silicon microring resonators JLT
  https://doi.org/10.1109/JLT.2012.2200478
- Chrostowski & Hochberg 2015 Silicon Photonics Design §4.5
  https://www.cambridge.org/core/books/silicon-photonics-design/
- SiEPIC EBeam PDK strip waveguide neff=2.4
  https://github.com/SiEPIC/SiEPIC_EBeam_PDK

运行: python examples/ring_resonator.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

# v5.0 子模块 sys.path 注入（指向 modules/sparam/src）
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "modules/sparam/src"))

from polaris_sparam import port_key, ring_resonator_s


def main() -> None:
    """运行环谐振器示例。"""
    # 高分辨率波长扫描以分辨谐振峰（FSR 随半径减小）
    wl = np.linspace(1.54, 1.56, 5000)

    print("=== 环谐振器谐振谱 ===")
    print(f"{'半径(μm)':>10} {'谐振峰数':>10} {'最小传输率':>12} {'FSR近似(nm)':>14}")
    print("-" * 50)

    for radius in [5.0, 10.0, 20.0, 50.0]:
        s = ring_resonator_s(wavelength_um=wl, radius_um=radius)
        t = np.abs(np.array(s[port_key("through", "in")])) ** 2

        # 检测谐振峰（局部极小值）
        # 用差分符号变化找极小值
        diff = np.diff(t)
        minima = np.where((diff[:-1] < 0) & (diff[1:] > 0))[0]
        n_peaks = len(minima)

        # FSR 估算（相邻谐振峰间距）
        if n_peaks >= 2:
            fsr_nm = float(np.mean(np.diff(wl[minima]))) * 1000
        else:
            fsr_nm = float("nan")

        print(f"{radius:>10.1f} {n_peaks:>10} {t.min():>12.6f} {fsr_nm:>14.2f}")

    print("\n=== 单环详细（R=10μm）===")
    s_ring = ring_resonator_s(wavelength_um=wl, radius_um=10.0)
    t_ring = np.abs(np.array(s_ring[port_key("through", "in")])) ** 2
    print(f"  传输率范围: {t_ring.min():.6f} ~ {t_ring.max():.6f}")
    print(f"  谐振深度 (消光比): {-10 * np.log10(t_ring.min()):.2f} dB")
    # FSR 公式: FSR = λ² / (n_g · L)，L = 2π·R（环周长），n_g 群折射率
    # 来源: Bogaerts 2012 JLT §II; Yariv 1997 §10.5
    lambda_um = 1.55
    n_g = 4.0  # SOI 群折射率典型值
    fsr_theory_nm = lambda_um ** 2 / (n_g * 2 * np.pi * 10.0) * 1000
    print(f"  理论 FSR (λ={lambda_um}μm, n_g={n_g}, R=10μm): "
          f"{fsr_theory_nm:.2f} nm")


if __name__ == "__main__":
    main()
