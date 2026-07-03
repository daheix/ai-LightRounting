# PoLaRIS 商业 Bug 扫描报告

> ⚠️ **已过时（2026-07-03 标注）**: 本报告扫描的是已删除的 v4 `src/polaris/`（421 文件/165512 行）。
> 该目录 2026-07-02 已删（commit 0277a9c），项目重构为 v5.0 33 子模块 monorepo。
> 报告中的 P0/P1/P2/P3 任务全部过时:
> - P0-1 bbox 0 兜底: v5.0 非违规（bbox.empty() 合法判断）
> - P0-2 环检测 ValueError:pass: v5.0 已修复（raise RuntimeError）
> - P0-3 负灵敏度 pass: v5.0 已修复（raise ValueError）
> - P0-4 CuPyBackend GPU API: 随 v4 删除（v5.0 零 GPU 违规）
> v5.0 真实审计结果见 `docs/36-RoundMap.md` §0.2 和 `操作记录.md` 2026-07-03 轮次。
> 本报告保留作历史参考，勿据此时任务清单派发工作。

> 扫描时间：2026-06-30
> 扫描范围：`src/polaris/` 全量代码（421 个 .py 文件，165512 行）
> 扫描分支：main
> 规则依据：R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R05 Bug 必修 / R11 质量门禁（函数≤80行、文件≤800行）
> 声明：本次只做分析，不做修复。所有违规均附文件:行号与修复方案。

---

## 0. 扫描汇总（摘要）

| 维度 | 真正违规 | 边界/技术债 | 合法用法 |
|------|---------|------------|---------|
| R03 except:pass | 2 处 | 2 处 | 8 处（TYPE_CHECKING/空构造/测试断言/清理re-raise） |
| R03 return None | 0 处严重 | ~30 处（有 `T\|None` 类型签名） | — |
| R03 return [] | 0 处严重 | ~10 处（有注释/上层校验） | — |
| R03 except Exception 吞异常 | 1 处（bbox 0 兜底） | — | 多处（清理 + raise） |
| R04 GPU 残留 | 1 处（CuPyBackend 方法体） | — | docstring 声明禁用 |
| R05 TODO/FIXME/HACK | 0 处 | — | 规则文档提及 |
| 质量门禁 超长函数(>80行) | 88 处 | — | — |
| 质量门禁 超长文件(>800行) | 24 处 | — | — |
| R02 文献引用<5 | 56 个业务文件 | — | — |

**严重违规总数：4 处**（必须立即修复）
**技术债总数：118+ 处**（按优先级排期修复）

---

## 1. R03 fall-back 违规清单

### 1.1 真正违规（严重，必须修复）

| 文件 | 行号 | 代码 | 严重度 | 修复方案 |
|------|------|------|--------|---------|
| `src/polaris/verification/gdsii_cell_hierarchy_analyzer.py` | 303-304 | `except Exception: bbox_um = (0.0, 0.0, 0.0, 0.0)` | 🔴严重 | 用 0 兜底 bbox 吞掉 KLayout 异常，导致下游分析基于错误几何数据。改为 `raise RuntimeError(f"cell {name} bbox 读取失败：{exc}") from exc`，让上层捕获并跳过该 cell 或终止。 |
| `src/polaris/verification/gdsii_cell_hierarchy_analyzer.py` | 459-461 | `except ValueError: pass  # v 不在 path 中（不应发生），跳过` | 🟡中等 | 环检测 DFS 中 `path.index(v)` 抛 ValueError 静默跳过。注释已承认"不应发生"，应改为 `raise RuntimeError(f"DFS 状态不一致：v={v} 不在 path={path}") from exc`，暴露算法 bug。 |
| `src/polaris/sim/yield_optimization.py` | 370 | `if np.any(sensitivities < 0): pass` | 🟡中等 | 检测到负灵敏度后 `pass` 不处理，紧接着只检查全 0。负值是非法输入，应改为 `raise ValueError(f"sensitivities 必须 >=0，得到 {sensitivities}")`。 |
| `src/polaris/engine/gpu_backend.py` | 188-239 | CuPyBackend 的 `fft2/ifft2/matmul/convolve2d/gaussian_kernel/to_numpy/from_numpy` 方法体仍引用 `self._cupy.fft.fft2` 等 GPU API | 🔴R04严重 | `__init__` 已 `raise RuntimeError` 阻断实例化，但方法体保留 GPU 代码违反 R04"禁止 CuPy"原则，且 `self._cupy` 从未定义（实例化前已 raise）。修复：每个方法体改为 `raise RuntimeError("🚫R04: CuPyBackend 已禁用")`，彻底删除 GPU API 引用。 |

