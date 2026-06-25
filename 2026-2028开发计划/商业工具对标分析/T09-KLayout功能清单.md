# T09 KLayout 功能点清单

## 文档信息

| 项目 | 内容 |
|---|---|
| 工具名 | KLayout |
| 维护方 | Matthias Köfferlein (klayoutmatthias) 及社区 |
| GitHub URL | https://github.com/KLayout/klayout |
| 官方网站 | https://www.klayout.de/ |
| 调研日期 | 2026-06-25 |
| 版本 | v1.0 |
| 开源协议 | GPLv2 |
| 当前版本 | 0.30.9 (2026-05-29 发布) |

> **学术诚信声明**：本文档所有功能点均来源于 KLayout 官网、GitHub 仓库及官方文档。未在公开文档中明确说明的功能标注为"未公开"。

---

## 1. 工具概述

KLayout 是一款开源的掩膜版图（mask layout）查看和编辑工具，广泛应用于半导体集成电路（IC）和光子掩膜设计。它以速度、准确性和对大版图文件的支持著称，适用于研究和专业芯片设计工作流。

- **来源**: https://www.klayout.de/
- **GitHub**: https://github.com/KLayout/klayout

---

## 2. 功能点清单

### 2.1 版图查看（View）

| 编号 | 功能点 | 描述 | 来源 URL |
|---|---|---|---|
| 1.1 | 查看器模式 | 以查看器模式启动 KLayout，提供准确快速的大掩膜版图文件查看器 | https://www.klayout.de/ |
| 1.2 | 大文件支持 | 能够处理多 GB 规模的大文件，包含数十亿多边形 | https://www.klayout.org/klayout-pypi/ |
| 1.3 | 多层叠加 | 支持多层叠加能力（overlay capability for multiple layers） | https://www.klayout.de/ |
| 1.4 | 标尺工具 | 提供标尺（rulers）工具 | https://www.klayout.de/ |
| 1.5 | 图像叠加 | 支持图像叠加（image overlays） | https://www.klayout.de/ |
| 1.6 | 样式选项 | 提供多种样式选项（many style options） | https://www.klayout.de/ |
| 1.7 | 可切换层视图 | 支持可切换层视图（switchable layer views） | https://www.klayout.de/ |
| 1.8 | 书签 | 支持书签（bookmarks）功能 | https://www.klayout.de/ |
| 1.9 | 层次化上下文视图 | 提供层次化上下文视图（hierarchical context views） | https://www.klayout.de/ |
| 1.10 | 搜索功能 | 提供搜索功能（search function） | https://www.klayout.de/ |
| 1.11 | 按实例/形状浏览 | 支持按实例或形状浏览（browsing by instances or shapes） | https://www.klayout.de/ |
| 1.12 | 选择性单元屏蔽 | 支持选择性单元屏蔽（selective cell blankout） | https://www.klayout.de/ |
| 1.13 | 2.5D 视图 | 支持 2.5D 视图模式，直观展示多层金属堆叠结构 | https://blog.csdn.net/gitblog_00207/article/details/157406033 |

### 2.2 版图编辑（Edit）

| 编号 | 功能点 | 描述 | 来源 URL |
|---|---|---|---|
| 2.1 | 编辑器模式 | 以编辑器模式启动 KLayout，访问丰富的编辑功能 | https://www.klayout.de/ |
| 2.2 | 创建层和单元 | 创建新层和单元，在其他单元中实例化 | https://www.klayout.de/ |
| 2.3 | 几何图形绘制 | 绘制多边形、矩形、路径和标签（polygons, boxes, wires, labels） | https://www.klayout.de/ |
| 2.4 | 变换操作 | 移动、旋转、缩放、镜像选中对象 | https://www.klayout.de/ |
| 2.5 | 布尔运算 | 使用布尔运算操作多边形和层 | https://www.klayout.de/ |
| 2.6 | 搜索替换 | 搜索和替换形状和实例 | https://www.klayout.de/ |
| 2.7 | 参数化单元 | 使用参数化单元（PCells）通过几次点击创建复杂几何 | https://www.klayout.de/ |
| 2.8 | 复制/粘贴 | 支持复制/粘贴选中对象 | https://www.klayout.de/ |
| 2.9 | 无限撤销/重做 | 所有功能支持完整且无限的撤销/重做 | https://www.klayout.de/ |

