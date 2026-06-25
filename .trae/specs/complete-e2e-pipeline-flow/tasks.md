# Tasks

- [ ] Task 1: 修复 grid_placement 边界违规
  - [ ] SubTask 1.1: 修复 grid_placement 自适应扩大画布（当 max_w*1.1 > canvas_w/cols 时）
  - [ ] SubTask 1.2: 验证 Ariane benchmark grid_placement DRV=0
  - [ ] SubTask 1.3: 修复 test_evaluate_benchmark_passed_no_overlap 测试逻辑

- [ ] Task 2: 修复 stage3 torch 硬依赖
  - [ ] SubTask 2.1: torch 改为可选 import（try/except）
  - [ ] SubTask 2.2: 无 torch 时使用纯 numpy PPO 后端加载 JSON checkpoint
  - [ ] SubTask 2.3: 验证 test_e2e_showcase 无 torch 可运行

- [ ] Task 3: 全流程测试验证
  - [ ] SubTask 3.1: test_web_ui.py 全部通过
  - [ ] SubTask 3.2: test_tilos_benchmark.py 全部通过
  - [ ] SubTask 3.3: test_e2e_showcase.py 全部通过（无 torch 环境）

- [ ] Task 4: 提交代码合并 main 分支
  - [ ] SubTask 4.1: 提交到 dev 分支
  - [ ] SubTask 4.2: 合并到 main 并推送

# Task Dependencies
- Task 1, 2 可并行
- Task 3 依赖 Task 1, 2
- Task 4 依赖 Task 3
