// PoLaRIS Web UI 前端逻辑

let selectedPreset = null;
let presets = [];

// 加载预设电路列表
async function loadPresets() {
  try {
    const resp = await fetch('/api/presets');
    const data = await resp.json();
    presets = data.presets || [];
    renderPresets();
  } catch (e) {
    document.getElementById('presets').innerHTML =
      '<div class="error-box">加载预设失败: ' + e.message + '</div>';
  }
}

function renderPresets() {
  const container = document.getElementById('presets');
  if (presets.length === 0) {
    container.innerHTML = '<div class="loading">无可用预设</div>';
    return;
  }
  container.innerHTML = presets.map(p => `
    <div class="preset-card" data-id="${p.id}" onclick="selectPreset('${p.id}')">
      <h4>${p.name}</h4>
      <p>${p.description}</p>
      <div class="preset-meta">
        <span>${p.devices} 器件</span>
        <span>${p.platform}</span>
      </div>
    </div>
  `).join('');
}

function selectPreset(id) {
  selectedPreset = id;
  document.querySelectorAll('.preset-card').forEach(card => {
    card.classList.toggle('selected', card.dataset.id === id);
  });
  document.getElementById('runBtn').disabled = false;
}

// 运行布局布线流水线
async function runPipeline() {
  if (!selectedPreset) return;
  const routerType = document.getElementById('routerType').value;
  const btn = document.getElementById('runBtn');
  btn.disabled = true;
  btn.classList.add('loading');
  btn.textContent = '运行中...';
  document.getElementById('errorPanel').style.display = 'none';
  document.getElementById('resultPanel').style.display = 'none';

  try {
    const resp = await fetch('/api/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ preset: selectedPreset, router_type: routerType }),
    });
    const data = await resp.json();
    if (!data.success) {
      throw new Error(data.error || '运行失败');
    }
    renderResult(data.result);
  } catch (e) {
    document.getElementById('errorContent').textContent = e.message;
    document.getElementById('errorPanel').style.display = 'block';
  } finally {
    btn.disabled = false;
    btn.classList.remove('loading');
    btn.textContent = '一键布局布线';
  }
}

function renderResult(result) {
  const panel = document.getElementById('resultPanel');
  panel.style.display = 'block';

  // 统计卡片
  const drcClass = result.drc_passed ? 'success' : 'error';
  const successClass = result.success ? 'success' : 'error';
  document.getElementById('statsGrid').innerHTML = `
    <div class="stat-card ${successClass}">
      <span class="stat-value">${result.success ? '✓ 成功' : '✗ 失败'}</span>
      <div class="stat-label">运行状态</div>
    </div>
    <div class="stat-card">
      <span class="stat-value">${result.n_devices}</span>
      <div class="stat-label">器件数</div>
    </div>
    <div class="stat-card">
      <span class="stat-value">${result.n_paths}</span>
      <div class="stat-label">布线数</div>
    </div>
    <div class="stat-card">
      <span class="stat-value">${result.total_loss_db.toFixed(2)}</span>
      <div class="stat-label">总损耗 (dB)</div>
    </div>
    <div class="stat-card">
      <span class="stat-value">${result.n_crossings}</span>
      <div class="stat-label">交叉数</div>
    </div>
    <div class="stat-card ${drcClass}">
      <span class="stat-value">${result.drc_passed ? '✓ 通过' : '✗ 违规'}</span>
      <div class="stat-label">DRC 检查</div>
    </div>
  `;

  // 路径表格
  const tbody = document.getElementById('pathsBody');
  if (result.paths && result.paths.length > 0) {
    tbody.innerHTML = result.paths.map(p => `
      <tr>
        <td>${p.connection}</td>
        <td>${p.length_um.toFixed(1)}</td>
        <td>${p.loss_db.toFixed(3)}</td>
        <td>${p.points.length}</td>
      </tr>
    `).join('');
  } else {
    tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;color:#94a3b8;">无布线路径</td></tr>';
  }

  // Canvas 可视化
  drawLayout(result);
  panel.scrollIntoView({ behavior: 'smooth' });
}

