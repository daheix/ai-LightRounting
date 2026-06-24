# Tasks

- [ ] Task 1: 流程诚信审查 - fall-back / mock / fake / dummy / hardcode 全量扫描
  - [ ] SubTask 1.1: 编写 `scripts/audit_pipeline_integrity.py`，grep 扫描 `src/polaris/` 中 `except: pass`、`except.*return None`、`except.*return \[\]`、`mock`、`fake`、`dummy`、`hardcode`、`TODO.*fallback`、`# 临时` 等模式
  - [ ] SubTask 1.2: 人工复核扫描结果，分类为「真 fall-back」「合法异常处理」「测试桩」三类
  - [ ] SubTask 1.3: 输出 `out/audit/pipeline_integrity_report.md`，列出所有问题项与文件位置
  - [ ] SubTask 1.4: 修复所有真 fall-back（改为 `raise` 或显式处理 + 日志告警）

- [ ] Task 2: 物理参数来源审查
  - [ ] SubTask 2.1: 提取 `src/polaris/` 全部固定物理常数与器件参数（弯曲半径、波导宽度、损耗系数、折射率、耦合系数等）
  - [ ] SubTask 2.2: 逐条核对参数是否标注 PDK / 论文 URL 来源
  - [ ] SubTask 2.3: 网络交叉验证参数是否在公开文献报告区间内（SiEPIC EBeam PDK / Ligentec / HyperLight / 文献）
  - [ ] SubTask 2.4: 输出 `out/audit/parameter_provenance.md`，列出参数值、来源、URL、验证结论
  - [ ] SubTask 2.5: 修复无来源或来源不符的参数（补充来源或标记为问题项）

- [ ] Task 3: 计算公式推导来源核对
  - [ ] SubTask 3.1: 提取全部模块中的核心计算公式（弯曲半径、插入损耗、耦合系数、S 参数、BER、HOM 干涉、酉矩阵等约 30+ 条）
  - [ ] SubTask 3.2: 逐条核对公式与原始文献的一致性（公式形式、系数、量纲）
  - [ ] SubTask 3.3: 输出 `out/audit/formula_provenance.md`，列出公式内容、推导来源、一致性结论
  - [ ] SubTask 3.4: 修复与文献不一致的公式实现

- [ ] Task 4: 流程设计缺陷审查
  - [ ] SubTask 4.1: 审查布局算法（`_DefaultPlacer`）：网格布局是否产生重叠、是否考虑器件尺寸异构性
  - [ ] SubTask 4.2: 审查布线算法（`_CurvyRouter`）：顺序布线 + 障碍物累积是否在大规模电路上产生拥塞死锁
  - [ ] SubTask 4.3: 审查仿真模块：`use_real_simulator=False` 时查表数据是否真实（非假数据）
  - [ ] SubTask 4.4: 审查 DRC 检查器：16 项规则是否覆盖完整、是否有规则被静默跳过
  - [ ] SubTask 4.5: 审查 GDS 导出：导出的 GDS 是否能被 KLayout 重新加载验证
  - [ ] SubTask 4.6: 输出 `out/audit/design_flaws.md`，列出设计缺陷与修复建议

- [ ] Task 5: 1000 电路生成器框架
  - [ ] SubTask 5.1: 创建 `scripts/generate_1000_circuits.py` 主入口，参数化生成器（拓扑、规模、平台、种子）
  - [ ] SubTask 5.2: 实现电路生成器基类 `CircuitGenerator`，统一接口 `generate() -> CircuitSpec`
  - [ ] SubTask 5.3: 实现电路序列化器，输出 JSON 到 `data/benchmarks/generated/{topology}/{scale}/{platform}/`
  - [ ] SubTask 5.4: 实现电路合法性校验（端口方向、连接闭合、画布尺寸、参数完整性）
  - [ ] SubTask 5.5: 生成电路索引清单 `data/benchmarks/generated/index.json`

