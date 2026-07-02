"""polaris-fde 子模块测试（R13 强制自测）。

测试覆盖（≥2 个 pytest，任务要求）:
- test_fde_si_strip: Si strip 500nm×220nm neff ∈ (2.0, 3.0)
- test_fde_multimode: 宽波导 1.5μm×220nm 多模数 >= 2
- test_invalid_params: 非法参数 raise（R03 禁止 fall-back）

来源（R02 学术诚信）:
- pytest 文档 https://docs.pytest.org/
- Smit & van Dam 1996 IEEE/OSA JLT
  https://opg.optica.org/jlt/abstract.cfm?uri=jlt-14-7-1746
- Silvester & Ferrari 1996 Cambridge（FD 本征模求解）
- Soref 1993 IEEE JQE https://ieeexplore.ieee.org/document/1148303
- scipy.sparse.linalg.eigsh
  https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html
- Lumerical MODE FDE https://optics.ansys.com/hc/en-us/articles/360034902413
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

# 让测试既能从已安装包导入，也能从源码树导入（CI/开发模式）
_SRC = str(Path(__file__).resolve().parents[1] / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import polaris_fde  # noqa: E402
from polaris_fde import solve_modes  # noqa: E402


def test_fde_si_strip():
    """Si strip 500nm×220nm @ 1550nm: neff ∈ (2.0, 3.0)。

    典型 SOI 条形波导 TE0 模: neff ≈ 2.4-2.5（Soref 1993 + Lumerical MODE 文档）。
    """
    result = solve_modes(
        width_um=0.5, height_um=0.22, wavelength_um=1.55,
        n_core=3.476, n_clad=1.444, n_modes=4,
        dx_um=0.025, pad_um=1.0,
    )
    # 至少有 1 个导模
    assert result["n_modes"] >= 1, f"至少 1 个导模，得到 {result['n_modes']}"
    # 基模 neff ∈ (2.0, 3.0)
    neff0 = result["modes"][0]["neff"]
    assert 2.0 < neff0 < 3.0, (
        f"Si strip 500×220nm 基模 neff 应在 (2.0, 3.0)，得到 {neff0}"
    )
    # neff 应在 (n_clad, n_core) = (1.444, 3.476) 之间
    for mode in result["modes"]:
        assert 1.444 < mode["neff"] < 3.476, (
            f"neff {mode['neff']} 应在 (1.444, 3.476) 之间"
        )
        # 模场分布非空且有限
        field = mode["field_2d"]
        assert len(field) > 0, "模场分布不应为空"
        # neff 必须是有限数
        assert math.isfinite(mode["neff"]), f"neff 必须有限，得到 {mode['neff']}"
    # 元数据
    assert result["wavelength_um"] == 1.55
    assert "grid_info" in result
    assert result["grid_info"]["nx"] > 0
    assert result["grid_info"]["ny"] > 0
    # 模式按 neff 降序排列
    for i in range(1, len(result["modes"])):
        assert result["modes"][i - 1]["neff"] >= result["modes"][i]["neff"], (
            "模式应按 neff 降序排列"
        )


def test_fde_multimode():
    """宽波导 1.5μm×220nm: 多模数 >= 2。

    单模条件（SOI @ 1550nm）: W < ~450nm。1.5μm 宽波导应支持多个 TE 模。
    来源: Soref 1993 IEEE JQE 单模条件。
    """
    result = solve_modes(
        width_um=1.5, height_um=0.22, wavelength_um=1.55,
        n_core=3.476, n_clad=1.444, n_modes=6,
        dx_um=0.025, pad_um=1.0,
    )
    # 宽波导至少 2 个导模
    assert result["n_modes"] >= 2, (
        f"1.5μm 宽波导应至少 2 个导模，得到 {result['n_modes']}"
    )
    # 基模 neff 仍应在 (2.0, 3.0)
    neff0 = result["modes"][0]["neff"]
    assert 2.0 < neff0 < 3.0, f"基模 neff 应 (2.0, 3.0)，得到 {neff0}"
    # 高阶模 neff < 基模 neff
    if result["n_modes"] >= 2:
        assert result["modes"][1]["neff"] < result["modes"][0]["neff"], (
            "高阶模 neff 应小于基模"
        )


def test_invalid_params():
    """非法参数应 raise（R03 禁止 fall-back）。"""
    # 负宽度
    with pytest.raises(ValueError):
        solve_modes(width_um=-0.5)
    # 负波长
    with pytest.raises(ValueError):
        solve_modes(wavelength_um=0.0)
    # n_core <= n_clad（无导模）
    with pytest.raises(ValueError):
        solve_modes(n_core=1.0, n_clad=2.0)
    # n_modes < 1
    with pytest.raises(ValueError):
        solve_modes(n_modes=0)
    # dx_um <= 0
    with pytest.raises(ValueError):
        solve_modes(dx_um=0.0)
    # dx_um >= width_um（芯区无网格点）
    with pytest.raises(ValueError):
        solve_modes(width_um=0.5, dx_um=1.0)
    # pad_um <= 0
    with pytest.raises(ValueError):
        solve_modes(pad_um=0.0)


def test_fde_version():
    """子模块版本号 5.0.0（7 子模块统一）。"""
    assert polaris_fde.__version__ == "5.0.0"
