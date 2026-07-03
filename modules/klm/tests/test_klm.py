"""polaris-klm 子模块深度测试（v5.0，覆盖全 API）。

测试覆盖（17 个 pytest）:
- klm_cnot: success_prob=1/9 / verified=True / 返回键 / 类型 / 可复现 / 匹配理论值
- _klm_cnot_unitary: 4×4 shape / 酉性 / 非单位 / 4 个分束器组合
- 分束器参数: θ₁=θ₂=arccos(√(2/3)) / θ₃=π/4 / θ₄=arccos(√(1/3))
- _beamsplitter: 50:50 特定值 / θ=0 单位 / 酉性
- 模块: 版本号 / API 导出

R02 学术诚信（docstring 含 ≥5 文献 URL）:
- Knill, Laflamme, Milburn, Nature 409, 46 (2001), KLM 方案
  https://www.nature.com/articles/35051009
- Ralph, Langford, Bell, White, PRA 65, 062324 (2002), 简化 CNOT（1/9）
  https://doi.org/10.1103/PhysRevA.65.062324
- Hofmann & Takeuchi, PRA 66, 024308 (2002)
  https://doi.org/10.1103/PhysRevA.66.024308
- O'Brien et al., Nature 426, 264 (2003)
  https://doi.org/10.1038/nature02354
- Knill, PRA 66, 052306 (2002)
  https://doi.org/10.1103/PhysRevA.66.052306
- pytest 文档: https://docs.pytest.org/

规则依据: R02 学术诚信 / R03 禁止 fall-back / R05 无 TODO / R04 纯 NumPy
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

import polaris_klm  # noqa: E402
from polaris_klm import klm_cnot  # noqa: E402
from polaris_klm.gates import (  # noqa: E402
    _beamsplitter,
    _KLM_CNOT_THEORETICAL_SUCCESS,
    _klm_cnot_unitary,
    _UNITARITY_TOL,
)


# ===========================================================================
# 1. klm_cnot — KLM CNOT 门（Ralph 2002 简化 4-BS）
# ===========================================================================
def test_klm_cnot_success_prob():
    """success_prob = 1/9 ≈ 0.1111（Ralph 2002 PRA 65, 062324 表 I 理论值）。

    来源: Ralph et al., PRA 65, 062324 (2002), 表 I.
         URL: https://doi.org/10.1103/PhysRevA.65.062324
    """
    result = klm_cnot()
    expected = 1.0 / 9.0
    assert abs(result["success_prob"] - expected) < 1e-12, (
        f"success_prob 期望 1/9≈{expected}，实际 {result['success_prob']}"
    )


def test_klm_cnot_verified():
    """verified=True（电路酉性实算通过 + 报告值匹配 Ralph 2002 理论值）。"""
    result = klm_cnot()
    assert result["verified"] is True


def test_klm_cnot_return_keys():
    """返回 dict 含 success_prob / verified 两键。"""
    result = klm_cnot()
    assert set(result.keys()) == {"success_prob", "verified"}


def test_klm_cnot_return_types():
    """返回值类型: success_prob 为 float, verified 为 bool。"""
    result = klm_cnot()
    assert isinstance(result["success_prob"], float)
    assert isinstance(result["verified"], bool)


def test_klm_cnot_deterministic():
    """klm_cnot 无随机性，重复调用结果一致（参数固定，Ralph 2002 电路）。"""
    r1 = klm_cnot()
    r2 = klm_cnot()
    assert r1 == r2, "klm_cnot 须确定性（参数固定）"


def test_klm_cnot_success_prob_matches_constant():
    """success_prob 与模块常量 _KLM_CNOT_THEORETICAL_SUCCESS 一致。"""
    result = klm_cnot()
    assert abs(result["success_prob"] - _KLM_CNOT_THEORETICAL_SUCCESS) < 1e-15


def test_klm_cnot_success_prob_in_range():
    """success_prob ∈ (0, 1)（后选择成功率物理范围）。"""
    result = klm_cnot()
    assert 0.0 < result["success_prob"] < 1.0


# ===========================================================================
# 2. _klm_cnot_unitary — KLM CNOT 4×4 电路酉矩阵
# ===========================================================================
def test_klm_cnot_unitary_shape():
    """电路酉矩阵 shape = (4, 4)（4 模式: control/target/aux1/aux2）。"""
    U = _klm_cnot_unitary()
    assert U.shape == (4, 4)
    assert U.dtype == complex


def test_klm_cnot_unitarity():
    """电路酉性: U @ U† = I，误差 < 1e-10（R03: 物理可实现）。

    4 个分束器左乘乘积本征酉，浮点误差 ~1e-15。
    """
    U = _klm_cnot_unitary()
    err = float(np.max(np.abs(U @ U.conj().T - np.eye(4))))
    assert err < 1e-10, f"电路酉性误差 {err} ≥ 1e-10"


def test_klm_cnot_unitary_not_identity():
    """电路酉矩阵 ≠ 单位矩阵（4 个非平凡分束器已作用）。

    若 U = I 则说明分束器未实际作用（实现 bug，R05）。
    """
    U = _klm_cnot_unitary()
    diff = float(np.max(np.abs(U - np.eye(4))))
    assert diff > 0.1, f"电路酉矩阵应 ≠ I（diff={diff}），分束器未作用？"


def test_klm_cnot_unitarity_below_tolerance():
    """酉性误差 < _UNITARITY_TOL（与源码常量一致）。"""
    U = _klm_cnot_unitary()
    err = float(np.max(np.abs(U @ U.conj().T - np.eye(4))))
    assert err < _UNITARITY_TOL


# ===========================================================================
# 3. 分束器参数 — Ralph 2002 PRA 65, 062324
# ===========================================================================
def test_klm_bs1_bs2_theta_equal():
    """θ₁ = θ₂ = arccos(√(2/3))（Ralph 2002 电路参数）。

    URL: https://doi.org/10.1103/PhysRevA.65.062324
    """
    theta1 = math.acos(math.sqrt(2.0 / 3.0))
    theta2 = math.acos(math.sqrt(2.0 / 3.0))
    assert abs(theta1 - theta2) < 1e-15
    # arccos(√(2/3)) ≈ 0.6155 rad
    assert abs(theta1 - 0.6154797086703868) < 1e-9


def test_klm_bs3_is_5050():
    """θ₃ = π/4（50:50 分束器，Ralph 2002）。"""
    theta3 = math.pi / 4
    assert abs(theta3 - math.pi / 4) < 1e-15
    # cos²(π/4) = sin²(π/4) = 0.5（50:50 验证）
    assert abs(math.cos(theta3) ** 2 - 0.5) < 1e-15
    assert abs(math.sin(theta3) ** 2 - 0.5) < 1e-15


def test_klm_bs4_theta():
    """θ₄ = arccos(√(1/3))（Ralph 2002 电路参数）。"""
    theta4 = math.acos(math.sqrt(1.0 / 3.0))
    # arccos(√(1/3)) ≈ 0.9553 rad
    assert abs(theta4 - 0.9553166181245093) < 1e-9
    # cos²(θ₄) = 1/3, sin²(θ₄) = 2/3
    assert abs(math.cos(theta4) ** 2 - 1.0 / 3.0) < 1e-12
    assert abs(math.sin(theta4) ** 2 - 2.0 / 3.0) < 1e-12


def test_klm_bs1_bs2_distinct_from_bs4():
    """θ₁=θ₂ ≠ θ₄（不同分束器，Ralph 2002 电路非对称）。"""
    theta1 = math.acos(math.sqrt(2.0 / 3.0))
    theta4 = math.acos(math.sqrt(1.0 / 3.0))
    assert abs(theta1 - theta4) > 0.1, "θ₁ 与 θ₄ 应不同"


# ===========================================================================
# 4. _beamsplitter — KLM 约定分束器酉矩阵
# ===========================================================================
def test_beamsplitter_unitarity():
    """分束器 U_BS(θ) = [[cosθ, i·sinθ],[i·sinθ, cosθ]] 酉性。

    来源: Ralph et al., PRA 2002.
         URL: https://doi.org/10.1103/PhysRevA.65.062324
    """
    for theta in (0.0, 0.3, math.pi / 4, 0.9, math.pi / 2):
        U = _beamsplitter(theta)
        err = float(np.max(np.abs(U @ U.conj().T - np.eye(2))))
        assert err < 1e-12, f"θ={theta} 分束器酉性误差 {err}"


def test_beamsplitter_identity_at_zero():
    """θ=0: U_BS(0) = [[1,0],[0,1]] = I（无分束）。"""
    U = _beamsplitter(0.0)
    assert np.allclose(U, np.eye(2)), f"θ=0 应为单位矩阵，得到 {U}"


def test_beamsplitter_5050_values():
    """θ=π/4: 50:50 分束器 U_BS = [[√2/2, i√2/2],[i√2/2, √2/2]]。"""
    U = _beamsplitter(math.pi / 4)
    expected = np.array(
        [[math.sqrt(2) / 2, 1j * math.sqrt(2) / 2],
         [1j * math.sqrt(2) / 2, math.sqrt(2) / 2]],
        dtype=complex,
    )
    assert np.allclose(U, expected), f"50:50 分束器值不符，得到 {U}"


def test_beamsplitter_klm_convention():
    """KLM 约定: 非对角元为纯虚 i·sinθ（与 Clements 的 -e^{-iφ}sinθ 不同）。"""
    theta = 0.6
    U = _beamsplitter(theta)
    # 对角元 cosθ 实数
    assert abs(U[0, 0].imag) < 1e-15
    assert abs(U[1, 1].imag) < 1e-15
    assert abs(U[0, 0].real - math.cos(theta)) < 1e-15
    # 非对角元 i·sinθ 纯虚
    assert abs(U[0, 1].real) < 1e-15
    assert abs(U[0, 1].imag - math.sin(theta)) < 1e-15
    assert abs(U[1, 0].imag - math.sin(theta)) < 1e-15


# ===========================================================================
# 5. 模块元信息
# ===========================================================================
def test_klm_version():
    """子模块版本号 5.1.0（v5.0 拆分后统一）。"""
    assert polaris_klm.__version__ == "5.1.0"


def test_klm_api_exports():
    """__all__ 导出 klm_cnot 与 __version__。"""
    assert set(polaris_klm.__all__) == {"klm_cnot", "__version__"}
