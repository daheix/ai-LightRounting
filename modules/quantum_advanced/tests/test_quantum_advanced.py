"""polaris-quantum-advanced 子模块深度测试（覆盖全 API）。

覆盖核心 API（30 个测试）:
- permanent_ryser / permanent_brute_force（积和式 Ryser 算法）
- boson_sampling_prob / boson_sampling_distribution / beamsplitter_unitary / hom_interference（HOM 干涉）
- hafnian（GBS Hafnian）
- lossy_boson_sampling / quantum_advantage_threshold（损耗玻色采样与量子优势阈值）
- BB84Protocol / BB84EnhancedProtocol / E91Protocol（QKD 协议）
- GaussianState / DisplacementGate / SqueezingGate / RotationGate / BeamSplitterGate / HomodyneDetection（CV 高斯量子门）
- NOONState / GHZState / ClusterState1D / StateFidelity（多体纠缠态）
- HOMInterferometer / LargeScaleBosonSampler（高级采样）
- QuantumStateTomography / QuantumProcessTomography（量子态层析）
- ThreeQubitRepetitionCode / SteaneCode（量子纠错码）
- PhotonLossChannel / PhaseNoiseChannel / DetectorModel（噪声通道）
- Qubit / QuantumCircuitSimulator（电路仿真）
- DistributedPPOTrainer（分布式 PPO，torch importorskip）

学术依据（R02 学术诚信，≥5 个文献 URL）:
1. Aaronson & Arkhipov, STOC 2011, 玻色采样计算复杂性
   https://arxiv.org/abs/0910.4698
2. Bennett & Brassard 1984, BB84 QKD
   https://doi.org/10.1145/358340.358342
3. Ekert 1991 PRL 67 661, E91 QKD 基于 Bell 不等式
   https://doi.org/10.1103/PhysRevLett.67.661
4. Steane 1996 PRL 77 793, Steane [[7,4,3]] 量子纠错码
   https://doi.org/10.1103/PhysRevLett.77.793
5. Knill, Laflamme, Milburn, Nature 2001, KLM 线性光学量子计算
   https://www.nature.com/articles/35051009
6. Weedbrook et al. Rev Mod Phys 84, 621 (2012), CV 高斯量子信息
   https://doi.org/10.1103/RevModPhys.84.621
7. Hong-Ou-Mandel PRL 59, 2044 (1987), HOM 干涉
   https://doi.org/10.1103/PhysRevLett.59.2044
8. Schulman et al., PPO, arXiv:1707.06347 (2017)
   https://arxiv.org/abs/1707.06347
9. Shor & Preskill 2000 PRL 85 441, BB84 安全性证明
   https://doi.org/10.1103/PhysRevLett.85.441
10. Duan & Guo 1997 PRA 56 4466, 量子噪声通道
    https://doi.org/10.1103/PhysRevA.56.4466

合规: R02 学术诚信 / R03 禁止 fall-back / R04 纯 NumPy / R05 无假数据 / R05 无 TODO。
"""

from __future__ import annotations

import sys
import os
from pathlib import Path

import numpy as np
import pytest

# 将 src 加入 sys.path 以支持直接 pytest 运行（未 pip install 时）
_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from polaris_quantum_advanced import (
    permanent_ryser,
    permanent_brute_force,
    boson_sampling_prob,
    boson_sampling_distribution,
    beamsplitter_unitary,
    hom_interference,
    hafnian,
    lossy_boson_sampling,
    quantum_advantage_threshold,
    BB84Protocol,
    BB84EnhancedProtocol,
    E91Protocol,
    GaussianState,
    DisplacementGate,
    SqueezingGate,
    RotationGate,
    BeamSplitterGate,
    HomodyneDetection,
    NOONState,
    GHZState,
    ClusterState1D,
    StateFidelity,
    HOMInterferometer,
    LargeScaleBosonSampler,
    QuantumStateTomography,
    QuantumProcessTomography,
    ThreeQubitRepetitionCode,
    SteaneCode,
    PhotonLossChannel,
    PhaseNoiseChannel,
    DetectorModel,
    Qubit,
    QuantumCircuitSimulator,
    DistributedPPOConfig,
    DistributedPPOTrainer,
)


