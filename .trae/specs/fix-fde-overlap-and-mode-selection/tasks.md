# Tasks

- [x] Task 1: 修复 `Mode.overlap` 因子 4 bug（添加 0.5 因子）
  - [x] SubTask 1.1: 读取 `src/polaris/sim/fde/mode.py` 的 `overlap` 方法
  - [x] SubTask 1.2: 修改 `cross = np.sum(...)` 为 `cross = 0.5 * np.sum(...)`
  - [x] SubTask 1.3: 更新方法 docstring 注明 0.5 因子来源（坡印廷矢量时间平均）
  - [x] SubTask 1.4: 验证修改后自重叠 = 1.0（数学推导）

- [x] Task 2: 修复 FDE `n_eff_shift` 默认值（新增 shift_frac=0.5）
  - [x] SubTask 2.1: 读取 `src/polaris/sim/fde/solver.py` 的 `solve` 方法
  - [x] SubTask 2.2: 新增 `shift_frac: float = 0.5` 字段，自动计算 `n_eff_shift`
  - [x] SubTask 2.3: 更新 `FdeSolverConfig` docstring 注明 0.5 系数与 Soref 1991 依据

- [x] Task 3: 修复 FDE 模式筛选排序（优先低损耗导模）
  - [x] SubTask 3.1: 修改 `solve` 方法中 `candidates.sort` 的 key
  - [x] SubTask 3.2: 从 `(re_neff, -abs(im_neff))` 改为 `re_neff - 10 * abs(im_neff)` 降序
  - [x] SubTask 3.3: 验证排序逻辑对 PML 污染模的惩罚效果

- [ ] Task 4: 修复 `te_fraction`/`tm_fraction` 定义（纵向分量 → 横向主场主导度）
  - [ ] SubTask 4.1: 修改 `src/polaris/sim/fde/solver.py` 的 `_te_tm_fraction` 方法
  - [ ] SubTask 4.2: 新定义 `te_fraction = |E_y|²/(|E_x|²+|E_y|²)`，`tm_fraction = |E_x|²/(|E_x|²+|E_y|²)`
  - [ ] SubTask 4.3: 更新 `src/polaris/sim/fde/mode.py` 的 Mode docstring 注明新定义
  - [ ] SubTask 4.4: 验证半矢量 TE 下 te_fraction=1.0

- [ ] Task 5: 修复 `Mode.overlap` 自重叠归一化（分母用复数模）
  - [ ] SubTask 5.1: 修改 `src/polaris/sim/fde/mode.py` 的 `overlap` 方法
  - [ ] SubTask 5.2: 分母从 `power_integral`（取实部）改为 `|cross_m|·|cross_n|`（复数模）
  - [ ] SubTask 5.3: 验证有损模式自重叠 = 1.0 ± 1e-6

- [ ] Task 6: 修复 FDE `k_request` 增大搜索范围
  - [ ] SubTask 6.1: 修改 `src/polaris/sim/fde/solver.py` 的 `solve` 方法
  - [ ] SubTask 6.2: `k_request` 从 `num_modes + 4` 改为 `num_modes + 8`
  - [ ] SubTask 6.3: 验证 SOI 基模 n_eff 接近 2.344（容差 0.05）

- [ ] Task 7: 调整 EME 测试窗口配置避免 PML 污染
  - [ ] SubTask 7.1: 修改 `tests/test_eme_backend.py` 的 `_make_backend` 函数
  - [ ] SubTask 7.2: `window_size` 从 `(2.0e-6, 1.5e-6)` 改为 `(3.0e-6, 2.5e-6)`
  - [ ] SubTask 7.3: 验证锥形/MMI energy_sum ∈ [0.999, 1.001]

- [ ] Task 8: 运行测试验证全通过
  - [ ] SubTask 8.1: 运行 `tests/test_a04_fde.py`（全部测试通过）
  - [ ] SubTask 8.2: 运行 `tests/test_eme_backend.py`（全部 9 个测试通过）
  - [ ] SubTask 8.3: 运行 `tests/test_a02_eme.py`（不回归）
  - [ ] SubTask 8.4: 如有失败，分析根因并迭代修复

- [ ] Task 9: 提交代码合并 main 分支 + 更新操作记录
  - [ ] SubTask 9.1: `git add` 精确文件（mode.py, solver.py, test_eme_backend.py）
  - [ ] SubTask 9.2: `git commit -m "fix: FDE te_fraction 定义 + overlap 归一化 + k_request + EME 窗口配置"`
  - [ ] SubTask 9.3: 推送到 main 远端，切回开发分支
  - [ ] SubTask 9.4: 更新 `操作记录.md` 追加本轮工作记录

# Task Dependencies
- Task 4, 5, 6, 7 可并行（不同文件/不同函数）
- Task 8 依赖 Task 4 + Task 5 + Task 6 + Task 7 全部完成
- Task 9 依赖 Task 8 全测试通过
