# PoLaRIS（光弈）光电子AI智能布局布线引擎 Spec

## Why
当前光子集成电路（PIC）的布局布线严重依赖人工经验，大规模芯片（>1000 器件）布线易拥堵、弯曲损耗难控制、相位匹配约束复杂，导致设计周期长、卡顿严重。需要一套基于真实光器件参数模型、采用 AI（GNN+PPO 强化学习）自主求解的 Python 自动布局布线工具，实现光波导约束下的高性能自动 PnR。

## What Changes
- 新建光器件模型资料库（PDK Lite）：覆盖硅光（SOI）、氮化硅（SiN）、InP、LNOI 四大主流平台的被动/主动器件真实参数模型，全部参数标注文献来源与网址
- 新建器件清单（device catalog）：含端口定义、几何约束、电光参数、版图模板
- 新建 AI 布局布线引擎核心：GNN 网格空间建模 + PPO 强化学习求解器（参考 NeurIPS 2022/2025 联合 PnR 神经流水线方法）
- 新建波导约束布线器：处理弯曲半径、等长相位、损耗、间距约束
- 新建数据集与训练框架：从器件模型合成训练样本
- 新建评测与可视化模块：版图渲染、布线拥堵热力图、指标统计
- 全部 Python 实现，禁止假数据，器件参数须来自公开文献/工艺手册，附网址

## Impact
- Affected specs: 无（首个 spec）
- Affected code: 全新仓库 `ai-LightRounting`，新增 `pdk/`、`engine/`、`router/`、`trainer/`、`eval/`、`tests/` 等模块

## 命名约定（来自用户方案）
- 正式软件产品：**PoLaRIS（光弈）**
- 轻量化开源插件：**PhIRoute（波策）**
- 内部 AI 训练工程代号：**OptiLearn / WaveGNN Studio**

---

## ADDED Requirements

### Requirement: 光器件模型资料库（PDK Lite）
系统 SHALL 提供基于公开文献真实参数的光器件模型资料库，覆盖四大主流光子平台，禁止使用虚构参数。每个器件参数须附带 `source` 字段（文献作者/年份 + 网址）。

#### 平台与器件清单（基于公开文献真实参数 + 来源网址）

---

**平台 1：硅光 SOI（Silicon-on-Insulator，220nm/300nm SOI 工艺）**

| 器件 | 参数 | 来源 |
|------|------|------|
| 条形波导 Strip WG | 厚 220nm，宽 450-500nm（单模），损耗 1-3 dB/cm | AIM Photonics 教程 https://www.latitudeda.com/document/716 ；硅光工艺平台比较 http://www.iccsz.com/site/cn/News/2019/05/18/20190518033317178663.htm |
| 肋形波导 Rib WG | slab 高 90nm，浅刻蚀，损耗更低（长 routing 用） | 同上 iccsz.com |
| 弯曲波导 Bend | 最小半径 2-6μm（高折射率差平台），损耗 0.01-0.1 dB/90° | 台积电 ISSCC 2026 https://cloud.tencent.com.cn/developer/article/2634252 ；AIM 教程 latitudeda.com |
| 定向耦合器 DC | 间隙 100-300nm，耦合长度 5-20μm | AIM Photonics 教程 https://www.latitudeda.com/document/716 |
| MMI 1x2/2x2 | 插损 <0.5dB，imbalance <5% | 硅光工艺平台比较 http://www.iccsz.com/site/cn/News/2019/05/18/20190518033317178663.htm |
| MZI | 双臂干涉，臂长差控相位 | AIM Photonics 教程 https://www.latitudeda.com/document/716 |
| 微环谐振器 Ring | 半径 5-20μm | AIM Photonics 教程 https://www.latitudeda.com/document/716 |
| 光栅耦合器 GC（1D Si） | 峰值耦合损耗 1.9dB，1-dB 带宽 27nm | 三星 300mm 硅光平台 OFC 2026 https://cloud.tencent.com/developer/article/2650050 |
| 光栅耦合器 GC（2D Si） | 耦合损耗 2.4dB，1-dB 带宽 17nm，TE/TM 双模 | 同上 |
| 光栅耦合器 GC（传统） | 损耗 ~3dB | 硅光工艺平台比较 http://www.iccsz.com/site/cn/News/2019/05/18/20190518033317178663.htm |
| 端面耦合器 Edge Coupler | 耦合损耗 ~2dB（传统），优化后 0.2-1dB | 硅光工艺平台比较 http://www.iccsz.com/site/cn/News/2019/05/18/20190518033317178663.htm ；耦合器件选型对比 https://m.toutiao.com/group/7646719858855428648/ |
| Y 分支 Y-Branch | 插损 <0.3dB | AIM Photonics 教程 https://www.latitudeda.com/document/716 |
| 波导交叉 Crossing | 插损 ~0.3dB，串扰 ~-30dB | 硅光工艺平台比较 http://www.iccsz.com/site/cn/News/2019/05/18/20190518033317178663.htm |
| 热光移相器 | Pπ ~20mW | 硅光工艺平台比较 http://www.iccsz.com/site/cn/News/2019/05/18/20190518033317178663.htm |
| MZ 调制器 MZM | 带宽 ~20GHz，插损 ~5dB，VπL ~2V·cm | 硅光工艺平台比较 http://www.iccsz.com/site/cn/News/2019/05/18/20190518033317178663.htm |
| 微环调制器 MRM | 垂直 PN 结效率 52 pm/V，横向 PN 结带宽 74GHz(3dB)/58GHz(6dB) | 三星 300mm 硅光平台 OFC 2026 https://cloud.tencent.com/developer/article/2650050 |
| Ge 光电探测器 | 带宽 ~30GHz，响应率 ~0.7A/W，暗电流 <100nA | 硅光工艺平台比较 http://www.iccsz.com/site/cn/News/2019/05/18/20190518033317178663.htm |
| Si 单模条形波导（三星） | 损耗 1.2 dB/cm | 三星 300mm 硅光平台 https://cloud.tencent.com/developer/article/2650050 |
| SiN 单模条形波导（三星） | 损耗 0.4 dB/cm | 同上 |
| Si 单模肋形波导（三星） | 损耗 0.7 dB/cm | 同上 |
| Si/SiN 模式转换 | 转换损耗 <0.1 dB | 同上 |
| 双环滤波器 DRF | drop 插损 <1.0dB，1-dB 带宽 105GHz | 同上 |
| Si 波导热光系数 | 1.8×10⁻⁴ /K | 台积电 ISSCC 2026 https://cloud.tencent.com.cn/developer/article/2634252 |
| Si 波导损耗（台积电） | <0.6 dB/cm | 同上 |
| NOEIC 平台 | 8英寸 200mm CMOS，最小 90nm 波导线宽，三层波导刻蚀 | NOEIC https://www.noeic.com/service01.html |

