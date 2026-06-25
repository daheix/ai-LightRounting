# AGENTS.md — PoLaRIS 智能体上下文规则

本文件是 PoLaRIS（光弈）光电子AI智能布局布线引擎项目的智能体上下文入口。智能体启动后必须读取本文件并将其添加到上下文中。

---

## 1. 项目规则入口

完整项目规则见 `.trae/rules/project_rules.md`（23 条强制规则）。本文件摘录关键强制规则，智能体必须严格遵守。

---

## 2. 保活脚本（规则 23，强制，最高优先级）

### 2.1 启动要求
- 每个会话启动后，**第一件事**必须启动保活脚本：
  - 每 5 分钟 touch 一个文件，防止会话超时断开；
  - 每 17 分钟向前台发送一条消息："做得很好，按照计划继续执行剩余任务。"
- 保活脚本文件：`scripts/keepalive.sh`（已 chmod +x）
- 启动命令：
  ```bash
  nohup bash scripts/keepalive.sh > /tmp/keepalive_stdout.log 2>&1 &
  ```
- 保活日志写入 `/tmp/keepalive.log`，标记文件 `/tmp/keepalive_marker`，
  最近消息文件 `/tmp/keepalive_message.txt`，前台 stdout 重定向到 `/tmp/keepalive_stdout.log`。

### 2.2 启动验证
- 启动后立即向用户报告："保活脚本已启动，每 5 分钟 touch 文件一次，每 17 分钟向前台发送进度消息。"
- 验证脚本运行：`ps aux | grep keepalive.sh` 或检查 `/tmp/keepalive.log` 是否有新写入。
- 验证消息发送：检查 `/tmp/keepalive_message.txt` 内容应为"做得很好，按照计划继续执行剩余任务。"

### 2.3 失败处理
- 若保活脚本启动失败，立即告警并退出（禁止 fall-back 静默继续）。
- 若会话中途检测到保活脚本停止，立即重启。

---

## 3. 代码提交纪律（规则 1.2，强制）

- 开发分支固定名称：`trae/solo-agent-QtGqG4-ai-Light`（永久不变）。
- 每 20 分钟（或每个小任务完成后）必须向远端 `main` 分支提交一次代码。
- 提交流程：`git add` 精确文件 → `git commit -m "<type>: <简述>"` → `git push origin main` → 切回开发分支。
- 禁止 `git add -A`/`git add .`，禁止 force push 到 `main`，禁止空提交。
- 提交前必须通过本地 lint/typecheck/pytest 冒烟测试。

---

## 4. 无 fall-back 设计（规则 14.1，强制）

- 所有错误必须 `raise`，禁止 `except: pass`、`except: return None`、`except: return []` 等静默兜底。
- 业务流程跑不通就是业务设计有问题，返回告警即可，禁止任何假数据 fall-back。
- 所有 `except` 块必须记录错误并 `raise`，或显式处理（如记录日志后继续，但不得返回假数据）。

---

## 5. 学术诚信（规则 18，强制）

- 所有参数、阈值、公式必须来自开源仓库实际源码或权威论文，禁止编造。
- 每个方案须记录：来源标题、作者/机构、年份、网址 URL。
- 创新点必须标注"【创新】"，记录创新逻辑、底层逻辑、案例和支持理论。

---

## 6. 质量门禁（规则 7，强制）

- 圈复杂度 ≤ 15
- 函数行数 ≤ 80
- 文件行数 ≤ 800
- 测试覆盖率 ≥ 90%
- 无 `except: pass`、无 `TODO`/`FIXME`、无假数据

---

## 7. 中文回答（强制）

- 必须使用中文回答问题，禁止使用英文沟通。
- 代码注释遵循同一语言规则（除非另有指示）。

---

## 8. 操作记录（强制）

- 所有操作结果、讨论结果必须保存到 `操作记录.md` 中。
- 每一轮工作记录包含：轮次编号、路标编号、交付文件清单、测试结果、创新点、文献引用、质量门禁达标声明、无 fall-back 声明。

---

## 9. 单文件版本升级（规则 2，强制）

- 代码文件只有一份，文件内可以升级 v1/v2/v3/v4，禁止多个 vx 文件同时存在。
- 新版本建立后，彻底删除老版本，只保留最新的代码和最新的设计。
- 文档根据最新版本重新写或同步刷新。

---

## 10. 研发资源清单（6 大类权威资源）

所有架构疑难、性能瓶颈、分布式问题、技术短板必须优先检索以下海外资源，再查国内资料：

