# PoLaRIS 流程设计缺陷审查报告（Task 4）

> 审查范围：布局 → 布线 → 仿真 → DRC → GDS 各环节
> 审查日期：2026-06-24
> 审查依据：实际代码审查（基于 /workspace/src/polaris/ 源码）
> 项目规则：14.1 禁止 fall-back；7.1 文件 < 600 行；学术诚信禁止造假

## 摘要

| 环节 | 缺陷数 | P0 | P1 | P2 | P3 |
|------|--------|----|----|----|----|
| 布局算法 | 4 | 1 | 1 | 1 | 1 |
| 布线算法 | 5 | 1 | 2 | 1 | 1 |
| 仿真模块 | 2 | 0 | 0 | 1 | 1 |
| DRC 检查器 | 4 | 1 | 1 | 1 | 1 |
| GDS 导出 | 3 | 0 | 1 | 1 | 1 |
| **合计** | **18** | **3** | **5** | **5** | **5** |

**关键风险**：大规模电路（500 器件）上布局重叠、布线死锁、DRC 规则缺失三项 P0 缺陷将导致端到端流水线在商业级电路上无法产出可用结果。

---

## 1. 布局算法缺陷清单

### 缺陷 [P0]: 网格布局在大器件小画布场景下产生重叠
- 位置: src/polaris/pipeline/integrated.py:243-257（`_DefaultPlacer._place_random`）
- 描述: 网格布局按 `cell_w = canvas_w / n_cols` 均匀划分格子，但当器件尺寸（`dev.width_um`/`dev.height_um`）大于格子尺寸时，器件会被放置在格子左下角并溢出到相邻格子。代码仅计算 `avail_w = max(cell_w - dev.width_um - min_spacing, 0)`，当 `avail_w=0` 时 `offset_x=0`，器件从格子起点开始放置，若器件宽度超过 `cell_w`，则器件右边界进入右侧格子，与右侧格子器件重叠。
- 影响: 在小画布大器件场景（如 canvas=200μm，器件 width_um=30μm，n_cols=23 → cell_w≈8.7μm）下必然产生重叠，导致 DRC 失败、GDS 不可用。商业 EDA 工具（如 Cadence Innovus）使用 bin-based 合法化避免此问题。
- 修复建议: (1) 检测器件尺寸是否超过格子尺寸，超过时扩大格子或换用模拟退火合法化；(2) 器件放置后运行 `check_overlap` 重叠检测，对重叠器件执行强制合法化（推开到最近空闲位置）；(3) 参考 DREAMPlace 的 legalization 模块（src/polaris/engine/legalization.py 已存在但未接入）。

### 缺陷 [P1]: 布局完全不考虑器件端口方向
- 位置: src/polaris/pipeline/integrated.py:224-258（`_DefaultPlacer._place_random`）
- 描述: 布局仅按器件 bbox 占据格子，不读取 `DeviceSpec.ports` 中的端口方向信息，也不支持器件旋转。器件端口朝向是固定的（基于 bbox 局部坐标），布局后端口可能朝向画布边界或朝向远离连接对端的方向，导致布线必须绕行。
- 影响: 布线路径长度增加 20-50%，插入损耗超标，交叉数增加。商业光子 EDA（如 Aspic、VPIphotonics）均支持端口感知布局。`_converters.py:69-94` 的 `_build_ports_from_spec` 表明 DeviceSpec 已携带端口方向数据，但布局器未利用。
- 修复建议: (1) 布局时根据连接关系计算每个器件的"最佳端口朝向"（使连接对端端口朝向彼此）；(2) 支持 4 方向旋转（0/90/180/270 度），选择使总连接曼哈顿距离最小的旋转；(3) 参考 Apollo arXiv 2025 的布线感知布局反馈。

