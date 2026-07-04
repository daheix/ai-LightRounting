#!/usr/bin/env bash
# scripts/imv5_onekey.sh — PoLaRIS LR 工具商用版一键启动
#
# 功能（一条命令完成）:
#   1. 环境自举（init.sh --no-daemon，幂等）
#   2. 守护进程（auto_commit 9min + keepalive 5min）
#   3. 确认 1000+ 测试用例（不足则生成）
#   4. Web 大屏（port 8000，polaris_gui.web_server）
#   5. 批量端到端测试（batch_test_1000_circuits.py --resume 断点续跑）
#   6. 前台循环 sleep 100 汇报测试进展（直到测试结束）
#
# 用法:
#   bash scripts/imv5_onekey.sh            # 完整启动 + 循环汇报
#   bash scripts/imv5_onekey.sh --no-test  # 只启动服务不跑测试
#
# 规则依据: R03 禁止 fall-back / R04 CPU 强制 / R11 工作流 / R10 进度汇报
set -euo pipefail

WORKSPACE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${WORKSPACE}"

NO_TEST=0
[ "${1:-}" = "--no-test" ] && NO_TEST=1

fail() { echo "[onekey][ERROR] $*" >&2; exit 1; }
log() { echo "[onekey] $(date '+%H:%M:%S') $*"; }

# ============================================================
# 步骤 1: 环境自举（幂等）
# ============================================================
log "[1/5] 环境自举..."
if [ ! -f /tmp/.polaris_installed ]; then
    bash "${WORKSPACE}/init.sh" --no-daemon
fi
# shellcheck disable=SC1091
source "${WORKSPACE}/3dtool/env.sh"
[ -n "${THREEDTOOL_PYTHON:-}" ] || fail "THREEDTOOL_PYTHON 未设置"
log "  Python: ${THREEDTOOL_PYTHON}"

# ============================================================
# 步骤 2: 守护进程
# ============================================================
log "[2/5] 守护进程..."
if ! pgrep -f "auto_commit.*V8" >/dev/null 2>&1; then
    nohup "${THREEDTOOL_PYTHON}" "${WORKSPACE}/scripts/auto_commit.py" V8 >/dev/null 2>&1 &
    log "  auto_commit 已启动（9min 轮询）"
fi
if ! pgrep -f "keepalive.sh" >/dev/null 2>&1; then
    nohup bash "${WORKSPACE}/scripts/keepalive.sh" >/dev/null 2>&1 &
    log "  keepalive 已启动（5min touch）"
fi

# ============================================================
# 步骤 3: 确认 1000+ 测试用例
# ============================================================
log "[3/5] 确认测试用例..."
GEN_DIR="${WORKSPACE}/data/benchmarks/generated"
CIRCUIT_COUNT=$(find "${GEN_DIR}" -name "*.json" ! -name "index.json" 2>/dev/null | wc -l)
if [ "${CIRCUIT_COUNT}" -lt 1000 ]; then
    log "  现有 ${CIRCUIT_COUNT} < 1000，生成中..."
    "${THREEDTOOL_PYTHON}" "${WORKSPACE}/scripts/generate_1000_circuits.py" \
        --topology all --scale XS,S,M,L,XL --platform SOI,SiN,InP,LNOI --seed 42
    CIRCUIT_COUNT=$(find "${GEN_DIR}" -name "*.json" ! -name "index.json" 2>/dev/null | wc -l)
fi
log "  测试用例: ${CIRCUIT_COUNT} 个"

# ============================================================
# 步骤 4: Web 大屏（port 8000）
# ============================================================
log "[4/5] Web 大屏..."
if ! pgrep -f "polaris_gui.web_server" >/dev/null 2>&1; then
    nohup "${THREEDTOOL_PYTHON}" -m polaris_gui.web_server >/dev/null 2>&1 &
    log "  Web UI 已启动: http://0.0.0.0:8000"
fi

# ============================================================
# 步骤 5: 批量端到端测试（--resume 断点续跑）
# ============================================================
BATCH_DIR="${WORKSPACE}/out/batch_test"
PROGRESS_FILE="${BATCH_DIR}/progress.json"
if [ "${NO_TEST}" = "0" ]; then
    log "[5/5] 批量测试启动（--resume 断点续跑）..."
    if ! pgrep -f "batch_test_1000_circuits" >/dev/null 2>&1; then
        nohup "${THREEDTOOL_PYTHON}" "${WORKSPACE}/scripts/batch_test_1000_circuits.py" \
            --resume >/dev/null 2>&1 &
        log "  测试进程已启动 PID=$!"
    fi
fi

# ============================================================
# 循环 sleep 100 汇报进展（直到测试结束）
# ============================================================
log ""
log "=========================================="
log "  PoLaRIS LR 商用版一键启动完成"
log "  Web 大屏: http://0.0.0.0:8000"
log "  测试用例: ${CIRCUIT_COUNT}"
log "  开始循环汇报（每 100 秒）"
log "=========================================="

if [ "${NO_TEST}" = "1" ]; then
    log "--no-test 模式，退出循环汇报"
    exit 0
fi

ROUND=0
while true; do
    sleep 100
    ROUND=$((ROUND + 1))
    echo ""
    echo "[汇报 #${ROUND}] $(date '+%Y-%m-%d %H:%M:%S CST')"
    
    # 测试进度
    if [ -f "${PROGRESS_FILE}" ]; then
        "${THREEDTOOL_PYTHON}" -c "
import json
from pathlib import Path
try:
    d = json.loads(Path('${PROGRESS_FILE}').read_text())
    total = d.get('total', 0)
    results = d.get('results', [])
    done = len(results)
    succ = sum(1 for r in results if isinstance(r, dict) and r.get('success'))
    fail = done - succ
    drc = sum(1 for r in results if isinstance(r, dict) and r.get('drc_passed'))
    pct = (done/total*100) if total else 0
    print(f'  测试进度: {done}/{total} ({pct:.1f}%) 成功={succ} 失败={fail} DRC通过={drc}')
except Exception as e:
    print(f'  读进度失败: {e}')
" 2>&1
    else
        echo "  进度文件尚未生成（测试可能正在初始化）"
    fi
    
    # 磁盘
    disk_info=$(df -h /workspace | tail -1 | awk '{print $4 " 可用 (" $5 " 使用)"}')
    echo "  磁盘: ${disk_info}"
    
    # 测试进程是否存活
    if pgrep -f "batch_test_1000_circuits" >/dev/null 2>&1; then
        echo "  测试进程: 运行中"
    else
        echo "  测试进程: 已结束"
        if [ -f "${PROGRESS_FILE}" ]; then
            echo "  最终状态:"
            "${THREEDTOOL_PYTHON}" -c "
import json
from pathlib import Path
d = json.loads(Path('${PROGRESS_FILE}').read_text())
total = d.get('total', 0)
results = d.get('results', [])
done = len(results)
succ = sum(1 for r in results if isinstance(r, dict) and r.get('success'))
drc = sum(1 for r in results if isinstance(r, dict) and r.get('drc_passed'))
print(f'    完成: {done}/{total}')
print(f'    成功: {succ}  失败: {done-succ}  DRC通过: {drc}')
" 2>&1
        fi
        echo "[onekey] 测试结束，退出循环"
        break
    fi
done
