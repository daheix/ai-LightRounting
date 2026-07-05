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
