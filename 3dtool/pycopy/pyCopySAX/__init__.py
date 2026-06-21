"""pyCopySAX — sax 纯 NumPy 100% 复刻（规则 3/21）。

复刻 SAX 的子网络增长算法，用于光子电路 S 参数级联。

原工具: SAX https://flaport.github.io/sax/ (Apache-2.0)
复刻位置: src/polaris/sim/cascade.py
复刻算法: 子网络增长（subnetwork growth）

版本历史: 见 VERSION.md
- v1.0.0 (2026-06-21): 100% 复刻完成，3 个对比测试通过

来源:
- SAX 子网络增长: https://flaport.github.io/sax/
- 光子电路 S 参数级联理论: 标准微波网络理论
"""

from polaris.sim.cascade import (
    CascadeContext,
    cascade_circuit,
)

__version__ = "1.0.0"

__all__ = [
    "cascade_circuit",
    "CascadeContext",
    "__version__",
]
