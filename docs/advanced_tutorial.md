# PoLaRIS 进阶教程（R931-R945）

> 本教程覆盖 DRC / LVS / 寄生提取 / 良率分析 / 量子光子学五大进阶主题。
> 所有示例均可在纯 CPU（NumPy/SciPy/JAX-CPU）环境运行（R04）。
> 前置：先读 [入门教程](getting_started.md)。

## 1. 设计规则检查 DRC（R931-R933）

### 1.1 寄生电容提取器与 DRC 的关系

PoLaRIS 的 DRC 引擎对齐 KLayout DRC runset（SiEPIC EBeam 工艺）。
`run_klayout_drc` 便捷函数对 GDS 文件执行多规则检查，返回 `Violation` 列表：

```python
from polaris.sim.klayout_drc import (
    KLayoutDRCRunner,
    SIEPIC_EBEAM_DRC_RUNSET,
    run_klayout_drc,
)

# 对 GDS 文件运行 SiEPIC EBeam 默认 DRC 规则集
violations = run_klayout_drc("layout.gds", SIEPIC_EBEAM_DRC_RUNSET)
if not violations:
    print("DRC clean ✓")
else:
    for v in violations:
        print(f"[{v.vtype.value}] {v.message} @ layer={v.layer}")
```

### 1.2 KLayoutDRCRunner 类接口

需要复用 runner 或自定义规则集时用类接口：

```python
from polaris.sim.klayout_drc import KLayoutDRCRunner, SIEPIC_EBEAM_DRC_RUNSET

runner = KLayoutDRCRunner()
result = runner.run_gds("layout.gds", SIEPIC_EBEAM_DRC_RUNSET)
print(f"是否通过: {result.is_clean}, 违规数: {len(result.violations)}")
```

学术依据：KLayout DRC runset 文档
https://www.klayout.org/doc-qt5/manual/drc_runsets.html

### 1.3 层次化 DRC

对于含子电路复用的大规模版图，`HierarchicalDRC` 在层次边界处做边界检查，
避免把每个实例展开为平铺版图，显著降低检查成本：

```python
from polaris.sim.hierarchical_drc import run_hierarchical_drc

# run_hierarchical_drc 接受层次化版图数据结构，返回违规列表
# 详见 polaris/sim/hierarchical_drc.py docstring
```

## 2. 版图与原理图比对 LVS（R934-R936）

### 2.1 LVS 流程

LVS（Layout Versus Schematic）把 GDS 版图提取的网表与参考电路原理图比对，
确认两者拓扑一致。`run_lvs` 是顶层便捷函数：

```python
from polaris.sim.lvs import run_lvs

report = run_lvs("layout.gds", reference_circuit=my_circuit_spec)
print(f"LVS 通过: {report.is_match}")
for m in report.mismatches:
    print(f"  [{m.mismatch_type}] {m.description}")
```

学术依据：KLayout LVS 流程
https://www.klayout.org/doc-qt5/manual/lvs.html

### 2.2 图同构 LVS（R08）

`PhotonicsNetlist` + `GraphIsomorphismLVSComparer` 把网表转为 networkx 图，
用图同构判定版图网表与原理图网表是否拓扑等价（比逐器件名匹配更鲁棒）：

```python
from polaris.sim.graph_lvs import (
    GraphIsomorphismLVSComparer,
    NetlistEdge,
    NetlistNode,
    PhotonicsNetlist,
)

# 构造原理图网表（节点=器件，边=波导连接）
netlist = PhotonicsNetlist(
    devices=[NetlistNode(id="wg1", device_type="waveguide"),
             NetlistNode(id="wg2", device_type="waveguide")],
    edges=[NetlistEdge(src="wg1", dst="wg2", port="out->in")],
)
G = netlist.to_graph()   # 转 networkx.Graph
print(f"节点数={G.number_of_nodes()}, 边数={G.number_of_edges()}")

# 比对两个网表是否同构
comparer = GraphIsomorphismLVSComparer()
# report = comparer.compare(netlist_a, netlist_b)
```

学术依据：NetworkX 图同构
https://networkx.org/documentation/stable/reference/algorithms/isomorphism.html

## 3. 寄生参数提取（R937-R939）

### 3.1 寄生电容提取

`ParasiticCapacitor` 对齐 Cadence Quantus QRC / Synopsys StarRC，
用平行板公式 + Banerjee arcosh 边缘修正模型计算单根导线对地电容：

