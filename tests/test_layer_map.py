"""GDS Layer Map 单元测试（止血7）。

验证 ``polaris.pdk.layer_map`` 模块的真实 foundry layer 编号与开源 PDK
（SiEPIC EBeam PDK / ubcpdk / gdsfactory generic_pdk）一致。

来源（均 MIT 许可证）：
- SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- ubcpdk: https://github.com/gdsfactory/ubc/blob/main/ubcpdk/tech.py
- gdsfactory generic_pdk:
  https://github.com/gdsfactory/gdsfactory/blob/main/gdsfactory/gpdk/layer_map.py
- SiEPIC OpenEBL: https://github.com/SiEPIC/openEBL-2024-10
"""

from __future__ import annotations

import pytest

from polaris.pdk.layer_map import (
    POLARIS_CATEGORY_LAYER_MAP,
    POLARIS_GDS_LAYER_MAP,
    get_category_layer_tuple,
    get_layer_tuple,
)


class TestLayerMapConstants:
    """验证 layer_map 中的真实 foundry layer 编号（止血7）。"""

    def test_wg_layer_is_soi_220nm_standard(self) -> None:
        """WG 层应为 (1,0) —— SiEPIC/gdsfactory 220nm SOI 标准核心层。"""
        wg = POLARIS_GDS_LAYER_MAP["WG"]
        assert wg.layer == 1
        assert wg.datatype == 0
        assert wg.fabricated is True

    def test_port_layer_is_pinrec_standard(self) -> None:
        """PORT 层应为 (1,10) —— SiEPIC PinRec 光学端口标准。"""
        port = POLARIS_GDS_LAYER_MAP["PORT"]
        assert port.layer == 1
        assert port.datatype == 10
        assert port.fabricated is False  # virtual 层

    def test_devrec_layer_is_siepic_standard(self) -> None:
        """DEVREC 层应为 (68,0) —— SiEPIC 器件识别层标准。"""
        devrec = POLARIS_GDS_LAYER_MAP["DEVREC"]
        assert devrec.layer == 68
        assert devrec.datatype == 0
        assert devrec.fabricated is False  # virtual 层

    def test_text_layer_is_siepic_standard(self) -> None:
        """TEXT 层应为 (10,0) —— SiEPIC 文本标注标准（非 gdsfactory 的 66）。"""
        text = POLARIS_GDS_LAYER_MAP["TEXT"]
        assert text.layer == 10
        assert text.datatype == 0

    def test_floorplan_layer_is_siepic_standard(self) -> None:
        """FLOORPLAN 层应为 (99,0) —— SiEPIC 版图设计区域标准。"""
        fp = POLARIS_GDS_LAYER_MAP["FLOORPLAN"]
        assert fp.layer == 99
        assert fp.datatype == 0

    def test_ge_layer_for_detector(self) -> None:
        """GE 层应为 (5,0) —— 锗探测器层。"""
        ge = POLARIS_GDS_LAYER_MAP["GE"]
        assert ge.layer == 5
        assert ge.datatype == 0

    def test_sin_layer_for_sin_platform(self) -> None:
        """WGN 层应为 (34,0) —— SiN 波导层（gdsfactory 标准）。"""
        wgn = POLARIS_GDS_LAYER_MAP["WGN"]
        assert wgn.layer == 34
        assert wgn.datatype == 0

    def test_source_layer(self) -> None:
        """SOURCE 层应为 (110,0) —— 光源标记层。"""
        src = POLARIS_GDS_LAYER_MAP["SOURCE"]
        assert src.layer == 110
        assert src.datatype == 0


