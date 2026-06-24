# Tasks

## 阶段一：数据收集与差距核实

- [x] Task 1: 收集第 80-94 轮所有进展记录
  - [x] SubTask 1.1: 从 `操作记录.md` 提取第 80-94 轮的关键改进（INSERTION_LOSS_DB、process_node 一致性、质量门禁零违规、器件损耗补全、DRV 评估）
  - [x] SubTask 1.2: 核实当前测试套件状态（2330 passed, 16 skipped）
  - [x] SubTask 1.3: 核实当前质量门禁状态（0 警告 0 错误）
  - [x] SubTask 1.4: 核实当前 PDK/DRC/Benchmark 数量（81 器件 / 9 foundry / 3 benchmark）

## 阶段二：商业对比分析报告编写（详细报告）

- [x] Task 2: 编写 `docs/commercial_gap_analysis_v2.md` 详细报告
  - [x] SubTask 2.1: 编写"摘要：PoLaRIS 当前定位（v2.0）"，刷新能力盘点表
  - [x] SubTask 2.2: 编写"商业光电子 EDA 工具能力矩阵"（保留 v1.0 的 7 个商业工具 + 3 个电子 EDA + 4 个开源对手）
  - [x] SubTask 2.3: 编写"PoLaRIS 关键差距清单（v2.0）"，刷新 P0/P1/P2 各项的"已修复"标记
  - [x] SubTask 2.4: 编写"v1.0 → v2.0 评分变更说明"，列出每个维度分数变更的具体轮次与依据
  - [x] SubTask 2.5: 编写"36 个月里程碑规划（M1-M6）"，每个里程碑含时间窗/核心目标/严格边界/验收标准/任务清单
  - [x] SubTask 2.6: 编写"来源 URL 列表"，保留 v1.0 全部来源 + 新增第 80-94 轮引用的来源
  - [x] SubTask 2.7: 编写"结论与建议"，刷新优先级建议为 36 个月里程碑版本

## 阶段三：现有文档覆盖重写

- [x] Task 3: 覆盖重写 `docs/commercial_gap_analysis.md`（v1.0 → v2.0）
  - [x] SubTask 3.1: 头部版本号更新为 v2.0，刷新日期 2026-06-22
  - [x] SubTask 3.2: 用 `commercial_gap_analysis_v2.md` 的内容覆盖（保留原文件名，内容刷新）
  - [x] SubTask 3.3: 确保不保留 v1.0 过时评分（6.0/10 → 6.1/10）

- [x] Task 4: 覆盖重写 `docs/industry_alignment_roadmap.md`（v1.0 → v2.0）
  - [x] SubTask 4.1: 头部版本号更新为 v2.0
  - [x] SubTask 4.2: 保留业界对照矩阵（AlphaChip/Apollo/LiDAR/PhIDO）
  - [x] SubTask 4.3: 用 36 个月里程碑（M1-M6）替换原"3/6/12-24 个月"路线图
  - [x] SubTask 4.4: 刷新学术前沿综合评估得分

- [x] Task 5: 刷新 `docs/roadmap.md`（v1.0 → v2.0）
  - [x] SubTask 5.1: 头部版本号更新为 v2.0
  - [x] SubTask 5.2: 商业化就绪度从 4/10 刷新为 6.1/10
  - [x] SubTask 5.3: 里程碑规划与 36 个月 M1-M6 对齐

## 阶段四：操作记录与验证

- [x] Task 6: 追加 `操作记录.md` 第 94 轮记录
  - [x] SubTask 6.1: 记录商业对比分析全面刷新（v1.0 → v2.0）
  - [x] SubTask 6.2: 记录 36 个月里程碑规划制定
  - [x] SubTask 6.3: 记录评分变更（6.0 → 6.1，文档与测试 +1）
  - [x] SubTask 6.4: 记录下一轮（第 95 轮）计划

- [x] Task 7: 验证文档一致性
  - [x] SubTask 7.1: 验证三个文档版本号均为 v2.0
  - [x] SubTask 7.2: 验证评分变更可溯源（每个分数变更对应具体轮次）
  - [x] SubTask 7.3: 验证 36 个月里程碑边界严格（不扩散、不超前）
  - [x] SubTask 7.4: 验证无造假数据（所有来源 URL 有效）

# Task Dependencies

- Task 2 依赖 Task 1（需先收集数据才能编写报告）
- Task 3/4/5 依赖 Task 2（需先完成详细报告才能覆盖重写）
- Task 6 依赖 Task 3/4/5（需完成文档刷新才能记录）
- Task 7 依赖 Task 6（需完成所有工作才能验证）
- Task 3/4/5 可并行（三个文档独立刷新）
