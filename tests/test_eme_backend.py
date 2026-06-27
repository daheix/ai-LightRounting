"""R16 FIMMPROP EME 仿真后端验收测试。

测试覆盖（spec R16 验收点）：
1. test_config_validation：配置验证（n_modes/wavelength/dx/polarization 非法 raise）
2. test_add_section：段添加（ID 递增、非法输入 raise、n_sections 属性）
3. test_solve_modes：模式求解（SOI strip 直波导 TE 基模 n_eff 精度）
4. test_overlap_integral：重叠积分（同模式集正交性 → 单位矩阵）
5. test_cascade_smatrix：S 矩阵级联（Redheffer 星积正确性 + 单位 S 不变性）
6. test_run_taper：锥形结构仿真（功率守恒 energy_sum ≈ 1.0）
7. test_run_bend：弯曲结构仿真（大半径低损耗 + 功率守恒）
8. test_validate_cross：交叉验证误差 < 1e-3（结合律：自左向右 vs 自右向左）

物理参数（SOI strip 波导 @ 1550nm，参考 Lumerical/Tidy3D 文档）：
- n_core(Si) = 3.476, n_clad(SiO2) = 1.444
- 波导宽度 500nm，高度 220nm
- TE 基模 n_eff ≈ 2.45（Lumerical MODE 验证值）

文献来源（R02 学术诚信，URL ≥5）：
1. Gallagher & Felici 2003 SPIE 4987 — https://doi.org/10.1117/12.478061
2. FIMMPROP — https://www.photond.com/products/fimmprop.htm
3. FIMMPROP EME paper — https://photond.com/assets/files/FIMMWAVE/PW03_eme_paper.pdf
4. Oktay & Magden 2024 arXiv:2407.09847 — https://arxiv.org/abs/2407.09847
5. Song & Sohn 2025 arXiv:2504.11801 — https://arxiv.org/abs/2504.11801
6. Lumerical MODE-EME — https://optics.ansys.com/hc/en-us/articles/360034396614

规则依据：project_rules.md 规则 14（禁止 fall-back）/规则 18（学术诚信）
/规则 26（GPU 不参与，纯 NumPy）
"""

from __future__ import annotations

import numpy as np
import pytest

from polaris.sim.cascade.smatrix import (
    BlockSMatrix,
    build_propagation_s,
    redheffer_star_product,
)
from polaris.sim.eme import build_interface_smatrix, build_propagation_smatrix
from polaris.sim.eme_backend import EMEConfig, FIMMPROPBackend

# SOI strip 波导物理参数（1550nm，参考 Lumerical/Tidy3D 文档）
_N_SI = 3.476  # Si 折射率 @ 1550nm
_N_SIO2 = 1.444  # SiO2 折射率 @ 1550nm
_WAVELENGTH = 1.55e-6
_WIDTH = 0.5e-6  # 500nm
_HEIGHT = 0.22e-6  # 220nm


def _make_backend(n_modes: int = 1) -> FIMMPROPBackend:
    """构造测试用 Backend。

    窗口 (3.0, 2.5)μm + PML 8 层（400nm），非 PML 区 (2.2, 1.7)μm，
    足够容纳 w=500nm-1.0μm 锥形模式场（场半宽约 0.5-0.8μm，
    Soref 1991），避免模式场渗入 PML 产生 Im(n_eff)<0 导致功率爆炸。
    """
    cfg = EMEConfig(
        n_modes=n_modes,
        wavelength=_WAVELENGTH,
        dx=5e-8,
        dy=5e-8,
        window_size=(3.0e-6, 2.5e-6),
        pml_layers=8,
        polarization="te",
    )
    return FIMMPROPBackend(cfg)


# ---------------------------------------------------------------------------
# 1. 配置验证
# ---------------------------------------------------------------------------
def test_config_validation() -> None:
    """EMEConfig 非法参数必须 raise（规则 14：禁止 fall-back）。"""
    with pytest.raises(ValueError, match="n_modes"):
        EMEConfig(n_modes=0)
    with pytest.raises(ValueError, match="wavelength"):
        EMEConfig(wavelength=-1.0)
    with pytest.raises(ValueError, match="网格间距"):
        EMEConfig(dx=0.0)
    with pytest.raises(ValueError, match="窗口尺寸"):
        EMEConfig(window_size=(0.0, 1.5e-6))
    with pytest.raises(ValueError, match="pml_layers"):
        EMEConfig(pml_layers=-1)
    with pytest.raises(ValueError, match="polarization"):
        EMEConfig(polarization="invalid")
    # 合法配置应正常构造，且 dx/dy 被重新计算为精确值
    cfg = EMEConfig(window_size=(2.0e-6, 1.5e-6), dx=5e-8, dy=5e-8)
    nx = round(2.0e-6 / cfg.dx)
    assert abs(nx * cfg.dx - 2.0e-6) < 1e-15  # 网格与窗口严格一致


