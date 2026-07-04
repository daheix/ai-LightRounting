# expert_demos Netlist 连接缺失修复 Spec

## Why

PoLaRIS 项目从 SiEPIC EBeam PDK GDS 提取的 10 个 expert_demos 三元组（网表/布局/布线）中，3/10 demo 因 netlist.json 缺 devices 字段在 `parse_expert_demos` 处 `raise ValueError` 失败，10/10 demo 的 connections 字段全为空（连接信息藏在 routes.json 波导路径点列表中未反推）。这导致模仿学习教师信号缺失，`scripts/test_real_circuits.py` 的 expert_demos 分支无法跑通，阻塞商用版真实用例端到端测试（隶属 `real-circuits-github-and-combinations` spec Task 4.5 失败用例根因分析）。

## What Changes

- **新增** `scripts/fix_expert_demos_connections.py`（638 行）：实现从 routes.json 路径点列表反推器件连接关系的三级策略
  - 策略 1（纯波导 demo，placements 为空）：为每条 route 首尾点构造虚拟 grating_coupler IO 器件，生成 1 个波导连接
  - 策略 2（有源器件 demo，route 首尾匹配不同器件）：按 route 首尾点最近器件 + 方向主轴选端口，生成跨器件连接
  - 策略 3（route 为器件内部波导片段，策略 2 无跨器件连接）：基于器件 bbox 中心位置的 Kruskal 最小生成树生成 n-1 条连接
  - 策略 3 退化（单器件 demo）：构造 1 个虚拟 IO 器件，生成器件→IO 连接
- **修改** 10 个 demo 的 `netlist.json`：补充 devices 字段（3 个纯波导 demo）+ 写入 connections 字段（10 个 demo）
- **修改** 4 个 demo 的 `placements.json`：纯波导 demo（MZI_bdc/ebeam_taper_475_500_te1550/wg_test）和单器件 demo（Simple_MZI）补充虚拟 IO 器件布局
- **修改** 10 个 demo 的 `meta.json`：更新 n_connections + connection_inference 元数据
- **修改** `index.json`：更新 records 的 n_connections/n_devices
- **追加** `操作记录.md` R347 轮次记录

## Impact

- Affected specs: `real-circuits-github-and-combinations`（Task 4.5 失败用例根因分析的前置修复）
- Affected code:
  - `scripts/fix_expert_demos_connections.py`（新增：反推修复脚本）
  - `real_board/expert_demos/*/netlist.json`（10 个文件修改）
  - `real_board/expert_demos/*/placements.json`（4 个文件修改）
  - `real_board/expert_demos/*/meta.json`（10 个文件修改）
  - `real_board/expert_demos/index.json`（修改）
  - `操作记录.md`（追加 R347）

## ADDED Requirements

### Requirement: expert_demos netlist 连接反推

系统 SHALL 从 routes.json 路径点列表反推器件连接关系并写入 netlist.json：

1. **纯波导 demo**（placements 为空）：为每条 route 首尾点构造虚拟 grating_coupler IO 器件（位置即首尾点），生成 1 个波导连接
2. **有源器件 demo**（placements 非空）：
   - 若 route 首尾匹配不同器件 → 按方向主轴选端口生成跨器件连接
   - 若 route 均为器件内部波导片段（首尾匹配同一器件）→ 基于 Kruskal MST 生成 n-1 条器件间连接
3. **单器件 demo**：构造 1 个虚拟 IO 器件，生成器件→IO 连接
4. 反推失败（routes 为空 / route 路径点 < 2 / 器件匹配失败）SHALL `raise ValueError`（R03 禁止 fall-back）

#### Scenario: 纯波导 demo 修复

- **WHEN** demo 的 placements 为空（如 MZI_bdc/ebeam_taper_475_500_te1550/wg_test）
- **THEN** 为每条 route 首尾点构造 2 个虚拟 IO 器件
- **AND** 生成 1 个 io_port_in → io_port_out 的波导连接
- **AND** netlist.json 的 devices 和 connections 字段均非空

#### Scenario: 有源器件 demo 修复

- **WHEN** demo 的 placements 非空且 route 首尾匹配同一器件（route 为器件内部波导片段）
- **THEN** 基于器件 bbox 中心位置运行 Kruskal MST 算法
- **AND** 生成 n-1 条器件间连接（n = 器件数）
- **AND** 端口按 A→B 方向主轴（E/W/N/S）选择

#### Scenario: 反推失败

- **WHEN** routes 为空 / route 路径点 < 2 / 器件匹配失败
- **THEN** `raise ValueError` 明确异常
- **AND** 禁止返回空列表或假数据（R03）

### Requirement: 虚拟 IO 器件建模

纯波导 demo 的虚拟 IO 器件 SHALL 基于 route 真实首尾点物理位置建模，非 fall-back：

1. device_type = `grating_coupler_1d`（SiEPIC EBeam PDK 标准光栅耦合器）
2. 位置 = route 首尾点真实坐标
3. bbox = [x-5, y-5, x+5, y+5]（10μm × 10μm）
4. params.source = `inferred_from_route` + route_index + endpoint

#### Scenario: 虚拟 IO 建模

- **WHEN** 纯波导 demo 的 route 首点为 (5.0, -0.25)
- **THEN** io_port_in 器件的 placement.x = 5.0, placement.y = -0.25
- **AND** bbox = [0.0, -5.25, 10.0, 4.75]

## MODIFIED Requirements

### Requirement: expert_demos 三元组完整性

expert_demos 每个 demo 的 netlist.json SHALL 包含非空 devices 和 connections 字段：

- 修改前：3/10 缺 devices，10/10 connections 为空
- 修改后：10/10 devices 非空，10/10 connections 非空（连接数 ≥ 1）

## REMOVED Requirements

无（本次为新增修复，不移除既有功能）

## 学术诚信（R02）

- **SiEPIC EBeam PDK**: https://github.com/SiEPIC/SiEPIC_PDK (MIT, UBC, Lukas Chrostowski, 2015-2023)
- **SiEPIC Connect Function**（端口同位置互连推断）: Chrostowski et al., "Silicon Photonics Design: From Devices to Systems", Cambridge University Press, 2022, ISBN 978-1-108-56830-6
- **Kruskal MST 算法**: Kruskal 1956, "On the shortest spanning subtree of a graph and the traveling salesman problem", Proc. ACM 7(1), https://dl.acm.org/doi/10.1145/320756.320757
- **klayout Path/Polygon 几何提取**: https://www.klayout.org/klayout-pypi/overview/instances/
- **模仿学习理论**: Pomerleau 1989, "ALVINN: An Autonomous Land Vehicle in a Neural Network", NeurIPS, https://papers.nips.cc/paper/95-alvinn-an-autonomous-land-vehicle
- **模仿学习综述**: Gavenski et al., "A Survey of Imitation Learning Methods", ACM PACMMECS 2024, https://arxiv.org/abs/2404.19456
