"""R22 路标 OptoDesigner Advanced Connectors Module 对齐测试。

测试内容:
1. TestEulerBend: 欧拉弯曲测试（5个）
2. TestLengthDefinedConnector: 等长连接器测试（4个）
3. TestPhaseMatchedRouter: 相位匹配路由测试（4个）
4. TestRFGSGRouter: RF GSG 路由测试（3个）
5. TestBusRouter: 总线路由测试（3个）
6. TestHighOrderBezierConnector: 高阶贝塞尔测试（3个）
7. TestR22Integration: R22 集成测试（3个）

来源:
- R22 路标: OptoDesigner Advanced Connectors Module 对齐
- Hong 2021 Photonics Research: https://doi.org/10.1364/PRJ.437726
- Yu 2026 Photonics Research: https://doi.org/10.1364/PRJ.574190
- OptoDesigner Advanced Connectors: https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/advanced-connectors-module.html
- Ghione & Naldi 1987 IEEE TMTT: https://doi.org/10.1109/TMTT.1987.1133623
"""

from __future__ import annotations

import math

from polaris.router.advanced_connectors import (
    BusRouter,
    EulerBend,
    EulerBendConfig,
    HighOrderBezierConnector,
    LengthDefinedConnector,
    PhaseMatchedRouter,
    RFGSGRouter,
)


# ---------------------------------------------------------------------------
# 1. TestEulerBend — 欧拉弯曲测试
# ---------------------------------------------------------------------------
class TestEulerBend:
    """欧拉弯曲连接器测试（Hong 2021 Photonics Research）。"""

    def test_compute_path(self):
        """欧拉螺旋路径计算：返回指定点数的路径。"""
        config = EulerBendConfig(radius=10.0, angle=90.0, n_points=50)
        bend = EulerBend(config)
        path = bend.compute_path()
        assert len(path) == 50
        # 起点应在原点附近
        assert round(path[0][0], 6) == 0.0
        assert round(path[0][1], 6) == 0.0

    def test_compute_length(self):
        """欧拉弯曲长度计算：对称欧拉弯曲总弧长 = 2 * R * angle_rad。"""
        config = EulerBendConfig(radius=10.0, angle=90.0, n_points=100)
        bend = EulerBend(config)
        length = bend.compute_length()
        # 2 * 10 * (π/2) = 10π ≈ 31.4159
        expected = 2.0 * 10.0 * math.pi / 2.0
        assert round(length, 4) == round(expected, 4)

    def test_compute_loss(self):
        """欧拉弯曲损耗计算：传播损耗 0.28 dB/cm（Hong 2021）。"""
        config = EulerBendConfig(radius=10.0, angle=90.0, n_points=100)
        bend = EulerBend(config)
        loss = bend.compute_loss(alpha=0.28)
        # 长度 = 10π μm = 0.00314159 cm
        # 损耗 = 0.28 * 0.00314159 ≈ 0.0008796 dB
        expected = 0.28 * (bend.compute_length() / 1e4)
        assert round(loss, 6) == round(expected, 6)
        assert loss > 0.0

    def test_low_loss(self):
        """欧拉弯曲低损耗特性：损耗应远低于 0.01 dB。"""
        config = EulerBendConfig(radius=10.0, angle=90.0, n_points=100)
        bend = EulerBend(config)
        loss = bend.compute_loss()
        # 10π μm ≈ 31.4 μm ≈ 0.00314 cm，损耗 ≈ 0.00088 dB
        assert loss < 0.01, f"欧拉弯曲损耗 {loss} 应 < 0.01 dB"

    def test_curvature_continuous(self):
        """曲率连续性：相邻点曲率差应很小（无突变）。"""
        config = EulerBendConfig(radius=10.0, angle=90.0, n_points=200)
        bend = EulerBend(config)
        path = bend.compute_path()
        # 计算每段方向角，检查无突变
        angles = []
        for i in range(1, len(path)):
            dx = path[i][0] - path[i - 1][0]
            dy = path[i][1] - path[i - 1][1]
            angles.append(math.atan2(dy, dx))
        # 相邻角度差应平滑（无大于 π/4 的突变）
        for i in range(1, len(angles)):
            diff = abs(angles[i] - angles[i - 1])
            if diff > math.pi:
                diff = 2 * math.pi - diff
            assert diff < math.pi / 4, (
                f"角度突变 {math.degrees(diff):.1f}° > 45°"
            )