### 1.2 边界情况（建议加日志或复核，非严重违规）

| 文件 | 行号 | 模式 | 说明 | 建议 |
|------|------|------|------|------|
| `src/polaris/pdk/gdsfactory_integration.py` | 433 | `except ImportError: pass` | 可选 PDK 模块导入失败静默跳过 | 加 `logger.debug(f"PDK 模块 {module_name} 不可用，跳过")`，便于诊断 |
| `src/polaris/sim/ibis_ami.py` | 244 | `elif keyword in ("voltage range","typ","min","max"): pass` | IBIS 元数据关键字未解析 | 加注释说明"这些关键字在 _collect_data_line 中处理"或显式记录 |

### 1.3 return None / return [] 边界清单（有 `T | None` 类型签名，技术债）

> 说明：以下均有明确类型注解（如 `float | None`、`tuple | None`），业务语义为"未找到/未启用/无解"，属 Optional 类型的合法用法。但 R03 严格条款禁止 `return None`，建议长期改为 `raise` 或 `Result` 类型。**不计入严重违规**，列为技术债。

**return None（约 30 处，按类别归类）：**

| 类别 | 文件:行号 | 业务语义 |
|------|----------|---------|
| A* 路径搜索无解 | `router/global_router.py:288,398`、`router/waveguide_router.py:489`、`router/diagonal_router.py:164` | A* 标准模式，建议改为 `raise RouteNotFoundError` |
| 端口/实例不存在 | `router/global_router.py:189,193`、`router/curvy_optodesigner.py:123,128` | 几何查找，建议 `raise KeyError` |
| 谐振特征不足 | `sim/simulator.py:467,492,510,616,620` | FSR/Q/BW 无法计算，建议 `raise ValueError("特征点不足")` |
| ILU 未启用 | `sim/fdfd/solver.py:382` | 配置开关，可保留 Optional 语义 |
| 层索引不存在 | `sim/lvs.py:376` | GDS 层查找，建议 `raise KeyError` |
| LRU 缓存未命中 | `pdk/pcell.py:77` | 标准缓存模式，可保留 |
| 路由 rip-up 失败 | `router/rip_reroute.py:202` | 已有 `logger.error`，建议改 `raise` |
| 其他 | `flow/tracker.py:59,86,89,110`、`flow/workspace.py:142,154`、`flow/ipkiss_flow.py:269`、`io/_cif.py:232`、`flow/stage.py:75`、`data/variant_generator.py:475`、`data/benchmark_history.py:237`、`verification/gdsii_drc_width_space.py:610`、`verification/gdsii_cell_renamer.py:165,177,184`、`gui/interactive.py:673,755` | 逐个复核 |

**return []（约 10 处，多数有注释说明）：**

| 文件:行号 | 说明 |
|----------|------|
| `sim/klayout_drc.py:364,368` | 层不存在/无图形，有注释"非违规"，可保留 |
| `router/commercial_router.py:487` | 重布失败信号，有注释"由 route_all 验证成功率"，可保留 |
| `sim/hierarchical_drc.py:62` | 空输入返回 None（BVH 构建），可保留 |
| `sim/hierarchical_drc.py:116,152,207,222,373,385` | DRC 检查无违规返回空列表，合法语义 |
| `router/bundle_router.py:131,172,217,255` | 束布线候选为空，建议复核 |
| `router/routing_env.py:348,352` | 候选为空，建议复核 |

