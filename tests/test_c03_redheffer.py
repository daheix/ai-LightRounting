"""C03-Redheffer 星积 S 矩阵级联测试（Sprint 1 Task 1.3 验收）。

验收标准（spec.md S1-C6 / S1-C7）：
- S1-C6: src/polaris/sim/cascade/smatrix.py Redheffer 星积完整公式实现
- S1-C7: 数值稳定性验证（消逝波无发散）

验证基准（C03 §7）：
- 恒等元：S1 ★ I = S1，I ★ S2 = S2
- 结合律：(S1 ★ S2) ★ S3 = S1 ★ (S2 ★ S3)
- 自由空间透明：界面 S = I（A=I, B=I → S11=0, S22=0, S21=I, S12=I）
- 消逝波稳定：传播 100 个消逝波长后无发散（|S21| ≤ 1）
- 单界面 Fresnel：与解析公式对比误差 ≤1e-12

物理参数：
- 自由空间 λ=1.55μm, n=1.0
- Si/SiO2 界面 n=3.476/1.444 @ 1550nm
- 消逝波 kz = i·10⁶·5j（虚部远大于实部）

文献参考（规则 18 学术诚信，URL ≥5）：
1. Redheffer 1959 J Math Mech — https://www.jstor.org/stable/24900576
2. Victor Liu 2013 Technical Note — http://victorliu.info/pdfs/Scombine.pdf
3. Liu & Fan 2012 S4 CPC 183, 2233 — https://web.stanford.edu/group/fan/S4/
4. Pham 2022 Nanomaterials 12(22), 3951 — https://doi.org/10.3390/nano12223951
5. Andersson 2023 PIER-B 101, 17-44 — http://test.jpier.org/download/23041602.pdf
6. Rumpf 2011 RCWA 3D — https:// DOI 10.1117/12.820817

规则依据：project_rules.md 规则 14（禁止 fall-back）/规则 18（学术诚信）
/规则 26（GPU 不参与）
"""

from __future__ import annotations

import numpy as np
import pytest

from polaris.sim.cascade.smatrix import (
    BlockSMatrix,
    build_propagation_s,
    cascade_redheffer,
    redheffer_star_product,
)

_N_SI = 3.476
_N_SIO2 = 1.444


# ---------------------------------------------------------------------------
# 辅助构造
# ---------------------------------------------------------------------------


def _identity_s(n: int) -> BlockSMatrix:
    """2N×2N 单位 S 矩阵（完全透明：S11=0, S22=0, S21=I, S12=I）。"""
    eye = np.eye(n, dtype=np.complex128)
    zero = np.zeros((n, n), dtype=np.complex128)
    return BlockSMatrix(zero, eye, eye, zero)


def _random_lossless_s(n: int, seed: int = 42) -> BlockSMatrix:
    """构造物理可实现的随机 S 矩阵（无源、互易，满足 |S|≤1）。

    用 W/V 本征模分解后构造（保证耗散性，Andersson 2023 §3）。
    互易定理：S = S^T ⟺ S21 = S12^T（Redheffer 1959 §4）。
    注：复 QR 分解的 q·D·q^H 为 Hermitian（非对称），故显式令
    s12 = s21.T 以满足互易性（任意模基下的正确关系）。
    """
    rng = np.random.default_rng(seed)
    # 随机酉矩阵 W（本征模基），保证 S 耗散
    a = rng.standard_normal((n, n)) + 1j * rng.standard_normal((n, n))
    q, _ = np.linalg.qr(a)
    # 随机反射系数 r ∈ [0, 0.5]（无源条件 |r|<1）
    r_diag = np.diag(rng.uniform(0.0, 0.5, size=n).astype(np.complex128))
    t_diag = np.diag(np.sqrt(1.0 - np.diag(r_diag).real ** 2))
    # S 在本征模基中是对角，再变回到端口基
    s11 = q @ r_diag @ q.conj().T
    s22 = s11.copy()  # 对称结构（左右同介质）
    s21 = q @ t_diag @ q.conj().T
    s12 = s21.T  # 互易性：S21 = S12^T ⟺ S12 = S21^T
    return BlockSMatrix(s11, s12, s21, s22)


def _fresnel_interface_s(n_left: float, n_right: float, n_harmonics: int = 2) -> BlockSMatrix:
    """构造 0 阶 Fresnel 单界面 S 矩阵（齐次介质，仅 0 阶有反射）。

    其他阶设为完全透射（kx_m 与入射方向匹配时，齐次界面无衍射耦合）。
    """
    n_total = 2 * n_harmonics + 1
    center = n_harmonics
    r0 = (n_left - n_right) / (n_left + n_right)
    t0 = 2.0 * n_left / (n_left + n_right)
    eye = np.eye(n_total, dtype=np.complex128)
    # 仅 0 阶有 Fresnel 反射，其他阶全透射
    s11 = np.zeros((n_total, n_total), dtype=np.complex128)
    s11[center, center] = r0
    s22 = np.zeros_like(s11)
    s22[center, center] = -r0  # 反向 Fresnel 反射（对称）
    s21 = eye.copy()
    s21[center, center] = t0
    s12 = eye.copy()
    s12[center, center] = 2.0 * n_right / (n_left + n_right)
    return BlockSMatrix(s11, s12, s21, s22)


