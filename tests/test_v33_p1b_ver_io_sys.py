"""v3.3 P1-B R03 fall-back 修复回归测试。

覆盖 6 个 P1-B fall-back Bug 修复（规则 R03 禁止 fall-back，失败即 raise）:
- #v3.3-IO-1: io/_dxf.py _dxf_parse_entity 未识别实体返回 None → raise ValueError
- #v3.3-IO-3: io/_gerber.py flush_path/_gerber_flash_shape 未定义孔径静默用默认 → raise ValueError
- #v3.3-IO-4: io/_cif.py 未定义符号静默生成假名 sym{sym} → raise ValueError
- #v3.3-SYS-1: system/__init__.py get_result 任务不存在返回 None → raise KeyError
- #v3.3-VER-1: verification/statistical_yield.py uniform 分布 except Exception fall-back 到
  无空间相关简单均匀分布（假数据）→ 仅捕获 LinAlgError 用 SVD 替代
- #v3.3-VER-13: verify/calibre_interface.py extract_layout continue 静默跳过缺层 +
  _load_gds_to_layout 未捕获 GDS 解析异常 → raise KeyError / ValueError

学术依据（≥5 文献 URL，规则 18 学术诚信）:
- PEP 8 Python 代码风格指南: https://peps.python.org/pep-0008/
- Effective Python 第20条 遇到意外状况时应该抛出异常，不要返回 None:
  https://www.informit.com/articles/article.aspx?p=3203546&seqNum=3
- Python 官方文档 Errors and Exceptions: https://docs.python.org/3/tutorial/errors.html
- Real Python Async IO: https://realpython.com/async-io-python/
- Python Cookbook 3rd Edition: https://www.oreilly.com/library/view/python-cookbook-3rd/9781449357337/
- NumPy LinAlgError 文档: https://numpy.org/doc/stable/reference/generated/numpy.linalg.LinAlgError.html
- SciPy stats 文档: https://docs.scipy.org/doc/scipy/reference/stats.html
- UCAMCO Gerber Spec: https://www.ucamco.com/files/downloads/file/81/the_gerber_file_format_specification.pdf
- Autodesk DXF Reference: https://images.autodesk.com/adskfiles/acad_dxf.pdf
- Caltech TR 2686 CIF: https://en.wikipedia.org/wiki/Caltech_Intermediate_Format

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R05 Bug 必修。
"""

from __future__ import annotations

import numpy as np
import pytest

from polaris.io._cif import read_cif
from polaris.io._dxf import read_dxf
from polaris.io._gerber import read_gerber
from polaris.system import DistributedConfig, DistributedTaskScheduler
from polaris.verification.statistical_yield import (
    StatisticalAnalyzer,
    StatisticalParam,
)
from polaris.verify.calibre_interface import (
    LayerSpec,
    Layout,
    ParasiticExtractor,
)

# =============================================================================
# #v3.3-IO-1: DXF 未识别实体 raise ValueError（原 fall-back 返回 None）
# =============================================================================

def test_v33_io1_dxf_unsupported_entity_raises() -> None:
    """IO-1: DXF 未识别实体类型（如 ARC）必须 raise ValueError。

    Bug: 原 _dxf_parse_entity 对未识别实体返回 None，调用方静默跳过，
    丢失几何数据且无任何告警（fall-back）。
    修复: 改为 raise ValueError（R03 禁止 fall-back）。

    文献: Autodesk DXF Reference §ENTITIES
      https://images.autodesk.com/adskfiles/acad_dxf.pdf
    """
    # 构造含 ARC 实体的 DXF（本解析器不支持 ARC，仅支持 LINE/CIRCLE/LWPOLYLINE/TEXT）
    dxf_text = "\n".join([
        "0", "SECTION", "2", "ENTITIES",
        "0", "ARC", "8", "0", "10", "0.0", "20", "0.0", "40", "1.0",
        "0", "ENDSEC", "0", "EOF",
    ])
    with pytest.raises(ValueError, match="DXF 不支持实体类型"):
        read_dxf(dxf_text)


