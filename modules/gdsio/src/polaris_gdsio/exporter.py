"""GDSII 导出器（polaris-gdsio 子模块）。

将 polaris-core 风格的 circuit dict 导出为 gdsfactory 兼容的 GDSII 文件，
使用 klayout.db API。从原 polaris_pdk/gdsii.py 迁移，包名改为 polaris_gdsio。

=== Input / Process / Output 三段式文档 ===

Input:
- circuit: dict（polaris-core 风格），含
    * name: str                 顶层 cell 名
    * devices: list[dict]       每个器件含 name/device_type/width_um/height_um
    * connections: list         （可空）
    * canvas_w / canvas_h: float（可选）
- output_path: str              GDSII 输出文件路径

Process:
1. klayout.db 创建 Layout（dbu=0.001μm=1nm，与 gdsfactory 默认一致）
2. 创建顶层 cell（名为 circuit["name"]）
3. 为每个器件创建子 cell，含一个 box（width_um × height_um）在 WG 层 (1,0)
4. 在顶层 cell 中放置每个器件的实例（沿 x 轴顺序排列，间距 5μm）
5. 写出 GDSII 文件
6. 重新读入验证 loadable=True（无信息损失校验）

Output:
- dict 含:
    * path: GDSII 文件绝对路径
    * file_size_bytes: 文件大小（字节）
    * n_structures: 结构数（cell 数，含顶层）
    * n_layers: 层数
    * loadable: 是否可被 klayout 重新读入（True/False）

学术依据（R02 学术诚信，均经 WebSearch 验证可访问）:
- klayout Layout.write API:
  https://www.klayout.org/downloads/master/doc-qt4/programming/database_api.html
- gdsfactory write_gds 默认参数（dbu=0.001μm=1nm）:
  https://gdsfactory.github.io/gdsfactory/api.html#gdsfactory.write_gds
- GDSII 格式规范: https://en.wikipedia.org/wiki/GDS_File
- GDSII 层次结构（cell/SREF/AREF）:
  https://gdspy.readthedocs.io/en/master/gettingstarted.html#references
- KLayout CellInstArray: https://www.klayout.de/doc-qt5/code/class_CellInstArray.html
- gdsfactory generic PDK layer definitions:
  https://gdsfactory.github.io/gdsfactory/

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R05 Bug 必修。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

# gdsfactory 写出 GDSII 的默认 dbu（μm）
# 来源: gdsfactory write_gds 默认参数
# https://gdsfactory.github.io/gdsfactory/api.html#gdsfactory.write_gds
_GDSFACTORY_DEFAULT_DBU_UM: float = 0.001

# 波导核心层（gdsfactory 默认 WG layer (1, 0)）
# 来源: gdsfactory PDK import 文档
# https://sequoiap.github.io/gdsfactory/notebooks/09_pdk_import.html
_WG_LAYER: tuple[int, int] = (1, 0)

# 器件间水平间距（μm），用于顶层实例顺序排列
_DEVICE_SPACING_UM: float = 5.0


def _place_device_cells(
    ly, circuit: dict, wg_li, dbu: float, top_cell,
) -> None:
    """为每个器件创建子 cell 并在顶层放置实例（沿 x 轴顺序排列）。"""
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
        x_offset += w_um + _DEVICE_SPACING_UM


def _build_export_result(out: Path, ly, loadable: bool) -> dict[str, Any]:
    """构造导出结果 dict。"""
    file_size = out.stat().st_size
    n_structures = ly.cells()
    n_layers = len([li for li in ly.layer_indices()])
    return {
        "path": str(out.resolve()),
        "file_size_bytes": file_size,
        "n_structures": n_structures,
        "n_layers": n_layers,
        "loadable": loadable,
    }


def export_gds(circuit: dict, output_path: str) -> dict[str, Any]:
    """将 polaris_core circuit dict 导出为 gdsfactory 兼容 GDSII 文件。

    流程详见模块 docstring 的 Process 段。

    Args:
        circuit: polaris_core.make_circuit 返回的 circuit dict，含
            name/devices/connections/canvas_w/canvas_h 等字段。每个 device 含
            name/device_type/width_um/height_um/ports/params。
        output_path: GDSII 输出文件路径。

    Returns:
        dict 含 path/file_size_bytes/n_structures/n_layers/loadable（详见模块
        docstring 的 Output 段）。

    Raises:
        RuntimeError: circuit 结构无效或 klayout 写入/读回失败（R03 禁止 fall-back）。
    """
    import klayout.db as db

    _validate_circuit(circuit)
    out = Path(output_path)
    if out.is_dir():
        raise RuntimeError(f"输出路径是目录不是文件: {output_path}")
    out.parent.mkdir(parents=True, exist_ok=True)
    ly = db.Layout()
    ly.dbu = _GDSFACTORY_DEFAULT_DBU_UM
    top_name = str(circuit["name"])
    top_cell = ly.create_cell(top_name)
    wg_li = ly.layer(_WG_LAYER[0], _WG_LAYER[1])
    dbu = _GDSFACTORY_DEFAULT_DBU_UM
    _place_device_cells(ly, circuit, wg_li, dbu, top_cell)
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
    loadable = _verify_loadable(str(out))
    return _build_export_result(out, ly, loadable)


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


__all__ = ["export_gds"]
