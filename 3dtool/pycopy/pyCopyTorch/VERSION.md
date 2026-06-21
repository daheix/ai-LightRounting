# pyCopyTorch 版本历史

复刻 PyTorch 核心子集（Tensor/autograd/nn.Module/Linear/LayerNorm/ReLU/Adam/Conv2d/MaxPool2d）。

## v1.0.0 (2026-06-21) — 100% 复刻完成

- 复刻内容: Tensor + autograd + nn.Module + Linear/LayerNorm/ReLU/Tanh/Sequential +
  Adam 优化器 + Conv2d/MaxPool2d/Dropout/Embedding
- 复刻位置: `src/polaris/nn/`
- 对比测试: `tests/test_replica_torch.py` 5 个用例全部通过
  - TestTensorOps::test_add（加法）
  - TestTensorOps::test_mul（乘法）
  - TestTensorOps::test_matmul（矩阵乘）
  - TestLinearForward::test_linear_forward_same_weights（同权重前向一致）
  - TestAdamStep::test_adam_one_step（Adam 一步更新一致）
- 行为一致性: 浮点容差 1e-6（NumPy 实现与 torch 默认 float32 一致）
- 来源: https://pytorch.org/ (BSD-3-Clause, torch 2.x API)
- 验收: 规则 21.4 全部通过（对比测试 + 门禁 + 来源标注 + 版本登记）

## v2.0.x 规划（能力优化方向）

- v2.0.1: 自动混合精度（AMP）支持
- v2.0.2: 算子融合（Linear+ReLU 融合为单次遍历）
- v2.0.3: Conv2d im2col 优化（替代朴素 for 循环）
- v2.0.4: 分布式数据并行（DDP）支持