### 1.4 合法用法（不计违规）

- `except Exception: tmp_path.unlink(missing_ok=True); raise` —— 原子写入清理 + re-raise（`io/multi_format.py:308`、`flow/workspace.py:128`、`eval/layout_render.py:110`、`pipeline/training.py:370`、`pipeline/integrated.py:744`）✓
- `except ImportError: jax = None` —— JAX/gdsfactory 可选依赖（`sim/autodiff.py:45`、`sim/types.py:32`、`sim/monte_carlo.py:39`、`sim/jax_backend.py:51`、`pdk/gdsfactory_pdk_bridge.py:38`）✓
- `if TYPE_CHECKING: pass` —— 类型检查占位（`router/curvy_optodesigner.py:42`、`pdk/pcell_gdsfactory_bridge.py:48`、`pdk/gpic.py:38`）✓
- `def __init__(self): pass` / `def render(self): pass` —— 接口占位（`trainer/dataset.py:245`、`engine/floorplan_env.py:564`、`device/tcad_thermal_package.py:871`、`pdk/pcell.py:318`）✓
- `except KeyError: raise KeyError(...)` —— 重新抛出带上下文（`pdk/foundry_platforms.py:294`、`pdk/process_nodes.py:270`、`pdk/catalog.py:323,327`）✓
- `except KeyError: pass`（测试代码断言验证）—— `pdk/foundry_pdk_expanded.py:406` ✓

---

## 2. 代码质量问题

### 2.1 TODO/FIXME/HACK 残留

**扫描结果：0 处真正残留。**

所有 `TODO/FIXME/HACK` 匹配均为规则文档（R05 规则文本、docstring 中"0 TODO/FIXME"声明）中的字符串引用，非代码残留。✓

### 2.2 超长函数（>80 行）—— 共 88 处

> 质量门禁：函数 ≤80 行（R11 §质量门禁）。88 个函数超标，Top 20 如下：

| 行数 | 文件:行号 | 函数名 |
|------|----------|--------|
| 237 | `sim/importance_sampling.py:862` | `cross_entropy_importance_sampling` |
| 230 | `verification/gdsii_edge_extractor.py:177` | `extract_edges` |
| 227 | `sim/stratified_sampling.py:363` | `stratified_monte_carlo` |
| 207 | `verification/gdsii_cell_substituter.py:279` | `substitute_cell_instances` |
| 195 | `verification/gdsii_cell_hierarchy_analyzer.py:154` | `analyze_cell_hierarchy` |
| 191 | `verification/gdsii_layout_merger.py:164` | `merge_gdsii` |
| 190 | `verification/gdsii_statistics.py:155` | `generate_gdsii_statistics` |
| 190 | `pdk/gdsfactory_integration.py:768` | `import_gdsii_from_gdsfactory` |
| 182 | `verification/gdsii_diff_tool.py:148` | `compare_gdsii_files` |
| 182 | `verification/gdsii_connectivity_analyzer.py:392` | `analyze_cross_layer_connectivity` |
| 175 | `verification/gdsii_cell_renamer.py:190` | `rename_cells` |
| 171 | `sim/importance_sampling.py:518` | `importance_sampling_yield` |
| 167 | `verification/gdsii_layer_visualizer.py:278` | `visualize_layers_ascii` |
| 166 | `verification/gdsii_boolean_ops.py:148` | `boolean_operation` |
| 165 | `verification/gdsii_sizing_tool.py:145` | `size_layer` |
| 165 | `verification/gdsii_grid_alignment_checker.py:155` | `check_grid_alignment` |
| 158 | `verification/gdsii_connectivity_analyzer.py:158` | `analyze_layer_connectivity` |
| 155 | `verification/gdsii_drc_batch.py:171` | `run_batch_drc` |
| 154 | `verification/gdsii_tapeout_precheck.py:128` | `tapeout_precheck` |
| 151 | `verification/gdsii_port_extractor.py:165` | `extract_ports` |

