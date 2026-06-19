# PoLaRIS API 参考

## 数据层 (`polaris.data`)

### CircuitSpec

电路规格定义。

```python
from polaris.data.specs import CircuitSpec, DeviceSpec

circuit = CircuitSpec(
    name="mzi",
    devices=[DeviceSpec(name="gc1", device_type="grating_coupler", width_um=10.0, height_um=10.0)],
    connections=[("gc1", "o1", "mmi1", "o1")],
    canvas_w=200.0,
    canvas_h=200.0,
)
```

| 字段 | 类型 | 说明 |
|------|------|------|
| name | str | 电路名称 |
| devices | list[DeviceSpec] | 器件列表 |
| connections | list[tuple] | 连接列表 [(dev1, port1, dev2, port2)] |
| canvas_w | float | 画布宽度 (μm) |
| canvas_h | float | 画布高度 (μm) |

### DeviceSpec

器件规格定义。

```python
DeviceSpec(
    name="mmi1",
    device_type="mmi_1x2",
    width_um=20.0,
    height_um=10.0,
    ports=[("o1", 0.0, 0.0, "E"), ("o2", 20.0, 0.0, "E")],
    params={"gap": 0.3},
)
```

| 字段 | 类型 | 说明 |
|------|------|------|
| name | str | 器件名称 |
| device_type | str | 器件类型 |
| width_um | float | 器件宽度 (μm) |
| height_um | float | 器件高度 (μm) |
| ports | list[tuple[str, float, float, str]] | 端口列表 [(name, dx, dy, direction)] |
| params | dict | 器件参数 |

### load_gds_to_circuit

从 SiEPIC GDS 文件提取电路规格。

```python
from polaris.data.gds_loader import load_gds_to_circuit

circuit = load_gds_to_circuit("path/to/layout.gds")
```

| 参数 | 类型 | 说明 |
|------|------|------|
| gds_path | str \| Path | GDS 文件路径 |

**返回**: `CircuitSpec`（含器件列表与连接列表）

**异常**: `FileNotFoundError`（文件不存在）、`ImportError`（klayout 未安装）

### 数据加载器

```python
from polaris.data.data_loader import (
    load_pic_ir, load_gdsfactory_yaml, load_picbench, load_phido, load_directory,
)

circuit = load_pic_ir("data/benchmarks/lidar_clements_8x8.json")
circuits = load_directory("data/benchmarks/", fmt="auto")
```

## 布局引擎 (`polaris.engine`)

### FloorplanEnv

布局强化学习环境（Gymnasium 接口）。

```python
from polaris.engine.floorplan_env import FloorplanEnv, FloorplanEnvConfig

env = FloorplanEnv(net, devices, config=FloorplanEnvConfig(
    canvas_w=200.0,
    canvas_h=200.0,
    grid_size=20.0,
    expert_shaper=shaper,  # 可选：专家奖励塑形
))
obs, info = env.reset()
obs, reward, done, truncated, info = env.step(action)
```

### FloorplanEnvConfig

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| canvas_w | float | 1000.0 | 画布宽度 |
| canvas_h | float | 1000.0 | 画布高度 |
| grid_size | float | 10.0 | 栅格分辨率 (μm) |
| overlap_penalty | float | 3.0 | 重叠惩罚权重 |
| hpwl_weight | float | 0.01 | HPWL 线长权重 |
| area_reward | float | 0.5 | 面积利用率奖励权重 |
| expert_shaper | ExpertRewardShaper \| None | None | 专家奖励塑形器 |
| state_encoder | GNN \| None | None | GNN 状态编码器 |

### load_netlist

一站式加载：解析网表 → 实例化器件 → 构建图。

```python
from polaris.engine.netlist import load_netlist

net, devices, graph = load_netlist("data/benchmarks/mzi.json")
```

| 参数 | 类型 | 说明 |
|------|------|------|
| data | str \| Path \| dict | YAML/JSON 文件路径或字典 |

**返回**: `tuple[Netlist, dict[str, Device], nx.Graph]`

## 布线引擎 (`polaris.router`)

### WaveguideRouter

波导布线器（A* + 拥塞感知）。

```python
from polaris.router.waveguide_router import WaveguideRouter

router = WaveguideRouter(
    placements=placements,
    netlist=net,
    canvas_w=200.0,
    canvas_h=200.0,
)
routes = router.route_all()
```

### RoutingEnv

布线强化学习环境。

```python
from polaris.router.routing_env import RoutingEnv

env = RoutingEnv(net, placements, canvas_w=200.0, canvas_h=200.0, grid_size=20.0)
```

## 训练器 (`polaris.trainer`)

### PPOAgent

连续动作空间 PPO 智能体（PyTorch 实现）。

