"""R947 定向耦合器示例。

演示：定向耦合器功率分光比随耦合区长度的变化（耦合模理论 CMT）。

公式（学术依据 R02）：
- 功率耦合比: P_cross/P_in = sin²(κL)
- 直通功率: P_through/P_in = cos²(κL)
- 完全耦合长度: L_c = π/(2κ)

来源：
- Yariv & Yeh 1984 Optical Waves in Crystals Wiley Ch.13（耦合模理论）
  https://www.wiley.com/en-us/Optical+Waves+in+Crystals
- Soldano & Pennings 1995 JLT（MMI/耦合器）
- SiPANN directional_coupler https://sipann.readthedocs.io/

运行: PYTHONPATH=src python examples/directional_coupler.py
"""

from __future__ import annotations

import numpy as np

from polaris.sim.models import directional_coupler_s


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
            wl=wl, coupling=coupling, length=10.0, gap=0.2, neff=2.4
        )
        # 端口: in1, in2, out1, out2（交叉耦合 out2←in1）
        p_through = float(np.abs(s[("out1", "in1")]) ** 2)
        p_cross = float(np.abs(s[("out2", "in1")]) ** 2)
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
    s_3db = directional_coupler_s(wl=1.55, coupling=0.5, length=10.0)
    print(f"  直通功率: {float(np.abs(s_3db[('out1','in1')])**2):.4f}")
    print(f"  交叉功率: {float(np.abs(s_3db[('out2','in1')])**2):.4f}")
    print(f"  总功率守恒: "
          f"{float(np.abs(s_3db[('out1','in1')])**2 + np.abs(s_3db[('out2','in1')])**2):.4f}")


if __name__ == "__main__":
    main()
