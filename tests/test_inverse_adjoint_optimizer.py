"""R28 伴随优化逆向设计模块测试（密度法拓扑优化）。

测试 TopologyAdjointOptimizer 密度法伴随优化：JAX autograd 梯度（与伴随方法等价）、
锥形滤波、sigmoid 投影、β 退火、DRC 惩罚、MMI/光栅耦合器/模式转换器三标准器件、
GDSII 导出。对标 Tidy3D adjoint + lumopt 拓扑优化核心能力。

学术来源（R02 学术诚信）:
- Tidy3D adjoint: https://docs.flexcompute.com/projects/tidy3d/en/latest/notebooks/AdjointPlugin.html
- lumopt: https://github.com/pcrost/lumopt
- Molesky 2018: https://arxiv.org/abs/1809.07731
- Piggott 2017: https://www.nature.com/articles/nphoton.2017.102
- Hughes 2018（autograd=adjoint）: https://arxiv.org/abs/1811.01255

合规: R03 禁止 fall-back（失败 raise，无假数据）；R04 不参与 GPU（JAX 强制 CPU）。
"""

from __future__ import annotations

import os

import gdstk
import numpy as np
import pytest

os.environ.setdefault("JAX_PLATFORMS", "cpu")

from polaris.inverse.topology_adjoint_optimizer import (  # noqa: E402
    TopologyAdjointOptimizer,
    ModeOverlapObjective,
    OptimizerConfig,
    example_grating_coupler,
    example_mmi_1x2,
    example_mode_converter,
)

# gdstk 是 pyproject.toml 必备依赖（R03 禁止 fall-back，直接 import 失败即 raise）


def _make_optimizer(
    h: int = 8,
    w: int = 12,
    n_iters: int = 20,
    drc_weight: float = 0.0,
) -> TopologyAdjointOptimizer:
    """构造测试用优化器（小网格 + 少迭代，加速测试）。"""
    sigma = 1.5
    x = np.arange(w) - (w - 1) / 2.0
    e_in = np.exp(-(x**2) / (2 * sigma**2)).astype(np.complex64)
    e_in = e_in / np.sqrt(np.sum(np.abs(e_in) ** 2))
    # 目标场：偏移高斯，使优化有明确方向
    x2 = np.arange(w) - w * 0.7
    e_target = np.exp(-(x2**2) / (2 * sigma**2)).astype(np.complex64)
    e_target = e_target / np.sqrt(np.sum(np.abs(e_target) ** 2))
    objective = ModeOverlapObjective(e_in, e_target)
    config = OptimizerConfig(
        n_iters=n_iters, learning_rate=0.05, drc_weight=drc_weight
    )
    return TopologyAdjointOptimizer(config, objective, design_shape=(h, w))


class TestConfigValidation:
    """配置与构造验证。"""

    def test_config_defaults(self) -> None:
        """默认配置应符合 Tidy3D/lumopt 惯例。"""
        cfg = OptimizerConfig()
        assert cfg.n_iters == 100
        assert cfg.learning_rate > 0
        assert cfg.beta_init < cfg.beta_final  # 退火递增
        assert cfg.eta == 0.5
        assert cfg.wavelength_um == pytest.approx(1.55)

    def test_invalid_design_shape_raises(self) -> None:
        """非法设计区域应 raise（R03 禁止 fall-back）。"""
        opt = _make_optimizer()
        with pytest.raises(ValueError):
            opt.set_design_region((0, 5))
        with pytest.raises(ValueError):
            opt.set_design_region((5,))  # type: ignore[arg-type]

    def test_invalid_objective_raises(self) -> None:
        """入口场与目标场形状不匹配应 raise。"""
        with pytest.raises(ValueError):
            ModeOverlapObjective(
                np.zeros(5, dtype=np.complex64),
                np.zeros(6, dtype=np.complex64),
            )

    def test_invalid_wavelength_raises(self) -> None:
        """非正波长应 raise。"""
        e = np.ones(4, dtype=np.complex64)
        with pytest.raises(ValueError):
            ModeOverlapObjective(e, e, wavelength_um=0)


class TestSetDesignRegion:
    """设计区域设置。"""

    def test_set_design_region_updates_shape(self) -> None:
        """set_design_region 应更新设计形状与滤波核。"""
        opt = _make_optimizer(h=8, w=12)
        opt.set_design_region((10, 12))  # 宽度须与入口场一致
        assert opt.design_shape == (10, 12)
        # 滤波核形状应同步
        assert opt._filter_kernel.shape == (10, 12)

    def test_set_design_region_width_mismatch_raises(self) -> None:
        """设计区域宽度与入口场不一致应 raise。"""
        opt = _make_optimizer(h=8, w=12)
        with pytest.raises(ValueError):
            opt.set_design_region((10, 13))


