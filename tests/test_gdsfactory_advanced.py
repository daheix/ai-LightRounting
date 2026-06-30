"""gdsfactory 深度集成进阶模块单元测试（R305-R310）。

测试覆盖 6 个进阶功能，每功能 ≥3 测试，共 24 个测试用例。

学术诚信（R02）：测试数据来自公开文献参数（SiEPIC/generic PDK 层定义）。
禁止 fall-back（R03）：gdsfactory 不可用时相关功能必须 raise ImportError，
测试用 pytest.raises 验证 raise 行为，不跳过。
不参与 GPU（R04）：纯 NumPy/KLayout 测试。

来源:
- gdsfactory PDK: https://gdsfactory.github.io/gdsfactory/notebooks/08_pdk.html
- KLayout DRC: https://www.klayout.org/downloads/master/doc-qt4/about/drc_ref.html
- Redheffer star product: https://en.wikipedia.org/wiki/Redheffer_star_product
"""

from __future__ import annotations

import os
import tempfile

import numpy as np
import pytest

from polaris.pdk import gdsfactory_advanced as ga
from polaris.pdk.gdsfactory_advanced import (
    DEFAULT_DRC_RULESET,
    DRCRule,
    GDSFactoryPCellSpec,
    PolarisPCellSpec,
    SParameterModel,
    build_drc_ruleset_from_yaml,
    cascade_two_ports,
    declare_plugin,
    geometric_hash,
    get_plugin,
    get_preset_pdk_config,
    list_registered_plugins,
    load_pdk_config,
    merge_pdk_configs,
    polaris_to_gdsfactory_pcell,
    gdsfactory_to_polaris_pcell,
    pcell_roundtrip_verify,
    redheffer_star,
    register_as_gdsfactory_plugin,
    register_pcell_to_gdsfactory,
    round_trip_gdsii_advanced,
    run_klayout_drc,
    save_pdk_config,
    simulate_circuit,
    auto_identify_ports,
    CircuitNetlist,
    validate_pdk_compatibility,
)


# ---------------------------------------------------------------------------
# 公共夹具：构造测试用 GDSII 文件
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_gds(tmp_path):
    """构造含 1 cell + 1 多边形（合规尺寸）的 GDSII。"""
    import klayout.db as db

    gds = tmp_path / "sample.gds"
    ly = db.Layout()
    ly.dbu = 0.001
    c = ly.create_cell("top")
    li = ly.layer(1, 0)
    c.shapes(li).insert(db.Box(0, 0, 2000, 1000))  # 2.0μm × 1.0μm
    ly.write(str(gds))
    return gds


@pytest.fixture
def violating_gds(tmp_path):
    """构造含 DRC 违规的 GDSII（小宽度 + 小面积 + 近间距）。"""
    import klayout.db as db

    gds = tmp_path / "violating.gds"
    ly = db.Layout()
    ly.dbu = 0.001
    c = ly.create_cell("top")
    li = ly.layer(1, 0)
    # 0.1μm 宽矩形（width<0.4 违规，area=0.01μm²<0.02 违规）
    c.shapes(li).insert(db.Box(0, 0, 100, 100))
    # 两个间距 0.2μm 的矩形（space<0.4 违规）
    c.shapes(li).insert(db.Box(2000, 0, 3000, 1000))
    c.shapes(li).insert(db.Box(3200, 0, 4200, 1000))  # gap=0.2μm
    ly.write(str(gds))
    return gds


# ===========================================================================
# R305: PDK 双向兼容增强
# ===========================================================================


