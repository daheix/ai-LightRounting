"""GUI 子包：L-Edit 风格版图编辑器（R19）。

提供版图编辑器主控（LayoutEditor），支持器件拖拽/旋转/删除、
布线结果实时可视化、DRC 错误高亮、撤销/重做、视图仿射变换，
以及 Web 预览 + KLayout 深度编辑双模式集成。
"""

from polaris.gui.layout_editor import (
    DRCHighlight,
    DeviceInstance,
    EditorConfig,
    LayoutEditor,
)

__all__ = [
    "DRCHighlight",
    "DeviceInstance",
    "EditorConfig",
    "LayoutEditor",
]
