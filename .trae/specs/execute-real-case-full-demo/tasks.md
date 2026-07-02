# Tasks

- [x] Task 1: 创建真实 case 目录骨架与真实输入参数模块
  - [x] SubTask 1.1: 创建 `examples/e2e_showcase/real_case/__init__.py`
  - [x] SubTask 1.2: 实现 `real_inputs.py`，集中管理真实输入参数，每个参数标注来源
        （SiEPIC EBeam PDK / Intel CWDM4 spec / literature URL），含：
        - 波导参数：neff=2.4, ng=4.27, 损耗 3.0 dB/cm（SiEPIC EBeam 220nm SOI strip）
        - MMI 参数：分束比 0.48:0.52, 串扰 -30dB, 插损 0.4dB（SiEPIC EBeam mmi1x2 实测）
        - 光栅耦合器：峰值波长 1550nm, 3dB 带宽 40nm, 插损 1.9dB（SiEPIC EBeam GC 实测）
        - MZI 臂长：100μm / 120μm（Intel CWDM4 MZM 臂长差 20μm 量级）
        - PAM4 调制：100Gbps, 16 采样/符号（IEEE 802.3bs 100GBASE-LR4 spec）
        - 商业对标：Intel 100G CWDM4 插损<8dB, BER<1e-12, 消光比>6dB
  - [x] SubTask 1.3: 验证所有参数有来源标注，无 mock/placeholder

- [x] Task 2: 实现真实 case 端到端运行脚本
  - [x] SubTask 2.1: 实现 `run_real_case.py`，复用已修复的 10 阶段 stage 代码，
        以 real_inputs.py 的真实参数替代 stage 内的默认合成参数
  - [x] SubTask 2.2: 对 100Gbps MZI 调制器 case 跑完整 10 阶段，记录每阶段输出
  - [x] SubTask 2.3: 对 Clements 4x4 光矩阵 case 跑完整 10 阶段，记录每阶段输出
  - [x] SubTask 2.4: 禁止任何 fall-back：若某阶段失败则 raise（R03），记录失败原因

- [x] Task 3: 实现真实性分析模块
  - [x] SubTask 3.1: 实现 `analyze_results.py`，对 10 阶段每阶段输出做真实性判定：
        - `REAL_USABLE`：数值物理合理，可对标商业产品
        - `LIMITED_BY_COMPUTE`：受 demo 算力/网格限制（如 stage10 JAX AD 开销）
        - `LIMITED_BY_DATA`：受训练数据/PDK 限制（如 stage3 无预训练 checkpoint）
  - [x] SubTask 3.2: 对每阶段输出与商业产品对标（Intel CWDM4 / AlphaChip / Lumerical），
        计算差距并诚实标注
  - [x] SubTask 3.3: 汇总真实性统计：X 个 REAL_USABLE / Y 个 LIMITED_BY_COMPUTE / Z 个 LIMITED_BY_DATA

- [x] Task 4: 生成真实 case 完整结果展示报告
  - [x] SubTask 4.1: 生成 `REAL_CASE_REPORT.md`，结构：
        - 概述：真实案例选取理由 + 商业对标产品
        - 真实输入参数清单（含来源溯源表）
        - 10 阶段逐阶段展示：输入→输出数值→真实性判定→对标差距→受限制原因
        - 真实性统计汇总表
        - 诚实结论：哪些真实可用，哪些受限制，与商业产品整体差距
  - [x] SubTask 4.2: 报告中所有数值须来自真实运行结果，禁止编造（R02 学术诚信）
  - [x] SubTask 4.3: 报告中商业对标数据须标注来源（产品 datasheet / literature URL）

- [x] Task 5: 修改 run_showcase.py 支持 --real-case 选项
  - [x] SubTask 5.1: 新增 `--real-case` CLI 选项，触发真实 case 流程
  - [x] SubTask 5.2: `--real-case` 时调用 real_case.run_real_case.run()，否则走原合成 demo
  - [x] SubTask 5.3: 确保不破坏原有合成 demo 流程（回归测试）

- [x] Task 6: 端到端验证与提交
  - [x] SubTask 6.1: 运行 `python examples/e2e_showcase/run_showcase.py --real-case`，
        验证 10 阶段全部成功（0 失败），无任何 fall-back
  - [x] SubTask 6.2: 验证 REAL_CASE_REPORT.md 生成且所有数值真实可溯源
  - [x] SubTask 6.3: git add 精确文件 → commit → push origin main（R11）
  - [x] SubTask 6.4: 追加操作记录到 `操作记录.md`（R07），含精确测试数值

# Task Dependencies
- Task 2 depends on Task 1（需要真实输入参数模块）
- Task 3 depends on Task 2（需要真实运行结果才能分析）
- Task 4 depends on Task 3（需要真实性分析才能生成报告）
- Task 5 depends on Task 2（需要真实 case 运行脚本才能集成）
- Task 6 depends on Task 4, Task 5（全部完成后端到端验证）
- Task 1 无依赖，可独立开始
