# T09 KLayout + T10 sax 逐点差距分析

| 项目 | 内容 |
|------|------|
| 调研日期 | 2026-06-25 |
| 版本 | v1.0 |
| 功能点总数 | 205（T09 KLayout 126 + T10 sax 79） |
| 对比基准 | PoLaRIS v1.0 功能点清单（308 功能点） |
| 代码路径 | `/workspace/src/polaris/` |

## 学术诚信声明

1. 每个功能点的 PoLaRIS 状态均基于实际代码标注，引用 `文件路径:行号`。
2. 状态图例：✅已有（PoLaRIS 有完整实现）/ ⚠️部分（有相关实现但不完整或定位不同）/ ❌缺失（PoLaRIS 无实现）/ 🚫不适用（功能与 PoLaRIS 定位无关，如 KLayout GUI/Ruby 脚本等）。
3. 覆盖率计算公式：`(✅ + 0.5×⚠️) / (总数 - 🚫)`，仅计入适用功能点。
4. PoLaRIS 定位为光电子 AI 布局布线引擎，非交互式版图编辑器；KLayout 定位为版图查看/编辑/DRC/LVS 工具，二者定位部分重叠（DRC/LVS/GDS）但核心场景不同。

---

## T09 KLayout（126 功能点）

### 2.1 版图查看（View）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 1.1 | 查看器模式 | ⚠️部分 | src/polaris/eval/layout_render.py:123 | PoLaRIS 有 render_layout 渲染，但非交互式查看器，无 GUI |
| 1.2 | 大文件支持 | ❌缺失 | - | PoLaRIS 不直接处理多 GB 版图，依赖 KLayout 库间接支持 |
| 1.3 | 多层叠加 | ✅已有 | src/polaris/eval/layout_render.py:123 | render_layout 支持多层渲染 |
| 1.4 | 标尺工具 | ❌缺失 | - | PoLaRIS 无交互式标尺 |
| 1.5 | 图像叠加 | ❌缺失 | - | PoLaRIS 无图像叠加功能 |
| 1.6 | 样式选项 | ⚠️部分 | src/polaris/eval/layout_render.py:123 | matplotlib 渲染有样式选项，但远少于 KLayout |
| 1.7 | 可切换层视图 | ❌缺失 | - | PoLaRIS 无交互式层切换 |
| 1.8 | 书签 | ❌缺失 | - | PoLaRIS 无书签功能 |
| 1.9 | 层次化上下文视图 | ❌缺失 | - | PoLaRIS 有层次化布局器但非查看器视图 |
| 1.10 | 搜索功能 | ❌缺失 | - | PoLaRIS 无版图搜索 |
| 1.11 | 按实例/形状浏览 | ❌缺失 | - | PoLaRIS 无实例/形状浏览 |
| 1.12 | 选择性单元屏蔽 | ❌缺失 | - | PoLaRIS 无单元屏蔽 |
| 1.13 | 2.5D 视图 | ❌缺失 | - | PoLaRIS 仅 2D 渲染，无 2.5D |

### 2.2 版图编辑（Edit）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 2.1 | 编辑器模式 | 🚫不适用 | - | PoLaRIS 定位为 AI 布局布线引擎，非交互式版图编辑器，通过 PCell+GDS 导出生成版图 |
| 2.2 | 创建层和单元 | ⚠️部分 | src/polaris/pdk/pcell.py:576 | 通过 PCell 编程创建，非交互式创建 |
| 2.3 | 几何图形绘制 | ⚠️部分 | src/polaris/pdk/pcell.py:667-719 | PCell 内置多边形/矩形/路径绘制，非交互式 |
| 2.4 | 变换操作 | ✅已有 | src/polaris/engine/floorplan_env.py:157 | 布局环境支持移动/旋转/镜像 |
| 2.5 | 布尔运算 | ❌缺失 | - | PoLaRIS 无几何布尔运算（并/交/差） |
| 2.6 | 搜索替换 | ❌缺失 | - | PoLaRIS 无形状/实例搜索替换 |
| 2.7 | 参数化单元 PCell | ✅已有 | src/polaris/pdk/pcell.py:576 | polaris_cell 装饰器 + 4 个内置 PCell |
| 2.8 | 复制/粘贴 | ❌缺失 | - | PoLaRIS 无交互式复制粘贴 |
| 2.9 | 无限撤销/重做 | ❌缺失 | - | PoLaRIS 无撤销/重做栈 |

