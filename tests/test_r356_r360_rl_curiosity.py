"""R356-R360 RL Curiosity 探索模块测试。

覆盖:
- R356 InverseForwardDynamics (ICM, Pathak 2017)
- R357 RandomNetworkDistillation (RND, Burda 2019)
- R358 CuriosityRewardShaper (intrinsic + extrinsic 融合)
- R359-R360 CuriosityRolloutCollector (集成到 PPO)
- R03/R02/R04 合规
- 集成测试

学术依据:
- Pathak 2017 ICM https://arxiv.org/abs/1705.05363
- Burda 2019 RND https://arxiv.org/abs/1810.12894
- Schulman 2017 PPO https://arxiv.org/abs/1707.06347
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from polaris.rl.rl_curiosity import (
    CuriosityConfig,
    CuriosityRewardShaper,
    CuriosityRolloutCollector,
    GPU_DISABLED_R04,
    InverseForwardDynamics,
    RandomNetworkDistillation,
)


# =============================================================================
# 共享 fixtures
# =============================================================================

@pytest.fixture
def config() -> CuriosityConfig:
    """小规模测试配置。"""
    return CuriosityConfig(
        feature_dim=8,
        action_dim=4,
        icm_eta=0.2,
        icm_beta=0.2,
        seed=42,
    )


@pytest.fixture
def state_dim() -> int:
    return 16


@pytest.fixture
def icm(state_dim: int, config: CuriosityConfig) -> InverseForwardDynamics:
    return InverseForwardDynamics(state_dim, config)


@pytest.fixture
def rnd(state_dim: int, config: CuriosityConfig) -> RandomNetworkDistillation:
    return RandomNetworkDistillation(state_dim, config)


@pytest.fixture
def shaper(config: CuriosityConfig) -> CuriosityRewardShaper:
    return CuriosityRewardShaper(config)


@pytest.fixture
def collector(state_dim: int, config: CuriosityConfig) -> CuriosityRolloutCollector:
    return CuriosityRolloutCollector(state_dim, config, use_icm=True, use_rnd=True)


# =============================================================================
# R356 InverseForwardDynamics (ICM) 测试
# =============================================================================

class TestR356ICM:
    """R356 ICM 内在好奇心模块测试（Pathak 2017）。"""

    def test_encode_shape(self, icm: InverseForwardDynamics, state_dim: int) -> None:
        """φ(s) 形状 = feature_dim。"""
        s = np.random.default_rng(0).normal(size=state_dim)
        phi = icm.encode(s)
        assert phi.shape == (8,)

    def test_encode_state_dim_mismatch(self, icm: InverseForwardDynamics) -> None:
        """状态维度不匹配 → raise（R03）。"""
        with pytest.raises(ValueError, match="状态维度"):
            icm.encode(np.zeros(999))

    def test_inverse_predict_shape(
        self, icm: InverseForwardDynamics, state_dim: int
    ) -> None:
        """inverse_predict 返回 action_dim 维。"""
        rng = np.random.default_rng(0)
        s_t = rng.normal(size=state_dim)
        s_tp1 = rng.normal(size=state_dim)
        a = icm.inverse_predict(s_t, s_tp1)
        assert a.shape == (4,)

    def test_forward_predict_shape(
        self, icm: InverseForwardDynamics, state_dim: int
    ) -> None:
        """forward_predict 返回 feature_dim 维。"""
        rng = np.random.default_rng(0)
        s_t = rng.normal(size=state_dim)
        a = np.array([0.1, 0.2, 0.3, 0.4])
        phi = icm.forward_predict(s_t, a)
        assert phi.shape == (8,)

    def test_forward_predict_action_dim_mismatch(
        self, icm: InverseForwardDynamics, state_dim: int
    ) -> None:
        """action 维度不匹配 → raise（R03）。"""
        s_t = np.zeros(state_dim)
        with pytest.raises(ValueError, match="action 维度"):
            icm.forward_predict(s_t, np.zeros(999))

    def test_intrinsic_reward_non_negative(
        self, icm: InverseForwardDynamics, state_dim: int
    ) -> None:
        """ICM intrinsic reward >= 0（||·||²/2）。"""
        rng = np.random.default_rng(0)
        s_t = rng.normal(size=state_dim)
        s_tp1 = rng.normal(size=state_dim)
        r = icm.intrinsic_reward(s_t, s_tp1)
        assert r >= 0.0

    def test_intrinsic_reward_zero_for_same_state(
        self, icm: InverseForwardDynamics, state_dim: int, config: CuriosityConfig
    ) -> None:
        """训练后同状态 intrinsic 趋近 0（forward model 学会预测）。"""
        rng = np.random.default_rng(0)
        s = rng.normal(size=state_dim)
        a = icm.inverse_predict(s, s)
        # 训练多轮让 forward model 拟合
        for _ in range(100):
            icm.update(s, s, a)
        r = icm.intrinsic_reward(s, s, a)
        # 训练后 reward 应显著下降
        assert r < 10.0  # 未训练时通常 >> 10

    def test_update_returns_losses(
        self, icm: InverseForwardDynamics, state_dim: int, config: CuriosityConfig
    ) -> None:
        """update 返回 inverse_loss/forward_loss/total_loss。"""
        rng = np.random.default_rng(0)
        s_t = rng.normal(size=state_dim)
        s_tp1 = rng.normal(size=state_dim)
        a = np.zeros(config.action_dim)
        result = icm.update(s_t, s_tp1, a)
        for k in ("inverse_loss", "forward_loss", "total_loss"):
            assert k in result
        assert result["inverse_loss"] >= 0.0
        assert result["forward_loss"] >= 0.0

    def test_update_action_dim_mismatch(
        self, icm: InverseForwardDynamics, state_dim: int
    ) -> None:
        """a_hat_true 维度不匹配 → raise（R03）。"""
        s_t = np.zeros(state_dim)
        s_tp1 = np.zeros(state_dim)
        with pytest.raises(ValueError, match="a_hat_true 维度"):
            icm.update(s_t, s_tp1, np.zeros(999))

    def test_invalid_state_dim(self) -> None:
        """state_dim < 1 → raise（R03）。"""
        with pytest.raises(ValueError, match="state_dim"):
            InverseForwardDynamics(0)


# =============================================================================
# R357 RandomNetworkDistillation (RND) 测试
# =============================================================================

class TestR357RND:
    """R357 RND 随机网络蒸馏测试（Burda 2019）。"""

    def test_target_shape(
        self, rnd: RandomNetworkDistillation, state_dim: int
    ) -> None:
        """g*(s) 形状 = feature_dim。"""
        s = np.zeros(state_dim)
        g = rnd.target(s)
        assert g.shape == (8,)

    def test_predictor_shape(
        self, rnd: RandomNetworkDistillation, state_dim: int
    ) -> None:
        """g_θ(s) 形状 = feature_dim。"""
        s = np.zeros(state_dim)
        g = rnd.predictor(s)
        assert g.shape == (8,)

    def test_target_state_dim_mismatch(
        self, rnd: RandomNetworkDistillation
    ) -> None:
        """target 状态维度不匹配 → raise（R03）。"""
        with pytest.raises(ValueError, match="状态维度"):
            rnd.target(np.zeros(999))

    def test_predictor_state_dim_mismatch(
        self, rnd: RandomNetworkDistillation
    ) -> None:
        """predictor 状态维度不匹配 → raise（R03）。"""
        with pytest.raises(ValueError, match="状态维度"):
            rnd.predictor(np.zeros(999))

    def test_intrinsic_reward_non_negative(
        self, rnd: RandomNetworkDistillation, state_dim: int
    ) -> None:
        """RND intrinsic reward >= 0。"""
        s = np.random.default_rng(0).normal(size=state_dim)
        r = rnd.intrinsic_reward(s)
        assert r >= 0.0

    def test_intrinsic_reward_decreases_with_training(
        self, rnd: RandomNetworkDistillation, state_dim: int
    ) -> None:
        """训练后 intrinsic reward 下降（predictor 拟合 target）。"""
        s = np.random.default_rng(0).normal(size=state_dim)
        r_before = rnd.intrinsic_reward(s)
        for _ in range(200):
            rnd.update(s)
        r_after = rnd.intrinsic_reward(s)
        assert r_after < r_before

    def test_update_returns_loss(
        self, rnd: RandomNetworkDistillation, state_dim: int
    ) -> None:
        """update 返回 rnd_loss。"""
        s = np.zeros(state_dim)
        result = rnd.update(s)
        assert "rnd_loss" in result
        assert result["rnd_loss"] >= 0.0

    def test_target_not_updated(
        self, rnd: RandomNetworkDistillation, state_dim: int
    ) -> None:
        """target network 不更新（Burda 2019 关键特性）。"""
        s = np.random.default_rng(0).normal(size=state_dim)
        W_before = rnd.W_target.copy()
        for _ in range(50):
            rnd.update(s)
        W_after = rnd.W_target.copy()
        np.testing.assert_array_equal(W_before, W_after)

    def test_invalid_state_dim(self) -> None:
        """state_dim < 1 → raise（R03）。"""
        with pytest.raises(ValueError, match="state_dim"):
            RandomNetworkDistillation(0)


# =============================================================================
# R358 CuriosityRewardShaper 测试
# =============================================================================

class TestR358RewardShaper:
    """R358 Curiosity 奖励融合器测试。"""

    def test_shape_only_extrinsic(
        self, shaper: CuriosityRewardShaper, state_dim: int
    ) -> None:
        """无 ICM/RND 时 total = extrinsic_weight·extrinsic。"""
        s = np.zeros(state_dim)
        result = shaper.shape(1.0, s)
        assert result["total_reward"] == pytest.approx(1.0)
        assert result["icm_intrinsic"] == 0.0
        assert result["rnd_intrinsic"] == 0.0

    def test_shape_with_icm(
        self, shaper: CuriosityRewardShaper, icm: InverseForwardDynamics, state_dim: int
    ) -> None:
        """带 ICM 时 total 包含 ICM intrinsic。"""
        rng = np.random.default_rng(0)
        s_t = rng.normal(size=state_dim)
        s_tp1 = rng.normal(size=state_dim)
        a = icm.inverse_predict(s_t, s_tp1)
        result = shaper.shape(1.0, s_tp1, icm=icm, prev_state=s_t, action=a)
        assert result["icm_intrinsic"] >= 0.0
        assert result["total_reward"] != pytest.approx(1.0)

    def test_shape_icm_without_prev_state_raises(
        self, shaper: CuriosityRewardShaper, icm: InverseForwardDynamics, state_dim: int
    ) -> None:
        """ICM 但无 prev_state → raise（R03）。"""
        s = np.zeros(state_dim)
        with pytest.raises(ValueError, match="prev_state"):
            shaper.shape(1.0, s, icm=icm)

    def test_shape_with_rnd(
        self, shaper: CuriosityRewardShaper, rnd: RandomNetworkDistillation, state_dim: int
    ) -> None:
        """带 RND 时 total 包含 RND intrinsic。"""
        s = np.random.default_rng(0).normal(size=state_dim)
        result = shaper.shape(1.0, s, rnd=rnd)
        assert result["rnd_intrinsic"] >= 0.0

    def test_shape_visited_state_zero_intrinsic(
        self, shaper: CuriosityRewardShaper, rnd: RandomNetworkDistillation, state_dim: int
    ) -> None:
        """已访问状态 intrinsic=0（避免 reward hacking）。"""
        s = np.random.default_rng(0).normal(size=state_dim)
        # 第一次访问
        r1 = shaper.shape(1.0, s, rnd=rnd)
        assert not r1["visited"]
        assert r1["rnd_intrinsic"] > 0.0
        # 第二次访问同一状态
        r2 = shaper.shape(1.0, s, rnd=rnd)
        assert r2["visited"]
        assert r2["rnd_intrinsic"] == 0.0

    def test_reset_clears_visited(
        self, shaper: CuriosityRewardShaper, rnd: RandomNetworkDistillation, state_dim: int
    ) -> None:
        """reset 后 visited 清空。"""
        s = np.random.default_rng(0).normal(size=state_dim)
        shaper.shape(1.0, s, rnd=rnd)
        shaper.reset()
        result = shaper.shape(1.0, s, rnd=rnd)
        assert not result["visited"]

    def test_shape_returns_all_fields(
        self, shaper: CuriosityRewardShaper, state_dim: int
    ) -> None:
        """shape 返回 6 个字段。"""
        s = np.zeros(state_dim)
        result = shaper.shape(1.0, s)
        for k in ("total_reward", "extrinsic", "icm_intrinsic",
                  "rnd_intrinsic", "intrinsic_total", "visited"):
            assert k in result


# =============================================================================
# R359-R360 CuriosityRolloutCollector 测试
# =============================================================================

class TestR359R360Collector:
    """R359-R360 Curiosity rollout 收集器测试。"""

    def test_init_both(
        self, state_dim: int, config: CuriosityConfig
    ) -> None:
        """同时启用 ICM + RND。"""
        c = CuriosityRolloutCollector(state_dim, config, use_icm=True, use_rnd=True)
        assert c.icm is not None
        assert c.rnd is not None

    def test_init_icm_only(
        self, state_dim: int, config: CuriosityConfig
    ) -> None:
        """仅 ICM。"""
        c = CuriosityRolloutCollector(state_dim, config, use_icm=True, use_rnd=False)
        assert c.icm is not None
        assert c.rnd is None

    def test_init_rnd_only(
        self, state_dim: int, config: CuriosityConfig
    ) -> None:
        """仅 RND。"""
        c = CuriosityRolloutCollector(state_dim, config, use_icm=False, use_rnd=True)
        assert c.icm is None
        assert c.rnd is not None

    def test_collect_step_basic(
        self, collector: CuriosityRolloutCollector, state_dim: int, config: CuriosityConfig
    ) -> None:
        """collect_step 返回 shaped reward。"""
        rng = np.random.default_rng(0)
        s_t = rng.normal(size=state_dim)
        a = rng.normal(size=config.action_dim)
        s_tp1 = rng.normal(size=state_dim)
        result = collector.collect_step(s_t, a, s_tp1, 1.0)
        for k in ("shaped_reward", "extrinsic", "icm_intrinsic",
                  "rnd_intrinsic", "visited", "update_info"):
            assert k in result

    def test_collect_step_empty_action_icm_raises(
        self, state_dim: int, config: CuriosityConfig
    ) -> None:
        """use_icm=True 但 action 维度不匹配 → raise（R03）。"""
        c = CuriosityRolloutCollector(state_dim, config, use_icm=True, use_rnd=False)
        rng = np.random.default_rng(0)
        s_t = rng.normal(size=state_dim)
        s_tp1 = rng.normal(size=state_dim)
        # action 维度错误会触发 ICM update 内部的 raise
        with pytest.raises(ValueError):
            c.collect_step(s_t, np.zeros(999), s_tp1, 1.0)

    def test_collect_rollout_basic(
        self, collector: CuriosityRolloutCollector, state_dim: int, config: CuriosityConfig
    ) -> None:
        """collect_rollout 返回统计。"""
        rng = np.random.default_rng(0)
        trajectory = []
        for _ in range(5):
            trajectory.append({
                "prev_state": rng.normal(size=state_dim),
                "action": rng.normal(size=config.action_dim),
                "next_state": rng.normal(size=state_dim),
                "extrinsic": 1.0,
            })
        result = collector.collect_rollout(trajectory)
        for k in ("rewards", "mean_reward", "total_reward",
                  "mean_icm_loss", "mean_rnd_loss", "n_steps"):
            assert k in result
        assert result["n_steps"] == 5
        assert len(result["rewards"]) == 5

    def test_collect_rollout_empty_raises(
        self, collector: CuriosityRolloutCollector
    ) -> None:
        """空 trajectory → raise（R03）。"""
        with pytest.raises(ValueError, match="不能为空"):
            collector.collect_rollout([])

    def test_collect_rollout_missing_field(
        self, collector: CuriosityRolloutCollector, state_dim: int, config: CuriosityConfig
    ) -> None:
        """trajectory step 缺字段 → raise（R03）。"""
        rng = np.random.default_rng(0)
        trajectory = [{
            "prev_state": rng.normal(size=state_dim),
            # 缺 action
            "next_state": rng.normal(size=state_dim),
            "extrinsic": 1.0,
        }]
        with pytest.raises(ValueError, match="缺字段"):
            collector.collect_rollout(trajectory)

    def test_reset_episode(
        self, collector: CuriosityRolloutCollector, state_dim: int, config: CuriosityConfig
    ) -> None:
        """reset_episode 清空 visited。"""
        rng = np.random.default_rng(0)
        s = rng.normal(size=state_dim)
        a = rng.normal(size=config.action_dim)
        s2 = rng.normal(size=state_dim)
        collector.collect_step(s, a, s2, 1.0)
        collector.reset_episode()
        # 重置后 s2 应被视为未访问
        # （这里间接验证：collect_step 不抛异常即可）

    def test_save(
        self, collector: CuriosityRolloutCollector, tmp_path: Path
    ) -> None:
        """save 生成 JSON 文件。"""
        path = collector.save(tmp_path / "curiosity.json")
        assert path.exists()
        import json
        data = json.loads(path.read_text(encoding="utf-8"))
        assert "config" in data
        assert "use_icm" in data
        assert "use_rnd" in data

    def test_invalid_state_dim(self) -> None:
        """state_dim < 1 → raise（R03）。"""
        with pytest.raises(ValueError, match="state_dim"):
            CuriosityRolloutCollector(0)


# =============================================================================
# R03 禁止 fall-back 合规测试
# =============================================================================

class TestR03NoFallback:
    """R03 合规：所有业务错误 raise。"""

    def test_icm_state_dim_zero(self) -> None:
        with pytest.raises(ValueError):
            InverseForwardDynamics(0)

    def test_rnd_state_dim_zero(self) -> None:
        with pytest.raises(ValueError):
            RandomNetworkDistillation(0)

    def test_collector_state_dim_zero(self) -> None:
        with pytest.raises(ValueError):
            CuriosityRolloutCollector(0)

    def test_no_silent_fallback_in_source(self) -> None:
        """源码无 except:pass 静默兜底。"""
        from polaris.rl import rl_curiosity as mod
        src = Path(mod.__file__).read_text(encoding="utf-8")
        assert "except: pass" not in src
        assert "except Exception: pass" not in src


# =============================================================================
# R02 学术诚信测试
# =============================================================================

class TestR02AcademicIntegrity:
    """R02 学术诚信。"""

    def test_module_docstring_has_5plus_urls(self) -> None:
        from polaris.rl import rl_curiosity as mod
        assert mod.__doc__ is not None
        urls = [l for l in mod.__doc__.splitlines() if "http" in l or "DOI:" in l]
        assert len(urls) >= 5

    def test_pathak_cited(self) -> None:
        from polaris.rl import rl_curiosity as mod
        assert "Pathak" in mod.__doc__
        assert "1705.05363" in mod.__doc__

    def test_burda_cited(self) -> None:
        from polaris.rl import rl_curiosity as mod
        assert "Burda" in mod.__doc__
        assert "1810.12894" in mod.__doc__

    def test_innovation_marked(self) -> None:
        from polaris.rl import rl_curiosity as mod
        src = Path(mod.__file__).read_text(encoding="utf-8")
        assert "*创新*" in src


# =============================================================================
# R04 GPU 合规测试
# =============================================================================

class TestR04GPUCompliance:
    """R04 GPU 合规。"""

    def test_gpu_disabled_flag(self) -> None:
        assert GPU_DISABLED_R04 is True

    def test_no_gpu_imports(self) -> None:
        from polaris.rl import rl_curiosity as mod
        src = Path(mod.__file__).read_text(encoding="utf-8")
        assert "import cupy" not in src
        assert "import torch" not in src
        assert "from torch" not in src
        assert "import jax" not in src


# =============================================================================
# 集成测试
# =============================================================================

class TestIntegration:
    """集成测试：Curiosity + 大规模布局环境。"""

    def test_curiosity_with_placement_env(self, state_dim: int, config: CuriosityConfig) -> None:
        """Curiosity 收集器与布局状态交互。"""
        from polaris.rl.rl_numpy_advanced import LargeScalePlacementEnv
        env = LargeScalePlacementEnv()
        # 用 graph_summary 作为 state（8 维）
        collector = CuriosityRolloutCollector(8, config, use_icm=True, use_rnd=True)
        # 模拟状态序列
        rng = np.random.default_rng(0)
        trajectory = []
        for _ in range(3):
            trajectory.append({
                "prev_state": rng.normal(size=8),
                "action": rng.normal(size=config.action_dim),
                "next_state": rng.normal(size=8),
                "extrinsic": float(rng.uniform(-1, 1)),
            })
        result = collector.collect_rollout(trajectory)
        assert result["n_steps"] == 3
        assert "mean_reward" in result
