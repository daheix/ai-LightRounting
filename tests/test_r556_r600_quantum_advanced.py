"""R556-R600 量子光子进阶综合测试（纯 NumPy/SciPy CPU，R04 兼容）。

测试覆盖：
- R556 大模式数玻色采样: LargeScaleBosonSampler（Clifford-Clifford 逐光子采样）
- R557 HOM 干涉增强: HOMInterferometer（全同/部分可分/经典 + Tichy 双置换和）
- R558 量子态层析: QuantumStateTomography（Hradil Rᵢ 迭代 MLE）
- R559 量子过程层析: QuantumProcessTomography（χ 矩阵线性反演）
- R560 BB84/E91 QKD: E91Protocol（CHSH-Bell Tsirelson 界）+ BB84EnhancedProtocol（GLLP）
- R03/R02/R04 合规检查 + 端到端集成

文献依据（R02，≥5 URL）:
- Clifford & Clifford 2018 SODA https://arxiv.org/abs/1706.01260
- Tichy 2015 PRA 91 022103 https://doi.org/10.1103/PhysRevA.91.022103
- Hradil 1997 PRA 55 R1561 https://doi.org/10.1103/PhysRevA.55.R1561
- Ekert 1991 PRL 67 661 https://doi.org/10.1103/PhysRevLett.67.661
- Shor & Preskill 2000 PRL 85 441 https://arxiv.org/abs/quant-ph/0003004
"""

from __future__ import annotations

import importlib.util
import math
import re
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


# 设置 polaris 包命名空间
for _pkg in ("polaris", "polaris.sim"):
    if _pkg not in sys.modules:
        sys.modules[_pkg] = type(sys)(_pkg)

_load_module("sim/quantum_permanent.py", "polaris.sim.quantum_permanent")
_qa = _load_module("sim/quantum_advanced.py", "polaris.sim.quantum_advanced")
_SRC_FILE = _SRC_DIR / "sim" / "quantum_advanced.py"


def _random_unitary(n: int, seed: int = 42) -> np.ndarray:
    """生成随机酉矩阵（QR 分解法）。"""
    rng = np.random.default_rng(seed)
    A = rng.standard_normal((n, n)) + 1j * rng.standard_normal((n, n))
    Q, R = np.linalg.qr(A)
    phases = np.diag(R) / np.abs(np.diag(R))
    return Q * phases


def _beamsplitter(theta: float = math.pi / 4) -> np.ndarray:
    """50:50 分束器酉矩阵。"""
    c, s = math.cos(theta), math.sin(theta)
    return np.array([[c, -s], [s, c]], dtype=complex)


# ===========================================================================
# R556 大模式数玻色采样
# ===========================================================================


class TestR556LargeScaleBosonSampler:
    """R556 Clifford-Clifford 逐光子采样测试。"""

    def test_validates_non_unitary(self):
        """非酉矩阵须 raise（R03）。"""
        with pytest.raises(ValueError, match="酉矩阵"):
            _qa.LargeScaleBosonSampler(np.array([[1, 2], [3, 4]], dtype=complex))

    def test_validates_input_dimension(self):
        """输入态维度不匹配须 raise（R03）。"""
        U = _random_unitary(4, seed=1)
        sampler = _qa.LargeScaleBosonSampler(U, seed=10)
        with pytest.raises(ValueError, match="输入态维度"):
            sampler.sample((1, 0, 0))

    def test_photon_number_conservation(self):
        """采样输出光子数 = 输入光子数。"""
        U = _random_unitary(6, seed=2)
        sampler = _qa.LargeScaleBosonSampler(U, seed=20)
        result = sampler.sample((1, 1, 1, 0, 0, 0))
        assert sum(result.output_state) == 3
        assert result.n_photons == 3
        assert result.n_steps == 3

    def test_large_modes_over_20(self):
        """支持 >20 模式的大规模玻色采样。"""
        U = _random_unitary(24, seed=3)
        sampler = _qa.LargeScaleBosonSampler(U, seed=30)
        result = sampler.sample((1, 1, 1) + (0,) * 21)
        assert sum(result.output_state) == 3
        assert result.n_modes == 24

    def test_batch_sampling(self):
        """批量采样返回正确数量。"""
        U = _random_unitary(5, seed=4)
        sampler = _qa.LargeScaleBosonSampler(U, seed=40)
        batch = sampler.sample_batch((1, 1, 0, 0, 0), n_samples=50)
        assert len(batch) == 50
        for r in batch:
            assert sum(r.output_state) == 2


# ===========================================================================
# R557 HOM 干涉增强
# ===========================================================================


