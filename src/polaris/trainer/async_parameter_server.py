"""异步参数聚合器（第38轮 P1-4 深化，A3C 风格）。

实现异步优势演员-评论家（A3C）风格的异步参数聚合，对标 DeepMind A3C
与 Ray RLlib 异步采样器。

## 架构

- 多个 ``AsyncWorker`` 异步独立采集 transitions 并计算梯度
- ``AsyncParameterServer`` 中心化共享参数存储
- worker 通过 ``push_gradient`` 推送梯度（Hogwild! 风格异步更新）
- worker 通过 ``pull_parameters`` 拉取最新参数
- 支持梯度聚合（N-step 平均）、梯度裁剪、学习率衰减

## 与 CTDE（distributed_learner.py）的差异

| 特性 | CTDE（同步） | A3C（异步） |
|------|-------------|------------|
| 采集 | 所有 worker 同步采集 | worker 异步独立采集 |
| 聚合 | 中心聚合所有 transitions | worker 各自计算梯度推送 |
| 更新 | 中心 PPO 批量更新 | 异步 Hogwild! 更新 |
| 参数同步 | 每轮广播 | worker 拉取最新参数 |
| 适用 | on-policy PPO | off-policy / A2C |

## 商业差距

P1-4 分布式训练深化：
- 商业标杆：AlphaChip 分布式 TPU + 异步采样，A3C Hogwild! 更新
- 本模块提供 A3C 风格异步参数聚合，补充 CTDE 同步框架

## 来源

- A3C: Mnih et al., 2016, https://arxiv.org/abs/1602.01783
- Hogwild!: Recht et al., 2011, https://arxiv.org/abs/1102.5462
- Ray RLlib 异步采样器:
  https://docs.ray.io/en/latest/rllib/package_ref/execution.html
- IMPALA V-trace: Espeholt et al., 2018,
  https://arxiv.org/abs/1802.01561


## 补充文献（R02 学术诚信补齐）
- Mirhoseini et al. 2021 Nature AlphaChip: https://www.nature.com/articles/s41586-021-03544-w
- NetworkX 文档: https://networkx.org/documentation/stable/
"""

from __future__ import annotations

import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum

import numpy as np


class AggregationMode(Enum):
    """梯度聚合模式。

    Attributes:
        MEAN: 所有 worker 梯度求平均（默认，对标 A3C）。
        SUM: 所有 worker 梯度求和。
        WEIGHTED_MEAN: 按步数加权平均。
    """

    MEAN = "mean"
    SUM = "sum"
    WEIGHTED_MEAN = "weighted_mean"


@dataclass(frozen=True)
class AsyncConfig:
    """异步训练配置。

    Attributes:
        num_workers: 异步工作器数量。
        max_gradient_queue: 梯度队列最大长度（背压）。
        aggregation_mode: 梯度聚合模式。
        gradient_clip_norm: 梯度裁剪范数（0 表示不裁剪）。
        learning_rate: 异步更新学习率。
        lr_decay: 学习率衰减率（每轮 *= lr_decay）。
        min_lr: 最小学习率。
        update_interval: 参数服务器更新间隔（梯度数）。
        worker_poll_interval: worker 拉取参数间隔（秒）。
    """

    num_workers: int = 4
    max_gradient_queue: int = 64
    aggregation_mode: AggregationMode = AggregationMode.MEAN
    gradient_clip_norm: float = 0.0
    learning_rate: float = 3e-4
    lr_decay: float = 0.999
    min_lr: float = 1e-6
    update_interval: int = 4
    worker_poll_interval: float = 0.01


@dataclass
class GradientUpdate:
    """单个梯度更新单元。

    Attributes:
        worker_id: 推送梯度的工作器 ID。
        gradients: 梯度字典 {参数名: 梯度数组}。
        weight: 权重（用于加权平均，通常为步数）。
        timestamp: 推送时间戳。
    """

    worker_id: int
    gradients: dict[str, np.ndarray]
    weight: float = 1.0
    timestamp: float = field(default_factory=time.time)


@dataclass
class AsyncStats:
    """异步训练统计信息。

    Attributes:
        total_updates: 总更新次数。
        total_gradients: 总梯度推送次数。
        avg_update_latency: 平均更新延迟（秒）。
        avg_gradient_norm: 平均梯度范数。
        worker_updates: 每个 worker 的更新次数。
    """

    total_updates: int = 0
    total_gradients: int = 0
    avg_update_latency: float = 0.0
    avg_gradient_norm: float = 0.0
    worker_updates: dict[int, int] = field(default_factory=dict)


