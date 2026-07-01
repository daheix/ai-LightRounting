"""R310 往返导入导出增强 — 多轮往返 + 几何哈希一致性验证。

批次 10-B 拆分说明（2026-07-01）:
    从 gdsfactory_advanced.py 抽出 R310 GDSII 往返验证模块。

来源（R02 学术诚信，≥5 文献 URL）:
1. GDSII binary format specification: https://en.wikipedia.org/wiki/GDS_File
2. KLayout Database API (Layout/Cell/Region):
   https://www.klayout.org/downloads/master/doc-qt4/programming/database_api.html
3. KLayout Layout.write: https://www.klayout.org/klayout-pypi/overview/instances/
4. gdsfactory write_gds: https://gdsfactory.github.io/gdsfactory/api.html#gdsfactory.write_gds
5. SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class RoundTripReport:
    """GDSII 往返验证报告（R310）。

    Attributes:
        input_path: 原始输入路径。
        output_path: 最终输出路径。
        n_rounds: 往返轮数。
        consistent: 一致性结果（True=通过）。
        geometric_hash_original: 原始几何哈希。
        geometric_hash_final: 最终几何哈希。
        n_cells: cell 数。
        n_polygons: 多边形数。
        n_instances: 实例数。
    """

    input_path: str
    output_path: str
    n_rounds: int
    consistent: bool
    geometric_hash_original: str
    geometric_hash_final: str
    n_cells: int
    n_polygons: int
    n_instances: int


def geometric_hash(gds_path: str | Path) -> str:
    """计算 GDS 文件的几何指纹（SHA256，R310）。

    对所有 cell 的多边形顶点、文本、实例变换做规范哈希，用于往返一致性验证。
    仅基于几何数据，不受 cell 排序或元数据影响。

    Args:
        gds_path: GDSII 文件路径。

    Returns:
        SHA256 十六进制摘要（64 字符）。

    Raises:
        FileNotFoundError: 文件不存在。
        RuntimeError: KLayout 读取失败。
    """
    import klayout.db as db

    path = Path(gds_path)
    if not path.exists():
        raise FileNotFoundError(f"GDS 文件不存在: {path}")
    ly = db.Layout()
    try:
        ly.read(str(path))
    except Exception as e:
        raise RuntimeError(f"KLayout 读取 GDS 失败: {type(e).__name__}: {e}") from e

    hasher = hashlib.sha256()
    # 按 cell.name 排序保证确定性（不受 cell 创建顺序影响）
    cells = sorted(list(ly.each_cell()), key=lambda c: c.name)
    for cell in cells:
        hasher.update(cell.name.encode("utf-8"))
        for li in ly.layer_indices():
            region = db.Region(cell.begin_shapes_rec(li))
            # region 的字符串表示含所有顶点（按规范排序）
            hasher.update(str(region).encode("utf-8"))
        # 实例变换（含被引用 cell 名）
        for inst in cell.each_inst():
            hasher.update(str(inst.trans).encode("utf-8"))
            hasher.update(inst.cell.name.encode("utf-8"))
    return hasher.hexdigest()

def round_trip_gdsii_advanced(
    input_path: str | Path,
    output_path: str | Path,
    n_rounds: int = 3,
    layer_map: dict[tuple[int, int], str] | None = None,
) -> RoundTripReport:
    """多轮 GDSII 往返 + 几何哈希一致性验证（R310）。

    流程:
    1. 计算原始几何哈希
    2. 重复 n_rounds 次：读入 → 写出
    3. 每轮重新计算几何哈希，与原始比对
    4. 全部一致则通过，否则 raise

    Args:
        input_path: 输入 GDSII 路径。
        output_path: 最终输出 GDSII 路径。
        n_rounds: 往返轮数（≥1）。
        layer_map: 可选层映射（兼容 R301）。

    Returns:
        RoundTripReport 实例。

    Raises:
        ValueError: n_rounds < 1。
        RuntimeError: 任一轮哈希不一致（R03：不静默通过）。
    """
    from polaris.pdk.gdsfactory_integration import import_gdsii_from_gdsfactory

    if n_rounds < 1:
        raise ValueError(f"n_rounds 必须 ≥ 1，实际 {n_rounds}")
    in_path = Path(input_path)
    out_path = Path(output_path)
    if not in_path.exists():
        raise FileNotFoundError(f"输入 GDSII 文件不存在: {in_path}")

    hash_original = geometric_hash(in_path)
    # 原始导入结果用于报告统计
    orig_result = import_gdsii_from_gdsfactory(in_path, layer_map=layer_map)

    current_in = in_path
    last_hash = hash_original
    for i in range(n_rounds):
        round_out = out_path if i == n_rounds - 1 else out_path.with_suffix(
            f".r{i}.gds"
        )
        last_hash = _roundtrip_write_and_verify(
            current_in, round_out, hash_original, i + 1
        )
        # 清理上一轮中间文件（missing_ok：文件已不存在非业务错误，不静默兜底业务）
        if i > 0 and current_in != in_path and current_in != out_path:
            current_in.unlink(missing_ok=True)
        current_in = round_out

    report = RoundTripReport(
        input_path=str(in_path),
        output_path=str(out_path),
        n_rounds=n_rounds,
        consistent=(last_hash == hash_original),
        geometric_hash_original=hash_original,
        geometric_hash_final=last_hash,
        n_cells=orig_result.n_cells,
        n_polygons=orig_result.total_polygons,
        n_instances=orig_result.total_instances,
    )
    logger.info(
        "GDSII 多轮往返验证通过: %s → %s (%d 轮, hash=%s...)",
        in_path.name,
        out_path.name,
        n_rounds,
        last_hash[:12],
    )
    return report


def _roundtrip_write_and_verify(
    in_path: Path, out_path: Path, hash_original: str, round_idx: int
) -> str:
    """单轮 GDSII 读入→写出→哈希验证（R310 内部 helper）。

    Args:
        in_path: 本轮输入 GDSII 路径。
        out_path: 本轮输出 GDSII 路径。
        hash_original: 原始几何哈希（用于一致性比对）。
        round_idx: 轮次序号（1-based，用于错误信息）。

    Returns:
        本轮输出文件的几何哈希。

    Raises:
        RuntimeError: 读取失败或哈希不一致（R03：不静默通过）。
    """
    import klayout.db as db

    ly = db.Layout()
    try:
        ly.read(str(in_path))
    except Exception as e:
        raise RuntimeError(
            f"第 {round_idx} 轮读取失败: {type(e).__name__}: {e}"
        ) from e
    ly.write(str(out_path))
    round_hash = geometric_hash(out_path)
    if round_hash != hash_original:
        raise RuntimeError(
            f"第 {round_idx} 轮往返哈希不一致:\n"
            f"  原始={hash_original}\n  第{round_idx}轮={round_hash}"
        )
    return round_hash


__all__ = [
    "RoundTripReport",
    "geometric_hash",
    "round_trip_gdsii_advanced",
]
