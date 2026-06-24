# 执行计划：依次完成 R03-R36 所有路标

**计划创建日期**: 2026-06-22
**计划范围**: R03（2026-09）→ R36（2029-06），共 34 个路标，6 个阶段
**目标**: 综合得分 6.5 → 9.2（超越行业最高 9.0）
**执行原则**: 依次完成，不等待；每个路标完整交付（代码+测试+文档+操作记录）

---

## 一、Summary（概要）

本计划依次执行 PoLaRIS 36-RoundMap 的 R03-R36 共 34 个路标，按 6 个阶段递进：

| 阶段 | 路标范围 | 追赶对象 | 得分区间 | 核心能力 |
|------|---------|---------|---------|---------|
| 阶段1（剩余） | R03-R06 | sax + simphony | 6.5→6.8 | S参数级联优化、子网络增长、JAX加速、阶段验收 |
| 阶段2 | R07-R12 | KLayout + gdsfactory | 6.8→7.4 | DRC/LVS、PDK生态、路由策略、PCell |
| 阶段3 | R13-R18 | Aspic + VPIphotonics | 7.4→7.9 | 频域S参数、系统级仿真、时域、layout-aware |
| 阶段4 | R19-R24 | L-Edit + OptoDesigner | 7.9→8.4 | GPIC iPDK、版图驱动、自动布线、eqDRC认证 |
| 阶段5 | R25-R30 | IPKISS + Tidy3D | 8.4→8.8 | PCell三视图、CAPHE、GPU FDTD、adjoint逆向设计 |
| 阶段6 | R31-R36 | Lumerical + AlphaChip | 8.8→9.2 | 3D FDTD、INTERCONNECT、Edge-GNN、预训练-微调 |

---

## 二、Current State Analysis（当前状态分析）

### 2.1 已完成路标
- **R01**（2026-07）：sax 频域 S 参数仿真对齐 ✅
  - 修复 cascade.py fall-back 兜底
  - SDict 切换到 jax.numpy 支持自动微分
  - 双后端自动切换（backend_selector.py）
  - 器件模型库扩展到 22 个
  - 78 个新测试全部通过

- **R02**（2026-08）：simphony 光子电路仿真对齐 ✅
  - simphony 兼容 API（subcircuit.py）
  - SiEPIC 缺失模型（half_ring/taper/add_drop_ring + Sellmeier 色散）
  - 群延迟和色散分析
  - SiEPIC JSON 网表解析器
  - 49 个 R02 新测试全部通过

### 2.2 当前测试状态
- 完整套件：2477 passed, 16 skipped, 1 failed
- 1 个预存失败（test_tilos_benchmark，与路标改动无关）

### 2.3 当前 Git 状态
- commit ce36b42（R02 已合并 main）
- 分支：trae/solo-agent-QtGqG4-ai-Light
- auto_merge 6 分钟提交机制持续运行

### 2.4 现有核心代码（sim 模块）
- `cascade.py`（399 行）：S 参数级联器，纯 numpy 子网络增长 + SAX 后端
- `simulator.py`（433 行）：电路仿真器 + 群延迟 + 色散分析
- `models.py` / `models_extended.py`：22+ 器件模型
- `types.py`：SDict 数据结构
- `backend_selector.py`（215 行）：双后端自动切换
- `netlist_adapter.py`（295 行）：网表格式适配器
- `subcircuit.py`（210 行）：simphony 兼容 API
- `siepic_netlist.py`（246 行）：SiEPIC JSON 网表解析器

### 2.5 现有其他模块
- `engine/`：放置引擎（analytical_placer, gnn, gpu_backend 等）
- `router/`：布线引擎（curvy_router, diagonal_router, global_router 等）
- `pdk/`：PDK 库（SOI/SiN/LNOI/InP + foundry_devices）
- `trainer/`：RL 训练（PPO, GNN, BC, vtrace）
- `data/`：基准测试（apollo, tilos, lidar, siepic）
- `nn/`：神经网络层（attention, conv, functional）

---

## 三、Proposed Changes（按阶段详细改动）

### 阶段 1 剩余：R03-R06（sax + simphony 验收）

#### R03（2026-09）：S 参数级联优化，6.5→6.6

**交付目标**: 删除所有 fall-back，KLU 稀疏求解后端，Redheffer 星积向量化，条件数监控