---

**平台 2：氮化硅 SiN（Silicon Nitride，低损耗平台）**

| 器件 | 参数 | 来源 |
|------|------|------|
| SiN 条形波导（LPCVD） | 损耗 <0.1 dB/cm，最低 2 dB/m（0.2 dB/cm），波长 405-2500nm | IMEC SiN 平台 https://www.imec-int.com/en/what-we-offer/development/silicon-nitride |
| SiN 条形波导（PECVD） | 损耗 <2 dB/cm | 同上 |
| TriPleX 双条带波导 | 损耗 <0.1 dB/cm，最低 0.1 dB/m，波长 405-2350nm，光纤耦合 <0.5dB/facet | LioniX TriPleX https://www.lionix-international.com/photonics/pic-technology/triplex-waveguide-technology/ |
| SiN 波导（Damascene 8寸） | 400nm 厚，0.157 dB/cm @1550nm，0.06 dB/cm @1580nm | Li et al., Appl. Sci. 2023, 13, 3660 https://doi.org/10.3390/app13063660 |
| SiN 超低损耗（UCSB） | 1.2 dB/m @1590nm | PatSnap Eureka 综述 https://www.patsnap.com/resources/blog/rd-blog/si₃n₄-waveguide-loss-reduction-patsnap-eureka/ |
| SiN 超低损耗（EPFL Damascene） | <1 dB/m，Q>10⁷（晶圆级） | 同上 |
| SiN 沟槽填充（Twente） | 0.4 dB/cm @1550nm，厚核 900nm | 同上 |
| SiN 双条带环（Twente） | 0.095 dB/cm | 同上 |
| SiN 可见光波导（Myongji） | 0.1 dB/cm | 同上 |
| SiN 微环 Q 值 | 37M（2.5μm 宽）/ 67M（10μm 宽），Cornell | 同上 |
| SiN 材料参数 | Eg~5.1eV，n~2 @1550nm，损耗 0.045±0.04 dB/m，热膨胀 2.35×10⁻⁶/°C | 中国物理学会期刊网 https://c.m.163.com/news/a/E9107H030516DOTJ.html |
| SiN 热光系数 | 0.2×10⁻⁴ /K（比 Si 低一个数量级） | 台积电 ISSCC 2026 https://cloud.tencent.com.cn/developer/article/2634252 |
| SiN 波导损耗（台积电） | <0.23 dB/cm | 同上 |
| SiN 光栅耦合器（1D） | 峰值耦合损耗 2.1dB，1-dB 带宽 57nm | 三星 300mm 硅光平台 https://cloud.tencent.com/developer/article/2650050 |

