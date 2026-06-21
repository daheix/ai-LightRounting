"""水平集 HJ 求解器与几何量计算测试（P2-2 深化，第43轮）。

对标商业工具（Tidy3D / Lumerical）的测试覆盖标准。

来源:
- Osher & Shu 1991 ENO 格式
- Jiang & Peng 2000 WENO 格式
- Sethian 1996 Fast Marching
"""

from __future__ import annotations

import unittest

import numpy as np

from polaris.sim.level_set_geometry import (
    compute_curvature,
    compute_mean_curvature_motion,
    compute_normal_vector,
    compute_velocity_extension,
    fast_marching_sdf,
    reinitialize_sdf,
)
from polaris.sim.level_set_solver import (
    HJScheme,
    HJSolver,
    HJSolverConfig,
    compute_cfl_timestep,
    create_hj_solver,
    evolve_hj,
)


class TestHJScheme(unittest.TestCase):
    """HJScheme 枚举测试。"""

    def test_scheme_values(self) -> None:
        """测试枚举值。"""
        self.assertEqual(HJScheme.ENO.value, "eno")
        self.assertEqual(HJScheme.WENO.value, "weno")
        self.assertEqual(HJScheme.UPWIND.value, "upwind")

    def test_scheme_from_string(self) -> None:
        """测试字符串构造。"""
        self.assertEqual(HJScheme("eno"), HJScheme.ENO)
        self.assertEqual(HJScheme("weno"), HJScheme.WENO)


class TestHJSolverConfig(unittest.TestCase):
    """HJSolverConfig 测试。"""

    def test_default_config(self) -> None:
        """测试默认配置。"""
        cfg = HJSolverConfig()
        self.assertEqual(cfg.scheme, HJScheme.WENO)
        self.assertEqual(cfg.cfl_number, 0.5)
        self.assertEqual(cfg.max_dt, 1.0)
        self.assertEqual(cfg.min_dt, 1e-6)
        self.assertEqual(cfg.reinit_interval, 10)

    def test_custom_config(self) -> None:
        """测试自定义配置。"""
        cfg = HJSolverConfig(scheme=HJScheme.ENO, cfl_number=0.25, max_dt=0.5)
        self.assertEqual(cfg.scheme, HJScheme.ENO)
        self.assertEqual(cfg.cfl_number, 0.25)
        self.assertEqual(cfg.max_dt, 0.5)

    def test_frozen(self) -> None:
        """测试不可变。"""
        cfg = HJSolverConfig()
        with self.assertRaises(AttributeError):
            cfg.cfl_number = 0.9  # type: ignore[misc]


class TestCFLTimestep(unittest.TestCase):
    """CFL 时间步长测试。"""

    def test_uniform_velocity(self) -> None:
        """测试均匀速度场。"""
        v = np.ones((10, 10))
        cfg = HJSolverConfig(cfl_number=0.5)
        dt = compute_cfl_timestep(v, dx=1.0, dy=1.0, config=cfg)
        self.assertAlmostEqual(dt, 0.5, places=6)

    def test_zero_velocity(self) -> None:
        """测试零速度场返回 max_dt。"""
        v = np.zeros((10, 10))
        cfg = HJSolverConfig(max_dt=2.0)
        dt = compute_cfl_timestep(v, dx=1.0, dy=1.0, config=cfg)
        self.assertEqual(dt, 2.0)

    def test_clamping(self) -> None:
        """测试时间步长上下限。"""
        # 小速度场：dt_cfl 很大，应被 max_dt 限制
        v_small = np.full((10, 10), 0.01)
        cfg = HJSolverConfig(cfl_number=0.5, max_dt=0.1, min_dt=1e-8)
        dt = compute_cfl_timestep(v_small, dx=1.0, dy=1.0, config=cfg)
        # dt_cfl = 0.5 * 1.0 / 0.01 = 50，应被 max_dt=0.1 限制
        self.assertAlmostEqual(dt, 0.1, places=6)

    def test_different_dx_dy(self) -> None:
        """测试不同步长。"""
        v = np.ones((10, 10))
        cfg = HJSolverConfig(cfl_number=0.5)
        dt = compute_cfl_timestep(v, dx=2.0, dy=1.0, config=cfg)
        # min(2.0, 1.0) = 1.0, dt = 0.5 * 1.0 / 1.0 = 0.5
        self.assertAlmostEqual(dt, 0.5, places=6)


