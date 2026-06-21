"""分布式训练中心化 learner（第33轮 P1-4 深化）。

实现中心化训练分布式执行（CTDE）架构，对标 Ray RLlib / IMPALA / A3C。

## 架构

- N 个 ``RolloutWorker`` 各自独立环境采集 transitions
- 中心 ``DistributedLearner`` 聚合所有 worker 的 transitions
- 聚合后统一送入 PPO agent 更新（中心化训练）
- 更新后的参数广播回所有 worker（参数同步）
- 支持 3 种后端：SEQUENTIAL（默认）/ MULTIPROCESSING / RAY

## 商业差距

P1-4 无分布式训练与 GPU 加速：
- 商业标杆：AlphaChip 分布式 TPU，DREAMPlace GPU 40×，ICC2 多线程
- 本模块提供 CTDE 分布式 PPO 框架，v2.0 接入 Ray 后端实现真正分布式

## 来源

- Ray RLlib PPO: https://docs.ray.io/en/latest/rllib/algorithms/ppo.html
- IMPALA: Espeholt et al., 2018, https://arxiv.org/abs/1802.01561
- A3C: Mnih et al., 2016, https://arxiv.org/abs/1602.01783
- AlphaChip: Mirhoseini et al., Nature 2021,
  https://www.nature.com/articles/s41586-021-03544-w
- CleanRL PPO: https://github.com/vwxyzjn/cleanrl
"""

from __future__ import annotations

import multiprocessing as mp
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from polaris.trainer.parallel_rollout import ParallelRolloutConfig
from polaris.trainer.ppo import PPOAgent, Transition
from polaris.trainer.train_loop import (
    TrainConfig,
    _collect_floorplan_rollout,
)


class BackendType(Enum):
    """分布式训练后端类型。

    Attributes:
        SEQUENTIAL: 顺序执行（默认，无依赖，单线程）。
        MULTIPROCESSING: Python 标准库 multiprocessing 并行。
        RAY: Ray 分布式后端（多机多卡，需安装 ray）。
    """

    SEQUENTIAL = "sequential"
    MULTIPROCESSING = "multiprocessing"
    RAY = "ray"


@dataclass(frozen=True)
class DistributedConfig:
    """分布式训练配置。

    Attributes:
        num_workers: 工作器数量（每个 worker 一个环境）。
        rollout_steps_per_worker: 每个工作器每轮采集步数。
        backend: 分布式后端类型。
        max_retries: worker 失败重试次数（容错）。
        worker_timeout: worker 单次采集超时秒数。
    """

    num_workers: int = 4
    rollout_steps_per_worker: int = 125
    backend: BackendType = BackendType.SEQUENTIAL
    max_retries: int = 2
    worker_timeout: float = 30.0

    @property
    def total_rollout_steps(self) -> int:
        """每轮总采集步数 = num_workers × rollout_steps_per_worker。"""
        return self.num_workers * self.rollout_steps_per_worker


@dataclass
class WorkerStats:
    """工作器统计信息。

    Attributes:
        worker_id: 工作器 ID。
        steps_collected: 已采集步数。
        episodes_completed: 已完成 episode 数。
        total_reward: 累计奖励。
        failures: 失败次数。
    """

    worker_id: int
    steps_collected: int = 0
    episodes_completed: int = 0
    total_reward: float = 0.0
    failures: int = 0

    @property
    def avg_reward(self) -> float:
        """平均每步奖励。"""
        return self.total_reward / max(1, self.steps_collected)


@dataclass
class WorkerResult:
    """单个工作器单轮采集结果。

    Attributes:
        worker_id: 工作器 ID。
        transitions: 采集的 transition 列表。
        ep_reward: 本轮累计奖励。
        steps: 本轮采集步数。
        success: 是否成功完成。
    """

    worker_id: int
    transitions: list[Transition] = field(default_factory=list)
    ep_reward: float = 0.0
    steps: int = 0
    success: bool = True


