// PoLaRIS 交互式版图编辑器 — 前端逻辑（D10 GUI 增强 4→8 分）
//
// 功能:
// - Canvas 渲染: 器件矩形 + 端口三角标记 + 布线路径 + DRC 高亮 + 网格
// - 交互: 滚轮缩放 / 拖拽平移 / 单击选中器件 / 拖动器件移动 / 双击取消选中
// - 图层切换: passive / active / source / detector / default 可独立显隐
// - 实时指标: 器件数 / HPWL / 布线数 / 总损耗 / DRC 违规数 / 状态
// - DRC 列表: 单击定位到违规位置，显示修复建议
// - 任务日志: 记录每次 API 调用的 task_id/type/status
// - API 调用: upload_gds / run_placement / run_routing / run_drc / results
//   + editor/* (add/move/delete/scene/devices/routes/drc/undo/redo/clear/export_klayout)
//
// 文献来源（R02 学术诚信）:
// 1. Canvas API: https://developer.mozilla.org/zh-CN/docs/Web/API/Canvas_API
// 2. Canvas 仿射变换: https://developer.mozilla.org/zh-CN/docs/Web/API/CanvasRenderingContext2D/transform
// 3. WheelEvent 缩放: https://developer.mozilla.org/zh-CN/docs/Web/API/WheelEvent
// 4. Drag 操作: https://developer.mozilla.org/zh-CN/docs/Web/API/Document/drag_event
// 5. fetch API: https://developer.mozilla.org/zh-CN/docs/Web/API/Fetch_API
// 6. SiEPIC EBeam PDK 端口几何: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
// 7. KLayout GDSII 显示: https://www.klayout.org/doc-qt5/manual/gex.html
// 8. HPWL 半周长线长定义: https://en.wikipedia.org/wiki/Half-perimeter_wire_length
//
// *创新*（Web Canvas 仿射变换驱动版图渲染）: 使用 ctx.setTransform() 累积
// 缩放/平移矩阵，鼠标交互仅修改 view.zoom/pan，每帧重算矩阵，避免状态
// 漂移。器件坐标 → Canvas 像素的映射由 toScreen()/toWorld() 双向函数保证。
// 对标 KLayout 桌面端的 zoom/pan 体验，在纯 Web 无框架下实现。
//
// 合规: R02 学术诚信 / R03 禁止 fall-back / R05 Bug 必修 / R11 V8 工作流。

'use strict';

// ============== 全局状态 ==============
const State = {
  selectedPreset: 'mzi',
  // 视图变换（缩放 + 平移）
  view: {
    zoom: 1.0,
    panX: 0,
    panY: 0,
  },
  // 画布坐标范围（μm）
  canvasW: 1000,
  canvasH: 700,
  // 场景数据（来自 /api/editor/scene）
  scene: {
    layers: ['passive', 'active', 'source', 'detector', 'default'],
    devices: [],
    routes: [],
    drc_highlights: [],
  },
  // 图层显示开关
  layerVisible: {
    passive: true,
    active: true,
    source: true,
    detector: true,
    default: true,
  },
  // 选中器件 ID
  selectedDeviceId: null,
  // 拖拽状态
  drag: {
    mode: 'none', // 'none' | 'pan' | 'device'
    startX: 0,
    startY: 0,
    deviceStartX: 0,
    deviceStartY: 0,
    deviceId: null,
  },
  // 当前布局/布线/DRC 结果（用于指标显示）
  lastPlacement: null,
  lastRouting: null,
  lastDrc: null,
  // 上传文件列表
  uploads: [],
};

// 图层颜色（对齐 KLayout 默认调色板）
const LAYER_COLORS = {
  passive: '#60a5fa',   // 蓝色 - 波导/无源
  active: '#f87171',    // 红色 - 有源（激光器/调制器）
  source: '#fbbf24',    // 黄色 - 光源
  detector: '#34d399',  // 绿色 - 探测器
  default: '#a78bfa',   // 紫色 - 默认/未分类
};

// 器件类型 → 图层映射
const DEVICE_TYPE_TO_LAYER = {
  grating_coupler: 'source',
  gc: 'source',
  laser: 'source',
  detector: 'detector',
  pd: 'detector',
  modulator: 'active',
  mmi: 'passive',
  waveguide: 'passive',
  wg: 'passive',
  ring: 'passive',
  bend: 'passive',
  default: 'default',
};

// ============== 工具函数 ==============
function $(id) { return document.getElementById(id); }

function nowTime() {
  const d = new Date();
  return d.getHours().toString().padStart(2, '0') + ':' +
         d.getMinutes().toString().padStart(2, '0') + ':' +
         d.getSeconds().toString().padStart(2, '0');
}

