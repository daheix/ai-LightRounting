"""R401-R450 RL 布局布线进阶功能单元测试。

覆盖 ``src/polaris/rl/rl_advanced.py`` 五个进阶模块：
- R401 ``LargeScaleGraphPartitioner`` / ``PartitionedParallelPlacer``：
  10000+ 节点多级图分割 + 分区并行布局
- R402 ``AdaptivePPOOptimizer``：KL 自适应学习率 + 自适应 clip + 目标熵
- R403 ``TimingWirelengthReward``：面积+线长+拥塞+时序四目标奖励
- R404 ``PolicyTransferManager``：预训练迁移 + EWC 防遗忘 + 微调
- R405 ``AnalyticalRLHybridPlacer``：解析法 quadratic + RL 交换微调

学术依据（R02 学术诚信，≥5 个文献 URL）：
1. Mirhoseini et al., Nature 2021, AlphaChip
   https://www.nature.com/articles/s41586-021-03544-w
2. Schulman et al., 2017, PPO https://arxiv.org/abs/1707.06347
3. Engstrom et al., 2020, PPO Implementation Matters
   https://arxiv.org/abs/2005.12729
4. Zhang et al., 2023, Adaptive-PPO https://arxiv.org/abs/2312.07624
5. Lin et al., TCAD 2020, DREAMPlace https://arxiv.org/abs/2004.10746
6. Liao et al., DATE 2022, DREAMPlace 4.0 timing-driven
   https://dl.acm.org/doi/10.5555/3539845.3540064
7. Kirkpatrick et al., PNAS 2017, EWC
   https://www.pnas.org/doi/full/10.1073/pnas.1611835114
8. Karypis & Kumar, 1998, METIS https://www.cs.umn.edu/~karypis/metis/
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


# ---------------------------------------------------------------------------
# 测试数据
# ---------------------------------------------------------------------------


def _make_circuit(n: int = 12, seed: int = 1, target_delay_ps: float = 5.0) -> dict:
    """构造链式 + 随机连接测试电路。"""
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
    # 随机远距离连接增加图复杂度
    for _ in range(max(n // 2, 1)):
        a, b = int(rng.integers(0, n)), int(rng.integers(0, n))
        if a != b:
            nets.append({"src": [f"d{a}", "p1"], "dst": [f"d{b}", "p0"]})
    return {"devices": devs, "nets": nets}


# ===========================================================================
# R401 — 大规模电路：图分割 + 分区并行布局
# ===========================================================================


class TestR401LargeScalePartition:
    """R401 大规模图分割与分区并行布局测试。"""

    def test_r401_graph_partition_small_balance(self):
        """小规模图分割：3 分区，标签全覆盖且平衡。"""
        circuit = _make_circuit(12, seed=1)
        part = LargeScaleGraphPartitioner(
            GraphPartitionConfig(n_partitions=3, seed=42)
        )
        labels = part.partition(circuit)
        assert labels.shape == (12,)
        assert len(set(labels.tolist())) == 3
        counts = np.bincount(labels, minlength=3)
        # 平衡容忍 ±25%：12/3=4，[3,5] 区间
        assert counts.min() >= 3
        assert counts.max() <= 5

    def test_r401_partition_parallel_place_complete(self):
        """分区并行布局：所有器件放置且位置在画布内。"""
        circuit = _make_circuit(16, seed=2)
        part = LargeScaleGraphPartitioner(
            GraphPartitionConfig(n_partitions=4, seed=42)
        )
        placer = PartitionedParallelPlacer(
            part, PartitionedPlacementConfig(grid_size=(8, 8))
        )
        placement = placer.place(circuit)
        assert len(placement) == 16
        for dev_id, p in placement.items():
            assert 0.0 <= p["x"] <= 7 * 100.0 + 1e-6
            assert 0.0 <= p["y"] <= 7 * 100.0 + 1e-6
            assert p["rotation"] == 0

    def test_r401_large_scale_10000_nodes(self):
        """R401 硬指标：10000+ 节点大规模图分割可完成且平衡。"""
        n = 10000
        rng = np.random.default_rng(7)
        devs = [
            {"id": f"d{i}", "type": "mzi", "width": 50.0, "height": 30.0,
             "ports": ["p0", "p1"]}
            for i in range(n)
        ]
        nets = [{"src": [f"d{i}", "p1"], "dst": [f"d{i+1}", "p0"]}
                 for i in range(n - 1)]
        for _ in range(n // 2):
            a, b = int(rng.integers(0, n)), int(rng.integers(0, n))
            if a != b:
                nets.append({"src": [f"d{a}", "p1"], "dst": [f"d{b}", "p0"]})
        circuit = {"devices": devs, "nets": nets}
        part = LargeScaleGraphPartitioner(
            GraphPartitionConfig(n_partitions=8, coarse_threshold=128,
                                 fm_max_nodes=2000, seed=42)
        )
        labels = part.partition(circuit)
        assert labels.shape == (n,)
        counts = np.bincount(labels, minlength=8)
        target = n / 8
        # ±25% 平衡容忍
        assert counts.max() <= target * 1.25 + 1
        assert counts.min() >= target * 0.75 - 1

    def test_r401_invalid_input_raise(self):
        """R03：非法输入（分区数超器件数 / 缺字段）必须 raise。"""
        part = LargeScaleGraphPartitioner(
            GraphPartitionConfig(n_partitions=5, seed=42)
        )
        # 分区数 > 器件数
        with pytest.raises(ValueError, match="分区数"):
            part.partition(_make_circuit(3, seed=1))
        # 缺字段
        with pytest.raises(ValueError, match="devices"):
            part.partition({"nets": []})
        # n_partitions < 1
        bad = LargeScaleGraphPartitioner(GraphPartitionConfig(n_partitions=0))
        with pytest.raises(ValueError, match="n_partitions"):
            bad.partition(_make_circuit(10, seed=1))

    def test_r401_build_adjacency_symmetric(self):
        """邻接矩阵对称且对角为 0。"""
        circuit = _make_circuit(8, seed=3)
        adj = build_adjacency(circuit)
        assert sparse.issparse(adj)
        assert adj.shape == (8, 8)
        dense = adj.toarray()
        assert np.allclose(dense, dense.T)
        assert np.all(np.diag(dense) == 0.0)


# ===========================================================================
# R402 — PPO 超参数自适应
# ===========================================================================


class TestR402AdaptivePPO:
    """R402 PPO 自适应学习率/clip/熵测试。"""

    def test_r402_approx_kl_zero_when_identical(self):
        """KL 散度：新旧策略相同时 KL≈0。"""
        ppo = AdaptivePPOOptimizer()
        lp = np.log(np.array([0.25, 0.5, 0.25]))
        kl = ppo.approx_kl(lp, lp)
        assert abs(kl) < 1e-9

    def test_r402_adapt_lr_clip_high_kl(self):
        """KL > target_kl 时学习率下降、clip 收紧。"""
        cfg = AdaptivePPOConfig(target_kl=0.02, lr_adapt_factor=2.0)
        ppo = AdaptivePPOOptimizer(cfg)
        lr0 = ppo.current_lr
        clip0 = ppo.current_clip
        # 构造大 KL（新策略显著偏离旧策略）
        new_lp = np.log(np.array([0.5, 0.5]))
        old_lp = np.log(np.array([0.3, 0.7]))
        kl = ppo.approx_kl(new_lp, old_lp)
        assert kl > cfg.target_kl
        lr1 = ppo.adapt_learning_rate(kl)
        clip1 = ppo.adapt_clip_range(kl)
        assert lr1 < lr0
        assert clip1 < clip0

    def test_r402_adapt_lr_low_kl_increase(self):
        """KL < target_kl/2 时学习率上升、clip 放宽。"""
        cfg = AdaptivePPOConfig(target_kl=0.02, lr_adapt_factor=2.0)
        ppo = AdaptivePPOOptimizer(cfg)
        lr0 = ppo.current_lr
        clip0 = ppo.current_clip
        # 极小 KL
        lr1 = ppo.adapt_learning_rate(1e-6)
        clip1 = ppo.adapt_clip_range(1e-6)
        assert lr1 > lr0
        assert clip1 > clip0

    def test_r402_target_entropy_adapt(self):
        """熵低于目标时 ent_coef 增大（鼓励探索）。"""
        cfg = AdaptivePPOConfig(target_entropy=0.5, ent_coef=0.01, ent_coef_max=0.05)
        ppo = AdaptivePPOOptimizer(cfg)
        ec0 = ppo.current_ent_coef
        ec1 = ppo.adapt_entropy_coef(0.1)  # 远低于目标 0.5
        assert ec1 > ec0

    def test_r402_step_end_to_end_metrics(self):
        """端到端 step 返回完整指标 dict。"""
        ppo = AdaptivePPOOptimizer()
        new_lp = np.log(np.array([0.3, 0.4, 0.5, 0.2]))
        old_lp = np.log(np.array([0.25, 0.45, 0.48, 0.22]))
        adv = np.array([1.0, -0.5, 0.3, 0.8])
        ent = np.array([0.4, 0.5, 0.3, 0.6])
        metrics = ppo.step(new_lp, old_lp, adv, ent)
        for key in ("policy_loss", "entropy", "kl", "clip_frac",
                    "clip_eps", "ent_coef", "lr"):
            assert key in metrics
        assert 0.0 <= metrics["clip_frac"] <= 1.0
        assert metrics["lr"] > 0.0

    def test_r402_shape_mismatch_raise(self):
        """R03：形状不一致必须 raise。"""
        ppo = AdaptivePPOOptimizer()
        with pytest.raises(ValueError, match="形状"):
            ppo.compute_loss(
                np.array([0.1, 0.2]), np.array([0.1]), np.array([1.0]), 0.3
            )


# ===========================================================================
# R403 — 多目标奖励：面积 + 线长 + 拥塞 + 时序
# ===========================================================================


class TestR403TimingWirelengthReward:
    """R403 多目标奖励测试。"""

    def test_r403_compute_components_nonneg(self):
        """各分量非负且奖励为负（惩罚）。"""
        circuit = _make_circuit(8, seed=4, target_delay_ps=0.001)
        placement = {
            f"d{i}": {"x": float(i * 100.0), "y": 0.0, "rotation": 0}
            for i in range(8)
        }
        r = TimingWirelengthReward()
        res = r.compute(placement, circuit)
        assert res["area"] > 0.0
        assert res["wirelength"] >= 0.0
        assert res["congestion"] >= 0.0
        assert res["timing_tns_ps"] >= 0.0
        assert res["reward"] <= 0.0

    def test_r403_wirelength_hpwl_correctness(self):
        """HPWL 线长：链式布局线长 = (n-1)*step。"""
        circuit = _make_circuit(5, seed=5)
        placement = {
            f"d{i}": {"x": float(i * 200.0), "y": 100.0, "rotation": 0}
            for i in range(5)
        }
        r = TimingWirelengthReward()
        wl = r.compute_wirelength(placement, circuit)
        # 每条 net HPWL = |dx| + |dy| = 200 + 0 = 200，端口映射到器件中心
        # 链式 4 条相邻 net（随机远距离 net 可能贡献更多）
        assert wl >= 4 * 200.0

    def test_r403_timing_tns_negative_slack(self):
        """时序 TNS：目标时延极小时全部 net 负 slack，TNS > 0。"""
        circuit = _make_circuit(6, seed=6, target_delay_ps=0.001)
        placement = {
            f"d{i}": {"x": float(i * 500.0), "y": 0.0, "rotation": 0}
            for i in range(6)
        }
        r = TimingWirelengthReward()
        tns = r.compute_timing_tns(placement, circuit)
        # 长 net 群时延远大于 0.001 ps，必有负 slack
        assert tns > 0.0

    def test_r403_reward_weighted_scaling(self):
        """加权奖励：权重为 0 的项不贡献奖励。"""
        circuit = _make_circuit(6, seed=7)
        placement = {
            f"d{i}": {"x": float(i * 100.0), "y": 0.0, "rotation": 0}
            for i in range(6)
        }
        # 全部权重为 0 → reward = 0
        cfg0 = TimingWirelengthRewardConfig(
            w_area=0.0, w_wirelength=0.0, w_congestion=0.0, w_timing=0.0
        )
        r0 = TimingWirelengthReward(cfg0)
        assert abs(r0.compute(placement, circuit)["reward"]) < 1e-9
        # 仅线长权重 > 0 → reward = -w_wl * wl_norm
        cfg1 = TimingWirelengthRewardConfig(
            w_area=0.0, w_wirelength=2.0, w_congestion=0.0, w_timing=0.0
        )
        r1 = TimingWirelengthReward(cfg1)
        res1 = r1.compute(placement, circuit)
        expected = -2.0 * res1["wirelength"] / 3200.0
        assert abs(res1["reward"] - expected) < 1e-9


# ===========================================================================
# R404 — 预训练模型迁移 + EWC
# ===========================================================================


class TestR404PolicyTransfer:
    """R404 预训练迁移 + EWC 防遗忘测试。"""

    def test_r404_fisher_estimation(self):
        """Fisher 矩阵对角 = 梯度样本平方均值。"""
        tm = PolicyTransferManager()
        theta = np.zeros(5)
        grads = np.array([[1.0, 2.0, 0.0, 0.0, 0.0],
                          [3.0, 0.0, 0.0, 0.0, 0.0]])
        fisher = tm.compute_fisher(theta, grads)
        # mean of squares: [(1+9)/2, (4+0)/2, 0, 0, 0] = [5, 2, 0, 0, 0]
        assert np.allclose(fisher, [5.0, 2.0, 0.0, 0.0, 0.0])
        assert np.all(fisher >= 0.0)

    def test_r404_transfer_weights_dim_adapt(self):
        """维度适配：大→小截断，小→大平铺。"""
        tm = PolicyTransferManager()
        theta_big = np.arange(10.0)  # [0,1,...,9]
        fisher_big = np.ones(10)
        tm.store_pretrained(theta_big, fisher_big)
        # 大→小：截断前 5
        tgt_small = np.zeros(5)
        trans_small = tm.transfer_weights(tgt_small)
        assert trans_small.shape == (5,)
        assert np.allclose(trans_small, [0, 1, 2, 3, 4])
        # 小→大：平铺（此处预训练已存为 10 维，迁移到 15 维平铺）
        tgt_big = np.zeros(15)
        trans_big = tm.transfer_weights(tgt_big)
        assert trans_big.shape == (15,)
        assert np.allclose(trans_big[:10], theta_big)
        assert np.allclose(trans_big[10:15], theta_big[:5])

    def test_r404_ewc_penalty_zero_at_pretrained(self):
        """EWC 惩罚：参数等于预训练值时 penalty=0。"""
        tm = PolicyTransferManager()
        theta = np.array([1.0, 2.0, 3.0])
        fisher = np.array([0.5, 1.0, 2.0])
        tm.store_pretrained(theta, fisher)
        # 参数 = 预训练值 → penalty = 0
        assert abs(tm.ewc_penalty(theta)) < 1e-9
        # 参数偏离 → penalty > 0
        assert tm.ewc_penalty(theta + 1.0) > 0.0

    def test_r404_fine_tune_reduces_drift(self):
        """EWC 微调：带正则时参数漂移小于无正则（保守）。"""
        tm = PolicyTransferManager(PolicyTransferConfig(
            ewc_lambda=100.0, fine_tune_lr=0.1
        ))
        theta_star = np.zeros(6)
        fisher = np.ones(6)
        tm.store_pretrained(theta_star, fisher)
        tgt = np.ones(6)
        task_grad = np.ones(6) * 0.5  # 推动远离预训练值
        new_theta, metrics = tm.fine_tune(tgt, task_grad)
        # EWC 阻力使参数趋向预训练值（漂移受限）
        assert metrics["ewc_penalty"] >= 0.0
        assert metrics["grad_norm"] > 0.0
        # 无 EWC 时纯梯度下降：new = 1 - 0.1*0.5 = 0.95
        # 带 EWC：额外 + 0.1*100*1*(1-0) = +10 → new = 1 - 0.05 - 1.0 = 负
        # 漂移应小于纯梯度下降的 0.95
        assert abs(new_theta[0] - theta_star[0]) < 0.95

    def test_r404_no_pretrained_raise(self):
        """R03：未存储预训练参数时 ewc_penalty / fine_tune 必须 raise。"""
        tm = PolicyTransferManager()
        with pytest.raises(ValueError, match="未存储预训练"):
            tm.ewc_penalty(np.zeros(3))
        with pytest.raises(ValueError, match="未存储预训练"):
            tm.fine_tune(np.zeros(3), np.zeros(3))

    def test_r404_fisher_negative_raise(self):
        """R03：Fisher 含负值必须 raise。"""
        tm = PolicyTransferManager()
        with pytest.raises(ValueError, match="Fisher"):
            tm.store_pretrained(np.zeros(3), np.array([-1.0, 0.0, 1.0]))


# ===========================================================================
# R405 — 混合布局：解析法 quadratic + RL 交换微调
# ===========================================================================


class TestR405AnalyticalRLHybrid:
    """R405 解析法 + RL 混合布局测试。"""

    def test_r405_analytical_place_anchor_convergence(self):
        """解析法：固定 I/O 锚点收敛到锚点位置。"""
        circuit = _make_circuit(8, seed=8)
        circuit["fixed_ios"] = {
            "d0": (0.0, 0.0), "d7": (700.0, 700.0)
        }
        placer = AnalyticalRLHybridPlacer(
            AnalyticalHybridConfig(grid_size=(8, 8), anchor_weight=1e6)
        )
        placement = placer.analytical_place(circuit)
        # 锚点器件应接近锚点位置
        assert placement["d0"]["x"] < 1.0
        assert placement["d0"]["y"] < 1.0
        assert abs(placement["d7"]["x"] - 700.0) < 1.0
        assert abs(placement["d7"]["y"] - 700.0) < 1.0

    def test_r405_rl_refine_reward_nondecreasing(self):
        """RL 交换微调：精修后奖励不劣于初始。"""
        circuit = _make_circuit(10, seed=9, target_delay_ps=100.0)
        placer = AnalyticalRLHybridPlacer(
            AnalyticalHybridConfig(grid_size=(16, 16), rl_refine_iters=30)
        )
        initial = placer.analytical_place(circuit)
        reward_fn = TimingWirelengthReward()
        r_before = reward_fn.compute(initial, circuit)["reward"]
        refined = placer.rl_refine(initial, circuit, reward_fn)
        r_after = reward_fn.compute(refined, circuit)["reward"]
        assert r_after >= r_before - 1e-9

    def test_r405_hybrid_place_end_to_end(self):
        """端到端混合布局：所有器件放置且位置有限。"""
        circuit = _make_circuit(8, seed=10)
        placer = AnalyticalRLHybridPlacer(
            AnalyticalHybridConfig(grid_size=(8, 8), rl_refine_iters=10)
        )
        placement = placer.place(circuit)
        assert len(placement) == 8
        for p in placement.values():
            assert np.isfinite(p["x"]) and np.isfinite(p["y"])
            assert 0.0 <= p["x"] <= 7 * 100.0 + 1e-6
            assert 0.0 <= p["y"] <= 7 * 100.0 + 1e-6

    def test_r405_empty_circuit_raise(self):
        """R03：空电路必须 raise。"""
        placer = AnalyticalRLHybridPlacer()
        with pytest.raises(ValueError, match="器件数"):
            placer.analytical_place({"devices": [], "nets": []})

    def test_r405_qp_matrix_laplacian(self):
        """QP 矩阵为拉普拉斯结构（对角 ≥ 0，非对角 ≤ 0）。"""
        circuit = _make_circuit(6, seed=11)
        circuit["fixed_ios"] = {"d0": (0.0, 0.0)}
        placer = AnalyticalRLHybridPlacer(
            AnalyticalHybridConfig(anchor_weight=1e3)
        )
        Q, idx2id, id2idx = placer._build_qp_matrix(circuit, circuit["fixed_ios"])
        dense = Q.toarray()
        # 对角非负（含锚点权重）
        assert np.all(np.diag(dense) >= 0.0)
        # 非对角元素 ≤ 0（负连接权重）
        off_diag = dense - np.diag(np.diag(dense))
        assert np.all(off_diag <= 1e-9)
        # 锚点器件对角含锚点权重
        assert dense[id2idx["d0"], id2idx["d0"]] >= 1e3
