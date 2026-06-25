# Tasks — 2028 开发计划执行框架

> 依据：`spec.md` §ADDED Requirements（8 阶段迭代开发框架）
> 来源：`2026-2028开发计划/功能清单与实现/完整开发计划.md` + 43 聚类算法文档
> 规则：project_rules.md 规则 1/7/10/14/17/18/22/25/26；python代码开发规则.md

---

## Sprint 0：P0 求解器底座（2026Q1）

- [ ] Task 0.1: A04-FDE 本征模求解 — 求解器栈底座，统一 Yee 网格数据结构供下游零成本复用
  - [ ] SubTask 0.1.1: 实现 `src/polaris/sim/fde/` Arnoldi 本征求解器（稀疏本征值，scipy.sparse.linalg.eigsh）
  - [ ] SubTask 0.1.2: 实现 Yee 网格共享组件 `src/polaris/sim/grid/yee.py`（供 A05/A06/A09 复用）
  - [ ] SubTask 0.1.3: 实现模式归一化（功率归一化 ∫|E|²dA=1）
  - [ ] SubTask 0.1.4: 验收 — SOI strip 波导 neff vs Lumerical 误差 ≤1e-4
  - [ ] SubTask 0.1.5: 测试 `tests/test_a04_fde.py` 覆盖率 ≥90%，文献 URL ≥5（Yee 1966/Snyder 1983/Joannopoulos 2008）

## Sprint 1：P0 频域求解器 + S 矩阵级联（2026Q1-Q2）

- [ ] Task 1.1: A05-FDFD 频域有限差分 — 与 A04 共享 Yee 网格 + SC-PML
  - [ ] SubTask 1.1.1: 实现 `src/polaris/sim/fdfd/` 频域 Maxwell 稀疏线性系统求解（scipy.sparse.linalg.spsolve）
  - [ ] SubTask 1.1.2: 实现 SC-PML（Stretched Coordinate Perfectly Matched Layer）
  - [ ] SubTask 1.1.3: 验收 — 单频高精度，能量守恒 Σ|R|²+Σ|T|²=1 偏差 ≤1e-3
  - 依赖：Task 0.1

- [ ] Task 1.2: A01-RCWA 严格耦合波分析 — Moharam 1995 + Li 1996
  - [ ] SubTask 1.2.1: 实现 `src/polaris/sim/rcwa/` 傅里叶展开 + 本征值 + Redheffer 星积
  - [ ] SubTask 1.2.2: 实现 Li 1996 normal/vector 公式自适应切换
  - [ ] SubTask 1.2.3: 验收 — 光栅衍射效率 vs Lumerical ≤0.5 dB
  - 依赖：Task 1.3（Redheffer 星积）

- [ ] Task 1.3: C03-Redheffer 星积 S 矩阵级联 — 自研星积内核，供 A01/A02 共享
  - [ ] SubTask 1.3.1: 实现 `src/polaris/sim/cascade/smatrix.py` Redheffer 星积完整公式
  - [ ] SubTask 1.3.2: 数值稳定性验证（消逝波无发散）
  - [ ] SubTask 1.3.3: 测试 `tests/test_c03_redheffer.py`，文献 URL ≥5（Redheffer 1962/Jin 2014）
  - 依赖：无（可与 Task 1.1/1.2 并行起步）

- [ ] Task 1.4: A02-EME 本征模展开 — 双向本征模展开，与 C03 共享 S 矩阵
  - [ ] SubTask 1.4.1: 实现 `src/polaris/sim/eme/` 模式求解 + 重叠积分 + S 矩阵级联
  - [ ] SubTask 1.4.2: 验收 — 长结构高精度，与 A04 FDE 模式对齐
  - 依赖：Task 0.1（FDE 模式）、Task 1.3（Redheffer）

## Sprint 2：P0 收尾 + P1 版图 DRC + 多物理基础（2026Q3-Q4）

- [ ] Task 2.1: A03-BPM 光束传播 — ADI 分裂 + Hadley 1992 TBC
  - [ ] SubTask 2.1.1: 实现 `src/polaris/sim/bpm/` Crank-Nicolson/ADI + 自适应步长 + TBC
  - [ ] SubTask 2.1.2: 验收 — 长距离波导 vs Lumerical ≤0.5 dB
  - 依赖：Task 0.1