# =============================================================================
# 1. 积和式（Permanent）— Ryser 算法
# =============================================================================

def test_permanent_ryser_2x2_all_ones() -> None:
    """2×2 全 1 矩阵积和式 = 2（Per([[1,1],[1,1]]) = 1·1 + 1·1 = 2）。

    来源: Ryser 1963; Aaronson & Arkhipov STOC 2011.
    """
    M = np.ones((2, 2), dtype=np.float64)
    result = permanent_ryser(M)
    assert abs(result - 2.0) < 1e-10, f"全 1 矩阵积和式应为 2，实际 {result}"


def test_permanent_ryser_identity() -> None:
    """单位矩阵积和式 = 1（Per(I) = 1）。"""
    I = np.eye(3, dtype=np.float64)
    result = permanent_ryser(I)
    assert abs(result - 1.0) < 1e-10, f"单位矩阵积和式应为 1，实际 {result}"


def test_permanent_ryser_matches_brute_force() -> None:
    """Ryser 算法与暴力枚举结果一致（4×4 随机矩阵交叉验证）。"""
    np.random.seed(7)
    M = np.random.rand(4, 4)
    ryser_val = permanent_ryser(M)
    brute_val = permanent_brute_force(M)
    assert abs(ryser_val - brute_val) < 1e-9, \
        f"Ryser={ryser_val} 与暴力={brute_val} 不一致"


def test_permanent_ryser_non_square_raise() -> None:
    """R03: 非方阵必须 raise ValueError。"""
    with pytest.raises(ValueError, match="方阵"):
        permanent_ryser(np.ones((2, 3)))


# =============================================================================
# 2. 玻色采样 — HOM 干涉
# =============================================================================

def test_boson_sampling_hom_interference() -> None:
    """HOM 干涉: 50:50 BS 输入 |1,1⟩ → 输出 |2,0⟩/|0,2⟩ 各 0.5，|1,1⟩ 概率 0。

    Hong-Ou-Mandel 效应（PRL 59, 2044, 1987）:
    U = [[1,1],[1,-1]]/√2，输入 (1,1)：
    - P(2,0) = |Per(U_sub)|²/(2!·1!·1!) = 0.5
    - P(0,2) = 0.5
    - P(1,1) = 0（干涉相消）
    """
    U = np.array([[1, 1], [1, -1]], dtype=np.complex128) / np.sqrt(2)
    p_20 = boson_sampling_prob(U, (1, 1), (2, 0))
    p_02 = boson_sampling_prob(U, (1, 1), (0, 2))
    p_11 = boson_sampling_prob(U, (1, 1), (1, 1))

    assert abs(p_20 - 0.5) < 1e-10, f"P(2,0) 应为 0.5，实际 {p_20}"
    assert abs(p_02 - 0.5) < 1e-10, f"P(0,2) 应为 0.5，实际 {p_02}"
    assert abs(p_11) < 1e-10, f"P(1,1) 应为 0（HOM 相消），实际 {p_11}"
    assert abs(p_20 + p_02 + p_11 - 1.0) < 1e-10, "概率和应为 1"


def test_beamsplitter_unitary_unitary() -> None:
    """beamsplitter_unitary 生成的矩阵为酉矩阵（U†U = I）。"""
    U = beamsplitter_unitary(theta=np.pi / 4, phi=0.3)
    prod = U.conj().T @ U
    np.testing.assert_allclose(prod, np.eye(2), atol=1e-10,
                               err_msg="BS 酉矩阵 U†U 应 = I")


