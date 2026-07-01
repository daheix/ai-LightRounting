"""R886-R900 内存优化"""R886-R900 内存优化模块（纯 NumPy/SciPy CPU，R04 兼容）。

面向 PoLaRIS 仿真大数组场景（FDTD 时序场、S 参数频扫矩阵、"""R886-R900 内存优化模块（纯 NumPy/SciPy CPU，R04 兼容）。

面向 PoLaRIS 仿真大数组场景（FDTD 时序场、S 参数频扫矩阵、密度场
多分辨率金字塔），提供内存优化"""R886-R900 内存优化模块（纯 NumPy/SciPy CPU，R04 兼容）。

面向 PoLaRIS 仿真大数组场景（FDTD 时序场、S 参数频扫矩阵、密度场
多分辨率金字塔），提供内存优化原语，覆盖 R886-R900 共 15 轮：

- R886 generator 流式产出（替代 list 一次性物化）
- R887 np.memmap 外存"""R886-R900 内存优化模块（纯 NumPy/SciPy CPU，R04 兼容）。

面向 PoLaRIS 仿真大数组场景（FDTD 时序场、S 参数频扫矩阵、密度场
多分辨率金字塔），提供内存优化原语，覆盖 R886-R900 共 15 轮：

- R886 generator 流式产出（替代 list 一次性物化）
- R887 np.memmap 外存大数组（>内存容量时磁盘映射）
"""R886-R900 内存优化模块（纯 NumPy/SciPy CPU，R04 兼容）。

面向 PoLaRIS 仿真大数组场景（FDTD 时序场、S 参数频扫矩阵、密度场
多分辨率金字塔），提供内存优化原语，覆盖 R886-R900 共 15 轮：

- R886 generator 流式产出（替代 list 一次性物化）
- R887 np.memmap 外存大数组（>内存容量时磁盘映射）
- R888 大对象 del + gc.collect 显"""R886-R900 内存优化模块（纯 NumPy/SciPy CPU，R04 兼容）。

面向 PoLaRIS 仿真大数组场景（FDTD 时序场、S 参数频扫矩阵、密度场
多分辨率金字塔），提供内存优化原语，覆盖 R886-R900 共 15 轮：

- R886 generator 流式产出（替代 list 一次性物化）
- R887 np.memmap 外存大数组（>内存容量时磁盘映射）
- R888 大对象 del + gc.collect 显式释放
- R889 分块处理 chunked_map（O(N) 内存处理 O(N) 数据）
- R890 峰值内存测量 memory_probe（context manager）
-"""R886-R900 内存优化模块（纯 NumPy/SciPy CPU，R04 兼容）。

面向 PoLaRIS 仿真大数组场景（FDTD 时序场、S 参数频扫矩阵、密度场
多分辨率金字塔），提供内存优化原语，覆盖 R886-R900 共 15 轮：

- R886 generator 流式产出（替代 list 一次性物化）
- R887 np.memmap 外存大数组（>内存容量时磁盘映射）
- R888 大对象 del + gc.collect 显式释放
- R889 分块处理 chunked_map（O(N) 内存处理 O(N) 数据）
- R890 峰值内存测量 memory_probe（context manager）
- R891 数组 dtype 降精度（"""R886-R900 内存优化模块（纯 NumPy/SciPy CPU，R04 兼容）。

面向 PoLaRIS 仿真大数组场景（FDTD 时序场、S 参数频扫矩阵、密度场
多分辨率金字塔），提供内存优化原语，覆盖 R886-R900 共 15 轮：

- R886 generator 流式产出（替代 list 一次性物化）
- R887 np.memmap 外存大数组（>内存容量时磁盘映射）
- R888 大对象 del + gc.collect 显式释放
- R889 分块处理 chunked_map（O(N) 内存处理 O(N) 数据）
- R890 峰值内存测量 memory_probe（context manager）
- R891 数组 dtype 降精度（float64→float32，精度可控场景）
"""R886-R900 内存优化模块（纯 NumPy/SciPy CPU，R04 兼容）。

面向 PoLaRIS 仿真大数组场景（FDTD 时序场、S 参数频扫矩阵、密度场
多分辨率金字塔），提供内存优化原语，覆盖 R886-R900 共 15 轮：

- R886 generator 流式产出（替代 list 一次性物化）
- R887 np.memmap 外存大数组（>内存容量时磁盘映射）
- R888 大对象 del + gc.collect 显式释放
- R889 分块处理 chunked_map（O(N) 内存处理 O(N) 数据）
- R890 峰值内存测量 memory_probe（context manager）
- R891 数组 dtype 降精度（float64→float32，精度可控场景）
- R892 视图替代切片复制（stride_tricks零拷贝）
- R"""R886-R900 内存优化模块（纯 NumPy/SciPy CPU，R04 兼容）。

面向 PoLaRIS 仿真大数组场景（FDTD 时序场、S 参数频扫矩阵、密度场
多分辨率金字塔），提供内存优化原语，覆盖 R886-R900 共 15 轮：

- R886 generator 流式产出（替代 list 一次性物化）
- R887 np.memmap 外存大数组（>内存容量时磁盘映射）
- R888 大对象 del + gc.collect 显式释放
- R889 分块处理 chunked_map（O(N) 内存处理 O(N) 数据）
- R890 峰值内存测量 memory_probe（context manager）
- R891 数组 dtype 降精度（float64→float32，精度可控场景）
- R892 视图替代切片复制（stride_tricks零拷贝）
- R893 稀疏替代密集（CSR"""R886-R900 内存优化模块（纯 NumPy/SciPy CPU，R04 兼容）。

面向 PoLaRIS 仿真大数组场景（FDTD 时序场、S 参数频扫矩阵、密度场
多分辨率金字塔），提供内存优化原语，覆盖 R886-R900 共 15 轮：

- R886 generator 流式产出（替代 list 一次性物化）
- R887 np.memmap 外存大数组（>内存容量时磁盘映射）
- R888 大对象 del + gc.collect 显式释放
- R889 分块处理 chunked_map（O(N) 内存处理 O(N) 数据）
- R890 峰值内存测量 memory_probe（context manager）
- R891 数组 dtype 降精度（float64→float32，精度可控场景）
- R892 视图替代切片复制（stride_tricks零拷贝）
- R893 稀疏替代密集（CSR 节省 ~95%）
- R894 流式归约 streaming_reduce（不物化"""R886-R900 内存优化模块（纯 NumPy/SciPy CPU，R04 兼容）。

面向 PoLaRIS 仿真大数组场景（FDTD 时序场、S 参数频扫矩阵、密度场
多分辨率金字塔），提供内存优化原语，覆盖 R886-R900 共 15 轮：

- R886 generator 流式产出（替代 list 一次性物化）
- R887 np.memmap 外存大数组（>内存容量时磁盘映射）
- R888 大对象 del + gc.collect 显式释放
- R889 分块处理 chunked_map（O(N) 内存处理 O(N) 数据）
- R890 峰值内存测量 memory_probe（context manager）
- R891 数组 dtype 降精度（float64→float32，精度可控场景）
- R892 视图替代切片复制（stride_tricks零拷贝）
- R893 稀疏替代密集（CSR 节省 ~95%）
- R894 流式归约 streaming_reduce（不物化中间数组）
- R895 释放回调 release_after（with 块结束自动 del+gc）
- R896-R900 综"""R886-R900 内存优化模块（纯 NumPy/SciPy CPU，R04 兼容）。

面向 PoLaRIS 仿真大数组场景（FDTD 时序场、S 参数频扫矩阵、密度场
多分辨率金字塔），提供内存优化原语，覆盖 R886-R900 共 15 轮：

- R886 generator 流式产出（替代 list 一次性物化）
- R887 np.memmap 外存大数组（>内存容量时磁盘映射）
- R888 大对象 del + gc.collect 显式释放
- R889 分块处理 chunked_map（O(N) 内存处理 O(N) 数据）
- R890 峰值内存测量 memory_probe（context manager）
- R891 数组 dtype 降精度（float64→float32，精度可控场景）
- R892 视图替代切片复制（stride_tricks零拷贝）
- R893 稀疏替代密集（CSR 节省 ~95%）
- R894 流式归约 streaming_reduce（不物化中间数组）
- R895 释放回调 release_after（with 块结束自动 del+gc）
- R896-R900 综合内存工具集 facade MemoryOptimizerKit

##"""R886-R900 内存优化模块（纯 NumPy/SciPy CPU，R04 兼容）。

面向 PoLaRIS 仿真大数组场景（FDTD 时序场、S 参数频扫矩阵、密度场
多分辨率金字塔），提供内存优化原语，覆盖 R886-R900 共 15 轮：

- R886 generator 流式产出（替代 list 一次性物化）
- R887 np.memmap 外存大数组（>内存容量时磁盘映射）
- R888 大对象 del + gc.collect 显式释放
- R889 分块处理 chunked_map（O(N) 内存处理 O(N) 数据）
- R890 峰值内存测量 memory_probe（context manager）
- R891 数组 dtype 降精度（float64→float32，精度可控场景）
- R892 视图替代切片复制（stride_tricks零拷贝）
- R893 稀疏替代密集（CSR 节省 ~95%）
- R894 流式归约 streaming_reduce（不物化中间数组）
- R895 释放回调 release_after（with 块结束自动 del+gc）
- R896-R900 综合内存工具集 facade MemoryOptimizerKit

## 设计原则

1. 内存优先：能流"""R886-R900 内存优化模块（纯 NumPy/SciPy CPU，R04 兼容）。

面向 PoLaRIS 仿真大数组场景（FDTD 时序场、S 参数频扫矩阵、密度场
多分辨率金字塔），提供内存优化原语，覆盖 R886-R900 共 15 轮：

- R886 generator 流式产出（替代 list 一次性物化）
- R887 np.memmap 外存大数组（>内存容量时磁盘映射）
- R888 大对象 del + gc.collect 显式释放
- R889 分块处理 chunked_map（O(N) 内存处理 O(N) 数据）
- R890 峰值内存测量 memory_probe（context manager）
- R891 数组 dtype 降精度（float64→float32，精度可控场景）
- R892 视图替代切片复制（stride_tricks零拷贝）
- R893 稀疏替代密集（CSR 节省 ~95%）
- R894 流式归约 streaming_reduce（不物化中间数组）
- R895 释放回调 release_after（with 块结束自动 del+gc）
- R896-R900 综合内存工具集 facade MemoryOptimizerKit

## 设计原则

1. 内存优先：能流式不物化，能 memmap 不全载入，能稀疏不密集
2"""R886-R900 内存优化模块（纯 NumPy/SciPy CPU，R04 兼容）。

