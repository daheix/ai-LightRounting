"""扩展测试（从 test_circuit.py 拆分，遵守 R11 质量门禁文件≤800行）.

来源（R02 学术诚信）: 同原文件 test_circuit.py。
"""


from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

# 让测试既能从已安装包导入，也能从源码树导入（CI/开发模式）
_SRC = str(Path(__file__).resolve().parents[1] / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from polaris_circuit import (  # noqa: E402
    BerEvaluator,
    C0,
    COND_NUM_FG_THRESHOLD,
    COND_NUM_KLU_THRESHOLD,
    CircuitSimulator,
    EPS0,
    FDTDSimulator,
    HybridSimulator,
    MU0,
    MNACircuit,
    NonlinearModel,
    OpticalLink,
    PMLBoundary,
    RingParams,
    SPEED_OF_LIGHT,
    SignalFlowGraph,
    Subcircuit,
    Term,
    Connector,
    TLLMLaser,
    TimeDomainCircuitSimulator,
    TimeDomainSimulator,
    WavelengthRange,
    YeeGrid,
    cascade_circuit,
    compute_condition_number,
    crossing_s,
    default_models,
    directional_coupler_s,
    grating_coupler_s,
    group_delay,
    mmi_1x2_s,
    mmi_2x2_s,
    phase_shifter_s,
    ring_resonator_s,
    run_mna_spice,
    run_time_domain_circuit,
    simulate_system_level,
    terminator_s,
    to_time_domain,
    waveguide_s,
    y_branch_s,
)


# ============================================================================
# 1. 波导模型 (waveguide_s) — 相位/损耗/互易/边界 (6 测试)
# ============================================================================


def test_pml_boundary_attenuates_edge_fields() -> None:
    """PML 应用后边界场应衰减（< 初始值）。"""
    grid = YeeGrid(nx=10, ny=10, dx=1e-6, dy=1e-6)
    grid.Ex[:] = 1.0
    pml = PMLBoundary(thickness=3, sigma=1.0)
    pml.apply(grid)
    # 边界场应 < 1.0（被衰减）
    assert grid.Ex[0, 0] < 1.0
    assert grid.Ex[-1, -1] < 1.0


def test_pml_boundary_invalid_params_raises() -> None:
    """PML 参数<=0 应 raise ValueError。"""
    with pytest.raises(ValueError, match="thickness 必须 > 0"):
        PMLBoundary(thickness=0, sigma=1.0)
    with pytest.raises(ValueError, match="sigma 必须 > 0"):
        PMLBoundary(thickness=5, sigma=0.0)


def test_fdtd_cfl_condition_value() -> None:
    """FDTD CFL 条件: dt_max = 1/(c·√(1/dx²+1/dy²))。"""
    dx = dy = 1e-6
    dt_max = FDTDSimulator.cfl_condition(dx, dy)
    expected = 1.0 / (C0 * np.sqrt(2.0) / dx)
    assert dt_max == pytest.approx(expected, rel=1e-9)


def test_fdtd_step_cfl_violation_raises() -> None:
    """FDTD dt 违反 CFL 条件应 raise ValueError。"""
    grid = YeeGrid(nx=5, ny=5, dx=1e-6, dy=1e-6)
    eps = np.ones((5, 5))
    sim = FDTDSimulator(grid, eps)
    dt_max = FDTDSimulator.cfl_condition(1e-6, 1e-6)
    with pytest.raises(ValueError, match="违反 CFL"):
        sim.step(dt=dt_max * 2.0)  # 2倍 CFL 必然违反


def test_fdtd_run_finite_output() -> None:
    """FDTD run: 输出 E/H/t 历史全部有限。"""
    grid = YeeGrid(nx=10, ny=10, dx=1e-7, dy=1e-7)
    eps = np.ones((10, 10))
    sim = FDTDSimulator(grid, eps)
    result = sim.run(n_steps=5, source_pos=(5, 5), source_freq=2e14)
    assert result["E"].shape == (5, 10, 10)
    assert result["H"].shape == (5, 10, 10)
    assert np.all(np.isfinite(result["E"]))
    assert np.all(np.isfinite(result["H"]))


# ============================================================================
# 12. 级联 cascade_circuit + CircuitSimulator (5 测试)
# ============================================================================
def test_circuit_simulator_mzi_double_waveguide() -> None:
    """CircuitSimulator: 双波导级联 |S|=1（无损），50 频点。"""
    sim = CircuitSimulator()
    for name, model in default_models().items():
        sim.register_model(name, model)
    netlist = {
        "instances": {"wg1": "waveguide", "wg2": "waveguide"},
        "connections": {"wg1.out": "wg2.in"},
        "ports": {"in": "wg1.in", "out": "wg2.out"},
    }
    wl_range = WavelengthRange(wl_start=1.55, wl_end=1.56, n_points=50)
    wavelengths, sdict = sim.sweep_wavelength(netlist, wl_range)
    assert len(wavelengths) == 50
    s_vals = sdict[("out", "in")]
    assert len(s_vals) == 50
    assert np.allclose(np.abs(s_vals), 1.0, atol=1e-9)
    assert np.all(np.isfinite(s_vals))


def test_circuit_simulator_unregistered_model_raises() -> None:
    """CircuitSimulator 引用未注册模型应 raise KeyError（R03）。"""
    sim = CircuitSimulator()
    netlist = {
        "instances": {"wg1": "unknown_model"},
        "connections": {},
        "ports": {"in": "wg1.in", "out": "wg1.out"},
    }
    with pytest.raises(KeyError, match="未注册"):
        sim.simulate(netlist, wavelengths=np.array([1.55]))


def test_cascade_two_waveguides_phase_additive() -> None:
    """级联两波导: 相位叠加，|S|=1（无损）。"""
    wl = np.array([1.55])
    s1 = waveguide_s(wl=wl, length=10.0, neff=2.4)
    s2 = waveguide_s(wl=wl, length=20.0, neff=2.4)
    result = cascade_circuit(
        {"wg1": s1, "wg2": s2},
        [("wg1.out", "wg2.in")],
        {"in": "wg1.in", "out": "wg2.out"},
    )
    assert ("out", "in") in result
    # |S|=1（无损波导级联）
    assert np.abs(result[("out", "in")][0]) == pytest.approx(1.0, abs=1e-9)


def test_cascade_singular_denominator_raises() -> None:
    """级联分母趋零（全反射谐振）应 raise RuntimeError（R03）。"""
    # s1: out 端口全反射 S_AA=1
    s1 = {
        ("in", "in"): np.array([0.0 + 0j]),
        ("out", "out"): np.array([1.0 + 0j]),
        ("out", "in"): np.array([0.0 + 0j]),
        ("in", "out"): np.array([0.0 + 0j]),
    }
    # s2: in 端口全反射 S_BB=1
    s2 = {
        ("in", "in"): np.array([1.0 + 0j]),
        ("out", "out"): np.array([0.0 + 0j]),
        ("out", "in"): np.array([0.0 + 0j]),
        ("in", "out"): np.array([0.0 + 0j]),
    }
    with pytest.raises(RuntimeError, match="分母趋零"):
        cascade_circuit(
            {"d1": s1, "d2": s2},
            [("d1.out", "d2.in")],
            None,
        )


def test_cascade_nonexistent_instance_raises() -> None:
    """级联连接指向不存在实例应 raise RuntimeError（R03）。"""
    wl = np.array([1.55])
    s1 = waveguide_s(wl=wl, length=10.0, neff=2.4)
    with pytest.raises(RuntimeError, match="指向不存在的实例"):
        cascade_circuit(
            {"wg1": s1},
            [("wg1.out", "wg2.in")],  # wg2 不存在
            None,
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
