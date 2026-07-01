"""P0-21~P0-25: TCAD-aware + 热仿真 + 封装设计 + 测试芯片 + M3 交付。

五个模块合并单文件，对齐 Lumerical HEAT / ANSYS Icepak / Synopsys Sentinel。

学术依据:
- Coenen et al., "A Critical Analysis of the Thermo-Optic Time Constant in Si Photonic Devices",
  Photonics 2024, 11, 603. https://doi.org/10.3390/photonics11070603
- Cocorullo et al., "Silicon thermooptical modulator with guide...", Electron. Lett. 1999, 35(6)
  453-455. https://doi.org/10.1049/el:19990151 (Si 热光系数 Δn/ΔT≈1.86e-4 K⁻¹)
- Sze & Ng, "Physics of Semiconductor Devices", 3rd ed., Wiley 2006 (PN 结/耗尽层物理)
  URL: https://www.wiley.com/en-us/Physics+of+Semiconductor+Devices-9780471143239
- Taflove & Hagness, "Computational Electrodynamics: The FDTD Method", 3rd ed., Artech 2005
  URL: https://us.artechhouse.com/Computational-Electrodynamics-The-FDTD-Method-Third-Edition-P1815.aspx
  (有限差分离散原理适用于热传导 FDM 求解)
- Scharfetter & Gummel, "Large-signal analysis of a silicon Read diode oscillator",
  IEEE Trans. Electron Devices 1969, 16(1) 64-77.
  https://doi.org/10.1109/T-ED.1969.16767 (界面变量连续的差分离散思想)
- Selberherr, "Analysis and Simulation of Semiconductor Devices", Springer 1984
  URL: https://link.springer.com/book/10.1007/978-3-7091-8752-4 (变系数扩散方程 FDM)
- Incropera & DeWitt, "Fundamentals of Heat and Mass Transfer", Wiley
  URL: https://www.wiley.com/en-us/Fundamentals+of+Heat+and+Mass+Transfer (§4.4 界面调和平均)
- Carslaw & Jaeger, "Conduction of Heat in Solids", 2nd ed., Oxford 1959, §10.4
  URL: https://global.oup.com/academic/product/conduction-of-heat-in-solids-9780198533689
  (2D 线热源 Green's 函数 ΔT=(P'/2πk)·ln(r_ref/r))
- Lumerical HEAT - Modeling thermal crosstalk in photonic circuit simulation
  URL: https://optics.ansys.com/hc/en-us/articles/47617107334291
- Photon Design FIMMWAVE Thermo-Optic Solver
  URL: https://photond.com/fimmwave/features/thermo-optic-solver
- Radulaski et al., "Thermally tunable hybrid photonic architecture", arXiv:1803.03591 2018
- Synopsys TCAD Sentaurus Device
  URL: https://www.synopsys.com/silicon/tcad/device-simulation.html
- scipy.sparse.linalg.spsolve
  URL: https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.spsolve.html
- IEEE P1687 IJTAG test infrastructure
  URL: https://standards.ieee.org/standard/1687-2014.html
- JEDEC JESD22 可靠性测试标准
  URL: https://www.jedec.org/standards-documents/results/term/213
- NIST CODATA 2018 物理常数精确值（探测器响应度计算 photodetector_responsivity 使用）:
  q=1.602176634e-19 C, h=6.62607015e-34 J·s, c=2.99792458e8 m/s
  URL: https://physics.nist.gov/cuu/Constants/

合规: R02 学术诚信 / R03 禁止 fall-back / R05 Bug 必修。
v3.3-P0-B 修复: ThermalSolver2D.solve_steady_state 实现真 2D 稳态 FDM（替换虚标解析近似），
thermal_crosstalk_matrix 用 Carslaw-Jaeger 线热源 Green's 函数（替换魔法数 0.5/15.0）。

批次 10-B 拆分说明（2026-07-01）:
    原文件 1257 行超过质量门禁（AGENTS.md §8 文件 ≤ 800 行），按 Extract Module
    模式拆分为 5 个子模块，本文件作为瘦壳 re-export 公共符号以保持向后兼容：
    - polaris.device.tcad_thermal_tcad_model: DopingType/TCADDeviceSpec/TCADAwareModel
      （等离子体色散 / PN 结耗尽 / 调制器 Vπ / 探测器响应度）
    - polaris.device.tcad_thermal_solver: ThermalLayer/ThermalSolver2D
      （2D 稳态/瞬态热传导 FDM + Carslaw-Jaeger 热串扰矩阵）
    - polaris.device.tcad_thermal_packaging: PackageType/PackageSpec/PackageDesigner
      （热预算 / 耦合损耗估算 / IO 计数）
    - polaris.device.tcad_thermal_testchip: TestType/TestStructure/TestChipDesigner
      （11 种标准测试结构 + 布图 + 测试计划）
    - polaris.device.tcad_thermal_m3: M3Deliverable（M3 里程碑交付物检查清单）

来源:
- Fowler, "Refactoring: Improving the Design of Existing Code", 1999
  https://martinfowler.com/books/refactoring.html
"""

from __future__ import annotations

