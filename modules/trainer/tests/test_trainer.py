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


def test_pareto_reward_individual_objectives_and_maximize():
    """MultiObjectiveParetoReward: 单目标计算 + config 权重 + pareto_front(maximize)。"""
    circuit = _make_circuit(2)
    placement = {
        "d0": {"x": 0.0, "y": 0.0, "rotation": 0},
        "d1": {"x": 200.0, "y": 200.0, "rotation": 0},
    }
    reward = MultiObjectiveParetoReward()
    # 单目标计算（Bogaerts 2013 损耗 / Reed 2010 时延）
    area = reward.compute_area(placement, circuit)
    assert area > 0  # 两器件面积之和
    delay = reward.compute_delay(placement, circuit)
    assert delay > 0  # n_g * L / c
    loss = reward.compute_loss(placement, circuit)
    assert loss >= 0  # 传播损耗 + 交叉损耗
    xtalk = reward.compute_xtalk(placement, circuit)
    assert xtalk >= 0
    # config 权重影响 reward
    cfg = MultiObjectiveRewardConfig(w_area=10.0, w_delay=0.0, w_loss=0.0, w_xtalk=0.0)
    reward_w = MultiObjectiveParetoReward(cfg)
    res = reward_w.compute(placement, circuit)
    # reward = -(10 * area_norm + 0 + 0 + 0)
    expected = -(10.0 * area / (3200.0 ** 2))
    assert abs(res["reward"] - expected) < 1e-9
    # pareto_front maximize: 第 0 个在两目标上都最大 → 在前沿
    objs = np.array([[0.9, 0.8], [0.1, 0.2], [0.5, 0.3]])
    front = reward.pareto_front(objs, maximize=True)
    assert 0 in front.tolist()
    # 非法输入 raise（R03）
    with pytest.raises(ValueError, match="2D"):
        reward.pareto_front(np.array([1.0, 2.0]))
    with pytest.raises(ValueError, match="不能为空"):
        reward.pareto_front(np.array([]).reshape(0, 2))


# =============================================================================
# §9 R354 PretrainedPolicyLibrary
# =============================================================================


def test_pretrained_policy_generate_all_strategies(tmp_path):
    """PretrainedPolicyLibrary: heuristic/random/curriculum 三种策略生成布局。"""
    cfg = PretrainedPolicyConfig(seed=42, grid_size=(8, 8), checkpoint_dir=str(tmp_path))
    lib = PretrainedPolicyLibrary(cfg)
    assert lib.list_policies() == ["heuristic", "random", "curriculum"]
    circuit = _make_circuit(3)
    for policy in ALL_POLICIES:
        placement = lib.generate_placement(circuit, policy)
        assert len(placement) == 3
        for dev_id in ("d0", "d1", "d2"):
            assert dev_id in placement
            assert "x" in placement[dev_id]
            assert "y" in placement[dev_id]
            assert "rotation" in placement[dev_id]
    # heuristic: 高连接度器件优先放中心（d1 连接度最高）
    placement_h = lib.generate_placement(circuit, POLICY_HEURISTIC)
    # d1 是 d0-d1, d1-d2 两条 net 的中心器件，连接度=2
    cache = lib.get_policy_cache(POLICY_HEURISTIC)
    assert cache["n_devices"] == 3
    # 未知策略 raise（R03）
    with pytest.raises(ValueError, match="未知策略"):
        lib.generate_placement(circuit, "bogus")
    # 超容量 raise（R03）
    big_circuit = {"devices": [{"id": f"d{i}", "type": "mzi"} for i in range(100)], "nets": []}
    lib_small = PretrainedPolicyLibrary(PretrainedPolicyConfig(grid_size=(2, 2)))
    with pytest.raises(ValueError, match="网格容量"):
        lib_small.generate_placement(big_circuit, POLICY_RANDOM)


def test_pretrained_policy_save_load_and_cache_raise(tmp_path):
    """PretrainedPolicyLibrary: save_policy/load_policy 往返 + get_policy_cache raise。"""
    cfg = PretrainedPolicyConfig(seed=0, grid_size=(8, 8), checkpoint_dir=str(tmp_path))
    lib = PretrainedPolicyLibrary(cfg)
    # save → load 往返
    weights = {"layer1": [[1, 2], [3, 4]], "bias": [0.1, 0.2]}
    path = lib.save_policy(POLICY_HEURISTIC, weights)
    assert path.exists()
    loaded = lib.load_policy(POLICY_HEURISTIC)
    assert loaded["policy_name"] == POLICY_HEURISTIC
    assert loaded["weights"] == weights
    assert loaded["metadata"]["version"] == "R354-v1.0"
    # 未生成的策略 cache raise（R03）
    with pytest.raises(ValueError, match="未生成"):
        lib.get_policy_cache(POLICY_RANDOM)
    # 加载不存在的 checkpoint raise（R03）
    with pytest.raises(ValueError, match="不存在"):
        lib.load_policy(POLICY_CURRICULUM)
    # 未知策略 save/load raise（R03）
    with pytest.raises(ValueError, match="未知策略"):
        lib.save_policy("bogus", {})


# =============================================================================
# §10 R355 HybridPlacementAgent
# =============================================================================


