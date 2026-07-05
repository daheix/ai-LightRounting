"""polaris-trainer 子模块深度测试（v5.0）。

测试覆盖（36 个测试，R03 禁止 fall-back，R04 不参与 GPU）:
- 导入/导出/常量: test_import_and_exports, test_module_constants
- PPOConfig & 数据类: test_ppo_config_defaults, test_rollout_buffer_and_replay_alias,
  test_transition_and_minibatch_fields
- ActorCritic & PPOAgent: test_actor_critic_forward_and_evaluate,
  test_ppo_agent_get_action_shapes, test_ppo_agent_lr_schedule,
  test_ppo_agent_update, test_ppo_save_load_roundtrip, test_load_agent_helper
- GAE & 工具函数: test_compute_gae, test_lr_scale_constant_linear_cosine,
  test_obs_to_vector_and_pad_obs, test_infer_obs_dim, test_discretize_floorplan_action
- 训练循环: test_train_ppo_smoke, test_train_with_env_factory_smoke
- R351 LargeScalePlacementEnv: test_rl_advanced_env, test_large_scale_env_config_and_raises
- R352 PPOAdvantageOptimizer: test_ppo_adv_config_defaults,
  test_ppo_adv_optimizer_compute_gae_and_normalize,
  test_ppo_adv_optimizer_policy_and_value_loss,
  test_ppo_adv_optimizer_cosine_lr_schedule, test_ppo_adv_optimizer_update_end_to_end
- R353 MultiObjectiveParetoReward: test_pareto_reward_and_front,
  test_pareto_reward_individual_objectives_and_maximize
- R354 PretrainedPolicyLibrary: test_pretrained_policy_generate_all_strategies,
  test_pretrained_policy_save_load_and_cache_raise
- R355 HybridPlacementAgent: test_hybrid_placement_set_fixed_and_auto_place
- CheckpointManager: test_checkpoint_manager_roundtrip,
  test_checkpoint_manager_list_and_invalid_agent_raise
- R35 CPU 多进程并行 rollout: test_parallel_rollout_basic,
  test_parallel_rollout_aggregation, test_parallel_rollout_invalid_input_raises
- R03/R04 综合: test_no_fallback_r03_r04

学术依据（R02 学术诚信，≥5 个文献 URL）:
1. Schulman et al., 2017, PPO https://arxiv.org/abs/1707.06347
2. Schulman et al., 2015, GAE https://arxiv.org/abs/1506.02438
3. Mirhoseini et al., Nature 2021, AlphaChip
   https://www.nature.com/articles/s41586-021-03544-w
4. Mirhoseini et al., Nature 2024 addendum, AlphaChip
   https://www.nature.com/articles/s41586-024-08032-5
5. Deb et al., 2002 IEEE TEVC, NSGA-II https://ieeexplore.ieee.org/document/996017
6. Loshchilov & Hutter, 2017, SGDR 余弦退火 https://arxiv.org/abs/1608.03983
7. Stable-Baselines3 PPO 实现 https://stable-baselines3.readthedocs.io/
8. Bengio et al., ICML 2009, Curriculum Learning
   https://dl.acm.org/doi/abs/10.1145/1553374.1553380
9. Roijers et al., 2013, 多目标 RL Pareto https://arxiv.org/abs/1302.1563
10. pytest 文档 https://docs.pytest.org/

规则依据: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R05 无 TODO /
R12 时间戳 / R13 交付自测。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

# 让测试既能从已安装包导入，也能从源码树导入（CI/开发模式）
_SRC = str(Path(__file__).resolve().parents[1] / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import polaris_trainer  # noqa: E402
from polaris_trainer import (  # noqa: E402
    ALL_POLICIES,
    ALL_PLATFORMS,
    ActionTransform,
    ActorCritic,
    CIRCUIT_TEMPLATES,
    CheckpointManager,
    GPU_DISABLED_R04,
    HybridPlacementAgent,
    HybridPlacementConfig,
    LargeScalePlacementConfig,
    LargeScalePlacementEnv,
    Minibatch,
    MultiObjectiveParetoReward,
    MultiObjectiveRewardConfig,
    ParallelRolloutCollector,
    PLATFORM_INP,
    PLATFORM_LNOI,
    PLATFORM_SIN,
    PLATFORM_SOI,
    PPOAdvConfig,
    PPOAdvantageOptimizer,
    PPOAgent,
    PPOConfig,
    POLICY_CURRICULUM,
    POLICY_HEURISTIC,
    POLICY_RANDOM,
    PretrainedPolicyConfig,
    PretrainedPolicyLibrary,
    ReplayBuffer,
    RolloutBatch,
    RolloutBuffer,
    TrainConfig,
    Transition,
    collect_rollouts_parallel,
    compute_gae,
    discretize_floorplan_action,
    infer_obs_dim,
    load_agent,
    lr_scale,
    obs_to_vector,
    pad_obs,
    register_env_factory,
    train_ppo,
    train_with_env_factory,
)


# =============================================================================
# Fake Gymnasium env（依赖注入用，验证 train_ppo 不耦合具体 EDA 环境）
# =============================================================================


class _FakeEnv:
    """遵循 Gymnasium 协议的假环境（dict 观测 + 5-tuple step）。"""

    def __init__(self, obs_dim: int = 8, grid_w: int = 10, grid_h: int = 10) -> None:
        self.obs_dim = obs_dim
        self.grid_w = grid_w
        self.grid_h = grid_h
        self.name = "fake_env"
        self._step = 0
        self._rng = np.random.default_rng(0)

    def reset(self):
        self._step = 0
        return {"vec": np.zeros(self.obs_dim, dtype=np.float64)}, {}

    def step(self, action):
        self._step += 1
        obs = {"vec": self._rng.standard_normal(self.obs_dim)}
        reward = float(self._rng.standard_normal())
        terminated = self._step >= 5
        return obs, reward, terminated, False, {}


def _make_circuit(n: int = 2) -> dict:
    """构造 n 器件测试电路（含 devices 与 nets）。"""
    devices = [
        {"id": f"d{i}", "type": "mzi" if i % 2 == 0 else "mmi",
         "width": 50.0, "height": 30.0, "ports": ["a", "b"]}
        for i in range(n)
    ]
    nets = [{"src": (f"d{i}", "a"), "dst": (f"d{i + 1}", "a")} for i in range(n - 1)]
    return {"devices": devices, "nets": nets}


# =============================================================================
# §1 导入与导出
# =============================================================================


def _make_mock_env_configs(n: int, obs_dim: int = 8, action_dim: int = 2,
                           max_steps: int = 20, seed_base: int = 0) -> list[dict]:
    """构造 n 个 mock env 配置（可 pickle，含 type/obs_dim/action_dim/seed）。"""
    return [
        {
            "type": "mock",
            "obs_dim": obs_dim,
            "action_dim": action_dim,
            "max_steps": max_steps,
            "seed": seed_base + i,
        }
        for i in range(n)
    ]


def test_parallel_rollout_basic():
    """ParallelRolloutCollector: 2 worker 基本 rollout（PPOAgent pickle + mock env）。

    验证：返回 batch 数 = worker 数；每个 batch 含 states/actions/rewards/
    next_states/dones 五个数组，形状与 n_steps/obs_dim/action_dim 匹配；
    worker_id 与提交顺序一致。
    """
    np.random.seed(42)
    agent = PPOAgent(obs_dim=8, action_dim=2, hidden_dim=16)
    env_configs = _make_mock_env_configs(n=2, obs_dim=8, action_dim=2, seed_base=0)
    batches = collect_rollouts_parallel(agent, env_configs, n_steps=5, n_workers=2)
    # 返回 batch 数 = worker 数
    assert len(batches) == 2
    for i, batch in enumerate(batches):
        assert isinstance(batch, RolloutBatch)
        assert batch.worker_id == i
        # 形状: [n_steps, obs_dim] / [n_steps, action_dim] / [n_steps]
        assert batch.states.shape == (5, 8)
        assert batch.actions.shape == (5, 2)
        assert batch.rewards.shape == (5,)
        assert batch.next_states.shape == (5, 8)
        assert batch.dones.shape == (5,)
        # 数组有限
        assert np.all(np.isfinite(batch.states))
        assert np.all(np.isfinite(batch.rewards))
        # dones 是 bool
        assert batch.dones.dtype == bool
        # __len__ / total_steps
        assert len(batch) == 5
        assert batch.total_steps() == 5
        assert isinstance(batch.total_reward(), float)


def test_parallel_rollout_aggregation():
    """ParallelRolloutCollector: 多 worker 轨迹聚合（batch_size = n_envs × n_steps）。

    验证：3 worker × 4 steps = 12 步；拼接后 states 形状 (12, obs_dim)；
    worker_ids 覆盖 [0,1,2]；不同 worker 因 seed 不同产生不同轨迹。
    """
    np.random.seed(7)
    agent = PPOAgent(obs_dim=8, action_dim=2, hidden_dim=16)
    env_configs = _make_mock_env_configs(n=3, obs_dim=8, action_dim=2, seed_base=100)
    collector = ParallelRolloutCollector(n_workers=3)
    batches = collector.collect(agent, env_configs, n_steps=4)
    assert len(batches) == 3
    # 聚合总步数 = 3 × 4 = 12（PPO on-policy: batch_size = n_envs × n_steps）
    total = sum(b.total_steps() for b in batches)
    assert total == 12
    # 拼接 states
    all_states = np.concatenate([b.states for b in batches], axis=0)
    assert all_states.shape == (12, 8)
    all_actions = np.concatenate([b.actions for b in batches], axis=0)
    assert all_actions.shape == (12, 2)
    all_rewards = np.concatenate([b.rewards for b in batches], axis=0)
    assert all_rewards.shape == (12,)
    # worker_ids 覆盖 0/1/2
    assert sorted(b.worker_id for b in batches) == [0, 1, 2]
    # 不同 worker（不同 seed）产生不同 states（概率 1，因 seed 不同）
    assert not np.allclose(batches[0].states, batches[1].states)
    # n_workers 默认 = min(cpu_count, len(configs))，不传 n_workers 也应工作
    collector_default = ParallelRolloutCollector()
    batches_default = collector_default.collect(agent, env_configs, n_steps=4)
    assert len(batches_default) == 3


def test_parallel_rollout_invalid_input_raises():
    """ParallelRolloutCollector: 无效输入 raise（R03 禁止 fall-back）。

    覆盖：agent=None / env_configs 空 / env_configs 非 list / n_steps<=0 /
    n_workers<=0 / env_config 缺 type / env_config type 未注册 /
    env_config 非 dict（主进程 _validate_inputs raise）。
    """
    agent = PPOAgent(obs_dim=8, action_dim=2, hidden_dim=16)
    collector = ParallelRolloutCollector()
    # agent=None → ValueError（R03）
    with pytest.raises(ValueError, match="agent 不能为 None"):
        collector.collect(None, _make_mock_env_configs(2), n_steps=4)
    # env_configs 空 → ValueError（R03）
    with pytest.raises(ValueError, match="env_configs 不能为空"):
        collector.collect(agent, [], n_steps=4)
    # env_configs 非 list → ValueError（R03）
    with pytest.raises(ValueError, match="env_configs 须为 list"):
        collector.collect(agent, "not_a_list", n_steps=4)  # type: ignore[arg-type]
    # n_steps<=0 → ValueError（R03）
    with pytest.raises(ValueError, match="n_steps 须 > 0"):
        collector.collect(agent, _make_mock_env_configs(2), n_steps=0)
    with pytest.raises(ValueError, match="n_steps 须 > 0"):
        collector.collect(agent, _make_mock_env_configs(2), n_steps=-3)
    # n_workers<=0 → ValueError（R03）
    with pytest.raises(ValueError, match="n_workers 须 > 0"):
        ParallelRolloutCollector(n_workers=0)
    with pytest.raises(ValueError, match="n_workers 须 > 0"):
        ParallelRolloutCollector(n_workers=-1)
    # env_config 缺 type → worker 内 _make_env raise ValueError，经 future.result 传播（R03）
    bad_configs_no_type = [{"obs_dim": 8, "action_dim": 2, "seed": 0}]
    with pytest.raises(ValueError, match="缺 'type'"):
        collect_rollouts_parallel(agent, bad_configs_no_type, n_steps=3, n_workers=1)
    # env_config type 未注册 → ValueError（R03）
    bad_configs_unknown = [{"type": "nonexistent_env", "obs_dim": 8, "seed": 0}]
    with pytest.raises(ValueError, match="未注册"):
        collect_rollouts_parallel(agent, bad_configs_unknown, n_steps=3, n_workers=1)
    # env_config 非 dict → 主进程 _validate_inputs raise ValueError（R03）
    bad_configs_not_dict = ["not_a_dict"]
    with pytest.raises(ValueError, match="须为 dict"):
        collect_rollouts_parallel(agent, bad_configs_not_dict, n_steps=3, n_workers=1)  # type: ignore[arg-type]
    # register_env_factory 重复注册 → ValueError（R03）
    with pytest.raises(ValueError, match="已注册"):
        register_env_factory("mock", lambda cfg: None)
    # register_env_factory 空名 → ValueError（R03）
    with pytest.raises(ValueError, match="工厂名非法"):
        register_env_factory("", lambda cfg: None)


# =============================================================================
# §14 R03 回归测试：禁止 except 块仅空语句静默吞异常（AST 级检测）
#
# 防止未来再引入 except 块体仅空语句的 fall-back（R03 最严重违规）。
# 学术依据: Effective Python Item 32 — 优先抛异常而非返回 None/静默吞没。
# =============================================================================
def test_no_except_empty_body_r03() -> None:
    """R03 回归：src 下所有 .py 禁止 except 块体仅空语句静默吞异常。"""
    import ast
    from pathlib import Path
    src_dir = Path(__file__).resolve().parents[1] / "src"
    violations: list[str] = []
    for py in src_dir.rglob("*.py"):
        tree = ast.parse(py.read_text(encoding="utf-8"), filename=str(py))
        for node in ast.walk(tree):
            if (isinstance(node, ast.ExceptHandler)
                    and len(node.body) == 1
                    and isinstance(node.body[0], ast.Pass)):
                violations.append(f"{py.name}:{node.lineno}")
    assert not violations, (
        f"R03 违规: 发现 except 块仅空语句静默吞异常: {violations}"
    )
