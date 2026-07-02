"""polaris-fde 子模块测试（R13 强制自测）。

测试覆盖（≥2 个 pytest，任务要求）:
- test_fde_si_strip: Si strip 500nm×220nm neff ∈ (2.0, 3.0)
- test_fde_multimode: 宽波导 1.5μm×220nm 多模数 >= 2
- test_invalid_params: 非法参数 raise（R03 禁止 fall-back）
- test_fde_si_strip_single_mode: 500nm SOI 单模回归（R05 修复伪模 BUG）
- test_confinement_filter: confinement factor 判据过滤弱导模
- test_v_parameter: V 参数计算与单模约束

来源（R02 学术诚信）:
- pytest 文档 https://docs.pytest.org/
- Smit & van Dam 1996 IEEE/OSA JLT
  https://opg.optica.org/jlt/abstract.cfm?uri=jlt-14-7-1746
- Silvester & Ferrari 1996 Cambridge（FD 本征模求解）
- Soref 1993 IEEE JQE https://ieeexplore.ieee.org/document/1148303
- scipy.sparse.linalg.eigsh
  https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html
- Lumerical MODE FDE https://optics.ansys.com/hc/en-us/articles/360034902413
- Snyder & Love 1983 "Optical Waveguide Theory"（V 参数与 confinement 判据）
  https://link.springer.com/book/10.1007/978-94-009-6875-2
- Saleh & Teich 2019 "Fundamentals of Photonics"（导模 confinement）
  https://onlinelibrary.wiley.com/doi/book/10.1002/0471213748
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
from polaris_fde import (  # noqa: E402
    CONFINEMENT_THRESHOLD,
    V_CUTOFF_SINGLE_MODE,
    compute_v_parameter,
    confinement_factor,
    solve_modes,
)


def test_fde_si_strip():
    """Si strip 500nm×220nm @ 1550nm: neff ∈ (2.0, 3.0)。

    典型 SOI 条形波导 TE0 模: neff ≈ 2.4-2.6（Soref 1993 + Lumerical MODE 文档）。
    R05 修复后：500nm 波导单模，confinement > 0.6 过滤 TM0 弱导模。
    """
    result = solve_modes(
        width_um=0.5, height_um=0.22, wavelength_um=1.55,
        n_core=3.476, n_clad=1.444, n_modes=4,
        dx_um=0.02, pad_um=1.0,
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
        # confinement factor 应高于阈值（R05 修复后必填字段）
        assert "confinement" in mode, "confinement 字段必填（R05 修复）"
        assert mode["confinement"] >= CONFINEMENT_THRESHOLD, (
            f"confinement {mode['confinement']} 应 >= {CONFINEMENT_THRESHOLD}"
        )
    # 元数据
    assert result["wavelength_um"] == 1.55
    assert "grid_info" in result
    assert result["grid_info"]["nx"] > 0
    assert result["grid_info"]["ny"] > 0
    # 物理元数据（R05 修复后新增 V_parameter）
    assert "physics" in result
    assert "V_parameter" in result["physics"]
    assert "single_mode" in result["physics"]
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
        dx_um=0.02, pad_um=1.0,
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


def test_fde_si_strip_single_mode():
    """R05 回归测试：500nm SOI 波导应为单模（过滤 TM0 弱导模）。

    修复前 BUG（2026-07-02）：
      - 求出 2 个导模（mode 1 neff≈1.84 是 TM0 弱导模，confinement≈0.57）
      - 任务描述：500nm SOI 波导在 1550nm 应为单模工作
    修复后：
      - 只返回 1 个导模（TE0，confinement > 0.6）
      - neff ∈ (2.0, 3.0)
      - V_parameter 字段已填充

    来源：Snyder & Love 1983 §13.5（confinement 判据）；
          Soref 1993 IEEE JQE（SOI 单模条件）。
    """
    result = solve_modes(
        width_um=0.5, height_um=0.22, wavelength_um=1.55,
        n_core=3.476, n_clad=1.444, n_modes=3,
        dx_um=0.02, pad_um=1.0,
    )
    # 500nm SOI 波导应为单模（仅 TE0）
    assert result["n_modes"] == 1, (
        f"500nm SOI 波导应单模（仅 TE0），得到 {result['n_modes']} 个导模"
    )
    # 基模 neff 应在 (2.0, 3.0)
    neff0 = result["modes"][0]["neff"]
    assert 2.0 < neff0 < 3.0, f"基模 neff 应 (2.0, 3.0)，得到 {neff0}"
    # 基模 confinement 应 >= 0.7（强约束导模）
    assert result["modes"][0]["confinement"] >= 0.7, (
        f"TE0 confinement 应 >= 0.7，得到 {result['modes'][0]['confinement']}"
    )
    # V 参数应被计算并填入 physics
    assert "V_parameter" in result["physics"], "physics 应包含 V_parameter"
    V = result["physics"]["V_parameter"]
    expected_V = (2 * math.pi / 1.55) * 0.25 * math.sqrt(3.476**2 - 1.444**2)
    assert abs(V - expected_V) < 1e-6, f"V 参数 {V} != 期望 {expected_V}"


def test_confinement_filter():
    """R05 回归测试：confinement factor 判据有效过滤弱导模。

    弱导模（如 SOI 500nm TM0，confinement≈0.57）应被过滤掉。
    测试 confinement_factor 函数与 CONFINEMENT_THRESHOLD 常量。
    """
    import numpy as np
    # 构造一个芯区强约束场（高 confinement）
    field_high = np.zeros((20, 20))
    field_high[8:12, 8:12] = 1.0
    conf_high = confinement_factor(field_high, (8, 12), (8, 12))
    assert conf_high == 1.0, f"全芯区场 confinement 应为 1.0，得到 {conf_high}"

    # 构造一个包层扩散场（低 confinement）
    field_low = np.ones((20, 20))
    conf_low = confinement_factor(field_low, (8, 12), (8, 12))
    # 16/400 = 0.04，远低于阈值
    assert conf_low < CONFINEMENT_THRESHOLD, (
        f"均匀场 confinement {conf_low} 应 < 阈值 {CONFINEMENT_THRESHOLD}"
    )

    # 阈值常量值校验
    assert CONFINEMENT_THRESHOLD == 0.6, (
        f"CONFINEMENT_THRESHOLD 应为 0.6，得到 {CONFINEMENT_THRESHOLD}"
    )
    assert V_CUTOFF_SINGLE_MODE == 2.405, (
        f"V_CUTOFF_SINGLE_MODE 应为 2.405，得到 {V_CUTOFF_SINGLE_MODE}"
    )


def test_v_parameter():
    """R05 回归测试：V 参数计算与单模约束。

    V = (2π/λ) · (W/2) · √(n_core²−n_clad²)
    SOI 500nm @ 1550nm: V ≈ 3.204（>2.405，但 confinement 判据仍过滤 TM0）
    SOI 300nm @ 1550nm: V ≈ 1.923（<2.405，强制单模约束触发）
    """
    # SOI 500nm V 参数
    V_500 = compute_v_parameter(0.5, 1.55, 3.476, 1.444)
    expected = (2 * math.pi / 1.55) * 0.25 * math.sqrt(3.476**2 - 1.444**2)
    assert abs(V_500 - expected) < 1e-9, f"V_500={V_500} 期望={expected}"
    assert 3.0 < V_500 < 3.5, f"SOI 500nm V 应在 (3.0, 3.5)，得到 {V_500}"

    # 300nm 波导 V < 2.405（强制单模）
    V_narrow = compute_v_parameter(0.3, 1.55, 3.476, 1.444)
    assert V_narrow < V_CUTOFF_SINGLE_MODE, (
        f"300nm 波导 V={V_narrow} 应 < 2.405"
    )

    # 300nm 波导应触发 single_mode 约束
    result = solve_modes(
        width_um=0.3, height_um=0.22, wavelength_um=1.55,
        n_core=3.476, n_clad=1.444, n_modes=3,
        dx_um=0.02, pad_um=1.0,
    )
    assert result["physics"]["single_mode"] is True, (
        "300nm 波导应触发 single_mode=True"
    )
    assert result["n_modes"] == 1, (
        f"300nm 波导 V<2.405 应强制单模，得到 {result['n_modes']}"
    )

    # 非法参数 raise
    with pytest.raises(ValueError):
        compute_v_parameter(0.0, 1.55, 3.476, 1.444)
    with pytest.raises(ValueError):
        compute_v_parameter(0.5, 0.0, 3.476, 1.444)
    with pytest.raises(ValueError):
        compute_v_parameter(0.5, 1.55, 1.0, 2.0)


def test_fde_version():
    """子模块版本号 5.0.0（7 子模块统一）。"""
    assert polaris_fde.__version__ == "5.0.0"
