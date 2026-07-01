"""R366-R450 RL 布局布线进阶验收 + 综合集成单元测试。

本文件覆盖两个维度，与 ``test_r401_r450_rl_advanced.py``（R401-R405 细节级）
互补，从**验收级**与**综合集成级**两个视角验证 RL 进阶功能：

## R366-R370 验收级测试（对标商业产品 AlphaChip/DREAMPlace 验收指标）

- R366 大规模电路布局：>1000 器件规模支持（LargeScaleGraphPartitioner +
  PartitionedParallelPlacer 验收：1500 器件完整布局 + 平衡约束）
- R367 PPO 算法优化：PPO-Clip + GAE 优势估计（PPOAdvantageOptimizer.compute_gae
  数学正确性 + PPO clipped surrogate loss 单调性）
- R368 多目标奖励：布线长度 + 面积 + 拥塞 + 时序加权（TimingWirelengthReward
  四分量独立 + 权重可调验收）
- R369 预训练模型：布局经验迁移（PolicyTransferManager pretrain→transfer→
  fine_tune 完整闭环验收）
- R370 混合布局：RL + 解析法混合策略（AnalyticalRLHybridPlacer 解析初局 +
  RL 精修奖励改善验收）

## R391-R396 综合集成测试（rl_integration.py 端到端流水线）

- R391 RLPipeline：端到端 RL 训练流水线
- R392 CrossModuleIntegration：跨模块集成（PPO+Curiosity / BC+CQL）
- R393 AlgorithmComparator：算法对比器（Wilcoxon + bootstrap CI）
- R394 RegressionTestSuite：回归测试套件
- R395 DocumentationGenerator：API 文档自动生成
- R396 TutorialGenerator：教程示例自动生成

## 学术依据（R02 学术诚信，≥5 个文献 URL）

1. Mirhoseini et al., Nature 2021, AlphaChip（edge GNN + 预训练迁移）
   https://www.nature.com/articles/s41586-021-03544-w
2. Mirhoseini et al., Nature 2024, AlphaChip addendum（pre-trained checkpoint）
   https://www.nature.com/articles/s41586-024-08032-5
3. Schulman et al., 2017, PPO clip + GAE
   https://arxiv.org/abs/1707.06347
4. Schulman et al., 2015, GAE（广义优势估计）
   https://arxiv.org/abs/1506.02438
5. Engstrom et al., 2020, PPO Implementation Matters（KL 自适应）
   https://arxiv.org/abs/2005.12729
6. Lin et al., TCAD 2020, DREAMPlace（解析法 + HPWL + RUDY）
   https://arxiv.org/abs/2004.10746
7. Kirkpatrick et al., PNAS 2017, EWC（Fisher 正则化防灾难性遗忘）
   https://www.pnas.org/doi/full/10.1073/pnas.1611835114
8. Karypis & Kumar, 1998, METIS 多级图划分
   https://www.cs.umn.edu/~karypis/metis/
9. Agarwal et al., 2021 NeurIPS, Statistical Precipice（Wilcoxon + bootstrap）
   https://arxiv.org/abs/2108.13264
10. Henderson et al., 2018, Deep RL Reproducibility
    https://arxiv.org/abs/1709.06560

## R03 禁止 fall-back

所有业务错误一律 ``raise``，禁止 except:pass / return None / 假数据兜底。

## R04 不参与 GPU

🚫纯 NumPy/SciPy CPU 实现，禁止 torch/CuPy/CUDA/ROCm。
"""

from __future__ import annotations

import numpy as np
import pytest
from scipy import sparse

from polaris.rl.rl_advanced import (
    AdaptivePPOConfig,
    AdaptivePPOOptimizer,
    AnalyticalHybridConfig,
    AnalyticalRLHybridPlacer,
    GraphPartitionConfig,
    LargeScaleGraphPartitioner,
    PartitionedParallelPlacer,
    PartitionedPlacementConfig,
    PolicyTransferConfig,
    PolicyTransferManager,
    TimingWirelengthReward,
    TimingWirelengthRewardConfig,
    build_adjacency,
)
from polaris.rl.rl_numpy_advanced import (
    PPOAdvConfig,
    PPOAdvantageOptimizer,
    _CANVAS_SIZE_UM,
)
from polaris.rl.rl_integration import (
    AlgorithmComparator,
    ComparisonConfig,
    CrossModuleIntegration,
    DocumentationGenerator,
    PipelineConfig,
    PipelineResult,
    RLPipeline,
    RegressionTestSuite,
    ReportConfig,
    TutorialGenerator,
    AlgorithmReportGenerator,
)


