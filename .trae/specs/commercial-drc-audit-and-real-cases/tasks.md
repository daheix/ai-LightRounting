# Tasks

- [x] Task 1: DRC 误报全量审查（real_board 87 电路违规分类，commit 65082681）
  - [x] SubTask 1.1: 编写 `scripts/audit_drc_false_positives.py`（796行），基于 real_board 87 电路（非原 1200 生成电路），严格模式 bend_compensate=False 收集 PORT_ALIGNMENT 违规
  - [x] SubTask 1.2: 按规则名统计违规分布（PORT_ALIGNMENT 违规 45 条，按类别: expert_demos/gdsfactory）
  - [x] SubTask 1.3: 抽样 50 个 PORT_ALIGNMENT 违规（实际 45 条全部抽样），自动核查是真违规还是误报（is_false_positive 5步判定）
  - [x] SubTask 1.4: 输出 `out/audit/drc_false_positive_report.md`，列出误报率（11.1%）、误报根因、修复建议
  - [x] SubTask 1.5: 误报率 ≤5% 商用门槛 — ❌ 未达标（11.1% > 5%），需优化布局算法（移入 Task 2 范畴）

- [ ] Task 2: 矩阵型拓扑布局端口对齐修复（DRC 通过率提升核心）
  - [ ] SubTask 2.1: 分析 `modules/place/src/polaris_place/analytical.py` 对矩阵拓扑的布局逻辑
  - [ ] SubTask 2.2: 增加端口对齐后处理：布局后对每条连接的端口做 y 轴对齐（移动器件使 dy ≤ 容差）
  - [ ] SubTask 2.3: 验证对齐后处理不破坏 NO_OVERLAP/MIN_SPACING 约束
  - [ ] SubTask 2.4: 回归测试：6 种矩阵拓扑 DRC 通过率 ≥ 90%

- [ ] Task 3: DRC 规则阈值文献审查（确保非静默放宽）
  - [ ] SubTask 3.1: 核对 PORT_ALIGNMENT 5μm 容差的文献来源（SiEPIC EBeam PDK / Chrostowski 2015）
  - [ ] SubTask 3.2: 若布局算法修复后仍不达标，评估容差调整的工艺合理性（需文献支撑）
  - [ ] SubTask 3.3: 在 `modules/drc/src/polaris_drc/engine.py` docstring 标注所有阈值的文献来源

- [ ] Task 4: 网络真实用例下载器
  - [ ] SubTask 4.1: 创建 `scripts/download_real_circuits.py`，支持从 GitHub 公开仓库批量下载
  - [ ] SubTask 4.2: 下载 SiEPIC EBeam PDK 完整示例集（GDS + netlist）
  - [ ] SubTask 4.3: 下载 gdsfactory 样例库 netlist（gf_*.json 已有 40 个，补全至全集）
  - [ ] SubTask 4.4: 下载 picbench 基准全集（已有 18 个，补全至全集）
  - [ ] SubTask 4.5: 下载 OpenROAD/ALIGN EPIC 基准电路
  - [ ] SubTask 4.6: 下载 Luceda IPKISS 公开示例
  - [ ] SubTask 4.7: 真实用例存储到 `data/benchmarks/real/{source}/`，生成 `data/benchmarks/real/index.json`

- [ ] Task 5: 真实用例格式转换器
  - [ ] SubTask 5.1: 创建 `scripts/convert_real_to_polaris.py`，支持 GDS/netlist/JSON → CircuitSpec
  - [ ] SubTask 5.2: SiEPIC GDS 转换：用 klayout 读取 GDS 提取器件+连接，转 CircuitSpec
  - [ ] SubTask 5.3: gdsfactory netlist 转换：解析 gf JSON 的 cells/connections，转 CircuitSpec
  - [ ] SubTask 5.4: picbench JSON 转换：解析 picbench 格式，转 CircuitSpec
  - [ ] SubTask 5.5: 转换后电路合法性校验（端口方向、连接闭合、画布尺寸）
  - [ ] SubTask 5.6: 输出转换报告：成功/失败数、失败根因

- [ ] Task 6: 批量测试脚本扩展（支持真实用例集）
  - [ ] SubTask 6.1: `scripts/batch_test_1000_circuits.py` 增加 `--source real/generated/all` 参数
  - [ ] SubTask 6.2: 真实用例单独索引，测试结果标记 `source=real`
  - [ ] SubTask 6.3: 测试报告分真实用例/程序化用例两组统计

- [ ] Task 7: 全量回归测试（真实 + 程序化 ≥1000）
  - [ ] SubTask 7.1: 对全部真实用例执行端到端测试
  - [ ] SubTask 7.2: 对全部程序化用例（1200）执行端到端测试（含 DRC 修复后重跑）
  - [ ] SubTask 7.3: 统计总体成功率、DRC 通过率、平均损耗、XL 耗时
  - [ ] SubTask 7.4: 验证商用门槛：成功率 ≥95%、DRC ≥90%、XL ≤5s

- [ ] Task 8: 商用版最终测试报告
  - [ ] SubTask 8.1: 生成 `docs/商用版最终测试报告.md`
  - [ ] SubTask 8.2: 总体统计 + 分拓扑 + 分规模 + 分平台 + 真实/程序化对比
  - [ ] SubTask 8.3: DRC 误报审查结论 + 布局修复效果
  - [ ] SubTask 8.4: 商用发布结论（通过/不通过 + 待优化项）

- [ ] Task 9: 代码提交与操作记录
  - [ ] SubTask 9.1: 每个小任务完成后 git add 精确文件 → commit → push origin main
  - [ ] SubTask 9.2: 追加 `操作记录.md`，含轮次编号、交付文件、测试结果、规则依据
  - [ ] SubTask 9.3: 更新 `docs/LR商用版测试报告_20260704.md` 链接最终报告

# Task Dependencies
- Task 1 可立即开始（读取已有测试结果）
- Task 2 依赖 Task 1（误报根因指导布局修复）
- Task 3 与 Task 2 可并行（文献审查独立于代码修复）
- Task 4 可立即开始（网络下载独立于 DRC 修复）
- Task 5 依赖 Task 4（转换需要下载完成的用例）
- Task 6 依赖 Task 5（测试脚本扩展需要转换器就绪）
- Task 7 依赖 Task 2/3/6（DRC 修复 + 真实用例就绪后全量回归）
- Task 8 依赖 Task 7（报告基于回归结果）
- Task 9 贯穿全程（每任务完成即提交）