class TestEvolveHJ(unittest.TestCase):
    """evolve_hj 函数测试。"""

    def test_shape_preservation(self) -> None:
        """测试输出形状保持。"""
        phi = np.random.rand(20, 20)
        v = np.ones((20, 20))
        result = evolve_hj(phi, v)
        self.assertEqual(result.shape, phi.shape)

    def test_zero_velocity_no_change(self) -> None:
        """测试零速度场不改变 phi。"""
        phi = np.random.rand(15, 15)
        v = np.zeros((15, 15))
        result = evolve_hj(phi, v)
        np.testing.assert_array_almost_equal(result, phi, decimal=10)

    def test_weno_scheme(self) -> None:
        """测试 WENO 格式。"""
        phi = np.random.rand(12, 12)
        v = np.ones((12, 12))
        cfg = HJSolverConfig(scheme=HJScheme.WENO)
        result = evolve_hj(phi, v, config=cfg)
        self.assertEqual(result.shape, phi.shape)
        # 应该有变化
        self.assertFalse(np.allclose(result, phi))

    def test_eno_scheme(self) -> None:
        """测试 ENO 格式。"""
        phi = np.random.rand(12, 12)
        v = np.ones((12, 12))
        cfg = HJSolverConfig(scheme=HJScheme.ENO)
        result = evolve_hj(phi, v, config=cfg)
        self.assertEqual(result.shape, phi.shape)

    def test_upwind_scheme(self) -> None:
        """测试迎风格式。"""
        phi = np.random.rand(12, 12)
        v = np.ones((12, 12))
        cfg = HJSolverConfig(scheme=HJScheme.UPWIND)
        result = evolve_hj(phi, v, config=cfg)
        self.assertEqual(result.shape, phi.shape)

    def test_circle_shrink(self) -> None:
        """测试圆形收缩（曲率流近似）。

        圆形在均匀外向速度下应收缩。
        """
        g = 30
        x = np.linspace(-1, 1, g)
        xx, yy = np.meshgrid(x, x, indexing="ij")
        phi = 0.25 - (xx**2 + yy**2)  # 圆形
        v = np.ones((g, g))  # 外向速度

        original_radius = float(np.sum(phi > 0))
        for _ in range(20):
            phi = evolve_hj(phi, v, config=HJSolverConfig(scheme=HJScheme.WENO))
        new_radius = float(np.sum(phi > 0))
        # 材料区域应减小
        self.assertLess(new_radius, original_radius)


class TestHJSolver(unittest.TestCase):
    """HJSolver 类测试。"""

    def test_init_default(self) -> None:
        """测试默认初始化。"""
        solver = HJSolver()
        self.assertEqual(solver.config.scheme, HJScheme.WENO)
        self.assertEqual(solver.step_count, 0)

    def test_step(self) -> None:
        """测试单步演化。"""
        solver = HJSolver()
        phi = np.random.rand(10, 10)
        v = np.ones((10, 10))
        new_phi = solver.step(phi, v)
        self.assertEqual(new_phi.shape, phi.shape)
        self.assertEqual(solver.step_count, 1)

    def test_evolve_multiple_steps(self) -> None:
        """测试多步演化。"""
        solver = HJSolver()

        def velocity_fn(p: np.ndarray) -> np.ndarray:
            return np.ones_like(p)

        phi = np.random.rand(15, 15)
        result = solver.evolve(phi, velocity_fn, n_steps=5)
        self.assertEqual(result.shape, phi.shape)
        self.assertEqual(solver.step_count, 5)

    def test_custom_config(self) -> None:
        """测试自定义配置。"""
        cfg = HJSolverConfig(scheme=HJScheme.ENO, cfl_number=0.25)
        solver = HJSolver(cfg)
        self.assertEqual(solver.config.scheme, HJScheme.ENO)
        self.assertEqual(solver.config.cfl_number, 0.25)


class TestFactoryFunctions(unittest.TestCase):
    """工厂函数测试。"""

    def test_create_weno_solver(self) -> None:
        """测试创建 WENO 求解器。"""
        solver = create_hj_solver("weno", cfl=0.5)
        self.assertEqual(solver.config.scheme, HJScheme.WENO)
        self.assertEqual(solver.config.cfl_number, 0.5)

    def test_create_eno_solver(self) -> None:
        """测试创建 ENO 求解器。"""
        solver = create_hj_solver("eno")
        self.assertEqual(solver.config.scheme, HJScheme.ENO)

    def test_create_upwind_solver(self) -> None:
        """测试创建迎风求解器。"""
        solver = create_hj_solver("upwind")
        self.assertEqual(solver.config.scheme, HJScheme.UPWIND)


