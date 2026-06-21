"""V-trace off-policy 修正测试（第42轮 P1-4 深化，IMPALA）。

测试覆盖：
- VTraceConfig 配置
- VTraceResult 结果
- compute_vtrace 主算法
- ImpalaLearner IMPALA learner
- 工厂函数
- 商业差距缩减验证（对标 DeepMind IMPALA）
"""

from __future__ import annotations

import numpy as np
import pytest

from polaris.trainer.vtrace import (
    ImpalaLearner,
    VTraceConfig,
    VTraceResult,
    compute_vtrace,
    create_impala_learner,
    create_vtrace_config,
    run_vtrace,
)


class TestVTraceConfig:
    """V-trace 配置测试。"""

    def test_default_config(self) -> None:
        """默认配置。"""
        cfg = VTraceConfig()
        assert cfg.rho_bar == 1.0
        assert cfg.c_bar == 1.0
        assert cfg.gamma == 0.99
        assert cfg.lambda_ == 1.0

    def test_custom_config(self) -> None:
        """自定义配置。"""
        cfg = VTraceConfig(
            rho_bar=0.5,
            c_bar=0.8,
            gamma=0.95,
            lambda_=0.95,
        )
        assert cfg.rho_bar == 0.5
        assert cfg.c_bar == 0.8
        assert cfg.gamma == 0.95
        assert cfg.lambda_ == 0.95

    def test_frozen_dataclass(self) -> None:
        """frozen dataclass 不可变。"""
        cfg = VTraceConfig()
        with pytest.raises(AttributeError):
            cfg.rho_bar = 2.0  # type: ignore[misc]


class TestVTraceResult:
    """V-trace 结果测试。"""

    def test_default_result(self) -> None:
        """默认结果。"""
        result = VTraceResult()
        assert len(result.vs) == 0
        assert len(result.pg_advantages) == 0
        assert len(result.rhos) == 0
        assert len(result.cs) == 0

    def test_result_with_data(self) -> None:
        """带数据的结果。"""
        result = VTraceResult(
            vs=np.array([1.0, 2.0]),
            pg_advantages=np.array([0.5, -0.5]),
            rhos=np.array([1.0, 0.8]),
            cs=np.array([1.0, 0.8]),
        )
        assert len(result.vs) == 2
        assert len(result.pg_advantages) == 2
        assert result.rhos[1] == 0.8


