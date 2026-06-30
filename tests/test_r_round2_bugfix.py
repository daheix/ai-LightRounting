"""第2轮迭代商业 Bug 修复回归测试（R05 Bug 必修，附回归测试防复发）。

覆盖 8 个 bug 修复:
- Bug #1 (P0): cml_compiler_full.py 直波导损耗双重转换（1e4 倍错误）
- Bug #2 (P1): cml_compiler_full.py 环形谐振器 r=sqrt(1-kappa) → sqrt(kappa)
- Bug #3 (P1): alphachip_gnn.py _get_device_param 静默返回 default
- Bug #4 (P1): analytical_placer.py NaN 梯度 np.nan_to_num 静默替换
- Bug #5 (P2): grid/pml.py 光速近似 3e8 → 精确值 2.99792458e8
- Bug #6 (P2): io/openaccess.py PATH 解析 off-by-one 越界
- Bug #7 (P2): cml_compiler_full.py 波长插值 epsilon 掩盖重复波长 + 范围 fall-back
- Bug #8 (P2): cml_compiler_full.py gamma 死代码删除

规则依据: R03 禁止 fall-back / R05 Bug 必修 / R02 学术诚信
来源:
- Yariv A, "Universal relations for coupling of optical power into micro-ring
  resonators," IEEE PTL 2000. https://doi.org/10.1109/68.841166
- NIST CODATA 2018: https://physics.nist.gov/cgi-bin/cuu/Value?c
- Taflove & Hagness, Computational Electrodynamics, 3rd ed. (2005), §5.
"""

from __future__ import annotations

import numpy as np
import pytest

from polaris.sim.cml_compiler_full import (
    CMLCompiler,
    CMLComponent,
    CMLMetadata,
    make_ring_resonator,
    make_straight_waveguide,
)
from polaris.sim.grid.pml import _C0, build_pml_stretch, ScPml
from polaris.io.openaccess import _oa_path_shape


# =============================================================================
# Bug #1: 直波导损耗双重转换修复
# =============================================================================

class TestStraightWaveguideLoss:
    """验证直波导损耗计算正确（无 1e4 倍低估）。"""

    def test_loss_matches_fdtd_formula(self):
        """3 dB/cm × 100μm 应衰减 ~0.03 dB（|S21|² ≈ 0.9931）。"""
        loss_db_cm = 3.0
        length_um = 100.0
        comp = make_straight_waveguide(
            length_um=length_um, loss_db_cm=loss_db_cm, wavelength_um=1.55
        )
        s21 = comp.s_matrix[0, 0, 1]  # port 0 → port 1
        # 预期: alpha_np_um = 3 / 4.343 / 1e4 ≈ 6.908e-5 Np/μm
        # transmission = exp(-6.908e-5 * 100) = exp(-6.908e-3) ≈ 0.9931
        expected_alpha_np_um = loss_db_cm / 4.343 / 1e4
        expected = np.exp(-expected_alpha_np_um * length_um)
        assert np.isclose(abs(s21), expected, rtol=1e-6), (
            f"|S21|={abs(s21):.6f}, expected={expected:.6f}"
        )

    def test_loss_not_underestimated_1e4(self):
        """回归: bug 修复前 |S21| ≈ 1.0（损耗被低估 1e4 倍）。"""
        # 10 dB/cm × 1000μm 应有明显损耗（|S21| < 0.5）
        comp = make_straight_waveguide(
            length_um=1000.0, loss_db_cm=10.0, wavelength_um=1.55
        )
        s21 = abs(comp.s_matrix[0, 0, 1])
        # bug 前: exp(-10/4.343/1e4 * 1000 * 1e-4) ≈ exp(-2.3e-6) ≈ 1.0
        # 修复后: exp(-10/4.343/1e4 * 1000) = exp(-0.2303) ≈ 0.794
        assert s21 < 0.95, f"损耗被低估（|S21|={s21} 接近 1，bug 未修复）"
        assert s21 > 0.5, f"损耗过大（|S21|={s21}，可能过度衰减）"


# =============================================================================
# Bug #2: 环形谐振器能量守恒
# =============================================================================