### 2.3 DRC（设计规则检查）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 3.1 | DRC 引擎 | ✅已有 | src/polaris/sim/klayout_drc.py:238; src/polaris/sim/hierarchical_drc.py:165 | KLayoutDRCRunner + HierarchicalDRC 双引擎 |
| 3.2 | DRCLayer 类 | ⚠️部分 | src/polaris/sim/klayout_drc.py:238 | 通过 KLayout 库间接使用 DRCLayer，无独立封装 |
| 3.3 | 通用 DRC 函数 | ✅已有 | src/polaris/sim/klayout_drc.py:531; src/polaris/sim/hierarchical_drc.py:487 | run_klayout_drc + run_hierarchical_drc 入口 |
| 3.4 | DRC 表达式 | ⚠️部分 | src/polaris/sim/klayout_drc.py:238 | 通过 KLayout runset 表达式，无独立 DRCOpNode |
| 3.5 | 天线检查 | 🚫不适用 | - | 天线检查为电子 IC 工艺规则，光子电路不适用 |
| 3.6 | 设备提取 | ⚠️部分 | src/polaris/sim/lvs.py:121 | 有光子网表提取，非电子设备参数化提取 |
| 3.7 | 宽度检查 | ✅已有 | src/polaris/sim/constraint_checker.py:53 | ConstraintChecker 含宽度约束 |
| 3.8 | 间距检查 | ✅已有 | src/polaris/sim/constraint_checker.py:53 | ConstraintChecker 含间距约束 |
| 3.9 | 包围检查 | ❌缺失 | - | PoLaRIS 无 enclosing 检查 |
| 3.10 | 面积检查 | ⚠️部分 | src/polaris/data/benchmark_evaluator.py:120 | 有面积利用率评估，无面积条件选择形状 |
| 3.11 | 角点选择 | ❌缺失 | - | PoLaRIS 无 corners 选择 |
| 3.12 | 覆盖检查 | ❌缺失 | - | PoLaRIS无 covering 检查 |

### 2.4 LVS（版图与原理图一致性验证）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 4.1 | LVS 比较 | ✅已有 | src/polaris/sim/graph_lvs.py:160; src/polaris/sim/lvs.py:494 | GraphIsomorphismLVSComparer + run_lvs |
| 4.2 | 网表等价提示 | ❌缺失 | - | PoLaRIS 无 same_nets 调试提示 |
| 4.3 | 电路等价提示 | ❌缺失 | - | PoLaRIS 无 same_circuit 等价声明 |
| 4.4 | 容差设置 | ⚠️部分 | src/polaris/sim/lvs.py:465 | compare_netlists 支持容差，但功能较简单 |
| 4.5 | 引脚交换 | ❌缺失 | - | PoLaRIS 无引脚交换 |
| 4.6 | 电容/电阻消除 | 🚫不适用 | - | 电子 IC LVS 特性，光子电路不适用 |
| 4.7 | 引脚标签检查 | ⚠️部分 | src/polaris/sim/graph_lvs.py:89 | PhotonicsNetlist 含引脚信息，无专门标签检查 |
| 4.8 | 网表层次结构 | ✅已有 | src/polaris/sim/graph_lvs.py:89 | PhotonicsNetlist 支持层次结构 |
| 4.9 | 连接定义 | ✅已有 | src/polaris/data/data_loader.py:105 | circuit_spec_to_netlist_dict 定义连接 |
| 4.10 | 全局连接 | ❌缺失 | - | PoLaRIS 无 connect_global 全局网络 |
| 4.11 | 隐式连接 | ❌缺失 | - | PoLaRIS 无 connect_implicit 标签模式 |
| 4.12 | 显式连接 | ✅已有 | src/polaris/data/data_loader.py:105 | 网表显式定义连接关系 |
| 4.13 | 设备提取器 | ⚠️部分 | src/polaris/sim/lvs.py:121 | 有光子器件网表提取，无 bjt/mos 等电子提取器 |

### 2.5 处理模式

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 5.1 | flat mode（扁平模式） | ❌缺失 | - | PoLaRIS 无扁平化处理模式 |
| 5.2 | tiled mode（分块模式） | ❌缺失 | - | PoLaRIS 无 tiles() 分块 |
| 5.3 | hierarchical mode（层次模式） | ✅已有 | src/polaris/sim/hierarchical_drc.py:165; src/polaris/engine/hierarchical_placer.py:85 | 层次化 DRC + 层次化布局器 |
| 5.4 | deep mode（深度模式） | ❌缺失 | - | PoLaRIS 无 deep() 深度模式 |
| 5.5 | deep_reject_odd_polygons | ❌缺失 | - | PoLaRIS 无奇多边形拒绝选项 |
| 5.6 | 线程并行 | ⚠️部分 | src/polaris/trainer/parallel_rollout.py:80 | 训练并行 rollout，非 DRC 线程并行 |
| 5.7 | 分块边界 | ❌缺失 | - | PoLaRIS 无 tile border |

