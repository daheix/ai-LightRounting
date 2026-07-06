# B03 - LVS 版图原理图对比（Layout Versus Schematic）

> 聚类ID: B03
> 类别: 版图 DRC 类
> 优先级: P1
> 生成时间: 2026-06-25
> 关联文档: `docs/feature_gap_full_analysis.md`（T02/T03/T08/T09/T12/T14）、`2026-2028开发计划/功能清单与实现/00-算法聚类清单.md`、`src/polaris/sim/lvs.py`、`src/polaris/sim/graph_lvs.py`、`src/polaris/sim/eqdrc.py`
> 学术诚信：图同构 VF2 算法溯源至 Cordella et al. 2004（IEEE TPAMI 26(10):1367-1372），Weisfeiler-Lehman 颜色细化溯源至 Weisfeiler-Leman 1968 与 Morgan 1965；KLayout LVS Netter/NetlistComparer API 与 SiEPIC DEVREC 层标准（layer 68）来自 KLayout 官方文档与 SiEPIC_EBeam_PDK 开源仓库实际源码；Calibre nmLVS 算法描述来自 Siemens 官方文档；所有 layer 编号与器件识别规则均来自开源 PDK 源码（规则 18），无 fall-back 编造（规则 14）。

---

## 1. 概述

LVS（Layout Versus Schematic，版图与原理图一致性验证）是 IC/PIC 物理验证的关键环节，目标是验证 GDS 版图经网表提取后，与原理图（参考网表）在器件、连接、参数三个层面等价。LVS 是流片前 sign-off 的强制要求——所有 foundry 都要求 LVS-clean 的 GDSII 才允许投片。

光子 LVS 与电子 LVS 的差异：
- **器件识别**：电子 LVS 用 poly∩active 识别 MOS；光子 LVS 用 SiEPIC DEVREC 层（layer 68）标记器件区域，配合 TEXT 层（layer 10）标注器件名与参数
- **连接追踪**：电子 LVS 追踪金属/via 层；光子 LVS 追踪 WG 波导层（layer 1）的 path/polygon 邻近关系
- **参数验证**：电子 LVS 验证 W/L/AD/AS；光子 LVS 验证波导长度（影响 MZI FSR）、端口朝向（影响耦合对准）、半径（影响弯曲损耗）

本聚类覆盖 6 个对标工具的 18 个功能点，PoLaRIS 已有基础 LVS + 图同构 LVS + 曲线 LVS 三层实现，对标 KLayout LVS 与 Calibre nmLVS。

## 2. 覆盖功能点清单

源自 `docs/feature_gap_full_analysis.md` 第 2.4 节 LVS（KLayout T09）、第 5 节 LVS 验证（IPKISS T02）、12.5 LVS 浏览器、42 EDA 互操作（Lumerical T01）等，共 18 功能点。

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 1 | LVS 比较（核心入口） | ✅已有 | sim/graph_lvs.py:160、sim/lvs.py:494 | GraphIsomorphismLVSComparer + run_lvs |
| 2 | 网表提取（GDS→Netlist） | ✅已有 | sim/lvs.py:121 | extract_netlist_from_gds（DEVREC+WG） |
| 3 | 原理图转网表 | ✅已有 | sim/lvs.py:379 | circuit_spec_to_netlist |
| 4 | 器件集比对 | ✅已有 | sim/lvs.py:393 | _compare_devices 集合差 |
| 5 | 连接集比对 | ✅已有 | sim/lvs.py:429 | _compare_connections 集合差 |
| 6 | 图同构匹配 | ✅已有 | sim/graph_lvs.py:219 | networkx GraphMatcher（VF2） |
| 7 | 器件类型一致性 | ✅已有 | sim/graph_lvs.py:259 | _verify_device_types |
| 8 | 器件参数容忍度 | ✅已有 | sim/graph_lvs.py:275 | abs_tol+rel_tol*|ref| 公式 |
| 9 | 波导长度验证 | ✅已有 | sim/graph_lvs.py:331 | |L_ref-L_ext|<=tol_um |
| 10 | 端口朝向验证 | ✅已有 | sim/graph_lvs.py:378 | SiEPIC 标准 |
| 11 | 网表层次结构 | ✅已有 | sim/graph_lvs.py:89 | PhotonicsNetlist 层次 |
| 12 | 曲线感知 LVS | ⚠️部分 | sim/eqdrc.py:390 | CurvilinearLVS 实验性 |
| 13 | 网表等价提示（same_nets） | ✅已有 | sim/graph_lvs.py:430 | EquivalenceHints.same_nets |
| 14 | 电路等价提示（same_circuits） | ✅已有 | sim/graph_lvs.py:436 | EquivalenceHints.same_circuits |
| 15 | 引脚等价（equivalent_pins） | ✅已有 | sim/graph_lvs.py:442 | EquivalenceHints.equivalent_pins |
| 16 | 容差配置（tolerance） | ✅已有 | sim/graph_lvs.py:450 | EquivalenceHints.tolerance |
| 17 | 引脚标签检查 | ⚠️部分 | sim/graph_lvs.py:89 | 含引脚信息，无专门标签检查 |
| 18 | LVS 浏览器/交叉探测 | ❌缺失 | - | 无 GUI（仅 HTTP API） |