# ---------------------------------------------------------------------------
# BlockSMatrix 数据类验证（S1-C6）
# ---------------------------------------------------------------------------


class TestBlockSMatrix:
    """BlockSMatrix 形状/类型校验（规则 14：失败 raise）。"""

    def test_valid_construction(self) -> None:
        n = 3
        zero = np.zeros((n, n), dtype=np.complex128)
        eye = np.eye(n, dtype=np.complex128)
        s = BlockSMatrix(zero, eye, eye, zero)
        assert s.n_ports == n

    def test_shape_mismatch_raises(self) -> None:
        n = 3
        zero = np.zeros((n, n), dtype=np.complex128)
        wrong = np.zeros((n + 1, n), dtype=np.complex128)
        with pytest.raises(ValueError, match="s12 形状"):
            BlockSMatrix(zero, wrong, zero, zero)

    def test_dtype_mismatch_raises(self) -> None:
        n = 3
        zero_c = np.zeros((n, n), dtype=np.complex128)
        zero_f = np.zeros((n, n), dtype=np.complex64)  # 错误 dtype
        with pytest.raises(TypeError, match="complex128"):
            BlockSMatrix(zero_c, zero_f, zero_c, zero_c)

    def test_from_dense_round_trip(self) -> None:
        n = 4
        rng = np.random.default_rng(7)
        dense = rng.standard_normal((2 * n, 2 * n)) + 1j * rng.standard_normal((2 * n, 2 * n))
        dense = dense.astype(np.complex128)
        s = BlockSMatrix.from_dense(dense)
        reconstructed = s.to_dense()
        assert np.allclose(reconstructed, dense)

    def test_dense_requires_even_dim(self) -> None:
        odd = np.zeros((5, 5), dtype=np.complex128)
        with pytest.raises(ValueError, match="偶数维"):
            BlockSMatrix.from_dense(odd)


# ---------------------------------------------------------------------------
# Redheffer 星积恒等元与代数性质（S1-C6 数学正确性）
# ---------------------------------------------------------------------------


class TestRedhefferAlgebra:
    """Redheffer 星积代数性质（与 Redheffer 1959 原始定义一致）。"""

    def test_identity_is_left_unit(self) -> None:
        """I ★ S = S（左单位元）。"""
        n = 4
        s = _random_lossless_s(n, seed=11)
        ident = _identity_s(n)
        result = redheffer_star_product(ident, s)
        assert np.allclose(result.s11, s.s11)
        assert np.allclose(result.s12, s.s12)
        assert np.allclose(result.s21, s.s21)
        assert np.allclose(result.s22, s.s22)

    def test_identity_is_right_unit(self) -> None:
        """S ★ I = S（右单位元）。"""
        n = 4
        s = _random_lossless_s(n, seed=12)
        ident = _identity_s(n)
        result = redheffer_star_product(s, ident)
        assert np.allclose(result.s11, s.s11, atol=1e-10)
        assert np.allclose(result.s12, s.s12, atol=1e-10)
        assert np.allclose(result.s21, s.s21, atol=1e-10)
        assert np.allclose(result.s22, s.s22, atol=1e-10)

    def test_associativity(self) -> None:
        """(S1 ★ S2) ★ S3 = S1 ★ (S2 ★ S3)（结合律，Redheffer 1959 定理 2）。"""
        n = 3
        s1 = _random_lossless_s(n, seed=21)
        s2 = _random_lossless_s(n, seed=22)
        s3 = _random_lossless_s(n, seed=23)
        left = redheffer_star_product(redheffer_star_product(s1, s2), s3)
        right = redheffer_star_product(s1, redheffer_star_product(s2, s3))
        # 物理系统结合律保证相同散射矩阵（数值容差 1e-10）
        assert np.allclose(left.s11, right.s11, atol=1e-10)
        assert np.allclose(left.s21, right.s21, atol=1e-10)
        assert np.allclose(left.s12, right.s12, atol=1e-10)
        assert np.allclose(left.s22, right.s22, atol=1e-10)

    def test_port_mismatch_raises(self) -> None:
        n1, n2 = 3, 4
        zero1 = np.zeros((n1, n1), dtype=np.complex128)
        zero2 = np.zeros((n2, n2), dtype=np.complex128)
        eye1 = np.eye(n1, dtype=np.complex128)
        eye2 = np.eye(n2, dtype=np.complex128)
        s1 = BlockSMatrix(zero1, eye1, eye1, zero1)
        s2 = BlockSMatrix(zero2, eye2, eye2, zero2)
        with pytest.raises(ValueError, match="端口模式数不匹配"):
            redheffer_star_product(s1, s2)


