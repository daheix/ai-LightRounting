# R105-R110 代码质量与合规基线报告

- 扫描时间: $(date)
- 扫描范围: src/polaris/ 共 360 个 Python 文件
- 覆盖规则: R105 圈复杂度 / R106 函数行长 / R107 类型注解 / R108 文献引用 / R109 fall-back / R110 GPU 合规

## R105 圈复杂度（radon cc）

- 函数总数: **1470**
- 复杂度 >15 函数数: **7**

### Top 20 复杂度最高函数
| 文件 | 函数 | 行号 | 圈复杂度 |
|------|------|------|----------|
| src/polaris/verification/drc_curvilinear_18rules.py | _polygon_taper_angle | 421 | 25 |
| src/polaris/quantum/quantum_circuit_distributed.py | _test | 1691 | 23 |
| src/polaris/io/_cif.py | _cif_dispatch | 114 | 18 |
| src/polaris/verification/drc_curvilinear_18rules.py | _segments_intersect | 239 | 17 |
| src/polaris/data/benchmark_evaluator.py | evaluate_drv | 373 | 16 |
| src/polaris/device/tcad_thermal_package.py | _test | 1171 | 16 |
| src/polaris/verification/statistical_yield.py | _test | 896 | 16 |
| src/polaris/gui/interactive.py | evaluate_object | 171 | 15 |
| src/polaris/io/_gerber.py | _gerber_process_blocks | 121 | 15 |
| src/polaris/quantum/boson_sampling.py | boson_sampling_probability | 139 | 15 |
| src/polaris/pdk/gdsfactory_pdk_bridge.py | parse_pic_yaml | 298 | 14 |
| src/polaris/pdk/process_nodes.py | suggest_process_node_for_circuit | 444 | 14 |
| src/polaris/sim/ddm/coupling.py | ddm_to_heat_joule | 90 | 14 |
| src/polaris/io/multi_format.py | layouts_equal | 172 | 13 |
| src/polaris/pdk/awg_ip_materials.py | _test | 547 | 13 |
| src/polaris/pdk/foundry_pdk_expanded.py | _test | 362 | 13 |
| src/polaris/sim/simulator.py | group_delay | 345 | 13 |
| src/polaris/pdk/gdsfactory_pdk_bridge.py | convert_layerstack | 142 | 12 |
| src/polaris/pdk/pcell.py | _is_instance | 509 | 12 |
| src/polaris/sim/constraint_checks_geometry.py | check_enclosure | 434 | 12 |

### 复杂度 >15 完整清单
| 文件 | 函数 | 行号 | 圈复杂度 |
|------|------|------|----------|
| src/polaris/verification/drc_curvilinear_18rules.py | _polygon_taper_angle | 421 | 25 |
| src/polaris/quantum/quantum_circuit_distributed.py | _test | 1691 | 23 |
| src/polaris/io/_cif.py | _cif_dispatch | 114 | 18 |
| src/polaris/verification/drc_curvilinear_18rules.py | _segments_intersect | 239 | 17 |
| src/polaris/data/benchmark_evaluator.py | evaluate_drv | 373 | 16 |
| src/polaris/device/tcad_thermal_package.py | _test | 1171 | 16 |
| src/polaris/verification/statistical_yield.py | _test | 896 | 16 |

## R106 函数行长

- 函数总数: **3993**
- >80 行函数数: **14**
- 文件总数: **360**
- >800 行文件数: **14**

