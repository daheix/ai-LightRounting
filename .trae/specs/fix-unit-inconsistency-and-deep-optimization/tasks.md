# Tasks

## 阶段1: P0 单位bug修复（最高优先级，并行）

- [ ] Task 1: 修复pretrain.py单位bug
  - [ ] SubTask 1.1: canvas_w默认1.0→1000.0，缺失raise KeyError
  - [ ] SubTask 1.2: 归一化1e5→1000.0（canvas_w/1000.0）
- [ ] Task 2: 修复transfer_learning.py单位bug
  - [ ] SubTask 2.1: canvas_w默认1.0→1000.0，缺失raise KeyError
  - [ ] SubTask 2.2: 归一化1e5→1000.0
- [ ] Task 3: 修复rl_pareto.py单位bug
  - [ ] SubTask 3.1: width→width_um字段读取，缺失raise KeyError
  - [ ] SubTask 3.2: _CANVAS_SIZE_UM=3200→动态读取circuit canvas_w
- [ ] Task 4: 修复rl_advanced.py单位bug
  - [ ] SubTask 4.1: 同rl_pareto修复
- [ ] Task 5: 统一波长换算
  - [ ] SubTask 5.1: 在调用simphony前添加wl_um=wl_nm/1000.0换算
  - [ ] SubTask 5.2: 在specs.py docstring标注单位制

## 阶段2: P0 42个超80行函数拆分（并行，参考split-long-functions-80-lines spec）

- [ ] Task 6: 拆分TOP10超长函数（>120L）
  - [ ] SubTask 6.1: route/__init__.py bend_compensate 259L
  - [ ] SubTask 6.2: inverse/adjoint.py run_adjoint_optimization 201L
  - [ ] SubTask 6.3: place/align.py _align_d2_global 193L
  - [ ] SubTask 6.4: eme/solver.py solve_eme 192L
  - [ ] SubTask 6.5: bpm/solver.py solve_bpm 187L
  - [ ] SubTask 6.6: fdfd/solver.py solve_fdfd 176L
  - [ ] SubTask 6.7: gds_tools multi_clip_gdsii 150L
- [ ] Task 7: 拆分100-125L函数（15个）
- [ ] Task 8: 拆分81-94L函数（16个）

## 阶段3: P1 继续下载真实用例（并行）

- [ ] Task 9: 搜索更多光子PDK数据源
  - [ ] SubTask 9.1: 搜索IMEC/AIM/AMF公开示例
  - [ ] SubTask 9.2: 搜索IEEE/Optica论文公开数据
- [ ] Task 10: 下载新数据源到real_board/
- [ ] Task 11: 从现有SiEPIC GDS提取更多expert_demos三元组

## 阶段4: P1 DRC通过率持续提升（并行）

- [ ] Task 12: 优化siepic多器件GDS的DRC
- [ ] Task 13: 优化expert_demos端口坐标精度
- [ ] Task 14: 改进矩阵拓扑端口对齐

## 阶段5: 验证与提交

- [ ] Task 15: 单位一致性验证（全部模块扫描）
- [ ] Task 16: 全量回归测试
- [ ] Task 17: 质量门禁验证（0超80行函数）
- [ ] Task 18: 操作记录更新+代码提交

# Task Dependencies
- Task 1-5 可并行（5个单位bug修复独立）
- Task 6-8 可并行（3批函数拆分独立，参考split-long-functions-80-lines spec）
- Task 9-11 可并行（3批下载独立）
- Task 12-14 可并行（3个DRC改进独立）
- Task 15 依赖Task 1-5完成
- Task 16-18 依赖Task 15完成