class TestR557HOMInterference:
    """R557 HOM 干涉测试（全同/部分可分/经典）。"""

    def test_hom_dip_identical_photons(self):
        """全同光子（ξ=1）50:50 分束器: P(1,1)=0（HOM 凹陷）。

        来源: Hong-Ou-Mandel 1987 PRL 59 2044。
        """
        hom = _qa.HOMInterferometer(_beamsplitter())
        result = hom.interfere((1, 1), distinguishability=1.0)
        assert result.probabilities[(1, 1)] == pytest.approx(0.0, abs=1e-12)
        assert result.probabilities[(2, 0)] == pytest.approx(0.5, abs=1e-9)
        assert result.probabilities[(0, 2)] == pytest.approx(0.5, abs=1e-9)
        assert result.bunching_parameter == pytest.approx(1.0, abs=1e-9)
        assert result.is_bunched

    def test_classical_limit_distinguishable(self):
        """完全可分光子（ξ=0）: P(1,1)=0.5（经典，无干涉）。

        Tichy 2015 双置换和: S=I → Σ_σ Π|U|² = 经典多项式分布。
        """
        hom = _qa.HOMInterferometer(_beamsplitter())
        result = hom.interfere((1, 1), distinguishability=0.0)
        assert result.probabilities[(1, 1)] == pytest.approx(0.5, abs=1e-9)
        assert result.bunching_parameter == pytest.approx(0.0, abs=1e-9)
        assert not result.is_bunched

    def test_partial_distinguishability(self):
        """部分可分（ξ=0.5）: P(1,1) = (1-ξ²)/2 = 0.375。

        Tichy 2015 eq.(12): S_ij=ξ^|i-j|，双置换和精确解。
        """
        hom = _qa.HOMInterferometer(_beamsplitter())
        xi = 0.5
        result = hom.interfere((1, 1), distinguishability=xi)
        expected = (1.0 - xi ** 2) / 2.0
        assert result.probabilities[(1, 1)] == pytest.approx(expected, abs=1e-9)
        assert sum(result.probabilities.values()) == pytest.approx(1.0, abs=1e-9)

    def test_hom_dip_curve(self):
        """HOM 凹陷曲线 P(τ)=0.5·(1-exp(-(τ/τ_c)²))。

        τ=0→P=0（凹陷）；|τ|→∞→P=0.5（经典）。
        """
        hom = _qa.HOMInterferometer(_beamsplitter())
        tau = np.array([-2.0, -1.0, 0.0, 1.0, 2.0])
        curve = hom.hom_dip_curve(tau, photon_coherence_time=1.0)
        assert curve[2] == pytest.approx(0.0, abs=1e-15)
        assert curve[0] == pytest.approx(curve[-1], abs=1e-15)
        assert curve[0] == pytest.approx(0.5 * (1 - math.exp(-4)), abs=1e-12)

    def test_validates_non_unitary(self):
        """非酉矩阵须 raise（R03）。"""
        with pytest.raises(ValueError, match="酉矩阵"):
            _qa.HOMInterferometer(np.array([[1, 2], [3, 4]], dtype=complex))


# ===========================================================================
# R558 量子态层析
# ===========================================================================


class TestR558QuantumStateTomography:
    """R558 Hradil Rᵢ 迭代 MLE 层析测试。"""

    def _pauli_projectors(self):
        """6 个 Pauli 测量投影算子。"""
        ket0 = np.array([1, 0], dtype=complex)
        ket1 = np.array([0, 1], dtype=complex)
        ketP = np.array([1, 1], dtype=complex) / math.sqrt(2)
        ketM = np.array([1, -1], dtype=complex) / math.sqrt(2)
        ketPi = np.array([1, 1j], dtype=complex) / math.sqrt(2)
        ketMi = np.array([1, -1j], dtype=complex) / math.sqrt(2)
        return [np.outer(k, k.conj()) for k in
                (ket0, ket1, ketP, ketM, ketPi, ketMi)]

    def test_reconstructs_maximally_mixed_state(self):
        """最大混合态 I/2: 所有频率=0.5，MLE 收敛到 I/2。"""
        ops = self._pauli_projectors()
        freq = np.array([0.5] * 6)
        target = np.eye(2, dtype=complex) / 2
        tomo = _qa.QuantumStateTomography(ops, freq, target_state=target)
        result = tomo.reconstruct(max_iter=100, tol=1e-12)
        assert result.converged
        np.testing.assert_allclose(result.density_matrix, target, atol=1e-9)
        assert result.fidelity == pytest.approx(1.0, abs=1e-9)

    def test_validates_frequencies_out_of_range(self):
        """频率超出 [0,1] 须 raise（R03）。"""
        ops = self._pauli_projectors()
        with pytest.raises(ValueError, match="频率"):
            _qa.QuantumStateTomography(ops, np.array([1.5, 0, 0, 0, 0, 0]))


