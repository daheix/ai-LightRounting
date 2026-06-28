# AGENTS.md — PoLaRIS 智能体上下文规则

> PoLaRIS（光弈）光电子AI智能布局布线引擎。所有规则必须严格遵守，详见 `.trae/rules/` 完整规则文件。

---

## 1. 启动第一件事

会话启动后**立即执行**：
```bash
# 1. 启动保活（防超时）
nohup bash scripts/keepalive.sh > /dev/null 2>&1 &

# 2. 检查分支（必须在 main）
git branch --show-current  # 必须在 main

# 3. 检查后台进程
ps aux | grep auto_commit  # V8 每 6 分钟自动提交
ps aux | grep keepalive    # 保活脚本
```

---

## 2. 工作流（V8 极简，强制）

**只在 main 分支开发，不切换，不备份。**

| 操作 | 规则 |
|------|------|
| 派发任务前 | 必须先核查 git 历史 + 操作记录 + 现有文件（R11 §3） |
| 完成任务后 | 立即 `git add 精确文件 → commit → push origin main` |
| 无变更 | 等待，不创建空提交 |
| 禁止 | `git add -A` / `--force` / `git worktree` / 分支切换 |

---

## 3. 操作记录（实时刷新）

每个小任务完成后 **5 分钟内**追加到 `操作记录.md`，包含：
- 轮次编号、交付文件、测试结果（精确数字）
- 规则依据、质量门禁达标声明
- **禁止**模糊描述，必须是实际数字

---

## 4. 禁止 fall-back（R03，强制）

- 业务流程跑不通 → 返回告警，不是返回假数据
- 所有 `except` 块必须 `raise` 或显式处理
- 禁止 `except: pass` / `return None` / `return []`

---

## 5. 学术诚信（R02，强制）

- 所有参数/公式必须有文献溯源（作者、年份、URL）
- 创新点标注 `*创新*` 并记录底层逻辑
- 禁止编造数据

---

## 6. 质量门禁（强制）

| 指标 | 限制 |
|------|------|
| 函数行数 | ≤ 80 |
| 文件行数 | ≤ 800 |
| 圈复杂度 | ≤ 15 |
| 测试覆盖率 | ≥ 90% |
| TODO/FIXME | 禁止残留 |

---

## 7. 代码规范

- 发现 Bug 立即修复，附回归测试
- 单文件只有一份，版本升级用 v1/v2/v3/v4，禁止多个版本并存
- 用中文回答，用中文注释

---

## 8. GPU 战略（不可撤销）

**不参与 GPU 计算**（项目所有者 2026-06-25 决策）。
- 禁止 CuPy/CUDA/ROCm/AppleMetal
- 纯 NumPy/SciPy/JAX(CPU) 实现

---

## 9. 磁盘空间

空间不足时删除：`swiftly`(6.5G) / `mise`(3.0G) / `rustup`(1.8G)

日志使用循环日志（10M 上限），详见 `scripts/logging_config.py`

---

## 10. 关键文件索引

| 文件 | 用途 |
|------|------|
| `操作记录.md` | 所有操作的工作记录 |
| `.trae/rules/R11-工作流规范.md` | V8 工作流完整规则 |
| `src/polaris/` | 项目源代码 |
| `scripts/auto_commit.py V8` | 自动提交守护（6 分钟轮询） |
| `scripts/keepalive.sh` | 保活脚本（5 分钟 touch） |
