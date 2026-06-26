# R04 不参与 GPU 计算（战略决策，不可撤销）

PoLaRIS 项目战略决策：不参与 GPU 计算（2026-06-25 项目所有者指示）。

- 禁止 CuPy/CUDA/ROCm/AppleMetal 等所有 GPU 后端
- 禁止 FP16/BF16 半精度、多卡 GPU 分布式
- GPU 相关功能点标记 `🚫不参与`，不计入覆盖率
- 纯 NumPy/SciPy/JAX(CPU) 实现