### Top 20 最长函数
| 文件 | 函数 | 行号 | 行长 |
|------|------|------|------|
| src/polaris/verification/statistical_yield.py | _test | 896 | 107 |
| src/polaris/quantum/quantum_circuit_distributed.py | _test | 1691 | 104 |
| src/polaris/nn/attention.py | _multi_head_attention_op | 114 | 94 |
| src/polaris/device/tcad_thermal_package.py | thermal_crosstalk_matrix | 629 | 93 |
| src/polaris/pdk/awg_ip_materials.py | _register_builtin | 218 | 93 |
| src/polaris/sim/lumerical_charge.py | electro_optic_simulation | 264 | 86 |
| src/polaris/quantum/quantum_circuit_distributed.py | training_step | 1333 | 85 |
| src/polaris/sim/fdtd_gpu_engine.py | _step | 350 | 85 |
| src/polaris/gui/layout_editor.py | export_klayout_script | 488 | 84 |
| src/polaris/sim/ibis_ami.py | _handle_keyword | 167 | 84 |
| src/polaris/ai/inverse_design.py | train_step | 313 | 83 |
| src/polaris/device/tcad_thermal_package.py | _test | 1171 | 83 |
| src/polaris/sim/quantum_klm.py | klm_cnot_simulate | 267 | 82 |
| src/polaris/data/benchmark_evaluator.py | evaluate_drv | 373 | 81 |
| src/polaris/sim/ddm/_newton.py | run_newton | 296 | 80 |
| src/polaris/verification/drc_curvilinear_18rules.py | _check_rule | 630 | 80 |
| src/polaris/verification/statistical_yield.py | extract_wire | 327 | 80 |
| src/polaris/web/server.py | do_POST | 557 | 80 |
| src/polaris/flow/stage_verification.py | stage6_drc_lvs | 125 | 79 |
| src/polaris/pipeline/integrated.py | _place_random | 234 | 79 |

### >800 行文件清单
| 文件 | 行数 |
|------|------|
| src/polaris/quantum/quantum_circuit_distributed.py | 1798 |
| src/polaris/verification/drc_curvilinear_18rules.py | 1377 |
| src/polaris/device/tcad_thermal_package.py | 1257 |
| src/polaris/verification/statistical_yield.py | 1006 |
| src/polaris/verify/calibre_interface.py | 989 |
| src/polaris/sim/subnetwork_decomp.py | 891 |
| src/polaris/sim/ibis_ami.py | 868 |
| src/polaris/web/server.py | 834 |
| src/polaris/sim/cml_compiler_full.py | 832 |
| src/polaris/sim/__init__.py | 820 |
| src/polaris/sim/fdtd_jax_backend.py | 814 |
| src/polaris/gui/interactive.py | 810 |
| src/polaris/pipeline/integrated.py | 805 |
| src/polaris/sim/cascade_backends.py | 805 |

## R107 类型注解覆盖率

- 参数总数: **7384**, 已注解: **7032**, 覆盖率: **95.23%**
- 返回值总数: **3993**, 已注解: **3841**, 覆盖率: **96.19%**

## R108 文献引用统计

- 模块总数: **360**
- URL 总数: **2141**
- 平均每模块 URL: **5.95**
- 引用 <5 的模块数: **146**