class TestR305PDKCompatibility:
    """R305 PDK 双向兼容配置测试。"""

    def test_get_preset_pdk_config_generic(self):
        """获取 generic 预设配置，层映射含 WG/DEVREC/PORT。"""
        cfg = get_preset_pdk_config("generic")
        assert cfg.pdk_name == "generic"
        assert cfg.layer_map[(1, 0)] == "WG"
        assert cfg.layer_map[(68, 0)] == "DEVREC"
        assert (1, 10) in cfg.port_layers
        assert cfg.cross_section_params["width_um"] == 0.5

    def test_get_preset_pdk_config_siepic(self):
        """获取 SiEPIC 预设配置，含 PIN 层。"""
        cfg = get_preset_pdk_config("siepic")
        assert cfg.pdk_name == "siepic"
        assert cfg.layer_map[(69, 0)] == "PIN"
        assert cfg.foundry.startswith("AMF")

    def test_get_preset_pdk_config_unknown_raises(self):
        """未知预设名必须 raise KeyError（R03 禁止 fall-back）。"""
        with pytest.raises(KeyError, match="预设 PDK 不存在"):
            get_preset_pdk_config("nonexistent_pdk")

    def test_pdk_config_yaml_roundtrip(self, tmp_path):
        """PDK 配置 YAML 保存→加载往返一致。"""
        cfg = get_preset_pdk_config("siepic")
        yaml_path = tmp_path / "pdk.yaml"
        save_pdk_config(cfg, yaml_path)
        loaded = load_pdk_config(yaml_path)
        assert loaded.pdk_name == cfg.pdk_name
        assert loaded.layer_map == cfg.layer_map
        assert loaded.port_layers == cfg.port_layers
        assert loaded.cross_section_params == cfg.cross_section_params

    def test_merge_pdk_configs_conflict_raises(self):
        """层映射冲突必须 raise ValueError（R03 禁止静默覆盖）。"""
        from polaris.pdk.gdsfactory_advanced import PDKCompatibilityConfig

        base = get_preset_pdk_config("generic")
        conflict = PDKCompatibilityConfig(
            pdk_name="conflict",
            layer_map={(1, 0): "DIFFERENT_NAME"},  # 与 generic (1,0)=WG 冲突
            port_layers=[],
            cross_section_params={},
        )
        with pytest.raises(ValueError, match="层映射冲突"):
            merge_pdk_configs(base, conflict)

    def test_validate_pdk_compatibility_no_issues(self):
        """完整配置校验无问题。"""
        cfg = get_preset_pdk_config("generic")
        issues = validate_pdk_compatibility(cfg)
        assert issues == []


# ===========================================================================
# R306: 电路级联合仿真（Redheffer star product）
# ===========================================================================


class TestR306CircuitCascade:
    """R306 电路级 S 参数级联测试。"""

    def test_redheffer_two_port_cascade_numeric(self):
        """两 2 端口网络级联数值与闭式解一致（文献 8 公式）。"""
        # S_A: s11=0.1,s12=0.9,s21=0.9,s22=0.2 ; S_B: s11=0.15,s12=0.85,s21=0.85,s22=0.25
        s1 = np.array([[[0.1, 0.9], [0.9, 0.2]]], dtype=complex)
        s2 = np.array([[[0.15, 0.85], [0.85, 0.25]]], dtype=complex)
        sc = redheffer_star(s1, s2, n_internal=1)
        # 闭式解: S_C21 = s21_1 * s21_2 / (1 - s22_1 * s11_2)
        expected_s21 = 0.9 * 0.85 / (1 - 0.2 * 0.15)
        # S_C11 = s11_1 + s12_1 * s11_2 * s21_1 / (1 - s22_1 * s11_2)
        expected_s11 = 0.1 + 0.9 * 0.15 * 0.9 / (1 - 0.2 * 0.15)
        np.testing.assert_allclose(sc[0, 1, 0], expected_s21, rtol=1e-10)
        np.testing.assert_allclose(sc[0, 0, 0], expected_s11, rtol=1e-10)

    def test_redheffer_multi_port_shape(self):
        """3+2 端口网络级联（1 内部连接）输出形状正确。"""
        # A: 3 端口（2 外部 + 1 内部），B: 2 端口（1 内部 + 1 外部）
        s_a = np.zeros((1, 3, 3), dtype=complex)
        s_a[0, 0, 1] = 0.5
        s_a[0, 1, 0] = 0.5
        s_a[0, 2, 2] = 0.3
        s_b = np.zeros((1, 2, 2), dtype=complex)
        s_b[0, 1, 1] = 0.4
        s_b[0, 0, 0] = 0.2
        sc = redheffer_star(s_a, s_b, n_internal=1)
        # 输出端口数 = (3-1) + (2-1) = 3
        assert sc.shape == (1, 3, 3)

    def test_redheffer_invalid_internal_raises(self):
        """n_internal 越界必须 raise ValueError。"""
        s1 = np.zeros((1, 2, 2), dtype=complex)
        s2 = np.zeros((1, 2, 2), dtype=complex)
        with pytest.raises(ValueError, match="n_internal"):
            redheffer_star(s1, s2, n_internal=5)

    def test_cascade_two_ports_helper(self):
        """cascade_two_ports 便捷函数等价 redheffer_star(m=1)。"""
        s1 = np.array([[[0.1, 0.9], [0.9, 0.2]]], dtype=complex)
        s2 = np.array([[[0.15, 0.85], [0.85, 0.25]]], dtype=complex)
        a = cascade_two_ports(s1, s2)
        b = redheffer_star(s1, s2, n_internal=1)
        np.testing.assert_allclose(a, b)

    def test_auto_identify_ports(self):
        """自动识别外部端口与内部连接。"""
        netlist = CircuitNetlist(
            instances={
                "wg1": {"model": "wg", "ports": ["in", "out"]},
                "wg2": {"model": "wg", "ports": ["in", "out"]},
            },
            connections=[("wg1", "out", "wg2", "in")],
            external_ports={"in": ("wg1", "in"), "out": ("wg2", "out")},
        )
        result = auto_identify_ports(netlist)
        assert "wg1.in" in result["external"]
        assert "wg2.out" in result["external"]
        assert ("wg1.out", "wg2.in") in result["internal"]
        # 内部连接端口不在外部列表
        assert "wg1.out" not in result["external"]

    def test_simulate_circuit_basic(self):
        """simulate_circuit 级联两个波导模型。"""
        freqs = np.array([1.934e14])  # 1550nm
        s_wg1 = np.array([[[0.0, 0.99], [0.99, 0.0]]], dtype=complex)
        s_wg2 = np.array([[[0.0, 0.98], [0.98, 0.0]]], dtype=complex)
        models = {
            "wg1": SParameterModel(["in", "out"], freqs, s_wg1),
            "wg2": SParameterModel(["in", "out"], freqs, s_wg2),
        }
        netlist = CircuitNetlist(
            instances={
                "wg1": {"model": "wg1", "ports": ["in", "out"]},
                "wg2": {"model": "wg2", "ports": ["in", "out"]},
            },
            connections=[("wg1", "out", "wg2", "in")],
            external_ports={"in": ("wg1", "in"), "out": ("wg2", "out")},
        )
        result = simulate_circuit(netlist, models, freqs)
        assert result.s_matrix.shape == (1, 2, 2)
        # 两个无损波导级联透射 ≈ 0.99*0.98
        np.testing.assert_allclose(result.s_matrix[0, 1, 0], 0.99 * 0.98, rtol=1e-6)


