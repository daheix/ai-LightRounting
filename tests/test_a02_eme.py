"""A02-EME 本征模展开验收测试（Sprint 1 Task 1.4 验收）。

验收标准（spec.md S1-C8 / A02-EME §11.2 M1-M3）：
- M1: FDE 内核对接 — 同模式集 modes_a == modes_b → M_E = M_H = I，
      界面 S11 = 0, S21 = I（正交归一性，偏差 < 1e-10）
- M2: 界面 S 矩阵 — Fresnel 单界面 n1→n2 反射/透射功率守恒 ≤1e-6
- M3: Redheffer 星积级联 — N cell 级联数值稳定，无指数溢出

验证基准（A02 §7 公式）：
- 重叠积分矩阵 M_E ≠ M_H（双向，einsum 向量化）
- 界面 S 矩阵：S11 = (M_E - M_H)·inv(M_E + M_H), S21 = 2·inv(M_E + M_H),
  S12 = S21^T（互易性）, S22 = -S11（对称结构）
- 传播 S 矩阵：P = diag(exp(i·β·L)), 消逝波 Im(β)>0 → |P|<1（C03 §7.2 稳定性）
- 级联顺序：S_global = I(0,1) ★ P(1) ★ I(1,2) ★ P(2) ★ ... ★ I(N-2,N-1) ★ P(N-1)

物理参数：
- 自由空间 λ=1.55μm
- SiO2/Si 界面 n=1.444/3.476 @ 1550nm
- 功率归一化平面波（TE，E 沿 x，传播沿 +z）

文献来源（规则 18 学术诚信，URL ≥5）：
1. Gallagher & Felici 2003 SPIE 4987, 69-82 —
   https://doi.org/10.1117/12.478061
2. Ansys Lumerical MODE-EME solver introduction —
   https://optics.ansys.com/hc/en-us/articles/360034396614
3. SimWorks Eigenmode Expansion (EME) Solver —
   https://www.emsimworks.com/en/solver/EME
4. EMEpy — Open-source eigenmode expansion solver in Python —
   https://emepy.readthedocs.io/en/stable/index.html
5. Liu & Fan 2012 S4 CPC 183, 2233 —
   https://web.stanford.edu/group/fan/S4/
6. Photon Design FIMMPROP EME paper —
   https://photond.com/assets/files/FIMMWAVE/PW03_eme_paper.pdf
7. Oktay & Magden 2024 arXiv:2407.09847 —
   https://arxiv.org/abs/2407.09847

规则依据：project_rules.md 规则 14（禁止 fall-back）/规则 18（学术诚信）
/规则 26（GPU 不参与，纯 NumPy）
"""

from __future__ import annotations

import numpy as np
import pytest

from polaris.sim.cascade.smatrix import BlockSMatrix, cascade_redheffer
from polaris.sim.eme import (
    EmeCell,
    EmeConfig,
    EmeResult,
    EmeSolver,
    build_interface_smatrix,
    build_propagation_smatrix,
    overlap_matrix,
    solve_eme,
)
from polaris.sim.fde import Mode

_ETA0 = 376.730313668  # 真空波阻抗（Ω）
_WAVELENGTH = 1.55e-6  # 1550nm
_N_SIO2 = 1.444
_N_SI = 3.476


# ---------------------------------------------------------------------------
# 辅助构造：功率归一化模式
# ---------------------------------------------------------------------------


def _make_plane_wave_mode(
    n: float,
    wavelength: float = _WAVELENGTH,
    dx: float = 1e-8,
    dy: float = 1e-8,
    nx: int = 4,
    ny: int = 4,
) -> Mode:
    """构造功率归一化平面波 Mode（TE，E 沿 x，传播沿 +z）。

    功率归一化：0.5·Re(E×H*)·A = 1W，A = nx·ny·dx·dy。
    平面波在 xy 均匀：ex = E0·ones, hy = E0·n/η0。
    E0 = sqrt(2·η0/(n·A)) 使 0.5·|E0|²·n/η0·A = 1。
    """
    area = nx * ny * dx * dy
    e0 = np.sqrt(2.0 * _ETA0 / (n * area))
    k0 = 2.0 * np.pi / wavelength
    ex = e0 * np.ones((nx, ny), dtype=np.complex128)
    ey = np.zeros((nx, ny), dtype=np.complex128)
    ez = np.zeros((nx, ny), dtype=np.complex128)
    hy = e0 * n / _ETA0 * np.ones((nx, ny), dtype=np.complex128)
    hx = np.zeros((nx, ny), dtype=np.complex128)
    hz = np.zeros((nx, ny), dtype=np.complex128)
    beta = k0 * n
    return Mode(
        ex=ex,
        ey=ey,
        ez=ez,
        hx=hx,
        hy=hy,
        hz=hz,
        beta=beta,
        n_eff=n,
        te_fraction=1.0,
        tm_fraction=0.0,
        loss_db_cm=0.0,
        wavelength=wavelength,
        normalized=True,
    )


