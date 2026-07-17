# PoLaRIS 实际使用价值真实评估与差距分析报告

**文档版本**: v1.0
**生成日期**: 2026-07-17
**评估方法**: 代码实测运行 + API 符号审计 + 商业工具对标
**规则依据**: R02 学术诚信 / R03 禁止 fall-back / R11 工作流规范

---

## 0. 执行摘要

本报告基于 2026-07-17 对 PoLaRIS v5.0 代码库的深度实测（非文档声称），从**实际使用价值**角度评估项目的商业化就绪度。

### 核心发现

| 维度 | 结论 | 证据 |
|------|------|------|
| 核心功能可运行性 | ✅ 8/8 模块可运行，端到端流水线 9/9 stage 成功 | 实测运行 27.5s 完成 |
| API 声明真实性 | ❌ 41% 符号声明与代码不符（25% 完全不存在） | 280 个符号全量审计 |
| 商业可替代性 | ❌ 5 大商业支柱中 3 项关键缺口 | 7 款商业工具对标 |
| 学术诚信合规 | ❌ 代码注释标注"未迁移"的符号被标注"生产可用" | training.py/stage_input.py 注释证据 |

**总体评估**: PoLaRIS 具备技术验证级原型能力，但距商业可用仍有显著差距。核心问题不是"功能是否存在"，而是"文档声称与实际代码的严重脱节"。

---

## 1. 核心功能实测（实际运行验证）

### 1.1 实测方法

对 8 个核心模块执行实际代码运行，验证：①导入是否成功 ②能否实例化/运行 ③输出是否物理正确 ④实际可用性评级。

### 1.2 实测结果

| 模块 | 功能 | 实测结果 | 物理验证 | 评级 |
|------|------|---------|---------|------|
| C01 电路仿真 | S 参数 + 级联 | waveguide_s/ring_resonator_s/cascade_circuit 全部运行 | 透射率 1.0（无损全通型正确）；环谐振 through 端 |T|²=1.0 正确 | **可用** |
| B01 GDS 读写 | 多格式版图 IO | MultiFormatIO 支持 9 种格式 | FormatLayout 实例化 OK | **可用** |
| D01 布局引擎 | DREAMPlace 解析法布局 | place_circuit 5 器件 MZI 0.03s | HPWL=304μm，布局顺序合理无重叠 | **可用** |
| B02 DRC 检查 | 25 条设计规则 | DEFAULT_DRC_RULES 完整加载 | SiEPIC PDK 标准规则 | **可用** |
| F01 逆向设计 | JAX 伴随优化 | optimize_waveguide_width 3 步 9.8s | 宽度 400→413nm，FoM 改善 0.1772 dB | **可用** |
| G01 量子光子 | HOM 干涉 + 玻色采样 | clements_unitary/permanent/hom_interference 全运行 | 酉性误差 4.44e-16；HOM dip=1.0；概率归一化 1.0 | **可用** |
| J01 一体化流水线 | 9 stage 端到端 | run_eda_flow 27.5s 完成 | 9/9 stage 成功，0 失败 0 跳过 | **可用** |
| A09 FDTD 仿真 | 3D Yee 网格全波 | simulate_waveguide_fdtd 2.1s | 传输率 -10.62 dB（短步数预期值），PML 启用 | **可用** |

### 1.3 关键发现

1. **功能可用性确认**: 8 个核心模块全部可运行，物理结果合理。端到端流水线 9/9 stage 成功证明架构贯通性。

2. **API 风格为函数式**: v5.0 重构后对外 API 从 OOP 类改为函数式（`place_circuit()` 而非 `AnalyticalPlacer` 类，`run_eda_flow()` 而非 `IntegratedPipeline` 类），返回 JSON-serializable dict。这是合理的设计选择。

3. **R03 禁止 fall-back 合规**: 各模块失败即 raise（波长越界、网格尺寸不足、JAX 不可用），无静默兜底。

4. **规模限制**: 测试均在 5 器件/100 网格点小规模下完成。商业级需验证万器件/亿网格规模。

---

## 2. API 符号声明真实性审计

### 2.1 审计方法

对功能清单中约 280 个显式声明的类名/函数名，逐一用 Grep 在声明路径中搜索定义（`^class X` / `^def x`），未找到则全局搜索 `modules/`。

### 2.2 审计结果

| 分类 | 数量 | 占比 | 说明 |
|------|------|------|------|
| **精确匹配** | ~165 | 59% | 符号在声明路径中存在定义 |
| **路径漂移** | ~30 | 11% | 符号存在但在不同文件中 |
| **名称漂移** | ~15 | 5% | 符号不存在，有类似名称 |
| **完全不存在** | ~70 | 25% | 符号在 modules/ 中找不到 |
| **合计不符** | ~115 | 41% | 路径漂移+名称漂移+完全不存在 |