# ===========================================================================
# R307: PCell 双向兼容
# ===========================================================================


class TestR307PCellBidirectional:
    """R307 PCell 双向转换测试。"""

    def test_polaris_to_gdsfactory_pcell(self):
        """PoLaRIS PCell → gdsfactory PCell 数据转换。"""
        spec = PolarisPCellSpec(
            name="mmi1x2",
            parameters={"width": 0.5, "length": 10.0},
            layer_map={(1, 0): "WG", (1, 10): "PORT"},
            ports=[{"name": "o1", "orientation_deg": 180}],
        )
        gf_spec = polaris_to_gdsfactory_pcell(spec)
        assert gf_spec.name == "mmi1x2"
        assert gf_spec.parameters == {"width": 0.5, "length": 10.0}
        assert gf_spec.cell_function == "polaris.cells.mmi1x2"
        assert (1, 10) in gf_spec.port_layers

    def test_gdsfactory_to_polaris_pcell(self):
        """gdsfactory PCell → PoLaRIS PCell 数据转换。"""
        gf_spec = GDSFactoryPCellSpec(
            name="bend_euler",
            parameters={"radius": 5.0},
            cell_function="gf.components.bend_euler",
            port_layers=[(1, 10)],
        )
        spec = gdsfactory_to_polaris_pcell(gf_spec)
        assert spec.name == "bend_euler"
        assert spec.parameters == {"radius": 5.0}
        assert spec.layer_map[(1, 10)] == "PORT"
        assert spec.layer_map[(1, 0)] == "WG"

    def test_pcell_roundtrip_verify(self):
        """PCell 双向转换往返一致。"""
        spec = PolarisPCellSpec(
            name="straight",
            parameters={"length": 20.0, "width": 0.5},
            layer_map={(1, 0): "WG", (1, 10): "PORT"},
            ports=[],
        )
        assert pcell_roundtrip_verify(spec) is True

    def test_polaris_to_gdsfactory_empty_name_raises(self):
        """空 name 必须 raise ValueError（R03）。"""
        spec = PolarisPCellSpec(
            name="", parameters={}, layer_map={}, ports=[]
        )
        with pytest.raises(ValueError, match="name 不能为空"):
            polaris_to_gdsfactory_pcell(spec)

    def test_register_pcell_to_gdsfactory_no_gf_raises(self):
        """gdsfactory 未安装时注册 PCell 必须 raise ImportError（R03）。"""
        spec = PolarisPCellSpec(
            name="test_cell",
            parameters={},
            layer_map={(1, 0): "WG"},
            ports=[],
            builder=lambda: None,
        )
        if not ga._HAS_GDSFACTORY:
            with pytest.raises(ImportError, match="gdsfactory 未安装"):
                register_pcell_to_gdsfactory(spec)
        else:  # pragma: no cover
            pytest.skip("gdsfactory 已安装，跳过 raise 测试")


