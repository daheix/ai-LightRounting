"""CML 自动生成模块（_cml_fit）测试。

验证:
1. FittedModel.evaluate 正确性
2. Vector Fitting (Gustavsen 1999) 已知有理函数恢复（一阶/二阶/高Q）
3. 无源性强制（|f|≤1）
4. R03 禁止 fall-back（全零数据 raise）
5. 波导参数提取（已知 neff/损耗）
6. 环谐振器 Lorentzian 拟合（已知 Q）
7. MMI 分束比/插入损耗/相位差
8. generate_cml_from_sparams 端到端

学术依据: R02 学术诚信 / R03 禁止 fall-back / R13 交付自测。
文献: Gustavsen & Semlyen 1999 https://doi.org/10.1109/61.772350
      Bogaerts 2012 https://doi.org/10.1109/JLT.2012.2200478
      Chrostowski & Hochberg 2015 Cambridge §3.2/§6
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

# sys.path 注入：使 src/polaris_lumerical 可被 import
_SRC = str(Path(__file__).resolve().parents[1] / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import polaris_lumerical as pl
from polaris_lumerical import (
    FittedModel, vector_fitting, fit_waveguide_params,
    fit_ring_resonator, fit_mmi_splitting, generate_cml_from_sparams,
)
from polaris_lumerical._cml_fit import _lorentzian_notch

_C0 = 2.99792458e8  # 真空光速 CODATA 2018


# =============================================================================
# 1. FittedModel.evaluate 正确性
# =============================================================================
def test_fitted_model_evaluate():
    """验证 FittedModel.evaluate 能精确重建已知有理模型。
    模型: f(s)=r/(s-p)+conj(r)/(s-conj(p))+d，无源性未强制。
    """
    p = -0.3 + 1j * 4.0
    r = 1.5 + 0.7j
    d = 0.2 + 0j
    freqs = np.linspace(0.1, 8.0, 150)
    s = 1j * 2.0 * np.pi * freqs
    f_true = r / (s - p) + np.conj(r) / (s - np.conj(p)) + d
    model = FittedModel(
        poles=np.array([p, np.conj(p)], dtype=complex),
        residues=np.array([r, np.conj(r)], dtype=complex),
        d=d, h=0j, fit_error=0.0, passivity_enforced=False)
    resp = model.evaluate(freqs)
    err = float(np.max(np.abs(resp - f_true)))
    assert err < 1e-12, f"FittedModel.evaluate 重建误差 {err:.3e} 过大"
    assert model.poles.shape == (2,)
    assert not model.passivity_enforced


# =============================================================================
# 2. Vector Fitting 已知有理函数恢复
# =============================================================================
def test_vector_fitting_known_rational():
    """验证 VF 能恢复已知二阶有理函数的极点/留数/常数项。
    来源: Gustavsen 1999 §IV, https://doi.org/10.1109/61.772350
    """
    np.random.seed(42)
    p_true = -0.5 + 1j * 5.0
    r_true = 2.0 + 1j * 0.5
    d_true = 0.1 + 0j
    freqs = np.linspace(0.01, 10.0, 200)
    s = 1j * 2.0 * np.pi * freqs
    f_data = r_true / (s - p_true) + np.conj(r_true) / (s - np.conj(p_true)) + d_true
    # 加微量噪声验证鲁棒性
    f_data += 1e-8 * (np.random.randn(len(freqs)) + 1j * np.random.randn(len(freqs)))

    model = vector_fitting(freqs, f_data, n_poles=4, max_iter=50,
                           enforce_passivity=False)
    # 拟合误差应极小
    assert model.fit_error < 1e-3, f"VF 拟合误差 {model.fit_error:.3e} 过大"
    # 检查是否找到真实极点（在拟合极点中存在接近 p_true 的）
    pole_match = min(min(abs(p - p_true), abs(p - np.conj(p_true)))
                     for p in model.poles)
    assert pole_match < 0.05, (
        f"VF 未恢复真实极点，最近距离 {pole_match:.3e}，"
        f"拟合极点 {model.poles}")
    # 所有极点须稳定（Re<0）
    assert np.all(model.poles.real < 0), "存在不稳定极点（Re>=0）"
    # 常数项接近真实
    assert abs(model.d - d_true) < 0.05, f"d={model.d} 偏离真实 {d_true}"


def test_vector_fitting_high_q_resonance():
    """验证 VF 能拟合高 Q（窄带）谐振，光子器件典型场景。"""
    p_true = -0.02 + 1j * 3.0  # Q = |Im|/(2|Re|) = 75
    r_true = 0.3 + 1j * 0.05
    d_true = 0.15 + 0j
    freqs = np.linspace(0.3, 1.5, 250)
    s = 1j * 2.0 * np.pi * freqs
    f_data = r_true / (s - p_true) + np.conj(r_true) / (s - np.conj(p_true)) + d_true
    model = vector_fitting(freqs, f_data, n_poles=4, max_iter=60,
                           enforce_passivity=False)
    assert model.fit_error < 1e-6, f"高Q VF 误差 {model.fit_error:.3e} 过大"
    pole_match = min(min(abs(p - p_true), abs(p - np.conj(p_true)))
                     for p in model.poles)
    assert pole_match < 0.02, f"高Q 极点恢复失败，距离 {pole_match:.3e}"


# =============================================================================
# 3. 无源性强制
# =============================================================================
def test_vector_fitting_passivity_enforcement():
    """验证无源性强制后 max|f(jω)| ≤ 1。
    来源: Grivet-Talocia 2007 §IV, https://doi.org/10.1109/TEMC.2006.888590
    """
    # 构造一个峰值 >1 的响应
    p = -0.1 + 1j * 2.0
    r = 3.0 + 1j * 0.5  # 大留数使峰值 >1
    d = 0.3 + 0j
    freqs = np.linspace(0.1, 4.0, 200)
    s = 1j * 2.0 * np.pi * freqs
    f_data = r / (s - p) + np.conj(r) / (s - np.conj(p)) + d
    peak_data = float(np.max(np.abs(f_data)))
    assert peak_data > 1.0, "测试数据峰值应 >1 才能验证强制"

    model = vector_fitting(freqs, f_data, n_poles=4, max_iter=50,
                           enforce_passivity=True)
    # 在密集频率点验证无源性
    dense = np.linspace(freqs[0], freqs[-1], 2000)
    resp = model.evaluate(dense)
    peak_model = float(np.max(np.abs(resp)))
    assert peak_model <= 1.0 + 1e-9, (
        f"无源性强制失败：max|f|={peak_model:.6f} > 1")
    assert model.passivity_enforced, "passivity_enforced 标志未置位"


# =============================================================================
# 4. R03 禁止 fall-back：全零数据 raise
# =============================================================================
def test_vector_fitting_raises_on_zero_data():
    """验证全零 s_data 触发 RuntimeError（R03 禁止 fall-back）。"""
    freqs = np.linspace(0.1, 10.0, 100)
    zero_data = np.zeros_like(freqs, dtype=complex)
    with pytest.raises(RuntimeError, match="全零"):
        vector_fitting(freqs, zero_data, n_poles=4)


def test_vector_fitting_raises_on_bad_npoles():
    """验证奇数 n_poles 触发 ValueError。"""
    freqs = np.linspace(0.1, 10.0, 100)
    s = 1j * 2.0 * np.pi * freqs
    f = 1.0 / (s + 1 + 0j)
    with pytest.raises(ValueError):
        vector_fitting(freqs, f, n_poles=3)


# =============================================================================
# 5. 波导参数提取（已知 neff/损耗）
# =============================================================================
def test_fit_waveguide_params():
    """验证从已知 neff/损耗的 S21 提取参数。
    公式: S21 = 10^(-α·L_cm/20) · exp(-j·2π·neff·L/λ)
    来源: Chrostowski & Hochberg 2015 §3.2,
    https://www.cambridge.org/core/books/silicon-photonics-design/
    """
    neff_true = 2.4              # 无色散 neff
    alpha_db_per_cm_true = 3.0   # 传播损耗 dB/cm
    length_um = 200.0            # 波导长度
    wl = np.linspace(1.5, 1.6, 201)  # 波长 um
    length_cm = length_um * 1e-4
    # 振幅 |S21| = 10^(-α·L_cm/20)，相位 = -2π·neff·L/λ
    amp = 10.0 ** (-alpha_db_per_cm_true * length_cm / 20.0)
    phase = -2.0 * np.pi * neff_true * length_um / wl
    s21 = amp * np.exp(1j * phase)

    result = fit_waveguide_params(wl, s21, length_um)
    # neff 应为常数 = 2.4
    n_eff = result["n_eff"]
    assert np.allclose(n_eff, neff_true, atol=1e-6), (
        f"neff 提取偏差 {np.max(np.abs(n_eff - neff_true)):.3e}")
    # 无色散时 n_g = n_eff
    assert abs(result["n_g_center"] - neff_true) < 1e-4, (
        f"n_g={result['n_g_center']:.4f} 偏离 {neff_true}")
    # 损耗
    alpha_mean = result["alpha_mean_db_per_cm"]
    assert abs(alpha_mean - alpha_db_per_cm_true) < 0.1, (
        f"α={alpha_mean:.4f} dB/cm 偏离 {alpha_db_per_cm_true}")


# =============================================================================
# 6. 环谐振器 Lorentzian 拟合（已知 Q）
# =============================================================================
def test_fit_ring_resonator():
    """验证从已知 Lorentzian 下陷提取 Q 和谐振波长。
    来源: Bogaerts 2012 JLT 30(12), https://doi.org/10.1109/JLT.2012.2200478
    """
    wl_r_true = 1550.0e-3      # 谐振波长 1550nm → um
    gamma_true = 5.0e-3        # HWHM = 5pm → FWHM=10pm
    depth_true = 0.8           # 下陷深度
    baseline_true = 1.0
    Q_true = wl_r_true / (2.0 * gamma_true)  # Q = λ_r/FWHM
    wl = np.linspace(1.549, 1.551, 1001)  # ±1nm 窗口
    T = _lorentzian_notch(wl, wl_r_true, gamma_true, depth_true, baseline_true)
    # 加微量噪声
    np.random.seed(7)
    T = T + 1e-5 * np.random.randn(len(wl))
    T = np.clip(T, 0.0, 1.0)

    result = fit_ring_resonator(wl, T)
    assert abs(result["lambda_r_um"] - wl_r_true) < 1e-4, (
        f"λ_r={result['lambda_r_um']:.6f} 偏离 {wl_r_true}")
    # Q 相对误差 <5%
    Q_rel_err = abs(result["Q"] - Q_true) / Q_true
    assert Q_rel_err < 0.05, f"Q={result['Q']:.1f} 偏离 {Q_true:.1f}（{Q_rel_err:.3%}）"
    # 耦合系数 κ≈√depth（临界耦合近似）
    assert abs(result["coupling_kappa"] - np.sqrt(depth_true)) < 0.1, (
        f"κ={result['coupling_kappa']:.4f} 偏离 √{depth_true}")


# =============================================================================
# 7. MMI 分束比/插入损耗/相位差
# =============================================================================
def test_fit_mmi_splitting():
    """验证从理想 50:50 MMI S 矩阵提取分束比=1、插入损耗≈0、相位差≈0。
    来源: Lumerical CML Compiler, https://optics.ansys.com/hc/en-us/articles/360034902353
    """
    wl = np.linspace(1.5, 1.6, 51)
    nf = len(wl)
    # 理想 2x2 MMI（4 端口表示）：S[0,1]=S[0,2]=1/√2, 相位 0
    S = np.zeros((nf, 4, 4), dtype=complex)
    amp = 1.0 / np.sqrt(2.0)
    S[:, 0, 1] = amp
    S[:, 0, 2] = amp
    # 互易性
    S[:, 1, 0] = amp
    S[:, 2, 0] = amp

    result = fit_mmi_splitting(wl, S)
    # 分束比 |S13|²/|S12|² = 1
    assert abs(result["splitting_ratio_mean"] - 1.0) < 1e-9, (
        f"分束比={result['splitting_ratio_mean']:.6f} 偏离 1")
    # 插入损耗 ≈ 0（两输出功率和=1）
    assert result["insertion_loss_mean_db"] < 1e-6, (
        f"插入损耗={result['insertion_loss_mean_db']:.6f} 应≈0")
    # 相位差 ≈ 0
    assert abs(result["phase_diff_mean_rad"]) < 1e-9, (
        f"相位差={result['phase_diff_mean_rad']:.6f} 应≈0")
    # 不平衡度 ≈ 0 dB
    assert abs(result["imbalance_mean_db"]) < 1e-9


def test_fit_mmi_splitting_unbalanced():
    """验证非对称 MMI（70:30）分束比提取。"""
    wl = np.linspace(1.5, 1.6, 51)
    nf = len(wl)
    S = np.zeros((nf, 4, 4), dtype=complex)
    # 70:30 分束
    p2 = 0.7
    p3 = 0.3
    S[:, 0, 1] = np.sqrt(p2)
    S[:, 0, 2] = np.sqrt(p3)
    result = fit_mmi_splitting(wl, S)
    # 分束比 = p3/p2 = 0.3/0.7
    expected = p3 / p2
    assert abs(result["splitting_ratio_mean"] - expected) < 1e-9, (
        f"分束比={result['splitting_ratio_mean']:.6f} 偏离 {expected}")


# =============================================================================
# 8. generate_cml_from_sparams 端到端
# =============================================================================
def test_generate_cml_from_sparams():
    """验证从 S 参数自动生成 CML 元件（VF + CMLCompiler 编排）。
    来源: Lumerical CML Compiler, https://optics.ansys.com/hc/en-us/articles/360034902353
    """
    # 2 端口波导 S 参数：S11≈0，S21=已知波导传输
    wl = np.linspace(1.5, 1.6, 61)
    neff = 2.4
    length_um = 100.0
    amp = 0.9  # 含损耗
    phase = -2.0 * np.pi * neff * length_um / wl
    nf = len(wl)
    S = np.zeros((nf, 2, 2), dtype=complex)
    S[:, 0, 1] = amp * np.exp(1j * phase)
    S[:, 1, 0] = amp * np.exp(1j * phase)  # 互易
    S[:, 0, 0] = 0.01 + 0j  # 微小反射
    S[:, 1, 1] = 0.01 + 0j

    comp = generate_cml_from_sparams(
        name="wg_test", port_names=["in", "out"],
        wavelengths_um=wl, s_matrix=S, n_poles=6, model_type="waveguide")
    # 返回 CMLComponent
    assert comp.metadata.name == "wg_test"
    assert comp.port_names == ["in", "out"]
    assert comp.s_matrix.shape == (nf, 2, 2)
    # 重建 S 参数应接近原始
    err = float(np.max(np.abs(comp.s_matrix - S)))
    assert err < 0.05, f"CML 重建 S 参数误差 {err:.3e} 过大"
    # 互易性应满足（S21≈S12）
    assert comp.metadata.reciprocity_ok, "互易性诊断失败"
    # 无源性（|S|≤1，峰值 amp=0.9 <1）
    assert comp.metadata.passivity_ok, "无源性诊断失败"


def test_generate_cml_module_exports():
    """验证 _cml_fit 全部 API 在 polaris_lumerical 顶层导出。"""
    for name in ["FittedModel", "vector_fitting", "fit_waveguide_params",
                 "fit_ring_resonator", "fit_mmi_splitting",
                 "generate_cml_from_sparams"]:
        assert hasattr(pl, name), f"缺少导出: {name}"
        assert name in pl.__all__, f"{name} 未在 __all__"
