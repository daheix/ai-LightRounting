"""R457-R550 性能优化进阶测试套件（纯 NumPy/SciPy CPU，R04 兼容）。

测试覆盖（perf_optimization_advanced.py）：
- R457 Redheffer 星积 S 参数级联 + LRU 缓存（redheffer_star_product / RedhefferCascade）
- R460 数值精度自适应求解器（PrecisionAdaptiveSolver，迭代求精）
- R461 稀疏矩阵 CSR/CSC 压缩格式优化（SparseMatrixCompressor）
- R462 向量化 I/O 批量结果写入（VectorizedIO）
- R463 综合性能基准工厂（build_advanced_benchmark_suite）
- R03/R02/R04 合规 + 端到端集成

加载策略：用 importlib 直接加载 advanced 模块，注入 fake polaris.sim 包
绕过 polaris.sim.__init__ 的 sax/tidy3d 依赖（与 test_r453_r550 风格一致）。

文献依据：
- Redheffer 1959 Amer Math Monthly 66 145-146
  https://www.jstor.org/stable/2309522
- Higham 2002 Accuracy and Stability of Numerical Algorithms 2nd SIAM
  https://doi.org/10.1137/1.9780898718027
- Davis 2006 Direct Methods for Sparse Linear Systems SIAM
  https://doi.org/10.1137/1.9780898718003
"""

from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
import types
from pathlib import Path

import numpy as np
import pytest
import scipy.linalg as sla
import scipy.sparse as sp

# ---------------------------------------------------------------------------
# 模块加载（绕过 polaris.sim.__init__ 的 sax/tidy3d 依赖）
# ---------------------------------------------------------------------------

_SRC = Path(__file__).resolve().parent.parent / "src" / "polaris"


def _load_module(rel_path: str, module_name: str):
    """从 src/polaris/ 下相对路径直接加载模块。"""
    file_path = _SRC / rel_path
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)
    return mod


# 注入 fake polaris / polaris.sim 包（使 advanced 的延迟 import 命中缓存，
# 不触发真实 sim/__init__.py 的 sax 依赖）
_pkg = types.ModuleType("polaris")
_pkg.__path__ = [str(_SRC.parent)]
sys.modules.setdefault("polaris", _pkg)
_simpkg = types.ModuleType("polaris.sim")
_simpkg.__path__ = [str(_SRC / "sim")]
sys.modules.setdefault("polaris.sim", _simpkg)

# 预加载 benchmark（advanced.build_advanced_benchmark_suite 延迟 import 它）
_bench = _load_module(
    "sim/perf_optimization_benchmark.py",
    "polaris.sim.perf_optimization_benchmark",
)
_adv = _load_module(
    "sim/perf_optimization_advanced.py",
    "polaris.sim.perf_optimization_advanced",
)

redheffer_star_product = _adv.redheffer_star_product
RedhefferCascade = _adv.RedhefferCascade
RedhefferCascadeResult = _adv.RedhefferCascadeResult
PrecisionAdaptiveSolver = _adv.PrecisionAdaptiveSolver
PrecisionSolveResult = _adv.PrecisionSolveResult
SparseMatrixCompressor = _adv.SparseMatrixCompressor
SparseCompressResult = _adv.SparseCompressResult
VectorizedIO = _adv.VectorizedIO
build_advanced_benchmark_suite = _adv.build_advanced_benchmark_suite


# ===========================================================================
# R457 Redheffer 星积 S 参数级联 + 缓存
# ===========================================================================


def _transparent_s(m: int) -> np.ndarray:
    """透明元件 S 矩阵：无反射、全透射（S11=S22=0, S21=S12=I）。"""
    s = np.zeros((2 * m, 2 * m))
    s[:m, m:] = np.eye(m)  # S12 = I
    s[m:, :m] = np.eye(m)  # S21 = I
    return s


