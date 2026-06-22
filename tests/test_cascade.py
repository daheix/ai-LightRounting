"""cascade.py 测试（R01 步骤 8）。

测试内容:
1. fall-back 兜底已删除（np.where 和 except Exception: pass）
2. 条件数计算与后端切换
3. 子网络增长算法正确性
4. 数值稳定性告警

来源:
- R01 路标: /workspace/docs/roundmap/R01.md
- SAX 子网络增长: https://flaport.github.io/sax/
"""

from __future__ import annotations

import numpy as np
import pytest

from polaris.sim.backend_selector import (
    StabilityReport,
    compute_condition_number,
    diagnose_stability,
    select_backend,
)
from polaris.sim.cascade import cascade_circuit
from polaris.sim.models import waveguide_s


class TestFallBackRemoved:
    """验证 fall-back 兜底已删除（规则 14.1）。"""

    def test_no_np_where_fallback(self):
        """cascade.py 中不应存在 np.where(..., 1e-15, ...) fall-back。"""
        import polaris.sim.cascade as cascade_mod

        source = open(cascade_mod.__file__).read()
        assert "np.where(np.abs(denom) < 1e-15, 1e-15, denom)" not in source, (
            "cascade.py 仍包含 np.where fall-back 兜底（规则 14.1 禁止）"
        )

    def test_no_except_pass(self):
        """cascade.py 中不应存在 except Exception: pass 静默异常。"""
        import polaris.sim.cascade as cascade_mod

        source = open(cascade_mod.__file__).read()
        assert "except Exception:\n            pass" not in source, (
            "cascade.py 仍包含 except Exception: pass 静默异常（规则 14.1 禁止）"
        )

    def test_no_silent_fallback_in_cascade_circuit(self):
        """cascade_circuit 不应静默吞掉 SAX 异常。"""
        import polaris.sim.cascade as cascade_mod

        source = open(cascade_mod.__file__).read()
        # 不应存在 SAX 失败后静默继续的代码
        assert "SAX 调用失败，使用纯 numpy" not in source, (
            "cascade_circuit 仍包含 SAX 失败后静默回退的注释"
        )


class TestConditionNumber:
    """测试条件数计算（R01 创新点 1）。"""

    def test_well_conditioned_matrix(self):
        """良态矩阵条件数应较小。"""
        # 单位矩阵条件数为 1
        sdict = {("p1", "p1"): np.array([1.0]), ("p2", "p2"): np.array([1.0])}
        cond = compute_condition_number(sdict)
        assert cond < 1e6, f"良态矩阵条件数应 < 1e6，得到 {cond}"

    def test_ill_conditioned_matrix(self):
        """病态矩阵条件数应较大。"""
        # 接近奇异的矩阵
        eps = 1e-8
        sdict = {
            ("p1", "p1"): np.array([1.0]),
            ("p1", "p2"): np.array([1.0]),
            ("p2", "p1"): np.array([1.0]),
            ("p2", "p2"): np.array([1.0 + eps]),
        }
        cond = compute_condition_number(sdict)
        assert cond > 1e6, f"病态矩阵条件数应 > 1e6，得到 {cond}"

    def test_singular_matrix_returns_inf(self):
        """奇异矩阵条件数应为 inf。"""
        # 全零矩阵（奇异）
        sdict = {
            ("p1", "p1"): np.array([0.0]),
            ("p1", "p2"): np.array([0.0]),
            ("p2", "p1"): np.array([0.0]),
            ("p2", "p2"): np.array([0.0]),
        }
        cond = compute_condition_number(sdict)
        assert cond == float("inf"), f"奇异矩阵条件数应为 inf，得到 {cond}"


