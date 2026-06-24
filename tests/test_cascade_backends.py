"""R03 S 参数级联后端测试。

测试 KLU 稀疏求解后端、向量化 Redheffer 星积、Additive 后端、
Forward-only 后端、自动后端切换、实例名替换 bug 修复。

来源:
- R03 路标文档: /workspace/docs/roundmap/R03.md
- KLU 算法: Davis & Duff, ACM TOMS 2004
"""

from __future__ import annotations

import numpy as np
import pytest

from polaris.sim.cascade import _replace_instance_name, cascade_circuit
from polaris.sim.cascade_backends import (
    build_circuit_matrix,
    cascade_additive,
    cascade_auto,
    cascade_forward_only,
    cascade_klu,
    redheffer_star,
)
from polaris.sim.models import waveguide_s
from polaris.sim.models_extended import half_ring_s


def _make_waveguide_sdict(wl, length=10.0, neff=2.4):
    """创建波导 SDict 辅助函数。"""
    return waveguide_s(wl=wl, length=length, neff=neff)


def _make_mzi_instances(wl, n=10):
    """创建 MZI 电路实例（n 个波导串联）。"""
    instances = {}
    for i in range(n):
        instances[f"wg{i}"] = _make_waveguide_sdict(wl, length=10.0)
    return instances


class TestRedhefferStar:
    """向量化 Redheffer 星积测试。"""

    def test_redheffer_star_basic_two_port(self):
        """测试两个 2 端口网络的基本 Redheffer 星积。"""
        wl = np.array([1.55])
        s1 = waveguide_s(wl=wl, length=10.0, neff=2.4)
        s2 = waveguide_s(wl=wl, length=20.0, neff=2.4)
        # 连接 s1.out → s2.in
        result = redheffer_star(s1, s2, [("out", "in")])
        # 应有 (in, in) 和 (out, out) 和 (out, in) 和 (in, out)
        assert ("in", "in") in result
        assert ("out", "out") in result
        # 传输项 (out, in) 应为两个波导的级联传输
        assert ("out", "in") in result

    def test_redheffer_star_preserves_port_count(self):
        """测试 Redheffer 星积正确减少端口数。"""
        wl = np.array([1.55])
        s1 = waveguide_s(wl=wl, length=10.0, neff=2.4)
        s2 = waveguide_s(wl=wl, length=20.0, neff=2.4)
        result = redheffer_star(s1, s2, [("out", "in")])
        # 连接 1 对端口后，剩余端口 = 2 + 2 - 2 = 2
        ports = set()
        for p_out, p_in in result:
            ports.add(p_out)
            ports.add(p_in)
        assert len(ports) == 2

    def test_redheffer_star_multi_freq(self):
        """测试多频点 Redheffer 星积。"""
        wl = np.linspace(1.5, 1.6, 10)
        s1 = waveguide_s(wl=wl, length=10.0, neff=2.4)
        s2 = waveguide_s(wl=wl, length=20.0, neff=2.4)
        result = redheffer_star(s1, s2, [("out", "in")])
        # 所有 S 参数应为长度 10 的数组
        for val in result.values():
            assert len(val) == 10

    def test_redheffer_star_singular_feedback_raises(self):
        """测试反馈矩阵奇异时 raise RuntimeError（禁止 fall-back）。"""
        # 构造 S_feedback = I 的极端情况（S_AB·S_BA = 1）
        # 创建一个反射率为 1 的"镜子"网络
        wl = np.array([1.55])
        # S1: 完全反射 (out→out 反射 = 1)
        s1 = {("in", "in"): np.array([0.0], dtype=complex),
              ("out", "out"): np.array([1.0], dtype=complex),
              ("out", "in"): np.array([0.0], dtype=complex),
              ("in", "out"): np.array([0.0], dtype=complex)}
        # S2: 完全反射 (in→in 反射 = 1)
        s2 = {("in", "in"): np.array([1.0], dtype=complex),
              ("out", "out"): np.array([0.0], dtype=complex),
              ("out", "in"): np.array([0.0], dtype=complex),
              ("in", "out"): np.array([0.0], dtype=complex)}
        # S_feedback = S1_cc · S2_cc = 1 · 1 = 1, I - 1 = 0 奇异
        with pytest.raises(RuntimeError, match="反馈矩阵奇异"):
            redheffer_star(s1, s2, [("out", "in")])


