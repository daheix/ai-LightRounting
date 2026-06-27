"""C05-DEVS：Zeigler 经典 DEVS 离散事件系统规范求解器。

实现 DEVS（Discrete Event System Specification）经典形式：
- 原子模型 AtomicDEVS：状态 + 时间推进 ta + 内/外转移 + 输出 λ
- 耦合模型 CoupledDEVS：组件网络 + 耦合关系 + 选择函数
- 仿真器 Simulator / Coordinator：事件调度 + 时间推进

核心算法（Zeigler 经典 DEVS 仿真循环）：
1. 计算下一事件时间 t_N = t_L + ta(s)
2. 等待输入或到达 t_N
3. 若到达 t_N：执行 λ 输出 → 执行 δ_int 内部转移
4. 若收到输入：执行 δ_ext 外部转移，更新 t_L

文献来源（≥5）：
1. Zeigler BP, Praehofer H, Kim TG. "Theory of Modeling and Simulation."
   2nd ed., Academic Press (2000). ISBN 0127784551.
   https://www.elsevier.com/books/theory-of-modeling-and-simulation/zeigler/978-0-12-778455-7
2. Zeigler BP. "Theory of Modeling and Simulation." 1st ed., Wiley (1976).
   https://onlinelibrary.wiley.com/doi/book/10.1002/9781118632123
3. Chow AC, Zeigler BP. "Parallel DEVS: a parallel, hierarchical, modular
   modeling formalism." WSC '94, 716-723 (1994).
   https://doi.org/10.1109/WSC.1994.717431
4. Van Tendeloo Y, Vangheluwe H. "An evaluation of DEVS simulation tools."
   SIMULATION 93(2), 103-121 (2017).
   https://doi.org/10.1177/0037549716676811
5. Wainer GA. "Discrete-Event Modeling and Simulation: A Practitioner's
   Approach." CRC Press (2009). ISBN 9781420053364.
   https://www.crcpress.com/Discrete-Event-Modeling-and-Simulation-A-Practitioners-Approach/Wainer/p/book/9781420053364
6. Nutaro JJ. "Building Software for Simulation." Wiley (2010).
   https://www.wiley.com/en-us/Building+Software+for+Simulation%3A+Theory+and+Algorithms%2C+with+Applications+in+C%2B%2B%2C+Java%2C+Python%2C+and+SIMULINK-p-9780470482315

规则依据：R03 无 fall-back / 纯 numpy/scipy / 中文注释
"""

from __future__ import annotations

import heapq
from dataclasses import dataclass
from typing import Any

# 无穷大时间（表示被动状态）
INFINITY = float("inf")


@dataclass
class DEVSMessage:
    """DEVS 消息（端口 + 值）。

    Attributes:
        port: 端口名。
        value: 消息值。
    """
    port: str
    value: Any