面向 PoLaRIS 仿真大数组场景（FDTD 时序场、S 参数频扫矩阵、密度场
多分辨率金字塔），提供内存优化原语，覆盖 R886-R900 共 15 轮：

- R886 generator 流式产出（替代 list 一次性物化）
- R887 np.memmap 外存大数组（>内存容量时磁盘映射）
- R888 大对象 del + gc.collect 显式释放
- R889 分块处理 chunked_map（O(N) 内存处理 O(N) 数据）
- R890 峰值内存测量 memory_probe（context manager）
- R891 数组 dtype 降精度（float64→float32，精度可控场景）
- R892 视图替代切片复制（stride_tricks零拷贝）
- R893 稀疏替代密集（CSR 节省 ~95%）
- R894 流式归约 streaming_reduce（不物化中间数组）
- R895 释放回调 release_after（with 块结束自动 del+gc）
- R896-R900 综合内存工具集 facade MemoryOptimizerKit

## 设计原则

1. 内存优先：能流式不物化，能 memmap 不全载入，能稀疏不密集
2. 显式释放：大对象用完即"""R886-R900 内存优化模块（纯 NumPy/SciPy CPU，R04 兼容）。

面向 PoLaRIS 仿真大数组场景（FDTD 时序场、S 参数频扫矩阵、密度场
多分辨率金字塔），提供内存优化原语，覆盖 R886-R900 共 15 轮：

- R886 generator 流式产出（替代 list 一次性物化）
- R887 np.memmap 外存大数组（>内存容量时磁盘映射）
- R888 大对象 del + gc.collect 显式释放
- R889 分块处理 chunked_map（O(N) 内存处理 O(N) 数据）
- R890 峰值内存测量 memory_probe（context manager）
- R891 数组 dtype 降精度（float64→float32，精度可控场景）
- R892 视图替代切片复制（stride_tricks零拷贝）
- R893 稀疏替代密集（CSR 节省 ~95%）
- R894 流式归约 streaming_reduce（不物化中间数组）
- R895 释放回调 release_after（with 块结束自动 del+gc）
- R896-R900 综合内存工具集 facade MemoryOptimizerKit

## 设计原则

1. 内存优先：能流式不物化，能 memmap 不全载入，能稀疏不密集
2. 显式释放：大对象用完即 del + gc.collect，不依赖 GC 时机
3. dtype 适配：存储用 float32，计算用 float64（避免累积误差"""R886-R900 内存优化模块（纯 NumPy/SciPy CPU，R04 兼容）。

面向 PoLaRIS 仿真大数组场景（FDTD 时序场、S 参数频扫矩阵、密度场
多分辨率金字塔），提供内存优化原语，覆盖 R886-R900 共 15 轮：

- R886 generator 流式产出（替代 list 一次性物化）
- R887 np.memmap 外存大数组（>内存容量时磁盘映射）
- R888 大对象 del + gc.collect 显式释放
- R889 分块处理 chunked_map（O(N) 内存处理 O(N) 数据）
- R890 峰值内存测量 memory_probe（context manager）
- R891 数组 dtype 降精度（float64→float32，精度可控场景）
- R892 视图替代切片复制（stride_tricks零拷贝）
- R893 稀疏替代密集（CSR 节省 ~95%）
- R894 流式归约 streaming_reduce（不物化中间数组）
- R895 释放回调 release_after（with 块结束自动 del+gc）
- R896-R900 综合内存工具集 facade MemoryOptimizerKit

## 设计原则

1. 内存优先：能流式不物化，能 memmap 不全载入，能稀疏不密集
2. 显式释放：大对象用完即 del + gc.collect，不依赖 GC 时机
3. dtype 适配：存储用 float32，计算用 float64（避免累积误差）
4. 零拷贝视图：stride_tricks 提供窗口视图，不复制"""R886-R900 内存优化模块（纯 NumPy/SciPy CPU，R04 兼容）。

面向 PoLaRIS 仿真大数组场景（FDTD 时序场、S 参数频扫矩阵、密度场
多分辨率金字塔），提供内存优化原语，覆盖 R886-R900 共 15 轮：

- R886 generator 流式产出（替代 list 一次性物化）
- R887 np.memmap 外存大数组（>内存容量时磁盘映射）
- R888 大对象 del + gc.collect 显式释放
- R889 分块处理 chunked_map（O(N) 内存处理 O(N) 数据）
- R890 峰值内存测量 memory_probe（context manager）
- R891 数组 dtype 降精度（float64→float32，精度可控场景）
- R892 视图替代切片复制（stride_tricks零拷贝）
- R893 稀疏替代密集（CSR 节省 ~95%）
- R894 流式归约 streaming_reduce（不物化中间数组）
- R895 释放回调 release_after（with 块结束自动 del+gc）
- R896-R900 综合内存工具集 facade MemoryOptimizerKit

## 设计原则

1. 内存优先：能流式不物化，能 memmap 不全载入，能稀疏不密集
2. 显式释放：大对象用完即 del + gc.collect，不依赖 GC 时机
3. dtype 适配：存储用 float32，计算用 float64（避免累积误差）
4. 零拷贝视图：stride_tricks 提供窗口视图，不复制数据

## R04 战略（不可撤销）

🚫不参与 GPU：纯 NumPy/"""R886-R900 内存优化模块（纯 NumPy/SciPy CPU，R04 兼容）。

面向 PoLaRIS 仿真大数组场景（FDTD 时序场、S 参数频扫矩阵、密度场
多分辨率金字塔），提供内存优化原语，覆盖 R886-R900 共 15 轮：

- R886 generator 流式产出（替代 list 一次性物化）
- R887 np.memmap 外存大数组（>内存容量时磁盘映射）
- R888 大对象 del + gc.collect 显式释放
- R889 分块处理 chunked_map（O(N) 内存处理 O(N) 数据）
- R890 峰值内存测量 memory_probe（context manager）
- R891 数组 dtype 降精度（float64→float32，精度可控场景）
- R892 视图替代切片复制（stride_tricks零拷贝）
- R893 稀疏替代密集（CSR 节省 ~95%）
- R894 流式归约 streaming_reduce（不物化中间数组）
- R895 释放回调 release_after（with 块结束自动 del+gc）
- R896-R900 综合内存工具集 facade MemoryOptimizerKit

## 设计原则

1. 内存优先：能流式不物化，能 memmap 不全载入，能稀疏不密集
2. 显式释放：大对象用完即 del + gc.collect，不依赖 GC 时机
3. dtype 适配：存储用 float32，计算用 float64（避免累积误差）
4. 零拷贝视图：stride_tricks 提供窗口视图，不复制数据

## R04 战略（不可撤销）

🚫不参与 GPU：纯 NumPy/SciPy。无 CuPy/CUDA/ROC"""R886-R900 内存优化模块（纯 NumPy/SciPy CPU，R04 兼容）。

面向 PoLaRIS 仿真大数组场景（FDTD 时序场、S 参数频扫矩阵、密度场
多分辨率金字塔），提供内存优化原语，覆盖 R886-R900 共 15 轮：

- R886 generator 流式产出（替代 list 一次性物化）
- R887 np.memmap 外存大数组（>内存容量时磁盘映射）
- R888 大对象 del + gc.collect 显式释放
- R889 分块处理 chunked_map（O(N) 内存处理 O(N) 数据）
- R890 峰值内存测量 memory_probe（context manager）
- R891 数组 dtype 降精度（float64→float32，精度可控场景）
- R892 视图替代切片复制（stride_tricks零拷贝）
- R893 稀疏替代密集（CSR 节省 ~95%）
- R894 流式归约 streaming_reduce（不物化中间数组）
- R895 释放回调 release_after（with 块结束自动 del+gc）
- R896-R900 综合内存工具集 facade MemoryOptimizerKit

## 设计原则

1. 内存优先：能流式不物化，能 memmap 不全载入，能稀疏不密集
2. 显式释放：大对象用完即 del + gc.collect，不依赖 GC 时机
3. dtype 适配：存储用 float32，计算用 float64（避免累积误差）
4. 零拷贝视图：stride_tricks 提供窗口视图，不复制数据

## R04 战略（不可撤销）

🚫不参与 GPU：纯 NumPy/SciPy。无 CuPy/CUDA/ROCm/AppleMetal。

## R03 禁止 fall-back

业务错误一律 raise。memmap 文件创建失败、dtype 非法、shape 非法
均 raise，无 except: pass / return None / return []。

## 学术依据（R02，≥5 个文献 URL）

1. Harris et al. 2020 Array programming with NumPy Nature 585 357-362
   https://doi.org/10.1038/s4"""R886-R900 内存优化模块（纯 NumPy/SciPy CPU，R04 兼容）。

面向 PoLaRIS 仿真大数组场景（FDTD 时序场、S 参数频扫矩阵、密度场
多分辨率金字塔），提供内存优化原语，覆盖 R886-R900 共 15 轮：

- R886 generator 流式产出（替代 list 一次性物化）
- R887 np.memmap 外存大数组（>内存容量时磁盘映射）
- R888 大对象 del + gc.collect 显式释放
- R889 分块处理 chunked_map（O(N) 内存处理 O(N) 数据）
- R890 峰值内存测量 memory_probe（context manager）
- R891 数组 dtype 降精度（float64→float32，精度可控场景）
- R892 视图替代切片复制（stride_tricks零拷贝）
- R893 稀疏替代密集（CSR 节省 ~95%）
- R894 流式归约 streaming_reduce（不物化中间数组）
- R895 释放回调 release_after（with 块结束自动 del+gc）
- R896-R900 综合内存工具集 facade MemoryOptimizerKit

## 设计原则

1. 内存优先：能流式不物化，能 memmap 不全载入，能稀疏不密集
2. 显式释放：大对象用完即 del + gc.collect，不依赖 GC 时机
3. dtype 适配：存储用 float32，计算用 float64（避免累积误差）
4. 零拷贝视图：stride_tricks 提供窗口视图，不复制数据

