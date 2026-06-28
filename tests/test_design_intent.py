"""R20 Design Intent 流程引擎测试（原理图→意图→PDK 三层映射）。

测试覆盖:
1. 配置验证（IntentConfig + 引擎初始化）
2. 原理图解析（合法 + 非法输入）
3. 布局意图生成（拓扑排序 + 深度分层）
4. 布线意图生成（曼哈顿路径 + 弯曲约束）
5. 约束意图生成（设计规则结构化）
6. PDK 器件映射
7. 约束传播
8. 意图验证（成功 + 失败）
9. 完整流程 run()
10. 无 fall-back 验证（R03）

来源（R02 学术诚信）:
- Synopsys OptoDesigner: https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner.html
- layout-aware SDL: https://doi.org/10.1117/12.2252001
- SiEPIC EBeam PDK 设计规则: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
"""

from __future__ import annotations

import pytest

from polaris.flow.design_intent import DesignIntentEngine, IntentConfig

# ---------------------------------------------------------------------------
# 测试夹具：MZI 原理图 + PDK 库 + 设计规则
# ---------------------------------------------------------------------------

# 设计规则（来源: SiEPIC EBeam PDK 公开文档）
# https://github.com/SiEPIC/SiEPIC_EBeam_PDK
SAMPLE_RULES = {
    "min_waveguide_width": 0.4,  # μm，SiEPIC EBeam 最小条形波导宽度
    "min_bend_radius": 5.0,  # μm，SiEPIC EBeam 最小弯曲半径
    "min_spacing": 2.0,  # μm，典型 PIC 最小器件间距
    "max_path_length": 1000.0,  # μm，最大路径长度
}

SAMPLE_PDK = {
    "grating_coupler": {
        "cell_name": "GC_TE_1310",
        "ports": ["in", "out"],
    },
    "directional_coupler": {
        "cell_name": "DC_10um",
        "ports": ["in1", "in2", "out1", "out2"],
    },
    "waveguide": {
        "cell_name": "WG_strip_500nm",
        "ports": ["in", "out"],
    },
}


def _make_mzi_schematic() -> dict:
    """构建 MZI 原理图（2 GC + 2 DC + 2 波导臂）。"""
    return {
        "devices": [
            {
                "id": "gc_in",
                "type": "grating_coupler",
                "params": {"period": 0.66, "n_periods": 20, "width": 0.5},
                "ports": ["in", "out"],
            },
            {
                "id": "dc1",
                "type": "directional_coupler",
                "params": {"length": 10.0, "gap": 0.2, "width": 0.5},
                "ports": ["in1", "in2", "out1", "out2"],
            },
            {
                "id": "wg_arm1",
                "type": "waveguide",
                "params": {"length": 50.0, "width": 0.5},
                "ports": ["in", "out"],
            },
            {
                "id": "wg_arm2",
                "type": "waveguide",
                "params": {"length": 55.0, "width": 0.5},
                "ports": ["in", "out"],
            },
            {
                "id": "dc2",
                "type": "directional_coupler",
                "params": {"length": 10.0, "gap": 0.2, "width": 0.5},
                "ports": ["in1", "in2", "out1", "out2"],
            },
            {
                "id": "gc_out",
                "type": "grating_coupler",
                "params": {"period": 0.66, "n_periods": 20, "width": 0.5},
                "ports": ["in", "out"],
            },
        ],
        "connections": [
            {"src": "gc_in", "src_port": "out", "dst": "dc1", "dst_port": "in1"},
            {"src": "dc1", "src_port": "out1", "dst": "wg_arm1", "dst_port": "in"},
            {"src": "dc1", "src_port": "out2", "dst": "wg_arm2", "dst_port": "in"},
            {"src": "wg_arm1", "src_port": "out", "dst": "dc2", "dst_port": "in1"},
            {"src": "wg_arm2", "src_port": "out", "dst": "dc2", "dst_port": "in2"},
            {"src": "dc2", "src_port": "out1", "dst": "gc_out", "dst_port": "in"},
        ],
    }


