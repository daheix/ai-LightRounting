"""一体化流水线包。

提供端到端自动布局布线 + 仿真回馈一体化流水线，以及 CLI 入口函数
``cmd_run`` / ``cmd_catalog`` / ``cmd_train`` 与 ``main`` argparse 入口。

CLI 用法::

    python -m polaris run --netlist circuit.yaml --output out/
    python -m polaris train --episodes 50 --output checkpoints/
    python -m polaris catalog --platform SOI

来源:
- Apollo arXiv 2025: https://arxiv.org/html/2504.18813v1
- LiDAR ISPD'25: https://dl.acm.org/doi/pdf/10.1145/3698364.3705355
- OptoSynthesizer arXiv 2026: https://arxiv.org/pdf/2604.15493v1
"""

from __future__ import annotations

import argparse
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from polaris.pdk.catalog import build_default_catalog

logger = logging.getLogger(__name__)

__all__ = ["cmd_run", "cmd_catalog", "cmd_train", "main"]


@dataclass
class CanvasConfig:
    """画布尺寸配置（将 _place/_route 的画布参数打包，降低函数参数个数）。

    Attributes:
        canvas_w: 画布宽度（μm）。
        canvas_h: 画布高度（μm）。
        grid_size: 栅格大小（μm）。
    """

    canvas_w: float = 200.0
    canvas_h: float = 200.0
    grid_size: float = 5.0


def _run_floorplan(net, devices, canvas_w: float, canvas_h: float, grid_size: float):
    """执行布局：每个器件放到网格 (5,5) 位置（与集成测试一致）。"""
    from polaris.engine.floorplan_env import FloorplanEnv

    fp = FloorplanEnv(net, devices, canvas_w=canvas_w, canvas_h=canvas_h, grid_size=grid_size)
    fp.reset()
    for _ in range(len(devices)):
        fp.step([5, 5, 0])
    return fp


def _run_routing(net, placements, canvas_w: float, canvas_h: float, grid_size: float):
    """执行布线：每条连接用零偏移动作（A* 默认路径）。"""
    import numpy as np

    from polaris.router.routing_env import RoutingEnv

    r_env = RoutingEnv(
        net,
        placements,
        canvas_w=canvas_w,
        canvas_h=canvas_h,
        grid_size=grid_size,
    )
    r_env.reset()
    for _ in range(len(net.connections)):
        r_env.step(np.zeros(3, dtype=np.float32))
    return r_env


def _write_report(out_dir: Path, net, devices: dict, placements, paths) -> None:
    """写出 report.json（含器件数/连接数/损耗/长度/DRC 摘要）。

    Args:
        out_dir: 输出目录。
        net: 网表（用于取电路名与连接数）。
        devices: 器件字典（用于取器件数）。
        placements: 布局结果。
        paths: 布线路径。
    """
    from polaris.eval.layout_render import run_drc

    drc = run_drc(placements, paths)
    total_loss = sum(getattr(wp, "loss_db", 0.0) for wp in paths.values())
    total_length = sum(getattr(wp, "length_um", 0.0) for wp in paths.values())
    report = {
        "circuit": net.name,
        "num_devices": len(devices),
        "num_connections": len(net.connections),
        "total_loss_db": total_loss,
        "total_length_um": total_length,
        "drc_total_violations": drc.total_violations,
        "drc_passed": drc.passed,
    }
    (out_dir / "report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def _export_layout(out_dir: Path, placements, paths) -> None:
    """导出 GDS/OAS/PNG 三件套。"""
    from polaris.eval.layout_render import (
        RenderOptions,
        export_gds,
        export_oasis,
        render_layout,
    )

    export_gds(placements, paths, str(out_dir / "layout.gds"))
    export_oasis(placements, paths, str(out_dir / "layout.oas"))
    render_layout(
        placements,
        paths,
        options=RenderOptions(save_path=str(out_dir / "layout.png")),
    )


def cmd_run(args: Any) -> int:
    """CLI run 命令：网表 → 布局 → 布线 → GDS/OAS/PNG → report.json。

    Args:
        args: 参数对象，需包含属性 netlist/output/canvas_w/canvas_h/grid_size。

    Returns:
        0 表示成功。
    """
    from polaris.engine.netlist import load_netlist

    net, devices, _ = load_netlist(args.netlist)
    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"[1/4] 加载网表: {net.name} ({len(devices)} 器件, {len(net.connections)} 连接)")
    fp = _run_floorplan(net, devices, args.canvas_w, args.canvas_h, args.grid_size)
    print(f"[2/4] 布局完成: {len(fp.state.placements)} 器件")
    r_env = _run_routing(net, fp.state.placements, args.canvas_w, args.canvas_h, args.grid_size)
    print(f"[3/4] 布线完成: {len(r_env.state.paths)} 连接")
    placements = fp.state.placements
    paths = r_env.state.paths
    _export_layout(out_dir, placements, paths)
    _write_report(out_dir, net, devices, placements, paths)
    print(f"[4/4] 报告已保存: {out_dir / 'report.json'}")
    logger.info("流水线完成: %s (%d 器件, %d 连接)", net.name, len(devices), len(net.connections))
    return 0


