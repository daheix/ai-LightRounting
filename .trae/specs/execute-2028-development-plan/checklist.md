# Checklist — 2028 开发计划执行框架

> 依据：`spec.md` §ADDED Requirements（验收标准与质量门禁）+ `tasks.md`（8 Sprint 42 任务）
> 规则：project_rules.md 规则 7/10/14/17/18/22/25/26；python代码开发规则.md §14 检查清单

---

## 通用验收检查点（每聚类必过，依据 spec.md Requirement: 验收标准与质量门禁）

- [ ] **C1. 功能覆盖**：聚类 ✅+⚠️ 功能点占比 ≥80%（P0）/ ≥70%（P1-P6），来源 `00-算法聚类清单.md` §1 总览表
- [ ] **C2. 正确性验证**：解析基准或跨求解器对比误差达标（如 FDTD vs Lumerical ≤0.5 dB），来源聚类算法文档 §10 商业对照
- [ ] **C3. 能量守恒**：TFSF 散射问题 Σ|R|²+Σ|T|²=1 偏差 ≤1e-3，失败立即 raise（规则 14）
- [ ] **C4. 质量门禁**：`python scripts/code_quality_gate.py` 0 警告 0 错误（规则 17）
- [ ] **C5. 测试覆盖**：核心模块 ≥90%，行覆盖 ≥80%（规则 10.1），`pytest tests/test_<cluster>.py --cov`
- [ ] **C6. 学术诚信**：文献溯源 URL ≥5 个，*创新* 点标注底层逻辑+支持理论+案例（规则 18），来源聚类算法文档 §8 文献来源
- [ ] **C7. 无 fall-back**：禁止 try/except 回退、禁止假数据、禁止待办/修复标记（规则 14），`grep -r "except.*pass\|TODO\|FIXME" src/polaris/<module>/` 无结果
- [ ] **C8. 代码风格**：Ruff format + Ruff check 通过（python代码开发规则.md §1），`ruff check src/polaris/<module>/ && ruff format --check src/polaris/<module>/`
- [ ] **C9. 类型注解**：mypy --strict 通过（python代码开发规则.md §2），`mypy src/polaris/<module>/`
- [ ] **C10. 三方库合规**：仅使用 ✅可商用 库（MIT/Apache/BSD/ISC/MPL/LGPL），来源 `3dtool/INVENTORY.md` 四档分类（规则 13.2）
- [ ] **C11. 算法合规**：无暴力算法/抵消算法/嵌套循环查重（python代码开发规则.md §4），复杂度达标
- [ ] **C12. 网络资源核查**：该聚类相关的最新论文/开源项目已核查并更新到算法文档 §8（spec.md Requirement: 网络资源核查与更新）

---

## Sprint 0 检查点（A04-FDE 本征模求解）

- [ ] **S0-C1**: `src/polaris/sim/fde/` 目录存在，含 Arnoldi 本征求解器实现
- [ ] **S0-C2**: `src/polaris/sim/grid/yee.py` Yee 网格共享组件存在，供 A05/A06/A09 复用
- [ ] **S0-C3**: SOI strip 波导 neff vs Lumerical 误差 ≤1e-4（解析基准或文献对比）
- [ ] **S0-C4**: 模式归一化实现（功率归一化 ∫|E|²dA=1），单元测试覆盖
- [ ] **S0-C5**: `tests/test_a04_fde.py` 覆盖率 ≥90%，文献 URL ≥5（Yee 1966/Snyder 1983/Joannopoulos 2008 等）
- [ ] **S0-C6**: 通用检查点 C1-C12 全部通过

## Sprint 1 检查点（A05-FDFD / A01-RCWA / A02-EME / C03-Redheffer）

- [ ] **S1-C1**: A05-FDFD `src/polaris/sim/fdfd/` 频域 Maxwell 稀疏线性系统求解实现
- [ ] **S1-C2**: A05-FDFD SC-PML 实现，单频高精度，能量守恒 Σ|R|²+Σ|T|²=1 偏差 ≤1e-3
- [ ] **S1-C3**: A01-RCWA `src/polaris/sim/rcwa/` 傅里叶展开 + 本征值 + Redheffer 星积实现
- [ ] **S1-C4**: A01-RCWA Li 1996 normal/vector 公式自适应切换实现
- [ ] **S1-C5**: A01-RCWA 光栅衍射效率 vs Lumerical ≤0.5 dB
- [ ] **S1-C6**: C03-Redheffer `src/polaris/sim/cascade/smatrix.py` Redheffer 星积完整公式实现
- [ ] **S1-C7**: C03-Redheffer 数值稳定性验证（消逝波无发散），`tests/test_c03_redheffer.py` 通过
- [ ] **S1-C8**: A02-EME `src/polaris/sim/eme/` 模式求解 + 重叠积分 + S 矩阵级联实现
- [ ] **S1-C9**: A02-EME 长结构高精度，与 A04 FDE 模式对齐
- [ ] **S1-C10**: Sprint 1 所有聚类的通用检查点 C1-C12 全部通过