def _make_engine() -> DesignIntentEngine:
    """构建配置完整的 Design Intent 引擎。"""
    config = IntentConfig(
        design_rules=dict(SAMPLE_RULES),
        pdk_library=dict(SAMPLE_PDK),
        grid_pitch=0.01,
        placement_spacing=50.0,
    )
    return DesignIntentEngine(config)


# ---------------------------------------------------------------------------
# 1. 配置验证
# ---------------------------------------------------------------------------


class TestConfigValidation:
    """IntentConfig 与引擎初始化验证。"""

    def test_config_creation(self):
        """IntentConfig 创建与默认值。"""
        config = IntentConfig()
        assert config.design_rules == {}
        assert config.pdk_library == {}
        assert config.grid_pitch == 0.01
        assert config.placement_spacing == 50.0

    def test_engine_init_valid(self):
        """引擎初始化（合法 config）。"""
        engine = _make_engine()
        assert engine.config.placement_spacing == 50.0
        assert "min_waveguide_width" in engine.config.design_rules

    def test_engine_init_invalid_config_type(self):
        """引擎初始化（非法 config 类型 → raise，R03 禁止 fall-back）。"""
        with pytest.raises(ValueError, match="IntentConfig"):
            DesignIntentEngine("not_a_config")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# 2. 原理图解析
# ---------------------------------------------------------------------------


class TestParseSchematic:
    """原理图解析测试。"""

    def test_parse_valid_schematic(self):
        """解析合法 MZI 原理图。"""
        engine = _make_engine()
        parsed = engine.parse_schematic(_make_mzi_schematic())
        assert len(parsed["devices"]) == 6
        assert len(parsed["connections"]) == 6
        assert "device_map" in parsed
        assert "gc_in" in parsed["device_map"]
        assert parsed["device_map"]["gc_in"]["type"] == "grating_coupler"

    def test_parse_missing_devices_key(self):
        """缺少 devices 键 → raise。"""
        engine = _make_engine()
        with pytest.raises(ValueError, match="devices"):
            engine.parse_schematic({"connections": []})

    def test_parse_device_missing_field(self):
        """器件缺少必需字段 → raise。"""
        engine = _make_engine()
        bad_sch = {
            "devices": [{"id": "d1", "type": "waveguide"}],  # 缺 params/ports
            "connections": [],
        }
        with pytest.raises(ValueError, match="params"):
            engine.parse_schematic(bad_sch)

    def test_parse_connection_invalid_port(self):
        """连接引用不存在的端口 → raise。"""
        engine = _make_engine()
        bad_sch = {
            "devices": [
                {"id": "d1", "type": "waveguide",
                 "params": {"length": 10}, "ports": ["in", "out"]},
                {"id": "d2", "type": "waveguide",
                 "params": {"length": 10}, "ports": ["in", "out"]},
            ],
            "connections": [
                {"src": "d1", "src_port": "bad_port",
                 "dst": "d2", "dst_port": "in"},
            ],
        }
        with pytest.raises(ValueError, match="bad_port"):
            engine.parse_schematic(bad_sch)


# ---------------------------------------------------------------------------
# 3. 布局意图生成
# ---------------------------------------------------------------------------


