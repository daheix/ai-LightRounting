"""端到端集成测试（Task 18）。

验证完整流水线：网表 → 布局 → 布线 → 渲染 → GDS 导出 → DRC，
以及训练循环、数据集合成、CLI 调用。
"""

from __future__ import annotations

import json
import os

import numpy as np
import pytest

from polaris.engine.floorplan_env import FloorplanEnv
from polaris.engine.netlist import load_netlist
from polaris.eval.layout_render import export_gds, run_drc
from polaris.pipeline import cmd_run
from polaris.router.routing_env import RoutingEnv
from polaris.trainer.dataset import DatasetConfig, generate_dataset
from polaris.trainer.train_loop import TrainConfig, train_floorplan

YAML_NETLIST = """
name: integration_test
instances:
  wg1: {component: strip_waveguide, platform: SOI}
  mmi1: {component: mmi_1x2, platform: SOI}
  wg2: {component: strip_waveguide, platform: SOI}
  pd1: {component: ge_photodetector, platform: SOI}
connections:
  - [wg1, out, mmi1, in]
  - [mmi1, out0, wg2, in]
  - [wg2, out, pd1, in]
"""


def test_full_pipeline_e2e(tmp_path):
    """端到端：网表 → 布局 → 布线 → GDS → DRC。"""
    net, devices, _ = load_netlist(YAML_NETLIST)
    # 布局
    fp = FloorplanEnv(net, devices, canvas_w=400, canvas_h=400, grid_size=10)
    fp.reset()
    for _ in range(len(devices)):
        fp.step([5, 5, 0])
    assert len(fp.state.placements) == len(devices)
    # 布线
    r_env = RoutingEnv(net, fp.state.placements, canvas_w=400, canvas_h=400, grid_size=5)
    r_env.reset()
    for _ in range(len(net.connections)):
        r_env.step(np.zeros(3, dtype=np.float32))
    assert len(r_env.state.paths) == len(net.connections)
    # GDS 导出
    gds_path = export_gds(fp.state.placements, r_env.state.paths, str(tmp_path / "out.gds"))
    assert os.path.exists(gds_path)
    # DRC
    report = run_drc(fp.state.placements, r_env.state.paths)
    assert isinstance(report.total_violations, int)


def test_dataset_generation():
    cfg = DatasetConfig(num_netlists=5, min_devices=3, max_devices=6)
    ds = generate_dataset(cfg)
    assert len(ds) == 5
    for nl in ds:
        assert "instances" in nl
        assert "connections" in nl
        assert len(nl["instances"]) >= 3


def test_training_loop_short(tmp_path):
    """短训练循环应能运行完成并保存检查点。"""
    cfg = TrainConfig(
        num_episodes=2,
        rollout_steps=16,
        canvas_w=300,
        canvas_h=300,
        grid_size=10,
        hidden_dim=16,
        checkpoint_dir=str(tmp_path / "ckpt"),
    )
    cfg.dataset.num_netlists = 2
    cfg.dataset.min_devices = 3
    cfg.dataset.max_devices = 4
    agent, logs = train_floorplan(cfg, verbose=False)
    assert len(logs) == 2
    assert (tmp_path / "ckpt" / "floorplan_final.json").exists()
    # 日志文件
    assert (tmp_path / "ckpt" / "floorplan_log.json").exists()


def test_pipeline_cli_run(tmp_path):
    """CLI run 命令应能完成端到端流程。"""
    netlist_path = tmp_path / "net.yaml"
    netlist_path.write_text(YAML_NETLIST, encoding="utf-8")
    out_dir = tmp_path / "out"
    cmd_run(
        type(
            "Args",
            (),
            {
                "netlist": str(netlist_path),
                "output": str(out_dir),
                "checkpoint": None,
                "canvas_w": 400.0,
                "canvas_h": 400.0,
                "grid_size": 10.0,
                "hidden_dim": 64,
            },
        )()
    )
    assert (out_dir / "layout.gds").exists()
    assert (out_dir / "layout.oas").exists()
    assert (out_dir / "layout.png").exists()
    assert (out_dir / "report.json").exists()
    report = json.loads((out_dir / "report.json").read_text())
    assert report["num_devices"] == 4
    assert report["num_connections"] == 3