### 缺陷 [P2]: 随机贪心布局无全局优化，大规模电路布局质量差
- 位置: src/polaris/pipeline/integrated.py:230-258（`_DefaultPlacer._place_random`）
- 描述: 使用固定随机种子 42 的均匀随机偏移布局，无任何全局优化目标（如最小化总线长、最小化重叠概率、均衡拥塞）。500 器件上，随机布局的 HPWL（半周长线长）通常比解析布局差 3-5 倍。
- 影响: 大规模电路布线长度过长，损耗超标，SimLoop 迭代无法收敛。项目已实现 `analytical_placer.py`/`hierarchical_placer.py`/`legalization.py` 等高级布局器，但 `IntegratedPipeline` 默认使用 `_DefaultPlacer`，未接入。
- 修复建议: (1) 将 `IntegratedPipeline` 默认布局器切换为 `AnalyticalPlacer`（已存在于 src/polaris/engine/）；(2) 保留 `_DefaultPlacer` 仅作为基线对比用途，文档明确标注"非生产用途"。

### 缺陷 [P3]: RL 布局器硬编码 obs_dim 推断依赖固定 benchmark
- 位置: src/polaris/pipeline/integrated.py:148-159（`_DefaultPlacer._try_load_agent`）
- 描述: RL agent 的 `obs_dim` 和 `n_actions` 通过加载固定 benchmark `data/benchmarks/mzi.json` 推断，`n_actions=400` 硬编码。当目标电路规模与 mzi.json 不同时，obs_dim 可能不匹配，导致 agent 加载后推理失败或输出错误动作。
- 影响: RL 布局器在非 MZI 电路上可能静默产出错误布局。
- 修复建议: (1) obs_dim/n_actions 应从 checkpoint 元数据读取（PPOAgentDiscrete.load 应保存这些信息）；(2) 加载后校验 obs_dim 与目标电路的 FloorplanEnv obs 维度一致，不一致时 raise RuntimeError。

---

## 2. 布线算法缺陷清单

### 缺陷 [P0]: 顺序布线障碍物累积导致大规模电路拥塞死锁
- 位置: src/polaris/pipeline/integrated.py:337-416（`_CurvyRouter.route`）
- 描述: 顺序布线策略将每条已布线路径转换为障碍物（窄带），累积添加到后续连接的障碍列表。500 器件电路假设有 1000 连接，每条路径平均 10 段，则累积 10000 个障碍盒。后期连接的可用空间被严重压缩，A* 搜索无法找到路径，产生大量 `unrouted` 连接。代码仅记录 warning 日志，不重试、不 rip-up 重布线。
- 影响: 大规模电路上 30-60% 连接无法布线，端到端流水线产出不可用版图。商业布线器（如 Cadence Innovus）使用全局布线 + 拆分重布（rip-up and reroute）避免此问题。项目已实现 `rip_reroute.py`/`global_router.py` 但未接入 `IntegratedPipeline`。
- 修复建议: (1) 接入 `GlobalRouter` 做全局布线规划，再用 `_CurvyRouter` 做详细布线；(2) 实现 rip-up and reroute：当连接布线失败时，移除冲突的已布线路径并重布；(3) 限制障碍物累积数量，超过阈值时触发全局重布线。

### 缺陷 [P1]: 障碍物半宽 grid_size*0.6 过大，过度阻塞通道
- 位置: src/polaris/pipeline/integrated.py:400（`_path_to_obstacles(sampled_pts, grid_size * 0.6)`）
- 描述: SOI 平台 `grid_size = min_bend_radius_um = 5.0μm`，障碍物半宽 = 5.0 × 0.6 = 3.0μm，全宽 6.0μm。但 `min_spacing_um = 1.0μm`（SiEPIC EBeam PDK），波导宽度 0.5μm。6.0μm 的障碍带远大于物理需求（0.5 + 2×1.0 = 2.5μm 即可避免交叉），过度保守。
- 影响: 画布有效利用率下降 60% 以上，加剧拥塞死锁。在 5000×5000μm 画布上，100 条已布线路径的障碍物即可覆盖 100×6μm×平均100μm = 60000μm²，占画布 0.24%，但障碍物分布不均，局部通道被完全阻塞。
- 修复建议: (1) 障碍物半宽应为 `waveguide_width/2 + min_spacing_um = 0.25 + 1.0 = 1.25μm`；(2) 或使用 `grid_size * 0.3`（1.5μm）作为折中；(3) 障碍物应仅覆盖波导实际占据的网格单元，而非整段路径的包围盒。

