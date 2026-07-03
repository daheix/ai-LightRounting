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
class TestRouteConstants:
    """损耗常量值与文献溯源一致（SiEPIC EBeam PDK + Soref 1993）。"""

    def test_propagation_loss_db_cm_value(self):
        """传播损耗 3.0 dB/cm（Soref 1993 SOI 上界）。"""
        assert PROPAGATION_LOSS_DB_CM == 3.0

    def test_bend_loss_db_value(self):
        """单弯损耗 0.05 dB（SiEPIC EBeam PDK 通用路径上界）。"""
        assert BEND_LOSS_DB == 0.05

    def test_crossing_loss_db_value(self):
        """单次交叉损耗 0.3 dB（SiEPIC EBeam PDK crossing_te1550 上界）。"""
        assert CROSSING_LOSS_DB == 0.3


# ============================================================
# 2. TestCurveType — 曲线类型枚举
# ============================================================
class TestCurveType:
    """CurveType 枚举值与字符串映射正确。"""

    def test_curve_type_euler_value(self):
        """EULER 枚举值为 'euler'。"""
        assert CurveType.EULER.value == "euler"

    def test_curve_type_arc_value(self):
        """ARC 枚举值为 'arc'。"""
        assert CurveType.ARC.value == "arc"

    def test_curve_type_bezier_value(self):
        """BEZIER 枚举值为 'bezier'。"""
        assert CurveType.BEZIER.value == "bezier"

    def test_curve_type_distinct_values(self):
        """三种曲线类型值互异。"""
        values = {CurveType.EULER.value, CurveType.ARC.value, CurveType.BEZIER.value}
        assert len(values) == 3


# ============================================================
# 3. TestCurvyRouteConfig — 配置校验
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
class TestPathLength:
    """path_length 折线累积长度计算。"""

    def test_path_length_straight(self):
        """直线路径长度 = 欧氏距离。"""
        points = [(0.0, 0.0), (10.0, 0.0)]
        assert path_length(points) == pytest.approx(10.0)

    def test_path_length_l_shape(self):
        """L 形路径长度 = 两段之和。"""
        points = [(0.0, 0.0), (10.0, 0.0), (10.0, 5.0)]
        assert path_length(points) == pytest.approx(15.0)

    def test_path_length_empty(self):
        """空路径或单点路径长度为 0。"""
        assert path_length([]) == 0.0
        assert path_length([(5.0, 5.0)]) == 0.0

    def test_path_length_diagonal(self):
        """对角线路径长度 = √2 * 边长。"""
        points = [(0.0, 0.0), (3.0, 4.0)]
        assert path_length(points) == pytest.approx(5.0)  # 3-4-5 三角形


# ============================================================
# 6. TestCountBends — 弯曲计数
# ============================================================
class TestCountBends:
    """count_bends 方向改变次数统计。"""

    def test_count_bends_straight(self):
        """直线路径 0 弯曲。"""
        assert count_bends([(0.0, 0.0), (10.0, 0.0)]) == 0

    def test_count_bends_l_shape(self):
        """L 形路径 1 弯曲。"""
        assert count_bends([(0.0, 0.0), (10.0, 0.0), (10.0, 5.0)]) == 1

    def test_count_bends_step(self):
        """step S-bend 4 点 2 弯曲。"""
        pts = [(0.0, 0.0), (50.0, 0.0), (50.0, 50.0), (100.0, 50.0)]
        assert count_bends(pts) == 2

    def test_count_bends_short_path(self):
        """< 3 点路径返回 0 弯曲。"""
        assert count_bends([]) == 0
        assert count_bends([(0.0, 0.0)]) == 0
        assert count_bends([(0.0, 0.0), (10.0, 0.0)]) == 0

    def test_count_bends_collinear(self):
        """共线三点 0 弯曲（方向未变）。"""
        assert count_bends([(0.0, 0.0), (5.0, 0.0), (10.0, 0.0)]) == 0


