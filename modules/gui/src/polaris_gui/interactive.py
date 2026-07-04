"""P0-3 GUI 版图编辑器交互功能（interactive.py）— Facade 层。

实现 L-Edit / KLayout / OptoDesigner 风格交互式版图编辑器：
- 曲线多边形（贝塞尔 / Catmull-Rom 样条 / 圆弧 / 椭圆 / 顶点编辑）
- 对象交互（snap-to-grid 抓取移动 / 拖放 / 飞线 airline / 查看器只读模式）
- 宏 IDE（断点 / 单步 / Python 交互控制台 / 监视表达式）

实现策略：**数据模型层 + 命令模式**，无 GUI 框架依赖（PyQt/Tkinter），
便于 CI/CD 与 Web 后端复用。

本文件为 facade 层，从拆分的子模块聚合（R11 质量门禁：文件≤800行）：
- widgets.py: ObjectType + LayoutObject + 曲线求值 + 命令模式 + SnapEngine + AirlineRouter
- dialogs.py: MacroDebugger + MacroIDE + ViewerGuard
- interactive.py（本文件）: 重新导出全部公共 API，保持向后兼容

文献来源（R02 学术诚信，≥5 条）：
1. KLayout Scripting Manual https://www.klayout.org/doc-qt5/manual/scripting.html
2. Siemens L-Edit Photonics
   https://eda.sw.siemens.com/en-US/ic/ic-custom/photonic/l-edit-photonics/
3. Farin, G., "Curves and Surfaces for CAGD", 5th ed., Morgan Kaufmann 2002
   https://www.sciencedirect.com/book/9781558607378/curves-and-surfaces-for-cagd
4. De Casteljau 算法 https://en.wikipedia.org/wiki/De_Casteljau%27s_algorithm
5. Catmull & Rom 1974 https://en.wikipedia.org/wiki/Centripetal_Catmull%E2%80%93Rom_spline
6. Gamma et al., "Design Patterns", Addison-Wesley 1994（Command Pattern）
   https://en.wikipedia.org/wiki/Command_pattern
7. Python bdb — Debugger framework https://docs.python.org/3/library/bdb.html
8. KLayout Rubber-band / airline https://www.klayout.de/doc-qt5/manual/rubberband.html

*创新*：纯 Python 数据模型 + 命令模式 GUI 引擎。底层逻辑：
``LayoutObject`` 统一抽象（点/折线/多边形/贝塞尔/样条/圆弧/椭圆/端口），
编辑操作封装为 ``EditCommand`` 入栈，``CommandStack`` 实现 undo/redo
（Gamma 1994 命令模式）。``SnapEngine`` 多模态吸附（网格/顶点/中点/端点），
对标 L-Edit "Snap to Objects" 与 KLayout snap-to-grid/vertex。
``AirlineRouter`` 为未连接端口生成直线飞线，对标 KLayout "show airlines"。
``MacroIDE`` 基于 ``sys.settrace``（bdb 底层机制）+
``code.InteractiveConsole``，提供 KLayout Macro IDE 等价的脚本调试/
控制台/监视能力，零 GUI 依赖。
支持理论：MVC 分离（Gamma 1994）+ Python bdb 跟踪框架（PSF 文档）。

合规: R02 学术诚信 / R03 禁止 fall-back / R05 Bug 必修。
"""

from __future__ import annotations

# 从拆分子模块重新导出全部公共 API，保持向后兼容
# （polaris_gui.__init__ 与 tests/test_gui.py 均从 polaris_gui.interactive 导入）
from polaris_gui.widgets import (
    AirlineRouter,
    AirlineSegment,
    AddObjectCommand,
    CommandStack,
    InsertVertexCommand,
    LayoutObject,
    MoveObjectCommand,
    MoveVertexCommand,
    ObjectType,
    RemoveObjectCommand,
    RemoveVertexCommand,
    SnapEngine,
    SnapResult,
    evaluate_object,
)
from polaris_gui.dialogs import (
    MacroDebugger,
    MacroIDE,
    ViewerGuard,
)

__all__ = [
    # 数据模型
    "ObjectType",
    "LayoutObject",
    "evaluate_object",
    # 命令模式
    "AddObjectCommand",
    "RemoveObjectCommand",
    "MoveObjectCommand",
    "InsertVertexCommand",
    "RemoveVertexCommand",
    "MoveVertexCommand",
    "CommandStack",
    # 吸附引擎
    "SnapEngine",
    "SnapResult",
    # 飞线路由
    "AirlineRouter",
    "AirlineSegment",
    # 宏 IDE
    "MacroDebugger",
    "MacroIDE",
    # 查看器守卫
    "ViewerGuard",
]