def test_hybrid_placement_set_fixed_and_auto_place(tmp_path):
    """HybridPlacementAgent: set_fixed_devices → auto_place_remaining → stats。"""
    cfg = HybridPlacementConfig(grid_size=(8, 8), seed=42)
    agent = HybridPlacementAgent(cfg)
    circuit = _make_circuit(3)
    # fix-then-optimize: 先固定 d0
    agent.set_fixed_devices({"d0": {"x": 0.0, "y": 0.0, "rotation": 0}})
    assert "d0" in agent.placement
    assert agent.fixed_devices["d0"]["x"] == 0.0
    # 自动布局剩余器件
    placement = agent.auto_place_remaining(circuit)
    assert len(placement) == 3
    for dev_id in ("d0", "d1", "d2"):
        assert dev_id in placement
    # d0 位置未被覆盖
    assert placement["d0"]["x"] == 0.0
    # stats
    stats = agent.stats()
    assert stats["n_fixed"] == 1
    assert stats["n_placed"] == 3
    assert stats["grid_size"] == (8, 8)
    # 越界 raise（R03）
    with pytest.raises(ValueError, match="越界"):
        agent.set_fixed_devices({"d0": {"x": 99999.0, "y": 0.0, "rotation": 0}})
    # 位置冲突 raise（R03）
    with pytest.raises(ValueError, match="冲突"):
        agent.set_fixed_devices({
            "d0": {"x": 0.0, "y": 0.0, "rotation": 0},
            "d1": {"x": 50.0, "y": 0.0, "rotation": 0},  # 同一 cell (0,0)
        })
    # place() 端到端
    agent2 = HybridPlacementAgent(cfg)
    placement2 = agent2.place(circuit, fixed_devices={"d0": {"x": 100.0, "y": 100.0, "rotation": 0}})
    assert len(placement2) == 3
    # 缺 devices raise（R03）
    with pytest.raises(ValueError, match="devices"):
        agent.auto_place_remaining({"nets": []})


# =============================================================================
# §11 CheckpointManager
# =============================================================================


def test_checkpoint_manager_roundtrip(tmp_path):
    """CheckpointManager: save_pretrained/load_pretrained 元信息往返。"""
    agent = PPOAgent(obs_dim=4, action_dim=2, hidden_dim=8)
    mgr = CheckpointManager(checkpoint_dir=tmp_path)
    ckpt = tmp_path / "pretrained.json"
    mgr.save_pretrained(agent, ckpt, metadata={"platform": "SOI"})
    raw = json.loads(ckpt.read_text(encoding="utf-8"))
    assert "pretrain_metadata" in raw
    assert raw["pretrain_metadata"]["platform"] == "SOI"
    assert raw["pretrain_metadata"]["version"] == "R34-v1.0"

    agent2 = PPOAgent(obs_dim=4, action_dim=2, hidden_dim=8)
    meta = mgr.load_pretrained(agent2, ckpt)
    assert meta["platform"] == "SOI"
    # 权重一致
    for a, b in zip(agent.ac.parameters(), agent2.ac.parameters()):
        np.testing.assert_allclose(a.data, b.data)


def test_checkpoint_manager_list_and_invalid_agent_raise(tmp_path):
    """CheckpointManager: list_checkpoints + 无 save/load 方法的 agent raise（R03）。"""
    mgr = CheckpointManager(checkpoint_dir=tmp_path)
    # 保存多个 checkpoint
    for i in range(3):
        agent = PPOAgent(obs_dim=4, action_dim=2, hidden_dim=8)
        mgr.save_pretrained(agent, tmp_path / f"ckpt_{i}.json", metadata={"idx": i})
    ckpts = mgr.list_checkpoints()
    assert len(ckpts) == 3
    # 全部是 .json 文件
    assert all(p.suffix == ".json" for p in ckpts)
    # 无 save 方法的 agent raise（R03）
    class _NoSave:
        pass
    with pytest.raises(ValueError, match="save"):
        mgr.save_pretrained(_NoSave(), tmp_path / "bad.json")
    # 无 load 方法的 agent raise（R03）
    with pytest.raises(ValueError, match="load"):
        mgr.load_pretrained(_NoSave(), tmp_path / "ckpt_0.json")
    # 加载不存在的 checkpoint raise（R03）
    agent = PPOAgent(obs_dim=4, action_dim=2, hidden_dim=8)
    with pytest.raises(FileNotFoundError, match="不存在"):
        mgr.load_pretrained(agent, tmp_path / "nonexistent.json")


# =============================================================================
# §12 R03/R04 综合
# =============================================================================


def test_no_fallback_r03_r04():
    """R03 禁止 fall-back（非法策略 raise）+ R04 GPU 声明。"""
    assert GPU_DISABLED_R04 is True
    lib = PretrainedPolicyLibrary()
    with pytest.raises(ValueError, match="未知策略"):
        lib.generate_placement({"devices": [], "nets": []}, "bogus_policy")
    # PPOAdvantageOptimizer 空输入 raise（R03）
    opt = PPOAdvantageOptimizer()
    with pytest.raises(ValueError, match="不能为空"):
        opt.compute_gae(np.array([]), np.array([]), np.array([]))
    assert ALL_PLATFORMS == ("SOI", "SiN", "InP", "LNOI")
    assert ALL_POLICIES == ("heuristic", "random", "curriculum")


# =============================================================================
# §13 R35 CPU 多进程并行 rollout（ParallelRolloutCollector）
#
# 学术依据: Schulman 2017 PPO 多 env 采样 https://arxiv.org/abs/1707.06347 /
# SB3 SubprocVecEnv https://stable-baselines3.readthedocs.io/en/master/guide/examples.html /
# Python concurrent.futures https://docs.python.org/3/library/concurrent.futures.html /
# Mayor 2025 ICML 并行采样 https://arxiv.org/abs/2506.03404 /
# Circuit Training 多 env https://github.com/google-research/circuit_training
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
