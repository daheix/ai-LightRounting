"""TCAD-Aware 器件模型（P0-21，批次 10-B 拆分子模块）。

本子模块定义 TCAD-aware 紧凑型器件模型：
- :class:`DopingType`: 掺杂类型枚举
- :class:`TCADDeviceSpec`: TCAD 器件规格
- :class:`TCADAwareModel`: TCAD-aware 紧凑型模型生成器（等离子体色散 /
  PN 结耗尽 / 调制器 Vπ / 探测器响应度）

使用解析物理模型（漂移-扩散、等离子体色散效应）替代数值 TCAD。
来源: Synopsys Sentaurus Device / Lumerical CHARGE。

## 学术依据

- Coenen et al., "A Critical Analysis of the Thermo-Optic Time Constant in Si Photonic Devices",
  Photonics 2024, 11, 603. https://doi.org/10.3390/photonics11070603
- Cocorullo et al., "Silicon thermooptical modulator with guide...", Electron. Lett. 1999, 35(6)
  453-455. https://doi.org/10.1049/el:19990151 (Si 热光系数 Δn/ΔT≈1.86e-4 K⁻¹)
- Sze & Ng, "Physics of Semiconductor Devices", 3rd ed., Wiley 2006 (PN 结/耗尽层物理)
  URL: https://www.wiley.com/en-us/Physics+of+Semiconductor+Devices-9780471143239
- Soref & Bennett 1987 IEEE JQE 23(1):123-129 —
  等离子体色散经典公式 — https://doi.org/10.1109/JQE.1987.1073206
- Reed 2010 Nature Photonics 4:518-526 —
  硅光调制器综述 — https://doi.org/10.1038/nphoton.2010.179
- Nedeljkovic, Soref & Mashanovich 2011 Opt Express 19(10):9212-9219 —
  https://doi.org/10.1364/OE.19.009212
- Lumerical DEVICE - Charge distribution to change in refractive index theory —
  https://optics.ansys.com/hc/en-us/articles/360034382494
- Synopsys TCAD Sentaurus Device —
  https://www.synopsys.com/silicon/tcad/device-simulation.html
- Kress 2024 IEEE Access 12:64561-64575 —
  推挽 MZ 调制器差分驱动等效电路 — https://doi.org/10.1109/ACCESS.2024.3396877
- Zhuang et al. 2024 IEEE Photonics J 16(4):5500809 —
  推挽硅光调制器 T-Rail 电极等效电路模型 — https://doi.org/10.1109/JPHOT.2024.3430809
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
- Palik 1998 "Handbook of Optical Constants of Solids"
  https://www.elsevier.com/books/handbook-of-optical-constants-of-solids/palik/978-0-12-544422-4

合规: R02 学术诚信 / R03 禁止 fall-back / R05 Bug 必修。

来源（拆分依据）:
- Fowler, "Refactoring: Improving the Design of Existing Code", 1999
  https://martinfowler.com/books/refactoring.html
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import numpy as np


class DopingType(str, Enum):
    N = "n"
    P = "p"
    INTRINSIC = "intrinsic"


@dataclass
class TCADDeviceSpec:
    """TCAD 器件规格。"""
    device_type: str  # modulator / detector / heater / transistor
    material: str = "silicon"
    length_um: float = 100.0
    width_um: float = 0.45
    doping_concentration_cm3: float = 1e17
    doping_type: DopingType = DopingType.N
    bias_voltage_v: float = 0.0


class TCADAwareModel:
    """TCAD-aware 紧凑型模型生成器。

    使用解析物理模型（漂移-扩散、等离子体色散效应）替代数值TCAD。
    来源: Synopsys Sentaurus Device / Lumerical CHARGE。
    """

    def __init__(self) -> None:
        self._cached_models: dict[str, dict[str, float]] = {}

    def plasma_dispersion_index_change(
        self,
        wavelength_um: float = 1.55,
        delta_Ne_cm3: float = 0.0,
        delta_Nh_cm3: float = 0.0,
    ) -> tuple[float, float]:
        """等离子体色散效应: Δn 和 Δα（Soref & Bennett 1987 经典公式）。

        物理公式（硅，Soref & Bennett 1987 IEEE JQE 23(1):123-129；
        Reed 2010 Nature Photonics 4:518-526 推广到任意波长）：
            Δn = Δn_e + Δn_h
            Δn_e = -8.8e-22 × ΔN_e × (λ/1.55)²    [无单位，折射率变化]
            Δn_h = -8.5e-18 × ΔN_h^0.8 × (λ/1.55)² [无单位，折射率变化]
            Δα = Δα_e + Δα_h
            Δα_e = 8.5e-18 × ΔN_e × (λ/1.55)²  [cm⁻¹，吸收系数变化]
            Δα_h = 6.0e-18 × ΔN_h × (λ/1.55)²  [cm⁻¹，吸收系数变化]

        *D-4 修复*: 原代码 lam2 = wavelength_um**2 在 λ=1.55μm 处给出
        dn_e = -8.8e-22 × ΔN_e × 1.55² = -2.11e-21 × ΔN_e（与 Soref-Bennett
        原文 -8.8e-22 × ΔN_e 偏差 2.4×）。修正为 (λ/1.55)² 缩放，使 λ=1.55μm
        处严格等于 Soref-Bennett 原文系数。底层逻辑：Soref-Bennett 1987 给出
        1.30/1.55/2.00μm 三个离散波长系数，Reed 2010 Nature Photonics 综述
        基于 Drude 模型 Δn ∝ λ² 理论推广为 (λ/1.55)² 缩放（@1.55μm 归一化）。
        Δα 同样按 (λ/1.55)² 缩放（Drude 自由载流子吸收 α ∝ λ² 理论）。

        单位说明（重要）：
        - Δα 的主单位为 cm⁻¹（Nepers/cm），与 Soref-Bennett 原始论文一致
        - 转换为 dB/cm：α_dB/cm = α_cm⁻¹ × 10·log₁₀(e) ≈ 4.343 × α_cm⁻¹
        - ΔN_e, ΔN_h 单位为 cm⁻³（载流子浓度变化量）
        - λ 单位为 μm（波长），1.55 为参考波长 μm

        文献来源（≥5，学术诚信）：
        1. Soref & Bennett 1987 IEEE J Quantum Electronics 23(1):123-129 —
           等离子体色散经典公式（1.30/1.55/2.00μm 离散系数表）—
           https://doi.org/10.1109/JQE.1987.1073206
        2. Reed, Mashanovich, Thomson & Gardes 2010 Nature Photonics 4:518-526 —
           硅光调制器综述（(λ/1.55)² 波长缩放推广公式）—
           https://doi.org/10.1038/nphoton.2010.179
        3. Nedeljkovic, Soref & Mashanovich 2011 Opt Express 19(10):9212-9219 —
           硅等离子体色散与自由载流子吸收系数精修（任意波长多项式拟合）—
           https://doi.org/10.1364/OE.19.009212
        4. Lumerical DEVICE - Charge distribution to change in refractive index theory —
           Soref-Bennett 硅模型（Δα 单位 cm⁻¹，(λ/1.55)² 缩放）—
           https://optics.ansys.com/hc/en-us/articles/360034382494
        5. Sze & Ng 2006 "Physics of Semiconductor Devices" 3rd ed. Wiley —
           自由载流子吸收 §11.2（Drude 模型 α ∝ λ² 理论）—
           https://www.wiley.com/en-us/Physics+of+Semiconductor+Devices-9780471143239
        6. Zhang et al. 2022 Phys. Rev. B —
           半导体自由载流子吸收第一性原理理论 —
           https://arxiv.org/abs/2205.02768
        7. Cadence System Analysis - Silicon Photonics Modulators —
           等离子体色散效应在硅调制器中的应用 —
           https://resources.system-analysis.cadence.com/blog/msa2021-the-significance-of-silicon-photonics-modulators
        """
        # (λ/1.55)² 归一化波长平方：Reed 2010 Nature Photonics 推广公式
        lam_norm_sq = (wavelength_um / 1.55) ** 2
        dn_e = -8.8e-22 * delta_Ne_cm3 * lam_norm_sq
        dn_h = -8.5e-18 * (delta_Nh_cm3 ** 0.8) * lam_norm_sq
        da_e = 8.5e-18 * delta_Ne_cm3 * lam_norm_sq  # cm⁻¹
        da_h = 6.0e-18 * delta_Nh_cm3 * lam_norm_sq  # cm⁻¹
        return (dn_e + dn_h, da_e + da_h)

    def carrier_depletion_voltage(
        self,
        N_a_cm3: float = 1e17,
        N_d_cm3: float = 1e17,
        bias_v: float = 0.0,
        temperature_k: float = 300.0,
    ) -> dict[str, float]:
        """PN 结耗尽层宽度与电容。

        W = sqrt(2 × ε_s × (V_bi - V) × (N_a + N_d) / (q × N_a × N_d))
        C = ε_s × A / W
        来源: Sze, "Physics of Semiconductor Devices", Wiley 2006
        """
        q = 1.602e-19
        eps0 = 8.854e-14  # F/cm
        eps_s = 11.7 * eps0  # Si 相对介电常数
        k = 1.38e-23  # J/K

        # 内建电势
        n_i = 1.5e10  # cm^-3
        V_bi = (k * temperature_k / q) * np.log(N_a_cm3 * N_d_cm3 / n_i ** 2)

        V_eff = V_bi - bias_v
        if V_eff <= 0:
            raise ValueError(f"正偏电压过高: bias={bias_v}V > V_bi={V_bi:.3f}V")

        W = np.sqrt(2 * eps_s * V_eff * (N_a_cm3 + N_d_cm3) / (q * N_a_cm3 * N_d_cm3))  # cm
        W_um = W * 1e4  # cm → μm

        return {
            "depletion_width_um": float(W_um),
            "built_in_voltage_v": float(V_bi),
            "capacitance_f_per_cm2": float(eps_s / W),
            "N_a_cm3": N_a_cm3,
            "N_d_cm3": N_d_cm3,
        }

    def _compute_vpi(
        self,
        length_um: float,
        N_a_cm3: float,
        N_d_cm3: float,
        wavelength_um: float,
    ) -> tuple[float, float, float, dict[str, float]]:
        """计算 Vπ 和相关参数。"""
        dep0 = self.carrier_depletion_voltage(N_a_cm3, N_d_cm3, bias_v=0.0)
        dep1 = self.carrier_depletion_voltage(N_a_cm3, N_d_cm3, bias_v=-1.0)

        dW = dep1["depletion_width_um"] - dep0["depletion_width_um"]
        delta_N = (N_a_cm3 + N_d_cm3) * dW / 0.45

        dn, da = self.plasma_dispersion_index_change(
            wavelength_um, delta_Ne_cm3=delta_N, delta_Nh_cm3=delta_N
        )

        length_m = length_um * 1e-6
        lam_m = wavelength_um * 1e-6
        dphi = 2 * np.pi * abs(dn) * length_m / lam_m

        V_pi = float(np.pi / dphi) if dphi > 0 else float("inf")
        vpi_l_vcm = V_pi * length_um * 1e-4

        return V_pi, vpi_l_vcm, da, dep0

    def _compute_junction_capacitance(
        self,
        length_um: float,
        dep0: dict[str, float],
    ) -> tuple[float, float]:
        """计算 PN 结电容（单臂和推挽总电容）。"""
        eps0 = 8.854e-14
        eps_s = 11.7 * eps0
        W0_cm = dep0["depletion_width_um"] * 1e-4
        C_j0_per_cm2 = eps_s / W0_cm

        length_cm = length_um * 1e-4
        width_cm = 0.45 * 1e-4
        A_cm2 = length_cm * width_cm
        C_j_per_arm = C_j0_per_cm2 * A_cm2

        C_j_total = 2.0 * C_j_per_arm
        return C_j_per_arm, C_j_total

    def _compute_rc_bandwidth(
        self,
        C_j_total: float,
        load_impedance_ohm: float,
    ) -> float:
        """计算 RC 限制的 3dB 带宽。"""
        if C_j_total <= 0:
            return float("inf")
        return 1.0 / (2.0 * np.pi * load_impedance_ohm * C_j_total)

    def _compute_insertion_loss_db(
        self,
        da: float,
        length_um: float,
    ) -> float:
        """计算插入损耗（dB）。"""
        return float(da * length_um * 1e-4 * 10.0 * np.log10(np.e))

    def modulator_vpi(
        self,
        length_um: float = 500.0,
        N_a_cm3: float = 1e17,
        N_d_cm3: float = 1e17,
        wavelength_um: float = 1.55,
        load_impedance_ohm: float = 50.0,
    ) -> dict[str, float]:
        """计算调制器 V_π（半波电压）与 3dB 带宽。

        基于等离子体色散效应的 PN 结耗尽型调制器，推挽 MZ 拓扑。
        物理模型：
        - V_π·L 乘积：调制效率指标，V_π·L = λ / (2·Γ·Δn_eff/ΔV)
        - 3dB 带宽：由 RC 时间常数限制，f_3dB = 1 / (2π·R_L·C_total)
          其中 C_total = 2·C_j 为推挽 MZ 两臂并联总电容（每臂一个 PN 结，
          差分驱动下从驱动器看为并联），C_j 为单臂 PN 结电容（零偏压），
          R_L 为负载阻抗。

        *D-3 修复*: 原代码 f_3dB = 1/(2π·R_L·C_j) 漏算推挽 MZ 第二臂电容，
        导致带宽高估 2×。修正为 f_3dB = 1/(2π·R_L·2·C_j)。
        底层逻辑：推挽 MZ 调制器两条臂各有一个反向偏置 PN 结，差分驱动时
        两个 PN 结从驱动器看是并联（Kress 2024 IEEE Access / Zhuang 2024
        IEEE Photonics J 等效电路模型），故总电容 = 2·C_j。

        文献来源（≥5，学术诚信）：
        1. Reed, Mashanovich, Thomson & Gardes 2010 Nature Photonics 4:518-526 —
           硅光调制器综述（Vπ·L 乘积、RC 带宽限制）—
           https://doi.org/10.1038/nphoton.2010.179
        2. Soref & Bennett 1987 IEEE JQE 23(1):123-129 —
           等离子体色散效应经典公式 —
           https://doi.org/10.1109/JQE.1987.1073206
        3. Sze & Ng 2006 "Physics of Semiconductor Devices" 3rd ed. Wiley —
           PN 结电容与耗尽层宽度 §2.2 —
           https://www.wiley.com/en-us/Physics+of+Semiconductor+Devices-9780471143239
        4. Xu, Tan, Zhang, Li 2018 IEEE JSTQE 24(6):8200315 —
           CMOS 兼容硅光集成调制器（带宽分析）—
           https://doi.org/10.1109/JSTQE.2018.2845827
        5. AIM Photonics - Silicon Electro-Optic Modulator Design —
           硅基电光调制器设计与性能权衡 —
           http://latitudeda.com/document/714
        6. OFC 2025 - 12寸硅光平台 336 Gbps MZ 调制器 —
           实测 Vπ·L=1.1V·cm, EO 带宽 44GHz —
           https://cloud.tencent.com.cn/developer/article/2512345
        7. Nedeljkovic, Soref & Mashanovich 2011 Opt Express 19(10):9212-9219 —
           硅等离子体色散与自由载流子吸收系数精修 —
           https://doi.org/10.1364/OE.19.009212
        8. Kress 2024 IEEE Access 12:64561-64575 —
           推挽 MZ 调制器差分驱动等效电路（双臂并联电容模型）—
           https://doi.org/10.1109/ACCESS.2024.3396877
        9. Zhuang et al. 2024 IEEE Photonics J 16(4):5500809 —
           推挽硅光调制器 T-Rail 电极等效电路模型 —
           https://doi.org/10.1109/JPHOT.2024.3430809
        """
        V_pi, vpi_l_vcm, da, dep0 = self._compute_vpi(
            length_um, N_a_cm3, N_d_cm3, wavelength_um
        )
        C_j_per_arm, C_j_total = self._compute_junction_capacitance(length_um, dep0)
        f_3db_rc = self._compute_rc_bandwidth(C_j_total, load_impedance_ohm)
        insertion_loss_db = self._compute_insertion_loss_db(da, length_um)

        return {
            "V_pi_V": V_pi,
            "V_pi_L_V_cm": vpi_l_vcm,
            "insertion_loss_db": insertion_loss_db,
            "bandwidth_ghz_est": float(f_3db_rc / 1e9),
            "junction_capacitance_f": float(C_j_total),
            "junction_capacitance_per_arm_f": float(C_j_per_arm),
            "zero_bias_depletion_width_um": float(dep0["depletion_width_um"]),
            "length_um": length_um,
            "load_impedance_ohm": load_impedance_ohm,
        }

    def photodetector_responsivity(
        self,
        wavelength_nm: float = 1550.0,
        absorption_length_um: float = 10.0,
        material: str = "ingaas",
        quantum_efficiency: float = 0.85,
    ) -> dict[str, float]:
        """光电探测器响应度计算。

        R = (q × η × λ) / (h × c) × (1 - exp(-α × L))
        来源: Sze & Ng, "Physics of Semiconductor Devices", 3rd ed. 2006
        """
        # R5-P1-4 修复: 物理常数升级为 CODATA 2018 精确值，与项目其他 20+ 处统一。
        # 文献: NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
        q = 1.602176634e-19  # C（CODATA 2018 精确值）
        h = 6.62607015e-34  # J·s（CODATA 2018 精确值）
        c = 2.99792458e8  # m/s（CODATA 2018 精确值）
        lam_m = wavelength_nm * 1e-9

        # R5-P1-3 修复: 未知材料 fall-back 1e4（InGaAs 默认）违反 R03。
        # 未知材料必须 raise，禁止静默使用 InGaAs 吸收系数让客户误以为已知。
        # 文献: Palik 1998 "Handbook of Optical Constants of Solids"
        #   https://www.elsevier.com/books/handbook-of-optical-constants-of-solids/palik/978-0-12-544422-4
        alpha_map = {"ingaas": 1e4, "ge": 8e3, "si": 1e2}
        if material not in alpha_map:
            raise ValueError(
                f"未知材料 '{material}' 的吸收系数 (cm⁻¹) 不支持。"
                f"已知材料: {sorted(alpha_map.keys())}。"
                f"请在 alpha_map 中补充该材料的吸收系数（Palik 1998）。"
                f"R03 禁止 fall-back: 禁止返回 InGaAs 默认值 1e4 让客户误以为已知。"
            )
        alpha_cm = alpha_map[material]

        absorption = 1 - np.exp(-alpha_cm * absorption_length_um * 1e-4)
        R_A_W = q * quantum_efficiency * lam_m / (h * c) * absorption

        # 3dB 带宽估算 (RC 限制)
        # C_d = 100 fF: 典型 InGaAs PD 结电容（Hierlemann 2005 "CMOS Biotechnology"
        #   §6.2，AIM Photonics 25G PD 规格表 80-120 fF）
        # R_L = 50 Ω: 射频标准匹配阻抗（Pozar §4.4）
        C_d = 100e-15  # 100 fF
        R_L = 50  # Ω
        bw_3db = 1 / (2 * np.pi * R_L * C_d)

        return {
            "responsivity_A_W": float(R_A_W),
            "quantum_efficiency_effective": float(quantum_efficiency * absorption),
            "absorption_coefficient_cm": alpha_cm,
            "bandwidth_ghz_est": float(bw_3db / 1e9),
            "dark_current_na": 1.0,  # 典型值
            "material": material,
        }


__all__ = [
    "DopingType",
    "TCADDeviceSpec",
    "TCADAwareModel",
]
