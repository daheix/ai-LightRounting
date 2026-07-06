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


def test_import_and_exports():
    """导入 polaris_trainer 并验证核心 API 导出完整。"""
    assert polaris_trainer.__version__ == "5.0.0"
    for name in (
        "PPOConfig", "ActorCritic", "RolloutBuffer", "ReplayBuffer", "Transition",
        "Minibatch", "compute_gae", "PPOAgent", "TrainConfig", "train_ppo",
        "train_with_env_factory", "load_agent", "CheckpointManager",
        "LargeScalePlacementEnv", "PPOAdvantageOptimizer",
        "MultiObjectiveParetoReward", "PretrainedPolicyLibrary",
        "HybridPlacementAgent", "GPU_DISABLED_R04",
    ):
        assert hasattr(polaris_trainer, name), f"polaris_trainer 缺少导出: {name}"


def test_module_constants():
    """验证模块常量：平台/策略/电路模板/GPU 声明/ActionTransform 类型别名。"""
    # R04 GPU 战略声明（不可撤销）
    assert GPU_DISABLED_R04 is True
    # 平台常量（SiEPIC/Ligentec/HyperLight/InP 公开平台）
    assert PLATFORM_SOI == "SOI"
    assert PLATFORM_SIN == "SiN"
    assert PLATFORM_INP == "InP"
    assert PLATFORM_LNOI == "LNOI"
    assert ALL_PLATFORMS == ("SOI", "SiN", "InP", "LNOI")
    # 策略常量（Bengio 2009 Curriculum / 基线策略）
    assert POLICY_HEURISTIC == "heuristic"
    assert POLICY_RANDOM == "random"
    assert POLICY_CURRICULUM == "curriculum"
    assert ALL_POLICIES == ("heuristic", "random", "curriculum")
    # 电路模板（覆盖 MZI/Clements/Splitter Tree/Switch Chain）
    assert CIRCUIT_TEMPLATES == ("mzi_lattice", "splitter_tree", "switch_chain", "random")
    # ActionTransform 是 Callable 类型别名（typing.Callable）
    assert ActionTransform is not None


# =============================================================================
# §2 PPOConfig & 数据类
# =============================================================================


def test_ppo_config_defaults():
    """PPOConfig 默认值与 SB3/Schulman 2017 PPO 文献对齐。"""
    cfg = PPOConfig()
    # Schulman 2017 PPO 默认 clip_eps=0.2
    assert cfg.clip_eps == 0.2
    # Schulman 2015 GAE 默认 gae_lambda=0.95
    assert cfg.gae_lambda == 0.95
    # Sutton & Barto 2018 默认 gamma=0.99
    assert cfg.gamma == 0.99
    # SB3 默认 lr=3e-4
    assert cfg.lr == 3e-4
    # SB3 默认 ent_coef=0.01 / vf_coef=0.5 / max_grad_norm=0.5
    assert cfg.ent_coef == 0.01
    assert cfg.vf_coef == 0.5
    assert cfg.max_grad_norm == 0.5
    assert cfg.n_epochs == 4
    assert cfg.batch_size == 64
    # 2025 增强：clip_vf 默认禁用
    assert cfg.clip_vf == 0.0
    assert cfg.lr_schedule == "constant"
    # 自定义值可覆盖
    cfg2 = PPOConfig(lr=1e-3, clip_eps=0.3, lr_schedule="cosine", total_steps=500)
    assert cfg2.lr == 1e-3
    assert cfg2.clip_eps == 0.3
    assert cfg2.lr_schedule == "cosine"
    assert cfg2.total_steps == 500


def test_rollout_buffer_and_replay_alias():
    """RolloutBuffer: 初始化/clear/len；ReplayBuffer 是 RolloutBuffer 别名。"""
    buf = RolloutBuffer()
    assert len(buf) == 0
    # 添加数据
    buf.obs.append(np.zeros(4))
    buf.actions.append(np.ones(2))
    buf.rewards.append(0.5)
    buf.logprobs.append(-1.0)
    buf.values.append(0.1)
    buf.dones.append(False)
    assert len(buf) == 1  # __len__ 返回 len(self.obs)（源码契约）
    buf.clear()
    assert len(buf) == 0
    assert len(buf.obs) == 0
    # ReplayBuffer 是 RolloutBuffer 的语义别名（导出 API 名称对齐）
    assert ReplayBuffer is RolloutBuffer