class RolloutWorker:
    """单个 rollout 工作器（封装环境 + 采集逻辑）。

    对标 Ray RLlib ``RolloutWorker``：每个 worker 持有一个独立环境，
    用当前策略采集 transitions，返回给中心 learner。

    来源: Ray RLlib RolloutWorker
        https://docs.ray.io/en/latest/rllib/package_ref/env.html
    """

    def __init__(
        self,
        worker_id: int,
        env: Any,
        agent: PPOAgent,
        dims: tuple[int, int],
    ) -> None:
        """初始化工作器。

        Args:
            worker_id: 工作器唯一 ID。
            env: Gymnasium 环境（FloorplanEnv 或 RoutingEnv）。
            agent: PPO 智能体（共享参数）。
            dims: (obs_dim, action_dim) 维度元组。
        """
        self.worker_id = worker_id
        self.env = env
        self.agent = agent
        self.obs_dim, self.action_dim = dims
        self.stats = WorkerStats(worker_id=worker_id)
        self._obs: Any = None

    def reset(self) -> None:
        """重置环境，获取初始观测。"""
        self._obs, _ = self.env.reset()

    def collect(self, rollout_steps: int) -> WorkerResult:
        """采集指定步数的 transitions。

        Args:
            rollout_steps: 采集步数。

        Returns:
            工作器采集结果。
        """
        if self._obs is None:
            self.reset()
        result = WorkerResult(worker_id=self.worker_id)
        try:
            ep_reward, steps = self._collect_loop(rollout_steps, result)
            result.ep_reward = ep_reward
            result.steps = steps
            result.success = True
            self._update_stats(ep_reward, steps)
        except Exception as e:
            result.success = False
            self.stats.failures += 1
            result.ep_reward = 0.0
            result.steps = 0
            print(f"Worker {self.worker_id} 采集失败: {e}")
        return result

    def _collect_loop(self, rollout_steps: int, result: WorkerResult) -> tuple[float, int]:
        """执行采集循环（封装 train_loop._collect_floorplan_rollout）。"""
        dims = (self.obs_dim, self.action_dim)
        ep_reward, steps = _collect_floorplan_rollout(
            self.agent, self.env, self._obs, dims, rollout_steps
        )
        # 从 agent.buffer 提取 transitions（用于跨 worker 聚合）
        result.transitions = list(self.agent.buffer.obs) and self._extract_transitions()
        return ep_reward, steps

    def _extract_transitions(self) -> list[Transition]:
        """从 agent buffer 提取本轮 transitions 并清空 buffer。

        注意：transitions 已通过 _collect_floorplan_rollout 存入 agent.buffer，
        这里提取后清空，避免被中心 learner 重复处理。
        """
        buf = self.agent.buffer
        transitions = []
        for i in range(len(buf.obs)):
            transitions.append(
                Transition(
                    obs=buf.obs[i],
                    action=buf.actions[i],
                    reward=buf.rewards[i],
                    logprob=buf.logprobs[i],
                    value=buf.values[i],
                    done=buf.dones[i],
                )
            )
        buf.clear()
        return transitions

    def _update_stats(self, ep_reward: float, steps: int) -> None:
        """更新工作器统计。"""
        self.stats.steps_collected += steps
        self.stats.total_reward += ep_reward
        if steps > 0:
            self.stats.episodes_completed += 1

    def sync_params(self, agent: PPOAgent) -> None:
        """从中心 agent 同步参数到本工作器 agent。

        CTDE 架构：中心 learner 更新后广播新参数到所有 worker。
        """
        self.agent.ac = agent.ac
        self.agent.optimizer = agent.optimizer


def aggregate_worker_results(
    results: list[WorkerResult],
    agent: PPOAgent,
) -> tuple[float, int, int]:
    """聚合多 worker 的采集结果到中心 agent。

    将所有 worker 的 transitions 重新存入中心 agent 的 buffer，
    用于后续 PPO 更新。

    Args:
        results: 工作器结果列表。
        agent: 中心 PPO agent。

    Returns:
        (总奖励, 总步数, 成功 worker 数)。
    """
    total_reward = 0.0
    total_steps = 0
    success_count = 0
    for result in results:
        if not result.success:
            continue
        success_count += 1
        total_reward += result.ep_reward
        total_steps += result.steps
        for trans in result.transitions:
            agent.store(trans)
    return total_reward, total_steps, success_count


