# PoLaRIS 光弈

> 光电子AI自动布局布线引擎（Photonic AI Place-and-Route Engine）

PoLaRIS（光弈）面向 SOI / SiN / InP / 薄膜铌酸锂（LNOI）等多工艺平台，提供器件资料库（PDK Lite）、AI 布局布线引擎、PPO 训练框架与版图评测的端到端流水线。

## 核心特性

- **四工艺平台 PDK**：SOI / SiN / InP / LNOI 器件模型库
- **AI 布局引擎**：GNN + CNN + Netlist + Routability 多策略融合
- **AI 布线引擎**：8 方向 A* + Rip-up&Reroute + 拥塞感知排序
- **PPO 训练框架**：PyTorch 加速 + 离散/连续 PPO + GAE + 专家奖励塑形
- **仿真系统**：S 参数级联 + 约束检查 + 校准验证
- **端到端流水线**：SimLoop 仿真回馈闭环 + IntegratedPipeline + TrainingPipeline
- **离线 wheel 包**：沙箱重启 70 秒一键恢复全部依赖

## 安装

### 方式一：离线一键安装（沙箱/新环境首选）

```bash
# 沙箱重启后必做：一键离线安装全部依赖（70 秒恢复）
bash 3dtool/wheels/install.sh --all

# 仅检查环境（不安装）
bash 3dtool/wheels/install.sh --check
```

### 方式二：联网 pip 安装

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## 快速开始

```bash
# 运行测试
python -m pytest tests/ -q --tb=short

# 启动 2M 轮 RL 训练（断点续训）
python scripts/train_2m.py

# 代码质量门禁
python scripts/code_quality_gate.py
```

## 代码质量

```bash
ruff check src/ tests/ 3dtool/          # lint 检查
ruff format --check src/ tests/ 3dtool/ # 格式检查
mypy src/polaris/ --ignore-missing-imports  # 类型检查
python scripts/code_quality_gate.py     # 质量门禁（文件/函数规模 + 圈复杂度）
```

## 项目结构

```
workspace/
├── 3dtool/              # 三方工具统一管理
│   ├── wheels/              # 离线 wheel 包（沙箱重启一键恢复）
│   ├── layout/              # 版图类工具（klayout/gdsfactory）
│   ├── simulation/          # 仿真类工具（simphony/sax/SiPANN）
│   ├── ml/                  # 机器学习类工具（torch/gymnasium/networkx）
│   ├── numeric/             # 数值计算类工具（numpy/scipy）
│   ├── viz/                 # 可视化类工具（matplotlib）
│   ├── serialization/       # 序列化类工具（pyyaml）
│   └── pycopy/              # 自研复刻工具（pyCopyTorch/pyCopySAX/...）
├── src/polaris/         # 所有自研代码（src layout）
│   ├── data/            # 数据加载与电路规格
│   ├── engine/          # 布局引擎（FloorplanEnv/GNN/CNN/Netlist）
│   ├── eval/            # 评估与渲染
│   ├── nn/              # 纯 NumPy 神经网络库（pyCopyTorch 复刻）
│   ├── pdk/             # 光子器件库（SOI/SiN/InP/LNOI）
│   ├── pipeline/        # 端到端流水线
│   ├── router/          # 布线引擎
│   ├── sim/             # 仿真系统（S参数/级联/约束检查/校准）
│   └── trainer/         # 训练器（PPO/GNN_PPO/reward_shaping/train_loop）
├── publish/             # 产品发布制品
│   ├── wheels/              # 构建 wheel 包
│   ├── docs/                # 用户文档
│   └── examples/            # 使用示例
├── tests/               # 测试代码（770+ 测试用例）
├── scripts/             # 工具脚本（训练/质量门禁/监控）
├── data/                # 数据（基准电路/变体数据集）
├── checkpoints/         # 训练检查点（.gitignore）
├── docs/                # 项目文档
└── pyproject.toml       # 项目配置
```

## 模块说明

| 模块 | 职责 | 关键类 |
|------|------|--------|
| `pdk` | 光子器件库 | SOI/SiN/InP/LNOI 四平台器件模型 |
| `engine` | 布局引擎 | FloorplanEnv, GNN, CNN, Netlist |
| `router` | 布线引擎 | WaveguideRouter, RoutingEnv |
| `trainer` | AI 训练 | PPOAgent, PPOAgentDiscrete, ExpertRewardShaper |
| `sim` | 仿真系统 | Simulator, Cascade, ConstraintChecker, Calibration |
| `pipeline` | 端到端流水线 | SimLoop, IntegratedPipeline, TrainingPipeline |
| `eval` | 评测渲染 | LayoutRender |
| `nn` | NumPy 神经网络 | Tensor, Linear, Adam（pyCopyTorch 复刻） |
| `data` | 数据加载 | CircuitSpec, DeviceSpec, VariantGenerator |

## 技术来源

- PPO: Schulman et al., 2017, https://arxiv.org/abs/1707.06347
- GAE: Schulman et al., 2015, https://arxiv.org/abs/1506.02438
- ICLR'26 Expertise-Enhanced RL: https://openreview.net/forum?id=yqvNwfxRR6
- Google Nature 2021: https://www.nature.com/articles/s41586-021-03544-w
- ChiPFormer ICML'23: https://arxiv.org/pdf/2306.14744.pdf
- SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK

## 许可证

MIT