**代码改动**:
1. **`src/polaris/sim/cascade.py`**（修改）:
   - 新增 `cascade_klu()`: 使用 klujax 实现 KLU 稀疏求解
   - 新增 `_build_circuit_matrix()`: 构建稀疏电路矩阵 M = I - S_block
   - 新增 `redheffer_star()`: 向量化 Redheffer 星积 S' = S_direct + S_cross·(I - S_feedback)⁻¹·S_through
   - 新增 `cascade_additive()`: 前向累加后端
   - 新增 `cascade_forward_only()`: 单向传播后端
   - 新增 `cascade_auto()`: 基于条件数自动选择后端
   - 修复实例名替换 bug（第 227-228 行字符串替换改为精确端口引用解析）

2. **`src/polaris/sim/backend_selector.py`**（扩展）:
   - 新增 `condition_number(S)`: 计算条件数 κ(S) = ||S||·||S⁻¹||
   - 新增 `diagnose_stability(S)`: 数值稳定性诊断报告

3. **`tests/test_cascade.py`**（扩展）:
   - 新增 KLU 后端测试（1000+ 器件电路）
   - 新增向量化 Redheffer 星积测试
   - 新增条件数监控测试
   - 新增自动后端切换测试

**验收标准**:
- 1000+ 器件电路稳定求解（无 NaN/Inf）
- 向量化 Redheffer 星积比逐端口消元快 5+ 倍
- 与 sax KLU 后端结果对比误差 < 1e-10
- 测试覆盖率 ≥ 90%

---

#### R04（2026-10）：子网络增长算法，6.6→6.7

**交付目标**: 块三对角矩阵子网络分解，Schur 补计算，DAG 并行调度

**代码改动**:
1. **`src/polaris/sim/cascade.py`**（扩展）:
   - 新增 `block_tridiagonal_solve()`: 块版本 Thomas 算法
   - 新增 `schur_complement()`: Schur 补 S = D - C·A⁻¹·B
   - 新增 `decompose_subnetworks()`: 基于图分割的自动子网络分解

2. **`src/polaris/sim/dag_scheduler.py`**（新建）:
   - `create_dag()`: 构建电路 DAG
   - `topological_sort()`: DAG 拓扑排序
   - `find_leaves()` / `find_root()`: 叶节点/根节点识别
   - `parallel_schedule()`: 并行调度独立子网络

3. **`tests/test_dag_scheduler.py`**（新建）:
   - DAG 创建和拓扑排序测试
   - 并行子网络合并测试
   - 块三对角求解测试
   - Schur 补测试

**验收标准**:
- 10000+ 器件电路求解 < 60 秒
- DAG 并行调度 8 核 CPU 加速 6+ 倍
- 块三对角求解比稠密求解快 100+ 倍

---

#### R05（2026-11）：JAX 加速集成，6.7→6.8

**交付目标**: 核心数据结构迁移到 jax.numpy，JIT 编译，自动微分，GPU 加速

**代码改动**:
1. **`src/polaris/sim/types.py`**（修改）:
   - 新增 `JaxSDict` 类型别名
   - SDict 支持 numpy/jax 双后端
   - ModelFunc 协议支持 jax 数组

2. **`src/polaris/sim/jax_backend.py`**（新建）:
   - `jit_simulate()`: JAX JIT 编译仿真
   - `grad_simulate()`: 自动微分梯度计算
   - `vjp_simulate()` / `jvp_simulate()`: VJP/JVP
   - `vmap_simulate()`: 向量化并行
   - `monte_carlo()`: 蒙特卡洛分析
   - `optimize()`: 梯度优化

3. **`src/polaris/sim/models.py`** / **`models_extended.py`**（修改）:
   - 所有模型函数支持 jax.numpy（通过 ArrayLike 抽象）

4. **`tests/test_jax_backend.py`**（新建）:
   - JIT 编译性能测试（5+ 倍加速）
   - 自动微分有限差分验证
   - 蒙特卡洛分析测试
   - GPU 加速测试（如可用）

**验收标准**:
- JIT 编译性能提升 5+ 倍
- 自动微分通过有限差分验证（误差 < 1e-6）
- 蒙特卡洛分析支持 1000+ 变体
- GPU 加速 50+ 倍（大规模电路，如可用）

---

#### R06（2026-12）：阶段 1 验收，6.8

**交付目标**: 阶段 1 整体验收，sax + simphony 100% 复刻确认

