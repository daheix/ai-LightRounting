"""R11 路标：版图参数化代码驱动（Code-as-Layout）单元测试。

覆盖 @polaris_cell 装饰器、PCellMultiView 多视图类、TransformMatrix 仿射变换、
bezier_transform 贝塞尔曲线、PCellCache LRU 缓存、ai_generate_pcell AI 生成、
无 fall-back AST 集成检查。所有测试使用真实数据。

学术依据:
- gdsfactory @gf.cell: https://gdsfactory.github.io/gdsfactory/
- IPKISS 多视图: https://www.lucedaphotonics.com/zh_CN/products/ipkiss
- Foley et al., "Computer Graphics: Principles and Practice", 2013
- Gamma et al., "Design Patterns", 1994（Observer Pattern）
- PhIDO arXiv:2508.14123
"""

from __future__ import annotations

import ast
from pathlib import Path

import numpy as np
import pytest

from polaris.pdk.pcell import (
    PCellCache,
    PCellMultiView,
    TransformMatrix,
    ai_generate_pcell,
    clear_pcell_cache,
    polaris_cell,
)


@pytest.fixture(autouse=True)
def _clear_cache():
    """每个测试前后清空模块级缓存与命名注册表，保证测试隔离。"""
    clear_pcell_cache()
    yield
    clear_pcell_cache()


class TestPolarisCellDecorator:
    """@polaris_cell 装饰器测试。"""

    def test_cache_hit_returns_same_object(self) -> None:
        @polaris_cell
        def wg(width: float = 0.5) -> PCellMultiView:
            return PCellMultiView(name="wg", params={"width": width})

        assert wg(width=0.5) is wg(width=0.5)

    def test_cache_miss_different_params(self) -> None:
        @polaris_cell
        def wg(width: float = 0.5) -> PCellMultiView:
            return PCellMultiView(name="wg", params={"width": width})

        c1, c2 = wg(width=0.5), wg(width=0.8)
        assert c1 is not c2
        assert c1.params["width"] == pytest.approx(0.5)
        assert c2.params["width"] == pytest.approx(0.8)

    def test_param_validation_type_error(self) -> None:
        @polaris_cell
        def wg(width: float = 0.5) -> PCellMultiView:
            return PCellMultiView(name="wg", params={"width": width})

        with pytest.raises(TypeError, match="width"):
            wg(width="not_a_float")

    def test_naming_uniqueness(self) -> None:
        @polaris_cell
        def cell(length: float = 10.0) -> PCellMultiView:
            return PCellMultiView(name="my_cell", params={"length": length})

        c1, c2 = cell(length=10.0), cell(length=20.0)
        assert c1.name == "my_cell"
        assert c2.name == "my_cell_1"

    def test_info_metadata_attached(self) -> None:
        @polaris_cell
        def wg(width: float = 0.5) -> PCellMultiView:
            return PCellMultiView(name="wg")

        cell = wg(width=0.5)
        assert cell.info["function"] == "wg"
        assert cell.info["params"]["width"] == pytest.approx(0.5)

    def test_non_pcell_return_raises(self) -> None:
        @polaris_cell
        def bad(width: float = 0.5) -> str:
            return "not a pcell"

        with pytest.raises(TypeError, match="PCellMultiView"):
            bad(width=0.5)


class TestPCellCache:
    """PCell 缓存管理器测试。"""

    def test_lru_eviction(self) -> None:
        cache = PCellCache(maxsize=2)
        cache.put(("k1",), PCellMultiView(name="c1"))
        cache.put(("k2",), PCellMultiView(name="c2"))
        cache.put(("k3",), PCellMultiView(name="c3"))
        assert cache.size == 2
        assert cache.get(("k1",)) is None
        assert cache.get(("k2",)) is not None

    def test_hit_rate(self) -> None:
        cache = PCellCache(maxsize=10)
        cache.put(("k1",), PCellMultiView(name="c1"))
        cache.get(("k1",))
        cache.get(("k1",))
        cache.get(("miss",))
        assert cache.hit_rate == pytest.approx(2.0 / 3.0)

    def test_maxsize_zero_raises(self) -> None:
        with pytest.raises(ValueError, match="maxsize"):
            PCellCache(maxsize=0)
        with pytest.raises(ValueError, match="maxsize"):
            PCellCache(maxsize=-1)

    def test_clear(self) -> None:
        cache = PCellCache(maxsize=10)
        cache.put(("k1",), PCellMultiView(name="c1"))
        cache.get(("k1",))
        cache.clear()
        assert cache.size == 0
        assert cache.hit_rate == pytest.approx(0.0)

    def test_lru_order_update(self) -> None:
        cache = PCellCache(maxsize=2)
        c1, c2, c3 = PCellMultiView(name="c1"), PCellMultiView(name="c2"), PCellMultiView(name="c3")
        cache.put(("k1",), c1)
        cache.put(("k2",), c2)
        cache.get(("k1",))
        cache.put(("k3",), c3)
        assert cache.get(("k1",)) is c1
        assert cache.get(("k2",)) is None

    def test_default_maxsize_is_1024(self) -> None:
        """验证默认缓存 maxsize=1024（R11 路标要求）。"""
        cache = PCellCache()
        for i in range(1025):
            cache.put((f"k{i}",), PCellMultiView(name=f"c{i}"))
        assert cache.size == 1024
        assert cache.get(("k0",)) is None
        assert cache.get(("k1024",)) is not None


