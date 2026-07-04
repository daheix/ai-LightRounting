# Tasks

- [x] Task 1: 创建 `modules/gds_tools/src/polaris_gds_tools/gds_loader.py`
  - [x] SubTask 1.1: 实现 klayout.db 读取 GDSII 文件
  - [x] SubTask 1.2: 实现多策略器件识别（instance / DEVREC polygon / 顶层 cell）
  - [x] SubTask 1.3: 实现 SiEPIC → PoLaRIS 器件名映射表
  - [x] SubTask 1.4: 实现 PIN 端口提取与 text→path 匹配（无匹配 raise，R03）
  - [x] SubTask 1.5: 实现跨器件连接推断（容差 15.0μm，排除同器件端口）
  - [x] SubTask 1.6: 实现 Spice_param 参数解析
  - [x] SubTask 1.7: 实现 DCplxTrans 手动变换（klayout 运算符不生效）
  - [x] SubTask 1.8: 三个对外 API（load_gds_to_circuit / load_gds_to_circuit_spec / siepic_to_polaris）
  - [x] SubTask 1.9: 压缩 docstring 使文件 ≤800 行（R11 质量门禁）

- [x] Task 2: 在 `__init__.py` 导出新 API
  - [x] SubTask 2.1: 添加 gds_loader 导入
  - [x] SubTask 2.2: 在 `__all__` 中添加三个新 API

- [x] Task 3: 创建 `scripts/test_siepic_gds_loader.py` 测试脚本
  - [x] SubTask 3.1: 默认测 10 个文件（覆盖三种识别策略）
  - [x] SubTask 3.2: `--all` 跑全量 229 个
  - [x] SubTask 3.3: 退出码：默认要求 100%，`--all` 要求 ≥95%

- [x] Task 4: 运行测试验证
  - [x] SubTask 4.1: 默认 10 个文件测试 100% 成功
  - [x] SubTask 4.2: 全量 229 个文件测试 100% 成功（3.20s）
  - [x] SubTask 4.3: 策略分布统计 {instance:104, devrec_polygon:68, top_cell:57}

- [x] Task 5: 修复 `test_real_circuits.py` siepic 分支
  - [x] SubTask 5.1: 移除"模块下线"的 raise
  - [x] SubTask 5.2: 改为调用 `load_gds_to_circuit`
  - [x] SubTask 5.3: 同步更新 docstring 和 FAILURE_CATEGORIES
  - [x] SubTask 5.4: 前 5 个 siepic 用例验证通过

- [x] Task 6: 验证 gds_loader.py 行数 ≤800（R11 质量门禁）
  - [x] SubTask 6.1: `wc -l` 验证行数（压缩后 715 行）
  - [x] SubTask 6.2: 压缩 docstring + 简化分隔注释（903→715 行）

- [x] Task 7: 重新运行默认 10 个文件测试确认无回归
  - [x] SubTask 7.1: 压缩 docstring 后再次运行测试（100% 成功，无回归）

- [x] Task 8: 按 R11 提交代码
  - [x] SubTask 8.1: `git add` 精确文件（4 个）
  - [x] SubTask 8.2: `git commit` (commit 53492a7)
  - [x] SubTask 8.3: `git push origin main` (c9acca9..53492a7)

- [x] Task 9: 按 R07 追加操作记录
  - [x] SubTask 9.1: 在 `操作记录.md` 追加轮次 R345B
  - [x] SubTask 9.2: 含交付文件、测试结果（精确数字）、规则依据（commit 6b43790）

# Task Dependencies
- Task 1-5 已完成（代码实现与测试）
- Task 6 依赖 Task 1（验证压缩后行数）
- Task 7 依赖 Task 6（压缩后回归测试）
- Task 8 依赖 Task 6/7（提交前确认无回归）
- Task 9 依赖 Task 8（提交后追加记录）
