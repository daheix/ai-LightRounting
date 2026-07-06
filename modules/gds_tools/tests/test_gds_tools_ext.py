"""扩展测试（从 test_gds_tools.py 拆分，遵守 R11 质量门禁文件≤800行）.

来源（R02 学术诚信）: 同原文件 test_gds_tools.py。
"""


from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# 让测试既能从已安装包导入，也能从源码树导入（CI/开发模式）
_SRC = str(Path(__file__).resolve().parents[1] / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import polaris_gds_tools as pgt
from polaris_gds_tools import (
    OPENACCESS_LAYER_MAP,
    SUPPORTED_FORMATS,
    Cell,
    FormatLayout,
    Instance,
    LayerInfo,
    MultiFormatIO,
    OpenAccessDB,
    Point,
    RenderOptions,
    Shape,
    atomic_write_text,
    get_default_layer_map,
    layouts_equal,
)


# ---------------------------------------------------------------------------
# pytest fixtures（从 test_gds_tools.py 复制，供 ext 测试使用）
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def klayout_db():
    """klayout.db 模块 fixture（未安装则跳过本模块所有 klayout 依赖测试）。

    用 importorskip("klayout.db") 直接导入子模块（klayout 顶层包不自动暴露 .db）。
    """
    return pytest.importorskip("klayout.db")


@pytest.fixture
def test_gds(tmp_path, klayout_db):
    """创建测试 GDSII 文件（顶层 cell + 1 子 cell + WG 层 box）。

    顶层 cell TOP 含子 cell CHILD 的实例，CHILD 在 WG 层 (1,0) 有 10×10μm box。
    """
    db = klayout_db
    ly = db.Layout()
    ly.dbu = 0.001
    top = ly.create_cell("TOP")
    child = ly.create_cell("CHILD")
    wg = ly.layer(1, 0)
    child.shapes(wg).insert(db.Box(0, 0, 10000, 10000))  # 10×10μm
    top.insert(db.CellInstArray(child.cell_index(), db.Trans(0, 0)))
    # 顶层也加一个 box
    top.shapes(wg).insert(db.Box(0, 0, 5000, 5000))  # 5×5μm
    out = tmp_path / "test.gds"
    ly.write(str(out))
    return out


@pytest.fixture
def two_layer_gds(tmp_path, klayout_db):
    """创建两层 GDSII（WG (1,0) + SLAB150 (2,0) 重叠 box），用于布尔/连通性测试。"""
    db = klayout_db
    ly = db.Layout()
    ly.dbu = 0.001
    top = ly.create_cell("TOP")
    wg = ly.layer(1, 0)
    slab = ly.layer(2, 0)
    top.shapes(wg).insert(db.Box(0, 0, 10000, 10000))
    top.shapes(slab).insert(db.Box(5000, 5000, 15000, 15000))
    out = tmp_path / "two_layer.gds"
    ly.write(str(out))
    return out


# ---------------------------------------------------------------------------
# 测试辅助：构造 FormatLayout 与 GDSII 文件
# ---------------------------------------------------------------------------


def test_check_grid_alignment(test_gds):
    """check_grid_alignment 返回 GridCheckReport。

    GridCheckReport 实际字段（源码 dataclass）: grid_um/grid_dbu/top_cell_name/
    violations/total_violations/layer_violation_counts/total_shapes_checked
    （无 misaligned_count/issues）。
    """
    from polaris_gds_tools import check_grid_alignment
    report = check_grid_alignment(str(test_gds), grid_um=0.001)
    assert hasattr(report, "total_violations")
    assert hasattr(report, "violations")
    assert hasattr(report, "total_shapes_checked")


def test_extract_edges(tmp_path, test_gds):
    """extract_edges 从 WG 层提取边缘。

    EdgeExtractionReport 实际字段（源码 dataclass）: input_path/output_path/layer/
    total_edges_before/total_edges_after/sample_edges（无 edges/edge_count）。
    """
    from polaris_gds_tools import extract_edges
    report = extract_edges(str(test_gds), (1, 0))
    assert hasattr(report, "total_edges_before")
    assert hasattr(report, "sample_edges")
    assert isinstance(report.sample_edges, list)


def test_extract_ports(test_gds):
    """extract_ports 提取端口（无 PORT 层应返回空报告）。"""
    from polaris_gds_tools import extract_ports
    report = extract_ports(str(test_gds))
    assert hasattr(report, "ports") or hasattr(report, "port_count")


def test_extract_text_labels(test_gds):
    """extract_text_labels 提取文本标签。"""
    from polaris_gds_tools import extract_text_labels
    report = extract_text_labels(str(test_gds))
    assert hasattr(report, "labels") or hasattr(report, "text_count")


def test_analyze_layer_connectivity(test_gds):
    """analyze_layer_connectivity 分析单层连通性。

    ConnectivityReport 实际字段（源码 dataclass）: top_cell_name/layer_results/
    total_components/total_isolated（无 nets/connected_components）。
    来源: gdsii_connectivity_analyzer.py L134-152
    """
    from polaris_gds_tools import analyze_layer_connectivity
    report = analyze_layer_connectivity(str(test_gds))
    assert hasattr(report, "layer_results")
    assert hasattr(report, "total_components")
    assert isinstance(report.layer_results, list)


def test_analyze_cross_layer_connectivity(two_layer_gds):
    """analyze_cross_layer_connectivity 分析跨层连通性。

    源码签名（必填 layer_pairs）:
      analyze_cross_layer_connectivity(gds_path, layer_pairs, ...) ->
      dict[str, list[set[str]]]
    layer_pairs 是层对连接规则（如 [('WG','SLAB150')] 表示两层通过重叠连通）。
    返回字典 {layer_name: [set_of_component_ids]}，非 report 对象。
    来源: gdsii_connectivity_analyzer.py L374-422
    并查集算法: Tarjan JACM 1975, DOI: 10.1145/321879.321884
    """
    from polaris_gds_tools import analyze_cross_layer_connectivity
    # two_layer_gds 含 WG(1,0) + SLAB150(2,0) 重叠 box，适合跨层连通测试
    report = analyze_cross_layer_connectivity(
        str(two_layer_gds), layer_pairs=[("WG", "SLAB150")]
    )
    assert isinstance(report, dict)
    # 每个值是 list[set[str]]
    for layer_name, components in report.items():
        assert isinstance(layer_name, str)
        assert isinstance(components, list)


def test_list_isolated_polygons(test_gds):
    """list_isolated_polygons 列出孤立多边形。

    源码签名: list_isolated_polygons(...) -> list[ConnectedComponent]
    返回孤立多边形分量列表（非 report 对象）。
    来源: gdsii_connectivity_analyzer.py L551
    """
    from polaris_gds_tools import list_isolated_polygons
    report = list_isolated_polygons(str(test_gds))
    assert isinstance(report, list)
    # 每个元素是 ConnectedComponent（含 component_id/layer_name/area_um2 等字段）
    for comp in report:
        assert hasattr(comp, "component_id")
        assert hasattr(comp, "layer_name")


def test_tapeout_precheck(test_gds):
    """tapeout_precheck 流片前综合预检查。"""
    from polaris_gds_tools import tapeout_precheck
    report = tapeout_precheck(str(test_gds))
    assert hasattr(report, "passed") or hasattr(report, "issues")
    assert hasattr(report, "checks_run")


def test_run_batch_pipeline(test_gds):
    """run_batch_pipeline 批量执行验证流水线。"""
    from polaris_gds_tools import run_batch_pipeline
    report = run_batch_pipeline([str(test_gds)])
    assert hasattr(report, "results") or hasattr(report, "file_results")


def test_check_area(test_gds):
    """check_area 对 WG 层执行最小面积检查。"""
    from polaris_gds_tools import check_area
    report = check_area(str(test_gds), (1, 0), min_area_um2=1.0)
    assert hasattr(report, "violations") or hasattr(report, "violation_count")


def test_check_area_finds_violations(test_gds):
    """check_area 高阈值时报告违规（box 面积 < 阈值）。"""
    from polaris_gds_tools import check_area
    # WG 层 box 最大 100μm²，设阈值 10000 应有违规
    report = check_area(str(test_gds), (1, 0), min_area_um2=10000.0)
    n_viol = (len(report.violations) if hasattr(report, "violations")
              else getattr(report, "violation_count", 0))
    assert n_viol > 0, "高面积阈值应报告违规"


# ===========================================================================
# 曲线离散化与样条曲线测试（v5.0 R11 路标：GDS/OASIS 1nm 精度导出）
# 来源（R02 学术诚信）:
# - de Boor 1978 A Practical Guide to Splines
#   https://link.springer.com/book/10.1007/978-1-4612-6332-9
# - Catmull & Rom 1974 Computer Aided Geometric Design
#   https://www.sciencedirect.com/science/article/pii/B9780120790500500205
# - SEMI P39 OASIS https://en.wikipedia.org/wiki/Open_Artwork_System_Interchange_Standard
# - GDSII 1nm dbu https://www.klayout.org/doc/manual/database.html
# - Piegl & Tiller 1997 The NURBS Book §3.5
#   https://link.springer.com/book/10.1007/978-3-642-59223-2
# ===========================================================================


def test_discretize_curve_1nm_arc_length():
    """discretize_curve_1nm 验证 1nm 弧长步长离散化。

    曲线 (t, t²)，t ∈ [0, 1]，理论弧长 ≈ 1.4789μm，1nm 步长 → ~1480 点。
    相邻点弦长应接近 1nm（0.001μm），数量级与理论一致。
    """
    import numpy as np
    from polaris_gds_tools.curve_discretization import discretize_curve_1nm

    pts = discretize_curve_1nm(lambda t: (t, t ** 2), 0.0, 1.0, tol_um=0.001)
    assert pts.ndim == 2 and pts.shape[1] == 2, f"shape={pts.shape}"
    # 弧长 ≈ 1.4789μm，1nm 步长 → ~1480 点，允许 1000~2000 范围
    n = pts.shape[0]
    assert 1000 <= n <= 2000, f"1nm 离散化点数 {n} 不在预期范围"

    # 相邻点弦长应接近 1nm（首点除外，平均弦长 0.001~0.002μm）
    diffs = np.diff(pts, axis=0)
    seg = np.sqrt(np.einsum("ij,ij->i", diffs, diffs))
    mean_seg = float(np.mean(seg))
    assert 0.0005 <= mean_seg <= 0.002, f"平均弧长步长 {mean_seg} 偏离 1nm"

    # 端点正确（首点 = t=0，末点 = t=1）
    assert abs(pts[0, 0] - 0.0) < 1e-9 and abs(pts[0, 1] - 0.0) < 1e-9
    assert abs(pts[-1, 0] - 1.0) < 1e-6 and abs(pts[-1, 1] - 1.0) < 1e-6


def test_bspline_curve_basic():
    """bspline_curve 验证 B-spline（de Boor 算法）基本功能。

    clamped B-spline 曲线首末端点必须经过首末控制点。
    """
    import numpy as np
    from polaris_gds_tools.curve_discretization import bspline_curve

    ctrl = np.array([[0.0, 0.0], [1.0, 2.0], [3.0, 1.0], [4.0, 0.0]])
    pts = bspline_curve(ctrl, degree=3, n_points=50)
    assert pts.shape == (50, 2), f"shape={pts.shape}"

    # clamped B-spline 首末端点经过首末控制点
    assert np.allclose(pts[0], ctrl[0], atol=1e-9), \
        f"首点 {pts[0]} != 首控制点 {ctrl[0]}"
    assert np.allclose(pts[-1], ctrl[-1], atol=1e-9), \
        f"末点 {pts[-1]} != 末控制点 {ctrl[-1]}"

    # 曲线应在控制点凸包内（x 坐标范围检查）
    assert pts[:, 0].min() >= ctrl[:, 0].min() - 1e-9
    assert pts[:, 0].max() <= ctrl[:, 0].max() + 1e-9


def test_catmull_rom_basic():
    """catmull_rom_spline 验证 Catmull-Rom 样条基本功能。

    Catmull-Rom 是插值样条，必须过所有控制点。
    """
    import numpy as np
    from polaris_gds_tools.curve_discretization import catmull_rom_spline

    ctrl = np.array([[0.0, 0.0], [1.0, 1.0], [2.0, 0.0], [3.0, 1.0]])
    pts = catmull_rom_spline(ctrl, n_points=80)
    assert pts.shape == (80, 2), f"shape={pts.shape}"

    # Catmull-Rom 过所有控制点：在控制点附近应能找到对应点
    for cp in ctrl:
        dists = np.sqrt(np.sum((pts - cp) ** 2, axis=1))
        assert dists.min() < 1e-6, f"控制点 {cp} 不在曲线上（min_dist={dists.min()})"

    # 端点必须等于首末控制点（端点镜像保证）
    assert np.allclose(pts[0], ctrl[0], atol=1e-9), \
        f"首点 {pts[0]} != 首控制点 {ctrl[0]}"
    assert np.allclose(pts[-1], ctrl[-1], atol=1e-9), \
        f"末点 {pts[-1]} != 末控制点 {ctrl[-1]}"


def test_discretize_invalid_input_raises():
    """验证无效输入 raise（R03 禁止 fall-back，不返回空数组）。"""
    import numpy as np
    from polaris_gds_tools.curve_discretization import (
        bspline_curve,
        catmull_rom_spline,
        discretize_curve_1nm,
        discretize_to_gds_path,
    )

    # discretize_curve_1nm: end <= start
    with pytest.raises(RuntimeError):
        discretize_curve_1nm(lambda t: (t, t), 1.0, 0.0)
    # discretize_curve_1nm: tol_um <= 0
    with pytest.raises(RuntimeError):
        discretize_curve_1nm(lambda t: (t, t), 0.0, 1.0, tol_um=0.0)
    # discretize_curve_1nm: curve_func 不可调用
    with pytest.raises(RuntimeError):
        discretize_curve_1nm("not_callable", 0.0, 1.0)

    # bspline_curve: 控制点数 < 2
    with pytest.raises(RuntimeError):
        bspline_curve(np.array([[0.0, 0.0]]), degree=1)
    # bspline_curve: degree >= n_ctrl
    with pytest.raises(RuntimeError):
        bspline_curve(np.array([[0.0, 0.0], [1.0, 1.0]]), degree=2)
    # bspline_curve: 非 (N,2) 形状
    with pytest.raises(RuntimeError):
        bspline_curve(np.array([0.0, 1.0, 2.0]), degree=1)

    # catmull_rom_spline: 控制点数 < 2
    with pytest.raises(RuntimeError):
        catmull_rom_spline(np.array([[0.0, 0.0]]))
    # catmull_rom_spline: n_points < 2
    with pytest.raises(RuntimeError):
        catmull_rom_spline(np.array([[0.0, 0.0], [1.0, 1.0]]), n_points=1)

    # discretize_to_gds_path: dbu_um <= 0
    with pytest.raises(RuntimeError):
        discretize_to_gds_path(lambda t: (t, t), 0.0, 1.0, dbu_um=0.0)
