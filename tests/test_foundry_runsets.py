"""多 foundry DRC runset 测试（第15轮 P0-1 扩展）。

测试覆盖:
- FoundryRunset dataclass
- 6 个 foundry runset 完整性（SiEPIC/AMF/IHP/GF_Fotonix/CompoundTek/LIGENTEC）
- foundry 注册表查询函数
- 材料平台筛选
- DRC 规则总数统计
- runset 对 GDS 文件的实际运行

来源:
- SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- Luceda IPKISS PDK: https://www.lucedaphotonics.com/zh_CN/luceda-design-kits
- IHP Open PDK: https://github.com/IHP-GmbH/IHP-Open-PDK
- GF Fotonix: https://www.globalfoundries.com/en/press-release/globalfoundries-introduces-monolithic-photonics-platform
"""

from __future__ import annotations

from pathlib import Path

import klayout.db as db
import pytest

from polaris.sim.constraint_checker import ViolationType
from polaris.sim.foundry_runsets import (
    AMF_DRC_RUNSET,
    COMPOUNDTEK_DRC_RUNSET,
    FOUNDRY_RUNSETS,
    GF_FOTONIX_DRC_RUNSET,
    IHP_DRC_RUNSET,
    LIGENTEC_DRC_RUNSET,
    FoundryRunset,
    foundry_runset_count,
    get_foundry_runset,
    list_foundry_runsets,
    list_foundry_runsets_by_material,
    total_drc_rules_count,
)
from polaris.sim.klayout_drc import DRCCheckType, DRCRule, KLayoutDRCRunner

# -- FoundryRunset dataclass 测试 --


def test_foundry_runset_dataclass():
    """测试 FoundryRunset dataclass。"""
    rule = DRCRule(
        name="TEST",
        layer_name="WG",
        check_type=DRCCheckType.WIDTH,
        threshold_um=0.5,
        vtype=ViolationType.MIN_WIDTH,
        description="测试",
    )
    runset = FoundryRunset(
        foundry_name="TEST",
        process_node="100nm SOI",
        material_platform="SOI",
        rules=[rule],
        source_url="https://example.com",
        notes="测试 runset",
    )
    assert runset.foundry_name == "TEST"
    assert runset.process_node == "100nm SOI"
    assert runset.material_platform == "SOI"
    assert len(runset.rules) == 1
    assert runset.source_url == "https://example.com"
    assert runset.notes == "测试 runset"


def test_foundry_runset_frozen():
    """测试 FoundryRunset 是 frozen dataclass。"""
    runset = FOUNDRY_RUNSETS["AMF"]
    with pytest.raises((AttributeError, Exception)):
        runset.foundry_name = "MODIFIED"  # type: ignore[misc]


# -- 注册表完整性测试 --


def test_foundry_runset_count():
    """测试 foundry runset 总数 >= 6。"""
    assert foundry_runset_count() >= 6


def test_list_foundry_runsets_sorted():
    """测试 list_foundry_runsets 返回排序后的列表。"""
    names = list_foundry_runsets()
    assert names == sorted(names)
    assert "SiEPIC_EBeam" in names
    assert "AMF" in names
    assert "IHP" in names
    assert "GF_Fotonix" in names
    assert "CompoundTek" in names
    assert "LIGENTEC" in names


def test_get_foundry_runset_valid():
    """测试 get_foundry_runset 返回有效 runset。"""
    runset = get_foundry_runset("AMF")
    assert runset.foundry_name == "AMF"
    assert runset.process_node == "180nm SOI"
    assert runset.material_platform == "SOI"
    assert len(runset.rules) > 0


def test_get_foundry_runset_invalid():
    """测试 get_foundry_runset 对未知 foundry 抛 KeyError。"""
    with pytest.raises(KeyError, match="未知 foundry"):
        get_foundry_runset("UNKNOWN_FOUNDRY")