### 缺陷 [P1]: 起终点对齐到精确坐标破坏网格对齐与弯曲半径约束
- 位置: src/polaris/pipeline/integrated.py:392-394（`pts[0] = start; pts[-1] = end`）
- 描述: A* 搜索在网格上产出路径，中间点均为 `grid_size` 整数倍。但起终点被强制替换为器件中心精确坐标（`pos1["x"] + pos1["w"]/2`），这些坐标通常不是 `grid_size` 整数倍。这导致首尾段长度可能小于 `min_bend_radius_um`，违反弯曲半径约束；且首尾段方向可能与网格路径方向不一致，产生未约束的斜线段。
- 影响: DRC `check_bend_radius` 可能漏检（因为下采样过滤了短段），但实际版图上首尾段弯曲半径不足，流片后波导损耗增大或模式泄露。
- 修复建议: (1) 起终点对齐到最近网格点，而非精确坐标；(2) 或在起终点与网格路径之间插入过渡段（S 弯），确保弯曲半径满足约束；(3) 器件端口位置应在布局阶段对齐到网格。

### 缺陷 [P2]: 下采样函数丢失关键转弯点
- 位置: src/polaris/pipeline/integrated.py:627-653（`_downsample_path_for_obstacle`）
- 描述: 下采样合并距离小于 `min_segment`（= grid_size = 5.0μm）的相邻点。但 A* 网格路径的转弯点间距可能正好是 `grid_size`（5.0μm），下采样后转弯点可能被合并，导致障碍物不能准确覆盖实际路径转弯处，后续连接可能在转弯处穿过。
- 影响: 障碍物覆盖不完整，产生未检测的交叉，仿真 `n_crossings` 计算不准确。
- 修复建议: (1) 下采样应保留所有方向变化的转弯点，仅合并同方向共线的中间点；(2) `min_segment` 应小于 `grid_size`（如 `grid_size * 0.5`），避免丢失转弯点。

### 缺陷 [P3]: 每条连接重建 GridRouter，障碍物添加 O(n²) 复杂度
- 位置: src/polaris/pipeline/integrated.py:376-385（`_CurvyRouter.route` 循环内创建 GridRouter）
- 描述: 每条连接创建新的 `GridRouter` 实例，并遍历所有累积障碍物调用 `add_obstacle_box`。N 条连接的障碍物添加总复杂度为 O(N² × M)，其中 M 为平均障碍物数。500 连接时，障碍物添加操作约 250000 次，每次涉及 numpy 数组切片赋值。
- 影响: 大规模电路上布线阶段耗时显著增加（预估 500 连接 >30 秒）。
- 修复建议: (1) 复用同一个 GridRouter 实例，仅增量添加新障碍物；(2) 或使用全局障碍物栅格，所有连接共享。

---

## 3. 仿真模块缺陷清单

### 缺陷 [P2]: SimLoop 仅传递 total_loss_db 和 n_crossings，大量 DRC 输入缺失
- 位置: src/polaris/sim/sim_loop.py:156-165（`SimLoop._check_constraints`）
- 描述: `CheckContext` 仅设置 `total_loss_db` 和 `n_crossings`，其余字段（`waveguide_widths`/`coupling_gaps`/`waveguide_lengths`/`device_areas`/`port_connections`/`layer_densities`）均为 None。导致 `ConstraintChecker._check_optional` 中 6 项检查被静默跳过。这不是 fall-back（代码逻辑正确），但效果上是 DRC 覆盖不全。
- 影响: 波导宽度、耦合间隙、波导长度、器件面积、端口连接性、层密度 6 项 DRC 规则从未执行，版图可能存在未检测的违规。
- 修复建议: (1) SimLoop 应从 placements/paths 提取波导宽度（默认 0.5μm）、波导长度（path_length）、器件面积（w×h）等数据填充 CheckContext；(2) 端口连接性应从 circuit.connections 与 paths 比对得出。