**完整 88 个清单见附录 A。**

**特征分析**：
- `verification/gdsii_*.py` 占超长函数的 ~60%（GDSII 处理流水线函数普遍 100-230 行）
- `sim/importance_sampling.py`、`sim/stratified_sampling.py` 统计采样函数普遍 >120 行
- 修复策略：按"提取子函数 + 策略对象"重构，优先处理 >150 行的 12 个函数

### 2.3 超长文件（>800 行）—— 共 24 处

> 质量门禁：文件 ≤800 行（R11 §质量门禁）。24 个文件超标。

| 行数 | 文件 |
|------|------|
| 1798 | `src/polaris/quantum/quantum_circuit_distributed.py` |
| 1737 | `src/polaris/pdk/gdsfactory_integration.py` |
| 1371 | `src/polaris/sim/lvs_advanced.py` |
| 1337 | `src/polaris/pdk/gdsfactory_advanced.py` |
| 1257 | `src/polaris/device/tcad_thermal_package.py` |
| 1109 | `src/polaris/sim/importance_sampling.py` |
| 1094 | `src/polaris/sim/parasitic_advanced.py` |
| 1018 | `src/polaris/verification/_drc_checks.py` |
| 1012 | `src/polaris/verification/statistical_yield.py` |
| 989 | `src/polaris/verify/calibre_interface.py` |
| 972 | `src/polaris/sim/__init__.py` |
| 924 | `src/polaris/rl/rl_numpy_advanced.py` |
| 913 | `src/polaris/verification/_drc_geometry.py` |
| 899 | `src/polaris/sim/subnetwork_decomp.py` |
| 868 | `src/polaris/sim/ibis_ami.py` |
| 866 | `src/polaris/sim/gdsfactory_cosim.py` |
| 858 | `src/polaris/verification/yield_advanced.py` |
| 834 | `src/polaris/web/server.py` |
| 832 | `src/polaris/sim/cml_compiler_full.py` |
| 814 | `src/polaris/sim/fdtd_jax_backend.py` |
| 810 | `src/polaris/gui/interactive.py` |
| 805 | `src/polaris/sim/cascade_backends.py` |
| 805 | `src/polaris/pipeline/integrated.py` |
| 800 | `src/polaris/sim/klu_backend.py` |

**修复策略**：按模块拆分。`quantum_circuit_distributed.py`(1798行) 和 `gdsfactory_integration.py`(1737行) 优先拆分为子模块。

---

## 3. R04 GPU 合规问题

### 3.1 真正违规（1 处，严重）

| 文件 | 行号 | 问题 | 修复方案 |
|------|------|------|---------|
| `src/polaris/engine/gpu_backend.py` | 188-239 | `CuPyBackend` 的 7 个方法（`fft2/ifft2/matmul/convolve2d/gaussian_kernel/to_numpy/from_numpy`）方法体仍引用 `self._cupy.fft.fft2`、`self._cupy.matmul`、`self._cupy.exp` 等 CuPy GPU API。虽然 `__init__` 已 `raise RuntimeError` 阻断实例化（方法不可达），但代码体保留 GPU API 违反 R04"禁止 CuPy"原则。 | 每个方法体改为 `raise RuntimeError("🚫R04: CuPyBackend 已禁用，使用 NumPyBackend")`，删除所有 `self._cupy.*` 引用。 |

### 3.2 合规（已正确修复）

