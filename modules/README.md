# PoLaRIS 子模块架构总览

> **版本**: v5.1（2026-07-03 同步刷新，33 模块真实状态）

PoLaRIS v5.0 细粒度拆分为 **33 个子模块**，每个子模块独立目录/独立 pyproject/独立测试/独立 C ABI 头文件，可独立管理升级。

**真实数据**（2026-07-03 扫描）：33 模块 / 289 源码文件 / 99,017 行 / 1,613 测试 / 3,031 文献 URL

## 拆分原则（IPO 三段式文档化）

每个子模块遵循 **Input → Process → Output** 单一职责设计：

- **Input**：明确函数入参（类型/默认值/物理含义）
- **Process**：明确算法/公式/文献溯源（R02 学术诚信）
- **Output**：明确返回 dict 字段（JSON-serializable，业务可直接消费）

每个子模块 `src/polaris_<name>/__init__.py` 顶部 docstring 含 IPO 段落，
对应 `c_api/<name>.h` 顶部注释同样标注 IPO。失败即 raise（R03 禁止 fall-back）。

## 拆分来源（v4 单包 → v5.0 33 子模块）

v4 单包 `src/polaris/`（421 文件/165512 行）于 2026-07-02 重构为 v5.0 monorepo 33 子模块（commit 0277a9c）。

## 33 子模块划分（12 功能分类）

### 核心与编排（3 模块）

| # | 子模块 | 路径 | 文件/行数/测试 | 职责 | 关键 API |
|---|--------|------|----------------|------|----------|
| 1 | polaris-core | `modules/core/` | 3/828/75 | 核心数据结构 | `make_device`, `make_circuit`, `validate_circuit`, `Tensor` |
| 2 | polaris-orchestrator | `modules/orchestrator/` | 2/396/25 | 9-stage EDA 编排 | `run_eda_flow` |
| 3 | polaris-flow | `modules/flow/` | 24/7344/47 | 作业调度/IPKISS/DesignIntent | `Job`, `Stage`, `IPKISSPCell`, `DesignIntentEngine` |

### PDK 与版图 IO（4 模块）

| # | 子模块 | 路径 | 文件/行数/测试 | 职责 | 关键 API |
|---|--------|------|----------------|------|----------|
| 4 | polaris-pdk | `modules/pdk/` | 2/993/40 | 4 平台 36 器件目录 | `list_platforms`, `get_device`, `list_devices` |
| 5 | polaris-pdk-advanced | `modules/pdk_advanced/` | 7/3607/43 | gdsfactory 互操作/PCell | `PolarisPDK`, `polaris_cell`, `parse_pdk_yaml` |
| 6 | polaris-gds-tools | `modules/gds_tools/` | 33/15207/75 | 22 GDSII 工具 + 6 格式 IO | `flatten_gdsii`, `merge_gdsii`, `tapeout_precheck` |
| 7 | polaris-gdsio | `modules/gdsio/` | 3/422/36 | GDSII import/export | `export_gds`, `import_gds` |

### 布局布线（3 模块）

| # | 子模块 | 路径 | 文件/行数/测试 | 职责 | 关键 API |
|---|--------|------|----------------|------|----------|
| 8 | polaris-place | `modules/place/` | 3/1317/45 | DREAMPlace + AlphaChip 布局 | `place_circuit`, `compute_hpwl`, `place_ppo_gnn` |
| 9 | polaris-route | `modules/route/` | 2/1146/72 | 曲线波导布线 | `route_circuit`, `CurvyRouter`, `compute_path_loss` |
| 10 | polaris-router-advanced | `modules/router_advanced/` | 21/8356/107 | 17 种高级布线算法 | `JPSRouter`, `HybridRouter`, `GlobalRouter` |

### 验证（3 模块）

| # | 子模块 | 路径 | 文件/行数/测试 | 职责 | 关键 API |
|---|--------|------|----------------|------|----------|
| 11 | polaris-drc | `modules/drc/` | 2/879/51 | 12 条 SiEPIC DRC 规则 | `run_drc`, `DRCEngine`, `DRCRule` |
| 12 | polaris-lvs | `modules/lvs/` | 2/423/42 | LVS 网表一致性比对 | `run_lvs`, `extract_netlist`, `compare_netlists` |
| 13 | polaris-verify-advanced | `modules/verify_advanced/` | 17/5688/68 | 图同构 LVS/层次化 DRC | `GraphIsomorphismLVSComparer`, `HierarchicalDRC` |

