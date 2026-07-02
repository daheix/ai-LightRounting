"""polaris-fdfd 子模块测试（R13 强制自测）。

测试覆盖（≥2 个 pytest，任务要求）:
- test_fdfd_waveguide: FDFD 求解场分布有限且非零，传输率为正
- test_fdfd_field_2d_shape: 场分布形状匹配网格
- test_invalid_params: 非法参数 raise（R03 禁止 fall-back）

来源（R02 学术诚信）:
- pytest 文档 https://docs.pytest.org/
- Taflove & Hagness 2005 "Computational Electrodynamics"
- Shin & Fan 2014 Opt. Express
  https://opg.optica.org/oe/abstract.cfm?uri=oe-22-5-5230
- scipy.sparse.linalg.spsolve
  https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.spsolve.html
- Lumerical FDFD https://optics.ansys.com/hc/en-us/articles/360034902393
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

import polaris_fdfd  # noqa: E402
from polaris_fdfd import solve_fdfd  # noqa: E402


def test_fdfd_waveguide():
    """FDFD 波导求解: 场分布有限且非零，传输率为正。

    高斯源激发波导，FDFD 求解稳态场分布。
    """
    result = solve_fdfd(
        width_um=0.5, length_um=8.0, wavelength_um=1.55,
        n_core=3.476, n_clad=1.444,
        dx_um=0.1, pad_um=1.0,
    )
    # 传输率为有限正数
    t = result["transmission"]
    assert math.isfinite(t), f"transmission 必须有限，得到 {t}"
    assert t > 0, f"transmission 应 > 0，得到 {t}"
    # 传输率 dB 为有限数
    assert math.isfinite(result["transmission_db"]), (
        f"transmission_db 必须有限，得到 {result['transmission_db']}"
    )
    # 元数据
    assert result["n_grid"] > 0
    assert result["wavelength_um"] == 1.55
    assert result["grid_info"]["nx"] > 0
    assert result["grid_info"]["nz"] > 0
    # 功率值合理
    assert result["p_source"] > 0
    assert result["p_output"] >= 0


def test_fdfd_field_2d_shape():
    """场分布形状匹配网格，且无 NaN。"""
    result = solve_fdfd(
        width_um=0.5, length_um=6.0, wavelength_um=1.55,
        n_core=3.476, n_clad=1.444,
        dx_um=0.1, pad_um=1.0,
    )
    field = np.array(result["field_2d"], dtype=complex)
    nx = result["grid_info"]["nx"]
    nz = result["grid_info"]["nz"]
    assert field.shape == (nx, nz), (
        f"场分布形状 {field.shape} 应为 ({nx}, {nz})"
    )
    assert np.all(np.isfinite(field)), "场分布含 NaN/Inf"
    # 场不应全为零（源激发）
    assert np.max(np.abs(field)) > 0, "场分布全零"


def test_invalid_params():
    """非法参数应 raise（R03 禁止 fall-back）。"""
    with pytest.raises(ValueError):
        solve_fdfd(width_um=0.0)
    with pytest.raises(ValueError):
        solve_fdfd(length_um=0.0)
    with pytest.raises(ValueError):
        solve_fdfd(wavelength_um=0.0)
    with pytest.raises(ValueError):
        solve_fdfd(dx_um=0.0)
    with pytest.raises(ValueError):
        solve_fdfd(pad_um=0.0)
    # n_core <= n_clad
    with pytest.raises(ValueError):
        solve_fdfd(n_core=1.0, n_clad=2.0)
    # dx >= width
    with pytest.raises(ValueError):
        solve_fdfd(width_um=0.5, dx_um=1.0)


def test_fdfd_version():
    """子模块版本号 5.0.0（7 子模块统一）。"""
    assert polaris_fdfd.__version__ == "5.0.0"