- [ ] Task 2.2: A06-2.5D-FDTD 变分 FDTD — 复用 FDE+FDTD 双内核
  - [ ] SubTask 2.2.1: 实现 `src/polaris/sim/varfdtd/` FDE 折叠 + 2D Yee leapfrog + 模式注入
  - [ ] SubTask 2.2.2: 验收 — 大尺寸 PIC 仿真效率 vs 3D FDTD 提升 10×
  - 依赖：Task 0.1、Task 2.3（FDTD）

- [ ] Task 2.3: A09-FDTD 时域有限差分 — 自研 Yee leapfrog + CPML + TFSF（Phase 1-4）
  - [ ] SubTask 2.3.1: Phase 1-2: `src/polaris/sim/fdtd/` Yee leapfrog + CPML + TFSF
  - [ ] SubTask 2.3.2: Phase 3-4: 色散 ADE + 亚像素平滑 + DFT 监视器 + S 参数提取
  - [ ] SubTask 2.3.3: 验收 — 高斯脉冲误差 <1e-3，CPML 反射 ≤-60 dB，金 Drude 反射率 vs Palik <2%，SOI 环 vs Lumerical ≤0.5 dB
  - [ ] SubTask 2.3.4: 文献 URL ≥5（Yee 1966/Taflove 2005/Roden & Gedney 2000 CPML/Moharam 1995/arXiv:2507.22301 PoLaRIS 论文）
  - 依赖：Task 0.1

- [ ] Task 2.4: A07-HEAT 热传导求解 — scipy.sparse 求解
  - [ ] SubTask 2.4.1: 实现 `src/polaris/sim/heat/` 傅里叶导热 + FEM + 5 类边界
  - [ ] SubTask 2.4.2: 验收 — 与 DDM/FDE 双向耦合
  - 依赖：无

- [ ] Task 2.5: A08-DDM 漂移扩散求解 — Scharfetter-Gummel 离散
  - [ ] SubTask 2.5.1: 实现 `src/polaris/sim/ddm/` Poisson + 连续性 + Scharfetter-Gummel + Gummel 迭代
  - [ ] SubTask 2.5.2: 验收 — 电热自洽，与 FDE 单向耦合
  - 依赖：Task 2.4（HEAT 双向耦合）

- [ ] Task 2.6: B02-DRC 设计规则检查扩展 — BVH + 层次化 DRC 扩展至 18 类规则
  - [ ] SubTask 2.6.1: 扩展 `src/polaris/layout/drc/` layer-wise BVH + 自适应行分块
  - [ ] SubTask 2.6.2: 验收 — KLayout DRC 100% 对齐
  - 依赖：无

- [ ] Task 2.7: B01/B03/B04 版图基础完善 — GDS 读写 + LVS + PDK 扩展
  - [ ] SubTask 2.7.1: 完善 `src/polaris/layout/gds/` GDS 读写 + 多边形布尔运算
  - [ ] SubTask 2.7.2: 完善 `src/polaris/layout/lvs/` 器件识别 + 网表提取 + VF2 图同构
  - [ ] SubTask 2.7.3: 完善 `src/polaris/layout/pdk/` 11 foundry 全覆盖
  - 依赖：Task 2.6

## Sprint 3：P2 仿真级联 + GUI + 逆向设计起步（2027Q1-Q2）

- [ ] Task 3.1: C01-S 参数仿真与级联 — SAX 复刻完善 + Touchstone 双向
  - [ ] SubTask 3.1.1: 完善 `src/polaris/sim/cascade/sparam.py` S 参数级联 + 子网络增长
  - [ ] SubTask 3.1.2: 验收 — 8 工具对齐，比 Lumerical 快 20×
  - 依赖：Task 1.3（Redheffer）

- [ ] Task 3.2: C02-子网络增长算法 — SAX 子网络算法完整复刻
  - [ ] SubTask 3.2.1: 实现 `src/polaris/sim/cascade/subnetwork.py` BFS 拓扑排序 + 逐步级联 O(N)
  - [ ] SubTask 3.2.2: 验收 — T10/T11 对齐
  - 依赖：Task 3.1