### 物理求解器（5 模块）

| # | 子模块 | 路径 | 文件/行数/测试 | 职责 | 关键 API |
|---|--------|------|----------------|------|----------|
| 14 | polaris-fdtd | `modules/fdtd/` | 4/1121/53 | 3D FDTD（Yee+PML+JAX 可微） | `simulate_waveguide_fdtd`, `YeeGrid3D` |
| 15 | polaris-fde | `modules/fde/` | 2/589/53 | 2D 有限差分本征模 | `solve_modes`, `build_index_profile` |
| 16 | polaris-fdfd | `modules/fdfd/` | 2/540/36 | 频域 Helmholtz | `solve_fdfd`, `build_helmholtz_operator` |
| 17 | polaris-eme | `modules/eme/` | 2/570/52 | 本征模展开（Redheffer） | `solve_eme`, `redheffer_star` |
| 18 | polaris-bpm | `modules/bpm/` | 2/573/33 | Crank-Nicolson 光束传播 | `solve_bpm`, `build_cn_matrices` |

### 电路仿真（2 模块）

| # | 子模块 | 路径 | 文件/行数/测试 | 职责 | 关键 API |
|---|--------|------|----------------|------|----------|
| 19 | polaris-circuit | `modules/circuit/` | 10/2700/88 | 频域/时域/SPICE/系统级 | `CircuitSimulator`, `cascade_circuit`, `MNACircuit` |
| 20 | polaris-sparam | `modules/sparam/` | 4/817/40 | S 参数模型 + Clements | `waveguide_s`, `simulate_mzi_sparam` |

### 逆向设计（2 模块）

| # | 子模块 | 路径 | 文件/行数/测试 | 职责 | 关键 API |
|---|--------|------|----------------|------|----------|
| 21 | polaris-inverse | `modules/inverse/` | 3/1157/56 | JAX 逆向设计 | `optimize_waveguide_width`, `run_adjoint_optimization` |
| 22 | polaris-optimizer | `modules/optimizer/` | 10/3859/76 | 12 种优化器 | `LBFGSOptimizer`, `CMAESOptimizer`, `NSGA3Optimizer` |

### AI/ML（2 模块）

| # | 子模块 | 路径 | 文件/行数/测试 | 职责 | 关键 API |
|---|--------|------|----------------|------|----------|
| 23 | polaris-nn | `modules/nn/` | 23/8094/48 | torch.nn 风格 + benchmark | `Module`, `MultiHeadAttention`, `evaluate_benchmark` |
| 24 | polaris-trainer | `modules/trainer/` | 7/2639/33 | PPO + AlphaChip RL | `PPOAgent`, `train_ppo`, `LargeScalePlacementEnv` |

### 多物理场（3 模块）

| # | 子模块 | 路径 | 文件/行数/测试 | 职责 | 关键 API |
|---|--------|------|----------------|------|----------|
| 25 | polaris-multiphysics | `modules/multiphysics/` | 44/13227/35 | DDM/HEAT/VarFDTD/RCWA | `DdmSolver`, `HeatSolver`, `solve_rcwa_1d` |
| 26 | polaris-lumerical | `modules/lumerical/` | 5/1091/31 | Lumerical/Tidy3D/MEEP 后端 | `LumericalFDTDBackend`, `ModeSolver` |
| 27 | polaris-parasitic | `modules/parasitic/` | 11/2887/49 | 寄生提取 + Verilog-A | `VerilogAModel`, `run_ngspice_cosimulation` |

### 光通信（2 模块）

| # | 子模块 | 路径 | 文件/行数/测试 | 职责 | 关键 API |
|---|--------|------|----------------|------|----------|
| 28 | polaris-pam4 | `modules/pam4/` | 2/347/30 | PAM4 信号 + BER/眼图 | `simulate_pam4`, `compute_ber` |
| 29 | polaris-yield | `modules/yield/` | 8/3615/49 | 蒙特卡洛 + Sobol 良率 | `monte_carlo_simulate`, `yield_analysis` |