class AsyncParameterServer:
    """异步参数服务器（A3C Hogwild! 风格）。

    中心化共享参数存储，worker 异步推送梯度，参数服务器按聚合模式
    更新参数。线程安全，支持多 worker 并发推送。

    对标 DeepMind A3C 共享参数服务器与 Ray RLlib 异步采样器。

    来源:
        Mnih et al., 2016, https://arxiv.org/abs/1602.01783
    """

    def __init__(
        self,
        initial_params: dict[str, np.ndarray],
        config: AsyncConfig | None = None,
    ) -> None:
        """初始化参数服务器。

        Args:
            initial_params: 初始参数字典 {参数名: 数组}。
            config: 异步配置。
        """
        self.config = config or AsyncConfig()
        self._params: dict[str, np.ndarray] = {
            k: v.copy() for k, v in initial_params.items()
        }
        self._gradient_queue: deque[GradientUpdate] = deque(
            maxlen=self.config.max_gradient_queue
        )
        self._lock = threading.Lock()
        self._current_lr = self.config.learning_rate
        self.stats = AsyncStats()

    def push_gradient(
        self,
        worker_id: int,
        gradients: dict[str, np.ndarray],
        weight: float = 1.0,
    ) -> None:
        """推送梯度到参数服务器（线程安全）。

        Args:
            worker_id: 工作器 ID。
            gradients: 梯度字典 {参数名: 梯度数组}。
            weight: 权重（用于加权平均）。
        """
        update = GradientUpdate(
            worker_id=worker_id,
            gradients={k: v.copy() for k, v in gradients.items()},
            weight=weight,
        )
        with self._lock:
            self._gradient_queue.append(update)
            self.stats.total_gradients += 1
            self.stats.worker_updates[worker_id] = (
                self.stats.worker_updates.get(worker_id, 0) + 1
            )
            if len(self._gradient_queue) >= self.config.update_interval:
                self._apply_aggregated_update()

    def pull_parameters(self) -> dict[str, np.ndarray]:
        """拉取最新参数（线程安全）。

        Returns:
            参数字典的深拷贝。
        """
        with self._lock:
            return {k: v.copy() for k, v in self._params.items()}

    def get_current_lr(self) -> float:
        """获取当前学习率。"""
        return self._current_lr

    def decay_lr(self) -> float:
        """衰减学习率。

        Returns:
            衰减后的学习率。
        """
        self._current_lr = max(
            self._current_lr * self.config.lr_decay,
            self.config.min_lr,
        )
        return self._current_lr

    def _apply_aggregated_update(self) -> None:
        """聚合队列中的梯度并更新参数（调用方持有锁）。"""
        if not self._gradient_queue:
            return
        updates = list(self._gradient_queue)
        self._gradient_queue.clear()
        start_time = time.time()
        aggregated = self._aggregate_gradients(updates)
        if self.config.gradient_clip_norm > 0:
            aggregated = self._clip_gradients(aggregated)
        self._update_params(aggregated)
        self._update_stats(updates, start_time)

    def _aggregate_gradients(
        self,
        updates: list[GradientUpdate],
    ) -> dict[str, np.ndarray]:
        """按聚合模式聚合梯度。"""
        mode = self.config.aggregation_mode
        if mode == AggregationMode.SUM:
            return self._aggregate_sum(updates)
        if mode == AggregationMode.WEIGHTED_MEAN:
            return self._aggregate_weighted_mean(updates)
        return self._aggregate_mean(updates)

    def _aggregate_mean(
        self,
        updates: list[GradientUpdate],
    ) -> dict[str, np.ndarray]:
        """简单平均聚合。"""
        n = len(updates)
        result: dict[str, np.ndarray] = {}
        for key in updates[0].gradients:
            result[key] = sum(
                u.gradients[key] for u in updates
            ) / n
        return result

    def _aggregate_sum(
        self,
        updates: list[GradientUpdate],
    ) -> dict[str, np.ndarray]:
        """求和聚合。"""
        result: dict[str, np.ndarray] = {}
        for key in updates[0].gradients:
            result[key] = sum(u.gradients[key] for u in updates)
        return result

    def _aggregate_weighted_mean(
        self,
        updates: list[GradientUpdate],
    ) -> dict[str, np.ndarray]:
        """加权平均聚合（按 weight 字段）。"""
        total_weight = sum(u.weight for u in updates)
        if total_weight <= 0:
            return self._aggregate_mean(updates)
        result: dict[str, np.ndarray] = {}
        for key in updates[0].gradients:
            result[key] = sum(
                u.weight * u.gradients[key] for u in updates
            ) / total_weight
        return result

    def _clip_gradients(
        self,
        gradients: dict[str, np.ndarray],
    ) -> dict[str, np.ndarray]:
        """全局梯度裁剪（L2 范数）。"""
        clip_norm = self.config.gradient_clip_norm
        total_norm = float(np.sqrt(sum(
            float(np.sum(g ** 2)) for g in gradients.values()
        )))
        if total_norm > clip_norm and total_norm > 0:
            scale = clip_norm / total_norm
            return {k: v * scale for k, v in gradients.items()}
        return gradients

    def _update_params(self, gradients: dict[str, np.ndarray]) -> None:
        """用聚合梯度更新参数（梯度下降）。"""
        lr = self._current_lr
        for key, grad in gradients.items():
            if key in self._params:
                self._params[key] = self._params[key] - lr * grad

    def _update_stats(
        self,
        updates: list[GradientUpdate],
        start_time: float,
    ) -> None:
        """更新统计信息。"""
        latency = time.time() - start_time
        n = self.stats.total_updates
        self.stats.avg_update_latency = (
            self.stats.avg_update_latency * n + latency
        ) / (n + 1)
        grad_norm = float(np.sqrt(sum(
            float(np.sum(u.gradients[k] ** 2))
            for u in updates for k in u.gradients
        ))) / max(1, len(updates))
        self.stats.avg_gradient_norm = (
            self.stats.avg_gradient_norm * n + grad_norm
        ) / (n + 1)
        self.stats.total_updates += 1

    def force_update(self) -> None:
        """强制聚合队列中所有梯度并更新（用于训练结束 flush）。"""
        with self._lock:
            self._apply_aggregated_update()


