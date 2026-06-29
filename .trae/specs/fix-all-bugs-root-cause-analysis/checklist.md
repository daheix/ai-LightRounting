# 全 Bug 根因分析与彻底修复 Checklist

## 根因分析（§7）

- [ ] `docs/学术诚信检查.md` 新增 §7 根因分析与流程改进
- [ ] 5 类根因识别（历史债/审查方法/算法复杂度/集成缺陷/文献不足）
- [ ] 每类根因含 Bug 数统计 + 3-5 典型案例 + 流程缺陷描述 + 改进措施

## 5 P0 Bug 修复（Year 1 Q1 优先）

- [ ] #v3.3-VER-2 verification/M4 硬编码 True 修复（WebSearch + 代码 + 测试 + docstring）
- [ ] #v3.3-Q-3 quantum/KLM_CNOT 实现（Knill Nature 2001 WebSearch 验证）
- [ ] #v3.3-Q-4 quantum/玻色采样实现（Aaronson 2011 WebSearch 验证）
- [ ] #v3.3-AI-6 ai/real_shapes 真实数据替换
- [ ] #v3.3-SYS-3 system/CANCELLED 真实实现（asyncio.CancelledError）
- [ ] 每个 P0 修复含回归测试（pytest 通过）

## P1-A 算法错误修复（16 项）

- [ ] verification #v3.3-VER-1/3/4/11/12（5 项，含 WebSearch 验证）
- [ ] inverse #v3.3-INV-3（1 项）
- [ ] quantum #v3.3-Q-1/2（2 项）
- [ ] device #v3.3-D-2/3/4/6（4 项）
- [ ] ai/nn/io/gui/sys #v3.3-AI-5/NN-3/IO-2/GUI-1/SYS-2（5 项）
- [ ] 每个 P1-A 修复含 WebSearch 文献验证 + 回归测试

## P1-B R03 fall-back 修复（33 项）

- [ ] verification #v3.3-VER-1/13（2 项）→ except raise
- [ ] flow #v3.3-F-1~7（7 项）→ except raise
- [ ] pipeline #v3.3-P-1~7（7 项）→ except raise
- [ ] data #v3.3-D-1~15（15 项）→ except raise
- [ ] io #v3.3-IO-1/3/4（3 项）→ except raise
- [ ] system #v3.3-SYS-1（1 项）→ except raise
- [ ] 每个 fall-back 修复后无 `except: pass` / `return None/[]/{}` 静默吞异常

## P1-C 文档不符修复（8 项）

- [ ] #v3.3-3 cuda_solver R04 声明
- [ ] #v3.3-PDK-1 process_nodes 9→13
- [ ] #v3.3-INV-4 λ/20 标注
- [ ] #v3.3-Q-5 final_key_hex 命名
- [ ] #v3.3-GUI-2 PIN 层死代码删除
- [ ] #v3.3-WEB-1 JSONL n_skipped
- [ ] #v3.3-EVAL-1 klayout import 位置
- [ ] #v3.3-EVAL-3 类型注解

## P1-D "修复中"占位真实修复（27 项）

- [ ] verification #v3.3-VER-5~10（6 项）→ 真实修复
- [ ] verify #v3.3-VER-14~17（4 项）→ 真实修复
- [ ] inverse #v3.3-INV-5~14（10 项）→ 真实修复
- [ ] quantum #v3.3-Q-7（1 项）→ 真实修复
- [ ] device #v3.3-D-7~9（3 项）→ 真实修复
- [ ] ai #v3.3-AI-7~9（3 项）→ 真实修复

## P2 文献补充（4 项）

- [ ] #v3.3-4 sim/quantum/qfdtd.py 补 5 篇量子 FDTD 文献
- [ ] #v3.3-5 sim/varfdtd/eff_index.py 补 5 篇 varFDTD 文献
- [ ] #v3.3-6 sim/cascade/scatter.py 补 5 篇散射矩阵文献
- [ ] #v3.3-Q-6 quantum Ray 文献虚标 → 替换真实文献

## 预防机制

- [ ] `docs/开发流程防Bug规范.md` 新增
- [ ] CI 前置审查 checklist（fall-back 扫描 / 文献 ≥5 / 回归测试 / 函数 ≤80 行）
- [ ] Bug 根因分类模板（5 类根因 + 记录模板）
- [ ] 防复发 roadmap（季度审查 + 自动化扫描）

## 文档更新

- [ ] `docs/学术诚信检查.md` v3.3 → v4.0
- [ ] §1 版本日志新增 v4.0 条目（95 Bug 全修，98%+）
- [ ] §5 Bug 历史全部 140 Bug 状态更新为"已修"
- [ ] §6 综合评分 92% → 98%+
- [ ] 新增 §7 根因分析 + §8 预防机制
- [ ] `商业活动计划表-五年.md` 更新 P0 未修 5→0 + 商业可用率 88%→98%+
- [ ] `操作记录.md` 追加 v4.0 记录

## 学术诚信（R02）

- [ ] 每个 Bug 修复含 WebSearch 权威文献验证（URL 记录在 docstring）
- [ ] 每个 docstring 含 ≥5 文献 URL（R02）
- [ ] 无凭经验/记忆直接修复（R01）
- [ ] 无 fall-back（R03）
- [ ] 纯 CPU 实现（R04）
- [ ] 每个 Bug 修复含回归测试（R05）

## 提交与记录

- [ ] git add 全部修复文件 + 文档
- [ ] git commit 含详细提交信息（v4.0）
- [ ] git push origin main 成功
- [ ] 操作记录.md 追加 v4.0 完整记录
- [ ] 提交记录含版本号 v4.0