```python
from polaris.trainer.ppo_torch import PPOAgent, PPOConfig, Transition

agent = PPOAgent(
    obs_dim=113,
    action_dim=3,
    config=PPOConfig(lr=3e-4, n_epochs=4, batch_size=64),
    hidden_dim=128,
)

action, logprob, value = agent.get_action(obs)
agent.store(Transition(obs, action, reward, logprob, value, done))
metrics = agent.update(last_value=0.0)
agent.save("checkpoint.json")
agent.load("checkpoint.json")
```

### PPOAgentDiscrete

离散动作空间 PPO 智能体。

```python
from polaris.trainer.ppo_torch import PPOAgentDiscrete
from polaris.trainer.ppo_buffers import AgentSpec

agent = PPOAgentDiscrete(obs_dim=113, n_actions=400, config=config, hidden_dim=128)

spec = AgentSpec(obs_dim=113, n_actions=400, hidden_dim=128)
agent = PPOAgentDiscrete.load("checkpoint.pt", config, spec)
```

### PPOConfig

PPO 超参数配置。

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| lr | float | 3e-4 | 学习率 |
| gamma | float | 0.99 | 折扣因子 |
| gae_lambda | float | 0.95 | GAE lambda |
| clip_eps | float | 0.2 | PPO clip 范围 |
| ent_coef | float | 0.01 | 熵系数 |
| vf_coef | float | 0.5 | 价值损失系数 |
| max_grad_norm | float | 0.5 | 梯度裁剪 |
| n_epochs | int | 4 | 每次 rollout 更新轮数 |
| batch_size | int | 64 | 小批量大小 |
| clip_vf | float | 0.0 | 价值函数 clip（0=禁用） |
| lr_schedule | str | "constant" | 学习率调度（constant/cosine/linear） |
| lr_warmup_steps | int | 0 | warmup 步数 |
| total_steps | int | 1000 | 总训练步数（用于 cosine 调度） |

### ExpertRewardShaper

专家知识奖励塑形器（ICLR'26）。

```python
from polaris.trainer.reward_shaping import ExpertRewardShaper, ExpertRewardInput, ExpertRewardConfig

shaper = ExpertRewardShaper(ExpertRewardConfig(
    port_alignment_weight=0.3,
    bend_violation_weight=0.5,
    crossing_weight=0.2,
    congestion_weight=0.2,
    thermal_weight=0.1,
    min_bend_radius_um=5.0,
))

result = shaper.compute(ExpertRewardInput(
    device_positions={"a": (0.0, 0.0), "b": (100.0, 0.0)},
    connections=[("a", "p1", "b", "p2")],
    congestion_map=cong_map,  # 可选
    thermal_sources={"heater"},  # 可选
    thermal_sensitive={"ring"},  # 可选
))
```

## 仿真系统 (`polaris.sim`)

### CircuitSimulator

S 参数仿真器。

```python
from polaris.sim.simulator import CircuitSimulator

sim = CircuitSimulator()
result = sim.simulate(circuit)
```

### SimLoop

仿真回馈闭环（布局 → 布线 → 仿真 → 约束检查 → 反馈调整 → 迭代）。

```python
from polaris.sim.sim_loop import SimLoop, SimLoopConfig

loop = SimLoop(
    placer=placer,
    router=router,
    simulator=simulator,
    config=SimLoopConfig(max_iterations=3),
)
result = loop.run(circuit)
```

### SimLoopResult

| 字段 | 类型 | 说明 |
|------|------|------|
| success | bool | 是否成功（无约束违规） |
| placements | dict | 最终器件布局 |
| paths | dict | 最终布线路径 |
| total_loss_db | float | 总插入损耗 (dB) |
| n_crossings | int | 交叉数 |
| violations | list[Violation] | 最终违规列表 |
| iterations | int | 实际迭代次数 |
| feedback_history | list[FeedbackResult] | 每轮反馈记录 |

### ConstraintChecker

约束检查器（8 种违规检查）。

```python
from polaris.sim.constraint_checker import ConstraintChecker, ConstraintConfig, CheckContext

checker = ConstraintChecker(ConstraintConfig(
    min_bend_radius_um=5.0,
    max_insertion_loss_db=5.0,
))
ctx = CheckContext(total_loss_db=2.5, n_crossings=0)
violations = checker.check(placements=placements, paths=paths, context=ctx)
```

### calibrate

仿真校准函数。

```python
from polaris.sim.calibration import calibrate, CalibrationConfig

result = calibrate(CalibrationConfig(
    loss_tolerance_db=0.5,
    benchmark_dir="data/benchmarks",
    max_calibration_rounds=5,
))
```

### CalibrationResult