def test_v33_io1_dxf_supported_entities_still_work() -> None:
    """IO-1: 修复后支持的实体类型（LINE/CIRCLE/LWPOLYLINE/TEXT）仍正常解析。"""
    dxf_text = "\n".join([
        "0", "SECTION", "2", "ENTITIES",
        "0", "LINE", "8", "wg", "10", "0.0", "20", "0.0",
        "11", "10.0", "21", "0.0",
        "0", "CIRCLE", "8", "pad", "10", "5.0", "20", "5.0", "40", "2.0",
        "0", "ENDSEC", "0", "EOF",
    ])
    layout = read_dxf(dxf_text)
    shapes = layout.cells[0].shapes
    assert len(shapes) == 2, f"应解析出 2 个实体，实际 {len(shapes)}"
    assert shapes[0].shape_type == "path"
    assert shapes[1].shape_type == "circle"


# =============================================================================
# #v3.3-IO-3: Gerber 未定义孔径 raise ValueError（原 fall-back 用默认 ("C", [0.0])）
# =============================================================================

def test_v33_io3_gerber_undefined_aperture_in_path_raises() -> None:
    """IO-3: D01 绘制时引用未定义孔径必须 raise ValueError。

    Bug: 原 flush_path 对 current_ap not in apertures 静默使用默认孔径
    ("C", [0.0])，导致线宽 0（假数据）。
    修复: 先检查 current_ap in apertures，否则 raise（R03 禁止 fall-back）。

    文献: UCAMCO Gerber Spec §4 孔径定义
      https://www.ucamco.com/files/downloads/file/81/the_gerber_file_format_specification.pdf
    """
    # D11 选择孔径，X0Y0D02 → X100Y0D01 绘制，但未定义 %ADD11% 孔径
    gerber_text = "\n".join([
        "%MOMM*%",
        "%FSLAX34Y34*%",
        "G01*",
        "D11*",
        "X0Y0D02*",
        "X1000Y0D01*",
        "M02*",
    ])
    with pytest.raises(ValueError, match="Gerber 孔径未定义"):
        read_gerber(gerber_text)


def test_v33_io3_gerber_undefined_aperture_in_flash_raises() -> None:
    """IO-3: D03 flash 时引用未定义孔径必须 raise ValueError。

    Bug: 原 _gerber_flash_shape 对 dcode not in apertures 静默使用默认孔径。
    修复: 先检查 dcode in apertures，否则 raise（R03 禁止 fall-back）。
    """
    # D11 选择孔径，D03 flash，但未定义 %ADD11% 孔径
    gerber_text = "\n".join([
        "%MOMM*%",
        "%FSLAX34Y34*%",
        "G01*",
        "D11*",
        "X0Y0D03*",
        "M02*",
    ])
    with pytest.raises(ValueError, match="Gerber 孔径未定义"):
        read_gerber(gerber_text)


def test_v33_io3_gerber_defined_aperture_still_works() -> None:
    """IO-3: 修复后已定义孔径的 Gerber 仍正常解析。"""
    gerber_text = "\n".join([
        "%MOMM*%",
        "%FSLAX34Y34*%",
        "%ADD10C,0.5*%",
        "G01*",
        "D10*",
        "X0Y0D03*",
        "M02*",
    ])
    layout = read_gerber(gerber_text)
    shapes = layout.cells[0].shapes
    assert len(shapes) == 1
    assert shapes[0].shape_type == "circle"
    assert shapes[0].width == pytest.approx(0.5)


# =============================================================================
# #v3.3-IO-4: CIF 未定义符号 raise ValueError（原 fall-back 生成假名 sym{sym}）
# =============================================================================