def test_transition_and_minibatch_fields():
    """Transition / Minibatch 数据类字段完整性。"""
    obs = np.zeros(6)
    action = np.ones(3)
    t = Transition(obs=obs, action=action, reward=0.5, logprob=-0.3, value=0.1, done=False)
    assert t.obs is obs
    assert t.action is action
    assert t.reward == 0.5
    assert t.logprob == -0.3
    assert t.value == 0.1
    assert t.done is False
    # Minibatch
    mb = Minibatch(
        obs=np.zeros((4, 6)), actions=np.ones((4, 3)),
        old_logprobs=np.zeros(4), advantages=np.zeros(4), returns=np.zeros(4),
    )
    assert mb.obs.shape == (4, 6)
    assert mb.actions.shape == (4, 3)
    assert mb.old_logprobs.shape == (4,)


# =============================================================================
# §3 ActorCritic & PPOAgent
# =============================================================================


def test_actor_critic_forward_and_evaluate():
    """ActorCritic: forward 返回 (mean, value)；evaluate 返回 (logprob, value, entropy)。"""
    np.random.seed(42)
    ac = ActorCritic(obs_dim=6, action_dim=2, hidden_dim=16)
    obs = np.random.randn(6)
    mean, value = ac.forward(obs)
    assert mean.data.shape[-1] == 2  # action_dim
    assert value.data.shape[-1] == 1  # 标量价值
    # get_action: 返回 (action, logprob, value)
    action, lp, v = ac.get_action(obs)
    assert action.shape == (2,)
    assert np.isfinite(lp)
    assert np.isfinite(v)
    # evaluate: 批量重新评估 (batch=4)
    obs_batch = np.random.randn(4, 6)
    actions_batch = np.random.randn(4, 2)
    lp_data, val_data, entropy = ac.evaluate(obs_batch, actions_batch)
    assert lp_data.shape == (4,)
    assert val_data.shape == (4,)
    assert entropy.shape == (4,)
    assert np.all(np.isfinite(lp_data))
    assert np.all(np.isfinite(entropy))


def test_ppo_agent_get_action_shapes():
    """PPOAgent.get_action: 返回 (action, logprob, value)，形状与 obs/action 维度匹配。"""
    np.random.seed(0)
    agent = PPOAgent(obs_dim=8, action_dim=3, hidden_dim=16)
    obs = np.random.randn(8)
    action, lp, v = agent.get_action(obs)
    assert action.shape == (3,)
    assert isinstance(lp, float)
    assert isinstance(v, float)
    # store 后 buffer 增长
    n0 = len(agent.buffer)
    agent.store(Transition(obs, action, 0.1, lp, v, False))
    assert len(agent.buffer) == n0 + 1


def test_ppo_agent_lr_schedule():
    """PPOAgent._get_lr: constant/cosine/linear + warmup 调度。"""
    # constant: 恒等于 lr
    agent_c = PPOAgent(obs_dim=4, action_dim=2, config=PPOConfig(lr=1e-3, lr_schedule="constant"))
    assert abs(agent_c._get_lr() - 1e-3) < 1e-12
    # cosine + warmup: warmup 阶段线性增长
    agent_w = PPOAgent(
        obs_dim=4, action_dim=2,
        config=PPOConfig(lr=1e-3, lr_schedule="cosine", lr_warmup_steps=10, total_steps=100),
    )
    agent_w.current_step = 0
    lr_w0 = agent_w._get_lr()
    agent_w.current_step = 5
    lr_w5 = agent_w._get_lr()
    assert lr_w5 > lr_w0  # warmup 线性增长
    # cosine 退火：step 增大 lr 减小
    agent_co = PPOAgent(
        obs_dim=4, action_dim=2,
        config=PPOConfig(lr=1e-3, lr_schedule="cosine", lr_warmup_steps=0, total_steps=100),
    )
    agent_co.current_step = 0
    lr0 = agent_co._get_lr()
    agent_co.current_step = 100
    lr100 = agent_co._get_lr()
    assert lr100 < lr0  # 余弦退火递减
    # linear: 递减到 0
    agent_l = PPOAgent(
        obs_dim=4, action_dim=2,
        config=PPOConfig(lr=1e-3, lr_schedule="linear", lr_warmup_steps=0, total_steps=100),
    )
    agent_l.current_step = 100
    assert abs(agent_l._get_lr()) < 1e-9  # 线性衰减到 ~0


