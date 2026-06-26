"""C05-DEVS 验收测试（Zeigler 经典 DEVS 离散事件系统）。

验收标准：
- M1: 经典 DEVS 原子模型时间推进正确
- M2: 耦合模型消息传递正确
- M3: 仿真器事件调度正确

文献来源（≥5）：
1. Zeigler BP, Praehofer H, Kim TG. "Theory of Modeling and Simulation."
   2nd ed., Academic Press (2000). ISBN 0127784551.
   https://www.elsevier.com/books/theory-of-modeling-and-simulation/zeigler/978-0-12-778455-7
2. Zeigler BP. "Theory of Modeling and Simulation." 1st ed., Wiley (1976).
3. Chow AC, Zeigler BP. "Parallel DEVS: a parallel, hierarchical, modular
   modeling formalism." WSC '94, 716-723 (1994).
   https://doi.org/10.1109/WSC.1994.717431
4. Van Tendeloo Y, Vangheluwe H. "An evaluation of DEVS simulation tools."
   SIMULATION 93(2), 103-121 (2017).
   https://doi.org/10.1177/0037549716676811
5. Wainer GA. "Discrete-Event Modeling and Simulation: A Practitioner's
   Approach." CRC Press (2009).
6. Nutaro JJ. "Building Software for Simulation." Wiley (2010).

规则依据：R03 无 fall-back / 纯 numpy/scipy / 中文注释
"""

from __future__ import annotations

import pytest

from polaris.sim.devs import (
    INFINITY,
    DEVSMessage,
    AtomicDEVS,
    CoupledDEVS,
    Simulator,
    Coordinator,
    Generator,
    Queue,
    Accumulator,
)


# ============================================================
# M1: 经典 DEVS 原子模型时间推进正确
# ============================================================

class TestM1AtomicTimeAdvance:
    """M1: 原子模型时间推进正确性验证。"""

    def test_generator_period(self):
        """生成器模型：时间推进 = period。"""
        gen = Generator("gen", period=2.5)
        ta = gen.time_advance(gen.state)
        assert ta == 2.5

    def test_passive_model_infinity_ta(self):
        """被动模型（累加器）：ta = ∞。"""
        acc = Accumulator("acc")
        ta = acc.time_advance(acc.state)
        assert ta == INFINITY

    def test_simulator_initial_next_time(self):
        """仿真器初始下一事件时间 = start_time + ta。"""
        gen = Generator("gen", period=3.0)
        sim = Simulator(gen, start_time=0.0)
        assert sim.next_event_time == pytest.approx(3.0)

    def test_simulator_run_internal_advances_time(self):
        """执行内部转移后，时间推进到下一事件。"""
        gen = Generator("gen", period=2.0)
        sim = Simulator(gen, start_time=0.0)

        outputs = sim.run_internal()

        assert sim.current_time == pytest.approx(2.0)
        assert sim.next_event_time == pytest.approx(4.0)
        assert len(outputs) == 1
        assert outputs[0].port == "out"
        assert outputs[0].value == 0

    def test_simulator_multiple_steps(self):
        """多步执行：时间累加正确。"""
        gen = Generator("gen", period=1.0)
        sim = Simulator(gen, start_time=0.0)

        # 第 1 步
        sim.run_internal()
        assert sim.current_time == pytest.approx(1.0)
        # 第 2 步
        sim.run_internal()
        assert sim.current_time == pytest.approx(2.0)
        # 第 3 步
        sim.run_internal()
        assert sim.current_time == pytest.approx(3.0)

    def test_external_transition_resets_elapsed(self):
        """外部转移后，elapsed 重置为 0，下一事件时间重新计算。"""
        gen = Generator("gen", period=10.0)
        sim = Simulator(gen, start_time=0.0)

        # 在 t=3 注入外部输入
        sim.inject_input(3.0, [DEVSMessage(port="in", value=42)])

        assert sim.current_time == pytest.approx(3.0)
        # 生成器外部转移不改变状态，但 elapsed 重置
        # 下一事件时间 = 3.0 + period = 13.0
        assert sim.next_event_time == pytest.approx(13.0)

    def test_accumulator_external_transition(self):
        """累加器外部转移：累加值正确。"""
        acc = Accumulator("acc")
        sim = Simulator(acc, start_time=0.0)

        sim.inject_input(1.0, [DEVSMessage(port="in", value=5.0)])
        assert acc.state["total"] == pytest.approx(5.0)
        assert acc.state["count"] == 1

        sim.inject_input(2.0, [DEVSMessage(port="in", value=3.0)])
        assert acc.state["total"] == pytest.approx(8.0)
        assert acc.state["count"] == 2

    def test_passive_model_never_internal(self):
        """被动模型不能执行内部转移（raise）。"""
        acc = Accumulator("acc")
        sim = Simulator(acc, start_time=0.0)

        with pytest.raises(RuntimeError, match="无内部事件"):
            sim.run_internal()

    def test_time_reversal_raises(self):
        """时间回退（注入过去的输入）raise。"""
        gen = Generator("gen", period=1.0)
        sim = Simulator(gen, start_time=5.0)

        with pytest.raises(ValueError, match="时间回退"):
            sim.inject_input(3.0, [DEVSMessage(port="in", value=0)])