### 2.3 DRC（设计规则检查）

| 编号 | 功能点 | 描述 | 来源 URL |
|---|---|---|---|
| 3.1 | DRC 引擎 | 集成 DRC 引擎，DRCEngine 类协调设计规则检查执行 | https://deepwiki.com/KLayout/klayout/4.1-design-rule-checking-(drc) |
| 3.2 | DRCLayer 类 | DRCLayer 类是几何处理的主要数据对象，表示多边形、边或边对集合 | https://deepwiki.com/KLayout/klayout/4.1-design-rule-checking-(drc) |
| 3.3 | 通用 DRC 函数 | `drc()` 方法提供通用接口，使用 DRC 表达式表达复杂设计规则 | https://deepwiki.com/KLayout/klayout/4.1-design-rule-checking-(drc) |
| 3.4 | DRC 表达式 | DRC 表达式是可组合对象（DRCOpNode），表示几何操作的抽象配方 | https://deepwiki.com/KLayout/klayout/4.1-design-rule-checking-(drc) |
| 3.5 | 天线检查 | `antenna_check` 执行连接网络的天线比率验证 | https://www.klayout.org/downloads/master/doc-qt5/about/drc_ref_global.html |
| 3.6 | 设备提取 | `extract_devices` 从版图识别和参数化设备 | https://www.klayout.org/downloads/master/doc-qt5/about/drc_ref_global.html |
| 3.7 | 宽度检查 | `width` 执行宽度检查 | https://www.klayout.org/downloads/master/doc-qt5/about/drc_ref_global.html |
| 3.8 | 间距检查 | `space` 执行间距检查 | https://www.klayout.org/downloads/master/doc-qt5/about/drc_ref_global.html |
| 3.9 | 包围检查 | `enclosing` 执行包围检查 | https://blog.csdn.net/gitblog_00207/article/details/157406033 |
| 3.10 | 面积检查 | `area` 计算总面积或根据面积条件选择主形状 | https://www.klayout.org/downloads/master/doc-qt5/about/drc_ref_global.html |
| 3.11 | 角点选择 | `corners` 选择多边形角点 | https://www.klayout.org/downloads/master/doc-qt5/about/drc_ref_global.html |
| 3.12 | 覆盖检查 | `covering` 选择完全覆盖其他形状的形状 | https://www.klayout.org/downloads/master/doc-qt5/about/drc_ref_global.html |

### 2.4 LVS（版图与原理图一致性验证）