**代码改动**:
1. **`tests/test_stage1_acceptance.py`**（新建）:
   - sax API 兼容性测试（≥ 95%）
   - simphony API 兼容性测试（≥ 95%）
   - 回归测试基准（与 sax/simphony 对比误差 < 1e-10）
   - 大规模电路稳定性测试（10000+ 器件）
   - JAX 加速性能基准
   - 自动微分验证
   - 测试覆盖率验证（≥ 90%）

2. **`docs/stage1_acceptance_report.md`**（新建）:
   - 阶段 1 总结报告
   - 综合得分 6.8 确认
   - 阶段 2 规划

**验收标准**:
- 综合得分 6.8
- sax + simphony 功能复刻 100%
- 测试覆盖率 ≥ 90%
- 50+ 集成测试用例通过

---

### 阶段 2：R07-R12（KLayout + gdsfactory）

#### R07（2027-01）：KLayout DRC 引擎深度对齐，6.8→7.0

**交付目标**: 6 类核心 DRC 检查完整复刻，8 项 foundry-grade DRC 规则，层次化 DRC

**代码改动**:
1. **`src/polaris/sim/klayout_drc.py`**（扩展）:
   - 6 类核心 DRC：width/space/notch/enclosed/area/density
   - 8 项 foundry-grade：density/enclosure/antenna/step coverage 等
   - 层次化 DRC 模式
   - layer-wise BVH 加速
   - 自适应行分块
   - 非曼哈顿几何 DRC

2. **`tests/test_klayout_drc.py`**（扩展）:
   - 6 类核心 DRC 测试
   - 8 项 foundry-grade 测试
   - 层次化 DRC 性能测试

---

#### R08（2027-02）：KLayout LVS 完整对齐，7.0→7.2

**交付目标**: Netter API 100% 复刻，图同构网表比对，光子专用 LVS

**代码改动**:
1. **`src/polaris/sim/lvs.py`**（扩展）:
   - Netter API: extract_devices/connect/compare/same_nets
   - 图同构算法（nauty/Traces 或 VF2）
   - 光子专用 LVS（波导长度/端口朝向/器件参数比对）
   - DEVREC/TEXT/WG/PinRec 层标准

2. **`tests/test_lvs.py`**（扩展）:
   - Netter API 测试
   - 图同构测试
   - 光子专用 LVS 测试

---

#### R09（2027-03）：gdsfactory 43+ PDK 生态桥接，7.2→7.3

**交付目标**: 43+ PDK 100% 桥接，Component/CrossSection/LayerStack/Port 四大抽象转换

**代码改动**:
1. **`src/polaris/pdk/gdsfactory_integration.py`**（扩展）:
   - 43+ PDK 桥接（ubcpdk/gf180mcu/ihp/skywater130 等）
   - Component/CrossSection/LayerStack/Port 转换
   - YAML 布局生成解析
   - 原生 PDK 注册机制

2. **`tests/test_gdsfactory_integration.py`**（扩展）:
   - 43+ PDK 桥接测试
   - 四大抽象转换测试

---

#### R10（2027-04）：gdsfactory routing strategies 对齐，7.3→7.35

**交付目标**: routing strategies 100% 对齐，JPS 剪枝加速 A*，curvy-aware routing

**代码改动**:
1. **`src/polaris/router/`**（扩展）:
   - route_single/route_bundle/all_angle/path_length_match/Dubins paths
   - JPS 剪枝加速 A*（5-15×）
   - curvy-aware routing
   - adaptive crossing insertion

2. **`tests/test_router.py`**（扩展）:
   - routing strategies 测试
   - JPS 性能测试

---

#### R11（2027-05）：gdsfactory + KLayout PCell 对齐，7.35→7.4

**交付目标**: Code-as-Layout 范式对齐，@gf.cell 装饰器 100% 复刻，KLayout PCell 桥接

**代码改动**:
1. **`src/polaris/pdk/gdsfactory_integration.py`**（扩展）:
   - @gf.cell 装饰器复刻（缓存/参数校验/命名唯一性/info 元数据）
   - 参数化变换矩阵引擎
   - 参数化器件 50→200+

2. **`src/polaris/pdk/klayout_pcell.py`**（新建）:
   - KLayout PCell 桥接（C++ db::PCell 与 Ruby PCellDeclaration）

