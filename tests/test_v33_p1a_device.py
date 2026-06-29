"""v3.3 P1-A 器件建模 Bug 修复回归测试。

覆盖 4 个 P1-A 算法 Bug 修复：
- D-2: 热串扰 Carslaw-Jaeger 镜像源法（r_ref = 2h）
- D-3: 推挽 MZ 调制器带宽公式（C_total = 2·C_j，f_3dB = 1/(2π·R_L·C_total)）
- D-4: Soref-Bennett (λ/1.55)² 波长缩放（替代错误的 λ²）
- D-6: ThermalSolver2D.solve_transient 瞬态热响应（委托 CrankNicolson2D）

学术诚信: 所有参数/公式源自权威文献：
- Carslaw & Jaeger 1959 "Conduction of Heat in Solids" §10.4 (iv) 镜像源法
  https://global.oup.com/academic/product/conduction-of-heat-in-solids-9780198533689
- Soref & Bennett 1987 IEEE JQE 23(1):123-129 等离子体色散经典公式
  https://doi.org/10.1109/JQE.1987.1073206
- Reed et al. 2010 Nature Photonics 4:518-526 (λ/1.55)² 波长推广
  https://doi.org/10.1038/nphoton.2010.179
- Kress 2024 IEEE Access 12:64561 推挽 MZ 等效电路
  https://doi.org/10.1109/ACCESS.2024.3396877
- Crank & Nicolson 1947 Proc. Camb. Phil. Soc. 43(1):50-67 隐式格式
  https://doi.org/10.1017/S0305004100023197
"""

from __future__ import annotations

import numpy as np
import pytest

from polaris.device.tcad_thermal_package import (
    TCADAwareModel,
    ThermalLayer,
    ThermalSolver2D,
)