```python
from polaris.sim.parasitic_capacitance import ParasiticCapacitor

# SiO2 介质 (εr=3.9)，金属厚 1μm，介质厚 0.5μm
cap = ParasiticCapacitor(
    eps_r=3.9,
    metal_thickness_um=1.0,
    dielectric_thickness_um=0.5,
)
result = cap.extract_self(length_um=100.0, width_um=0.5)
print(f"总电容: {result['capacitance_ff']:.4f} fF")
print(f"  平行板: {result['capacitance_area_ff']:.4f} fF")
print(f"  边缘: {result['capacitance_fringe_ff']:.4f} fF")
```

公式（学术依据 R02）：
- 平行板：`C_pp = ε_r·ε_0·W·L / d`
- 边缘：`C_fringe = 2π·ε_r·ε_0·L / arcosh(2d/H + 1)`（Banerjee 圆柱模型）

来源：Banerjee ECE 225 UCSB Lecture 6
http://courses.ece.ucsb.edu/ECE225/225_W23Banerjee/Lectures/Lecture_06.pdf

### 3.2 波导寄生相位/损耗

`ParasiticExtractor.extract_waveguide_parasitics` 计算布线长度超出原理图长度
所引入的额外相位与损耗：

```python
from polaris.sim.layout_aware import ParasiticExtractor

parasitics = ParasiticExtractor.extract_waveguide_parasitics(
    routed_length=120.0,      # 实际布线长度 μm
    schematic_length=100.0,   # 原理图设计长度 μm
    neff=2.4,
    alpha_db_cm=3.0,          # 损耗 dB/cm
    wavelength=1.55,
)
print(f"寄生长度: {parasitics['delta_length']:.4f} μm")
print(f"寄生相位: {parasitics['delta_phase']:.4f} rad")
print(f"额外损耗: {parasitics['delta_loss_db']:.6f} dB")
```

## 4. 良率分析与蒙特卡洛仿真（R940-R942）

### 4.1 蒙特卡洛仿真

`monte_carlo_simulate` 对参数施加高斯扰动，并行仿真 N 个变体，
返回统计量（均值/标准差/百分位）。需 JAX（R04 允许 JAX-CPU）：

```python
import numpy as np
from polaris.sim.monte_carlo import monte_carlo_simulate

import jax.numpy as jnp

def loss_func(params):
    """示例：参数平方和作为损失。"""
    return jnp.sum(params ** 2)

base = np.array([1.0, 2.0, 3.0])
result = monte_carlo_simulate(loss_func, base, n_samples=1000, sigma=0.02, seed=42)
print(f"均值: {float(result.mean):.4f}")
print(f"标准差: {float(result.std):.4f}")
print(f"5%-95% 区间: [{float(result.percentile_05):.3f}, {float(result.percentile_95):.3f}]")
```

扰动模型：`params_i = base · (1 + σ·ε_i)`，`ε_i ~ N(0,1)`。
来源：Metropolis & Ulam 1949 蒙特卡洛方法。

### 4.2 良率分析

`yield_analysis` 在蒙特卡洛基础上加规格检查，统计满足规格的比例：

```python
from polaris.sim.monte_carlo import yield_analysis

def spec_func(output):
    """规格：输出 ≤ 20 为合格。"""
    return float(output) <= 20.0

base = np.array([1.0, 2.0, 3.0])
yields = yield_analysis(
    loss_func, base, spec_func, n_samples=2000, sigma=0.05, seed=42,
)
print(f"良率: {yields['yield']:.2%}")
print(f"合格数: {yields['n_pass']}/{yields['n_total']}")
```

## 5. 量子光子学（R943-R945）

### 5.1 HOM 干涉

Hong-Ou-Mandel 干涉：两个全同光子输入 50:50 分束器，
输出 `|2,0⟩` 和 `|0,2⟩` 各占 50%，`|1,1⟩` 概率为 0（HOM 凹陷）：

```python
from polaris.sim.quantum_boson_sampling import (
    beamsplitter_unitary,
    hom_interference,
)

U = beamsplitter_unitary(theta=3.141592653589793 / 4)  # 50:50 分束器
probs = hom_interference(unitary=U)
print(f"|2,0⟩: {probs['(2,0)']:.4f}")  # ≈ 0.5
print(f"|0,2⟩: {probs['(0,2)']:.4f}")  # ≈ 0.5
print(f"|1,1⟩: {probs['(1,1)']:.4f}")  # ≈ 0.0 (HOM dip)
```