- [ ] Task 3.3: C04-时域仿真 — CAPHEBackend 自动稀疏化
  - [ ] SubTask 3.3.1: 完善 `src/polaris/sim/time/` 状态空间 + RK45 + CAPHE CMT
  - [ ] SubTask 3.3.2: 实现无源线性节点自动消去（图论叶子节点消去）
  - 依赖：Task 3.1

- [ ] Task 3.4: C05-频域扫描 — 频率/参数扫描完善
  - [ ] SubTask 3.4.1: 实现 `src/polaris/sim/freq/` 频率点生成 + JAX vmap 向量化
  - [ ] SubTask 3.4.2: 验收 — 6 工具对齐
  - 依赖：Task 3.1

- [ ] Task 3.5: B05-版图编辑器 GUI — `src/polaris/eval/gui/` 编辑器
  - [ ] SubTask 3.5.1: 实现场景图 + 视图变换 + 撤销栈 + DRC 高亮
  - [ ] SubTask 3.5.2: 验收 — KLayout 集成，4/8/20 状态提升
  - 依赖：Task 2.6、Task 2.7

- [ ] Task 3.6: F01-伴随方法逆向设计 Phase 1-2 — FDFD 伴随 + FDTD 时域伴随
  - [ ] SubTask 3.6.1: Phase 1: FDFD 频域伴随（SC-PML 算子构造 A）
  - [ ] SubTask 3.6.2: Phase 2: FDTD 时域伴随（leapfrog 复用为伴随内核）
  - [ ] SubTask 3.6.3: 验收 — SOI Y 分支梯度 vs CS ≤1e-3
  - 依赖：Task 1.1（FDFD）、Task 2.3（FDTD）

## Sprint 4：P3 ML/RL + 布线对标 AlphaChip（2027Q3-Q4）

- [ ] Task 4.1: D01-GNN 图神经网络 — Edge-GNN 多关系 + GAT + GlobalAttention
  - [ ] SubTask 4.1.1: 实现 `src/polaris/ml/gnn/` 15 维光子边特征 + 三关系 R-GCN
  - [ ] SubTask 4.1.2: 验收 — TILOS Ariane 基准对齐
  - 依赖：无（可与 D03/D04 并行）

- [ ] Task 4.2: D03-PPO 强化学习 — PPO-clip + GAE 完整复刻
  - [ ] SubTask 4.2.1: 实现 `src/polaris/ml/rl/ppo.py` PPO-clip + GAE + actor-critic
  - [ ] SubTask 4.2.2: 验收 — 与 Stable-Baselines3 超参对齐
  - 依赖：无

- [ ] Task 4.3: D04-奖励塑造与课程学习 — EWC + 课程学习完善
  - [ ] SubTask 4.3.1: 实现 `src/polaris/ml/rl/reward.py` 多目标奖励 + PBRS + 课程调度 L0-L4
  - [ ] SubTask 4.3.2: 验收 — 防遗忘 λ=0.4
  - 依赖：Task 4.2

- [ ] Task 4.4: D05-AlphaChip 对标 — 15 维光子边特征 + 三关系 R-GCN + GAT + GlobalAttention
  - [ ] SubTask 4.4.1: 实现 `src/polaris/ml/alpha_chip.py` 光子版 AlphaChip
  - [ ] SubTask 4.4.2: 验收 — IEEE TCAD 投稿（AC-12.2），文献 URL ≥5（Schlichtkrull 2018 R-GCN/Veličković 2018 GAT/Mirhoseini 2021 Nature/arXiv:2504.18813 Apollo）
  - 依赖：Task 4.1、Task 4.2、Task 4.3

- [ ] Task 4.5: D02-CNN 拥塞预测 — CongestionCNN 光子领域首个
  - [ ] SubTask 4.5.1: 实现 `src/polaris/ml/cnn/congestion.py` U-Net + 拥塞预测 + 栅格化
  - [ ] SubTask 4.5.2: 验收 — DRC 违例预测准确率 ≥85%
  - 依赖：无