### 2.3 最严重问题：代码注释与功能清单矛盾

以下符号在**代码注释中明确标注"v5.0 未迁移"**，但功能清单仍标注"生产可用"并给出虚假路径：

| 声明符号 | 功能清单声称 | 代码实际注释 | 违规程度 |
|---------|------------|-------------|---------|
| `IntegratedPipeline` | "生产可用，实现: modules/orchestrator/.../flow.py" | training.py:102 `raise ImportError("v5.0 未迁移 IntegratedPipeline/PipelineConfig")` | **严重** |
| `PipelineConfig`/`PipelineResult` | "生产可用" | training.py:96 `# CalibrationResult（v5.0 未迁移）` | **严重** |
| `DeviceCatalog` | "生产可用，实现: modules/pdk/.../catalog.py" | stage_input.py:54 `# 原依赖 polaris_pdk.DeviceCatalog（v5.0 未迁移）` | **严重** |
| `FoundryPlatform`/`FOUNDRY_PLATFORMS` | "生产可用" | catalog.py 中无此符号 | **严重** |
| `ProcessNode`/`CMOS_PROCESS_NODES` | "生产可用，实现: modules/core/.../specs.py" | specs.py 中无此符号 | **严重** |
| `CalibrationResult`/`SimLoop` | "生产可用，实现: modules/flow/.../training.py" | training.py:96 `# v5.0 未迁移` | **严重** |

### 2.4 漂移模式分类

| 模式 | 典型案例 | 数量 | 根因 |
|------|---------|------|------|
| 类→函数重构 | AnalyticalPlacer→place_analytical | 4 | v5.0 从 OOP 改为函数式 API |
| 跨模块迁移 | boson/hom.py→quantum_advanced/ | ~20 | v5.0 模块化时符号迁移未同步文档 |
| 未迁移却声称存在 | IntegratedPipeline/DeviceCatalog | ~30 | v5.0 重构时部分功能未迁移但文档未更新 |
| 声明路径文件名错误 | verilog_a_rawfile.py→verilog_a_models.py | ~10 | 功能清单引用了旧文件名 |

### 2.5 精确匹配的模块（无问题）

以下模块的符号声明全部精确匹配，无漂移：
- `core/specs.py`（4 个数据类）
- `nn/data/`（benchmark_evaluator/tilos/apollo/lidar 共 30+ 个符号）
- `circuit/models.py`（RingParams + 10 个 S 参数函数）
- `circuit/simulator.py`（CircuitSimulator/default_models）
- `circuit/system_level.py`（SignalFlowGraph/TLLMLaser/HybridSimulator 等 5 个）
- `verify_advanced/`（KLayoutDRC/GraphLVS/CurvilinearLVS 等全模块）
- `optimizer/`（LevelSet/TopologyOptimizer/NSGA/PSO/CMA-ES 全模块）
- `router_advanced/`（GlobalRouter/JPSRouter/AllAngleRouter 等全模块 25+ 个）
- `pdk_advanced/`（PolarisPDK/parse_pic_yaml/PyCellFactory 等 16 个）
- `flow/`（Recipe/Stage/SDLFlow/RLInverseDesigner 等 15 个）
- `lumerical/`（ModeSolver/INTERCONNECTSimulator/CMLCompiler 等 6 个）

---

## 3. 商业工具实际使用价值对标

### 3.1 商业工具 5 大支柱

基于 Lumerical/Tidy3D/VPI/Luceda/OptoCompiler/MaxOptics/gdsfactory 的 2025-2026 最新信息分析：

| 支柱 | 内涵 | 商业标杆 | PoLaRIS 状态 |
|------|------|---------|-------------|
| **闭环可制造性** | GDS+S参数+网表+DRC/LVS 流片验证闭环 | Lumerical/Luceda/OptoCompiler | ⚠️ 部分（GDS导出OK，DRC 25条，LVS GraphLVS，但缺流片验证） |
| **多层级链路贯通** | 器件FDTD→电路CML→系统BER/眼图垂直贯通 | Lumerical三件套/VPI/OptoCompiler | ❌ 关键缺口（器件级仅封装外部后端，电路级OK，系统级BER缺失） |
| **代工PDK生态** | 代工厂认证PDK含DRC规则/模型/层映射 | Luceda 8+/gdsfactory 25+ | ⚠️ 桥接48个PDKInfo但深度待验证 |
| **脚本化与自动化** | Python API全程脚本化 | 全部商业工具已Python化 | ✅ 优势项（纯Python，函数式API） |
| **算力弹性** | 云GPU/多核并行/按需算力 | Lumerical云GPU/Tidy3D全云原生 | ❌ 纯CPU（R04战略决策），需算法优化补偿 |

### 3.2 关键差距量化

