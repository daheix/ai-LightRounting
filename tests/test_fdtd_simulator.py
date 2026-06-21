"""P0-4 FDTD 仿真集成测试（第14轮）。

验证 FDTD 仿真接口的正确性与后端可用性检测。

来源: commercial_gap_analysis.md P0-4 FDTD 仿真缺失
"""

from __future__ import annotations

import numpy as np
import pytest

from polaris.pdk.catalog import build_default_catalog
from polaris.sim.fdtd_simulator import (
    FDTDBackend,
    FDTDConfig,
    FDTDResult,
    get_available_backends,
    is_meep_available,
    is_tidy3d_available,
    run_fdtd_simulation,
)


class TestFDTDBackendAvailability:
    """FDTD 后端可用性检测。"""

    def test_analytical_always_available(self):
        """解析后端始终可用。"""
        backends = get_available_backends()
        assert FDTDBackend.ANALYTICAL in backends

    def test_meep_availability_check(self):
        """MEEP 可用性检测不抛异常。"""
        # 只验证函数能正常调用，不要求返回 True
        result = is_meep_available()
        assert isinstance(result, bool)

    def test_tidy3d_availability_check(self):
        """Tidy3D 可用性检测不抛异常。"""
        result = is_tidy3d_available()
        assert isinstance(result, bool)

    def test_available_backends_list(self):
        """get_available_backends 返回列表。"""
        backends = get_available_backends()
        assert isinstance(backends, list)
        assert len(backends) >= 1  # 至少有 ANALYTICAL


class TestFDTDConfig:
    """FDTD 配置测试。"""

    def test_default_config(self):
        """默认配置值正确。"""
        cfg = FDTDConfig()
        assert cfg.wavelength_start_um == 1.5
        assert cfg.wavelength_end_um == 1.6
        assert cfg.n_wavelengths == 50
        assert cfg.boundary_type == "PML"
        assert cfg.backend == FDTDBackend.MEEP

    def test_custom_config(self):
        """自定义配置。"""
        cfg = FDTDConfig(
            wavelength_start_um=1.3,
            wavelength_end_um=1.4,
            n_wavelengths=100,
            backend=FDTDBackend.ANALYTICAL,
        )
        assert cfg.wavelength_start_um == 1.3
        assert cfg.n_wavelengths == 100
        assert cfg.backend == FDTDBackend.ANALYTICAL


class TestAnalyticalSimulation:
    """解析模型仿真测试（始终可用）。"""

    @pytest.fixture
    def waveguide_device(self):
        """获取测试用波导器件。"""
        cat = build_default_catalog()
        return cat.get("strip_waveguide", platform="SOI")

    def test_analytical_returns_result(self, waveguide_device):
        """解析仿真返回 FDTDResult。"""
        cfg = FDTDConfig(backend=FDTDBackend.ANALYTICAL)
        result = run_fdtd_simulation(waveguide_device, cfg)
        assert isinstance(result, FDTDResult)
        assert result.backend_used == FDTDBackend.ANALYTICAL

    def test_analytical_wavelengths(self, waveguide_device):
        """解析仿真波长数组正确。"""
        cfg = FDTDConfig(
            backend=FDTDBackend.ANALYTICAL,
            wavelength_start_um=1.5,
            wavelength_end_um=1.6,
            n_wavelengths=20,
        )
        result = run_fdtd_simulation(waveguide_device, cfg)
        assert len(result.wavelengths_um) == 20
        assert result.wavelengths_um[0] == pytest.approx(1.5)
        assert result.wavelengths_um[-1] == pytest.approx(1.6)

    def test_analytical_s_params(self, waveguide_device):
        """解析仿真 S 参数提取。"""
        cfg = FDTDConfig(backend=FDTDBackend.ANALYTICAL)
        result = run_fdtd_simulation(waveguide_device, cfg)
        # 波导有 in/out 端口
        assert len(result.s_params) > 0
        for key, s in result.s_params.items():
            assert isinstance(key, tuple)
            assert len(s) == cfg.n_wavelengths

    def test_analytical_transmission_positive_loss(self, waveguide_device):
        """解析仿真传输损耗为负值（dB）。"""
        cfg = FDTDConfig(backend=FDTDBackend.ANALYTICAL)
        result = run_fdtd_simulation(waveguide_device, cfg)
        # 插入损耗应为负值（dB）
        assert result.insertion_loss_db <= 0

    def test_analytical_simulation_time(self, waveguide_device):
        """解析仿真耗时记录。"""
        cfg = FDTDConfig(backend=FDTDBackend.ANALYTICAL)
        result = run_fdtd_simulation(waveguide_device, cfg)
        assert result.simulation_time_s >= 0


class TestMEEPSimulation:
    """MEEP 仿真后端测试。"""

    def test_meep_import_error_when_unavailable(self):
        """MEEP 不可用时抛出 ImportError。"""
        if is_meep_available():
            pytest.skip("MEEP 已安装，跳过不可用测试")
        cat = build_default_catalog()
        dev = cat.get("strip_waveguide", platform="SOI")
        cfg = FDTDConfig(backend=FDTDBackend.MEEP)
        with pytest.raises(ImportError, match="MEEP 后端不可用"):
            run_fdtd_simulation(dev, cfg)

    def test_meep_available_runs_simulation(self):
        """MEEP 可用时运行仿真。"""
        if not is_meep_available():
            pytest.skip("MEEP 未安装，跳过可用测试")
        cat = build_default_catalog()
        dev = cat.get("strip_waveguide", platform="SOI")
        cfg = FDTDConfig(backend=FDTDBackend.MEEP, n_wavelengths=5)
        result = run_fdtd_simulation(dev, cfg)
        assert result.backend_used == FDTDBackend.MEEP
        assert len(result.wavelengths_um) == 5


