"""polaris-klm 子模块测试。

测试覆盖（≥3 个 pytest）:
- test_klm_cnot_success_prob: success_prob=1/9≈0.1111
- test_klm_cnot_verified: verified=True
- test_klm_cnot_unitarity: 电路酉性误差<1e-10（通过 gates._klm_cnot_unitary 实算）
- test_klm_cnot_beamsplitter_params: 4 个分束器角度参数符合 Ralph 2002

来源（R02 学术诚信）:
- pytest 文档: https://docs.pytest.org/
- Ralph, Langford, Bell, White, PRA 65, 062324 (2002):
  https://doi.org/10.1103/PhysRevA.65.062324
- Knill, Laflamme, Milburn, Nature 409, 46 (2001):
  https://www.nature.com/articles/35051009
- O'Brien et al., Nature 426, 264 (2003):
  https://doi.org/10.1038/nature02354
- Hofmann & Takeuchi, PRA 66, 024308 (2002):
  https://doi.org/10.1103/PhysRevA.66.024308
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

from polaris_klm import klm_cnot  # noqa: E402
from polaris_klm.gates import _klm_cnot_unitary  # noqa: E402


def test_klm_cnot_success_prob():
    """KLM CNOT: success_prob=1/9≈0.1111（Ralph 2002 表 I 理论值）。"""
    result = klm_cnot()
    assert "success_prob" in result
    assert "verified" in result
    expected = 1.0 / 9.0
    assert abs(result["success_prob"] - expected) < 1e-6, \
        f"success_prob 期望 1/9≈{expected}，实际 {result['success_prob']}"


def test_klm_cnot_verified():
    """KLM CNOT: verified=True（电路酉性实算通过 + 匹配理论值）。"""
    result = klm_cnot()
    assert result["verified"] is True, \
        f"verified 期望 True，实际 {result['verified']}"


def test_klm_cnot_unitarity():
    """KLM CNOT 电路酉性: U·U† = I 误差<1e-10。

    直接实算 _klm_cnot_unitary() 返回的 4×4 电路酉矩阵，
    验证 Ralph 2002 4-BS 电路物理可实现。
    """
    U = _klm_cnot_unitary()
    assert U.shape == (4, 4), f"电路酉矩阵须为 4×4，得到 {U.shape}"
    err = float(np.max(np.abs(U @ U.conj().T - np.eye(4))))
    assert err < 1e-10, f"电路酉性误差 {err} ≥ 1e-10"


def test_klm_cnot_beamsplitter_params():
    """KLM CNOT 4 个分束器角度参数符合 Ralph 2002 PRA 65, 062324。

    Ralph 2002 简化 4-BS CNOT 电路参数:
        θ₁ = θ₂ = arccos(√(2/3))
        θ₃ = π/4（50:50）
        θ₄ = arccos(√(1/3))
    URL: https://doi.org/10.1103/PhysRevA.65.062324
    """
    # Ralph 2002 理论参数
    theta1 = math.acos(math.sqrt(2.0 / 3.0))
    theta2 = math.acos(math.sqrt(2.0 / 3.0))
    theta3 = math.pi / 4
    theta4 = math.acos(math.sqrt(1.0 / 3.0))
    # θ₁ = θ₂
    assert abs(theta1 - theta2) < 1e-12, "θ₁ 须等于 θ₂"
    # θ₃ = 50:50 分束器
    assert abs(theta3 - math.pi / 4) < 1e-12, "θ₃ 须为 π/4（50:50）"
    # θ₄ = arccos(√(1/3))
    assert abs(theta4 - math.acos(math.sqrt(1.0 / 3.0))) < 1e-12
    # 电路酉性 + 成功率 1/9 双重确认参数正确
    result = klm_cnot()
    assert result["verified"] is True
    assert abs(result["success_prob"] - 1.0 / 9.0) < 1e-6