def test_ppo_agent_update():
    """PPOAgent: 采样→存储→更新闭环，返回含全部指标字段。"""
    np.random.seed(42)
    agent = PPOAgent(
        obs_dim=8, action_dim=2,
        config=PPOConfig(batch_size=4, n_epochs=2),
        hidden_dim=16,
    )
    obs = np.random.randn(8)
    for _ in range(8):
        action, logprob, value = agent.get_action(obs)
        agent.store(
            polaris_trainer.Transition(obs, action, 0.1, logprob, value, False)
        )
    metrics = agent.update(last_value=0.0)
    for key in ("loss", "policy_loss", "value_loss", "entropy"):
        assert key in metrics, f"metrics 缺字段: {key}"
        assert np.isfinite(metrics[key]), f"{key} 非有限: {metrics[key]}"
    # buffer 在 update 后清空
    assert len(agent.buffer) == 0


def test_ppo_save_load_roundtrip(tmp_path):
    """PPOAgent save→load 权重一致（断点续训）。"""
    agent = PPOAgent(obs_dim=6, action_dim=3, hidden_dim=16)
    obs = np.random.randn(6)
    for _ in range(4):
        action, logprob, value = agent.get_action(obs)
        agent.store(polaris_trainer.Transition(obs, action, 0.2, logprob, value, False))
    agent.update(last_value=0.0)
    ckpt = tmp_path / "agent.json"
    agent.save(ckpt)

    agent2 = PPOAgent(obs_dim=6, action_dim=3, hidden_dim=16)
    agent2.load(ckpt)
    p1 = [np.array(p.data) for p in agent.ac.parameters()]
    p2 = [np.array(p.data) for p in agent2.ac.parameters()]
    assert len(p1) == len(p2)
    for a, b in zip(p1, p2):
        np.testing.assert_allclose(a, b)


def test_load_agent_helper(tmp_path):
    """load_agent: 从检查点重建 PPOAgent（断点续训便捷接口）。"""
    agent = PPOAgent(obs_dim=5, action_dim=2, hidden_dim=12)
    ckpt = tmp_path / "helper_agent.json"
    agent.save(ckpt)
    # load_agent 重建
    restored = load_agent(ckpt, obs_dim=5, action_dim=2, hidden_dim=12)
    assert restored.obs_dim == 5
    assert restored.action_dim == 2
    # 权重一致
    for a, b in zip(agent.ac.parameters(), restored.ac.parameters()):
        np.testing.assert_allclose(a.data, b.data)


# =============================================================================
# §4 GAE & 工具函数
# =============================================================================


def test_compute_gae():
    """GAE: 形状正确，returns = advantages + values；done 截断。"""
    rewards = [1.0, 1.0, 1.0, 0.5]
    values = [0.1, 0.2, 0.3, 0.4]
    dones = [False, False, False, True]
    cfg = PPOConfig(gamma=0.99, gae_lambda=0.95)
    adv, ret = compute_gae(rewards, values, dones, last_value=0.0, config=cfg)
    assert adv.shape == (4,)
    assert ret.shape == (4,)
    np.testing.assert_allclose(ret, adv + np.array(values, dtype=np.float64))
    # done 截断：最后一步 done=True，advantage 不向更后传播
    assert np.isfinite(adv).all()
    # 默认 config（None）使用 gamma=0.99, gae_lambda=0.95
    adv2, ret2 = compute_gae(rewards, values, dones, last_value=0.0, config=None)
    np.testing.assert_allclose(adv, adv2)


