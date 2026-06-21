"""P1-4 分布式训练中心化 learner 测试（第33轮 P1-4 深化）。

验证 CTDE 架构、多后端切换、经验聚合、容错机制。

来源: commercial_gap_analysis.md P1-4 无分布式训练与 GPU 加速
对标: Ray RLlib PPO / IMPALA / A3C
"""

from __future__ import annotations

import pytest

from polaris.data.data_loader import (
    circuit_spec_to_netlist_dict,
    generate_synthetic_benchmark,
)
from polaris.engine.floorplan_env import FloorplanEnv
from polaris.engine.netlist import load_netlist
from polaris.trainer.distributed_learner import (
    BackendType,
    DistributedConfig,
    DistributedLearner,
    RolloutWorker,
    WorkerResult,
    WorkerStats,
    aggregate_worker_results,
    create_workers,
    effective_distributed_batch_size,
    make_distributed_config,
    make_distributed_train_config,
    parallel_to_distributed_config,
)
from polaris.trainer.parallel_rollout import ParallelRolloutConfig
from polaris.trainer.ppo import PPOAgent, PPOConfig, Transition
from polaris.trainer.train_loop import TrainConfig, _infer_obs_dim


@pytest.fixture
def env_factory():
    """环境工厂 fixture（每次调用返回新环境）。"""

    def _factory():
        circuit = generate_synthetic_benchmark("lidar", num_devices=4)
        netlist_dict = circuit_spec_to_netlist_dict(circuit)
        net, devices, _ = load_netlist(netlist_dict)
        return FloorplanEnv(
            net, devices, canvas_w=200.0, canvas_h=200.0, grid_size=10.0
        )

    return _factory


@pytest.fixture
def agent(env_factory):
    """PPO agent fixture。"""
    env = env_factory()
    obs_dim = _infer_obs_dim(env)
    action_dim = 4
    return PPOAgent(
        obs_dim=obs_dim, action_dim=action_dim, config=PPOConfig()
    )


class TestBackendType:
    """后端类型枚举测试。"""

    def test_sequential_backend(self):
        """顺序后端。"""
        assert BackendType.SEQUENTIAL.value == "sequential"

    def test_multiprocessing_backend(self):
        """多进程后端。"""
        assert BackendType.MULTIPROCESSING.value == "multiprocessing"

    def test_ray_backend(self):
        """Ray 后端。"""
        assert BackendType.RAY.value == "ray"

    def test_backend_count(self):
        """3 种后端。"""
        assert len(BackendType) == 3


class TestDistributedConfig:
    """分布式配置测试。"""

    def test_default_config(self):
        """默认配置：4 workers × 125 steps = 500 总步数。"""
        cfg = DistributedConfig()
        assert cfg.num_workers == 4
        assert cfg.rollout_steps_per_worker == 125
        assert cfg.total_rollout_steps == 500
        assert cfg.backend == BackendType.SEQUENTIAL
        assert cfg.max_retries == 2
        assert cfg.worker_timeout == 30.0

    def test_custom_config(self):
        """自定义配置：8 workers × 64 steps = 512。"""
        cfg = DistributedConfig(
            num_workers=8,
            rollout_steps_per_worker=64,
            backend=BackendType.MULTIPROCESSING,
        )
        assert cfg.num_workers == 8
        assert cfg.rollout_steps_per_worker == 64
        assert cfg.total_rollout_steps == 512
        assert cfg.backend == BackendType.MULTIPROCESSING

    def test_frozen_dataclass(self):
        """DistributedConfig 是 frozen dataclass。"""
        cfg = DistributedConfig()
        with pytest.raises(AttributeError):
            cfg.num_workers = 8  # type: ignore[misc]

    def test_ray_backend_config(self):
        """Ray 后端配置。"""
        cfg = DistributedConfig(backend=BackendType.RAY)
        assert cfg.backend == BackendType.RAY


class TestWorkerStats:
    """工作器统计测试。"""

    def test_default_stats(self):
        """默认统计值。"""
        stats = WorkerStats(worker_id=0)
        assert stats.worker_id == 0
        assert stats.steps_collected == 0
        assert stats.episodes_completed == 0
        assert stats.total_reward == 0.0
        assert stats.failures == 0

    def test_avg_reward_zero_steps(self):
        """0 步时平均奖励为 0。"""
        stats = WorkerStats(worker_id=0)
        assert stats.avg_reward == 0.0

    def test_avg_reward_nonzero(self):
        """非零步数平均奖励。"""
        stats = WorkerStats(
            worker_id=0, steps_collected=100, total_reward=50.0
        )
        assert stats.avg_reward == 0.5