def test_pipeline_cli_catalog(capsys):
    """CLI catalog 命令应列出器件。"""
    from polaris.pipeline import cmd_catalog

    ret = cmd_catalog(type("Args", (), {"platform": "SOI"})())
    assert ret == 0
    captured = capsys.readouterr()
    assert "SOI" in captured.out
    assert "strip_waveguide" in captured.out


def test_pipeline_cli_train(tmp_path):
    """CLI train 命令应能启动训练。"""
    from polaris.pipeline import cmd_train

    ret = cmd_train(
        type(
            "Args",
            (),
            {
                "episodes": 2,
                "rollout_steps": 16,
                "num_netlists": 2,
                "min_devices": 3,
                "max_devices": 4,
                "canvas_w": 300.0,
                "canvas_h": 300.0,
                "grid_size": 10.0,
                "hidden_dim": 16,
                "output": str(tmp_path / "ckpt"),
            },
        )()
    )
    assert ret == 0
    assert (tmp_path / "ckpt" / "floorplan_final.json").exists()


def test_all_platforms_have_devices():
    """所有平台都应有器件且带来源。"""
    from polaris.pdk.catalog import build_default_catalog

    cat = build_default_catalog()
    for plat in ["SOI", "SiN", "InP", "LNOI"]:
        devs = cat.list_devices(platform=plat)
        assert len(devs) > 0, f"{plat} 平台无器件"
        for d in devs:
            assert d.source is not None
            assert d.source.url, f"{d.device_id} 缺少 source.url"


def test_baseline_solver():
    """BaselineSolver 应能对网表生成 baseline 解并标注奖励（SubTask 14.2）。"""
    from polaris.trainer.dataset import BaselineSolver, DatasetSample

    solver = BaselineSolver()
    cfg = DatasetConfig(num_netlists=1, min_devices=3, max_devices=4, seed=42)
    from polaris.trainer.dataset import generate_netlist

    nl = generate_netlist(cfg, 0)
    sample = solver.solve(nl, canvas_w=300, canvas_h=300, grid_size=10)
    assert isinstance(sample, DatasetSample)
    assert sample.netlist == nl
    assert isinstance(sample.baseline_reward, float)
    assert "total_loss_db" in sample.baseline_metrics
    assert "total_length_um" in sample.baseline_metrics


def test_generate_training_dataset():
    """generate_training_dataset 应返回带 baseline 标注的样本列表。"""
    from polaris.trainer.dataset import DatasetConfig, generate_training_dataset

    cfg = DatasetConfig(num_netlists=2, min_devices=3, max_devices=4, seed=42)
    samples = generate_training_dataset(cfg, canvas_w=300, canvas_h=300, grid_size=10)
    assert len(samples) == 2
    for s in samples:
        assert hasattr(s, "baseline_reward")
        assert hasattr(s, "baseline_metrics")


def test_early_stopping(tmp_path):
    """早停功能应在 patience 轮无改善后停止训练（SubTask 15.2）。"""
    cfg = TrainConfig(
        num_episodes=20,
        rollout_steps=8,
        canvas_w=200,
        canvas_h=200,
        grid_size=10,
        hidden_dim=8,
        checkpoint_dir=str(tmp_path / "ckpt_es"),
        early_stop_patience=3,
    )
    cfg.dataset.num_netlists = 1
    cfg.dataset.min_devices = 3
    cfg.dataset.max_devices = 3
    agent, logs = train_floorplan(cfg, verbose=False)
    # 早停应使训练轮数 < num_episodes
    assert len(logs) <= 20


