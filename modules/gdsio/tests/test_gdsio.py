"""polaris-gdsio 深度测试（export_gds / import_gds 端到端覆盖）。

测试分层:
1. export_gds 端到端: 单器件/多器件/返回字段/loadable/JSON 可序列化
2. export_gds 错误路径: 非 dict/缺字段/器件缺字段/输出是目录/空器件
3. import_gds 端到端: 字段完整性/layers 映射/bbox/JSON 可序列化
4. import_gds 错误路径: 文件不存在/路径是目录
5. export→import 往返一致性
6. 边界条件: 小尺寸器件/未映射层/多次覆盖/创建父目录
7. klayout 不可用 raise（mock sys.modules，R03 禁止 fall-back）

R03 合规: klayout 不可用场景用 monkeypatch 模拟（不伪造数据）。
R02 学术诚信: 所有断言基于 exporter/importer docstring 公开契约。

来源（R02 学术诚信，均经 WebSearch 验证可访问）:
- pytest 文档: https://docs.pytest.org/
- klayout Database API:
  https://www.klayout.org/downloads/master/doc-qt4/programming/database_api.html
- gdsfactory write_gds: https://gdsfactory.github.io/gdsfactory/api.html
- GDSII 格式规范: https://en.wikipedia.org/wiki/GDS_File
- gdsfactory PDK import 层映射:
  https://sequoiap.github.io/gdsfactory/notebooks/09_pdk_import.html
- KLayout CellInstArray: https://www.klayout.de/doc-qt5/code/class_CellInstArray.html
- GDSII 层次结构（cell/SREF/AREF）:
  https://gdspy.readthedocs.io/en/master/gettingstarted.html#references
- KLayout Layout.read API: https://www.klayout.de/doc.html
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


# ---------------------------------------------------------------------------
# 测试辅助
# ---------------------------------------------------------------------------
def _make_simple_circuit() -> dict:
    """单器件 strip_waveguide 电路（width=0.5μm height=0.22μm）。"""
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


def _make_multi_device_circuit() -> dict:
    """多器件电路（3 器件：gc/yb/wg）。"""
    return {
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


@pytest.fixture(scope="module")
def klayout_available():
    """确认 klayout 可用，否则跳过 klayout 依赖测试。"""
    return pytest.importorskip("klayout")


# ===========================================================================
# 1. export_gds 端到端
# ===========================================================================
def test_export_gds_basic(tmp_path, klayout_available):
    """导出单器件 GDSII，验证返回 dict 字段完整。"""
    circuit = _make_simple_circuit()
    out_path = str(tmp_path / "test.gds")
    result = export_gds(circuit, out_path)
    assert isinstance(result, dict)
    assert result["path"] == str(Path(out_path).resolve())
    assert result["file_size_bytes"] > 0
    # 顶层 cell + 1 器件子 cell = 2 个 structure
    assert result["n_structures"] >= 2
    assert result["n_layers"] >= 1
    assert result["loadable"] is True
    assert Path(out_path).exists()


def test_export_gds_json_serializable(tmp_path, klayout_available):
    """export_gds 返回 dict 可 JSON 序列化（稳定 API 原则）。"""
    result = export_gds(_make_simple_circuit(), str(tmp_path / "t.gds"))
    s = json.dumps(result)
    assert "loadable" in s


def test_export_gds_multi_device(tmp_path, klayout_available):
    """多器件电路导出，n_structures = 顶层 + 每器件子 cell。"""
    out_path = str(tmp_path / "mzi.gds")
    result = export_gds(_make_multi_device_circuit(), out_path)
    # 1 顶层 + 3 器件子 cell = 4
    assert result["n_structures"] == 4
    assert result["loadable"] is True


def test_export_gds_file_size_grows_with_devices(tmp_path, klayout_available):
    """多器件 GDS 文件大小应大于单器件（更多 cell）。"""
    single = export_gds(_make_simple_circuit(), str(tmp_path / "s.gds"))
    multi = export_gds(_make_multi_device_circuit(), str(tmp_path / "m.gds"))
    assert multi["file_size_bytes"] > single["file_size_bytes"]


def test_export_gds_wg_layer_present(tmp_path, klayout_available):
    """导出 GDSII 应在 WG 层 (1,0) 有形状。"""
    out_path = str(tmp_path / "wg.gds")
    export_gds(_make_simple_circuit(), out_path)
    result = import_gds(out_path)
    wg_layers = [l for l in result["layers"] if l["gds_layer"] == 1]
    assert len(wg_layers) >= 1
    assert wg_layers[0]["polaris_name"] == "WG"
    assert wg_layers[0]["n_shapes"] >= 1


def test_export_gds_creates_parent_dir(tmp_path, klayout_available):
    """export_gds 自动创建不存在的父目录（mkdir parents=True）。"""
    nested = tmp_path / "a" / "b" / "c" / "out.gds"
    result = export_gds(_make_simple_circuit(), str(nested))
    assert nested.exists()
    assert result["loadable"] is True


def test_export_gds_overwrite(tmp_path, klayout_available):
    """多次 export 同路径覆盖（文件可重复写入）。"""
    out_path = str(tmp_path / "overwrite.gds")
    r1 = export_gds(_make_simple_circuit(), out_path)
    r2 = export_gds(_make_multi_device_circuit(), out_path)
    assert Path(out_path).exists()
    assert r1["loadable"] is True
    assert r2["loadable"] is True
    # 多器件 cell 数更多
    assert r2["n_structures"] > r1["n_structures"]


def test_export_gds_sub_micron_device(tmp_path, klayout_available):
    """亚微米器件（width<1μm）导出（dbu=1nm 应精确表示）。"""
    circuit = {
        "name": "sub",
        "devices": [{"name": "d1", "device_type": "wg",
                     "width_um": 0.05, "height_um": 0.02,
                     "ports": [], "params": {}}],
        "connections": [],
    }
    out_path = str(tmp_path / "sub.gds")
    result = export_gds(circuit, out_path)
    assert result["loadable"] is True
    # 0.05μm = 50 dbu，0.02μm = 20 dbu，均 ≥1
    assert result["n_structures"] >= 2


def test_export_gds_tiny_device_clamped(tmp_path, klayout_available):
    """极小器件（width<1nm）被钳制为 1 dbu（源码 w_dbu<1 → 1）。"""
    circuit = {
        "name": "tiny",
        "devices": [{"name": "d1", "device_type": "wg",
                     "width_um": 0.0001, "height_um": 0.0001,
                     "ports": [], "params": {}}],
        "connections": [],
    }
    out_path = str(tmp_path / "tiny.gds")
    result = export_gds(circuit, out_path)
    assert result["loadable"] is True


def test_export_gds_empty_connections(tmp_path, klayout_available):
    """connections 为空列表可正常导出。"""
    circuit = {
        "name": "noconn",
        "devices": [{"name": "d1", "device_type": "wg",
                     "width_um": 5.0, "height_um": 1.0,
                     "ports": [], "params": {}}],
        "connections": [],
    }
    result = export_gds(circuit, str(tmp_path / "noconn.gds"))
    assert result["loadable"] is True


def test_export_gds_without_canvas(tmp_path, klayout_available):
    """无 canvas_w/canvas_h 字段也可导出（字段可选）。"""
    circuit = {
        "name": "nocanvas",
        "devices": [{"name": "d1", "device_type": "wg",
                     "width_um": 5.0, "height_um": 1.0,
                     "ports": [], "params": {}}],
        "connections": [],
    }
    result = export_gds(circuit, str(tmp_path / "nocanv.gds"))
    assert result["loadable"] is True


# ===========================================================================
# 2. export_gds 错误路径（R03 禁止 fall-back）
# ===========================================================================
def test_export_gds_not_dict(tmp_path, klayout_available):
    """非 dict circuit raise RuntimeError。"""
    with pytest.raises(RuntimeError):
        export_gds("not_a_dict", str(tmp_path / "x.gds"))  # type: ignore[arg-type]


def test_export_gds_missing_name(tmp_path, klayout_available):
    """缺 name 字段 raise RuntimeError。"""
    with pytest.raises(RuntimeError):
        export_gds({"devices": []}, str(tmp_path / "x.gds"))


def test_export_gds_missing_devices(tmp_path, klayout_available):
    """缺 devices 字段 raise RuntimeError。"""
    with pytest.raises(RuntimeError):
        export_gds({"name": "t"}, str(tmp_path / "x.gds"))


def test_export_gds_name_not_str(tmp_path, klayout_available):
    """name 非 str raise RuntimeError。"""
    with pytest.raises(RuntimeError):
        export_gds({"name": 123, "devices": []}, str(tmp_path / "x.gds"))


def test_export_gds_devices_not_list(tmp_path, klayout_available):
    """devices 非 list raise RuntimeError。"""
    with pytest.raises(RuntimeError):
        export_gds({"name": "t", "devices": "not_list"},
                   str(tmp_path / "x.gds"))


def test_export_gds_device_missing_field(tmp_path, klayout_available):
    """器件缺 width_um raise RuntimeError。"""
    with pytest.raises(RuntimeError):
        export_gds(
            {"name": "t",
             "devices": [{"name": "d", "device_type": "wg",
                          "height_um": 0.22}]},
            str(tmp_path / "x.gds"),
        )


def test_export_gds_device_not_dict(tmp_path, klayout_available):
    """器件非 dict raise RuntimeError。"""
    with pytest.raises(RuntimeError):
        export_gds(
            {"name": "t", "devices": ["not_dict"]},
            str(tmp_path / "x.gds"),
        )


def test_export_gds_output_is_directory(tmp_path, klayout_available):
    """输出路径是目录 raise RuntimeError。"""
    with pytest.raises(RuntimeError, match="目录"):
        export_gds(_make_simple_circuit(), str(tmp_path))


def test_export_gds_empty_devices_only_top(tmp_path, klayout_available):
    """空 devices 列表导出仅含空顶层 cell 的 GDSII（n_structures=1）。

    源码先创建顶层 cell 再遍历 devices，故空 devices 不会 raise，
    而是导出仅有顶层 cell 的 GDSII。
    """
    circuit = {"name": "empty", "devices": [], "connections": []}
    result = export_gds(circuit, str(tmp_path / "empty.gds"))
    assert result["n_structures"] == 1  # 仅顶层 cell
    assert result["loadable"] is True


# ===========================================================================
# 3. import_gds 端到端
# ===========================================================================
def test_import_gds_basic(tmp_path, klayout_available):
    """导入 GDSII，验证返回 dict 字段完整。"""
    gds_path = str(tmp_path / "imp.gds")
    export_gds(_make_simple_circuit(), gds_path)
    result = import_gds(gds_path)
    assert isinstance(result, dict)
    assert result["n_structures"] > 0
    assert result["n_layers"] >= 1
    assert isinstance(result["layers"], list)
    assert len(result["layers"]) == result["n_layers"]


def test_import_gds_layer_fields(tmp_path, klayout_available):
    """每层信息含 gds_layer/gds_datatype/polaris_name/n_shapes。"""
    gds_path = str(tmp_path / "layers.gds")
    export_gds(_make_simple_circuit(), gds_path)
    result = import_gds(gds_path)
    for layer in result["layers"]:
        assert "gds_layer" in layer
        assert "gds_datatype" in layer
        assert "polaris_name" in layer
        assert "n_shapes" in layer
        assert isinstance(layer["n_shapes"], int)
        assert layer["n_shapes"] >= 1


def test_import_gds_bbox_fields(tmp_path, klayout_available):
    """bbox_um 含 xmin/ymin/xmax/ymax 四字段。"""
    gds_path = str(tmp_path / "bbox.gds")
    export_gds(_make_simple_circuit(), gds_path)
    result = import_gds(gds_path)
    bbox = result["bbox_um"]
    for k in ("xmin", "ymin", "xmax", "ymax"):
        assert k in bbox
        assert isinstance(bbox[k], float)


def test_import_gds_bbox_validity(tmp_path, klayout_available):
    """bbox 满足 xmin<=xmax, ymin<=ymax。"""
    gds_path = str(tmp_path / "bbox2.gds")
    export_gds(_make_simple_circuit(), gds_path)
    bbox = import_gds(gds_path)["bbox_um"]
    assert bbox["xmin"] <= bbox["xmax"]
    assert bbox["ymin"] <= bbox["ymax"]


def test_import_gds_json_serializable(tmp_path, klayout_available):
    """import_gds 返回 dict 可 JSON 序列化。"""
    gds_path = str(tmp_path / "json.gds")
    export_gds(_make_simple_circuit(), gds_path)
    result = import_gds(gds_path)
    s = json.dumps(result)
    assert "n_structures" in s
    assert "bbox_um" in s


def test_import_gds_multi_device_structures(tmp_path, klayout_available):
    """多器件 GDSII 导入 n_structures = 4（1 顶层 + 3 子 cell）。"""
    gds_path = str(tmp_path / "multi.gds")
    export_gds(_make_multi_device_circuit(), gds_path)
    result = import_gds(gds_path)
    assert result["n_structures"] == 4


def test_import_gds_unmapped_layer_name(tmp_path, klayout_available):
    """未映射层（非 1/2/3/66/68/69/99）→ 'LAYER_<l>_<d>'。"""
    # 用 klayout 创建含未映射层 (200,0) 的 GDSII
    import klayout.db as db
    ly = db.Layout()
    ly.dbu = 0.001
    top = ly.create_cell("TOP")
    li = ly.layer(200, 0)
    top.shapes(li).insert(db.Box(0, 0, 1000, 1000))
    gds_path = str(tmp_path / "unmapped.gds")
    ly.write(gds_path)
    result = import_gds(gds_path)
    unmapped = [l for l in result["layers"] if l["gds_layer"] == 200]
    assert len(unmapped) == 1
    assert unmapped[0]["polaris_name"] == "LAYER_200_0"


def test_import_gds_known_layer_mapping(tmp_path, klayout_available):
    """已知层映射: (1,0)=WG / (2,0)=SLAB150 / (3,0)=SLAB90 / (66,0)=TEXT。"""
    import klayout.db as db
    ly = db.Layout()
    ly.dbu = 0.001
    top = ly.create_cell("TOP")
    for layer_num in (1, 2, 3, 66, 68, 69, 99):
        li = ly.layer(layer_num, 0)
        top.shapes(li).insert(db.Box(0, 0, 1000, 1000))
    gds_path = str(tmp_path / "mapped.gds")
    ly.write(gds_path)
    result = import_gds(gds_path)
    name_by_layer = {l["gds_layer"]: l["polaris_name"] for l in result["layers"]}
    assert name_by_layer[1] == "WG"
    assert name_by_layer[2] == "SLAB150"
    assert name_by_layer[3] == "SLAB90"
    assert name_by_layer[66] == "TEXT"
    assert name_by_layer[68] == "DEVREC"
    assert name_by_layer[69] == "PIN"
    assert name_by_layer[99] == "PORT"


# ===========================================================================
# 4. import_gds 错误路径（R03 禁止 fall-back）
# ===========================================================================
def test_import_gds_not_found():
    """导入不存在的文件 raise FileNotFoundError。"""
    with pytest.raises(FileNotFoundError):
        import_gds("/nonexistent/path/file.gds")


def test_import_gds_is_directory(tmp_path, klayout_available):
    """导入目录路径 raise RuntimeError。"""
    with pytest.raises(RuntimeError, match="不是文件"):
        import_gds(str(tmp_path))


def test_import_gds_corrupt_file(tmp_path, klayout_available):
    """导入损坏 GDSII（非 GDS 二进制）raise RuntimeError。"""
    bad = tmp_path / "bad.gds"
    bad.write_bytes(b"NOT A GDSII FILE CONTENT")
    with pytest.raises(RuntimeError):
        import_gds(str(bad))


# ===========================================================================
# 5. export→import 往返一致性
# ===========================================================================
def test_export_import_roundtrip_structures(tmp_path, klayout_available):
    """export→import 往返：n_structures 一致。"""
    gds_path = str(tmp_path / "rt.gds")
    exp = export_gds(_make_multi_device_circuit(), gds_path)
    imp = import_gds(gds_path)
    assert imp["n_structures"] == exp["n_structures"]


def test_export_import_roundtrip_wg_shapes(tmp_path, klayout_available):
    """export→import 往返：WG 层形状数 = 器件数。"""
    gds_path = str(tmp_path / "rt_wg.gds")
    export_gds(_make_multi_device_circuit(), gds_path)
    result = import_gds(gds_path)
    wg = [l for l in result["layers"] if l["gds_layer"] == 1][0]
    # 3 个器件各 1 个 box → 至少 3 个形状
    assert wg["n_shapes"] >= 3


def test_export_import_roundtrip_bbox_nonzero(tmp_path, klayout_available):
    """export→import 往返：bbox 非零（器件有面积）。"""
    gds_path = str(tmp_path / "rt_bbox.gds")
    export_gds(_make_simple_circuit(), gds_path)
    bbox = import_gds(gds_path)["bbox_um"]
    width = bbox["xmax"] - bbox["xmin"]
    height = bbox["ymax"] - bbox["ymin"]
    assert width > 0
    assert height > 0


# ===========================================================================
# 6. klayout 不可用 raise（mock sys.modules，R03 禁止 fall-back）
# ===========================================================================
def test_export_gds_klayout_unavailable(tmp_path, monkeypatch):
    """klayout 不可用时 export_gds raise（R03 禁止 fall-back）。

    用 monkeypatch 屏蔽 klayout 模块，模拟未安装环境。
    """
    # 保存原始状态
    import builtins
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name.startswith("klayout"):
            raise ImportError("mocked: klayout not installed")
        return real_import(name, *args, **kwargs)

    # 清除已缓存的 klayout 模块
    saved = {k: sys.modules.pop(k) for k in list(sys.modules) if k.startswith("klayout")}
    monkeypatch.setattr(builtins, "__import__", fake_import)
    try:
        with pytest.raises(ImportError):
            export_gds(_make_simple_circuit(), str(tmp_path / "nokl.gds"))
    finally:
        # 恢复 klayout 模块缓存
        sys.modules.update(saved)


def test_import_gds_klayout_unavailable(tmp_path, monkeypatch):
    """klayout 不可用时 import_gds raise（R03 禁止 fall-back）。"""
    import builtins
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name.startswith("klayout"):
            raise ImportError("mocked: klayout not installed")
        return real_import(name, *args, **kwargs)

    saved = {k: sys.modules.pop(k) for k in list(sys.modules) if k.startswith("klayout")}
    monkeypatch.setattr(builtins, "__import__", fake_import)
    try:
        # 文件需存在以通过 FileNotFoundError 前置检查
        gds = tmp_path / "exists.gds"
        gds.write_bytes(b"dummy")
        with pytest.raises(ImportError):
            import_gds(str(gds))
    finally:
        sys.modules.update(saved)