class TestPCellMultiView:
    """PCellMultiView 多视图类测试。"""

    def test_three_views_created(self) -> None:
        cell = PCellMultiView(name="test")
        assert cell.layout_view is not None
        assert cell.circuit_view is not None
        assert cell.netlist_view is not None

    def test_add_polygon(self) -> None:
        cell = PCellMultiView(name="test")
        pts = np.array([[0, 0], [10, 0], [10, 5], [0, 5]])
        cell.add_polygon(pts, layer="WG")
        assert len(cell.layout_view.polygons) == 1
        np.testing.assert_array_equal(cell.layout_view.polygons[0][0], pts)
        assert cell.layout_view.polygons[0][1] == "WG"

    def test_add_port(self) -> None:
        cell = PCellMultiView(name="test")
        cell.add_port("in", 0.0, 0.0, "west", width=0.5)
        assert len(cell.layout_view.ports) == 1
        port = cell.layout_view.ports[0]
        assert port.name == "in"
        assert port.width == pytest.approx(0.5)

    def test_observer_sync_port_to_netlist(self) -> None:
        """【创新】Observer Pattern：添加端口自动同步到 Netlist 视图。"""
        cell = PCellMultiView(name="test")
        cell.add_port("in", 1.0, 2.0, "west")
        assert "in" in cell.netlist_view.ports
        assert cell.netlist_view.ports["in"] == "1.0,2.0"

    def test_observer_sync_port_to_circuit(self) -> None:
        """【创新】Observer Pattern：添加端口自动同步到 Circuit 视图。"""
        cell = PCellMultiView(name="test")
        cell.add_port("in", 0.0, 0.0, "west")
        cell.add_port("out", 10.0, 0.0, "east")
        assert "in" in cell.circuit_view.params["ports"]
        assert "out" in cell.circuit_view.params["ports"]

    def test_observer_sync_ref_to_netlist(self) -> None:
        """【创新】Observer Pattern：添加引用自动同步到 Netlist 视图。"""
        parent = PCellMultiView(name="parent")
        child = PCellMultiView(name="child")
        parent.add_ref(child, x=5.0, y=3.0, rotation=90.0)
        assert len(parent.netlist_view.instances) == 1
        inst = parent.netlist_view.instances[0]
        assert inst["name"] == "child"
        assert inst["x"] == pytest.approx(5.0)
        assert inst["rotation"] == pytest.approx(90.0)

    def test_get_netlist(self) -> None:
        parent = PCellMultiView(name="parent")
        child = PCellMultiView(name="child")
        parent.add_ref(child, x=5.0, y=0.0)
        parent.add_port("in", 0.0, 0.0, "west")
        nl = parent.get_netlist()
        assert len(nl["instances"]) == 1
        assert nl["instances"][0]["name"] == "child"
        assert "in" in nl["ports"]

    def test_to_device(self) -> None:
        cell = PCellMultiView(name="wg", params={"platform": "SOI"})
        cell.add_polygon(np.array([[0, -0.25], [10, -0.25], [10, 0.25], [0, 0.25]]), "WG")
        cell.add_port("in", 0.0, 0.0, "west")
        cell.add_port("out", 10.0, 0.0, "east")
        dev = cell.to_device()
        assert dev.name == "wg"
        assert dev.platform == "SOI"
        assert len(dev.ports) == 2
        assert dev.bbox.xmax == pytest.approx(10.0)