# ---------------------------------------------------------------------------
# 测试数据工厂
# ---------------------------------------------------------------------------


def _make_circuit(n: int = 12, seed: int = 1, target_delay_ps: float = 5.0) -> dict:
    """构造链式 + 随机连接测试电路（与 test_r401 共用风格）。"""
    rng = np.random.default_rng(seed)
    devs = [
        {"id": f"d{i}", "type": "mzi", "width": 50.0, "height": 30.0,
         "ports": ["p0", "p1"]}
        for i in range(n)
    ]
    nets = []
    for i in range(n - 1):
        nets.append({
            "src": [f"d{i}", "p1"], "dst": [f"d{i+1}", "p0"],
            "type": "waveguide", "target_delay_ps": target_delay_ps,
        })
    for _ in range(max(n // 2, 1)):
        a, b = int(rng.integers(0, n)), int(rng.integers(0, n))
        if a != b:
            nets.append({"src": [f"d{a}", "p1"], "dst": [f"d{b}", "p0"]})
    return {"devices": devs, "nets": nets}


def _make_large_circuit(n: int = 1500, seed: int = 99) -> dict:
    """构造 >1000 器件大规模电路（R366 验收级）。"""
    rng = np.random.default_rng(seed)
    devs = [
        {"id": f"d{i}", "type": "mzi", "width": 50.0, "height": 30.0,
         "ports": ["p0", "p1"]}
        for i in range(n)
    ]
    nets = []
    for i in range(n - 1):
        nets.append({"src": [f"d{i}", "p1"], "dst": [f"d{i+1}", "p0"]})
    for _ in range(n // 3):
        a, b = int(rng.integers(0, n)), int(rng.integers(0, n))
        if a != b:
            nets.append({"src": [f"d{a}", "p1"], "dst": [f"d{b}", "p0"]})
    return {"devices": devs, "nets": nets}


# ===========================================================================
# R366 — 大规模电路布局：>1000 器件规模支持（验收级）
# ===========================================================================


class TestR366LargeScalePlacementAcceptance:
    """R366 验收级：>1000 器件大规模电路布局。

    验收指标（对标 AlphaChip/DREAMPlace 工业级 hierarchical placement）：
    - 1500 器件可完整分割 + 布局
    - 分区平衡（±25%）
    - 所有器件位置在画布内
    """

    def test_r366_1500_devices_partition_balanced(self):
        """R366 验收：1500 器件 8 分区，标签全覆盖且平衡。"""
        n = 1500
        circuit = _make_large_circuit(n, seed=99)
        part = LargeScaleGraphPartitioner(
            GraphPartitionConfig(n_partitions=8, coarse_threshold=128,
                                 fm_max_nodes=2000, seed=42)
        )
        labels = part.partition(circuit)
        assert labels.shape == (n,)
        assert len(set(labels.tolist())) == 8
        counts = np.bincount(labels, minlength=8)
        target = n / 8
        # ±25% 平衡容忍
        assert counts.max() <= target * 1.25 + 1
        assert counts.min() >= target * 0.75 - 1

    def test_r366_1500_devices_placement_complete(self):
        """R366 验收：1500 器件分区并行布局，全部放置且位置合法。

        grid (48,48) → 2304 cells / 8 分区 = 288 cells/分区，
        足以容纳最大分区 ~234 器件（1500/8·1.25）。
        """
        n = 1500
        circuit = _make_large_circuit(n, seed=100)
        part = LargeScaleGraphPartitioner(
            GraphPartitionConfig(n_partitions=8, seed=42)
        )
        placer = PartitionedParallelPlacer(
            part, PartitionedPlacementConfig(grid_size=(48, 48))
        )
        placement = placer.place(circuit)
        assert len(placement) == n
        max_xy = 47 * 100.0 + 1e-6
        for dev_id, p in placement.items():
            assert 0.0 <= p["x"] <= max_xy
            assert 0.0 <= p["y"] <= max_xy
            assert p["rotation"] == 0

    def test_r366_adjacency_build_symmetric(self):
        """R366 验收：大规模图邻接矩阵对称、对角为 0。"""
        circuit = _make_large_circuit(1200, seed=7)
        adj = build_adjacency(circuit)
        assert sparse.issparse(adj)
        assert adj.shape == (1200, 1200)
        dense = adj.toarray()
        assert np.allclose(dense, dense.T)
        assert np.all(np.diag(dense) == 0.0)


# ===========================================================================
# R367 — PPO 算法优化：PPO-Clip + GAE 优势估计（验收级）
# ===========================================================================


class TestR367PPOClipGAEAcceptance:
    """R367 验收级：PPO-Clip surrogate loss + GAE 优势估计数学正确性。

    验收指标（对标 Schulman 2017 PPO + Schulman 2015 GAE）：
    - GAE 优势估计数学正确（δ_t = r_t + γV(s_{t+1}) - V(s_t)）
    - PPO clipped surrogate loss 在 r_t∈[1-ε,1+ε] 内无 clip
    - PPO clip 在 r_t 超出范围时截断
    """

    def test_r367_gae_td_residual_correctness(self):
        """R367 验收：GAE 优势 = TD 残差（λ=0 时 Â_t = δ_t）。"""
        ppo = PPOAdvantageOptimizer(PPOAdvConfig(gae_lambda=0.0, gamma=0.9))
        rewards = np.array([1.0, 0.5, 0.3])
        values = np.array([0.4, 0.3, 0.2])
        dones = np.array([0.0, 0.0, 1.0])
        adv, ret = ppo.compute_gae(rewards, values, dones, last_value=0.0)
        # λ=0: Â_t = δ_t = r_t + γ·V(s_{t+1})·(1-done) - V(s_t)
        delta_2 = 0.3 + 0.9 * 0.0 * (1 - 1.0) - 0.2  # done=1 → next_v 不计
        assert abs(adv[2] - delta_2) < 1e-9
        delta_1 = 0.5 + 0.9 * 0.2 * (1 - 0.0) - 0.3
        assert abs(adv[1] - delta_1) < 1e-9
        # returns = adv + values
        assert np.allclose(ret, adv + values)

    def test_r367_gae_lambda_full_monte_carlo(self):
        """R367 验收：λ=1 时 GAE 退化为 Monte-Carlo 回报。"""
        ppo = PPOAdvantageOptimizer(PPOAdvConfig(gae_lambda=1.0, gamma=1.0))
        rewards = np.array([1.0, 1.0, 1.0])
        values = np.array([0.0, 0.0, 0.0])
        dones = np.array([0.0, 0.0, 1.0])
        adv, _ = ppo.compute_gae(rewards, values, dones, last_value=0.0)
        # λ=1, γ=1: Â_t = Σ_{k≥t} r_k（Monte-Carlo）
        # Â_2 = r_2 = 1, Â_1 = r_1 + r_2 = 2, Â_0 = r_0 + r_1 + r_2 = 3
        assert abs(adv[2] - 1.0) < 1e-9
        assert abs(adv[1] - 2.0) < 1e-9
        assert abs(adv[0] - 3.0) < 1e-9

    def test_r367_ppo_clip_no_clip_inside_range(self):
        """R367 验收：r_t∈[1-ε,1+ε] 时 PPO 无 clip，loss = -r_t·Â_t。"""
        ppo = PPOAdvantageOptimizer(PPOAdvConfig(clip_eps=0.2))
        # logprob 比率 r_t = exp(new - old) = 1.0（在 clip 范围内）
        new_lp = np.log(np.array([0.5]))
        old_lp = np.log(np.array([0.5]))
        adv = np.array([1.0])
        loss, info = ppo.compute_policy_loss(new_lp, old_lp, adv, entropy=0.0)
        # r_t=1, Â=1 → L^CLIP = -min(1·1, clip(1,0.8,1.2)·1) = -1.0
        assert abs(loss - (-1.0)) < 1e-9
        assert info["clip_frac"] == 0.0

    def test_r367_ppo_clip_truncated_outside_range(self):
        """R367 验收：r_t 超出 [1-ε,1+ε] 时 PPO clip 生效。"""
        ppo = PPOAdvantageOptimizer(PPOAdvConfig(clip_eps=0.2))
        # r_t = exp(new - old) = exp(2.0) ≈ 7.39（远超 1+ε=1.2）
        new_lp = np.array([np.log(0.5) + 2.0])
        old_lp = np.log(np.array([0.5]))
        adv = np.array([1.0])
        loss, info = ppo.compute_policy_loss(new_lp, old_lp, adv, entropy=0.0)
        # clip 生效：min(7.39·1, 1.2·1) = 1.2 → L = -1.2
        assert abs(loss - (-1.2)) < 1e-6
        assert info["clip_frac"] == 1.0

    def test_r367_gae_empty_rewards_raise(self):
        """R03：空 rewards 必须 raise（禁止 fall-back）。"""
        ppo = PPOAdvantageOptimizer()
        with pytest.raises(ValueError, match="不能为空"):
            ppo.compute_gae(np.array([]), np.array([]), np.array([]))


# ===========================================================================
# R368 — 多目标奖励：布线长度+面积+拥塞+时序加权（验收级）
# ===========================================================================


class TestR368MultiObjectiveRewardAcceptance:
    """R368 验收级：四目标加权奖励（面积+线长+拥塞+时序）。

    验收指标（对标 DREAMPlace 4.0 timing-driven + RUDY 拥塞）：
    - 四个分量独立计算且非负
    - 权重独立可调，权重为 0 的分量不贡献
    - 奖励为加权和的负值（最大化奖励 = 最小化惩罚）
    """

    def test_r368_four_objectives_all_present(self):
        """R368 验收：四分量（area/wirelength/congestion/timing）全部存在且非负。"""
        circuit = _make_circuit(10, seed=4, target_delay_ps=0.001)
        placement = {
            f"d{i}": {"x": float(i * 100.0), "y": float(i % 3 * 100.0),
                       "rotation": 0}
            for i in range(10)
        }
        r = TimingWirelengthReward()
        res = r.compute(placement, circuit)
        for key in ("area", "wirelength", "congestion", "timing_tns_ps", "reward"):
            assert key in res
        assert res["area"] > 0.0
        assert res["wirelength"] >= 0.0
        assert res["congestion"] >= 0.0
        assert res["timing_tns_ps"] >= 0.0
        assert res["reward"] <= 0.0

    def test_r368_weights_independent_zero_isolated(self):
        """R368 验收：各权重独立，权重 0 的分量不贡献奖励。

        面积归一化: area_norm = area / (CANVAS_SIZE²)
        线长归一化: wl_norm = wl / CANVAS_SIZE
        """
        circuit = _make_circuit(8, seed=5)
        placement = {
            f"d{i}": {"x": float(i * 150.0), "y": 0.0, "rotation": 0}
            for i in range(8)
        }
        # 仅面积权重
        cfg_area = TimingWirelengthRewardConfig(
            w_area=1.0, w_wirelength=0.0, w_congestion=0.0, w_timing=0.0
        )
        r_area = TimingWirelengthReward(cfg_area)
        res_area = r_area.compute(placement, circuit)
        canvas_area = _CANVAS_SIZE_UM ** 2
        area_norm = res_area["area"] / canvas_area
        assert abs(res_area["reward"] - (-1.0 * area_norm)) < 1e-9
        # 仅时序权重
        cfg_t = TimingWirelengthRewardConfig(
            w_area=0.0, w_wirelength=0.0, w_congestion=0.0, w_timing=3.0
        )
        r_t = TimingWirelengthReward(cfg_t)
        res_t = r_t.compute(placement, circuit)
        assert res_t["timing_tns_ps"] > 0.0  # 长 net 必负 slack

    def test_r368_reward_improves_with_compact_placement(self):
        """R368 验收：紧凑布局（线长短）奖励优于松散布局（线长长）。"""
        circuit = _make_circuit(8, seed=6, target_delay_ps=1000.0)
        # 紧凑布局
        compact = {
            f"d{i}": {"x": float(i * 100.0), "y": 0.0, "rotation": 0}
            for i in range(8)
        }
        # 松散布局
        spread = {
            f"d{i}": {"x": float(i * 800.0), "y": float(i * 800.0), "rotation": 0}
            for i in range(8)
        }
        cfg = TimingWirelengthRewardConfig(
            w_area=0.0, w_wirelength=1.0, w_congestion=0.0, w_timing=0.0
        )
        r = TimingWirelengthReward(cfg)
        r_compact = r.compute(compact, circuit)["reward"]
        r_spread = r.compute(spread, circuit)["reward"]
        # 紧凑线长更短 → 奖励更高（更接近 0）
        assert r_compact > r_spread


# ===========================================================================
# R369 — 预训练模型：布局经验迁移（验收级）
# ===========================================================================


class TestR369PretrainTransferAcceptance:
    """R369 验收级：预训练→迁移→微调完整闭环。

    验收指标（对标 AlphaChip Mirhoseini 2024 pre-trained checkpoint + EWC）：
    - Fisher 矩阵估计正确（梯度平方均值）
    - 维度迁移（大→小截断、小→大平铺）
    - EWC 微调减少参数漂移（防灾难性遗忘）
    - 完整 pretrain→transfer→fine_tune 闭环
    """

    def test_r369_pretrain_transfer_finetune_pipeline(self):
        """R369 验收：完整 pretrain→transfer→fine_tune 闭环。"""
        tm = PolicyTransferManager()
        # 1) 预训练：大电路参数 + Fisher
        theta_pretrain = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        grads = np.array([[1.0, 0.5, 0.3, 0.2, 0.1],
                          [0.8, 0.4, 0.2, 0.1, 0.05]])
        fisher = tm.compute_fisher(theta_pretrain, grads)
        tm.store_pretrained(theta_pretrain, fisher)
        # 2) 迁移：目标小电路（3 维）
        theta_target = np.zeros(3)
        transferred = tm.transfer_weights(theta_target)
        assert transferred.shape == (3,)
        # 大→小截断前 3
        assert np.allclose(transferred, [1.0, 2.0, 3.0])
        # 3) 微调：带 EWC 正则
        task_grad = np.array([0.5, -0.5, 0.3])
        new_theta, metrics = tm.fine_tune(theta_target, task_grad)
        assert new_theta.shape == (3,)
        assert "ewc_penalty" in metrics
        assert "grad_norm" in metrics

    def test_r369_fisher_correctness(self):
        """R369 验收：Fisher 对角 = 梯度样本平方均值。"""
        tm = PolicyTransferManager()
        theta = np.zeros(4)
        grads = np.array([[2.0, 0.0, 1.0, 0.0],
                          [4.0, 0.0, 1.0, 0.0]])
        fisher = tm.compute_fisher(theta, grads)
        # mean of squares: [(4+16)/2, 0, (1+1)/2, 0] = [10, 0, 1, 0]
        assert np.allclose(fisher, [10.0, 0.0, 1.0, 0.0])

    def test_r369_ewc_reduces_drift(self):
        """R369 验收：EWC 正则使参数漂移小于无正则（防遗忘）。"""
        theta_star = np.zeros(6)
        fisher = np.ones(6)
        tgt = np.ones(6)
        task_grad = np.ones(6) * 0.5
        # 无 EWC
        tm_no = PolicyTransferManager(PolicyTransferConfig(
            ewc_lambda=0.0, fine_tune_lr=0.05
        ))
        tm_no.store_pretrained(theta_star, fisher)
        new_no, _ = tm_no.fine_tune(tgt, task_grad)
        drift_no = float(np.linalg.norm(new_no - theta_star))
        # 有 EWC
        tm_ewc = PolicyTransferManager(PolicyTransferConfig(
            ewc_lambda=20.0, fine_tune_lr=0.05
        ))
        tm_ewc.store_pretrained(theta_star, fisher)
        new_ewc, _ = tm_ewc.fine_tune(tgt, task_grad)
        drift_ewc = float(np.linalg.norm(new_ewc - theta_star))
        assert drift_ewc < drift_no

    def test_r369_no_pretrained_raise(self):
        """R03：未存储预训练参数时 ewc_penalty/fine_tune 必须 raise。"""
        tm = PolicyTransferManager()
        with pytest.raises(ValueError, match="未存储预训练"):
            tm.ewc_penalty(np.zeros(3))
        with pytest.raises(ValueError, match="未存储预训练"):
            tm.fine_tune(np.zeros(3), np.zeros(3))


# ===========================================================================
# R370 — 混合布局：RL + 解析法混合策略（验收级）
# ===========================================================================


class TestR370HybridPlacementAcceptance:
    """R370 验收级：解析法 quadratic + RL 交换微调混合布局。

    验收指标（对标 DREAMPlace 解析法 + AlphaChip RL 精修）：
    - 解析法锚点收敛
    - RL 精修后奖励不劣于初始
    - 端到端混合布局所有器件放置合法
    """

    def test_r370_analytical_anchor_convergence(self):
        """R370 验收：解析法固定 I/O 锚点收敛到锚点位置。"""
        circuit = _make_circuit(10, seed=8)
        circuit["fixed_ios"] = {
            "d0": (0.0, 0.0), "d9": (900.0, 900.0)
        }
        placer = AnalyticalRLHybridPlacer(
            AnalyticalHybridConfig(grid_size=(16, 16), anchor_weight=1e6)
        )
        placement = placer.analytical_place(circuit)
        assert placement["d0"]["x"] < 1.0
        assert placement["d0"]["y"] < 1.0
        assert abs(placement["d9"]["x"] - 900.0) < 1.0
        assert abs(placement["d9"]["y"] - 900.0) < 1.0

    def test_r370_rl_refine_reward_nondecreasing(self):
        """R370 验收：RL 交换微调后奖励不劣于初始（混合策略价值）。"""
        circuit = _make_circuit(12, seed=9, target_delay_ps=100.0)
        placer = AnalyticalRLHybridPlacer(
            AnalyticalHybridConfig(grid_size=(16, 16), rl_refine_iters=30)
        )
        initial = placer.analytical_place(circuit)
        reward_fn = TimingWirelengthReward()
        r_before = reward_fn.compute(initial, circuit)["reward"]
        refined = placer.rl_refine(initial, circuit, reward_fn)
        r_after = reward_fn.compute(refined, circuit)["reward"]
        assert r_after >= r_before - 1e-9

    def test_r370_hybrid_place_end_to_end_complete(self):
        """R370 验收：端到端混合布局所有器件放置且位置合法。"""
        circuit = _make_circuit(10, seed=10)
        placer = AnalyticalRLHybridPlacer(
            AnalyticalHybridConfig(grid_size=(16, 16), rl_refine_iters=10)
        )
        placement = placer.place(circuit)
        assert len(placement) == 10
        max_xy = 15 * 100.0 + 1e-6
        for p in placement.values():
            assert np.isfinite(p["x"]) and np.isfinite(p["y"])
            assert 0.0 <= p["x"] <= max_xy
            assert 0.0 <= p["y"] <= max_xy

    def test_r370_empty_circuit_raise(self):
        """R03：空电路解析布局必须 raise（禁止 fall-back）。"""
        placer = AnalyticalRLHybridPlacer()
        with pytest.raises(ValueError, match="器件数"):
            placer.analytical_place({"devices": [], "nets": []})


# ===========================================================================
# R391 — 端到端 RL 训练流水线
# ===========================================================================


class TestR391RLPipeline:
    """R391 RLPipeline 端到端训练流水线测试。"""

    def test_r391_pipeline_run_complete(self):
        """R391 验收：流水线运行返回完整 PipelineResult。"""
        pipeline = RLPipeline(PipelineConfig(n_iterations=5, eval_every=1))

        def train_step(it, rng):
            return {"reward": float(1.0 - it * 0.1), "loss": float(0.5 - it * 0.05)}

        def eval_fn(rng):
            return float(rng.normal(0.8, 0.05))

        result = pipeline.run("PPO", train_step, eval_fn)
        assert isinstance(result, PipelineResult)
        assert result.algorithm_name == "PPO"
        assert len(result.iterations) == 5
        assert len(result.rewards) == 5
        assert len(result.losses) == 5
        assert len(result.eval_values) == 5
        assert result.elapsed_s > 0.0
        assert "reward_mean" in result.final_metrics
        assert "reward_final" in result.final_metrics

    def test_r391_pipeline_non_callable_train_step_raise(self):
        """R03：train_step_fn 不可调用必须 raise。"""
        pipeline = RLPipeline()
        with pytest.raises(ValueError, match="须可调用"):
            pipeline.run("PPO", "not_callable")

    def test_r391_pipeline_missing_reward_key_raise(self):
        """R03：train_step_fn 返回缺 reward/loss 必须 raise。"""
        pipeline = RLPipeline(PipelineConfig(n_iterations=2))

        def bad_step(it, rng):
            return {"reward": 1.0}  # 缺 loss

        with pytest.raises(ValueError, match="须返回"):
            pipeline.run("PPO", bad_step)


# ===========================================================================
# R392 — 跨模块集成
# ===========================================================================


class TestR392CrossModuleIntegration:
    """R392 CrossModuleIntegration 跨模块集成测试。"""

    def test_r392_ppo_plus_curiosity(self):
        """R392 验收：PPO + Curiosity 联合训练返回三路奖励。"""
        result = CrossModuleIntegration.ppo_plus_curiosity(n_steps=10, seed=42)
        assert "rewards_extrinsic" in result
        assert "rewards_intrinsic" in result
        assert "rewards_total" in result
        assert len(result["rewards_total"]) == 10
        # total = ext + int
        for i in range(10):
            expected = result["rewards_extrinsic"][i] + result["rewards_intrinsic"][i]
            assert abs(result["rewards_total"][i] - expected) < 1e-9

    def test_r392_bc_plus_cql(self):
        """R392 验收：BC + CQL 联合训练返回两路 loss。"""
        result = CrossModuleIntegration.bc_plus_cql(n_steps=8, seed=42)
        assert "bc_losses" in result
        assert "cql_losses" in result
        assert len(result["bc_losses"]) == 8
        assert len(result["cql_losses"]) == 8

    def test_r392_validate_module_imports(self):
        """R392 验收：所有 RL 模块可正常导入。"""
        results = CrossModuleIntegration.validate_module_imports()
        assert isinstance(results, dict)
        assert len(results) >= 7
        for mod_name, ok in results.items():
            assert ok is True, f"模块 {mod_name} 导入失败"


# ===========================================================================
# R393 — 算法对比器（Wilcoxon + bootstrap CI）
# ===========================================================================


class TestR393AlgorithmComparator:
    """R393 AlgorithmComparator 算法对比器测试。"""

    def test_r393_compare_multiple_algorithms(self):
        """R393 验收：对比多算法返回 mean/std/ci/n_runs。"""
        comp = AlgorithmComparator(ComparisonConfig(n_runs=5, n_iterations=3, seed=42))

        def algo_a(it, rng):
            return {"reward": float(rng.normal(1.0, 0.1))}

        def algo_b(it, rng):
            return {"reward": float(rng.normal(0.5, 0.1))}

        results = comp.compare({"A": algo_a, "B": algo_b})
        assert "A" in results and "B" in results
        for name, r in results.items():
            assert r["n_runs"] == 5
            assert "mean" in r and "std" in r
            assert "ci_lo" in r and "ci_hi" in r
            assert r["ci_lo"] <= r["mean"] <= r["ci_hi"]

    def test_r393_statistical_test_wilcoxon(self):
        """R393 验收：Wilcoxon 检验返回 W/p_value/significant。"""
        comp = AlgorithmComparator(ComparisonConfig(n_runs=8, n_iterations=2, seed=42))

        def algo_a(it, rng):
            return {"reward": float(rng.normal(1.0, 0.05))}

        def algo_b(it, rng):
            return {"reward": float(rng.normal(0.3, 0.05))}

        results = comp.compare({"A": algo_a, "B": algo_b})
        stats = comp.statistical_test(results, baseline="B")
        assert "A" in stats
        assert "W_statistic" in stats["A"]
        assert "p_value" in stats["A"]
        assert "significant" in stats["A"]
        assert "better_than_baseline" in stats["A"]
        # A 均值高于 B → better_than_baseline = 1.0
        assert stats["A"]["better_than_baseline"] == 1.0

    def test_r393_compare_empty_algorithms_raise(self):
        """R03：空算法字典必须 raise。"""
        comp = AlgorithmComparator()
        with pytest.raises(ValueError, match="不能为空"):
            comp.compare({})

    def test_r393_statistical_test_baseline_missing_raise(self):
        """R03：基线不在结果中必须 raise。"""
        comp = AlgorithmComparator()
        with pytest.raises(ValueError, match="基线"):
            comp.statistical_test({}, baseline="Nonexistent")


# ===========================================================================
# R394 — 回归测试套件
# ===========================================================================


class TestR394RegressionTestSuite:
    """R394 RegressionTestSuite 回归测试套件测试。"""

    def test_r394_register_and_run_all_pass(self):
        """R394 验收：注册通过的测试，run_all 全部 pass。"""
        suite = RegressionTestSuite()
        suite.register("test_a", "测试A", lambda: None)
        suite.register("test_b", "测试B", lambda: None)
        assert suite.n_tests == 2
        results = suite.run_all()
        assert results["test_a"]["pass"] is True
        assert results["test_b"]["pass"] is True
        assert results["test_a"]["error"] is None

    def test_r394_run_all_catches_failure(self):
        """R394 验收：失败的测试被捕获，pass=False 且记录 error。"""
        suite = RegressionTestSuite()

        def failing():
            raise AssertionError("故意失败")

        suite.register("fail_test", "失败测试", failing)
        results = suite.run_all()
        assert results["fail_test"]["pass"] is False
        assert "故意失败" in results["fail_test"]["error"]

    def test_r394_register_empty_name_raise(self):
        """R03：空 name 注册必须 raise。"""
        suite = RegressionTestSuite()
        with pytest.raises(ValueError, match="须有效"):
            suite.register("", "描述", lambda: None)

    def test_r394_register_non_callable_raise(self):
        """R03：非 callable test_fn 注册必须 raise。"""
        suite = RegressionTestSuite()
        with pytest.raises(ValueError, match="须有效"):
            suite.register("test", "描述", "not_callable")


# ===========================================================================
# R395 — API 文档自动生成
# ===========================================================================


class TestR395DocumentationGenerator:
    """R395 DocumentationGenerator API 文档生成测试。"""

    def test_r395_generate_module_doc_content(self):
        """R395 验收：生成模块文档含模块名、docstring、类、函数。"""
        doc = DocumentationGenerator.generate_module_doc("polaris.rl.rl_integration")
        assert isinstance(doc, str)
        assert "polaris.rl.rl_integration" in doc
        # 含类
        assert "RLPipeline" in doc
        assert "AlgorithmComparator" in doc
        # 含函数或方法
        assert "run" in doc or "compare" in doc

    def test_r395_write_doc_creates_file(self, tmp_path):
        """R395 验收：write_doc 写入文件且内容非空。"""
        out = DocumentationGenerator.write_doc(
            "polaris.rl.rl_integration", tmp_path / "rl_integration.md"
        )
        assert out.exists()
        content = out.read_text(encoding="utf-8")
        assert len(content) > 100
        assert "RLPipeline" in content


# ===========================================================================
# R396 — 教程示例自动生成
# ===========================================================================


class TestR396TutorialGenerator:
    """R396 TutorialGenerator 教程生成测试。"""

    def test_r396_ppo_tutorial_content(self):
        """R396 验收：PPO 教程含关键 import 和用法。"""
        tutorial = TutorialGenerator.ppo_tutorial()
        assert isinstance(tutorial, str)
        assert "PPOAdvantageOptimizer" in tutorial
        assert "compute_gae" in tutorial
        assert "LargeScalePlacementEnv" in tutorial

    def test_r396_cql_tutorial_content(self):
        """R396 验收：CQL 教程含离线 RL 关键组件。"""
        tutorial = TutorialGenerator.cql_tutorial()
        assert "ConservativeQLearning" in tutorial
        assert "OfflineDataset" in tutorial
        assert "OfflineTrainer" in tutorial

    def test_r396_write_all_tutorials(self, tmp_path):
        """R396 验收：write_all_tutorials 生成 3 个教程文件。"""
        paths = TutorialGenerator.write_all_tutorials(tmp_path / "tutorials")
        assert len(paths) == 3
        for p in paths:
            assert p.exists()
            assert p.stat().st_size > 50
        names = {p.name for p in paths}
        assert "ppo_tutorial.py" in names
        assert "cql_tutorial.py" in names
        assert "benchmark_tutorial.py" in names


# ===========================================================================
# R397-R400 — 算法对比报告生成（综合）
# ===========================================================================


class TestR397ReportGenerator:
    """R397-R400 AlgorithmReportGenerator 综合报告生成测试。"""

    def test_r397_generate_full_report(self, tmp_path):
        """R397 验收：生成 JSON + Markdown + 教程完整报告。"""
        comp = AlgorithmComparator(ComparisonConfig(n_runs=4, n_iterations=2, seed=42))

        def algo_a(it, rng):
            return {"reward": float(rng.normal(1.0, 0.1))}

        def algo_b(it, rng):
            return {"reward": float(rng.normal(0.5, 0.1))}

        results = comp.compare({"A": algo_a, "B": algo_b})
        stats = comp.statistical_test(results, baseline="B")
        outputs = AlgorithmReportGenerator.generate(
            results, stats,
            ReportConfig(output_dir=str(tmp_path), generate_json=True,
                         generate_markdown=True, generate_tutorial=True)
        )
        assert "json" in outputs
        assert "markdown" in outputs
        assert "tutorials" in outputs
        assert tmp_path.joinpath("comparison_report.json").exists()
        assert tmp_path.joinpath("comparison_report.md").exists()
        # JSON 含对比和统计
        import json
        data = json.loads(
            tmp_path.joinpath("comparison_report.json").read_text(encoding="utf-8")
        )
        assert "comparison" in data
        assert "A" in data["comparison"]
        assert "statistical_tests" in data