## R04 战略（不可撤销）

🚫不参与 GPU：纯 NumPy/SciPy。无 CuPy/CUDA/ROCm/AppleMetal。

## R03 禁止 fall-back

业务错误一律 raise。memmap 文件创建失败、dtype 非法、shape 非法
均 raise，无 except: pass / return None / return []。

## 学术依据（R02，≥5 个文献 URL）

1. Harris et al. 2020 Array programming with NumPy Nature 585 357-362
   https://doi.org/10.1038/s41586-020-2649-2
2. NumPy memmap 官方文档（内存映射文件，out-of-core 计算）
   https://numpy.org/doc/stable/reference/generated/numpy.memmap.html
3. Virtanen et al. 2020 SciPy"""R886-R900 内存优化模块（纯 NumPy/SciPy CPU，R04 兼容）。

面向 PoLaRIS 仿真大数组场景（FDTD 时序场、S 参数频扫矩阵、密度场
多分辨率金字塔），提供内存优化原语，覆盖 R886-R900 共 15 轮：

- R886 generator 流式产出（替代 list 一次性物化）
- R887 np.memmap 外存大数组（>内存容量时磁盘映射）
- R888 大对象 del + gc.collect 显式释放
- R889 分块处理 chunked_map（O(N) 内存处理 O(N) 数据）
- R890 峰值内存测量 memory_probe（context manager）
- R891 数组 dtype 降精度（float64→float32，精度可控场景）
- R892 视图替代切片复制（stride_tricks零拷贝）
- R893 稀疏替代密集（CSR 节省 ~95%）
- R894 流式归约 streaming_reduce（不物化中间数组）
- R895 释放回调 release_after（with 块结束自动 del+gc）
- R896-R900 综合内存工具集 facade MemoryOptimizerKit

## 设计原则

1. 内存优先：能流式不物化，能 memmap 不全载入，能稀疏不密集
2. 显式释放：大对象用完即 del + gc.collect，不依赖 GC 时机
3. dtype 适配：存储用 float32，计算用 float64（避免累积误差）
4. 零拷贝视图：stride_tricks 提供窗口视图，不复制数据

## R04 战略（不可撤销）

🚫不参与 GPU：纯 NumPy/SciPy。无 CuPy/CUDA/ROCm/AppleMetal。

## R03 禁止 fall-back

业务错误一律 raise。memmap 文件创建失败、dtype 非法、shape 非法
均 raise，无 except: pass / return None / return []。

## 学术依据（R02，≥5 个文献 URL）

1. Harris et al. 2020 Array programming with NumPy Nature 585 357-362
   https://doi.org/10.1038/s41586-020-2649-2
2. NumPy memmap 官方文档（内存映射文件，out-of-core 计算）
   https://numpy.org/doc/stable/reference/generated/numpy.memmap.html
3. Virtanen et al. 2020 SciPy 1.0 Nature Methods 17 261-272
   https://doi.org/10.1038/s41592-0"""R886-R900 内存优化模块（纯 NumPy/SciPy CPU，R04 兼容）。

面向 PoLaRIS 仿真大数组场景（FDTD 时序场、S 参数频扫矩阵、密度场
多分辨率金字塔），提供内存优化原语，覆盖 R886-R900 共 15 轮：

- R886 generator 流式产出（替代 list 一次性物化）
- R887 np.memmap 外存大数组（>内存容量时磁盘映射）
- R888 大对象 del + gc.collect 显式释放
- R889 分块处理 chunked_map（O(N) 内存处理 O(N) 数据）
- R890 峰值内存测量 memory_probe（context manager）
- R891 数组 dtype 降精度（float64→float32，精度可控场景）
- R892 视图替代切片复制（stride_tricks零拷贝）
- R893 稀疏替代密集（CSR 节省 ~95%）
- R894 流式归约 streaming_reduce（不物化中间数组）
- R895 释放回调 release_after（with 块结束自动 del+gc）
- R896-R900 综合内存工具集 facade MemoryOptimizerKit

## 设计原则

1. 内存优先：能流式不物化，能 memmap 不全载入，能稀疏不密集
2. 显式释放：大对象用完即 del + gc.collect，不依赖 GC 时机
3. dtype 适配：存储用 float32，计算用 float64（避免累积误差）
4. 零拷贝视图：stride_tricks 提供窗口视图，不复制数据

## R04 战略（不可撤销）

🚫不参与 GPU：纯 NumPy/SciPy。无 CuPy/CUDA/ROCm/AppleMetal。

## R03 禁止 fall-back

业务错误一律 raise。memmap 文件创建失败、dtype 非法、shape 非法
均 raise，无 except: pass / return None / return []。

## 学术依据（R02，≥5 个文献 URL）

1. Harris et al. 2020 Array programming with NumPy Nature 585 357-362
   https://doi.org/10.1038/s41586-020-2649-2
2. NumPy memmap 官方文档（内存映射文件，out-of-core 计算）
   https://numpy.org/doc/stable/reference/generated/numpy.memmap.html
3. Virtanen et al. 2020 SciPy 1.0 Nature Methods 17 261-272
   https://doi.org/10.1038/s41592-019-0686-2
4. Dask chunked arrays 文档（分块"""R886-R900 内存优化模块（纯 NumPy/SciPy CPU，R04 兼容）。

面向 PoLaRIS 仿真大数组场景（FDTD 时序场、S 参数频扫矩阵、密度场
多分辨率金字塔），提供内存优化原语，覆盖 R886-R900 共 15 轮：

- R886 generator 流式产出（替代 list 一次性物化）
- R887 np.memmap 外存大数组（>内存容量时磁盘映射）
- R888 大对象 del + gc.collect 显式释放
- R889 分块处理 chunked_map（O(N) 内存处理 O(N) 数据）
- R890 峰值内存测量 memory_probe（context manager）
- R891 数组 dtype 降精度（float64→float32，精度可控场景）
- R892 视图替代切片复制（stride_tricks零拷贝）
- R893 稀疏替代密集（CSR 节省 ~95%）
- R894 流式归约 streaming_reduce（不物化中间数组）
- R895 释放回调 release_after（with 块结束自动 del+gc）
- R896-R900 综合内存工具集 facade MemoryOptimizerKit

## 设计原则

1. 内存优先：能流式不物化，能 memmap 不全载入，能稀疏不密集
2. 显式释放：大对象用完即 del + gc.collect，不依赖 GC 时机
3. dtype 适配：存储用 float32，计算用 float64（避免累积误差）
4. 零拷贝视图：stride_tricks 提供窗口视图，不复制数据

## R04 战略（不可撤销）

🚫不参与 GPU：纯 NumPy/SciPy。无 CuPy/CUDA/ROCm/AppleMetal。

## R03 禁止 fall-back

业务错误一律 raise。memmap 文件创建失败、dtype 非法、shape 非法
均 raise，无 except: pass / return None / return []。

## 学术依据（R02，≥5 个文献 URL）

1. Harris et al. 2020 Array programming with NumPy Nature 585 357-362
   https://doi.org/10.1038/s41586-020-2649-2
2. NumPy memmap 官方文档（内存映射文件，out-of-core 计算）
   https://numpy.org/doc/stable/reference/generated/numpy.memmap.html
3. Virtanen et al. 2020 SciPy 1.0 Nature Methods 17 261-272
   https://doi.org/10.1038/s41592-019-0686-2
4. Dask chunked arrays 文档（分块数组 out-of-core 范式）
   https"""R886-R900 内存优化模块（纯 NumPy/SciPy CPU，R04 兼容）。

面向 PoLaRIS 仿真大数组场景（FDTD 时序场、S 参数频扫矩阵、密度场
多分辨率金字塔），提供内存优化原语，覆盖 R886-R900 共 15 轮：

- R886 generator 流式产出（替代 list 一次性物化）
- R887 np.memmap 外存大数组（>内存容量时磁盘映射）
- R888 大对象 del + gc.collect 显式释放
- R889 分块处理 chunked_map（O(N) 内存处理 O(N) 数据）
- R890 峰值内存测量 memory_probe（context manager）
- R891 数组 dtype 降精度（float64→float32，精度可控场景）
- R892 视图替代切片复制（stride_tricks零拷贝）
- R893 稀疏替代密集（CSR 节省 ~95%）
- R894 流式归约 streaming_reduce（不物化中间数组）
- R895 释放回调 release_after（with 块结束自动 del+gc）
- R896-R900 综合内存工具集 facade MemoryOptimizerKit

## 设计原则

1. 内存优先：能流式不物化，能 memmap 不全载入，能稀疏不密集
2. 显式释放：大对象用完即 del + gc.collect，不依赖 GC 时机
3. dtype 适配：存储用 float32，计算用 float64（避免累积误差）
4. 零拷贝视图：stride_tricks 提供窗口视图，不复制数据

## R04 战略（不可撤销）

🚫不参与 GPU：纯 NumPy/SciPy。无 CuPy/CUDA/ROCm/AppleMetal。

## R03 禁止 fall-back

业务错误一律 raise。memmap 文件创建失败、dtype 非法、shape 非法
均 raise，无 except: pass / return None / return []。

## 学术依据（R02，≥5 个文献 URL）

1. Harris et al. 2020 Array programming with NumPy Nature 585 357-362
   https://doi.org/10.1038/s41586-020-2649-2
2. NumPy memmap 官方文档（内存映射文件，out-of-core 计算）
   https://numpy.org/doc/stable/reference/generated/numpy.memmap.html
3. Virtanen et al. 2020 SciPy 1.0 Nature Methods 17 261-272
   https://doi.org/10.1038/s41592-019-0686-2
4. Dask chunked arrays 文档（分块数组 out-of-core 范式）
   https://docs.dask.org/en/stable/array.html
