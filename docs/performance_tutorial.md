# PoLaRIS 性能优化与基准测试教程（R916-R930 补充篇）

> 本教程系统讲解 PoLaRIS 三大性能基础设施的使用：
> **性能调优原语**（`perf_tuning_r851`）、**内存优化工具**（`memory_optimization_r886`）、
> **基准测试套件**（`tests/benchmarks/suite.py`）。
> 所有示例均可在纯 CPU（NumPy/SciPy）环境运行（R04 不参与 GPU）。
> 前置：先读 [入门教程](getting_started.md)。

## 1. 为什么需要性能优化

光子 EDA 的核心计算（FDTD 时域步进、DRC 规则扫描、布线 A* 搜索、寄生提取批量计算）
天然是数据密集型任务。Python 解释器逐元素循环的开销（类型检查、引用计数、对象分配）
会使热点路径慢 10–100 倍。NumPy 向量化将迭代下推到编译后的 C 循环，利用 SIMD 与缓存
友好的连续内存访问，典型加速 10–100 倍。

PoLaRIS 在 `src/polaris/sim/perf_tuning_r851.py` 中封装了 9 个可复用调优原语，
覆盖向量化、缓冲池、缓存、稀疏矩阵、广播距离五大模式。

### 学术依据（R02）

1. Harris et al. 2020 Array programming with NumPy Nature 585 357-362
   https://doi.org/10.1038/s41586-020-2649-2
2. Virtanen et al. 2020 SciPy 1.0 Nature Methods 17 261-272
   https://doi.org/10.1038/s41592-019-0686-2
3. NumPy `sliding_window_view` 官方文档（NumPy ≥1.20 零拷贝窗口视图）
   https://numpy.org/doc/stable/reference/generated/numpy.lib.stride_tricks.sliding_window_view.html
4. SciPy 稀疏矩阵 CSR 格式文档（Compressed Sparse Row）
   https://docs.scipy.org/doc/scipy/reference/sparse.html
5. Lin et al. DREAMPlace TCAD 2020（FFT 密度场平滑，向量化布局）
   https://doi.org/10.1109/TCAD.2020.3003146
6. Soremekun et al. 2021 ABCDPlace ISPD（密度场/布线基准方法学）
   https://doi.org/10.1145/3452144.3462196

## 2. 向量化模板（sliding_window_view）

### 2.1 问题：差分模板的 Python 循环

FDTD / DRC 中的拉普拉斯算子、Sobel 边缘检测等模板卷积，若用双重 for 循环实现，
对 64×64 网格就要 4096 次 Python 迭代：

```python
# 慢：Python 双重循环（仅示意，请勿用于生产）
import numpy as np
field = np.random.rand(64, 64)
kernel = np.array([[0, 1, 0], [1, -4, 1], [0, 1, 0]])
out = np.zeros_like(field)
for i in range(1, field.shape[0] - 1):
    for j in range(1, field.shape[1] - 1):
        out[i, j] = (field[i-1:i+2, j-1:j+2] * kernel).sum()
```

### 2.2 方案：vectorized_stencil 零拷贝窗口

`vectorized_stencil` 用 `np.lib.stride_tricks.sliding_window_view` 生成窗口视图
（不复制数据），再用 `np.einsum` 一次性完成所有窗口与核的乘加，返回与输入同形的卷积结果：

```python
import numpy as np
from polaris.sim.perf_tuning_r851 import vectorized_stencil

field = np.random.rand(64, 64)
kernel = np.array([[0, 1, 0], [1, -4, 1], [0, 1, 0]])  # 拉普拉斯
out = vectorized_stencil(field, kernel, boundary="zero")
print(out.shape)  # (64, 64)，与 field 同形
print(f"结果有限: {np.all(np.isfinite(out))}")
```

### 2.3 PerfTuningKit facade（加速比对照）

需要量化向量化相对 Python 循环的加速比时用 `PerfTuningKit.benchmark_stencil`，
它返回 `StencilResult`（含 `loop_time_ms` / `vector_time_ms` / `speedup` / `max_abs_diff`）：

```python
import numpy as np
from polaris.sim.perf_tuning_r851 import PerfTuningKit

kit = PerfTuningKit()
kernel = np.array([[0, 1, 0], [1, -4, 1], [0, 1, 0]])
r = kit.benchmark_stencil(np.random.rand(64, 64), kernel, repeat=5)
print(f"循环 {r.loop_time_ms:.3f} ms vs 向量化 {r.vector_time_ms:.3f} ms")
print(f"加速比 {r.speedup:.2f}x，最大误差 {r.max_abs_diff:.2e}")
```

