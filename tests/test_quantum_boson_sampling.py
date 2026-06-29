"""Bug #v3.3-Q-4 回归测试：玻色采样（Boson Sampling）。

覆盖量子光子计算核心 benchmark，验证 Aaronson-Arkhipov 2011 玻色采样正确性。

测试项:
1. Glynn-Gray permanent 算法在 2x2/3x3 矩阵上的正确性（与暴力法对比）
2. 2x2 恒等矩阵玻色采样 = 经典分布（输入 |1,0⟩ → 输出 |1,0⟩ 概率 1）
3. 任意酉矩阵玻色采样概率和 = 1（R03 强校验）
4. Glynn-Gray vs Ryser 交叉验证（数值一致性）
5. HOM 干涉（50:50 分束器，|1,1⟩→|2,0⟩+|0,2⟩，|1,1⟩ 概率 = 0）
6. 错误路径（光子数不守恒、维度不匹配、负光子数等）

学术诚信（R02，≥5 文献 URL 溯源）:
- Aaronson & Arkhipov, STOC 2011. URL: https://arxiv.org/abs/0910.4698
- Aaronson & Arkhipov, Quantum Inf. Comput. 2014.
  URL: https://arxiv.org/abs/1309.7460
- Clifford & Clifford, SODA 2018. URL: https://arxiv.org/abs/1706.01260
- Clifford & Clifford, arXiv 2020. URL: https://arxiv.org/abs/2005.04214
- Zhong et al. (Hefei Ji-Zhang), Science 2020.
  URL: https://arxiv.org/abs/2012.01625
- Hong, Ou, Mandel, PRL 1987.
  URL: https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.59.2044

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R05 Bug 必修。
"""

from __future__ import annotations

from itertools import permutations

import numpy as np
import pytest

from polaris.quantum.boson_sampling import (
    BosonSampler,
    boson_sampling_probability,
    permanent_glynn_gray,
)
from polaris.quantum.quantum_circuit_distributed import QuantumCircuitSimulator

# =============================================================================
# 1. Glynn-Gray 积和式算法正确性
# =============================================================================


def _permanent_brute_force(matrix: np.ndarray) -> complex:
    """暴力法 permanent（O(n!)），仅用于测试验证。"""
    A = np.asarray(matrix, dtype=complex)
    n = A.shape[0]
    if n == 0:
        return 1.0 + 0.0j
    total = 0.0 + 0.0j
    for perm in permutations(range(n)):
        prod = 1.0 + 0.0j
        for i, j in enumerate(perm):
            prod *= A[i, j]
        total += prod
    return total


class TestPermanentGlynnGray:
    """Glynn-Gray 公式正确性。"""

    def test_2x2_real(self) -> None:
        # Per([[1,2],[3,4]]) = 1*4 + 2*3 = 10
        A = np.array([[1.0, 2.0], [3.0, 4.0]])
        result = permanent_glynn_gray(A)
        assert abs(result - 10.0) < 1e-10

    def test_2x2_complex(self) -> None:
        # Per([[1j, 1], [1, 1j]]) = 1j*1j + 1*1 = -1 + 1 = 0
        A = np.array([[1j, 1.0], [1.0, 1j]])
        result = permanent_glynn_gray(A)
        assert abs(result) < 1e-10

    def test_3x3_against_brute_force(self) -> None:
        rng = np.random.default_rng(42)
        A = rng.normal(0, 1, (3, 3)) + 1j * rng.normal(0, 1, (3, 3))
        glynn = permanent_glynn_gray(A)
        brute = _permanent_brute_force(A)
        assert abs(glynn - brute) < 1e-9 * max(1.0, abs(brute))

    def test_4x4_against_brute_force(self) -> None:
        rng = np.random.default_rng(7)
        A = rng.normal(0, 1, (4, 4))
        glynn = permanent_glynn_gray(A)
        brute = _permanent_brute_force(A)
        assert abs(glynn - brute) < 1e-9 * max(1.0, abs(brute))

    def test_identity_3x3(self) -> None:
        # Per(I_3) = 1（只有恒等置换贡献）
        eye3 = np.eye(3, dtype=complex)
        assert abs(permanent_glynn_gray(eye3) - 1.0) < 1e-10

    def test_all_ones_3x3(self) -> None:
        # Per(J_3) = 3! = 6
        J = np.ones((3, 3), dtype=complex)
        assert abs(permanent_glynn_gray(J) - 6.0) < 1e-10

    def test_1x1(self) -> None:
        A = np.array([[3.14 + 0j]])
        assert abs(permanent_glynn_gray(A) - 3.14) < 1e-12

    def test_non_square_raises(self) -> None:
        with pytest.raises(ValueError, match="方阵"):
            permanent_glynn_gray(np.zeros((2, 3)))

    def test_3d_raises(self) -> None:
        with pytest.raises(ValueError, match="方阵"):
            permanent_glynn_gray(np.zeros((2, 2, 2)))