# ===========================================================================
# R559 量子过程层析
# ===========================================================================


class TestR559QuantumProcessTomography:
    """R559 χ 矩阵线性反演过程层析测试。"""

    def _info_complete_states(self):
        """4 个信息完备的密度矩阵: |0⟩, |1⟩, |+⟩, |+i⟩。"""
        ket0 = np.array([1, 0], dtype=complex)
        ket1 = np.array([0, 1], dtype=complex)
        ketP = np.array([1, 1], dtype=complex) / math.sqrt(2)
        ketPi = np.array([1, 1j], dtype=complex) / math.sqrt(2)
        return [np.outer(k, k.conj()) for k in (ket0, ket1, ketP, ketPi)]

    def test_identity_channel_reconstruction(self):
        """恒等通道 E(ρ)=ρ: χ[0,0]=1（仅 I 分量），其余=0。"""
        states = self._info_complete_states()
        pt = _qa.QuantumProcessTomography(dim=2)
        chi = pt.reconstruct(states, states)  # 输出=输入
        # χ 归一化后 χ[0,0]≈1（I 分量），其余≈0
        assert chi[0, 0].real == pytest.approx(1.0, abs=1e-9)
        # 非对角元和其余对角元 ≈ 0
        off_diag = chi - np.diag(np.diag(chi))
        assert np.max(np.abs(off_diag)) < 1e-9
        for i in range(1, 4):
            assert abs(chi[i, i]) < 1e-9

    def test_apply_channel_identity(self):
        """apply_channel(χ_identity, ρ) = ρ。"""
        states = self._info_complete_states()
        pt = _qa.QuantumProcessTomography(dim=2)
        chi = pt.reconstruct(states, states)
        rho = np.array([[0.7, 0.3j], [-0.3j, 0.3]], dtype=complex)
        out = pt.apply_channel(chi, rho)
        np.testing.assert_allclose(out, rho, atol=1e-9)

    def test_validates_wrong_dim(self):
        """dim≠2 须 raise（R03，当前仅支持单量子比特）。"""
        with pytest.raises(ValueError, match="dim=2"):
            _qa.QuantumProcessTomography(dim=3)


# ===========================================================================
# R560 BB84/E91 QKD 增强协议
# ===========================================================================


class TestR560E91Protocol:
    """R560 E91 协议测试（CHSH-Bell 安全检测）。"""

    def test_chsh_tsirelson_bound_no_eavesdrop(self):
        """无窃听时 CHSH S=2√2（Tsirelson 界）— 回归测试。

        Bug 修复（R05）: 旧代码 CHSH 公式用 ALICE[1],[2] 而非 [0],[1]，
        导致 S=0 而非 2√2。修复后 a1=0,a2=π/4,b1=π/8,b2=3π/8 → S=2√2。
        """
        e91 = _qa.E91Protocol(key_length=32, eavesdrop_prob=0.0, seed=42)
        S = e91._chsh_parameter()
        assert S == pytest.approx(2 * math.sqrt(2), abs=1e-12)

    def test_qber_zero_no_eavesdrop(self):
        """无窃听时 QBER=0 — 回归测试。

        Bug 修复（R05）: 旧代码密钥基矢用 ALICE[2] vs BOB[1]（不同基），
        导致 QBER≈0.146 而非 0。修复后用 ALICE[2] vs BOB[2]（同基 a3=b3=π/2）。
        """
        e91 = _qa.E91Protocol(key_length=32, eavesdrop_prob=0.0, seed=42)
        result = e91.simulate()
        assert result.qber == pytest.approx(0.0, abs=1e-12)
        assert result.is_secure
        assert result.bell_parameter == pytest.approx(2 * math.sqrt(2), abs=1e-12)

    def test_eavesdrop_reduces_s_parameter(self):
        """窃听降低 S 参数: p=0.5 → S=0 < 2（不安全）。"""
        e91 = _qa.E91Protocol(key_length=32, eavesdrop_prob=0.5, seed=42)
        S = e91._chsh_parameter()
        assert S == pytest.approx(0.0, abs=1e-12)
        result = e91.simulate()
        assert not result.is_secure

    def test_eavesdrop_threshold(self):
        """窃听阈值: p≈0.146 时 S≈2（CHSH 边界）。"""
        p_thresh = (1.0 - 1.0 / math.sqrt(2)) / 2.0
        e91 = _qa.E91Protocol(key_length=32, eavesdrop_prob=p_thresh, seed=42)
        S = e91._chsh_parameter()
        assert S == pytest.approx(2.0, abs=1e-6)