基准套件 R874 实测约 9.8 倍（64×64 网格，repeat=3），数值完全一致（`max_abs_diff < 1e-9`）。

## 3. 预分配数组缓冲池（ArrayBufferPool）

### 3.1 问题：热路径反复 malloc/free

FDTD 每步都要临时分配电场、磁场更新数组；DRC 每条规则都要分配掩码数组。
频繁 `np.zeros` 触发内存分配器开销，且碎片化缓存。

### 3.2 方案：LRU 缓冲池复用

`ArrayBufferPool` 按 `(shape, dtype)` 键缓存已分配数组，命中时直接复用：

```python
import numpy as np
from polaris.sim.perf_tuning_r851 import ArrayBufferPool

pool = ArrayBufferPool(max_entries=16)
for i in range(1000):
    buf = pool.get((128, 128), np.float64)  # 首次分配，后续命中
    buf[0, 0] = float(i)
print(pool.stats)  # {'hits': 999, 'misses': 1, 'hit_rate': 0.999}
```

实测 1000 次获取命中率 >99%，省去 999 次分配。

## 4. 计算结果 LRU 缓存（keyed_lru_cache）

### 4.1 问题：重复 S 参数 / 模式求解

频域扫描中，同一器件在同一波长/温度下的 S 参数会被反复求解。标准 `functools.lru_cache`
无法缓存 `np.ndarray`（不可哈希）。

### 4.2 方案：keyed_lru_cache 按可哈希键缓存

`keyed_lru_cache` 将 ndarray 序列化为字节键，实现 LRU 缓存：

```python
import numpy as np
from polaris.sim.perf_tuning_r851 import keyed_lru_cache

@keyed_lru_cache(maxsize=64)
def spectrum(arr: np.ndarray, fs: float) -> np.ndarray:
    return np.abs(np.fft.rfft(arr)) ** 2

arr = np.random.rand(256)
for _ in range(200):
    spectrum(arr, 1.0)  # 首次计算，后续命中
print(spectrum.cache_info())  # {'hits': 199, 'misses': 1, 'hit_rate': 0.995}
```

实测命中率 >99% 时加速最高 73 倍（见基准测试 R876）。

## 5. 稀疏 CSR 矩阵（to_sparse_csr）

### 5.1 问题：DRC/LVS 邻接矩阵稠密存储

版图中器件连接关系天然稀疏（N 个器件，每个仅连接少数邻居），
稠密邻接矩阵占 N² 内存，且矩阵向量乘 O(N²)。

### 5.2 方案：scipy.sparse CSR

`to_sparse_csr` 将 (row, col, val) 三元组转为 CSR 稀疏矩阵：

```python
import numpy as np
from polaris.sim.perf_tuning_r851 import to_sparse_csr

rows = [0, 1, 2]
cols = [1, 2, 0]
vals = np.array([1.0, 2.0, 3.0])
A = to_sparse_csr(rows, cols, vals, (3, 3))
x = np.array([1.0, 2.0, 3.0])
print(A.dot(x))           # 稀疏 matvec
print(f"nnz={A.nnz}")     # 非零元数
```

对 N=1000、nnz=3000 的矩阵，CSR 内存仅稠密的 ~1%，matvec 显著加速（见基准 R877）。

## 6. 广播化成对距离（pairwise_distance）

布线器障碍配对、端口匹配需计算两组点的成对欧氏距离。
双重循环 O(n²) Python 迭代；`pairwise_distance` 用广播一次性算出：

```python
import numpy as np
from polaris.sim.perf_tuning_r851 import pairwise_distance

a = np.random.rand(200, 2)
b = np.random.rand(200, 2)
r = pairwise_distance(a, b)
print(r.distance.shape)  # (200, 200)
# 与 scipy.spatial.distance.cdist 结果一致（max_abs_diff < 1e-9）
```

## 7. 内存优化工具（memory_optimization_r886）

`src/polaris/sim/memory_optimization_r886.py` 提供 6 个内存优化原语。

### 7.1 流式生成器（streaming_generator）

避免物化整个数组，按块产出：

```python
import numpy as np
from polaris.sim.memory_optimization_r886 import streaming_generator

for chunk in streaming_generator(10, 3, lambda s, e: np.arange(s, e)):
    print(chunk)  # [0 1 2] [3 4 5] [6 7 8] [9]
```