class TestLayoutIntent:
    """布局意图生成测试（拓扑排序 + 深度分层放置）。"""

    def test_generate_layout_intent(self):
        """生成布局意图：所有器件被放置，位置在栅格上。"""
        engine = _make_engine()
        parsed = engine.parse_schematic(_make_mzi_schematic())
        layout = engine.generate_layout_intent(parsed)
        devices = layout["devices"]
        assert len(devices) == 6
        for dev in devices:
            assert "x" in dev and "y" in dev and "orientation" in dev
            # 位置应在栅格上（grid_pitch=0.01）
            assert round(dev["x"], 6) == dev["x"]
            assert round(dev["y"], 6) == dev["y"]

    def test_layout_topological_order(self):
        """拓扑排序：gc_in 在 dc1 之前（深度更小）。"""
        engine = _make_engine()
        parsed = engine.parse_schematic(_make_mzi_schematic())
        layout = engine.generate_layout_intent(parsed)
        placement = layout["placement"]
        # gc_in 深度 0，dc1 深度 1
        assert placement["gc_in"]["x"] < placement["dc1"]["x"]
        # dc1 深度 1，wg_arm 深度 2
        assert placement["dc1"]["x"] < placement["wg_arm1"]["x"]

    def test_layout_branch_y_offset(self):
        """分支器件（wg_arm1/arm2）沿 y 轴分开。"""
        engine = _make_engine()
        parsed = engine.parse_schematic(_make_mzi_schematic())
        layout = engine.generate_layout_intent(parsed)
        p = layout["placement"]
        # wg_arm1 和 wg_arm2 同深度，y 应不同
        assert p["wg_arm1"]["y"] != p["wg_arm2"]["y"]
        # 两者 x 应相同（同深度）
        assert p["wg_arm1"]["x"] == p["wg_arm2"]["x"]

    def test_layout_cyclic_schematic_raises(self):
        """含环原理图 → raise（R03 禁止 fall-back 跳过环）。"""
        engine = _make_engine()
        cyclic = {
            "devices": [
                {"id": "a", "type": "waveguide",
                 "params": {"length": 10}, "ports": ["in", "out"]},
                {"id": "b", "type": "waveguide",
                 "params": {"length": 10}, "ports": ["in", "out"]},
            ],
            "connections": [
                {"src": "a", "src_port": "out", "dst": "b", "dst_port": "in"},
                {"src": "b", "src_port": "out", "dst": "a", "dst_port": "in"},
            ],
        }
        parsed = engine.parse_schematic(cyclic)
        with pytest.raises(ValueError, match="环"):
            engine.generate_layout_intent(parsed)


# ---------------------------------------------------------------------------
# 4. 布线意图生成
# ---------------------------------------------------------------------------


class TestRoutingIntent:
    """布线意图生成测试（曼哈顿路径 + 弯曲约束）。"""

    def test_generate_routing_intent(self):
        """生成布线意图：每条连接生成 L 形路径。"""
        engine = _make_engine()
        parsed = engine.parse_schematic(_make_mzi_schematic())
        engine.generate_layout_intent(parsed)
        routing = engine.generate_routing_intent(parsed["connections"])
        assert len(routing) == 6
        for _net_id, route in routing.items():
            assert len(route["path"]) == 3  # L 形: 3 个点
            assert route["bend_radius"] == 5.0
            assert "min_bend_radius" in route["constraints"]

    def test_routing_requires_layout(self):
        """未先生成布局意图 → raise（R03 禁止 fall-back）。"""
        engine = _make_engine()
        with pytest.raises(ValueError, match="布局意图"):
            engine.generate_routing_intent([])


# ---------------------------------------------------------------------------
# 5. 约束意图生成
# ---------------------------------------------------------------------------


class TestConstraintIntent:
    """约束意图生成测试。"""

    def test_generate_constraint_intent(self):
        """生成约束意图：设计规则结构化。"""
        engine = _make_engine()
        constraints = engine.generate_constraint_intent(SAMPLE_RULES)
        assert constraints["waveguide"]["min_width"] == 0.4
        assert constraints["bend"]["min_radius"] == 5.0
        assert constraints["placement"]["min_spacing"] == 2.0
        assert constraints["routing"]["max_length"] == 1000.0

    def test_constraint_missing_required_rule(self):
        """缺少必需规则 → raise（R03 禁止 fall-back 默认值）。"""
        engine = _make_engine()
        incomplete = {"min_waveguide_width": 0.4}  # 缺 min_bend_radius
        with pytest.raises(ValueError, match="min_bend_radius"):
            engine.generate_constraint_intent(incomplete)

    def test_constraint_empty_rules_raises(self):
        """空设计规则 → raise。"""
        engine = _make_engine()
        with pytest.raises(ValueError, match="非空"):
            engine.generate_constraint_intent({})


