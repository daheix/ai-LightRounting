"""polaris-fdfd 子模块测试（R13 强制自测）。

测试覆盖（≥2 个 pytest，任务要求）:
- test_fdfd_waveguide: FDFD 求解场分布有限且非零，传输率为正
- test_fdfd_field_2d_shape: 场分布形状匹配网格
- test_invalid_params: 非法参数 raise（R03 禁止 fall-back）
- test_grid_size_regression: R05 回归测试（网格尺寸 BUG + PML/Poynting 修复）

来源（R02 学术诚信）:
- pytest 文档 https://docs.pytest.org/
- Taflove & Hagness 2005 "Computational Electrodynamics" §5.8 PML
- Shin & Fan 2014 Opt. Express
  https://opg.optica.org/oe/abstract.cfm?uri=oe-22-5-5230
- Shin & Fan 2012 J. Comput. Phys. (SC-PML)
  https://doi.org/10.1016/j.jcp.2012.01.015
- Berenger 1994 J. Comput. Phys. (PML 原创)
  https://doi.org/10.1006/jcph.1994.1159
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


def test_grid_size_regression():
    """R05 回归测试：网格尺寸 BUG + PML/Poynting 修复。

    BUG 现象（修复前）:
      solve_fdfd(width=0.5, length=10.0, dx=0.05, pad=1.0)
      → n_grid=10000 (100×100), transmission_db=-49.7 dB
      根因: 旧实现 int(round(W/dx)) 且按 N 重算步长，导致
      - 网格点数少 1，物理尺寸被压缩
      - length_um=10μm 方向波导被截断
      - Dirichlet 边界 + 实数系统 → 场纯实数 → Poynting 流=0
      - transmission 用 |E|²/|b|² 尺度不匹配

    修复后预期:
      - nx = int((0.5+2*1.0)/0.05)+1 = 51
      - nz = int(10.0/0.05)+1 = 201
      - n_grid = 51*201 = 10251 (>10000)
      - transmission_db ∈ (-20, 0)（10μm 直波导近无损）
      - 场有非零虚部（PML 复坐标拉伸生效）
      - p_source > 0（Poynting 流为正）
    """
    result = solve_fdfd(
        width_um=0.5, length_um=10.0, wavelength_um=1.55,
        n_core=3.476, n_clad=1.444,
        dx_um=0.05, pad_um=1.0,
    )
    # 1. 网格尺寸正确（BUG 核心：n_grid 必须 > 10000）
    assert result["n_grid"] > 10000, (
        f"n_grid={result['n_grid']} 网格仍然太小（BUG 未修复）"
    )
    gi = result["grid_info"]
    assert gi["nx"] == 51, f"nx 应为 51，得到 {gi['nx']}"
    assert gi["nz"] == 201, f"nz 应为 201，得到 {gi['nz']}"
    assert result["n_grid"] == 51 * 201, (
        f"n_grid 应为 10251，得到 {result['n_grid']}"
    )
    # 2. 传输率合理（BUG 时 -49.7 dB）
    t_db = result["transmission_db"]
    assert -20 < t_db < 0, (
        f"transmission_db={t_db} 不在合理范围 (-20, 0)"
    )
    t = result["transmission"]
    assert 0 < t < 1, f"transmission 应在 (0,1)，得到 {t}"
    # 3. Poynting 流为正（BUG 时场纯实数 → Poynting 流=0）
    assert result["p_source"] > 0, (
        f"p_source={result['p_source']} 须 > 0（Poynting 流）"
    )
    assert result["p_output"] > 0, (
        f"p_output={result['p_output']} 须 > 0（Poynting 流）"
    )
    # 4. 场有非零虚部（PML 复坐标拉伸生效，BUG 时场纯实数）
    field = np.array(result["field_2d"], dtype=complex)
    assert np.max(np.abs(field.imag)) > 0, (
        "场虚部全零，PML 复坐标拉伸未生效"
    )
    assert np.all(np.isfinite(field)), "场分布含 NaN/Inf"
    # 5. PML 元数据存在
    assert gi["pml_n"] >= 4, f"pml_n 须 >= 4，得到 {gi['pml_n']}"
    assert gi["sigma_max"] > 0, f"sigma_max 须 > 0，得到 {gi['sigma_max']}"
    # 6. 监视器位置正确（源在 PML 后，输出在输出端 PML 前）
    assert gi["source_z_idx"] == gi["pml_n"], (
        f"源应在 z=pml_n={gi['pml_n']}，得到 {gi['source_z_idx']}"
    )
    assert gi["output_z_idx"] == gi["nz"] - 1 - gi["pml_n"], (
        f"输出应在 z=nz-1-pml_n={gi['nz']-1-gi['pml_n']}，"
        f"得到 {gi['output_z_idx']}"
    )
    assert gi["input_z_idx"] > gi["source_z_idx"], (
        "输入监视器应在源之后"
    )
    assert gi["output_z_idx"] > gi["input_z_idx"], (
        "输出监视器应在输入监视器之后"
    )


def test_fdfd_version():
    """子模块版本号 5.0.0（7 子模块统一）。"""
    assert polaris_fdfd.__version__ == "5.0.0"
