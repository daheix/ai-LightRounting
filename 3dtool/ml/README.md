# ml/ — 机器学习类工具

存放机器学习与图算法相关的第三方工具说明。

## 工具清单

### torch

- **用途**: GNN/PPO 神经网络、强化学习
- **状态**: ✅ 已装 2.12.1+cpu（CPU 版，规则 26 GPU 不参与）
- **许可**: BSD-3-Clause（✅可商用）
- **来源**: https://pytorch.org/
- **安装**: `pip install torch`
- **项目使用**:
  - `src/polaris/trainer/ppo_torch.py` — PyTorch PPO 实现
  - `src/polaris/trainer/ppo_networks.py` — ActorCritic 网络

### gymnasium

- **用途**: 布局/布线 RL 环境（observation/action/reward）
- **状态**: ✅ 已装 1.3.0
- **许可**: MIT（✅可商用）
- **来源**: https://gymnasium.farama.org/
- **安装**: `pip install gymnasium`
- **项目使用**:
  - `src/polaris/engine/floorplan_env.py` — 布局 RL 环境
  - `src/polaris/router/routing_env.py` — 布线 RL 环境

### networkx

- **用途**: 器件连接图建模、最短路径、图算法
- **状态**: ✅ 已装 3.6.1
- **许可**: BSD-3-Clause（✅可商用）
- **来源**: https://networkx.org/
- **安装**: `pip install networkx`
- **项目使用**: `src/polaris/engine/netlist.py` 构建连接图
