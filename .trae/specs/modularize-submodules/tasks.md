# Tasks

- [ ] Task 1: 创建 8 个子模块目录骨架 + C ABI 公共层
  - [ ] SubTask 1.1: 创建 `modules/` 根目录 + `modules/_c_abi/` 公共 C ABI 工具层
        （`polaris_types.h` 统一张量/电路/错误码结构，`polaris_error.h` 错误处理）
  - [ ] SubTask 1.2: 创建 8 个子模块目录骨架：`modules/{core,pdk,place,route,sim,verify,inverse,quantum}/`
        每个含 `pyproject.toml` + `src/polaris_<name>/__init__.py` + `c_api/<name>.h` + `tests/`
  - [ ] SubTask 1.3: 创建 `modules/orchestrator/` 编排层骨架

- [ ] Task 2: 实现 polaris-core 子模块（核心数据结构）
  - [ ] SubTask 2.1: 迁移 `data/specs.py`（CircuitSpec/DeviceSpec/BenchmarkSource/TargetMetric）
        到 `modules/core/src/polaris_core/specs.py`
  - [ ] SubTask 2.2: 迁移 `nn/`（Tensor 自动微分）到 `modules/core/src/polaris_core/tensor.py`
  - [ ] SubTask 2.3: 暴露稳定 Python API：`make_circuit()`, `make_device()`, `circuit_to_dict()`
  - [ ] SubTask 2.4: 生成 C ABI 头文件 `c_api/core.h`（polaris_circuit_t/polaris_device_spec_t/
        polaris_connection_t + polaris_core_make_circuit/polaris_core_free_circuit）
  - [ ] SubTask 2.5: 写 tests/test_specs.py 验证数据结构

- [ ] Task 3: 实现 polaris-pdk 子模块（PDK 管理）
  - [ ] SubTask 3.1: 迁移 `pdk/catalog.py` + `pdk/device.py` + `pdk/foundry_devices*.py`
        到 `modules/pdk/src/polaris_pdk/`
  - [ ] SubTask 3.2: 迁移 `pdk/gdsii_exporter.py` + `pdk/gdsii_importer.py` + `io/` 多格式
        到 `modules/pdk/src/polaris_pdk/io/`
  - [ ] SubTask 3.3: 暴露 Python API：`list_platforms()`, `get_device()`, `export_gds()`, `import_gds()`
  - [ ] SubTask 3.4: 生成 C ABI `c_api/pdk.h`（polaris_pdk_list_platforms/polaris_pdk_export_gds）
  - [ ] SubTask 3.5: tests 验证 4 平台 36 器件可枚举 + GDS 可导出

- [ ] Task 4: 实现 polaris-place 子模块（AI 布局）
  - [ ] SubTask 4.1: 迁移 `engine/alphachip_gnn.py` + `engine/analytical_placer.py` +
        `engine/legalization.py` + `rl/alpha_chip*.py` + `rl/edge_gnn.py` 到 `modules/place/`
  - [ ] SubTask 4.2: 暴露 Python API：`place_circuit(circuit, mode="ppo_gnn")` → {placements, hpwl}
  - [ ] SubTask 4.3: 生成 C ABI `c_api/place.h`（polaris_place_circuit/polaris_placement_result_t）
  - [ ] SubTask 4.4: tests 验证 MZI 5 器件布局成功 + HPWL>0

- [ ] Task 5: 实现 polaris-route 子模块（智能布线）
  - [ ] SubTask 5.1: 迁移 `router/curvy_router.py` + `router/all_angle_router.py` +
        `router/diagonal_router.py` + `router/jps_router.py` 到 `modules/route/`
  - [ ] SubTask 5.2: 暴露 Python API：`route_circuit(circuit, placements)` → {paths, total_loss_db}
  - [ ] SubTask 5.3: 生成 C ABI `c_api/route.h`（polaris_route_circuit/polaris_routing_result_t）
  - [ ] SubTask 5.4: tests 验证 MZI 5 连接布线成功 + 损耗物理合理

- [ ] Task 6: 实现 polaris-sim 子模块（仿真）
  - [ ] SubTask 6.1: 迁移 `sim/__init__.py` 公共 API（waveguide_s/mmi_s/grating_coupler_s/
        clements_unitary/compute_ber/compute_snr_db/generate_pam4_signal/compute_eye_diagram）
        到 `modules/sim/src/polaris_sim/`
  - [ ] SubTask 6.2: 迁移 `sim/fdtd/` + `sim/fdtd_jax_backend.py` + `sim/fde/` + `sim/eme/` +
        `sim/bpm/` 到 `modules/sim/src/polaris_sim/solvers/`
  - [ ] SubTask 6.3: 暴露 Python API：`simulate_mzi_sparam()`, `simulate_fdtd_waveguide()`,
        `simulate_pam4_eye()`, `compute_clements_unitary()`
  - [ ] SubTask 6.4: 生成 C ABI `c_api/sim.h`（polaris_sim_mzi_sparam/polaris_sim_fdtd_waveguide）
  - [ ] SubTask 6.5: tests 验证 MZI 谐振 1549nm + ER=30dB + PAM4 BER 量级合理