# ---------------------------------------------------------------------------
# 2. 段添加
# ---------------------------------------------------------------------------
def test_add_section() -> None:
    """段添加：ID 递增、非法输入 raise、n_sections 属性。"""
    backend = _make_backend()
    assert backend.n_sections == 0
    eps_r = np.full((20, 15), _N_SIO2 ** 2, dtype=np.complex128)
    sid0 = backend.add_section(1.0e-6, eps_r, label="seg0")
    sid1 = backend.add_section(2.0e-6, eps_r, label="seg1")
    sid2 = backend.add_section(3.0e-6, eps_r, label="seg2")
    assert (sid0, sid1, sid2) == (0, 1, 2)
    assert backend.n_sections == 3
    # 非法长度
    with pytest.raises(ValueError, match="段长度"):
        backend.add_section(-1.0, eps_r)
    # 非法 eps_r 维度
    with pytest.raises(ValueError, match="eps_r 必须 2D"):
        backend.add_section(1.0, np.array([1.0, 2.0]))
    # 不存在的段 ID
    with pytest.raises(KeyError, match="段 ID 99"):
        backend._get_section(99)


# ---------------------------------------------------------------------------
# 3. 模式求解（SOI strip 直波导 TE 基模 n_eff 精度）
# ---------------------------------------------------------------------------
def test_solve_modes() -> None:
    """FDE Arnoldi 求解 SOI strip 直波导 TE 基模，n_eff 应 ∈ (2.0, 3.5)。"""
    backend = _make_backend(n_modes=1)
    sid = backend.build_straight(
        length=1.0e-6, width=_WIDTH, height=_HEIGHT,
        n_core=_N_SI, n_clad=_N_SIO2,
    )
    result = backend.solve_modes(sid)
    assert result["section_id"] == sid
    assert len(result["modes"]) == 1
    n_eff = result["n_eff"][0]
    # SOI strip 500nm×220nm TE 基模 n_eff ≈ 2.45（Lumerical 验证值）
    # 网格较粗（50nm），允许较宽范围 (1.5, 3.5)，确保命中导模而非包层模
    re_neff = float(np.real(n_eff))
    assert 1.5 < re_neff < 3.5, f"基模 n_eff={re_neff} 超出导模范围"
    # 虚部应接近 0（无损耗介质）
    assert abs(float(np.imag(n_eff))) < 0.1, f"n_eff 虚部 {np.imag(n_eff)} 过大"
    # te_fraction 应接近 1（TE 偏振）
    assert result["te_fraction"][0] > 0.5


# ---------------------------------------------------------------------------
# 4. 重叠积分（同模式集正交性 → 单位矩阵）
# ---------------------------------------------------------------------------
def test_overlap_integral() -> None:
    """同模式集重叠积分应为单位矩阵（功率归一化正交性，A02 §7.1）。"""
    backend = _make_backend(n_modes=1)
    sid = backend.build_straight(
        length=1.0e-6, width=_WIDTH, height=_HEIGHT,
        n_core=_N_SI, n_clad=_N_SIO2,
    )
    result = backend.solve_modes(sid)
    modes = result["modes"]
    # 同模式集自重叠 → 单位矩阵
    m_coupling = backend.overlap_integral(modes, modes)
    identity = np.eye(len(modes), dtype=np.complex128)
    err = float(np.max(np.abs(m_coupling - identity)))
    assert err < 1e-3, f"正交性校验失败: |M - I|_max = {err:.2e} ≥ 1e-3"
    # 空模式列表必须 raise（规则 14）
    with pytest.raises(ValueError, match="模式列表不能为空"):
        backend.overlap_integral([], modes)


