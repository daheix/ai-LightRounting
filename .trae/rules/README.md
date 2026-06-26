# 项目规则索引

> PoLaRIS（光弈）光电子 AI 智能布局布线引擎项目强制开发规则。
> 所有规则文件强制执行，违反即视为代码不合格。
> 拆分原则：一个规则编号对应一个文件；超 50 行按子章节拆为 a/b/c；每文件 ≤ 50 行。

## 目录结构

```
.trae/rules/
├── README.md                    # 本索引文件
├── project_rules/               # 项目规则（R01-R27，源自 project_rules.md）
├── python_rules/                # Python 开发规则（P00-P15，源自 python代码开发规则.md）
└── D01-磁盘空间管理.md          # 其他规则（源自 磁盘空间管理.md）
```

## 项目规则（project_rules/）

| 编号 | 文件 | 标题 |
|------|------|------|
| R01 | project_rules/R01-方案检索与代码提交.md | 方案检索与代码提交纪律 |
| R02a | project_rules/R02a-项目目录结构-顶层与职责.md | 项目目录结构规范（顶层结构与职责） |
| R02b | project_rules/R02b-项目目录结构-模块划分与放置.md | 项目目录结构规范（模块划分与文件放置） |
| R03a | project_rules/R03a-三方工具-目录结构.md | 三方工具统一管理规范（目录结构） |
| R03b | project_rules/R03b-三方工具-清单与状态.md | 三方工具统一管理规范（清单与安装状态） |
| R03c | project_rules/R03c-三方工具-使用原则与文档.md | 三方工具统一管理规范（使用原则与文档） |
| R04a | project_rules/R04a-自研复刻-触发与结构.md | 自研复刻工具规范（触发条件与目录结构） |
| R04b | project_rules/R04b-自研复刻-质量与验证.md | 自研复刻工具规范（质量要求与验证） |
| R05a | project_rules/R05a-工具环境-离线一键安装.md | 工具环境安装与使用规范（离线一键安装） |
| R05b | project_rules/R05b-工具环境-联网安装与决策.md | 工具环境安装与使用规范（联网安装与决策矩阵） |
| R05c | project_rules/R05c-工具环境-使用与验证.md | 工具环境安装与使用规范（使用规范与验证） |
| R05d | project_rules/R05d-工具环境-状态同步与离线包.md | 工具环境安装与使用规范（状态同步与离线包） |
| R06 | project_rules/R06-发布制品管理.md | 发布制品管理规范 |
| R07a | project_rules/R07a-质量门禁-文件规模限制.md | 工业标准代码质量门禁（文件规模限制与重构） |
| R07b | project_rules/R07b-质量门禁-圈复杂度与脚本.md | 工业标准代码质量门禁（圈复杂度与门禁脚本） |
| R08 | project_rules/R08-Python编码风格.md | Python 编码风格规范 |
| R09a | project_rules/R09a-Git工作流-分支与提交.md | Git 工作流与团队协作规范（分支与提交） |
| R09b | project_rules/R09b-Git工作流-审查与gitignore.md | Git 工作流与团队协作规范（代码审查与 .gitignore） |
| R10 | project_rules/R10-测试规范.md | 测试规范 |
| R11 | project_rules/R11-文档规范.md | 文档规范 |
| R12 | project_rules/R12-CICD与自动化.md | CI/CD 与自动化 |
| R13 | project_rules/R13-依赖管理规范.md | 依赖管理规范 |
| R14 | project_rules/R14-错误处理与日志.md | 错误处理与日志规范 |
| R15 | project_rules/R15-性能与可维护性.md | 性能与可维护性规范 |
| R16 | project_rules/R16-发现Bug必须修复.md | 发现 Bug 必须修复纪律 |
| R17a | project_rules/R17a-开发完成即检门禁-要求与命令.md | 开发完成即检门禁纪律（要求与检查命令） |
| R17b | project_rules/R17b-开发完成即检门禁-处理与禁止.md | 开发完成即检门禁纪律（处理流程与禁止行为） |
| R18 | project_rules/R18-学术诚信与引用.md | 学术诚信与引用规范 |
| R19a | project_rules/R19a-操作记录-要求与格式.md | 操作记录维护纪律（要求与格式） |
| R19b | project_rules/R19b-操作记录-内容与禁止.md | 操作记录维护纪律（内容要求与禁止） |
| R20 | project_rules/R20-3dtool大文件管理.md | 3dtool 大文件管理规范 |
| R21a | project_rules/R21a-pyCopy版本管理-规则与文件.md | pyCopy 复刻品版本管理规范（版本规则与文件要求） |
| R21b | project_rules/R21b-pyCopy版本管理-优化与验收.md | pyCopy 复刻品版本管理规范（优化方向与验收） |
| R22 | project_rules/R22-商业交付与差距分析.md | 商业交付与差距分析纪律 |
| R23 | project_rules/R23-长时间任务进度汇报.md | 长时间后台任务进度汇报 |
| R24 | project_rules/R24-分支管理纪律.md | 分支管理纪律（禁止孤儿分支） |
| R25 | project_rules/R25-小任务网络检索必做.md | 小任务网络检索必做（新增） |
| R26 | project_rules/R26-学术诚信与质量来源.md | 学术诚信与质量来源（新增） |
| R27a | project_rules/R27a-权威检索资源-学术与社区.md | 权威检索资源清单（学术与社区，新增） |
| R27b | project_rules/R27b-权威检索资源-标准与智库.md | 权威检索资源清单（标准与智库，新增） |

