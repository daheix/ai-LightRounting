# T06 Siemens L-Edit Photonics 商业光子 EDA 工具功能点清单

| 项目 | 内容 |
|------|------|
| 工具名 | L-Edit Photonics（Tanner 系列） |
| 厂商 | Siemens Digital Industries Software（西门子数字化工业软件） |
| 官网 URL | https://eda.sw.siemens.com/en-US/ic/l-edit-photonics/ |
| 调研日期 | 2026-06-25 |
| 版本 | v1.0 |

> 学术诚信声明：本文档所有功能点均来源于 Siemens 官网公开页面及官方 Fact Sheet，每个功能点均标注来源 URL。若官网未明确说明的内容，标注"未公开"。

---

## 1. 版图编辑（Layout Editing）

| 序号 | 功能点 | 来源 URL |
|------|--------|----------|
| 1.1 | 完整层次化物理版图编辑器，支持产品级光芯片设计 | https://www.eda-solutions.com/app/uploads/2021/10/Siemens-SW-Tanner-L-Edit-IC-Photonics-FS-81552-C1.pdf |
| 1.2 | 支持曲线多边形（curved polygons）与任意角度图形（all-angle geometries） | https://www.eda-solutions.com/app/uploads/2021/10/Siemens-SW-Tanner-L-Edit-IC-Photonics-FS-81552-C1.pdf |
| 1.3 | 快速渲染（fast rendering） | https://www.eda-solutions.com/app/uploads/2021/10/Siemens-SW-Tanner-L-Edit-IC-Photonics-FS-81552-C1.pdf |
| 1.4 | 对象抓取（object snapping / gravity）用于快速、准确的版图 | https://www.eda-solutions.com/app/uploads/2021/10/Siemens-SW-Tanner-L-Edit-IC-Photonics-FS-81552-C1.pdf |
| 1.5 | 基于 OpenAccess 构建，设计数据可与任何支持 OpenAccess 的版图工具互换 | https://www.eda-solutions.com/app/uploads/2021/10/Siemens-SW-Tanner-L-Edit-IC-Photonics-FS-81552-C1.pdf |
| 1.6 | 支持 FinFET、平面及所有其他晶体管技术 | https://www.siemens.com/en-us/products/ic/ic-custom/ams/l-edit-ic/ |
| 1.7 | 内置全角度与曲线支持，用于功率晶体管、MEMS 与光子学 | https://www.siemens.com/en-us/products/ic/ic-custom/ams/l-edit-ic/ |
| 1.8 | 原生 OpenAccess 多用户支持 | https://www.siemens.com/en-us/products/ic/ic-custom/ams/l-edit-ic/ |

---

## 2. GPIC PDK 与多 Foundry 支持（GPIC PDK & Multi-Foundry）

| 序号 | 功能点 | 来源 URL |
|------|--------|----------|
| 2.1 | 支持 Siemens 格式 PDK 与可互操作的行业标准 iPDK | https://www.eda-solutions.com/app/uploads/2021/10/Siemens-SW-Tanner-L-Edit-IC-Photonics-FS-81552-C1.pdf |
| 2.2 | PDK 可从多家光子晶圆代工厂获得 | https://www.eda-solutions.com/app/uploads/2021/10/Siemens-SW-Tanner-L-Edit-IC-Photonics-FS-81552-C1.pdf |
| 2.3 | 设计人员可创建自己的元器件或创建自己的 PDK | https://www.eda-solutions.com/app/uploads/2021/10/Siemens-SW-Tanner-L-Edit-IC-Photonics-FS-81552-C1.pdf |
| 2.4 | 支持 30+ 代工厂、200+ PDK（L-Edit IC 整体能力） | https://www.siemens.com/en-us/products/ic/ic-custom/ams/l-edit-ic/ |
| 2.5 | General Photonic Integrated Circuit (GPIC) PDK，由 Siemens EDA 团队开发，作为开发任意 foundry 自定义 Python 组件的起点 | https://www.vpiphotonics.com/Tools/PDK/PDK_GPIC/ |
| 2.6 | GPIC PDK 提供构建模块（BBs）库与真实仿真模型，支持 ASPIC 原型设计 | https://www.vpiphotonics.com/Tools/PDK/PDK_GPIC/ |

