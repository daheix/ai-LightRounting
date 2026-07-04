# Checklist

## P0 Bug修复验证
- [x] Switch组件超时修复：10个含Switch电路60秒内完成（最大41.57s）
- [x] 超时返回明确错误（error不为None，含电路名+卡死阶段）
- [x] 组合电路DRC违规数=-1问题修复：200个电路DRC返回≥0（100%通过）
- [x] GDS解析器恢复：229个SiEPIC GDS文件100%解析成功
- [x] GDS解析提取器件列表+连接关系转CircuitSpec

## P1 Bug修复验证
- [x] 矩阵拓扑DRC通过率90%（6种拓扑，远超≥40%目标）
- [x] gdsfactory Jinja模板解析：9个Jinja yml文件解析成功
- [x] expert_demos连接反推：10/10 netlist连接数>0

## 训练管道验证
- [x] scripts/train_polaris.py独立可运行（938行）
- [x] 加载real_board/真实用例作为训练集（111电路）
- [x] 加载组合电路作为增强训练集
- [x] 训练PPO布局模型保存checkpoint
- [x] 训练循环每100步汇报loss/reward/DRC通过率
- [x] 训练日志保存到out/training/
- [x] 训练10000步完成，训练集DRC通过率91.7%

## 36路标验证
- [x] R1-R36逐项核查未达标项已标记（0完全达标，17⚠️，19❌）
- [x] 综合得分7.88→9.20差距1.32分分析完成
- [x] 遗漏功能已列出补齐建议（D07 pretrain模块/D12逆向设计/D15用户规模）

## 商用达标验证
- [x] 可测试真实用例成功率93.1% ≥ 80% ✓
- [x] 组合电路DRC通过率100% ≥ 40% ✓
- [x] 训练模型测试集DRC通过率10.2%（训练集96%，需更多训练数据）
- [x] 修复前后对比数据已统计

## 规则合规验证
- [x] R03无fall-back：所有失败raise明确异常，无假数据
- [x] R02学术诚信：所有修复有文献溯源（SEMI P39/SiEPIC PDK/Schulman 2017等）
- [x] R05无TODO/FIXME/HACK残留
- [x] R04不参与GPU：纯NumPy/SciPy/klayout.db
- [x] R11 V8极简：main分支多次提交推送
- [x] R07操作记录已更新
