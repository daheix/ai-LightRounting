"""模仿学习 + RL 微调 4 阶段流水线端到端测试（规则 10）。

测试 scripts/train_il_pipeline.py 的 BC 预训练、RL 微调、流水线汇总、
CLI 参数解析、检查点持久化等完整流程。

来源:
- Pomerleau, NeurIPS 1989, ALVINN (BC)
  https://papers.nips.cc/paper/95-alvinn-an-autonomous-land-vehicle-in-a-neural-network
- Bengio et al., "Curriculum Learning", ICML 2009
  https://dl.acm.org/doi/abs/10.1145/1553374.1553380
- Schulman et al., 2017, PPO https://arxiv.org/abs/1707.06347
- pytest 最佳实践: https://docs.pytest.org/en/stable/explanation/goodpractices.html
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from il_rl_loops import (  # noqa: E402
    _select_lidar_benchmark,
    run_gnn_rl_loop,
    run_real_rl_loop,
)
from train_il_pipeline import (  # noqa: E402
    PipelineConfig,
    StageResult,
    _find_level,
    args_to_config,
    parse_args,
    run_bc_pretrain,
    run_rl_finetune,
    save_pipeline_summary,
)

from polaris.data.variant_generator import CURRICULUM_LEVELS  # noqa: E402
from polaris.trainer.expert_dataset import ACTION_DIM, OBS_DIM  # noqa: E402
from polaris.trainer.ppo_torch import PPOAgent  # noqa: E402

EXPERT_DIR = ROOT / "data" / "expert_demos"


# ---------------------------------------------------------------------------
# PipelineConfig / StageResult 数据类
# ---------------------------------------------------------------------------


def test_pipeline_config_defaults() -> None:
    """测试 PipelineConfig 默认值。"""
    cfg = PipelineConfig()
    assert cfg.bc_epochs == 50
    assert cfg.small_episodes == 500
    assert cfg.medium_episodes == 1000
    assert cfg.large_episodes == 2000
    assert cfg.hidden_dim == 64
    assert cfg.lr == 3e-4
    assert cfg.batch_size == 16
    assert cfg.seed == 42
    assert cfg.output_dir == "checkpoints/il_pipeline"
    assert cfg.expert_data_dir == "data/expert_demos"


def test_stage_result_defaults() -> None:
    """测试 StageResult 默认值。"""
    r = StageResult("test")
    assert r.stage_name == "test"
    assert r.episodes == 0
    assert r.final_loss == 0.0
    assert r.final_reward == 0.0
    assert r.checkpoint_path == ""


# ---------------------------------------------------------------------------
# _find_level 课程级别查找
# ---------------------------------------------------------------------------


def test_find_level_small() -> None:
    """测试查找 small 级别。"""
    lv = _find_level("small")
    assert lv is not None
    assert lv.name == "small"
    assert lv.n_devices_min == 5
    assert lv.n_devices_max == 10


def test_find_level_medium() -> None:
    """测试查找 medium 级别。"""
    lv = _find_level("medium")
    assert lv is not None
    assert lv.name == "medium"
    assert lv.n_devices_min == 20


def test_find_level_large() -> None:
    """测试查找 large 级别。"""
    lv = _find_level("large")
    assert lv is not None
    assert lv.name == "large"
    assert lv.n_devices_min == 80


def test_find_level_xlarge() -> None:
    """测试查找 xlarge 级别。"""
    lv = _find_level("xlarge")
    assert lv is not None
    assert lv.name == "xlarge"
    assert lv.n_devices_min == 150


def test_find_level_not_found() -> None:
    """测试查找不存在的级别返回 None。"""
    assert _find_level("nonexistent") is None


def test_curriculum_levels_sorted() -> None:
    """测试课程级别按器件数升序排列。"""
    mins = [lv.n_devices_min for lv in CURRICULUM_LEVELS]
    assert mins == sorted(mins)


# ---------------------------------------------------------------------------
# parse_args / args_to_config CLI 参数解析
# ---------------------------------------------------------------------------


def test_parse_args_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    """测试 CLI 参数默认值。"""
    monkeypatch.setattr("sys.argv", ["train_il_pipeline.py"])
    args = parse_args()
    assert args.stage == "all"
    assert args.bc_epochs == 50
    assert args.small_episodes == 500
    assert args.medium_episodes == 1000
    assert args.large_episodes == 2000
    assert args.hidden_dim == 64
    assert args.lr == 3e-4
    assert args.batch_size == 16
    assert args.seed == 42


def test_parse_args_custom(monkeypatch: pytest.MonkeyPatch) -> None:
    """测试 CLI 参数自定义值。"""
    monkeypatch.setattr(
        "sys.argv",
        [
            "train_il_pipeline.py",
            "--stage",
            "bc-only",
            "--bc-epochs",
            "10",
            "--small-episodes",
            "100",
            "--seed",
            "123",
        ],
    )
    args = parse_args()
    assert args.stage == "bc-only"
    assert args.bc_epochs == 10
    assert args.small_episodes == 100
    assert args.seed == 123


def test_args_to_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """测试 args_to_config 转换。"""
    monkeypatch.setattr(
        "sys.argv",
        [
            "train_il_pipeline.py",
            "--bc-epochs",
            "5",
            "--seed",
            "99",
            "--output",
            "/tmp/test_cfg",
        ],
    )
    args = parse_args()
    cfg = args_to_config(args)
    assert cfg.bc_epochs == 5
    assert cfg.seed == 99
    assert cfg.output_dir == "/tmp/test_cfg"


# ---------------------------------------------------------------------------
# run_bc_pretrain BC 预训练阶段
# ---------------------------------------------------------------------------


@pytest.fixture
def pipeline_cfg(tmp_path: Path) -> PipelineConfig:
    """流水线配置 fixture（小规模，用于测试）。"""
    return PipelineConfig(
        bc_epochs=2,
        small_episodes=5,
        medium_episodes=5,
        large_episodes=5,
        hidden_dim=32,
        lr=3e-4,
        batch_size=8,
        output_dir=str(tmp_path / "il_pipeline"),
        expert_data_dir=str(EXPERT_DIR),
        seed=42,
    )


def test_run_bc_pretrain(pipeline_cfg: PipelineConfig) -> None:
    """测试 BC 预训练阶段端到端。"""
    agent, result = run_bc_pretrain(pipeline_cfg)
    assert isinstance(agent, PPOAgent)
    assert result.stage_name == "bc"
    assert result.episodes == pipeline_cfg.bc_epochs
    assert result.final_loss > 0.0
    assert result.checkpoint_path != ""
    assert Path(result.checkpoint_path).exists()


def test_run_bc_pretrain_checkpoint_loadable(pipeline_cfg: PipelineConfig) -> None:
    """测试 BC 预训练检查点可重新加载。"""
    agent, result = run_bc_pretrain(pipeline_cfg)
    from polaris.trainer.ppo_buffers import PPOConfig

    loaded = PPOAgent(
        obs_dim=OBS_DIM,
        action_dim=ACTION_DIM,
        config=PPOConfig(lr=pipeline_cfg.lr),
        hidden_dim=pipeline_cfg.hidden_dim,
    )
    loaded.load(result.checkpoint_path)
    assert loaded is not None


# ---------------------------------------------------------------------------
# run_rl_finetune RL 微调阶段
# ---------------------------------------------------------------------------


def test_run_rl_finetune_small(pipeline_cfg: PipelineConfig) -> None:
    """测试 small 级别 RL 微调。"""
    agent, _ = run_bc_pretrain(pipeline_cfg)
    level = _find_level("small")
    assert level is not None
    result = run_rl_finetune(agent, level, 5, pipeline_cfg, "small")
    assert result.stage_name == "small"
    assert result.episodes == 5
    assert result.final_reward != 0.0
    assert Path(result.checkpoint_path).exists()


def test_run_rl_finetune_medium(pipeline_cfg: PipelineConfig) -> None:
    """测试 medium 级别 RL 微调。"""
    agent, _ = run_bc_pretrain(pipeline_cfg)
    level = _find_level("medium")
    assert level is not None
    result = run_rl_finetune(agent, level, 5, pipeline_cfg, "medium")
    assert result.stage_name == "medium"
    assert result.episodes == 5


def test_run_rl_finetune_large(pipeline_cfg: PipelineConfig) -> None:
    """测试 large 级别 RL 微调。"""
    agent, _ = run_bc_pretrain(pipeline_cfg)
    level = _find_level("large")
    assert level is not None
    result = run_rl_finetune(agent, level, 5, pipeline_cfg, "large")
    assert result.stage_name == "large"
    assert result.episodes == 5


# ---------------------------------------------------------------------------
# _run_real_rl_loop 真实 RL 循环（FloorplanEnv + PPO）
# ---------------------------------------------------------------------------


def test_select_lidar_benchmark_small() -> None:
    """测试 small 级别 LiDAR benchmark 选择。"""
    level = _find_level("small")
    assert level is not None
    path = _select_lidar_benchmark(level)
    assert path is not None
    assert Path(path).exists()


def test_select_lidar_benchmark_large() -> None:
    """测试 large 级别 LiDAR benchmark 选择。"""
    level = _find_level("large")
    assert level is not None
    path = _select_lidar_benchmark(level)
    assert path is not None
    assert Path(path).exists()


def test_run_real_rl_loop_basic(pipeline_cfg: PipelineConfig) -> None:
    """测试真实 RL 循环基本功能（FloorplanEnv + PPO）。"""
    agent, _ = run_bc_pretrain(pipeline_cfg)
    level = _find_level("small")
    assert level is not None
    benchmark_path = _select_lidar_benchmark(level)
    assert benchmark_path is not None
    avg_reward = run_real_rl_loop(agent, benchmark_path, 3, pipeline_cfg.seed)
    assert isinstance(avg_reward, float)
    assert np.isfinite(avg_reward)


def test_run_real_rl_loop_reproducible(pipeline_cfg: PipelineConfig) -> None:
    """测试真实 RL 循环可复现性（同种子同结果）。"""
    from polaris.trainer.ppo_buffers import PPOConfig

    _, bc_result = run_bc_pretrain(pipeline_cfg)
    agent1 = PPOAgent(
        obs_dim=OBS_DIM,
        action_dim=ACTION_DIM,
        config=PPOConfig(lr=pipeline_cfg.lr),
        hidden_dim=pipeline_cfg.hidden_dim,
    )
    agent2 = PPOAgent(
        obs_dim=OBS_DIM,
        action_dim=ACTION_DIM,
        config=PPOConfig(lr=pipeline_cfg.lr),
        hidden_dim=pipeline_cfg.hidden_dim,
    )
    agent1.load(bc_result.checkpoint_path)
    agent2.load(bc_result.checkpoint_path)
    level = _find_level("small")
    assert level is not None
    benchmark_path = _select_lidar_benchmark(level)
    assert benchmark_path is not None
    r1 = run_real_rl_loop(agent1, benchmark_path, 3, 42)
    r2 = run_real_rl_loop(agent2, benchmark_path, 3, 42)
    assert abs(r1 - r2) < 1e-6


# ---------------------------------------------------------------------------
# run_gnn_rl_loop GNN-PPO 循环（孤岛#1 打通）
# ---------------------------------------------------------------------------


def test_run_gnn_rl_loop_basic(pipeline_cfg: PipelineConfig) -> None:
    """测试 GNN-PPO RL 循环基本功能（孤岛#1 打通）。"""
    agent, _ = run_bc_pretrain(pipeline_cfg)
    pipeline_cfg.use_gnn = True
    pipeline_cfg.gnn_out_dim = 32
    level = _find_level("small")
    assert level is not None
    benchmark_path = _select_lidar_benchmark(level)
    assert benchmark_path is not None
    avg_reward = run_gnn_rl_loop(agent, benchmark_path, 2, pipeline_cfg)
    assert isinstance(avg_reward, float)
    assert np.isfinite(avg_reward)


