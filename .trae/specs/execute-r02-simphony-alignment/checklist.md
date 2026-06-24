# Checklist

## simphony 兼容 API

- [ ] `src/polaris/sim/subcircuit.py` 已创建
- [ ] `Term` 类已实现（端口定义）
- [ ] `Connector` 类已实现（连接器）
- [ ] `Subcircuit` 类已实现（含 connect 方法）
- [ ] API 与 simphony 兼容

## SiEPIC 缺失模型

- [ ] `half_ring_s()` 模型已实现
- [ ] `taper_s()` 模型已实现
- [ ] `add_drop_ring_s()` 模型已实现（双总线）
- [ ] Sellmeier 色散 neff(λ) 模型已实现
- [ ] half_ring 与 simphony 对比误差 < 1e-10

## 群延迟和色散分析

- [ ] `group_delay(sdict, wavelengths)` 方法已实现
- [ ] `analyze_dispersion(sdict, wavelengths)` 方法已实现
- [ ] 峰值检测算法已实现
- [ ] Lorentzian 拟合已实现
- [ ] 波导群延迟通过解析解验证（τ_g = n_g·L/c）
- [ ] 环谐振器 FSR 验证通过

## SiEPIC JSON 网表解析器

- [ ] `src/polaris/sim/siepic_netlist.py` 已创建
- [ ] SiEPIC JSON schema 解析已实现
- [ ] 自动转换为 PoLaRIS 内部网表已实现
- [ ] `/workspace/data/benchmarks/siepic_netlists/` 网表解析验证通过

## add-drop 型环谐振器

- [ ] add-drop 型环谐振器模型已实现
- [ ] 功率守恒测试通过（through + drop = 1）

## 测试验证

- [ ] test_subcircuit.py 测试通过
- [ ] test_group_delay.py 测试通过
- [ ] test_siepic_netlist.py 测试通过
- [ ] test_models.py 扩展测试通过
- [ ] 完整测试套件通过（无回归）

## 学术诚信

- [ ] 所有改动基于 R02.md 改进计划路线图
- [ ] 所有器件模型参数基于真实文献值
- [ ] 无任何 fall-back 兜底代码
- [ ] 无任何假数据

## 操作记录

- [ ] `操作记录.md` 第 98 轮记录已追加
- [ ] 记录包含：R02 路标实际交付过程
- [ ] 记录包含：新增的 simphony 兼容 API
- [ ] 记录包含：下一轮（第 99 轮）计划

## 代码提交

- [ ] git commit 完成
- [ ] git merge main 完成
- [ ] git push origin main 完成