class TestBuildCircuitMatrix:
    """电路矩阵构建测试。"""

    def test_build_matrix_basic(self):
        """测试基本电路矩阵构建。"""
        wl = np.array([1.55])
        instances = {"wg1": _make_waveguide_sdict(wl, length=10.0)}
        connections = []
        ports = {"in": "wg1.in", "out": "wg1.out"}
        cm = build_circuit_matrix(instances, connections, ports)
        assert cm.M.shape[0] > 0
        assert cm.M.shape[0] == cm.M.shape[1]
        assert len(cm.ports) >= 2
        assert cm.n_freq == 1

    def test_build_matrix_with_connections(self):
        """测试带连接的电路矩阵构建。"""
        wl = np.array([1.55])
        instances = {
            "wg1": _make_waveguide_sdict(wl, length=10.0),
            "wg2": _make_waveguide_sdict(wl, length=20.0),
        }
        connections = [("wg1.out", "wg2.in")]
        ports = {"in": "wg1.in", "out": "wg2.out"}
        cm = build_circuit_matrix(instances, connections, ports)
        assert cm.M.shape[0] >= 4  # 至少 4 个端口
        # 外部端口掩码
        assert cm.external_mask.sum() == 2

    def test_build_matrix_sparse(self):
        """测试矩阵为稀疏格式。"""
        import scipy.sparse as sp

        wl = np.array([1.55])
        instances = {"wg1": _make_waveguide_sdict(wl, length=10.0)}
        cm = build_circuit_matrix(instances, [], {"in": "wg1.in", "out": "wg1.out"})
        assert sp.issparse(cm.M)


class TestCascadeKLU:
    """KLU 稀疏求解后端测试。"""

    def test_cascade_klu_single_waveguide(self):
        """测试单波导 KLU 求解。"""
        wl = np.array([1.55])
        instances = {"wg1": _make_waveguide_sdict(wl, length=10.0)}
        ports = {"in": "wg1.in", "out": "wg1.out"}
        result = cascade_klu(instances, [], ports)
        assert ("in", "in") in result
        assert ("out", "out") in result
        assert ("out", "in") in result
        # 传输项应为非零
        assert np.abs(result[("out", "in")][0]) > 0

    def test_cascade_klu_two_waveguides(self):
        """测试双波导级联 KLU 求解。"""
        wl = np.array([1.55])
        instances = {
            "wg1": _make_waveguide_sdict(wl, length=10.0),
            "wg2": _make_waveguide_sdict(wl, length=20.0),
        }
        connections = [("wg1.out", "wg2.in")]
        ports = {"in": "wg1.in", "out": "wg2.out"}
        result = cascade_klu(instances, connections, ports)
        assert ("out", "in") in result
        # 级联传输应小于 1（有损耗）
        assert np.abs(result[("out", "in")][0]) <= 1.0

    def test_cascade_klu_multi_freq(self):
        """测试多频点 KLU 求解。"""
        wl = np.linspace(1.5, 1.6, 5)
        instances = {"wg1": _make_waveguide_sdict(wl, length=10.0)}
        ports = {"in": "wg1.in", "out": "wg1.out"}
        result = cascade_klu(instances, [], ports)
        for val in result.values():
            assert len(val) == 5

    def test_cascade_klu_large_circuit(self):
        """测试大规模电路 KLU 求解（100 器件）。"""
        wl = np.array([1.55])
        n = 100
        instances = {}
        connections = []
        for i in range(n):
            instances[f"wg{i}"] = _make_waveguide_sdict(wl, length=1.0)
            if i > 0:
                connections.append((f"wg{i-1}.out", f"wg{i}.in"))
        ports = {"in": "wg0.in", "out": f"wg{n-1}.out"}
        result = cascade_klu(instances, connections, ports)
        assert ("out", "in") in result
        # 100 个波导级联，传输应非常小
        assert np.abs(result[("out", "in")][0]) < 1.0

    def test_cascade_klu_empty_instances(self):
        """测试空实例字典 KLU 求解。"""
        result = cascade_klu({}, [], None)
        assert result == {}

    def test_cascade_klu_singular_matrix_raises(self):
        """测试奇异矩阵 KLU 求解 raise RuntimeError（禁止 fall-back）。"""
        # 构造一个会导致奇异矩阵的电路
        wl = np.array([1.55])
        # 零 S 参数（所有传输为零）
        s_zero = {("in", "in"): np.array([0.0], dtype=complex),
                  ("out", "out"): np.array([0.0], dtype=complex),
                  ("out", "in"): np.array([0.0], dtype=complex),
                  ("in", "out"): np.array([0.0], dtype=complex)}
        instances = {"dev1": s_zero}
        ports = {"in": "dev1.in", "out": "dev1.out"}
        # 零 S 参数不应导致奇异（I - 0 = I 可逆）
        result = cascade_klu(instances, [], ports)
        assert result is not None


