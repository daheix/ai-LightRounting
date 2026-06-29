"""TrainingPipeline 真实 RL 训练流程测试（Task P0）。

验证 TrainingPipeline 接入真正的 PPO 训练（train_floorplan/train_routing），
而非伪实现（反复跑 pipeline.run + 记录奖励）。

测试覆盖：
- TrainingConfig 默认值与字段设置
- TrainingPipeline 初始化
- 仅布局训练（调用 train_floorplan）
- 仅布线训练（调用 train_routing）
- 完整训练（布局+布线+校验）
- 检查点保存与内容验证
- TrainingResult 字段完整性

来源:
- PPO 标准训练循环: https://scalable-ai.eecs.berkeley.edu/assets/lecture_slides/lecture_15.pdf
- CleanRL ppo.py: https://github.com/vwxyzjn/cleanrl
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from polaris.pipeline.training import TrainingConfig, TrainingPipeline, TrainingResult

# 真实基准数据目录（含 71 个基准电路）
BENCHMARK_DIR = "data/benchmarks"


def _make_small_config(tmp_path: Path, **overrides) -> TrainingConfig:
    """构造小规模训练配置（2 episodes，快速完成）。"""
    defaults = dict(
        benchmark_dir=BENCHMARK_DIR,
        num_episodes=2,
        rollout_steps=16,
        canvas_w=300.0,
        canvas_h=300.0,
        grid_size=10.0,
        hidden_dim=16,
        save_dir=str(tmp_path / "ckpt"),
        calibrate_every=1,
    )
    defaults.update(overrides)
    return TrainingConfig(**defaults)


def test_training_config_defaults():
    """TrainingConfig 默认值应正确。"""
    cfg = TrainingConfig()
    assert cfg.benchmark_dir == "data/benchmarks"
    assert cfg.num_episodes == 50
    assert cfg.hidden_dim == 64
    assert cfg.lr == 3e-4
    assert cfg.train_floorplan_enabled is True
    assert cfg.train_routing_enabled is True
    assert cfg.sim_feedback is False
    assert cfg.seed == 42


def test_training_pipeline_init():
    """TrainingPipeline 应能正确初始化。"""
    pipeline = TrainingPipeline()
    assert pipeline.config is not None
    assert pipeline.pipeline is not None


def test_training_pipeline_floorplan_only(tmp_path):
    """仅训练布局 agent，应调用真正的 train_floorplan 并返回日志。"""
    cfg = _make_small_config(tmp_path, train_floorplan_enabled=True, train_routing_enabled=False)
    pipeline = TrainingPipeline(cfg)
    result = pipeline.train()

    assert result.episodes_completed == 2
    # 布局训练应产生日志（真正的 PPO 训练，非伪实现）
    assert len(result.floorplan_logs) == 2
    assert result.routing_logs == []
    # 每条日志应含 PPO 训练指标
    for log in result.floorplan_logs:
        assert "episode" in log
        assert "ep_reward" in log
        assert "policy_loss" in log
        assert "value_loss" in log
    # 检查点文件应存在
    assert (tmp_path / "ckpt" / "floorplan_final.json").exists()
    assert (tmp_path / "ckpt" / "floorplan_log.json").exists()


def test_training_pipeline_routing_only(tmp_path):
    """仅训练布线 agent，应调用真正的 train_routing 并返回日志。"""
    cfg = _make_small_config(tmp_path, train_floorplan_enabled=False, train_routing_enabled=True)
    pipeline = TrainingPipeline(cfg)
    result = pipeline.train()

    assert result.episodes_completed == 2
    assert result.floorplan_logs == []
    # 布线训练应产生日志（真正的 PPO 训练）
    assert len(result.routing_logs) == 2
    for log in result.routing_logs:
        assert "episode" in log
        assert "ep_reward" in log
        assert "policy_loss" in log
    # 检查点文件应存在
    assert (tmp_path / "ckpt" / "routing_final.json").exists()
    assert (tmp_path / "ckpt" / "routing_log.json").exists()


def test_training_pipeline_full(tmp_path):
    """完整训练：布局+布线+校验，应返回完整 TrainingResult。"""
    cfg = _make_small_config(tmp_path)
    pipeline = TrainingPipeline(cfg)
    result = pipeline.train()

    assert result.episodes_completed == 2
    # 布局与布线都应有日志
    assert len(result.floorplan_logs) == 2
    assert len(result.routing_logs) == 2
    # 校准结果应存在（基准目录存在）
    assert result.calibration_result is not None
    assert result.calibration_result.total_items > 0
    # 检查点应保存
    assert Path(result.checkpoint_path).exists()


def test_training_pipeline_checkpoint_content(tmp_path):
    """检查点文件应含完整训练与校准信息。"""
    cfg = _make_small_config(tmp_path)
    pipeline = TrainingPipeline(cfg)
    result = pipeline.train()

    ckpt_path = Path(result.checkpoint_path)
    assert ckpt_path.exists()
    ckpt = json.loads(ckpt_path.read_text(encoding="utf-8"))
    assert ckpt["episodes"] == 2
    assert "best_reward" in ckpt
    assert "avg_loss_db" in ckpt
    assert "calibration_passed" in ckpt
    assert "calibration_passed_items" in ckpt
    assert "calibration_total_items" in ckpt
    assert "calibration_max_error_db" in ckpt
    assert "calibration_mean_error_db" in ckpt


def test_training_result_fields():
    """TrainingResult 应含所有必要字段。"""
    result = TrainingResult()
    assert result.episodes_completed == 0
    assert result.best_reward == 0.0
    assert result.avg_loss_db == 0.0
    assert result.calibration_passed is False
    assert result.calibration_result is None
    assert result.checkpoint_path == ""
    assert result.floorplan_logs == []
    assert result.routing_logs == []


def test_training_pipeline_no_benchmarks(tmp_path):
    """基准目录不存在时应 raise FileNotFoundError（R03: 禁止 fall-back）。

    回归 #v3.3-P-3：原实现 fall-back 返回空 TrainingResult 掩盖配置错误，
    现已修正为 raise。本测试固化修正后行为，防止 fall-back 复发。
    """
    cfg = _make_small_config(tmp_path, benchmark_dir=str(tmp_path / "nonexistent"))
    pipeline = TrainingPipeline(cfg)
    with pytest.raises(FileNotFoundError, match="基准目录不存在"):
        pipeline.train()


def test_training_pipeline_sim_feedback(tmp_path):
    """启用 sim_feedback 时布局训练应记录约束违规数。"""
    cfg = _make_small_config(
        tmp_path,
        train_floorplan_enabled=True,
        train_routing_enabled=False,
        sim_feedback=True,
    )
    pipeline = TrainingPipeline(cfg)
    result = pipeline.train()
    assert len(result.floorplan_logs) == 2
    # sim_feedback 启用时日志应含 sim_violations 字段
    for log in result.floorplan_logs:
        assert "sim_violations" in log
        assert isinstance(log["sim_violations"], int)


def test_training_pipeline_best_reward(tmp_path):
    """best_reward 应为布局与布线日志中的最大 ep_reward。"""
    cfg = _make_small_config(tmp_path)
    pipeline = TrainingPipeline(cfg)
    result = pipeline.train()

    all_rewards = []
    all_rewards.extend(lg["ep_reward"] for lg in result.floorplan_logs)
    all_rewards.extend(lg["ep_reward"] for lg in result.routing_logs)
    expected_best = max(all_rewards) if all_rewards else 0.0
    assert result.best_reward == pytest.approx(expected_best, rel=1e-9)