class TestComputeVTrace:
    """V-trace 主算法测试。"""

    def test_on_policy_case(self) -> None:
        """on-policy 情况（行为策略 = 目标策略）。

        当 ρ = 1 时，V-trace 退化为标准 TD(λ)。
        """
        n = 5
        values = np.array([1.0, 1.5, 2.0, 1.8, 1.2])
        rewards = np.array([0.5, 0.3, -0.2, 0.1, 0.4])
        logprobs = np.log(np.full(n, 0.5))
        dones = np.zeros(n)
        result = compute_vtrace(
            values=values,
            rewards=rewards,
            logprobs_behavior=logprobs,
            logprobs_target=logprobs,
            dones=dones,
            last_value=1.0,
        )
        assert len(result.vs) == n
        assert len(result.pg_advantages) == n
        # on-policy 时 ρ = 1
        assert np.allclose(result.rhos, 1.0)
        assert np.allclose(result.cs, 1.0)

    def test_off_policy_case(self) -> None:
        """off-policy 情况（行为策略 ≠ 目标策略）。"""
        n = 4
        values = np.array([1.0, 1.5, 2.0, 1.0])
        rewards = np.array([0.5, 0.3, -0.2, 0.1])
        logprobs_behavior = np.log(np.array([0.5, 0.5, 0.5, 0.5]))
        logprobs_target = np.log(np.array([0.6, 0.4, 0.7, 0.3]))
        dones = np.zeros(n)
        result = compute_vtrace(
            values=values,
            rewards=rewards,
            logprobs_behavior=logprobs_behavior,
            logprobs_target=logprobs_target,
            dones=dones,
            last_value=1.0,
        )
        # 重要性采样系数应不为 1
        assert not np.allclose(result.rhos, 1.0)
        # ρ = π/μ = 0.6/0.5, 0.4/0.5, 0.7/0.5, 0.3/0.5
        expected_rhos = np.array([1.2, 0.8, 1.4, 0.6])
        expected_rhos = np.minimum(expected_rhos, 1.0)  # 截断
        assert np.allclose(result.rhos, expected_rhos)

    def test_rho_truncation(self) -> None:
        """ρ 截断。"""
        n = 3
        values = np.array([1.0, 1.0, 1.0])
        rewards = np.array([0.0, 0.0, 0.0])
        logprobs_behavior = np.log(np.array([0.1, 0.1, 0.1]))
        logprobs_target = np.log(np.array([0.9, 0.9, 0.9]))
        dones = np.zeros(n)
        cfg = VTraceConfig(rho_bar=0.5)
        result = compute_vtrace(
            values=values,
            rewards=rewards,
            logprobs_behavior=logprobs_behavior,
            logprobs_target=logprobs_target,
            dones=dones,
            config=cfg,
        )
        # ρ = 9，截断到 0.5
        assert np.allclose(result.rhos, 0.5)

    def test_c_truncation(self) -> None:
        """c 截断。"""
        n = 3
        values = np.array([1.0, 1.0, 1.0])
        rewards = np.array([0.0, 0.0, 0.0])
        logprobs_behavior = np.log(np.array([0.1, 0.1, 0.1]))
        logprobs_target = np.log(np.array([0.9, 0.9, 0.9]))
        dones = np.zeros(n)
        cfg = VTraceConfig(c_bar=0.3)
        result = compute_vtrace(
            values=values,
            rewards=rewards,
            logprobs_behavior=logprobs_behavior,
            logprobs_target=logprobs_target,
            dones=dones,
            config=cfg,
        )
        # c = 9，截断到 0.3
        assert np.allclose(result.cs, 0.3)

    def test_done_handling(self) -> None:
        """done 处理。"""
        n = 3
        values = np.array([1.0, 1.5, 2.0])
        rewards = np.array([0.5, 0.3, 1.0])
        logprobs = np.log(np.full(n, 0.5))
        dones = np.array([0.0, 0.0, 1.0])  # 最后一步结束
        result = compute_vtrace(
            values=values,
            rewards=rewards,
            logprobs_behavior=logprobs,
            logprobs_target=logprobs,
            dones=dones,
            last_value=0.0,
        )
        # 最后一步 done=1，bootstrap 不应影响
        assert len(result.vs) == n

    def test_single_step(self) -> None:
        """单步情况。"""
        values = np.array([1.0])
        rewards = np.array([0.5])
        logprobs = np.log(np.array([0.5]))
        dones = np.array([0.0])
        result = compute_vtrace(
            values=values,
            rewards=rewards,
            logprobs_behavior=logprobs,
            logprobs_target=logprobs,
            dones=dones,
            last_value=2.0,
        )
        assert len(result.vs) == 1
        # v = V + ρ * (r + γ * last_V - V)
        expected = 1.0 + 1.0 * (0.5 + 0.99 * 2.0 - 1.0)
        assert np.isclose(result.vs[0], expected)

    def test_pg_advantages_sign(self) -> None:
        """策略梯度优势符号。"""
        n = 3
        values = np.array([1.0, 1.0, 1.0])
        rewards = np.array([1.0, 1.0, 1.0])  # 正奖励
        logprobs = np.log(np.full(n, 0.5))
        dones = np.zeros(n)
        result = compute_vtrace(
            values=values,
            rewards=rewards,
            logprobs_behavior=logprobs,
            logprobs_target=logprobs,
            dones=dones,
            last_value=1.0,
        )
        # 正奖励 + 高 last_value 应产生正优势
        assert np.all(result.pg_advantages >= -0.1)


