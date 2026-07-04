# Tasks

- [ ] Task 1: 真实用例统一目录与索引
  - [ ] SubTask 1.1: 创建 `data/real_circuits/` 目录结构（siepic/gdsfactory/picbench/lidar/align/expert_demos 子目录）
  - [ ] SubTask 1.2: 创建 `scripts/consolidate_real_circuits.py`，合并 417 个真实用例到统一目录
  - [ ] SubTask 1.3: 生成 `data/real_circuits/index.json`（含 name/source/format/path/origin_url/license）
  - [ ] SubTask 1.4: 验证合并后用例数 = 417，无丢失

- [ ] Task 2: 真实用例上传 GitHub
  - [ ] SubTask 2.1: 检查仓库体积，确认无超过 GitHub 100MB 单文件限制
  - [ ] SubTask 2.2: git add data/real_circuits/ → commit → push origin main
  - [ ] SubTask 2.3: 验证 GitHub 远端可见真实用例

- [ ] Task 3: 真实用例格式转换（GDS/netlist → CircuitSpec）
  - [ ] SubTask 3.1: 创建 `scripts/convert_real_to_polaris.py`
  - [ ] SubTask 3.2: SiEPIC GDS 转换：klayout 读取 GDS 提取器件+连接
  - [ ] SubTask 3.3: gdsfactory netlist (.pic.yml/.yml) 转换
  - [ ] SubTask 3.4: picbench/lidar JSON 转换
  - [ ] SubTask 3.5: 转换后合法性校验 + 转换报告

- [ ] Task 4: 真实板子端到端测试与汇报
  - [ ] SubTask 4.1: 创建 `scripts/test_real_circuits.py`，对真实用例执行端到端流水线
  - [ ] SubTask 4.2: 测试全部 417 个真实用例（含 GDS 和 netlist 来源）
  - [ ] SubTask 4.3: 汇报成功率、DRC 通过率、平均损耗、平均耗时
  - [ ] SubTask 4.4: 与程序化 1200 电路结果对比
  - [ ] SubTask 4.5: 失败用例根因分析

- [ ] Task 5: 基于真实板子组合生成器
  - [ ] SubTask 5.1: 创建 `scripts/generate_combination_circuits.py`
  - [ ] SubTask 5.2: 从真实板子提取拓扑组件（MZI/Ring/DC/MMI/Switch/Modulator/WDM）
  - [ ] SubTask 5.3: 二元组合生成（A+B，覆盖 7×6=42 种组合 × 10 变种 = 420 个）
  - [ ] SubTask 5.4: 多元组合生成（A+B+C+D，10 种典型混合 × 5 变种 = 50 个）
  - [ ] SubTask 5.5: 规模扩展生成（单组件 ×N 阵列化，N=2/4/8/16，7 组件 × 4 规模 = 28 个）
  - [ ] SubTask 5.6: 总数 ≥500 个组合电路，输出到 `data/benchmarks/combinations/`

- [ ] Task 6: 组合电路测试与汇报
  - [ ] SubTask 6.1: 对 ≥500 个组合电路执行端到端测试
  - [ ] SubTask 6.2: 汇报成功率、DRC 通过率、平均损耗
  - [ ] SubTask 6.3: 识别失败组合并分析根因
  - [ ] SubTask 6.4: 与真实+程序化结果对比

- [ ] Task 7: 商用版最终测试报告（含真实+组合+程序化）
  - [ ] SubTask 7.1: 生成 `docs/商用版最终测试报告.md`
  - [ ] SubTask 7.2: 总体统计（≥2100 电路）+ 真实/组合/程序化三组对比
  - [ ] SubTask 7.3: 商用发布结论

- [ ] Task 8: 代码提交与操作记录
  - [ ] SubTask 8.1: 每个小任务完成后 git add 精确文件 → commit → push origin main
  - [ ] SubTask 8.2: 追加 `操作记录.md`

# Task Dependencies
- Task 1 可立即开始
- Task 2 依赖 Task 1
- Task 3 可立即开始（与 Task 1 并行）
- Task 4 依赖 Task 3
- Task 5 可立即开始（与 Task 1/3 并行）
- Task 6 依赖 Task 5
- Task 7 依赖 Task 4/6
- Task 8 贯穿全程
