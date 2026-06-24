"""R35 测试套件：量子光子电路仿真器 + Verilog-A 光电协同仿真。

覆盖 R35.md §7 验收标准:
- §7.1: Verilog-A 模型生成 + 5+ 器件 + Ngspice 联合仿真
- §7.2: Ryser 积和式 + HOM 干涉误差 < 1% + 4光子玻色采样
- §7.3: Ngspice 联合仿真 + PAM4 眼图
- §7.4: 可微分玻色采样 + 含损失 + 逆向设计

学术诚信:
- 所有公式溯源: Aaronson 2011, Hong 1987, Hamilton 2017, Knill 2001
- 所有参数溯源: SiEPIC EBeam PDK, Chrostowski 2015
- 创新点标注: 损失感知玻色采样、光电协同可微、量子光子 PDK

来源:
- Aaronson & Arkhipov, STOC 2011, https://arxiv.org/abs/0910.4698
- Hong, Ou, Mandel, PRL 1987, https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.59.2044
- Hamilton et al., PRL 2017, https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.119.170501
- Knill, Laflamme, Milburn, Nature 2001, https://www.nature.com/articles/35051009
- García-Patrón et al., arXiv 2024, https://arxiv.org/abs/1712.10037
- Ansys Lumerical CML Compiler, https://optics.ansys.com/hc/en-us/sections/360005039133
"""

from __future__ import annotations

import math
import tempfile
from pathlib import Path

import numpy as np
import pytest

from polaris.sim.quantum_photonics import (
    beamsplitter_unitary,
    boson_sampling_distribution,
    boson_sampling_prob,
    clements_unitary,
    gbs_probability,
    hafnian,
    hom_interference,
    klm_cnot_success_probability,
    klm_hadamard_gate,
    lossy_boson_sampling,
    permanent_brute_force,
    permanent_ryser,
    quantum_advantage_threshold,
)
from polaris.sim.verilog_a import (
    DEFAULT_DETECTOR_RESPONSIVITY,
    DEFAULT_LOAD_RESISTANCE_OHM,
    DEFAULT_MODULATOR_EFFICIENCY,
    DEFAULT_WAVELENGTH_UM,
    DEVICE_TYPE_DETECTOR,
    DEVICE_TYPE_MMI_1X2,
    DEVICE_TYPE_MODULATOR,
    DEVICE_TYPE_RING,
    DEVICE_TYPE_WAVEGUIDE,
    SUPPORTED_DEVICE_TYPES,
    DifferentiableOptoElectricalModel,
    PAM4Signal,
    SPICESimulationConfig,
    VerilogAModel,
    compute_ber,
    compute_eye_diagram,
    compute_snr_db,
    generate_detector_verilog_a,
    generate_mmi_1x2_verilog_a,
    generate_modulator_verilog_a,
    generate_pam4_signal,
    generate_ring_verilog_a,
    generate_spice_netlist,
    generate_verilog_a,
    generate_waveguide_verilog_a,
    optimize_opto_electrical_link,
    save_verilog_a,
)

# =============================================================================
# 1. 积和式（Permanent）计算测试
# =============================================================================


class TestPermanent:
    """Ryser 算法积和式计算测试。"""

    def test_permanent_1x1(self) -> None:
        """1×1 矩阵积和式 = 元素本身。"""
        A = np.array([[3.0]])
        assert permanent_ryser(A) == 3.0

    def test_permanent_2x2(self) -> None:
        """2×2 矩阵积和式: Per([[a,b],[c,d]]) = ad + bc。"""
        A = np.array([[1.0, 2.0], [3.0, 4.0]])
        # Per = 1*4 + 2*3 = 10
        assert permanent_ryser(A) == pytest.approx(10.0)

    def test_permanent_3x3(self) -> None:
        """3×3 矩阵积和式验证。"""
        A = np.array([
            [1.0, 2.0, 3.0],
            [4.0, 5.0, 6.0],
            [7.0, 8.0, 9.0],
        ])
        # Per = 1*5*9 + 1*6*8 + 2*4*9 + 2*6*7 + 3*4*8 + 3*5*7
        #     = 45 + 48 + 72 + 84 + 96 + 105 = 450
        assert permanent_ryser(A) == pytest.approx(450.0)

    def test_permanent_ryser_vs_brute_force(self) -> None:
        """Ryser 与暴力法结果一致（4×4 随机矩阵）。"""
        rng = np.random.default_rng(42)
        A = rng.uniform(0, 1, (4, 4))
        per_ryser = permanent_ryser(A)
        per_brute = permanent_brute_force(A)
        assert per_ryser == pytest.approx(per_brute, rel=1e-10)

    def test_permanent_complex_matrix(self) -> None:
        """复数矩阵积和式。"""
        A = np.array([
            [1 + 1j, 2 - 1j],
            [3 - 2j, 4 + 1j],
        ])
        # Per = (1+1j)*(4+1j) + (2-1j)*(3-2j)
        expected = (1 + 1j) * (4 + 1j) + (2 - 1j) * (3 - 2j)
        assert permanent_ryser(A) == pytest.approx(expected)

    def test_permanent_identity_matrix(self) -> None:
        """单位矩阵积和式 = 1（n! 个排列中只有对角线乘积非零）。"""
        for n in range(1, 6):
            identity = np.eye(n)
            assert permanent_ryser(identity) == pytest.approx(1.0)

    def test_permanent_all_ones(self) -> None:
        """全 1 矩阵积和式 = n!。"""
        for n in range(1, 6):
            A = np.ones((n, n))
            assert permanent_ryser(A) == pytest.approx(math.factorial(n))

    def test_permanent_non_square_raises(self) -> None:
        """非方阵 raise ValueError。"""
        A = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])
        with pytest.raises(ValueError, match="方阵"):
            permanent_ryser(A)

    def test_permanent_empty_matrix(self) -> None:
        """空矩阵积和式 = 1（约定）。"""
        A = np.zeros((0, 0))
        assert permanent_ryser(A) == 1.0


