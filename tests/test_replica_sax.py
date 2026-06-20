"""pyCopySAX 与真实 sax 对比测试（规则 4.6）。

对比 src/polaris/sim/cascade.py（pyCopySAX 复刻）与 SAX 的级联一致性，
覆盖两波导级联、反射项为零、多频率数组等场景。

来源:
- SAX: https://flaport.github.io/sax/ (Apache-2.0)
- 复刻位置: src/polaris/sim/cascade.py
- 复刻入口: 3dtool/pycopy/pyCopySAX/__init__.py
"""

from __future__ import annotations

import numpy as np
import sax
from pycopy.pyCopySAX import cascade_circuit  # noqa: E402

from polaris.sim.models import waveguide_s  # noqa: E402


def _build_sax_circuit(instances, connections, ports):
    """用真实 SAX 构建电路并返回 S 参数字典。

    直接使用 SAX 的 circuit API，端口引用使用逗号分隔格式。
    """
    models = {}
    netlist_instances = {}
    for name, sdict in instances.items():
        model_name = f"model_{name}"

        def make_model(sd):
            def model(**kwargs):
                return sd

            return model

        models[model_name] = make_model(sdict)
        netlist_instances[name] = model_name

    def to_sax_ref(ref):
        parts = ref.split(".", 1)
        return f"{parts[0]},{parts[1]}" if len(parts) == 2 else ref

    netlist = {
        "instances": netlist_instances,
        "connections": {to_sax_ref(c[0]): to_sax_ref(c[1]) for c in connections},
        "ports": {ext: to_sax_ref(int_ref) for ext, int_ref in ports.items()},
    }
    circuit, _ = sax.circuit(netlist=netlist, models=models)
    return circuit()


class TestCascadeCircuit:
    """对比 pyCopySAX cascade_circuit 与真实 SAX 的级联结果。"""

    def test_two_waveguides_transmission(self):
        # Arrange — 两个 50μm 波导级联，传输应等于 100μm 波导
        wl = np.array([1.55])
        s1 = waveguide_s(wl=wl, length=50.0, neff=2.4)
        s2 = waveguide_s(wl=wl, length=50.0, neff=2.4)
        instances = {"wg1": s1, "wg2": s2}
        connections = [("wg1.out", "wg2.in")]
        ports = {"in": "wg1.in", "out": "wg2.out"}

        # Act
        out_replica = cascade_circuit(instances, connections, ports)
        out_sax = _build_sax_circuit(instances, connections, ports)

        # Assert — 传输项 S21 一致
        np.testing.assert_allclose(out_replica[("out", "in")], out_sax[("out", "in")], atol=1e-9)

    def test_two_waveguides_reflection_zero(self):
        # Arrange — 无损波导级联后反射项 S11/S22 应为零
        wl = np.array([1.55])
        s1 = waveguide_s(wl=wl, length=50.0, neff=2.4)
        s2 = waveguide_s(wl=wl, length=50.0, neff=2.4)
        instances = {"wg1": s1, "wg2": s2}
        connections = [("wg1.out", "wg2.in")]
        ports = {"in": "wg1.in", "out": "wg2.out"}

        # Act
        out_replica = cascade_circuit(instances, connections, ports)
        out_sax = _build_sax_circuit(instances, connections, ports)

        # Assert — 反射项 S11 与 S22 均为零且一致
        np.testing.assert_allclose(out_replica[("in", "in")], out_sax[("in", "in")], atol=1e-9)
        np.testing.assert_allclose(out_replica[("out", "out")], out_sax[("out", "out")], atol=1e-9)

    def test_multi_frequency_array(self):
        # Arrange — 多波长数组级联
        wl = np.linspace(1.5, 1.6, 50)
        s1 = waveguide_s(wl=wl, length=30.0, neff=2.4)
        s2 = waveguide_s(wl=wl, length=70.0, neff=2.4)
        instances = {"wg1": s1, "wg2": s2}
        connections = [("wg1.out", "wg2.in")]
        ports = {"in": "wg1.in", "out": "wg2.out"}

        # Act
        out_replica = cascade_circuit(instances, connections, ports)
        out_sax = _build_sax_circuit(instances, connections, ports)

        # Assert — 全频段传输项一致
        np.testing.assert_allclose(out_replica[("out", "in")], out_sax[("out", "in")], atol=1e-9)
        np.testing.assert_allclose(out_replica[("in", "out")], out_sax[("in", "out")], atol=1e-9)