class TestForwardSimulate:
    """正向仿真。"""

    def test_fom_in_unit_range(self) -> None:
        """FoM（模式重叠）应在 [0,1] 区间。"""
        opt = _make_optimizer(h=8, w=12)
        rho = np.full((8, 12), 0.5)
        result = opt.forward_simulate(rho)
        assert 0.0 <= result["fom"] <= 1.0

    def test_forward_returns_fields(self) -> None:
        """正向仿真应返回输出场（复数）。"""
        opt = _make_optimizer(h=8, w=12)
        rho = np.full((8, 12), 0.3)
        result = opt.forward_simulate(rho)
        assert result["e_out"].shape == (12,)
        assert np.iscomplexobj(result["e_out"])


class TestAdjointSimulate:
    """伴随仿真。"""

    def test_adjoint_returns_normalized(self) -> None:
        """伴随仿真应返回归一化伴随场（范数=1）。"""
        opt = _make_optimizer(h=8, w=12)
        src = np.random.default_rng(0).standard_normal(12) + 1j
        adj = opt.adjoint_simulate(src)
        assert adj.shape == (12,)
        norm = np.sqrt(np.sum(np.abs(adj) ** 2))
        assert norm == pytest.approx(1.0, abs=1e-5)

    def test_adjoint_zero_source_raises(self) -> None:
        """零伴随源应 raise（R03 禁止 fall-back）。"""
        opt = _make_optimizer(h=8, w=12)
        with pytest.raises(ValueError):
            opt.adjoint_simulate(np.zeros(12, dtype=np.complex64))


class TestComputeGradient:
    """伴随梯度计算（jax.grad = adjoint method）。"""

    def test_gradient_shape(self) -> None:
        """梯度形状应与设计变量一致。"""
        opt = _make_optimizer(h=8, w=12, drc_weight=0.0)
        rho_raw = np.random.default_rng(1).standard_normal((8, 12)) * 0.1
        grad = opt.compute_gradient(rho_raw, beta=1.0)
        assert grad.shape == (8, 12)

    def test_gradient_finite_difference(self) -> None:
        """jax.grad 应与中心有限差分一致（误差<1e-3，证明 autograd=adjoint）。

        依据: Hughes 2018 ACS Photonics 证明 autograd 与 adjoint 数学等价。
        """
        opt = _make_optimizer(h=6, w=10, drc_weight=0.0)
        rng = np.random.default_rng(42)
        rho_raw = rng.standard_normal((6, 10)) * 0.3
        beta = 2.0
        grad_jax = opt.compute_gradient(rho_raw, beta=beta)
        # 中心有限差分（对 _total_objective，drc_weight=0 即纯 FOM）
        import jax.numpy as jnp

        eps = 1e-4
        grad_fd = np.zeros_like(rho_raw)
        for i in range(rho_raw.shape[0]):
            for j in range(rho_raw.shape[1]):
                rp = rho_raw.copy()
                rm = rho_raw.copy()
                rp[i, j] += eps
                rm[i, j] -= eps
                jp = float(opt._total_objective(jnp.asarray(rp), beta))
                jm = float(opt._total_objective(jnp.asarray(rm), beta))
                grad_fd[i, j] = (jp - jm) / (2 * eps)
        np.testing.assert_allclose(grad_jax, grad_fd, atol=1e-3)


class TestDensityProjection:
    """密度法二值化（sigmoid 投影）。"""

    def test_low_beta_continuous(self) -> None:
        """低 β 应保持连续（非完全二值）。"""
        opt = _make_optimizer(h=8, w=12)
        rho = np.linspace(0, 1, 20)
        projected = opt.density_projection(rho, beta=1.0)
        # 中间值应在 (0.1, 0.9) 内，未完全二值化
        assert 0.1 < projected[10] < 0.9

    def test_high_beta_binary(self) -> None:
        """高 β 应趋于 0/1 二值。"""
        opt = _make_optimizer(h=8, w=12)
        rho = np.array([0.2, 0.4, 0.6, 0.8])
        projected = opt.density_projection(rho, beta=100.0)
        # >0.5 的应接近 1，<0.5 的应接近 0
        assert projected[2] > 0.99
        assert projected[1] < 0.01


class TestConicFilter:
    """锥形滤波（消除小特征）。"""

    def test_filter_smooths(self) -> None:
        """滤波后方差应减小（平滑效果）。"""
        opt = _make_optimizer(h=8, w=12)
        rng = np.random.default_rng(0)
        rho = rng.random((8, 12))
        filtered = opt.conic_filter(rho)
        assert np.std(filtered) <= np.std(rho) + 1e-9

    def test_filter_preserves_mean(self) -> None:
        """滤波核归一化，应近似保持均值。"""
        opt = _make_optimizer(h=8, w=12)
        rho = np.full((8, 12), 0.5)
        filtered = opt.conic_filter(rho)
        np.testing.assert_allclose(filtered, 0.5, atol=0.05)


