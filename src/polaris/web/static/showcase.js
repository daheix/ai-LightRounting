// PoLaRIS 端到端 Demo Showcase 前端逻辑
// 9 阶段定义（与后端 _SHOWCASE_STAGES 对齐）
const STAGES = [
    {id: 1, name: "PDK 器件目录展示"},
    {id: 2, name: "电路规格定义"},
    {id: 3, name: "AI 布局"},
    {id: 4, name: "智能布线"},
    {id: 5, name: "仿真验证"},
    {id: 6, name: "DRC/LVS 验证"},
    {id: 7, name: "GDS 导出"},
    {id: 8, name: "光电协同"},
    {id: 9, name: "量子光子验证"},
];

// 状态图标映射
const STATUS_ICONS = {
    pending: "⏳",
    running: "🔄",
    done: "✅",
    failed: "❌",
};

// 全局状态
let currentRunId = null;
let pollInterval = null;
const POLL_INTERVAL_MS = 1000;

// 初始化：渲染阶段卡片
function renderStageCards() {
    const grid = document.getElementById("stages-grid");
    grid.innerHTML = STAGES.map(s => `
        <div class="stage-card pending" data-stage="${s.id}">
            <div class="stage-header">
                <span class="stage-id">${s.id}</span>
                <span class="stage-name">${s.name}</span>
                <span class="stage-status">${STATUS_ICONS.pending}</span>
            </div>
            <div class="stage-body">
                <div class="stage-duration">—</div>
                <div class="stage-output">等待启动</div>
            </div>
        </div>
    `).join("");
}

// 启动 Showcase
async function startShowcase() {
    const btn = document.getElementById("run-btn");
    btn.disabled = true;
    btn.textContent = "启动中...";
    document.getElementById("error-panel").style.display = "none";

    try {
        const resp = await fetch("/api/showcase/run", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({output_dir: "out/e2e_showcase_web"}),
        });
        const data = await resp.json();
        if (!data.success) {
            throw new Error(data.error || "启动失败");
        }
        currentRunId = data.run_id;
        document.getElementById("run-status").textContent = "运行中: " + currentRunId;
        document.getElementById("log-output").textContent = "Showcase 已启动，等待阶段日志...\n";
        // 重置所有卡片为 pending
        renderStageCards();
        // 开始轮询
        pollInterval = setInterval(pollProgress, POLL_INTERVAL_MS);
    } catch (e) {
        document.getElementById("error-content").textContent = e.message;
        document.getElementById("error-panel").style.display = "block";
    } finally {
        btn.disabled = false;
        btn.textContent = "启动 Showcase";
    }
}

// 轮询进度
async function pollProgress() {
    if (!currentRunId) return;
    try {
        const resp = await fetch(`/api/showcase/report/${currentRunId}`);
        const data = await resp.json();
        if (!data.success) {
            throw new Error(data.error || "查询失败");
        }
        // 更新阶段卡片
        data.stages.forEach(stage => updateStageCard(stage));
        // 更新汇总统计
        updateSummary(data.summary);
        // 更新日志流
        updateLogStream(data);
        // 检查是否完成
        if (data.status === "done" || data.status === "failed") {
            clearInterval(pollInterval);
            pollInterval = null;
            const statusText = data.status === "done" ? "完成" : "失败";
            document.getElementById("run-status").textContent = statusText + ": " + currentRunId;
            if (data.status === "failed" && data.error) {
                document.getElementById("error-content").textContent = data.error;
                document.getElementById("error-panel").style.display = "block";
            }
        }
    } catch (e) {
        document.getElementById("error-content").textContent = "轮询失败: " + e.message;
        document.getElementById("error-panel").style.display = "block";
    }
}

// 更新单个阶段卡片
function updateStageCard(stage) {
    const card = document.querySelector(`[data-stage="${stage.stage_id}"]`);
    if (!card) return;
    const statusEl = card.querySelector(".stage-status");
    const durationEl = card.querySelector(".stage-duration");
    const outputEl = card.querySelector(".stage-output");

    // 状态图标
    statusEl.textContent = STATUS_ICONS[stage.status] || STATUS_ICONS.pending;
    // 耗时
    durationEl.textContent = stage.duration_s ? `${stage.duration_s.toFixed(2)}s` : "—";
    // 输出摘要（截断到 200 字符避免溢出）
    if (stage.outputs && Object.keys(stage.outputs).length > 0) {
        const text = JSON.stringify(stage.outputs, null, 2);
        outputEl.textContent = text.length > 200 ? text.substring(0, 200) + "..." : text;
    } else if (stage.error) {
        outputEl.textContent = "错误: " + stage.error;
    }
    // 卡片状态色
    card.className = `stage-card ${stage.status}`;
}

// 更新汇总统计
function updateSummary(summary) {
    if (!summary) return;
    document.getElementById("stat-done").textContent = summary.n_done || 0;
    document.getElementById("stat-failed").textContent = summary.n_failed || 0;
    document.getElementById("stat-total").textContent = summary.n_total || 0;
    document.getElementById("stat-duration").textContent =
        summary.total_duration_s != null ? summary.total_duration_s.toFixed(2) : "—";
}

// 更新日志流
function updateLogStream(data) {
    const logEl = document.getElementById("log-output");
    const lines = data.stages.map(s => {
        const dur = s.duration_s ? s.duration_s.toFixed(2) : "0.00";
        return `[${s.status.toUpperCase()}] 阶段 ${s.stage_id}: ${s.stage_name} (${dur}s)`;
    });
    if (lines.length === 0) {
        logEl.textContent = "等待阶段日志...";
    } else {
        logEl.textContent = lines.join("\n");
    }
}

// 初始化
renderStageCards();
document.getElementById("run-btn").addEventListener("click", startShowcase);