# ============================================================
# 7. TestCountCrossings — 交叉计数
# ============================================================
class TestCountCrossings:
    """count_crossings CCW 叉积法线段相交检测。"""

    def test_count_crossings_parallel(self):
        """平行线段 0 交叉。"""
        path1 = [(0.0, 0.0), (10.0, 0.0)]
        path2 = [(0.0, 5.0), (10.0, 5.0)]
        assert count_crossings(path1, path2) == 0

    def test_count_crossings_x_pattern(self):
        """X 形交叉 1 次。"""
        path1 = [(0.0, 0.0), (10.0, 10.0)]
        path2 = [(0.0, 10.0), (10.0, 0.0)]
        assert count_crossings(path1, path2) == 1

    def test_count_crossings_disjoint(self):
        """不相交线段 0 交叉。"""
        path1 = [(0.0, 0.0), (5.0, 0.0)]
        path2 = [(10.0, 0.0), (15.0, 0.0)]
        assert count_crossings(path1, path2) == 0

    def test_count_crossings_shared_endpoint(self):
        """共享端点不算交叉（CCW 严格符号判定）。"""
        path1 = [(0.0, 0.0), (10.0, 10.0)]
        path2 = [(0.0, 0.0), (10.0, 0.0)]
        assert count_crossings(path1, path2) == 0

    def test_count_crossings_l_paths(self):
        """两条 L 形路径相交 1 次。"""
        # path1: (0,5)→(5,5)→(5,0)
        # path2: (0,0)→(5,0)→(5,10)... 不交
        # 改为确实相交: path1 横线 y=5, path2 竖线 x=3
        path1 = [(0.0, 5.0), (10.0, 5.0)]
        path2 = [(3.0, 0.0), (3.0, 10.0)]
        assert count_crossings(path1, path2) == 1


# ============================================================
# 8. TestGenerateArcBend — 圆弧弯曲几何
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
class TestComputePathLoss:
    """compute_path_loss 传播损耗 + 弯曲损耗。"""

    def test_compute_path_loss_propagation_only(self):
        """直线无弯曲: 损耗 = 传播损耗（3.0 * 长度 / 1e4）。"""
        points = [(0.0, 0.0), (100.0, 0.0)]
        loss = compute_path_loss(points, loss_db_cm=3.0)
        expected = 3.0 * 100.0 / 1e4  # 0.03 dB
        assert abs(loss - expected) < 1e-9

    def test_compute_path_loss_with_bend(self):
        """L 形 1 弯曲: 损耗 = 传播 + 1*0.05。"""
        points = [(0.0, 0.0), (100.0, 0.0), (100.0, 50.0)]
        loss = compute_path_loss(points, loss_db_cm=3.0)
        expected = 3.0 * 150.0 / 1e4 + 1 * 0.05  # 0.045 + 0.05 = 0.095
        assert abs(loss - expected) < 1e-9

    def test_compute_path_loss_empty(self):
        """空路径或单点路径损耗为 0。"""
        assert compute_path_loss([]) == 0.0
        assert compute_path_loss([(5.0, 5.0)]) == 0.0

    def test_compute_path_loss_negative_coeff_raises(self):
        """负 loss_db_cm 应 raise RuntimeError（R03 禁止 fall-back）。"""
        with pytest.raises(RuntimeError, match="loss_db_cm 不能为负"):
            compute_path_loss([(0.0, 0.0), (10.0, 0.0)], loss_db_cm=-1.0)

    def test_compute_path_loss_custom_coeff(self):
        """自定义 loss_db_cm 影响传播损耗部分。"""
        points = [(0.0, 0.0), (100.0, 0.0)]
        loss = compute_path_loss(points, loss_db_cm=2.0)
        expected = 2.0 * 100.0 / 1e4  # 0.02 dB
        assert abs(loss - expected) < 1e-9

    def test_compute_path_loss_accepts_list_of_lists(self):
        """compute_path_loss 兼容 list[list[float]] 输入。"""
        points = [[0.0, 0.0], [100.0, 0.0]]
        loss = compute_path_loss(points, loss_db_cm=3.0)
        expected = 3.0 * 100.0 / 1e4
        assert abs(loss - expected) < 1e-9