## Sprint 2 检查点（A03/A06/A09/A07/A08/B01-B04）

- [ ] **S2-C1**: A03-BPM `src/polaris/sim/bpm/` ADI 分裂 + Hadley 1992 TBC + 自适应步长实现
- [ ] **S2-C2**: A03-BPM 长距离波导 vs Lumerical ≤0.5 dB
- [ ] **S2-C3**: A06-2.5D-FDTD `src/polaris/sim/varfdtd/` FDE 折叠 + 2D Yee leapfrog 实现
- [ ] **S2-C4**: A06-2.5D-FDTD 大尺寸 PIC 仿真效率 vs 3D FDTD 提升 10×
- [ ] **S2-C5**: A09-FDTD Phase 1-2 `src/polaris/sim/fdtd/` Yee leapfrog + CPML + TFSF 实现
- [ ] **S2-C6**: A09-FDTD Phase 3-4 色散 ADE + 亚像素平滑 + DFT 监视器 + S 参数提取实现
- [ ] **S2-C7**: A09-FDTD 高斯脉冲误差 <1e-3，CPML 反射 ≤-60 dB，金 Drude 反射率 vs Palik <2%，SOI 环 vs Lumerical ≤0.5 dB
- [ ] **S2-C8**: A09-FDTD 文献 URL ≥5（Yee 1966/Taflove 2005/Roden & Gedney 2000/Moharam 1995/arXiv:2507.22301）
- [ ] **S2-C9**: A07-HEAT `src/polaris/sim/heat/` 傅里叶导热 + FEM + 5 类边界实现
- [ ] **S2-C10**: A07-HEAT 与 DDM/FDE 双向耦合验证
- [ ] **S2-C11**: A08-DDM `src/polaris/sim/ddm/` Poisson + Scharfetter-Gummel + Gummel 迭代实现
- [ ] **S2-C12**: A08-DDM 电热自洽，与 FDE 单向耦合验证
- [ ] **S2-C13**: B02-DRC `src/polaris/layout/drc/` layer-wise BVH + 自适应行分块实现
- [ ] **S2-C14**: B02-DRC 扩展至 18 类规则，KLayout DRC 100% 对齐
- [ ] **S2-C15**: B01/B03/B04 GDS 读写 + LVS + PDK 11 foundry 全覆盖
- [ ] **S2-C16**: M1 里程碑达成（P0 求解器 7/7 完成）+ M2 里程碑达成（MVP v1.0 端到端流水线跑通，100 次迭代稳定性 ≥95%）+ M3 里程碑达成（P1 版图 DRC 完成）
- [ ] **S2-C17**: Sprint 2 所有聚类的通用检查点 C1-C12 全部通过

## Sprint 3 检查点（B05/C01-C05/F01-P1-2）

- [ ] **S3-C1**: C01-S 参数 `src/polaris/sim/cascade/sparam.py` S 参数级联 + 子网络增长实现
- [ ] **S3-C2**: C01-S 参数 8 工具对齐，比 Lumerical 快 20×
- [ ] **S3-C3**: C02-子网络 `src/polaris/sim/cascade/subnetwork.py` BFS 拓扑排序 + 逐步级联 O(N) 实现
- [ ] **S3-C4**: C04-时域 `src/polaris/sim/time/` 状态空间 + RK45 + CAPHE CMT + 无源线性节点自动消去实现
- [ ] **S3-C5**: C05-频域 `src/polaris/sim/freq/` 频率点生成 + JAX vmap 向量化实现
- [ ] **S3-C6**: B05-GUI `src/polaris/eval/gui/` 场景图 + 视图变换 + 撤销栈 + DRC 高亮实现
- [ ] **S3-C7**: B05-GUI KLayout 集成，4/8/20 状态提升
- [ ] **S3-C8**: F01-伴随 Phase 1 FDFD 频域伴随实现（SC-PML 算子构造 A）
- [ ] **S3-C9**: F01-伴随 Phase 2 FDTD 时域伴随实现（leapfrog 复用为伴随内核）
- [ ] **S3-C10**: F01-伴随 SOI Y 分支梯度 vs CS 检验 ≤1e-3
- [ ] **S3-C11**: M4 里程碑达成（P2 仿真级联完成，S 参数级联比 Lumerical 快 20×，Redheffer 自研稳定）
- [ ] **S3-C12**: Sprint 3 所有聚类的通用检查点 C1-C12 全部通过

