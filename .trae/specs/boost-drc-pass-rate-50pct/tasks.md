# Tasks

- [ ] Task 1: 同步 DENSITY_MIN 规则描述到连续缩放逻辑
  - [ ] SubTask 1.1: 修改 `modules/drc/src/polaris_drc/rules.py` 的 DENSITY_MIN
        规则 description，移除 "XXL=0.0001%, XXXL=0.00001%" 旧描述，改为
        "XS/S=0.01%, M=0.005%, L=0.002%, XL=0.001%, ≥10mm 连续缩放
        threshold=100μm²/canvas_area×100"
  - [ ] SubTask 1.2: 修改 `modules/drc/src/polaris_drc/engine.py` 模块
        docstring 中 DENSITY_MIN 行（第 40 行附近），同步连续缩放描述
  - [ ] SubTask 1.3: 修改 `modules/drc/src/polaris_drc/checks.py` 的
        `density_min_threshold_by_canvas` docstring，确保连续缩放说明清晰

- [ ] Task 2: 更新 DRC 单元测试反映新行为
  - [ ] SubTask 2.1: 修改 `modules/drc/tests/test_drc.py` 的
        `test_density_min_xxl_threshold`：50000×50000 期望值从 0.0001 改为
        100/(50000×50000)×100 = 4e-6；违规场景更新（device 10×10=100μm²，
        density=4e-6% == threshold 4e-6%，需用更小 device 触发违规）
  - [ ] SubTask 2.2: 修改 `test_density_min_xxxl_threshold`：200000×200000
        期望值从 0.00001 改为 100/(200000×200000)×100 = 2.5e-7；移除
        100000/99999 边界离散值断言，改为连续缩放断言
  - [ ] SubTask 2.3: 验证 PORT_FACING 的 4 个测试（test_port_facing_correct/
        wrong/bend_compensate_default/perpendicular_bend）全部通过

- [ ] Task 3: 运行 DRC 全量单元测试验证
  - [ ] SubTask 3.1: 执行 `cd /workspace && python -m pytest modules/drc/tests/ -x`
  - [ ] SubTask 3.2: 确认所有测试通过（预期 47+ 个 pytest 全绿）
  - [ ] SubTask 3.3: 如有失败，修复至全绿（R05 Bug 必修）

- [ ] Task 4: 验证 expert_demos DRC 通过率
  - [ ] SubTask 4.1: 对 10 个 expert_demos 执行 DRC 检查
  - [ ] SubTask 4.2: 确认 MZI1/RingResonator/Ring_series/mzi_adjustable_splitter
        4 个原 DENSITY_MIN 失败用例现在通过
  - [ ] SubTask 4.3: 确认 expert_demos DRC 通过率 ≥ 80%（目标 10/10 = 100%）

- [ ] Task 5: 验证 70 个真实板子抽样 DRC 通过率 ≥ 50%
  - [ ] SubTask 5.1: 执行 70 个真实板子端到端 DRC 检查
  - [ ] SubTask 5.2: 统计 DRC 通过率，确认 ≥ 50%（目标 35/70+）
  - [ ] SubTask 5.3: 如未达标，分析剩余失败用例根因

- [ ] Task 6: 提交代码到 main 分支并刷新操作记录
  - [ ] SubTask 6.1: `git add` 精确文件（rules.py / engine.py / checks.py /
        test_drc.py）
  - [ ] SubTask 6.2: `git commit -m "fix(drc): bend_compensate+DENSITY_MIN连续
        缩放提升通过率37.1%→≥50%（R03禁止fall-back）"`
  - [ ] SubTask 6.3: `git push origin main`
  - [ ] SubTask 6.4: 追加 `操作记录.md`，含轮次编号、交付文件、测试结果、
        规则依据、无 fall-back 声明

# Task Dependencies
- Task 1（描述同步）与 Task 2（测试更新）可并行
- Task 3（测试验证）依赖 Task 1+2 完成
- Task 4（expert_demos 验证）依赖 Task 3 通过
- Task 5（70 板子验证）依赖 Task 3 通过
- Task 6（提交）依赖 Task 4+5 达标
# Tasks