# 批次 10-B: 从拆分后的子模块 re-export 公共符号（保持向后兼容）。
# 任何外部代码 `from polaris.device.tcad_thermal_package import X`
# 仍可直接使用，无需修改 import 路径。
from polaris.device.tcad_thermal_tcad_model import (
    DopingType,
    TCADAwareModel,
    TCADDeviceSpec,
)
from polaris.device.tcad_thermal_solver import (
    ThermalLayer,
    ThermalSolver2D,
)
from polaris.device.tcad_thermal_packaging import (
    PackageDesigner,
    PackageSpec,
    PackageType,
)
from polaris.device.tcad_thermal_testchip import (
    TestChipDesigner,
    TestStructure,
    TestType,
)
from polaris.device.tcad_thermal_m3 import M3Deliverable

__all__ = [
    # TCAD-Aware 器件模型
    "DopingType",
    "TCADDeviceSpec",
    "TCADAwareModel",
    # 热仿真引擎
    "ThermalLayer",
    "ThermalSolver2D",
    # 封装设计
    "PackageType",
    "PackageSpec",
    "PackageDesigner",
    # 测试芯片设计
    "TestType",
    "TestStructure",
    "TestChipDesigner",
    # M3 交付
    "M3Deliverable",
]


# =============================================================================
# 单元测试（冒烟测试，保留入口）
# =============================================================================

def _test() -> None:
    """冒烟测试。"""
    # Test 1: TCAD-Aware
    tcad = TCADAwareModel()
    # 等离子体色散
    dn, da = tcad.plasma_dispersion_index_change(
        1.55, delta_Ne_cm3=1e17, delta_Nh_cm3=1e17
    )
    assert dn < 0
    assert da > 0
    # PN 结
    pn = tcad.carrier_depletion_voltage(N_a_cm3=1e17, N_d_cm3=1e17, bias_v=-2.0)
    assert pn["depletion_width_um"] > 0
    assert pn["built_in_voltage_v"] > 0
    # 调制器 Vpi
    mod = tcad.modulator_vpi(length_um=500.0)
    assert mod["V_pi_V"] > 0
    # 探测器
    pd = tcad.photodetector_responsivity(1550.0, 10.0, "ingaas", 0.85)
    assert pd["responsivity_A_W"] > 0.5
    print(f"TCAD: Vπ={mod['V_pi_V']:.2f}V ({mod['V_pi_L_V_cm']:.3f}V·cm), "
          f"PD R={pd['responsivity_A_W']:.3f}A/W, BW={pd['bandwidth_ghz_est']:.1f}GHz")

    # Test 2: Thermal Solver
    layers = [
        ThermalLayer("substrate", 500.0, 148.0),  # Si 衬底
        ThermalLayer("buried_oxide", 2.0, 1.4),  # BOX
        ThermalLayer("waveguide", 0.22, 148.0),  # Si 波导
        ThermalLayer("upper_cladding", 1.0, 1.4),  # SiO2 上包层
        ThermalLayer("heater", 0.1, 1.0, True, 0.5),  # TiN 加热器 (mW/μm)
    ]
    ts = ThermalSolver2D(layers, width_um=20.0, nx=40)
    T = ts.solve_steady_state(max_iter=2000)
    T_max = ts.max_temperature_k()
    T_wg = ts.avg_temp_at_layer("waveguide")
    assert T_max > 300
    assert T_wg > 300
    # 热串扰矩阵
    heaters = [0.0, 50.0, 100.0]
    devices = [25.0, 75.0, 125.0]
    crosstalk = ts.thermal_crosstalk_matrix(heaters, devices, heater_power_mw=10.0)
    assert crosstalk.shape == (3, 3)
    print(f"Thermal: T_max={T_max:.1f}K (Δ={T_max-300:.1f}K), "
          f"T_wg={T_wg:.1f}K, 热串扰矩阵形状={crosstalk.shape}")

    # Test 3: Package Design
    pkg = PackageDesigner()
    spec = PackageSpec(
        package_type=PackageType.PHOTONIC_PACKAGE,
        pin_count=48, body_size_mm=8.0,
        thermal_resistance_jc_K_W=8.0,
        fiber_count=4, has_hermetic=True,
    )
    budget = pkg.thermal_budget(spec, chip_power_w=0.5, ambient_temp_c=25.0)
    assert budget["pass"]
    loss = pkg.estimate_insertion_loss_db(4, "grating")
    io = pkg.io_count_summary(spec)
    print(f"Package: T_j={budget['T_junction_c']:.1f}°C, "
          f"裕量={budget['margin_c']:.1f}°C, "
          f"耦合损耗={loss['total_insertion_loss_db']:.1f}dB, "
          f"引脚={io['total_pins']}")

    # Test 4: Test Chip
    tc = TestChipDesigner()
    assert tc.total_structures >= 10
    area = tc.total_area_um2()
    fp = tc.floorplan((3000, 3000))
    plan = tc.test_plan()
    assert "DC" in plan
    assert "Optical" in plan
    print(f"TestChip: {tc.total_structures} 个结构, 总面积={area:.0f}μm², "
          f"利用率={fp['utilization']:.1%}, 5 大类测试")

    # Test 5: M3 交付检查
    m3 = M3Deliverable()
    rpt = m3.report()
    assert rpt["total_items"] >= 30
    assert rpt["completion_rate"] >= 0.9
    print(f"M3交付: {rpt['passed_items']}/{rpt['total_items']} 通过, "
          f"完成率={rpt['completion_rate']:.1%}, "
          f"目标得分={rpt['target_score']}")

    print("\n所有测试通过 ✅")


if __name__ == "__main__":
    _test()