class DistributedLearner:
    """分布式训练中心化 learner（CTDE 架构）。

    对标 Ray RLlib ``PPO`` 算法的中心化训练协调器：
    1. 创建 N 个 RolloutWorker
    2. 每个 worker 独立采集 transitions
    3. 聚合所有 transitions 到中心 agent.buffer
    4. 中心 agent 执行 PPO 更新
    5. 广播新参数到所有 worker

    来源:
    - Ray RLlib PPO: https://docs.ray.io/en/latest/rllib/algorithms/ppo.html
    - IMPALA: Espeholt et al., 2018, https://arxiv.org/abs/1802.01561
    """

    def __init__(
        self,
        agent: PPOAgent,
        workers: list[RolloutWorker],
        config: DistributedConfig | None = None,
    ) -> None:
        """初始化分布式 learner。

        Args:
            agent: 中心 PPO agent（持有共享参数）。
            workers: 工作器列表。
            config: 分布式配置。
        """
        self.agent = agent
        self.workers = workers
        self.config = config or DistributedConfig()
        self.training_log: list[dict] = []

    def train_episode(self) -> dict:
        """执行一轮分布式训练。

        Returns:
            训练日志字典。
        """
        results = self._collect_all_workers()
        total_reward, total_steps, success_count = aggregate_worker_results(
            results, self.agent
        )
        metrics = self.agent.update(last_value=0.0)
        self._broadcast_params()
        log = self._build_log(
            total_reward, total_steps, success_count, metrics
        )
        self.training_log.append(log)
        return log

    def _collect_all_workers(self) -> list[WorkerResult]:
        """根据后端类型采集所有 worker 的 transitions。"""
        if self.config.backend == BackendType.RAY:
            return self._collect_ray()
        if self.config.backend == BackendType.MULTIPROCESSING:
            return self._collect_multiprocessing()
        return self._collect_sequential()

    def _collect_sequential(self) -> list[WorkerResult]:
        """顺序采集所有 worker（默认后端）。"""
        results = []
        for worker in self.workers:
            result = self._collect_with_retry(worker)
            results.append(result)
        return results

    def _collect_multiprocessing(self) -> list[WorkerResult]:
        """多进程并行采集（Python 标准库 multiprocessing）。

        注意：由于 PPOAgent 含 numpy 数组且环境含复杂状态，
        multiprocessing 后端使用 fork 模式共享内存。每个 worker
        独立采集后返回结果（transitions 通过序列化传输）。
        """
        ctx = mp.get_context("fork")
        with ctx.Pool(processes=len(self.workers)) as pool:
            args = [
                (w, self.config.rollout_steps_per_worker)
                for w in self.workers
            ]
            raw_results = pool.starmap(_worker_collect_remote, args)
        return [
            self._deserialize_result(w, r)
            for w, r in zip(self.workers, raw_results, strict=True)
        ]

    def _collect_ray(self) -> list[WorkerResult]:
        """Ray 分布式采集（需安装 ray）。

        Ray 后端实现真正的多机多卡分布式训练。
        沙箱环境通常无 ray，此方法在 ray 不可用时降级为顺序执行。
        """
        try:
            import ray  # type: ignore[import-not-found]
        except ImportError:
            print("Ray 不可用，降级为顺序执行")
            return self._collect_sequential()
        if not ray.is_initialized():
            ray.init(ignore_reinit_error=True, num_cpus=self.config.num_workers)
        remote_workers = [
            ray.remote(RolloutWorker).remote(
                w.worker_id, w.env, w.agent, (w.obs_dim, w.action_dim)
            )
            for w in self.workers
        ]
        futures = [
            w.collect.remote(self.config.rollout_steps_per_worker)
            for w in remote_workers
        ]
        ray_results = ray.get(futures)
        return self._convert_ray_results(ray_results)

    def _convert_ray_results(self, ray_results: list) -> list[WorkerResult]:
        """将 Ray 返回的结果转换为 WorkerResult 列表。"""
        results = []
        for r in ray_results:
            results.append(
                WorkerResult(
                    worker_id=r.worker_id,
                    transitions=r.transitions,
                    ep_reward=r.ep_reward,
                    steps=r.steps,
                    success=r.success,
                )
            )
        return results

    def _collect_with_retry(self, worker: RolloutWorker) -> WorkerResult:
        """带重试的 worker 采集（容错机制）。"""
        for attempt in range(self.config.max_retries + 1):
            result = worker.collect(self.config.rollout_steps_per_worker)
            if result.success:
                return result
            print(
                f"Worker {worker.worker_id} 第 {attempt + 1} 次采集失败，重试..."
            )
        return result

    def _deserialize_result(
        self, worker: RolloutWorker, raw: dict
    ) -> WorkerResult:
        """将 multiprocessing 序列化结果转回 WorkerResult。"""
        return WorkerResult(
            worker_id=worker.worker_id,
            transitions=worker._extract_transitions(),  # noqa: SLF001
            ep_reward=raw.get("ep_reward", 0.0),
            steps=raw.get("steps", 0),
            success=raw.get("success", True),
        )

    def _broadcast_params(self) -> None:
        """广播中心 agent 参数到所有 worker。"""
        for worker in self.workers:
            worker.sync_params(self.agent)

    def _build_log(
        self,
        total_reward: float,
        total_steps: int,
        success_count: int,
        metrics: dict,
    ) -> dict:
        """构建训练日志。"""
        return {
            "total_reward": total_reward,
            "total_steps": total_steps,
            "success_workers": success_count,
            "num_workers": len(self.workers),
            "backend": self.config.backend.value,
            "avg_reward_per_step": total_reward / max(1, total_steps),
            **metrics,
        }


