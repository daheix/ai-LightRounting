#!/usr/bin/env bash
# PoLaRIS 质量门禁 pre-commit hook
#
# 功能: 提交前自动运行质量门禁检查，不通过则阻止提交
# 指标: 流水线成功率、DRC通过率、布线成功率、损耗、耗时
# 逻辑: 当前指标 < 基准则阻止提交; > 基准则自动刷新基准
#
# 安装: cp scripts/quality_gate_pre_commit.sh .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit
# 跳过: git commit --no-verify (紧急情况, 不推荐)

set -e

REPO_DIR=$(git rev-parse --show-toplevel)
cd "$REPO_DIR"

# 跳过条件1: worktree 目录 (守护进程已在主仓库运行质量门禁, 无需重复)
case "$REPO_DIR" in
    /tmp/ai-polaris-autocommit*)
        echo "[quality_gate] worktree 目录, 跳过 (守护进程已在主仓库运行门禁)"
        exit 0
        ;;
esac

# 跳过条件2: 仅文档/配置变更时不运行门禁 (加速提交)
CHANGED_FILES=$(git diff --cached --name-only --diff-filter=ACM | grep -E '\.(py|json)$' | head -20)
if [ -z "$CHANGED_FILES" ]; then
    echo "[quality_gate] 仅非代码文件变更, 跳过质量门禁"
    exit 0
fi

echo "[quality_gate] 检测到代码变更, 运行质量门禁..."
echo "[quality_gate] 变更文件:"
echo "$CHANGED_FILES" | head -10 | sed 's/^/  /'

# 运行质量门禁检查
python scripts/quality_gate_baseline.py --check
RESULT=$?

if [ $RESULT -eq 0 ]; then
    echo "[quality_gate] 门禁通过, 允许提交"
    exit 0
else
    echo "[quality_gate] 门禁未通过, 禁止提交"
    echo "[quality_gate] 如需紧急提交, 使用: git commit --no-verify"
    exit 1
fi
