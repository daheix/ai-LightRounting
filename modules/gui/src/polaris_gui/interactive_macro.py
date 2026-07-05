"""GUI 交互 - 宏 IDE 模块（polaris-gui 子模块）。

从 ``interactive.py`` 拆分而来，包含 KLayout Macro IDE 等价的脚本调试/控制台/
监视能力:
- MacroDebugger: 基于 sys.settrace（bdb 底层机制），断点/单步
- MacroIDE: 集成 code.InteractiveConsole，Python 交互控制台 + 监视表达式
- ViewerGuard: 只读模式守卫

*创新*：纯 Python 实现，零 GUI 依赖。

文献来源（R02 学术诚信）:
1. Python bdb — Debugger framework https://docs.python.org/3/library/bdb.html
2. Python code — InteractiveConsole
   https://docs.python.org/3/library/code.html
3. KLayout Macro IDE https://www.klayout.org/doc-qt5/manual/macro_editor.html
4. Gamma et al., "Design Patterns", Addison-Wesley 1994
5. Siemens L-Edit Photonics
   https://eda.sw.siemens.com/en-US/ic/ic-custom/photonic/l-edit-photonics/

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU。
"""

from __future__ import annotations

import sys
from code import InteractiveConsole
from typing import Any

class _PauseSignal(Exception):
    """调试器暂停信号（控制流信号，非业务异常）。

    在 sys.settrace 回调中抛出以中断脚本执行，实现断点/单步暂停。
    捕获方应记录已暂停状态后正常返回。
    """


class MacroDebugger:
    """宏调试器：基于 ``sys.settrace`` 行级跟踪（bdb 底层机制）。

    文献：https://docs.python.org/3/library/bdb.html
    支持：断点（含条件断点）、单步（step/next/continue）、监视表达式、执行轨迹。
    """

    def __init__(self) -> None:
        self._breakpoints: dict[tuple[str, int], str | None] = {}
        self._watches: list[str] = []
        self._watch_values: dict[str, Any] = {}
        self._executed_lines: list[tuple[str, int]] = []
        self._paused_at: tuple[str, int] | None = None
        self._step_mode: str = "continue"

    def set_breakpoint(
        self, filename: str, line: int, cond: str | None = None
    ) -> None:
        """设置断点（``cond`` 为 None 表示无条件）。"""
        if line <= 0:
            raise ValueError(f"断点行号必须 >0，收到 {line}")
        if cond is not None and (not isinstance(cond, str) or not cond.strip()):
            raise ValueError(f"断点条件必须为非空字符串或 None，收到 {cond!r}")
        self._breakpoints[(filename, line)] = cond

    def clear_breakpoint(self, filename: str, line: int) -> None:
        if (filename, line) not in self._breakpoints:
            raise KeyError(f"断点 ({filename!r}, {line}) 不存在")
        del self._breakpoints[(filename, line)]

    def add_watch(self, expr: str) -> None:
        if not isinstance(expr, str) or not expr.strip():
            raise ValueError(f"监视表达式必须为非空字符串，收到 {expr!r}")
        self._watches.append(expr)

    def clear_watches(self) -> None:
        self._watches.clear()
        self._watch_values.clear()

    @property
    def paused_at(self) -> tuple[str, int] | None:
        return self._paused_at

    @property
    def watch_values(self) -> dict[str, Any]:
        return dict(self._watch_values)

    @property
    def executed_lines(self) -> list[tuple[str, int]]:
        return list(self._executed_lines)

    @property
    def breakpoints(self) -> dict[tuple[str, int], str | None]:
        return dict(self._breakpoints)

    def run(
        self, code_obj: Any, namespace: dict,
        step_mode: str = "continue",
    ) -> bool:
        """执行代码对象，命中断点或单步时暂停。True=暂停，False=运行到结束。"""
        if step_mode not in ("step", "next", "continue"):
            raise ValueError(f"未知 step_mode: {step_mode!r}")
        self._step_mode = step_mode
        self._executed_lines = []
        self._paused_at = None
        self._watch_values = {}
        old_trace = sys.gettrace()
        sys.settrace(self._make_trace())
        paused = False
        try:
            exec(code_obj, namespace)
        except _PauseSignal:
            # 设计的暂停信号：状态已记录到 _paused_at/watch_values
            paused = True
        finally:
            sys.settrace(old_trace)
        return paused

    def _make_trace(self):
        def trace(frame, event, _arg):
            if event == "call":
                # next 模式且已开始跟踪则不进入子帧
                if self._step_mode == "next" and self._executed_lines:
                    return None
                return trace
            if event != "line":
                return trace
            fn = frame.f_code.co_filename
            ln = frame.f_lineno
            self._executed_lines.append((fn, ln))
            if self._should_pause(fn, ln, frame):
                self._paused_at = (fn, ln)
                self._eval_watches(frame)
                raise _PauseSignal()
            return trace
        return trace

    def _should_pause(self, fn: str, ln: int, frame) -> bool:
        if (fn, ln) in self._breakpoints:
            bp_cond = self._breakpoints[(fn, ln)]
            if bp_cond:
                return bool(self._eval_condition(bp_cond, frame))
            return True
        return self._step_mode in ("step", "next")

    def _eval_condition(self, cond: str, frame) -> bool:
        try:
            return bool(eval(cond, frame.f_globals, frame.f_locals))
        except Exception as e:
            raise RuntimeError(
                f"断点条件 {cond!r} 求值失败: {type(e).__name__}: {e}") from e

    def _eval_watches(self, frame) -> None:
        self._watch_values = {}
        for expr in self._watches:
            try:
                self._watch_values[expr] = eval(
                    expr, frame.f_globals, frame.f_locals)
            except Exception as e:
                self._watch_values[expr] = (
                    f"<error: {type(e).__name__}: {e}>")