---

## 3. SDL 原理图驱动版图（Schematic-Driven Layout）

| 序号 | 功能点 | 来源 URL |
|------|--------|----------|
| 3.1 | 原理图驱动版图流程，允许首次即创建与原理图匹配的版图 | https://www.siemens.com/en-us/products/ic/ic-custom/ams/l-edit-ic/ |
| 3.2 | 自动生成参数化单元（PCell）并实例化到设计中 | https://www.siemens.com/en-us/products/ic/ic-custom/ams/l-edit-ic/ |
| 3.3 | 显示飞线（flylines）以放置模块、最小化布线拥塞 | https://www.siemens.com/en-us/products/ic/ic-custom/ams/l-edit-ic/ |
| 3.4 | SDL short 与 open Connectivity Checker 检查连接性问题 | https://www.siemens.com/en-us/products/ic/ic-custom/ams/l-edit-ic/ |
| 3.5 | 对象抓取（gravity）用于快速、准确版图 | https://www.siemens.com/en-us/products/ic/ic-custom/ams/l-edit-ic/ |
| 3.6 | 对于传统定制 IC 设计流程，S-Edit 可用于创建原理图；大型设计可在 L-Edit IC 中使用 SDL 流程（含 L-Edit Photonics 全部光子版图能力） | https://www.eda-solutions.com/app/uploads/2021/10/Siemens-SW-Tanner-L-Edit-IC-Photonics-FS-81552-C1.pdf |

---

## 4. Calibre 集成（Calibre Integration）

| 序号 | 功能点 | 来源 URL |
|------|--------|----------|
| 4.1 | L-Edit Photonics 启动 Calibre Interactive™ 推动物理验证 | https://www.eda-solutions.com/app/uploads/2021/10/Siemens-SW-Tanner-L-Edit-IC-Photonics-FS-81552-C1.pdf |
| 4.2 | Calibre nmDRC™ 用于设计规则检查（DRC） | https://www.eda-solutions.com/app/uploads/2021/10/Siemens-SW-Tanner-L-Edit-IC-Photonics-FS-81552-C1.pdf |
| 4.3 | Calibre nmLVS™ 用于版图与原理图检查（LVS） | https://www.eda-solutions.com/app/uploads/2021/10/Siemens-SW-Tanner-L-Edit-IC-Photonics-FS-81552-C1.pdf |
| 4.4 | Calibre xACT™ 用于寄生效应提取（parasitic extraction） | https://www.eda-solutions.com/app/uploads/2021/10/Siemens-SW-Tanner-L-Edit-IC-Photonics-FS-81552-C1.pdf |
| 4.5 | Calibre LFD（Litho-Friendly Design）用于光刻友好设计，找出光刻热点 | https://www.eda-solutions.com/app/uploads/2021/10/Siemens-SW-Tanner-L-Edit-IC-Photonics-FS-81552-C1.pdf |
| 4.6 | Calibre RVE™ 查看结果并高亮网络与器件，支持与 L-Edit Photonics 交叉探测（cross probing） | https://www.eda-solutions.com/app/uploads/2021/10/Siemens-SW-Tanner-L-Edit-IC-Photonics-FS-81552-C1.pdf |
| 4.7 | 与 Calibre 和 Calibre RealTime 集成 | https://www.siemens.com/en-us/products/ic/ic-custom/ams/l-edit-ic/ |
| 4.8 | 光子版图验证使用 Calibre 基于方程的设计规则（equation based design rules） | https://www.siemens.com/en-us/products/ic/ic-custom/photonic/l-edit-photonics/ |