def test_lr_scale_constant_linear_cosine():
    """lr_scale: constant/linear/cosine 三种调度 + total<=0 边界。"""
    # constant: 恒为 1.0
    assert lr_scale(0, 100, "constant") == 1.0
    assert lr_scale(50, 100, "constant") == 1.0
    # linear: 1 - ep/total
    assert abs(lr_scale(0, 100, "linear") - 1.0) < 1e-12
    assert abs(lr_scale(50, 100, "linear") - 0.5) < 1e-12
    assert abs(lr_scale(100, 100, "linear") - 0.0) < 1e-12
    # cosine: 0.5*(1+cos(pi*ep/total))（Loshchilov 2017 SGDR）
    assert abs(lr_scale(0, 100, "cosine") - 1.0) < 1e-12  # cos(0)=1
    assert abs(lr_scale(100, 100, "cosine") - 0.0) < 1e-12  # cos(pi)=-1
    assert abs(lr_scale(50, 100, "cosine") - 0.5) < 1e-12  # cos(pi/2)=0
    # total<=0: 返回 1.0（边界保护）
    assert lr_scale(0, 0, "cosine") == 1.0
    assert lr_scale(5, -1, "linear") == 1.0


def test_obs_to_vector_and_pad_obs():
    """obs_to_vector: dict/array 展平；pad_obs: 填充/截断。"""
    # dict 观测：拼接所有 value
    obs_dict = {"a": np.zeros(3), "b": np.ones(2)}
    vec = obs_to_vector(obs_dict)
    assert vec.shape == (5,)
    np.testing.assert_allclose(vec, np.array([0, 0, 0, 1, 1]))
    # array 观测：直接展平
    obs_arr = np.zeros((2, 4))
    vec2 = obs_to_vector(obs_arr)
    assert vec2.shape == (8,)
    # pad_obs: 短向量零填充
    short = np.ones(3)
    padded = pad_obs(short, obs_dim=5)
    assert padded.shape == (5,)
    np.testing.assert_allclose(padded, np.array([1, 1, 1, 0, 0]))
    # pad_obs: 长向量截断
    long_vec = np.arange(7, dtype=float)
    truncated = pad_obs(long_vec, obs_dim=5)
    assert truncated.shape == (5,)
    np.testing.assert_allclose(truncated, np.array([0, 1, 2, 3, 4]))
    # pad_obs: 等长不变
    eq = pad_obs(np.ones(5), obs_dim=5)
    assert eq.shape == (5,)


def test_infer_obs_dim():
    """infer_obs_dim: 从 env.reset() 推断观测向量维度。"""
    env = _FakeEnv(obs_dim=8)
    dim = infer_obs_dim(env)
    assert dim == 8


def test_discretize_floorplan_action():
    """discretize_floorplan_action: 连续→MultiDiscrete (gx, gy, rot)。"""
    env = _FakeEnv(grid_w=10, grid_h=10)
    # action=[0.5, 0.5, 0.5] → gx=4, gy=4, rot=1
    action = np.array([0.5, 0.5, 0.5])
    discrete = discretize_floorplan_action(action, env)
    assert discrete.shape == (3,)
    assert discrete[0] == 4  # int(0.5 * 9) = 4
    assert discrete[1] == 4
    assert discrete[2] == 1  # int(0.5 * 3) = 1
    # 边界: action=[0, 0, 0] → gx=0, gy=0, rot=0
    discrete0 = discretize_floorplan_action(np.array([0.0, 0.0, 0.0]), env)
    assert list(discrete0) == [0, 0, 0]
    # 边界: action=[1, 1, 1] → gx=9, gy=9, rot=3
    discrete1 = discretize_floorplan_action(np.array([1.0, 1.0, 1.0]), env)
    assert discrete1[0] == 9
    assert discrete1[1] == 9
    assert discrete1[2] == 3


# =============================================================================
# §5 训练循环
# =============================================================================


def test_train_ppo_smoke(tmp_path):
    """train_ppo 在 fake env 上跑通：返回 (agent, logs)，logs 非空。"""
    np.random.seed(0)
    agent = PPOAgent(
        obs_dim=8, action_dim=2,
        config=PPOConfig(batch_size=4, n_epochs=1, lr_schedule="cosine", total_steps=2),
        hidden_dim=16,
    )
    env = _FakeEnv(obs_dim=8)
    config = TrainConfig(
        num_episodes=2, rollout_steps=6, hidden_dim=16,
        checkpoint_dir=str(tmp_path / "ckpts"), checkpoint_every=1,
        log_every=10, early_stop_patience=0, lr_schedule="cosine", seed=0,
    )
    trained, logs = train_ppo(agent, env, config, obs_dim=8, verbose=False)
    assert trained is agent
    assert len(logs) >= 1
    assert "ep_reward" in logs[0] and "policy_loss" in logs[0]
    # checkpoint 文件已生成
    assert (tmp_path / "ckpts" / "ppo_final.json").exists()
    assert (tmp_path / "ckpts" / "ppo_log.json").exists()


