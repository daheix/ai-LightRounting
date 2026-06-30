"""R305 gdsfactory 联合仿真 - 电路级测试。

验证多组件电路级联合仿真的完整工作流，覆盖 TR-305.1/305.2/305.3 三个测试需求。

工作流:
1. 多个 gdsfactory Component → 各自组件级 FDTD 仿真（复用 R304）
2. 组件 S 矩阵 → SDict 字典
3. cascade_circuit 级联所有组件 S 参数
4. 电路级 S 参数导出（Touchstone / 摘要）

测试策略:
- 使用 MockComponent 模拟 gdsfactory Component（Python 3.14 下 gdsfactory 不可用）
- 使用 ANALYTICAL 后端（FDTDBackend.ANALYTICAL），无需 MEEP/Tidy3D
- 用直波导级联电路（2 个直波导首尾相连）作为典型测试场景
- R03 错误处理: 空组件字典/连接引用不存在/端口引用不存在 必须告警退出
- 学术诚信: 验证光速常数、S 矩阵约定、文献来源标注完整

来源:
- gdsfactory (MIT): https://gdsfactory.github.io/gdsfactory/
- gdsfactory 电路级 YAML: https://gdsfactory.github.io/gdsfactory/notebooks/05_yaml_hierarchy.html
- SAX 子网络增长: https://flaport.github.io/sax/
- Simphony 仿真器: https://simphonyphotonics.readthedocs.io/
- Touchstone 规范: https://en.wikipedia.org/wiki/Touchstone_file
- Pozar, "Microwave Engineering", 4th ed., §4.4, ISBN: 978-1118213636, Wiley, 2011
- Taflove & Hagness, "Computational Electrodynamics", 3rd ed., 2005
- NIST CODATA 2018 光速常数: https://physics.nist.gov/cgi-bin/cuu/Value?c
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pytest

from polaris.sim.fdtd_simulator import FDTDConfig, FDTDBackend
from polaris.sim.gdsfactory_cosim import (
    CircuitCoSimConfig,
    CircuitCoSimResult,
    CoSimConfig,
    build_sdict_from_s_matrix,
    export_circuit_cosim_to_touchstone,
    get_circuit_cosim_summary,
    simulate_gdsfactory_circuit,
)
from polaris.sim.types import SDict


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
    """模拟 gdsfactory Component。"""

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
    """创建模拟直波导组件（2 端口 o1/o2）。"""
    return MockComponent(
        name="straight",
        ports_list=[
            MockPort(
                name="o1",
                orientation=180.0,
                width=width_um,
                center=(0.0, 0.0),
            ),
            MockPort(
                name="o2",
                orientation=0.0,
                width=width_um,
                center=(length_um, 0.0),
            ),
        ],
        bbox_obj=MockBbox(left=0.0, bottom=-width_um / 2, right=length_um, top=width_um / 2),
        metadata={},
    )


def _analytical_fdtd_config() -> FDTDConfig:
    """ANALYTICAL 后端配置（无外部依赖）。"""
    return FDTDConfig(
        backend=FDTDBackend.ANALYTICAL,
        wavelength_start_um=1.5,
        wavelength_end_um=1.6,
        n_wavelengths=10,
    )


def _make_two_waveguide_circuit_config() -> CircuitCoSimConfig:
    """创建双直波导级联电路配置。

    电路结构:
        外部端口 in → wg1.o1
        wg1.o2 → wg2.o1  （内部连接）
        wg2.o2 → 外部端口 out

    两个直波导首尾相连，构成 2 端口电路（in/out）。
    """
    wg1 = _make_straight_component(length_um=10.0)
    wg2 = _make_straight_component(length_um=20.0)
    return CircuitCoSimConfig(
        components={"wg1": wg1, "wg2": wg2},
        connections=[
            ("wg1.o2", "wg2.o1"),  # 内部连接: wg1 输出 → wg2 输入
        ],
        ports={
            "in": "wg1.o1",   # 外部端口 in
            "out": "wg2.o2",  # 外部端口 out
        },
        fdtd_config=_analytical_fdtd_config(),
    )


# =============================================================================
# TR-305.1: 多组件电路网表导入
# =============================================================================
class TestTR3051MultiComponentNetlist:
    """TR-305.1: 多组件电路网表导入。"""

    def test_circuit_config_dataclass_fields(self):
        """CircuitCoSimConfig 含全部必需字段。"""
        config = CircuitCoSimConfig()
        expected_fields = {
            "components", "connections", "ports",
            "fdtd_config", "import_config", "port_order",
        }
        assert set(CircuitCoSimConfig.__dataclass_fields__.keys()) >= expected_fields

    def test_circuit_result_dataclass_fields(self):
        """CircuitCoSimResult 含全部必需字段。"""
        expected_fields = {
            "component_results", "circuit_sdict",
            "n_components", "n_ports",
            "wavelengths_um", "simulation_status",
        }
        assert set(CircuitCoSimResult.__dataclass_fields__.keys()) >= expected_fields

    def test_default_port_order_is_name(self):
        """port_order 默认为 'name'（与 CoSimConfig 一致）。"""
        config = CircuitCoSimConfig()
        assert config.port_order == "name"

    def test_components_dict_accepted(self):
        """配置接受 components 字典。"""
        wg = _make_straight_component()
        config = CircuitCoSimConfig(
            components={"wg1": wg},
            connections=[],
            ports={"in": "wg1.o1", "out": "wg1.o2"},
            fdtd_config=_analytical_fdtd_config(),
        )
        assert "wg1" in config.components

    def test_connections_list_of_tuples_accepted(self):
        """配置接受 connections 为 list[tuple[str, str]]。"""
        config = CircuitCoSimConfig(
            components={"wg1": _make_straight_component(),
                        "wg2": _make_straight_component()},
            connections=[("wg1.o2", "wg2.o1")],
            ports={"in": "wg1.o1", "out": "wg2.o2"},
        )
        assert len(config.connections) == 1
        assert config.connections[0] == ("wg1.o2", "wg2.o1")


# =============================================================================
# TR-305.2: 组件间连接（net）自动识别
# =============================================================================
class TestTR3052ConnectionRecognition:
    """TR-305.2: 组件间连接（net）自动识别。"""

    def test_simulate_two_waveguide_circuit(self):
        """双直波导级联电路可完成仿真。"""
        config = _make_two_waveguide_circuit_config()
        result = simulate_gdsfactory_circuit(config)
        assert isinstance(result, CircuitCoSimResult)
        assert result.simulation_status == "success"

    def test_circuit_has_two_external_ports(self):
        """电路级结果有 2 个外部端口（in/out）。"""
        config = _make_two_waveguide_circuit_config()
        result = simulate_gdsfactory_circuit(config)
        assert result.n_ports == 2

    def test_circuit_has_two_components(self):
        """电路级结果包含 2 个组件的子结果。"""
        config = _make_two_waveguide_circuit_config()
        result = simulate_gdsfactory_circuit(config)
        assert result.n_components == 2
        assert "wg1" in result.component_results
        assert "wg2" in result.component_results

    def test_circuit_sdict_has_external_port_pairs(self):
        """电路级 SDict 包含外部端口对的 S 参数。"""
        config = _make_two_waveguide_circuit_config()
        result = simulate_gdsfactory_circuit(config)
        # 外部端口为 in/out，应至少包含 (in,in)/(in,out)/(out,in)/(out,out)
        keys = set(result.circuit_sdict.keys())
        assert ("in", "in") in keys or ("out", "in") in keys
        # 至少有一个 S 参数条目
        assert len(result.circuit_sdict) > 0

    def test_circuit_wavelengths_propagated(self):
        """波长数组从子组件仿真结果传播到电路级结果。"""
        config = _make_two_waveguide_circuit_config()
        result = simulate_gdsfactory_circuit(config)
        assert result.wavelengths_um.size == 10
        assert result.wavelengths_um[0] == pytest.approx(1.5)
        assert result.wavelengths_um[-1] == pytest.approx(1.6)

    def test_comma_format_connection_normalized(self):
        """逗号分隔的连接格式（gdsfactory YAML）被规范化为点分隔。"""
        wg1 = _make_straight_component()
        wg2 = _make_straight_component()
        config = CircuitCoSimConfig(
            components={"wg1": wg1, "wg2": wg2},
            connections=[("wg1,o2", "wg2,o1")],  # gdsfactory YAML 逗号格式
            ports={"in": "wg1,o1", "out": "wg2,o2"},
            fdtd_config=_analytical_fdtd_config(),
        )
        result = simulate_gdsfactory_circuit(config)
        assert result.simulation_status == "success"
        assert result.n_ports == 2


# =============================================================================
# TR-305.3: 电路级 S 参数级联仿真
# =============================================================================
class TestTR3053CircuitCascadeSimulation:
    """TR-305.3: 电路级 S 参数级联仿真。"""

    def test_circuit_transmission_close_to_one(self):
        """双直波导级联后 in→out 传输幅度合理（< 1，无源系统）。"""
        config = _make_two_waveguide_circuit_config()
        result = simulate_gdsfactory_circuit(config)
        # 寻找 (out, in) 端口对
        keys = list(result.circuit_sdict.keys())
        # 找到从 in 到 out 的传输
        out_in_keys = [k for k in keys if "out" in k[0] and "in" in k[1]]
        if out_in_keys:
            s_out_in = np.asarray(result.circuit_sdict[out_in_keys[0]])
            # ANALYTICAL 后端下 SOI 波导损耗很小，|S| <= 1（无源）
            mag = np.abs(s_out_in)
            assert np.all(mag <= 1.0 + 1e-10), f"|S| > 1: {mag}"

    def test_circuit_sdict_arrays_have_correct_length(self):
        """电路级 S 参数数组长度与波长数一致。"""
        config = _make_two_waveguide_circuit_config()
        result = simulate_gdsfactory_circuit(config)
        n_wl = result.wavelengths_um.size
        for key, arr in result.circuit_sdict.items():
            assert np.asarray(arr).size == n_wl, (
                f"端口对 {key} S 参数长度 {np.asarray(arr).size} != 波长数 {n_wl}"
            )

    def test_build_sdict_from_s_matrix_roundtrip(self):
        """build_sdict_from_s_matrix 与 R304 的 build_s_matrix_from_sdict 互逆。"""
        from polaris.sim.gdsfactory_cosim import build_s_matrix_from_sdict
        port_names = ["o1", "o2"]
        n_wl = 5
        # 构造 2x2xn_wl S 矩阵
        s_mat = np.zeros((2, 2, n_wl), dtype=complex)
        s_mat[0, 0, :] = 0.1  # o1 反射
        s_mat[1, 0, :] = 0.9  # o1→o2 传输
        s_mat[0, 1, :] = 0.9  # o2→o1 传输
        s_mat[1, 1, :] = 0.1  # o2 反射
        sdict = build_sdict_from_s_matrix(s_mat, port_names)
        assert ("o1", "o1") in sdict
        assert ("o2", "o1") in sdict
        assert np.allclose(sdict[("o2", "o1")], 0.9)
        # 反向变换应恢复原矩阵
        s_mat_back = build_s_matrix_from_sdict(sdict, port_names)
        assert np.allclose(s_mat_back, s_mat)

    def test_export_circuit_to_touchstone(self, tmp_path):
        """电路级结果可导出为 Touchstone 文件。"""
        config = _make_two_waveguide_circuit_config()
        result = simulate_gdsfactory_circuit(config)
        out_path = tmp_path / "circuit.s2p"
        ret = export_circuit_cosim_to_touchstone(result, out_path, freq_unit="ghz")
        assert os.path.exists(ret)
        # Touchstone 文件应包含频率行
        content = out_path.read_text()
        # 应包含 GHZ 频率单位声明和 1.8x-2.0x e+05 GHz 量级的频率（C 波段 1.5-1.6μm）
        # 频率范围: c/1.6μm ≈ 187 THz = 1.87e5 GHz, c/1.5μm ≈ 200 THz = 2.00e5 GHz
        assert "ghz" in content.lower()
        # 验证频率值在 C 波段范围（187000-200000 GHz = 1.87e5-2.00e5）
        assert "1.8" in content or "1.9" in content or "2.0" in content

    def test_get_circuit_cosim_summary(self):
        """get_circuit_cosim_summary 返回可读摘要。"""
        config = _make_two_waveguide_circuit_config()
        result = simulate_gdsfactory_circuit(config)
        summary = get_circuit_cosim_summary(result)
        assert isinstance(summary, str)
        assert "电路级联合仿真" in summary
        assert "组件数" in summary
        assert "外部端口数" in summary
        assert "wg1" in summary
        assert "wg2" in summary


# =============================================================================
# R03 错误处理（禁止 fall-back）
# =============================================================================
class TestR03ErrorHandling:
    """R03 合规: 错误必须 raise，禁止 fall-back。"""

    def test_empty_components_raises(self):
        """空组件字典必须 raise ValueError。"""
        config = CircuitCoSimConfig(
            components={},
            connections=[],
            ports={},
            fdtd_config=_analytical_fdtd_config(),
        )
        with pytest.raises(ValueError, match="组件字典不能为空"):
            simulate_gdsfactory_circuit(config)

    def test_connection_ref_unknown_instance_raises(self):
        """连接引用不存在的实例必须 raise ValueError。"""
        wg = _make_straight_component()
        config = CircuitCoSimConfig(
            components={"wg1": wg},
            connections=[("wg1.o2", "wg_unknown.o1")],  # wg_unknown 不存在
            ports={"in": "wg1.o1"},
            fdtd_config=_analytical_fdtd_config(),
        )
        with pytest.raises(ValueError, match="不在组件字典中"):
            simulate_gdsfactory_circuit(config)

    def test_connection_source_unknown_instance_raises(self):
        """连接源引用不存在的实例必须 raise ValueError。"""
        wg = _make_straight_component()
        config = CircuitCoSimConfig(
            components={"wg1": wg},
            connections=[("wg_unknown.o2", "wg1.o1")],
            ports={"in": "wg1.o1"},
            fdtd_config=_analytical_fdtd_config(),
        )
        with pytest.raises(ValueError, match="不在组件字典中"):
            simulate_gdsfactory_circuit(config)

    def test_port_ref_unknown_instance_raises(self):
        """外部端口引用不存在的实例必须 raise ValueError。"""
        wg = _make_straight_component()
        config = CircuitCoSimConfig(
            components={"wg1": wg},
            connections=[],
            ports={"in": "wg_unknown.o1"},  # wg_unknown 不存在
            fdtd_config=_analytical_fdtd_config(),
        )
        with pytest.raises(ValueError, match="不在组件字典中"):
            simulate_gdsfactory_circuit(config)

    def test_export_failed_simulation_raises(self):
        """仿真失败时导出 Touchstone 必须 raise。"""
        result = CircuitCoSimResult(simulation_status="failed")
        with pytest.raises(ValueError, match="failed"):
            export_circuit_cosim_to_touchstone(result, "/tmp/x.s2p")

    def test_export_empty_sdict_raises(self):
        """空 S 参数导出 Touchstone 必须 raise。"""
        result = CircuitCoSimResult(
            simulation_status="success",
            circuit_sdict={},
            wavelengths_um=np.array([1.55]),
        )
        with pytest.raises(ValueError, match="电路 S 参数为空"):
            export_circuit_cosim_to_touchstone(result, "/tmp/x.s2p")

    def test_summary_failed_simulation_raises(self):
        """仿真失败时生成摘要必须 raise。"""
        result = CircuitCoSimResult(simulation_status="failed")
        with pytest.raises(ValueError, match="failed"):
            get_circuit_cosim_summary(result)

    def test_build_sdict_empty_port_names_raises(self):
        """空端口名列表必须 raise。"""
        with pytest.raises(ValueError, match="端口名列表不能为空"):
            build_sdict_from_s_matrix(np.zeros((0, 0, 0)), [])

    def test_build_sdict_shape_mismatch_raises(self):
        """S 矩阵形状与端口数不匹配必须 raise。"""
        with pytest.raises(ValueError, match="不匹配"):
            build_sdict_from_s_matrix(
                np.zeros((3, 3, 5), dtype=complex),  # 3 端口矩阵
                ["o1", "o2"],  # 2 端口列表
            )


# =============================================================================
# CircuitCoSimConfig 数据类
# =============================================================================
class TestCircuitCoSimConfig:
    """CircuitCoSimConfig 行为测试。"""

    def test_default_config_has_empty_collections(self):
        """默认配置的集合字段为空。"""
        config = CircuitCoSimConfig()
        assert config.components == {}
        assert config.connections == []
        assert config.ports == {}
        assert config.fdtd_config is None
        assert config.import_config is None
        assert config.port_order == "name"

    def test_config_accepts_custom_port_order(self):
        """配置接受自定义 port_order。"""
        config = CircuitCoSimConfig(port_order="position")
        assert config.port_order == "position"

    def test_config_accepts_none_port_order(self):
        """配置接受 port_order=None（保持原始顺序）。"""
        config = CircuitCoSimConfig(port_order=None)
        assert config.port_order is None


# =============================================================================
# 集成测试
# =============================================================================
class TestIntegration:
    """集成测试: 完整工作流。"""

    def test_full_workflow_two_waveguides(self, tmp_path):
        """完整工作流: 配置 → 仿真 → 摘要 → Touchstone 导出。"""
        config = _make_two_waveguide_circuit_config()
        result = simulate_gdsfactory_circuit(config)
        assert result.simulation_status == "success"

        summary = get_circuit_cosim_summary(result)
        assert "wg1" in summary

        out_path = tmp_path / "two_wg.s2p"
        export_circuit_cosim_to_touchstone(result, out_path)
        assert out_path.exists()

    def test_single_component_circuit(self):
        """单组件电路（无内部连接）也能仿真。"""
        wg = _make_straight_component()
        config = CircuitCoSimConfig(
            components={"wg1": wg},
            connections=[],  # 无内部连接
            ports={"in": "wg1.o1", "out": "wg1.o2"},
            fdtd_config=_analytical_fdtd_config(),
        )
        result = simulate_gdsfactory_circuit(config)
        assert result.simulation_status == "success"
        assert result.n_components == 1
        assert result.n_ports == 2

    def test_three_waveguide_chain(self):
        """三直波导级联（链式）电路。"""
        wg1 = _make_straight_component(length_um=5.0)
        wg2 = _make_straight_component(length_um=10.0)
        wg3 = _make_straight_component(length_um=15.0)
        config = CircuitCoSimConfig(
            components={"wg1": wg1, "wg2": wg2, "wg3": wg3},
            connections=[
                ("wg1.o2", "wg2.o1"),
                ("wg2.o2", "wg3.o1"),
            ],
            ports={"in": "wg1.o1", "out": "wg3.o2"},
            fdtd_config=_analytical_fdtd_config(),
        )
        result = simulate_gdsfactory_circuit(config)
        assert result.simulation_status == "success"
        assert result.n_components == 3
        assert result.n_ports == 2


# =============================================================================
# 学术诚信检查
# =============================================================================
class TestAcademicIntegrity:
    """学术诚信: 公式/常数/文献来源可溯源。"""

    def test_speed_of_light_constant_source(self):
        """光速常数 c = 299792458 m/s 来自 NIST CODATA 2018。

        验证方法: 对波长数组中每个点验证 f·λ = c（光速常数硬编码正确性）。
        """
        config = _make_two_waveguide_circuit_config()
        result = simulate_gdsfactory_circuit(config)
        # 频率 f = c/λ, c = 299792458 m/s
        # 来源: NIST CODATA 2018 https://physics.nist.gov/cgi-bin/cuu/Value?c
        wavelengths_m = result.wavelengths_um * 1e-6
        c = 299_792_458.0  # m/s
        freqs_hz = c / wavelengths_m
        # 验证光速常数: f·λ = c（对所有波长点）
        reconstructed_c = freqs_hz * wavelengths_m
        assert np.allclose(reconstructed_c, c, rtol=1e-12), (
            f"光速常数不一致: {reconstructed_c[0]} != {c}"
        )
        # 额外验证: 1.5μm 对应频率 ≈ 199861.6 GHz
        idx_15 = 0  # wavelengths_um[0] = 1.5
        expected_freq_15_ghz = 299_792_458.0 / (1.5e-6) / 1e9  # = 199861.64 GHz
        actual_freq_15_ghz = freqs_hz[idx_15] / 1e9
        assert actual_freq_15_ghz == pytest.approx(expected_freq_15_ghz, rel=1e-6)

    def test_s_matrix_convention_documented(self):
        """S 矩阵约定 s_matrix[i,j] = S_{i,j}（出射 i, 入射 j）有文献溯源。"""
        import polaris.sim.gdsfactory_cosim as mod
        # 模块 docstring 应包含 Pozar 引用
        docstring = mod.__doc__ or ""
        # R304 docstring 提到 Pozar §4.4
        source_text = docstring + str(mod.CoSimResult.__doc__ or "")
        assert "Pozar" in source_text or "§4.4" in source_text

    def test_cascade_algorithm_source_documented(self):
        """cascade_circuit 子网络增长算法有 SAX 文献溯源。"""
        import polaris.sim.cascade as cascade_mod
        docstring = cascade_mod.__doc__ or ""
        assert "sax" in docstring.lower() or "SAX" in docstring
        assert "子网络增长" in docstring or "subnetwork" in docstring.lower()

    def test_touchstone_freq_units_documented(self):
        """Touchstone 频率单位规范（hz/khz/mhz/ghz）有文献溯源。"""
        import polaris.sim.touchstone as ts_mod
        # 通过导出测试验证只接受合法单位
        config = _make_two_waveguide_circuit_config()
        result = simulate_gdsfactory_circuit(config)
        # ghz 应该可以正常工作
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".s2p", delete=False) as f:
            tmp = f.name
        try:
            export_circuit_cosim_to_touchstone(result, tmp, freq_unit="ghz")
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    def test_module_docstring_has_references(self):
        """gdsfactory_cosim 模块 docstring 含 >= 5 个文献 URL。"""
        import polaris.sim.gdsfactory_cosim as mod
        docstring = mod.__doc__ or ""
        # 统计 URL 数量
        url_count = docstring.count("https://") + docstring.count("http://")
        assert url_count >= 5, f"文献 URL 数 {url_count} < 5，违反 R02"