3. **`tests/test_pcell.py`**（新建）:
   - @gf.cell 装饰器测试
   - KLayout PCell 桥接测试

---

#### R12（2027-06）：阶段 2 验收，6.8→7.4

**交付目标**: 阶段 2 整体验收，端到端集成测试，性能基准

**代码改动**:
1. **`tests/test_stage2_acceptance.py`**（新建）:
   - KLayout + gdsfactory 功能对比矩阵
   - 端到端集成测试
   - 性能基准测试

2. **`docs/stage2_acceptance_report.md`**（新建）:
   - 阶段 2 总结报告
   - 综合得分 7.4 确认
   - 阶段 3 规划

---

### 阶段 3：R13-R18（Aspic + VPIphotonics）

#### R13（2027-07）：Aspic 频域 S 参数电路仿真对齐，7.4→7.55

**交付目标**: building block 级联，传输矩阵 T=(M₊+M₋)⁻¹(M₊−M₋)，虚拟实验扫描

**代码改动**:
1. **`src/polaris/sim/aspic_backend.py`**（新建）:
   - 传输矩阵形式化
   - building block 级联
   - what-if 扫描
   - 与 Aspic 公开案例数值对齐（误差 < 1e-4）

2. **`tests/test_aspic_backend.py`**（新建）:
   - MZI/Ring/MMI 对齐测试

---

#### R14（2027-08）：VPIphotonics 系统级仿真对齐，7.55→7.65

**交付目标**: 时域+频域+TLLM 三种模式，信号流图（SFG）抽象，≥3 个光通信链路示例

**代码改动**:
1. **`src/polaris/sim/vpi_backend.py`**（新建）:
   - TLLM（Transmission-Line Laser Model）
   - 信号流图（SFG）抽象
   - Mason 增益公式
   - 频域 S-matrix + 时域 TLLM 混合框架
   - NRZ/PAM4/QAM 链路示例

2. **`tests/test_vpi_backend.py`**（新建）:
   - 时域/频域/TLLM 测试
   - 光通信链路测试

---

#### R15（2027-09）：VPItoolkit PDK <fab> 体系对齐，7.65→7.75

**交付目标**: ≥3 个 VPI 风格 foundry 模型库，PDAflow API 标准 BB 交换

**代码改动**:
1. **`src/polaris/pdk/vpi_foundry.py`**（新建）:
   - HHI/LIGENTEC/LioniX 模型库
   - BB 参数化模型
   - PDAflow API 标准

2. **`tests/test_vpi_foundry.py`**（新建）:
   - 3+ foundry 模型库测试

---

#### R16（2027-10）：时域光子电路仿真对齐，7.75→7.85

**交付目标**: 非线性效应（Kerr/TPA/FCD），FDTD 风格时域波动方程求解，CFL 稳定性

**代码改动**:
1. **`src/polaris/sim/time_domain.py`**（新建）:
   - Yee 1966 算法
   - Berenger PML 吸收边界
   - CFL 稳定性条件
   - 非线性效应（Kerr/TPA/FCD）
   - 200 器件时域仿真 < 60 秒

2. **`tests/test_time_domain.py`**（新建）:
   - 时域仿真测试
   - 非线性效应测试
   - PML 吸收边界测试

---

#### R17（2027-11）：layout-aware 仿真对齐，7.85→7.9

**交付目标**: smart elastic optical connector 模型，寄生参数提取，与 PoLaRIS 布局布线集成

**代码改动**:
1. **`src/polaris/sim/layout_aware.py`**（新建）:
   - smart elastic connector
   - 寄生参数提取（rule-based + field-solver）
   - layout→电路反馈循环

2. **`tests/test_layout_aware.py`**（新建）:
   - 寄生参数提取测试
   - layout-aware 仿真测试

---

#### R18（2027-12）：阶段 3 验收，7.9

**交付目标**: 阶段 3 整体验收，Aspic 频域/VPI 系统级/PDK/时域/layout-aware 全部对齐

**代码改动**:
1. **`tests/test_stage3_acceptance.py`**（新建）
2. **`docs/stage3_acceptance_report.md`**（新建）

---

### 阶段 4：R19-R24（L-Edit + OptoDesigner）

#### R19（2028-01）：L-Edit GPIC iPDK 对齐，7.9→8.0

**交付目标**: ≥15 个基础 BB 器件库映射，版图驱动网表提取，与 Lumerical INTERCONNECT 互操作