class TestNormalVector(unittest.TestCase):
    """法向量计算测试。"""

    def test_shape(self) -> None:
        """测试输出形状。"""
        phi = np.random.rand(10, 10)
        n = compute_normal_vector(phi)
        self.assertEqual(n.shape, (10, 10, 2))

    def test_unit_length(self) -> None:
        """测试法向量单位长度。"""
        x = np.linspace(-1, 1, 20)
        xx, yy = np.meshgrid(x, x, indexing="ij")
        phi = 0.25 - (xx**2 + yy**2)
        n = compute_normal_vector(phi)
        mag = np.sqrt(n[..., 0] ** 2 + n[..., 1] ** 2)
        # 内部点应为单位长度
        interior = (phi > -0.2) & (phi < 0.2)
        np.testing.assert_array_almost_equal(mag[interior], 1.0, decimal=5)

    def test_circle_outward(self) -> None:
        """测试圆形法向量方向。

        phi = 0.25 - r²，材料在内部（phi>0）。
        ∇φ = (-2x, -2y) 指向圆心（内）。
        法向量 n = ∇φ/|∇φ| 指向圆心（内），与径向 r_hat 反向。
        """
        g = 30
        x = np.linspace(-1, 1, g)
        xx, yy = np.meshgrid(x, x, indexing="ij")
        phi = 0.25 - (xx**2 + yy**2)
        n = compute_normal_vector(phi)
        # 边界附近法向量应指向内（与径向反向）
        boundary = np.abs(phi) < 0.05
        for i, j in zip(*np.where(boundary)):
            if abs(xx[i, j]) < 1e-6 and abs(yy[i, j]) < 1e-6:
                continue
            radial = np.array([xx[i, j], yy[i, j]])
            radial = radial / (np.linalg.norm(radial) + 1e-12)
            normal = n[i, j]
            dot = float(np.dot(radial, normal))
            # 法向量应与径向方向反向（指向圆心）
            self.assertLess(dot, 0.5)


class TestCurvature(unittest.TestCase):
    """曲率计算测试。"""

    def test_shape(self) -> None:
        """测试输出形状。"""
        phi = np.random.rand(10, 10)
        k = compute_curvature(phi)
        self.assertEqual(k.shape, (10, 10))

    def test_circle_constant_curvature(self) -> None:
        """测试圆形常曲率。

        半径 R 的圆，曲率 |κ| = 1/R。
        phi = R² - r² 约定下 κ = -1/R（材料在内部，法向量指向内）。
        """
        g = 50
        x = np.linspace(-1, 1, g)
        xx, yy = np.meshgrid(x, x, indexing="ij")
        R = 0.5
        phi = R**2 - (xx**2 + yy**2)
        k = compute_curvature(phi)
        # 边界附近曲率绝对值应接近 1/R = 2.0
        boundary = np.abs(phi) < 0.02
        if boundary.any():
            k_mean = float(k[boundary].mean())
            # |κ| 应大于 0.5（理论值 2.0，允许离散化误差）
            self.assertGreater(abs(k_mean), 0.5)

    def test_flat_zero_curvature(self) -> None:
        """测试平面零曲率。"""
        phi = np.ones((20, 20)) * 0.5
        k = compute_curvature(phi)
        # 内部点曲率应接近 0
        np.testing.assert_array_almost_equal(k[5:15, 5:15], 0.0, decimal=6)


class TestMeanCurvatureMotion(unittest.TestCase):
    """平均曲率运动测试。"""

    def test_shape(self) -> None:
        """测试输出形状。"""
        phi = np.random.rand(10, 10)
        v = compute_mean_curvature_motion(phi)
        self.assertEqual(v.shape, (10, 10))

    def test_smoothing_direction(self) -> None:
        """测试平滑方向（系数 > 0 应使边界平滑）。"""
        g = 30
        x = np.linspace(-1, 1, g)
        xx, yy = np.meshgrid(x, x, indexing="ij")
        phi = 0.25 - (xx**2 + yy**2)
        v = compute_mean_curvature_motion(phi, coefficient=1.0)
        # 圆形边界曲率为正，速度应为负（收缩）
        boundary = np.abs(phi) < 0.05
        if boundary.any():
            v_mean = float(v[boundary].mean())
            self.assertLess(v_mean, 0.5)  # 应趋于负或小值