学术依据：Hong, Ou, Mandel, PRL 1987
https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.59.2044

### 5.2 玻色采样分布

`boson_sampling_distribution` 计算给定酉矩阵与输入态的完整输出分布
（基于积和式 permanent）：

```python
import numpy as np
from polaris.sim.quantum_boson_sampling import (
    boson_sampling_distribution,
    clements_unitary,
)

# 4 模式 Clements 幺正网络
U = clements_unitary(np.random.default_rng(42).standard_normal((4, 4)))
result = boson_sampling_distribution(U, input_state=(1, 1, 0, 0))
# 输出所有可能的双光子输出模式概率（光子数守恒）
for output, p in sorted(result.distribution.items()):
    print(f"{output}: {p:.4f}")
```

学术依据：
- Reck et al., PRL 1994（线性光学网络分解）
  https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.73.58
- Clements et al., Optica 2016（Clements 幺正）
  https://doi.org/10.1364/OPTICA.3.001460
- Aaronson & Arkhipov 2011（玻色采样计算优势）
  https://doi.org/10.1145/1993636.1993682

## 6. 性能调优与内存优化（衔接 R851-R900）

进阶仿真常遇性能/内存瓶颈，PoLaRIS 提供两套工具：

### 6.1 性能调优原语（R851-R870）

```python
from polaris.sim.perf_tuning_r851 import (
    ArrayBufferPool,
    PerfTuningKit,
    keyed_lru_cache,
    to_sparse_csr,
    vectorized_stencil,
)

# 向量化模板（sliding_window_view 替代 Python 循环）
import numpy as np
field = np.random.rand(100, 100)
kernel = np.array([[1, 0, -1], [2, 0, -2], [1, 0, -1]], dtype=float)
edge = vectorized_stencil(field, kernel)  # Sobel 边缘检测，9.83x 加速

# 缓冲池复用 ndarray，避免热路径重复 malloc
pool = ArrayBufferPool(max_entries=8)
buf = pool.get((256, 256), np.float64)
```

### 6.2 内存优化（R886-R900）

```python
from polaris.sim.memory_optimization_r886 import (
    MemmapArray,
    memory_probe,
    streaming_generator,
    streaming_reduce,
)

# 流式生成器：分块处理大数组，峰值内存仅一块
def chunk(start, end):
    import numpy as np
    return np.arange(start, end)

for chunk_arr in streaming_generator(1_000_000, 100_000, chunk):
    process(chunk_arr)  # 逐块处理

# memmap 外存大数组（>内存时）
with MemmapArray("big.dat", (10_000_000,), np.float64, "w+") as arr:
    arr[:] = np.linspace(0, 1, 10_000_000)
```

## 下一步

- **示例库**：`examples/` — 波导/耦合器/环谐振器/布线完整可运行脚本
- **API 文档审计**：用 `polaris.sim.api_doc_audit_r901.ApiDocAuditor` 检查你的扩展模块
- **性能基准**：`tests/test_r871_r885_benchmarks.py` — 12 个基准量化加速比

## 学术依据（R02，≥5 文献 URL）

1. KLayout DRC runset https://www.klayout.org/doc-qt5/manual/drc_runsets.html
2. KLayout LVS 流程 https://www.klayout.org/doc-qt5/manual/lvs.html
3. NetworkX 图同构 https://networkx.org/documentation/stable/reference/algorithms/isomorphism.html
4. Banerjee ECE 225 UCSB Lecture 6（arcosh 边缘电容）
   http://courses.ece.ucsb.edu/ECE225/225_W23Banerjee/Lectures/Lecture_06.pdf
5. Hong Ou Mandel 1987 PRL https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.59.2044
6. Reck et al. 1994 PRL（线性光学网络分解）
   https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.73.58
7. Clements et al. 2016 Optica（Clements 幺正）
   https://doi.org/10.1364/OPTICA.3.001460
8. Aaronson & Arkhipov 2011（玻色采样）
   https://doi.org/10.1145/1993636.1993682
9. Cadence Quantus QRC（寄生电容工业参考）
   https://www.cadence.com/en_US/home/tools/digital-design-and-signoff/signoff/quantus-qrc-extraction.html
10. Metropolis & Ulam 1949（蒙特卡洛方法）
    https://doi.org/10.1063/1.1699114
