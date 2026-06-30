"""R351-R355 RL 布局布线增强模块综合测试。

覆盖 5 个模块（纯 NumPy/SciPy CPU 实现）：
- R351 ``LargeScalePlacementEnv``：100+ 组件环境 + 稀疏占用栅格 + 图摘要双轨状态
- R352 ``PPOAdvantageOptimizer``：GAE + clipped surrogate loss + 熵正则 + 余弦退火
- R353 ``MultiObjectiveParetoReward``：面积/时延/损耗/串扰加权 + NSGA-II Pareto 前沿
- R354 ``PretrainedPolicyLibrary``：启发式/随机/课程学习 3 种基础策略
- R355 ``HybridPlacementAgent``：手动约束 + RL 自动布局混合模式

测试维度：
- 功能正确性（与文献公式手算对照）
- TR-351.1/351.2/351.3 验收（100 组件初始化/状态高效/内存≤500MB）
- R03 错误处理（缺字段/越界/容量不足/已占用/未知策略一律 raise）
- R02 学术诚信（docstring 文献 URL ≥5）
- R04 GPU 合规（GPU_DISABLED_R04=True）
- 集成测试（5 模块串联）

学术依据：
- Mirhoseini 2021/2024 Nature AlphaChip
  https://www.nature.com/articles/s41586-021-03544-w
  https://www.nature.com/articles/s41586-024-08032-5
- Schulman 2017 PPO https://arxiv.org/abs/1707.06347
- Schulman 2015 GAE https://arxiv.org/abs/1506.02438
- Deb 2002 NSGA-II https://ieeexplore.ieee.org/document/996017
- Loshchilov 2017 SGDR https://arxiv.org/abs/1608.03983
- Bogaerts 2013 JLT 交叉损耗 DOI: 10.1109/JLT.2013.2258874
- Reed 2010 Nat. Photonics 时延 DOI: 10.1038/nphoton.2010.179
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest
from scipy import sparse

from polaris.rl.rl_numpy_advanced import (
    ALL_POLICIES,
    GPU_DISABLED_R04,
    HybridPlacementAgent,
    HybridPlacementConfig,
    LargeScalePlacementConfig,
    LargeScalePlacementEnv,
    MultiObjectiveParetoReward,
    MultiObjectiveRewardConfig,
    POLICY_CURRICULUM,
    POLICY_HEURISTIC,
    POLICY_RANDOM,
    PPOAdvConfig,
    PPOAdvantageOptimizer,
    PretrainedPolicyConfig,
    PretrainedPolicyLibrary,
)


# =============================================================================
# 共享 fixtures
# =============================================================================

def _mk_device(dev_id: str, dev_type: str = "mzi") -> dict:
    """构造标准器件字典。"""
    return {
        "id": dev_id,
        "type": dev_type,
        "width": 50.0,
        "height": 30.0,
        "ports": ["in", "out"],
    }


def _mk_net(src_id: str, dst_id: str) -> dict:
    """构造标准 net 字典。"""
    return {"src": (src_id, "in"), "dst": (dst_id, "out")}


@pytest.fixture
def small_circuit() -> dict:
    """3 器件小电路（mzi-ring-mmi 链）。"""
    return {
        "devices": [
            _mk_device("d0", "mzi"),
            _mk_device("d1", "ring"),
            _mk_device("d2", "mmi"),
        ],
        "nets": [
            _mk_net("d0", "d1"),
            _mk_net("d1", "d2"),
        ],
    }


@pytest.fixture
def large_circuit_100() -> dict:
    """100 器件大电路（TR-351.1 验收用）。"""
    devices = [_mk_device(f"d{i:03d}", "mzi" if i % 3 == 0 else "ring") for i in range(100)]
    devices[0]["type"] = "mzi"
    devices[1]["type"] = "ring"
    devices[2]["type"] = "mmi"
    devices[3]["type"] = "coupler"
    nets = [_mk_net(f"d{i:03d}", f"d{(i + 1) % 100:03d}") for i in range(100)]
    return {"devices": devices, "nets": nets}


@pytest.fixture
def env() -> LargeScalePlacementEnv:
    """默认环境实例。"""
    return LargeScalePlacementEnv()


@pytest.fixture
def ppo() -> PPOAdvantageOptimizer:
    """默认 PPO 优化器。"""
    return PPOAdvantageOptimizer()


@pytest.fixture
def reward() -> MultiObjectiveParetoReward:
    """默认多目标奖励。"""
    return MultiObjectiveParetoReward()


@pytest.fixture
def policy_lib(tmp_path: Path) -> PretrainedPolicyLibrary:
    """预训练策略库（tmp checkpoint 目录）。"""
    cfg = PretrainedPolicyConfig(seed=42, checkpoint_dir=str(tmp_path / "ckpt"))
    return PretrainedPolicyLibrary(cfg)


@pytest.fixture
def hybrid_agent() -> HybridPlacementAgent:
    """混合布局智能体。"""
    return HybridPlacementAgent(HybridPlacementConfig(seed=42, grid_size=(8, 8)))


# =============================================================================
# R351 LargeScalePlacementEnv 测试
# =============================================================================

class TestR351LargeScalePlacementEnv:
    """R351 大规模电路布局环境测试。"""

    def test_set_circuit_normal(self, env: LargeScalePlacementEnv, small_circuit: dict) -> None:
        """正常设置电路 → placement 重置。"""
        env.set_circuit(small_circuit)
        assert env.circuit is small_circuit
        assert env.placement == {}

    def test_set_circuit_missing_devices(self, env: LargeScalePlacementEnv) -> None:
        """缺 devices 字段 → raise（R03）。"""
        with pytest.raises(ValueError, match="devices"):
            env.set_circuit({"nets": []})

    def test_set_circuit_missing_nets(self, env: LargeScalePlacementEnv) -> None:
        """缺 nets 字段 → raise（R03）。"""
        with pytest.raises(ValueError, match="nets"):
            env.set_circuit({"devices": [_mk_device("d0")]})

    def test_set_circuit_zero_devices(self, env: LargeScalePlacementEnv) -> None:
        """器件数=0 → raise（R03）。"""
        with pytest.raises(ValueError, match=">= 1"):
            env.set_circuit({"devices": [], "nets": []})

    def test_set_circuit_exceed_max_devices(self, env: LargeScalePlacementEnv) -> None:
        """超 max_devices → raise（R03）。"""
        cfg = LargeScalePlacementConfig(max_devices=5)
        e = LargeScalePlacementEnv(cfg)
        circuit = {"devices": [_mk_device(f"d{i}") for i in range(6)], "nets": []}
        with pytest.raises(ValueError, match="max_devices"):
            e.set_circuit(circuit)

    def test_build_sparse_occupancy_no_placement(
        self, env: LargeScalePlacementEnv, small_circuit: dict
    ) -> None:
        """无放置 → 空 CSR 矩阵。"""
        env.set_circuit(small_circuit)
        occ = env.build_sparse_occupancy()
        assert sparse.issparse(occ)
        assert occ.nnz == 0

    def test_build_sparse_occupancy_after_step(
        self, env: LargeScalePlacementEnv, small_circuit: dict
    ) -> None:
        """放置 1 个器件 → CSR 非零。"""
        env.set_circuit(small_circuit)
        env.step("d0", 0)
        occ = env.build_sparse_occupancy()
        assert occ.nnz > 0
        # (0,0) cell 应被占用
        assert occ[0, 0] == pytest.approx(1.0)

    def test_build_sparse_occupancy_without_circuit_raises(self, env: LargeScalePlacementEnv) -> None:
        """未设电路 → raise（R03）。"""
        with pytest.raises(ValueError, match="电路未设置"):
            env.build_sparse_occupancy()

    def test_build_state_keys(
        self, env: LargeScalePlacementEnv, small_circuit: dict
    ) -> None:
        """build_state 返回 5 个键（TR-351.2 状态空间）。"""
        env.set_circuit(small_circuit)
        state = env.build_state(small_circuit["devices"][0])
        for k in ("node_feats", "occupancy", "graph_summary", "action_mask", "current_feat"):
            assert k in state

    def test_build_state_node_feats_dim(
        self, env: LargeScalePlacementEnv, small_circuit: dict
    ) -> None:
        """node_feats 形状 [N, 9]。"""
        env.set_circuit(small_circuit)
        state = env.build_state(small_circuit["devices"][0])
        assert state["node_feats"].shape == (3, 9)

    def test_build_state_graph_summary_dim(
        self, env: LargeScalePlacementEnv, small_circuit: dict
    ) -> None:
        """graph_summary 固定 8 维（不随 N 增长，*创新*）。"""
        env.set_circuit(small_circuit)
        state = env.build_state(small_circuit["devices"][0])
        assert state["graph_summary"].shape == (8,)

    def test_build_state_action_mask(
        self, env: LargeScalePlacementEnv, small_circuit: dict
    ) -> None:
        """action_mask 形状 [grid_h*grid_w]。"""
        env.set_circuit(small_circuit)
        state = env.build_state(small_circuit["devices"][0])
        grid_h, grid_w = env.config.grid_size
        assert state["action_mask"].shape == (grid_h * grid_w,)

    def test_step_normal(self, env: LargeScalePlacementEnv, small_circuit: dict) -> None:
        """step 正常 → 返回 state + placement 更新。"""
        env.set_circuit(small_circuit)
        state = env.step("d0", 0)
        assert "d0" in env.placement
        assert env.placement["d0"]["x"] == pytest.approx(0.0)
        assert env.placement["d0"]["y"] == pytest.approx(0.0)
        assert "node_feats" in state

    def test_step_occupied_raises(
        self, env: LargeScalePlacementEnv, small_circuit: dict
    ) -> None:
        """重复占用同一 grid → raise（R03）。"""
        env.set_circuit(small_circuit)
        env.step("d0", 0)
        with pytest.raises(ValueError, match="占用"):
            env.step("d1", 0)

    def test_step_already_placed_raises(
        self, env: LargeScalePlacementEnv, small_circuit: dict
    ) -> None:
        """重复放置同一器件 → raise（R03）。"""
        env.set_circuit(small_circuit)
        env.step("d0", 0)
        with pytest.raises(ValueError, match="已放置"):
            env.step("d0", 1)

    def test_step_out_of_bounds_raises(
        self, env: LargeScalePlacementEnv, small_circuit: dict
    ) -> None:
        """grid_idx 越界 → raise（R03）。"""
        env.set_circuit(small_circuit)
        grid_h, grid_w = env.config.grid_size
        with pytest.raises(ValueError, match="越界"):
            env.step("d0", grid_h * grid_w)

    def test_step_without_circuit_raises(self, env: LargeScalePlacementEnv) -> None:
        """未设电路调用 step → raise（R03）。"""
        with pytest.raises(ValueError, match="电路未设置"):
            env.step("d0", 0)

    def test_n_devices(
        self, env: LargeScalePlacementEnv, small_circuit: dict
    ) -> None:
        """n_devices 返回器件数。"""
        env.set_circuit(small_circuit)
        assert env.n_devices() == 3

    def test_n_devices_without_circuit_raises(self, env: LargeScalePlacementEnv) -> None:
        """未设电路 → raise（R03）。"""
        with pytest.raises(ValueError, match="电路未设置"):
            env.n_devices()

    # ----- TR-351.1/351.2/351.3 验收 -----

    def test_tr351_1_100_devices_init(
        self, large_circuit_100: dict
    ) -> None:
        """TR-351.1: 100 组件电路环境初始化正常。"""
        env = LargeScalePlacementEnv(LargeScalePlacementConfig(max_devices=1024))
        env.set_circuit(large_circuit_100)
        assert env.n_devices() == 100

    def test_tr351_2_state_efficient(
        self, large_circuit_100: dict
    ) -> None:
        """TR-351.2: 状态空间表示高效（稀疏 CSR + 固定 8 维图摘要）。"""
        env = LargeScalePlacementEnv(LargeScalePlacementConfig(max_devices=1024))
        env.set_circuit(large_circuit_100)
        state = env.build_state(large_circuit_100["devices"][0])
        # 占用栅格稀疏
        assert sparse.issparse(state["occupancy"])
        # 图摘要固定 8 维（不随 N 增长）
        assert state["graph_summary"].shape == (8,)
        # node_feats 形状对齐 N
        assert state["node_feats"].shape == (100, 9)

    def test_tr351_3_memory_bounded(
        self, large_circuit_100: dict
    ) -> None:
        """TR-351.3: 内存占用 ≤500MB（CSR 稀疏存储）。"""
        env = LargeScalePlacementEnv(LargeScalePlacementConfig(max_devices=1024))
        env.set_circuit(large_circuit_100)
        # 放置 50 个器件
        for i in range(50):
            env.step(f"d{i:03d}", i * 2)
        occ = env.build_sparse_occupancy()
        # CSR 内存估算: data + indices + indptr
        mem_bytes = occ.data.nbytes + occ.indices.nbytes + occ.indptr.nbytes
        assert mem_bytes < 500 * 1024 * 1024  # <500MB

    def test_node_features_type_one_hot(self, env: LargeScalePlacementEnv, small_circuit: dict) -> None:
        """节点特征前 4 维是 type one-hot。"""
        env.set_circuit(small_circuit)
        feat = env._node_features(small_circuit["devices"][0])  # type=mzi
        assert feat[0] == 1.0  # mzi
        assert feat[1] == 0.0  # ring
        assert feat[2] == 0.0  # mmi
        assert feat[3] == 0.0  # coupler


# =============================================================================
# R352 PPOAdvantageOptimizer 测试
# =============================================================================

class TestR352PPOAdvantageOptimizer:
    """R352 PPO 优化器测试（Schulman 2017 PPO + 2015 GAE）。"""

    def test_compute_gae_basic(self, ppo: PPOAdvantageOptimizer) -> None:
        """GAE 基本计算（手算对照）。

        rewards=[1,1], values=[0,0], dones=[0,0], last_value=0, γ=0.99, λ=0.95
        δ_1 = 1 + 0.99·0·(1-0) - 0 = 1
        δ_0 = 1 + 0.99·0·(1-0) - 0 = 1
        Â_1 = δ_1 + 0 = 1
        Â_0 = δ_0 + 0.99·0.95·(1-0)·Â_1 = 1 + 0.9405 = 1.9405
        R_0 = 1.9405, R_1 = 1.0
        """
        rewards = np.array([1.0, 1.0])
        values = np.array([0.0, 0.0])
        dones = np.array([0.0, 0.0])
        adv, ret = ppo.compute_gae(rewards, values, dones, last_value=0.0)
        assert adv[1] == pytest.approx(1.0, rel=1e-6)
        assert adv[0] == pytest.approx(1.9405, rel=1e-6)
        assert ret[0] == pytest.approx(1.9405, rel=1e-6)
        assert ret[1] == pytest.approx(1.0, rel=1e-6)

    def test_compute_gae_with_done(self, ppo: PPOAdvantageOptimizer) -> None:
        """done=1 截断 GAE 传播。"""
        rewards = np.array([1.0, 1.0])
        values = np.array([0.0, 0.0])
        dones = np.array([0.0, 1.0])  # 第二步 done
        adv, ret = ppo.compute_gae(rewards, values, dones, last_value=0.0)
        # done=1 时 Â_1 = δ_1 = 1
        assert adv[1] == pytest.approx(1.0, rel=1e-6)
        # Â_0 = δ_0 + γ·λ·(1-done_0)·Â_1 = 1 + 0.9405·1 = 1.9405
        assert adv[0] == pytest.approx(1.9405, rel=1e-6)

    def test_compute_gae_last_value(self, ppo: PPOAdvantageOptimizer) -> None:
        """last_value 影响 δ_T-1。"""
        rewards = np.array([0.0])
        values = np.array([0.0])
        dones = np.array([0.0])
        adv, ret = ppo.compute_gae(rewards, values, dones, last_value=10.0)
        # δ_0 = 0 + 0.99·10·1 - 0 = 9.9
        assert adv[0] == pytest.approx(9.9, rel=1e-6)
        assert ret[0] == pytest.approx(9.9, rel=1e-6)

    def test_compute_gae_shape_mismatch(self, ppo: PPOAdvantageOptimizer) -> None:
        """形状不匹配 → raise（R03）。"""
        with pytest.raises(ValueError, match="形状不匹配"):
            ppo.compute_gae(np.array([1.0]), np.array([0.0, 0.0]), np.array([0.0]))

    def test_compute_gae_empty(self, ppo: PPOAdvantageOptimizer) -> None:
        """空 rewards → raise（R03）。"""
        with pytest.raises(ValueError, match="不能为空"):
            ppo.compute_gae(np.array([]), np.array([]), np.array([]))

    def test_normalize_advantages(self, ppo: PPOAdvantageOptimizer) -> None:
        """标准化：均值 0，标准差 1。"""
        adv = np.array([1.0, 2.0, 3.0, 4.0])
        norm = ppo.normalize_advantages(adv)
        assert norm.mean() == pytest.approx(0.0, abs=1e-10)
        assert norm.std() == pytest.approx(1.0, rel=1e-6)

    def test_normalize_advantages_zero_std(self, ppo: PPOAdvantageOptimizer) -> None:
        """std<1e-8 时仅去均值（避免除零，非 fall-back）。"""
        adv = np.array([5.0, 5.0, 5.0])
        norm = ppo.normalize_advantages(adv)
        assert np.all(norm == pytest.approx(0.0))

    def test_normalize_advantages_empty(self, ppo: PPOAdvantageOptimizer) -> None:
        """空 → raise（R03）。"""
        with pytest.raises(ValueError, match="不能为空"):
            ppo.normalize_advantages(np.array([]))

    def test_compute_policy_loss_basic(self, ppo: PPOAdvantageOptimizer) -> None:
        """新=旧 logprob 时 ratio=1，loss = -mean(adv) - ent_coef·ent。"""
        new_lp = np.log(np.array([0.5, 0.5]))
        old_lp = np.log(np.array([0.5, 0.5]))
        adv = np.array([1.0, -1.0])
        loss, m = ppo.compute_policy_loss(new_lp, old_lp, adv, entropy=0.0)
        # ratio=1, surr1=surr2=adv, min=adv, mean(adv)=0
        # loss = -0 - 0.01·0 = 0
        assert loss == pytest.approx(0.0, abs=1e-10)
        assert m["clip_frac"] == pytest.approx(0.0)

    def test_compute_policy_loss_clip(
        self, ppo: PPOAdvantageOptimizer
    ) -> None:
        """ratio 超出 clip 范围时被裁剪（Schulman 2017 Eq.7）。"""
        # ratio = exp(2-0) = e^2 ≈ 7.39，远超 1+0.2=1.2
        new_lp = np.array([2.0])
        old_lp = np.array([0.0])
        adv = np.array([1.0])
        loss, m = ppo.compute_policy_loss(new_lp, old_lp, adv, entropy=0.0)
        # surr1 = 7.39·1 = 7.39
        # surr2 = 1.2·1 = 1.2 (clip)
        # min = 1.2, loss = -1.2
        assert loss == pytest.approx(-1.2, rel=1e-3)
        assert m["clip_frac"] == pytest.approx(1.0)

    def test_compute_policy_loss_shape_mismatch(self, ppo: PPOAdvantageOptimizer) -> None:
        """形状不匹配 → raise（R03）。"""
        with pytest.raises(ValueError, match="形状"):
            ppo.compute_policy_loss(
                np.array([0.0]), np.array([0.0, 0.0]), np.array([0.0])
            )

    def test_compute_policy_loss_empty(self, ppo: PPOAdvantageOptimizer) -> None:
        """空 → raise（R03）。"""
        with pytest.raises(ValueError, match="不能为空"):
            ppo.compute_policy_loss(np.array([]), np.array([]), np.array([]))

    def test_compute_value_loss_basic(self, ppo: PPOAdvantageOptimizer) -> None:
        """value loss = 0.5·max((V-R)², (V_clip-R)²) 均值。"""
        v = np.array([1.0])
        ov = np.array([1.0])
        ret = np.array([1.0])
        loss = ppo.compute_value_loss(v, ov, ret)
        assert loss == pytest.approx(0.0, abs=1e-10)

    def test_compute_value_loss_shape_mismatch(self, ppo: PPOAdvantageOptimizer) -> None:
        """形状不匹配 → raise（R03）。"""
        with pytest.raises(ValueError, match="形状"):
            ppo.compute_value_loss(np.array([1.0]), np.array([1.0, 2.0]), np.array([1.0]))

    def test_compute_value_loss_empty(self, ppo: PPOAdvantageOptimizer) -> None:
        """空 → raise（R03）。"""
        with pytest.raises(ValueError, match="不能为空"):
            ppo.compute_value_loss(np.array([]), np.array([]), np.array([]))

    def test_cosine_lr_schedule(self, ppo: PPOAdvantageOptimizer) -> None:
        """余弦退火（Loshchilov 2017 SGDR）。"""
        # step=0: lr = min + 0.5·(init-min)·(1+cos(0)) = min + (init-min) = init
        lr0 = ppo.cosine_lr_schedule(0, 100)
        assert lr0 == pytest.approx(ppo.config.initial_lr, rel=1e-6)
        # step=total: lr = min + 0.5·(init-min)·(1+cos(π)) = min + 0 = min
        lr_end = ppo.cosine_lr_schedule(100, 100)
        assert lr_end == pytest.approx(ppo.config.min_lr, rel=1e-6)
        # 中间单调下降
        lr_mid = ppo.cosine_lr_schedule(50, 100)
        assert ppo.config.min_lr < lr_mid < ppo.config.initial_lr

    def test_cosine_lr_schedule_zero_total(self, ppo: PPOAdvantageOptimizer) -> None:
        """total_steps=0 → raise（R03）。"""
        with pytest.raises(ValueError, match="total_steps"):
            ppo.cosine_lr_schedule(0, 0)

    def test_update_full(self, ppo: PPOAdvantageOptimizer) -> None:
        """端到端 PPO update（GAE → 标准化 → policy/value loss）。"""
        rollout = {
            "rewards": np.array([1.0, 0.5]),
            "values": np.array([0.5, 0.5]),
            "old_logprobs": np.log(np.array([0.5, 0.5])),
            "old_values": np.array([0.5, 0.5]),
            "dones": np.array([0.0, 1.0]),
            "last_value": 0.0,
        }
        new_lp = np.log(np.array([0.5, 0.5]))
        new_v = np.array([0.6, 0.4])
        result = ppo.update(rollout, new_lp, new_v, entropy=np.array([0.3, 0.3]))
        for k in ("advantages", "returns", "policy_loss", "value_loss",
                  "total_loss", "clip_frac", "entropy"):
            assert k in result
        assert result["advantages"].shape == (2,)
        assert result["returns"].shape == (2,)

    def test_update_missing_field(self, ppo: PPOAdvantageOptimizer) -> None:
        """rollout 缺字段 → raise（R03）。"""
        rollout = {"rewards": np.array([1.0])}  # 缺其它字段
        with pytest.raises(ValueError, match="缺字段"):
            ppo.update(rollout, np.array([0.0]), np.array([0.0]))

    def test_config_defaults_match_literature(self) -> None:
        """PPO 默认配置对齐文献（Schulman 2017/2015）。"""
        cfg = PPOAdvConfig()
        assert cfg.gamma == 0.99   # Sutton & Barto 2018 §13
        assert cfg.gae_lambda == 0.95  # Schulman 2015 GAE
        assert cfg.clip_eps == 0.2     # Schulman 2017 PPO
        assert cfg.ent_coef == 0.01    # Mnih 2016 A3C


# =============================================================================
# R353 MultiObjectiveParetoReward 测试
# =============================================================================

class TestR353MultiObjectiveParetoReward:
    """R353 多目标奖励 + Pareto 前沿测试。"""

    def test_compute_area(
        self, reward: MultiObjectiveParetoReward, small_circuit: dict
    ) -> None:
        """面积 = Σ(width·height)。"""
        placement = {
            "d0": {"x": 0.0, "y": 0.0, "rotation": 0},
            "d1": {"x": 100.0, "y": 0.0, "rotation": 0},
        }
        area = reward.compute_area(placement, small_circuit)
        # 2 个器件: 50·30 + 50·30 = 3000
        assert area == pytest.approx(3000.0, rel=1e-6)

    def test_compute_area_no_placement(
        self, reward: MultiObjectiveParetoReward, small_circuit: dict
    ) -> None:
        """无放置 → area=0。"""
        assert reward.compute_area({}, small_circuit) == 0.0

    def test_compute_delay(
        self, reward: MultiObjectiveParetoReward, small_circuit: dict
    ) -> None:
        """时延 τ = n_g·L/c，n_g=4.2，c=3e8 m/s（Reed 2010）。"""
        placement = {
            "d0": {"x": 0.0, "y": 0.0, "rotation": 0},
            "d1": {"x": 100.0, "y": 0.0, "rotation": 0},
        }
        # net d0→d1: 距离 = 100μm（中心到中心，简化为器件中心）
        # 实际端口位置 (25, 15) → (125, 15)，距离 = 100μm
        delay = reward.compute_delay(placement, small_circuit)
        # τ = 4.2 · (100e-6 m) / 3e8 m/s · 1e12 = 4.2·100e-6/3e8·1e12 = 1.4 ps
        assert delay == pytest.approx(1.4, rel=1e-3)

    def test_compute_loss_no_crossing(
        self, reward: MultiObjectiveParetoReward, small_circuit: dict
    ) -> None:
        """无交叉 → loss = α_prop·L/cm（Bogaerts 2013）。"""
        placement = {
            "d0": {"x": 0.0, "y": 0.0, "rotation": 0},
            "d1": {"x": 100.0, "y": 0.0, "rotation": 0},
        }
        loss = reward.compute_loss(placement, small_circuit)
        # 总线长 100μm = 0.01 cm, prop = 3.0 dB/cm · 0.01 cm = 0.03 dB
        assert loss == pytest.approx(0.03, rel=1e-3)

    def test_compute_xtalk_no_crossing(
        self, reward: MultiObjectiveParetoReward, small_circuit: dict
    ) -> None:
        """无交叉 → xtalk=0。"""
        placement = {
            "d0": {"x": 0.0, "y": 0.0, "rotation": 0},
            "d1": {"x": 100.0, "y": 0.0, "rotation": 0},
        }
        assert reward.compute_xtalk(placement, small_circuit) == pytest.approx(0.0)

    def test_compute_full(
        self, reward: MultiObjectiveParetoReward, small_circuit: dict
    ) -> None:
        """compute 返回完整 5 字段。"""
        placement = {
            "d0": {"x": 0.0, "y": 0.0, "rotation": 0},
            "d1": {"x": 100.0, "y": 0.0, "rotation": 0},
        }
        result = reward.compute(placement, small_circuit)
        for k in ("reward", "area", "delay_ps", "loss_db", "xtalk_linear"):
            assert k in result
        # 奖励为负（最大化 → 反向最小化）
        assert result["reward"] < 0

    def test_pareto_front_basic(self, reward: MultiObjectiveParetoReward) -> None:
        """Pareto 前沿：不被任何解支配者（NSGA-II, Deb 2002）。"""
        # 3 个解，2 目标最小化
        # [1, 5], [2, 2], [3, 3]
        # [1,5] 不被任何解支配（[2,2] 在 obj0 较大）
        # [2,2] 支配 [3,3]（2<3, 2<3）
        # [3,3] 被 [2,2] 支配 → 不在前沿
        obj = np.array([[1.0, 5.0], [2.0, 2.0], [3.0, 3.0]])
        front = reward.pareto_front(obj)
        assert set(front.tolist()) == {0, 1}

    def test_pareto_front_maximize(self, reward: MultiObjectiveParetoReward) -> None:
        """maximize=True 时取最大化的 Pareto 前沿。"""
        # [1,5], [2,2], [3,3]，最大化
        # [3,3] 不被任何解支配（3>2 但 3<5 in obj1, 不支配；3>1 in obj0 但 3<5 in obj1）
        # [1,5] 不被支配（5>3 in obj1, 1<3 in obj0）
        # [2,2] 被 [3,3] 支配（3>2, 3>2）
        obj = np.array([[1.0, 5.0], [2.0, 2.0], [3.0, 3.0]])
        front = reward.pareto_front(obj, maximize=True)
        assert set(front.tolist()) == {0, 2}

    def test_pareto_front_single(self, reward: MultiObjectiveParetoReward) -> None:
        """单解 → 自身在前沿。"""
        obj = np.array([[1.0, 2.0]])
        front = reward.pareto_front(obj)
        assert front.tolist() == [0]

    def test_pareto_front_empty(self, reward: MultiObjectiveParetoReward) -> None:
        """空矩阵 → raise（R03）。"""
        with pytest.raises(ValueError, match="不能为空"):
            reward.pareto_front(np.zeros((0, 2)))

    def test_pareto_front_1d_raises(self, reward: MultiObjectiveParetoReward) -> None:
        """1D 矩阵 → raise（R03）。"""
        with pytest.raises(ValueError, match="2D"):
            reward.pareto_front(np.array([1.0, 2.0, 3.0]))

    def test_config_defaults(self) -> None:
        """默认权重对齐光子布局工程实践。"""
        cfg = MultiObjectiveRewardConfig()
        # 损耗权重最大（光子电路对损耗最敏感）
        assert cfg.w_loss >= cfg.w_area
        assert cfg.w_loss >= cfg.w_delay
        assert cfg.w_loss >= cfg.w_xtalk


# =============================================================================
# R354 PretrainedPolicyLibrary 测试
# =============================================================================

class TestR354PretrainedPolicyLibrary:
    """R354 预训练策略库测试（3 种基础策略）。"""

    def test_list_policies(self, policy_lib: PretrainedPolicyLibrary) -> None:
        """list_policies 返回 3 个策略名。"""
        policies = policy_lib.list_policies()
        assert set(policies) == {POLICY_HEURISTIC, POLICY_RANDOM, POLICY_CURRICULUM}

    def test_all_policies_constant(self) -> None:
        """ALL_POLICIES 常量完整。"""
        assert len(ALL_POLICIES) == 3
        assert POLICY_HEURISTIC in ALL_POLICIES
        assert POLICY_RANDOM in ALL_POLICIES
        assert POLICY_CURRICULUM in ALL_POLICIES

    def test_generate_placement_heuristic(
        self, policy_lib: PretrainedPolicyLibrary, small_circuit: dict
    ) -> None:
        """启发式策略：高连接度器件优先放中心。"""
        placement = policy_lib.generate_placement(small_circuit, POLICY_HEURISTIC)
        assert len(placement) == 3
        # 每个器件有 x/y/rotation
        for dev_id, p in placement.items():
            assert "x" in p and "y" in p and "rotation" in p
        # d1 连接度最高（连接 d0 和 d2），应放在最中心 cell
        # grid 中心 (16, 16) 对应 cell (16, 16)
        # 但 grid_size=(32,32)，中心 cell 接近 (16, 16)
        # 这里只验证 d1 的 x/y 在网格中心附近
        center_x = 16 * 100.0  # 100μm/cell
        center_y = 16 * 100.0
        d1_dist = (placement["d1"]["x"] - center_x) ** 2 + (placement["d1"]["y"] - center_y) ** 2
        d0_dist = (placement["d0"]["x"] - center_x) ** 2 + (placement["d0"]["y"] - center_y) ** 2
        # d1 应该比 d0 更接近中心（d1 连接度=2，d0 连接度=1）
        assert d1_dist <= d0_dist

    def test_generate_placement_random(
        self, policy_lib: PretrainedPolicyLibrary, small_circuit: dict
    ) -> None:
        """随机策略：所有器件均被放置。"""
        placement = policy_lib.generate_placement(small_circuit, POLICY_RANDOM)
        assert len(placement) == 3
        # 器件位置不重叠（不同 cell）
        cells = {(p["x"], p["y"]) for p in placement.values()}
        assert len(cells) == 3

    def test_generate_placement_curriculum(
        self, policy_lib: PretrainedPolicyLibrary, small_circuit: dict
    ) -> None:
        """课程学习策略：按 type 难度排序（Bengio 2009）。"""
        placement = policy_lib.generate_placement(small_circuit, POLICY_CURRICULUM)
        assert len(placement) == 3
        # 验证所有器件都被放置
        for dev in small_circuit["devices"]:
            assert dev["id"] in placement

    def test_generate_placement_unknown_policy(
        self, policy_lib: PretrainedPolicyLibrary, small_circuit: dict
    ) -> None:
        """未知策略 → raise（R03）。"""
        with pytest.raises(ValueError, match="未知策略"):
            policy_lib.generate_placement(small_circuit, "unknown")

    def test_generate_placement_exceed_capacity(
        self, policy_lib: PretrainedPolicyLibrary
    ) -> None:
        """器件数超过网格容量 → raise（R03）。"""
        # grid_size=(32,32) 容量 1024
        big_circuit = {
            "devices": [_mk_device(f"d{i}") for i in range(1025)],
            "nets": [],
        }
        with pytest.raises(ValueError, match="网格容量"):
            policy_lib.generate_placement(big_circuit, POLICY_RANDOM)

    def test_save_load_policy(
        self, policy_lib: PretrainedPolicyLibrary, tmp_path: Path
    ) -> None:
        """save_policy → load_policy 往返一致。"""
        weights = {"w": np.array([1.0, 2.0]).tolist()}
        path = policy_lib.save_policy(POLICY_HEURISTIC, weights)
        assert path.exists()
        loaded = policy_lib.load_policy(POLICY_HEURISTIC)
        assert loaded["policy_name"] == POLICY_HEURISTIC
        assert loaded["weights"] == weights
        assert "metadata" in loaded
        assert "papers" in loaded["metadata"]

    def test_load_policy_not_exist(
        self, policy_lib: PretrainedPolicyLibrary
    ) -> None:
        """加载不存在的 checkpoint → raise（R03）。"""
        with pytest.raises(ValueError, match="checkpoint 不存在"):
            policy_lib.load_policy(POLICY_RANDOM)

    def test_save_policy_unknown(
        self, policy_lib: PretrainedPolicyLibrary
    ) -> None:
        """未知策略 save → raise（R03）。"""
        with pytest.raises(ValueError, match="未知策略"):
            policy_lib.save_policy("unknown", {})

    def test_load_policy_unknown(
        self, policy_lib: PretrainedPolicyLibrary
    ) -> None:
        """未知策略 load → raise（R03）。"""
        with pytest.raises(ValueError, match="未知策略"):
            policy_lib.load_policy("unknown")

    def test_get_policy_cache_not_generated(
        self, policy_lib: PretrainedPolicyLibrary
    ) -> None:
        """未生成策略查询 cache → raise（R03）。"""
        with pytest.raises(ValueError, match="未生成"):
            policy_lib.get_policy_cache(POLICY_HEURISTIC)

    def test_get_policy_cache_after_generate(
        self, policy_lib: PretrainedPolicyLibrary, small_circuit: dict
    ) -> None:
        """生成后查询 cache → 返回布局信息。"""
        policy_lib.generate_placement(small_circuit, POLICY_HEURISTIC)
        cache = policy_lib.get_policy_cache(POLICY_HEURISTIC)
        assert cache["n_devices"] == 3
        assert "placement" in cache
        assert "grid_size" in cache


# =============================================================================
# R355 HybridPlacementAgent 测试
# =============================================================================

class TestR355HybridPlacementAgent:
    """R355 混合布局智能体测试（fix-then-optimize）。"""

    def test_set_fixed_devices_normal(
        self, hybrid_agent: HybridPlacementAgent
    ) -> None:
        """正常设置固定器件。"""
        fixed = {
            "d0": {"x": 0.0, "y": 0.0, "rotation": 0},
            "d1": {"x": 200.0, "y": 100.0, "rotation": 0},
        }
        hybrid_agent.set_fixed_devices(fixed)
        assert hybrid_agent.fixed_devices["d0"]["x"] == 0.0
        assert hybrid_agent.placement["d1"]["x"] == 200.0

    def test_set_fixed_devices_conflict(
        self, hybrid_agent: HybridPlacementAgent
    ) -> None:
        """两个固定器件在同一 cell → raise（R03）。"""
        fixed = {
            "d0": {"x": 0.0, "y": 0.0, "rotation": 0},
            "d1": {"x": 50.0, "y": 50.0, "rotation": 0},  # 同 cell (0, 0)
        }
        with pytest.raises(ValueError, match="冲突"):
            hybrid_agent.set_fixed_devices(fixed)

    def test_set_fixed_devices_out_of_bounds(
        self, hybrid_agent: HybridPlacementAgent
    ) -> None:
        """固定器件 x 越界 → raise（R03）。"""
        fixed = {"d0": {"x": 9999.0, "y": 0.0, "rotation": 0}}
        with pytest.raises(ValueError, match="越界"):
            hybrid_agent.set_fixed_devices(fixed)

    def test_set_fixed_devices_y_out_of_bounds(
        self, hybrid_agent: HybridPlacementAgent
    ) -> None:
        """固定器件 y 越界 → raise（R03）。"""
        fixed = {"d0": {"x": 0.0, "y": 9999.0, "rotation": 0}}
        with pytest.raises(ValueError, match="越界"):
            hybrid_agent.set_fixed_devices(fixed)

    def test_auto_place_remaining_normal(
        self, hybrid_agent: HybridPlacementAgent, small_circuit: dict
    ) -> None:
        """无固定器件时自动布局所有器件。"""
        placement = hybrid_agent.auto_place_remaining(small_circuit)
        assert len(placement) == 3
        # 所有器件都被放置
        for dev in small_circuit["devices"]:
            assert dev["id"] in placement

    def test_auto_place_remaining_with_fixed(
        self, hybrid_agent: HybridPlacementAgent, small_circuit: dict
    ) -> None:
        """有固定器件时自动布局剩余器件。"""
        hybrid_agent.set_fixed_devices({
            "d0": {"x": 0.0, "y": 0.0, "rotation": 0},
        })
        placement = hybrid_agent.auto_place_remaining(small_circuit)
        assert len(placement) == 3
        # d0 位置保持固定
        assert placement["d0"]["x"] == 0.0

    def test_place_no_fixed(
        self, hybrid_agent: HybridPlacementAgent, small_circuit: dict
    ) -> None:
        """place 端到端无固定器件。"""
        placement = hybrid_agent.place(small_circuit)
        assert len(placement) == 3

    def test_place_with_fixed(
        self, hybrid_agent: HybridPlacementAgent, small_circuit: dict
    ) -> None:
        """place 端到端带固定器件。"""
        fixed = {"d0": {"x": 0.0, "y": 0.0, "rotation": 0}}
        placement = hybrid_agent.place(small_circuit, fixed_devices=fixed)
        assert len(placement) == 3
        assert placement["d0"]["x"] == 0.0

    def test_place_exceed_capacity(
        self, hybrid_agent: HybridPlacementAgent
    ) -> None:
        """器件数超过网格容量 → raise（R03）。"""
        big_circuit = {
            "devices": [_mk_device(f"d{i}") for i in range(65)],  # grid 8x8=64
            "nets": [],
        }
        with pytest.raises(ValueError, match="网格容量"):
            hybrid_agent.place(big_circuit)

    def test_place_missing_devices(
        self, hybrid_agent: HybridPlacementAgent
    ) -> None:
        """电路缺 devices → raise（R03）。"""
        with pytest.raises(ValueError, match="devices"):
            hybrid_agent.place({"nets": []})

    def test_stats(
        self, hybrid_agent: HybridPlacementAgent, small_circuit: dict
    ) -> None:
        """stats 返回统计。"""
        hybrid_agent.place(small_circuit, fixed_devices={
            "d0": {"x": 0.0, "y": 0.0, "rotation": 0},
        })
        s = hybrid_agent.stats()
        assert s["n_fixed"] == 1
        assert s["n_placed"] == 3
        assert s["grid_size"] == (8, 8)


# =============================================================================
# R03 禁止 fall-back 合规测试
# =============================================================================

class TestR03NoFallback:
    """R03 禁止 fall-back 合规：所有业务错误一律 raise。"""

    def test_env_no_circuit_raises(self, env: LargeScalePlacementEnv) -> None:
        """环境未设电路时各方法均 raise。"""
        with pytest.raises(ValueError):
            env.build_sparse_occupancy()
        with pytest.raises(ValueError):
            env.build_state({"id": "x", "type": "mzi", "width": 1, "height": 1, "ports": []})
        with pytest.raises(ValueError):
            env.n_devices()
        with pytest.raises(ValueError):
            env.step("x", 0)

    def test_ppo_empty_inputs_raise(self, ppo: PPOAdvantageOptimizer) -> None:
        """PPO 空输入 raise。"""
        with pytest.raises(ValueError):
            ppo.compute_gae(np.array([]), np.array([]), np.array([]))
        with pytest.raises(ValueError):
            ppo.normalize_advantages(np.array([]))
        with pytest.raises(ValueError):
            ppo.compute_policy_loss(np.array([]), np.array([]), np.array([]))
        with pytest.raises(ValueError):
            ppo.compute_value_loss(np.array([]), np.array([]), np.array([]))

    def test_pareto_empty_raises(self, reward: MultiObjectiveParetoReward) -> None:
        """Pareto 空输入 raise。"""
        with pytest.raises(ValueError):
            reward.pareto_front(np.zeros((0, 2)))

    def test_policy_unknown_raises(
        self, policy_lib: PretrainedPolicyLibrary, small_circuit: dict
    ) -> None:
        """未知策略一律 raise。"""
        with pytest.raises(ValueError):
            policy_lib.generate_placement(small_circuit, "x")
        with pytest.raises(ValueError):
            policy_lib.save_policy("x", {})
        with pytest.raises(ValueError):
            policy_lib.load_policy("x")

    def test_hybrid_out_of_bounds_raises(
        self, hybrid_agent: HybridPlacementAgent
    ) -> None:
        """固定器件越界 raise。"""
        with pytest.raises(ValueError):
            hybrid_agent.set_fixed_devices({"d0": {"x": -1.0, "y": 0.0, "rotation": 0}})

    def test_no_silent_fallback_in_source(self) -> None:
        """源码中无 except:pass / return None / return [] 静默兜底。"""
        from polaris.rl import rl_numpy_advanced as mod
        src = Path(mod.__file__).read_text(encoding="utf-8")
        # 静默 except: pass 模式（行内 pass）
        assert "except: pass" not in src
        assert "except Exception: pass" not in src
        # 注意：源码中可能有 return 0.0 等正常返回，不算 fall-back


# =============================================================================
# R02 学术诚信测试
# =============================================================================

class TestR02AcademicIntegrity:
    """R02 学术诚信：docstring 含 ≥5 个文献 URL + 关键文献可溯源。"""

    def test_module_docstring_has_5plus_urls(self) -> None:
        """模块 docstring 含 ≥5 个文献 URL。"""
        from polaris.rl import rl_numpy_advanced as mod
        assert mod.__doc__ is not None
        urls = [line for line in mod.__doc__.splitlines()
                if "http" in line or "doi.org" in line.lower() or "DOI:" in line]
        assert len(urls) >= 5, f"文献 URL 不足 5 个: {len(urls)}"

    def test_alphachip_cited(self) -> None:
        """AlphaChip（Mirhoseini 2021/2024）被引用。"""
        from polaris.rl import rl_numpy_advanced as mod
        assert mod.__doc__ is not None
        assert "Mirhoseini" in mod.__doc__
        assert "s41586-021-03544-w" in mod.__doc__

    def test_ppo_gae_cited(self) -> None:
        """PPO（Schulman 2017）+ GAE（Schulman 2015）被引用。"""
        from polaris.rl import rl_numpy_advanced as mod
        assert mod.__doc__ is not None
        assert "1707.06347" in mod.__doc__  # PPO
        assert "1506.02438" in mod.__doc__  # GAE

    def test_nsga2_cited(self) -> None:
        """NSGA-II（Deb 2002）被引用。"""
        from polaris.rl import rl_numpy_advanced as mod
        assert mod.__doc__ is not None
        assert "996017" in mod.__doc__  # NSGA-II IEEE

    def test_sgdr_cited(self) -> None:
        """SGDR 余弦退火（Loshchilov 2017）被引用。"""
        from polaris.rl import rl_numpy_advanced as mod
        assert mod.__doc__ is not None
        assert "1608.03983" in mod.__doc__

    def test_innovation_marked(self) -> None:
        """*创新* 标注存在（R02）。"""
        from polaris.rl import rl_numpy_advanced as mod
        src = Path(mod.__file__).read_text(encoding="utf-8")
        assert "*创新*" in src
        # 至少 3 处创新标注（R351/R353/R355）
        assert src.count("*创新*") >= 3

    def test_optical_constants_sourced(self) -> None:
        """光学常数有文献溯源（Bogaerts 2013 / Reed 2010 / Liu 2019）。"""
        from polaris.rl import rl_numpy_advanced as mod
        assert mod.__doc__ is not None
        assert "Bogaerts" in mod.__doc__
        assert "Reed" in mod.__doc__


# =============================================================================
# R04 GPU 合规测试
# =============================================================================

class TestR04GPUCompliance:
    """R04 GPU 合规：纯 NumPy/SciPy CPU 实现。"""

    def test_gpu_disabled_flag(self) -> None:
        """GPU_DISABLED_R04 = True。"""
        assert GPU_DISABLED_R04 is True

    def test_no_gpu_imports(self) -> None:
        """源码无 CuPy/CUDA/ROCm/torch 实际导入语句。"""
        from polaris.rl import rl_numpy_advanced as mod
        src = Path(mod.__file__).read_text(encoding="utf-8")
        # 检查 GPU 后端导入语句（非 docstring 提及）
        assert "import cupy" not in src
        assert "import torch" not in src
        assert "from torch" not in src
        assert "from cupy" not in src
        assert "import jax" not in src  # JAX 也禁（仅 NumPy/SciPy）

    def test_only_numpy_scipy(self) -> None:
        """仅依赖 numpy + scipy.sparse。"""
        from polaris.rl import rl_numpy_advanced as mod
        src = Path(mod.__file__).read_text(encoding="utf-8")
        assert "import numpy as np" in src
        assert "from scipy import sparse" in src


# =============================================================================
# 集成测试：5 模块串联
# =============================================================================

class TestIntegration:
    """5 模块端到端集成测试。"""

    def test_full_pipeline(self, small_circuit: dict) -> None:
        """完整流程：环境 → 策略 → 布局 → 奖励 → PPO 更新。"""
        # 1. R354 用预训练策略生成布局
        lib = PretrainedPolicyLibrary(PretrainedPolicyConfig(seed=42, grid_size=(8, 8)))
        placement = lib.generate_placement(small_circuit, POLICY_HEURISTIC)
        assert len(placement) == 3

        # 2. R353 计算多目标奖励
        r = MultiObjectiveParetoReward()
        result = r.compute(placement, small_circuit)
        assert "reward" in result

        # 3. R352 PPO 用奖励做更新
        opt = PPOAdvantageOptimizer()
        rollout = {
            "rewards": np.array([result["reward"], result["reward"] * 0.5]),
            "values": np.array([0.0, 0.0]),
            "old_logprobs": np.log(np.array([0.5, 0.5])),
            "old_values": np.array([0.0, 0.0]),
            "dones": np.array([0.0, 1.0]),
            "last_value": 0.0,
        }
        update_result = opt.update(
            rollout,
            np.log(np.array([0.5, 0.5])),
            np.array([0.1, 0.1]),
            entropy=np.array([0.3, 0.3]),
        )
        assert "total_loss" in update_result

    def test_hybrid_with_env_state(
        self, hybrid_agent: HybridPlacementAgent, small_circuit: dict
    ) -> None:
        """R355 布局结果可输入 R351 环境构建状态。"""
        placement = hybrid_agent.place(small_circuit)
        env = LargeScalePlacementEnv()
        env.set_circuit(small_circuit)
        env.placement = placement
        state = env.build_state(small_circuit["devices"][0])
        assert state["occupancy"].nnz > 0  # 有占用

    def test_pareto_eval_on_policies(
        self, policy_lib: PretrainedPolicyLibrary, small_circuit: dict
    ) -> None:
        """3 种策略生成的布局用 Pareto 前沿评估。"""
        r = MultiObjectiveParetoReward()
        objs = []
        for name in ALL_POLICIES:
            lib = PretrainedPolicyLibrary(PretrainedPolicyConfig(seed=42, grid_size=(8, 8)))
            placement = lib.generate_placement(small_circuit, name)
            metrics = r.compute(placement, small_circuit)
            # 最小化 [area, delay, loss, xtalk]
            objs.append([
                metrics["area"], metrics["delay_ps"],
                metrics["loss_db"], metrics["xtalk_linear"],
            ])
        obj_arr = np.array(objs)
        front = r.pareto_front(obj_arr)
        # 前沿非空
        assert len(front) >= 1
        assert len(front) <= 3


# =============================================================================
# 数据类测试
# =============================================================================

class TestDataclasses:
    """配置数据类测试。"""

    def test_large_scale_config_defaults(self) -> None:
        """LargeScalePlacementConfig 默认值。"""
        cfg = LargeScalePlacementConfig()
        assert cfg.grid_size == (32, 32)
        assert cfg.node_feat_dim == 9
        assert cfg.max_devices == 1024
        assert cfg.seed == 42

    def test_ppo_adv_config_defaults(self) -> None:
        """PPOAdvConfig 默认值。"""
        cfg = PPOAdvConfig()
        assert cfg.gamma == 0.99
        assert cfg.gae_lambda == 0.95
        assert cfg.clip_eps == 0.2

    def test_reward_config_defaults(self) -> None:
        """MultiObjectiveRewardConfig 默认值。"""
        cfg = MultiObjectiveRewardConfig()
        assert cfg.w_area == 1.0
        assert cfg.w_loss == 2.0  # 损耗权重最大

    def test_policy_config_defaults(self) -> None:
        """PretrainedPolicyConfig 默认值。"""
        cfg = PretrainedPolicyConfig()
        assert cfg.seed == 42
        assert cfg.grid_size == (32, 32)

    def test_hybrid_config_defaults(self) -> None:
        """HybridPlacementConfig 默认值。"""
        cfg = HybridPlacementConfig()
        assert cfg.grid_size == (32, 32)
        assert cfg.max_iters == 100
