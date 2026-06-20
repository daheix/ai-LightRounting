"""从 SiEPIC GDS 提取网表并保存为 JSON（roadmap M2.1）。

遍历 ``data/benchmarks/siepic_examples/*.gds``，用
:func:`polaris.data.gds_loader.load_gds_to_circuit` 解析为
:class:`~polaris.data.specs.CircuitSpec`，序列化为 JSON 保存到
``data/benchmarks/siepic_netlists/``。

来源:
- SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- klayout GDS 解析: https://www.klayout.org/klayout-pypi/
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from polaris.data.gds_loader import load_gds_to_circuit

logger = logging.getLogger(__name__)

_GDS_DIR = Path("data/benchmarks/siepic_examples")
_OUT_DIR = Path("data/benchmarks/siepic_netlists")


def circuit_to_dict(circuit) -> dict:
    """将 CircuitSpec 序列化为可 JSON 化的字典。

    Args:
        circuit: CircuitSpec 对象。

    Returns:
        与现有 benchmark JSON 格式兼容的字典。
    """
    return {
        "name": circuit.name,
        "platform": "SOI",
        "source": "SiEPIC EBeam PDK GDS",
        "canvas_w": circuit.canvas_w,
        "canvas_h": circuit.canvas_h,
        "devices": [
            {
                "name": d.name,
                "type": d.device_type,
                "width_um": d.width_um,
                "height_um": d.height_um,
                "ports": [list(p) for p in d.ports],
                "params": d.params,
            }
            for d in circuit.devices
        ],
        "connections": [list(c) for c in circuit.connections],
    }


def main() -> None:
    """提取所有 SiEPIC GDS 网表到 JSON。"""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    _OUT_DIR.mkdir(parents=True, exist_ok=True)
    gds_files = sorted(_GDS_DIR.glob("*.gds"))
    success = 0
    skipped = 0
    for gds in gds_files:
        try:
            circuit = load_gds_to_circuit(gds)
            if not circuit.devices:
                logger.warning("跳过 %s（无器件实例，非 SiEPIC 标准格式）", gds.name)
                skipped += 1
                continue
            out_path = _OUT_DIR / f"{gds.stem}.json"
            data = circuit_to_dict(circuit)
            out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            logger.info(
                "%s → %s（%d 器件, %d 连接）",
                gds.name,
                out_path.name,
                len(circuit.devices),
                len(circuit.connections),
            )
            success += 1
        except Exception as e:
            logger.error("解析 %s 失败: %s: %s", gds.name, type(e).__name__, e)
            skipped += 1
    logger.info("完成: %d 成功, %d 跳过, 共 %d", success, skipped, len(gds_files))


if __name__ == "__main__":
    main()