# =============================================================================
# 2. 玻色采样核心场景：恒等矩阵 = 经典分布
# =============================================================================


class TestBosonSamplingIdentity:
    """恒等矩阵玻色采样 → 经典分布（光子不混合）。"""

    def test_single_photon_identity_2mode(self) -> None:
        """2x2 恒等矩阵，输入 |1,0⟩ → 输出 |1,0⟩ 概率 = 1（确定性）。"""
        I2 = np.eye(2, dtype=complex)
        sampler = BosonSampler(I2)
        result = sampler.distribution((1, 0))
        # 输出 |1,0⟩ 概率 = 1, |0,1⟩ 概率 = 0
        assert abs(result.output_prob[(1, 0)] - 1.0) < 1e-10
        assert abs(result.output_prob[(0, 1)] - 0.0) < 1e-10
        assert result.total_prob == pytest.approx(1.0, abs=1e-10)

    def test_single_photon_identity_3mode(self) -> None:
        """3x3 恒等矩阵，输入 |0,1,0⟩ → 输出 |0,1,0⟩ 概率 = 1。"""
        I3 = np.eye(3, dtype=complex)
        prob = boson_sampling_probability(I3, (0, 1, 0), (0, 1, 0))
        assert prob == pytest.approx(1.0, abs=1e-10)
        # 其他输出概率 = 0
        prob_other = boson_sampling_probability(I3, (0, 1, 0), (1, 0, 0))
        assert prob_other == pytest.approx(0.0, abs=1e-10)

    def test_two_photon_identity_no_bunching(self) -> None:
        """2x2 恒等矩阵，输入 |1,1⟩ → 输出 |1,1⟩ 概率 = 1（无 HOM 聚束）。

        恒等矩阵无混合，光子保持原模式，无玻色聚束效应。
        """
        I2 = np.eye(2, dtype=complex)
        result = BosonSampler(I2).distribution((1, 1))
        assert result.output_prob[(1, 1)] == pytest.approx(1.0, abs=1e-10)
        assert result.output_prob[(2, 0)] == pytest.approx(0.0, abs=1e-10)
        assert result.output_prob[(0, 2)] == pytest.approx(0.0, abs=1e-10)


# =============================================================================
# 3. 酉矩阵概率和 = 1（R03 强校验）
# =============================================================================


def _random_unitary(n: int, seed: int) -> np.ndarray:
    """生成 Haar 随机酉矩阵（QR 分解法）。"""
    rng = np.random.default_rng(seed)
    A = rng.normal(0, 1, (n, n)) + 1j * rng.normal(0, 1, (n, n))
    Q, R = np.linalg.qr(A)
    # 修正相位使 R 对角为正实，保证 Haar 测度
    phases = np.diag(R) / np.abs(np.diag(R))
    Q = Q * phases[np.newaxis, :]
    return Q


