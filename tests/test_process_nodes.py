"""process_nodes 模块测试（P1-3 深化，第28轮）。

测试 CMOS photonics 工艺节点元数据与查询 API。
对标 Cadence Innovus / Synopsys ICC2 的工艺节点支持能力。

来源:
- GF Fotonix: https://www.globalfoundries.com/technology-innovation/silicon-photonics
- Tower/OpenLight: https://www.openlightphotonics.com/
- IHP SG25H5: https://www.ihp-microelectronics.com/fileadmin/user_upload/flyers_photonics2023.pdf
"""

from __future__ import annotations

import pytest

from polaris.pdk.process_nodes import (
    CMOS_PROCESS_NODES,
    ProcessNode,
    cmos_process_node_count,
    get_process_node,
    get_process_node_for_foundry,
    list_foundries_with_process_node,
    list_process_nodes,
    list_process_nodes_by_cmos_node,
    list_process_nodes_by_foundry,
    list_process_nodes_by_material,
    parse_process_node_string,
    suggest_process_node_for_circuit,
)


class TestProcessNodeDataclass:
    """ProcessNode 数据类测试。"""

    def test_frozen_dataclass(self) -> None:
        """ProcessNode 应为 frozen dataclass。"""
        node = ProcessNode(
            name="test",
            foundry="TestFoundry",
            cmos_node_nm=45,
            photonic_layer_nm=220,
            material_platform="SOI",
            wafer_size_mm=300,
            integration_type="monolithic",
        )
        assert node.name == "test"
        with pytest.raises((AttributeError, TypeError)):
            node.name = "other"  # type: ignore[misc]

    def test_default_sources_empty(self) -> None:
        """默认 sources 应为空列表。"""
        node = ProcessNode(
            name="t",
            foundry="t",
            cmos_node_nm=0,
            photonic_layer_nm=220,
            material_platform="SOI",
            wafer_size_mm=100,
            integration_type="photonic_only",
        )
        assert node.sources == []
        assert node.notes == ""


class TestCmosProcessNodesRegistry:
    """CMOS_PROCESS_NODES 注册表测试。"""

    def test_registry_non_empty(self) -> None:
        """注册表应非空。"""
        assert len(CMOS_PROCESS_NODES) > 0

    def test_registry_count(self) -> None:
        """应有 13 个公开工艺节点（第89轮新增 4 个）。"""
        assert cmos_process_node_count() == 13

    def test_gf_fotonix_45clo_exists(self) -> None:
        """应含 GF Fotonix 45CLO（45nm CMOS photonics）。"""
        assert "GF_Fotonix_45CLO" in CMOS_PROCESS_NODES
        node = CMOS_PROCESS_NODES["GF_Fotonix_45CLO"]
        assert node.cmos_node_nm == 45
        assert node.foundry == "GlobalFoundries"
        assert node.material_platform == "SOI"
        assert node.wafer_size_mm == 300

    def test_gf_fotonix_90wg_exists(self) -> None:
        """应含 GF Fotonix 90WG。"""
        assert "GF_Fotonix_90WG" in CMOS_PROCESS_NODES
        node = CMOS_PROCESS_NODES["GF_Fotonix_90WG"]
        assert node.cmos_node_nm == 90

    def test_tower_ph18da_exists(self) -> None:
        """应含 Tower PH18DA（OpenLight）。"""
        assert "Tower_PH18DA" in CMOS_PROCESS_NODES
        node = CMOS_PROCESS_NODES["Tower_PH18DA"]
        assert node.cmos_node_nm == 180
        assert node.foundry == "Tower Semiconductor"

    def test_ihp_sg25h5_exists(self) -> None:
        """应含 IHP SG25H5（250nm BiCMOS）。"""
        assert "IHP_SG25H5" in CMOS_PROCESS_NODES
        node = CMOS_PROCESS_NODES["IHP_SG25H5"]
        assert node.cmos_node_nm == 250
        assert node.foundry == "IHP Microelectronics"

    def test_intel_300mm_exists(self) -> None:
        """应含 Intel 300mm CMOS photonics。"""
        assert "Intel_300mm_CMOS_Ph" in CMOS_PROCESS_NODES

    def test_amf_130nm_exists(self) -> None:
        """应含 AMF 130nm CMOS。"""
        assert "AMF_130nm_CMOS" in CMOS_PROCESS_NODES
        node = CMOS_PROCESS_NODES["AMF_130nm_CMOS"]
        assert node.cmos_node_nm == 130

    def test_aim_pure_photonic(self) -> None:
        """AIM 应为纯光子平台（cmos_node_nm=0）。"""
        node = CMOS_PROCESS_NODES["AIM_300mm_SOI"]
        assert node.cmos_node_nm == 0
        assert node.integration_type == "photonic_only"

    def test_lionix_sin_platform(self) -> None:
        """LioniX TriPleX 应为 SiN 平台。"""
        node = CMOS_PROCESS_NODES["LioniX_TriPleX"]
        assert node.material_platform == "SiN"
        assert node.cmos_node_nm == 0

    def test_hyperlight_lnoi_platform(self) -> None:
        """HyperLight 应为 LNOI 平台。"""
        node = CMOS_PROCESS_NODES["HyperLight_LNOI"]
        assert node.material_platform == "LNOI"
        assert node.cmos_node_nm == 0

    def test_all_nodes_have_sources(self) -> None:
        """所有节点应有来源 URL（学术诚信）。"""
        for name, node in CMOS_PROCESS_NODES.items():
            assert len(node.sources) > 0, f"{name} 缺少来源 URL"
            for url in node.sources:
                assert url.startswith("https://") or url.startswith("http://"), (
                    f"{name} 来源 URL 无效: {url}"
                )