- [ ] Task 4.6: E01-A*/JPS-Bend 布线完善 — 波导布线核心算法完善
  - [ ] SubTask 4.6.1: 完善 `src/polaris/router/waveguide_router.py` A* + JPS 跳跃 + Euler 弯曲
  - [ ] SubTask 4.6.2: 验收 — 单连接 <50ms（规则 15.1），文献 URL ≥5（LiDAR ISPD 2025/arXiv:2507.22301）
  - 依赖：无

- [ ] Task 4.7: E02-通道布线 — rip-up-reroute + 曼哈顿
  - [ ] SubTask 4.7.1: 实现 `src/polaris/router/channel.py` 左缘算法 + VCG/HCG + RRR 迭代
  - [ ] SubTask 4.7.2: 验收 — 4 工具对齐
  - 依赖：Task 4.6

- [ ] Task 4.8: E03-多层布线 — 光子 OTV + 电子 TSV 混合 3D
  - [ ] SubTask 4.8.1: 实现 `src/polaris/router/multilayer.py` 层分配 + OTV + 3D A* + 光子 via
  - [ ] SubTask 4.8.2: 验收 — 3 工具对齐
  - 依赖：Task 4.6

- [ ] Task 4.9: E04-光电协同布线 — 光电联合代价可微公式
  - [ ] SubTask 4.9.1: 实现 `src/polaris/router/electro_optic.py` 光电联合代价 + 先光后电 + 虚拟屏蔽
  - [ ] SubTask 4.9.2: 验收 — 5 工具对齐
  - 依赖：Task 4.6

- [ ] Task 4.10: F01-伴随方法逆向设计 Phase 3-5 — 密度法二值化 + DRC 感知 + 一行入口
  - [ ] SubTask 4.10.1: Phase 3: 密度法二值化（锥形滤波 + sigmoid 投影 + 螺旋 β 退火）
  - [ ] SubTask 4.10.2: Phase 4: DRC 感知约束梯度惩罚（与 B02 联合）
  - [ ] SubTask 4.10.3: Phase 5: 一行入口 `polaris.inverse_design(...)`
  - [ ] SubTask 4.10.4: 验收 — GDSII 100% DRC 通过
  - 依赖：Task 3.6、Task 2.6（DRC）

## Sprint 5：P4 优化 + 量子光子（2028Q1-Q2）

- [ ] Task 5.1: F02-自动微分 — JAX 可微器件模型 + 中心差分交叉校验
  - [ ] SubTask 5.1.1: 实现 `src/polaris/optimize/autodiff.py` 链式法则 + JVP/VJP + 双数 + JAX autograd
  - [ ] SubTask 5.1.2: 验收 — atol=1e-4 失败即告警
  - 依赖：Task 3.1（S 参数）

- [ ] Task 5.2: F03-贝叶斯与全局优化 — PSO/CMA-ES/NSGA-II/III 完整
  - [ ] SubTask 5.2.1: 实现 `src/polaris/optimize/bayesian.py` BO/PSO/CMA-ES/NSGA-II + GP 后验 + EI/UCB
  - [ ] SubTask 5.2.2: 验收 — 7 工具对齐
  - 依赖：无

- [ ] Task 5.3: F04-梯度下降与 Adam — L-BFGS/Adam 优化器
  - [ ] SubTask 5.3.1: 实现 `src/polaris/optimize/gradient.py` SGD/Adam/L-BFGS + AMSGrad + AdamW + 余弦退火
  - [ ] SubTask 5.3.2: 验收 — 5 工具对齐
  - 依赖：无

- [ ] Task 5.4: G01-HOM 干涉与量子门 — 量子门 + KLM CNOT
  - [ ] SubTask 5.4.1: 实现 `src/polaris/quantum/hom.py` HOM dip + KLM CNOT + 玻色采样 + Ryser 积和式
  - [ ] SubTask 5.4.2: 验收 — T01 对齐
  - 依赖：无

- [ ] Task 5.5: G02-Clements/Reck 分解 — 量子光路分解
  - [ ] SubTask 5.5.1: 实现 `src/polaris/quantum/decompose.py` Reck 三角 + Clements 矩形 + QR 迭代 + MZI 参数化
  - [ ] SubTask 5.5.2: 验收 — T11 对齐
  - 依赖：无

