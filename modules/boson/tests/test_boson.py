"""polaris-boson 子模块深度测试（v5.0，覆盖全 API）。

测试覆盖（24 个 pytest）:
- permanent_glynn_gray: 2×2/3×3/复数/全 1/单位/1×1/非方阵 raise/与行列式区别
- clements_unitary: 酉性/可复现/不同 n_modes/输出格式/n_modes=1/n_modes<1 raise
- boson_sampling: 2 模式 2 光子/4 模式 2 光子/真空输入/输入维度不匹配 raise/负光子 raise
- hom_interference: θ=0 dip=1.0/大 θ 经典极限/dip 单调递减/verified 一致性/符合计数率范围

R02 学术诚信（docstring 含 ≥5 文献 URL）:
- Aaronson & Arkhipov, STOC 2011, 玻色采样
  https://arxiv.org/abs/0910.4698
- Glynn, Eur. J. Comb. 2010, 积和式算法
  https://doi.org/10.1016/j.ejc.2010.01.010
- Clements et al., Optica 2016, Clements 分解
  https://opg.optica.org/optica/fulltext.cfm?uri=optica-3-12-1460
- Hong, Ou, Mandel, PRL 1987, HOM 干涉
  https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.59.2044
- Knill, Laflamme, Milburn, Nature 2001, KLM 方案
  https://www.nature.com/articles/35051009
- Björklund 2012, "Counting Perfect Matchings as Fast as Ryser"
  https://arxiv.org/abs/1203.5687
- pytest 文档: https://docs.pytest.org/

规则依据: R02 学术诚信 / R03 禁止 fall-back / R05 无 TODO / R04 纯 NumPy
"""

from __future__ import annotations

import itertools
import math
import sys
from pathlib import Path

import numpy as np
import pytest

