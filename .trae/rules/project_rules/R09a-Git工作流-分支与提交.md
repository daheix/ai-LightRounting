# 规则 R09：Git 工作流与团队协作规范（强制）— 分支与提交

## 9.1 分支策略

采用 **GitHub Flow**（简化版，适合持续部署）：

| 分支 | 用途 | 保护规则 |
|------|------|----------|
| `main` | 生产就绪代码 | 禁止直接推送，需 CI 通过 + 代码审查 |
| `feature/<name>` | 新功能开发 | 从 `main` 拉出，完成后 PR 合并回 `main` |
| `fix/<name>` | Bug 修复 | 从 `main` 拉出，修复后 PR 合并回 `main` |
| `hotfix/<name>` | 紧急生产修复 | 从 `main` 拉出，优先合并 |

分支命名规范：`feature/s-parameter-cascade`、`fix/euler-bend-first-point`、`hotfix/grid-index-out-of-bounds`

来源: GitHub Flow https://docs.github.com/en/get-started/quickstart/github-flow | Git Best Practices https://devtoolhub.com/git-best-practices-branching-approvals/

## 9.2 提交规范（Conventional Commits）

提交消息格式：`<type>: <简述>`

| type | 用途 |
|------|------|
| `feat` | 新功能 |
| `fix` | Bug 修复 |
| `docs` | 文档变更 |
| `refactor` | 重构（不改变功能） |
| `test` | 测试相关 |
| `chore` | 构建/工具/依赖变更 |
| `perf` | 性能优化 |
| `style` | 代码格式（不影响功能） |

规范：简述不超过 50 字符，使用祈使句（"添加"而非"添加了"）；复杂变更用 HEREDOC 添加正文说明"为什么"；一个提交只做一件事，禁止混合不相关变更。

来源: Conventional Commits https://www.conventionalcommits.org/
