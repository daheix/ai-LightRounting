"""polaris-gdsio 子模块测试。

测试覆盖（≥3 个 pytest，R03 禁止 fall-back）:
- test_export_gds: 导出 GDSII，验证 loadable=True / file_size>0 / n_structures≥2
- test_import_gds: 导入 GDSII，验证 n_structures>0 / layers / bbox_um
- test_export_invalid_circuit: 无效 circuit raise RuntimeError
- test_import_gds_not_found: 不存在文件 raise FileNotFoundError

来源（R02 学术诚信）:
- pytest 文档: https://docs.pytest.org/
- klayout Database API:
  https://www.klayout.org/downloads/master/doc-qt4/programming/database_api.html
- gdsfactory write_gds: https://gdsfactory.github.io/gdsfactory/api.html
- GDSII 格式规范: https://en.wikipedia.org/wiki/GDS_File
- gdsfactory PDK import 层映射:
  https://sequoiap.github.io/gdsfactory/notebooks/09_pdk_import.html
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

from polaris_gdsio import export_gds, import_gds


def _make_simple_circuit() -> dict:
    """构造一个简单的 circuit dict（不依赖 polaris_core，保持 gdsio 独立）。

    单器件 strip_waveguide：width=0.5μm height=0.22μm。
    """
    return {
        "name": "test_circuit",
        "devices": [
            {
                "name": "wg1",
                "device_type": "strip_waveguide",
                "width_um": 0.5,
                "height_um": 0.22,
                "ports": [("in", 0.0, 0.0, "west"),
                          ("out", 10.0, 0.0, "east")],
                "params": {"loss_db_cm": 2.0},
            },
        ],
        "connections": [],
        "canvas_w": 100.0,
        "canvas_h": 50.0,
    }


def test_export_gds(tmp_path):
    """导出 GDSII，验证 loadable=True / file_size>0 / n_structures≥2。"""
    circuit = _make_simple_circuit()
    out_path = str(tmp_path / "test.gds")
    result = export_gds(circuit, out_path)
    assert isinstance(result, dict)
    assert result["path"] == str(Path(out_path).resolve())
    assert result["file_size_bytes"] > 0
    # 顶层 cell + 1 个器件子 cell = 2 个 structure
    assert result["n_structures"] >= 2
    assert result["n_layers"] >= 1
    assert result["loadable"] is True
    # 文件确实存在
    assert Path(out_path).exists()
    # JSON 可序列化（稳定 API 原则）
    json.dumps(result)


def test_export_gds_multi_device(tmp_path):
    """多器件电路导出，n_structures = 顶层 + 每器件子 cell。"""
    circuit = {
        "name": "mzi_top",
        "devices": [
            {"name": "gc1", "device_type": "grating_coupler",
             "width_um": 20.0, "height_um": 12.0, "ports": [], "params": {}},
            {"name": "yb1", "device_type": "y_branch",
             "width_um": 10.0, "height_um": 2.0, "ports": [], "params": {}},
            {"name": "wg1", "device_type": "strip_waveguide",
             "width_um": 50.0, "height_um": 0.5, "ports": [], "params": {}},
        ],
        "connections": [],
        "canvas_w": 200.0,
        "canvas_h": 50.0,
    }
    out_path = str(tmp_path / "mzi.gds")
    result = export_gds(circuit, out_path)
    # 1 顶层 + 3 器件子 cell = 4
    assert result["n_structures"] == 4
    assert result["loadable"] is True


def test_import_gds(tmp_path):
    """导入 GDSII，验证 n_structures>0 / layers / bbox_um 字段。"""
    circuit = _make_simple_circuit()
    gds_path = str(tmp_path / "imp.gds")
    export_gds(circuit, gds_path)

    result = import_gds(gds_path)
    assert isinstance(result, dict)
    assert result["n_structures"] > 0
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
    assert wg_layers[0]["polaris_name"] == "WG"
    # JSON 可序列化
    json.dumps(result)


def test_export_invalid_circuit(tmp_path):
    """无效 circuit raise RuntimeError（R03 禁止 fall-back）。"""
    # 非 dict
    with pytest.raises(RuntimeError):
        export_gds("not_a_dict", str(tmp_path / "x.gds"))  # type: ignore[arg-type]
    # 缺少 name 字段
    with pytest.raises(RuntimeError):
        export_gds({"devices": []}, str(tmp_path / "x.gds"))
    # 缺少 devices 字段
    with pytest.raises(RuntimeError):
        export_gds({"name": "t"}, str(tmp_path / "x.gds"))
    # 器件缺少 width_um
    with pytest.raises(RuntimeError):
        export_gds(
            {"name": "t",
             "devices": [{"name": "d", "device_type": "wg",
                          "height_um": 0.22}]},
            str(tmp_path / "x.gds"),
        )


def test_import_gds_not_found():
    """导入不存在的文件 raise FileNotFoundError（R03 禁止 fall-back）。"""
    with pytest.raises(FileNotFoundError):
        import_gds("/nonexistent/path/file.gds")
