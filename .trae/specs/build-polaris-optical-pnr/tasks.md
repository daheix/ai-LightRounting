# Tasks

## 阶段一：光器件模型资料库（PDK Lite）

- [x] Task 1: 搭建 Python 项目骨架与包结构
  - [ ] SubTask 1.1: 创建 `polaris/` 包目录及子模块（`pdk/`, `engine/`, `router/`, `trainer/`, `eval/`）
  - [ ] SubTask 1.2: 创建 `pyproject.toml`、依赖清单（numpy, scipy, networkx, torch, gymnasium, gdspy/klayout, matplotlib）
  - [ ] SubTask 1.3: 创建 `tests/` 目录与 pytest 配置

- [x] Task 2: 定义器件数据结构与基类
  - [ ] SubTask 2.1: 实现 `Device` 数据类（device_id, platform, category, name, geometry, params, ports, constraints, source）
  - [ ] SubTask 2.2: 实现 `Port` 数据类（name, x, y, direction, waveguide_type, width）
  - [ ] SubTask 2.3: 实现 `Source` 数据类（authors, year, title, url）用于文献溯源
  - [ ] SubTask 2.4: 实现器件变换工具（平移、旋转、包围盒计算）

- [x] Task 3: 硅光 SOI 平台器件库（真实参数 + 来源网址）
  - [ ] SubTask 3.1: 条形/肋形波导（厚 220nm，宽 450-500nm，损耗 1-3 dB/cm）来源 latitudeda.com / iccsz.com
  - [ ] SubTask 3.2: 弯曲波导（最小半径 2-6μm）来源 cloud.tencent.com.cn/developer/article/2634252
  - [ ] SubTask 3.3: 定向耦合器 DC（间隙 100-300nm）来源 latitudeda.com
  - [ ] SubTask 3.4: MMI（插损 <0.5dB，imbalance <5%）来源 iccsz.com
  - [ ] SubTask 3.5: MZI、微环谐振器 来源 latitudeda.com
  - [ ] SubTask 3.6: 光栅耦合器（1D Si 1.9dB/27nm，2D Si 2.4dB/17nm，传统 3dB）来源 cloud.tencent.com/developer/article/2650050 + iccsz.com
  - [ ] SubTask 3.7: 端面耦合器（~2dB，优化 0.2-1dB）、Y 分支（<0.3dB）、Crossing（0.3dB/-30dB）来源 iccsz.com
  - [ ] SubTask 3.8: 热光移相器（Pπ ~20mW）、MZM（20GHz/5dB/VπL 2V·cm）、MRM（52pm/V, 74GHz）来源 iccsz.com + cloud.tencent.com/developer/article/2650050
  - [ ] SubTask 3.9: Ge 探测器（30GHz/0.7A/W/<100nA）来源 iccsz.com
  - [ ] SubTask 3.10: 三星平台器件（Si 1.2dB/cm, SiN 0.4dB/cm, Si rib 0.7dB/cm, DRF）来源 cloud.tencent.com/developer/article/2650050
  - [ ] SubTask 3.11: 为每个器件标注 source 字段（作者/年份 + URL）

- [x] Task 4: 氮化硅 SiN 平台器件库（真实参数 + 来源网址）
  - [ ] SubTask 4.1: IMEC LPCVD 波导（<0.1 dB/cm，最低 2 dB/m，405-2500nm）来源 imec-int.com
  - [ ] SubTask 4.2: LioniX TriPleX 双条带（<0.1 dB/cm，最低 0.1 dB/m，光纤耦合 <0.5dB/facet）来源 lionix-international.com
  - [ ] SubTask 4.3: Damascene SiN 8寸（0.157 dB/cm @1550nm）来源 doi.org/10.3390/app13063660
  - [ ] SubTask 4.4: 超低损耗数据（UCSB 1.2dB/m, EPFL <1dB/m, Twente 0.4/0.095dB/cm, Cornell Q 37M/67M）来源 patsnap.com
  - [ ] SubTask 4.5: 材料参数（Eg~5.1eV, n~2, 热光系数 0.2e-4/K）来源 c.m.163.com + cloud.tencent.com.cn

