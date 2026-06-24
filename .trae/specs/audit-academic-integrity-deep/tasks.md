# Tasks

- [ ] Task 1: 网络检索验证关键论文 URL 可达性
  - [ ] SubTask 1.1: 收集 R01-R36 全部模块中引用的论文 DOI/URL（约 50+ 条）
  - [ ] SubTask 1.2: 逐条网络检索验证 URL 可达性与内容匹配
  - [ ] SubTask 1.3: 记录不可达/内容不符的 URL，标记为问题项

- [ ] Task 2: 固定参数来源与依据清单
  - [ ] SubTask 2.1: 提取 src/polaris/ 全部模块中的固定物理常数与器件参数
  - [ ] SubTask 2.2: 逐条标注参数值、来源文献、文献 URL、参数依据
  - [ ] SubTask 2.3: 网络交叉验证参数是否在公开文献报告区间内

- [ ] Task 3: 计算公式推导来源核对
  - [ ] SubTask 3.1: 提取全部模块中的核心计算公式（约 30+ 条）
  - [ ] SubTask 3.2: 逐条核对公式与原始文献的一致性
  - [ ] SubTask 3.3: 记录公式内容、推导来源、一致性结论

- [ ] Task 4: 关键论文作者（人物）学术背景分析
  - [ ] SubTask 4.1: 筛选 10-15 位关键作者（Yee/Berenger/Marcuse/Lowery/Mirhoseini/Schulman/Mingaleev/Bogaerts/Smit/Augustin/Melati 等）
  - [ ] SubTask 4.2: 网络检索每位作者的所属机构、H-index、主要贡献、被引次数
  - [ ] SubTask 4.3: 评估引用权威性，记录人物背景清单

- [ ] Task 5: fall-back / 假数据 / mock 终检
  - [ ] SubTask 5.1: 全量 grep 检查 src/polaris/ 是否含 fallback/mock/fake/dummy/hardcode
  - [ ] SubTask 5.2: 运行已有 fall-back 检查测试
  - [ ] SubTask 5.3: 记录终检结果

- [ ] Task 6: 生成学术诚信审核报告
  - [ ] SubTask 6.1: 汇总 Task 1-5 结果到 docs/academic_integrity_audit.md
  - [ ] SubTask 6.2: 追加审核记录到操作记录.md
  - [ ] SubTask 6.3: 修复审核中发现的问题（如有）

# Task Dependencies
- Task 1, 2, 3, 4, 5 可并行执行
- Task 6 依赖 Task 1-5 全部完成