# ===========================================================================
# D-2: 热串扰 Carslaw-Jaeger 镜像源法（r_ref = 2h）
# ===========================================================================
class TestD2ThermalCrosstalkMirrorSource:
    """D-2: Carslaw-Jaeger 镜像源法（r_ref = 2h）回归测试。

    修复内容: 原 r_ref = h（衬底厚度）→ 修正为 r_ref = 2h（热源到镜像源距离）。
    文献: Carslaw & Jaeger 1959 §10.4 (iv) 镜像源法 Green's 函数。
    """

    def _make_model(self) -> ThermalSolver2D:
        """构造含 Si 衬底的热模型（用于 Carslaw-Jaeger 公式测试）。"""
        layers = [
            ThermalLayer(name="BOX", thickness_um=2.0, thermal_conductivity_w_mk=1.4),
            ThermalLayer(name="Si_dev", thickness_um=0.22, thermal_conductivity_w_mk=148.0),
            ThermalLayer(
                name="Si_substrate", thickness_um=500.0, thermal_conductivity_w_mk=148.0
            ),
        ]
        return ThermalSolver2D(layers=layers, width_um=200.0, nx=200)

    def test_r_ref_is_2h_mirror_source(self) -> None:
        """r_ref = 2h（镜像源距离），不是 h（衬底厚度）。

        Carslaw-Jaeger §10.4 (iv) 镜像源法：热源在 z=+h，镜像源在 z=-h，
        两者距离 = 2h。原 bug r_ref = h 是错误的近似。
        """
        model = self._make_model()
        # Si 衬底层总厚度 h = 0.22 + 500 = 500.22 μm
        # r_ref = 2h = 1000.44 μm（镜像源法严格公式）
        h_um = 500.22
        r_ref_expected = 2.0 * h_um

        # 取 r1 = 5μm, r2 = 20μm，验证 ln(r_ref/r1)/ln(r_ref/r2) 比例
        r1, r2 = 5.0, 20.0
        matrix = model.thermal_crosstalk_matrix(
            heater_positions_um=[0.0],
            device_positions_um=[r1, r2],
            heater_power_mw=10.0,
            heater_length_um=50.0,
        )
        dT1, dT2 = matrix[0, 0], matrix[0, 1]
        expected_ratio = np.log(r_ref_expected / r1) / np.log(r_ref_expected / r2)
        actual_ratio = dT1 / dT2
        assert np.isclose(actual_ratio, expected_ratio, rtol=1e-6), (
            f"镜像源法 r_ref=2h 验证失败：实际比 {actual_ratio:.6f} ≠ "
            f"理论比 {expected_ratio:.6f}（r_ref={r_ref_expected}μm）"
        )

    def test_r_ref_not_h(self) -> None:
        """验证 r_ref ≠ h（原 bug 值）。"""
        model = self._make_model()
        h_um = 500.22
        r_ref_bug = h_um  # 原 bug: r_ref = h

        r1, r2 = 5.0, 20.0
        matrix = model.thermal_crosstalk_matrix(
            heater_positions_um=[0.0],
            device_positions_um=[r1, r2],
            heater_power_mw=10.0,
            heater_length_um=50.0,
        )
        dT1, dT2 = matrix[0, 0], matrix[0, 1]
        actual_ratio = dT1 / dT2
        buggy_ratio = np.log(r_ref_bug / r1) / np.log(r_ref_bug / r2)
        assert not np.isclose(actual_ratio, buggy_ratio, rtol=1e-3), (
            f"r_ref 仍为 h（原 bug）：实际比 {actual_ratio:.6f} ≈ "
            f"bug 比 {buggy_ratio:.6f}（r_ref=h={h_um}μm）"
        )

    def test_crosstalk_zero_beyond_2h(self) -> None:
        """距离 ≥ 2h 时串扰为 0（r_ref = 2h 镜像源距离）。"""
        model = self._make_model()
        # r_ref = 2 × 500.22 = 1000.44 μm
        # device 在 2000μm 远大于 r_ref
        matrix = model.thermal_crosstalk_matrix(
            heater_positions_um=[0.0],
            device_positions_um=[2000.0],
            heater_power_mw=10.0,
            heater_length_um=50.0,
        )
        assert matrix[0, 0] == 0.0, "距离 ≥ 2h 应无串扰"

    def test_no_magic_number_05(self) -> None:
        """验证无魔法数 0.5：自热温升不是 P×0.5。"""
        model = self._make_model()
        matrix = model.thermal_crosstalk_matrix(
            heater_positions_um=[0.0],
            device_positions_um=[0.0],
            heater_power_mw=10.0,
            heater_length_um=50.0,
        )
        dT = matrix[0, 0]
        assert not np.isclose(dT, 0.5 * 10.0, rtol=1e-3), (
            "仍使用魔法数 0.5！ΔT = 0.5 × P_mW"
        )

    def test_crosstalk_proportional_to_power(self) -> None:
        """热串扰与加热功率成正比（线性系统）。"""
        model = self._make_model()
        m1 = model.thermal_crosstalk_matrix(
            heater_positions_um=[0.0],
            device_positions_um=[10.0],
            heater_power_mw=5.0,
            heater_length_um=50.0,
        )
        m2 = model.thermal_crosstalk_matrix(
            heater_positions_um=[0.0],
            device_positions_um=[10.0],
            heater_power_mw=10.0,
            heater_length_um=50.0,
        )
        ratio = m2[0, 0] / m1[0, 0]
        assert np.isclose(ratio, 2.0, rtol=1e-10)