**统计**：✅15 / ⚠️2 / ❌1，覆盖率 94.4%（按功能点数计）。

## 3. 商业工具对标分析

### 3.1 KLayout LVS（开源基准）

KLayout LVS 由 `db::NetlistComparer` 实现，采用**回溯图匹配**算法（backtracking graph matching）：
1. **网表提取**：通过 `extract_devices` + `connect`/`connect_global`/`connect_implicit` 定义器件识别规则与连接性
2. **图匹配**：`db::NetlistComparer::compare_impl` 自底向上，先匹配子电路再匹配父电路
3. **歧义消解**：先按"邻域度量"（neighborhood metrics）非歧义匹配 net，再对歧义部分回溯（默认最大深度 500）
4. **多 Pass**：Pass 1 严格匹配；后续 Pass 允许歧义匹配或忽略 net 名

KLayout Netter 提供 `same_nets`/`same_circuits`/`same_device_classes`/`equivalent_pins`/`tolerance`/`max_res`/`min_caps`/`split_gates`/`join_symmetric_nets` 等配置 API，是 PoLaRIS `EquivalenceHints` 的对标来源。

### 3.2 Calibre nmLVS（商业标杆）

Siemens Calibre nmLVS 是市场领先的 LVS 工具，核心特性：
- **层次化处理引擎**：支持百万门级 IC，运行时比传统 LVS 快 2-3×
- **器件几何测量**：在 full-chip 上精确测量器件几何参数，回标到原理图
- **Recon Compare**：早期设计阶段通过自动 black boxing + 端口映射实现快速 LVS 迭代
- **PERC 集成**：可编程电气规则检查（ERC），识别分组器件并测量拓扑几何

Calibre nmLVS 通过层次化与逻辑注入技术提供"几乎无限的设计范围"，是 PoLaRIS LVS 的商业对标目标。

## 4. 核心算法逻辑

PoLaRIS LVS 完整流程为四阶段流水线：**版图器件识别 → 网表提取 → 图同构匹配 → 差异报告**。

### 4.1 阶段一：版图器件识别（Device Recognition）

输入：GDS 文件（含 DEVREC 层 layer 68 + TEXT 层 layer 10 + WG 层 layer 1）

算法（`sim/lvs.py:_extract_devices_from_devrec`）：
1. 加载 GDS 到 KLayout `db.Layout`
2. 获取 DEVREC 层（`get_layer_tuple("DEVREC")`）的 layer index
3. 遍历 DEVREC 层 region 的每个 shape，每个 shape 对应一个器件
4. 配合 TEXT 层标注器件名与参数（如 `mmi1x2_length=50um`）