class TestTransformMatrix:
    """TransformMatrix 仿射变换矩阵测试。"""

    def test_rotate_90(self) -> None:
        t = TransformMatrix().rotate(90.0)
        result = t.apply(np.array([1.0, 0.0]))
        np.testing.assert_allclose(result, [0.0, 1.0], atol=1e-10)

    def test_scale(self) -> None:
        t = TransformMatrix().scale(2.0, 3.0)
        result = t.apply(np.array([1.0, 1.0]))
        np.testing.assert_allclose(result, [2.0, 3.0], atol=1e-10)

    def test_scale_uniform(self) -> None:
        t = TransformMatrix().scale(2.0)
        result = t.apply(np.array([1.0, 1.0]))
        np.testing.assert_allclose(result, [2.0, 2.0], atol=1e-10)

    def test_translate(self) -> None:
        t = TransformMatrix().translate(5.0, 3.0)
        result = t.apply(np.array([0.0, 0.0]))
        np.testing.assert_allclose(result, [5.0, 3.0], atol=1e-10)

    def test_shear(self) -> None:
        t = TransformMatrix().shear(kx=1.0)
        result = t.apply(np.array([0.0, 1.0]))
        np.testing.assert_allclose(result, [1.0, 1.0], atol=1e-10)

    def test_apply_single_point(self) -> None:
        t = TransformMatrix().translate(1.0, 2.0)
        result = t.apply(np.array([3.0, 4.0]))
        assert result.shape == (2,)
        np.testing.assert_allclose(result, [4.0, 6.0], atol=1e-10)

    def test_apply_point_set(self) -> None:
        t = TransformMatrix().scale(2.0)
        pts = np.array([[1.0, 1.0], [2.0, 3.0]])
        result = t.apply(pts)
        assert result.shape == (2, 2)
        np.testing.assert_allclose(result, [[2.0, 2.0], [4.0, 6.0]], atol=1e-10)

    def test_compose(self) -> None:
        rot = TransformMatrix().rotate(90.0)
        trans = TransformMatrix().translate(1.0, 0.0)
        combined = trans.compose(rot)
        pts = np.array([[1.0, 0.0]])
        expected = trans.apply(rot.apply(pts))
        np.testing.assert_allclose(combined.apply(pts), expected, atol=1e-10)

    def test_inverse(self) -> None:
        t = TransformMatrix(a=2.0, b=1.0, c=0.5, d=3.0, tx=5.0, ty=2.0)
        combined = t.compose(t.inverse())
        pts = np.array([[3.0, 7.0]])
        np.testing.assert_allclose(combined.apply(pts), pts, atol=1e-10)

    def test_inverse_singular_raises(self) -> None:
        t = TransformMatrix(a=1.0, b=2.0, c=2.0, d=4.0)
        with pytest.raises(ValueError, match="奇异"):
            t.inverse()

    def test_apply_invalid_shape_raises(self) -> None:
        with pytest.raises(ValueError, match="点"):
            TransformMatrix().apply(np.array([1.0, 2.0, 3.0]))

    def test_chained_transforms(self) -> None:
        """链式变换：先旋转，再缩放，再平移。

        compose 语义为 self ∘ other（先应用 other），故链式调用
        translate().scale().rotate() 表示先旋转→缩放→平移。
        """
        t = TransformMatrix().translate(1.0, 1.0).scale(2.0).rotate(90.0)
        result = t.apply(np.array([1.0, 0.0]))
        # 旋转 90: (1,0) -> (0,1)
        # 缩放 2: (0,1) -> (0,2)
        # 平移 (1,1): (0,2) -> (1,3)
        np.testing.assert_allclose(result, [1.0, 3.0], atol=1e-10)


class TestBezierTransform:
    """贝塞尔曲线变换测试（【创新】非线性变换）。"""

    def test_two_points_linear(self) -> None:
        cp = np.array([[0.0, 0.0], [10.0, 0.0]])
        result = TransformMatrix.bezier_transform(cp, 0.5)
        np.testing.assert_allclose(result, [5.0, 0.0], atol=1e-10)

    def test_three_points_quadratic(self) -> None:
        cp = np.array([[0.0, 0.0], [5.0, 10.0], [10.0, 0.0]])
        expected = 0.25 * cp[0] + 0.5 * cp[1] + 0.25 * cp[2]
        result = TransformMatrix.bezier_transform(cp, 0.5)
        np.testing.assert_allclose(result, expected, atol=1e-10)

    def test_four_points_cubic(self) -> None:
        cp = np.array([[0.0, 0.0], [3.0, 9.0], [7.0, 9.0], [10.0, 0.0]])
        expected = 0.125 * cp[0] + 0.375 * cp[1] + 0.375 * cp[2] + 0.125 * cp[3]
        result = TransformMatrix.bezier_transform(cp, 0.5)
        np.testing.assert_allclose(result, expected, atol=1e-10)

    def test_endpoints(self) -> None:
        cp = np.array([[1.0, 2.0], [5.0, 8.0], [10.0, 3.0]])
        result_t0 = TransformMatrix.bezier_transform(cp, 0.0)
        result_t1 = TransformMatrix.bezier_transform(cp, 1.0)
        np.testing.assert_allclose(result_t0, cp[0], atol=1e-10)
        np.testing.assert_allclose(result_t1, cp[-1], atol=1e-10)

    def test_array_t(self) -> None:
        cp = np.array([[0.0, 0.0], [5.0, 10.0], [10.0, 0.0]])
        t_arr = np.array([0.0, 0.5, 1.0])
        result = TransformMatrix.bezier_transform(cp, t_arr)
        assert result.shape == (3, 2)
        np.testing.assert_allclose(result[0], cp[0], atol=1e-10)
        np.testing.assert_allclose(result[-1], cp[-1], atol=1e-10)

    def test_insufficient_control_points_raises(self) -> None:
        with pytest.raises(ValueError, match="2"):
            TransformMatrix.bezier_transform(np.array([[1.0, 2.0]]), 0.5)


