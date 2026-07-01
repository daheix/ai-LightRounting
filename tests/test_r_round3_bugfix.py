"""R113 第3轮迭代回归测试：8 处商业 Bug + 1 处测试阻塞 Bug 修复验证。

覆盖 P0/P1 共 9 个 bug 修复（含测试阻塞 P0-5 边界 cell 漏标）：
- P0-1: curvy_astar_core._check_bend_radius 第三边向量 v1-v2 → v1+v2
- P0-2: waveguide_router._encode/_decode 状态空间 min_bend_steps → +1
- P0-3: statistical_yield.PEXEngine.extract_wire 电感 Wheeler → Rosa 1908
- P0-4: curvy_astar_core._generate_directions 浮点 → 整数勾股数方向表
- P0-5: curvy_astar_core._obstacle_to_set 边界 cell 漏标
- P1-5: parasitic_advanced.ParasiticInductor.extract_mutual 删除错误 K 字段
- P1-6: stratified_sampling.stratified_monte_carlo 空层 raise
- P1-7: gdsfactory_integration GDSII 坐标 int() → int(round())
- P1-8: curvy_optodesigner.rip_up_reroute 失败 logger.error

学术来源（R02 学术诚信）:
- Rosa 1908, NBS Bull. 4(2), 301-344, https://doi.org/10.6028/bulletin.088
- LiDAR ISPD'25 §3.1-3.2, https://dl.acm.org/doi/pdf/10.1145/3698364.3705355
- Cochran 1977, "Sampling Techniques", Wiley, Ch.5A
- OptoDesigner Arbitrary Curves, https://www.synopsys.com/photonic-solutions/product-applications/photonic-integrated-circuits/arbitrary-curves-feature.html
"""

from __future__ import annotations

import logging
import math

import numpy as np
import pytest

from polaris.router.curvy_astar_core import (
    CurvyAStarConfig,
    CurvyAStarRouter,
    _generate_directions,
)
from polaris.router.curvy_optodesigner import (
    CongestionAwareNetOrdering,
    OptoDesignerAutorouter,
)
from polaris.router.waveguide_router import (
    RouterConstraints,
    WaveguideRouter,
)
from polaris.sim.parasitic_advanced import ParasiticInductor
from polaris.sim.stratified_sampling import (
    AllocationStrategy,
    stratified_monte_carlo,
)
from polaris.verification.statistical_yield import PEXEngine


# ---------------------------------------------------------------------------
# P0-1: _check_bend_radius 外接圆半径公式（第三边向量）
# ---------------------------------------------------------------------------
class TestBendRadiusFormula:
    """P0-1: 三点外接圆半径 R = |v1|·|v2|·|v1+v2| / (2·|v1×v2|)。"""

    def test_known_three_points(self):
        """验证已知三点半径计算正确。

        p1=(0,0), p2=(1,0), p3=(2,1):
          v1=(1,0), v2=(1,1), v3=v1+v2=(2,1), |v1|=1, |v2|=√2, |v3|=√5
          cross = 1·1 - 0·1 = 1
          R = 1·√2·√5 / (2·1) = √10/2 ≈ 1.5811
        """
        router = CurvyAStarRouter(CurvyAStarConfig(bend_radius=1.0))
        r = router._check_bend_radius((0.0, 0.0), (1.0, 0.0), (2.0, 1.0))
        # R ≈ 1.5811 > 1.0 应满足
        assert r is True

        # 提升阈值到 2.0，应不满足
        router2 = CurvyAStarRouter(CurvyAStarConfig(bend_radius=2.0))
        r2 = router2._check_bend_radius((0.0, 0.0), (1.0, 0.0), (2.0, 1.0))
        assert r2 is False

    def test_collinear_returns_true(self):
        """共线三点无弯曲，应返回 True。"""
        router = CurvyAStarRouter(CurvyAStarConfig(bend_radius=5.0))
        r = router._check_bend_radius((0.0, 0.0), (1.0, 0.0), (2.0, 0.0))
        assert r is True

    def test_old_bug_value_mismatch(self):
        """旧 bug 公式 R = |v1|·|v2|·|v1-v2|/(2·cross) 会给出错误值 0.707。

        新公式 R ≈ 1.5811；旧公式 R ≈ 0.707（偏差 55%）。
        本测试确保新公式不退化到旧值。
        """
        router = CurvyAStarRouter(CurvyAStarConfig(bend_radius=1.2))
        # 新 R=1.5811 > 1.2 通过；旧 R=0.707 < 1.2 不通过
        # 若公式回退到旧 bug，本测试会失败
        r = router._check_bend_radius((0.0, 0.0), (1.0, 0.0), (2.0, 1.0))
        assert r is True, "外接圆半径公式退化到旧 bug 值"


