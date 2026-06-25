# Checklist — 三方库清单与商用许可分析

## 基线核查
- [x] 扫描 `src/polaris/` 全部 import，生成实际使用三方库基线清单（含使用文件位置）
- [x] 读取 `3dtool/wheels/MANIFEST.txt`，盘点已离线打包的库
- [x] 比对 src/ import 与 wheels/ 打包，识别差异（漏装/多装）

## 四档分类清单（INVENTORY.md）
- [x] 创建 `3dtool/INVENTORY.md` 框架，建立四档分类章节
- [x] "✅可直接商用"章节覆盖 ≥ 30 个库（许可+Py3.14+维护活跃均满足）
- [x] "⚠️许可受限"章节标注 GPL/AGPL/双重许可库（含 meep GPL 影响分析）
- [x] "🚫不可商用/待复刻"章节覆盖 tidy3d/SiPANN/lumerical/vpi 等
- [x] "❌缺失待实现"章节覆盖 ≥ 8 个求解器（RCWA/EME/BPM/HEAT/DDM/FDE/FDFD/2.5D-FDTD）
- [x] 每个库条目含字段：库名/版本/许可/商用状态/Py3.14状态/项目使用位置/来源URL/复刻决策
- [x] 可商用库排在文档前面（用户要求"可以直接商用的放在前面"）
- [x] 每个库的许可类型有 PyPI 或 GitHub 官方 URL 引用（规则 18 学术诚信）

## 求解器算法公式（ALGORITHMS.md）
- [x] 创建 `3dtool/ALGORITHMS.md` 框架，含 8 个求解器章节
- [x] RCWA 章节：傅里叶展开 + 本征模 + Redheffer 星积，含 Moharam 1995 / Li 1996 文献
- [x] EME 章节：纵向本征模展开 + 模式匹配 + S 矩阵级联，含 Lumerical/Photon Design 文献
- [x] BPM 章节：SVEA + ADI + 透明边界，含 Hadley 1992 文献
- [x] HEAT 章节：傅里叶导热 + 5 类边界 + 光-热/电-热耦合，含 T15 曼光 OFC 2026 文献
- [x] DDM 章节：Poisson + 连续性 + Scharfetter-Gummel，含 Scharfetter-Gummel 1969 文献
- [x] FDE 章节：Maxwell 本征值 + 有限元/有限差分 + 模式归一化
- [x] FDFD 章节：频域 Maxwell 离散 + 稀疏线性系统 + PML，含 Shin 1997 文献
- [x] 2.5D-FDTD 章节：FDTD+FDE 混合 + 模式分解注入
- [x] 每节含 LaTeX 公式（用 $...$ 表达）+ 伪代码 + 文献 URL
- [x] PoLaRIS 自研差异化设计标注【创新】并记录创新逻辑（规则 18）

## 规则与文档同步
- [x] `3dtool/README.md` 顶部新增清单索引，引用 INVENTORY.md 和 ALGORITHMS.md
- [x] `.trae/rules/project_rules.md` 规则 3.2 工具清单表新增"许可"和"商用状态"两列
- [x] 规则 4.1 复刻触发条件引用 INVENTORY.md 的"🚫不可商用"章节
      **已修复**：2026-06-25 在 project_rules.md 规则 4.1 末尾（第 256 行）追加"复刻候选清单：参见 INVENTORY.md 的'🚫不可商用/待复刻'章节（tidy3d/SiPANN/lumerical/vpi/CuPy）。当前已复刻：pyCopySiPANN"。
- [x] `3dtool/layout/README.md` 工具表新增"许可"列
- [x] `3dtool/simulation/README.md` 工具表新增"许可"列
- [x] `3dtool/ml/README.md` 工具表新增"许可"列
- [x] `3dtool/numeric/README.md` 工具表新增"许可"列
- [x] `3dtool/viz/README.md` 工具表新增"许可"列
- [x] `3dtool/serialization/README.md` 工具表新增"许可"列
- [x] `操作记录.md` 追加轮次 R-2026-06-25-LIB-INVENTORY 完整记录

## 网络调研真实性（规则 18）
- [x] 每个库的许可类型经 PyPI/GitHub 官方页面核实，无编造
- [x] 每个求解器公式经 arXiv/IEEE/官方文档核实，无编造
- [x] 商业工具（Lumerical/Tidy3D/曼光/SimWorks）的求解器实现经官方文档核实
- [x] 所有文献引用含标题/作者/年份/URL

## GPU 不参与一致性（规则 26）
- [x] CuPy/CUDA/torch.cuda 等 GPU 库在 INVENTORY.md 标记🚫不参与
- [x] ALGORITHMS.md 中求解器公式不包含 GPU 加速实现（仅 CPU 算法）
- [x] 复刻决策不新增 GPU 相关任务

## 提交与合并
- [x] git 提交消息遵循 Conventional Commits（docs 类型）
- [x] dev 分支提交
- [x] 合并到 main 分支
- [x] 推送 main 到远端
- [x] dev 与 main 同步

## 质量门禁
- [x] INVENTORY.md 覆盖 ≥ 50 个三方库
- [x] ALGORITHMS.md 覆盖 ≥ 8 个求解器
- [x] 无 fall-back（规则 14）：调研失败须告警，禁止编造数据
- [x] 无 TODO/FIXME 残留
- [x] 文档行数合理（INVENTORY.md 预计 400-600 行，ALGORITHMS.md 预计 600-900 行）
