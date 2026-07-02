"""polaris-fdtd 子模块测试（R13 强制自测）。

测试覆盖（≥2 个 pytest，任务要求）:
- test_waveguide_fdtd: waveguide T_fdtd 是有限数（无 NaN）
- test_mmi_fdtd: mmi 返回 split_ratio 在 [0, 1]

来源（R02 学术诚信）:
- pytest 文档 https://docs.pytest.org/
- Yee 1966 IEEE TAP https://doi.org/10.1109/TAP.1966.1138693
- Gedney 1996 IEEE TAP https://doi.org/10.1109/8.546249
- Taflove & Hagness 2005 "Computational Electrodynamics"
- Soref 1993 IEEE JQE https://ieeexplore.ieee.org/document/1148303
- Lumerical FDTD 求解器
  https://optics.ansys.com/hc/en-us/articles/360034914833
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pytest

# 让测试既能从已安装包导入，也能从源码树导入（CI/开发模式）
_SRC = str(Path(__file__).resolve().parents[1] / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import polaris_fdtd  # noqa: E402
from polaris_fdtd import (  # noqa: E402
    simulate_mmi_fdtd,
    simulate_waveguide_fdtd,
)


def test_waveguide_fdtd():
    """波导 FDTD: T_fdtd 是有限数（无 NaN）。

    使用较小网格 + 少步数以加速测试（JAX 编译后 ~10s）。
    """
    result = simulate_waveguide_fdtd(
        dx_um=0.1, n_steps=300, wavelength_um=1.55,
        nx=32, ny=16, nz=12, pml_layers=4,
    )
    # T_fdtd 必须是有限数
    assert math.isfinite(result["T_fdtd"]), (
        f"T_fdtd 必须有限，得到 {result['T_fdtd']}"
    )
    assert not math.isnan(result["T_fdtd"]), "T_fdtd 不能为 NaN"
    # T_fdtd 应非负（功率比值）
    assert result["T_fdtd"] >= 0, f"T_fdtd 应 >= 0，得到 {result['T_fdtd']}"
    # transmission_db 必须有限
    assert math.isfinite(result["transmission_db"]), (
        f"transmission_db 必须有限，得到 {result['transmission_db']}"
    )
    # 元数据
    assert result["n_steps"] == 300
    assert result["dx_um"] == 0.1
    assert result["pml_enabled"] is True
    assert result["fdtd_duration_s"] > 0


def test_mmi_fdtd():
    """MMI FDTD: split_ratio 在 [0, 1]。

    使用较小网格 + 少步数以加速测试。
    """
    result = simulate_mmi_fdtd(
        dx_um=0.1, n_steps=300, wavelength_um=1.55,
        nx=32, ny=16, nz=12, pml_layers=4,
    )
    # split_ratio 必须在 [0, 1]
    assert 0.0 <= result["split_ratio"] <= 1.0, (
        f"split_ratio 应在 [0, 1]，得到 {result['split_ratio']}"
    )
    # T_fdtd 必须有限
    assert math.isfinite(result["T_fdtd"]), (
        f"T_fdtd 必须有限，得到 {result['T_fdtd']}"
    )
    assert result["T_fdtd"] >= 0
    # 元数据
    assert result["n_steps"] == 300
    assert result["pml_enabled"] is True


def test_invalid_params():
    """非法参数应 raise（R03 禁止 fall-back）。"""
    with pytest.raises(ValueError):
        simulate_waveguide_fdtd(dx_um=0.0)
    with pytest.raises(ValueError):
        simulate_waveguide_fdtd(n_steps=0)
    with pytest.raises(ValueError):
        simulate_waveguide_fdtd(wavelength_um=0.0)
    with pytest.raises(ValueError):
        # pml_layers*2 >= min(nx,ny,nz)
        simulate_waveguide_fdtd(nx=4, ny=4, nz=4, pml_layers=4)


def test_fdtd_version():
    """子模块版本号 5.0.0（7 子模块统一）。"""
    assert polaris_fdtd.__version__ == "5.0.0"
