"""polaris-bpm 子模块测试（R13 强制自测）。

测试覆盖（≥2 个 pytest，任务要求）:
- test_bpm_straight_waveguide: 直波导 BPM 传输率合理（> 0.5，功率守恒）
- test_bpm_field_finite: 末态场分布有限（无 NaN）
- test_invalid_params: 非法参数 raise（R03 禁止 fall-back）

来源（R02 学术诚信）:
- pytest 文档 https://docs.pytest.org/
- Feit & Fleck 1978 Appl. Opt.（BPM 理论）
  https://opg.optica.org/ao/abstract.cfm?uri=ao-17-24-3990
- Crank & Nicolson 1947（隐式差分格式）
- Chung & Dagli 1990 IEEE JQE（ADI 扩展）
  https://ieeexplore.ieee.org/document/59635
- scipy.linalg.solve_banded
  https://docs.scipy.org/doc/scipy/reference/generated/scipy.linalg.solve_banded.html
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
from polaris_bpm import solve_bpm  # noqa: E402


def test_bpm_straight_waveguide():
    """直波导 BPM: 传输率 > 0.5（功率守恒，BPM 无源无损耗）。

    高斯光束在直波导中传播，BPM 无源（抛物近似）应保持功率。
    由于初始高斯不完全匹配基模，部分功率辐射到包层（被边界吸收），
    但主体功率应保留（> 0.5）。
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
    # 直波导无损耗，传输率应较高（高斯耦合到基模 + 辐射模）
    # 实际 BPM 由于高斯不完全匹配基模，部分功率辐射，但主体应保留
    assert t > 0.5, (
        f"直波导 BPM 传输率应 > 0.5（功率守恒），得到 {t}"
    )
    # 元数据
    assert result["n_steps"] > 0
    assert result["wavelength_um"] == 1.55
    assert result["grid_info"]["nx"] > 0
    assert result["grid_info"]["nz"] > 0
    # 功率值合理
    assert result["p_initial"] > 0
    assert result["p_final"] > 0


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