def _make_orthogonal_modes(
    n_modes: int,
    n: float,
    wavelength: float = _WAVELENGTH,
    dx: float = 1e-8,
    dy: float = 1e-8,
    nx: int = 8,
    ny: int = 8,
) -> list[Mode]:
    """构造 n_modes 个互相正交且功率归一化的模式集。

    使用空间正弦函数构造正交模式：
        mode m: ex_m(x,y) = sin(m·π·x/Lx)，m = 1, 2, ..., n_modes
    不同 m 的正弦函数在 [0, Lx] 上正交（∫sin(mπx/Lx)·sin(m'πx/Lx)dx = 0, m≠m'）。
    每个模式按 1W 功率归一化（0.5·Re(E×H*)·A = 1）。

    TE 平面波近似：hy = ex·n/η0（保证功率积分正比于 |ex|²）。
    """
    k0 = 2.0 * np.pi / wavelength
    lx = nx * dx
    x = np.arange(nx) * dx
    y = np.arange(ny) * dy
    x_grid, _ = np.meshgrid(x, y, indexing="ij")
    modes: list[Mode] = []
    for m in range(1, n_modes + 1):
        pattern = np.sin(m * np.pi * x_grid / lx)
        # 归一化 pattern 使 ∫|pattern|²·dx·dy = 1
        pattern_norm = np.sqrt(np.sum(np.abs(pattern) ** 2) * dx * dy)
        pattern_unit = pattern / pattern_norm
        # 功率归一化：0.5·|E0·pattern|²·n/η0·∫|pattern|²·dA = 1
        # 已 ∫|pattern_unit|²·dA = 1，故 E0 = sqrt(2·η0/n)
        e0 = np.sqrt(2.0 * _ETA0 / n)
        ex = e0 * pattern_unit.astype(np.complex128)
        ey = np.zeros_like(ex)
        ez = np.zeros_like(ex)
        hy = ex * n / _ETA0
        hx = np.zeros_like(ex)
        hz = np.zeros_like(ex)
        beta = k0 * n
        modes.append(
            Mode(
                ex=ex,
                ey=ey,
                ez=ez,
                hx=hx,
                hy=hy,
                hz=hz,
                beta=beta,
                n_eff=n,
                te_fraction=1.0,
                tm_fraction=0.0,
                loss_db_cm=0.0,
                wavelength=wavelength,
                normalized=True,
            )
        )
    return modes


def _fresnel_r(n1: float, n2: float) -> float:
    """Fresnel 反射系数（正入射，功率归一化）。"""
    return (n1 - n2) / (n1 + n2)


def _fresnel_t(n1: float, n2: float) -> float:
    """Fresnel 透射系数（正入射，功率归一化，含 sqrt(n1·n2) 因子）。"""
    return 2.0 * np.sqrt(n1 * n2) / (n1 + n2)


# ---------------------------------------------------------------------------
# overlap_matrix 重叠积分矩阵（A02 §7.2）
# ---------------------------------------------------------------------------


