"""polaris-boson 子模块测试。

测试覆盖（≥4 个 pytest）:
- test_permanent_2x2: 2×2 矩阵积和式正确性（Glynn-Gray）
- test_boson_sampling_prob_sum: 2 模式玻色采样 prob_sum≈1.0（误差<1e-6）
- test_hom_dip_depth: HOM dip_depth=1.0（θ=0 完全不可区分）
- test_clements_unitarity: Clements 酉矩阵酉性误差<1e-10
- test_boson_4mode: 4 模式 2 光子玻色采样 n_outputs=10

来源（R02 学术诚信）:
- pytest 文档: https://docs.pytest.org/
- Aaronson & Arkhipov, STOC 2011: https://arxiv.org/abs/0910.4698
- Glynn, Eur. J. Comb. 2010: https://doi.org/10.1016/j.ejc.2010.01.010
- Hong, Ou, Mandel, PRL 1987:
  https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.59.2044
- Clements et al., Optica 2016:
  https://opg.optica.org/optica/fulltext.cfm?uri=optica-3-12-1460
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

from polaris_boson import (  # noqa: E402
    boson_sampling,
    clements_unitary,
    hom_interference,
    permanent_glynn_gray,
)


def test_permanent_2x2():
    """2×2 矩阵积和式正确性。

    Per([[a,b],[c,d]]) = ad + bc（注意: 积和式不是行列式，无符号翻转）。
    验证 [[1,2],[3,4]] → 1*4 + 2*3 = 10。
    """
    A = [[1, 2], [3, 4]]
    per = permanent_glynn_gray(A)
    assert abs(per - 10.0) < 1e-9, f"Per 期望 10.0，实际 {per}"

    # 复数矩阵验证: Per([[1,1j],[1j,1]]) = 1*1 + 1j*1j = 1 - 1 = 0
    B = [[1, 1j], [1j, 1]]
    per_b = permanent_glynn_gray(B)
    assert abs(per_b) < 1e-9, f"复数 Per 期望 0，实际 {per_b}"


def test_boson_sampling_prob_sum():
    """2 模式 2 光子玻色采样: prob_sum≈1.0（误差<1e-6）。

    输入 [1,1]（2 光子 2 模式），Clements 酉矩阵。
    输出模式数 = C(n_photons + n_modes - 1, n_photons) = C(3,2) = 3。
    概率分布归一化由酉矩阵保证（Aaronson-Arkhipov 2011）。
    """
    U = clements_unitary(n_modes=2, seed=42)
    # clements_unitary 返回 list of list of [real, imag]，可直接喂给 boson_sampling
    result = boson_sampling(U, [1, 1])
    assert "prob_distribution" in result
    assert "prob_sum" in result
    assert "n_outputs" in result
    assert abs(result["prob_sum"] - 1.0) < 1e-6, \
        f"prob_sum 期望 1.0，实际 {result['prob_sum']}"
    # 2 模式 2 光子: 3 个输出态 (2,0)(1,1)(0,2)
    assert result["n_outputs"] == 3, \
        f"n_outputs 期望 3，实际 {result['n_outputs']}"
    # 所有概率非负
    assert all(p >= 0.0 for p in result["prob_distribution"])


def test_boson_4mode():
    """4 模式 2 光子玻色采样: n_outputs=10, prob_sum≈1.0。

    输入 [1,1,0,0]（2 光子 4 模式），Clements 酉矩阵。
    输出模式数 = C(4+2-1, 2) = C(5,2) = 10。
    """
    U = clements_unitary(4, seed=42)
    result = boson_sampling(U, [1, 1, 0, 0])
    assert abs(result["prob_sum"] - 1.0) < 1e-6
    assert result["n_outputs"] == 10
    assert all(p >= 0.0 for p in result["prob_distribution"])


def test_hom_dip_depth():
    """HOM 干涉: dip_depth=1.0, verified=True。

    theta=0 → 完全不可区分 → dip_depth=1.0，符合计数率=0（HOM dip）。
    """
    result = hom_interference(0.0)
    assert "coincidence_prob" in result
    assert "dip_depth" in result
    assert "verified" in result
    assert abs(result["dip_depth"] - 1.0) < 1e-9, \
        f"dip_depth 期望 1.0，实际 {result['dip_depth']}"
    assert result["verified"] is True
    # theta=0: 完全不可分辨 → 符合计数率为 0
    assert abs(result["coincidence_prob"]) < 1e-9, \
        f"coincidence_prob 期望 0.0，实际 {result['coincidence_prob']}"


def test_clements_unitarity():
    """Clements 4×4 酉矩阵: 酉性误差<1e-10。

    验证返回格式为 list of list of [real, imag]，且 U @ U† = I。
    """
    U = clements_unitary(4, seed=42)
    assert len(U) == 4
    assert len(U[0]) == 4
    # 每个元素是 [real, imag] 二元组
    for i in range(4):
        for j in range(4):
            assert len(U[i][j]) == 2, \
                f"U[{i}][{j}] 须为 [real, imag]，得到 {U[i][j]}"
    # 转为 numpy 复矩阵验证酉性
    Un = np.array([[complex(r, i) for r, i in row] for row in U])
    err = np.max(np.abs(Un @ Un.conj().T - np.eye(4)))
    assert err < 1e-10, f"酉性误差 {err} ≥ 1e-10"