| 编号 | 功能点 | 描述 | 来源 URL |
|---|---|---|---|
| 4.1 | LVS 比较 | `compare` 方法提取网表并与原理图比较，成功返回 true | https://www.klayout.org/downloads/master/doc-qt5/manual/lvs_compare.html |
| 4.2 | 网表等价提示 | `same_nets` 声明两个网络相同用于调试 | https://www.klayout.org/downloads/master/doc-qt5/manual/lvs_compare.html |
| 4.3 | 电路等价提示 | `same_circuit` 建立电路等价关系 | https://www.klayout.org/downloads/master/doc-qt5/manual/lvs_compare.html |
| 4.4 | 容差设置 | 支持设置容差（Tolerances） | https://www.klayout.org/downloads/master/doc-qt5/manual/lvs_compare.html |
| 4.5 | 引脚交换 | 支持引脚交换（Pin swapping） | https://www.klayout.org/downloads/master/doc-qt5/manual/lvs_compare.html |
| 4.6 | 电容/电阻消除 | 支持电容和电阻消除（Capacitor and resistor elimination） | https://www.klayout.org/downloads/master/doc-qt5/manual/lvs_compare.html |
| 4.7 | 引脚标签检查 | 支持检查引脚标签（Checking pin labels） | https://www.klayout.org/downloads/master/doc-qt5/manual/lvs_compare.html |
| 4.8 | 网表层次结构 | 支持比较和网表层次结构（Compare and netlist hierarchy） | https://www.klayout.org/downloads/master/doc-qt5/manual/lvs_compare.html |
| 4.9 | 连接定义 | `connect` 指定两层之间的连接 | https://www.klayout.org/downloads/master/doc-qt5/about/drc_ref_global.html |
| 4.10 | 全局连接 | `connect_global` 指定到全局网络的连接 | https://www.klayout.org/downloads/master/doc-qt5/about/drc_ref_global.html |
| 4.11 | 隐式连接 | `connect_implicit` 指定隐式网络连接的标签模式 | https://www.klayout.org/downloads/master/doc-qt5/about/drc_ref_global.html |
| 4.12 | 显式连接 | `connect_explicit` 指定显式网络连接 | https://www.klayout.org/downloads/master/doc-qt5/about/drc_ref_global.html |
| 4.13 | 设备提取器 | 提供多种设备提取器类（bjt3、bjt4、capacitor、diode、dmos3、mos3、mos4、resistor 等） | https://www.klayout.org/downloads/master/doc-qt5/about/drc_ref_global.html |

### 2.5 处理模式

| 编号 | 功能点 | 描述 | 来源 URL |
|---|---|---|---|
| 5.1 | flat mode（扁平模式） | 扁平化版图层次后处理，适用于小/简单设计，简单可预测单 CPU | https://wiki.f-si.org/images/1/19/FSiC2023_KLayout_DRCLVS_best_practices.pdf |
| 5.2 | tiled mode（分块模式） | `tiles()` 将版图分块处理，减少内存使用并支持并行处理 | https://www.klayout.org/downloads/master/doc-qt5/about/drc_ref_global.html |
| 5.3 | hierarchical mode（层次模式） | 层次化处理，尽可能保留层次（每个单元本地计算一次） | https://wiki.f-si.org/images/1/19/FSiC2023_KLayout_DRCLVS_best_practices.pdf |
| 5.4 | deep mode（深度模式） | `deep()` 进入深度（层次）模式，使用 db::DeepShapeStore 进行层次处理 | https://www.klayout.org/downloads/master/doc-qt5/about/drc_ref_global.html |
| 5.5 | deep_reject_odd_polygons | `deep_reject_odd_polygons` 获取或设置是否在深度模式下拒绝奇多边形 | https://www.klayout.org/downloads/master/doc-qt5/about/drc_ref_global.html |
| 5.6 | 线程并行 | `threads(count)` 设置并行处理的线程数 | https://deepwiki.com/KLayout/klayout/4.1-design-rule-checking-(drc) |
| 5.7 | 分块边界 | 分块可通过指定分块边界（tile border）使分块重叠 | https://www.klayout.org/downloads/master/doc-qt5/about/drc_ref_global.html |

### 2.6 文件格式支持

| 编号 | 功能点 | 描述 | 来源 URL |
|---|---|---|---|
| 6.1 | GDSII 读写 | 支持 GDS2（GDSII）格式读写 | https://www.klayout.de/ |
| 6.2 | OASIS 读写 | 支持 OASIS 格式读写 | https://www.klayout.de/ |
| 6.3 | DXF 导入 | 支持 DXF 格式导入 | https://www.klayout.org/downloads/master/doc-qt5/manual/loading.html |
| 6.4 | CIF 导入 | 支持 CIF 格式导入 | https://www.klayout.org/downloads/master/doc-qt5/manual/loading.html |
| 6.5 | Gerber 导入 | 支持 Gerber PCB 数据导入（需一些准备） | https://www.klayout.org/downloads/master/doc-qt5/manual/loading.html |
| 6.6 | LEF/DEF 导入 | 支持 LEF/DEF 格式导入 | https://www.klayout.de/ |
| 6.7 | GDS2 文本版本 | 支持 GDS2 的文本版本 | https://www.klayout.org/downloads/master/doc-qt5/manual/loading.html |
| 6.8 | gzip/zlib 压缩 | 如果文件是 gzip/zlib 压缩的，将自动解压 | https://www.klayout.org/downloads/master/doc-qt5/manual/loading.html |
| 6.9 | 读取器选项 | 提供读取器选项配置（限制层集、禁用文本对象、禁用用户属性等） | https://www.klayout.org/downloads/master/doc-qt5/manual/loading.html |
| 6.10 | SPICE 网表 | 支持 SPICE 网表格式用于 LVS 验证 | https://blog.csdn.net/gitblog_00207/article/details/157406033 |
| 6.11 | Verilog 网表 | 支持 Verilog 网表格式 | https://blog.csdn.net/gitblog_00207/article/details/157406033 |