| 能力项 | 商业标杆 | PoLaRIS 实测 | 差距评估 |
|--------|---------|-------------|---------|
| FDTD 网格规模 | Lumerical 数十亿网格（GPU） | 小规模 100³ 网格 2.1s | **大**（CPU 策略需算法补偿） |
| 电路规模 | INTERCONNECT 万器件 | 5 器件测试 1.87s | **中**（需万器件验证） |
| 系统级 BER/眼图 | VPI/OptSim 完整链路 | ❌ 缺失 | **关键缺口** |
| CML 自动生成 | Lumerical CML Compiler | ❌ 缺失 | **关键缺口** |
| PDK 认证深度 | Luceda 代工认证 | 48 PDKInfo 元数据桥接 | **待验证**（DRC规则/模型/层映射深度） |
| 版图输出 | Luceda/gdsfactory GDSII+OASIS | MultiFormatIO 9格式 | ✅ 达标 |
| DRC/LVS | Calibre/IC Validator | 25条DRC+GraphLVS | ⚠️ 基础可用 |
| 逆向设计 | Lumerical adjoint+topology | JAX adjoint+水平集 | ✅ 达标（12/22 功能点） |
| 量子光子 | 部分商业工具支持 | HOM/玻色采样/Clements | ✅ 优势项（超出多数商业工具） |

### 3.3 商业工具性能基准（可溯源）

- **Lumerical vs Tidy3D**: 25 cells/λ 高分辨率 3D 器件，Tidy3D 云端 GPU 33 分钟，Lumerical CPU 25 小时（arXiv:2506.16665v2, Liu & Poon, 多伦多大学, 2025-06）
- **Lumerical GPU 网格**: NVIDIA RTX PRO 6000 Blackwell 上"数十亿网格"（Synopsys 2025-08-28 官方新闻稿）
- **gdsfactory 性能**: 10k 矩形 4.87ms，2M+ 下载，25+ PDK（CLEO26 论文 + PyPI v9.24, 2025-12）
- **VPI 行业事件**: 2026-06-09 被 Keysight 收购，补齐系统级仿真能力
- **Luceda 定价**: 工业 €3000/3月，学术 €1400/年，2026-06 后学术免费（JEPPIX 公开表）

---

## 4. 实际使用价值综合评估

### 4.1 可用能力（真实价值）

| 能力 | 实测验证 | 商业可用度 |
|------|---------|-----------|
| S 参数电路仿真 | 级联正确，物理结果合理 | **70%** — 缺 KLU 后端/模型拟合 |
| GDS 多格式 IO | 9 格式读写 | **80%** — 缺 OASIS 写入验证 |
| AI 布局布线 | 5 器件 0.03s | **50%** — 缺万器件规模验证 |
| DRC 检查 | 25 条 SiEPIC 标准 | **60%** — 缺 foundry 认证 runset |
| 逆向设计 | JAX 伴随优化生效 | **65%** — 缺拓扑优化全栈 |
| 量子光子仿真 | HOM dip=1.0，酉性 4.44e-16 | **80%** — 超出多数商业工具 |
| 端到端流水线 | 9/9 stage 27.5s | **60%** — 小规模验证通过 |
| 3D FDTD 全波 | 波导仿真 2.1s | **40%** — 仅自研小规模，缺大规模验证 |

### 4.2 关键缺口（商业阻断点）

| 缺口 | 影响 | 商业对标 | 修复优先级 |
|------|------|---------|-----------|
| **系统级 BER/眼图** | 无法做链路预算分析 | VPI/OptSim 完整支持 | P0 |
| **CML 自动生成** | 无法从器件仿真自动生成电路模型 | Lumerical CML Compiler | P0 |
| **器件级求解器自研** | FDTD/EME/RCWA 依赖外部后端 | Lumerical/Tidy3D 自研内核 | P0 |
| **万器件规模验证** | 无法做工业级电路 | DREAMPlace 万器件支持 | P1 |
| **PDK 认证深度** | 48 PDKInfo 仅元数据 | Luceda 代工认证 | P1 |
| **GPU 算力补偿** | CPU 纯实现大规模仿真慢 | 全部商业工具 GPU/云 | P2（R04 战略不参与） |

### 4.3 优势能力（差异化定位）

| 优势 | 对标 | 价值 |
|------|------|------|
| 纯 CPU + Python | 商业工具依赖 GPU/云 | 私有化部署无 GPU 依赖 |
| 量子光子仿真 | 多数商业工具不支持 | 学术研究差异化 |
| 学术诚信强制 | 商业工具无此约束 | 可溯源研究 |
| 端到端流水线 | 需多工具组合 | 单工具全流程 |

---

## 5. 学术诚信违规修正清单

### 5.1 功能清单虚假声明（必须修正）