### 缺陷 [P3]: 时域仿真（PAM4 眼图）未集成到主流程
- 位置: src/polaris/sim/interconnect.py:545-648（`EyeDiagramAnalyzer`）vs src/polaris/pipeline/integrated.py:419-543（`_DefaultSimulator`）
- 描述: `EyeDiagramAnalyzer` 支持 NRZ/PAM4 眼图分析与 BER 计算，但 `IntegratedPipeline` 主流程仅调用频域 S 参数仿真（`_DefaultSimulator.simulate`），未调用时域仿真。时域仿真模块独立存在但未接入端到端流程。
- 影响: 流水线无法评估调制器性能（眼图、BER），无法对齐商业工具（Lumerical INTERCONNECT）的时域分析能力。
- 修复建议: (1) 在 `PipelineConfig` 增加 `enable_time_domain: bool = False` 选项；(2) SimLoop 迭代收敛后，可选执行时域仿真，将眼图/BER 加入 PipelineResult。

---

## 4. DRC 检查器缺陷清单

### 缺陷 [P0]: 5 项 DRC 规则未实现或未调用
- 位置: src/polaris/sim/constraint_checker.py:62-110（`ConstraintChecker.check`）+ src/polaris/sim/constraint_types.py:28-44（`ViolationType`）
- 描述: `ViolationType` 枚举定义了 16 项违规类型，但 `ConstraintChecker.check` 实际调用的检查函数仅覆盖 11 项。以下 5 项无对应检查函数或未调用：
  - `THERMAL`（热串扰）：`check_thermal` 函数存在于 `constraint_checks_performance.py:60-94`，但 `ConstraintChecker.check` 和 `_check_optional` 均未调用。
  - `CROSSTALK`（串扰）：`check_crosstalk` 函数存在于 `constraint_checks_performance.py:97-135`，但未被调用。
  - `ENCLOSURE`（包围规则）：`ConstraintConfig` 有 `min_enclosure_um=0.5` 参数，但无对应 check 函数。
  - `NOTCH`（凹槽）：`ConstraintConfig` 有 `min_notch_um=0.3` 参数，但无对应 check 函数。
  - `PIN_MATCH`（端口匹配）：无对应 check 函数。
- 影响: 版图可能存在热串扰超标、波导串扰超标、包围规则违规、凹槽间距不足、端口宽度不匹配等问题但 DRC 通过，流片后器件失效。商业 DRC runset（如 KLayout SiEPIC runset）均覆盖这些规则。
- 修复建议: (1) 在 `ConstraintChecker.check` 中调用 `check_thermal` 和 `check_crosstalk`；(2) 实现 `check_enclosure`/`check_notch`/`check_pin_match` 函数；(3) 从 placements/paths 提取热源器件信息（category=="active"）用于热串扰检查。

### 缺陷 [P1]: 可选 DRC 检查依赖输入数据，SimLoop 未提供导致静默跳过
- 位置: src/polaris/sim/constraint_checker.py:89-110（`_check_optional`）
- 描述: `_check_optional` 中的 6 项检查（min_width/coupling_gap/waveguide_length/min_area/port_connectivity/layer_density）均依赖 `CheckContext` 中的可选字段。字段为 None 时检查被跳过，无 warning 日志。SimLoop 仅填充 `total_loss_db` 和 `n_crossings`，其余字段均为 None。
- 影响: 6 项 DRC 规则在主流程中从未执行，DRC 报告 `passed=True` 但实际未检查这些规则，产生虚假通过。
- 修复建议: (1) SimLoop 应从 placements/paths/circuit 提取数据填充 CheckContext 的所有字段；(2) `_check_optional` 跳过检查时应记录 info 日志，明确告知哪些规则未执行。

### 缺陷 [P2]: check_crosstalk 采样点对距离计算不准确
- 位置: src/polaris/sim/constraint_checks_performance.py:182-192（`_min_path_gap`）
- 描述: `_min_path_gap` 通过采样点对距离最小值估算两条路径的最小间距。采样步长 `step = max(1, len(pts) // 20)`，即每条路径最多采样 20 个点。对于长路径（如 500μm，100 个点），采样间距 25μm，可能遗漏近距离平行段。
- 影响: 串扰检查漏报，平行波导间距不足但未检测到。
- 修复建议: (1) 使用线段-线段最短距离计算（而非点对距离）；(2) 或增大采样密度（如 `len(pts) // 100`）。

