# Tasks

## 阶段 1: 根因分析（为什么有 95 Bug）

- [ ] Task 1: 撰写根因分析报告（`docs/学术诚信检查.md` 新增 §7）
  - [ ] SubTask 1.1: 统计 95 Bug 按 5 类根因分布（历史债/审查方法/算法复杂度/集成缺陷/文献不足）
  - [ ] SubTask 1.2: 每类根因列出典型案例（3-5 Bug）+ 流程缺陷描述 + 改进措施
  - [ ] SubTask 1.3: 撰写 §7 根因分析与流程改进（含 5 类根因表 + 改进 roadmap）

## 阶段 2: 5 P0 Bug 修复（Year 1 Q1 优先，WebSearch 验证）

- [ ] Task 2: 修复 #v3.3-VER-2 verification/M4 硬编码 True
  - [ ] SubTask 2.1: WebSearch "M4 milestone delivery checklist software engineering"
  - [ ] SubTask 2.2: 读取 `src/polaris/verification/drc_curvilinear_18rules.py`，移除硬编码 True，改为真实状态查询
  - [ ] SubTask 2.3: 回归测试 + docstring 文献补充
- [ ] Task 3: 修复 #v3.3-Q-3 quantum/KLM_CNOT 未实现
  - [ ] SubTask 3.1: WebSearch "KLM CNOT gate linear optical quantum computing Knill Nature 2001"
  - [ ] SubTask 3.2: 读取 `src/polaris/quantum/quantum_circuit_distributed.py`，实现 KLM CNOT 门（含辅助光子 + 后选择）
  - [ ] SubTask 3.3: 回归测试 + docstring 补 Knill 2001 / Ralph 2002 / Hofmann 2002 / O'Brien 2003 / Knill 2002
- [ ] Task 4: 修复 #v3.3-Q-4 quantum/玻色采样缺失
  - [ ] SubTask 4.1: WebSearch "boson sampling Aaronson 2011 Arkhipov implementation"
  - [ ] SubTask 4.2: 实现玻色采样（ permanents of submatrix / Glynn-Gray 算法）
  - [ ] SubTask 4.3: 回归测试 + docstring 补 Aaronson 2011 / Arkhipov 2014 / Clifford 2017 / Wu 2020 / Zhong 2020
- [ ] Task 5: 修复 #v3.3-AI-6 ai/real_shapes 合成数据
  - [ ] SubTask 5.1: WebSearch "inverse design real photonic shapes dataset training"
  - [ ] SubTask 5.2: 读取 `src/polaris/ai/inverse_design.py`，移除 real_shapes 合成数据，改为真实 PDK 器件采样
  - [ ] SubTask 5.3: 回归测试 + docstring 补真实数据来源（SiEPIC EBeam PDK）
- [ ] Task 6: 修复 #v3.3-SYS-3 system/CANCELLED 假实现
  - [ ] SubTask 6.1: WebSearch "python asyncio task cancellation CancelledError best practice"
  - [ ] SubTask 6.2: 读取 `src/polaris/system/system.py`，实现真实 CANCELLED 状态（asyncio.CancelledError + 状态机）
  - [ ] SubTask 6.3: 回归测试 + docstring 补 PEP 8 异常处理

## 阶段 3: P1-A 算法错误修复（16 项，WebSearch 验证）

- [ ] Task 7: 修复 verification/ P1-A Bug（#v3.3-VER-1/3/4/11/12，5 项）
  - [ ] SubTask 7.1: #v3.3-VER-1 DRC 18 规则无几何实现 → WebSearch "curvilinear DRC geometry check KLayout" + 实现真实几何运算
  - [ ] SubTask 7.2: #v3.3-VER-3 PEX 边缘电容公式 → WebSearch "parasitic capacitance fringing edge formula"
  - [ ] SubTask 7.3: #v3.3-VER-4 Layout-Aware MC 空间相关 → WebSearch "layout aware Monte Carlo spatial correlation"
  - [ ] SubTask 7.4: #v3.3-VER-11 凹多边形 → WebSearch "concave polygon point in polygon algorithm"
  - [ ] SubTask 7.5: #v3.3-VER-12 耦合长度 → WebSearch "directional coupler coupling length formula"
  - [ ] SubTask 7.6: 回归测试 + docstring 文献补充
