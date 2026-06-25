## A09 — FDTD 时域有限差分（器件级）

> 生成时间：202# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3d# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Y# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polar# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 Num# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 M# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

#### A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \v# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} +# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\math# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$ 处理。

### 2.2 色# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$ 处理。

### 2.2 色散材料（辅助微分方程 ADE）

Drude-Lorentz 色散介质极化# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$ 处理。

### 2.2 色散材料（辅助微分方程 ADE）

Drude-Lorentz 色散介质极化密度 $\mathbf{P}$ 满足# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$ 处理。

### 2.2 色散材料（辅助微分方程 ADE）

Drude-Lorentz 色散介质极化密度 $\mathbf{P}$ 满足二阶 ODE：

$$\frac{\partial^2 \mathbf{P}}{\partial# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$ 处理。

### 2.2 色散材料（辅助微分方程 ADE）

Drude-Lorentz 色散介质极化密度 $\mathbf{P}$ 满足二阶 ODE：

$$\frac{\partial^2 \mathbf{P}}{\partial t^2} + \gamma \frac{\# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$ 处理。

### 2.2 色散材料（辅助微分方程 ADE）

Drude-Lorentz 色散介质极化密度 $\mathbf{P}$ 满足二阶 ODE：

$$\frac{\partial^2 \mathbf{P}}{\partial t^2} + \gamma \frac{\partial \mathbf{P}}{\partial t# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$ 处理。

### 2.2 色散材料（辅助微分方程 ADE）

Drude-Lorentz 色散介质极化密度 $\mathbf{P}$ 满足二阶 ODE：

$$\frac{\partial^2 \mathbf{P}}{\partial t^2} + \gamma \frac{\partial \mathbf{P}}{\partial t} + \omega_0^2 \mathbf{P} = \varepsilon_0 \omega_p^2 \mathbf{# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$ 处理。

### 2.2 色散材料（辅助微分方程 ADE）

Drude-Lorentz 色散介质极化密度 $\mathbf{P}$ 满足二阶 ODE：

$$\frac{\partial^2 \mathbf{P}}{\partial t^2} + \gamma \frac{\partial \mathbf{P}}{\partial t} + \omega_0^2 \mathbf{P} = \varepsilon_0 \omega_p^2 \mathbf{E}$$

其中 $\omega_0$# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$ 处理。

### 2.2 色散材料（辅助微分方程 ADE）

Drude-Lorentz 色散介质极化密度 $\mathbf{P}$ 满足二阶 ODE：

$$\frac{\partial^2 \mathbf{P}}{\partial t^2} + \gamma \frac{\partial \mathbf{P}}{\partial t} + \omega_0^2 \mathbf{P} = \varepsilon_0 \omega_p^2 \mathbf{E}$$

其中 $\omega_0$ 为共振频率，$\gamma$ 为阻尼# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$ 处理。

### 2.2 色散材料（辅助微分方程 ADE）

Drude-Lorentz 色散介质极化密度 $\mathbf{P}$ 满足二阶 ODE：

$$\frac{\partial^2 \mathbf{P}}{\partial t^2} + \gamma \frac{\partial \mathbf{P}}{\partial t} + \omega_0^2 \mathbf{P} = \varepsilon_0 \omega_p^2 \mathbf{E}$$

其中 $\omega_0$ 为共振频率，$\gamma$ 为阻尼率，$\omega_p$ 为等离子频率。# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$ 处理。

### 2.2 色散材料（辅助微分方程 ADE）

Drude-Lorentz 色散介质极化密度 $\mathbf{P}$ 满足二阶 ODE：

$$\frac{\partial^2 \mathbf{P}}{\partial t^2} + \gamma \frac{\partial \mathbf{P}}{\partial t} + \omega_0^2 \mathbf{P} = \varepsilon_0 \omega_p^2 \mathbf{E}$$

其中 $\omega_0$ 为共振频率，$\gamma$ 为阻尼率，$\omega_p$ 为等离子频率。$\mathbf{D}=\varepsilon_0\varepsilon_\infty\mathbf{E}+\mathbf{P}$，代入 Maxwell 旋度方程得 ADE-FDTD 更新格式（Lumerical M# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$ 处理。

### 2.2 色散材料（辅助微分方程 ADE）

Drude-Lorentz 色散介质极化密度 $\mathbf{P}$ 满足二阶 ODE：

$$\frac{\partial^2 \mathbf{P}}{\partial t^2} + \gamma \frac{\partial \mathbf{P}}{\partial t} + \omega_0^2 \mathbf{P} = \varepsilon_0 \omega_p^2 \mathbf{E}$$

其中 $\omega_0$ 为共振频率，$\gamma$ 为阻尼率，$\omega_p$ 为等离子频率。$\mathbf{D}=\varepsilon_0\varepsilon_\infty\mathbf{E}+\mathbf{P}$，代入 Maxwell 旋度方程得 ADE-FDTD 更新格式（Lumerical MCM、Tidy3D PoleResidue 共# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$ 处理。

### 2.2 色散材料（辅助微分方程 ADE）

Drude-Lorentz 色散介质极化密度 $\mathbf{P}$ 满足二阶 ODE：

$$\frac{\partial^2 \mathbf{P}}{\partial t^2} + \gamma \frac{\partial \mathbf{P}}{\partial t} + \omega_0^2 \mathbf{P} = \varepsilon_0 \omega_p^2 \mathbf{E}$$

其中 $\omega_0$ 为共振频率，$\gamma$ 为阻尼率，$\omega_p$ 为等离子频率。$\mathbf{D}=\varepsilon_0\varepsilon_\infty\mathbf{E}+\mathbf{P}$，代入 Maxwell 旋度方程得 ADE-FDTD 更新格式（Lumerical MCM、Tidy3D PoleResidue 共同方案）。多系数材料 MCM 通过加# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$ 处理。

### 2.2 色散材料（辅助微分方程 ADE）

Drude-Lorentz 色散介质极化密度 $\mathbf{P}$ 满足二阶 ODE：

$$\frac{\partial^2 \mathbf{P}}{\partial t^2} + \gamma \frac{\partial \mathbf{P}}{\partial t} + \omega_0^2 \mathbf{P} = \varepsilon_0 \omega_p^2 \mathbf{E}$$

其中 $\omega_0$ 为共振频率，$\gamma$ 为阻尼率，$\omega_p$ 为等离子频率。$\mathbf{D}=\varepsilon_0\varepsilon_\infty\mathbf{E}+\mathbf{P}$，代入 Maxwell 旋度方程得 ADE-FDTD 更新格式（Lumerical MCM、Tidy3D PoleResidue 共同方案）。多系数材料 MCM 通过加和多个 Lorentz 极点拟合实测# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$ 处理。

### 2.2 色散材料（辅助微分方程 ADE）

Drude-Lorentz 色散介质极化密度 $\mathbf{P}$ 满足二阶 ODE：

$$\frac{\partial^2 \mathbf{P}}{\partial t^2} + \gamma \frac{\partial \mathbf{P}}{\partial t} + \omega_0^2 \mathbf{P} = \varepsilon_0 \omega_p^2 \mathbf{E}$$

其中 $\omega_0$ 为共振频率，$\gamma$ 为阻尼率，$\omega_p$ 为等离子频率。$\mathbf{D}=\varepsilon_0\varepsilon_\infty\mathbf{E}+\mathbf{P}$，代入 Maxwell 旋度方程得 ADE-FDTD 更新格式（Lumerical MCM、Tidy3D PoleResidue 共同方案）。多系数材料 MCM 通过加和多个 Lorentz 极点拟合实测 $n(\omega)$ 数据。

### 2# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$ 处理。

### 2.2 色散材料（辅助微分方程 ADE）

Drude-Lorentz 色散介质极化密度 $\mathbf{P}$ 满足二阶 ODE：

$$\frac{\partial^2 \mathbf{P}}{\partial t^2} + \gamma \frac{\partial \mathbf{P}}{\partial t} + \omega_0^2 \mathbf{P} = \varepsilon_0 \omega_p^2 \mathbf{E}$$

其中 $\omega_0$ 为共振频率，$\gamma$ 为阻尼率，$\omega_p$ 为等离子频率。$\mathbf{D}=\varepsilon_0\varepsilon_\infty\mathbf{E}+\mathbf{P}$，代入 Maxwell 旋度方程得 ADE-FDTD 更新格式（Lumerical MCM、Tidy3D PoleResidue 共同方案）。多系数材料 MCM 通过加和多个 Lorentz 极点拟合实测 $n(\omega)$ 数据。

### 2.3 非线性（Kerr +# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$ 处理。

### 2.2 色散材料（辅助微分方程 ADE）

Drude-Lorentz 色散介质极化密度 $\mathbf{P}$ 满足二阶 ODE：

$$\frac{\partial^2 \mathbf{P}}{\partial t^2} + \gamma \frac{\partial \mathbf{P}}{\partial t} + \omega_0^2 \mathbf{P} = \varepsilon_0 \omega_p^2 \mathbf{E}$$

其中 $\omega_0$ 为共振频率，$\gamma$ 为阻尼率，$\omega_p$ 为等离子频率。$\mathbf{D}=\varepsilon_0\varepsilon_\infty\mathbf{E}+\mathbf{P}$，代入 Maxwell 旋度方程得 ADE-FDTD 更新格式（Lumerical MCM、Tidy3D PoleResidue 共同方案）。多系数材料 MCM 通过加和多个 Lorentz 极点拟合实测 $n(\omega)$ 数据。

### 2.3 非线性（Kerr + 拉曼）

三阶非线性 $\mathbf{# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$ 处理。

### 2.2 色散材料（辅助微分方程 ADE）

Drude-Lorentz 色散介质极化密度 $\mathbf{P}$ 满足二阶 ODE：

$$\frac{\partial^2 \mathbf{P}}{\partial t^2} + \gamma \frac{\partial \mathbf{P}}{\partial t} + \omega_0^2 \mathbf{P} = \varepsilon_0 \omega_p^2 \mathbf{E}$$

其中 $\omega_0$ 为共振频率，$\gamma$ 为阻尼率，$\omega_p$ 为等离子频率。$\mathbf{D}=\varepsilon_0\varepsilon_\infty\mathbf{E}+\mathbf{P}$，代入 Maxwell 旋度方程得 ADE-FDTD 更新格式（Lumerical MCM、Tidy3D PoleResidue 共同方案）。多系数材料 MCM 通过加和多个 Lorentz 极点拟合实测 $n(\omega)$ 数据。

### 2.3 非线性（Kerr + 拉曼）

三阶非线性 $\mathbf{P}_{NL}=\varepsilon_0\chi^{(3)}|\mathbf{# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$ 处理。

### 2.2 色散材料（辅助微分方程 ADE）

Drude-Lorentz 色散介质极化密度 $\mathbf{P}$ 满足二阶 ODE：

$$\frac{\partial^2 \mathbf{P}}{\partial t^2} + \gamma \frac{\partial \mathbf{P}}{\partial t} + \omega_0^2 \mathbf{P} = \varepsilon_0 \omega_p^2 \mathbf{E}$$

其中 $\omega_0$ 为共振频率，$\gamma$ 为阻尼率，$\omega_p$ 为等离子频率。$\mathbf{D}=\varepsilon_0\varepsilon_\infty\mathbf{E}+\mathbf{P}$，代入 Maxwell 旋度方程得 ADE-FDTD 更新格式（Lumerical MCM、Tidy3D PoleResidue 共同方案）。多系数材料 MCM 通过加和多个 Lorentz 极点拟合实测 $n(\omega)$ 数据。

### 2.3 非线性（Kerr + 拉曼）

三阶非线性 $\mathbf{P}_{NL}=\varepsilon_0\chi^{(3)}|\mathbf{E}|^2\mathbf{E}$（瞬时 Kerr）+ 卷积拉曼项# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$ 处理。

### 2.2 色散材料（辅助微分方程 ADE）

Drude-Lorentz 色散介质极化密度 $\mathbf{P}$ 满足二阶 ODE：

$$\frac{\partial^2 \mathbf{P}}{\partial t^2} + \gamma \frac{\partial \mathbf{P}}{\partial t} + \omega_0^2 \mathbf{P} = \varepsilon_0 \omega_p^2 \mathbf{E}$$

其中 $\omega_0$ 为共振频率，$\gamma$ 为阻尼率，$\omega_p$ 为等离子频率。$\mathbf{D}=\varepsilon_0\varepsilon_\infty\mathbf{E}+\mathbf{P}$，代入 Maxwell 旋度方程得 ADE-FDTD 更新格式（Lumerical MCM、Tidy3D PoleResidue 共同方案）。多系数材料 MCM 通过加和多个 Lorentz 极点拟合实测 $n(\omega)$ 数据。

### 2.3 非线性（Kerr + 拉曼）

三阶非线性 $\mathbf{P}_{NL}=\varepsilon_0\chi^{(3)}|\mathbf{E}|^2\mathbf{E}$（瞬时 Kerr）+ 卷积拉曼项，ADE 法处理。光子芯片中典型# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$ 处理。

### 2.2 色散材料（辅助微分方程 ADE）

Drude-Lorentz 色散介质极化密度 $\mathbf{P}$ 满足二阶 ODE：

$$\frac{\partial^2 \mathbf{P}}{\partial t^2} + \gamma \frac{\partial \mathbf{P}}{\partial t} + \omega_0^2 \mathbf{P} = \varepsilon_0 \omega_p^2 \mathbf{E}$$

其中 $\omega_0$ 为共振频率，$\gamma$ 为阻尼率，$\omega_p$ 为等离子频率。$\mathbf{D}=\varepsilon_0\varepsilon_\infty\mathbf{E}+\mathbf{P}$，代入 Maxwell 旋度方程得 ADE-FDTD 更新格式（Lumerical MCM、Tidy3D PoleResidue 共同方案）。多系数材料 MCM 通过加和多个 Lorentz 极点拟合实测 $n(\omega)$ 数据。

### 2.3 非线性（Kerr + 拉曼）

三阶非线性 $\mathbf{P}_{NL}=\varepsilon_0\chi^{(3)}|\mathbf{E}|^2\mathbf{E}$（瞬时 Kerr）+ 卷积拉曼项，ADE 法处理。光子芯片中典型应用为 SiN 微环的克尔自相位调制、LNOI 的 $\chi^{(2)}$ 二次谐波。

---

### A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$ 处理。

### 2.2 色散材料（辅助微分方程 ADE）

Drude-Lorentz 色散介质极化密度 $\mathbf{P}$ 满足二阶 ODE：

$$\frac{\partial^2 \mathbf{P}}{\partial t^2} + \gamma \frac{\partial \mathbf{P}}{\partial t} + \omega_0^2 \mathbf{P} = \varepsilon_0 \omega_p^2 \mathbf{E}$$

其中 $\omega_0$ 为共振频率，$\gamma$ 为阻尼率，$\omega_p$ 为等离子频率。$\mathbf{D}=\varepsilon_0\varepsilon_\infty\mathbf{E}+\mathbf{P}$，代入 Maxwell 旋度方程得 ADE-FDTD 更新格式（Lumerical MCM、Tidy3D PoleResidue 共同方案）。多系数材料 MCM 通过加和多个 Lorentz 极点拟合实测 $n(\omega)$ 数据。

### 2.3 非线性（Kerr + 拉曼）

三阶非线性 $\mathbf{P}_{NL}=\varepsilon_0\chi^{(3)}|\mathbf{E}|^2\mathbf{E}$（瞬时 Kerr）+ 卷积拉曼项，ADE 法处理。光子芯片中典型应用为 SiN 微环的克尔自相位调制、LNOI 的 $\chi^{(2)}$ 二次谐波。

---

## 3. Yee 网格离散化方案

### 3.1 Yee 196# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$ 处理。

### 2.2 色散材料（辅助微分方程 ADE）

Drude-Lorentz 色散介质极化密度 $\mathbf{P}$ 满足二阶 ODE：

$$\frac{\partial^2 \mathbf{P}}{\partial t^2} + \gamma \frac{\partial \mathbf{P}}{\partial t} + \omega_0^2 \mathbf{P} = \varepsilon_0 \omega_p^2 \mathbf{E}$$

其中 $\omega_0$ 为共振频率，$\gamma$ 为阻尼率，$\omega_p$ 为等离子频率。$\mathbf{D}=\varepsilon_0\varepsilon_\infty\mathbf{E}+\mathbf{P}$，代入 Maxwell 旋度方程得 ADE-FDTD 更新格式（Lumerical MCM、Tidy3D PoleResidue 共同方案）。多系数材料 MCM 通过加和多个 Lorentz 极点拟合实测 $n(\omega)$ 数据。

### 2.3 非线性（Kerr + 拉曼）

三阶非线性 $\mathbf{P}_{NL}=\varepsilon_0\chi^{(3)}|\mathbf{E}|^2\mathbf{E}$（瞬时 Kerr）+ 卷积拉曼项，ADE 法处理。光子芯片中典型应用为 SiN 微环的克尔自相位调制、LNOI 的 $\chi^{(2)}$ 二次谐波。

---

## 3. Yee 网格离散化方案

### 3.1 Yee 1966 网格布局

3D Yee# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$ 处理。

### 2.2 色散材料（辅助微分方程 ADE）

Drude-Lorentz 色散介质极化密度 $\mathbf{P}$ 满足二阶 ODE：

$$\frac{\partial^2 \mathbf{P}}{\partial t^2} + \gamma \frac{\partial \mathbf{P}}{\partial t} + \omega_0^2 \mathbf{P} = \varepsilon_0 \omega_p^2 \mathbf{E}$$

其中 $\omega_0$ 为共振频率，$\gamma$ 为阻尼率，$\omega_p$ 为等离子频率。$\mathbf{D}=\varepsilon_0\varepsilon_\infty\mathbf{E}+\mathbf{P}$，代入 Maxwell 旋度方程得 ADE-FDTD 更新格式（Lumerical MCM、Tidy3D PoleResidue 共同方案）。多系数材料 MCM 通过加和多个 Lorentz 极点拟合实测 $n(\omega)$ 数据。

### 2.3 非线性（Kerr + 拉曼）

三阶非线性 $\mathbf{P}_{NL}=\varepsilon_0\chi^{(3)}|\mathbf{E}|^2\mathbf{E}$（瞬时 Kerr）+ 卷积拉曼项，ADE 法处理。光子芯片中典型应用为 SiN 微环的克尔自相位调制、LNOI 的 $\chi^{(2)}$ 二次谐波。

---

## 3. Yee 网格离散化方案

### 3.1 Yee 1966 网格布局

3D Yee 单元中：电场分量 $E_x,E_y,E_z$ 位于棱中点，磁场分量 $H_x,H_y,H_z$ 位于面中心，空间半步错位。该布局使每个旋度运算的中心差分天然落在被求场位置，二阶精度 $O(\Delta h^2)$，且离散 Gauss 定律 $\nabla_h\# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$ 处理。

### 2.2 色散材料（辅助微分方程 ADE）

Drude-Lorentz 色散介质极化密度 $\mathbf{P}$ 满足二阶 ODE：

$$\frac{\partial^2 \mathbf{P}}{\partial t^2} + \gamma \frac{\partial \mathbf{P}}{\partial t} + \omega_0^2 \mathbf{P} = \varepsilon_0 \omega_p^2 \mathbf{E}$$

其中 $\omega_0$ 为共振频率，$\gamma$ 为阻尼率，$\omega_p$ 为等离子频率。$\mathbf{D}=\varepsilon_0\varepsilon_\infty\mathbf{E}+\mathbf{P}$，代入 Maxwell 旋度方程得 ADE-FDTD 更新格式（Lumerical MCM、Tidy3D PoleResidue 共同方案）。多系数材料 MCM 通过加和多个 Lorentz 极点拟合实测 $n(\omega)$ 数据。

### 2.3 非线性（Kerr + 拉曼）

三阶非线性 $\mathbf{P}_{NL}=\varepsilon_0\chi^{(3)}|\mathbf{E}|^2\mathbf{E}$（瞬时 Kerr）+ 卷积拉曼项，ADE 法处理。光子芯片中典型应用为 SiN 微环的克尔自相位调制、LNOI 的 $\chi^{(2)}$ 二次谐波。

---

## 3. Yee 网格离散化方案

### 3.1 Yee 1966 网格布局

3D Yee 单元中：电场分量 $E_x,E_y,E_z$ 位于棱中点，磁场分量 $H_x,H_y,H_z$ 位于面中心，空间半步错位。该布局使每个旋度运算的中心差分天然落在被求场位置，二阶精度 $O(\Delta h^2)$，且离散 Gauss 定律 $\nabla_h\cdot(\nabla_h\times\cdot)\equiv 0$ 自动满足（避免非物理电荷积累）。Yee 网格是# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$ 处理。

### 2.2 色散材料（辅助微分方程 ADE）

Drude-Lorentz 色散介质极化密度 $\mathbf{P}$ 满足二阶 ODE：

$$\frac{\partial^2 \mathbf{P}}{\partial t^2} + \gamma \frac{\partial \mathbf{P}}{\partial t} + \omega_0^2 \mathbf{P} = \varepsilon_0 \omega_p^2 \mathbf{E}$$

其中 $\omega_0$ 为共振频率，$\gamma$ 为阻尼率，$\omega_p$ 为等离子频率。$\mathbf{D}=\varepsilon_0\varepsilon_\infty\mathbf{E}+\mathbf{P}$，代入 Maxwell 旋度方程得 ADE-FDTD 更新格式（Lumerical MCM、Tidy3D PoleResidue 共同方案）。多系数材料 MCM 通过加和多个 Lorentz 极点拟合实测 $n(\omega)$ 数据。

### 2.3 非线性（Kerr + 拉曼）

三阶非线性 $\mathbf{P}_{NL}=\varepsilon_0\chi^{(3)}|\mathbf{E}|^2\mathbf{E}$（瞬时 Kerr）+ 卷积拉曼项，ADE 法处理。光子芯片中典型应用为 SiN 微环的克尔自相位调制、LNOI 的 $\chi^{(2)}$ 二次谐波。

---

## 3. Yee 网格离散化方案

### 3.1 Yee 1966 网格布局

3D Yee 单元中：电场分量 $E_x,E_y,E_z$ 位于棱中点，磁场分量 $H_x,H_y,H_z$ 位于面中心，空间半步错位。该布局使每个旋度运算的中心差分天然落在被求场位置，二阶精度 $O(\Delta h^2)$，且离散 Gauss 定律 $\nabla_h\cdot(\nabla_h\times\cdot)\equiv 0$ 自动满足（避免非物理电荷积累）。Yee 网格是 FDE/FDFD/FDTD/2.# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$ 处理。

### 2.2 色散材料（辅助微分方程 ADE）

Drude-Lorentz 色散介质极化密度 $\mathbf{P}$ 满足二阶 ODE：

$$\frac{\partial^2 \mathbf{P}}{\partial t^2} + \gamma \frac{\partial \mathbf{P}}{\partial t} + \omega_0^2 \mathbf{P} = \varepsilon_0 \omega_p^2 \mathbf{E}$$

其中 $\omega_0$ 为共振频率，$\gamma$ 为阻尼率，$\omega_p$ 为等离子频率。$\mathbf{D}=\varepsilon_0\varepsilon_\infty\mathbf{E}+\mathbf{P}$，代入 Maxwell 旋度方程得 ADE-FDTD 更新格式（Lumerical MCM、Tidy3D PoleResidue 共同方案）。多系数材料 MCM 通过加和多个 Lorentz 极点拟合实测 $n(\omega)$ 数据。

### 2.3 非线性（Kerr + 拉曼）

三阶非线性 $\mathbf{P}_{NL}=\varepsilon_0\chi^{(3)}|\mathbf{E}|^2\mathbf{E}$（瞬时 Kerr）+ 卷积拉曼项，ADE 法处理。光子芯片中典型应用为 SiN 微环的克尔自相位调制、LNOI 的 $\chi^{(2)}$ 二次谐波。

---

## 3. Yee 网格离散化方案

### 3.1 Yee 1966 网格布局

3D Yee 单元中：电场分量 $E_x,E_y,E_z$ 位于棱中点，磁场分量 $H_x,H_y,H_z$ 位于面中心，空间半步错位。该布局使每个旋度运算的中心差分天然落在被求场位置，二阶精度 $O(\Delta h^2)$，且离散 Gauss 定律 $\nabla_h\cdot(\nabla_h\times\cdot)\equiv 0$ 自动满足（避免非物理电荷积累）。Yee 网格是 FDE/FDFD/FDTD/2.5D-FDTD 共同基础（ALGORITHMS.md 附录 C）。

### 3.# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$ 处理。

### 2.2 色散材料（辅助微分方程 ADE）

Drude-Lorentz 色散介质极化密度 $\mathbf{P}$ 满足二阶 ODE：

$$\frac{\partial^2 \mathbf{P}}{\partial t^2} + \gamma \frac{\partial \mathbf{P}}{\partial t} + \omega_0^2 \mathbf{P} = \varepsilon_0 \omega_p^2 \mathbf{E}$$

其中 $\omega_0$ 为共振频率，$\gamma$ 为阻尼率，$\omega_p$ 为等离子频率。$\mathbf{D}=\varepsilon_0\varepsilon_\infty\mathbf{E}+\mathbf{P}$，代入 Maxwell 旋度方程得 ADE-FDTD 更新格式（Lumerical MCM、Tidy3D PoleResidue 共同方案）。多系数材料 MCM 通过加和多个 Lorentz 极点拟合实测 $n(\omega)$ 数据。

### 2.3 非线性（Kerr + 拉曼）

三阶非线性 $\mathbf{P}_{NL}=\varepsilon_0\chi^{(3)}|\mathbf{E}|^2\mathbf{E}$（瞬时 Kerr）+ 卷积拉曼项，ADE 法处理。光子芯片中典型应用为 SiN 微环的克尔自相位调制、LNOI 的 $\chi^{(2)}$ 二次谐波。

---

## 3. Yee 网格离散化方案

### 3.1 Yee 1966 网格布局

3D Yee 单元中：电场分量 $E_x,E_y,E_z$ 位于棱中点，磁场分量 $H_x,H_y,H_z$ 位于面中心，空间半步错位。该布局使每个旋度运算的中心差分天然落在被求场位置，二阶精度 $O(\Delta h^2)$，且离散 Gauss 定律 $\nabla_h\cdot(\nabla_h\times\cdot)\equiv 0$ 自动满足（避免非物理电荷积累）。Yee 网格是 FDE/FDFD/FDTD/2.5D-FDTD 共同基础（ALGORITHMS.md 附录 C）。

### 3.2 E/H leapfrog 时间推进

时间半# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$ 处理。

### 2.2 色散材料（辅助微分方程 ADE）

Drude-Lorentz 色散介质极化密度 $\mathbf{P}$ 满足二阶 ODE：

$$\frac{\partial^2 \mathbf{P}}{\partial t^2} + \gamma \frac{\partial \mathbf{P}}{\partial t} + \omega_0^2 \mathbf{P} = \varepsilon_0 \omega_p^2 \mathbf{E}$$

其中 $\omega_0$ 为共振频率，$\gamma$ 为阻尼率，$\omega_p$ 为等离子频率。$\mathbf{D}=\varepsilon_0\varepsilon_\infty\mathbf{E}+\mathbf{P}$，代入 Maxwell 旋度方程得 ADE-FDTD 更新格式（Lumerical MCM、Tidy3D PoleResidue 共同方案）。多系数材料 MCM 通过加和多个 Lorentz 极点拟合实测 $n(\omega)$ 数据。

### 2.3 非线性（Kerr + 拉曼）

三阶非线性 $\mathbf{P}_{NL}=\varepsilon_0\chi^{(3)}|\mathbf{E}|^2\mathbf{E}$（瞬时 Kerr）+ 卷积拉曼项，ADE 法处理。光子芯片中典型应用为 SiN 微环的克尔自相位调制、LNOI 的 $\chi^{(2)}$ 二次谐波。

---

## 3. Yee 网格离散化方案

### 3.1 Yee 1966 网格布局

3D Yee 单元中：电场分量 $E_x,E_y,E_z$ 位于棱中点，磁场分量 $H_x,H_y,H_z$ 位于面中心，空间半步错位。该布局使每个旋度运算的中心差分天然落在被求场位置，二阶精度 $O(\Delta h^2)$，且离散 Gauss 定律 $\nabla_h\cdot(\nabla_h\times\cdot)\equiv 0$ 自动满足（避免非物理电荷积累）。Yee 网格是 FDE/FDFD/FDTD/2.5D-FDTD 共同基础（ALGORITHMS.md 附录 C）。

### 3.2 E/H leapfrog 时间推进

时间半步错位，磁场在 $n+1# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$ 处理。

### 2.2 色散材料（辅助微分方程 ADE）

Drude-Lorentz 色散介质极化密度 $\mathbf{P}$ 满足二阶 ODE：

$$\frac{\partial^2 \mathbf{P}}{\partial t^2} + \gamma \frac{\partial \mathbf{P}}{\partial t} + \omega_0^2 \mathbf{P} = \varepsilon_0 \omega_p^2 \mathbf{E}$$

其中 $\omega_0$ 为共振频率，$\gamma$ 为阻尼率，$\omega_p$ 为等离子频率。$\mathbf{D}=\varepsilon_0\varepsilon_\infty\mathbf{E}+\mathbf{P}$，代入 Maxwell 旋度方程得 ADE-FDTD 更新格式（Lumerical MCM、Tidy3D PoleResidue 共同方案）。多系数材料 MCM 通过加和多个 Lorentz 极点拟合实测 $n(\omega)$ 数据。

### 2.3 非线性（Kerr + 拉曼）

三阶非线性 $\mathbf{P}_{NL}=\varepsilon_0\chi^{(3)}|\mathbf{E}|^2\mathbf{E}$（瞬时 Kerr）+ 卷积拉曼项，ADE 法处理。光子芯片中典型应用为 SiN 微环的克尔自相位调制、LNOI 的 $\chi^{(2)}$ 二次谐波。

---

## 3. Yee 网格离散化方案

### 3.1 Yee 1966 网格布局

3D Yee 单元中：电场分量 $E_x,E_y,E_z$ 位于棱中点，磁场分量 $H_x,H_y,H_z$ 位于面中心，空间半步错位。该布局使每个旋度运算的中心差分天然落在被求场位置，二阶精度 $O(\Delta h^2)$，且离散 Gauss 定律 $\nabla_h\cdot(\nabla_h\times\cdot)\equiv 0$ 自动满足（避免非物理电荷积累）。Yee 网格是 FDE/FDFD/FDTD/2.5D-FDTD 共同基础（ALGORITHMS.md 附录 C）。

### 3.2 E/H leapfrog 时间推进

时间半步错位，磁场在 $n+1/2$ 时刻更新，电场在 $n+1$ 时刻更新。以# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$ 处理。

### 2.2 色散材料（辅助微分方程 ADE）

Drude-Lorentz 色散介质极化密度 $\mathbf{P}$ 满足二阶 ODE：

$$\frac{\partial^2 \mathbf{P}}{\partial t^2} + \gamma \frac{\partial \mathbf{P}}{\partial t} + \omega_0^2 \mathbf{P} = \varepsilon_0 \omega_p^2 \mathbf{E}$$

其中 $\omega_0$ 为共振频率，$\gamma$ 为阻尼率，$\omega_p$ 为等离子频率。$\mathbf{D}=\varepsilon_0\varepsilon_\infty\mathbf{E}+\mathbf{P}$，代入 Maxwell 旋度方程得 ADE-FDTD 更新格式（Lumerical MCM、Tidy3D PoleResidue 共同方案）。多系数材料 MCM 通过加和多个 Lorentz 极点拟合实测 $n(\omega)$ 数据。

### 2.3 非线性（Kerr + 拉曼）

三阶非线性 $\mathbf{P}_{NL}=\varepsilon_0\chi^{(3)}|\mathbf{E}|^2\mathbf{E}$（瞬时 Kerr）+ 卷积拉曼项，ADE 法处理。光子芯片中典型应用为 SiN 微环的克尔自相位调制、LNOI 的 $\chi^{(2)}$ 二次谐波。

---

## 3. Yee 网格离散化方案

### 3.1 Yee 1966 网格布局

3D Yee 单元中：电场分量 $E_x,E_y,E_z$ 位于棱中点，磁场分量 $H_x,H_y,H_z$ 位于面中心，空间半步错位。该布局使每个旋度运算的中心差分天然落在被求场位置，二阶精度 $O(\Delta h^2)$，且离散 Gauss 定律 $\nabla_h\cdot(\nabla_h\times\cdot)\equiv 0$ 自动满足（避免非物理电荷积累）。Yee 网格是 FDE/FDFD/FDTD/2.5D-FDTD 共同基础（ALGORITHMS.md 附录 C）。

### 3.2 E/H leapfrog 时间推进

时间半步错位，磁场在 $n+1/2$ 时刻更新，电场在 $n+1$ 时刻更新。以 $E_z$（TEz 2D# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$ 处理。

### 2.2 色散材料（辅助微分方程 ADE）

Drude-Lorentz 色散介质极化密度 $\mathbf{P}$ 满足二阶 ODE：

$$\frac{\partial^2 \mathbf{P}}{\partial t^2} + \gamma \frac{\partial \mathbf{P}}{\partial t} + \omega_0^2 \mathbf{P} = \varepsilon_0 \omega_p^2 \mathbf{E}$$

其中 $\omega_0$ 为共振频率，$\gamma$ 为阻尼率，$\omega_p$ 为等离子频率。$\mathbf{D}=\varepsilon_0\varepsilon_\infty\mathbf{E}+\mathbf{P}$，代入 Maxwell 旋度方程得 ADE-FDTD 更新格式（Lumerical MCM、Tidy3D PoleResidue 共同方案）。多系数材料 MCM 通过加和多个 Lorentz 极点拟合实测 $n(\omega)$ 数据。

### 2.3 非线性（Kerr + 拉曼）

三阶非线性 $\mathbf{P}_{NL}=\varepsilon_0\chi^{(3)}|\mathbf{E}|^2\mathbf{E}$（瞬时 Kerr）+ 卷积拉曼项，ADE 法处理。光子芯片中典型应用为 SiN 微环的克尔自相位调制、LNOI 的 $\chi^{(2)}$ 二次谐波。

---

## 3. Yee 网格离散化方案

### 3.1 Yee 1966 网格布局

3D Yee 单元中：电场分量 $E_x,E_y,E_z$ 位于棱中点，磁场分量 $H_x,H_y,H_z$ 位于面中心，空间半步错位。该布局使每个旋度运算的中心差分天然落在被求场位置，二阶精度 $O(\Delta h^2)$，且离散 Gauss 定律 $\nabla_h\cdot(\nabla_h\times\cdot)\equiv 0$ 自动满足（避免非物理电荷积累）。Yee 网格是 FDE/FDFD/FDTD/2.5D-FDTD 共同基础（ALGORITHMS.md 附录 C）。

### 3.2 E/H leapfrog 时间推进

时间半步错位，磁场在 $n+1/2$ 时刻更新，电场在 $n+1$ 时刻更新。以 $E_z$（TEz 2D）为例：

$$H_x^{n+1# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$ 处理。

### 2.2 色散材料（辅助微分方程 ADE）

Drude-Lorentz 色散介质极化密度 $\mathbf{P}$ 满足二阶 ODE：

$$\frac{\partial^2 \mathbf{P}}{\partial t^2} + \gamma \frac{\partial \mathbf{P}}{\partial t} + \omega_0^2 \mathbf{P} = \varepsilon_0 \omega_p^2 \mathbf{E}$$

其中 $\omega_0$ 为共振频率，$\gamma$ 为阻尼率，$\omega_p$ 为等离子频率。$\mathbf{D}=\varepsilon_0\varepsilon_\infty\mathbf{E}+\mathbf{P}$，代入 Maxwell 旋度方程得 ADE-FDTD 更新格式（Lumerical MCM、Tidy3D PoleResidue 共同方案）。多系数材料 MCM 通过加和多个 Lorentz 极点拟合实测 $n(\omega)$ 数据。

### 2.3 非线性（Kerr + 拉曼）

三阶非线性 $\mathbf{P}_{NL}=\varepsilon_0\chi^{(3)}|\mathbf{E}|^2\mathbf{E}$（瞬时 Kerr）+ 卷积拉曼项，ADE 法处理。光子芯片中典型应用为 SiN 微环的克尔自相位调制、LNOI 的 $\chi^{(2)}$ 二次谐波。

---

## 3. Yee 网格离散化方案

### 3.1 Yee 1966 网格布局

3D Yee 单元中：电场分量 $E_x,E_y,E_z$ 位于棱中点，磁场分量 $H_x,H_y,H_z$ 位于面中心，空间半步错位。该布局使每个旋度运算的中心差分天然落在被求场位置，二阶精度 $O(\Delta h^2)$，且离散 Gauss 定律 $\nabla_h\cdot(\nabla_h\times\cdot)\equiv 0$ 自动满足（避免非物理电荷积累）。Yee 网格是 FDE/FDFD/FDTD/2.5D-FDTD 共同基础（ALGORITHMS.md 附录 C）。

### 3.2 E/H leapfrog 时间推进

时间半步错位，磁场在 $n+1/2$ 时刻更新，电场在 $n+1$ 时刻更新。以 $E_z$（TEz 2D）为例：

$$H_x^{n+1/2}\big|_{i,j+1/2} = D_{a,\mu}\# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$ 处理。

### 2.2 色散材料（辅助微分方程 ADE）

Drude-Lorentz 色散介质极化密度 $\mathbf{P}$ 满足二阶 ODE：

$$\frac{\partial^2 \mathbf{P}}{\partial t^2} + \gamma \frac{\partial \mathbf{P}}{\partial t} + \omega_0^2 \mathbf{P} = \varepsilon_0 \omega_p^2 \mathbf{E}$$

其中 $\omega_0$ 为共振频率，$\gamma$ 为阻尼率，$\omega_p$ 为等离子频率。$\mathbf{D}=\varepsilon_0\varepsilon_\infty\mathbf{E}+\mathbf{P}$，代入 Maxwell 旋度方程得 ADE-FDTD 更新格式（Lumerical MCM、Tidy3D PoleResidue 共同方案）。多系数材料 MCM 通过加和多个 Lorentz 极点拟合实测 $n(\omega)$ 数据。

### 2.3 非线性（Kerr + 拉曼）

三阶非线性 $\mathbf{P}_{NL}=\varepsilon_0\chi^{(3)}|\mathbf{E}|^2\mathbf{E}$（瞬时 Kerr）+ 卷积拉曼项，ADE 法处理。光子芯片中典型应用为 SiN 微环的克尔自相位调制、LNOI 的 $\chi^{(2)}$ 二次谐波。

---

## 3. Yee 网格离散化方案

### 3.1 Yee 1966 网格布局

3D Yee 单元中：电场分量 $E_x,E_y,E_z$ 位于棱中点，磁场分量 $H_x,H_y,H_z$ 位于面中心，空间半步错位。该布局使每个旋度运算的中心差分天然落在被求场位置，二阶精度 $O(\Delta h^2)$，且离散 Gauss 定律 $\nabla_h\cdot(\nabla_h\times\cdot)\equiv 0$ 自动满足（避免非物理电荷积累）。Yee 网格是 FDE/FDFD/FDTD/2.5D-FDTD 共同基础（ALGORITHMS.md 附录 C）。

### 3.2 E/H leapfrog 时间推进

时间半步错位，磁场在 $n+1/2$ 时刻更新，电场在 $n+1$ 时刻更新。以 $E_z$（TEz 2D）为例：

$$H_x^{n+1/2}\big|_{i,j+1/2} = D_{a,\mu}\, H_x^{n-1/2}\big|_{i,j+1/2}# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$ 处理。

### 2.2 色散材料（辅助微分方程 ADE）

Drude-Lorentz 色散介质极化密度 $\mathbf{P}$ 满足二阶 ODE：

$$\frac{\partial^2 \mathbf{P}}{\partial t^2} + \gamma \frac{\partial \mathbf{P}}{\partial t} + \omega_0^2 \mathbf{P} = \varepsilon_0 \omega_p^2 \mathbf{E}$$

其中 $\omega_0$ 为共振频率，$\gamma$ 为阻尼率，$\omega_p$ 为等离子频率。$\mathbf{D}=\varepsilon_0\varepsilon_\infty\mathbf{E}+\mathbf{P}$，代入 Maxwell 旋度方程得 ADE-FDTD 更新格式（Lumerical MCM、Tidy3D PoleResidue 共同方案）。多系数材料 MCM 通过加和多个 Lorentz 极点拟合实测 $n(\omega)$ 数据。

### 2.3 非线性（Kerr + 拉曼）

三阶非线性 $\mathbf{P}_{NL}=\varepsilon_0\chi^{(3)}|\mathbf{E}|^2\mathbf{E}$（瞬时 Kerr）+ 卷积拉曼项，ADE 法处理。光子芯片中典型应用为 SiN 微环的克尔自相位调制、LNOI 的 $\chi^{(2)}$ 二次谐波。

---

## 3. Yee 网格离散化方案

### 3.1 Yee 1966 网格布局

3D Yee 单元中：电场分量 $E_x,E_y,E_z$ 位于棱中点，磁场分量 $H_x,H_y,H_z$ 位于面中心，空间半步错位。该布局使每个旋度运算的中心差分天然落在被求场位置，二阶精度 $O(\Delta h^2)$，且离散 Gauss 定律 $\nabla_h\cdot(\nabla_h\times\cdot)\equiv 0$ 自动满足（避免非物理电荷积累）。Yee 网格是 FDE/FDFD/FDTD/2.5D-FDTD 共同基础（ALGORITHMS.md 附录 C）。

### 3.2 E/H leapfrog 时间推进

时间半步错位，磁场在 $n+1/2$ 时刻更新，电场在 $n+1$ 时刻更新。以 $E_z$（TEz 2D）为例：

$$H_x^{n+1/2}\big|_{i,j+1/2} = D_{a,\mu}\, H_x^{n-1/2}\big|_{i,j+1/2} - D_{b,\mu}\,\frac{E_z^n|_{i,j+1}-# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$ 处理。

### 2.2 色散材料（辅助微分方程 ADE）

Drude-Lorentz 色散介质极化密度 $\mathbf{P}$ 满足二阶 ODE：

$$\frac{\partial^2 \mathbf{P}}{\partial t^2} + \gamma \frac{\partial \mathbf{P}}{\partial t} + \omega_0^2 \mathbf{P} = \varepsilon_0 \omega_p^2 \mathbf{E}$$

其中 $\omega_0$ 为共振频率，$\gamma$ 为阻尼率，$\omega_p$ 为等离子频率。$\mathbf{D}=\varepsilon_0\varepsilon_\infty\mathbf{E}+\mathbf{P}$，代入 Maxwell 旋度方程得 ADE-FDTD 更新格式（Lumerical MCM、Tidy3D PoleResidue 共同方案）。多系数材料 MCM 通过加和多个 Lorentz 极点拟合实测 $n(\omega)$ 数据。

### 2.3 非线性（Kerr + 拉曼）

三阶非线性 $\mathbf{P}_{NL}=\varepsilon_0\chi^{(3)}|\mathbf{E}|^2\mathbf{E}$（瞬时 Kerr）+ 卷积拉曼项，ADE 法处理。光子芯片中典型应用为 SiN 微环的克尔自相位调制、LNOI 的 $\chi^{(2)}$ 二次谐波。

---

## 3. Yee 网格离散化方案

### 3.1 Yee 1966 网格布局

3D Yee 单元中：电场分量 $E_x,E_y,E_z$ 位于棱中点，磁场分量 $H_x,H_y,H_z$ 位于面中心，空间半步错位。该布局使每个旋度运算的中心差分天然落在被求场位置，二阶精度 $O(\Delta h^2)$，且离散 Gauss 定律 $\nabla_h\cdot(\nabla_h\times\cdot)\equiv 0$ 自动满足（避免非物理电荷积累）。Yee 网格是 FDE/FDFD/FDTD/2.5D-FDTD 共同基础（ALGORITHMS.md 附录 C）。

### 3.2 E/H leapfrog 时间推进

时间半步错位，磁场在 $n+1/2$ 时刻更新，电场在 $n+1$ 时刻更新。以 $E_z$（TEz 2D）为例：

$$H_x^{n+1/2}\big|_{i,j+1/2} = D_{a,\mu}\, H_x^{n-1/2}\big|_{i,j+1/2} - D_{b,\mu}\,\frac{E_z^n|_{i,j+1}-E_z^n|_{i,j}}{\Delta y}$$

$$H_y^{n+# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$ 处理。

### 2.2 色散材料（辅助微分方程 ADE）

Drude-Lorentz 色散介质极化密度 $\mathbf{P}$ 满足二阶 ODE：

$$\frac{\partial^2 \mathbf{P}}{\partial t^2} + \gamma \frac{\partial \mathbf{P}}{\partial t} + \omega_0^2 \mathbf{P} = \varepsilon_0 \omega_p^2 \mathbf{E}$$

其中 $\omega_0$ 为共振频率，$\gamma$ 为阻尼率，$\omega_p$ 为等离子频率。$\mathbf{D}=\varepsilon_0\varepsilon_\infty\mathbf{E}+\mathbf{P}$，代入 Maxwell 旋度方程得 ADE-FDTD 更新格式（Lumerical MCM、Tidy3D PoleResidue 共同方案）。多系数材料 MCM 通过加和多个 Lorentz 极点拟合实测 $n(\omega)$ 数据。

### 2.3 非线性（Kerr + 拉曼）

三阶非线性 $\mathbf{P}_{NL}=\varepsilon_0\chi^{(3)}|\mathbf{E}|^2\mathbf{E}$（瞬时 Kerr）+ 卷积拉曼项，ADE 法处理。光子芯片中典型应用为 SiN 微环的克尔自相位调制、LNOI 的 $\chi^{(2)}$ 二次谐波。

---

## 3. Yee 网格离散化方案

### 3.1 Yee 1966 网格布局

3D Yee 单元中：电场分量 $E_x,E_y,E_z$ 位于棱中点，磁场分量 $H_x,H_y,H_z$ 位于面中心，空间半步错位。该布局使每个旋度运算的中心差分天然落在被求场位置，二阶精度 $O(\Delta h^2)$，且离散 Gauss 定律 $\nabla_h\cdot(\nabla_h\times\cdot)\equiv 0$ 自动满足（避免非物理电荷积累）。Yee 网格是 FDE/FDFD/FDTD/2.5D-FDTD 共同基础（ALGORITHMS.md 附录 C）。

### 3.2 E/H leapfrog 时间推进

时间半步错位，磁场在 $n+1/2$ 时刻更新，电场在 $n+1$ 时刻更新。以 $E_z$（TEz 2D）为例：

$$H_x^{n+1/2}\big|_{i,j+1/2} = D_{a,\mu}\, H_x^{n-1/2}\big|_{i,j+1/2} - D_{b,\mu}\,\frac{E_z^n|_{i,j+1}-E_z^n|_{i,j}}{\Delta y}$$

$$H_y^{n+1/2}\big|_{i+1/2,j} = D_{a,\mu}\, H_y^{n-1/2# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$ 处理。

### 2.2 色散材料（辅助微分方程 ADE）

Drude-Lorentz 色散介质极化密度 $\mathbf{P}$ 满足二阶 ODE：

$$\frac{\partial^2 \mathbf{P}}{\partial t^2} + \gamma \frac{\partial \mathbf{P}}{\partial t} + \omega_0^2 \mathbf{P} = \varepsilon_0 \omega_p^2 \mathbf{E}$$

其中 $\omega_0$ 为共振频率，$\gamma$ 为阻尼率，$\omega_p$ 为等离子频率。$\mathbf{D}=\varepsilon_0\varepsilon_\infty\mathbf{E}+\mathbf{P}$，代入 Maxwell 旋度方程得 ADE-FDTD 更新格式（Lumerical MCM、Tidy3D PoleResidue 共同方案）。多系数材料 MCM 通过加和多个 Lorentz 极点拟合实测 $n(\omega)$ 数据。

### 2.3 非线性（Kerr + 拉曼）

三阶非线性 $\mathbf{P}_{NL}=\varepsilon_0\chi^{(3)}|\mathbf{E}|^2\mathbf{E}$（瞬时 Kerr）+ 卷积拉曼项，ADE 法处理。光子芯片中典型应用为 SiN 微环的克尔自相位调制、LNOI 的 $\chi^{(2)}$ 二次谐波。

---

## 3. Yee 网格离散化方案

### 3.1 Yee 1966 网格布局

3D Yee 单元中：电场分量 $E_x,E_y,E_z$ 位于棱中点，磁场分量 $H_x,H_y,H_z$ 位于面中心，空间半步错位。该布局使每个旋度运算的中心差分天然落在被求场位置，二阶精度 $O(\Delta h^2)$，且离散 Gauss 定律 $\nabla_h\cdot(\nabla_h\times\cdot)\equiv 0$ 自动满足（避免非物理电荷积累）。Yee 网格是 FDE/FDFD/FDTD/2.5D-FDTD 共同基础（ALGORITHMS.md 附录 C）。

### 3.2 E/H leapfrog 时间推进

时间半步错位，磁场在 $n+1/2$ 时刻更新，电场在 $n+1$ 时刻更新。以 $E_z$（TEz 2D）为例：

$$H_x^{n+1/2}\big|_{i,j+1/2} = D_{a,\mu}\, H_x^{n-1/2}\big|_{i,j+1/2} - D_{b,\mu}\,\frac{E_z^n|_{i,j+1}-E_z^n|_{i,j}}{\Delta y}$$

$$H_y^{n+1/2}\big|_{i+1/2,j} = D_{a,\mu}\, H_y^{n-1/2}\big|_{i+1/2,j# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$ 处理。

### 2.2 色散材料（辅助微分方程 ADE）

Drude-Lorentz 色散介质极化密度 $\mathbf{P}$ 满足二阶 ODE：

$$\frac{\partial^2 \mathbf{P}}{\partial t^2} + \gamma \frac{\partial \mathbf{P}}{\partial t} + \omega_0^2 \mathbf{P} = \varepsilon_0 \omega_p^2 \mathbf{E}$$

其中 $\omega_0$ 为共振频率，$\gamma$ 为阻尼率，$\omega_p$ 为等离子频率。$\mathbf{D}=\varepsilon_0\varepsilon_\infty\mathbf{E}+\mathbf{P}$，代入 Maxwell 旋度方程得 ADE-FDTD 更新格式（Lumerical MCM、Tidy3D PoleResidue 共同方案）。多系数材料 MCM 通过加和多个 Lorentz 极点拟合实测 $n(\omega)$ 数据。

### 2.3 非线性（Kerr + 拉曼）

三阶非线性 $\mathbf{P}_{NL}=\varepsilon_0\chi^{(3)}|\mathbf{E}|^2\mathbf{E}$（瞬时 Kerr）+ 卷积拉曼项，ADE 法处理。光子芯片中典型应用为 SiN 微环的克尔自相位调制、LNOI 的 $\chi^{(2)}$ 二次谐波。

---

## 3. Yee 网格离散化方案

### 3.1 Yee 1966 网格布局

3D Yee 单元中：电场分量 $E_x,E_y,E_z$ 位于棱中点，磁场分量 $H_x,H_y,H_z$ 位于面中心，空间半步错位。该布局使每个旋度运算的中心差分天然落在被求场位置，二阶精度 $O(\Delta h^2)$，且离散 Gauss 定律 $\nabla_h\cdot(\nabla_h\times\cdot)\equiv 0$ 自动满足（避免非物理电荷积累）。Yee 网格是 FDE/FDFD/FDTD/2.5D-FDTD 共同基础（ALGORITHMS.md 附录 C）。

### 3.2 E/H leapfrog 时间推进

时间半步错位，磁场在 $n+1/2$ 时刻更新，电场在 $n+1$ 时刻更新。以 $E_z$（TEz 2D）为例：

$$H_x^{n+1/2}\big|_{i,j+1/2} = D_{a,\mu}\, H_x^{n-1/2}\big|_{i,j+1/2} - D_{b,\mu}\,\frac{E_z^n|_{i,j+1}-E_z^n|_{i,j}}{\Delta y}$$

$$H_y^{n+1/2}\big|_{i+1/2,j} = D_{a,\mu}\, H_y^{n-1/2}\big|_{i+1/2,j} + D_{b,\mu}\,\frac{E_z^n|_{i+1,j# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$ 处理。

### 2.2 色散材料（辅助微分方程 ADE）

Drude-Lorentz 色散介质极化密度 $\mathbf{P}$ 满足二阶 ODE：

$$\frac{\partial^2 \mathbf{P}}{\partial t^2} + \gamma \frac{\partial \mathbf{P}}{\partial t} + \omega_0^2 \mathbf{P} = \varepsilon_0 \omega_p^2 \mathbf{E}$$

其中 $\omega_0$ 为共振频率，$\gamma$ 为阻尼率，$\omega_p$ 为等离子频率。$\mathbf{D}=\varepsilon_0\varepsilon_\infty\mathbf{E}+\mathbf{P}$，代入 Maxwell 旋度方程得 ADE-FDTD 更新格式（Lumerical MCM、Tidy3D PoleResidue 共同方案）。多系数材料 MCM 通过加和多个 Lorentz 极点拟合实测 $n(\omega)$ 数据。

### 2.3 非线性（Kerr + 拉曼）

三阶非线性 $\mathbf{P}_{NL}=\varepsilon_0\chi^{(3)}|\mathbf{E}|^2\mathbf{E}$（瞬时 Kerr）+ 卷积拉曼项，ADE 法处理。光子芯片中典型应用为 SiN 微环的克尔自相位调制、LNOI 的 $\chi^{(2)}$ 二次谐波。

---

## 3. Yee 网格离散化方案

### 3.1 Yee 1966 网格布局

3D Yee 单元中：电场分量 $E_x,E_y,E_z$ 位于棱中点，磁场分量 $H_x,H_y,H_z$ 位于面中心，空间半步错位。该布局使每个旋度运算的中心差分天然落在被求场位置，二阶精度 $O(\Delta h^2)$，且离散 Gauss 定律 $\nabla_h\cdot(\nabla_h\times\cdot)\equiv 0$ 自动满足（避免非物理电荷积累）。Yee 网格是 FDE/FDFD/FDTD/2.5D-FDTD 共同基础（ALGORITHMS.md 附录 C）。

### 3.2 E/H leapfrog 时间推进

时间半步错位，磁场在 $n+1/2$ 时刻更新，电场在 $n+1$ 时刻更新。以 $E_z$（TEz 2D）为例：

$$H_x^{n+1/2}\big|_{i,j+1/2} = D_{a,\mu}\, H_x^{n-1/2}\big|_{i,j+1/2} - D_{b,\mu}\,\frac{E_z^n|_{i,j+1}-E_z^n|_{i,j}}{\Delta y}$$

$$H_y^{n+1/2}\big|_{i+1/2,j} = D_{a,\mu}\, H_y^{n-1/2}\big|_{i+1/2,j} + D_{b,\mu}\,\frac{E_z^n|_{i+1,j}-E_z^n|_{i,j}}{\Delta x}$$

$$E_z^{n# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$ 处理。

### 2.2 色散材料（辅助微分方程 ADE）

Drude-Lorentz 色散介质极化密度 $\mathbf{P}$ 满足二阶 ODE：

$$\frac{\partial^2 \mathbf{P}}{\partial t^2} + \gamma \frac{\partial \mathbf{P}}{\partial t} + \omega_0^2 \mathbf{P} = \varepsilon_0 \omega_p^2 \mathbf{E}$$

其中 $\omega_0$ 为共振频率，$\gamma$ 为阻尼率，$\omega_p$ 为等离子频率。$\mathbf{D}=\varepsilon_0\varepsilon_\infty\mathbf{E}+\mathbf{P}$，代入 Maxwell 旋度方程得 ADE-FDTD 更新格式（Lumerical MCM、Tidy3D PoleResidue 共同方案）。多系数材料 MCM 通过加和多个 Lorentz 极点拟合实测 $n(\omega)$ 数据。

### 2.3 非线性（Kerr + 拉曼）

三阶非线性 $\mathbf{P}_{NL}=\varepsilon_0\chi^{(3)}|\mathbf{E}|^2\mathbf{E}$（瞬时 Kerr）+ 卷积拉曼项，ADE 法处理。光子芯片中典型应用为 SiN 微环的克尔自相位调制、LNOI 的 $\chi^{(2)}$ 二次谐波。

---

## 3. Yee 网格离散化方案

### 3.1 Yee 1966 网格布局

3D Yee 单元中：电场分量 $E_x,E_y,E_z$ 位于棱中点，磁场分量 $H_x,H_y,H_z$ 位于面中心，空间半步错位。该布局使每个旋度运算的中心差分天然落在被求场位置，二阶精度 $O(\Delta h^2)$，且离散 Gauss 定律 $\nabla_h\cdot(\nabla_h\times\cdot)\equiv 0$ 自动满足（避免非物理电荷积累）。Yee 网格是 FDE/FDFD/FDTD/2.5D-FDTD 共同基础（ALGORITHMS.md 附录 C）。

### 3.2 E/H leapfrog 时间推进

时间半步错位，磁场在 $n+1/2$ 时刻更新，电场在 $n+1$ 时刻更新。以 $E_z$（TEz 2D）为例：

$$H_x^{n+1/2}\big|_{i,j+1/2} = D_{a,\mu}\, H_x^{n-1/2}\big|_{i,j+1/2} - D_{b,\mu}\,\frac{E_z^n|_{i,j+1}-E_z^n|_{i,j}}{\Delta y}$$

$$H_y^{n+1/2}\big|_{i+1/2,j} = D_{a,\mu}\, H_y^{n-1/2}\big|_{i+1/2,j} + D_{b,\mu}\,\frac{E_z^n|_{i+1,j}-E_z^n|_{i,j}}{\Delta x}$$

$$E_z^{n+1}\big|_{i,j} = C_{a,\varepsilon}\, E# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$ 处理。

### 2.2 色散材料（辅助微分方程 ADE）

Drude-Lorentz 色散介质极化密度 $\mathbf{P}$ 满足二阶 ODE：

$$\frac{\partial^2 \mathbf{P}}{\partial t^2} + \gamma \frac{\partial \mathbf{P}}{\partial t} + \omega_0^2 \mathbf{P} = \varepsilon_0 \omega_p^2 \mathbf{E}$$

其中 $\omega_0$ 为共振频率，$\gamma$ 为阻尼率，$\omega_p$ 为等离子频率。$\mathbf{D}=\varepsilon_0\varepsilon_\infty\mathbf{E}+\mathbf{P}$，代入 Maxwell 旋度方程得 ADE-FDTD 更新格式（Lumerical MCM、Tidy3D PoleResidue 共同方案）。多系数材料 MCM 通过加和多个 Lorentz 极点拟合实测 $n(\omega)$ 数据。

### 2.3 非线性（Kerr + 拉曼）

三阶非线性 $\mathbf{P}_{NL}=\varepsilon_0\chi^{(3)}|\mathbf{E}|^2\mathbf{E}$（瞬时 Kerr）+ 卷积拉曼项，ADE 法处理。光子芯片中典型应用为 SiN 微环的克尔自相位调制、LNOI 的 $\chi^{(2)}$ 二次谐波。

---

## 3. Yee 网格离散化方案

### 3.1 Yee 1966 网格布局

3D Yee 单元中：电场分量 $E_x,E_y,E_z$ 位于棱中点，磁场分量 $H_x,H_y,H_z$ 位于面中心，空间半步错位。该布局使每个旋度运算的中心差分天然落在被求场位置，二阶精度 $O(\Delta h^2)$，且离散 Gauss 定律 $\nabla_h\cdot(\nabla_h\times\cdot)\equiv 0$ 自动满足（避免非物理电荷积累）。Yee 网格是 FDE/FDFD/FDTD/2.5D-FDTD 共同基础（ALGORITHMS.md 附录 C）。

### 3.2 E/H leapfrog 时间推进

时间半步错位，磁场在 $n+1/2$ 时刻更新，电场在 $n+1$ 时刻更新。以 $E_z$（TEz 2D）为例：

$$H_x^{n+1/2}\big|_{i,j+1/2} = D_{a,\mu}\, H_x^{n-1/2}\big|_{i,j+1/2} - D_{b,\mu}\,\frac{E_z^n|_{i,j+1}-E_z^n|_{i,j}}{\Delta y}$$

$$H_y^{n+1/2}\big|_{i+1/2,j} = D_{a,\mu}\, H_y^{n-1/2}\big|_{i+1/2,j} + D_{b,\mu}\,\frac{E_z^n|_{i+1,j}-E_z^n|_{i,j}}{\Delta x}$$

$$E_z^{n+1}\big|_{i,j} = C_{a,\varepsilon}\, E_z^n\big|_{i,j} +# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$ 处理。

### 2.2 色散材料（辅助微分方程 ADE）

Drude-Lorentz 色散介质极化密度 $\mathbf{P}$ 满足二阶 ODE：

$$\frac{\partial^2 \mathbf{P}}{\partial t^2} + \gamma \frac{\partial \mathbf{P}}{\partial t} + \omega_0^2 \mathbf{P} = \varepsilon_0 \omega_p^2 \mathbf{E}$$

其中 $\omega_0$ 为共振频率，$\gamma$ 为阻尼率，$\omega_p$ 为等离子频率。$\mathbf{D}=\varepsilon_0\varepsilon_\infty\mathbf{E}+\mathbf{P}$，代入 Maxwell 旋度方程得 ADE-FDTD 更新格式（Lumerical MCM、Tidy3D PoleResidue 共同方案）。多系数材料 MCM 通过加和多个 Lorentz 极点拟合实测 $n(\omega)$ 数据。

### 2.3 非线性（Kerr + 拉曼）

三阶非线性 $\mathbf{P}_{NL}=\varepsilon_0\chi^{(3)}|\mathbf{E}|^2\mathbf{E}$（瞬时 Kerr）+ 卷积拉曼项，ADE 法处理。光子芯片中典型应用为 SiN 微环的克尔自相位调制、LNOI 的 $\chi^{(2)}$ 二次谐波。

---

## 3. Yee 网格离散化方案

### 3.1 Yee 1966 网格布局

3D Yee 单元中：电场分量 $E_x,E_y,E_z$ 位于棱中点，磁场分量 $H_x,H_y,H_z$ 位于面中心，空间半步错位。该布局使每个旋度运算的中心差分天然落在被求场位置，二阶精度 $O(\Delta h^2)$，且离散 Gauss 定律 $\nabla_h\cdot(\nabla_h\times\cdot)\equiv 0$ 自动满足（避免非物理电荷积累）。Yee 网格是 FDE/FDFD/FDTD/2.5D-FDTD 共同基础（ALGORITHMS.md 附录 C）。

### 3.2 E/H leapfrog 时间推进

时间半步错位，磁场在 $n+1/2$ 时刻更新，电场在 $n+1$ 时刻更新。以 $E_z$（TEz 2D）为例：

$$H_x^{n+1/2}\big|_{i,j+1/2} = D_{a,\mu}\, H_x^{n-1/2}\big|_{i,j+1/2} - D_{b,\mu}\,\frac{E_z^n|_{i,j+1}-E_z^n|_{i,j}}{\Delta y}$$

$$H_y^{n+1/2}\big|_{i+1/2,j} = D_{a,\mu}\, H_y^{n-1/2}\big|_{i+1/2,j} + D_{b,\mu}\,\frac{E_z^n|_{i+1,j}-E_z^n|_{i,j}}{\Delta x}$$

$$E_z^{n+1}\big|_{i,j} = C_{a,\varepsilon}\, E_z^n\big|_{i,j} + C_{b,\varepsilon}\left[\# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$ 处理。

### 2.2 色散材料（辅助微分方程 ADE）

Drude-Lorentz 色散介质极化密度 $\mathbf{P}$ 满足二阶 ODE：

$$\frac{\partial^2 \mathbf{P}}{\partial t^2} + \gamma \frac{\partial \mathbf{P}}{\partial t} + \omega_0^2 \mathbf{P} = \varepsilon_0 \omega_p^2 \mathbf{E}$$

其中 $\omega_0$ 为共振频率，$\gamma$ 为阻尼率，$\omega_p$ 为等离子频率。$\mathbf{D}=\varepsilon_0\varepsilon_\infty\mathbf{E}+\mathbf{P}$，代入 Maxwell 旋度方程得 ADE-FDTD 更新格式（Lumerical MCM、Tidy3D PoleResidue 共同方案）。多系数材料 MCM 通过加和多个 Lorentz 极点拟合实测 $n(\omega)$ 数据。

### 2.3 非线性（Kerr + 拉曼）

三阶非线性 $\mathbf{P}_{NL}=\varepsilon_0\chi^{(3)}|\mathbf{E}|^2\mathbf{E}$（瞬时 Kerr）+ 卷积拉曼项，ADE 法处理。光子芯片中典型应用为 SiN 微环的克尔自相位调制、LNOI 的 $\chi^{(2)}$ 二次谐波。

---

## 3. Yee 网格离散化方案

### 3.1 Yee 1966 网格布局

3D Yee 单元中：电场分量 $E_x,E_y,E_z$ 位于棱中点，磁场分量 $H_x,H_y,H_z$ 位于面中心，空间半步错位。该布局使每个旋度运算的中心差分天然落在被求场位置，二阶精度 $O(\Delta h^2)$，且离散 Gauss 定律 $\nabla_h\cdot(\nabla_h\times\cdot)\equiv 0$ 自动满足（避免非物理电荷积累）。Yee 网格是 FDE/FDFD/FDTD/2.5D-FDTD 共同基础（ALGORITHMS.md 附录 C）。

### 3.2 E/H leapfrog 时间推进

时间半步错位，磁场在 $n+1/2$ 时刻更新，电场在 $n+1$ 时刻更新。以 $E_z$（TEz 2D）为例：

$$H_x^{n+1/2}\big|_{i,j+1/2} = D_{a,\mu}\, H_x^{n-1/2}\big|_{i,j+1/2} - D_{b,\mu}\,\frac{E_z^n|_{i,j+1}-E_z^n|_{i,j}}{\Delta y}$$

$$H_y^{n+1/2}\big|_{i+1/2,j} = D_{a,\mu}\, H_y^{n-1/2}\big|_{i+1/2,j} + D_{b,\mu}\,\frac{E_z^n|_{i+1,j}-E_z^n|_{i,j}}{\Delta x}$$

$$E_z^{n+1}\big|_{i,j} = C_{a,\varepsilon}\, E_z^n\big|_{i,j} + C_{b,\varepsilon}\left[\frac{H_y^{n+1/2# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$ 处理。

### 2.2 色散材料（辅助微分方程 ADE）

Drude-Lorentz 色散介质极化密度 $\mathbf{P}$ 满足二阶 ODE：

$$\frac{\partial^2 \mathbf{P}}{\partial t^2} + \gamma \frac{\partial \mathbf{P}}{\partial t} + \omega_0^2 \mathbf{P} = \varepsilon_0 \omega_p^2 \mathbf{E}$$

其中 $\omega_0$ 为共振频率，$\gamma$ 为阻尼率，$\omega_p$ 为等离子频率。$\mathbf{D}=\varepsilon_0\varepsilon_\infty\mathbf{E}+\mathbf{P}$，代入 Maxwell 旋度方程得 ADE-FDTD 更新格式（Lumerical MCM、Tidy3D PoleResidue 共同方案）。多系数材料 MCM 通过加和多个 Lorentz 极点拟合实测 $n(\omega)$ 数据。

### 2.3 非线性（Kerr + 拉曼）

三阶非线性 $\mathbf{P}_{NL}=\varepsilon_0\chi^{(3)}|\mathbf{E}|^2\mathbf{E}$（瞬时 Kerr）+ 卷积拉曼项，ADE 法处理。光子芯片中典型应用为 SiN 微环的克尔自相位调制、LNOI 的 $\chi^{(2)}$ 二次谐波。

---

## 3. Yee 网格离散化方案

### 3.1 Yee 1966 网格布局

3D Yee 单元中：电场分量 $E_x,E_y,E_z$ 位于棱中点，磁场分量 $H_x,H_y,H_z$ 位于面中心，空间半步错位。该布局使每个旋度运算的中心差分天然落在被求场位置，二阶精度 $O(\Delta h^2)$，且离散 Gauss 定律 $\nabla_h\cdot(\nabla_h\times\cdot)\equiv 0$ 自动满足（避免非物理电荷积累）。Yee 网格是 FDE/FDFD/FDTD/2.5D-FDTD 共同基础（ALGORITHMS.md 附录 C）。

### 3.2 E/H leapfrog 时间推进

时间半步错位，磁场在 $n+1/2$ 时刻更新，电场在 $n+1$ 时刻更新。以 $E_z$（TEz 2D）为例：

$$H_x^{n+1/2}\big|_{i,j+1/2} = D_{a,\mu}\, H_x^{n-1/2}\big|_{i,j+1/2} - D_{b,\mu}\,\frac{E_z^n|_{i,j+1}-E_z^n|_{i,j}}{\Delta y}$$

$$H_y^{n+1/2}\big|_{i+1/2,j} = D_{a,\mu}\, H_y^{n-1/2}\big|_{i+1/2,j} + D_{b,\mu}\,\frac{E_z^n|_{i+1,j}-E_z^n|_{i,j}}{\Delta x}$$

$$E_z^{n+1}\big|_{i,j} = C_{a,\varepsilon}\, E_z^n\big|_{i,j} + C_{b,\varepsilon}\left[\frac{H_y^{n+1/2}|_{i+1/2,j}-H_y^{n+1/2}|_{i# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$ 处理。

### 2.2 色散材料（辅助微分方程 ADE）

Drude-Lorentz 色散介质极化密度 $\mathbf{P}$ 满足二阶 ODE：

$$\frac{\partial^2 \mathbf{P}}{\partial t^2} + \gamma \frac{\partial \mathbf{P}}{\partial t} + \omega_0^2 \mathbf{P} = \varepsilon_0 \omega_p^2 \mathbf{E}$$

其中 $\omega_0$ 为共振频率，$\gamma$ 为阻尼率，$\omega_p$ 为等离子频率。$\mathbf{D}=\varepsilon_0\varepsilon_\infty\mathbf{E}+\mathbf{P}$，代入 Maxwell 旋度方程得 ADE-FDTD 更新格式（Lumerical MCM、Tidy3D PoleResidue 共同方案）。多系数材料 MCM 通过加和多个 Lorentz 极点拟合实测 $n(\omega)$ 数据。

### 2.3 非线性（Kerr + 拉曼）

三阶非线性 $\mathbf{P}_{NL}=\varepsilon_0\chi^{(3)}|\mathbf{E}|^2\mathbf{E}$（瞬时 Kerr）+ 卷积拉曼项，ADE 法处理。光子芯片中典型应用为 SiN 微环的克尔自相位调制、LNOI 的 $\chi^{(2)}$ 二次谐波。

---

## 3. Yee 网格离散化方案

### 3.1 Yee 1966 网格布局

3D Yee 单元中：电场分量 $E_x,E_y,E_z$ 位于棱中点，磁场分量 $H_x,H_y,H_z$ 位于面中心，空间半步错位。该布局使每个旋度运算的中心差分天然落在被求场位置，二阶精度 $O(\Delta h^2)$，且离散 Gauss 定律 $\nabla_h\cdot(\nabla_h\times\cdot)\equiv 0$ 自动满足（避免非物理电荷积累）。Yee 网格是 FDE/FDFD/FDTD/2.5D-FDTD 共同基础（ALGORITHMS.md 附录 C）。

### 3.2 E/H leapfrog 时间推进

时间半步错位，磁场在 $n+1/2$ 时刻更新，电场在 $n+1$ 时刻更新。以 $E_z$（TEz 2D）为例：

$$H_x^{n+1/2}\big|_{i,j+1/2} = D_{a,\mu}\, H_x^{n-1/2}\big|_{i,j+1/2} - D_{b,\mu}\,\frac{E_z^n|_{i,j+1}-E_z^n|_{i,j}}{\Delta y}$$

$$H_y^{n+1/2}\big|_{i+1/2,j} = D_{a,\mu}\, H_y^{n-1/2}\big|_{i+1/2,j} + D_{b,\mu}\,\frac{E_z^n|_{i+1,j}-E_z^n|_{i,j}}{\Delta x}$$

$$E_z^{n+1}\big|_{i,j} = C_{a,\varepsilon}\, E_z^n\big|_{i,j} + C_{b,\varepsilon}\left[\frac{H_y^{n+1/2}|_{i+1/2,j}-H_y^{n+1/2}|_{i-1/2,j}}{\Delta x} - \frac{H_x^{n+1/2}|_{i,j+1/2# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$ 处理。

### 2.2 色散材料（辅助微分方程 ADE）

Drude-Lorentz 色散介质极化密度 $\mathbf{P}$ 满足二阶 ODE：

$$\frac{\partial^2 \mathbf{P}}{\partial t^2} + \gamma \frac{\partial \mathbf{P}}{\partial t} + \omega_0^2 \mathbf{P} = \varepsilon_0 \omega_p^2 \mathbf{E}$$

其中 $\omega_0$ 为共振频率，$\gamma$ 为阻尼率，$\omega_p$ 为等离子频率。$\mathbf{D}=\varepsilon_0\varepsilon_\infty\mathbf{E}+\mathbf{P}$，代入 Maxwell 旋度方程得 ADE-FDTD 更新格式（Lumerical MCM、Tidy3D PoleResidue 共同方案）。多系数材料 MCM 通过加和多个 Lorentz 极点拟合实测 $n(\omega)$ 数据。

### 2.3 非线性（Kerr + 拉曼）

三阶非线性 $\mathbf{P}_{NL}=\varepsilon_0\chi^{(3)}|\mathbf{E}|^2\mathbf{E}$（瞬时 Kerr）+ 卷积拉曼项，ADE 法处理。光子芯片中典型应用为 SiN 微环的克尔自相位调制、LNOI 的 $\chi^{(2)}$ 二次谐波。

---

## 3. Yee 网格离散化方案

### 3.1 Yee 1966 网格布局

3D Yee 单元中：电场分量 $E_x,E_y,E_z$ 位于棱中点，磁场分量 $H_x,H_y,H_z$ 位于面中心，空间半步错位。该布局使每个旋度运算的中心差分天然落在被求场位置，二阶精度 $O(\Delta h^2)$，且离散 Gauss 定律 $\nabla_h\cdot(\nabla_h\times\cdot)\equiv 0$ 自动满足（避免非物理电荷积累）。Yee 网格是 FDE/FDFD/FDTD/2.5D-FDTD 共同基础（ALGORITHMS.md 附录 C）。

### 3.2 E/H leapfrog 时间推进

时间半步错位，磁场在 $n+1/2$ 时刻更新，电场在 $n+1$ 时刻更新。以 $E_z$（TEz 2D）为例：

$$H_x^{n+1/2}\big|_{i,j+1/2} = D_{a,\mu}\, H_x^{n-1/2}\big|_{i,j+1/2} - D_{b,\mu}\,\frac{E_z^n|_{i,j+1}-E_z^n|_{i,j}}{\Delta y}$$

$$H_y^{n+1/2}\big|_{i+1/2,j} = D_{a,\mu}\, H_y^{n-1/2}\big|_{i+1/2,j} + D_{b,\mu}\,\frac{E_z^n|_{i+1,j}-E_z^n|_{i,j}}{\Delta x}$$

$$E_z^{n+1}\big|_{i,j} = C_{a,\varepsilon}\, E_z^n\big|_{i,j} + C_{b,\varepsilon}\left[\frac{H_y^{n+1/2}|_{i+1/2,j}-H_y^{n+1/2}|_{i-1/2,j}}{\Delta x} - \frac{H_x^{n+1/2}|_{i,j+1/2}-H_x^{n+1/2}|_{i,j-1/2}}{\Delta y}\right]$$

其中 $D_{a,\mu}=\frac{1-\sigma_m\Delta t/(2\mu_0# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$ 处理。

### 2.2 色散材料（辅助微分方程 ADE）

Drude-Lorentz 色散介质极化密度 $\mathbf{P}$ 满足二阶 ODE：

$$\frac{\partial^2 \mathbf{P}}{\partial t^2} + \gamma \frac{\partial \mathbf{P}}{\partial t} + \omega_0^2 \mathbf{P} = \varepsilon_0 \omega_p^2 \mathbf{E}$$

其中 $\omega_0$ 为共振频率，$\gamma$ 为阻尼率，$\omega_p$ 为等离子频率。$\mathbf{D}=\varepsilon_0\varepsilon_\infty\mathbf{E}+\mathbf{P}$，代入 Maxwell 旋度方程得 ADE-FDTD 更新格式（Lumerical MCM、Tidy3D PoleResidue 共同方案）。多系数材料 MCM 通过加和多个 Lorentz 极点拟合实测 $n(\omega)$ 数据。

### 2.3 非线性（Kerr + 拉曼）

三阶非线性 $\mathbf{P}_{NL}=\varepsilon_0\chi^{(3)}|\mathbf{E}|^2\mathbf{E}$（瞬时 Kerr）+ 卷积拉曼项，ADE 法处理。光子芯片中典型应用为 SiN 微环的克尔自相位调制、LNOI 的 $\chi^{(2)}$ 二次谐波。

---

## 3. Yee 网格离散化方案

### 3.1 Yee 1966 网格布局

3D Yee 单元中：电场分量 $E_x,E_y,E_z$ 位于棱中点，磁场分量 $H_x,H_y,H_z$ 位于面中心，空间半步错位。该布局使每个旋度运算的中心差分天然落在被求场位置，二阶精度 $O(\Delta h^2)$，且离散 Gauss 定律 $\nabla_h\cdot(\nabla_h\times\cdot)\equiv 0$ 自动满足（避免非物理电荷积累）。Yee 网格是 FDE/FDFD/FDTD/2.5D-FDTD 共同基础（ALGORITHMS.md 附录 C）。

### 3.2 E/H leapfrog 时间推进

时间半步错位，磁场在 $n+1/2$ 时刻更新，电场在 $n+1$ 时刻更新。以 $E_z$（TEz 2D）为例：

$$H_x^{n+1/2}\big|_{i,j+1/2} = D_{a,\mu}\, H_x^{n-1/2}\big|_{i,j+1/2} - D_{b,\mu}\,\frac{E_z^n|_{i,j+1}-E_z^n|_{i,j}}{\Delta y}$$

$$H_y^{n+1/2}\big|_{i+1/2,j} = D_{a,\mu}\, H_y^{n-1/2}\big|_{i+1/2,j} + D_{b,\mu}\,\frac{E_z^n|_{i+1,j}-E_z^n|_{i,j}}{\Delta x}$$

$$E_z^{n+1}\big|_{i,j} = C_{a,\varepsilon}\, E_z^n\big|_{i,j} + C_{b,\varepsilon}\left[\frac{H_y^{n+1/2}|_{i+1/2,j}-H_y^{n+1/2}|_{i-1/2,j}}{\Delta x} - \frac{H_x^{n+1/2}|_{i,j+1/2}-H_x^{n+1/2}|_{i,j-1/2}}{\Delta y}\right]$$

其中 $D_{a,\mu}=\frac{1-\sigma_m\Delta t/(2\mu_0)}{1+\sigma_m\Delta t/(2\mu_0)}$，$D_{b,\mu}=\frac{\Delta t# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$ 处理。

### 2.2 色散材料（辅助微分方程 ADE）

Drude-Lorentz 色散介质极化密度 $\mathbf{P}$ 满足二阶 ODE：

$$\frac{\partial^2 \mathbf{P}}{\partial t^2} + \gamma \frac{\partial \mathbf{P}}{\partial t} + \omega_0^2 \mathbf{P} = \varepsilon_0 \omega_p^2 \mathbf{E}$$

其中 $\omega_0$ 为共振频率，$\gamma$ 为阻尼率，$\omega_p$ 为等离子频率。$\mathbf{D}=\varepsilon_0\varepsilon_\infty\mathbf{E}+\mathbf{P}$，代入 Maxwell 旋度方程得 ADE-FDTD 更新格式（Lumerical MCM、Tidy3D PoleResidue 共同方案）。多系数材料 MCM 通过加和多个 Lorentz 极点拟合实测 $n(\omega)$ 数据。

### 2.3 非线性（Kerr + 拉曼）

三阶非线性 $\mathbf{P}_{NL}=\varepsilon_0\chi^{(3)}|\mathbf{E}|^2\mathbf{E}$（瞬时 Kerr）+ 卷积拉曼项，ADE 法处理。光子芯片中典型应用为 SiN 微环的克尔自相位调制、LNOI 的 $\chi^{(2)}$ 二次谐波。

---

## 3. Yee 网格离散化方案

### 3.1 Yee 1966 网格布局

3D Yee 单元中：电场分量 $E_x,E_y,E_z$ 位于棱中点，磁场分量 $H_x,H_y,H_z$ 位于面中心，空间半步错位。该布局使每个旋度运算的中心差分天然落在被求场位置，二阶精度 $O(\Delta h^2)$，且离散 Gauss 定律 $\nabla_h\cdot(\nabla_h\times\cdot)\equiv 0$ 自动满足（避免非物理电荷积累）。Yee 网格是 FDE/FDFD/FDTD/2.5D-FDTD 共同基础（ALGORITHMS.md 附录 C）。

### 3.2 E/H leapfrog 时间推进

时间半步错位，磁场在 $n+1/2$ 时刻更新，电场在 $n+1$ 时刻更新。以 $E_z$（TEz 2D）为例：

$$H_x^{n+1/2}\big|_{i,j+1/2} = D_{a,\mu}\, H_x^{n-1/2}\big|_{i,j+1/2} - D_{b,\mu}\,\frac{E_z^n|_{i,j+1}-E_z^n|_{i,j}}{\Delta y}$$

$$H_y^{n+1/2}\big|_{i+1/2,j} = D_{a,\mu}\, H_y^{n-1/2}\big|_{i+1/2,j} + D_{b,\mu}\,\frac{E_z^n|_{i+1,j}-E_z^n|_{i,j}}{\Delta x}$$

$$E_z^{n+1}\big|_{i,j} = C_{a,\varepsilon}\, E_z^n\big|_{i,j} + C_{b,\varepsilon}\left[\frac{H_y^{n+1/2}|_{i+1/2,j}-H_y^{n+1/2}|_{i-1/2,j}}{\Delta x} - \frac{H_x^{n+1/2}|_{i,j+1/2}-H_x^{n+1/2}|_{i,j-1/2}}{\Delta y}\right]$$

其中 $D_{a,\mu}=\frac{1-\sigma_m\Delta t/(2\mu_0)}{1+\sigma_m\Delta t/(2\mu_0)}$，$D_{b,\mu}=\frac{\Delta t/\mu_0}{1+\sigma_m\Delta t/(2\mu_0)}$，$C_{a,\varepsilon}=\frac{1-\sigma\Delta t/(2\varepsilon_0\varepsilon_r# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$ 处理。

### 2.2 色散材料（辅助微分方程 ADE）

Drude-Lorentz 色散介质极化密度 $\mathbf{P}$ 满足二阶 ODE：

$$\frac{\partial^2 \mathbf{P}}{\partial t^2} + \gamma \frac{\partial \mathbf{P}}{\partial t} + \omega_0^2 \mathbf{P} = \varepsilon_0 \omega_p^2 \mathbf{E}$$

其中 $\omega_0$ 为共振频率，$\gamma$ 为阻尼率，$\omega_p$ 为等离子频率。$\mathbf{D}=\varepsilon_0\varepsilon_\infty\mathbf{E}+\mathbf{P}$，代入 Maxwell 旋度方程得 ADE-FDTD 更新格式（Lumerical MCM、Tidy3D PoleResidue 共同方案）。多系数材料 MCM 通过加和多个 Lorentz 极点拟合实测 $n(\omega)$ 数据。

### 2.3 非线性（Kerr + 拉曼）

三阶非线性 $\mathbf{P}_{NL}=\varepsilon_0\chi^{(3)}|\mathbf{E}|^2\mathbf{E}$（瞬时 Kerr）+ 卷积拉曼项，ADE 法处理。光子芯片中典型应用为 SiN 微环的克尔自相位调制、LNOI 的 $\chi^{(2)}$ 二次谐波。

---

## 3. Yee 网格离散化方案

### 3.1 Yee 1966 网格布局

3D Yee 单元中：电场分量 $E_x,E_y,E_z$ 位于棱中点，磁场分量 $H_x,H_y,H_z$ 位于面中心，空间半步错位。该布局使每个旋度运算的中心差分天然落在被求场位置，二阶精度 $O(\Delta h^2)$，且离散 Gauss 定律 $\nabla_h\cdot(\nabla_h\times\cdot)\equiv 0$ 自动满足（避免非物理电荷积累）。Yee 网格是 FDE/FDFD/FDTD/2.5D-FDTD 共同基础（ALGORITHMS.md 附录 C）。

### 3.2 E/H leapfrog 时间推进

时间半步错位，磁场在 $n+1/2$ 时刻更新，电场在 $n+1$ 时刻更新。以 $E_z$（TEz 2D）为例：

$$H_x^{n+1/2}\big|_{i,j+1/2} = D_{a,\mu}\, H_x^{n-1/2}\big|_{i,j+1/2} - D_{b,\mu}\,\frac{E_z^n|_{i,j+1}-E_z^n|_{i,j}}{\Delta y}$$

$$H_y^{n+1/2}\big|_{i+1/2,j} = D_{a,\mu}\, H_y^{n-1/2}\big|_{i+1/2,j} + D_{b,\mu}\,\frac{E_z^n|_{i+1,j}-E_z^n|_{i,j}}{\Delta x}$$

$$E_z^{n+1}\big|_{i,j} = C_{a,\varepsilon}\, E_z^n\big|_{i,j} + C_{b,\varepsilon}\left[\frac{H_y^{n+1/2}|_{i+1/2,j}-H_y^{n+1/2}|_{i-1/2,j}}{\Delta x} - \frac{H_x^{n+1/2}|_{i,j+1/2}-H_x^{n+1/2}|_{i,j-1/2}}{\Delta y}\right]$$

其中 $D_{a,\mu}=\frac{1-\sigma_m\Delta t/(2\mu_0)}{1+\sigma_m\Delta t/(2\mu_0)}$，$D_{b,\mu}=\frac{\Delta t/\mu_0}{1+\sigma_m\Delta t/(2\mu_0)}$，$C_{a,\varepsilon}=\frac{1-\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}{1+\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$ 处理。

### 2.2 色散材料（辅助微分方程 ADE）

Drude-Lorentz 色散介质极化密度 $\mathbf{P}$ 满足二阶 ODE：

$$\frac{\partial^2 \mathbf{P}}{\partial t^2} + \gamma \frac{\partial \mathbf{P}}{\partial t} + \omega_0^2 \mathbf{P} = \varepsilon_0 \omega_p^2 \mathbf{E}$$

其中 $\omega_0$ 为共振频率，$\gamma$ 为阻尼率，$\omega_p$ 为等离子频率。$\mathbf{D}=\varepsilon_0\varepsilon_\infty\mathbf{E}+\mathbf{P}$，代入 Maxwell 旋度方程得 ADE-FDTD 更新格式（Lumerical MCM、Tidy3D PoleResidue 共同方案）。多系数材料 MCM 通过加和多个 Lorentz 极点拟合实测 $n(\omega)$ 数据。

### 2.3 非线性（Kerr + 拉曼）

三阶非线性 $\mathbf{P}_{NL}=\varepsilon_0\chi^{(3)}|\mathbf{E}|^2\mathbf{E}$（瞬时 Kerr）+ 卷积拉曼项，ADE 法处理。光子芯片中典型应用为 SiN 微环的克尔自相位调制、LNOI 的 $\chi^{(2)}$ 二次谐波。

---

## 3. Yee 网格离散化方案

### 3.1 Yee 1966 网格布局

3D Yee 单元中：电场分量 $E_x,E_y,E_z$ 位于棱中点，磁场分量 $H_x,H_y,H_z$ 位于面中心，空间半步错位。该布局使每个旋度运算的中心差分天然落在被求场位置，二阶精度 $O(\Delta h^2)$，且离散 Gauss 定律 $\nabla_h\cdot(\nabla_h\times\cdot)\equiv 0$ 自动满足（避免非物理电荷积累）。Yee 网格是 FDE/FDFD/FDTD/2.5D-FDTD 共同基础（ALGORITHMS.md 附录 C）。

### 3.2 E/H leapfrog 时间推进

时间半步错位，磁场在 $n+1/2$ 时刻更新，电场在 $n+1$ 时刻更新。以 $E_z$（TEz 2D）为例：

$$H_x^{n+1/2}\big|_{i,j+1/2} = D_{a,\mu}\, H_x^{n-1/2}\big|_{i,j+1/2} - D_{b,\mu}\,\frac{E_z^n|_{i,j+1}-E_z^n|_{i,j}}{\Delta y}$$

$$H_y^{n+1/2}\big|_{i+1/2,j} = D_{a,\mu}\, H_y^{n-1/2}\big|_{i+1/2,j} + D_{b,\mu}\,\frac{E_z^n|_{i+1,j}-E_z^n|_{i,j}}{\Delta x}$$

$$E_z^{n+1}\big|_{i,j} = C_{a,\varepsilon}\, E_z^n\big|_{i,j} + C_{b,\varepsilon}\left[\frac{H_y^{n+1/2}|_{i+1/2,j}-H_y^{n+1/2}|_{i-1/2,j}}{\Delta x} - \frac{H_x^{n+1/2}|_{i,j+1/2}-H_x^{n+1/2}|_{i,j-1/2}}{\Delta y}\right]$$

其中 $D_{a,\mu}=\frac{1-\sigma_m\Delta t/(2\mu_0)}{1+\sigma_m\Delta t/(2\mu_0)}$，$D_{b,\mu}=\frac{\Delta t/\mu_0}{1+\sigma_m\Delta t/(2\mu_0)}$，$C_{a,\varepsilon}=\frac{1-\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}{1+\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}$，$C_{b,\varepsilon}=\frac{\Delta t/(\vare# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$ 处理。

### 2.2 色散材料（辅助微分方程 ADE）

Drude-Lorentz 色散介质极化密度 $\mathbf{P}$ 满足二阶 ODE：

$$\frac{\partial^2 \mathbf{P}}{\partial t^2} + \gamma \frac{\partial \mathbf{P}}{\partial t} + \omega_0^2 \mathbf{P} = \varepsilon_0 \omega_p^2 \mathbf{E}$$

其中 $\omega_0$ 为共振频率，$\gamma$ 为阻尼率，$\omega_p$ 为等离子频率。$\mathbf{D}=\varepsilon_0\varepsilon_\infty\mathbf{E}+\mathbf{P}$，代入 Maxwell 旋度方程得 ADE-FDTD 更新格式（Lumerical MCM、Tidy3D PoleResidue 共同方案）。多系数材料 MCM 通过加和多个 Lorentz 极点拟合实测 $n(\omega)$ 数据。

### 2.3 非线性（Kerr + 拉曼）

三阶非线性 $\mathbf{P}_{NL}=\varepsilon_0\chi^{(3)}|\mathbf{E}|^2\mathbf{E}$（瞬时 Kerr）+ 卷积拉曼项，ADE 法处理。光子芯片中典型应用为 SiN 微环的克尔自相位调制、LNOI 的 $\chi^{(2)}$ 二次谐波。

---

## 3. Yee 网格离散化方案

### 3.1 Yee 1966 网格布局

3D Yee 单元中：电场分量 $E_x,E_y,E_z$ 位于棱中点，磁场分量 $H_x,H_y,H_z$ 位于面中心，空间半步错位。该布局使每个旋度运算的中心差分天然落在被求场位置，二阶精度 $O(\Delta h^2)$，且离散 Gauss 定律 $\nabla_h\cdot(\nabla_h\times\cdot)\equiv 0$ 自动满足（避免非物理电荷积累）。Yee 网格是 FDE/FDFD/FDTD/2.5D-FDTD 共同基础（ALGORITHMS.md 附录 C）。

### 3.2 E/H leapfrog 时间推进

时间半步错位，磁场在 $n+1/2$ 时刻更新，电场在 $n+1$ 时刻更新。以 $E_z$（TEz 2D）为例：

$$H_x^{n+1/2}\big|_{i,j+1/2} = D_{a,\mu}\, H_x^{n-1/2}\big|_{i,j+1/2} - D_{b,\mu}\,\frac{E_z^n|_{i,j+1}-E_z^n|_{i,j}}{\Delta y}$$

$$H_y^{n+1/2}\big|_{i+1/2,j} = D_{a,\mu}\, H_y^{n-1/2}\big|_{i+1/2,j} + D_{b,\mu}\,\frac{E_z^n|_{i+1,j}-E_z^n|_{i,j}}{\Delta x}$$

$$E_z^{n+1}\big|_{i,j} = C_{a,\varepsilon}\, E_z^n\big|_{i,j} + C_{b,\varepsilon}\left[\frac{H_y^{n+1/2}|_{i+1/2,j}-H_y^{n+1/2}|_{i-1/2,j}}{\Delta x} - \frac{H_x^{n+1/2}|_{i,j+1/2}-H_x^{n+1/2}|_{i,j-1/2}}{\Delta y}\right]$$

其中 $D_{a,\mu}=\frac{1-\sigma_m\Delta t/(2\mu_0)}{1+\sigma_m\Delta t/(2\mu_0)}$，$D_{b,\mu}=\frac{\Delta t/\mu_0}{1+\sigma_m\Delta t/(2\mu_0)}$，$C_{a,\varepsilon}=\frac{1-\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}{1+\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}$，$C_{b,\varepsilon}=\frac{\Delta t/(\varepsilon_0\varepsilon_r)}{1# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$ 处理。

### 2.2 色散材料（辅助微分方程 ADE）

Drude-Lorentz 色散介质极化密度 $\mathbf{P}$ 满足二阶 ODE：

$$\frac{\partial^2 \mathbf{P}}{\partial t^2} + \gamma \frac{\partial \mathbf{P}}{\partial t} + \omega_0^2 \mathbf{P} = \varepsilon_0 \omega_p^2 \mathbf{E}$$

其中 $\omega_0$ 为共振频率，$\gamma$ 为阻尼率，$\omega_p$ 为等离子频率。$\mathbf{D}=\varepsilon_0\varepsilon_\infty\mathbf{E}+\mathbf{P}$，代入 Maxwell 旋度方程得 ADE-FDTD 更新格式（Lumerical MCM、Tidy3D PoleResidue 共同方案）。多系数材料 MCM 通过加和多个 Lorentz 极点拟合实测 $n(\omega)$ 数据。

### 2.3 非线性（Kerr + 拉曼）

三阶非线性 $\mathbf{P}_{NL}=\varepsilon_0\chi^{(3)}|\mathbf{E}|^2\mathbf{E}$（瞬时 Kerr）+ 卷积拉曼项，ADE 法处理。光子芯片中典型应用为 SiN 微环的克尔自相位调制、LNOI 的 $\chi^{(2)}$ 二次谐波。

---

## 3. Yee 网格离散化方案

### 3.1 Yee 1966 网格布局

3D Yee 单元中：电场分量 $E_x,E_y,E_z$ 位于棱中点，磁场分量 $H_x,H_y,H_z$ 位于面中心，空间半步错位。该布局使每个旋度运算的中心差分天然落在被求场位置，二阶精度 $O(\Delta h^2)$，且离散 Gauss 定律 $\nabla_h\cdot(\nabla_h\times\cdot)\equiv 0$ 自动满足（避免非物理电荷积累）。Yee 网格是 FDE/FDFD/FDTD/2.5D-FDTD 共同基础（ALGORITHMS.md 附录 C）。

### 3.2 E/H leapfrog 时间推进

时间半步错位，磁场在 $n+1/2$ 时刻更新，电场在 $n+1$ 时刻更新。以 $E_z$（TEz 2D）为例：

$$H_x^{n+1/2}\big|_{i,j+1/2} = D_{a,\mu}\, H_x^{n-1/2}\big|_{i,j+1/2} - D_{b,\mu}\,\frac{E_z^n|_{i,j+1}-E_z^n|_{i,j}}{\Delta y}$$

$$H_y^{n+1/2}\big|_{i+1/2,j} = D_{a,\mu}\, H_y^{n-1/2}\big|_{i+1/2,j} + D_{b,\mu}\,\frac{E_z^n|_{i+1,j}-E_z^n|_{i,j}}{\Delta x}$$

$$E_z^{n+1}\big|_{i,j} = C_{a,\varepsilon}\, E_z^n\big|_{i,j} + C_{b,\varepsilon}\left[\frac{H_y^{n+1/2}|_{i+1/2,j}-H_y^{n+1/2}|_{i-1/2,j}}{\Delta x} - \frac{H_x^{n+1/2}|_{i,j+1/2}-H_x^{n+1/2}|_{i,j-1/2}}{\Delta y}\right]$$

其中 $D_{a,\mu}=\frac{1-\sigma_m\Delta t/(2\mu_0)}{1+\sigma_m\Delta t/(2\mu_0)}$，$D_{b,\mu}=\frac{\Delta t/\mu_0}{1+\sigma_m\Delta t/(2\mu_0)}$，$C_{a,\varepsilon}=\frac{1-\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}{1+\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}$，$C_{b,\varepsilon}=\frac{\Delta t/(\varepsilon_0\varepsilon_r)}{1+\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}$。3D 形式按 6 个分量类似展开。

### 3.3 共形网格# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$ 处理。

### 2.2 色散材料（辅助微分方程 ADE）

Drude-Lorentz 色散介质极化密度 $\mathbf{P}$ 满足二阶 ODE：

$$\frac{\partial^2 \mathbf{P}}{\partial t^2} + \gamma \frac{\partial \mathbf{P}}{\partial t} + \omega_0^2 \mathbf{P} = \varepsilon_0 \omega_p^2 \mathbf{E}$$

其中 $\omega_0$ 为共振频率，$\gamma$ 为阻尼率，$\omega_p$ 为等离子频率。$\mathbf{D}=\varepsilon_0\varepsilon_\infty\mathbf{E}+\mathbf{P}$，代入 Maxwell 旋度方程得 ADE-FDTD 更新格式（Lumerical MCM、Tidy3D PoleResidue 共同方案）。多系数材料 MCM 通过加和多个 Lorentz 极点拟合实测 $n(\omega)$ 数据。

### 2.3 非线性（Kerr + 拉曼）

三阶非线性 $\mathbf{P}_{NL}=\varepsilon_0\chi^{(3)}|\mathbf{E}|^2\mathbf{E}$（瞬时 Kerr）+ 卷积拉曼项，ADE 法处理。光子芯片中典型应用为 SiN 微环的克尔自相位调制、LNOI 的 $\chi^{(2)}$ 二次谐波。

---

## 3. Yee 网格离散化方案

### 3.1 Yee 1966 网格布局

3D Yee 单元中：电场分量 $E_x,E_y,E_z$ 位于棱中点，磁场分量 $H_x,H_y,H_z$ 位于面中心，空间半步错位。该布局使每个旋度运算的中心差分天然落在被求场位置，二阶精度 $O(\Delta h^2)$，且离散 Gauss 定律 $\nabla_h\cdot(\nabla_h\times\cdot)\equiv 0$ 自动满足（避免非物理电荷积累）。Yee 网格是 FDE/FDFD/FDTD/2.5D-FDTD 共同基础（ALGORITHMS.md 附录 C）。

### 3.2 E/H leapfrog 时间推进

时间半步错位，磁场在 $n+1/2$ 时刻更新，电场在 $n+1$ 时刻更新。以 $E_z$（TEz 2D）为例：

$$H_x^{n+1/2}\big|_{i,j+1/2} = D_{a,\mu}\, H_x^{n-1/2}\big|_{i,j+1/2} - D_{b,\mu}\,\frac{E_z^n|_{i,j+1}-E_z^n|_{i,j}}{\Delta y}$$

$$H_y^{n+1/2}\big|_{i+1/2,j} = D_{a,\mu}\, H_y^{n-1/2}\big|_{i+1/2,j} + D_{b,\mu}\,\frac{E_z^n|_{i+1,j}-E_z^n|_{i,j}}{\Delta x}$$

$$E_z^{n+1}\big|_{i,j} = C_{a,\varepsilon}\, E_z^n\big|_{i,j} + C_{b,\varepsilon}\left[\frac{H_y^{n+1/2}|_{i+1/2,j}-H_y^{n+1/2}|_{i-1/2,j}}{\Delta x} - \frac{H_x^{n+1/2}|_{i,j+1/2}-H_x^{n+1/2}|_{i,j-1/2}}{\Delta y}\right]$$

其中 $D_{a,\mu}=\frac{1-\sigma_m\Delta t/(2\mu_0)}{1+\sigma_m\Delta t/(2\mu_0)}$，$D_{b,\mu}=\frac{\Delta t/\mu_0}{1+\sigma_m\Delta t/(2\mu_0)}$，$C_{a,\varepsilon}=\frac{1-\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}{1+\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}$，$C_{b,\varepsilon}=\frac{\Delta t/(\varepsilon_0\varepsilon_r)}{1+\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}$。3D 形式按 6 个分量类似展开。

### 3.3 共形网格亚像素平滑（Yu-Mittra 1# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$ 处理。

### 2.2 色散材料（辅助微分方程 ADE）

Drude-Lorentz 色散介质极化密度 $\mathbf{P}$ 满足二阶 ODE：

$$\frac{\partial^2 \mathbf{P}}{\partial t^2} + \gamma \frac{\partial \mathbf{P}}{\partial t} + \omega_0^2 \mathbf{P} = \varepsilon_0 \omega_p^2 \mathbf{E}$$

其中 $\omega_0$ 为共振频率，$\gamma$ 为阻尼率，$\omega_p$ 为等离子频率。$\mathbf{D}=\varepsilon_0\varepsilon_\infty\mathbf{E}+\mathbf{P}$，代入 Maxwell 旋度方程得 ADE-FDTD 更新格式（Lumerical MCM、Tidy3D PoleResidue 共同方案）。多系数材料 MCM 通过加和多个 Lorentz 极点拟合实测 $n(\omega)$ 数据。

### 2.3 非线性（Kerr + 拉曼）

三阶非线性 $\mathbf{P}_{NL}=\varepsilon_0\chi^{(3)}|\mathbf{E}|^2\mathbf{E}$（瞬时 Kerr）+ 卷积拉曼项，ADE 法处理。光子芯片中典型应用为 SiN 微环的克尔自相位调制、LNOI 的 $\chi^{(2)}$ 二次谐波。

---

## 3. Yee 网格离散化方案

### 3.1 Yee 1966 网格布局

3D Yee 单元中：电场分量 $E_x,E_y,E_z$ 位于棱中点，磁场分量 $H_x,H_y,H_z$ 位于面中心，空间半步错位。该布局使每个旋度运算的中心差分天然落在被求场位置，二阶精度 $O(\Delta h^2)$，且离散 Gauss 定律 $\nabla_h\cdot(\nabla_h\times\cdot)\equiv 0$ 自动满足（避免非物理电荷积累）。Yee 网格是 FDE/FDFD/FDTD/2.5D-FDTD 共同基础（ALGORITHMS.md 附录 C）。

### 3.2 E/H leapfrog 时间推进

时间半步错位，磁场在 $n+1/2$ 时刻更新，电场在 $n+1$ 时刻更新。以 $E_z$（TEz 2D）为例：

$$H_x^{n+1/2}\big|_{i,j+1/2} = D_{a,\mu}\, H_x^{n-1/2}\big|_{i,j+1/2} - D_{b,\mu}\,\frac{E_z^n|_{i,j+1}-E_z^n|_{i,j}}{\Delta y}$$

$$H_y^{n+1/2}\big|_{i+1/2,j} = D_{a,\mu}\, H_y^{n-1/2}\big|_{i+1/2,j} + D_{b,\mu}\,\frac{E_z^n|_{i+1,j}-E_z^n|_{i,j}}{\Delta x}$$

$$E_z^{n+1}\big|_{i,j} = C_{a,\varepsilon}\, E_z^n\big|_{i,j} + C_{b,\varepsilon}\left[\frac{H_y^{n+1/2}|_{i+1/2,j}-H_y^{n+1/2}|_{i-1/2,j}}{\Delta x} - \frac{H_x^{n+1/2}|_{i,j+1/2}-H_x^{n+1/2}|_{i,j-1/2}}{\Delta y}\right]$$

其中 $D_{a,\mu}=\frac{1-\sigma_m\Delta t/(2\mu_0)}{1+\sigma_m\Delta t/(2\mu_0)}$，$D_{b,\mu}=\frac{\Delta t/\mu_0}{1+\sigma_m\Delta t/(2\mu_0)}$，$C_{a,\varepsilon}=\frac{1-\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}{1+\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}$，$C_{b,\varepsilon}=\frac{\Delta t/(\varepsilon_0\varepsilon_r)}{1+\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}$。3D 形式按 6 个分量类似展开。

### 3.3 共形网格亚像素平滑（Yu-Mittra 1/2、Volume-Average）

阶梯近似在# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$ 处理。

### 2.2 色散材料（辅助微分方程 ADE）

Drude-Lorentz 色散介质极化密度 $\mathbf{P}$ 满足二阶 ODE：

$$\frac{\partial^2 \mathbf{P}}{\partial t^2} + \gamma \frac{\partial \mathbf{P}}{\partial t} + \omega_0^2 \mathbf{P} = \varepsilon_0 \omega_p^2 \mathbf{E}$$

其中 $\omega_0$ 为共振频率，$\gamma$ 为阻尼率，$\omega_p$ 为等离子频率。$\mathbf{D}=\varepsilon_0\varepsilon_\infty\mathbf{E}+\mathbf{P}$，代入 Maxwell 旋度方程得 ADE-FDTD 更新格式（Lumerical MCM、Tidy3D PoleResidue 共同方案）。多系数材料 MCM 通过加和多个 Lorentz 极点拟合实测 $n(\omega)$ 数据。

### 2.3 非线性（Kerr + 拉曼）

三阶非线性 $\mathbf{P}_{NL}=\varepsilon_0\chi^{(3)}|\mathbf{E}|^2\mathbf{E}$（瞬时 Kerr）+ 卷积拉曼项，ADE 法处理。光子芯片中典型应用为 SiN 微环的克尔自相位调制、LNOI 的 $\chi^{(2)}$ 二次谐波。

---

## 3. Yee 网格离散化方案

### 3.1 Yee 1966 网格布局

3D Yee 单元中：电场分量 $E_x,E_y,E_z$ 位于棱中点，磁场分量 $H_x,H_y,H_z$ 位于面中心，空间半步错位。该布局使每个旋度运算的中心差分天然落在被求场位置，二阶精度 $O(\Delta h^2)$，且离散 Gauss 定律 $\nabla_h\cdot(\nabla_h\times\cdot)\equiv 0$ 自动满足（避免非物理电荷积累）。Yee 网格是 FDE/FDFD/FDTD/2.5D-FDTD 共同基础（ALGORITHMS.md 附录 C）。

### 3.2 E/H leapfrog 时间推进

时间半步错位，磁场在 $n+1/2$ 时刻更新，电场在 $n+1$ 时刻更新。以 $E_z$（TEz 2D）为例：

$$H_x^{n+1/2}\big|_{i,j+1/2} = D_{a,\mu}\, H_x^{n-1/2}\big|_{i,j+1/2} - D_{b,\mu}\,\frac{E_z^n|_{i,j+1}-E_z^n|_{i,j}}{\Delta y}$$

$$H_y^{n+1/2}\big|_{i+1/2,j} = D_{a,\mu}\, H_y^{n-1/2}\big|_{i+1/2,j} + D_{b,\mu}\,\frac{E_z^n|_{i+1,j}-E_z^n|_{i,j}}{\Delta x}$$

$$E_z^{n+1}\big|_{i,j} = C_{a,\varepsilon}\, E_z^n\big|_{i,j} + C_{b,\varepsilon}\left[\frac{H_y^{n+1/2}|_{i+1/2,j}-H_y^{n+1/2}|_{i-1/2,j}}{\Delta x} - \frac{H_x^{n+1/2}|_{i,j+1/2}-H_x^{n+1/2}|_{i,j-1/2}}{\Delta y}\right]$$

其中 $D_{a,\mu}=\frac{1-\sigma_m\Delta t/(2\mu_0)}{1+\sigma_m\Delta t/(2\mu_0)}$，$D_{b,\mu}=\frac{\Delta t/\mu_0}{1+\sigma_m\Delta t/(2\mu_0)}$，$C_{a,\varepsilon}=\frac{1-\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}{1+\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}$，$C_{b,\varepsilon}=\frac{\Delta t/(\varepsilon_0\varepsilon_r)}{1+\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}$。3D 形式按 6 个分量类似展开。

### 3.3 共形网格亚像素平滑（Yu-Mittra 1/2、Volume-Average）

阶梯近似在介质界面产生 $O(\Delta h)$ 误差。Yu-Mittra 1/2# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$ 处理。

### 2.2 色散材料（辅助微分方程 ADE）

Drude-Lorentz 色散介质极化密度 $\mathbf{P}$ 满足二阶 ODE：

$$\frac{\partial^2 \mathbf{P}}{\partial t^2} + \gamma \frac{\partial \mathbf{P}}{\partial t} + \omega_0^2 \mathbf{P} = \varepsilon_0 \omega_p^2 \mathbf{E}$$

其中 $\omega_0$ 为共振频率，$\gamma$ 为阻尼率，$\omega_p$ 为等离子频率。$\mathbf{D}=\varepsilon_0\varepsilon_\infty\mathbf{E}+\mathbf{P}$，代入 Maxwell 旋度方程得 ADE-FDTD 更新格式（Lumerical MCM、Tidy3D PoleResidue 共同方案）。多系数材料 MCM 通过加和多个 Lorentz 极点拟合实测 $n(\omega)$ 数据。

### 2.3 非线性（Kerr + 拉曼）

三阶非线性 $\mathbf{P}_{NL}=\varepsilon_0\chi^{(3)}|\mathbf{E}|^2\mathbf{E}$（瞬时 Kerr）+ 卷积拉曼项，ADE 法处理。光子芯片中典型应用为 SiN 微环的克尔自相位调制、LNOI 的 $\chi^{(2)}$ 二次谐波。

---

## 3. Yee 网格离散化方案

### 3.1 Yee 1966 网格布局

3D Yee 单元中：电场分量 $E_x,E_y,E_z$ 位于棱中点，磁场分量 $H_x,H_y,H_z$ 位于面中心，空间半步错位。该布局使每个旋度运算的中心差分天然落在被求场位置，二阶精度 $O(\Delta h^2)$，且离散 Gauss 定律 $\nabla_h\cdot(\nabla_h\times\cdot)\equiv 0$ 自动满足（避免非物理电荷积累）。Yee 网格是 FDE/FDFD/FDTD/2.5D-FDTD 共同基础（ALGORITHMS.md 附录 C）。

### 3.2 E/H leapfrog 时间推进

时间半步错位，磁场在 $n+1/2$ 时刻更新，电场在 $n+1$ 时刻更新。以 $E_z$（TEz 2D）为例：

$$H_x^{n+1/2}\big|_{i,j+1/2} = D_{a,\mu}\, H_x^{n-1/2}\big|_{i,j+1/2} - D_{b,\mu}\,\frac{E_z^n|_{i,j+1}-E_z^n|_{i,j}}{\Delta y}$$

$$H_y^{n+1/2}\big|_{i+1/2,j} = D_{a,\mu}\, H_y^{n-1/2}\big|_{i+1/2,j} + D_{b,\mu}\,\frac{E_z^n|_{i+1,j}-E_z^n|_{i,j}}{\Delta x}$$

$$E_z^{n+1}\big|_{i,j} = C_{a,\varepsilon}\, E_z^n\big|_{i,j} + C_{b,\varepsilon}\left[\frac{H_y^{n+1/2}|_{i+1/2,j}-H_y^{n+1/2}|_{i-1/2,j}}{\Delta x} - \frac{H_x^{n+1/2}|_{i,j+1/2}-H_x^{n+1/2}|_{i,j-1/2}}{\Delta y}\right]$$

其中 $D_{a,\mu}=\frac{1-\sigma_m\Delta t/(2\mu_0)}{1+\sigma_m\Delta t/(2\mu_0)}$，$D_{b,\mu}=\frac{\Delta t/\mu_0}{1+\sigma_m\Delta t/(2\mu_0)}$，$C_{a,\varepsilon}=\frac{1-\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}{1+\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}$，$C_{b,\varepsilon}=\frac{\Delta t/(\varepsilon_0\varepsilon_r)}{1+\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}$。3D 形式按 6 个分量类似展开。

### 3.3 共形网格亚像素平滑（Yu-Mittra 1/2、Volume-Average）

阶梯近似在介质界面产生 $O(\Delta h)$ 误差。Yu-Mittra 1/2 共形方案：在 Yee 棱上的# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$ 处理。

### 2.2 色散材料（辅助微分方程 ADE）

Drude-Lorentz 色散介质极化密度 $\mathbf{P}$ 满足二阶 ODE：

$$\frac{\partial^2 \mathbf{P}}{\partial t^2} + \gamma \frac{\partial \mathbf{P}}{\partial t} + \omega_0^2 \mathbf{P} = \varepsilon_0 \omega_p^2 \mathbf{E}$$

其中 $\omega_0$ 为共振频率，$\gamma$ 为阻尼率，$\omega_p$ 为等离子频率。$\mathbf{D}=\varepsilon_0\varepsilon_\infty\mathbf{E}+\mathbf{P}$，代入 Maxwell 旋度方程得 ADE-FDTD 更新格式（Lumerical MCM、Tidy3D PoleResidue 共同方案）。多系数材料 MCM 通过加和多个 Lorentz 极点拟合实测 $n(\omega)$ 数据。

### 2.3 非线性（Kerr + 拉曼）

三阶非线性 $\mathbf{P}_{NL}=\varepsilon_0\chi^{(3)}|\mathbf{E}|^2\mathbf{E}$（瞬时 Kerr）+ 卷积拉曼项，ADE 法处理。光子芯片中典型应用为 SiN 微环的克尔自相位调制、LNOI 的 $\chi^{(2)}$ 二次谐波。

---

## 3. Yee 网格离散化方案

### 3.1 Yee 1966 网格布局

3D Yee 单元中：电场分量 $E_x,E_y,E_z$ 位于棱中点，磁场分量 $H_x,H_y,H_z$ 位于面中心，空间半步错位。该布局使每个旋度运算的中心差分天然落在被求场位置，二阶精度 $O(\Delta h^2)$，且离散 Gauss 定律 $\nabla_h\cdot(\nabla_h\times\cdot)\equiv 0$ 自动满足（避免非物理电荷积累）。Yee 网格是 FDE/FDFD/FDTD/2.5D-FDTD 共同基础（ALGORITHMS.md 附录 C）。

### 3.2 E/H leapfrog 时间推进

时间半步错位，磁场在 $n+1/2$ 时刻更新，电场在 $n+1$ 时刻更新。以 $E_z$（TEz 2D）为例：

$$H_x^{n+1/2}\big|_{i,j+1/2} = D_{a,\mu}\, H_x^{n-1/2}\big|_{i,j+1/2} - D_{b,\mu}\,\frac{E_z^n|_{i,j+1}-E_z^n|_{i,j}}{\Delta y}$$

$$H_y^{n+1/2}\big|_{i+1/2,j} = D_{a,\mu}\, H_y^{n-1/2}\big|_{i+1/2,j} + D_{b,\mu}\,\frac{E_z^n|_{i+1,j}-E_z^n|_{i,j}}{\Delta x}$$

$$E_z^{n+1}\big|_{i,j} = C_{a,\varepsilon}\, E_z^n\big|_{i,j} + C_{b,\varepsilon}\left[\frac{H_y^{n+1/2}|_{i+1/2,j}-H_y^{n+1/2}|_{i-1/2,j}}{\Delta x} - \frac{H_x^{n+1/2}|_{i,j+1/2}-H_x^{n+1/2}|_{i,j-1/2}}{\Delta y}\right]$$

其中 $D_{a,\mu}=\frac{1-\sigma_m\Delta t/(2\mu_0)}{1+\sigma_m\Delta t/(2\mu_0)}$，$D_{b,\mu}=\frac{\Delta t/\mu_0}{1+\sigma_m\Delta t/(2\mu_0)}$，$C_{a,\varepsilon}=\frac{1-\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}{1+\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}$，$C_{b,\varepsilon}=\frac{\Delta t/(\varepsilon_0\varepsilon_r)}{1+\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}$。3D 形式按 6 个分量类似展开。

### 3.3 共形网格亚像素平滑（Yu-Mittra 1/2、Volume-Average）

阶梯近似在介质界面产生 $O(\Delta h)$ 误差。Yu-Mittra 1/2 共形方案：在 Yee 棱上的等效介电常数取界面两侧的体积加权# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$ 处理。

### 2.2 色散材料（辅助微分方程 ADE）

Drude-Lorentz 色散介质极化密度 $\mathbf{P}$ 满足二阶 ODE：

$$\frac{\partial^2 \mathbf{P}}{\partial t^2} + \gamma \frac{\partial \mathbf{P}}{\partial t} + \omega_0^2 \mathbf{P} = \varepsilon_0 \omega_p^2 \mathbf{E}$$

其中 $\omega_0$ 为共振频率，$\gamma$ 为阻尼率，$\omega_p$ 为等离子频率。$\mathbf{D}=\varepsilon_0\varepsilon_\infty\mathbf{E}+\mathbf{P}$，代入 Maxwell 旋度方程得 ADE-FDTD 更新格式（Lumerical MCM、Tidy3D PoleResidue 共同方案）。多系数材料 MCM 通过加和多个 Lorentz 极点拟合实测 $n(\omega)$ 数据。

### 2.3 非线性（Kerr + 拉曼）

三阶非线性 $\mathbf{P}_{NL}=\varepsilon_0\chi^{(3)}|\mathbf{E}|^2\mathbf{E}$（瞬时 Kerr）+ 卷积拉曼项，ADE 法处理。光子芯片中典型应用为 SiN 微环的克尔自相位调制、LNOI 的 $\chi^{(2)}$ 二次谐波。

---

## 3. Yee 网格离散化方案

### 3.1 Yee 1966 网格布局

3D Yee 单元中：电场分量 $E_x,E_y,E_z$ 位于棱中点，磁场分量 $H_x,H_y,H_z$ 位于面中心，空间半步错位。该布局使每个旋度运算的中心差分天然落在被求场位置，二阶精度 $O(\Delta h^2)$，且离散 Gauss 定律 $\nabla_h\cdot(\nabla_h\times\cdot)\equiv 0$ 自动满足（避免非物理电荷积累）。Yee 网格是 FDE/FDFD/FDTD/2.5D-FDTD 共同基础（ALGORITHMS.md 附录 C）。

### 3.2 E/H leapfrog 时间推进

时间半步错位，磁场在 $n+1/2$ 时刻更新，电场在 $n+1$ 时刻更新。以 $E_z$（TEz 2D）为例：

$$H_x^{n+1/2}\big|_{i,j+1/2} = D_{a,\mu}\, H_x^{n-1/2}\big|_{i,j+1/2} - D_{b,\mu}\,\frac{E_z^n|_{i,j+1}-E_z^n|_{i,j}}{\Delta y}$$

$$H_y^{n+1/2}\big|_{i+1/2,j} = D_{a,\mu}\, H_y^{n-1/2}\big|_{i+1/2,j} + D_{b,\mu}\,\frac{E_z^n|_{i+1,j}-E_z^n|_{i,j}}{\Delta x}$$

$$E_z^{n+1}\big|_{i,j} = C_{a,\varepsilon}\, E_z^n\big|_{i,j} + C_{b,\varepsilon}\left[\frac{H_y^{n+1/2}|_{i+1/2,j}-H_y^{n+1/2}|_{i-1/2,j}}{\Delta x} - \frac{H_x^{n+1/2}|_{i,j+1/2}-H_x^{n+1/2}|_{i,j-1/2}}{\Delta y}\right]$$

其中 $D_{a,\mu}=\frac{1-\sigma_m\Delta t/(2\mu_0)}{1+\sigma_m\Delta t/(2\mu_0)}$，$D_{b,\mu}=\frac{\Delta t/\mu_0}{1+\sigma_m\Delta t/(2\mu_0)}$，$C_{a,\varepsilon}=\frac{1-\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}{1+\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}$，$C_{b,\varepsilon}=\frac{\Delta t/(\varepsilon_0\varepsilon_r)}{1+\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}$。3D 形式按 6 个分量类似展开。

### 3.3 共形网格亚像素平滑（Yu-Mittra 1/2、Volume-Average）

阶梯近似在介质界面产生 $O(\Delta h)$ 误差。Yu-Mittra 1/2 共形方案：在 Yee 棱上的等效介电常数取界面两侧的体积加权平均，使界面处的等效 $\varepsilon# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$ 处理。

### 2.2 色散材料（辅助微分方程 ADE）

Drude-Lorentz 色散介质极化密度 $\mathbf{P}$ 满足二阶 ODE：

$$\frac{\partial^2 \mathbf{P}}{\partial t^2} + \gamma \frac{\partial \mathbf{P}}{\partial t} + \omega_0^2 \mathbf{P} = \varepsilon_0 \omega_p^2 \mathbf{E}$$

其中 $\omega_0$ 为共振频率，$\gamma$ 为阻尼率，$\omega_p$ 为等离子频率。$\mathbf{D}=\varepsilon_0\varepsilon_\infty\mathbf{E}+\mathbf{P}$，代入 Maxwell 旋度方程得 ADE-FDTD 更新格式（Lumerical MCM、Tidy3D PoleResidue 共同方案）。多系数材料 MCM 通过加和多个 Lorentz 极点拟合实测 $n(\omega)$ 数据。

### 2.3 非线性（Kerr + 拉曼）

三阶非线性 $\mathbf{P}_{NL}=\varepsilon_0\chi^{(3)}|\mathbf{E}|^2\mathbf{E}$（瞬时 Kerr）+ 卷积拉曼项，ADE 法处理。光子芯片中典型应用为 SiN 微环的克尔自相位调制、LNOI 的 $\chi^{(2)}$ 二次谐波。

---

## 3. Yee 网格离散化方案

### 3.1 Yee 1966 网格布局

3D Yee 单元中：电场分量 $E_x,E_y,E_z$ 位于棱中点，磁场分量 $H_x,H_y,H_z$ 位于面中心，空间半步错位。该布局使每个旋度运算的中心差分天然落在被求场位置，二阶精度 $O(\Delta h^2)$，且离散 Gauss 定律 $\nabla_h\cdot(\nabla_h\times\cdot)\equiv 0$ 自动满足（避免非物理电荷积累）。Yee 网格是 FDE/FDFD/FDTD/2.5D-FDTD 共同基础（ALGORITHMS.md 附录 C）。

### 3.2 E/H leapfrog 时间推进

时间半步错位，磁场在 $n+1/2$ 时刻更新，电场在 $n+1$ 时刻更新。以 $E_z$（TEz 2D）为例：

$$H_x^{n+1/2}\big|_{i,j+1/2} = D_{a,\mu}\, H_x^{n-1/2}\big|_{i,j+1/2} - D_{b,\mu}\,\frac{E_z^n|_{i,j+1}-E_z^n|_{i,j}}{\Delta y}$$

$$H_y^{n+1/2}\big|_{i+1/2,j} = D_{a,\mu}\, H_y^{n-1/2}\big|_{i+1/2,j} + D_{b,\mu}\,\frac{E_z^n|_{i+1,j}-E_z^n|_{i,j}}{\Delta x}$$

$$E_z^{n+1}\big|_{i,j} = C_{a,\varepsilon}\, E_z^n\big|_{i,j} + C_{b,\varepsilon}\left[\frac{H_y^{n+1/2}|_{i+1/2,j}-H_y^{n+1/2}|_{i-1/2,j}}{\Delta x} - \frac{H_x^{n+1/2}|_{i,j+1/2}-H_x^{n+1/2}|_{i,j-1/2}}{\Delta y}\right]$$

其中 $D_{a,\mu}=\frac{1-\sigma_m\Delta t/(2\mu_0)}{1+\sigma_m\Delta t/(2\mu_0)}$，$D_{b,\mu}=\frac{\Delta t/\mu_0}{1+\sigma_m\Delta t/(2\mu_0)}$，$C_{a,\varepsilon}=\frac{1-\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}{1+\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}$，$C_{b,\varepsilon}=\frac{\Delta t/(\varepsilon_0\varepsilon_r)}{1+\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}$。3D 形式按 6 个分量类似展开。

### 3.3 共形网格亚像素平滑（Yu-Mittra 1/2、Volume-Average）

阶梯近似在介质界面产生 $O(\Delta h)$ 误差。Yu-Mittra 1/2 共形方案：在 Yee 棱上的等效介电常数取界面两侧的体积加权平均，使界面处的等效 $\varepsilon$ 接近真实积分形式，误差降至# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$ 处理。

### 2.2 色散材料（辅助微分方程 ADE）

Drude-Lorentz 色散介质极化密度 $\mathbf{P}$ 满足二阶 ODE：

$$\frac{\partial^2 \mathbf{P}}{\partial t^2} + \gamma \frac{\partial \mathbf{P}}{\partial t} + \omega_0^2 \mathbf{P} = \varepsilon_0 \omega_p^2 \mathbf{E}$$

其中 $\omega_0$ 为共振频率，$\gamma$ 为阻尼率，$\omega_p$ 为等离子频率。$\mathbf{D}=\varepsilon_0\varepsilon_\infty\mathbf{E}+\mathbf{P}$，代入 Maxwell 旋度方程得 ADE-FDTD 更新格式（Lumerical MCM、Tidy3D PoleResidue 共同方案）。多系数材料 MCM 通过加和多个 Lorentz 极点拟合实测 $n(\omega)$ 数据。

### 2.3 非线性（Kerr + 拉曼）

三阶非线性 $\mathbf{P}_{NL}=\varepsilon_0\chi^{(3)}|\mathbf{E}|^2\mathbf{E}$（瞬时 Kerr）+ 卷积拉曼项，ADE 法处理。光子芯片中典型应用为 SiN 微环的克尔自相位调制、LNOI 的 $\chi^{(2)}$ 二次谐波。

---

## 3. Yee 网格离散化方案

### 3.1 Yee 1966 网格布局

3D Yee 单元中：电场分量 $E_x,E_y,E_z$ 位于棱中点，磁场分量 $H_x,H_y,H_z$ 位于面中心，空间半步错位。该布局使每个旋度运算的中心差分天然落在被求场位置，二阶精度 $O(\Delta h^2)$，且离散 Gauss 定律 $\nabla_h\cdot(\nabla_h\times\cdot)\equiv 0$ 自动满足（避免非物理电荷积累）。Yee 网格是 FDE/FDFD/FDTD/2.5D-FDTD 共同基础（ALGORITHMS.md 附录 C）。

### 3.2 E/H leapfrog 时间推进

时间半步错位，磁场在 $n+1/2$ 时刻更新，电场在 $n+1$ 时刻更新。以 $E_z$（TEz 2D）为例：

$$H_x^{n+1/2}\big|_{i,j+1/2} = D_{a,\mu}\, H_x^{n-1/2}\big|_{i,j+1/2} - D_{b,\mu}\,\frac{E_z^n|_{i,j+1}-E_z^n|_{i,j}}{\Delta y}$$

$$H_y^{n+1/2}\big|_{i+1/2,j} = D_{a,\mu}\, H_y^{n-1/2}\big|_{i+1/2,j} + D_{b,\mu}\,\frac{E_z^n|_{i+1,j}-E_z^n|_{i,j}}{\Delta x}$$

$$E_z^{n+1}\big|_{i,j} = C_{a,\varepsilon}\, E_z^n\big|_{i,j} + C_{b,\varepsilon}\left[\frac{H_y^{n+1/2}|_{i+1/2,j}-H_y^{n+1/2}|_{i-1/2,j}}{\Delta x} - \frac{H_x^{n+1/2}|_{i,j+1/2}-H_x^{n+1/2}|_{i,j-1/2}}{\Delta y}\right]$$

其中 $D_{a,\mu}=\frac{1-\sigma_m\Delta t/(2\mu_0)}{1+\sigma_m\Delta t/(2\mu_0)}$，$D_{b,\mu}=\frac{\Delta t/\mu_0}{1+\sigma_m\Delta t/(2\mu_0)}$，$C_{a,\varepsilon}=\frac{1-\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}{1+\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}$，$C_{b,\varepsilon}=\frac{\Delta t/(\varepsilon_0\varepsilon_r)}{1+\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}$。3D 形式按 6 个分量类似展开。

### 3.3 共形网格亚像素平滑（Yu-Mittra 1/2、Volume-Average）

阶梯近似在介质界面产生 $O(\Delta h)$ 误差。Yu-Mittra 1/2 共形方案：在 Yee 棱上的等效介电常数取界面两侧的体积加权平均，使界面处的等效 $\varepsilon$ 接近真实积分形式，误差降至 $O(\Delta h^2)$。Lumerical Conformal Variant 0/1/2 在介质/金属/PEC 界# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$ 处理。

### 2.2 色散材料（辅助微分方程 ADE）

Drude-Lorentz 色散介质极化密度 $\mathbf{P}$ 满足二阶 ODE：

$$\frac{\partial^2 \mathbf{P}}{\partial t^2} + \gamma \frac{\partial \mathbf{P}}{\partial t} + \omega_0^2 \mathbf{P} = \varepsilon_0 \omega_p^2 \mathbf{E}$$

其中 $\omega_0$ 为共振频率，$\gamma$ 为阻尼率，$\omega_p$ 为等离子频率。$\mathbf{D}=\varepsilon_0\varepsilon_\infty\mathbf{E}+\mathbf{P}$，代入 Maxwell 旋度方程得 ADE-FDTD 更新格式（Lumerical MCM、Tidy3D PoleResidue 共同方案）。多系数材料 MCM 通过加和多个 Lorentz 极点拟合实测 $n(\omega)$ 数据。

### 2.3 非线性（Kerr + 拉曼）

三阶非线性 $\mathbf{P}_{NL}=\varepsilon_0\chi^{(3)}|\mathbf{E}|^2\mathbf{E}$（瞬时 Kerr）+ 卷积拉曼项，ADE 法处理。光子芯片中典型应用为 SiN 微环的克尔自相位调制、LNOI 的 $\chi^{(2)}$ 二次谐波。

---

## 3. Yee 网格离散化方案

### 3.1 Yee 1966 网格布局

3D Yee 单元中：电场分量 $E_x,E_y,E_z$ 位于棱中点，磁场分量 $H_x,H_y,H_z$ 位于面中心，空间半步错位。该布局使每个旋度运算的中心差分天然落在被求场位置，二阶精度 $O(\Delta h^2)$，且离散 Gauss 定律 $\nabla_h\cdot(\nabla_h\times\cdot)\equiv 0$ 自动满足（避免非物理电荷积累）。Yee 网格是 FDE/FDFD/FDTD/2.5D-FDTD 共同基础（ALGORITHMS.md 附录 C）。

### 3.2 E/H leapfrog 时间推进

时间半步错位，磁场在 $n+1/2$ 时刻更新，电场在 $n+1$ 时刻更新。以 $E_z$（TEz 2D）为例：

$$H_x^{n+1/2}\big|_{i,j+1/2} = D_{a,\mu}\, H_x^{n-1/2}\big|_{i,j+1/2} - D_{b,\mu}\,\frac{E_z^n|_{i,j+1}-E_z^n|_{i,j}}{\Delta y}$$

$$H_y^{n+1/2}\big|_{i+1/2,j} = D_{a,\mu}\, H_y^{n-1/2}\big|_{i+1/2,j} + D_{b,\mu}\,\frac{E_z^n|_{i+1,j}-E_z^n|_{i,j}}{\Delta x}$$

$$E_z^{n+1}\big|_{i,j} = C_{a,\varepsilon}\, E_z^n\big|_{i,j} + C_{b,\varepsilon}\left[\frac{H_y^{n+1/2}|_{i+1/2,j}-H_y^{n+1/2}|_{i-1/2,j}}{\Delta x} - \frac{H_x^{n+1/2}|_{i,j+1/2}-H_x^{n+1/2}|_{i,j-1/2}}{\Delta y}\right]$$

其中 $D_{a,\mu}=\frac{1-\sigma_m\Delta t/(2\mu_0)}{1+\sigma_m\Delta t/(2\mu_0)}$，$D_{b,\mu}=\frac{\Delta t/\mu_0}{1+\sigma_m\Delta t/(2\mu_0)}$，$C_{a,\varepsilon}=\frac{1-\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}{1+\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}$，$C_{b,\varepsilon}=\frac{\Delta t/(\varepsilon_0\varepsilon_r)}{1+\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}$。3D 形式按 6 个分量类似展开。

### 3.3 共形网格亚像素平滑（Yu-Mittra 1/2、Volume-Average）

阶梯近似在介质界面产生 $O(\Delta h)$ 误差。Yu-Mittra 1/2 共形方案：在 Yee 棱上的等效介电常数取界面两侧的体积加权平均，使界面处的等效 $\varepsilon$ 接近真实积分形式，误差降至 $O(\Delta h^2)$。Lumerical Conformal Variant 0/1/2 在介质/金属/PEC 界面分别采用不同共形规则；Tidy3D 默认开启 subpixel averaging。PoLaRIS 将实现 Volume-Average + Yu# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$ 处理。

### 2.2 色散材料（辅助微分方程 ADE）

Drude-Lorentz 色散介质极化密度 $\mathbf{P}$ 满足二阶 ODE：

$$\frac{\partial^2 \mathbf{P}}{\partial t^2} + \gamma \frac{\partial \mathbf{P}}{\partial t} + \omega_0^2 \mathbf{P} = \varepsilon_0 \omega_p^2 \mathbf{E}$$

其中 $\omega_0$ 为共振频率，$\gamma$ 为阻尼率，$\omega_p$ 为等离子频率。$\mathbf{D}=\varepsilon_0\varepsilon_\infty\mathbf{E}+\mathbf{P}$，代入 Maxwell 旋度方程得 ADE-FDTD 更新格式（Lumerical MCM、Tidy3D PoleResidue 共同方案）。多系数材料 MCM 通过加和多个 Lorentz 极点拟合实测 $n(\omega)$ 数据。

### 2.3 非线性（Kerr + 拉曼）

三阶非线性 $\mathbf{P}_{NL}=\varepsilon_0\chi^{(3)}|\mathbf{E}|^2\mathbf{E}$（瞬时 Kerr）+ 卷积拉曼项，ADE 法处理。光子芯片中典型应用为 SiN 微环的克尔自相位调制、LNOI 的 $\chi^{(2)}$ 二次谐波。

---

## 3. Yee 网格离散化方案

### 3.1 Yee 1966 网格布局

3D Yee 单元中：电场分量 $E_x,E_y,E_z$ 位于棱中点，磁场分量 $H_x,H_y,H_z$ 位于面中心，空间半步错位。该布局使每个旋度运算的中心差分天然落在被求场位置，二阶精度 $O(\Delta h^2)$，且离散 Gauss 定律 $\nabla_h\cdot(\nabla_h\times\cdot)\equiv 0$ 自动满足（避免非物理电荷积累）。Yee 网格是 FDE/FDFD/FDTD/2.5D-FDTD 共同基础（ALGORITHMS.md 附录 C）。

### 3.2 E/H leapfrog 时间推进

时间半步错位，磁场在 $n+1/2$ 时刻更新，电场在 $n+1$ 时刻更新。以 $E_z$（TEz 2D）为例：

$$H_x^{n+1/2}\big|_{i,j+1/2} = D_{a,\mu}\, H_x^{n-1/2}\big|_{i,j+1/2} - D_{b,\mu}\,\frac{E_z^n|_{i,j+1}-E_z^n|_{i,j}}{\Delta y}$$

$$H_y^{n+1/2}\big|_{i+1/2,j} = D_{a,\mu}\, H_y^{n-1/2}\big|_{i+1/2,j} + D_{b,\mu}\,\frac{E_z^n|_{i+1,j}-E_z^n|_{i,j}}{\Delta x}$$

$$E_z^{n+1}\big|_{i,j} = C_{a,\varepsilon}\, E_z^n\big|_{i,j} + C_{b,\varepsilon}\left[\frac{H_y^{n+1/2}|_{i+1/2,j}-H_y^{n+1/2}|_{i-1/2,j}}{\Delta x} - \frac{H_x^{n+1/2}|_{i,j+1/2}-H_x^{n+1/2}|_{i,j-1/2}}{\Delta y}\right]$$

其中 $D_{a,\mu}=\frac{1-\sigma_m\Delta t/(2\mu_0)}{1+\sigma_m\Delta t/(2\mu_0)}$，$D_{b,\mu}=\frac{\Delta t/\mu_0}{1+\sigma_m\Delta t/(2\mu_0)}$，$C_{a,\varepsilon}=\frac{1-\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}{1+\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}$，$C_{b,\varepsilon}=\frac{\Delta t/(\varepsilon_0\varepsilon_r)}{1+\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}$。3D 形式按 6 个分量类似展开。

### 3.3 共形网格亚像素平滑（Yu-Mittra 1/2、Volume-Average）

阶梯近似在介质界面产生 $O(\Delta h)$ 误差。Yu-Mittra 1/2 共形方案：在 Yee 棱上的等效介电常数取界面两侧的体积加权平均，使界面处的等效 $\varepsilon$ 接近真实积分形式，误差降至 $O(\Delta h^2)$。Lumerical Conformal Variant 0/1/2 在介质/金属/PEC 界面分别采用不同共形规则；Tidy3D 默认开启 subpixel averaging。PoLaRIS 将实现 Volume-Average + Yu-Mittra 1/2 两种共形方案。

### 3.4 自动非# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$ 处理。

### 2.2 色散材料（辅助微分方程 ADE）

Drude-Lorentz 色散介质极化密度 $\mathbf{P}$ 满足二阶 ODE：

$$\frac{\partial^2 \mathbf{P}}{\partial t^2} + \gamma \frac{\partial \mathbf{P}}{\partial t} + \omega_0^2 \mathbf{P} = \varepsilon_0 \omega_p^2 \mathbf{E}$$

其中 $\omega_0$ 为共振频率，$\gamma$ 为阻尼率，$\omega_p$ 为等离子频率。$\mathbf{D}=\varepsilon_0\varepsilon_\infty\mathbf{E}+\mathbf{P}$，代入 Maxwell 旋度方程得 ADE-FDTD 更新格式（Lumerical MCM、Tidy3D PoleResidue 共同方案）。多系数材料 MCM 通过加和多个 Lorentz 极点拟合实测 $n(\omega)$ 数据。

### 2.3 非线性（Kerr + 拉曼）

三阶非线性 $\mathbf{P}_{NL}=\varepsilon_0\chi^{(3)}|\mathbf{E}|^2\mathbf{E}$（瞬时 Kerr）+ 卷积拉曼项，ADE 法处理。光子芯片中典型应用为 SiN 微环的克尔自相位调制、LNOI 的 $\chi^{(2)}$ 二次谐波。

---

## 3. Yee 网格离散化方案

### 3.1 Yee 1966 网格布局

3D Yee 单元中：电场分量 $E_x,E_y,E_z$ 位于棱中点，磁场分量 $H_x,H_y,H_z$ 位于面中心，空间半步错位。该布局使每个旋度运算的中心差分天然落在被求场位置，二阶精度 $O(\Delta h^2)$，且离散 Gauss 定律 $\nabla_h\cdot(\nabla_h\times\cdot)\equiv 0$ 自动满足（避免非物理电荷积累）。Yee 网格是 FDE/FDFD/FDTD/2.5D-FDTD 共同基础（ALGORITHMS.md 附录 C）。

### 3.2 E/H leapfrog 时间推进

时间半步错位，磁场在 $n+1/2$ 时刻更新，电场在 $n+1$ 时刻更新。以 $E_z$（TEz 2D）为例：

$$H_x^{n+1/2}\big|_{i,j+1/2} = D_{a,\mu}\, H_x^{n-1/2}\big|_{i,j+1/2} - D_{b,\mu}\,\frac{E_z^n|_{i,j+1}-E_z^n|_{i,j}}{\Delta y}$$

$$H_y^{n+1/2}\big|_{i+1/2,j} = D_{a,\mu}\, H_y^{n-1/2}\big|_{i+1/2,j} + D_{b,\mu}\,\frac{E_z^n|_{i+1,j}-E_z^n|_{i,j}}{\Delta x}$$

$$E_z^{n+1}\big|_{i,j} = C_{a,\varepsilon}\, E_z^n\big|_{i,j} + C_{b,\varepsilon}\left[\frac{H_y^{n+1/2}|_{i+1/2,j}-H_y^{n+1/2}|_{i-1/2,j}}{\Delta x} - \frac{H_x^{n+1/2}|_{i,j+1/2}-H_x^{n+1/2}|_{i,j-1/2}}{\Delta y}\right]$$

其中 $D_{a,\mu}=\frac{1-\sigma_m\Delta t/(2\mu_0)}{1+\sigma_m\Delta t/(2\mu_0)}$，$D_{b,\mu}=\frac{\Delta t/\mu_0}{1+\sigma_m\Delta t/(2\mu_0)}$，$C_{a,\varepsilon}=\frac{1-\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}{1+\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}$，$C_{b,\varepsilon}=\frac{\Delta t/(\varepsilon_0\varepsilon_r)}{1+\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}$。3D 形式按 6 个分量类似展开。

### 3.3 共形网格亚像素平滑（Yu-Mittra 1/2、Volume-Average）

阶梯近似在介质界面产生 $O(\Delta h)$ 误差。Yu-Mittra 1/2 共形方案：在 Yee 棱上的等效介电常数取界面两侧的体积加权平均，使界面处的等效 $\varepsilon$ 接近真实积分形式，误差降至 $O(\Delta h^2)$。Lumerical Conformal Variant 0/1/2 在介质/金属/PEC 界面分别采用不同共形规则；Tidy3D 默认开启 subpixel averaging。PoLaRIS 将实现 Volume-Average + Yu-Mittra 1/2 两种共形方案。

### 3.4 自动非均匀网格

按"每波长最少 N 个# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$ 处理。

### 2.2 色散材料（辅助微分方程 ADE）

Drude-Lorentz 色散介质极化密度 $\mathbf{P}$ 满足二阶 ODE：

$$\frac{\partial^2 \mathbf{P}}{\partial t^2} + \gamma \frac{\partial \mathbf{P}}{\partial t} + \omega_0^2 \mathbf{P} = \varepsilon_0 \omega_p^2 \mathbf{E}$$

其中 $\omega_0$ 为共振频率，$\gamma$ 为阻尼率，$\omega_p$ 为等离子频率。$\mathbf{D}=\varepsilon_0\varepsilon_\infty\mathbf{E}+\mathbf{P}$，代入 Maxwell 旋度方程得 ADE-FDTD 更新格式（Lumerical MCM、Tidy3D PoleResidue 共同方案）。多系数材料 MCM 通过加和多个 Lorentz 极点拟合实测 $n(\omega)$ 数据。

### 2.3 非线性（Kerr + 拉曼）

三阶非线性 $\mathbf{P}_{NL}=\varepsilon_0\chi^{(3)}|\mathbf{E}|^2\mathbf{E}$（瞬时 Kerr）+ 卷积拉曼项，ADE 法处理。光子芯片中典型应用为 SiN 微环的克尔自相位调制、LNOI 的 $\chi^{(2)}$ 二次谐波。

---

## 3. Yee 网格离散化方案

### 3.1 Yee 1966 网格布局

3D Yee 单元中：电场分量 $E_x,E_y,E_z$ 位于棱中点，磁场分量 $H_x,H_y,H_z$ 位于面中心，空间半步错位。该布局使每个旋度运算的中心差分天然落在被求场位置，二阶精度 $O(\Delta h^2)$，且离散 Gauss 定律 $\nabla_h\cdot(\nabla_h\times\cdot)\equiv 0$ 自动满足（避免非物理电荷积累）。Yee 网格是 FDE/FDFD/FDTD/2.5D-FDTD 共同基础（ALGORITHMS.md 附录 C）。

### 3.2 E/H leapfrog 时间推进

时间半步错位，磁场在 $n+1/2$ 时刻更新，电场在 $n+1$ 时刻更新。以 $E_z$（TEz 2D）为例：

$$H_x^{n+1/2}\big|_{i,j+1/2} = D_{a,\mu}\, H_x^{n-1/2}\big|_{i,j+1/2} - D_{b,\mu}\,\frac{E_z^n|_{i,j+1}-E_z^n|_{i,j}}{\Delta y}$$

$$H_y^{n+1/2}\big|_{i+1/2,j} = D_{a,\mu}\, H_y^{n-1/2}\big|_{i+1/2,j} + D_{b,\mu}\,\frac{E_z^n|_{i+1,j}-E_z^n|_{i,j}}{\Delta x}$$

$$E_z^{n+1}\big|_{i,j} = C_{a,\varepsilon}\, E_z^n\big|_{i,j} + C_{b,\varepsilon}\left[\frac{H_y^{n+1/2}|_{i+1/2,j}-H_y^{n+1/2}|_{i-1/2,j}}{\Delta x} - \frac{H_x^{n+1/2}|_{i,j+1/2}-H_x^{n+1/2}|_{i,j-1/2}}{\Delta y}\right]$$

其中 $D_{a,\mu}=\frac{1-\sigma_m\Delta t/(2\mu_0)}{1+\sigma_m\Delta t/(2\mu_0)}$，$D_{b,\mu}=\frac{\Delta t/\mu_0}{1+\sigma_m\Delta t/(2\mu_0)}$，$C_{a,\varepsilon}=\frac{1-\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}{1+\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}$，$C_{b,\varepsilon}=\frac{\Delta t/(\varepsilon_0\varepsilon_r)}{1+\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}$。3D 形式按 6 个分量类似展开。

### 3.3 共形网格亚像素平滑（Yu-Mittra 1/2、Volume-Average）

阶梯近似在介质界面产生 $O(\Delta h)$ 误差。Yu-Mittra 1/2 共形方案：在 Yee 棱上的等效介电常数取界面两侧的体积加权平均，使界面处的等效 $\varepsilon$ 接近真实积分形式，误差降至 $O(\Delta h^2)$。Lumerical Conformal Variant 0/1/2 在介质/金属/PEC 界面分别采用不同共形规则；Tidy3D 默认开启 subpixel averaging。PoLaRIS 将实现 Volume-Average + Yu-Mittra 1/2 两种共形方案。

### 3.4 自动非均匀网格

按"每波长最少 N 个网格"（典型 N=10~20，# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$ 处理。

### 2.2 色散材料（辅助微分方程 ADE）

Drude-Lorentz 色散介质极化密度 $\mathbf{P}$ 满足二阶 ODE：

$$\frac{\partial^2 \mathbf{P}}{\partial t^2} + \gamma \frac{\partial \mathbf{P}}{\partial t} + \omega_0^2 \mathbf{P} = \varepsilon_0 \omega_p^2 \mathbf{E}$$

其中 $\omega_0$ 为共振频率，$\gamma$ 为阻尼率，$\omega_p$ 为等离子频率。$\mathbf{D}=\varepsilon_0\varepsilon_\infty\mathbf{E}+\mathbf{P}$，代入 Maxwell 旋度方程得 ADE-FDTD 更新格式（Lumerical MCM、Tidy3D PoleResidue 共同方案）。多系数材料 MCM 通过加和多个 Lorentz 极点拟合实测 $n(\omega)$ 数据。

### 2.3 非线性（Kerr + 拉曼）

三阶非线性 $\mathbf{P}_{NL}=\varepsilon_0\chi^{(3)}|\mathbf{E}|^2\mathbf{E}$（瞬时 Kerr）+ 卷积拉曼项，ADE 法处理。光子芯片中典型应用为 SiN 微环的克尔自相位调制、LNOI 的 $\chi^{(2)}$ 二次谐波。

---

## 3. Yee 网格离散化方案

### 3.1 Yee 1966 网格布局

3D Yee 单元中：电场分量 $E_x,E_y,E_z$ 位于棱中点，磁场分量 $H_x,H_y,H_z$ 位于面中心，空间半步错位。该布局使每个旋度运算的中心差分天然落在被求场位置，二阶精度 $O(\Delta h^2)$，且离散 Gauss 定律 $\nabla_h\cdot(\nabla_h\times\cdot)\equiv 0$ 自动满足（避免非物理电荷积累）。Yee 网格是 FDE/FDFD/FDTD/2.5D-FDTD 共同基础（ALGORITHMS.md 附录 C）。

### 3.2 E/H leapfrog 时间推进

时间半步错位，磁场在 $n+1/2$ 时刻更新，电场在 $n+1$ 时刻更新。以 $E_z$（TEz 2D）为例：

$$H_x^{n+1/2}\big|_{i,j+1/2} = D_{a,\mu}\, H_x^{n-1/2}\big|_{i,j+1/2} - D_{b,\mu}\,\frac{E_z^n|_{i,j+1}-E_z^n|_{i,j}}{\Delta y}$$

$$H_y^{n+1/2}\big|_{i+1/2,j} = D_{a,\mu}\, H_y^{n-1/2}\big|_{i+1/2,j} + D_{b,\mu}\,\frac{E_z^n|_{i+1,j}-E_z^n|_{i,j}}{\Delta x}$$

$$E_z^{n+1}\big|_{i,j} = C_{a,\varepsilon}\, E_z^n\big|_{i,j} + C_{b,\varepsilon}\left[\frac{H_y^{n+1/2}|_{i+1/2,j}-H_y^{n+1/2}|_{i-1/2,j}}{\Delta x} - \frac{H_x^{n+1/2}|_{i,j+1/2}-H_x^{n+1/2}|_{i,j-1/2}}{\Delta y}\right]$$

其中 $D_{a,\mu}=\frac{1-\sigma_m\Delta t/(2\mu_0)}{1+\sigma_m\Delta t/(2\mu_0)}$，$D_{b,\mu}=\frac{\Delta t/\mu_0}{1+\sigma_m\Delta t/(2\mu_0)}$，$C_{a,\varepsilon}=\frac{1-\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}{1+\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}$，$C_{b,\varepsilon}=\frac{\Delta t/(\varepsilon_0\varepsilon_r)}{1+\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}$。3D 形式按 6 个分量类似展开。

### 3.3 共形网格亚像素平滑（Yu-Mittra 1/2、Volume-Average）

阶梯近似在介质界面产生 $O(\Delta h)$ 误差。Yu-Mittra 1/2 共形方案：在 Yee 棱上的等效介电常数取界面两侧的体积加权平均，使界面处的等效 $\varepsilon$ 接近真实积分形式，误差降至 $O(\Delta h^2)$。Lumerical Conformal Variant 0/1/2 在介质/金属/PEC 界面分别采用不同共形规则；Tidy3D 默认开启 subpixel averaging。PoLaRIS 将实现 Volume-Average + Yu-Mittra 1/2 两种共形方案。

### 3.4 自动非均匀网格

按"每波长最少 N 个网格"（典型 N=10~20，金属/色散材料处加密至 N=# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$ 处理。

### 2.2 色散材料（辅助微分方程 ADE）

Drude-Lorentz 色散介质极化密度 $\mathbf{P}$ 满足二阶 ODE：

$$\frac{\partial^2 \mathbf{P}}{\partial t^2} + \gamma \frac{\partial \mathbf{P}}{\partial t} + \omega_0^2 \mathbf{P} = \varepsilon_0 \omega_p^2 \mathbf{E}$$

其中 $\omega_0$ 为共振频率，$\gamma$ 为阻尼率，$\omega_p$ 为等离子频率。$\mathbf{D}=\varepsilon_0\varepsilon_\infty\mathbf{E}+\mathbf{P}$，代入 Maxwell 旋度方程得 ADE-FDTD 更新格式（Lumerical MCM、Tidy3D PoleResidue 共同方案）。多系数材料 MCM 通过加和多个 Lorentz 极点拟合实测 $n(\omega)$ 数据。

### 2.3 非线性（Kerr + 拉曼）

三阶非线性 $\mathbf{P}_{NL}=\varepsilon_0\chi^{(3)}|\mathbf{E}|^2\mathbf{E}$（瞬时 Kerr）+ 卷积拉曼项，ADE 法处理。光子芯片中典型应用为 SiN 微环的克尔自相位调制、LNOI 的 $\chi^{(2)}$ 二次谐波。

---

## 3. Yee 网格离散化方案

### 3.1 Yee 1966 网格布局

3D Yee 单元中：电场分量 $E_x,E_y,E_z$ 位于棱中点，磁场分量 $H_x,H_y,H_z$ 位于面中心，空间半步错位。该布局使每个旋度运算的中心差分天然落在被求场位置，二阶精度 $O(\Delta h^2)$，且离散 Gauss 定律 $\nabla_h\cdot(\nabla_h\times\cdot)\equiv 0$ 自动满足（避免非物理电荷积累）。Yee 网格是 FDE/FDFD/FDTD/2.5D-FDTD 共同基础（ALGORITHMS.md 附录 C）。

### 3.2 E/H leapfrog 时间推进

时间半步错位，磁场在 $n+1/2$ 时刻更新，电场在 $n+1$ 时刻更新。以 $E_z$（TEz 2D）为例：

$$H_x^{n+1/2}\big|_{i,j+1/2} = D_{a,\mu}\, H_x^{n-1/2}\big|_{i,j+1/2} - D_{b,\mu}\,\frac{E_z^n|_{i,j+1}-E_z^n|_{i,j}}{\Delta y}$$

$$H_y^{n+1/2}\big|_{i+1/2,j} = D_{a,\mu}\, H_y^{n-1/2}\big|_{i+1/2,j} + D_{b,\mu}\,\frac{E_z^n|_{i+1,j}-E_z^n|_{i,j}}{\Delta x}$$

$$E_z^{n+1}\big|_{i,j} = C_{a,\varepsilon}\, E_z^n\big|_{i,j} + C_{b,\varepsilon}\left[\frac{H_y^{n+1/2}|_{i+1/2,j}-H_y^{n+1/2}|_{i-1/2,j}}{\Delta x} - \frac{H_x^{n+1/2}|_{i,j+1/2}-H_x^{n+1/2}|_{i,j-1/2}}{\Delta y}\right]$$

其中 $D_{a,\mu}=\frac{1-\sigma_m\Delta t/(2\mu_0)}{1+\sigma_m\Delta t/(2\mu_0)}$，$D_{b,\mu}=\frac{\Delta t/\mu_0}{1+\sigma_m\Delta t/(2\mu_0)}$，$C_{a,\varepsilon}=\frac{1-\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}{1+\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}$，$C_{b,\varepsilon}=\frac{\Delta t/(\varepsilon_0\varepsilon_r)}{1+\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}$。3D 形式按 6 个分量类似展开。

### 3.3 共形网格亚像素平滑（Yu-Mittra 1/2、Volume-Average）

阶梯近似在介质界面产生 $O(\Delta h)$ 误差。Yu-Mittra 1/2 共形方案：在 Yee 棱上的等效介电常数取界面两侧的体积加权平均，使界面处的等效 $\varepsilon$ 接近真实积分形式，误差降至 $O(\Delta h^2)$。Lumerical Conformal Variant 0/1/2 在介质/金属/PEC 界面分别采用不同共形规则；Tidy3D 默认开启 subpixel averaging。PoLaRIS 将实现 Volume-Average + Yu-Mittra 1/2 两种共形方案。

### 3.4 自动非均匀网格

按"每波长最少 N 个网格"（典型 N=10~20，金属/色散材料处加密至 N=30+）+ 局部 mesh override# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$ 处理。

### 2.2 色散材料（辅助微分方程 ADE）

Drude-Lorentz 色散介质极化密度 $\mathbf{P}$ 满足二阶 ODE：

$$\frac{\partial^2 \mathbf{P}}{\partial t^2} + \gamma \frac{\partial \mathbf{P}}{\partial t} + \omega_0^2 \mathbf{P} = \varepsilon_0 \omega_p^2 \mathbf{E}$$

其中 $\omega_0$ 为共振频率，$\gamma$ 为阻尼率，$\omega_p$ 为等离子频率。$\mathbf{D}=\varepsilon_0\varepsilon_\infty\mathbf{E}+\mathbf{P}$，代入 Maxwell 旋度方程得 ADE-FDTD 更新格式（Lumerical MCM、Tidy3D PoleResidue 共同方案）。多系数材料 MCM 通过加和多个 Lorentz 极点拟合实测 $n(\omega)$ 数据。

### 2.3 非线性（Kerr + 拉曼）

三阶非线性 $\mathbf{P}_{NL}=\varepsilon_0\chi^{(3)}|\mathbf{E}|^2\mathbf{E}$（瞬时 Kerr）+ 卷积拉曼项，ADE 法处理。光子芯片中典型应用为 SiN 微环的克尔自相位调制、LNOI 的 $\chi^{(2)}$ 二次谐波。

---

## 3. Yee 网格离散化方案

### 3.1 Yee 1966 网格布局

3D Yee 单元中：电场分量 $E_x,E_y,E_z$ 位于棱中点，磁场分量 $H_x,H_y,H_z$ 位于面中心，空间半步错位。该布局使每个旋度运算的中心差分天然落在被求场位置，二阶精度 $O(\Delta h^2)$，且离散 Gauss 定律 $\nabla_h\cdot(\nabla_h\times\cdot)\equiv 0$ 自动满足（避免非物理电荷积累）。Yee 网格是 FDE/FDFD/FDTD/2.5D-FDTD 共同基础（ALGORITHMS.md 附录 C）。

### 3.2 E/H leapfrog 时间推进

时间半步错位，磁场在 $n+1/2$ 时刻更新，电场在 $n+1$ 时刻更新。以 $E_z$（TEz 2D）为例：

$$H_x^{n+1/2}\big|_{i,j+1/2} = D_{a,\mu}\, H_x^{n-1/2}\big|_{i,j+1/2} - D_{b,\mu}\,\frac{E_z^n|_{i,j+1}-E_z^n|_{i,j}}{\Delta y}$$

$$H_y^{n+1/2}\big|_{i+1/2,j} = D_{a,\mu}\, H_y^{n-1/2}\big|_{i+1/2,j} + D_{b,\mu}\,\frac{E_z^n|_{i+1,j}-E_z^n|_{i,j}}{\Delta x}$$

$$E_z^{n+1}\big|_{i,j} = C_{a,\varepsilon}\, E_z^n\big|_{i,j} + C_{b,\varepsilon}\left[\frac{H_y^{n+1/2}|_{i+1/2,j}-H_y^{n+1/2}|_{i-1/2,j}}{\Delta x} - \frac{H_x^{n+1/2}|_{i,j+1/2}-H_x^{n+1/2}|_{i,j-1/2}}{\Delta y}\right]$$

其中 $D_{a,\mu}=\frac{1-\sigma_m\Delta t/(2\mu_0)}{1+\sigma_m\Delta t/(2\mu_0)}$，$D_{b,\mu}=\frac{\Delta t/\mu_0}{1+\sigma_m\Delta t/(2\mu_0)}$，$C_{a,\varepsilon}=\frac{1-\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}{1+\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}$，$C_{b,\varepsilon}=\frac{\Delta t/(\varepsilon_0\varepsilon_r)}{1+\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}$。3D 形式按 6 个分量类似展开。

### 3.3 共形网格亚像素平滑（Yu-Mittra 1/2、Volume-Average）

阶梯近似在介质界面产生 $O(\Delta h)$ 误差。Yu-Mittra 1/2 共形方案：在 Yee 棱上的等效介电常数取界面两侧的体积加权平均，使界面处的等效 $\varepsilon$ 接近真实积分形式，误差降至 $O(\Delta h^2)$。Lumerical Conformal Variant 0/1/2 在介质/金属/PEC 界面分别采用不同共形规则；Tidy3D 默认开启 subpixel averaging。PoLaRIS 将实现 Volume-Average + Yu-Mittra 1/2 两种共形方案。

### 3.4 自动非均匀网格

按"每波长最少 N 个网格"（典型 N=10~20，金属/色散材料处加密至 N=30+）+ 局部 mesh override 框生成非均匀网格，CFL 时间步# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$ 处理。

### 2.2 色散材料（辅助微分方程 ADE）

Drude-Lorentz 色散介质极化密度 $\mathbf{P}$ 满足二阶 ODE：

$$\frac{\partial^2 \mathbf{P}}{\partial t^2} + \gamma \frac{\partial \mathbf{P}}{\partial t} + \omega_0^2 \mathbf{P} = \varepsilon_0 \omega_p^2 \mathbf{E}$$

其中 $\omega_0$ 为共振频率，$\gamma$ 为阻尼率，$\omega_p$ 为等离子频率。$\mathbf{D}=\varepsilon_0\varepsilon_\infty\mathbf{E}+\mathbf{P}$，代入 Maxwell 旋度方程得 ADE-FDTD 更新格式（Lumerical MCM、Tidy3D PoleResidue 共同方案）。多系数材料 MCM 通过加和多个 Lorentz 极点拟合实测 $n(\omega)$ 数据。

### 2.3 非线性（Kerr + 拉曼）

三阶非线性 $\mathbf{P}_{NL}=\varepsilon_0\chi^{(3)}|\mathbf{E}|^2\mathbf{E}$（瞬时 Kerr）+ 卷积拉曼项，ADE 法处理。光子芯片中典型应用为 SiN 微环的克尔自相位调制、LNOI 的 $\chi^{(2)}$ 二次谐波。

---

## 3. Yee 网格离散化方案

### 3.1 Yee 1966 网格布局

3D Yee 单元中：电场分量 $E_x,E_y,E_z$ 位于棱中点，磁场分量 $H_x,H_y,H_z$ 位于面中心，空间半步错位。该布局使每个旋度运算的中心差分天然落在被求场位置，二阶精度 $O(\Delta h^2)$，且离散 Gauss 定律 $\nabla_h\cdot(\nabla_h\times\cdot)\equiv 0$ 自动满足（避免非物理电荷积累）。Yee 网格是 FDE/FDFD/FDTD/2.5D-FDTD 共同基础（ALGORITHMS.md 附录 C）。

### 3.2 E/H leapfrog 时间推进

时间半步错位，磁场在 $n+1/2$ 时刻更新，电场在 $n+1$ 时刻更新。以 $E_z$（TEz 2D）为例：

$$H_x^{n+1/2}\big|_{i,j+1/2} = D_{a,\mu}\, H_x^{n-1/2}\big|_{i,j+1/2} - D_{b,\mu}\,\frac{E_z^n|_{i,j+1}-E_z^n|_{i,j}}{\Delta y}$$

$$H_y^{n+1/2}\big|_{i+1/2,j} = D_{a,\mu}\, H_y^{n-1/2}\big|_{i+1/2,j} + D_{b,\mu}\,\frac{E_z^n|_{i+1,j}-E_z^n|_{i,j}}{\Delta x}$$

$$E_z^{n+1}\big|_{i,j} = C_{a,\varepsilon}\, E_z^n\big|_{i,j} + C_{b,\varepsilon}\left[\frac{H_y^{n+1/2}|_{i+1/2,j}-H_y^{n+1/2}|_{i-1/2,j}}{\Delta x} - \frac{H_x^{n+1/2}|_{i,j+1/2}-H_x^{n+1/2}|_{i,j-1/2}}{\Delta y}\right]$$

其中 $D_{a,\mu}=\frac{1-\sigma_m\Delta t/(2\mu_0)}{1+\sigma_m\Delta t/(2\mu_0)}$，$D_{b,\mu}=\frac{\Delta t/\mu_0}{1+\sigma_m\Delta t/(2\mu_0)}$，$C_{a,\varepsilon}=\frac{1-\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}{1+\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}$，$C_{b,\varepsilon}=\frac{\Delta t/(\varepsilon_0\varepsilon_r)}{1+\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}$。3D 形式按 6 个分量类似展开。

### 3.3 共形网格亚像素平滑（Yu-Mittra 1/2、Volume-Average）

阶梯近似在介质界面产生 $O(\Delta h)$ 误差。Yu-Mittra 1/2 共形方案：在 Yee 棱上的等效介电常数取界面两侧的体积加权平均，使界面处的等效 $\varepsilon$ 接近真实积分形式，误差降至 $O(\Delta h^2)$。Lumerical Conformal Variant 0/1/2 在介质/金属/PEC 界面分别采用不同共形规则；Tidy3D 默认开启 subpixel averaging。PoLaRIS 将实现 Volume-Average + Yu-Mittra 1/2 两种共形方案。

### 3.4 自动非均匀网格

按"每波长最少 N 个网格"（典型 N=10~20，金属/色散材料处加密至 N=30+）+ 局部 mesh override 框生成非均匀网格，CFL 时间步由最细网格决定。Lumerical `# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$ 处理。

### 2.2 色散材料（辅助微分方程 ADE）

Drude-Lorentz 色散介质极化密度 $\mathbf{P}$ 满足二阶 ODE：

$$\frac{\partial^2 \mathbf{P}}{\partial t^2} + \gamma \frac{\partial \mathbf{P}}{\partial t} + \omega_0^2 \mathbf{P} = \varepsilon_0 \omega_p^2 \mathbf{E}$$

其中 $\omega_0$ 为共振频率，$\gamma$ 为阻尼率，$\omega_p$ 为等离子频率。$\mathbf{D}=\varepsilon_0\varepsilon_\infty\mathbf{E}+\mathbf{P}$，代入 Maxwell 旋度方程得 ADE-FDTD 更新格式（Lumerical MCM、Tidy3D PoleResidue 共同方案）。多系数材料 MCM 通过加和多个 Lorentz 极点拟合实测 $n(\omega)$ 数据。

### 2.3 非线性（Kerr + 拉曼）

三阶非线性 $\mathbf{P}_{NL}=\varepsilon_0\chi^{(3)}|\mathbf{E}|^2\mathbf{E}$（瞬时 Kerr）+ 卷积拉曼项，ADE 法处理。光子芯片中典型应用为 SiN 微环的克尔自相位调制、LNOI 的 $\chi^{(2)}$ 二次谐波。

---

## 3. Yee 网格离散化方案

### 3.1 Yee 1966 网格布局

3D Yee 单元中：电场分量 $E_x,E_y,E_z$ 位于棱中点，磁场分量 $H_x,H_y,H_z$ 位于面中心，空间半步错位。该布局使每个旋度运算的中心差分天然落在被求场位置，二阶精度 $O(\Delta h^2)$，且离散 Gauss 定律 $\nabla_h\cdot(\nabla_h\times\cdot)\equiv 0$ 自动满足（避免非物理电荷积累）。Yee 网格是 FDE/FDFD/FDTD/2.5D-FDTD 共同基础（ALGORITHMS.md 附录 C）。

### 3.2 E/H leapfrog 时间推进

时间半步错位，磁场在 $n+1/2$ 时刻更新，电场在 $n+1$ 时刻更新。以 $E_z$（TEz 2D）为例：

$$H_x^{n+1/2}\big|_{i,j+1/2} = D_{a,\mu}\, H_x^{n-1/2}\big|_{i,j+1/2} - D_{b,\mu}\,\frac{E_z^n|_{i,j+1}-E_z^n|_{i,j}}{\Delta y}$$

$$H_y^{n+1/2}\big|_{i+1/2,j} = D_{a,\mu}\, H_y^{n-1/2}\big|_{i+1/2,j} + D_{b,\mu}\,\frac{E_z^n|_{i+1,j}-E_z^n|_{i,j}}{\Delta x}$$

$$E_z^{n+1}\big|_{i,j} = C_{a,\varepsilon}\, E_z^n\big|_{i,j} + C_{b,\varepsilon}\left[\frac{H_y^{n+1/2}|_{i+1/2,j}-H_y^{n+1/2}|_{i-1/2,j}}{\Delta x} - \frac{H_x^{n+1/2}|_{i,j+1/2}-H_x^{n+1/2}|_{i,j-1/2}}{\Delta y}\right]$$

其中 $D_{a,\mu}=\frac{1-\sigma_m\Delta t/(2\mu_0)}{1+\sigma_m\Delta t/(2\mu_0)}$，$D_{b,\mu}=\frac{\Delta t/\mu_0}{1+\sigma_m\Delta t/(2\mu_0)}$，$C_{a,\varepsilon}=\frac{1-\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}{1+\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}$，$C_{b,\varepsilon}=\frac{\Delta t/(\varepsilon_0\varepsilon_r)}{1+\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}$。3D 形式按 6 个分量类似展开。

### 3.3 共形网格亚像素平滑（Yu-Mittra 1/2、Volume-Average）

阶梯近似在介质界面产生 $O(\Delta h)$ 误差。Yu-Mittra 1/2 共形方案：在 Yee 棱上的等效介电常数取界面两侧的体积加权平均，使界面处的等效 $\varepsilon$ 接近真实积分形式，误差降至 $O(\Delta h^2)$。Lumerical Conformal Variant 0/1/2 在介质/金属/PEC 界面分别采用不同共形规则；Tidy3D 默认开启 subpixel averaging。PoLaRIS 将实现 Volume-Average + Yu-Mittra 1/2 两种共形方案。

### 3.4 自动非均匀网格

按"每波长最少 N 个网格"（典型 N=10~20，金属/色散材料处加密至 N=30+）+ 局部 mesh override 框生成非均匀网格，CFL 时间步由最细网格决定。Lumerical `auto nonuniform` mesh accuracy 1-8 对应不同 N；Tidy3D `# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$ 处理。

### 2.2 色散材料（辅助微分方程 ADE）

Drude-Lorentz 色散介质极化密度 $\mathbf{P}$ 满足二阶 ODE：

$$\frac{\partial^2 \mathbf{P}}{\partial t^2} + \gamma \frac{\partial \mathbf{P}}{\partial t} + \omega_0^2 \mathbf{P} = \varepsilon_0 \omega_p^2 \mathbf{E}$$

其中 $\omega_0$ 为共振频率，$\gamma$ 为阻尼率，$\omega_p$ 为等离子频率。$\mathbf{D}=\varepsilon_0\varepsilon_\infty\mathbf{E}+\mathbf{P}$，代入 Maxwell 旋度方程得 ADE-FDTD 更新格式（Lumerical MCM、Tidy3D PoleResidue 共同方案）。多系数材料 MCM 通过加和多个 Lorentz 极点拟合实测 $n(\omega)$ 数据。

### 2.3 非线性（Kerr + 拉曼）

三阶非线性 $\mathbf{P}_{NL}=\varepsilon_0\chi^{(3)}|\mathbf{E}|^2\mathbf{E}$（瞬时 Kerr）+ 卷积拉曼项，ADE 法处理。光子芯片中典型应用为 SiN 微环的克尔自相位调制、LNOI 的 $\chi^{(2)}$ 二次谐波。

---

## 3. Yee 网格离散化方案

### 3.1 Yee 1966 网格布局

3D Yee 单元中：电场分量 $E_x,E_y,E_z$ 位于棱中点，磁场分量 $H_x,H_y,H_z$ 位于面中心，空间半步错位。该布局使每个旋度运算的中心差分天然落在被求场位置，二阶精度 $O(\Delta h^2)$，且离散 Gauss 定律 $\nabla_h\cdot(\nabla_h\times\cdot)\equiv 0$ 自动满足（避免非物理电荷积累）。Yee 网格是 FDE/FDFD/FDTD/2.5D-FDTD 共同基础（ALGORITHMS.md 附录 C）。

### 3.2 E/H leapfrog 时间推进

时间半步错位，磁场在 $n+1/2$ 时刻更新，电场在 $n+1$ 时刻更新。以 $E_z$（TEz 2D）为例：

$$H_x^{n+1/2}\big|_{i,j+1/2} = D_{a,\mu}\, H_x^{n-1/2}\big|_{i,j+1/2} - D_{b,\mu}\,\frac{E_z^n|_{i,j+1}-E_z^n|_{i,j}}{\Delta y}$$

$$H_y^{n+1/2}\big|_{i+1/2,j} = D_{a,\mu}\, H_y^{n-1/2}\big|_{i+1/2,j} + D_{b,\mu}\,\frac{E_z^n|_{i+1,j}-E_z^n|_{i,j}}{\Delta x}$$

$$E_z^{n+1}\big|_{i,j} = C_{a,\varepsilon}\, E_z^n\big|_{i,j} + C_{b,\varepsilon}\left[\frac{H_y^{n+1/2}|_{i+1/2,j}-H_y^{n+1/2}|_{i-1/2,j}}{\Delta x} - \frac{H_x^{n+1/2}|_{i,j+1/2}-H_x^{n+1/2}|_{i,j-1/2}}{\Delta y}\right]$$

其中 $D_{a,\mu}=\frac{1-\sigma_m\Delta t/(2\mu_0)}{1+\sigma_m\Delta t/(2\mu_0)}$，$D_{b,\mu}=\frac{\Delta t/\mu_0}{1+\sigma_m\Delta t/(2\mu_0)}$，$C_{a,\varepsilon}=\frac{1-\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}{1+\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}$，$C_{b,\varepsilon}=\frac{\Delta t/(\varepsilon_0\varepsilon_r)}{1+\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}$。3D 形式按 6 个分量类似展开。

### 3.3 共形网格亚像素平滑（Yu-Mittra 1/2、Volume-Average）

阶梯近似在介质界面产生 $O(\Delta h)$ 误差。Yu-Mittra 1/2 共形方案：在 Yee 棱上的等效介电常数取界面两侧的体积加权平均，使界面处的等效 $\varepsilon$ 接近真实积分形式，误差降至 $O(\Delta h^2)$。Lumerical Conformal Variant 0/1/2 在介质/金属/PEC 界面分别采用不同共形规则；Tidy3D 默认开启 subpixel averaging。PoLaRIS 将实现 Volume-Average + Yu-Mittra 1/2 两种共形方案。

### 3.4 自动非均匀网格

按"每波长最少 N 个网格"（典型 N=10~20，金属/色散材料处加密至 N=30+）+ 局部 mesh override 框生成非均匀网格，CFL 时间步由最细网格决定。Lumerical `auto nonuniform` mesh accuracy 1-8 对应不同 N；Tidy3D `auto_nonuniform_mesh=True`（arXiv# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$ 处理。

### 2.2 色散材料（辅助微分方程 ADE）

Drude-Lorentz 色散介质极化密度 $\mathbf{P}$ 满足二阶 ODE：

$$\frac{\partial^2 \mathbf{P}}{\partial t^2} + \gamma \frac{\partial \mathbf{P}}{\partial t} + \omega_0^2 \mathbf{P} = \varepsilon_0 \omega_p^2 \mathbf{E}$$

其中 $\omega_0$ 为共振频率，$\gamma$ 为阻尼率，$\omega_p$ 为等离子频率。$\mathbf{D}=\varepsilon_0\varepsilon_\infty\mathbf{E}+\mathbf{P}$，代入 Maxwell 旋度方程得 ADE-FDTD 更新格式（Lumerical MCM、Tidy3D PoleResidue 共同方案）。多系数材料 MCM 通过加和多个 Lorentz 极点拟合实测 $n(\omega)$ 数据。

### 2.3 非线性（Kerr + 拉曼）

三阶非线性 $\mathbf{P}_{NL}=\varepsilon_0\chi^{(3)}|\mathbf{E}|^2\mathbf{E}$（瞬时 Kerr）+ 卷积拉曼项，ADE 法处理。光子芯片中典型应用为 SiN 微环的克尔自相位调制、LNOI 的 $\chi^{(2)}$ 二次谐波。

---

## 3. Yee 网格离散化方案

### 3.1 Yee 1966 网格布局

3D Yee 单元中：电场分量 $E_x,E_y,E_z$ 位于棱中点，磁场分量 $H_x,H_y,H_z$ 位于面中心，空间半步错位。该布局使每个旋度运算的中心差分天然落在被求场位置，二阶精度 $O(\Delta h^2)$，且离散 Gauss 定律 $\nabla_h\cdot(\nabla_h\times\cdot)\equiv 0$ 自动满足（避免非物理电荷积累）。Yee 网格是 FDE/FDFD/FDTD/2.5D-FDTD 共同基础（ALGORITHMS.md 附录 C）。

### 3.2 E/H leapfrog 时间推进

时间半步错位，磁场在 $n+1/2$ 时刻更新，电场在 $n+1$ 时刻更新。以 $E_z$（TEz 2D）为例：

$$H_x^{n+1/2}\big|_{i,j+1/2} = D_{a,\mu}\, H_x^{n-1/2}\big|_{i,j+1/2} - D_{b,\mu}\,\frac{E_z^n|_{i,j+1}-E_z^n|_{i,j}}{\Delta y}$$

$$H_y^{n+1/2}\big|_{i+1/2,j} = D_{a,\mu}\, H_y^{n-1/2}\big|_{i+1/2,j} + D_{b,\mu}\,\frac{E_z^n|_{i+1,j}-E_z^n|_{i,j}}{\Delta x}$$

$$E_z^{n+1}\big|_{i,j} = C_{a,\varepsilon}\, E_z^n\big|_{i,j} + C_{b,\varepsilon}\left[\frac{H_y^{n+1/2}|_{i+1/2,j}-H_y^{n+1/2}|_{i-1/2,j}}{\Delta x} - \frac{H_x^{n+1/2}|_{i,j+1/2}-H_x^{n+1/2}|_{i,j-1/2}}{\Delta y}\right]$$

其中 $D_{a,\mu}=\frac{1-\sigma_m\Delta t/(2\mu_0)}{1+\sigma_m\Delta t/(2\mu_0)}$，$D_{b,\mu}=\frac{\Delta t/\mu_0}{1+\sigma_m\Delta t/(2\mu_0)}$，$C_{a,\varepsilon}=\frac{1-\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}{1+\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}$，$C_{b,\varepsilon}=\frac{\Delta t/(\varepsilon_0\varepsilon_r)}{1+\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}$。3D 形式按 6 个分量类似展开。

### 3.3 共形网格亚像素平滑（Yu-Mittra 1/2、Volume-Average）

阶梯近似在介质界面产生 $O(\Delta h)$ 误差。Yu-Mittra 1/2 共形方案：在 Yee 棱上的等效介电常数取界面两侧的体积加权平均，使界面处的等效 $\varepsilon$ 接近真实积分形式，误差降至 $O(\Delta h^2)$。Lumerical Conformal Variant 0/1/2 在介质/金属/PEC 界面分别采用不同共形规则；Tidy3D 默认开启 subpixel averaging。PoLaRIS 将实现 Volume-Average + Yu-Mittra 1/2 两种共形方案。

### 3.4 自动非均匀网格

按"每波长最少 N 个网格"（典型 N=10~20，金属/色散材料处加密至 N=30+）+ 局部 mesh override 框生成非均匀网格，CFL 时间步由最细网格决定。Lumerical `auto nonuniform` mesh accuracy 1-8 对应不同 N；Tidy3D `auto_nonuniform_mesh=True`（arXiv:2506.16665）。

---

### A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$ 处理。

### 2.2 色散材料（辅助微分方程 ADE）

Drude-Lorentz 色散介质极化密度 $\mathbf{P}$ 满足二阶 ODE：

$$\frac{\partial^2 \mathbf{P}}{\partial t^2} + \gamma \frac{\partial \mathbf{P}}{\partial t} + \omega_0^2 \mathbf{P} = \varepsilon_0 \omega_p^2 \mathbf{E}$$

其中 $\omega_0$ 为共振频率，$\gamma$ 为阻尼率，$\omega_p$ 为等离子频率。$\mathbf{D}=\varepsilon_0\varepsilon_\infty\mathbf{E}+\mathbf{P}$，代入 Maxwell 旋度方程得 ADE-FDTD 更新格式（Lumerical MCM、Tidy3D PoleResidue 共同方案）。多系数材料 MCM 通过加和多个 Lorentz 极点拟合实测 $n(\omega)$ 数据。

### 2.3 非线性（Kerr + 拉曼）

三阶非线性 $\mathbf{P}_{NL}=\varepsilon_0\chi^{(3)}|\mathbf{E}|^2\mathbf{E}$（瞬时 Kerr）+ 卷积拉曼项，ADE 法处理。光子芯片中典型应用为 SiN 微环的克尔自相位调制、LNOI 的 $\chi^{(2)}$ 二次谐波。

---

## 3. Yee 网格离散化方案

### 3.1 Yee 1966 网格布局

3D Yee 单元中：电场分量 $E_x,E_y,E_z$ 位于棱中点，磁场分量 $H_x,H_y,H_z$ 位于面中心，空间半步错位。该布局使每个旋度运算的中心差分天然落在被求场位置，二阶精度 $O(\Delta h^2)$，且离散 Gauss 定律 $\nabla_h\cdot(\nabla_h\times\cdot)\equiv 0$ 自动满足（避免非物理电荷积累）。Yee 网格是 FDE/FDFD/FDTD/2.5D-FDTD 共同基础（ALGORITHMS.md 附录 C）。

### 3.2 E/H leapfrog 时间推进

时间半步错位，磁场在 $n+1/2$ 时刻更新，电场在 $n+1$ 时刻更新。以 $E_z$（TEz 2D）为例：

$$H_x^{n+1/2}\big|_{i,j+1/2} = D_{a,\mu}\, H_x^{n-1/2}\big|_{i,j+1/2} - D_{b,\mu}\,\frac{E_z^n|_{i,j+1}-E_z^n|_{i,j}}{\Delta y}$$

$$H_y^{n+1/2}\big|_{i+1/2,j} = D_{a,\mu}\, H_y^{n-1/2}\big|_{i+1/2,j} + D_{b,\mu}\,\frac{E_z^n|_{i+1,j}-E_z^n|_{i,j}}{\Delta x}$$

$$E_z^{n+1}\big|_{i,j} = C_{a,\varepsilon}\, E_z^n\big|_{i,j} + C_{b,\varepsilon}\left[\frac{H_y^{n+1/2}|_{i+1/2,j}-H_y^{n+1/2}|_{i-1/2,j}}{\Delta x} - \frac{H_x^{n+1/2}|_{i,j+1/2}-H_x^{n+1/2}|_{i,j-1/2}}{\Delta y}\right]$$

其中 $D_{a,\mu}=\frac{1-\sigma_m\Delta t/(2\mu_0)}{1+\sigma_m\Delta t/(2\mu_0)}$，$D_{b,\mu}=\frac{\Delta t/\mu_0}{1+\sigma_m\Delta t/(2\mu_0)}$，$C_{a,\varepsilon}=\frac{1-\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}{1+\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}$，$C_{b,\varepsilon}=\frac{\Delta t/(\varepsilon_0\varepsilon_r)}{1+\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}$。3D 形式按 6 个分量类似展开。

### 3.3 共形网格亚像素平滑（Yu-Mittra 1/2、Volume-Average）

阶梯近似在介质界面产生 $O(\Delta h)$ 误差。Yu-Mittra 1/2 共形方案：在 Yee 棱上的等效介电常数取界面两侧的体积加权平均，使界面处的等效 $\varepsilon$ 接近真实积分形式，误差降至 $O(\Delta h^2)$。Lumerical Conformal Variant 0/1/2 在介质/金属/PEC 界面分别采用不同共形规则；Tidy3D 默认开启 subpixel averaging。PoLaRIS 将实现 Volume-Average + Yu-Mittra 1/2 两种共形方案。

### 3.4 自动非均匀网格

按"每波长最少 N 个网格"（典型 N=10~20，金属/色散材料处加密至 N=30+）+ 局部 mesh override 框生成非均匀网格，CFL 时间步由最细网格决定。Lumerical `auto nonuniform` mesh accuracy 1-8 对应不同 N；Tidy3D `auto_nonuniform_mesh=True`（arXiv:2506.16665）。

---

## 4. Courant-Friedrichs-Lewy 稳定性条件

显式 leapfrog 格式稳定的必要条件（3D）# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$ 处理。

### 2.2 色散材料（辅助微分方程 ADE）

Drude-Lorentz 色散介质极化密度 $\mathbf{P}$ 满足二阶 ODE：

$$\frac{\partial^2 \mathbf{P}}{\partial t^2} + \gamma \frac{\partial \mathbf{P}}{\partial t} + \omega_0^2 \mathbf{P} = \varepsilon_0 \omega_p^2 \mathbf{E}$$

其中 $\omega_0$ 为共振频率，$\gamma$ 为阻尼率，$\omega_p$ 为等离子频率。$\mathbf{D}=\varepsilon_0\varepsilon_\infty\mathbf{E}+\mathbf{P}$，代入 Maxwell 旋度方程得 ADE-FDTD 更新格式（Lumerical MCM、Tidy3D PoleResidue 共同方案）。多系数材料 MCM 通过加和多个 Lorentz 极点拟合实测 $n(\omega)$ 数据。

### 2.3 非线性（Kerr + 拉曼）

三阶非线性 $\mathbf{P}_{NL}=\varepsilon_0\chi^{(3)}|\mathbf{E}|^2\mathbf{E}$（瞬时 Kerr）+ 卷积拉曼项，ADE 法处理。光子芯片中典型应用为 SiN 微环的克尔自相位调制、LNOI 的 $\chi^{(2)}$ 二次谐波。

---

## 3. Yee 网格离散化方案

### 3.1 Yee 1966 网格布局

3D Yee 单元中：电场分量 $E_x,E_y,E_z$ 位于棱中点，磁场分量 $H_x,H_y,H_z$ 位于面中心，空间半步错位。该布局使每个旋度运算的中心差分天然落在被求场位置，二阶精度 $O(\Delta h^2)$，且离散 Gauss 定律 $\nabla_h\cdot(\nabla_h\times\cdot)\equiv 0$ 自动满足（避免非物理电荷积累）。Yee 网格是 FDE/FDFD/FDTD/2.5D-FDTD 共同基础（ALGORITHMS.md 附录 C）。

### 3.2 E/H leapfrog 时间推进

时间半步错位，磁场在 $n+1/2$ 时刻更新，电场在 $n+1$ 时刻更新。以 $E_z$（TEz 2D）为例：

$$H_x^{n+1/2}\big|_{i,j+1/2} = D_{a,\mu}\, H_x^{n-1/2}\big|_{i,j+1/2} - D_{b,\mu}\,\frac{E_z^n|_{i,j+1}-E_z^n|_{i,j}}{\Delta y}$$

$$H_y^{n+1/2}\big|_{i+1/2,j} = D_{a,\mu}\, H_y^{n-1/2}\big|_{i+1/2,j} + D_{b,\mu}\,\frac{E_z^n|_{i+1,j}-E_z^n|_{i,j}}{\Delta x}$$

$$E_z^{n+1}\big|_{i,j} = C_{a,\varepsilon}\, E_z^n\big|_{i,j} + C_{b,\varepsilon}\left[\frac{H_y^{n+1/2}|_{i+1/2,j}-H_y^{n+1/2}|_{i-1/2,j}}{\Delta x} - \frac{H_x^{n+1/2}|_{i,j+1/2}-H_x^{n+1/2}|_{i,j-1/2}}{\Delta y}\right]$$

其中 $D_{a,\mu}=\frac{1-\sigma_m\Delta t/(2\mu_0)}{1+\sigma_m\Delta t/(2\mu_0)}$，$D_{b,\mu}=\frac{\Delta t/\mu_0}{1+\sigma_m\Delta t/(2\mu_0)}$，$C_{a,\varepsilon}=\frac{1-\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}{1+\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}$，$C_{b,\varepsilon}=\frac{\Delta t/(\varepsilon_0\varepsilon_r)}{1+\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}$。3D 形式按 6 个分量类似展开。

### 3.3 共形网格亚像素平滑（Yu-Mittra 1/2、Volume-Average）

阶梯近似在介质界面产生 $O(\Delta h)$ 误差。Yu-Mittra 1/2 共形方案：在 Yee 棱上的等效介电常数取界面两侧的体积加权平均，使界面处的等效 $\varepsilon$ 接近真实积分形式，误差降至 $O(\Delta h^2)$。Lumerical Conformal Variant 0/1/2 在介质/金属/PEC 界面分别采用不同共形规则；Tidy3D 默认开启 subpixel averaging。PoLaRIS 将实现 Volume-Average + Yu-Mittra 1/2 两种共形方案。

### 3.4 自动非均匀网格

按"每波长最少 N 个网格"（典型 N=10~20，金属/色散材料处加密至 N=30+）+ 局部 mesh override 框生成非均匀网格，CFL 时间步由最细网格决定。Lumerical `auto nonuniform` mesh accuracy 1-8 对应不同 N；Tidy3D `auto_nonuniform_mesh=True`（arXiv:2506.16665）。

---

## 4. Courant-Friedrichs-Lewy 稳定性条件

显式 leapfrog 格式稳定的必要条件（3D）：

$$\Delta t \le \frac{1}{c\sqrt{\frac{1}{\Delta x^2}+\frac{1# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$ 处理。

### 2.2 色散材料（辅助微分方程 ADE）

Drude-Lorentz 色散介质极化密度 $\mathbf{P}$ 满足二阶 ODE：

$$\frac{\partial^2 \mathbf{P}}{\partial t^2} + \gamma \frac{\partial \mathbf{P}}{\partial t} + \omega_0^2 \mathbf{P} = \varepsilon_0 \omega_p^2 \mathbf{E}$$

其中 $\omega_0$ 为共振频率，$\gamma$ 为阻尼率，$\omega_p$ 为等离子频率。$\mathbf{D}=\varepsilon_0\varepsilon_\infty\mathbf{E}+\mathbf{P}$，代入 Maxwell 旋度方程得 ADE-FDTD 更新格式（Lumerical MCM、Tidy3D PoleResidue 共同方案）。多系数材料 MCM 通过加和多个 Lorentz 极点拟合实测 $n(\omega)$ 数据。

### 2.3 非线性（Kerr + 拉曼）

三阶非线性 $\mathbf{P}_{NL}=\varepsilon_0\chi^{(3)}|\mathbf{E}|^2\mathbf{E}$（瞬时 Kerr）+ 卷积拉曼项，ADE 法处理。光子芯片中典型应用为 SiN 微环的克尔自相位调制、LNOI 的 $\chi^{(2)}$ 二次谐波。

---

## 3. Yee 网格离散化方案

### 3.1 Yee 1966 网格布局

3D Yee 单元中：电场分量 $E_x,E_y,E_z$ 位于棱中点，磁场分量 $H_x,H_y,H_z$ 位于面中心，空间半步错位。该布局使每个旋度运算的中心差分天然落在被求场位置，二阶精度 $O(\Delta h^2)$，且离散 Gauss 定律 $\nabla_h\cdot(\nabla_h\times\cdot)\equiv 0$ 自动满足（避免非物理电荷积累）。Yee 网格是 FDE/FDFD/FDTD/2.5D-FDTD 共同基础（ALGORITHMS.md 附录 C）。

### 3.2 E/H leapfrog 时间推进

时间半步错位，磁场在 $n+1/2$ 时刻更新，电场在 $n+1$ 时刻更新。以 $E_z$（TEz 2D）为例：

$$H_x^{n+1/2}\big|_{i,j+1/2} = D_{a,\mu}\, H_x^{n-1/2}\big|_{i,j+1/2} - D_{b,\mu}\,\frac{E_z^n|_{i,j+1}-E_z^n|_{i,j}}{\Delta y}$$

$$H_y^{n+1/2}\big|_{i+1/2,j} = D_{a,\mu}\, H_y^{n-1/2}\big|_{i+1/2,j} + D_{b,\mu}\,\frac{E_z^n|_{i+1,j}-E_z^n|_{i,j}}{\Delta x}$$

$$E_z^{n+1}\big|_{i,j} = C_{a,\varepsilon}\, E_z^n\big|_{i,j} + C_{b,\varepsilon}\left[\frac{H_y^{n+1/2}|_{i+1/2,j}-H_y^{n+1/2}|_{i-1/2,j}}{\Delta x} - \frac{H_x^{n+1/2}|_{i,j+1/2}-H_x^{n+1/2}|_{i,j-1/2}}{\Delta y}\right]$$

其中 $D_{a,\mu}=\frac{1-\sigma_m\Delta t/(2\mu_0)}{1+\sigma_m\Delta t/(2\mu_0)}$，$D_{b,\mu}=\frac{\Delta t/\mu_0}{1+\sigma_m\Delta t/(2\mu_0)}$，$C_{a,\varepsilon}=\frac{1-\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}{1+\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}$，$C_{b,\varepsilon}=\frac{\Delta t/(\varepsilon_0\varepsilon_r)}{1+\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}$。3D 形式按 6 个分量类似展开。

### 3.3 共形网格亚像素平滑（Yu-Mittra 1/2、Volume-Average）

阶梯近似在介质界面产生 $O(\Delta h)$ 误差。Yu-Mittra 1/2 共形方案：在 Yee 棱上的等效介电常数取界面两侧的体积加权平均，使界面处的等效 $\varepsilon$ 接近真实积分形式，误差降至 $O(\Delta h^2)$。Lumerical Conformal Variant 0/1/2 在介质/金属/PEC 界面分别采用不同共形规则；Tidy3D 默认开启 subpixel averaging。PoLaRIS 将实现 Volume-Average + Yu-Mittra 1/2 两种共形方案。

### 3.4 自动非均匀网格

按"每波长最少 N 个网格"（典型 N=10~20，金属/色散材料处加密至 N=30+）+ 局部 mesh override 框生成非均匀网格，CFL 时间步由最细网格决定。Lumerical `auto nonuniform` mesh accuracy 1-8 对应不同 N；Tidy3D `auto_nonuniform_mesh=True`（arXiv:2506.16665）。

---

## 4. Courant-Friedrichs-Lewy 稳定性条件

显式 leapfrog 格式稳定的必要条件（3D）：

$$\Delta t \le \frac{1}{c\sqrt{\frac{1}{\Delta x^2}+\frac{1}{\Delta y^2}+\frac{1}{\Delta z^2}}}$$

2D 退化为 $\Delta t \le# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$ 处理。

### 2.2 色散材料（辅助微分方程 ADE）

Drude-Lorentz 色散介质极化密度 $\mathbf{P}$ 满足二阶 ODE：

$$\frac{\partial^2 \mathbf{P}}{\partial t^2} + \gamma \frac{\partial \mathbf{P}}{\partial t} + \omega_0^2 \mathbf{P} = \varepsilon_0 \omega_p^2 \mathbf{E}$$

其中 $\omega_0$ 为共振频率，$\gamma$ 为阻尼率，$\omega_p$ 为等离子频率。$\mathbf{D}=\varepsilon_0\varepsilon_\infty\mathbf{E}+\mathbf{P}$，代入 Maxwell 旋度方程得 ADE-FDTD 更新格式（Lumerical MCM、Tidy3D PoleResidue 共同方案）。多系数材料 MCM 通过加和多个 Lorentz 极点拟合实测 $n(\omega)$ 数据。

### 2.3 非线性（Kerr + 拉曼）

三阶非线性 $\mathbf{P}_{NL}=\varepsilon_0\chi^{(3)}|\mathbf{E}|^2\mathbf{E}$（瞬时 Kerr）+ 卷积拉曼项，ADE 法处理。光子芯片中典型应用为 SiN 微环的克尔自相位调制、LNOI 的 $\chi^{(2)}$ 二次谐波。

---

## 3. Yee 网格离散化方案

### 3.1 Yee 1966 网格布局

3D Yee 单元中：电场分量 $E_x,E_y,E_z$ 位于棱中点，磁场分量 $H_x,H_y,H_z$ 位于面中心，空间半步错位。该布局使每个旋度运算的中心差分天然落在被求场位置，二阶精度 $O(\Delta h^2)$，且离散 Gauss 定律 $\nabla_h\cdot(\nabla_h\times\cdot)\equiv 0$ 自动满足（避免非物理电荷积累）。Yee 网格是 FDE/FDFD/FDTD/2.5D-FDTD 共同基础（ALGORITHMS.md 附录 C）。

### 3.2 E/H leapfrog 时间推进

时间半步错位，磁场在 $n+1/2$ 时刻更新，电场在 $n+1$ 时刻更新。以 $E_z$（TEz 2D）为例：

$$H_x^{n+1/2}\big|_{i,j+1/2} = D_{a,\mu}\, H_x^{n-1/2}\big|_{i,j+1/2} - D_{b,\mu}\,\frac{E_z^n|_{i,j+1}-E_z^n|_{i,j}}{\Delta y}$$

$$H_y^{n+1/2}\big|_{i+1/2,j} = D_{a,\mu}\, H_y^{n-1/2}\big|_{i+1/2,j} + D_{b,\mu}\,\frac{E_z^n|_{i+1,j}-E_z^n|_{i,j}}{\Delta x}$$

$$E_z^{n+1}\big|_{i,j} = C_{a,\varepsilon}\, E_z^n\big|_{i,j} + C_{b,\varepsilon}\left[\frac{H_y^{n+1/2}|_{i+1/2,j}-H_y^{n+1/2}|_{i-1/2,j}}{\Delta x} - \frac{H_x^{n+1/2}|_{i,j+1/2}-H_x^{n+1/2}|_{i,j-1/2}}{\Delta y}\right]$$

其中 $D_{a,\mu}=\frac{1-\sigma_m\Delta t/(2\mu_0)}{1+\sigma_m\Delta t/(2\mu_0)}$，$D_{b,\mu}=\frac{\Delta t/\mu_0}{1+\sigma_m\Delta t/(2\mu_0)}$，$C_{a,\varepsilon}=\frac{1-\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}{1+\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}$，$C_{b,\varepsilon}=\frac{\Delta t/(\varepsilon_0\varepsilon_r)}{1+\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}$。3D 形式按 6 个分量类似展开。

### 3.3 共形网格亚像素平滑（Yu-Mittra 1/2、Volume-Average）

阶梯近似在介质界面产生 $O(\Delta h)$ 误差。Yu-Mittra 1/2 共形方案：在 Yee 棱上的等效介电常数取界面两侧的体积加权平均，使界面处的等效 $\varepsilon$ 接近真实积分形式，误差降至 $O(\Delta h^2)$。Lumerical Conformal Variant 0/1/2 在介质/金属/PEC 界面分别采用不同共形规则；Tidy3D 默认开启 subpixel averaging。PoLaRIS 将实现 Volume-Average + Yu-Mittra 1/2 两种共形方案。

### 3.4 自动非均匀网格

按"每波长最少 N 个网格"（典型 N=10~20，金属/色散材料处加密至 N=30+）+ 局部 mesh override 框生成非均匀网格，CFL 时间步由最细网格决定。Lumerical `auto nonuniform` mesh accuracy 1-8 对应不同 N；Tidy3D `auto_nonuniform_mesh=True`（arXiv:2506.16665）。

---

## 4. Courant-Friedrichs-Lewy 稳定性条件

显式 leapfrog 格式稳定的必要条件（3D）：

$$\Delta t \le \frac{1}{c\sqrt{\frac{1}{\Delta x^2}+\frac{1}{\Delta y^2}+\frac{1}{\Delta z^2}}}$$

2D 退化为 $\Delta t \le [c\sqrt{1/\Delta x^2+1/\Delta y^2}]^{-1}$，1D 为 $\Delta t\# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$ 处理。

### 2.2 色散材料（辅助微分方程 ADE）

Drude-Lorentz 色散介质极化密度 $\mathbf{P}$ 满足二阶 ODE：

$$\frac{\partial^2 \mathbf{P}}{\partial t^2} + \gamma \frac{\partial \mathbf{P}}{\partial t} + \omega_0^2 \mathbf{P} = \varepsilon_0 \omega_p^2 \mathbf{E}$$

其中 $\omega_0$ 为共振频率，$\gamma$ 为阻尼率，$\omega_p$ 为等离子频率。$\mathbf{D}=\varepsilon_0\varepsilon_\infty\mathbf{E}+\mathbf{P}$，代入 Maxwell 旋度方程得 ADE-FDTD 更新格式（Lumerical MCM、Tidy3D PoleResidue 共同方案）。多系数材料 MCM 通过加和多个 Lorentz 极点拟合实测 $n(\omega)$ 数据。

### 2.3 非线性（Kerr + 拉曼）

三阶非线性 $\mathbf{P}_{NL}=\varepsilon_0\chi^{(3)}|\mathbf{E}|^2\mathbf{E}$（瞬时 Kerr）+ 卷积拉曼项，ADE 法处理。光子芯片中典型应用为 SiN 微环的克尔自相位调制、LNOI 的 $\chi^{(2)}$ 二次谐波。

---

## 3. Yee 网格离散化方案

### 3.1 Yee 1966 网格布局

3D Yee 单元中：电场分量 $E_x,E_y,E_z$ 位于棱中点，磁场分量 $H_x,H_y,H_z$ 位于面中心，空间半步错位。该布局使每个旋度运算的中心差分天然落在被求场位置，二阶精度 $O(\Delta h^2)$，且离散 Gauss 定律 $\nabla_h\cdot(\nabla_h\times\cdot)\equiv 0$ 自动满足（避免非物理电荷积累）。Yee 网格是 FDE/FDFD/FDTD/2.5D-FDTD 共同基础（ALGORITHMS.md 附录 C）。

### 3.2 E/H leapfrog 时间推进

时间半步错位，磁场在 $n+1/2$ 时刻更新，电场在 $n+1$ 时刻更新。以 $E_z$（TEz 2D）为例：

$$H_x^{n+1/2}\big|_{i,j+1/2} = D_{a,\mu}\, H_x^{n-1/2}\big|_{i,j+1/2} - D_{b,\mu}\,\frac{E_z^n|_{i,j+1}-E_z^n|_{i,j}}{\Delta y}$$

$$H_y^{n+1/2}\big|_{i+1/2,j} = D_{a,\mu}\, H_y^{n-1/2}\big|_{i+1/2,j} + D_{b,\mu}\,\frac{E_z^n|_{i+1,j}-E_z^n|_{i,j}}{\Delta x}$$

$$E_z^{n+1}\big|_{i,j} = C_{a,\varepsilon}\, E_z^n\big|_{i,j} + C_{b,\varepsilon}\left[\frac{H_y^{n+1/2}|_{i+1/2,j}-H_y^{n+1/2}|_{i-1/2,j}}{\Delta x} - \frac{H_x^{n+1/2}|_{i,j+1/2}-H_x^{n+1/2}|_{i,j-1/2}}{\Delta y}\right]$$

其中 $D_{a,\mu}=\frac{1-\sigma_m\Delta t/(2\mu_0)}{1+\sigma_m\Delta t/(2\mu_0)}$，$D_{b,\mu}=\frac{\Delta t/\mu_0}{1+\sigma_m\Delta t/(2\mu_0)}$，$C_{a,\varepsilon}=\frac{1-\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}{1+\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}$，$C_{b,\varepsilon}=\frac{\Delta t/(\varepsilon_0\varepsilon_r)}{1+\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}$。3D 形式按 6 个分量类似展开。

### 3.3 共形网格亚像素平滑（Yu-Mittra 1/2、Volume-Average）

阶梯近似在介质界面产生 $O(\Delta h)$ 误差。Yu-Mittra 1/2 共形方案：在 Yee 棱上的等效介电常数取界面两侧的体积加权平均，使界面处的等效 $\varepsilon$ 接近真实积分形式，误差降至 $O(\Delta h^2)$。Lumerical Conformal Variant 0/1/2 在介质/金属/PEC 界面分别采用不同共形规则；Tidy3D 默认开启 subpixel averaging。PoLaRIS 将实现 Volume-Average + Yu-Mittra 1/2 两种共形方案。

### 3.4 自动非均匀网格

按"每波长最少 N 个网格"（典型 N=10~20，金属/色散材料处加密至 N=30+）+ 局部 mesh override 框生成非均匀网格，CFL 时间步由最细网格决定。Lumerical `auto nonuniform` mesh accuracy 1-8 对应不同 N；Tidy3D `auto_nonuniform_mesh=True`（arXiv:2506.16665）。

---

## 4. Courant-Friedrichs-Lewy 稳定性条件

显式 leapfrog 格式稳定的必要条件（3D）：

$$\Delta t \le \frac{1}{c\sqrt{\frac{1}{\Delta x^2}+\frac{1}{\Delta y^2}+\frac{1}{\Delta z^2}}}$$

2D 退化为 $\Delta t \le [c\sqrt{1/\Delta x^2+1/\Delta y^2}]^{-1}$，1D 为 $\Delta t\le \Delta x/c$。工程上取# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$ 处理。

### 2.2 色散材料（辅助微分方程 ADE）

Drude-Lorentz 色散介质极化密度 $\mathbf{P}$ 满足二阶 ODE：

$$\frac{\partial^2 \mathbf{P}}{\partial t^2} + \gamma \frac{\partial \mathbf{P}}{\partial t} + \omega_0^2 \mathbf{P} = \varepsilon_0 \omega_p^2 \mathbf{E}$$

其中 $\omega_0$ 为共振频率，$\gamma$ 为阻尼率，$\omega_p$ 为等离子频率。$\mathbf{D}=\varepsilon_0\varepsilon_\infty\mathbf{E}+\mathbf{P}$，代入 Maxwell 旋度方程得 ADE-FDTD 更新格式（Lumerical MCM、Tidy3D PoleResidue 共同方案）。多系数材料 MCM 通过加和多个 Lorentz 极点拟合实测 $n(\omega)$ 数据。

### 2.3 非线性（Kerr + 拉曼）

三阶非线性 $\mathbf{P}_{NL}=\varepsilon_0\chi^{(3)}|\mathbf{E}|^2\mathbf{E}$（瞬时 Kerr）+ 卷积拉曼项，ADE 法处理。光子芯片中典型应用为 SiN 微环的克尔自相位调制、LNOI 的 $\chi^{(2)}$ 二次谐波。

---

## 3. Yee 网格离散化方案

### 3.1 Yee 1966 网格布局

3D Yee 单元中：电场分量 $E_x,E_y,E_z$ 位于棱中点，磁场分量 $H_x,H_y,H_z$ 位于面中心，空间半步错位。该布局使每个旋度运算的中心差分天然落在被求场位置，二阶精度 $O(\Delta h^2)$，且离散 Gauss 定律 $\nabla_h\cdot(\nabla_h\times\cdot)\equiv 0$ 自动满足（避免非物理电荷积累）。Yee 网格是 FDE/FDFD/FDTD/2.5D-FDTD 共同基础（ALGORITHMS.md 附录 C）。

### 3.2 E/H leapfrog 时间推进

时间半步错位，磁场在 $n+1/2$ 时刻更新，电场在 $n+1$ 时刻更新。以 $E_z$（TEz 2D）为例：

$$H_x^{n+1/2}\big|_{i,j+1/2} = D_{a,\mu}\, H_x^{n-1/2}\big|_{i,j+1/2} - D_{b,\mu}\,\frac{E_z^n|_{i,j+1}-E_z^n|_{i,j}}{\Delta y}$$

$$H_y^{n+1/2}\big|_{i+1/2,j} = D_{a,\mu}\, H_y^{n-1/2}\big|_{i+1/2,j} + D_{b,\mu}\,\frac{E_z^n|_{i+1,j}-E_z^n|_{i,j}}{\Delta x}$$

$$E_z^{n+1}\big|_{i,j} = C_{a,\varepsilon}\, E_z^n\big|_{i,j} + C_{b,\varepsilon}\left[\frac{H_y^{n+1/2}|_{i+1/2,j}-H_y^{n+1/2}|_{i-1/2,j}}{\Delta x} - \frac{H_x^{n+1/2}|_{i,j+1/2}-H_x^{n+1/2}|_{i,j-1/2}}{\Delta y}\right]$$

其中 $D_{a,\mu}=\frac{1-\sigma_m\Delta t/(2\mu_0)}{1+\sigma_m\Delta t/(2\mu_0)}$，$D_{b,\mu}=\frac{\Delta t/\mu_0}{1+\sigma_m\Delta t/(2\mu_0)}$，$C_{a,\varepsilon}=\frac{1-\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}{1+\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}$，$C_{b,\varepsilon}=\frac{\Delta t/(\varepsilon_0\varepsilon_r)}{1+\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}$。3D 形式按 6 个分量类似展开。

### 3.3 共形网格亚像素平滑（Yu-Mittra 1/2、Volume-Average）

阶梯近似在介质界面产生 $O(\Delta h)$ 误差。Yu-Mittra 1/2 共形方案：在 Yee 棱上的等效介电常数取界面两侧的体积加权平均，使界面处的等效 $\varepsilon$ 接近真实积分形式，误差降至 $O(\Delta h^2)$。Lumerical Conformal Variant 0/1/2 在介质/金属/PEC 界面分别采用不同共形规则；Tidy3D 默认开启 subpixel averaging。PoLaRIS 将实现 Volume-Average + Yu-Mittra 1/2 两种共形方案。

### 3.4 自动非均匀网格

按"每波长最少 N 个网格"（典型 N=10~20，金属/色散材料处加密至 N=30+）+ 局部 mesh override 框生成非均匀网格，CFL 时间步由最细网格决定。Lumerical `auto nonuniform` mesh accuracy 1-8 对应不同 N；Tidy3D `auto_nonuniform_mesh=True`（arXiv:2506.16665）。

---

## 4. Courant-Friedrichs-Lewy 稳定性条件

显式 leapfrog 格式稳定的必要条件（3D）：

$$\Delta t \le \frac{1}{c\sqrt{\frac{1}{\Delta x^2}+\frac{1}{\Delta y^2}+\frac{1}{\Delta z^2}}}$$

2D 退化为 $\Delta t \le [c\sqrt{1/\Delta x^2+1/\Delta y^2}]^{-1}$，1D 为 $\Delta t\le \Delta x/c$。工程上取 0.95~0.99 倍 CFL 上限以保留稳定裕度。Cour# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$ 处理。

### 2.2 色散材料（辅助微分方程 ADE）

Drude-Lorentz 色散介质极化密度 $\mathbf{P}$ 满足二阶 ODE：

$$\frac{\partial^2 \mathbf{P}}{\partial t^2} + \gamma \frac{\partial \mathbf{P}}{\partial t} + \omega_0^2 \mathbf{P} = \varepsilon_0 \omega_p^2 \mathbf{E}$$

其中 $\omega_0$ 为共振频率，$\gamma$ 为阻尼率，$\omega_p$ 为等离子频率。$\mathbf{D}=\varepsilon_0\varepsilon_\infty\mathbf{E}+\mathbf{P}$，代入 Maxwell 旋度方程得 ADE-FDTD 更新格式（Lumerical MCM、Tidy3D PoleResidue 共同方案）。多系数材料 MCM 通过加和多个 Lorentz 极点拟合实测 $n(\omega)$ 数据。

### 2.3 非线性（Kerr + 拉曼）

三阶非线性 $\mathbf{P}_{NL}=\varepsilon_0\chi^{(3)}|\mathbf{E}|^2\mathbf{E}$（瞬时 Kerr）+ 卷积拉曼项，ADE 法处理。光子芯片中典型应用为 SiN 微环的克尔自相位调制、LNOI 的 $\chi^{(2)}$ 二次谐波。

---

## 3. Yee 网格离散化方案

### 3.1 Yee 1966 网格布局

3D Yee 单元中：电场分量 $E_x,E_y,E_z$ 位于棱中点，磁场分量 $H_x,H_y,H_z$ 位于面中心，空间半步错位。该布局使每个旋度运算的中心差分天然落在被求场位置，二阶精度 $O(\Delta h^2)$，且离散 Gauss 定律 $\nabla_h\cdot(\nabla_h\times\cdot)\equiv 0$ 自动满足（避免非物理电荷积累）。Yee 网格是 FDE/FDFD/FDTD/2.5D-FDTD 共同基础（ALGORITHMS.md 附录 C）。

### 3.2 E/H leapfrog 时间推进

时间半步错位，磁场在 $n+1/2$ 时刻更新，电场在 $n+1$ 时刻更新。以 $E_z$（TEz 2D）为例：

$$H_x^{n+1/2}\big|_{i,j+1/2} = D_{a,\mu}\, H_x^{n-1/2}\big|_{i,j+1/2} - D_{b,\mu}\,\frac{E_z^n|_{i,j+1}-E_z^n|_{i,j}}{\Delta y}$$

$$H_y^{n+1/2}\big|_{i+1/2,j} = D_{a,\mu}\, H_y^{n-1/2}\big|_{i+1/2,j} + D_{b,\mu}\,\frac{E_z^n|_{i+1,j}-E_z^n|_{i,j}}{\Delta x}$$

$$E_z^{n+1}\big|_{i,j} = C_{a,\varepsilon}\, E_z^n\big|_{i,j} + C_{b,\varepsilon}\left[\frac{H_y^{n+1/2}|_{i+1/2,j}-H_y^{n+1/2}|_{i-1/2,j}}{\Delta x} - \frac{H_x^{n+1/2}|_{i,j+1/2}-H_x^{n+1/2}|_{i,j-1/2}}{\Delta y}\right]$$

其中 $D_{a,\mu}=\frac{1-\sigma_m\Delta t/(2\mu_0)}{1+\sigma_m\Delta t/(2\mu_0)}$，$D_{b,\mu}=\frac{\Delta t/\mu_0}{1+\sigma_m\Delta t/(2\mu_0)}$，$C_{a,\varepsilon}=\frac{1-\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}{1+\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}$，$C_{b,\varepsilon}=\frac{\Delta t/(\varepsilon_0\varepsilon_r)}{1+\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}$。3D 形式按 6 个分量类似展开。

### 3.3 共形网格亚像素平滑（Yu-Mittra 1/2、Volume-Average）

阶梯近似在介质界面产生 $O(\Delta h)$ 误差。Yu-Mittra 1/2 共形方案：在 Yee 棱上的等效介电常数取界面两侧的体积加权平均，使界面处的等效 $\varepsilon$ 接近真实积分形式，误差降至 $O(\Delta h^2)$。Lumerical Conformal Variant 0/1/2 在介质/金属/PEC 界面分别采用不同共形规则；Tidy3D 默认开启 subpixel averaging。PoLaRIS 将实现 Volume-Average + Yu-Mittra 1/2 两种共形方案。

### 3.4 自动非均匀网格

按"每波长最少 N 个网格"（典型 N=10~20，金属/色散材料处加密至 N=30+）+ 局部 mesh override 框生成非均匀网格，CFL 时间步由最细网格决定。Lumerical `auto nonuniform` mesh accuracy 1-8 对应不同 N；Tidy3D `auto_nonuniform_mesh=True`（arXiv:2506.16665）。

---

## 4. Courant-Friedrichs-Lewy 稳定性条件

显式 leapfrog 格式稳定的必要条件（3D）：

$$\Delta t \le \frac{1}{c\sqrt{\frac{1}{\Delta x^2}+\frac{1}{\Delta y^2}+\frac{1}{\Delta z^2}}}$$

2D 退化为 $\Delta t \le [c\sqrt{1/\Delta x^2+1/\Delta y^2}]^{-1}$，1D 为 $\Delta t\le \Delta x/c$。工程上取 0.95~0.99 倍 CFL 上限以保留稳定裕度。Courant 数 $S=c\Delta t/\Delta h_{\min}$ 反映每步波# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$ 处理。

### 2.2 色散材料（辅助微分方程 ADE）

Drude-Lorentz 色散介质极化密度 $\mathbf{P}$ 满足二阶 ODE：

$$\frac{\partial^2 \mathbf{P}}{\partial t^2} + \gamma \frac{\partial \mathbf{P}}{\partial t} + \omega_0^2 \mathbf{P} = \varepsilon_0 \omega_p^2 \mathbf{E}$$

其中 $\omega_0$ 为共振频率，$\gamma$ 为阻尼率，$\omega_p$ 为等离子频率。$\mathbf{D}=\varepsilon_0\varepsilon_\infty\mathbf{E}+\mathbf{P}$，代入 Maxwell 旋度方程得 ADE-FDTD 更新格式（Lumerical MCM、Tidy3D PoleResidue 共同方案）。多系数材料 MCM 通过加和多个 Lorentz 极点拟合实测 $n(\omega)$ 数据。

### 2.3 非线性（Kerr + 拉曼）

三阶非线性 $\mathbf{P}_{NL}=\varepsilon_0\chi^{(3)}|\mathbf{E}|^2\mathbf{E}$（瞬时 Kerr）+ 卷积拉曼项，ADE 法处理。光子芯片中典型应用为 SiN 微环的克尔自相位调制、LNOI 的 $\chi^{(2)}$ 二次谐波。

---

## 3. Yee 网格离散化方案

### 3.1 Yee 1966 网格布局

3D Yee 单元中：电场分量 $E_x,E_y,E_z$ 位于棱中点，磁场分量 $H_x,H_y,H_z$ 位于面中心，空间半步错位。该布局使每个旋度运算的中心差分天然落在被求场位置，二阶精度 $O(\Delta h^2)$，且离散 Gauss 定律 $\nabla_h\cdot(\nabla_h\times\cdot)\equiv 0$ 自动满足（避免非物理电荷积累）。Yee 网格是 FDE/FDFD/FDTD/2.5D-FDTD 共同基础（ALGORITHMS.md 附录 C）。

### 3.2 E/H leapfrog 时间推进

时间半步错位，磁场在 $n+1/2$ 时刻更新，电场在 $n+1$ 时刻更新。以 $E_z$（TEz 2D）为例：

$$H_x^{n+1/2}\big|_{i,j+1/2} = D_{a,\mu}\, H_x^{n-1/2}\big|_{i,j+1/2} - D_{b,\mu}\,\frac{E_z^n|_{i,j+1}-E_z^n|_{i,j}}{\Delta y}$$

$$H_y^{n+1/2}\big|_{i+1/2,j} = D_{a,\mu}\, H_y^{n-1/2}\big|_{i+1/2,j} + D_{b,\mu}\,\frac{E_z^n|_{i+1,j}-E_z^n|_{i,j}}{\Delta x}$$

$$E_z^{n+1}\big|_{i,j} = C_{a,\varepsilon}\, E_z^n\big|_{i,j} + C_{b,\varepsilon}\left[\frac{H_y^{n+1/2}|_{i+1/2,j}-H_y^{n+1/2}|_{i-1/2,j}}{\Delta x} - \frac{H_x^{n+1/2}|_{i,j+1/2}-H_x^{n+1/2}|_{i,j-1/2}}{\Delta y}\right]$$

其中 $D_{a,\mu}=\frac{1-\sigma_m\Delta t/(2\mu_0)}{1+\sigma_m\Delta t/(2\mu_0)}$，$D_{b,\mu}=\frac{\Delta t/\mu_0}{1+\sigma_m\Delta t/(2\mu_0)}$，$C_{a,\varepsilon}=\frac{1-\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}{1+\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}$，$C_{b,\varepsilon}=\frac{\Delta t/(\varepsilon_0\varepsilon_r)}{1+\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}$。3D 形式按 6 个分量类似展开。

### 3.3 共形网格亚像素平滑（Yu-Mittra 1/2、Volume-Average）

阶梯近似在介质界面产生 $O(\Delta h)$ 误差。Yu-Mittra 1/2 共形方案：在 Yee 棱上的等效介电常数取界面两侧的体积加权平均，使界面处的等效 $\varepsilon$ 接近真实积分形式，误差降至 $O(\Delta h^2)$。Lumerical Conformal Variant 0/1/2 在介质/金属/PEC 界面分别采用不同共形规则；Tidy3D 默认开启 subpixel averaging。PoLaRIS 将实现 Volume-Average + Yu-Mittra 1/2 两种共形方案。

### 3.4 自动非均匀网格

按"每波长最少 N 个网格"（典型 N=10~20，金属/色散材料处加密至 N=30+）+ 局部 mesh override 框生成非均匀网格，CFL 时间步由最细网格决定。Lumerical `auto nonuniform` mesh accuracy 1-8 对应不同 N；Tidy3D `auto_nonuniform_mesh=True`（arXiv:2506.16665）。

---

## 4. Courant-Friedrichs-Lewy 稳定性条件

显式 leapfrog 格式稳定的必要条件（3D）：

$$\Delta t \le \frac{1}{c\sqrt{\frac{1}{\Delta x^2}+\frac{1}{\Delta y^2}+\frac{1}{\Delta z^2}}}$$

2D 退化为 $\Delta t \le [c\sqrt{1/\Delta x^2+1/\Delta y^2}]^{-1}$，1D 为 $\Delta t\le \Delta x/c$。工程上取 0.95~0.99 倍 CFL 上限以保留稳定裕度。Courant 数 $S=c\Delta t/\Delta h_{\min}$ 反映每步波传播距离与最小网格之比。

**色# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$ 处理。

### 2.2 色散材料（辅助微分方程 ADE）

Drude-Lorentz 色散介质极化密度 $\mathbf{P}$ 满足二阶 ODE：

$$\frac{\partial^2 \mathbf{P}}{\partial t^2} + \gamma \frac{\partial \mathbf{P}}{\partial t} + \omega_0^2 \mathbf{P} = \varepsilon_0 \omega_p^2 \mathbf{E}$$

其中 $\omega_0$ 为共振频率，$\gamma$ 为阻尼率，$\omega_p$ 为等离子频率。$\mathbf{D}=\varepsilon_0\varepsilon_\infty\mathbf{E}+\mathbf{P}$，代入 Maxwell 旋度方程得 ADE-FDTD 更新格式（Lumerical MCM、Tidy3D PoleResidue 共同方案）。多系数材料 MCM 通过加和多个 Lorentz 极点拟合实测 $n(\omega)$ 数据。

### 2.3 非线性（Kerr + 拉曼）

三阶非线性 $\mathbf{P}_{NL}=\varepsilon_0\chi^{(3)}|\mathbf{E}|^2\mathbf{E}$（瞬时 Kerr）+ 卷积拉曼项，ADE 法处理。光子芯片中典型应用为 SiN 微环的克尔自相位调制、LNOI 的 $\chi^{(2)}$ 二次谐波。

---

## 3. Yee 网格离散化方案

### 3.1 Yee 1966 网格布局

3D Yee 单元中：电场分量 $E_x,E_y,E_z$ 位于棱中点，磁场分量 $H_x,H_y,H_z$ 位于面中心，空间半步错位。该布局使每个旋度运算的中心差分天然落在被求场位置，二阶精度 $O(\Delta h^2)$，且离散 Gauss 定律 $\nabla_h\cdot(\nabla_h\times\cdot)\equiv 0$ 自动满足（避免非物理电荷积累）。Yee 网格是 FDE/FDFD/FDTD/2.5D-FDTD 共同基础（ALGORITHMS.md 附录 C）。

### 3.2 E/H leapfrog 时间推进

时间半步错位，磁场在 $n+1/2$ 时刻更新，电场在 $n+1$ 时刻更新。以 $E_z$（TEz 2D）为例：

$$H_x^{n+1/2}\big|_{i,j+1/2} = D_{a,\mu}\, H_x^{n-1/2}\big|_{i,j+1/2} - D_{b,\mu}\,\frac{E_z^n|_{i,j+1}-E_z^n|_{i,j}}{\Delta y}$$

$$H_y^{n+1/2}\big|_{i+1/2,j} = D_{a,\mu}\, H_y^{n-1/2}\big|_{i+1/2,j} + D_{b,\mu}\,\frac{E_z^n|_{i+1,j}-E_z^n|_{i,j}}{\Delta x}$$

$$E_z^{n+1}\big|_{i,j} = C_{a,\varepsilon}\, E_z^n\big|_{i,j} + C_{b,\varepsilon}\left[\frac{H_y^{n+1/2}|_{i+1/2,j}-H_y^{n+1/2}|_{i-1/2,j}}{\Delta x} - \frac{H_x^{n+1/2}|_{i,j+1/2}-H_x^{n+1/2}|_{i,j-1/2}}{\Delta y}\right]$$

其中 $D_{a,\mu}=\frac{1-\sigma_m\Delta t/(2\mu_0)}{1+\sigma_m\Delta t/(2\mu_0)}$，$D_{b,\mu}=\frac{\Delta t/\mu_0}{1+\sigma_m\Delta t/(2\mu_0)}$，$C_{a,\varepsilon}=\frac{1-\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}{1+\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}$，$C_{b,\varepsilon}=\frac{\Delta t/(\varepsilon_0\varepsilon_r)}{1+\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}$。3D 形式按 6 个分量类似展开。

### 3.3 共形网格亚像素平滑（Yu-Mittra 1/2、Volume-Average）

阶梯近似在介质界面产生 $O(\Delta h)$ 误差。Yu-Mittra 1/2 共形方案：在 Yee 棱上的等效介电常数取界面两侧的体积加权平均，使界面处的等效 $\varepsilon$ 接近真实积分形式，误差降至 $O(\Delta h^2)$。Lumerical Conformal Variant 0/1/2 在介质/金属/PEC 界面分别采用不同共形规则；Tidy3D 默认开启 subpixel averaging。PoLaRIS 将实现 Volume-Average + Yu-Mittra 1/2 两种共形方案。

### 3.4 自动非均匀网格

按"每波长最少 N 个网格"（典型 N=10~20，金属/色散材料处加密至 N=30+）+ 局部 mesh override 框生成非均匀网格，CFL 时间步由最细网格决定。Lumerical `auto nonuniform` mesh accuracy 1-8 对应不同 N；Tidy3D `auto_nonuniform_mesh=True`（arXiv:2506.16665）。

---

## 4. Courant-Friedrichs-Lewy 稳定性条件

显式 leapfrog 格式稳定的必要条件（3D）：

$$\Delta t \le \frac{1}{c\sqrt{\frac{1}{\Delta x^2}+\frac{1}{\Delta y^2}+\frac{1}{\Delta z^2}}}$$

2D 退化为 $\Delta t \le [c\sqrt{1/\Delta x^2+1/\Delta y^2}]^{-1}$，1D 为 $\Delta t\le \Delta x/c$。工程上取 0.95~0.99 倍 CFL 上限以保留稳定裕度。Courant 数 $S=c\Delta t/\Delta h_{\min}$ 反映每步波传播距离与最小网格之比。

**色散误差**：数值相速 $v_p# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$ 处理。

### 2.2 色散材料（辅助微分方程 ADE）

Drude-Lorentz 色散介质极化密度 $\mathbf{P}$ 满足二阶 ODE：

$$\frac{\partial^2 \mathbf{P}}{\partial t^2} + \gamma \frac{\partial \mathbf{P}}{\partial t} + \omega_0^2 \mathbf{P} = \varepsilon_0 \omega_p^2 \mathbf{E}$$

其中 $\omega_0$ 为共振频率，$\gamma$ 为阻尼率，$\omega_p$ 为等离子频率。$\mathbf{D}=\varepsilon_0\varepsilon_\infty\mathbf{E}+\mathbf{P}$，代入 Maxwell 旋度方程得 ADE-FDTD 更新格式（Lumerical MCM、Tidy3D PoleResidue 共同方案）。多系数材料 MCM 通过加和多个 Lorentz 极点拟合实测 $n(\omega)$ 数据。

### 2.3 非线性（Kerr + 拉曼）

三阶非线性 $\mathbf{P}_{NL}=\varepsilon_0\chi^{(3)}|\mathbf{E}|^2\mathbf{E}$（瞬时 Kerr）+ 卷积拉曼项，ADE 法处理。光子芯片中典型应用为 SiN 微环的克尔自相位调制、LNOI 的 $\chi^{(2)}$ 二次谐波。

---

## 3. Yee 网格离散化方案

### 3.1 Yee 1966 网格布局

3D Yee 单元中：电场分量 $E_x,E_y,E_z$ 位于棱中点，磁场分量 $H_x,H_y,H_z$ 位于面中心，空间半步错位。该布局使每个旋度运算的中心差分天然落在被求场位置，二阶精度 $O(\Delta h^2)$，且离散 Gauss 定律 $\nabla_h\cdot(\nabla_h\times\cdot)\equiv 0$ 自动满足（避免非物理电荷积累）。Yee 网格是 FDE/FDFD/FDTD/2.5D-FDTD 共同基础（ALGORITHMS.md 附录 C）。

### 3.2 E/H leapfrog 时间推进

时间半步错位，磁场在 $n+1/2$ 时刻更新，电场在 $n+1$ 时刻更新。以 $E_z$（TEz 2D）为例：

$$H_x^{n+1/2}\big|_{i,j+1/2} = D_{a,\mu}\, H_x^{n-1/2}\big|_{i,j+1/2} - D_{b,\mu}\,\frac{E_z^n|_{i,j+1}-E_z^n|_{i,j}}{\Delta y}$$

$$H_y^{n+1/2}\big|_{i+1/2,j} = D_{a,\mu}\, H_y^{n-1/2}\big|_{i+1/2,j} + D_{b,\mu}\,\frac{E_z^n|_{i+1,j}-E_z^n|_{i,j}}{\Delta x}$$

$$E_z^{n+1}\big|_{i,j} = C_{a,\varepsilon}\, E_z^n\big|_{i,j} + C_{b,\varepsilon}\left[\frac{H_y^{n+1/2}|_{i+1/2,j}-H_y^{n+1/2}|_{i-1/2,j}}{\Delta x} - \frac{H_x^{n+1/2}|_{i,j+1/2}-H_x^{n+1/2}|_{i,j-1/2}}{\Delta y}\right]$$

其中 $D_{a,\mu}=\frac{1-\sigma_m\Delta t/(2\mu_0)}{1+\sigma_m\Delta t/(2\mu_0)}$，$D_{b,\mu}=\frac{\Delta t/\mu_0}{1+\sigma_m\Delta t/(2\mu_0)}$，$C_{a,\varepsilon}=\frac{1-\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}{1+\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}$，$C_{b,\varepsilon}=\frac{\Delta t/(\varepsilon_0\varepsilon_r)}{1+\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}$。3D 形式按 6 个分量类似展开。

### 3.3 共形网格亚像素平滑（Yu-Mittra 1/2、Volume-Average）

阶梯近似在介质界面产生 $O(\Delta h)$ 误差。Yu-Mittra 1/2 共形方案：在 Yee 棱上的等效介电常数取界面两侧的体积加权平均，使界面处的等效 $\varepsilon$ 接近真实积分形式，误差降至 $O(\Delta h^2)$。Lumerical Conformal Variant 0/1/2 在介质/金属/PEC 界面分别采用不同共形规则；Tidy3D 默认开启 subpixel averaging。PoLaRIS 将实现 Volume-Average + Yu-Mittra 1/2 两种共形方案。

### 3.4 自动非均匀网格

按"每波长最少 N 个网格"（典型 N=10~20，金属/色散材料处加密至 N=30+）+ 局部 mesh override 框生成非均匀网格，CFL 时间步由最细网格决定。Lumerical `auto nonuniform` mesh accuracy 1-8 对应不同 N；Tidy3D `auto_nonuniform_mesh=True`（arXiv:2506.16665）。

---

## 4. Courant-Friedrichs-Lewy 稳定性条件

显式 leapfrog 格式稳定的必要条件（3D）：

$$\Delta t \le \frac{1}{c\sqrt{\frac{1}{\Delta x^2}+\frac{1}{\Delta y^2}+\frac{1}{\Delta z^2}}}$$

2D 退化为 $\Delta t \le [c\sqrt{1/\Delta x^2+1/\Delta y^2}]^{-1}$，1D 为 $\Delta t\le \Delta x/c$。工程上取 0.95~0.99 倍 CFL 上限以保留稳定裕度。Courant 数 $S=c\Delta t/\Delta h_{\min}$ 反映每步波传播距离与最小网格之比。

**色散误差**：数值相速 $v_p/c \approx 1 - \tfrac{# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$ 处理。

### 2.2 色散材料（辅助微分方程 ADE）

Drude-Lorentz 色散介质极化密度 $\mathbf{P}$ 满足二阶 ODE：

$$\frac{\partial^2 \mathbf{P}}{\partial t^2} + \gamma \frac{\partial \mathbf{P}}{\partial t} + \omega_0^2 \mathbf{P} = \varepsilon_0 \omega_p^2 \mathbf{E}$$

其中 $\omega_0$ 为共振频率，$\gamma$ 为阻尼率，$\omega_p$ 为等离子频率。$\mathbf{D}=\varepsilon_0\varepsilon_\infty\mathbf{E}+\mathbf{P}$，代入 Maxwell 旋度方程得 ADE-FDTD 更新格式（Lumerical MCM、Tidy3D PoleResidue 共同方案）。多系数材料 MCM 通过加和多个 Lorentz 极点拟合实测 $n(\omega)$ 数据。

### 2.3 非线性（Kerr + 拉曼）

三阶非线性 $\mathbf{P}_{NL}=\varepsilon_0\chi^{(3)}|\mathbf{E}|^2\mathbf{E}$（瞬时 Kerr）+ 卷积拉曼项，ADE 法处理。光子芯片中典型应用为 SiN 微环的克尔自相位调制、LNOI 的 $\chi^{(2)}$ 二次谐波。

---

## 3. Yee 网格离散化方案

### 3.1 Yee 1966 网格布局

3D Yee 单元中：电场分量 $E_x,E_y,E_z$ 位于棱中点，磁场分量 $H_x,H_y,H_z$ 位于面中心，空间半步错位。该布局使每个旋度运算的中心差分天然落在被求场位置，二阶精度 $O(\Delta h^2)$，且离散 Gauss 定律 $\nabla_h\cdot(\nabla_h\times\cdot)\equiv 0$ 自动满足（避免非物理电荷积累）。Yee 网格是 FDE/FDFD/FDTD/2.5D-FDTD 共同基础（ALGORITHMS.md 附录 C）。

### 3.2 E/H leapfrog 时间推进

时间半步错位，磁场在 $n+1/2$ 时刻更新，电场在 $n+1$ 时刻更新。以 $E_z$（TEz 2D）为例：

$$H_x^{n+1/2}\big|_{i,j+1/2} = D_{a,\mu}\, H_x^{n-1/2}\big|_{i,j+1/2} - D_{b,\mu}\,\frac{E_z^n|_{i,j+1}-E_z^n|_{i,j}}{\Delta y}$$

$$H_y^{n+1/2}\big|_{i+1/2,j} = D_{a,\mu}\, H_y^{n-1/2}\big|_{i+1/2,j} + D_{b,\mu}\,\frac{E_z^n|_{i+1,j}-E_z^n|_{i,j}}{\Delta x}$$

$$E_z^{n+1}\big|_{i,j} = C_{a,\varepsilon}\, E_z^n\big|_{i,j} + C_{b,\varepsilon}\left[\frac{H_y^{n+1/2}|_{i+1/2,j}-H_y^{n+1/2}|_{i-1/2,j}}{\Delta x} - \frac{H_x^{n+1/2}|_{i,j+1/2}-H_x^{n+1/2}|_{i,j-1/2}}{\Delta y}\right]$$

其中 $D_{a,\mu}=\frac{1-\sigma_m\Delta t/(2\mu_0)}{1+\sigma_m\Delta t/(2\mu_0)}$，$D_{b,\mu}=\frac{\Delta t/\mu_0}{1+\sigma_m\Delta t/(2\mu_0)}$，$C_{a,\varepsilon}=\frac{1-\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}{1+\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}$，$C_{b,\varepsilon}=\frac{\Delta t/(\varepsilon_0\varepsilon_r)}{1+\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}$。3D 形式按 6 个分量类似展开。

### 3.3 共形网格亚像素平滑（Yu-Mittra 1/2、Volume-Average）

阶梯近似在介质界面产生 $O(\Delta h)$ 误差。Yu-Mittra 1/2 共形方案：在 Yee 棱上的等效介电常数取界面两侧的体积加权平均，使界面处的等效 $\varepsilon$ 接近真实积分形式，误差降至 $O(\Delta h^2)$。Lumerical Conformal Variant 0/1/2 在介质/金属/PEC 界面分别采用不同共形规则；Tidy3D 默认开启 subpixel averaging。PoLaRIS 将实现 Volume-Average + Yu-Mittra 1/2 两种共形方案。

### 3.4 自动非均匀网格

按"每波长最少 N 个网格"（典型 N=10~20，金属/色散材料处加密至 N=30+）+ 局部 mesh override 框生成非均匀网格，CFL 时间步由最细网格决定。Lumerical `auto nonuniform` mesh accuracy 1-8 对应不同 N；Tidy3D `auto_nonuniform_mesh=True`（arXiv:2506.16665）。

---

## 4. Courant-Friedrichs-Lewy 稳定性条件

显式 leapfrog 格式稳定的必要条件（3D）：

$$\Delta t \le \frac{1}{c\sqrt{\frac{1}{\Delta x^2}+\frac{1}{\Delta y^2}+\frac{1}{\Delta z^2}}}$$

2D 退化为 $\Delta t \le [c\sqrt{1/\Delta x^2+1/\Delta y^2}]^{-1}$，1D 为 $\Delta t\le \Delta x/c$。工程上取 0.95~0.99 倍 CFL 上限以保留稳定裕度。Courant 数 $S=c\Delta t/\Delta h_{\min}$ 反映每步波传播距离与最小网格之比。

**色散误差**：数值相速 $v_p/c \approx 1 - \tfrac{1}{24}(2\pi\Delta h# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$ 处理。

### 2.2 色散材料（辅助微分方程 ADE）

Drude-Lorentz 色散介质极化密度 $\mathbf{P}$ 满足二阶 ODE：

$$\frac{\partial^2 \mathbf{P}}{\partial t^2} + \gamma \frac{\partial \mathbf{P}}{\partial t} + \omega_0^2 \mathbf{P} = \varepsilon_0 \omega_p^2 \mathbf{E}$$

其中 $\omega_0$ 为共振频率，$\gamma$ 为阻尼率，$\omega_p$ 为等离子频率。$\mathbf{D}=\varepsilon_0\varepsilon_\infty\mathbf{E}+\mathbf{P}$，代入 Maxwell 旋度方程得 ADE-FDTD 更新格式（Lumerical MCM、Tidy3D PoleResidue 共同方案）。多系数材料 MCM 通过加和多个 Lorentz 极点拟合实测 $n(\omega)$ 数据。

### 2.3 非线性（Kerr + 拉曼）

三阶非线性 $\mathbf{P}_{NL}=\varepsilon_0\chi^{(3)}|\mathbf{E}|^2\mathbf{E}$（瞬时 Kerr）+ 卷积拉曼项，ADE 法处理。光子芯片中典型应用为 SiN 微环的克尔自相位调制、LNOI 的 $\chi^{(2)}$ 二次谐波。

---

## 3. Yee 网格离散化方案

### 3.1 Yee 1966 网格布局

3D Yee 单元中：电场分量 $E_x,E_y,E_z$ 位于棱中点，磁场分量 $H_x,H_y,H_z$ 位于面中心，空间半步错位。该布局使每个旋度运算的中心差分天然落在被求场位置，二阶精度 $O(\Delta h^2)$，且离散 Gauss 定律 $\nabla_h\cdot(\nabla_h\times\cdot)\equiv 0$ 自动满足（避免非物理电荷积累）。Yee 网格是 FDE/FDFD/FDTD/2.5D-FDTD 共同基础（ALGORITHMS.md 附录 C）。

### 3.2 E/H leapfrog 时间推进

时间半步错位，磁场在 $n+1/2$ 时刻更新，电场在 $n+1$ 时刻更新。以 $E_z$（TEz 2D）为例：

$$H_x^{n+1/2}\big|_{i,j+1/2} = D_{a,\mu}\, H_x^{n-1/2}\big|_{i,j+1/2} - D_{b,\mu}\,\frac{E_z^n|_{i,j+1}-E_z^n|_{i,j}}{\Delta y}$$

$$H_y^{n+1/2}\big|_{i+1/2,j} = D_{a,\mu}\, H_y^{n-1/2}\big|_{i+1/2,j} + D_{b,\mu}\,\frac{E_z^n|_{i+1,j}-E_z^n|_{i,j}}{\Delta x}$$

$$E_z^{n+1}\big|_{i,j} = C_{a,\varepsilon}\, E_z^n\big|_{i,j} + C_{b,\varepsilon}\left[\frac{H_y^{n+1/2}|_{i+1/2,j}-H_y^{n+1/2}|_{i-1/2,j}}{\Delta x} - \frac{H_x^{n+1/2}|_{i,j+1/2}-H_x^{n+1/2}|_{i,j-1/2}}{\Delta y}\right]$$

其中 $D_{a,\mu}=\frac{1-\sigma_m\Delta t/(2\mu_0)}{1+\sigma_m\Delta t/(2\mu_0)}$，$D_{b,\mu}=\frac{\Delta t/\mu_0}{1+\sigma_m\Delta t/(2\mu_0)}$，$C_{a,\varepsilon}=\frac{1-\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}{1+\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}$，$C_{b,\varepsilon}=\frac{\Delta t/(\varepsilon_0\varepsilon_r)}{1+\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}$。3D 形式按 6 个分量类似展开。

### 3.3 共形网格亚像素平滑（Yu-Mittra 1/2、Volume-Average）

阶梯近似在介质界面产生 $O(\Delta h)$ 误差。Yu-Mittra 1/2 共形方案：在 Yee 棱上的等效介电常数取界面两侧的体积加权平均，使界面处的等效 $\varepsilon$ 接近真实积分形式，误差降至 $O(\Delta h^2)$。Lumerical Conformal Variant 0/1/2 在介质/金属/PEC 界面分别采用不同共形规则；Tidy3D 默认开启 subpixel averaging。PoLaRIS 将实现 Volume-Average + Yu-Mittra 1/2 两种共形方案。

### 3.4 自动非均匀网格

按"每波长最少 N 个网格"（典型 N=10~20，金属/色散材料处加密至 N=30+）+ 局部 mesh override 框生成非均匀网格，CFL 时间步由最细网格决定。Lumerical `auto nonuniform` mesh accuracy 1-8 对应不同 N；Tidy3D `auto_nonuniform_mesh=True`（arXiv:2506.16665）。

---

## 4. Courant-Friedrichs-Lewy 稳定性条件

显式 leapfrog 格式稳定的必要条件（3D）：

$$\Delta t \le \frac{1}{c\sqrt{\frac{1}{\Delta x^2}+\frac{1}{\Delta y^2}+\frac{1}{\Delta z^2}}}$$

2D 退化为 $\Delta t \le [c\sqrt{1/\Delta x^2+1/\Delta y^2}]^{-1}$，1D 为 $\Delta t\le \Delta x/c$。工程上取 0.95~0.99 倍 CFL 上限以保留稳定裕度。Courant 数 $S=c\Delta t/\Delta h_{\min}$ 反映每步波传播距离与最小网格之比。

**色散误差**：数值相速 $v_p/c \approx 1 - \tfrac{1}{24}(2\pi\Delta h/\lambda)^2 \cdot [\sin^2# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$ 处理。

### 2.2 色散材料（辅助微分方程 ADE）

Drude-Lorentz 色散介质极化密度 $\mathbf{P}$ 满足二阶 ODE：

$$\frac{\partial^2 \mathbf{P}}{\partial t^2} + \gamma \frac{\partial \mathbf{P}}{\partial t} + \omega_0^2 \mathbf{P} = \varepsilon_0 \omega_p^2 \mathbf{E}$$

其中 $\omega_0$ 为共振频率，$\gamma$ 为阻尼率，$\omega_p$ 为等离子频率。$\mathbf{D}=\varepsilon_0\varepsilon_\infty\mathbf{E}+\mathbf{P}$，代入 Maxwell 旋度方程得 ADE-FDTD 更新格式（Lumerical MCM、Tidy3D PoleResidue 共同方案）。多系数材料 MCM 通过加和多个 Lorentz 极点拟合实测 $n(\omega)$ 数据。

### 2.3 非线性（Kerr + 拉曼）

三阶非线性 $\mathbf{P}_{NL}=\varepsilon_0\chi^{(3)}|\mathbf{E}|^2\mathbf{E}$（瞬时 Kerr）+ 卷积拉曼项，ADE 法处理。光子芯片中典型应用为 SiN 微环的克尔自相位调制、LNOI 的 $\chi^{(2)}$ 二次谐波。

---

## 3. Yee 网格离散化方案

### 3.1 Yee 1966 网格布局

3D Yee 单元中：电场分量 $E_x,E_y,E_z$ 位于棱中点，磁场分量 $H_x,H_y,H_z$ 位于面中心，空间半步错位。该布局使每个旋度运算的中心差分天然落在被求场位置，二阶精度 $O(\Delta h^2)$，且离散 Gauss 定律 $\nabla_h\cdot(\nabla_h\times\cdot)\equiv 0$ 自动满足（避免非物理电荷积累）。Yee 网格是 FDE/FDFD/FDTD/2.5D-FDTD 共同基础（ALGORITHMS.md 附录 C）。

### 3.2 E/H leapfrog 时间推进

时间半步错位，磁场在 $n+1/2$ 时刻更新，电场在 $n+1$ 时刻更新。以 $E_z$（TEz 2D）为例：

$$H_x^{n+1/2}\big|_{i,j+1/2} = D_{a,\mu}\, H_x^{n-1/2}\big|_{i,j+1/2} - D_{b,\mu}\,\frac{E_z^n|_{i,j+1}-E_z^n|_{i,j}}{\Delta y}$$

$$H_y^{n+1/2}\big|_{i+1/2,j} = D_{a,\mu}\, H_y^{n-1/2}\big|_{i+1/2,j} + D_{b,\mu}\,\frac{E_z^n|_{i+1,j}-E_z^n|_{i,j}}{\Delta x}$$

$$E_z^{n+1}\big|_{i,j} = C_{a,\varepsilon}\, E_z^n\big|_{i,j} + C_{b,\varepsilon}\left[\frac{H_y^{n+1/2}|_{i+1/2,j}-H_y^{n+1/2}|_{i-1/2,j}}{\Delta x} - \frac{H_x^{n+1/2}|_{i,j+1/2}-H_x^{n+1/2}|_{i,j-1/2}}{\Delta y}\right]$$

其中 $D_{a,\mu}=\frac{1-\sigma_m\Delta t/(2\mu_0)}{1+\sigma_m\Delta t/(2\mu_0)}$，$D_{b,\mu}=\frac{\Delta t/\mu_0}{1+\sigma_m\Delta t/(2\mu_0)}$，$C_{a,\varepsilon}=\frac{1-\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}{1+\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}$，$C_{b,\varepsilon}=\frac{\Delta t/(\varepsilon_0\varepsilon_r)}{1+\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}$。3D 形式按 6 个分量类似展开。

### 3.3 共形网格亚像素平滑（Yu-Mittra 1/2、Volume-Average）

阶梯近似在介质界面产生 $O(\Delta h)$ 误差。Yu-Mittra 1/2 共形方案：在 Yee 棱上的等效介电常数取界面两侧的体积加权平均，使界面处的等效 $\varepsilon$ 接近真实积分形式，误差降至 $O(\Delta h^2)$。Lumerical Conformal Variant 0/1/2 在介质/金属/PEC 界面分别采用不同共形规则；Tidy3D 默认开启 subpixel averaging。PoLaRIS 将实现 Volume-Average + Yu-Mittra 1/2 两种共形方案。

### 3.4 自动非均匀网格

按"每波长最少 N 个网格"（典型 N=10~20，金属/色散材料处加密至 N=30+）+ 局部 mesh override 框生成非均匀网格，CFL 时间步由最细网格决定。Lumerical `auto nonuniform` mesh accuracy 1-8 对应不同 N；Tidy3D `auto_nonuniform_mesh=True`（arXiv:2506.16665）。

---

## 4. Courant-Friedrichs-Lewy 稳定性条件

显式 leapfrog 格式稳定的必要条件（3D）：

$$\Delta t \le \frac{1}{c\sqrt{\frac{1}{\Delta x^2}+\frac{1}{\Delta y^2}+\frac{1}{\Delta z^2}}}$$

2D 退化为 $\Delta t \le [c\sqrt{1/\Delta x^2+1/\Delta y^2}]^{-1}$，1D 为 $\Delta t\le \Delta x/c$。工程上取 0.95~0.99 倍 CFL 上限以保留稳定裕度。Courant 数 $S=c\Delta t/\Delta h_{\min}$ 反映每步波传播距离与最小网格之比。

**色散误差**：数值相速 $v_p/c \approx 1 - \tfrac{1}{24}(2\pi\Delta h/\lambda)^2 \cdot [\sin^2(\theta/2)] + O(\Delta h# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$ 处理。

### 2.2 色散材料（辅助微分方程 ADE）

Drude-Lorentz 色散介质极化密度 $\mathbf{P}$ 满足二阶 ODE：

$$\frac{\partial^2 \mathbf{P}}{\partial t^2} + \gamma \frac{\partial \mathbf{P}}{\partial t} + \omega_0^2 \mathbf{P} = \varepsilon_0 \omega_p^2 \mathbf{E}$$

其中 $\omega_0$ 为共振频率，$\gamma$ 为阻尼率，$\omega_p$ 为等离子频率。$\mathbf{D}=\varepsilon_0\varepsilon_\infty\mathbf{E}+\mathbf{P}$，代入 Maxwell 旋度方程得 ADE-FDTD 更新格式（Lumerical MCM、Tidy3D PoleResidue 共同方案）。多系数材料 MCM 通过加和多个 Lorentz 极点拟合实测 $n(\omega)$ 数据。

### 2.3 非线性（Kerr + 拉曼）

三阶非线性 $\mathbf{P}_{NL}=\varepsilon_0\chi^{(3)}|\mathbf{E}|^2\mathbf{E}$（瞬时 Kerr）+ 卷积拉曼项，ADE 法处理。光子芯片中典型应用为 SiN 微环的克尔自相位调制、LNOI 的 $\chi^{(2)}$ 二次谐波。

---

## 3. Yee 网格离散化方案

### 3.1 Yee 1966 网格布局

3D Yee 单元中：电场分量 $E_x,E_y,E_z$ 位于棱中点，磁场分量 $H_x,H_y,H_z$ 位于面中心，空间半步错位。该布局使每个旋度运算的中心差分天然落在被求场位置，二阶精度 $O(\Delta h^2)$，且离散 Gauss 定律 $\nabla_h\cdot(\nabla_h\times\cdot)\equiv 0$ 自动满足（避免非物理电荷积累）。Yee 网格是 FDE/FDFD/FDTD/2.5D-FDTD 共同基础（ALGORITHMS.md 附录 C）。

### 3.2 E/H leapfrog 时间推进

时间半步错位，磁场在 $n+1/2$ 时刻更新，电场在 $n+1$ 时刻更新。以 $E_z$（TEz 2D）为例：

$$H_x^{n+1/2}\big|_{i,j+1/2} = D_{a,\mu}\, H_x^{n-1/2}\big|_{i,j+1/2} - D_{b,\mu}\,\frac{E_z^n|_{i,j+1}-E_z^n|_{i,j}}{\Delta y}$$

$$H_y^{n+1/2}\big|_{i+1/2,j} = D_{a,\mu}\, H_y^{n-1/2}\big|_{i+1/2,j} + D_{b,\mu}\,\frac{E_z^n|_{i+1,j}-E_z^n|_{i,j}}{\Delta x}$$

$$E_z^{n+1}\big|_{i,j} = C_{a,\varepsilon}\, E_z^n\big|_{i,j} + C_{b,\varepsilon}\left[\frac{H_y^{n+1/2}|_{i+1/2,j}-H_y^{n+1/2}|_{i-1/2,j}}{\Delta x} - \frac{H_x^{n+1/2}|_{i,j+1/2}-H_x^{n+1/2}|_{i,j-1/2}}{\Delta y}\right]$$

其中 $D_{a,\mu}=\frac{1-\sigma_m\Delta t/(2\mu_0)}{1+\sigma_m\Delta t/(2\mu_0)}$，$D_{b,\mu}=\frac{\Delta t/\mu_0}{1+\sigma_m\Delta t/(2\mu_0)}$，$C_{a,\varepsilon}=\frac{1-\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}{1+\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}$，$C_{b,\varepsilon}=\frac{\Delta t/(\varepsilon_0\varepsilon_r)}{1+\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}$。3D 形式按 6 个分量类似展开。

### 3.3 共形网格亚像素平滑（Yu-Mittra 1/2、Volume-Average）

阶梯近似在介质界面产生 $O(\Delta h)$ 误差。Yu-Mittra 1/2 共形方案：在 Yee 棱上的等效介电常数取界面两侧的体积加权平均，使界面处的等效 $\varepsilon$ 接近真实积分形式，误差降至 $O(\Delta h^2)$。Lumerical Conformal Variant 0/1/2 在介质/金属/PEC 界面分别采用不同共形规则；Tidy3D 默认开启 subpixel averaging。PoLaRIS 将实现 Volume-Average + Yu-Mittra 1/2 两种共形方案。

### 3.4 自动非均匀网格

按"每波长最少 N 个网格"（典型 N=10~20，金属/色散材料处加密至 N=30+）+ 局部 mesh override 框生成非均匀网格，CFL 时间步由最细网格决定。Lumerical `auto nonuniform` mesh accuracy 1-8 对应不同 N；Tidy3D `auto_nonuniform_mesh=True`（arXiv:2506.16665）。

---

## 4. Courant-Friedrichs-Lewy 稳定性条件

显式 leapfrog 格式稳定的必要条件（3D）：

$$\Delta t \le \frac{1}{c\sqrt{\frac{1}{\Delta x^2}+\frac{1}{\Delta y^2}+\frac{1}{\Delta z^2}}}$$

2D 退化为 $\Delta t \le [c\sqrt{1/\Delta x^2+1/\Delta y^2}]^{-1}$，1D 为 $\Delta t\le \Delta x/c$。工程上取 0.95~0.99 倍 CFL 上限以保留稳定裕度。Courant 数 $S=c\Delta t/\Delta h_{\min}$ 反映每步波传播距离与最小网格之比。

**色散误差**：数值相速 $v_p/c \approx 1 - \tfrac{1}{24}(2\pi\Delta h/\lambda)^2 \cdot [\sin^2(\theta/2)] + O(\Delta h^4)$，每波长 ≥20 网格时误差 <0.5%。各向# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$ 处理。

### 2.2 色散材料（辅助微分方程 ADE）

Drude-Lorentz 色散介质极化密度 $\mathbf{P}$ 满足二阶 ODE：

$$\frac{\partial^2 \mathbf{P}}{\partial t^2} + \gamma \frac{\partial \mathbf{P}}{\partial t} + \omega_0^2 \mathbf{P} = \varepsilon_0 \omega_p^2 \mathbf{E}$$

其中 $\omega_0$ 为共振频率，$\gamma$ 为阻尼率，$\omega_p$ 为等离子频率。$\mathbf{D}=\varepsilon_0\varepsilon_\infty\mathbf{E}+\mathbf{P}$，代入 Maxwell 旋度方程得 ADE-FDTD 更新格式（Lumerical MCM、Tidy3D PoleResidue 共同方案）。多系数材料 MCM 通过加和多个 Lorentz 极点拟合实测 $n(\omega)$ 数据。

### 2.3 非线性（Kerr + 拉曼）

三阶非线性 $\mathbf{P}_{NL}=\varepsilon_0\chi^{(3)}|\mathbf{E}|^2\mathbf{E}$（瞬时 Kerr）+ 卷积拉曼项，ADE 法处理。光子芯片中典型应用为 SiN 微环的克尔自相位调制、LNOI 的 $\chi^{(2)}$ 二次谐波。

---

## 3. Yee 网格离散化方案

### 3.1 Yee 1966 网格布局

3D Yee 单元中：电场分量 $E_x,E_y,E_z$ 位于棱中点，磁场分量 $H_x,H_y,H_z$ 位于面中心，空间半步错位。该布局使每个旋度运算的中心差分天然落在被求场位置，二阶精度 $O(\Delta h^2)$，且离散 Gauss 定律 $\nabla_h\cdot(\nabla_h\times\cdot)\equiv 0$ 自动满足（避免非物理电荷积累）。Yee 网格是 FDE/FDFD/FDTD/2.5D-FDTD 共同基础（ALGORITHMS.md 附录 C）。

### 3.2 E/H leapfrog 时间推进

时间半步错位，磁场在 $n+1/2$ 时刻更新，电场在 $n+1$ 时刻更新。以 $E_z$（TEz 2D）为例：

$$H_x^{n+1/2}\big|_{i,j+1/2} = D_{a,\mu}\, H_x^{n-1/2}\big|_{i,j+1/2} - D_{b,\mu}\,\frac{E_z^n|_{i,j+1}-E_z^n|_{i,j}}{\Delta y}$$

$$H_y^{n+1/2}\big|_{i+1/2,j} = D_{a,\mu}\, H_y^{n-1/2}\big|_{i+1/2,j} + D_{b,\mu}\,\frac{E_z^n|_{i+1,j}-E_z^n|_{i,j}}{\Delta x}$$

$$E_z^{n+1}\big|_{i,j} = C_{a,\varepsilon}\, E_z^n\big|_{i,j} + C_{b,\varepsilon}\left[\frac{H_y^{n+1/2}|_{i+1/2,j}-H_y^{n+1/2}|_{i-1/2,j}}{\Delta x} - \frac{H_x^{n+1/2}|_{i,j+1/2}-H_x^{n+1/2}|_{i,j-1/2}}{\Delta y}\right]$$

其中 $D_{a,\mu}=\frac{1-\sigma_m\Delta t/(2\mu_0)}{1+\sigma_m\Delta t/(2\mu_0)}$，$D_{b,\mu}=\frac{\Delta t/\mu_0}{1+\sigma_m\Delta t/(2\mu_0)}$，$C_{a,\varepsilon}=\frac{1-\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}{1+\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}$，$C_{b,\varepsilon}=\frac{\Delta t/(\varepsilon_0\varepsilon_r)}{1+\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}$。3D 形式按 6 个分量类似展开。

### 3.3 共形网格亚像素平滑（Yu-Mittra 1/2、Volume-Average）

阶梯近似在介质界面产生 $O(\Delta h)$ 误差。Yu-Mittra 1/2 共形方案：在 Yee 棱上的等效介电常数取界面两侧的体积加权平均，使界面处的等效 $\varepsilon$ 接近真实积分形式，误差降至 $O(\Delta h^2)$。Lumerical Conformal Variant 0/1/2 在介质/金属/PEC 界面分别采用不同共形规则；Tidy3D 默认开启 subpixel averaging。PoLaRIS 将实现 Volume-Average + Yu-Mittra 1/2 两种共形方案。

### 3.4 自动非均匀网格

按"每波长最少 N 个网格"（典型 N=10~20，金属/色散材料处加密至 N=30+）+ 局部 mesh override 框生成非均匀网格，CFL 时间步由最细网格决定。Lumerical `auto nonuniform` mesh accuracy 1-8 对应不同 N；Tidy3D `auto_nonuniform_mesh=True`（arXiv:2506.16665）。

---

## 4. Courant-Friedrichs-Lewy 稳定性条件

显式 leapfrog 格式稳定的必要条件（3D）：

$$\Delta t \le \frac{1}{c\sqrt{\frac{1}{\Delta x^2}+\frac{1}{\Delta y^2}+\frac{1}{\Delta z^2}}}$$

2D 退化为 $\Delta t \le [c\sqrt{1/\Delta x^2+1/\Delta y^2}]^{-1}$，1D 为 $\Delta t\le \Delta x/c$。工程上取 0.95~0.99 倍 CFL 上限以保留稳定裕度。Courant 数 $S=c\Delta t/\Delta h_{\min}$ 反映每步波传播距离与最小网格之比。

**色散误差**：数值相速 $v_p/c \approx 1 - \tfrac{1}{24}(2\pi\Delta h/\lambda)^2 \cdot [\sin^2(\theta/2)] + O(\Delta h^4)$，每波长 ≥20 网格时误差 <0.5%。各向异性数值色散通过高阶 FDTD（2-4 阶）或共形网格降低。

---

## 5. PML 吸收边界条件（CPML 递归# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$ 处理。

### 2.2 色散材料（辅助微分方程 ADE）

Drude-Lorentz 色散介质极化密度 $\mathbf{P}$ 满足二阶 ODE：

$$\frac{\partial^2 \mathbf{P}}{\partial t^2} + \gamma \frac{\partial \mathbf{P}}{\partial t} + \omega_0^2 \mathbf{P} = \varepsilon_0 \omega_p^2 \mathbf{E}$$

其中 $\omega_0$ 为共振频率，$\gamma$ 为阻尼率，$\omega_p$ 为等离子频率。$\mathbf{D}=\varepsilon_0\varepsilon_\infty\mathbf{E}+\mathbf{P}$，代入 Maxwell 旋度方程得 ADE-FDTD 更新格式（Lumerical MCM、Tidy3D PoleResidue 共同方案）。多系数材料 MCM 通过加和多个 Lorentz 极点拟合实测 $n(\omega)$ 数据。

### 2.3 非线性（Kerr + 拉曼）

三阶非线性 $\mathbf{P}_{NL}=\varepsilon_0\chi^{(3)}|\mathbf{E}|^2\mathbf{E}$（瞬时 Kerr）+ 卷积拉曼项，ADE 法处理。光子芯片中典型应用为 SiN 微环的克尔自相位调制、LNOI 的 $\chi^{(2)}$ 二次谐波。

---

## 3. Yee 网格离散化方案

### 3.1 Yee 1966 网格布局

3D Yee 单元中：电场分量 $E_x,E_y,E_z$ 位于棱中点，磁场分量 $H_x,H_y,H_z$ 位于面中心，空间半步错位。该布局使每个旋度运算的中心差分天然落在被求场位置，二阶精度 $O(\Delta h^2)$，且离散 Gauss 定律 $\nabla_h\cdot(\nabla_h\times\cdot)\equiv 0$ 自动满足（避免非物理电荷积累）。Yee 网格是 FDE/FDFD/FDTD/2.5D-FDTD 共同基础（ALGORITHMS.md 附录 C）。

### 3.2 E/H leapfrog 时间推进

时间半步错位，磁场在 $n+1/2$ 时刻更新，电场在 $n+1$ 时刻更新。以 $E_z$（TEz 2D）为例：

$$H_x^{n+1/2}\big|_{i,j+1/2} = D_{a,\mu}\, H_x^{n-1/2}\big|_{i,j+1/2} - D_{b,\mu}\,\frac{E_z^n|_{i,j+1}-E_z^n|_{i,j}}{\Delta y}$$

$$H_y^{n+1/2}\big|_{i+1/2,j} = D_{a,\mu}\, H_y^{n-1/2}\big|_{i+1/2,j} + D_{b,\mu}\,\frac{E_z^n|_{i+1,j}-E_z^n|_{i,j}}{\Delta x}$$

$$E_z^{n+1}\big|_{i,j} = C_{a,\varepsilon}\, E_z^n\big|_{i,j} + C_{b,\varepsilon}\left[\frac{H_y^{n+1/2}|_{i+1/2,j}-H_y^{n+1/2}|_{i-1/2,j}}{\Delta x} - \frac{H_x^{n+1/2}|_{i,j+1/2}-H_x^{n+1/2}|_{i,j-1/2}}{\Delta y}\right]$$

其中 $D_{a,\mu}=\frac{1-\sigma_m\Delta t/(2\mu_0)}{1+\sigma_m\Delta t/(2\mu_0)}$，$D_{b,\mu}=\frac{\Delta t/\mu_0}{1+\sigma_m\Delta t/(2\mu_0)}$，$C_{a,\varepsilon}=\frac{1-\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}{1+\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}$，$C_{b,\varepsilon}=\frac{\Delta t/(\varepsilon_0\varepsilon_r)}{1+\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}$。3D 形式按 6 个分量类似展开。

### 3.3 共形网格亚像素平滑（Yu-Mittra 1/2、Volume-Average）

阶梯近似在介质界面产生 $O(\Delta h)$ 误差。Yu-Mittra 1/2 共形方案：在 Yee 棱上的等效介电常数取界面两侧的体积加权平均，使界面处的等效 $\varepsilon$ 接近真实积分形式，误差降至 $O(\Delta h^2)$。Lumerical Conformal Variant 0/1/2 在介质/金属/PEC 界面分别采用不同共形规则；Tidy3D 默认开启 subpixel averaging。PoLaRIS 将实现 Volume-Average + Yu-Mittra 1/2 两种共形方案。

### 3.4 自动非均匀网格

按"每波长最少 N 个网格"（典型 N=10~20，金属/色散材料处加密至 N=30+）+ 局部 mesh override 框生成非均匀网格，CFL 时间步由最细网格决定。Lumerical `auto nonuniform` mesh accuracy 1-8 对应不同 N；Tidy3D `auto_nonuniform_mesh=True`（arXiv:2506.16665）。

---

## 4. Courant-Friedrichs-Lewy 稳定性条件

显式 leapfrog 格式稳定的必要条件（3D）：

$$\Delta t \le \frac{1}{c\sqrt{\frac{1}{\Delta x^2}+\frac{1}{\Delta y^2}+\frac{1}{\Delta z^2}}}$$

2D 退化为 $\Delta t \le [c\sqrt{1/\Delta x^2+1/\Delta y^2}]^{-1}$，1D 为 $\Delta t\le \Delta x/c$。工程上取 0.95~0.99 倍 CFL 上限以保留稳定裕度。Courant 数 $S=c\Delta t/\Delta h_{\min}$ 反映每步波传播距离与最小网格之比。

**色散误差**：数值相速 $v_p/c \approx 1 - \tfrac{1}{24}(2\pi\Delta h/\lambda)^2 \cdot [\sin^2(\theta/2)] + O(\Delta h^4)$，每波长 ≥20 网格时误差 <0.5%。各向异性数值色散通过高阶 FDTD（2-4 阶）或共形网格降低。

---

## 5. PML 吸收边界条件（CPML 递归卷积）

### 5.1 Berenger# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$ 处理。

### 2.2 色散材料（辅助微分方程 ADE）

Drude-Lorentz 色散介质极化密度 $\mathbf{P}$ 满足二阶 ODE：

$$\frac{\partial^2 \mathbf{P}}{\partial t^2} + \gamma \frac{\partial \mathbf{P}}{\partial t} + \omega_0^2 \mathbf{P} = \varepsilon_0 \omega_p^2 \mathbf{E}$$

其中 $\omega_0$ 为共振频率，$\gamma$ 为阻尼率，$\omega_p$ 为等离子频率。$\mathbf{D}=\varepsilon_0\varepsilon_\infty\mathbf{E}+\mathbf{P}$，代入 Maxwell 旋度方程得 ADE-FDTD 更新格式（Lumerical MCM、Tidy3D PoleResidue 共同方案）。多系数材料 MCM 通过加和多个 Lorentz 极点拟合实测 $n(\omega)$ 数据。

### 2.3 非线性（Kerr + 拉曼）

三阶非线性 $\mathbf{P}_{NL}=\varepsilon_0\chi^{(3)}|\mathbf{E}|^2\mathbf{E}$（瞬时 Kerr）+ 卷积拉曼项，ADE 法处理。光子芯片中典型应用为 SiN 微环的克尔自相位调制、LNOI 的 $\chi^{(2)}$ 二次谐波。

---

## 3. Yee 网格离散化方案

### 3.1 Yee 1966 网格布局

3D Yee 单元中：电场分量 $E_x,E_y,E_z$ 位于棱中点，磁场分量 $H_x,H_y,H_z$ 位于面中心，空间半步错位。该布局使每个旋度运算的中心差分天然落在被求场位置，二阶精度 $O(\Delta h^2)$，且离散 Gauss 定律 $\nabla_h\cdot(\nabla_h\times\cdot)\equiv 0$ 自动满足（避免非物理电荷积累）。Yee 网格是 FDE/FDFD/FDTD/2.5D-FDTD 共同基础（ALGORITHMS.md 附录 C）。

### 3.2 E/H leapfrog 时间推进

时间半步错位，磁场在 $n+1/2$ 时刻更新，电场在 $n+1$ 时刻更新。以 $E_z$（TEz 2D）为例：

$$H_x^{n+1/2}\big|_{i,j+1/2} = D_{a,\mu}\, H_x^{n-1/2}\big|_{i,j+1/2} - D_{b,\mu}\,\frac{E_z^n|_{i,j+1}-E_z^n|_{i,j}}{\Delta y}$$

$$H_y^{n+1/2}\big|_{i+1/2,j} = D_{a,\mu}\, H_y^{n-1/2}\big|_{i+1/2,j} + D_{b,\mu}\,\frac{E_z^n|_{i+1,j}-E_z^n|_{i,j}}{\Delta x}$$

$$E_z^{n+1}\big|_{i,j} = C_{a,\varepsilon}\, E_z^n\big|_{i,j} + C_{b,\varepsilon}\left[\frac{H_y^{n+1/2}|_{i+1/2,j}-H_y^{n+1/2}|_{i-1/2,j}}{\Delta x} - \frac{H_x^{n+1/2}|_{i,j+1/2}-H_x^{n+1/2}|_{i,j-1/2}}{\Delta y}\right]$$

其中 $D_{a,\mu}=\frac{1-\sigma_m\Delta t/(2\mu_0)}{1+\sigma_m\Delta t/(2\mu_0)}$，$D_{b,\mu}=\frac{\Delta t/\mu_0}{1+\sigma_m\Delta t/(2\mu_0)}$，$C_{a,\varepsilon}=\frac{1-\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}{1+\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}$，$C_{b,\varepsilon}=\frac{\Delta t/(\varepsilon_0\varepsilon_r)}{1+\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}$。3D 形式按 6 个分量类似展开。

### 3.3 共形网格亚像素平滑（Yu-Mittra 1/2、Volume-Average）

阶梯近似在介质界面产生 $O(\Delta h)$ 误差。Yu-Mittra 1/2 共形方案：在 Yee 棱上的等效介电常数取界面两侧的体积加权平均，使界面处的等效 $\varepsilon$ 接近真实积分形式，误差降至 $O(\Delta h^2)$。Lumerical Conformal Variant 0/1/2 在介质/金属/PEC 界面分别采用不同共形规则；Tidy3D 默认开启 subpixel averaging。PoLaRIS 将实现 Volume-Average + Yu-Mittra 1/2 两种共形方案。

### 3.4 自动非均匀网格

按"每波长最少 N 个网格"（典型 N=10~20，金属/色散材料处加密至 N=30+）+ 局部 mesh override 框生成非均匀网格，CFL 时间步由最细网格决定。Lumerical `auto nonuniform` mesh accuracy 1-8 对应不同 N；Tidy3D `auto_nonuniform_mesh=True`（arXiv:2506.16665）。

---

## 4. Courant-Friedrichs-Lewy 稳定性条件

显式 leapfrog 格式稳定的必要条件（3D）：

$$\Delta t \le \frac{1}{c\sqrt{\frac{1}{\Delta x^2}+\frac{1}{\Delta y^2}+\frac{1}{\Delta z^2}}}$$

2D 退化为 $\Delta t \le [c\sqrt{1/\Delta x^2+1/\Delta y^2}]^{-1}$，1D 为 $\Delta t\le \Delta x/c$。工程上取 0.95~0.99 倍 CFL 上限以保留稳定裕度。Courant 数 $S=c\Delta t/\Delta h_{\min}$ 反映每步波传播距离与最小网格之比。

**色散误差**：数值相速 $v_p/c \approx 1 - \tfrac{1}{24}(2\pi\Delta h/\lambda)^2 \cdot [\sin^2(\theta/2)] + O(\Delta h^4)$，每波长 ≥20 网格时误差 <0.5%。各向异性数值色散通过高阶 FDTD（2-4 阶）或共形网格降低。

---

## 5. PML 吸收边界条件（CPML 递归卷积）

### 5.1 Berenger 1994 分裂场 PML（原始# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$ 处理。

### 2.2 色散材料（辅助微分方程 ADE）

Drude-Lorentz 色散介质极化密度 $\mathbf{P}$ 满足二阶 ODE：

$$\frac{\partial^2 \mathbf{P}}{\partial t^2} + \gamma \frac{\partial \mathbf{P}}{\partial t} + \omega_0^2 \mathbf{P} = \varepsilon_0 \omega_p^2 \mathbf{E}$$

其中 $\omega_0$ 为共振频率，$\gamma$ 为阻尼率，$\omega_p$ 为等离子频率。$\mathbf{D}=\varepsilon_0\varepsilon_\infty\mathbf{E}+\mathbf{P}$，代入 Maxwell 旋度方程得 ADE-FDTD 更新格式（Lumerical MCM、Tidy3D PoleResidue 共同方案）。多系数材料 MCM 通过加和多个 Lorentz 极点拟合实测 $n(\omega)$ 数据。

### 2.3 非线性（Kerr + 拉曼）

三阶非线性 $\mathbf{P}_{NL}=\varepsilon_0\chi^{(3)}|\mathbf{E}|^2\mathbf{E}$（瞬时 Kerr）+ 卷积拉曼项，ADE 法处理。光子芯片中典型应用为 SiN 微环的克尔自相位调制、LNOI 的 $\chi^{(2)}$ 二次谐波。

---

## 3. Yee 网格离散化方案

### 3.1 Yee 1966 网格布局

3D Yee 单元中：电场分量 $E_x,E_y,E_z$ 位于棱中点，磁场分量 $H_x,H_y,H_z$ 位于面中心，空间半步错位。该布局使每个旋度运算的中心差分天然落在被求场位置，二阶精度 $O(\Delta h^2)$，且离散 Gauss 定律 $\nabla_h\cdot(\nabla_h\times\cdot)\equiv 0$ 自动满足（避免非物理电荷积累）。Yee 网格是 FDE/FDFD/FDTD/2.5D-FDTD 共同基础（ALGORITHMS.md 附录 C）。

### 3.2 E/H leapfrog 时间推进

时间半步错位，磁场在 $n+1/2$ 时刻更新，电场在 $n+1$ 时刻更新。以 $E_z$（TEz 2D）为例：

$$H_x^{n+1/2}\big|_{i,j+1/2} = D_{a,\mu}\, H_x^{n-1/2}\big|_{i,j+1/2} - D_{b,\mu}\,\frac{E_z^n|_{i,j+1}-E_z^n|_{i,j}}{\Delta y}$$

$$H_y^{n+1/2}\big|_{i+1/2,j} = D_{a,\mu}\, H_y^{n-1/2}\big|_{i+1/2,j} + D_{b,\mu}\,\frac{E_z^n|_{i+1,j}-E_z^n|_{i,j}}{\Delta x}$$

$$E_z^{n+1}\big|_{i,j} = C_{a,\varepsilon}\, E_z^n\big|_{i,j} + C_{b,\varepsilon}\left[\frac{H_y^{n+1/2}|_{i+1/2,j}-H_y^{n+1/2}|_{i-1/2,j}}{\Delta x} - \frac{H_x^{n+1/2}|_{i,j+1/2}-H_x^{n+1/2}|_{i,j-1/2}}{\Delta y}\right]$$

其中 $D_{a,\mu}=\frac{1-\sigma_m\Delta t/(2\mu_0)}{1+\sigma_m\Delta t/(2\mu_0)}$，$D_{b,\mu}=\frac{\Delta t/\mu_0}{1+\sigma_m\Delta t/(2\mu_0)}$，$C_{a,\varepsilon}=\frac{1-\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}{1+\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}$，$C_{b,\varepsilon}=\frac{\Delta t/(\varepsilon_0\varepsilon_r)}{1+\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}$。3D 形式按 6 个分量类似展开。

### 3.3 共形网格亚像素平滑（Yu-Mittra 1/2、Volume-Average）

阶梯近似在介质界面产生 $O(\Delta h)$ 误差。Yu-Mittra 1/2 共形方案：在 Yee 棱上的等效介电常数取界面两侧的体积加权平均，使界面处的等效 $\varepsilon$ 接近真实积分形式，误差降至 $O(\Delta h^2)$。Lumerical Conformal Variant 0/1/2 在介质/金属/PEC 界面分别采用不同共形规则；Tidy3D 默认开启 subpixel averaging。PoLaRIS 将实现 Volume-Average + Yu-Mittra 1/2 两种共形方案。

### 3.4 自动非均匀网格

按"每波长最少 N 个网格"（典型 N=10~20，金属/色散材料处加密至 N=30+）+ 局部 mesh override 框生成非均匀网格，CFL 时间步由最细网格决定。Lumerical `auto nonuniform` mesh accuracy 1-8 对应不同 N；Tidy3D `auto_nonuniform_mesh=True`（arXiv:2506.16665）。

---

## 4. Courant-Friedrichs-Lewy 稳定性条件

显式 leapfrog 格式稳定的必要条件（3D）：

$$\Delta t \le \frac{1}{c\sqrt{\frac{1}{\Delta x^2}+\frac{1}{\Delta y^2}+\frac{1}{\Delta z^2}}}$$

2D 退化为 $\Delta t \le [c\sqrt{1/\Delta x^2+1/\Delta y^2}]^{-1}$，1D 为 $\Delta t\le \Delta x/c$。工程上取 0.95~0.99 倍 CFL 上限以保留稳定裕度。Courant 数 $S=c\Delta t/\Delta h_{\min}$ 反映每步波传播距离与最小网格之比。

**色散误差**：数值相速 $v_p/c \approx 1 - \tfrac{1}{24}(2\pi\Delta h/\lambda)^2 \cdot [\sin^2(\theta/2)] + O(\Delta h^4)$，每波长 ≥20 网格时误差 <0.5%。各向异性数值色散通过高阶 FDTD（2-4 阶）或共形网格降低。

---

## 5. PML 吸收边界条件（CPML 递归卷积）

### 5.1 Berenger 1994 分裂场 PML（原始方案）

将 $\mathbf{E},\# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R39 优先级实现。**当前状态：⚠️ 部分**——`src/polaris/sim/fdtd_simulator.py:279` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$ 处理。

### 2.2 色散材料（辅助微分方程 ADE）

Drude-Lorentz 色散介质极化密度 $\mathbf{P}$ 满足二阶 ODE：

$$\frac{\partial^2 \mathbf{P}}{\partial t^2} + \gamma \frac{\partial \mathbf{P}}{\partial t} + \omega_0^2 \mathbf{P} = \varepsilon_0 \omega_p^2 \mathbf{E}$$

其中 $\omega_0$ 为共振频率，$\gamma$ 为阻尼率，$\omega_p$ 为等离子频率。$\mathbf{D}=\varepsilon_0\varepsilon_\infty\mathbf{E}+\mathbf{P}$，代入 Maxwell 旋度方程得 ADE-FDTD 更新格式（Lumerical MCM、Tidy3D PoleResidue 共同方案）。多系数材料 MCM 通过加和多个 Lorentz 极点拟合实测 $n(\omega)$ 数据。

### 2.3 非线性（Kerr + 拉曼）

三阶非线性 $\mathbf{P}_{NL}=\varepsilon_0\chi^{(3)}|\mathbf{E}|^2\mathbf{E}$（瞬时 Kerr）+ 卷积拉曼项，ADE 法处理。光子芯片中典型应用为 SiN 微环的克尔自相位调制、LNOI 的 $\chi^{(2)}$ 二次谐波。

---

## 3. Yee 网格离散化方案

### 3.1 Yee 1966 网格布局

3D Yee 单元中：电场分量 $E_x,E_y,E_z$ 位于棱中点，磁场分量 $H_x,H_y,H_z$ 位于面中心，空间半步错位。该布局使每个旋度运算的中心差分天然落在被求场位置，二阶精度 $O(\Delta h^2)$，且离散 Gauss 定律 $\nabla_h\cdot(\nabla_h\times\cdot)\equiv 0$ 自动满足（避免非物理电荷积累）。Yee 网格是 FDE/FDFD/FDTD/2.5D-FDTD 共同基础（ALGORITHMS.md 附录 C）。

### 3.2 E/H leapfrog 时间推进

时间半步错位，磁场在 $n+1/2$ 时刻更新，电场在 $n+1$ 时刻更新。以 $E_z$（TEz 2D）为例：

$$H_x^{n+1/2}\big|_{i,j+1/2} = D_{a,\mu}\, H_x^{n-1/2}\big|_{i,j+1/2} - D_{b,\mu}\,\frac{E_z^n|_{i,j+1}-E_z^n|_{i,j}}{\Delta y}$$

$$H_y^{n+1/2}\big|_{i+1/2,j} = D_{a,\mu}\, H_y^{n-1/2}\big|_{i+1/2,j} + D_{b,\mu}\,\frac{E_z^n|_{i+1,j}-E_z^n|_{i,j}}{\Delta x}$$

$$E_z^{n+1}\big|_{i,j} = C_{a,\varepsilon}\, E_z^n\big|_{i,j} + C_{b,\varepsilon}\left[\frac{H_y^{n+1/2}|_{i+1/2,j}-H_y^{n+1/2}|_{i-1/2,j}}{\Delta x} - \frac{H_x^{n+1/2}|_{i,j+1/2}-H_x^{n+1/2}|_{i,j-1/2}}{\Delta y}\right]$$

其中 $D_{a,\mu}=\frac{1-\sigma_m\Delta t/(2\mu_0)}{1+\sigma_m\Delta t/(2\mu_0)}$，$D_{b,\mu}=\frac{\Delta t/\mu_0}{1+\sigma_m\Delta t/(2\mu_0)}$，$C_{a,\varepsilon}=\frac{1-\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}{1+\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}$，$C_{b,\varepsilon}=\frac{\Delta t/(\varepsilon_0\varepsilon_r)}{1+\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}$。3D 形式按 6 个分量类似展开。

### 3.3 共形网格亚像素平滑（Yu-Mittra 1/2、Volume-Average）

阶梯近似在介质界面产生 $O(\Delta h)$ 误差。Yu-Mittra 1/2 共形方案：在 Yee 棱上的等效介电常数取界面两侧的体积加权平均，使界面处的等效 $\varepsilon$ 接近真实积分形式，误差降至 $O(\Delta h^2)$。Lumerical Conformal Variant 0/1/2 在介质/金属/PEC 界面分别采用不同共形规则；Tidy3D 默认开启 subpixel averaging。PoLaRIS 将实现 Volume-Average + Yu-Mittra 1/2 两种共形方案。

### 3.4 自动非均匀网格

按"每波长最少 N 个网格"（典型 N=10~20，金属/色散材料处加密至 N=30+）+ 局部 mesh override 框生成非均匀网格，CFL 时间步由最细网格决定。Lumerical `auto nonuniform` mesh accuracy 1-8 对应不同 N；Tidy3D `auto_nonuniform_mesh=True`（arXiv:2506.16665）。

---

## 4. Courant-Friedrichs-Lewy 稳定性条件

显式 leapfrog 格式稳定的必要条件（3D）：

$$\Delta t \le \frac{1}{c\sqrt{\frac{1}{\Delta x^2}+\frac{1}{\Delta y^2}+\frac{1}{\Delta z^2}}}$$

2D 退化为 $\Delta t \le [c\sqrt{1/\Delta x^2+1/\Delta y^2}]^{-1}$，1D 为 $\Delta t\le \Delta x/c$。工程上取 0.95~0.99 倍 CFL 上限以保留稳定裕度。Courant 数 $S=c\Delta t/\Delta h_{\min}$ 反映每步波传播距离与最小网格之比。

**色散误差**：数值相速 $v_p/c \approx 1 - \tfrac{1}{24}(2\pi\Delta h/\lambda)^2 \cdot [\sin^2(\theta/2)] + O(\Delta h^4)$，每波长 ≥20 网格时误差 <0.5%。各向异性数值色散通过高阶 FDTD（2-4 阶）或共形网格降低。

---

## 5. PML 吸收边界条件（CPML 递归卷积）

### 5.1 Berenger 1994 分裂场 PML（原始方案）

将 $\mathbf{E},\mathbf{H}$ 分裂为两个分量