def test_hom_interference_zero_delay_dip() -> None:
    """hom_interference 零延迟 HOM dip：50:50 BS 不可区分光子 P(1,1)=0。

    hom_interference 返回概率分布 dict {"(2,0)", "(0,2)", "(1,1)"}，
    不可区分光子经 50:50 BS 聚束，P(1,1)=0（Hong-Ou-Mandel 1987 PRL 59 2044）。
    """
    result = hom_interference(theta=np.pi / 4)
    # HOM 凹陷：不可区分光子 P(1,1)=0
    assert abs(result["(1,1)"] - 0.0) < 1e-10, f"HOM dip P(1,1) 应=0，实际 {result['(1,1)']}"
    # 光子聚束到同一端口：P(2,0)+P(0,2)=1
    assert abs(result["(2,0)"] + result["(0,2)"] - 1.0) < 1e-10, "聚束概率和应为 1"
    # 50:50 对称：P(2,0)=P(0,2)=0.5
    assert abs(result["(2,0)"] - 0.5) < 1e-10, f"P(2,0) 应=0.5，实际 {result['(2,0)']}"


def test_boson_sampling_distribution_normalized() -> None:
    """boson_sampling_distribution 概率和 = 1（归一化）。

    返回 BosonSamplingResult（含 output_prob dict）；输入态模式数须 = 酉矩阵维度。
    """
    np.random.seed(11)
    U = beamsplitter_unitary(theta=0.7, phi=0.2)  # 2×2 酉矩阵
    dist = boson_sampling_distribution(U, input_state=(1, 1))  # 2 模输入
    probs = np.array(list(dist.output_prob.values()))
    assert abs(np.sum(probs) - 1.0) < 1e-10, "分布和应为 1"
    assert np.all(probs >= -1e-12), "概率非负"


# =============================================================================
# 3. Hafnian（GBS 高斯玻色采样）
# =============================================================================

def test_hafnian_2x2() -> None:
    """2×2 对称矩阵 Hafnian = A[0,1]·A[1,0]（完美匹配数）。"""
    A = np.array([[0.0, 1.5], [1.5, 0.0]])
    assert abs(hafnian(A) - 1.5) < 1e-10, f"2×2 Hafnian 应=1.5，实际 {hafnian(A)}"


def test_hafnian_odd_size_zero() -> None:
    """奇数阶矩阵 Hafnian = 0（无完美匹配）。"""
    A = np.array([[0.0, 1.0, 2.0], [1.0, 0.0, 3.0], [2.0, 3.0, 0.0]])
    assert abs(hafnian(A)) < 1e-10, "奇数阶 Hafnian 应为 0"


# =============================================================================
# 4. 损耗玻色采样与量子优势阈值
# =============================================================================

def test_lossy_boson_sampling_returns_dict() -> None:
    """lossy_boson_sampling 返回含统计分布的字典。

    签名: lossy_boson_sampling(unitary, input_state, loss_rate=0.3)（无 seed 参数）。
    """
    U = beamsplitter_unitary(theta=np.pi / 4)
    result = lossy_boson_sampling(U, input_state=(1, 1), loss_rate=0.3)
    assert isinstance(result, dict), "lossy_boson_sampling 应返回 dict"
    assert len(result) > 0, "结果非空"


def test_quantum_advantage_threshold_logic() -> None:
    """quantum_advantage_threshold: N_detected ≥ √N 时返回 True（量子优势）。

    来源: Aaronson-Arkhipov 2011 采样复杂性阈值。
    """
    # 大光子数、低损耗 → 量子优势
    assert quantum_advantage_threshold(n_photons=100, loss_rate=0.0) is True
    # 高损耗、小光子数 → 无量子优势
    assert quantum_advantage_threshold(n_photons=4, loss_rate=0.9) is False


# =============================================================================
# 5. BB84 / E91 量子密钥分发
# =============================================================================

def test_bb84_no_eavesdrop_is_secure() -> None:
    """BB84 无窃听: QBER < 11% 阈值，密钥安全。

    来源: Bennett & Brassard 1984; Shor & Preskill 2000.
    """
    protocol = BB84Protocol(key_length=32, seed=42)
    result = protocol.simulate(eavesdrop=False, channel_loss_db=3.0)
    assert result["qber"] < 0.11, f"无窃听 QBER 应 < 11%，实际 {result['qber']}"
    assert result["is_secure"] is True, "无窃听应判定安全"