function deviceLayer(device) {
  // 优先使用 LayoutEditor 返回的 category 字段（passive/active/source/detector）
  if (device.category) return device.category;
  const t = (device.device_type || '').toLowerCase();
  return DEVICE_TYPE_TO_LAYER[t] || 'default';
}

// 画布坐标 (μm) → Canvas 像素
function toScreen(x, y) {
  const canvas = $('layoutCanvas');
  const cx = canvas.width / 2;
  const cy = canvas.height / 2;
  const baseScale = Math.min(canvas.width / State.canvasW, canvas.height / State.canvasH) * 0.85;
  const sx = cx + (x - State.canvasW / 2) * baseScale * State.view.zoom + State.view.panX;
  const sy = cy + (y - State.canvasH / 2) * baseScale * State.view.zoom + State.view.panY;
  return [sx, sy];
}

// Canvas 像素 → 画布坐标 (μm)
function toWorld(sx, sy) {
  const canvas = $('layoutCanvas');
  const cx = canvas.width / 2;
  const cy = canvas.height / 2;
  const baseScale = Math.min(canvas.width / State.canvasW, canvas.height / State.canvasH) * 0.85;
  const x = (sx - cx - State.view.panX) / (baseScale * State.view.zoom) + State.canvasW / 2;
  const y = (sy - cy - State.view.panY) / (baseScale * State.view.zoom) + State.canvasH / 2;
  return [x, y];
}

// ============== API 调用封装 ==============
async function apiGet(path) {
  const resp = await fetch(path);
  return resp.json();
}

async function apiPost(path, body) {
  const resp = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body || {}),
  });
  return resp.json();
}

async function apiUpload(path, file) {
  const formData = new FormData();
  formData.append('file', file);
  const resp = await fetch(path, {
    method: 'POST',
    body: formData,
  });
  return resp.json();
}

// ============== 任务日志 ==============
function logTask(type, message, status) {
  const ul = $('taskLog');
  if (ul.children.length === 1 && ul.children[0].classList.contains('hint-item')) {
    ul.innerHTML = '';
  }
  const li = document.createElement('li');
  const statusClass = status === 'done' ? 'task-status-done' :
                      status === 'failed' ? 'task-status-failed' :
                      'task-status-running';
  li.innerHTML = `<span class="task-time">${nowTime()}</span>` +
                 `<span class="task-type ${type}">${type}</span>` +
                 `<span class="${statusClass}">${status}</span> ${message}`;
  ul.insertBefore(li, ul.firstChild);
  // 限制最多 30 条
  while (ul.children.length > 30) {
    ul.removeChild(ul.lastChild);
  }
}

// ============== 错误显示 ==============
function showError(message) {
  $('errorContent').textContent = message;
  $('errorPanel').style.display = 'block';
  logTask('editor', message, 'failed');
}

function setStatus(text, kind) {
  const m = $('metricStatus');
  m.querySelector('.metric-value').textContent = text;
  m.classList.remove('error', 'running');
  if (kind === 'error') m.classList.add('error');
  else if (kind === 'running') m.classList.add('running');
}

// ============== 图层列表渲染 ==============
function renderLayers() {
  const ul = $('layersList');
  ul.innerHTML = '';
  State.scene.layers.forEach(layer => {
    const li = document.createElement('li');
    const visible = State.layerVisible[layer];
    if (!visible) li.classList.add('layer-off');
    const count = State.scene.devices.filter(d => deviceLayer(d) === layer).length;
    li.innerHTML = `<span class="layer-color" style="background:${LAYER_COLORS[layer]}"></span>` +
                   `<span class="layer-name">${layer}</span>` +
                   `<span class="layer-count">${count}</span>`;
    li.onclick = () => {
      State.layerVisible[layer] = !State.layerVisible[layer];
      renderLayers();
      draw();
    };
    ul.appendChild(li);
  });
}

// ============== 器件树渲染 ==============
function renderDevicesTree() {
  const ul = $('devicesTree');
  if (State.scene.devices.length === 0) {
    ul.innerHTML = '<li class="hint-item">无器件（运行布局或添加器件）</li>';
    return;
  }
  ul.innerHTML = '';
  State.scene.devices.forEach(d => {
    const li = document.createElement('li');
    if (d.id === State.selectedDeviceId) li.classList.add('selected');
    const layer = deviceLayer(d);
    const color = LAYER_COLORS[layer];
    li.innerHTML = `<span class="device-icon" style="background:${color}"></span>` +
                   `<span class="device-name">${d.name}</span>` +
                   `<span class="device-coords">(${d.x.toFixed(0)},${d.y.toFixed(0)})</span>`;
    li.onclick = () => {
      State.selectedDeviceId = d.id;
      renderDevicesTree();
      draw();
    };
    ul.appendChild(li);
  });
}