5. Python gc 模块文档（显式垃圾回收 + 循环引用检测"""R886-R900 内存优化模块（纯 NumPy/SciPy CPU，R04 兼容）。

面向 PoLaRIS 仿真大数组场景（FDTD 时序场、S 参数频扫矩阵、密度场
多分辨率金字塔），提供内存优化原语，覆盖 R886-R900 共 15 轮：

- R886 generator 流式产出（替代 list 一次性物化）
- R887 np.memmap 外存大数组（>内存容量时磁盘映射）
- R888 大对象 del + gc.collect 显式释放
- R889 分块处理 chunked_map（O(N) 内存处理 O(N) 数据）
- R890 峰值内存测量 memory_probe（context manager）
- R891 数组 dtype 降精度（float64→float32，精度可控场景）
- R892 视图替代切片复制（stride_tricks零拷贝）
- R893 稀疏替代密集（CSR 节省 ~95%）
- R894 流式归约 streaming_reduce（不物化中间数组）
- R895 释放回调 release_after（with 块结束自动 del+gc）
- R896-R900 综合内存工具集 facade MemoryOptimizerKit

## 设计原则

1. 内存优先：能流式不物化，能 memmap 不全载入，能稀疏不密集
2. 显式释放：大对象用完即 del + gc.collect，不依赖 GC 时机
3. dtype 适配：存储用 float32，计算用 float64（避免累积误差）
4. 零拷贝视图：stride_tricks 提供窗口视图，不复制数据

## R04 战略（不可撤销）

🚫不参与 GPU：纯 NumPy/SciPy。无 CuPy/CUDA/ROCm/AppleMetal。

## R03 禁止 fall-back

业务错误一律 raise。memmap 文件创建失败、dtype 非法、shape 非法
均 raise，无 except: pass / return None / return []。

## 学术依据（R02，≥5 个文献 URL）

1. Harris et al. 2020 Array programming with NumPy Nature 585 357-362
   https://doi.org/10.1038/s41586-020-2649-2
2. NumPy memmap 官方文档（内存映射文件，out-of-core 计算）
   https://numpy.org/doc/stable/reference/generated/numpy.memmap.html
3. Virtanen et al. 2020 SciPy 1.0 Nature Methods 17 261-272
   https://doi.org/10.1038/s41592-019-0686-2
4. Dask chunked arrays 文档（分块数组 out-of-core 范式）
   https://docs.dask.org/en/stable/array.html
5. Python gc 模块文档（显式垃圾回收 + 循环引用检测）
   https://docs.python.org/3/library/gc.html
6. Higham 2002 Accuracy and Stability of Numerical Algorithms 2nd SIAM
   （float32 vs float"""R886-R900 内存优化模块（纯 NumPy/SciPy CPU，R04 兼容）。

面向 PoLaRIS 仿真大数组场景（FDTD 时序场、S 参数频扫矩阵、密度场
多分辨率金字塔），提供内存优化原语，覆盖 R886-R900 共 15 轮：

- R886 generator 流式产出（替代 list 一次性物化）
- R887 np.memmap 外存大数组（>内存容量时磁盘映射）
- R888 大对象 del + gc.collect 显式释放
- R889 分块处理 chunked_map（O(N) 内存处理 O(N) 数据）
- R890 峰值内存测量 memory_probe（context manager）
- R891 数组 dtype 降精度（float64→float32，精度可控场景）
- R892 视图替代切片复制（stride_tricks零拷贝）
- R893 稀疏替代密集（CSR 节省 ~95%）
- R894 流式归约 streaming_reduce（不物化中间数组）
- R895 释放回调 release_after（with 块结束自动 del+gc）
- R896-R900 综合内存工具集 facade MemoryOptimizerKit

## 设计原则

1. 内存优先：能流式不物化，能 memmap 不全载入，能稀疏不密集
2. 显式释放：大对象用完即 del + gc.collect，不依赖 GC 时机
3. dtype 适配：存储用 float32，计算用 float64（避免累积误差）
4. 零拷贝视图：stride_tricks 提供窗口视图，不复制数据

## R04 战略（不可撤销）

🚫不参与 GPU：纯 NumPy/SciPy。无 CuPy/CUDA/ROCm/AppleMetal。

## R03 禁止 fall-back

业务错误一律 raise。memmap 文件创建失败、dtype 非法、shape 非法
均 raise，无 except: pass / return None / return []。

## 学术依据（R02，≥5 个文献 URL）

1. Harris et al. 2020 Array programming with NumPy Nature 585 357-362
   https://doi.org/10.1038/s41586-020-2649-2
2. NumPy memmap 官方文档（内存映射文件，out-of-core 计算）
   https://numpy.org/doc/stable/reference/generated/numpy.memmap.html
3. Virtanen et al. 2020 SciPy 1.0 Nature Methods 17 261-272
   https://doi.org/10.1038/s41592-019-0686-2
4. Dask chunked arrays 文档（分块数组 out-of-core 范式）
   https://docs.dask.org/en/stable/array.html
5. Python gc 模块文档（显式垃圾回收 + 循环引用检测）
   https://docs.python.org/3/library/gc.html
6. Higham 2002 Accuracy and Stability of Numerical Algorithms 2nd SIAM
   （float32 vs float64 累积误差分析）https://doi.org/10.1137/1.9780898718027
7. McKinney 2017 Python for Data Analysis"""R886-R900 内存优化模块（纯 NumPy/SciPy CPU，R04 兼容）。

面向 PoLaRIS 仿真大数组场景（FDTD 时序场、S 参数频扫矩阵、密度场
多分辨率金字塔），提供内存优化原语，覆盖 R886-R900 共 15 轮：

- R886 generator 流式产出（替代 list 一次性物化）
- R887 np.memmap 外存大数组（>内存容量时磁盘映射）
- R888 大对象 del + gc.collect 显式释放
- R889 分块处理 chunked_map（O(N) 内存处理 O(N) 数据）
- R890 峰值内存测量 memory_probe（context manager）
- R891 数组 dtype 降精度（float64→float32，精度可控场景）
- R892 视图替代切片复制（stride_tricks零拷贝）
- R893 稀疏替代密集（CSR 节省 ~95%）
- R894 流式归约 streaming_reduce（不物化中间数组）
- R895 释放回调 release_after（with 块结束自动 del+gc）
- R896-R900 综合内存工具集 facade MemoryOptimizerKit

## 设计原则

1. 内存优先：能流式不物化，能 memmap 不全载入，能稀疏不密集
2. 显式释放：大对象用完即 del + gc.collect，不依赖 GC 时机
3. dtype 适配：存储用 float32，计算用 float64（避免累积误差）
4. 零拷贝视图：stride_tricks 提供窗口视图，不复制数据

## R04 战略（不可撤销）

🚫不参与 GPU：纯 NumPy/SciPy。无 CuPy/CUDA/ROCm/AppleMetal。

## R03 禁止 fall-back

业务错误一律 raise。memmap 文件创建失败、dtype 非法、shape 非法
均 raise，无 except: pass / return None / return []。

## 学术依据（R02，≥5 个文献 URL）

1. Harris et al. 2020 Array programming with NumPy Nature 585 357-362
   https://doi.org/10.1038/s41586-020-2649-2
2. NumPy memmap 官方文档（内存映射文件，out-of-core 计算）
   https://numpy.org/doc/stable/reference/generated/numpy.memmap.html
3. Virtanen et al. 2020 SciPy 1.0 Nature Methods 17 261-272
   https://doi.org/10.1038/s41592-019-0686-2
4. Dask chunked arrays 文档（分块数组 out-of-core 范式）
   https://docs.dask.org/en/stable/array.html
5. Python gc 模块文档（显式垃圾回收 + 循环引用检测）
   https://docs.python.org/3/library/gc.html
6. Higham 2002 Accuracy and Stability of Numerical Algorithms 2nd SIAM
   （float32 vs float64 累积误差分析）https://doi.org/10.1137/1.9780898718027
7. McKinney 2017 Python for Data Analysis 2nd O'Reilly（流式处理）
"""R886-R900 内存优化模块（纯 NumPy/SciPy CPU，R04 兼容）。

面向 PoLaRIS 仿真大数组场景（FDTD 时序场、S 参数频扫矩阵、密度场
多分辨率金字塔），提供内存优化原语，覆盖 R886-R900 共 15 轮：

- R886 generator 流式产出（替代 list 一次性物化）
- R887 np.memmap 外存大数组（>内存容量时磁盘映射）
- R888 大对象 del + gc.collect 显式释放
- R889 分块处理 chunked_map（O(N) 内存处理 O(N) 数据）
- R890 峰值内存测量 memory_probe（context manager）
- R891 数组 dtype 降精度（float64→float32，精度可控场景）
- R892 视图替代切片复制（stride_tricks零拷贝）
- R893 稀疏替代密集（CSR 节省 ~95%）
- R894 流式归约 streaming_reduce（不物化中间数组）
- R895 释放回调 release_after（with 块结束自动 del+gc）
- R896-R900 综合内存工具集 facade MemoryOptimizerKit

## 设计原则

1. 内存优先：能流式不物化，能 memmap 不全载入，能稀疏不密集
2. 显式释放：大对象用完即 del + gc.collect，不依赖 GC 时机
3. dtype 适配：存储用 float32，计算用 float64（避免累积误差）
4. 零拷贝视图：stride_tricks 提供窗口视图，不复制数据

## R04 战略（不可撤销）

🚫不参与 GPU：纯 NumPy/SciPy。无 CuPy/CUDA/ROCm/AppleMetal。

## R03 禁止 fall-back

业务错误一律 raise。memmap 文件创建失败、dtype 非法、shape 非法
均 raise，无 except: pass / return None / return []。

## 学术依据（R02，≥5 个文献 URL）

1. Harris et al. 2020 Array programming with NumPy Nature 585 357-362
   https://doi.org/10.1038/s41586-020-2649-2
2. NumPy memmap 官方文档（内存映射文件，out-of-core 计算）
   https://numpy.org/doc/stable/reference/generated/numpy.memmap.html
3. Virtanen et al. 2020 SciPy 1.0 Nature Methods 17 261-272
   https://doi.org/10.1038/s41592-019-0686-2
4. Dask chunked arrays 文档（分块数组 out-of-core 范式）
   https://docs.dask.org/en/stable/array.html
5. Python gc 模块文档（显式垃圾回收 + 循环引用检测）
   https://docs.python.org/3/library/gc.html
6. Higham 2002 Accuracy and Stability of Numerical Algorithms 2nd SIAM
   （float32 vs float64 累积误差分析）https://doi.org/10.1137/1.9780898718027
7. McKinney 2017 Python for Data Analysis 2nd O'Reilly（流式处理）
   https://wesmckinney.com/book/