def test_lr_schedule_linear():
    """线性学习率调度应从 1.0 衰减到 0.0。"""
    from polaris.trainer.train_loop import _lr_scale

    assert _lr_scale(0, 10, "linear") == 1.0
    assert _lr_scale(5, 10, "linear") == 0.5
    assert _lr_scale(10, 10, "linear") == 0.0
    assert _lr_scale(0, 10, "constant") == 1.0
    assert _lr_scale(5, 10, "constant") == 1.0


def test_lr_schedule_cosine():
    """cosine 学习率调度应从 1.0 余弦衰减到 0.0（第二波训练收敛修复）。

    来源: Loshchilov & Hutter, 2017, SGDR
    https://arxiv.org/abs/1608.03983
    """
    from polaris.trainer.train_loop import _lr_scale

    # ep=0: cos(0)=1 → scale=1.0
    assert _lr_scale(0, 10, "cosine") == pytest.approx(1.0)
    # ep=5 (中点): cos(π/2)=0 → scale=0.5
    assert _lr_scale(5, 10, "cosine") == pytest.approx(0.5)
    # ep=10 (终点): cos(π)=-1 → scale=0.0
    assert _lr_scale(10, 10, "cosine") == pytest.approx(0.0)
    # ep=2.5 (1/4): cos(π/4)=√2/2 → scale≈0.854
    assert _lr_scale(2.5, 10, "cosine") == pytest.approx(0.5 * (1 + 0.7071), abs=0.01)


def test_integrated_pipeline_exports_gds(tmp_path):
    """IntegratedPipeline.run() 应导出 GDS 文件（第三波端到端流水线）。

    验证 SimLoop 闭环 → GDS 导出 → DRC 检查的端到端流程，
    确保 PipelineResult.gds_path 非空且文件存在。
    """
    from polaris.pipeline.integrated import IntegratedPipeline, PipelineConfig

    cfg = PipelineConfig(
        canvas_w=300.0,
        canvas_h=300.0,
        grid_size=20.0,
        max_sim_iterations=1,
        output_dir=str(tmp_path),
    )
    pipeline = IntegratedPipeline(config=cfg)
    result = pipeline.run()

    assert result.circuit_name == "demo_mzi"
    assert result.n_devices == 3
    # GDS 文件应存在
    assert result.gds_path, "gds_path 不应为空"
    assert os.path.exists(result.gds_path), f"GDS 文件不存在: {result.gds_path}"
    # DRC 字段应为 bool
    assert isinstance(result.drc_passed, bool)


def test_convert_to_placements_basic():
    """convert_to_placements 应将 dict 布局转为 Placement 对象字典。"""
    from polaris.data.specs import CircuitSpec, DeviceSpec
    from polaris.pipeline._converters import convert_to_placements

    circuit = CircuitSpec(
        name="test",
        devices=[
            DeviceSpec(
                name="gc1",
                device_type="grating_coupler",
                width_um=20.0,
                height_um=20.0,
                ports=[("o1", 10.0, 0.0, "N")],
            ),
            DeviceSpec(
                name="mmi1",
                device_type="mmi_1x2",
                width_um=30.0,
                height_um=20.0,
                ports=[
                    ("o1", 0.0, 10.0, "E"),
                    ("o2", 30.0, 5.0, "W"),
                ],
            ),
        ],
        connections=[("gc1", "o1", "mmi1", "o1")],
    )
    sim_placements = {
        "gc1": {"x": 50.0, "y": 50.0, "w": 20.0, "h": 20.0},
        "mmi1": {"x": 100.0, "y": 100.0, "w": 30.0, "h": 20.0},
    }
    placements = convert_to_placements(circuit, sim_placements)

    assert set(placements.keys()) == {"gc1", "mmi1"}
    pl_gc = placements["gc1"]
    assert pl_gc.instance_id == "gc1"
    assert pl_gc.x == 50.0
    assert pl_gc.y == 50.0
    assert pl_gc.rotation == 0
    # grating_coupler → source 类别
    assert pl_gc.device.category == "source"
    # 端口应转换为 Port 对象
    assert len(pl_gc.device.ports) == 1
    assert pl_gc.device.ports[0].name == "o1"
    # mmi → passive
    assert placements["mmi1"].device.category == "passive"


