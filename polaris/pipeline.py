"""端到端流水线 CLI（Task 17）。

提供命令行入口，串联：网表解析 → 布局（PPO/随机）→ 布线 → 渲染 → GDS/OASIS 导出 → DRC 报告。

用法::

    python -m polaris.pipeline run --netlist circuit.yaml --output out/
    python -m polaris.pipeline train --episodes 50 --output checkpoints/
    python -m polaris.pipeline catalog --platform SOI
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from polaris.engine.floorplan_env import FloorplanEnv
from polaris.engine.netlist import load_netlist
from polaris.eval.layout_render import (
    export_gds,
    export_oasis,
    render_layout,
    run_drc,
)
from polaris.router.routing_env import RoutingEnv
from polaris.trainer.train_loop import TrainConfig, train_floorplan


@dataclass
class CanvasConfig:
    """画布尺寸与网格配置。

    Attributes:
        canvas_w: 画布宽（μm）。
        canvas_h: 画布高（μm）。
        grid_size: 网格大小（μm）。
    """

    canvas_w: float = 1000.0
    canvas_h: float = 1000.0
    grid_size: float = 10.0


def _place_with_agent(env, agent, devices, obs_dim, action_dim):
    """用 PPO 智能体进行布局，返回放置结果。"""
    from polaris.trainer.train_loop import (
        _discretize_floorplan_action,
        _obs_to_vector,
        _pad_obs,
    )

    for _ in range(len(devices)):
        obs = env._obs() if env.state.placements else env.reset()[0]
        obs_vec = _pad_obs(_obs_to_vector(obs), obs_dim)
        action, _, _ = agent.get_action(obs_vec)
        disc_action = _discretize_floorplan_action(action, env, action_dim)
        _, _, term, _, _ = env.step(disc_action.tolist())
        if term:
            break
    return env.state.placements


def _place_random(env, devices):
    """随机布局（避免重叠的贪心放置），返回放置结果。"""
    for _ in range(len(devices)):
        best = None
        best_reward = -1e9
        for _ in range(20):
            a = env.action_space.sample()
            # 备份状态
            saved = dict(env.state.placements)
            saved_idx = env._step_idx
            _, r, _, _, _ = env.step(a)
            if r > best_reward:
                best_reward = r
                best = a
            # 回退
            env.state.placements = saved
            env._step_idx = saved_idx
        env.step(best)
    return env.state.placements


def _place(net, devices, canvas_cfg: CanvasConfig, agent=None):
    """布局阶段（用 agent 或随机）。"""
    env = FloorplanEnv(
        net,
        devices,
        canvas_w=canvas_cfg.canvas_w,
        canvas_h=canvas_cfg.canvas_h,
        grid_size=canvas_cfg.grid_size,
    )
    env.reset()
    if agent is not None:
        from polaris.trainer.train_loop import _obs_to_vector

        obs_dim = _obs_to_vector(env.reset()[0]).shape[0]
        action_dim = int(np.prod(env.action_space.shape))
        return _place_with_agent(env, agent, devices, obs_dim, action_dim)
    return _place_random(env, devices)


def _route(net, placements, canvas_w, canvas_h, grid_size):
    """布线阶段。"""
    env = RoutingEnv(net, placements, canvas_w=canvas_w, canvas_h=canvas_h, grid_size=grid_size)
    env.reset()
    for _ in range(len(net.connections)):
        obs, _, term, _, _ = env.step(np.zeros(3, dtype=np.float32))
        if term:
            break
    return env.state.paths, env.congestion_heatmap(), env.total_metrics()


def _load_agent_if_any(args, net, devices):
    """根据 checkpoint 加载 PPO 智能体（无则返回 None）。"""
    if not args.checkpoint:
        return None
    from polaris.trainer.train_loop import _obs_to_vector, load_agent

    env0 = FloorplanEnv(
        net,
        devices,
        canvas_w=args.canvas_w,
        canvas_h=args.canvas_h,
        grid_size=args.grid_size,
    )
    obs_dim = _obs_to_vector(env0.reset()[0]).shape[0]
    action_dim = int(np.prod(env0.action_space.shape))
    agent = load_agent(args.checkpoint, obs_dim, action_dim, args.hidden_dim)
    print(f"      加载检查点: {args.checkpoint}")
    return agent


def _export_layout(out: Path, placements, paths, congestion, net):
    """渲染版图并导出 GDS/OASIS。"""
    render_layout(
        placements,
        paths,
        congestion,
        title=f"PoLaRIS - {net.name}",
        save_path=str(out / "layout.png"),
    )
    gds_path = export_gds(placements, paths, str(out / "layout.gds"))
    oasis_path = export_oasis(placements, paths, str(out / "layout.oas"))
    print(f"      GDS: {gds_path}")
    print(f"      OASIS: {oasis_path}")


def _run_drc_stage(placements, paths):
    """执行 DRC 检查并打印结果，返回 DRC 报告。"""
    drc = run_drc(placements, paths)
    status = "PASSED" if drc.passed else f"FAILED ({drc.total_violations} violations)"
    print(f"      DRC: {status}")
    if drc.details:
        for d in drc.details[:10]:
            print(f"        - {d}")
    return drc


def _save_report(out: Path, net, devices, metrics, drc):
    """保存指标报告 JSON。"""
    report = {
        "netlist": net.name,
        "num_devices": len(devices),
        "num_connections": len(net.connections),
        "routing_metrics": metrics,
        "drc": {
            "passed": drc.passed,
            "total_violations": drc.total_violations,
            "details": drc.details,
        },
    }
    (out / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\n报告已保存: {out / 'report.json'}")


def cmd_run(args):
    """端到端运行：网表 → 布局 → 布线 → 渲染 → 导出 → DRC。"""
    net, devices, _ = load_netlist(args.netlist)
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    print(f"[1/5] 加载网表: {net.name} ({len(devices)} 器件, {len(net.connections)} 连接)")

    agent = _load_agent_if_any(args, net, devices)

    print("[2/5] 布局...")
    canvas_cfg = CanvasConfig(args.canvas_w, args.canvas_h, args.grid_size)
    placements = _place(net, devices, canvas_cfg, agent)
    print(f"      放置 {len(placements)} 器件")

    print("[3/5] 布线...")
    paths, congestion, metrics = _route(
        net, placements, args.canvas_w, args.canvas_h, args.grid_size
    )
    print(f"      布线 {len(paths)} 连接, 总损耗 {metrics['total_loss_db']:.3f} dB")

    print("[4/5] 渲染与导出...")
    _export_layout(out, placements, paths, congestion, net)

    print("[5/5] DRC 检查...")
    drc = _run_drc_stage(placements, paths)
    _save_report(out, net, devices, metrics, drc)
    return 0 if drc.passed else 1


def cmd_train(args):
    """训练 PPO 智能体。"""
    print(f"训练布局 PPO 智能体 ({args.episodes} episodes)...")
    cfg = TrainConfig(
        num_episodes=args.episodes,
        rollout_steps=args.rollout_steps,
        canvas_w=args.canvas_w,
        canvas_h=args.canvas_h,
        grid_size=args.grid_size,
        hidden_dim=args.hidden_dim,
        checkpoint_dir=args.output,
    )
    cfg.dataset.num_netlists = args.num_netlists
    cfg.dataset.min_devices = args.min_devices
    cfg.dataset.max_devices = args.max_devices
    agent, logs = train_floorplan(cfg, verbose=True)
    print(f"\n训练完成，检查点: {Path(args.output) / 'floorplan_final.json'}")
    return 0


def cmd_catalog(args):
    """列出器件目录。"""
    from polaris.pdk.catalog import build_default_catalog

    cat = build_default_catalog()
    if args.platform:
        devs = cat.list_devices(platform=args.platform)
    else:
        devs = cat.list_devices()
    print(f"共 {len(devs)} 器件:")
    for dev in devs:
        src = dev.source.url if dev.source else "NO SOURCE"
        print(f"  [{dev.platform:4s}] {dev.category:8s} {dev.name:35s} <- {src}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="polaris",
        description="PoLaRIS 光电子 AI 智能布局布线引擎",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # run
    p_run = sub.add_parser("run", help="端到端运行")
    p_run.add_argument("--netlist", required=True, help="网表文件路径 (YAML/JSON)")
    p_run.add_argument("--output", "-o", default="out", help="输出目录")
    p_run.add_argument("--checkpoint", default=None, help="PPO 检查点路径")
    p_run.add_argument("--canvas-w", type=float, default=1000.0)
    p_run.add_argument("--canvas-h", type=float, default=1000.0)
    p_run.add_argument("--grid-size", type=float, default=10.0)
    p_run.add_argument("--hidden-dim", type=int, default=64)
    p_run.set_defaults(func=cmd_run)

    # train
    p_train = sub.add_parser("train", help="训练 PPO 智能体")
    p_train.add_argument("--episodes", type=int, default=50)
    p_train.add_argument("--rollout-steps", type=int, default=64)
    p_train.add_argument("--num-netlists", type=int, default=50)
    p_train.add_argument("--min-devices", type=int, default=3)
    p_train.add_argument("--max-devices", type=int, default=12)
    p_train.add_argument("--canvas-w", type=float, default=1000.0)
    p_train.add_argument("--canvas-h", type=float, default=1000.0)
    p_train.add_argument("--grid-size", type=float, default=10.0)
    p_train.add_argument("--hidden-dim", type=int, default=64)
    p_train.add_argument("--output", "-o", default="checkpoints")
    p_train.set_defaults(func=cmd_train)

    # catalog
    p_cat = sub.add_parser("catalog", help="列出器件目录")
    p_cat.add_argument("--platform", default=None, help="过滤平台 (SOI/SiN/InP/LNOI)")
    p_cat.set_defaults(func=cmd_catalog)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