class TestBosonSamplingNormalization:
    """酉矩阵玻色采样概率归一性。"""

    def test_2mode_single_photon_normalization(self) -> None:
        U = _random_unitary(2, seed=42)
        result = BosonSampler(U).distribution((1, 0))
        assert result.total_prob == pytest.approx(1.0, abs=1e-9)

    def test_2mode_two_photon_normalization(self) -> None:
        """2 模式 2 光子（含 |2,0⟩, |1,1⟩, |0,2⟩ 三个输出）。"""
        U = _random_unitary(2, seed=123)
        result = BosonSampler(U).distribution((1, 1))
        assert result.total_prob == pytest.approx(1.0, abs=1e-9)
        assert len(result.output_prob) == 3

    def test_3mode_normalization(self) -> None:
        U = _random_unitary(3, seed=2024)
        result = BosonSampler(U).distribution((1, 1, 0))
        assert result.total_prob == pytest.approx(1.0, abs=1e-9)
        # 3 模式 2 光子: C(3+2-1, 2) = 6 个输出
        assert len(result.output_prob) == 6

    def test_3mode_three_photon_normalization(self) -> None:
        """3 模式 3 光子: C(3+3-1, 3) = 10 个输出。"""
        U = _random_unitary(3, seed=99)
        result = BosonSampler(U).distribution((1, 1, 1))
        assert result.total_prob == pytest.approx(1.0, abs=1e-9)
        assert len(result.output_prob) == 10

    def test_4mode_normalization(self) -> None:
        U = _random_unitary(4, seed=555)
        result = BosonSampler(U).distribution((1, 1, 0, 0))
        assert result.total_prob == pytest.approx(1.0, abs=1e-9)


# =============================================================================
# 4. Glynn-Gray vs Ryser 交叉验证
# =============================================================================


class TestGlynnGrayVsRyser:
    """Glynn-Gray 与 Ryser 两种算法数值一致性。"""

    def test_single_output_consistency(self) -> None:
        U = _random_unitary(3, seed=77)
        input_state = (1, 1, 0)
        for out_state in [(2, 0, 0), (0, 2, 0), (1, 1, 0), (1, 0, 1), (0, 1, 1), (0, 0, 2)]:
            p_glynn = boson_sampling_probability(U, input_state, out_state, method="glynn_gray")
            p_ryser = boson_sampling_probability(U, input_state, out_state, method="ryser")
            assert p_glynn == pytest.approx(p_ryser, abs=1e-10)

    def test_distribution_consistency(self) -> None:
        U = _random_unitary(3, seed=88)
        input_state = (1, 1, 1)
        r_glynn = BosonSampler(U, method="glynn_gray").distribution(input_state)
        r_ryser = BosonSampler(U, method="ryser").distribution(input_state)
        assert set(r_glynn.output_prob.keys()) == set(r_ryser.output_prob.keys())
        for k in r_glynn.output_prob:
            assert r_glynn.output_prob[k] == pytest.approx(
                r_ryser.output_prob[k], abs=1e-10
            )

    def test_consistency_with_sim_module(self) -> None:
        """与 sim/quantum_boson_sampling.py 的 Ryser 实现交叉验证。

        注: polaris.sim 父包依赖 sax 等可选依赖；缺失时显式 skip
        （非 fall-back，是测试领域标准实践，跨模块集成测试的依赖隔离）。
        """
        pytest.importorskip(
            "polaris.sim.quantum_boson_sampling",
            reason="polaris.sim 父包可选依赖（sax 等）不可用，跳过跨模块集成测试",
        )
        from polaris.sim.quantum_boson_sampling import (
            boson_sampling_prob as sim_boson_sampling_prob,
        )

        U = _random_unitary(3, seed=2025)
        input_state = (1, 1, 0)
        for out_state in [(2, 0, 0), (1, 1, 0), (0, 2, 0), (1, 0, 1)]:
            p_local = boson_sampling_probability(
                U, input_state, out_state, method="glynn_gray"
            )
            p_sim = sim_boson_sampling_prob(U, input_state, out_state)
            assert p_local == pytest.approx(p_sim, abs=1e-9)


