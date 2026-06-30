"""GUI 子包：L-Edit 风格版图编辑器（R19）+ P0-3 交互功能。

提供版图编辑器主控（LayoutEditor），支持器件拖拽/旋转/删除、
布线结果实时可视化、DRC 错误高亮、撤销/重做、视图仿射变换，
以及 Web 预览 + KLayout 深度编辑双模式集成。

P0-3 交互功能（interactive.py）：曲线多边形编辑、对象交互、宏 IDE。
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