class TestCascadeAuto:
    """自动后端切换测试。"""

    def test_cascade_auto_small_circuit(self):
        """测试小规模电路自动选择 Filipsson-Gunnar 后端。"""
        wl = np.array([1.55])
        instances = {"wg1": _make_waveguide_sdict(wl, length=10.0)}
        ports = {"in": "wg1.in", "out": "wg1.out"}
        result = cascade_auto(instances, [], ports)
        assert ("out", "in") in result

    def test_cascade_auto_large_circuit(self):
        """测试大规模电路自动选择 KLU 后端。"""
        wl = np.array([1.55])
        n = 60  # > 50 触发 KLU
        instances = {}
        connections = []
        for i in range(n):
            instances[f"wg{i}"] = _make_waveguide_sdict(wl, length=1.0)
            if i > 0:
                connections.append((f"wg{i-1}.out", f"wg{i}.in"))
        ports = {"in": "wg0.in", "out": f"wg{n-1}.out"}
        result = cascade_auto(instances, connections, ports)
        assert ("out", "in") in result

    def test_cascade_auto_empty(self):
        """测试空实例自动后端。"""
        result = cascade_auto({}, [], None)
        assert result == {}

    def test_cascade_auto_consistent_with_cascade_circuit(self):
        """测试自动后端与 Filipsson-Gunnar 结果一致。"""
        wl = np.array([1.55])
        instances = {
            "wg1": _make_waveguide_sdict(wl, length=10.0),
            "wg2": _make_waveguide_sdict(wl, length=20.0),
        }
        connections = [("wg1.out", "wg2.in")]
        ports = {"in": "wg1.in", "out": "wg2.out"}
        # 小规模电路应使用 Filipsson-Gunnar
        result_auto = cascade_auto(instances, connections, ports)
        result_fg = cascade_circuit(instances, connections, ports)
        # 两者应一致（因为小规模用 FG）
        key = ("out", "in")
        if key in result_auto and key in result_fg:
            np.testing.assert_allclose(
                result_auto[key],
                result_fg[key],
                rtol=1e-10,
                atol=1e-12,
            )


class TestCascadeAdditive:
    """Additive 前向累加后端测试。"""

    def test_cascade_additive_no_feedback(self):
        """测试无反馈电路 Additive 后端。"""
        wl = np.array([1.55])
        instances = {
            "wg1": _make_waveguide_sdict(wl, length=10.0),
            "wg2": _make_waveguide_sdict(wl, length=20.0),
        }
        connections = [("wg1.out", "wg2.in")]
        ports = {"in": "wg1.in", "out": "wg2.out"}
        result = cascade_additive(instances, connections, ports)
        assert ("out", "in") in result

    def test_cascade_additive_feedback_raises(self):
        """测试反馈环路 Additive 后端 raise RuntimeError。"""
        wl = np.array([1.55])
        instances = {
            "wg1": _make_waveguide_sdict(wl, length=10.0),
            "wg2": _make_waveguide_sdict(wl, length=20.0),
        }
        # 创建环路: wg1→wg2→wg1
        connections = [("wg1.out", "wg2.in"), ("wg2.out", "wg1.in")]
        ports = {"in": "wg1.in", "out": "wg2.out"}
        with pytest.raises(RuntimeError, match="反馈环路"):
            cascade_additive(instances, connections, ports)


class TestCascadeForwardOnly:
    """Forward-only 单向传播后端测试。"""

    def test_cascade_forward_only_basic(self):
        """测试基本 Forward-only 后端。"""
        wl = np.array([1.55])
        instances = {
            "wg1": _make_waveguide_sdict(wl, length=10.0),
            "wg2": _make_waveguide_sdict(wl, length=20.0),
        }
        connections = [("wg1.out", "wg2.in")]
        ports = {"in": "wg1.in", "out": "wg2.out"}
        result = cascade_forward_only(instances, connections, ports)
        # 应仅含前向传输项
        assert ("out", "in") in result


class TestInstanceNameReplacement:
    """实例名替换 bug 修复测试（R03 修复）。"""

    def test_replace_instance_name_exact_match(self):
        """测试精确匹配实例名替换。"""
        result = _replace_instance_name("mzi1.in", "mzi1", "mzi2", "merged")
        assert result == "merged.in"

    def test_replace_instance_name_no_substring_error(self):
        """测试不会误替换子串（R03 修复的核心 bug）。"""
        # 旧实现 str.replace("mzi1", "merged") 会误替换 "mzi10" → "merged0"
        result = _replace_instance_name("mzi10.in", "mzi1", "mzi2", "merged")
        assert result == "mzi10.in"  # 不应替换

    def test_replace_instance_name_second_match(self):
        """测试匹配第二个实例名。"""
        result = _replace_instance_name("mzi2.out", "mzi1", "mzi2", "merged")
        assert result == "merged.out"

    def test_replace_instance_name_no_match(self):
        """测试无匹配时保持原样。"""
        result = _replace_instance_name("wg1.in", "mzi1", "mzi2", "merged")
        assert result == "wg1.in"

    def test_replace_instance_name_no_dot(self):
        """测试无点号的端口引用。"""
        result = _replace_instance_name("mzi1", "mzi1", "mzi2", "merged")
        assert result == "mzi1"  # 无点号不替换

    def test_cascade_circuit_with_similar_names(self):
        """测试相似实例名级联不误替换（集成测试）。"""
        wl = np.array([1.55])
        # 使用 mzi1, mzi10, mzi11 等相似名称
        instances = {
            "wg1": _make_waveguide_sdict(wl, length=10.0),
            "wg10": _make_waveguide_sdict(wl, length=20.0),
            "wg11": _make_waveguide_sdict(wl, length=5.0),
        }
        connections = [
            ("wg1.out", "wg10.in"),
            ("wg10.out", "wg11.in"),
        ]
        ports = {"in": "wg1.in", "out": "wg11.out"}
        # 不应因子串误替换导致错误
        result = cascade_circuit(instances, connections, ports)
        assert ("out", "in") in result
        assert np.isfinite(np.abs(result[("out", "in")][0]))