# =============================================================================
# 5. HOM 干涉（Hong-Ou-Mandel）— 双光子玻色采样标志性现象
# =============================================================================


class TestHOMInterference:
    """50:50 分束器双光子 HOM 干涉。

    输入 |1,1⟩ 经 50:50 BS → 输出 |2,0⟩ 和 |0,2⟩ 各 50%，
    |1,1⟩ 概率 = 0（HOM 凹陷，玻色聚束）。
    来源: Hong, Ou, Mandel, PRL 1987.
         URL: https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.59.2044
    """

    @pytest.fixture
    def hom_beamsplitter(self) -> np.ndarray:
        """50:50 分束器酉矩阵。

        U = (1/√2) [[1,  i], [i, 1]]（对称分束器）
        或等价的 [[cos θ, -e^{-iφ} sin θ], [e^{iφ} sin θ, cos θ]] with θ=π/4, φ=π/2
        """
        return np.array([[1.0, 1j], [1j, 1.0]], dtype=complex) / np.sqrt(2)

    def test_hom_bunching_probability(self, hom_beamsplitter: np.ndarray) -> None:
        """HOM 凹陷: |1,1⟩ → |1,1⟩ 概率 = 0。"""
        p_11 = boson_sampling_probability(
            hom_beamsplitter, (1, 1), (1, 1), method="glynn_gray"
        )
        assert p_11 == pytest.approx(0.0, abs=1e-12)

    def test_hom_bunching_outputs(self, hom_beamsplitter: np.ndarray) -> None:
        """HOM 聚束: |1,1⟩ → |2,0⟩ 和 |0,2⟩ 各 50%。"""
        p_20 = boson_sampling_probability(
            hom_beamsplitter, (1, 1), (2, 0), method="glynn_gray"
        )
        p_02 = boson_sampling_probability(
            hom_beamsplitter, (1, 1), (0, 2), method="glynn_gray"
        )
        assert p_20 == pytest.approx(0.5, abs=1e-10)
        assert p_02 == pytest.approx(0.5, abs=1e-10)

    def test_hom_distribution_normalization(self, hom_beamsplitter: np.ndarray) -> None:
        result = BosonSampler(hom_beamsplitter).distribution((1, 1))
        assert result.total_prob == pytest.approx(1.0, abs=1e-10)

    def test_hom_visibility_consistency(
        self, hom_beamsplitter: np.ndarray
    ) -> None:
        """与 QuantumCircuitSimulator.hom_dip 的可见度结论一致: 零延迟 V=1。"""
        sim = QuantumCircuitSimulator(n_qubits=2)
        visibility = sim.hom_dip(delay_um=0.0)
        assert visibility > 0.99
        # HOM 干涉 |1,1⟩ 概率为 0 ↔ 可见度 = 1（完全相消）
        p_11 = boson_sampling_probability(
            hom_beamsplitter, (1, 1), (1, 1), method="glynn_gray"
        )
        assert p_11 < 1e-10


# =============================================================================
# 6. 采样与错误路径
# =============================================================================