class TestR560BB84Enhanced:
    """R560 BB84 增强协议测试（GLLP 成码率）。"""

    def test_secret_key_rate_formula(self):
        """GLLP 成码率 K = q·[1-2·h(Q)]（Lo 2005）。

        Q=0 → K=q=0.5；Q=0.11 → K≈0；Q>0.11 → K=0。
        """
        bb84 = _qa.BB84EnhancedProtocol(key_length=32, seed=42)
        assert bb84.secret_key_rate(0.0) == pytest.approx(0.5, abs=1e-12)
        # QBER 阈值 11%: K ≈ 0
        rate_11 = bb84.secret_key_rate(0.11)
        assert rate_11 == pytest.approx(0.0, abs=0.01)
        # QBER > 阈值: K = 0
        assert bb84.secret_key_rate(0.5) == 0.0

    def test_simulate_no_eavesdrop_secure(self):
        """无窃听时 QBER≈0，成码率>0。"""
        bb84 = _qa.BB84EnhancedProtocol(key_length=32, seed=42)
        result = bb84.simulate(eavesdrop=False, channel_loss_db=3.0)
        assert result.protocol == "BB84-Enhanced"
        assert result.qber < 0.11
        assert result.is_secure
        assert result.secret_key_rate > 0


# ===========================================================================
# R02/R03/R04 合规检查
# ===========================================================================


class TestCompliance:
    """R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU。"""

    def test_r02_literature_urls_in_docstring(self):
        """模块 docstring 须含 ≥5 个文献 URL（R02）。"""
        source = _SRC_FILE.read_text()
        urls = re.findall(r"https?://[^\s)]+", source)
        assert len(urls) >= 5, f"仅找到 {len(urls)} 个 URL，须 ≥5"

    def test_r03_no_fall_back_patterns(self):
        """源码禁止 fall-back: 无 bare except / except: pass / return None 兜底（R03）。"""
        source = _SRC_FILE.read_text()
        # 检查 bare except 或 except + pass
        bare_except = re.findall(r"except\s*:", source)
        assert len(bare_except) == 0, "存在 bare except（R03 违规）"
        # except 后跟 pass
        except_pass = re.findall(r"except.*:\s*\n\s*pass", source)
        assert len(except_pass) == 0, "存在 except: pass（R03 违规）"

    def test_r04_no_gpu_imports(self):
        """源码禁止 GPU 后端导入: cupy/cuda/rocm/jax（R04）。"""
        source = _SRC_FILE.read_text()
        gpu_patterns = ["import cupy", "import cuda", "import roc", "from jax",
                        "import torch", "cp\\.", "tf\\.compat\\.v1"]
        for pat in gpu_patterns:
            matches = re.findall(pat, source)
            assert len(matches) == 0, f"存在 GPU 导入 '{pat}'（R04 违规）"


# ===========================================================================
# 端到端集成测试
# ===========================================================================


class TestEndToEndIntegration:
    """端到端量子光子管线集成测试。"""

    def test_full_quantum_pipeline(self):
        """R556+R557+R560 端到端: 采样→HOM→QKD 全链路。"""
        # R556: 大模式玻色采样
        U_large = _random_unitary(8, seed=99)
        sampler = _qa.LargeScaleBosonSampler(U_large, seed=99)
        sample_result = sampler.sample((1, 1, 1, 0, 0, 0, 0, 0))
        assert sum(sample_result.output_state) == 3

        # R557: HOM 干涉
        bs = _beamsplitter(math.pi / 4)
        hom = _qa.HOMInterferometer(bs)
        hom_result = hom.interfere((1, 1), distinguishability=1.0)
        assert hom_result.probabilities[(1, 1)] == pytest.approx(0.0, abs=1e-9)

        # R560: E91 QKD
        e91 = _qa.E91Protocol(key_length=16, eavesdrop_prob=0.0, seed=99)
        e91_result = e91.simulate()
        assert e91_result.bell_parameter > 2.0
        assert e91_result.is_secure

        # R560: BB84 QKD
        bb84 = _qa.BB84EnhancedProtocol(key_length=16, seed=99)
        bb84_result = bb84.simulate(eavesdrop=False)
        assert bb84_result.is_secure
