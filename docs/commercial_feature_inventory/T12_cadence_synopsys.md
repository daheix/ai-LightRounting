# T12 商业 EDA 标杆功能清单：Cadence Innovus + Synopsys ICC2

> **学术诚信声明**：本文档所有功能点均来自公开来源（官网、数据手册、技术博客、白皮书、学术论文）。每个功能点均标注来源 URL。未公开信息明确标注"未公开"。本文档不含任何臆造内容。

---

## 文档元信息

| 项目 | 内容 |
|---|---|
| 工具名 | Cadence Innovus Implementation System + Synopsys IC Compiler II (ICC2) |
| 厂商 | Cadence Design Systems / Synopsys |
| 官网 URL | Cadence: https://www.cadence.com/en_US/home/tools/digital-design-and-signoff/soc-implementation-and-floorplanning/innovus-implementation-system.html <br> Synopsys: https://www.synopsys.com/implementation-and-signoff/physical-implementation/ic-compiler.html |
| 调研日期 | 2026-06-25 |
| 文档版本 | v1.0 |
| 调研员 | EDA + AI 标杆调研员 |

---

## 第一部分：Cadence Innovus Implementation System

### 工具概述

Cadence Innovus Implementation System 是 Cadence 公司的业界领先数字实现（place-and-route）系统，覆盖从综合后网表到 GDSII 的完整物理设计流程，包括布局规划、布局、时钟树综合、布线、优化与签核收敛。最新版本集成 GigaPlace、GigaOpt、CCOpt、PRO 布线器与 Innovus+ AI Assistant 等核心引擎，并已通过 TSMC N3/N2/A16/A14 工艺认证。

来源：
- https://community.cadence.com/cadence_blogs_8/b/di/posts/unlocking-ppa-with-innovus-what-s-new-and-how-to-unleash-it
- https://www.fangzhenxiu.com/post/15154106/

---

### 功能点清单

#### 1. GigaPlace 全局布局引擎

| 编号 | 子功能 | 描述 | 来源 URL |
|---|---|---|---|
| INV-1.1 | Startpoint TNS Method | 在端点（endpoint）代价之外，将关键 launch flop 的 startpoint slack 加入代价函数（Total Cost = ∑endpoint_WNS + ∑startpoint_WNS），重平衡 launch-capture 对，加速收敛 | https://community.cadence.com/cadence_blogs_8/b/di/posts/unlocking-ppa-with-innovus-what-s-new-and-how-to-unleash-it |
| INV-1.2 | Unbalanced Path-Based SKP | 在每个 flop 两侧评估关键性，沿整条关键路径施加比例化时序权重，提升 WNS/TNS | https://community.cadence.com/cadence_blogs_8/b/di/posts/unlocking-ppa-with-innovus-what-s-new-and-how-to-unleash-it |
| INV-1.3 | Advanced Pipeline Placement | 自动收集纯 F/F 流水线，平衡级间距与点对点线长，消除歪斜流水线结构 | https://community.cadence.com/cadence_blogs_8/b/di/posts/unlocking-ppa-with-innovus-what-s-new-and-how-to-unleash-it |
| INV-1.4 | Integrated Congestion-Driven Placement (ICDP) | 替代旧的 padding 方案，将长线源/宿移出热点，更有效清除宏单元/阻塞区上的穿越流量 | https://community.cadence.com/cadence_blogs_8/b/di/posts/unlocking-ppa-with-innovus-what-s-new-and-how-to-unleash-it |
| INV-1.5 | Switching Power Placement (SPP) | 将 activity-weighted wirelength 直接集成到布局代价函数，降低高翻转 net 线长，降低整体翻转功耗 | https://community.cadence.com/cadence_blogs_8/b/di/posts/unlocking-ppa-with-innovus-what-s-new-and-how-to-unleash-it |

#### 2. GigaOpt 优化引擎