# ============================================================
# M2: 耦合模型消息传递正确
# ============================================================

class TestM2CoupledMessagePassing:
    """M2: 耦合模型消息传递正确性验证。"""

    def test_eic_propagation(self):
        """外部输入耦合（EIC）：输入正确路由到子组件。"""
        coupled = CoupledDEVS("coupled")
        coupled.add_input_port("in")
        acc = Accumulator("acc")
        coupled.add_component(acc)
        coupled.add_eic("in", "acc", "in")

        msgs = [DEVSMessage(port="in", value=10.0)]
        result = coupled.propagate_input(msgs)

        assert "acc" in result
        assert len(result["acc"]) == 1
        assert result["acc"][0].port == "in"
        assert result["acc"][0].value == 10.0

    def test_eoc_propagation(self):
        """外部输出耦合（EOC）：子组件输出路由到耦合输出。"""
        coupled = CoupledDEVS("coupled")
        coupled.add_output_port("out")
        gen = Generator("gen", period=1.0)
        coupled.add_component(gen)
        coupled.add_eoc("gen", "out", "out")

        comp_outputs = {"gen": [DEVSMessage(port="out", value=42)]}
        outputs = coupled.propagate_output(comp_outputs)

        assert len(outputs) == 1
        assert outputs[0].port == "out"
        assert outputs[0].value == 42

    def test_ic_propagation(self):
        """内部耦合（IC）：一个组件的输出成为另一个的输入。"""
        coupled = CoupledDEVS("coupled")
        gen = Generator("gen", period=1.0)
        acc = Accumulator("acc")
        coupled.add_component(gen)
        coupled.add_component(acc)
        coupled.add_ic("gen", "out", "acc", "in")

        comp_outputs = {"gen": [DEVSMessage(port="out", value=7.0)]}
        internal_inputs = coupled.propagate_internal(comp_outputs)

        assert "acc" in internal_inputs
        assert len(internal_inputs["acc"]) == 1
        assert internal_inputs["acc"][0].port == "in"
        assert internal_inputs["acc"][0].value == 7.0

    def test_generator_accumulator_coupled(self):
        """生成器 → 累加器 耦合仿真：累加值正确。"""
        coupled = CoupledDEVS("sys")
        gen = Generator("gen", period=1.0)
        acc = Accumulator("acc")
        coupled.add_component(gen)
        coupled.add_component(acc)
        coupled.add_ic("gen", "out", "acc", "in")

        coord = Coordinator(coupled, start_time=0.0)
        events = coord.simulate(end_time=4.5)

        # 应有 4 个事件（t=1,2,3,4）
        assert len(events) >= 4
        # 累加器最终 total = 0 + 1 + 2 + 3 = 6（生成器 count 从 0 开始）
        assert acc.state["total"] == pytest.approx(6.0)
        assert acc.state["count"] == 4

    def test_coupled_add_duplicate_component_raises(self):
        """添加重名组件 raise。"""
        coupled = CoupledDEVS("sys")
        gen1 = Generator("gen", period=1.0)
        gen2 = Generator("gen", period=2.0)
        coupled.add_component(gen1)
        with pytest.raises(ValueError, match="已存在"):
            coupled.add_component(gen2)

    def test_coupled_eic_invalid_port_raises(self):
        """EIC 引用不存在的端口 raise。"""
        coupled = CoupledDEVS("sys")
        acc = Accumulator("acc")
        coupled.add_component(acc)
        with pytest.raises(ValueError, match="输入端口"):
            coupled.add_eic("nonexistent", "acc", "in")