class TestR457RedhefferStarProduct:
    """R457 Redheffer 星积核心算法测试。"""

    def test_transparent_left_cascade_returns_right(self):
        """透明元件（左）级联 B 应返回 B（Redheffer 恒等性）。"""
        m = 3
        s_trans = _transparent_s(m)
        rng = np.random.default_rng(0)
        s_b = rng.standard_normal((2 * m, 2 * m))
        s_out = redheffer_star_product(s_trans, s_b)
        np.testing.assert_allclose(s_out, s_b, atol=1e-10)

    def test_transparent_right_cascade_returns_left(self):
        """A 级联透明元件（右）应返回 A（Redheffer 恒等性）。"""
        m = 4
        s_trans = _transparent_s(m)
        rng = np.random.default_rng(1)
        s_a = rng.standard_normal((2 * m, 2 * m))
        s_out = redheffer_star_product(s_a, s_trans)
        np.testing.assert_allclose(s_out, s_a, atol=1e-10)

    def test_associativity(self):
        """星积满足结合律 (A⋆B)⋆C = A⋆(B⋆C)（Redheffer 1959 性质）。"""
        m = 3
        rng = np.random.default_rng(42)
        # 构造物理合理 S 矩阵（小幅度避免 (I−B11·A22) 奇异）
        sa = 0.3 * rng.standard_normal((2 * m, 2 * m))
        sb = 0.3 * rng.standard_normal((2 * m, 2 * m))
        sc = 0.3 * rng.standard_normal((2 * m, 2 * m))
        left = redheffer_star_product(
            redheffer_star_product(sa, sb), sc,
        )
        right = redheffer_star_product(
            sa, redheffer_star_product(sb, sc),
        )
        np.testing.assert_allclose(left, right, atol=1e-10)

    def test_validates_non_square(self):
        """非方阵须 raise（R03）。"""
        with pytest.raises(ValueError, match="方阵"):
            redheffer_star_product(
                np.zeros((4, 5)), np.zeros((4, 4)),
            )

    def test_validates_shape_mismatch(self):
        """形状不匹配须 raise（R03）。"""
        with pytest.raises(ValueError, match="不匹配"):
            redheffer_star_product(
                np.zeros((4, 4)), np.zeros((6, 6)),
            )

    def test_validates_odd_dimension(self):
        """奇数维度须 raise（R03，S 须 2M）。"""
        with pytest.raises(ValueError, match="偶数"):
            redheffer_star_product(
                np.zeros((5, 5)), np.zeros((5, 5)),
            )

    def test_singular_interface_raises(self):
        """(I−B11·A22) 奇异须 raise LinAlgError（R03：禁止 fall-back）。"""
        m = 2
        # A22 = I, B11 = I → I − B11·A22 = 0 奇异
        sa = np.zeros((2 * m, 2 * m))
        sa[m:, m:] = np.eye(m)  # A22 = I
        sb = np.zeros((2 * m, 2 * m))
        sb[:m, :m] = np.eye(m)  # B11 = I
        with pytest.raises(np.linalg.LinAlgError):
            redheffer_star_product(sa, sb)