---

**平台 3：InP（Indium Phosphide，有源集成平台）**

| 器件 | 参数 | 来源 |
|------|------|------|
| InP 有源波导 | 宽 1.5-2.5μm，SSC 模场 10×7μm | Soares et al., Appl. Sci. 2019, 9, 1588 https://doi.org/10.3390/app9081588 |
| EAM 电吸收调制器 | 带宽 ~45GHz | 同上 |
| InP 光电探测器 | 内部响应率 >0.8 A/W | 同上 |
| SOA 半导体光放大器 | 增益 ~4dB/100μm | 同上 |
| DFB/DBR 激光器 | 输出功率 >3mW | 同上 |
| SGDBR 激光器 | 调谐 1521-1565nm，SMSR >45dB | Zhao et al., IEEE JSTQE 2018, 24, 6101806 https://doi.org/10.1109/JSTQE.2018.2866565 |
| InP MZM | 1mm 长，集成于 PIC | 同上 |
| O-band DFB 激光器（SemiNex） | 200-250mW CW @25°C | AP Technologies https://www.aptechnologies.co.uk/news |
| 超高功率 SOA | >1W 输出，PCE ~25%@25°C | 同上 |
| InP BH DFB 激光器（Coherent） | 1311nm，400mW@55°C，线宽 <200kHz，RIN <-145 dB/Hz | Coherent 产品报道 http://ep.cntronics.com/guide/4364/14539 |
| IMOS DFB 激光器（TU Eindhoven） | 250μm 长，600μW 光纤功率，带宽 15GHz，25Gbit/s | Zozulia et al., Photonics Benelux 2023 https://photonics-benelux.org/wp-content/uploads/pb-files/proceedings/2023/Posters_even_numbers/Zozulia.pdf |

---

**平台 4：薄膜铌酸锂 LNOI（Lithium Niobate on Insulator）**

| 器件 | 参数 | 来源 |
|------|------|------|
| LNOI 波导 | 损耗 <0.4 dB/cm | Liu et al., Light: Advanced Manufacturing 2025, 6, 47 https://doi.org/10.37188/lam.2025.047 |
| LNOI 电光调制器 | 带宽 >110GHz，Vπ <3V，良率 50%，4英寸晶圆 | 同上 |
| LNOI MZM（高约束） | VπL 1.2 V·cm，过剩损耗 ~2.4dB，带宽 >40GHz | Chen et al., Optics Letters 2023, 48(7):1602-1605 https://doi.org/10.1364/OL.481827 |
| LNOI 行波电极调制器 | VπL 1.77 V·cm，光损耗 0.022 dB/cm，带宽 >100GHz | MDPI Photonics 2023, 12(7):648 https://www.mdpi.com/2304-6732/12/7/648 |
| LNOI 调制器综述 | VπL<2 V·cm，双锥形耦合 <0.5dB/facet，带宽 >100GHz | 刘海锋等，中国光学 2022, 15(1):1-13 https://doi.org/10.37188/CO.2021-0115 |
| LNOI 集成光子学综述 | LN 透明窗口 0.4-5μm，高电光系数 | Zhu et al., Adv. Opt. Photonics 2021, 13:242-352 https://doi.org/10.1364/AOP.411024 |
| LNOI CMOS 兼容调制器 | Nature 2018 首篇 CMOS 兼容电压 LN 调制器 | Wang et al., Nature 2018, 562:101-104 https://doi.org/10.1038/s41586-018-0551-y |

---

#### Scenario: 器件参数可溯源
- **WHEN** 用户查询任意器件模型
- **THEN** 系统返回该器件的几何参数、电光参数、参考来源（文献作者/年份 + 网址）
- **AND** 所有数值落在公开文献报告区间内，无虚构数据
- **AND** 若某参数无可靠文献，标注为 `estimated` 并给出估算依据

#### Scenario: 器件端口定义
- **WHEN** 加载器件到布局引擎
- **THEN** 每个器件提供端口列表（名称、坐标、方向、波导类型、模式宽度）
- **AND** 端口坐标相对器件原点定义，支持旋转/平移变换

### Requirement: 器件清单数据结构
系统 SHALL 提供统一的器件清单数据结构，支持序列化与程序化检索。