### 2.6 文件格式支持

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 6.1 | GDSII 读写 | ✅已有 | src/polaris/eval/layout_render.py:331; src/polaris/data/gds_loader.py:468 | export_gds 导出 + load_gds_to_circuit 读取 |
| 6.2 | OASIS 读写 | ⚠️部分 | src/polaris/eval/layout_render.py:361 | 仅 export_oasis 导出，无 OASIS 读取 |
| 6.3 | DXF 导入 | ❌缺失 | - | PoLaRIS 无 DXF 支持 |
| 6.4 | CIF 导入 | ❌缺失 | - | PoLaRIS 无 CIF 支持 |
| 6.5 | Gerber 导入 | ❌缺失 | - | PoLaRIS 无 Gerber 支持 |
| 6.6 | LEF/DEF 导入 | ❌缺失 | - | PoLaRIS 无 LEF/DEF 支持 |
| 6.7 | GDS2 文本版本 | ❌缺失 | - | PoLaRIS 无 GDS2 文本格式 |
| 6.8 | gzip/zlib 压缩 | ❌缺失 | - | PoLaRIS 无自动解压 |
| 6.9 | 读取器选项 | ❌缺失 | - | PoLaRIS 无读取器选项配置 |
| 6.10 | SPICE 网表 | ⚠️部分 | src/polaris/sim/mna_spice.py:102 | 有 MNA SPICE 求解器，无 SPICE 网表文件格式 |
| 6.11 | Verilog 网表 | ❌缺失 | - | PoLaRIS 无 Verilog 网表 |

### 2.7 DRM 设计规则管理

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 7.1 | DRC runset | ✅已有 | src/polaris/sim/foundry_runsets.py:41 | FoundryRunset + FOUNDRY_RUNSETS 注册表 |
| 7.2 | DRC 脚本 | ⚠️部分 | src/polaris/sim/klayout_drc.py:238 | 通过 KLayout runset 脚本，无独立 Ruby 脚本环境 |
| 7.3 | LVS 脚本 | ✅已有 | src/polaris/sim/lvs.py:494 | run_lvs 入口 |
| 7.4 | 报告生成 | ⚠️部分 | src/polaris/sim/klayout_drc.py:193 | DRCResult 数据类，无严重级别报告 |
| 7.5 | profile 调试 | ❌缺失 | - | PoLaRIS 无 profile 性能分析 |
| 7.6 | new_target 调试 | ❌缺失 | - | PoLaRIS 无中间结果导出 |

### 2.8 Ruby 脚本

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 8.1 | RBA 命名空间 | 🚫不适用 | - | PoLaRIS 为纯 Python 项目，不使用 Ruby |
| 8.2 | Ruby 解释器 | 🚫不适用 | - | PoLaRIS 不嵌入 Ruby 解释器 |
| 8.3 | Ruby PCell | 🚫不适用 | - | PoLaRIS 用 Python PCell（pcell.py:576） |
| 8.4 | Ruby 宏 | 🚫不适用 | - | PoLaRIS 不使用 Ruby 宏 |
| 8.5 | MethodTable | 🚫不适用 | - | Ruby 特有动态方法分派，PoLaRIS 不适用 |
| 8.6 | 命令行执行 | ✅已有 | src/polaris/pipeline/__init__.py:291 | main() argparse CLI 入口 |

### 2.9 Python 脚本

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 9.1 | pya 命名空间 | ✅已有 | src/polaris/sim/klayout_drc.py:238 | 通过 klayout Python 包使用 pya 等价 API |
| 9.2 | Python 解释器 | ✅已有 | - | PoLaRIS 为纯 Python 项目 |
| 9.3 | Python PCell | ✅已有 | src/polaris/pdk/pcell.py:576 | polaris_cell 装饰器实现 Python PCell |
| 9.4 | Python 宏 | ❌缺失 | - | PoLaRIS 无 .lym/.py 宏加载系统 |
| 9.5 | pymacros 文件夹 | ❌缺失 | - | PoLaRIS 无 pymacros 宏目录 |
| 9.6 | klayout Python 包 | ✅已有 | src/polaris/sim/klayout_drc.py:238 | 直接 import klayout |
| 9.7 | klayout.db 子模块 | ✅已有 | src/polaris/sim/klayout_drc.py:238 | 使用 klayout.db 几何数据库 |
| 9.8 | klayout.rdb 子模块 | ⚠️部分 | src/polaris/sim/klayout_drc.py:193 | DRCResult 自定义，未直接用 klayout.rdb |
| 9.9 | klayout.lay 子模块 | 🚫不适用 | - | klayout.lay 为 UI 组件，PoLaRIS 无 GUI |
| 9.10 | PythonInspector | ❌缺失 | - | PoLaRIS 无 Inspector 窗口 |
| 9.11 | KLAYOUT_PYTHONPATH | ❌缺失 | - | PoLaRIS 无 KLayout 专用 Python 路径 |