def test_total_drc_rules_count():
    """测试 DRC 规则总数 >= 40（6 foundry × 平均 7 条）。"""
    total = total_drc_rules_count()
    assert total >= 40, f"DRC 规则总数 {total} 应 >= 40"


# -- 材料平台筛选测试 --


def test_list_foundry_runsets_by_material_soi():
    """测试 SOI 平台 foundry 数 >= 5。"""
    soi = list_foundry_runsets_by_material("SOI")
    assert len(soi) >= 5
    assert "SiEPIC_EBeam" in soi
    assert "AMF" in soi
    assert "IHP" in soi
    assert "GF_Fotonix" in soi
    assert "CompoundTek" in soi


def test_list_foundry_runsets_by_material_sin():
    """测试 SiN 平台 foundry 数 >= 1。"""
    sin = list_foundry_runsets_by_material("SiN")
    assert len(sin) >= 1
    assert "LIGENTEC" in sin


def test_list_foundry_runsets_by_material_inp():
    """测试 InP 平台 foundry 数 >= 2。"""
    inp = list_foundry_runsets_by_material("InP")
    assert len(inp) >= 2
    assert "HHI_InP" in inp
    assert "LioniX_InP" in inp


def test_list_foundry_runsets_by_material_lnoi():
    """测试 LNOI 平台 foundry 数 >= 1。"""
    lnoi = list_foundry_runsets_by_material("LNOI")
    assert len(lnoi) >= 1
    assert "LNOI" in lnoi


def test_list_foundry_runsets_by_material_empty():
    """测试未知材料返回空列表。"""
    unknown = list_foundry_runsets_by_material("Unknown")
    assert unknown == []


# -- 单 foundry runset 数据完整性测试 --


def test_siepic_ebeam_runset_unchanged():
    """测试 SiEPIC EBeam runset 规则数（第85轮新增 WG_DENSITY）。"""
    from polaris.sim.klayout_drc import SIEPIC_EBEAM_DRC_RUNSET

    assert len(SIEPIC_EBEAM_DRC_RUNSET) == 9
    runset = FOUNDRY_RUNSETS["SiEPIC_EBeam"]
    assert runset.rules is SIEPIC_EBEAM_DRC_RUNSET


def test_amf_runset_rules():
    """测试 AMF runset 规则数和阈值（第86轮新增 WG_DENSITY）。"""
    assert len(AMF_DRC_RUNSET) == 11
    # WG 最小宽度 0.4μm
    wg_width = next(r for r in AMF_DRC_RUNSET if r.name == "AMF_WG_MIN_WIDTH")
    assert wg_width.threshold_um == 0.4
    # WG 最小间距 1.5μm（AMF 比 SiEPIC 1.0 更严格）
    wg_space = next(r for r in AMF_DRC_RUNSET if r.name == "AMF_WG_MIN_SPACE")
    assert wg_space.threshold_um == 1.5
    # DEEPTRENCH 最小宽度 3.0μm
    dt = next(r for r in AMF_DRC_RUNSET if r.name == "AMF_DEEPTRENCH_MIN_WIDTH")
    assert dt.threshold_um == 3.0


def test_ihp_runset_rules():
    """测试 IHP runset 规则数和阈值（第86轮新增 WG_DENSITY）。"""
    assert len(IHP_DRC_RUNSET) == 12
    # IHP 包含 N/P 掺杂规则
    n_width = next(r for r in IHP_DRC_RUNSET if r.name == "IHP_N_MIN_WIDTH")
    assert n_width.threshold_um == 0.5
    p_width = next(r for r in IHP_DRC_RUNSET if r.name == "IHP_P_MIN_WIDTH")
    assert p_width.threshold_um == 0.5
    # VIAC 接触孔 0.8μm
    viac = next(r for r in IHP_DRC_RUNSET if r.name == "IHP_VIAC_MIN_WIDTH")
    assert viac.threshold_um == 0.8