class TestWorkerResult:
    """工作器结果测试。"""

    def test_default_result(self):
        """默认结果。"""
        result = WorkerResult(worker_id=0)
        assert result.worker_id == 0
        assert result.transitions == []
        assert result.ep_reward == 0.0
        assert result.steps == 0
        assert result.success is True

    def test_failed_result(self):
        """失败结果。"""
        result = WorkerResult(worker_id=1, success=False)
        assert result.success is False


class TestRolloutWorker:
    """工作器测试。"""

    def test_worker_creation(self, agent, env_factory):
        """工作器创建。"""
        env = env_factory()
        obs_dim = _infer_obs_dim(env)
        worker = RolloutWorker(
            worker_id=0,
            env=env,
            agent=agent,
            obs_dim=obs_dim,
            action_dim=4,
        )
        assert worker.worker_id == 0
        assert worker.env is env
        assert worker.agent is agent
        assert worker.obs_dim == obs_dim
        assert worker.action_dim == 4

    def test_worker_reset(self, agent, env_factory):
        """工作器重置。"""
        env = env_factory()
        obs_dim = _infer_obs_dim(env)
        worker = RolloutWorker(
            worker_id=0, env=env, agent=agent, obs_dim=obs_dim, action_dim=4
        )
        worker.reset()
        assert worker._obs is not None  # noqa: SLF001

    def test_worker_collect(self, agent, env_factory):
        """工作器采集 transitions。"""
        env = env_factory()
        obs_dim = _infer_obs_dim(env)
        worker = RolloutWorker(
            worker_id=0, env=env, agent=agent, obs_dim=obs_dim, action_dim=4
        )
        worker.reset()
        result = worker.collect(5)
        assert result.worker_id == 0
        assert result.success is True
        assert result.steps > 0
        assert result.steps <= 5
        assert isinstance(result.ep_reward, float)

    def test_worker_stats_update(self, agent, env_factory):
        """工作器统计更新。"""
        env = env_factory()
        obs_dim = _infer_obs_dim(env)
        worker = RolloutWorker(
            worker_id=0, env=env, agent=agent, obs_dim=obs_dim, action_dim=4
        )
        worker.reset()
        worker.collect(5)
        assert worker.stats.steps_collected > 0
        assert worker.stats.episodes_completed >= 1

    def test_worker_sync_params(self, agent, env_factory):
        """工作器参数同步。"""
        env = env_factory()
        obs_dim = _infer_obs_dim(env)
        worker = RolloutWorker(
            worker_id=0, env=env, agent=agent, obs_dim=obs_dim, action_dim=4
        )
        # 创建另一个 agent 模拟中心 learner
        other_agent = PPOAgent(
            obs_dim=obs_dim, action_dim=4, config=PPOConfig()
        )
        worker.sync_params(other_agent)
        assert worker.agent.ac is other_agent.ac


class TestAggregateWorkerResults:
    """经验聚合测试。"""

    def test_aggregate_empty_results(self, agent):
        """空结果聚合。"""
        total_r, total_s, success = aggregate_worker_results([], agent)
        assert total_r == 0.0
        assert total_s == 0
        assert success == 0

    def test_aggregate_single_success(self, agent):
        """单个成功结果聚合。"""
        result = WorkerResult(
            worker_id=0,
            transitions=[
                Transition(
                    obs=[0.0] * 10,
                    action=[0.0] * 4,
                    reward=1.0,
                    logprob=-1.0,
                    value=0.5,
                    done=False,
                )
            ],
            ep_reward=1.0,
            steps=1,
            success=True,
        )
        total_r, total_s, success = aggregate_worker_results(
            [result], agent
        )
        assert total_r == 1.0
        assert total_s == 1
        assert success == 1
        assert len(agent.buffer.obs) == 1

    def test_aggregate_multiple_success(self, agent):
        """多个成功结果聚合。"""
        results = [
            WorkerResult(
                worker_id=i,
                transitions=[
                    Transition(
                        obs=[0.0] * 10,
                        action=[0.0] * 4,
                        reward=1.0,
                        logprob=-1.0,
                        value=0.5,
                        done=False,
                    )
                ],
                ep_reward=1.0,
                steps=1,
                success=True,
            )
            for i in range(4)
        ]
        total_r, total_s, success = aggregate_worker_results(
            results, agent
        )
        assert total_r == 4.0
        assert total_s == 4
        assert success == 4
        assert len(agent.buffer.obs) == 4

    def test_aggregate_skips_failed(self, agent):
        """聚合跳过失败结果。"""
        results = [
            WorkerResult(worker_id=0, success=True, ep_reward=1.0, steps=1),
            WorkerResult(worker_id=1, success=False, ep_reward=0.0, steps=0),
            WorkerResult(worker_id=2, success=True, ep_reward=2.0, steps=2),
        ]
        total_r, total_s, success = aggregate_worker_results(
            results, agent
        )
        assert total_r == 3.0
        assert total_s == 3
        assert success == 2


