"""InP/LNOI 平台 foundry DRC runset 测试（第18轮 P0-1 深化）。

测试覆盖:
- 3 个 InP/LNOI runset 完整性（HHI_InP/LioniX_InP/LNOI）
- runset 注册表查询函数
- 材料平台筛选（InP/LNOI）
- DRC 规则总数统计
- runset 对 GDS 文件的实际运行
- InP vs LNOI 工艺差异化

来源:
- JePPIX InP: https://www.jeppix.eu/
- LioniX InP: https://www.lionix-international.com/photonics/
- LNOI: https://www.nanochemistrygroup.com/lnoi
"""

from __future__ import annotations

from pathlib import Path

import klayout.db as db
import pytest

from polaris.pdk.layer_map import get_layer_tuple
from polaris.sim.foundry_runsets_inplnoi import (
    HHI_INP_DRC_RUNSET,
    INP_LNOI_RUNSETS,
    LIONIX_INP_DRC_RUNSET,
    LNOI_DRC_RUNSET,
    get_inplnoi_runset,
    inplnoi_runset_count,
    inplnoi_total_drc_rules_count,
    list_inplnoi_runsets,
    list_inplnoi_runsets_by_material,
)
from polaris.sim.klayout_drc import KLayoutDRCRunner

# -- 注册表完整性测试 --


def test_inplnoi_runset_count():
    """测试 InP/LNOI runset 总数 >= 3。"""
    assert inplnoi_runset_count() >= 3


def test_list_inplnoi_runsets_sorted():
    """测试 list_inplnoi_runsets 返回排序后的列表。"""
    names = list_inplnoi_runsets()
    assert names == sorted(names)
    assert "HHI_InP" in names
    assert "LioniX_InP" in names
    assert "LNOI" in names


def test_get_inplnoi_runset_valid():
    """测试 get_inplnoi_runset 返回有效 runset。"""
    runset = get_inplnoi_runset("HHI_InP")
    assert runset["foundry_name"] == "HHI"
    assert runset["process_node"] == "InP generic"
    assert runset["material_platform"] == "InP"
    assert len(runset["rules"]) > 0


def test_get_inplnoi_runset_invalid():
    """测试 get_inplnoi_runset 对未知 foundry 抛 KeyError。"""
    with pytest.raises(KeyError, match="未知 InP/LNOI foundry"):
        get_inplnoi_runset("UNKNOWN_FOUNDRY")


def test_inplnoi_total_drc_rules_count():
    """测试 InP/LNOI DRC 规则总数 >= 18（3 foundry × 平均 6 条）。"""
    total = inplnoi_total_drc_rules_count()
    assert total >= 18, f"InP/LNOI DRC 规则总数 {total} 应 >= 18"


# -- 材料平台筛选测试 --


def test_list_inplnoi_runsets_by_material_inp():
    """测试 InP 平台 foundry 数 >= 2。"""
    inp = list_inplnoi_runsets_by_material("InP")
    assert len(inp) >= 2
    assert "HHI_InP" in inp
    assert "LioniX_InP" in inp


def test_list_inplnoi_runsets_by_material_lnoi():
    """测试 LNOI 平台 foundry 数 >= 1。"""
    lnoi = list_inplnoi_runsets_by_material("LNOI")
    assert len(lnoi) >= 1
    assert "LNOI" in lnoi


def test_list_inplnoi_runsets_by_material_empty():
    """测试未知材料返回空列表。"""
    soi = list_inplnoi_runsets_by_material("SOI")
    assert soi == []


# -- 单 foundry runset 数据完整性测试 --


def test_hhi_inp_runset_rules():
<<<<<<< HEAD
    """测试 HHI InP runset 规则数和阈值（第88轮新增 VIAC WIDTH + VIA ENCLOSURE）。"""
    assert len(HHI_INP_DRC_RUNSET) == 10
=======
    """测试 HHI InP runset 规则数和阈值。"""
    assert len(HHI_INP_DRC_RUNSET) == 7