- [ ] Task 5.6: G03-BER 误码率与 Q 因子 — 通信指标达商业级
  - [ ] SubTask 5.6.1: 实现 `src/polaris/quantum/ber.py` Q 因子 + BER 高斯近似 + 眼图 + 蒙特卡洛
  - [ ] SubTask 5.6.2: 验收 — 4 工具对齐，超越实验性
  - 依赖：无

## Sprint 6：P5 多物理场（2028Q3）

- [ ] Task 6.1: H01-电光耦合与载流子输运 — DDM→电光效应→FDE 三场自洽
  - [ ] SubTask 6.1.1: 实现 `src/polaris/multiphysics/electro_optic.py` Poisson + Scharfetter-Gummel + Soref 等离子色散 + Pockels/Kerr
  - [ ] SubTask 6.1.2: 验收 — 5 工具对齐，VπL 闭环，文献 URL ≥5（Soref & Bennett 1987）
  - 依赖：Task 2.5（DDM）、Task 0.1（FDE）

- [ ] Task 6.2: H02-热光效应与热调谐 — Cocorullo 1999 二阶精度热光
  - [ ] SubTask 6.2.1: 实现 `src/polaris/multiphysics/thermo_optic.py` 傅里叶导热 + Cocorullo dn/dT + 热串扰矩阵
  - [ ] SubTask 6.2.2: 验收 — 4 工具对齐，超越线性近似
  - 依赖：Task 2.4（HEAT）

## Sprint 7：P6 数据 IO + 平台生态（2028Q4）

- [ ] Task 7.1: I01-网表解析与序列化 — YAML/JSON/SiEPIC 网表
  - [ ] SubTask 7.1.1: 实现 `src/polaris/io/netlist.py` DAG + Kahn 拓扑排序 + 子电路展开 + Hash 签名
  - [ ] SubTask 7.1.2: 验收 — 6 工具对齐
  - 依赖：无

- [ ] Task 7.2: I02-可视化与渲染 — 拥塞热力图 + 反馈闭环
  - [ ] SubTask 7.2.1: 实现 `src/polaris/io/viz.py` 仿射视图变换 + Marching Squares + Smith 圆图 + Poincaré 球
  - [ ] SubTask 7.2.2: 验收 — 9 工具对齐
  - 依赖：无

- [ ] Task 7.3: I03-GDS/OASIS 导出 — 双格式导出 + AI 闭环
  - [ ] SubTask 7.3.1: 实现 `src/polaris/io/gds_export.py` 贝塞尔离散 + Euler 螺线 + Sutherland-Hodgman + VarCode 压缩
  - [ ] SubTask 7.3.2: 验收 — 7 工具对齐
  - 依赖：Task 2.7（GDS 读写）

- [ ] Task 7.4: I04-SPICE 电路导出 — SPICE/Verilog-A 协同仿真
  - [ ] SubTask 7.4.1: 实现 `src/polaris/io/spice_export.py` RLCG 等效电路 + S→Y→Z + Verilog-A ddt + Newton-Raphson
  - [ ] SubTask 7.4.2: 验收 — 5 工具对齐
  - 依赖：无

- [ ] Task 7.5: J01-脚本 API 与平台集成 — Python API + 平台集成
  - [ ] SubTask 7.5.1: 实现 `src/polaris/platform/api.py` API 契约 + Kahn 拓扑 + 令牌桶限流 + LRU-Zipf 缓存
  - [ ] SubTask 7.5.2: 验收 — 10 工具对齐
  - 依赖：Task 7.1（网表）、Task 7.2（可视化）

- [ ] Task 7.6: J02-商业生态与教育文档 — 教育文档 + 开源生态
  - [ ] SubTask 7.6.1: 实现 `src/polaris/platform/education.py` 知识图谱 + TF-IDF + PageRank + IRT 评估
  - [ ] SubTask 7.6.2: 验收 — 6 工具对齐
  - 依赖：Task 7.3（GDS 导出流片闭环）

---

# Task Dependencies

## 关键路径依赖