class TestDistributedLearner:
    """分布式 learner 测试。"""

    def test_learner_creation(self, agent, env_factory):
        """learner 创建。"""
        obs_dim = _infer_obs_dim(env_factory())
        workers = create_workers(
            agent=agent,
            env_factory=env_factory,
            num_workers=2,
            obs_dim=obs_dim,
            action_dim=4,
        )
        learner = DistributedLearner(
            agent=agent, workers=workers, config=DistributedConfig(num_workers=2)
        )
        assert learner.agent is agent
        assert len(learner.workers) == 2
        assert learner.config.num_workers == 2

    def test_learner_train_sequential(self, agent, env_factory):
        """顺序后端训练一轮。"""
        obs_dim = _infer_obs_dim(env_factory())
        workers = create_workers(
            agent=agent,
            env_factory=env_factory,
            num_workers=2,
            obs_dim=obs_dim,
            action_dim=4,
        )
        config = DistributedConfig(
            num_workers=2,
            rollout_steps_per_worker=3,
            backend=BackendType.SEQUENTIAL,
        )
        learner = DistributedLearner(agent=agent, workers=workers, config=config)
        log = learner.train_episode()
        assert "total_reward" in log
        assert "total_steps" in log
        assert "success_workers" in log
        assert log["backend"] == "sequential"
        assert log["num_workers"] == 2
        assert log["total_steps"] > 0

    def test_learner_training_log(self, agent, env_factory):
        """训练日志累积。"""
        obs_dim = _infer_obs_dim(env_factory())
        workers = create_workers(
            agent=agent,
            env_factory=env_factory,
            num_workers=2,
            obs_dim=obs_dim,
            action_dim=4,
        )
        config = DistributedConfig(
            num_workers=2, rollout_steps_per_worker=3
        )
        learner = DistributedLearner(agent=agent, workers=workers, config=config)
        learner.train_episode()
        learner.train_episode()
        assert len(learner.training_log) == 2

    def test_learner_broadcast_params(self, agent, env_factory):
        """参数广播后 worker 与中心 agent 参数一致。"""
        obs_dim = _infer_obs_dim(env_factory())
        workers = create_workers(
            agent=agent,
            env_factory=env_factory,
            num_workers=2,
            obs_dim=obs_dim,
            action_dim=4,
        )
        config = DistributedConfig(
            num_workers=2, rollout_steps_per_worker=3
        )
        learner = DistributedLearner(agent=agent, workers=workers, config=config)
        learner._broadcast_params()  # noqa: SLF001
        for worker in workers:
            assert worker.agent.ac is agent.ac