class TestR457RedhefferCascade:
    """R457 Redheffer 级联器 + LRU 缓存测试。"""

    def test_make_key_deterministic(self):
        """相同参数生成相同键。"""
        k1 = RedhefferCascade.make_key([1.0, 2.0], 4, 1.55e-6)
        k2 = RedhefferCascade.make_key([1.0, 2.0], 4, 1.55e-6)
        assert k1 == k2

    def test_make_key_distinct_for_different_lengths(self):
        """不同 cell_lengths 生成不同键。"""
        k1 = RedhefferCascade.make_key([1.0, 2.0], 4, 1.55e-6)
        k2 = RedhefferCascade.make_key([1.0, 2.5], 4, 1.55e-6)
        assert k1 != k2

    def test_cascade_single_returns_input(self):
        """单 cell 级联应返回该 cell 的 S 矩阵。"""
        m = 3
        rng = np.random.default_rng(7)
        s0 = 0.3 * rng.standard_normal((2 * m, 2 * m))
        casc = RedhefferCascade()
        res = casc.cascade([s0], [1.0], m, 1.55e-6)
        np.testing.assert_allclose(res.s_matrix, s0, atol=1e-12)
        assert res.n_cells == 1
        assert not res.cache_hit

    def test_cascade_cache_hit_on_repeat(self):
        """相同参数第二次级联应命中缓存。"""
        m = 3
        rng = np.random.default_rng(11)
        s1 = 0.3 * rng.standard_normal((2 * m, 2 * m))
        s2 = 0.3 * rng.standard_normal((2 * m, 2 * m))
        casc = RedhefferCascade(max_size=8)
        r1 = casc.cascade([s1, s2], [1.0, 2.0], m, 1.55e-6)
        assert not r1.cache_hit
        r2 = casc.cascade([s1, s2], [1.0, 2.0], m, 1.55e-6)
        assert r2.cache_hit
        # 缓存命中结果与首次一致
        np.testing.assert_allclose(r2.s_matrix, r1.s_matrix, atol=1e-12)
        assert casc.hits == 1
        assert casc.misses == 1

    def test_cache_miss_for_different_wavelength(self):
        """不同波长应 miss。"""
        m = 2
        rng = np.random.default_rng(13)
        s1 = 0.3 * rng.standard_normal((2 * m, 2 * m))
        casc = RedhefferCascade()
        casc.cascade([s1], [1.0], m, 1.55e-6)
        res2 = casc.cascade([s1], [1.0], m, 1.30e-6)
        assert not res2.cache_hit

    def test_lru_eviction(self):
        """超 max_size 应丢弃最旧。"""
        m = 2
        rng = np.random.default_rng(17)
        casc = RedhefferCascade(max_size=2)
        s = 0.3 * rng.standard_normal((2 * m, 2 * m))
        casc.cascade([s], [1.0], m, 1.55e-6)   # key A
        casc.cascade([s], [2.0], m, 1.55e-6)   # key B
        casc.cascade([s], [3.0], m, 1.55e-6)   # key C → 驱逐 A
        # 再次请求 A 应 miss（重新计算）
        res = casc.cascade([s], [1.0], m, 1.55e-6)
        assert not res.cache_hit

    def test_validates_empty_matrices(self):
        """空 S 矩阵列表须 raise（R03）。"""
        casc = RedhefferCascade()
        with pytest.raises(ValueError, match="不能为空"):
            casc.cascade([], [], 4, 1.55e-6)

    def test_validates_length_mismatch(self):
        """s_matrices 与 cell_lengths 长度不匹配须 raise（R03）。"""
        casc = RedhefferCascade()
        m = 2
        s = np.zeros((2 * m, 2 * m))
        with pytest.raises(ValueError, match="不匹配"):
            casc.cascade([s, s], [1.0], m, 1.55e-6)

    def test_validates_n_modes(self):
        """n_modes 非法须 raise（R03）。"""
        casc = RedhefferCascade()
        s = np.zeros((4, 4))
        with pytest.raises(ValueError, match="n_modes"):
            casc.cascade([s], [1.0], 0, 1.55e-6)

    def test_clear_resets(self):
        """clear 应清空缓存与统计。"""
        m = 2
        rng = np.random.default_rng(19)
        s = 0.3 * rng.standard_normal((2 * m, 2 * m))
        casc = RedhefferCascade()
        casc.cascade([s], [1.0], m, 1.55e-6)
        casc.clear()
        assert casc.hits == 0
        assert casc.misses == 0
        assert casc.hit_rate == 0.0


# ===========================================================================
# R460 数值精度自适应求解器
# ===========================================================================


class TestR460PrecisionAdaptiveSolver:
    """R460 精度自适应求解器测试。"""

    def test_validates_rtol(self):
        """rtol 非法须 raise（R03）。"""
        with pytest.raises(ValueError, match="rtol"):
            PrecisionAdaptiveSolver(rtol=0.0)
        with pytest.raises(ValueError, match="rtol"):
            PrecisionAdaptiveSolver(rtol=float("inf"))

    def test_validates_max_refinements(self):
        """max_refinements 非法须 raise（R03）。"""
        with pytest.raises(ValueError, match="max_refinements"):
            PrecisionAdaptiveSolver(rtol=1e-8, max_refinements=-1)

    def test_validates_shape(self):
        """A 非方阵须 raise（R03）。"""
        solver = PrecisionAdaptiveSolver(rtol=1e-8)
        with pytest.raises(ValueError, match="方阵"):
            solver.solve(np.zeros((3, 4)), np.zeros(3))

    def test_validates_b_shape(self):
        """b 维度不匹配须 raise（R03）。"""
        solver = PrecisionAdaptiveSolver(rtol=1e-8)
        with pytest.raises(ValueError, match="不匹配"):
            solver.solve(np.eye(4), np.zeros(3))

    def test_well_conditioned_meets_rtol(self):
        """良态矩阵应达 rtol（残差迭代求精或直接高精度）。"""
        rng = np.random.default_rng(23)
        n = 12
        a = rng.standard_normal((n, n)) + n * np.eye(n)  # 良态
        b = rng.standard_normal(n)
        solver = PrecisionAdaptiveSolver(rtol=1e-12)
        res = solver.solve(a, b)
        assert res.relative_residual < 1e-12
        # 与 scipy 直接求解一致
        x_ref = sla.solve(a, b)
        np.testing.assert_allclose(res.x, x_ref, atol=1e-8)

    def test_singular_matrix_raises(self):
        """奇异矩阵须 raise LinAlgError（R03：禁止 fall-back）。"""
        a = np.zeros((5, 5))
        a[0, 1] = 1.0  # 仍奇异
        b = np.ones(5)
        solver = PrecisionAdaptiveSolver(rtol=1e-6)
        with pytest.raises(np.linalg.LinAlgError):
            solver.solve(a, b)

    def test_low_rtol_uses_float32(self):
        """宽松 rtol 应选 float32 初始 dtype。"""
        solver = PrecisionAdaptiveSolver(rtol=1e-3)
        assert solver._select_initial_dtype() == np.dtype(np.float32)

    def test_strict_rtol_uses_float64(self):
        """中等 rtol 应选 float64。"""
        solver = PrecisionAdaptiveSolver(rtol=1e-10)
        assert solver._select_initial_dtype() == np.dtype(np.float64)

    def test_result_dtype_recorded(self):
        """结果应记录所用 dtype。"""
        rng = np.random.default_rng(29)
        n = 10
        a = rng.standard_normal((n, n)) + n * np.eye(n)
        b = rng.standard_normal(n)
        solver = PrecisionAdaptiveSolver(rtol=1e-10)
        res = solver.solve(a, b)
        assert res.dtype in (
            np.dtype(np.float32), np.dtype(np.float64), np.dtype(np.longdouble),
        )
        assert res.relative_residual < 1e-10


