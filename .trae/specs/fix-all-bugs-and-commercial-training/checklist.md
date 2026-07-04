# Checklist

## P0 Bug修复验证
- [x] Switch组件超时修复：10个含Switch电路60秒内完成
- [x] 超时返回明确错误（error不为None，含电路名+卡死阶段）
- [ ] 组合电路DRC违规数=-1问题修复：100个电路DRC返回≥0
- [ ] GDS解析器恢复：10个SiEPIC GDS文件解析成功
- [ ] GDS解析提取器件列表+连接关系转CircuitSpec

## P1 Bug修复验证
- [ ] 矩阵拓扑DRC通过率≥40%（6种拓扑）
- [ ] gdsfactory Jinja模板解析：9个Jinja yml文件解析成功
- [ ] expert_demos连接反推：10个netlist连接数>0

## 训练管道验证
- [ ] scripts/train_polaris.py独立可运行
- [ ] 加载real_board/448真实用例作为训练集
- [ ] 加载组合电路作为增强训练集
- [ ] 训练PPO布局模型保存checkpoint
- [ ] 训练GNN布线模型保存checkpoint
- [ ] 训练循环每100步汇报loss/reward/DRC通过率
- [ ] 训练日志保存到out/training/

## 36路标验证
- [ ] R1-R36逐项核查未达标项已标记
- [ ] 综合得分7.88→8.5差距分析完成
- [ ] 遗漏功能已补齐（如有）

## 商用达标验证
- [ ] 可测试真实用例成功率≥80%
- [ ] 组合电路DRC通过率≥40%
- [ ] 训练模型测试集DRC通过率≥60%
- [ ] 修复前后对比数据已统计

## 规则合规验证
- [ ] R03无fall-back：无except:pass/return None/return []假数据
- [ ] R02学术诚信：所有修复有文献溯源
- [ ] R05无TODO/FIXME/HACK残留
- [ ] R04不参与GPU：纯NumPy/SciPy
- [ ] R11 V8极简：main分支提交
- [ ] R07操作记录已更新