>>>>>>> trae/solo-agent-pkVjID
    # InP WG 最小宽度 1.0μm（比 SOI 0.4μm 更大）
    wg_width = next(r for r in HHI_INP_DRC_RUNSET if r.name == "HHI_INP_WG_MIN_WIDTH")
    assert wg_width.threshold_um == 1.0
    # InP WG 最小间距 2.0μm（比 SOI 1.0μm 更大）
    wg_space = next(r for r in HHI_INP_DRC_RUNSET if r.name == "HHI_INP_WG_MIN_SPACE")
    assert wg_space.threshold_um == 2.0
    # DEEPTRENCH 5.0μm（InP 深刻蚀工艺）
    dt = next(r for r in HHI_INP_DRC_RUNSET if r.name == "HHI_INP_DEEPTRENCH_MIN_WIDTH")
    assert dt.threshold_um == 5.0


def test_lionix_inp_runset_rules():
<<<<<<< HEAD
    """测试 LioniX InP runset 规则数和阈值（第88轮新增 VIAC WIDTH + VIA ENCLOSURE）。"""
    assert len(LIONIX_INP_DRC_RUNSET) == 8
=======
    """测试 LioniX InP runset 规则数和阈值。"""
    assert len(LIONIX_INP_DRC_RUNSET) == 5
>>>>>>> trae/solo-agent-pkVjID
    # LioniX InP WG 最小宽度 1.5μm（TriPleX 工艺）
    wg_width = next(r for r in LIONIX_INP_DRC_RUNSET if r.name == "LIONIX_INP_WG_MIN_WIDTH")
    assert wg_width.threshold_um == 1.5
    # LioniX InP WG 最小间距 2.5μm
    wg_space = next(r for r in LIONIX_INP_DRC_RUNSET if r.name == "LIONIX_INP_WG_MIN_SPACE")
    assert wg_space.threshold_um == 2.5


def test_lnoi_runset_rules():
<<<<<<< HEAD
    """测试 LNOI runset 规则数和阈值（第86轮 WG_DENSITY，第87轮 VIAC_M1_ENCLOSURE）。"""
    assert len(LNOI_DRC_RUNSET) == 10
=======
    """测试 LNOI runset 规则数和阈值。"""
    assert len(LNOI_DRC_RUNSET) == 8
>>>>>>> trae/solo-agent-pkVjID
    # LNOI WG 最小宽度 0.8μm（薄膜铌酸锂干法刻蚀极限）
    wg_width = next(r for r in LNOI_DRC_RUNSET if r.name == "LNOI_WG_MIN_WIDTH")
    assert wg_width.threshold_um == 0.8
    # LNOI WG 最小间距 1.5μm
    wg_space = next(r for r in LNOI_DRC_RUNSET if r.name == "LNOI_WG_MIN_SPACE")
    assert wg_space.threshold_um == 1.5
    # LNOI VIAC 接触孔 1.0μm
    viac = next(r for r in LNOI_DRC_RUNSET if r.name == "LNOI_VIAC_MIN_WIDTH")
    assert viac.threshold_um == 1.0


# -- 工艺节点差异化测试 --


def test_inp_vs_soi_wg_width():
    """测试 InP 平台 WG 宽度 > SOI 平台（InP 工艺波导较粗）。"""
    from polaris.sim.foundry_runsets import AMF_DRC_RUNSET

    hhi_wg = next(r for r in HHI_INP_DRC_RUNSET if r.name == "HHI_INP_WG_MIN_WIDTH")
    amf_wg = next(r for r in AMF_DRC_RUNSET if r.name == "AMF_WG_MIN_WIDTH")
    # InP WG 1.0μm > SOI WG 0.4μm
    assert hhi_wg.threshold_um > amf_wg.threshold_um


def test_lnoi_vs_soi_wg_width():
    """测试 LNOI 平台 WG 宽度 > SOI 平台（LNOI 干法刻蚀极限）。"""
    from polaris.sim.foundry_runsets import AMF_DRC_RUNSET

    lnoi_wg = next(r for r in LNOI_DRC_RUNSET if r.name == "LNOI_WG_MIN_WIDTH")
    amf_wg = next(r for r in AMF_DRC_RUNSET if r.name == "AMF_WG_MIN_WIDTH")
    # LNOI WG 0.8μm > SOI WG 0.4μm
    assert lnoi_wg.threshold_um > amf_wg.threshold_um


