#!/usr/bin/env bash
# 保活脚本（规则 23，强制，最高优先级）
#
# 作用：
#   1. 每 5 分钟（300s）touch 标记文件，防止会话超时断开
#   2. 每 15 分钟（900s）向前台发送进度消息：
#      "继续加油完成剩余任务"
#
# 启动方式（后台守护）：
#   nohup bash scripts/keepalive.sh > /dev/null 2>&1 &
#
# 输出文件：
#   /tmp/keepalive.log          — 全量保活日志（每次 touch + 每次消息）
#   /tmp/keepalive_marker       — touch 标记文件（最近 touch 时间）
#   /tmp/keepalive_message.txt  — 最近一次发送的前台消息（覆盖写）
#
# 来源:
# - AGENTS.md §2 保活脚本（规则 23）
# - 用户指示 2026-07-01：保活改为每 15 分钟发"继续加油完成剩余任务"
# - TRAE Stop 阻断格式: https://forum.trae.cn/t/topic/30024

set -uo pipefail

LOG="/tmp/keepalive.log"
MARKER="/tmp/keepalive_marker"
MSG_FILE="/tmp/keepalive_message.txt"
INTERVAL_TOUCH=300    # 5 分钟 touch 一次（防会话超时）
INTERVAL_MSG=900      # 15 分钟发一次消息（15 * 60 = 900s）
MSG="继续加油完成剩余任务"

last_msg_time=0

while true; do
    now=$(date +%s)
    # 1. 保活：touch 标记文件
    date >> "$LOG"
    touch "$MARKER"

    # 2. 每 15 分钟向前台发送进度消息
    if (( now - last_msg_time >= INTERVAL_MSG )); then
        ts=$(date '+%Y-%m-%d %H:%M:%S')
        echo "[$ts] $MSG" >> "$LOG"
        echo "$MSG" > "$MSG_FILE"
        # 向前台输出（若 nohup 未重定向 stdout，则直接显示在终端）
        echo "$MSG"
        last_msg_time=$now
    fi

    sleep "$INTERVAL_TOUCH"
done
