"""一体化流水线包。

提供端到端自动布局布线 + 仿真回馈一体化流水线，以及 CLI 入口函数
``cmd_run`` / ``cmd_catalog`` / ``cmd_train``。

来源:
- Apollo arXiv 2025: https://arxiv.org/html/2504.18813v1
- LiDAR ISPD'25: https://dl.acm.org/doi/pdf/10.1145/3698364.3705355
- OptoSynthesizer arXiv 2026: https://arxiv.org/pdf/2604.15493v1
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from polaris.pdk.catalog import build_default_catalog

logger = logging.getLogger(__name__)

__all__ = ["cmd_run", "cmd_catalog", "cmd_train"]


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
        args: 参数对象，需包含属性 netlist/output/checkpoint/canvas_w/canvas_h/
            grid_size/hidden_dim。

    Returns:
        0 表示成功。
    """
    from polaris.engine.netlist import load_netlist

    net, devices, _ = load_netlist(args.netlist)
    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)
    fp = _run_floorplan(net, devices, args.canvas_w, args.canvas_h, args.grid_size)
    r_env = _run_routing(net, fp.state.placements, args.canvas_w, args.canvas_h, args.grid_size)
    placements = fp.state.placements
    paths = r_env.state.paths
    _export_layout(out_dir, placements, paths)
    _write_report(out_dir, net, devices, placements, paths)
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