class AsyncWorker:
    """异步工作器（A3C 风格）。

    每个 worker 独立采集 transitions、计算梯度、推送梯度到参数服务器，
    并周期性拉取最新参数。线程安全，可多线程并发执行。

    对标 DeepMind A3C 异步 worker。

    来源:
        Mnih et al., 2016, https://arxiv.org/abs/1602.01783
    """

    def __init__(
        self,
        worker_id: int,
        param_server: AsyncParameterServer,
        grad_fn: Callable[[dict[str, np.ndarray]], dict[str, np.ndarray]],
        config: AsyncConfig | None = None,
    ) -> None:
        """初始化异步工作器。

        Args:
            worker_id: 工作器唯一 ID。
            param_server: 参数服务器引用。
            grad_fn: 梯度计算函数，输入参数字典返回梯度字典。
            config: 异步配置。
        """
        self.worker_id = worker_id
        self.param_server = param_server
        self.grad_fn = grad_fn
        self.config = config or AsyncConfig()
        self._local_params: dict[str, np.ndarray] | None = None
        self._steps = 0
        self._lock = threading.Lock()

    def step(self) -> dict[str, np.ndarray]:
        """执行一步异步更新。

        1. 拉取最新参数
        2. 计算梯度
        3. 推送梯度到参数服务器

        Returns:
            本次计算的梯度。
        """
        self._local_params = self.param_server.pull_parameters()
        gradients = self.grad_fn(self._local_params)
        self.param_server.push_gradient(
            worker_id=self.worker_id,
            gradients=gradients,
            weight=1.0,
        )
        with self._lock:
            self._steps += 1
        return gradients

    def step_n(self, n: int) -> int:
        """执行 n 步异步更新。

        Args:
            n: 步数。

        Returns:
            实际执行的步数。
        """
        for _ in range(n):
            self.step()
        return n

    @property
    def steps(self) -> int:
        """已执行步数。"""
        return self._steps


def run_async_training(
    initial_params: dict[str, np.ndarray],
    grad_fn: Callable[[dict[str, np.ndarray]], dict[str, np.ndarray]],
    config: AsyncConfig | None = None,
    total_steps: int = 100,
) -> tuple[dict[str, np.ndarray], AsyncStats]:
    """运行异步训练（便捷工厂函数）。

    创建参数服务器和 N 个 worker，每个 worker 执行 total_steps 步
    异步更新，最后返回最终参数和统计信息。

    Args:
        initial_params: 初始参数字典。
        grad_fn: 梯度计算函数。
        config: 异步配置。
        total_steps: 每个 worker 的总步数。

    Returns:
        (最终参数, 统计信息)。
    """
    cfg = config or AsyncConfig()
    server = AsyncParameterServer(initial_params, cfg)
    workers = [
        AsyncWorker(i, server, grad_fn, cfg) for i in range(cfg.num_workers)
    ]
    threads = []
    for w in workers:
        t = threading.Thread(target=w.step_n, args=(total_steps,))
        threads.append(t)
        t.start()
    for t in threads:
        t.join()
    server.force_update()
    return server.pull_parameters(), server.stats


def create_async_parameter_server(
    initial_params: dict[str, np.ndarray],
    config: AsyncConfig | None = None,
) -> AsyncParameterServer:
    """工厂函数：创建异步参数服务器。"""
    return AsyncParameterServer(initial_params, config)


def create_async_worker(
    worker_id: int,
    param_server: AsyncParameterServer,
    grad_fn: Callable[[dict[str, np.ndarray]], dict[str, np.ndarray]],
    config: AsyncConfig | None = None,
) -> AsyncWorker:
    """工厂函数：创建异步工作器。"""
    return AsyncWorker(worker_id, param_server, grad_fn, config)


def parallel_to_async_config(
    num_workers: int,
    learning_rate: float = 3e-4,
) -> AsyncConfig:
    """从并行配置转换为异步配置（便捷函数）。

    Args:
        num_workers: 工作器数量。
        learning_rate: 学习率。

    Returns:
        异步配置。
    """
    return AsyncConfig(
        num_workers=num_workers,
        learning_rate=learning_rate,
        update_interval=max(1, num_workers),
    )