### 7.2 内存映射（MemmapArray）

大数组（>内存容量）用 memmap 映射到磁盘，按需读写：

```python
import numpy as np
from polaris.sim.memory_optimization_r886 import MemmapArray

with MemmapArray("/tmp/big.dat", (1_000_000,), np.float64, "w+") as arr:
    arr[:] = np.arange(1_000_000.0)
    arr.flush()
    print(arr.sum())  # 499999500000.0
```

### 7.3 分块映射聚合（chunked_map）

大数据集分块处理 + 聚合，峰值内存仅一个块：

```python
import numpy as np
from polaris.sim.memory_optimization_r886 import chunked_map

r = chunked_map(10, 3, lambda a: float(a.sum()),
                lambda s, e: np.arange(s, e), aggregate=sum)
print(r.outputs)  # 45.0（0+1+...+9）
```

### 7.4 流式归约（streaming_reduce）

sum/max/min 流式归约，不物化全量数据：

```python
import numpy as np
from polaris.sim.memory_optimization_r886 import streaming_reduce

total = streaming_reduce(100, 7,
    lambda s, e: np.arange(s, e, dtype=float), "sum")
print(total)  # 4950.0
```

### 7.5 内存探针（memory_probe）

用 `tracemalloc` 测量代码块峰值内存：

```python
from polaris.sim.memory_optimization_r886 import memory_probe

with memory_probe() as probe:
    _ = list(range(1_000_000))
print(f"峰值 {probe.peak_bytes / 1e6:.1f} MB")
```

### 7.6 list vs generator 对照（MemoryOptimizerKit）

```python
from polaris.sim.memory_optimization_r886 import MemoryOptimizerKit

kit = MemoryOptimizerKit()
r = kit.compare_list_vs_generator(1_000_000)
print(f"list 峰值 {r.list_peak_bytes/1e6:.1f} MB")
print(f"generator 峰值 {r.generator_peak_bytes/1e6:.1f} MB")
print(f"内存节省 {r.speedup:.1f}x")
```

实测 generator 峰值远低于 list（N=1,000,000 时差异显著）。

## 8. 基准测试套件（tests/benchmarks/suite.py）

### 8.1 一键执行全部基准

```python
from tests.benchmarks import run_full_suite

result = run_full_suite()
print(f"基准数 {result.summary['total_benchmarks']}")
print(f"通过 {result.passed}/{result.summary['total_benchmarks']}")
print(f"平均加速 {result.summary['avg_speedup']:.2f}x")
print(f"最高加速 {result.summary['max_speedup']:.2f}x")
for c in result.cases:
    status = "✓" if c.ok else "✗"
    print(f"  {status} {c.name}: {c.elapsed_ms:.2f} ms")
```

### 8.2 12 个基准覆盖

| 基准名 | 域 | 真实内核 |
|--------|-----|---------|
| fdtd_leapfrog | sim/FDTD | FdtdSolver 300 步 |
| fde_mode_solve | sim/FDE | 波导基模求解 |
| parasitic_extraction_batch | sim/寄生 | 批量电容提取 |
| vectorized_stencil_vs_loop | perf 原语 | sliding_window vs 循环 |
| array_buffer_pool_reuse | perf 原语 | 缓冲池命中率 |
| keyed_lru_cache_hit | perf 原语 | LRU 缓存命中率 |
| sparse_vs_dense_matvec | perf 原语 | CSR vs 稠密 matvec |
| pairwise_distance_vs_cdist | perf 原语 | 广播距离 vs cdist |
| fft_density_field | engine | FFT 高斯卷积 |
| curvy_astar_router | router | CurvyAStar 布线 |
| graph_lvs_compare | verification | 图同构 LVS 比对 |
| accumulate_inplace_vs_loop | perf 原语 | ufunc.accumulate vs 循环 |

### 8.3 执行单个基准

```python
from tests.benchmarks import BenchmarkRunner

runner = BenchmarkRunner()
case = runner.run_one("fdtd_leapfrog")
print(f"{case.name}: {case.elapsed_ms:.2f} ms, ok={case.ok}")
print(f"metric: {case.metric}")
```

### 8.4 CI 回归对比

基准框架设计为 CI 友好：每个基准返回 `BenchmarkCase(name, elapsed_ms, metric, ok)`，
失败时 `ok=False` 且 `error` 保留完整 traceback（不静默兜底，R03）。
可在 CI 中对比 commit 前后 `elapsed_ms` 与 `speedup` 回归。