**代码改动**:
1. **`src/polaris/pdk/ledit_gpic.py`**（新建）:
   - GPIC iPDK 器件库映射
   - 版图驱动网表提取
   - SPICE 网表导出（.spi）
   - 层映射/工艺节点/设计规则

2. **`tests/test_ledit_gpic.py`**（新建）

---

#### R20（2028-02）：OptoDesigner 版图驱动对齐，8.0→8.1

**交付目标**: Python 脚本 PyCells，Design Intent 机制，Any-angle flexConnector

**代码改动**:
1. **`src/polaris/pdk/optodesigner.py`**（新建）:
   - PyCells 脚本化布局
   - Design Intent 机制（单层设计→多层掩膜）
   - Any-angle flexConnector
   - PDAflow 互操作

2. **`tests/test_optodesigner.py`**（新建）

---

#### R21（2028-03）：OptoDesigner 自动布线 + LiDAR SOTA，8.1→8.2

**交付目标**: 曲线感知 A* 布线引擎，自适应交叉插入，拥塞感知网排序，≥1000 器件

**代码改动**:
1. **`src/polaris/router/curvy_router.py`**（扩展）:
   - 曲线感知 A*（8 方向+弯曲半径约束）
   - 自适应交叉插入
   - 拥塞感知网排序 + Rip-up & Reroute
   - RUDY 拥塞预估
   - DRV-free 版图生成

2. **`tests/test_curvy_router.py`**（扩展）

---

#### R22（2028-04）：高级波导连接器对齐，8.2→8.3

**交付目标**: 弹性连接器，路径长度定义连接器，相位匹配路由，欧拉螺旋/贝塞尔曲线

**代码改动**:
1. **`src/polaris/router/advanced_connectors.py`**（新建）:
   - 弹性连接器
   - 路径长度定义连接器（等长约束）
   - 相位匹配路由（MZI 臂/差分对）
   - RF GSG 路由
   - 欧拉螺旋（clothoid）
   - 高阶贝塞尔曲线
   - partial Euler bends

2. **`tests/test_advanced_connectors.py`**（新建）

---

#### R23（2028-05）：Calibre eqDRC + nmLVS 认证，8.3→8.35

**交付目标**: 方程化 DRC 引擎（eqDRC），曲线感知 LVS，多 foundry DRC runset 认证

**代码改动**:
1. **`src/polaris/sim/eq_drc.py`**（新建）:
   - eqDRC 方程化 DRC
   - 曲线感知多维规则
   - curvilinear LVS
   - text/marker 层识别
   - DRC 违反自动修复建议

2. **`src/polaris/sim/foundry_runsets.py`**（扩展）:
   - 7+ foundry 认证（AMF/IHP/GF Fotonix/CompoundTek/LIGENTEC/LioniX）

3. **`tests/test_eq_drc.py`**（新建）

---

#### R24（2028-06）：阶段 4 验收，8.35→8.4

**交付目标**: 阶段 4 综合验收，5 维度全面追赶验证，大规模 PIC 端到端测试

**代码改动**:
1. **`tests/test_stage4_acceptance.py`**（新建）
2. **`docs/stage4_acceptance_report.md`**（新建）

---

### 阶段 5：R25-R30（IPKISS + Tidy3D）

#### R25（2028-07）：IPKISS 全流程对齐，8.4→8.5

**交付目标**: PCell/SDL/CircuitModel 三视图体系，SDL 闭环，post-layout 仿真

**代码改动**:
1. **`src/polaris/pdk/ipkiss_compat.py`**（新建）:
   - PCell 多视图抽象（五元组）
   - SDL 闭环
   - 视图间一致性约束
   - post-layout 仿真

2. **`tests/test_ipkiss_compat.py`**（新建）

---

#### R26（2028-08）：IPKISS CAPHE 电路仿真器对齐，8.5→8.6

**交付目标**: 节点抽象（S 参数+状态变量+ODE），频域消去，时域 CMT 快速求解

**代码改动**:
1. **`src/polaris/sim/caphe_backend.py`**（新建）:
   - CAPHE 节点抽象（六元组）
   - 稀疏矩阵分解（scipy.sparse.linalg.splu）
   - CMT 耦合模理论
   - 频域消去算法
   - 与 sax/simphony 交叉验证误差 < 1e-4