# ===========================================================================
# D-3: 推挽 MZ 调制器带宽公式（C_total = 2·C_j）
# ===========================================================================
class TestD3ModulatorVpiBandwidth:
    """D-3: 推挽 MZ 调制器带宽公式（2× 因子）回归测试。

    修复内容: 原 f_3dB = 1/(2π·R_L·C_j) → 修正为 f_3dB = 1/(2π·R_L·2·C_j)。
    文献: Kress 2024 IEEE Access / Zhuang 2024 IEEE Photonics J 推挽 MZ 等效电路。
    """

    def setup_method(self) -> None:
        self.pkg = TCADAwareModel()

    def test_total_capacitance_is_2x_per_arm(self) -> None:
        """推挽 MZ 总电容 = 2 × 单臂电容（两臂并联）。"""
        result = self.pkg.modulator_vpi(length_um=500.0)
        c_total = result["junction_capacitance_f"]
        c_per_arm = result["junction_capacitance_per_arm_f"]
        assert c_total > 0
        assert c_per_arm > 0
        assert np.isclose(c_total, 2.0 * c_per_arm, rtol=1e-15), (
            f"C_total={c_total} 应 = 2 × C_per_arm={c_per_arm}（推挽 MZ 并联）"
        )

    def test_bandwidth_uses_total_capacitance(self) -> None:
        """带宽公式使用 C_total = 2·C_j，而非单臂 C_j。

        f_3dB = 1 / (2π · R_L · C_total) = 1 / (2π · R_L · 2·C_j)
        """
        result = self.pkg.modulator_vpi(length_um=500.0, load_impedance_ohm=50.0)
        c_total = result["junction_capacitance_f"]
        r_l = result["load_impedance_ohm"]
        expected_bw_hz = 1.0 / (2.0 * np.pi * r_l * c_total)
        expected_bw_ghz = expected_bw_hz / 1e9
        assert np.isclose(
            result["bandwidth_ghz_est"], expected_bw_ghz, rtol=1e-10
        ), (
            f"带宽 {result['bandwidth_ghz_est']} GHz ≠ "
            f"1/(2π·R_L·C_total) = {expected_bw_ghz} GHz"
        )

    def test_bandwidth_half_of_single_arm_model(self) -> None:
        """推挽 MZ 带宽 = 单臂模型带宽 / 2（因 C_total = 2·C_j）。

        原 bug: f_3dB = 1/(2π·R_L·C_j)（漏算第二臂）
        修复后: f_3dB = 1/(2π·R_L·2·C_j) = 原 bug 带宽 / 2
        """
        result = self.pkg.modulator_vpi(length_um=500.0, load_impedance_ohm=50.0)
        c_per_arm = result["junction_capacitance_per_arm_f"]
        r_l = result["load_impedance_ohm"]
        # 原 bug 公式带宽（用单臂 C_j，漏算 2× 因子）
        buggy_bw_ghz = (1.0 / (2.0 * np.pi * r_l * c_per_arm)) / 1e9
        # 修复后带宽应 = 原 bug / 2
        assert np.isclose(
            result["bandwidth_ghz_est"], buggy_bw_ghz / 2.0, rtol=1e-10
        ), (
            f"修复后带宽 {result['bandwidth_ghz_est']} GHz 应 = "
            f"原 bug 带宽 / 2 = {buggy_bw_ghz / 2.0} GHz"
        )

    def test_bandwidth_rc_inverse_scaling(self) -> None:
        """带宽 ∝ 1/R_L：负载阻抗加倍 → 带宽减半。"""
        r1 = self.pkg.modulator_vpi(load_impedance_ohm=25.0)
        r2 = self.pkg.modulator_vpi(load_impedance_ohm=50.0)
        ratio = r1["bandwidth_ghz_est"] / r2["bandwidth_ghz_est"]
        assert np.isclose(ratio, 2.0, rtol=1e-10), (
            f"RC 反比关系失效：R=25Ω/R=50Ω 带宽比 = {ratio:.6f} ≠ 2.0"
        )

    def test_vpi_l_product_reasonable_range(self) -> None:
        """V_π·L 乘积应在 0.1~10.0 V·cm 范围（硅 PN 结调制器典型值）。"""
        result = self.pkg.modulator_vpi(length_um=500.0)
        vpi_l = result["V_pi_L_V_cm"]
        assert 0.1 <= vpi_l <= 10.0, f"V_π·L = {vpi_l} V·cm 超出合理范围"