| 编号 | 子功能 | 描述 | 来源 URL |
|---|---|---|---|
| INV-2.1 | Mega Options 优化等级控制 | 通过 setOptMode / set_db 显式设置 timing/power/area effort（standard/high、none/low/high/ultrahigh、standard/high） | https://community.cadence.com/cadence_blogs_8/b/di/posts/unlocking-ppa-with-innovus-what-s-new-and-how-to-unleash-it |
| INV-2.2 | New Path Compaction (CPR) | 局部布局精化，对高移动概率实例赋权重，最小化侧路径影响；改进关键路径探索与工作集创建 | https://community.cadence.com/cadence_blogs_8/b/di/posts/unlocking-ppa-with-innovus-what-s-new-and-how-to-unleash-it |
| INV-2.3 | Pervasive Global Skew | 全流程贯穿全局偏斜，最大化 useful skew，降低前期功耗，为功耗回收留余量 | https://community.cadence.com/cadence_blogs_8/b/di/posts/unlocking-ppa-with-innovus-what-s-new-and-how-to-unleash-it |
| INV-2.4 | New Hold Optimizer | 改进 hold TNS、面积与功耗，自动提升 QoR | https://community.cadence.com/cadence_blogs_8/b/di/posts/unlocking-ppa-with-innovus-what-s-new-and-how-to-unleash-it |
| INV-2.5 | XOR-tree Gating / Data Gating | 数据稳定时禁用时钟（XOR-tree gating）；将 D 引脚与 ICG enable 相与（Data-gating），针对高活动性 flop | https://community.cadence.com/cadence_blogs_8/b/di/posts/unlocking-ppa-with-innovus-what-s-new-and-how-to-unleash-it |
| INV-2.6 | 时序驱动逻辑重映射/缓冲器插入 | GigaOpt 引擎在布局后进行时序驱动逻辑重映射、缓冲器插入、驱动能力优化 | https://wenku.csdn.net/answer/7pcjs53ntv |

#### 3. PRO 全局-详细布线

| 编号 | 子功能 | 描述 | 来源 URL |
|---|---|---|---|
| INV-3.1 | Hard Wires 详细布线 | 从 soft wires + eDR 全局布线升级为 hard wires（最终详细布线），让优化器在近最终寄生参数下尝试更大胆的变更 | https://community.cadence.com/cadence_blogs_8/b/di/posts/unlocking-ppa-with-innovus-what-s-new-and-how-to-unleash-it |
| INV-3.2 | 四阶段流程 (Init/Soft/Hard/Final) | Init 回收低效 buffer 链与差层分配；Soft 用 eDR 全局布线 + SI 时序；Hard 切换到详细布线；Final 收敛 | https://community.cadence.com/cadence_blogs_8/b/di/posts/unlocking-ppa-with-innovus-what-s-new-and-how-to-unleash-it |

#### 4. ML DRC 闭合 / AI 驱动

| 编号 | 子功能 | 描述 | 来源 URL |
|---|---|---|---|
| INV-4.1 | Innovus+ AI Assistant | 自然语言调试接口，工程师可用英文描述任务（如"show timing violations in the CPU core"），返回验证过的脚本或修正；可节省 40% 脚本编写时间 | https://www.ust.com/en/insights/ai-in-cadence-innovus-workflows-10x-faster-physical-design-in-2025 |
| INV-4.2 | 自动化 DRC 违例修复辅助 | AI 驱动的 DRC 违例识别与修复辅助，TSMC 已在 N2 节点验证 | https://www.eetimes.com/ai-and-chiplets-prominent-at-tsmc-oip-2025/ |
| INV-4.3 | AI 驱动 PPA 收敛 | Cerebrus Intelligent Chip Explorer + JedAI 平台将 ML/LLM 引入迭代优化循环，实现 AI 引导的 PPA 收敛 | https://windowsforum.com/threads/cadence-and-tsmc-expand-ai-driven-flows-for-n2p-n3-3d-ic-designs.382889/ |
| INV-4.4 | Voltus InsightAI 生成式 AI | EDA 业界首个用于早期 EM-IR 违例检测与修复的生成式 AI；构建神经网络驱动的电源网格模型，签核前可修复 95% 违例，EM-IR 闭合效率提升 2× | https://www.ust.com/en/insights/ai-in-cadence-innovus-workflows-10x-faster-physical-design-in-2025 |