class TestGetProcessNode:
    """get_process_node 函数测试。"""

    def test_get_existing_node(self) -> None:
        """查询存在的节点应返回 ProcessNode。"""
        node = get_process_node("GF_Fotonix_45CLO")
        assert isinstance(node, ProcessNode)
        assert node.cmos_node_nm == 45

    def test_get_nonexistent_node_raises(self) -> None:
        """查询不存在的节点应抛出 KeyError。"""
        with pytest.raises(KeyError, match="不在注册表中"):
            get_process_node("Nonexistent_Node")


class TestListProcessNodes:
    """list_process_nodes 函数测试。"""

    def test_list_all(self) -> None:
        """list_process_nodes 应返回全部节点名（第89轮 13 个）。"""
        names = list_process_nodes()
        assert len(names) == 13
        assert "GF_Fotonix_45CLO" in names

    def test_list_by_cmos_node_45(self) -> None:
        """按 45nm CMOS 筛选应返回 GF Fotonix 45CLO。"""
        names = list_process_nodes_by_cmos_node(45)
        assert "GF_Fotonix_45CLO" in names

    def test_list_by_cmos_node_0(self) -> None:
        """按 0nm（纯光子）筛选应返回 6 个平台（第89轮新增 3 个）。"""
        names = list_process_nodes_by_cmos_node(0)
        assert "AIM_300mm_SOI" in names
        assert "LioniX_TriPleX" in names
        assert "HyperLight_LNOI" in names
        # 第89轮新增
        assert "LIGENTEC_AN800_SiN" in names
        assert "VTT_ThickSOI" in names
        assert "Tyndall_InP_SOI_Hybrid" in names
        assert len(names) == 6

    def test_list_by_foundry_gf(self) -> None:
        """按 GlobalFoundries 筛选应返回 2 个节点。"""
        names = list_process_nodes_by_foundry("GlobalFoundries")
        assert "GF_Fotonix_45CLO" in names
        assert "GF_Fotonix_90WG" in names
        assert len(names) == 2

    def test_list_by_material_soi(self) -> None:
        """按 SOI 筛选应返回多个节点。"""
        names = list_process_nodes_by_material("SOI")
        assert "GF_Fotonix_45CLO" in names
        assert "AIM_300mm_SOI" in names
        assert len(names) >= 6

    def test_list_by_material_sin(self) -> None:
        """按 SiN 筛选应返回 LioniX。"""
        names = list_process_nodes_by_material("SiN")
        assert "LioniX_TriPleX" in names

    def test_list_by_material_lnoi(self) -> None:
        """按 LNOI 筛选应返回 HyperLight。"""
        names = list_process_nodes_by_material("LNOI")
        assert "HyperLight_LNOI" in names