# ---------------------------------------------------------------------------
# 2. TestLengthDefinedConnector — 等长连接器测试
# ---------------------------------------------------------------------------
class TestLengthDefinedConnector:
    """路径长度定义连接器测试（OptoDesigner Advanced Connectors）。"""

    def test_route_equal_length(self):
        """等长路由：生成指定长度的路径。"""
        connector = LengthDefinedConnector()
        start = (0.0, 0.0)
        end = (10.0, 0.0)
        target = 20.0
        path = connector.route_equal_length(start, end, target)
        assert len(path) >= 2
        assert path[0] == start
        assert path[-1] == end
        # 实际路径长度应接近目标长度
        actual = _path_length(path)
        assert round(actual, 1) == round(target, 1), (
            f"路径长度 {actual} ≠ 目标 {target}"
        )

    def test_route_phase_matched(self):
        """相位匹配路由：多臂等长。"""
        connector = LengthDefinedConnector()
        arms = [
            ((0.0, 0.0), (10.0, 0.0)),
            ((0.0, 5.0), (15.0, 5.0)),
        ]
        paths = connector.route_phase_matched(arms)
        assert len(paths) == 2
        # 两臂长度应相等
        l1 = _path_length(paths[0])
        l2 = _path_length(paths[1])
        assert round(l1, 4) == round(l2, 4), (
            f"臂 1 长度 {l1} ≠ 臂 2 长度 {l2}"
        )

    def test_target_length_accuracy(self):
        """目标长度精度：实际长度与目标长度误差 < 1%。"""
        connector = LengthDefinedConnector()
        start = (0.0, 0.0)
        end = (20.0, 0.0)
        target = 30.0
        path = connector.route_equal_length(start, end, target)
        actual = _path_length(path)
        error = abs(actual - target) / target
        assert error < 0.01, f"长度误差 {error:.2%} > 1%"

    def test_mzi_arms(self):
        """MZI 两臂等长：两臂长度差应 < 0.01 μm。"""
        connector = LengthDefinedConnector()
        arms = [
            ((0.0, 0.0), (50.0, 0.0)),
            ((0.0, 10.0), (50.0, 10.0)),
        ]
        paths = connector.route_phase_matched(arms)
        l1 = _path_length(paths[0])
        l2 = _path_length(paths[1])
        assert abs(l1 - l2) < 0.01, f"臂长差 {abs(l1 - l2)} > 0.01 μm"


# ---------------------------------------------------------------------------
# 3. TestPhaseMatchedRouter — 相位匹配路由测试
# ---------------------------------------------------------------------------
class TestPhaseMatchedRouter:
    """相位匹配路由器测试（OptoDesigner Advanced Connectors）。"""

    def test_route_mzi_arms(self):
        """MZI 两臂等长路由：返回等长路径对。"""
        router = PhaseMatchedRouter(wavelength=1.55, neff=2.34)
        arm1, arm2 = router.route_mzi_arms(
            (0.0, 0.0), (50.0, 0.0),
            (0.0, 10.0), (50.0, 10.0),
        )
        assert len(arm1) >= 2
        assert len(arm2) >= 2
        l1 = _path_length(arm1)
        l2 = _path_length(arm2)
        assert round(l1, 4) == round(l2, 4)

    def test_route_differential_pair(self):
        """差分对等长路由：所有对长度相等。"""
        router = PhaseMatchedRouter()
        pairs = [
            ((0.0, 0.0), (30.0, 0.0)),
            ((0.0, 5.0), (30.0, 5.0)),
            ((0.0, 10.0), (30.0, 10.0)),
        ]
        paths = router.route_differential_pair(pairs)
        assert len(paths) == 3
        lengths = [_path_length(p) for p in paths]
        for length in lengths:
            assert round(length, 4) == round(lengths[0], 4)

    def test_compute_phase_mismatch(self):
        """相位失配计算：Δφ = (2π/λ) * neff * ΔL。"""
        router = PhaseMatchedRouter(wavelength=1.55, neff=2.34)
        # 路径 1 长度 = 10，路径 2 长度 = 10.5
        path1 = [(0.0, 0.0), (10.0, 0.0)]
        path2 = [(0.0, 0.0), (10.5, 0.0)]
        mismatch = router.compute_phase_mismatch(path1, path2)
        # ΔL = 0.5，Δφ = (2π/1.55) * 2.34 * 0.5
        expected = (2.0 * math.pi / 1.55) * 2.34 * 0.5
        assert round(mismatch, 4) == round(expected, 4)

    def test_phase_matched(self):
        """相位匹配验证：等长路径相位失配应 < λ/10 对应相位。"""
        router = PhaseMatchedRouter(wavelength=1.55, neff=2.34)
        arm1, arm2 = router.route_mzi_arms(
            (0.0, 0.0), (50.0, 0.0),
            (0.0, 10.0), (50.0, 10.0),
        )
        mismatch = router.compute_phase_mismatch(arm1, arm2)
        # λ/10 对应相位 = 2π/10 = 0.628 rad
        assert mismatch < 2.0 * math.pi / 10.0, (
            f"相位失配 {mismatch} > λ/10 ({2.0 * math.pi / 10.0})"
        )