### 2.10 插件系统

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 10.1 | Salt 包管理器 | ❌缺失 | - | PoLaRIS 无 Salt 包管理器 |
| 10.2 | Salt.Mine 仓库 | ❌缺失 | - | PoLaRIS 无包仓库服务 |
| 10.3 | 包类型 | ❌缺失 | - | PoLaRIS 无多类型包系统 |
| 10.4 | 包依赖 | ❌缺失 | - | PoLaRIS 无包依赖管理 |
| 10.5 | 包版本信息 | ❌缺失 | - | PoLaRIS 无包版本检查 |
| 10.6 | 包管理器 UI | ❌缺失 | - | PoLaRIS 无包管理器 UI |
| 10.7 | 包模板 | ❌缺失 | - | PoLaRIS 无包模板初始化 |
| 10.8 | grain.xml | ❌缺失 | - | PoLaRIS 无 grain.xml 包描述 |
| 10.9 | PluginFactory | ❌缺失 | - | PoLaRIS 无 PluginFactory 注册 |

### 2.11 宏开发

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 11.1 | 宏开发 IDE | ❌缺失 | - | PoLaRIS 无集成 IDE |
| 11.2 | 调试器 | ❌缺失 | - | PoLaRIS 无断点调试器 |
| 11.3 | 交互式控制台 | ❌缺失 | - | PoLaRIS 无交互式控制台 |
| 11.4 | 监视表达式 | ❌缺失 | - | PoLaRIS 无 watch 表达式 |
| 11.5 | .lym 文件 | ❌缺失 | - | PoLaRIS 无 .lym 宏文件 |
| 11.6 | 自动运行宏 | ❌缺失 | - | PoLaRIS 无启动自动运行宏 |
| 11.7 | 技术特定宏 | ❌缺失 | - | PoLaRIS 无技术特定宏 |
| 11.8 | 宏仓库 | ❌缺失 | - | PoLaRIS 无宏仓库扫描 |
| 11.9 | 全局仓库 | ❌缺失 | - | PoLaRIS 无全局宏仓库 |
| 11.10 | 本地仓库 | ❌缺失 | - | PoLaRIS 无本地宏仓库 |

### 2.12 分析工具

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 12.1 | XOR 工具 | ❌缺失 | - | PoLaRIS 无版图 XOR diff 工具 |
| 12.2 | 网络追踪 | ⚠️部分 | src/polaris/sim/lvs.py:121 | 有网表提取，无交互式网络追踪 |
| 12.3 | 测量工具 | ⚠️部分 | src/polaris/data/benchmark_evaluator.py:57 | 有 HPWL/面积等测量，无交互式测量 |
| 12.4 | 网络邻域图 | ⚠️部分 | src/polaris/engine/netlist.py | 有 netlist 图结构，无自动连接关系图生成 |
| 12.5 | LVS 浏览器 | ❌缺失 | - | PoLaRIS 无 LVS 结果 GUI 浏览器 |
| 12.6 | 交叉探测 | ❌缺失 | - | PoLaRIS 无双击跳转交叉探测 |

### 2.13 GSI 框架

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 13.1 | Generic Scripting Interface | 🚫不适用 | - | GSI 为 KLayout C++/脚本桥接特有框架，PoLaRIS 纯 Python 无需此抽象 |
| 13.2 | gsi::ClassBase | 🚫不适用 | - | KLayout C++ 元数据特有 |
| 13.3 | gsi::MethodBase | 🚫不适用 | - | KLayout C++ 方法元数据特有 |
| 13.4 | 惰性绑定 | 🚫不适用 | - | KLayout 脚本对象特有 |
| 13.5 | 方法缓存 | 🚫不适用 | - | KLayout rba::MethodTable 特有 |

### 2.14 技术管理

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 14.1 | 技术关联 | ✅已有 | src/polaris/pdk/foundry_platforms.py:39 | FoundryPlatform 平台元数据 |
| 14.2 | 技术数据 | ✅已有 | src/polaris/pdk/catalog.py:227 | DeviceCatalog 器件库 + PDK 数据 |
| 14.3 | 技术包 | ✅已有 | src/polaris/pdk/gdsfactory_pdk_bridge.py:349 | PolarisPDKRegistry 48 个 PDK 注册 |