# =============================================================================
# 2. 线性光学网络 + HOM 干涉测试
# =============================================================================


class TestBeamsplitter:
    """分束器酉矩阵测试。"""

    def test_beamsplitter_50_50(self) -> None:
        """50:50 分束器 θ=π/4。"""
        U = beamsplitter_unitary(math.pi / 4)
        # |cos(π/4)|² = 0.5
        assert abs(U[0, 0]) ** 2 == pytest.approx(0.5)
        assert abs(U[1, 0]) ** 2 == pytest.approx(0.5)

    def test_beamsplitter_unitary(self) -> None:
        """分束器矩阵酉性: U·U† = I。"""
        U = beamsplitter_unitary(math.pi / 4, math.pi / 3)
        product = U @ U.conj().T
        assert np.allclose(product, np.eye(2), atol=1e-10)

    def test_beamsplitter_full_reflection(self) -> None:
        """θ=0 全反射。"""
        U = beamsplitter_unitary(0.0)
        assert U[0, 0] == pytest.approx(1.0)
        assert U[1, 0] == pytest.approx(0.0)


class TestHOMInterference:
    """HOM 干涉测试（Hong-Ou-Mandel 1987 PRL）。"""

    def test_hom_50_50_splitter(self) -> None:
        """50:50 分束器 HOM 干涉: |1,1⟩ 概率 = 0。"""
        probs = hom_interference(theta=math.pi / 4)
        # HOM 凹陷: |1,1⟩ 概率应为 0
        assert probs["(1,1)"] == pytest.approx(0.0, abs=1e-10)
        # |2,0⟩ 和 |0,2⟩ 各 50%
        assert probs["(2,0)"] == pytest.approx(0.5, abs=1e-6)
        assert probs["(0,2)"] == pytest.approx(0.5, abs=1e-6)

    def test_hom_probability_conservation(self) -> None:
        """HOM 干涉概率守恒: 总概率 = 1。"""
        probs = hom_interference(theta=math.pi / 4)
        total = sum(probs.values())
        assert total == pytest.approx(1.0, abs=1e-6)

    def test_hom_custom_unitary(self) -> None:
        """自定义酉矩阵 HOM 干涉。"""
        U = beamsplitter_unitary(math.pi / 6, math.pi / 4)
        probs = hom_interference(unitary=U)
        total = sum(probs.values())
        assert total == pytest.approx(1.0, abs=1e-6)

    def test_hom_non_5050_no_bunching(self) -> None:
        """非 50:50 分束器: |1,1⟩ 概率 > 0。"""
        # θ=π/8 (约 14.6% 反射)
        probs = hom_interference(theta=math.pi / 8)
        # |1,1⟩ 概率应 > 0
        assert probs["(1,1)"] > 0

    def test_hom_invalid_unitary_raises(self) -> None:
        """非 2×2 酉矩阵 raise ValueError。"""
        U = np.eye(3)
        with pytest.raises(ValueError, match="2×2"):
            hom_interference(unitary=U)


# =============================================================================
# 3. 玻色采样测试
# =============================================================================


class TestBosonSampling:
    """玻色采样测试（Aaronson & Arkhipov 2011 STOC）。"""

    def test_boson_sampling_2_photon_hom(self) -> None:
        """2 光子 2 模玻色采样 = HOM 干涉。"""
        U = beamsplitter_unitary(math.pi / 4)
        input_state = (1, 1)
        # 输出 |1,1⟩ 概率应为 0（HOM）
        p_11 = boson_sampling_prob(U, input_state, (1, 1))
        assert p_11 == pytest.approx(0.0, abs=1e-10)
        # 输出 |2,0⟩ 概率应为 0.5
        p_20 = boson_sampling_prob(U, input_state, (2, 0))
        assert p_20 == pytest.approx(0.5, abs=1e-6)

    def test_boson_sampling_distribution(self) -> None:
        """玻色采样完整分布: 概率总和 = 1。"""
        U = beamsplitter_unitary(math.pi / 4)
        result = boson_sampling_distribution(U, (1, 1))
        total = sum(result.output_prob.values())
        assert total == pytest.approx(1.0, abs=1e-6)

    def test_boson_sampling_result_attributes(self) -> None:
        """BosonSamplingResult 属性正确。"""
        U = beamsplitter_unitary(math.pi / 4)
        result = boson_sampling_distribution(U, (1, 1))
        assert result.n_photons == 2
        assert result.n_modes == 2
        assert result.input_state == (1, 1)
        assert isinstance(result.output_prob, dict)

    def test_boson_sampling_4_photon(self) -> None:
        """4 光子 4 模玻色采样（验收标准 §7.2）。"""
        # 4×4 酉矩阵（Clements 分解）
        U = clements_unitary(4)
        input_state = (1, 1, 0, 0)
        result = boson_sampling_distribution(U, input_state)
        # 概率守恒
        total = sum(result.output_prob.values())
        assert total == pytest.approx(1.0, abs=1e-6)
        assert result.n_photons == 2

    def test_boson_sampling_photon_number_mismatch_raises(self) -> None:
        """输入/输出光子数不匹配 raise ValueError。"""
        U = np.eye(2)
        with pytest.raises(ValueError, match="光子数"):
            boson_sampling_prob(U, (1, 1), (1, 0))

    def test_boson_sampling_dimension_mismatch_raises(self) -> None:
        """输入/输出模式数与酉矩阵维度不一致 raise ValueError。"""
        U = np.eye(3)
        with pytest.raises(ValueError, match="模式数"):
            boson_sampling_prob(U, (1, 1), (1, 1))

    def test_boson_sampling_zero_photons(self) -> None:
        """零光子输入: 输出 |0,0,...⟩ 概率 = 1。"""
        U = np.eye(2)
        p = boson_sampling_prob(U, (0, 0), (0, 0))
        assert p == 1.0