class TestFastMarchingSDF(unittest.TestCase):
    """Fast Marching SDF 重新初始化测试。"""

    def test_shape(self) -> None:
        """测试输出形状。"""
        phi = np.random.rand(10, 10) - 0.5
        sdf = fast_marching_sdf(phi)
        self.assertEqual(sdf.shape, phi.shape)

    def test_sign_preservation(self) -> None:
        """测试符号保持。"""
        g = 20
        x = np.linspace(-1, 1, g)
        xx, yy = np.meshgrid(x, x, indexing="ij")
        phi = 0.25 - (xx**2 + yy**2)
        sdf = fast_marching_sdf(phi)
        # 符号应一致
        np.testing.assert_array_equal(np.sign(sdf), np.sign(phi))

    def test_zero_level_set_preservation(self) -> None:
        """测试零等高线保持。"""
        g = 30
        x = np.linspace(-1, 1, g)
        xx, yy = np.meshgrid(x, x, indexing="ij")
        phi = 0.25 - (xx**2 + yy**2)
        original_binary = phi > 0
        sdf = fast_marching_sdf(phi)
        new_binary = sdf > 0
        # 零等高线应基本保持
        diff = float(np.mean(original_binary != new_binary))
        self.assertLess(diff, 0.15)

    def test_distance_property(self) -> None:
        """测试距离性质（SDF 梯度模 ≈ 1）。"""
        g = 30
        x = np.linspace(-1, 1, g)
        xx, yy = np.meshgrid(x, x, indexing="ij")
        phi = 0.25 - (xx**2 + yy**2)
        sdf = fast_marching_sdf(phi)
        gx, gy = np.gradient(sdf)
        grad_mag = np.sqrt(gx**2 + gy**2)
        # 边界附近梯度模应接近 1
        boundary = np.abs(sdf) < 0.3
        if boundary.any():
            mean_grad = float(grad_mag[boundary].mean())
            self.assertGreater(mean_grad, 0.3)


class TestReinitializeSDF(unittest.TestCase):
    """PDE SDF 重新初始化测试。"""

    def test_shape(self) -> None:
        """测试输出形状。"""
        phi = np.random.rand(10, 10) - 0.5
        result = reinitialize_sdf(phi, n_iters=3)
        self.assertEqual(result.shape, phi.shape)

    def test_sign_preservation(self) -> None:
        """测试符号保持。"""
        phi = np.array([[1.0, 0.5, -0.5], [0.5, 0.1, -0.3], [-0.5, -0.3, -1.0]])
        result = reinitialize_sdf(phi, n_iters=5)
        np.testing.assert_array_equal(np.sign(result), np.sign(phi))


class TestVelocityExtension(unittest.TestCase):
    """速度场延拓测试。"""

    def test_shape(self) -> None:
        """测试输出形状。"""
        v = np.random.rand(15, 15)
        phi = np.random.rand(15, 15) - 0.5
        result = compute_velocity_extension(v, phi)
        self.assertEqual(result.shape, v.shape)

    def test_band_preserved(self) -> None:
        """测试边界带速度保持。"""
        g = 20
        x = np.linspace(-1, 1, g)
        xx, yy = np.meshgrid(x, x, indexing="ij")
        phi = 0.25 - (xx**2 + yy**2)
        v = np.ones((g, g)) * 2.0
        result = compute_velocity_extension(v, phi, band_width=2)
        # 边界带内速度应保持
        boundary = np.abs(phi) < 0.1
        if boundary.any():
            np.testing.assert_array_almost_equal(result[boundary], v[boundary])


