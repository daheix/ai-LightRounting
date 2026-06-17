# PoLaRIS（光弈）光电子AI智能布局布线引擎 Spec

## Why
当前光子集成电路（PIC）的布局布线严重依赖人工经验，大规模芯片（>1000 器件）布线易拥堵、弯曲损耗难控制、相位匹配约束复杂，导致设计周期长、卡顿严重。需要一套基于真实光器件参数模型、采用 AI（GNN+PPO 强化学习）自主求解的 Python 自动布局布线工具，实现光波导约束下的高性能自动 PnR。

## What Changes
- 新建光器件模型资料库（PDK Lite）：覆盖硅光（SOI）、氮化硅（SiN）、InP、LNOI 四大主流平台的被动/主动器件真实参数模型
- 新建器件清单（device catalog）：含端口定义、几何约束、电光参数、版图模板
- 新建 AI 布局布线引擎核心：GNN 网格空间建模 + PPO 强化学习求解器
- 新建波导约束布线器：处理弯曲半径、等长相位、损耗、间距约束
- 新建数据集与训练框架：从器件模型合成训练样本
- 新建评测与可视化模块：版图渲染、布线拥堵热力图、指标统计
- 全部 Python 实现，禁止假数据，器件参数须来自公开文献/工艺手册

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
系统 SHALL 提供基于公开文献真实参数的光器件模型资料库，覆盖四大主流光子平台，禁止使用虚构参数。

#### 平台与器件清单（基于公开文献真实参数）

**平台 1：硅光 SOI（Silicon-on-Insulator，220nm SOI 工艺）**
- 参考工艺：IMEC 200mm/300mm iSiPP、AMF、CompoundTek；文献 Soref 2018、Chrostowski Hochberg 2015
- 条形波导 Strip Waveguide：宽 450-500nm，高 220nm，损耗 0.5-3 dB/cm
- 肋形波导 Rib Waveguide：宽 500-1000nm，slab 高 90nm，损耗 1-2 dB/cm
- 弯曲波导 Bend：最小半径 5μm（条形）/10μm（低损耗），单位损耗 0.01-0.1 dB/90°
- 定向耦合器 Directional Coupler：间隙 100-300nm，耦合长度 5-20μm
- 多模干涉耦合器 MMI 1x2/2x2：尺寸 ~3x10μm，插损 <0.5dB
- 马赫曾德干涉仪 MZI：臂长差 ΔL 控制相位，调制器用
- 微环谐振器 Ring Resonator：半径 5-20μm，Q 值 1e4-1e5
- 光栅耦合器 Grating Coupler（垂直）：插损 3-5dB，带宽 ~30nm
- 端面耦合器 Edge Coupler：插损 0.5-2dB
- Y 分支 Y-Branch：插损 <0.3dB
- 波导交叉 Crossing：插损 <0.1dB，串扰 <-40dB
- 锥形渐变器 Taper：宽度过渡，降低模式失配
- 热光调制器 Thermo-optic MZM：TiN 加热器，π相位功率 20-50mW
- PN 结相位调制器：VπL ~1-2 V·cm，带宽 >20GHz
- Ge-Si 光电探测器：响应度 0.8-1.0 A/W，暗电流 10-100nA

**平台 2：氮化硅 SiN（Silicon Nitride，低损耗平台）**
- 参考工艺：Ligentec、IMEC；文献 Subbaraman 2018
- 条形波导：宽 700-1500nm，高 150-300nm，损耗 0.05-0.5 dB/cm（超低损耗 0.001 dB/cm）
- 弯曲半径：最小 50-100μm（大截面低约束）
- 微环谐振器：Q 值 >1e6
- MMI、耦合器、Y 分支同硅光结构