# ===========================================================================
# R461 稀疏矩阵 CSR/CSC 压缩格式优化
# ===========================================================================


class TestR461SparseMatrixCompressor:
    """R461 稀疏矩阵压缩测试。"""

    def test_validates_2d(self):
        """非 2D 须 raise（R03）。"""
        with pytest.raises(ValueError, match="2D"):
            SparseMatrixCompressor(np.zeros((3,)))

    def test_validates_empty(self):
        """空矩阵须 raise（R03）。"""
        with pytest.raises(ValueError, match="空"):
            SparseMatrixCompressor(np.zeros((0, 0)))

    def test_validates_op(self):
        """非法 op 须 raise（R03）。"""
        comp = SparseMatrixCompressor(np.eye(4))
        with pytest.raises(ValueError, match="op"):
            comp.compress(op="invalid")

    def test_row_op_selects_csr(self):
        """行操作应选 CSR。"""
        comp = SparseMatrixCompressor(np.eye(6))
        res = comp.compress(op="row")
        assert res.format == "csr"
        assert res.nnz == 6
        assert "CSR" in res.reason

    def test_col_op_selects_csc(self):
        """列操作应选 CSC。"""
        comp = SparseMatrixCompressor(np.eye(6))
        res = comp.compress(op="col")
        assert res.format == "csc"
        assert "CSC" in res.reason

    def test_spmv_matches_dense(self):
        """SpMV 应与密集矩阵-向量乘一致。"""
        rng = np.random.default_rng(31)
        dense = rng.standard_normal((8, 8))
        dense[np.abs(dense) < 0.7] = 0.0
        x = rng.standard_normal(8)
        comp = SparseMatrixCompressor(dense)
        y = comp.spmv(x, op="spmv")
        np.testing.assert_allclose(y, dense @ x, atol=1e-12)

    def test_spmv_validates_x_shape(self):
        """x 维度不匹配须 raise（R03）。"""
        comp = SparseMatrixCompressor(np.eye(6))
        with pytest.raises(ValueError, match="不匹配"):
            comp.spmv(np.zeros(5))

    def test_memory_bytes_positive(self):
        """内存字节应为正。"""
        comp = SparseMatrixCompressor(np.eye(10))
        res = comp.compress(op="spmv")
        assert res.memory_bytes > 0

    def test_accepts_sparse_input(self):
        """应接受稀疏矩阵输入。"""
        csc_in = sp.csc_matrix(np.eye(6))
        comp = SparseMatrixCompressor(csc_in)
        res = comp.compress(op="row")
        assert res.format == "csr"
        assert res.nnz == 6


# ===========================================================================
# R462 向量化 I/O 批量结果写入
# ===========================================================================