2. **`tests/test_caphe_backend.py`**（新建）

---

#### R27（2028-09）：Tidy3D 云 API 深度集成，8.6→8.7

**交付目标**: GPU 加速 FDTD 全波电磁仿真，完整 S 参数提取，亚像素精度验证

**代码改动**:
1. **`src/polaris/sim/fdtd_tidy3d_backend.py`**（扩展）:
   - Tidy3D 云 API 集成
   - GPU 加速 FDTD（10-5000× 速度提升）
   - 完整 S 参数提取流程
   - 亚像素精度验证
   - 异步任务管理
   - Tidy3D vs MEEP 交叉验证误差 < 1e-3

2. **`tests/test_fdtd_tidy3d_backend.py`**（扩展）

---

#### R28（2028-10）：Tidy3D GPU FDTD 引擎核心能力对齐，8.7→8.75

**交付目标**: Yee 网格并行更新，PML 吸收边界，亚像素介质边界，色散材料建模，本地 CPU/GPU 运行等价 FDTD

**代码改动**:
1. **`src/polaris/sim/fdtd_gpu.py`**（新建）:
   - Yee 网格并行更新
   - PML 吸收边界
   - 亚像素介质边界
   - 色散材料建模
   - JAX/PyTorch GPU 后端
   - 内存带宽优化
   - 多 GPU 并行扩展

2. **`tests/test_fdtd_gpu.py`**（新建）

---

#### R29（2028-11）：adjoint method 逆向设计完整实现，8.75→8.8

**交付目标**: 拓扑优化（水平集+二值化），制造约束，多目标优化，≥3 逆向设计示例

**代码改动**:
1. **`src/polaris/sim/adjoint_optimizer.py`**（扩展）:
   - adjoint method（两次仿真计算梯度）
   - 拓扑优化
   - 水平集
   - 二值化
   - 制造约束（最小特征尺寸+连通性）
   - NSGA-II/MOEA 多目标优化
   - **创新：AdjointDiffusion（DDPM + adjoint）**

2. **`tests/test_adjoint_optimizer.py`**（扩展）:
   - MMI/光栅耦合器/模式转换器逆向设计测试

---

#### R30（2028-12）：阶段 5 验收，8.8

**交付目标**: 阶段 5 整体验收，IPKISS + Tidy3D 所有核心功能 100% 复刻验证

**代码改动**:
1. **`tests/test_stage5_acceptance.py`**（新建）
2. **`docs/stage5_acceptance_report.md`**（新建）

---

### 阶段 6：R31-R36（Lumerical + AlphaChip）

#### R31（2029-01）：Lumerical FDTD 3D 全波电磁仿真 100% 复刻，8.8→8.93

**交付目标**: 3D Yee 网格，PML 边界，CFL 稳定性，模式源/监视器，S 参数提取，可微分 FDTD（创新）

**代码改动**:
1. **`src/polaris/sim/fdtd_3d.py`**（新建）:
   - 3D Yee 网格
   - Berenger 分裂场 PML / Gedney 单轴各向异性 PML
   - CFL 条件
   - 模式源/监视器
   - S 参数提取
   - MEEP/Tidy3D 双后端
   - **创新：JAX 可微分 FDTD**

2. **`tests/test_fdtd_3d.py`**（新建）

---

#### R32（2029-02）：Lumerical INTERCONNECT 100% 复刻，8.93→9.05

**交付目标**: 时域/频域双向仿真，S 参数级联，CML 编译器，ONA，WDM 仿真，统计眼图分析

**代码改动**:
1. **`src/polaris/sim/interconnect.py`**（新建）:
   - 时域/频域双向仿真
   - S 参数级联（子网络增长算法）
   - CML 编译器
   - ONA（光学网络分析仪）
   - WDM 仿真
   - 统计眼图分析
   - SiPANN 解析模型
   - **创新：JAX 加速频域仿真**

2. **`tests/test_interconnect.py`**（新建）

---

#### R33（2029-03）：AlphaChip Edge-GNN 100% 复刻，9.05→9.13

**交付目标**: 边特征图神经网络，可微消息传递，注意力机制，图级读出，与 PPO 联合训练

**代码改动**:
1. **`src/polaris/trainer/edge_gnn.py`**（新建）:
   - Edge-GNN 边特征消息传递
   - R-GCN 关系图卷积
   - 可微消息传递
   - 注意力机制
   - 图级读出
   - 与 PPO 联合训练
   - Circuit Training 开源框架参考
   - **创新：光电子专用边特征设计**

