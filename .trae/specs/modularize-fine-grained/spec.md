# PoLaRIS 细粒度子模块重构 Spec（v2）

## Why
v1 拆分为8子模块仍太大（如 polaris-sim 混了 FDTD/FDE/EME/BPM/FDFD/S参数/PAM4，
polaris-verify 混了 DRC+LVS）。用户要求"每个功能就是一个独立的子模块"：
DRC 就是 DRC，LVS 是 LVS，每种仿真独立。每个模块按 **input→process→output** 模式
组织，并写明模块文档（输入是什么/处理什么/输出是什么）。

## What Changes
- **BREAKING**: 将 v1 的 8 子模块进一步拆分为 **18 个细粒度功能子模块**
- 每个子模块只做一件事（单一职责原则）
- 每个子模块文档按 input→process→output 三段式书写
- 每个子模块独立目录 + 独立 pyproject + 独立 tests + 独立 C ABI
- 保留 v1 的 polaris-core 作为公共数据结构层（所有子模块依赖）
- 新增 polaris-orchestrator 调用18个子模块

## 子模块划分（18 个）

### 数据与基础设施层（2 个）
| # | 子模块 | 职责 | input | process | output |
|---|--------|------|-------|---------|--------|
| 1 | polaris-core | 核心数据结构 | 器件/连接描述 | dataclass+dict构造 | CircuitSpec/DeviceSpec dict |
| 2 | polaris-pdk | PDK 器件库 | 平台名/器件类型 | 查4平台36器件目录 | 器件规格 dict |

### 物理设计流程层（4 个）
| # | 子模块 | 职责 | input | process | output |
|---|--------|------|-------|---------|--------|
| 3 | polaris-place | AI 布局 | CircuitSpec | 解析布局/AlphaChip | placements+HPWL |
| 4 | polaris-route | 智能布线 | Circuit+placements | curvy 曲线布线 | paths+损耗 |
| 5 | polaris-drc | DRC 设计规则检查 | Circuit+placements | 12条规则检查 | violations+pass_rate |
| 6 | polaris-lvs | LVS 网表比对 | Circuit+netlist | 拓扑比对 | is_consistent+mismatches |

### 仿真求解器层（7 个，每种独立）
| # | 子模块 | 职责 | input | process | output |
|---|--------|------|-------|---------|--------|
| 7 | polaris-fdtd | 时域有限差分 | 网格+源+eps_r | Yee 网格时间步进 | 时域场分布 |
| 8 | polaris-fde | 频域本征模 | 波导截面+波长 | 求解本征模 | 模式场+neff |
| 9 | polaris-eme | 本征模展开 | 器件几何+波长 | 模式传播+匹配 | S 参数 |
| 10 | polaris-bpm | 光束传播法 | 折射率分布+源 | CN/ADI 方向传播 | 场分布 |
| 11 | polaris-fdfd | 频域有限差分 | 网格+源+波长 | 线性方程组求解 | 稳态场分布 |
| 12 | polaris-sparam | 频域 S 参数 | 波长+器件参数 | 解析模型级联 | S 参数矩阵 |
| 13 | polaris-pam4 | PAM4 信号仿真 | 符号数+比特率 | 生成+噪声+检测 | BER+SNR+眼图 |

### 逆向设计与量子层（3 个）
| # | 子模块 | 职责 | input | process | output |
|---|--------|------|-------|---------|--------|
| 14 | polaris-inverse | Adjoint 逆向设计 | 初始宽度+迭代数 | JAX jax.grad 优化 | 最优宽度+FoM历史 |
| 15 | polaris-quantum-boson | 玻色采样 | 酉矩阵+输入态 | permanent 计算 | 概率分布 |
| 16 | polaris-quantum-klm | KLM 线性光学量子计算 | 无 | Ralph 2002 CNOT门 | 成功率+验证 |

### GDS 与验证层（2 个）
| # | 子模块 | 职责 | input | process | output |
|---|--------|------|-------|---------|--------|
| 17 | polaris-gdsio | GDSII 导入导出 | Circuit/GDS文件 | klayout.db 读写 | GDS文件/结构信息 |
| 18 | polaris-orchestrator | 业务编排 | Circuit+output_dir | 调用17子模块 | 9 stage 结果汇总 |

## ADDED Requirements

### Requirement: 每个子模块单一职责
每个子模块只做一件事，DRC 不含 LVS，FDTD 不含 FDE，玻色采样不含 KLM。

### Requirement: input-process-output 文档
每个子模块 SHALL 在 `__init__.py` 和 `c_api/<name>.h` 顶部按三段式书写文档：
- **Input**: 输入参数（类型、单位、来源）
- **Process**: 处理逻辑（算法、公式、文献）
- **Output**: 输出结果（类型、单位、物理意义）

### Requirement: 每个子模块可独立 pip install + pytest
每个子模块有独立 pyproject.toml + 独立 tests/，互不依赖（除依赖 polaris-core）。

## Impact
- v1 的 polaris-sim 拆分为 7 个（fdtd/fde/eme/bpm/fdfd/sparam/pam4）
- v1 的 polaris-verify 拆分为 2 个（drc/lvs）
- v1 的 polaris-quantum 拆分为 2 个（boson/klm）
- v1 的 polaris-pdk GDS 部分独立为 polaris-gdsio
- 共 18 个子模块