- [x] Task 5: InP 平台器件库（真实参数 + 来源网址）
  - [ ] SubTask 5.1: Fraunhofer HHI InP Foundry（EAM 45GHz, PD 0.8A/W, SOA 4dB/100μm, DFB/DBR >3mW）来源 doi.org/10.3390/app9081588
  - [ ] SubTask 5.2: UCSB SGDBR 激光器（1521-1565nm, SMSR >45dB, MZM）来源 doi.org/10.1109/JSTQE.2018.2866565
  - [ ] SubTask 5.3: SemiNex 高功率 DFB（200-250mW）/SOA（>1W）来源 aptechnologies.co.uk
  - [ ] SubTask 5.4: Coherent BH DFB（1311nm, 400mW@55°C, 线宽 <200kHz）来源 ep.cntronics.com
  - [ ] SubTask 5.5: IMOS DFB on InP membrane（250μm, 15GHz, 25Gbit/s）来源 photonics-benelux.org

- [x] Task 6: LNOI 薄膜铌酸锂平台器件库（真实参数 + 来源网址）
  - [ ] SubTask 6.1: 量产 LNOI 波导（<0.4 dB/cm）+ 调制器（>110GHz, Vπ<3V）来源 doi.org/10.37188/lam.2025.047
  - [ ] SubTask 6.2: 高约束 MZM（VπL 1.2 V·cm, >40GHz）来源 doi.org/10.1364/OL.481827
  - [ ] SubTask 6.3: 行波电极调制器（VπL 1.77 V·cm, 0.022 dB/cm, >100GHz）来源 mdpi.com/2304-6732/12/7/648
  - [ ] SubTask 6.4: 综述参数（VπL<2, 耦合 <0.5dB/facet, >100GHz）来源 doi.org/10.37188/CO.2021-0115
  - [ ] SubTask 6.5: TFLN 综述 + Nature 2018 来源 doi.org/10.1364/AOP.411024 + doi.org/10.1038/s41586-018-0551-y

- [x] Task 7: 器件清单注册表与检索 API
  - [ ] SubTask 7.1: 实现 `DeviceCatalog` 注册表，按平台/类别检索
  - [ ] SubTask 7.2: 实现序列化（JSON/YAML）与加载
  - [ ] SubTask 7.3: 实现参数溯源校验（source.url 字段非空校验）

## 阶段二：布局引擎（Floorplan）

- [x] Task 8: 网表解析与图构建
  - [ ] SubTask 8.1: 实现网表解析器（JSON/YAML → 器件实例 + 连接边）
  - [ ] SubTask 8.2: 构建 networkx 图（节点=器件，边=连接，属性=端口/约束）

- [x] Task 9: 布局环境（Gymnasium 接口）
  - [ ] SubTask 9.1: 实现网格化画布、放置动作空间
  - [ ] SubTask 9.2: 实现状态观测（占用栅格、端口位置、拥塞图）
  - [ ] SubTask 9.3: 实现奖励函数（面积、HPWL 线长、拥塞、重叠惩罚）参考 NeurIPS 2025 Basso et al.

- [x] Task 10: GNN 状态编码器
  - [ ] SubTask 10.1: 实现器件-连接图 GNN 编码（PyTorch，参考 R-GCN）
  - [ ] SubTask 10.2: 融合栅格空间特征

## 阶段三：布线引擎（Routing）

- [x] Task 11: 波导约束布线器
  - [ ] SubTask 11.1: 实现网格布线（A*/Lee 算法 baseline）
  - [ ] SubTask 11.2: 实现弯曲半径约束（SOI 2-6μm / SiN 50-100μm 检查、S 弯生成）
  - [ ] SubTask 11.3: 实现波导间距约束（SOI 1μm / SiN 2μm）、交叉最小化（crossing 0.3dB/-30dB）
  - [ ] SubTask 11.4: 实现等长路径约束（MZI 臂、差分对长度差 < 阈值）

- [x] Task 12: 布线环境（Gymnasium 接口）
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
  - [ ] SubTask 18.1: 器件库参数溯源校验测试（source.url 非空，无假数据）
  - [ ] SubTask 18.2: 布局/布线约束合规测试（弯曲半径、间距、等长）
  - [ ] SubTask 18.3: 训练收敛性冒烟测试（小规模网表）

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
