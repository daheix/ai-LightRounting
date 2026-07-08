"""扩展测试（从 test_trainer.py 拆分，遵守 R11 质量门禁文件≤800行）.

来源（R02 学术诚信）: 同原文件 test_trainer.py。
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


def _make_circuit(n: int = 2) -> dict:
    """构造 n 器件测试电路（含 devices 与 nets）。"""
    devices = [
        {"id": f"d{i}", "type": "mzi" if i % 2 == 0 else "mmi",
         "width_um": 50.0, "height_um": 30.0, "ports": ["a", "b"]}
        for i in range(n)
    ]
    nets = [{"src": (f"d{i}", "a"), "dst": (f"d{i + 1}", "a")} for i in range(n - 1)]
    return {"devices": devices, "nets": nets,
            "canvas_w": 3200.0, "canvas_h": 3200.0}


# =============================================================================
# §1 导入与导出
# =============================================================================


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