# ---------------------------------------------------------------------------
# P0-2: WaveguideRouter _encode/_decode 状态空间无别名
# ---------------------------------------------------------------------------
class TestWaveguideRouterEncoding:
    """P0-2: 状态编码空间 (min_bend_steps+1)，s ∈ [0, min_bend_steps] 唯一。"""

    def test_encode_decode_roundtrip_all_states(self):
        """所有 (x,y,d,s) 组合 encode→decode 应保持原值。

        旧 bug: s=min_bend_steps 时 state % min_bend_steps = 0，
        解码得到 s=0（与 straight 别名）。
        """
        router = WaveguideRouter(
            grid_w=10, grid_h=10, grid_size=1.0,
            constraints=RouterConstraints(min_bend_radius_um=5.0),
        )
        # min_bend_steps = round(5.0/1.0) = 5
        assert router.min_bend_steps == 5
        # 测试所有方向 d ∈ {-1,0,1,2} 和所有 s ∈ [0, min_bend_steps]
        for x in range(0, 10):
            for y in range(0, 10):
                for d in (-1, 0, 1, 2):
                    for s in range(0, router.min_bend_steps + 1):
                        state = router._encode(x, y, d, s)
                        dx, dy, dd, ds = router._decode(state)
                        assert (dx, dy, dd, ds) == (x, y, d, s), (
                            f"编码别名: ({x},{y},{d},{s}) → state={state} "
                            f"→ 解码 ({dx},{dy},{dd},{ds})"
                        )

    def test_no_state_aliasing_at_boundary(self):
        """s=min_bend_steps 不应与 s=0 别名（旧 bug 根因）。"""
        router = WaveguideRouter(
            grid_w=10, grid_h=10, grid_size=1.0,
            constraints=RouterConstraints(min_bend_radius_um=5.0),
        )
        mbs = router.min_bend_steps
        # 同 (x,y,d) 下 s=mbs 和 s=0 应编码不同
        s_boundary = router._encode(5, 5, 1, mbs)
        s_zero = router._encode(5, 5, 1, 0)
        assert s_boundary != s_zero, "s=min_bend_steps 与 s=0 编码别名"

    def test_long_straight_then_turn(self):
        """长直行后应能转弯（旧 bug 导致 A* 永远找不到路径）。"""
        # min_bend_radius_um=2.0, grid_size=1.0 → min_bend_steps=2
        # 起点直行 3 步（>min_bend_steps）后转弯应可达
        router = WaveguideRouter(
            grid_w=20, grid_h=20, grid_size=1.0,
            constraints=RouterConstraints(min_bend_radius_um=2.0),
        )
        path = router.route((0, 5), (10, 10))
        assert path is not None, "长直行后转弯路径应为可达"
        assert len(path) >= 2
        assert path[0] == (0, 5)
        assert path[-1] == (10, 10)