class TestR462VectorizedIO:
    """R462 向量化 I/O 测试。"""

    def test_validates_batch_size(self):
        """batch_size 非法须 raise（R03）。"""
        with pytest.raises(ValueError, match="batch_size"):
            VectorizedIO(batch_size=0)

    def test_validates_empty_key(self):
        """空 key 须 raise（R03）。"""
        vio = VectorizedIO(batch_size=4)
        with pytest.raises(ValueError, match="key"):
            vio.append("", np.zeros(3))

    def test_validates_duplicate_key(self):
        """重复 key 须 raise（R03）。"""
        vio = VectorizedIO(batch_size=4)
        vio.append("k1", np.zeros(3))
        with pytest.raises(ValueError, match="k1"):
            vio.append("k1", np.zeros(3))

    def test_auto_flush_at_batch_size(self):
        """满 batch_size 应自动 flush。"""
        vio = VectorizedIO(batch_size=3)
        vio.append("a", np.zeros(2))
        vio.append("b", np.zeros(2))
        assert vio.pending == 2
        vio.append("c", np.zeros(2))  # 触发自动 flush
        assert vio.pending == 0
        assert vio.flushed_count == 3

    def test_manual_flush(self):
        """手动 flush 应写入并清空缓冲。"""
        vio = VectorizedIO(batch_size=10)
        vio.append("a", np.ones(2))
        vio.append("b", np.ones(2))
        n = vio.flush()
        assert n == 2
        assert vio.pending == 0
        assert vio.flushed_count == 2

    def test_flush_empty_returns_zero(self):
        """空缓冲 flush 应返回 0。"""
        vio = VectorizedIO(batch_size=4)
        assert vio.flush() == 0

    def test_file_write_readback(self):
        """写入文件后应能读回所有数组。"""
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "out.npz")
            vio = VectorizedIO(batch_size=4, path=path)
            arr_a = np.arange(6).reshape(2, 3).astype(np.float64)
            arr_b = np.linspace(0, 1, 4)
            vio.append("a", arr_a)
            vio.append("b", arr_b)
            n = vio.flush()
            assert n == 2
            assert vio.total_bytes > 0
            with np.load(path, allow_pickle=False) as data:
                assert "a" in data.files
                assert "b" in data.files
                np.testing.assert_allclose(data["a"], arr_a)
                np.testing.assert_allclose(data["b"], arr_b)

    def test_file_append_preserves_history(self):
        """二次 flush 应保留首次写入的数据（累加模式）。"""
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "app.npz")
            vio = VectorizedIO(batch_size=2, path=path)
            vio.append("a", np.array([1.0, 2.0]))
            vio.flush()
            vio.append("b", np.array([3.0, 4.0]))
            vio.flush()
            with np.load(path, allow_pickle=False) as data:
                assert set(data.files) == {"a", "b"}
                np.testing.assert_allclose(data["a"], [1.0, 2.0])
                np.testing.assert_allclose(data["b"], [3.0, 4.0])

    def test_file_invalid_dir_raises(self):
        """目录不存在须 raise（R03：禁止 fall-back）。"""
        vio = VectorizedIO(
            batch_size=2, path="/nonexistent_dir_xyz/out.npz",
        )
        vio.append("a", np.zeros(2))  # batch_size=2 不触发自动 flush
        with pytest.raises(ValueError, match="目录"):
            vio.flush()


# ===========================================================================
# R463 综合性能基准工厂
# ===========================================================================


class TestR463AdvancedBenchmarkSuite:
    """R463 综合性能基准工厂测试。"""

    def test_validates_n(self):
        """n 过小须 raise（R03）。"""
        with pytest.raises(ValueError, match="n"):
            build_advanced_benchmark_suite(n=4)

    def test_validates_n_modes(self):
        """n_modes 非法须 raise（R03）。"""
        with pytest.raises(ValueError, match="n_modes"):
            build_advanced_benchmark_suite(n_modes=0)

    def test_suite_has_four_cases(self):
        """工厂应注入 4 个基准用例。"""
        suite = build_advanced_benchmark_suite(n=20, n_modes=3)
        # PerfBenchmarkSuite 内部 _cases
        assert len(suite._cases) == 4
        names = [c.name for c in suite._cases]
        assert "redheffer_cascade_cache" in names
        assert "precision_adaptive_solve" in names
        assert "sparse_csr_spmv" in names
        assert "vectorized_io_batch" in names

    def test_suite_runs_all_pass(self):
        """套件应能完整运行且全部通过阈值。"""
        suite = build_advanced_benchmark_suite(n=20, n_modes=3)
        results = suite.run()
        assert len(results) == 4
        for r in results:
            assert r.median_time > 0.0
            assert r.min_time <= r.median_time <= r.max_time
            assert r.passed, f"用例 {r.name} 未通过阈值（{r.median_time:.3e}s）"