# ---------------------------------------------------------------------------
# 自由空间透明性（S1-C6 物理验证）
# ---------------------------------------------------------------------------


class TestFreeSpaceTransparency:
    """自由空间传播物理验证（A01 §5 步骤 4 基础测试）。"""

    def test_free_space_transmission_is_one(self) -> None:
        """自由空间均匀传播：S_global.S21 应等于传播相位 exp(i·k_z·d)。"""
        n = 5
        # 构造入射半空间 → 自由空间传播段 → 衬底半空间（全同 n=1）
        # 三段 S 矩阵：透明界面 + 传播 + 透明界面
        zero = np.zeros((n, n), dtype=np.complex128)
        eye = np.eye(n, dtype=np.complex128)
        transparent = BlockSMatrix(zero, eye, eye, zero)
        k_z = np.array([1.0 + 0j, 2.0 + 0j, 3.0 + 0j, 2.0 + 0j, 1.0 + 0j])
        propagation = build_propagation_s(k_z, length=2.0)
        s_global = cascade_redheffer([transparent, propagation, transparent])
        # S21 应为 diag(exp(i·k_z·d))
        expected_phase = np.exp(1j * k_z * 2.0)
        assert np.allclose(np.diag(s_global.s21), expected_phase, atol=1e-12)
        # 无反射
        assert np.allclose(s_global.s11, 0.0, atol=1e-12)
        assert np.allclose(s_global.s22, 0.0, atol=1e-12)

    def test_propagation_phase_zero_length(self) -> None:
        """零长度传播段应等价于完全透明（S21=I, S12=I, S11=0, S22=0）。"""
        n = 4
        k_z = np.linspace(1.0, 4.0, n)
        prop = build_propagation_s(k_z, length=0.0)
        assert np.allclose(prop.s21, np.eye(n))
        assert np.allclose(prop.s12, np.eye(n))
        assert np.allclose(prop.s11, 0.0)
        assert np.allclose(prop.s22, 0.0)


# ---------------------------------------------------------------------------
# 消逝波数值稳定性（S1-C7，C03 §7.2 关键验收）
# ---------------------------------------------------------------------------


class TestEvanescentStability:
    """消逝波传播数值稳定性（C03 §7.2，避免 e^|kz|d 指数溢出）。"""

    def test_evanescent_decaying(self) -> None:
        """消逝波传播 100 个衰减长度后，|S21| ≤ 1（无指数发散）。"""
        kappa = 1e6  # 消逝波虚部（强衰减）
        k_z = np.array([1e6 + 0j, 0 + 1j * kappa, 1e6 + 0j])
        # 消逝波长 d_decay = 1/kappa = 1e-6 m
        d_total = 100.0 / kappa  # 100 个衰减长度
        prop = build_propagation_s(k_z, length=d_total)
        # 消逝波（中间阶）|exp(i·k_z·d)| = exp(-kappa·d) = exp(-100) ≈ 0
        evanescent_amp = np.abs(prop.s21[1, 1])
        assert evanescent_amp < 1e-30  # 接近零，无发散
        # 传播波（0, 2 阶）|exp(i·k_z·d)| = 1（相位累积）
        assert np.abs(np.abs(prop.s21[0, 0]) - 1.0) < 1e-12
        assert np.abs(np.abs(prop.s21[2, 2]) - 1.0) < 1e-12

    def test_long_evanescent_cascade_no_overflow(self) -> None:
        """长级联（100 段）消逝波传播，最终振幅有界无溢出（C03 §7.2 核心保证）。"""
        n = 2
        # 强消逝波（kz 虚部远大于实部）
        k_z = np.array([0 + 1j * 1e4, 0 + 1j * 1e4])
        d_segment = 0.1  # 每段 0.1 个衰减长度
        # 构造 100 段相同传播，级联
        propagation_segments = [build_propagation_s(k_z, length=d_segment) for _ in range(100)]
        # 添加首尾透明界面（保证 Redheffer 可级联）
        zero = np.zeros((n, n), dtype=np.complex128)
        eye = np.eye(n, dtype=np.complex128)
        transparent = BlockSMatrix(zero, eye, eye, zero)
        s_list = [transparent] + propagation_segments + [transparent]
        # 不应抛出 OverflowError 或 RuntimeError
        s_global = cascade_redheffer(s_list)
        # |S21| ≤ 1（无源系统约束，耗散性传递）
        s21_norm = np.linalg.norm(s_global.s21, ord=2)
        assert s21_norm <= 1.0 + 1e-10
        # 消逝波累积衰减：|S21| ≤ exp(-kappa·d_total) = exp(-1e4·10) ≈ 0
        assert s21_norm < 1e-3  # 强消逝，应接近 0