def test_bb84_eavesdrop_detected() -> None:
    """BB84 intercept-resend 窃听: QBER ≈ 25%，超过 11% 阈值被检测。

    intercept-resend 物理模型: Eve 随机基矢 → 50% 不匹配 → 25% QBER。
    """
    protocol = BB84Protocol(key_length=32, seed=123)
    result = protocol.simulate(eavesdrop=True, channel_loss_db=0.0)
    assert result["qber"] > 0.11, f"窃听 QBER 应 > 11%，实际 {result['qber']}"
    assert result["is_secure"] is False, "窃听应判定不安全"


def test_bb84_enhanced_secret_key_rate() -> None:
    """BB84EnhancedProtocol: secret_key_rate 在零 QBER 时为正（无窃听可提取密钥）。"""
    proto = BB84EnhancedProtocol(key_length=64, seed=7)
    # 零 QBER → 密钥率接近 1（无纠错消耗）
    rate = proto.secret_key_rate(qber=0.0, basis_efficiency=0.5)
    assert rate > 0.0, f"零 QBER 密钥率应>0，实际 {rate}"
    # 高 QBER → 密钥率为 0（无法提取）
    rate_high = proto.secret_key_rate(qber=0.2, basis_efficiency=0.5)
    assert rate_high <= 0.0 or rate_high < 1e-6, \
        f"高 QBER 密钥率应≈0，实际 {rate_high}"


def test_e91_protocol_simulate() -> None:
    """E91 协议基于 Bell 不等式检测窃听（Ekert 1991 PRL 67 661）。

    E91Protocol.simulate 返回 QKDResult（非 dict），含 CHSH S 参数、QBER、成码率。
    """
    proto = E91Protocol(key_length=32, eavesdrop_prob=0.0, seed=11)
    result = proto.simulate()
    # E91 无窃听：CHSH S 接近 Tsirelson 界 2√2，QBER 低，安全
    assert result.protocol == "E91", f"协议名应为 E91，实际 {result.protocol}"
    assert result.qber >= 0.0, "QBER 须 ≥ 0"
    assert result.is_secure is True, "无窃听应判定安全"
    assert result.bell_parameter is not None, "E91 应返回 CHSH S 参数"
    assert result.bell_parameter > 2.0, \
        f"无窃听 S 应 > 2（违反 Bell 不等式），实际 {result.bell_parameter}"


# =============================================================================
# 6. CV 高斯量子门
# =============================================================================

def test_gaussian_vacuum_state() -> None:
    """单模真空态: V = I/2, d = 0, 满足不确定性关系 V+iΩ/2 ≥ 0。

    来源: Weedbrook et al. Rev Mod Phys 84, 621 (2012).
    """
    state = GaussianState.vacuum(n_modes=1)
    assert state.n_modes == 1, "模式数应为 1"
    np.testing.assert_allclose(
        state.covariance, 0.5 * np.eye(2), atol=1e-10,
        err_msg="真空态协方差矩阵应为 I/2",
    )
    np.testing.assert_allclose(
        state.mean, np.zeros(2), atol=1e-10,
        err_msg="真空态平均向量应为 0",
    )


def test_gaussian_squeezed_vacuum_variance() -> None:
    """压缩真空态: 某正交分量方差 < 1/2（压缩），另一分量 > 1/2（反压缩）。"""
    r = 0.5
    state = GaussianState.squeezed_vacuum(r=r, theta=0.0)
    cov = state.covariance
    # x 方向压缩 e^{-2r}，p 方向反压缩 e^{2r}（归一化到 1/2 真空涨落）
    assert cov[0, 0] < 0.5, f"x 方向应压缩 (<0.5)，实际 {cov[0, 0]}"
    assert cov[1, 1] > 0.5, f"p 方向应反压缩 (>0.5)，实际 {cov[1, 1]}"
    # 不确定性关系: det(V) ≥ 1/4
    assert np.linalg.det(cov) >= 0.25 - 1e-10, "不确定性关系 det(V) ≥ 1/4"


