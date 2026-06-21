"""P1-4 并行 rollout 采集器测试（第20轮 分布式训练基础）。

验证多环境并行采集接口的正确性与大规模训练配置。

来源: commercial_gap_analysis.md P1-4 无分布式训练与 GPU 加速
"""

from __future__ import annotations

import pytest

from polaris.data.data_loader import (
    circuit_spec_to_netlist_dict,
    generate_synthetic_benchmark,
)
from polaris.trainer.parallel_rollout import (
    ParallelRolloutConfig,
    collect_floorplan_rollout_parallel,
    collect_routing_rollout_parallel,
    effective_batch_size,
    make_large_scale_train_config,
)
from polaris.trainer.train_loop import TrainConfig


class TestParallelRolloutConfig:
    """并行 rollout 配置测试。"""

    def test_default_config(self):
        """默认配置：4 envs × 125 steps = 500 总步数。"""
        cfg = ParallelRolloutConfig()
        assert cfg.num_envs == 4
        assert cfg.rollout_steps_per_env == 125
        assert cfg.total_rollout_steps == 500

    def test_custom_config(self):
        """自定义配置：8 envs × 64 steps = 512 总步数。"""
        cfg = ParallelRolloutConfig(num_envs=8, rollout_steps_per_env=64)
        assert cfg.num_envs == 8
        assert cfg.rollout_steps_per_env == 64
        assert cfg.total_rollout_steps == 512

    def test_single_env_config(self):
        """单环境配置：1 env × 500 steps = 500 总步数。"""
        cfg = ParallelRolloutConfig(num_envs=1, rollout_steps_per_env=500)
        assert cfg.total_rollout_steps == 500

    def test_frozen_dataclass(self):
        """ParallelRolloutConfig 是 frozen dataclass。"""
        cfg = ParallelRolloutConfig()
        with pytest.raises(AttributeError):
            cfg.num_envs = 8  # type: ignore[misc]


class TestLargeScaleConfig:
    """大规模训练配置工厂测试。"""

    def test_default_large_scale_config(self):
        """默认大规模配置：rollout_steps=500。"""
        cfg = make_large_scale_train_config()
        assert cfg.rollout_steps == 500
        assert cfg.num_episodes == 100
        assert cfg.hidden_dim == 128

    def test_custom_large_scale_config(self):
        """自定义大规模配置：8 envs × 64 = 512。"""
        cfg = make_large_scale_train_config(num_envs=8, rollout_steps_per_env=64)
        assert cfg.rollout_steps == 512

    def test_large_scale_config_is_train_config(self):
        """工厂返回 TrainConfig 实例。"""
        cfg = make_large_scale_train_config()
        assert isinstance(cfg, TrainConfig)

    def test_rollout_steps_meets_p1_4_target(self):
        """P1-4 目标：rollout_steps >= 500（对齐商业大规模训练）。"""
        cfg = make_large_scale_train_config()
        assert cfg.rollout_steps >= 500, (
            f"rollout_steps={cfg.rollout_steps} < 500（P1-4 目标）"
        )


class TestEffectiveBatchSize:
    """有效 batch size 计算测试。"""

    def test_default_batch_size(self):
        """默认 batch size = 4 × 125 = 500。"""
        cfg = ParallelRolloutConfig()
        assert effective_batch_size(cfg) == 500

    def test_batch_size_scales_with_envs(self):
        """batch size 随环境数线性扩展。"""
        cfg1 = ParallelRolloutConfig(num_envs=1, rollout_steps_per_env=100)
        cfg4 = ParallelRolloutConfig(num_envs=4, rollout_steps_per_env=100)
        cfg8 = ParallelRolloutConfig(num_envs=8, rollout_steps_per_env=100)
        assert effective_batch_size(cfg1) == 100
        assert effective_batch_size(cfg4) == 400
        assert effective_batch_size(cfg8) == 800

    def test_batch_size_meets_alphachip_scale(self):
        """对齐 AlphaChip 大规模训练：batch >= 500。"""
        cfg = ParallelRolloutConfig(num_envs=4, rollout_steps_per_env=125)
        assert effective_batch_size(cfg) >= 500