class TestParseProcessNodeString:
    """parse_process_node_string 函数测试。"""

    def test_parse_45nm_cmos(self) -> None:
        """解析 '45nm CMOS, 220nm SOI (300mm)'。"""
        result = parse_process_node_string("45nm CMOS, 220nm SOI (300mm)")
        assert result["cmos_node_nm"] == 45
        assert result["photonic_layer_nm"] == 220
        assert result["wafer_size_mm"] == 300
        assert result["has_cmos"] is True

    def test_parse_0_13um_cmos(self) -> None:
        """解析 '0.13μm CMOS, 220nm SOI (200mm)'。"""
        result = parse_process_node_string("0.13μm CMOS, 220nm SOI (200mm)")
        assert result["cmos_node_nm"] == 130
        assert result["photonic_layer_nm"] == 220
        assert result["wafer_size_mm"] == 200
        assert result["has_cmos"] is True

    def test_parse_90nm_only(self) -> None:
        """解析 '90nm, 220nm SOI (200mm)'。"""
        result = parse_process_node_string("90nm, 220nm SOI (200mm)")
        assert result["cmos_node_nm"] == 90
        assert result["has_cmos"] is True

    def test_parse_bicmos(self) -> None:
        """解析 '0.25μm BiCMOS + 220nm SOI (200mm)'。"""
        result = parse_process_node_string("0.25μm BiCMOS + 220nm SOI (200mm)")
        assert result["cmos_node_nm"] == 250
        assert result["has_cmos"] is True

    def test_parse_pure_photonic(self) -> None:
        """解析 '220nm SOI + 220nm SiN (300mm)'（无 CMOS）。"""
        result = parse_process_node_string("220nm SOI + 220nm SiN (300mm)")
        assert result["cmos_node_nm"] == 0
        assert result["has_cmos"] is False
        assert result["photonic_layer_nm"] == 220
        assert result["wafer_size_mm"] == 300

    def test_parse_sin_platform(self) -> None:
        """解析 'AN800, 800nm SiN (200mm)'。"""
        result = parse_process_node_string("AN800, 800nm SiN (200mm)")
        assert result["photonic_layer_nm"] == 800
        assert result["wafer_size_mm"] == 200

    def test_parse_lnoi_platform(self) -> None:
        """解析 '600nm LNOI X-cut (100mm)'。"""
        result = parse_process_node_string("600nm LNOI X-cut (100mm)")
        assert result["photonic_layer_nm"] == 600
        assert result["wafer_size_mm"] == 100

    def test_parse_empty_string(self) -> None:
        """空字符串应返回全 0 结果。"""
        result = parse_process_node_string("")
        assert result["cmos_node_nm"] == 0
        assert result["has_cmos"] is False

    def test_parse_foundry_platforms_strings(self) -> None:
        """应能解析 foundry_platforms.py 中所有 process_node 字符串。"""
        from polaris.pdk.foundry_platforms import FOUNDRY_PLATFORMS

        for _name, fp in FOUNDRY_PLATFORMS.items():
            result = parse_process_node_string(fp.process_node)
            # 至少应解析出晶圆直径或光子层
            assert isinstance(result, dict)
            assert "cmos_node_nm" in result


