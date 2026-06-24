# Checklist

## 流程诚信审查

- [ ] `src/polaris/` 全量扫描 fall-back / mock / fake / dummy / hardcode 模式完成
- [ ] 扫描结果分类为「真 fall-back」「合法异常处理」「测试桩」三类
- [ ] 所有真 fall-back 已修复（改为 `raise` 或显式处理 + 日志告警）
- [ ] `out/audit/pipeline_integrity_report.md` 已生成
- [ ] 物理参数来源审查完成，每个参数标注 PDK / 论文 URL
- [ ] 网络交叉验证参数在公开文献报告区间内
- [ ] `out/audit/parameter_provenance.md` 已生成
- [ ] 无来源或来源不符的参数已修复
- [ ] 计算公式核对完成，与原始文献一致
- [ ] `out/audit/formula_provenance.md` 已生成
- [ ] 与文献不一致的公式已修复
- [ ] 布局算法设计缺陷审查完成（重叠、异构尺寸）
- [ ] 布线算法设计缺陷审查完成（拥塞死锁、障碍物累积）
- [ ] 仿真模块查表数据真实性审查完成（非假数据）
- [ ] DRC 检查器 16 项规则完整性审查完成（无静默跳过）
- [ ] GDS 导出可被 KLayout 重新加载验证
- [ ] `out/audit/design_flaws.md` 已生成

## 1000 电路测试集

- [ ] 电路生成器框架 `scripts/generate_1000_circuits.py` 已实现
- [ ] `CircuitGenerator` 基类与统一接口已实现
- [ ] 电路序列化器输出 JSON 到 `data/benchmarks/generated/`
- [ ] 电路合法性校验通过（端口方向、连接闭合、画布尺寸、参数完整性）
- [ ] 电路索引清单 `data/benchmarks/generated/index.json` 已生成
- [ ] MZI 阵列生成器实现完成
- [ ] Ring 滤波器组生成器实现完成
- [ ] Clements 矩阵生成器实现完成
- [ ] Reck 三角矩阵生成器实现完成
- [ ] Spanke 矩阵生成器实现完成
- [ ] MMI 阵列生成器实现完成
- [ ] DC 阵列生成器实现完成
- [ ] WDM MUX/DEMUX 生成器实现完成
- [ ] 光开关矩阵生成器实现完成
- [ ] 调制器阵列生成器实现完成
- [ ] 量子光路生成器实现完成
- [ ] 格栅滤波器生成器实现完成
- [ ] 微环延迟线生成器实现完成
- [ ] 偏振分束阵列生成器实现完成
- [ ] 混合拓扑生成器实现完成
- [ ] 拓扑种类 ≥ 15 种
- [ ] XS 规模（4-16 器件）电路生成完成
- [ ] S 规模（16-64 器件）电路生成完成
- [ ] M 规模（64-128 器件）电路生成完成
- [ ] L 规模（128-256 器件）电路生成完成
- [ ] XL 规模（256-500 器件）电路生成完成
- [ ] SOI 平台电路生成完成
- [ ] SiN 平台电路生成完成
- [ ] InP 平台电路生成完成
- [ ] LNOI 平台电路生成完成
- [ ] SiEPIC EBeam PDK 变种电路生成完成
- [ ] gdsfactory picbench 变种电路生成完成
- [ ] LiDAR ISPD'25 benchmark 变种电路生成完成
- [ ] OpenROAD EPIC 变种电路生成完成
- [ ] Luceda IPKISS 变种电路生成完成
- [ ] Synopsys OptoDesigner 变种电路生成完成
- [ ] 电路总数 ≥ 1000 个

## 批量测试与报告

- [ ] 批量测试脚本 `scripts/batch_test_1000_circuits.py` 已实现
- [ ] 端到端流水线对每个电路执行完成
- [ ] 并行执行（multiprocessing）已实现
- [ ] 断点续跑支持已实现
- [ ] 测试报告 `scripts/generate_test_report.py` 已实现
- [ ] 总体统计（成功率、DRC 通过率、平均损耗、平均耗时、P50/P95/P99）已生成
- [ ] 分拓扑统计表已生成
- [ ] 分规模统计表已生成
- [ ] 分平台统计表已生成
- [ ] 失败电路清单与根因分类已生成
- [ ] `out/batch_test/report.md` 已生成
- [ ] `out/batch_test/stats.json` 已生成

## 失败修复与回归

- [ ] 失败电路根因分析完成
- [ ] 布局算法问题已修复
- [ ] 布线算法问题已修复
- [ ] DRC 检查问题已修复
- [ ] 仿真问题已修复
- [ ] GDS 导出问题已修复
- [ ] 修复后重跑成功率 ≥ 95%
- [ ] 修复后重跑 DRC 通过率 ≥ 90%
- [ ] 电路生成器单元测试 `tests/test_circuit_generators.py` 通过
- [ ] 批量测试冒烟测试 `tests/test_batch_test.py` 通过
- [ ] 引擎修复回归测试通过
- [ ] ruff check 通过
- [ ] 全量回归测试通过

## 文档与提交

- [ ] `操作记录.md` 已更新本次审查与优化全过程
- [ ] `docs/academic_integrity_audit.md` 已追加本次审查结果
- [ ] `README.md` 已补充 1000 电路测试集使用说明
- [ ] 代码已提交到开发分支
- [ ] 已合并 main 分支
- [ ] 已推送远端