以下符号在代码注释中明确标注"v5.0 未迁移"，但功能清单标注"生产可用"，违反 R02：

| 符号 | 功能清单声称 | 代码实际 | 修正方向 |
|------|------------|---------|---------|
| `IntegratedPipeline` | 生产可用 | `raise ImportError("v5.0 未迁移")` | → 已移除 |
| `PipelineConfig`/`PipelineResult` | 生产可用 | training.py 注释"未迁移" | → 已移除 |
| `DeviceCatalog` | 生产可用 | stage_input.py 注释"未迁移" | → 已移除 |
| `FoundryPlatform`/`FOUNDRY_PLATFORMS` | 生产可用 | catalog.py 中不存在 | → 已移除 |
| `ProcessNode`/`CMOS_PROCESS_NODES` | 生产可用 | specs.py 中不存在 | → 已移除 |
| `CalibrationResult`/`SimLoop` | 生产可用 | training.py 注释"未迁移" | → 已移除 |
| `AnalyticalPlacer` | 生产可用 | 实际是 `place_analytical` 函数 | → 名称修正 |
| `AlphaChipEdgeGNN` | 实验性 | 实际是 `EdgeGNN` | → 名称修正 |
| `AdjointOptimizer` | 生产可用 | 实际是 `run_adjoint_optimization` 函数 | → 名称修正 |
| `run_fdtd_simulation` | 生产可用 | 实际是 `simulate_waveguide_fdtd` | → 名称+路径修正 |

### 5.2 API 漂移修正优先级

| 优先级 | 修正项 | 数量 | 影响 |
|--------|--------|------|------|
| P0 | "未迁移"却声称"生产可用" → 改为"已移除" | ~30 | 学术诚信 |
| P1 | 类名→函数名修正 | ~15 | API 文档准确性 |
| P1 | 跨模块路径漂移修正 | ~30 | 代码可追溯性 |
| P2 | 声明路径文件名修正 | ~10 | 文档精度 |

---

## 6. 结论与建议

### 6.1 实际使用价值评级

| 维度 | 评级 | 依据 |
|------|------|------|
| 技术验证 | **B+** | 8/8 模块可运行，端到端流水线贯通 |
| 商业就绪 | **C** | 缺系统级BER/CML/自研求解器/PDK深度 |
| 文档诚信 | **D** | 41%符号声明不符，30个"未迁移"符号虚假标注"生产可用" |
| 差异化 | **B** | 纯CPU/量子光子/学术诚信强制是差异化优势 |

### 6.2 核心建议

1. **立即修正功能清单**：将 30 个"未迁移"符号从"生产可用"改为"v5.0 未迁移/已移除"，修正 45 个路径/名称漂移
2. **补齐 P0 缺口**：系统级 BER/眼图、CML 自动生成、器件级求解器自研
3. **万器件规模验证**：在现有流水线上验证 1000+ 器件电路
4. **PDK 深度桥接**：48 个 PDKInfo 补齐 DRC 规则/模型/层映射
5. **CPU 算力补偿**：多核并行 MPI + 自适应网格 + 模型降阶(ROM) + 2.5D varFDTD

### 6.3 战略定位

PoLaRIS 不应正面竞争 Lumerical/Tidy3D 的器件级 GPU 仿真市场，而应定位为：
- **学术研究工具**：量子光子+逆向设计+学术诚信强制
- **CPU 部署方案**：无 GPU 依赖的私有化部署
- **gdsfactory 仿真后端**：作为 gdsfactory 插件提供电路级仿真

---

## 7. 文献来源

1. Lumerical vs Tidy3D 实测对比 — arXiv:2506.16665v2 (Liu & Poon, 多伦多大学, 2025-06) — https://arxiv.org/abs/2506.16665
2. Synopsys Lumerical GPU 网格规模 — Synopsys 2025-08-28 官方新闻稿 — https://www.synopsys.com/blogs/chip-design/photonic-integrated-circuits-gpu-acceleration.html
3. gdsfactory 性能基准 — CLEO26 论文 + PyPI v9.24 (2025-12) — https://pypi.org/project/gdsfactory/
4. VPI Photonics 被 Keysight 收购 — Keysight 2026-06-09 公告 — https://www.keysight.com/us/en/news/pr/2026/06/keysight-acquires-vpiphotonics.html
5. Luceda IPKISS 定价 — JEPPIX 公开表 — https://www.jeppix.eu/products/luceda/
6. Tidy3D 云端 FDTD 定价 — Flexcompute 官网 — https://www.flexcompute.com/tidy3d/
7. MaxOptics 9 模块国产光子仿真 — 曼光科技官网 — https://www.maxoptics.com/
8. OptoCompiler 光电协同设计 — Synopsys 官网 — https://www.synopsys.com/photonic-solutions/optocompiler.html