8. Van Rossum & Drake 2024 Python Language Reference §3 Data model
   （del 与引用计数）https://docs.python"""R886-R900 内存优化模块（纯 NumPy/SciPy CPU，R04 兼容）。

面向 PoLaRIS 仿真大数组场景（FDTD 时序场、S 参数频扫矩阵、密度场
多分辨率金字塔），提供内存优化原语，覆盖 R886-R900 共 15 轮：

- R886 generator 流式产出（替代 list 一次性物化）
- R887 np.memmap 外存大数组（>内存容量时磁盘映射）
- R888 大对象 del + gc.collect 显式释放
- R889 分块处理 chunked_map（O(N) 内存处理 O(N) 数据）
- R890 峰值内存测量 memory_probe（context manager）
- R891 数组 dtype 降精度（float64→float32，精度可控场景）
- R892 视图替代切片复制（stride_tricks零拷贝）
- R893 稀疏替代密集（CSR 节省 ~95%）
- R894 流式归约 streaming_reduce（不物化中间数组）
- R895 释放回调 release_after（with 块结束自动 del+gc）
- R896-R900 综合内存工具集 facade MemoryOptimizerKit

## 设计原则

1. 内存优先：能流式不物化，能 memmap 不全载入，能稀疏不密集
2. 显式释放：大对象用完即 del + gc.collect，不依赖 GC 时机
3. dtype 适配：存储用 float32，计算用 float64（避免累积误差）
4. 零拷贝视图：stride_tricks 提供窗口视图，不复制数据

## R04 战略（不可撤销）

🚫不参与 GPU：纯 NumPy/SciPy。无 CuPy/CUDA/ROCm/AppleMetal。

## R03 禁止 fall-back

业务错误一律 raise。memmap 文件创建失败、dtype 非法、shape 非法
均 raise，无 except: pass / return None / return []。

## 学术依据（R02，≥5 个文献 URL）

1. Harris et al. 2020 Array programming with NumPy Nature 585 357-362
   https://doi.org/10.1038/s41586-020-2649-2
2. NumPy memmap 官方文档（内存映射文件，out-of-core 计算）
   https://numpy.org/doc/stable/reference/generated/numpy.memmap.html
3. Virtanen et al. 2020 SciPy 1.0 Nature Methods 17 261-272
   https://doi.org/10.1038/s41592-019-0686-2
4. Dask chunked arrays 文档（分块数组 out-of-core 范式）
   https://docs.dask.org/en/stable/array.html
5. Python gc 模块文档（显式垃圾回收 + 循环引用检测）
   https://docs.python.org/3/library/gc.html
6. Higham 2002 Accuracy and Stability of Numerical Algorithms 2nd SIAM
   （float32 vs float64 累积误差分析）https://doi.org/10.1137/1.9780898718027
7. McKinney 2017 Python for Data Analysis 2nd O'Reilly（流式处理）
   https://wesmckinney.com/book/
8. Van Rossum & Drake 2024 Python Language Reference §3 Data model
   （del 与引用计数）https://docs.python.org/3/reference/datamodel.html
9. SciPy scipy.sparse 稀疏矩阵内存优势"""R886-R900 内存优化模块（纯 NumPy/SciPy CPU，R04 兼容）。

面向 PoLaRIS 仿真大数组场景（FDTD 时序场、S 参数频扫矩阵、密度场
多分辨率金字塔），提供内存优化原语，覆盖 R886-R900 共 15 轮：

- R886 generator 流式产出（替代 list 一次性物化）
- R887 np.memmap 外存大数组（>内存容量时磁盘映射）
- R888 大对象 del + gc.collect 显式释放
- R889 分块处理 chunked_map（O(N) 内存处理 O(N) 数据）
- R890 峰值内存测量 memory_probe（context manager）
- R891 数组 dtype 降精度（float64→float32，精度可控场景）
- R892 视图替代切片复制（stride_tricks零拷贝）
- R893 稀疏替代密集（CSR 节省 ~95%）
- R894 流式归约 streaming_reduce（不物化中间数组）
- R895 释放回调 release_after（with 块结束自动 del+gc）
- R896-R900 综合内存工具集 facade MemoryOptimizerKit

## 设计原则

1. 内存优先：能流式不物化，能 memmap 不全载入，能稀疏不密集
2. 显式释放：大对象用完即 del + gc.collect，不依赖 GC 时机
3. dtype 适配：存储用 float32，计算用 float64（避免累积误差）
4. 零拷贝视图：stride_tricks 提供窗口视图，不复制数据

## R04 战略（不可撤销）

🚫不参与 GPU：纯 NumPy/SciPy。无 CuPy/CUDA/ROCm/AppleMetal。

## R03 禁止 fall-back

业务错误一律 raise。memmap 文件创建失败、dtype 非法、shape 非法
均 raise，无 except: pass / return None / return []。

## 学术依据（R02，≥5 个文献 URL）

1. Harris et al. 2020 Array programming with NumPy Nature 585 357-362
   https://doi.org/10.1038/s41586-020-2649-2
2. NumPy memmap 官方文档（内存映射文件，out-of-core 计算）
   https://numpy.org/doc/stable/reference/generated/numpy.memmap.html
3. Virtanen et al. 2020 SciPy 1.0 Nature Methods 17 261-272
   https://doi.org/10.1038/s41592-019-0686-2
4. Dask chunked arrays 文档（分块数组 out-of-core 范式）
   https://docs.dask.org/en/stable/array.html
5. Python gc 模块文档（显式垃圾回收 + 循环引用检测）
   https://docs.python.org/3/library/gc.html
6. Higham 2002 Accuracy and Stability of Numerical Algorithms 2nd SIAM
   （float32 vs float64 累积误差分析）https://doi.org/10.1137/1.9780898718027
7. McKinney 2017 Python for Data Analysis 2nd O'Reilly（流式处理）
   https://wesmckinney.com/book/
8. Van Rossum & Drake 2024 Python Language Reference §3 Data model
   （del 与引用计数）https://docs.python.org/3/reference/datamodel.html
9. SciPy scipy.sparse 稀疏矩阵内存优势（CSR 格式）
   https://docs.sc"""R886-R900 内存优化模块（纯 NumPy/SciPy CPU，R04 兼容）。

面向 PoLaRIS 仿真大数组场景（FDTD 时序场、S 参数频扫矩阵、密度场
多分辨率金字塔），提供内存优化原语，覆盖 R886-R900 共 15 轮：

- R886 generator 流式产出（替代 list 一次性物化）
- R887 np.memmap 外存大数组（>内存容量时磁盘映射）
- R888 大对象 del + gc.collect 显式释放
- R889 分块处理 chunked_map（O(N) 内存处理 O(N) 数据）
- R890 峰值内存测量 memory_probe（context manager）
- R891 数组 dtype 降精度（float64→float32，精度可控场景）
- R892 视图替代切片复制（stride_tricks零拷贝）
- R893 稀疏替代密集（CSR 节省 ~95%）
- R894 流式归约 streaming_reduce（不物化中间数组）
- R895 释放回调 release_after（with 块结束自动 del+gc）
- R896-R900 综合内存工具集 facade MemoryOptimizerKit

## 设计原则

1. 内存优先：能流式不物化，能 memmap 不全载入，能稀疏不密集
2. 显式释放：大对象用完即 del + gc.collect，不依赖 GC 时机
3. dtype 适配：存储用 float32，计算用 float64（避免累积误差）
4. 零拷贝视图：stride_tricks 提供窗口视图，不复制数据

## R04 战略（不可撤销）

🚫不参与 GPU：纯 NumPy/SciPy。无 CuPy/CUDA/ROCm/AppleMetal。

## R03 禁止 fall-back

业务错误一律 raise。memmap 文件创建失败、dtype 非法、shape 非法
均 raise，无 except: pass / return None / return []。

## 学术依据（R02，≥5 个文献 URL）

1. Harris et al. 2020 Array programming with NumPy Nature 585 357-362
   https://doi.org/10.1038/s41586-020-2649-2
2. NumPy memmap 官方文档（内存映射文件，out-of-core 计算）
   https://numpy.org/doc/stable/reference/generated/numpy.memmap.html
3. Virtanen et al. 2020 SciPy 1.0 Nature Methods 17 261-272
   https://doi.org/10.1038/s41592-019-0686-2
4. Dask chunked arrays 文档（分块数组 out-of-core 范式）
   https://docs.dask.org/en/stable/array.html
5. Python gc 模块文档（显式垃圾回收 + 循环引用检测）
   https://docs.python.org/3/library/gc.html
6. Higham 2002 Accuracy and Stability of Numerical Algorithms 2nd SIAM
   （float32 vs float64 累积误差分析）https://doi.org/10.1137/1.9780898718027
7. McKinney 2017 Python for Data Analysis 2nd O'Reilly（流式处理）
   https://wesmckinney.com/book/
8. Van Rossum & Drake 2024 Python Language Reference §3 Data model
   （del 与引用计数）https://docs.python.org/3/reference/datamodel.html
9. SciPy scipy.sparse 稀疏矩阵内存优势（CSR 格式）
   https://docs.scipy.org/doc/scipy/reference/sparse.html
