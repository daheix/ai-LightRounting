# Tasks

## 阶段一：光器件模型资料库（PDK Lite）

- [ ] Task 1: 搭建 Python 项目骨架与包结构
  - [ ] SubTask 1.1: 创建 `polaris/` 包目录及子模块（`pdk/`, `engine/`, `router/`, `trainer/`, `eval/`）
  - [ ] SubTask 1.2: 创建 `pyproject.toml`、依赖清单（numpy, scipy, networkx, torch, gymnasium, gdspy/klayout, matplotlib）
  - [ ] SubTask 1.3: 创建 `tests/` 目录与 pytest 配置

- [ ] Task 2: 定义器件数据结构与基类
  - [ ] SubTask 2.1: 实现 `Device` 数据类（device_id, platform, category, name, geometry, params, ports, constraints, source）
  - [ ] SubTask 2.2: 实现 `Port` 数据类（name, x, y, direction, waveguide_type, width）
  - [ ] SubTask 2.3: 实现器件变换工具（平移、旋转、包围盒计算）

- [ ] Task 3: 硅光 SOI 平台器件库（真实参数）
  - [ ] SubTask 3.1: 条形/肋形波导模型（宽 450-500nm，高 220nm，损耗区间）
  - [ ] SubTask 3.2: 弯曲波导（最小半径 5μm，单位损耗）
  - [ ] SubTask 3.3: 定向耦合器 DC（间隙 100-300nm，耦合长度）
  - [ ] SubTask 3.4: MMI 1x2/2x2（尺寸、插损）
  - [ ] SubTask 3.5: MZI、微环谐振器（半径、Q 值）
  - [ ] SubTask 3.6: 光栅耦合器、端面耦合器、Y 分支、Crossing、Taper
  - [ ] SubTask 3.7: 热光调制器、PN 结调制器、Ge 探测器
  - [ ] SubTask 3.8: 为每个器件标注文献来源字段

- [ ] Task 4: 氮化硅 SiN 平台器件库
  - [ ] SubTask 4.1: 条形波导（宽 700-1500nm，损耗 0.05-0.5 dB/cm）
  - [ ] SubTask 4.2: 弯曲（最小半径 50-100μm）、微环（Q>1e6）
  - [ ] SubTask 4.3: MMI、耦合器、Y 分支

- [ ] Task 5: InP 平台器件库
  - [ ] SubTask 5.1: 有源波导、DFB/DBR 激光器、SOA
  - [ ] SubTask 5.2: EAM 调制器、PIN 探测器、SSC、MMI

- [ ] Task 6: LNOI 薄膜铌酸锂平台器件库
  - [ ] SubTask 6.1: 干法刻蚀波导（宽 1-2μm，损耗 0.1-1 dB/cm）
  - [ ] SubTask 6.2: 电光调制器（VπL）、SSC、Y 分支、MMI

- [ ] Task 7: 器件清单注册表与检索 API
  - [ ] SubTask 7.1: 实现 `DeviceCatalog` 注册表，按平台/类别检索
  - [ ] SubTask 7.2: 实现序列化（JSON/YAML）与加载
  - [ ] SubTask 7.3: 实现参数溯源校验（source 字段非空校验）

## 阶段二：布局引擎（Floorplan）

- [ ] Task 8: 网表解析与图构建
  - [ ] SubTask 8.1: 实现网表解析器（JSON/YAML → 器件实例 + 连接边）
  - [ ] SubTask 8.2: 构建 networkx 图（节点=器件，边=连接，属性=端口/约束）

- [ ] Task 9: 布局环境（Gymnasium 接口）
  - [ ] SubTask 9.1: 实现网格化画布、放置动作空间
  - [ ] SubTask 9.2: 实现状态观测（占用栅格、端口位置、拥塞图）
  - [ ] SubTask 9.3: 实现奖励函数（面积、线长、拥塞、重叠惩罚）

- [ ] Task 10: GNN 状态编码器
  - [ ] SubTask 10.1: 实现器件-连接图 GNN 编码（PyTorch）
  - [ ] SubTask 10.2: 融合栅格空间特征

## 阶段三：布线引擎（Routing）

- [ ] Task 11: 波导约束布线器
  - [ ] SubTask 11.1: 实现网格布线（A*/Lee 算法 baseline）
  - [ ] SubTask 11.2: 实现弯曲半径约束（最小半径检查、S 弯生成）
  - [ ] SubTask 11.3: 实现波导间距约束、交叉最小化
  - [ ] SubTask 11.4: 实现等长路径约束（MZI 臂、差分对）

- [ ] Task 12: 布线环境（Gymnasium 接口）
  - [ ] SubTask 12.1: 实现逐连接布线动作空间
  - [ ] SubTask 12.2: 实现拥塞检测与热力图
  - [ ] SubTask 12.3: 实现奖励（损耗、长度、拥塞、DRC 违规）

## 阶段四：AI 训练框架（OptiLearn）

- [ ] Task 13: PPO 智能体实现
  - [ ] SubTask 13.1: 实现 actor-critic 网络（结合 GNN 编码）
  - [ ] SubTask 13.2: 实现 PPO 更新（clip、GAE、多步）
  - [ ] SubTask 13.3: 实现断点续训、指标记录

- [ ] Task 14: 训练数据集合成
  - [ ] SubTask 14.1: 从器件库随机生成网表（10/100/1000 器件级）
  - [ ] SubTask 14.2: 用经典布线器生成 baseline 解，标注奖励

- [ ] Task 15: 训练循环与迭代
  - [ ] SubTask 15.1: 实现训练主循环（采样→GNN→PPO→环境→奖励→更新）
  - [ ] SubTask 15.2: 实现早停、学习率调度、日志

## 阶段五：评测与可视化

- [ ] Task 16: 版图渲染与导出
  - [ ] SubTask 16.1: matplotlib 版图渲染（器件 + 波导）
  - [ ] SubTask 16.2: 导出 GDS 兼容中间格式（gdspy/klayout）
  - [ ] SubTask 16.3: 拥塞热力图、指标报告

- [ ] Task 17: 端到端流水线
  - [ ] SubTask 17.1: CLI 入口（网表 → 布局 → 布线 → 版图 → 报告）
  - [ ] SubTask 17.2: 端到端测试（小规模网表跑通）

## 阶段六：测试与验证

- [ ] Task 18: 单元测试与集成测试
  - [ ] SubTask 18.1: 器件库参数溯源校验测试（无假数据）
  - [ ] SubTask 18.2: 布局/布线约束合规测试
  - [ ] SubTask 18.3: 训练收敛性冒烟测试

# Task Dependencies
- Task 2 依赖 Task 1
- Task 3-6 依赖 Task 2
- Task 7 依赖 Task 3-6
- Task 8 依赖 Task 7
- Task 9 依赖 Task 8
- Task 10 依赖 Task 9
- Task 11 依赖 Task 9（共享画布/约束）
- Task 12 依赖 Task 11
- Task 13 依赖 Task 10、Task 12
- Task 14 依赖 Task 7、Task 11
- Task 15 依赖 Task 13、Task 14
- Task 16 依赖 Task 9、Task 12
- Task 17 依赖 Task 15、Task 16
- Task 18 依赖 Task 17
