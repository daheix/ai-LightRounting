"""R947 定向耦合器示例（v5.0 迁移至 polaris-sparam 子模块）。

演示：定向耦合器功率分光比随目标耦合比 coupling 的变化（耦合模理论 CMT）。

公式（学术依据 R02）:
- 功率耦合比: P_cross/P_in = sin²(κL)
- 直通功率: P_through/P_in = cos²(κL)
- 完全耦合长度: L_c = π/(2κ)
- 由目标 coupling 反算: κL = arcsin(√coupling)

v5.0 迁移说明:
- 旧 ``polaris.sim.models.directional_coupler_s`` → 新 ``polaris_sparam.directional_coupler_s``
- 新 API 参数名带 _um 后缀: wavelength_um / length_um / gap_um
- 新 API 返回 dict 用 port_key() str key（非 tuple key）

来源（R02 学术诚信，≥5 个文献 URL）:
- Yariv & Yeh 1984 Optical Waves in Crystals Wiley Ch.13（耦合模理论）
  https://www.wiley.com/en-us/Optical+Waves+in+Crystals
- Chrostowski & Hochberg 2015 Silicon Photonics Design §4.5
  https://www.cambridge.org/core/books/silicon-photonics-design/
- Soldano & Pennings 1995 JLT（MMI/耦合器）
  https://ieeexplore.ieee.org/document/374358
- SiPANN directional_coupler https://sipann.readthedocs.io/en/latest/models.html
- Snyder & Love 1983 Optical Waveguide Theory Chapman & Hall
- Lumerical Directional Couplers
  https://optics.ansys.com/hc/en-us/articles/360042077053

运行: python examples/directional_coupler.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

# v5.0 子模块 sys.path 注入（指向 modules/sparam/src）
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "modules/sparam/src"))

from polaris_sparam import directional_coupler_s, port_key


def main() -> None:
    """运行定向耦合器示例。"""
    wl = 1.55

    print("=== 定向耦合器分光比 vs 目标耦合比 coupling ===")
    print(f"{'coupling':>10} {'直通':>8} {'交叉':>8} {'状态':>10}")
    print("-" * 42)

    # 扫描目标功率耦合比 coupling（0=全直通，1=全交叉，0.5=3dB）
    # coupling 直接决定 P_cross = sin²(κL)，length/gap 影响相位与损耗
    for coupling in [0.0, 0.1, 0.3, 0.5, 0.7, 0.9, 1.0]:
        s = directional_coupler_s(
            wavelength_um=wl, coupling=coupling, length_um=10.0, gap_um=0.2, neff=2.4
        )
        # 端口: in1, in2, out1, out2（交叉耦合 out2←in1）
        # 新 API 标量波长返回长度1的 list，取 [0] 转标量
        p_through = float(np.abs(np.array(s[port_key("out1", "in1")])[0]) ** 2)
        p_cross = float(np.abs(np.array(s[port_key("out2", "in1")])[0]) ** 2)
        if p_cross < 0.01:
            status = "直通"
        elif p_through < 0.01:
            status = "全交叉"
        elif abs(p_through - p_cross) < 0.05:
            status = "3dB 耦合"
        else:
            status = "部分耦合"
        print(f"{coupling:>10.1f} {p_through:>8.4f} {p_cross:>8.4f} {status:>10}")

    print("\n=== 3dB 耦合器（coupling=0.5, 50:50 分光）===")
    s_3db = directional_coupler_s(
        wavelength_um=1.55, coupling=0.5, length_um=10.0
    )
    p_thr = float(np.abs(np.array(s_3db[port_key("out1", "in1")])[0]) ** 2)
    p_crs = float(np.abs(np.array(s_3db[port_key("out2", "in1")])[0]) ** 2)
    print(f"  直通功率: {p_thr:.4f}")
    print(f"  交叉功率: {p_crs:.4f}")
    print(f"  总功率守恒: {p_thr + p_crs:.4f}")


if __name__ == "__main__":
    main()