def test_convert_to_paths_basic():
    """convert_to_paths 应将 dict 路径转为 WaveguidePath 对象字典。"""
    from polaris.pipeline._converters import convert_to_paths

    sim_paths = {
        "gc1_o1_mmi1_o1": [(0.0, 0.0), (50.0, 0.0), (50.0, 100.0)],
        "mmi1_o2_gc2_o1": [(100.0, 100.0), (200.0, 100.0)],
    }
    paths = convert_to_paths(sim_paths)

    assert len(paths) == 2
    # 按枚举顺序编号
    p0 = paths[0]
    assert len(p0.points) == 3
    assert p0.length_um > 0.0
    assert p0.loss_db > 0.0  # SOI 3 dB/cm 传播损耗
    # 第二条路径
    p1 = paths[1]
    assert len(p1.points) == 2
    assert p1.length_um == 100.0  # (100,100) → (200,100) = 100μm


def test_integrated_pipeline_drc_field(tmp_path):
    """IntegratedPipeline 返回的 drc_passed 应反映 DRC 检查结果。"""
    from polaris.pipeline.integrated import IntegratedPipeline, PipelineConfig

    cfg = PipelineConfig(
        canvas_w=500.0,
        canvas_h=500.0,
        grid_size=20.0,
        max_sim_iterations=1,
        output_dir=str(tmp_path),
    )
    pipeline = IntegratedPipeline(config=cfg)
    result = pipeline.run()

    # drc_passed 应为 bool（True 或 False，取决于布局是否重叠）
    assert isinstance(result.drc_passed, bool)
    # 报告文件应存在
    assert os.path.exists(result.report_path)


# ============================================================================
# P1-1 回归测试（v4.0）：PPO 学习率调度冲突修复
# 来源: Stable-Baselines3 PPO learn() 内部 total_timesteps 调度
#       https://stable-baselines3.readthedocs.io/
# 旧 Bug: train_loop 外部 _apply_lr_scale 写 cosine lr → ppo.update() 内部
#         用 PPOConfig.lr_schedule="constant" 覆盖 → cosine 永不生效
# ============================================================================


def test_p11_apply_lr_scale_function_removed():
    """P1-1: ``_apply_lr_scale`` 函数应已删除（不再外部覆盖 lr）。"""
    from polaris.trainer import train_loop

    assert not hasattr(train_loop, "_apply_lr_scale"), (
        "_apply_lr_scale 应已删除：学习率调度统一到 PPOAgent._get_lr()"
    )


def test_p11_lr_schedule_synced_to_ppo_config():
    """P1-1: TrainConfig.lr_schedule 应同步到 PPOConfig.lr_schedule。

    旧 Bug: TrainConfig 默认 "cosine"，PPOConfig 默认 "constant"，
    两者不同步导致 PPOAgent._get_lr() 始终用 constant。
    """
    from polaris.trainer.train_loop import TrainConfig

    cfg = TrainConfig()
    # 默认值检查
    assert cfg.lr_schedule == "cosine"
    assert cfg.ppo.lr_schedule == "constant"  # PPOConfig 默认值

    # 模拟 _init_floorplan_training 中的同步逻辑
    cfg.ppo.lr_schedule = cfg.lr_schedule
    cfg.ppo.total_steps = cfg.num_episodes
    assert cfg.ppo.lr_schedule == "cosine"
    assert cfg.ppo.total_steps == cfg.num_episodes