class TestOverlapMatrix:
    """重叠积分矩阵 M_E / M_H 双向计算（A02 §7.2）。"""

    def test_orthonormal_same_modeset_identity(self) -> None:
        """同模式集 modes_a == modes_b → M_E = M_H = I（正交归一性，M1 验收点）。"""
        modes = _make_orthogonal_modes(n_modes=3, n=1.5)
        dx, dy = 1e-8, 1e-8
        m_e, m_h = overlap_matrix(modes, modes, dx, dy)
        eye3 = np.eye(3, dtype=np.complex128)
        assert np.allclose(m_e, eye3, atol=1e-10), f"M_E 偏离单位矩阵: {m_e}"
        assert np.allclose(m_h, eye3, atol=1e-10), f"M_H 偏离单位矩阵: {m_h}"

    def test_me_ne_mh_different_media(self) -> None:
        """不同介质模式集 → M_E ≠ M_H（双向重叠积分不对称）。"""
        modes_a = [_make_plane_wave_mode(n=2.0)]
        modes_b = [_make_plane_wave_mode(n=3.0)]
        dx, dy = 1e-8, 1e-8
        m_e, m_h = overlap_matrix(modes_a, modes_b, dx, dy)
        # M_E = sqrt(n1/n2), M_H = sqrt(n2/n1)（Fresnel 验证推导）
        expected_me = np.sqrt(2.0 / 3.0)
        expected_mh = np.sqrt(3.0 / 2.0)
        assert np.isclose(m_e[0, 0], expected_me, atol=1e-10)
        assert np.isclose(m_h[0, 0], expected_mh, atol=1e-10)
        assert not np.allclose(m_e, m_h)

    def test_shape_matches_mode_count(self) -> None:
        """M_E/M_H 形状为 (M_A, M_B)。"""
        modes_a = _make_orthogonal_modes(n_modes=2, n=1.5)
        modes_b = _make_orthogonal_modes(n_modes=3, n=1.5)
        dx, dy = 1e-8, 1e-8
        m_e, m_h = overlap_matrix(modes_a, modes_b, dx, dy)
        assert m_e.shape == (2, 3)
        assert m_h.shape == (2, 3)

    def test_off_diagonal_orthogonal_zero(self) -> None:
        """同模式集非对角元 = 0（模式正交性）。"""
        modes = _make_orthogonal_modes(n_modes=4, n=1.5)
        dx, dy = 1e-8, 1e-8
        m_e, _ = overlap_matrix(modes, modes, dx, dy)
        off_diag = m_e - np.diag(np.diag(m_e))
        assert np.allclose(off_diag, 0.0, atol=1e-10)

    def test_empty_modeset_raises(self) -> None:
        """空模式列表 raise（规则 14）。"""
        modes = _make_orthogonal_modes(n_modes=2, n=1.5)
        dx, dy = 1e-8, 1e-8
        with pytest.raises(ValueError, match="模式列表不能为空"):
            overlap_matrix([], modes, dx, dy)
        with pytest.raises(ValueError, match="模式列表不能为空"):
            overlap_matrix(modes, [], dx, dy)

    def test_nonpositive_grid_raises(self) -> None:
        """网格间距非正 raise（规则 14）。"""
        modes = _make_orthogonal_modes(n_modes=2, n=1.5)
        with pytest.raises(ValueError, match="网格间距必须为正"):
            overlap_matrix(modes, modes, 0.0, 1e-8)
        with pytest.raises(ValueError, match="网格间距必须为正"):
            overlap_matrix(modes, modes, 1e-8, -1.0)

    def test_shape_mismatch_raises(self) -> None:
        """两侧网格形状不一致 raise（规则 14）。"""
        modes_a = _make_orthogonal_modes(n_modes=2, n=1.5, nx=8, ny=8)
        modes_b = _make_orthogonal_modes(n_modes=2, n=1.5, nx=4, ny=8)
        with pytest.raises(ValueError, match="网格形状不一致"):
            overlap_matrix(modes_a, modes_b, 1e-8, 1e-8)


# ---------------------------------------------------------------------------
# build_interface_smatrix 界面 S 矩阵（A02 §7.3，M1/M2 验收）
# ---------------------------------------------------------------------------