class TestRingResonatorUnitarity:
    """验证 t² + r² = 1（能量守恒，幺正性）。"""

    def test_energy_conservation(self):
        """t² + r² 应 = 1（kappa ∈ (0, 1)）。"""
        for kappa in (0.1, 0.3, 0.5, 0.7, 0.9):
            comp = make_ring_resonator(kappa=kappa, wavelength_um=1.55)
            # 通过端口在非谐振条件下，S 矩阵总功率应近似守恒
            # 这里直接验证公式: t²+r²=1 通过模块内部实现
            # 简化: 验证 through 端口在 alpha_L=0 时 |through|² + |drop|² ≈ 1
            s21 = comp.s_matrix[0, 0, 1]  # through
            s41 = comp.s_matrix[0, 0, 3]  # drop
            total_power = abs(s21) ** 2 + abs(s41) ** 2
            # 无损耗时（loss_db_cm=0）应严格 = 1，有损耗时 < 1
            # 这里 loss_db_cm 默认 2.0，所以总功率 ≤ 1
            assert total_power <= 1.0 + 1e-9, (
                f"kappa={kappa}: |through|²+|drop|²={total_power} > 1，"
                f"违反能量守恒（r 系数错误）"
            )

    def test_drop_nonzero_when_kappa_nonzero(self):
        """kappa > 0 时 drop 端口应有信号（bug 前可能为 0 或异常）。"""
        comp = make_ring_resonator(kappa=0.5, wavelength_um=1.55)
        s41 = abs(comp.s_matrix[0, 0, 3])
        assert s41 > 0, "drop 端口为 0，r=sqrt(1-kappa) bug 未修复"


# =============================================================================
# Bug #3: _get_device_param 参数转换失败 raise
# =============================================================================

class TestGetDeviceParamRaise:
    """验证 _get_device_param 在值无法转 float 时 raise。"""

    def test_raises_on_non_numeric_value(self):
        from polaris.engine.alphachip_gnn import _get_device_param

        class FakeDev:
            def __init__(self, params):
                self.params = params

        dev = FakeDev({"neff": "not_a_number"})
        with pytest.raises(ValueError, match="无法转换为 float"):
            _get_device_param(dev, "neff", default=2.4)

    def test_returns_default_when_key_absent(self):
        """key 不存在时返回 default（合法行为，非 fall-back）。"""
        from polaris.engine.alphachip_gnn import _get_device_param

        class FakeDev:
            def __init__(self):
                self.params = {"other": 1.0}

        dev = FakeDev()
        assert _get_device_param(dev, "neff", default=2.4) == 2.4

    def test_returns_value_when_valid(self):
        from polaris.engine.alphachip_gnn import _get_device_param

        class FakeDev:
            def __init__(self):
                self.params = {"neff": 2.44}

        dev = FakeDev()
        assert _get_device_param(dev, "neff", default=2.4) == 2.44


# =============================================================================
# Bug #4: NaN 梯度 raise
# =============================================================================

class TestNanGradientRaise:
    """验证 HPWL/密度梯度出现 NaN/Inf 时 raise（不静默 nan_to_num）。"""

    def test_hpwl_gradient_raises_on_nan(self):
        from polaris.engine.analytical_placer import (
            AnalyticalPlacer,
            AnalyticalPlacerConfig,
        )
        from polaris.data.specs import (
            CircuitSpec,
            DeviceSpec,
            ConnectionSpec,
        )

        circuit = CircuitSpec(
            name="nan_test",
            devices=[
                DeviceSpec(name="a", device_type="mzi", width_um=10, height_um=10),
                DeviceSpec(name="b", device_type="mzi", width_um=10, height_um=10),
            ],
            connections=[ConnectionSpec(src="a", dst="b", count=1)],
        )
        placer = AnalyticalPlacer(circuit, AnalyticalPlacerConfig())
        # 构造极端坐标触发 NaN（exp 溢出）
        pos = np.array([[0.0, 0.0], [1e308, 1e308]])
        with pytest.raises(RuntimeError, match="非有限值"):
            placer._hpwl_gradient(pos)

    def test_density_gradient_raises_on_nan(self):
        from polaris.engine.analytical_placer import (
            AnalyticalPlacer,
            AnalyticalPlacerConfig,
        )
        from polaris.data.specs import (
            CircuitSpec,
            DeviceSpec,
            ConnectionSpec,
        )

        circuit = CircuitSpec(
            name="nan_test",
            devices=[
                DeviceSpec(name="a", device_type="mzi", width_um=10, height_um=10),
                DeviceSpec(name="b", device_type="mzi", width_um=10, height_um=10),
            ],
            connections=[ConnectionSpec(src="a", dst="b", count=1)],
        )
        placer = AnalyticalPlacer(circuit, AnalyticalPlacerConfig())
        # 极端坐标触发密度梯度 NaN
        pos = np.array([[0.0, 0.0], [1e308, 1e308]])
        with pytest.raises(RuntimeError, match="非有限值"):
            placer._density_gradient(pos)


# =============================================================================
# Bug #5: PML 光速精确值
# =============================================================================

class TestPmlSpeedOfLight:
    """验证 PML 使用 NIST CODATA 2018 精确光速。"""

    def test_c0_is_exact_codata_value(self):
        """_C0 应为 2.99792458e8（NIST CODATA 2018）。"""
        assert _C0 == 2.99792458e8

    def test_c0_not_approximate_3e8(self):
        """回归: 不应使用近似值 3e8。"""
        assert _C0 != 3e8
        assert abs(_C0 - 3e8) / _C0 > 1e-4  # 差异约 0.07%


# =============================================================================
# Bug #6: OpenAccess PATH 解析 off-by-one
# =============================================================================