class TestSuggestProcessNode:
    """suggest_process_node_for_circuit 函数测试。"""

    def test_suggest_45nm_cmos_soi(self) -> None:
        """推荐 45nm CMOS + SOI 应返回 GF Fotonix 45CLO。"""
        name = suggest_process_node_for_circuit(cmos_node_nm=45, material="SOI")
        assert name == "GF_Fotonix_45CLO"

    def test_suggest_90nm_cmos_soi(self) -> None:
        """推荐 90nm CMOS + SOI 应返回 GF Fotonix 90WG 或 Intel。"""
        name = suggest_process_node_for_circuit(cmos_node_nm=90, material="SOI")
        assert name in ("GF_Fotonix_90WG", "Intel_300mm_CMOS_Ph")

    def test_suggest_no_cmos_soi(self) -> None:
        """无 CMOS 需求 + SOI 应返回纯光子平台。"""
        name = suggest_process_node_for_circuit(cmos_node_nm=0, material="SOI")
        assert name == "AIM_300mm_SOI"

    def test_suggest_no_cmos_sin(self) -> None:
        """无 CMOS 需求 + SiN 应返回 LioniX。"""
        name = suggest_process_node_for_circuit(cmos_node_nm=0, material="SiN")
        assert name == "LioniX_TriPleX"

    def test_suggest_no_cmos_lnoi(self) -> None:
        """无 CMOS 需求 + LNOI 应返回 HyperLight。"""
        name = suggest_process_node_for_circuit(cmos_node_nm=0, material="LNOI")
        assert name == "HyperLight_LNOI"

    def test_suggest_smaller_cmos_node(self) -> None:
        """需求 100nm CMOS 应选 ≤100nm 的最先进工艺（45nm）。"""
        name = suggest_process_node_for_circuit(cmos_node_nm=100, material="SOI")
        # 应选 45nm 或 90nm（≤100nm 中最先进的）
        node = CMOS_PROCESS_NODES[name]
        assert node.cmos_node_nm <= 100
        assert node.cmos_node_nm > 0

    def test_suggest_no_match_returns_none(self) -> None:
        """无匹配材料应返回 None。"""
        name = suggest_process_node_for_circuit(cmos_node_nm=0, material="UnknownMaterial")
        assert name is None


class TestCommercialGapReduction:
    """商业差距缩减验证（P1-3）。"""

    def test_cmos_photonics_nodes_covered(self) -> None:
        """应覆盖主流 CMOS photonics 工艺节点。"""
        # GF Fotonix 45CLO/90WG
        assert "GF_Fotonix_45CLO" in CMOS_PROCESS_NODES
        assert "GF_Fotonix_90WG" in CMOS_PROCESS_NODES
        # Tower PH18DA
        assert "Tower_PH18DA" in CMOS_PROCESS_NODES
        # IHP SG25H5
        assert "IHP_SG25H5" in CMOS_PROCESS_NODES
        # Intel
        assert "Intel_300mm_CMOS_Ph" in CMOS_PROCESS_NODES

    def test_cmos_node_range(self) -> None:
        """CMOS 节点应覆盖 45nm-250nm 范围。"""
        cmos_nodes = {
            n.cmos_node_nm for n in CMOS_PROCESS_NODES.values() if n.cmos_node_nm > 0
        }
        assert 45 in cmos_nodes
        assert 90 in cmos_nodes
        assert 130 in cmos_nodes
        assert 180 in cmos_nodes
        assert 250 in cmos_nodes

    def test_material_platforms_covered(self) -> None:
        """应覆盖 SOI/SiN/LNOI 三大材料平台。"""
        materials = {n.material_platform for n in CMOS_PROCESS_NODES.values()}
        assert "SOI" in materials
        assert "SiN" in materials
        assert "LNOI" in materials

    def test_integration_types_covered(self) -> None:
        """应覆盖 monolithic/photonic_only 集成类型。"""
        types = {n.integration_type for n in CMOS_PROCESS_NODES.values()}
        assert "monolithic" in types
        assert "photonic_only" in types

    def test_source_traceability(self) -> None:
        """所有工艺节点应有来源 URL（学术诚信）。"""
        for name, node in CMOS_PROCESS_NODES.items():
            assert len(node.sources) > 0, f"{name} 缺少来源"
            for url in node.sources:
                assert url.startswith("http"), f"{name} 来源 URL 无效"

    def test_aligned_with_innovus_icc2(self) -> None:
        """工艺节点支持应对齐 Innovus/ICC2 的工艺节点标注能力。"""
        # Innovus/ICC2 支持 3nm-250nm 全谱
        # PoLaRIS 应至少支持 45nm-250nm CMOS photonics
        cmos_nodes = {
            n.cmos_node_nm for n in CMOS_PROCESS_NODES.values() if n.cmos_node_nm > 0
        }
        assert min(cmos_nodes) <= 90  # 至少支持到 90nm
        assert max(cmos_nodes) >= 250  # 至少支持到 250nm

    def test_foundry_platforms_integration(self) -> None:
        """应能与 foundry_platforms.py 集成（process_node 字符串解析）。"""
        from polaris.pdk.foundry_platforms import FOUNDRY_PLATFORMS

        # 所有 foundry 平台的 process_node 字符串应可解析
        for name, fp in FOUNDRY_PLATFORMS.items():
            result = parse_process_node_string(fp.process_node)
            assert isinstance(result, dict)
            # 至少应解析出晶圆直径
            assert result["wafer_size_mm"] > 0, f"{name} 未解析出晶圆直径"