class TestBuildInterfaceSmatrix:
    """界面 S 矩阵构造（A02 §7.3，切向场连续 + 正交投影）。"""

    def test_same_modeset_transparent(self) -> None:
        """同模式集 → S11 = 0, S21 = I（M1 验收点，正交归一透明界面）。"""
        modes = _make_orthogonal_modes(n_modes=3, n=1.5)
        dx, dy = 1e-8, 1e-8
        s = build_interface_smatrix(modes, modes, dx, dy)
        eye3 = np.eye(3, dtype=np.complex128)
        assert np.allclose(s.s11, 0.0, atol=1e-10), f"S11 应为 0: {s.s11}"
        assert np.allclose(s.s21, eye3, atol=1e-10), f"S21 应为 I: {s.s21}"
        assert np.allclose(s.s22, 0.0, atol=1e-10)

    def test_fresnel_reflection_single_interface(self) -> None:
        """单界面 Fresnel 反射 r = (n1-n2)/(n1+n2)（M2 验收点）。"""
        n1, n2 = _N_SIO2, _N_SI
        modes_a = [_make_plane_wave_mode(n=n1)]
        modes_b = [_make_plane_wave_mode(n=n2)]
        dx, dy = 1e-8, 1e-8
        s = build_interface_smatrix(modes_a, modes_b, dx, dy)
        r_expected = _fresnel_r(n1, n2)
        assert np.isclose(s.s11[0, 0], r_expected, atol=1e-10), (
            f"S11={s.s11[0, 0]} vs Fresnel r={r_expected}"
        )

    def test_fresnel_transmission_single_interface(self) -> None:
        """单界面 Fresnel 透射 t = 2·sqrt(n1·n2)/(n1+n2)（功率归一化，M2）。"""
        n1, n2 = 2.0, 3.0
        modes_a = [_make_plane_wave_mode(n=n1)]
        modes_b = [_make_plane_wave_mode(n=n2)]
        dx, dy = 1e-8, 1e-8
        s = build_interface_smatrix(modes_a, modes_b, dx, dy)
        t_expected = _fresnel_t(n1, n2)
        assert np.isclose(s.s21[0, 0], t_expected, atol=1e-10), (
            f"S21={s.s21[0, 0]} vs Fresnel t={t_expected}"
        )

    def test_fresnel_power_conservation(self) -> None:
        """Fresnel 单界面功率守恒 |r|² + |t|² = 1（M2 验收点，≤1e-6）。"""
        n1, n2 = _N_SIO2, _N_SI
        modes_a = [_make_plane_wave_mode(n=n1)]
        modes_b = [_make_plane_wave_mode(n=n2)]
        dx, dy = 1e-8, 1e-8
        s = build_interface_smatrix(modes_a, modes_b, dx, dy)
        r = s.s11[0, 0]
        t = s.s21[0, 0]
        power_sum = abs(r) ** 2 + abs(t) ** 2
        assert np.isclose(power_sum, 1.0, atol=1e-10), f"功率守恒偏差: {power_sum} vs 1.0"

    def test_reciprocity_s12_transpose_s21(self) -> None:
        """互易性 S12 = S21^T（洛伦兹互易定理，A02 §7.2）。"""
        modes_a = _make_orthogonal_modes(n_modes=3, n=2.0)
        modes_b = _make_orthogonal_modes(n_modes=3, n=3.0)
        dx, dy = 1e-8, 1e-8
        s = build_interface_smatrix(modes_a, modes_b, dx, dy)
        assert np.allclose(s.s12, s.s21.T, atol=1e-12), (
            f"S12 != S21^T: S12={s.s12}, S21^T={s.s21.T}"
        )

    def test_symmetric_structure_s22_negative_s11(self) -> None:
        """对称结构 S22 = -S11（A02 §7.3 对称假设）。"""
        modes_a = _make_orthogonal_modes(n_modes=2, n=2.0)
        modes_b = _make_orthogonal_modes(n_modes=2, n=3.0)
        dx, dy = 1e-8, 1e-8
        s = build_interface_smatrix(modes_a, modes_b, dx, dy)
        assert np.allclose(s.s22, -s.s11, atol=1e-12)

    def test_mode_count_mismatch_raises(self) -> None:
        """两侧模式数不匹配 raise（规则 14）。"""
        modes_a = _make_orthogonal_modes(n_modes=2, n=1.5)
        modes_b = _make_orthogonal_modes(n_modes=3, n=1.5)
        dx, dy = 1e-8, 1e-8
        with pytest.raises(ValueError, match="模式数不匹配"):
            build_interface_smatrix(modes_a, modes_b, dx, dy)

    def test_returns_blocksmatrix(self) -> None:
        """返回 BlockSMatrix 类型（与 C03 级联接口兼容）。"""
        modes = _make_orthogonal_modes(n_modes=2, n=1.5)
        dx, dy = 1e-8, 1e-8
        s = build_interface_smatrix(modes, modes, dx, dy)
        assert isinstance(s, BlockSMatrix)
        assert s.n_ports == 2


# ---------------------------------------------------------------------------
# build_propagation_smatrix 传播 S 矩阵（A02 §7.4）
# ---------------------------------------------------------------------------


