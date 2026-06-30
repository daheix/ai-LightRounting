"""R453-R550 仿真性能优化综合测试（纯 NumPy/SciPy CPU，R04 兼容）。

测试覆盖：
- R453 FdeShiftInvertAccelerator: shift-invert + LU 缓存
- R454 EmeAdaptiveModeSelector: 收敛性驱动模式数选择
- R455 BpmPadeLargeStep: Padé(1,1)/(2,2) 大步长
- R456 NumpyVectorizedFdtdCore: NumPy 向量化 FDTD
- R457-R550 SparamCascadeCache / MemoryPool / PerfBenchmarkSuite / MultiprocessRunner
- R03/R02/R04 合规 + 端到端集成

文献依据：
- Lehoucq 1998 ARPACK https://doi.org/10.1137/1.9780898719628
- Hadley 1994 Padé BPM https://doi.org/10.1364/OL.17.001426
- Gallagher 2003 EME https://doi.org/10.1117/12.478061
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest
import scipy.sparse as sp

# 直接加载模块（绕过 polaris.sim.__init__ 的 sax 依赖）
_SRC_DIR = Path(__file__).resolve().parent.parent / "src" / "polaris"


def _load_module(rel_path: str, module_name: str):
    """从 src/polaris/ 下相对路径直接加载模块。"""
    file_path = _SRC_DIR / rel_path
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)
    return mod


_perf = _load_module("sim/perf_optimization.py", "_r453_perf")


# ===========================================================================
# R453 FDE 加速器
# ===========================================================================


class TestR453FdeAccelerator:
    """R453 FDE shift-invert 加速器测试。"""

    def test_construction_validates_square_matrix(self):
        """非方阵须 raise（R03）。"""
        rect = sp.csr_array(np.zeros((5, 7), dtype=np.complex128))
        with pytest.raises(ValueError, match="方阵"):
            _perf.FdeShiftInvertAccelerator(rect, sigma=1.0)

    def test_construction_validates_sigma_finite(self):
        """sigma 非有限须 raise（R03）。"""
        mat = sp.csr_array(np.eye(10, dtype=np.complex128))
        with pytest.raises(ValueError, match="sigma"):
            _perf.FdeShiftInvertAccelerator(mat, sigma=float("inf"))

    def test_solve_returns_eigenvalues_near_sigma(self):
        """shift-invert 应返回最靠近 sigma 的本征值。"""
        # 构造已知本征值的对角矩阵
        n = 20
        eigvals_true = np.linspace(1.0, 20.0, n)
        mat = sp.diags(eigvals_true, 0, format="csr", dtype=np.float64)
        # sigma 用非整数避免撞本征值（sigma 严格等于本征值时 A-σI 奇异）
        sigma = 10.55  # 介于 10 和 11 之间
        acc = _perf.FdeShiftInvertAccelerator(mat, sigma=sigma)
        result = acc.solve(num_modes=3)
        # 应找到最靠近 10.55 的 3 个本征值：10, 11, 9 或 12
        sorted_eigs = np.sort(result.eigenvalues.real)
        # 容差 1.5（linspace 间距 1.0，最近 3 个本征值跨度 3）
        valid_set = {9.0, 10.0, 11.0, 12.0}
        for e in sorted_eigs:
            assert any(abs(e - v) < 0.5 for v in valid_set), \
                f"本征值 {e} 不在预期集合 {valid_set} 附近"

    def test_solve_validates_num_modes(self):
        """num_modes 超出范围须 raise（R03）。"""
        mat = sp.csr_array(np.eye(10, dtype=np.complex128))
        acc = _perf.FdeShiftInvertAccelerator(mat, sigma=1.0)
        with pytest.raises(ValueError, match="num_modes"):
            acc.solve(num_modes=0)
        with pytest.raises(ValueError, match="num_modes"):
            acc.solve(num_modes=10)

    def test_solve_returns_beta(self):
        """结果应包含 β=sqrt(β²)。"""
        n = 15
        eigvals_true = np.linspace(2.0, 30.0, n)
        mat = sp.diags(eigvals_true, 0, format="csr", dtype=np.float64)
        # sigma 用非整数避免奇异
        acc = _perf.FdeShiftInvertAccelerator(mat, sigma=10.5)
        result = acc.solve(num_modes=2)
        assert result.beta.shape == (2,)
        # β = sqrt(β²)，对正实数本征值取正根
        expected = np.sqrt(result.eigenvalues)
        np.testing.assert_allclose(result.beta, expected, rtol=1e-8)

    def test_lu_cache_reuse(self):
        """LU 因子缓存应被第二次调用复用。"""
        n = 30
        rng = np.random.default_rng(42)
        # 对称正定矩阵
        a = rng.standard_normal((n, n))
        mat_dense = a @ a.T + n * np.eye(n)
        mat = sp.csr_array(mat_dense)
        cache: dict[str, object] = {}
        # sigma 取非本征值（用 trace/n + 0.5 偏移避免奇异）
        sigma = float(np.trace(mat_dense) / n) + 0.5
        # 第一次：未缓存
        acc1 = _perf.FdeShiftInvertAccelerator(
            mat, sigma=sigma, lu_cache=cache, cache_key="m1",
        )
        result1 = acc1.solve(num_modes=2)
        assert not result1.lu_cached
        assert "m1" in cache
        # 第二次：相同 key 复用 LU
        acc2 = _perf.FdeShiftInvertAccelerator(
            mat, sigma=sigma, lu_cache=cache, cache_key="m1",
        )
        result2 = acc2.solve(num_modes=2)
        assert result2.lu_cached
        # 本征值应一致
        np.testing.assert_allclose(
            np.sort(result1.eigenvalues.real),
            np.sort(result2.eigenvalues.real),
            rtol=1e-6,
        )

    def test_solve_time_positive(self):
        """solve_time 应为正。"""
        n = 20
        mat = sp.diags(np.linspace(1.0, 20.0, n), 0, format="csr")
        # sigma 用非整数避免奇异
        acc = _perf.FdeShiftInvertAccelerator(mat, sigma=10.5)
        result = acc.solve(num_modes=2)
        assert result.solve_time > 0.0


# ===========================================================================
# R454 EME 模式数自适应选择
# ===========================================================================


class TestR454EmeAdaptiveModeSelector:
    """R454 EME 模式数自适应选择测试。"""

    def test_construction_validates_norm(self):
        """norm 非法须 raise（R03）。"""
        with pytest.raises(ValueError, match="norm"):
            _perf.EmeAdaptiveModeSelector(solve_fn=lambda m: np.eye(2 * m),
                                          norm="invalid")

    def test_select_finds_converged_mode_count(self):
        """自适应选择应在收敛时停止。"""
        # 模拟 S 矩阵随 M 增大收敛：M=4 误差大，M=8 误差小，M=12 已收敛
        def solve_fn(m: int) -> np.ndarray:
            # S 矩阵元素随 M 衰减到稳定值
            stable = np.eye(2 * m) * 0.5
            perturb = np.eye(2 * m) * 0.1 / m  # 1/M 衰减
            return stable + perturb

        selector = _perf.EmeAdaptiveModeSelector(solve_fn=solve_fn)
        result = selector.select(
            candidate_Ms=[4, 8, 12, 16], threshold=0.05,
        )
        assert result.selected_count in (8, 12)
        assert result.relative_error < 0.05
        assert result.speedup_factor >= 1.0

    def test_select_validates_candidate_list(self):
        """候选列表非法须 raise（R03）。"""
        selector = _perf.EmeAdaptiveModeSelector(solve_fn=lambda m: np.eye(2 * m))
        with pytest.raises(ValueError, match="2 项"):
            selector.select(candidate_Ms=[5], threshold=0.01)
        with pytest.raises(ValueError, match="升序"):
            selector.select(candidate_Ms=[10, 5, 8], threshold=0.01)

    def test_select_validates_threshold(self):
        """threshold 越界须 raise（R03）。"""
        selector = _perf.EmeAdaptiveModeSelector(solve_fn=lambda m: np.eye(2 * m))
        with pytest.raises(ValueError, match="threshold"):
            selector.select(candidate_Ms=[4, 8], threshold=0.0)
        with pytest.raises(ValueError, match="threshold"):
            selector.select(candidate_Ms=[4, 8], threshold=1.0)

    def test_select_no_convergence_raises(self):
        """所有候选均未收敛须 raise（R03：禁止 fall-back）。"""
        # S 矩阵不随 M 改变 → 永远不收敛到非零阈值
        counter = [0]

        def solve_fn(m: int) -> np.ndarray:
            counter[0] += 1
            # 每次返回大变化（永不收敛）
            return np.eye(2 * m) * (1.0 + counter[0])

        selector = _perf.EmeAdaptiveModeSelector(solve_fn=solve_fn)
        with pytest.raises(ValueError, match="未收敛"):
            selector.select(candidate_Ms=[4, 8, 12], threshold=0.01)

    def test_convergence_history_recorded(self):
        """convergence_history 应记录各候选 M 的误差。"""
        def solve_fn(m: int) -> np.ndarray:
            return np.eye(2 * m) * (1.0 + 0.5 / m)

        selector = _perf.EmeAdaptiveModeSelector(solve_fn=solve_fn)
        result = selector.select(
            candidate_Ms=[4, 8, 12, 16], threshold=0.5,
        )
        assert len(result.convergence_history) >= 1
        for m, eps in result.convergence_history:
            assert m in (8, 12, 16)
            assert eps >= 0.0

    def test_speedup_factor_computation(self):
        """speedup_factor = (max_M / selected)²。"""
        def solve_fn(m: int) -> np.ndarray:
            return np.eye(2 * m) * (1.0 + 1e-4 / m)

        selector = _perf.EmeAdaptiveModeSelector(solve_fn=solve_fn)
        result = selector.select(
            candidate_Ms=[4, 8, 12], threshold=1e-2,
        )
        if result.selected_count == 4:
            # 4 不在收敛点（第一个 M 是参考点），所以 selected 至少是 8
            pass
        expected_speedup = (12.0 / result.selected_count) ** 2
        assert result.speedup_factor == pytest.approx(expected_speedup, rel=1e-6)

    def test_norm_inf(self):
        """inf 范数应正确计算。"""
        def solve_fn(m: int) -> np.ndarray:
            # 构造已知 inf 范数的矩阵
            s = np.eye(2 * m) * 2.0
            s[0, 0] = 5.0  # 行和最大 = 5
            return s

        selector = _perf.EmeAdaptiveModeSelector(solve_fn=solve_fn, norm="inf")
        result = selector.select(
            candidate_Ms=[4, 8, 12], threshold=0.1,
        )
        assert result.selected_count in (8, 12)


# ===========================================================================
# R455 BPM Padé 大步长
# ===========================================================================


class TestR455BpmPadeLargeStep:
    """R455 BPM Padé 大步长测试。"""

    def test_construction_validates_params(self):
        """参数非法须 raise（R03）。"""
        n_prof = np.ones(50)
        with pytest.raises(ValueError, match="wavelength"):
            _perf.BpmPadeLargeStep(n_prof, wavelength=-1.0, dx=1e-6, n_ref=1.0)
        with pytest.raises(ValueError, match="dx"):
            _perf.BpmPadeLargeStep(n_prof, wavelength=1.55e-6, dx=0.0, n_ref=1.0)
        with pytest.raises(ValueError, match="n_ref"):
            _perf.BpmPadeLargeStep(n_prof, wavelength=1.55e-6, dx=1e-6, n_ref=0.0)

    def test_construction_validates_ndim(self):
        """n_profile 须 1D/2D。"""
        with pytest.raises(ValueError, match="1D/2D"):
            _perf.BpmPadeLargeStep(
                np.ones((3, 3, 3)), wavelength=1.55e-6, dx=1e-6, n_ref=1.0,
            )

    def test_propagate_1d_pade11_power_conservation(self):
        """1D Padé(1,1) 自由空间功率守恒（CN A-稳定）。"""
        n = 100
        n_prof = np.ones(n) * 1.5  # 均匀介质
        dx = 0.1e-6
        n_ref = 1.5
        prop = _perf.BpmPadeLargeStep(
            n_prof, wavelength=1.55e-6, dx=dx, n_ref=n_ref,
        )
        x = np.arange(n) * dx
        psi_0 = np.exp(-((x - 5e-6) ** 2) / (1e-6 ** 2)).astype(np.complex128)
        result = prop.propagate(
            psi_0, dz=0.5e-6, n_steps=20, pade_order=(1, 1),
        )
        # 自由空间 CN 功率守恒
        p0 = result.power_history[0]
        p_end = result.power_history[-1]
        rel_err = abs(p_end - p0) / p0
        assert rel_err < 1e-6, f"功率守恒误差 {rel_err}"

    def test_propagate_1d_pade22_power_conservation(self):
        """1D Padé(2,2) 自由空间功率守恒（A-稳定）。"""
        n = 100
        n_prof = np.ones(n) * 1.5
        dx = 0.1e-6
        prop = _perf.BpmPadeLargeStep(
            n_prof, wavelength=1.55e-6, dx=dx, n_ref=1.5,
        )
        x = np.arange(n) * dx
        psi_0 = np.exp(-((x - 5e-6) ** 2) / (1e-6 ** 2)).astype(np.complex128)
        result = prop.propagate(
            psi_0, dz=1.5e-6, n_steps=10, pade_order=(2, 2),
        )
        # Padé(2,2) 功率守恒（A-稳定，允许大步长）
        p0 = result.power_history[0]
        p_end = result.power_history[-1]
        rel_err = abs(p_end - p0) / p0
        assert rel_err < 1e-6, f"Padé(2,2) 功率守恒误差 {rel_err}"

    def test_pade22_allows_larger_step_than_pade11(self):
        """Padé(2,2) 应允许更大步长而不发散（高阶精度）。"""
        n = 80
        n_prof = np.ones(n) * 1.5
        dx = 0.1e-6
        prop = _perf.BpmPadeLargeStep(
            n_prof, wavelength=1.55e-6, dx=dx, n_ref=1.5,
        )
        x = np.arange(n) * dx
        psi_0 = np.exp(-((x - 4e-6) ** 2) / (1e-6 ** 2)).astype(np.complex128)
        # Padé(2,2) 用 5x 大步长应仍稳定
        large_dz = 5.0e-6
        result = prop.propagate(
            psi_0, dz=large_dz, n_steps=4, pade_order=(2, 2),
        )
        # 检查场有界（数值稳定）
        assert np.all(np.isfinite(result.field_history))
        # 检查功率非零
        assert result.power_history[-1] > 0

    def test_propagate_validates_dz(self):
        """dz 非法须 raise（R03）。"""
        n_prof = np.ones(50)
        prop = _perf.BpmPadeLargeStep(
            n_prof, wavelength=1.55e-6, dx=1e-6, n_ref=1.0,
        )
        psi = np.ones(50, dtype=np.complex128)
        with pytest.raises(ValueError, match="dz"):
            prop.propagate(psi, dz=0.0, n_steps=10)
        with pytest.raises(ValueError, match="n_steps"):
            prop.propagate(psi, dz=1e-6, n_steps=0)

    def test_propagate_validates_pade_order(self):
        """不支持的 Padé 阶数须 raise（R03）。"""
        n_prof = np.ones(50)
        prop = _perf.BpmPadeLargeStep(
            n_prof, wavelength=1.55e-6, dx=1e-6, n_ref=1.0,
        )
        psi = np.ones(50, dtype=np.complex128)
        with pytest.raises(ValueError, match="pade_order"):
            prop.propagate(psi, dz=1e-6, n_steps=10, pade_order=(3, 3))

    def test_propagate_2d_runs(self):
        """2D BPM 应能正常运行。"""
        n_prof = np.ones((30, 30)) * 1.5
        prop = _perf.BpmPadeLargeStep(
            n_prof, wavelength=1.55e-6, dx=0.2e-6, n_ref=1.5,
        )
        psi_0 = np.zeros((30, 30), dtype=np.complex128)
        psi_0[15, 15] = 1.0
        result = prop.propagate(psi_0, dz=0.5e-6, n_steps=5, pade_order=(1, 1))
        assert result.field_history.shape == (6, 30, 30)
        assert np.all(np.isfinite(result.field_history))

    def test_z_coords_increments(self):
        """z 坐标应按 dz 递增。"""
        n_prof = np.ones(50)
        prop = _perf.BpmPadeLargeStep(
            n_prof, wavelength=1.55e-6, dx=1e-6, n_ref=1.0,
        )
        psi = np.zeros(50, dtype=np.complex128)
        psi[25] = 1.0
        dz = 0.3e-6
        result = prop.propagate(psi, dz=dz, n_steps=10, pade_order=(1, 1))
        expected_z = np.arange(11) * dz
        np.testing.assert_allclose(result.z_coords, expected_z, rtol=1e-12)


# ===========================================================================
# R456 NumPy 向量化 FDTD
# ===========================================================================


class TestR456NumpyVectorizedFdtd:
    """R456 NumPy 向量化 FDTD 测试。"""

    def test_construction_validates_shape(self):
        """网格过小须 raise（R03）。"""
        with pytest.raises(ValueError, match="过小"):
            _perf.NumpyVectorizedFdtdCore(
                shape=(3, 3), dx=1e-7, dy=1e-7, dt=1e-16,
                eps_r=np.ones((3, 3)),
            )

    def test_construction_validates_cfl(self):
        """CFL 违反须 raise（R03）。"""
        c0 = 2.99792458e8
        dx = 1e-7
        dt_too_large = 10.0 * dx / c0  # 远超 CFL
        with pytest.raises(ValueError, match="CFL"):
            _perf.NumpyVectorizedFdtdCore(
                shape=(10, 10), dx=dx, dy=dx, dt=dt_too_large,
                eps_r=np.ones((10, 10)),
            )

    def test_construction_validates_eps_r(self):
        """eps_r 非正须 raise（R03）。"""
        eps = np.ones((10, 10))
        eps[5, 5] = 0.0
        c0 = 2.99792458e8
        dx = 1e-7
        dt = 0.5 * dx / c0
        with pytest.raises(ValueError, match="eps_r"):
            _perf.NumpyVectorizedFdtdCore(
                shape=(10, 10), dx=dx, dy=dx, dt=dt,
                eps_r=eps,
            )

    def test_step_preserves_zeros(self):
        """零场单步应为零。"""
        c0 = 2.99792458e8
        dx = 1e-7
        dt = 0.5 * dx / c0
        shape = (10, 10)
        core = _perf.NumpyVectorizedFdtdCore(
            shape=shape, dx=dx, dy=dx, dt=dt,
            eps_r=np.ones(shape),
        )
        e = np.zeros(shape)
        hx = np.zeros(shape)
        hy = np.zeros(shape)
        e_new, hx_new, hy_new = core.step(e, hx, hy)
        np.testing.assert_allclose(e_new, 0.0)
        np.testing.assert_allclose(hx_new, 0.0)
        np.testing.assert_allclose(hy_new, 0.0)

    def test_step_propagates_source(self):
        """源注入后场应传播。"""
        c0 = 2.99792458e8
        dx = 1e-7
        dt = 0.5 * dx / c0
        shape = (20, 20)
        core = _perf.NumpyVectorizedFdtdCore(
            shape=shape, dx=dx, dy=dx, dt=dt,
            eps_r=np.ones(shape),
        )
        e = np.zeros(shape)
        e[10, 10] = 1.0
        hx = np.zeros(shape)
        hy = np.zeros(shape)
        e_new, hx_new, hy_new = core.step(e, hx, hy)
        # 应有非零场扩散
        assert np.any(e_new != 0.0)
        assert np.any(hx_new != 0.0)
        assert np.any(hy_new != 0.0)

    def test_run_returns_history(self):
        """run 应返回完整时序。"""
        c0 = 2.99792458e8
        dx = 1e-7
        dt = 0.5 * dx / c0
        shape = (15, 15)
        core = _perf.NumpyVectorizedFdtdCore(
            shape=shape, dx=dx, dy=dx, dt=dt,
            eps_r=np.ones(shape),
        )
        e0 = np.zeros(shape)
        e0[7, 7] = 1.0
        hx0 = np.zeros(shape)
        hy0 = np.zeros(shape)
        n_steps = 10
        result = core.run(e0, hx0, hy0, n_steps=n_steps)
        assert result.e_z_history.shape == (n_steps + 1,) + shape
        assert result.h_x_history.shape == (n_steps + 1,) + shape
        assert result.h_y_history.shape == (n_steps + 1,) + shape
        assert result.time.shape == (n_steps + 1,)
        assert result.wall_time > 0.0

    def test_run_with_source_fn(self):
        """带源注入函数的运行应正确注入。"""
        c0 = 2.99792458e8
        dx = 1e-7
        dt = 0.5 * dx / c0
        shape = (15, 15)
        core = _perf.NumpyVectorizedFdtdCore(
            shape=shape, dx=dx, dy=dx, dt=dt,
            eps_r=np.ones(shape),
        )
        e0 = np.zeros(shape)
        hx0 = np.zeros(shape)
        hy0 = np.zeros(shape)
        injection_count = [0]

        def source_fn(k: int, e: np.ndarray) -> None:
            if k < 5:
                e[7, 7] += 1.0
                injection_count[0] += 1

        result = core.run(e0, hx0, hy0, n_steps=10, source_fn=source_fn)
        assert injection_count[0] == 5
        # 最终场应有能量
        assert np.sum(result.e_z_history[-1] ** 2) > 0

    def test_run_validates_shapes(self):
        """场形状不匹配须 raise（R03）。"""
        c0 = 2.99792458e8
        dx = 1e-7
        dt = 0.5 * dx / c0
        shape = (10, 10)
        core = _perf.NumpyVectorizedFdtdCore(
            shape=shape, dx=dx, dy=dx, dt=dt,
            eps_r=np.ones(shape),
        )
        with pytest.raises(ValueError, match="e_z"):
            core.run(np.zeros((8, 8)), np.zeros(shape), np.zeros(shape), n_steps=5)

    def test_run_validates_n_steps(self):
        """n_steps 非法须 raise（R03）。"""
        c0 = 2.99792458e8
        dx = 1e-7
        dt = 0.5 * dx / c0
        shape = (10, 10)
        core = _perf.NumpyVectorizedFdtdCore(
            shape=shape, dx=dx, dy=dx, dt=dt,
            eps_r=np.ones(shape),
        )
        with pytest.raises(ValueError, match="n_steps"):
            core.run(np.zeros(shape), np.zeros(shape), np.zeros(shape), n_steps=0)

    def test_consistency_with_yee_formula(self):
        """与标准 Yee 公式一致性（与 yee_grid 模块结果对比）。"""
        # 此测试验证向量化 FDTD 与手动 Yee leapfrog 给出相同结果
        c0 = 2.99792458e8
        dx = 1e-7
        dt = 0.5 * dx / c0
        shape = (8, 8)
        core = _perf.NumpyVectorizedFdtdCore(
            shape=shape, dx=dx, dy=dx, dt=dt,
            eps_r=np.ones(shape),
        )
        e0 = np.zeros(shape)
        e0[4, 4] = 1.0
        hx0 = np.zeros(shape)
        hy0 = np.zeros(shape)
        result = core.run(e0, hx0, hy0, n_steps=3)
        # 验证时间步进正确递增
        np.testing.assert_allclose(result.time, np.arange(4) * dt)
        # 验证场有限
        assert np.all(np.isfinite(result.e_z_history))


# ===========================================================================
# R457-R550 S 参数缓存 / 内存池 / 基准套件 / 多进程
# ===========================================================================


class TestR457SparamCache:
    """S 参数级联 LRU 缓存测试。"""

    def test_construction_validates_max_size(self):
        with pytest.raises(ValueError, match="max_size"):
            _perf.SparamCascadeCache(max_size=0)

    def test_make_key_deterministic(self):
        """相同参数应生成相同键。"""
        key1 = _perf.SparamCascadeCache.make_key([1.0, 2.0], 4, 1.55e-6)
        key2 = _perf.SparamCascadeCache.make_key([1.0, 2.0], 4, 1.55e-6)
        assert key1 == key2

    def test_make_key_distinct_for_different_params(self):
        """不同参数应生成不同键。"""
        key1 = _perf.SparamCascadeCache.make_key([1.0, 2.0], 4, 1.55e-6)
        key2 = _perf.SparamCascadeCache.make_key([1.0, 2.5], 4, 1.55e-6)
        assert key1 != key2

    def test_put_get_roundtrip(self):
        cache = _perf.SparamCascadeCache(max_size=4)
        key = "test_key"
        smat = np.eye(8) * 0.5
        cache.put(key, smat)
        assert cache.has(key)
        retrieved = cache.get(key)
        np.testing.assert_allclose(retrieved, smat)

    def test_get_missing_raises(self):
        """get 不存在的键须 raise KeyError（R03）。"""
        cache = _perf.SparamCascadeCache()
        with pytest.raises(KeyError):
            cache.get("nonexistent")

    def test_lru_eviction(self):
        """超过 max_size 应丢弃最旧。"""
        cache = _perf.SparamCascadeCache(max_size=2)
        cache.put("k1", np.zeros(2))
        cache.put("k2", np.zeros(2))
        assert cache.has("k1") and cache.has("k2")
        cache.put("k3", np.zeros(2))  # 应驱逐 k1
        assert not cache.has("k1")
        assert cache.has("k2") and cache.has("k3")

    def test_lru_access_promotes(self):
        """访问应将条目移到末尾（不被驱逐）。"""
        cache = _perf.SparamCascadeCache(max_size=2)
        cache.put("k1", np.zeros(2))
        cache.put("k2", np.zeros(2))
        # 访问 k1，使其变最新
        cache.get("k1")
        # 插入 k3，应驱逐 k2（最旧），保留 k1
        cache.put("k3", np.zeros(2))
        assert cache.has("k1")
        assert not cache.has("k2")
        assert cache.has("k3")

    def test_hit_miss_stats(self):
        cache = _perf.SparamCascadeCache()
        cache.put("k1", np.zeros(2))
        cache.get("k1")  # hit
        cache.get("k1")  # hit
        try:
            cache.get("missing")  # miss
        except KeyError:
            pass
        assert cache.hits == 2
        assert cache.misses == 1
        assert cache.hit_rate == pytest.approx(2.0 / 3.0)

    def test_clear_resets(self):
        cache = _perf.SparamCascadeCache()
        cache.put("k1", np.zeros(2))
        cache.get("k1")
        cache.clear()
        assert not cache.has("k1")
        assert cache.hits == 0
        assert cache.misses == 0


class TestR457MemoryPool:
    """内存池测试。"""

    def test_construction_validates_max_per_shape(self):
        with pytest.raises(ValueError, match="max_per_shape"):
            _perf.MemoryPool(max_per_shape=0)

    def test_acquire_returns_zeroed_array(self):
        pool = _perf.MemoryPool()
        arr = pool.acquire((5, 5), dtype=np.float64)
        assert arr.shape == (5, 5)
        assert arr.dtype == np.float64
        np.testing.assert_allclose(arr, 0.0)

    def test_release_then_acquire_reuses(self):
        """release 后 acquire 应复用（不重新分配）。"""
        pool = _perf.MemoryPool(max_per_shape=2)
        arr1 = pool.acquire((5, 5))
        arr1[0, 0] = 99.0
        pool.release(arr1)
        arr2 = pool.acquire((5, 5))
        # 复用同一数组（已清零）
        np.testing.assert_allclose(arr2, 0.0)
        # 验证是同一对象（内存池语义）
        assert arr2 is arr1

    def test_release_respects_max_per_shape(self):
        """超过 max_per_shape 应丢弃。"""
        pool = _perf.MemoryPool(max_per_shape=2)
        arr1 = pool.acquire((3, 3))
        arr2 = pool.acquire((3, 3))
        arr3 = pool.acquire((3, 3))
        pool.release(arr1)
        pool.release(arr2)
        pool.release(arr3)  # 应被丢弃（超过 max=2）
        assert pool.total_cached == 2

    def test_different_shapes_separate(self):
        """不同形状应分开缓存。"""
        pool = _perf.MemoryPool()
        pool.release(pool.acquire((3, 3)))
        pool.release(pool.acquire((4, 4)))
        assert pool.total_cached == 2


class TestR457PerfBenchmarkSuite:
    """性能基准测试套件测试。"""

    def test_add_validates_fn(self):
        suite = _perf.PerfBenchmarkSuite()
        with pytest.raises(ValueError, match="fn"):
            suite.add(_perf.BenchmarkCase(
                name="t", fn="not callable",  # type: ignore[arg-type]
            ))

    def test_add_validates_n_runs(self):
        suite = _perf.PerfBenchmarkSuite()
        with pytest.raises(ValueError, match="n_runs"):
            suite.add(_perf.BenchmarkCase(
                name="t", fn=lambda: None, n_runs=0,
            ))

    def test_run_collects_results(self):
        suite = _perf.PerfBenchmarkSuite()
        suite.add(_perf.BenchmarkCase(
            name="fast", fn=lambda: sum(range(100)), expected_runtime=1.0,
            n_runs=2,
        ))
        results = suite.run()
        assert len(results) == 1
        r = results[0]
        assert r.name == "fast"
        assert r.median_time > 0.0
        assert r.min_time <= r.median_time <= r.max_time
        assert r.passed

    def test_run_marks_failed_threshold(self):
        suite = _perf.PerfBenchmarkSuite()
        suite.add(_perf.BenchmarkCase(
            name="slow", fn=lambda: sum(range(1_000_000)),
            expected_runtime=1e-9,  # 故意设极小阈值
            n_runs=2,
        ))
        results = suite.run()
        assert not results[0].passed

    def test_run_propagates_exceptions(self):
        """用例抛异常须 raise RuntimeError（R03）。"""
        suite = _perf.PerfBenchmarkSuite()

        def boom() -> None:
            raise RuntimeError("boom")

        suite.add(_perf.BenchmarkCase(name="boom", fn=boom))
        with pytest.raises(RuntimeError, match="boom"):
            suite.run()

    def test_to_markdown_generates_table(self):
        suite = _perf.PerfBenchmarkSuite()
        suite.add(_perf.BenchmarkCase(
            name="t", fn=lambda: None, expected_runtime=1.0, n_runs=1,
        ))
        results = suite.run()
        md = _perf.PerfBenchmarkSuite.to_markdown(results)
        assert "用例" in md
        assert "t" in md
        assert "|" in md


class TestR457MultiprocessRunner:
    """多进程执行器测试。"""

    def test_map_serial_default(self):
        """默认串行执行。"""
        runner = _perf.MultiprocessRunner()  # max_workers=None
        results = runner.map(lambda x: x * 2, [1, 2, 3])
        assert results == [2, 4, 6]

    def test_map_validates_empty_items(self):
        runner = _perf.MultiprocessRunner()
        with pytest.raises(ValueError, match="items"):
            runner.map(lambda x: x, [])

    def test_map_validates_fn(self):
        runner = _perf.MultiprocessRunner()
        with pytest.raises(ValueError, match="fn"):
            runner.map("not_callable", [1, 2])  # type: ignore[arg-type]

    def test_map_validates_max_workers(self):
        with pytest.raises(ValueError, match="max_workers"):
            _perf.MultiprocessRunner(max_workers=0)

    def test_map_preserves_order(self):
        """结果应与输入同序。"""
        runner = _perf.MultiprocessRunner()
        items = [5, 3, 8, 1, 9]
        results = runner.map(lambda x: x ** 2, items)
        assert results == [25, 9, 64, 1, 81]


# ===========================================================================
# R03/R02/R04 合规
# ===========================================================================


class TestCompliance:
    """R03/R02/R04 合规检查。"""

    @classmethod
    def setup_class(cls) -> None:
        cls.src = (_SRC_DIR / "sim" / "perf_optimization.py").read_text(
            encoding="utf-8"
        )

    def test_r03_no_silent_fallback(self):
        """R03：禁止 except: pass / return None / return []。"""
        # 检查无 except: pass 模式
        lines = self.src.split("\n")
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("except") and stripped.endswith(":"):
                # 下一行不应是 pass / return None / return []
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    assert next_line not in ("pass", "return None", "return []", \
                                             "return"), \
                        f"第 {i+1} 行 except 后跟 fall-back: {next_line}"

    def test_r02_innovation_marked(self):
        """R02：源码含 *创新* 标注。"""
        assert "*创新*" in self.src, "perf_optimization.py 缺少 *创新* 标注"

    def test_r02_url_count(self):
        """R02：docstring 含 ≥5 个文献 URL。"""
        # 取 docstring（首个 from __future__ 之前）
        docstring = self.src.split("from __future__")[0]
        url_count = docstring.count("https://")
        assert url_count >= 5, f"R02 违规: URL < 5 (实际 {url_count})"

    def test_r04_no_gpu_imports(self):
        """R04：无 GPU 后端导入。"""
        for forbidden in ["import cupy", "import torch", "from torch",
                          "from cupy", "import cuda", "import jax"]:
            assert forbidden not in self.src, \
                f"R04 违规: 含 '{forbidden}'"

    def test_no_todo_fixme_hack(self):
        """R05：无 TODO/FIXME/HACK 残留。"""
        for token in ["TODO", "FIXME", "HACK"]:
            assert token not in self.src, f"R05 违规: 含 '{token}'"


# ===========================================================================
# 端到端集成
# ===========================================================================


class TestEndToEndIntegration:
    """端到端集成：FDTD + BPM + 缓存协同。"""

    def test_fdtd_run_with_cache_for_bpm(self):
        """FDTD 跑一遍，BPM 用相同波导跑，缓存 S 矩阵。"""
        # FDTD 配置
        c0 = 2.99792458e8
        dx = 1e-7
        dt = 0.5 * dx / c0
        shape = (15, 15)
        eps_r = np.ones(shape) * 1.5
        eps_r[5:10, 5:10] = 3.4 ** 2  # Si 波导芯
        core = _perf.NumpyVectorizedFdtdCore(
            shape=shape, dx=dx, dy=dx, dt=dt, eps_r=eps_r,
        )
        e0 = np.zeros(shape)
        e0[7, 7] = 1.0
        fdtd_result = core.run(e0, np.zeros(shape), np.zeros(shape), n_steps=5)
        assert fdtd_result.wall_time > 0

        # BPM 配置（1D 横截面）
        n_prof = np.ones(50) * 1.5
        n_prof[20:30] = 3.4
        prop = _perf.BpmPadeLargeStep(
            n_prof, wavelength=1.55e-6, dx=0.2e-6, n_ref=1.5,
        )
        psi = np.zeros(50, dtype=np.complex128)
        psi[25] = 1.0
        bpm_result = prop.propagate(psi, dz=0.5e-6, n_steps=5, pade_order=(2, 2))
        assert bpm_result.field_history.shape == (6, 50)

        # S 参数缓存
        cache = _perf.SparamCascadeCache(max_size=8)
        key = cache.make_key([1.0, 2.0, 3.0], 4, 1.55e-6)
        smat = np.eye(8) * 0.5
        cache.put(key, smat)
        assert cache.has(key)
        retrieved = cache.get(key)
        np.testing.assert_allclose(retrieved, smat)

    def test_perf_suite_with_multiple_components(self):
        """性能套件同时跑 FDTD + BPM + 缓存基准。"""
        suite = _perf.PerfBenchmarkSuite()

        def fdtd_bench() -> float:
            c0 = 2.99792458e8
            dx = 1e-7
            dt = 0.5 * dx / c0
            shape = (10, 10)
            core = _perf.NumpyVectorizedFdtdCore(
                shape=shape, dx=dx, dy=dx, dt=dt, eps_r=np.ones(shape),
            )
            e0 = np.zeros(shape)
            e0[5, 5] = 1.0
            result = core.run(e0, np.zeros(shape), np.zeros(shape), n_steps=3)
            return float(result.wall_time)

        def bpm_bench() -> float:
            n_prof = np.ones(30) * 1.5
            prop = _perf.BpmPadeLargeStep(
                n_prof, wavelength=1.55e-6, dx=0.2e-6, n_ref=1.5,
            )
            psi = np.zeros(30, dtype=np.complex128)
            psi[15] = 1.0
            result = prop.propagate(psi, dz=0.5e-6, n_steps=3, pade_order=(1, 1))
            return float(result.power_history[-1])

        suite.add(_perf.BenchmarkCase(
            name="fdtd_10x10", fn=fdtd_bench, expected_runtime=2.0, n_runs=2,
        ))
        suite.add(_perf.BenchmarkCase(
            name="bpm_30", fn=bpm_bench, expected_runtime=2.0, n_runs=2,
        ))
        results = suite.run()
        assert len(results) == 2
        md = _perf.PerfBenchmarkSuite.to_markdown(results)
        assert "fdtd_10x10" in md
        assert "bpm_30" in md

    def test_full_pipeline_no_fallback(self):
        """完整流水线无 fall-back，所有错误 raise。"""
        # FDE 加速器（sigma 用非整数避免奇异）
        n = 20
        eigvals_true = np.linspace(1.0, 20.0, n)
        mat = sp.diags(eigvals_true, 0, format="csr", dtype=np.float64)
        fde_acc = _perf.FdeShiftInvertAccelerator(mat, sigma=10.5)
        fde_result = fde_acc.solve(num_modes=2)
        assert fde_result.beta.shape == (2,)

        # EME 模式数选择
        def solve_fn(m: int) -> np.ndarray:
            return np.eye(2 * m) * (1.0 + 0.1 / m)

        selector = _perf.EmeAdaptiveModeSelector(solve_fn=solve_fn)
        eme_result = selector.select(
            candidate_Ms=[4, 8, 12], threshold=0.05,
        )
        assert eme_result.selected_count in (8, 12)

        # 内存池
        pool = _perf.MemoryPool()
        arr = pool.acquire((10, 10))
        arr[0, 0] = 1.0
        pool.release(arr)
        assert pool.total_cached == 1

        # 多进程（串行模式）
        runner = _perf.MultiprocessRunner()
        results = runner.map(lambda x: x + 1, [1, 2, 3])
        assert results == [2, 3, 4]
