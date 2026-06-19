# PoLaRIS 光弈

> 光电子AI智能布局布线引擎（Photonic AI Place-and-Route Engine）

PoLaRIS（光弈）面向 SOI / SiN / InP / 薄膜铌酸锂（LNOI）等多工艺平台，提供器件资料库（PDK Lite）、AI 布局布线引擎、PPO 训练框架与版图评测的端到端流水线。从网表（YAML/JSON/GDS）到 GDS 版图导出与 DRC 校验一站式自动化，结合强化学习与专家知识奖励塑形实现布线感知布局优化。

## 核心特性

- **RL 布局引擎**：PPO + GNN/CNN 多策略融合，HPWL/拥塞/面积多目标奖励
- **A\* 布线引擎**：8 方向 A* + Rip-up&Reroute + 拥塞感知排序
- **S 参数仿真**：S 参数级联 + SimLoop 反馈闭环 + 校准验证
- **GDS 导出**：klayout.db 导出 SiEPIC 格式 GDSII/OASIS
- **DRC 校验**：8 种违规检查（弯曲半径/间距/损耗/交叉/重叠/最小宽度/耦合间隙等）
- **四工艺平台 PDK**：SOI / SiN / InP / LNOI 器件模型库（81 个器件，全部来源溯源）
- **SiEPIC 集成**：GDS 网表提取 + 器件名双向映射 + gdsfactory 可选集成
- **PPO 训练框架**：PyTorch 加速 + 离散/连续 PPO + GAE + 专家奖励塑形（ICLR'26）
- **离线 wheel 包**：沙箱重启 70 秒一键恢复全部依赖

## 快速开始

```bash
# 1. 安装依赖（沙箱/离线环境首选）
bash 3dtool/wheels/install.sh --all

# 2. 运行端到端流水线（网表 → 布局 → 布线 → GDS → DRC）
python -m polaris run --netlist data/benchmarks/mzi.json --output out/

# 3. Python API 快速演示
python publish/examples/02_pipeline_e2e.py

# 4. 运行测试
python -m pytest tests/ -q --tb=short
```

```python
# Python API 示例
from polaris.pipeline.integrated import IntegratedPipeline

result = IntegratedPipeline().run()  # 内置默认 MZI 电路
print(f"成功: {result.success}, 损耗: {result.total_loss_db:.2f} dB")
```

## 文档

- [用户手册](./publish/docs/用户手册.md) — 安装、CLI、Python API、完整工作流
- [API 参考](./publish/docs/API参考.md) — 核心类与函数签名
- [安装指南](./publish/docs/安装指南.md) — 详细安装步骤与依赖清单
- [示例代码](./publish/examples/) — 4 个可运行示例脚本
- [项目规则](./.trae/rules/project_rules.md) — 开发规范与质量门禁

## 安装

### 方式一：离线一键安装（沙箱/新环境首选）

```bash
bash 3dtool/wheels/install.sh --all      # 70 秒恢复全部依赖
bash 3dtool/wheels/install.sh --check    # 仅检查环境
```

### 方式二：联网 pip 安装

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## CLI 用法

```bash
# 端到端运行
python -m polaris run --netlist circuit.yaml --output out/

# PPO 训练
python -m polaris train --episodes 50 --output checkpoints/

# 器件目录查询
python -m polaris catalog --platform SOI
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
│   ├── data/            # 数据加载与电路规格（CircuitSpec/GDS loader）
│   ├── engine/          # 布局引擎（FloorplanEnv/GNN/CNN/Netlist）
│   ├── eval/            # 评估与渲染（GDS导出/DRC）
│   ├── nn/              # 纯 NumPy 神经网络库（pyCopyTorch 复刻）
│   ├── pdk/             # 光子器件库（SOI/SiN/InP/LNOI + SiEPIC mapping）
│   ├── pipeline/        # 端到端流水线（IntegratedPipeline/TrainingPipeline）
│   ├── router/          # 布线引擎（WaveguideRouter/RoutingEnv）
│   ├── sim/             # 仿真系统（S参数/级联/约束检查/SimLoop/校准）
│   └── trainer/         # 训练器（PPO/GNN_PPO/reward_shaping/train_loop）
├── publish/             # 产品发布制品
│   ├── wheels/              # 构建 wheel 包
│   ├── docs/                # 用户文档（用户手册/API参考/安装指南）
│   └── examples/            # 使用示例（4 个可运行脚本）
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
| `pdk` | 光子器件库 | SOI/SiN/InP/LNOI 四平台器件模型 + SiEPIC 映射 |
| `engine` | 布局引擎 | FloorplanEnv, GNN, CNN, Netlist |
| `router` | 布线引擎 | WaveguideRouter, RoutingEnv |
| `trainer` | AI 训练 | PPOAgent, PPOAgentDiscrete, ExpertRewardShaper |
| `sim` | 仿真系统 | Simulator, SimLoop, ConstraintChecker, Calibration |
| `pipeline` | 端到端流水线 | SimLoop, IntegratedPipeline, TrainingPipeline |
| `eval` | 评测渲染 | LayoutRender, export_gds, run_drc |
| `nn` | NumPy 神经网络 | Tensor, Linear, Adam（pyCopyTorch 复刻） |
| `data` | 数据加载 | CircuitSpec, DeviceSpec, load_gds_to_circuit |

## 技术来源

- PPO: Schulman et al., 2017, https://arxiv.org/abs/1707.06347
- GAE: Schulman et al., 2015, https://arxiv.org/abs/1506.02438
- ICLR'26 Expertise-Enhanced RL: https://openreview.net/forum?id=yqvNwfxRR6
- Apollo arXiv 2025: https://arxiv.org/html/2504.18813v1
- Google Nature 2021: https://www.nature.com/articles/s41586-021-03544-w
- ChiPFormer ICML'23: https://arxiv.org/pdf/2306.14744.pdf
- SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- gdsfactory: https://gdsfactory.github.io/gdsfactory/
- klayout: https://www.klayout.de/
- Simphony: https://simphonyphotonics.readthedocs.io/
- SAX: https://flaport.github.io/sax/

## 许可证

MIT
