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

| 字段 | 类型 | 说明 |
|------|------|------|
| name | str | 器件名称 |
| device_type | str | 器件类型 |
| width_um | float | 器件宽度 (μm) |
| height_um | float | 器件高度 (μm) |

## 布局引擎 (`polaris.engine`)

### FloorplanEnv

布局强化学习环境。

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
| canvas_w | float | 500.0 | 画布宽度 |
| canvas_h | float | 500.0 | 画布高度 |
| grid_size | float | 10.0 | 栅格大小 |
| expert_shaper | ExpertRewardShaper \| None | None | 专家奖励塑形器 |

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

# 采样动作
action, logprob, value = agent.get_action(obs)

# 存储转移
agent.store(Transition(obs, action, reward, logprob, value, done))

# PPO 更新
metrics = agent.update(last_value=0.0)

# 保存/加载检查点
agent.save("checkpoint.json")
agent.load("checkpoint.json")
```

### PPOAgentDiscrete

离散动作空间 PPO 智能体。

```python
from polaris.trainer.ppo_torch import PPOAgentDiscrete
from polaris.trainer.ppo_buffers import AgentSpec

agent = PPOAgentDiscrete(obs_dim=113, n_actions=400, hidden_dim=128)

# 类方法加载
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

### Simulator

S 参数仿真器。

```python
from polaris.sim.simulator import Simulator

sim = Simulator()
result = sim.simulate(circuit)
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

端到端布局布线流水线。

```python
from polaris.pipeline.integrated import IntegratedPipeline, PipelineConfig

pipeline = IntegratedPipeline(PipelineConfig())
result = pipeline.run(circuit)
```

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

## PDK 器件库 (`polaris.pdk`)

```python
from polaris.pdk.soi import SOI_CATALOG
from polaris.pdk.sin import SIN_CATALOG
from polaris.pdk.inp import INP_CATALOG
from polaris.pdk.lnoi import LNOI_CATALOG

# 列出所有器件
for name, device in SOI_CATALOG.devices.items():
    print(f"{name}: {device.description}")
```

## 来源

- PPO: Schulman et al., 2017, https://arxiv.org/abs/1707.06347
- GAE: Schulman et al., 2015, https://arxiv.org/abs/1506.02438
- ICLR'26 Expertise-Enhanced RL: https://openreview.net/forum?id=yqvNwfxRR6
- SB3 PPO: https://stable-baselines3.readthedocs.io/
- SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
