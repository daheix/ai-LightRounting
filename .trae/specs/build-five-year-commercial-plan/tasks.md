# Tasks

## 阶段 1: 商业可行性差距分析（基于学术诚信报告）

- [x] Task 1: 从 `docs/学术诚信检查.md` v3.3 提取 140 Bug 清单并按商业影响分级
  - [x] SubTask 1.1: 读取 §5 Bug 历史的 108 v3.3 新发现 Bug + 32 历史 Bug
  - [x] SubTask 1.2: 按 P0（阻断商业使用）/ P1（影响商业信誉）/ P2（优化项）分级
  - [x] SubTask 1.3: 列出每个 Bug 的商业影响描述（如"GAN 不训练 → 无法提供 AI 逆向设计服务"）
  - [x] SubTask 1.4: 输出"不满足商业使用模块清单"表格

- [x] Task 2: 核查 22 子包代码实际实现完整性（grep/ls/read 验证）
  - [x] SubTask 2.1: 验证 sim/ 161 文件实际实现（采样 10 个核心模块）
  - [x] SubTask 2.2: 验证 pdk/ 46 文件（采样 5 个）
  - [x] SubTask 2.3: 验证 trainer/ + rl/ + engine/ + router/ 75 文件（采样 10 个）
  - [x] SubTask 2.4: 验证 quantum/ + device/ + ai/ + inverse/ + verification/ + verify/ 15 文件
  - [x] SubTask 2.5: 输出"代码实际实现核查报告"（38/40 完整实现，0/40 假实现）

## 阶段 2: 商业工具功能差距矩阵（网络检索）

- [x] Task 3: 检索商业光子 EDA 工具功能清单（WebSearch + WebFetch）
  - [x] SubTask 3.1: Ansys Lumerical（FDTD/MODE/INTERCONNECT/CHARGE）官方文档检索
  - [x] SubTask 3.2: Luceda IPKISS 官方文档检索
  - [x] SubTask 3.3: Synopsys OptoDesigner + RSoft 官方文档检索
  - [x] SubTask 3.4: Tidy3D 官方文档检索
  - [x] SubTask 3.5: VPIphotonics VPItransmissionMaker 官方文档检索
  - [x] SubTask 3.6: Siemens L-Edit + Calibre 官方文档检索
  - [x] SubTask 3.7: Cadence Virtuoso 官方文档检索
  - [x] SubTask 3.8: 开源工具（gdsfactory/KLayout/sax/simphony/OpenROAD）官方文档检索
  - [x] SubTask 3.9: 输出"商业工具功能矩阵"（26 功能 × 12 工具，PoLaRIS 领先 5 项）

- [x] Task 4: 检索光子集成电路（PIC）市场规模数据
  - [x] SubTask 4.1: LightCounting PIC 市场报告检索（2025 USD 4.0B → 2031 USD 15.0B 光芯片）
  - [x] SubTask 4.2: Yole PIC 市场报告检索（硅光 2024 USD 0.278B → 2030 USD 2.7B）
  - [x] SubTask 4.3: Omdia 光子市场报告检索
  - [x] SubTask 4.4: Silicon Photonics 市场规模预测（2026-2031）
  - [x] SubTask 4.5: 输出"市场规模数据汇总"（TAM USD 15B / SAM USD 888M / SOM USD 25-40M）

## 阶段 3: 五年商业活动计划制定

- [x] Task 5: 制定 Year 1 商业化准备计划（2026H2-2027H1）
- [x] Task 6: 制定 Year 2 早期客户与产品化计划（2027H2-2028H1）
- [x] Task 7: 制定 Year 3 规模化与市场扩张计划（2028H2-2029H1）
- [x] Task 8: 制定 Year 4 行业领先与生态建设计划（2029H2-2030H1）
- [x] Task 9: 制定 Year 5 退出准备与平台化计划（2030H2-2031H1）

## 阶段 4: 营收与融资预测

- [x] Task 10: 五年营收预测（Year 5 ARR USD 35M，CAGR 182%）
- [x] Task 11: 五年融资预测（累计 USD 152-286M，5 轮）

## 阶段 5: 文档撰写与提交

- [x] Task 12: 撰写 `商业活动计划表-五年.md`（§1-§9 完整章节）
- [x] Task 13: 提交代码 + 更新操作记录
  - [ ] SubTask 13.1: git add 商业活动计划表-五年.md 操作记录.md
  - [ ] SubTask 13.2: git commit -m "docs(commercial): 五年商业活动计划表 v1.0（基于 v3.3 学术诚信收官）"
  - [ ] SubTask 13.3: git push origin main
  - [ ] SubTask 13.4: 操作记录.md 追加本轮商业分析记录

# Task Dependencies

- Task 1 → Task 5（先识别不满足商业使用的模块，才能制定 Year 1 技术债清理计划）
- Task 2 → Task 5（代码实际实现核查结果影响 Year 1 计划）
- Task 3 → Task 5（商业工具功能差距影响 Year 1 产品化方向）
- Task 4 → Task 10（市场规模数据是营收预测基础）
- Task 1-4 → Task 12（撰写文档依赖前 4 阶段分析结果）
- Task 5-9 可并行（五年计划各年独立）
- Task 10-11 可并行（营收与融资预测独立）
- Task 12 → Task 13（先写文档再提交）
