#!/usr/bin/env bash
# Stop Hook：检查是否还有未完成任务，如有则阻断停止并让 AI 继续。
#
# 触发时机：智能体完成输出、准备结束当前 Query 时。
# 行为：
#   - 检查项目中是否有未完成的 todo/任务标记
#   - 若有未完成任务 → 输出 JSON {"decision":"block","reason":"..."} 阻断停止
#   - 若所有任务完成 → 输出纯文本提示（不阻断），允许停止
#
# 来源:
# - TRAE Hook 规范: https://docs.trae.cn/ide/hook-configuration-reference
# - Claude Code Hooks 规范: https://docs.claude.com/en/docs/claude-code/hooks
# - Stop 事件可阻断: https://docs.trae.cn/ide/automate-actions-with-hooks

set -euo pipefail

# 读取 stdin（TRAE 传入的 JSON 上下文）
INPUT=$(cat || true)

# 检查操作记录中是否有"未完成"标记
# 例如：todo 列表中存在 "in_progress" 或 "pending" 状态
PROJECT_ROOT="${CLAUDE_PROJECT_DIR:-$(pwd)}"
RECORD_FILE="$PROJECT_ROOT/操作记录.md"

# 检查是否有未完成的阶段标记（roadmap 中的 ⬜ 或 🔄）
has_unfinished_tasks() {
    # 检查 roadmap 中的未完成阶段
    local roadmap="$PROJECT_ROOT/docs/industry_alignment_roadmap.md"
    if [ -f "$roadmap" ]; then
        if grep -qE '⬜|🔄|TODO|未完成|待实现' "$roadmap" 2>/dev/null; then
            return 0
        fi
    fi

    # 检查 spec/tasks.md 中是否有未完成任务
    local tasks_dir="$PROJECT_ROOT/.trae/specs"
    if [ -d "$tasks_dir" ]; then
        if grep -rqE '\[ \]|pending|in_progress' "$tasks_dir" 2>/dev/null; then
            return 0
        fi
    fi

    return 1
}

# 主逻辑
if has_unfinished_tasks; then
    # 阻断停止：返回 JSON decision=block，AI 会继续执行
    cat <<'EOF'
{
  "decision": "block",
  "reason": "检测到项目中仍有未完成的任务（roadmap 中存在 ⬜/🔄 标记或 tasks.md 中有未完成项）。请阅读整个项目的 md 文档和代码，参考网络上的最新实现，继续完成产品到商业化交付。不要停止，继续执行下一个未完成任务。"
}
EOF
else
    # 允许停止：输出纯文本提示（作为附加上下文，不阻断）
    echo "所有任务已完成。如需继续推进商业化交付，请阅读 docs/industry_alignment_roadmap.md 并启动新阶段。"
fi