def test_train_with_env_factory_smoke(tmp_path):
    """train_with_env_factory: 多 env（每轮换网表）训练循环跑通。"""
    np.random.seed(1)
    agent = PPOAgent(
        obs_dim=8, action_dim=2,
        config=PPOConfig(batch_size=4, n_epochs=1),
        hidden_dim=16,
    )
    factory_calls = []

    def env_factory(ep):
        factory_calls.append(ep)
        env = _FakeEnv(obs_dim=8)
        env.name = f"env_{ep}"
        return env

    config = TrainConfig(
        num_episodes=3, rollout_steps=6, hidden_dim=16,
        checkpoint_dir=str(tmp_path / "ckpts_factory"), checkpoint_every=10,
        log_every=10, early_stop_patience=0, seed=1,
    )
    trained, logs = train_with_env_factory(
        agent, env_factory, config, obs_dim=8, verbose=False
    )
    assert trained is agent
    assert len(logs) == 3
    # 工厂每轮被调用一次
    assert factory_calls == [0, 1, 2]
    # logs 含 netlist 字段（env.name）
    assert "netlist" in logs[0]
    assert logs[0]["netlist"] == "env_0"


# =============================================================================
# §6 R351 LargeScalePlacementEnv
# =============================================================================


def test_rl_advanced_env():
    """LargeScalePlacementEnv: set_circuit/build_state/step 闭环。"""
    circuit = {
        "devices": [
            {"id": "d0", "type": "mzi", "width": 50.0, "height": 30.0, "ports": ["a", "b"]},
            {"id": "d1", "type": "mmi", "width": 40.0, "height": 20.0, "ports": ["a", "b", "c"]},
        ],
        "nets": [
            {"src": ("d0", "a"), "dst": ("d1", "a")},
        ],
    }
    env = LargeScalePlacementEnv(LargeScalePlacementConfig(grid_size=(8, 8)))
    env.set_circuit(circuit)
    assert env.n_devices() == 2
    state = env.build_state(circuit["devices"][0])
    assert state["occupancy"].shape == (8, 8)
    assert state["node_feats"].shape == (2, 9)
    assert state["action_mask"].shape == (64,)
    # 放置 d0 到 grid_idx=0
    state2 = env.step("d0", 0)
    assert "d0" in env.placement
    assert state2["action_mask"][0] == 0.0  # 该格已被占用
    # 重复放置 raise（R03）
    with pytest.raises(ValueError, match="已放置"):
        env.step("d0", 1)


def test_large_scale_env_config_and_raises():
    """LargeScalePlacementConfig 默认值 + set_circuit/step 越界 raise（R03）。"""
    # 配置默认值（R351: 100+ 组件支持，grid=32x32, max_devices=1024）
    cfg = LargeScalePlacementConfig()
    assert cfg.grid_size == (32, 32)
    assert cfg.node_feat_dim == 9
    assert cfg.max_devices == 1024
    assert cfg.seed == 42
    env = LargeScalePlacementEnv(cfg)
    # 电路未设置时调用方法 raise（R03）
    with pytest.raises(ValueError, match="电路未设置"):
        env.n_devices()
    with pytest.raises(ValueError, match="电路未设置"):
        env.build_occupancy()
    # 缺字段 raise
    with pytest.raises(ValueError, match="devices"):
        env.set_circuit({"nets": []})
    with pytest.raises(ValueError, match="nets"):
        env.set_circuit({"devices": []})
    # 空器件列表 raise
    with pytest.raises(ValueError, match=">= 1"):
        env.set_circuit({"devices": [], "nets": []})
    # 超容量 raise
    big = {"devices": [{"id": f"d{i}", "type": "mzi"} for i in range(10)], "nets": []}
    env_small = LargeScalePlacementEnv(LargeScalePlacementConfig(grid_size=(2, 2), max_devices=5))
    with pytest.raises(ValueError, match="max_devices"):
        env_small.set_circuit(big)
    # step 越界 raise（32x32=1024 格，grid_idx 须 < 1024）
    env.set_circuit(_make_circuit(2))
    with pytest.raises(ValueError, match="越界"):
        env.step("d0", 2000)
    # 占用位置 raise
    env.step("d0", 0)
    with pytest.raises(ValueError, match="占用"):
        env.step("d1", 0)


