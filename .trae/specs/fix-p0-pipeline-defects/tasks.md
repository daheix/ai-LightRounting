# Tasks

- [x] Task 1: P0-1 修复 `_DefaultPlacer._place_random` 布局重叠
  - [x] SubTask 1.1: 重写 `_place_random`，增加重叠检测 + 合法化 + 画布扩大重试（3 次 ×1.5）
  - [x] SubTask 1.2: 实现辅助函数 `_grid_place`/`_rects_overlap`/`_has_overlap`/`_legalize_overlaps`/`_find_nearest_free`
  - [x] SubTask 1.3: 来源注释标注 DREAMPlace TCAD 2020

- [x] Task 2: P0-2 修复 `_CurvyRouter.route` 顺序布线拥塞死锁
  - [x] SubTask 2.1: 将 `_CurvyRouter` 拆分到 `polaris.pipeline.curvy_router`（规则 7.1 文件 < 600 行）
  - [x] SubTask 2.2: 实现 rip-up and reroute 算法（最多 3 次迭代）
  - [x] SubTask 2.3: 优化障碍物半宽 grid_size*0.6 → waveguide_width/2 + min_spacing_um = 1.25μm
  - [x] SubTask 2.4: 复用同一 GridRouter 实例降低 O(n²) 复杂度
  - [x] SubTask 2.5: 将 `_DefaultSimulator` 拆分到 `polaris.pipeline.default_simulator`

- [x] Task 3: P0-3 修复 5 项 DRC 规则缺失
  - [x] SubTask 3.1: 在 `CheckContext` 添加 `canvas_w`/`canvas_h`/`pin_pairs` 字段
  - [x] SubTask 3.2: 实现 `check_enclosure`（IHP SG25H5 PDK enclosure 规则）
  - [x] SubTask 3.3: 实现 `check_notch`（KLayout DRC runset notch 规则，简化版）
  - [x] SubTask 3.4: 实现 `check_pin_match`（SiEPIC EBeam PDK 端口方向约定）
  - [x] SubTask 3.5: 在 `ConstraintChecker.check()` 调用全部 16 项 ViolationType 检查
  - [x] SubTask 3.6: 修改 `SimLoop._check_constraints` 填充 CheckContext 缺失字段（waveguide_widths/waveguide_lengths/device_areas/port_connections/canvas_w/canvas_h/pin_pairs）
  - [x] SubTask 3.7: 修复 `ViolationType.ENCLOSEMENT` 拼写错误 → `ENCLOSURE`（影响 5 个文件）

- [x] Task 4: 验证修复有效性
  - [x] SubTask 4.1: 运行 `pytest tests/test_sim_loop.py tests/test_integration.py` → 27 passed
  - [x] SubTask 4.2: 运行 DRC 测试（5 个文件）→ 127 passed
  - [x] SubTask 4.3: 运行 `scripts/mvp_100_iterations.py --iterations 5` → 成功率 100%，DRC 通过率 100%
  - [x] SubTask 4.4: 确认 `integrated.py` 文件行数 589 < 600（规则 7.1）

# Task Dependencies
- Task 3 SubTask 3.6 依赖 SubTask 3.1-3.5 完成（CheckContext 字段和检查函数就绪后才能填充）
- Task 4 依赖 Task 1-3 全部完成