- [ ] Task 6: 电路生成 - 拓扑变种（≥ 15 种）
  - [ ] SubTask 6.1: MZI 阵列生成器（1x1 / 2x2 / 4x4 / 8x8 / 16x16 阵列，平衡/非平衡臂长）
  - [ ] SubTask 6.2: Ring 滤波器组生成器（单环 / 双环耦合 / 三环耦合 / 阵列 8/16/32 通道）
  - [ ] SubTask 6.3: Clements 矩阵生成器（4x4 / 8x8 / 16x16 / 32x32 酉矩阵分解）
  - [ ] SubTask 6.4: Reck 三角矩阵生成器（4x4 / 8x8 / 16x16）
  - [ ] SubTask 6.5: Spanke 矩阵生成器（4x4 / 8x8 / 16x16）
  - [ ] SubTask 6.6: MMI 阵列生成器（1x2 / 2x2 / 1x4 / 4x4 级联）
  - [ ] SubTask 6.7: 定向耦合器（DC）阵列生成器（2/4/8/16 通道）
  - [ ] SubTask 6.8: WDM MUX/DEMUX 生成器（4/8/16/32 通道 AWG）
  - [ ] SubTask 6.9: 光开关矩阵生成器（2x2 / 4x4 / 8x8 Benes 网络）
  - [ ] SubTask 6.10: 调制器阵列生成器（Mach-Zehnder 调制器 4/8/16 通道）
  - [ ] SubTask 6.11: 量子光路生成器（KLM CNOT / HOM 干涉 / 玻色采样 4/8/16 模）
  - [ ] SubTask 6.12: 格栅滤波器生成器（FIR/IIR 拓扑）
  - [ ] SubTask 6.13: 微环谐振器延迟线生成器（CROW / SCISSOR 拓扑）
  - [ ] SubTask 6.14: 偏振分束/合束阵列生成器
  - [ ] SubTask 6.15: 混合拓扑生成器（MZI + Ring + DC 组合，模拟真实 OEIC）

- [ ] Task 7: 电路生成 - 规模梯度（4-500 器件，5 档）
  - [ ] SubTask 7.1: XS 规模（4-16 器件，画布 200×200μm）每种拓扑 5 个变种
  - [ ] SubTask 7.2: S 规模（16-64 器件，画布 500×500μm）每种拓扑 5 个变种
  - [ ] SubTask 7.3: M 规模（64-128 器件，画布 1000×1000μm）每种拓扑 5 个变种
  - [ ] SubTask 7.4: L 规模（128-256 器件，画布 2000×2000μm）每种拓扑 3 个变种
  - [ ] SubTask 7.5: XL 规模（256-500 器件，画布 5000×5000μm）每种拓扑 2 个变种

- [ ] Task 8: 电路生成 - 工艺平台变种（SOI / SiN / InP / LNOI）
  - [ ] SubTask 8.1: SOI 平台参数集（SiEPIC EBeam：R_min=5μm, w=0.5μm, λ=1550nm）
  - [ ] SubTask 8.2: SiN 平台参数集（Ligentec：R_min=100μm, w=1.0μm, λ=1550nm）
  - [ ] SubTask 8.3: InP 平台参数集（R_min=200μm, w=2.0μm, λ=1550nm）
  - [ ] SubTask 8.4: LNOI 平台参数集（HyperLight：R_min=50μm, w=1.5μm, λ=1550nm）
  - [ ] SubTask 8.5: 每种拓扑 × 每种规模 × 每种平台组合生成（控制总数 ≥ 1000）

- [ ] Task 9: 电路生成 - 借鉴变种设计
  - [ ] SubTask 9.1: 借鉴 SiEPIC EBeam PDK 示例电路（MZI、Ring、DC）变种
  - [ ] SubTask 9.2: 借鉴 gdsfactory picbench 基准电路变种
  - [ ] SubTask 9.3: 借鉴 LiDAR ISPD'25 benchmark 电路变种
  - [ ] SubTask 9.4: 借鉴 OpenROAD EPIC 基准电路变种
  - [ ] SubTask 9.5: 借鉴 Luceda IPKISS 示例电路变种
  - [ ] SubTask 9.6: 借鉴 Synopsys OptoDesigner 示例电路变种