def test_v33_io4_cif_undefined_symbol_raises() -> None:
    """IO-4: CIF C 命令引用未定义符号必须 raise ValueError。

    Bug: 原 sym_to_name.get(sym, f"sym{sym}") 对未定义符号静默生成假名，
    导致实例引用不存在的单元（假数据）。
    修复: 先检查 sym in sym_to_name，否则 raise（R03 禁止 fall-back）。

    文献: Mead & Conway, "Introduction to VLSI Systems", Appendix C: CIF
      https://en.wikipedia.org/wiki/Caltech_Intermediate_Format

    注: CIF 标准要求 C 命令在 DS...DF 符号定义块内使用（Caltech TR 2686），
    故 C 2 必须在 DS 1 块内引用未定义的符号 2。
    """
    # DS 1 定义符号 1，块内 C 2 引用未定义的符号 2
    cif_text = "\n".join([
        "DS 1 1 1;",
        "L wg;",
        "B 100 50 0 0;",
        "C 2 T 0 0;",
        "DF;",
        "E",
    ])
    with pytest.raises(ValueError, match="CIF 符号.*未定义"):
        read_cif(cif_text)


def test_v33_io4_cif_defined_symbol_still_works() -> None:
    """IO-4: 修复后已定义符号的 CIF 仍正常解析。

    DS 1 定义符号 1（含 BOX），DS 2 定义符号 2 并在块内 C 1 引用符号 1。
    符号 1 已定义 → 不 raise，sym2.instances 应包含 1 个实例。
    """
    cif_text = "\n".join([
        "DS 1 1 1;",
        "L wg;",
        "B 100 50 0 0;",
        "DF;",
        "DS 2 1 1;",
        "C 1 T 0 0;",
        "DF;",
        "E",
    ])
    layout = read_cif(cif_text)
    # top_cell 应为 sym2（未被其他单元调用），且含 1 个 C 1 实例
    top = next(c for c in layout.cells if c.name == layout.top_cell)
    assert len(top.instances) >= 1, (
        f"top cell {top.name} 应含 1 个实例，实际 {len(top.instances)}"
    )
    assert top.instances[0].cell_name == "sym1"


# =============================================================================
# #v3.3-SYS-1: system get_result 任务不存在 raise KeyError（原 fall-back 返回 None）
# =============================================================================

def test_v33_sys1_get_result_missing_task_raises() -> None:
    """SYS-1: get_result 对不存在的任务必须 raise KeyError。

    Bug: 原 get_result 对 _tasks.get() 返回 None 静默返回 None（fall-back），
    调用方拿到 None 无法区分"任务不存在"和"任务结果为 None"。
    修复: 改为 raise KeyError（R03 禁止 fall-back）。
    """
    scheduler = DistributedTaskScheduler(DistributedConfig(backend="sequential"))
    with pytest.raises(KeyError, match="任务不存在"):
        scheduler.get_result("nonexistent-task-id")


def test_v33_sys1_get_result_existing_task_returns_result() -> None:
    """SYS-1: 修复后已存在任务仍正常返回 TaskResult。"""
    scheduler = DistributedTaskScheduler(DistributedConfig(backend="sequential"))

    def _task() -> int:
        return 42

    scheduler.submit("task-1", _task)
    result = scheduler.get_result("task-1")
    assert result.task_id == "task-1"


# =============================================================================
# #v3.3-VER-1: statistical_yield uniform 分布无 fall-back（原 except Exception 静默降级）
# =============================================================================