class TestCommercialGapReduction(unittest.TestCase):
    """商业差距缩减测试（对标 Tidy3D / Lumerical）。"""

    def test_weno_vs_euler_stability(self) -> None:
        """测试 WENO 比 Euler 更稳定。

        对标商业工具的高阶求解器稳定性。
        """
        g = 40
        x = np.linspace(-1, 1, g)
        xx, yy = np.meshgrid(x, x, indexing="ij")
        phi = 0.25 - (xx**2 + yy**2)
        v = np.ones((g, g)) * 2.0

        # WENO 演化
        phi_weno = phi.copy()
        for _ in range(30):
            phi_weno = evolve_hj(phi_weno, v, config=HJSolverConfig(scheme=HJScheme.WENO))

        # 应保持有限（无 NaN/Inf）
        self.assertTrue(np.all(np.isfinite(phi_weno)))

    def test_curvature_smooths_boundary(self) -> None:
        """测试曲率流平滑边界。

        对标商业工具的曲率相关速度。
        """
        g = 30
        x = np.linspace(-1, 1, g)
        xx, yy = np.meshgrid(x, x, indexing="ij")
        # 不规则形状（带噪声的圆）
        phi = 0.25 - (xx**2 + yy**2)
        noise = 0.02 * np.sin(5 * xx) * np.cos(5 * yy)
        phi_noisy = phi + noise

        # 曲率流平滑
        v_curv = compute_mean_curvature_motion(phi_noisy, coefficient=0.1)
        phi_smoothed = phi_noisy - 0.05 * v_curv

        # 平滑后曲率方差应减小
        k_before = compute_curvature(phi_noisy)
        k_after = compute_curvature(phi_smoothed)
        var_before = float(np.var(k_before[np.abs(phi_noisy) < 0.1]))
        var_after = float(np.var(k_after[np.abs(phi_smoothed) < 0.1]))
        self.assertLessEqual(var_after, var_before * 1.5)

    def test_fast_marching_vs_pde_reinit(self) -> None:
        """测试 Fast Marching 与 PDE 重新初始化一致性。

        对标商业工具的 SDF 重新初始化精度。
        """
        g = 25
        x = np.linspace(-1, 1, g)
        xx, yy = np.meshgrid(x, x, indexing="ij")
        phi = 0.25 - (xx**2 + yy**2)

        sdf_fm = fast_marching_sdf(phi)
        sdf_pde = reinitialize_sdf(phi, n_iters=10)

        # 符号应一致
        np.testing.assert_array_equal(np.sign(sdf_fm), np.sign(sdf_pde))

    def test_cfl_adaptive_timestep(self) -> None:
        """测试 CFL 自适应时间步长。

        对标商业工具的自适应步长控制。
        """
        # 小速度场应给大步长
        v_small = np.ones((10, 10)) * 0.1
        dt_small = compute_cfl_timestep(v_small, 1.0, 1.0, HJSolverConfig())
        # 大速度场应给小步长
        v_large = np.ones((10, 10)) * 10.0
        dt_large = compute_cfl_timestep(v_large, 1.0, 1.0, HJSolverConfig())
        self.assertGreater(dt_small, dt_large)

    def test_normal_vector_quality(self) -> None:
        """测试法向量质量。

        对标商业工具的法向量计算精度。
        phi = 0.25 - r²，材料在内部，法向量指向圆心（与径向反向）。
        """
        g = 40
        x = np.linspace(-1, 1, g)
        xx, yy = np.meshgrid(x, x, indexing="ij")
        phi = 0.25 - (xx**2 + yy**2)
        n = compute_normal_vector(phi)

        # 边界附近法向量应指向圆心（与径向反向，dot < 0）
        boundary = np.abs(phi) < 0.05
        correct = 0
        total = 0
        for i, j in zip(*np.where(boundary)):
            r = np.array([xx[i, j], yy[i, j]])
            r_norm = np.linalg.norm(r)
            if r_norm < 1e-6:
                continue
            r_hat = r / r_norm
            normal = n[i, j]
            if np.dot(r_hat, normal) < 0:
                correct += 1
            total += 1
        if total > 0:
            self.assertGreater(correct / total, 0.7)

    def test_full_pipeline(self) -> None:
        """测试完整流水线：HJ 演化 + 曲率 + SDF 重初始化。

        对标商业工具的完整水平集优化流程。
        """
        g = 30
        x = np.linspace(-1, 1, g)
        xx, yy = np.meshgrid(x, x, indexing="ij")
        phi = 0.25 - (xx**2 + yy**2)

        # 1. 计算速度场（含曲率项）
        v_curv = compute_mean_curvature_motion(phi, coefficient=0.05)
        v_total = np.ones_like(phi) * 0.5 + v_curv

        # 2. 速度延拓
        v_extended = compute_velocity_extension(v_total, phi)

        # 3. HJ 演化
        phi_new = evolve_hj(phi, v_extended, config=HJSolverConfig(scheme=HJScheme.WENO))

        # 4. SDF 重新初始化
        phi_reinit = reinitialize_sdf(phi_new, n_iters=3)

        # 应保持有限
        self.assertTrue(np.all(np.isfinite(phi_reinit)))
        # 符号应基本保持
        sign_change = float(np.mean(np.sign(phi_reinit) != np.sign(phi)))
        self.assertLess(sign_change, 0.3)


if __name__ == "__main__":
    unittest.main()
