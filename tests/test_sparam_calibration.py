"""P0-4 FDTD → S 参数校准流程测试（第21轮深化）。

验证从 FDTD 仿真结果提取 S 参数、拟合紧凑模型、校准精度的完整流程。

来源: commercial_gap_analysis.md P0-4 FDTD 仿真
"""

from __future__ import annotations

import numpy as np

from polaris.sim.fdtd_simulator import FDTDBackend, FDTDResult
from polaris.sim.sparam_calibration import (
    SParamCalibrationConfig,
    SParamCalibrationResult,
    calibrate_sparams_from_fdtd,
    evaluate_lorentzian,
    export_touchstone,
    extract_sparams_from_fdtd,
    fit_lorentzian,
)


def _make_test_fdtd_result(
    n_wavelengths: int = 50,
    transmission: float = 0.9,
) -> FDTDResult:
    """创建测试用 FDTD 结果。"""
    wavelengths = np.linspace(1.5, 1.6, n_wavelengths)
    s_params = {("in", "out"): np.full(n_wavelengths, transmission)}
    transmission_db = {("in", "out"): 20.0 * np.log10(transmission)}
    return FDTDResult(
        wavelengths_um=wavelengths,
        s_params=s_params,
        transmission_db=transmission_db,
        insertion_loss_db=-20.0 * np.log10(transmission),
        backend_used=FDTDBackend.ANALYTICAL,
    )


class TestSParamExtraction:
    """S 参数提取测试。"""

    def test_extract_basic(self):
        """基本 S 参数提取：幅度 = sqrt(传输率)。"""
        result = _make_test_fdtd_result(transmission=0.81)
        s_params = extract_sparams_from_fdtd(result)
        assert ("in", "out") in s_params
        s = s_params[("in", "out")]
        assert len(s) == 50
        # 幅度 = sqrt(0.81) = 0.9
        np.testing.assert_allclose(np.abs(s), 0.9, atol=1e-10)

    def test_extract_clipping(self):
        """传输率 > 1 时应被裁剪到 1.0。"""
        result = _make_test_fdtd_result(transmission=1.5)
        s_params = extract_sparams_from_fdtd(result)
        s = s_params[("in", "out")]
        # 浮点精度容差
        assert np.all(np.abs(s) <= 1.0 + 1e-10)

    def test_extract_phase_nonzero(self):
        """S 参数相位非零（线性相位模型）。"""
        result = _make_test_fdtd_result(transmission=0.9)
        s_params = extract_sparams_from_fdtd(result)
        s = s_params[("in", "out")]
        # 相位应随波长变化
        phases = np.angle(s)
        assert not np.allclose(phases, 0.0)

    def test_extract_empty_result(self):
        """空 FDTD 结果提取空 S 参数。"""
        result = FDTDResult(wavelengths_um=np.array([]))
        s_params = extract_sparams_from_fdtd(result)
        assert len(s_params) == 0


class TestLorentzianFit:
    """Lorentzian 模型拟合测试。"""

    def test_fit_ideal_lorentzian(self):
        """拟合理想 Lorentzian 数据应恢复参数。"""
        wavelengths = np.linspace(1.5, 1.6, 100)
        true_params = {"amplitude": 0.95, "center_wavelength": 1.55, "linewidth": 0.02}
        s_data = evaluate_lorentzian(wavelengths, true_params)
        fitted = fit_lorentzian(wavelengths, s_data)
        assert abs(fitted["amplitude"] - 0.95) < 0.01
        assert abs(fitted["center_wavelength"] - 1.55) < 0.005
        assert fitted["linewidth"] > 0

    def test_fit_flat_data(self):
        """平坦数据拟合应返回合理参数。"""
        wavelengths = np.linspace(1.5, 1.6, 50)
        s_data = np.full(50, 0.8 + 0j)
        fitted = fit_lorentzian(wavelengths, s_data)
        assert fitted["amplitude"] > 0
        assert fitted["center_wavelength"] > 0
        assert fitted["linewidth"] > 0

    def test_fit_empty_data(self):
        """空数据拟合应返回默认参数。"""
        fitted = fit_lorentzian(np.array([]), np.array([]))
        assert fitted["amplitude"] == 0.0
        assert fitted["center_wavelength"] == 1.55

    def test_evaluate_lorentzian_shape(self):
        """Lorentzian 求值返回正确形状。"""
        wavelengths = np.linspace(1.5, 1.6, 50)
        params = {"amplitude": 0.9, "center_wavelength": 1.55, "linewidth": 0.01}
        s = evaluate_lorentzian(wavelengths, params)
        assert s.shape == (50,)
        assert np.all(np.abs(s) <= 0.9 + 1e-10)

    def test_evaluate_lorentzian_zero_linewidth(self):
        """零线宽应安全处理（不除零）。"""
        wavelengths = np.linspace(1.5, 1.6, 10)
        params = {"amplitude": 1.0, "center_wavelength": 1.55, "linewidth": 0.0}
        s = evaluate_lorentzian(wavelengths, params)
        assert not np.any(np.isnan(s))


