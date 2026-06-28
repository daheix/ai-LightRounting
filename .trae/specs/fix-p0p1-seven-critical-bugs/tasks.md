# Tasks

- [ ] Task 1: P0-A 修复 `ai/inverse_design.py` WGAN-GP/DDPM 参数永不更新
  - [ ] SubTask 1.1: 重构 `_adam_init`/`_adam_update`，G/D 参数分别管理，仅更新提供的梯度
  - [ ] SubTask 1.2: 重写 `GANInverseDesigner.train_step` 实现 WGAN-GP（5 次 critic + 1 次 G），手写解析反向传播
  - [ ] SubTask 1.3: 重写 `DiffusionInverseDesigner.train_step` 实现 DDPM 前向加噪 + MSE 反向 + Adam 更新
  - [ ] SubTask 1.4: 验证 train_step 调用后 G/D 参数实际变化（not allclose）
  - [ ] SubTask 1.5: 压缩 `inverse_design.py` ≤800 行（规则 7.1）
  - [ ] SubTask 1.6: 添加回归测试 `tests/test_inverse_design_p0a.py` 验证参数更新

- [ ] Task 2: P0-B 修复 `device/tcad_thermal_package.py` `solve_steady_state` FDM 虚标
  - [ ] SubTask 2.1: 实现 2D FDM 离散化稳态热扩散方程 ∇·(k∇T) + Q = 0，构建稀疏矩阵
  - [ ] SubTask 2.2: 用 `scipy.sparse.linalg.spsolve` 求解稀疏线性系统
  - [ ] SubTask 2.3: 删除原 1D 热阻 + 高斯横向扩散解析近似
  - [ ] SubTask 2.4: 删除 `thermal_crosstalk_matrix` magic number 0.5，改用 FDM 解的 heater 中心温升
  - [ ] SubTask 2.5: 修正 docstring 标注真实 FDM 来源（Cocorullo 1999/Sze 2006/Taflove 2005）
  - [ ] SubTask 2.6: 添加回归测试 `tests/test_tcad_thermal_p0b.py` 验证能量守恒 + 温度场单调衰减

- [ ] Task 3: P0-C 修复 `nn/attention.py` MultiHeadAttention/TransformerBlock 不可微
  - [ ] SubTask 3.1: 删除 `MultiHeadAttention.forward` 中 4 处 `.data` 截断
  - [ ] SubTask 3.2: 删除 `TransformerBlock.forward` 中 2 处 `.data` 截断
  - [ ] SubTask 3.3: 验证全部计算为 `Tensor` 操作，autograd 图完整
  - [ ] SubTask 3.4: 添加回归测试 `tests/test_attention_p0c.py` 验证 backward 梯度流通

- [ ] Task 4: P0-D 修复 `eval/layout_render.py` `_check_bend_radius` 算法错误
  - [ ] SubTask 4.1: 用三点圆弧公式 R = |P1P2|·|P2P3|·|P1P3| / (4·三角形面积) 替换错误实现
  - [ ] SubTask 4.2: 处理共线三点退化情形（raise ValueError，禁止 fall-back）
  - [ ] SubTask 4.3: 添加回归测试 `tests/test_layout_render_p0d.py` 验证已知三点 (0,0)/(1,1)/(2,0) → R≈1.414

- [ ] Task 5: P0-E 修复 `sim/jax_backend.py` benchmark 返回 -1 假数据
  - [ ] SubTask 5.1: 将 `return {..., "jit_time": -1, "speedup": -1}` 改为 `raise RuntimeError("JAX 不可用...")`
  - [ ] SubTask 5.2: 修正 docstring 移除"GPU 加速 50+ 倍"虚标表述（违反 R04）
  - [ ] SubTask 5.3: 添加回归测试 `tests/test_jax_backend_p0e.py` 验证 JAX 不可用时 raise

- [ ] Task 6: P1-F 删除 `inverse/adjoint_optimizer.py` 死代码
  - [ ] SubTask 6.1: 全项目搜索 `from polaris.inverse.adjoint_optimizer` / `import adjoint_optimizer` 引用
  - [ ] SubTask 6.2: 将引用迁移至 `topology_adjoint_optimizer`（如有）
  - [ ] SubTask 6.3: 删除 `src/polaris/inverse/adjoint_optimizer.py`
  - [ ] SubTask 6.4: 验证 `inverse/__init__.py` 仅从 `topology_adjoint_optimizer` 导入
  - [ ] SubTask 6.5: 验证 `import polaris.inverse` 仍可正常工作

- [ ] Task 7: P1-G 修复 `inverse/topology_adjoint_optimizer.py` `adjoint_simulate` 假实现
  - [ ] SubTask 7.1: 实现 `adjoint_simulate` 计算真伴随梯度（基于 `jax.grad(_total_objective)` 在当前 rho_raw）
  - [ ] SubTask 7.2: 需要传入 rho_raw/beta 上下文，调整签名（保持向后兼容或更新调用方）
  - [ ] SubTask 7.3: 添加回归测试 `tests/test_topology_adjoint_p0g.py` 验证 `adjoint_simulate` 与 `compute_gradient` 数值一致（相对误差 < 1e-6）

- [ ] Task 8: 全量回归测试与提交
  - [ ] SubTask 8.1: 运行 `pytest tests/` 全量测试套件
  - [ ] SubTask 8.2: 确认无新增 fall-back / 假数据（R03）
  - [ ] SubTask 8.3: 确认无 TODO/FIXME/HACK 残留（R05）
  - [ ] SubTask 8.4: 确认所有修改文件 ≤800 行、函数 ≤80 行、圈复杂度 ≤15
  - [ ] SubTask 8.5: 每个修复立即 `git add <精确文件>` → `git commit -m "fix(v3.3-P0X): ..."` → `git push origin main`
  - [ ] SubTask 8.6: 刷新 `操作记录.md` 记录本轮所有修复

# Task Dependencies
- Task 1 SubTask 1.4 依赖 1.1/1.2/1.3 完成
- Task 1 SubTask 1.5（压缩行数）依赖 1.2/1.3 完成
- Task 6 SubTask 6.3（删除文件）依赖 6.1/6.2 完成（先迁移引用）
- Task 7 可与 Task 6 并行（topology_adjoint_optimizer 是保留文件）
- Task 8 依赖 Task 1-7 全部完成