# 让测试既能从已安装包导入，也能从源码树导入（CI/开发模式）
_SRC = str(Path(__file__).resolve().parents[1] / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import polaris_boson  # noqa: E402
from polaris_boson import (  # noqa: E402
    boson_sampling,
    clements_unitary,
    hom_interference,
    permanent_glynn_gray,
)


# ===========================================================================
# 1. permanent_glynn_gray — 矩阵积和式（Glynn-Gray 公式）
# ===========================================================================
def test_permanent_2x2_real():
    """2×2 实矩阵: Per([[1,2],[3,4]]) = 1*4 + 2*3 = 10。

    积和式无行列式那样的符号翻转（Glynn 2010）。
    """
    per = permanent_glynn_gray([[1, 2], [3, 4]])
    assert abs(per - 10.0) < 1e-9, f"Per 期望 10.0，实际 {per}"


def test_permanent_3x3_real():
    """3×3 实矩阵: 与暴力枚举所有排列的结果一致。

    Per(A) = Σ_{σ∈S_n} Π_i a_{i,σ(i)}（定义式，Glynn 2010 eq.1）。
    """
    A = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
    # 暴力枚举 3! = 6 种排列
    expected = 0.0
    for perm in itertools.permutations(range(3)):
        prod = 1.0
        for i in range(3):
            prod *= A[i][perm[i]]
        expected += prod
    per = permanent_glynn_gray(A)
    assert abs(per - expected) < 1e-9, f"3×3 Per 期望 {expected}，实际 {per}"


def test_permanent_complex():
    """复数矩阵: Per([[1,1j],[1j,1]]) = 1*1 + 1j*1j = 1 - 1 = 0。"""
    per = permanent_glynn_gray([[1, 1j], [1j, 1]])
    assert abs(per) < 1e-9, f"复数 Per 期望 0，实际 {per}"


def test_permanent_identity():
    """单位矩阵: Per(I_n) = 1（唯一完美匹配，主对角线乘积）。"""
    for n in (1, 2, 3, 4):
        I = np.eye(n)
        per = permanent_glynn_gray(I)
        assert abs(per - 1.0) < 1e-9, f"Per(I_{n}) 期望 1.0，实际 {per}"


def test_permanent_all_ones():
    """全 1 矩阵: Per(J_n) = n!（每个排列贡献 1，共 n! 项）。"""
    for n in (1, 2, 3, 4):
        J = np.ones((n, n))
        per = permanent_glynn_gray(J)
        expected = math.factorial(n)
        assert abs(per - expected) < 1e-9, (
            f"Per(J_{n}) 期望 {expected}，实际 {per}"
        )


def test_permanent_vs_determinant():
    """积和式 ≠ 行列式（无符号翻转）。

    [[1,2],[3,4]]: det = 1*4 - 2*3 = -2, Per = 1*4 + 2*3 = 10。
    """
    A = [[1, 2], [3, 4]]
    per = permanent_glynn_gray(A)
    det = 1 * 4 - 2 * 3
    assert abs(per - 10.0) < 1e-9
    assert det == -2
    assert abs(per - det) > 1e-9, "Per 与 det 应不同（无符号翻转）"


def test_permanent_1x1():
    """1×1 矩阵: Per([[a]]) = a。"""
    per = permanent_glynn_gray([[3.14]])
    assert abs(per - 3.14) < 1e-12, f"1×1 Per 期望 3.14，实际 {per}"


def test_permanent_non_square_raises():
    """非方阵 raise ValueError（R03 禁止 fall-back）。"""
    with pytest.raises(ValueError):
        permanent_glynn_gray([[1, 2, 3], [4, 5, 6]])  # 2×3 非方阵


# ===========================================================================
# 2. clements_unitary — Clements 酉矩阵分解
# ===========================================================================
def test_clements_unitarity():
    """Clements 4×4 酉矩阵: U @ U† = I，误差 < 1e-10。

    来源: Clements et al., Optica 2016.
    """
    U_list = clements_unitary(4, seed=42)
    U = np.array([[complex(r, i) for r, i in row] for row in U_list])
    err = float(np.max(np.abs(U @ U.conj().T - np.eye(4))))
    assert err < 1e-10, f"酉性误差 {err} ≥ 1e-10"


def test_clements_reproducible():
    """同种子同输出（可复现）。"""
    U1 = clements_unitary(4, seed=42)
    U2 = clements_unitary(4, seed=42)
    assert U1 == U2, "同 seed 须返回相同酉矩阵"


def test_clements_different_seeds_differ():
    """不同种子产生不同酉矩阵（保证随机性）。"""
    U1 = clements_unitary(4, seed=42)
    U2 = clements_unitary(4, seed=7)
    assert U1 != U2, "不同 seed 应产生不同酉矩阵"


def test_clements_different_n_modes_all_unitary():
    """n_modes = 2/3/4/5 均生成酉矩阵。"""
    for n in (2, 3, 4, 5):
        U_list = clements_unitary(n, seed=42)
        U = np.array([[complex(r, i) for r, i in row] for row in U_list])
        err = float(np.max(np.abs(U @ U.conj().T - np.eye(n))))
        assert err < 1e-10, f"n_modes={n} 酉性误差 {err} ≥ 1e-10"


def test_clements_output_format():
    """输出格式: list of list of [real, imag] 二元组。"""
    U = clements_unitary(3, seed=42)
    assert isinstance(U, list)
    assert len(U) == 3
    for row in U:
        assert isinstance(row, list)
        assert len(row) == 3
        for elem in row:
            assert isinstance(elem, list)
            assert len(elem) == 2, f"元素须为 [real, imag]，得到 {elem}"


def test_clements_n_modes_1():
    """n_modes=1: 1×1 酉矩阵，外层 1 行 × 1 元素 [real, imag] = [[[1.0, 0.0]]]。"""
    U = clements_unitary(1, seed=42)
    # 1×1 矩阵: 外层 list 1 行，行内 1 个元素 [1.0, 0.0]
    assert U == [[[1.0, 0.0]]], f"n_modes=1 应返回 [[[1,0]]]，得到 {U}"


def test_clements_n_modes_lt_1_raises():
    """n_modes < 1 raise RuntimeError（R03 禁止 fall-back）。"""
    with pytest.raises(RuntimeError):
        clements_unitary(0, seed=42)
    with pytest.raises(RuntimeError):
        clements_unitary(-1, seed=42)


# ===========================================================================
# 3. boson_sampling — 玻色采样（Aaronson-Arkhipov 2011）
# ===========================================================================
def test_boson_sampling_2mode_prob_sum():
    """2 模式 2 光子: prob_sum = 1.0, n_outputs = 3。

    输出态数 = C(n_photons + n_modes - 1, n_photons) = C(3,2) = 3。
    """
    U = clements_unitary(n_modes=2, seed=42)
    result = boson_sampling(U, [1, 1])
    assert abs(result["prob_sum"] - 1.0) < 1e-6
    assert result["n_outputs"] == 3
    assert len(result["prob_distribution"]) == 3
    assert all(p >= 0.0 for p in result["prob_distribution"])


def test_boson_sampling_4mode_2photons():
    """4 模式 2 光子: n_outputs = C(5,2) = 10, prob_sum = 1.0。"""
    U = clements_unitary(4, seed=42)
    result = boson_sampling(U, [1, 1, 0, 0])
    assert abs(result["prob_sum"] - 1.0) < 1e-6
    assert result["n_outputs"] == 10
    assert len(result["prob_distribution"]) == 10


def test_boson_sampling_vacuum_input():
    """真空输入 [0,0,...]: 唯一输出真空态，概率 1.0。"""
    U = clements_unitary(3, seed=42)
    result = boson_sampling(U, [0, 0, 0])
    assert result["prob_distribution"] == [1.0]
    assert result["prob_sum"] == 1.0
    assert result["n_outputs"] == 1


def test_boson_sampling_single_photon():
    """单光子输入: 概率分布 = |U[i,0]|² 集合（与酉矩阵列模方一致），和 = 1。

    _generate_output_states(1, 3) 顺序为 (0,0,1),(0,1,0),(1,0,0)，
    对应 |U[2,0]|²,|U[1,0]|²,|U[0,0]|²；用排序比较避免顺序依赖。
    """
    U = clements_unitary(3, seed=42)
    result = boson_sampling(U, [1, 0, 0])
    assert result["n_outputs"] == 3
    assert abs(result["prob_sum"] - 1.0) < 1e-6
    # 单光子输出概率 = |U[i,0]|²（输入模式 0），排序后应一致
    U_np = np.array([[complex(r, i) for r, i in row] for row in U])
    expected = sorted(abs(U_np[i, 0]) ** 2 for i in range(3))
    got = sorted(result["prob_distribution"])
    for g, e in zip(got, expected):
        assert abs(g - e) < 1e-9, f"单光子概率 {g} ≠ |U|² {e}"


def test_boson_sampling_input_mismatch_raises():
    """input_state 长度 ≠ 模式数 raise RuntimeError（R03）。"""
    U = clements_unitary(2, seed=42)
    with pytest.raises(RuntimeError):
        boson_sampling(U, [1, 1, 1])  # 长度 3 ≠ 模式数 2


def test_boson_sampling_negative_photons_raises():
    """input_state 含负值 raise RuntimeError（R03）。"""
    U = clements_unitary(2, seed=42)
    with pytest.raises(RuntimeError):
        boson_sampling(U, [1, -1])


def test_boson_sampling_returns_dict_keys():
    """返回 dict 含 prob_distribution / prob_sum / n_outputs 三键。"""
    U = clements_unitary(2, seed=42)
    result = boson_sampling(U, [1, 1])
    assert set(result.keys()) == {"prob_distribution", "prob_sum", "n_outputs"}


# ===========================================================================
# 4. hom_interference — HOM 双光子干涉
# ===========================================================================
def test_hom_dip_at_zero():
    """θ=0: 完全不可区分 → dip_depth=1.0, coincidence_prob=0, verified=True。

    来源: Hong, Ou, Mandel, PRL 59, 2044 (1987).
    """
    result = hom_interference(0.0)
    assert abs(result["dip_depth"] - 1.0) < 1e-9
    assert abs(result["coincidence_prob"]) < 1e-9
    assert result["verified"] is True


def test_hom_classical_limit():
    """θ→∞: 完全可分辨 → dip_depth→0, coincidence_prob→0.5（经典极限）。"""
    result = hom_interference(100.0)  # 大 θ 近似经典
    assert result["dip_depth"] < 1e-9, f"大 θ dip_depth 应→0，实际 {result['dip_depth']}"
    assert abs(result["coincidence_prob"] - 0.5) < 1e-9, (
        f"大 θ coincidence_prob 应→0.5，实际 {result['coincidence_prob']}"
    )


def test_hom_dip_monotonic_decrease():
    """dip_depth 随 θ 单调递减（高斯重叠 exp(-θ²/2) 单调下降）。"""
    thetas = [0.0, 0.5, 1.0, 2.0, 4.0]
    dips = [hom_interference(t)["dip_depth"] for t in thetas]
    for i in range(len(dips) - 1):
        assert dips[i] > dips[i + 1], (
            f"dip_depth 应单调递减: θ={thetas[i]}→{dips[i]}, "
            f"θ={thetas[i+1]}→{dips[i+1]}"
        )


def test_hom_verified_always_true():
    """verified 在合法 θ 下均为 True（输出在物理合法域内）。"""
    for theta in (0.0, 0.5, 1.0, 2.0, 10.0):
        result = hom_interference(theta)
        assert result["verified"] is True, (
            f"θ={theta} verified 应为 True，实际 {result['verified']}"
        )


def test_hom_verified_false_on_nan():
    """R392 回归: θ=NaN 时 verified=False（非恒真校验，防假验证复发）。

    R390 标准（klm/gates.py 同）: verified 必须是能失败的真实校验。
    NaN 输入 → exp(NaN)=NaN → 值域比较恒 False → verified=False。
    θ=±Inf 是合法极限（exp(-Inf)=0 → 经典极限），verified 仍为 True。
    """
    result = hom_interference(float("nan"))
    assert result["verified"] is False, (
        f"θ=NaN verified 应为 False，实际 {result['verified']}"
    )
    # ±Inf 合法极限: 经典极限输出 (P=0.5, dip=0)，verified=True
    for inf_theta in (float("inf"), float("-inf")):
        result = hom_interference(inf_theta)
        assert result["verified"] is True, (
            f"θ={inf_theta}（合法经典极限）verified 应为 True，"
            f"实际 {result['verified']}"
        )
        assert result["dip_depth"] == 0.0
        assert result["coincidence_prob"] == 0.5


def test_hom_coincidence_range():
    """coincidence_prob ∈ [0, 0.5]（量子下界 0，经典上界 0.5）。"""
    for theta in (0.0, 0.5, 1.0, 2.0, 10.0, 100.0):
        result = hom_interference(theta)
        assert 0.0 <= result["coincidence_prob"] <= 0.5 + 1e-12, (
            f"θ={theta} coincidence_prob 应 ∈ [0, 0.5]，"
            f"实际 {result['coincidence_prob']}"
        )


def test_hom_dip_range():
    """dip_depth ∈ [0, 1]（0=经典，1=完全量子干涉）。"""
    for theta in (0.0, 0.5, 1.0, 2.0, 10.0, 100.0):
        result = hom_interference(theta)
        assert 0.0 <= result["dip_depth"] <= 1.0 + 1e-12, (
            f"θ={theta} dip_depth 应 ∈ [0, 1]，实际 {result['dip_depth']}"
        )


def test_hom_formula_correctness():
    """高斯重叠模型数值验证: dip_depth = exp(-θ²/2)。"""
    for theta in (0.0, 0.5, 1.0, 2.0):
        result = hom_interference(theta)
        expected_dip = math.exp(-(theta ** 2) / 2.0)
        assert abs(result["dip_depth"] - expected_dip) < 1e-9, (
            f"θ={theta} dip_depth 期望 {expected_dip}，实际 {result['dip_depth']}"
        )


def test_hom_return_keys():
    """返回 dict 含 coincidence_prob / dip_depth / verified 三键。"""
    result = hom_interference(1.0)
    assert set(result.keys()) == {"coincidence_prob", "dip_depth", "verified"}


# ===========================================================================
# 5. 模块元信息
# ===========================================================================
def test_boson_version():
    """子模块版本号 5.1.0（v5.0 拆分后统一）。"""
    assert polaris_boson.__version__ == "5.1.0"


def test_boson_api_exports():
    """__all__ 导出 4 个稳定 API。"""
    assert set(polaris_boson.__all__) == {
        "boson_sampling",
        "clements_unitary",
        "hom_interference",
        "permanent_glynn_gray",
        "__version__",
    }