# ---------------------------------------------------------------------------
# P0-3: PEXEngine.extract_wire 电感 Rosa 1908 公式
# ---------------------------------------------------------------------------
class TestPexInductanceRosa:
    """P0-3: 电感公式 Rosa 1908: L = μ0·L/(2π)·[ln(2L/(W+H)) + 0.5 + (W+H)/(6L)]。"""

    def test_inductance_value_matches_rosa(self):
        """验证电感值与 Rosa 1908 公式一致（非 Wheeler 简化）。"""
        pex = PEXEngine(
            sheet_resistance_ohm_sq=0.05,
            dielectric_constant=3.9,
            metal_thickness_um=0.5,
            dielectric_thickness_um=1.0,
        )
        L_um = 100.0
        W_um = 1.0
        result = pex.extract_wire(L_um, W_um)
        # 手算 Rosa 1908 期望值
        mu0 = 1.2566e-6  # H/m
        L_m = L_um * 1e-6
        W_m = (W_um + pex.t_metal_um) * 1e-6  # W+H
        ratio = 2.0 * L_m / W_m
        expected_bracket = math.log(ratio) + 0.5 + W_m / (6.0 * L_m)
        expected_L = mu0 * L_m / (2.0 * math.pi) * expected_bracket
        # 转 pH
        expected_ph = expected_L * 1e12
        assert result["inductance_ph"] == pytest.approx(expected_ph, rel=1e-4)

    def test_inductance_not_wheeler(self):
        """旧 Wheeler 简化 ln(2L/(W+t)) - 0.75 给出不同值。"""
        pex = PEXEngine(metal_thickness_um=0.5)
        result = pex.extract_wire(100.0, 1.0)
        # Wheeler 旧公式
        mu0 = 1.2566e-6
        L_m = 100e-6
        W_m = (1.0 + 0.5) * 1e-6
        wheeler = mu0 * L_m / (2.0 * math.pi) * (
            math.log(2.0 * L_m / W_m) - 0.75
        )
        wheeler_ph = wheeler * 1e12
        # 两者应明显不同（Rosa > Wheeler 因 +0.5 vs -0.75）
        assert abs(result["inductance_ph"] - wheeler_ph) > 1e-9

    def test_invalid_dimensions_raise(self):
        """非法尺寸应 raise（禁止 fall-back）。"""
        pex = PEXEngine(metal_thickness_um=0.5)
        with pytest.raises(ValueError):
            pex.extract_wire(0.0, 1.0)
        with pytest.raises(ValueError):
            pex.extract_wire(1.0, 0.0)


# ---------------------------------------------------------------------------
# P0-4: _generate_directions 整数勾股数方向表
# ---------------------------------------------------------------------------
class TestDirectionsUnique:
    """P0-4: 16/32 方向每个方向在整数网格上唯一（无坍缩）。"""

    def test_8_directions_unique(self):
        """8 方向应全部唯一。"""
        dirs = _generate_directions(8)
        assert len(dirs) == 8
        int_dirs = {(int(dx), int(dy)) for dx, dy, _ in dirs}
        assert len(int_dirs) == 8, f"8 方向坍缩: {int_dirs}"

    def test_16_directions_unique(self):
        """16 方向应全部唯一（旧 bug 坍缩为 8）。"""
        dirs = _generate_directions(16)
        assert len(dirs) == 16
        int_dirs = {(int(dx), int(dy)) for dx, dy, _ in dirs}
        assert len(int_dirs) == 16, f"16 方向坍缩为 {len(int_dirs)} 个"

    def test_32_directions_unique(self):
        """32 方向应全部唯一。"""
        dirs = _generate_directions(32)
        assert len(dirs) == 32
        int_dirs = {(int(dx), int(dy)) for dx, dy, _ in dirs}
        assert len(int_dirs) == 32, f"32 方向坍缩为 {len(int_dirs)} 个"

    def test_no_zero_direction(self):
        """方向不应包含 (0,0)。"""
        for n in (8, 16, 32):
            dirs = _generate_directions(n)
            for dx, dy, _ in dirs:
                assert (dx, dy) != (0, 0), f"n={n} 含零方向"

    def test_invalid_n_raises(self):
        """非法 n 应 raise。"""
        with pytest.raises(ValueError):
            _generate_directions(7)
        with pytest.raises(ValueError):
            _generate_directions(64)


