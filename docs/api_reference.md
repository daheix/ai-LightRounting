# PoLaRIS API 参考手册

> 版本 v6.1 · 2026-07 · 33 子模块公共 API 完整参考
> 数据来源：modules/*/src/polaris_* 实际代码（R02 学术诚信）
> 合规声明：R03 禁止 fall-back / R04 不参与 GPU / R05 Bug 必修 / R13 不保留 v4 兼容

---

## 目录

- [第 1 章：核心编排层（polaris-core / polaris-flow / polaris-orchestrator）](#第-1-章核心编排层polaris-core--polaris-flow--polaris-orchestrator)
- [第 2 章：布局（polaris-place）](#第-2-章布局polaris-place)
- [第 3 章：布线（polaris-route / polaris-router-advanced）](#第-3-章布线polaris-route--polaris-router-advanced)
- [第 4 章：物理求解器（polaris-fdtd / fde / fdfd / eme / bpm / circuit / sparam）](#第-4-章物理求解器polaris-fdtd--fde--fdfd--eme--bpm--circuit--sparam)
- [第 5 章：验证（polaris-drc / polaris-lvs / polaris-verify-advanced）](#第-5-章验证polaris-drc--polaris-lvs--polaris-verify-advanced)
- [第 6 章：输出 IO（polaris-gdsio / polaris-gds-tools / polaris-pdk / polaris-pdk-advanced）](#第-6-章输出-iopolis-gdsio--polaris-gds-tools--polaris-pdk--polaris-pdk-advanced)
- [第 7 章：AI/ML（polaris-nn / polaris-trainer）](#第-7-章aimlpolaris-nn--polaris-trainer)
- [第 8 章：逆向设计（polaris-inverse / polaris-optimizer）](#第-8-章逆向设计polaris-inverse--polaris-optimizer)
- [第 9 章：量子光子（polaris-boson / polaris-klm / polaris-quantum-advanced）](#第-9-章量子光子polaris-boson--polaris-klm--polaris-quantum-advanced)
- [第 10 章：GUI（polaris-gui）](#第-10-章guipolaris-gui)
- [第 11 章：光电协同（polaris-parasitic / polaris-multiphysics / polaris-pam4 / polaris-yield / polaris-lumerical）](#第-11-章光电协同polaris-parasitic--polaris-multiphysics--polaris-pam4--polaris-yield--polaris-lumerical)
- [附录 A：数据类型参考](#附录-a数据类型参考)
- [附录 B：错误码与异常](#附录-b错误码与异常)

---

## 第 1 章：核心编排层（polaris-core / polaris-flow / polaris-orchestrator）

### 1.1 polaris-core — 核心数据结构

> 源码：`modules/core/src/polaris_core/__init__.py` · 版本 `5.0.0`
> 文献：GDSFactory https://gdsfactory.github.io/gdsfactory/ · TILOS https://github.com/TILOS-AI-Institute/MacroPlacement · Apollo https://github.com/ASU-LOPE-Group/Apollo · SiEPIC PDK https://github.com/SiEPIC/SiEPIC_EBeam_PDK

#### `make_device(name, device_type, width_um=10.0, height_um=10.0, ports=None, params=None, process_node=None) -> dict`

创建器件规格，返回 JSON-serializable dict。

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `name` | `str` | — | 器件实例名（如 `"gc1"`） |
| `device_type` | `str` | — | 器件类型（如 `"grating_coupler"`） |
| `width_um` | `float` | `10.0` | 器件宽度（μm） |
| `height_um` | `float` | `10.0` | 器件高度（μm） |
| `ports` | `list \| None` | `None` | 端口列表 `[(name, dx, dy, direction), ...]` |
| `params` | `dict \| None` | `None` | 器件参数 dict |
| `process_node` | `str \| None` | `None` | 工艺节点（如 `"220nm SOI"`） |

**返回**：`dict` 含 `name`/`device_type`/`width_um`/`height_um`/`ports`/`params`/`process_node` 字段。

```python
import polaris_core

dev = polaris_core.make_device(
    name="gc1",
    device_type="grating_coupler",
    width_um=10.0,
    height_um=10.0,
    ports=[("o1", 0.0, 5.0, "east")],
    params={"insertion_loss_db": 1.9},
    process_node="220nm SOI",
)
```

#### `make_circuit(name, devices, connections, canvas_w=1000.0, canvas_h=1000.0, process_node=None, optical_wavelength_nm=1550.0) -> dict`

创建电路规格，返回 JSON-serializable dict。

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `name` | `str` | — | 电路名（如 `"MZI"`） |
| `devices` | `list` | — | 器件列表（`DeviceSpec` 或 `dict` 均可） |
| `connections` | `list` | — | 连接列表 `[(dev1, port1, dev2, port2), ...]` |
| `canvas_w` | `float` | `1000.0` | 画布宽度（μm） |
| `canvas_h` | `float` | `1000.0` | 画布高度（μm） |
| `process_node` | `str \| None` | `None` | 工艺节点 |
| `optical_wavelength_nm` | `float` | `1550.0` | 工作波长（nm） |

**返回**：`dict` 含 `name`/`devices`/`connections`/`canvas_w`/`canvas_h`/`process_node`/`optical_wavelength_nm`。

#### `circuit_to_dict(circuit) -> dict`

将 `CircuitSpec` 或 dict 转换为 JSON-serializable dict。

| 参数 | 类型 | 说明 |
|------|------|------|
| `circuit` | `CircuitSpec \| dict` | 电路规格 |

**返回**：JSON-serializable circuit dict。

**异常**：`RuntimeError` — circuit 类型非法或 dict 缺少必要字段。

#### `validate_circuit(circuit) -> bool`

验证 circuit dict 结构完整性，失败 raise `RuntimeError`（R03 禁止 fall-back）。

校验项：circuit 为 dict；含 `name`/`devices`/`connections`/`canvas_w`/`canvas_h` 字段；每个 device 含 `name`/`device_type`/`width_um`/`height_um`/`ports`/`params`；每条 connection 为长度 4 的 list/tuple 且引用的器件名存在。

| 参数 | 类型 | 说明 |
|------|------|------|
| `circuit` | `dict` | 待验证的 circuit dict |

**返回**：`True`（验证通过）。失败时 raise `RuntimeError`。

```python
import polaris_core

circuit = polaris_core.make_circuit(
    name="MZI",
    devices=[
        polaris_core.make_device("gc1", "grating_coupler", 10, 10,
            [("o1", 0, 5, "east")]),
        polaris_core.make_device("mmi1", "mmi_1x2", 20, 10,
            [("o1", 0, 5, "west"), ("o2", 20, 5, "east")]),
    ],
    connections=[("gc1", "o1", "mmi1", "o1")],
)
assert polaris_core.validate_circuit(circuit) is True
```

#### 数据类（内部使用）

- `DeviceSpec` — 器件规格 dataclass（字段：`name`/`device_type`/`width_um`/`height_um`/`ports`/`params`/`process_node`）
- `CircuitSpec` — 电路规格 dataclass（字段：`name`/`devices`/`connections`/`canvas_w`/`canvas_h`/`benchmark_source`/`process_node`/`optical_wavelength_nm`/`target_metric`/`target_value`）
- `BenchmarkSource` — 枚举（`TILOS`/`APOLLO`/`LIDAR`/`CUSTOM`）
- `TargetMetric` — 枚举（`HPWL`/`DRV`/`ROUTING_SUCCESS_RATE`/`INSERTION_LOSS_DB`）
- `Tensor` — 自动微分张量基类（PyTorch autograd 风格）

---

### 1.2 polaris-flow — 通用流程编排

> 源码：`modules/flow/src/polaris_flow/__init__.py` · 版本 `5.0.0`
> 文献：IPKISS https://www.lucedaphotonics.com/products/ipkiss · Cadence ADE-XL https://docs.cadence.com/ · Synopsys OptoDesigner https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner.html · Mingaleev SPIE 2017 https://doi.org/10.1117/12.2252001 · Sutton & Barto 2018 http://incompleteideas.net/book/RLbook2020.pdf

#### `Job` 数据类

作业数据结构，表示一次完整的 10 阶段流水线执行。

| 字段 | 类型 | 说明 |
|------|------|------|
| `job_id` | `str` | 时间戳格式 `YYYYMMDD_HHMMSS_<6位随机>` |
| `recipe` | `Recipe` | 作业配方 |
| `workspace` | `Workspace` | 工作空间 |
| `status` | `JobStatus` | 作业状态（默认 `QUEUED`） |
| `stage_results` | `list[StageResult]` | 各阶段结果 |
| `submit_time` | `datetime` | 提交时间 |
| `start_time` | `datetime \| None` | 开始时间 |
| `end_time` | `datetime \| None` | 结束时间 |
| `error` | `str \| None` | 错误信息 |
| `current_stage` | `int` | 当前阶段（0=未开始，1-10=阶段N） |

方法：`mark_running()` / `mark_completed()` / `mark_failed(error)` / `mark_cancelled()` / `to_dict()` / `progress` 属性。

#### `JobStatus` 枚举

`QUEUED`（已提交）/ `RUNNING`（执行中）/ `COMPLETED`（完成）/ `FAILED`（失败）/ `CANCELLED`（取消）。

#### `JobState` 状态机

状态转换规则：`QUEUED → RUNNING → COMPLETED/FAILED`；`QUEUED/RUNNING → CANCELLED`；终态不可再转换。非法转换 raise `RuntimeError`。

方法：`can_transition(from, to)` / `is_terminal(status)` / `assert_transition(from, to)`。

#### `Stage` 数据类

阶段定义（字段：`stage_id`/`name`/`slug`/`description`/`ipkiss_step`/`inputs_spec`/`outputs_spec`/`depends_on`/`execute_fn`）。

#### `STANDARD_STAGES` — 10 个标准化阶段

| ID | 名称 | slug | IPKISS 步骤 | 依赖 |
|----|------|------|------------|------|
| 1 | PDK 器件目录 | `stage1_pdk` | 器件设计 | — |
| 2 | 电路规格定义 | `stage2_circuit` | 线路设计 | [1] |
| 3 | AI 布局 | `stage3_placement` | 线路设计 | [2] |
| 4 | 智能布线 | `stage4_routing` | 线路设计 | [3] |
| 5 | S 参数仿真 | `stage5_simulation` | 设计验证 | [4] |
| 6 | DRC/LVS 验证 | `stage6_drc_lvs` | 设计验证 | [4] |
| 7 | GDS 导出 | `stage7_gds` | 流片准备 | [4] |
| 8 | 光电协同 | `stage8_opto_electrical` | 设计验证 | [3] |
| 9 | 量子光子验证 | `stage9_quantum` | 设计验证 | [2] |
| 10 | 逆向设计 | `stage10_inverse` | 器件设计 | — |

#### `get_stage(stage_id) -> Stage`

根据 ID 获取阶段定义。**异常**：`ValueError` — 未知阶段 ID。

#### `Recipe` 数据类

作业配方（可序列化的流水线配置）。

| 字段 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `preset_id` | `str` | `"mzi"` | 电路预设 ID |
| `platform` | `str` | `"SOI"` | 工艺平台（SOI/SiN/InP/LNOI） |
| `placement_algo` | `str` | `"analytical"` | 布局算法（rl/analytical/ppo_gnn） |
| `router_algo` | `str` | `"curvy"` | 布线算法（curvy/diagonal/hybrid） |
| `sim_config` | `SimConfig` | — | 仿真配置 |
| `output_dir` | `str` | `"out/jobs"` | 输出目录 |
| `enabled_stages` | `list[int]` | `[1..10]` | 启用的阶段 ID |
| `canvas_w` | `float` | `1000.0` | 画布宽度 |
| `canvas_h` | `float` | `600.0` | 画布高度 |
| `custom_circuit` | `dict \| None` | `None` | 自定义电路规格 |

序列化方法：`to_dict()` / `to_json()` / `from_dict(d)` / `from_json(s)` / `to_yaml()` / `from_yaml(s)`。

#### `SimConfig` 数据类

| 字段 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `max_iterations` | `int` | `3` | 最大迭代次数 |
| `loss_target_db` | `float` | `5.0` | 目标插损（dB） |
| `use_real_simulator` | `bool` | `False` | 是否使用真实仿真器 |

#### `STAGE_EXECUTORS`（lazy 导出，依赖 polaris-core）

10 阶段执行器映射。每个阶段函数签名：`stageN_xxx(recipe, workspace, prev_outputs) -> dict`。由 `JobScheduler` 按 `recipe.enabled_stages` 顺序调用。

#### 其他 API

- `StageInput` / `StageOutput` / `StageResult` / `StageStatus` — 阶段输入输出与状态
- `Workspace` — 工作空间持久化（含 metadata.json）
- `JobTracker` — 作业追踪
- `JobScheduler` — 作业调度器
- `DesignIntentEngine` / `IntentConfig` — Design Intent 流程引擎
- `DistributedTaskScheduler` / `DistributedConfig` / `TaskStatus` / `TaskState` / `TaskResult` — 分布式任务调度（sequential/threading/asyncio 三后端）
- `IPKISSPCell` / `IPKISSView` / `NetlistView` / `LayoutView` / `CircuitModelView` / `SDLFlow` / `ClosedLoopValidator` / `IPKISSPDKBridge` — IPKISS 兼容流程
- `RLInverseDesigner` / `GANInverseDesigner` / `DiffusionInverseDesigner` — AI 逆向设计
- `PDKDevice` / `PDKDeviceSampler` / `WaveguideSimulator` — PDK 器件采样
- `TrainingPipeline` / `TrainingConfig` / `TrainingResult`（lazy 导出）— 训练流水线

---

### 1.3 polaris-orchestrator — EDA 流程编排入口

> 源码：`modules/orchestrator/src/polaris_orchestrator/__init__.py` · 版本 `5.0.0`
> 文献：OpenROAD https://github.com/The-OpenROAD-Project/OpenROAD · TILOS https://github.com/TILOS-AI-Institute/MacroPlacement · gdsfactory https://gdsfactory.github.io/gdsfactory/ · Hamard OE 2020 https://doi.org/10.1364/OE.391040 · Chrostowski & Hochberg 2015 §10

#### `run_eda_flow(circuit, output_dir, skip_stages=None, strict=False) -> dict`

一键运行完整 PoLaRIS EDA 流程（9 个 stage，对应 14 个子模块）。

顺序执行：PDK 目录 → 电路验证 → AI 布局 → 智能布线 → 仿真验证 → DRC/LVS → GDS 导出 → 逆向设计 → 量子验证。每 stage 用 try/except 捕获异常，失败记录 `error` 但不中断（除非 `strict=True`）。

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `circuit` | `dict` | — | polaris-core 风格 circuit dict |
| `output_dir` | `str` | — | 输出目录路径（不存在则创建） |
| `skip_stages` | `list \| None` | `None` | 跳过的 stage id 列表（如 `[8]` 跳过逆向设计） |
| `strict` | `bool` | `False` | 严格模式，`True` 时首个 stage 失败即 raise |

**返回**：

```python
{
    "stages": [                          # 各 stage 结果列表
        {
            "stage_id": int,
            "name": str,
            "status": "success" | "failed" | "skipped",
            "duration": float,           # 耗时（秒）
            "result": Any,               # stage 结果（JSON 可序列化）
            "error": str | None,         # 错误信息
        },
        ...
    ],
    "n_success": int,                    # 成功 stage 数
    "n_failed": int,                     # 失败 stage 数
    "n_skipped": int,                    # 跳过 stage 数
    "total_duration": float,             # 总耗时（秒）
}
```

**异常**：`RuntimeError` — `strict=True` 且某 stage 失败时，立即 raise 该 stage 的异常（含 stage_id 与 traceback）。

```python
import polaris_core
import polaris_orchestrator

circuit = polaris_core.make_circuit(
    name="MZI",
    devices=[
        polaris_core.make_device("gc1", "grating_coupler", 10, 10,
            [("o1", 0, 5, "east")]),
        polaris_core.make_device("mmi1", "mmi_1x2", 20, 10,
            [("o1", 0, 5, "west"), ("o2", 20, 5, "east")]),
    ],
    connections=[("gc1", "o1", "mmi1", "o1")],
)
result = polaris_orchestrator.run_eda_flow(
    circuit, output_dir="out/mzi_demo", skip_stages=[8]
)
print(f"成功 {result['n_success']}/{len(result['stages'])} stage")
```

> **编排策略 vs R03 fall-back 禁令**：编排层允许 stage 失败继续（`strict=False` 默认），这是编排策略而非业务 fall-back。子模块内部仍禁止 fall-back（上游失败时下游自然 raise）。

---

## 第 2 章：布局（polaris-place）

> 源码：`modules/place/src/polaris_place/__init__.py` · 版本 `5.1.0`
> 文献：DREAMPlace DAC 2019 https://cseweb.ucsd.edu/classes/fa23/cse248-a/papers/placement/dreamplace.pdf · DREAMPlace TCAD 2020 https://arxiv.org/abs/2004.10746 · AlphaChip Nature 2021 https://www.nature.com/articles/s41586-021-03544-w · HPWL Kahng & Lienig IEEE TCAD 2009 https://ieeexplore.ieee.org/document/4685534 · GDSFactory https://gdsfactory.github.io/gdsfactory/ · TILOS https://github.com/TILOS-AI-Institute/MacroPlacement

### `place_circuit(circuit, mode="analytical") -> dict`

对电路执行布局，返回布局结果 dict。

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `circuit` | `dict` | — | polaris-core 风格 circuit dict |
| `mode` | `str` | `"analytical"` | 布局模式：`"analytical"`（DREAMPlace 解析法）/ `"ppo_gnn"`（AlphaChip Edge-GNN + PPO，需 checkpoint） |

**返回**：

```python
{
    "placements": {name: {"x": float, "y": float, "w": float, "h": float}},
    "hpwl": float,              # 半周长线长（μm），越小越好
    "placement_mode": str,      # "analytical" 或 "ppo_gnn"
    "checkpoint_loaded": bool,  # ppo_gnn 模式下是否加载了 checkpoint
}
```

坐标约定：`x, y` 为器件**左下角**坐标（μm），与 `modules/_c_abi/polaris_types.h` 中 `polaris_placement_t` 一致。

**异常**：`RuntimeError` — mode 非法 / circuit 结构非法 / ppo_gnn 无 checkpoint 或 checkpoint 损坏（R03 禁止 fall-back）。

### `compute_hpwl(circuit, placements) -> float`

计算半周长线长 HPWL（Half-Perimeter Wirelength）。

公式：`HPWL = Σ (|x_i - x_j| + |y_i - y_j|)` 对所有连接求和，其中 `(x_i, y_i)` 为器件 i 的**中心**坐标。

| 参数 | 类型 | 说明 |
|------|------|------|
| `circuit` | `dict` | circuit dict（含 connections） |
| `placements` | `dict` | 器件布局结果 `{name: {x, y, w, h}}` |

**返回**：HPWL 值（μm）。

### `render_ascii_layout(circuit, placements, grid_w=40, grid_h=15) -> str`

渲染 ASCII 布局预览。器件字符映射：`G`=grating_coupler, `M`=mmi, `W`=waveguide, `P`=phase_shifter, `D`=detector, `?`=未知。

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `circuit` | `dict` | — | circuit dict（含画布尺寸与 devices） |
| `placements` | `dict` | — | 器件布局结果 |
| `grid_w` | `int` | `40` | 网格宽度（字符数） |
| `grid_h` | `int` | `15` | 网格高度（字符数） |

**返回**：ASCII 布局预览字符串（含标题与图例）。

**异常**：`RuntimeError` — 画布尺寸非正。

```python
import polaris_core, polaris_place

circuit = polaris_core.make_circuit(
    name="MZI", devices=[...], connections=[...]
)
result = polaris_place.place_circuit(circuit, mode="analytical")
print(polaris_place.render_ascii_layout(circuit, result["placements"]))
print(f"HPWL = {result['hpwl']:.1f} μm")
```

### 其他 API

- `AnalyticalConfig` — 解析法布局配置 dataclass
- `place_analytical(circuit)` — 解析法布局内部入口
- `place_ppo_gnn(circuit)` — PPO+GNN AI 布局入口（无 checkpoint raise）
- 子模块：`polaris_place.metrics`（HPWL/密度梯度/Tarjan SCC/拓扑深度）/ `polaris_place.legalize`（FFDH 合法化）/ `polaris_place.align`（端口对齐）/ `polaris_place.residual`（残余违规修复）

---

## 第 3 章：布线（polaris-route / polaris-router-advanced）

### 3.1 polaris-route — 智能布线

> 源码：`modules/route/src/polaris_route/__init__.py` · 版本 `5.0.0`
> 文献：LiDAR ISPD'25 https://dl.acm.org/doi/pdf/10.1145/3698364.3705355 · LiDAR 2.0 TCAD 2025 https://scopex-asu.github.io/files/publications/PD_TCAD2025_LiDARv2.pdf · SiEPIC EBeam PDK https://github.com/SiEPIC/SiEPIC_EBeam_PDK · Soref 1993 IEEE https://ieeexplore.ieee.org/document/1148303 · Klauss OE 2018 https://doi.org/10.1364/OE.26.029637 · A* 算法 https://en.wikipedia.org/wiki/A*_search_algorithm

#### `route_circuit(circuit, placements, mode="curvy") -> dict`

对已布局电路执行智能布线，返回布线结果 dict。

对电路每条连接 `(dev1.port1 → dev2.port2)`：查找器件/端口坐标 → `CurvyRouter` 生成 S-bend 曲线波导 → 统计弯曲/交叉/损耗。

损耗模型（R02）：
- 路径级 `loss_db` = 波导损耗(传播+弯曲+交叉) + 终点器件(dev2)插入损耗
- 电路级 `total_loss_db` = sum(所有波导损耗) + sum(所有器件插入损耗去重)
- 传播损耗 3.0 dB/cm（Soref 1993 SOI 上界），单弯 0.05 dB，单次交叉 0.3 dB（SiEPIC EBeam PDK）

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `circuit` | `dict` | — | polaris-core 风格 circuit dict |
| `placements` | `dict` | — | polaris-place 输出 `{name: {x, y, w, h}}` |
| `mode` | `str` | `"curvy"` | 布线模式（目前支持 `"curvy"`） |

**返回**：

```python
{
    "paths": [
        {
            "dev1": str, "port1": str, "dev2": str, "port2": str,
            "points": [[x, y], ...],   # 路径点序列（μm）
            "loss_db": float,          # 路径损耗（dB）
            "n_bends": int,            # 弯曲数
            "n_crossings": int,        # 交叉数
        },
        ...
    ],
    "total_loss_db": float,             # 电路级总损耗（dB）
    "n_crossings": int,                 # 交叉对数（去重）
    "n_bends": int,                     # 总弯曲数
    "router_type": "curvy",
}
```

**异常**：`RuntimeError` — mode 非法 / circuit/placements 结构非法 / 端口未找到 / 连接引用的器件不在 placements 中。

#### `compute_path_loss(points, loss_db_cm=3.0) -> float`

计算波导路径损耗（传播损耗 + 弯曲损耗）。

公式：`loss_db = propagation + n_bends * 0.05`，其中传播损耗 = `loss_db_cm × 路径长度(μm) / 1e4`。

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `points` | `list` | — | 路径点序列 `[[x, y], ...]`（μm） |
| `loss_db_cm` | `float` | `3.0` | 传播损耗系数（dB/cm），SOI 波导上界 |

**返回**：路径总损耗（dB）。

**异常**：`RuntimeError` — `loss_db_cm` 为负。

#### `bend_compensate(circuit, placements, route_result) -> tuple`

弯曲波导补偿后处理：检测 `PORT_ALIGNMENT` 端口偏差（dx>10μm 且 dy>10μm）的连接，自动调整下游器件位置使端口对齐。

**返回**：`(new_placements, new_route_result)`。

#### 其他 API

- `CurvyRouter` — 曲线波导布线器类
- `CurvyRouteConfig` / `CurveType` — 布线配置与曲线类型枚举
- `count_bends(points)` / `count_crossings(path1, path2)` / `path_length(points)` / `s_bend_bezier(...)` / `generate_euler_bend(...)` / `generate_arc_bend(...)`
- 物理常量：`PROPAGATION_LOSS_DB_CM=3.0` / `BEND_LOSS_DB=0.05` / `CROSSING_LOSS_DB=0.3`

### 3.2 polaris-router-advanced — 高级布线

> 源码：`modules/router_advanced/src/polaris_router_advanced/__init__.py` · 版本 `5.0.0`
> 文献：JPS Harabor 2011 https://cdn.aaai.org/ojs/7994/7994-13-11522-1-2-20201228.pdf · LiDAR ISPD'25 https://dl.acm.org/doi/pdf/10.1145/3698364.3705355 · Dubins 1957 https://www.jstor.org/stable/2372560 · Synopsys OptoDesigner https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner/advanced-connectors-module.html · gdsfactory routing https://gdsfactory.github.io/gdsfactory/notebooks/04_routing.html · A* Hart 1968 https://ieeexplore.ieee.org/document/4082128

17 种高级光波导布线算法。主要 API：

| API | 说明 |
|-----|------|
| `JPSRouter` | JPS 跳点搜索布线器（Harabor 2011） |
| `AllAngleRouter` | 任意角度欧拉弯曲布线 |
| `route_bundle(...)` / `route_bundle_path_length_match(...)` | Bundle 并行等长布线 |
| `dubins_path(...)` | Dubins 路径生成 |
| `auto_taper(...)` | 自动锥形过渡 |
| `DiagonalGridRouter` | 对角布线 |
| `MultiLayerRouter` / `MultiLayerRouteResult` / `LayerSpec` / `OTVSpec` | 多层跨层布线（OTV via） |
| `HybridRouter` / `HybridRouterConfig` | 混合多波导型布线（strip/rib） |
| `OptoElectricalRouter` / `OptoElectricalResult` | 光电协同布线 |
| `route_with_rip_reroute(...)` / `RipRerouteConfig` | RIP 撕裂重布 |
| `EulerBend` / `LengthDefinedConnector` / `PhaseMatchedRouter` / `RFGSGRouter` / `BusRouter` / `HighOrderBezierConnector` | Advanced Connectors（OptoDesigner 对齐） |
| `CurvyAStarRouter` / `CurvyAStarConfig` | CurvyA* 曲线感知 A* |
| `OptoDesignerAutorouter` / `AdaptiveCrossingInserter` / `CongestionAwareNetOrdering` | OptoDesigner Autorouting |
| `DRVFreeValidator` | DRV-free 验证器 |
| `CommercialRouter` / `CommercialRouterConfig` | Commercial 综合策略布线 |
| `GdsfactoryStyleRouter` | GdsfactoryStyle 风格布线 |
| `GlobalRouter` / `run_global_routing(...)` | Global GCell 全局布线 |
| `RoutingEnv` / `RoutingEnvConfig` / `RoutingState` | RL 布线环境（Gymnasium 接口） |

---

## 第 4 章：物理求解器（polaris-fdtd / fde / fdfd / eme / bpm / circuit / sparam）

### 4.1 polaris-fdtd — 时域有限差分

> 源码：`modules/fdtd/src/polaris_fdtd/__init__.py` · 版本 `5.0.0`
> 文献：Yee 1966 IEEE TAP https://doi.org/10.1109/TAP.1966.1138693 · Gedney 1996 IEEE TAP https://doi.org/10.1109/8.546249 · Taflove & Hagness 2005 · Soref 1993 IEEE JQE https://ieeexplore.ieee.org/document/1148303 · NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/ · Mahau 2024 arXiv:2412.12360 https://arxiv.org/abs/2412.12360 · Hughes 2018 ACS Photonics https://arxiv.org/abs/1811.01255 · Lumerical FDTD https://optics.ansys.com/hc/en-us/articles/360034914833

#### `simulate_waveguide_fdtd(dx_um=0.05, n_steps=2000, wavelength_um=1.55, nx=32, ny=24, nz=20) -> dict`

3D FDTD 波导全波仿真。构建硅波导（Si 芯 eps_r=12.08 / SiO₂ 包层 eps_r=2.085）→ YeeGrid3D + GedneyPML 4 层 → 高斯脉冲源 + jax.lax.scan 时间步进 → 双监视器比值法提取传输率。

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `dx_um` | `float` | `0.05` | 网格步长（μm） |
| `n_steps` | `int` | `2000` | 时间步数 |
| `wavelength_um` | `float` | `1.55` | 波长（μm） |
| `nx`/`ny`/`nz` | `int` | `32`/`24`/`20` | 网格数 |

**返回**：`dict{transmission_db, T_fdtd, fdtd_duration_s, n_steps, dx_um, pml_enabled}`。

**异常**：`RuntimeError` — JAX 不可用或仿真结果为 NaN（R03 禁止 fall-back）。

#### `simulate_mmi_fdtd(dx_um=0.05, n_steps=2000, wavelength_um=1.55) -> dict`

MMI 多模干涉 FDTD 仿真。

**返回**：`dict{split_ratio, T_fdtd, transmission_db, fdtd_duration_s, ...}`。

#### 底层内核

- `YeeGrid3D(nx, ny, nz, dx, dy, dz, epsilon_r=None, mu_r=None)` — 3D Yee 网格
- `GedneyPML(grid, n_layers=8, sigma_ratio=1.0, m=3, eps_r_bg=None)` — Gedney PML 吸收边界
- `DifferentiableFDTD(grid, pml=None, dt=None, eps_r_bg=None)` — JAX 可微 FDTD 内核
- 物理常量：`C0`/`EPS0`/`MU0`/`SOI_N_SI=3.476`/`SOI_N_SIO2=1.444`/`SOI_EPS_R_SI=12.08`/`SOI_EPS_R_SIO2=2.085`/`CFL_SAFETY`

### 4.2 polaris-fde — 频域本征模

> 源码：`modules/fde/src/polaris_fde/__init__.py` · 版本 `5.0.0`
> 文献：Smit & van Dam 1996 JLT https://opg.optica.org/jlt/abstract.cfm?uri=jlt-14-7-1746 · Silvester & Ferrari 1996 · Soref 1993 https://ieeexplore.ieee.org/document/1148303 · Bogaerts 2012 https://onlinelibrary.wiley.com/doi/10.1002/lpor.201100017 · scipy eigsh https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html · Lumerical MODE https://optics.ansys.com/hc/en-us/articles/360034902413 · NIST CODATA 2018

#### `solve_modes(width_um=0.5, height_um=0.22, wavelength_um=1.55, n_core=3.476, n_clad=1.444, n_modes=4, dx_um=0.02, pad_um=1.0) -> dict`

2D 有限差分本征模求解器。求解标量 Helmholtz 方程 `∇²E + k₀²n²(x,y)E = β²E`，`scipy.sparse.linalg.eigsh` 求前 n_modes 个最大代数特征值，`n_eff = sqrt(eigenvalue) / k₀`。

导模严格过滤三重判据：(1) β² 范围 `k₀²n_clad² < β² < k₀²n_core²`；(2) Confinement factor Γ > 0.6；(3) V 参数 < 2.405 时强制单模。

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `width_um` | `float` | `0.5` | 波导宽度（μm） |
| `height_um` | `float` | `0.22` | 波导高度（μm，220nm SOI） |
| `wavelength_um` | `float` | `1.55` | 波长（μm） |
| `n_core` | `float` | `3.476` | 芯区折射率（Si） |
| `n_clad` | `float` | `1.444` | 包层折射率（SiO₂） |
| `n_modes` | `int` | `4` | 求解的模式数 |
| `dx_um` | `float` | `0.02` | 网格步长（μm） |
| `pad_um` | `float` | `1.0` | 包层填充（μm） |

**返回**：`dict{modes: [{neff, field_2d, beta, confinement}], n_modes, wavelength_um, grid_info, physics}`。

#### 其他 API

- `build_index_profile(width_um, height_um, n_core, n_clad, dx_um, pad_um)` — 构建 2D 折射率分布
- `build_laplacian_operator(nx, ny, dx, dy)` — 构建 5 点拉普拉斯稀疏算子
- `compute_v_parameter(width_um, wavelength_um, n_core, n_clad)` — 计算 V 参数
- `confinement_factor(field_2d, core_mask)` — 计算 confinement factor
- 常量：`C0` / `CONFINEMENT_THRESHOLD=0.6` / `V_CUTOFF_SINGLE_MODE=2.405`

### 4.3 polaris-fdfd — 频域有限差分

> 源码：`modules/fdfd/src/polaris_fdfd/__init__.py` · 版本 `5.0.0`
> 文献：Taflove & Hagness 2005 · Shin & Fan OE 2014 https://opg.optica.org/oe/fulltext.cfm?uri=oe-22-5-5230 · scipy spsolve https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.spsolve.html · Lumerical FDFD https://optics.ansys.com/hc/en-us/articles/360034902393 · Soref 1993

#### `solve_fdfd(width_um=0.5, length_um=10.0, wavelength_um=1.55, n_core=3.476, n_clad=1.444, dx_um=0.05, pad_um=1.5) -> dict`

频域 Helmholtz 方程稀疏矩阵求解。构建 2D 网格 5 点拉普拉斯算子 + 折射率项 `A = ∇² + diag(k₀²n²)`，高斯线源 `b`，`scipy.sparse.linalg.spsolve` 求解 `A·E = b`。

**返回**：`dict{field_2d, transmission_db, n_grid, ...}`。

#### 其他 API：`build_helmholtz_operator(...)` / `build_line_source(...)` / 常量 `C0`

### 4.4 polaris-eme — 本征模展开

> 源码：`modules/eme/src/polaris_eme/__init__.py` · 版本 `5.0.0`
> 文献：Smit & van Dam 1996 https://opg.optica.org/jlt/abstract.cfm?uri=jlt-14-7-1746 · Lumerical EME https://optics.ansys.com/hc/en-us/articles/360034902433 · Bienstman 2001 https://www.photonics.intec.ugent.be/publications/PhD_Bienstman.pdf · Sztefanka 1993 https://ieeexplore.ieee.org/document/247559 · scipy eigsh

#### `solve_eme(sections, wavelength_um=1.55, n_modes_per_section=2) -> dict`

基于本征模展开的传播仿真。将结构沿 z 切片，每段求解本地 slab 本征模，界面用模式匹配（重叠积分）计算透射/反射，段内用 `exp(j·β·L)` 传播，Redheffer 星积级联所有段 S 矩阵。

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `sections` | `list` | — | 段列表 `[{width_um, length_um, n_core, n_clad}, ...]` |
| `wavelength_um` | `float` | `1.55` | 波长（μm） |
| `n_modes_per_section` | `int` | `2` | 每段模式数 |

**返回**：`dict{transmission, transmission_db, reflection, s_matrix, sections_info}`。

#### 其他 API：`solve_slab_modes(...)` / `compute_overlap_1d(...)` / `propagate_phase(...)` / `redheffer_star(...)`

### 4.5 polaris-bpm — 光束传播法

> 源码：`modules/bpm/src/polaris_bpm/__init__.py` · 版本 `5.0.0`
> 文献：Feit & Fleck 1978 Appl. Opt. https://opg.optica.org/ao/abstract.cfm?uri=ao-17-24-3990 · Crank & Nicolson 1947 · Lumerical varFDTD https://optics.ansys.com/hc/en-us/articles/360034902433 · scipy solve_banded https://docs.scipy.org/doc/scipy/reference/generated/scipy.linalg.solve_banded.html · Chung & Dagli 1990 IEEE JQE https://ieeexplore.ieee.org/document/59635 · Hadley 1992 Opt. Lett. https://opg.optica.org/ol/abstract.cfm?uri=ol-17-10-726

#### `solve_bpm(width_um=0.5, length_um=50.0, wavelength_um=1.55, n_core=3.476, n_clad=1.444, dz_um=0.1, dx_um=0.01, pad_um=2.0) -> dict`

Crank-Nicolson 隐式格式抛物波动方程求解。沿 z 步进，每步求解三对角线性系统 `(I - dz·H/2) E^{n+1} = (I + dz·H/2) E^n`，无条件稳定。

**返回**：`dict{field_z, transmission_db, n_steps, grid_info, ...}`。

#### 其他 API：`build_cn_matrices(...)` / `gaussian_source(...)` / `build_loss_profile(...)` / 常量 `C0`/`LOSS_DB_PER_CM_SI`/`CAP_STRENGTH`/`CAP_FRACTION`

### 4.6 polaris-circuit — 电路级仿真

> 源码：`modules/circuit/src/polaris_circuit/__init__.py` · 版本 `5.0.0`
> 文献：Simphony Pflüger 2021 https://arxiv.org/abs/2009.05146 · Filipsson 1978 https://doi.org/10.1109/EUMA.1978.332681 · MNA Ho/Ruehli/Brennan 1974 https://ieeexplore.ieee.org/document/1084079 · Mason 1956 https://ieeexplore.ieee.org/document/4052034 · Yee 1966 https://ieeexplore.ieee.org/document/1138693 · Berenger 1994 https://doi.org/10.1006/jcph.1994.1159 · TLLM Lowery 1987 https://digital-library.theiet.org/doi/abs/10.1049/ip-j-1.1987.0062 · ITU-T G.977 https://www.itu.int/rec/T-REC-G.977 · Golub & Van Loan 2013 · Chrostowski & Hochberg 2015

#### 基础器件 S 参数模型

| API | 签名 | 说明 |
|-----|------|------|
| `waveguide_s` | `(wavelength_um, length_um, neff=2.4, loss_db_cm=3.0) -> dict` | 波导 S 参数：`S = exp(-α·L/2 + j·2π·neff·L/λ)` |
| `mmi_1x2_s` | `(wavelength_um, insertion_loss_db=0.4) -> dict` | MMI 1×2：`sqrt(10^(-il/10)/2)·exp(j·π/2)` |
| `mmi_2x2_s` | `(wavelength_um, insertion_loss_db=0.5) -> dict` | MMI 2×2 |
| `grating_coupler_s` | `(wavelength_um, peak_wl=1.55, bandwidth_3db=0.04, insertion_loss_db=1.9) -> dict` | 光栅耦合器：高斯波长响应 |
| `ring_resonator_s` | `(...) -> dict` | 环形谐振器 |
| `directional_coupler_s` | `(...) -> dict` | 定向耦合器 |
| `y_branch_s` | `(...) -> dict` | Y 分支 |
| `crossing_s` | `(...) -> dict` | 波导交叉 |
| `terminator_s` | `(...) -> dict` | 终端器 |
| `phase_shifter_s` | `(...) -> dict` | 相移器 |

#### `cascade_circuit(...) -> dict`

子网络增长算法级联器件 S 参数（Filipsson 1978）。*创新*：子网络增长分母趋零检测，当 `|1-S_AB·S_BA|<1e-15` 时告警退出（区别于 SAX 静默返回）。

#### `CircuitSimulator` / `WavelengthRange` / `default_models` / `group_delay`

频域电路仿真器。群延迟 `τ_g = dφ/dω`（中心差分）。

#### MNA SPICE API

| API | 说明 |
|-----|------|
| `MNACircuit` | MNA 电路描述（节点 + R/C/L/V/I/D 元件） |
| `MNASolver` | MNA 求解器（DC + 后向欧拉瞬态） |
| `MNADCResult` | DC 结果 `{node_voltages, vsource_currents}` |
| `MNATransientResult` | 瞬态结果 `{time, node_voltages, vsource_currents}` |
| `run_mna_spice(...)` | MNA SPICE 仿真入口 |

#### 系统级 API

- `SignalFlowGraph` — Mason 信号流图增益公式
- `TLLMLaser` — TLLM 速率方程（RK4）
- `TimeDomainSimulator` / `HybridSimulator` / `OpticalLink` — 系统级仿真
- `BerEvaluator` — BER 评估（Q-factor 法 + OSNR→BER，ITU-T G.977）
- `to_time_domain(...)` — *创新* 频域→时域一键转换（IFFT）
- `simulate_system_level(...)` — 系统级仿真入口

#### 时域电路 API

- `YeeGrid` / `PMLBoundary` / `FDTDSimulator` — 2D TMz Yee 网格 + PML
- `NonlinearModel` — Kerr/TPA 非线性模型
- `TimeDomainCircuitSimulator` / `run_time_domain_circuit(...)` — 时域电路仿真

#### 类型与常量

- `SDict` = `dict[tuple[str, str], np.ndarray]` — S 参数字典
- `SArray` = `np.ndarray` — S 参数数组
- `ModelFunc` = `Callable[..., SDict]` — 器件模型函数
- `Term` / `Connector` / `Subcircuit` — SPICE 风格子电路构建
- `RingParams` — 环形谐振器参数 dataclass
- `compute_condition_number(...)` / `COND_NUM_FG_THRESHOLD` / `COND_NUM_KLU_THRESHOLD` — 条件数诊断
- 常量：`SPEED_OF_LIGHT` / `C0` / `EPS0` / `MU0`

### 4.7 polaris-sparam — 频域 S 参数

> 源码：`modules/sparam/src/polaris_sparam/__init__.py` · 版本 `5.0.0`
> 文献：Simphony https://simphonyphotonics.readthedocs.io/ · SiPANN https://sipann.readthedocs.io/ · SiEPIC EBeam PDK https://github.com/SiEPIC/SiEPIC_EBeam_PDK · Saleh & Teich 2019 §4.4 · Soldano & Pennings 1995 https://ieeexplore.ieee.org/document/374358 · Clements et al. Optica 2016 https://opg.optica.org/optica/fulltext.cfm?uri=optica-3-12-1460 · Chrostowski & Hochberg 2015

#### `simulate_mzi_sparam(wavelength_nm=None) -> dict`

MZI S 参数扫描。公式：`T_bar = R²+T²+2RT·cos(2π·neff·ΔL/λ)`（Saleh & Teich 2019 §4.4）。

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `wavelength_nm` | `list \| None` | `None` | 波长数组（nm），None 默认 1500-1600nm 101 点 |

**返回**：`dict{resonant_wavelength_nm, extinction_ratio_db, ...}`。

#### `compute_clements_unitary(n_modes=4) -> dict`

Clements 酉矩阵分解（Clements et al. Optica 2016）。交替层左乘分束器构成酉矩阵。

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `n_modes` | `int` | `4` | 模式数 |

**返回**：`dict{unitary, unitarity_error, is_unitary}`。

#### 其他 API

- `waveguide_s(wavelength_um, length_um, neff=2.4, loss_db_cm=3.0) -> dict`
- `mmi_1x2_s(wavelength_um, insertion_loss_db=0.4) -> dict`
- `mmi_2x2_s(wavelength_um, insertion_loss_db=0.5) -> dict`
- `grating_coupler_s(wavelength_um, peak_wl=1.55, bandwidth_3db=0.04, insertion_loss_db=1.9) -> dict`
- `ring_resonator_s(...) -> dict` / `directional_coupler_s(...) -> dict`
- `port_key(out_port, in_port) -> str` — 端口对 key 生成

---

## 第 5 章：验证（polaris-drc / polaris-lvs / polaris-verify-advanced）

### 5.1 polaris-drc — DRC 设计规则检查

> 源码：`modules/drc/src/polaris_drc/__init__.py` · 版本 `5.0.0`
> 文献：SiEPIC EBeam PDK DRC runset https://github.com/SiEPIC/SiEPIC_EBeam_PDK · Chrostowski & Hochberg 2015 p.353 · KLayout DRC https://www.klayout.org/doc-qt5/manual/drc_runsets.html · OpenDRC DAC 2023 https://doi.org/10.1109/DAC56929.2023.10247734 · Berg 2014 Computational Geometry https://doi.org/10.1007/978-3-540-77974-2 · Ericson RTCD 2005 https://realtimecollisiondetection.net/

#### `run_drc(circuit, placements, bend_compensate=True) -> dict`

对已布局电路执行 18 条 DRC 设计规则检查。

18 条规则（12 SiEPIC EBeam PDK 基础 + 6 P0 波导级）：`MIN_SPACING` 1.0μm / `MIN_WIDTH` 0.5μm / `MIN_HEIGHT` 0.4μm / `MIN_AREA` 0.1μm² / `BOUNDARY` / `NO_OVERLAP` / `PORT_ALIGNMENT` 10μm / `PORT_DIRECTION` / `PORT_CONNECTIVITY` / `PORT_FACING` / `DENSITY_MAX` 80% / `DENSITY_MIN` 0.01% / `BEND_RADIUS_MIN` 5.0μm / `WAVEGUIDE_WIDTH_MATCH` / `MIN_NOTCH` 0.1μm / `WAVEGUIDE_MANHATTAN` / `ENCLOSED_AREA_MIN` 0.01μm² / `CROSSING_ANGULAR` 90°。

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `circuit` | `dict` | — | polaris-core 风格 circuit dict |
| `placements` | `dict` | — | polaris-place 输出 `{name: {x, y, w, h}}` |
| `bend_compensate` | `bool` | `True` | 是否启用波导弯曲补偿 |

**返回**：

```python
{
    "n_rules": 18,                    # 规则总数
    "n_violations": int,              # 违规总数
    "n_passed": int,                  # 通过规则数
    "pass_rate": float,               # 通过率 [0, 1]，1.0=DRC clean
    "violations": [                   # 违规清单
        {"rule_name": str, "severity": str, "message": str,
         "device_name": str, "location": [x, y]},
        ...
    ],
}
```

**异常**：`RuntimeError` — circuit/placements 结构非法。

> *创新*（弯曲补偿）：SiEPIC PDK `PORT_FACING` 规则假设直连，但光子电路实际可通过波导弯曲补偿任意方向组合。

#### 其他 API

- `DRCEngine` / `DRCRule` / `DRCViolation` / `CheckType` — DRC 引擎与规则类
- `DEFAULT_DRC_RULES` — 默认 18 条规则
- `run_drc_rules(rules, circuit, placements)` — 自定义规则集 DRC

### 5.2 polaris-lvs — LVS 网表一致性比对

> 源码：`modules/lvs/src/polaris_lvs/__init__.py` · 版本 `5.0.0`
> 文献：KLayout LVS https://www.klayout.org/doc-qt5/manual/lvs.html · SiEPIC EBeam PDK DEVREC https://github.com/SiEPIC/SiEPIC_EBeam_PDK · Chrostowski & Hochberg 2015 p.353 · gdsfactory PDK https://gdsfactory.github.io/gdsfactory/notebooks/09_pdk_import.html · Luceda IPKISS https://www.lucedaphotonics.com/en/products/ipkiss · Calibre nmLVS https://eda.sw.siemens.com/en-US/calibre/

#### `run_lvs(circuit, netlist=None) -> dict`

对电路执行 LVS 网表比对。

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `circuit` | `dict` | — | polaris-core 风格 circuit dict |
| `netlist` | `dict \| None` | `None` | 提取网表，None 时用 circuit 自身派生网表（自比对） |

**返回**：

```python
{
    "is_consistent": bool,           # 是否完全一致
    "n_mismatches": int,             # 不匹配项数
    "mismatches": [                  # 不匹配详情
        {"type": str, "message": str, "device_name": str, "net_name": str},
        ...
    ],
    "n_devices": int,                # 参考网表器件数
    "n_connections": int,            # 参考网表连接数
}
```

`is_consistent=True` 表示版图与原理图拓扑一致，可签核流片。

#### 其他 API：`Netlist` / `LVSMismatch` / `LVSMismatchType` / `extract_netlist(circuit)` / `compare_netlists(ref, ext)` / `run_lvs_check(circuit, netlist)`

### 5.3 polaris-verify-advanced — 高级验证

> 源码：`modules/verify_advanced/src/polaris_verify_advanced/__init__.py` · 版本 `1.0.0`
> 文献：OpenDRC DAC 2023 https://doi.org/10.1109/DAC56929.2023.10247734 · Calibre eqDRC https://blogs.sw.siemens.com/calibre/2015/11/17/ · Calibre xACT https://eda.sw.siemens.com/en-US/calibre/ · Calibre LFD SPIE 2006 https://www.spiedigitallibrary.org/conference-proceedings-of-spie/6349/63492Z/ · SiEPIC EBeam PDK https://github.com/SiEPIC/SiEPIC_EBeam_PDK · KLayout DRC https://www.klayout.de/doc-qt5/manual/drc.html · Chrostowski & Hochberg 2015

主要 API 分类：

**图同构 LVS**（VF2 算法）：`run_graph_lvs(...)` / `GraphIsomorphismLVSComparer` / `PhotonicsNetlist` / `PhotonicsLVSReport` / `verify_port_orientation(...)` / `verify_waveguide_length(...)`

**层次化 LVS**（≥3 层递归比对）：`run_hierarchical_lvs(...)` / `HierarchicalLVS` / `HierarchicalLVSReport` / `LevelMatchResult`

**LVS 进阶**：`match_devices_with_tolerance(...)` / `extract_connectivity(...)` / `generate_structured_error_report(...)`

**方程驱动 DRC**（eqDRC，对齐 Calibre）：`EqDRCEngine` / `EqDRCRule` / `EqDRCViolation` / `FoundryDRCCertifier` / `FoundryDRCRunset`

**KLayout DRC 桥接**：`run_klayout_drc(...)` / `KLayoutDRCRunner` / `SIEPIC_EBEAM_DRC_RUNSET` / `DRCResult` / `DRCRule`

**层次化 DRC**（BVH 加速）：`run_hierarchical_drc(...)` / `HierarchicalDRC` / `BVH` / `BVHNode`

**Tiled/Deep 模式 DRC**：`run_tiled_drc(...)` / `run_deep_drc(...)` / `TiledDRC` / `DeepDRC`

**Calibre xACT 寄生提取**：`ParasiticExtractor` / `ParasiticNet` / `ParasiticElement` / `LayerSpec` / `Layout`

**Calibre LFD 光刻友好设计**：`LithoFriendlyChecker` / `LithoReport` / `LithoRule` / `LithoHotspot`

**曲线感知 DRC**（18 类规则 + 8 类扩展）：`CurvilinearDRCEngine` / `CurvilinearDRCRule` / `DRCViolation18`

**DRC 规则集预设**：`get_preset_ruleset(name)` / `list_preset_rulesets()` / `validate_ruleset(rs)` / `SIEPIC_EBEAM_SOI_RULESET` / `SIEPIC_EBEAM_SIN_RULESET` / `GENERIC_CONSERVATIVE_RULESET`

---

## 第 6 章：输出 IO（polaris-gdsio / polaris-gds-tools / polaris-pdk / polaris-pdk-advanced）

### 6.1 polaris-gdsio — GDSII 导入导出

> 源码：`modules/gdsio/src/polaris_gdsio/__init__.py` · 版本 `5.1.0`
> 文献：klayout Layout Database API https://www.klayout.org/downloads/master/doc-qt4/programming/database_api.html · gdsfactory write_gds https://gdsfactory.github.io/gdsfactory/api.html · GDSII 格式 https://en.wikipedia.org/wiki/GDS_File · GDSII 层次结构 https://gdspy.readthedocs.io/en/master/gettingstarted.html · gdsfactory PDK import https://sequoiap.github.io/gdsfactory/notebooks/09_pdk_import.html · KLayout CellInstArray https://www.klayout.de/doc-qt5/code/class_CellInstArray.html

#### `export_gds(circuit, output_path) -> dict`

将 circuit dict 导出为 GDSII 文件（klayout.db API，dbu=0.001μm=1nm）。

| 参数 | 类型 | 说明 |
|------|------|------|
| `circuit` | `dict` | polaris-core 风格 circuit dict |
| `output_path` | `str` | GDSII 输出文件路径 |

**返回**：`dict{path, file_size_bytes, n_structures, n_layers, loadable}`。`loadable=True` 表示可被 klayout 重新读入。

层映射：`(1,0)=WG` / `(2,0)=SLAB150` / `(3,0)=SLAB90` / `(66,0)=TEXT` / `(68,0)=DEVREC` / `(69,0)=PIN` / `(99,0)=PORT`。

#### `import_gds(gds_path) -> dict`

读取 GDSII 文件，返回层信息与 bbox。

| 参数 | 类型 | 说明 |
|------|------|------|
| `gds_path` | `str` | GDSII 文件路径 |

**返回**：`dict{n_structures, n_layers, layers: [{gds_layer, gds_datatype, polaris_name, n_shapes}], bbox_um: {xmin, ymin, xmax, ymax}}`。

### 6.2 polaris-gds-tools — GDSII 工程化工具与多格式 IO

> 源码：`modules/gds_tools/src/polaris_gds_tools/__init__.py` · 版本 `5.1.0`
> 文献：GDSII 规范 https://en.wikipedia.org/wiki/GDS_File · KLayout API https://www.klayout.de/doc.html · SiEPIC EBeam PDK https://github.com/SiEPIC/SiEPIC_EBeam_PDK · ODB++ http://www.odb-sa.com/ · OpenAccess https://si2.org/openaccess/ · Gerber Rev 2024.06 https://www.ucamco.com/ · DXF https://images.autodesk.com/adskfiles/acad_dxf.pdf · LEF/DEF https://github.com/The-OpenROAD-Project/OpenDB · OASIS https://en.wikipedia.org/wiki/Open_Artwork_System_Interchange_Standard

#### 多格式 IO

- `MultiFormatIO.read(path, fmt)` / `MultiFormatIO.write(layout, path, fmt)` — 统一多格式读写
- `SUPPORTED_FORMATS` = `("cif", "gerber", "dxf", "odb++", "lef_def", "openaccess")`
- `FormatLayout` / `Cell` / `Shape` / `Instance` / `LayerInfo` / `Point` — 统一数据模型
- `layouts_equal(layout1, layout2)` — 浮点容差 1e-6 往返一致性校验

#### GDSII 工程化工具（22 个）

| API | 说明 |
|-----|------|
| `generate_gdsii_statistics(path)` / `generate_statistics_report(path)` | GDSII 统计 |
| `check_gdsii_health(path)` | GDSII 健康检查 |
| `flatten_gdsii(path)` / `generate_flatten_report(path)` | 展平 |
| `clip_gdsii(path, bbox)` / `multi_clip_gdsii(path, bboxes)` | 裁剪 |
| `copy_layer(path, src, dst)` / `delete_layers(path, layers)` / `merge_layers(path, layers)` | 层操作 |
| `merge_gdsii(paths)` | 合并 |
| `scale_gdsii(path, scale)` | 缩放 |
| `analyze_cell_hierarchy(path)` / `detect_circular_references(path)` | 层次分析 |
| `rename_cells(path, mapping)` | 重命名 cell |
| `boolean_operation(path, op)` | 布尔运算 |
| `transform_gdsii_geometry(path, transform)` | 几何变换 |
| `size_layer(path, layer, delta)` | Sizing |
| `compare_gdsii_files(p1, p2)` / `generate_diff_report(p1, p2)` | Diff |
| `check_density_rules(path, rules)` / `compute_density_map(path)` / `compute_layer_density(path)` | 密度分析 |
| `check_grid_alignment(path, grid)` | 网格对齐检查 |
| `extract_edges(path)` / `extract_ports(path)` / `extract_text_labels(path)` | 提取 |
| `analyze_layer_connectivity(path)` / `analyze_cross_layer_connectivity(path)` / `list_isolated_polygons(path)` | 连通性分析 |
| `tapeout_precheck(path)` | Tapeout 预检 |
| `run_batch_pipeline(paths, ops)` | 批量流水线 |
| `check_area(path, min_area)` | 面积检查 |

#### 版图渲染

- `render_layout(layout, congestion=None, options=None)` — 版图渲染
- `export_oasis(layout, path)` — OASIS 导出
- `LayoutRender` / `RenderOptions`

#### SiEPIC GDS 电路解析器

- `load_gds_to_circuit(path)` / `load_gds_to_circuit_spec(path)` / `siepic_to_polaris(path)`

#### 曲线离散化

- `discretize_curve_1nm(curve)` — 1nm 精度离散化
- `discretize_to_gds_path(curve)` — GDS path 离散化
- `bspline_curve(...)` / `catmull_rom_spline(...)`

#### 共享基础设施

- `get_klayout_db()` / `get_default_layer_map()` / `atomic_write_klayout(...)` / `atomic_write_text(...)`

### 6.3 polaris-pdk — PDK 器件库管理

> 源码：`modules/pdk/src/polaris_pdk/__init__.py` · 版本 `5.1.0`
> 文献：SiEPIC EBeam PDK https://github.com/SiEPIC/SiEPIC_EBeam_PDK · Ligentec ANR https://www.ligentec.com/ · Pattern Project / JEPPIX InP https://www.jeppix.eu/ · HyperLight LNOI https://hyperlightphotonics.com/ · Soares 2019 https://doi.org/10.3390/app9081588 · Liu 2025 https://doi.org/10.37188/lam.2025.047

#### `list_platforms() -> list`

列出所有 PDK 平台（4 平台 36 器件）。

**返回**：`list[{platform, foundry, process_node, device_count, device_names}]`。

| 平台 | Foundry | 工艺节点 |
|------|---------|---------|
| SOI | SiEPIC EBeam | 220nm SOI |
| SiN | Ligentec ANR | SiN TriPleX |
| InP | Pattern Project / JEPPIX | InP generic |
| LNOI | HyperLight | X-cut TFLN |

#### `get_device(platform, device_type) -> dict`

获取指定平台指定类型的器件规格。

| 参数 | 类型 | 说明 |
|------|------|------|
| `platform` | `str` | 平台名（SOI/SiN/InP/LNOI） |
| `device_type` | `str` | 器件类型（如 `"strip_waveguide"`） |

**返回**：`dict{platform, device_type, name, category, foundry, process_node, params, source, ports, bbox_um}`。每个器件 params 含 `pdk_reference` 字段标注来源 PDK。

**异常**：`RuntimeError` — 器件未找到（R03 禁止 fall-back）。

#### `list_devices(platform=None) -> list`

列出器件。**返回**：`list[device dict]`。

```python
import polaris_pdk

platforms = polaris_pdk.list_platforms()
dev = polaris_pdk.get_device("SOI", "strip_waveguide")
print(f"neff={dev['params'].get('neff')}, 来源={dev['source']}")
```

### 6.4 polaris-pdk-advanced — 高级 PDK

> 源码：`modules/pdk_advanced/src/polaris_pdk_advanced/__init__.py` · 版本 `5.1.0`
> 文献：gdsfactory https://gdsfactory.github.io/gdsfactory/ · Matres CLEO 2026 · Synopsys OptoDesigner https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner.html · Luceda IPKISS https://www.lucedaphotonics.com/en/products/ipkiss · Fowler PoEAA 2002 https://martinfowler.com/books/eaa.html · Gamma Design Patterns 1994 · Farin CAGD 2002 · PDAflow http://pdaflow.org/ · SiEPIC EBeam PDK · PhIDO arXiv:2508.14123 https://arxiv.org/abs/2508.14123

主要 API 分类：

**基础数据类**：`BoundingBox` / `Device` / `Direction` / `Port` / `Source`

**gdsfactory 互操作**（*创新* 独立注册表+冲突检测）：`PolarisPDK` / `PolarisPDKRegistry` / `PolarisLayerStack` / `PolarisCrossSection` / `convert_layerstack(...)` / `convert_crosssection(...)` / `parse_pic_yaml(...)` / `polaris_to_gdsfactory_component(...)` / `check_gdsfactory_version_compatibility(...)` / `list_gdsfactory_pdks()` / `get_gdsfactory_pdk(name)`

**PCell 多视图参数化**（*创新* Observer Pattern 三视图自动同步）：`polaris_cell` 装饰器 / `PCellMultiView` / `PCellCache` / `TransformMatrix` / `clear_pcell_cache()` / `ai_generate_pcell(...)`（*创新* AI 辅助 PCell 代码生成，PhIDO arXiv:2508.14123）

**YAML PDK 配置**：`parse_pdk_yaml(path)` / `serialize_pdk_yaml(pdk)` / `validate_pdk_yaml(path)` / `build_polaris_pdk_from_yaml(path)` / `build_polaris_layer_stack(...)` / `build_polaris_cross_section(...)` / `PDKYamlConfig` / `YamlLayerSpec` / `YamlLayerLevelSpec` / `YamlSectionSpec` / `YamlCrossSectionSpec` / `YamlCellSpec`

**多 PDK 管理**（Memento + Composite）：`MultiPDKManager` / `PDKMetadata` / `PDKSnapshot`

**OptoDesigner 版图驱动**：`DesignIntent` / `DesignIntentEngine` / `FlexConnector` / `HierarchyDesign` / `PyCell` / `PyCellFactory` / `PDAflowInterop` / `TechnologyRule`

---

## 第 7 章：AI/ML（polaris-nn / polaris-trainer）

### 7.1 polaris-nn — 神经网络与数据 benchmark

> 源码：`modules/nn/src/polaris_nn/__init__.py` · 版本 `5.0.0`
> 文献：PyTorch torch.nn https://pytorch.org/docs/stable/nn.html · Vaswani 2017 NeurIPS https://arxiv.org/abs/1706.03762 · Kingma & Ba 2015 Adam https://arxiv.org/abs/1412.6980 · TILOS https://github.com/TILOS-AI-Institute/MacroPlacement · Apollo https://github.com/ASU-LOPE-Group/Apollo · LiDAR ISPD'25 https://dl.acm.org/doi/10.1145/3698364.3705355 · DREAMPlace https://arxiv.org/abs/2004.10746 · SiEPIC EBeam PDK

#### 神经网络层（torch.nn 风格，基于 polaris_core.Tensor 自动微分）

| API | 说明 |
|-----|------|
| `Module` | 神经网络模块基类 |
| `Linear(in_features, out_features, bias=True)` | 全连接层 |
| `ReLU()` / `Tanh()` / `leaky_relu(x)` | 激活函数 |
| `LayerNorm(features)` | 层归一化 |
| `Sequential(*layers)` | 顺序容器 |
| `Conv2d(in_ch, out_ch, kernel_size)` | 2D 卷积 |
| `MaxPool2d(kernel_size)` | 2D 最大池化 |
| `Dropout(p)` | Dropout |
| `Embedding(num_embeddings, embedding_dim)` | 嵌入层 |
| `ScaledDotProductAttention(...)` | 缩放点积注意力 |
| `MultiHeadAttention(d_model, n_heads)` | 多头注意力 |
| `TransformerBlock(d_model, n_heads, d_ff)` | Transformer 块 |
| `Adam(params, lr)` / `AdamConfig` | Adam 优化器 |

#### 可微函数

`cat(tensors)` / `scatter_add(...)` / `index_select(...)` / `matmul_backward(...)` / `segment_softmax(...)`

#### Benchmark 数据加载器

| API | 说明 |
|-----|------|
| `load_ariane_benchmark()` / `load_tilos_ariane()` | TILOS Ariane benchmark |
| `load_apollo_ptc()` / `load_apollo_ptc_benchmark()` | Apollo PTC benchmark |
| `load_apollo_onoc()` / `load_apollo_onoc_benchmark()` | Apollo oNoC benchmark |
| `load_lidar_benchmark()` / `load_lidar_ptc_benchmark()` / `load_lidar_onoc_benchmark()` | LiDAR ISPD'25 benchmark |

#### 评估器与报告

- `evaluate_benchmark(circuit, method)` / `BenchmarkResult` — 基准评估
- `grid_placement(circuit)` / `placement_by_method(circuit, method)` — 布局方法
- `generate_report(...)` / `generate_grid_report(...)` / `generate_comparison_report(...)` / `run_all_benchmarks()` / `BenchmarkReport` / `ComparisonReport`

#### 历史趋势

- `BenchmarkHistory` / `HistoryTracker` / `HistoryEntry` / `TrendAnalysis`

#### 数据集生成

- `generate_dataset(n)` / `generate_layout(circuit)` — 生成 CircuitSpec 列表
- `STANDARD_DEVICES` — 标准器件集

#### Specs（re-export from polaris_core）

`BenchmarkSource` / `TargetMetric` / `DeviceSpec` / `CircuitSpec` / `Tensor`

### 7.2 polaris-trainer — PPO 训练器

> 源码：`modules/trainer/src/polaris_trainer/__init__.py` · 版本 `5.0.0`
> 文献：Schulman 2017 PPO https://arxiv.org/abs/1707.06347 · Schulman 2015 GAE https://arxiv.org/abs/1506.02438 · AlphaChip Nature 2021 https://www.nature.com/articles/s41586-021-03544-w · AlphaChip Nature 2024 https://www.nature.com/articles/s41586-024-08032-5 · Stable-Baselines3 https://stable-baselines3.readthedocs.io/ · CleanRL https://github.com/vwxyzjn/cleanrl · Loshchilov 2017 SGDR https://arxiv.org/abs/1608.03983 · Roijers 2013 多目标 RL https://arxiv.org/abs/1302.1563 · Deb 2002 NSGA-II https://ieeexplore.ieee.org/document/996017 · Bengio 2009 Curriculum https://dl.acm.org/doi/abs/10.1145/1553374.1553380 · Kingma & Ba 2015 Adam https://arxiv.org/abs/1412.6980

#### PPO 核心

| API | 说明 |
|-----|------|
| `PPOConfig` | PPO 超参数（lr/gamma/gae_lambda/clip_eps/ent_coef/lr_schedule） |
| `ActorCritic` | Actor-Critic 网络 |
| `PPOAgent` | PPO 智能体（含 actor-critic 权重） |
| `RolloutBuffer` / `ReplayBuffer` | 经验回放缓冲（RolloutBuffer 别名） |
| `Transition` / `Minibatch` | 数据结构 |
| `compute_gae(...)` | GAE 优势估计 |

#### 训练循环

| API | 签名 | 说明 |
|-----|------|------|
| `train_ppo` | `(env, config, ...)` | PPO 训练循环 |
| `train_with_env_factory` | `(env_factory, config, ...)` | 环境工厂训练 |
| `load_agent` | `(checkpoint_path)` | 加载训练好的 agent |
| `TrainConfig` | — | 训练循环配置 |

#### R351-R352 高级 RL

- `LargeScalePlacementEnv` / `LargeScalePlacementConfig` — 占用栅格 + 图摘要双轨状态
- `PPOAdvantageOptimizer` / `PPOAdvConfig` — GAE + clipped loss + 熵正则 + 余弦退火

#### R353-R355 多目标/预训练/混合布局

- `MultiObjectiveParetoReward` / `MultiObjectiveRewardConfig` — 面积/时延/损耗/串扰加权 + NSGA-II Pareto
- `PretrainedPolicyLibrary` / `PretrainedPolicyConfig` — 启发式/随机/课程学习 3 种基础策略
- `HybridPlacementAgent` / `HybridPlacementConfig` — fix-then-optimize 手动约束 + RL 自动布局

#### R36 BC 预训练 + 迁移学习

- `pretrain(...)` / `BCPretrainConfig` / `BehaviorCloningModel` — 行为克隆预训练
- `ExpertDemoLoader` — 专家演示加载器
- `load_bc_checkpoint(path)` — 加载 BC checkpoint
- `transfer_learn(...)` / `TransferConfig` / `RoutingPolicyModel` — 迁移学习
- `extract_routing_targets(...)`

#### CPU 多进程并行 rollout

- `collect_rollouts_parallel(...)` / `ParallelRolloutCollector` / `RolloutBatch` / `register_env_factory(name, factory)` / `ENV_FACTORIES`

#### Checkpoint 管理

- `CheckpointManager` / `CIRCUIT_TEMPLATES` / `ALL_PLATFORMS` / `PLATFORM_SOI` / `PLATFORM_SIN` / `PLATFORM_INP` / `PLATFORM_LNOI`

#### D07 增强：日志 + benchmark + 可视化 + 预设

- `TrainingLogger` / `JsonlLogger` / `load_jsonl_log(path)`
- `compute_hpwl(...)` / `compute_overlap_count(...)` / `compute_area_utilization(...)`
- `run_benchmark(...)` / `compare_with_baselines(...)` / `BenchmarkReport` / `BaselineResult` / `save_report(...)`
- `REPLACE_BASELINES` / `DREAMPLACE_BASELINES` / `ALPHACHIP_BASELINES`
- `plot_reward_curve(...)` / `plot_hpwl_convergence(...)` / `plot_training_dashboard(...)` / `save_dashboard(...)`
- `smoke_test_preset()` / `full_ppo_preset()` / `ariane_train_preset()` / `mempool_train_preset()` / `nvdla_train_preset()` / `benchmark_eval_preset()` / `list_presets()` / `get_preset(name)`

---

## 第 8 章：逆向设计（polaris-inverse / polaris-optimizer）

### 8.1 polaris-inverse — Adjoint 逆向设计

> 源码：`modules/inverse/src/polaris_inverse/__init__.py` · 版本 `5.1.0`
> 文献：Yee 1966 IEEE TAP https://doi.org/10.1109/TAP.1966.1138693 · Taflove & Hagness 2005 · Mahau 2024 arXiv:2412.12360 https://arxiv.org/abs/2412.12360 · Polyak 1964 · Jensen & Sigmund 2011 https://doi.org/10.1002/lpor.201000014 · lumopt https://github.com/chriskeraly/lumopt · Gedney 1996 IEEE TAP https://doi.org/10.1109/8.546249 · Hughes 2018 ACS Photonics https://arxiv.org/abs/1811.01255 · Giles & Pierce 2000 SIAM Review · Piggott 2017 Nature Photonics https://doi.org/10.1038/nphoton.2017.102 · Osher & Sethian 1988 JCP https://doi.org/10.1016/0021-9991(88)90002-2 · Bendsøe & Sigmund 2003 Topology Optimization

#### `optimize_waveguide_width(n_iterations=50, learning_rate=0.5) -> dict`

Adjoint 逆向设计：JAX `jax.grad` 自动微分优化波导宽度（*创新*，替代 lumopt 手动伴随方程），heavy-ball 动量优化器（Polyak 1964）+ 梯度裁剪防 NaN。

优化目标：最大化监视器时域信号峰值（正比于目标波长透过率）。网格 24×12×8, dx=200nm，Si 芯(eps_si=12.08) + SiO₂ 包层(eps_bg=2.085)。

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `n_iterations` | `int` | `50` | 优化迭代次数 |
| `learning_rate` | `float` | `0.5` | 学习率（配合动量 0.9） |

**返回**：

```python
{
    "initial_width_nm": float,    # 初始波导半宽度（nm）
    "optimal_width_nm": float,    # 优化后波导半宽度（nm）
    "initial_fom": float,         # 初始 FoM
    "final_fom": float,           # 最终 FoM
    "improvement_db": float,      # FoM 改善量（dB）
    "fom_history": list[float],   # FoM 历史（长度 n_iterations+1）
    "converged": bool,            # 是否收敛
    "iterations": int,            # 实际迭代次数
}
```

**异常**：`RuntimeError` — JAX 不可用或优化过程出现 NaN。`ValueError` — 参数非法。

#### Showcase 基线 3 器件

- `optimize_mmi(...)` / `mmi_fom(...)` — MMI 逆向设计
- `optimize_wdm(...)` / `wdm_fom(...)` — WDM 逆向设计
- `optimize_ybranch(...)` / `ybranch_fom(...)` — Y 分支逆向设计
- `run_showcase(...)` — 运行完整 showcase

#### V5.1.0 D12 增强 stage 函数

- `stage_topology_optimization(...)` — 拓扑优化 stage
- `stage_level_set_optimization(...)` — Level-set 优化 stage
- `stage_3d_adjoint_optimization(...)` — 3D 逆向设计 stage

#### 拓扑优化（topology_opt）

- `optimize_topology_mmi_1x2(...)` / `mmi_1x2_topology_fom(...)` — MMI 1×2 拓扑优化
- `optimize_topology_mmi_2x2(...)` / `mmi_2x2_topology_fom(...)` — MMI 2×2 拓扑优化
- `optimize_topology_wdm(...)` / `wdm_topology_fom(...)` — WDM 拓扑优化
- `simp_interpolation(...)` / `sensitivity_filter(...)` / `heaviside_projection(...)` — SIMP 滤波投影
- 常量：`SIMP_PENALTY_P` / `PROJECTION_BETA` / `PROJECTION_ETA` / `FILTER_RADIUS_PX`

#### Level-set（level_set）

- `optimize_levelset_ybranch(...)` / `ybranch_levelset_fom(...)` — Y 分支 Level-set
- `optimize_levelset_bend(...)` / `bend_waveguide_levelset_fom(...)` — 弯曲波导 Level-set
- `regularized_heaviside(...)` / `phi_to_epsilon(...)` / `hji_evolve_step(...)` / `reinitialize_phi(...)` / `gradient_magnitude(...)`
- 常量：`DT_LEVELSET` / `HEAVISIDE_EPS` / `REINIT_INTERVAL` / `REINIT_N_STEPS`

#### 3D 逆向设计（adjoint_3d）

- `optimize_3d_adjoint_taper(...)` / `taper_3d_fom(...)` — 3D 锥形逆向设计
- `optimize_3d_adjoint_grating(...)` / `grating_coupler_3d_fom(...)` — 3D 光栅耦合器逆向设计
- `simp_interpolation_3d(...)` / `sensitivity_filter_3d(...)` / `voxelize_3d(...)`
- 常量：`TAPER_RADIATION_ALPHA` / `GRATING_PERIOD_UM` / `GRATING_DUTY_CYCLE`

#### 底层内核

- `DifferentiableFDTD` / `GedneyPML` / `YeeGrid3D` — JAX 可微 FDTD 内核
- `epsilon_r_from_width(...)` / `fom_fn(...)` / `run_adjoint_optimization(...)`
- 常量：`EPS_R_SI=12.08` / `EPS_R_SIO2=2.085` / `GRID_NX=24` / `GRID_NY=12` / `GRID_NZ=8` / `GRID_DX_M=2e-7` / `PML_N_LAYERS=4` / `N_ITERATIONS=50` / `LEARNING_RATE=0.5` / `MOMENTUM=0.9` / `INITIAL_WIDTH_PIXELS` / `TARGET_WAVELENGTH_UM=1.55`

### 8.2 polaris-optimizer — 优化器（12 种）

> 源码：`modules/optimizer/src/polaris_optimizer/__init__.py` · 版本 `5.0.0`
> 文献：Liu & Nocedal 1989 L-BFGS https://doi.org/10.1007/BF01589116 · Kennedy & Eberhart 1995 PSO https://doi.org/10.1109/ICNN.1995.488968 · Hansen 2001 CMA-ES https://doi.org/10.1162/106365601750190398 · Deb 2002 NSGA-II https://doi.org/10.1109/4235.996017 · Deb & Jain 2014 NSGA-III https://doi.org/10.1109/TEVC.2013.2281535 · Osher & Sethian 1988 https://doi.org/10.1016/S0021-9991(88)80002-2 · Piggott 2017 https://www.nature.com/articles/nphoton.2017.102 · Hughes 2018 https://arxiv.org/abs/1811.01255 · Wang 2018 Robust TO https://doi.org/10.1364/OE.26.023273 · Apollo 2025 https://arxiv.org/html/2504.18813v1

12 种光子学优化器统一接口：

| 优化器 | 主要 API | 算法 |
|--------|---------|------|
| L-BFGS | `run_lbfgs_optimization(...)` / `LBFGSOptimizer` / `LBFGSConfig` / `LBFGSResult` | 两循环递归 + Wolfe 线搜索 |
| PSO | `create_pso_optimizer(...)` / `ParticleSwarmOptimizer` / `PSOConfig` | 粒子群（Kennedy 1995） |
| CMA-ES | `create_cmaes_optimizer(...)` / `CMAESOptimizer` / `CMAESConfig` | 协方差矩阵自适应（Hansen 2001） |
| Global | `run_global_optimization(...)` / `create_global_optimizer(...)` / `GlobalOptimizer` / `GlobalResult` / `GlobalMethod` | 统一全局优化 |
| NSGA-II | `NSGA2Optimizer` / `NSGA2Config` / `ParetoResult` / `fast_non_dominated_sort(...)` / `compute_crowding_distance(...)` / `sbx_crossover(...)` / `polynomial_mutation(...)` / `tournament_selection(...)` | 快速非支配排序 + 拥挤距离 |
| NSGA-III | `NSGA3Optimizer` / `NSGA3Config` / `NSGA3Result` / `generate_reference_points(...)` / `NicheSelectionState` | 参考点法 + 小生境选择 |
| 拓扑优化 | `run_topology_optimization(...)` / `TopologyOptimizer` / `TopologyConfig` / `TopologyResult` / `LevelSet` | 水平集 + Hamilton-Jacobi |
| HJ 求解器 | `create_hj_solver(...)` / `HJSolver` / `evolve_hj(...)` / `compute_cfl_timestep(...)` / `HJScheme` / `FluxPair` / `GridStep` | Hamilton-Jacobi 方程 |
| 鲁棒优化 | `run_robust_optimization(...)` / `RobustOptimizer` / `RobustConfig` / `RobustResult` / `create_tolerance_model(...)` / `evaluate_robustness(...)` / `MonteCarloEvaluator` / `ToleranceModel` | 蒙特卡洛公差扰动 |
| 形状伴随 | `run_shape_adjoint_optimization(...)` / `ShapeAdjointOptimizer` / `ShapeAdjointConfig` / `ParameterizedGeometry` / `AnalyticalWaveguideCoupler` / `ForwardSimulator` / `OptimizationBackend` | 参数化几何 + Adam |
| 反馈适配 | `FeedbackAdapter` / `FeedbackResult` / `Violation` / `PlacementHint` / `RoutingHint` | 约束违规 → 布局布线建议 |
| 辅助函数 | `dominates(a, b)` / `Objective` / `ObjectiveType` / `Individual` / `SBXConfig` | NSGA 辅助 |

---

## 第 9 章：量子光子（polaris-boson / polaris-klm / polaris-quantum-advanced）

### 9.1 polaris-boson — 玻色采样

> 源码：`modules/boson/src/polaris_boson/__init__.py` · 版本 `5.1.0`
> 文献：Aaronson & Arkhipov STOC 2011 https://arxiv.org/abs/0910.4698 · KLM Nature 2001 https://www.nature.com/articles/35051009 · HOM PRL 1987 https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.59.2044 · Clements Optica 2016 https://opg.optica.org/optica/fulltext.cfm?uri=optica-3-12-1460 · Glynn 2010 https://doi.org/10.1016/j.ejc.2010.01.010 · Björklund 2012 https://arxiv.org/abs/1203.5687

#### `boson_sampling(unitary, input_state) -> dict`

线性光学玻色采样。

| 参数 | 类型 | 说明 |
|------|------|------|
| `unitary` | `list` | M×M 酉矩阵 |
| `input_state` | `list` | 输入光子态 |

**返回**：玻色采样结果 dict（含输出概率分布）。

#### `clements_unitary(n_modes=4, seed=42) -> list`

Clements 酉矩阵生成器（Clements et al. Optica 2016）。

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `n_modes` | `int` | `4` | 模式数 |
| `seed` | `int` | `42` | 随机种子 |

**返回**：酉矩阵 `list[list[complex]]`。

#### `hom_interference(theta=0.0) -> dict`

HOM 双光子干涉（Hong-Ou-Mandel 1987）。

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `theta` | `float` | `0.0` | 分束器角度 |

**返回**：dict 含 HOM dip 可见度等。`theta=0.0` 时 HOM dip=1。

#### `permanent_glynn_gray(matrix) -> complex`

矩阵积和式计算（Glynn 2010 算法）。

### 9.2 polaris-klm — KLM 线性光学量子计算

> 源码：`modules/klm/src/polaris_klm/__init__.py` · 版本 `5.1.0`
> 文献：KLM Nature 2001 https://www.nature.com/articles/35051009 · Ralph 2002 PRA https://doi.org/10.1103/PhysRevA.65.062324 · Hofmann 2002 PRA https://doi.org/10.1103/PhysRevA.66.024308 · O'Brien 2003 Nature https://doi.org/10.1038/nature02354 · Knill 2002 PRA https://doi.org/10.1103/PhysRevA.66.052306

#### `klm_cnot() -> dict`

KLM CNOT 量子门仿真（Ralph 2002 简化 4-BS 电路，后选择成功率 1/9）。

**返回**：dict 含电路酉矩阵、成功率（1/9）、酉性校验（<1e-10）。

**异常**：`RuntimeError` — 电路酉性校验失败。

### 9.3 polaris-quantum-advanced — 高级量子计算

> 源码：`modules/quantum_advanced/src/polaris_quantum_advanced/__init__.py` · 版本 `5.1.0`
> 文献：Aaronson & Arkhipov 2011 https://arxiv.org/abs/0910.4698 · Hamilton 2017 PRL https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.119.170501 · García-Patrón 2019 https://arxiv.org/abs/1712.10037 · Bennett & Brassard 1984 https://doi.org/10.1145/358340.358342 · Ekert 1991 PRL https://doi.org/10.1103/PhysRevLett.67.661 · Shor & Preskill 2000 PRL https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.85.441 · Acín 2006 PRL https://doi.org/10.1103/PhysRevLett.97.230503 · Hradil 1997 PRA https://doi.org/10.1103/PhysRevA.55.R1561 · Chuang & Nielsen 1997 https://arxiv.org/abs/quant-ph/9610001 · Weedbrook 2012 RMP https://doi.org/10.1103/RevModPhys.84.621 · Steane 1996 PRL https://doi.org/10.1103/PhysRevLett.77.793 · KLM Nature 2001 https://www.nature.com/articles/35051009 · Ralph 2002 PRA https://doi.org/10.1103/PhysRevA.65.062324 · HOM 1987 PRL https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.59.2044 · Schulman 2017 PPO https://arxiv.org/abs/1707.06347 · Schulman 2016 GAE https://arxiv.org/abs/1506.02438 · Kok & Lovett 2007 RMP https://doi.org/10.1103/RevModPhys.79.135

主要 API 分类：

**积和式**：`permanent_ryser(matrix)` / `permanent_brute_force(matrix)`

**玻色采样**：`boson_sampling_prob(...)` / `boson_sampling_distribution(...)` / `beamsplitter_unitary(theta)` / `hom_interference(theta)` / `BosonSamplingResult`

**GBS**：`hafnian(matrix)` / `gbs_probability(...)`

**含损玻色采样**：`lossy_boson_sampling(...)` / `quantum_advantage_threshold(...)`（Beer-Lambert `η=exp(-αL)`）

**数值仿真**：`hom_dip_simulation(...)` / `boson_sampling_sampler(...)` / `boson_sampling_chi_square_test(...)`

**高级采样**：`LargeScaleBosonSampler` / `HOMInterferometer`

**量子层析**：`QuantumStateTomography` / `QuantumProcessTomography` / `TomographyResult`

**QKD**：`BB84Protocol` / `BB84EnhancedProtocol` / `E91Protocol` / `QKDResult`（Shor-Preskill 阈值 11%，Acín 2006 成码率下界）

**CV 高斯态**：`GaussianState` / `DisplacementGate` / `SqueezingGate` / `RotationGate` / `BeamSplitterGate` / `HomodyneDetection`

**QEC**：`ThreeQubitRepetitionCode` / `SteaneCode` / `BitFlipError` / `PhaseFlipError` / `SyndromeMeasurement` / `RecoveryOperation`

**资源态**：`GHZState` / `ClusterState1D` / `NOONState` / `StateFidelity`

**噪声**：`PhotonLossChannel` / `PhaseNoiseChannel` / `DetectorModel`

**拟合**：`SParamFitter` / `LossExtractor` / `CouplingEfficiencyExtractor` / `FitResult`

**量子电路模拟器**：`QuantumCircuitSimulator` / `Qubit` / `QuantumGateType`

**分布式 PPO**：`DistributedPPOTrainer` / `DistributedPPOConfig` / `WorkerStats`

> *创新* R05 v4.0-FAKE-ENV-P0 守门逻辑：分布式 PPO 训练器默认拒绝用合成环境训练（`synthetic_env_mode=False`），必须注入真实 FloorplanEnv 或显式开启合成测试模式。

---

## 第 10 章：GUI（polaris-gui）

> 源码：`modules/gui/src/polaris_gui/__init__.py` · 版本 `5.0.0`
> 文献：KLayout 编辑器 https://www.klayout.de/doc-qt5/manual/editor.html · Siemens L-Edit Photonics https://eda.sw.siemens.com/en-US/ic/ic-custom/photonic/l-edit-photonics/ · GDSFactory https://gdsfactory.github.io/gdsfactory/ · Krinke ISPD 2024 https://dl.acm.org/doi/pdf/10.1145/3626184.3635289 · SiEPIC-Tools https://github.com/SiEPIC/SiEPIC-Tools/wiki · Foley & Van Dam 2013 · Gamma Design Patterns 1994 · Python http.server https://docs.python.org/3/library/http.server.html · Manning IR Book 2008 https://nlp.stanford.edu/IR-book/ · PageRank 1998 http://ilpubs.stanford.edu:8090/422/ · Brandes 2001 https://www.sciencedirect.com/science/article/pii/S0306437901000707 · Carbonell MMR 1998 https://dl.acm.org/doi/10.1145/290941.291025 · Lord IRT 1980 · Luceda Academy https://academy.lucedaphotonics.com/

### 版图编辑器（纯 NumPy）

| API | 说明 |
|-----|------|
| `LayoutEditor` | 版图编辑器（器件拖拽/旋转/删除/镜像，NumPy 仿射变换，撤销/重做栈，DRC 错误高亮） |
| `EditorConfig` | 编辑器配置（网格/DBU/快捷键） |
| `DeviceInstance` | 器件实例（位置/旋转/镜像/类别） |
| `DRCHighlight` | DRC 错误高亮区域 |

### 交互式编辑（纯 stdlib + NumPy）

| API | 说明 |
|-----|------|
| `ObjectType` / `LayoutObject` / `evaluate_object(...)` | 交互式曲线多边形对象 |
| `CommandStack` | 撤销/重做栈 |
| `SnapEngine` / `SnapResult` | 网格吸附引擎 |
| `AirlineRouter` / `AirlineSegment` | 航线布线 |
| `MacroIDE` / `MacroDebugger` | 宏脚本 IDE 与调试器 |
| `ViewerGuard` | 视图边界保护 |

### Web Server（lazy 导出，依赖 polaris-flow）

| API | 说明 |
|-----|------|
| `WebServer` | HTTP Web Server（REST API + 静态文件服务 + Showcase 端到端 Demo） |
| `run_server(...)` | 启动 Web Server |

REST API 端点：`/api/health` / `/api/presets` / `/api/run` / `/api/jobs` 等。

### 教育平台（纯 NumPy）

| API | 说明 |
|-----|------|
| `KnowledgeGraph` / `KGNode` | 知识图谱构建（NumPy 邻接矩阵） |
| `TFIDFRetriever` | TF-IDF 文档检索 + MMR 多样性重排 |
| `PageRank` | 文档重要性排序（幂迭代） |
| `IRT3PL` | 三参数逻辑斯蒂教学评估 |

---

## 第 11 章：光电协同（polaris-parasitic / polaris-multiphysics / polaris-pam4 / polaris-yield / polaris-lumerical）

### 11.1 polaris-parasitic — 寄生提取与 Verilog-A

> 源码：`modules/parasitic/src/polaris_parasitic/__init__.py` · 版本 `5.0.0`
> 文献：Synopsys StarRC https://www.synopsys.com/content/dam/synopsys/implementation&signoff/datasheets/starrc-ds.pdf · StarRC Resistance https://www.synopsys.com/blogs/chip-design/exploring-resistance-extraction-techniques-starrc.html · Cadence Quantus QRC · Ansys Lumerical CML Compiler https://optics.ansys.com/hc/en-us/sections/360005039133-CML-Compiler · Verilog-AMS LRM https://www.accellera.org/downloads/standards/v-ams · Ngspice https://ngspice.sourceforge.io/docs.html · Pozar Microwave Engineering §4 · Chrostowski 2015 §2.3/§8/§9 · Rosa NIST 1908 https://nvlpubs.nist.gov/nistpubs/bulletin/04/nbsbulletin-v04-n1-p301-a2b.pdf · Wheeler 1928 https://ieeexplore.ieee.org/document/1654891 · SiPANN https://sipann.readthedocs.io/ · Simphony https://simphonyphotonics.readthedocs.io/ · SiEPIC EBeam PDK · JAX https://jax.readthedocs.io/ · PyTorch autograd https://pytorch.org/docs/stable/autograd.html

#### 寄生参数提取

| API | 公式 | 说明 |
|-----|------|------|
| `ParasiticResistor.extract(...)` | `R = RPSQ × L / W`; `R(T)=R0·(1+TC1·ΔT+TC2·ΔT²)` | 电阻提取（StarRC TC1/TC2） |
| `ParasiticCapacitor.extract_self(...)` | `C_pp=ε·W·L/d + C_fringe=2π·ε·L/arcosh(2d/H+1)` | 电容提取（Banerjee 圆柱模型） |
| `ParasiticInductor.extract_self(...)` | `L_self=μ0·L/(2π)·[ln(2L/(W+H))+0.5+(W+H)/(6L)]` | 电感提取（Rosa 1908） |
| `ParasiticSParam.compute_s_params(...)` | π 型网络 ABCD → S | S 参数提取（Pozar §4.4） |
| `SpiceNetlistWriter.to_string(...)` | — | SPICE 网表生成（StarRC DSPF 语法） |
| `AdvancedParasiticExtractor.extract_all(...)` | — | 一站式综合 R/L/C |

#### Verilog-A 紧凑模型生成（10 器件）

| API | 说明 |
|-----|------|
| `generate_waveguide_verilog_a(...)` | 波导 `S21=exp(-α·L/2)·exp(j·2π·neff·L/λ)` |
| `generate_mmi_1x2_verilog_a(...)` / `generate_mmi_2x2_verilog_a(...)` | MMI |
| `generate_grating_coupler_verilog_a(...)` | 光栅耦合器 |
| `generate_ring_verilog_a(...)` | 环形谐振器 `T=(t-a·e^{jφ})/(1-t·a·e^{jφ})`（Yariv 1997） |
| `generate_modulator_verilog_a(...)` | 调制器 `P_out=η·V²·cos²(π·V/(2·V_π))` |
| `generate_detector_verilog_a(...)` | 探测器 `I_photo=R·P_in, V_out=I_photo·R_load` |
| `generate_directional_coupler_verilog_a(...)` / `generate_phase_shifter_verilog_a(...)` / `generate_y_branch_verilog_a(...)` | 其他器件 |
| `generate_verilog_a(device_type, ...)` | 统一入口（按 device_type 分发） |
| `save_verilog_a(model, path)` | 保存 .va 文件 |
| `VerilogAModel` / `SDict` | 模型数据结构 |

#### SPICE 联合仿真（Ngspice）

- `generate_spice_netlist(models, config, input_signal)` — 生成 Ngspice 兼容网表
- `run_ngspice_cosimulation(netlist, config)` — 调用 ngspice -b -r rawfile（不可用时 raise FileNotFoundError，R03 无 fall-back）
- `run_photoelectric_cosim(...)` — 光电联合仿真
- `CoSimulationResult` / `SPICESimulationConfig`

#### 光电协同可微分仿真（*创新*）

- `DifferentiableOptoElectricalModel.forward(voltage_in, modulator_length=100)` — 前向 `P_opt=η·V²·exp(-α·L) → I_photo=R·P_opt → V_out=I_photo·R_load`
- `DifferentiableOptoElectricalModel.gradient(voltage_in, modulator_length, eps=1e-6)` — *创新* 有限差分梯度跨光电边界 `∂V_out/∂V_in`, `∂V_out/∂L_mod`
- `optimize_opto_electrical_link(target_output_voltage=0.5, initial_voltage=1.0, n_iterations=10)` — *创新* 梯度下降联合优化 V_in 与 L_mod

### 11.2 polaris-multiphysics — 多物理场仿真

> 源码：`modules/multiphysics/src/polaris_multiphysics/__init__.py` · 版本 `5.0.0`
> 文献：Scharfetter & Gummel 1969 IEEE TED https://doi.org/10.1109/T-ED.1969.16766 · Soref & Bennett 1987 IEEE JQE https://doi.org/10.1109/JQE.1987.1073206 · Cocorullo 1999 IEEE JSTQE https://doi.org/10.1109/2944.788409 · Moharam 1995 JOSA A https://doi.org/10.1364/JOSAA.12.001077 · Li 1996 JOSA A https://doi.org/10.1364/JOSAA.13.001870 · Chang 1980 IEEE TMTT https://doi.org/10.1109/TMTT.1980.1130551 · Yee 1966 IEEE TAP https://doi.org/10.1109/TAP.1966.1138693 · Newmark 1959 ASCE https://doi.org/10.1061/JMCEA3.0000097 · Redheffer 1959 https://www.jstor.org/stable/24900576 · Carslaw & Jaeger 1959 · Taflove & Hagness 2005 · Selberherr 1984 · Jin 2014 FEM · Roden & Gedney 2000 CPML · NIST CODATA 2018

#### DDM 漂移扩散

| API | 说明 |
|-----|------|
| `solve_ddm(config)` / `solve_ddm_gummel(config)` | PN 结漂移扩散仿真（Poisson + 连续性 + SG 离散 + SRH + 阻尼牛顿） |
| `DdmSolver` / `GummelSolver` | 求解器类 |
| `DdmConfig` / `DdmResult` | 配置与结果 |

#### HEAT 热传导

| API | 说明 |
|-----|------|
| `solve_heat(config)` | 稳态热传导 `∇·(k∇T)+Q=0`（5 点有限差分 + 调和平均 k） |
| `solve_transient_heat(config)` | 瞬态热传导 |
| `HeatSolver` / `TransientHeatSolver` / `HeatConfig` / `HeatResult` | 求解器与配置 |

#### VarFDTD 2.5D

| API | 说明 |
|-----|------|
| `solve_varfdtd(config)` | EIM + 2D Yee leapfrog + CPML + TFSF |
| `compute_effective_index(...)` | 有效折射率计算 |
| `VarFdtdSolver` / `VarFdtdConfig` / `VarFdtdResult` / `EffectiveIndexResult` | 求解器与配置 |

#### RCWA 严格耦合波

| API | 说明 |
|-----|------|
| `solve_rcwa_1d(config)` | 1D RCWA（Moharam 1995 ETM + Li 1996 FFF + Redheffer 星积） |
| `solve_rcwa_2d(config)` | 2D RCWA |
| `RcwaConfig1D` / `RcwaConfig2D` / `RcwaResult1D` / `RcwaResult2D` | 配置与结果 |

#### FETD 有限元时域

| API | 说明 |
|-----|------|
| `FetdSolver` / `NewmarkIntegrator` / `FetdConfig` / `FetdResult` | Newmark-β (β=0.25, γ=0.5) 无条件稳定 |

#### 电-光/热-光耦合

| API | 说明 |
|-----|------|
| `apply_electro_optic_coupling(...)` | Soref-Bennett 等离子体色散（电-光） |
| `apply_thermo_optic_coupling(...)` | Cocorullo 热光效应（热-光） |
| `compute_delta_n_from_carriers(...)` | 载流子引起的折射率变化 |
| `compute_delta_n_from_temperature(...)` | 温度引起的折射率变化 |
| `ElectroOpticCouplingResult` / `ThermoOpticCouplingResult` | 耦合结果 |

#### TCAD 2D 热仿真

| API | 说明 |
|-----|------|
| `ThermalSolver2D` | 2D 热仿真（5 点 FDM + Carslaw-Jaeger 线热源） |
| `ThermalLayer` | 热层定义 |

### 11.3 polaris-pam4 — PAM4 信号仿真

> 源码：`modules/pam4/src/polaris_pam4/__init__.py` · 版本 `5.0.0`
> 文献：Shafik 2016 IEEE CommSurveys https://ieeexplore.ieee.org/document/7410082 · OIF CEI-112G https://www.oiforum.com/ · Lumerical INTERCONNECT https://optics.ansys.com/hc/en-us/articles/49697869166611 · Chrostowski 2015 §9 · Proakis Digital Communications 2007 §5 · Agrawal Fiber-Optic 2012 §4

#### `simulate_pam4(n_symbols=1000, bit_rate_gbps=100, samples_per_symbol=16, noise_std=0.05) -> dict`

PAM4 信号仿真。4 电平 (0, 1/3, 2/3, 1) + BER `=0.5·erfc(√(SNR_eye/2))`（Shafik 2016）。

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `n_symbols` | `int` | `1000` | 符号数 |
| `bit_rate_gbps` | `float` | `100` | 比特率（Gbps） |
| `samples_per_symbol` | `int` | `16` | 每符号采样数 |
| `noise_std` | `float` | `0.05` | 噪声标准差 |

**返回**：`dict{ber, snr_db, n_symbols, bit_rate_gbps}`。

#### `generate_pam4_signal(n_symbols, bit_rate, samples_per_symbol, seed=42) -> tuple`

生成 PAM4 信号（4 电平等概率 + 上采样）。**返回**：`(time, signal)` ndarray。

#### `compute_ber(signal, samples_per_symbol=16, n_levels=4, noise_std=0.05) -> float`

计算 BER。`SNR_eye=(eye/2)²/σ²`, `BER=0.5·erfc(√(SNR_eye/2))`。

#### `compute_snr_db(signal, noise_std=0.05) -> float`

计算 SNR (dB)。`SNR_dB = 10·log10(mean(signal²)/σ²)`。

#### `compute_eye_diagram(signal, samples_per_symbol=16, n_levels=4) -> ndarray`

计算眼图（按 2 符号周期折叠）。**返回**：`ndarray[2*samples_per_symbol, n_windows]`。

### 11.4 polaris-yield — 统计与良率分析

> 源码：`modules/yield/src/polaris_yield/__init__.py` · 版本 `5.0.0`
> 文献：Metropolis & Ulam 1949 https://doi.org/10.1080/01621459.1949.10483310 · Sobol 2001 https://doi.org/10.1007/BF02304730 · Saltelli 2010 https://doi.org/10.1016/j.cpc.2009.09.018 · McKay 1979 Technometrics https://doi.org/10.1080/00401706.1979.10489755 · Sobol 1967 · Halton 1960 · Niederreiter 1992 SIAM · Glasserman 2003 Springer · Glynn & Iglehart 1989 https://doi.org/10.1287/mnsc.35.11.1367 · Heidelberger 1995 https://doi.org/10.1145/270261.270264 · Bucklew 2004 Springer · Siegmund 1976 · Rubinstein 1997 · Kroese 2011 Wiley · Asmussen & Glynn 2007 Springer · Cochran 1977 · Neyman 1934 · Singhal & Pinel 1981 IEEE TCS · Parkinson 1993 · Madkour 2015 IEEE TCAS-I · Bogaerts 2018 OFC · NIST Taguchi https://www.itl.nist.gov/div898/handbook/pri/section5/pri56.htm · SciPy sobol_indices / QMC

主要 API：

| API | 说明 |
|-----|------|
| `monte_carlo_simulate(func, base_params, ...)` | 蒙特卡洛仿真 |
| `sobol_sensitivity_analysis(func, param_distributions, ...)` | Sobol 全局灵敏度 |
| `yield_analysis(func, base_params, spec_func, ...)` | 蒙特卡洛良率 |
| `generate_qmc_samples(n, dim, ...)` / `qmc_monte_carlo(...)` | QMC 准随机采样与仿真 |
| `importance_sampling_yield(...)` / `rare_event_yield(...)` | 稀有事件良率 IS 估计 |
| `cross_entropy_importance_sampling(...)` | CE 自适应 IS |
| `stratified_monte_carlo(...)` | 分层采样方差减少 |
| `compute_worst_case_distance(...)` | WCD 工业良率指标 |
| `allocate_tolerance_by_sensitivity(...)` | Taguchi 容差分配 |
| `optimize_yield_via_nominal_shift(...)` | 标称值良率优化 |
| `batch_simulate(...)` / `batch_yield_analysis(...)` | 多场景批量仿真 |

结果类型：`MonteCarloResult` / `SobolSensitivityResult` / `ImportanceSamplingResult` / `StratifiedSamplingResult` / `WorstCaseDistanceResult` / `ToleranceAllocationResult` / `YieldOptimizationResult` / `BatchSimulationResult` / `BatchYieldResult`

### 11.5 polaris-lumerical — 商业软件集成

> 源码：`modules/lumerical/src/polaris_lumerical/__init__.py` · 版本 `5.0.0`
> 文献：Yee 1966 IEEE TAP https://doi.org/10.1109/TAP.1966.1138693 · Soref & Bennett 1987 IEEE JQE https://doi.org/10.1109/JQE.1987.1073206 · Marcatili 1969 Bell Syst Tech J https://doi.org/10.1002/j.1538-7305.1969.tb01163.x · Sze & Ng 2007 · Agrawal 2010 §4.5-4.7 · ITU-T O.150 PRBS https://www.itu.int/rec/T-REC-O.150 · Mur 1981 IEEE EMC · Chrostowski 2015 · Ansys Lumerical https://optics.ansys.com/hc/en-us · Tidy3D https://docs.flexcompute.com/projects/tidy3d/ · MEEP https://meep.readthedocs.io/

主要 API 分类：

**Lumerical FDTD3D**：`FDTD3DConfig` / `LumericalFDTDBackend` / `courant_dt_3d(...)`

**Lumerical MODE**：`ModeConfig` / `ModeSolver`

**Lumerical CHARGE**：`CHARGEConfig` / `CHARGESimulator`

**Lumerical INTERCONNECT**：`INTERCONNECTConfig` / `INTERCONNECTSimulator`

**Lumerical Integration**：`LumericalIntegration`

**Tidy3D**：`Tidy3DConfig` / `Tidy3DBackend` / `is_tidy3d_available()`

**GPUFDTD**（纯 NumPy CPU，R04 合规）：`GPUFDTDConfig` / `GPUFDTDEngine`

**MEEP**：`MeepAdjointBackend` / `MeepSimulationConfig` / `MeepAdjointResult` / `check_meep_availability()` / `is_meep_available()`

**FDTD Simulator**：`FDTDBackend` / `FDTDConfig` / `FDTDResult` / `compute_soi_waveguide_sparams(...)`

**Photoelectric CoSim**：`PhotoelectricCoSim` / `CoSimConfig` / `ModulatorSpec` / `PhotodetectorSpec` / `LaserSpec`

**CML Compiler**：`CMLCompiler` / `CMLMetadata` / `CMLComponent` / `CMLDiagnostics`（S 参数 + 无源性/互易性诊断）

**物理常数**：`ELECTRON_CHARGE=1.602176634e-19` / `PLANCK_CONSTANT=6.62607015e-34` / `SPEED_OF_LIGHT=2.99792458e8` / `SOI_N_EFF_CENTER` / `SOI_DN_D_LAMBDA` / `SOI_ALPHA_DB_PER_UM` / `DB_TO_NP` / `PASSIVITY_TOL` / `RECIPROCITY_TOL`

> 商业软件未安装时 raise（R03 禁止 fall-back）。

---

## 附录 A：数据类型参考

### A.1 CircuitSpec 字段表

| 字段 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `name` | `str` | — | 电路名称 |
| `devices` | `list[DeviceSpec]` | `[]` | 器件列表 |
| `connections` | `list[tuple[str,str,str,str]]` | `[]` | 连接列表 `[(dev1, port1, dev2, port2), ...]` |
| `canvas_w` | `float` | `1000.0` | 画布宽度（μm） |
| `canvas_h` | `float` | `1000.0` | 画布高度（μm） |
| `benchmark_source` | `BenchmarkSource` | `CUSTOM` | Benchmark 来源 |
| `process_node` | `str \| None` | `None` | 工艺节点 |
| `optical_wavelength_nm` | `float` | `1550.0` | 工作波长（nm） |
| `target_metric` | `TargetMetric` | `ROUTING_SUCCESS_RATE` | 评估指标 |
| `target_value` | `float` | `1.0` | 目标值 |

### A.2 DeviceSpec 字段表

| 字段 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `name` | `str` | — | 器件名称 |
| `device_type` | `str` | — | 器件类型 |
| `width_um` | `float` | `10.0` | 器件宽度（μm） |
| `height_um` | `float` | `10.0` | 器件高度（μm） |
| `ports` | `list[tuple[str, float, float, str]]` | `[]` | 端口列表 `[(name, dx, dy, direction), ...]` |
| `params` | `dict` | `{}` | 器件参数（可含 `insertion_loss_db`/`neff` 等） |
| `process_node` | `str \| None` | `None` | 工艺节点 |

### A.3 circuit dict（JSON-serializable）key 说明

| key | 类型 | 说明 |
|-----|------|------|
| `name` | `str` | 电路名 |
| `devices` | `list[dict]` | 器件 dict 列表 |
| `connections` | `list[list]` | 连接列表 `[[dev1, port1, dev2, port2], ...]` |
| `canvas_w` | `float` | 画布宽度（μm） |
| `canvas_h` | `float` | 画布高度（μm） |
| `process_node` | `str \| None` | 工艺节点 |
| `optical_wavelength_nm` | `float` | 工作波长（nm） |

### A.4 device dict（JSON-serializable）key 说明

| key | 类型 | 说明 |
|-----|------|------|
| `name` | `str` | 器件实例名 |
| `device_type` | `str` | 器件类型 |
| `width_um` | `float` | 器件宽度（μm） |
| `height_um` | `float` | 器件高度（μm） |
| `ports` | `list[list]` | 端口列表 `[[name, dx, dy, direction], ...]` |
| `params` | `dict` | 器件参数 |
| `process_node` | `str \| None` | 工艺节点 |

### A.5 placements dict key 说明

| key | 类型 | 说明 |
|-----|------|------|
| `{device_name}` | `dict` | 器件名 → 布局位置 |
| `.x` | `float` | 左下角 x 坐标（μm） |
| `.y` | `float` | 左下角 y 坐标（μm） |
| `.w` | `float` | 器件宽度（μm） |
| `.h` | `float` | 器件高度（μm） |

### A.6 BenchmarkSource 枚举值

| 值 | 说明 | 来源 |
|----|------|------|
| `TILOS` | TILOS Ariane/MemPool/NVDLA（电子芯片对照） | https://github.com/TILOS-AI-Institute/MacroPlacement |
| `APOLLO` | Apollo PTC/oNoC（光子芯片对照） | https://github.com/ASU-LOPE-Group/Apollo |
| `LIDAR` | LiDAR ISPD'25（光子曲线布线对照） | https://dl.acm.org/doi/pdf/10.1145/3698364.3705355 |
| `CUSTOM` | PoLaRIS 自有 benchmark | — |

### A.7 TargetMetric 枚举值

| 值 | 说明 | 单位 |
|----|------|------|
| `HPWL` | 半周长线长 | μm |
| `DRV` | 设计规则违规数 | 个 |
| `ROUTING_SUCCESS_RATE` | 布线成功率 | 0-1 |
| `INSERTION_LOSS_DB` | 插入损耗 | dB |

### A.8 StageStatus 枚举值

| 值 | 说明 |
|----|------|
| `PENDING` | 未开始 |
| `RUNNING` | 执行中 |
| `COMPLETED` | 成功完成 |
| `FAILED` | 执行失败 |
| `BLOCKED` | 被阻塞（依赖未满足） |
| `SKIPPED` | 跳过 |

### A.9 JobStatus 枚举值

| 值 | 说明 |
|----|------|
| `QUEUED` | 已提交，等待执行 |
| `RUNNING` | 正在执行 |
| `COMPLETED` | 全部阶段成功完成 |
| `FAILED` | 执行失败 |
| `CANCELLED` | 被取消 |

---

## 附录 B：错误码与异常

PoLaRIS 遵循 R03 禁止 fall-back 原则：所有业务错误必须 `raise` 明确异常，禁止 `except: pass` / `return None` / `return []` 静默兜底。

### B.1 异常类型

| 异常 | 触发场景 | 典型模块 |
|------|---------|---------|
| `RuntimeError` | 电路/器件结构非法、字段缺失、类型不符、参数非法、模式不支持、端口未找到、JAX 不可用、仿真 NaN、checkpoint 损坏、酉性校验失败、概率和≠1、状态转换非法 | 所有模块（统一用 RuntimeError 表示业务错误） |
| `ValueError` | 未知阶段 ID、参数值越界 | polaris-flow / polaris-inverse |
| `ImportError` | lazy 导出模块依赖未安装（如 polaris-flow 的 TrainingPipeline 依赖 polaris-core） | polaris-flow / polaris-gui |
| `AttributeError` | 访问不存在的模块属性 | polaris-flow / polaris-gui |
| `FileNotFoundError` | Ngspice 商业软件不可用（R03 无 fall-back） | polaris-parasitic |

### B.2 常见 RuntimeError 消息模式

| 消息模式 | 说明 |
|---------|------|
| `"circuit 必须是 dict，得到 {type}"` | circuit 参数类型错误 |
| `"circuit 缺少必要字段: {key}"` | circuit dict 缺少必要字段 |
| `"画布尺寸必须为正: canvas_w={w}, canvas_h={h}（R03 禁止 fall-back）"` | 画布尺寸非正 |
| `"不支持的布局模式: {mode}（可选: 'analytical' / 'ppo_gnn'）"` | 布局 mode 非法 |
| `"不支持的布线模式: {mode}（可选: {modes}）"` | 布线 mode 非法 |
| `"器件 {name} 未找到端口: {port}（R03 禁止 fall-back）"` | 端口未找到 |
| `"连接 {conn} 引用了不存在的器件: {dev}（R03 禁止 fall-back）"` | 连接引用悬空器件 |
| `"非法状态转换: {from} → {to}"` | Job 状态机非法转换 |
| `"JAX 不可用或优化过程出现 NaN（R03 禁止 fall-back）"` | JAX 逆向设计失败 |
| `"电路酉性校验失败"` | KLM 量子门酉性错误 |

### B.3 编排层异常处理策略

编排层（`run_eda_flow`）的 `strict` 参数控制异常传播：

| `strict` | stage 失败行为 |
|----------|---------------|
| `False`（默认） | 捕获异常，记录 `error` 与 `traceback`，继续后续 stage，最终汇总 `n_failed` |
| `True` | 首个 stage 失败立即 raise `RuntimeError`（含 stage_id 与 traceback） |

> **注意**：编排层的 `strict=False` 是编排策略（全流程诊断报告），不是 R03 业务 fall-back。子模块内部仍零 fall-back：上游 stage 失败时下游子模块自身 raise（如 `placements=None → route_circuit raise`）。

---

> **文档统计**：本文档覆盖 33 个子模块的公共 API，包含 11 个章节 + 2 个附录，所有 API 签名均从 `modules/*/src/polaris_*/__init__.py` 实际代码提取（R02 学术诚信），所有物理参数/公式均标注文献来源 URL。