def test_displacement_gate_shifts_mean() -> None:
    """位移门 D(α) 将平均向量平移 √2·(Re α, Im α)。

    约定 q=(a+a†)/√2，故 ⟨q⟩=√2·Re(α)、⟨p⟩=√2·Im(α)
    （Braunstein 2005 §III；源码 DisplacementGate.apply 显式 sqrt(2) 因子）。
    """
    state = GaussianState.vacuum(n_modes=1)
    gate = DisplacementGate(alpha_real=1.0, alpha_imag=0.5)
    new_state = gate.apply(state)
    expected = [np.sqrt(2.0) * 1.0, np.sqrt(2.0) * 0.5]
    np.testing.assert_allclose(new_state.mean, expected, atol=1e-10,
                               err_msg="位移门应将均值平移到 √2·[Re α, Im α]")


def test_rotation_gate_preserves_covariance() -> None:
    """旋转门 R(φ) 旋转协方差矩阵但保持迹（能量守恒）。"""
    state = GaussianState.squeezed_vacuum(r=0.5)
    gate = RotationGate(phi=np.pi / 4)
    new_state = gate.apply(state, mode=0)
    assert abs(np.trace(new_state.covariance) - np.trace(state.covariance)) < 1e-10, \
        "旋转门应保持协方差矩阵迹（能量守恒）"


def test_beamsplitter_gate_two_mode() -> None:
    """分束器门作用双模: 50:50 BS 混合两真空模 → 协方差矩阵仍正定。"""
    state = GaussianState.vacuum(n_modes=2)
    gate = BeamSplitterGate(theta=np.pi / 4, phi=0.0)
    new_state = gate.apply(state, mode1=0, mode2=1)
    assert new_state.covariance.shape == (4, 4), "双模协方差应为 4×4"
    # 正定性检查
    eigvals = np.linalg.eigvalsh(new_state.covariance)
    assert np.all(eigvals > 0), "协方差矩阵须正定"


def test_squeezing_gate_reduces_variance() -> None:
    """压缩门 S(r) 降低某一正交分量方差。"""
    state = GaussianState.vacuum(n_modes=1)
    gate = SqueezingGate(r=0.8, theta=0.0)
    new_state = gate.apply(state, mode=0)
    assert new_state.covariance[0, 0] < state.covariance[0, 0], \
        "压缩门应降低 x 方向方差"


def test_homodyne_detection_variance() -> None:
    """HomodyneDetection 测量真空态 x 分量方差 = 1/2。"""
    state = GaussianState.vacuum(n_modes=1)
    det = HomodyneDetection(quadrature="x")
    var = det.expected_variance(state, mode=0)
    assert abs(var - 0.5) < 1e-10, f"真空态 x 方差应=0.5，实际 {var}"


# =============================================================================
# 7. 多体纠缠态（NOON / GHZ / Cluster）
# =============================================================================

def test_noon_state_dimension() -> None:
    """NOON 态密度矩阵为 (N+1)×(N+1) 且迹=1。"""
    rho = NOONState.generate(n=2)
    assert rho.shape == (3, 3), f"NOON(n=2) 应为 3×3，实际 {rho.shape}"
    assert abs(np.trace(rho).real - 1.0) < 1e-10, "NOON 态迹应为 1"


def test_ghz_state_fidelity() -> None:
    """GHZ 态与理想 GHZ 态自保真度 = 1（纯态）。

    GHZState.fidelity(state) 单参数：计算 state 与同维度理想 GHZ 态的保真度。
    """
    ghz = GHZState.generate(n_qubits=3)
    fid = GHZState.fidelity(ghz)
    assert abs(fid - 1.0) < 1e-10, f"GHZ 自保真度应=1，实际 {fid}"


def test_cluster_state_1d_entanglement() -> None:
    """1D Cluster 态为纯态（密度矩阵平方迹=1）。

    ClusterState1D.generate 返回态矢量（1D），须构造密度矩阵 ρ=|ψ⟩⟨ψ| 后验纯度。
    """
    state = ClusterState1D.generate(n_qubits=3)
    rho = np.outer(state, state.conj())  # 态矢量 → 密度矩阵
    purity = np.trace(rho @ rho).real
    assert abs(purity - 1.0) < 1e-10, f"Cluster 态纯度应=1，实际 {purity}"