## Sprint 4 检查点（D01-D05/E01-E04/F01-P3-5）

- [ ] **S4-C1**: D01-GNN `src/polaris/ml/gnn/` 15 维光子边特征 + 三关系 R-GCN + GAT + GlobalAttention 实现
- [ ] **S4-C2**: D01-GNN TILOS Ariane 基准对齐
- [ ] **S4-C3**: D03-PPO `src/polaris/ml/rl/ppo.py` PPO-clip + GAE + actor-critic 实现
- [ ] **S4-C4**: D03-PPO 与 Stable-Baselines3 超参对齐
- [ ] **S4-C5**: D04-奖励 `src/polaris/ml/rl/reward.py` 多目标奖励 + PBRS + 课程调度 L0-L4 实现
- [ ] **S4-C6**: D04-奖励 防遗忘 λ=0.4 验证
- [ ] **S4-C7**: D05-AlphaChip `src/polaris/ml/alpha_chip.py` 光子版 AlphaChip 实现
- [ ] **S4-C8**: D05-AlphaChip 文献 URL ≥5（Schlichtkrull 2018/Veličković 2018/Mirhoseini 2021/arXiv:2504.18813 Apollo/arXiv:2507.22301 PoLaRIS）
- [ ] **S4-C9**: D05-AlphaChip IEEE TCAD 投稿准备（AC-12.2）
- [ ] **S4-C10**: D02-CNN `src/polaris/ml/cnn/congestion.py` U-Net + 拥塞预测 + 栅格化实现
- [ ] **S4-C11**: D02-CNN DRC 违例预测准确率 ≥85%
- [ ] **S4-C12**: E01-A* `src/polaris/router/waveguide_router.py` A* + JPS 跳跃 + Euler 弯曲完善
- [ ] **S4-C13**: E01-A* 单连接 <50ms（规则 15.1），文献 URL ≥5（LiDAR ISPD 2025 等）
- [ ] **S4-C14**: E02-通道 `src/polaris/router/channel.py` 左缘算法 + VCG/HCG + RRR 迭代实现，4 工具对齐
- [ ] **S4-C15**: E03-多层 `src/polaris/router/multilayer.py` 层分配 + OTV + 3D A* 实现，3 工具对齐
- [ ] **S4-C16**: E04-光电协同 `src/polaris/router/electro_optic.py` 光电联合代价可微公式实现，5 工具对齐
- [x] **S4-C17**: F01-伴随 Phase 3 密度法二值化（锥形滤波 + sigmoid 投影 + 螺旋 β 退火）实现（`src/polaris/inverse/adjoint_optimizer.py` conic_filter + density_projection + _beta_schedule）
- [x] **S4-C18**: F01-伴随 Phase 4 DRC 感知约束梯度惩罚（与 B02 联合）实现（`_drc_penalty_jax` 基于 mean(|∇ρ|²)，Piggott 2020 ACS Photonics）
- [ ] **S4-C19**: F01-伴随 Phase 5 一行入口 `polaris.inverse_design(...)` 实现（部分完成：已有设备级 example_mmi_1x2/example_grating_coupler/example_mode_converter 入口，待补 generic inverse_design() 通用入口）
- [x] **S4-C20**: F01-伴随 GDSII 100% DRC 通过（`export_gds` via gdstk 像素矩形，28 测试全通过含读回验证）
- [ ] **S4-C21**: M5 里程碑达成（AlphaChip 对标，TILOS 基准对齐）+ M6 里程碑达成（逆向设计平台，FDTD/FDFD 双伴随 + DRC 感知 + 一行入口）
- [ ] **S4-C22**: Sprint 4 所有聚类的通用检查点 C1-C12 全部通过

## Sprint 5 检查点（F02-F04/G01-G03）