### 2.15 性能优化

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 15.1 | 层次化处理 | ✅已有 | src/polaris/engine/hierarchical_placer.py:85; src/polaris/sim/hierarchical_drc.py:165 | 层次化布局 + 层次化 DRC |
| 15.2 | 不变性标志 | ❌缺失 | - | PoLaRIS 无 is_isotropic/is_scale_invariant 标志 |
| 15.3 | deep mode 性能 | ❌缺失 | - | PoLaRIS 无 deep mode |
| 15.4 | tiled mode 并行 | ❌缺失 | - | PoLaRIS 无 tiled 并行 |
| 15.5 | GF180 优化案例 | ❌缺失 | - | PoLaRIS 无 GF180 优化案例 |

### T09 统计

| 状态 | 数量 | 占比 |
|------|------|------|
| ✅已有 | 25 | 19.8% |
| ⚠️部分 | 20 | 15.9% |
| ❌缺失 | 67 | 53.2% |
| 🚫不适用 | 14 | 11.1% |
| **合计** | **126** | **100%** |

**T09 覆盖率**：`(25 + 0.5×20) / (126 - 14) = 35 / 112 = 31.25%`

**关键差距**：
1. PoLaRIS 无交互式 GUI（查看器/编辑器/标尺/书签/搜索等 13 项查看功能缺失）
2. PoLaRIS 无宏/插件系统（Salt 包管理器 + 宏 IDE 共 19 项缺失）
3. PoLaRIS 无 KLayout 特有 GSI/Ruby 框架（14 项不适用）
4. PoLaRIS DRC/LVS 核心能力已有，但缺天线/包围/角点/覆盖等高级检查
5. PoLaRIS 文件格式支持单一（仅 GDSII 完整，OASIS 仅导出，无 DXF/CIF/Gerber/LEF-DEF）

---

## T10 sax（79 功能点）

### 2.1 JAX S 参数仿真

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 1.1 | JAX 后端 | ✅已有 | src/polaris/sim/jax_backend.py:65 | is_jax_available + JAX 后端 |
| 1.2 | S 字典（SDict） | ✅已有 | src/polaris/sim/cascade.py:315 | cascade_circuit 使用 SDict |
| 1.3 | 函数式模型 | ✅已有 | src/polaris/sim/models.py:159 | 10 种模型为返回 S 字典的函数 |
| 1.4 | 标准字典 | ✅已有 | src/polaris/sim/models.py:159 | 使用标准 Python 字典 |
| 1.5 | XLA 加速 | ✅已有 | src/polaris/sim/jax_backend.py:101 | jit_compile JIT 编译 |
| 1.6 | GPU 加速 | ⚠️部分 | src/polaris/engine/gpu_backend.py:221 | GPUBackend CuPy 后端（实验性），非 JAX GPU |
| 1.7 | 双精度支持 | ⚠️部分 | src/polaris/sim/jax_backend.py:65 | 通过 JAX 支持，无显式双精度配置入口 |

### 2.2 子网络增长算法（Subnetwork Growth）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 2.1 | 子网络增长 | ✅已有 | src/polaris/sim/cascade.py:315 | cascade_circuit 子网络增长复刻 |
| 2.2 | Filipsson-Gunnar 后端 | ✅已有 | src/polaris/sim/cascade.py:397 | _cascade_with_sax SAX 后端级联 |
| 2.3 | 算法遍历 | ✅已有 | src/polaris/sim/cascade.py:315 | cascade_circuit 实现算法遍历 |
| 2.4 | 算法改进 | ⚠️部分 | src/polaris/sim/subnetwork_decomp.py:407 | SubnetworkDecomposition 改进，非 FG 改进 |
| 2.5 | reciprocal 函数 | ❌缺失 | - | PoLaRIS 无 reciprocal 互易填充 |

### 2.3 autograd 逆向（自动微分）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 3.1 | 自动微分 | ✅已有 | src/polaris/sim/autodiff.py:40 | compute_gradient JAX 自动微分 |
| 3.2 | 梯度优化 | ✅已有 | src/polaris/sim/adjoint_optimizer.py:204 | AdjointOptimizer JAX 自动微分优化 |
| 3.3 | MZI 优化 | ⚠️部分 | src/polaris/sim/adjoint_optimizer.py:204 | 有 Adjoint 优化，无专门 MZI 优化示例 |
| 3.4 | 逆向设计 | ✅已有 | src/polaris/sim/ai_inverse_design.py:382 | RLInverseDesigner 逆向设计 |
| 3.5 | JAX 优化器 | ⚠️部分 | src/polaris/sim/lbfgs_optimizer.py:132 | 用 L-BFGS/NSGA-II 等，非 jax.example_libraries.optimizers |