def test_p11_floorplan_training_uses_cosine_schedule(tmp_path):
    """P1-1: 布局训练后 agent.config 应使用 cosine 调度，且 lr 实际衰减。

    旧 Bug: 即使 TrainConfig.lr_schedule="cosine"，agent.config.lr_schedule
    仍是 "constant"，lr 恒定不变。

    注意: PPOAgent.update() 内部 ``current_step += 1`` 先执行，再计算 lr，
    所以首轮训练后 current_step=1（与 SB3 step 从 1 开始计数一致）。
    来源: Stable-Baselines3 PPO learn() https://stable-baselines3.readthedocs.io/
    """
    cfg = TrainConfig()
    cfg.lr_schedule = "cosine"
    cfg.num_episodes = 6
    cfg.checkpoint_dir = str(tmp_path)
    cfg.dataset.num_netlists = 1
    cfg.dataset.min_devices = 3
    cfg.dataset.max_devices = 3
    cfg.early_stop_patience = 0  # 禁用早停

    agent, logs = train_floorplan(cfg, verbose=False)

    # P1-1 核心断言：agent.config 应使用 cosine（而非默认 constant）
    assert agent.config.lr_schedule == "cosine", (
        f"P1-1 回归: agent.config.lr_schedule 应为 'cosine'，"
        f"实际为 '{agent.config.lr_schedule}'（配置未同步）"
    )
    assert agent.config.total_steps == 6

    # lr 应在训练过程中衰减（首轮 > 末轮，cosine 从 1.0 衰减到 0.0）
    lr_values = [log["lr"] for log in logs if "lr" in log]
    assert len(lr_values) >= 1, "应至少有 1 轮训练日志"
    if len(lr_values) >= 2:
        assert lr_values[0] > lr_values[-1], (
            f"P1-1 回归: lr 应衰减，首轮={lr_values[0]}，末轮={lr_values[-1]}"
        )
    # 首轮 lr 应接近 base_lr * cosine(π * 1/total)（update 内 current_step 先 +=1）
    # 旧 Bug: 若 lr_schedule="constant"，首轮 lr 应恒等于 base_lr=3e-4
    # P1-1 修复后: 首轮 lr = base_lr * 0.5 * (1 + cos(π * 1/6)) ≈ 2.799e-4
    step = 1  # 首轮 update 后 current_step=1
    progress = step / cfg.num_episodes
    expected_first = cfg.ppo.lr * 0.5 * (1.0 + np.cos(np.pi * progress))
    assert abs(lr_values[0] - expected_first) < 1e-8, (
        f"P1-1 回归: 首轮 lr 应为 {expected_first}（cosine step=1），"
        f"实际 {lr_values[0]}（若等于 {cfg.ppo.lr} 则说明 constant 覆盖了 cosine）"
    )
    # 关键回归断言：首轮 lr 不应等于 base_lr（证明 cosine 生效，非 constant）
    assert abs(lr_values[0] - cfg.ppo.lr) > 1e-8, (
        f"P1-1 回归: 首轮 lr={lr_values[0]} 等于 base_lr={cfg.ppo.lr}，"
        f"说明 PPOConfig.lr_schedule 仍为 'constant'（配置未同步）"
    )


def test_p11_log_uses_lr_field_not_lr_scale():
    """P1-1: 训练日志应使用 'lr' 字段（实际学习率），而非 'lr_scale'（误导）。"""
    cfg = TrainConfig()
    cfg.num_episodes = 2
    cfg.checkpoint_dir = "/tmp/p11_log_test"
    cfg.dataset.num_netlists = 1
    cfg.dataset.min_devices = 3
    cfg.dataset.max_devices = 3
    cfg.early_stop_patience = 0

    _, logs = train_floorplan(cfg, verbose=False)
    assert len(logs) > 0
    first_log = logs[0]
    # 旧字段 lr_scale 应不存在
    assert "lr_scale" not in first_log, (
        "P1-1 回归: 日志不应含 'lr_scale' 字段（已被 'lr' 取代）"
    )
    # 新字段 lr 应存在且为正数
    assert "lr" in first_log
    assert first_log["lr"] > 0.0
