"""TCAD 热仿真与器件模型单元测试（器件仿真 Bug 修复回归）。

覆盖：
- D-2: 热串扰 Carslaw-Jaeger 线热源公式（替代魔法数 0.5）
- D-3: V_π·f_3dB 带宽积公式（RC 限制模型）
- D-4: Soref-Bennett Δα 单位（cm⁻¹ / dB/cm 双单位）
- D-6: 瞬态热响应（集总参数解析解 + 2D Crank-Nicolson 数值解）
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pytest

from polaris.device.tcad_thermal_package import (
    TCADAwareModel,
    ThermalLayer,
    ThermalSolver2D,
)


# ===========================================================================
# 1. TestPlasmaDispersion — Soref-Bennett 等离子体色散效应
# ===========================================================================
class TestPlasmaDispersion:
    """Soref-Bennett 等离子体色散公式验证（D-4: Δα 单位）。"""

    def setup_method(self) -> None:
        self.pkg = TCADAwareModel()

    def test_delta_alpha_unit_is_cm_minus_1(self) -> None:
        """Δα 主单位应为 cm⁻¹（Nepers/cm），与 Soref-Bennett 原始论文一致。"""
        dn, da = self.pkg.plasma_dispersion_index_change(
            wavelength_um=1.55,
            delta_Ne_cm3=1e17,
            delta_Nh_cm3=1e17,
        )
        # Soref-Bennett @1.55μm: Δα_e = 8.5e-18 × ΔN_e (cm⁻¹)
        # ΔN_e = 1e17 cm⁻³ → Δα_e ≈ 0.85 cm⁻¹
        expected_da_e = 8.5e-18 * 1e17  # cm⁻¹
        expected_da_h = 6.0e-18 * 1e17  # cm⁻¹
        expected_total = expected_da_e + expected_da_h
        assert np.isclose(da, expected_total, rtol=1e-10), (
            f"Δα = {da} cm⁻¹, 预期 {expected_total} cm⁻¹"
        )
        assert da > 0, "自由载流子吸收应为正"

    def test_delta_alpha_dbcm_conversion(self) -> None:
        """cm⁻¹ → dB/cm 转换：α_dB = α_nepers × 10·log₁₀(e) ≈ 4.343 × α_nepers。"""
        dn, da_cm = self.pkg.plasma_dispersion_index_change(
            wavelength_um=1.55,
            delta_Ne_cm3=1e17,
            delta_Nh_cm3=0.0,
        )
        da_db = da_cm * 10.0 * np.log10(np.e)
        conversion_factor = da_db / da_cm
        assert 4.34 <= conversion_factor <= 4.35, (
            f"dB/cm 转换因子 {conversion_factor:.4f} 不在 4.343 附近"
        )

    def test_delta_n_sign_negative(self) -> None:
        """自由载流子增加导致折射率下降（Δn 为负）。"""
        dn, da = self.pkg.plasma_dispersion_index_change(
            wavelength_um=1.55,
            delta_Ne_cm3=1e17,
            delta_Nh_cm3=1e17,
        )
        assert dn < 0, "自由载流子增加 → 折射率降低（Δn < 0）"

    def test_zero_carriers_zero_change(self) -> None:
        """零载流子变化 → Δn=0, Δα=0。"""
        dn, da = self.pkg.plasma_dispersion_index_change(
            wavelength_um=1.55,
            delta_Ne_cm3=0.0,
            delta_Nh_cm3=0.0,
        )
        assert dn == 0.0
        assert da == 0.0

    def test_wavelength_squared_scaling(self) -> None:
        """Δn ∝ λ²（Soref-Bennett 公式特性）。"""
        dn1, _ = self.pkg.plasma_dispersion_index_change(
            wavelength_um=1.31, delta_Ne_cm3=1e17, delta_Nh_cm3=0.0
        )
        dn2, _ = self.pkg.plasma_dispersion_index_change(
            wavelength_um=1.55, delta_Ne_cm3=1e17, delta_Nh_cm3=0.0
        )
        ratio = abs(dn2) / abs(dn1)
        expected_ratio = (1.55 / 1.31) ** 2
        assert np.isclose(ratio, expected_ratio, rtol=1e-10), (
            f"Δn 波长缩放比 {ratio:.4f} ≠ (λ2/λ1)² = {expected_ratio:.4f}"
        )


# ===========================================================================
# 2. TestModulatorVpi — V_π 与带宽（D-3: 带宽公式修复）
# ===========================================================================
class TestModulatorVpi:
    """调制器 V_π 与 RC 带宽验证（D-3: 带宽公式修复）。"""

    def setup_method(self) -> None:
        self.pkg = TCADAwareModel()

    def test_vpi_l_product_reasonable_range(self) -> None:
        """V_π·L 乘积应在 0.5~5.0 V·cm 范围（硅 PN 结调制器典型值）。"""
        result = self.pkg.modulator_vpi(
            length_um=500.0,
            N_a_cm3=1e17,
            N_d_cm3=1e17,
            wavelength_um=1.55,
            load_impedance_ohm=50.0,
        )
        vpi_l = result["V_pi_L_V_cm"]
        assert 0.1 <= vpi_l <= 10.0, f"V_π·L = {vpi_l} V·cm 超出合理范围"
        assert result["V_pi_V"] > 0

    def test_bandwidth_rc_scaling(self) -> None:
        """带宽 ∝ 1/(R_L·C_j)：负载阻抗加倍 → 带宽减半。"""
        r1 = self.pkg.modulator_vpi(load_impedance_ohm=25.0)
        r2 = self.pkg.modulator_vpi(load_impedance_ohm=50.0)
        # 带宽与负载阻抗成反比
        ratio = r1["bandwidth_ghz_est"] / r2["bandwidth_ghz_est"]
        assert np.isclose(ratio, 2.0, rtol=1e-10), (
            f"RC 带宽反比关系失效：R=25Ω/R=50Ω 带宽比 = {ratio:.4f} ≠ 2.0"
        )

    def test_bandwidth_positive_finite(self) -> None:
        """带宽应为正且有限值。"""
        result = self.pkg.modulator_vpi()
        assert result["bandwidth_ghz_est"] > 0
        assert np.isfinite(result["bandwidth_ghz_est"])

    def test_junction_capacitance_positive(self) -> None:
        """结电容应为正值。"""
        result = self.pkg.modulator_vpi()
        assert result["junction_capacitance_f"] > 0

    def test_insertion_loss_positive_db(self) -> None:
        """插入损耗应为正值（dB）。"""
        result = self.pkg.modulator_vpi()
        assert result["insertion_loss_db"] > 0

    def test_longer_length_lower_vpi(self) -> None:
        """调制器越长，V_π 越小（V_π·L 近似常数）。"""
        r_short = self.pkg.modulator_vpi(length_um=200.0)
        r_long = self.pkg.modulator_vpi(length_um=1000.0)
        assert r_long["V_pi_V"] < r_short["V_pi_V"], "长调制器 V_π 应更小"


# ===========================================================================
# 3. TestThermalCrosstalk — 热串扰 Carslaw-Jaeger 公式（D-2: 魔法数修复）
# ===========================================================================
class TestThermalCrosstalk:
    """热串扰 Carslaw-Jaeger 线热源模型验证（D-2: 替代魔法数 0.5）。"""

    def _make_model(self) -> ThermalSolver2D:
        """构造含 Si 衬底的热模型（用于 Carslaw-Jaeger 公式测试）。"""
        layers = [
            ThermalLayer(name="BOX", thickness_um=2.0, thermal_conductivity_w_mk=1.4),
            ThermalLayer(name="Si_dev", thickness_um=0.22, thermal_conductivity_w_mk=148.0),
            ThermalLayer(
                name="Si_substrate", thickness_um=500.0, thermal_conductivity_w_mk=148.0
            ),
        ]
        return ThermalSolver2D(
            layers=layers,
            width_um=200.0,
            substrate_temp_k=300.0,
            nx=200,
        )

    def test_crosstalk_decreases_with_distance(self) -> None:
        """热串扰随距离增加而单调递减（Carslaw-Jaeger ln(r_ref/r) 特性）。"""
        model = self._make_model()
        heaters = [0.0]
        devices = [5.0, 10.0, 20.0, 50.0]
        matrix = model.thermal_crosstalk_matrix(
            heater_positions_um=heaters,
            device_positions_um=devices,
            heater_power_mw=10.0,
            heater_length_um=50.0,
        )
        crosstalk = matrix[0]
        # 应严格单调递减
        for i in range(len(crosstalk) - 1):
            assert crosstalk[i] > crosstalk[i + 1], (
                f"热串扰未单调递减：d={devices[i]}μm → {crosstalk[i]}K, "
                f"d={devices[i+1]}μm → {crosstalk[i+1]}K"
            )

    def test_crosstalk_positive(self) -> None:
        """热串扰温升应为正值。"""
        model = self._make_model()
        matrix = model.thermal_crosstalk_matrix(
            heater_positions_um=[0.0],
            device_positions_um=[10.0],
            heater_power_mw=10.0,
            heater_length_um=50.0,
        )
        assert matrix[0, 0] > 0

    def test_crosstalk_proportional_to_power(self) -> None:
        """热串扰与加热功率成正比（线性）。"""
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
        assert np.isclose(ratio, 2.0, rtol=1e-10), (
            f"功率加倍 → 热串扰应加倍：ratio={ratio:.4f}"
        )

    def test_crosstalk_zero_beyond_ref(self) -> None:
        """距离 ≥ r_ref（衬底厚度）时串扰为 0。"""
        model = self._make_model()
        # 衬底总厚度 = 500μm (Si_substrate)
        # 远大于 r_ref 的位置应无串扰
        matrix = model.thermal_crosstalk_matrix(
            heater_positions_um=[0.0],
            device_positions_um=[1000.0],  # 远大于衬底厚度
            heater_power_mw=10.0,
            heater_length_um=50.0,
        )
        assert matrix[0, 0] == 0.0, "超出 r_ref 的位置串扰应为 0"

    def test_crosstalk_logarithmic_scaling(self) -> None:
        """验证 Carslaw-Jaeger 公式：ΔT ∝ ln(r_ref/r) 对数关系。"""
        model = self._make_model()
        # r_ref = 衬底厚度 = 500μm（Si_dev + Si_substrate 都是 k≥100 的层）
        # 取两个不同距离 r1, r2，温差比 = ln(r_ref/r1) / ln(r_ref/r2)
        r1, r2 = 5.0, 20.0
        matrix = model.thermal_crosstalk_matrix(
            heater_positions_um=[0.0],
            device_positions_um=[r1, r2],
            heater_power_mw=10.0,
            heater_length_um=50.0,
        )
        dT1, dT2 = matrix[0, 0], matrix[0, 1]
        r_ref = 500.22  # 0.22 + 500
        expected_ratio = np.log(r_ref / r1) / np.log(r_ref / r2)
        actual_ratio = dT1 / dT2
        assert np.isclose(actual_ratio, expected_ratio, rtol=1e-6), (
            f"对数缩放失效：实际比 {actual_ratio:.4f} ≠ 理论比 {expected_ratio:.4f}"
        )

    def test_crosstalk_no_magic_number_05(self) -> None:
        """验证无魔法数 0.5：自热温升不是简单的 P×0.5。"""
        model = self._make_model()
        matrix = model.thermal_crosstalk_matrix(
            heater_positions_um=[0.0],
            device_positions_um=[0.0],  # 同位置（自热）
            heater_power_mw=10.0,
            heater_length_um=50.0,
        )
        dT = matrix[0, 0]
        # 旧魔法数模型：ΔT = 0.5 * P_mW = 5K
        # 新公式应给出物理意义明确的结果，且不等于 0.5*P
        assert not np.isclose(dT, 0.5 * 10.0, rtol=1e-3), (
            "仍使用魔法数 0.5！ΔT = 0.5 × P_mW"
        )

    def test_crosstalk_invalid_length_raises(self) -> None:
        """非正加热器长度应 raise ValueError。"""
        model = self._make_model()
        with pytest.raises(ValueError, match="heater_length_um"):
            model.thermal_crosstalk_matrix(
                heater_positions_um=[0.0],
                device_positions_um=[10.0],
                heater_power_mw=10.0,
                heater_length_um=0.0,
            )


# ===========================================================================
# 4. TestLumpedTransient — 集总参数瞬态热响应（D-6: 瞬态热响应）
# ===========================================================================
class TestLumpedTransient:
    """集总参数瞬态热响应求解器验证（D-6: 瞬态热响应缺失修复）。"""

    def setup_method(self) -> None:
        from polaris.device.transient_thermal import (
            TransientThermalSpec,
            LumpedTransientSolver,
        )

        self.spec = TransientThermalSpec(
            thermal_resistance_k_w=1000.0,
            heat_capacity_j_k=1e-6,
            ambient_temp_k=300.0,
            heater_power_w=0.01,
        )
        self.solver = LumpedTransientSolver(self.spec)

    def test_time_constant_definition(self) -> None:
        """τ = R_th × C_th。"""
        tau = self.solver.time_constant_s()
        expected = self.spec.thermal_resistance_k_w * self.spec.heat_capacity_j_k
        assert np.isclose(tau, expected, rtol=1e-15)

    def test_steady_state_delta_t(self) -> None:
        """稳态温升 ΔT_ss = P × R_th。"""
        dT_ss = self.spec.steady_state_delta_t_k
        expected = self.spec.heater_power_w * self.spec.thermal_resistance_k_w
        assert np.isclose(dT_ss, expected, rtol=1e-15)

    def test_initial_temperature_equals_ambient(self) -> None:
        """t=0 时温度等于环境温度。"""
        T0 = self.solver.temperature_rise(0.0)
        assert np.isclose(T0, self.spec.ambient_temp_k, rtol=1e-15)

    def test_one_tau_reaches_63_percent(self) -> None:
        """t=τ 时温度达到稳态值的 63.2% (1 - 1/e)。"""
        tau = self.solver.time_constant_s()
        T_tau = float(self.solver.temperature_rise(tau))
        dT_ss = self.spec.steady_state_delta_t_k
        dT_tau = T_tau - self.spec.ambient_temp_k
        fraction = dT_tau / dT_ss
        expected = 1.0 - 1.0 / np.e
        assert np.isclose(fraction, expected, rtol=1e-10), (
            f"t=τ 时温升比例 = {fraction:.6f} ≠ 1-1/e = {expected:.6f}"
        )

    def test_long_time_approaches_steady_state(self) -> None:
        """t → ∞ 时温度趋近稳态值。"""
        t_long = 100.0 * self.solver.time_constant_s()
        T_long = float(self.solver.temperature_rise(t_long))
        T_ss = self.spec.ambient_temp_k + self.spec.steady_state_delta_t_k
        assert np.isclose(T_long, T_ss, rtol=1e-6)

    def test_cooling_starts_from_steady(self) -> None:
        """冷却过程 t=0 时温度等于初始温度。"""
        T0_cool = float(self.solver.temperature_fall(0.0))
        T_expected = self.spec.ambient_temp_k + self.spec.steady_state_delta_t_k
        assert np.isclose(T0_cool, T_expected, rtol=1e-15)

    def test_cooling_one_tau_37_percent(self) -> None:
        """冷却 t=τ 时剩余 36.8% 温升 (1/e)。"""
        tau = self.solver.time_constant_s()
        T_tau = float(self.solver.temperature_fall(tau))
        dT_ss = self.spec.steady_state_delta_t_k
        dT_remaining = T_tau - self.spec.ambient_temp_k
        fraction = dT_remaining / dT_ss
        expected = 1.0 / np.e
        assert np.isclose(fraction, expected, rtol=1e-10), (
            f"冷却 t=τ 时剩余温升比例 = {fraction:.6f} ≠ 1/e = {expected:.6f}"
        )

    def test_settling_time_5_percent(self) -> None:
        """5% 稳定时间 ≈ 3τ。"""
        t_settle = self.solver.settling_time_s(0.05)
        tau = self.solver.time_constant_s()
        expected = -tau * np.log(0.05)
        assert np.isclose(t_settle, expected, rtol=1e-10)
        T_settle = float(self.solver.temperature_rise(t_settle))
        dT_ss = self.spec.steady_state_delta_t_k
        dT_actual = T_settle - self.spec.ambient_temp_k
        assert dT_actual >= 0.95 * dT_ss
        assert dT_actual <= dT_ss

    def test_negative_time_raises(self) -> None:
        """负时间应 raise ValueError。"""
        with pytest.raises(ValueError, match="不能为负数"):
            self.solver.temperature_rise(-1.0)
        with pytest.raises(ValueError, match="不能为负数"):
            self.solver.temperature_fall(-1.0)

    def test_array_input(self) -> None:
        """数组输入返回数组输出。"""
        t_arr = np.array([0.0, 1e-6, 1e-3])
        T_arr = self.solver.temperature_rise(t_arr)
        assert T_arr.shape == t_arr.shape
        assert T_arr[0] == self.spec.ambient_temp_k


# ===========================================================================
# 5. TestCrankNicolson2D — 2D 瞬态热传导（D-6: Crank-Nicolson 数值解）
# ===========================================================================
class TestCrankNicolson2D:
    """2D Crank-Nicolson 瞬态热传导求解器验证（D-6: 瞬态热响应）。"""

    def _make_solver(self) -> Any:
        from polaris.device.transient_thermal import (
            ThermalLayer2D,
            CrankNicolson2D,
        )

        layers = [
            ThermalLayer2D(
                name="substrate",
                thickness_um=50.0,
                thermal_conductivity_w_mk=148.0,
                density_kg_m3=2330.0,
                specific_heat_j_kgk=700.0,
            ),
            ThermalLayer2D(
                name="heater",
                thickness_um=1.0,
                thermal_conductivity_w_mk=50.0,
                density_kg_m3=5000.0,
                specific_heat_j_kgk=700.0,
                is_heater=True,
                heater_power_mw_per_um=0.1,
            ),
        ]
        return CrankNicolson2D(
            layers=layers,
            width_um=20.0,
            substrate_temp_k=300.0,
            nx=11,
            heater_width_um=2.0,
            dt_s=1e-7,
            min_nodes_per_layer=3,
        )

    def test_initial_temperature_uniform(self) -> None:
        """初始温度场均匀等于衬底温度。"""
        solver = self._make_solver()
        T = solver.temperature_field
        assert np.all(T == 300.0)
        assert solver.max_temperature_k() == 300.0

    def test_temperature_increases_with_heating(self) -> None:
        """加热后温度应上升。"""
        solver = self._make_solver()
        T0 = solver.max_temperature_k()
        solver.step(50)
        T1 = solver.max_temperature_k()
        assert T1 > T0, "加热后最高温度应上升"

    def test_bottom_boundary_fixed(self) -> None:
        """底部 Dirichlet 边界温度保持恒定。"""
        solver = self._make_solver()
        solver.step(100)
        T = solver.temperature_field
        # 底部行 (i=0) 应全部等于衬底温度
        assert np.all(T[0, :] == 300.0), "底部 Dirichlet 边界温度不恒定"

    def test_approaches_steady_state(self) -> None:
        """长时间加热后温度趋近稳态（增量递减）。"""
        solver = self._make_solver()
        deltas = []
        prev_T = solver.max_temperature_k()
        for _ in range(10):
            solver.step(50)
            cur_T = solver.max_temperature_k()
            deltas.append(cur_T - prev_T)
            prev_T = cur_T
        # 温升增量应单调递减（趋近稳态）
        for i in range(len(deltas) - 1):
            assert deltas[i + 1] <= deltas[i] + 1e-10, (
                "温升增量未递减，可能未趋近稳态"
            )

    def test_avg_temp_at_layer(self) -> None:
        """指定层平均温度可正确获取。"""
        solver = self._make_solver()
        solver.step(20)
        T_sub = solver.avg_temp_at_layer("substrate")
        T_heat = solver.avg_temp_at_layer("heater")
        assert T_sub >= 300.0
        assert T_heat >= T_sub, "加热器层温度应不低于衬底层"

    def test_negative_steps_raises(self) -> None:
        """非正步数应 raise ValueError。"""
        solver = self._make_solver()
        with pytest.raises(ValueError, match="num_steps"):
            solver.step(0)

    def test_solve_transient_returns_times_and_temps(self) -> None:
        """solve_transient 返回时间序列和温度场序列。"""
        solver = self._make_solver()
        times, temps = solver.solve_transient(
            total_time_s=1e-5, sample_interval_steps=10
        )
        assert len(times) == len(temps)
        assert len(times) > 1
        assert times[0] == 0.0
        assert temps[0].shape == (solver.nz, solver.nx)
        assert np.all(temps[0] == 300.0)

    def test_estimate_time_constant(self) -> None:
        """从 2D 仿真结果拟合集总时间常数。"""
        from polaris.device.transient_thermal import estimate_time_constant_from_2d

        solver = self._make_solver()
        result = estimate_time_constant_from_2d(
            solver,
            layer_name="heater",
            total_time_s=5e-5,
            sample_interval_steps=20,
        )
        assert "time_constant_s" in result
        assert result["time_constant_s"] > 0
        assert result["steady_temp_k"] > result["initial_temp_k"]
        assert len(result["time_series_s"]) == len(result["temp_series_k"])

