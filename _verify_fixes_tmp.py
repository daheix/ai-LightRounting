"""临时回归验证脚本：验证本轮 sim/ 顶层审查的 6 个 fix 修复点。

验证范围：
- fix1: lumerical_mode.py 5 处 fall-back -> raise ValueError
- fix2: lumerical_interconnect.py 3 处 fall-back -> raise ValueError
- fix3: lumerical_charge.py 3 处 fall-back + R02 溯源（Soref 1987）
- fix4: quantum_lossy.py quantum_advantage_threshold R02 溯源
- fix6: tidy3d_integration.py GPUFDTDEngine R04 合规声明
"""
from __future__ import annotations

import sys
import traceback

sys.path.insert(0, "/workspace/src")

PASS = 0
FAIL = 0


def _ok(name: str) -> None:
    global PASS
    PASS += 1
    print(f"  [PASS] {name}")


def _fail(name: str, exc: Exception) -> None:
    global FAIL
    FAIL += 1
    print(f"  [FAIL] {name}: {exc}")
    traceback.print_exc()


# ============================================================================
# fix1: lumerical_mode.py
# ============================================================================
def test_fix1_lumerical_mode() -> None:
    print("\n[fix1] lumerical_mode.py 5 处 fall-back -> raise ValueError")
    import numpy as np
    from polaris.sim.lumerical_mode import ModeSolver, ModeConfig

    # 1.1 solve_waveguide: n_core <= n_clad 时未找到导模应 raise
    try:
        cfg = ModeConfig()
        solver = ModeSolver(cfg)
        solver.solve_waveguide(width=0.5, height=0.2, core_index=1.0, cladding_index=1.5)
        _fail("solve_waveguide 应 raise 但未 raise", AssertionError("未抛出异常"))
    except ValueError as e:
        _ok(f"solve_waveguide raise ValueError: {str(e)[:60]}")
    except Exception as e:
        _fail("solve_waveguide", e)

    # 1.2 compute_neff 截止条件应 raise（构造截止场景：极小宽度）
    try:
        cfg = ModeConfig()
        solver = ModeSolver(cfg)
        # 极小宽度使 n_eff^2 < n_clad^2
        solver.compute_neff(width=0.001, core_index=1.45, cladding_index=1.44, wavelength=1.55)
        _fail("compute_neff 截止应 raise 但未 raise", AssertionError("未抛出异常"))
    except ValueError as e:
        _ok(f"compute_neff 截止 raise ValueError: {str(e)[:60]}")
    except Exception as e:
        _fail("compute_neff", e)

    # 1.3 compute_dispersion 波长点数 <3 应 raise
    try:
        cfg = ModeConfig()
        solver = ModeSolver(cfg)
        solver.compute_dispersion(wavelengths=[1.55], width=0.5)  # 仅 1 个点
        _fail("compute_dispersion 应 raise 但未 raise", AssertionError("未抛出异常"))
    except ValueError as e:
        _ok(f"compute_dispersion 点数<3 raise ValueError: {str(e)[:60]}")
    except Exception as e:
        _fail("compute_dispersion", e)

    # 1.4 compute_overlap 形状不一致应 raise
    try:
        cfg = ModeConfig()
        solver = ModeSolver(cfg)
        a = np.ones((5, 5))
        b = np.ones((6, 6))
        solver.compute_overlap(a, b)
        _fail("compute_overlap 形状不一致应 raise 但未 raise", AssertionError("未抛出异常"))
    except ValueError as e:
        _ok(f"compute_overlap 形状不一致 raise ValueError: {str(e)[:60]}")
    except Exception as e:
        _fail("compute_overlap", e)

    # 1.5 compute_overlap 零范数应 raise
    try:
        cfg = ModeConfig()
        solver = ModeSolver(cfg)
        a = np.zeros((5, 5))
        b = np.zeros((5, 5))
        solver.compute_overlap(a, b)
        _fail("compute_overlap 零范数应 raise 但未 raise", AssertionError("未抛出异常"))
    except ValueError as e:
        _ok(f"compute_overlap 零范数 raise ValueError: {str(e)[:60]}")
    except Exception as e:
        _fail("compute_overlap zero norm", e)