10. Apache Arrow memory management（zero-copy 流"""R886-R900 内存优化模块（纯 NumPy/SciPy CPU，R04 兼容）。

面向 PoLaRIS 仿真大数组场景（FDTD 时序场、S 参数频扫矩阵、密度场
多分辨率金字塔），提供内存优化原语，覆盖 R886-R900 共 15 轮：

- R886 generator 流式产出（替代 list 一次性物化）
- R887 np.memmap 外存大数组（>内存容量时磁盘映射）
- R888 大对象 del + gc.collect 显式释放
- R889 分块处理 chunked_map（O(N) 内存处理 O(N) 数据）
- R890 峰值内存测量 memory_probe（context manager）
- R891 数组 dtype 降精度（float64→float32，精度可控场景）
- R892 视图替代切片复制（stride_tricks零拷贝）
- R893 稀疏替代密集（CSR 节省 ~95%）
- R894 流式归约 streaming_reduce（不物化中间数组）
- R895 释放回调 release_after（with 块结束自动 del+gc）
- R896-R900 综合内存工具集 facade MemoryOptimizerKit

## 设计原则

1. 内存优先：能流式不物化，能 memmap 不全载入，能稀疏不密集
2. 显式释放：大对象用完即 del + gc.collect，不依赖 GC 时机
3. dtype 适配：存储用 float32，计算用 float64（避免累积误差）
4. 零拷贝视图：stride_tricks 提供窗口视图，不复制数据

## R04 战略（不可撤销）

🚫不参与 GPU：纯 NumPy/SciPy。无 CuPy/CUDA/ROCm/AppleMetal。

## R03 禁止 fall-back

业务错误一律 raise。memmap 文件创建失败、dtype 非法、shape 非法
均 raise，无 except: pass / return None / return []。

## 学术依据（R02，≥5 个文献 URL）

1. Harris et al. 2020 Array programming with NumPy Nature 585 357-362
   https://doi.org/10.1038/s41586-020-2649-2
2. NumPy memmap 官方文档（内存映射文件，out-of-core 计算）
   https://numpy.org/doc/stable/reference/generated/numpy.memmap.html
3. Virtanen et al. 2020 SciPy 1.0 Nature Methods 17 261-272
   https://doi.org/10.1038/s41592-019-0686-2
4. Dask chunked arrays 文档（分块数组 out-of-core 范式）
   https://docs.dask.org/en/stable/array.html
5. Python gc 模块文档（显式垃圾回收 + 循环引用检测）
   https://docs.python.org/3/library/gc.html
6. Higham 2002 Accuracy and Stability of Numerical Algorithms 2nd SIAM
   （float32 vs float64 累积误差分析）https://doi.org/10.1137/1.9780898718027
7. McKinney 2017 Python for Data Analysis 2nd O'Reilly（流式处理）
   https://wesmckinney.com/book/
8. Van Rossum & Drake 2024 Python Language Reference §3 Data model
   （del 与引用计数）https://docs.python.org/3/reference/datamodel.html
9. SciPy scipy.sparse 稀疏矩阵内存优势（CSR 格式）
   https://docs.scipy.org/doc/scipy/reference/sparse.html
10. Apache Arrow memory management（zero-copy 流式处理参考）
    https://arrow.apache.org"""R886-R900 内存优化模块（纯 NumPy/SciPy CPU，R04 兼容）。

面向 PoLaRIS 仿真大数组场景（FDTD 时序场、S 参数频扫矩阵、密度场
多分辨率金字塔），提供内存优化原语，覆盖 R886-R900 共 15 轮：

- R886 generator 流式产出（替代 list 一次性物化）
- R887 np.memmap 外存大数组（>内存容量时磁盘映射）
- R888 大对象 del + gc.collect 显式释放
- R889 分块处理 chunked_map（O(N) 内存处理 O(N) 数据）
- R890 峰值内存测量 memory_probe（context manager）
- R891 数组 dtype 降精度（float64→float32，精度可控场景）
- R892 视图替代切片复制（stride_tricks零拷贝）
- R893 稀疏替代密集（CSR 节省 ~95%）
- R894 流式归约 streaming_reduce（不物化中间数组）
- R895 释放回调 release_after（with 块结束自动 del+gc）
- R896-R900 综合内存工具集 facade MemoryOptimizerKit

## 设计原则

1. 内存优先：能流式不物化，能 memmap 不全载入，能稀疏不密集
2. 显式释放：大对象用完即 del + gc.collect，不依赖 GC 时机
3. dtype 适配：存储用 float32，计算用 float64（避免累积误差）
4. 零拷贝视图：stride_tricks 提供窗口视图，不复制数据

## R04 战略（不可撤销）

🚫不参与 GPU：纯 NumPy/SciPy。无 CuPy/CUDA/ROCm/AppleMetal。

## R03 禁止 fall-back

业务错误一律 raise。memmap 文件创建失败、dtype 非法、shape 非法
均 raise，无 except: pass / return None / return []。

## 学术依据（R02，≥5 个文献 URL）

1. Harris et al. 2020 Array programming with NumPy Nature 585 357-362
   https://doi.org/10.1038/s41586-020-2649-2
2. NumPy memmap 官方文档（内存映射文件，out-of-core 计算）
   https://numpy.org/doc/stable/reference/generated/numpy.memmap.html
3. Virtanen et al. 2020 SciPy 1.0 Nature Methods 17 261-272
   https://doi.org/10.1038/s41592-019-0686-2
4. Dask chunked arrays 文档（分块数组 out-of-core 范式）
   https://docs.dask.org/en/stable/array.html
5. Python gc 模块文档（显式垃圾回收 + 循环引用检测）
   https://docs.python.org/3/library/gc.html
6. Higham 2002 Accuracy and Stability of Numerical Algorithms 2nd SIAM
   （float32 vs float64 累积误差分析）https://doi.org/10.1137/1.9780898718027
7. McKinney 2017 Python for Data Analysis 2nd O'Reilly（流式处理）
   https://wesmckinney.com/book/
8. Van Rossum & Drake 2024 Python Language Reference §3 Data model
   （del 与引用计数）https://docs.python.org/3/reference/datamodel.html
9. SciPy scipy.sparse 稀疏矩阵内存优势（CSR 格式）
   https://docs.scipy.org/doc/scipy/reference/sparse.html
10. Apache Arrow memory management（zero-copy 流式处理参考）
    https://arrow.apache.org/docs/python/memory.html

## *创新* 标注（R02）

- *创新* R887：`MemmapArray`"""R886-R900 内存优化模块（纯 NumPy/SciPy CPU，R04 兼容）。

面向 PoLaRIS 仿真大数组场景（FDTD 时序场、S 参数频扫矩阵、密度场
多分辨率金字塔），提供内存优化原语，覆盖 R886-R900 共 15 轮：

- R886 generator 流式产出（替代 list 一次性物化）
- R887 np.memmap 外存大数组（>内存容量时磁盘映射）
- R888 大对象 del + gc.collect 显式释放
- R889 分块处理 chunked_map（O(N) 内存处理 O(N) 数据）
- R890 峰值内存测量 memory_probe（context manager）
- R891 数组 dtype 降精度（float64→float32，精度可控场景）
- R892 视图替代切片复制（stride_tricks零拷贝）
- R893 稀疏替代密集（CSR 节省 ~95%）
- R894 流式归约 streaming_reduce（不物化中间数组）
- R895 释放回调 release_after（with 块结束自动 del+gc）
- R896-R900 综合内存工具集 facade MemoryOptimizerKit

## 设计原则

1. 内存优先：能流式不物化，能 memmap 不全载入，能稀疏不密集
2. 显式释放：大对象用完即 del + gc.collect，不依赖 GC 时机
3. dtype 适配：存储用 float32，计算用 float64（避免累积误差）
4. 零拷贝视图：stride_tricks 提供窗口视图，不复制数据

## R04 战略（不可撤销）

🚫不参与 GPU：纯 NumPy/SciPy。无 CuPy/CUDA/ROCm/AppleMetal。

## R03 禁止 fall-back

业务错误一律 raise。memmap 文件创建失败、dtype 非法、shape 非法
均 raise，无 except: pass / return None / return []。

## 学术依据（R02，≥5 个文献 URL）

1. Harris et al. 2020 Array programming with NumPy Nature 585 357-362
   https://doi.org/10.1038/s41586-020-2649-2
2. NumPy memmap 官方文档（内存映射文件，out-of-core 计算）
   https://numpy.org/doc/stable/reference/generated/numpy.memmap.html
3. Virtanen et al. 2020 SciPy 1.0 Nature Methods 17 261-272
   https://doi.org/10.1038/s41592-019-0686-2
4. Dask chunked arrays 文档（分块数组 out-of-core 范式）
   https://docs.dask.org/en/stable/array.html
5. Python gc 模块文档（显式垃圾回收 + 循环引用检测）
   https://docs.python.org/3/library/gc.html
6. Higham 2002 Accuracy and Stability of Numerical Algorithms 2nd SIAM
   （float32 vs float64 累积误差分析）https://doi.org/10.1137/1.9780898718027
7. McKinney 2017 Python for Data Analysis 2nd O'Reilly（流式处理）
   https://wesmckinney.com/book/
8. Van Rossum & Drake 2024 Python Language Reference §3 Data model
   （del 与引用计数）https://docs.python.org/3/reference/datamodel.html
9. SciPy scipy.sparse 稀疏矩阵内存优势（CSR 格式）
   https://docs.scipy.org/doc/scipy/reference/sparse.html
10. Apache Arrow memory management（zero-copy 流式处理参考）
    https://arrow.apache.org/docs/python/memory.html

## *创新* 标注（R02）

- *创新* R887：`MemmapArray` 上下文管理器封装 np.memmap，with"""R886-R900 内存优化模块（纯 NumPy/SciPy CPU，R04 兼容）。

面向 PoLaRIS 仿真大数组场景（FDTD 时序场、S 参数频扫矩阵、密度场
多分辨率金字塔），提供内存优化原语，覆盖 R886-R900 共 15 轮：

- R886 generator 流式产出（替代 list 一次性物化）
- R887 np.memmap 外存大数组（>内存容量时磁盘映射）
- R888 大对象 del + gc.collect 显式释放
- R889 分块处理 chunked_map（O(N) 内存处理 O(N) 数据）
- R890 峰值内存测量 memory_probe（context manager）
- R891 数组 dtype 降精度（float64→float32，精度可控场景）
- R892 视图替代切片复制（stride_tricks零拷贝）
- R893 稀疏替代密集（CSR 节省 ~95%）
- R894 流式归约 streaming_reduce（不物化中间数组）
- R895 释放回调 release_after（with 块结束自动 del+gc）
- R896-R900 综合内存工具集 facade MemoryOptimizerKit

## 设计原则

1. 内存优先：能流式不物化，能 memmap 不全载入，能稀疏不密集
2. 显式释放：大对象用完即 del + gc.collect，不依赖 GC 时机
3. dtype 适配：存储用 float32，计算用 float64（避免累积误差）
4. 零拷贝视图：stride_tricks 提供窗口视图，不复制数据

## R04 战略（不可撤销）

🚫不参与 GPU：纯 NumPy/SciPy。无 CuPy/CUDA/ROCm/AppleMetal。

## R03 禁止 fall-back

业务错误一律 raise。memmap 文件创建失败、dtype 非法、shape 非法
均 raise，无 except: pass / return None / return []。

## 学术依据（R02，≥5 个文献 URL）