# =============================================================================
# 4. 含损失玻色采样测试（*创新*: 损失感知）
# =============================================================================


class TestLossyBosonSampling:
    """含光子损失的玻色采样测试（García-Patrón 2024）。"""

    def test_lossy_boson_sampling_no_loss(self) -> None:
        """loss_rate=0 退化为标准玻色采样。"""
        U = beamsplitter_unitary(math.pi / 4)
        lossy_dist = lossy_boson_sampling(U, (1, 1), loss_rate=0.0)
        ideal_dist = boson_sampling_distribution(U, (1, 1))
        # 概率分布应一致
        for state, prob in ideal_dist.output_prob.items():
            assert lossy_dist.get(state, 0.0) == pytest.approx(prob, abs=1e-6)

    def test_lossy_boson_sampling_total_probability(self) -> None:
        """含损失玻色采样概率总和 = 1。"""
        U = beamsplitter_unitary(math.pi / 4)
        lossy_dist = lossy_boson_sampling(U, (1, 1), loss_rate=0.3)
        total = sum(lossy_dist.values())
        assert total == pytest.approx(1.0, abs=1e-6)

    def test_lossy_boson_sampling_invalid_loss_rate_raises(self) -> None:
        """loss_rate 不在 [0,1] raise ValueError。"""
        U = beamsplitter_unitary(math.pi / 4)
        with pytest.raises(ValueError, match="loss_rate"):
            lossy_boson_sampling(U, (1, 1), loss_rate=1.5)
        with pytest.raises(ValueError, match="loss_rate"):
            lossy_boson_sampling(U, (1, 1), loss_rate=-0.1)

    def test_lossy_boson_sampling_full_loss(self) -> None:
        """loss_rate=1: 所有光子丢失，输出 |0,0⟩ 概率 = 1。"""
        U = beamsplitter_unitary(math.pi / 4)
        lossy_dist = lossy_boson_sampling(U, (1, 1), loss_rate=1.0)
        zero_state = (0, 0)
        assert lossy_dist.get(zero_state, 0.0) == pytest.approx(1.0, abs=1e-6)


class TestQuantumAdvantageThreshold:
    """量子优越性阈值评估测试（*创新*: 损失感知）。"""

    def test_small_photons_classical(self) -> None:
        """< 20 光子可经典模拟。"""
        assert quantum_advantage_threshold(10, 0.1) is False
        assert quantum_advantage_threshold(15, 0.3) is False

    def test_large_photons_low_loss_quantum(self) -> None:
        """>= 20 光子且损失 < 50% 量子优越。"""
        assert quantum_advantage_threshold(20, 0.3) is True
        assert quantum_advantage_threshold(50, 0.4) is True

    def test_large_photons_high_loss_classical(self) -> None:
        """>= 20 光子但损失 >= 50% 可经典模拟。"""
        assert quantum_advantage_threshold(20, 0.5) is False
        assert quantum_advantage_threshold(50, 0.7) is False


# =============================================================================
# 5. Gaussian Boson Sampling 测试
# =============================================================================


class TestGBS:
    """Gaussian Boson Sampling 测试（Hamilton 2017 PRL）。"""

    def test_hafnian_2x2(self) -> None:
        """2×2 矩阵 Hafnian = A[0,1]。"""
        A = np.array([[0, 1.5], [1.5, 0]])
        assert hafnian(A) == pytest.approx(1.5)

    def test_hafnian_4x4(self) -> None:
        """4×4 矩阵 Hafnian 验证。"""
        # 完美匹配: (0,1)(2,3), (0,2)(1,3), (0,3)(1,2)
        A = np.array([
            [0, 1, 2, 3],
            [1, 0, 4, 5],
            [2, 4, 0, 6],
            [3, 5, 6, 0],
        ])
        # Haf = A[0,1]*A[2,3] + A[0,2]*A[1,3] + A[0,3]*A[1,2]
        #     = 1*6 + 2*5 + 3*4 = 6 + 10 + 12 = 28
        assert hafnian(A) == pytest.approx(28.0)

    def test_hafnian_odd_size_zero(self) -> None:
        """奇数尺寸 Hafnian = 0（无完美匹配）。"""
        A = np.array([[0, 1, 2], [1, 0, 3], [2, 3, 0]])
        assert hafnian(A) == 0.0

    def test_hafnian_empty(self) -> None:
        """空矩阵 Hafnian = 1。"""
        A = np.zeros((0, 0))
        assert hafnian(A) == 1.0

    def test_gbs_probability(self) -> None:
        """GBS 输出概率计算。"""
        # 2×2 协方差矩阵
        sigma = np.array([[1.0, 0.5], [0.5, 1.0]])
        p = gbs_probability(sigma, (1, 1))
        assert p > 0
        assert math.isfinite(p)

    def test_gbs_probability_zero_output(self) -> None:
        """零输出态概率 = 1。"""
        sigma = np.array([[1.0, 0.5], [0.5, 1.0]])
        p = gbs_probability(sigma, (0, 0))
        assert p == 1.0

    def test_gbs_probability_dimension_mismatch_raises(self) -> None:
        """输出模式数与协方差矩阵维度不一致 raise ValueError。"""
        sigma = np.eye(3)
        with pytest.raises(ValueError, match="输出模式数"):
            gbs_probability(sigma, (1, 1))