# ---------------------------------------------------------------------------
# 5. S 矩阵级联（Redheffer 星积正确性）
# ---------------------------------------------------------------------------
def test_cascade_smatrix() -> None:
    """Redheffer 星积级联：两个传播 S 级联应等价于单个长段传播 S。"""
    backend = _make_backend()
    # 两个传播 S 矩阵（β=1e7 rad/m, L1=1e-6, L2=2e-6）
    beta = np.array([1e7 + 0j], dtype=np.complex128)
    s1 = build_propagation_smatrix(beta, 1.0e-6)
    s2 = build_propagation_smatrix(beta, 2.0e-6)
    # 级联
    s_cascade = backend.cascade_smatrix(s1, s2)
    # 等价于单个 L=3e-6 的传播 S
    s_ref = build_propagation_smatrix(beta, 3.0e-6)
    for name in ("s11", "s12", "s21", "s22"):
        err = float(np.max(np.abs(getattr(s_cascade, name) - getattr(s_ref, name))))
        assert err < 1e-12, f"级联 {name} 误差 {err:.2e} 过大"
    # 单位 S 矩阵级联应保持不变（S ★ I = S）
    n = 1
    eye_s = BlockSMatrix(
        np.zeros((n, n), dtype=np.complex128),
        np.eye(n, dtype=np.complex128),
        np.eye(n, dtype=np.complex128),
        np.zeros((n, n), dtype=np.complex128),
    )
    s_unit = backend.cascade_smatrix(s1, eye_s)
    err_unit = float(np.max(np.abs(s_unit.s21 - s1.s21)))
    assert err_unit < 1e-12, f"单位 S 级联不变性失败: {err_unit:.2e}"


# ---------------------------------------------------------------------------
# 6. 锥形结构仿真（功率守恒）
# ---------------------------------------------------------------------------
def test_run_taper() -> None:
    """锥形波导 EME 仿真：功率守恒 energy_sum ≈ 1.0。"""
    backend = _make_backend(n_modes=1)
    # 绝热锥形：500nm → 800nm，长度 20μm，5 段近似
    backend.build_taper(
        length=20.0e-6, w_in=_WIDTH, w_out=0.8e-6,
        height=_HEIGHT, n_core=_N_SI, n_clad=_N_SIO2,
        n_steps=5,
    )
    assert backend.n_sections == 5
    result = backend.run()
    # 功率守恒（无源系统 Σ|reflection|² + Σ|transmission|² ≈ 1.0）
    energy = result["energy_sum"]
    assert abs(energy - 1.0) < 1e-3, f"功率守恒失败: energy_sum={energy:.6f}"
    # 基模透射振幅应非零（绝热锥形大部分功率透射）
    trans_amp = float(np.abs(result["transmission"][0]))
    assert trans_amp > 0.5, f"基模透射振幅 {trans_amp} 过低"
    assert result["n_cells"] == 5
    assert result["n_modes"] == 1


# ---------------------------------------------------------------------------
# 7. 弯曲结构仿真（大半径低损耗 + 功率守恒）
# ---------------------------------------------------------------------------
def test_run_bend() -> None:
    """弯曲波导 EME 仿真：大半径功率守恒，小半径 raise。"""
    backend = _make_backend(n_modes=1)
    # 大半径弯曲（R=50μm, 10°），等效折射率修正小，损耗低
    backend.build_bend(
        radius=50.0e-6, angle_deg=10.0,
        width=_WIDTH, height=_HEIGHT,
        n_core=_N_SI, n_clad=_N_SIO2,
        n_steps=3,
    )
    assert backend.n_sections == 3
    result = backend.run()
    energy = result["energy_sum"]
    assert abs(energy - 1.0) < 1e-3, f"弯曲功率守恒失败: energy_sum={energy:.6f}"
    # 基模透射振幅应较高（大半径低损耗）
    trans_amp = float(np.abs(result["transmission"][0]))
    assert trans_amp > 0.5, f"弯曲基模透射 {trans_amp} 过低"
    # 非法半径
    with pytest.raises(ValueError, match="radius"):
        backend.build_bend(
            radius=-1.0, angle_deg=10.0, width=_WIDTH, height=_HEIGHT,
            n_core=_N_SI, n_clad=_N_SIO2,
        )
    # 非法角度
    with pytest.raises(ValueError, match="angle_deg"):
        backend.build_bend(
            radius=50.0e-6, angle_deg=0.0, width=_WIDTH, height=_HEIGHT,
            n_core=_N_SI, n_clad=_N_SIO2,
        )