## 9. 性能优化决策树

```
热点是逐元素循环？
├─ 是 → 能否用 ufunc / 广播向量化？（vectorized_stencil / pairwise_distance）
│       ├─ 能 → 向量化（典型 10-100x）
│       └─ 不能（数据依赖分支）→ 考虑算法重写降阶
└─ 否
    ├─ 重复计算同输入？→ keyed_lru_cache（命中率 >99% 时最高 73x）
    ├─ 频繁分配同形状数组？→ ArrayBufferPool（命中率 >99%）
    ├─ 稠密矩阵稀疏？→ to_sparse_csr（内存省 ~95%）
    ├─ 大数组超内存？→ MemmapArray / streaming_generator / chunked_map
    └─ 累加/前缀和？→ accumulate_inplace（ufunc.accumulate）
```

## 10. 端到端性能基准（2026-07-10 同步）

### 10.1 5 项核心性能指标（规则 15.1，5/5 达标）

| # | 操作 | 目标耗时 | 实测平均 | 标准差 | 判定 |
|---|------|----------|----------|--------|------|
| 1 | 网表解析（100 器件） | < 100ms | 3.793ms | 11.391ms | 达标 |
| 2 | A* 布线（单连接） | < 50ms | 1.532ms | 1.694ms | 达标 |
| 3 | GNN 前向推理 | < 10ms | 1.020ms | 1.284ms | 达标 |
| 4 | PPO 训练单步 | < 100ms | 13.099ms | 9.004ms | 达标 |
| 5 | GDS 导出（100 器件） | < 500ms | 14.279ms | 10.196ms | 达标 |

来源：`docs/performance_benchmark.md`（Python 3.14.4 / Xeon 8582C 3 核 / 5.8GB）

### 10.2 端到端流水线基准

| 电路 | 器件数 | 端到端耗时 | 来源 |
|------|--------|-----------|------|
| MZI（showcase 全 11 阶段） | 5 | 21.17s | `examples/e2e_showcase/out/reports/report.md` |
| MZI（生产级 50 步逆向） | 5 | 184.57s | 同上 |

### 10.3 算法 benchmark

| 指标 | 数值 | 来源 |
|------|------|------|
| 布局 HPWL（4 benchmark 平均） | 7052.38 μm | `docs/benchmark_report_analytical.md` |
| 逆向 FoM（生产级 50 步） | +14.72 dB | `docs/mvp_100iter_report.md` |
| 逆向 FoM（showcase 5 步） | +0.18 dB | `examples/e2e_showcase/out/` |
| 量子酉性误差 | 4.44e-16 | `examples/e2e_showcase/out/` |
| 电路 S 参数级联误差 | < 1e-15 | R3 验收 |

### 10.4 性能瓶颈分析

最接近目标上限的指标：**PPO 训练单步**，实测 13.099ms 占目标 100ms 的 13.1%。

```bash
# 复现性能基准
cd /workspace
python scripts/performance_benchmark.py
```

## 11. R03 禁止 fall-back / R04 不参与 GPU

- 所有调优原语失败时 `raise`（如 `vectorized_stencil` 入参非 ndarray 抛 `TypeError`），
  无 `except: pass` / `return None` / `return []`。
- 纯 NumPy/SciPy 实现，无 CuPy/CUDA/ROCm/AppleMetal（R04 战略，不可撤销）。
- 基准测试失败记 `ok=False` 并保留异常信息，不返回假数据。

## 参考资源

- [NumPy 官方文档：向量化与广播](https://numpy.org/doc/stable/user/basics.broadcasting.html)
- [SciPy 稀疏矩阵文档](https://docs.scipy.org/doc/scipy/reference/sparse.html)
- [NumPy stride_tricks 文档](https://numpy.org/doc/stable/reference/generated/numpy.lib.stride_tricks.sliding_window_view.html)
- [Harris 2020 NumPy Nature 论文](https://doi.org/10.1038/s41586-020-2649-2)
- [Virtanen 2020 SciPy Nature Methods 论文](https://doi.org/10.1038/s41592-019-0686-2)
- [Lin DREAMPlace TCAD 2020](https://doi.org/10.1109/TCAD.2020.3003146)
- [Soremekun 2021 ISPD 基准方法学](https://doi.org/10.1145/3452144.3462196)
- [Python tracemalloc 文档](https://docs.python.org/3/library/tracemalloc.html)
- [NumPy memmap 文档](https://numpy.org/doc/stable/reference/generated/numpy.memmap.html)