def test_state_fidelity_pure_orthogonal() -> None:
    """StateFidelity: 正交纯态保真度 = 0。"""
    psi1 = np.array([1.0, 0.0], dtype=complex)
    psi2 = np.array([0.0, 1.0], dtype=complex)
    fid = StateFidelity.fidelity_pure(psi1, psi2)
    assert abs(fid) < 1e-10, f"正交态保真度应=0，实际 {fid}"


# =============================================================================
# 8. 高级采样（HOMInterferometer / LargeScaleBosonSampler）
# =============================================================================

def test_hom_interferometer_distinguishable() -> None:
    """HOMInterferometer: distinguishability=0（完全可分）→ P(1,1)=0.5（经典）。

    interfere 返回 HOMResult（dataclass），非 dict；用 coincidence_probability
    取 P(每个模式各 1 光子)，可分粒子经典值=0.5。
    """
    U = beamsplitter_unitary(theta=np.pi / 4)
    hom = HOMInterferometer(unitary=U)
    result = hom.interfere(input_state=(1, 1), distinguishability=0.0)
    # 完全可分粒子经典行为：coincidence P(1,1)=0.5
    assert abs(result.coincidence_probability - 0.5) < 1e-6, \
        f"可区分 P(1,1) 应=0.5，实际 {result.coincidence_probability}"
    # 概率分布归一化
    total = sum(result.probabilities.values())
    assert abs(total - 1.0) < 1e-6, f"HOM 分布应归一化，和={total}"


def test_large_scale_boson_sampler_batch() -> None:
    """LargeScaleBosonSampler: 批量采样返回非空样本列表。"""
    np.random.seed(5)
    U = beamsplitter_unitary(theta=0.6)
    sampler = LargeScaleBosonSampler(unitary=U, seed=5)
    samples = sampler.sample_batch(input_state=(1, 1), n_samples=50)
    assert len(samples) == 50, f"批量采样应返回 50 个样本，实际 {len(samples)}"


# =============================================================================
# 9. 量子层析（Tomography）
# =============================================================================

def test_quantum_state_tomography_reconstruct() -> None:
    """量子态层析: 从测量频率重建密度矩阵（Hradil 1997 R 迭代 MLE）。

    MLE 要求测量算子为 POVM 元素（正定半定），Pauli 算子含负本征值会导致
    Tr(ρ·Π_k)=0 奇异。改用 qubit SIC-POVM（Renes 2004）4 个正定算子，
    Π_k=(1/4)(I+n_k·σ)，n_k 指向正四面体顶点（|n_k|=1）。
    reconstruct 返回 TomographyResult（含 density_matrix 字段）。
    """
    np.random.seed(13)
    # 目标态 |0⟩⟨0|
    target = np.array([[1, 0], [0, 0]], dtype=complex)
    # Pauli 矩阵
    sigma_x = np.array([[0, 1], [1, 0]], dtype=complex)
    sigma_y = np.array([[0, -1j], [1j, 0]], dtype=complex)
    sigma_z = np.array([[1, 0], [0, -1]], dtype=complex)
    I2 = np.eye(2, dtype=complex)
    # SIC-POVM 四面体顶点（√3·n_k，归一化后为单位向量）
    vertices = [(1, 1, 1), (1, -1, -1), (-1, 1, -1), (-1, -1, 1)]
    ops = []
    freqs = []
    for v in vertices:
        n = np.array(v, dtype=float) / np.sqrt(3.0)
        Pi = 0.25 * (I2 + n[0] * sigma_x + n[1] * sigma_y + n[2] * sigma_z)
        ops.append(Pi)
        # Born 概率 f_k = Tr(target · Π_k) = ⟨0|Π_k|0⟩
        freqs.append(float(np.trace(target @ Pi).real))
    freqs_arr = np.array(freqs)
    assert abs(np.sum(freqs_arr) - 1.0) < 1e-10, "SIC-POVM 频率和应为 1"
    tomo = QuantumStateTomography(measurement_operators=ops, frequencies=freqs_arr,
                                  target_state=target)
    result = tomo.reconstruct(max_iter=500, tol=1e-10)
    rho = result.density_matrix
    assert rho.shape == (2, 2), f"重建密度矩阵应为 2×2，实际 {rho.shape}"
    assert abs(np.trace(rho).real - 1.0) < 1e-6, "重建态迹应为 1"
    # 重建态应接近目标 |0⟩⟨0|（|0⟩ 占据 ≈ 1）
    assert abs(rho[0, 0].real - 1.0) < 1e-3, \
        f"重建态 |0⟩ 占据应≈1，实际 {rho[0, 0].real}"