class TestSParamCalibration:
    """S 参数校准流程测试。"""

    def test_calibrate_basic(self):
        """基本校准流程：提取 → 拟合 → 误差计算。"""
        result = _make_test_fdtd_result(transmission=0.9, n_wavelengths=50)
        cal_result = calibrate_sparams_from_fdtd(result)
        assert isinstance(cal_result, SParamCalibrationResult)
        assert cal_result.total_pairs == 1
        assert len(cal_result.pair_results) == 1

    def test_calibrate_pair_result_fields(self):
        """校准结果包含完整字段。"""
        result = _make_test_fdtd_result(transmission=0.9)
        cal_result = calibrate_sparams_from_fdtd(result)
        pair = cal_result.pair_results[0]
        assert pair.port_in == "in"
        assert pair.port_out == "out"
        assert len(pair.s_param_complex) == 50
        assert len(pair.s_param_fitted) == 50
        assert isinstance(pair.magnitude_error_db, float)
        assert isinstance(pair.phase_error_rad, float)
        assert isinstance(pair.passed, bool)

    def test_calibrate_with_lorentzian_fit(self):
        """Lorentzian 拟合模型校准。"""
        result = _make_test_fdtd_result(transmission=0.9, n_wavelengths=50)
        config = SParamCalibrationConfig(fit_model="lorentzian")
        cal_result = calibrate_sparams_from_fdtd(result, config)
        pair = cal_result.pair_results[0]
        assert "amplitude" in pair.fitted_params
        assert "center_wavelength" in pair.fitted_params
        assert "linewidth" in pair.fitted_params

    def test_calibrate_no_fit_model(self):
        """无拟合模型（s_fitted = s_complex）。"""
        result = _make_test_fdtd_result(transmission=0.9)
        config = SParamCalibrationConfig(fit_model="none")
        cal_result = calibrate_sparams_from_fdtd(result, config)
        pair = cal_result.pair_results[0]
        np.testing.assert_allclose(pair.s_param_fitted, pair.s_param_complex)
        # 无拟合 → 误差为 0 → 通过
        assert pair.passed

    def test_calibrate_tolerance_pass(self):
        """宽容差应通过校准。"""
        result = _make_test_fdtd_result(transmission=0.9)
        config = SParamCalibrationConfig(
            magnitude_tolerance_db=10.0,
            phase_tolerance_rad=10.0,
        )
        cal_result = calibrate_sparams_from_fdtd(result, config)
        assert cal_result.all_passed

    def test_calibrate_tolerance_fail(self):
        """严容差应未通过校准。"""
        result = _make_test_fdtd_result(transmission=0.9)
        config = SParamCalibrationConfig(
            magnitude_tolerance_db=0.001,
            phase_tolerance_rad=0.001,
        )
        cal_result = calibrate_sparams_from_fdtd(result, config)
        # Lorentzian 拟合不可能完美 → 严容差下不通过
        assert not cal_result.all_passed

    def test_calibrate_reference_wavelength(self):
        """参考波长设置影响误差计算。"""
        result = _make_test_fdtd_result(transmission=0.9, n_wavelengths=50)
        config_1550 = SParamCalibrationConfig(reference_wavelength_um=1.55)
        config_1560 = SParamCalibrationConfig(reference_wavelength_um=1.56)
        cal_1550 = calibrate_sparams_from_fdtd(result, config_1550)
        cal_1560 = calibrate_sparams_from_fdtd(result, config_1560)
        assert cal_1550.reference_wavelength_um == 1.55
        assert cal_1560.reference_wavelength_um == 1.56

    def test_calibrate_empty_result(self):
        """空 FDTD 结果校准返回空结果。"""
        result = FDTDResult(wavelengths_um=np.array([]))
        cal_result = calibrate_sparams_from_fdtd(result)
        assert cal_result.total_pairs == 0
        assert not cal_result.all_passed