def test_gf_fotonix_runset_rules():
    """测试 GF Fotonix 45nm 工艺规则（更紧凑的阈值，第86轮新增 WG_DENSITY）。"""
    assert len(GF_FOTONIX_DRC_RUNSET) == 10
    # 45nm 工艺 WG 最小宽度 0.3μm（比 180nm 工艺更小）
    wg_width = next(r for r in GF_FOTONIX_DRC_RUNSET if r.name == "GF_WG_MIN_WIDTH")
    assert wg_width.threshold_um == 0.3
    # 45nm 工艺 WG 最小间距 0.8μm
    wg_space = next(r for r in GF_FOTONIX_DRC_RUNSET if r.name == "GF_WG_MIN_SPACE")
    assert wg_space.threshold_um == 0.8
    # VIAC 0.5μm（45nm 工艺更小）
    viac = next(r for r in GF_FOTONIX_DRC_RUNSET if r.name == "GF_VIAC_MIN_WIDTH")
    assert viac.threshold_um == 0.5


def test_compoundtek_runset_rules():
    """测试 CompoundTek 130nm SOI runset（第86轮新增 WG_DENSITY）。"""
    assert len(COMPOUNDTEK_DRC_RUNSET) == 7
    wg_width = next(r for r in COMPOUNDTEK_DRC_RUNSET if r.name == "CT_WG_MIN_WIDTH")
    assert wg_width.threshold_um == 0.4
    wg_space = next(r for r in COMPOUNDTEK_DRC_RUNSET if r.name == "CT_WG_MIN_SPACE")
    assert wg_space.threshold_um == 1.2


def test_ligentec_runset_rules():
    """测试 LIGENTEC SiN 平台 runset（第86轮新增 WGN_DENSITY）。"""
    assert len(LIGENTEC_DRC_RUNSET) == 6
    # SiN 波导最小宽度 0.8μm（比 SOI 0.4μm 更大）
    wgn_width = next(r for r in LIGENTEC_DRC_RUNSET if r.name == "LIG_WGN_MIN_WIDTH")
    assert wgn_width.threshold_um == 0.8
    assert wgn_width.layer_name == "WGN"
    # WGN_CLAD 层
    clad = next(r for r in LIGENTEC_DRC_RUNSET if r.name == "LIG_WGN_CLAD_MIN_WIDTH")
    assert clad.layer_name == "WGN_CLAD"


# -- 工艺节点差异化测试 --


def test_process_node_diversity():
    """测试 foundry runset 覆盖多个工艺节点。"""
    nodes = {r.process_node for r in FOUNDRY_RUNSETS.values()}
    # 至少覆盖 4 个不同工艺节点
    assert len(nodes) >= 4
    # 包含 45nm/130nm/180nm/220nm/250nm 中的多个
    node_str = " ".join(nodes)
    assert "nm" in node_str


def test_material_platform_diversity():
    """测试 foundry runset 覆盖多个材料平台。"""
    materials = {r.material_platform for r in FOUNDRY_RUNSETS.values()}
    assert "SOI" in materials
    assert "SiN" in materials
    assert "InP" in materials
    assert "LNOI" in materials


def test_rule_name_prefix_consistency():
    """测试每个 foundry 的规则名前缀一致。"""
    prefixes = {
        "SiEPIC_EBeam": "WG_",
        "AMF": "AMF_",
        "IHP": "IHP_",
        "GF_Fotonix": "GF_",
        "CompoundTek": "CT_",
        "LIGENTEC": "LIG_",
        "HHI_InP": "HHI_INP_",
        "LioniX_InP": "LIONIX_INP_",
        "LNOI": "LNOI_",
    }
    for foundry_name, prefix in prefixes.items():
        runset = FOUNDRY_RUNSETS[foundry_name]
        for rule in runset.rules:
            if foundry_name == "SiEPIC_EBeam":
                # SiEPIC 沿用旧命名（无前缀），跳过
                continue
            assert rule.name.startswith(prefix), (
                f"{foundry_name} 规则 {rule.name} 应以前缀 {prefix} 开头"
            )


# -- GDS 实际运行测试 --


