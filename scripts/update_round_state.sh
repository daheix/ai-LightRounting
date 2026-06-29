#!/bin/bash
# 更新轮次状态文件（每轮开始/结束时调用）
# 用法: bash scripts/update_round_state.sh R6 扫描中 1 2 3 "执行 R6 排查清单"

STATE_DIR="/tmp/polaris_round_state"
mkdir -p "$STATE_DIR"

ROUND="${1:-R6}"
STATUS="${2:-扫描中}"
P0="${3:-0}"
P1="${4:-0}"
P2="${5:-0}"
NEXT="${6:-执行下一轮排查}"
FALLBACK="${7:-80}"

echo "$ROUND" > "$STATE_DIR/current_round"
echo "$STATUS" > "$STATE_DIR/status"
echo "$P0" > "$STATE_DIR/p0_count"
echo "$P1" > "$STATE_DIR/p1_count"
echo "$P2" > "$STATE_DIR/p2_count"
echo "$NEXT" > "$STATE_DIR/next_action"
echo "$FALLBACK" > "$STATE_DIR/fallback_total"

echo "[$(date '+%H:%M:%S')] 状态已更新: $ROUND | $STATUS | P0=$P0 P1=$P1 P2=$P2"