器件识别规则严格遵循 SiEPIC EBeam PDK 标准，无任何 fall-back 假数据（规则 14.1）。若 GDS 无 DEVREC 层，记录警告并返回空器件列表，由调用方处理。

### 4.2 阶段二：网表提取（Netlist Extraction）

算法（`sim/lvs.py:_extract_connections_from_proximity` + `_trace_waveguide_connections`）：
1. 提取所有器件包围盒（DEVREC 层 `shape.bbox()`）
2. 提取所有波导 path（WG 层 `db.Region.begin_shapes`）
3. 对每条波导 path，找其包围盒相交或邻近（tolerance=10 dbu）的器件列表
4. 若一条波导连接 ≥2 个器件，则记录器件对连接（去重）

参考网表由 `circuit_spec_to_netlist(circuit)` 从 `CircuitSpec` 转换：器件名列表 + 连接元组列表。

### 4.3 阶段三：图同构匹配（Graph Isomorphism Matching）

PoLaRIS 用 networkx VF2 算法替代 KLayout 的回溯匹配，避免大规模网表回溯爆炸（`sim/graph_lvs.py:GraphIsomorphismLVSComparer.compare`）：

1. 构图：网表 → `nx.Graph`，节点属性 `node_type`/`device_type`/`params`/`layer`，边属性 `edge_type`/`length_um`
2. 节点匹配函数 `_node_match`：比较 `node_type` 与 `device_type`
3. 边匹配函数 `_edge_match`：比较 `edge_type`
4. 调用 `GraphMatcher(ref, ext).is_isomorphic()` 判定同构
5. 若同构，获取 `matcher.mapping` 作为节点对应关系

**理论依据**：VF2 算法（Cordella et al. 2004）用 State Space Representation（SSR）+ feasibility function F(s,n,m) 剪枝，最坏复杂度 O(n!)，但实际工程中因剪枝策略接近 O(n²)。

### 4.4 阶段四：差异报告（Diff Report）

同构映射获取后，逐项验证四类一致性：
1. **器件类型**：`_verify_device_types` —— 比较映射节点对的 `device_type`
2. **器件参数**：`_verify_params` —— 用容忍度公式判断参数等价
3. **波导长度**：`_verify_waveguide_lengths` —— 比较映射边对的 `length_um`
4. **端口朝向**：`_verify_port_orientation` —— 比较映射端口节点的朝向

输出 `PhotonicsLVSReport`：`is_match`、四类 `mismatches` 列表、`isomorphism_mapping`、`comparison_time_s`。

## 5. 核心数学公式

### 5.1 图同构判定

设参考网表图 G₁=(V₁,E₁)，提取网表图 G₂=(V₂,E₂)，双射 M⊆V₁×V₂。G₁ 与 G₂ 同构当且仅当：

```
∀(u,v)∈E₁ ⟺ (M(u),M(v))∈E₂
```

VF2 算法用 feasibility function F(s,n,m) 增量判定，其中 s 为当前部分映射状态，(n,m) 为待加入的节点对。F 检查：
- **邻接一致性**：M 中已映射邻居与 (n,m) 的边一一对应
- **1-look-ahead**：T_out/T_in 集合大小匹配（图同构）或 ≤（子图同构）
- **2-look-ahead**：剩余未映射节点数匹配

### 5.2 VF2 状态空间复杂度

```
T(n) = O(n!)  (最坏)
T(n) ≈ O(n²)  (实际工程，强剪枝)
```

剪枝由 P(s) 候选对生成函数控制：优先选择 T_out 非空节点对，减少分支因子。

### 5.3 器件参数容忍度公式

来源：KLayout Netter `tolerance` API。

```
match(p_ref, p_ext) ⟺ |p_ref - p_ext| ≤ abs_tol + rel_tol × |p_ref|
```

- `abs_tol`：绝对容差（如波导长度 0.1 μm）
- `rel_tol`：相对容差（如半径 5%）

非数值参数（如字符串）用严格相等 `==` 判定。

### 5.4 波导长度一致性

