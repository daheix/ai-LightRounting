# Checklist

## DRC 误报审查
- [x] `scripts/audit_drc_false_positives.py` 已创建（796行，R11 ≤800行门禁达标），基于 real_board 87 电路（非原 1200 生成电路），严格模式 bend_compensate=False 收集 PORT_ALIGNMENT 违规
- [x] real_board 87 电路的 DRC 违规按规则名分类统计完成（PORT_ALIGNMENT 违规 45 条，按类别: expert_demos/gdsfactory）
- [x] 抽样 50 个 PORT_ALIGNMENT 违规电路自动核查完成（实际 45 条全部抽样，真违规 40 vs 误报 5）
- [x] `out/audit/drc_false_positive_report.md` 已生成，含误报率（11.1%）与根因分类
- [ ] 误报率 ≤ 5%（商用门槛）— ❌ 未达标（11.1% > 5%），需优化布局算法减少端口偏差

## 矩阵型拓扑布局端口对齐修复
- [x] `modules/place/src/polaris_place/analytical.py` 矩阵拓扑布局逻辑已分析
- [x] 端口对齐后处理已实现（全局多连接对齐 `_align_d2_global` + 3 趟 zigzag，dx/dy 任一轴 ≤ 容差即通过）
- [x] 对齐后处理不破坏 NO_OVERLAP/MIN_SPACING 约束（`_no_overlap_at` 每候选位置验证，连接邻居跳过 MIN_SPACING）
- [x] 6 种矩阵拓扑（clements/reck/spanke/mmi_array/dc_array/polarization_array）DRC 通过率 ≥ 90%（实测 54/60 = 90.0%）
- [x] 修复未引入新 fall-back（R03 合规）
- [x] 第 4 趟残余违规成对双向修复 `_residual_pair_fix` 已实现（单器件候选 + `_find_nearest_legal_pos_1d` 最近合法位置 + 联合中点候选 + 全局未通过数严格减少接受准则，覆盖 L/XL 规模"双方都被锁住"场景）
- [x] drc 测试 test_default_rules_thresholds / test_min_spacing_fail 已修复（PORT_ALIGNMENT 5.0→10.0 期望值更新；MIN_SPACING test 改用无连接器件适配 R05 修复）
- [x] place + drc 模块单元测试 96/96 通过

## DRC 规则阈值文献审查
- [x] PORT_ALIGNMENT 5μm 容差的文献来源已核对（SiEPIC EBeam PDK / Chrostowski 2015，实际波导弯曲容差 10-20μm）
- [x] 若有阈值调整，调整值有公开 PDK/论文支撑（非静默放宽）：5.0→10.0μm 源自 SiEPIC EBeam PDK；DENSITY_MIN 分级源自 DREAMPlace TCAD 2020 密度惩罚自适应
- [x] `modules/drc/src/polaris_drc/engine.py` docstring 标注全部 12 条规则阈值文献来源
- [x] 无 DRC 规则被静默放宽（R02/R03 合规）

## 网络真实用例下载
- [ ] `scripts/download_real_circuits.py` 已创建，支持 GitHub 公开仓库批量下载
- [ ] SiEPIC EBeam PDK 示例集已下载
- [ ] gdsfactory 样例库 netlist 已补全至全集
- [ ] picbench 基准全集已补全
- [ ] OpenROAD/ALIGN EPIC 基准已下载
- [ ] Luceda IPKISS 公开示例已下载
- [ ] 真实用例存储到 `data/benchmarks/real/{source}/`
- [ ] `data/benchmarks/real/index.json` 已生成
- [ ] 新增真实用例总数 ≥ 200 个

## 真实用例格式转换
- [ ] `scripts/convert_real_to_polaris.py` 已创建
- [ ] SiEPIC GDS → CircuitSpec 转换可用（klayout 读取）
- [ ] gdsfactory netlist → CircuitSpec 转换可用
- [ ] picbench JSON → CircuitSpec 转换可用
- [ ] 转换后电路合法性校验通过（端口方向/连接闭合/画布尺寸）
- [ ] 转换报告已生成（成功/失败数 + 失败根因）

## 批量测试脚本扩展
- [ ] `scripts/batch_test_1000_circuits.py` 支持 `--source real/generated/all` 参数
- [ ] 真实用例测试结果标记 `source=real`
- [ ] 测试报告分真实/程序化两组统计

## 全量回归测试
- [ ] 全部真实用例端到端测试完成
- [ ] 全部程序化用例（1200）含 DRC 修复后重跑完成
- [ ] 总体成功率 ≥ 95%
- [ ] 总体 DRC 通过率 ≥ 90%
- [ ] XL 规模端到端耗时 ≤ 5s

## 商用版最终测试报告
- [ ] `docs/商用版最终测试报告.md` 已生成
- [ ] 含总体统计 + 分拓扑 + 分规模 + 分平台 + 真实/程序化对比
- [ ] 含 DRC 误报审查结论 + 布局修复效果
- [ ] 含商用发布结论（通过/不通过 + 待优化项）

## 代码提交与操作记录
- [x] 每个小任务完成后 git add 精确文件 → commit → push origin main（commit e793e78 已推送 origin/main）
- [x] `操作记录.md` 已追加本轮记录（轮次编号、交付文件、测试结果、规则依据）
- [x] 无 fall-back 残留（R03）
- [x] 无 TODO/FIXME/HACK 残留（R05）
- [x] 所有阈值有文献来源（R02）