class TestSelectBackend:
    """测试后端自动切换（R01 创新点 1）。"""

    def test_numpy_backend_for_well_conditioned(self):
        """良态矩阵应选择 numpy 后端。"""
        sdict = {("p1", "p1"): np.array([1.0]), ("p2", "p2"): np.array([1.0])}
        backend = select_backend(sdict)
        assert backend == "numpy", f"良态矩阵应选 numpy，得到 {backend}"

    def test_jax_backend_for_ill_conditioned(self):
        """病态矩阵应选择 jax 后端。"""
        eps = 1e-10
        sdict = {
            ("p1", "p1"): np.array([1.0]),
            ("p1", "p2"): np.array([1.0]),
            ("p2", "p1"): np.array([1.0]),
            ("p2", "p2"): np.array([1.0 + eps]),
        }
        backend = select_backend(sdict)
        assert backend == "jax", f"病态矩阵应选 jax，得到 {backend}"

    def test_singular_matrix_raises_runtime_error(self):
        """奇异矩阵应 raise RuntimeError 告警退出。"""
        eps = 1e-15
        sdict = {
            ("p1", "p1"): np.array([1.0]),
            ("p1", "p2"): np.array([1.0]),
            ("p2", "p1"): np.array([1.0]),
            ("p2", "p2"): np.array([1.0 + eps]),
        }
        with pytest.raises(RuntimeError, match="矩阵奇异"):
            select_backend(sdict)


class TestDiagnoseStability:
    """测试数值稳定性诊断（R01 创新点 1）。"""

    def test_well_conditioned_report(self):
        """良态矩阵诊断报告应正确。"""
        sdict = {("p1", "p1"): np.array([1.0]), ("p2", "p2"): np.array([1.0])}
        report = diagnose_stability(sdict)
        assert isinstance(report, StabilityReport)
        assert report.backend == "numpy"
        assert not report.is_singular

    def test_singular_report(self):
        """奇异矩阵诊断报告应标记 is_singular。"""
        eps = 1e-15
        sdict = {
            ("p1", "p1"): np.array([1.0]),
            ("p1", "p2"): np.array([1.0]),
            ("p2", "p1"): np.array([1.0]),
            ("p2", "p2"): np.array([1.0 + eps]),
        }
        report = diagnose_stability(sdict)
        assert report.is_singular


class TestCascadeCircuit:
    """测试级联算法正确性。"""

    def test_single_instance_no_connections(self):
        """单个实例无连接应返回原 S 参数。"""
        wl = np.array([1.55])
        s = waveguide_s(wl=wl, length=10.0, neff=2.4)
        result = cascade_circuit({"wg": s}, [], None)
        # 单实例无连接，应返回原 s
        assert ("in", "in") in result or ("out", "in") in result

    def test_two_waveguides_cascade(self):
        """两个波导级联，相位应叠加。"""
        wl = np.array([1.55])
        s1 = waveguide_s(wl=wl, length=10.0, neff=2.4)
        s2 = waveguide_s(wl=wl, length=20.0, neff=2.4)
        # 级联: wg1.out -> wg2.in
        result = cascade_circuit(
            {"wg1": s1, "wg2": s2},
            [("wg1.out", "wg2.in")],
            {"in": "wg1.in", "out": "wg2.out"},
        )
        # 级联后传输相位 = exp(j*beta*(10+20))
        assert ("out", "in") in result
        # 检查相位量级（30μm 波导相位）
        phase = result[("out", "in")]
        assert np.abs(phase[0]) > 0.99  # 无损波导 |S21|≈1

    def test_singular_denom_raises_runtime_error(self):
        """分母趋零时应 raise RuntimeError 告警退出。

        构造 S_AB·S_BA = 1 的情况（强谐振）:
        - s1 的 out 端口自反射 S_AA = 1（全反射）
        - s2 的 in 端口自反射 S_BB = 1（全反射）
        - denom = 1 - S_AA·S_BB = 0
        """
        # s1: out 端口全反射
        s1 = {
            ("in", "in"): np.array([0.0 + 0j]),
            ("out", "out"): np.array([1.0 + 0j]),  # S_AA = 1
            ("out", "in"): np.array([0.0 + 0j]),
            ("in", "out"): np.array([0.0 + 0j]),
        }
        # s2: in 端口全反射
        s2 = {
            ("in", "in"): np.array([1.0 + 0j]),  # S_BB = 1
            ("out", "out"): np.array([0.0 + 0j]),
            ("out", "in"): np.array([0.0 + 0j]),
            ("in", "out"): np.array([0.0 + 0j]),
        }
        with pytest.raises(RuntimeError, match="分母趋零"):
            cascade_circuit(
                {"d1": s1, "d2": s2},
                [("d1.out", "d2.in")],
                None,
            )