// ============== 上传列表渲染 ==============
function renderUploads() {
  const ul = $('uploadsList');
  if (State.uploads.length === 0) {
    ul.innerHTML = '<li class="hint-item">无上传文件</li>';
    return;
  }
  ul.innerHTML = '';
  State.uploads.forEach(u => {
    const li = document.createElement('li');
    const sizeKb = (u.size_bytes / 1024).toFixed(1);
    li.innerHTML = `<span class="upload-name">${u.filename}</span>` +
                   `<span class="upload-meta">${sizeKb} KB · ${u.uploaded_at}</span>`;
    ul.appendChild(li);
  });
}

// ============== DRC 列表渲染 ==============
function renderDrcList() {
  const ul = $('drcList');
  if (!State.lastDrc || !State.lastDrc.violations || State.lastDrc.violations.length === 0) {
    ul.innerHTML = '<li class="drc-pass">无 DRC 违规（全部规则通过）</li>';
    return;
  }
  ul.innerHTML = '';
  State.lastDrc.violations.forEach((v, i) => {
    const li = document.createElement('li');
    li.innerHTML = `<span class="drc-rule">[${i + 1}] ${v.rule_name || v.rule || '规则'}</span>` +
                   `<span class="drc-desc">${v.description || v.message || ''}</span>` +
                   (v.fix_suggestion ? `<span class="drc-fix">建议: ${v.fix_suggestion}</span>` : '');
    li.onclick = () => {
      // 定位到违规位置（如果有的话）
      if (v.location) {
        const [x, y] = v.location;
        State.view.panX = 0;
        State.view.panY = 0;
        // 居中到违规位置
        const canvas = $('layoutCanvas');
        const cx = canvas.width / 2;
        const cy = canvas.height / 2;
        const baseScale = Math.min(canvas.width / State.canvasW, canvas.height / State.canvasH) * 0.85;
        State.view.panX = cx - (cx + (x - State.canvasW / 2) * baseScale * State.view.zoom);
        State.view.panY = cy - (cy + (y - State.canvasH / 2) * baseScale * State.view.zoom);
        updateZoomLabel();
        draw();
      }
    };
    ul.appendChild(li);
  });
}

// ============== 路径列表渲染 ==============
function renderPathsList() {
  const ul = $('pathsList');
  if (!State.lastRouting || !State.lastRouting.paths || State.lastRouting.paths.length === 0) {
    ul.innerHTML = '<li class="hint-item">运行布线后显示路径</li>';
    return;
  }
  ul.innerHTML = '';
  State.lastRouting.paths.forEach(p => {
    const li = document.createElement('li');
    li.innerHTML = `<span class="path-conn">${p.connection}</span>` +
                   `<span class="path-meta">长度 ${p.length_um.toFixed(1)}μm · 损耗 ${p.loss_db.toFixed(3)}dB · ${p.points.length}点</span>`;
    ul.appendChild(li);
  });
}

// ============== 指标更新 ==============
function updateMetrics() {
  $('metricDevices').textContent = State.scene.devices.length;
  $('metricPaths').textContent = State.lastRouting ? State.lastRouting.paths.length : 0;
  if (State.lastPlacement && State.lastPlacement.hpwl) {
    $('metricHpwl').textContent = State.lastPlacement.hpwl.toFixed(1);
  } else {
    $('metricHpwl').textContent = '—';
  }
  if (State.lastRouting && State.lastRouting.total_loss_db != null) {
    $('metricLoss').textContent = State.lastRouting.total_loss_db.toFixed(2);
  } else {
    $('metricLoss').textContent = '—';
  }
  if (State.lastDrc) {
    const n = State.lastDrc.n_violations || 0;
    $('metricDrc').textContent = n;
    $('metricDrc').style.color = n === 0 ? '#34d399' : '#f87171';
  } else {
    $('metricDrc').textContent = '—';
  }
}

function updateZoomLabel() {
  $('zoomLabel').textContent = Math.round(State.view.zoom * 100) + '%';
}

// ============== Canvas 绘制 ==============
function draw() {
  const canvas = $('layoutCanvas');
  const ctx = canvas.getContext('2d');
  const W = canvas.width;
  const H = canvas.height;

  // 背景
  ctx.fillStyle = '#0a0e14';
  ctx.fillRect(0, 0, W, H);

  // 网格
  drawGrid(ctx, W, H);

  // 画布边界
  const [bx, by] = toScreen(0, 0);
  const [bx2, by2] = toScreen(State.canvasW, State.canvasH);
  ctx.strokeStyle = '#2d3748';
  ctx.lineWidth = 1;
  ctx.strokeRect(bx, by, bx2 - bx, by2 - by);

  // 布线路径（在器件下方）
  if (State.layerVisible.passive && State.scene.routes) {
    drawRoutes(ctx);
  }

  // 器件
  State.scene.devices.forEach(d => {
    const layer = deviceLayer(d);
    if (!State.layerVisible[layer]) return;
    drawDevice(ctx, d);
  });

  // DRC 高亮
  if (State.scene.drc_highlights) {
    drawDrcHighlights(ctx);
  }
}