class TestFoundryProcessNodeAssociation:
    """Foundry 平台 → 结构化 ProcessNode 关联测试（第75轮 P1-3 深化）。"""

    def test_get_process_node_for_foundry_amf(self) -> None:
        """AMF foundry 应映射到 AMF_130nm_CMOS 结构化节点。"""
        node = get_process_node_for_foundry("AMF")
        assert node is not None
        assert node.name == "AMF_130nm_CMOS"
        assert node.cmos_node_nm == 130
        assert node.foundry == "Advanced Micro Foundry"

    def test_get_process_node_for_foundry_gf_fotonix(self) -> None:
        """GF_Fotonix foundry 应映射到 GF_Fotonix_45CLO 结构化节点。"""
        node = get_process_node_for_foundry("GF_Fotonix")
        assert node is not None
        assert node.name == "GF_Fotonix_45CLO"
        assert node.cmos_node_nm == 45
        assert node.foundry == "GlobalFoundries"

    def test_get_process_node_for_foundry_ihp(self) -> None:
        """IHP foundry 应映射到 IHP_SG25H5 结构化节点。"""
        node = get_process_node_for_foundry("IHP")
        assert node is not None
        assert node.name == "IHP_SG25H5"
        assert node.cmos_node_nm == 250
        assert node.foundry == "IHP Microelectronics"

    def test_get_process_node_for_foundry_tower(self) -> None:
        """Tower_OpenLight foundry 应映射到 Tower_PH18DA 结构化节点。"""
        node = get_process_node_for_foundry("Tower_OpenLight")
        assert node is not None
        assert node.name == "Tower_PH18DA"
        assert node.cmos_node_nm == 180

    def test_get_process_node_for_foundry_photonic_only(self) -> None:
        """纯光子平台（AIM/LioniX/HyperLight）应映射到 cmos_node_nm=0 的节点。"""
        for foundry_name, expected_name in [
            ("AIM", "AIM_300mm_SOI"),
            ("LioniX", "LioniX_TriPleX"),
            ("HyperLight", "HyperLight_LNOI"),
        ]:
            node = get_process_node_for_foundry(foundry_name)
            assert node is not None, f"{foundry_name} 无映射"
            assert node.name == expected_name
            assert node.cmos_node_nm == 0  # 纯光子平台

    def test_get_process_node_for_unknown_foundry_returns_none(self) -> None:
        """未映射的 foundry 应返回 None（第89轮全量映射后仅 UnknownFoundry 返回 None）。"""
        # 第89轮已全量映射 11/11 foundry，仅未知 foundry 返回 None
        assert get_process_node_for_foundry("UnknownFoundry") is None

    def test_get_process_node_for_foundry_compoundtek(self) -> None:
        """CompoundTek foundry 应映射到 CompoundTek_90nm_SOI 结构化节点（第89轮新增）。"""
        node = get_process_node_for_foundry("CompoundTek")
        assert node is not None
        assert node.name == "CompoundTek_90nm_SOI"
        assert node.cmos_node_nm == 90
        assert node.foundry == "CompoundTek"
        assert node.material_platform == "SOI"

    def test_get_process_node_for_foundry_ligentec(self) -> None:
        """LIGENTEC foundry 应映射到 LIGENTEC_AN800_SiN 结构化节点（第89轮新增）。"""
        node = get_process_node_for_foundry("LIGENTEC")
        assert node is not None
        assert node.name == "LIGENTEC_AN800_SiN"
        assert node.cmos_node_nm == 0  # 纯光子平台
        assert node.material_platform == "SiN"
        assert node.photonic_layer_nm == 800

    def test_get_process_node_for_foundry_vtt(self) -> None:
        """VTT foundry 应映射到 VTT_ThickSOI 结构化节点（第89轮新增）。"""
        node = get_process_node_for_foundry("VTT")
        assert node is not None
        assert node.name == "VTT_ThickSOI"
        assert node.cmos_node_nm == 0  # 纯光子平台
        assert node.material_platform == "ThickSOI"
        assert node.photonic_layer_nm == 3000  # 3μm

    def test_get_process_node_for_foundry_tyndall(self) -> None:
        """Tyndall foundry 应映射到 Tyndall_InP_SOI_Hybrid 结构化节点（第89轮新增）。"""
        node = get_process_node_for_foundry("Tyndall")
        assert node is not None
        assert node.name == "Tyndall_InP_SOI_Hybrid"
        assert node.cmos_node_nm == 0  # 纯光子平台
        assert node.material_platform == "Hybrid"
        assert node.integration_type == "heterogeneous"

    def test_list_foundries_with_process_node(self) -> None:
        """应列出 11 个有结构化映射的 foundry 平台（第89轮全量映射）。"""
        foundries = list_foundries_with_process_node()
        assert len(foundries) == 11
        # 应包含主要 CMOS photonics foundry
        assert "AMF" in foundries
        assert "GF_Fotonix" in foundries
        assert "IHP" in foundries
        assert "Tower_OpenLight" in foundries
        # 第89轮新增的 4 个 foundry
        assert "CompoundTek" in foundries
        assert "LIGENTEC" in foundries
        assert "VTT" in foundries
        assert "Tyndall" in foundries

    def test_foundry_to_process_node_consistency(self) -> None:
        """所有 foundry 映射的 ProcessNode 应存在于 CMOS_PROCESS_NODES 注册表。"""
        foundries = list_foundries_with_process_node()
        for fname in foundries:
            node = get_process_node_for_foundry(fname)
            assert node is not None
            assert node.name in CMOS_PROCESS_NODES