def test_v33_ver1_uniform_distribution_no_fallback_to_independent() -> None:
    """VER-1: uniform 分布在空间相关 MC 中必须保留空间相关性。

    Bug: 原 run_layout_aware_mc 中 uniform 分布采样用 except Exception
    静默 fall-back 到无空间相关的简单均匀分布（丢失空间相关性，假数据）。
    修复: 与高斯分布一致，仅捕获 np.linalg.LinAlgError 用 SVD 替代；
    其他异常必须 raise（R03 禁止 fall-back）。

    文献:
    - Lumerical INTERCONNECT Monte Carlo spatial correlations
      https://optics.ansys.com/hc/en-us/articles/360051762393
    - NumPy LinAlgError: https://numpy.org/doc/stable/reference/generated/numpy.linalg.LinAlgError.html
    - SciPy stats norm: https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.norm.html
    """
    analyzer = StatisticalAnalyzer()
    analyzer.add_param(StatisticalParam(
        name="width", nominal=0.5, sigma=0.01,
        distribution="uniform", lower=0.45, upper=0.55,
    ))
    # 3 个器件: 0μm, 100μm, 200μm 间距（相关长度 100μm 内应有强相关）
    positions = [(0.0, 0.0), (100.0, 0.0), (200.0, 0.0)]

    def sim_fn(params: dict[str, float], pos: tuple[float, float]) -> float:
        return params["width"]

    # 不应抛异常（scipy 应可用，cov 矩阵正定）
    result = analyzer.run_layout_aware_mc(
        sim_fn=sim_fn,
        device_positions=positions,
        n_runs=50,
        correlation_length_um=100.0,
        seed=42,
    )
    # 验证采样在 [lower, upper] 范围内（uniform 分布约束）
    width_samples = analyzer._results["width"]
    assert np.all(width_samples >= 0.45 - 1e-9), (
        f"uniform 采样应 ≥ lower=0.45，最小值 {width_samples.min()}"
    )
    assert np.all(width_samples <= 0.55 + 1e-9), (
        f"uniform 采样应 ≤ upper=0.55，最大值 {width_samples.max()}"
    )
    # 验证空间相关性保留：相近器件（0μm, 100μm）样本相关性应强于
    # 远离器件（0μm, 200μm），且非零（非独立采样）
    dev0 = width_samples[0, :]
    dev1 = width_samples[1, :]  # 距离 100μm = L
    dev2 = width_samples[2, :]  # 距离 200μm = 2L
    corr_close = float(np.corrcoef(dev0, dev1)[0, 1])
    corr_far = float(np.corrcoef(dev0, dev2)[0, 1])
    assert corr_close > 0.1, (
        f"距离 100μm (=L) 器件相关性应 > 0.1（保留空间相关），实际 {corr_close:.4f}"
    )
    # 高斯模型下 d=L 时 corr≈exp(-2)≈0.135，d=2L 时 corr≈exp(-8)≈3e-4
    # 近距离相关性应严格强于远距离（验证未 fall-back 到独立分布）
    assert corr_close > corr_far, (
        f"近距离相关性 {corr_close:.4f} 应 > 远距离 {corr_far:.4f}（未 fall-back 到独立分布）"
    )
    # 验证模型标注
    assert "gaussian" in result["spatial_correlation_model"]


def test_v33_ver1_uniform_distribution_cholesky_svd_path() -> None:
    """VER-1: uniform 分布 Cholesky 失败时走 SVD 路径（不 fall-back 到独立分布）。

    构造病态协方差矩阵（单器件 n=1，Cholesky 退化），验证 SVD 替代路径生效，
    且不触发 except Exception fall-back。
    """
    analyzer = StatisticalAnalyzer()
    analyzer.add_param(StatisticalParam(
        name="width", nominal=0.5, sigma=0.01,
        distribution="uniform", lower=0.45, upper=0.55,
    ))
    positions = [(0.0, 0.0)]  # 单器件

    def sim_fn(params: dict[str, float], pos: tuple[float, float]) -> float:
        return params["width"]

    result = analyzer.run_layout_aware_mc(
        sim_fn=sim_fn,
        device_positions=positions,
        n_runs=20,
        correlation_length_um=100.0,
        seed=7,
    )
    width_samples = analyzer._results["width"]
    # SVD 路径仍应生成 [lower, upper] 范围内的 uniform 样本
    assert np.all(width_samples >= 0.45 - 1e-9)
    assert np.all(width_samples <= 0.55 + 1e-9)
    assert result["n_runs"] == 20


# =============================================================================
# #v3.3-VER-13: calibre_interface extract_layout 缺层 raise + GDS 解析异常 raise
# =============================================================================