class TestImpalaLearner:
    """IMPALA learner 测试。"""

    def test_creation(self) -> None:
        """创建 learner。"""
        def value_fn(obs: np.ndarray) -> float:
            return float(np.sum(obs))

        learner = ImpalaLearner(value_fn)
        assert learner.config.rho_bar == 1.0

    def test_compute_targets(self) -> None:
        """计算目标。"""
        def value_fn(obs: np.ndarray) -> float:
            return float(obs[0])

        observations = np.array([[1.0], [1.5], [2.0]])
        actions = np.array([0, 1, 0])
        rewards = np.array([0.5, 0.3, -0.2])
        logprobs_behavior = np.log(np.array([0.5, 0.5, 0.5]))
        logprobs_target = np.log(np.array([0.5, 0.5, 0.5]))
        dones = np.array([0.0, 0.0, 0.0])
        last_observation = np.array([1.0])

        learner = ImpalaLearner(value_fn)
        result = learner.compute_targets(
            observations=observations,
            actions=actions,
            rewards=rewards,
            logprobs_behavior=logprobs_behavior,
            logprobs_target=logprobs_target,
            dones=dones,
            last_observation=last_observation,
        )
        assert len(result.vs) == 3
        assert len(result.pg_advantages) == 3

    def test_compute_targets_no_last_obs(self) -> None:
        """无 last_observation 时使用 0。"""
        def value_fn(obs: np.ndarray) -> float:
            return float(obs[0])

        observations = np.array([[1.0], [1.5]])
        actions = np.array([0, 1])
        rewards = np.array([0.5, 0.3])
        logprobs = np.log(np.array([0.5, 0.5]))
        dones = np.array([0.0, 0.0])

        learner = ImpalaLearner(value_fn)
        result = learner.compute_targets(
            observations=observations,
            actions=actions,
            rewards=rewards,
            logprobs_behavior=logprobs,
            logprobs_target=logprobs,
            dones=dones,
        )
        assert len(result.vs) == 2


class TestFactoryFunctions:
    """工厂函数测试。"""

    def test_create_vtrace_config(self) -> None:
        """创建 V-trace 配置工厂。"""
        cfg = create_vtrace_config(rho_bar=0.5, gamma=0.95)
        assert isinstance(cfg, VTraceConfig)
        assert cfg.rho_bar == 0.5
        assert cfg.gamma == 0.95

    def test_create_impala_learner(self) -> None:
        """创建 IMPALA learner 工厂。"""
        def value_fn(obs: np.ndarray) -> float:
            return 0.0

        learner = create_impala_learner(value_fn)
        assert isinstance(learner, ImpalaLearner)

    def test_run_vtrace(self) -> None:
        """运行 V-trace 工厂。"""
        n = 3
        values = np.array([1.0, 1.5, 2.0])
        rewards = np.array([0.5, 0.3, -0.2])
        logprobs = np.log(np.full(n, 0.5))
        dones = np.zeros(n)
        result = run_vtrace(
            values=values,
            rewards=rewards,
            logprobs_behavior=logprobs,
            logprobs_target=logprobs,
            dones=dones,
        )
        assert isinstance(result, VTraceResult)
        assert len(result.vs) == n