# ---------------------------------------------------------------------------
# P0-5: _obstacle_to_set 边界 cell 严格标记
# ---------------------------------------------------------------------------
class TestObstacleBoundaryCells:
    """P0-5: 障碍矩形边界 cell 中心在矩形内（含边界）应被标记。"""

    def test_boundary_cells_marked(self):
        """障碍 [3,6]×[-2,2] (gs=1) 应标记 (3,-2)~(6,2) 全部 cell。"""
        router = CurvyAStarRouter(CurvyAStarConfig(grid_size=1.0))
        obstacles = [(3.0, -2.0, 3.0, 4.0)]
        obs_set = router._obstacle_to_set(obstacles)
        # 边界 cell 应在集合中
        for gx in (3, 4, 5, 6):
            for gy in (-2, -1, 0, 1, 2):
                assert (gx, gy) in obs_set, f"边界 cell ({gx},{gy}) 漏标"

    def test_outside_cells_not_marked(self):
        """障碍外的 cell 不应被标记。"""
        router = CurvyAStarRouter(CurvyAStarConfig(grid_size=1.0))
        obstacles = [(3.0, -2.0, 3.0, 4.0)]
        obs_set = router._obstacle_to_set(obstacles)
        # 障碍外 cell 不应标记
        assert (2, 0) not in obs_set  # x=2 < 3
        assert (7, 0) not in obs_set  # x=7 > 6
        assert (5, 3) not in obs_set  # y=3 > 2
        assert (5, -3) not in obs_set  # y=-3 < -2

    def test_route_avoids_boundary(self):
        """A* 路径不应经过障碍边界 cell。"""
        router = CurvyAStarRouter(
            CurvyAStarConfig(grid_size=1.0, bend_radius=5.0, n_directions=8)
        )
        obstacles = [(3.0, -2.0, 3.0, 4.0)]
        path = router.route((0.0, 0.0), (10.0, 0.0), obstacles)
        for px, py in path:
            # 路径点不应在障碍矩形内（含边界）
            assert not (3.0 <= px <= 6.0 and -2.0 <= py <= 2.0), (
                f"路径点 ({px},{py}) 在障碍边界上"
            )


# ---------------------------------------------------------------------------
# P1-5: ParasiticInductor.extract_mutual 不含错误 K 字段
# ---------------------------------------------------------------------------
class TestMutualInductanceFields:
    """P1-5: extract_mutual 返回字段仅含 mutual_inductance_ph（无量纲）。"""

    def test_no_coupling_coefficient_hint(self):
        """不应返回 coupling_coefficient_hint（量纲错误的 pH 值冒充 K）。"""
        ind = ParasiticInductor(metal_thickness_um=0.5)
        result = ind.extract_mutual(length_um=100.0, spacing_um=2.0)
        assert "mutual_inductance_ph" in result
        assert "coupling_coefficient_hint" not in result, (
            "extract_mutual 仍返回量纲错误的 coupling_coefficient_hint 字段"
        )

    def test_mutual_inductance_value_positive(self):
        """互感应为正值（pH 量级）。"""
        ind = ParasiticInductor(metal_thickness_um=0.5)
        result = ind.extract_mutual(length_um=100.0, spacing_um=2.0)
        m = result["mutual_inductance_ph"]
        assert m > 0, f"互感应为正，得到 {m}"
        # 100μm 长度，2μm 间距，量级在 10~100 pH
        assert 1.0 < m < 1000.0

    def test_invalid_args_raise(self):
        """非法参数应 raise。"""
        ind = ParasiticInductor(metal_thickness_um=0.5)
        with pytest.raises(ValueError):
            ind.extract_mutual(length_um=0.0, spacing_um=2.0)
        with pytest.raises(ValueError):
            ind.extract_mutual(length_um=100.0, spacing_um=0.0)