class MacroIDE:
    """宏 IDE（KLayout Macro IDE 风格，纯 Python）。

    集成控制台（``code.InteractiveConsole``）、调试器（:class:`MacroDebugger`）、
    脚本加载（编译后可重复调试运行）。文献：
    https://www.klayout.org/doc-qt5/manual/scripting.html
    """

    def __init__(self, namespace: dict | None = None) -> None:
        self._namespace: dict = namespace if namespace is not None else {
            "__name__": "__macro__", "__builtins__": __builtins__}
        self._console = InteractiveConsole(self._namespace)
        self._debugger = MacroDebugger()
        self._filename: str = "<macro>"
        self._code_obj: Any = None

    @property
    def namespace(self) -> dict:
        return self._namespace

    @property
    def debugger(self) -> MacroDebugger:
        return self._debugger

    def load_script(self, filename: str, source: str) -> None:
        """加载并编译宏脚本。"""
        if not isinstance(source, str) or not source.strip():
            raise ValueError("宏脚本源码必须为非空字符串")
        self._filename = filename
        self._code_obj = compile(source, filename, "exec")

    def console_eval(self, source: str) -> Any:
        """在交互控制台中求值表达式/语句。表达式返回结果，语句返回 None。"""
        if not isinstance(source, str) or not source.strip():
            raise ValueError("控制台输入必须为非空字符串")
        try:
            return eval(source, self._namespace)
        except SyntaxError:
            # 语句而非表达式：交由 InteractiveConsole 执行
            more = self._console.push(source)
            if more:
                raise SyntaxError(f"控制台输入不完整: {source!r}")
            return None

    def set_breakpoint(self, line: int, cond: str | None = None) -> None:
        if self._code_obj is None:
            raise RuntimeError("尚未加载宏脚本，无法设置断点")
        self._debugger.set_breakpoint(self._filename, line, cond)

    def clear_breakpoint(self, line: int) -> None:
        self._debugger.clear_breakpoint(self._filename, line)

    def add_watch(self, expr: str) -> None:
        self._debugger.add_watch(expr)

    def run(self, step_mode: str = "continue") -> bool:
        """执行宏脚本（按 step_mode 暂停策略）。True 表示暂停命中。"""
        if self._code_obj is None:
            raise RuntimeError("尚未加载宏脚本，无法运行")
        return self._debugger.run(
            self._code_obj, self._namespace, step_mode=step_mode)

    @property
    def watch_values(self) -> dict[str, Any]:
        return self._debugger.watch_values

    @property
    def paused_at(self) -> tuple[str, int] | None:
        return self._debugger.paused_at

    @property
    def executed_lines(self) -> list[tuple[str, int]]:
        return self._debugger.executed_lines


# === 6. ViewerGuard 查看器只读模式守卫（对标 L-Edit Viewer Mode） ===

class ViewerGuard:
    """查看器只读模式守卫（对标 L-Edit Viewer Mode）。

    viewer_mode=True 时所有编辑操作 raise PermissionError（R03 禁止 fall-back）。
    调用方组合各组件时通过 :meth:`require_editable` 守卫编辑入口。
    """

    def __init__(self, viewer_mode: bool = False) -> None:
        self._viewer_mode = bool(viewer_mode)

    @property
    def viewer_mode(self) -> bool:
        return self._viewer_mode

    def set_viewer_mode(self, enabled: bool) -> None:
        self._viewer_mode = bool(enabled)

    def require_editable(self) -> None:
        """检查可编辑性，viewer_mode=True 时 raise PermissionError。"""
        if self._viewer_mode:
            raise PermissionError("查看器模式下禁止编辑（只读）")


__all__ = ["MacroDebugger", "MacroIDE", "ViewerGuard"]