class TestTidy3DSimulation:
    """Tidy3D 仿真后端测试。"""

    def test_tidy3d_import_error_when_unavailable(self):
        """Tidy3D 不可用时抛出 ImportError。"""
        if is_tidy3d_available():
            pytest.skip("Tidy3D 已安装，跳过不可用测试")
        cat = build_default_catalog()
        dev = cat.get("strip_waveguide", platform="SOI")
        cfg = FDTDConfig(backend=FDTDBackend.TIDY3D)
        with pytest.raises(ImportError, match="Tidy3D 后端不可用"):
            run_fdtd_simulation(dev, cfg)

    def test_tidy3d_runtime_error_without_api_key(self):
        """Tidy3D 已安装但无 API key 时抛出 RuntimeError（不 fall-back）。

        来源: 用户规则"公式计算等功能可以单独设计独立的接口，
              仅供在特定条件下使用，而不是作为 fall-back 使用"
        """
        import os

        if not is_tidy3d_available():
            pytest.skip("Tidy3D 未安装，跳过 API key 测试")
        # 确保无 API key
        old_key = os.environ.pop("TIDY3D_API_KEY", None)
        try:
            cat = build_default_catalog()
            dev = cat.get("strip_waveguide", platform="SOI")
            cfg = FDTDConfig(backend=FDTDBackend.TIDY3D, n_wavelengths=5)
            with pytest.raises(RuntimeError, match="TIDY3D_API_KEY"):
                run_fdtd_simulation(dev, cfg)
        finally:
            if old_key is not None:
                os.environ["TIDY3D_API_KEY"] = old_key


class TestSOIWaveguideSparams:
    """SOI 波导解析 S 参数独立接口测试。"""

    def test_sparams_returns_complex(self):
        """_compute_soi_waveguide_sparams 返回复数数组。"""
        from polaris.sim.fdtd_simulator import _compute_soi_waveguide_sparams

        wavelengths = np.linspace(1.5, 1.6, 10)
        s21 = _compute_soi_waveguide_sparams(wavelengths, length_um=100.0)
        assert s21.dtype == np.complex128
        assert s21.shape == (10,)

    def test_sparams_amplitude_decreases_with_length(self):
        """S 参数幅度随波导长度增加而减小（损耗）。"""
        from polaris.sim.fdtd_simulator import _compute_soi_waveguide_sparams

        wavelengths = np.array([1.55])
        s21_short = _compute_soi_waveguide_sparams(wavelengths, length_um=10.0)
        s21_long = _compute_soi_waveguide_sparams(wavelengths, length_um=1000.0)
        assert np.abs(s21_short[0]) > np.abs(s21_long[0])

    def test_sparams_phase_increases_with_length(self):
        """S 参数相位随波导长度增加而增加。"""
        from polaris.sim.fdtd_simulator import _compute_soi_waveguide_sparams

        wavelengths = np.array([1.55])
        s21_short = _compute_soi_waveguide_sparams(wavelengths, length_um=10.0)
        s21_long = _compute_soi_waveguide_sparams(wavelengths, length_um=1000.0)
        phase_short = np.angle(s21_short[0])
        phase_long = np.angle(s21_long[0])
        assert abs(phase_long) > abs(phase_short)


class TestFDTDIntegration:
    """FDTD 与 PoLaRIS 集成测试。"""

    def test_fdtd_with_multi_platform_devices(self):
        """FDTD 解析仿真支持多平台器件。"""
        cat = build_default_catalog()
        cfg = FDTDConfig(backend=FDTDBackend.ANALYTICAL)
        for platform in ["SOI", "SiN", "InP", "LNOI"]:
            try:
                dev = cat.get("strip_waveguide", platform=platform)
            except KeyError:
                # 某些平台可能没有 strip_waveguide，跳过
                continue
            result = run_fdtd_simulation(dev, cfg)
            assert result.backend_used == FDTDBackend.ANALYTICAL

    def test_fdtd_result_serializable(self):
        """FDTD 结果可序列化为基本类型。"""
        cat = build_default_catalog()
        dev = cat.get("strip_waveguide", platform="SOI")
        cfg = FDTDConfig(backend=FDTDBackend.ANALYTICAL, n_wavelengths=10)
        result = run_fdtd_simulation(dev, cfg)
        # 验证结果字段类型
        assert isinstance(result.wavelengths_um, np.ndarray)
        assert isinstance(result.s_params, dict)
        assert isinstance(result.transmission_db, dict)
        assert isinstance(result.insertion_loss_db, float)
        assert isinstance(result.simulation_time_s, float)

    def test_fdtd_backend_enum_values(self):
        """FDTDBackend 枚举值正确。"""
        assert FDTDBackend.MEEP.value == "meep"
        assert FDTDBackend.TIDY3D.value == "tidy3d"
        assert FDTDBackend.ANALYTICAL.value == "analytical"