class AtomicDEVS:
    """经典 DEVS 原子模型基类。

    原子模型由以下要素构成：
    - X: 输入端口集合
    - Y: 输出端口集合
    - S: 状态集合
    - ta(s): 时间推进函数 → R+ ∪ {∞}
    - δ_ext(s, e, x): 外部转移函数
    - δ_int(s): 内部转移函数
    - λ(s): 输出函数 → Y

    使用方法：
        子类继承并实现以下方法：
        - __init__: 定义输入/输出端口 + 初始状态
        - time_advance: ta(s)
        - external_transition: δ_ext
        - internal_transition: δ_int
        - output_function: λ
    """

    def __init__(self, name: str):
        self.name = name
        self.input_ports: list[str] = []
        self.output_ports: list[str] = []
        self.state: Any = None
        self._elapsed: float = 0.0
        self._last_time: float = 0.0

    def add_input_port(self, port: str) -> None:
        """添加输入端口。"""
        if port not in self.input_ports:
            self.input_ports.append(port)

    def add_output_port(self, port: str) -> None:
        """添加输出端口。"""
        if port not in self.output_ports:
            self.output_ports.append(port)

    def time_advance(self, state: Any) -> float:
        """时间推进函数 ta(s) → 下次内部事件的时间增量。

        返回 INFINITY 表示被动状态（无内部事件）。
        子类必须重写此方法。
        """
        raise NotImplementedError("子类必须实现 time_advance")

    def external_transition(
        self, state: Any, elapsed: float, messages: list[DEVSMessage]
    ) -> Any:
        """外部转移函数 δ_ext(s, e, x) → s'。

        Args:
            state: 当前状态 s。
            elapsed: 自上次转移以来经过的时间 e。
            messages: 输入消息列表 x。

        Returns:
            新状态 s'。
        """
        raise NotImplementedError("子类必须实现 external_transition")

    def internal_transition(self, state: Any) -> Any:
        """内部转移函数 δ_int(s) → s'。

        子类必须重写此方法。
        """
        raise NotImplementedError("子类必须实现 internal_transition")

    def output_function(self, state: Any) -> list[DEVSMessage]:
        """输出函数 λ(s) → y（输出消息列表）。

        子类必须重写此方法。
        """
        raise NotImplementedError("子类必须实现 output_function")

    def _time_of_next_event(self, current_time: float) -> float:
        """计算下一事件的绝对时间。"""
        ta = self.time_advance(self.state)
        if ta == INFINITY:
            return INFINITY
        return current_time + ta - self._elapsed


class CoupledDEVS:
    """经典 DEVS 耦合模型（网络模型）。

    耦合模型由以下要素构成：
    - D: 组件模型集合（原子或耦合）
    - EIC: 外部输入耦合（模型输入 → 组件输入）
    - EOC: 外部输出耦合（组件输出 → 模型输出）
    - IC: 内部耦合（组件输出 → 组件输入）
    - select: 冲突选择函数（多个组件同时触发时选谁先）

    Attributes:
        name: 模型名。
        components: 子组件字典 {name: model}。
    """

    def __init__(self, name: str):
        self.name = name
        self.input_ports: list[str] = []
        self.output_ports: list[str] = []
        self.components: dict[str, AtomicDEVS | CoupledDEVS] = {}
        # 耦合关系: List[(src_comp, src_port, dst_comp, dst_port)]
        self._eic: list[tuple[str, str, str, str]] = []  # 外部输入耦合
        self._eoc: list[tuple[str, str, str, str]] = []  # 外部输出耦合
        self._ic: list[tuple[str, str, str, str]] = []   # 内部耦合

    def add_input_port(self, port: str) -> None:
        if port not in self.input_ports:
            self.input_ports.append(port)

    def add_output_port(self, port: str) -> None:
        if port not in self.output_ports:
            self.output_ports.append(port)

    def add_component(self, component: AtomicDEVS | CoupledDEVS) -> None:
        """添加子组件。"""
        if component.name in self.components:
            raise ValueError(f"组件 {component.name} 已存在")
        self.components[component.name] = component

    def add_eic(self, src_port: str, dst_comp: str, dst_port: str) -> None:
        """添加外部输入耦合（本模型输入 → 子组件输入）。"""
        if src_port not in self.input_ports:
            raise ValueError(f"输入端口 {src_port} 不存在")
        if dst_comp not in self.components:
            raise ValueError(f"组件 {dst_comp} 不存在")
        self._eic.append((src_port, dst_comp, dst_port))

    def add_eoc(self, src_comp: str, src_port: str, dst_port: str) -> None:
        """添加外部输出耦合（子组件输出 → 本模型输出）。"""
        if src_comp not in self.components:
            raise ValueError(f"组件 {src_comp} 不存在")
        if dst_port not in self.output_ports:
            raise ValueError(f"输出端口 {dst_port} 不存在")
        self._eoc.append((src_comp, src_port, dst_port))

    def add_ic(
        self, src_comp: str, src_port: str, dst_comp: str, dst_port: str
    ) -> None:
        """添加内部耦合（子组件输出 → 子组件输入）。"""
        if src_comp not in self.components or dst_comp not in self.components:
            raise ValueError(f"组件不存在: {src_comp} 或 {dst_comp}")
        self._ic.append((src_comp, src_port, dst_comp, dst_port))

    def propagate_input(
        self, messages: list[DEVSMessage]
    ) -> dict[str, list[DEVSMessage]]:
        """将外部输入通过 EIC 传播到子组件。

        Returns:
            {组件名: [消息列表]} 字典。
        """
        result: dict[str, list[DEVSMessage]] = {}
        for msg in messages:
            for src_port, dst_comp, dst_port in self._eic:
                if msg.port == src_port:
                    if dst_comp not in result:
                        result[dst_comp] = []
                    result[dst_comp].append(DEVSMessage(port=dst_port, value=msg.value))
        return result

    def propagate_output(
        self, comp_outputs: dict[str, list[DEVSMessage]]
    ) -> list[DEVSMessage]:
        """将子组件输出通过 EOC 传播为耦合模型输出。"""
        outputs: list[DEVSMessage] = []
        for comp_name, msgs in comp_outputs.items():
            for msg in msgs:
                for src_comp, src_port, dst_port in self._eoc:
                    if comp_name == src_comp and msg.port == src_port:
                        outputs.append(DEVSMessage(port=dst_port, value=msg.value))
        return outputs

    def propagate_internal(
        self, comp_outputs: dict[str, list[DEVSMessage]]
    ) -> dict[str, list[DEVSMessage]]:
        """通过 IC 将子组件输出传播为其他子组件的输入。"""
        result: dict[str, list[DEVSMessage]] = {}
        for comp_name, msgs in comp_outputs.items():
            for msg in msgs:
                for src_comp, src_port, dst_comp, dst_port in self._ic:
                    if comp_name == src_comp and msg.port == src_port:
                        if dst_comp not in result:
                            result[dst_comp] = []
                        result[dst_comp].append(
                            DEVSMessage(port=dst_port, value=msg.value)
                        )
        return result