# ============================================================
# M3: 仿真器事件调度正确
# ============================================================

class TestM3EventScheduling:
    """M3: 仿真器事件调度正确性验证。"""

    def test_coordinator_next_event_time(self):
        """协调器下一事件时间 = 所有子组件中最早的。"""
        coupled = CoupledDEVS("sys")
        gen_fast = Generator("fast", period=1.0)
        gen_slow = Generator("slow", period=5.0)
        coupled.add_component(gen_fast)
        coupled.add_component(gen_slow)

        coord = Coordinator(coupled, start_time=0.0)
        assert coord.next_event_time == pytest.approx(1.0)

    def test_coordinator_step_order(self):
        """多步仿真：事件按时间顺序发生。"""
        coupled = CoupledDEVS("sys")
        gen = Generator("gen", period=1.0)
        coupled.add_component(gen)

        coord = Coordinator(coupled, start_time=0.0)
        times = []
        for _ in range(5):
            t, _ = coord.step()
            times.append(t)

        # 时间严格递增
        for i in range(1, len(times)):
            assert times[i] > times[i - 1]
        # 每步间隔 = period
        for i in range(len(times)):
            assert times[i] == pytest.approx((i + 1) * 1.0)

    def test_simulate_end_time(self):
        """simulate(end_time)：所有事件时间 ≤ end_time。"""
        coupled = CoupledDEVS("sys")
        gen = Generator("gen", period=0.5)
        coupled.add_component(gen)

        coord = Coordinator(coupled, start_time=0.0)
        events = coord.simulate(end_time=3.0)

        assert len(events) == 6  # t=0.5,1.0,1.5,2.0,2.5,3.0
        for t, _ in events:
            assert t <= 3.0 + 1e-12

    def test_simulate_no_events_if_passive(self):
        """全被动系统：无事件。"""
        coupled = CoupledDEVS("sys")
        acc = Accumulator("acc")
        coupled.add_component(acc)

        coord = Coordinator(coupled, start_time=0.0)
        events = coord.simulate(end_time=10.0)

        assert len(events) == 0
        assert coord.next_event_time == INFINITY

    def test_concurrent_events(self):
        """并发事件：两个组件同时触发，都执行。"""
        coupled = CoupledDEVS("sys")
        gen1 = Generator("gen1", period=2.0)
        gen2 = Generator("gen2", period=2.0)
        acc1 = Accumulator("acc1")
        acc2 = Accumulator("acc2")
        coupled.add_component(gen1)
        coupled.add_component(gen2)
        coupled.add_component(acc1)
        coupled.add_component(acc2)
        coupled.add_ic("gen1", "out", "acc1", "in")
        coupled.add_ic("gen2", "out", "acc2", "in")

        coord = Coordinator(coupled, start_time=0.0)
        coord.step()  # t=2.0，两个生成器同时触发

        assert acc1.state["count"] == 1
        assert acc2.state["count"] == 1
        assert acc1.state["total"] == pytest.approx(0.0)  # gen 初始 count=0

    def test_inject_input_to_coupled(self):
        """向耦合模型注入外部输入。"""
        coupled = CoupledDEVS("sys")
        coupled.add_input_port("input")
        acc = Accumulator("acc")
        coupled.add_component(acc)
        coupled.add_eic("input", "acc", "in")

        coord = Coordinator(coupled, start_time=0.0)
        coord.inject_input(1.5, [DEVSMessage(port="input", value=100.0)])

        assert acc.state["total"] == pytest.approx(100.0)
        assert coord.current_time == pytest.approx(1.5)

    def test_generator_count_sequence(self):
        """生成器输出值序列：0, 1, 2, 3, ..."""
        gen = Generator("gen", period=1.0)
        sim = Simulator(gen, start_time=0.0)

        values = []
        for _ in range(5):
            outputs = sim.run_internal()
            values.append(outputs[0].value)

        assert values == [0, 1, 2, 3, 4]


