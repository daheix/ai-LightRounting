"""R11 路标：版图参数化代码驱动（Code-as-Layout）单元测试。

覆盖 @polaris_cell 装饰器、PCell 多视图类、Transform2D 仿射变换、
bezier_transform 贝塞尔曲线、PCellCache LRU 缓存、ai_generate_pcell AI 生成、
无 fall-back AST 集成检查。所有测试使用真实数据。
"""

from __future__ import annotations

import ast
from pathlib import Path

import numpy as np
import pytest

from polaris.pdk.pcell_engine import (
    BezierTransform,
    NetlistView,
    PCell,
    PCellCache,
    Reference,
    Transform2D,
    ai_generate_pcell,
    bezier_transform,
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
        def wg(width: float = 0.5) -> PCell:
            return PCell(name="wg", params={"width": width})

        assert wg(width=0.5) is wg(width=0.5)

    def test_cache_miss_different_params(self) -> None:
        @polaris_cell
        def wg(width: float = 0.5) -> PCell:
            return PCell(name="wg", params={"width": width})

        c1, c2 = wg(width=0.5), wg(width=0.8)
        assert c1 is not c2
        assert c1.params["width"] == pytest.approx(0.5)
        assert c2.params["width"] == pytest.approx(0.8)

    def test_param_validation_type_error(self) -> None:
        @polaris_cell
        def wg(width: float = 0.5) -> PCell:
            return PCell(name="wg", params={"width": width})

        with pytest.raises(TypeError, match="width"):
            wg(width="not_a_float")

    def test_naming_uniqueness(self) -> None:
        @polaris_cell
        def cell(length: float = 10.0) -> PCell:
            return PCell(name="my_cell", params={"length": length})

        c1, c2 = cell(length=10.0), cell(length=20.0)
        assert c1.name == "my_cell"
        assert c2.name == "my_cell_1"

    def test_info_metadata_attached(self) -> None:
        @polaris_cell
        def wg(width: float = 0.5) -> PCell:
            return PCell(name="wg")

        cell = wg(width=0.5)
        assert cell.info["function"] == "wg"
        assert cell.info["params"]["width"] == pytest.approx(0.5)

    def test_non_pcell_return_raises(self) -> None:
        @polaris_cell
        def bad(width: float = 0.5) -> str:
            return "not a pcell"

        with pytest.raises(TypeError, match="PCell"):
            bad(width=0.5)


class TestPCell:
    """PCell 多视图类测试。"""

    def test_add_polygon(self) -> None:
        cell = PCell(name="test")
        pts = np.array([[0, 0], [10, 0], [10, 5], [0, 5]])
        cell.add_polygon(pts, layer="WG")
        assert cell.layout_view is not None
        assert len(cell.layout_view.polygons) == 1
        np.testing.assert_array_equal(cell.layout_view.polygons[0][0], pts)
        assert cell.layout_view.polygons[0][1] == "WG"

    def test_add_port(self) -> None:
        cell = PCell(name="test")
        cell.add_port("in", 0.0, 0.0, "west", width=0.5)
        assert len(cell.layout_view.ports) == 1
        port = cell.layout_view.ports[0]
        assert port.name == "in"
        assert port.width == pytest.approx(0.5)

    def test_add_ref(self) -> None:
        parent, child = PCell(name="parent"), PCell(name="child")
        ref = parent.add_ref(child, x=5.0, y=3.0, rotation=90.0)
        assert isinstance(ref, Reference)
        assert ref.cell is child
        assert ref.x == pytest.approx(5.0)
        assert ref.rotation == pytest.approx(90.0)
        assert len(parent.layout_view.refs) == 1

    def test_get_netlist_from_layout(self) -> None:
        parent, child = PCell(name="parent"), PCell(name="child")
        parent.add_ref(child, x=5.0, y=0.0)
        parent.add_port("in", 0.0, 0.0, "west")
        nl = parent.get_netlist()
        assert len(nl["instances"]) == 1
        assert nl["instances"][0]["name"] == "child"
        assert "in" in nl["ports"]

    def test_get_netlist_from_netlist_view(self) -> None:
        cell = PCell(name="test")
        cell.netlist_view = NetlistView(
            instances=[{"name": "sub"}],
            connections=[{"from": "a", "to": "b"}],
            ports={"in": "0,0"},
        )
        nl = cell.get_netlist()
        assert len(nl["instances"]) == 1
        assert nl["ports"]["in"] == "0,0"

    def test_to_device(self) -> None:
        cell = PCell(name="wg", params={"platform": "SOI"})
        cell.add_polygon(np.array([[0, -0.25], [10, -0.25], [10, 0.25], [0, 0.25]]), "WG")
        cell.add_port("in", 0.0, 0.0, "west")
        cell.add_port("out", 10.0, 0.0, "east")
        dev = cell.to_device()
        assert dev.name == "wg"
        assert dev.platform == "SOI"
        assert len(dev.ports) == 2
        assert dev.bbox.xmax == pytest.approx(10.0)

    def test_to_device_no_layout_raises(self) -> None:
        with pytest.raises(ValueError, match="layout"):
            PCell(name="empty").to_device()


class TestTransform2D:
    """2D 仿射变换矩阵测试。"""

    def test_rotation_90(self) -> None:
        t = Transform2D.rotation(90.0)
        np.testing.assert_allclose(t.apply(np.array([[1.0, 0.0]])), [[0.0, 1.0]], atol=1e-10)

    def test_scaling(self) -> None:
        t = Transform2D.scaling(2.0, 3.0)
        np.testing.assert_allclose(t.apply(np.array([[1.0, 1.0]])), [[2.0, 3.0]], atol=1e-10)

    def test_scaling_uniform(self) -> None:
        t = Transform2D.scaling(2.0)
        np.testing.assert_allclose(t.apply(np.array([[1.0, 1.0]])), [[2.0, 2.0]], atol=1e-10)

    def test_translation(self) -> None:
        t = Transform2D.translation(5.0, 3.0)
        np.testing.assert_allclose(t.apply(np.array([[0.0, 0.0]])), [[5.0, 3.0]], atol=1e-10)

    def test_shear(self) -> None:
        t = Transform2D.shear(kx=1.0)
        np.testing.assert_allclose(t.apply(np.array([[0.0, 1.0]])), [[1.0, 1.0]], atol=1e-10)

    def test_compose(self) -> None:
        rot, trans = Transform2D.rotation(90.0), Transform2D.translation(1.0, 0.0)
        combined = trans.compose(rot)
        pts = np.array([[1.0, 0.0]])
        expected = trans.apply(rot.apply(pts))
        np.testing.assert_allclose(combined.apply(pts), expected, atol=1e-10)

    def test_inverse(self) -> None:
        t = Transform2D(a=2.0, b=1.0, c=0.5, d=3.0, tx=5.0, ty=2.0)
        combined = t.compose(t.inverse())
        pts = np.array([[3.0, 7.0]])
        np.testing.assert_allclose(combined.apply(pts), pts, atol=1e-10)

    def test_inverse_singular_raises(self) -> None:
        t = Transform2D(a=1.0, b=2.0, c=2.0, d=4.0)
        with pytest.raises(ValueError, match="奇异"):
            t.inverse()

    def test_apply_invalid_shape_raises(self) -> None:
        with pytest.raises(ValueError, match="points"):
            Transform2D().apply(np.array([1.0, 2.0, 3.0]))


class TestBezierTransform:
    """贝塞尔曲线变换测试。"""

    def test_two_points_linear(self) -> None:
        cp = np.array([[0.0, 0.0], [10.0, 0.0]])
        np.testing.assert_allclose(bezier_transform(cp, np.array([0.5])), [[5.0, 0.0]], atol=1e-10)

    def test_three_points_quadratic(self) -> None:
        cp = np.array([[0.0, 0.0], [5.0, 10.0], [10.0, 0.0]])
        expected = 0.25 * cp[0] + 0.5 * cp[1] + 0.25 * cp[2]
        np.testing.assert_allclose(bezier_transform(cp, np.array([0.5])), [expected], atol=1e-10)

    def test_four_points_cubic(self) -> None:
        cp = np.array([[0.0, 0.0], [3.0, 9.0], [7.0, 9.0], [10.0, 0.0]])
        expected = 0.125 * cp[0] + 0.375 * cp[1] + 0.375 * cp[2] + 0.125 * cp[3]
        np.testing.assert_allclose(bezier_transform(cp, np.array([0.5])), [expected], atol=1e-10)

    def test_endpoints(self) -> None:
        cp = np.array([[1.0, 2.0], [5.0, 8.0], [10.0, 3.0]])
        result = bezier_transform(cp, np.array([0.0, 1.0]))
        np.testing.assert_allclose(result[0], cp[0], atol=1e-10)
        np.testing.assert_allclose(result[1], cp[-1], atol=1e-10)

    def test_bezier_transform_class(self) -> None:
        bt = BezierTransform(control_points=np.array([[0.0, 0.0], [10.0, 0.0]]))
        np.testing.assert_allclose(bt.evaluate(np.array([0.5])), [[5.0, 0.0]], atol=1e-10)

    def test_insufficient_control_points_raises(self) -> None:
        with pytest.raises(ValueError, match="2"):
            bezier_transform(np.array([[1.0, 2.0]]), np.array([0.5]))


class TestPCellCache:
    """PCell 缓存管理器测试。"""

    def test_lru_eviction(self) -> None:
        cache = PCellCache(maxsize=2)
        cache.put(("k1",), PCell(name="c1"))
        cache.put(("k2",), PCell(name="c2"))
        cache.put(("k3",), PCell(name="c3"))
        assert cache.size == 2
        assert cache.get(("k1",)) is None
        assert cache.get(("k2",)) is not None

    def test_hit_rate(self) -> None:
        cache = PCellCache(maxsize=10)
        cache.put(("k1",), PCell(name="c1"))
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
        cache.put(("k1",), PCell(name="c1"))
        cache.get(("k1",))
        cache.clear()
        assert cache.size == 0
        assert cache.hit_rate == pytest.approx(0.0)

    def test_lru_order_update(self) -> None:
        cache = PCellCache(maxsize=2)
        c1, c2, c3 = PCell(name="c1"), PCell(name="c2"), PCell(name="c3")
        cache.put(("k1",), c1)
        cache.put(("k2",), c2)
        cache.get(("k1",))
        cache.put(("k3",), c3)
        assert cache.get(("k1",)) is c1
        assert cache.get(("k2",)) is None


class TestAIGeneratePCell:
    """AI 辅助 PCell 生成测试。"""

    def test_ring_resonator(self) -> None:
        code = ai_generate_pcell("半径5μm的环谐振器")
        assert "@polaris_cell" in code
        assert "ring_resonator" in code
        assert "radius: float = 5.0" in code

    def test_mmi(self) -> None:
        code = ai_generate_pcell("MMI 1x2 长度10")
        assert "@polaris_cell" in code
        assert "mmi1x2" in code
        assert "length: float = 10.0" in code

    def test_waveguide(self) -> None:
        code = ai_generate_pcell("直波导 width 0.8")
        assert "@polaris_cell" in code
        assert "straight_waveguide" in code
        assert "width: float = 0.8" in code

    def test_y_branch(self) -> None:
        code = ai_generate_pcell("Y branch 分支")
        assert "@polaris_cell" in code
        assert "y_branch" in code

    def test_unrecognized_raises(self) -> None:
        with pytest.raises(ValueError, match="无法识别"):
            ai_generate_pcell("这是一个量子计算芯片")

    def test_generated_code_is_valid_python(self) -> None:
        ast.parse(ai_generate_pcell("半径3μm的环谐振器"))


class TestR11Integration:
    """R11 集成测试：无 fall-back AST 检查。"""

    def test_no_fallback_ast(self) -> None:
        """AST 检查 pcell_engine.py 无 fall-back 模式（裸 except/pass/return None）。"""
        source = Path("src/polaris/pdk/pcell_engine.py").read_text()
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

    def test_pcell_to_device_roundtrip(self) -> None:
        @polaris_cell
        def mmi(width: float = 0.5, length: float = 10.0) -> PCell:
            cell = PCell(name="mmi", params={"platform": "SOI"})
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
        cp = np.array([[0.0, 0.0], [5.0, 10.0], [10.0, 0.0]])
        curve = bezier_transform(cp, np.linspace(0, 1, 50))
        assert curve.shape == (50, 2)
        rotated = Transform2D.rotation(45.0).apply(curve)
        assert rotated.shape == (50, 2)
        np.testing.assert_allclose(rotated[0], [0.0, 0.0], atol=1e-10)
