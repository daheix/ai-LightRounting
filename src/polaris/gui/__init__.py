"""GUI 子包：L-Edit 风格版图编辑器（R19）+ P0-3 交互功能。

提供版图编辑器主控（LayoutEditor），支持器件拖拽/旋转/删除、
布线结果实时可视化、DRC 错误高亮、撤销/重做、视图仿射变换，
以及 Web 预览 + KLayout 深度编辑双模式集成。

P0-3 交互功能（interactive.py）：曲线多边形编辑、对象交互、宏 IDE。

参考文献：
[1] Qt Group. Qt Graphics View Framework[EB/OL]. 2024. https://doc.qt.io/qt-6/graphicsview.html
[2] KLayout. KLayout Application API[EB/OL]. 2024. https://www.klayout.org/downloads/master/doc-qt5/programming/application_api.html
[3] Ousterhout J K. Magic: A VLSI layout system[C]//Design Automation Conference (DAC). 1984: 152-159. https://ece.umd.edu/~newrocmb/vlsi/magic_tut/tut2.pdf
[4] LayoutEditor. GDSII file format documentation[EB/OL]. 2024. https://www.layouteditor.org/layout/file-formats/gdsii
[5] gdsfactory. gdsfactory photonics training: Layout editor[EB/OL]. 2024. https://gdsfactory.github.io/gdsfactory-photonics-training/
[6] Rubin S M. Computer aids for VLSI design[M]. Addison-Wesley, 1987. https://www.rulabinsky.com/cavd/text/chapc.html
"""

from polaris.gui.layout_editor import (
    DeviceInstance,
    DRCHighlight,
    EditorConfig,
    LayoutEditor,
)
from polaris.gui.interactive import (
    AirlineRouter,
    AirlineSegment,
    CommandStack,
    LayoutObject,
    MacroDebugger,
    MacroIDE,
    ObjectType,
    SnapEngine,
    SnapResult,
    ViewerGuard,
    evaluate_object,
)

__all__ = [
    "AirlineRouter",
    "AirlineSegment",
    "CommandStack",
    "DRCHighlight",
    "DeviceInstance",
    "EditorConfig",
    "LayoutEditor",
    "LayoutObject",
    "MacroDebugger",
    "MacroIDE",
    "ObjectType",
    "SnapEngine",
    "SnapResult",
    "ViewerGuard",
    "evaluate_object",
]