### 2.7 DRM 设计规则管理

| 编号 | 功能点 | 描述 | 来源 URL |
|---|---|---|---|
| 7.1 | DRC runset | DRC 运行集（runsets）作为包（packages）进行管理 | https://www.klayout.org/downloads/master/doc-qt5/about/packages.html |
| 7.2 | DRC 脚本 | DRC 脚本基本上是 Ruby 脚本，在自定义环境中运行 | https://www.klayout.org/downloads/master/doc-qt5/about/macro_editor.html |
| 7.3 | LVS 脚本 | LVS 脚本与 DRC 脚本类似，在自定义环境中运行 | https://www.klayout.org/downloads/master/doc-qt5/about/macro_editor.html |
| 7.4 | 报告生成 | 支持报告生成（report），可指定严重级别 | https://blog.csdn.net/gitblog_00207/article/details/157406033 |
| 7.5 | profile 调试 | `profile` 可按 CPU 时间和进程内存增量打印命令 | https://wiki.f-si.org/images/1/19/FSiC2023_KLayout_DRCLVS_best_practices.pdf |
| 7.6 | new_target 调试 | `new_target` 允许将中间结果发送到单独的版图文件以便检查 | https://wiki.f-si.org/images/1/19/FSiC2023_KLayout_DRCLVS_best_practices.pdf |

### 2.8 Ruby 脚本

| 编号 | 功能点 | 描述 | 来源 URL |
|---|---|---|---|
| 8.1 | RBA 命名空间 | Ruby 脚本通过 RBA 命名空间访问 C++ API | https://www.klayout.org/downloads/master/doc-qt5/programming/python.html |
| 8.2 | Ruby 解释器 | KLayout 嵌入 Ruby 解释器，通过 RBA 模块暴露 C++ API | https://deepwiki.com/KLayout/klayout/8-scripting-and-extensions |
| 8.3 | Ruby PCell | 支持用 Ruby 实现 PCell | https://www.klayout.org/downloads/master/doc-qt5/programming/python.html |
| 8.4 | Ruby 宏 | 宏创建在 "Ruby" 标签页使用 Ruby 解释器 | https://www.klayout.org/downloads/master/doc-qt5/programming/python.html |
| 8.5 | MethodTable | Ruby 集成利用 MethodTable 处理动态方法分派和属性 | https://deepwiki.com/KLayout/klayout/8-scripting-and-extensions |
| 8.6 | 命令行执行 | 支持 `-rm`（运行后执行正常应用）和 `-r`（运行后退出）命令行选项 | https://www.klayout.org/downloads/master/doc-qt5/about/macro_editor.html |

### 2.9 Python 脚本