- [ ] Task 7: 实现 polaris-verify 子模块（DRC/LVS）
  - [ ] SubTask 7.1: 迁移 `sim/hierarchical_drc.py` + `sim/klayout_drc.py` + `sim/eqdrc.py` +
        `sim/lvs*.py` + `sim/constraint_*.py` 到 `modules/verify/`
  - [ ] SubTask 7.2: 暴露 Python API：`run_drc(circuit, placements)`, `run_lvs(circuit, netlist)`
  - [ ] SubTask 7.3: 生成 C ABI `c_api/verify.h`（polaris_verify_drc/polaris_verify_lvs）
  - [ ] SubTask 7.4: tests 验证 DRC pass_rate>0 + LVS is_consistent

- [ ] Task 8: 实现 polaris-inverse 子模块（逆向设计）
  - [ ] SubTask 8.1: 迁移 `inverse/topology_adjoint_optimizer.py` + `sim/ai_inverse_design*.py` +
        `sim/fdtd_jax_backend.py`（JAX Adjoint）到 `modules/inverse/`
  - [ ] SubTask 8.2: 暴露 Python API：`optimize_waveguide_width(n_iterations=50)` → {fom_history, converged}
  - [ ] SubTask 8.3: 生成 C ABI `c_api/inverse.h`（polaris_inverse_optimize_width）
  - [ ] SubTask 8.4: tests 验证 50 次迭代无 NaN + FoM 改善

- [ ] Task 9: 实现 polaris-quantum 子模块（量子光子）
  - [ ] SubTask 9.1: 迁移 `quantum/boson_sampling.py` + `quantum/klm_helpers.py` +
        `quantum/bb84_protocol.py` + `sim/quantum_*.py` 到 `modules/quantum/`
  - [ ] SubTask 9.2: 暴露 Python API：`boson_sampling(unitary, input_state)`, `klm_cnot_success_prob()`,
        `hom_dip_depth(theta)`
  - [ ] SubTask 9.3: 生成 C ABI `c_api/quantum.h`（polaris_quantum_boson_sampling）
  - [ ] SubTask 9.4: tests 验证玻色采样概率和=1 + HOM dip_depth=1 + KLM 成功率=1/9

- [ ] Task 10: 实现 polaris-orchestrator 编排层
  - [ ] SubTask 10.1: 实现 `modules/orchestrator/src/polaris_orchestrator/__init__.py`
        暴露 `run_eda_flow(circuit, output_dir)` 一键调用 8 个子模块
  - [ ] SubTask 10.2: 编排顺序：PDK→布局→布线→仿真→验证→GDS导出→逆向设计→量子验证
  - [ ] SubTask 10.3: 生成 C ABI `c_api/orchestrator.h`（polaris_orchestrator_run_eda_flow）
  - [ ] SubTask 10.4: tests 验证完整流程 10 阶段全部成功

- [ ] Task 11: 业务侧真实调用示例（C + Python 双版本）
  - [ ] SubTask 11.1: 创建 `examples/business_real_case/main.py`：Python 业务侧调用
        8 个子模块 API 完成 100Gbps MZI 设计（对标 Intel CWDM4）
  - [ ] SubTask 11.2: 创建 `examples/business_real_case/main.c`：C 业务侧调用
        8 个子模块 C ABI 完成同样流程
  - [ ] SubTask 11.3: 创建 `examples/business_real_case/Makefile` + `README.md`
        说明编译运行方式
  - [ ] SubTask 11.4: 验证 Python 版可运行 + C 版可编译（至少头文件包含通过）

- [ ] Task 12: 端到端验证与提交
  - [ ] SubTask 12.1: 运行 `python examples/business_real_case/main.py`，验证 8 子模块
        全部被调用且输出真实结果
  - [ ] SubTask 12.2: 验证每个子模块可独立 import + 独立测试（pytest modules/<name>/tests/）
  - [ ] SubTask 12.3: 生成 `modules/README.md` 总览文档（8 子模块 API 速查表 + C ABI 对照表）
  - [ ] SubTask 12.4: git add 精确文件 → commit → push origin main（R11）
  - [ ] SubTask 12.5: 追加操作记录到 `操作记录.md`（R07）

# Task Dependencies
- Task 2-9 依赖 Task 1（需要目录骨架 + C ABI 公共层）
- Task 2-9 之间相互独立，可并行
- Task 10 依赖 Task 2-9（编排层调用所有子模块）
- Task 11 依赖 Task 10（业务示例调用编排层）
- Task 12 依赖 Task 11
