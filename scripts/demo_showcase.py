#!/usr/bin/env python3
"""演示图形生成脚本：运行 5 个 demo 电路并生成 PNG 图形。

输出:
- checkpoints/demo_showcase/<circuit>.png: 每个电路的版图渲染图
- checkpoints/demo_showcase/<circuit>_report.json: 报告
- checkpoints/demo_showcase/summary.json: 汇总
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("demo_showcase")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEMO_DIR = PROJECT_ROOT / "data" / "benchmarks" / "demo"
OUTPUT_DIR = PROJECT_ROOT / "checkpoints" / "demo_showcase"


def build_circuit_spec(circuit_data: dict):
    from polaris.data.specs import CircuitSpec, DeviceSpec

    devices = []
    for dev in circuit_data.get("devices", []):
        ports = [(p[0], float(p[1]), float(p[2]), p[3]) for p in dev.get("ports", [])]
        devices.append(
            DeviceSpec(
                name=dev["name"],
                device_type=dev["type"],
                width_um=float(dev["width_um"]),
                height_um=float(dev["height_um"]),
                ports=ports,
            )
        )

    connections = [tuple(c) for c in circuit_data.get("connections", [])]

    return CircuitSpec(
        name=circuit_data.get("name", "demo"),
        devices=devices,
        connections=connections,
        canvas_w=float(circuit_data.get("canvas_w", 300.0)),
        canvas_h=float(circuit_data.get("canvas_h", 200.0)),
    )


def render_layout_png(circuit, placements: dict, paths: dict, output_path: Path) -> None:
    """用 matplotlib 渲染版图为 PNG。"""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    fig, ax = plt.subplots(1, 1, figsize=(10, 8))
    ax.set_xlim(0, circuit.canvas_w)
    ax.set_ylim(0, circuit.canvas_h)
    ax.set_aspect("equal")
    ax.set_title(f"{circuit.name} — PoLaRIS Layout (devices={len(circuit.devices)}, "
                 f"nets={len(circuit.connections)})", fontsize=12)
    ax.set_xlabel("x (μm)")
    ax.set_ylabel("y (μm)")
    ax.grid(True, alpha=0.3, linestyle="--")

    # 颜色映射：器件类型 → 颜色
    type_colors = {
        "grating_coupler": "#FF6B6B",
        "y_branch": "#4ECDC4",
        "mmi": "#FFE66D",
        "strip_waveguide": "#95E1D3",
        "ring": "#A8E6CF",
        "directional_coupler": "#C7CEEA",
        "phase_shifter": "#FFAAA5",
        "crossing": "#FFD3B6",
        "photodetector": "#B5EAD7",
    }

    # 绘制器件
    for dev in circuit.devices:
        if dev.name not in placements:
            continue
        p = placements[dev.name]
        color = type_colors.get(dev.device_type, "#DDA0DD")
        rect = Rectangle(
            (p["x"], p["y"]),
            p["w"],
            p["h"],
            linewidth=1.5,
            edgecolor="black",
            facecolor=color,
            alpha=0.8,
        )
        ax.add_patch(rect)
        # 器件名标签
        ax.text(
            p["x"] + p["w"] / 2,
            p["y"] + p["h"] / 2,
            dev.name,
            ha="center",
            va="center",
            fontsize=8,
            fontweight="bold",
        )

    # 绘制布线路径
    for net_name, pts in paths.items():
        if len(pts) < 2:
            continue
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        ax.plot(xs, ys, "-", color="#2C3E50", linewidth=1.2, alpha=0.7)

    # 图例
    from matplotlib.patches import Patch

    legend_handles = []
    seen_types = set()
    for dev in circuit.devices:
        if dev.device_type in seen_types:
            continue
        seen_types.add(dev.device_type)
        color = type_colors.get(dev.device_type, "#DDA0DD")
        legend_handles.append(Patch(facecolor=color, edgecolor="black", label=dev.device_type))
    ax.legend(handles=legend_handles, loc="upper right", fontsize=8, framealpha=0.9)

    plt.tight_layout()
    plt.savefig(str(output_path), dpi=120, bbox_inches="tight")
    plt.close()
    logger.info("渲染 PNG: %s", output_path)


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    from polaris.pipeline.integrated import IntegratedPipeline, PipelineConfig

    circuits = []
    for json_file in sorted(DEMO_DIR.glob("demo_*.json")):
        data = json.loads(json_file.read_text(encoding="utf-8"))
        circuits.append({"name": data.get("name", json_file.stem), "data": data})

    summary = {"circuits": []}

    for circuit in circuits:
        name = circuit["name"]
        logger.info("=" * 60)
        logger.info("运行 demo: %s", name)

        spec = build_circuit_spec(circuit["data"])
        out_dir = OUTPUT_DIR / name
        out_dir.mkdir(parents=True, exist_ok=True)

        config = PipelineConfig(
            canvas_w=spec.canvas_w,
            canvas_h=spec.canvas_h,
            grid_size=10.0,
            max_sim_iterations=2,
            output_dir=str(out_dir),
        )
        pipeline = IntegratedPipeline(config=config)
        result = pipeline.run(spec)

        # 渲染 PNG
        png_path = OUTPUT_DIR / f"{name}.png"
        render_layout_png(spec, result.placements, result.paths, png_path)

        info = {
            "name": name,
            "n_devices": result.n_devices,
            "n_connections": result.n_connections,
            "total_loss_db": result.total_loss_db,
            "n_crossings": result.n_crossings,
            "drc_passed": result.drc_passed,
            "sim_iterations": result.sim_iterations,
            "png_path": str(png_path),
            "gds_path": result.gds_path,
            "report_path": result.report_path,
        }
        summary["circuits"].append(info)
        logger.info(
            "完成: %s | 器件=%d | 连接=%d | 损耗=%.3fdB | DRC=%s",
            name,
            result.n_devices,
            result.n_connections,
            result.total_loss_db,
            "Y" if result.drc_passed else "N",
        )

    summary_path = OUTPUT_DIR / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("=" * 60)
    logger.info("汇总: %s", summary_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
