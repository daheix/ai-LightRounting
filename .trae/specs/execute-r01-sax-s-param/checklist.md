# Checklist

## fall-back 修复

- [x] cascade.py 第 106 行 `np.where(..., 1e-15, ...)` fall-back 已删除
- [x] cascade.py 第 287 行 `except Exception: pass` 已删除
- [x] 改为基于条件数的自动后端切换
- [x] 改为 raise RuntimeError 告警退出
- [x] 无任何 fall-back 兜底代码

## SDict jax.numpy 支持

- [x] types.py SDict 内部数据使用 jax.numpy
- [x] SDict 支持 `jax.grad` 自动微分
- [x] 保留 numpy 后端兼容（双后端）

## 双后端自动切换

- [x] 实现条件数监控函数 `compute_condition_number(S)`
- [x] 实现自动后端切换逻辑（κ < 1e6 用 numpy，κ ≥ 1e6 用 jax）
- [x] 添加数值稳定性诊断报告

## 模型参数 schema 验证

- [x] 定义器件模型参数 schema
- [x] 实现参数验证函数
- [x] 非法参数 raise ValueError 告警退出

## 网表格式自动适配器

- [x] 实现 sax 网表解析器
- [x] 实现 simphony 网表解析器
- [x] 实现 PoLaRIS 内部网表格式
- [x] 实现自动格式检测与转换

## 器件模型库扩展

- [x] waveguide 模型已添加
- [x] coupler 模型已添加
- [x] mzi 模型已添加
- [x] ring 模型已添加
- [x] grating_coupler 模型已添加
- [x] taper 模型已添加
- [x] crossing 模型已添加
- [x] splitter 模型已添加
- [x] combiner 模型已添加
- [x] phase_shifter 模型已添加
- [x] modulator 模型已添加
- [x] detector 模型已添加
- [x] 器件模型总数 ≥ 20

## 测试验证

- [x] test_cascade.py 测试通过（fall-back 已删除、条件数切换）
- [x] test_models.py 测试通过（20+ 器件模型）
- [x] test_types.py 测试通过（SDict jax.numpy 支持）
- [x] test_netlist_adapter.py 测试通过（网表格式适配）
- [x] 完整测试套件通过（无回归）

## 学术诚信

- [x] 所有改动基于 R01.md 改进计划路线图
- [x] 所有器件模型参数基于真实文献值
- [x] 无任何 fall-back 兜底代码
- [x] 无任何假数据

## 操作记录

- [x] `操作记录.md` 第 97 轮记录已追加
- [x] 记录包含：R01 路标实际交付过程
- [x] 记录包含：修复的 fall-back 问题
- [x] 记录包含：新增的器件模型
- [x] 记录包含：下一轮（第 98 轮）计划

## 代码提交

- [x] git commit 完成
- [ ] git merge main 完成
- [ ] git push origin main 完成