# ---------------------------------------------------------------------------
# 4. TestRFGSGRouter — RF GSG 路由测试
# ---------------------------------------------------------------------------
class TestRFGSGRouter:
    """RF GSG 电极路由测试（OptoDesigner Advanced Connectors）。"""

    def test_route_gsg(self):
        """GSG 路由：返回 signal + ground1 + ground2 三条路径。"""
        router = RFGSGRouter(
            signal_width=10.0, ground_width=20.0, gap=5.0
        )
        result = router.route_gsg((0.0, 0.0), (100.0, 0.0))
        assert "signal" in result
        assert "ground1" in result
        assert "ground2" in result
        # 信号导体应从起点到终点
        assert result["signal"][0] == (0.0, 0.0)
        assert result["signal"][-1] == (100.0, 0.0)
        # 地导体应平行偏移
        assert len(result["ground1"]) == 2
        assert len(result["ground2"]) == 2

    def test_compute_impedance(self):
        """特征阻抗计算：Ghione & Naldi 1987 共面波导公式。"""
        router = RFGSGRouter(
            signal_width=10.0, ground_width=20.0, gap=5.0
        )
        z0 = router.compute_impedance()
        # 典型 GSG 共面波导阻抗应在 30-100 Ω 范围
        assert 30.0 < z0 < 100.0, f"阻抗 {z0} 超出典型范围 30-100 Ω"

    def test_gsg_geometry(self):
        """GSG 几何验证：地导体应在信号导体两侧对称。"""
        router = RFGSGRouter(
            signal_width=10.0, ground_width=20.0, gap=5.0
        )
        result = router.route_gsg((0.0, 0.0), (100.0, 0.0))
        sig = result["signal"]
        g1 = result["ground1"]
        g2 = result["ground2"]
        # 信号导体中点
        sig_mid = ((sig[0][0] + sig[1][0]) / 2, (sig[0][1] + sig[1][1]) / 2)
        # 地导体 1 中点
        g1_mid = ((g1[0][0] + g1[1][0]) / 2, (g1[0][1] + g1[1][1]) / 2)
        # 地导体 2 中点
        g2_mid = ((g2[0][0] + g2[1][0]) / 2, (g2[0][1] + g2[1][1]) / 2)
        # 两侧地导体到信号导体的距离应相等
        d1 = math.hypot(g1_mid[0] - sig_mid[0], g1_mid[1] - sig_mid[1])
        d2 = math.hypot(g2_mid[0] - sig_mid[0], g2_mid[1] - sig_mid[1])
        assert round(d1, 4) == round(d2, 4), (
            f"地导体不对称：d1={d1}, d2={d2}"
        )
        # 偏移距离 = signal_width/2 + gap + ground_width/2 = 5 + 5 + 10 = 20
        expected_offset = 10.0 / 2.0 + 5.0 + 20.0 / 2.0
        assert round(d1, 4) == round(expected_offset, 4)