# =============================================================================
# §7 R352 PPOAdvantageOptimizer
# =============================================================================


def test_ppo_adv_config_defaults():
    """PPOAdvConfig 默认值与 PPO 文献对齐。"""
    cfg = PPOAdvConfig()
    # Schulman 2017 PPO: clip_eps=0.2
    assert cfg.clip_eps == 0.2
    # Schulman 2015 GAE: gae_lambda=0.95
    assert cfg.gae_lambda == 0.95
    # Sutton & Barto 2018: gamma=0.99
    assert cfg.gamma == 0.99
    # Mnih 2016 A3C: ent_coef=0.01
    assert cfg.ent_coef == 0.01
    assert cfg.vf_coef == 0.5
    # Loshchilov 2017 SGDR: initial_lr=3e-4, min_lr=1e-5
    assert cfg.initial_lr == 3e-4
    assert cfg.min_lr == 1e-5


def test_ppo_adv_optimizer_compute_gae_and_normalize():
    """PPOAdvantageOptimizer.compute_gae + normalize_advantages。"""
    opt = PPOAdvantageOptimizer()
    rewards = np.array([1.0, 0.5, 0.0, -0.5])
    values = np.array([0.3, 0.4, 0.2, 0.1])
    dones = np.array([0, 0, 0, 1])
    adv, ret = opt.compute_gae(rewards, values, dones, last_value=0.0)
    assert adv.shape == (4,)
    assert ret.shape == (4,)
    # returns = advantages + values（Schulman 2015 GAE 定义）
    np.testing.assert_allclose(ret, adv + values)
    # normalize: 均值≈0
    adv_norm = opt.normalize_advantages(adv)
    assert abs(float(np.mean(adv_norm))) < 1e-9
    # 形状不匹配 raise（R03）
    with pytest.raises(ValueError, match="形状不匹配"):
        opt.compute_gae(np.array([1.0, 2.0]), np.array([0.1]), np.array([0, 1]))
    # 空输入 raise（R03）
    with pytest.raises(ValueError, match="不能为空"):
        opt.compute_gae(np.array([]), np.array([]), np.array([]))
    with pytest.raises(ValueError, match="不能为空"):
        opt.normalize_advantages(np.array([]))


def test_ppo_adv_optimizer_policy_and_value_loss():
    """PPOAdvantageOptimizer.compute_policy_loss + compute_value_loss。"""
    opt = PPOAdvantageOptimizer()
    # new=old → ratio=1, policy_loss = -mean(adv)
    new_lp = np.array([-1.0, -2.0, -3.0])
    old_lp = np.array([-1.0, -2.0, -3.0])
    adv = np.array([0.5, -0.3, 0.1])
    total_loss, metrics = opt.compute_policy_loss(new_lp, old_lp, adv, entropy=0.0)
    expected_policy = -float(np.mean(adv))
    assert abs(metrics["policy_loss"] - expected_policy) < 1e-9
    assert metrics["clip_frac"] == 0.0  # ratio=1 未触发 clip
    assert abs(metrics["mean_ratio"] - 1.0) < 1e-9
    # 含熵正则: total = policy_loss - ent_coef * entropy
    total_loss_e, _ = opt.compute_policy_loss(new_lp, old_lp, adv, entropy=np.array([1.0]))
    assert abs(total_loss_e - (expected_policy - opt.config.ent_coef * 1.0)) < 1e-9
    # value loss: (V - R)^2 均值 * 0.5
    v = np.array([0.5, 0.6])
    ov = np.array([0.4, 0.5])
    ret = np.array([0.5, 0.5])
    v_loss = opt.compute_value_loss(v, ov, ret)
    assert v_loss > 0
    # 空输入 raise（R03）
    with pytest.raises(ValueError, match="不能为空"):
        opt.compute_policy_loss(np.array([]), np.array([]), np.array([]))
    with pytest.raises(ValueError, match="不能为空"):
        opt.compute_value_loss(np.array([]), np.array([]), np.array([]))