- `src/polaris/engine/gpu_backend.py` `check_cupy_availability()` 直接 `return False`，不 import cupy ✓
- `src/polaris/engine/gpu_backend.py` `CuPyBackend.__init__` 立即 `raise RuntimeError` ✓
- `src/polaris/engine/gpu_backend.py` `GPUBackend` 强制使用 `NumPyBackend`（CPU）✓
- `src/polaris/engine/gpu_density_field.py` 已改为纯 CPU 实现，仅 import `GPUBackend`（内部 CPU）✓
- `src/polaris/sim/fdtd_gpu_engine.py` `GPUFDTDConfig.use_gpu` 强制 False，`__init__` 校验 raise ✓
- 其他 `cupy/cuda/rocm/metal` 匹配均为 docstring 中"🚫禁止"声明 ✓

### 3.3 FP16/BF16 半精度扫描

未发现 `float16`/`bfloat16`/`FP16`/`BF16` 实际使用（仅 docstring 声明禁止）。✓

---

## 4. 学术诚信问题（文献引用 <5）

> R02 规则：每个模块 docstring 含 ≥5 个文献 URL。
> 扫描结果：421 个 .py 文件中，**56 个业务文件 URL < 5**（已排除 `__init__.py` 包初始化文件）。

### 4.1 严重缺失（URL ≤ 1，共 6 个）

| URL数 | 文件 | 修复建议 |
|-------|------|---------|
| 0 | `src/polaris/__main__.py` | 入口文件，补 CLI 设计文献 |
| 1 | `src/polaris/sim/ibis_ami.py` | IBIS-AMI 标准（IBIS 6.1 spec）、SerDes AMI 规范 |
| 1 | `src/polaris/sim/grid/yee.py` | Yee 网格原始论文（Yee 1966 IEEE TAP）、Taflove FDTD 教材 |
| 1 | `src/polaris/sim/grid/pml.py` | PML 原始论文（Berenger 1994 JCP）、Gedney PML 改进 |
| 1 | `src/polaris/sim/fdfd/sparam.py` | S 参数提取文献、EM 仿真教材 |
| 1 | `src/polaris/pipeline/_converters.py` | 数据转换格式规范 |

### 4.2 一般缺失（URL 2-4，共 50 个）

| URL数 | 文件（示例） |
|-------|------------|
| 2 | `sim/netlist_adapter.py`、`sim/models_extended.py`、`sim/batch_simulation.py`、`pdk/source.py`、`pdk/optodesigner_flexconnector.py`、`pdk/foundry_devices_active.py`、`pdk/siepic_mapping.py`、`pdk/inp/passive.py`、`pdk/inp/active.py`、`pdk/inp/tapers.py`、`engine/netlist.py`、`engine/gpu_density_field.py` |
| 3 | `sim/yield_optimization.py`、`sim/lumerical_mode.py`、`sim/lbfgs_optimizer.py`、`sim/importance_sampling.py`、`sim/types.py`、`sim/siepic_netlist.py`、`sim/dag_scheduler.py`、`sim/pso_optimizer.py`、`pdk/optodesigner.py`、`pdk/port.py`、`pdk/module_library.py`、`data/standard_devices.py`、`engine/density_field.py`、`engine/fft_density_field.py`、`trainer/parallel_rollout.py` |
| 4 | `sim/constraint_checker.py`、`sim/mna_spice.py`、`sim/monte_carlo.py`、`sim/topology_optimizer.py`、`pdk/pcell.py`、`pdk/optodesigner_pycell.py`、`flow/job.py`、`flow/stage.py`、`io/_odbpp.py`、`trainer/vtrace.py`、`rl/alpha_chip_trainer.py`、`rl/alpha_chip_encoder.py` |

**修复策略**：每个文件补齐 ≥5 个权威文献 URL（arXiv/IEEE/Springer/官方文档），优先修复 URL ≤ 1 的 6 个文件。

---

## 5. 修复任务清单（按优先级排序）

### P0 — 立即修复（商业 Bug，阻塞正确性）