# ---------------------------------------------------------------------------
# 5. TestBusRouter — 总线路由测试
# ---------------------------------------------------------------------------
class TestBusRouter:
    """总线路由器测试（OptoDesigner Advanced Connectors）。"""

    def test_route_bus_serial(self):
        """串联总线：器件依次连接。"""
        router = BusRouter()
        devices = [
            {"in_port": (0.0, 0.0), "out_port": (10.0, 0.0)},
            {"in_port": (20.0, 0.0), "out_port": (30.0, 0.0)},
            {"in_port": (40.0, 0.0), "out_port": (50.0, 0.0)},
        ]
        paths = router.route_bus(devices, bus_type="serial")
        assert len(paths) == 1
        # 串联路径应包含所有器件的端口
        path = paths[0]
        assert (0.0, 0.0) in path
        assert (50.0, 0.0) in path

    def test_route_bus_parallel(self):
        """并联总线：每器件独立路径。"""
        router = BusRouter()
        devices = [
            {"in_port": (0.0, 0.0), "out_port": (10.0, 0.0)},
            {"in_port": (0.0, 5.0), "out_port": (10.0, 5.0)},
            {"in_port": (0.0, 10.0), "out_port": (10.0, 10.0)},
        ]
        paths = router.route_bus(devices, bus_type="parallel")
        assert len(paths) == 3
        for p in paths:
            assert len(p) == 2

    def test_bus_topology(self):
        """总线拓扑验证：串联路径点数 = 2 * n_devices。"""
        router = BusRouter()
        n = 4
        devices = [
            {"in_port": (float(i) * 20.0, 0.0),
             "out_port": (float(i) * 20.0 + 10.0, 0.0)}
            for i in range(n)
        ]
        paths = router.route_bus(devices, bus_type="serial")
        # 串联：每个器件 2 个端口，但相邻器件间共享连接点
        # 路径点数 = 2 * n（每个器件 in + out）
        assert len(paths[0]) == 2 * n


# ---------------------------------------------------------------------------
# 6. TestHighOrderBezierConnector — 高阶贝塞尔测试
# ---------------------------------------------------------------------------
class TestHighOrderBezierConnector:
    """高阶贝塞尔连接器测试（Yu 2026 Photonics Research）。"""

    def test_compute_path(self):
        """高阶贝塞尔路径计算：返回 100 个采样点。"""
        connector = HighOrderBezierConnector(order=5)
        path = connector.compute_path(
            (0.0, 0.0), (10.0, 10.0), 0.0, 90.0
        )
        assert len(path) == 100
        # 起点终点对齐
        assert round(path[0][0], 6) == 0.0
        assert round(path[0][1], 6) == 0.0
        assert round(path[-1][0], 6) == 10.0
        assert round(path[-1][1], 6) == 10.0

    def test_compute_control_points(self):
        """控制点计算：返回 order + 1 个控制点。"""
        connector = HighOrderBezierConnector(order=5)
        cp = connector.compute_control_points(
            (0.0, 0.0), (10.0, 0.0), 0.0, 0.0, 5
        )
        assert len(cp) == 6  # order + 1
        # 首尾控制点 = 起止点
        assert cp[0] == (0.0, 0.0)
        assert cp[-1] == (10.0, 0.0)

    def test_arbitrary_angle(self):
        """任意角度多模弯曲：支持 60°/90°/120°/180°。"""
        connector = HighOrderBezierConnector(order=5)
        for angle in (60.0, 90.0, 120.0, 180.0):
            path = connector.compute_path(
                (0.0, 0.0),
                (10.0 * math.cos(math.radians(angle)),
                 10.0 * math.sin(math.radians(angle))),
                0.0,
                angle,
            )
            assert len(path) == 100
            # 起点对齐
            assert round(path[0][0], 6) == 0.0
            assert round(path[0][1], 6) == 0.0
            # 终点对齐
            assert round(path[-1][0], 4) == round(
                10.0 * math.cos(math.radians(angle)), 4
            )
            assert round(path[-1][1], 4) == round(
                10.0 * math.sin(math.radians(angle)), 4
            )