- [ ] Task 8: 修复 inverse/ P1-A Bug（#v3.3-INV-3，1 项）
  - [ ] SubTask 8.1: WebSearch "topology adjoint optimization sigmoid projection three layer"
  - [ ] SubTask 8.2: 修复三层 sigmoid 投影
  - [ ] SubTask 8.3: 回归测试
- [ ] Task 9: 修复 quantum/ P1-A Bug（#v3.3-Q-1/2，2 项）
  - [ ] SubTask 9.1: #v3.3-Q-1 PPO 梯度截断 → WebSearch "PPO gradient clipping implementation"
  - [ ] SubTask 9.2: #v3.3-Q-2 GAE V(s)=0 边界 → WebSearch "GAE terminal value bootstrap Schulman 2015"
  - [ ] SubTask 9.3: 回归测试
- [ ] Task 10: 修复 device/ P1-A Bug（#v3.3-D-2/3/4/6，4 项）
  - [ ] SubTask 10.1: #v3.3-D-2 热串扰魔法数 0.5 → 已用 Carslaw-Jaeger，文档同步
  - [ ] SubTask 10.2: #v3.3-D-3 V_π 带宽公式 → WebSearch "modulator Vpi bandwidth formula"
  - [ ] SubTask 10.3: #v3.3-D-4 Δα 单位错 → WebSearch "plasma dispersion effect delta alpha unit"
  - [ ] SubTask 10.4: #v3.3-D-6 瞬态热响应缺失 → WebSearch "transient thermal response FDM Crank-Nicolson"
  - [ ] SubTask 10.5: 回归测试
- [ ] Task 11: 修复 ai/nn/io/gui/eval/ P1-A Bug（#v3.3-AI-5/NN-3/IO-2/GUI-1/SYS-2，5 项）
  - [ ] SubTask 11.1: #v3.3-AI-5 启发式公式无溯源 → WebSearch 验证 + 补溯源或删除
  - [ ] SubTask 11.2: #v3.3-NN-3 dtype 类型不一致 → 统一 float32/float64
  - [ ] SubTask 11.3: #v3.3-IO-2 读写不对称 → 实现对称 IO
  - [ ] SubTask 11.4: #v3.3-GUI-1 RemoveObjectCommand 浅拷贝 → 改深拷贝
  - [ ] SubTask 11.5: #v3.3-SYS-2 _future 未声明 → 补声明
  - [ ] SubTask 11.6: 回归测试

## 阶段 4: P1-B R03 fall-back 修复（33 项，按子包分批）

- [ ] Task 12: 修复 verification/ flow/ pipeline/ fall-back（16 项）
  - [ ] SubTask 12.1: verification #v3.3-VER-1/13（2 项）→ except raise
  - [ ] SubTask 12.2: flow #v3.3-F-1~7（7 项）→ except raise
  - [ ] SubTask 12.3: pipeline #v3.3-P-1~7（7 项）→ except raise
  - [ ] SubTask 12.4: 回归测试
- [ ] Task 13: 修复 data/ io/ system/ fall-back（19 项）
  - [ ] SubTask 13.1: data #v3.3-D-1~15（15 项）→ except raise
  - [ ] SubTask 13.2: io #v3.3-IO-1/3/4（3 项）→ except raise
  - [ ] SubTask 13.3: system #v3.3-SYS-1（1 项）→ except raise
  - [ ] SubTask 13.4: 回归测试

## 阶段 5: P1-C 文档不符 + P1-D 占位修复（35 项）

- [ ] Task 14: 修复 P1-C 文档不符（8 项）
  - [ ] SubTask 14.1: #v3.3-3 cuda_solver R04 声明
  - [ ] SubTask 14.2: #v3.3-PDK-1 process_nodes 9→13
  - [ ] SubTask 14.3: #v3.3-INV-4 λ/20 标注
  - [ ] SubTask 14.4: #v3.3-Q-5 final_key_hex 命名
  - [ ] SubTask 14.5: #v3.3-GUI-2 PIN 层死代码
  - [ ] SubTask 14.6: #v3.3-WEB-1 JSONL n_skipped
  - [ ] SubTask 14.7: #v3.3-EVAL-1/3 klayout import + 类型注解
  - [ ] SubTask 14.8: 回归测试