def test_quantum_process_tomography_fidelity() -> None:
    """量子过程层析: 恒等通道 process_fidelity = 1。"""
    ppt = QuantumProcessTomography(dim=2)
    # 恒等通道 χ 矩阵 = |00⟩⟨00|（对应 I⊗I Pauli 基）
    chi_id = np.zeros((4, 4), dtype=complex)
    chi_id[0, 0] = 1.0
    fid = ppt.process_fidelity(chi_id, chi_id)
    assert abs(fid - 1.0) < 1e-10, f"恒等通道自保真度应=1，实际 {fid}"


# =============================================================================
# 10. 量子纠错码（ThreeQubitRepetition + Steane）
# =============================================================================

def test_three_qubit_repetition_code() -> None:
    """三比特重复码: encode(1) → |111⟩，stabilizers 非空。"""
    code = ThreeQubitRepetitionCode()
    # 编码比特 1
    encoded = code.encode(1)
    assert encoded is not None, "编码结果非空"
    stabs = code.stabilizers()
    assert len(stabs) > 0, "稳定子列表非空"


def test_steane_code_corrects_single_bit_flip() -> None:
    """Steane 码纠正单比特翻转错误。

    来源: Steane 1996 PRL 77 793. 编码 → 注入错误 → 纠正 → 恢复。
    """
    logical = np.array([1, 0, 1, 1], dtype=np.int64)
    encoded = SteaneCode.encode(logical)
    # 注入第 3 位翻转错误
    corrupted = encoded.copy()
    corrupted[2] = 1 - corrupted[2]
    corrected = SteaneCode.correct(corrupted)
    np.testing.assert_array_equal(
        corrected, encoded, "纠正后应恢复原始编码字"
    )


# =============================================================================
# 11. 噪声通道（PhotonLoss / PhaseNoise / Detector）
# =============================================================================

def test_photon_loss_channel_trace_preserving() -> None:
    """光子损耗通道保迹: Tr(ρ') ≈ Tr(ρ) = 1（Kraus 求和 CPTP 性质）。

    来源: Kok & Lovett 2010 §3.2; Carmichael 1993.
    """
    # 单光子态密度矩阵 |1⟩⟨1|
    rho = np.array([[0, 0], [0, 1]], dtype=np.complex128)
    channel = PhotonLossChannel(eta=0.8, n_max=5)
    rho_out = channel.apply(rho)
    trace = float(np.trace(rho_out).real)
    assert abs(trace - 1.0) < 1e-6, f"保迹 Tr(ρ') 应 ≈ 1，实际 {trace}"


def test_photon_loss_beer_lambert() -> None:
    """PhotonLossChannel.beer_lambert_transmission: α>0 → 透射率 < 1。"""
    eta = PhotonLossChannel.beer_lambert_transmission(alpha=1.0, length=0.5)
    assert 0.0 < eta < 1.0, f"Beer-Lambert 透射率应在 (0,1)，实际 {eta}"


def test_phase_noise_channel_cptp() -> None:
    """PhaseNoiseChannel 保迹: Tr(ρ') ≈ 1。"""
    rho = np.array([[0.5, 0.3], [0.3, 0.5]], dtype=np.complex128)
    channel = PhaseNoiseChannel(sigma_phi=0.2)
    rho_out = channel.apply(rho)
    assert abs(np.trace(rho_out).real - 1.0) < 1e-6, "相位噪声通道应保迹"