# ===========================================================================
# R03/R02/R04 合规
# ===========================================================================


class TestCompliance:
    """R03/R02/R04 合规检查。"""

    @classmethod
    def setup_class(cls) -> None:
        cls.src = (
            _SRC / "sim" / "perf_optimization_advanced.py"
        ).read_text(encoding="utf-8")

    def test_r02_url_count(self):
        """R02：docstring 含 ≥5 个文献 URL。"""
        docstring = self.src.split("from __future__")[0]
        assert docstring.count("https://") >= 5

    def test_r02_innovation_marked(self):
        """R02：源码含 *创新* 标注。"""
        assert "*创新*" in self.src

    def test_r04_no_gpu_imports(self):
        """R04：无 GPU 后端导入。"""
        for forbidden in (
            "import cupy", "import torch", "from torch",
            "from cupy", "import cuda", "import jax",
        ):
            assert forbidden not in self.src, f"R04 违规: 含 '{forbidden}'"

    def test_no_todo_fixme_hack(self):
        """R05：无 TODO/FIXME/HACK 残留。"""
        for token in ("TODO", "FIXME", "HACK"):
            assert token not in self.src, f"R05 违规: 含 '{token}'"

    def test_r03_no_silent_fallback(self):
        """R03：except 块后无 pass/return None/return [] 静默兜底。"""
        lines = self.src.split("\n")
        for i, line in enumerate(lines):
            s = line.strip()
            if s.startswith("except") and s.endswith(":"):
                if i + 1 < len(lines):
                    nxt = lines[i + 1].strip()
                    assert nxt not in (
                        "pass", "return None", "return []", "return",
                    ), f"第 {i+1} 行 except 后 fall-back: {nxt}"


# ===========================================================================
# 端到端集成
# ===========================================================================


class TestEndToEndIntegration:
    """端到端集成：四模块协同。"""

    def test_full_pipeline_redheffer_precision_sparse_io(self):
        """完整流水线：Redheffer 级联 → 精度求解 → 稀疏 SpMV → 批量 I/O。"""
        # 1. Redheffer 级联
        m = 3
        rng = np.random.default_rng(2026)
        s1 = 0.3 * rng.standard_normal((2 * m, 2 * m))
        s2 = 0.3 * rng.standard_normal((2 * m, 2 * m))
        casc = RedhefferCascade(max_size=16)
        rc = casc.cascade([s1, s2], [1.0, 2.0], m, 1.55e-6)
        assert rc.s_matrix.shape == (2 * m, 2 * m)
        assert not rc.cache_hit

        # 2. 精度自适应求解（用级联结果构造良态系统）
        a = rc.s_matrix + 2 * m * np.eye(2 * m)
        b = rng.standard_normal(2 * m)
        solver = PrecisionAdaptiveSolver(rtol=1e-10)
        pres = solver.solve(a, b)
        assert pres.relative_residual < 1e-10

        # 3. 稀疏 SpMV
        dense = rng.standard_normal((10, 10))
        dense[np.abs(dense) < 0.8] = 0.0
        comp = SparseMatrixCompressor(dense)
        x = rng.standard_normal(10)
        y = comp.spmv(x)
        np.testing.assert_allclose(y, dense @ x, atol=1e-12)

        # 4. 批量 I/O 写入全部结果
        with tempfile.TemporaryDirectory() as d:
            vio = VectorizedIO(
                batch_size=4,
                path=os.path.join(d, "pipeline.npz"),
            )
            vio.append("redheffer_s", rc.s_matrix)
            vio.append("precision_x", pres.x)
            vio.append("sparse_y", y)
            n = vio.flush()
            assert n == 3
            assert vio.total_bytes > 0

    def test_no_fallback_full_path(self):
        """完整路径无 fall-back：非法输入均 raise。"""
        casc = RedhefferCascade()
        with pytest.raises(ValueError):
            casc.cascade([], [], 4, 1.55e-6)
        solver = PrecisionAdaptiveSolver(rtol=1e-8)
        with pytest.raises(ValueError):
            solver.solve(np.zeros((3, 4)), np.zeros(3))
        comp = SparseMatrixCompressor(np.eye(4))
        with pytest.raises(ValueError):
            comp.compress(op="bad")
        vio = VectorizedIO(batch_size=2)
        with pytest.raises(ValueError):
            vio.append("", np.zeros(2))