#### 5. 先进节点支持（3nm / 2nm 及以下）

| 编号 | 子功能 | 描述 | 来源 URL |
|---|---|---|---|
| INV-5.1 | TSMC N3 工艺认证 | Innovus Implementation System 已通过 TSMC N3 工艺认证，Artisan 基础 IP 已用于 N3 量产设计 | https://www.fangzhenxiu.com/post/15154106/ |
| INV-5.2 | TSMC N2 / N2P 工艺认证 | 全流程（Innovus + Tempus + Quantus + Pegasus）已通过 TSMC N2 / N2P 工艺认证 | https://www.fangzhenxiu.com/post/15154106/ |
| INV-5.3 | TSMC A16 工艺认证 | 已通过 TSMC A16（背面供电节点）工艺认证 | https://www.fangzhenxiu.com/post/15154106/ |
| INV-5.4 | TSMC A14 PDK 合作 | 与 TSMC 持续合作 A14 PDK，加速 AI/HPC 应用流片质量收敛 | https://www.fangzhenxiu.com/post/15154106/ |
| INV-5.5 | 3nm 及以下 AI 加速 | AI for 3nm design 工作流基准引用 10× 加速，将数周工作压缩为数小时 | https://www.ust.com/en/insights/ai-in-cadence-innovus-workflows-10x-faster-physical-design-in-2025 |

#### 6. 分布式与多线程

| 编号 | 子功能 | 描述 | 来源 URL |
|---|---|---|---|
| INV-6.1 | 分布式多线程架构 | Innovus 支持分布式与多线程计算，GigaOpt 可通过 -numThreads / GIGAOPT_NUM_THREADS 控制线程数 | https://wenku.csdn.net/answer/7pcjs53ntv |
| INV-6.2 | 云端可扩展 | 与 Microsoft Azure 等云平台协作，支持 Pegasus on CloudBurst 进行 giga-scale 物理验证 | https://windowsforum.com/threads/cadence-and-tsmc-expand-ai-driven-flows-for-n2p-n3-3d-ic-designs.382889/ |

#### 7. 时序优化

| 编号 | 子功能 | 描述 | 来源 URL |
|---|---|---|---|
| INV-7.1 | CCOpt 时钟树综合 | CCOpt（Cadence Clock Optimization）引擎，与 GigaPlace/GigaOpt 协同进行并发时钟与数据优化 | https://community.cadence.com/cadence_blogs_8/b/di/posts/unlocking-ppa-with-innovus-what-s-new-and-how-to-unleash-it |
| INV-7.2 | Tempus 时序签核集成 | 与 Tempus Timing Signoff 紧密集成，提供签核级时序精度 | https://www.fangzhenxiu.com/post/15154106/ |
| INV-7.3 | SI-based 时序 | PRO Soft 阶段使用基于 SI 的时序进行大尺度优化 | https://community.cadence.com/cadence_blogs_8/b/di/posts/unlocking-ppa-with-innovus-what-s-new-and-how-to-unleash-it |

#### 8. 功耗优化

| 编号 | 子功能 | 描述 | 来源 URL |
|---|---|---|---|
| INV-8.1 | Switching Power Placement | 见 INV-1.5 | https://community.cadence.com/cadence_blogs_8/b/di/posts/unlocking-ppa-with-innovus-what-s-new-and-how-to-unleash-it |
| INV-8.2 | XOR-tree / Data Gating | 见 INV-2.5 | https://community.cadence.com/cadence_blogs_8/b/di/posts/unlocking-ppa-with-innovus-what-s-new-and-how-to-unleash-it |
| INV-8.3 | Power Reclaim via Global Skew | 通过 pervasive global skew 为功耗回收留出余量 | https://community.cadence.com/cadence_blogs_8/b/di/posts/unlocking-ppa-with-innovus-what-s-new-and-how-to-unleash-it |

#### 9. IR 分析与电源完整性