---

## 5. GDSII/OASIS 导出与互操作（GDSII/OASIS Export & Interoperability）

| 序号 | 功能点 | 来源 URL |
|------|--------|----------|
| 5.1 | 导入与导出 ODB++ | https://www.siemens.com/en-us/products/ic/ic-custom/ams/l-edit-ic/ |
| 5.2 | 与第三方 IP 互操作支持 | https://www.eda-solutions.com/app/uploads/2021/10/Siemens-SW-Tanner-L-Edit-IC-Photonics-FS-81552-C1.pdf |
| 5.3 | 与第三方版本控制工具集成 | https://www.siemens.com/en-us/products/ic/ic-custom/ams/l-edit-ic/ |
| 5.4 | 基于 OpenAccess，设计数据可与任何支持 OpenAccess 的版图工具互换 | https://www.eda-solutions.com/app/uploads/2021/10/Siemens-SW-Tanner-L-Edit-IC-Photonics-FS-81552-C1.pdf |
| 5.5 | OASIS 导出支持 — 未公开（官方 Fact Sheet 未明确列出 OASIS，主要强调 OpenAccess/ODB++；GDSII 作为 IC 版图标准格式默认支持，但光子专用页未显式声明） | https://www.siemens.com/en-us/products/ic/ic-custom/photonic/l-edit-photonics/ |

---

## 6. 曲线多边形与波导（Curved Polygons & Waveguides）

| 序号 | 功能点 | 来源 URL |
|------|--------|----------|
| 6.1 | 支持曲线多边形与任意角度图形 | https://www.eda-solutions.com/app/uploads/2021/10/Siemens-SW-Tanner-L-Edit-IC-Photonics-FS-81552-C1.pdf |
| 6.2 | 简单波导创建与编辑 | https://www.siemens.com/en-us/products/ic/ic-custom/photonic/l-edit-photonics/ |
| 6.3 | 自动交叉插入（automated crossing insertion） | https://www.siemens.com/en-us/products/ic/ic-custom/photonic/l-edit-photonics/ |
| 6.4 | 精确抓取至光学引脚（precision snapping to optical pins） | https://www.siemens.com/en-us/products/ic/ic-custom/photonic/l-edit-photonics/ |
| 6.5 | 波导到引脚检查（waveguide to pin checking） | https://www.siemens.com/en-us/products/ic/ic-custom/photonic/l-edit-photonics/ |
| 6.6 | 多种波导类型：带状（striped）、脊型（ribbed）、分段组合（multi-segmented） | https://www.eda-solutions.com/app/uploads/2021/10/Siemens-SW-Tanner-L-Edit-IC-Photonics-FS-81552-C1.pdf |
| 6.7 | 波导长度编辑，可定义精确有效长度 | https://www.eda-solutions.com/app/uploads/2021/10/Siemens-SW-Tanner-L-Edit-IC-Photonics-FS-81552-C1.pdf |
| 6.8 | 两步波导创建：先创建正交布线，再按热键根据工艺转换为适当曲率波导 | https://m.elecfans.com/article/7383488.html |

---

## 7. S-Edit 电路图（S-Edit Schematic Capture）

| 序号 | 功能点 | 来源 URL |
|------|--------|----------|
| 7.1 | S-Edit 提供强大的 IC 与 PIC 原理图捕获环境 | https://www.vpiphotonics.com/Tools/PDK/PDK_GPIC/ |
| 7.2 | 原理图流程可选（optional with S-Edit），支持传统定制 IC 设计流程 | https://www.siemens.com/en-us/products/ic/ic-custom/photonic/l-edit-photonics/ |
| 7.3 | S-Edit 与 L-Edit 工具均可提取描述电路元件与连接的网表（netlist） | https://optics.ansys.com/hc/en-us/articles/360042662454 |
| 7.4 | 网表导入 INTERCONNECT 等 CML 仿真器，生成基于紧凑模型库的电路 | https://optics.ansys.com/hc/en-us/articles/360042662454 |
| 7.5 | S-Edit 与 VPI Design Suite 联合提供电子/光子设计自动化（EPDA）环境，仿真含电气与光子子电路的集成电路 | https://www.vpiphotonics.com/Tools/PDK/PDK_GPIC/ |

