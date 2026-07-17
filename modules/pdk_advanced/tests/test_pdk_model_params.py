"""PDK 工艺级光学模型参数测试（PDK 深度桥接 R384，2026-07-17）。

覆盖 ``polaris_pdk_advanced.pdk_model_params`` 模块的全部公开 API:
- PDKModelParameters dataclass 10 个字段
- PDK_MODEL_PARAMS_REGISTRY 4 PDK 注册表
- get_pdk_model_params() 查询 / R03 KeyError 行为
- list_available_pdk_model_params() 列表

R03 合规验证: 未注册 PDK 必须 raise KeyError，禁止 fall-back。
R02 学术诚信: 每个参数值有文献溯源（见 pdk_model_params.py docstring）。

学术依据（R02 学术诚信，≥5 文献 URL）:
- Soref 1993 SOI: https://doi.org/10.1364/AO.32.003546
- SiEPIC EBeam PDK: https://github.com/SiEPIC/OpenEBL
- IMEC iSiPP50G: https://www.imec-int.com/en/what-we-offer/research-platforms/silicon-photonics
- AMF Foundry: https://www.a-star.edu.sg/amf
- Ligentec SiN: https://www.ligentec.com/
- Cocorullo 1999 (Si dn/dT): https://doi.org/10.1088/0268-1242/14/11/307
- Subbaraman 2013 (SiN dn/dT): https://doi.org/10.1364/OE.21.027289
- Chrostowski & Hochberg 2015: https://www.cambridge.org/core/search?searchField=isbn&searchTerms=1107007731

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R05 无 TODO。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# 让测试既能从已安装包导入，也能从源码树导入（CI/开发模式）
_SRC = str(Path(__file__).resolve().parents[1] / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from polaris_pdk_advanced.pdk_model_params import (  # noqa: E402
    PDK_MODEL_PARAMS_REGISTRY,
    PDKModelParameters,
    get_pdk_model_params,
    list_available_pdk_model_params,
)


# =============================================================================
# 1. SiEPIC EBeam PDK 模型参数（Soref 1993 SOI / Chrostowski 2015）
# =============================================================================


def test_siepic_ebeam_model_params():
    """SiEPIC EBeam PDK 模型参数（220nm SOI）。

    来源: https://github.com/SiEPIC/OpenEBL
          Chrostowski & Hochberg 2015 §3.2/3.4
    """
    params = get_pdk_model_params("siepic_ebeam")
    assert isinstance(params, PDKModelParameters)
    # neff_strip_1550=2.40（Chrostowski 2015 §3.2，220nm×450nm SOI strip WG）
    assert params.neff_strip_1550 == pytest.approx(2.40, abs=1e-6)
    # ng_strip_1550=4.20（Chrostowski 2015 §3.4，Si ng≈4.2）
    assert params.ng_strip_1550 == pytest.approx(4.20, abs=1e-6)
    # propagation_loss=3.0 dB/cm（SiEPIC EBeam PDK 文档）
    assert params.propagation_loss_db_cm == pytest.approx(3.0, abs=1e-6)
    # bend_radius_min=5.0μm（SiEPIC EBeam PDK 标准）
    assert params.bend_radius_min_um == pytest.approx(5.0, abs=1e-6)
    # MZM Vπ·L=2.0 V·cm（Soref & Bennett 1987 等离子色散 + SiEPIC p-n 结）
    assert params.modulator_vpi_l_v_cm == pytest.approx(2.0, abs=1e-6)
    # heater_resistance=1000Ω（SiEPIC TiN 加热器典型 1kΩ）
    assert params.heater_resistance_ohm == pytest.approx(1000.0, abs=1e-6)
    # pd_responsivity=0.80 A/W（SiEPIC Ge PD @ 1550nm）
    assert params.pd_responsivity_a_w == pytest.approx(0.80, abs=1e-6)
    # coupling_loss=4.5 dB（SiEPIC GC 典型）
    assert params.coupling_loss_db == pytest.approx(4.5, abs=1e-6)
    # temperature_coefficient_dn_dT=1.86e-4 /K（Cocorullo 1999, Si）
    assert params.temperature_coefficient_dn_dT == pytest.approx(1.86e-4, rel=1e-3)
    # neff_rib_1550 应大于 neff_strip_1550（肋形波导限制更强）
    assert params.neff_rib_1550 > params.neff_strip_1550


# =============================================================================
# 2. IMEC iSiPP50G 模型参数（IMEC 220nm SOI）
# =============================================================================


def test_imec_isipp50g_model_params():
    """IMEC iSiPP50G PDK 模型参数（220nm SOI，低损耗）。

    来源: https://www.imec-int.com/en/what-we-offer/research-platforms/silicon-photonics
    """
    params = get_pdk_model_params("imec_isipp50g")
    assert isinstance(params, PDKModelParameters)
    # neff_strip_1550=2.46（IMEC iSiPP50G 文档）
    assert params.neff_strip_1550 == pytest.approx(2.46, abs=1e-6)
    # propagation_loss=2.7 dB/cm（IMEC iSiPP50G 损耗低于 SiEPIC）
    assert params.propagation_loss_db_cm == pytest.approx(2.7, abs=1e-6)
    # bend_radius_min=5.0μm（IMEC iSiPP50G 标准）
    assert params.bend_radius_min_um == pytest.approx(5.0, abs=1e-6)
    # coupling_loss=3.5 dB（IMEC GC 优于 SiEPIC）
    assert params.coupling_loss_db == pytest.approx(3.5, abs=1e-6)
    # Si 工艺热光系数与 SiEPIC 相同（Cocorullo 1999）
    assert params.temperature_coefficient_dn_dT == pytest.approx(1.86e-4, rel=1e-3)
    # IMEC 损耗应低于 SiEPIC（工艺更先进）
    siepic = get_pdk_model_params("siepic_ebeam")
    assert params.propagation_loss_db_cm < siepic.propagation_loss_db_cm


# =============================================================================
# 3. AMF 模型参数（A*STAR IME 220nm SOI）
# =============================================================================


def test_amf_model_params():
    """AMF (A*STAR IME) PDK 模型参数（220nm SOI，弯曲半径 10μm）。

    来源: https://www.a-star.edu.sg/amf
    """
    params = get_pdk_model_params("amf")
    assert isinstance(params, PDKModelParameters)
    # neff_strip_1550=2.40（与 SiEPIC 同为 220nm SOI）
    assert params.neff_strip_1550 == pytest.approx(2.40, abs=1e-6)
    # bend_radius_min=10.0μm（AMF 标准，大于 SiEPIC/IMEC 的 5μm）
    assert params.bend_radius_min_um == pytest.approx(10.0, abs=1e-6)
    # pd_responsivity=0.85 A/W（AMF Ge PD 略优）
    assert params.pd_responsivity_a_w == pytest.approx(0.85, abs=1e-6)
    # coupling_loss=5.0 dB（AMF GC 略差于 SiEPIC）
    assert params.coupling_loss_db == pytest.approx(5.0, abs=1e-6)
    # Si 工艺热光系数
    assert params.temperature_coefficient_dn_dT == pytest.approx(1.86e-4, rel=1e-3)
    # AMF 弯曲半径应大于 SiEPIC（AMF 工艺限制）
    siepic = get_pdk_model_params("siepic_ebeam")
    assert params.bend_radius_min_um > siepic.bend_radius_min_um


# =============================================================================
# 4. Ligentec SiN 模型参数（AN800 SiN 无源 PDK）
# =============================================================================


def test_ligentec_sic_model_params():
    """Ligentec AN800 SiN PDK 模型参数（无源 SiN，低损耗大弯曲半径）。

    来源: https://www.ligentec.com/
          Subbaraman 2013 (SiN dn/dT=2.45e-5 /K)
    """
    params = get_pdk_model_params("ligentec_sic")
    assert isinstance(params, PDKModelParameters)
    # neff_strip_1550=2.00（SiN @ 1550nm，低于 Si 的 2.4）
    assert params.neff_strip_1550 == pytest.approx(2.00, abs=1e-6)
    # propagation_loss=1.0 dB/cm（SiN 超低损耗，Ligentec 文档）
    assert params.propagation_loss_db_cm == pytest.approx(1.0, abs=1e-6)
    # bend_radius_min=100.0μm（SiN 弯曲半径大，因 neff 对比度低）
    assert params.bend_radius_min_um == pytest.approx(100.0, abs=1e-6)
    # modulator_vpi_l=0.0（Ligentec AN800 纯无源 PDK，无集成调制器）
    assert params.modulator_vpi_l_v_cm == pytest.approx(0.0, abs=1e-6)
    # pd_responsivity=0.0（Ligentec AN800 纯无源 PDK，无集成 PD）
    assert params.pd_responsivity_a_w == pytest.approx(0.0, abs=1e-6)
    # coupling_loss=1.5 dB（SiN GC 优于 SOI GC）
    assert params.coupling_loss_db == pytest.approx(1.5, abs=1e-6)
    # SiN 热光系数 2.45e-5 /K（Subbaraman 2013，比 Si 小一个量级）
    assert params.temperature_coefficient_dn_dT == pytest.approx(2.45e-5, rel=1e-3)
    # SiN 损耗应低于 SOI（SiN 超低损耗特性）
    siepic = get_pdk_model_params("siepic_ebeam")
    assert params.propagation_loss_db_cm < siepic.propagation_loss_db_cm
    # SiN 弯曲半径应远大于 SOI（neff 对比度低）
    assert params.bend_radius_min_um > siepic.bend_radius_min_um
    # SiN 热光系数应远小于 Si（~10x 差异）
    assert params.temperature_coefficient_dn_dT < siepic.temperature_coefficient_dn_dT / 5


# =============================================================================
# 5. 注册表完整性与 R03 错误处理
# =============================================================================


def test_pdk_model_params_registry_completeness():
    """注册表完整性: 应包含 4 个 PDK，list 函数返回排序后列表。"""
    expected = {"siepic_ebeam", "imec_isipp50g", "amf", "ligentec_sic"}
    assert set(PDK_MODEL_PARAMS_REGISTRY.keys()) == expected
    # list_available_pdk_model_params 返回排序后列表
    listed = list_available_pdk_model_params()
    assert listed == sorted(expected)
    assert len(listed) == 4


def test_get_pdk_model_params_unregistered_raises_keyerror():
    """R03 合规: 未注册 PDK 必须 raise KeyError，禁止 fall-back。"""
    with pytest.raises(KeyError, match="未注册"):
        get_pdk_model_params("nonexistent_pdk_xyz")


def test_pdk_model_params_immutable():
    """PDKModelParameters 为 frozen dataclass，禁止修改字段（R03 数据一致性）。"""
    params = get_pdk_model_params("siepic_ebeam")
    with pytest.raises((AttributeError, Exception)):
        params.neff_strip_1550 = 3.0  # type: ignore[misc]
