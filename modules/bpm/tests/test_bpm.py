"""polaris-bpm 子模块测试（R13 强制自测）。

测试覆盖（≥2 个 pytest，任务要求）:
- test_bpm_straight_waveguide: 直波导 BPM 传输率合理（> 0.5，含物理损耗）
- test_bpm_field_finite: 末态场分布有限（无 NaN）
- test_invalid_params: 非法参数 raise（R03 禁止 fall-back）
- test_transmission_loss_regression: 传输率回归测试（必须为合理负 dB，R05）
- test_loss_profile: 损耗分布物理正确性（Soref 芯区 + CAP 边界渐变）

来源（R02 学术诚信）:
- pytest 文档 https://docs.pytest.org/
- Feit & Fleck 1978 Appl. Opt.（BPM 理论）
  https://opg.optica.org/ao/abstract.cfm?uri=ao-17-24-3990
- Crank & Nicolson 1947（隐式差分格式）
- Chung & Dagli 1990 IEEE JQE（ADI 扩展）
  https://ieeexplore.ieee.org/document/59635
- scipy.linalg.solve_banded
  https://docs.scipy.org/doc/scipy/reference/generated/scipy.linalg.solve_banded.html
- Soref 1993 Proc. IEEE（SOI 波导损耗）
  https://ieeexplore.ieee.org/document/249720
- Hadley 1992 Opt. Lett.（TBC/CAP 边界）
  https://opg.optica.org/ol/abstract.cfm?uri=ol-17-10-726
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pytest

# 让测试既能从已安装包导入，也能从源码树导入
_SRC = str(Path(__file__).resolve().parents[1] / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import polaris_bpm  # noqa: E402
from polaris_bpm import (  # noqa: E402
    CAP_FRACTION,
    CAP_STRENGTH,
    LOSS_DB_PER_CM_SI,
    build_loss_profile,
    solve_bpm,
)


def test_bpm_straight_waveguide():
    """直波导 BPM: 传输率 > 0.5（含 Soref 材料损耗 + CAP 边界吸收）。

    高斯光束在直波导中传播 20μm：
    - Soref 1993 SOI 3 dB/cm → 20μm 约 0.006 dB 材料损耗
    - 高斯-基模失配的辐射模被 CAP 吸收 ~0.1 dB
    总损耗 ~0.1 dB，传输率 ~0.977 > 0.5。短直波导主体功率应保留。
    """
    result = solve_bpm(
        width_um=0.5, length_um=20.0, wavelength_um=1.55,
        n_core=3.476, n_clad=1.444,
        dz_um=0.1, dx_um=0.02, pad_um=2.0,
    )
    # 传输率为有限正数
    t = result["transmission"]
    assert math.isfinite(t), f"transmission 必须有限，得到 {t}"
    assert t > 0, f"transmission 应 > 0，得到 {t}"
    # 直波导短距离损耗小，传输率应 > 0.5
    assert t > 0.5, (
        f"直波导 BPM 传输率应 > 0.5，得到 {t}"
    )
    # 元数据
    assert result["n_steps"] > 0
    assert result["wavelength_um"] == 1.55
    assert result["grid_info"]["nx"] > 0
    assert result["grid_info"]["nz"] > 0
    # 功率值合理
    assert result["p_initial"] > 0
    assert result["p_final"] > 0
    # 损耗元数据
    assert result["loss"]["loss_db_per_cm"] == LOSS_DB_PER_CM_SI
    assert result["loss"]["cap_strength"] == CAP_STRENGTH


def test_bpm_field_finite():
    """末态场分布有限（无 NaN/Inf）。

    Crank-Nicolson 无条件稳定，场不应发散。
    """
    result = solve_bpm(
        width_um=0.5, length_um=10.0, wavelength_um=1.55,
        n_core=3.476, n_clad=1.444,
        dz_um=0.05, dx_um=0.02, pad_um=2.0,
    )
    field = np.array(result["field_z"], dtype=complex)
    assert field.shape == (result["grid_info"]["nx"],), (
        f"场分布形状不匹配: {field.shape} vs ({result['grid_info']['nx']},)"
    )
    assert np.all(np.isfinite(field)), "场分布含 NaN/Inf"
    assert np.all(np.isfinite(np.abs(field))), "|E| 含 NaN/Inf"
    # 场不应全为零
    assert np.max(np.abs(field)) > 0, "场分布全零"


def test_invalid_params():
    """非法参数应 raise（R03 禁止 fall-back）。"""
    with pytest.raises(ValueError):
        solve_bpm(width_um=0.0)
    with pytest.raises(ValueError):
        solve_bpm(length_um=0.0)
    with pytest.raises(ValueError):
        solve_bpm(wavelength_um=0.0)
    with pytest.raises(ValueError):
        solve_bpm(dz_um=0.0)
    with pytest.raises(ValueError):
        solve_bpm(dx_um=0.0)
    with pytest.raises(ValueError):
        solve_bpm(pad_um=0.0)
    # dx >= width
    with pytest.raises(ValueError):
        solve_bpm(width_um=0.5, dx_um=1.0)


def test_bpm_version():
    """子模块版本号 5.0.0（7 子模块统一）。"""
    assert polaris_bpm.__version__ == "5.0.0"


def test_transmission_loss_regression():
    """传输率回归测试（R05 Bug 必须修复）。

    复现 BUG: 修复前 transmission_db ≡ 0.0 dB（CN 严格功率守恒 +
    Dirichlet 反射辐射模）。修复后（split-step Soref + CAP）必须为合理负值。

    验证场景: 20μm 直波导（任务要求参数）
    - transmission_db < -0.0001（必须有明显损耗，不为 0）
    - transmission_db > -1.0（20μm 直波导损耗不应超 1 dB）
    - p_final < p_initial（功率单调递减）
    - transmission_db 与 Soref 解析值 0.006 dB 同量级或略大（含 CAP 辐射吸收）
    """
    result = solve_bpm(
        width_um=0.5, length_um=20.0, wavelength_um=1.55,
        n_core=3.476, n_clad=1.444,
        dz_um=0.5, dx_um=0.02, pad_um=1.0,
    )
    tdb = result["transmission_db"]
    t = result["transmission"]
    # 必须有损耗（不为 0）
    assert tdb < -0.0001, (
        f"transmission_db={tdb} 不应为 0（CN 守恒 BUG 未修复）"
    )
    # 20μm 直波导损耗合理上界（Soref 0.006 + CAP 辐射 < 1 dB）
    assert tdb > -1.0, (
        f"transmission_db={tdb} 衰减过大（>1dB 不合理）"
    )
    # 功率单调递减
    assert result["p_final"] < result["p_initial"], (
        f"p_final={result['p_final']} 应 < p_initial={result['p_initial']}"
    )
    # 传输率与 dB 一致性
    assert abs(t - 10.0 ** (tdb / 10.0)) < 1e-9, (
        f"transmission={t} 与 transmission_db={tdb} 不一致"
    )


def test_loss_profile():
    """损耗分布 α(x) 物理正确性。

    - 芯区: α = loss_db_per_cm · ln(10)/10 / 1e4 (μm⁻¹)
    - pad 外侧 CAP_FRACTION: 平方渐变，边界处 = CAP_STRENGTH，内侧 = 0
    - 非芯区非CAP: α = 0
    """
    nx, core_x0, core_x1, pad_pts = 200, 80, 105, 80
    alpha = build_loss_profile(nx, core_x0, core_x1, pad_pts)
    assert alpha.shape == (nx,)
    assert np.all(alpha >= 0), "α 须非负"

    # 芯区中部 Soref 损耗（远离 CAP）
    alpha_core_expected = LOSS_DB_PER_CM_SI * np.log(10.0) / 10.0 / 1e4
    mid_core = (core_x0 + core_x1) // 2
    assert abs(alpha[mid_core] - alpha_core_expected) < 1e-12, (
        f"芯区 α={alpha[mid_core]} 期望 {alpha_core_expected}"
    )

    # CAP 区域: 边界处 = CAP_STRENGTH，向内单调递减
    cap_pts = int(round(pad_pts * CAP_FRACTION))
    assert abs(alpha[0] - CAP_STRENGTH) < 1e-9, (
        f"左边界 α={alpha[0]} 期望 {CAP_STRENGTH}"
    )
    assert abs(alpha[-1] - CAP_STRENGTH) < 1e-9, (
        f"右边界 α={alpha[-1]} 期望 {CAP_STRENGTH}"
    )
    # CAP 边界附近应大于内侧（平方渐变单调递减向内）
    assert alpha[1] > alpha[cap_pts - 1], "CAP 应单调递减向内"
    # CAP 之外、芯区之外的纯包层区域 α=0
    pure_clad = cap_pts + 5  # CAP 之外 5 点
    if pure_clad < core_x0:
        assert alpha[pure_clad] == 0.0, (
            f"纯包层 α={alpha[pure_clad]} 应为 0"
        )

    # 非法参数 raise（R03）
    with pytest.raises(ValueError):
        build_loss_profile(200, 50, 40, 80)  # core_x0 > core_x1
    with pytest.raises(ValueError):
        build_loss_profile(200, 80, 105, 80, cap_fraction=1.5)