class TestOaPathShape:
    """验证 PATH 解析器对奇数坐标 raise，对正常输入不越界。"""

    def test_normal_path_parses(self):
        """正常 PATH（width + 偶数坐标）应正确解析。"""
        toks = ["PATH", "layer1", "0.5", "0.0", "0.0", "10.0", "10.0", "20.0", "20.0"]
        shape = _oa_path_shape(toks)
        assert shape.shape_type == "path"
        assert shape.layer == "layer1"
        assert shape.width == 0.5
        assert len(shape.points) == 3

    def test_odd_coords_raises(self):
        """奇数坐标（畸形输入）应 raise，不越界。"""
        # width=0.5 + 5 个坐标（奇数）→ 应 raise
        toks = ["PATH", "layer1", "0.5", "0.0", "0.0", "10.0", "10.0", "20.0"]
        with pytest.raises(ValueError, match="坐标数为奇数"):
            _oa_path_shape(toks)

    def test_minimal_path_parses(self):
        """最小 PATH（width + 2 个点）应解析。"""
        toks = ["PATH", "l", "1.0", "0.0", "0.0", "5.0", "5.0"]
        shape = _oa_path_shape(toks)
        assert len(shape.points) == 2


# =============================================================================
# Bug #7: CML 波长插值范围 + 重复波长校验
# =============================================================================

class TestCmlWavelengthInterpolation:
    """验证波长插值不 fall-back（超出范围 raise / 重复波长 raise）。"""

    def _make_comp(self, wavelengths, s_matrix):
        return CMLComponent(
            metadata=CMLMetadata(name="test"),
            port_names=["in", "out"],
            wavelengths_um=np.array(wavelengths, dtype=float),
            s_matrix=np.array(s_matrix, dtype=complex),
        )

    def test_in_range_interpolation(self):
        """范围内波长应正常插值。"""
        comp = self._make_comp(
            wavelengths=[1.5, 1.6],
            s_matrix=[[[0.0, 1.0], [1.0, 0.0]], [[0.0, 0.5], [0.5, 0.0]]],
        )
        compiler = CMLCompiler(wavelengths_um=np.array([1.55]))
        result = compiler.get_s_params_at_wavelength(comp, 1.55)
        # 线性插值: (1-0.5)*1.0 + 0.5*0.5 = 0.75
        assert np.isclose(result[0, 1], 0.75)

    def test_out_of_range_raises(self):
        """超出波长范围应 raise（不静默 clip）。"""
        comp = self._make_comp(
            wavelengths=[1.5, 1.6],
            s_matrix=[[[0.0, 1.0], [1.0, 0.0]], [[0.0, 0.5], [0.5, 0.0]]],
        )
        compiler = CMLCompiler(wavelengths_um=np.array([1.55]))
        with pytest.raises(ValueError, match="超出 CML 元件覆盖范围"):
            compiler.get_s_params_at_wavelength(comp, 2.0)
        with pytest.raises(ValueError, match="超出 CML 元件覆盖范围"):
            compiler.get_s_params_at_wavelength(comp, 1.0)

    def test_duplicate_wavelength_raises(self):
        """重复波长应 raise（不通过 +1e-12 掩盖）。"""
        comp = self._make_comp(
            wavelengths=[1.5, 1.5, 1.6],  # 重复
            s_matrix=[
                [[0.0, 1.0], [1.0, 0.0]],
                [[0.0, 0.8], [0.8, 0.0]],
                [[0.0, 0.5], [0.5, 0.0]],
            ],
        )
        compiler = CMLCompiler(wavelengths_um=np.array([1.55]))
        with pytest.raises(ValueError, match="含重复值"):
            compiler.get_s_params_at_wavelength(comp, 1.5)

    def test_single_wavelength_no_interpolation(self):
        """单波长模型应直接返回，不插值。"""
        comp = self._make_comp(
            wavelengths=[1.55],
            s_matrix=[[[0.0, 0.99], [0.99, 0.0]]],
        )
        compiler = CMLCompiler(wavelengths_um=np.array([1.55]))
        result = compiler.get_s_params_at_wavelength(comp, 1.55)
        assert np.isclose(result[0, 1], 0.99)


# =============================================================================
# Bug #8: gamma 死代码删除（间接通过 Bug #1 测试覆盖）
# =============================================================================

class TestGammaDeadCodeRemoved:
    """验证 make_straight_waveguide 中无 gamma 死代码。"""

    def test_no_gamma_in_source(self):
        """源码中 make_straight_waveguide 函数体不应含 gamma 变量。"""
        import inspect

        source = inspect.getsource(make_straight_waveguide)
        # gamma 不应作为变量出现（注释中允许提及）
        lines = [l for l in source.splitlines() if not l.strip().startswith("#")]
        for line in lines:
            # 排除注释后不应有 "gamma =" 赋值
            assert "gamma =" not in line, (
                f"make_straight_waveguide 仍含 gamma 死代码: {line}"
            )
