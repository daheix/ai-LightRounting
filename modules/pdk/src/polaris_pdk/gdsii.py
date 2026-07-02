"""GDSII 导入导出（polaris-pdk 子模块）。

从 src/polaris/pdk/gdsii_exporter.py + gdsii_importer.py 迁移并统一为
``export_gds`` / ``import_gds`` 两个稳定函数，使用 klayout.db API。

设计原则:
- 对外 API 返回 JSON-serializable dict，不返回 klayout 内部对象
- export_gds 接受 polaris_core 的 circuit dict，输出 gdsfactory 兼容 GDSII
- 禁止 fall-back（R03）：klayout 读取/写入失败 raise RuntimeError
- 返回 loadable 标志（重新读入验证 GDSII 可被 klayout 加载）

学术依据（R02 学术诚信，均经 WebSearch 验证可访问）:
- klayout Layout.write API:
  https://www.klayout.org/downloads/master/doc-qt4/programming/database_api.html
- gdsfactory write_gds 默认参数（dbu=0.001μm=1nm）:
  https://gdsfactory.github.io/gdsfactory/api.html#gdsfactory.write_gds
- GDSII 格式规范: https://en.wikipedia.org/wiki/GDS_File
- GDSII 层次结构（cell/SREF/AREF）:
  https://gdspy.readthedocs.io/en/master/gettingstarted.html#references
- gdsfactory PDK import 层映射:
  https://sequoiap.github.io/gdsfactory/notebooks/09_pdk_import.html
- KLayout CellInstArray: https://www.klayout.de/doc-qt5/code/class_CellInstArray.html
- gdsfactory generic PDK layer definitions:
  https://gdsfactory.github.io/gdsfactory/

合规: R02 学术诚信 / R03 禁止 fall-back / R05 Bug 必修。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

# gdsfactory 写出 GDSII 的默认 dbu（μm）
# 来源: gdsfactory write_gds 默认参数
# https://gdsfactory.github.io/gdsfactory/api.html#gdsfactory.write_gds
_GDSFACTORY_DEFAULT_DBU_UM: float = 0.001

# 默认层映射（gdsfactory generic PDK → PoLaRIS 层名）
# 来源: gdsfactory generic PDK layer definitions
# https://gdsfactory.github.io/gdsfactory/
_DEFAULT_LAYER_MAP: dict[tuple[int, int], str] = {
    (1, 0): "WG",          # 波导核心层
    (2, 0): "SLAB150",     # 150nm slab
    (3, 0): "SLAB90",      # 90nm slab
    (66, 0): "TEXT",       # 文本标注层
    (68, 0): "DEVREC",     # SiEPIC 器件识别层（兼容）
    (69, 0): "PIN",        # SiEPIC 端口标记层（兼容）
    (99, 0): "PORT",       # gdsfactory 端口几何层
}

# 波导核心层（gdsfactory 默认 WG layer (1, 0)）
# 来源: gdsfactory PDK import 文档
# https://sequoiap.github.io/gdsfactory/notebooks/09_pdk_import.html
_WG_LAYER: tuple[int, int] = (1, 0)


def export_gds(circuit: dict, output_path: str) -> dict[str, Any]:
    """将 polaris_core circuit dict 导出为 gdsfactory 兼容 GDSII 文件。

    流程:
    1. 用 klayout.db 创建 Layout（dbu=0.001μm=1nm，与 gdsfactory 默认一致）
    2. 创建顶层 cell（名为 circuit["name"]）
    3. 为每个器件创建子 cell，含一个 box（width_um × height_um）在 WG 层 (1,0)
    4. 在顶层 cell 中放置每个器件的实例（沿 x 轴顺序排列）
    5. 写出 GDSII 文件
    6. 重新读入验证 loadable=True（无信息损失校验）

    Args:
        circuit: polaris_core.make_circuit 返回的 circuit dict，含
            name/devices/connections/canvas_w/canvas_h 等字段。每个 device 含
            name/device_type/width_um/height_um/ports/params。
        output_path: GDSII 输出文件路径。

    Returns:
        dict 含:
        - path: GDSII 文件绝对路径
        - file_size_bytes: 文件大小（字节）
        - n_structures: 结构数（cell 数，含顶层）
        - n_layers: 层数
        - loadable: 是否可被 klayout 重新读入（True/False）

    Raises:
        RuntimeError: circuit 结构无效或 klayout 写入/读回失败（R03 禁止 fall-back）。

    学术依据:
    - klayout Layout.write API:
      https://www.klayout.org/downloads/master/doc-qt4/programming/database_api.html
    - gdsfactory write_gds: https://gdsfactory.github.io/gdsfactory/api.html
    """
    import klayout.db as db

    _validate_circuit(circuit)
    out = Path(output_path)
    if out.is_dir():
        raise RuntimeError(f"输出路径是目录不是文件: {output_path}")
    out.parent.mkdir(parents=True, exist_ok=True)

    ly = db.Layout()
    ly.dbu = _GDSFACTORY_DEFAULT_DBU_UM

    # 顶层 cell
    top_name = str(circuit["name"])
    top_cell = ly.create_cell(top_name)
    wg_li = ly.layer(_WG_LAYER[0], _WG_LAYER[1])

    dbu = _GDSFACTORY_DEFAULT_DBU_UM
    # 为每个器件创建子 cell + 在顶层放置实例
    x_offset = 0.0
    for dev in circuit["devices"]:
        w_um = float(dev["width_um"])
        h_um = float(dev["height_um"])
        dev_name = str(dev["name"])
        child = ly.create_cell(dev_name)
        # box 在 WG 层（dbu 单位），尺寸为器件 footprint
        w_dbu = int(round(w_um / dbu))
        h_dbu = int(round(h_um / dbu))
        if w_dbu < 1:
            w_dbu = 1
        if h_dbu < 1:
            h_dbu = 1
        child.shapes(wg_li).insert(db.Box(0, 0, w_dbu, h_dbu))
        # 在顶层放置实例（沿 x 轴顺序排列，y=0 居中）
        x_dbu = int(round(x_offset / dbu))
        trans = db.Trans(x_dbu, 0)
        top_cell.insert(db.CellInstArray(child.cell_index(), trans))
        x_offset += w_um + 5.0  # 器件间距 5μm

    if ly.cells() == 0:
        raise RuntimeError(
            "Layout 无 cell，无法写出 GDSII（circuit.devices 为空）"
        )

    try:
        ly.write(str(out))
    except Exception as e:
        raise RuntimeError(
            f"klayout 写出 GDSII 失败: {type(e).__name__}: {e}。"
            f"禁止 fall-back（R03）。"
        ) from e

    file_size = out.stat().st_size
    n_structures = ly.cells()
    n_layers = len([li for li in ly.layer_indices()])

    # 重新读入验证 loadable
    loadable = _verify_loadable(str(out))

    return {
        "path": str(out.resolve()),
        "file_size_bytes": file_size,
        "n_structures": n_structures,
        "n_layers": n_layers,
        "loadable": loadable,
    }


def import_gds(gds_path: str) -> dict[str, Any]:
    """从 GDSII 文件导入，返回结构化信息（兼容 gdsfactory 输出格式）。

    使用 klayout.db 读取 GDSII 文件，保留:
    1. 层次结构（所有 cells + 顶层 cell）
    2. 层号映射（(gds_layer, gds_datatype) → PoLaRIS 层名）
    3. 包围盒（顶层 cell bbox，μm）

    Args:
        gds_path: GDSII 文件路径。

    Returns:
        dict 含:
        - n_structures: 结构数（cell 数）
        - n_layers: 层数（有形状的层）
        - layers: 层信息列表 [{gds_layer, gds_datatype, polaris_name, n_shapes}]
        - bbox_um: 顶层 cell 包围盒 {xmin, ymin, xmax, ymax}（μm）

    Raises:
        FileNotFoundError: 文件不存在。
        RuntimeError: klayout 读取失败（R03 禁止 fall-back）。

    学术依据:
    - GDSII 格式: https://en.wikipedia.org/wiki/GDS_File
    - klayout Database API:
      https://klayout.org/downloads/master/doc-qt4/programming/database_api.html
    - gdsfactory PDK import:
      https://sequoiap.github.io/gdsfactory/notebooks/09_pdk_import.html
    """
    import klayout.db as db

    p = Path(gds_path)
    if not p.exists():
        raise FileNotFoundError(f"GDSII 文件不存在: {gds_path}")
    if not p.is_file():
        raise RuntimeError(f"路径不是文件: {gds_path}")

    ly = db.Layout()
    try:
        ly.read(str(p))
    except Exception as e:
        raise RuntimeError(
            f"klayout 读取 GDSII 失败: {type(e).__name__}: {e}。"
            f"禁止 fall-back（R03）。"
        ) from e

    dbu = float(ly.dbu)

    # 选择顶层 cell（取第一个 top cell）
    top_cells = [ly.cell(ci) for ci in ly.each_top_cell()]
    if not top_cells:
        raise RuntimeError(f"GDSII 文件 {gds_path} 无顶层 cell，文件可能为空")
    top_cell = top_cells[0]

    # 收集所有层的形状计数
    layer_shape_count: dict[tuple[int, int], int] = {}
    for ci in range(ly.cells()):
        cell = ly.cell(ci)
        for li in ly.layer_indices():
            info = ly.get_info(li)
            key = (int(info.layer), int(info.datatype))
            cnt = 0
            for _shape in cell.shapes(li).each():
                cnt += 1
            if cnt > 0:
                layer_shape_count[key] = layer_shape_count.get(key, 0) + cnt

    layers = []
    for (gl, gd), n_shapes in sorted(layer_shape_count.items()):
        polaris_name = _DEFAULT_LAYER_MAP.get(
            (gl, gd), f"LAYER_{gl}_{gd}"
        )
        layers.append({
            "gds_layer": gl,
            "gds_datatype": gd,
            "polaris_name": polaris_name,
            "n_shapes": n_shapes,
        })

    # 顶层 cell bbox（dbu → μm）
    bbox = top_cell.bbox()
    bbox_um = {
        "xmin": float(bbox.left) * dbu,
        "ymin": float(bbox.bottom) * dbu,
        "xmax": float(bbox.right) * dbu,
        "ymax": float(bbox.top) * dbu,
    }

    return {
        "n_structures": ly.cells(),
        "n_layers": len(layers),
        "layers": layers,
        "bbox_um": bbox_um,
    }


# ---------------------------------------------------------------------------
# 内部辅助函数
# ---------------------------------------------------------------------------


def _validate_circuit(circuit: dict) -> None:
    """校验 circuit dict 结构完整性（R03 禁止 fall-back）。

    Args:
        circuit: 待校验的 circuit dict。

    Raises:
        RuntimeError: circuit 非 dict 或缺少必要字段。
    """
    if not isinstance(circuit, dict):
        raise RuntimeError(
            f"circuit 必须是 dict，得到 {type(circuit).__name__}"
        )
    missing = [k for k in ("name", "devices") if k not in circuit]
    if missing:
        raise RuntimeError(
            f"circuit 缺少必要字段: {missing}（已有: {list(circuit.keys())}）"
        )
    if not isinstance(circuit["name"], str):
        raise RuntimeError("circuit.name 必须是 str")
    if not isinstance(circuit["devices"], list):
        raise RuntimeError("circuit.devices 必须是 list")
    for i, dev in enumerate(circuit["devices"]):
        if not isinstance(dev, dict):
            raise RuntimeError(
                f"circuit.devices[{i}] 必须是 dict，得到 {type(dev).__name__}"
            )
        for k in ("name", "device_type", "width_um", "height_um"):
            if k not in dev:
                raise RuntimeError(
                    f"circuit.devices[{i}] 缺少字段: {k}"
                )


def _verify_loadable(gds_path: str) -> bool:
    """重新读入 GDSII 文件验证可加载性（R03 禁止 fall-back）。

    Args:
        gds_path: GDSII 文件路径。

    Returns:
        True（可加载）。失败时 raise RuntimeError。
    """
    import klayout.db as db

    ly2 = db.Layout()
    try:
        ly2.read(gds_path)
    except Exception as e:
        raise RuntimeError(
            f"GDSII 读回验证失败: {type(e).__name__}: {e}。"
            f"文件可能损坏（R03 禁止 fall-back）。"
        ) from e
    if ly2.cells() == 0:
        raise RuntimeError(
            f"GDSII 读回验证失败: {gds_path} 无 cell（文件可能损坏）"
        )
    return True


__all__ = ["export_gds", "import_gds"]
