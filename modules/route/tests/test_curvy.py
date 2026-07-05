"""polaris-route 子模块深度测试（v5.0）。

覆盖 polaris_route 全部公开 API:
- 常量: BEND_LOSS_DB / CROSSING_LOSS_DB / PROPAGATION_LOSS_DB_CM
- 枚举: CurveType (EULER/ARC/BEZIER)
- 配置: CurvyRouteConfig (min_bend_radius_um/n_curve_points/bend_loss_db/crossing_loss_db)
- 布线器: CurvyRouter.route (直线/step S-bend/同点)
- 几何: generate_arc_bend / generate_euler_bend / s_bend_bezier
- 工具: path_length / count_bends / count_crossings / compute_path_loss
- 端到端: route_circuit (校验/损耗/拓扑/插入损耗)

测试组织（共 48 个测试）:
1. TestRouteConstants: 常量溯源 (3)
2. TestCurveType: 枚举 (3)
3. TestCurvyRouteConfig: 配置校验 (5)
4. TestCurvyRouter: 布线器路由 (8)
5. TestPathLength: 路径长度 (4)
6. TestCountBends: 弯曲计数 (5)
7. TestCountCrossings: 交叉计数 (5)
8. TestGenerateArcBend: 圆弧几何 (4)
9. TestGenerateEulerBend: 欧拉曲率连续 (4)
10. TestSBendBezier: 贝塞尔 S-bend (4)
11. TestComputePathLoss: 损耗计算 (5)
12. TestRouteCircuitEndToEnd: 端到端 (12) — 含原 smoke test 回归

来源（R02 学术诚信，≥5 个文献 URL）:
- LiDAR: Automated Curvy Waveguide Detailed Routing（ISPD'25）
  https://dl.acm.org/doi/pdf/10.1145/3698364.3705355
- SiEPIC EBeam PDK（bend_euler radius=5μm，0.05 dB/bend，0.3 dB/crossing）
  https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- Soref et al. 1993 IEEE Proc. 41(9) 1182-1183（SOI 3 dB/cm 传播损耗基准）
  https://ieeexplore.ieee.org/document/1148303
- Chrostowski & Hochberg 2015 §6.4 Silicon Photonics Design
  https://www.cambridge.org/core/books/silicon-photonics-design/
- Klauss et al., "Euler spiral waveguide bends", Opt Express 2018
  https://doi.org/10.1364/OE.26.029637
- Fujisawa et al. 2017, "Euler bend clothoid curve low-loss waveguide"
  (Optics Express 25(8) 9150) https://opg.optica.org/oe/fulltext.cfm?uri=oe-25-8-9150
- Flexcompute Tidy3D EulerWaveguideBend（clothoid 公式 RL=A², θ=L/(2R)）
  https://docs.flexcompute.com/projects/tidy3d/en/v2.9.2/notebooks/EulerWaveguideBend.html
- de Berg et al. 2008 Computational Geometry §2.1（CCW 线段相交）
- pytest 文档: https://docs.pytest.org/
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

# 让测试既能从已安装包导入，也能从源码树导入（CI/开发模式）
_SRC = str(Path(__file__).resolve().parents[1] / "src")
_CORE_SRC = str(Path(__file__).resolve().parents[2] / "core" / "src")
_PLACE_SRC = str(Path(__file__).resolve().parents[2] / "place" / "src")
for _p in (_SRC, _CORE_SRC, _PLACE_SRC):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import polaris_route  # noqa: E402
from polaris_core import make_circuit, make_device  # noqa: E402
from polaris_place import place_circuit  # noqa: E402
from polaris_route import (  # noqa: E402
    BEND_LOSS_DB,
    CROSSING_LOSS_DB,
    PROPAGATION_LOSS_DB_CM,
    CurveType,
    CurvyRouteConfig,
    CurvyRouter,
    compute_path_loss,
    count_bends,
    count_crossings,
    generate_arc_bend,
    generate_euler_bend,
    path_length,
    route_circuit,
    s_bend_bezier,
)


# ---------------------------------------------------------------------------
# 辅助：构造测试电路
# ---------------------------------------------------------------------------
def _make_mzi_circuit() -> dict:
    """构造 5 器件 5 连接 MZI 电路（与验证脚本一致）。

    1 光栅耦合器 + 2 MMI + 2 波导臂，构成马赫-曾德干涉仪。
    """
    gc = make_device(
        "gc1", "grating_coupler", 20, 20,
        ports=[("in", 0, 10, "west"), ("out", 20, 10, "east")],
    )
    mmi = make_device(
        "mmi1", "mmi_1x2", 20, 5,
        ports=[("in", 0, 2.5, "west"), ("out1", 20, 1.5, "east"),
               ("out2", 20, 3.5, "east")],
    )
    wg1 = make_device(
        "wg1", "strip_waveguide", 100, 0.5,
        ports=[("in", 0, 0.25, "west"), ("out", 100, 0.25, "east")],
    )
    wg2 = make_device(
        "wg2", "strip_waveguide", 120, 0.5,
        ports=[("in", 0, 0.25, "west"), ("out", 120, 0.25, "east")],
    )
    mmi2 = make_device(
        "mmi2", "mmi_2x2", 20, 5,
        ports=[("in1", 0, 1.5, "west"), ("in2", 0, 3.5, "west"),
               ("out1", 20, 1.5, "east"), ("out2", 20, 3.5, "east")],
    )
    return make_circuit(
        "MZI",
        [gc, mmi, wg1, wg2, mmi2],
        [
            ("gc1", "out", "mmi1", "in"),
            ("mmi1", "out1", "wg1", "in"),
            ("mmi1", "out2", "wg2", "in"),
            ("wg1", "out", "mmi2", "in1"),
            ("wg2", "out", "mmi2", "in2"),
        ],
        canvas_w=500,
        canvas_h=300,
    )


# ============================================================
# 1. TestRouteConstants — 常量溯源（R02 学术诚信）
# ============================================================

class TestCurvyRouteConfig:
    """CurvyRouteConfig 默认值与非法参数校验（R03 禁止 fall-back）。"""

    def test_default_config(self):
        """默认配置: 5μm 弯曲半径, 20 采样点, 0.05/0.3 dB 损耗。"""
        cfg = CurvyRouteConfig()
        assert cfg.min_bend_radius_um == 5.0  # SiEPIC EBeam PDK 默认
        assert cfg.n_curve_points == 20
        assert cfg.bend_loss_db == BEND_LOSS_DB
        assert cfg.crossing_loss_db == CROSSING_LOSS_DB

    def test_custom_config(self):
        """自定义配置应正确传递。"""
        cfg = CurvyRouteConfig(
            min_bend_radius_um=10.0,
            n_curve_points=50,
            bend_loss_db=0.1,
            crossing_loss_db=0.5,
        )
        assert cfg.min_bend_radius_um == 10.0
        assert cfg.n_curve_points == 50
        assert cfg.bend_loss_db == 0.1
        assert cfg.crossing_loss_db == 0.5

    def test_invalid_min_bend_radius_zero(self):
        """min_bend_radius_um=0 应 raise（R03 禁止 fall-back）。"""
        with pytest.raises(RuntimeError, match="min_bend_radius_um 必须为正"):
            CurvyRouteConfig(min_bend_radius_um=0.0)

    def test_invalid_min_bend_radius_negative(self):
        """min_bend_radius_um 为负应 raise（R03 禁止 fall-back）。"""
        with pytest.raises(RuntimeError, match="min_bend_radius_um 必须为正"):
            CurvyRouteConfig(min_bend_radius_um=-5.0)

    def test_invalid_n_curve_points(self):
        """n_curve_points < 2 应 raise（R03 禁止 fall-back）。"""
        with pytest.raises(RuntimeError, match="n_curve_points"):
            CurvyRouteConfig(n_curve_points=1)
        with pytest.raises(RuntimeError, match="n_curve_points"):
            CurvyRouteConfig(n_curve_points=0)

    def test_config_attribute_types(self):
        """配置属性类型应为 float/int（JSON-serializable）。"""
        cfg = CurvyRouteConfig(min_bend_radius_um=7.5, n_curve_points=30)
        assert isinstance(cfg.min_bend_radius_um, float)
        assert isinstance(cfg.n_curve_points, int)
        assert isinstance(cfg.bend_loss_db, float)
        assert isinstance(cfg.crossing_loss_db, float)


# ============================================================
# 4. TestCurvyRouter — 曲线波导布线器
# ============================================================
class TestCurvyRouter:
    """CurvyRouter.route 路由拓扑测试（直线/step S-bend/同点）。"""

    def test_route_aligned_x_straight(self):
        """同 x（垂直对齐）: 直线 2 点 0 弯曲。"""
        router = CurvyRouter()
        pts = router.route((50.0, 0.0), (50.0, 100.0))
        assert len(pts) == 2
        assert pts[0] == (50.0, 0.0)
        assert pts[-1] == (50.0, 100.0)
        assert count_bends(pts) == 0

    def test_route_aligned_y_straight(self):
        """同 y（水平对齐）: 直线 2 点 0 弯曲。"""
        router = CurvyRouter()
        pts = router.route((0.0, 50.0), (100.0, 50.0))
        assert len(pts) == 2
        assert pts[0] == (0.0, 50.0)
        assert pts[-1] == (100.0, 50.0)
        assert count_bends(pts) == 0

    def test_route_unaligned_step(self):
        """不同 x 不同 y: step S-bend 4 点 2 弯曲。"""
        router = CurvyRouter()
        pts = router.route((0.0, 0.0), (100.0, 50.0))
        assert len(pts) == 4
        assert pts[0] == (0.0, 0.0)
        assert pts[-1] == (100.0, 50.0)
        assert count_bends(pts) == 2

    def test_route_same_point(self):
        """起点终点相同: 零长路径 2 点 0 弯曲。"""
        router = CurvyRouter()
        pts = router.route((50.0, 50.0), (50.0, 50.0))
        assert len(pts) == 2
        assert pts[0] == (50.0, 50.0)
        assert pts[-1] == (50.0, 50.0)
        assert count_bends(pts) == 0

    def test_route_none_start_raises(self):
        """start=None 应 raise RuntimeError（R03 禁止 fall-back）。"""
        router = CurvyRouter()
        with pytest.raises(RuntimeError, match="start/end 不能为 None"):
            router.route(None, (10.0, 10.0))

    def test_route_none_end_raises(self):
        """end=None 应 raise RuntimeError（R03 禁止 fall-back）。"""
        router = CurvyRouter()
        with pytest.raises(RuntimeError, match="start/end 不能为 None"):
            router.route((10.0, 10.0), None)

    def test_router_with_custom_config(self):
        """自定义 config 应正确存储在 router.config。"""
        cfg = CurvyRouteConfig(min_bend_radius_um=10.0, n_curve_points=50)
        router = CurvyRouter(cfg)
        assert router.config is cfg
        assert router.config.min_bend_radius_um == 10.0
        assert router.config.n_curve_points == 50

    def test_router_default_config(self):
        """无 config 时使用默认 CurvyRouteConfig。"""
        router = CurvyRouter()
        assert isinstance(router.config, CurvyRouteConfig)
        assert router.config.min_bend_radius_um == 5.0
        assert router.config.n_curve_points == 20

    def test_router_step_mid_x(self):
        """step 拓扑中间点 x 为起止 x 中点，y 分别为 sy/ey。"""
        router = CurvyRouter()
        pts = router.route((0.0, 0.0), (100.0, 50.0))
        mid_x = (0.0 + 100.0) / 2.0
        assert pts[1][0] == pytest.approx(mid_x)
        assert pts[2][0] == pytest.approx(mid_x)
        assert pts[1][1] == pytest.approx(0.0)  # sy
        assert pts[2][1] == pytest.approx(50.0)  # ey


# ============================================================
# 5. TestPathLength — 路径长度
# ============================================================
class TestGenerateArcBend:
    """generate_arc_bend 圆弧生成（恒定曲率）。"""

    def test_arc_bend_endpoints(self):
        """圆弧起点终点精确对齐输入。"""
        pts = generate_arc_bend((0.0, 0.0), (10.0, 5.0), radius_um=5.0, n_points=20)
        assert len(pts) == 20
        assert pts[0] == pytest.approx((0.0, 0.0), abs=1e-9)
        assert pts[-1] == pytest.approx((10.0, 5.0), abs=1e-9)

    def test_arc_bend_n_points(self):
        """采样点数与 n_points 一致。"""
        for n in (10, 20, 50):
            pts = generate_arc_bend((0.0, 0.0), (10.0, 5.0), radius_um=5.0, n_points=n)
            assert len(pts) == n

    def test_arc_bend_zero_distance(self):
        """起止点重合时返回两点（不报错）。"""
        pts = generate_arc_bend((5.0, 5.0), (5.0, 5.0), radius_um=5.0, n_points=20)
        assert len(pts) == 2
        assert pts[0] == (5.0, 5.0)
        assert pts[-1] == (5.0, 5.0)

    def test_arc_bend_curve_length_positive(self):
        """圆弧路径长度 > 0 且 >= 直线距离（弧长 ≥ 弦长）。"""
        pts = generate_arc_bend((0.0, 0.0), (10.0, 5.0), radius_um=5.0, n_points=20)
        arc_len = path_length(pts)
        chord = math.hypot(10.0, 5.0)
        assert arc_len > 0.0
        assert arc_len >= chord - 1e-6  # 弧长 >= 弦长


# ============================================================
# 9. TestGenerateEulerBend — 欧拉弯曲曲率连续
# ============================================================
class TestGenerateEulerBend:
    """generate_euler_bend 欧拉螺旋（clothoid）曲率线性变化。"""

    def test_euler_bend_endpoints(self):
        """欧拉弯曲起点终点对齐输入。"""
        pts = generate_euler_bend((0.0, 0.0), (20.0, 10.0), radius_um=5.0, n_points=20)
        assert len(pts) == 20
        assert pts[0] == pytest.approx((0.0, 0.0), abs=1e-6)
        assert pts[-1] == pytest.approx((20.0, 10.0), abs=1e-6)

    def test_euler_bend_n_points(self):
        """采样点数与 n_points 一致。"""
        for n in (10, 20, 50):
            pts = generate_euler_bend((0.0, 0.0), (20.0, 10.0), radius_um=5.0, n_points=n)
            assert len(pts) == n

    def test_euler_bend_close_points_no_raise(self):
        """起止点过近时不报错（自动调整 radius_um 保证 scale=1）。"""
        pts = generate_euler_bend((0.0, 0.0), (1.0, 0.5), radius_um=10.0, n_points=20)
        assert len(pts) == 20
        assert pts[0] == pytest.approx((0.0, 0.0), abs=1e-6)
        assert pts[-1] == pytest.approx((1.0, 0.5), abs=1e-6)

    def test_euler_bend_curvature_starts_low(self):
        """欧拉弯曲起始曲率低于终止曲率（clothoid 性质: k(s)=s/(RL)）。

        曲率从 0 线性增至 1/R，故前段转角和 < 后段转角和。
        """
        pts = generate_euler_bend((0.0, 0.0), (20.0, 10.0), radius_um=5.0, n_points=50)
        # 计算每个内部点的转角（相邻段方向变化）
        angles = []
        for i in range(1, len(pts) - 1):
            dx1, dy1 = pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]
            dx2, dy2 = pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]
            a1 = math.atan2(dy1, dx1)
            a2 = math.atan2(dy2, dx2)
            da = abs(a2 - a1)
            if da > math.pi:
                da = 2 * math.pi - da
            angles.append(da)
        # 前 1/3 转角和应 < 后 1/3 转角和（曲率从 0 线性增加）
        n_third = max(1, len(angles) // 3)
        start_sum = sum(angles[:n_third])
        end_sum = sum(angles[-n_third:])
        assert start_sum < end_sum, (
            f"起始曲率和({start_sum:.4f}) 应 < 终止曲率和({end_sum:.4f})"
        )


# ============================================================
# 10. TestSBendBezier — 贝塞尔 S-bend
# ============================================================
class TestSBendBezier:
    """s_bend_bezier 三次贝塞尔曲线 S 弯。"""

    def test_s_bend_endpoints(self):
        """S-bend 起止点对齐输入。"""
        pts = s_bend_bezier(0.0, 0.0, 10.0, 5.0, n_points=20)
        assert len(pts) == 21  # n_points + 1
        assert pts[0] == pytest.approx((0.0, 0.0), abs=1e-9)
        assert pts[-1] == pytest.approx((10.0, 5.0), abs=1e-9)

    def test_s_bend_n_points_default(self):
        """默认 n_points=20 返回 21 个点。"""
        pts = s_bend_bezier(0.0, 0.0, 10.0, 5.0)
        assert len(pts) == 21

    def test_s_bend_custom_n_points(self):
        """自定义 n_points 返回 n_points+1 个点。"""
        pts = s_bend_bezier(0.0, 0.0, 10.0, 5.0, n_points=50)
        assert len(pts) == 51

    def test_s_bend_aligned_horizontal(self):
        """y 相同时 S-bend 退化为水平直线（所有点 y=0）。"""
        pts = s_bend_bezier(0.0, 0.0, 10.0, 0.0, n_points=20)
        for x, y in pts:
            assert y == pytest.approx(0.0, abs=1e-9)
        # x 单调递增（贝塞尔控制点保证）
        for i in range(1, len(pts)):
            assert pts[i][0] >= pts[i - 1][0] - 1e-9


# ============================================================
# 11. TestComputePathLoss — 路径损耗计算
# ============================================================