# ============================================================================
# fix2: lumerical_interconnect.py
# ============================================================================
def test_fix2_lumerical_interconnect() -> None:
    print("\n[fix2] lumerical_interconnect.py 3 处 fall-back -> raise ValueError")
    import numpy as np
    from polaris.sim.lumerical_interconnect import INTERCONNECTSimulator, INTERCONNECTConfig

    sim = INTERCONNECTSimulator(INTERCONNECTConfig())

    # 2.1 compute_ber n==0 应 raise（空比特数组）
    try:
        sim.compute_ber(np.array([], dtype=np.uint8), np.array([], dtype=np.uint8))
        _fail("compute_ber 空 input 应 raise 但未 raise", AssertionError("未抛出异常"))
    except ValueError as e:
        _ok(f"compute_ber 空 input raise ValueError: {str(e)[:60]}")
    except Exception as e:
        _fail("compute_ber", e)

    # 2.2 compute_eye_diagram crossings<2 应 raise（全 1 信号无过零）
    try:
        sig = np.ones(1000)
        sim.compute_eye_diagram(sig, n_bits=10)
        _fail("compute_eye_diagram crossings<2 应 raise 但未 raise", AssertionError("未抛出异常"))
    except ValueError as e:
        _ok(f"compute_eye_diagram crossings<2 raise ValueError: {str(e)[:60]}")
    except Exception as e:
        _fail("compute_eye_diagram", e)

    # 2.3 compute_osnr noise_power<1e-15 应 raise（全零噪声）
    try:
        signal = np.ones(100)
        noise = np.zeros(100)  # 全零噪声 -> noise_power ≈ 0
        sim.compute_osnr(signal, noise)
        _fail("compute_osnr noise<1e-15 应 raise 但未 raise", AssertionError("未抛出异常"))
    except ValueError as e:
        _ok(f"compute_osnr noise<1e-15 raise ValueError: {str(e)[:60]}")
    except Exception as e:
        _fail("compute_osnr", e)


# ============================================================================
# fix3: lumerical_charge.py
# ============================================================================
def test_fix3_lumerical_charge() -> None:
    print("\n[fix3] lumerical_charge.py 3 处 fall-back + R02 Soref 1987 溯源")
    import numpy as np
    from polaris.sim.lumerical_charge import (
        CHARGEConfig,
        CHARGESimulator,
        _SOREF_DN_AN,
        _SOREF_DN_AP,
    )

    # 3.0 R02 溯源：系数存在且为 Soref 1987 值
    try:
        assert _SOREF_DN_AN == -8.8e-22, f"dn_An 不符 Soref 1987: {_SOREF_DN_AN}"
        assert _SOREF_DN_AP == -8.5e-18, f"dn_Ap 不符 Soref 1987: {_SOREF_DN_AP}"
        _ok(f"R02 Soref 1987 系数正确: dn_An={_SOREF_DN_AN}, dn_Ap={_SOREF_DN_AP}")
    except Exception as e:
        _fail("R02 Soref 系数", e)

    cfg = CHARGEConfig(temperature=300.0, doping_n=1e18, doping_p=1e18, confinement_factor=0.3)
    sim = CHARGESimulator(cfg)

    # 3.1 compute_depletion_width v_total<=0 应 raise（强正向偏置）
    try:
        sim.compute_depletion_width(va=100.0)
        _fail("compute_depletion_width v_total<=0 应 raise 但未 raise", AssertionError("未抛出异常"))
    except ValueError as e:
        _ok(f"compute_depletion_width v_total<=0 raise ValueError: {str(e)[:60]}")
    except Exception as e:
        _fail("compute_depletion_width", e)

    # 3.2 compute_junction_capacitance w<1e-12 应 raise（接近内建电势的正向偏置）
    try:
        v_bi = sim._compute_build_in_potential()
        sim.compute_junction_capacitance(area=1e-12, va=v_bi - 1e-6)
        _fail("compute_junction_capacitance w<1e-12 应 raise 但未 raise", AssertionError("未抛出异常"))
    except ValueError as e:
        _ok(f"compute_junction_capacitance w<1e-12 raise ValueError: {str(e)[:60]}")
    except Exception as e:
        _fail("compute_junction_capacitance", e)

    # 3.3 compute_modulator_bandwidth RC<1e-30 应 raise（零电阻）
    try:
        sim.compute_modulator_bandwidth(r_series=0.0, c_j=1e-15)
        _fail("compute_modulator_bandwidth RC<1e-30 应 raise 但未 raise", AssertionError("未抛出异常"))
    except ValueError as e:
        _ok(f"compute_modulator_bandwidth RC<1e-30 raise ValueError: {str(e)[:60]}")
    except Exception as e:
        _fail("compute_modulator_bandwidth", e)

    # 3.4 electro_optic_simulation 正常流程（基于 Soref 1987 严格推导）
    try:
        result = sim.electro_optic_simulation({
            "voltage": 2.0,
            "length": 100.0,
            "wavelength": 1.55,
            "width": 0.5,
        })
        assert "delta_n_carrier" in result, "delta_n_carrier 字段缺失"
        assert "delta_n" in result, "delta_n 字段缺失"
        assert "confinement_factor" in result, "confinement_factor 字段缺失"
        assert "n_eff_doping_cm3" in result, "n_eff_doping_cm3 字段缺失"
        assert result["delta_w"] > 0, f"反向偏置 delta_w 应 > 0，实际 {result['delta_w']}"
        assert np.isfinite(result["delta_n"]), f"delta_n 非有限值: {result['delta_n']}"
        assert np.isfinite(result["phase_shift"]), f"phase_shift 非有限值: {result['phase_shift']}"
        _ok(f"electro_optic_simulation 正常返回: delta_w={result['delta_w']:.3e} m, "
            f"delta_n={result['delta_n']:.3e}, phase_shift={result['phase_shift']:.3e} rad")
    except Exception as e:
        _fail("electro_optic_simulation", e)