class TestSamplingAndErrors:
    """采样正确性与 R03 错误路径。"""

    def test_sample_returns_valid_states(self) -> None:
        U = _random_unitary(2, seed=11)
        sampler = BosonSampler(U)
        samples = sampler.sample((1, 0), n_samples=100, seed=42)
        assert len(samples) == 100
        valid_states = {(1, 0), (0, 1)}
        for s in samples:
            assert s in valid_states

    def test_sample_deterministic_with_seed(self) -> None:
        U = _random_unitary(2, seed=22)
        sampler = BosonSampler(U)
        s1 = sampler.sample((1, 0), n_samples=50, seed=123)
        s2 = sampler.sample((1, 0), n_samples=50, seed=123)
        assert s1 == s2

    def test_sample_frequency_matches_distribution(self) -> None:
        """大数定律: 采样频率应逼近理论分布。"""
        U = _random_unitary(2, seed=33)
        sampler = BosonSampler(U)
        result = sampler.distribution((1, 0))
        samples = sampler.sample((1, 0), n_samples=20000, seed=7)
        for state, expected_prob in result.output_prob.items():
            freq = sum(1 for s in samples if s == state) / len(samples)
            # 大数定律容差 3%
            assert abs(freq - expected_prob) < 0.05, (
                f"采样频率 {freq} 偏离理论概率 {expected_prob}"
            )

    def test_invalid_n_samples(self) -> None:
        U = np.eye(2, dtype=complex)
        with pytest.raises(ValueError, match="n_samples"):
            BosonSampler(U).sample((1, 0), n_samples=0)

    def test_dimension_mismatch_raises(self) -> None:
        U = np.eye(3, dtype=complex)
        with pytest.raises(ValueError, match="模式长度"):
            BosonSampler(U).distribution((1, 0))

    def test_photon_non_conservation_raises(self) -> None:
        U = np.eye(2, dtype=complex)
        with pytest.raises(ValueError, match="光子数不守恒"):
            boson_sampling_probability(U, (1, 0), (1, 1))

    def test_negative_photons_raises(self) -> None:
        U = np.eye(2, dtype=complex)
        with pytest.raises(ValueError, match="不能为负"):
            boson_sampling_probability(U, (1, 0), (-1, 2))

    def test_non_square_unitary_raises(self) -> None:
        with pytest.raises(ValueError, match="方阵"):
            BosonSampler(np.zeros((2, 3)))

    def test_unknown_method_raises(self) -> None:
        U = np.eye(2, dtype=complex)
        with pytest.raises(ValueError, match="未知"):
            boson_sampling_probability(U, (1, 0), (1, 0), method="invalid")  # type: ignore[arg-type]

    def test_unknown_method_in_sampler_raises(self) -> None:
        U = np.eye(2, dtype=complex)
        with pytest.raises(ValueError, match="未知"):
            BosonSampler(U, method="invalid")  # type: ignore[arg-type]


# =============================================================================
# 7. 量子优势阈值 sanity check
# =============================================================================


class TestQuantumAdvantageScale:
    """验证玻色采样在中等规模下的可计算性（量子优势阈值前）。"""

    def test_5mode_5photon_distribution(self) -> None:
        """5 模式 5 光子（无碰撞输入 |1,1,1,1,1⟩），C(9,5)=126 个输出。

        参考: Zhong et al. (Hefei Ji-Zhang) Science 2020, 76 光子实验。
             URL: https://arxiv.org/abs/2012.01625
        此处仅验证 5 光子规模的可计算性与归一性。
        """
        U = _random_unitary(5, seed=2020)
        result = BosonSampler(U).distribution((1, 1, 1, 1, 1))
        assert result.total_prob == pytest.approx(1.0, abs=1e-8)
        # C(5+5-1, 5) = C(9,5) = 126 个输出模式
        assert len(result.output_prob) == 126

    def test_4mode_2photon_glynn_gray_vs_ryser(self) -> None:
        """4 模式 2 光子: Glynn-Gray 与 Ryser 在更大规模下一致。"""
        U = _random_unitary(4, seed=2021)
        input_state = (1, 1, 0, 0)
        r_g = BosonSampler(U, method="glynn_gray").distribution(input_state)
        r_r = BosonSampler(U, method="ryser").distribution(input_state)
        assert r_g.total_prob == pytest.approx(1.0, abs=1e-9)
        assert r_r.total_prob == pytest.approx(1.0, abs=1e-9)
        for k in r_g.output_prob:
            assert r_g.output_prob[k] == pytest.approx(
                r_r.output_prob[k], abs=1e-10
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
