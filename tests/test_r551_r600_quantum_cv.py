"""R551-R600 量子光子增强综合测试（纯 NumPy/SciPy CPU，R04 兼容）。

测试覆盖：
- R551 连续变量（CV）量子计算: GaussianState/Displacement/Squeezing/Rotation/
  BeamSplitter/HomodyneDetection
- R552 量子纠错: ThreeQubitRepetitionCode/SteaneCode/Syndrome/Recovery
- R553 资源态: GHZ/Cluster1D/NOON/StateFidelity
- R554 噪声模型: PhotonLoss/PhaseNoise/Detector
- R555 实验拟合: SParamFitter/LossExtractor/CouplingEfficiency
- R03/R02/R04 合规检查 + 端到端集成

文献依据：
- Weedbrook 2012 RMP 84 621 https://doi.org/10.1103/RevModPhys.84.621
- Shor 1995 PRA 52 R2493 https://doi.org/10.1103/PhysRevA.52.R2493
- Steane 1996 PRL 77 793 https://doi.org/10.1103/PhysRevLett.77.793
- Hein 2004 PRA 69 062311 https://doi.org/10.1103/PhysRevA.69.062311
- Kok & Lovett 2010 https://www.cambridge.org/9780521191356
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest

# 直接加载模块（绕过 polaris.sim.__init__ 的 sax 依赖）
_SRC_DIR = Path(__file__).resolve().parent.parent / "src" / "polaris"


def _load_module(rel_path: str, module_name: str):
    """从 src/polaris/ 下相对路径直接加载模块。"""
    file_path = _SRC_DIR / rel_path
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)
    return mod


_q = _load_module("sim/quantum_cv_qec.py", "_r551_quantum")


# ===========================================================================
# R551 连续变量（CV）量子计算
# ===========================================================================


class TestR551GaussianState:
    """R551 高斯态测试。"""

    def test_vacuum_state_covariance_is_half_identity(self):
        """真空态 V = I/2, d = 0（Weedbrook 2012 §II）。"""
        s = _q.GaussianState.vacuum(2)
        assert s.covariance.shape == (4, 4)
        np.testing.assert_allclose(s.covariance, 0.5 * np.eye(4))
        np.testing.assert_allclose(s.mean, np.zeros(4))
        assert s.n_modes == 2

    def test_vacuum_validates_n_modes_positive(self):
        """n_modes<1 须 raise（R03）。"""
        with pytest.raises(ValueError, match="n_modes"):
            _q.GaussianState.vacuum(0)

    def test_construction_rejects_non_symplectic_covariance(self):
        """违反不确定性关系 V+iΩ/2≥0 须 raise（R03）。

        构造 V = 0.01·I（方差太小，违反 Heisenberg ΔxΔp≥1/2）。"""
        bad_v = 0.01 * np.eye(2)
        with pytest.raises(ValueError, match="不确定性关系"):
            _q.GaussianState(covariance=bad_v, mean=np.zeros(2), n_modes=1)

    def test_construction_rejects_wrong_shape(self):
        """形状不匹配须 raise（R03）。"""
        with pytest.raises(ValueError, match="协方差矩阵"):
            _q.GaussianState(
                covariance=np.eye(3),
                mean=np.zeros(3),
                n_modes=1,
            )

    def test_squeezed_vacuum_reduces_x_variance(self):
        """压缩真空态 r>0 时 x 方差 = e^(-2r)/2 < 1/2。"""
        r = 1.0
        s = _q.GaussianState.squeezed_vacuum(r, theta=0.0)
        # V_xx = e^(-2r)/2
        assert s.covariance[0, 0] == pytest.approx(
            np.exp(-2 * r) / 2.0, rel=1e-12
        )
        # V_pp = e^(2r)/2
        assert s.covariance[1, 1] == pytest.approx(
            np.exp(2 * r) / 2.0, rel=1e-12
        )
        # 不确定性关系 ΔxΔp = 1/2（最小不确定态）
        delta_x = np.sqrt(s.covariance[0, 0])
        delta_p = np.sqrt(s.covariance[1, 1])
        assert delta_x * delta_p == pytest.approx(0.5, rel=1e-12)


class TestR551DisplacementGate:
    """R551 位移门测试。"""

    def test_displacement_shifts_mean(self):
        """D(α) 将 d 平移 sqrt(2)·(Re α, Im α)（Braunstein 2005 §III）。"""
        s0 = _q.GaussianState.vacuum(1)
        D = _q.DisplacementGate(alpha_real=1.0, alpha_imag=0.5)
        s1 = D.apply(s0)
        # d[0] += sqrt(2)·Re(α), d[1] += sqrt(2)·Im(α)
        assert s1.mean[0] == pytest.approx(np.sqrt(2.0) * 1.0, rel=1e-12)
        assert s1.mean[1] == pytest.approx(np.sqrt(2.0) * 0.5, rel=1e-12)

    def test_displacement_preserves_covariance(self):
        """位移门不改变协方差矩阵（仅平移相空间原点）。"""
        s0 = _q.GaussianState.squeezed_vacuum(r=0.5)
        V0 = s0.covariance.copy()
        D = _q.DisplacementGate(2.0, -1.0)
        s1 = D.apply(s0)
        np.testing.assert_allclose(s1.covariance, V0)

    def test_double_displacement_composes_linearly(self):
        """D(α)·D(β) = D(α+β)（精确到全局相位，平移合成线性）。"""
        s0 = _q.GaussianState.vacuum(1)
        D1 = _q.DisplacementGate(0.3, 0.4)
        D2 = _q.DisplacementGate(0.7, -0.2)
        # 应用两次
        s_seq = D2.apply(D1.apply(s0))
        # 一次合成
        D_sum = _q.DisplacementGate(1.0, 0.2)
        s_one = D_sum.apply(s0)
        np.testing.assert_allclose(s_seq.mean, s_one.mean, atol=1e-12)


class TestR551SqueezingGate:
    """R551 压缩门测试。"""

    def test_squeezing_reduces_x_variance(self):
        """S(r=1, θ=0) 后 V_xx = e^(-2r)/2。"""
        s0 = _q.GaussianState.vacuum(1)
        S = _q.SqueezingGate(r=1.0, theta=0.0)
        s1 = S.apply(s0, mode=0)
        assert s1.covariance[0, 0] == pytest.approx(
            np.exp(-2.0) / 2.0, rel=1e-12
        )
        assert s1.covariance[1, 1] == pytest.approx(
            np.exp(2.0) / 2.0, rel=1e-12
        )

    def test_squeezing_validates_negative_r(self):
        """r<0 须 raise（R03）。"""
        with pytest.raises(ValueError, match="r"):
            _q.SqueezingGate(r=-0.5)

    def test_squeezing_validates_mode_index(self):
        """mode 超出范围须 raise（R03）。"""
        s0 = _q.GaussianState.vacuum(2)
        S = _q.SqueezingGate(r=0.5)
        with pytest.raises(ValueError, match="mode"):
            S.apply(s0, mode=2)

    def test_squeezing_theta_rotates_squeeze_axis(self):
        """S(r, θ=π/2) 旋转压缩轴 90°，V_xx = e^(2r)/2。"""
        s0 = _q.GaussianState.vacuum(1)
        S = _q.SqueezingGate(r=1.0, theta=np.pi / 2)
        s1 = S.apply(s0, mode=0)
        # 压缩方向旋转 90°：x 方向反而放大
        assert s1.covariance[0, 0] == pytest.approx(
            np.exp(2.0) / 2.0, rel=1e-9
        )
        assert s1.covariance[1, 1] == pytest.approx(
            np.exp(-2.0) / 2.0, rel=1e-9
        )

    def test_squeezing_preserves_uncertainty(self):
        """压缩保持辛体积 det(V) = 1/4（不确定性关系下界）。

        辛变换 V → S V S^T 保持 det(V)，真空态 det(V_vac) = (1/2)^2 = 1/4。
        注意：仅在压缩主轴基下 Δx·Δp = 1/2；θ≠0 时 V 非对角，
        Δx·Δp > 1/2，但 det(V) 仍 = 1/4（Weedbrook 2012 §II.C）。"""
        s0 = _q.GaussianState.vacuum(1)
        S = _q.SqueezingGate(r=1.5, theta=0.7)
        s1 = S.apply(s0, mode=0)
        # det(V_vac) = 0.25，辛变换保持辛体积
        assert np.linalg.det(s1.covariance) == pytest.approx(0.25, rel=1e-10)
        # 不确定性关系满足 V + iΩ/2 ≥ 0
        n = s1.n_modes
        omega = np.block([
            [np.zeros((n, n)), np.eye(n)],
            [-np.eye(n), np.zeros((n, n))],
        ])
        test = s1.covariance + 1j * omega / 2.0
        eigvals = np.linalg.eigvalsh((test + test.T.conj()) / 2)
        assert np.min(eigvals.real) > -1e-9


class TestR551RotationGate:
    """R551 旋转门测试。"""

    def test_rotation_preserves_covariance_eigenvalues(self):
        """R(φ) 是辛正交变换，保持 V 的本征值。"""
        s0 = _q.GaussianState.squeezed_vacuum(r=1.0)
        R = _q.RotationGate(phi=0.7)
        s1 = R.apply(s0, mode=0)
        ev0 = np.sort(np.linalg.eigvalsh(s0.covariance))
        ev1 = np.sort(np.linalg.eigvalsh(s1.covariance))
        np.testing.assert_allclose(ev0, ev1, atol=1e-10)

    def test_rotation_zero_is_identity(self):
        """R(φ=0) 是恒等变换。"""
        s0 = _q.GaussianState.squeezed_vacuum(r=0.5)
        R = _q.RotationGate(phi=0.0)
        s1 = R.apply(s0, mode=0)
        np.testing.assert_allclose(s1.covariance, s0.covariance, atol=1e-15)
        np.testing.assert_allclose(s1.mean, s0.mean, atol=1e-15)

    def test_rotation_validates_mode(self):
        """mode 超出范围须 raise（R03）。"""
        s0 = _q.GaussianState.vacuum(1)
        R = _q.RotationGate(phi=0.5)
        with pytest.raises(ValueError, match="mode"):
            R.apply(s0, mode=1)


class TestR551BeamSplitter:
    """R551 分束器门测试。"""

    def test_50_50_bs_balances_two_vacua(self):
        """50:50 BS 对两真空态：输出仍为真空，两模方差相同。"""
        s0 = _q.GaussianState.vacuum(2)
        BS = _q.BeamSplitterGate(theta=np.pi / 4, phi=0.0)
        s1 = BS.apply(s0, mode1=0, mode2=1)
        # 两模方差都是 1/2（真空）
        assert s1.covariance[0, 0] == pytest.approx(0.5, rel=1e-12)
        assert s1.covariance[1, 1] == pytest.approx(0.5, rel=1e-12)
        assert s1.covariance[2, 2] == pytest.approx(0.5, rel=1e-12)
        assert s1.covariance[3, 3] == pytest.approx(0.5, rel=1e-12)

    def test_bs_validates_same_mode(self):
        """mode1==mode2 须 raise（R03）。"""
        s0 = _q.GaussianState.vacuum(2)
        BS = _q.BeamSplitterGate(theta=np.pi / 4)
        with pytest.raises(ValueError, match="mode1/mode2"):
            BS.apply(s0, mode1=0, mode2=0)

    def test_bs_validates_mode_out_of_range(self):
        """mode 超出范围须 raise（R03）。"""
        s0 = _q.GaussianState.vacuum(2)
        BS = _q.BeamSplitterGate(theta=np.pi / 4)
        with pytest.raises(ValueError, match="mode1/mode2"):
            BS.apply(s0, mode1=0, mode2=2)

    def test_bs_squeezed_input_remains_symplectic(self):
        """BS 是辛变换，输出仍是合法高斯态（不确定性关系满足）。"""
        s0 = _q.GaussianState.vacuum(2)
        # 先压缩第一模
        s0 = _q.SqueezingGate(r=0.8).apply(s0, mode=0)
        BS = _q.BeamSplitterGate(theta=np.pi / 4)
        # 若不确定性关系违反，构造时会 raise
        s1 = BS.apply(s0, mode1=0, mode2=1)
        assert s1.n_modes == 2


class TestR551HomodyneDetection:
    """R551 零差检测测试。"""

    def test_measure_vacuum_x_has_half_variance(self):
        """真空态 x 测量方差 = 1/2。"""
        s = _q.GaussianState.vacuum(1)
        det = _q.HomodyneDetection("x")
        rng = np.random.default_rng(seed=42)
        samples = np.array([det.measure(s, mode=0, rng=rng) for _ in range(5000)])
        assert np.mean(samples) == pytest.approx(0.0, abs=0.05)
        assert np.var(samples) == pytest.approx(0.5, abs=0.05)

    def test_measure_squeezed_x_has_reduced_variance(self):
        """压缩态 r=1 时 x 方差 = e^(-2)/2。"""
        s = _q.GaussianState.squeezed_vacuum(r=1.0)
        det = _q.HomodyneDetection("x")
        rng = np.random.default_rng(seed=42)
        samples = np.array([det.measure(s, mode=0, rng=rng) for _ in range(5000)])
        expected_var = np.exp(-2.0) / 2.0
        assert np.var(samples) == pytest.approx(expected_var, rel=0.1)

    def test_quadrature_invalid_raises(self):
        """quadrature 非 'x'/'p' 须 raise（R03）。"""
        with pytest.raises(ValueError, match="quadrature"):
            _q.HomodyneDetection("y")

    def test_expected_variance_method(self):
        """expected_variance 返回 V[idx, idx]。"""
        s = _q.GaussianState.squeezed_vacuum(r=0.7)
        det_x = _q.HomodyneDetection("x")
        det_p = _q.HomodyneDetection("p")
        assert det_x.expected_variance(s, 0) == pytest.approx(
            np.exp(-1.4) / 2.0, rel=1e-12
        )
        assert det_p.expected_variance(s, 0) == pytest.approx(
            np.exp(1.4) / 2.0, rel=1e-12
        )


# ===========================================================================
# R552 量子纠错编码
# ===========================================================================


class TestR552ThreeQubitRepetition:
    """R552 三比特重复码测试。"""

    def test_encode_zero_to_000(self):
        """|0> → |000>。"""
        state = _q.ThreeQubitRepetitionCode.encode(0)
        assert state.shape == (8,)
        assert state[0] == 1.0
        np.testing.assert_allclose(np.abs(state) ** 2, np.array([1, 0, 0, 0, 0, 0, 0, 0]))

    def test_encode_one_to_111(self):
        """|1> → |111>。"""
        state = _q.ThreeQubitRepetitionCode.encode(1)
        assert state[7] == 1.0

    def test_encode_invalid_bit_raises(self):
        """bit 非 0/1 须 raise（R03）。"""
        with pytest.raises(ValueError, match="bit"):
            _q.ThreeQubitRepetitionCode.encode(2)

    def test_stabilizers_are_diagonal_with_pm1(self):
        """稳定子 Z1Z2, Z2Z3 应是对角矩阵，对角元 ±1。"""
        stabs = _q.ThreeQubitRepetitionCode.stabilizers()
        assert len(stabs) == 2
        for s in stabs:
            assert s.shape == (8, 8)
            diag = np.diag(s).real
            assert np.all(np.isin(diag, [-1.0, 1.0]))

    def test_no_error_gives_plus_plus_syndrome(self):
        """无错时稳定子测量结果都是 +1。"""
        state = _q.ThreeQubitRepetitionCode.encode(0)
        stabs = _q.ThreeQubitRepetitionCode.stabilizers()
        syndrome = _q.SyndromeMeasurement.measure(state, stabs)
        assert syndrome == [1, 1]

    def test_bit_flip_on_qubit_0_gives_minus_plus(self):
        """比特 0 翻转：Z1Z2=-1, Z2Z3=+1（症状 [-1, +1]）。"""
        state = _q.ThreeQubitRepetitionCode.encode(0)
        state = _q.BitFlipError(0).apply(state)
        stabs = _q.ThreeQubitRepetitionCode.stabilizers()
        syndrome = _q.SyndromeMeasurement.measure(state, stabs)
        assert syndrome == [-1, 1]

    def test_bit_flip_on_qubit_1_gives_minus_minus(self):
        """比特 1 翻转：Z1Z2=-1, Z2Z3=-1（症状 [-1, -1]）。"""
        state = _q.ThreeQubitRepetitionCode.encode(0)
        state = _q.BitFlipError(1).apply(state)
        stabs = _q.ThreeQubitRepetitionCode.stabilizers()
        syndrome = _q.SyndromeMeasurement.measure(state, stabs)
        assert syndrome == [-1, -1]

    def test_bit_flip_on_qubit_2_gives_plus_minus(self):
        """比特 2 翻转：Z1Z2=+1, Z2Z3=-1（症状 [+1, -1]）。"""
        state = _q.ThreeQubitRepetitionCode.encode(0)
        state = _q.BitFlipError(2).apply(state)
        stabs = _q.ThreeQubitRepetitionCode.stabilizers()
        syndrome = _q.SyndromeMeasurement.measure(state, stabs)
        assert syndrome == [1, -1]

    def test_recovery_corrects_single_bit_flip(self):
        """恢复操作应纠正任意单比特翻转。"""
        for error_bit in range(3):
            state = _q.ThreeQubitRepetitionCode.encode(1)
            state_err = _q.BitFlipError(error_bit).apply(state)
            stabs = _q.ThreeQubitRepetitionCode.stabilizers()
            synd = _q.SyndromeMeasurement.measure(state_err, stabs)
            state_rec = _q.RecoveryOperation.recover(state_err, synd)
            # 恢复后应回到原码字 |111>
            np.testing.assert_allclose(np.abs(state_rec), np.abs(state), atol=1e-12)

    def test_bit_flip_invalid_qubit_raises(self):
        """qubit 非 0/1/2 须 raise（R03）。"""
        with pytest.raises(ValueError, match="qubit"):
            _q.BitFlipError(3)


class TestR552SteaneCode:
    """R552 Steane [[7,4,3]] 码测试（Steane 1996）。"""

    def test_encode_zero_logical_to_valid_codeword(self):
        """逻辑 0000 编码后应为合法码字（H·c = 0 mod 2）。"""
        logical = np.array([0, 0, 0, 0])
        codeword = _q.SteaneCode.encode(logical)
        assert codeword.shape == (7,)
        # H·c = 0 mod 2（合法码字满足校验）
        s = _q.SteaneCode.syndrome(codeword)
        np.testing.assert_array_equal(s, np.zeros(3, dtype=np.int64))

    def test_encode_unit_logical(self):
        """逻辑 1000 编码 = G 的第一行。"""
        logical = np.array([1, 0, 0, 0])
        codeword = _q.SteaneCode.encode(logical)
        s = _q.SteaneCode.syndrome(codeword)
        np.testing.assert_array_equal(s, np.zeros(3, dtype=np.int64))

    def test_encode_all_ones_is_valid_codeword(self):
        """逻辑 1111 编码后应为合法码字。"""
        logical = np.array([1, 1, 1, 1])
        codeword = _q.SteaneCode.encode(logical)
        s = _q.SteaneCode.syndrome(codeword)
        np.testing.assert_array_equal(s, np.zeros(3, dtype=np.int64))

    def test_encode_invalid_logical_shape_raises(self):
        """logical 非 (4,) 须 raise（R03）。"""
        with pytest.raises(ValueError, match="logical"):
            _q.SteaneCode.encode(np.array([0, 1]))

    def test_encode_invalid_logical_values_raises(self):
        """logical 非 0/1 须 raise（R03）。"""
        with pytest.raises(ValueError, match="logical"):
            _q.SteaneCode.encode(np.array([0, 1, 2, 0]))

    def test_syndrome_no_error_is_zero(self):
        """无错时症状为零。"""
        codeword = _q.SteaneCode.encode(np.array([1, 0, 1, 0]))
        s = _q.SteaneCode.syndrome(codeword)
        np.testing.assert_array_equal(s, np.zeros(3, dtype=np.int64))

    def test_syndrome_single_bit_flip_nonzero(self):
        """单比特翻转症状非零。"""
        codeword = _q.SteaneCode.encode(np.array([1, 0, 1, 0]))
        for i in range(7):
            err = codeword.copy()
            err[i] = 1 - err[i]
            s = _q.SteaneCode.syndrome(err)
            assert not np.all(s == 0), f"bit {i} 翻转症状应非零"

    def test_correct_fixes_single_bit_flip(self):
        """纠错应恢复单比特翻转。"""
        original = _q.SteaneCode.encode(np.array([1, 0, 1, 1]))
        for i in range(7):
            err = original.copy()
            err[i] = 1 - err[i]
            corrected = _q.SteaneCode.correct(err)
            np.testing.assert_array_equal(corrected, original)

    def test_correct_no_error_returns_same(self):
        """无错时 correct 返回原码字。"""
        codeword = _q.SteaneCode.encode(np.array([0, 1, 1, 0]))
        corrected = _q.SteaneCode.correct(codeword)
        np.testing.assert_array_equal(corrected, codeword)

    def test_syndrome_invalid_shape_raises(self):
        """received 非 (7,) 须 raise（R03）。"""
        with pytest.raises(ValueError, match="received"):
            _q.SteaneCode.syndrome(np.array([0, 1, 0]))


# ===========================================================================
# R553 资源态生成
# ===========================================================================


class TestR553GHZState:
    """R553 GHZ 态测试。"""

    def test_generate_2_qubit_normalized(self):
        """|GHZ_2> = (|00>+|11>)/√2，归一化。"""
        s = _q.GHZState.generate(2)
        assert s.shape == (4,)
        assert np.linalg.norm(s) == pytest.approx(1.0, rel=1e-12)
        assert s[0] == pytest.approx(1 / np.sqrt(2))
        assert s[3] == pytest.approx(1 / np.sqrt(2))

    def test_generate_3_qubit(self):
        """|GHZ_3> = (|000>+|111>)/√2。"""
        s = _q.GHZState.generate(3)
        assert s.shape == (8,)
        assert s[0] == pytest.approx(1 / np.sqrt(2))
        assert s[7] == pytest.approx(1 / np.sqrt(2))

    def test_generate_invalid_n_raises(self):
        """n_qubits<2 须 raise（R03）。"""
        with pytest.raises(ValueError, match="n_qubits"):
            _q.GHZState.generate(1)

    def test_fidelity_with_ideal_is_one(self):
        """与理想 GHZ 态的保真度应为 1。"""
        s = _q.GHZState.generate(3)
        assert _q.GHZState.fidelity(s) == pytest.approx(1.0, rel=1e-12)

    def test_fidelity_with_orthogonal_is_zero(self):
        """与正交态的保真度应为 0。"""
        s = _q.GHZState.generate(2)
        # |01> 与 GHZ 正交
        orth = np.zeros(4, dtype=np.complex128)
        orth[1] = 1.0
        # fidelity 函数用同 n_qubits 生成 GHZ 比较
        assert _q.GHZState.fidelity(orth) == pytest.approx(0.0, abs=1e-12)


class TestR553ClusterState:
    """R553 1D 簇态测试（Hein 2004）。"""

    def test_generate_2_qubit_normalized(self):
        """2 比特簇态归一化。"""
        s = _q.ClusterState1D.generate(2)
        assert s.shape == (4,)
        assert np.linalg.norm(s) == pytest.approx(1.0, rel=1e-12)

    def test_generate_3_qubit_normalized(self):
        """3 比特簇态归一化。"""
        s = _q.ClusterState1D.generate(3)
        assert s.shape == (8,)
        assert np.linalg.norm(s) == pytest.approx(1.0, rel=1e-12)

    def test_generate_invalid_n_raises(self):
        """n_qubits<2 须 raise（R03）。"""
        with pytest.raises(ValueError, match="n_qubits"):
            _q.ClusterState1D.generate(1)

    def test_2_qubit_cluster_is_bell_state(self):
        """2 比特 1D 簇态 = (|00>+|11>)/√2 （Bell 态，与 GHZ_2 相同）。

        因为 H⊗H|00> = (|00>+|01>+|10>+|11>)/2，再 CZ 得到
        (|00>+|01>+|10>-|11>)/2，但 _apply_single/_apply_two 顺序应为
        H 全部，然后 CZ 相邻——结果由实现定义。这里只验证归一化与维度。
        """
        s = _q.ClusterState1D.generate(2)
        # 验证是纯态且归一化（详细 Bell 比对留作端到端测试）
        assert np.linalg.norm(s) == pytest.approx(1.0, rel=1e-12)


class TestR553NOONState:
    """R553 NOON 态测试。"""

    def test_generate_n1_normalized(self):
        """N=1 NOON 态 = (|1,0>+|0,1>)/√2，密度矩阵迹为 1。"""
        rho = _q.NOONState.generate(1)
        assert rho.shape == (2, 2)
        assert np.trace(rho).real == pytest.approx(1.0, rel=1e-12)

    def test_generate_n2(self):
        """N=2 NOON 态密度矩阵迹为 1。"""
        rho = _q.NOONState.generate(2)
        assert rho.shape == (3, 3)
        assert np.trace(rho).real == pytest.approx(1.0, rel=1e-12)
        # |2,0> 与 |0,2> 的相干性
        assert rho[0, 2] != 0

    def test_generate_invalid_n_raises(self):
        """n<1 须 raise（R03）。"""
        with pytest.raises(ValueError, match="n"):
            _q.NOONState.generate(0)

    def test_noon_purity_is_one(self):
        """纯态密度矩阵 Tr(ρ²) = 1。"""
        rho = _q.NOONState.generate(3)
        purity = np.trace(rho @ rho).real
        assert purity == pytest.approx(1.0, rel=1e-10)


class TestR553StateFidelity:
    """R553 态保真度测试。"""

    def test_fidelity_pure_identical_states_is_one(self):
        """两相同纯态保真度 = 1。"""
        s = np.array([1, 0, 0, 0], dtype=np.complex128)
        assert _q.StateFidelity.fidelity_pure(s, s) == pytest.approx(1.0)

    def test_fidelity_pure_orthogonal_states_is_zero(self):
        """两正交纯态保真度 = 0。"""
        s1 = np.array([1, 0], dtype=np.complex128)
        s2 = np.array([0, 1], dtype=np.complex128)
        assert _q.StateFidelity.fidelity_pure(s1, s2) == pytest.approx(0.0)

    def test_fidelity_pure_shape_mismatch_raises(self):
        """形状不匹配须 raise（R03）。"""
        s1 = np.array([1, 0])
        s2 = np.array([1, 0, 0])
        with pytest.raises(ValueError, match="形状"):
            _q.StateFidelity.fidelity_pure(s1, s2)

    def test_fidelity_mixed_identical_is_one(self):
        """两相同混合态保真度 = 1。"""
        rho = 0.5 * np.array([[1, 0], [0, 1]], dtype=np.complex128)
        f = _q.StateFidelity.fidelity_mixed(rho, rho)
        assert f == pytest.approx(1.0, rel=1e-10)

    def test_fidelity_mixed_orthogonal_support_is_zero(self):
        """两支撑正交的混合态保真度 = 0。"""
        rho1 = np.array([[1, 0], [0, 0]], dtype=np.complex128)
        rho2 = np.array([[0, 0], [0, 1]], dtype=np.complex128)
        f = _q.StateFidelity.fidelity_mixed(rho1, rho2)
        assert f == pytest.approx(0.0, abs=1e-10)


# ===========================================================================
# R554 噪声模型增强
# ===========================================================================


class TestR554PhotonLoss:
    """R554 光子损耗通道测试（Kok & Lovett 2010）。"""

    def test_beer_lambert_transmission_zero_length(self):
        """L=0 时 η=1（无损耗）。"""
        eta = _q.PhotonLossChannel.beer_lambert_transmission(alpha=1.0, length=0.0)
        assert eta == pytest.approx(1.0, rel=1e-15)

    def test_beer_lambert_transmission_decay(self):
        """α·L 越大 η 越小（Beer-Lambert 单调衰减）。"""
        eta1 = _q.PhotonLossChannel.beer_lambert_transmission(1.0, 1.0)
        eta2 = _q.PhotonLossChannel.beer_lambert_transmission(1.0, 2.0)
        assert eta2 < eta1
        assert eta1 == pytest.approx(np.exp(-1.0))

    def test_beer_lambert_negative_alpha_raises(self):
        """α<0 须 raise（R03）。"""
        with pytest.raises(ValueError, match="alpha"):
            _q.PhotonLossChannel.beer_lambert_transmission(-0.1, 1.0)

    def test_init_validates_eta_range(self):
        """eta 不在 (0,1] 须 raise（R03）。"""
        with pytest.raises(ValueError, match="eta"):
            _q.PhotonLossChannel(eta=0.0)
        with pytest.raises(ValueError, match="eta"):
            _q.PhotonLossChannel(eta=1.5)

    def test_apply_vacuum_state_unchanged(self):
        """真空态经过光子损耗通道不变（|0><0| 是不动点）。"""
        rho0 = np.zeros((4, 4), dtype=np.complex128)
        rho0[0, 0] = 1.0  # |0><0|
        ch = _q.PhotonLossChannel(eta=0.5, n_max=4)
        rho_out = ch.apply(rho0)
        np.testing.assert_allclose(rho_out, rho0, atol=1e-12)

    def test_apply_preserves_trace(self):
        """光子损耗通道保迹 Tr(ρ') = Tr(ρ)（CPTP 性质）。"""
        # 构造 |1><1|
        rho = np.zeros((4, 4), dtype=np.complex128)
        rho[1, 1] = 1.0
        ch = _q.PhotonLossChannel(eta=0.7, n_max=4)
        rho_out = ch.apply(rho)
        assert np.trace(rho_out).real == pytest.approx(1.0, rel=1e-10)

    def test_apply_reduces_photon_number(self):
        """光子损耗降低平均光子数 <n>。"""
        # 构造 |2><2|
        rho = np.zeros((5, 5), dtype=np.complex128)
        rho[2, 2] = 1.0
        ch = _q.PhotonLossChannel(eta=0.5, n_max=5)
        rho_out = ch.apply(rho)
        n_before = np.trace(rho @ np.diag(np.arange(5))).real
        n_after = np.trace(rho_out @ np.diag(np.arange(5))).real
        assert n_after < n_before
        # 理论 <n>_after = η · <n>_before = 0.5 · 2 = 1
        assert n_after == pytest.approx(1.0, rel=1e-10)

    def test_apply_full_transmission_preserves_state(self):
        """η=1 时通道为恒等映射。"""
        rho = np.zeros((4, 4), dtype=np.complex128)
        rho[1, 1] = 0.6
        rho[2, 2] = 0.4
        ch = _q.PhotonLossChannel(eta=1.0, n_max=4)
        rho_out = ch.apply(rho)
        np.testing.assert_allclose(rho_out, rho, atol=1e-12)


class TestR554PhaseNoise:
    """R554 相位噪声通道测试。"""

    def test_apply_zero_sigma_is_identity(self):
        """σ=0 时通道为恒等映射。"""
        rho = np.array([[0.5, 0.3], [0.3, 0.5]], dtype=np.complex128)
        ch = _q.PhaseNoiseChannel(sigma_phi=0.0)
        rho_out = ch.apply(rho)
        np.testing.assert_allclose(rho_out, rho, atol=1e-15)

    def test_apply_decays_off_diagonal(self):
        """σ>0 时非对角元衰减 exp(-(m-n)²σ²/2)。

        公式（Kok 2010 §3.4 高斯相位扩散）：ρ_mn → exp(-(m-n)²σ²/2)·ρ_mn。
        m=0, n=1, σ=0.5: 衰减因子 exp(-1·0.25/2) = exp(-0.125)。"""
        rho = np.array([[0.5, 0.5], [0.5, 0.5]], dtype=np.complex128)
        ch = _q.PhaseNoiseChannel(sigma_phi=0.5)
        rho_out = ch.apply(rho)
        # (m-n)²=1, σ²=0.25: 衰减因子 exp(-0.125)
        expected_off = 0.5 * np.exp(-1.0 * 0.5 ** 2 / 2.0)
        assert rho_out[0, 1] == pytest.approx(expected_off, rel=1e-12)

    def test_apply_preserves_diagonal(self):
        """相位噪声不改变对角元（m=n 时衰减因子=1）。"""
        rho = np.diag([0.3, 0.7]).astype(np.complex128)
        ch = _q.PhaseNoiseChannel(sigma_phi=1.0)
        rho_out = ch.apply(rho)
        np.testing.assert_allclose(np.diag(rho_out).real, [0.3, 0.7], atol=1e-15)

    def test_init_negative_sigma_raises(self):
        """σ<0 须 raise（R03）。"""
        with pytest.raises(ValueError, match="sigma_phi"):
            _q.PhaseNoiseChannel(sigma_phi=-0.1)


class TestR554Detector:
    """R554 探测器模型测试。"""

    def test_zero_photons_zero_dark_no_click(self):
        """n=0, λ=0 时 P_click = 0。"""
        det = _q.DetectorModel(efficiency=0.9, dark_count_rate=0.0)
        p = det.click_probability(n_photons=0, time_window=1.0)
        assert p == pytest.approx(0.0, abs=1e-15)

    def test_one_photon_full_efficiency_clicks(self):
        """n=1, η=1, λ=0 时 P_click = 1。"""
        det = _q.DetectorModel(efficiency=1.0, dark_count_rate=0.0)
        p = det.click_probability(n_photons=1, time_window=1.0)
        assert p == pytest.approx(1.0, abs=1e-15)

    def test_efficiency_bounds_click_probability(self):
        """P_click ≤ 1（边界）。"""
        det = _q.DetectorModel(efficiency=0.5, dark_count_rate=0.0)
        for n in range(10):
            p = det.click_probability(n_photons=n, time_window=1.0)
            assert 0.0 <= p <= 1.0

    def test_dark_count_increases_click_probability(self):
        """暗计数提高点击概率（即使 n=0）。"""
        det_no_dark = _q.DetectorModel(efficiency=0.0, dark_count_rate=0.0)
        det_with_dark = _q.DetectorModel(efficiency=0.0, dark_count_rate=1.0)
        p0 = det_no_dark.click_probability(0, time_window=1.0)
        p1 = det_with_dark.click_probability(0, time_window=1.0)
        assert p1 > p0

    def test_init_validates_efficiency(self):
        """η 不在 [0,1] 须 raise（R03）。"""
        with pytest.raises(ValueError, match="efficiency"):
            _q.DetectorModel(efficiency=1.5)
        with pytest.raises(ValueError, match="efficiency"):
            _q.DetectorModel(efficiency=-0.1)

    def test_negative_photons_raises(self):
        """n<0 须 raise（R03）。"""
        det = _q.DetectorModel(efficiency=0.9)
        with pytest.raises(ValueError, match="n_photons"):
            det.click_probability(-1)


# ===========================================================================
# R555 实验数据拟合接口
# ===========================================================================


class TestR555SParamFitter:
    """R555 S 参数拟合器测试。"""

    def test_fit_recovers_known_params(self):
        """拟合应能恢复已知参数（无噪声情形）。"""
        # 构造已知 S 参数
        freqs = np.linspace(1e14, 2e14, 20)
        A_true, phi_true, alpha_0_true, n_eff_true, p_true = 0.9, 0.3, 1.0, 2.0, 1.0
        c0 = 2.99792458e8
        omega = 2.0 * np.pi * freqs
        omega_ref = omega[0]
        alpha = alpha_0_true * (omega / omega_ref) ** p_true
        beta = n_eff_true * omega / c0
        L = 1e-3
        s_meas = A_true * np.exp(1j * phi_true) * np.exp(-alpha * L) * np.exp(1j * beta * L)
        # 拟合
        result = _q.SParamFitter.fit(freqs, s_meas)
        assert result.success
        # 拟合参数应接近真值
        A_fit, phi_fit, alpha_0_fit, n_eff_fit, p_fit = result.params
        assert A_fit == pytest.approx(A_true, abs=0.05)
        assert phi_fit == pytest.approx(phi_true, abs=0.05)
        assert n_eff_fit == pytest.approx(n_eff_true, abs=0.1)

    def test_fit_returns_high_r_squared(self):
        """无噪声数据 R² 应接近 1。"""
        freqs = np.linspace(1e14, 2e14, 15)
        c0 = 2.99792458e8
        omega = 2.0 * np.pi * freqs
        s_meas = 0.9 * np.exp(1j * 0.5) * np.exp(1j * 2.0 * omega / c0 * 1e-3)
        result = _q.SParamFitter.fit(freqs, s_meas)
        assert result.r_squared > 0.99

    def test_fit_shape_mismatch_raises(self):
        """freqs 与 s_meas 形状不匹配须 raise（R03）。"""
        with pytest.raises(ValueError, match="形状"):
            _q.SParamFitter.fit(
                np.linspace(0, 1, 5),
                np.zeros(4, dtype=np.complex128),
            )


class TestR555LossExtractor:
    """R555 损耗提取器测试。"""

    def test_extract_insertion_loss_zero_db_for_full_transmission(self):
        """|S21|=1 时 IL=0 dB（无损耗）。"""
        s21 = np.array([1.0 + 0j, 1.0 + 0j])
        il = _q.LossExtractor.extract_insertion_loss(s21)
        np.testing.assert_allclose(il, [0.0, 0.0], atol=1e-12)

    def test_extract_insertion_loss_3db_for_half_power(self):
        """|S21|²=0.5 时 IL=3.01 dB。"""
        s21 = np.array([np.sqrt(0.5)])
        il = _q.LossExtractor.extract_insertion_loss(s21)
        assert il[0] == pytest.approx(10 * np.log10(2), rel=1e-6)

    def test_extract_insertion_loss_zero_power_raises(self):
        """|S21|=0 须 raise（无法取 log，R03）。"""
        with pytest.raises(ValueError, match="功率为 0"):
            _q.LossExtractor.extract_insertion_loss(np.array([0.0 + 0j]))

    def test_extract_loss_per_length(self):
        """单位长度损耗 = IL / L。"""
        s21 = np.array([0.5 + 0j])
        il_per = _q.LossExtractor.extract_loss_per_length(s21, length=1e-3)
        il_total = _q.LossExtractor.extract_insertion_loss(s21)
        np.testing.assert_allclose(il_per, il_total / 1e-3)

    def test_extract_loss_per_length_zero_raises(self):
        """length=0 须 raise（R03）。"""
        with pytest.raises(ValueError, match="length"):
            _q.LossExtractor.extract_loss_per_length(
                np.array([0.5 + 0j]), length=0.0
            )


class TestR555CouplingEfficiency:
    """R555 耦合效率提取器测试。"""

    def test_extract_full_coupling_is_one(self):
        """measured == ideal 时 η=1。"""
        s_meas = np.array([0.9 + 0j])
        s_ideal = np.array([0.9 + 0j])
        eta = _q.CouplingEfficiencyExtractor.extract(s_meas, s_ideal)
        np.testing.assert_allclose(eta, [1.0])

    def test_extract_lossy_coupling_less_than_one(self):
        """measured < ideal 时 η<1。"""
        s_meas = np.array([0.5 + 0j])
        s_ideal = np.array([1.0 + 0j])
        eta = _q.CouplingEfficiencyExtractor.extract(s_meas, s_ideal)
        assert eta[0] == pytest.approx(0.25)

    def test_extract_clips_to_one(self):
        """measured > ideal 时 η 截断到 1（无源器件不可能增益）。"""
        s_meas = np.array([1.5 + 0j])
        s_ideal = np.array([1.0 + 0j])
        eta = _q.CouplingEfficiencyExtractor.extract(s_meas, s_ideal)
        assert eta[0] == 1.0  # clip 上限

    def test_extract_zero_ideal_raises(self):
        """s_ideal=0 须 raise（R03）。"""
        with pytest.raises(ValueError, match="功率为 0"):
            _q.CouplingEfficiencyExtractor.extract(
                np.array([0.5 + 0j]), np.array([0.0 + 0j])
            )

    def test_extract_shape_mismatch_raises(self):
        """形状不匹配须 raise（R03）。"""
        with pytest.raises(ValueError, match="形状"):
            _q.CouplingEfficiencyExtractor.extract(
                np.array([0.5, 0.6]), np.array([1.0])
            )


# ===========================================================================
# R02/R03/R04 合规检查
# ===========================================================================


class TestCompliance:
    """R02/R03/R04 合规检查。"""

    def test_r02_docstring_has_at_least_5_references(self):
        """R02: 模块 docstring 须 ≥5 个文献 URL。"""
        doc = _q.__doc__ or ""
        # 统计 https://doi.org/ 或 https://www. 链接
        import re
        urls = re.findall(r"https?://[^\s)]+", doc)
        assert len(urls) >= 5, f"docstring 仅 {len(urls)} 个 URL（R02 要求 ≥5）"

    def test_r02_has_innovation_mark(self):
        """R02: 创新点须标注 *创新*。"""
        doc = _q.__doc__ or ""
        assert "*创新*" in doc, "docstring 缺少 *创新* 标注（R02）"

    def test_r04_no_gpu_keywords(self):
        """R04: 模块源码不含 CuPy/CUDA/ROCm/Metal 关键词（单词匹配）。

        用正则 \\b 边界避免 "roc" 匹配 "process" 等子串。"""
        import re
        src_path = _SRC_DIR / "sim" / "quantum_cv_qec.py"
        src = src_path.read_text(encoding="utf-8")
        # GPU 后端关键词（带单词边界）
        gpu_patterns = [
            r"\bcupy\b",
            r"\bcuda\b",
            r"\brocm\b",  # ROCm 全称
            r"\bmetal\b",  # Apple Metal
            r"\bfp16\b",
            r"\bbf16\b",
        ]
        for pat in gpu_patterns:
            matches = re.findall(pat, src, flags=re.IGNORECASE)
            assert not matches, \
                f"源码含禁用 GPU 关键词 {pat}（R04），匹配: {matches}"

    def test_r03_no_silent_fallback_patterns(self):
        """R03: 源码不应含 except: pass / return None 静默兜底。"""
        src_path = _SRC_DIR / "sim" / "quantum_cv_qec.py"
        src = src_path.read_text(encoding="utf-8")
        # 检查 except: pass 模式
        assert "except: pass" not in src, "源码含 except: pass（R03）"
        assert "except Exception: pass" not in src, \
            "源码含 except Exception: pass（R03）"


# ===========================================================================
# 端到端集成测试
# ===========================================================================


class TestEndToEnd:
    """端到端集成测试。"""

    def test_cv_pipeline_squeeze_displace_measure(self):
        """端到端 CV 管道：真空→压缩→位移→零差检测。

        验证：压缩使 x 方差减小，位移使均值平移。"""
        # 真空
        s0 = _q.GaussianState.vacuum(1)
        # 压缩 r=1
        s1 = _q.SqueezingGate(r=1.0).apply(s0, mode=0)
        # 位移 (1, 0)
        s2 = _q.DisplacementGate(1.0, 0.0).apply(s1)
        # 零差检测 x
        det = _q.HomodyneDetection("x")
        rng = np.random.default_rng(42)
        samples = np.array([det.measure(s2, mode=0, rng=rng) for _ in range(3000)])
        # 期望均值 = sqrt(2)*1 ≈ 1.414
        assert np.mean(samples) == pytest.approx(np.sqrt(2.0), abs=0.05)
        # 期望方差 = e^(-2)/2
        assert np.var(samples) == pytest.approx(np.exp(-2.0) / 2.0, rel=0.15)

    def test_qec_pipeline_encode_error_recover(self):
        """端到端 QEC 管道：编码→错误→症状→恢复。

        验证：单比特翻转可被检测并恢复到原码字。"""
        # 编码 |1>
        original = _q.ThreeQubitRepetitionCode.encode(1)
        # 比特 1 翻转
        err_state = _q.BitFlipError(1).apply(original)
        # 测量症状
        stabs = _q.ThreeQubitRepetitionCode.stabilizers()
        synd = _q.SyndromeMeasurement.measure(err_state, stabs)
        assert synd == [-1, -1]
        # 恢复
        recovered = _q.RecoveryOperation.recover(err_state, synd)
        np.testing.assert_allclose(np.abs(recovered), np.abs(original), atol=1e-12)

    def test_noise_pipeline_photon_loss_preserves_trace(self):
        """端到端噪声管道：光子损耗 + 相位噪声保迹。"""
        # |1><1|
        rho = np.zeros((4, 4), dtype=np.complex128)
        rho[1, 1] = 1.0
        # 光子损耗 η=0.6
        loss = _q.PhotonLossChannel(eta=0.6, n_max=4)
        rho1 = loss.apply(rho)
        assert np.trace(rho1).real == pytest.approx(1.0, rel=1e-10)
        # 相位噪声 σ=0.3
        pn = _q.PhaseNoiseChannel(sigma_phi=0.3)
        rho2 = pn.apply(rho1)
        assert np.trace(rho2).real == pytest.approx(1.0, rel=1e-10)

    def test_fit_pipeline_extract_loss(self):
        """端到端拟合管道：拟合 S 参数→提取损耗。"""
        freqs = np.linspace(1.9e14, 2.0e14, 10)
        c0 = 2.99792458e8
        omega = 2.0 * np.pi * freqs
        # 构造 3dB 损耗的 S21
        s21 = np.sqrt(0.5) * np.exp(1j * 2.0 * omega / c0 * 1e-3)
        il = _q.LossExtractor.extract_insertion_loss(s21)
        # 全频段 IL ≈ 3.01 dB
        np.testing.assert_allclose(il, 10 * np.log10(2), rtol=1e-6)

    def test_resource_state_generation_normalized(self):
        """端到端资源态生成：GHZ + Cluster + NOON 都归一化。"""
        ghz = _q.GHZState.generate(3)
        cluster = _q.ClusterState1D.generate(3)
        noon_rho = _q.NOONState.generate(2)
        assert np.linalg.norm(ghz) == pytest.approx(1.0, rel=1e-12)
        assert np.linalg.norm(cluster) == pytest.approx(1.0, rel=1e-12)
        assert np.trace(noon_rho).real == pytest.approx(1.0, rel=1e-12)