# ===========================================================================
# D-4: Soref-Bennett (λ/1.55)² 波长缩放
# ===========================================================================
class TestD4PlasmaDispersionWavelengthScaling:
    """D-4: Soref-Bennett (λ/1.55)² 波长缩放回归测试。

    修复内容: 原 lam2 = wavelength_um**2 → 修正为 lam_norm_sq = (λ/1.55)²。
    文献: Soref & Bennett 1987 IEEE JQE / Reed 2010 Nature Photonics 推广公式。
    """

    def setup_method(self) -> None:
        self.pkg = TCADAwareModel()

    def test_at_1550nm_matches_soref_bennett_coefficient(self) -> None:
        """@1.55μm 处 Δn_e 严格等于 Soref-Bennett 原文系数 -8.8e-22 × ΔN_e。

        原 bug: lam2 = wavelength_um**2，@1.55μm 给出
                dn_e = -8.8e-22 × ΔN_e × 1.55² = -2.11e-21 × ΔN_e（偏差 2.4×）
        修复后: lam_norm_sq = (λ/1.55)²，@1.55μm 给出
                dn_e = -8.8e-22 × ΔN_e × 1 = -8.8e-22 × ΔN_e
        """
        delta_Ne = 1e17
        dn, da = self.pkg.plasma_dispersion_index_change(
            wavelength_um=1.55,
            delta_Ne_cm3=delta_Ne,
            delta_Nh_cm3=0.0,
        )
        expected_dn_e = -8.8e-22 * delta_Ne  # Soref-Bennett @1.55μm 严格值
        assert np.isclose(dn, expected_dn_e, rtol=1e-15), (
            f"@1.55μm: dn={dn} ≠ Soref-Bennett 系数 {expected_dn_e}"
            f"（原 bug 偏差 {abs(dn / expected_dn_e):.2f}×）"
        )

    def test_delta_alpha_at_1550nm_matches_soref_bennett(self) -> None:
        """@1.55μm 处 Δα 严格等于 Soref-Bennett 原文系数 8.5e-18 × ΔN_e。"""
        delta_Ne = 1e17
        dn, da = self.pkg.plasma_dispersion_index_change(
            wavelength_um=1.55,
            delta_Ne_cm3=delta_Ne,
            delta_Nh_cm3=0.0,
        )
        expected_da_e = 8.5e-18 * delta_Ne  # Soref-Bennett @1.55μm 严格值
        assert np.isclose(da, expected_da_e, rtol=1e-15), (
            f"@1.55μm: da={da} ≠ Soref-Bennett 系数 {expected_da_e}"
        )

    def test_delta_n_wavelength_squared_scaling(self) -> None:
        """Δn ∝ (λ/1.55)²（Reed 2010 Nature Photonics 推广公式）。"""
        dn1, _ = self.pkg.plasma_dispersion_index_change(
            wavelength_um=1.31, delta_Ne_cm3=1e17, delta_Nh_cm3=0.0
        )
        dn2, _ = self.pkg.plasma_dispersion_index_change(
            wavelength_um=1.55, delta_Ne_cm3=1e17, delta_Nh_cm3=0.0
        )
        ratio = abs(dn2) / abs(dn1)
        expected_ratio = (1.55 / 1.31) ** 2  # (λ2/λ1)² = (1.55/1.31)²
        assert np.isclose(ratio, expected_ratio, rtol=1e-10), (
            f"Δn (λ/1.55)² 缩放比 {ratio:.6f} ≠ (1.55/1.31)² = {expected_ratio:.6f}"
        )

    def test_delta_alpha_wavelength_squared_scaling(self) -> None:
        """Δα ∝ (λ/1.55)²（Drude 自由载流子吸收 α ∝ λ² 理论）。"""
        _, da1 = self.pkg.plasma_dispersion_index_change(
            wavelength_um=1.31, delta_Ne_cm3=1e17, delta_Nh_cm3=0.0
        )
        _, da2 = self.pkg.plasma_dispersion_index_change(
            wavelength_um=1.55, delta_Ne_cm3=1e17, delta_Nh_cm3=0.0
        )
        ratio = da2 / da1
        expected_ratio = (1.55 / 1.31) ** 2
        assert np.isclose(ratio, expected_ratio, rtol=1e-10), (
            f"Δα (λ/1.55)² 缩放比 {ratio:.6f} ≠ (1.55/1.31)² = {expected_ratio:.6f}"
        )

    def test_no_wavelength_um_squared_bug(self) -> None:
        """验证修复后 ≠ 原 bug 公式（wavelength_um**2 缩放）。"""
        delta_Ne = 1e17
        dn, _ = self.pkg.plasma_dispersion_index_change(
            wavelength_um=1.55,
            delta_Ne_cm3=delta_Ne,
            delta_Nh_cm3=0.0,
        )
        # 原 bug: dn_e = -8.8e-22 × ΔN_e × 1.55²
        buggy_dn_e = -8.8e-22 * delta_Ne * (1.55 ** 2)
        assert not np.isclose(dn, buggy_dn_e, rtol=1e-3), (
            f"仍使用 wavelength_um**2 缩放（原 bug）：dn={dn} ≈ bug 值 {buggy_dn_e}"
        )

    def test_zero_carriers_zero_change(self) -> None:
        """零载流子变化 → Δn=0, Δα=0。"""
        dn, da = self.pkg.plasma_dispersion_index_change(
            wavelength_um=1.55,
            delta_Ne_cm3=0.0,
            delta_Nh_cm3=0.0,
        )
        assert dn == 0.0
        assert da == 0.0

    def test_delta_n_sign_negative(self) -> None:
        """自由载流子增加 → 折射率降低（Δn < 0）。"""
        dn, da = self.pkg.plasma_dispersion_index_change(
            wavelength_um=1.55,
            delta_Ne_cm3=1e17,
            delta_Nh_cm3=1e17,
        )
        assert dn < 0
        assert da > 0


