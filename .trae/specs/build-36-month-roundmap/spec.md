# 36 个月逐月路标（36-RoundMap）+ 商业工具功能清单对比 Spec

## Why

PoLaRIS 已迭代至第 94 轮（2026-06-22），综合得分 6.1/10，与商业领先工具（Lumerical 8.7/10）差距 -2.6。用户要求制定一份**逐月精度的 36 个月路标**（每月一个位置，共 36 个位置），在 36 个月内达到目前最先进同行工具的所有功能。为此需要先做**网络综合分析**，列出所有商业/开源光子 EDA 工具的**完整功能清单**，然后按"从小到大逐个追赶"的策略规划每月交付。

与已有 spec `refresh-commercial-gap-analysis-36mo` 的区别：
- 已有 spec：6 个 6 个月里程碑（M1-M6），粒度粗
- 本 spec：36 个月逐月路标（R1-R36），粒度细，每月一个交付位置
- 本 spec 产出新文件 `docs/36-RoundMap.md`，不覆盖已有文档

## What Changes

- 新增 `docs/36-RoundMap.md`：36 个月逐月路标（R1-R36），每月一个交付位置
- 新增 `docs/commercial_tools_feature_matrix.md`：所有商业/开源光子 EDA 工具功能清单对比矩阵
- 网络综合分析：检索 Lumerical/Luceda IPKISS/Synopsys OptoDesigner/Tidy3D/VPIphotonics/Siemens L-Edit/gdsfactory/KLayout/sax/simphony/OpenROAD 等工具的完整功能清单
- 按"从小到大逐个追赶"策略排序：先追赶最小的开源工具（sax/simphony），再中等工具（KLayout/gdsfactory），最后商业巨头（Luceda/Lumerical/Synopsys）

## Impact

- Affected specs: `refresh-commercial-gap-analysis-36mo`（并行存在，本 spec 更细粒度）
- Affected code: 无代码改动，纯规划文档
- Affected docs:
  - `docs/36-RoundMap.md`（新增）
  - `docs/commercial_tools_feature_matrix.md`（新增）

## 数据来源与学术诚信

所有功能清单必须来自：
1. 商业工具官方文档（WebSearch + WebFetch 检索）
2. 开源工具 GitHub README/文档
3. 学术论文（AlphaChip/Apollo/LiDAR/PhIDO/DREAMPlace）
4. PoLaRIS 现有代码与 `操作记录.md`（第 1-94 轮）

**禁止造假**：所有功能清单须标注来源 URL，不得凭空编造功能。路标中每月交付须可验证（测试/文档/代码）。

---

## ADDED Requirements

### Requirement: 商业工具功能清单对比矩阵

系统 SHALL 提供一份完整的功能清单对比矩阵（`docs/commercial_tools_feature_matrix.md`），覆盖所有主流光子 EDA 工具的完整功能项。

#### 工具覆盖范围（至少 12 个工具）

**商业光子 EDA（7 个）**：
1. Ansys Lumerical（FDTD/MODE/INTERCONNECT/CML Compiler）
2. Luceda IPKISS（版图+仿真+验证）
3. Synopsys OptoDesigner（版图+DRC+布线）
4. Flexcompute Tidy3D（GPU FDTD）
5. VPIphotonics（系统级仿真）
6. Siemens L-Edit Photonics（版图+GPIC）
7. Aspic（电路仿真）

**开源光子 EDA（4 个）**：
8. gdsfactory（Python 版图+仿真+验证，4M+ 下载）
9. KLayout（版图查看+DRC+LVS）
10. sax（频域 S 参数仿真）
11. simphony（光子电路仿真）

**电子 EDA 标杆（2 个，参考）**：
12. Cadence Innovus / Synopsys ICC2（数字 IC PnR 标杆）
13. Google AlphaChip / Circuit Training（AI 布局标杆）

#### 功能清单维度（至少 15 个维度）