**平台 3：InP（Indium Phosphide，有源集成平台）**
- 参考工艺：InP Foundry、SMART；文献 Smit 2014
- 有源波导：宽 1.5-2.5μm，高 0.2-0.5μm
- DFB 激光器：波长 1310/1550nm，输出功率 >10mW
- DBR 激光器、SOA 半导体光放大器：增益 >20dB
- 电吸收调制器 EAM：带宽 >40GHz
- PIN 光电探测器：响应度 0.8 A/W
- MMI、SSC 锥形模斑转换器

**平台 4：薄膜铌酸锂 LNOI（Lithium Niobate on Insulator）**
- 参考工艺：Hyper Light、硅基铌酸锂；文献 Wang 2018、Zhang 2021
- 干法刻蚀波导：宽 1-2μm，高 400-600nm，损耗 0.1-1 dB/cm
- 弯曲半径：最小 50-100μm
- 电光调制器：VπL ~2-5 V·cm，带宽 >100GHz（异构集成）
- 模斑转换器 SSC、Y 分支、MMI

#### Scenario: 器件参数可溯源
- **WHEN** 用户查询任意器件模型
- **THEN** 系统返回该器件的几何参数、电光参数、参考来源（文献/工艺手册名）
- **AND** 所有数值落在公开文献报告区间内，无虚构数据

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
  - `params`：电光参数字典（含单位与文献来源）
  - `layout_template`：GDS 友好的多边形/路径描述
  - `constraints`：最小间距、最小弯曲半径、禁布区

### Requirement: AI 布局引擎（Floorplan）
系统 SHALL 提供基于 GNN+PPO 的自动布局引擎，将器件网表放置到芯片画布。

#### Scenario: 网表输入
- **WHEN** 用户提供器件网表（器件列表 + 连接关系）
- **THEN** 引擎解析为图结构（节点=器件，边=连接）
- **AND** 提取器件尺寸、端口、约束

#### Scenario: 自动放置
- **WHEN** 触发布局
- **THEN** PPO 智能体在网格化画布上放置器件
- **AND** 满足：器件不重叠、端口朝向合理、关键器件优先放置、留出布线通道
- **AND** 奖励函数综合：面积利用率、布线长度估计、拥塞度、弯曲损耗惩罚

### Requirement: AI 布线引擎（Routing）
系统 SHALL 提供波导约束感知的自动布线引擎，支持强化学习与经典算法混合求解。

#### Scenario: 波导约束布线
- **WHEN** 布局完成，触发布线
- **THEN** 为每条连接生成光波导路径
- **AND** 满足约束：
  - 弯曲半径 ≥ 平台最小值（SOI 5μm，SiN 50μm）
  - 波导间距 ≥ 最小间距（SOI 1μm，SiN 2μm）
  - 等长路径（差分对、MZI 臂）长度差 < 阈值
  - 交叉最小化，必要时用专用 crossing 器件
  - 损耗预算不超限

#### Scenario: 拥塞处理
- **WHEN** 某区域布线密度超阈值
- **THEN** 触发重布线或局部布局调整
- **AND** 输出拥塞热力图供分析

### Requirement: 训练框架（OptiLearn / WaveGNN Studio）
系统 SHALL 提供 PPO 训练框架，从器件模型合成训练样本并迭代优化策略。

#### Scenario: 训练循环
- **WHEN** 启动训练
- **THEN** 框架执行：采样网表 → GNN 编码状态 → PPO 采样动作 → 环境执行 → 计算奖励 → 更新策略
- **AND** 支持断点续训、指标记录、早停

#### Scenario: 数据集合成
- **WHEN** 需要训练数据
- **THEN** 从器件库随机生成不同规模网表（10/100/1000 器件级）
- **AND** 标注最优/可行解参考（用经典布线器生成 baseline）

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
- **THEN** 附带 `source` 字段标注文献作者/年份或工艺手册名
- **AND** 若某参数无可靠文献，标注为 `estimated` 并给出估算依据

---

## MODIFIED Requirements
（首个 spec，无修改项）

## REMOVED Requirements
（首个 spec，无移除项）