| 编号 | 子功能 | 描述 | 来源 URL |
|---|---|---|---|
| INV-9.1 | Voltus IC Power Integrity Solution | Voltus 提供电压降与电迁移分析；Innovus PI 在布局/布线阶段插入 Voltus 分析，及早发现 IR/EM 问题 | https://blog.csdn.net/nuoweishizi/article/details/113474776 |
| INV-9.2 | 早期 IR 修复 | 通过 cell spreading / cell sizing / clock skewing / PG insertion/removal / signal EM fix 修复 IR/EM 违例，可将最终电压降违例减少上百倍 | https://blog.csdn.net/nuoweishizi/article/details/113474776 |
| INV-9.3 | Voltus XM 层级建模 | Voltus XM (extreme modeling) 对重复 IP 块建模，提升签核效率，减少资源需求 | https://blog.csdn.net/nuoweishizi/article/details/113474776 |
| INV-9.4 | 大规模仿真扩展 | 30 亿门级 GPU 芯片，Voltus 用 13T 内存、近千 CPU，一天内完成所有仿真 | https://blog.csdn.net/nuoweishizi/article/details/113474776 |

#### 10. 拥塞预测与优化

| 编号 | 子功能 | 描述 | 来源 URL |
|---|---|---|---|
| INV-10.1 | Integrated Congestion-Driven Placement | 见 INV-1.4 | https://community.cadence.com/cadence_blogs_8/b/di/posts/unlocking-ppa-with-innovus-what-s-new-and-how-to-unleash-it |
| INV-10.2 | AI 拥塞感知布线 | ML 引导的拥塞感知布线，强化学习与策略引导自适应，自动绕开设计瓶颈 | https://www.ust.com/en/insights/ai-in-cadence-innovus-workflows-10x-faster-physical-design-in-2025 |

#### 11. 3D-IC 与先进封装

| 编号 | 子功能 | 描述 | 来源 URL |
|---|---|---|---|
| INV-11.1 | Integrity 3D-IC Platform | 支持 TSMC-COUPE 参考流程，用于堆叠芯片设计 | https://www.fangzhenxiu.com/post/15154106/ |
| INV-11.2 | 3DFabric 支持 | 支持 TSMC 3DFabric 平台的 SoIC/CoWoS/InFO 等先进封装配置，覆盖 N3/N2/A16 节点 | https://www.eetimes.com/ai-and-chiplets-prominent-at-tsmc-oip-2025/ |
| INV-11.3 | 多芯片物理实现与分析 | 支持 bump connection 自动化、多 chiplet 物理实现与分析、smart alignment marker insertion | https://windowsforum.com/threads/cadence-and-tsmc-expand-ai-driven-flows-for-n2p-n3-3d-ic-designs.382889/ |

#### 12. 物理验证

| 编号 | 子功能 | 描述 | 来源 URL |
|---|---|---|---|
| INV-12.1 | Pegasus Verification System | Pegasus 物理验证系统，与 Innovus 集成进行签核级 DRC/LVS | https://www.fangzhenxiu.com/post/15154106/ |
| INV-12.2 | Quantus Extraction | Quantus 提取解决方案，与 Innovus 协同进行寄生参数提取 | https://www.fangzhenxiu.com/post/15154106/ |

---

## 第二部分：Synopsys IC Compiler II (ICC2)

### 工具概述

Synopsys IC Compiler™ II (ICC2) 是 Synopsys 公司的业界领先 place-and-route 解决方案，为各类市场与工艺节点的新一代设计提供最佳 QoR。核心架构包含 pervasively parallel 优化框架、多目标全局布局、Zroute 布线、Arc-based 并发时钟数据优化、ML 驱动拥塞预测与 DRC 闭合，以及与 PrimeTime / IC Validator 的 Advanced Fusion 集成。支持 500M+ 实例容量，已通过 TSMC/Samsung/Intel Foundry 等先进节点认证。

来源：
- https://www.synopsys.com/zh-cn/implementation-and-signoff/physical-implementation/ic-compiler.html
- https://www.synopsys.com/content/dam/synopsys/implementation&signoff/datasheets/ic-compiler-ii-ds.pdf

---

### 功能点清单

#### 1. 多目标全局布局