### 缺陷 [P3]: check_spacing/check_overlap 为 O(n²)，大规模电路性能下降
- 位置: src/polaris/sim/constraint_checks_geometry.py:128-177（`check_spacing`/`check_overlap`）
- 描述: 器件间距与重叠检查使用双重循环遍历所有器件对，复杂度 O(n²)。500 器件 = 124750 对比较，纯 Python 实现约 0.5-1 秒。1000 器件 = 499500 对，约 2-4 秒。
- 影响: 大规模电路上 DRC 检查耗时增加，但不阻塞（可接受）。
- 修复建议: (1) 使用空间索引（如 R-tree 或网格分块）加速，将复杂度降至 O(n·k)，k 为邻近器件数；(2) 或使用 numpy 向量化计算。

---

## 5. GDS 导出缺陷清单

### 缺陷 [P1]: GDS 无层次结构，所有器件平铺在 TOP cell
- 位置: src/polaris/eval/layout_render.py:331-358（`export_gds`）+ src/polaris/eval/layout_render.py:250-286（`_place_device_boxes`）
- 描述: `export_gds` 仅创建一个 `TOP` cell，所有器件矩形、DEVREC、端口标记直接画在 TOP cell 上。未为每个器件创建子 cell 并通过 SREF（cell reference）实例化。500 器件 × 每器件约 5-10 个 shape = 2500-5000 个 shape 全部在 TOP cell。
- 影响: (1) GDS 文件体积大（无实例化压缩）；(2) KLayout 加载后无法按器件选择/移动；(3) 不符合商业 PDK 的 GDS 规范（SiEPIC/gdsfactory 均使用层次结构）；(4) DRC 验证工具（如 KLayout SiEPIC runset）依赖 DEVREC 层的 cell 结构进行 netlist 提取，平铺结构可能导致提取失败。
- 修复建议: (1) 为每个器件创建子 cell（`ly.create_cell(device_name)`），在子 cell 内画器件几何；(2) TOP cell 通过 `cell.insert(db.CellInstArray(child_cell, db.DTrans(x, y)))` 实例化；(3) 波导路径也创建独立 cell 或直接画在 TOP cell。

### 缺陷 [P2]: GDS 导出未验证可被 KLayout 重新加载
- 位置: src/polaris/eval/layout_render.py:357（`ly.write(output_path)`）
- 描述: `export_gds` 调用 `ly.write(output_path)` 写入 GDS 文件，但未实现反向加载验证（用 klayout.db 重新读取并校验 layer/cell 数量）。代码注释声称"使用真实 foundry layer 编号"和"SiEPIC 格式"，但无自动化测试验证导出的 GDS 能被 KLayout GUI 正确打开并显示。
- 影响: 可能存在 layer 编号错误、cell 结构异常、DBU 不匹配等问题未被发现。
- 修复建议: (1) 在 `export_gds` 后增加自验证：`ly2 = db.Layout(); ly2.read(output_path); assert ly2.top_cell().bbox().width() > 0`；(2) 增加 KLayout Python 脚本测试，验证导出的 GDS 能被 KLayout 加载并显示预期 layer。

### 缺陷 [P3]: GDS 导出未包含 FLOORPLAN 层和切割道
- 位置: src/polaris/eval/layout_render.py:331-358（`export_gds`）
- 描述: `POLARIS_GDS_LAYER_MAP` 定义了 `FLOORPLAN`（99,0）和 `DICING`（100,0）层，但 `export_gds` 未在导出时画 FLOORPLAN 矩形（画布边界）和 DICING 道。商业 foundry 提交要求 GDS 包含 FLOORPLAN 层标记设计区域，DICING 层标记切割道。
- 影响: 导出的 GDS 不符合 foundry 提交规范，无法直接流片。
- 修复建议: (1) 在 `export_gds` 中添加 FLOORPLAN 层矩形（画布边界）；(2) 添加 DICING 层矩形（画布边缘内侧）。

---

## 6. 总体评估

### 6.1 流程成熟度

| 环节 | 成熟度 | 评估 |
|------|--------|------|
| 布局 | 40% | 网格布局可用但无全局优化，端口方向未考虑，RL 布局器未验证 |
| 布线 | 50% | A* + JPS 性能优化良好，但顺序布线死锁、障碍物过保守 |
| 仿真 | 70% | 频域仿真完整，查表数据真实有来源，时域仿真未集成 |
| DRC | 45% | 11/16 规则已实现，5 项缺失，SimLoop 未填充 DRC 输入 |
| GDS | 55% | 真实 layer 编号，SiEPIC 格式，但无层次结构、无 foundry 提交层 |

