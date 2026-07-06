"""D07 AI/ML 维度增强测试（polaris-trainer，8→10 分）。

测试覆盖（R03 禁止 fall-back，R04 不参与 GPU）:
- §1 TrainingLogger: JSONL 核心 + 可选 TB / add_scalar / add_scalars /
  add_histogram / log_episode / load_jsonl_log / close 幂等
- §2 benchmark_runner: compute_hpwl / compute_overlap_count /
  compute_area_utilization / compare_with_baselines / run_benchmark /
  save_report / format_report_text / 基线数据完整性
- §3 visualization: plot_reward_curve / plot_hpwl_convergence /
  plot_policy_entropy / plot_learning_rate / plot_training_dashboard /
  save_dashboard / plot_benchmark_comparison
- §4 presets: smoke_test / full_ppo / ariane_train / mempool_train /
  nvdla_train / benchmark_eval / list_presets / get_preset / R03 raise
- §5 train_loop logger 集成: train_ppo(logger=...) / train_with_env_factory
- §6 TILOS MemPool/NVDLA benchmark（如 polaris_nn 可用）

学术依据（R02 学术诚信，≥5 个文献 URL）:
1. Schulman et al., 2017, PPO https://arxiv.org/abs/1707.06347
2. TILOS MacroPlacement https://github.com/TILOS-AI-Institute/MacroPlacement
3. RePlAce ICCAD 2019 https://doi.org/10.1109/ICCAD45719.2019.8942087
4. DREAMPlace DAC 2019 https://doi.org/10.1109/DAC.2019.8721934
5. AlphaChip Nature 2021 https://www.nature.com/articles/s41586-021-03544-w
6. Loshchilov & Hutter, 2017, SGDR https://arxiv.org/abs/1608.03983
7. matplotlib https://matplotlib.org/stable/contents.html
8. Stable-Baselines3 PPO https://stable-baselines3.readthedocs.io/

规则依据: R02 / R03 / R04 / R05 / R11 / R12 / R13。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

# 让测试既能从已安装包导入，也能从源码树导入
_SRC = str(Path(__file__).resolve().parents[1] / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import polaris_trainer  # noqa: E402
from polaris_trainer import (  # noqa: E402
    ALPHACHIP_BASELINES,
    BaselineResult,
    BenchmarkReport,
    DREAMPLACE_BASELINES,
    PPOAgent,
    PPOConfig,
    REPLACE_BASELINES,
    TrainingLogger,
    TrainConfig,
    ariane_train_preset,
    benchmark_eval_preset,
    compare_with_baselines,
    compute_area_utilization,
    compute_hpwl,
    compute_overlap_count,
    format_report_text,
    full_ppo_preset,
    get_preset,
    list_presets,
    load_jsonl_log,
    mempool_train_preset,
    nvdla_train_preset,
    plot_benchmark_comparison,
    plot_hpwl_convergence,
    plot_learning_rate,
    plot_policy_entropy,
    plot_reward_curve,
    plot_training_dashboard,
    run_benchmark,
    save_dashboard,
    save_report,
    smoke_test_preset,
    train_ppo,
    train_with_env_factory,
)


# =============================================================================
# §1 TrainingLogger（JSONL 核心 + 可选 TB）
# =============================================================================


def test_training_logger_jsonl_core(tmp_path):
    """TrainingLogger: JSONL 核心层始终可用（add_scalar/add_scalars/log_episode）。"""
    logger = TrainingLogger(log_dir=tmp_path, enable_tensorboard=False)
    assert logger.tensorboard_enabled is False
    logger.add_scalar("test/loss", 0.5, step=0)
    logger.add_scalars("train", {"reward": 1.2, "loss": 0.3}, step=1)
    logger.add_histogram("weights/grad", np.random.randn(100), step=2)
    logger.log_episode(0, 1.5, hpwl=12000.0,
                       metrics={"policy_loss": 0.01, "value_loss": 0.5},
                       lr=3e-4)
    logger.flush()
    logger.close()
    # JSONL 文件已生成
    jsonl_path = tmp_path / "metrics.jsonl"
    assert jsonl_path.exists()
    records = load_jsonl_log(jsonl_path)
    assert len(records) >= 4  # 至少 4 条记录
    # 第一条含 test/loss
    assert "test/loss" in records[0]
    assert records[0]["test/loss"] == 0.5
    # log_episode 写入 train/ 前缀
    ep_rec = next(r for r in records if "train/ep_reward" in r)
    assert ep_rec["train/ep_reward"] == 1.5
    assert ep_rec["train/hpwl_um"] == 12000.0


def test_training_logger_close_idempotent(tmp_path):
    """TrainingLogger.close 幂等（多次调用不报错）。"""
    logger = TrainingLogger(log_dir=tmp_path, enable_tensorboard=False)
    logger.add_scalar("x", 1.0, step=0)
    logger.close()
    logger.close()  # 幂等
    logger.flush()  # 幂等


def test_training_logger_nan_inf_handling(tmp_path):
    """TrainingLogger: NaN/Inf 写 0（JSON 规范要求有限数）。"""
    logger = TrainingLogger(log_dir=tmp_path, enable_tensorboard=False)
    logger.add_scalar("nan_val", float("nan"), step=0)
    logger.add_scalar("inf_val", float("inf"), step=1)
    logger.close()
    records = load_jsonl_log(tmp_path / "metrics.jsonl")
    assert records[0]["nan_val"] == 0.0
    assert records[1]["inf_val"] == 0.0


def test_load_jsonl_log_missing_raise(tmp_path):
    """load_jsonl_log: 文件不存在 raise（R03 无 fall-back）。"""
    with pytest.raises(FileNotFoundError, match="R03"):
        load_jsonl_log(tmp_path / "nonexistent.jsonl")


def test_training_logger_force_tb_unavailable_raise(tmp_path):
    """TrainingLogger: enable_tensorboard=True 但 TB 不可用时 raise（R03）。"""
    # 模拟 TB 不可用：monkeypatch _try_import_tensorboard 返回 None
    import polaris_trainer.tensorboard_logger as tb_mod
    original = tb_mod._try_import_tensorboard
    tb_mod._try_import_tensorboard = lambda: None
    try:
        with pytest.raises(ImportError, match="R03"):
            TrainingLogger(log_dir=tmp_path, enable_tensorboard=True)
    finally:
        tb_mod._try_import_tensorboard = original


# =============================================================================
# §2 benchmark_runner（HPWL + 基线对比）
# =============================================================================


def test_compute_hpwl_basic():
    """compute_hpwl: 两模块单连接 HPWL = |dx|+|dy|。"""
    placements = {"a": (0.0, 0.0), "b": (3.0, 4.0)}
    connections = [("a", "b", "p1", "p2")]
    hpwl = compute_hpwl(placements, connections)
    assert abs(hpwl - 7.0) < 1e-9  # |3| + |4| = 7


def test_compute_hpwl_multi_connection():
    """compute_hpwl: 多连接求和。"""
    placements = {"a": (0.0, 0.0), "b": (1.0, 0.0), "c": (0.0, 1.0)}
    connections = [("a", "b"), ("a", "c"), ("b", "c")]
    hpwl = compute_hpwl(placements, connections)
    # |1-0|+|0-0| + |0-0|+|1-0| + |0-1|+|1-0| = 1 + 1 + 2 = 4
    assert abs(hpwl - 4.0) < 1e-9


def test_compute_hpwl_empty_connections():
    """compute_hpwl: 空连接返回 0。"""
    assert compute_hpwl({"a": (0.0, 0.0)}, []) == 0.0


def test_compute_hpwl_missing_module_raise():
    """compute_hpwl: 连接引用缺失模块 raise（R03 无 fall-back）。"""
    with pytest.raises(KeyError, match="R03"):
        compute_hpwl({"a": (0.0, 0.0)}, [("a", "nonexistent")])


def test_compute_overlap_count():
    """compute_overlap_count: 重叠模块对计数。"""
    # 两个重叠模块
    placements = {
        "a": (0.0, 0.0, 10.0, 10.0),
        "b": (5.0, 5.0, 10.0, 10.0),  # 与 a 重叠
        "c": (50.0, 50.0, 10.0, 10.0),  # 不重叠
    }
    assert compute_overlap_count(placements) == 1


def test_compute_area_utilization():
    """compute_area_utilization: 模块面积/画布面积。"""
    placements = {"a": (0.0, 0.0, 50.0, 50.0)}  # 2500 μm²
    util = compute_area_utilization(placements, canvas_w=100.0, canvas_h=100.0)
    assert abs(util - 0.25) < 1e-9  # 2500/10000


def test_compute_area_utilization_zero_canvas_raise():
    """compute_area_utilization: 画布尺寸 ≤0 raise（R03）。"""
    with pytest.raises(ValueError, match="R03"):
        compute_area_utilization({"a": (0, 0, 1, 1)}, canvas_w=0, canvas_h=100)


def test_baseline_data_completeness():
    """基线数据: RePlAce/DREAMPlace/AlphaChip 三个 benchmark 均有数据。"""
    for name in ("ariane", "mempool", "nvdla"):
        assert name in REPLACE_BASELINES
        assert name in DREAMPLACE_BASELINES
        assert name in ALPHACHIP_BASELINES
        # AlphaChip 应优于 RePlAce（归一化 HPWL 更低）
        assert ALPHACHIP_BASELINES[name] < REPLACE_BASELINES[name]


def test_compare_with_baselines():
    """compare_with_baselines: 返回基线列表 + 改进比例。"""
    baselines, imp_r, imp_d = compare_with_baselines(
        our_hpwl=45000.0, target_hpwl=50000.0, benchmark_name="ariane"
    )
    assert len(baselines) == 3  # RePlAce/DREAMPlace/AlphaChip
    methods = {b.method for b in baselines}
    assert methods == {"RePlAce", "DREAMPlace", "AlphaChip"}
    # our_norm = 0.9, RePlAce=1.2 → improvement = (1.2-0.9)/1.2 = 0.25
    assert imp_r > 0  # 我们优于 RePlAce
    assert imp_d > 0  # 我们优于 DREAMPlace


def test_compare_with_baselines_invalid_target_raise():
    """compare_with_baselines: target_hpwl ≤0 raise（R03）。"""
    with pytest.raises(ValueError, match="R03"):
        compare_with_baselines(100.0, 0.0, "ariane")


def test_compare_with_baselines_unknown_benchmark_raise():
    """compare_with_baselines: 未知 benchmark raise（R03）。"""
    with pytest.raises(KeyError):
        compare_with_baselines(100.0, 200.0, "unknown_chip")


def test_run_benchmark_full_flow(tmp_path):
    """run_benchmark: 端到端评估 → 报告 → 保存 → 格式化文本。"""
    placements = {
        "pc_gen": (40.0, 30.0),
        "fetch": (60.0, 40.0),
        "decode": (75.0, 50.0),
        "alu": (50.0, 35.0),
        "icache": (100.0, 75.0),
        "dcache": (110.0, 85.0),
    }
    connections = [
        ("pc_gen", "fetch", "pc", "pc_in"),
        ("fetch", "decode", "instr", "instr_in"),
        ("decode", "alu", "op", "op_in"),
        ("fetch", "icache", "req", "req_in"),
        ("alu", "dcache", "mem", "mem_in"),
    ]
    report = run_benchmark(
        benchmark_name="ariane",
        placements=placements,
        module_count=6,
        connection_count=5,
        connections=connections,
        target_hpwl=500.0,
    )
    assert isinstance(report, BenchmarkReport)
    assert report.benchmark_name == "ariane"
    assert report.our_hpwl_um > 0
    assert report.normalized_hpwl > 0
    assert len(report.baselines) == 3
    # 保存报告
    report_path = save_report(report, tmp_path / "report.json")
    assert report_path.exists()
    saved = json.loads(report_path.read_text(encoding="utf-8"))
    assert saved["benchmark_name"] == "ariane"
    # 格式化文本
    text = format_report_text(report)
    assert "TILOS Benchmark Report" in text
    assert "ariane" in text


# =============================================================================
# §3 visualization（matplotlib 纯 CPU）
# =============================================================================


_SAMPLE_LOGS = [
    {"step": 0, "train/ep_reward": 1.0, "train/hpwl_um": 50000.0,
     "train/entropy": 2.5, "train/lr": 3e-4},
    {"step": 1, "train/ep_reward": 1.5, "train/hpwl_um": 45000.0,
     "train/entropy": 2.3, "train/lr": 2.8e-4},
    {"step": 2, "train/ep_reward": 2.0, "train/hpwl_um": 40000.0,
     "train/entropy": 2.0, "train/lr": 2.5e-4},
    {"step": 3, "train/ep_reward": 2.2, "train/hpwl_um": 38000.0,
     "train/entropy": 1.8, "train/lr": 2.0e-4},
    {"step": 4, "train/ep_reward": 2.5, "train/hpwl_um": 35000.0,
     "train/entropy": 1.5, "train/lr": 1.5e-4},
]


def test_plot_reward_curve(tmp_path):
    """plot_reward_curve: 从 logs 绘制奖励曲线并保存。"""
    import matplotlib
    matplotlib.use("Agg")
    ax = plot_reward_curve(_SAMPLE_LOGS, window=3)
    assert ax is not None
    import matplotlib.pyplot as plt
    fig = ax.figure
    fig.savefig(tmp_path / "reward.png", dpi=72)
    plt.close(fig)
    assert (tmp_path / "reward.png").exists()


def test_plot_hpwl_convergence(tmp_path):
    """plot_hpwl_convergence: 绘制 HPWL 收敛曲线。"""
    import matplotlib
    matplotlib.use("Agg")
    ax = plot_hpwl_convergence(_SAMPLE_LOGS)
    assert ax is not None
    import matplotlib.pyplot as plt
    plt.close(ax.figure)


def test_plot_policy_entropy(tmp_path):
    """plot_policy_entropy: 绘制 policy entropy 曲线。"""
    import matplotlib
    matplotlib.use("Agg")
    ax = plot_policy_entropy(_SAMPLE_LOGS)
    assert ax is not None
    import matplotlib.pyplot as plt
    plt.close(ax.figure)


def test_plot_learning_rate(tmp_path):
    """plot_learning_rate: 绘制学习率调度曲线。"""
    import matplotlib
    matplotlib.use("Agg")
    ax = plot_learning_rate(_SAMPLE_LOGS)
    assert ax is not None
    import matplotlib.pyplot as plt
    plt.close(ax.figure)


def test_save_dashboard(tmp_path):
    """save_dashboard: 保存综合仪表盘到 PNG。"""
    output = save_dashboard(_SAMPLE_LOGS, tmp_path / "dashboard.png")
    assert output.exists()
    assert output.stat().st_size > 0


def test_plot_benchmark_comparison(tmp_path):
    """plot_benchmark_comparison: 绘制 benchmark 对比柱状图。"""
    import matplotlib
    matplotlib.use("Agg")
    reports = [
        {"benchmark_name": "ariane", "normalized_hpwl": 0.95,
         "baselines": [
             {"method": "RePlAce", "normalized_hpwl": 1.2},
             {"method": "DREAMPlace", "normalized_hpwl": 1.05},
             {"method": "AlphaChip", "normalized_hpwl": 0.92},
         ]},
        {"benchmark_name": "mempool", "normalized_hpwl": 1.05,
         "baselines": [
             {"method": "RePlAce", "normalized_hpwl": 1.25},
             {"method": "DREAMPlace", "normalized_hpwl": 1.10},
             {"method": "AlphaChip", "normalized_hpwl": 0.95},
         ]},
    ]
    ax = plot_benchmark_comparison(reports)
    assert ax is not None
    import matplotlib.pyplot as plt
    plt.close(ax.figure)


def test_plot_benchmark_comparison_empty_raise():
    """plot_benchmark_comparison: 空 reports raise（R03）。"""
    with pytest.raises(ValueError, match="R03"):
        plot_benchmark_comparison([])


# =============================================================================
# §4 presets（训练预设）
# =============================================================================


def test_smoke_test_preset():
    """smoke_test_preset: 10 episodes + cosine + early_stop=0。"""
    preset = smoke_test_preset()
    assert preset.name == "smoke_test"
    assert preset.train.num_episodes == 10
    assert preset.ppo.lr_schedule == "cosine"
    assert preset.train.early_stop_patience == 0  # 禁用早停


def test_full_ppo_preset_1000_episodes():
    """full_ppo_preset: 1000+ episodes + cosine + warmup + clip_vf。"""
    preset = full_ppo_preset()
    assert preset.name == "full_ppo"
    assert preset.train.num_episodes == 1000  # 默认 1000
    assert preset.ppo.lr_schedule == "cosine"
    assert preset.ppo.lr_warmup_steps == 50
    assert preset.ppo.clip_vf == 0.2  # Engstrom 2020 推荐
    assert preset.train.early_stop_patience == 100
    assert preset.train.checkpoint_every == 50
    # 可自定义 num_episodes
    preset_2k = full_ppo_preset(num_episodes=2000)
    assert preset_2k.train.num_episodes == 2000


def test_ariane_train_preset():
    """ariane_train_preset: 1500 episodes + 17 模块 + 增强探索。"""
    preset = ariane_train_preset()
    assert preset.name == "ariane_train"
    assert preset.train.num_episodes == 1500
    assert preset.ppo.ent_coef == 0.02  # 增加探索
    assert preset.ppo.lr == 2e-4  # 稍小学习率


def test_mempool_train_preset():
    """mempool_train_preset: 2000 episodes + 15 模块 + 大隐藏层。"""
    preset = mempool_train_preset()
    assert preset.name == "mempool_train"
    assert preset.train.num_episodes == 2000
    assert preset.train.hidden_dim == 256  # 更大隐藏层
    assert preset.ppo.n_epochs == 6  # 更多 epoch


def test_nvdla_train_preset():
    """nvdla_train_preset: 1800 episodes + 11 模块。"""
    preset = nvdla_train_preset()
    assert preset.name == "nvdla_train"
    assert preset.train.num_episodes == 1800
    assert preset.ppo.ent_coef == 0.015


def test_benchmark_eval_preset():
    """benchmark_eval_preset: 不训练（num_episodes=0）。"""
    preset = benchmark_eval_preset()
    assert preset.name == "benchmark_eval"
    assert preset.train.num_episodes == 0
    assert preset.ppo.lr == 0.0


def test_list_presets_and_get_preset():
    """list_presets + get_preset: 注册表完整 + 工厂函数可用。"""
    names = list_presets()
    assert "smoke_test" in names
    assert "full_ppo" in names
    assert "ariane_train" in names
    assert "mempool_train" in names
    assert "nvdla_train" in names
    assert "benchmark_eval" in names
    # get_preset 工厂
    preset = get_preset("smoke_test")
    assert preset.name == "smoke_test"
    # 带参数
    preset_2k = get_preset("full_ppo", num_episodes=2000)
    assert preset_2k.train.num_episodes == 2000


def test_get_preset_unknown_raise():
    """get_preset: 未知预设 raise（R03 无 fall-back）。"""
    with pytest.raises(KeyError, match="R03"):
        get_preset("nonexistent_preset")


# =============================================================================
# §5 train_loop logger 集成
# =============================================================================


class _FakeEnvWithHPWL:
    """带 HPWL info 的假环境（测试 logger 集成）。"""

    def __init__(self, obs_dim: int = 8) -> None:
        self.obs_dim = obs_dim
        self.name = "fake_hpwl_env"
        self._step = 0
        self._rng = np.random.default_rng(42)

    def reset(self):
        self._step = 0
        return {"vec": np.zeros(self.obs_dim, dtype=np.float64)}, {}

    def step(self, action):
        self._step += 1
        obs = {"vec": self._rng.standard_normal(self.obs_dim)}
        reward = float(self._rng.standard_normal())
        terminated = self._step >= 5
        info = {"hpwl_um": 50000.0 - self._step * 1000.0}  # HPWL 递减
        return obs, reward, terminated, False, info


def test_train_ppo_with_logger(tmp_path):
    """train_ppo(logger=...): 训练 + 日志记录到 JSONL。"""
    np.random.seed(0)
    agent = PPOAgent(
        obs_dim=8, action_dim=2,
        config=PPOConfig(batch_size=4, n_epochs=1, lr_schedule="cosine", total_steps=2),
        hidden_dim=16,
    )
    env = _FakeEnvWithHPWL(obs_dim=8)
    config = TrainConfig(
        num_episodes=3, rollout_steps=6, hidden_dim=16,
        checkpoint_dir=str(tmp_path / "ckpts"), checkpoint_every=10,
        log_every=10, early_stop_patience=0, lr_schedule="cosine", seed=0,
    )
    logger = TrainingLogger(
        log_dir=tmp_path / "logs", enable_tensorboard=False
    )
    trained, logs = train_ppo(
        agent, env, config, obs_dim=8, verbose=False, logger=logger
    )
    assert trained is agent
    assert len(logs) == 3
    # logs 含 hpwl_um（从 env info 提取）
    assert "hpwl_um" in logs[0]
    # JSONL 日志文件已生成
    jsonl_path = tmp_path / "logs" / "metrics.jsonl"
    assert jsonl_path.exists()
    records = load_jsonl_log(jsonl_path)
    # 每轮一条 log_episode 记录
    ep_records = [r for r in records if "train/ep_reward" in r]
    assert len(ep_records) == 3
    # 含 hpwl_um
    assert "train/hpwl_um" in ep_records[0]


def test_train_with_env_factory_with_logger(tmp_path):
    """train_with_env_factory(logger=...): 多 env 训练 + 日志记录。"""
    np.random.seed(1)
    agent = PPOAgent(
        obs_dim=8, action_dim=2,
        config=PPOConfig(batch_size=4, n_epochs=1),
        hidden_dim=16,
    )

    def env_factory(ep):
        env = _FakeEnvWithHPWL(obs_dim=8)
        env.name = f"env_{ep}"
        return env

    config = TrainConfig(
        num_episodes=2, rollout_steps=6, hidden_dim=16,
        checkpoint_dir=str(tmp_path / "ckpts_factory"), checkpoint_every=10,
        log_every=10, early_stop_patience=0, seed=1,
    )
    logger = TrainingLogger(
        log_dir=tmp_path / "logs_factory", enable_tensorboard=False
    )
    trained, logs = train_with_env_factory(
        agent, env_factory, config, obs_dim=8, verbose=False, logger=logger
    )
    assert len(logs) == 2
    jsonl_path = tmp_path / "logs_factory" / "metrics.jsonl"
    assert jsonl_path.exists()


def test_train_ppo_without_logger_backward_compat(tmp_path):
    """train_ppo: logger=None 时向后兼容（无 JSONL 但训练正常）。"""
    np.random.seed(0)
    agent = PPOAgent(
        obs_dim=8, action_dim=2,
        config=PPOConfig(batch_size=4, n_epochs=1),
        hidden_dim=16,
    )
    env = _FakeEnvWithHPWL(obs_dim=8)
    config = TrainConfig(
        num_episodes=2, rollout_steps=4, hidden_dim=16,
        checkpoint_dir=str(tmp_path / "ckpts"), checkpoint_every=10,
        log_every=10, early_stop_patience=0, seed=0,
    )
    trained, logs = train_ppo(agent, env, config, obs_dim=8, verbose=False)
    assert len(logs) == 2


# =============================================================================
# §6 TILOS MemPool / NVDLA benchmark（如 polaris_nn 可用）
# =============================================================================
# polaris_nn 是可选测试依赖（polaris_trainer 不强依赖 polaris_nn）
# 在每个测试函数内部用 pytest.importorskip 检查，避免影响 §1-§5 测试收集


def test_tilos_mempool_benchmark():
    """load_mempool_benchmark: 15 模块 + 31 连接 + CircuitSpec 完整。"""
    pytest.importorskip("polaris_nn", reason="polaris_nn 不可用")
    from polaris_nn.data.tilos_benchmark import (
        MEMPOOL_CONNECTIONS,
        MEMPOOL_MODULES,
        load_mempool_benchmark,
        load_tilos_benchmark,
    )
    assert len(MEMPOOL_MODULES) == 15
    assert len(MEMPOOL_CONNECTIONS) == 31
    circuit = load_mempool_benchmark()
    assert circuit.name == "tilos_mempool"
    assert len(circuit.devices) == 15
    assert len(circuit.connections) == 31
    # 工厂函数路由
    circuit2 = load_tilos_benchmark("mempool")
    assert circuit2.name == "tilos_mempool"


def test_tilos_nvdla_benchmark():
    """load_nvdla_benchmark: 11 模块 + 24 连接 + CircuitSpec 完整。"""
    pytest.importorskip("polaris_nn", reason="polaris_nn 不可用")
    from polaris_nn.data.tilos_benchmark import (
        NVDLA_CONNECTIONS,
        NVDLA_MODULES,
        load_nvdla_benchmark,
        load_tilos_benchmark,
    )
    assert len(NVDLA_MODULES) == 11
    assert len(NVDLA_CONNECTIONS) == 24
    circuit = load_nvdla_benchmark()
    assert circuit.name == "tilos_nvdla"
    assert len(circuit.devices) == 11
    assert len(circuit.connections) == 24
    # 工厂函数路由
    circuit2 = load_tilos_benchmark("nvdla")
    assert circuit2.name == "tilos_nvdla"


def test_tilos_benchmark_factory_all():
    """load_tilos_benchmark: 三个 benchmark 均可加载。"""
    pytest.importorskip("polaris_nn", reason="polaris_nn 不可用")
    from polaris_nn.data.tilos_benchmark import (
        list_tilos_benchmarks,
        load_tilos_benchmark,
    )
    names = list_tilos_benchmarks()
    assert names == ["ariane", "mempool", "nvdla"]
    for name in names:
        circuit = load_tilos_benchmark(name)
        assert circuit.name == f"tilos_{name}"
        assert len(circuit.devices) > 0


def test_tilos_benchmark_factory_unknown_raise():
    """load_tilos_benchmark: 未知名称 raise（R03 无 fall-back）。"""
    pytest.importorskip("polaris_nn", reason="polaris_nn 不可用")
    from polaris_nn.data.tilos_benchmark import load_tilos_benchmark
    with pytest.raises(KeyError, match="R03"):
        load_tilos_benchmark("unknown_chip")


def test_tilos_benchmark_info():
    """tilos_benchmark_info: 返回完整元信息。"""
    pytest.importorskip("polaris_nn", reason="polaris_nn 不可用")
    from polaris_nn.data.tilos_benchmark import tilos_benchmark_info
    info = tilos_benchmark_info("mempool")
    assert info["name"] == "tilos_mempool"
    assert info["module_count"] == 15
    assert info["connection_count"] == 31
    assert info["benchmark_source"] == "TILOS"
    assert "source_url" in info
    assert "cpu_source_url" in info


def test_tilos_benchmark_info_unknown_raise():
    """tilos_benchmark_info: 未知名称 raise（R03）。"""
    pytest.importorskip("polaris_nn", reason="polaris_nn 不可用")
    from polaris_nn.data.tilos_benchmark import tilos_benchmark_info
    with pytest.raises(KeyError):
        tilos_benchmark_info("unknown")


def test_tilos_benchmark_end_to_end_with_runner():
    """端到端: 加载 TILOS benchmark → 生成布局 → benchmark_runner 评估。"""
    pytest.importorskip("polaris_nn", reason="polaris_nn 不可用")
    from polaris_nn.data.tilos_benchmark import (
        ARIANE_MODULES,
        load_ariane_benchmark,
    )
    circuit = load_ariane_benchmark()
    # 生成简单网格布局（模块中心坐标）
    placements: dict[str, tuple[float, float]] = {}
    for i, dev in enumerate(circuit.devices):
        gx = i % 5
        gy = i // 5
        placements[dev.name] = (gx * 200.0 + 100.0, gy * 200.0 + 100.0)
    # 用 benchmark_runner 评估
    # circuit.connections 为 4-tuple (src_module, src_port, dst_module, dst_port)，
    # compute_hpwl 需要 (src_module, dst_module)，故取 (c[0], c[2])。
    # 回归修复: 此前误取 (c[0], c[1]) 导致 dst 被解释为端口名（R05 Bug 必修）。
    connections = [(c[0], c[2]) for c in circuit.connections]
    report = run_benchmark(
        benchmark_name="ariane",
        placements=placements,
        module_count=len(circuit.devices),
        connection_count=len(circuit.connections),
        connections=connections,
        target_hpwl=circuit.target_value,
    )
    assert report.our_hpwl_um > 0
    assert len(report.baselines) == 3