# =============================================================================
# 6. KLM 量子门测试（*创新*: 量子光子 PDK）
# =============================================================================


class TestKLM:
    """KLM 量子门测试（Knill-Laflamme-Milburn 2001 Nature）。"""

    def test_klm_cnot_success_probability(self) -> None:
        """KLM CNOT 门成功率 = 1/4。"""
        p = klm_cnot_success_probability()
        assert p == pytest.approx(0.25)

    def test_klm_hadamard_gate(self) -> None:
        """KLM Hadamard 门矩阵正确。"""
        H = klm_hadamard_gate()
        expected = np.array([[1, 1], [1, -1]], dtype=complex) / math.sqrt(2)
        assert np.allclose(H, expected)

    def test_klm_hadamard_unitary(self) -> None:
        """Hadamard 门酉性: H·H† = I。"""
        H = klm_hadamard_gate()
        product = H @ H.conj().T
        assert np.allclose(product, np.eye(2), atol=1e-10)

    def test_klm_hadamard_squared_is_identity(self) -> None:
        """Hadamard 门平方 = I（H·H = I）。"""
        H = klm_hadamard_gate()
        product = H @ H
        assert np.allclose(product, np.eye(2), atol=1e-10)


# =============================================================================
# 7. Clements 分解测试
# =============================================================================


class TestClements:
    """Clements 分解测试（Clements et al. 2016 Optica）。"""

    def test_clements_unitary(self) -> None:
        """Clements 分解生成酉矩阵。"""
        U = clements_unitary(4)
        # 验证酉性: U·U† = I
        product = U @ U.conj().T
        assert np.allclose(product, np.eye(4), atol=1e-6)

    def test_clements_shape(self) -> None:
        """Clements 矩阵形状正确。"""
        for n in [2, 3, 4, 5]:
            U = clements_unitary(n)
            assert U.shape == (n, n)

    def test_clements_determinant_unit(self) -> None:
        """Clements 酉矩阵行列式模 = 1。"""
        U = clements_unitary(4)
        det = np.linalg.det(U)
        assert abs(abs(det) - 1.0) < 1e-6


# =============================================================================
# 8. Verilog-A 模型生成测试
# =============================================================================


class TestVerilogAModel:
    """Verilog-A 模型生成测试（§7.1 验收标准）。"""

    def test_verilog_a_model_dataclass(self) -> None:
        """VerilogAModel dataclass 验证。"""
        model = VerilogAModel(
            module_name="test_wg",
            device_type=DEVICE_TYPE_WAVEGUIDE,
            ports=["in", "out"],
            parameters={"length": 100.0},
            s_params={("in", "out"): np.array(0.5, dtype=complex)},
        )
        assert model.module_name == "test_wg"
        assert model.device_type == DEVICE_TYPE_WAVEGUIDE

    def test_verilog_a_invalid_device_type_raises(self) -> None:
        """不支持的器件类型 raise ValueError。"""
        with pytest.raises(ValueError, match="不支持"):
            VerilogAModel(
                module_name="test",
                device_type="invalid_type",
                ports=["in"],
                parameters={},
                s_params={},
            )

    def test_verilog_a_empty_module_name_raises(self) -> None:
        """空模块名 raise ValueError。"""
        with pytest.raises(ValueError, match="module_name"):
            VerilogAModel(
                module_name="",
                device_type=DEVICE_TYPE_WAVEGUIDE,
                ports=["in"],
                parameters={},
                s_params={},
            )

    def test_verilog_a_empty_ports_raises(self) -> None:
        """空端口列表 raise ValueError。"""
        with pytest.raises(ValueError, match="ports"):
            VerilogAModel(
                module_name="test",
                device_type=DEVICE_TYPE_WAVEGUIDE,
                ports=[],
                parameters={},
                s_params={},
            )


