# R01 路标实际交付：sax 频域 S 参数仿真对齐 Spec

## Why

R01 路标（2026-07）是 36-RoundMap 阶段 1 的第一个月，目标是追赶 sax 的频域 S 参数仿真能力。根据 [docs/roundmap/R01.md](file:///workspace/docs/roundmap/R01.md) 的改进计划路线图，需要修复 PoLaRIS 现有仿真代码的 fall-back 兜底问题、数值稳定性问题，并实现双后端自动切换、模型参数 schema 验证、网表格式自动适配器。综合得分从 6.1 提升至 6.3。

## What Changes

- 修复 `src/polaris/sim/cascade.py` 第 106 行 fall-back 兜底（`np.where(..., 1e-15, ...)`）→ 改为基于条件数的自动后端切换
- 修复 `src/polaris/sim/cascade.py` 第 287 行 `except Exception: pass` → 改为告警退出
- 将 `src/polaris/sim/types.py` SDict 从 numpy 切换到 jax.numpy 支持自动微分
- 实现双后端自动切换（numpy/jax）基于条件数监控
- 实现模型参数 schema 验证
- 实现网表格式自动适配器（支持 sax/simphony/PoLaRIS 三种网表格式）
- 扩展 `src/polaris/sim/models.py` 器件模型库（从 10 个扩展到 20+，对齐 sax）
- 添加测试验证所有改动

## Impact

- Affected specs: `roundmap-detailed-tech-docs`（R01 路标的实际交付）
- Affected code:
  - `src/polaris/sim/cascade.py`（修复 fall-back + 双后端切换）
  - `src/polaris/sim/types.py`（SDict 切换到 jax.numpy）
  - `src/polaris/sim/models.py`（扩展器件模型库）
  - `src/polaris/sim/simulator.py`（JIT 编译 + GPU 支持）
  - `tests/test_cascade.py`（新增测试）
  - `tests/test_models.py`（新增测试）
- Affected docs:
  - `操作记录.md`（追加第 97 轮记录）

## 数据来源与学术诚信

所有改动基于：
1. [docs/roundmap/R01.md](file:///workspace/docs/roundmap/R01.md) 的改进计划路线图
2. sax GitHub 仓库（https://github.com/flaport/sax）真实代码
3. simphony GitHub 仓库（https://github.com/BYUCamachoLab/simphony）真实代码
4. PoLaRIS 现有代码（经 Read/Grep 验证）
5. 学术论文（Ploeg et al. IEEE CiSE 2021, Frostig et al. SysML 2018, Davis & Duff ACM TOMS 2004）

**禁止 fall-back**：业务必须正确，禁止假数据，跑不通就告警退出。

---

## ADDED Requirements

### Requirement: 修复 cascade.py fall-back 兜底

系统 SHALL 修复 `src/polaris/sim/cascade.py` 中的 fall-back 兜底代码，改为基于条件数的自动后端切换。

#### Scenario: fall-back 兜底已删除
- **WHEN** 检查 cascade.py 第 106 行
- **THEN** 不存在 `np.where(..., 1e-15, ...)` 形式的 fall-back
- **AND** 改为基于条件数 κ(S) 的自动后端切换

#### Scenario: except Exception: pass 已删除
- **WHEN** 检查 cascade.py 第 287 行
- **THEN** 不存在 `except Exception: pass` 形式的静默异常
- **AND** 改为告警退出（raise RuntimeError）

### Requirement: SDict 切换到 jax.numpy

系统 SHALL 将 `src/polaris/sim/types.py` 中的 SDict 从 numpy 切换到 jax.numpy，支持自动微分。

#### Scenario: SDict 支持 jax.numpy
- **WHEN** 创建 SDict 实例
- **THEN** 内部数据使用 jax.numpy 数组
- **AND** 支持 `jax.grad` 自动微分

### Requirement: 双后端自动切换

系统 SHALL 实现基于条件数的双后端（numpy/jax）自动切换。

#### Scenario: 条件数小用 numpy
- **WHEN** 条件数 κ(S) < 1e6
- **THEN** 使用 numpy 后端（速度快）

#### Scenario: 条件数大用 jax
- **WHEN** 条件数 κ(S) ≥ 1e6
- **THEN** 使用 jax 后端（数值稳定）

### Requirement: 模型参数 schema 验证

系统 SHALL 实现模型参数 schema 验证，确保器件模型参数合法。

#### Scenario: 参数合法
- **WHEN** 传入合法参数
- **THEN** 模型正常创建

#### Scenario: 参数非法
- **WHEN** 传入非法参数（如负数宽度）
- **THEN** raise ValueError 告警退出

### Requirement: 网表格式自动适配器

系统 SHALL 实现网表格式自动适配器，支持 sax/simphony/PoLaRIS 三种网表格式。

#### Scenario: sax 网表
- **WHEN** 传入 sax 格式网表
- **THEN** 自动解析为 PoLaRIS 内部格式

#### Scenario: simphony 网表
- **WHEN** 传入 simphony 格式网表
- **THEN** 自动解析为 PoLaRIS 内部格式

### Requirement: 扩展器件模型库

系统 SHALL 扩展 `src/polaris/sim/models.py` 器件模型库，从 10 个扩展到 20+，对齐 sax。

#### Scenario: 器件模型数量
- **WHEN** 检查 models.py
- **THEN** 器件模型数量 ≥ 20
- **AND** 包含 sax 的所有核心器件模型

---

## MODIFIED Requirements

无

## REMOVED Requirements

无