def test_run_gnn_rl_loop_reproducible(pipeline_cfg: PipelineConfig) -> None:
    """测试 GNN-PPO RL 循环可复现性（同种子同结果）。"""
    pipeline_cfg.use_gnn = True
    pipeline_cfg.gnn_out_dim = 32
    _, bc_result = run_bc_pretrain(pipeline_cfg)
    from polaris.trainer.ppo_buffers import PPOConfig

    agent1 = PPOAgent(
        obs_dim=OBS_DIM,
        action_dim=ACTION_DIM,
        config=PPOConfig(lr=pipeline_cfg.lr),
        hidden_dim=pipeline_cfg.hidden_dim,
    )
    agent2 = PPOAgent(
        obs_dim=OBS_DIM,
        action_dim=ACTION_DIM,
        config=PPOConfig(lr=pipeline_cfg.lr),
        hidden_dim=pipeline_cfg.hidden_dim,
    )
    agent1.load(bc_result.checkpoint_path)
    agent2.load(bc_result.checkpoint_path)
    level = _find_level("small")
    assert level is not None
    benchmark_path = _select_lidar_benchmark(level)
    assert benchmark_path is not None
    r1 = run_gnn_rl_loop(agent1, benchmark_path, 2, pipeline_cfg)
    r2 = run_gnn_rl_loop(agent2, benchmark_path, 2, pipeline_cfg)
    assert abs(r1 - r2) < 1e-6