### 量子光子（3 模块）

| # | 子模块 | 路径 | 文件/行数/测试 | 职责 | 关键 API |
|---|--------|------|----------------|------|----------|
| 30 | polaris-quantum-advanced | `modules/quantum_advanced/` | 17/4811/42 | 玻色/QKD/层析/QEC | `BB84Protocol`, `SteaneCode`, `hafnian` |
| 31 | polaris-boson | `modules/boson/` | 5/577/32 | 玻色采样 | `boson_sampling`, `hom_interference` |
| 32 | polaris-klm | `modules/klm/` | 2/194/21 | KLM 量子 CNOT 门 | `klm_cnot` |

### GUI（1 模块）

| # | 子模块 | 路径 | 文件/行数/测试 | 职责 | 关键 API |
|---|--------|------|----------------|------|----------|
| 33 | polaris-gui | `modules/gui/` | 5/3003/30 | 版图编辑器 + Macro IDE | `LayoutEditor`, `MacroIDE`, `WebServer` |

## C ABI 公共层

`modules/_c_abi/`：
- `polaris_types.h`：统一类型（`polaris_circuit_t`/`polaris_device_spec_t`/`polaris_connection_t`/`polaris_tensor_t`/`polaris_placement_result_t`/`polaris_routing_result_t`/`polaris_result_t`/`polaris_error_t`）
- `polaris_error.h`：统一错误处理（`POLARIS_OK`=0 / `POLARIS_ERR_INVALID`/`POLARIS_ERR_NOTFOUND`/...）

## C ABI 设计原则

1. **Python 函数 ↔ C 函数一一对应**：函数名 `polaris_<module>_<verb>_<noun>`，参数/返回/异常语义完全一致
2. **纯数据结构**：用 `polaris_circuit_t` 等结构体跨语言传递，无 Python 对象泄漏
3. **统一错误码**：所有 C 函数返回 `polaris_error_t`（0=成功，非0=错误码）
4. **显式生命周期**：caller 用 `polaris_*_free()` 释放返回的结构

## Python ↔ C API 对照表

| Python API | C ABI 函数 | 返回 |
|-----------|-----------|------|
| `make_device(name, type, w, h, ports, params)` | `polaris_core_make_device(...)` | `polaris_device_spec_t` |
| `make_circuit(name, devices, connections, ...)` | `polaris_core_make_circuit(...)` | `polaris_circuit_t` |
| `validate_circuit(circuit)` | `polaris_core_validate_circuit(...)` | `polaris_error_t` |
| `list_platforms()` | `polaris_pdk_list_platforms(...)` | `polaris_result_t` (JSON) |
| `get_device(platform, type)` | `polaris_pdk_get_device(...)` | `polaris_result_t` (JSON) |
| `export_gds(circuit, path)` | `polaris_gdsio_export(...)` | `polaris_result_t` (JSON) |
| `import_gds(gds_path)` | `polaris_gdsio_import(...)` | `polaris_result_t` (JSON) |
| `place_circuit(circuit, mode)` | `polaris_place_circuit(...)` | `polaris_placement_result_t` |
| `compute_hpwl(circuit, placements)` | `polaris_place_compute_hpwl(...)` | `double` |
| `route_circuit(circuit, placements, mode)` | `polaris_route_circuit(...)` | `polaris_routing_result_t` |
| `simulate_mzi_sparam(...)` | `polaris_sparam_mzi(...)` | `polaris_result_t` (JSON) |
| `compute_clements_unitary(n)` | `polaris_sparam_clements(...)` | `polaris_result_t` (JSON) |
| `simulate_pam4(...)` | `polaris_pam4_simulate(...)` | `polaris_result_t` (JSON) |
| `run_drc(circuit, placements)` | `polaris_drc_run(...)` | `polaris_result_t` (JSON) |
| `run_lvs(circuit)` | `polaris_lvs_run(...)` | `polaris_result_t` (JSON) |
| `optimize_waveguide_width(...)` | `polaris_inverse_optimize_width(...)` | `polaris_result_t` (JSON) |
| `boson_sampling(unitary, state)` | `polaris_boson_sampling(...)` | `polaris_result_t` (JSON) |
| `klm_cnot()` | `polaris_klm_cnot(...)` | `polaris_result_t` (JSON) |
| `hom_interference(theta)` | `polaris_boson_hom(...)` | `polaris_result_t` (JSON) |
| `run_eda_flow(circuit, output_dir)` | `polaris_orchestrator_run_eda_flow(...)` | `polaris_result_t` (JSON) |