#### Scenario: 器件实例化
- **WHEN** 引擎请求某类器件
- **THEN** 返回包含以下字段的器件对象：
  - `device_id`：唯一标识
  - `platform`：SOI/SiN/InP/LNOI
  - `category`：passive/active/source/detector
  - `name`：器件类型名（如 ring_resonator）
  - `geometry`：包围盒、端口坐标、关键尺寸
  - `params`：电光参数字典（含单位与文献来源 + 网址）
  - `layout_template`：GDS 友好的多边形/路径描述
  - `constraints`：最小间距、最小弯曲半径、禁布区
  - `source`：文献引用（作者, 年份, 标题, URL）

### Requirement: AI 布局引擎（Floorplan）
系统 SHALL 提供基于 GNN+PPO 的自动布局引擎，将器件网表放置到芯片画布。方法参考 NeurIPS 2022 联合 PnR 神经流水线（Cheng et al., SJTU+华为）与 NeurIPS 2025 模拟 IC 布局感知 floorplanning（Basso et al., Infineon）。

#### Scenario: 网表输入
- **WHEN** 用户提供器件网表（器件列表 + 连接关系）
- **THEN** 引擎解析为图结构（节点=器件，边=连接）
- **AND** 提取器件尺寸、端口、约束

#### Scenario: 自动放置
- **WHEN** 触发布局
- **THEN** PPO 智能体在网格化画布上放置器件
- **AND** 满足：器件不重叠、端口朝向合理、关键器件优先放置、留出布线通道
- **AND** 奖励函数综合：面积利用率、布线长度估计（HPWL）、拥塞度、弯曲损耗惩罚
- **AND** 参考：RL+R-GCN 在模拟 IC 上实现死区减少 13.8%、线长减少 40.6%、布线成功率提升 73.4%（Basso et al., NeurIPS 2025 MLForSystems https://mlforsystems.org/assets/papers/neurips2025/paper42.pdf）

### Requirement: AI 布线引擎（Routing）
系统 SHALL 提供波导约束感知的自动布线引擎，支持强化学习与经典算法混合求解。参考 Cheng et al. NeurIPS 2022 一次性生成式布线模型（https://openreview.net/pdf?id=uNYqDfPEDD8）。

#### Scenario: 波导约束布线
- **WHEN** 布局完成，触发布线
- **THEN** 为每条连接生成光波导路径
- **AND** 满足约束：
  - 弯曲半径 ≥ 平台最小值（SOI 2-6μm，SiN 50-100μm）
  - 波导间距 ≥ 最小间距（SOI 1μm，SiN 2μm）
  - 等长路径（差分对、MZI 臂）长度差 < 阈值
  - 交叉最小化，必要时用专用 crossing 器件（插损 0.3dB，串扰 -30dB）
  - 损耗预算不超限

#### Scenario: 拥塞处理
- **WHEN** 某区域布线密度超阈值
- **THEN** 触发重布线或局部布局调整
- **AND** 输出拥塞热力图供分析

### Requirement: 训练框架（OptiLearn / WaveGNN Studio）
系统 SHALL 提供 PPO 训练框架，从器件模型合成训练样本并迭代优化策略。PPO 选型依据：训练稳定性与采样效率平衡，对超参数不敏感（参考 Google AlphaChip、Cadence Cerebrus 等工业实践，综述见 https://www.chipfoundryservices.com/topic/ml-for-place-and-route ）。

#### Scenario: 训练循环
- **WHEN** 启动训练
- **THEN** 框架执行：采样网表 → GNN 编码状态 → PPO 采样动作 → 环境执行 → 计算奖励 → 更新策略
- **AND** 支持断点续训、指标记录、早停

#### Scenario: 数据集合成
- **WHEN** 需要训练数据
- **THEN** 从器件库随机生成不同规模网表（10/100/1000 器件级）
- **AND** 标注最优/可行解参考（用经典布线器 A* 生成 baseline）

### Requirement: 评测与可视化
系统 SHALL 提供版图渲染与指标统计，支持人机协同调试。

#### Scenario: 版图输出
- **WHEN** 布局布线完成
- **THEN** 渲染芯片版图（器件 + 波导）
- **AND** 导出 GDS 兼容格式（或可转 GDS 的中间格式）
- **AND** 输出指标报告：总面积、总线长、总损耗、拥塞分布、DRC 违规数

### Requirement: 禁止假数据
系统 SHALL 确保所有器件参数、文献来源、工艺数据真实可查，禁止虚构。

#### Scenario: 参数溯源
- **WHEN** 任意器件参数被加载
- **THEN** 附带 `source` 字段标注文献作者/年份 + 网址
- **AND** 若某参数无可靠文献，标注为 `estimated` 并给出估算依据
- **AND** spec.md 中已列出全部来源网址，实现阶段须逐项核对

---