# ===========================================================================
# D-6: ThermalSolver2D.solve_transient 瞬态热响应
# ===========================================================================
class TestD6ThermalSolverTransient:
    """D-6: ThermalSolver2D.solve_transient 瞬态热响应回归测试。

    修复内容: ThermalSolver2D 原仅支持稳态，现添加 solve_transient 方法
    委托 transient_thermal.CrankNicolson2D 求解瞬态热传导。
    文献: Crank & Nicolson 1947 / Carslaw & Jaeger 1959 / Incropera §5.9。
    """

    def _make_solver(self) -> ThermalSolver2D:
        """构造含加热器的 2D 热求解器。"""
        layers = [
            ThermalLayer(
                name="substrate",
                thickness_um=50.0,
                thermal_conductivity_w_mk=148.0,
                density_kg_m3=2330.0,
                specific_heat_j_kgk=700.0,
            ),
            ThermalLayer(
                name="heater",
                thickness_um=1.0,
                thermal_conductivity_w_mk=50.0,
                density_kg_m3=5000.0,
                specific_heat_j_kgk=700.0,
                is_heater=True,
                heater_power_mw_per_um=0.1,
            ),
        ]
        return ThermalSolver2D(
            layers=layers,
            width_um=20.0,
            substrate_temp_k=300.0,
            nx=11,
            heater_width_um=2.0,
        )

    def test_solve_transient_returns_times_and_temps(self) -> None:
        """solve_transient 返回 (times, temps) 元组，形状正确。"""
        solver = self._make_solver()
        times, temps = solver.solve_transient(
            total_time_s=1e-5,
            dt_s=1e-7,
            sample_interval_steps=10,
        )
        assert len(times) == temps.shape[0]
        assert len(times) > 1
        assert times[0] == 0.0
        assert temps.shape[1] == solver.nz
        assert temps.shape[2] == solver.nx

    def test_initial_temperature_is_ambient(self) -> None:
        """t=0 时温度场应等于衬底温度 300K。"""
        solver = self._make_solver()
        times, temps = solver.solve_transient(
            total_time_s=1e-6,
            dt_s=1e-7,
            sample_interval_steps=1,
        )
        assert np.all(temps[0] == 300.0), "t=0 温度场应等于衬底温度"

    def test_temperature_rises_with_heating(self) -> None:
        """加热后温度应上升（T_final > T_initial）。"""
        solver = self._make_solver()
        times, temps = solver.solve_transient(
            total_time_s=1e-5,
            dt_s=1e-7,
            sample_interval_steps=10,
        )
        T_initial_max = float(np.max(temps[0]))
        T_final_max = float(np.max(temps[-1]))
        assert T_final_max > T_initial_max, (
            f"加热后最高温度 {T_final_max}K 应 > 初始 {T_initial_max}K"
        )

    def test_bottom_boundary_fixed(self) -> None:
        """底部 Dirichlet 边界温度保持 300K。"""
        solver = self._make_solver()
        times, temps = solver.solve_transient(
            total_time_s=1e-5,
            dt_s=1e-7,
            sample_interval_steps=10,
        )
        # 底部行 (i=0) 应全部等于衬底温度
        assert np.all(temps[-1][0, :] == 300.0), "底部 Dirichlet 边界温度不恒定"

    def test_approaches_steady_state(self) -> None:
        """长时间加热后温升增量递减（趋近稳态）。"""
        solver = self._make_solver()
        times, temps = solver.solve_transient(
            total_time_s=5e-5,
            dt_s=1e-7,
            sample_interval_steps=20,
        )
        max_temps = [float(np.max(t)) for t in temps]
        deltas = [max_temps[i + 1] - max_temps[i] for i in range(len(max_temps) - 1)]
        # 温升增量应单调递减
        for i in range(len(deltas) - 1):
            assert deltas[i + 1] <= deltas[i] + 1e-10, (
                f"温升增量未递减：step {i} delta={deltas[i]:.6f}K, "
                f"step {i+1} delta={deltas[i+1]:.6f}K"
            )

    def test_invalid_total_time_raises(self) -> None:
        """非正 total_time_s 应 raise ValueError。"""
        solver = self._make_solver()
        with pytest.raises(ValueError, match="total_time_s"):
            solver.solve_transient(total_time_s=0.0)
        with pytest.raises(ValueError, match="total_time_s"):
            solver.solve_transient(total_time_s=-1.0)

    def test_invalid_dt_raises(self) -> None:
        """非正 dt_s 应 raise ValueError。"""
        solver = self._make_solver()
        with pytest.raises(ValueError, match="dt_s"):
            solver.solve_transient(total_time_s=1e-5, dt_s=0.0)

    def test_invalid_sample_interval_raises(self) -> None:
        """sample_interval_steps < 1 应 raise ValueError。"""
        solver = self._make_solver()
        with pytest.raises(ValueError, match="sample_interval_steps"):
            solver.solve_transient(total_time_s=1e-5, sample_interval_steps=0)

    def test_self_T_synced_after_transient(self) -> None:
        """solve_transient 后 self._T 应同步为最后一帧温度场。"""
        solver = self._make_solver()
        times, temps = solver.solve_transient(
            total_time_s=1e-5,
            dt_s=1e-7,
            sample_interval_steps=10,
        )
        assert np.allclose(solver._T, temps[-1]), (
            "solve_transient 后 self._T 未同步为最后一帧"
        )
        # max_temperature_k 应可正常调用
        T_max = solver.max_temperature_k()
        assert T_max > 300.0

    def test_thermal_layer_default_density_specific_heat(self) -> None:
        """ThermalLayer 默认 density=2330 (Si), specific_heat=700 (Si)。"""
        layer = ThermalLayer(name="Si", thickness_um=1.0, thermal_conductivity_w_mk=148.0)
        assert layer.density_kg_m3 == 2330.0
        assert layer.specific_heat_j_kgk == 700.0

    def test_thermal_layer_custom_density_specific_heat(self) -> None:
        """ThermalLayer 支持自定义 density/specific_heat（如 SiO2）。"""
        layer = ThermalLayer(
            name="SiO2",
            thickness_um=2.0,
            thermal_conductivity_w_mk=1.4,
            density_kg_m3=2200.0,
            specific_heat_j_kgk=730.0,
        )
        assert layer.density_kg_m3 == 2200.0
        assert layer.specific_heat_j_kgk == 730.0