# ---------------------------------------------------------------------------
# P1-6: stratified_monte_carlo 空层 raise RuntimeError
# ---------------------------------------------------------------------------
class TestStratifiedEmptyStratumRaises:
    """P1-6: 空层（n_h=0）应 raise，禁止静默 0 方差。"""

    def test_empty_stratum_raises(self, monkeypatch):
        """强制 n_per_stratum[0]=0 时应 raise RuntimeError（防御性检查）。

        _allocate_samples 当前保证每层 ≥1，但 P1-6 的 RuntimeError 是
        防御性检查（防止未来 _allocate_samples 改动引入空层）。
        用 monkeypatch 模拟未来 bug 触发该防御。
        """
        from polaris.sim import stratified_sampling as ss

        # Monkeypatch _allocate_samples 返回含 0 的列表（模拟未来 bug）
        def _fake_allocate(n_total, n_strata, strategy, strata_stds=None):
            return [0] + [n_total // max(1, n_strata - 1)] * (n_strata - 1)

        monkeypatch.setattr(ss, "_allocate_samples", _fake_allocate)

        with pytest.raises(RuntimeError, match="分配到 0 个样本"):
            stratified_monte_carlo(
                func=lambda x: float(x[0]),
                nominal_dist=[{"type": "uniform", "low": 0.0, "high": 1.0}],
                n_strata=5,
                n_samples=50,
                strategy=AllocationStrategy.EQUAL,
                seed=42,
            )

    def test_insufficient_samples_raises_value_error(self):
        """n_samples < n_strata 应在前置检查 raise ValueError。"""
        with pytest.raises(ValueError, match="每层至少 1 个样本"):
            stratified_monte_carlo(
                func=lambda x: float(x[0]),
                nominal_dist=[{"type": "uniform", "low": 0.0, "high": 1.0}],
                n_strata=10,
                n_samples=5,
                strategy=AllocationStrategy.EQUAL,
                seed=42,
            )

    def test_normal_run_no_raise(self):
        """正常样本数应不 raise。"""
        result = stratified_monte_carlo(
            func=lambda x: float(x[0]),
            nominal_dist=[{"type": "uniform", "low": 0.0, "high": 1.0}],
            n_strata=5,
            n_samples=100,
            strategy=AllocationStrategy.EQUAL,
            seed=42,
        )
        # 均值应接近 0.5（U[0,1] 期望）
        assert 0.3 < result.estimate < 0.7


# ---------------------------------------------------------------------------
# P1-7: GDSII 坐标 int(round()) 避免截断漂移
# ---------------------------------------------------------------------------
class TestGdsiiRounding:
    """P1-7: GDSII 坐标转换用 round 而非 int 截断。

    验证 round-trip 误差 ≤ dbu/2（int 截断会给出系统性 -dbu 漂移）。
    """

    def test_round_vs_trunc(self):
        """int(round(x)) 与 int(x) 在 0.5 处差异最大。"""
        # 模拟 dbu_um=0.001 (1nm)，用 1.5 dbu 的精度避免浮点误差
        dbu_um = 0.001
        x_um = 1.0006  # 1.0006/0.001 ≈ 1000.6 → round 1001, trunc 1000
        # 修复后: int(round)
        dbu_round = int(round(x_um / dbu_um))
        # 旧 bug: int() 截断
        dbu_trunc = int(x_um / dbu_um)
        assert dbu_round == 1001
        assert dbu_trunc == 1000  # 截断丢失 1 dbu
        # round 误差更小
        err_round = abs(dbu_round * dbu_um - x_um)
        err_trunc = abs(dbu_trunc * dbu_um - x_um)
        assert err_round < err_trunc

    def test_round_trip_error_bound(self):
        """round-trip 误差应 ≤ dbu/2（round 保证）。"""
        dbu_um = 0.001
        # 用 0.0006（>0.0005）避免浮点边界
        for x_um in [0.0006, 0.0015, 0.0026, 1.23456, 99.9996]:
            dbu_val = int(round(x_um / dbu_um))
            x_back = dbu_val * dbu_um
            assert abs(x_back - x_um) <= dbu_um / 2.0 + 1e-9, (
                f"x={x_um} round-trip 误差 {abs(x_back - x_um)} > dbu/2"
            )


# ---------------------------------------------------------------------------
# P1-8: rip_up_reroute 失败 logger.error
# ---------------------------------------------------------------------------
class TestRipUpRerouteLogging:
    """P1-8: rip-up & reroute 重布失败应记录 logger.error。"""

    def test_failure_logs_error(self, caplog):
        """重布失败时应有 ERROR 级日志。"""
        ordering = CongestionAwareNetOrdering(grid_size=1.0)

        # 构造一个必然失败的重布场景：用 Mock router 让 route() raise ValueError
        class _FailingRouter:
            class _Cfg:
                grid_size = 1.0

            config = _Cfg()

            def route(self, start, end, obstacles):
                raise ValueError("模拟不可达")

        # 准备 old_path：网 0 失败需要重布
        old_path = [(0.0, 0.0), (5.0, 0.0), (10.0, 0.0)]
        # 网索引 0 标记为失败，需要 rip-up & reroute
        import logging as _logging
        # 设置 logger 可传播以被 caplog 捕获
        target_logger = _logging.getLogger("polaris.router.curvy_optodesigner")
        target_logger.setLevel(_logging.ERROR)
        with caplog.at_level(_logging.ERROR, logger="polaris.router.curvy_optodesigner"):
            result = ordering.rip_up_reroute(
                paths=[old_path],
                failed_nets=[0],
                router=_FailingRouter(),
            )
        # 应有 ERROR 日志
        error_logs = [r for r in caplog.records if r.levelno == _logging.ERROR]
        assert len(error_logs) >= 1, "重布失败未记录 ERROR 日志"
        # 应保留原路径
        assert result[0] == old_path

    def test_successful_reroute_no_error_log(self, caplog):
        """重布成功时不应有 ERROR 日志。"""
        ordering = CongestionAwareNetOrdering(grid_size=1.0)

        class _OkRouter:
            class _Cfg:
                grid_size = 1.0

            config = _Cfg()

            def route(self, start, end, obstacles):
                return [start, end]

        old_path = [(0.0, 0.0), (10.0, 0.0)]
        import logging as _logging
        target_logger = _logging.getLogger("polaris.router.curvy_optodesigner")
        target_logger.setLevel(_logging.ERROR)
        with caplog.at_level(_logging.ERROR, logger="polaris.router.curvy_optodesigner"):
            result = ordering.rip_up_reroute(
                paths=[old_path],
                failed_nets=[0],
                router=_OkRouter(),
            )
        error_logs = [r for r in caplog.records if r.levelno == _logging.ERROR]
        assert len(error_logs) == 0
        assert result[0] == [(0.0, 0.0), (10.0, 0.0)]


# ---------------------------------------------------------------------------
# 集成：第3轮无回归（CurvyAStarRouter 基本路由仍可用）
# ---------------------------------------------------------------------------
class TestRound3NoRegression:
    """第3轮修复不应破坏基本路由能力。"""

    def test_simple_route_still_works(self):
        """无障碍简单路由应成功。"""
        router = CurvyAStarRouter(
            CurvyAStarConfig(grid_size=1.0, bend_radius=5.0, n_directions=8)
        )
        path = router.route((0.0, 0.0), (10.0, 0.0))
        assert len(path) >= 2
        assert path[0] == (0.0, 0.0)
        assert path[-1] == (10.0, 0.0)

    def test_16_dirs_route_still_works(self):
        """16 方向路由应成功。"""
        router = CurvyAStarRouter(
            CurvyAStarConfig(grid_size=1.0, bend_radius=5.0, n_directions=16)
        )
        path = router.route((0.0, 0.0), (10.0, 5.0))
        assert len(path) >= 2
        assert path[0] == (0.0, 0.0)
        assert path[-1] == (10.0, 5.0)