| 编号 | 功能点 | 描述 | 来源 URL |
|---|---|---|---|
| 9.1 | pya 命名空间 | Python 脚本通过 pya 命名空间（小写以符合 PEP-8）访问 C++ API | https://www.klayout.org/downloads/master/doc-qt5/programming/python.html |
| 9.2 | Python 解释器 | KLayout 嵌入 Python 解释器，通过 pya 模块暴露 C++ API | https://deepwiki.com/KLayout/klayout/8-scripting-and-extensions |
| 9.3 | Python PCell | 支持用 Python 实现 PCell，与 Ruby PCell 非常相似 | https://www.klayout.org/downloads/master/doc-qt5/programming/python.html |
| 9.4 | Python 宏 | Python 宏加载使用 ".py" 文件或 ".lym" 文件（解释器设为 "Python"） | https://www.klayout.org/downloads/master/doc-qt5/programming/python.html |
| 9.5 | pymacros 文件夹 | Python 宏文件夹称为 "pymacros"，与 Ruby 宏世界清晰分离 | https://www.klayout.org/downloads/master/doc-qt5/programming/python.html |
| 9.6 | klayout Python 包 | klayout Python 包在 PyPI 上提供，包含 klayout.db、klayout.tl、klayout.rdb 子模块 | https://www.klayout.org/klayout-pypi/ |
| 9.7 | klayout.db 子模块 | 几何数据库子模块（最重要模块） | https://www.klayout.org/klayout-pypi/ |
| 9.8 | klayout.rdb 子模块 | 报告数据库类子模块 | https://www.klayout.org/klayout-pypi/ |
| 9.9 | klayout.lay 子模块 | 用户界面组件子模块（仅完整 KLayout 包含） | https://www.klayout.org/klayout-pypi/ |
| 9.10 | PythonInspector | Python 脚本可在 "Inspector" 窗口检查本地上下文 | https://www.klayout.org/downloads/master/doc-qt5/about/macro_editor.html |
| 9.11 | KLAYOUT_PYTHONPATH | KLayout 从 `$KLAYOUT_PYTHONPATH` 读取 Python 路径 | https://www.klayout.org/downloads/master/doc-qt5/programming/python.html |

### 2.10 插件系统

| 编号 | 功能点 | 描述 | 来源 URL |
|---|---|---|---|
| 10.1 | Salt 包管理器 | "Salt" 是 KLayout 的包管理器，允许从全局仓库选择和安装包 | https://www.klayout.org/downloads/master/doc-qt5/about/packages.html |
| 10.2 | Salt.Mine 仓库 | "Salt.Mine" 包仓库服务是公共包部署的关键组件 | https://www.klayout.org/downloads/master/doc-qt5/about/packages.html |
| 10.3 | 包类型 | 包可覆盖 Ruby/Python 宏、DRC 运行集、技术、字体、静态版图库、PCell 库、代码库、二进制扩展 | https://www.klayout.org/downloads/master/doc-qt5/about/packages.html |
| 10.4 | 包依赖 | 包可依赖其他包，自动安装所需依赖 | https://www.klayout.org/downloads/master/doc-qt5/about/packages.html |
| 10.5 | 包版本信息 | 包附带版本信息，KLayout 可检查更新 | https://www.klayout.org/downloads/master/doc-qt5/about/packages.html |
| 10.6 | 包管理器 UI | 通过 "Tools/Manage Packages" 打开包管理器 | https://www.klayout.org/downloads/master/doc-qt5/about/packages.html |
| 10.7 | 包模板 | KLayout 提供从模板初始化新包的功能 | https://www.klayout.org/downloads/master/doc-qt5/about/packages.html |
| 10.8 | grain.xml | 包详情保存在包文件夹内的 "grain.xml" 文件中 | https://www.klayout.org/downloads/master/doc-qt5/about/packages.html |
| 10.9 | PluginFactory | 插件通过 lay::PluginFactory 注册扩展 UI 行为 | https://deepwiki.com/KLayout/klayout/8-scripting-and-extensions |

### 2.11 宏开发