1. 布局算法（RL/解析法/手工/参数化）
2. 布线算法（A*/Global-Detail/Curvy/手动）
3. 仿真精度（FDTD/EME/S 参数/频域/时域）
4. PDK 覆盖（foundry 数量/器件数量）
5. DRC/LVS（认证/规则数/引擎）
6. GDS/OASIS 导出（格式/层映射）
7. AI/ML 能力（RL/GNN/逆向设计/LLM）
8. 工艺节点支持（CMOS 节点标注）
9. 规模可扩展性（最大器件数/GPU 加速）
10. GUI/可视化（桌面/Web/CLI）
11. 光电协同仿真（Verilog-A/SPICE）
12. 逆向设计（adjoint/topology/level-set）
13. 量子光子支持
14. 开源/许可模式
15. 用户规模/生态

#### Scenario: 功能清单可溯源
- **WHEN** 用户查看功能清单对比矩阵
- **THEN** 每个功能项标注来源 URL（官方文档/GitHub/论文）
- **AND** PoLaRIS 当前能力列基于第 94 轮真实状态（非造假）

### Requirement: 36 个月逐月路标（R1-R36）

系统 SHALL 提供一份 36 个月逐月路标（`docs/36-RoundMap.md`），每月一个交付位置（R1-R36），在 36 个月内达到最先进同行工具的所有功能。

#### 路标结构

每月（R1-R36）须包含：
1. **月份编号**：R1（2026-07）至 R36（2029-06）
2. **交付目标**：该月交付的具体功能/改进
3. **追赶对象**：该月追赶的工具名（从小到大逐个追赶）
4. **验收标准**：可验证的完成标准（测试/文档/代码）
5. **依赖**：前置月份依赖

#### "从小到大逐个追赶"策略

| 阶段 | 月份范围 | 追赶对象 | 目标 |
|------|----------|----------|------|
| 阶段 1 | R1-R6（2026-07 ~ 2026-12） | sax + simphony | 电路仿真对齐 |
| 阶段 2 | R7-R12（2027-01 ~ 2027-06） | KLayout + gdsfactory | 版图/DRC/PDK 对齐 |
| 阶段 3 | R13-R18（2027-07 ~ 2027-12） | Aspic + VPIphotonics | 系统级仿真对齐 |
| 阶段 4 | R19-R24（2028-01 ~ 2028-06） | Siemens L-Edit + Synopsys OptoDesigner | 商业版图/DRC/布线对齐 |
| 阶段 5 | R25-R30（2028-07 ~ 2028-12） | Luceda IPKISS + Tidy3D | 全流程+FDTD 对齐 |
| 阶段 6 | R31-R36（2029-01 ~ 2029-06） | Ansys Lumerical + AlphaChip | 顶级商业+AI 对齐 |

#### Scenario: 每月交付可验证
- **WHEN** 某月（R_n）交付完成
- **THEN** 该月交付目标有明确的验收标准（测试通过/文档发布/代码合并）
- **AND** 该月追赶对象的功能项在对比矩阵中标注"已对齐"

#### Scenario: 36 个月达到最先进
- **WHEN** R36（2029-06）完成
- **THEN** PoLaRIS 在所有 15 个功能维度上达到或超越最先进同行工具
- **AND** 综合得分从 6.1/10 提升至 9.0/10 以上

### Requirement: 网络综合分析

系统 SHALL 通过 WebSearch/WebFetch 对所有 12+ 个工具进行网络综合分析，获取最新功能清单。

#### 检索范围
- 商业工具官方文档与产品页
- 开源工具 GitHub README 与文档站
- 学术论文（AlphaChip Nature 2021/2024、Apollo arXiv 2025、LiDAR ISPD 2025、PhIDO arXiv 2025、DREAMPlace DAC 2019/TCAD 2020）
- 行业报告与对比文章

#### Scenario: 功能清单基于网络检索
- **WHEN** 编写功能清单对比矩阵
- **THEN** 每个工具的功能项来自 WebSearch/WebFetch 检索结果
- **AND** 标注检索日期（2026-06-22）与来源 URL

---

## MODIFIED Requirements

无（本 spec 为新增，不修改已有 spec）

## REMOVED Requirements

无（本 spec 不移除已有需求）