def test_pipeline_config_use_gnn_flag() -> None:
    """测试 PipelineConfig.use_gnn 默认值与设置。"""
    cfg = PipelineConfig()
    assert cfg.use_gnn is False
    assert cfg.gnn_out_dim == 64
    cfg.use_gnn = True
    cfg.gnn_out_dim = 128
    assert cfg.use_gnn is True
    assert cfg.gnn_out_dim == 128


def test_parse_args_use_gnn(monkeypatch: pytest.MonkeyPatch) -> None:
    """测试 --use-gnn CLI 参数解析。"""
    monkeypatch.setattr(
        "sys.argv",
        ["train_il_pipeline.py", "--use-gnn", "--gnn-out-dim", "128"],
    )
    args = parse_args()
    assert args.use_gnn is True
    assert args.gnn_out_dim == 128


def test_args_to_config_use_gnn(monkeypatch: pytest.MonkeyPatch) -> None:
    """测试 args_to_config 转换 use_gnn 字段。"""
    monkeypatch.setattr(
        "sys.argv",
        ["train_il_pipeline.py", "--use-gnn"],
    )
    args = parse_args()
    cfg = args_to_config(args)
    assert cfg.use_gnn is True
    assert cfg.gnn_out_dim == 64


# ---------------------------------------------------------------------------
# save_pipeline_summary 流水线汇总
# ---------------------------------------------------------------------------