| 字段 | 类型 | 说明 |
|------|------|------|
| items | list[CalibrationItem] | 各电路校准结果 |
| total_items | int | 总校准项数 |
| passed_items | int | 通过项数 |
| max_error_db | float | 最大误差 (dB) |
| mean_error_db | float | 平均误差 (dB) |
| all_passed | bool | 是否全部通过 |

## 流水线 (`polaris.pipeline`)

### IntegratedPipeline

端到端布局布线流水线（推荐入口）。

```python
from polaris.pipeline.integrated import IntegratedPipeline, PipelineConfig

pipeline = IntegratedPipeline(PipelineConfig(
    canvas_w=200.0,
    canvas_h=200.0,
    grid_size=10.0,
    max_sim_iterations=3,
    loss_target_db=5.0,
    min_bend_radius_um=5.0,
    output_dir="out",
    placement_checkpoint=None,
    use_real_simulator=False,
))
result = pipeline.run(circuit)
```

### PipelineConfig

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| canvas_w | float | 1000.0 | 画布宽度 (μm) |
| canvas_h | float | 1000.0 | 画布高度 (μm) |
| grid_size | float | 10.0 | 栅格大小 (μm) |
| max_sim_iterations | int | 3 | SimLoop 最大迭代次数 |
| router_type | str | "curvy" | 布线器类型 |
| loss_target_db | float | 5.0 | 目标插入损耗 (dB) |
| min_bend_radius_um | float | 5.0 | 最小弯曲半径 (μm) |
| output_dir | str | "out" | 输出目录 |
| placement_checkpoint | str \| None | None | RL 布局 agent 检查点路径 |
| use_real_simulator | bool | False | 是否使用真实 S 参数仿真器 |

### PipelineResult

| 字段 | 类型 | 说明 |
|------|------|------|
| success | bool | 是否成功 |
| circuit_name | str | 电路名称 |
| n_devices | int | 器件数 |
| n_connections | int | 连接数 |
| placements | dict | 器件布局 |
| paths | dict | 布线路径 |
| total_loss_db | float | 总插入损耗 (dB) |
| n_crossings | int | 交叉数 |
| drc_passed | bool | DRC 是否通过 |
| sim_iterations | int | 仿真迭代次数 |
| report_path | str | 报告路径 |
| gds_path | str | GDS 文件路径 |

### TrainingPipeline

RL 训练流水线（接入真正 PPO 训练）。

```python
from polaris.pipeline.training import TrainingPipeline, TrainingConfig

pipeline = TrainingPipeline(TrainingConfig(
    benchmark_dir="data/benchmarks",
    num_episodes=1000,
    rollout_steps=32,
    canvas_w=200.0,
    canvas_h=200.0,
    grid_size=20.0,
    hidden_dim=128,
    train_floorplan_enabled=True,
    train_routing_enabled=True,
))
result = pipeline.train()
```

### TrainingResult

| 字段 | 类型 | 说明 |
|------|------|------|
| episodes_completed | int | 完成的训练轮次 |
| best_reward | float | 最佳奖励 |
| avg_loss_db | float | 平均损耗 (dB) |
| calibration_passed | bool | 校准是否通过 |
| calibration_result | CalibrationResult | 校准详细结果 |
| checkpoint_path | str | 检查点路径 |
| floorplan_logs | list[dict] | 布局训练日志 |
| routing_logs | list[dict] | 布线训练日志 |

### CLI 入口

```python
from polaris.pipeline import main

# 等价于 python -m polaris
exit_code = main(["run", "--netlist", "circuit.yaml", "--output", "out/"])
```

## PDK 器件库 (`polaris.pdk`)

### DeviceCatalog

光器件清单注册表，支持按平台/类别检索与序列化。

```python
from polaris.pdk import default_catalog, DeviceCatalog

# 默认目录（含四大平台全部器件）
catalog = default_catalog()
print(f"总器件数: {len(catalog)}")

# 检索 API
devices = catalog.list_devices(platform="SOI", category="passive")
device = catalog.get("device_id")               # 按 device_id
device = catalog.get("mmi_1x2", platform="SOI")  # 按名+平台

# 序列化
catalog.to_json("catalog.json")
catalog.to_yaml("catalog.yaml")
catalog2 = DeviceCatalog.from_json("catalog.json")

# 来源溯源校验
missing = catalog.validate_sources()
```

### list_devices / get_device

```python
catalog = default_catalog()

# 列出器件（可按平台/类别过滤）
all_devices = catalog.list_devices()                       # 全部
soi_devices = catalog.list_devices(platform="SOI")          # 仅 SOI
soi_passive = catalog.list_devices(platform="SOI", category="passive")

# 获取单个器件
device = catalog.get("soi::mmi_1x2", platform="SOI")
```