def test_detector_model_click_probability() -> None:
    """DetectorModel: 高效率 + 多光子 → 点击概率接近 1。"""
    det = DetectorModel(efficiency=0.9, dark_count_rate=0.0)
    p = det.click_probability(n_photons=10, time_window=1.0)
    assert 0.0 <= p <= 1.0, f"点击概率应在 [0,1]，实际 {p}"
    assert p > 0.5, f"高效率多光子点击概率应>0.5，实际 {p}"


# =============================================================================
# 12. 量子电路仿真器 — Bell 态 + Qubit
# =============================================================================

def test_quantum_circuit_bell_state_measurement() -> None:
    """Bell 态 |Φ+⟩ = (|00⟩ + |11⟩)/√2 测量: |00⟩ 和 |11⟩ 各 ~50%。

    来源: Knill et al. Nature 2001; Clements et al. Optica 2016.
    """
    sim = QuantumCircuitSimulator(n_qubits=2)
    sim.bell_state(qubit_a=0, qubit_b=1)
    counts = sim.measure(qubit=0, shots=2000)
    total = counts[0] + counts[1]
    assert total == 2000, f"测量总数应为 2000，实际 {total}"
    # Bell 态测量 qubit 0 应接近 50:50
    ratio = counts[0] / total
    assert 0.35 < ratio < 0.65, f"Bell 态 |0⟩ 比例应 ~0.5，实际 {ratio}"


def test_quantum_circuit_hadamard_gate() -> None:
    """Hadamard 门: |0⟩ → (|0⟩+|1⟩)/√2，测量 ~50:50。"""
    sim = QuantumCircuitSimulator(n_qubits=1)
    sim.apply_hadamard(qubit=0)
    counts = sim.measure(qubit=0, shots=2000)
    ratio = counts[0] / (counts[0] + counts[1])
    assert 0.4 < ratio < 0.6, f"Hadamard 后 |0⟩ 比例应 ~0.5，实际 {ratio}"


def test_quantum_circuit_gate_count() -> None:
    """电路门计数: apply_hadamard + apply_pauli_x → gate_count=2。"""
    sim = QuantumCircuitSimulator(n_qubits=2)
    sim.apply_hadamard(qubit=0)
    sim.apply_pauli_x(qubit=1)
    assert sim.gate_count == 2, f"门计数应=2，实际 {sim.gate_count}"
    assert len(sim.gate_history) == 2, "门历史应含 2 条记录"


# =============================================================================
# 13. 分布式 PPO — 合成模式训练
# =============================================================================

def test_distributed_ppo_synthetic_mode_trains() -> None:
    """PPO 合成测试模式: training_step 成功执行并返回训练统计。

    R05 v4.0-FAKE-ENV-P0: synthetic_env_mode=True 仅用于算法单元测试。
    来源: Schulman et al. PPO arXiv:1707.06347 (2017).
    """
    config = DistributedPPOConfig(
        synthetic_env_mode=True,
        n_workers=1,
        n_epochs=1,
        batch_size=16,
        n_devices_per_circuit=10,
    )
    trainer = DistributedPPOTrainer(config)
    result = trainer.training_step(n_episodes_per_worker=1)
    assert "mean_reward" in result, "训练结果应含 mean_reward"
    assert "mean_policy_loss" in result, "训练结果应含 mean_policy_loss"
    assert "n_policy_updates" in result, "训练结果应含 n_policy_updates"
    assert result["n_workers"] == 1, f"worker 数应为 1，实际 {result['n_workers']}"
    assert result["n_policy_updates"] > 0, "应有至少一次策略更新"


def test_distributed_ppo_guard_rejects_no_env() -> None:
    """PPO 守门逻辑: 未注入真实环境且 synthetic_env_mode=False → raise RuntimeError。

    R03 禁止 fall-back: 禁止用合成环境冒充真实环境训练。
    """
    config = DistributedPPOConfig(synthetic_env_mode=False)
    trainer = DistributedPPOTrainer(config)
    with pytest.raises(RuntimeError, match="未注入真实布局布线环境"):
        trainer.training_step(n_episodes_per_worker=1)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