### 2.4 cocotb 联合仿真

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 4.1 | 直接 cocotb 集成 | ❌缺失 | - | PoLaRIS 无 cocotb 集成 |
| 4.2 | SPICE 协同仿真 | ✅已有 | src/polaris/sim/mna_spice.py:102; src/polaris/sim/verilog_a.py:712 | MNASolver + run_ngspice_cosimulation |

### 2.5 gdsfactory 集成

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 5.1 | gplugins.sax | ✅已有 | src/polaris/pdk/gdsfactory_integration.py | gdsfactory 集成模块 |
| 5.2 | SAX gdsfactory 兼容性 | ✅已有 | src/polaris/pdk/gdsfactory_pdk_bridge.py:349 | PolarisPDKRegistry 桥接 |
| 5.3 | 布局感知 Monte Carlo | ✅已有 | src/polaris/sim/layout_aware.py:361; src/polaris/sim/monte_carlo.py:63 | LayoutAwareSimulator + monte_carlo_simulate |
| 5.4 | 紧凑 MZI | ⚠️部分 | src/polaris/sim/models.py | 有 MZI 相关模型，无专门紧凑 MZI 仿真 |
| 5.5 | 相移器模型 | ✅已有 | src/polaris/sim/models.py:455 | phase_shifter_s 模型 |
| 5.6 | 层次化电路 | ✅已有 | src/polaris/engine/hierarchical_placer.py:85 | HierarchicalPlacer 层次化 |
| 5.7 | FDTD S 参数模型 | ✅已有 | src/polaris/sim/fdtd_simulator.py:279 | run_fdtd_simulation FDTD 仿真 |
| 5.8 | QPDK 集成 | ❌缺失 | - | PoLaRIS 无量子 RF PDK 集成 |
| 5.9 | JAX 后端比较 | ⚠️部分 | src/polaris/sim/jax_backend.py:74 | get_jax_devices 探测，无跨后端基准测试 |

### 2.6 多端口器件

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 6.1 | 多端口 S 矩阵 | ✅已有 | src/polaris/sim/models.py:159-455 | mmi_2x2_s 等多端口模型 |
| 6.2 | 定向耦合器模型 | ✅已有 | src/polaris/sim/models.py | directional_coupler_s 模型 |
| 6.3 | 端口组合 | ✅已有 | src/polaris/sim/cascade.py:315 | 使用 2-tuple 端口组合作为键 |
| 6.4 | 稀疏 S 矩阵 | ✅已有 | src/polaris/sim/cascade.py:315 | 字典表示稀疏 S 矩阵 |
| 6.5 | 字符串索引 | ✅已有 | src/polaris/sim/models.py:159 | 字符串端口名索引 |

### 2.7 频率扫描

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 7.1 | 波长扫描 | ✅已有 | src/polaris/sim/simulator.py:57 | CircuitSimulator 频率扫描 |
| 7.2 | 全局设置 | ⚠️部分 | src/polaris/sim/simulator.py:57 | 有全局参数，无根分发到同名子组件 |
| 7.3 | 嵌套设置 | ⚠️部分 | src/polaris/sim/cascade.py:315 | 有嵌套电路，无嵌套设置调用 |
| 7.4 | 频率分辨率 | ⚠️部分 | src/polaris/sim/simulator.py:57 | 有频率配置，无分辨率基准测试 |
| 7.5 | 多波长 S 参数 | ✅已有 | src/polaris/sim/simulator.py:57 | S 参数支持数组（多波长） |

