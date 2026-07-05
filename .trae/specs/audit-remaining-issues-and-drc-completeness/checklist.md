# 遗留问题审计+DRC光电子完整性 Checklist

## 阶段1: 光电子DRC规则完整性审计

- [ ] SiEPIC EBeam PDK完整DRC规则集已检索
- [ ] AIM Photonics PDK DRC规则已检索
- [ ] IMEC iSiPP50G PDK DRC规则已检索
- [ ] AMF PDK DRC规则已检索
- [ ] KLayout generic DRC scripts已检索
- [ ] `docs/drc_rules_audit.md` 已生成（含12条当前规则 vs 行业PDK对照表）
- [ ] 缺失规则优先级已标注
- [ ] 每条规则文献来源已标注（R02学术诚信）

## 阶段2: 剩余失败用例根因分析

- [ ] gdsfactory 2/37失败用例根因已分析
- [ ] gdsfactory真实bug已修复
- [ ] gdsfactory数据错误已标记为known_limitation
- [ ] expert_demos 4/19失败用例根因已分析
- [ ] expert_demos真实bug已修复
- [ ] expert_demos数据错误已标记为known_limitation

## 阶段3: DRC误报率量化

- [ ] `scripts/audit_drc_false_positives.py` 已创建/完善
- [ ] 50个PORT_ALIGNMENT违规用例已抽样
- [ ] 人工核查完成（真违规 vs 误报）
- [ ] `out/audit/drc_false_positive_report.md` 已生成
- [ ] 误报率≤5%（商用门槛）

## 阶段4: 100%准确度必要性评估

- [ ] "DRC clean tape-out requirement"行业惯例已检索
- [ ] Mohan DATE 2023 ML for DRC误报率标准已检索
- [ ] AI训练数据噪声容忍度（Bengio ICML 2009）已检索
- [ ] 3类场景（tape-out/研发/AI训练）建议已给出
- [ ] PoLaRIS定位明确（研发+AI训练，95%+商用门槛）

## 阶段5: 补齐缺失DRC规则

- [ ] BEND_RADIUS_MIN规则已实现（SiEPIC EBeam PDK标准）
- [ ] WAVEGUIDE_TAPER_ANGLE规则已实现
- [ ] 其他高优先级规则已实现
- [ ] 每条新规则至少3个单元测试（pass/fail/edge case）
- [ ] 新规则全量pytest通过

## 阶段6: 商用版DRC完整性报告

- [ ] `docs/drc_completeness_audit_report.md` 已生成
- [ ] 含规则对照表
- [ ] 含通过率分拓扑/分规模/分平台统计
- [ ] 含误报率量化结果
- [ ] 含100%准确度必要性结论
- [ ] 含商用发布建议（通过/不通过 + 待优化项）
- [ ] 操作记录.md已追加本轮记录

## 阶段7: 验证与提交

- [ ] `python -m pytest modules/drc/tests/ -x --timeout=60` 全绿
- [ ] `python scripts/run_real_board_drc.py` 全量DRC通过率≥95%
- [ ] 0超80行函数（AST扫描）
- [ ] 0 except:pass / 0 TODO/FIXME/HACK
- [ ] 所有缺失字段raise（R03禁止fall-back）
- [ ] 所有阈值有文献来源（R02学术诚信）
- [ ] 代码已提交到main分支并push