# ============================================================
# Queue 模型测试 + 其他原子模型
# ============================================================

class TestQueueModel:
    """Queue 原子模型测试。"""

    def test_queue_initially_passive(self):
        """空队列：ta = ∞（被动）。"""
        q = Queue("q", processing_time=1.0)
        ta = q.time_advance(q.state)
        assert ta == INFINITY
        assert q.state["busy"] == False
        assert len(q.state["items"]) == 0

    def test_queue_receives_item_becomes_busy(self):
        """收到项目后变为 busy，ta = processing_time。"""
        q = Queue("q", processing_time=2.0)
        sim = Simulator(q, start_time=0.0)

        sim.inject_input(1.0, [DEVSMessage(port="in", value="job1")])

        assert q.state["busy"] == True
        assert len(q.state["items"]) == 1
        assert sim.next_event_time == pytest.approx(3.0)  # 1.0 + 2.0

    def test_queue_output_first_item(self):
        """处理完成后输出队首项目。"""
        q = Queue("q", processing_time=1.0)
        sim = Simulator(q, start_time=0.0)

        sim.inject_input(0.0, [DEVSMessage(port="in", value="A")])
        outputs = sim.run_internal()  # t=1.0

        assert len(outputs) == 1
        assert outputs[0].port == "out"
        assert outputs[0].value == "A"
        # 处理完成后 busy=False
        assert q.state["busy"] == False
        # 但 items 里还有（直到收到 done）
        # 注意：当前 Queue 实现在 internal_transition 只把 busy 设为 False
        # items 要等 done 消息才弹出

    def test_queue_fifo_order(self):
        """队列 FIFO 顺序：先入先出。"""
        q = Queue("q", processing_time=0.5)
        sim = Simulator(q, start_time=0.0)

        # 依次注入 3 个项目
        sim.inject_input(0.0, [DEVSMessage(port="in", value=1)])
        sim.inject_input(0.1, [DEVSMessage(port="in", value=2)])
        sim.inject_input(0.2, [DEVSMessage(port="in", value=3)])

        # 第一个输出应该是 1
        outputs = sim.run_internal()  # t=0.5
        assert outputs[0].value == 1


# ============================================================
# 消息与数据类测试
# ============================================================

class TestDEVSMessage:
    """DEVSMessage 数据类测试。"""

    def test_message_creation(self):
        """消息创建正确。"""
        msg = DEVSMessage(port="out", value=42)
        assert msg.port == "out"
        assert msg.value == 42

    def test_message_equality(self):
        """相同消息相等。"""
        msg1 = DEVSMessage(port="a", value=1)
        msg2 = DEVSMessage(port="a", value=1)
        assert msg1 == msg2

    def test_message_different(self):
        """不同消息不相等。"""
        msg1 = DEVSMessage(port="a", value=1)
        msg2 = DEVSMessage(port="b", value=1)
        assert msg1 != msg2


# ============================================================
# R03 规则验证
# ============================================================

class TestR03NoFallback:
    """R03 规则验证：无 fall-back 兜底。"""

    def test_solver_no_except_pass(self):
        """AST 检查：solver.py 无 except:pass 模式。"""
        import ast

        with open("src/polaris/sim/devs/solver.py") as f:
            source = f.read()
        tree = ast.parse(source)

        fallback_count = 0
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                for child in ast.walk(node):
                    if isinstance(child, ast.Pass):
                        fallback_count += 1

        assert fallback_count == 0, (
            f"发现 {fallback_count} 个 except:pass fall-back，违反 R03"
        )