### 引用 <5 模块清单（前 50）
| 文件 | URL 数 |
|------|--------|
| src/polaris/__init__.py | 0 |
| src/polaris/__main__.py | 0 |
| src/polaris/engine/__init__.py | 0 |
| src/polaris/eval/__init__.py | 0 |
| src/polaris/gui/__init__.py | 0 |
| src/polaris/io/__init__.py | 0 |
| src/polaris/pdk/sin/passive.py | 0 |
| src/polaris/pdk/sin/resonators.py | 0 |
| src/polaris/pdk/soi/couplers.py | 0 |
| src/polaris/router/__init__.py | 0 |
| src/polaris/sim/grid/__init__.py | 0 |
| src/polaris/sim/nsga3_optimizer.py | 0 |
| src/polaris/sim/subnetwork_decomp.py | 0 |
| src/polaris/trainer/__init__.py | 0 |
| src/polaris/pdk/optodesigner_flexconnector.py | 1 |
| src/polaris/pipeline/_converters.py | 1 |
| src/polaris/router/jps_router.py | 1 |
| src/polaris/sim/autodiff.py | 1 |
| src/polaris/sim/backend_selector.py | 1 |
| src/polaris/sim/cascade/__init__.py | 1 |
| src/polaris/sim/constraint_checks_performance.py | 1 |
| src/polaris/sim/fde/mode.py | 1 |
| src/polaris/sim/fdfd/sparam.py | 1 |
| src/polaris/sim/grid/pml.py | 1 |
| src/polaris/sim/grid/yee.py | 1 |
| src/polaris/sim/ibis_ami.py | 1 |
| src/polaris/sim/level_set_solver.py | 1 |
| src/polaris/sim/lumerical_mode.py | 1 |
| src/polaris/sim/monte_carlo.py | 1 |
| src/polaris/sim/multi_objective_optimizer.py | 1 |
| src/polaris/sim/nsga2_operators.py | 1 |
| src/polaris/web/__init__.py | 1 |
| src/polaris/engine/density_field.py | 2 |
| src/polaris/engine/gpu_density_field.py | 2 |
| src/polaris/engine/netlist.py | 2 |
| src/polaris/pdk/foundry_devices_active.py | 2 |
| src/polaris/pdk/inp/active.py | 2 |
| src/polaris/pdk/inp/passive.py | 2 |
| src/polaris/pdk/inp/tapers.py | 2 |
| src/polaris/pdk/optodesigner_hierarchy.py | 2 |
| src/polaris/pdk/optodesigner_pdaflow.py | 2 |
| src/polaris/pdk/optodesigner_pycell.py | 2 |
| src/polaris/pdk/pcell.py | 2 |
| src/polaris/pdk/siepic_mapping.py | 2 |
| src/polaris/pdk/soi/resonators.py | 2 |
| src/polaris/pdk/source.py | 2 |
| src/polaris/rl/__init__.py | 2 |
| src/polaris/router/curvy_validator.py | 2 |
| src/polaris/router/global_router.py | 2 |
| src/polaris/sim/feedback_adapter.py | 2 |

## R109 R03 fall-back 风险

- 风险总数: **107**

### 按模式分类
| 模式 | 数量 |
|------|------|
| except: pass | 0 |
| except Exception: pass | 1 |
| except X: pass | 1 |
| return None | 45 |
| return [] | 43 |
| return {} | 17 |