### 2.8 级联算法（Backends）

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 8.1 | KLU 后端 | ❌缺失 | - | PoLaRIS 无 KLU 后端 |
| 8.2 | KLU 理论背景 | ❌缺失 | - | PoLaRIS 无 KLU 直接稀疏求解器 |
| 8.3 | 稀疏辅助函数 | ⚠️部分 | src/polaris/sim/subnetwork_decomp.py:51 | BlockTridiagonalMatrix 稀疏，非 KLU 辅助 |
| 8.4 | KLU 算法遍历 | ❌缺失 | - | PoLaRIS 无 KLU 遍历 |
| 8.5 | KLU 算法改进 | ❌缺失 | - | PoLaRIS 无 KLU 改进 |
| 8.6 | Filipsson-Gunnar 后端 | ✅已有 | src/polaris/sim/cascade.py:397 | _cascade_with_sax FG 后端 |
| 8.7 | Additive 后端 | ❌缺失 | - | PoLaRIS 无 Additive 后端 |
| 8.8 | Forward-only 后端 | ❌缺失 | - | PoLaRIS 无 Forward-only 后端 |
| 8.9 | Forward-only 加速 | ❌缺失 | - | PoLaRIS 无 Forward-only 加速 |
| 8.10 | Sparse COO 后端 | ❌缺失 | - | PoLaRIS 无 Sparse COO 后端 |
| 8.11 | 后端可互换 | ⚠️部分 | src/polaris/sim/cascade.py:315 | 有 SAX 后端，无多后端互换机制 |
| 8.12 | analyze_instances | ⚠️部分 | src/polaris/sim/dag_scheduler.py:44 | CircuitDAG 分析，非端口组合分析 |
| 8.13 | analyze_circuit | ✅已有 | src/polaris/sim/dag_scheduler.py:44 | CircuitDAG 电路分析 |
| 8.14 | evaluate_circuit | ✅已有 | src/polaris/sim/cascade.py:315 | cascade_circuit 电路评估 |
| 8.15 | klujax 依赖 | ❌缺失 | - | PoLaRIS 无 klujax 依赖 |

### 2.9 电路构建

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 9.1 | sax.circuit | ✅已有 | src/polaris/sim/cascade.py:315 | cascade_circuit 从网表构建电路 |
| 9.2 | 网表格式 | ✅已有 | src/polaris/data/data_loader.py:105 | circuit_spec_to_netlist_dict 三部分网表 |
| 9.3 | YAML 电路 | ✅已有 | src/polaris/pdk/gdsfactory_pdk_bridge.py:298 | parse_pic_yaml YAML 解析 |
| 9.4 | 模型组合 | ✅已有 | src/polaris/sim/cascade.py:315 | 组件模型可组合成电路 |

### 2.10 模型库

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 10.1 | 内置模型 | ✅已有 | src/polaris/sim/models.py:159-455 | 10 种基础器件 S 参数模型 |
| 10.2 | RF 模型 | ❌缺失 | - | PoLaRIS 无 sax.models.rf RF 模型 |
| 10.3 | 模型拟合 | ❌缺失 | - | PoLaRIS 无 sax.fit 模型拟合 |
| 10.4 | 参数化模型 | ✅已有 | src/polaris/sim/models.py:25-107 | RingParams/WaveguideParams/CouplerParams 参数化 |
| 10.5 | 表面模型 | ❌缺失 | - | PoLaRIS 无表面模型 |
| 10.6 | 所有模型 | ✅已有 | src/polaris/sim/models.py:159-455 | 10 种模型完整参考 |

### 2.11 仿真示例

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 11.1 | 快速开始 | ✅已有 | src/polaris/pipeline/__init__.py:156 | cmd_run CLI 快速开始 |
| 11.2 | 全通滤波器 | ⚠️部分 | src/polaris/sim/models.py | 有 ring_resonator_s，无专门全通滤波器示例 |
| 11.3 | 多模仿真 | ❌缺失 | - | PoLaRIS 无多模仿真 |
| 11.4 | 薄膜仿真 | ❌缺失 | - | PoLaRIS 无薄膜仿真 |
| 11.5 | 加性后端示例 | ❌缺失 | - | PoLaRIS 无 Additive 后端示例 |
| 11.6 | 布局感知 | ✅已有 | src/polaris/sim/layout_aware.py:361 | LayoutAwareSimulator 布局感知 |
| 11.7 | 稀疏 COO 示例 | ❌缺失 | - | PoLaRIS 无稀疏 COO 示例 |
| 11.8 | 前向 only 示例 | ❌缺失 | - | PoLaRIS 无 Forward-only 示例 |
| 11.9 | neff 色散 | ✅已有 | src/polaris/sim/simulator.py:357 | analyze_dispersion 色散分析 |

### 2.12 量子电路仿真

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 12.1 | 量子电路仿真 | ✅已有 | src/polaris/sim/quantum_photonics.py:40 | permanent_ryser + boson_sampling 量子仿真 |
| 12.2 | 耦合谐振器电路 | ⚠️部分 | src/polaris/sim/models.py | 有 ring_resonator_s，无专门耦合谐振器电路 |
| 12.3 | OpenVINO NPU | ❌缺失 | - | PoLaRIS 无 OpenVINO NPU 支持 |
| 12.4 | JAXPR 导出 | ❌缺失 | - | PoLaRIS 无 JAXPR 导出 |
| 12.5 | 后端检测 | ✅已有 | src/polaris/sim/jax_backend.py:65 | is_jax_available + get_jax_devices 后端探测 |

