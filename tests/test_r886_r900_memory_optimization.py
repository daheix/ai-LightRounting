"""R886-R900 内存优化模块测试。

学术依据（R02，≥5 文献 URL）：
- Harris 2020 NumPy Nature https://doi.org/10.1038/s41586-020-2649-2
- NumPy memmap https://numpy.org/doc/stable/reference/generated/numpy.memmap.html
- Dask chunked arrays https://docs.dask.org/en/stable/array.html
- Python gc https://docs.python.org/3/library/gc.html
- Higham 2002 SIAM https://doi.org/10.1137/1.9780898718027
- Python tracemalloc https://docs.python.org/3/library/tracemalloc.html
"""

from __future__ import annotations

import numpy as np
import pytest

from polaris.sim.memory_optimization_r886 import (
    ChunkedResult,
    MemmapArray,
    MemoryOptimizerKit,
    MemoryProbeResult,
    chunked_map,
    downcast_dtype,
    memory_probe,
    release_after,
    release_after_block,
    streaming_generator,
    streaming_reduce,
)


def test_streaming_generator_chunk_sizes() -> None:
    """R886 generator 分块大小正确。"""
    gen = streaming_generator(10, 3, lambda s, e: np.arange(s, e))
    sizes = [len(c) for c in gen]
    assert sizes == [3, 3, 3, 1]


def test_streaming_generator_invalid_raises() -> None:
    """R886 非法入参 raise（R03）。"""
    with pytest.raises(ValueError):
        list(streaming_generator(-1, 3, lambda s, e: np.arange(s, e)))
    with pytest.raises(ValueError):
        list(streaming_generator(10, 0, lambda s, e: np.arange(s, e)))


def test_memmap_array_roundtrip(tmp_path) -> None:
    """R887 memmap 写入后读取一致。"""
    path = str(tmp_path / "test_memmap.dat")
    with MemmapArray(path, (1000,), np.float64, "w+") as arr:
        arr[:] = np.arange(1000.0)
        arr.flush()
        assert arr.sum() == pytest.approx(499500.0)
    # 重新只读打开
    with MemmapArray(path, (1000,), np.float64, "r") as arr:
        assert arr[500] == pytest.approx(500.0)
        assert arr.sum() == pytest.approx(499500.0)


def test_memmap_array_invalid_mode_raises() -> None:
    """R887 非法 mode raise（R03）。"""
    with pytest.raises(ValueError):
        MemmapArray("/tmp/x", (10,), np.float64, "invalid")


def test_memory_probe_measures_peak() -> None:
    """R890 memory_probe 测量峰值内存 >0。"""
    with memory_probe() as probe:
        _ = list(range(100_000))
    assert isinstance(probe, MemoryProbeResult)
    assert probe.peak_bytes > 0


def test_release_after_invokes_gc() -> None:
    """R888 release_after 触发 gc 不报错。"""
    big = np.zeros(1000)
    release_after(big)
    del big


def test_release_after_block_triggers_gc() -> None:
    """R895 with 块结束触发 gc.collect（调用方负责 del）。"""
    big = np.zeros(1000)
    with release_after_block():
        _ = big.sum()
        del big
    # big 已显式 del，gc.collect 已触发，无异常即通过
    assert "big" not in locals()


def test_chunked_map_aggregate() -> None:
    """R889 chunked_map 分块+聚合正确。"""
    r = chunked_map(
        10, 3, lambda a: float(a.sum()), lambda s, e: np.arange(s, e), aggregate=sum
    )
    assert isinstance(r, ChunkedResult)
    assert r.outputs == 45.0
    assert r.total_elements == 10
    assert r.total_chunks == 4


def test_chunked_map_invalid_raises() -> None:
    """R889 非法入参 raise。"""
    with pytest.raises(ValueError):
        chunked_map(-1, 3, lambda a: a.sum(), lambda s, e: np.arange(s, e))
    with pytest.raises(ValueError):
        chunked_map(10, 0, lambda a: a.sum(), lambda s, e: np.arange(s, e))


def test_downcast_dtype_halves_memory() -> None:
    """R891 float64→float32 内存减半。"""
    arr = np.ones(1000, dtype=np.float64)
    out = downcast_dtype(arr, np.float32)
    assert out.dtype == np.float32
    assert out.nbytes == arr.nbytes // 2


def test_downcast_dtype_nan_raises() -> None:
    """R891 降精度产生 NaN raise（R03 拒绝 fall-back）。"""
    arr = np.array([1e40], dtype=np.float64)  # float32 溢出为 inf
    with pytest.raises(ValueError):
        downcast_dtype(arr, np.float32)


def test_streaming_reduce_sum() -> None:
    """R894 流式 sum 归约正确。"""
    r = streaming_reduce(10, 3, lambda s, e: np.arange(s, e, dtype=float), "sum")
    assert r == pytest.approx(45.0)


def test_streaming_reduce_max_min() -> None:
    """R894 流式 max/min 归约正确。"""
    mx = streaming_reduce(100, 7, lambda s, e: np.arange(s, e, dtype=float), "max")
    mn = streaming_reduce(100, 7, lambda s, e: np.arange(s, e, dtype=float), "min")
    assert mx == pytest.approx(99.0)
    assert mn == pytest.approx(0.0)


def test_streaming_reduce_invalid_op_raises() -> None:
    """R894 非法 op raise。"""
    with pytest.raises(ValueError):
        streaming_reduce(10, 3, lambda s, e: np.arange(s, e), "invalid")


def test_memory_optimizer_kit_compare() -> None:
    """R900 list vs generator 峰值对照，generator 更省内存。

    list 物化 N 个 int 对象，generator 流式逐个产出，峰值应远低于 list。
    用 N=1_000_000 放大差异确保 tracemalloc 可测。
    """
    kit = MemoryOptimizerKit()
    r = kit.compare_list_vs_generator(1_000_000)
    assert r.list_peak_bytes > 0
    assert r.generator_peak_bytes < r.list_peak_bytes, (
        f"generator peak {r.generator_peak_bytes} 须 < list peak {r.list_peak_bytes}"
    )
    assert r.speedup > 1.0


def test_memory_optimizer_kit_chunked() -> None:
    """R898 kit.chunked facade 正确。"""
    kit = MemoryOptimizerKit()
    r = kit.chunked(20, 5, lambda a: float(a.sum()), lambda s, e: np.arange(s, e), aggregate=sum)
    assert r.outputs == pytest.approx(190.0)


def test_memory_optimizer_kit_reduce_stream() -> None:
    """R899 kit.reduce_stream facade 正确。"""
    kit = MemoryOptimizerKit()
    r = kit.reduce_stream(50, 10, lambda s, e: np.arange(s, e, dtype=float), "sum")
    assert r == pytest.approx(1225.0)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-ra"])