| 任务ID | 描述 | 文件 | 预估工作量 |
|--------|------|------|-----------|
| P0-1 | 修复 `gdsii_cell_hierarchy_analyzer.py:303` bbox 0 兜底 fall-back，改为 raise + 上层捕获 | `verification/gdsii_cell_hierarchy_analyzer.py` | 0.5h（含回归测试） |
| P0-2 | 修复 `gdsii_cell_hierarchy_analyzer.py:459` 环检测 ValueError:pass，改为 raise 暴露 DFS bug | `verification/gdsii_cell_hierarchy_analyzer.py` | 0.5h |
| P0-3 | 修复 `sim/yield_optimization.py:370` 负灵敏度 pass，改为 raise ValueError | `sim/yield_optimization.py` | 0.3h |
| P0-4 | 删除 `engine/gpu_backend.py:188-239` CuPyBackend 方法体 GPU API，改为 raise（R04 合规） | `engine/gpu_backend.py` | 0.5h |

### P1 — 高优先级（R04 合规 + 学术诚信严重缺失）

| 任务ID | 描述 | 文件 | 预估工作量 |
|--------|------|------|-----------|
| P1-1 | 补齐 6 个 URL≤1 文件的文献引用（ibis_ami/yee/pml/sparam/_converters/__main__） | `sim/`、`pipeline/` | 3h |
| P1-2 | `gdsfactory_integration.py:433` 加 `logger.debug` 诊断可选 PDK 模块跳过 | `pdk/gdsfactory_integration.py` | 0.2h |
| P1-3 | `ibis_ami.py:244` 加注释说明未解析关键字的去向 | `sim/ibis_ami.py` | 0.2h |

### P2 — 中优先级（超长文件拆分，影响可维护性）

| 任务ID | 描述 | 文件 | 预估工作量 |
|--------|------|------|-----------|
| P2-1 | 拆分 `quantum_circuit_distributed.py`（1798行）为子模块 | `quantum/` | 1d |
| P2-2 | 拆分 `gdsfactory_integration.py`（1737行）为子模块 | `pdk/` | 1d |
| P2-3 | 拆分 `lvs_advanced.py`（1371行）、`gdsfactory_advanced.py`（1337行） | `sim/`、`pdk/` | 1d |
| P2-4 | 拆分 `tcad_thermal_package.py`（1257行）、`importance_sampling.py`（1109行） | `device/`、`sim/` | 1d |
| P2-5 | 拆分剩余 19 个 800-1100 行文件（按模块批量处理） | 多模块 | 3d |

### P3 — 低优先级（超长函数重构 + 文献补齐）

| 任务ID | 描述 | 文件 | 预估工作量 |
|--------|------|------|-----------|
| P3-1 | 重构 12 个 >150 行的函数（提取子函数 + 策略对象） | `verification/gdsii_*.py`、`sim/importance_sampling.py` | 3d |
| P3-2 | 重构 76 个 80-150 行的函数 | 多模块 | 5d |
| P3-3 | 补齐 50 个 URL 2-4 文件的文献引用至 ≥5 | 多模块 | 2d |
| P3-4 | 复核 ~30 处 `return None` 边界情况，按业务语义改为 raise 或保留 Optional | `router/`、`sim/`、`flow/` | 2d |
| P3-5 | 复核 ~10 处 `return []` 边界情况 | `router/bundle_router.py`、`router/routing_env.py` | 0.5d |

---

## 附录 A：超长函数完整清单（88 个）

