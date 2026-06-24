# Tasks

## 阶段一：分析现有代码与差距

- [x] Task 1: 分析 PoLaRIS 现有仿真代码与 sax 的差距
  - [x] SubTask 1.1: Read `src/polaris/sim/cascade.py` 确认 fall-back 兜底位置
  - [x] SubTask 1.2: Read `src/polaris/sim/types.py` 确认 SDict 实现
  - [x] SubTask 1.3: Read `src/polaris/sim/models.py` 确认器件模型数量
  - [x] SubTask 1.4: Read `src/polaris/sim/simulator.py` 确认 JIT/GPU 支持
  - [x] SubTask 1.5: WebSearch sax GitHub README 确认器件模型清单

## 阶段二：修复 fall-back 与数值稳定性

- [x] Task 2: 修复 cascade.py fall-back 兜底
  - [x] SubTask 2.1: 删除第 106 行 `np.where(..., 1e-15, ...)` fall-back
  - [x] SubTask 2.2: 实现基于条件数的自动后端切换
  - [x] SubTask 2.3: 删除第 287 行 `except Exception: pass` 静默异常
  - [x] SubTask 2.4: 改为 raise RuntimeError 告警退出

## 阶段三：SDict 切换到 jax.numpy

- [x] Task 3: 将 SDict 切换到 jax.numpy
  - [x] SubTask 3.1: 修改 `src/polaris/sim/types.py` SDict 内部数据为 jax.numpy
  - [x] SubTask 3.2: 确保 SDict 支持 `jax.grad` 自动微分
  - [x] SubTask 3.3: 保留 numpy 后端兼容（双后端）

## 阶段四：实现双后端自动切换

- [x] Task 4: 实现双后端自动切换
  - [x] SubTask 4.1: 实现条件数监控函数 `compute_condition_number(S)`
  - [x] SubTask 4.2: 实现自动后端切换逻辑（κ < 1e6 用 numpy，κ ≥ 1e6 用 jax）
  - [x] SubTask 4.3: 添加数值稳定性诊断报告

## 阶段五：实现模型参数 schema 验证

- [x] Task 5: 实现模型参数 schema 验证
  - [x] SubTask 5.1: 定义器件模型参数 schema（使用 dataclass 或 pydantic）
  - [x] SubTask 5.2: 实现参数验证函数（检查负数宽度、非法波长等）
  - [x] SubTask 5.3: 非法参数 raise ValueError 告警退出

## 阶段六：实现网表格式自动适配器

- [x] Task 6: 实现网表格式自动适配器
  - [x] SubTask 6.1: 实现 sax 网表解析器
  - [x] SubTask 6.2: 实现 simphony 网表解析器
  - [x] SubTask 6.3: 实现 PoLaRIS 内部网表格式
  - [x] SubTask 6.4: 实现自动格式检测与转换

## 阶段七：扩展器件模型库

- [x] Task 7: 扩展器件模型库到 20+
  - [x] SubTask 7.1: 添加 waveguide 模型（含损耗、色散）
  - [x] SubTask 7.2: 添加 coupler 模型（方向耦合器）
  - [x] SubTask 7.3: 添加 mzi 模型（马赫-曾德干涉仪）
  - [x] SubTask 7.4: 添加 ring 模型（微环谐振器）
  - [x] SubTask 7.5: 添加 grating_coupler 模型（光栅耦合器）
  - [x] SubTask 7.6: 添加 taper 模型（锥形转换器）
  - [x] SubTask 7.7: 添加 crossing 模型（波导交叉）
  - [x] SubTask 7.8: 添加 splitter 模型（Y 分支）
  - [x] SubTask 7.9: 添加 combiner 模型（合波器）
  - [x] SubTask 7.10: 添加 phase_shifter 模型（相移器）
  - [x] SubTask 7.11: 添加 modulator 模型（调制器）
  - [x] SubTask 7.12: 添加 detector 模型（探测器）

## 阶段八：添加测试

- [x] Task 8: 添加测试验证所有改动
  - [x] SubTask 8.1: 添加 test_cascade.py 测试（fall-back 已删除、条件数切换）
  - [x] SubTask 8.2: 添加 test_models.py 测试（20+ 器件模型）
  - [x] SubTask 8.3: 添加 test_types.py 测试（SDict jax.numpy 支持）
  - [x] SubTask 8.4: 添加 test_netlist_adapter.py 测试（网表格式适配）
  - [x] SubTask 8.5: 运行完整测试套件验证

## 阶段九：操作记录与提交

- [x] Task 9: 追加操作记录第 97 轮
  - [x] SubTask 9.1: 记录 R01 路标实际交付过程
  - [x] SubTask 9.2: 记录修复的 fall-back 问题
  - [x] SubTask 9.3: 记录新增的器件模型
  - [x] SubTask 9.4: 记录下一轮（第 98 轮）计划

- [x] Task 10: 提交代码并合并到 main 分支
  - [x] SubTask 10.1: git add 相关文件
  - [x] SubTask 10.2: git commit
  - [x] SubTask 10.3: git checkout main && git merge
  - [x] SubTask 10.4: git push origin main

# Task Dependencies

- Task 2-7 依赖 Task 1（需先分析现有代码）
- Task 8 依赖 Task 2-7（需完成所有改动才能测试）
- Task 9 依赖 Task 8（需测试通过才能记录）
- Task 10 依赖 Task 9（需记录完成才能提交）

# 并行执行策略

- Task 2/3/4/5/6 可部分并行（修改不同文件）
- Task 7 依赖 Task 5（需 schema 验证才能添加模型）
- Task 8 依赖所有改动完成