- [ ] **S5-C1**: F02-自动微分 `src/polaris/optimize/autodiff.py` 链式法则 + JVP/VJP + 双数 + JAX autograd 实现
- [ ] **S5-C2**: F02-自动微分 atol=1e-4 失败即告警（中心差分交叉校验）
- [ ] **S5-C3**: F03-贝叶斯 `src/polaris/optimize/bayesian.py` BO/PSO/CMA-ES/NSGA-II + GP 后验 + EI/UCB 实现
- [ ] **S5-C4**: F03-贝叶斯 7 工具对齐
- [ ] **S5-C5**: F04-梯度 `src/polaris/optimize/gradient.py` SGD/Adam/L-BFGS + AMSGrad + AdamW + 余弦退火实现
- [ ] **S5-C6**: F04-梯度 5 工具对齐
- [ ] **S5-C7**: G01-HOM `src/polaris/quantum/hom.py` HOM dip + KLM CNOT + 玻色采样 + Ryser 积和式实现
- [ ] **S5-C8**: G01-HOM T01 对齐
- [ ] **S5-C9**: G02-Clements/Reck `src/polaris/quantum/decompose.py` Reck 三角 + Clements 矩形 + QR 迭代实现
- [ ] **S5-C10**: G02-Clements/Reck T11 对齐
- [ ] **S5-C11**: G03-BER `src/polaris/quantum/ber.py` Q 因子 + BER 高斯近似 + 眼图 + 蒙特卡洛实现
- [ ] **S5-C12**: G03-BER 4 工具对齐，超越实验性
- [ ] **S5-C13**: M7 里程碑达成（商业级 v2.0，1000 器件规模，差距 ≤2.0 分）
- [ ] **S5-C14**: Sprint 5 所有聚类的通用检查点 C1-C12 全部通过

## Sprint 6 检查点（H01/H02）

- [ ] **S6-C1**: H01-电光耦合 `src/polaris/multiphysics/electro_optic.py` Poisson + Scharfetter-Gummel + Soref 等离子色散 + Pockels/Kerr 实现
- [ ] **S6-C2**: H01-电光耦合 DDM→电光效应→FDE 三场自洽验证
- [ ] **S6-C3**: H01-电光耦合 5 工具对齐，VπL 闭环，文献 URL ≥5（Soref & Bennett 1987）
- [ ] **S6-C4**: H02-热光效应 `src/polaris/multiphysics/thermo_optic.py` 傅里叶导热 + Cocorullo dn/dT + 热串扰矩阵实现
- [ ] **S6-C5**: H02-热光效应 4 工具对齐，超越线性近似
- [ ] **S6-C6**: Sprint 6 所有聚类的通用检查点 C1-C12 全部通过

## Sprint 7 检查点（I01-I04/J01/J02）

- [ ] **S7-C1**: I01-网表 `src/polaris/io/netlist.py` DAG + Kahn 拓扑排序 + 子电路展开 + Hash 签名实现，6 工具对齐
- [ ] **S7-C2**: I02-可视化 `src/polaris/io/viz.py` 仿射视图变换 + Marching Squares + Smith 圆图 + Poincaré 球实现，9 工具对齐
- [ ] **S7-C3**: I03-GDS/OASIS `src/polaris/io/gds_export.py` 贝塞尔离散 + Euler 螺线 + Sutherland-Hodgman + VarCode 压缩实现，7 工具对齐
- [ ] **S7-C4**: I04-SPICE `src/polaris/io/spice_export.py` RLCG 等效电路 + S→Y→Z + Verilog-A ddt + Newton-Raphson 实现，5 工具对齐
- [ ] **S7-C5**: J01-脚本 API `src/polaris/platform/api.py` API 契约 + Kahn 拓扑 + 令牌桶限流 + LRU-Zipf 缓存实现，10 工具对齐
- [ ] **S7-C6**: J02-商业生态 `src/polaris/platform/education.py` 知识图谱 + TF-IDF + PageRank + IRT 评估实现，6 工具对齐
- [ ] **S7-C7**: M8 里程碑达成（全量交付 v3.0，43 聚类 100% 覆盖，940 功能点 ≥90% ✅）
- [ ] **S7-C8**: Sprint 7 所有聚类的通用检查点 C1-C12 全部通过

---

## 框架完整性检查点（spec 执行层）

- [x] **F1**: spec.md 存在且包含 5 个 ADDED Requirements（8 阶段框架/标准化任务结构/关键路径依赖/网络资源核查/验收标准）
- [x] **F2**: tasks.md 存在且包含 8 Sprint × 42 任务，每任务含算法文档引用 + 代码路径 + 验收标准 + 依赖关系
- [x] **F3**: checklist.md 存在且包含 12 通用检查点 + 8 Sprint 专项检查点 + 框架完整性检查点
- [x] **F4**: 网络资源核查已完成（5 项关键资源：arXiv:2507.22301/LiDAR ISPD 2025/Apollo arXiv:2504.18813/FDTDX 0.6.2/PPO OES 2026）
- [x] **F5**: 43 聚类算法文档均被引用（A01-J02），路径 `2026-2028开发计划/功能清单与实现/`
- [x] **F6**: 关键路径依赖明确（A04→A09→F01 / A01+A02→C03 / D01+D03+D04→D05）
- [x] **F7**: 8 个里程碑（M1-M8）对应 Sprint 验收点
- [x] **F8**: 规则对齐（规则 1/7/10/14/17/18/22/25/26 + python代码开发规则.md）