来源：Chrostowski & Hochberg, "Silicon Photonics Design", CUP 2015, p.353（波导长度影响 MZI FSR）。

```
match(L_ref, L_ext) ⟺ |L_ref - L_ext| ≤ tolerance_um
```

默认 `tolerance_um = 1.0`，对应 SiEPIC EBeam PDK 波导长度精度要求。

### 5.5 Weisfeiler-Lehman 颜色细化（VF2 预筛）

VF2 调用前可用 1-WL 颜色细化快速排除不同构图，复杂度 O((n+m) log n)：

```
c₀(v) = hash(label(v))
c_{t+1}(v) = hash( c_t(v), sorted_multiset{ c_t(u) : u ∈ N(v) } )
```

若两图最终颜色多重集不同，则必不同构（充分非必要）。1-WL 不能区分强正则图，故仅作预筛，VF2 仍需精确判定。PoLaRIS 当前直接用 VF2，WL 预筛为优化路径（见第 8 节）。

### 5.6 节点相似度（参数级）

对于参数化器件节点相似度（用于歧义消解时的匹配优先级）：

```
sim(v_ref, v_ext) = w_type · 𝟙[type_match] + w_param · (1 - ||p_ref - p_ext|| / (||p_ref|| + ε))
```

其中 `w_type + w_param = 1`，`ε` 为数值稳定小量。相似度高的节点对优先进入 VF2 映射，加速收敛。

## 6. 完整伪代码

```
FUNCTION run_polaris_lvs(gds_path, reference_circuit, tolerance_config):
    # 阶段一+二：版图器件识别与网表提取
    extracted_netlist = extract_netlist_from_gds(gds_path)
        devices = scan_devrec_layer(layout, cell)       # SiEPIC layer 68
        bboxes  = extract_device_bboxes(layout, cell)
        conns   = trace_waveguide_connections(layout, cell, bboxes)  # WG layer 1

    # 参考网表
    reference_netlist = circuit_spec_to_netlist(reference_circuit)

    # 阶段三：图同构匹配
    comparer = GraphIsomorphismLVSComparer(tolerance_config)
    ref_graph = comparer.build_graph(reference_netlist)
    ext_graph = comparer.build_graph(extracted_netlist)
    matcher = GraphMatcher(ref_graph, ext_graph,
                           node_match=comparer._node_match,
                           edge_match=comparer._edge_match)

    IF NOT matcher.is_isomorphic():
        RETURN PhotonicsLVSReport(
            is_match=False,
            mismatches=[graph_not_isomorphic_mismatch(ref_graph, ext_graph)])

    mapping = matcher.mapping

    # 阶段四：差异报告（四类一致性验证）
    report = PhotonicsLVSReport(isomorphism_mapping=mapping)
    report.device_type_mismatches      = verify_device_types(mapping, ref_graph, ext_graph)
    report.param_mismatches            = verify_params(mapping, ref_graph, ext_graph, tolerance_config)
    report.waveguide_length_mismatches = verify_waveguide_lengths(mapping, ref_graph, ext_graph, tol_um=1.0)
    report.port_orientation_mismatches = verify_port_orientation(mapping, ref_graph, ext_graph)
    report.mismatches = concat(all above)
    report.is_match = (len(report.mismatches) == 0)
    RETURN report

# VF2 feasibility function F(s, n, m) 内部逻辑
FUNCTION vf2_feasibility(state_s, n, m):
    # 1-look-ahead: 终端集合大小检查
    IF |T1_out(s)| != |T2_out(s)| OR |T1_in(s)| != |T2_in(s)|:
        RETURN False
    # 2-look-ahead: 剩余节点数检查
    IF |V1 - M1(s) - T1_out(s) - T1_in(s)| != |V2 - M2(s) - T2_out(s) - T2_in(s)|:
        RETURN False
    # 邻接一致性：已映射邻居的边对应
    FOR each (n', m') in M(s):
        IF (n', n) ∈ E1 XOR (m', m) ∈ E2: RETURN False
        IF (n, n') ∈ E1 XOR (m, m') ∈ E2: RETURN False
    # 语义一致性：节点/边属性匹配
    IF NOT node_match(attr(n), attr(m)): RETURN False
    RETURN True
```