- [ ] Task 1: 同步 DENSITY_MIN 规则描述到连续缩放逻辑
  - [ ] SubTask 1.1: 修改 `modules/drc/src/polaris_drc/rules.py` 的 DENSITY_MIN
        规则 description，移除 "XXL=0.0001%, XXXL=0.00001%" 旧描述，改为
        "XS/S=0.01%, M=0.005%, L=0.002%, XL=0.001%, ≥10mm 连续缩放
        threshold=100μm²/canvas_area×100"
  - [ ] SubTask 1.2: 修改 `modules/drc/src/polaris_drc/engine.py` 模块
        docstring 中 DENSITY_MIN 行（第 40 行附近），同步连续缩放描述
  - [ ] SubTask 1.3: 修改 `modules/drc/src/polaris_drc/checks.py` 的
        `density_min_threshold_by_canvas` docstring，确保连续缩放说明清晰

- [ ] Task 2: 更新 DRC 单元测试反映新行为
  - [ ] SubTask 2.1: 修改 `modules/drc/tests/test_drc.py` 的
        `test_density_min_xxl_threshold`：50000×50000 期望值从 0.0001 改为
        100/(50000×50000)×100 = 4e-6；违规场景更新（device 10×10=100μm²，
        density=4e-6% == threshold 4e-6%，需用更小 device 触发违规）
  - [ ] SubTask 2.2: 修改 `test_density_min_xxxl_threshold`：200000×200000
        期望值从 0.00001 改为 100/(200000×200000)×100 = 2.5e-7；移除
        100000/99999 边界离散值断言，改为连续缩放断言
  - [ ] SubTask 2.3: 验证 PORT_FACING 的 4 个测试（test_port_facing_correct/
        wrong/bend_compensate_default/perpendicular_bend）全部通过

- [ ] Task 3: 运行 DRC 全量单元测试验证
  - [ ] SubTask 3.1: 执行 `cd /workspace && python -m pytest modules/drc/tests/ -x`
  - [ ] SubTask 3.2: 确认所有测试通过（预期 47+ 个 pytest 全绿）
  - [ ] SubTask 3.3: 如有失败，修复至全绿（R05 Bug 必修）

- [ ] Task 4: 验证 expert_demos DRC 通过率
  - [ ] SubTask 4.1: 对 10 个 expert_demos 执行 DRC 检查
  - [ ] SubTask 4.2: 确认 MZI1/RingResonator/Ring_series/mzi_adjustable_splitter
        4 个原 DENSITY_MIN 失败用例现在通过
  - [ ] SubTask 4.3: 确认 expert_demos DRC 通过率 ≥ 80%（目标 10/10 = 100%）

- [ ] Task 5: 验证 70 个真实板子抽样 DRC 通过率 ≥ 50%
  - [ ] SubTask 5.1: 执行 70 个真实板子端到端 DRC 检查
  - [ ] SubTask 5.2: 统计 DRC 通过率，确认 ≥ 50%（目标 35/70+）
  - [ ] SubTask 5.3: 如未达标，分析剩余失败用例根因

- [ ] Task 6: 提交代码到 main 分支并刷新操作记录
  - [ ] SubTask 6.1: `git add` 精确文件（rules.py / engine.py / checks.py /
        test_drc.py）
  - [ ] SubTask 6.2: `git commit -m "fix(drc): bend_compensate+DENSITY_MIN连续
        缩放提升通过率37.1%→≥50%（R03禁止fall-back）"`
  - [ ] SubTask 6.3: `git push origin main`
  - [ ] SubTask 6.4: 追加 `操作记录.md`，含轮次编号、交付文件、测试结果、
        规则依据、无 fall-back 声明

# Task Dependencies
- Task 1（描述同步）与 Task 2（测试更新）可并行
- Task 3（测试验证）依赖 Task 1+2 完成
- Task 4（expert_demos 验证）依赖 Task 3 通过
- Task 5（70 板子验证）依赖 Task 3 通过
- Task 6（提交）依赖 Task 4