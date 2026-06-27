# Checklist

## simphony 兼容 API

- [x] `src/polaris/sim/subcircuit.py` 已创建
- [x] `Term` 类已实现（端口定义）
- [x] `Connector` 类已实现（连接器）
- [x] `Subcircuit` 类已实现（含 connect 方法）
- [x] API 与 simphony 兼容

## SiEPIC 缺失模型

- [x] `half_ring_s()` 模型已实现
- [x] `taper_s()` 模型已实现
- [x] `add_drop_ring_s()` 模型已实现（双总线）
- [x] Sellmeier 色散 neff(λ) 模型已实现
- [x] half_ring 与 simphony 对比误差 < 1e-10

## 群延迟和色散分析

- [x] `group_delay(sdict, wavelengths)` 方法已实现
- [x] `analyze_dispersion(sdict, wavelengths)` 方法已实现
- [x] 峰值检测算法已实现
- [x] Lorentzian 拟合已实现
- [x] 波导群延迟通过解析解验证（τ_g = n_g·L/c）
- [x] 环谐振器 FSR 验证通过

## SiEPIC JSON 网表解析器

- [x] `src/polaris/sim/siepic_netlist.py` 已创建
- [x] SiEPIC JSON schema 解析已实现
- [x] 自动转换为 PoLaRIS 内部网表已实现
- [x] `/workspace/data/benchmarks/siepic_netlists/` 网表解析验证通过

## add-drop 型环谐振器

- [x] add-drop 型环谐振器模型已实现
- [x] 功率守恒测试通过（through + drop = 1）

## 测试验证

- [x] test_subcircuit.py 测试通过
- [x] test_group_delay.py 测试通过
- [x] test_siepic_netlist.py 测试通过
- [x] test_models.py 扩展测试通过
- [x] 完整测试套件通过（无回归）

## 学术诚信

- [x] 所有改动基于 R02.md 改进计划路线图
- [x] 所有器件模型参数基于真实文献值
- [x] 无任何 fall-back 兜底代码
- [x] 无任何假数据

## 操作记录

- [x] `操作记录.md` 第 98 轮记录已追加
- [x] 记录包含：R02 路标实际交付过程
- [x] 记录包含：新增的 simphony 兼容 API
- [x] 记录包含：下一轮（第 99 轮）计划

## 代码提交

- [x] git commit 完成
- [x] git merge main 完成
- [x] git push origin main 完成