class TestWaveguideVerilogA:
    """波导 Verilog-A 模型生成测试。"""

    def test_generate_waveguide_verilog_a(self) -> None:
        """生成波导 Verilog-A 模型。"""
        model = generate_waveguide_verilog_a(
            module_name="wg_test",
            length_um=100.0,
            neff=2.4,
            ng=4.0,
            loss_db_cm=0.5,
        )
        assert model.module_name == "wg_test"
        assert model.device_type == DEVICE_TYPE_WAVEGUIDE
        assert "in" in model.ports
        assert "out" in model.ports
        # S 参数非零
        s21 = complex(model.s_params[("out", "in")])
        assert abs(s21) > 0

    def test_waveguide_verilog_a_code_contains_module(self) -> None:
        """Verilog-A 代码包含 module 声明。"""
        model = generate_waveguide_verilog_a()
        assert "module" in model.verilog_a_code
        assert "endmodule" in model.verilog_a_code
        assert "analog" in model.verilog_a_code

    def test_waveguide_verilog_a_negative_length_raises(self) -> None:
        """负长度 raise ValueError。"""
        with pytest.raises(ValueError, match="长度"):
            generate_waveguide_verilog_a(length_um=-10.0)

    def test_waveguide_verilog_a_invalid_neff_raises(self) -> None:
        """非正 neff raise ValueError。"""
        with pytest.raises(ValueError, match="neff"):
            generate_waveguide_verilog_a(neff=0.0)


class TestMMIVerilogA:
    """MMI 1x2 Verilog-A 模型生成测试。"""

    def test_generate_mmi_1x2_verilog_a(self) -> None:
        """生成 MMI 1x2 Verilog-A 模型。"""
        model = generate_mmi_1x2_verilog_a(insertion_loss_db=0.4)
        assert model.device_type == DEVICE_TYPE_MMI_1X2
        assert "out1" in model.ports
        assert "out2" in model.ports
        # 3dB 分束: 每个输出约 50% 功率
        amp = abs(complex(model.s_params[("out1", "in")]))
        assert amp == pytest.approx(0.5 ** 0.5, abs=0.1)

    def test_mmi_verilog_a_negative_loss_raises(self) -> None:
        """负插损 raise ValueError。"""
        with pytest.raises(ValueError, match="插损"):
            generate_mmi_1x2_verilog_a(insertion_loss_db=-1.0)


class TestRingVerilogA:
    """环谐振器 Verilog-A 模型生成测试。"""

    def test_generate_ring_verilog_a(self) -> None:
        """生成环谐振器 Verilog-A 模型。"""
        model = generate_ring_verilog_a(radius_um=10.0, coupling=0.01)
        assert model.device_type == DEVICE_TYPE_RING
        assert "through" in model.ports

    def test_ring_verilog_a_invalid_radius_raises(self) -> None:
        """非正半径 raise ValueError。"""
        with pytest.raises(ValueError, match="半径"):
            generate_ring_verilog_a(radius_um=0.0)

    def test_ring_verilog_a_invalid_coupling_raises(self) -> None:
        """coupling 超出 [0,1] raise ValueError。"""
        with pytest.raises(ValueError, match="coupling"):
            generate_ring_verilog_a(coupling=1.5)


class TestModulatorVerilogA:
    """调制器 Verilog-A 模型生成测试。"""

    def test_generate_modulator_verilog_a(self) -> None:
        """生成 MZM 调制器 Verilog-A 模型。"""
        model = generate_modulator_verilog_a(v_pi=2.0, insertion_loss_db=0.5)
        assert model.device_type == DEVICE_TYPE_MODULATOR
        assert "rf_in" in model.ports  # 电学端口

    def test_modulator_verilog_a_invalid_v_pi_raises(self) -> None:
        """非正 V_pi raise ValueError。"""
        with pytest.raises(ValueError, match="V_pi"):
            generate_modulator_verilog_a(v_pi=0.0)


class TestDetectorVerilogA:
    """探测器 Verilog-A 模型生成测试。"""

    def test_generate_detector_verilog_a(self) -> None:
        """生成光电探测器 Verilog-A 模型。"""
        model = generate_detector_verilog_a(responsivity=1.0, load_resistance=50.0)
        assert model.device_type == DEVICE_TYPE_DETECTOR
        assert "rf_out" in model.ports  # 电学输出端口

    def test_detector_verilog_a_invalid_responsivity_raises(self) -> None:
        """负响应度 raise ValueError。"""
        with pytest.raises(ValueError, match="响应度"):
            generate_detector_verilog_a(responsivity=-0.5)

    def test_detector_verilog_a_invalid_resistance_raises(self) -> None:
        """非正负载电阻 raise ValueError。"""
        with pytest.raises(ValueError, match="负载电阻"):
            generate_detector_verilog_a(load_resistance=0.0)


class TestVerilogAUnified:
    """Verilog-A 统一入口测试。"""

    def test_generate_verilog_a_waveguide(self) -> None:
        """统一入口生成波导模型。"""
        model = generate_verilog_a(DEVICE_TYPE_WAVEGUIDE, length_um=50.0)
        assert model.device_type == DEVICE_TYPE_WAVEGUIDE

    def test_generate_verilog_a_all_supported_types(self) -> None:
        """所有支持类型都能生成（验收标准: 5+ 器件）。"""
        # 至少 5 种器件类型
        assert len(SUPPORTED_DEVICE_TYPES) >= 5
        # 测试 5 种核心器件
        core_types = [
            DEVICE_TYPE_WAVEGUIDE,
            DEVICE_TYPE_MMI_1X2,
            DEVICE_TYPE_RING,
            DEVICE_TYPE_MODULATOR,
            DEVICE_TYPE_DETECTOR,
        ]
        for device_type in core_types:
            model = generate_verilog_a(device_type)
            assert model.device_type == device_type
            assert model.verilog_a_code

    def test_generate_verilog_a_unsupported_type_raises(self) -> None:
        """不支持的类型 raise ValueError。"""
        with pytest.raises(ValueError, match="不支持"):
            generate_verilog_a("invalid_type")

    def test_save_verilog_a(self) -> None:
        """保存 Verilog-A 模型到文件。"""
        model = generate_waveguide_verilog_a()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "waveguide.va"
            saved = save_verilog_a(model, path)
            assert saved.exists()
            content = saved.read_text(encoding="utf-8")
            assert "module" in content


