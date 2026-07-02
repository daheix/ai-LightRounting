"""polaris-pdk 子模块测试（v5.1：仅器件库查询）。

v5.1 起 GDSII 导入导出测试已迁移到 polaris-gdsio/tests/test_gdsio.py。
本文件只测试器件目录查询。

测试覆盖:
- test_list_platforms: 4 平台（SOI/SiN/InP/LNOI），每平台 9 器件
- test_get_device: SOI grating_coupler insertion_loss_db=1.9
- test_get_device_not_found: 不存在的器件 raise RuntimeError（R03 禁止 fall-back）
- test_list_devices: 列出某平台所有器件

来源（R02 学术诚信）:
- pytest 文档: https://docs.pytest.org/
- SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- Ligentec ANR PDK: https://www.ligentec.com/
- Pattern Project / JEPPIX InP: https://www.jeppix.eu/
- HyperLight LNOI PDK: https://hyperlightphotonics.com/
- Soares et al., Appl. Sci. 2019, 9(8), 1588:
  https://doi.org/10.3390/app9081588
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

from polaris_pdk import get_device, list_devices, list_platforms


def test_list_platforms():
    """4 平台（SOI/SiN/InP/LNOI），每平台含必要字段且 device_count=9。"""
    ps = list_platforms()
    assert isinstance(ps, list)
    assert len(ps) == 4
    names = [p["platform"] for p in ps]
    assert names == ["SOI", "SiN", "InP", "LNOI"]
    for p in ps:
        assert "foundry" in p
        assert "process_node" in p
        assert "device_count" in p
        assert "device_names" in p
        assert p["device_count"] == len(p["device_names"])
        assert p["device_count"] == 9  # 每平台 9 器件，共 36
    # 验证 foundry 标注（来源 PDK）
    foundry_map = {p["platform"]: p["foundry"] for p in ps}
    assert "SiEPIC" in foundry_map["SOI"]
    assert "Ligentec" in foundry_map["SiN"]
    assert "Pattern Project" in foundry_map["InP"]
    assert "HyperLight" in foundry_map["LNOI"]
    # JSON 可序列化（稳定 API 原则）
    json.dumps(ps)


def test_get_device():
    """SOI grating_coupler 返回 dict，insertion_loss_db=1.9，含来源标注。"""
    d = get_device("SOI", "grating_coupler")
    assert isinstance(d, dict)
    assert d["platform"] == "SOI"
    assert d["device_type"] == "grating_coupler"
    # 关键参数：三星 300mm 平台峰值耦合损耗 1.9dB
    assert d["params"]["insertion_loss_db"] == 1.9
    # 来源标注（R02 学术诚信）
    assert "pdk_reference" in d["params"]
    assert d["params"]["pdk_reference"] == "SiEPIC_EBeam_PDK"
    assert "source" in d
    assert d["source"]["url"]  # 非空 URL
    # 端口与包围盒
    assert isinstance(d["ports"], list)
    assert len(d["ports"]) >= 1
    assert "bbox_um" in d
    # JSON 可序列化
    json.dumps(d)


def test_get_device_not_found():
    """器件未找到 raise RuntimeError（R03 禁止 fall-back，不返回假数据）。"""
    with pytest.raises(RuntimeError):
        get_device("SOI", "nonexistent_device")
    # 平台不存在也 raise
    with pytest.raises(RuntimeError):
        get_device("UnknownPlatform", "grating_coupler")


def test_list_devices():
    """list_devices 列出某平台所有器件，返回 dict 列表。"""
    devs = list_devices("SiN")
    assert isinstance(devs, list)
    assert len(devs) == 9
    for d in devs:
        assert d["platform"] == "SiN"
        assert "pdk_reference" in d["params"]
        assert d["params"]["pdk_reference"] == "Ligentec_ANR_PDK"
    # 验证深拷贝独立性（修改返回值不影响内部数据）
    devs[0]["params"]["loss_db_cm"] = 999.0
    devs2 = list_devices("SiN")
    assert devs2[0]["params"]["loss_db_cm"] != 999.0


def test_pdk_no_gdsio_attr():
    """v5.1: polaris-pdk 不再导出 export_gds/import_gds（已拆到 polaris-gdsio）。"""
    import polaris_pdk
    assert not hasattr(polaris_pdk, "export_gds")
    assert not hasattr(polaris_pdk, "import_gds")
    # __all__ 只含器件库查询 API
    assert set(polaris_pdk.__all__) == {
        "list_platforms", "get_device", "list_devices", "__version__",
    }