| 方法 | 签名 | 说明 |
|------|------|------|
| `list_devices` | `(platform=None, category=None) -> list[Device]` | 按平台/类别组合检索 |
| `list_by_platform` | `(platform: str) -> list[Device]` | 按平台检索 |
| `list_by_category` | `(category: str) -> list[Device]` | 按类别检索 |
| `get` | `(device_id, platform=None) -> Device` | 检索单个器件 |
| `names` | `(platform=None) -> list[str]` | 已注册器件名列表 |
| `validate_sources` | `() -> list[str]` | 校验来源溯源 |

### Device / Port / Source

```python
from polaris.pdk import Device, Port, Direction, Source, BoundingBox

device = Device(
    device_id="soi::mmi_1x2",
    platform="SOI",
    category="passive",
    name="mmi_1x2",
    ports=[Port(name="in", x=0.0, y=0.0, direction=Direction.EAST,
                waveguide_type="strip", width=0.5)],
    bbox=BoundingBox(xmin=0, ymin=0, xmax=20, ymax=10),
    params={"gap": 0.3},
    source=Source(title="...", authors="...", year=2020, url="https://..."),
)
```

### SiEPIC 器件名映射

SiEPIC EBeam PDK 真实器件名 ↔ PoLaRIS 器件名双向映射。

```python
from polaris.pdk.siepic_mapping import (
    siepic_to_polaris, polaris_to_siepic,
    SIEPIC_TO_POLARIS, POLARIS_TO_SIEPIC,
)

# SiEPIC → PoLaRIS
polaris_name = siepic_to_polaris("ebeam_y_1550")           # → "y_branch"
polaris_name = siepic_to_polaris("ebeam_gc_te1550")        # → "grating_coupler_1d"
polaris_name = siepic_to_polaris("ebeam_dc_halfring_te1550")  # → "ring_resonator"

# PoLaRIS → SiEPIC
siepic_name = polaris_to_siepic("y_branch")                # → "ebeam_y_1550"
```

| 函数 | 签名 | 说明 |
|------|------|------|
| `siepic_to_polaris` | `(siepic_name: str) -> str \| None` | SiEPIC → PoLaRIS 器件名 |
| `polaris_to_siepic` | `(polaris_name: str) -> str \| None` | PoLaRIS → SiEPIC 器件名 |

### gdsfactory 集成（可选）

```python
from polaris.pdk.gdsfactory_integration import (
    is_available, generate_mzi_gds, generate_ring_resonator_gds,
    generate_component_gds, list_available_components,
)

if is_available():
    generate_mzi_gds("out/mzi.gds", delta_length_um=100.0, bend_radius_um=5.0)
    generate_ring_resonator_gds("out/ring.gds", radius_um=5.0, gap_nm=200.0)
    generate_component_gds("mmi1x2", "out/mmi.gds", length=10.0)
```

### 四大平台器件库

```python
from polaris.pdk.soi import SOI_CATALOG, SOI_DEVICES
from polaris.pdk.sin import SIN_CATALOG, SIN_DEVICES
from polaris.pdk.inp import INP_CATALOG, INP_DEVICES
from polaris.pdk.lnoi import LNOI_CATALOG, LNOI_DEVICES

# 查询 SOI 平台器件
for name, device in SOI_CATALOG.devices.items():
    print(f"{name}: {device.description}")
```

## 版图渲染与导出 (`polaris.eval`)

### export_gds / export_oasis

```python
from polaris.eval.layout_render import export_gds, export_oasis, render_layout, RenderOptions

export_gds(placements, paths, "out/layout.gds")
export_oasis(placements, paths, "out/layout.oas")
render_layout(placements, paths, options=RenderOptions(save_path="out/layout.png"))
```

### run_drc

DRC 检查（器件重叠 + 间距 + 弯曲半径）。

```python
from polaris.eval.layout_render import run_drc

report = run_drc(placements, paths)
print(f"通过: {report.passed}, 总违规: {report.total_violations}")
print(f"  重叠: {report.overlap_violations}")
print(f"  间距: {report.spacing_violations}")
print(f"  弯曲半径: {report.min_bend_radius_violations}")
```

## 来源

- PPO: Schulman et al., 2017, https://arxiv.org/abs/1707.06347
- GAE: Schulman et al., 2015, https://arxiv.org/abs/1506.02438
- ICLR'26 Expertise-Enhanced RL: https://openreview.net/forum?id=yqvNwfxRR6
- Apollo arXiv 2025: https://arxiv.org/html/2504.18813v1
- SB3 PPO: https://stable-baselines3.readthedocs.io/
- SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- gdsfactory: https://gdsfactory.github.io/gdsfactory/
- klayout: https://www.klayout.de/
- Simphony: https://simphonyphotonics.readthedocs.io/
- SAX: https://flaport.github.io/sax/
