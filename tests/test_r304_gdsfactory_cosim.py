"""R304 gdsfactory 联合仿真 - 组件级测试。

验证 gdsfactory Component → PoLaRIS Device → FDTD 仿真 → S 参数提取 → 结果回传
的完整工作流，覆盖 TR-304.1/304.2/304.3 三个测试需求。

测试策略:
- 使用 MockComponent 模拟 gdsfactory Component，使测试在 Python 3.14（gdsfactory
  不可用）下也能运行
- 使用 ANALYTICAL 后端（FDTDBackend.ANALYTICAL），无需 MEEP/Tidy3D
- 真实 gdsfactory 集成测试用 pytest.mark.skipif 跳过

来源:
- gdsfactory (MIT): https://gdsfactory.github.io/gdsfactory/
- MEEP: https://meep.readthedocs.io/
- Tidy3D: https://www.flexcompute.com/tidy3d/
- Touchstone 规范: https://en.wikipedia.org/wiki/Touchstone_file
- Pozar, "Microwave Engineering", 4th ed., §4.4
- Taflove & Hagness, "Computational Electrodynamics", 3rd ed., 2005
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pytest

from polaris.sim.fdtd_simulator import FDTDConfig, FDTDBackend
from polaris.sim.gdsfactory_cosim import (
    CoSimConfig,
    CoSimResult,
    attach_metadata_to_component,
    build_s_matrix_from_sdict,
    cosim_to_gdsfactory_metadata,
    export_cosim_to_touchstone,
    get_cosim_summary,
    simulate_gdsfactory_component,
)
from polaris.pdk.gdsfactory_integration import DeviceImportConfig, is_available


# =============================================================================
# Mock gdsfactory Component（Python 3.14 下 gdsfactory 不可用时的测试替身）
# =============================================================================
@dataclass
class MockPort:
    """模拟 gdsfactory Port。"""

    name: str
    orientation: float  # 度
    width: float
    port_type: str = "optical"
    center: tuple[float, float] = (0.0, 0.0)


@dataclass
class MockBbox:
    """模拟 gdsfactory Component.bbox() 返回的 klayout Box。"""

    left: float
    bottom: float
    right: float
    top: float


@dataclass
class MockComponent:
    """模拟 gdsfactory Component。

    提供联合仿真所需的全部属性：
    - .name: 组件名
    - .ports: list[MockPort]
    - .bbox(): callable，返回 MockBbox
    - .metadata: dict
    """

    name: str
    ports_list: list[MockPort] = field(default_factory=list)
    bbox_obj: MockBbox | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def ports(self) -> list[MockPort]:
        """gdsfactory Component.ports 属性。"""
        return self.ports_list

    def bbox(self) -> MockBbox:
        """gdsfactory Component.bbox() 方法。"""
        if self.bbox_obj is None:
            raise ValueError("MockComponent.bbox_obj 未设置")
        return self.bbox_obj


def _make_straight_component(
    length_um: float = 10.0,
    width_um: float = 0.5,
) -> MockComponent:
    """创建模拟直波导组件（2 端口）。"""
    return MockComponent(
        name="straight",
        ports_list=[
            MockPort(
                name="o1",
                orientation=180.0,  # 西侧
                width=width_um,
                center=(0.0, 0.0),
            ),
            MockPort(
                name="o2",
                orientation=0.0,  # 东侧
                width=width_um,
                center=(length_um, 0.0),
            ),
        ],
        bbox_obj=MockBbox(left=0.0, bottom=-width_um / 2, right=length_um, top=width_um / 2),
        metadata={},
    )


def _make_mmi_component() -> MockComponent:
    """创建模拟 MMI 1x2 组件（3 端口）。"""
    return MockComponent(
        name="mmi1x2",
        ports_list=[
            MockPort(name="o1", orientation=180.0, width=0.5, center=(0.0, 0.0)),
            MockPort(name="o2", orientation=0.0, width=0.5, center=(10.0, 0.5)),
            MockPort(name="o3", orientation=0.0, width=0.5, center=(10.0, -0.5)),
        ],
        bbox_obj=MockBbox(left=0.0, bottom=-1.0, right=10.0, top=1.0),
        metadata={},
    )


def _analytical_config() -> FDTDConfig:
    """创建 ANALYTICAL 后端配置（无外部依赖）。"""
    return FDTDConfig(
        backend=FDTDBackend.ANALYTICAL,
        wavelength_start_um=1.5,
        wavelength_end_um=1.6,
        n_wavelengths=10,
    )


def _default_cosim_config() -> CoSimConfig:
    """创建默认联合仿真配置（ANALYTICAL 后端）。"""
    return CoSimConfig(
        device_id="test_component",
        fdtd_config=_analytical_config(),
    )


# =============================================================================
# TR-304.1: gdsfactory 波导 → FDTD 仿真流程顺畅
# =============================================================================
class TestTR3041GdsfactoryToFdtdFlow:
    """TR-304.1: gdsfactory 波导→FDTD 仿真流程顺畅。"""

    def test_straight_component_simulate(self):
        """直波导组件能完成完整仿真流程。"""
        component = _make_straight_component(length_um=10.0)
        result = simulate_gdsfactory_component(component, _default_cosim_config())
        assert isinstance(result, CoSimResult)
        assert result.simulation_status == "success"

    def test_simulate_returns_device(self):
        """仿真结果包含转换后的 PoLaRIS Device。"""
        component = _make_straight_component()
        result = simulate_gdsfactory_component(component, _default_cosim_config())
        assert result.device is not None
        assert result.device.device_id == "test_component"
        assert result.device.platform == "SOI"

    def test_simulate_returns_fdtd_result(self):
        """仿真结果包含 FDTD 原始结果。"""
        component = _make_straight_component()
        result = simulate_gdsfactory_component(component, _default_cosim_config())
        assert result.fdtd_result is not None
        assert result.fdtd_result.backend_used == FDTDBackend.ANALYTICAL

    def test_analytical_backend_runs_without_external_deps(self):
        """ANALYTICAL 后端无需 MEEP/Tidy3D 即可运行。"""
        component = _make_straight_component(length_um=5.0)
        config = CoSimConfig(
            device_id="wg",
            fdtd_config=FDTDConfig(
                backend=FDTDBackend.ANALYTICAL,
                wavelength_start_um=1.55,
                wavelength_end_um=1.55,
                n_wavelengths=1,
            ),
        )
        result = simulate_gdsfactory_component(component, config)
        assert result.n_wavelengths == 1

    def test_simulate_preserves_wavelength_range(self):
        """仿真结果保留配置的波长范围。"""
        component = _make_straight_component()
        config = CoSimConfig(
            device_id="wl_test",
            fdtd_config=FDTDConfig(
                backend=FDTDBackend.ANALYTICAL,
                wavelength_start_um=1.50,
                wavelength_end_um=1.60,
                n_wavelengths=20,
            ),
        )
        result = simulate_gdsfactory_component(component, config)
        assert result.fdtd_result.wavelengths_um[0] == pytest.approx(1.50)
        assert result.fdtd_result.wavelengths_um[-1] == pytest.approx(1.60)
        assert len(result.fdtd_result.wavelengths_um) == 20


# =============================================================================
# TR-304.2: 端口自动识别与 S 参数提取
# =============================================================================
class TestTR3042PortAutoDetectSParam:
    """TR-304.2: 端口自动识别与 S 参数提取。"""

    def test_port_names_extracted(self):
        """端口名从 gdsfactory Component 自动提取。"""
        component = _make_straight_component()
        result = simulate_gdsfactory_component(component, _default_cosim_config())
        assert "o1" in result.port_names
        assert "o2" in result.port_names
        assert result.n_ports == 2

    def test_port_order_name_alphabetical(self):
        """port_order='name' 按字母序排序。"""
        component = _make_mmi_component()  # o1, o2, o3
        config = CoSimConfig(
            device_id="mmi",
            fdtd_config=_analytical_config(),
            port_order="name",
        )
        result = simulate_gdsfactory_component(component, config)
        assert result.port_names == ["o1", "o2", "o3"]

    def test_port_order_position(self):
        """port_order='position' 按 (x, y) 坐标排序。"""
        component = _make_mmi_component()  # o1@(0,0), o2@(10,0.5), o3@(10,-0.5)
        config = CoSimConfig(
            device_id="mmi",
            fdtd_config=_analytical_config(),
            port_order="position",
        )
        result = simulate_gdsfactory_component(component, config)
        # 按 (x, y) 排序: o1(0,0) < o3(10,-0.5) < o2(10,0.5)
        assert result.port_names == ["o1", "o3", "o2"]

    def test_port_order_none_preserves_original(self):
        """port_order=None 保持 gdsfactory 原始端口顺序。"""
        component = _make_mmi_component()
        config = CoSimConfig(
            device_id="mmi",
            fdtd_config=_analytical_config(),
            port_order=None,
        )
        result = simulate_gdsfactory_component(component, config)
        assert result.port_names == ["o1", "o2", "o3"]

    def test_s_matrix_shape(self):
        """S 矩阵形状为 (n_ports, n_ports, n_wavelengths)。"""
        component = _make_straight_component()
        result = simulate_gdsfactory_component(component, _default_cosim_config())
        assert result.s_matrix.shape == (2, 2, 10)

    def test_s_matrix_complex_dtype(self):
        """S 矩阵为复数类型。"""
        component = _make_straight_component()
        result = simulate_gdsfactory_component(component, _default_cosim_config())
        assert result.s_matrix.dtype == complex

    def test_s_matrix_values_match_sdict(self):
        """S 矩阵值与 FDTD 结果的 s_params 字典一致。"""
        component = _make_straight_component()
        result = simulate_gdsfactory_component(component, _default_cosim_config())
        # ANALYTICAL 后端: s_params[(o1, o2)] = s21 数组
        # port_order='name' 排序后: ['o1', 'o2']
        # s_matrix[0, 1, :] = S_{o1, o2}（从 o2 入射到 o1 出射）
        # 但 ANALYTICAL 后端用 (in_port, out_port) = (o1, o2) 作为键
        # 需要确认键的顺序
        for key, arr in result.fdtd_result.s_params.items():
            p_out, p_in = key
            i = result.port_names.index(p_out)
            j = result.port_names.index(p_in)
            np.testing.assert_allclose(result.s_matrix[i, j, :], arr)

    def test_n_ports_matches_component(self):
        """端口数与组件端口数一致。"""
        component = _make_mmi_component()  # 3 端口
        config = CoSimConfig(
            device_id="mmi",
            fdtd_config=_analytical_config(),
            port_order=None,  # 保持原始顺序，避免排序影响
        )
        result = simulate_gdsfactory_component(component, config)
        assert result.n_ports == 3


# =============================================================================
# TR-304.3: 结果回传给 gdsfactory
# =============================================================================
class TestTR3043ResultReturnToGdsfactory:
    """TR-304.3: 结果回传给 gdsfactory。"""

    def test_touchstone_export(self, tmp_path):
        """S 参数能导出为 Touchstone 文件。"""
        component = _make_straight_component()
        result = simulate_gdsfactory_component(component, _default_cosim_config())
        output = export_cosim_to_touchstone(result, tmp_path / "straight.s2p")
        assert output == str(tmp_path / "straight.s2p")
        assert (tmp_path / "straight.s2p").exists()

    def test_touchstone_file_format(self, tmp_path):
        """Touchstone 文件格式正确（选项行 + 数据行）。"""
        component = _make_straight_component()
        result = simulate_gdsfactory_component(component, _default_cosim_config())
        output_path = tmp_path / "wg.s2p"
        export_cosim_to_touchstone(result, output_path)
        content = output_path.read_text(encoding="utf-8")
        # 选项行以 # 开头
        assert content.startswith("# ")
        # 包含频率单位 ghz
        assert "ghz" in content.split("\n")[0].lower()
        # 包含 S 参数 RI 格式
        assert "S RI" in content.split("\n")[0]
        # 数据行数 = 波长数（10 个波长）
        data_lines = [
            line for line in content.split("\n")
            if line and not line.startswith("!") and not line.startswith("#")
        ]
        assert len(data_lines) == 10

    def test_touchstone_freq_value(self, tmp_path):
        """Touchstone 频率值正确（c/λ，193414.5 GHz @ 1.55μm）。

        Touchstone 规范只支持 hz/khz/mhz/ghz，不支持 thz。
        来源: https://en.wikipedia.org/wiki/Touchstone_file
        """
        component = _make_straight_component()
        config = CoSimConfig(
            device_id="freq_test",
            fdtd_config=FDTDConfig(
                backend=FDTDBackend.ANALYTICAL,
                wavelength_start_um=1.55,
                wavelength_end_um=1.55,
                n_wavelengths=1,
            ),
        )
        result = simulate_gdsfactory_component(component, config)
        output_path = tmp_path / "freq.s2p"
        export_cosim_to_touchstone(result, output_path, freq_unit="ghz")
        content = output_path.read_text(encoding="utf-8")
        # 第一行数据: 频率 (GHz) = c / λ = 299792458 / 1.55e-6 / 1e9 ≈ 193414.5 GHz
        data_line = [
            line for line in content.split("\n")
            if line and not line.startswith("!") and not line.startswith("#")
        ][0]
        freq_ghz = float(data_line.split()[0])
        assert freq_ghz == pytest.approx(193414.5, rel=1e-3)

    def test_metadata_dict(self):
        """仿真结果能转换为 gdsfactory metadata 字典。"""
        component = _make_straight_component()
        result = simulate_gdsfactory_component(component, _default_cosim_config())
        metadata = cosim_to_gdsfactory_metadata(result)
        assert "simulation" in metadata
        assert metadata["simulation"]["backend"] == "analytical"
        assert metadata["simulation"]["ports"] == ["o1", "o2"]
        assert metadata["simulation"]["n_wavelengths"] == 10
        assert metadata["simulation"]["s_params_available"] is True
        assert "s_matrix_shape" in metadata
        assert metadata["s_matrix_shape"] == [2, 2, 10]
        assert "wavelengths_um" in metadata
        assert len(metadata["wavelengths_um"]) == 10

    def test_attach_metadata_to_component(self):
        """metadata 能写回 gdsfactory Component。"""
        component = _make_straight_component()
        result = simulate_gdsfactory_component(component, _default_cosim_config())
        attach_metadata_to_component(component, result)
        assert "polaris_cosim" in component.metadata
        assert component.metadata["polaris_cosim"]["simulation"]["backend"] == "analytical"

    def test_summary_string(self):
        """仿真摘要字符串格式正确。"""
        component = _make_straight_component()
        result = simulate_gdsfactory_component(component, _default_cosim_config())
        summary = get_cosim_summary(result)
        assert "gdsfactory 联合仿真结果摘要" in summary
        assert "后端: analytical" in summary
        assert "端口数: 2" in summary
        assert "o1" in summary and "o2" in summary


# =============================================================================
# R03 错误处理
# =============================================================================
class TestR03ErrorHandling:
    """R03 禁止 fall-back：所有错误路径必须 raise。"""

    def test_no_ports_raises(self):
        """组件无端口时 raise ValueError。"""
        component = MockComponent(
            name="empty",
            ports_list=[],
            bbox_obj=MockBbox(0, 0, 1, 1),
        )
        with pytest.raises(ValueError, match="无端口"):
            simulate_gdsfactory_component(component, _default_cosim_config())

    def test_duplicate_port_names_raises(self):
        """端口名重复时 raise ValueError。"""
        component = MockComponent(
            name="dup",
            ports_list=[
                MockPort(name="o1", orientation=0, width=0.5, center=(0, 0)),
                MockPort(name="o1", orientation=180, width=0.5, center=(10, 0)),
            ],
            bbox_obj=MockBbox(0, 0, 10, 0.5),
        )
        with pytest.raises(ValueError, match="端口名重复"):
            simulate_gdsfactory_component(component, _default_cosim_config())

    def test_invalid_port_order_raises(self):
        """不支持的端口排序方式 raise ValueError。"""
        component = _make_straight_component()
        config = CoSimConfig(
            device_id="test",
            fdtd_config=_analytical_config(),
            port_order="invalid",
        )
        with pytest.raises(ValueError, match="不支持的端口排序方式"):
            simulate_gdsfactory_component(component, config)

    def test_empty_port_names_raises(self):
        """build_s_matrix_from_sdict 空端口名 raise ValueError。"""
        with pytest.raises(ValueError, match="端口名列表不能为空"):
            build_s_matrix_from_sdict({("o1", "o2"): np.array([1.0 + 0j])}, [])

    def test_empty_s_params_raises(self):
        """build_s_matrix_from_sdict 空 S 参数 raise ValueError。"""
        with pytest.raises(ValueError, match="S 参数字典为空"):
            build_s_matrix_from_sdict({}, ["o1"])

    def test_port_not_in_list_raises(self):
        """S 参数字典端口名不在列表中 raise ValueError。"""
        s_params = {("o1", "o3"): np.array([1.0 + 0j])}
        with pytest.raises(ValueError, match="不在 port_names 列表中"):
            build_s_matrix_from_sdict(s_params, ["o1", "o2"])

    def test_inconsistent_array_length_raises(self):
        """S 参数数组长度不一致 raise ValueError。"""
        s_params = {
            ("o1", "o2"): np.array([1.0 + 0j, 2.0 + 0j]),
            ("o2", "o1"): np.array([1.0 + 0j]),  # 长度不一致
        }
        with pytest.raises(ValueError, match="数组长度.*不一致"):
            build_s_matrix_from_sdict(s_params, ["o1", "o2"])

    def test_failed_sim_touchstone_raises(self):
        """仿真失败时导出 Touchstone raise ValueError。"""
        component = _make_straight_component()
        result = simulate_gdsfactory_component(component, _default_cosim_config())
        result.simulation_status = "failed"
        with pytest.raises(ValueError, match="仿真状态为 'failed'"):
            export_cosim_to_touchstone(result, "/tmp/test.s2p")

    def test_empty_matrix_touchstone_raises(self):
        """S 矩阵为空时导出 Touchstone raise ValueError。"""
        component = _make_straight_component()
        result = simulate_gdsfactory_component(component, _default_cosim_config())
        result.s_matrix = np.zeros((0, 0, 0), dtype=complex)
        with pytest.raises(ValueError, match="S 矩阵为空"):
            export_cosim_to_touchstone(result, "/tmp/test.s2p")

    def test_failed_sim_metadata_raises(self):
        """仿真失败时生成 metadata raise ValueError。"""
        component = _make_straight_component()
        result = simulate_gdsfactory_component(component, _default_cosim_config())
        result.simulation_status = "failed"
        with pytest.raises(ValueError, match="仿真状态为 'failed'"):
            cosim_to_gdsfactory_metadata(result)

    def test_failed_sim_summary_raises(self):
        """仿真失败时生成摘要 raise ValueError。"""
        component = _make_straight_component()
        result = simulate_gdsfactory_component(component, _default_cosim_config())
        result.simulation_status = "failed"
        with pytest.raises(ValueError, match="仿真状态为 'failed'"):
            get_cosim_summary(result)

    def test_failed_sim_attach_raises(self):
        """仿真失败时附加 metadata raise ValueError。"""
        component = _make_straight_component()
        result = simulate_gdsfactory_component(component, _default_cosim_config())
        result.simulation_status = "failed"
        with pytest.raises(ValueError, match="仿真状态为 'failed'"):
            attach_metadata_to_component(component, result)

    def test_no_metadata_attribute_raises(self):
        """组件无 metadata 属性时 raise AttributeError。"""
        component = _make_straight_component()
        result = simulate_gdsfactory_component(component, _default_cosim_config())
        # 创建无 metadata 属性的 mock 对象
        class NoMetadata:
            name = "no_meta"

        with pytest.raises(AttributeError, match="无 metadata 属性"):
            attach_metadata_to_component(NoMetadata(), result)


# =============================================================================
# CoSimConfig 数据类
# =============================================================================
class TestCoSimConfig:
    """CoSimConfig 配置数据类。"""

    def test_defaults(self):
        """默认配置正确。"""
        config = CoSimConfig()
        assert config.device_id == "gdsfactory_component"
        assert config.import_config is None
        assert config.fdtd_config is None
        assert config.port_order == "name"

    def test_custom_config(self):
        """自定义配置正确。"""
        fdtd_config = FDTDConfig(backend=FDTDBackend.ANALYTICAL, n_wavelengths=5)
        import_config = DeviceImportConfig(platform="SiN", category="passive")
        config = CoSimConfig(
            device_id="custom",
            import_config=import_config,
            fdtd_config=fdtd_config,
            port_order="position",
        )
        assert config.device_id == "custom"
        assert config.import_config is import_config
        assert config.fdtd_config is fdtd_config
        assert config.port_order == "position"

    def test_with_import_config(self):
        """带导入配置的仿真正确运行。"""
        component = _make_straight_component()
        config = CoSimConfig(
            device_id="sin_wg",
            import_config=DeviceImportConfig(platform="SiN", name="sin_straight"),
            fdtd_config=_analytical_config(),
        )
        result = simulate_gdsfactory_component(component, config)
        assert result.device.platform == "SiN"
        assert result.device.name == "sin_straight"


# =============================================================================
# 集成测试
# =============================================================================
class TestIntegration:
    """集成测试。"""

    def test_full_workflow_mock(self, tmp_path):
        """完整工作流：mock 组件 → 仿真 → Touchstone + metadata。"""
        component = _make_straight_component(length_um=20.0)
        result = simulate_gdsfactory_component(component, _default_cosim_config())

        # 1. 仿真结果有效
        assert result.simulation_status == "success"
        assert result.n_ports == 2

        # 2. 导出 Touchstone
        ts_path = export_cosim_to_touchstone(result, tmp_path / "full.s2p")
        assert (tmp_path / "full.s2p").exists()

        # 3. 生成 metadata
        metadata = cosim_to_gdsfactory_metadata(result)
        assert metadata["simulation"]["backend"] == "analytical"

        # 4. 附加到组件
        attach_metadata_to_component(component, result)
        assert "polaris_cosim" in component.metadata

        # 5. 生成摘要
        summary = get_cosim_summary(result)
        assert "o1" in summary and "o2" in summary

    def test_importable_from_sim_package(self):
        """R304 符号可从 polaris.sim 顶层导入。"""
        from polaris.sim import (
            CoSimConfig,
            CoSimResult,
            simulate_gdsfactory_component,
        )
        assert CoSimConfig is not None
        assert CoSimResult is not None
        assert simulate_gdsfactory_component is not None

    @pytest.mark.skipif(not is_available(), reason="gdsfactory 未安装")
    def test_real_gdsfactory_integration(self):
        """真实 gdsfactory 组件联合仿真（Python 3.10-3.13）。"""
        import gdsfactory as gf

        gf.get_active_pdk()
        component = gf.components.straight(length=10.0, width=0.5)
        config = CoSimConfig(
            device_id="real_straight",
            fdtd_config=_analytical_config(),
        )
        result = simulate_gdsfactory_component(component, config)
        assert result.simulation_status == "success"
        assert result.n_ports >= 2


# =============================================================================
# 学术诚信
# =============================================================================
class TestAcademicIntegrity:
    """R02 学术诚信：参数/公式/常数可溯源。"""

    def test_module_docstring_has_references(self):
        """模块 docstring 包含文献引用。"""
        import polaris.sim.gdsfactory_cosim as mod
        docstring = mod.__doc__
        # 至少 5 个文献 URL
        assert "gdsfactory" in docstring
        assert "meep" in docstring.lower()
        assert "tidy3d" in docstring.lower()
        assert "touchstone" in docstring.lower()
        assert "pozar" in docstring.lower() or "Microwave Engineering" in docstring
        assert "taflove" in docstring.lower() or "Computational Electrodynamics" in docstring

    def test_speed_of_light_constant(self):
        """光速常数 c = 299792458 m/s（NIST CODATA 2018）。"""
        # 从 export_cosim_to_touchstone 源码中验证光速常数
        import inspect

        source = inspect.getsource(export_cosim_to_touchstone)
        assert "299_792_458" in source or "299792458" in source

    def test_s_matrix_convention(self):
        """S 矩阵约定（i=出射, j=入射）与 Pozar §4.4 一致。"""
        # 构造已知 S 参数验证矩阵索引
        s_params = {
            ("o1", "o1"): np.array([0.1 + 0.0j]),  # S11 反射
            ("o1", "o2"): np.array([0.9 + 0.0j]),  # S12 从 o2 到 o1
            ("o2", "o1"): np.array([0.9 + 0.0j]),  # S21 从 o1 到 o2
            ("o2", "o2"): np.array([0.1 + 0.0j]),  # S22 反射
        }
        s_matrix = build_s_matrix_from_sdict(s_params, ["o1", "o2"])
        # s_matrix[i, j, :] = S_{port_names[i], port_names[j]}
        # s_matrix[0, 1, 0] = S_{o1, o2} = 0.9（从 o2 入射到 o1 出射）
        assert s_matrix[0, 1, 0] == pytest.approx(0.9 + 0j)
        # s_matrix[1, 0, 0] = S_{o2, o1} = 0.9（从 o1 入射到 o2 出射）
        assert s_matrix[1, 0, 0] == pytest.approx(0.9 + 0j)
        # 对角线为反射
        assert s_matrix[0, 0, 0] == pytest.approx(0.1 + 0j)
        assert s_matrix[1, 1, 0] == pytest.approx(0.1 + 0j)

    def test_frequency_wavelength_conversion(self, tmp_path):
        """波长→频率转换 f = c/λ 正确（NIST CODATA 2018）。"""
        component = _make_straight_component()
        config = CoSimConfig(
            device_id="freq_conv",
            fdtd_config=FDTDConfig(
                backend=FDTDBackend.ANALYTICAL,
                wavelength_start_um=1.50,
                wavelength_end_um=1.50,
                n_wavelengths=1,
            ),
        )
        result = simulate_gdsfactory_component(component, config)
        # f = c / λ = 299792458 / 1.50e-6 / 1e9 = 199861.6 GHz
        output_path = tmp_path / "freq.s2p"
        export_cosim_to_touchstone(result, output_path, freq_unit="ghz")
        content = output_path.read_text(encoding="utf-8")
        data_line = [
            line for line in content.split("\n")
            if line and not line.startswith("!") and not line.startswith("#")
        ][0]
        freq_ghz = float(data_line.split()[0])
        assert freq_ghz == pytest.approx(199861.6, rel=1e-3)

    def test_touchstone_ri_format(self, tmp_path):
        """Touchstone 使用 RI（实部-虚部）格式（业界标准）。"""
        component = _make_straight_component()
        result = simulate_gdsfactory_component(component, _default_cosim_config())
        output_path = tmp_path / "ri.s2p"
        export_cosim_to_touchstone(result, output_path)
        content = output_path.read_text(encoding="utf-8")
        # 选项行应包含 "S RI"
        first_line = content.split("\n")[0]
        assert "S RI" in first_line
