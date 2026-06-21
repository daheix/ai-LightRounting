"""异步参数聚合器测试（第38轮 P1-4 深化，A3C 风格）。

测试覆盖：
- AsyncConfig 配置
- AggregationMode 枚举
- GradientUpdate 数据类
- AsyncStats 统计
- AsyncParameterServer 参数服务器
- AsyncWorker 异步工作器
- 工厂函数
- run_async_training 端到端
- 商业差距缩减验证（对标 A3C / Ray RLlib）
"""

from __future__ import annotations

import threading

import numpy as np
import pytest

from polaris.trainer.async_parameter_server import (
    AggregationMode,
    AsyncConfig,
    AsyncParameterServer,
    AsyncStats,
    AsyncWorker,
    GradientUpdate,
    create_async_parameter_server,
    create_async_worker,
    parallel_to_async_config,
    run_async_training,
)


class TestAsyncConfig:
    """异步配置测试。"""

    def test_default_config(self) -> None:
        """默认配置值。"""
        cfg = AsyncConfig()
        assert cfg.num_workers == 4
        assert cfg.max_gradient_queue == 64
        assert cfg.aggregation_mode == AggregationMode.MEAN
        assert cfg.gradient_clip_norm == 0.0
        assert cfg.learning_rate == 3e-4
        assert cfg.lr_decay == 0.999
        assert cfg.min_lr == 1e-6
        assert cfg.update_interval == 4
        assert cfg.worker_poll_interval == 0.01

    def test_custom_config(self) -> None:
        """自定义配置。"""
        cfg = AsyncConfig(
            num_workers=8,
            learning_rate=1e-3,
            gradient_clip_norm=1.0,
            aggregation_mode=AggregationMode.SUM,
        )
        assert cfg.num_workers == 8
        assert cfg.learning_rate == 1e-3
        assert cfg.gradient_clip_norm == 1.0
        assert cfg.aggregation_mode == AggregationMode.SUM

    def test_frozen_dataclass(self) -> None:
        """frozen dataclass 不可变。"""
        cfg = AsyncConfig()
        with pytest.raises(AttributeError):
            cfg.num_workers = 10  # type: ignore[misc]


class TestAggregationMode:
    """聚合模式测试。"""

    def test_enum_values(self) -> None:
        """枚举值。"""
        assert AggregationMode.MEAN.value == "mean"
        assert AggregationMode.SUM.value == "sum"
        assert AggregationMode.WEIGHTED_MEAN.value == "weighted_mean"

    def test_enum_from_value(self) -> None:
        """从字符串构造枚举。"""
        assert AggregationMode("mean") == AggregationMode.MEAN
        assert AggregationMode("sum") == AggregationMode.SUM
        assert AggregationMode("weighted_mean") == AggregationMode.WEIGHTED_MEAN


class TestGradientUpdate:
    """梯度更新单元测试。"""

    def test_creation(self) -> None:
        """创建 GradientUpdate。"""
        grads = {"w": np.array([1.0, 2.0])}
        update = GradientUpdate(worker_id=0, gradients=grads, weight=2.0)
        assert update.worker_id == 0
        assert update.weight == 2.0
        assert "w" in update.gradients
        assert update.timestamp > 0

    def test_default_weight(self) -> None:
        """默认权重为 1.0。"""
        update = GradientUpdate(worker_id=0, gradients={})
        assert update.weight == 1.0


class TestAsyncStats:
    """统计信息测试。"""

    def test_default_stats(self) -> None:
        """默认统计。"""
        stats = AsyncStats()
        assert stats.total_updates == 0
        assert stats.total_gradients == 0
        assert stats.avg_update_latency == 0.0
        assert stats.avg_gradient_norm == 0.0
        assert stats.worker_updates == {}


