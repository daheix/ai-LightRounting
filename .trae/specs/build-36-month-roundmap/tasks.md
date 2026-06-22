# Tasks

## 阶段一：网络综合分析（功能清单收集）

- [ ] Task 1: 检索商业光子 EDA 工具功能清单（7 个工具）
  - [ ] SubTask 1.1: WebSearch + WebFetch Ansys Lumerical（FDTD/MODE/INTERCONNECT/CML Compiler）官方文档
  - [ ] SubTask 1.2: WebSearch + WebFetch Luceda IPKISS 官方文档与 PDK 清单
  - [ ] SubTask 1.3: WebSearch + WebFetch Synopsys OptoDesigner 官方文档
  - [ ] SubTask 1.4: WebSearch + WebFetch Flexcompute Tidy3D 官方文档
  - [ ] SubTask 1.5: WebSearch + WebFetch VPIphotonics 官方文档与 PDK 清单
  - [ ] SubTask 1.6: WebSearch + WebFetch Siemens L-Edit Photonics（GPIC）官方文档
  - [ ] SubTask 1.7: WebSearch + WebFetch Aspic 官方文档

- [ ] Task 2: 检索开源光子 EDA 工具功能清单（4 个工具）
  - [ ] SubTask 2.1: WebFetch gdsfactory GitHub README 与文档站
  - [ ] SubTask 2.2: WebFetch KLayout 官方文档与 GitHub
  - [ ] SubTask 2.3: WebFetch sax GitHub README 与文档
  - [ ] SubTask 2.4: WebFetch simphony GitHub README 与 arXiv 论文

- [ ] Task 3: 检索电子 EDA 标杆与 AI 前沿（参考）
  - [ ] SubTask 3.1: WebSearch Cadence Innovus 2026 功能与 PPA 博客
  - [ ] SubTask 3.2: WebSearch Synopsys IC Compiler II 数据手册
  - [ ] SubTask 3.3: WebFetch AlphaChip Nature 2021/2024 论文与 Circuit Training 开源仓库
  - [ ] SubTask 3.4: WebFetch Apollo arXiv 2025 + LiDAR ISPD 2025 + PhIDO arXiv 2025

## 阶段二：编写商业工具功能清单对比矩阵

- [ ] Task 4: 编写 `docs/commercial_tools_feature_matrix.md`
  - [ ] SubTask 4.1: 编写头部（文档版本 v1.0，检索日期 2026-06-22）
  - [ ] SubTask 4.2: 编写"工具覆盖范围"章节（12+ 工具列表）
  - [ ] SubTask 4.3: 编写"功能清单维度"章节（15 个维度定义）
  - [ ] SubTask 4.4: 编写"功能对比大表"（12 工具 × 15 维度矩阵，每格标注来源 URL）
  - [ ] SubTask 4.5: 编写"PoLaRIS 当前能力"列（基于第 94 轮真实状态）
  - [ ] SubTask 4.6: 编写"差距分析"章节（按维度列出 PoLaRIS 与每个工具的差距）
  - [ ] SubTask 4.7: 编写"来源 URL 汇总"章节

## 阶段三：编写 36 个月逐月路标

- [ ] Task 5: 编写 `docs/36-RoundMap.md`
  - [ ] SubTask 5.1: 编写头部（文档版本 v1.0，创建日期 2026-06-22）
  - [ ] SubTask 5.2: 编写"路标总览"章节（6 阶段 × 6 月 = 36 月表格）
  - [ ] SubTask 5.3: 编写"从小到大逐个追赶策略"章节（阶段 1-6 追赶对象）
  - [ ] SubTask 5.4: 编写"阶段 1：R1-R6 追赶 sax + simphony"（每月交付目标/验收标准/依赖）
  - [ ] SubTask 5.5: 编写"阶段 2：R7-R12 追赶 KLayout + gdsfactory"
  - [ ] SubTask 5.6: 编写"阶段 3：R13-R18 追赶 Aspic + VPIphotonics"
  - [ ] SubTask 5.7: 编写"阶段 4：R19-R24 追赶 Siemens L-Edit + Synopsys OptoDesigner"
  - [ ] SubTask 5.8: 编写"阶段 5：R25-R30 追赶 Luceda IPKISS + Tidy3D"
  - [ ] SubTask 5.9: 编写"阶段 6：R31-R36 追赶 Ansys Lumerical + AlphaChip"
  - [ ] SubTask 5.10: 编写"验收标准汇总"章节（每月可验证标准）
  - [ ] SubTask 5.11: 编写"风险与依赖"章节

## 阶段四：操作记录与验证

- [ ] Task 6: 追加 `操作记录.md` 第 95 轮记录
  - [ ] SubTask 6.1: 记录 36-RoundMap 制定过程
  - [ ] SubTask 6.2: 记录商业工具功能清单对比矩阵编写
  - [ ] SubTask 6.3: 记录网络综合分析结果
  - [ ] SubTask 6.4: 记录下一轮（第 96 轮）计划

- [ ] Task 7: 验证文档完整性与学术诚信
  - [ ] SubTask 7.1: 验证 `36-RoundMap.md` 含 R1-R36 共 36 个月位置
  - [ ] SubTask 7.2: 验证 `commercial_tools_feature_matrix.md` 含 12+ 工具 × 15+ 维度
  - [ ] SubTask 7.3: 验证所有功能项标注来源 URL
  - [ ] SubTask 7.4: 验证 PoLaRIS 当前能力列基于第 94 轮真实状态（无造假）
  - [ ] SubTask 7.5: 验证"从小到大逐个追赶"策略顺序正确

# Task Dependencies

- Task 4 依赖 Task 1/2/3（需先完成网络检索才能编写矩阵）
- Task 5 依赖 Task 4（需先完成功能矩阵才能规划路标）
- Task 6 依赖 Task 4/5（需完成文档才能记录）
- Task 7 依赖 Task 6（需完成所有工作才能验证）
- Task 1/2/3 可并行（三类工具检索独立）