2. **`src/polaris/trainer/gnn_ppo.py`**（扩展）:
   - Edge-GNN 作为 PoLaRIS AI 布局引擎状态编码器

3. **`tests/test_edge_gnn.py`**（新建）

---

#### R34（2029-04）：AlphaChip 预训练-微调范式 100% 复刻，9.13→9.20

**交付目标**: 预训练数据集构建，课程学习，迁移学习，checkpoint 管理，多平台迁移学习（创新）

**代码改动**:
1. **`src/polaris/trainer/pretrain_finetune.py`**（新建）:
   - 预训练数据集构建（MZI/Clements/Ring/Splitter Tree）
   - 课程学习
   - 迁移学习
   - checkpoint 管理
   - hMetis 分组（适配光电子）
   - **创新：多平台迁移学习**

2. **`tests/test_pretrain_finetune.py`**（新建）

---

#### R35（2029-05）：Lumerical Verilog-A + 量子光子，9.20→9.27

**交付目标**: 光电协同仿真（Verilog-A + Cadence Virtuoso/Spectre），量子光子电路仿真，可微分量子光子仿真（创新）

**代码改动**:
1. **`src/polaris/sim/verilog_a.py`**（新建）:
   - Verilog-A 紧凑模型
   - SPICE 联合仿真
   - PAM4 调制器/相干接收机

2. **`src/polaris/sim/quantum_photonics.py`**（新建）:
   - 玻色采样
   - GBS（高斯玻色采样）
   - 线性光学量子计算
   - HOM 干涉
   - 矩阵积和式（Ryser 算法）
   - BosonSampling.jl 参考
   - **创新：可微分量子光子仿真**

3. **`tests/test_verilog_a.py`** / **`tests/test_quantum_photonics.py`**（新建）

---

#### R36（2029-06）：阶段 6 总验收，9.27→9.2（最终目标，超越行业最高 9.0）

**交付目标**: 36 个月路标最终验收，阶段 6 所有功能整合测试，发布 PoLaRIS v9.2 正式版

**代码改动**:
1. **`tests/test_stage6_acceptance.py`**（新建）:
   - 15 维度全面对齐或超越顶级商业 + AI 工具
   - MacroPlacement 基准对比
   - 可微分 FDTD 基准对比（fdtdx）

2. **`docs/stage6_acceptance_report.md`**（新建）:
   - 36 个月路标最终验收报告
   - PoLaRIS v9.2 正式版发布文档
   - 完整文档/测试套件/预训练 checkpoint/示例库

---

## 四、Assumptions & Decisions（假设与决策）

### 4.1 假设
1. **klujax 可用**: R03 KLU 后端依赖 klujax，假设已在 `/workspace/3dtool/wheels/gdsfactory/` 中
2. **JAX 可用**: R05 JAX 加速依赖 jax + jaxlib，假设已安装
3. **Tidy3D API 可用**: R27 Tidy3D 云 API 集成假设有 API key（如无则跳过云部分，保留本地 FDTD）
4. **MEEP 可用**: R31 Lumerical FDTD 双后端之一假设 MEEP 已安装
5. **GPU 可用**: R05/R28/R31 GPU 加速测试假设有 GPU 环境（如无则跳过 GPU 测试，保留 CPU 测试）

### 4.2 决策
1. **依次执行**: 严格按 R03→R04→...→R36 顺序执行，每个路标完整交付后再进入下一个
2. **每个路标完整交付**: 代码 + 测试 + 文档 + 操作记录，不留半成品
3. **禁止 fall-back**: 所有数值不稳定问题通过正确后端选择解决，不兜底
4. **学术诚信**: 所有引用论文真实可溯源，创新点标注"创新"并记录逻辑
5. **6 分钟提交**: auto_merge 持续运行，每个路标完成后立即提交
6. **质量门禁**: 圈复杂度 ≤ 15，函数行数 ≤ 40，参数个数 ≤ 5，文件行数 ≤ 500
7. **测试覆盖率**: 每个路标测试覆盖率 ≥ 90%

### 4.3 风险与缓解
1. **风险**: 部分依赖（klujax/Tidy3D/MEEP）可能未安装
   - **缓解**: 执行前检查依赖，缺失则安装；无法安装则跳过该部分，保留已有能力