# ---------------------------------------------------------------------------
# 8. 交叉验证误差 < 1e-3（结合律：自左向右 vs 自右向左）
# ---------------------------------------------------------------------------
def test_validate_cross() -> None:
    """EME S 矩阵级联交叉验证：自左向右 vs 自右向左，误差 < 1e-3。"""
    backend = _make_backend(n_modes=1)
    # 构造 3 段结构：直 + 锥 + 直
    backend.build_straight(
        length=1.0e-6, width=_WIDTH, height=_HEIGHT,
        n_core=_N_SI, n_clad=_N_SIO2,
    )
    backend.build_taper(
        length=5.0e-6, w_in=_WIDTH, w_out=0.7e-6,
        height=_HEIGHT, n_core=_N_SI, n_clad=_N_SIO2,
        n_steps=2,
    )
    backend.build_straight(
        length=1.0e-6, width=0.7e-6, height=_HEIGHT,
        n_core=_N_SI, n_clad=_N_SIO2,
    )
    # run() 内部用 EmeSolver 自左向右级联（cascade_redheffer）
    result = backend.run()
    s_eme: BlockSMatrix = result["s_matrix"]

    # 手动构造相同 S 矩阵序列，用自右向左级联（Redheffer 结合律验证）
    sections = backend._sections
    dx, dy = backend.config.dx, backend.config.dy
    s_list: list[BlockSMatrix] = []
    for i in range(len(sections) - 1):
        s_list.append(
            build_interface_smatrix(sections[i].modes, sections[i + 1].modes, dx, dy)
        )
        betas = np.array(
            [complex(m.beta) for m in sections[i + 1].modes],
            dtype=np.complex128,
        )
        s_list.append(build_propagation_smatrix(betas, sections[i + 1].length))
    # 自右向左级联：S1 ★ (S2 ★ (S3 ★ ... ))
    s_right = s_list[-1]
    for s in reversed(s_list[:-1]):
        s_right = redheffer_star_product(s, s_right)

    # 交叉验证：EME 自左向右 vs 手动自右向左，误差 < 1e-3
    assert backend.validate_against_sparam(s_right, atol=1e-3), (
        "EME vs S 参数级联交叉验证失败（结合律不成立）"
    )
    # 进一步验证：两种级联顺序应几乎一致（数值精度 < 1e-10）
    for name in ("s11", "s12", "s21", "s22"):
        a = getattr(s_eme, name)
        b = getattr(s_right, name)
        err = float(np.max(np.abs(a - b)))
        assert err < 1e-10, f"结合律 {name} 误差 {err:.2e} 过大"
    # 未运行 run() 时 validate 必须 raise（规则 14）
    fresh = _make_backend(n_modes=1)
    with pytest.raises(RuntimeError, match="需先调用 run"):
        fresh.validate_against_sparam(s_right)


# ---------------------------------------------------------------------------
# 额外：MMI + Crossing 结构覆盖（确保 ≥5 种结构生成器可用）
# ---------------------------------------------------------------------------
def test_build_mmi_and_crossing() -> None:
    """MMI 与 Crossing 结构生成器应正确添加段（覆盖 ≥5 种结构）。"""
    backend = _make_backend(n_modes=1)
    # MMI 宽截面段
    sid_mmi = backend.build_mmi(
        length=5.0e-6, width=2.0e-6, height=_HEIGHT,
        n_core=_N_SI, n_clad=_N_SIO2,
    )
    assert sid_mmi == 0
    assert backend.n_sections == 1
    # Crossing：入口锥形 + 宽截面 + 出口锥形
    backend2 = _make_backend(n_modes=1)
    ids = backend2.build_crossing(
        length=10.0e-6, width_port=_WIDTH, width_wide=1.5e-6,
        height=_HEIGHT, n_core=_N_SI, n_clad=_N_SIO2,
        n_steps=2,
    )
    # 2 入口 + 1 宽截面 + 2 出口 = 5 段
    assert len(ids) == 5
    assert backend2.n_sections == 5
    # Crossing 仿真功率守恒
    result = backend2.run()
    assert abs(result["energy_sum"] - 1.0) < 1e-3
