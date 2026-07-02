"""polaris-eme 子模块测试（R13 强制自测）。

测试覆盖（≥2 个 pytest，任务要求）:
- test_eme_straight_waveguide: 直波导（单段）传输率 |T| ≈ 1（无反射）
- test_eme_taper: 锥形段（宽→窄）传输率有限且 < 1
- test_invalid_params: 非法参数 raise（R03 禁止 fall-back）

来源（R02 学术诚信）:
- pytest 文档 https://docs.pytest.org/
- Smit & van Dam 1996 IEEE/OSA JLT
  https://opg.optica.org/jlt/abstract.cfm?uri=jlt-14-7-1746
- Bienstman 2001 PhD（Redheffer 星积）
  https://www.photonics.intec.ugent.be/publications/PhD_Bienstman.pdf
- Lumerical EME https://optics.ansys.com/hc/en-us/articles/360034902433
- scipy.sparse.linalg.eigsh
  https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

# 让测试既能从已安装包导入，也能从源码树导入
_SRC = str(Path(__file__).resolve().parents[1] / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import polaris_eme  # noqa: E402
from polaris_eme import solve_eme  # noqa: E402


def test_eme_straight_waveguide():
    """直波导（单段）: 传输率 |T| ≈ 1（无反射，无界面损耗）。

    单段均匀波导无界面，仅有相位传播 exp(j·β·L)，故 |T| = 1。
    """
    result = solve_eme(
        sections=[
            {"width_um": 0.5, "length_um": 10.0,
             "n_core": 3.476, "n_clad": 1.444},
        ],
        wavelength_um=1.55,
        n_modes_per_section=2,
        dx_um=0.01,
        pad_um=1.0,
    )
    # 单段: |T| = 1（仅有相位）
    t_abs = abs(result["transmission"])
    assert math.isclose(t_abs, 1.0, rel_tol=1e-9), (
        f"单段直波导 |T| 应 = 1，得到 {t_abs}"
    )
    # 反射 = 0（无界面）
    r_abs = abs(result["reflection"])
    assert r_abs < 1e-10, f"单段反射应 ≈ 0，得到 {r_abs}"
    # 元数据
    assert result["n_sections"] == 1
    assert result["wavelength_um"] == 1.55
    # 段信息
    assert len(result["sections_info"]) == 1
    s0 = result["sections_info"][0]
    assert s0["width_um"] == 0.5
    assert s0["length_um"] == 10.0
    assert s0["neff"] > 1.444  # neff > n_clad（导模）
    assert s0["neff"] < 3.476  # neff < n_core


def test_eme_taper():
    """锥形（宽→窄）: 传输率有限且 < 1（有界面反射）。

    两段宽度不同的波导相连，模式失配 → |T| < 1, |R| > 0。
    """
    result = solve_eme(
        sections=[
            {"width_um": 1.0, "length_um": 5.0,
             "n_core": 3.476, "n_clad": 1.444},
            {"width_um": 0.5, "length_um": 5.0,
             "n_core": 3.476, "n_clad": 1.444},
        ],
        wavelength_um=1.55,
        n_modes_per_section=2,
        dx_um=0.01,
        pad_um=1.0,
    )
    # 两段锥形: 0 < |T| < 1
    t_abs = abs(result["transmission"])
    assert 0.0 < t_abs < 1.0, (
        f"锥形 |T| 应在 (0, 1)，得到 {t_abs}"
    )
    # 反射 > 0（有模式失配）
    r_abs = abs(result["reflection"])
    assert r_abs > 0, f"锥形反射应 > 0，得到 {r_abs}"
    # 功率守恒: |T|^2 + |R|^2 ≈ 1（无损耗）
    power = t_abs ** 2 + r_abs ** 2
    assert math.isclose(power, 1.0, rel_tol=1e-6), (
        f"功率守恒 |T|²+|R|² 应 ≈ 1，得到 {power}"
    )
    # 元数据
    assert result["n_sections"] == 2
    assert len(result["sections_info"]) == 2
    # 段 0 宽度 > 段 1 宽度（锥形）
    assert result["sections_info"][0]["width_um"] > result["sections_info"][1]["width_um"]
    # 传输率 dB 应为负（损耗）
    assert result["transmission_db"] < 0, (
        f"锥形 transmission_db 应 < 0，得到 {result['transmission_db']}"
    )


def test_eme_uniform_multisection():
    """多段相同波导: 传输率 |T| ≈ 1（无界面失配）。

    多段相同截面波导相连，模式完全匹配 → |T| = 1。
    """
    result = solve_eme(
        sections=[
            {"width_um": 0.5, "length_um": 5.0,
             "n_core": 3.476, "n_clad": 1.444},
            {"width_um": 0.5, "length_um": 5.0,
             "n_core": 3.476, "n_clad": 1.444},
            {"width_um": 0.5, "length_um": 5.0,
             "n_core": 3.476, "n_clad": 1.444},
        ],
        wavelength_um=1.55,
        n_modes_per_section=2,
        dx_um=0.01,
        pad_um=1.0,
    )
    # 三段相同波导: |T| = 1（模式完全匹配，无反射）
    t_abs = abs(result["transmission"])
    assert math.isclose(t_abs, 1.0, rel_tol=1e-6), (
        f"多段相同波导 |T| 应 = 1，得到 {t_abs}"
    )
    assert result["n_sections"] == 3


def test_invalid_params():
    """非法参数应 raise（R03 禁止 fall-back）。"""
    # 空段列表
    with pytest.raises(ValueError):
        solve_eme(sections=[])
    # 负波长
    with pytest.raises(ValueError):
        solve_eme(
            sections=[{"width_um": 0.5, "length_um": 5.0,
                       "n_core": 3.476, "n_clad": 1.444}],
            wavelength_um=0.0,
        )
    # 段缺少字段
    with pytest.raises(ValueError):
        solve_eme(sections=[{"width_um": 0.5}])
    # 负长度
    with pytest.raises(ValueError):
        solve_eme(
            sections=[{"width_um": 0.5, "length_um": -1.0,
                       "n_core": 3.476, "n_clad": 1.444}],
        )
    # n_modes_per_section < 1
    with pytest.raises(ValueError):
        solve_eme(
            sections=[{"width_um": 0.5, "length_um": 5.0,
                       "n_core": 3.476, "n_clad": 1.444}],
            n_modes_per_section=0,
        )


def test_eme_version():
    """子模块版本号 5.0.0（7 子模块统一）。"""
    assert polaris_eme.__version__ == "5.0.0"