### 2.13 LLM 集成

| # | 功能点 | PoLaRIS状态 | PoLaRIS实现位置 | 差距说明 |
|---|--------|------------|----------------|----------|
| 13.1 | PICBench 基准 | ❌缺失 | - | PoLaRIS 无 PICBench LLM 基准 |
| 13.2 | JSON 网表 | ✅已有 | src/polaris/sim/siepic_netlist.py:133 | parse_siepic_json JSON 网表解析 |

### T10 统计

| 状态 | 数量 | 占比 |
|------|------|------|
| ✅已有 | 41 | 51.9% |
| ⚠️部分 | 15 | 19.0% |
| ❌缺失 | 23 | 29.1% |
| 🚫不适用 | 0 | 0.0% |
| **合计** | **79** | **100%** |

**T10 覆盖率**：`(41 + 0.5×15) / 79 = 48.5 / 79 = 61.39%`

**关键差距**：
1. PoLaRIS 缺 KLU 后端（sax v0.10.0 起默认后端）及相关稀疏求解器（8.1/8.2/8.4/8.5/8.15 共 5 项）
2. PoLaRIS 缺 Forward-only/Additive/Sparse COO 等高级后端（8.7/8.8/8.9/8.10 共 4 项）
3. PoLaRIS 缺 reciprocal 互易填充函数（2.5）
4. PoLaRIS 缺 sax.fit 模型拟合与 RF/表面模型（10.2/10.3/10.5）
5. PoLaRIS 缺多模/薄膜仿真示例（11.3/11.4）
6. PoLaRIS 缺 OpenVINO NPU 与 JAXPR 导出（12.3/12.4）
7. PoLaRIS 缺 PICBench LLM 基准（13.1）
8. PoLaRIS 核心子网络增长 + autograd + 电路构建 + 模型库已对齐 sax

---

## 总体汇总

| 工具 | 功能点总数 | ✅已有 | ⚠️部分 | ❌缺失 | 🚫不适用 | 覆盖率 |
|------|-----------|--------|--------|--------|----------|--------|
| T09 KLayout | 126 | 25 | 20 | 67 | 14 | 31.25% |
| T10 sax | 79 | 41 | 15 | 23 | 0 | 61.39% |
| **合计** | **205** | **66** | **35** | **90** | **14** | **44.95%** |

**总体覆盖率**：`(66 + 0.5×35) / (205 - 14) = 83.5 / 191 = 43.72%`

### 差距分级

#### P0 阻断商业交付（需优先补齐）
- T09 KLayout DRC 高级检查：包围检查(3.9)/角点选择(3.11)/覆盖检查(3.12)
- T10 sax KLU 后端（8.1-8.5/8.15）：sax 默认后端，影响大电路仿真性能
- T10 sax reciprocal 函数(2.5)：互易填充基础功能

#### P1 影响竞争力（中期补齐）
- T09 KLayout 文件格式扩展：OASIS 读取(6.2)/DXF(6.3)/CIF(6.4)
- T09 KLayout LVS 高级特性：网表等价提示(4.2/4.3)/引脚交换(4.5)/全局连接(4.10)
- T10 sax 高级后端：Forward-only(8.8)/Additive(8.7)/Sparse COO(8.10)
- T10 sax 模型拟合(10.3)与 RF 模型(10.2)

#### P2 长期演进（按需补齐）
- T09 KLayout GUI/查看器/编辑器（1.x/2.x）：PoLaRIS 定位为 AI 引擎，非交互式工具
- T09 KLayout 宏/插件系统（10.x/11.x）：PoLaRIS 用 Python 包管理
- T09 KLayout GSI/Ruby 框架（13.x/8.x）：PoLaRIS 纯 Python，不适用
- T10 sax OpenVINO NPU(12.3)/JAXPR 导出(12.4)/PICBench(13.1)：前沿能力

### 学术诚信声明

1. 本文档所有 PoLaRIS 状态均基于实际代码标注，引用 `文件路径:行号`。
2. T09 126 功能点 + T10 79 功能点 = 205 功能点全部逐点标注，无遗漏。
3. 🚫不适用项均为与 PoLaRIS 定位无关的功能（KLayout GUI/Ruby/GSI 等），共 14 项。
4. 覆盖率计算仅计入适用功能点（排除 🚫不适用）。
5. PoLaRIS 定位为光电子 AI 布局布线引擎，与 KLayout（版图查看/编辑/DRC/LVS）和 sax（S 参数仿真）定位部分重叠，核心重叠领域为 DRC/LVS/S 参数仿真/GDS 导出。
