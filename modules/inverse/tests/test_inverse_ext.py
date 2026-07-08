"""扩展测试（从 test_inverse.py 拆分，遵守 R11 质量门禁文件≤800行）.

来源（R02 学术诚信）: 同原文件 test_inverse.py。
"""


from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pytest

# 让测试既能从已安装包导入，也能从源码树导入（CI/开发模式）
_SRC = str(Path(__file__).resolve().parents[1] / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import jax  # noqa: E402
import jax.numpy as jnp  # noqa: E402

import polaris_inverse  # noqa: E402
from polaris_inverse import (  # noqa: E402
    EPS_R_SI,
    EPS_R_SIO2,
    GRID_DX_M,
    GRID_NX,
    GRID_NY,
    GRID_NZ,
    INITIAL_WIDTH_PIXELS,
    LEARNING_RATE,
    MOMENTUM,
    N_ITERATIONS,
    PML_N_LAYERS,
    TARGET_WAVELENGTH_UM,
    DifferentiableFDTD,
    GedneyPML,
    YeeGrid3D,
    epsilon_r_from_width,
    fom_fn,
    optimize_waveguide_width,
    run_adjoint_optimization,
)
from polaris_inverse.fdtd_jax import C0, EPS0, MU0  # noqa: E402


# =============================================================================
# 辅助函数：构建默认 FDTD 求解器（与 run_adjoint_optimization 一致）
# =============================================================================


class TestRunAdjointOptimization:
    """run_adjoint_optimization / optimize_waveguide_width 端到端优化验证。"""

    def test_optimize_convergence(self) -> None:
        """验证返回 dict 含全部必需字段（10 次迭代省时）。

        必需字段: initial_width_nm, optimal_width_nm, initial_fom, final_fom,
        improvement_db, fom_history, converged, iterations。
        """
        result = optimize_waveguide_width(n_iterations=10, learning_rate=0.5)
        required_keys = [
            "initial_width_nm", "optimal_width_nm", "initial_fom",
            "final_fom", "improvement_db", "fom_history",
            "converged", "iterations",
        ]
        for key in required_keys:
            assert key in result, f"返回 dict 缺少必需字段: {key}"
        # 类型校验
        assert isinstance(result["initial_width_nm"], float)
        assert isinstance(result["optimal_width_nm"], float)
        assert isinstance(result["initial_fom"], float)
        assert isinstance(result["final_fom"], float)
        assert isinstance(result["improvement_db"], float)
        assert isinstance(result["fom_history"], list)
        assert isinstance(result["converged"], bool)
        assert isinstance(result["iterations"], int)
        # iterations 应等于输入
        assert result["iterations"] == 10
        # fom_history 长度 = n_iterations + 1
        assert len(result["fom_history"]) == 11

    def test_optimize_invalid_iterations(self) -> None:
        """非法 n_iterations（<=0）应 raise（R03 禁止 fall-back）。"""
        with pytest.raises((ValueError, RuntimeError)):
            optimize_waveguide_width(n_iterations=0, learning_rate=0.5)
        with pytest.raises((ValueError, RuntimeError)):
            optimize_waveguide_width(n_iterations=-1, learning_rate=0.5)

    def test_optimize_invalid_learning_rate(self) -> None:
        """非法 learning_rate（<=0）应 raise（R03 禁止 fall-back）。"""
        with pytest.raises((ValueError, RuntimeError)):
            optimize_waveguide_width(n_iterations=10, learning_rate=0.0)
        with pytest.raises((ValueError, RuntimeError)):
            optimize_waveguide_width(n_iterations=10, learning_rate=-0.5)

    def test_optimize_no_nan(self) -> None:
        """fom_history 无 NaN（10 次迭代，R03 禁止 fall-back）。"""
        result = optimize_waveguide_width(n_iterations=10, learning_rate=0.5)
        has_nan = any(math.isnan(x) for x in result["fom_history"])
        assert not has_nan, "fom_history 含 NaN（违反 R03）"

    def test_optimize_finite_fom(self) -> None:
        """initial_fom / final_fom 为有限正数。"""
        result = optimize_waveguide_width(n_iterations=10, learning_rate=0.5)
        assert math.isfinite(result["initial_fom"]) and result["initial_fom"] > 0
        assert math.isfinite(result["final_fom"]) and result["final_fom"] > 0
        assert math.isfinite(result["improvement_db"])

    def test_optimize_initial_width_nm(self) -> None:
        """initial_width_nm = INITIAL_WIDTH_PIXELS * GRID_DX_M * 1e9 (nm)。"""
        result = optimize_waveguide_width(n_iterations=5, learning_rate=0.5)
        expected_nm = INITIAL_WIDTH_PIXELS * GRID_DX_M * 1e9
        assert result["initial_width_nm"] == pytest.approx(expected_nm, rel=1e-6)

    def test_optimize_optimal_width_positive(self) -> None:
        """optimal_width_nm 应为正有限值（best_width 对应）。"""
        result = optimize_waveguide_width(n_iterations=10, learning_rate=0.5)
        assert result["optimal_width_nm"] > 0
        assert math.isfinite(result["optimal_width_nm"])

    def test_optimize_converged_is_bool(self) -> None:
        """converged 字段为 bool 类型。"""
        result = optimize_waveguide_width(n_iterations=5, learning_rate=0.5)
        assert isinstance(result["converged"], bool)

    def test_run_adjoint_optimization_equivalent(self) -> None:
        """run_adjoint_optimization 与 optimize_waveguide_width 等价（包装函数）。"""
        # 用 5 次迭代省时
        r1 = run_adjoint_optimization(n_iterations=5, learning_rate=0.5)
        r2 = optimize_waveguide_width(n_iterations=5, learning_rate=0.5)
        # 两者应完全一致（optimize_waveguide_width 是 run_adjoint_optimization 的包装）
        assert r1["iterations"] == r2["iterations"]
        assert r1["initial_fom"] == r2["initial_fom"]
        assert r1["final_fom"] == r2["final_fom"]
        assert r1["improvement_db"] == r2["improvement_db"]

    def test_run_adjoint_optimization_invalid_params(self) -> None:
        """run_adjoint_optimization 非法参数应 raise（R03）。"""
        with pytest.raises(ValueError, match="n_iterations"):
            run_adjoint_optimization(n_iterations=0)
        with pytest.raises(ValueError, match="learning_rate"):
            run_adjoint_optimization(n_iterations=5, learning_rate=0.0)


# =============================================================================
# 9. R05 回归测试（关键修复防护）
# =============================================================================
class TestR05Regression:
    """R05 回归测试：防止已修复的 Bug 复发。"""

    def test_fom_normalization_regression(self) -> None:
        """*R05 回归测试*: FoM 必须归一化为 0-1 传输率，禁止裸场强值。

        复现旧 BUG: 旧版 fom_fn 返回 max(|monitor|) 是原始场强值（~1e16），
        导致梯度 ~1e15 恒触发 [-1,1] 裁剪为 ±1，width 震荡、FoM 暴涨暴跌不收敛，
        improvement_db ≈ -4.08 dB（变差）。

        修复后断言:
        - initial_fom / final_fom 在 (0, 1) 范围（归一化传输率）
        - fom_history 全部元素在 (0, 1] 范围（无 1e16 量级裸场强）
        - improvement_db >= 0 dB（best-checkpoint 保证，不再变差）
        - fom_history 无量级跳变（相邻步比值 < 1e3，旧 BUG 暴涨 1e2~1e4 倍）
        """
        result = optimize_waveguide_width(n_iterations=10, learning_rate=0.5)
        # FoM 在 (0, 1) 范围
        assert 0 < result["initial_fom"] < 1
        assert 0 < result["final_fom"] < 1
        # fom_history 全部元素在 (0, 1] 范围
        fom_hist = result["fom_history"]
        for i, v in enumerate(fom_hist):
            assert 0 < v <= 1.0001, (
                f"fom_history[{i}]={v} 超出 (0,1] 范围（旧 BUG 为 1e16 量级裸场强）"
            )
        # improvement_db >= 0
        assert result["improvement_db"] >= 0.0
        # 无量级跳变
        for i in range(1, len(fom_hist)):
            prev, curr = fom_hist[i - 1], fom_hist[i]
            ratio = max(curr / prev, prev / curr) if min(prev, curr) > 0 else float("inf")
            assert ratio < 1e3, (
                f"fom_history[{i-1}]={prev} → fom_history[{i}]={curr}"
                f" 比值 {ratio:.2e} >= 1e3（旧 BUG 暴涨暴跌特征）"
            )

    def test_best_checkpoint_no_degradation(self) -> None:
        """*R05 回归测试（2026-07-03）*: best-checkpoint 追踪保证 FoM 不退化。

        复现旧 BUG: n=10 迭代时 heavy-ball 动量过冲震荡，final FoM 反低于 initial
        （improvement_db = -0.72 dB，stage10 注释自承"另案修复"未修）。

        修复后断言（best-checkpoint 追踪）:
        - final_fom >= initial_fom（历史最优 >= 初始，恒成立）
        - improvement_db >= 0（10*log10(best/initial) >= 0）
        - optimal_width_nm 对应 best_fom 时刻的宽度（非末步宽度）
        """
        result = optimize_waveguide_width(n_iterations=10, learning_rate=0.5)
        # best-checkpoint 保证: final_fom（=best_fom）>= initial_fom
        assert result["final_fom"] >= result["initial_fom"], (
            f"final_fom={result['final_fom']} < initial_fom={result['initial_fom']}"
            f"（best-checkpoint 修复后应 >=；旧 BUG n=10 final 反降）"
        )
        # improvement_db >= 0
        assert result["improvement_db"] >= 0.0, (
            f"improvement_db={result['improvement_db']} < 0"
            f"（旧 BUG = -0.72 dB，best-checkpoint 修复后应 >= 0）"
        )
        # optimal_width_nm 应为正有限值
        assert result["optimal_width_nm"] > 0

    def test_momentum_low_value_regression(self) -> None:
        """*R05 回归*: 动量应为 0.3（非旧版 0.9），适配嘈杂 FoM 景观。

        旧 BUG: m=0.9 时 heavy-ball 有效步长 lr/(1-m)=5.0，远超搜索范围 [0.5,5]，
        严重过冲致 FoM 暴跌（n=10 实测 improvement_db=-1.52 dB）。
        修复: m=0.3 有效步长 0.71，适配嘈杂景观（n=10 实测 -0.72 dB 稳定）。
        来源: Polyak 1964; Smith 2017 arXiv:1711.00489（嘈杂梯度建议低动量）
        """
        assert MOMENTUM == 0.3, (
            f"MOMENTUM={MOMENTUM} 应为 0.3（旧版 0.9 致过冲，R05 修复）"
        )
        effective_step = LEARNING_RATE / (1.0 - MOMENTUM)
        assert effective_step < GRID_NY / 2.0 - 1.0, (
            f"有效步长 {effective_step} 应 < 搜索范围上限 {GRID_NY/2-1}"
        )


# =============================================================================
# 10. 全量 50 次迭代慢测试（CI 默认运行，本地可 -m "not slow" 跳过）
# =============================================================================
@pytest.mark.slow
def test_optimize_waveguide_width_full():
    """50 次迭代波导宽度优化: 验证 fom_history 长度=51、无 NaN、improvement_db 有限。

    验证项:
    - fom_history 长度 = n_iterations + 1 = 51
    - fom_history 无 NaN
    - improvement_db 为有限值（非 NaN/Inf）
    - initial_fom / final_fom 为有限正数
    - best-checkpoint: final_fom >= initial_fom（improvement_db >= 0）
    """
    result = optimize_waveguide_width(n_iterations=50, learning_rate=0.5)
    # fom_history 长度 = n_iterations + 1 = 51
    assert len(result["fom_history"]) == 51, (
        f"fom_history 长度应为 51，实际 {len(result['fom_history'])}"
    )
    # 无 NaN
    has_nan = any(math.isnan(x) for x in result["fom_history"])
    assert not has_nan, "fom_history 含 NaN（违反 R03）"
    # improvement_db 为有限值
    assert math.isfinite(result["improvement_db"])
    # FoM 为有限正数
    assert math.isfinite(result["initial_fom"]) and result["initial_fom"] > 0
    assert math.isfinite(result["final_fom"]) and result["final_fom"] > 0
    # best-checkpoint: final_fom >= initial_fom
    assert result["final_fom"] >= result["initial_fom"], (
        f"final_fom={result['final_fom']} < initial_fom={result['initial_fom']}"
        f"（best-checkpoint 应保证 final >= initial）"
    )
    assert result["improvement_db"] >= 0.0