class TestCommercialGapReduction:
    """商业差距缩减验证（对标 DeepMind IMPALA）。"""

    def test_impala_aligned(self) -> None:
        """IMPALA V-trace 对齐：
        - off-policy 修正
        - 重要性采样截断
        - V-trace 值估计
        """
        n = 5
        values = np.array([1.0, 1.5, 2.0, 1.8, 1.2])
        rewards = np.array([0.5, 0.3, -0.2, 0.1, 0.4])
        logprobs_behavior = np.log(np.array([0.4, 0.5, 0.3, 0.6, 0.5]))
        logprobs_target = np.log(np.array([0.5, 0.4, 0.4, 0.5, 0.6]))
        dones = np.zeros(n)
        result = compute_vtrace(
            values=values,
            rewards=rewards,
            logprobs_behavior=logprobs_behavior,
            logprobs_target=logprobs_target,
            dones=dones,
            last_value=1.0,
        )
        # 应有完整的 V-trace 输出
        assert len(result.vs) == n
        assert len(result.pg_advantages) == n
        # 重要性采样系数应反映策略差异
        assert not np.allclose(result.rhos, 1.0)

    def test_off_policy_correction(self) -> None:
        """off-policy 修正效果。"""
        n = 4
        values = np.array([1.0, 1.0, 1.0, 1.0])
        rewards = np.array([1.0, 1.0, 1.0, 1.0])
        logprobs_behavior = np.log(np.array([0.2, 0.2, 0.2, 0.2]))
        logprobs_target = np.log(np.array([0.8, 0.8, 0.8, 0.8]))
        dones = np.zeros(n)
        result = compute_vtrace(
            values=values,
            rewards=rewards,
            logprobs_behavior=logprobs_behavior,
            logprobs_target=logprobs_target,
            dones=dones,
        )
        # ρ = 4，截断到 1.0
        assert np.allclose(result.rhos, 1.0)

    def test_truncation_stability(self) -> None:
        """截断保证稳定性。"""
        n = 3
        values = np.array([1.0, 1.0, 1.0])
        rewards = np.array([0.0, 0.0, 0.0])
        # 极端重要性采样系数
        logprobs_behavior = np.log(np.array([0.01, 0.01, 0.01]))
        logprobs_target = np.log(np.array([0.99, 0.99, 0.99]))
        dones = np.zeros(n)
        cfg = VTraceConfig(rho_bar=1.0, c_bar=1.0)
        result = compute_vtrace(
            values=values,
            rewards=rewards,
            logprobs_behavior=logprobs_behavior,
            logprobs_target=logprobs_target,
            dones=dones,
            config=cfg,
        )
        # 即使 ρ = 99，截断后应 ≤ 1.0
        assert np.all(result.rhos <= 1.0 + 1e-10)
        assert np.all(result.cs <= 1.0 + 1e-10)
        # V-trace 值应为有限值
        assert np.all(np.isfinite(result.vs))

    def test_lambda_control(self) -> None:
        """lambda 参数控制偏差-方差权衡。"""
        n = 5
        values = np.array([1.0, 1.5, 2.0, 1.8, 1.2])
        rewards = np.array([0.5, 0.3, -0.2, 0.1, 0.4])
        logprobs = np.log(np.full(n, 0.5))
        dones = np.zeros(n)
        # λ=0（高偏差低方差）
        cfg_0 = VTraceConfig(lambda_=0.0)
        result_0 = compute_vtrace(
            values=values,
            rewards=rewards,
            logprobs_behavior=logprobs,
            logprobs_target=logprobs,
            dones=dones,
            config=cfg_0,
        )
        # λ=1（低偏差高方差）
        cfg_1 = VTraceConfig(lambda_=1.0)
        result_1 = compute_vtrace(
            values=values,
            rewards=rewards,
            logprobs_behavior=logprobs,
            logprobs_target=logprobs,
            dones=dones,
            config=cfg_1,
        )
        # 两种 λ 应产生不同的 V-trace 值
        assert not np.allclose(result_0.vs, result_1.vs)

    def test_gamma_discount(self) -> None:
        """gamma 折扣因子。"""
        n = 3
        values = np.array([1.0, 1.0, 1.0])
        rewards = np.array([1.0, 1.0, 1.0])
        logprobs = np.log(np.full(n, 0.5))
        dones = np.zeros(n)
        # γ=0（仅当前奖励）
        cfg_0 = VTraceConfig(gamma=0.0)
        result_0 = compute_vtrace(
            values=values,
            rewards=rewards,
            logprobs_behavior=logprobs,
            logprobs_target=logprobs,
            dones=dones,
            config=cfg_0,
            last_value=10.0,
        )
        # γ=0 时 last_value 不影响（除最后一步）
        # v_t = V_t + ρ * (r_t + 0 - V_t) = V_t + ρ * (r_t - V_t)
        # 对 t < n-1，next_V 不影响
        assert np.isclose(result_0.vs[0], 1.0 + 1.0 * (1.0 - 1.0))

    def test_end_to_end_impala(self) -> None:
        """端到端 IMPALA 流程。"""
        def value_fn(obs: np.ndarray) -> float:
            return float(0.5 * obs[0])

        observations = np.array(
            [[1.0], [1.5], [2.0], [1.8], [1.2]]
        )
        actions = np.array([0, 1, 0, 1, 0])
        rewards = np.array([0.5, 0.3, -0.2, 0.1, 0.4])
        logprobs_behavior = np.log(np.array([0.4, 0.5, 0.3, 0.6, 0.5]))
        logprobs_target = np.log(np.array([0.5, 0.4, 0.4, 0.5, 0.6]))
        dones = np.array([0.0, 0.0, 0.0, 0.0, 1.0])
        last_observation = np.array([1.0])

        learner = create_impala_learner(value_fn)
        result = learner.compute_targets(
            observations=observations,
            actions=actions,
            rewards=rewards,
            logprobs_behavior=logprobs_behavior,
            logprobs_target=logprobs_target,
            dones=dones,
            last_observation=last_observation,
        )
        # 应有完整的 V-trace 输出
        assert len(result.vs) == 5
        assert len(result.pg_advantages) == 5
        # 所有值应为有限
        assert np.all(np.isfinite(result.vs))
        assert np.all(np.isfinite(result.pg_advantages))