class Simulator:
    """DEVS 原子模型仿真器。

    维护原子模型的时间推进与事件调度。
    """

    def __init__(self, model: AtomicDEVS, start_time: float = 0.0):
        self.model = model
        self._current_time = start_time
        self._next_time = self._compute_next_time()

    def _compute_next_time(self) -> float:
        ta = self.model.time_advance(self.model.state)
        if ta == INFINITY:
            return INFINITY
        return self._current_time + ta - self.model._elapsed

    @property
    def next_event_time(self) -> float:
        return self._next_time

    @property
    def current_time(self) -> float:
        return self._current_time

    def inject_input(
        self, time: float, messages: list[DEVSMessage]
    ) -> None:
        """注入外部输入并执行外部转移。"""
        if time < self._current_time:
            raise ValueError(f"时间回退: {time} < {self._current_time}")
        elapsed = time - self._current_time + self.model._elapsed
        # 检查时间合法性（elapsed ≤ ta）
        ta = self.model.time_advance(self.model.state)
        if elapsed > ta + 1e-12:
            raise ValueError(
                f"外部转移时间越界: elapsed={elapsed} > ta={ta}"
            )
        # 执行外部转移
        self.model.state = self.model.external_transition(
            self.model.state, elapsed, messages
        )
        self._current_time = time
        self.model._elapsed = 0.0
        self._next_time = self._compute_next_time()

    def run_internal(self) -> list[DEVSMessage]:
        """执行内部转移并返回输出。"""
        if self._next_time == INFINITY:
            raise RuntimeError("无内部事件可执行（被动状态）")
        # 推进到下一事件时间
        self._current_time = self._next_time
        self.model._elapsed = self.model.time_advance(self.model.state)
        # 输出
        outputs = self.model.output_function(self.model.state)
        # 内部转移
        self.model.state = self.model.internal_transition(self.model.state)
        self.model._elapsed = 0.0
        self._next_time = self._compute_next_time()
        return outputs