## 业务侧使用方式

### Python（推荐 orchestrator 一键调用）

```python
from polaris_orchestrator import run_eda_flow
from polaris_core import make_device, make_circuit

circuit = make_circuit('MZI', [...], [...], canvas_w=500, canvas_h=300)
result = run_eda_flow(circuit, 'out/my_design')
# result = {stages: [...], n_success: 9, n_failed: 0, total_duration: 26.04}
```

### Python（精细控制，直接调用子模块）

```python
from polaris_place import place_circuit
from polaris_route import route_circuit
placement = place_circuit(circuit, mode='analytical')
routing = route_circuit(circuit, placement['placements'])
```

### C（通过 C ABI）

```c
#include "orchestrator.h"
polaris_circuit_t circuit;
polaris_core_make_circuit("MZI", devices, 5, conns, 5, 500.0, 300.0, &circuit);
polaris_result_t result;
polaris_orchestrator_run_eda_flow(&circuit, "out/my_design", &result);
printf("%s\n", result.json);
```

## 业务示例

`examples/business_real_case/`：
- `main.py`：Python 版（方式A orchestrator + 方式B 直接调用）
- `main.c`：C 版（多子模块 C ABI 调用）
- `Makefile`：`make check_headers` 验证头文件 / `make` 编译
- `README.md`：编译运行说明

## 独立管理

每个子模块可独立：
- `pip install -e modules/<name>/`（独立安装）
- `pytest modules/<name>/tests/`（独立测试）
- 修改 `modules/<name>/` 不影响其他子模块（独立升级）

## 验证结果（2026-07-03 实测，全 33 子模块）

- **33 子模块全部独立 import 通过**（`pip install -e modules/<name>/` + `python -c "import polaris_<name>"`）
- **orchestrator 一键调用 9 stage 全部成功**（n_success=9, n_failed=0, total_duration≈28s）
- **业务示例 Python 版方式 A + 方式 B 全流程跑通**（13 子模块被调用，`examples/business_real_case/main.py`）
- **业务示例 C 版头文件包含通过**（`gcc -fsyntax-only` 0 错误 0 警告，`examples/business_real_case/main.c`）
- **各子模块独立 pytest 全部通过**（0 failed / 1 skipped，分模块 pytest 实测）：

| 分类 | 子模块（测试数） |
|------|------------------|
| 核心与编排 | core(75) / orchestrator(25) / flow(47) |
| PDK 与版图 IO | pdk(40) / pdk_advanced(43) / gds_tools(75) / gdsio(36) |
| 布局布线 | place(45) / route(72) / router_advanced(107) |
| 验证 | drc(51) / lvs(42) / verify_advanced(68) |
| 物理求解器 | fdtd(53) / fde(53) / fdfd(36) / eme(52) / bpm(33) |
| 电路仿真 | circuit(88) / sparam(40) |
| 逆向设计 | inverse(56) / optimizer(76) |
| AI/ML | nn(48) / trainer(33) |
| 多物理场 | multiphysics(35) / lumerical(31) / parasitic(49) |
| 光通信 | pam4(30) / yield(49) |
| 量子光子 | quantum_advanced(42) / boson(32) / klm(21) |
| GUI | gui(30) |

**合计**：1,613 测试（与 §"33 子模块划分" 各模块测试数加总一致），全量 pytest 实测 1614 passed / 0 failed / 1 skipped。

> 历史对照：v4 单包 9506 测试函数 → v5.0 monorepo 1613 测试（重构后 IPO 单一职责收敛，重复测试合并，新增 33 模块独立 import 测试 + 12 批 subagent 深度测试全 API 表面）。