class TestBuildPropagationSmatrix:
    """传播 S 矩阵构造（A02 §7.4，均匀段相位累积）。"""

    def test_phase_accumulation(self) -> None:
        """P = diag(exp(i·β·L))，传播相位累积正确。"""
        betas = np.array([1.0 + 0j, 2.0 + 0j, 3.0 + 0j])
        length = 0.5
        s = build_propagation_smatrix(betas, length)
        expected_phase = np.exp(1j * betas * length)
        assert np.allclose(np.diag(s.s21), expected_phase)
        assert np.allclose(np.diag(s.s12), expected_phase)

    def test_zero_length_transparent(self) -> None:
        """零长度 → S21 = I, S11 = 0（完全透明）。"""
        betas = np.array([1.0 + 0j, 2.0 + 0j])
        s = build_propagation_smatrix(betas, 0.0)
        eye2 = np.eye(2, dtype=np.complex128)
        assert np.allclose(s.s21, eye2)
        assert np.allclose(s.s12, eye2)
        assert np.allclose(s.s11, 0.0)
        assert np.allclose(s.s22, 0.0)

    def test_evanescent_decay(self) -> None:
        """消逝波 Im(β) > 0 → |P| = exp(-Im(β)·L) < 1（C03 §7.2 稳定性）。"""
        beta_evanescent = 0 + 1j * 1e6
        betas = np.array([beta_evanescent])
        length = 1e-5  # 10 个衰减长度
        s = build_propagation_smatrix(betas, length)
        amp = np.abs(s.s21[0, 0])
        expected_amp = np.exp(-1e6 * 1e-5)  # exp(-10) ≈ 4.5e-5
        assert np.isclose(amp, expected_amp, atol=1e-12)
        assert amp < 1e-3  # 强衰减

    def test_negative_length_raises(self) -> None:
        """负长度 raise（规则 14）。"""
        betas = np.array([1.0 + 0j])
        with pytest.raises(ValueError, match="长度必须非负"):
            build_propagation_smatrix(betas, -1.0)

    def test_empty_betas_raises(self) -> None:
        """空 beta 向量 raise（规则 14）。"""
        with pytest.raises(ValueError, match="beta 向量不能为空"):
            build_propagation_smatrix(np.array([], dtype=np.complex128), 1.0)

    def test_multidim_betas_raises(self) -> None:
        """非 1D beta 向量 raise（规则 14）。"""
        betas_2d = np.ones((2, 2), dtype=np.complex128)
        with pytest.raises(ValueError, match="beta 必须为 1D"):
            build_propagation_smatrix(betas_2d, 1.0)


# ---------------------------------------------------------------------------
# EmeCell 数据类（A02 §4）
# ---------------------------------------------------------------------------


class TestEmeCell:
    """EmeCell 数据类校验（A02 §4）。"""

    def test_valid_construction(self) -> None:
        """有效 EmeCell 构造。"""
        modes = _make_orthogonal_modes(n_modes=2, n=1.5)
        cell = EmeCell(length=1e-6, modes=modes)
        assert cell.length == 1e-6
        assert len(cell.modes) == 2

    def test_negative_length_raises(self) -> None:
        """负长度 raise（规则 14）。"""
        modes = _make_orthogonal_modes(n_modes=2, n=1.5)
        with pytest.raises(ValueError, match="cell 长度必须非负"):
            EmeCell(length=-1.0, modes=modes)

    def test_zero_length_allowed(self) -> None:
        """零长度允许（输入参考 cell，不参与传播）。"""
        modes = _make_orthogonal_modes(n_modes=2, n=1.5)
        cell = EmeCell(length=0.0, modes=modes)
        assert cell.length == 0.0

    def test_empty_modes_raises(self) -> None:
        """空模式列表 raise（规则 14）。"""
        with pytest.raises(ValueError, match="模式列表不能为空"):
            EmeCell(length=1e-6, modes=[])


# ---------------------------------------------------------------------------
# EmeConfig 配置类（A02 §6，规则 4 参数集合）
# ---------------------------------------------------------------------------


class TestEmeConfig:
    """EmeConfig 参数校验（规则 4：降低函数参数个数）。"""

    def test_valid_config(self) -> None:
        """有效配置构造。"""
        cfg = EmeConfig(wavelength=1.55e-6, dx=1e-8, dy=1e-8, n_modes=4)
        assert cfg.wavelength == 1.55e-6
        assert cfg.n_modes == 4

    def test_nonpositive_wavelength_raises(self) -> None:
        """非正波长 raise（规则 14）。"""
        with pytest.raises(ValueError, match="波长必须为正"):
            EmeConfig(wavelength=0.0, dx=1e-8, dy=1e-8)

    def test_nonpositive_grid_raises(self) -> None:
        """非正网格间距 raise（规则 14）。"""
        with pytest.raises(ValueError, match="网格间距必须为正"):
            EmeConfig(wavelength=1.55e-6, dx=0.0, dy=1e-8)

    def test_zero_modes_allowed(self) -> None:
        """n_modes=None 跳过模式数校验（允许各 cell 模式数不同）。"""
        cfg = EmeConfig(wavelength=1.55e-6, dx=1e-8, dy=1e-8, n_modes=None)
        assert cfg.n_modes is None

    def test_invalid_n_modes_raises(self) -> None:
        """n_modes < 1 raise（规则 14）。"""
        with pytest.raises(ValueError, match="模式数必须"):
            EmeConfig(wavelength=1.55e-6, dx=1e-8, dy=1e-8, n_modes=0)