class Coordinator:
    """DEVS 耦合模型协调器。

    管理多个子仿真器/协调器，按时间优先调度事件。
    使用最小堆实现事件队列。
    """

    def __init__(
        self,
        coupled_model: CoupledDEVS,
        start_time: float = 0.0,
    ):
        self.model = coupled_model
        self._current_time = start_time
        self._children: dict[str, Simulator | Coordinator] = {}
        self._event_heap: list[tuple[float, str]] = []  # (time, comp_name) 最小堆

        # 为每个子组件创建仿真器/协调器
        for name, comp in coupled_model.components.items():
            if isinstance(comp, AtomicDEVS):
                sim = Simulator(comp, start_time)
                self._children[name] = sim
            elif isinstance(comp, CoupledDEVS):
                coord = Coordinator(comp, start_time)
                self._children[name] = coord
            else:
                raise TypeError(f"未知组件类型: {type(comp)}")
            # 初始化事件堆
            t_next = self._children[name].next_event_time
            if t_next < INFINITY:
                heapq.heappush(self._event_heap, (t_next, name))

    @property
    def next_event_time(self) -> float:
        """最近的下一事件时间。"""
        if not self._event_heap:
            return INFINITY
        return self._event_heap[0][0]

    @property
    def current_time(self) -> float:
        return self._current_time

    def _update_child_time(self, name: str) -> None:
        """更新子组件的下一事件时间（重新入堆）。"""
        child = self._children[name]
        t_next = child.next_event_time
        if t_next < INFINITY:
            heapq.heappush(self._event_heap, (t_next, name))

    def _imminent_components(self, time: float) -> list[str]:
        """获取所有在 time 时刻触发的组件（时间相等的）。"""
        imminent: list[str] = []
        temp: list[tuple[float, str]] = []
        while self._event_heap and abs(self._event_heap[0][0] - time) < 1e-12:
            t, name = heapq.heappop(self._event_heap)
            imminent.append(name)
            temp.append((t, name))
        # 注意：这些组件执行完内部转移后需要重新入堆
        return imminent

    def inject_input(
        self, time: float, messages: list[DEVSMessage]
    ) -> None:
        """注入外部输入并传播。"""
        if time < self._current_time:
            raise ValueError(f"时间回退: {time} < {self._current_time}")
        # 通过 EIC 传播到子组件
        comp_inputs = self.model.propagate_input(messages)
        for comp_name, msgs in comp_inputs.items():
            child = self._children[comp_name]
            child.inject_input(time, msgs)
            # 更新该子组件的事件时间
            self._update_child_time(comp_name)
        self._current_time = time

    def step(self) -> tuple[float, list[DEVSMessage]]:
        """执行一步仿真（到下一事件时间）。

        Returns:
            (event_time, output_messages)。
        """
        if not self._event_heap:
            return (INFINITY, [])

        t_next = self._event_heap[0][0]
        self._current_time = t_next

        # 找到所有即将触发的组件
        imminent = self._imminent_components(t_next)

        # 1. 执行所有即将触发组件的内部转移，收集输出
        comp_outputs: dict[str, list[DEVSMessage]] = {}
        for name in imminent:
            child = self._children[name]
            outputs = child.run_internal()
            if outputs:
                comp_outputs[name] = outputs
            # 重新入堆
            self._update_child_time(name)

        # 2. 通过 IC 传播内部输出，产生新的外部输入
        if comp_outputs:
            internal_inputs = self.model.propagate_internal(comp_outputs)
            for comp_name, msgs in internal_inputs.items():
                child = self._children[comp_name]
                child.inject_input(t_next, msgs)
                self._update_child_time(comp_name)

        # 3. 通过 EOC 传播到耦合模型输出
        all_outputs = self.model.propagate_output(comp_outputs)

        return (t_next, all_outputs)

    def simulate(self, end_time: float) -> list[tuple[float, list[DEVSMessage]]]:
        """仿真到 end_time，返回所有事件记录。

        Returns:
            [(time, [messages]), ...] 按时间排序的事件列表。
        """
        events: list[tuple[float, list[DEVSMessage]]] = []
        while self.next_event_time <= end_time + 1e-12:
            t, outputs = self.step()
            if outputs:
                events.append((t, outputs))
            else:
                events.append((t, []))
        return events


