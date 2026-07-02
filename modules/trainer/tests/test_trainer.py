"""polaris-trainer 子模块 smoke 测试。

测试覆盖（≥3 smoke test，R03 禁止 fall-back，R04 不参与 GPU）:
- test_import_and_exports: 导入与核心 API 导出完整性
- test_compute_gae: GAE 优势/回报计算正确性
- test_ppo_agent_update: PPOAgent 采样→存储→更新闭环 + 指标字段
- test_ppo_save_load_roundtrip: PPOAgent 检查点保存/加载权重一致
- test_train_ppo_smoke: train_ppo 在 fake Gymnasium env 上跑通
- test_rl_advanced_env: LargeScalePlacementEnv set_circuit/build_state/step
- test_pareto_reward_and_front: 多目标奖励 + Pareto 前沿
- test_no_fallback_r03_r04: 非法输入 raise + GPU_DISABLED_R04 声明

来源（R02 学术诚信）:
- pytest 文档: https://docs.pytest.org/
- Schulman 2017 PPO https://arxiv.org/abs/1707.06347
- Schulman 2015 GAE https://arxiv.org/abs/1506.02438
- Mirhoseini 2021 Nature AlphaChip
  https://www.nature.com/articles/s41586-021-03544-w
- Deb 2002 NSGA-II https://ieeexplore.ieee.org/document/996017
"""

from __future__ import annotations

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
    ActorCritic,
    CheckpointManager,
    GPU_DISABLED_R04,
    LargeScalePlacementConfig,
    LargeScalePlacementEnv,
    MultiObjectiveParetoReward,
    PPOAdvantageOptimizer,
    PPOAgent,
    PPOConfig,
    PretrainedPolicyLibrary,
    RolloutBuffer,
    ReplayBuffer,
    TrainConfig,
    compute_gae,
    train_ppo,
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


# =============================================================================
# Smoke tests
# =============================================================================


def test_import_and_exports():
    """导入 polaris_trainer 并验证核心 API 导出完整。"""
    assert polaris_trainer.__version__ == "5.0.0"
    for name in (
        "PPOConfig", "ActorCritic", "RolloutBuffer", "ReplayBuffer", "Transition",
        "compute_gae", "PPOAgent", "TrainConfig", "train_ppo",
        "train_with_env_factory", "load_agent", "CheckpointManager",
        "LargeScalePlacementEnv", "PPOAdvantageOptimizer",
        "MultiObjectiveParetoReward", "PretrainedPolicyLibrary",
        "HybridPlacementAgent", "GPU_DISABLED_R04",
    ):
        assert hasattr(polaris_trainer, name), f"polaris_trainer 缺少导出: {name}"
    # ReplayBuffer 是 RolloutBuffer 的语义别名
    assert ReplayBuffer is RolloutBuffer


def test_compute_gae():
    """GAE: 形状正确，returns = advantages + values。"""
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


def test_checkpoint_manager_roundtrip(tmp_path):
    """CheckpointManager: save_pretrained/load_pretrained 元信息往返。"""
    agent = PPOAgent(obs_dim=4, action_dim=2, hidden_dim=8)
    mgr = CheckpointManager(checkpoint_dir=tmp_path)
    ckpt = tmp_path / "pretrained.json"
    mgr.save_pretrained(agent, ckpt, metadata={"platform": "SOI"})
    raw = __import__("json").loads(ckpt.read_text(encoding="utf-8"))
    assert "pretrain_metadata" in raw
    assert raw["pretrain_metadata"]["platform"] == "SOI"
    assert raw["pretrain_metadata"]["version"] == "R34-v1.0"

    agent2 = PPOAgent(obs_dim=4, action_dim=2, hidden_dim=8)
    meta = mgr.load_pretrained(agent2, ckpt)
    assert meta["platform"] == "SOI"
    # 权重一致
    for a, b in zip(agent.ac.parameters(), agent2.ac.parameters()):
        np.testing.assert_allclose(a.data, b.data)


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