| 编号 | 功能点 | 描述 | 来源 URL |
|---|---|---|---|
| 11.1 | 宏开发 IDE | 集成开发环境（IDE），允许编辑和调试 Ruby 和 Python 脚本 | https://www.klayout.org/downloads/master/doc-qt5/about/macro_editor.html |
| 11.2 | 调试器 | 提供简单调试器，支持设置断点和在断点处交互 | https://www.klayout.org/downloads/master/doc-qt5/about/macro_editor.html |
| 11.3 | 交互式控制台 | 交互式"控制台"允许输入和评估表达式 | https://www.klayout.org/downloads/master/doc-qt5/about/macro_editor.html |
| 11.4 | 监视表达式 | 支持监视表达式（Watch expressions），配置一系列表达式在断点中评估显示 | https://www.klayout.org/downloads/master/doc-qt5/about/macro_editor.html |
| 11.5 | .lym 文件 | 宏文件使用 ".lym" 后缀，是 XML 文件，存储宏代码和附加信息 | https://www.klayout.org/downloads/master/doc-qt5/about/macro_editor.html |
| 11.6 | 自动运行宏 | 宏可设置在启动时自动运行 | https://www.klayout.org/downloads/master/doc-qt5/about/macro_editor.html |
| 11.7 | 技术特定宏 | 宏可以是技术特定的，与技术打包并关联 | https://www.klayout.org/downloads/master/doc-qt5/about/macro_editor.html |
| 11.8 | 宏仓库 | KLayout 扫描 macros/pymacros 文件夹查找宏文件，递归扫描子目录 | https://www.klayout.org/downloads/master/doc-qt5/about/macro_editor.html |
| 11.9 | 全局仓库 | 安装路径中的 "macros" 或 "pymacros" 文件夹是"全局"仓库，通常所有用户共享 | https://www.klayout.org/downloads/master/doc-qt5/about/macro_editor.html |
| 11.10 | 本地仓库 | 用户特定应用文件夹中的 "macros" 或 "pymacros" 文件夹是"本地"仓库 | https://www.klayout.org/downloads/master/doc-qt5/about/macro_editor.html |

### 2.12 分析工具

| 编号 | 功能点 | 描述 | 来源 URL |
|---|---|---|---|
| 12.1 | XOR 工具 | 集成 XOR 和 diff 工具比较版图 | https://www.klayout.de/ |
| 12.2 | 网络追踪 | 集成网络追踪工具（net tracing tool） | https://www.klayout.de/ |
| 12.3 | 测量工具 | 提供测量布局功能 | https://www.klayout.de/ |
| 12.4 | 网络邻域图 | 能够自动从版图提取电路网络，生成直观的连接关系图 | https://blog.csdn.net/gitblog_00207/article/details/157406033 |
| 12.5 | LVS 浏览器 | LVS 浏览器直观展示匹配结果，绿色标识匹配项，红色标识差异点 | https://blog.csdn.net/gitblog_00207/article/details/157406033 |
| 12.6 | 交叉探测 | 双击差异项自动跳转到版图对应位置，结合原理图交叉验证 | https://blog.csdn.net/gitblog_00207/article/details/157406033 |

### 2.13 GSI 框架

| 编号 | 功能点 | 描述 | 来源 URL |
|---|---|---|---|
| 13.1 | Generic Scripting Interface | 通用脚本接口（GSI）是核心抽象层，使 KLayout 语言无关 | https://deepwiki.com/KLayout/klayout/8-scripting-and-extensions |
| 13.2 | gsi::ClassBase | C++ 类的元数据（继承、名称、模块） | https://deepwiki.com/KLayout/klayout/8-scripting-and-extensions |
| 13.3 | gsi::MethodBase | C++ 方法的元数据（参数、返回类型、标志） | https://deepwiki.com/KLayout/klayout/8-scripting-and-extensions |
| 13.4 | 惰性绑定 | Python 和 Ruby 对象仅在从脚本访问时创建 | https://deepwiki.com/KLayout/klayout/8-scripting-and-extensions |
| 13.5 | 方法缓存 | rba::MethodTable 和 pya::PythonModule 缓存解析的方法指针以最小化循环中的查找开销 | https://deepwiki.com/KLayout/klayout/8-scripting-and-extensions |

### 2.14 技术管理