# ---------------------------------------------------------------------------
# EmeSolver / solve_eme 求解器（A02 §6，M3 级联验收）
# ---------------------------------------------------------------------------


class TestEmeSolver:
    """EME 求解器级联（A02 §6，Redheffer 星积 S 矩阵级联）。"""

    def test_empty_cells_raises(self) -> None:
        """空 cell 列表 raise（规则 14）。"""
        cfg = EmeConfig(wavelength=1.55e-6, dx=1e-8, dy=1e-8)
        with pytest.raises(ValueError, match="cell 列表不能为空"):
            EmeSolver(cells=[], config=cfg)

    def test_mode_count_mismatch_raises(self) -> None:
        """cell 模式数与配置不一致 raise（规则 14）。"""
        cfg = EmeConfig(wavelength=1.55e-6, dx=1e-8, dy=1e-8, n_modes=3)
        modes2 = _make_orthogonal_modes(n_modes=2, n=1.5)
        cell0 = EmeCell(length=1e-6, modes=modes2)
        with pytest.raises(ValueError, match="模式数"):
            EmeSolver(cells=[cell0], config=cfg)

    def test_grid_shape_mismatch_raises(self) -> None:
        """cell 间网格形状不一致 raise（规则 14）。"""
        cfg = EmeConfig(wavelength=1.55e-6, dx=1e-8, dy=1e-8)
        modes_a = _make_orthogonal_modes(n_modes=2, n=1.5, nx=8, ny=8)
        modes_b = _make_orthogonal_modes(n_modes=2, n=1.5, nx=4, ny=8)
        cell0 = EmeCell(length=1e-6, modes=modes_a)
        cell1 = EmeCell(length=1e-6, modes=modes_b)
        with pytest.raises(ValueError, match="网格形状"):
            EmeSolver(cells=[cell0, cell1], config=cfg)

    def test_single_cell_uniform_waveguide(self) -> None:
        """单 cell 退化：均匀波导段，无反射，仅相位累积。"""
        n = 2.0
        modes = _make_orthogonal_modes(n_modes=2, n=n)
        cfg = EmeConfig(wavelength=1.55e-6, dx=1e-8, dy=1e-8)
        cell = EmeCell(length=1e-6, modes=modes)
        result = EmeSolver(cells=[cell], config=cfg).solve()
        # 单 cell 无界面，仅传播 S21 = diag(exp(i·β·L))
        k0 = 2.0 * np.pi / 1.55e-6
        beta = k0 * n
        expected_phase = np.exp(1j * beta * 1e-6)
        assert np.allclose(np.diag(result.s_matrix.s21), expected_phase, atol=1e-10)
        # 无反射
        assert np.allclose(result.s_matrix.s11, 0.0, atol=1e-10)
        # 能量守恒（无损耗传播）
        assert np.isclose(result.energy_sum, 1.0, atol=1e-10)

    def test_multicell_cascade_stability(self) -> None:
        """N=10 cell 级联数值稳定，无指数溢出（M3 验收点）。"""
        n = 1.5
        modes = _make_orthogonal_modes(n_modes=3, n=n)
        cfg = EmeConfig(wavelength=1.55e-6, dx=1e-8, dy=1e-8)
        # 10 个同介质 cell（无界面反射，纯传播累积）
        cells = [EmeCell(length=1e-6, modes=modes) for _ in range(10)]
        result = EmeSolver(cells=cells, config=cfg).solve()
        # 同介质无反射，能量守恒
        assert np.isclose(result.energy_sum, 1.0, atol=1e-6), (
            f"10 cell 级联能量守恒偏差: {result.energy_sum}"
        )
        assert result.n_cells == 10
        assert result.n_modes == 3

    def test_cascade_with_interface_energy(self) -> None:
        """含界面的多 cell 级联能量守恒（M2/M3 联合验收）。"""
        modes_a = _make_orthogonal_modes(n_modes=2, n=2.0)
        modes_b = _make_orthogonal_modes(n_modes=2, n=3.0)
        cfg = EmeConfig(wavelength=1.55e-6, dx=1e-8, dy=1e-8)
        # n=2 → n=3 → n=2（对称结构，往返反射抵消）
        cells = [
            EmeCell(length=0.0, modes=modes_a),  # 输入参考
            EmeCell(length=1e-6, modes=modes_b),  # n=3 段
            EmeCell(length=0.0, modes=modes_a),  # 输出参考
        ]
        result = EmeSolver(cells=cells, config=cfg).solve()
        # 功率归一化模式 → 能量守恒
        assert np.isclose(result.energy_sum, 1.0, atol=1e-6), (
            f"对称结构能量守恒偏差: {result.energy_sum}"
        )