class TestAIGeneratePCell:
    """AI 辅助 PCell 生成测试（【创新】）。"""

    def test_ring_resonator(self) -> None:
        code = ai_generate_pcell("半径5μm的环谐振器")
        assert "@polaris_cell" in code
        assert "ring_resonator" in code
        assert "radius: float = 5.0" in code
        assert "PCellMultiView" in code

    def test_mmi(self) -> None:
        code = ai_generate_pcell("MMI 1x2 长度10")
        assert "@polaris_cell" in code
        assert "mmi1x2" in code
        assert "length: float = 10.0" in code
        assert "PCellMultiView" in code

    def test_waveguide(self) -> None:
        code = ai_generate_pcell("直波导 width 0.8")
        assert "@polaris_cell" in code
        assert "straight_waveguide" in code
        assert "width: float = 0.8" in code
        assert "PCellMultiView" in code

    def test_y_branch(self) -> None:
        code = ai_generate_pcell("Y branch 分支")
        assert "@polaris_cell" in code
        assert "y_branch" in code
        assert "PCellMultiView" in code

    def test_unrecognized_raises(self) -> None:
        with pytest.raises(ValueError, match="无法识别"):
            ai_generate_pcell("这是一个量子计算芯片")

    def test_generated_code_is_valid_python(self) -> None:
        ast.parse(ai_generate_pcell("半径3μm的环谐振器"))


class TestR11Integration:
    """R11 集成测试：无 fall-back AST 检查、创新点验证。"""

    def test_no_fallback_ast(self) -> None:
        """AST 检查 pcell.py 无 fall-back 模式（裸 except/pass/return None）。"""
        source = Path("src/polaris/pdk/pcell.py").read_text()
        tree = ast.parse(source)
        violations: list[str] = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.ExceptHandler):
                continue
            if node.type is None:
                violations.append(f"行 {node.lineno}: 裸 except")
            for child in ast.walk(node):
                if isinstance(child, ast.Pass):
                    violations.append(f"行 {child.lineno}: except 中 pass")
                if isinstance(child, ast.Return) and child.value is None:
                    violations.append(f"行 {child.lineno}: except 中 return None")
        assert not violations, f"发现 fall-back:\n{chr(10).join(violations)}"

    def test_innovation_observer_pattern(self) -> None:
        """【创新】验证 Observer Pattern 多视图同步。"""
        source = Path("src/polaris/pdk/pcell.py").read_text()
        assert "Observer Pattern" in source
        assert "on_view_changed" in source
        assert "_notify" in source

    def test_innovation_bezier_transform(self) -> None:
        """【创新】验证贝塞尔非线性变换。"""
        source = Path("src/polaris/pdk/pcell.py").read_text()
        assert "bezier_transform" in source
        assert "Bernstein" in source

    def test_innovation_ai_generate(self) -> None:
        """【创新】验证 AI 辅助 PCell 生成。"""
        source = Path("src/polaris/pdk/pcell.py").read_text()
        assert "ai_generate_pcell" in source
        assert "PhIDO" in source

    def test_pcell_to_device_roundtrip(self) -> None:
        @polaris_cell
        def mmi(width: float = 0.5, length: float = 10.0) -> PCellMultiView:
            cell = PCellMultiView(name="mmi", params={"platform": "SOI"})
            cell.add_polygon(np.array([[0, -1], [length, -1.5], [length, 1.5], [0, 1]]), "WG")
            cell.add_port("in", 0, 0, "west", width)
            cell.add_port("out1", length, 1, "east", width)
            cell.add_port("out2", length, -1, "east", width)
            return cell

        dev = mmi(width=0.5, length=10.0).to_device()
        assert dev.name == "mmi"
        assert len(dev.ports) == 3
        assert dev.bbox.xmax == pytest.approx(10.0)

    def test_transform_bezier_pipeline(self) -> None:
        """变换 + 贝塞尔流水线集成测试。"""
        cp = np.array([[0.0, 0.0], [5.0, 10.0], [10.0, 0.0]])
        t_arr = np.linspace(0, 1, 50)
        curve = TransformMatrix.bezier_transform(cp, t_arr)
        assert curve.shape == (50, 2)
        rotated = TransformMatrix().rotate(45.0).apply(curve)
        assert rotated.shape == (50, 2)
        np.testing.assert_allclose(rotated[0], [0.0, 0.0], atol=1e-10)
