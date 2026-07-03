"""polaris-pdk 子模块深度测试（v5.1：仅器件库查询，36 器件 × 4 平台）。

v5.1 起 GDSII 导入导出测试已迁移到 polaris-gdsio/tests/test_gdsio.py。
本文件覆盖 3 个公开 API 的深度验证:
    - list_platforms(): 4 平台元信息（SOI/SiN/InP/LNOI）
    - list_devices(platform): 单平台 9 器件清单
    - get_device(platform, device_type): 单器件参数（对照公开文献）

测试维度（共 36 个测试，R05 回归防护）:
1. 平台元信息完整性：4 平台、foundry、process_node、device_count
2. 各平台器件清单：SOI/SiN/InP/LNOI 各 9 器件，共 36
3. 关键器件参数对照公开文献（R02 学术诚信，禁止假数据）:
   - SOI grating_coupler: insertion_loss_db=1.9（三星 300mm OFC 2026）
   - SOI strip_waveguide: width_um=0.5, loss_db_cm=2.0（SiEPIC EBeam PDK）
   - SOI ge_photodetector: responsivity_a_w=0.8（AIM Photonics）
   - SiN sin_waveguide_lpcvd: loss_db_cm=0.1（Ligentec ANR PDK）
   - SiN sin_ring_high_q: q_factor=1000000.0（EPFL Damascene）
   - InP dfb_laser: output_power_mw=3.0, smsr_db=40.0（Soares 2019）
   - InP soa: gain_db=20.0（Soares 2019）
   - InP soa_high_power: output_power_mw=1000.0（SemiNex）
   - LNOI lnoi_eo_modulator: bandwidth_ghz=110.0, vpi_v=3.0（Liu 2025）
   - LNOI lnoi_waveguide: loss_db_cm=0.4（Liu 2025）
   - LNOI lnoi_cmos_modulator: drive_voltage_v=1.0（Wang Nature 2018）
4. 器件参数边界: width_um>0, loss_db_cm>=0, q_factor>0, bandwidth_ghz>0
5. 错误处理（R03 禁止 fall-back）: 未知平台/器件 raise RuntimeError
6. 深拷贝独立性: 修改返回值不影响内部数据
7. JSON 可序列化（稳定 API 原则）
8. pdk_reference 字段每平台一致
9. 模块元信息: __version__ / __all__ / 无 GDSII 残留

来源（R02 学术诚信，均经 WebSearch 验证可访问，>=5 个文献 URL）:
- SiEPIC EBeam PDK (UBC, MIT): https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- 三星 300mm 硅光平台 OFC 2026:
  https://cloud.tencent.com.cn/developer/article/2650050
- Ligentec ANR SiN PDK: https://www.ligentec.com/
- LioniX TriPleX SiN 波导技术:
  https://www.lionix-international.com/photonics/pic-technology/triplex-waveguide-technology/
- Soares et al., "InP-Based Foundry PICs for Optical Interconnects",
  Appl. Sci. 2019, 9(8), 1588 — https://doi.org/10.3390/app9081588
- Liu et al., Light: Advanced Manufacturing 2025, 6, 47 —
  https://doi.org/10.37188/lam.2025.047
- Wang et al., Nature 2018, 562:101-104 — https://doi.org/10.1038/s41586-018-0551-y
- EPFL Damascene SiN high-Q microring — https://doi.org/10.3390/app13063660
- HyperLight LNOI PDK: https://hyperlightphotonics.com/
- pytest 文档: https://docs.pytest.org/

合规: R02 学术诚信 / R03 禁止 fall-back / R05 Bug 必修 / R04 不参与 GPU。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# 让测试既能从已安装包导入，也能从源码树导入（CI/开发模式）
_SRC = str(Path(__file__).resolve().parents[1] / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from polaris_pdk import get_device, list_devices, list_platforms  # noqa: E402

# ---------------------------------------------------------------------------
# 期望常量（与 catalog.py 数据完全一致，避免硬编码字符串散落）
# ---------------------------------------------------------------------------
_PLATFORMS_EXPECTED = ["SOI", "SiN", "InP", "LNOI"]
_FOUNDRY_MAP = {
    "SOI": "SiEPIC",
    "SiN": "Ligentec",
    "InP": "Pattern Project",
    "LNOI": "HyperLight",
}
_PROCESS_NODE_MAP = {
    "SOI": "220nm SOI",
    "SiN": "SiN TriPleX",
    "InP": "InP generic",
    "LNOI": "LNOI X-cut",
}
_PDK_REFERENCE_MAP = {
    "SOI": "SiEPIC_EBeam_PDK",
    "SiN": "Ligentec_ANR_PDK",
    "InP": "Pattern_Project_InP_PDK",
    "LNOI": "HyperLight_LNOI_PDK",
}
# 各平台 device_type 清单（共 36，4 × 9）
_DEVICE_TYPES_PER_PLATFORM = {
    "SOI": [
        "strip_waveguide", "grating_coupler", "y_branch", "mmi_1x2",
        "ring_resonator", "directional_coupler", "mzi",
        "thermo_optic_phase_shifter", "ge_photodetector",
    ],
    "SiN": [
        "sin_waveguide_lpcvd", "triplex_double_stripe", "sin_grating_coupler_1d",
        "sin_ring_high_q", "sin_mmi_1x2", "sin_directional_coupler",
        "sin_mzi", "sin_thermo_optic", "sin_waveguide_damascene",
    ],
    "InP": [
        "inp_waveguide", "eam_modulator", "inp_photodetector", "soa",
        "dfb_laser", "dbr_laser", "sgdbr_laser", "inp_mzm", "soa_high_power",
    ],
    "LNOI": [
        "lnoi_waveguide", "lnoi_eo_modulator", "lnoi_mzm_high_confined",
        "lnoi_mzm_traveling_wave", "lnoi_modulator_review",
        "lnoi_photonics_review", "lnoi_cmos_modulator",
        "lnoi_tfln_modulator", "lnoi_y_branch",
    ],
}


# ===========================================================================
# 1. list_platforms API 测试（5 个）
# ===========================================================================
class TestListPlatforms:
    """list_platforms API 深度验证。"""

    def test_platforms_count_is_4(self):
        """平台总数必须为 4（SOI/SiN/InP/LNOI）。"""
        ps = list_platforms()
        assert isinstance(ps, list)
        assert len(ps) == 4

    def test_platforms_order_and_names(self):
        """平台顺序固定为 SOI/SiN/InP/LNOI（与 _PLATFORM_META 字典顺序一致）。"""
        ps = list_platforms()
        names = [p["platform"] for p in ps]
        assert names == _PLATFORMS_EXPECTED

    def test_platforms_required_fields(self):
        """每个平台 dict 必须含 5 个必要字段。"""
        ps = list_platforms()
        for p in ps:
            assert "platform" in p
            assert "foundry" in p
            assert "process_node" in p
            assert "device_count" in p
            assert "device_names" in p
            assert isinstance(p["device_names"], list)
            assert p["device_count"] == len(p["device_names"])

    def test_platforms_foundry_and_process_node_correctness(self):
        """foundry + process_node 对照公开文献（SiEPIC 220nm SOI / Ligentec SiN TriPleX 等）。"""
        ps = list_platforms()
        foundry_map = {p["platform"]: p["foundry"] for p in ps}
        pn_map = {p["platform"]: p["process_node"] for p in ps}
        for plat in _PLATFORMS_EXPECTED:
            expected_foundry = _FOUNDRY_MAP[plat]
            expected_pn = _PROCESS_NODE_MAP[plat]
            assert expected_foundry in foundry_map[plat], (
                f"{plat} foundry 应含 '{expected_foundry}'，实际 '{foundry_map[plat]}'"
            )
            assert pn_map[plat] == expected_pn, (
                f"{plat} process_node 应为 '{expected_pn}'，实际 '{pn_map[plat]}'"
            )


# ===========================================================================
# 2. list_devices API 测试（6 个）
# ===========================================================================
class TestListDevices:
    """list_devices API 深度验证。"""

    @pytest.mark.parametrize("platform", _PLATFORMS_EXPECTED)
    def test_list_devices_count_9(self, platform):
        """每个平台返回 9 个器件（4 × 9 = 36 总数）。"""
        devs = list_devices(platform)
        assert isinstance(devs, list)
        assert len(devs) == 9
        for d in devs:
            assert d["platform"] == platform

    def test_list_devices_device_types_match(self):
        """各平台返回的 device_type 与目录清单完全一致。"""
        for platform, expected_types in _DEVICE_TYPES_PER_PLATFORM.items():
            devs = list_devices(platform)
            actual_types = [d["device_type"] for d in devs]
            assert actual_types == expected_types, (
                f"{platform} device_type 清单不匹配"
            )

    def test_list_devices_unknown_raises(self):
        """未知平台 raise RuntimeError（R03 禁止 fall-back）。"""
        with pytest.raises(RuntimeError, match="平台"):
            list_devices("UnknownPlatform")
        with pytest.raises(RuntimeError, match="平台"):
            list_devices("")

    def test_list_devices_deep_copy_independence(self):
        """list_devices 返回深拷贝，修改不影响内部数据（R05 回归防护）。"""
        devs1 = list_devices("SOI")
        original_loss = devs1[0]["params"].get("loss_db_cm")
        # 篡改返回值
        devs1[0]["params"]["loss_db_cm"] = 999.0
        devs1[0]["name"] = "TAMPERED"
        devs1[0]["ports"].append(("fake", 0, 0, "north"))
        # 再次获取应不受影响
        devs2 = list_devices("SOI")
        assert devs2[0]["name"] != "TAMPERED"
        assert devs2[0]["params"].get("loss_db_cm") == original_loss
        assert len(devs2[0]["ports"]) != len(devs1[0]["ports"]) - 1 + 1  # 内部未被追加

    def test_list_devices_all_have_pdk_reference(self):
        """所有 36 器件 params 必须含 pdk_reference 字段且与平台一致。"""
        for platform in _PLATFORMS_EXPECTED:
            devs = list_devices(platform)
            expected_ref = _PDK_REFERENCE_MAP[platform]
            for d in devs:
                assert d["params"]["pdk_reference"] == expected_ref, (
                    f"{platform}/{d['device_type']} pdk_reference 应为 '{expected_ref}'"
                )

    def test_list_devices_all_have_source_url(self):
        """所有 36 器件必须含 source.url（R02 学术诚信溯源）。"""
        for platform in _PLATFORMS_EXPECTED:
            devs = list_devices(platform)
            for d in devs:
                assert "source" in d
                assert "url" in d["source"]
                assert d["source"]["url"].startswith("http"), (
                    f"{platform}/{d['device_type']} source.url 非有效 URL"
                )
                assert "year" in d["source"]
                assert d["source"]["year"] >= 2000


# ===========================================================================
# 3. get_device SOI 平台测试（5 个）
# ===========================================================================
class TestGetDeviceSOI:
    """SOI 平台器件参数对照公开文献（SiEPIC EBeam PDK / Samsung 300mm）。"""

    def test_soi_strip_waveguide_params(self):
        """SOI strip_waveguide: width=0.5μm, height=0.22μm, loss=2.0 dB/cm（SiEPIC）。"""
        d = get_device("SOI", "strip_waveguide")
        assert d["platform"] == "SOI"
        assert d["device_type"] == "strip_waveguide"
        assert d["category"] == "passive"
        assert d["foundry"] == "SiEPIC"
        assert d["process_node"] == "220nm SOI"
        # 关键参数对照 SiEPIC EBeam PDK
        assert d["params"]["width_um"] == 0.5
        assert d["params"]["height_um"] == 0.22
        assert d["params"]["loss_db_cm"] == 2.0  # SiEPIC 典型 2-3 dB/cm
        assert d["params"]["wavelength_nm"] == 1550
        assert d["params"]["pdk_reference"] == "SiEPIC_EBeam_PDK"
        # 端口与包围盒
        assert len(d["ports"]) == 2  # in / out
        assert d["bbox_um"]["xmax"] > d["bbox_um"]["xmin"]

    def test_soi_grating_coupler_samsung_300mm(self):
        """SOI grating_coupler: insertion_loss_db=1.9（三星 300mm OFC 2026）。"""
        d = get_device("SOI", "grating_coupler")
        # 三星 300mm 平台峰值耦合损耗 1.9dB（OFC 2026）
        assert d["params"]["insertion_loss_db"] == 1.9
        # SiEPIC EBeam GC 典型 3-5 dB（对照参考）
        assert d["params"]["siepic_typical_loss_db"] == 4.1
        assert d["params"]["bandwidth_1db_nm"] == 27
        assert d["params"]["polarization"] == "TE"
        # foundry 联合标注
        assert "SiEPIC" in d["foundry"]
        assert "Samsung" in d["foundry"]

    def test_soi_ring_resonator_q_factor(self):
        """SOI ring_resonator: Q=10000, FSR=10nm（SiEPIC 典型）。"""
        d = get_device("SOI", "ring_resonator")
        assert d["params"]["radius_um"] == 10.0
        assert d["params"]["q_factor"] == 10000.0  # SiEPIC 典型 Q ~1e4
        assert d["params"]["fsr_nm"] == 10.0
        # 三端口: in / through / drop
        port_names = [p[0] for p in d["ports"]]
        assert "in" in port_names
        assert "through" in port_names
        assert "drop" in port_names

    def test_soi_ge_photodetector_responsivity(self):
        """SOI ge_photodetector: responsivity=0.8 A/W, BW=40GHz（AIM Photonics）。"""
        d = get_device("SOI", "ge_photodetector")
        assert d["category"] == "detector"
        assert d["params"]["responsivity_a_w"] == 0.8  # Ge PD >0.8 A/W
        assert d["params"]["bandwidth_ghz"] == 40.0
        assert d["params"]["dark_current_na"] == 10.0

    def test_soi_thermo_optic_phase_shifter_pi_power(self):
        """SOI thermo_optic_phase_shifter: Pπ=20mW（SiEPIC 热光移相器典型值）。"""
        d = get_device("SOI", "thermo_optic_phase_shifter")
        assert d["category"] == "active"
        assert d["params"]["pi_power_mw"] == 20.0
        assert d["params"]["length_um"] == 100.0
        assert d["params"]["loss_db"] == 0.5


# ===========================================================================
# 4. get_device SiN 平台测试（4 个）
# ===========================================================================
class TestGetDeviceSiN:
    """SiN 平台器件参数对照公开文献（Ligentec ANR / LioniX TriPleX / EPFL）。"""

    def test_sin_waveguide_lpcvd_low_loss(self):
        """SiN sin_waveguide_lpcvd: loss=0.1 dB/cm（Ligentec LPCVD SiN <0.1）。"""
        d = get_device("SiN", "sin_waveguide_lpcvd")
        assert d["params"]["width_um"] == 1.0
        assert d["params"]["height_um"] == 0.2
        assert d["params"]["loss_db_cm"] == 0.1  # Ligentec LPCVD SiN <0.1 dB/cm
        assert d["foundry"] == "Ligentec"
        assert d["process_node"] == "SiN TriPleX"

    def test_sin_ring_high_q_one_million(self):
        """SiN sin_ring_high_q: Q=1000000（EPFL Damascene SiN 高 Q ~1e6）。"""
        d = get_device("SiN", "sin_ring_high_q")
        assert d["params"]["radius_um"] == 100.0
        assert d["params"]["q_factor"] == 1000000.0  # EPFL Damascene ~1e6
        assert d["params"]["fsr_nm"] == 1.0
        # 来源 EPFL Damascene
        assert "EPFL" in d["source"]["authors"]
        assert d["source"]["year"] == 2023

    def test_sin_triplex_double_stripe_lionix(self):
        """SiN triplex_double_stripe: width=1.5μm, loss=0.1 dB/cm（LioniX TriPleX）。"""
        d = get_device("SiN", "triplex_double_stripe")
        assert d["params"]["width_um"] == 1.5
        assert d["params"]["loss_db_cm"] == 0.1
        assert "LioniX" in d["foundry"]
        # LioniX TriPleX 来源 URL
        assert "lionix-international.com" in d["source"]["url"]

    def test_sin_mzi_arm_length_longer_than_soi(self):
        """SiN sin_mzi 臂长 500μm > SOI mzi 100μm（SiN 弯曲半径大）。"""
        sin_mzi = get_device("SiN", "sin_mzi")
        soi_mzi = get_device("SOI", "mzi")
        assert sin_mzi["params"]["arm_length_um"] == 500.0
        assert soi_mzi["params"]["arm_length_um"] == 100.0
        # SiN 臂长 > SOI 臂长（物理一致性：SiN 弯曲半径更大）
        assert sin_mzi["params"]["arm_length_um"] > soi_mzi["params"]["arm_length_um"]


# ===========================================================================
# 5. get_device InP 平台测试（4 个）
# ===========================================================================
class TestGetDeviceInP:
    """InP 平台器件参数对照公开文献（Pattern Project / JEPPIX / Soares 2019）。"""

    def test_inp_dfb_laser_specs(self):
        """InP dfb_laser: Pout=3mW, SMSR=40dB（Soares 2019 Appl. Sci.）。"""
        d = get_device("InP", "dfb_laser")
        assert d["category"] == "source"
        assert d["params"]["output_power_mw"] == 3.0
        assert d["params"]["smsr_db"] == 40.0
        assert d["params"]["wavelength_nm"] == 1550
        # 来源 Soares 2019
        assert "Soares" in d["source"]["authors"]
        assert d["source"]["year"] == 2019
        assert "app9081588" in d["source"]["url"]

    def test_inp_soa_gain_20db(self):
        """InP soa: gain=20dB, gain/100μm=4dB（Soares 2019）。"""
        d = get_device("InP", "soa")
        assert d["category"] == "active"
        assert d["params"]["gain_db"] == 20.0  # SOA 增益 ~20dB
        assert d["params"]["gain_db_per_100um"] == 4.0
        assert d["params"]["length_um"] == 500.0

    def test_inp_soa_high_power_1w(self):
        """InP soa_high_power: Pout=1000mW (1W), gain=30dB（SemiNex）。"""
        d = get_device("InP", "soa_high_power")
        assert d["params"]["output_power_mw"] == 1000.0  # >1W 输出
        assert d["params"]["gain_db"] == 30.0
        assert d["params"]["pce_percent"] == 25.0  # 功率转换效率 ~25%@25°C
        assert d["params"]["length_um"] == 2000.0
        # 来源 SemiNex
        assert "SemiNex" in d["source"]["authors"]

    def test_inp_mzm_vpi_3v(self):
        """InP inp_mzm: Vπ=3V, BW=40GHz（Zhao 2018 JSTQE）。"""
        d = get_device("InP", "inp_mzm")
        assert d["category"] == "active"
        assert d["params"]["vpi_v"] == 3.0
        assert d["params"]["bandwidth_ghz"] == 40.0
        assert d["params"]["length_um"] == 1000.0
        # 来源 Zhao 2018
        assert "Zhao" in d["source"]["authors"]
        assert "JSTQE" in d["source"]["url"]


# ===========================================================================
# 6. get_device LNOI 平台测试（4 个）
# ===========================================================================
class TestGetDeviceLNOI:
    """LNOI 平台器件参数对照公开文献（HyperLight / Liu 2025 / Wang Nature 2018）。"""

    def test_lnoi_eo_modulator_110ghz(self):
        """LNOI lnoi_eo_modulator: BW=110GHz, Vπ=3V（Liu 2025 LAM）。"""
        d = get_device("LNOI", "lnoi_eo_modulator")
        assert d["category"] == "active"
        assert d["foundry"] == "HyperLight"
        assert d["params"]["bandwidth_ghz"] == 110.0  # >110 GHz
        assert d["params"]["vpi_v"] == 3.0  # <3 V
        assert d["params"]["modulator_length_um"] == 1000.0
        # 来源 Liu 2025
        assert "Liu" in d["source"]["authors"]
        assert d["source"]["year"] == 2025
        assert "lam.2025.047" in d["source"]["url"]

    def test_lnoi_waveguide_low_loss(self):
        """LNOI lnoi_waveguide: loss=0.4 dB/cm（Liu 2025 <0.4 dB/cm）。"""
        d = get_device("LNOI", "lnoi_waveguide")
        assert d["params"]["width_um"] == 1.5
        assert d["params"]["loss_db_cm"] == 0.4
        assert d["category"] == "passive"

    def test_lnoi_cmos_modulator_1v(self):
        """LNOI lnoi_cmos_modulator: Vdrive=1V（Wang Nature 2018 CMOS 兼容）。"""
        d = get_device("LNOI", "lnoi_cmos_modulator")
        assert d["params"]["drive_voltage_v"] == 1.0  # CMOS 兼容 <1V
        assert d["params"]["vpi_v"] == 1.0
        assert d["params"]["bandwidth_ghz"] == 100.0
        # 来源 Wang Nature 2018
        assert "Wang" in d["source"]["authors"]
        assert d["source"]["year"] == 2018
        assert "s41586-018-0551-y" in d["source"]["url"]

    def test_lnoi_photonics_review_r33(self):
        """LNOI lnoi_photonics_review: r33=30 pm/V, 透明窗口 0.4-5.0μm（Zhu 2021）。"""
        d = get_device("LNOI", "lnoi_photonics_review")
        assert d["params"]["transparency_window_min_um"] == 0.4
        assert d["params"]["transparency_window_max_um"] == 5.0
        assert d["params"]["eo_coefficient_r33_pm_v"] == 30.0  # r33 ~30 pm/V
        # 来源 Zhu 2021 AOP
        assert "Zhu" in d["source"]["authors"]
        assert "AOP.411024" in d["source"]["url"]


# ===========================================================================
# 7. 错误处理与边界测试（5 个）
# ===========================================================================
class TestErrorHandling:
    """R03 禁止 fall-back：未知平台/器件必须 raise RuntimeError。"""

    def test_get_device_unknown_platform_raises(self):
        """get_device 未知平台 raise RuntimeError，错误消息含可用平台列表。"""
        with pytest.raises(RuntimeError, match="平台"):
            get_device("UnknownPlatform", "grating_coupler")
        with pytest.raises(RuntimeError, match="平台"):
            get_device("", "grating_coupler")

    def test_get_device_unknown_device_raises(self):
        """get_device 未知器件 raise RuntimeError，错误消息含可用器件列表。"""
        with pytest.raises(RuntimeError, match="器件"):
            get_device("SOI", "nonexistent_device")
        with pytest.raises(RuntimeError, match="器件"):
            get_device("LNOI", "typo_device_name")

    def test_get_device_correct_platform_wrong_device_raises(self):
        """跨平台查询: SOI 的 device_type 在 SiN 平台查询应 raise。"""
        # SOI 的 strip_waveguide 在 SiN 平台不存在
        with pytest.raises(RuntimeError, match="器件"):
            get_device("SiN", "strip_waveguide")
        # SiN 的 sin_ring_high_q 在 SOI 平台不存在
        with pytest.raises(RuntimeError, match="器件"):
            get_device("SOI", "sin_ring_high_q")

    def test_list_devices_unknown_platform_raises(self):
        """list_devices 未知平台 raise RuntimeError。"""
        with pytest.raises(RuntimeError, match="平台"):
            list_devices("GaAs")
        with pytest.raises(RuntimeError, match="平台"):
            list_devices("silicon")  # 大小写敏感

    def test_get_device_all_36_combinations_valid(self):
        """所有 4×9=36 个 platform/device_type 组合都能正确返回（无遗漏）。"""
        for platform, device_types in _DEVICE_TYPES_PER_PLATFORM.items():
            for dt in device_types:
                d = get_device(platform, dt)
                assert d["platform"] == platform
                assert d["device_type"] == dt
                assert d["params"]["pdk_reference"] == _PDK_REFERENCE_MAP[platform]


# ===========================================================================
# 8. 深拷贝与序列化测试（3 个）
# ===========================================================================
class TestDeepCopyAndSerialization:
    """深拷贝独立性与 JSON 可序列化验证。"""

    def test_get_device_deep_copy_independence(self):
        """get_device 返回深拷贝，修改不影响内部数据。"""
        d1 = get_device("SOI", "grating_coupler")
        original_loss = d1["params"]["insertion_loss_db"]
        # 篡改返回值
        d1["params"]["insertion_loss_db"] = 999.0
        d1["params"]["new_field"] = "injected"
        d1["source"]["url"] = "https://evil.com"
        d1["ports"].append(["fake", 0, 0, "north"])
        d1["bbox_um"]["xmin"] = -999.0
        # 再次获取应不受影响
        d2 = get_device("SOI", "grating_coupler")
        assert d2["params"]["insertion_loss_db"] == original_loss
        assert "new_field" not in d2["params"]
        assert d2["source"]["url"] != "https://evil.com"
        assert len(d2["ports"]) == 1  # 原始只有 1 个端口
        assert d2["bbox_um"]["xmin"] != -999.0

    def test_get_device_json_serializable(self):
        """所有 36 器件 dict 必须可 JSON 序列化（稳定 API 原则）。"""
        for platform in _PLATFORMS_EXPECTED:
            devs = list_devices(platform)
            for d in devs:
                # 不抛异常即成功
                json_str = json.dumps(d)
                # 反序列化后字段完整
                restored = json.loads(json_str)
                assert restored["platform"] == d["platform"]
                assert restored["device_type"] == d["device_type"]
                assert restored["params"]["pdk_reference"] == d["params"]["pdk_reference"]

    def test_list_platforms_json_serializable(self):
        """list_platforms 返回值必须可 JSON 序列化。"""
        ps = list_platforms()
        json_str = json.dumps(ps)
        restored = json.loads(json_str)
        assert len(restored) == 4
        assert restored[0]["platform"] == "SOI"
        assert restored[-1]["platform"] == "LNOI"


# ===========================================================================
# 9. 多平台对比测试（3 个）
# ===========================================================================
class TestMultiPlatformComparison:
    """跨平台物理一致性验证。"""

    def test_waveguide_loss_comparison(self):
        """波导损耗对比: SiN(0.1) < LNOI(0.4) < SOI=InP(2.0)。"""
        soi_wg = get_device("SOI", "strip_waveguide")
        sin_wg = get_device("SiN", "sin_waveguide_lpcvd")
        inp_wg = get_device("InP", "inp_waveguide")
        lnoi_wg = get_device("LNOI", "lnoi_waveguide")
        # SiN 损耗最低（Ligentec LPCVD <0.1 dB/cm）
        assert sin_wg["params"]["loss_db_cm"] < lnoi_wg["params"]["loss_db_cm"]
        assert lnoi_wg["params"]["loss_db_cm"] < soi_wg["params"]["loss_db_cm"]
        # SOI 与 InP 损耗相同（2.0 dB/cm）
        assert soi_wg["params"]["loss_db_cm"] == inp_wg["params"]["loss_db_cm"]

    def test_ring_q_factor_comparison(self):
        """环谐振器 Q 因子对比: SiN(1e6) >> SOI(1e4)。"""
        soi_ring = get_device("SOI", "ring_resonator")
        sin_ring = get_device("SiN", "sin_ring_high_q")
        # SiN Damascene 高 Q 比 SOI 高 100 倍
        assert sin_ring["params"]["q_factor"] > soi_ring["params"]["q_factor"]
        assert sin_ring["params"]["q_factor"] / soi_ring["params"]["q_factor"] == 100.0
        # SiN 环半径更大（高 Q 需要更大周长）
        assert sin_ring["params"]["radius_um"] > soi_ring["params"]["radius_um"]

    def test_modulator_bandwidth_comparison(self):
        """调制器带宽对比: LNOI EO(110GHz) > InP MZM(40GHz)。"""
        lnoi_mod = get_device("LNOI", "lnoi_eo_modulator")
        inp_mod = get_device("InP", "inp_mzm")
        # LNOI 电光调制器带宽 > InP MZM（LNOI 本征高速）
        assert lnoi_mod["params"]["bandwidth_ghz"] > inp_mod["params"]["bandwidth_ghz"]
        assert lnoi_mod["params"]["bandwidth_ghz"] == 110.0
        assert inp_mod["params"]["bandwidth_ghz"] == 40.0


# ===========================================================================
# 10. 模块元信息与 GDSII 拆分验证（2 个）
# ===========================================================================
class TestModuleMetadata:
    """模块元信息与 v5.1 GDSII 拆分回归测试。"""

    def test_pdk_no_gdsio_attr(self):
        """v5.1: polaris-pdk 不再导出 export_gds/import_gds（已拆到 polaris-gdsio）。"""
        import polaris_pdk
        assert not hasattr(polaris_pdk, "export_gds")
        assert not hasattr(polaris_pdk, "import_gds")
        # __all__ 只含器件库查询 API
        assert set(polaris_pdk.__all__) == {
            "list_platforms", "get_device", "list_devices", "__version__",
        }

    def test_version_is_5_1_0(self):
        """版本号必须为 5.1.0（v5.1 GDSII 拆分后）。"""
        import polaris_pdk
        assert polaris_pdk.__version__ == "5.1.0"