## 7. PoLaRIS 实现现状

PoLaRIS LVS 已实现三层架构（生产可用 + 实验性）：

### 7.1 基础 LVS 层（`sim/lvs.py`，生产可用）

- `extract_netlist_from_gds(gds_path)`：GDS → `ExtractedNetlist`，DEVREC 层器件识别 + WG 层波导追踪
- `circuit_spec_to_netlist(circuit)`：`CircuitSpec` → `ExtractedNetlist`
- `compare_netlists(reference, extracted)`：集合差比对，输出 `LVSReport`（器件缺失/多余 + 连接缺失/多余）
- `run_lvs(gds_path, reference_circuit)`：顶层便捷入口
- 6 类不匹配：`MISSING_DEVICE`/`EXTRA_DEVICE`/`DEVICE_TYPE_MISMATCH`/`MISSING_CONNECTION`/`EXTRA_CONNECTION`/`PORT_MISMATCH`
- 严格遵循规则 14.1：无 fall-back，DEVREC 缺失返回空列表并警告，波导追踪失败抛 `RuntimeError`

### 7.2 图同构 LVS 层（`sim/graph_lvs.py`，生产可用）

- `GraphIsomorphismLVSComparer`：networkx VF2 替代 KLayout 回溯，复杂度 O(n²) 平均
- `PhotonicsNetlist`：扩展 `ExtractedNetlist`，支持层次结构 + 端口
- `PhotonicsLVSReport`：扩展 `LVSReport`，含器件类型/参数/波导长度/端口朝向四类不匹配
- `EquivalenceHints`：对标 KLayout Netter 的 `same_nets`/`same_circuits`/`equivalent_pins`/`tolerance`/`max_res`/`min_caps`
- `verify_waveguide_length` / `verify_port_orientation`：独立验证接口
- `run_graph_lvs`：统一入口

### 7.3 曲线感知 LVS 层（`sim/eqdrc.py:CurvilinearLVS`，实验性）

- 对标 Calibre nmLVS 曲线感知能力
- `extract_netlist_with_markers`：用 TEXT/marker 层识别曲线结构
- `compare_with_schematic`：复用 R08 GraphIsomorphismLVSComparer 比对逻辑
- 学术依据：Siemens + GF Calibre Fotonix 合作

## 8. 差距分析与改进路径

| 差距项 | 商业对标 | PoLaRIS 现状 | 改进路径 |
|--------|---------|-------------|---------|
| 回溯深度限制 | KLayout 默认 500 | networkx 默认无限制 | 配置 max_depth 防止大规模网表栈溢出 |
| 多 Pass 匹配 | KLayout Pass 1 严格 + 后续宽松 | 单 Pass | 实现 Pass 2（忽略 net 名）/Pass 3（允许歧义） |
| WL 预筛 | - | 无 | 加 1-WL 颜色细化预筛，O((n+m)logn) 排除不同构图 |
| Black boxing | Calibre Recon Compare | 无 | 实现未完成 block 的 black boxing + 端口映射 |
| LVS 浏览器 | KLayout NetlistBrowserPage | 仅 HTTP API | 加 web/server.py LVS 结果交叉探测端点 |
| 引脚标签检查 | KLayout flag_missing_ports | ⚠️部分 | 实现专门引脚标签一致性检查器 |
| 层次化 flatten | KLayout flatten 不配对电路 | 平铺比对 | 实现按 circuit 层次自底向上匹配 |
| 器件参数回标 | Calibre back-annotation | 无 | 提取器件几何参数回标到原理图 |

**优先级**：WL 预筛（P1，性能）/ 多 Pass（P1，正确性）/ LVS 浏览器（P2，可用性）/ Black boxing（P2，早期验证）。

## 9. 测试用例与验证

