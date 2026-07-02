# PoLaRIS 子模块架构总览

PoLaRIS v5.1 拆分为 **9 个独立子模块 + 1 个编排层**，每个子模块独立目录/独立 pyproject/独立测试/独立 C ABI 头文件，可独立管理升级。

## 子模块划分

| # | 子模块 | 路径 | 职责 | Python API | C ABI 函数 |
|---|--------|------|------|-----------|-----------|
| 1 | polaris-core | `modules/core/` | 核心数据结构（CircuitSpec/DeviceSpec/Tensor） | `make_device`, `make_circuit`, `validate_circuit`, `Tensor` | `polaris_core_make_device`, `polaris_core_make_circuit`, `polaris_core_validate_circuit` |
| 2 | polaris-pdk | `modules/pdk/` | PDK 器件库（4平台36器件，单一职责） | `list_platforms`, `get_device`, `list_devices` | `polaris_pdk_list_platforms`, `polaris_pdk_get_device` |
| 3 | polaris-gdsio | `modules/gdsio/` | GDSII 导入导出（klayout.db 后端，单一职责） | `export_gds`, `import_gds` | `polaris_gdsio_export`, `polaris_gdsio_import` |
| 4 | polaris-place | `modules/place/` | AI 布局（解析布局 + AlphaChip Edge-GNN+PPO） | `place_circuit`, `compute_hpwl`, `render_ascii_layout` | `polaris_place_circuit`, `polaris_place_compute_hpwl` |
| 5 | polaris-route | `modules/route/` | 智能布线（curvy 曲线波导） | `route_circuit`, `compute_path_loss` | `polaris_route_circuit` |
| 6 | polaris-sim | `modules/sim/` | 仿真（频域S参数/Clements酉矩阵/PAM4） | `waveguide_s`, `mmi_1x2_s`, `mmi_2x2_s`, `grating_coupler_s`, `simulate_mzi_sparam`, `compute_clements_unitary`, `simulate_pam4` | `polaris_sim_mzi_sparam`, `polaris_sim_clements_unitary`, `polaris_sim_pam4` |
| 7 | polaris-verify | `modules/verify/` | 验证（DRC 12条规则 + LVS 网表比对） | `run_drc`, `run_lvs` | `polaris_verify_drc`, `polaris_verify_lvs` |
| 8 | polaris-inverse | `modules/inverse/` | 逆向设计（JAX jax.grad 自动微分 *创新*） | `optimize_waveguide_width` | `polaris_inverse_optimize_width` |
| 9 | polaris-quantum | `modules/quantum/` | 量子光子（玻色采样/KLM/HOM/Clements） | `boson_sampling`, `klm_cnot`, `hom_interference`, `clements_unitary` | `polaris_quantum_boson_sampling`, `polaris_quantum_klm_cnot`, `polaris_quantum_hom` |
| - | polaris-orchestrator | `modules/orchestrator/` | 业务编排层（一键调用8子模块） | `run_eda_flow` | `polaris_orchestrator_run_eda_flow` |

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
| `simulate_mzi_sparam(...)` | `polaris_sim_mzi_sparam(...)` | `polaris_result_t` (JSON) |
| `compute_clements_unitary(n)` | `polaris_sim_clements_unitary(...)` | `polaris_result_t` (JSON) |
| `simulate_pam4(...)` | `polaris_sim_pam4(...)` | `polaris_result_t` (JSON) |
| `run_drc(circuit, placements)` | `polaris_verify_drc(...)` | `polaris_result_t` (JSON) |
| `run_lvs(circuit)` | `polaris_verify_lvs(...)` | `polaris_result_t` (JSON) |
| `optimize_waveguide_width(...)` | `polaris_inverse_optimize_width(...)` | `polaris_result_t` (JSON) |
| `boson_sampling(unitary, state)` | `polaris_quantum_boson_sampling(...)` | `polaris_result_t` (JSON) |
| `klm_cnot()` | `polaris_quantum_klm_cnot(...)` | `polaris_result_t` (JSON) |
| `hom_interference(theta)` | `polaris_quantum_hom(...)` | `polaris_result_t` (JSON) |
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
- `main.c`：C 版（8子模块C ABI 调用）
- `Makefile`：`make check_headers` 验证头文件 / `make` 编译
- `README.md`：编译运行说明

## 独立管理

每个子模块可独立：
- `pip install -e modules/<name>/`（独立安装）
- `pytest modules/<name>/tests/`（独立测试）
- 修改 `modules/<name>/` 不影响其他子模块（独立升级）

## 验证结果

- 8 子模块 + orchestrator 全部独立 import 通过
- orchestrator 一键调用 9 stage 全部成功（n_success=9, n_failed=0）
- 业务示例 Python 版可运行 + C 版头文件包含通过（gcc -fsyntax-only 0 错误 0 警告）