# ---------------------------------------------------------------------------
# solve_eme 便捷入口 + 自由空间透明
# ---------------------------------------------------------------------------


class TestSolveEme:
    """solve_eme 便捷入口与自由空间物理验证。"""

    def test_solve_eme_returns_result(self) -> None:
        """solve_eme 返回 EmeResult 类型。"""
        modes = _make_orthogonal_modes(n_modes=2, n=1.5)
        cfg = EmeConfig(wavelength=1.55e-6, dx=1e-8, dy=1e-8)
        cells = [EmeCell(length=1e-6, modes=modes)]
        result = solve_eme(cells, cfg)
        assert isinstance(result, EmeResult)
        assert isinstance(result.s_matrix, BlockSMatrix)
        assert result.reflection.shape == (2,)
        assert result.transmission.shape == (2,)

    def test_free_space_transparent(self) -> None:
        """同介质多 cell → 无反射，S21 = 传播相位（自由空间透明性）。"""
        n = 1.5
        modes = _make_orthogonal_modes(n_modes=2, n=n)
        cfg = EmeConfig(wavelength=1.55e-6, dx=1e-8, dy=1e-8)
        # 3 个同介质 cell，总长 = 2e-6（cell0 不传播，cell1+cell2 各 1e-6）
        cells = [
            EmeCell(length=0.0, modes=modes),  # 输入参考
            EmeCell(length=1e-6, modes=modes),
            EmeCell(length=1e-6, modes=modes),
        ]
        result = solve_eme(cells, cfg)
        # 无反射
        assert np.allclose(result.s_matrix.s11, 0.0, atol=1e-10)
        # 总透射相位 = exp(i·β·2e-6)
        k0 = 2.0 * np.pi / 1.55e-6
        beta = k0 * n
        expected_total_phase = np.exp(1j * beta * 2e-6)
        assert np.allclose(np.diag(result.s_matrix.s21), expected_total_phase, atol=1e-10)

    def test_analysis_mode_length_sweep(self) -> None:
        """Analysis 模式：cell 长度扫描不重算模式（M4 间接验收）。"""
        n = 2.0
        modes = _make_orthogonal_modes(n_modes=2, n=n)
        cfg = EmeConfig(wavelength=1.55e-6, dx=1e-8, dy=1e-8)
        k0 = 2.0 * np.pi / 1.55e-6
        beta = k0 * n
        # 扫描不同长度，验证 S21 相位与长度线性相关
        for length in [0.5e-6, 1.0e-6, 2.0e-6, 5.0e-6]:
            cells = [EmeCell(length=length, modes=modes)]
            result = solve_eme(cells, cfg)
            expected_phase = np.exp(1j * beta * length)
            assert np.allclose(np.diag(result.s_matrix.s21), expected_phase, atol=1e-10)

    def test_fresnel_two_port_sparam(self) -> None:
        """单界面 EME → S11 = Fresnel r, S21 = Fresnel t（M2 端口验收）。"""
        n1, n2 = _N_SIO2, _N_SI
        modes_a = [_make_plane_wave_mode(n=n1)]
        modes_b = [_make_plane_wave_mode(n=n2)]
        cfg = EmeConfig(wavelength=1.55e-6, dx=1e-8, dy=1e-8)
        cells = [
            EmeCell(length=0.0, modes=modes_a),  # 输入参考
            EmeCell(length=0.0, modes=modes_b),  # 输出参考
        ]
        result = solve_eme(cells, cfg)
        r_expected = _fresnel_r(n1, n2)
        t_expected = _fresnel_t(n1, n2)
        assert np.isclose(result.reflection[0], r_expected, atol=1e-10)
        assert np.isclose(result.transmission[0], t_expected, atol=1e-10)

    def test_empty_cells_raises(self) -> None:
        """空 cell 列表 raise（规则 14）。"""
        cfg = EmeConfig(wavelength=1.55e-6, dx=1e-8, dy=1e-8)
        with pytest.raises(ValueError, match="cell 列表不能为空"):
            solve_eme([], cfg)