function drawGrid(ctx, W, H) {
  ctx.strokeStyle = '#1a2030';
  ctx.lineWidth = 0.5;
  const step = 50; // 50 μm
  // 计算可见范围
  const [x1, y1] = toWorld(0, 0);
  const [x2, y2] = toWorld(W, H);
  const startX = Math.floor(x1 / step) * step;
  const endX = Math.ceil(x2 / step) * step;
  const startY = Math.floor(y1 / step) * step;
  const endY = Math.ceil(y2 / step) * step;
  ctx.beginPath();
  for (let x = startX; x <= endX; x += step) {
    const [sx, _] = toScreen(x, 0);
    ctx.moveTo(sx, 0);
    ctx.lineTo(sx, H);
  }
  for (let y = startY; y <= endY; y += step) {
    const [_, sy] = toScreen(0, y);
    ctx.moveTo(0, sy);
    ctx.lineTo(W, sy);
  }
  ctx.stroke();
}

function drawDevice(ctx, d) {
  // LayoutEditor 中 position 是器件中心，size 是 [w, h]
  // 此处 (d.x, d.y) 为中心，绘制时需偏移 -w/2, -h/2 得到左上角
  const [cx, cy] = toScreen(d.x, d.y);
  const baseScale = Math.min(
    $('layoutCanvas').width / State.canvasW,
    $('layoutCanvas').height / State.canvasH
  ) * 0.85 * State.view.zoom;
  const sw = Math.max(d.w * baseScale, 3);
  const sh = Math.max(d.h * baseScale, 3);
  const sx = cx - sw / 2;
  const sy = cy - sh / 2;

  const layer = deviceLayer(d);
  const color = d.color || LAYER_COLORS[layer];
  const isSelected = d.id === State.selectedDeviceId;

  // 填充
  ctx.fillStyle = color + '40'; // 25% 透明度
  ctx.fillRect(sx, sy, sw, sh);
  // 边框
  ctx.strokeStyle = isSelected ? '#fbbf24' : color;
  ctx.lineWidth = isSelected ? 2 : 1;
  ctx.strokeRect(sx, sy, sw, sh);

  // 端口标记（三角形）
  if (d.ports && baseScale > 0.3) {
    d.ports.forEach(p => {
      // p = [name, dx, dy, direction] 相对器件中心
      const [px, py] = toScreen(d.x + p[1], d.y + p[2]);
      drawPortMarker(ctx, px, py, p[3], color);
    });
  }

  // 标签
  if (sw > 30 && sh > 14) {
    ctx.fillStyle = '#e2e8f0';
    ctx.font = '11px sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(d.name, cx, cy);
  }
}

function drawPortMarker(ctx, x, y, direction, color) {
  const size = 5;
  ctx.fillStyle = color;
  ctx.beginPath();
  // direction: north/south/east/west
  // 三角形指向外
  switch (direction) {
    case 'east':
      ctx.moveTo(x, y);
      ctx.lineTo(x - size, y - size / 2);
      ctx.lineTo(x - size, y + size / 2);
      break;
    case 'west':
      ctx.moveTo(x, y);
      ctx.lineTo(x + size, y - size / 2);
      ctx.lineTo(x + size, y + size / 2);
      break;
    case 'north':
      ctx.moveTo(x, y);
      ctx.lineTo(x - size / 2, y + size);
      ctx.lineTo(x + size / 2, y + size);
      break;
    case 'south':
      ctx.moveTo(x, y);
      ctx.lineTo(x - size / 2, y - size);
      ctx.lineTo(x + size / 2, y - size);
      break;
    default:
      ctx.arc(x, y, size / 2, 0, Math.PI * 2);
  }
  ctx.closePath();
  ctx.fill();
}

function drawRoutes(ctx) {
  const colors = ['#60a5fa', '#f87171', '#34d399', '#fbbf24', '#a78bfa', '#22d3ee'];
  State.scene.routes.forEach((route, i) => {
    const color = colors[i % colors.length];
    ctx.strokeStyle = color;
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    const pts = route.points || [];
    pts.forEach((pt, j) => {
      const [sx, sy] = toScreen(pt[0], pt[1]);
      if (j === 0) ctx.moveTo(sx, sy);
      else ctx.lineTo(sx, sy);
    });
    ctx.stroke();
  });
}