| 编号 | 功能点 | 描述 | 来源 URL |
|---|---|---|---|
| 14.1 | 技术关联 | 版图文件可与技术关联，技术允许将版图与附加数据关联 | https://www.klayout.org/downloads/master/doc-qt5/manual/loading.html |
| 14.2 | 技术数据 | 技术数据包括库、宏、网络追踪器设置、层属性等 | https://www.klayout.org/downloads/master/doc-qt5/manual/loading.html |
| 14.3 | 技术包 | 技术可作为包进行管理 | https://www.klayout.org/downloads/master/doc-qt5/about/packages.html |

### 2.15 性能优化

| 编号 | 功能点 | 描述 | 来源 URL |
|---|---|---|---|
| 15.1 | 层次化处理 | 脚本集合（如 Region）可在不扁平化的情况下操作层次数据，显著减少内存使用 | https://deepwiki.com/KLayout/klayout/8-scripting-and-extensions |
| 15.2 | 不变性标志 | 自定义过滤器可声明 is_isotropic 或 is_scale_invariant 以优化层次几何处理 | https://deepwiki.com/KLayout/klayout/8-scripting-and-extensions |
| 15.3 | deep mode 性能 | deep mode 是大型层次版图的首选解决方案，结果/中间层是层次的，内存占用小 | https://wiki.f-si.org/images/1/19/FSiC2023_KLayout_DRCLVS_best_practices.pdf |
| 15.4 | tiled mode 并行 | tiled mode 沿分块并行化，良好扩展性，按 "cores 0.5" 扩展 | https://wiki.f-si.org/images/1/19/FSiC2023_KLayout_DRCLVS_best_practices.pdf |
| 15.5 | GF180 优化案例 | GF180 DRC/LVS 优化后：速度 10h→1h，内存 40G→<4G | https://wiki.f-si.org/images/1/19/FSiC2023_KLayout_DRCLVS_best_practices.pdf |

---

## 3. 功能点统计

| 类别 | 功能点数量 |
|---|---|
| 版图查看（View） | 13 |
| 版图编辑（Edit） | 9 |
| DRC（设计规则检查） | 12 |
| LVS（版图与原理图一致性验证） | 13 |
| 处理模式 | 7 |
| 文件格式支持 | 11 |
| DRM 设计规则管理 | 6 |
| Ruby 脚本 | 6 |
| Python 脚本 | 11 |
| 插件系统 | 9 |
| 宏开发 | 10 |
| 分析工具 | 6 |
| GSI 框架 | 5 |
| 技术管理 | 3 |
| 性能优化 | 5 |
| **总计** | **126** |

---

## 4. 参考来源

1. KLayout 官网: https://www.klayout.de/
2. KLayout GitHub: https://github.com/KLayout/klayout
3. KLayout 文档 (Qt5): https://www.klayout.org/downloads/master/doc-qt5/index.html
4. DRC Reference: Global Functions: https://www.klayout.org/downloads/master/doc-qt5/about/drc_ref_global.html
5. LVS Compare: https://www.klayout.org/downloads/master/doc-qt5/manual/lvs_compare.html
6. Loading A File: https://www.klayout.org/downloads/master/doc-qt5/manual/loading.html
7. About Packages: https://www.klayout.org/downloads/master/doc-qt5/about/packages.html
8. About Macro Development: https://www.klayout.org/downloads/master/doc-qt5/about/macro_editor.html
9. Using Python: https://www.klayout.org/downloads/master/doc-qt5/programming/python.html
10. The klayout Python Module: https://www.klayout.org/klayout-pypi/
11. FSiC2023 KLayout DRC/LVS Best Practices: https://wiki.f-si.org/images/1/19/FSiC2023_KLayout_DRCLVS_best_practices.pdf
12. DeepWiki KLayout DRC: https://deepwiki.com/KLayout/klayout/4.1-design-rule-checking-(drc)
13. DeepWiki KLayout Scripting: https://deepwiki.com/KLayout/klayout/8-scripting-and-extensions