# ============================================================
# 12. TestRouteCircuitEndToEnd — 端到端布线
# ============================================================
class TestRouteCircuitEndToEnd:
    """route_circuit 端到端布线与校验（含原 smoke test 回归）。"""

    def test_route_mzi(self):
        """5 器件 MZI 布线: n_paths=5, total_loss_db>0, router_type="curvy"。

        回归测试: 保留原 v5.0 smoke test 行为。
        """
        circuit = _make_mzi_circuit()
        placement_result = place_circuit(circuit, mode="analytical")
        placements = placement_result["placements"]

        result = route_circuit(circuit, placements)

        for key in ("paths", "total_loss_db", "n_crossings", "n_bends", "router_type"):
            assert key in result, f"结果缺少字段: {key}"

        assert result["router_type"] == "curvy"

        paths = result["paths"]
        assert len(paths) == 5, f"应有 5 条路径，实际 {len(paths)}"

        for i, path in enumerate(paths):
            for field in ("dev1", "port1", "dev2", "port2",
                          "points", "loss_db", "n_bends", "n_crossings"):
                assert field in path, f"path[{i}] 缺少字段: {field}"
            points = path["points"]
            assert len(points) >= 2, \
                f"path[{i}] points 至少 2 个点，实际 {len(points)}"
            assert path["loss_db"] >= 0.0
            assert path["n_bends"] >= 0
            assert path["n_crossings"] >= 0

        assert result["total_loss_db"] > 0.0
        assert result["n_bends"] >= 0
        assert result["n_crossings"] >= 0

    def test_route_path_count_matches_connections(self):
        """路径数 = 连接数（端到端一致性）。"""
        circuit = _make_mzi_circuit()
        placements = place_circuit(circuit, mode="analytical")["placements"]
        result = route_circuit(circuit, placements)
        assert len(result["paths"]) == len(circuit["connections"])

    def test_route_empty(self):
        """无连接的电路返回空 paths，total_loss_db=0。"""
        gc = make_device(
            "gc1", "grating_coupler", 20, 20,
            ports=[("in", 0, 10, "west"), ("out", 20, 10, "east")],
        )
        circuit = make_circuit("Empty", [gc], [], canvas_w=500, canvas_h=300)
        placements = {"gc1": {"x": 0.0, "y": 0.0, "w": 20.0, "h": 20.0}}

        result = route_circuit(circuit, placements)

        assert result["paths"] == []
        assert result["total_loss_db"] == 0.0
        assert result["n_crossings"] == 0
        assert result["n_bends"] == 0
        assert result["router_type"] == "curvy"

    def test_route_invalid_mode(self):
        """非法 mode 应 raise RuntimeError（R03 禁止 fall-back）。"""
        circuit = _make_mzi_circuit()
        placements = place_circuit(circuit, mode="analytical")["placements"]
        with pytest.raises(RuntimeError, match="不支持的布线模式"):
            route_circuit(circuit, placements, mode="unknown_mode")

    def test_route_missing_port(self):
        """端口缺失应 raise RuntimeError（R03 禁止 fall-back）。"""
        gc = make_device(
            "gc1", "grating_coupler", 20, 20,
            ports=[("in", 0, 10, "west"), ("out", 20, 10, "east")],
        )
        mmi = make_device(
            "mmi1", "mmi_1x2", 20, 5,
            ports=[("in", 0, 2.5, "west"), ("out1", 20, 1.5, "east")],
        )
        circuit = make_circuit(
            "BadLink", [gc, mmi],
            [("gc1", "out", "mmi1", "out2")],  # mmi1 无 out2 端口
            canvas_w=500, canvas_h=300,
        )
        placements = {
            "gc1": {"x": 0.0, "y": 0.0, "w": 20.0, "h": 20.0},
            "mmi1": {"x": 100.0, "y": 0.0, "w": 20.0, "h": 5.0},
        }
        with pytest.raises(RuntimeError, match="未找到端口"):
            route_circuit(circuit, placements)

    def test_route_missing_placement(self):
        """连接引用的器件不在 placements 中应 raise RuntimeError（R03）。"""
        gc = make_device(
            "gc1", "grating_coupler", 20, 20,
            ports=[("in", 0, 10, "west"), ("out", 20, 10, "east")],
        )
        mmi = make_device(
            "mmi1", "mmi_1x2", 20, 5,
            ports=[("in", 0, 2.5, "west"), ("out1", 20, 1.5, "east")],
        )
        circuit = make_circuit(
            "Link", [gc, mmi],
            [("gc1", "out", "mmi1", "in")],
            canvas_w=500, canvas_h=300,
        )
        placements = {"gc1": {"x": 0.0, "y": 0.0, "w": 20.0, "h": 20.0}}
        with pytest.raises(RuntimeError, match="不在 placements 中"):
            route_circuit(circuit, placements)

    def test_route_negative_insertion_loss(self):
        """负 insertion_loss_db 应 raise RuntimeError（R03 禁止 fall-back）。"""
        gc = make_device(
            "gc1", "grating_coupler", 20, 20,
            ports=[("out", 20, 10, "east")],
            params={"insertion_loss_db": -0.5},
        )
        mmi = make_device(
            "mmi1", "mmi_1x2", 20, 5,
            ports=[("in", 0, 2.5, "west")],
        )
        circuit = make_circuit(
            "NegLoss", [gc, mmi],
            [("gc1", "out", "mmi1", "in")],
            canvas_w=500, canvas_h=300,
        )
        placements = {
            "gc1": {"x": 0.0, "y": 0.0, "w": 20.0, "h": 20.0},
            "mmi1": {"x": 100.0, "y": 0.0, "w": 20.0, "h": 5.0},
        }
        with pytest.raises(RuntimeError, match="insertion_loss_db 不能为负"):
            route_circuit(circuit, placements)

    def test_route_path_topology_aligned(self):
        """同 y 端口: 直线 2 点 0 弯曲。"""
        gc = make_device(
            "gc1", "grating_coupler", 20, 20,
            ports=[("out", 20, 10, "east")],
        )
        mmi = make_device(
            "mmi1", "mmi_1x2", 20, 20,
            ports=[("in", 0, 10, "west")],
        )
        circuit = make_circuit(
            "Straight", [gc, mmi],
            [("gc1", "out", "mmi1", "in")],
            canvas_w=500, canvas_h=300,
        )
        placements = {
            "gc1": {"x": 0.0, "y": 0.0, "w": 20.0, "h": 20.0},
            "mmi1": {"x": 100.0, "y": 0.0, "w": 20.0, "h": 20.0},
        }
        result = route_circuit(circuit, placements)
        path = result["paths"][0]
        assert len(path["points"]) == 2, \
            f"同 y 应为直线（2 点），实际 {len(path['points'])} 点"
        assert path["n_bends"] == 0

    def test_route_path_topology_step(self):
        """不同 y 端口: step S-bend 4 点 2 弯曲。"""
        gc = make_device(
            "gc1", "grating_coupler", 20, 20,
            ports=[("out", 20, 10, "east")],
        )
        mmi = make_device(
            "mmi1", "mmi_1x2", 20, 20,
            ports=[("in", 0, 10, "west")],
        )
        circuit = make_circuit(
            "Step", [gc, mmi],
            [("gc1", "out", "mmi1", "in")],
            canvas_w=500, canvas_h=300,
        )
        placements = {
            "gc1": {"x": 0.0, "y": 0.0, "w": 20.0, "h": 20.0},
            "mmi1": {"x": 100.0, "y": 30.0, "w": 20.0, "h": 20.0},
        }
        result = route_circuit(circuit, placements)
        path = result["paths"][0]
        assert len(path["points"]) == 4, \
            f"不同 y 应为 step（4 点），实际 {len(path['points'])} 点"
        assert path["n_bends"] == 2

    def test_route_device_insertion_loss(self):
        """回归测试: 路径损耗含 dev2 插入损耗, total 含所有器件去重(R05)。

        构造 gc1(insertion_loss=1.9) → mmi1(insertion_loss=0.4) 单连接电路:
        - 路径 (20,10)→(100,2.5), step 拓扑 2 弯曲, 长度 87.5μm
        - 波导损耗 = 传播(3.0*87.5/1e4=0.02625) + 弯曲(2*0.05=0.1) = 0.12625
        - 路径级 loss_db = 波导损耗 + dev2(mmi1)插入损耗(0.4) = 0.52625
        - total = 波导损耗 + 所有器件去重(gc1=1.9 + mmi1=0.4) = 2.42625

        来源: SiEPIC EBeam PDK GC 1.9dB / MMI1x2 0.4dB
          https://github.com/SiEPIC/SiEPIC_EBeam_PDK
        """
        gc = make_device(
            "gc1", "grating_coupler", 20, 20,
            ports=[("out", 20, 10, "east")],
            params={"insertion_loss_db": 1.9},
        )
        mmi = make_device(
            "mmi1", "mmi_1x2", 20, 5,
            ports=[("in", 0, 2.5, "west")],
            params={"insertion_loss_db": 0.4},
        )
        circuit = make_circuit(
            "InsertionLoss", [gc, mmi],
            [("gc1", "out", "mmi1", "in")],
            canvas_w=500, canvas_h=300,
        )
        placements = {
            "gc1": {"x": 0.0, "y": 0.0, "w": 20.0, "h": 20.0},
            "mmi1": {"x": 100.0, "y": 0.0, "w": 20.0, "h": 5.0},
        }
        result = route_circuit(circuit, placements)

        path = result["paths"][0]
        expected_waveguide = 3.0 * 87.5 / 1e4 + 2 * 0.05  # 0.12625
        expected_path = expected_waveguide + 0.4  # 0.52625
        assert abs(path["loss_db"] - expected_path) < 1e-9

        expected_total = expected_waveguide + 1.9 + 0.4  # 2.42625
        assert abs(result["total_loss_db"] - expected_total) < 1e-9
        # total 必须包含起始器件 gc1(1.9), 故 > 2.3
        assert result["total_loss_db"] > 2.3

    def test_route_invalid_circuit_dict(self):
        """circuit 非 dict 应 raise RuntimeError（R03 禁止 fall-back）。"""
        placements = {"gc1": {"x": 0.0, "y": 0.0, "w": 20.0, "h": 20.0}}
        with pytest.raises(RuntimeError, match="circuit 必须是 dict"):
            route_circuit("not a dict", placements)
        with pytest.raises(RuntimeError, match="circuit 必须是 dict"):
            route_circuit(None, placements)

    def test_route_invalid_placements(self):
        """placements 非 dict 应 raise RuntimeError（R03 禁止 fall-back）。"""
        circuit = _make_mzi_circuit()
        with pytest.raises(RuntimeError, match="placements 必须是 dict"):
            route_circuit(circuit, "not a dict")
        with pytest.raises(RuntimeError, match="placements 必须是 dict"):
            route_circuit(circuit, None)

    def test_route_zero_canvas_raises(self):
        """画布尺寸为 0 应 raise RuntimeError（R03 禁止 fall-back）。"""
        gc = make_device(
            "gc1", "grating_coupler", 20, 20,
            ports=[("out", 20, 10, "east")],
        )
        circuit = make_circuit("Zero", [gc], [], canvas_w=0, canvas_h=300)
        placements = {"gc1": {"x": 0.0, "y": 0.0, "w": 20.0, "h": 20.0}}
        with pytest.raises(RuntimeError, match="画布尺寸必须为正"):
            route_circuit(circuit, placements)

    def test_route_duplicate_device_name(self):
        """器件名重复应 raise RuntimeError（R03 禁止 fall-back）。"""
        # 直接构造 circuit dict 绕过 make_circuit 校验
        circuit = {
            "name": "Dup",
            "devices": [
                {"name": "gc1", "device_type": "gc", "width_um": 20,
                 "height_um": 20, "ports": [("out", 20, 10, "east")], "params": {}},
                {"name": "gc1", "device_type": "gc", "width_um": 20,
                 "height_um": 20, "ports": [("in", 0, 10, "west")], "params": {}},
            ],
            "connections": [],
            "canvas_w": 500,
            "canvas_h": 300,
        }
        placements = {"gc1": {"x": 0.0, "y": 0.0, "w": 20.0, "h": 20.0}}
        with pytest.raises(RuntimeError, match="器件名重复"):
            route_circuit(circuit, placements)

    def test_route_invalid_connection_format(self):
        """connection 非长度 4 应 raise RuntimeError（R03 禁止 fall-back）。"""
        circuit = {
            "name": "BadConn",
            "devices": [
                {"name": "gc1", "device_type": "gc", "width_um": 20,
                 "height_um": 20, "ports": [("out", 20, 10, "east")], "params": {}},
            ],
            "connections": [["gc1", "out"]],  # 长度 2，非法
            "canvas_w": 500,
            "canvas_h": 300,
        }
        placements = {"gc1": {"x": 0.0, "y": 0.0, "w": 20.0, "h": 20.0}}
        with pytest.raises(RuntimeError, match="connection 必须是长度 4"):
            route_circuit(circuit, placements)

    def test_route_unknown_device_in_connection(self):
        """连接引用不存在的器件应 raise RuntimeError（R03 禁止 fall-back）。"""
        gc = make_device(
            "gc1", "grating_coupler", 20, 20,
            ports=[("out", 20, 10, "east")],
        )
        circuit = make_circuit(
            "Unknown", [gc],
            [("gc1", "out", "ghost", "in")],  # ghost 不在 devices
            canvas_w=500, canvas_h=300,
        )
        placements = {"gc1": {"x": 0.0, "y": 0.0, "w": 20.0, "h": 20.0}}
        with pytest.raises(RuntimeError, match="引用了不存在的器件"):
            route_circuit(circuit, placements)

    def test_route_placement_missing_xy(self):
        """placements 器件缺 x/y 字段应 raise RuntimeError（R03）。"""
        gc = make_device(
            "gc1", "grating_coupler", 20, 20,
            ports=[("out", 20, 10, "east")],
        )
        mmi = make_device(
            "mmi1", "mmi_1x2", 20, 5,
            ports=[("in", 0, 2.5, "west")],
        )
        circuit = make_circuit(
            "Link", [gc, mmi],
            [("gc1", "out", "mmi1", "in")],
            canvas_w=500, canvas_h=300,
        )
        # mmi1 缺 y 字段
        placements = {
            "gc1": {"x": 0.0, "y": 0.0, "w": 20.0, "h": 20.0},
            "mmi1": {"x": 100.0, "w": 20.0, "h": 5.0},
        }
        with pytest.raises(RuntimeError, match="缺少字段"):
            route_circuit(circuit, placements)

    def test_route_invalid_params_type(self):
        """器件 params 非 dict 应 raise RuntimeError（R03 禁止 fall-back）。"""
        circuit = {
            "name": "BadParams",
            "devices": [
                {"name": "gc1", "device_type": "gc", "width_um": 20,
                 "height_um": 20, "ports": [("out", 20, 10, "east")],
                 "params": "not a dict"},
                {"name": "mmi1", "device_type": "mmi", "width_um": 20,
                 "height_um": 5, "ports": [("in", 0, 2.5, "west")], "params": {}},
            ],
            "connections": [["gc1", "out", "mmi1", "in"]],
            "canvas_w": 500,
            "canvas_h": 300,
        }
        placements = {
            "gc1": {"x": 0.0, "y": 0.0, "w": 20.0, "h": 20.0},
            "mmi1": {"x": 100.0, "y": 0.0, "w": 20.0, "h": 5.0},
        }
        with pytest.raises(RuntimeError, match="params 必须是 dict"):
            route_circuit(circuit, placements)