- [ ] Task 10: 批量端到端测试脚本
  - [ ] SubTask 10.1: 创建 `scripts/batch_test_1000_circuits.py`，遍历 `data/benchmarks/generated/` 全部电路
  - [ ] SubTask 10.2: 对每个电路执行端到端流水线（布局→布线→仿真→DRC→GDS）
  - [ ] SubTask 10.3: 收集每个电路的 success / drc_passed / total_loss_db / n_crossings / elapsed_s
  - [ ] SubTask 10.4: 支持并行执行（multiprocessing，CPU 核数自适应）
  - [ ] SubTask 10.5: 支持断点续跑（已完成电路跳过，记录到 `out/batch_test/progress.json`）

- [ ] Task 11: 测试报告生成
  - [ ] SubTask 11.1: 创建 `scripts/generate_test_report.py`，读取批量测试结果
  - [ ] SubTask 11.2: 生成总体统计（成功率、DRC 通过率、平均损耗、平均耗时、P50/P95/P99）
  - [ ] SubTask 11.3: 生成分拓扑统计表（每种拓扑的成功率 / DRC 通过率 / 平均损耗）
  - [ ] SubTask 11.4: 生成分规模统计表（XS/S/M/L/XL 各档位的成功率 / DRC 通过率）
  - [ ] SubTask 11.5: 生成分平台统计表（SOI/SiN/InP/LNOI 各平台的成功率 / DRC 通过率）
  - [ ] SubTask 11.6: 生成失败电路清单与根因分类（布局失败 / 布线失败 / DRC 失败 / 仿真失败 / GDS 失败）
  - [ ] SubTask 11.7: 输出 `out/batch_test/report.md` + `out/batch_test/stats.json`

- [ ] Task 12: 失败电路根因分析与引擎修复
  - [ ] SubTask 12.1: 对每类失败电路抽样 5-10 个，定位根因
  - [ ] SubTask 12.2: 修复布局算法问题（如大规模电路重叠、器件尺寸异构导致网格失效）
  - [ ] SubTask 12.3: 修复布线算法问题（如大规模电路拥塞死锁、障碍物累积导致不可达）
  - [ ] SubTask 12.4: 修复 DRC 检查问题（如规则误报、规则漏报）
  - [ ] SubTask 12.5: 修复仿真问题（如查表数据缺失、参数解析失败）
  - [ ] SubTask 12.6: 修复 GDS 导出问题（如层次缺失、单元引用错误）
  - [ ] SubTask 12.7: 重跑失败电路，验证修复后成功率 ≥ 95%、DRC 通过率 ≥ 90%

- [ ] Task 13: 测试用例与回归
  - [ ] SubTask 13.1: 为电路生成器编写单元测试 `tests/test_circuit_generators.py`，验证每种拓扑生成合法
  - [ ] SubTask 13.2: 为批量测试脚本编写冒烟测试 `tests/test_batch_test.py`，验证 10 个电路可跑通
  - [ ] SubTask 13.3: 为修复的引擎问题编写回归测试，防止问题复发
  - [ ] SubTask 13.4: ruff check + 全量回归测试通过

- [ ] Task 14: 文档同步与操作记录
  - [ ] SubTask 14.1: 更新 `操作记录.md`，记录本次审查与优化全过程
  - [ ] SubTask 14.2: 更新 `docs/academic_integrity_audit.md`，追加本次审查结果
  - [ ] SubTask 14.3: 更新 `README.md`，补充 1000 电路测试集使用说明
  - [ ] SubTask 14.4: 提交代码到开发分支，合并 main 分支，推送远端

# Task Dependencies

- Task 1-4 可并行执行（流程诚信审查四方向）
- Task 5 依赖 Task 1-4 完成（修复后再扩展电路，避免在坏流程上扩展）
- Task 6-9 可并行执行（电路生成四方向，依赖 Task 5 框架）
- Task 10 依赖 Task 5-9 完成（需要 1000 电路生成完毕）
- Task 11 依赖 Task 10 完成（需要批量测试结果）
- Task 12 依赖 Task 11 完成（需要失败分析报告）
- Task 13 依赖 Task 5-12 完成（全量回归）
- Task 14 依赖 Task 1-13 完成（最终文档同步）
