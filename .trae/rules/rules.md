# 开源工具集成规则 (Open Source Integration Rules)

本文件定义 PoLaRIS（光弈）项目的开源工具集成策略：能直接集成的全部集成，不好集成的用 Python 100% 复刻。

## 规则 2：开源工具最大化集成（强制）

### 2.1 必须直接集成的开源工具（pip 安装即用）

| 工具 | 用途 | 来源 |
|------|------|------|
| **gdsfactory** | 版图生成、PDK、自动布线、GDS/OASIS 导出 | https://gdsfactory.github.io/gdsfactory/ |
| **klayout** (klayout python) | DRC 规则检查、LVS、版图查看 | https://www.klayout.de/ |
| **networkx** | 器件连接图建模、最短路径、图算法 | https://networkx.org/ |
| **numpy / scipy** | 数值计算、优化求解 | https://numpy.org/ |
| **torch** | GNN/PPO 神经网络、强化学习 | https://pytorch.org/ |
| **gymnasium** | 布局/布线 RL 环境（observation/action/reward） | https://gymnasium.farama.org/ |
| **matplotlib** | 版图渲染、拥塞热力图 | https://matplotlib.org/ |
| **shapely** | 几何运算（多边形、缓冲区、相交检测） | https://shapely.readthedocs.io/ |
| **pyyaml** | 网表/配置序列化 | https://pyyaml.org/ |

### 2.2 可选集成（按需引入）

| 工具 | 用途 | 来源 |
|------|------|------|
| **gdstk** | 高性能 GDS 文件读写（替代 gdspy） | https://heitzmann.github.io/gdstk/ |
| **MEEP** | FDTD 电磁仿真（器件参数验证） | https://meep.readthedocs.io/ |
| **Simphony** | 光子电路 S 参数仿真 | https://simphonyphotonics.readthedocs.io/ |
| **SAX** | 光子电路频率域仿真 | https://flaport.github.io/sax/ |
| **SiPANN** | 硅光器件模型（耦合器、环谐振器） | https://sipann.readthedocs.io/ |
| **femwell** | FEM 模式求解器 | https://helgegehring.github.io/femwell/ |
| **meow** | 模式求解器 | https://github.com/flaport/meow |
| **lygadgets** | KLayout Python 工具链 | https://github.com/atait/lygadgets |
| **SiEPIC-EBeam-PDK** | 开源硅光 PDK（UBC/SiEPIC） | https://github.com/gdsfactory/ubc |
| **cspdk** | Cornerstone 开源 PDK | https://github.com/gdsfactory/cspdk |
| **vtt PDK** | VTT 开源 SiN PDK | https://github.com/gdsfactory/vtt |

### 2.3 需 Python 100% 复刻的工具（无法直接集成时）

以下能力若无合适开源库或集成成本过高，须用纯 Python 100% 复刻一个可用版本：

| 能力 | 复刻方案 | 参考 |
|------|----------|------|
| 波导约束布线器 | A*/Lee 算法 + 弯曲半径/间距/等长约束 | NeurIPS 2022 Cheng et al. https://openreview.net/pdf?id=uNYqDfPEDD8 |
| 光子器件 PDK Lite | dataclass + 真实文献参数（spec.md 已列来源） | 本项目 spec.md |
| GNN 状态编码器 | PyTorch message-passing GNN | R-GCN, Basso et al. NeurIPS 2025 |
| PPO 强化学习 | actor-critic + clip + GAE | Stable-Baselines3 / CleanRL 参考 |
| 拥塞热力图 | numpy 栅格化 + matplotlib | — |
| 网表解析器 | YAML/JSON → networkx 图 | — |
| HPWL 线长估计 | 半周长线长公式 | 经典 EDA 方法 |
| S 弯/弯曲路径生成 | 贝塞尔/欧拉曲线 | 光波导标准方法 |

### 2.4 集成原则
1. **优先直接集成**：能用 pip 安装的开源库，直接集成，不重复造轮子
2. **复刻须 100% 可用**：不好集成的，用纯 Python 复刻一个完整可用的版本，不留半成品
3. **来源须标注**：每个集成的工具或复刻的算法，记录来源 URL
4. **依赖最小化**：核心功能（PDK + 布局 + 布线 + 训练）的依赖须精简，仿真类工具（MEEP/Simphony）作为可选依赖
5. **不依赖商业工具**：禁止依赖 Lumerical/IPKISS/Tidy3D 等商业软件作为核心功能

## 参考来源
- GDSFactory 论文 (CLEO 2026): https://raw.githubusercontent.com/gdsfactory/gdsfactory-paper-cleo26/gh-pages/gdsfactory.pdf
- Awesome Photonics: https://github.com/joamatab/awesome_photonics
- Simphony 文档: https://simphonyphotonics.readthedocs.io/en/stable/
- Prefab: Python for photonics: https://docs.prefabphotonics.com/python-for-photonics/