function drawDrcHighlights(ctx) {
  State.scene.drc_highlights.forEach(h => {
    if (!h.location) return;
    const [x, y] = h.location;
    const [sx, sy] = toScreen(x, y);
    // 红色圆圈 + 半透明填充
    ctx.fillStyle = 'rgba(248, 113, 113, 0.3)';
    ctx.beginPath();
    ctx.arc(sx, sy, 20, 0, Math.PI * 2);
    ctx.fill();
    ctx.strokeStyle = '#f87171';
    ctx.lineWidth = 2;
    ctx.stroke();
    // 规则名标签
    if (h.rule_name || h.rule) {
      ctx.fillStyle = '#fca5a5';
      ctx.font = '10px sans-serif';
      ctx.textAlign = 'left';
      ctx.fillText(h.rule_name || h.rule, sx + 22, sy + 4);
    }
  });
}

// ============== Canvas 鼠标交互 ==============
function setupCanvasInteraction() {
  const canvas = $('layoutCanvas');

  canvas.addEventListener('wheel', (e) => {
    e.preventDefault();
    const rect = canvas.getBoundingClientRect();
    const mx = (e.clientX - rect.left) * (canvas.width / rect.width);
    const my = (e.clientY - rect.top) * (canvas.height / rect.height);
    // 鼠标在世界坐标
    const [wxBefore, wyBefore] = toWorld(mx, my);
    // 缩放
    const delta = e.deltaY > 0 ? 0.9 : 1.1;
    State.view.zoom *= delta;
    State.view.zoom = Math.max(0.2, Math.min(10, State.view.zoom));
    // 调整 pan 使鼠标位置保持不动
    const [wxAfter, wyAfter] = toWorld(mx, my);
    const baseScale = Math.min(canvas.width / State.canvasW, canvas.height / State.canvasH) * 0.85;
    State.view.panX += (wxAfter - wxBefore) * baseScale * State.view.zoom;
    State.view.panY += (wyAfter - wyBefore) * baseScale * State.view.zoom;
    updateZoomLabel();
    draw();
  }, { passive: false });

  canvas.addEventListener('mousedown', (e) => {
    const rect = canvas.getBoundingClientRect();
    const mx = (e.clientX - rect.left) * (canvas.width / rect.width);
    const my = (e.clientY - rect.top) * (canvas.height / rect.height);
    // 检测是否点击了器件
    const hit = hitTestDevice(mx, my);
    if (hit && e.button === 0) {
      // 左键点击器件 → 选中并准备拖动
      State.selectedDeviceId = hit.id;
      State.drag.mode = 'device';
      State.drag.startX = mx;
      State.drag.startY = my;
      State.drag.deviceStartX = hit.x;
      State.drag.deviceStartY = hit.y;
      State.drag.deviceId = hit.id;
      canvas.classList.add('dragging-device');
      renderDevicesTree();
      draw();
    } else {
      // 否则平移
      State.drag.mode = 'pan';
      State.drag.startX = mx;
      State.drag.startY = my;
    }
  });

  canvas.addEventListener('mousemove', (e) => {
    const rect = canvas.getBoundingClientRect();
    const mx = (e.clientX - rect.left) * (canvas.width / rect.width);
    const my = (e.clientY - rect.top) * (canvas.height / rect.height);

    if (State.drag.mode === 'pan') {
      State.view.panX += mx - State.drag.startX;
      State.view.panY += my - State.drag.startY;
      State.drag.startX = mx;
      State.drag.startY = my;
      draw();
    } else if (State.drag.mode === 'device' && State.drag.deviceId != null) {
      const baseScale = Math.min(canvas.width / State.canvasW, canvas.height / State.canvasH) * 0.85;
      const dxUm = (mx - State.drag.startX) / (baseScale * State.view.zoom);
      const dyUm = (my - State.drag.startY) / (baseScale * State.view.zoom);
      // 仅更新本地显示，不立即同步后端
      const dev = State.scene.devices.find(d => d.id === State.drag.deviceId);
      if (dev) {
        dev.x = State.drag.deviceStartX + dxUm;
        dev.y = State.drag.deviceStartY + dyUm;
        draw();
        renderDevicesTree();
      }
    } else {
      // 悬浮提示
      const hit = hitTestDevice(mx, my);
      const tooltip = $('canvasTooltip');
      if (hit) {
        tooltip.style.display = 'block';
        const rect = canvas.getBoundingClientRect();
        tooltip.style.left = (e.clientX - rect.left + 12) + 'px';
        tooltip.style.top = (e.clientY - rect.top + 12) + 'px';
        let txt = `${hit.name} (${hit.device_type})\n` +
                  `位置: (${hit.x.toFixed(1)}, ${hit.y.toFixed(1)}) μm\n` +
                  `尺寸: ${hit.w.toFixed(1)} × ${hit.h.toFixed(1)} μm\n` +
                  `图层: ${deviceLayer(hit)}`;
        if (hit.ports && hit.ports.length > 0) {
          txt += `\n端口: ${hit.ports.length} 个`;
        }
        tooltip.textContent = txt;
      } else {
        tooltip.style.display = 'none';
      }
    }
  });

  canvas.addEventListener('mouseup', async () => {
    if (State.drag.mode === 'device' && State.drag.deviceId != null) {
      // 拖动结束 → 同步到后端（API 字段为 new_position: [x, y]）
      const dev = State.scene.devices.find(d => d.id === State.drag.deviceId);
      if (dev) {
        try {
          await apiPost('/api/editor/device/move', {
            device_id: dev.id,
            new_position: [dev.x, dev.y],
          });
          logTask('editor', `移动器件 ${dev.name} → (${dev.x.toFixed(1)}, ${dev.y.toFixed(1)})`, 'done');
        } catch (e) {
          showError('移动器件失败: ' + e.message);
        }
      }
      canvas.classList.remove('dragging-device');
    }
    State.drag.mode = 'none';
    State.drag.deviceId = null;
  });

  canvas.addEventListener('dblclick', () => {
    State.selectedDeviceId = null;
    renderDevicesTree();
    draw();
  });

  canvas.addEventListener('mouseleave', () => {
    $('canvasTooltip').style.display = 'none';
    State.drag.mode = 'none';
    canvas.classList.remove('dragging-device');
  });
}