class TestDeviceCatalogProcessNode:
    """DeviceCatalog.list_by_process_node 检索 API 测试（第75轮 P1-3 深化）。"""

    def test_list_by_process_node_returns_matching_devices(self) -> None:
        """list_by_process_node 应返回匹配工艺节点的器件列表。"""
        from polaris.pdk.catalog import default_catalog

        catalog = default_catalog()
        # 默认目录的 SOI 平台器件应有 process_node="220nm SOI"
        soi_devices = catalog.list_by_process_node("220nm SOI")
        assert len(soi_devices) > 0
        for dev in soi_devices:
            assert dev.process_node == "220nm SOI"

    def test_list_by_process_node_no_match_returns_empty(self) -> None:
        """不匹配的工艺节点应返回空列表。"""
        from polaris.pdk.catalog import default_catalog

        catalog = default_catalog()
        result = catalog.list_by_process_node("999nm UnknownMaterial")
        assert result == []

    def test_list_by_process_node_none_excluded(self) -> None:
        """process_node 为 None 的器件不应被匹配。"""
        from polaris.pdk.catalog import DeviceCatalog
        from polaris.pdk.device import BoundingBox, Device
        from polaris.pdk.port import Direction, Port

        catalog = DeviceCatalog()
        dev_no_pn = Device(
            device_id="test_no_pn",
            platform="SOI",
            category="passive",
            name="test",
            ports=[Port("in", 0.0, 0.0, Direction.WEST, "strip", 0.5)],
            bbox=BoundingBox(0.0, 0.0, 1.0, 0.5),
            process_node=None,
        )
        catalog.register(dev_no_pn)
        assert catalog.list_by_process_node("220nm SOI") == []