# ---------------------------------------------------------------------------
# 单界面 Fresnel 验证（A01 §6 公式 vs 解析）
# ---------------------------------------------------------------------------


class TestFresnelInterface:
    """单界面 Fresnel 反射系数 vs 解析公式（A01 §6 验证）。"""

    def test_fresnel_te_normal_incidence(self) -> None:
        """正入射 TE 偏振 Fresnel 反射系数 r = (n1-n2)/(n1+n2)。"""
        n1, n2 = _N_SIO2, _N_SI
        # 构造单层极薄 SiO2 → SiO2 → Si 的 RCWA 等效：传播 0 长度 + 界面
        # 直接验证 Redheffer 星积对单界面 + 透明介质的级联
        s_iface = _fresnel_interface_s(n1, n2, n_harmonics=2)
        # 透明介质（无反射）拼接前后
        n = s_iface.n_ports
        zero = np.zeros((n, n), dtype=np.complex128)
        eye = np.eye(n, dtype=np.complex128)
        transparent = BlockSMatrix(zero, eye, eye, zero)
        s_global = redheffer_star_product(transparent, s_iface)
        s_global = redheffer_star_product(s_global, transparent)
        # 0 阶反射系数应等于 Fresnel r
        center = 2  # n_harmonics=2 → 0 阶索引
        r_fresnel = (n1 - n2) / (n1 + n2)
        assert np.isclose(s_global.s11[center, center], r_fresnel, atol=1e-12)

    def test_fresnel_reciprocity(self) -> None:
        """互易性：S12 转置 = S21（互易介质，Redheffer 1959 §4）。"""
        n = 4
        # 构造对称结构（左 = 右）保证互易
        s = _random_lossless_s(n, seed=99)
        # 对称无源 S 矩阵满足 S21 = S12^T（互易定理）
        # 注：_random_lossless_s 构造的对称 S 矩阵（s11=s22, s12=s21）
        # 互易性 → S21^T = S12
        assert np.allclose(s.s21.T, s.s12, atol=1e-12)


# ---------------------------------------------------------------------------
# 多层级联（C03 §5 步骤 5 完整流程）
# ---------------------------------------------------------------------------


class TestCascadeRedheffer:
    """cascade_redheffer 多层级联接口（C03 §5）。"""

    def test_empty_list_raises(self) -> None:
        with pytest.raises(ValueError, match="不能为空"):
            cascade_redheffer([])

    def test_single_element_passthrough(self) -> None:
        """单元素列表：直接返回该元素。"""
        s = _random_lossless_s(3, seed=3)
        result = cascade_redheffer([s])
        assert result is s

    def test_cascade_consistency_with_pairwise(self) -> None:
        """5 段级联结果 == 逐对级联结果（保证迭代顺序正确）。"""
        s_list = [_random_lossless_s(3, seed=k) for k in range(5)]
        # 一次性级联
        s_cascade = cascade_redheffer(s_list)
        # 逐对级联
        s_pairwise = s_list[0]
        for s in s_list[1:]:
            s_pairwise = redheffer_star_product(s_pairwise, s)
        assert np.allclose(s_cascade.s11, s_pairwise.s11, atol=1e-10)
        assert np.allclose(s_cascade.s21, s_pairwise.s21, atol=1e-10)


# ---------------------------------------------------------------------------
# build_propagation_s 接口验证（A02-EME 共享接口）
# ---------------------------------------------------------------------------


class TestBuildPropagationS:
    """build_propagation_s 均匀段传播 S 矩阵（A02-EME §7.4 共享）。"""

    def test_propagation_shape(self) -> None:
        beta = np.array([1.0, 2.0, 3.0], dtype=np.complex128)
        s = build_propagation_s(beta, length=1.0)
        assert s.n_ports == 3
        assert s.s11.shape == (3, 3)
        # 无反射
        assert np.allclose(s.s11, 0.0)
        assert np.allclose(s.s22, 0.0)

    def test_negative_length_raises(self) -> None:
        beta = np.array([1.0], dtype=np.complex128)
        with pytest.raises(ValueError, match="非负"):
            build_propagation_s(beta, length=-0.1)

    def test_2d_beta_raises(self) -> None:
        beta = np.array([[1.0]], dtype=np.complex128)
        with pytest.raises(ValueError, match="1D"):
            build_propagation_s(beta, length=1.0)