class TestAsyncParameterServer:
    """参数服务器测试。"""

    def test_creation(self) -> None:
        """创建参数服务器。"""
        params = {"w": np.zeros(3)}
        server = AsyncParameterServer(params)
        pulled = server.pull_parameters()
        assert np.allclose(pulled["w"], 0.0)
        # 修改返回值不影响内部参数
        pulled["w"][0] = 1.0
        assert np.allclose(server.pull_parameters()["w"], 0.0)

    def test_push_gradient_updates_params(self) -> None:
        """推送梯度更新参数。"""
        params = {"w": np.array([1.0, 1.0])}
        cfg = AsyncConfig(update_interval=1, learning_rate=0.1)
        server = AsyncParameterServer(params, cfg)
        grads = {"w": np.array([1.0, 1.0])}
        server.push_gradient(0, grads)
        # w_new = w - lr * grad = 1.0 - 0.1 * 1.0 = 0.9
        assert np.allclose(server.pull_parameters()["w"], 0.9)

    def test_mean_aggregation(self) -> None:
        """MEAN 聚合模式。"""
        params = {"w": np.array([0.0])}
        cfg = AsyncConfig(
            update_interval=2,
            learning_rate=1.0,
            aggregation_mode=AggregationMode.MEAN,
        )
        server = AsyncParameterServer(params, cfg)
        server.push_gradient(0, {"w": np.array([2.0])})
        # 队列未满，不更新
        assert np.allclose(server.pull_parameters()["w"], 0.0)
        server.push_gradient(1, {"w": np.array([4.0])})
        # MEAN: (2 + 4) / 2 = 3, w_new = 0 - 1.0 * 3 = -3
        assert np.allclose(server.pull_parameters()["w"], -3.0)

    def test_sum_aggregation(self) -> None:
        """SUM 聚合模式。"""
        params = {"w": np.array([0.0])}
        cfg = AsyncConfig(
            update_interval=2,
            learning_rate=0.5,
            aggregation_mode=AggregationMode.SUM,
        )
        server = AsyncParameterServer(params, cfg)
        server.push_gradient(0, {"w": np.array([2.0])})
        server.push_gradient(1, {"w": np.array([4.0])})
        # SUM: 2 + 4 = 6, w_new = 0 - 0.5 * 6 = -3
        assert np.allclose(server.pull_parameters()["w"], -3.0)

    def test_weighted_mean_aggregation(self) -> None:
        """WEIGHTED_MEAN 聚合模式。"""
        params = {"w": np.array([0.0])}
        cfg = AsyncConfig(
            update_interval=2,
            learning_rate=1.0,
            aggregation_mode=AggregationMode.WEIGHTED_MEAN,
        )
        server = AsyncParameterServer(params, cfg)
        server.push_gradient(0, {"w": np.array([2.0])}, weight=1.0)
        server.push_gradient(1, {"w": np.array([4.0])}, weight=3.0)
        # WEIGHTED_MEAN: (1*2 + 3*4) / (1+3) = 14/4 = 3.5
        # w_new = 0 - 1.0 * 3.5 = -3.5
        assert np.allclose(server.pull_parameters()["w"], -3.5)

    def test_gradient_clipping(self) -> None:
        """梯度裁剪。"""
        params = {"w": np.array([0.0])}
        cfg = AsyncConfig(
            update_interval=1,
            learning_rate=1.0,
            gradient_clip_norm=1.0,
        )
        server = AsyncParameterServer(params, cfg)
        # 梯度范数 = 5，裁剪到 1
        server.push_gradient(0, {"w": np.array([5.0])})
        # w_new = 0 - 1.0 * 1.0 = -1.0
        assert np.allclose(server.pull_parameters()["w"], -1.0)

    def test_lr_decay(self) -> None:
        """学习率衰减。"""
        cfg = AsyncConfig(learning_rate=1.0, lr_decay=0.5, min_lr=0.1)
        server = AsyncParameterServer({"w": np.array([0.0])}, cfg)
        assert server.get_current_lr() == 1.0
        assert server.decay_lr() == 0.5
        assert server.decay_lr() == 0.25
        # 衰减到 min_lr 以下时保持 min_lr
        for _ in range(20):
            server.decay_lr()
        assert server.get_current_lr() == 0.1

    def test_force_update(self) -> None:
        """强制 flush 队列。"""
        params = {"w": np.array([0.0])}
        cfg = AsyncConfig(update_interval=10, learning_rate=1.0)
        server = AsyncParameterServer(params, cfg)
        server.push_gradient(0, {"w": np.array([1.0])})
        # 队列未满，但 force_update 触发更新
        server.force_update()
        assert np.allclose(server.pull_parameters()["w"], -1.0)

    def test_stats_tracking(self) -> None:
        """统计信息追踪。"""
        cfg = AsyncConfig(update_interval=2, learning_rate=0.1)
        server = AsyncParameterServer({"w": np.array([0.0])}, cfg)
        server.push_gradient(0, {"w": np.array([1.0])})
        server.push_gradient(1, {"w": np.array([2.0])})
        assert server.stats.total_gradients == 2
        assert server.stats.total_updates == 1
        assert server.stats.worker_updates[0] == 1
        assert server.stats.worker_updates[1] == 1
        assert server.stats.avg_update_latency > 0
        assert server.stats.avg_gradient_norm > 0

    def test_thread_safety(self) -> None:
        """多线程并发推送。"""
        params = {"w": np.array([0.0])}
        cfg = AsyncConfig(update_interval=1, learning_rate=0.01)
        server = AsyncParameterServer(params, cfg)

        def push_many(wid: int) -> None:
            for _ in range(50):
                server.push_gradient(wid, {"w": np.array([1.0])})

        threads = [
            threading.Thread(target=push_many, args=(i,))
            for i in range(4)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        # 4 workers * 50 steps = 200 gradients
        assert server.stats.total_gradients == 200
        # 参数应该被更新（值减小）
        assert server.pull_parameters()["w"][0] < 0


class TestAsyncWorker:
    """异步工作器测试。"""

    def test_creation(self) -> None:
        """创建工作器。"""
        server = AsyncParameterServer({"w": np.zeros(2)})
        worker = AsyncWorker(0, server, lambda p: {"w": np.ones(2)})
        assert worker.worker_id == 0
        assert worker.steps == 0

    def test_step(self) -> None:
        """单步更新。"""
        params = {"w": np.array([1.0])}
        cfg = AsyncConfig(update_interval=1, learning_rate=0.1)
        server = AsyncParameterServer(params, cfg)

        def grad_fn(p: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
            return {"w": np.array([2.0])}

        worker = AsyncWorker(0, server, grad_fn, cfg)
        worker.step()
        assert worker.steps == 1
        # w_new = 1.0 - 0.1 * 2.0 = 0.8
        assert np.allclose(server.pull_parameters()["w"], 0.8)

    def test_step_n(self) -> None:
        """多步更新。"""
        params = {"w": np.array([0.0])}
        cfg = AsyncConfig(update_interval=1, learning_rate=0.1)
        server = AsyncParameterServer(params, cfg)
        worker = AsyncWorker(0, server, lambda p: {"w": np.array([1.0])}, cfg)
        worker.step_n(5)
        assert worker.steps == 5
        # 每步 w -= 0.1 * 1.0，5 步后 w = -0.5
        assert np.allclose(server.pull_parameters()["w"], -0.5)

    def test_local_params_pulled(self) -> None:
        """step 后本地参数已拉取。"""
        server = AsyncParameterServer({"w": np.array([1.0, 2.0])})
        worker = AsyncWorker(0, server, lambda p: {"w": np.zeros(2)})
        worker.step()
        assert worker._local_params is not None
        assert np.allclose(worker._local_params["w"], [1.0, 2.0])


class TestFactoryFunctions:
    """工厂函数测试。"""

    def test_create_async_parameter_server(self) -> None:
        """创建参数服务器工厂。"""
        params = {"w": np.zeros(3)}
        server = create_async_parameter_server(params)
        assert isinstance(server, AsyncParameterServer)
        assert np.allclose(server.pull_parameters()["w"], 0.0)

    def test_create_async_worker(self) -> None:
        """创建工作器工厂。"""
        server = create_async_parameter_server({"w": np.zeros(2)})
        worker = create_async_worker(0, server, lambda p: {"w": np.ones(2)})
        assert isinstance(worker, AsyncWorker)
        assert worker.worker_id == 0

    def test_parallel_to_async_config(self) -> None:
        """并行配置转异步配置。"""
        cfg = parallel_to_async_config(num_workers=8, learning_rate=1e-3)
        assert cfg.num_workers == 8
        assert cfg.learning_rate == 1e-3
        assert cfg.update_interval == 8


class TestRunAsyncTraining:
    """端到端异步训练测试。"""

    def test_run_quadratic(self) -> None:
        """二次函数最小化（端到端）。

        目标：min (w - 3)^2，梯度 = 2*(w - 3)
        """
        def grad_fn(p: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
            return {"w": 2.0 * (p["w"] - 3.0)}

        cfg = AsyncConfig(
            num_workers=4,
            update_interval=1,
            learning_rate=0.01,
        )
        final_params, stats = run_async_training(
            initial_params={"w": np.array([0.0])},
            grad_fn=grad_fn,
            config=cfg,
            total_steps=100,
        )
        # 参数应向 3 靠拢
        assert final_params["w"][0] > 0.5
        assert stats.total_gradients == 400  # 4 workers * 100 steps

    def test_run_multi_param(self) -> None:
        """多参数异步训练。"""
        def grad_fn(p: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
            return {
                "w1": 2.0 * p["w1"],
                "w2": 2.0 * (p["w2"] - 5.0),
            }

        cfg = AsyncConfig(
            num_workers=2,
            update_interval=1,
            learning_rate=0.01,
        )
        final_params, stats = run_async_training(
            initial_params={
                "w1": np.array([1.0]),
                "w2": np.array([0.0]),
            },
            grad_fn=grad_fn,
            config=cfg,
            total_steps=50,
        )
        # w1 应向 0 靠拢，w2 应向 5 靠拢
        assert abs(final_params["w1"][0]) < 1.0
        assert final_params["w2"][0] > 0.5
        assert stats.total_gradients == 100


class TestCommercialGapReduction:
    """商业差距缩减验证（对标 A3C / Ray RLlib）。"""

    def test_a3c_aligned(self) -> None:
        """A3C 架构对齐：
        - 多 worker 异步独立采集
        - 共享参数服务器
        - Hogwild! 风格异步更新
        """
        params = {"w": np.array([0.0])}
        cfg = AsyncConfig(
            num_workers=4,
            update_interval=1,
            learning_rate=0.1,
        )
        server = AsyncParameterServer(params, cfg)
        workers = [
            AsyncWorker(i, server, lambda p: {"w": np.array([1.0])}, cfg)
            for i in range(4)
        ]
        threads = [
            threading.Thread(target=w.step_n, args=(10,))
            for w in workers
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        server.force_update()
        # 4 workers * 10 steps = 40 次梯度推送
        assert server.stats.total_gradients == 40
        # 参数应被更新（值减小）
        assert server.pull_parameters()["w"][0] < 0

    def test_hogwild_async_update(self) -> None:
        """Hogwild! 异步更新：无锁读取，有锁写入。"""
        params = {"w": np.array([0.0])}
        cfg = AsyncConfig(update_interval=1, learning_rate=0.01)
        server = AsyncParameterServer(params, cfg)
        # 并发拉取和推送
        results: list[dict[str, np.ndarray]] = []

        def pull_many() -> None:
            for _ in range(20):
                results.append(server.pull_parameters())

        def push_many() -> None:
            for _ in range(20):
                server.push_gradient(0, {"w": np.array([1.0])})

        t1 = threading.Thread(target=pull_many)
        t2 = threading.Thread(target=push_many)
        t1.start()
        t2.start()
        t1.join()
        t2.join()
        # 所有拉取都应成功
        assert len(results) == 20
        # 参数应被更新
        assert server.pull_parameters()["w"][0] < 0

    def test_gradient_clipping_aligned_a3c(self) -> None:
        """梯度裁剪对齐 A3C（防止梯度爆炸）。"""
        params = {"w": np.array([0.0])}
        cfg = AsyncConfig(
            update_interval=1,
            learning_rate=1.0,
            gradient_clip_norm=1.0,
        )
        server = AsyncParameterServer(params, cfg)
        # 大梯度应被裁剪
        server.push_gradient(0, {"w": np.array([100.0])})
        # 裁剪后梯度范数 = 1.0，w_new = 0 - 1.0 * 1.0 = -1.0
        assert np.allclose(server.pull_parameters()["w"], -1.0)

    def test_lr_decay_aligned_ray(self) -> None:
        """学习率衰减对齐 Ray RLlib。"""
        cfg = AsyncConfig(learning_rate=1.0, lr_decay=0.9, min_lr=0.01)
        server = AsyncParameterServer({"w": np.array([0.0])}, cfg)
        lrs = [server.get_current_lr()]
        for _ in range(10):
            lrs.append(server.decay_lr())
        # 学习率应单调递减
        for i in range(1, len(lrs)):
            assert lrs[i] <= lrs[i - 1]
        # 最终学习率不低于 min_lr
        assert lrs[-1] >= 0.01

    def test_worker_independence(self) -> None:
        """worker 独立性：每个 worker 独立计算梯度。"""
        params = {"w": np.array([0.0])}
        cfg = AsyncConfig(update_interval=1, learning_rate=0.1)
        server = AsyncParameterServer(params, cfg)
        # 不同 worker 使用不同梯度函数
        def make_grad_fn(scale: float):
            def grad_fn(p: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
                return {"w": np.array([scale])}
            return grad_fn

        workers = [
            AsyncWorker(i, server, make_grad_fn(float(i + 1)), cfg)
            for i in range(3)
        ]
        for w in workers:
            w.step()
        # 每个 worker 应记录自己的更新
        assert server.stats.worker_updates[0] == 1
        assert server.stats.worker_updates[1] == 1
        assert server.stats.worker_updates[2] == 1

    def test_aggregation_modes_comparison(self) -> None:
        """三种聚合模式对比。"""
        # MEAN
        params1 = {"w": np.array([0.0])}
        cfg1 = AsyncConfig(
            update_interval=2,
            learning_rate=1.0,
            aggregation_mode=AggregationMode.MEAN,
        )
        s1 = AsyncParameterServer(params1, cfg1)
        s1.push_gradient(0, {"w": np.array([2.0])})
        s1.push_gradient(1, {"w": np.array([4.0])})
        result1 = s1.pull_parameters()["w"][0]

        # SUM
        params2 = {"w": np.array([0.0])}
        cfg2 = AsyncConfig(
            update_interval=2,
            learning_rate=1.0,
            aggregation_mode=AggregationMode.SUM,
        )
        s2 = AsyncParameterServer(params2, cfg2)
        s2.push_gradient(0, {"w": np.array([2.0])})
        s2.push_gradient(1, {"w": np.array([4.0])})
        result2 = s2.pull_parameters()["w"][0]

        # MEAN: (2+4)/2 = 3, w = -3
        # SUM: 2+4 = 6, w = -6
        assert abs(result1 - (-3.0)) < 1e-6
        assert abs(result2 - (-6.0)) < 1e-6
        # SUM 更新幅度更大
        assert abs(result2) > abs(result1)
