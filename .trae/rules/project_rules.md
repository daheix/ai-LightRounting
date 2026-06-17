# 项目规则 (Project Rules)

本文件定义了 PoLaRIS（光弈）光电子AI智能布局布线引擎项目的强制开发规则。所有任务执行必须严格遵守。

## 规则 1：方案检索与代码提交纪律（强制）

每一个小任务（SubTask）在动手实现之前与实现过程中，都必须执行以下流程：

### 1.1 方案检索（动手前必做）
- 必须检索各种期刊、论文、白皮书以及各大高校的论文论坛，寻找最合理、最优秀的解决方案。
- 检索来源至少覆盖：
  - 学术期刊与会议：Nature、Nature Photonics、Optics Express、Optics Letters、Light: Advanced Manufacturing、IEEE JSTQE、NeurIPS、ICCAD、DAC、Advanced Optics Photonics
  - 工艺手册与白皮书：IMEC、AMF、AIM Photonics、CompoundTek、IHP、LioniX、NOEIC、三星、台积电等 foundry PDK 与白皮书
  - 高校论文论坛与开放仓库：arXiv、ResearchGate、IEEE Xplore、GitHub（如 Thinklab-SJTU/EDA-AI）、高校课题组主页
  - 技术博客与产业分析：latitudeda.com、iccsz.com、cloud.tencent.com、mdpi.com 等
- 每个方案须记录：来源标题、作者/机构、年份、网址 URL，写入对应模块的 `source` 字段或文档。
- 禁止使用未经检索核实的参数或方案；禁止假数据。

### 1.2 代码提交纪律（每 5 分钟一次）
- 实现过程中，每 5 分钟必须向远端 `main` 分支提交一次代码。
- 提交流程：
  1. `git add` 相关变更文件（按文件名精确添加，禁止 `git add -A`/`git add .`）
  2. `git commit -m "<type>: <简述>"`，type 遵循 Conventional Commits（feat/fix/docs/refactor/test/chore）
  3. `git push origin main`
- 若 5 分钟内仍在进行复杂改动，先创建一个可编译/可测试的中间状态再提交，保证 `main` 分支始终可用。
- 提交前必须通过本地 lint/typecheck（如 ruff、mypy、pytest 冒烟测试）。
- 禁止 force push 到 `main`；禁止提交含密钥/凭据的文件。

### 1.3 完整产品流程遵守
- 完整的产品研发流程必须遵守，不得跳过：
  1. 需求与方案检索（本规则 1.1）
  2. 设计（数据结构、接口、模块划分）
  3. 实现（编码 + 每 5 分钟提交）
  4. 测试（单元测试 + 集成测试 + 约束合规测试）
  5. 验证（按 checklist.md 逐项核对）
  6. 文档与来源溯源更新
- 任何阶段不得省略来源标注与测试验证。

## 规则 2：开源工具最大化集成（强制）

能直接集成的开源工具全部集成进来，不好集成的用 Python 100% 复刻一个可用的。

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

### 2.5 参考来源
- GDSFactory 论文 (CLEO 2026): https://raw.githubusercontent.com/gdsfactory/gdsfactory-paper-cleo26/gh-pages/gdsfactory.pdf
- Awesome Photonics: https://github.com/joamatab/awesome_photonics
- Simphony 文档: https://simphonyphotonics.readthedocs.io/en/stable/
- Prefab: Python for photonics: https://docs.prefabphotonics.com/python-for-photonics/

## 后续规则
（其他规则将随项目推进追加）