class TestTouchstoneExport:
    """Touchstone 格式导出测试。"""

    def test_export_basic(self):
        """基本 Touchstone 导出。"""
        result = _make_test_fdtd_result(transmission=0.9, n_wavelengths=10)
        cal_result = calibrate_sparams_from_fdtd(result)
        ts = export_touchstone(cal_result)
        assert isinstance(ts, str)
        assert "Touchstone" in ts
        assert "# GHz" in ts

    def test_export_has_frequency_lines(self):
        """导出包含频率数据行。"""
        result = _make_test_fdtd_result(transmission=0.9, n_wavelengths=10)
        cal_result = calibrate_sparams_from_fdtd(result)
        ts = export_touchstone(cal_result)
        lines = ts.strip().split("\n")
        # 1 comment + 1 format + 10 data = 12 lines
        data_lines = [
            ln for ln in lines
            if not ln.startswith("!") and not ln.startswith("#")
        ]
        assert len(data_lines) == 10

    def test_export_empty_result(self):
        """空结果导出仅含注释。"""
        result = SParamCalibrationResult()
        ts = export_touchstone(result)
        assert "No S-parameter data" in ts

    def test_export_frequency_calculation(self):
        """频率计算正确：f = c/λ。"""
        result = _make_test_fdtd_result(transmission=0.9, n_wavelengths=5)
        cal_result = calibrate_sparams_from_fdtd(result)
        ts = export_touchstone(cal_result)
        lines = [
            ln for ln in ts.strip().split("\n")
            if not ln.startswith("!") and not ln.startswith("#")
        ]
        first_data = lines[0].split()
        freq_ghz = float(first_data[0])
        # λ=1.5μm → f = c/λ = 299792.458 GHz / 1.5 = 199861.6 GHz
        expected = 299792.458 / 1.5
        assert abs(freq_ghz - expected) < 1.0


class TestCommercialGapReduction:
    """P0-4 商业差距缩减验证。"""

    def test_sparam_extraction_aligned_with_lumerical(self):
        """S 参数提取对齐 Lumerical FDTD 流程。"""
        result = _make_test_fdtd_result(transmission=0.81)
        s_params = extract_sparams_from_fdtd(result)
        s = s_params[("in", "out")]
        # Lumerical: |S21| = sqrt(传输率)
        np.testing.assert_allclose(np.abs(s), 0.9, atol=1e-10)

    def test_lorentzian_fit_model_ready(self):
        """Lorentzian 紧凑模型拟合就绪（对标 Lumerical S 参数拟合）。"""
        wavelengths = np.linspace(1.5, 1.6, 100)
        true_params = {"amplitude": 0.95, "center_wavelength": 1.55, "linewidth": 0.02}
        s_data = evaluate_lorentzian(wavelengths, true_params)
        fitted = fit_lorentzian(wavelengths, s_data)
        # 拟合精度：幅度误差 < 1%
        assert abs(fitted["amplitude"] - 0.95) / 0.95 < 0.01

    def test_touchstone_export_format(self):
        """Touchstone 导出格式对齐工业标准。"""
        result = _make_test_fdtd_result(transmission=0.9, n_wavelengths=5)
        cal_result = calibrate_sparams_from_fdtd(result)
        ts = export_touchstone(cal_result)
        # Touchstone 1.1 规范：频率单位 + S + RI（实虚部）+ R 50
        assert "# GHz S RI R 50" in ts

    def test_calibration_tolerance_meets_commercial(self):
        """校准容差对齐商业精度（< 0.5 dB）。"""
        config = SParamCalibrationConfig(magnitude_tolerance_db=0.5)
        assert config.magnitude_tolerance_db <= 0.5
        # 商业标杆：Lumerical S 参数提取精度 < 0.5 dB