# ---------------------------------------------------------------------------
# 6. PDK 器件映射
# ---------------------------------------------------------------------------


class TestMapToPDK:
    """PDK 器件映射测试。"""

    def test_map_to_pdk(self):
        """意图 → PDK 器件实例映射。"""
        engine = _make_engine()
        parsed = engine.parse_schematic(_make_mzi_schematic())
        layout = engine.generate_layout_intent(parsed)
        result = engine.map_to_pdk(layout, SAMPLE_PDK)
        assert result["count"] == 6
        for inst in result["instances"]:
            assert "instance_id" in inst
            assert "pdk_cell" in inst
            assert inst["device_type"] in SAMPLE_PDK
        # 验证 cell_name 映射
        gc_inst = [i for i in result["instances"]
                   if i["device_type"] == "grating_coupler"]
        assert gc_inst[0]["pdk_cell"] == "GC_TE_1310"

    def test_map_to_pdk_missing_type(self):
        """器件类型不在 PDK 库 → raise（R03 禁止 fall-back 默认映射）。"""
        engine = _make_engine()
        parsed = engine.parse_schematic(_make_mzi_schematic())
        layout = engine.generate_layout_intent(parsed)
        incomplete_pdk = {"grating_coupler": SAMPLE_PDK["grating_coupler"]}
        with pytest.raises(ValueError, match="不在 PDK 库"):
            engine.map_to_pdk(layout, incomplete_pdk)

    def test_map_to_pdk_empty_library(self):
        """空 PDK 库 → raise。"""
        engine = _make_engine()
        with pytest.raises(ValueError, match="非空"):
            engine.map_to_pdk({"devices": []}, {})


# ---------------------------------------------------------------------------
# 7. 约束传播
# ---------------------------------------------------------------------------


class TestPropagateConstraints:
    """约束传播测试。"""

    def test_propagate_constraints(self):
        """约束传播到器件参数。"""
        engine = _make_engine()
        parsed = engine.parse_schematic(_make_mzi_schematic())
        layout = engine.generate_layout_intent(parsed)
        constraints = engine.generate_constraint_intent(SAMPLE_RULES)
        intent = {"devices": layout["devices"], "constraints": constraints}
        propagated = engine.propagate_constraints(intent)
        # 波导类器件应有 min_width 约束
        wg_constraints = propagated["wg_arm1"]
        rules = [c["rule"] for c in wg_constraints]
        assert "min_width" in rules
        assert "min_spacing" in rules
        # 所有器件应有 min_spacing 约束
        for _dev_id, dev_constraints in propagated.items():
            rule_names = [c["rule"] for c in dev_constraints]
            assert "min_spacing" in rule_names


# ---------------------------------------------------------------------------
# 8. 意图验证
# ---------------------------------------------------------------------------


