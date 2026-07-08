"""GUI 交互 - 命令模式（undo/redo）模块（polaris-gui 子模块）。

从 ``interactive.py`` 拆分而来，包含 Gamma 1994 命令模式实现:
- AddObjectCommand / RemoveObjectCommand / MoveObjectCommand
- InsertVertexCommand / RemoveVertexCommand / MoveVertexCommand
- CommandStack（undo/redo 栈）

无 GUI 框架依赖。

文献来源（R02 学术诚信）:
1. Gamma et al., "Design Patterns", Addison-Wesley 1994（Command Pattern）
   https://en.wikipedia.org/wiki/Command_pattern
2. KLayout Scripting https://www.klayout.org/doc-qt5/manual/scripting.html
3. Siemens L-Edit Photonics
   https://eda.sw.siemens.com/en-US/ic/ic-custom/photonic/l-edit-photonics/
4. Qt Undo Framework（命令栈对标） https://doc.qt.io/qt-6/qundostack.html
5. Python copy（深拷贝快照隔离） https://docs.python.org/3/library/copy.html
6. Gamma Design Patterns（GoF 经典）
   https://en.wikipedia.org/wiki/Design_Patterns

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU。
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .interactive_objects import LayoutObject, ObjectType, _require_object


@dataclass
class AddObjectCommand:
    """添加对象命令。

    使用深拷贝保存对象快照，避免外部修改导致撤销/重做副作用。
    来源: Gamma et al., "Design Patterns", Addison-Wesley 1994 (Command Pattern)
    URL: https://en.wikipedia.org/wiki/Command_pattern
    """

    obj: LayoutObject

    def do(self, scene: dict[int, LayoutObject]) -> None:
        if self.obj.obj_id in scene:
            raise KeyError(f"对象 ID {self.obj.obj_id} 已存在")
        scene[self.obj.obj_id] = copy.deepcopy(self.obj)

    def undo(self, scene: dict[int, LayoutObject]) -> None:
        if self.obj.obj_id not in scene:
            raise KeyError(f"对象 ID {self.obj.obj_id} 不存在，无法撤销")
        del scene[self.obj.obj_id]


@dataclass
class RemoveObjectCommand:
    """删除对象命令（do 时深拷贝快照当前对象以备撤销）。

    使用深拷贝保存对象快照，避免外部修改导致撤销/重做副作用。
    来源: Gamma et al., "Design Patterns", Addison-Wesley 1994 (Command Pattern)
    URL: https://en.wikipedia.org/wiki/Command_pattern
    深度拷贝参考: https://docs.python.org/3/library/copy.html
    """

    obj: LayoutObject

    def do(self, scene: dict[int, LayoutObject]) -> None:
        if self.obj.obj_id not in scene:
            raise KeyError(f"对象 ID {self.obj.obj_id} 不存在")
        self.obj = copy.deepcopy(scene[self.obj.obj_id])
        del scene[self.obj.obj_id]

    def undo(self, scene: dict[int, LayoutObject]) -> None:
        if self.obj.obj_id in scene:
            raise KeyError(f"对象 ID {self.obj.obj_id} 已存在，无法撤销")
        scene[self.obj.obj_id] = copy.deepcopy(self.obj)


@dataclass
class MoveObjectCommand:
    """平移对象命令（整体偏移 dx,dy；含 center 属性同步）。"""

    obj_id: int
    dx: float
    dy: float

    def _apply(self, scene: dict[int, LayoutObject], sign: float) -> None:
        obj = _require_object(scene, self.obj_id)
        sdx, sdy = sign * self.dx, sign * self.dy
        obj.points = [(p[0] + sdx, p[1] + sdy) for p in obj.points]
        if "center" in obj.attrs:
            cx, cy = obj.attrs["center"]
            obj.attrs["center"] = (cx + sdx, cy + sdy)

    def do(self, scene: dict[int, LayoutObject]) -> None:
        self._apply(scene, 1.0)

    def undo(self, scene: dict[int, LayoutObject]) -> None:
        self._apply(scene, -1.0)


@dataclass
class InsertVertexCommand:
    """在折线/多边形的指定索引处插入顶点。"""

    obj_id: int
    index: int
    vertex: tuple[float, float]

    def do(self, scene: dict[int, LayoutObject]) -> None:
        obj = _require_object(scene, self.obj_id)
        if obj.obj_type not in (ObjectType.POLYLINE.value,
                                ObjectType.POLYGON.value):
            raise ValueError(f"仅折线/多边形支持顶点编辑，收到 {obj.obj_type!r}")
        if not 0 <= self.index <= len(obj.points):
            raise IndexError(f"插入索引越界: {self.index} (len={len(obj.points)})")
        obj.points.insert(self.index, self.vertex)

    def undo(self, scene: dict[int, LayoutObject]) -> None:
        obj = _require_object(scene, self.obj_id)
        if len(obj.points) <= self.index or obj.points[self.index] != self.vertex:
            raise RuntimeError("撤销插入顶点失败：状态不一致")
        obj.points.pop(self.index)


@dataclass
class RemoveVertexCommand:
    """删除折线/多边形指定索引顶点。"""

    obj_id: int
    index: int
    vertex: tuple[float, float]

    def do(self, scene: dict[int, LayoutObject]) -> None:
        obj = _require_object(scene, self.obj_id)
        if obj.obj_type not in (ObjectType.POLYLINE.value,
                                ObjectType.POLYGON.value):
            raise ValueError(f"仅折线/多边形支持顶点编辑，收到 {obj.obj_type!r}")
        if not 0 <= self.index < len(obj.points):
            raise IndexError(f"删除索引越界: {self.index} (len={len(obj.points)})")
        if len(obj.points) <= 2:
            raise ValueError(f"对象至少保留 2 个顶点，当前 {len(obj.points)}")
        self.vertex = obj.points[self.index]
        obj.points.pop(self.index)

    def undo(self, scene: dict[int, LayoutObject]) -> None:
        obj = _require_object(scene, self.obj_id)
        if not 0 <= self.index <= len(obj.points):
            raise IndexError(f"恢复索引越界: {self.index}")
        obj.points.insert(self.index, self.vertex)


@dataclass
class MoveVertexCommand:
    """移动折线/多边形指定顶点到新坐标。"""

    obj_id: int
    index: int
    old_vertex: tuple[float, float]
    new_vertex: tuple[float, float]

    def do(self, scene: dict[int, LayoutObject]) -> None:
        obj = _require_object(scene, self.obj_id)
        if not 0 <= self.index < len(obj.points):
            raise IndexError(f"顶点索引越界: {self.index}")
        self.old_vertex = obj.points[self.index]
        obj.points[self.index] = self.new_vertex

    def undo(self, scene: dict[int, LayoutObject]) -> None:
        obj = _require_object(scene, self.obj_id)
        if not 0 <= self.index < len(obj.points):
            raise IndexError(f"顶点索引越界: {self.index}")
        obj.points[self.index] = self.old_vertex


class CommandStack:
    """命令栈（undo/redo，Gamma 1994 命令模式）。

    ``execute`` 执行命令并压入 undo 栈；``undo`` 弹出执行反向；
    ``redo`` 弹出重做。新命令清空 redo 栈。
    """

    def __init__(self, max_steps: int = 100) -> None:
        if max_steps <= 0:
            raise ValueError(f"max_steps 必须 >0，收到 {max_steps}")
        self._undo: list[Any] = []
        self._redo: list[Any] = []
        self._max_steps = max_steps

    def execute(self, cmd: Any, target: dict[int, LayoutObject]) -> None:
        cmd.do(target)
        self._undo.append(cmd)
        self._redo.clear()
        overflow = len(self._undo) - self._max_steps
        if overflow > 0:
            del self._undo[:overflow]

    def undo(self, target: dict[int, LayoutObject]) -> bool:
        if not self._undo:
            return False
        cmd = self._undo.pop()
        cmd.undo(target)
        self._redo.append(cmd)
        return True

    def redo(self, target: dict[int, LayoutObject]) -> bool:
        if not self._redo:
            return False
        cmd = self._redo.pop()
        cmd.do(target)
        self._undo.append(cmd)
        return True

    @property
    def undo_depth(self) -> int:
        return len(self._undo)

    @property
    def redo_depth(self) -> int:
        return len(self._redo)


__all__ = [
    "AddObjectCommand",
    "RemoveObjectCommand",
    "MoveObjectCommand",
    "InsertVertexCommand",
    "RemoveVertexCommand",
    "MoveVertexCommand",
    "CommandStack",
]