1. Harris et al. 2020 Array programming with NumPy Nature 585 357-362
   https://doi.org/10.1038/s41586-020-2649-2
2. NumPy memmap 官方文档（内存映射文件，out-of-core 计算）
   https://numpy.org/doc/stable/reference/generated/numpy.memmap.html
3. Virtanen et al. 2020 SciPy 1.0 Nature Methods 17 261-272
   https://doi.org/10.1038/s41592-019-0686-2
4. Dask chunked arrays 文档（分块数组 out-of-core 范式）
   https://docs.dask.org/en/stable/array.html
5. Python gc 模块文档（显式垃圾回收 + 循环引用检测）
   https://docs.python.org/3/library/gc.html
6. Higham 2002 Accuracy and Stability of Numerical Algorithms 2nd SIAM
   （float32 vs float64 累积误差分析）https://doi.org/10.1137/1.9780898718027
7. McKinney 2017 Python for Data Analysis 2nd O'Reilly（流式处理）
   https://wesmckinney.com/book/
8. Van Rossum & Drake 2024 Python Language Reference §3 Data model
   （del 与引用计数）https://docs.python.org/3/reference/datamodel.html
9. SciPy scipy.sparse 稀疏矩阵内存优势（CSR 格式）
   https://docs.scipy.org/doc/scipy/reference/sparse.html
10. Apache Arrow memory management（zero-copy 流式处理参考）
    https://arrow.apache.org/docs/python/memory.html

## *创新* 标注（R02）

- *创新* R887：`MemmapArray` 上下文管理器封装 np.memmap，with 块
  结束自动 flush + close + del，避免忘记释放导致文件句柄泄漏。
  底层逻辑：np.mem"""R886-R900 内存优化模块（纯 NumPy/SciPy CPU，R04 兼容）。

面向 PoLaRIS 仿真大数组场景（FDTD 时序场、S 参数频扫矩阵、密度场
多分辨率金字塔），提供内存优化原语，覆盖 R886-R900 共 15 轮：

- R886 generator 流式产出（替代 list 一次性物化）
- R887 np.memmap 外存大数组（>内存容量时磁盘映射）
- R888 大对象 del + gc.collect 显式释放
- R889 分块处理 chunked_map（O(N) 内存处理 O(N) 数据）
- R890 峰值内存测量 memory_probe（context manager）
- R891 数组 dtype 降精度（float64→float32，精度可控场景）
- R892 视图替代切片复制（stride_tricks零拷贝）
- R893 稀疏替代密集（CSR 节省 ~95%）
- R894 流式归约 streaming_reduce（不物化中间数组）
- R895 释放回调 release_after（with 块结束自动 del+gc）
- R896-R900 综合内存工具集 facade MemoryOptimizerKit

## 设计原则

1. 内存优先：能流式不物化，能 memmap 不全载入，能稀疏不密集
2. 显式释放：大对象用完即 del + gc.collect，不依赖 GC 时机
3. dtype 适配：存储用 float32，计算用 float64（避免累积误差）
4. 零拷贝视图：stride_tricks 提供窗口视图，不复制数据

## R04 战略（不可撤销）

🚫不参与 GPU：纯 NumPy/SciPy。无 CuPy/CUDA/ROCm/AppleMetal。

## R03 禁止 fall-back

业务错误一律 raise。memmap 文件创建失败、dtype 非法、shape 非法
均 raise，无 except: pass / return None / return []。

## 学术依据（R02，≥5 个文献 URL）

1. Harris et al. 2020 Array programming with NumPy Nature 585 357-362
   https://doi.org/10.1038/s41586-020-2649-2
2. NumPy memmap 官方文档（内存映射文件，out-of-core 计算）
   https://numpy.org/doc/stable/reference/generated/numpy.memmap.html
3. Virtanen et al. 2020 SciPy 1.0 Nature Methods 17 261-272
   https://doi.org/10.1038/s41592-019-0686-2
4. Dask chunked arrays 文档（分块数组 out-of-core 范式）
   https://docs.dask.org/en/stable/array.html
5. Python gc 模块文档（显式垃圾回收 + 循环引用检测）
   https://docs.python.org/3/library/gc.html
6. Higham 2002 Accuracy and Stability of Numerical Algorithms 2nd SIAM
   （float32 vs float64 累积误差分析）https://doi.org/10.1137/1.9780898718027
7. McKinney 2017 Python for Data Analysis 2nd O'Reilly（流式处理）
   https://wesmckinney.com/book/
8. Van Rossum & Drake 2024 Python Language Reference §3 Data model
   （del 与引用计数）https://docs.python.org/3/reference/datamodel.html
9. SciPy scipy.sparse 稀疏矩阵内存优势（CSR 格式）
   https://docs.scipy.org/doc/scipy/reference/sparse.html
10. Apache Arrow memory management（zero-copy 流式处理参考）
    https://arrow.apache.org/docs/python/memory.html

## *创新* 标注（R02）

- *创新* R887：`MemmapArray` 上下文管理器封装 np.memmap，with 块
  结束自动 flush + close + del，避免忘记释放导致文件句柄泄漏。
  底层逻辑：np.memmap 本质是 mmap.mmap + ndarray 视图，显式 close
  释放映射，del 触发 __del__；支持理论：NumPy memmap 文档 + Python
  数据模型 §3；案例："""R886-R900 内存优化模块（纯 NumPy/SciPy CPU，R04 兼容）。

面向 PoLaRIS 仿真大数组场景（FDTD 时序场、S 参数频扫矩阵、密度场
多分辨率金字塔），提供内存优化原语，覆盖 R886-R900 共 15 轮：

- R886 generator 流式产出（替代 list 一次性物化）
- R887 np.memmap 外存大数组（>内存容量时磁盘映射）
- R888 大对象 del + gc.collect 显式释放
- R889 分块处理 chunked_map（O(N) 内存处理 O(N) 数据）
- R890 峰值内存测量 memory_probe（context manager）
- R891 数组 dtype 降精度（float64→float32，精度可控场景）
- R892 视图替代切片复制（stride_tricks零拷贝）
- R893 稀疏替代密集（CSR 节省 ~95%）
- R894 流式归约 streaming_reduce（不物化中间数组）
- R895 释放回调 release_after（with 块结束自动 del+gc）
- R896-R900 综合内存工具集 facade MemoryOptimizerKit

## 设计原则

1. 内存优先：能流式不物化，能 memmap 不全载入，能稀疏不密集
2. 显式释放：大对象用完即 del + gc.collect，不依赖 GC 时机
3. dtype 适配：存储用 float32，计算用 float64（避免累积误差）
4. 零拷贝视图：stride_tricks 提供窗口视图，不复制数据

## R04 战略（不可撤销）

🚫不参与 GPU：纯 NumPy/SciPy。无 CuPy/CUDA/ROCm/AppleMetal。

## R03 禁止 fall-back

业务错误一律 raise。memmap 文件创建失败、dtype 非法、shape 非法
均 raise，无 except: pass / return None / return []。

## 学术依据（R02，≥5 个文献 URL）

1. Harris et al. 2020 Array programming with NumPy Nature 585 357-362
   https://doi.org/10.1038/s41586-020-2649-2
2. NumPy memmap 官方文档（内存映射文件，out-of-core 计算）
   https://numpy.org/doc/stable/reference/generated/numpy.memmap.html
3. Virtanen et al. 2020 SciPy 1.0 Nature Methods 17 261-272
   https://doi.org/10.1038/s41592-019-0686-2
4. Dask chunked arrays 文档（分块数组 out-of-core 范式）
   https://docs.dask.org/en/stable/array.html
5. Python gc 模块文档（显式垃圾回收 + 循环引用检测）
   https://docs.python.org/3/library/gc.html
6. Higham 2002 Accuracy and Stability of Numerical Algorithms 2nd SIAM
   （float32 vs float64 累积误差分析）https://doi.org/10.1137/1.9780898718027
7. McKinney 2017 Python for Data Analysis 2nd O'Reilly（流式处理）
   https://wesmckinney.com/book/
8. Van Rossum & Drake 2024 Python Language Reference §3 Data model
   （del 与引用计数）https://docs.python.org/3/reference/datamodel.html
9. SciPy scipy.sparse 稀疏矩阵内存优势（CSR 格式）
   https://docs.scipy.org/doc/scipy/reference/sparse.html
10. Apache Arrow memory management（zero-copy 流式处理参考）
    https://arrow.apache.org/docs/python/memory.html

## *创新* 标注（R02）

