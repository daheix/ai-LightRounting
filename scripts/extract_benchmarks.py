"""基准数据提取脚本。

从已下载的开源仓库中提取标准成品走线布线布局数据，
转换为 PoLaRIS 统一格式，作为基准数据和校准数据。

数据来源:
- LiDAR PIC IR: https://github.com/ScopeX-ASU/LiDAR
- PICBench: https://github.com/PICDA/PICBench
- GDSFactory: https://gdsfactory.github.io/gdsfactory/
- UBC SiEPIC PDK: https://github.com/gdsfactory/ubc
- SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK

用法:
    python scripts/extract_benchmarks.py --output data/benchmarks
    python scripts/extract_benchmarks.py --source lidar --output data/benchmarks
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

# 默认工具目录
TOOLS_DIR = Path(__file__).parent.parent / "data" / "tools"


def extract_lidar_benchmarks(tools_dir: Path, output_dir: Path) -> list[dict]:
    """从 LiDAR 仓库提取 PIC IR 基准数据。

    来源: https://github.com/ScopeX-ASU/LiDAR

    Args:
        tools_dir: 工具目录（含 LiDAR 仓库）。
        output_dir: 输出目录。

    Returns:
        提取的基准数据列表。
    """
    lidar_dir = tools_dir / "LiDAR" / "src" / "picroute" / "benchmarks"
    if not lidar_dir.exists():
        logger.error("LiDAR 基准目录不存在: %s", lidar_dir)
        return []

    benchmarks: list[dict] = []
    for yml_file in sorted(lidar_dir.glob("**/*.yml")):
        if yml_file.name in ("default_config.yml", "comp_LiDAR.yml"):
            continue
        try:
            text = yml_file.read_text(encoding="utf-8")
            # 处理 !!python/tuple 标签（LiDAR 使用了 Python 特有标签）
            text = text.replace("!!python/tuple ", "")
            raw = yaml.safe_load(text)
        except Exception as e:
            logger.warning("解析失败: %s (%s)", yml_file, e)
            continue

        name = yml_file.stem.replace(".gp", "")
        instances = raw.get("instances", [])
        nets = raw.get("nets", [])
        placements = raw.get("placements", {})

        bench = {
            "source": "LiDAR",
            "name": name,
            "file": str(yml_file.relative_to(tools_dir)),
            "n_devices": len(instances),
            "n_nets": len(nets),
            "has_placements": bool(placements),
            "instances": instances,
            "nets": nets,
            "placements": placements,
        }
        benchmarks.append(bench)

        # 保存到输出目录
        out_file = output_dir / f"lidar_{name}.json"
        out_file.write_text(json.dumps(bench, indent=2, ensure_ascii=False), encoding="utf-8")

    logger.info("LiDAR: 提取了 %d 个基准", len(benchmarks))
    return benchmarks


def extract_picbench_data(tools_dir: Path, output_dir: Path) -> list[dict]:
    """从 PICBench 仓库提取光子电路基准数据。

    来源: https://github.com/PICDA/PICBench

    Args:
        tools_dir: 工具目录（含 PICBench 仓库）。
        output_dir: 输出目录。

    Returns:
        提取的基准数据列表。
    """
    picbench_dir = tools_dir / "PICBench" / "testcases"
    if not picbench_dir.exists():
        logger.error("PICBench 目录不存在: %s", picbench_dir)
        return []

    benchmarks: list[dict] = []
    for ref_file in sorted(picbench_dir.glob("**/*_ref.json")):
        try:
            raw = json.loads(ref_file.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning("解析失败: %s (%s)", ref_file, e)
            continue

        name = ref_file.parent.name
        bench = {
            "source": "PICBench",
            "name": name,
            "file": str(ref_file.relative_to(tools_dir)),
            "data": raw,
        }
        # 尝试提取器件和连接数
        if isinstance(raw, dict):
            bench["n_components"] = len(raw.get("components", raw.get("instances", [])))
            bench["n_connections"] = len(raw.get("connections", raw.get("nets", [])))
        benchmarks.append(bench)

        out_file = output_dir / f"picbench_{name}.json"
        out_file.write_text(json.dumps(bench, indent=2, ensure_ascii=False), encoding="utf-8")

    logger.info("PICBench: 提取了 %d 个基准", len(benchmarks))
    return benchmarks


def extract_gdsfactory_circuits(tools_dir: Path, output_dir: Path) -> list[dict]:
    """从 GDSFactory 仓库提取 YAML 示例电路。

    来源: https://gdsfactory.github.io/gdsfactory/

    Args:
        tools_dir: 工具目录（含 gdsfactory 仓库）。
        output_dir: 输出目录。

    Returns:
        提取的电路数据列表。
    """
    gf_dir = tools_dir / "gdsfactory"
    if not gf_dir.exists():
        logger.error("GDSFactory 目录不存在: %s", gf_dir)
        return []

    circuits: list[dict] = []
    # 搜索所有 *.pic.yml 文件
    for yml_file in sorted(gf_dir.glob("**/*.pic.yml")):
        try:
            raw = yaml.safe_load(yml_file.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning("解析失败: %s (%s)", yml_file, e)
            continue

        name = yml_file.stem.replace(".pic", "")
        instances = raw.get("instances", {})
        connections = raw.get("connections", [])
        routes = raw.get("routes", {})
        placements = raw.get("placements", {})

        circuit = {
            "source": "GDSFactory",
            "name": name,
            "file": str(yml_file.relative_to(tools_dir)),
            "n_instances": len(instances) if isinstance(instances, dict) else len(instances),
            "n_connections": len(connections),
            "n_routes": len(routes) if isinstance(routes, dict) else len(routes),
            "has_placements": bool(placements),
            "instances": instances,
            "connections": connections,
            "routes": routes,
            "placements": placements,
        }
        circuits.append(circuit)

        out_file = output_dir / f"gf_{name}.json"
        out_file.write_text(json.dumps(circuit, indent=2, ensure_ascii=False), encoding="utf-8")

    logger.info("GDSFactory: 提取了 %d 个电路", len(circuits))
    return circuits


def extract_all(tools_dir: Path, output_dir: Path) -> dict:
    """提取所有数据源的基准数据。

    Args:
        tools_dir: 工具目录。
        output_dir: 输出目录。

    Returns:
        提取统计。
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    lidar = extract_lidar_benchmarks(tools_dir, output_dir)
    picbench = extract_picbench_data(tools_dir, output_dir)
    gdsfactory = extract_gdsfactory_circuits(tools_dir, output_dir)

    stats = {
        "lidar": len(lidar),
        "picbench": len(picbench),
        "gdsfactory": len(gdsfactory),
        "total": len(lidar) + len(picbench) + len(gdsfactory),
    }

    # 保存总索引
    index_path = output_dir / "index.json"
    index = {
        "stats": stats,
        "lidar_benchmarks": [
            {"name": b["name"], "n_devices": b["n_devices"], "n_nets": b["n_nets"]} for b in lidar
        ],
        "picbench_benchmarks": [{"name": b["name"]} for b in picbench],
        "gdsfactory_circuits": [
            {"name": c["name"], "n_instances": c["n_instances"]} for c in gdsfactory
        ],
    }
    index_path.write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")

    logger.info(
        "提取完成: LiDAR=%d, PICBench=%d, GDSFactory=%d, 总计=%d",
        len(lidar),
        len(picbench),
        len(gdsfactory),
        stats["total"],
    )
    return stats


def main() -> None:
    """命令行入口。"""
    parser = argparse.ArgumentParser(description="提取开源光子电路基准数据")
    parser.add_argument("--tools", default=str(TOOLS_DIR), help="工具目录")
    parser.add_argument("--output", default="data/benchmarks", help="输出目录")
    parser.add_argument(
        "--source", choices=["all", "lidar", "picbench", "gdsfactory"], default="all", help="数据源"
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    tools_dir = Path(args.tools)
    output_dir = Path(args.output)

    if args.source == "all":
        extract_all(tools_dir, output_dir)
    elif args.source == "lidar":
        extract_lidar_benchmarks(tools_dir, output_dir)
    elif args.source == "picbench":
        extract_picbench_data(tools_dir, output_dir)
    elif args.source == "gdsfactory":
        extract_gdsfactory_circuits(tools_dir, output_dir)


if __name__ == "__main__":
    main()