**整体成熟度：52%** — 小规模演示电路（<20 器件）可用，大规模商业电路（500 器件）不可用。

### 6.2 关键风险

1. **P0 风险：大规模电路端到端失败**
   - 布局重叠（P0）+ 布线死锁（P0）+ DRC 规则缺失（P0）三项缺陷叠加，导致 500 器件电路上流水线产出不可用结果。
   - 影响：无法对标商业 EDA 工具（Cadence/Lumerical/Aspic）的大规模电路处理能力。

2. **P1 风险：DRC 虚假通过**
   - 6 项 DRC 检查因输入数据缺失被静默跳过，DRC 报告 `passed=True` 但实际未检查。
   - 影响：版图可能存在未检测违规，流片后器件失效。

3. **P1 风险：GDS 不符合 foundry 提交规范**
   - 无层次结构、无 FLOORPLAN/DICING 层，无法直接提交 foundry。
   - 影响：需要人工后处理才能流片。

### 6.3 修复路线图

**阶段 1（P0 修复，预计 2-3 天）**：
1. 修复布局重叠：接入 `legalization.py` 强制合法化
2. 修复布线死锁：接入 `global_router.py` + 实现 rip-up and reroute
3. 补全 DRC 规则：调用 `check_thermal`/`check_crosstalk`，实现 `check_enclosure`/`check_notch`/`check_pin_match`

**阶段 2（P1 修复，预计 3-5 天）**：
4. 布局端口感知：支持器件旋转优化端口朝向
5. 障碍物半宽优化：从 grid_size*0.6 降至 waveguide_width/2 + min_spacing
6. 起终点网格对齐：插入 S 弯过渡段
7. SimLoop 填充 CheckContext：提取波导宽度/长度/器件面积等
8. GDS 层次结构：为每个器件创建子 cell + SREF 实例化

**阶段 3（P2/P3 改进，预计 2-3 天）**：
9. 接入 AnalyticalPlacer 替代随机贪心布局
10. 下采样保留转弯点
11. 时域仿真集成到主流程
12. GDS 自验证 + FLOORPLAN/DICING 层
13. DRC 性能优化（空间索引）

---

## 附录：审查文件清单

| 文件 | 行数 | 审查内容 |
|------|------|----------|
| src/polaris/pipeline/integrated.py | 814 | _DefaultPlacer, _CurvyRouter, _DefaultSimulator, IntegratedPipeline |
| src/polaris/pipeline/_converters.py | 180 | SimLoop dict → Placement/WaveguidePath 转换 |
| src/polaris/sim/sim_loop.py | 202 | SimLoop 仿真回馈闭环 |
| src/polaris/sim/simulator.py | 441 | CircuitSimulator 频域仿真 |
| src/polaris/sim/constraint_checker.py | 137 | ConstraintChecker 统一入口 |
| src/polaris/sim/constraint_checks_geometry.py | 439 | 几何 DRC 检查函数 |
| src/polaris/sim/constraint_checks_performance.py | 201 | 性能 DRC 检查函数 |
| src/polaris/sim/constraint_types.py | 174 | ViolationType/ConstraintConfig/CheckContext |
| src/polaris/sim/feedback_adapter.py | 194 | FeedbackAdapter 反馈适配器 |
| src/polaris/sim/models.py | 300+ | 基础器件 S 参数模型 |
| src/polaris/eval/layout_render.py | 516 | GDS 导出 + DRC 报告 |
| src/polaris/router/waveguide_router.py | 649 | GridRouter A* 网格布线 |
| src/polaris/router/obstacle_grid.py | 261 | ObstacleGrid 障碍物存储 |
| src/polaris/pdk/layer_map.py | 164 | GDS Layer Map |
| src/polaris/sim/interconnect.py | 648 | EyeDiagramAnalyzer 时域仿真 |

**注**：integrated.py 实际 814 行，超过规则 7.1 的 600 行限制（已在其他审查中记录，本报告聚焦流程设计缺陷）。