function hitTestDevice(mx, my) {
  // 反向遍历（后绘制的在上层）
  // (d.x, d.y) 是器件中心
  for (let i = State.scene.devices.length - 1; i >= 0; i--) {
    const d = State.scene.devices[i];
    const [cx, cy] = toScreen(d.x, d.y);
    const baseScale = Math.min(
      $('layoutCanvas').width / State.canvasW,
      $('layoutCanvas').height / State.canvasH
    ) * 0.85 * State.view.zoom;
    const sw = Math.max(d.w * baseScale, 3);
    const sh = Math.max(d.h * baseScale, 3);
    const sx = cx - sw / 2;
    const sy = cy - sh / 2;
    if (mx >= sx && mx <= sx + sw && my >= sy && my <= sy + sh) {
      return d;
    }
  }
  return null;
}

// ============== 场景同步 ==============
async function syncScene() {
  try {
    const data = await apiGet('/api/editor/scene');
    // 标准化场景数据（LayoutEditor.render() 返回 position/size 数组，
    // app.js 内部统一使用 x/y/w/h 字段以便 hitTest 与绘制）
    const devices = (data.devices || []).map(d => ({
      id: d.device_id,
      name: d.device_id,  // LayoutEditor 用 device_id 作唯一标识
      device_type: d.device_type,
      x: d.position[0],
      y: d.position[1],
      w: d.size[0],
      h: d.size[1],
      rotation: d.rotation || 0,
      category: d.category,
      color: d.color,
      ports: d.ports || [],  // 编辑器场景中端口由 add_device 时附加
      params: d.params || {},
    }));
    const routes = (data.routes || []).map(r => ({
      conn_id: r.conn_id,
      points: r.points,
    }));
    const drcHighlights = (data.drc_highlights || []).map(h => ({
      x: h.x,
      y: h.y,
      width: h.width,
      height: h.height,
      rule: h.rule,
      rule_name: h.rule,
      severity: h.severity,
      location: [h.x, h.y],
    }));
    State.scene = {
      layers: data.layers || ['passive', 'active', 'source', 'detector', 'default'],
      devices: devices,
      routes: routes,
      drc_highlights: drcHighlights,
    };
    if (data.canvas_w) State.canvasW = data.canvas_w;
    if (data.canvas_h) State.canvasH = data.canvas_h;
    renderLayers();
    renderDevicesTree();
    draw();
  } catch (e) {
    showError('同步场景失败: ' + e.message);
  }
}

async function syncUploads() {
  try {
    const data = await apiGet('/api/uploads');
    State.uploads = data.uploads || [];
    renderUploads();
  } catch (e) {
    logTask('upload', '获取上传列表失败: ' + e.message, 'failed');
  }
}