# ---------------------------------------------------------------------------
# 能量守恒综合验证（M2/M3 物理正确性）
# ---------------------------------------------------------------------------


class TestEnergyConservation:
    """能量守恒综合验证（无源系统 Σ|R|² + Σ|T|² = 1）。"""

    def test_uniform_waveguide_energy(self) -> None:
        """均匀波导段能量守恒（无反射，全部透射）。"""
        n = 2.0
        modes = _make_orthogonal_modes(n_modes=3, n=n)
        cfg = EmeConfig(wavelength=1.55e-6, dx=1e-8, dy=1e-8)
        cells = [EmeCell(length=5e-6, modes=modes)]
        result = solve_eme(cells, cfg)
        assert np.isclose(result.energy_sum, 1.0, atol=1e-10)

    def test_symmetric_interface_energy(self) -> None:
        """对称界面 n1→n2→n1 能量守恒（往返反射抵消）。"""
        modes_a = _make_orthogonal_modes(n_modes=2, n=2.0)
        modes_b = _make_orthogonal_modes(n_modes=2, n=3.0)
        cfg = EmeConfig(wavelength=1.55e-6, dx=1e-8, dy=1e-8)
        cells = [
            EmeCell(length=0.0, modes=modes_a),
            EmeCell(length=2e-6, modes=modes_b),
            EmeCell(length=0.0, modes=modes_a),
        ]
        result = solve_eme(cells, cfg)
        assert np.isclose(result.energy_sum, 1.0, atol=1e-6), (
            f"对称界面能量守恒偏差: {result.energy_sum}"
        )

    def test_long_cascade_no_overflow(self) -> None:
        """长级联（20 cell）无溢出（M3 数值稳定性）。"""
        n = 1.5
        modes = _make_orthogonal_modes(n_modes=2, n=n)
        cfg = EmeConfig(wavelength=1.55e-6, dx=1e-8, dy=1e-8)
        cells = [EmeCell(length=1e-6, modes=modes) for _ in range(20)]
        result = solve_eme(cells, cfg)
        # 无源系统能量守恒
        assert np.isclose(result.energy_sum, 1.0, atol=1e-6)
        # S21 范数有界（无指数发散）
        s21_norm = np.linalg.norm(result.s_matrix.s21, ord=2)
        assert s21_norm <= 1.0 + 1e-6


# ---------------------------------------------------------------------------
# 与 C03-Redheffer 接口兼容性（A02 §9.1 共享组件）
# ---------------------------------------------------------------------------


class TestCascadeInterfaceCompat:
    """EME S 矩阵与 C03-Redheffer 星积接口兼容性（A02 §9.1 共享内核）。"""

    def test_eme_smatrix_cascadable(self) -> None:
        """EME 界面 S 矩阵可被 cascade_redheffer 直接级联。"""
        modes_a = _make_orthogonal_modes(n_modes=2, n=2.0)
        modes_b = _make_orthogonal_modes(n_modes=2, n=3.0)
        dx, dy = 1e-8, 1e-8
        s_iface = build_interface_smatrix(modes_a, modes_b, dx, dy)
        # 构造透明传播 S（与界面级联应不报错）
        betas = np.array([m.beta for m in modes_b], dtype=np.complex128)
        s_prop = build_propagation_smatrix(betas, 1e-6)
        # Redheffer 星积级联（C03 共享内核）
        s_total = cascade_redheffer([s_iface, s_prop])
        assert isinstance(s_total, BlockSMatrix)
        assert s_total.n_ports == 2

    def test_eme_propagation_compatible_with_c03(self) -> None:
        """EME build_propagation_smatrix 与 C03 build_propagation_s 公式一致。"""
        from polaris.sim.cascade.smatrix import build_propagation_s

        betas = np.array([1.0 + 0j, 2.0 + 0j, 3.0 + 0j])
        length = 0.5
        s_eme = build_propagation_smatrix(betas, length)
        s_c03 = build_propagation_s(betas, length)
        assert np.allclose(s_eme.s11, s_c03.s11)
        assert np.allclose(s_eme.s21, s_c03.s21)
        assert np.allclose(s_eme.s12, s_c03.s12)
        assert np.allclose(s_eme.s22, s_c03.s22)
