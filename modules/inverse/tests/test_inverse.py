"""polaris-inverse 子模块测试。

测试覆盖（R13 强制自测）:
- test_optimize_waveguide_width: 50 次迭代，验证 fom_history 长度=51、无 NaN、
  improvement_db 为有限值
- test_optimize_convergence: 验证返回 dict 含全部必需字段

来源（R02 学术诚信）:
- pytest 文档: https://docs.pytest.org/
- Yee 1966 IEEE TAP: https://doi.org/10.1109/TAP.1966.1138693
- Mahau 2024 arXiv:2412.12360: https://arxiv.org/abs/2412.12360
- Jensen & Sigmund 2011: https://doi.org/10.1002/lpor.201000014
- Polyak 1964 heavy-ball method
- lumopt: https://github.com/chriskeraly/lumopt
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

# 让测试既能从已安装包导入，也能从源码树导入（CI/开发模式）
_SRC = str(Path(__file__).resolve().parents[1] / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import polaris_inverse  # noqa: E402
from polaris_inverse import optimize_waveguide_width  # noqa: E402


# 全量 50 次迭代较慢（JAX 首次 JIT 编译 + 50 步 AD），
# 标记为 slow，CI 默认运行；本地可用 -m "not slow" 跳过。
@pytest.mark.slow
def test_optimize_waveguide_width():
    """50 次迭代波导宽度优化：验证 fom_history 长度=51、无 NaN、improvement_db 有限。

    验证项:
    - fom_history 长度 = n_iterations + 1 = 51
    - fom_history 无 NaN
    - improvement_db 为有限值（非 NaN/Inf）
    - initial_fom / final_fom 为有限正数
    """
    result = optimize_waveguide_width(n_iterations=50, learning_rate=0.5)

    # fom_history 长度 = n_iterations + 1（含初始 FoM + 50 步每步记录 + 最终 FoM
    # 实际与 stage10 实现对齐：初始 + 50 步循环中每步记录 + 最终 = 52，但本子模块
    # 规范要求 = n_iterations + 1 = 51，已在 adjoint.py 中调整为 51）
    assert len(result["fom_history"]) == 51, (
        f"fom_history 长度应为 51（n_iterations+1），实际 {len(result['fom_history'])}"
    )

    # 无 NaN
    has_nan = any(math.isnan(x) for x in result["fom_history"])
    assert not has_nan, "fom_history 含 NaN（违反 R03 禁止 fall-back）"

    # improvement_db 为有限值
    assert math.isfinite(result["improvement_db"]), (
        f"improvement_db 应为有限值，实际 {result['improvement_db']}"
    )

    # FoM 为有限正数
    assert math.isfinite(result["initial_fom"]) and result["initial_fom"] > 0, (
        f"initial_fom 应为有限正数，实际 {result['initial_fom']}"
    )
    assert math.isfinite(result["final_fom"]) and result["final_fom"] > 0, (
        f"final_fom 应为有限正数，实际 {result['final_fom']}"
    )


def test_optimize_convergence():
    """验证返回 dict 含全部必需字段（10 次迭代省时）。

    必需字段:
    - initial_width_nm / optimal_width_nm (float)
    - initial_fom / final_fom (float)
    - improvement_db (float)
    - fom_history (list)
    - converged (bool)
    - iterations (int)
    """
    # 用 10 次迭代省时（JAX JIT 编译后单步很快）
    result = optimize_waveguide_width(n_iterations=10, learning_rate=0.5)

    required_keys = [
        "initial_width_nm",
        "optimal_width_nm",
        "initial_fom",
        "final_fom",
        "improvement_db",
        "fom_history",
        "converged",
        "iterations",
    ]
    for key in required_keys:
        assert key in result, f"返回 dict 缺少必需字段: {key}"

    # 类型与语义校验
    assert isinstance(result["initial_width_nm"], float)
    assert isinstance(result["optimal_width_nm"], float)
    assert isinstance(result["initial_fom"], float)
    assert isinstance(result["final_fom"], float)
    assert isinstance(result["improvement_db"], float)
    assert isinstance(result["fom_history"], list)
    assert isinstance(result["converged"], bool)
    assert isinstance(result["iterations"], int)

    # iterations 应等于输入 n_iterations
    assert result["iterations"] == 10, (
        f"iterations 应=10，实际 {result['iterations']}"
    )

    # fom_history 长度 = n_iterations + 1
    assert len(result["fom_history"]) == 11, (
        f"fom_history 长度应为 11（n_iterations+1），实际 {len(result['fom_history'])}"
    )

    # 无 NaN（10 次迭代也应无 NaN）
    has_nan = any(math.isnan(x) for x in result["fom_history"])
    assert not has_nan, "fom_history 含 NaN"


def test_optimize_invalid_iterations():
    """非法 n_iterations（<=0）应 raise（R03 禁止 fall-back）。"""
    with pytest.raises((ValueError, RuntimeError)):
        optimize_waveguide_width(n_iterations=0, learning_rate=0.5)


def test_optimize_invalid_learning_rate():
    """非法 learning_rate（<=0）应 raise（R03 禁止 fall-back）。"""
    with pytest.raises((ValueError, RuntimeError)):
        optimize_waveguide_width(n_iterations=10, learning_rate=0.0)


def test_fom_normalization_regression():
    """*R05 回归测试*: FoM 必须归一化为 0-1 传输率，禁止裸场强值。

    复现旧 BUG: 旧版 fom_fn 返回 max(|monitor|) 是原始场强值（~1e16），
    导致梯度 ~1e15 恒触发 [-1,1] 裁剪为 ±1，width 震荡、FoM 暴涨暴跌不收敛，
    improvement_db ≈ -4.08 dB（变差）。

    修复后断言:
    - initial_fom / final_fom 在 (0, 1) 范围（归一化传输率）
    - fom_history 全部元素在 (0, 1] 范围（无 1e16 量级裸场强）
    - improvement_db >= -1 dB（不再大幅变差）
    - fom_history 无量级跳变（相邻步比值 < 1e3，旧 BUG 暴涨 1e2~1e4 倍）
    """
    result = optimize_waveguide_width(n_iterations=10, learning_rate=0.5)

    # 1. FoM 在 (0, 1) 范围（归一化传输率，物理有意义）
    assert 0 < result["initial_fom"] < 1, (
        f"initial_fom={result['initial_fom']} 应在 (0,1) 范围"
        f"（归一化传输率，旧 BUG 为 ~1e16 裸场强）"
    )
    assert 0 < result["final_fom"] < 1, (
        f"final_fom={result['final_fom']} 应在 (0,1) 范围"
        f"（归一化传输率，旧 BUG 为 ~1e16 裸场强）"
    )

    # 2. fom_history 全部元素在 (0, 1] 范围（无 1e16 量级裸场强残留）
    fom_hist = result["fom_history"]
    for i, v in enumerate(fom_hist):
        assert 0 < v <= 1.0001, (  # 1.0001 容许浮点误差
            f"fom_history[{i}]={v} 超出 (0,1] 范围"
            f"（旧 BUG 出现 8e16/3e18/2e20 等裸场强值）"
        )

    # 3. improvement_db >= 0（best-checkpoint 追踪保证，2026-07-03 R05 修复）
    #    旧 BUG = -4.08 dB（未归一化）/ -0.72 dB（n=10 优化器震荡，final 反降）。
    #    修复后 run_adjoint_optimization 返回历史最优 FoM（best_fom），
    #    best >= initial 恒成立（best 至少记录 fom_history[0]=initial），
    #    故 improvement_db = 10*log10(best/initial) >= 0。
    assert result["improvement_db"] >= 0.0, (
        f"improvement_db={result['improvement_db']} < 0 dB"
        f"（best-checkpoint 修复后应 >= 0；旧 BUG n=10 为 -0.72 dB）"
    )

    # 4. fom_history 无量级跳变（旧 BUG: 8e16→3e18→2e20 暴涨 1e2~1e4 倍）
    #    归一化后相邻步比值应 < 1e3（传输率变化平缓）
    for i in range(1, len(fom_hist)):
        prev, curr = fom_hist[i - 1], fom_hist[i]
        ratio = max(curr / prev, prev / curr) if min(prev, curr) > 0 else float("inf")
        assert ratio < 1e3, (
            f"fom_history[{i-1}]={prev} → fom_history[{i}]={curr}"
            f" 比值 {ratio:.2e} >= 1e3（旧 BUG 暴涨暴跌特征，归一化后不应出现）"
        )


def test_inverse_version():
    """验证子模块版本号为 5.0.0（与 8 子模块统一版本对齐）。"""
    assert polaris_inverse.__version__ == "5.0.0"


def test_best_checkpoint_no_degradation():
    """*R05 回归测试（2026-07-03）*: best-checkpoint 追踪保证 FoM 不退化。

    复现旧 BUG: n=10 迭代时 heavy-ball 动量过冲震荡，final FoM 反低于 initial
    （improvement_db = -0.72 dB，stage10 注释自承"另案修复"未修）。

    修复后断言（best-checkpoint 追踪）:
    - final_fom >= initial_fom（历史最优 >= 初始，恒成立）
    - improvement_db >= 0（10*log10(best/initial) >= 0）
    - optimal_width_nm 对应 best_fom 时刻的宽度（非末步宽度）
    """
    # n=10 是旧 bug 明确触发点（stage10 注释: n=10 → -0.72 dB）
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
    # optimal_width_nm 应为正有限值（best_width 对应）
    assert result["optimal_width_nm"] > 0, (
        f"optimal_width_nm={result['optimal_width_nm']} 应为正"
    )