| 编号 | 子功能 | 描述 | 来源 URL |
|---|---|---|---|
| ICC2-1.1 | Multi-objective Global Placement | 多目标全局布局，同时优化时序、功耗、面积、拥塞 | https://www.synopsys.com/content/dam/synopsys/implementation&signoff/datasheets/ic-compiler-ii-ds.pdf |
| ICC2-1.2 | Routing Driven Placement Optimization | 布线驱动的布局优化，提前考虑可布线性 | https://www.synopsys.com/content/dam/synopsys/implementation&signoff/datasheets/ic-compiler-ii-ds.pdf |
| ICC2-1.3 | Next-generation Advanced 2D Placement | 新一代先进二维布局与合规化（legalization） | https://www.synopsys.com/content/dam/synopsys/implementation&signoff/datasheets/ic-compiler-ii-ds.pdf |
| ICC2-1.4 | Congestion Aware Placement | 拥塞感知布局与优化 | https://www.synopsys.com/zh-cn/implementation-and-signoff/physical-implementation/ic-compiler.html |
| ICC2-1.5 | Unified TNS-driven Optimization | 统一 TNS（Total Negative Slack）驱动的优化框架 | https://www.synopsys.com/content/dam/synopsys/implementation&signoff/datasheets/ic-compiler-ii-ds.pdf |

#### 2. Zroute 布线

| 编号 | 子功能 | 描述 | 来源 URL |
|---|---|---|---|
| ICC2-2.1 | Zroute 多线程布线架构 | Zroute 利用先进布线算法与多线程能力，在主流多核平台上实现高达 10× 加速 | https://ww-w.catagle.com/25-3/ICC_AG_Datasheet_Final_110711.htm |
| ICC2-2.2 | Native Soft Rules 光刻感知 | Zroute 架构集成原生 soft rules，实现光刻感知布线，避免制造问题 | https://ww-w.catagle.com/25-3/ICC_AG_Datasheet_Final_110711.htm |
| ICC2-2.3 | 并发优化 | Zroute 同时考虑制造规则、时序与其他设计目标的影响，并发优化 | https://ww-w.catagle.com/25-3/ICC_AG_Datasheet_Final_110711.htm |
| ICC2-2.4 | Routing Layer Driven Optimization | 布线层驱动优化、自动 NDR（Non-Default Rules）、过孔支柱（via pillar）优化 | https://www.synopsys.com/content/dam/synopsys/implementation&signoff/datasheets/ic-compiler-ii-ds.pdf |

#### 3. ML 拥塞预测与 DRC 闭合

| 编号 | 子功能 | 描述 | 来源 URL |
|---|---|---|---|
| ICC2-3.1 | ML 驱动布线拥塞预测 | 机器学习驱动的布线拥塞预测，提升设计收敛可预测性 | https://www.synopsys.com/content/dam/synopsys/implementation&signoff/datasheets/ic-compiler-ii-ds.pdf |
| ICC2-3.2 | ML 驱动 DRC 收敛 | 机器学习驱动的 DRC 收敛，加速详细布线后违例修复 | https://www.synopsys.com/content/dam/synopsys/implementation&signoff/datasheets/ic-compiler-ii-ds.pdf |
| ICC2-3.3 | ML 宏单元布局 (MLMP) | ML-based Macro Placement 自动化宏单元布局迭代，支持 on-edge / free-form / hybrid 三种风格 | https://www.synopsys.com/content/dam/synopsys/implementation&signoff/white-papers/ml-macro-placement-wp.pdf |
| ICC2-3.4 | ML ECO 预测 | ML 从 ECO 数据学习，快速准确预测功耗回收选择，避免昂贵穷举计算 | https://iipseries.org/assets/docupload/rsl202611C86761DFFFE0F.pdf |
| ICC2-3.5 | AI 驱动优化 (2025.06) | 2025.06 版本引入 AI 驱动优化，ML 算法分析时序/拥塞/功耗瓶颈，自动交付更智能的闭合策略 | https://stablewarez.com/shop/synopsys-ic-compiler-ii-icc2-2025-06-download/ |

#### 4. PrimeTime 时序签核

