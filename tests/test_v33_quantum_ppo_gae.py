"""v3.3-Q PPO/GAE Bug 回归测试。

Bug 清单:
- #v3.3-Q-1: PPO 梯度截断实现错误
- #v3.3-Q-2: GAE V(s)=0 边界处理错误

文献:
- Schulman et al., PPO, arXiv:1707.06347, 2017.
  URL: https://arxiv.org/abs/1707.06347
- Schulman et al., GAE, ICLR 2016.
  URL: https://arxiv.org/abs/1506.02438
- Sutton & Barto, Reinforcement Learning: An Introduction, 2nd ed., 2018.
  URL: http://incompleteideas.net/book/the-book-2nd.html
- Mnih et al., A3C, ICML 2016.
  URL: http://proceedings.mlr.press/v48/mniha16.html
- Williams, REINFORCE, MLJ 1992.
  URL: https://link.springer.com/article/10.1007/BF00992696
"""

from __future__ import annotations

import numpy as np
import pytest

from polaris.quantum.quantum_circuit_distributed import (
    DistributedPPOConfig,
    DistributedPPOTrainer,
    _PolicyNetwork,
    _ValueNetwork,
)


class TestPPOGradientClipping:
    """#v3.3-Q-1: PPO 梯度截断回归测试。"""

    def test_clip_loss_formula(self):
        """PPO-Clip loss 公式正确性验证。"""
        policy = _PolicyNetwork(obs_dim=4, action_dim=2, lr=0.0)
        rng = np.random.default_rng(42)

        obs = rng.normal(0, 1, (10, 4))
        actions = rng.integers(0, 2, 10)
        old_log_probs, _, _ = policy.evaluate(obs, actions)
        advantages = rng.normal(0, 1, 10)
        clip_ratio = 0.2

        loss_info = policy.update(
            obs, actions, old_log_probs, advantages,
            clip_ratio=clip_ratio, entropy_coeff=0.0,
        )

        new_log_probs, _, _ = policy.evaluate(obs, actions)
        ratios = np.exp(new_log_probs - old_log_probs)

        clipped = np.clip(ratios, 1 - clip_ratio, 1 + clip_ratio)
        surr1 = ratios * advantages
        surr2 = clipped * advantages
        expected_loss = -np.mean(np.minimum(surr1, surr2))

        assert np.isclose(loss_info["policy_loss"], expected_loss, rtol=1e-8), (
            f"PPO loss 公式错误: {loss_info['policy_loss']} vs {expected_loss}"
        )

    def test_clipped_upper_bound_zero_gradient(self):
        """A>0 且 ratio>1+ε 时（上界截断），梯度应为 0。"""
        policy = _PolicyNetwork(obs_dim=4, action_dim=2, lr=1e-3)
        rng = np.random.default_rng(42)

        obs = rng.normal(0, 1, (1, 4))
        actions = np.array([0], dtype=np.int64)

        old_log_probs_before, _, _ = policy.evaluate(obs, actions)
        old_log_probs = old_log_probs_before - 10.0
        advantages = np.array([1.0])

        params_before = [p.copy() for p in policy._params()]
        policy.update(
            obs, actions, old_log_probs, advantages,
            clip_ratio=0.2, entropy_coeff=0.0,
        )
        params_after = policy._params()

        total_change = sum(
            np.sum(np.abs(p_after - p_before))
            for p_before, p_after in zip(params_before, params_after)
        )

        assert total_change < 1e-8, (
            f"上界截断样本不应有梯度更新，但参数变化量为 {total_change}"
        )

    def test_clipped_lower_bound_zero_gradient(self):
        """A<0 且 ratio<1-ε 时（下界截断），梯度应为 0。"""
        policy = _PolicyNetwork(obs_dim=4, action_dim=2, lr=1e-3)
        rng = np.random.default_rng(42)

        obs = rng.normal(0, 1, (1, 4))
        actions = np.array([0], dtype=np.int64)

        old_log_probs_before, _, _ = policy.evaluate(obs, actions)
        old_log_probs = old_log_probs_before + 10.0
        advantages = np.array([-1.0])

        params_before = [p.copy() for p in policy._params()]
        policy.update(
            obs, actions, old_log_probs, advantages,
            clip_ratio=0.2, entropy_coeff=0.0,
        )
        params_after = policy._params()

        total_change = sum(
            np.sum(np.abs(p_after - p_before))
            for p_before, p_after in zip(params_before, params_after)
        )

        assert total_change < 1e-8, (
            f"下界截断样本不应有梯度更新，但参数变化量为 {total_change}"
        )

    def test_unclipped_samples_have_gradient(self):
        """未截断的样本（ratio=1）应有非零梯度。"""
        policy = _PolicyNetwork(obs_dim=4, action_dim=2, lr=1e-2)
        rng = np.random.default_rng(42)

        obs = rng.normal(0, 1, (5, 4))
        actions = rng.integers(0, 2, 5)
        old_log_probs, _, _ = policy.evaluate(obs, actions)
        advantages = rng.normal(0, 1, 5)

        params_before = [p.copy() for p in policy._params()]
        policy.update(
            obs, actions, old_log_probs, advantages,
            clip_ratio=0.2, entropy_coeff=0.0,
        )
        params_after = policy._params()

        total_change = sum(
            np.sum(np.abs(p_after - p_before))
            for p_before, p_after in zip(params_before, params_after)
        )

        assert total_change > 1e-6, (
            f"未截断样本应有梯度更新，但参数变化量为 {total_change}"
        )

    def test_gradient_all_logits(self):
        """softmax 梯度应影响所有 logits，不仅是所选动作。"""
        policy = _PolicyNetwork(obs_dim=4, action_dim=3, lr=1e-2)
        rng = np.random.default_rng(42)

        obs = rng.normal(0, 1, (1, 4))
        actions = np.array([0], dtype=np.int64)
        old_log_probs, _, _ = policy.evaluate(obs, actions)
        advantages = np.array([1.0])

        W3_before = policy.W3.copy()
        policy.update(
            obs, actions, old_log_probs, advantages,
            clip_ratio=0.5, entropy_coeff=0.0,
        )
        W3_change = np.abs(policy.W3 - W3_before)

        assert np.any(W3_change[:, 1] > 1e-10) or np.any(W3_change[:, 2] > 1e-10), (
            "非选动作的 logits 也应有梯度更新（softmax 全连接）"
        )

    def test_ratio_sign_positive_advantage(self):
        """正优势时，策略更新应增加所选动作概率。"""
        policy = _PolicyNetwork(obs_dim=4, action_dim=2, lr=1e-2)
        rng = np.random.default_rng(42)

        obs = rng.normal(0, 1, (10, 4))
        actions = np.zeros(10, dtype=np.int64)
        old_log_probs, _, old_probs = policy.evaluate(obs, actions)
        advantages = np.ones(10) * 2.0

        policy.update(
            obs, actions, old_log_probs, advantages,
            clip_ratio=0.5, entropy_coeff=0.0,
        )

        _, _, new_probs = policy.evaluate(obs, actions)
        avg_prob_old = np.mean(old_probs[:, 0])
        avg_prob_new = np.mean(new_probs[:, 0])

        assert avg_prob_new > avg_prob_old, (
            f"正优势应增加动作概率: {avg_prob_old:.4f} → {avg_prob_new:.4f}"
        )