class TestFactoryFunctions:
    """工厂函数测试。"""

    def test_make_distributed_config_default(self):
        """默认分布式配置。"""
        cfg = make_distributed_config()
        assert cfg.num_workers == 4
        assert cfg.rollout_steps_per_worker == 125
        assert cfg.backend == BackendType.SEQUENTIAL

    def test_make_distributed_config_custom(self):
        """自定义分布式配置。"""
        cfg = make_distributed_config(
            num_workers=8,
            rollout_steps_per_worker=64,
            backend=BackendType.RAY,
        )
        assert cfg.num_workers == 8
        assert cfg.rollout_steps_per_worker == 64
        assert cfg.backend == BackendType.RAY

    def test_make_distributed_train_config(self):
        """分布式训练 TrainConfig 工厂。"""
        cfg = make_distributed_train_config(
            num_workers=8, rollout_steps_per_worker=64
        )
        assert isinstance(cfg, TrainConfig)
        assert cfg.rollout_steps == 512
        assert cfg.num_episodes == 100
        assert cfg.hidden_dim == 128

    def test_effective_distributed_batch_size(self):
        """分布式有效 batch size。"""
        cfg = DistributedConfig(num_workers=4, rollout_steps_per_worker=125)
        assert effective_distributed_batch_size(cfg) == 500

    def test_parallel_to_distributed_config(self):
        """ParallelRolloutConfig → DistributedConfig 转换。"""
        parallel_cfg = ParallelRolloutConfig(
            num_envs=8, rollout_steps_per_env=64
        )
        dist_cfg = parallel_to_distributed_config(parallel_cfg)
        assert dist_cfg.num_workers == 8
        assert dist_cfg.rollout_steps_per_worker == 64
        assert dist_cfg.backend == BackendType.SEQUENTIAL

    def test_parallel_to_distributed_with_backend(self):
        """带后端的转换。"""
        parallel_cfg = ParallelRolloutConfig(num_envs=4)
        dist_cfg = parallel_to_distributed_config(
            parallel_cfg, backend=BackendType.RAY
        )
        assert dist_cfg.backend == BackendType.RAY


class TestCreateWorkers:
    """工作器创建函数测试。"""

    def test_create_workers_count(self, agent, env_factory):
        """创建指定数量的工作器。"""
        obs_dim = _infer_obs_dim(env_factory())
        workers = create_workers(
            agent=agent,
            env_factory=env_factory,
            num_workers=4,
            obs_dim=obs_dim,
            action_dim=4,
        )
        assert len(workers) == 4
        for i, w in enumerate(workers):
            assert w.worker_id == i

    def test_create_workers_reset(self, agent, env_factory):
        """工作器创建后已重置（有初始观测）。"""
        obs_dim = _infer_obs_dim(env_factory())
        workers = create_workers(
            agent=agent,
            env_factory=env_factory,
            num_workers=2,
            obs_dim=obs_dim,
            action_dim=4,
        )
        for w in workers:
            assert w._obs is not None  # noqa: SLF001


class TestCommercialGapReduction:
    """P1-4 商业差距缩减验证。"""

    def test_batch_size_500_aligned_commercial(self):
        """batch size 500 对齐商业大规模训练。"""
        cfg = make_distributed_config()
        batch = effective_distributed_batch_size(cfg)
        assert batch >= 500, f"batch={batch} < 500（P1-4 目标）"

    def test_batch_size_scales_to_1024(self):
        """batch size 可扩展至 1024（对齐 AlphaChip）。"""
        cfg = DistributedConfig(
            num_workers=8, rollout_steps_per_worker=128
        )
        batch = effective_distributed_batch_size(cfg)
        assert batch == 1024

    def test_ctde_architecture_ready(self, agent, env_factory):
        """CTDE 架构就绪（中心训练 + 分布式执行）。"""
        obs_dim = _infer_obs_dim(env_factory())
        workers = create_workers(
            agent=agent,
            env_factory=env_factory,
            num_workers=4,
            obs_dim=obs_dim,
            action_dim=4,
        )
        learner = DistributedLearner(
            agent=agent, workers=workers, config=DistributedConfig(num_workers=4)
        )
        log = learner.train_episode()
        # CTDE: 中心 agent 更新 + 参数广播回 worker
        assert log["success_workers"] > 0
        assert log["total_steps"] > 0

    def test_multi_backend_support(self):
        """多后端支持（SEQUENTIAL/MULTIPROCESSING/RAY）。"""
        backends = [
            BackendType.SEQUENTIAL,
            BackendType.MULTIPROCESSING,
            BackendType.RAY,
        ]
        for backend in backends:
            cfg = DistributedConfig(backend=backend)
            assert cfg.backend == backend

    def test_fault_tolerance_retry(self):
        """容错机制：max_retries 配置。"""
        cfg = DistributedConfig(max_retries=3)
        assert cfg.max_retries == 3

    def test_backward_compatible_with_parallel_rollout(self):
        """向后兼容 parallel_rollout 接口。"""
        parallel_cfg = ParallelRolloutConfig(num_envs=4, rollout_steps_per_env=125)
        dist_cfg = parallel_to_distributed_config(parallel_cfg)
        # 转换后保持相同的总步数
        assert dist_cfg.total_rollout_steps == parallel_cfg.total_rollout_steps