### 详细清单（前 100 条）
| 模式 | 文件 | 行号 | 代码 |
|------|------|------|------|
| except Exception: pass | src/polaris/sim/cascade/__init__.py | 346 | `# 禁止 except Exception: pass 静默吞异常（规则 14.1）` |
| except X: pass | src/polaris/sim/cascade/__init__.py | 346 | `# 禁止 except Exception: pass 静默吞异常（规则 14.1）` |
| return None | src/polaris/data/benchmark_history.py | 237 | `return None` |
| return None | src/polaris/data/variant_generator.py | 475 | `return None` |
| return None | src/polaris/flow/ipkiss_flow.py | 269 | `return None` |
| return None | src/polaris/flow/stage.py | 75 | `return None` |
| return None | src/polaris/flow/tracker.py | 59 | `return None` |
| return None | src/polaris/flow/tracker.py | 86 | `return None` |
| return None | src/polaris/flow/tracker.py | 89 | `return None` |
| return None | src/polaris/flow/tracker.py | 110 | `return None` |
| return None | src/polaris/flow/workspace.py | 142 | `return None` |
| return None | src/polaris/flow/workspace.py | 154 | `return None` |
| return None | src/polaris/gui/interactive.py | 673 | `return None` |
| return None | src/polaris/gui/interactive.py | 755 | `return None` |
| return None | src/polaris/io/_cif.py | 232 | `return None` |
| return None | src/polaris/pdk/catalog.py | 99 | `return None` |
| return None | src/polaris/pdk/catalog.py | 112 | `return None` |
| return None | src/polaris/pdk/gdsfactory_integration.py | 445 | `return None` |
| return None | src/polaris/pdk/pcell.py | 77 | `return None` |
| return None | src/polaris/pdk/pcell.py | 644 | `return None` |
| return None | src/polaris/pdk/process_nodes.py | 532 | `return None` |
| return None | src/polaris/pipeline/curvy_router.py | 330 | `return None` |
| return None | src/polaris/router/curvy_optodesigner.py | 123 | `return None` |
| return None | src/polaris/router/curvy_optodesigner.py | 128 | `return None` |
| return None | src/polaris/router/diagonal_router.py | 164 | `return None` |
| return None | src/polaris/router/global_router.py | 179 | `return None` |
| return None | src/polaris/router/global_router.py | 183 | `return None` |
| return None | src/polaris/router/global_router.py | 278 | `return None` |
| return None | src/polaris/router/global_router.py | 388 | `return None` |
| return None | src/polaris/router/rip_reroute.py | 175 | `return None` |
| return None | src/polaris/router/waveguide_router.py | 474 | `return None` |
| return None | src/polaris/sim/dag_scheduler.py | 136 | `return None` |
| return None | src/polaris/sim/fdfd/solver.py | 382 | `return None` |
| return None | src/polaris/sim/graph_lvs.py | 376 | `return None` |
| return None | src/polaris/sim/heat/transient.py | 243 | `return None` |
| return None | src/polaris/sim/heat/transient.py | 250 | `return None` |
| return None | src/polaris/sim/hierarchical_drc.py | 53 | `return None` |
| return None | src/polaris/sim/klayout_drc.py | 359 | `return None` |
| return None | src/polaris/sim/klayout_drc.py | 369 | `return None` |
| return None | src/polaris/sim/lvs.py | 376 | `return None` |
| return None | src/polaris/sim/photoelectric_cosim.py | 691 | `return None` |
| return None | src/polaris/sim/simulator.py | 467 | `return None` |
| return None | src/polaris/sim/simulator.py | 492 | `return None` |
| return None | src/polaris/sim/simulator.py | 510 | `return None` |
| return None | src/polaris/sim/simulator.py | 616 | `return None` |
| return None | src/polaris/sim/simulator.py | 620 | `return None` |
| return None | src/polaris/system/__init__.py | 135 | `return None` |
| return [] | src/polaris/data/_pic_ir.py | 273 | `return []` |
| return [] | src/polaris/flow/tracker.py | 70 | `return []` |
| return [] | src/polaris/pdk/gdsfactory_integration.py | 412 | `return []` |
| return [] | src/polaris/pipeline/curvy_router.py | 375 | `return []` |
| return [] | src/polaris/pipeline/training.py | 588 | `return []` |
| return [] | src/polaris/pipeline/training.py | 593 | `return []` |
| return [] | src/polaris/router/bundle_router.py | 131 | `return []` |
| return [] | src/polaris/router/bundle_router.py | 172 | `return []` |
| return [] | src/polaris/router/bundle_router.py | 217 | `return []` |
| return [] | src/polaris/router/bundle_router.py | 255 | `return []` |
| return [] | src/polaris/router/commercial_router.py | 487 | `return []  # 重布失败信号(显式空,由 route_all 验证成功率)` |
| return [] | src/polaris/router/curvy_router.py | 299 | `return []` |
| return [] | src/polaris/router/routing_env.py | 341 | `return []` |
| return [] | src/polaris/router/routing_env.py | 345 | `return []` |
| return [] | src/polaris/router/waveguide_router.py | 313 | `return []` |
| return [] | src/polaris/router/waveguide_router.py | 373 | `return []` |
| return [] | src/polaris/sim/constraint_checks_geometry.py | 110 | `return []` |
| return [] | src/polaris/sim/constraint_checks_performance.py | 41 | `return []` |
| return [] | src/polaris/sim/constraint_checks_performance.py | 57 | `return []` |
| return [] | src/polaris/sim/devs/solver.py | 531 | `return []` |
| return [] | src/polaris/sim/devs/solver.py | 565 | `return []` |
| return [] | src/polaris/sim/eqdrc.py | 320 | `return []` |
| return [] | src/polaris/sim/fdtd_meep_backend.py | 82 | `return []` |
| return [] | src/polaris/sim/hierarchical_drc.py | 107 | `return []` |
| return [] | src/polaris/sim/hierarchical_drc.py | 143 | `return []` |
| return [] | src/polaris/sim/hierarchical_drc.py | 198 | `return []` |
| return [] | src/polaris/sim/hierarchical_drc.py | 213 | `return []` |
| return [] | src/polaris/sim/hierarchical_drc.py | 362 | `return []` |
| return [] | src/polaris/sim/hierarchical_drc.py | 374 | `return []` |
| return [] | src/polaris/sim/jax_backend.py | 84 | `return []` |
| return [] | src/polaris/sim/klayout_drc.py | 328 | `return []  # 层不存在，跳过（非违规）` |
| return [] | src/polaris/sim/klayout_drc.py | 332 | `return []  # 层无图形，跳过` |
| return [] | src/polaris/sim/klayout_drc.py | 346 | `return []` |
| return [] | src/polaris/sim/klayout_drc.py | 408 | `return []` |
| return [] | src/polaris/sim/klayout_drc.py | 411 | `return []` |
| return [] | src/polaris/sim/klayout_drc.py | 414 | `return []` |
| return [] | src/polaris/sim/klayout_drc.py | 474 | `return []` |
| return [] | src/polaris/sim/klayout_drc.py | 479 | `return []` |
| return [] | src/polaris/sim/klayout_drc.py | 497 | `return []` |
| return [] | src/polaris/sim/lvs.py | 222 | `return []` |
| return [] | src/polaris/sim/lvs.py | 257 | `return []` |
| return [] | src/polaris/verify/calibre_interface.py | 425 | `return []` |
| return [] | src/polaris/verify/calibre_interface.py | 450 | `return []` |
| return {} | src/polaris/data/benchmark_evaluator.py | 557 | `return {}` |
| return {} | src/polaris/engine/analytical_placer.py | 546 | `return {}` |
| return {} | src/polaris/engine/legalization.py | 91 | `return {}` |
| return {} | src/polaris/pdk/gdsfactory_integration.py | 525 | `return {}` |
| return {} | src/polaris/pdk/pcell.py | 589 | `return {}` |
| return {} | src/polaris/pipeline/curvy_router.py | 104 | `return {}` |
| return {} | src/polaris/pipeline/integrated.py | 249 | `return {}` |
| return {} | src/polaris/router/commercial_router.py | 399 | `return {}` |
| return {} | src/polaris/sim/cascade/__init__.py | 185 | `return {}` |
| return {} | src/polaris/sim/cascade/__init__.py | 368 | `return {}` |