| 编号 | 子功能 | 描述 | 来源 URL |
|---|---|---|---|
| ICC2-4.1 | PrimeTime 延迟计算集成 | IC Compiler II 内部直接访问 Golden PrimeTime 延迟计算引擎，最小化 ECO 迭代 | https://www.synopsys.com/content/dam/synopsys/implementation&signoff/datasheets/ic-compiler-ii-ds.pdf |
| ICC2-4.2 | PrimeTime ECO 集成 | 布线优化进程中集成 PrimeTime ECO 流程，达到飞快周转时间 | https://www.synopsys.com/content/dam/synopsys/implementation&signoff/datasheets/ic-compiler-ii-ds.pdf |
| ICC2-4.3 | Path-Based Analysis (PBA) | 穷举路径分析（exhaustive path-based analysis），提供无与伦比的 QoR | https://www.synopsys.com/content/dam/synopsys/implementation&signoff/datasheets/ic-compiler-ii-ds.pdf |
| ICC2-4.4 | Arc-based 并发时钟数据优化 | 全流程基于 Arc 的并发时钟与数据优化 | https://www.synopsys.com/content/dam/synopsys/implementation&signoff/datasheets/ic-compiler-ii-ds.pdf |

#### 5. PrimePower / 功耗优化

| 编号 | 子功能 | 描述 | 来源 URL |
|---|---|---|---|
| ICC2-5.1 | Total Power Optimization | 全局最小值驱动的总功耗优化 | https://www.synopsys.com/content/dam/synopsys/implementation&signoff/datasheets/ic-compiler-ii-ds.pdf |
| ICC2-5.2 | IEEE 1801 UPF / 多电压支持 | 支持 IEEE 1801 UPF 多电压设计 | https://www.synopsys.com/content/dam/synopsys/implementation&signoff/datasheets/ic-compiler-ii-ds.pdf |
| ICC2-5.3 | 功耗驱动逻辑再综合 | 布线拥塞、时序与功耗驱动的逻辑再综合 | https://www.synopsys.com/content/dam/synopsys/implementation&signoff/datasheets/ic-compiler-ii-ds.pdf |
| ICC2-5.4 | IR Drop Driven Optimization | 先进融合技术：所有重要流程步骤都执行电压降驱动优化 | https://www.synopsys.com/content/dam/synopsys/implementation&signoff/datasheets/ic-compiler-ii-ds.pdf |
| ICC2-5.5 | Leakage/Dynamic Power 优化 (2025.06) | 2025.06 版本增强漏电与动态功耗优化，降低低功耗 SoC 总功耗 | https://stablewarez.com/shop/synopsys-ic-compiler-ii-icc2-2025-06-download/ |

#### 6. 物理验证

| 编号 | 子功能 | 描述 | 来源 URL |
|---|---|---|---|
| ICC2-6.1 | IC Validator In-Loop | IC Validator 在环提供签核 DRC 反馈，实现签核驱动 DRC 验证与修复 | https://www.synopsys.com/content/dam/synopsys/implementation&signoff/datasheets/ic-compiler-ii-ds.pdf |
| ICC2-6.2 | Signoff-driven DRC Validation | 签核驱动的 DRC 验证与修复环路 | https://www.synopsys.com/zh-cn/implementation-and-signoff/physical-implementation/ic-compiler.html |

#### 7. 先进节点支持（3nm / 2nm 及以下）

| 编号 | 子功能 | 描述 | 来源 URL |
|---|---|---|---|
| ICC2-7.1 | Multi-pattern / FinFET 感知流程 | 多重图形与 FinFET 感知设计流程 | https://www.synopsys.com/content/dam/synopsys/implementation&signoff/datasheets/ic-compiler-ii-ds.pdf |
| ICC2-7.2 | 3nm / 2nm 节点优化 (2025.06) | 2025.06 版本针对 3nm、2nm 及更先进节点的布局、布线、时序闭合算法优化 | https://stablewarez.com/shop/synopsys-ic-compiler-ii-icc2-2025-06-download/ |
| ICC2-7.3 | IBM 3nm DTCO 合作 | 与 IBM 合作将 DTCO 工具流扩展到 3nm 及以下，覆盖 GAA nanowire/nanoslab 新晶体管架构 | https://anysilicon.com/ibm-synopsys-accelerate-3nm-process-development-dtco-innovations/ |
| ICC2-7.4 | 晶圆代工厂认证 | 针对先进工艺节点的高级晶圆代工厂支持与认证 | https://www.synopsys.com/content/dam/synopsys/implementation&signoff/datasheets/ic-compiler-ii-ds.pdf |