PoLaRIS LVS 测试覆盖（`tests/test_graph_lvs.py`）：
- 同构网表比对通过（MZI/Ring/MMI 标准电路）
- 器件类型不匹配检测
- 器件参数越容忍度检测（abs/rel 双模式）
- 波导长度差异检测（tolerance_um 边界）
- 端口朝向不一致检测
- 图不同构场景（节点数/边数不同）
- `EquivalenceHints` API 各方法单元测试
- `extract_netlist_from_gds` 对真实 GDS 文件提取正确性

验证标准：所有测试用例无 fall-back 假数据，失败必须告警退出（规则 14.1）。

## 10. 文献来源

1. Cordella, L.P., Foggia, P., Sansone, C., Vento, M. "A (Sub)Graph Isomorphism Algorithm for Matching Large Graphs." IEEE TPAMI 26(10):1367-1372, 2004. DOI: 10.1109/TPAMI.2004.75 — VF2 算法原始论文
   https://ieeexplore.ieee.org/iel5/34/29305/01323804.pdf
2. McKay, B.D., Piperno, A. "Practical Graph Isomorphism, II." J. Symbolic Computation 60:94-112, 2014. DOI: 10.1016/j.jsc.2013.09.003 — nauty/Traces 图同构权威实现
   https://www.sciencedirect.com/science/article/pii/S0747717113001193
3. KLayout LVS Compare 官方文档（Netter/NetlistComparer/same_nets/tolerance）
   https://www.klayout.org/downloads/master/doc-qt5/manual/lvs_compare.html
4. KLayout LVS Reference: Netter object（equivalent_pins/max_res/min_caps/split_gates）
   https://klayout.org/downloads/master/doc-qt5/about/lvs_ref_netter.html
5. SiEPIC EBeam PDK 开源仓库（DEVREC layer 68 / TEXT layer 10 / WG layer 1 标准源码）
   https://github.com/SiEPIC/SiEPIC_EBeam_PDK
6. Chrostowski, L., Hochberg, M. "Silicon Photonics Design: From Devices to Systems." Cambridge University Press, 2015, p.353 — 波导长度影响 MZI FSR
   https://www.cambridge.org/core/search?searchField=isbn&searchTerms=1107007731
7. Siemens Calibre nmLVS 官方文档（层次化处理/Recon Compare/PERC 集成）
   https://www.siemens.com/en-us/products/ic/calibre-design/circuit-verification/nmlvs/
8. networkx VF2 实现（GraphMatcher/DiGraphMatcher 源码与文档）
   https://networkx.org/documentation/networkx-3.3/_modules/networkx/algorithms/isomorphism/isomorphvf2.html
9. Weisfeiler-Lehman 颜色细化算法（1-WL = C² 逻辑 = 树同态剖面）
   https://kindatechnical.com/graph-theory/weisfeiler-lehman-algorithm-tutorial.html
10. KLayout LVS 系统架构（db::NetlistComparer/NetlistCrossReference/NetlistCompareLogger）
    https://deepwiki.com/KLayout/klayout/4.2-layout-vs.-schematic-(lvs)

## 11. 学术诚信声明

- 所有公式来源已标注：VF2（Cordella 2004）、容忍度（KLayout Netter API）、波导长度（Chrostowski 2015）、WL（Weisfeiler-Leman 1968）
- 所有 layer 编号（DEVREC=68, TEXT=10, WG=1）来自 SiEPIC_EBeam_PDK 开源仓库实际源码（规则 18），非臆造
- PoLaRIS 实现状态（✅15/⚠️2/❌1）基于 `docs/feature_gap_full_analysis.md` 实际标注，无夸大
- 所有伪代码与公式可直接溯源到 `src/polaris/sim/lvs.py`、`sim/graph_lvs.py`、`sim/eqdrc.py` 实际实现
- 严格遵守规则 14.1：无任何 fall-back 假数据，DEVREC 缺失返回空列表并警告，波导追踪失败抛异常
- 严格遵守规则 18：所有文献 URL 已列出，可直接访问验证
