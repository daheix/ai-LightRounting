#!/bin/bash
# 自动合并脚本：每20分钟将 trae/solo-agent-fk2qDL 合并到 main
# 按标准流程：fetch → merge → push，冲突时跳过并记录日志
# 来源: GitHub Flow https://docs.github.com/en/get-started/quickstart/github-flow

set -u
INTERVAL=1200  # 20分钟（用户规则：自动提交代码间隔）
DEV_BRANCH="trae/solo-agent-fk2qDL"
MAIN_BRANCH="main"
LOG_FILE="/workspace/checkpoints/rl_2m/auto_merge.log"
LOCK_FILE="/workspace/.git/index.lock"
LOCK_WAIT_MAX=60  # 最多等待 lock 60秒

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

wait_for_lock() {
    local waited=0
    while [ -f "$LOCK_FILE" ] && [ $waited -lt $LOCK_WAIT_MAX ]; do
        sleep 2
        waited=$((waited + 2))
    done
    if [ -f "$LOCK_FILE" ]; then
        log "WARNING: lock 仍存在（等待 ${waited}s），强制删除"
        rm -f "$LOCK_FILE"
    fi
}

while true; do
    log "=== 开始自动合并周期 ==="

    # 等待 git lock 释放（训练进程可能正在 commit）
    wait_for_lock

    # 1. 切换到 main
    git checkout "$MAIN_BRANCH" >> "$LOG_FILE" 2>&1
    if [ $? -ne 0 ]; then
        log "ERROR: 切换到 $MAIN_BRANCH 失败，跳过本次"
        sleep "$INTERVAL"
        continue
    fi

    # 2. 拉取远端 main 最新
    wait_for_lock
    git fetch origin "$MAIN_BRANCH" >> "$LOG_FILE" 2>&1
    git pull origin "$MAIN_BRANCH" >> "$LOG_FILE" 2>&1
    if [ $? -ne 0 ]; then
        log "WARNING: pull main 失败，尝试 reset 到 origin/main"
        wait_for_lock
        git reset --hard "origin/$MAIN_BRANCH" >> "$LOG_FILE" 2>&1
    fi

    # 3. 拉取开发分支最新
    wait_for_lock
    git fetch origin "$DEV_BRANCH" >> "$LOG_FILE" 2>&1

    # 4. 检查开发分支是否有新提交
    LOCAL_MAIN=$(git rev-parse "$MAIN_BRANCH")
    REMOTE_DEV=$(git rev-parse "origin/$DEV_BRANCH")
    MERGE_BASE=$(git merge-base "$MAIN_BRANCH" "origin/$DEV_BRANCH")

    if [ "$REMOTE_DEV" = "$MERGE_BASE" ]; then
        log "开发分支无新提交，跳过合并"
    else
        log "开发分支有新提交，开始合并: $REMOTE_DEV"

        # 5. 合并开发分支（使用 --no-edit 避免交互）
        wait_for_lock
        git merge "$DEV_BRANCH" --no-edit >> "$LOG_FILE" 2>&1
        if [ $? -ne 0 ]; then
            log "ERROR: 合并冲突，中止合并并跳过本次"
            wait_for_lock
            git merge --abort >> "$LOG_FILE" 2>&1
            wait_for_lock
            git checkout "$DEV_BRANCH" >> "$LOG_FILE" 2>&1
            sleep "$INTERVAL"
            continue
        fi

        # 6. 推送到远端 main
        wait_for_lock
        git push origin "$MAIN_BRANCH" >> "$LOG_FILE" 2>&1
        if [ $? -ne 0 ]; then
            log "ERROR: push main 失败"
        else
            log "OK: 合并并推送成功"
        fi
    fi

    # 7. 切回开发分支，继续开发
    wait_for_lock
    git checkout "$DEV_BRANCH" >> "$LOG_FILE" 2>&1

    log "=== 周期结束，等待 ${INTERVAL}s ==="
    sleep "$INTERVAL"
done