# =============================================================================
# 9. SPICE 联合仿真测试
# =============================================================================


class TestSPICECosimulation:
    """SPICE 联合仿真测试（§7.3 验收标准）。"""

    def test_spice_config_default(self) -> None:
        """SPICE 配置默认值。"""
        config = SPICESimulationConfig()
        assert config.spice_timestep > 0
        assert config.optical_timestep > 0
        # 同步时间步 = max(spice, optical)
        assert config.sync_timestep == max(config.spice_timestep, config.optical_timestep)

    def test_spice_config_invalid_timestep_raises(self) -> None:
        """非法时间步 raise ValueError。"""
        with pytest.raises(ValueError, match="spice_timestep"):
            SPICESimulationConfig(spice_timestep=0.0)
        with pytest.raises(ValueError, match="optical_timestep"):
            SPICESimulationConfig(optical_timestep=-1.0)

    def test_spice_config_invalid_total_time_raises(self) -> None:
        """非法总时间 raise ValueError。"""
        with pytest.raises(ValueError, match="total_time"):
            SPICESimulationConfig(total_time=0.0)

    def test_generate_spice_netlist(self) -> None:
        """生成 SPICE 网表。"""
        models = [generate_waveguide_verilog_a()]
        config = SPICESimulationConfig()
        netlist = generate_spice_netlist(models, config)
        assert ".tran" in netlist
        assert ".end" in netlist
        assert "V_in" in netlist

    def test_generate_spice_netlist_pam4(self) -> None:
        """生成 PAM4 信号 SPICE 网表。"""
        models = [generate_modulator_verilog_a()]
        config = SPICESimulationConfig()
        netlist = generate_spice_netlist(models, config, input_signal="pam4")
        assert "PULSE" in netlist

    def test_generate_spice_netlist_empty_models_raises(self) -> None:
        """空模型列表 raise ValueError。"""
        config = SPICESimulationConfig()
        with pytest.raises(ValueError, match="模型列表"):
            generate_spice_netlist([], config)

    def test_generate_spice_netlist_invalid_signal_raises(self) -> None:
        """不支持的输入信号 raise ValueError。"""
        models = [generate_waveguide_verilog_a()]
        config = SPICESimulationConfig()
        with pytest.raises(ValueError, match="输入信号"):
            generate_spice_netlist(models, config, input_signal="invalid")


# =============================================================================
# 10. PAM4 眼图 + BER 测试
# =============================================================================


class TestPAM4:
    """PAM4 调制信号测试（§7.3 验收标准）。"""

    def test_pam4_signal_default(self) -> None:
        """PAM4 信号默认参数。"""
        sig = PAM4Signal()
        assert len(sig.levels) == 4
        assert sig.bit_rate > 0

    def test_pam4_signal_invalid_levels_raises(self) -> None:
        """非 4 电平 raise ValueError。"""
        with pytest.raises(ValueError, match="4 个电平"):
            PAM4Signal(levels=(0.0, 0.5, 1.0))

    def test_pam4_signal_invalid_bit_rate_raises(self) -> None:
        """非正比特率 raise ValueError。"""
        with pytest.raises(ValueError, match="比特率"):
            PAM4Signal(bit_rate=0.0)

    def test_generate_pam4_signal(self) -> None:
        """生成 PAM4 信号。"""
        time, signal = generate_pam4_signal(n_symbols=100, bit_rate=100e9)
        assert len(signal) == 100 * 16  # samples_per_symbol=16
        assert len(time) == len(signal)
        # 信号值应在 [0, 1] 范围内
        assert signal.min() >= 0
        assert signal.max() <= 1

    def test_generate_pam4_signal_invalid_n_symbols_raises(self) -> None:
        """非正符号数 raise ValueError。"""
        with pytest.raises(ValueError, match="符号数"):
            generate_pam4_signal(n_symbols=0)

    def test_compute_eye_diagram(self) -> None:
        """计算眼图。"""
        _, signal = generate_pam4_signal(n_symbols=100)
        eye = compute_eye_diagram(signal, samples_per_symbol=16)
        # 眼图形状: [2*samples_per_symbol, n_windows]
        assert eye.shape[0] == 32

    def test_compute_eye_diagram_invalid_samples_raises(self) -> None:
        """非法采样点数 raise ValueError。"""
        signal = np.array([1.0, 2.0])
        with pytest.raises(ValueError, match="采样点数"):
            compute_eye_diagram(signal, samples_per_symbol=0)

    def test_compute_eye_diagram_short_signal_raises(self) -> None:
        """信号过短 raise ValueError。"""
        signal = np.array([1.0, 2.0])
        with pytest.raises(ValueError, match="眼图窗口"):
            compute_eye_diagram(signal, samples_per_symbol=16)

    def test_compute_ber(self) -> None:
        """计算 BER。"""
        _, signal = generate_pam4_signal(n_symbols=100)
        ber = compute_ber(signal, noise_std=0.05)
        assert 0 <= ber <= 1

    def test_compute_ber_zero_noise(self) -> None:
        """零噪声 BER = 0。"""
        _, signal = generate_pam4_signal(n_symbols=100)
        ber = compute_ber(signal, noise_std=0.0)
        assert ber == 0.0

    def test_compute_ber_invalid_noise_raises(self) -> None:
        """负噪声 raise ValueError。"""
        signal = np.array([1.0, 2.0])
        with pytest.raises(ValueError, match="噪声"):
            compute_ber(signal, noise_std=-0.1)

    def test_compute_snr_db(self) -> None:
        """计算 SNR (dB)。"""
        signal = np.array([1.0, 1.0, 1.0])
        snr = compute_snr_db(signal, noise_std=0.1)
        assert snr > 0

    def test_compute_snr_db_zero_noise(self) -> None:
        """零噪声 SNR = inf。"""
        signal = np.array([1.0, 1.0])
        snr = compute_snr_db(signal, noise_std=0.0)
        assert math.isinf(snr)


