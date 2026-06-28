# PDK 子包深度学术诚信审查报告生成 Spec

## Why

PoLaRIS 项目 `src/polaris/pdk/` 子包是光电子 PDK（工艺设计套件）核心，含 46 个 .py 文件、13,167 行代码，覆盖 14 个 foundry 平台、4 大材料平台（SOI/SiN/InP/LNOI）、9 类器件、OptoDesigner/gdsfactory/VPIphotonics/GPIC 多生态集成。在商业交付前，需对该子包进行一轮细粒度的学术诚信审查，生成结构化 markdown 报告插入到 `docs/学术诚信检查.md` §3.2，验证：每个器件参数可溯源到 foundry 官方文档/论文、每模块 docstring 文献 URL 数量达标、无 fall-back 假数据、无 GPU 代码、无 TODO/FIXME 残留。

本任务与既有 spec `audit-academic-integrity-deep`（覆盖整个 src/polaris/，输出到 docs/academic_integrity_audit.md）的区别：本任务范围聚焦 pdk/ 子包、粒度细化到逐文件、输出格式为 §3.2 七小节结构、严格只读不修改任何文件。

## What Changes

- 读取 `src/polaris/pdk/` 全部 46 个 .py 文件（顶层 25 + soi/ 6 + sin/ 5 + inp/ 6）
- 核查 R02 学术诚信：每模块 docstring 文献 URL 数量（≥5）、PDK 参数溯源（SiEPIC/LIGENTEC/HyperLight 等 foundry 官方文档/论文）
- 核查 R03 禁止 fall-back：except:pass / return None / return [] / 假数据兜底
- 核查 R04 不参与 GPU：CuPy/CUDA/ROCm 等 GPU 后端
- 核查 R05 Bug 必修：TODO/FIXME/HACK 残留
- 整理 PDK 参数溯源清单（Si 折射率 3.477、SiO₂ 1.444、SiEPIC R_min 5μm、HyperLight wg_width 1.5μm 等）
- 整理 Bug 清单（含已发现 #v3.3-PDK-1 process_nodes.py 计数错误），标注 Bug ID 与修复建议
- 生成 500-1000 行结构化 markdown 报告，严格遵循 3.2.1-3.2.7 格式
- **不修改任何文件**（纯只读分析任务）

## Impact

- Affected specs: audit-academic-integrity-deep（既有全量审查，本任务为其 pdk/ 子包的细化补充）
- Affected code: 无（只读审查，不修改任何 .py 文件）
- Affected docs: docs/学术诚信检查.md §3.2（报告内容由用户后续手动插入，本任务不写入文件）

## ADDED Requirements

### Requirement: 全文件覆盖审查
审查 SHALL 覆盖 `src/polaris/pdk/` 全部 46 个 .py 文件，按子目录组织（顶层/soi/sin/inp），每个文件记录：行数、主要功能、文献 URL 数量、Source 溯源对象数量。

#### Scenario: 文件清单完整性
- **WHEN** 审查完成
- **THEN** 3.2.1 文件清单含全部 46 文件，无遗漏

### Requirement: R02-R05 合规核查
审查 SHALL 逐条核查 R02（文献 URL ≥5/模块）、R03（无 fall-back）、R04（无 GPU）、R05（无 TODO/FIXME/HACK），记录每条规则的合规/违规结论。

#### Scenario: R03 fall-back 核查
- **WHEN** 发现 return None / return [] / except:pass
- **THEN** 逐一核实上下文，区分"查询未命中语义"（合规）与"假数据兜底"（违规）

### Requirement: PDK 参数溯源
审查 SHALL 整理 PDK 器件参数溯源清单，每条记录：参数名、参数值、来源文献/文档、URL、是否在公开文献报告区间内。

#### Scenario: SiEPIC 参数溯源
- **WHEN** 审查 SiEPIC EBeam PDK 器件
- **THEN** 记录 strip_waveguide width=500nm / bend radius=5μm / DC gap=200nm / half_ring gap=50nm 等参数的 SiEPIC 官方 PDK 溯源

### Requirement: Bug 标注与修复建议
审查 SHALL 对发现的 Bug 标注唯一 Bug ID（格式 #v3.3-PDK-N），记录 Bug 位置、根因、修复建议，但**不实际修复**。

#### Scenario: 已知 Bug 标注
- **WHEN** 发现 process_nodes.py docstring 计数错误
- **THEN** 标注为 #v3.3-PDK-1，记录"9 个 vs 13 个"不一致，建议统一为 13 个

### Requirement: 报告格式严格遵循
报告 SHALL 严格遵循 3.2.1 文件清单 / 3.2.2 算法清单 / 3.2.3 公式清单 / 3.2.4 文献引用清单 / 3.2.5 Bug 清单 / 3.2.6 完成度评估 / 3.2.7 代码-设计匹配性 七小节结构。

#### Scenario: 报告生成
- **WHEN** 审查完成
- **THEN** 返回 500-1000 行 markdown 文本，含七小节，可插入 docs/学术诚信检查.md §3.2

## MODIFIED Requirements

无（本任务为独立新增审查，不修改既有 spec 的需求）

## REMOVED Requirements

无
