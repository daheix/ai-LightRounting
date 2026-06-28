# 学术诚信检查统一管理 Checklist

## 文档结构与命名

- [ ] 新文档路径为 `/workspace/docs/学术诚信检查.md`（中文文件名，按用户要求）
- [ ] 文档文件头含：文档说明 + 当前版本号 v3.0 + 最后更新日期 2026-06-28
- [ ] §1 版本日志在文件开头（最新在前），含 v3.0 条目
- [ ] §2 项目总览含 22 子包 / 357 文件 / 120,692 行统计表
- [ ] §3 按子包逐项审查，覆盖全部 22 个子包
- [ ] §4 关键算法与公式溯源（FDTD/EME/FDE/RCWA/BPM/PPO/GAE/KLM/BB84 等）
- [ ] §5 Bug 与修复历史（按版本号归档）
- [ ] §6 学术诚信声明（R02/R03/R05/R07 合规）

## 历史文档合并

- [ ] 4 个旧文档的关键发现已提取到 §5 Bug 历史
- [ ] `20260627-mvp技术诚信学术审核.md` 的 6 维度审核结果已合并
- [ ] `academic_integrity_audit.md` v1.0/v2.0 的 bug 已合并
- [ ] `academic_integrity_audit_v2.md` 的 43 聚类模块评分已合并
- [ ] `devplan_audit_report.md` 的设计-代码分歧已合并
- [ ] 重复 bug 已去重

## 子包审查覆盖（22/22）

- [ ] sim/（161 文件 58,325 行）— 12 子目录全覆盖
- [ ] pdk/（46 文件 13,167 行）— 顶层 + soi/sin/inp + optodesigner
- [x] trainer/（29 文件 7,908 行）— PPO/BC/GNN-PPO/预训练/迁移学习（v3.1 完成）
- [x] router/（22 文件 7,919 行）— curvy/global/hybrid/multilayer（v3.2 完成，修复 Bug #v3.2-1 Euler 弯曲公式）
- [ ] data/（17 文件 6,250 行）— dataset/benchmark/specs
- [ ] flow/（16 文件 3,599 行）— stage/scheduler/job
- [x] engine/（15 文件 6,071 行）— gnn/alphachip_gnn/floorplan_env（v3.2 完成，R04 标记 gpu_*.py 🚫不参与）
- [x] rl/（9 文件 2,815 行）— alpha_chip/edge_gnn/pretraining（v3.1 完成）
- [ ] io/（8 文件 1,688 行）— GDS/OASIS/CIF/DXF/Gerber/LEF-DEF/ODB++/OpenAccess
- [ ] pipeline/（6 文件 2,371 行）— integrated/curvy_router/training
- [ ] nn/（4 文件 1,236 行）— attention/conv/functional
- [ ] inverse/（3 文件 1,226 行）— adjoint/topology_adjoint
- [ ] gui/（3 文件 1,429 行）— interactive/layout_editor
- [ ] web/（2 文件 783 行）— server/static
- [ ] verify/（2 文件 826 行）— calibre_interface
- [ ] verification/（2 文件 1,194 行）— drc_curvilinear_18rules/statistical_yield
- [ ] quantum/（2 文件 1,027 行）— quantum_circuit_distributed
- [ ] platform/（2 文件 536 行）— education
- [ ] eval/（2 文件 521 行）— layout_render
- [ ] ai/（2 文件 829 行）— inverse_design
- [ ] system/（1 文件 193 行）
- [ ] device/（1 文件 759 行）— tcad_thermal_package

## 每个子包审查内容

- [ ] 文件清单（文件名 / 行数 / 主要功能）
- [ ] 算法清单（算法名 / 实现位置 / 来源文献 / 一致性）
- [ ] 公式清单（公式 / 参数 / 来源 / 一致性）
- [ ] 文献引用清单（URL / 作者 / 年份 / 可达性）
- [ ] Bug 清单（描述 / 根因 / 修复 / 验证）
- [ ] 完成度评估（100% / 部分 / 未完成）
- [ ] 代码-设计匹配性（一致 / 分歧 / 待核查）

## 关键算法溯源

- [ ] FDTD Yee 网格（Kane S. Yee, IEEE TAP 1966）
- [ ] CPML 完美匹配层（Gedney, TAFM 1996）
- [ ] EME 本征模展开（Sztencel 1987）
- [ ] RCWA 严格耦合波分析（Mohar 1995）
- [ ] BPM 光束传播法（Feit & Fleck 1978）
- [ ] KLM 线性光学量子计算（Knill, Laflamme, Milburn, Nature 2001）
- [ ] HOM 双光子干涉（Hong, Ou, Mandel, PRL 1987）
- [ ] BB84 量子密钥分发（Bennett & Brassard 1984）
- [x] PPO 近端策略优化（Schulman et al. 2017）— v3.1 验证 4 文件一致
- [x] GAE 广义优势估计（Schulman et al. ICLR 2016）— v3.1 验证 2 文件一致
- [x] Adam 优化器（Kingma & Ba, ICLR 2015）— v3.1 验证偏置修正 + 一阶/二阶矩
- [x] AlphaChip Edge-GNN（Mirhoseini et al. Nature 2021）— v3.1 验证 R-GCN+GAT+GlobalAttention 3 创新点
- [ ] Si 等离子体色散（Soref & Bennett, IEEE JQE 1987）
- [ ] CODATA 2018 物理常数（c/h/q/k_B/ε_0）

## Bug 修复与版本号

- [ ] v3.0 版本号记录在 §1 顶部
- [ ] v3.0 发现的 bug 数已统计
- [ ] v3.0 修复的 bug 数已统计
- [ ] v3.0 数据修正清单已记录
- [ ] 所有 bug 同步到 §5 Bug 历史
- [ ] 修复的 bug 含回归测试验证

## 旧文档归档

- [ ] `20260627-mvp技术诚信学术审核.md` 顶部追加归档声明
- [ ] `academic_integrity_audit.md` 顶部追加归档声明
- [ ] `academic_integrity_audit_v2.md` 顶部追加归档声明
- [ ] `devplan_audit_report.md` 顶部追加归档声明
- [ ] 旧文档内容未被删除（保留历史可追溯）
- [ ] 归档声明指向 `docs/学术诚信检查.md`

## 学术诚信声明

- [ ] R02 学术诚信合规声明（所有公式/参数真实可溯源）
- [ ] R03 禁止 fall-back 声明（无假数据/无 mock/fake/dummy）
- [ ] R05 Bug 必修声明（无 TODO/FIXME/HACK 残留）
- [ ] R07 操作记录声明（本轮审查已记录到操作记录.md）
- [ ] 无造假数据声明（所有数字真实可验证）

## 提交与记录

- [ ] git add 精确文件（docs/学术诚信检查.md + 4 个旧文档归档声明 + bug 修复）
- [ ] git commit 含详细提交信息
- [ ] git push origin main 成功
- [ ] 操作记录.md 追加本轮学术诚信统一审查记录
- [ ] 提交记录含版本号 v3.0