def test_inp_vs_lnoi_wg_width():
    """测试 InP 平台 WG 宽度 > LNOI 平台（InP 工艺对准精度限制）。"""
    hhi_wg = next(r for r in HHI_INP_DRC_RUNSET if r.name == "HHI_INP_WG_MIN_WIDTH")
    lnoi_wg = next(r for r in LNOI_DRC_RUNSET if r.name == "LNOI_WG_MIN_WIDTH")
    # InP WG 1.0μm > LNOI WG 0.8μm
    assert hhi_wg.threshold_um > lnoi_wg.threshold_um


def test_material_platform_diversity():
    """测试 InP/LNOI runset 覆盖 InP 和 LNOI 两个材料平台。"""
    materials = {r["material_platform"] for r in INP_LNOI_RUNSETS.values()}
    assert "InP" in materials
    assert "LNOI" in materials


def test_rule_name_prefix_consistency():
    """测试每个 foundry 的规则名前缀一致。"""
    prefixes = {
        "HHI_InP": "HHI_INP_",
        "LioniX_InP": "LIONIX_INP_",
        "LNOI": "LNOI_",
    }
    for foundry_name, prefix in prefixes.items():
        runset = INP_LNOI_RUNSETS[foundry_name]
        for rule in runset["rules"]:
            assert rule.name.startswith(prefix), (
                f"{foundry_name} 规则 {rule.name} 应以前缀 {prefix} 开头"
            )


# -- GDS 实际运行测试 --


def _create_test_gds_with_violation(
    tmp_path: Path, layer_name: str, width_um: float
) -> Path:
    """创建测试 GDS 文件（指定宽度的矩形，可能违反 DRC）。"""
    layer_num, datatype = get_layer_tuple(layer_name)
    layout = db.Layout()
    layout.dbu = 0.001
    cell = layout.create_cell("TOP")
    layer = layout.layer(layer_num, datatype)
    w_dbu = int(width_um / layout.dbu)
    h_dbu = int(10.0 / layout.dbu)
    cell.shapes(layer).insert(db.Box(0, 0, w_dbu, h_dbu))
    gds_path = tmp_path / f"test_{layer_name}_{width_um}.gds"
    layout.write(str(gds_path))
    return gds_path


def test_hhi_inp_runset_detects_violation(tmp_path):
    """测试 HHI InP runset 能检测 WG 宽度违规。"""
    # 创建 0.5μm 宽的 WG（HHI InP 要求 1.0μm）
    gds = _create_test_gds_with_violation(tmp_path, "WG", 0.5)
    runner = KLayoutDRCRunner()
    result = runner.run_gds(gds, HHI_INP_DRC_RUNSET)
    width_violations = [
        v for v in result.violations if "HHI_INP_WG_MIN_WIDTH" in v.message
    ]
    assert len(width_violations) > 0


def test_lnoi_runset_detects_violation(tmp_path):
    """测试 LNOI runset 能检测 WG 宽度违规。"""
    # 创建 0.5μm 宽的 WG（LNOI 要求 0.8μm）
    gds = _create_test_gds_with_violation(tmp_path, "WG", 0.5)
    runner = KLayoutDRCRunner()
    result = runner.run_gds(gds, LNOI_DRC_RUNSET)
    width_violations = [
        v for v in result.violations if "LNOI_WG_MIN_WIDTH" in v.message
    ]
    assert len(width_violations) > 0


def test_hhi_inp_runset_clean_layout(tmp_path):
    """测试 HHI InP runset 对合规版图无违规。"""
    # 创建 2.0μm 宽的 WG（远大于 1.0μm 要求）
    gds = _create_test_gds_with_violation(tmp_path, "WG", 2.0)
    runner = KLayoutDRCRunner()
    result = runner.run_gds(gds, HHI_INP_DRC_RUNSET)
    width_violations = [
        v for v in result.violations if "MIN_WIDTH" in v.message and "WG" in v.message
    ]
    assert len(width_violations) == 0


def test_runset_source_url_valid():
    """测试所有 InP/LNOI runset 都有有效 source_url。"""
    for name, runset in INP_LNOI_RUNSETS.items():
        assert runset["source_url"].startswith("https://"), (
            f"{name} source_url 应为 https URL"
        )


def test_runset_notes_nonempty():
    """测试所有 InP/LNOI runset 都有非空 notes。"""
    for name, runset in INP_LNOI_RUNSETS.items():
        assert len(runset["notes"]) > 0, f"{name} notes 不应为空"
