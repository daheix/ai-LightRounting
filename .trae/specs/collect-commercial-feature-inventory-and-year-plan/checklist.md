# Checklist

## 阶段一：商业产品功能点级清单

- [x] T01 Ansys Lumerical 功能点清单包含 FDTD/MODE/INTERCONNECT/CML Compiler 四模块子功能
- [x] T01 每个功能点标注来源 URL（Ansys 官网）
- [x] T02 Luceda IPKISS 功能点清单包含核心/Canvas/Design Flow 子功能
- [x] T02 每个功能点标注来源 URL（Luceda 官网）
- [x] T03 Synopsys OptoDesigner 功能点清单包含 Design Intent/布线/DRC/GDS 子功能
- [x] T03 每个功能点标注来源 URL（Synopsys 官网）
- [x] T04 Tidy3D 功能点清单包含 GPU FDTD/伴随优化/拓扑优化子功能
- [x] T04 每个功能点标注来源 URL（Tidy3D 官网）
- [x] T05 VPIphotonics 功能点清单包含时域/频域/TLM/BPM/光电协同子功能
- [x] T05 每个功能点标注来源 URL（VPIphotonics 官网）
- [x] T06 L-Edit Photonics 功能点清单包含版图编辑/GPIC/SDL/Calibre 子功能
- [x] T06 每个功能点标注来源 URL（Siemens 官网）
- [x] T07 Photon Design 功能点清单包含 FIMMPROP/OmniSim/PICWave/Kallistos 子功能
- [x] T07 每个功能点标注来源 URL（Photon Design 官网）
- [x] T08 gdsfactory 功能点清单包含参数化器件/布线/DRC/PDK 子功能
- [x] T08 每个功能点标注来源 URL（gdsfactory GitHub）
- [x] T09 KLayout 功能点清单包含查看/编辑/DRC/LVS/格式子功能
- [x] T09 每个功能点标注来源 URL（KLayout 官网）
- [x] T10 sax 功能点清单包含 JAX S 参数/autograd 子功能
- [x] T10 每个功能点标注来源 URL（sax GitHub）
- [x] T11 simphony 功能点清单包含 S 参数级联/SiEPIC 子功能
- [x] T11 每个功能点标注来源 URL（simphony GitHub）
- [x] T12 Cadence Innovus + Synopsys ICC2 功能点清单含 GigaPlace/PRO/Zroute 子功能
- [x] T12 每个功能点标注来源 URL（Cadence/Synopsys 官网）
- [x] T13 AlphaChip + Circuit Training 功能点清单含 Edge-GNN/PPO/预训练子功能
- [x] T13 每个功能点标注来源 URL（Nature 论文 + GitHub）

## 阶段二：PoLaRIS 自身功能点清单

- [x] polaris_feature_inventory.md 覆盖 src/polaris/ 所有模块
- [x] 每个功能点标注实现位置（文件:行号）
- [x] 每个功能点标注成熟度（生产可用/实验性/原型）
- [x] 实验性功能诚实标注"实验性"，不夸大

## 阶段三：全量差距分析

- [x] feature_gap_full_analysis.md 对 T01-T13 每个功能点标注 PoLaRIS 状态
- [x] 状态标注使用统一图例（✅已有/⚠️部分/❌缺失/🚫不适用）
- [x] 统计每个工具的覆盖率百分比
- [x] 列出 PoLaRIS 独家功能点
- [x] 缺失功能点按 P0/P1/P2/P3 优先级排序

## 阶段四：一年开发计划

- [x] year_plan_2026_06_2027_05.md 覆盖 12 个月（2026-06 到 2027-05）
- [x] 每个月有核心目标（1 句话）
- [x] 每个月有交付功能点清单（从差距分析选取）
- [x] 每个月有可量化验收标准
- [x] 每个月标注依赖关系
- [x] 优先级遵循 P0>P1>P2>P3 原则

## 学术诚信

- [x] 所有商业产品功能点来源 URL 可访问
- [x] 未公开能力标注"未公开"而非臆造
- [x] PoLaRIS 功能点基于实际代码（引用文件:行号）
- [x] 定价/用户规模等敏感数据标注"估算（来源 URL）"
- [x] 无任何夸大或造假

## 文档完整性

- [x] 操作记录.md 追加本轮记录
- [x] 代码已提交合并 main 分支
- [x] 所有文档版本号统一（v1.0）
- [x] 最终汇总报告展示给用户