---

## 8. 网表生成与仿真伙伴集成（Netlisting & Simulation Partners）

| 序号 | 功能点 | 来源 URL |
|------|--------|----------|
| 8.1 | 以版图为中心的设计流程，内置网表生成（built-in netlisting） | https://www.eda-solutions.com/app/uploads/2021/10/Siemens-SW-Tanner-L-Edit-IC-Photonics-FS-81552-C1.pdf |
| 8.2 | 网表支持西门子所有光仿真软件合作伙伴 | https://m.elecfans.com/article/7383488.html |
| 8.3 | 仿真合作伙伴：Ansys、Luceda、Optiwave、VPIphotonics | https://www.siemens.com/en-us/products/ic/ic-custom/photonic/l-edit-photonics/ |
| 8.4 | 若设计含电气与光学元器件，网表还支持西门子晶体管级与混合模式仿真器 | https://m.elecfans.com/article/7383488.html |
| 8.5 | 网表格式：`InstanceName Nets ModelName Parameters=values`；支持子电路 `.subckt`/`.ends` 层次化定义 | https://optics.ansys.com/hc/en-us/articles/360042662454 |
| 8.6 | 网表参数包含 library、lay_x..lay_f（版图几何）、sch_x..sch_f（原理图几何）及其他元件参数 | https://optics.ansys.com/hc/en-us/articles/360042662454 |

---

## 9. 热光协同（Thermo-Optical Co-Simulation）

| 序号 | 功能点 | 来源 URL |
|------|--------|----------|
| 9.1 | 电元器件可手动布局并互连，连接至光子 PCell 中的加热器与外部电气组件 | https://www.eda-solutions.com/app/uploads/2021/10/Siemens-SW-Tanner-L-Edit-IC-Photonics-FS-81552-C1.pdf |
| 9.2 | Calibre xACT 寄生效应提取支持热相关电气寄生分析 | https://www.eda-solutions.com/app/uploads/2021/10/Siemens-SW-Tanner-L-Edit-IC-Photonics-FS-81552-C1.pdf |
| 9.3 | 与 VPIphotonics Design Suite 联合提供 EPDA 环境，支持电-光-热协同仿真（通过 VPI 侧 TLLM 模型） | https://www.vpiphotonics.com/Tools/PDK/PDK_GPIC/ |
| 9.4 | 专用热-光协同仿真模块 — 未公开（L-Edit Photonics 官方页面未明确列出独立热光协同模块，热效应主要通过外部仿真器与 PDK 模型处理） | https://www.siemens.com/en-us/products/ic/ic-custom/photonic/l-edit-photonics/ |

---

## 10. 脚本与可扩展性（Scripting & Extensibility）

| 序号 | 功能点 | 来源 URL |
|------|--------|----------|
| 10.1 | 可使用 Python 脚本化 | https://www.siemens.com/en-us/products/ic/ic-custom/photonic/l-edit-photonics/ |
| 10.2 | 完全可脚本化与可扩展，使用 Python、TCL/Tk 或 C++ | https://www.siemens.com/en-us/products/ic/ic-custom/ams/l-edit-ic/ |
| 10.3 | 支持拖放（drag and drop）方法论，无需编写代码即可创建设计 | https://www.siemens.com/en-us/products/ic/ic-custom/photonic/l-edit-photonics/ |
| 10.4 | 支持脚本驱动方法论（script-driven methodology） | https://www.siemens.com/en-us/products/ic/ic-custom/photonic/l-edit-photonics/ |

---