def test_save_pipeline_summary(tmp_path: Path, pipeline_cfg: PipelineConfig) -> None:
    """测试流水线汇总报告保存。"""
    results = [
        StageResult("bc", 2, 2.81, 0.0, str(tmp_path / "bc.json")),
        StageResult("small", 5, 0.0, -2.97, str(tmp_path / "small.json")),
        StageResult("medium", 5, 0.0, -3.29, str(tmp_path / "medium.json")),
        StageResult("large", 5, 0.0, -2.94, str(tmp_path / "large.json")),
    ]
    save_pipeline_summary(results, pipeline_cfg, tmp_path)
    summary_path = tmp_path / "pipeline_summary.json"
    assert summary_path.exists()
    with summary_path.open(encoding="utf-8") as f:
        data = json.load(f)
    assert "config" in data
    assert "stages" in data
    assert len(data["stages"]) == 4
    assert data["stages"][0]["name"] == "bc"
    assert data["stages"][3]["name"] == "large"
    assert data["config"]["bc_epochs"] == pipeline_cfg.bc_epochs


# ---------------------------------------------------------------------------
# 完整 4 阶段流水线端到端
# ---------------------------------------------------------------------------


def test_full_pipeline_end_to_end(pipeline_cfg: PipelineConfig) -> None:
    """测试完整 4 阶段流水线端到端（BC→small→medium→large）。"""
    results: list[StageResult] = []

    # 阶段1: BC 预训练
    agent, bc_result = run_bc_pretrain(pipeline_cfg)
    results.append(bc_result)
    assert bc_result.stage_name == "bc"
    assert Path(bc_result.checkpoint_path).exists()

    # 阶段2: small RL 微调
    small_level = _find_level("small")
    assert small_level is not None
    small_result = run_rl_finetune(agent, small_level, 5, pipeline_cfg, "small")
    results.append(small_result)
    assert Path(small_result.checkpoint_path).exists()

    # 阶段3: medium RL 微调
    medium_level = _find_level("medium")
    assert medium_level is not None
    medium_result = run_rl_finetune(agent, medium_level, 5, pipeline_cfg, "medium")
    results.append(medium_result)
    assert Path(medium_result.checkpoint_path).exists()

    # 阶段4: large RL 微调
    large_level = _find_level("large")
    assert large_level is not None
    large_result = run_rl_finetune(agent, large_level, 5, pipeline_cfg, "large")
    results.append(large_result)
    assert Path(large_result.checkpoint_path).exists()

    # 保存汇总
    output_dir = Path(pipeline_cfg.output_dir)
    save_pipeline_summary(results, pipeline_cfg, output_dir)
    summary_path = output_dir / "pipeline_summary.json"
    assert summary_path.exists()

    # 验证汇总内容
    with summary_path.open(encoding="utf-8") as f:
        data = json.load(f)
    assert len(data["stages"]) == 4
    stage_names = [s["name"] for s in data["stages"]]
    assert stage_names == ["bc", "small", "medium", "large"]


def test_pipeline_checkpoints_persist(pipeline_cfg: PipelineConfig) -> None:
    """测试流水线各阶段检查点持久化。"""
    agent, bc_result = run_bc_pretrain(pipeline_cfg)
    bc_ckpt = Path(bc_result.checkpoint_path)
    assert bc_ckpt.exists()
    assert bc_ckpt.stat().st_size > 0

    small_level = _find_level("small")
    assert small_level is not None
    small_result = run_rl_finetune(agent, small_level, 3, pipeline_cfg, "small")
    small_ckpt = Path(small_result.checkpoint_path)
    assert small_ckpt.exists()
    assert small_ckpt.stat().st_size > 0