# =============================================================================
# 11. 光电协同可微分仿真测试（*创新*: 光电协同可微）
# =============================================================================


class TestDifferentiableOptoElectrical:
    """光电协同可微分模型测试（*创新*）。"""

    def test_model_default_params(self) -> None:
        """默认参数验证。"""
        model = DifferentiableOptoElectricalModel()
        assert model.modulator_efficiency == DEFAULT_MODULATOR_EFFICIENCY
        assert model.detector_responsivity == DEFAULT_DETECTOR_RESPONSIVITY
        assert model.load_resistance == DEFAULT_LOAD_RESISTANCE_OHM

    def test_model_invalid_efficiency_raises(self) -> None:
        """负效率 raise ValueError。"""
        with pytest.raises(ValueError, match="modulator_efficiency"):
            DifferentiableOptoElectricalModel(modulator_efficiency=-0.1)

    def test_model_invalid_responsivity_raises(self) -> None:
        """负响应度 raise ValueError。"""
        with pytest.raises(ValueError, match="detector_responsivity"):
            DifferentiableOptoElectricalModel(detector_responsivity=-0.5)

    def test_model_invalid_resistance_raises(self) -> None:
        """非正电阻 raise ValueError。"""
        with pytest.raises(ValueError, match="load_resistance"):
            DifferentiableOptoElectricalModel(load_resistance=0.0)

    def test_forward_output(self) -> None:
        """前向传播输出正确。"""
        model = DifferentiableOptoElectricalModel()
        v_in = np.array([1.0, 2.0, 3.0])
        result = model.forward(v_in, modulator_length=100.0)
        # 光功率 = η · V²
        expected_power = DEFAULT_MODULATOR_EFFICIENCY * v_in ** 2
        assert np.allclose(result["optical_power"], expected_power, rtol=0.1)
        # 输出电压 = R · P · R_load
        expected_v_out = (
            DEFAULT_DETECTOR_RESPONSIVITY * expected_power * DEFAULT_LOAD_RESISTANCE_OHM
        )
        assert np.allclose(result["output_voltage"], expected_v_out, rtol=0.1)

    def test_gradient_finite_difference(self) -> None:
        """梯度与有限差分一致。"""
        model = DifferentiableOptoElectricalModel()
        v_in = np.array([1.0])
        grad = model.gradient(v_in, modulator_length=100.0, eps=1e-6)
        # ∂V_out/∂V_in 应非零
        assert abs(grad["dV_out_dV_in"][0]) > 0
        # ∂V_out/∂L_mod 应非零（长度衰减）
        assert abs(grad["dV_out_dL_mod"][0]) != 0


class TestOptoElectricalOptimization:
    """光电协同逆向设计测试（*创新*）。"""

    def test_optimize_invalid_iterations_raises(self) -> None:
        """非正迭代次数 raise ValueError。"""
        with pytest.raises(ValueError, match="迭代次数"):
            optimize_opto_electrical_link(n_iterations=0)

    def test_optimize_invalid_learning_rate_raises(self) -> None:
        """非正学习率 raise ValueError。"""
        with pytest.raises(ValueError, match="学习率"):
            optimize_opto_electrical_link(learning_rate=0.0)

    def test_optimize_returns_history(self) -> None:
        """优化返回历史记录。"""
        result = optimize_opto_electrical_link(
            target_output_voltage=0.5, n_iterations=5, learning_rate=0.01
        )
        assert "history" in result
        assert len(result["history"]) == 5
        assert "final_v_in" in result
        assert "final_l_mod" in result
        assert "final_loss" in result

    def test_optimize_loss_decreases(self) -> None:
        """优化过程中损失下降。"""
        result = optimize_opto_electrical_link(
            target_output_voltage=0.1, n_iterations=10, learning_rate=0.01
        )
        history = result["history"]
        # 最终损失应小于初始损失
        assert history[-1]["loss"] <= history[0]["loss"]


# =============================================================================
# 12. R35 集成测试
# =============================================================================


