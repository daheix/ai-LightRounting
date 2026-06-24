# Tasks

## 阶段一：分析现有代码与差距

- [ ] Task 1: 分析 PoLaRIS 现有仿真代码与 simphony 的差距
  - [ ] SubTask 1.1: Read `src/polaris/sim/simulator.py` 确认 CircuitSimulator 实现
  - [ ] SubTask 1.2: Read `src/polaris/sim/models.py` 确认现有模型清单
  - [ ] SubTask 1.3: Read `src/polaris/sim/cascade.py` 确认子网络增长算法
  - [ ] SubTask 1.4: Read `src/polaris/sim/__init__.py` 确认导出
  - [ ] SubTask 1.5: WebSearch simphony GitHub 确认 SiEPIC 模型清单

## 阶段二：实现 simphony 兼容 API

- [ ] Task 2: 实现 simphony 兼容 API
  - [ ] SubTask 2.1: 创建 `src/polaris/sim/subcircuit.py`
  - [ ] SubTask 2.2: 实现 `Term` 类（端口定义）
  - [ ] SubTask 2.3: 实现 `Connector` 类（连接器）
  - [ ] SubTask 2.4: 实现 `Subcircuit` 类（子电路，含 connect 方法）

## 阶段三：新增 SiEPIC 缺失模型

- [ ] Task 3: 新增 SiEPIC 缺失模型
  - [ ] SubTask 3.1: 实现 `half_ring_s()` 模型（对齐 simphony siepic.half_ring）
  - [ ] SubTask 3.2: 实现 `taper_s()` 模型（对齐 simphony siepic.taper）
  - [ ] SubTask 3.3: 实现 add-drop 型环谐振器 `add_drop_ring_s()`（双总线）
  - [ ] SubTask 3.4: 实现 Sellmeier 色散 neff(λ) 模型

## 阶段四：实现群延迟和色散分析

- [ ] Task 4: 实现群延迟和色散分析
  - [ ] SubTask 4.1: 实现 `group_delay(sdict, wavelengths)` 方法
  - [ ] SubTask 4.2: 实现 `analyze_dispersion(sdict, wavelengths)` 方法（FSR、Q、ER、BW_3dB）
  - [ ] SubTask 4.3: 添加峰值检测和 Lorentzian 拟合

## 阶段五：实现 SiEPIC JSON 网表解析器

- [ ] Task 5: 实现 SiEPIC JSON 网表解析器
  - [ ] SubTask 5.1: 创建 `src/polaris/sim/siepic_netlist.py`
  - [ ] SubTask 5.2: 实现 SiEPIC JSON schema 解析
  - [ ] SubTask 5.3: 实现自动转换为 PoLaRIS 内部网表
  - [ ] SubTask 5.4: 验证 `/workspace/data/benchmarks/siepic_netlists/` 网表解析

## 阶段六：添加测试

- [ ] Task 6: 添加测试验证所有改动
  - [ ] SubTask 6.1: 添加 `tests/test_subcircuit.py`（simphony 兼容 API 测试）
  - [ ] SubTask 6.2: 添加 `tests/test_group_delay.py`（群延迟和色散分析测试）
  - [ ] SubTask 6.3: 添加 `tests/test_siepic_netlist.py`（SiEPIC 网表解析测试）
  - [ ] SubTask 6.4: 添加 `tests/test_models.py` 扩展（half_ring/taper/add_drop_ring 测试）
  - [ ] SubTask 6.5: 运行完整测试套件验证

## 阶段七：操作记录与提交

- [ ] Task 7: 追加操作记录第 98 轮
  - [ ] SubTask 7.1: 记录 R02 路标实际交付过程
  - [ ] SubTask 7.2: 记录新增的 simphony 兼容 API
  - [ ] SubTask 7.3: 记录新增的 SiEPIC 模型
  - [ ] SubTask 7.4: 记录下一轮（第 99 轮）计划

- [ ] Task 8: 提交代码并合并到 main 分支
  - [ ] SubTask 8.1: git add 相关文件
  - [ ] SubTask 8.2: git commit
  - [ ] SubTask 8.3: git checkout main && git merge
  - [ ] SubTask 8.4: git push origin main

# Task Dependencies

- Task 2-5 依赖 Task 1（需先分析现有代码）
- Task 6 依赖 Task 2-5（需完成所有改动才能测试）
- Task 7 依赖 Task 6（需测试通过才能记录）
- Task 8 依赖 Task 7（需记录完成才能提交）

# 并行执行策略

- Task 2/3/4/5 可部分并行（修改不同文件）
- Task 6 依赖所有改动完成