#### 8. 分布式与多线程

| 编号 | 子功能 | 描述 | 来源 URL |
|---|---|---|---|
| ICC2-8.1 | Pervasively Parallel Framework | 普遍的并行优化框架，覆盖所有主要流程步骤 | https://www.synopsys.com/content/dam/synopsys/implementation&signoff/datasheets/ic-compiler-ii-ds.pdf |
| ICC2-8.2 | Multi-threaded & Distributed Computing | 适合所有主要流程步骤的多线程与分布式计算 | https://www.synopsys.com/content/dam/synopsys/implementation&signoff/datasheets/ic-compiler-ii-ds.pdf |
| ICC2-8.3 | 紧凑数据模型 | 层次化数据模型内存占用比传统工具少 2-3×，容量上限 500M+ 可放置实例 | https://www.synopsys.com/content/dam/synopsys/implementation&signoff/datasheets/ic-compiler-ii-ds.pdf |
| ICC2-8.4 | Near-linear 多核线程 | 关键基础组件（数据库访问、时序分析）近线性多核线程，加速各阶段优化 | https://www.synopsys.com/content/dam/synopsys/implementation&signoff/datasheets/ic-compiler-ii-ds.pdf |
| ICC2-8.5 | 分布式加速 (2025.06) | 2025.06 版本新增分布式与多线程处理，运行时速度较前版本提升 30% | https://stablewarez.com/shop/synopsys-ic-compiler-ii-icc2-2025-06-download/ |

#### 9. Advanced Fusion Technology（先进融合技术）

| 编号 | 子功能 | 描述 | 来源 URL |
|---|---|---|---|
| ICC2-9.1 | Physically-aware Logic Re-synthesis | 物理感知逻辑再综合 | https://www.synopsys.com/content/dam/synopsys/implementation&signoff/datasheets/ic-compiler-ii-ds.pdf |
| ICC2-9.2 | IR Drop Driven Optimization (全流程) | 所有重要流程步骤都执行电压降驱动优化 | https://www.synopsys.com/content/dam/synopsys/implementation&signoff/datasheets/ic-compiler-ii-ds.pdf |
| ICC2-9.3 | PrimeTime Delay Calc-based Routing Opt | 基于 PrimeTime 延迟计算的布线优化，达到金牌准确度 | https://www.synopsys.com/content/dam/synopsys/implementation&signoff/datasheets/ic-compiler-ii-ds.pdf |
| ICC2-9.4 | Integrated PrimeTime ECO Flow | 布线优化进程中集成 PrimeTime ECO 流程 | https://www.synopsys.com/content/dam/synopsys/implementation&signoff/datasheets/ic-compiler-ii-ds.pdf |

#### 10. 设计规划与容量

| 编号 | 子功能 | 描述 | 来源 URL |
|---|---|---|---|
| ICC2-10.1 | 500M+ 实例容量 | 支持超过 5 亿个标准单元实例的最高容量解决方案 | https://www.synopsys.com/content/dam/synopsys/implementation&signoff/datasheets/ic-compiler-ii-ds.pdf |
| ICC2-10.2 | 透明层次化优化 | 全套设计规划功能，包括透明层次化优化 | https://www.synopsys.com/content/dam/synopsys/implementation&signoff/datasheets/ic-compiler-ii-ds.pdf |
| ICC2-10.3 | Reference Methodology (RM) | 开箱即用的简单参考方法，便于完成设置；RM Flow 按代工厂工艺/设计类型定制 | https://www.synopsys.com/content/dam/synopsys/implementation&signoff/datasheets/ic-compiler-ii-ds.pdf |
| ICC2-10.4 | MCMM 并发感知 | 并发 MCMM（Multi-Corner Multi-Mode）感知布局、布线与优化转换 | https://ww-w.catagle.com/25-3/ICC_AG_Datasheet_Final_110711.htm |