class TestCategoryLayerMap:
    """验证 PoLaRIS 器件类别到 GDS layer 的映射。"""

    def test_passive_maps_to_wg(self) -> None:
        """passive 类别应映射到 WG (1,0)。"""
        assert get_category_layer_tuple("passive") == (1, 0)

    def test_active_maps_to_wg(self) -> None:
        """active 类别应映射到 WG (1,0)（与 passive 同层，掺杂另画）。"""
        assert get_category_layer_tuple("active") == (1, 0)

    def test_source_maps_to_source_layer(self) -> None:
        """source 类别应映射到 SOURCE (110,0)。"""
        assert get_category_layer_tuple("source") == (110, 0)

    def test_detector_maps_to_ge(self) -> None:
        """detector 类别应映射到 GE (5,0)。"""
        assert get_category_layer_tuple("detector") == (5, 0)

    def test_waveguide_maps_to_wg(self) -> None:
        """waveguide 类别应映射到 WG (1,0)（与器件同层）。"""
        assert get_category_layer_tuple("waveguide") == (1, 0)

    def test_port_maps_to_pinrec(self) -> None:
        """port 类别应映射到 PORT (1,10)。"""
        assert get_category_layer_tuple("port") == (1, 10)

    def test_devrec_maps_to_devrec(self) -> None:
        """devrec 类别应映射到 DEVREC (68,0)。"""
        assert get_category_layer_tuple("devrec") == (68, 0)

    def test_unknown_category_falls_back_to_wg(self) -> None:
        """未知类别应回退到 WG (1,0)。"""
        assert get_category_layer_tuple("nonexistent") == (1, 0)


class TestGetLayerTuple:
    """验证 get_layer_tuple 函数。"""

    def test_get_wg_tuple(self) -> None:
        """get_layer_tuple('WG') 应返回 (1,0)。"""
        assert get_layer_tuple("WG") == (1, 0)

    def test_get_port_tuple(self) -> None:
        """get_layer_tuple('PORT') 应返回 (1,10)。"""
        assert get_layer_tuple("PORT") == (1, 10)

    def test_get_unknown_raises_keyerror(self) -> None:
        """未知层名应抛出 KeyError。"""
        with pytest.raises(KeyError):
            get_layer_tuple("NONEXISTENT_LAYER")


class TestLayerMapCompleteness:
    """验证 layer_map 的完整性与一致性。"""

    def test_all_layers_have_unique_layer_datatype(self) -> None:
        """所有物理层（fabricated=True）的 (layer, datatype) 应唯一。

        Virtual 层（fabricated=False）可与物理层同 layer 号但不同 datatype
        （如 PORT=(1,10) 与 WG=(1,0) 同 layer=1 但 datatype 不同）。
        """
        fabricated_pairs = [
            (gl.layer, gl.datatype) for gl in POLARIS_GDS_LAYER_MAP.values() if gl.fabricated
        ]
        assert len(fabricated_pairs) == len(set(fabricated_pairs)), (
            "物理层 (layer, datatype) 对存在重复"
        )

    def test_all_layers_have_nonempty_name_and_purpose(self) -> None:
        """所有层应有非空 name 与 purpose。"""
        for key, gl in POLARIS_GDS_LAYER_MAP.items():
            assert gl.name, f"{key} 的 name 为空"
            assert gl.purpose, f"{key} 的 purpose 为空"

    def test_layer_numbers_in_valid_gds_range(self) -> None:
        """物理流片层 layer number 应在 GDSII 合法范围 [0, 255]。

        Virtual 层（fabricated=False）允许使用 klayout 扩展范围 [0, 65535]，
        因为 klayout/OASIS 支持扩展层号（如 gdsfactory 的 WAFER=999）。
        物理层必须严格 GDSII 合规以确保 foundry 能流片。
        """
        for key, gl in POLARIS_GDS_LAYER_MAP.items():
            assert 0 <= gl.datatype <= 255, f"{key} 的 datatype {gl.datatype} 超出 GDSII 范围"
            if gl.fabricated:
                assert 0 <= gl.layer <= 255, (
                    f"物理层 {key} 的 layer {gl.layer} 超出 GDSII 范围 [0,255]"
                )
            else:
                assert 0 <= gl.layer <= 65535, (
                    f"virtual 层 {key} 的 layer {gl.layer} 超出 klayout 扩展范围"
                )

    def test_category_map_covers_all_polaris_categories(self) -> None:
        """类别映射应覆盖 PoLaRIS 所有器件类别。"""
        required = {"passive", "active", "source", "detector", "waveguide", "port"}
        for cat in required:
            assert cat in POLARIS_CATEGORY_LAYER_MAP, f"缺少类别映射: {cat}"

    def test_category_map_values_are_valid_layer_names(self) -> None:
        """类别映射的值应为 POLARIS_GDS_LAYER_MAP 中的有效层名。"""
        for cat, layer_name in POLARIS_CATEGORY_LAYER_MAP.items():
            assert layer_name in POLARIS_GDS_LAYER_MAP, (
                f"类别 {cat} 引用了不存在的层名: {layer_name}"
            )
