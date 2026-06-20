"""构建模仿学习专家示范数据集 — 从 SiEPIC GDS 提取三元组。

将 data/benchmarks/siepic_examples/*.gds 转换为
(网表 JSON, 专家布局 JSON, 专家布线 JSON) 三元组，
存放到 data/expert_demos/<gds_name>/ 目录。

每个 GDS 生成一个子目录，包含：
- netlist.json: CircuitSpec 序列化（器件+连接+画布）
- placements.json: 专家布局 {device_name: {x, y, rotation, mirror, bbox, w, h}}
- routes.json: 专家布线 [[(x1,y1), (x2,y2), ...], ...]
- meta.json: 元数据（来源 GDS, URL, 协议, 提取时间, 器件数, 波导数）

来源:
- SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK (MIT, UBC, Lukas Chrostowski)
- 模仿学习理论: Pomerleau 1989, "ALVINN: An Autonomous Land Vehicle in a Neural Network"
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from polaris.data.expert_layout import load_gds_to_circuit_with_layout

logger = logging.getLogger(__name__)

# SiEPIC EBeam PDK 来源信息（学术诚信标注）
_SIEPIC_SOURCE = {
    "name": "SiEPIC_EBeam_PDK",
    "publisher": "University of British Columbia (UBC), SiEPIC",
    "author": "Lukas Chrostowski et al.",
    "license": "MIT",
    "url": "https://github.com/SiEPIC/SiEPIC_EBeam_PDK",
    "examples_url": "https://github.com/SiEPIC/SiEPIC_EBeam_PDK/tree/master/Examples",
    "year": "2015-2023",
}


def _circuit_to_dict(circuit) -> dict:
    """将 CircuitSpec 序列化为可 JSON 化的字典。

    Args:
        circuit: CircuitSpec 对象。

    Returns:
        JSON 兼容的字典。
    """
    return {
        "name": circuit.name,
        "canvas_w": circuit.canvas_w,
        "canvas_h": circuit.canvas_h,
        "devices": [asdict(d) for d in circuit.devices],
        "connections": [list(c) for c in circuit.connections],
    }


def build_expert_dataset(
    gds_dir: str | Path = "data/benchmarks/siepic_examples",
    output_dir: str | Path = "data/expert_demos",
) -> dict:
    """从 SiEPIC GDS 构建专家示范三元组数据集。

    Args:
        gds_dir: SiEPIC GDS 例子目录。
        output_dir: 输出目录（每个 GDS 一个子目录）。

    Returns:
        统计字典 {total_gds, success, failed, total_devices, total_routes}。
    """
    gds_dir = Path(gds_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    gds_files = sorted(list(gds_dir.glob("*.gds")) + list(gds_dir.glob("*.GDS")))
    stats = {
        "total_gds": len(gds_files),
        "success": 0,
        "failed": 0,
        "total_devices": 0,
        "total_routes": 0,
        "total_placements": 0,
        "records": [],
    }

    for gds_path in gds_files:
        record_name = gds_path.stem
        record_dir = output_dir / record_name
        try:
            circuit, placements, routes = load_gds_to_circuit_with_layout(gds_path)

            # 序列化三元组
            netlist_data = _circuit_to_dict(circuit)
            (record_dir).mkdir(parents=True, exist_ok=True)
            (record_dir / "netlist.json").write_text(
                json.dumps(netlist_data, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            (record_dir / "placements.json").write_text(
                json.dumps(placements, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            (record_dir / "routes.json").write_text(
                json.dumps(routes, indent=2, ensure_ascii=False), encoding="utf-8"
            )

            # 元数据（学术诚信标注）
            meta = {
                "source_gds": gds_path.name,
                "source_url": f"{_SIEPIC_SOURCE['examples_url']}/{gds_path.name}",
                "source_pdk": _SIEPIC_SOURCE,
                "extract_time": datetime.now().isoformat(),
                "circuit_name": circuit.name,
                "n_devices": len(circuit.devices),
                "n_connections": len(circuit.connections),
                "n_placements": len(placements),
                "n_routes": len(routes),
                "canvas_w_um": circuit.canvas_w,
                "canvas_h_um": circuit.canvas_h,
            }
            (record_dir / "meta.json").write_text(
                json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
            )

            stats["success"] += 1
            stats["total_devices"] += len(circuit.devices)
            stats["total_routes"] += len(routes)
            stats["total_placements"] += len(placements)
            stats["records"].append(
                {
                    "name": record_name,
                    "n_devices": len(circuit.devices),
                    "n_routes": len(routes),
                    "status": "success",
                }
            )
            logger.info(
                "✅ %s: %d 器件, %d 布局, %d 波导",
                gds_path.name,
                len(circuit.devices),
                len(placements),
                len(routes),
            )
        except Exception as e:
            stats["failed"] += 1
            stats["records"].append({"name": record_name, "status": f"failed: {e}"})
            logger.error("❌ %s: %s", gds_path.name, e)

    # 写入数据集索引
    index = {
        "dataset_name": "PoLaRIS Expert Demos (SiEPIC)",
        "description": "从真实 SiEPIC EBeam PDK GDS 提取的专家示范三元组数据集",
        "source": _SIEPIC_SOURCE,
        "extract_time": datetime.now().isoformat(),
        "stats": stats,
        "records": stats["records"],
    }
    (output_dir / "index.json").write_text(
        json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    return stats


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    s = build_expert_dataset()
    print(
        f"\n数据集构建完成: {s['success']}/{s['total_gds']} 成功, "
        f"{s['total_devices']} 器件, {s['total_placements']} 布局, {s['total_routes']} 波导"
    )
