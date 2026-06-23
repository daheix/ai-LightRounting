# Tasks

- [x] Task 1: 搭建 e2e_showcase 骨架与日志配置
  - [x] SubTask 1.1: 创建 `examples/e2e_showcase/` 目录与 `__init__.py`
  - [x] SubTask 1.2: 实现 `logging_config.py` 统一日志（控制台彩色 + JSONL 文件 + 阶段计时装饰器）
  - [x] SubTask 1.3: 实现 `run_showcase.py` 主入口（参数解析 `--stage`、`--output-dir`、9 阶段调度器）
  - [x] SubTask 1.4: 创建 `out/e2e_showcase/{logs,gds,verilog_a,spice,reports}` 输出目录结构

- [x] Task 2: 阶段 1 PDK 器件目录展示
  - [x] SubTask 2.1: 实现 `stages/stage1_pdk_catalog.py`，遍历 SOI/SiN/InP/LNOI 四平台
  - [x] SubTask 2.2: 列出每平台器件计数与 3+ 代表器件参数
  - [x] SubTask 2.3: 标注器件来源 foundry（SiEPIC/Ligentec/HyperLight/Pattern Project）

- [x] Task 3: 阶段 2 电路规格定义
  - [x] SubTask 3.1: 实现 `stages/stage2_circuit_spec.py`
  - [x] SubTask 3.2: 定义 MZI 干涉仪 CircuitSpec（5 器件）
  - [x] SubTask 3.3: 定义 Clements 4x4 CircuitSpec（6 分束器 + 4 相移器）
  - [x] SubTask 3.4: 定义量子玻色采样电路规格（4 模酉矩阵）

- [x] Task 4: 阶段 3 AI 布局
  - [x] SubTask 4.1: 实现 `stages/stage3_ai_placement.py`
  - [x] SubTask 4.2: 尝试加载 R34 预训练 checkpoint，失败则降级为解析布局并告警
  - [x] SubTask 4.3: 对 3 个电路生成布局坐标，计算 HPWL
  - [x] SubTask 4.4: 输出 ASCII 布局预览

- [x] Task 5: 阶段 4 智能布线
  - [x] SubTask 5.1: 实现 `stages/stage4_routing.py`
  - [x] SubTask 5.2: 对 3 个电路执行布线（弹性连接器 + 曲线波导）
  - [x] SubTask 5.3: 计算总插入损耗、交叉数、弯曲数
  - [x] SubTask 5.4: 输出路径几何 ASCII 预览

- [x] Task 6: 阶段 5 仿真验证
  - [x] SubTask 6.1: 实现 `stages/stage5_simulation.py`
  - [x] SubTask 6.2: 对 MZI 执行 1500-1600nm 频域 S 参数扫描，输出谐振波长与消光比
  - [x] SubTask 6.3: 对 Clements 计算酉矩阵传输
  - [x] SubTask 6.4: 对 MZI 调制器生成 PAM4 眼图，计算 BER/SNR

- [x] Task 7: 阶段 6 DRC/LVS 验证
  - [x] SubTask 7.1: 实现 `stages/stage6_drc_lvs.py`
  - [x] SubTask 7.2: 执行 16 项 DRC 规则检查，输出违规清单
  - [x] SubTask 7.3: 提取网表并执行 LVS 比对，输出一致性报告

- [x] Task 8: 阶段 7 GDS 导出
  - [x] SubTask 8.1: 实现 `stages/stage7_gds_export.py`
  - [x] SubTask 8.2: 将 3 个电路导出为 GDSII 文件
  - [x] SubTask 8.3: 验证 GDS 文件可重新加载，输出文件大小/结构数/层次数

- [x] Task 9: 阶段 8 光电协同
  - [x] SubTask 9.1: 实现 `stages/stage8_opto_electrical.py`
  - [x] SubTask 9.2: 为 5+ 器件生成 Verilog-A 模型文件
  - [x] SubTask 9.3: 生成 Ngspice 联合仿真网表
  - [x] SubTask 9.4: 生成 PAM4 眼图与 BER

- [x] Task 10: 阶段 9 量子光子验证
  - [x] SubTask 10.1: 实现 `stages/stage9_quantum_photonics.py`
  - [x] SubTask 10.2: 执行 4 光子 4 模玻色采样，输出概率分布与守恒验证
  - [x] SubTask 10.3: 验证 HOM 干涉 |1,1⟩ 概率 = 0
  - [x] SubTask 10.4: 验证 KLM CNOT 成功率 = 0.25 与 Hadamard 门酉性

- [x] Task 11: 汇总报告生成
  - [x] SubTask 11.1: 实现 `report_generator.py`，汇总 9 阶段状态表
  - [x] SubTask 11.2: 生成 `out/e2e_showcase/report.md`（含状态表/指标/产物清单/ASCII 可视化）
  - [x] SubTask 11.3: 编写 `README.md` 演示说明与运行方式

- [x] Task 12: Web 页面扩展
  - [x] SubTask 12.1: 在 `src/polaris/web/server.py` 新增 `/api/showcase/run`、`/api/showcase/report/{run_id}`、`/api/showcase/stages/{run_id}/{stage_id}` 端点
  - [x] SubTask 12.2: 在 `src/polaris/web/static/` 新增 `showcase.html` 页面，9 阶段卡片布局
  - [x] SubTask 12.3: 新增 `showcase.js` 轮询进度与日志流展示
  - [x] SubTask 12.4: 新增 `showcase.css` 卡片样式与状态色

- [ ] Task 13: 测试与验证
  - [ ] SubTask 13.1: 编写 `tests/test_e2e_showcase.py`，验证 9 个阶段独立运行
  - [ ] SubTask 13.2: 验证端到端串联（`run_showcase.py` 全流程）
  - [ ] SubTask 13.3: 验证 JSONL 日志格式与字段完整性
  - [ ] SubTask 13.4: 验证 Markdown 报告生成
  - [ ] SubTask 13.5: ruff check + 全量回归测试

# Task Dependencies

- Task 2-10 依赖 Task 1（骨架与日志配置）
- Task 11 依赖 Task 2-10（汇总各阶段产物）
- Task 12 依赖 Task 11（Web 展示汇总报告）
- Task 13 依赖 Task 1-12（全量验证）
- Task 2-10 之间相互独立，可并行开发