#### 11. Fusion Compiler 集成

| 编号 | 子功能 | 描述 | 来源 URL |
|---|---|---|---|
| ICC2-11.1 | Fusion Compiler 无缝集成 | 2025.06 版本增强与 Synopsys Fusion Compiler 与 PrimeTime 签核工具的数据共享 | https://stablewarez.com/shop/synopsys-ic-compiler-ii-icc2-2025-06-download/ |
| ICC2-11.2 | Design Compiler Graphical 协同 | 与 Design Compiler Graphical 协同，提供业界最强的综合与物理实现相关性，最小化布局拥塞 | https://ww-w.catagle.com/25-3/ICC_AG_Datasheet_Final_110711.htm |

---

## 功能点统计

### Cadence Innovus 部分

| 类别 | 子功能数 |
|---|---|
| 1. GigaPlace 全局布局 | 5 |
| 2. GigaOpt 优化 | 6 |
| 3. PRO 全局-详细布线 | 2 |
| 4. ML DRC / AI 驱动 | 4 |
| 5. 先进节点支持 | 5 |
| 6. 分布式与多线程 | 2 |
| 7. 时序优化 | 3 |
| 8. 功耗优化 | 3 |
| 9. IR 分析 | 4 |
| 10. 拥塞预测 | 2 |
| 11. 3D-IC 与先进封装 | 3 |
| 12. 物理验证 | 2 |
| **小计** | **41** |

### Synopsys ICC2 部分

| 类别 | 子功能数 |
|---|---|
| 1. 多目标全局布局 | 5 |
| 2. Zroute 布线 | 4 |
| 3. ML 拥塞预测与 DRC 闭合 | 5 |
| 4. PrimeTime 时序签核 | 4 |
| 5. PrimePower / 功耗优化 | 5 |
| 6. 物理验证 | 2 |
| 7. 先进节点支持 | 4 |
| 8. 分布式与多线程 | 5 |
| 9. Advanced Fusion Technology | 4 |
| 10. 设计规划与容量 | 4 |
| 11. Fusion Compiler 集成 | 2 |
| **小计** | **44** |

### 总计

| 工具 | 功能点数 |
|---|---|
| Cadence Innovus | 41 |
| Synopsys ICC2 | 44 |
| **T12 文档总计** | **85** |

---

## 参考来源汇总

1. https://community.cadence.com/cadence_blogs_8/b/di/posts/unlocking-ppa-with-innovus-what-s-new-and-how-to-unleash-it
2. https://wenku.csdn.net/answer/7pcjs53ntv
3. https://www.synopsys.com/zh-cn/implementation-and-signoff/physical-implementation/ic-compiler.html
4. https://www.synopsys.com/content/dam/synopsys/implementation&signoff/datasheets/ic-compiler-ii-ds.pdf
5. https://ww-w.catagle.com/25-3/ICC_AG_Datasheet_Final_110711.htm
6. https://windowsforum.com/threads/cadence-and-tsmc-expand-ai-driven-flows-for-n2p-n3-3d-ic-designs.382889/
7. https://www.fangzhenxiu.com/post/15154106/
8. https://www.eetimes.com/ai-and-chiplets-prominent-at-tsmc-oip-2025/
9. https://www.ust.com/en/insights/ai-in-cadence-innovus-workflows-10x-faster-physical-design-in-2025
10. https://blog.csdn.net/nuoweishizi/article/details/113474776
11. https://stablewarez.com/shop/synopsys-ic-compiler-ii-icc2-2025-06-download/
12. https://www.synopsys.com/content/dam/synopsys/implementation&signoff/white-papers/ml-macro-placement-wp.pdf
13. https://anysilicon.com/ibm-synopsys-accelerate-3nm-process-development-dtco-innovations/
14. https://iipseries.org/assets/docupload/rsl202611C86761DFFFE0F.pdf

---

**文档结束** | 调研日期 2026-06-25 | 版本 v1.0