## 参考文献汇总（实现阶段须逐项核对网址可达性）

### 硅光 SOI 平台
1. AIM Photonics 无源硅基光电子芯片元件教程 — https://www.latitudeda.com/document/716
2. 光学小豆芽：硅光工艺平台比较（IMEC/AMF/AIM/Leti/IHP 等 PDK 参数） — http://www.iccsz.com/site/cn/News/2019/05/18/20190518033317178663.htm
3. 台积电 ISSCC 2026 硅光子学平台解析 — https://cloud.tencent.com.cn/developer/article/2634252
4. 三星 300mm 硅光平台 OFC 2026 — https://cloud.tencent.com/developer/article/2650050
5. NOEIC 硅光流片服务 PDK — https://www.noeic.com/service01.html
6. 端面耦合与光栅耦合选型对比 — https://m.toutiao.com/group/7646719858855428648/

### 氮化硅 SiN 平台
7. IMEC Silicon Nitride Photonics — https://www.imec-int.com/en/what-we-offer/development/silicon-nitride
8. LioniX TriPleX SiN 波导技术 — https://www.lionix-international.com/photonics/pic-technology/triplex-waveguide-technology/
9. Li et al., Appl. Sci. 2023, 13, 3660（Damascene SiN 8寸） — https://doi.org/10.3390/app13063660
10. PatSnap Eureka: SiN 波导损耗综述（UCSB/EPFL/Twente/Cornell） — https://www.patsnap.com/resources/blog/rd-blog/si₃n₄-waveguide-loss-reduction-patsnap-eureka/
11. 中国物理学会期刊网：Si3N4 波导材料 — https://c.m.163.com/news/a/E9107H030516DOTJ.html

### InP 平台
12. Soares et al., Appl. Sci. 2019, 9, 1588（InP Foundry PICs） — https://doi.org/10.3390/app9081588
13. Zhao et al., IEEE JSTQE 2018, 24, 6101806（InP PIC 自由空间光通信） — https://doi.org/10.1109/JSTQE.2018.2866565
14. AP Technologies: 超高功率 InP 器件 — https://www.aptechnologies.co.uk/news
15. Coherent 400mW InP BH DFB 激光器 — http://ep.cntronics.com/guide/4364/14539
16. Zozulia et al., Photonics Benelux 2023（IMOS DFB on InP membrane） — https://photonics-benelux.org/wp-content/uploads/pb-files/proceedings/2023/Posters_even_numbers/Zozulia.pdf

### LNOI 薄膜铌酸锂平台
17. Liu et al., Light: Advanced Manufacturing 2025, 6, 47（量产 LNOI 调制器） — https://doi.org/10.37188/lam.2025.047
18. Chen et al., Optics Letters 2023, 48(7):1602-1605（高约束 LNOI MZM） — https://doi.org/10.1364/OL.481827
19. MDPI Photonics 2023, 12(7):648（U-T 双层行波电极 LNOI） — https://www.mdpi.com/2304-6732/12/7/648
20. 刘海锋等，中国光学 2022, 15(1):1-13（LNOI 调制器综述） — https://doi.org/10.37188/CO.2021-0115
21. Zhu et al., Adv. Opt. Photonics 2021, 13:242-352（TFLN 集成光子学综述） — https://doi.org/10.1364/AOP.411024
22. Wang et al., Nature 2018, 562:101-104（CMOS 兼容 LN 调制器） — https://doi.org/10.1038/s41586-018-0551-y

### AI 布局布线算法
23. Cheng et al., NeurIPS 2022（策略梯度布局 + 生成式布线，SJTU+华为） — https://openreview.net/pdf?id=uNYqDfPEDD8 ；代码 https://github.com/Thinklab-SJTU/EDA-AI
24. Basso et al., NeurIPS 2025 MLForSystems（RL+R-GCN 模拟 IC 布局感知 floorplanning，Infineon） — https://mlforsystems.org/assets/papers/neurips2025/paper42.pdf
25. ChipFoundryServices: ML for Place and Route 综述（PPO/GNN/CNN，AlphaChip） — https://www.chipfoundryservices.com/topic/ml-for-place-and-route
26. ChipFoundryServices: RL for Chip Optimization — https://www.chipfoundryservices.com/topic/reinforcement-learning-chip-optimization
27. CSDN：深度强化学习在芯片物理设计布局中的应用（PPO 选型） — https://wenku.csdn.net/column/n6ju7sp01vq
28. AIBR：Multi-Agent RL for PIC Inverse Design — https://aibr.jp/archives/112508

---

## MODIFIED Requirements
（首个 spec，无修改项）

## REMOVED Requirements
（首个 spec，无移除项）