2. **风险**: 大规模电路测试可能超时
   - **缓解**: 使用 pytest-timeout 设置超时，超时用例标记 skip
3. **风险**: 文件行数超 500
   - **缓解**: 拆分到新文件（如 models.py → models_extended.py → models_quantum.py）

---

## 五、Verification Steps（验证步骤）

### 5.1 每个路标的验证流程
1. **代码实现**: 按 R03.md-R36.md 详细技术文档实现
2. **单元测试**: 新增测试用例全部通过
3. **回归测试**: 完整测试套件无新增失败
4. **文档更新**: 操作记录.md 追加新一轮记录
5. **Git 提交**: auto_merge 6 分钟提交，合并 main

### 5.2 阶段验收的验证流程
1. **集成测试**: 阶段内所有路标集成测试通过
2. **性能基准**: 性能指标达标（JIT 5+ 倍、GPU 50+ 倍等）
3. **回归测试**: 与 sax/simphony/KLayout/gdsfactory 等对比误差达标
4. **综合得分**: 加权计算确认得分提升
5. **验收报告**: 发布阶段验收报告

### 5.3 最终验收（R36）
1. **15 维度全面对齐**: 商业工具功能矩阵所有维度 ≥ 9.0
2. **端到端测试**: 从网表→布局→布线→仿真→优化→版图全流程
3. **性能基准**: 与 Lumerical + AlphaChip 全面对比
4. **PoLaRIS v9.2 发布**: 完整文档/测试套件/预训练 checkpoint/示例库

---

## 六、执行顺序（TodoList）

按以下顺序依次执行，每个路标作为一个独立任务：

**阶段 1 剩余**:
1. R03: S 参数级联优化（KLU + Redheffer 星积向量化）
2. R04: 子网络增长算法（块三对角 + Schur 补 + DAG）
3. R05: JAX 加速集成（JIT + 自动微分 + GPU）
4. R06: 阶段 1 验收

**阶段 2**:
5. R07: KLayout DRC 引擎深度对齐
6. R08: KLayout LVS 完整对齐
7. R09: gdsfactory 43+ PDK 生态桥接
8. R10: gdsfactory routing strategies 对齐
9. R11: gdsfactory + KLayout PCell 对齐
10. R12: 阶段 2 验收

**阶段 3**:
11. R13: Aspic 频域 S 参数电路仿真对齐
12. R14: VPIphotonics 系统级仿真对齐
13. R15: VPItoolkit PDK <fab> 体系对齐
14. R16: 时域光子电路仿真对齐
15. R17: layout-aware 仿真对齐
16. R18: 阶段 3 验收

**阶段 4**:
17. R19: L-Edit GPIC iPDK 对齐
18. R20: OptoDesigner 版图驱动对齐
19. R21: OptoDesigner 自动布线 + LiDAR SOTA
20. R22: 高级波导连接器对齐
21. R23: Calibre eqDRC + nmLVS 认证
22. R24: 阶段 4 验收

**阶段 5**:
23. R25: IPKISS 全流程对齐
24. R26: IPKISS CAPHE 电路仿真器对齐
25. R27: Tidy3D 云 API 深度集成
26. R28: Tidy3D GPU FDTD 引擎核心能力对齐
27. R29: adjoint method 逆向设计完整实现
28. R30: 阶段 5 验收

**阶段 6**:
29. R31: Lumerical FDTD 3D 全波电磁仿真 100% 复刻
30. R32: Lumerical INTERCONNECT 100% 复刻
31. R33: AlphaChip Edge-GNN 100% 复刻
32. R34: AlphaChip 预训练-微调范式 100% 复刻
33. R35: Lumerical Verilog-A + 量子光子
34. R36: 阶段 6 总验收，PoLaRIS v9.2 发布

---

## 七、备注

1. **本计划为依次执行的总体计划**，每个路标的具体实现细节参考对应的 `docs/roundmap/R03.md` ~ `R36.md` 详细技术文档
2. **每个路标完成后**：更新操作记录.md、刷新文档版本号、提交代码合并 main
3. **如遇阻塞**：立即告警退出，不使用 fall-back 兜底
4. **创新点标注**：所有创新点在代码注释和文档中标注"创新"，记录创新逻辑和支持理论
5. **学术诚信**：所有引用论文真实可溯源，公式标注推导来源和适用条件
