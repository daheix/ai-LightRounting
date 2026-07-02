# PoLaRIS 子模块化重构 Spec

## Why
当前 `src/polaris/` 是单包结构，17 个一级目录耦合在一起（ai/data/device/engine/eval/flow/
gui/inverse/io/nn/pdk/pipeline/platform/quantum/rl/router/sim），300+ 文件混在一个包里，
无法独立管理/升级/测试/发布。用户要求拆分为独立子模块，每个子模块：
(1) 独立目录 + 独立 setup.py/pyproject.toml；
(2) 提供稳定的 C ABI 接口（Python 函数可转 C 函数，函数说明一致）；
(3) 业务侧通过统一编排层调用，不直接耦合子模块内部。

## What Changes
- **BREAKING**: 将 `src/polaris/` 单包重构为 `modules/` 下 8 个独立子模块
- 新增 `modules/<name>/` 目录结构，每个子模块含：`pyproject.toml` + `src/` + `tests/` + `c_api/`
- 每个子模块对外暴露稳定 Python API（`__init__.py`）+ C ABI 头文件（`c_api/<module>.h`）
- 新增 `modules/_c_abi/` 公共 C ABI 工具层（统一内存管理/错误处理/张量结构）
- 新增 `modules/orchestrator/` 业务编排层，调用 8 个子模块组合成完整 EDA 流程
- 新增 `examples/business_real_case/` 业务侧真实调用示例（C + Python 双版本）
- 不修改现有 `src/polaris/` 源码（保留作为参考实现，新模块从其抽取）

## Impact
- Affected code: 全部 `src/polaris/` 模块迁移至 `modules/<name>/src/`
- Affected specs: build-e2e-demo-showcase, execute-real-case-full-demo（编排层对接）
- C API 兼容性：所有公共函数遵循 `polaris_<module>_<verb>_<noun>` 命名，参数用纯数据结构

## ADDED Requirements

### Requirement: 8 个独立子模块划分
系统 SHALL 将 PoLaRIS 拆分为 8 个独立子模块，每个有明确职责边界：

| # | 子模块 | 职责 | 来源目录 |
|---|--------|------|---------|
| 1 | `polaris-core` | 核心数据结构（CircuitSpec/DeviceSpec/Tensor/端口/连接） | `data/specs.py`, `nn/` |
| 2 | `polaris-pdk` | PDK 管理（器件库、SiEPIC/gdsfactory PDK、GDSII 导入导出） | `pdk/`, `io/` |
| 3 | `polaris-place` | AI 布局（AlphaChip Edge-GNN + PPO、解析布局、legalization） | `engine/`, `rl/` |
| 4 | `polaris-route` | 智能布线（curvy router、全角度、对角线、JPS） | `router/`, `pipeline/curvy_router.py` |
| 5 | `polaris-sim` | 仿真（FDTD/FDE/EME/BPM/FDFD/频域 S 参数/时域/PAM4） | `sim/` |
| 6 | `polaris-verify` | 验证（DRC/LVS/物理规则/制造约束） | `sim/drc*.py`, `sim/lvs*.py` |
| 7 | `polaris-inverse` | 逆向设计（JAX Adjoint、拓扑优化、形状优化） | `inverse/`, `sim/ai_inverse_design*` |
| 8 | `polaris-quantum` | 量子光子（玻色采样、KLM、HOM、BB84） | `quantum/`, `sim/quantum_*.py` |

#### Scenario: 子模块独立管理
- **WHEN** 升级 polaris-sim 的 FDTD 求解器
- **THEN** 只需修改 `modules/sim/` 目录，其他子模块不受影响，各自独立测试

### Requirement: 稳定 Python API
每个子模块 SHALL 通过 `__init__.py` 暴露稳定的 Python API，遵循：
- 函数名 `snake_case`，参数用纯数据结构（dict/dataclass/ndarray）
- 无内部对象泄漏（不暴露私有类实例）
- 返回值用 JSON-serializable dict 或 numpy ndarray

#### Scenario: Python API 调用
- **WHEN** 业务侧调用布局
- **THEN** `from polaris_place import place_circuit; result = place_circuit(circuit_spec)`
  返回 `{placements: {name: {x,y,w,h}}, hpwl: float}`

### Requirement: C ABI 接口
每个子模块 SHALL 提供 C ABI 头文件 `c_api/<module>.h`，所有 Python 公共函数对应一个 C 函数，
函数说明（参数/返回/异常）与 Python 完全一致。C ABI 遵循：

```c
// 统一错误处理：所有函数返回 polaris_error_t（0=成功，非0=错误码）
typedef int polaris_error_t;

// 统一张量结构（替代 numpy ndarray 跨语言传递）
typedef struct {
    void* data;          // 数据指针（row-major）
    int32_t ndim;        // 维度数
    int64_t* shape;      // 形状数组
    int32_t dtype;       // 0=f32, 1=f64, 2=i32, 3=i64
} polaris_tensor_t;

// 统一电路规格（替代 CircuitSpec）
typedef struct {
    char* name;
    int32_t n_devices;
    polaris_device_spec_t* devices;
    int32_t n_connections;
    polaris_connection_t* connections;
    double canvas_w_um;
    double canvas_h_um;
} polaris_circuit_t;

// 每个函数前缀 polaris_<module>_
polaris_error_t polaris_place_circuit(
    const polaris_circuit_t* circuit,    // 输入：电路规格
    polaris_placement_result_t* out      // 输出：布局结果
);
```

#### Scenario: C 函数与 Python 一致
- **WHEN** 查看任一 C ABI 函数
- **THEN** 其参数/返回/异常语义与对应 Python 函数完全一致，仅类型从 Python 转为 C

### Requirement: 业务编排层
系统 SHALL 提供 `modules/orchestrator/` 编排层，组合 8 个子模块为完整 EDA 流程，
业务侧只需调用编排层，不直接依赖子模块。

#### Scenario: 业务侧一键调用
- **WHEN** 业务侧运行完整 EDA 流程
- **THEN** `from polaris_orchestrator import run_eda_flow; run_eda_flow(circuit, output_dir)`
  自动调用 PDK→布局→布线→仿真→验证→GDS→逆向设计 全流程

### Requirement: 业务侧真实调用程序
系统 SHALL 提供业务侧真实调用示例（C + Python 双版本），展示如何用 8 个子模块 API
完成真实 PIC 设计（100Gbps MZI 调制器，对标 Intel CWDM4）。

#### Scenario: C 业务调用
- **WHEN** C 工程师集成 PoLaRIS
- **THEN** 参考 `examples/business_real_case/main.c`，调用 8 个子模块 C ABI 完成完整流程

## MODIFIED Requirements
（无修改，本 spec 为架构重构）

## REMOVED Requirements
（无移除，旧 `src/polaris/` 保留作为参考实现）