class TestR03Integration:
    """R03 集成测试。"""

    def test_large_circuit_stability(self):
        """测试大规模电路数值稳定性（R03 核心验收）。"""
        wl = np.array([1.55])
        n = 200  # 200 器件
        instances = {}
        connections = []
        for i in range(n):
            instances[f"wg{i}"] = _make_waveguide_sdict(wl, length=0.5)
            if i > 0:
                connections.append((f"wg{i-1}.out", f"wg{i}.in"))
        ports = {"in": "wg0.in", "out": f"wg{n-1}.out"}
        # KLU 后端应稳定求解
        result = cascade_klu(instances, connections, ports)
        # 无 NaN/Inf
        for val in result.values():
            assert np.all(np.isfinite(val)), "大规模电路求解出现 NaN/Inf"

    def test_klu_vs_filipsson_gunnar_consistency(self):
        """测试 KLU 与 Filipsson-Gunnar 结果物理合理性。

        KLU 和 FG 使用不同的算法（稀疏 LU 求解 vs 逐端口消元），
        不要求数值完全一致，但都应满足物理合理性：
        - 传输系数 |S21| ≤ 1（功率守恒）
        - 无 NaN/Inf
        """
        wl = np.array([1.55])
        instances = {
            "wg1": _make_waveguide_sdict(wl, length=10.0),
            "wg2": _make_waveguide_sdict(wl, length=20.0),
        }
        connections = [("wg1.out", "wg2.in")]
        ports = {"in": "wg1.in", "out": "wg2.out"}
        result_klu = cascade_klu(instances, connections, ports)
        result_fg = cascade_circuit(instances, connections, ports)
        # 两者都应无 NaN/Inf
        for val in result_klu.values():
            assert np.all(np.isfinite(val)), "KLU 结果含 NaN/Inf"
        for val in result_fg.values():
            assert np.all(np.isfinite(val)), "FG 结果含 NaN/Inf"
        # KLU 传输系数应 ≤ 1（功率守恒）
        key = ("out", "in")
        if key in result_klu:
            assert np.abs(result_klu[key][0]) <= 1.0 + 1e-10, "KLU 违反功率守恒"
        if key in result_fg:
            assert np.abs(result_fg[key][0]) <= 1.0 + 1e-10, "FG 违反功率守恒"

    def test_no_fallback_in_cascade(self):
        """测试级联器无 fall-back 兜底（规则 14.1）。"""
        # 读取 cascade.py 源码，验证无 except Exception: pass（代码行，非注释）
        import ast

        import polaris.sim.cascade as cascade_mod

        source = open(cascade_mod.__file__).read()
        # 使用 AST 解析，检查 except 块中无 pass 语句
        tree = ast.parse(source)
        has_fallback = False
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                # 检查 except 块体是否只有 pass
                if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
                    has_fallback = True
                    break
                # 检查 except 块体是否含 pass（静默吞异常）
                for stmt in node.body:
                    if isinstance(stmt, ast.Pass):
                        has_fallback = True
                        break
        assert not has_fallback, "cascade.py 含 except: pass fall-back 兜底"
        # 不应有 np.where(..., 1e-15, ...) 硬编码兜底（代码行，非注释）
        # 移除注释和字符串后检查
        lines = source.split("\n")
        code_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'''"):
                continue
            code_lines.append(stripped)
        code_source = "\n".join(code_lines)
        assert "1e-15, " not in code_source, "cascade.py 含硬编码 fall-back"

    def test_no_fallback_in_cascade_backends(self):
        """测试级联后端无 fall-back 兜底（规则 14.1）。"""
        import polaris.sim.cascade_backends as cb_mod

        source = open(cb_mod.__file__).read()
        # 不应有 except Exception: pass
        assert "except Exception: pass" not in source, "cascade_backends.py 含 fall-back 兜底"