- Task 0.1 (A04-FDE) → Task 1.1 (A05-FDFD)、Task 1.4 (A02-EME)、Task 2.1 (A03-BPM)、Task 2.2 (A06-2.5D-FDTD)、Task 2.3 (A09-FDTD)、Task 3.6 (F01-伴随)、Task 6.1 (H01-电光)
- Task 1.3 (C03-Redheffer) → Task 1.2 (A01-RCWA)、Task 1.4 (A02-EME)、Task 3.1 (C01-S 参数)
- Task 2.3 (A09-FDTD) → Task 2.2 (A06-2.5D-FDTD)、Task 3.6 (F01-伴随)
- Task 2.4 (A07-HEAT) → Task 6.2 (H02-热光)
- Task 2.5 (A08-DDM) → Task 6.1 (H01-电光)
- Task 2.6 (B02-DRC) → Task 2.7 (B01/B03/B04)、Task 3.5 (B05-GUI)、Task 4.10 (F01-DRC 感知)
- Task 3.1 (C01-S 参数) → Task 3.2 (C02-子网络)、Task 3.3 (C04-时域)、Task 3.4 (C05-频域)、Task 5.1 (F02-自动微分)
- Task 3.6 (F01-伴随 P1-2) → Task 4.10 (F01-伴随 P3-5)
- Task 4.1 (D01-GNN) + Task 4.2 (D03-PPO) + Task 4.3 (D04-奖励) → Task 4.4 (D05-AlphaChip)
- Task 4.6 (E01-A*) → Task 4.7 (E02-通道)、Task 4.8 (E03-多层)、Task 4.9 (E04-光电协同)
- Task 7.1 (I01-网表) + Task 7.2 (I02-可视化) → Task 7.5 (J01-脚本 API)
- Task 7.3 (I03-GDS 导出) → Task 7.6 (J02-商业生态)

## 可并行任务

- Sprint 1: Task 1.1 (A05-FDFD)、Task 1.2 (A01-RCWA)、Task 1.3 (C03-Redheffer) 可并行起步
- Sprint 2: Task 2.4 (A07-HEAT)、Task 2.6 (B02-DRC) 无相互依赖可并行
- Sprint 4: Task 4.1 (D01-GNN)、Task 4.2 (D03-PPO)、Task 4.5 (D02-CNN)、Task 4.6 (E01-A*) 无相互依赖可并行
- Sprint 5: Task 5.2 (F03-贝叶斯)、Task 5.3 (F04-梯度)、Task 5.4 (G01-HOM)、Task 5.5 (G02-Clements)、Task 5.6 (G03-BER) 无相互依赖可并行
- Sprint 7: Task 7.1 (I01-网表)、Task 7.2 (I02-可视化)、Task 7.4 (I04-SPICE) 无相互依赖可并行

---

# 验收汇总

| Sprint | 聚类数 | 关键 KPI | 里程碑 |
|--------|--------|---------|--------|
| Sprint 0 | 1 (A04) | neff 误差 ≤1e-4 | P0 底座完成 |
| Sprint 1 | 4 (A05/A01/A02/C03) | 光栅衍射 ≤0.5 dB, 能量守恒 ≤1e-3 | P0 频域求解器完成 |
| Sprint 2 | 7 (A03/A06/A09/A07/A08/B01-B04) | FDTD vs Lumerical ≤0.5 dB, DRC 18 类 | M1: P0 求解器完成, M2: MVP v1.0, M3: P1 版图 DRC |
| Sprint 3 | 6 (B05/C01-C05/F01-P1-2) | S 参数级联快 20× | M4: P2 仿真级联完成 |
| Sprint 4 | 10 (D01-D05/E01-E04/F01-P3-5) | TILOS 基准对齐, GDSII DRC 100% | M5: AlphaChip 对标, M6: 逆向设计平台 |
| Sprint 5 | 6 (F02-F04/G01-G03) | 7 工具对齐, atol=1e-4 | M7: 商业级 v2.0 |
| Sprint 6 | 2 (H01/H02) | VπL 闭环, 5 工具对齐 | 多物理场完成 |
| Sprint 7 | 6 (I01-I04/J01/J02) | 10 工具对齐 | M8: 全量交付 v3.0 (43 聚类 100%) |