- [ ] Task 15: 修复 P1-D "修复中"占位（27 项）
  - [ ] SubTask 15.1: verification #v3.3-VER-5~10（6 项）→ 真实修复
  - [ ] SubTask 15.2: verify #v3.3-VER-14~17（4 项）→ 真实修复
  - [ ] SubTask 15.3: inverse #v3.3-INV-5~14（10 项）→ 真实修复
  - [ ] SubTask 15.4: quantum #v3.3-Q-7（1 项）→ 真实修复
  - [ ] SubTask 15.5: device #v3.3-D-7~9（3 项）→ 真实修复
  - [ ] SubTask 15.6: ai #v3.3-AI-7~9（3 项）→ 真实修复
  - [ ] SubTask 15.7: 回归测试

## 阶段 6: P2 文献补充 + 预防机制（4 + 1 项）

- [ ] Task 16: 修复 P2 文献不足（4 项）
  - [ ] SubTask 16.1: #v3.3-4 sim/quantum/qfdtd.py 补 5 篇量子 FDTD 文献
  - [ ] SubTask 16.2: #v3.3-5 sim/varfdtd/eff_index.py 补 5 篇 varFDTD 文献
  - [ ] SubTask 16.3: #v3.3-6 sim/cascade/scatter.py 补 5 篇散射矩阵文献
  - [ ] SubTask 16.4: #v3.3-Q-6 quantum Ray 文献虚标 → 替换真实文献
- [ ] Task 17: 新增 `docs/开发流程防Bug规范.md`
  - [ ] SubTask 17.1: CI 前置审查 checklist（fall-back 扫描 / 文献 ≥5 / 回归测试 / 函数 ≤80 行）
  - [ ] SubTask 17.2: Bug 根因分类模板（5 类根因 + 记录模板）
  - [ ] SubTask 17.3: 防复发 roadmap（季度审查 + 自动化扫描）

## 阶段 7: 文档更新与提交

- [ ] Task 18: 更新 `docs/学术诚信检查.md` v3.3 → v4.0
  - [ ] SubTask 18.1: §1 版本日志新增 v4.0 条目（95 Bug 全修，98%+）
  - [ ] SubTask 18.2: §5 Bug 历史全部 140 Bug 状态更新为"已修"
  - [ ] SubTask 18.3: §6 综合评分 92% → 98%+
  - [ ] SubTask 18.4: 新增 §7 根因分析 + §8 预防机制
- [ ] Task 19: 更新 `商业活动计划表-五年.md`
  - [ ] SubTask 19.1: P0 未修数量 5→0
  - [ ] SubTask 19.2: 综合商业可用率 88% → 98%+
- [ ] Task 20: 提交代码 + 更新操作记录
  - [ ] SubTask 20.1: git add 全部修复文件 + 文档
  - [ ] SubTask 20.2: git commit -m "fix(v4.0): 全 95 Bug 修复 + 根因分析 + 预防机制"
  - [ ] SubTask 20.3: git push origin main
  - [ ] SubTask 20.4: 操作记录.md 追加 v4.0 记录

# Task Dependencies

- Task 1 → Task 2-6（先根因分析，再修复）
- Task 2-6 可并行（5 P0 Bug 独立，Year 1 Q1 优先）
- Task 2-6 → Task 7-11（P0 修复后修 P1-A）
- Task 7-11 可并行（P1-A 按子包独立）
- Task 7-11 → Task 12-13（P1-A 后修 P1-B fall-back）
- Task 12-13 可并行（不同子包）
- Task 12-13 → Task 14-15（P1-B 后修 P1-C/D）
- Task 14-15 可并行
- Task 14-15 → Task 16-17（P1 后修 P2 + 预防机制）
- Task 16-17 可并行
- Task 16-17 → Task 18-20（修复完成后更新文档 + 提交）