1. **国际顶级学术期刊**：arXiv、IEEE Xplore、ACM Digital Library、SpringerLink、ScienceDirect、Nature Computer Science、MDPI、USENIX、VLDB/SIGMOD
2. **国外一线研发工程师实战论坛**：Stack Overflow、Hacker News、Reddit r/programming、Dev.to、Medium Engineering Blog、InfoQ International、CodeProject
3. **顶级开源官方研发社区**：GitHub Discussions、GitHub Issues、GitLab Community、Apache Community、CNCF Community
4. **国际技术标准**：IETF RFC、W3C、OASIS、OpenAPI Official、ISO/IEC
5. **海外高端技术智库**：Google Research、Meta Engineering Blog、Amazon AWS Architecture Blog、Microsoft Research、Cloudflare Blog、Netflix Tech Blog
6. **垂直研发社区**：High Scalability、Database Internals、Distributed Systems Reading Group、Martin Fowler Blog

**权威优先级**：国际顶会论文 > 大厂官方工程博客 > 海外高赞社区实践 > 国内技术内容。

---

## 11. 36 月路标（R01-R36）

- **路标总览**：`docs/36-RoundMap.md`
- **路标文档**：`docs/roundmap/R01.md` ~ `R36.md`
- **执行计划**：`.trae/documents/execute-r07-to-r36-roundmaps-v4.md`
- **当前进度**：R01-R06 已完成合并 main，R07 进行中，R08-R36 待执行。
- **目标**：36 个月内综合得分从 6.1 提升至 9.2，对齐并超越商业产品。

---

## 12. 分支管理纪律（规则 24，强制，禁止孤儿分支）

### 12.1 核心原则：禁止孤儿分支
- 仓库**只允许保留两个长期分支**：`main`（稳定发布）+ `dev`（开发集成）。
- **禁止孤儿分支**：所有开发分支必须最终合并到 `main`，合并后立即删除，禁止残留。
- 临时开发分支（`trae/agent-xxx`、`feature/xxx`）合并后必须立即删除（本地 + 远端）。

### 12.2 分支生命周期
1. 从 `dev` 创建临时分支开发
2. 合并到 `dev`，再由 `dev` 合并到 `main`
3. 合并后立即删除临时分支
4. `main` 和 `dev` 必须保持同步

### 12.3 强制清理
- 每次会话启动必须检查分支状态：`git fetch --all --prune && git branch -a`
- 发现孤儿分支必须立即合并或删除
- 禁止保留 `develop`、`trae/auto-commit`、`trae/solo-agent-xxx` 等冗余分支

---

## 14. Plan/Spec 自动执行纪律（规则 25，强制）

所有的 plan 和 spec 制定的规则与任务，**无需用户同意，立即执行**。

- Spec 批准后直接进入实施阶段，不再询问
- Plan 制定后直接添加所有任务到 todos 并一次性完成
- 任务执行中途不暂停询问，失败时告警并尝试替代方案
- 禁止过度确认，直接执行

---

## 15. 不参与 GPU 计算战略决策（规则 26，强制，不可撤销）

**PoLaRIS 项目战略决策：不参与 GPU 计算。** 由项目所有者于 2026-06-25 明确指示。

### 15.1 不参与范围
- GPU 加速（CuPy/CUDA/ROCm/AppleMetal 等所有 GPU 后端）
- 多卡 GPU 分布式并行（多 GPU 训练/多 GPU 仿真）
- FP16/BF16 半精度计算（GPU 专属特性）
- 云端弹性 GPU 算力（商业云计算 GPU 集群）
- GPU 加速 FDTD（GPUFDTDEngine/Tidy3D GPU/曼光 100× 加速等）

### 15.2 标记规范
所有 GPU 相关功能点状态统一标记为 `🚫不参与`，差距说明统一使用：
```
**PoLaRIS 战略决策：不参与 GPU 计算**。<具体不适用原因>
```

### 15.3 代码保留策略
- GPU 代码（`src/polaris/engine/gpu_backend.py`、`GPUFDTDEngine`）保留但不作为发展方向
- 禁止新增 GPU 相关开发任务
- 禁止将 GPU 功能点计入商业对标覆盖率
- 覆盖率公式：`(✅已有 + ⚠️部分) / (✅已有 + ⚠️部分 + ❌缺失)`，剔除🚫不参与/🚫不适用项

### 15.4 已标记文件清单
- `docs/polaris_feature_inventory.md`：3 处 GPU 条目（GPUBackend/CuPyBackend/GPUFDTDEngine）
- `docs/feature_gap_full_analysis.md`：~43 处 GPU 相关功能点
- `docs/year_plan_2026_06_2027_05.md`：~7 处 GPU 开发计划已剔除
- `.trae/rules/project_rules.md` 规则 26：战略决策正式记录

---

## 16. 空间清理（按需）

若空间不够用，可删除以下冗余工具（识别主要冗余）：
- swiftly（6.5G）
- mise（3.0G）
- rustup（1.8G）

保留 Python 开发所需工具即可。项目内部的三方库目录有所有的工具使用和安装方法，环境初始化保证工具都可用。