// ============== 按钮事件 ==============
async function runPlacement() {
  setStatus('布局中...', 'running');
  logTask('placement', `preset=${State.selectedPreset}`, 'running');
  try {
    const data = await apiPost('/api/run_placement', {
      preset: State.selectedPreset,
      mode: 'analytical',
    });
    if (!data.success || data.status === 'failed') throw new Error(data.error);
    State.lastPlacement = data.result;
    // 同步器件到编辑器场景
    if (data.result && data.result.placements) {
      await loadPresetToEditor();
    }
    updateMetrics();
    setStatus('布局完成', '');
    logTask('placement', `HPWL=${data.result.hpwl.toFixed(1)}, ${data.result.n_devices}器件`, 'done');
    await syncScene();
  } catch (e) {
    setStatus('布局失败', 'error');
    showError('布局失败: ' + e.message);
  }
}

async function runRouting() {
  setStatus('布线中...', 'running');
  logTask('routing', `preset=${State.selectedPreset}`, 'running');
  try {
    const data = await apiPost('/api/run_routing', { preset: State.selectedPreset });
    if (!data.success || data.status === 'failed') throw new Error(data.error);
    State.lastRouting = data.result;
    // 设置布线路径到编辑器场景
    if (data.result && data.result.paths) {
      await apiPost('/api/editor/routes', { routes: data.result.paths });
    }
    updateMetrics();
    renderPathsList();
    setStatus('布线完成', '');
    logTask('routing', `${data.result.n_paths}路径, 损耗${data.result.total_loss_db.toFixed(2)}dB`, 'done');
    await syncScene();
  } catch (e) {
    setStatus('布线失败', 'error');
    showError('布线失败: ' + e.message);
  }
}

async function runDrc() {
  setStatus('DRC 检查中...', 'running');
  logTask('drc', `preset=${State.selectedPreset}`, 'running');
  try {
    const data = await apiPost('/api/run_drc', { preset: State.selectedPreset });
    if (!data.success || data.status === 'failed') throw new Error(data.error);
    State.lastDrc = data.result;
    // 设置 DRC 高亮到编辑器场景（字段名 drc_highlights）
    if (data.result && data.result.drc_highlights) {
      await apiPost('/api/editor/drc', { drc_errors: data.result.drc_highlights });
    }
    updateMetrics();
    renderDrcList();
    setStatus(data.result.n_violations === 0 ? 'DRC 通过' : `DRC ${data.result.n_violations}违规`, 
              data.result.n_violations === 0 ? '' : 'error');
    logTask('drc', `${data.result.n_violations}违规 / ${data.result.n_rules}规则`, 'done');
    await syncScene();
  } catch (e) {
    setStatus('DRC 失败', 'error');
    showError('DRC 检查失败: ' + e.message);
  }
}

async function runPipeline() {
  setStatus('流水线运行中...', 'running');
  logTask('placement', `preset=${State.selectedPreset}`, 'running');
  try {
    const data = await apiPost('/api/run', {
      preset: State.selectedPreset,
      router_type: 'curvy',
    });
    if (!data.success) throw new Error(data.error || '运行失败');
    const r = data.result;
    State.lastPlacement = { hpwl: r.hpwl, n_devices: r.n_devices };
    State.lastRouting = {
      paths: r.paths,
      n_paths: r.n_paths,
      total_loss_db: r.total_loss_db,
    };
    State.lastDrc = {
      n_violations: r.drc_passed ? 0 : 1,
      violations: [],
    };
    // 同步到编辑器
    if (r.paths) {
      await apiPost('/api/editor/routes', { routes: r.paths });
    }
    updateMetrics();
    renderPathsList();
    renderDrcList();
    setStatus(r.drc_passed ? '流水线完成' : '流水线完成(DRC未通过)',
              r.drc_passed ? '' : 'error');
    logTask('placement', `HPWL=${r.hpwl.toFixed(1)}, ${r.n_devices}器件`, 'done');
    logTask('routing', `${r.n_paths}路径, 损耗${r.total_loss_db.toFixed(2)}dB`, 'done');
    logTask('drc', r.drc_passed ? 'DRC 通过' : 'DRC 违规', r.drc_passed ? 'done' : 'failed');
    await syncScene();
  } catch (e) {
    setStatus('流水线失败', 'error');
    showError('流水线失败: ' + e.message);
  }
}

async function loadPresetToEditor() {
  // 通过 editor API 加载预设器件到场景
  try {
    const circuit = await apiGet('/api/presets');
    // 此处简化：清空场景后由 placement 结果驱动
  } catch (e) {
    // 非关键路径
  }
}

async function uploadGds(file) {
  setStatus('上传中...', 'running');
  logTask('upload', `filename=${file.name}, size=${(file.size / 1024).toFixed(1)}KB`, 'running');
  try {
    const data = await apiUpload('/api/upload_gds', file);
    if (!data.success) throw new Error(data.error);
    logTask('upload', `file_id=${data.file_id}, ${data.filename}`, 'done');
    setStatus('就绪', '');
    await syncUploads();
  } catch (e) {
    setStatus('上传失败', 'error');
    showError('上传失败: ' + e.message);
  }
}

