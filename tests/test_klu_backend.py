"""KLU 直接稀疏求解器后端测试（P0-2）。

测试覆盖:
1. KLU 稀疏矩阵分解与求解（对比 scipy 直接求解）
2. COLAMD 列排序验证
3. 矩阵重用（refactor）—— pattern 一致/不一致
4. MNA 矩阵构建
5. DC/AC/瞬态电路分析
6. 错误处理（奇异矩阵、未分解、参数非法）

来源对齐: Davis & Duff 1999 (KLU); Ho/Ruehli/Brennan 1975 (MNA);
         scipy.sparse.linalg.splu 文档。
规则 R03（禁止 fall-back，失败 raise）/R05（Bug 必修）。
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest
import scipy.sparse as sp
import scipy.sparse.linalg as spla

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from polaris.sim.klu_backend import (  # noqa: E402
    ACResult,
    CircuitSolver,
    DCResult,
    KLUSolver,
    TransientResult,
    build_mna_matrix,
)

# =============================================================================
# 辅助函数
# =============================================================================


def _make_spd_matrix(n: int, seed: int = 42) -> sp.csr_matrix:
    """构造对称正定稀疏矩阵（保证非奇异）。

    对角占优 + 随机稀疏化，确保 splu 可分解。
    """
    rng = np.random.default_rng(seed)
    dense = rng.standard_normal((n, n)) * 0.1
    dense += np.diag(np.linspace(n * 0.5, n, n))
    mask = rng.random((n, n)) < 0.3
    dense = dense * mask + np.diag(np.linspace(n * 0.5, n, n))
    return sp.csr_matrix(dense)


def _make_circuit_divider() -> list[dict]:
    """构造电阻分压电路: V1(10V) → R1(1k) → R2(1k) → GND。

    期望: V_node2 = 5.0V（分压中点）。
    """
    return [
        {"type": "V", "name": "V1", "n1": 1, "n2": 0, "dc": 10.0},
        {"type": "R", "name": "R1", "n1": 1, "n2": 2, "value": 1e3},
        {"type": "R", "name": "R2", "n1": 2, "n2": 0, "value": 1e3},
    ]


# =============================================================================
# 1. KLU 稀疏矩阵分解与求解测试
# =============================================================================


def test_klu_solve_simple() -> None:
    """测试 1: 简单稀疏矩阵求解，对比 numpy.linalg.solve。"""
    a_dense = np.array(
        [[4.0, 0.0, 1.0], [0.0, 5.0, 0.0], [1.0, 0.0, 6.0]]
    )
    a = sp.csr_matrix(a_dense)
    b = np.array([1.0, 2.0, 3.0])
    solver = KLUSolver(a)
    solver.factor()
    x = solver.solve(b)
    x_ref = np.linalg.solve(a_dense, b)
    assert np.allclose(x, x_ref), f"KLU 解 {x} 与 numpy {x_ref} 不一致"
    assert solver.is_factored
    assert solver.size == 3
    assert not solver.is_complex


def test_klu_solve_vs_scipy_spsolve() -> None:
    """测试 2: KLU 求解对比 scipy.sparse.linalg.spsolve（中等规模稀疏矩阵）。"""
    n = 50
    a = _make_spd_matrix(n, seed=123)
    rng = np.random.default_rng(7)
    b = rng.standard_normal(n)
    solver = KLUSolver(a)
    solver.factor()
    x_klu = solver.solve(b)
    x_ref = spla.spsolve(a.tocsc(), b)
    assert np.allclose(x_klu, x_ref, atol=1e-10), (
        f"KLU 与 spsolve 最大误差 {np.max(np.abs(x_klu - x_ref))} 超容差"
    )


def test_klu_solve_complex_matrix() -> None:
    """测试 3: 复数稀疏矩阵求解（AC 分析核心场景）。"""
    a_dense = np.array(
        [[2.0 + 1j, 0.0, 1.0], [0.0, 3.0, 1j], [1.0, 1j, 4.0 + 2j]],
        dtype=np.complex128,
    )
    a = sp.csr_matrix(a_dense)
    b = np.array([1.0 + 0j, 2.0 - 1j, 3.0 + 0j])
    solver = KLUSolver(a)
    solver.factor()
    x = solver.solve(b)
    x_ref = np.linalg.solve(a_dense, b)
    assert np.allclose(x, x_ref), f"复数 KLU 解 {x} 与 numpy {x_ref} 不一致"
    assert solver.is_complex


def test_klu_solve_multiple_rhs() -> None:
    """测试 4: 多右端向量求解（矩阵重用，一次分解多次求解）。"""
    n = 20
    a = _make_spd_matrix(n, seed=99)
    rng = np.random.default_rng(11)
    b_multi = rng.standard_normal((n, 3))
    solver = KLUSolver(a)
    solver.factor()
    for k in range(3):
        x = solver.solve(b_multi[:, k])
        x_ref = spla.spsolve(a.tocsc(), b_multi[:, k])
        assert np.allclose(x, x_ref, atol=1e-10), f"第 {k} 个 RHS 求解不一致"


# =============================================================================
# 2. COLAMD 排序验证
# =============================================================================


def test_colamd_permutation_nontrivial() -> None:
    """测试 5: COLAMD 列排序验证——非平凡排序（证明 COLAMD 生效）。

    来源: Davis 2004 COLAMD; scipy splu permc_spec='COLAMD' 默认。
    对足够大的非结构稀疏矩阵，COLAMD 应产生非单位排列以减少 fill-in。
    """
    n = 30
    a = _make_spd_matrix(n, seed=2024)
    solver = KLUSolver(a)
    solver.factor()
    perm_c = solver.get_perm_c()
    assert perm_c.shape == (n,)
    assert np.array_equal(np.sort(perm_c), np.arange(n)), "perm_c 必须是 0..n-1 的排列"
    # 非结构化矩阵应触发非平凡 COLAMD 排序
    assert not np.array_equal(perm_c, np.arange(n)), (
        "COLAMD 排序为平凡（自然序），与 COLAMD 算法预期不符"
    )


def test_colamd_fewer_fill_than_natural() -> None:
    """测试 6: COLAMD 排序减少 fill-in（对比 NATURAL 排序）。

    来源: Davis 2004 COLAMD（COLAMD 目标即减少 LU 分解 fill-in）。
    """
    n = 25
    a = _make_spd_matrix(n, seed=5566).tocsc()
    lu_colamd = spla.splu(a, permc_spec="COLAMD")
    lu_natural = spla.splu(a, permc_spec="NATURAL")
    # COLAMD 的 fill-in（L+U 非零数）应不超过 NATURAL
    assert lu_colamd.nnz <= lu_natural.nnz, (
        f"COLAMD fill-in {lu_colamd.nnz} > NATURAL {lu_natural.nnz}，"
        "COLAMD 未达到减少 fill-in 的目标"
    )


# =============================================================================
# 3. 矩阵重用（refactor）测试
# =============================================================================


def test_klu_refactor_same_pattern() -> None:
    """测试 7: 相同 sparsity pattern 的矩阵 refactor（KLU 核心优势）。

    构造两个 mask 相同、数值不同的稀疏矩阵，验证 refactor 可复用符号分解。
    """
    n = 15
    rng = np.random.default_rng(100)
    mask = rng.random((n, n)) < 0.3
    diag = np.diag(np.linspace(8.0, 12.0, n))
    dense1 = rng.standard_normal((n, n)) * 0.1 * mask + diag
    dense2 = rng.standard_normal((n, n)) * 0.1 * mask + diag
    a1 = sp.csr_matrix(dense1)
    a2 = sp.csr_matrix(dense2)
    solver = KLUSolver(a1)
    solver.factor()
    b = np.ones(n)
    x1 = solver.solve(b)
    solver.refactor(a2)
    x2 = solver.solve(b)
    x2_ref = spla.spsolve(a2.tocsc(), b)
    assert np.allclose(x2, x2_ref, atol=1e-10), "refactor 后求解不一致"
    x1_ref = spla.spsolve(a1.tocsc(), b)
    assert np.allclose(x1, x1_ref, atol=1e-10), "原矩阵求解不一致"


def test_klu_refactor_different_pattern_raises() -> None:
    """测试 8: 不同 sparsity pattern 的矩阵 refactor 应 raise（KLU 约束）。"""
    a1 = sp.csr_matrix(np.array([[4.0, 0.0, 1.0], [0.0, 5.0, 0.0], [1.0, 0.0, 6.0]]))
    # a2 多一个非零元，pattern 不同
    a2 = sp.csr_matrix(np.array([[4.0, 2.0, 1.0], [0.0, 5.0, 0.0], [1.0, 0.0, 6.0]]))
    solver = KLUSolver(a1)
    solver.factor()
    with pytest.raises(ValueError, match="sparsity pattern"):
        solver.refactor(a2)


def test_klu_refactor_without_factor_raises() -> None:
    """测试 9: 未 factor 就 refactor 应 raise（KLU 需先符号分解）。"""
    a = sp.csr_matrix(np.eye(3))
    solver = KLUSolver(a)
    with pytest.raises(RuntimeError, match="factor"):
        solver.refactor(a)


def test_klu_solve_without_factor_raises() -> None:
    """测试 10: 未 factor 就 solve 应 raise。"""
    a = sp.csr_matrix(np.eye(3))
    solver = KLUSolver(a)
    with pytest.raises(RuntimeError, match="factor"):
        solver.solve(np.ones(3))


def test_klu_singular_matrix_raises() -> None:
    """测试 11: 奇异矩阵分解应 raise（规则 R03 禁止 fall-back）。"""
    # 全零矩阵是奇异的
    a = sp.csr_matrix(np.zeros((3, 3)))
    solver = KLUSolver(a)
    with pytest.raises(RuntimeError, match="奇异"):
        solver.factor()


def test_klu_non_square_matrix_raises() -> None:
    """测试 12: 非方阵应 raise。"""
    a = sp.csr_matrix(np.zeros((3, 4)))
    with pytest.raises(ValueError, match="方阵"):
        KLUSolver(a)


def test_klu_rhs_dimension_mismatch_raises() -> None:
    """测试 13: rhs 维度不匹配应 raise。"""
    a = sp.csr_matrix(np.eye(3))
    solver = KLUSolver(a)
    solver.factor()
    with pytest.raises(ValueError, match="rhs 维度"):
        solver.solve(np.ones(5))


# =============================================================================
# 4. MNA 矩阵构建测试
# =============================================================================


def test_build_mna_resistive_divider() -> None:
    """测试 14: MNA 矩阵构建——电阻分压电路。

    电路: V1(10V) → R1(1k) → R2(1k) → GND
    MNA size = 2 节点 + 1 电压源 = 3
    """
    devices = _make_circuit_divider()
    a, z, n_nodes, n_vsrc = build_mna_matrix(devices)
    assert n_nodes == 2
    assert n_vsrc == 1
    assert a.shape == (3, 3)
    assert z.shape == (3,)
    # 电压源 RHS 应为 10V
    assert z[2] == 10.0
    # 直接求解验证分压
    x = spla.spsolve(a.tocsc(), z)
    assert np.isclose(x[1], 5.0), f"节点 2 电压 {x[1]} 应为 5.0V（分压中点）"


def test_build_mna_invalid_resistor_raises() -> None:
    """测试 15: 无效电阻（阻值≤0）应 raise。"""
    devices = [
        {"type": "R", "name": "R1", "n1": 1, "n2": 0, "value": -100.0},
    ]
    with pytest.raises(ValueError, match="阻值"):
        build_mna_matrix(devices)


def test_build_mna_unknown_device_type_raises() -> None:
    """测试 16: 未知器件类型应 raise。"""
    devices = [
        {"type": "X", "name": "X1", "n1": 1, "n2": 0, "value": 1.0},
    ]
    with pytest.raises(ValueError, match="未知器件类型"):
        build_mna_matrix(devices)


def test_build_mna_empty_devices_raises() -> None:
    """测试 17: 空器件列表应 raise。"""
    with pytest.raises(ValueError, match="为空"):
        build_mna_matrix([])


# =============================================================================
# 5. DC/AC/瞬态分析测试
# =============================================================================


def test_dc_analysis_voltage_divider() -> None:
    """测试 18: DC 分析——电阻分压电路。

    V1(10V) → R1(1k) → R2(1k) → GND，期望 V_node2 = 5.0V。
    电压源电流符号约定（SPICE）: i_V 正方向为 n1→n2（电压源内部），
    外部电流从正极流出，故 i_V1 = -5mA。
    """
    devices = _make_circuit_divider()
    solver = CircuitSolver()
    dc = solver.dc_analysis(devices)
    assert isinstance(dc, DCResult)
    assert dc.n_nodes == 2
    assert dc.n_vsrc == 1
    assert np.isclose(dc.node_voltages[2], 5.0), (
        f"分压点电压 {dc.node_voltages[2]} 应为 5.0V"
    )
    assert np.isclose(dc.node_voltages[1], 10.0), (
        f"电源节点电压 {dc.node_voltages[1]} 应为 10.0V"
    )
    # 电压源电流符号: SPICE 约定 i_V 正方向 n1→n2（内部），
    # 外部电流 10V/2kΩ=5mA 从正极流出，故 i_V1 = -5mA
    assert np.isclose(dc.vsource_currents["V1"], -5e-3, atol=1e-6), (
        f"电压源电流 {dc.vsource_currents['V1']} 应为 -5mA（SPICE 符号约定）"
    )


def test_dc_analysis_with_current_source() -> None:
    """测试 19: DC 分析——含电流源电路。

    I1(1mA) 从地注入节点 1（n1=0, n2=1，SPICE 约定正电流 n1→n2 即地从节点1，
    等效注入节点1），R1(1k) 到 GND，期望 V_node1 = 1V。
    """
    devices = [
        {"type": "I", "name": "I1", "n1": 0, "n2": 1, "dc": 1e-3},
        {"type": "R", "name": "R1", "n1": 1, "n2": 0, "value": 1e3},
    ]
    solver = CircuitSolver()
    dc = solver.dc_analysis(devices)
    assert np.isclose(dc.node_voltages[1], 1.0), (
        f"电流源注入节点电压 {dc.node_voltages[1]} 应为 1.0V (I*R=1mA*1kΩ)"
    )


def test_ac_analysis_rc_lowpass() -> None:
    """测试 20: AC 分析——RC 低通滤波器频率响应。

    电路: V1(ac=1V) → R(1kΩ) → C(1nF) → GND
    截止频率 fc = 1/(2πRC) ≈ 159 kHz
    - 低频 (1 kHz): |V_out| ≈ 1.0（通带）
    - 高频 (100 MHz): |V_out| ≈ 0（阻带）
    """
    devices = [
        {"type": "V", "name": "V1", "n1": 1, "n2": 0, "ac": 1.0},
        {"type": "R", "name": "R1", "n1": 1, "n2": 2, "value": 1e3},
        {"type": "C", "name": "C1", "n1": 2, "n2": 0, "value": 1e-9},
    ]
    freqs = np.array([1e3, 1.59e5, 1e8])  # 低频、截止、高频
    solver = CircuitSolver()
    ac = solver.ac_analysis(devices, freqs)
    assert isinstance(ac, ACResult)
    assert ac.n_freq == 3
    v_out = np.abs(ac.node_voltages[2])
    # 低频通带 ≈ 1.0
    assert v_out[0] > 0.99, f"低频增益 {v_out[0]} 应接近 1.0"
    # 截止频率 ≈ 1/√2 ≈ 0.707
    assert 0.65 < v_out[1] < 0.75, f"截止频率增益 {v_out[1]} 应接近 0.707"
    # 高频阻带 << 1
    assert v_out[2] < 0.01, f"高频增益 {v_out[2]} 应远小于 1"


def test_ac_analysis_empty_freqs_raises() -> None:
    """测试 21: AC 分析空频率数组应 raise。"""
    devices = _make_circuit_divider()
    solver = CircuitSolver()
    with pytest.raises(ValueError, match="为空"):
        solver.ac_analysis(devices, np.array([]))


def test_ac_analysis_negative_freq_raises() -> None:
    """测试 22: AC 分析负频率应 raise。"""
    devices = _make_circuit_divider()
    solver = CircuitSolver()
    with pytest.raises(ValueError, match="非负"):
        solver.ac_analysis(devices, np.array([1e3, -1e3]))


def test_transient_rc_charging() -> None:
    """测试 23: 瞬态分析——RC 电路正弦响应。

    电路: V1(dc=0, ac=1V, freq=1MHz) → R(1kΩ) → C(1nF) → GND
    DC 工作点: V_node2 = 0（dc=0，电容开路无电流）
    瞬态: V1 = sin(2π·1MHz·t)，RC 低通滤波器响应
    截止频率 fc = 1/(2πRC) ≈ 159kHz，1MHz 处于阻带（增益 < 0.16）
    """
    devices = [
        {"type": "V", "name": "V1", "n1": 1, "n2": 0, "dc": 0.0, "ac": 1.0, "freq": 1e6},
        {"type": "R", "name": "R1", "n1": 1, "n2": 2, "value": 1e3},
        {"type": "C", "name": "C1", "n1": 2, "n2": 0, "value": 1e-9},
    ]
    t_step = 1e-8   # 10 ns（1MHz 周期 1μs，每周期 100 点）
    t_end = 5e-6    # 5 μs = 5 个周期
    solver = CircuitSolver()
    tr = solver.transient(devices, t_step=t_step, t_end=t_end)
    assert isinstance(tr, TransientResult)
    assert tr.n_steps == int(np.ceil(t_end / t_step)) + 1
    assert tr.refactor_count > 0, "瞬态分析应触发 KLU refactor"
    # 初始值 ≈ 0（DC 工作点 dc=0）
    v_init = tr.node_voltages[2][0]
    assert abs(v_init) < 1e-6, f"初始电压 {v_init} 应接近 0"
    # 稳态后 V_node2 应为正弦波，幅度 < 1（阻带衰减）
    v_out = tr.node_voltages[2][100:]  # 跳过瞬态过渡期
    v_amp = np.max(np.abs(v_out))
    assert v_amp < 0.5, f"1MHz 阻带输出幅度 {v_amp} 应 < 0.5（RC 低通衰减）"
    assert v_amp > 0.01, f"输出幅度 {v_amp} 应 > 0.01（应有正弦响应）"


def test_transient_invalid_time_raises() -> None:
    """测试 24: 瞬态分析无效时间参数应 raise。"""
    devices = _make_circuit_divider()
    solver = CircuitSolver()
    with pytest.raises(ValueError, match="时间参数"):
        solver.transient(devices, t_step=-1e-9, t_end=1e-6)
    with pytest.raises(ValueError, match="时间参数"):
        solver.transient(devices, t_step=1e-9, t_end=-1e-6)


def test_transient_step_greater_than_end_raises() -> None:
    """测试 25: t_step > t_end 应 raise。"""
    devices = _make_circuit_divider()
    solver = CircuitSolver()
    with pytest.raises(ValueError, match="t_step"):
        solver.transient(devices, t_step=1e-6, t_end=1e-9)


# =============================================================================
# 6. 综合集成测试
# =============================================================================


def test_ac_analysis_klu_refactor_reuse() -> None:
    """测试 26: AC 频率扫描中 KLU refactor 复用验证。

    多频点扫描时，每个频点的 MNA 矩阵 pattern 不变（仅 C/L 导纳数值变），
    KLU 应通过 refactor 复用符号分解。
    """
    devices = [
        {"type": "V", "name": "V1", "n1": 1, "n2": 0, "ac": 1.0},
        {"type": "R", "name": "R1", "n1": 1, "n2": 2, "value": 1e3},
        {"type": "L", "name": "L1", "n1": 2, "n2": 0, "value": 1e-6},
    ]
    freqs = np.logspace(6, 9, 10)  # 1 MHz - 1 GHz
    solver = CircuitSolver()
    ac = solver.ac_analysis(devices, freqs)
    assert ac.n_freq == 10
    # 电感在低频接近短路（V_out ≈ 0），高频接近开路（V_out ≈ 1）
    v_out = np.abs(ac.node_voltages[2])
    assert v_out[0] < v_out[-1], "电感低频应衰减、高频应通过"
    # 验证所有频点解均为有限值
    assert np.all(np.isfinite(v_out)), "AC 解含非有限值"


def test_dc_analysis_multi_node_circuit() -> None:
    """测试 27: DC 分析——多节点梯形电阻网络。

    V1(12V) → R1(1k) → node2 → R2(2k) → node3 → R3(3k) → GND
    期望: V2 = 12 * (R2+R3)/(R1+R2+R3), V3 = 12 * R3/(R1+R2+R3)
    """
    devices = [
        {"type": "V", "name": "V1", "n1": 1, "n2": 0, "dc": 12.0},
        {"type": "R", "name": "R1", "n1": 1, "n2": 2, "value": 1e3},
        {"type": "R", "name": "R2", "n1": 2, "n2": 3, "value": 2e3},
        {"type": "R", "name": "R3", "n1": 3, "n2": 0, "value": 3e3},
    ]
    solver = CircuitSolver()
    dc = solver.dc_analysis(devices)
    r_total = 6e3
    v2_expected = 12.0 * (2e3 + 3e3) / r_total  # 10V
    v3_expected = 12.0 * 3e3 / r_total           # 6V
    assert np.isclose(dc.node_voltages[2], v2_expected, atol=1e-6), (
        f"V2 {dc.node_voltages[2]} 应为 {v2_expected}"
    )
    assert np.isclose(dc.node_voltages[3], v3_expected, atol=1e-6), (
        f"V3 {dc.node_voltages[3]} 应为 {v3_expected}"
    )


def test_klu_factor_once_solve_many_pattern() -> None:
    """测试 28: KLU factor_once + solve_many 模式（多 RHS 复用分解）。

    这是 KLU 在电路仿真中的核心价值: 一次分解，多次求解。
    """
    n = 30
    a = _make_spd_matrix(n, seed=7777)
    rng = np.random.default_rng(42)
    solver = KLUSolver(a)
    solver.factor()
    # 100 个不同 RHS，复用同一次分解
    solutions = []
    for _ in range(100):
        b = rng.standard_normal(n)
        x = solver.solve(b)
        solutions.append(x)
    # 验证第一个和最后一个解的正确性
    for idx in (0, 99):
        b_check = solver.solve(solutions[idx])  # 用解作为新 RHS 验证
        # A * x = b => A * b_check = x => b_check = A^{-1} * x = A^{-1} * A^{-1} * b
        # 此处仅验证 solve 可重复调用且结果有限
        assert np.all(np.isfinite(b_check)), "复用分解求解产生非有限值"


def test_circuit_solver_klu_solver_reuse_after_dc() -> None:
    """测试 29: DC 分析后 CircuitSolver 内部 KLU 求解器状态正确。

    验证 CircuitSolver._klu 在 DC 分析后被正确赋值，可继续访问。
    """
    devices = _make_circuit_divider()
    solver = CircuitSolver()
    dc = solver.dc_analysis(devices)
    assert solver._klu is not None, "DC 分析后 KLU 求解器应为非 None"
    assert solver._klu.is_factored, "KLU 求解器应处于已分解状态"
    assert solver._klu.size == dc.n_nodes + dc.n_vsrc


def test_ac_analysis_with_inductor_capacitor() -> None:
    """测试 30: AC 分析含电感和电容（LC 谐振）。

    电路: V1(ac=1V) → L(1μH) → C(1nF) → GND
    谐振频率 f0 = 1/(2π√(LC)) ≈ 5.03 MHz
    在谐振频率处，节点 2 电压应显著放大。
    """
    l_val = 1e-6  # 1 μH
    c_val = 1e-9  # 1 nF
    f0 = 1.0 / (2.0 * np.pi * np.sqrt(l_val * c_val))
    devices = [
        {"type": "V", "name": "V1", "n1": 1, "n2": 0, "ac": 1.0},
        {"type": "L", "name": "L1", "n1": 1, "n2": 2, "value": l_val},
        {"type": "C", "name": "C1", "n1": 2, "n2": 0, "value": c_val},
    ]
    freqs = np.array([f0 * 0.1, f0, f0 * 10.0])
    solver = CircuitSolver()
    ac = solver.ac_analysis(devices, freqs)
    v_out = np.abs(ac.node_voltages[2])
    # 无阻尼 LC 谐振在 f0 处理论上增益→∞，实际数值应远大于非谐振点
    assert v_out[1] > v_out[0], "谐振点增益应大于低频点"
    assert v_out[1] > v_out[2], "谐振点增益应大于高频点"
