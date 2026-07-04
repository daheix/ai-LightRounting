# 恢复 SiEPIC GDS 解析器 Spec

## Why

PoLaRIS 项目从 v4 单包重构为 v5.0 多模块后，旧的 `polaris.data.gds_loader` 被删除。
真实板子测试中 229 个 SiEPIC GDS 文件无法解析，`scripts/test_real_circuits.py`
在 `siepic` 分支直接 `raise ValueError("siepic GDS 解析依赖 polaris.data.gds_loader，
V5.0 拆包后该模块已下线")`，导致 229/448 真实用例无法进入端到端流水线。

本变更在 `polaris-gds-tools` 子模块下重建 GDS 解析器，恢复 229 个 SiEPIC GDS 用例
的解析能力，并接入 `test_real_circuits.py` 的 `siepic` 分支。

## What Changes

- 新增 `modules/gds_tools/src/polaris_gds_tools/gds_loader.py`：
  - 多策略器件识别（instance / DEVREC polygon / 顶层 cell 自身）
  - SiEPIC → PoLaRIS 器件名映射（30+ 项）
  - PIN 端口提取与跨器件连接推断（容差 15.0μm）
  - DEVREC `Spice_param` 参数解析
  - DCplxTrans 手动变换（klayout Python 绑定运算符不生效）
  - 三个对外 API：`load_gds_to_circuit` / `load_gds_to_circuit_spec` / `siepic_to_polaris`
- 修改 `modules/gds_tools/src/polaris_gds_tools/__init__.py`：导出三个新 API
- 新增 `scripts/test_siepic_gds_loader.py`：默认测 10 个文件（3 种策略全覆盖），
  `--all` 跑全量 229 个
- 修改 `scripts/test_real_circuits.py`：`siepic` 分支调用 `load_gds_to_circuit`
  （移除"模块下线"的 raise）

## Impact

- Affected specs:
  - `real-circuits-github-and-combinations`（本变更为其 Task 3 SubTask 3.2 的实现）
- Affected code:
  - `modules/gds_tools/src/polaris_gds_tools/gds_loader.py`（新增）
  - `modules/gds_tools/src/polaris_gds_tools/__init__.py`（修改）
  - `scripts/test_siepic_gds_loader.py`（新增）
  - `scripts/test_real_circuits.py`（修改 siepic 分支）
  - `操作记录.md`（追加轮次记录）

## ADDED Requirements

### Requirement: SiEPIC GDS 解析器（polaris-gds-tools）
系统 SHALL 在 `polaris_gds_tools.gds_loader` 提供 SiEPIC GDS → CircuitSpec 解析：
1. 用 `klayout.db` 读取 GDSII 文件（SEMI P39-0308E 标准）
2. 多策略器件识别：
   - 策略 A：顶层 cell 的 instance（cell 名非辅助前缀）
   - 策略 B：DEVREC(68,0) polygon（Lumerical CML 导出格式）
   - 策略 C：顶层 cell 自身（单器件电路）
3. PIN(69,0) 端口提取（text → 最近 path 匹配，无匹配即 raise，R03）
4. 跨器件连接推断（同位置端口互连，容差 15.0μm，排除同器件端口）
5. `Spice_param` 参数解析
6. 返回 polaris-core 兼容 dict（含 name/devices/connections/canvas_w/canvas_h）

#### Scenario: 默认 10 个文件解析
- **WHEN** 运行 `python scripts/test_siepic_gds_loader.py`
- **THEN** 10 个文件 100% 解析成功
- **AND** 三种识别策略均被覆盖

#### Scenario: 全量 229 个文件回归
- **WHEN** 运行 `python scripts/test_siepic_gds_loader.py --all`
- **THEN** 229 个文件 100% 解析成功
- **AND** 策略分布约 instance=104 / devrec_polygon=68 / top_cell=57

#### Scenario: test_real_circuits siepic 分支
- **WHEN** `test_real_circuits.py` 遇到 siepic 来源用例
- **THEN** 调用 `polaris_gds_tools.gds_loader.load_gds_to_circuit`
- **AND** 不再 raise "模块下线" 异常

### Requirement: R03 禁止 fall-back
GDS 解析失败 SHALL raise 明确异常，禁止：
- `except: pass` / `return None` / `return []`
- 用假数据让程序"跑通"
- PIN text 无匹配 path 时静默跳过
- 端口未匹配到器件时静默跳过

### Requirement: R02 学术诚信
所有 GDSII 层定义、SiEPIC PDK 器件名映射、参数解析逻辑须可溯源：
- GDSII 标准：SEMI P39-0308E
- SiEPIC EBeam PDK：https://github.com/SiEPIC/SiEPIC_EBeam_PDK (MIT, UBC)
- klayout.db API：https://www.klayout.de/doc-qt5/code/index.html

### Requirement: R04 不参与 GPU
纯 `klayout.db`（CPU）实现，禁止 CuPy/CUDA/ROCm。

## MODIFIED Requirements

### Requirement: test_real_circuits.py siepic 分支
原：`raise ValueError("siepic GDS 解析依赖 polaris.data.gds_loader，V5.0 拆包后该模块已下线")`
改：`from polaris_gds_tools.gds_loader import load_gds_to_circuit; return load_gds_to_circuit(path)`

## REMOVED Requirements

### Requirement: polaris.data.gds_loader（v4 单包）
**Reason**: v5.0 多模块拆包后该模块已下线，功能迁移到 `polaris_gds_tools.gds_loader`
**Migration**: 调用方改用 `polaris_gds_tools.gds_loader.load_gds_to_circuit`