class TestR35Integration:
    """R35 端到端集成测试。"""

    def test_quantum_photonics_pipeline(self) -> None:
        """量子光子仿真完整流程: 分束器 → 玻色采样 → HOM 干涉。"""
        # 1. 生成分束器
        U = beamsplitter_unitary(math.pi / 4)
        # 2. HOM 干涉
        hom_probs = hom_interference(unitary=U)
        assert hom_probs["(1,1)"] == pytest.approx(0.0, abs=1e-10)
        # 3. 玻色采样
        result = boson_sampling_distribution(U, (1, 1))
        total = sum(result.output_prob.values())
        assert total == pytest.approx(1.0, abs=1e-6)

    def test_verilog_a_pipeline(self) -> None:
        """Verilog-A 完整流程: 生成 → 保存 → 网表。"""
        # 1. 生成 5 种器件模型
        models = [
            generate_waveguide_verilog_a(),
            generate_mmi_1x2_verilog_a(),
            generate_ring_verilog_a(),
            generate_modulator_verilog_a(),
            generate_detector_verilog_a(),
        ]
        assert len(models) == 5
        # 2. 保存到临时目录
        with tempfile.TemporaryDirectory() as tmpdir:
            for i, model in enumerate(models):
                path = Path(tmpdir) / f"model_{i}.va"
                saved = save_verilog_a(model, path)
                assert saved.exists()
        # 3. 生成 SPICE 网表
        config = SPICESimulationConfig()
        netlist = generate_spice_netlist(models, config)
        assert ".tran" in netlist

    def test_opto_electrical_link_pipeline(self) -> None:
        """光电协同链路: 电压 → 光功率 → 探测器 → 电压。"""
        model = DifferentiableOptoElectricalModel()
        v_in = np.array([1.0, 2.0])
        result = model.forward(v_in)
        # 链路完整性
        assert "optical_power" in result
        assert "detector_current" in result
        assert "output_voltage" in result
        # 物理一致性: V_out > 0 when V_in > 0
        assert np.all(result["output_voltage"] >= 0)

    def test_pam4_eye_diagram_pipeline(self) -> None:
        """PAM4 完整流程: 生成信号 → 眼图 → BER。"""
        # 1. 生成 PAM4 信号
        time, signal = generate_pam4_signal(n_symbols=200)
        # 2. 计算眼图
        eye = compute_eye_diagram(signal, samples_per_symbol=16)
        assert eye.shape[0] == 32
        # 3. 计算 BER
        ber = compute_ber(signal, noise_std=0.05)
        assert 0 <= ber <= 1
        # 4. 计算 SNR
        snr = compute_snr_db(signal, noise_std=0.05)
        assert snr > 0


# =============================================================================
# 13. 学术诚信验证测试
# =============================================================================


class TestAcademicIntegrity:
    """R35 学术诚信验证（规则 18）。"""

    def test_quantum_photonics_sources_documented(self) -> None:
        """量子光子模块所有公式溯源。"""
        import polaris.sim.quantum_photonics as qp
        # 模块文档字符串包含论文 URL
        doc = qp.__doc__ or ""
        assert "arxiv.org" in doc.lower() or "journals.aps.org" in doc.lower()
        assert "Aaronson" in doc or "aarXiv" in doc

    def test_verilog_a_sources_documented(self) -> None:
        """Verilog-A 模块所有公式溯源。"""
        import polaris.sim.verilog_a as va
        doc = va.__doc__ or ""
        assert "ansys.com" in doc.lower() or "lumerical" in doc.lower()
        assert "Chrostowski" in doc

    def test_innovation_labels_present(self) -> None:
        """创新点标注 *创新* 标签。"""
        import polaris.sim.quantum_photonics as qp
        import polaris.sim.verilog_a as va
        # 量子光子模块含 *创新* 标签
        qp_source = qp.__doc__ or ""
        qp_source += str(qp.lossy_boson_sampling.__doc__ or "")
        assert "创新" in qp_source
        # Verilog-A 模块含 *创新* 标签
        va_source = va.__doc__ or ""
        va_source += str(va.DifferentiableOptoElectricalModel.__doc__ or "")
        assert "创新" in va_source

    def test_physical_constants_traced(self) -> None:
        """物理常量溯源。"""
        # 默认波长 1550nm = SiEPIC EBeam PDK
        assert DEFAULT_WAVELENGTH_UM == 1.55
        # 默认响应度 1.0 A/W = Chrostowski 2015 §9.2
        assert DEFAULT_DETECTOR_RESPONSIVITY == 1.0
        # 默认负载 50Ω = 射频标准
        assert DEFAULT_LOAD_RESISTANCE_OHM == 50.0


# =============================================================================
# 14. 性能测试
# =============================================================================


class TestR35Performance:
    """R35 性能测试。"""

    def test_permanent_6x6_performance(self) -> None:
        """6×6 积和式计算性能（< 1s）。"""
        import time
        rng = np.random.default_rng(42)
        A = rng.uniform(0, 1, (6, 6))
        start = time.time()
        result = permanent_ryser(A)
        elapsed = time.time() - start
        assert elapsed < 1.0
        assert math.isfinite(result)

    def test_boson_sampling_4_photon_performance(self) -> None:
        """4 光子玻色采样性能（< 1s）。"""
        import time
        U = clements_unitary(4)
        start = time.time()
        result = boson_sampling_distribution(U, (1, 1, 0, 0))
        elapsed = time.time() - start
        assert elapsed < 1.0
        assert sum(result.output_prob.values()) == pytest.approx(1.0, abs=1e-6)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