class TestParallelRolloutCollection:
    """并行 rollout 采集功能测试。"""

    def test_collect_floorplan_parallel_single_env(self):
        """单环境并行采集（退化为单环境）。"""
        from polaris.engine.floorplan_env import FloorplanEnv
        from polaris.engine.netlist import load_netlist
        from polaris.trainer.ppo import PPOAgent, PPOConfig
        from polaris.trainer.train_loop import _infer_obs_dim

        circuit = generate_synthetic_benchmark("lidar", num_devices=4)
        netlist_dict = circuit_spec_to_netlist_dict(circuit)
        net, devices, _graph = load_netlist(netlist_dict)
        env = FloorplanEnv(net, devices, canvas_w=200.0, canvas_h=200.0, grid_size=10.0)
        obs, _ = env.reset()
        obs_dim = _infer_obs_dim(env)
        action_dim = 4
        agent = PPOAgent(obs_dim=obs_dim, action_dim=action_dim, config=PPOConfig())
        envs = [env]
        obs_list = [obs]
        reward, steps = collect_floorplan_rollout_parallel(
            agent, envs, obs_list, (obs_dim, action_dim), 5
        )
        assert steps > 0
        assert steps <= 5
        assert isinstance(reward, float)

    def test_collect_floorplan_parallel_multi_env(self):
        """多环境并行采集（4 envs × 5 steps）。"""
        from polaris.engine.floorplan_env import FloorplanEnv
        from polaris.engine.netlist import load_netlist
        from polaris.trainer.ppo import PPOAgent, PPOConfig
        from polaris.trainer.train_loop import _infer_obs_dim

        num_envs = 4
        envs = []
        obs_list = []
        for _ in range(num_envs):
            circuit = generate_synthetic_benchmark("lidar", num_devices=4)
            netlist_dict = circuit_spec_to_netlist_dict(circuit)
            net, devices, _graph = load_netlist(netlist_dict)
            env = FloorplanEnv(
                net, devices, canvas_w=200.0, canvas_h=200.0, grid_size=10.0
            )
            obs, _ = env.reset()
            envs.append(env)
            obs_list.append(obs)
        obs_dim = _infer_obs_dim(envs[0])
        action_dim = 4
        agent = PPOAgent(obs_dim=obs_dim, action_dim=action_dim, config=PPOConfig())
        reward, steps = collect_floorplan_rollout_parallel(
            agent, envs, obs_list, (obs_dim, action_dim), 5
        )
        # 4 envs × 5 steps = 20 max（部分 env 可能提前终止）
        assert steps > 0
        assert steps <= 20
        assert isinstance(reward, float)

    def test_collect_routing_parallel_single_env(self):
        """单环境布线并行采集。"""
        from polaris.engine.netlist import load_netlist
        from polaris.trainer.ppo import PPOAgent, PPOConfig
        from polaris.trainer.train_loop import _build_routing_env, _infer_obs_dim

        config = TrainConfig(canvas_w=200.0, canvas_h=200.0, grid_size=10.0)
        circuit = generate_synthetic_benchmark("lidar", num_devices=4)
        netlist_dict = circuit_spec_to_netlist_dict(circuit)
        net, devices, _graph = load_netlist(netlist_dict)
        env = _build_routing_env(net, devices, config)
        obs, _ = env.reset()
        obs_dim = _infer_obs_dim(env)
        action_dim = 3
        agent = PPOAgent(obs_dim=obs_dim, action_dim=action_dim, config=PPOConfig())
        envs = [env]
        obs_list = [obs]
        reward, steps = collect_routing_rollout_parallel(
            agent, envs, obs_list, obs_dim, 5
        )
        assert steps > 0
        assert steps <= 5


class TestCommercialGapReduction:
    """P1-4 商业差距缩减验证。"""

    def test_rollout_500_aligned_with_commercial(self):
        """rollout 500 步对齐商业大规模训练基准。"""
        cfg = make_large_scale_train_config()
        # 商业标杆：AlphaChip/ICC2 大规模训练 batch >= 500
        assert cfg.rollout_steps >= 500

    def test_parallel_envs_interface_ready(self):
        """多环境接口就绪，为 v2.0 Ray 后端铺路。"""
        cfg = ParallelRolloutConfig(num_envs=8, rollout_steps_per_env=64)
        # 8 envs 接口就绪（当前顺序执行，v2.0 接入 Ray）
        assert cfg.num_envs == 8
        assert cfg.total_rollout_steps == 512

    def test_batch_size_vs_alphachip(self):
        """有效 batch size 对齐 AlphaChip 规模。"""
        # AlphaChip: TPU pod 分布式，单次更新 batch ~1024+
        # PoLaRIS 当前: 4 envs × 125 = 500（CPU 顺序版）
        cfg = ParallelRolloutConfig()
        batch = effective_batch_size(cfg)
        # 差距：500 vs 1024+ = ~2×（v2.0 Ray 后端可扩展至 1024+）
        assert batch == 500
        # 验证接口可扩展至 1024+
        cfg_large = ParallelRolloutConfig(num_envs=8, rollout_steps_per_env=128)
        assert effective_batch_size(cfg_large) == 1024
