# 下载 3dtool 工具集合包 + 融合三方库 + 完成剩余任务计划 Spec

## Why

项目设计文档多次引用 `3dtool/ALGORITHMS.md` 和 `3dtool/INVENTORY.md`，但 `daheix/3dtool` 仓库（1.6GB AppImage 工具集合包，含 Python 3.14 / KiCad / openEMS / C++ / Fortran / Java）尚未下载融合。同时，设计文档 vs 代码对齐核查发现多个 P0/P1 级问题需修复，确保代码只能超越设计、不可降低要求。

## What Changes

### 阶段一：3dtool 仓库下载与融合
- **清理磁盘空间**：删除 swiftly（71M）、pip 缓存、__pycache__ 等冗余文件，确保 ≥4G 可用
- **完整克隆 daheix/3dtool 仓库**：17 个分片（1.6G），使用已有 token 认证
- **恢复 3dtool-appimage**：运行 `restore_3dtool_appimage.sh` 合并分片+解压
- **融合到 workspace/3dtool/**：将 AppImage 工具链与现有 `3dtool/wheels/` 目录融合
- **验证工具链**：运行 `AppRun check` 自检 25 项工具

### 阶段二：P0 级 R03 违规修复
- **I04 verilog_a.py**：删除"合成脉冲信号"fall-back，改为真实 Ngspice 输出解析或 raise 告警
- **calibration.py**：`except Exception: continue` 改为 raise 或显式处理
- **gdsfactory_integration.py**：3 处 `except Exception: return False/[]/{}` 改为 raise 或显式处理
- **data_loader.py**：2 处 `except Exception: continue/warning` 改为 raise 或显式处理

### 阶段三：P0 级多物理耦合层补充
- **H01 电光耦合**：创建 `src/polaris/sim/multiphysics/electro_optic.py`，实现电光效应耦合
- **H02 热光耦合**：创建 `src/polaris/sim/multiphysics/thermo_optic.py`，实现热光效应耦合

### 阶段四：P1 级问题整改
- **D05 AlphaChip 架构统一**：`rl/alpha_chip.py` 复用 `engine/alphachip_gnn.py` + `ppo_torch.py`
- **C05 频域扫描 JAX vmap**：集成 `jax.vmap` + `jax.jit` 并行频率扫描
- **D04 RewardNormalizer**：实现运行均值方差奖励归一化

## Impact

- Affected specs: H01-电光耦合, H02-热光效应, I04-SPICE电路导出, D04-奖励塑造, D05-AlphaChip, C05-频域扫描
- Affected code:
  - `src/polaris/sim/verilog_a.py`（I04 fall-back 修复）
  - `src/polaris/sim/calibration.py`（R03 修复）
  - `src/polaris/pdk/gdsfactory_integration.py`（R03 修复）
  - `src/polaris/data/data_loader.py`（R03 修复）
  - `src/polaris/sim/multiphysics/`（新建目录）
  - `src/polaris/rl/alpha_chip.py`（架构统一）
  - `src/polaris/sim/interconnect.py`（C05 vmap）
  - `src/polaris/engine/reward_shaping.py`（D04 归一化）
  - `3dtool/` 目录结构（工具集合包融合）

## ADDED Requirements

### Requirement: 3dtool 工具集合包下载与融合
系统 SHALL 从 GitHub `daheix/3dtool` 仓库完整下载 17 个分片，恢复为 `3dtool/3dtool-appimage/` 工作目录，并与项目 `3dtool/wheels/` 目录融合，作为自仓库工具链使用。

#### Scenario: 成功下载与恢复
- **WHEN** 执行 `git clone` + `restore_3dtool_appimage.sh`
- **THEN** `3dtool/3dtool-appimage/AppRun` 可执行
- **AND** `AppRun check` 自检 25 项工具全部通过

### Requirement: R03 无 fall-back 全面合规
系统 SHALL 不包含任何静默兜底（`except: pass`、`except: return None/[]/{}`、合成假数据），所有异常必须 raise 或显式处理。

#### Scenario: I04 Ngspice 输出解析
- **WHEN** Ngspice 可用但输出格式不符合预期
- **THEN** raise RuntimeError 告警，不使用合成脉冲信号

### Requirement: H01/H02 多物理耦合层
系统 SHALL 提供电光耦合和热光耦合的顶层多物理场模块，连接 DDM/HEAT 求解器与光学仿真。

#### Scenario: 电光耦合仿真
- **WHEN** 用户配置电光调制器仿真
- **THEN** DDM 求解器计算载流子分布 → 电光效应模块转换为折射率变化 → 光学求解器更新

## MODIFIED Requirements

### Requirement: D05 AlphaChip 架构统一
`rl/alpha_chip.py` SHALL 复用 `engine/alphachip_gnn.py` 中的 `AlphaChipEdgeGNN` 和 `ppo_torch.py` 中的 `PPOAgent`，消除代码冗余。

### Requirement: C05 频域扫描性能优化
频域扫描 SHALL 使用 `jax.vmap` + `jax.jit` 实现并行频率扫描，超越设计文档要求的串行扫描。

### Requirement: D04 奖励归一化
`ExpertRewardShaper` SHALL 实现运行均值方差奖励归一化，确保各奖励分量梯度尺度平衡。