# ============================================================
# 常用原子模型示例
# ============================================================

class Generator(AtomicDEVS):
    """事件生成器：按固定周期产生输出。

    状态: {"count": int, "period": float}
    输出: "out" 端口，值为当前计数。
    """

    def __init__(self, name: str, period: float):
        super().__init__(name)
        self.add_output_port("out")
        self.state = {"count": 0, "period": period}

    def time_advance(self, state: dict) -> float:
        return state["period"]

    def external_transition(
        self, state: dict, elapsed: float, messages: list
    ) -> dict:
        # 生成器通常不接收外部输入
        return state

    def internal_transition(self, state: dict) -> dict:
        return {"count": state["count"] + 1, "period": state["period"]}

    def output_function(self, state: dict) -> list:
        return [DEVSMessage(port="out", value=state["count"])]


class Queue(AtomicDEVS):
    """FIFO 队列模型。

    状态: {"items": list, "processing_time": float, "busy": bool}
    输入: "in" 端口 → 入队；"done" 端口 → 处理完成
    输出: "out" 端口 → 取出的项目
    """

    def __init__(self, name: str, processing_time: float = 1.0):
        super().__init__(name)
        self.add_input_port("in")
        self.add_input_port("done")
        self.add_output_port("out")
        self.state = {
            "items": [],
            "processing_time": processing_time,
            "busy": False,
        }

    def time_advance(self, state: dict) -> float:
        if state["busy"] and state["items"]:
            return state["processing_time"]
        return INFINITY

    def external_transition(
        self, state: dict, elapsed: float, messages: list
    ) -> dict:
        new_items = list(state["items"])
        busy = state["busy"]
        for msg in messages:
            if msg.port == "in":
                new_items.append(msg.value)
            elif msg.port == "done":
                # 处理完成，弹出队首
                if new_items and busy:
                    new_items.pop(0)
                    busy = False
        # 如果不忙且有项目，开始处理
        if not busy and new_items:
            busy = True
        return {
            "items": new_items,
            "processing_time": state["processing_time"],
            "busy": busy,
        }

    def internal_transition(self, state: dict) -> dict:
        # 处理完成后变为不忙
        return {
            "items": state["items"],
            "processing_time": state["processing_time"],
            "busy": False,
        }

    def output_function(self, state: dict) -> list:
        if state["items"]:
            return [DEVSMessage(port="out", value=state["items"][0])]
        return []


class Accumulator(AtomicDEVS):
    """累加器模型：被动接收输入并累加。

    状态: {"total": float, "count": int}
    输入: "in" 端口 → 累加值
    输出: 无（被动模型，ta = ∞）
    """

    def __init__(self, name: str):
        super().__init__(name)
        self.add_input_port("in")
        self.state = {"total": 0.0, "count": 0}

    def time_advance(self, state: dict) -> float:
        return INFINITY

    def external_transition(
        self, state: dict, elapsed: float, messages: list
    ) -> dict:
        total = state["total"]
        count = state["count"]
        for msg in messages:
            if msg.port == "in":
                total += float(msg.value)
                count += 1
        return {"total": total, "count": count}

    def internal_transition(self, state: dict) -> dict:
        return state

    def output_function(self, state: dict) -> list:
        return []
