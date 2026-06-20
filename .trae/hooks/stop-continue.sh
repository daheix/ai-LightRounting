#!/usr/bin/env bash
# Stop Hook：检查是否还有未完成任务，如有则阻断停止并让 AI 继续。
#
# 触发时机：智能体完成输出、准备结束当前 Query 时。
# 行为：
#   - 检查项目中是否有未完成的 todo/任务标记
#   - 若有未完成任务 → 输出 JSON {"continue":false,"reason":"..."} 阻断停止
#   - 若所有任务完成 → 输出纯文本提示（不阻断），允许停止
#
# TRAE Hook 输出规范（与 Claude Code 不同）:
#   - 阻断停止: {"continue": false, "reason": "..."}
#   - 允许停止: 纯文本或 {"continue": true}
#
# 来源:
# - TRAE Hook 实战: https://cloud.tencent.com/developer/article/2689656
# - TRAE Stop 阻断格式: https://forum.trae.cn/t/topic/30024
# - TRAE Hook 配置: https://docs.trae.cn/ide/hook-configuration-reference

set -euo pipefail

# 读取 stdin（TRAE 传入的 JSON 上下文，可选读取）
INPUT=$(cat || true)

# 项目根目录（TRAE 注入 CLAUDE_PROJECT_DIR 环境变量，回退到 cwd）
PROJECT_ROOT="${CLAUDE_PROJECT_DIR:-$(pwd)}"

# 检查是否有未完成的任务标记
has_unfinished_tasks() {
    # 1. 检查 roadmap 中的未完成阶段标记（⬜ 或 🔄）
    local roadmap="$PROJECT_ROOT/docs/industry_alignment_roadmap.md"
    if [ -f "$roadmap" ]; then
        if grep -qE '⬜|🔄' "$roadmap" 2>/dev/null; then
            return 0
        fi
    fi

    # 2. 检查 spec/tasks.md 中是否有未完成任务（[ ] 或 pending 或 in_progress）
    local tasks_dir="$PROJECT_ROOT/.trae/specs"
    if [ -d "$tasks_dir" ]; then
        if grep -rqE '\[ \]|pending|in_progress' "$tasks_dir" 2>/dev/null; then
            return 0
        fi
    fi

    # 3. 检查操作记录中最近的 todo 是否有 pending/in_progress
    local record="$PROJECT_ROOT/操作记录.md"
    if [ -f "$record" ]; then
        if tail -100 "$record" | grep -qE 'pending|in_progress|⬜|🔄' 2>/dev/null; then
            return 0
        fi
    fi

    return 1
}

# 主逻辑
if has_unfinished_tasks; then
    # 阻断停止：返回 JSON continue=false，AI 会继续执行
    # 注意：TRAE 用 continue:false（不是 Claude Code 的 decision:block）
    cat <<'EOF'
{"continue": false, "reason": "检测到项目中仍有未完成的任务（roadmap 中存在 ⬜/🔄 标记或 tasks.md 中有未完成项）。请阅读整个项目的 md 文档和代码，参考网络上的最新实现，继续完成产品到商业化交付。不要停止，继续执行下一个未完成任务。"}
EOF
else
    # 允许停止：输出纯文本提示（作为附加上下文，不阻断）
    echo "所有任务已完成。如需继续推进商业化交付，请阅读 docs/industry_alignment_roadmap.md 并启动新阶段。"
fi