# ---------------------------------------------------------------------------
# 7. TestR22Integration — R22 集成测试
# ---------------------------------------------------------------------------
class TestR22Integration:
    """R22 集成测试（MZI 完整流程 + OptoDesigner 对齐 + 综合得分）。"""

    def test_end_to_end_mzi(self):
        """MZI 完整连接器流程：欧拉弯曲 + 等长路由 + 相位匹配。"""
        # 1. 欧拉弯曲（低损耗弯曲段）
        euler_config = EulerBendConfig(radius=10.0, angle=90.0, n_points=50)
        bend = EulerBend(euler_config)
        bend_path = bend.compute_path()
        assert len(bend_path) == 50
        bend_loss = bend.compute_loss()
        assert bend_loss < 0.01

        # 2. MZI 两臂等长路由
        router = PhaseMatchedRouter(wavelength=1.55, neff=2.34)
        arm1, arm2 = router.route_mzi_arms(
            (0.0, 0.0), (50.0, 0.0),
            (0.0, 10.0), (50.0, 10.0),
        )
        l1 = _path_length(arm1)
        l2 = _path_length(arm2)
        assert round(l1, 4) == round(l2, 4)

        # 3. 相位失配验证
        mismatch = router.compute_phase_mismatch(arm1, arm2)
        assert mismatch < 2.0 * math.pi / 10.0  # < λ/10

        # 4. RF GSG 电极布线（调制器电极）
        gsg_router = RFGSGRouter(
            signal_width=10.0, ground_width=20.0, gap=5.0
        )
        gsg = gsg_router.route_gsg((0.0, 0.0), (100.0, 0.0))
        assert len(gsg) == 3
        z0 = gsg_router.compute_impedance()
        assert 30.0 < z0 < 100.0

    def test_optodesigner_alignment(self):
        """OptoDesigner Advanced Connectors 对齐度 ≥ 90%。

        验证 OptoDesigner Advanced Connectors Module 的六大核心特性：
        1. 欧拉弯曲连接器（低损耗）
        2. 路径长度定义连接器（等长约束）
        3. 相位匹配路由（MZI 臂）
        4. RF GSG 电极路由
        5. 总线路由
        6. 高阶贝塞尔连接器（任意角度）
        """
        features_total = 10
        features_passed = 0

        # 1. 欧拉弯曲连接器（2 项）
        config = EulerBendConfig(radius=10.0, angle=90.0, n_points=50)
        bend = EulerBend(config)
        path = bend.compute_path()
        if len(path) == 50:
            features_passed += 1
        if bend.compute_loss() < 0.01:
            features_passed += 1

        # 2. 路径长度定义连接器（2 项）
        connector = LengthDefinedConnector()
        eq_path = connector.route_equal_length((0.0, 0.0), (10.0, 0.0), 20.0)
        if len(eq_path) >= 2 and _path_length(eq_path) >= 19.9:
            features_passed += 1
        arms = connector.route_phase_matched([
            ((0.0, 0.0), (10.0, 0.0)),
            ((0.0, 5.0), (15.0, 5.0)),
        ])
        if len(arms) == 2:
            l1 = _path_length(arms[0])
            l2 = _path_length(arms[1])
            if round(l1, 4) == round(l2, 4):
                features_passed += 1

        # 3. 相位匹配路由（2 项）
        pm_router = PhaseMatchedRouter()
        a1, a2 = pm_router.route_mzi_arms(
            (0.0, 0.0), (50.0, 0.0),
            (0.0, 10.0), (50.0, 10.0),
        )
        if len(a1) >= 2 and len(a2) >= 2:
            features_passed += 1
        mismatch = pm_router.compute_phase_mismatch(a1, a2)
        if mismatch < 2.0 * math.pi / 10.0:
            features_passed += 1

        # 4. RF GSG 路由（1 项）
        gsg_router = RFGSGRouter()
        gsg = gsg_router.route_gsg((0.0, 0.0), (100.0, 0.0))
        if len(gsg) == 3 and len(gsg["signal"]) >= 2:
            features_passed += 1

        # 5. 总线路由（1 项）
        bus_router = BusRouter()
        devices = [
            {"in_port": (0.0, 0.0), "out_port": (10.0, 0.0)},
            {"in_port": (20.0, 0.0), "out_port": (30.0, 0.0)},
        ]
        bus_paths = bus_router.route_bus(devices, "serial")
        if len(bus_paths) == 1 and len(bus_paths[0]) >= 2:
            features_passed += 1

        # 6. 高阶贝塞尔连接器（2 项）
        bezier = HighOrderBezierConnector(order=5)
        b_path = bezier.compute_path(
            (0.0, 0.0), (10.0, 10.0), 0.0, 90.0
        )
        if len(b_path) == 100:
            features_passed += 1
        cp = bezier.compute_control_points(
            (0.0, 0.0), (10.0, 0.0), 0.0, 0.0, 5
        )
        if len(cp) == 6:
            features_passed += 1

        alignment = features_passed / features_total
        assert alignment >= 0.9, (
            f"OptoDesigner Advanced Connectors 对齐度 {alignment:.0%} < 90%"
        )

    def test_comprehensive_score(self):
        """综合得分评估（目标 ≥ 8.3）。

        评分维度（每项 1.0 分，共 10 项）：
        1. 欧拉弯曲路径计算
        2. 欧拉弯曲低损耗（< 0.01 dB）
        3. 等长路由精度（误差 < 1%）
        4. 相位匹配多臂等长
        5. MZI 两臂相位匹配（< λ/10）
        6. RF GSG 三导体路由
        7. RF GSG 阻抗计算（30-100 Ω）
        8. 串联总线路由
        9. 高阶贝塞尔任意角度
        10. 高阶贝塞尔控制点
        """
        score = 0.0

        # 1. 欧拉弯曲路径计算
        config = EulerBendConfig(radius=10.0, angle=90.0, n_points=50)
        bend = EulerBend(config)
        path = bend.compute_path()
        if len(path) == 50 and round(path[0][0], 6) == 0.0:
            score += 1.0

        # 2. 欧拉弯曲低损耗
        if bend.compute_loss() < 0.01:
            score += 1.0

        # 3. 等长路由精度
        connector = LengthDefinedConnector()
        eq_path = connector.route_equal_length(
            (0.0, 0.0), (20.0, 0.0), 30.0
        )
        actual = _path_length(eq_path)
        if abs(actual - 30.0) / 30.0 < 0.01:
            score += 1.0

        # 4. 相位匹配多臂等长
        arms = connector.route_phase_matched([
            ((0.0, 0.0), (10.0, 0.0)),
            ((0.0, 5.0), (15.0, 5.0)),
        ])
        l1 = _path_length(arms[0])
        l2 = _path_length(arms[1])
        if round(l1, 4) == round(l2, 4):
            score += 1.0

        # 5. MZI 两臂相位匹配
        pm_router = PhaseMatchedRouter()
        a1, a2 = pm_router.route_mzi_arms(
            (0.0, 0.0), (50.0, 0.0),
            (0.0, 10.0), (50.0, 10.0),
        )
        mismatch = pm_router.compute_phase_mismatch(a1, a2)
        if mismatch < 2.0 * math.pi / 10.0:
            score += 1.0

        # 6. RF GSG 三导体路由
        gsg_router = RFGSGRouter()
        gsg = gsg_router.route_gsg((0.0, 0.0), (100.0, 0.0))
        if len(gsg) == 3 and "signal" in gsg and "ground1" in gsg:
            score += 1.0

        # 7. RF GSG 阻抗计算
        z0 = gsg_router.compute_impedance()
        if 30.0 < z0 < 100.0:
            score += 1.0

        # 8. 串联总线路由
        bus_router = BusRouter()
        devices = [
            {"in_port": (0.0, 0.0), "out_port": (10.0, 0.0)},
            {"in_port": (20.0, 0.0), "out_port": (30.0, 0.0)},
        ]
        bus_paths = bus_router.route_bus(devices, "serial")
        if len(bus_paths) == 1 and len(bus_paths[0]) >= 2:
            score += 1.0

        # 9. 高阶贝塞尔任意角度
        bezier = HighOrderBezierConnector(order=5)
        b_path = bezier.compute_path(
            (0.0, 0.0), (10.0, 10.0), 0.0, 90.0
        )
        if len(b_path) == 100:
            score += 1.0

        # 10. 高阶贝塞尔控制点
        cp = bezier.compute_control_points(
            (0.0, 0.0), (10.0, 0.0), 0.0, 0.0, 5
        )
        if len(cp) == 6 and cp[0] == (0.0, 0.0) and cp[-1] == (10.0, 0.0):
            score += 1.0

        # 综合得分 = score，目标 ≥ 8.3
        assert score >= 8.3, f"综合得分 {score} < 8.3"


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------


def _path_length(path: list[tuple[float, float]]) -> float:
    """计算路径总长度（μm）。"""
    if len(path) < 2:
        return 0.0
    total = 0.0
    for i in range(1, len(path)):
        total += math.hypot(
            path[i][0] - path[i - 1][0], path[i][1] - path[i - 1][1]
        )
    return total
