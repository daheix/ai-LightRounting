# Tasks

## 阶段1: 光电子DRC规则完整性审计（网络资料对照）

- [ ] Task 1: 检索光电子行业PDK DRC规则集
  - [ ] SubTask 1.1: 检索SiEPIC EBeam PDK完整DRC规则集（https://github.com/SiEPIC/SiEPIC_EBeam_PDK）
  - [ ] SubTask 1.2: 检索AIM Photonics PDK DRC规则（AIM Academy官网）
  - [ ] SubTask 1.3: 检索IMEC iSiPP50G PDK DRC规则（IMEC官网）
  - [ ] SubTask 1.4: 检索AMF PDK DRC规则（Advanced Micro Foundry）
  - [ ] SubTask 1.5: 检索KLayout generic DRC scripts（https://www.klayout.de/manual/drc.xml）
  - [ ] SubTask 1.6: 整理"当前12条规则 vs 行业PDK规则集"对照表，标注缺失规则
- [ ] Task 2: 生成DRC规则对照报告
  - [ ] SubTask 2.1: 创建 `docs/drc_rules_audit.md`，含对照表+缺失规则优先级
  - [ ] SubTask 2.2: 标注每条规则的文献来源（R02学术诚信）

## 阶段2: 剩余失败用例根因分析

- [ ] Task 3: 分析gdsfactory 2/37失败用例
  - [ ] SubTask 3.1: 运行 `python scripts/run_real_board_drc.py --source gdsfactory` 获取失败列表
  - [ ] SubTask 3.2: 逐个分析失败根因（数据错误/真实bug/算法局限）
  - [ ] SubTask 3.3: 修复真实bug（数据错误标记为known_limitation）
- [ ] Task 4: 分析expert_demos 4/19失败用例
  - [ ] SubTask 4.1: 运行DRC获取失败列表
  - [ ] SubTask 4.2: 逐个分析根因
  - [ ] SubTask 4.3: 修复真实bug

## 阶段3: DRC误报率量化

- [ ] Task 5: 实现DRC误报审查脚本
  - [ ] SubTask 5.1: 创建/完善 `scripts/audit_drc_false_positives.py`
  - [ ] SubTask 5.2: 抽样50个PORT_ALIGNMENT违规用例
  - [ ] SubTask 5.3: 人工核查每个用例（真违规 vs 误报）
  - [ ] SubTask 5.4: 生成 `out/audit/drc_false_positive_report.md`

## 阶段4: 100%准确度必要性评估

- [ ] Task 6: 检索行业实践资料
  - [ ] SubTask 6.1: 检索"DRC clean tape-out requirement"行业惯例
  - [ ] SubTask 6.2: 检索Mohan DATE 2023 "Machine Learning for DRC"误报率标准
  - [ ] SubTask 6.3: 检索AI训练数据噪声容忍度（Bengio ICML 2009）
- [ ] Task 7: 生成100%准确度评估报告
  - [ ] SubTask 7.1: 基于3类场景（tape-out/研发/AI训练）给出建议
  - [ ] SubTask 7.2: PoLaRIS定位明确（研发+AI训练，95%+商用门槛）

## 阶段5: 补齐缺失DRC规则

- [x] Task 8: 实现缺失的高优先级规则（6 条 P0 波导级，覆盖率 48%→72%）
  - [x] SubTask 8.1: BEND_RADIUS_MIN（5.0μm，SiEPIC/IMEC/AMF/LiDAR/FluxCore）
  - [x] SubTask 8.2: WAVEGUIDE_WIDTH_MATCH（0.0 完全匹配，SiEPIC Verification "Mismatched pin widths"）
  - [x] SubTask 8.3: MIN_NOTCH（0.1μm=100nm，KLayout notch()/FluxCore）
  - [x] SubTask 8.4: WAVEGUIDE_MANHATTAN（SiEPIC Verification "首末段必须 Manhattan"）
  - [x] SubTask 8.5: ENCLOSED_AREA_MIN（0.01μm²，KLayout area_check + DFS 环检测）
  - [x] SubTask 8.6: CROSSING_ANGULAR（90°，LiDAR 2.0 arXiv:2505.17239 II-B3）
- [x] Task 9: 为新规则添加单元测试
  - [x] SubTask 9.1: 每条新规则 3 个测试（pass/fail/edge case），共 18 个新测试

## 阶段6: 商用版DRC完整性报告

- [ ] Task 10: 生成综合报告
  - [ ] SubTask 10.1: 创建 `docs/drc_completeness_audit_report.md`
  - [ ] SubTask 10.2: 含规则对照表+通过率统计+误报率+100%评估+商用建议
  - [ ] SubTask 10.3: 追加操作记录到`操作记录.md`

## 阶段7: 验证与提交

- [x] Task 11: 全量回归测试
  - [x] SubTask 11.1: `python -m pytest modules/drc/tests/` → 78 passed in 0.14s
  - [x] SubTask 11.2: AST 扫描 0 函数超 80 行（rules.py/engine.py/checks.py）
- [ ] Task 12: 提交代码与文档
  - [x] SubTask 12.1: rules.py/engine.py/checks.py 已由 auto_commit 自动提交（HEAD 48002a90）
  - [ ] SubTask 12.2: __init__.py + tests/test_drc.py + checklist.md + 操作记录.md 待提交

# Task Dependencies
- Task 1-2 可并行（规则检索+对照报告）
- Task 3-4 可并行（gdsfactory+expert_demos失败分析）
- Task 5 独立（误报率量化）
- Task 6-7 独立（100%评估）
- Task 8 依赖Task 1-2完成（识别缺失规则后实现）
- Task 9 依赖Task 8完成
- Task 10 依赖Task 1-9全部完成
- Task 11-12 依赖Task 10完成