class TestValidateIntent:
    """意图验证测试。"""

    def test_validate_intent_success(self):
        """合法意图验证通过。"""
        engine = _make_engine()
        parsed = engine.parse_schematic(_make_mzi_schematic())
        layout = engine.generate_layout_intent(parsed)
        routing = engine.generate_routing_intent(parsed["connections"])
        constraints = engine.generate_constraint_intent(SAMPLE_RULES)
        intent = {
            "devices": layout["devices"],
            "routing": routing,
            "constraints": constraints,
        }
        assert engine.validate_intent(intent) is True

    def test_validate_intent_width_violation(self):
        """波导宽度违规 → raise（R03 禁止 fall-back 返回 False）。"""
        engine = _make_engine()
        # 波导宽度 0.3 < min_width 0.4
        sch = _make_mzi_schematic()
        sch["devices"][2]["params"]["width"] = 0.3  # wg_arm1
        parsed = engine.parse_schematic(sch)
        layout = engine.generate_layout_intent(parsed)
        constraints = engine.generate_constraint_intent(SAMPLE_RULES)
        intent = {"devices": layout["devices"], "constraints": constraints}
        with pytest.raises(ValueError, match="宽度"):
            engine.validate_intent(intent)

    def test_validate_intent_spacing_violation(self):
        """器件间距违规 → raise。"""
        engine = _make_engine()
        parsed = engine.parse_schematic(_make_mzi_schematic())
        layout = engine.generate_layout_intent(parsed)
        # 手动将两个器件移到相同位置
        layout["devices"][0]["x"] = 0.0
        layout["devices"][0]["y"] = 0.0
        layout["devices"][1]["x"] = 0.0
        layout["devices"][1]["y"] = 0.0
        constraints = engine.generate_constraint_intent(SAMPLE_RULES)
        intent = {"devices": layout["devices"], "constraints": constraints}
        with pytest.raises(ValueError, match="间距"):
            engine.validate_intent(intent)


# ---------------------------------------------------------------------------
# 9. 完整流程
# ---------------------------------------------------------------------------


class TestRunComplete:
    """完整流程 run() 测试。"""

    def test_run_complete_flow(self):
        """完整流程：原理图→意图→PDK→验证。"""
        engine = _make_engine()
        result = engine.run(_make_mzi_schematic())
        # 验证所有意图层齐全
        assert "devices" in result
        assert "routing" in result
        assert "constraints" in result
        assert "propagated_constraints" in result
        assert "pdk_instances" in result
        # 验证器件数
        assert len(result["devices"]) == 6
        assert len(result["routing"]) == 6
        assert result["pdk_instances"]["count"] == 6
        # 验证约束传播覆盖所有器件
        assert len(result["propagated_constraints"]) == 6

    def test_run_missing_rule_raises(self):
        """run() 缺少必需设计规则 → raise（R03 禁止 fall-back）。"""
        config = IntentConfig(
            design_rules={"min_waveguide_width": 0.4},  # 缺其他规则
            pdk_library=dict(SAMPLE_PDK),
        )
        engine = DesignIntentEngine(config)
        with pytest.raises(ValueError, match="min_bend_radius"):
            engine.run(_make_mzi_schematic())

    def test_run_empty_pdk_raises(self):
        """run() 空 PDK 库 → raise（R03 禁止 fall-back）。"""
        config = IntentConfig(
            design_rules=dict(SAMPLE_RULES),
            pdk_library={},  # 空
        )
        engine = DesignIntentEngine(config)
        with pytest.raises(ValueError, match="非空"):
            engine.run(_make_mzi_schematic())


# ---------------------------------------------------------------------------
# 10. 三层映射完整性验证
# ---------------------------------------------------------------------------


class TestThreeLayerMapping:
    """原理图→意图→PDK 三层映射完整性验证。"""

    def test_three_layers_present(self):
        """验证三层映射齐全：原理图层→意图层→PDK 层。"""
        engine = _make_engine()
        result = engine.run(_make_mzi_schematic())
        # 第一层：原理图层（器件 + 连接）
        assert len(engine._schematic_cache["devices"]) == 6
        assert len(engine._schematic_cache["connections"]) == 6
        # 第二层：意图层（布局 + 布线 + 约束）
        assert len(result["devices"]) == 6  # 布局意图
        assert len(result["routing"]) == 6  # 布线意图
        assert "waveguide" in result["constraints"]  # 约束意图
        # 第三层：PDK 层（器件实例）
        assert result["pdk_instances"]["count"] == 6
        for inst in result["pdk_instances"]["instances"]:
            assert inst["pdk_cell"] in {
                "GC_TE_1310", "DC_10um", "WG_strip_500nm"
            }
