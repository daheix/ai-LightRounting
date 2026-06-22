# R02 路标实际交付：simphony 光子电路仿真对齐 Spec

## Why

R02 路标（2026-08）是 36-RoundMap 阶段 1 的第二个月，目标是追赶 simphony 的光子电路仿真能力。根据 [docs/roundmap/R02.md](file:///workspace/docs/roundmap/R02.md) 的改进计划路线图，需要实现 simphony 兼容 API（Subcircuit/Term/Connector）、新增 SiEPIC 缺失模型（half_ring/taper）、实现群延迟和色散分析、实现 add-drop 型环谐振器、SiEPIC JSON 网表解析器。综合得分从 6.3 提升至 6.5。

## What Changes

- 新增 simphony 兼容 API：`Subcircuit`、`Term`、`Connector` 类
- 新增 SiEPIC 缺失模型：`half_ring_s()`、`taper_s()`
- 实现群延迟计算：`group_delay(sdict, wavelengths)`
- 实现色散分析：`analyze_dispersion(sdict, wavelengths)`（FSR、Q 因子、3dB 带宽、消光比）
- 实现 add-drop 型环谐振器（双总线）
- 增加波长相关 neff（Sellmeier 方程）
- 实现 SiEPIC JSON 网表解析器
- 添加测试验证所有改动

## Impact

- Affected specs: `roundmap-detailed-tech-docs`（R02 路标的实际交付）
- Affected code:
  - `src/polaris/sim/simulator.py`（新增 group_delay/analyze_dispersion 方法）
  - `src/polaris/sim/models.py`（新增 half_ring_s/taper_s/add_drop_ring_s + Sellmeier 色散）
  - `src/polaris/sim/subcircuit.py`（新增 simphony 兼容 API）
  - `src/polaris/sim/siepic_netlist.py`（新增 SiEPIC JSON 网表解析器）
  - `tests/test_subcircuit.py`（新增测试）
  - `tests/test_group_delay.py`（新增测试）
  - `tests/test_siepic_netlist.py`（新增测试）
- Affected docs:
  - `操作记录.md`（追加第 98 轮记录）

## 数据来源与学术诚信

所有改动基于：
1. [docs/roundmap/R02.md](file:///workspace/docs/roundmap/R02.md) 的改进计划路线图
2. simphony GitHub 仓库（https://github.com/BYUCamachoLab/simphony）真实代码
3. Ploeg et al. IEEE CiSE 2021（DOI: 10.1109/MCSE.2020.3012099）子网络增长算法
4. Yariv 1997 §10.5 环谐振器理论
5. Chrostowski 2015 §4.5 硅光子设计教材

**禁止 fall-back**：业务必须正确，禁止假数据，跑不通就告警退出。

---

## ADDED Requirements

### Requirement: simphony 兼容 API

系统 SHALL 实现 simphony 兼容的电路构建 API，包括 `Subcircuit`、`Term`、`Connector` 类。

#### Scenario: Subcircuit 构建电路
- **WHEN** 用户使用 `Subcircuit` 类构建电路
- **THEN** 与 simphony API 完全兼容
- **AND** 可通过 `connect()` 方法连接器件

### Requirement: SiEPIC 缺失模型

系统 SHALL 新增 `half_ring_s()` 和 `taper_s()` 模型，对齐 simphony SiEPIC 模型库。

#### Scenario: half_ring 模型
- **WHEN** 调用 `half_ring_s()`
- **THEN** 返回与 simphony half_ring 对比误差 < 1e-10 的 S 参数

### Requirement: 群延迟计算

系统 SHALL 实现 `group_delay(sdict, wavelengths)` 方法计算群延迟。

#### Scenario: 波导群延迟
- **WHEN** 对波导 sdict 调用 `group_delay()`
- **THEN** 返回 τ_g = n_g·L/c（解析解验证）

### Requirement: 色散分析

系统 SHALL 实现 `analyze_dispersion(sdict, wavelengths)` 方法，自动提取 FSR、Q 因子、3dB 带宽、消光比。

#### Scenario: 环谐振器色散分析
- **WHEN** 对环谐振器 sdict 调用 `analyze_dispersion()`
- **THEN** 返回 {FSR, Q, ER, BW_3dB} 字典

### Requirement: add-drop 型环谐振器

系统 SHALL 实现 add-drop 型（双总线）环谐振器模型。

#### Scenario: 功率守恒
- **WHEN** 仿真 add-drop 环谐振器
- **THEN** through + drop = 1（功率守恒）

### Requirement: SiEPIC JSON 网表解析器

系统 SHALL 实现 SiEPIC JSON 网表解析器，自动解析 SiEPIC-Tools KLayout 导出的 JSON 网表。

#### Scenario: 解析 SiEPIC 网表
- **WHEN** 加载 SiEPIC JSON 网表
- **THEN** 自动转换为 PoLaRIS 内部网表
- **AND** 仿真结果与手动构建一致

---

## MODIFIED Requirements

无

## REMOVED Requirements

无