function drawLayout(result) {
  const canvas = document.getElementById('layoutCanvas');
  const ctx = canvas.getContext('2d');
  const W = canvas.width;
  const H = canvas.height;

<<<<<<< HEAD
  // 深色主题画布背景
  ctx.fillStyle = '#0a0e14';
  ctx.fillRect(0, 0, W, H);

  if (!result.placements || result.placements.length === 0) {
    ctx.fillStyle = '#64748b';
=======
  ctx.fillStyle = '#fafbfc';
  ctx.fillRect(0, 0, W, H);

  if (!result.placements || result.placements.length === 0) {
    ctx.fillStyle = '#94a3b8';
>>>>>>> trae/solo-agent-pkVjID
    ctx.font = '14px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('无布局数据', W / 2, H / 2);
    return;
  }

  // 计算缩放比例（画布坐标 → Canvas 像素）
  const canvasW = result.canvas_w || 1000;
  const canvasH = result.canvas_h || 1000;
  const margin = 20;
  const scaleX = (W - 2 * margin) / canvasW;
  const scaleY = (H - 2 * margin) / canvasH;
  const scale = Math.min(scaleX, scaleY);
  const offsetX = (W - canvasW * scale) / 2;
  const offsetY = (H - canvasH * scale) / 2;

<<<<<<< HEAD
  // 绘制画布边界（深色主题）
  ctx.strokeStyle = '#2d3748';
  ctx.lineWidth = 1;
  ctx.strokeRect(offsetX, offsetY, canvasW * scale, canvasH * scale);

  // 绘制布线路径（先画路径，再画器件覆盖）— 深色主题亮色路径
  const colors = ['#60a5fa', '#f87171', '#34d399', '#fbbf24', '#a78bfa', '#22d3ee'];
=======
  // 绘制画布边界
  ctx.strokeStyle = '#cbd5e1';
  ctx.lineWidth = 1;
  ctx.strokeRect(offsetX, offsetY, canvasW * scale, canvasH * scale);

  // 绘制布线路径（先画路径，再画器件覆盖）
  const colors = ['#2d5aa0', '#dc2626', '#16a34a', '#d97706', '#7c3aed', '#0891b2'];
>>>>>>> trae/solo-agent-pkVjID
  if (result.paths) {
    result.paths.forEach((path, i) => {
      const color = colors[i % colors.length];
      ctx.strokeStyle = color;
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      const pts = path.points || [];
      pts.forEach((pt, j) => {
        const x = offsetX + pt[0] * scale;
        const y = offsetY + pt[1] * scale;
        if (j === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      });
      ctx.stroke();
    });
  }

<<<<<<< HEAD
  // 绘制器件（深色主题）
=======
  // 绘制器件
>>>>>>> trae/solo-agent-pkVjID
  ctx.font = '10px sans-serif';
  ctx.textAlign = 'center';
  result.placements.forEach(pl => {
    const x = offsetX + pl.x * scale;
    const y = offsetY + pl.y * scale;
    const w = pl.w * scale;
    const h = pl.h * scale;
<<<<<<< HEAD
    ctx.fillStyle = '#1e3a5f';
    ctx.fillRect(x, y, Math.max(w, 2), Math.max(h, 2));
    ctx.strokeStyle = '#3b82f6';
    ctx.lineWidth = 0.5;
    ctx.strokeRect(x, y, Math.max(w, 2), Math.max(h, 2));
    if (w > 30 && h > 12) {
      ctx.fillStyle = '#f1f5f9';
=======
    ctx.fillStyle = '#1a365d';
    ctx.fillRect(x, y, Math.max(w, 2), Math.max(h, 2));
    ctx.strokeStyle = '#0f172a';
    ctx.lineWidth = 0.5;
    ctx.strokeRect(x, y, Math.max(w, 2), Math.max(h, 2));
    if (w > 30 && h > 12) {
      ctx.fillStyle = 'white';
>>>>>>> trae/solo-agent-pkVjID
      ctx.fillText(pl.name, x + w / 2, y + h / 2 + 3);
    }
  });
}

// 初始化
document.getElementById('runBtn').addEventListener('click', runPipeline);
loadPresets();