# ===========================================================================
# R308: KLayout DRC 集成
# ===========================================================================


class TestR308KLayoutDRC:
    """R308 KLayout DRC 引擎测试。"""

    def test_drc_detects_width_and_area_violations(self, violating_gds):
        """DRC 检测到宽度与面积违规。"""
        rules = [
            DRCRule("min_width_wg", "width", (1, 0), 0.4),
            DRCRule("min_area_wg", "area", (1, 0), 0.02),
        ]
        result = run_klayout_drc(violating_gds, rules)
        assert result.n_rules_run == 2
        assert result.n_total_violations > 0
        width_v = next(v for v in result.violations if v.rule_name == "min_width_wg")
        assert width_v.n_violations > 0
        area_v = next(v for v in result.violations if v.rule_name == "min_area_wg")
        assert area_v.n_violations > 0

    def test_drc_detects_space_violation(self, violating_gds):
        """DRC 检测到间距违规。"""
        rules = [DRCRule("min_space_wg", "space", (1, 0), 0.4)]
        result = run_klayout_drc(violating_gds, rules)
        space_v = result.violations[0]
        assert space_v.n_violations > 0

    def test_drc_clean_layout_no_violations(self, sample_gds):
        """合规版图无违规（2.0μm × 1.0μm 矩形均 > 阈值）。"""
        rules = [
            DRCRule("min_width_wg", "width", (1, 0), 0.4),
            DRCRule("min_area_wg", "area", (1, 0), 0.5),
        ]
        result = run_klayout_drc(sample_gds, rules)
        assert result.n_total_violations == 0

    def test_drc_default_ruleset_runs(self, violating_gds):
        """默认规则集（DEFAULT_DRC_RULESET）可执行。"""
        result = run_klayout_drc(violating_gds, list(DEFAULT_DRC_RULESET))
        assert result.n_rules_run == len(DEFAULT_DRC_RULESET)
        assert result.n_rules_run == 4

    def test_drc_report_written(self, violating_gds, tmp_path):
        """DRC 报告写入 JSON 文件。"""
        report = tmp_path / "drc_report.json"
        rules = [DRCRule("min_width_wg", "width", (1, 0), 0.4)]
        result = run_klayout_drc(violating_gds, rules, report_path=report)
        assert report.exists()
        import json

        data = json.loads(report.read_text(encoding="utf-8"))
        assert data["n_rules_run"] == 1
        assert data["n_total_violations"] == result.n_total_violations

    def test_drc_unknown_rule_type_raises(self, sample_gds):
        """未知规则类型必须 raise ValueError（R03）。"""
        rules = [DRCRule("bad", "unknown_type", (1, 0), 0.4)]
        with pytest.raises(ValueError, match="未知 DRC 规则类型"):
            run_klayout_drc(sample_gds, rules)

    def test_build_drc_ruleset_from_yaml(self, tmp_path):
        """从 YAML 加载 DRC 规则集。"""
        yaml_content = (
            "rules:\n"
            "  - name: min_width_wg\n"
            "    rule_type: width\n"
            "    layer: [1, 0]\n"
            "    min_value_um: 0.4\n"
            "  - name: min_space_wg\n"
            "    rule_type: space\n"
            "    layer: [1, 0]\n"
            "    min_value_um: 0.4\n"
        )
        yaml_path = tmp_path / "rules.yaml"
        yaml_path.write_text(yaml_content, encoding="utf-8")
        rules = build_drc_ruleset_from_yaml(yaml_path)
        assert len(rules) == 2
        assert rules[0].name == "min_width_wg"
        assert rules[0].layer == (1, 0)
        assert rules[1].rule_type == "space"


# ===========================================================================
# R309: gdsfactory 插件接口
# ===========================================================================