# ============================================================================
# fix4: quantum_lossy.py
# ============================================================================
def test_fix4_quantum_lossy() -> None:
    print("\n[fix4] quantum_lossy.py quantum_advantage_threshold R02 溯源")
    from polaris.sim.quantum_lossy import quantum_advantage_threshold

    # 4.1 参数校验：n_photons=0 应 raise
    try:
        quantum_advantage_threshold(n_photons=0, loss_rate=0.1)
        _fail("n_photons=0 应 raise 但未 raise", AssertionError("未抛出异常"))
    except ValueError as e:
        _ok(f"n_photons<1 raise ValueError: {str(e)[:60]}")
    except Exception as e:
        _fail("n_photons=0", e)

    # 4.2 参数校验：loss_rate>1 应 raise
    try:
        quantum_advantage_threshold(n_photons=10, loss_rate=1.5)
        _fail("loss_rate>1 应 raise 但未 raise", AssertionError("未抛出异常"))
    except ValueError as e:
        _ok(f"loss_rate>1 raise ValueError: {str(e)[:60]}")
    except Exception as e:
        _fail("loss_rate=1.5", e)

    # 4.3 定理验证：N_detected >= sqrt(N) -> True（量子优势）
    try:
        result = quantum_advantage_threshold(n_photons=100, loss_rate=0.0)
        assert result is True, f"N=100 loss=0 应 True，实际 {result}"
        _ok("N=100 loss=0 -> True（N_detected=100 >= sqrt(100)=10）")
    except Exception as e:
        _fail("N=100 loss=0", e)

    # 4.4 定理验证：N_detected < sqrt(N) -> False（可经典模拟）
    try:
        result = quantum_advantage_threshold(n_photons=100, loss_rate=0.99)
        assert result is False, f"N=100 loss=0.99 应 False，实际 {result}"
        _ok("N=100 loss=0.99 -> False（N_detected=1 < sqrt(100)=10）")
    except Exception as e:
        _fail("N=100 loss=0.99", e)

    # 4.5 临界点：N=100, loss=0.9 -> N_detected=10 = sqrt(100)=10 -> True
    try:
        result = quantum_advantage_threshold(n_photons=100, loss_rate=0.9)
        assert result is True, f"N=100 loss=0.9 应 True，实际 {result}"
        _ok("N=100 loss=0.9 -> True（N_detected=10 >= sqrt(100)=10，临界点）")
    except Exception as e:
        _fail("N=100 loss=0.9", e)


# ============================================================================
# fix6: tidy3d_integration.py GPUFDTDEngine R04 合规声明
# ============================================================================
def test_fix6_tidy3d_integration() -> None:
    print("\n[fix6] tidy3d_integration.py GPUFDTDEngine R04 合规声明")
    from polaris.sim.tidy3d_integration import GPUFDTDEngine, GPUFDTDConfig

    # 6.1 类可正常实例化（纯 NumPy，无 GPU 依赖）
    try:
        cfg = GPUFDTDConfig(wavelength_um=1.55, n_steps=10, dx_um=0.05, n_layers=5)
        engine = GPUFDTDEngine(cfg)
        _ok("GPUFDTDEngine 实例化成功（纯 NumPy，无 GPU 依赖）")
    except Exception as e:
        _fail("GPUFDTDEngine 实例化", e)

    # 6.2 docstring 包含 R04 合规声明
    try:
        doc = GPUFDTDEngine.__doc__ or ""
        assert "R04" in doc, "docstring 缺少 R04 合规声明"
        assert "不参与 GPU" in doc or "🚫" in doc, "docstring 缺少不参与 GPU 声明"
        _ok("GPUFDTDEngine docstring 含 R04 合规声明")
    except Exception as e:
        _fail("docstring R04 声明", e)

    # 6.3 模块顶部 docstring 含 R04 章节
    try:
        import polaris.sim.tidy3d_integration as mod
        mod_doc = mod.__doc__ or ""
        assert "R04" in mod_doc, "模块 docstring 缺少 R04 章节"
        assert "不参与 GPU" in mod_doc or "🚫" in mod_doc, "模块 docstring 缺少不参与 GPU 声明"
        _ok("模块顶部 docstring 含 R04 章节")
    except Exception as e:
        _fail("模块 docstring R04", e)


def main() -> int:
    print("=" * 70)
    print("PoLaRIS sim/ 顶层审查 fix1-fix6 回归验证")
    print("=" * 70)

    test_fix1_lumerical_mode()
    test_fix2_lumerical_interconnect()
    test_fix3_lumerical_charge()
    test_fix4_quantum_lossy()
    test_fix6_tidy3d_integration()

    print("\n" + "=" * 70)
    print(f"总计: PASS={PASS}, FAIL={FAIL}")
    print("=" * 70)
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