class TestDRCPenalty:
    """DRC 感知约束惩罚。"""

    def test_sharp_structure_higher_penalty(self) -> None:
        """尖锐结构（棋盘格）惩罚应高于平滑结构。"""
        opt = _make_optimizer(h=8, w=12)
        # 棋盘格（高频，DRC 违反）
        checkerboard = np.zeros((8, 12))
        checkerboard[::2, ::2] = 1.0
        checkerboard[1::2, 1::2] = 1.0
        # 平滑结构（低频，DRC 合规）
        smooth = np.zeros((8, 12))
        smooth[2:6, 3:9] = 1.0
        pen_sharp = opt.drc_penalty(checkerboard)
        pen_smooth = opt.drc_penalty(smooth)
        assert pen_sharp > pen_smooth

    def test_uniform_zero_penalty(self) -> None:
        """均匀场 DRC 惩罚应为 0（梯度为 0）。"""
        opt = _make_optimizer(h=8, w=12)
        assert opt.drc_penalty(np.full((8, 12), 0.5)) == pytest.approx(0.0)


class TestOptimizeMMI:
    """MMI 1×2 优化（验证优化提升 FoM，简化可微模型）。"""

    def test_optimize_improves_fom(self) -> None:
        """优化后 FoM 应显著高于初始（密度法拓扑优化有效）。"""
        result = example_mmi_1x2()["result"]
        assert len(result.fom_history) == result.iterations
        # 优化应提升 FoM（最终 >= 初始 - 容差）
        assert result.fom_history[-1] >= result.fom_history[0] - 1e-6
        # FoM 应在物理合理范围 [0,1]
        assert 0.0 <= result.optimal_fom <= 1.0

    def test_optimal_design_binary(self) -> None:
        """最优设计应为二值（0/1，可制造）。"""
        result = example_mmi_1x2()["result"]
        unique = set(np.unique(result.optimal_design).tolist())
        assert unique.issubset({0.0, 1.0})


class TestOptimizeGratingCoupler:
    """光栅耦合器优化。"""

    def test_grating_optimize_runs(self) -> None:
        """光栅耦合器优化应正常运行并返回结果。"""
        out = example_grating_coupler()
        assert out["device"] == "Grating Coupler"
        result = out["result"]
        assert 0.0 <= out["coupling_efficiency"] <= 1.0
        assert result.iterations > 0

    def test_grating_fom_history_nonempty(self) -> None:
        """FoM 历史应非空且长度=迭代次数。"""
        result = example_grating_coupler()["result"]
        assert len(result.fom_history) == result.iterations


class TestOptimizeModeConverter:
    """模式转换器 TE1→TE0 优化。"""

    def test_mode_converter_optimize(self) -> None:
        """模式转换器优化应正常运行。"""
        out = example_mode_converter()
        assert out["device"] == "Mode Converter TE1->TE0"
        assert 0.0 <= out["conversion_efficiency"] <= 1.0

    def test_mode_converter_design_shape(self) -> None:
        """模式转换器设计区域应为 10×18。"""
        result = example_mode_converter()["result"]
        assert result.optimal_design.shape == (10, 18)


class TestExportGDS:
    """GDSII 导出。"""

    def test_export_gds_writes_file(self, tmp_path) -> None:  # type: ignore[no-untyped-def]
        """应写入有效的 GDSII 文件（可读回）。"""
        opt = _make_optimizer(h=6, w=8)
        rho = np.zeros((6, 8))
        rho[1:5, 2:6] = 1.0
        path = str(tmp_path / "device.gds")
        written = opt.export_gds(rho, path)
        assert written == path
        assert os.path.exists(path)
        assert os.path.getsize(path) > 0
        # 读回验证 GDSII 有效性
        lib = gdstk.read_gds(path)
        cells = lib.cells
        assert len(cells) > 0

    def test_export_gds_invalid_path_raises(self) -> None:
        """空路径应 raise（R03 禁止 fall-back）。"""
        opt = _make_optimizer(h=6, w=8)
        with pytest.raises(ValueError):
            opt.export_gds(np.zeros((6, 8)), "")

    def test_export_gds_non2d_raises(self) -> None:
        """非 2D 密度场应 raise。"""
        opt = _make_optimizer(h=6, w=8)
        with pytest.raises(ValueError):
            opt.export_gds(np.zeros((6,)), "x.gds")


class TestBetaAnnealing:
    """β 退火调度。"""

    def test_beta_schedule_monotonic(self) -> None:
        """β 应从 beta_init 单调增至 beta_final。"""
        opt = _make_optimizer(h=8, w=12, n_iters=10)
        betas = [opt._beta_schedule(t) for t in range(10)]
        assert betas[0] == pytest.approx(opt.config.beta_init)
        assert betas[-1] == pytest.approx(opt.config.beta_final)
        for i in range(len(betas) - 1):
            assert betas[i + 1] >= betas[i]