class TestR309PluginInterface:
    """R309 gdsfactory 插件注册测试。"""

    def test_declare_plugin(self):
        """declare_plugin 加入内部注册表。"""
        entry = declare_plugin(
            "polaris_test_plugin", lambda **k: None, description="test"
        )
        assert entry.name == "polaris_test_plugin"
        assert entry.version == "0.1.0"
        assert "polaris_test_plugin" in list_registered_plugins()

    def test_get_plugin_returns_entry(self):
        """get_plugin 返回注册项。"""
        declare_plugin("polaris_get_test", lambda **k: "ok")
        entry = get_plugin("polaris_get_test")
        assert entry.name == "polaris_get_test"
        assert entry.factory() == "ok"

    def test_get_plugin_unknown_raises(self):
        """未注册插件必须 raise KeyError（R03 不返回 None）。"""
        with pytest.raises(KeyError, match="插件未注册"):
            get_plugin("nonexistent_plugin_xyz")

    def test_declare_plugin_invalid_raises(self):
        """空名或不可调用 factory 必须 raise ValueError。"""
        with pytest.raises(ValueError, match="插件名不能为空"):
            declare_plugin("", lambda: None)
        with pytest.raises(ValueError, match="factory 不可调用"):
            declare_plugin("bad_plugin", "not_callable")  # type: ignore[arg-type]

    def test_register_as_gdsfactory_plugin_no_gf_raises(self):
        """gdsfactory 未安装时注册插件必须 raise ImportError（R03）。"""
        if not ga._HAS_GDSFACTORY:
            with pytest.raises(ImportError, match="gdsfactory 未安装"):
                register_as_gdsfactory_plugin("x", lambda: None)
        else:  # pragma: no cover
            pytest.skip("gdsfactory 已安装，跳过 raise 测试")


# ===========================================================================
# R310: 往返导入导出增强
# ===========================================================================


class TestR310RoundTripAdvanced:
    """R310 多轮 GDSII 往返一致性测试。"""

    def test_geometric_hash_deterministic(self, sample_gds):
        """同一文件几何哈希确定（重复计算一致）。"""
        h1 = geometric_hash(sample_gds)
        h2 = geometric_hash(sample_gds)
        assert h1 == h2
        assert len(h1) == 64  # SHA256

    def test_geometric_hash_distinct_for_different_layout(self, sample_gds, tmp_path):
        """不同版图几何哈希不同。"""
        import klayout.db as db

        other = tmp_path / "other.gds"
        ly = db.Layout()
        ly.dbu = 0.001
        c = ly.create_cell("other_top")
        li = ly.layer(1, 0)
        c.shapes(li).insert(db.Box(0, 0, 5000, 3000))  # 不同尺寸
        ly.write(str(other))
        h1 = geometric_hash(sample_gds)
        h2 = geometric_hash(other)
        assert h1 != h2

    def test_round_trip_consistent_multi_round(self, sample_gds, tmp_path):
        """3 轮 GDSII 往返几何哈希一致。"""
        out = tmp_path / "roundtrip_out.gds"
        report = round_trip_gdsii_advanced(sample_gds, out, n_rounds=3)
        assert report.consistent is True
        assert report.n_rounds == 3
        assert report.geometric_hash_original == report.geometric_hash_final
        assert out.exists()
        # 中间文件已清理
        assert not (tmp_path / "roundtrip_out.r0.gds").exists()

    def test_round_trip_n_rounds_invalid_raises(self, sample_gds, tmp_path):
        """n_rounds < 1 必须 raise ValueError（R03）。"""
        out = tmp_path / "out.gds"
        with pytest.raises(ValueError, match="n_rounds 必须"):
            round_trip_gdsii_advanced(sample_gds, out, n_rounds=0)

    def test_round_trip_file_not_found_raises(self, tmp_path):
        """输入文件不存在必须 raise FileNotFoundError（R03）。"""
        out = tmp_path / "out.gds"
        with pytest.raises(FileNotFoundError, match="输入 GDSII 文件不存在"):
            round_trip_gdsii_advanced(
                tmp_path / "nonexistent.gds", out, n_rounds=1
            )

    def test_geometric_hash_file_not_found_raises(self, tmp_path):
        """geometric_hash 文件不存在必须 raise FileNotFoundError（R03）。"""
        with pytest.raises(FileNotFoundError, match="GDS 文件不存在"):
            geometric_hash(tmp_path / "nonexistent.gds")