class TestGAEBoundaryHandling:
    """#v3.3-Q-2: GAE 终止状态边界处理回归测试。"""

    def test_terminal_state_not_bootstrapped(self):
        """终止状态 s_{T+1} 不应 bootstrap（乘 0 mask）。

        验证: 即使 next_values[T] 很大，只要 dones[T]=True，
        最后一步的 TD error 就不应受 next_values[T] 影响。
        """
        trainer = DistributedPPOTrainer(DistributedPPOConfig(obs_dim=4, action_dim=2))

        rewards = np.array([1.0, 1.0])
        values = np.array([0.0, 0.0])
        dones = np.array([False, True])

        next_values_small = np.array([0.0, 0.0])
        next_values_large = np.array([0.0, 999.0])

        _, returns_small = trainer._compute_gae(
            rewards, values, next_values_small, dones,
            gamma=0.99, lam=0.95,
        )
        _, returns_large = trainer._compute_gae(
            rewards, values, next_values_large, dones,
            gamma=0.99, lam=0.95,
        )

        assert np.allclose(returns_small, returns_large, rtol=1e-8), (
            "终止状态的 next_value 不应影响 returns（terminal mask 应为 0）"
        )

    def test_non_terminal_uses_bootstrap(self):
        """非终止状态应使用 V(s_{t+1}) 进行 bootstrap。

        验证: 改变 next_value 会改变 advantage 和 return。
        """
        trainer = DistributedPPOTrainer(DistributedPPOConfig(obs_dim=4, action_dim=2))

        rewards = np.array([1.0])
        values = np.array([0.5])
        dones = np.array([False])

        nv_low = np.array([0.0])
        nv_high = np.array([10.0])

        _, returns_low = trainer._compute_gae(
            rewards, values, nv_low, dones, gamma=0.99, lam=0.95,
        )
        _, returns_high = trainer._compute_gae(
            rewards, values, nv_high, dones, gamma=0.99, lam=0.95,
        )

        assert returns_high[0] > returns_low[0], (
            "非终止状态的 next_value 越大，return 应越大"
        )

    def test_episode_boundary_separation(self):
        """多 episode 连接时，优势估计不应跨 episode 传播。

        验证: done 标志应切断 GAE 的反向传播。
        """
        trainer = DistributedPPOTrainer(DistributedPPOConfig(obs_dim=4, action_dim=2))

        rewards = np.array([100.0, 0.0, 0.0])
        values = np.zeros(3)
        next_values = np.zeros(3)
        dones = np.array([True, False, False])

        _, returns = trainer._compute_gae(
            rewards, values, next_values, dones,
            gamma=0.99, lam=0.95,
        )

        assert returns[0] == 100.0, "第一步 done，return 应等于 reward"
        assert returns[1] == 0.0 and returns[2] == 0.0, (
            "后续 episode 不应受前一 episode 的大奖励影响"
        )

    def test_returns_consistent_with_advantage(self):
        """returns 与 advantage 的一致性（未标准化前）。

        验证: 单步无 discount (gamma=1, lambda=1, 无标准化) 时，
        return = r + V(s') * (1-done)
        """
        trainer = DistributedPPOTrainer(DistributedPPOConfig(obs_dim=4, action_dim=2))

        rewards = np.array([5.0])
        values = np.array([2.0])
        next_values = np.array([3.0])
        dones = np.array([False])

        _, returns = trainer._compute_gae(
            rewards, values, next_values, dones,
            gamma=1.0, lam=1.0,
        )

        expected_return = 5.0 + 3.0
        assert np.isclose(returns[0], expected_return, rtol=1e-8), (
            f"return 计算错误: {returns[0]} vs {expected_return}"
        )

    def test_terminal_return_equals_reward(self):
        """终止状态的 return 应等于该步 reward（无未来）。"""
        trainer = DistributedPPOTrainer(DistributedPPOConfig(obs_dim=4, action_dim=2))

        rewards = np.array([7.0])
        values = np.array([100.0])
        next_values = np.array([999.0])
        dones = np.array([True])

        _, returns = trainer._compute_gae(
            rewards, values, next_values, dones,
            gamma=0.99, lam=0.95,
        )

        assert np.isclose(returns[0], 7.0, rtol=1e-8), (
            "终止状态 return 应等于 reward（不 bootstrap）"
        )

    def test_value_network_in_training(self):
        """训练中 Value Network 应参与 GAE 计算。"""
        config = DistributedPPOConfig(
            n_workers=2, obs_dim=4, action_dim=2, n_epochs=1,
            batch_size=8, n_devices_per_circuit=100,
        )
        trainer = DistributedPPOTrainer(config)

        result = trainer.training_step(n_episodes_per_worker=3)

        assert "mean_value_loss" in result, "训练结果应包含 value_loss"
        assert result["mean_value_loss"] >= 0.0, "value_loss 应为非负"
        assert result["n_rollout_steps"] > 0, "应采集到 rollout 数据"


class TestEndToEndTraining:
    """端到端训练冒烟测试。"""

    def test_distributed_ppo_runs(self):
        """分布式 PPO 训练应能正常运行。"""
        config = DistributedPPOConfig(
            n_workers=2, obs_dim=8, action_dim=4,
            n_epochs=2, batch_size=16, n_devices_per_circuit=100,
        )
        trainer = DistributedPPOTrainer(config)

        result = trainer.training_step(n_episodes_per_worker=2)

        assert result["n_workers"] == 2
        assert result["episodes_this_step"] == 4
        assert result["total_episodes"] == 4
        assert result["mean_policy_loss"] is not None
        assert result["mean_value_loss"] is not None
        assert result["best_reward"] > -float("inf")

    def test_progressive_scaling(self):
        """渐进式规模扩展应正常工作。"""
        config = DistributedPPOConfig(
            n_workers=2, obs_dim=4, action_dim=2,
            n_epochs=1, batch_size=8,
        )
        trainer = DistributedPPOTrainer(config)

        stages = trainer.progressive_scaling(target_devices=1000)

        assert len(stages) == 5
        assert stages[-1]["stage_devices"] == 1000
        assert all("mean_reward" in s for s in stages)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