## Python 开发规则（python_rules/）

| 编号 | 文件 | 标题 |
|------|------|------|
| P00 | python_rules/P00-角色与心智模型.md | 角色与心智模型 |
| P01 | python_rules/P01-代码风格与格式.md | 代码风格与格式（PEP 8 + Ruff 强制） |
| P02 | python_rules/P02-类型注解.md | 类型注解（强制 PEP 484） |
| P03 | python_rules/P03-三方库使用规范.md | 三方库使用规范（优先商用许可库） |
| P04a | python_rules/P04a-算法与数据结构-复杂度与向量化.md | 算法与数据结构规范（复杂度红线与向量化） |
| P04b | python_rules/P04b-算法与数据结构-选型与反模式.md | 算法与数据结构规范（选型与反模式） |
| P05a | python_rules/P05a-函数与模块设计-原则与模块.md | 函数与模块设计（原则与模块划分） |
| P05b | python_rules/P05b-函数签名规范.md | 函数与模块设计（函数签名规范） |
| P06 | python_rules/P06-错误处理.md | 错误处理（禁止 fall-back） |
| P07 | python_rules/P07-性能优化规范.md | 性能优化规范 |
| P08 | python_rules/P08-测试规范.md | 测试规范 |
| P09 | python_rules/P09-文档与注释.md | 文档与注释 |
| P10 | python_rules/P10-并发与异步.md | 并发与异步 |
| P11 | python_rules/P11-日志与可观测性.md | 日志与可观测性 |
| P12 | python_rules/P12-版本控制与提交.md | 版本控制与提交 |
| P13 | python_rules/P13-学术诚信.md | 学术诚信 |
| P14 | python_rules/P14-检查清单.md | 检查清单（提交前必过） |
| P15 | python_rules/P15-权威资源参考.md | 权威资源参考（持续更新） |

## 其他规则

| 编号 | 文件 | 标题 |
|------|------|------|
| D01 | D01-磁盘空间管理.md | 磁盘空间管理 |

## 规则来源与拆分说明

- **项目规则（R01-R24）**：源自原 `project_rules.md`（约 1474 行，24 条规则），已删除冗余的"参考来源汇总"章节（来源 URL 已内嵌至各规则文件）。
- **Python 开发规则（P00-P15）**：源自原 `python代码开发规则.md`（约 588 行，15 章节）。新增 P00 保留原"角色与心智模型"章节（含文件头元数据）。
- **磁盘空间管理（D01）**：源自原 `磁盘空间管理.md`（约 109 行），整体保留并精简至 50 行以内。
- **新增规则（R25-R27）**：基于用户指令新增，R27 因资源清单较长拆为 R27a/R27b。