## 11. 平台与设计流程（Platform & Design Flow）

| 序号 | 功能点 | 来源 URL |
|------|--------|----------|
| 11.1 | 支持 Windows® 与 Linux® 双平台 | https://www.siemens.com/en-us/products/ic/ic-custom/photonic/l-edit-photonics/ |
| 11.2 | 以版图为中心的设计流程（layout-centric flow），无需创建原理图，节省设计时间 | https://www.eda-solutions.com/app/uploads/2021/10/Siemens-SW-Tanner-L-Edit-IC-Photonics-FS-81552-C1.pdf |
| 11.3 | 版图作为最重要的设计数据库（golden design database） | https://m.elecfans.com/article/7383488.html |
| 11.4 | 完整 PIC 设计流程：版图创建 → 网表提取 → 仿真 → Calibre 物理验证 → tape-out | https://www.siemens.com/en-us/products/ic/ic-custom/photonic/l-edit-photonics/ |
| 11.5 | 直观且易于上手的学习曲线 | https://www.eda-solutions.com/app/uploads/2021/10/Siemens-SW-Tanner-L-Edit-IC-Photonics-FS-81552-C1.pdf |

---

## 12. Luceda IPKISS 集成（Luceda IPKISS Integration）

| 序号 | 功能点 | 来源 URL |
|------|--------|----------|
| 12.1 | IPKISS.eda 设计框架基于 Tanner L-Edit 版图编辑器构建，无缝接口 Tanner Calibre® One 物理验证套件 | https://www.eda-solutions.com/resources/1520/ |
| 12.2 | L-Edit 结合 IPKISS 参数化光子元件库与 PDK，支持拖放光子元件到版图 | https://www.eda-solutions.com/resources/1520/ |
| 12.3 | 通过波导连接元件，完全控制截面形状、弯曲与轨迹 | https://www.eda-solutions.com/resources/1520/ |
| 12.4 | 后版图效应（如波导交叉引起的反射与衰减）通过 IPKISS.eda 紧凑模型仿真器处理 | https://www.eda-solutions.com/resources/1520/ |

---

## 功能点总数统计

| 类别 | 功能点数 |
|------|----------|
| 1. 版图编辑 | 8 |
| 2. GPIC PDK 与多 Foundry 支持 | 6 |
| 3. SDL 原理图驱动版图 | 6 |
| 4. Calibre 集成 | 8 |
| 5. GDSII/OASIS 导出与互操作 | 5 |
| 6. 曲线多边形与波导 | 8 |
| 7. S-Edit 电路图 | 5 |
| 8. 网表生成与仿真伙伴集成 | 6 |
| 9. 热光协同 | 4 |
| 10. 脚本与可扩展性 | 4 |
| 11. 平台与设计流程 | 5 |
| 12. Luceda IPKISS 集成 | 4 |
| **总计** | **69** |

---

## 参考来源汇总

1. Siemens L-Edit Photonics 官方产品页 — https://www.siemens.com/en-us/products/ic/ic-custom/photonic/l-edit-photonics/
2. Siemens L-Edit IC 官方产品页 — https://www.siemens.com/en-us/products/ic/ic-custom/ams/l-edit-ic/
3. Tanner L-Edit Photonics Fact Sheet (PDF) — https://www.eda-solutions.com/app/uploads/2021/10/Siemens-SW-Tanner-L-Edit-IC-Photonics-FS-81552-C1.pdf
4. VPItoolkit PDK GPIC — https://www.vpiphotonics.com/Tools/PDK/PDK_GPIC/
5. Lumerical INTERCONNECT 与 Tanner L-Edit & S-Edit 流程用户指南 — https://optics.ansys.com/hc/en-us/articles/360042662454
6. Luceda Photonics L-Edit Photonics 白皮书 — https://www.eda-solutions.com/resources/1520/
7. L-Edit Photonics 中文产品介绍 — https://m.elecfans.com/article/7383488.html