def _create_test_gds_with_violation(
    tmp_path: Path, layer_name: str, width_um: float
) -> Path:
    """创建测试 GDS 文件（指定宽度的矩形，可能违反 DRC）。

    Args:
        tmp_path: 临时目录。
        layer_name: 层名（如 ``"WG"``）。
        width_um: 矩形宽度（μm）。

    Returns:
        GDS 文件路径。
    """
    from polaris.pdk.layer_map import get_layer_tuple

    layer_num, datatype = get_layer_tuple(layer_name)
    layout = db.Layout()
    layout.dbu = 0.001  # 1nm
    cell = layout.create_cell("TOP")
    layer = layout.layer(layer_num, datatype)
    # 创建 width_um × 10μm 的矩形
    w_dbu = int(width_um / layout.dbu)
    h_dbu = int(10.0 / layout.dbu)
    cell.shapes(layer).insert(db.Box(0, 0, w_dbu, h_dbu))
    gds_path = tmp_path / f"test_{layer_name}_{width_um}.gds"
    layout.write(str(gds_path))
    return gds_path


def test_amf_runset_detects_violation(tmp_path):
    """测试 AMF runset 能检测 WG 宽度违规。"""
    # 创建 0.3μm 宽的 WG（AMF 要求 0.4μm）
    gds = _create_test_gds_with_violation(tmp_path, "WG", 0.3)
    runner = KLayoutDRCRunner()
    result = runner.run_gds(gds, AMF_DRC_RUNSET)
    # 应该检测到 AMF_WG_MIN_WIDTH 违规
    width_violations = [
        v for v in result.violations if "AMF_WG_MIN_WIDTH" in v.message
    ]
    assert len(width_violations) > 0


def test_amf_runset_clean_layout(tmp_path):
    """测试 AMF runset 对合规版图无违规。"""
    # 创建 1.0μm 宽的 WG（远大于 0.4μm 要求）
    gds = _create_test_gds_with_violation(tmp_path, "WG", 1.0)
    runner = KLayoutDRCRunner()
    result = runner.run_gds(gds, AMF_DRC_RUNSET)
    # WG 宽度 1.0μm > 0.4μm，不应有 WIDTH 违规
    width_violations = [
        v for v in result.violations if "MIN_WIDTH" in v.message and "WG" in v.message
    ]
    assert len(width_violations) == 0


def test_gf_fotonix_runset_stricter_than_amf():
    """测试 GF Fotonix 45nm 工艺比 AMF 180nm 工艺更紧凑。"""
    gf_wg_width = next(
        r for r in GF_FOTONIX_DRC_RUNSET if r.name == "GF_WG_MIN_WIDTH"
    )
    amf_wg_width = next(
        r for r in AMF_DRC_RUNSET if r.name == "AMF_WG_MIN_WIDTH"
    )
    # 45nm 工艺 WG 宽度 0.3μm < 180nm 工艺 0.4μm
    assert gf_wg_width.threshold_um < amf_wg_width.threshold_um

    gf_wg_space = next(
        r for r in GF_FOTONIX_DRC_RUNSET if r.name == "GF_WG_MIN_SPACE"
    )
    amf_wg_space = next(
        r for r in AMF_DRC_RUNSET if r.name == "AMF_WG_MIN_SPACE"
    )
    # 45nm 工艺 WG 间距 0.8μm < 180nm 工艺 1.5μm
    assert gf_wg_space.threshold_um < amf_wg_space.threshold_um


def test_runset_source_url_valid():
    """测试所有 foundry runset 都有有效 source_url。"""
    for name, runset in FOUNDRY_RUNSETS.items():
        assert runset.source_url.startswith("https://"), (
            f"{name} source_url 应为 https URL"
        )
        assert len(runset.source_url) > 20


def test_runset_notes_nonempty():
    """测试所有 foundry runset 都有非空 notes。"""
    for name, runset in FOUNDRY_RUNSETS.items():
        assert len(runset.notes) > 0, f"{name} notes 不应为空"
