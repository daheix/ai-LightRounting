# pyCopySAX 版本历史

复刻 SAX 的子网络增长算法（subnetwork growth），用于光子电路 S 参数级联。

## v1.0.0 (2026-06-21) — 100% 复刻完成

- 复刻内容: cascade_circuit（子网络增长算法）+ CascadeContext
- 复刻位置: `src/polaris/sim/cascade.py`
- 对比测试: `tests/test_replica_sax.py` 3 个用例全部通过
  - TestCascadeCircuit::test_two_waveguides_transmission（双波导传输）
  - TestCascadeCircuit::test_two_waveguides_reflection_zero（双波导反射为零）
  - TestCascadeCircuit::test_multi_frequency_array（多频率数组）
- 行为一致性: 浮点容差 1e-9
- 来源: https://flaport.github.io/sax/ (Apache-2.0, sax 0.14.x)
- 算法依据: 标准微波网络 S 参数级联理论
- 验收: 规则 21.4 全部通过

## v2.0.x 规划（能力优化方向）

- v2.0.1: 子网络增长算法并行化（多频率并行）
- v2.0.2: 稀疏矩阵优化（大电路 S 矩阵稀疏化）
- v2.0.3: S 参数缓存（相同子电路复用结果）
- v2.0.4: 多端口网络级联（>2 端口）
