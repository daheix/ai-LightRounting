# 三方库清单与商用许可分析 Spec

## Why

PoLaRIS 项目当前依赖 80+ 个 Python 三方库（`3dtool/wheels/` 离线打包），但缺少一份**完整的、按商用可行性分类**的工具清单。项目规则 3（三方工具统一管理）和规则 4（自研复刻）需要一个权威的决策依据：

1. 哪些库可以**直接商用**（许可允许、维护活跃、API 稳定）→ 优先直接集成
2. 哪些库**不能商用**（许可冲突、依赖商业软件、Py3.14 不可用）→ 标记并规划复刻
3. 哪些库**项目尚无**但商业工具有（如 RCWA/EME/BPM/HEAT 求解器）→ 标记缺失并给出核心算法公式供后续实现

本 spec 产出一份可执行的三方库决策清单，作为规则 3/4 的执行依据，并填补 year_plan 中求解器矩阵（RCWA/EME/BPM/HEAT 等）的算法公式空白。

## What Changes

- 新增 `3dtool/INVENTORY.md`：完整三方库清单，按"可商用 / 不可商用 / 待复刻 / 缺失"四档分类
- 新增 `3dtool/ALGORITHMS.md`：核心求解器算法公式手册（RCWA/EME/BPM/HEAT/DDM/FDE/FDFD/2.5D-FDTD），含文献来源
- 更新 `3dtool/README.md`：引用上述两份清单
- 更新 `3dtool/<category>/README.md`：每个分类目录的 README 同步许可状态标记
- 更新 `.trae/rules/project_rules.md` 规则 3.2：在工具清单表中新增"许可/商用"列
- 更新 `操作记录.md`：追加本轮操作记录

## Impact

- **Affected specs**: `collect-commercial-feature-inventory-and-year-plan`（求解器矩阵来源对齐）、`build-36-month-roundmap`（求解器算法公式）
- **Affected code**: 无源码改动，仅文档与清单
- **Affected rules**: 规则 3（三方工具管理）、规则 4（复刻触发条件）、规则 26（GPU 不参与，确认复刻范围排除 GPU）

## ADDED Requirements

### Requirement: 三方库完整清单（INVENTORY.md）

系统 SHALL 提供一份覆盖项目实际 import 的所有三方库 + 商业工具对照的完整清单，按以下四档分类：

1. **✅ 可直接商用**：开源许可（MIT/Apache-2.0/BSD/ISC/MPL-2.0/LGPL）、维护活跃（近一年有 release）、Py3.14 可装、API 稳定 → 排在前面
2. **⚠️ 许可受限**：GPL/AGPL/SSPL/商业许可/双重许可，需法律评估或商业授权
3. **🚫 不可商用/待复刻**：依赖商业软件（如 Lumerical/Tidy3D API）、Py3.14 无 wheel、项目已复刻（pyCopy 前缀）
4. **❌ 缺失**：项目尚无该库但商业对标工具有（如 RCWA/EME/BPM/HEAT 求解器），标记并指向 `ALGORITHMS.md` 的算法公式

#### Scenario: 工程师查询某库是否可商用
- **WHEN** 工程师在 `3dtool/INVENTORY.md` 查询某库
- **THEN** 能立即看到许可类型、商用状态、Py3.14 状态、项目使用位置、复刻决策

#### Scenario: 规划求解器复刻
- **WHEN** 规划 RCWA/EME/BPM/HEAT 等求解器
- **THEN** 能在 `3dtool/ALGORITHMS.md` 找到核心算法公式、离散化方案、边界条件、文献来源

### Requirement: 核心算法公式手册（ALGORITHMS.md）

系统 SHALL 为每个"缺失"求解器提供以下内容：

1. **数学模型**：控制方程（如 Maxwell 方程、热传导方程、漂移扩散方程）
2. **离散化方案**：网格类型（Yee/FD/FEM）、时间步进、稳定性条件（CFL）
3. **边界条件**：PML/周期/Bloch/Dirichlet/Neumann
4. **核心公式**：用 LaTeX/伪代码表达关键递推式
5. **文献来源**：论文标题、作者、年份、URL（规则 18 学术诚信）

#### Scenario: 实现新求解器
- **WHEN** 开发者按 year_plan 实现新求解器
- **THEN** 能依据 `ALGORITHMS.md` 的公式与来源实现，并标注创新点

## MODIFIED Requirements

### Requirement: 规则 3.2 工具清单表

现有规则 3.2 的工具清单表新增"许可/商用"列，标注每个工具的许可类型与商用状态。

### Requirement: 3dtool README

`3dtool/README.md` 顶部新增"清单索引"，引用 `INVENTORY.md` 和 `ALGORITHMS.md`。

## REMOVED Requirements

无删除项。

## 范围与边界

### 必须覆盖（基于实际 import 与商业对标）
- **已使用的库**：numpy/scipy/networkx/matplotlib/pyyaml/torch/gymnasium/klayout/simphony/sax/jax/optax/flax/shapely/gdstk/pandas/sympy 等
- **已复刻的库**：pyCopySiPANN
- **商业对标独有求解器**：RCWA/EME/BPM/HEAT/DDM/FDE/FDFD/2.5D-FDTD（来自 T01 Lumerical/T04 Tidy3D/T07 Photon Design/T15 曼光/T16 SimWorks）
- **GPU 相关库**：CuPy（按规则 26 标记🚫不参与，不深入分析）

### 不在本 spec 范围
- 实际编写求解器代码（属 year_plan 的 R37-R50 路标任务）
- 删除现有 pyCopy 复刻品（属规则 4 范围）
- 修改 `3dtool/wheels/` 离线包结构

## 网络调研要求（用户明确强调）

本 spec 的大任务性质要求**必须结合网络分析**才能完成：
1. 每个库的许可类型须查 PyPI/GitHub 官方页面核实
2. 每个求解器的算法公式须查 arXiv/IEEE/官方文档核实
3. 商业工具（Lumerical/Tidy3D/曼光/SimWorks）的求解器实现须查官方文档
4. 禁止编造许可类型或算法公式（规则 18 学术诚信）

## 验收标准

- `3dtool/INVENTORY.md` 覆盖 ≥ 50 个三方库（实际 import 的全部 + 商业对标关键库）
- `3dtool/ALGORITHMS.md` 覆盖 ≥ 8 个求解器（RCWA/EME/BPM/HEAT/DDM/FDE/FDFD/2.5D-FDTD）
- 每个库的许可类型有 PyPI/GitHub URL 引用
- 每个求解器公式有论文/教材 URL 引用
- 四档分类清晰，可商用库排在前面
- 规则 3.2 表格同步更新