def cmd_catalog(args: Any) -> int:
    """CLI catalog 命令：列出器件目录。

    Args:
        args: 参数对象，需包含属性 platform（可为 None 表示全部）。

    Returns:
        0 表示成功。
    """
    cat = build_default_catalog()
    platform = getattr(args, "platform", None)
    devices = cat.list_devices(platform=platform)
    plat_label = platform or "ALL"
    print(f"平台: {plat_label}")
    print(f"器件数: {len(devices)}")
    print("-" * 60)
    for d in devices:
        print(f"  [{d.platform}] {d.name} ({d.category})")
    return 0


def cmd_train(args: Any) -> int:
    """CLI train 命令：启动 PPO 布局训练。

    Args:
        args: 参数对象，需包含属性 episodes/rollout_steps/num_netlists/
            min_devices/max_devices/canvas_w/canvas_h/grid_size/hidden_dim/output。

    Returns:
        0 表示成功。
    """
    from polaris.trainer.train_loop import TrainConfig, train_floorplan

    cfg = TrainConfig(
        num_episodes=int(args.episodes),
        rollout_steps=int(args.rollout_steps),
        canvas_w=float(args.canvas_w),
        canvas_h=float(args.canvas_h),
        grid_size=float(args.grid_size),
        hidden_dim=int(args.hidden_dim),
        checkpoint_dir=str(args.output),
    )
    cfg.dataset.num_netlists = int(args.num_netlists)
    cfg.dataset.min_devices = int(args.min_devices)
    cfg.dataset.max_devices = int(args.max_devices)
    train_floorplan(cfg, verbose=False)
    return 0


def _build_parser() -> argparse.ArgumentParser:
    """构建 CLI argparse 解析器。"""
    parser = argparse.ArgumentParser(
        prog="polaris",
        description="PoLaRIS 光电子 AI 智能布局布线引擎",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # run
    p_run = sub.add_parser("run", help="端到端运行：网表 → 布局 → 布线 → GDS/OAS → 报告")
    p_run.add_argument("--netlist", required=True, help="网表文件路径 (YAML/JSON)")
    p_run.add_argument("--output", "-o", default="out", help="输出目录")
    p_run.add_argument("--canvas-w", type=float, default=200.0)
    p_run.add_argument("--canvas-h", type=float, default=200.0)
    p_run.add_argument("--grid-size", type=float, default=5.0)
    p_run.set_defaults(func=cmd_run)

    # train
    p_train = sub.add_parser("train", help="训练 PPO 智能体")
    p_train.add_argument("--episodes", type=int, default=50)
    p_train.add_argument("--rollout-steps", type=int, default=64)
    p_train.add_argument("--num-netlists", type=int, default=50)
    p_train.add_argument("--min-devices", type=int, default=3)
    p_train.add_argument("--max-devices", type=int, default=12)
    p_train.add_argument("--canvas-w", type=float, default=200.0)
    p_train.add_argument("--canvas-h", type=float, default=200.0)
    p_train.add_argument("--grid-size", type=float, default=5.0)
    p_train.add_argument("--hidden-dim", type=int, default=64)
    p_train.add_argument("--output", "-o", default="checkpoints")
    p_train.set_defaults(func=cmd_train)

    # catalog
    p_cat = sub.add_parser("catalog", help="列出器件目录")
    p_cat.add_argument("--platform", default=None, help="过滤平台 (SOI/SiN/InP/LNOI)")
    p_cat.set_defaults(func=cmd_catalog)

    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI 主入口。

    Args:
        argv: 命令行参数列表，None 时读取 sys.argv。

    Returns:
        退出码（0 成功）。
    """
    parser = _build_parser()
    args = parser.parse_args(argv)
    return args.func(args)
