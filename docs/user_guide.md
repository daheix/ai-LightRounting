# PoLaRIS 用户指南

> PoLaRIS（光弈）光电子 AI 智能布局布线引擎。本指南按功能场景系统组织，
> 覆盖 4 平台 36 器件 PDK、10 阶段 EDA 流水线的完整使用方法。
>
> - 入门教程见 [getting_started.md](getting_started.md)（15 分钟快速上手）
> - 进阶教程见 [advanced_tutorial.md](advanced_tutorial.md)（DRC/LVS/寄生/良率/量子）
> - **本指南**：按功能场景系统组织的完整使用手册，每章含完整可运行代码示例
>
> 所有代码示例均从 `examples/` 与 `docs/api_reference.md` 真实提取（R02 学术诚信），
> 禁止编造 API 或假数据（R03 禁止 fall-back）。纯 NumPy/SciPy/JAX(CPU) 实现（R04）。

---

## 目录

- [第 1 章 PDK 与器件管理](#第-1-章-pdk-与器件管理)
- [第 2 章 电路规格定义](#第-2-章-电路规格定义)
- [第 3 章 器件布局](#第-3-章-器件布局)
- [第 4 章 波导布线](#第-4-章-波导布线)
- [第 5 章 物理仿真](#第-5-章-物理仿真)
- [第 6 章 DRC 设计规则检查](#第-6-章-drc-设计规则检查)
- [第 7 章 LVS 版图验证](#第-7-章-lvs-版图验证)
- [第 8 章 GDS 导出](#第-8-章-gds-导出)
- [第 9 章 逆向设计](#第-9-章-逆向设计)
- [第 10 章 量子光子验证](#第-10-章-量子光子验证)
- [第 11 章 光电协同](#第-11-章-光电协同)
- [第 12 章 Web GUI 使用](#第-12-章-web-gui-使用)
- [第 13 章 完整流水线编排](#第-13-章-完整流水线编排)
- [附录 A 常见电路模板](#附录-a-常见电路模板)
- [附录 B 性能参考](#附录-b-性能参考)

---

## 第 1 章 PDK 与器件管理

PoLaRIS 内置 4 个光电子工艺平台 PDK，共 36 个代表性器件。所有器件参数均
来自公开文献/工艺手册并附带来源标注。

### 1.1 平台概览

| 平台 | Foundry | 工艺节点 | 器件数 | PDK 来源 |
|------|---------|----------|--------|----------|
| SOI | SiEPIC | 220nm SOI | 9 | [SiEPIC EBeam PDK](https://github.com/SiEPIC/SiEPIC_EBeam_PDK) |
| SiN | Ligentec | SiN TriPleX | 9 | [Ligentec ANR PDK](https://www.ligentec.com/) |
| InP | Pattern Project | InP generic | 9 | [JePPIX](https://www.jeppix.eu/) |
| LNOI | HyperLight | LNOI X-cut | 9 | [HyperLight](https://hyperlightphotonics.com/) |

### 1.2 列出所有平台

```python
import polaris_pdk

# 列出 4 个 PDK 平台
platforms = polaris_pdk.list_platforms()
for p in platforms:
    print(f"{p['platform']:5s} | {p['foundry']:14s} | "
          f"{p['process_node']:12s} | {p['device_count']} 器件")
    # 输出示例:
    # SOI   | SiEPIC         | 220nm SOI    | 9 器件
    # SiN   | Ligentec       | SiN TriPleX  | 9 器件
    # InP   | Pattern Project| InP generic  | 9 器件
    # LNOI  | HyperLight     | LNOI X-cut   | 9 器件
```

> 来源：`examples/e2e_showcase/stages/stage1_pdk_catalog.py`、
> `modules/pdk/src/polaris_pdk/catalog.py`

### 1.3 列出指定平台的器件

```python
import polaris_pdk

# 列出 SOI 平台全部器件
soi_devices = polaris_pdk.list_devices("SOI")
for d in soi_devices:
    print(f"  {d['device_type']:30s} | {d['category']:8s} | "
          f"{d['name']}")
```

SOI 平台 9 器件清单：

| device_type | 类别 | 名称 | 关键参数 |
|-------------|------|------|----------|
| strip_waveguide | passive | Strip Waveguide | 500nm×220nm, loss 2.0 dB/cm |
| grating_coupler | passive | Grating Coupler (1D Si) | IL 1.9 dB @1550nm |
| y_branch | passive | Y Branch | IL 0.3 dB |
| mmi_1x2 | passive | MMI 1x2 | IL 0.4 dB |
| ring_resonator | passive | Ring Resonator | Q=1e4, FSR=10nm |
| directional_coupler | passive | Directional Coupler | gap 200nm, 3dB 耦合 |
| mzi | passive | Mach-Zehnder Interferometer | 臂长 100μm, FSR 10nm |
| thermo_optic_phase_shifter | active | Thermo-Optic Phase Shifter | Pπ=20mW |
| ge_photodetector | detector | Ge Photodetector | R=0.8 A/W, BW=40GHz |

> 参数来源：`modules/pdk/src/polaris_pdk/devices.py`，每个器件均含
> `pdk_reference` 与 `source` 字段标注文献溯源（R02）。

### 1.4 查询单个器件详情

```python
import polaris_pdk

# 获取 SOI 平台的光栅耦合器详情
gc = polaris_pdk.get_device("SOI", "grating_coupler")
print(f"名称: {gc['name']}")
print(f"插损: {gc['params']['insertion_loss_db']} dB")
print(f"波长: {gc['params']['wavelength_nm']} nm")
print(f"极化: {gc['params']['polarization']}")
print(f"端口: {gc['ports']}")
print(f"来源: {gc['source']['title']}")
print(f"文献: {gc['source']['url']}")
```

> **R03 禁止 fall-back**：平台或器件不存在时 `get_device` / `list_devices`
> 会 `raise RuntimeError`，不返回假数据。

### 1.5 各平台代表性器件

**SiN 平台**（低损耗，适合大功率/传感）：

```python
import polaris_pdk
sin_wg = polaris_pdk.get_device("SiN", "sin_waveguide_lpcvd")
# loss_db_cm = 0.1（Ligentec LPCVD SiN <0.1 dB/cm）

sin_ring = polaris_pdk.get_device("SiN", "sin_ring_high_q")
# q_factor = 1000000.0（EPFL Damascene SiN 高 Q ~1e6）
```

**InP 平台**（有源，含激光器/调制器/探测器）：

```python
import polaris_pdk
dfb = polaris_pdk.get_device("InP", "dfb_laser")
# output_power_mw = 3.0, smsr_db = 40.0

soa = polaris_pdk.get_device("InP", "soa")
# gain_db = 20.0（SOA 增益 ~20dB）
```

**LNOI 平台**（薄膜铌酸锂，超高速调制）：

```python
import polaris_pdk
lnoi_mzm = polaris_pdk.get_device("LNOI", "lnoi_eo_modulator")
# bandwidth_ghz = 110.0（>110 GHz）, vpi_v = 3.0

lnoi_cmos = polaris_pdk.get_device("LNOI", "lnoi_cmos_modulator")
# drive_voltage_v = 1.0（CMOS 兼容 <1V）
# 来源: Wang et al., Nature 2018, https://doi.org/10.1038/s41586-018-0551-y
```

---

## 第 2 章 电路规格定义

PoLaRIS 使用 `polaris_core` 子模块定义电路规格，包含器件规格（DeviceSpec）、
电路规格（CircuitSpec）和电路校验（validate_circuit）。

### 2.1 创建单个器件

```python
from polaris_core import make_device

# 创建光栅耦合器器件
gc1 = make_device(
    name="gc1",
    device_type="grating_coupler",
    width_um=20,
    height_um=20,
    ports=[("in", 0, 10, "west"), ("out", 20, 10, "east")],
    params={"insertion_loss_db": 1.9, "peak_wavelength_nm": 1550.0},
)
# 返回 dict，含 name/device_type/width_um/height_um/ports/params
```

> 来源：`examples/full_pipeline_18modules/main.py` `build_circuit()` 函数

### 2.2 创建 MZI 干涉仪电路

```python
from polaris_core import make_device, make_circuit, validate_circuit

# 5 器件 MZI 调制器电路（对标 Intel 100G CWDM4 MZM）
gc1 = make_device("gc1", "grating_coupler", 20, 20,
                  ports=[("in", 0, 10, "west"), ("out", 20, 10, "east")],
                  params={"insertion_loss_db": 1.9, "peak_wavelength_nm": 1550.0})
mmi1 = make_device("mmi1", "mmi_1x2", 30, 20,
                   ports=[("in", 0, 10, "west"),
                          ("out1", 30, 5, "east"), ("out2", 30, 15, "east")],
                   params={"insertion_loss_db": 0.4, "split_ratio": 0.48})
ps1 = make_device("ps1", "phase_shifter", 100, 10,
                  ports=[("in", 0, 5, "west"), ("out", 100, 5, "east")],
                  params={"neff": 2.4, "pi_voltage": 3.0, "length_um": 100.0})
mmi2 = make_device("mmi2", "mmi_2x2", 30, 20,
                   ports=[("in1", 0, 5, "west"), ("in2", 0, 15, "west"),
                          ("out1", 30, 10, "east"), ("out2", 30, 10, "east")],
                   params={"insertion_loss_db": 0.5})
gc2 = make_device("gc2", "grating_coupler", 20, 20,
                  ports=[("in", 0, 10, "west"), ("out", 20, 10, "east")],
                  params={"insertion_loss_db": 1.9, "peak_wavelength_nm": 1550.0})

# 连接列表: [源器件, 源端口, 目标器件, 目标端口]
connections = [
    ["gc1", "out", "mmi1", "in"],
    ["mmi1", "out1", "ps1", "in"],
    ["ps1", "out", "mmi2", "in1"],
    ["mmi1", "out2", "mmi2", "in2"],
    ["mmi2", "out1", "gc2", "in"],
]

circuit = make_circuit(
    "MZI_100G", [gc1, mmi1, ps1, mmi2, gc2], connections,
    canvas_w=500, canvas_h=300,
    process_node="220nm SOI",
    optical_wavelength_nm=1550.0,
)

# 校验电路结构完整性
ok = validate_circuit(circuit)
print(f"电路 {circuit['name']}: {len(circuit['devices'])} 器件, "
      f"{len(circuit['connections'])} 连接, 校验={ok}")
```

> 来源：`examples/full_pipeline_18modules/main.py` `build_circuit()`、
> `examples/e2e_showcase/stages/stage2_circuit_spec.py`

### 2.3 电路转字典

```python
from polaris_core import circuit_to_dict

# 将电路对象转为 JSON 可序列化 dict（供下游布局/布线/导出使用）
circuit_dict = circuit_to_dict(circuit)
# circuit_dict 含: name / devices / connections / canvas_w / canvas_h
#                 / process_node / optical_wavelength_nm
```

### 2.4 Clements 4×4 光矩阵电路

```python
from polaris_core import make_device, make_circuit

# 10 器件 Clements 4x4 光矩阵: 6 个 mmi_2x2 + 4 个 phase_shifter
devices = []
connections = []
# 构建 6 个 MZI 单元 + 4 个相移器（详见 stage2_circuit_spec.py）
clements_circuit = make_circuit(
    "Clements_4x4", devices, connections,
    canvas_w=800, canvas_h=600,
    optical_wavelength_nm=1550.0,
)
```

> 来源：`examples/e2e_showcase/stages/stage2_circuit_spec.py`
> Clements 幺正网络文献：Clements et al., Optica 2016,
> https://doi.org/10.1364/OPTICA.3.001460

---

## 第 3 章 器件布局

PoLaRIS 提供两种 AI 布局模式：`analytical`（DREAMPlace 解析法）和
`ppo_gnn`（AlphaChip PPO-GNN 强化学习）。布局以 HPWL（半周长线长）为优化目标。

### 3.1 analytical 解析法布局

```python
import polaris_place

# 对 MZI 电路执行解析法布局
result = polaris_place.place_circuit(circuit, mode="analytical")

print(f"布局模式: {result['placement_mode']}")
print(f"HPWL = {result['hpwl']:.2f} μm")
for name, pl in result["placements"].items():
    print(f"  {name:5s} x={pl['x']:7.2f} y={pl['y']:7.2f} "
          f"w={pl['w']:6.1f} h={pl['h']:6.1f}")
```

> 来源：`examples/e2e_showcase/stages/stage3_ai_placement.py`、
> `examples/full_pipeline_18modules/main.py`

### 3.2 ASCII 布局可视化

```python
import polaris_place

# 将布局渲染为 ASCII 网格图
ascii_layout = polaris_place.render_ascii_layout(
    circuit, result["placements"], grid_w=40, grid_h=15
)
print(ascii_layout)
# # = 器件, . = 空白, 可直观查看器件分布
```

### 3.3 布局算法参数

analytical 模式基于 DREAMPlace 解析法（将布局问题转化为无约束优化）：

| 参数 | 默认值 | 说明 | 来源 |
|------|--------|------|------|
| gamma | 4.0 | 密度惩罚平滑系数 | DREAMPlace DAC 2020 |
| density_weight | 1e-3 | 密度权重 | DREAMPlace |
| learning_rate | 0.01 | 学习率 | DREAMPlace |
| max_iterations | 200 | 最大迭代次数 | DREAMPlace |

ppo_gnn 模式基于 AlphaChip PPO + GNN：

| 参数 | 值 | 说明 |
|------|-----|------|
| _OBS_DIM | 8 | 观测维度 |
| _GNN_OUT_DIM | 16 | GNN 输出维度 |
| _GNN_HIDDEN_DIM | 32 | GNN 隐藏层维度 |
| _GNN_NUM_LAYERS | 2 | GNN 层数 |
| PHOTONIC_EDGE_DIM | 15 | 光子边特征维度 |

> 来源：`docs/algorithm_handbook.md`
> DREAMPlace: Lin et al., DAC 2020, https://doi.org/10.1109/DAC18072.2020.9218756
> AlphaChip: Mirhoseini et al., Nature 2021, https://doi.org/10.1038/s41586-021-03544-w
> HPWL 公式: Kahng & Lienig, IEEE TCAD 2009, https://doi.org/10.1109/TCAD.2008.2012395

---

## 第 4 章 波导布线

PoLaRIS 使用 `polaris_route` 子模块执行曲线感知布线（curvy routing），
基于 Euler 螺旋波导弯曲，支持损耗模型与交叉检测。

### 4.1 电路级布线

```python
import polaris_place
import polaris_route

# 先布局，再布线
placement = polaris_place.place_circuit(circuit, mode="analytical")
routing = polaris_route.route_circuit(
    circuit, placement["placements"], mode="curvy"
)

print(f"总损耗 = {routing['total_loss_db']:.3f} dB")
print(f"路径数 = {len(routing['paths'])}")
print(f"总弯曲数 = {routing['n_bends']}")
print(f"总交叉数 = {routing['n_crossings']}")

# 逐路径查看
for i, p in enumerate(routing["paths"]):
    print(f"  路径{i+1}: {p['dev1']}.{p['port1']} -> {p['dev2']}.{p['port2']}, "
          f"弯曲={p['n_bends']}, 交叉={p['n_crossings']}, "
          f"损耗={p['loss_db']:.4f} dB")
```

> 来源：`examples/e2e_showcase/stages/stage4_routing.py`、
> `examples/curvy_routing.py`

### 4.2 损耗模型

布线损耗由四部分组成：

| 损耗项 | 参数 | 默认值 | 来源 |
|--------|------|--------|------|
| 传播损耗 | PROPAGATION_LOSS_DB_CM | 3.0 dB/cm | Soref 1993 IEEE |
| 弯曲损耗 | BEND_LOSS_DB | 0.05 dB/bend | SiEPIC EBeam PDK |
| 交叉损耗 | CROSSING_LOSS_DB | 0.3 dB/crossing | SiEPIC EBeam PDK |
| 最小弯曲半径 | DEFAULT_MIN_BEND_RADIUS_UM | 5.0 μm | SiEPIC EBeam PDK |

> 来源：`docs/algorithm_handbook.md`
> Soref et al. 1993 IEEE JQE: https://ieeexplore.ieee.org/document/1148303
> SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK

### 4.3 弯曲波导补偿

布局后可能存在端口未对齐的情况，`bend_compensate` 自动调整下游器件位置
使端口对齐，消除 PORT_ALIGNMENT DRC 违规：

```python
import polaris_route

# 布线后执行弯曲补偿
if placement["placements"] and routing.get("paths"):
    new_placements, new_routing = polaris_route.bend_compensate(
        circuit, placement["placements"], routing
    )
    # new_placements: 调整后的器件位置（端口对齐）
    # new_routing: 重新生成的路径（弯曲数减少）
```

> 来源：`modules/orchestrator/src/polaris_orchestrator/flow.py` `_stage_route()`
> *创新*：在布线后自动调整下游器件位置使端口对齐，消除 PORT_ALIGNMENT DRC 违规。
> 底层逻辑：SiEPIC EBeam PDK 波导弯曲容差 10μm，超过此容差需 S-bend 补偿。

### 4.4 底层 CurvyRouter API

```python
from polaris_route import CurvyRouter, CurvyRouteConfig, count_crossings, path_length

# 自定义最小弯曲半径
config = CurvyRouteConfig(min_bend_radius_um=5.0, n_curve_points=20)
router = CurvyRouter(config)

# 单条连接布线
path = router.route(start=(0.0, 0.0), end=(40.0, 30.0))
print(f"路径点数: {len(path)}")
print(f"路径长度: {path_length(path):.2f} μm")

# 交叉检测
crossings = count_crossings(path, path)  # 自交叉检测（单路径应为 0）
print(f"自交叉数: {crossings}")
```

> 来源：`examples/curvy_routing.py` 场景 4
> LiDAR ISPD'25 曲线感知布线: https://dl.acm.org/doi/10.1145/3698364.3705355
> Euler spiral 波导: Klauss et al. 2018, https://doi.org/10.1364/OE.26.029637

### 4.5 ASCII 布线可视化

```python
# stage4_routing.py 中的布线可视化函数
def render_ascii_routing(routing, grid_w=50, grid_h=15):
    """将布线结果渲染为 ASCII 图。
    # = 路径, O = 起止端口, . = 空白
    """
    # 实现详见 examples/e2e_showcase/stages/stage4_routing.py
    pass
```

---

## 第 5 章 物理仿真

PoLaRIS 提供 7 个物理仿真子模块，覆盖频域/时域/模式求解全场景。
其中 `polaris_sparam`、`polaris_pam4`、`polaris_fdtd` 进入主流程 stage 5，
`polaris_fde`/`polaris_eme`/`polaris_bpm`/`polaris_fdfd` 为独立子模块按需调用。

### 5.1 频域 S 参数仿真（polaris-sparam）

```python
import polaris_sparam

# MZI S 参数扫描
mzi = polaris_sparam.simulate_mzi_sparam()
print(f"谐振陷波波长 = {mzi['resonant_wavelength_nm']:.2f} nm")
print(f"理论消光比 = {mzi['extinction_ratio_db']:.2f} dB")
print(f"实际消光比 = {mzi['extinction_ratio_physical_db']:.2f} dB")

# Clements 4x4 酉矩阵验证
clements = polaris_sparam.compute_clements_unitary(n_modes=4)
print(f"酉性: {clements['is_unitary']}, 误差={clements['unitarity_error']:.2e}")
```

MZI 传输公式（Saleh & Teich 2019 §4.4）：

```
T_bar = R² + T² + 2·R·T·cos(Δφ)
```

其中 R=0.48（SiEPIC 实测分束比），T=0.52，ER ≈ 28 dB。

> 来源：`examples/e2e_showcase/stages/stage5_simulation.py`
> Saleh & Teich, "Fundamentals of Photonics", Wiley 2019

### 5.2 PAM4 信号仿真（polaris-pam4）

```python
import polaris_pam4

# PAM4 眼图仿真
pam4 = polaris_pam4.simulate_pam4(n_symbols=1000, bit_rate_gbps=100)
print(f"PAM4 ({pam4['n_symbols']} 符号 @ {pam4['bit_rate_gbps']:.0f}Gbps)")
print(f"BER = {pam4['ber']:.2e}")
print(f"SNR = {pam4['snr_db']:.2f} dB")
```

> 来源：`examples/full_pipeline_18modules/main.py`、
> `examples/e2e_showcase/stages/stage8_opto_electrical.py`

### 5.3 FDTD 时域全波仿真（polaris-fdtd）

```python
import polaris_fdtd

# 3D Yee + PML 全波仿真
fdtd = polaris_fdtd.simulate_waveguide_fdtd(dx_um=0.1, n_steps=200)
print(f"dx = {fdtd['dx_um']} μm, n_steps = {fdtd['n_steps']}")
print(f"T_fdtd = {fdtd['T_fdtd']:.6f}")
print(f"传输 = {fdtd['transmission_db']:.4f} dB")
print(f"PML 启用 = {fdtd['pml_enabled']}")
```

FDTD 核心参数：

| 参数 | 值 | 说明 | 来源 |
|------|-----|------|------|
| C0 | 2.99792458e8 m/s | 光速 | 物理常数 |
| SOI_N_SI | 3.476 | 硅折射率 | Palik |
| SOI_N_SIO2 | 1.444 | SiO2 折射率 | Palik |
| SOI_EPS_R_SI | 12.08 | 硅相对介电常数 | n² |
| SOI_EPS_R_SIO2 | 2.085 | SiO2 相对介电常数 | n² |
| CFL_SAFETY | 0.95 | CFL 安全系数 | Taflove 2005 |

> 来源：`docs/algorithm_handbook.md`、`examples/e2e_showcase/stages/stage5_simulation.py`
> Yee 1966 IEEE TAP: https://doi.org/10.1109/TAP.1966.1138693
> Taflove 2005 Computational Electrodynamics: https://doi.org/10.1002/0471758467

### 5.4 FDE 模式求解（polaris-fde）

```python
import polaris_fde

# 2D 有限差分本征模求解
fde = polaris_fde.solve_modes(
    width_um=0.5, height_um=0.22, wavelength_um=1.55,
    n_core=3.476, n_clad=1.444, n_modes=3,
)
print(f"模式数: {fde['n_modes']}")
for i, mode in enumerate(fde["modes"]):
    print(f"  mode {i}: neff = {mode['neff']:.6f}")
```

FDE 核心参数：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| width_um | 0.5 | 波导宽度 |
| height_um | 0.22 | 波导高度 |
| n_core | 3.476 | 硅核折射率 |
| n_clad | 1.444 | SiO2 包层折射率 |
| CONFINEMENT_THRESHOLD | 0.6 | 模式限制因子阈值 |
| V_CUTOFF_SINGLE_MODE | 2.405 | 单模截止 V 参数 |

> 来源：`examples/full_pipeline_18modules/main.py`
> 单模条件 V < 2.405（Bessel 函数第一零点）

### 5.5 EME 本征模展开（polaris-eme）

```python
import polaris_eme

# 锥形波导模式匹配 + Redheffer 星积
eme = polaris_eme.solve_eme(
    sections=[
        {"width_um": 1.0, "length_um": 5.0,
         "n_core": 3.476, "n_clad": 1.444},
        {"width_um": 0.5, "length_um": 5.0,
         "n_core": 3.476, "n_clad": 1.444},
    ],
    wavelength_um=1.55,
    n_modes_per_section=2,
)
print(f"段数: {eme['n_sections']}")
print(f"|T| = {abs(eme['transmission']):.6f}")
print(f"|R| = {abs(eme['reflection']):.2e}")
```

> 来源：`examples/full_pipeline_18modules/main.py`

### 5.6 BPM 光束传播法（polaris-bpm）

```python
import polaris_bpm

# Crank-Nicolson 隐式步进
bpm = polaris_bpm.solve_bpm(
    width_um=0.5, length_um=20.0, wavelength_um=1.55,
    n_core=3.476, n_clad=1.444,
    dz_um=0.5, dx_um=0.02, pad_um=1.0,
)
print(f"步数: {bpm['n_steps']}")
print(f"传输 = {bpm['transmission_db']:.4f} dB")
```

> 来源：`examples/full_pipeline_18modules/main.py`

### 5.7 FDFD 频域有限差分（polaris-fdfd）

```python
import polaris_fdfd

# Helmholtz 稀疏求解稳态场
fdfd = polaris_fdfd.solve_fdfd(
    width_um=0.5, length_um=10.0, wavelength_um=1.55,
    n_core=3.476, n_clad=1.444,
    dx_um=0.05, pad_um=1.0,
)
print(f"网格数: {fdfd['n_grid']}")
print(f"传输 = {fdfd['transmission_db']:.4f} dB")
```

> 来源：`examples/full_pipeline_18modules/main.py`

---

## 第 6 章 DRC 设计规则检查

PoLaRIS 的 `polaris_drc` 子模块对齐 KLayout DRC runset（SiEPIC EBeam 工艺），
内置 18 条设计规则检查。

### 6.1 运行 DRC 检查

```python
import polaris_place
import polaris_drc

# 先布局，再 DRC
placement = polaris_place.place_circuit(circuit, mode="analytical")
drc = polaris_drc.run_drc(circuit, placement["placements"], bend_compensate=True)

print(f"规则数: {drc['n_rules']}")
print(f"通过数: {drc['n_passed']}")
print(f"违规数: {drc['n_violations']}")
print(f"通过率: {drc['pass_rate']:.1%}")

# 查看违规详情
for v in drc["violations"]:
    print(f"  [{v['rule']}] {v['message']}")
```

> 来源：`examples/e2e_showcase/stages/stage6_drc_lvs.py`、
> `examples/full_pipeline_18modules/main.py`

### 6.2 DRC 规则清单

| 规则名 | 阈值 | 说明 |
|--------|------|------|
| MIN_SPACING | 1.0 μm | 最小器件间距 |
| MIN_WIDTH | 0.5 μm | 最小波导宽度 |
| MIN_HEIGHT | 0.4 μm | 最小器件高度 |
| MIN_AREA | 0.1 μm² | 最小面积 |
| PORT_ALIGNMENT | 10 μm | 端口对齐容差 |
| BEND_RADIUS_MIN | 5.0 μm | 最小弯曲半径 |
| DENSITY_MAX | 80% | 最大器件密度 |
| DENSITY_MIN | 0.01% | 最小器件密度 |

> 完整 18 条规则详见 `docs/algorithm_handbook.md`
> KLayout DRC 文档: https://www.klayout.org/doc-qt5/manual/drc_runsets.html

### 6.3 弯曲补偿与 DRC 联动

```python
import polaris_drc

# bend_compensate=True 时，DRC 检查前自动执行弯曲补偿
# 消除 PORT_ALIGNMENT 违规
drc = polaris_drc.run_drc(circuit, placement["placements"], bend_compensate=True)
# 若 PORT_ALIGNMENT 违规 dx>10μm 且 dy>10μm，自动调整下游器件位置
```

---

## 第 7 章 LVS 版图验证

`polaris_lvs` 子模块将版图提取的网表与参考电路原理图比对，确认拓扑一致。

### 7.1 运行 LVS 检查

```python
import polaris_lvs

# 网表一致性比对
lvs = polaris_lvs.run_lvs(circuit, netlist=None)

print(f"一致性: {lvs['is_consistent']}")
print(f"不匹配数: {lvs['n_mismatches']}")
print(f"器件数: {lvs['n_devices']}")
print(f"连接数: {lvs['n_connections']}")
```

> 来源：`examples/e2e_showcase/stages/stage6_drc_lvs.py`、
> `examples/full_pipeline_18modules/main.py`
> KLayout LVS 文档: https://www.klayout.org/doc-qt5/manual/lvs.html

### 7.2 DRC + LVS 联合检查

```python
import polaris_drc
import polaris_lvs

# 先布局
placement = polaris_place.place_circuit(circuit, mode="analytical")

# DRC + LVS 联合检查
drc = polaris_drc.run_drc(circuit, placement["placements"])
lvs = polaris_lvs.run_lvs(circuit)

print(f"DRC: 通过率 {drc['pass_rate']:.1%} ({drc['n_passed']}/{drc['n_rules']})")
print(f"LVS: 一致={lvs['is_consistent']} "
      f"(器件={lvs['n_devices']}, 连接={lvs['n_connections']})")
```

> 来源：`examples/e2e_showcase/stages/stage6_drc_lvs.py`

---

## 第 8 章 GDS 导出

`polaris_gdsio` 子模块将电路导出为 GDSII 文件（OASIS 也可选），
使用 klayout.db 后端，dbu=1nm。

### 8.1 导出 GDSII 文件

```python
import os
import polaris_gdsio

output_dir = "out/gds_output"
os.makedirs(output_dir, exist_ok=True)
gds_path = os.path.join(output_dir, f"{circuit['name']}.gds")

gds = polaris_gdsio.export_gds(circuit, gds_path)

print(f"文件路径: {gds['path']}")
print(f"文件大小: {gds['file_size_bytes']} bytes")
print(f"结构数: {gds['n_structures']}")
print(f"层数: {gds['n_layers']}")
print(f"可加载: {gds['loadable']}")
```

> 来源：`examples/e2e_showcase/stages/stage7_gds_export.py`、
> `examples/full_pipeline_18modules/main.py`

### 8.2 GDS 层映射

PoLaRIS 使用 SiEPIC EBeam PDK 标准层映射：

| 层 (GDS layer, datatype) | 含义 |
|--------------------------|------|
| (1, 0) | WG — 波导 |
| (2, 0) | SLAB150 — 150nm Slab |
| (3, 0) | SLAB90 — 90nm Slab |
| (66, 0) | TEXT — 文本标注 |
| (68, 0) | DEVREC — 器件边界 |
| (69, 0) | PIN — 引脚标注 |
| (99, 0) | PORT — 端口标注 |

> 来源：`docs/api_reference.md`
> SiEPIC EBeam PDK 层定义: https://github.com/SiEPIC/SiEPIC_EBeam_PDK

### 8.3 批量导出多个电路

```python
import os
import polaris_gdsio

# 导出 MZI、Clements_4x4、量子玻色采样三个电路
circuits = [mzi_circuit, clements_circuit, boson_circuit]
output_dir = "out/gds_batch"
os.makedirs(output_dir, exist_ok=True)

for circuit in circuits:
    gds_path = os.path.join(output_dir, f"{circuit['name']}.gds")
    gds = polaris_gdsio.export_gds(circuit, gds_path)
    print(f"  {circuit['name']}: {gds['file_size_bytes']} bytes, "
          f"{gds['n_structures']} 结构, loadable={gds['loadable']}")
```

> 来源：`examples/e2e_showcase/stages/stage7_gds_export.py`

---

## 第 9 章 逆向设计

`polaris_inverse` 子模块使用 JAX `jax.grad` 自动微分实现伴随法逆向设计，
替代传统 lumopt 手动推导伴随方程。

### 9.1 波导宽度优化

```python
import polaris_inverse

# JAX 自动微分逆向设计
result = polaris_inverse.optimize_waveguide_width(
    n_iterations=50,     # 迭代次数
    learning_rate=0.5,   # 学习率
)

print(f"初始宽度: {result['initial_width_nm']:.1f} nm")
print(f"最优宽度: {result['optimal_width_nm']:.1f} nm")
print(f"初始 FoM: {result['initial_fom']:.4f}")
print(f"最终 FoM: {result['final_fom']:.4f}")
print(f"改善: {result['improvement_db']:.2f} dB")
print(f"收敛: {result['converged']}")
print(f"迭代: {result['iterations']}")

# 查看 FoM 历史
print(f"FoM 历史: {result['fom_history'][:5]}...（共 {len(result['fom_history'])} 步）")
```

> 来源：`examples/e2e_showcase/stages/stage10_adjoint_inverse_design.py`、
> `examples/full_pipeline_18modules/main.py`

### 9.2 *创新*：JAX 自动微分替代手动伴随方程

PoLaRIS 的逆向设计使用 JAX `jax.grad` 自动微分计算梯度，
替代传统 lumopt 库需要手动推导伴随方程的方式：

- **传统方法**（lumopt）：需手动推导伴随方程，每个目标函数单独推导
- **PoLaRIS 方法**（*创新*）：JAX 自动微分，任意目标函数自动求导

底层逻辑：JAX 的 `jax.grad` 通过 Tracer 追踪计算图，自动应用链式法则，
对任意可微目标函数计算梯度，无需手动推导伴随方程。

> 来源：`modules/orchestrator/src/polaris_orchestrator/flow.py` docstring
> JAX 文档: https://docs.jax.dev/
> lumopt（传统伴随法）: https://github.com/chriskeraly/lumopt

### 9.3 Adjoint 优化参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| GRID_NX | 24 | X 网格数 |
| GRID_NY | 12 | Y 网格数 |
| GRID_NZ | 8 | Z 网格数 |
| GRID_DX_M | 0.2e-6 | 网格间距（米） |
| N_ITERATIONS | 50 | 迭代次数 |
| LEARNING_RATE | 0.5 | 学习率 |
| MOMENTUM | 0.3 | 动量系数（heavy-ball） |

> 来源：`docs/algorithm_handbook.md`

### 9.4 Benchmark 数据

逆向设计实测改善幅度（50 步生产级迭代）：

| 优化目标 | 初始 FoM (dB) | 最终 FoM (dB) | 改善 (dB) |
|----------|---------------|---------------|-----------|
| 硅波导宽度优化 | 0.00 | 14.72 | +14.72 |
| MMI 1x2 | 0.00 | 16.59 | +16.59 |
| WDM 滤波器 | 0.00 | 10.06 | +10.06 |
| Y 分支 | 0.00 | 10.92 | +10.92 |

> 来源：`docs/algorithm_handbook.md`（polaris-inverse 单元测试实测数据）

---

## 第 10 章 量子光子验证

PoLaRIS 提供三个量子光子学子模块：`polaris_boson`（玻色采样/HOM 干涉）、
`polaris_klm`（KLM 量子门）、`polaris_quantum_advanced`（高级量子验证）。

### 10.1 玻色采样

```python
import polaris_boson

# 4 模 Clements 酉矩阵
unitary = polaris_boson.clements_unitary(n_modes=4, seed=42)

# 4 光子玻色采样（输入 |1,1,1,1>）
bs = polaris_boson.boson_sampling(unitary, input_state=[1, 1, 1, 1])

print(f"概率总和: {bs['prob_sum']:.6f}（应≈1.0，概率守恒）")
print(f"输出模式数: {bs['n_outputs']}")
```

> 来源：`examples/e2e_showcase/stages/stage9_quantum_photonics.py`、
> `examples/full_pipeline_18modules/main.py`
> Aaronson & Arkhipov 2011: https://doi.org/10.1145/1993636.1993682
> Clements et al., Optica 2016: https://doi.org/10.1364/OPTICA.3.001460

### 10.2 HOM 双光子干涉

```python
import polaris_boson

# Hong-Ou-Mandel 双光子干涉
hom = polaris_boson.hom_interference(theta=0.0)

print(f"HOM 凹陷深度: {hom['dip_depth']:.2f}（θ=0 时应为 1.0）")
print(f"符合概率: {hom['coincidence_prob']:.4f}（应为 0.0）")
print(f"验证通过: {hom['verified']}")
```

HOM 干涉：两个全同光子输入 50:50 分束器，输出 `|2,0⟩` 和 `|0,2⟩` 各占 50%，
`|1,1⟩` 概率为 0（HOM 凹陷）。

> 来源：`examples/e2e_showcase/stages/stage9_quantum_photonics.py`
> Hong, Ou, Mandel, PRL 1987: https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.59.2044

### 10.3 KLM CNOT 量子门

```python
import polaris_klm

# KLM 线性光学 CNOT 门（Ralph 2002 简化方案）
klm = polaris_klm.klm_cnot()

print(f"成功率: {klm['success_prob']:.6f}（=1/9={1/9:.6f}）")
print(f"验证通过: {klm['verified']}")
```

KLM 方案使用线性光学元件（分束器+相移器）实现量子门，
Ralph 2002 简化方案用 4 个分束器实现 CNOT，成功率 1/9。

> 来源：`examples/e2e_showcase/stages/stage9_quantum_photonics.py`、
> `modules/orchestrator/src/polaris_orchestrator/flow.py`
> Ralph et al. 2002: https://doi.org/10.1103/PhysRevA.65.012324
> KLM 原始论文: Knill, Laflamme, Milburn, Nature 2001,
> https://doi.org/10.1038/35051009

### 10.4 三项联合验证

```python
import polaris_boson
import polaris_klm

# 1. 玻色采样概率守恒（4 光子 4 模）
unitary = polaris_boson.clements_unitary(n_modes=4, seed=42)
bs = polaris_boson.boson_sampling(unitary, [1, 1, 1, 1])
assert abs(bs["prob_sum"] - 1.0) < 1e-6, "概率不守恒"

# 2. HOM 干涉 dip_depth=1.0（θ=0）
hom = polaris_boson.hom_interference(theta=0.0)
assert hom["dip_depth"] == 1.0, "HOM 凹陷深度不为 1.0"

# 3. KLM CNOT 成功率 1/9（Ralph 2002）
klm = polaris_klm.klm_cnot()
assert abs(klm["success_prob"] - 1/9) < 1e-10, "成功率不为 1/9"

print("三项量子验证全部通过 ✓")
```

> 来源：`examples/e2e_showcase/stages/stage9_quantum_photonics.py`

---

## 第 11 章 光电协同

PoLaRIS 的光电协同模块涵盖 PAM4 信号完整性、探测器噪声建模、
光路损耗预算与寄生参数提取。

### 11.1 PAM4 眼图仿真

```python
import polaris_pam4

# PAM4 眼图仿真（100 Gbps）
pam4 = polaris_pam4.simulate_pam4(
    n_symbols=2000,
    bit_rate_gbps=100,
    samples_per_symbol=32,
    seed=88,
)

print(f"PAM4 眼图 ({pam4['n_symbols']} 符号 @ {pam4['bit_rate_gbps']:.0f}Gbps)")
print(f"BER = {pam4['ber']:.2e}")
print(f"SNR = {pam4['snr_db']:.2f} dB")
```

> 来源：`examples/e2e_showcase/stages/stage8_opto_electrical.py`

### 11.2 探测器噪声建模

探测器噪声包含散粒噪声和热噪声两部分：

```python
import numpy as np

# 散粒噪声: i_shot = sqrt(2 * q * R * P * B)
# 热噪声:   i_thermal = sqrt(4 * k * T * B / R_L)
#
# 其中:
#   q = 1.602e-19 C   (电子电荷)
#   k = 1.381e-23 J/K (玻尔兹曼常数)
#   T = 300 K         (温度)
#   R = 0.8 A/W       (Ge PD 响应率, SiEPIC EBeam PDK)
#   P = 光功率 (W)
#   B = 带宽 (Hz)
#   R_L = 负载电阻 (Ω)

q = 1.602e-19
k = 1.381e-23
T = 300.0
R_pd = 0.8       # Ge PD 响应率
B = 40e9          # 40 GHz 带宽
R_L = 50.0        # 50Ω 负载

# 光路损耗 5.7 dB，链路预算目标 20 dB
OPTICAL_LOSS_DB = 5.7
print(f"光路损耗: {OPTICAL_LOSS_DB} dB")
print(f"链路预算目标: 20 dB")
```

> 来源：`examples/e2e_showcase/stages/stage8_opto_electrical.py`
> 散粒噪声/热噪声公式: Saleh & Teich 2019

### 11.3 寄生参数提取

寄生电容提取使用平行板公式 + Banerjee arcosh 边缘修正模型：

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

公式（R02 学术诚信）：
- 平行板：`C_pp = ε_r·ε_0·W·L / d`
- 边缘：`C_fringe = 2π·ε_r·ε_0·L / arcosh(2d/H + 1)`（Banerjee 圆柱模型）

> 来源：`docs/advanced_tutorial.md` §3.1
> Banerjee ECE 225 UCSB Lecture 6:
> http://courses.ece.ucsb.edu/ECE225/225_W23Banerjee/Lectures/Lecture_06.pdf

### 11.4 良率分析

```python
from polaris.sim.monte_carlo import yield_analysis
import numpy as np

def loss_func(params):
    """示例：参数平方和作为损失。"""
    import jax.numpy as jnp
    return jnp.sum(params ** 2)

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

> 来源：`docs/advanced_tutorial.md` §4.2
> 蒙特卡洛方法: Metropolis & Ulam 1949, https://doi.org/10.1063/1.1699114

---

## 第 12 章 Web GUI 使用

PoLaRIS 提供 Web UI 服务器与交互式版图编辑器（LayoutEditor），
对标 Tanner L-Edit Photonics + KLayout。

### 12.1 启动 Web 服务器

```python
from polaris_gui import WebServer, run_server

# 方式 1: 阻塞启动（默认端口 8000）
run_server(host="0.0.0.0", port=8000)

# 方式 2: 后台线程启动
server = WebServer(host="0.0.0.0", port=8000)
server.start(blocking=False)
# ... 执行其他操作 ...
server.stop()
```

> 来源：`modules/gui/src/polaris_gui/web_server.py`
> 默认 host=0.0.0.0, port=8000

### 12.2 API 端点

| 方法 | 路径 | 功能 |
|------|------|------|
| GET | /api/health | 健康检查 |
| GET | /api/presets | 列出预设电路 |
| POST | /api/run | 运行布局布线流水线 |
| POST | /api/showcase/run | 启动端到端 Demo Showcase |
| GET | /api/showcase/report/{run_id} | 查询 Showcase 汇总报告 |
| GET | /api/showcase/stages/{run_id}/{stage_id} | 查询单阶段结果 |
| POST | /api/jobs | 提交作业 |
| GET | /api/jobs | 列出所有作业 |
| GET | /api/jobs/{job_id} | 查询作业详情 |
| GET | /api/jobs/{job_id}/status | 查询作业状态 |
| POST | /api/jobs/{job_id}/cancel | 取消作业 |
| GET | /api/jobs/{job_id}/report | 查询作业汇总报告 |

> 来源：`modules/gui/src/polaris_gui/web_server.py`

### 12.3 健康检查

```bash
curl http://localhost:8000/api/health
```

### 12.4 运行布局布线

```bash
curl -X POST http://localhost:8000/api/run \
  -H "Content-Type: application/json" \
  -d '{"preset": "mzi"}'
```

### 12.5 LayoutEditor 交互式编辑

```python
from polaris_core import CircuitSpec, DeviceSpec, circuit_to_dict
from polaris_place import place_circuit
from polaris_route import route_circuit
from polaris_drc import run_drc
from polaris_gui.layout_editor import LayoutEditor

# 构建电路 → 布局 → 布线 → DRC
circuit = CircuitSpec(name="MZI", canvas_w=500, canvas_h=300, ...)
circuit_dict = circuit_to_dict(circuit)
placements = place_circuit(circuit_dict, mode="analytical")["placements"]
routing = route_circuit(circuit_dict, placements, mode="curvy")
drc = run_drc(circuit_dict, placements)

# 创建 LayoutEditor，灌入器件/布线/DRC
editor = LayoutEditor()
editor.add_device(circuit_dict, placements)
editor.set_routes(routing["paths"])
editor.highlight_drc(drc["violations"])

# 交互操作
editor.move_device("gc1", x=20.0, y=30.0)  # 移动器件
editor.rotate_device("mmi1", angle=90)       # 旋转器件
editor.undo()  # 撤销
editor.redo()  # 重做

# 渲染 Web 预览
scene = editor.render()  # 输出 scene.json

# 导出 KLayout 脚本（深度编辑模式）
editor.export_klayout_script("mzi_edit.py")
```

> 来源：`examples/e2e_showcase/stages/stage11_interactive_layout_edit.py`
> LayoutEditor 对标 Tanner L-Edit Photonics: https://www.tanner.com/products/l-edit-photonic
> KLayout Python API: https://www.klayout.de/doc/about/macro_editor.html
> Command Pattern（撤销/重做栈）: Gamma et al., "Design Patterns", Addison-Wesley 1994

---

## 第 13 章 完整流水线编排

`polaris_orchestrator` 子模块提供 `run_eda_flow` 一键运行完整 EDA 流程，
9 个 stage 顺序执行。

### 13.1 一键运行全流程

```python
import polaris_orchestrator

# 一键运行 9 stage 完整 EDA 流程
result = polaris_orchestrator.run_eda_flow(
    circuit=circuit,
    output_dir="out/eda_flow",
    skip_stages=None,  # 不跳过任何 stage
    strict=False,      # stage 失败不中断（编排策略）
)

print(f"成功: {result['n_success']}")
print(f"失败: {result['n_failed']}")
print(f"跳过: {result['n_skipped']}")
print(f"总耗时: {result['total_duration']:.2f}s")

for s in result["stages"]:
    mark = "✓" if s["status"] == "success" else "✗"
    print(f"  [{mark}] stage {s['stage_id']} {s['name']:8s} "
          f"{s['status']:8s} ({s['duration']:.2f}s)")
```

> 来源：`examples/full_pipeline_18modules/main.py`、
> `modules/orchestrator/src/polaris_orchestrator/flow.py`

### 13.2 Stage 流程

| Stage | 名称 | 子模块 | 功能 |
|-------|------|--------|------|
| 1 | PDK目录 | polaris_pdk | 列出所有 PDK 平台 |
| 2 | 电路验证 | polaris_core | 校验 circuit 结构完整性 |
| 3 | AI布局 | polaris_place | analytical 解析法布局 |
| 4 | 智能布线 | polaris_route | curvy 曲线波导布线 + 弯曲补偿 |
| 5 | 仿真验证 | polaris_sparam + pam4 + fdtd | MZI S 参数 + Clements + PAM4 + FDTD |
| 6 | DRC_LVS | polaris_drc + lvs | 设计规则检查 + 网表一致性比对 |
| 7 | GDS导出 | polaris_gdsio | 导出 GDSII 文件 |
| 8 | 逆向设计 | polaris_inverse | JAX jax.grad 波导宽度优化 |
| 9 | 量子验证 | polaris_klm + boson | KLM CNOT + HOM 干涉 |

### 13.3 编排策略 vs R03 fall-back 禁令

```python
import polaris_orchestrator

# strict=False（默认）: stage 失败记录 error 但不中断
result = polaris_orchestrator.run_eda_flow(
    circuit=circuit,
    output_dir="out/eda_flow",
    strict=False,
)
# 仿真失败不阻塞 GDS 导出，DRC 失败不阻塞量子验证
# 用户获得全流程诊断报告而非单点中断

# strict=True: 首个 stage 失败立即 raise
result = polaris_orchestrator.run_eda_flow(
    circuit=circuit,
    output_dir="out/eda_flow_strict",
    strict=True,
)
```

> *创新*（编排策略）: 编排层允许某 stage 失败后继续执行后续 stage
> （`strict=False` 默认），这是**编排策略**而非业务 fall-back。
> - 底层逻辑：EDA 流程中仿真失败不应阻塞 GDS 导出，DRC 失败不应阻塞
>   量子验证——用户需要全流程诊断报告而非单点中断。
> - 上游 stage 失败时，下游 stage 不使用假数据 fall-back，而是让子模块
>   自身抛 RuntimeError（如 placements=None → route_circuit raise），
>   编排层捕获后记录为 stage 失败。即"失败向上传播，编排层汇总"，
>   子模块内部仍零 fall-back。
>
> 来源：`modules/orchestrator/src/polaris_orchestrator/flow.py` docstring
> OpenROAD: https://github.com/The-OpenROAD-Project/OpenROAD
> TILOS MacroPlacement: https://github.com/TILOS-AI-Institute/MacroPlacement

### 13.4 跳过指定 stage

```python
import polaris_orchestrator

# 跳过 stage 8（逆向设计）和 stage 9（量子验证）省时
result = polaris_orchestrator.run_eda_flow(
    circuit=circuit,
    output_dir="out/eda_flow_fast",
    skip_stages=[8, 9],
)
print(f"跳过: {result['n_skipped']} 个 stage")
```

### 13.5 18 子模块完整流水线

除了 `run_eda_flow` 的 9 stage 主流程，PoLaRIS 还提供显式调用全部 18 子模块
的完整流水线示例：

```python
# 详见 examples/full_pipeline_18modules/main.py
# 18 子模块: core, pdk, place, route, sparam, pam4, fdtd, fde, eme, bpm,
#            fdfd, drc, lvs, inverse, boson, klm, gdsio, orchestrator
```

> 来源：`examples/full_pipeline_18modules/main.py`
> 运行: `python examples/full_pipeline_18modules/main.py`

---

## 附录 A 常见电路模板

### A.1 MZI 干涉仪（5 器件）

```
[GC1] → [MMI1] → [PS1] → [MMI2] → [GC2]
                 ↘──────────────↗
```

```python
from polaris_core import make_device, make_circuit

gc1 = make_device("gc1", "grating_coupler", 20, 20,
                  ports=[("in", 0, 10, "west"), ("out", 20, 10, "east")],
                  params={"insertion_loss_db": 1.9})
mmi1 = make_device("mmi1", "mmi_1x2", 30, 20,
                   ports=[("in", 0, 10, "west"),
                          ("out1", 30, 5, "east"), ("out2", 30, 15, "east")],
                   params={"insertion_loss_db": 0.4})
ps1 = make_device("ps1", "phase_shifter", 100, 10,
                  ports=[("in", 0, 5, "west"), ("out", 100, 5, "east")],
                  params={"neff": 2.4, "pi_voltage": 3.0})
mmi2 = make_device("mmi2", "mmi_2x2", 30, 20,
                   ports=[("in1", 0, 5, "west"), ("in2", 0, 15, "west"),
                          ("out1", 30, 10, "east")],
                   params={"insertion_loss_db": 0.5})
gc2 = make_device("gc2", "grating_coupler", 20, 20,
                  ports=[("in", 0, 10, "west"), ("out", 20, 10, "east")],
                  params={"insertion_loss_db": 1.9})

circuit = make_circuit(
    "MZI_100G", [gc1, mmi1, ps1, mmi2, gc2],
    [["gc1", "out", "mmi1", "in"],
     ["mmi1", "out1", "ps1", "in"],
     ["ps1", "out", "mmi2", "in1"],
     ["mmi1", "out2", "mmi2", "in2"],
     ["mmi2", "out1", "gc2", "in"]],
    canvas_w=500, canvas_h=300,
    optical_wavelength_nm=1550.0,
)
```

> 来源：`examples/full_pipeline_18modules/main.py`

### A.2 Clements 4×4 光矩阵（10 器件）

```
6 个 mmi_2x2 + 4 个 phase_shifter，构成 4×4 酉矩阵
```

> 详见 `examples/e2e_showcase/stages/stage2_circuit_spec.py`
> Clements et al., Optica 2016: https://doi.org/10.1364/OPTICA.3.001460

### A.3 量子玻色采样电路（12 器件）

```
4 输入耦合器 + 6 MZI + 4 相移器 + 4 输出耦合器 = 18 器件
```

> 详见 `examples/e2e_showcase/stages/stage7_gds_export.py`

---

## 附录 B 性能参考

### B.1 逆向设计 Benchmark

| 优化目标 | 改善 (dB) | 迭代步数 | 来源 |
|----------|-----------|----------|------|
| 硅波导宽度优化 | +14.72 | 50 | algorithm_handbook.md |
| MMI 1x2 | +16.59 | 50 | algorithm_handbook.md |
| WDM 滤波器 | +10.06 | 50 | algorithm_handbook.md |
| Y 分支 | +10.92 | 50 | algorithm_handbook.md |

### B.2 布局算法参数

| 算法 | 参数 | 默认值 |
|------|------|--------|
| DREAMPlace (analytical) | gamma | 4.0 |
| | density_weight | 1e-3 |
| | learning_rate | 0.01 |
| | max_iterations | 200 |
| AlphaChip (ppo_gnn) | _OBS_DIM | 8 |
| | _GNN_OUT_DIM | 16 |
| | _GNN_HIDDEN_DIM | 32 |
| | _GNN_NUM_LAYERS | 2 |
| | PHOTONIC_EDGE_DIM | 15 |

### B.3 布线损耗参数

| 参数 | 默认值 | 来源 |
|------|--------|------|
| PROPAGATION_LOSS_DB_CM | 3.0 dB/cm | Soref 1993 |
| BEND_LOSS_DB | 0.05 dB/bend | SiEPIC EBeam PDK |
| CROSSING_LOSS_DB | 0.3 dB/crossing | SiEPIC EBeam PDK |
| DEFAULT_MIN_BEND_RADIUS_UM | 5.0 μm | SiEPIC EBeam PDK |

### B.4 FDTD 仿真参数

| 参数 | 值 | 来源 |
|------|-----|------|
| C0 | 2.99792458e8 m/s | 物理常数 |
| SOI_N_SI | 3.476 | Palik |
| SOI_N_SIO2 | 1.444 | Palik |
| SOI_EPS_R_SI | 12.08 | n² |
| SOI_EPS_R_SIO2 | 2.085 | n² |
| CFL_SAFETY | 0.95 | Taflove 2005 |

### B.5 FDE 模式参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| width_um | 0.5 | 波导宽度 |
| height_um | 0.22 | 波导高度 |
| n_core | 3.476 | 硅核折射率 |
| n_clad | 1.444 | SiO2 包层折射率 |
| CONFINEMENT_THRESHOLD | 0.6 | 限制因子阈值 |
| V_CUTOFF_SINGLE_MODE | 2.405 | 单模截止 |

### B.6 Adjoint 优化参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| GRID_NX | 24 | X 网格数 |
| GRID_NY | 12 | Y 网格数 |
| GRID_NZ | 8 | Z 网格数 |
| GRID_DX_M | 0.2e-6 | 网格间距 |
| N_ITERATIONS | 50 | 迭代次数 |
| LEARNING_RATE | 0.5 | 学习率 |
| MOMENTUM | 0.3 | 动量系数（heavy-ball） |

### B.7 量子验证基准

| 验证项 | 理论值 | 来源 |
|--------|--------|------|
| 玻色采样概率总和 | 1.0 | 概率守恒 |
| HOM 凹陷深度 (θ=0) | 1.0 | Hong-Ou-Mandel 1987 |
| KLM CNOT 成功率 | 1/9 ≈ 0.1111 | Ralph 2002 |

### B.8 平台器件速查

| 平台 | 低损耗波导 (dB/cm) | 高速调制器 | 探测器 | 激光器 |
|------|---------------------|------------|--------|--------|
| SOI | strip_waveguide 2.0 | thermo_optic_phase_shifter Pπ=20mW | ge_photodetector 40GHz | — |
| SiN | sin_waveguide_lpcvd 0.1 | sin_thermo_optic Pπ=50mW | — | — |
| InP | inp_waveguide 2.0 | eam_modulator 45GHz / inp_mzm 40GHz | inp_photodetector 60GHz | dfb/dbr/sgdbr_laser |
| LNOI | lnoi_waveguide 0.4 | lnoi_eo_modulator 110GHz | — | — |

> 所有参数来源：`modules/pdk/src/polaris_pdk/devices.py`（R02 学术诚信，可溯源）

---

## 学术依据汇总（R02）

本指南所有参数/公式/算法均经文献溯源，核心文献如下：

1. SiEPIC EBeam PDK (220nm SOI): https://github.com/SiEPIC/SiEPIC_EBeam_PDK
2. Ligentec ANR PDK (SiN TriPleX): https://www.ligentec.com/
3. JePPIX / Pattern Project (InP): https://www.jeppix.eu/
4. HyperLight LNOI PDK (X-cut TFLN): https://hyperlightphotonics.com/
5. Soref et al. 1993 IEEE JQE (SOI 材料参数): https://ieeexplore.ieee.org/document/1148303
6. Chrostowski & Hochberg 2015 Silicon Photonics Design: https://doi.org/10.1017/CBO9781316084168
7. Kahng & Lienig 2009 IEEE TCAD (HPWL 布局): https://doi.org/10.1109/TCAD.2008.2012395
8. DREAMPlace DAC 2020 (解析法布局): https://doi.org/10.1109/DAC18072.2020.9218756
9. AlphaChip Nature 2021 (PPO-GNN): https://doi.org/10.1038/s41586-021-03544-w
10. LiDAR ISPD'25 (曲线感知布线): https://dl.acm.org/doi/10.1145/3698364.3705355
11. Yee 1966 IEEE TAP (FDTD): https://doi.org/10.1109/TAP.1966.1138693
12. Taflove 2005 Computational Electrodynamics: https://doi.org/10.1002/0471758467
13. Clements et al. 2016 Optica (幺正网络): https://doi.org/10.1364/OPTICA.3.001460
14. Hong, Ou, Mandel 1987 PRL (HOM 干涉): https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.59.2044
15. Ralph et al. 2002 (KLM CNOT): https://doi.org/10.1103/PhysRevA.65.012324
16. Knill, Laflamme, Milburn 2001 Nature (KLM 方案): https://doi.org/10.1038/35051009
17. Aaronson & Arkhipov 2011 (玻色采样): https://doi.org/10.1145/1993636.1993682
18. Wang et al. 2018 Nature (LNOI CMOS 调制器): https://doi.org/10.1038/s41586-018-0551-y
19. Saleh & Teich 2019 Fundamentals of Photonics (MZI 传输公式)
20. KLayout DRC runset: https://www.klayout.org/doc-qt5/manual/drc_runsets.html
21. KLayout LVS: https://www.klayout.org/doc-qt5/manual/lvs.html
22. JAX 自动微分: https://docs.jax.dev/
23. OpenROAD RTL-to-GDS: https://github.com/The-OpenROAD-Project/OpenROAD
24. TILOS MacroPlacement: https://github.com/TILOS-AI-Institute/MacroPlacement
25. gdsfactory PDK 框架: https://github.com/gdsfactory/gdsfactory