| 行数 | 文件:行号 | 函数名 |
|------|----------|--------|
| 237 | sim/importance_sampling.py:862 | cross_entropy_importance_sampling |
| 230 | verification/gdsii_edge_extractor.py:177 | extract_edges |
| 227 | sim/stratified_sampling.py:363 | stratified_monte_carlo |
| 207 | verification/gdsii_cell_substituter.py:279 | substitute_cell_instances |
| 195 | verification/gdsii_cell_hierarchy_analyzer.py:154 | analyze_cell_hierarchy |
| 191 | verification/gdsii_layout_merger.py:164 | merge_gdsii |
| 190 | verification/gdsii_statistics.py:155 | generate_gdsii_statistics |
| 190 | pdk/gdsfactory_integration.py:768 | import_gdsii_from_gdsfactory |
| 182 | verification/gdsii_diff_tool.py:148 | compare_gdsii_files |
| 182 | verification/gdsii_connectivity_analyzer.py:392 | analyze_cross_layer_connectivity |
| 175 | verification/gdsii_cell_renamer.py:190 | rename_cells |
| 171 | sim/importance_sampling.py:518 | importance_sampling_yield |
| 167 | verification/gdsii_layer_visualizer.py:278 | visualize_layers_ascii |
| 166 | verification/gdsii_boolean_ops.py:148 | boolean_operation |
| 165 | verification/gdsii_sizing_tool.py:145 | size_layer |
| 165 | verification/gdsii_grid_alignment_checker.py:155 | check_grid_alignment |
| 158 | verification/gdsii_connectivity_analyzer.py:158 | analyze_layer_connectivity |
| 155 | verification/gdsii_drc_batch.py:171 | run_batch_drc |
| 154 | verification/gdsii_tapeout_precheck.py:128 | tapeout_precheck |
| 151 | verification/gdsii_port_extractor.py:165 | extract_ports |
| 150 | verification/gdsii_density_analyzer.py:308 | compute_density_map |
| 150 | verification/gdsii_clip_tool.py:267 | multi_clip_gdsii |
| 145 | verification/gdsii_layer_visualizer.py:128 | compute_layer_stats |
| 142 | sim/yield_optimization.py:448 | optimize_yield_via_nominal_shift |
| 135 | verification/gdsii_layout_scaler.py:195 | scale_gdsii |
| 133 | verification/gdsii_clip_tool.py:129 | clip_gdsii |
| 131 | sim/importance_sampling.py:275 | _construct_biasing_distribution |
| 130 | verification/gdsii_density_analyzer.py:173 | compute_layer_density |
| 129 | pdk/gdsfactory_integration.py:1167 | create_gdsii_layout_from_cells |
| 127 | verification/gdsii_text_label_extractor.py:143 | extract_text_labels |
| 127 | verification/gdsii_batch_pipeline.py:176 | run_batch_pipeline |
| 124 | verification/gdsii_drc_grid.py:147 | check_grid |
| 123 | verification/gdsii_drc_interlayer.py:317 | _run_interlayer_check |
| 122 | verification/gdsii_drc_area.py:150 | check_area |
| 121 | sim/importance_sampling.py:691 | importance_sampling_mean |
| 120 | verification/gdsii_drc_width_space.py:264 | _run_check |
| 118 | verification/gdsii_drc_strange_polygon.py:164 | check_strange_polygon |
| 118 | verification/gdsii_drc_notch.py:154 | check_notch |
| 118 | verification/gdsii_drc_isolated.py:153 | check_isolated |
| 117 | sim/yield_optimization.py:329 | allocate_tolerance_by_sensitivity |
| 116 | verification/gdsii_health_check.py:417 | check_gdsii_health |
| 113 | verification/statistical_yield.py:896 | _test |
| 112 | verification/gdsii_flattener.py:133 | flatten_gdsii |
| 111 | verification/gdsii_device_position_reporter.py:160 | extract_device_positions |
| 108 | verification/gdsii_geometry_transformer.py:154 | transform_gdsii_geometry |
| 108 | pdk/pcell_gdsfactory_bridge.py:266 | gdsfactory_component_to_pcell |
| 105 | verification/batch_drc_processor.py:118 | run_batch_drc |
| 104 | quantum/quantum_circuit_distributed.py:1691 | _test |
| 103 | sim/yield_optimization.py:224 | compute_worst_case_distance |
| 103 | sim/lvs_advanced.py:1202 | generate_structured_error_report |
| 102 | sim/batch_simulation.py:125 | batch_simulate |
| 101 | pdk/pcell_gdsfactory_bridge.py:160 | pcell_to_gdsfactory_component |
| 100 | sim/monte_carlo.py:363 | sobol_sensitivity_analysis |
| 99 | pdk/gdsfactory_integration.py:1066 | round_trip_gdsii |
| 98 | sim/stratified_sampling.py:592 | compare_stratified_convergence |
| 96 | verification/gdsii_drc_batch.py:378 | _validate_rule |
| 96 | verification/gdsii_density_analyzer.py:463 | check_density_rules |
| 94 | verification/gdsii_drc_validator.py:100 | extract_polygons_from_gdsii |
| 94 | nn/attention.py:114 | _multi_head_attention_op |
| 93 | sim/batch_simulation.py:229 | batch_yield_analysis |
| 93 | pdk/awg_ip_materials.py:218 | _register_builtin |
| 93 | device/tcad_thermal_package.py:629 | thermal_crosstalk_matrix |
| 92 | verification/_drc_geometry.py:764 | _polygon_symmetry_score |
| 92 | sim/qmc_sampling.py:372 | compare_qmc_convergence |
| 90 | verification/yield_advanced.py:282 | run |
| 89 | sim/lvs_advanced.py:538 | extract_directional_couplers |
| 87 | pdk/yaml_pdk_config.py:455 | serialize_pdk_yaml |
| 86 | verification/_drc_checks.py:108 | _apply_single_rule |
| 86 | sim/lvs_advanced.py:792 | extract_ring_resonators |
| 86 | sim/lumerical_charge.py:264 | electro_optic_simulation |
| 85 | verification/yield_advanced.py:589 | compute |
| 85 | sim/fdtd_gpu_engine.py:362 | _step |
| 85 | quantum/quantum_circuit_distributed.py:1333 | training_step |
| 84 | sim/lvs_advanced.py:680 | extract_mmis |
| 84 | sim/ibis_ami.py:167 | _handle_keyword |
| 84 | gui/layout_editor.py:488 | export_klayout_script |
| 83 | verification/yield_advanced.py:752 | worst_case_search |
| 83 | sim/three_d_effects.py:220 | sidewall_roughness_loss |
| 83 | sim/gdsfactory_cosim.py:671 | simulate_gdsfactory_circuit |
| 83 | pdk/pdk_version_checker.py:334 | check_pdk_version_compatibility |
| 83 | device/tcad_thermal_package.py:1171 | _test |
| 83 | ai/inverse_design.py:313 | train_step |
| 82 | verification/yield_advanced.py:420 | run |
| 82 | sim/quantum_klm.py:267 | klm_cnot_simulate |
| 82 | sim/_lvs_nets.py:404 | detect_open_circuits |
| 81 | sim/qmc_sampling.py:123 | generate_qmc_samples |
| 81 | sim/parasitic_advanced.py:559 | compute_s_params |
| 81 | data/benchmark_evaluator.py:373 | evaluate_drv |

---

## 附录 B：扫描方法与规则依据

| 扫描项 | 工具 | 规则依据 |
|--------|------|---------|
| except:pass / return None / return [] | Grep + 人工复核 | R03 禁止 fall-back |
| except Exception 吞异常 | Grep + 上下文读 | R03 禁止静默兜底 |
| TODO/FIXME/HACK | Grep | R05 Bug 必修 |
| 超长函数 | Python AST (`ast.walk`) | R11 §质量门禁 函数≤80行 |
| 超长文件 | `wc -l` + sort | R11 §质量门禁 文件≤800行 |
| GPU 合规 | Grep `cupy\|cuda\|rocm\|metal\|FP16\|BF16` | R04 不参与 GPU |
| 文献引用 | Python `re.findall(r'https?://...')` | R02 学术诚信 ≥5 URL |

**声明**：本报告基于静态扫描 + 人工上下文复核，未执行动态测试。所有"真正违规"均经 Read 工具确认上下文。无 fall-back 假数据，无凭经验判断。

---

**报告生成完毕。**