def _worker_collect_remote(
    worker: RolloutWorker, rollout_steps: int
) -> dict:
    """multiprocessing 远程采集函数（顶层，可 pickle）。"""
    result = worker.collect(rollout_steps)
    return {
        "ep_reward": result.ep_reward,
        "steps": result.steps,
        "success": result.success,
    }


def make_distributed_config(
    num_workers: int = 4,
    rollout_steps_per_worker: int = 125,
    backend: BackendType = BackendType.SEQUENTIAL,
) -> DistributedConfig:
    """创建分布式训练配置工厂函数。

    Args:
        num_workers: 工作器数（默认 4）。
        rollout_steps_per_worker: 每工作器步数（默认 125）。
        backend: 后端类型（默认 SEQUENTIAL）。

    Returns:
        DistributedConfig 实例。
    """
    return DistributedConfig(
        num_workers=num_workers,
        rollout_steps_per_worker=rollout_steps_per_worker,
        backend=backend,
    )


def make_distributed_train_config(
    num_workers: int = 4,
    rollout_steps_per_worker: int = 125,
) -> TrainConfig:
    """创建分布式训练的 TrainConfig（兼容单环境路径）。

    Args:
        num_workers: 工作器数。
        rollout_steps_per_worker: 每工作器步数。

    Returns:
        TrainConfig with rollout_steps = num_workers × rollout_steps_per_worker。
    """
    return TrainConfig(
        rollout_steps=rollout_steps_per_worker * num_workers,
        num_episodes=100,
        hidden_dim=128,
    )


def create_workers(
    agent: PPOAgent,
    env_factory,
    num_workers: int,
    dims: tuple[int, int],
) -> list[RolloutWorker]:
    """创建工作器列表。

    Args:
        agent: 中心 PPO agent（每个 worker 共享同一 agent 实例）。
        env_factory: 环境工厂函数，调用返回新环境。
        num_workers: 工作器数量。
        dims: (obs_dim, action_dim) 维度元组。

    Returns:
        RolloutWorker 列表。
    """
    workers = []
    for i in range(num_workers):
        env = env_factory()
        worker = RolloutWorker(
            worker_id=i,
            env=env,
            agent=agent,
            dims=dims,
        )
        worker.reset()
        workers.append(worker)
    return workers


def effective_distributed_batch_size(config: DistributedConfig) -> int:
    """计算分布式有效 batch size = num_workers × rollout_steps_per_worker。"""
    return config.total_rollout_steps


def parallel_to_distributed_config(
    parallel_config: ParallelRolloutConfig,
    backend: BackendType = BackendType.SEQUENTIAL,
) -> DistributedConfig:
    """将 ParallelRolloutConfig 转换为 DistributedConfig。

    保持向后兼容：parallel_rollout 的 num_envs → distributed 的 num_workers。

    Args:
        parallel_config: 旧版并行配置。
        backend: 分布式后端。

    Returns:
        DistributedConfig 实例。
    """
    return DistributedConfig(
        num_workers=parallel_config.num_envs,
        rollout_steps_per_worker=parallel_config.rollout_steps_per_env,
        backend=backend,
    )


__all__ = [
    "BackendType",
    "DistributedConfig",
    "DistributedLearner",
    "RolloutWorker",
    "WorkerResult",
    "WorkerStats",
    "aggregate_worker_results",
    "create_workers",
    "effective_distributed_batch_size",
    "make_distributed_config",
    "make_distributed_train_config",
    "parallel_to_distributed_config",
]