- *创新* R887：`MemmapArray` 上下文管理器封装 np.memmap，with 块
  结束自动 flush + close + del，避免忘记释放导致文件句柄泄漏。
  底层逻辑：np.memmap 本质是 mmap.mmap + ndarray 视图，显式 close
  释放映射，del 触发 __del__；支持理论：NumPy memmap 文档 + Python
  数据模型 §3；案例：1GB S 参数矩阵磁盘映射，峰值内存"""R886-R900 内存优化模块（纯 NumPy/SciPy CPU，R04 兼容）。

面向 PoLaRIS 仿真大数组场景（FDTD 时序场、S 参数频扫矩阵、密度场
多分辨率金字塔），提供内存优化原语，覆盖 R886-R900 共 15 轮：

- R886 generator 流式产出（替代 list 一次性物化）
- R887 np.memmap 外存大数组（>内存容量时磁盘映射）
- R888 大对象 del + gc.collect 显式释放
- R889 分块处理 chunked_map（O(N) 内存处理 O(N) 数据）
- R890 峰值内存测量 memory_probe（context manager）
- R891 数组 dtype 降精度（float64→float32，精度可控场景）
- R892 视图替代切片复制（stride_tricks零拷贝）
- R893 稀疏替代密集（CSR 节省 ~95%）
- R894 流式归约 streaming_reduce（不物化中间数组）
- R895 释放回调 release_after（with 块结束自动 del+gc）
- R896-R900 综合内存工具集 facade MemoryOptimizerKit

## 设计原则

1. 内存优先：能流式不物化，能 memmap 不全载入，能稀疏不密集
2. 显式释放：大对象用完即 del + gc.collect，不依赖 GC 时机
3. dtype 适配：存储用 float32，计算用 float64（避免累积误差）
4. 零拷贝视图：stride_tricks 提供窗口视图，不复制数据

## R04 战略（不可撤销）

🚫不参与 GPU：纯 NumPy/SciPy。无 CuPy/CUDA/ROCm/AppleMetal。

## R03 禁止 fall-back

业务错误一律 raise。memmap 文件创建失败、dtype 非法、shape 非法
均 raise，无 except: pass / return None / return []。

## 学术依据（R02，≥5 个文献 URL）

1. Harris et al. 2020 Array programming with NumPy Nature 585 357-362
   https://doi.org/10.1038/s41586-020-2649-2
2. NumPy memmap 官方文档（内存映射文件，out-of-core 计算）
   https://numpy.org/doc/stable/reference/generated/numpy.memmap.html
3. Virtanen et al. 2020 SciPy 1.0 Nature Methods 17 261-272
   https://doi.org/10.1038/s41592-019-0686-2
4. Dask chunked arrays 文档（分块数组 out-of-core 范式）
   https://docs.dask.org/en/stable/array.html
5. Python gc 模块文档（显式垃圾回收 + 循环引用检测）
   https://docs.python.org/3/library/gc.html
6. Higham 2002 Accuracy and Stability of Numerical Algorithms 2nd SIAM
   （float32 vs float64 累积误差分析）https://doi.org/10.1137/1.9780898718027
7. McKinney 2017 Python for Data Analysis 2nd O'Reilly（流式处理）
   https://wesmckinney.com/book/
8. Van Rossum & Drake 2024 Python Language Reference §3 Data model
   （del 与引用计数）https://docs.python.org/3/reference/datamodel.html
9. SciPy scipy.sparse 稀疏矩阵内存优势（CSR 格式）
   https://docs.scipy.org/doc/scipy/reference/sparse.html
10. Apache Arrow memory management（zero-copy 流式处理参考）
    https://arrow.apache.org/docs/python/memory.html

## *创新* 标注（R02）

- *创新* R887：`MemmapArray` 上下文管理器封装 np.memmap，with 块
  结束自动 flush + close + del，避免忘记释放导致文件句柄泄漏。
  底层逻辑：np.memmap 本质是 mmap.mmap + ndarray 视图，显式 close
  释放映射，del 触发 __del__；支持理论：NumPy memmap 文档 + Python
  数据模型 §3；案例：1GB S 参数矩阵磁盘映射，峰值内存 <100MB。
- *创新* R890：`memory_probe` 用 tracemalloc 测量 with 块内峰值内存，
  返回 peak_bytes/current_bytes，量化内存"""R886-R900 内存优化模块（纯 NumPy/SciPy CPU，R04 兼容）。

面向 PoLaRIS 仿真大数组场景（FDTD 时序场、S 参数频扫矩阵、密度场
多分辨率金字塔），提供内存优化原语，覆盖 R886-R900 共 15 轮：

- R886 generator 流式产出（替代 list 一次性物化）
- R887 np.memmap 外存大数组（>内存容量时磁盘映射）
- R888 大对象 del + gc.collect 显式释放
- R889 分块处理 chunked_map（O(N) 内存处理 O(N) 数据）
- R890 峰值内存测量 memory_probe（context manager）
- R891 数组 dtype 降精度（float64→float32，精度可控场景）
- R892 视图替代切片复制（stride_tricks零拷贝）
- R893 稀疏替代密集（CSR 节省 ~95%）
- R894 流式归约 streaming_reduce（不物化中间数组）
- R895 释放回调 release_after（with 块结束自动 del+gc）
- R896-R900 综合内存工具集 facade MemoryOptimizerKit

## 设计原则

1. 内存优先：能流式不物化，能 memmap 不全载入，能稀疏不密集
2. 显式释放：大对象用完即 del + gc.collect，不依赖 GC 时机
3. dtype 适配：存储用 float32，计算用 float64（避免累积误差）
4. 零拷贝视图：stride_tricks 提供窗口视图，不复制数据

## R04 战略（不可撤销）

🚫不参与 GPU：纯 NumPy/SciPy。无 CuPy/CUDA/ROCm/AppleMetal。

## R03 禁止 fall-back

业务错误一律 raise。memmap 文件创建失败、dtype 非法、shape 非法
均 raise，无 except: pass / return None / return []。

## 学术依据（R02，≥5 个文献 URL）

1. Harris et al. 2020 Array programming with NumPy Nature 585 357-362
   https://doi.org/10.1038/s41586-020-2649-2
2. NumPy memmap 官方文档（内存映射文件，out-of-core 计算）
   https://numpy.org/doc/stable/reference/generated/numpy.memmap.html
3. Virtanen et al. 2020 SciPy 1.0 Nature Methods 17 261-272
   https://doi.org/10.1038/s41592-019-0686-2
4. Dask chunked arrays 文档（分块数组 out-of-core 范式）
   https://docs.dask.org/en/stable/array.html
5. Python gc 模块文档（显式垃圾回收 + 循环引用检测）
   https://docs.python.org/3/library/gc.html
6. Higham 2002 Accuracy and Stability of Numerical Algorithms 2nd SIAM
   （float32 vs float64 累积误差分析）https://doi.org/10.1137/1.9780898718027
7. McKinney 2017 Python for Data Analysis 2nd O'Reilly（流式处理）
   https://wesmckinney.com/book/
8. Van Rossum & Drake 2024 Python Language Reference §3 Data model
   （del 与引用计数）https://docs.python.org/3/reference/datamodel.html
9. SciPy scipy.sparse 稀疏矩阵内存优势（CSR 格式）
   https://docs.scipy.org/doc/scipy/reference/sparse.html
10. Apache Arrow memory management（zero-copy 流式处理参考）
    https://arrow.apache.org/docs/python/memory.html

## *创新* 标注（R02）

- *创新* R887：`MemmapArray` 上下文管理器封装 np.memmap，with 块
  结束自动 flush + close + del，避免忘记释放导致文件句柄泄漏。
  底层逻辑：np.memmap 本质是 mmap.mmap + ndarray 视图，显式 close
  释放映射，del 触发 __del__；支持理论：NumPy memmap 文档 + Python
  数据模型 §3；案例：1GB S 参数矩阵磁盘映射，峰值内存 <100MB。
- *创新* R890：`memory_probe` 用 tracemalloc 测量 with 块内峰值内存，
  返回 peak_bytes/current_bytes，量化内存优化效果。底层逻辑：
  tracemalloc 跟踪 Python 分配器，peak 反"""R886-R900 内存优化模块（纯 NumPy/SciPy CPU，R04 兼容）。

面向 PoLaRIS 仿真大数组场景（FDTD 时序场、S 参数频扫矩阵、密度场
多分辨率金字塔），提供内存优化原语，覆盖 R886-R900 共 15 轮：

- R886 generator 流式产出（替代 list 一次性物化）
- R887 np.memmap 外存大数组（>内存容量时磁盘映射）
- R888 大对象 del + gc.collect 显式释放
- R889 分块处理 chunked_map（O(N) 内存处理 O(N) 数据）
- R890 峰值内存测量 memory_probe（context manager）
- R891 数组 dtype 降精度（float64→float32，精度可控场景）
- R892 视图替代切片复制（stride_tricks零拷贝）
- R893 稀疏替代密集（CSR 节省 ~95%）
- R894 流式归约 streaming_reduce（不物化中间数组）
- R895 释放回调 release_after（with 块结束自动 del+gc）
- R896-R900 综合内存工具集 facade MemoryOptimizerKit

## 设计原则

1. 内存优先：能流式不物化，能 memmap 不全载入，能稀疏不密集
2. 显式释放：大对象用完即 del + gc.collect，不依赖 GC 时机
3. dtype 适配：存储用 float32，计算用 float64（避免累积误差）
4. 零拷贝视图：stride_tricks 提供窗口视图，不复制数据

## R04 战略（不可撤销）

🚫不参与 GPU：纯 NumPy/SciPy。无 CuPy/CUDA/ROCm/AppleMetal。

## R03 禁止 fall-back

业务错误一律 raise。memmap 文件创建失败、dtype 非法、shape 非法
均 raise，无 except: pass / return None / return []。

## 学术依据（R02，≥5 个文献 URL）

1. Harris et al. 2020 Array programming with NumPy Nature 585 357-362
   https://doi.org/10.1038/s41586-020-2649-2
2. NumPy memmap 官方文档（内存映射文件，out-of-core 计算）
   https://numpy.org/doc/stable/reference/generated/numpy.memmap.html
3. Virtanen et al. 2020 SciPy 1.0 Nature Methods 17 261-272
   https://doi.org/10.1038/s41592-019-0686-2
4. Dask chunked arrays 文档（分块数组 out-of-core 范式）
   https://docs.dask.org/en/stable/array.html
5. Python gc 模块文档（显式垃圾回收 + 循环引用检测）
   https://docs.python.org/3/library/gc.html
6. Higham 2002 Accuracy and Stability of Numerical Algorithms 2nd SIAM
   （float32 vs float64 累积误差分析）https://doi.org/10.1137/1.9780898718027
7. McKinney 2017 Python for Data Analysis 2nd O'Reilly（流式处理）
   https://wesmckinney.com/book/
8. Van Rossum & Drake 2024 Python Language Reference §3 Data model
   （del 与引用计数）https://docs.python.org/3/reference/datamodel.html
9. SciPy scipy.sparse 稀疏矩阵内存优势（CSR 格式）
   https://docs.scipy.org/doc/scipy/reference/sparse.html
10. Apache Arrow memory management（zero-copy 流式处理参考）
    https://arrow.apache.org/docs/python/memory.html

## *创新* 标注（R02）

- *创新* R887：`MemmapArray` 上下文管理器封装 np.memmap，with 块
  结束自动 flush + close + del，避免忘记释放导致文件句柄泄漏。
  底层逻辑：np.memmap 本质是 mmap.mmap + ndarray 视图，显式 close
  释放映射，del 触发 __del__；支持理论：NumPy memmap 文档 + Python
  数据模型 §3；案例：1GB S 参数矩阵磁盘映射，峰值内存 <100MB。
- *创新* R890：`memory_probe` 用 tracemalloc 测量 with 块内峰值内存，
  返回 peak_bytes/current_bytes，量化内存优化效果。底层逻辑：
  tracemalloc 跟踪 Python 分配器，peak 反映瞬时最大占用；支持理论：
  Python