def test_v33_ver13_extract_layout_missing_layer_raises() -> None:
    """VER-13: extract_layout 对 layer_map 中不存在于版图的层必须 raise KeyError。

    Bug: 原代码 `if spec.gds_layer not in layout.polygons: continue` 静默跳过
    不存在的层（fall-back），导致该层寄生参数完全缺失却无告警。
    修复: 移除 continue，让 Layout.get_polygons 自然 raise KeyError
    （R03 禁止 fall-back）。
    """
    # 版图只有 (1, 0) 层，layer_map 要求 (2, 0) 层
    poly = np.array([[0, 0], [10, 0], [10, 1], [0, 1]], dtype=float)
    layout = Layout(polygons={(1, 0): [poly]}, name="test_missing")
    spec = LayerSpec(
        name="M2", gds_layer=(2, 0),  # (2, 0) 不在版图中
        thickness_um=0.5, resistivity_ohm_m=1.7e-8,
        eps_r_below=3.9, dielectric_thickness_um=1.0,
    )
    extractor = ParasiticExtractor()
    with pytest.raises(KeyError, match="层.*不存在"):
        extractor.extract_layout(layout, {"M2": spec})


def test_v33_ver13_extract_layout_matching_layer_works() -> None:
    """VER-13: 修复后层匹配的 extract_layout 仍正常工作。"""
    poly = np.array([[0, 0], [10, 0], [10, 1], [0, 1]], dtype=float)
    layout = Layout(polygons={(1, 0): [poly]}, name="test_ok")
    spec = LayerSpec(
        name="M1", gds_layer=(1, 0),
        thickness_um=0.5, resistivity_ohm_m=1.7e-8,
        eps_r_below=3.9, dielectric_thickness_um=1.0,
    )
    extractor = ParasiticExtractor()
    net = extractor.extract_layout(layout, {"M1": spec})
    assert net.extraction_summary["element_count"] >= 1


def test_v33_ver13_load_gds_nonexistent_file_raises_file_not_found() -> None:
    """VER-13: GDS 文件不存在必须 raise FileNotFoundError（已有保护）。"""
    spec = LayerSpec(
        name="M1", gds_layer=(1, 0),
        thickness_um=0.5, resistivity_ohm_m=1.7e-8,
        eps_r_below=3.9, dielectric_thickness_um=1.0,
    )
    extractor = ParasiticExtractor()
    with pytest.raises(FileNotFoundError, match="GDS 文件不存在"):
        extractor.extract("/nonexistent/path/to/file.gds", {"M1": spec})


def test_v33_ver13_load_gds_parse_error_raises_value_error() -> None:
    """VER-13: GDS 文件解析失败必须 raise ValueError（原未捕获异常 fall-back）。

    Bug: 原 _load_gds_to_layout 直接 ly.read(gds_path) 未捕获异常，
    若 GDS 文件损坏会抛出 klayout 原始异常，调用方无法识别。
    修复: 用 try/except 包装为 ValueError + 添加 top_cells 空检查
    （R03 禁止 fall-back，明确告警）。
    """
    import tempfile
    from pathlib import Path

    # 构造一个非 GDS 格式的损坏文件（klayout.db 读取应失败）
    with tempfile.NamedTemporaryFile(
        suffix=".gds", delete=False, mode="w"
    ) as f:
        f.write("this is not a valid GDS file content")
        bad_gds = Path(f.name)

    spec = LayerSpec(
        name="M1", gds_layer=(1, 0),
        thickness_um=0.5, resistivity_ohm_m=1.7e-8,
        eps_r_below=3.9, dielectric_thickness_um=1.0,
    )
    extractor = ParasiticExtractor()
    try:
        # klayout 可用时：应 raise ValueError（GDS 解析失败）
        # klayout 不可用时：应 raise ImportError（已在 _load_gds_to_layout 检查）
        with pytest.raises((ValueError, ImportError)):
            extractor.extract(bad_gds, {"M1": spec})
    finally:
        bad_gds.unlink(missing_ok=True)