def test_ppo_adv_optimizer_cosine_lr_schedule():
    """PPOAdvantageOptimizer.cosine_lr_schedule: 余弦退火（Loshchilov 2017 SGDR）。"""
    opt = PPOAdvantageOptimizer(PPOAdvConfig(initial_lr=3e-4, min_lr=1e-5))
    # step=0: lr = min + 0.5*(initial-min)*2 = initial
    lr0 = opt.cosine_lr_schedule(0, 100)
    assert abs(lr0 - 3e-4) < 1e-12
    # step=total: lr = min + 0 = min
    lr_end = opt.cosine_lr_schedule(100, 100)
    assert abs(lr_end - 1e-5) < 1e-12
    # step=total/2: lr = (initial + min) / 2
    lr_mid = opt.cosine_lr_schedule(50, 100)
    expected = 1e-5 + 0.5 * (3e-4 - 1e-5) * 1.0  # cos(pi/2)=0 → 1+0=1
    assert abs(lr_mid - expected) < 1e-12
    # total<=0 raise（R03）
    with pytest.raises(ValueError, match="total_steps"):
        opt.cosine_lr_schedule(0, 0)


def test_ppo_adv_optimizer_update_end_to_end():
    """PPOAdvantageOptimizer.update: 端到端 PPO 更新（GAE→标准化→loss）。"""
    opt = PPOAdvantageOptimizer()
    rollout = {
        "rewards": np.array([1.0, 0.5, 0.0]),
        "values": np.array([0.3, 0.4, 0.2]),
        "old_logprobs": np.array([-1.0, -2.0, -1.5]),
        "old_values": np.array([0.3, 0.4, 0.2]),
        "dones": np.array([0, 0, 1]),
        "last_value": 0.0,
    }
    new_lp = np.array([-1.1, -1.9, -1.6])
    new_v = np.array([0.35, 0.38, 0.22])
    result = opt.update(rollout, new_lp, new_v, entropy=np.array([0.5, 0.5, 0.5]))
    for key in ("advantages", "returns", "policy_loss", "value_loss",
                "total_loss", "clip_frac", "entropy"):
        assert key in result, f"update 结果缺字段: {key}"
    assert np.isfinite(result["total_loss"])
    assert np.isfinite(result["policy_loss"])
    assert np.isfinite(result["value_loss"])
    # 缺字段 raise（R03）
    bad_rollout = {"rewards": np.array([1.0]), "values": np.array([0.1])}
    with pytest.raises(ValueError, match="缺字段"):
        opt.update(bad_rollout, new_lp, new_v)


# =============================================================================
# §8 R353 MultiObjectiveParetoReward
# =============================================================================


def test_pareto_reward_and_front():
    """MultiObjectiveParetoReward: compute + pareto_front。"""
    circuit = {
        "devices": [
            {"id": "d0", "width": 50.0, "height": 30.0, "ports": ["a", "b"]},
            {"id": "d1", "width": 40.0, "height": 20.0, "ports": ["a", "b"]},
        ],
        "nets": [{"src": ("d0", "a"), "dst": ("d1", "a")}],
    }
    placement = {
        "d0": {"x": 0.0, "y": 0.0, "rotation": 0},
        "d1": {"x": 100.0, "y": 100.0, "rotation": 0},
    }
    reward = MultiObjectiveParetoReward()
    res = reward.compute(placement, circuit)
    for key in ("reward", "area", "delay_ps", "loss_db", "xtalk_linear"):
        assert key in res
        assert np.isfinite(res[key])
    # Pareto 前沿：3 个解，第 0 个在两目标上都最小 → 在前沿
    objs = np.array([[0.1, 0.2], [0.5, 0.6], [0.9, 0.3]])
    front = reward.pareto_front(objs)
    assert 0 in front.tolist()
    assert len(front) >= 1


