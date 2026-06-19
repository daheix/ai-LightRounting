"""PoLaRIS S 参数模型与 simphony siepic 真实器件对比测试（步骤3）。

验证 PoLaRIS 复刻的 S 参数模型（src/polaris/sim/models.py）与
simphony siepic 库（真实 SiEPIC EBeam PDK 器件模型）的输出一致性。

simphony 为可选依赖（规则 5.3）：缺失时测试用
``pytest.importorskip("simphony")`` 跳过。

来源:
- simphony (MIT): https://simphonyphotonics.readthedocs.io/en/stable/libs/siepic.html
- SiEPIC EBeam PDK (MIT, UBC): https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- PoLaRIS 复刻模型: src/polaris/sim/models.py
"""

from __future__ import annotations

import numpy as np
import pytest

simphony = pytest.importorskip("simphony")
from polaris.sim.models import (  # noqa: E402
    grating_coupler_s,
    waveguide_s,
    y_branch_s,
)
from simphony.libraries import siepic  # noqa: E402


def test_waveguide_s_param_consistency():
    """PoLaRIS 波导 S 参数应与 simphony siepic 一致（相位+损耗）。

    两者都使用 ``S = exp(-alpha*L/2) * exp(1j*2*pi*neff*L/wl)`` 公式。
    """
    wl = np.array([1.55])
    length = 10.0
    neff = 2.4  # SiEPIC 默认 neff
    loss_db_cm = 3.0  # SOI 3 dB/cm

    # simphony siepic 波导
    s_simphony = siepic.waveguide(wl=wl, length=length, loss=loss_db_cm)
    simphony_s = s_simphony[("o1", "o0")][0]

    # PoLaRIS 波导（端口名 in/out，与 simphony 的 o0/o1 不同）
    s_polaris = waveguide_s(wl=wl, length=length, neff=neff, loss_db_cm=loss_db_cm)
    polaris_s = s_polaris[("out", "in")][0]

    # 功率传输应一致（损耗相同）
    simphony_power = abs(simphony_s) ** 2
    polaris_power = abs(polaris_s) ** 2
    np.testing.assert_almost_equal(polaris_power, simphony_power, decimal=3)

    # 相位应接近（neff 可能略有差异，但量级一致）
    simphony_phase = np.angle(simphony_s)
    polaris_phase = np.angle(polaris_s)
    # 相位差应在 2π 内（模 2π 比较）
    phase_diff = abs((polaris_phase - simphony_phase + np.pi) % (2 * np.pi) - np.pi)
    assert phase_diff < 0.5, (
        f"波导相位差异过大: simphony={simphony_phase:.4f}, "
        f"polaris={polaris_phase:.4f}, diff={phase_diff:.4f}"
    )


def test_y_branch_power_splitting():
    """PoLaRIS Y 分支应实现 3dB 功率分束（与 simphony siepic 一致）。

    真实 SiEPIC Y 分支：每个输出端口获得约 50% 功率（-3dB）。
    """
    wl = np.array([1.55])

    # simphony siepic Y 分支
    s_simphony = siepic.y_branch(wl=wl)
    simphony_s01 = abs(s_simphony[("o1", "o0")][0]) ** 2
    simphony_s02 = abs(s_simphony[("o2", "o0")][0]) ** 2

    # PoLaRIS Y 分支（插损 0.3dB）
    s_polaris = y_branch_s(wl=wl, insertion_loss_db=0.3)
    polaris_s01 = abs(s_polaris[("port_2", "port_1")][0]) ** 2
    polaris_s02 = abs(s_polaris[("port_3", "port_1")][0]) ** 2

    # 两者都应接近 0.5（-3dB 分束）
    np.testing.assert_almost_equal(simphony_s01, 0.5, decimal=2)
    np.testing.assert_almost_equal(simphony_s02, 0.5, decimal=2)
    # PoLaRIS 含 0.3dB 插损，功率略低于 0.5
    assert 0.45 < polaris_s01 < 0.50, f"PoLaRIS Y 分支功率 {polaris_s01} 应在 0.45-0.50"
    assert 0.45 < polaris_s02 < 0.50, f"PoLaRIS Y 分支功率 {polaris_s02} 应在 0.45-0.50"
    # 两个输出端口功率应相等（对称性）
    np.testing.assert_almost_equal(polaris_s01, polaris_s02, decimal=4)


def test_grating_coupler_peak_response():
    """PoLaRIS 光栅耦合器在峰值波长应有合理插损（与 simphony 量级一致）。

    真实 SiEPIC GC：峰值耦合损耗约 3-5 dB（simphony 实测 ~1.9dB）。
    """
    wl = np.array([1.55])

    # simphony siepic GC
    s_simphony = siepic.grating_coupler(wl=wl)
    simphony_power = abs(s_simphony[("o1", "o0")][0]) ** 2
    simphony_loss_db = -10 * np.log10(simphony_power)

    # PoLaRIS GC（峰值损耗 1.9dB，对齐三星 300mm 平台）
    s_polaris = grating_coupler_s(wl=wl, peak_wl=1.55, insertion_loss_db=1.9)
    polaris_power = abs(s_polaris[("waveguide", "fiber")][0]) ** 2
    polaris_loss_db = -10 * np.log10(polaris_power)

    # 两者损耗应在合理范围（1-5 dB）
    assert 1.0 < simphony_loss_db < 5.0, f"simphony GC 损耗 {simphony_loss_db} 应在 1-5 dB"
    assert 1.0 < polaris_loss_db < 5.0, f"PoLaRIS GC 损耗 {polaris_loss_db} 应在 1-5 dB"


def test_waveguide_loss_scaling():
    """PoLaRIS 波导损耗应随长度线性增长（与 simphony 一致）。

    损耗公式: loss_db = loss_db_cm * length_cm
    """
    wl = np.array([1.55])
    loss_db_cm = 3.0

    # 10μm 和 20μm 波导
    s10 = waveguide_s(wl=wl, length=10.0, loss_db_cm=loss_db_cm)
    s20 = waveguide_s(wl=wl, length=20.0, loss_db_cm=loss_db_cm)

    p10 = abs(s10[("out", "in")][0]) ** 2
    p20 = abs(s20[("out", "in")][0]) ** 2

    # 20μm 应比 10μm 多损耗 3dB/cm * (20-10)μm = 3 * 0.001cm = 0.003dB
    loss10_db = -10 * np.log10(p10)
    loss20_db = -10 * np.log10(p20)
    loss_diff = loss20_db - loss10_db

    # 10μm→20μm 增加 10μm = 0.001cm，损耗增加 0.003dB
    np.testing.assert_almost_equal(loss_diff, 0.003, decimal=4)


def test_y_branch_reciprocity():
    """Y 分支应满足互易性（S(i,j) = S(j,i)，与 simphony 一致）。

    光学无源器件的 S 矩阵应对称（互易性原理）。
    """
    wl = np.array([1.55])

    # PoLaRIS Y 分支
    s = y_branch_s(wl=wl)
    # S(port_2, port_1) 应等于 S(port_1, port_2)
    s_21 = s[("port_2", "port_1")][0]
    s_12 = s[("port_1", "port_2")][0]
    np.testing.assert_almost_equal(s_21, s_12, decimal=6)

    # simphony siepic Y 分支
    s_sim = siepic.y_branch(wl=wl)
    sim_21 = s_sim[("o1", "o0")][0]
    sim_12 = s_sim[("o0", "o1")][0]
    np.testing.assert_almost_equal(sim_21, sim_12, decimal=6)