## R110 R04 GPU 合规

- 实际使用（import/代码）: **23**
- 文档/注释提及: **3**

### 实际使用清单
| 文件 | 行号 | 代码 |
|------|------|------|
| src/polaris/engine/gpu_backend.py | 0 | `import cupy` |
| src/polaris/engine/gpu_backend.py | 10 | `违反 R04"禁止 CuPy/CUDA/ROCm 等所有 GPU 后端"战略决策。修复：` |
| src/polaris/engine/gpu_backend.py | 27 | `- 禁止 CuPy/CUDA/ROCm/AppleMetal 等所有 GPU 后端` |
| src/polaris/engine/gpu_backend.py | 42 | `- CuPy: Okuta et al., 2017, https://cupy.dev/` |
| src/polaris/engine/gpu_backend.py | 78 | `_ = cupy.cuda.Device(0).compute_capability` |
| src/polaris/engine/gpu_backend.py | 180 | `"禁止 CuPy/CUDA/ROCm 等所有 GPU 后端。"` |
| src/polaris/pdk/awg_ip_materials.py | 164 | `category: str  # semiconductor / dielectric / polymer / metal` |
| src/polaris/pdk/awg_ip_materials.py | 287 | `name="aluminum", category="metal",` |
| src/polaris/pdk/awg_ip_materials.py | 293 | `name="gold", category="metal",` |
| src/polaris/pdk/awg_ip_materials.py | 299 | `name="titanium", category="metal",` |
| src/polaris/quantum/quantum_circuit_distributed.py | 1089 | `本实现: multiprocessing.Pool 多进程并行（R04 纯 CPU，无 GPU/CUDA/Ray）。` |
| src/polaris/rl/edge_gnn.py | 14 | `本模块纯 NumPy/SciPy CPU 实现，禁止 CuPy/CUDA/ROCm/AppleMetal，` |
| src/polaris/rl/edge_gnn.py | 15 | `禁止 FP16/BF16 半精度。Apollo (arXiv:2504.18813) 的 GPU 加速 PIC 布局` |
| src/polaris/sim/harold.py | 61 | `纯 NumPy/SciPy 实现，无 CuPy/CUDA 等 GPU 后端。` |
| src/polaris/sim/jax_backend.py | 11 | `- 🚫不参与 GPU 加速：禁止 CuPy/CUDA/ROCm/AppleMetal 等所有 GPU 后端` |
| src/polaris/sim/jax_backend.py | 12 | `- 禁止 FP16/BF16 半精度、多卡 GPU 分布式` |
| src/polaris/sim/lumerical_charge.py | 34 | `纯 NumPy 实现，不引入 CuPy/CUDA/ROCm 等 GPU 后端。` |
| src/polaris/sim/lumerical_integration.py | 43 | `纯 NumPy/SciPy/CPU 实现，不引入 CuPy/CUDA/ROCm 等 GPU 后端。` |
| src/polaris/sim/lumerical_interconnect.py | 19 | `纯 NumPy 实现，不引入 CuPy/CUDA/ROCm 等 GPU 后端。` |
| src/polaris/sim/lumerical_mode.py | 26 | `纯 NumPy 实现，不引入 CuPy/CUDA/ROCm 等 GPU 后端。` |
| src/polaris/sim/stack_solver.py | 65 | `纯 NumPy 实现，无 CuPy/CUDA 等 GPU 后端。` |
| src/polaris/sim/tidy3d_integration.py | 19 | `NumPy 向量化 CPU 计算，不引入任何 GPU 后端（CuPy/CUDA/ROCm/AppleMetal）。` |
| src/polaris/sim/tidy3d_integration.py | 400 | `纯 NumPy 向量化 CPU 计算，不引入任何 GPU 后端（CuPy/CUDA/ROCm/` |

### 文档/注释提及清单（前 30）
| 文件 | 行号 | 代码 |
|------|------|------|
| src/polaris/engine/gpu_backend.py | 175 | `# R04 战略决策：不参与 GPU 计算，禁止 CuPy/CUDA/ROCm` |
| src/polaris/engine/gpu_backend.py | 176 | `# 原 try/except import cupy 路径已删除，禁止任何 GPU 后端初始化` |
| src/polaris/sim/tidy3d_integration.py | 390 | `# 严格遵守 R04：无 CuPy/CUDA/ROCm/AppleMetal 等任何 GPU 后端依赖。` |

## 结论

- R105/R106: 圈复杂度 >15 与 >80 行函数为代码质量改进重点，后续 R601+ 质量完成阶段处理。
- R107: 类型注解覆盖率为可量化指标，需在 R601+ 提升至 ≥90%。
- R108: 引用 <5 的模块需补充文献（R02 学术诚信，每个模块 docstring ≥5 文献 URL）。
- R109: fall-back 风险需逐条审核，区分合法（边界返回 None）与违规（静默兜底假数据）。
- R110: GPU 实际使用需逐条核查，若仅文档提及（R04 战略说明）则合规；若实际 import 则违规需删除。