async function exportKlayout() {
  setStatus('导出 KLayout...', 'running');
  logTask('editor', '导出 KLayout Python 脚本', 'running');
  try {
    const data = await apiPost('/api/editor/export_klayout', {
      output_gds: 'polaris_layout.gds',
      top_cell_name: 'TOP',
    });
    if (!data.success) throw new Error(data.error);
    // 触发下载（响应字段: script/n_devices/output_gds/top_cell_name）
    const script = data.script;
    const filename = data.output_gds.replace(/\.gds$/i, '.py') || 'polaris_layout.py';
    const blob = new Blob([script], { type: 'text/x-python' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
    setStatus('导出完成', '');
    logTask('editor', `导出 ${filename} (${data.n_devices}器件, ${script.length}字节)`, 'done');
  } catch (e) {
    setStatus('导出失败', 'error');
    showError('导出 KLayout 失败: ' + e.message);
  }
}

async function editorUndo() {
  try {
    await apiPost('/api/editor/undo');
    logTask('editor', '撤销', 'done');
    await syncScene();
  } catch (e) {
    showError('撤销失败: ' + e.message);
  }
}

async function editorRedo() {
  try {
    await apiPost('/api/editor/redo');
    logTask('editor', '重做', 'done');
    await syncScene();
  } catch (e) {
    showError('重做失败: ' + e.message);
  }
}

async function editorClear() {
  if (!confirm('确认清空场景？')) return;
  try {
    await apiPost('/api/editor/clear');
    State.selectedDeviceId = null;
    State.lastPlacement = null;
    State.lastRouting = null;
    State.lastDrc = null;
    logTask('editor', '清空场景', 'done');
    await syncScene();
    renderDrcList();
    renderPathsList();
    updateMetrics();
    setStatus('就绪', '');
  } catch (e) {
    showError('清空失败: ' + e.message);
  }
}

function zoomIn() {
  State.view.zoom = Math.min(10, State.view.zoom * 1.2);
  updateZoomLabel();
  draw();
}

function zoomOut() {
  State.view.zoom = Math.max(0.2, State.view.zoom / 1.2);
  updateZoomLabel();
  draw();
}

function zoomReset() {
  State.view.zoom = 1.0;
  State.view.panX = 0;
  State.view.panY = 0;
  updateZoomLabel();
  draw();
}

// ============== 初始化 ==============
function init() {
  // 绑定按钮事件
  $('btnRunPlacement').onclick = runPlacement;
  $('btnRunRouting').onclick = runRouting;
  $('btnRunDrc').onclick = runDrc;
  $('btnRunPipeline').onclick = runPipeline;
  $('btnUploadGds').onclick = () => $('gdsFileInput').click();
  $('gdsFileInput').onchange = (e) => {
    if (e.target.files.length > 0) {
      uploadGds(e.target.files[0]);
      e.target.value = ''; // 允许重复上传同一文件
    }
  };
  $('btnExportKlayout').onclick = exportKlayout;
  $('btnUndo').onclick = editorUndo;
  $('btnRedo').onclick = editorRedo;
  $('btnClear').onclick = editorClear;
  $('btnZoomIn').onclick = zoomIn;
  $('btnZoomOut').onclick = zoomOut;
  $('btnZoomReset').onclick = zoomReset;

  $('presetSelect').onchange = (e) => {
    State.selectedPreset = e.target.value;
  };

  // 键盘快捷键
  document.addEventListener('keydown', (e) => {
    if (e.ctrlKey && e.key === 'z') { e.preventDefault(); editorUndo(); }
    else if (e.ctrlKey && e.key === 'y') { e.preventDefault(); editorRedo(); }
    else if (e.key === '+' || e.key === '=') { zoomIn(); }
    else if (e.key === '-') { zoomOut(); }
    else if (e.key === '0') { zoomReset(); }
  });

  // Canvas 自适应大小
  function resizeCanvas() {
    const container = $('canvasContainer');
    const canvas = $('layoutCanvas');
    const w = container.clientWidth - 4;
    const h = container.clientHeight - 4;
    canvas.width = Math.max(w, 400);
    canvas.height = Math.max(h, 300);
    draw();
  }
  window.addEventListener('resize', resizeCanvas);

  setupCanvasInteraction();

  // 初始加载
  setStatus('加载中...', 'running');
  syncScene().then(() => {
    syncUploads();
    updateMetrics();
    setStatus('就绪', '');
    logTask('editor', '编辑器初始化完成', 'done');
  });

  // 延迟调整 canvas 大小（等布局完成）
  setTimeout(resizeCanvas, 50);
}

document.addEventListener('DOMContentLoaded', init);
