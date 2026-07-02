"""polaris-pdk 子模块测试。

测试覆盖:
- test_list_platforms: 4 平台（SOI/SiN/InP/LNOI），每平台 9 器件
- test_get_device: SOI grating_coupler insertion_loss_db=1.9
- test_get_device_not_found: 不存在的器件 raise RuntimeError（R03 禁止 fall-back）
- test_list_devices: 列出某平台所有器件
- test_export_gds: 用 polaris_core.make_circuit 创建 MZI，导出 GDSII，验证 loadable=True
- test_import_gds: 导入 GDSII，验证 n_structures/n_layers/bbox_um

来源:
- pytest 文档: https://docs.pytest.org/
- klayout Database API:
  https://www.klayout.org/downloads/master/doc-qt4/programming/database_api.html
- gdsfactory write_gds: https://gdsfactory.github.io/gdsfactory/api.html
- SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

# 让测试既能从已安装包导入，也能从源码树导入（CI/开发模式）
_SRC = str(Path(__file__).resolve().parents[1] / "src")
_CORE_SRC = str(Path(__file__).resolve().parents[2] / "core" / "src")
for _p in (_SRC, _CORE_SRC):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from polaris_core import make_circuit, make_device
from polaris_pdk import export_gds, get_device, import_gds, list_devices, list_platforms


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


def test_export_gds(tmp_path):
    """用 polaris_core.make_circuit 创建 MZI，导出 GDSII，验证 loadable=True。"""
    # 构建 MZI 电路：2 光栅耦合器 + 2 Y 分支 + 1 波导
    gc1 = make_device("gc1", "grating_coupler", 20, 12,
                      ports=[("wg", 0, 6, "west")],
                      params={"insertion_loss_db": 1.9},
                      process_node="220nm SOI")
    gc2 = make_device("gc2", "grating_coupler", 20, 12,
                      ports=[("wg", 20, 6, "east")],
                      params={"insertion_loss_db": 1.9},
                      process_node="220nm SOI")
    yb1 = make_device("yb1", "y_branch", 10, 2,
                      ports=[("in", 0, 1, "west"),
                             ("out1", 10, 0.5, "east"),
                             ("out2", 10, -0.5, "east")],
                      process_node="220nm SOI")
    yb2 = make_device("yb2", "y_branch", 10, 2,
                      ports=[("in", 0, 0.5, "west"),
                             ("out1", 10, 1, "east"),
                             ("out2", 10, -1, "east")],
                      process_node="220nm SOI")
    wg = make_device("wg1", "strip_waveguide", 50, 0.5,
                     ports=[("in", 0, 0, "west"), ("out", 50, 0, "east")],
                     process_node="220nm SOI")
    circuit = make_circuit(
        "MZI",
        devices=[gc1, gc2, yb1, yb2, wg],
        connections=[
            ["gc1", "wg", "yb1", "in"],
            ["yb1", "out1", "wg", "in"],
            ["wg", "out", "yb2", "in"],
            ["yb2", "out1", "gc2", "wg"],
        ],
        canvas_w=200.0,
        canvas_h=50.0,
        process_node="220nm SOI",
    )
    out_path = str(tmp_path / "mzi.gds")
    result = export_gds(circuit, out_path)
    assert isinstance(result, dict)
    assert result["path"] == str(Path(out_path).resolve())
    assert result["file_size_bytes"] > 0
    assert result["n_structures"] >= 2  # 顶层 + 至少 1 子 cell
    assert result["n_layers"] >= 1
    assert result["loadable"] is True
    # 文件确实存在
    assert Path(out_path).exists()
    # JSON 可序列化
    json.dumps(result)


def test_import_gds(tmp_path):
    """导入 GDSII，验证 n_structures/n_layers/layers/bbox_um 字段。"""
    # 先导出一个 GDSII 再导入（端到端往返）
    dev = make_device("d1", "strip_waveguide", 10, 0.5,
                      ports=[("in", 0, 0, "west"), ("out", 10, 0, "east")])
    circuit = make_circuit("TestCircuit", devices=[dev], connections=[],
                           canvas_w=100.0, canvas_h=20.0)
    gds_path = str(tmp_path / "test.gds")
    export_gds(circuit, gds_path)

    result = import_gds(gds_path)
    assert isinstance(result, dict)
    assert result["n_structures"] >= 1
    assert result["n_layers"] >= 1
    assert isinstance(result["layers"], list)
    assert len(result["layers"]) == result["n_layers"]
    for layer in result["layers"]:
        assert "gds_layer" in layer
        assert "gds_datatype" in layer
        assert "polaris_name" in layer
        assert "n_shapes" in layer
    assert "bbox_um" in result
    for k in ("xmin", "ymin", "xmax", "ymax"):
        assert k in result["bbox_um"]
    # WG 层 (1, 0) 应存在
    wg_layers = [l for l in result["layers"] if l["gds_layer"] == 1]
    assert len(wg_layers) >= 1
    # JSON 可序列化
    json.dumps(result)


def test_import_gds_not_found():
    """导入不存在的文件 raise FileNotFoundError（R03 禁止 fall-back）。"""
    with pytest.raises(FileNotFoundError):
        import_gds("/nonexistent/path/file.gds")
