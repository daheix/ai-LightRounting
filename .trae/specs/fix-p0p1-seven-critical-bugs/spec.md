# 修复 7 项 P0/P1 严重 Bug Spec

## Why

代码审查发现 PoLaRIS 项目存在 7 项 P0/P1 级严重 Bug，违反 R02（学术诚信）、R03（禁止 fall-back）、R05（Bug 必修）规则，导致核心 AI/仿真模块要么参数永不更新（P0-A）、要么虚标算法（P0-B）、要么不可微（P0-C）、要么算法错误（P0-D）、要么返回假数据（P0-E）、要么是死代码（P1-F）、要么是假实现（P1-G）。这些缺陷使逆向设计/神经网络/热仿真/版图校验/伴随优化等核心能力名存实亡，必须立即修复以恢复业务正确性。

## What Changes

### P0-A: 修复 `ai/inverse_design.py` WGAN-GP/DDPM 参数永不更新
- 重写 `GANInverseDesigner.train_step`：实现完整 WGAN-GP（5 次 critic 步 + 1 次 G 步），手写解析反向传播 + Adam 更新
- 重写 `DiffusionInverseDesigner.train_step`：实现 DDPM 前向加噪 + 噪声预测 + MSE 反向 + Adam 更新
- 重构 `_adam_init`/`_adam_update`：G/D 参数分别管理，仅更新提供的梯度
- 来源：Gulrajani et al. 2017 NeurIPS "Improved Training of WGANs"；Ho et al. 2020 NeurIPS "DDPM"；Kingma & Ba 2015 ICLR "Adam"

### P0-B: 修复 `device/tcad_thermal_package.py` `solve_steady_state` FDM 虚标
- 实现 2D 有限差分法（FDM）稳态热扩散求解器，使用 `scipy.sparse.linalg.spsolve` 求解稀疏线性系统
- 删除原 1D 热阻 + 高斯横向扩散解析近似（被 docstring 虚标为 FDM）
- 删除 `thermal_crosstalk_matrix` 中的 magic number `0.5`，改为通过 FDM 解的 heater 中心温升直接计算
- 来源：Cocorullo 1999；Sze 2006 "Physics of Semiconductor Devices"；Taflove 2005 "Computational Electrodynamics"

### P0-C: 修复 `nn/attention.py` MultiHeadAttention/TransformerBlock 不可微
- 删除 `MultiHeadAttention.forward` 中 4 处 `.data` 截断（行 78、81-83）
- 删除 `TransformerBlock.forward` 中 2 处 `.data` 截断（行 136、139）
- 保持全部计算为 `Tensor` 操作，使 autograd 梯度流通
- 来源：Vaswani et al. 2017 NeurIPS "Attention Is All You Need"

### P0-D: 修复 `eval/layout_render.py` `_check_bend_radius` 算法错误
- 用三点圆弧公式替换错误用线段长度当半径的实现
- 公式：R = |P1P2|·|P2P3|·|P1P3| / (4·三角形面积)
- 来源：基于解析几何三点定圆公式

### P0-E: 修复 `sim/jax_backend.py` benchmark 返回 -1 假数据
- 将 `return {"numpy_time": numpy_time, "jit_time": -1, "speedup": -1}` 改为 `raise RuntimeError("JAX 不可用，无法执行 benchmark")`
- 修复 docstring 中"GPU 加速 50+ 倍"虚标表述（违反 R04 不参与 GPU）
- 来源：R03 禁止 fall-back；R04 不参与 GPU

### P1-F: 删除 `inverse/adjoint_optimizer.py` 死代码
- 文件 99% 与 `topology_adjoint_optimizer.py` 重复，类名 `AdjointOptimizer` 已被 `TopologyAdjointOptimizer` 替代
- `inverse/__init__.py` 已不导入该模块
- 删除文件，更新任何引用

### P1-G: 修复 `inverse/topology_adjoint_optimizer.py` `adjoint_simulate` 假实现
- 当前 `adjoint_simulate` 仅返回归一化伴随源，未真正计算梯度
- 实现真正的伴随梯度计算：返回 `Re(E_adj · ∂A/∂ρ · E_fwd)` 即 `jax.grad` 在当前 rho_raw 处的梯度
- 来源：Piggott 2017 Nature Photonics；Hughes 2018 arXiv:1811.01255（autograd = adjoint）

## Impact

- Affected specs:
  - `audit-academic-integrity-deep`（学术诚信审查相关）
  - `unify-academic-integrity-checks`（统一学术诚信检查）
  - `fix-p0-pipeline-defects`（同属 P0 修复轮次）
- Affected code:
  - `src/polaris/ai/inverse_design.py`（P0-A 重写训练循环）
  - `src/polaris/device/tcad_thermal_package.py`（P0-B 重写 solve_steady_state）
  - `src/polaris/nn/attention.py`（P0-C 删除 .data）
  - `src/polaris/eval/layout_render.py`（P0-D 修复三点公式）
  - `src/polaris/sim/jax_backend.py`（P0-E 删除 -1 fall-back）
  - `src/polaris/inverse/adjoint_optimizer.py`（P1-F 删除文件）
  - `src/polaris/inverse/topology_adjoint_optimizer.py`（P1-G 实现真伴随）

## ADDED Requirements

### Requirement: WGAN-GP/DDPM 参数真实更新
系统 SHALL 在 `GANInverseDesigner.train_step` 和 `DiffusionInverseDesigner.train_step` 中执行完整的反向传播 + Adam 优化器更新，确保每次 `train_step` 调用后 G/D 参数实际变化。

#### Scenario: GAN 训练步参数更新
- **WHEN** 调用 `GANInverseDesigner.train_step(real_shapes)`
- **THEN** Generator 参数（G_W1/G_b1/G_W2/G_b2）和 Discriminator 参数（D_W1/D_b1/D_W2/D_b2）均发生变化（与调用前 not allclose）
- **AND** 返回字典包含 d_loss/g_loss 数值，符合 WGAN-GP 损失定义

#### Scenario: DDPM 训练步参数更新
- **WHEN** 调用 `DiffusionInverseDesigner.train_step(x0, t, rng)`
- **THEN** DDPM 网络参数（U-Net 权重）发生变化，返回 loss 为有限实数

### Requirement: 2D FDM 稳态热求解
系统 SHALL 使用 2D 有限差分法离散化稳态热扩散方程 ∇·(k∇T) + Q = 0，通过 `scipy.sparse.linalg.spsolve` 求解稀疏线性系统，禁用任何解析近似 fall-back。

#### Scenario: 单加热器稳态求解
- **WHEN** 调用 `solve_steady_state(heater_powers=[P], ...)`
- **THEN** 返回 2D 温度场 T[y,x]，加热器位置温度最高，向边界单调衰减
- **AND** 满足能量守恒（边界热流 = 总加热功率，误差 < 5%）

### Requirement: 注意力机制可微分
系统 SHALL 保证 `MultiHeadAttention.forward` 和 `TransformerBlock.forward` 的全部计算保留 `Tensor` autograd 图，无 `.data` 截断，使梯度可流通。

#### Scenario: 反向传播梯度流
- **WHEN** 构造 `Tensor(requires_grad=True)` 输入，经过 `TransformerBlock.forward` 后调用 `.backward()`
- **THEN** 输入 Tensor 的 `.grad` 非 None，且数值有限

### Requirement: 弯曲半径三点公式正确
系统 SHALL 用三点圆弧公式 R = |P1P2|·|P2P3|·|P1P3| / (4·三角形面积) 计算弯曲半径，禁止用线段长度近似。

#### Scenario: 已知三点验证
- **WHEN** 输入三点 (0,0)、(1,1)、(2,0)
- **THEN** 计算半径 R ≈ 1.414（单位圆过此三点），误差 < 1%

### Requirement: JAX benchmark 失败即 raise
系统 SHALL 在 JAX 不可用时 raise `RuntimeError`，禁止返回 -1 假数据。docstring SHALL 移除"GPU 加速"表述（R04 不参与 GPU）。

#### Scenario: JAX 不可用
- **WHEN** JAX 未安装或不可用，调用 `benchmark(...)`
- **THEN** raise `RuntimeError` 明确说明 JAX 不可用

### Requirement: 伴随优化器单文件无死代码
系统 SHALL 只保留 `topology_adjoint_optimizer.py`，删除 99% 重复的 `adjoint_optimizer.py`。

#### Scenario: 死代码删除
- **WHEN** 检查 `src/polaris/inverse/` 目录
- **THEN** `adjoint_optimizer.py` 文件不存在
- **AND** `inverse/__init__.py` 仅从 `topology_adjoint_optimizer` 导入

### Requirement: 真伴随梯度计算
系统 SHALL 在 `TopologyAdjointOptimizer.adjoint_simulate` 中计算真正的伴随梯度 `Re(E_adj · ∂A/∂ρ · E_fwd)`，等价于 `jax.grad(_total_objective)`，禁止仅返回归一化伴随源。

#### Scenario: 伴随梯度数值正确
- **WHEN** 调用 `adjoint_simulate(adjoint_source)`，且 adjoint_source 为目标模式
- **THEN** 返回的梯度与 `compute_gradient(rho_raw)` 在相同 rho_raw 处数值一致（相对误差 < 1e-6）

## MODIFIED Requirements

### Requirement: 学术诚信合规
所有模块 SHALL 在 docstring 中标注 ≥5 个文献 URL，所有参数/公式真实可溯源。删除任何 magic number（如 `0.5`）或假数据（如 `-1`），违规则视为 fall-back（违反 R03）。

### Requirement: 文件行数限制
`ai/inverse_design.py` SHALL 压缩至 ≤800 行（规则 7.1）。函数 ≤80 行，圈复杂度 ≤15。

## REMOVED Requirements

### Requirement: WGAN-GP/DDPM 静默 no-op 训练
**Reason**: 违反 R03（禁止 fall-back）和 R05（Bug 必修）—— 训练步不更新参数等同于假实现
**Migration**: 重写为完整反向传播 + Adam 更新

### Requirement: solve_steady_state 解析近似被虚标为 FDM
**Reason**: 违反 R02（学术诚信）—— docstring 标 FDM 但实现是解析近似
**Migration**: 重写为真实 2D FDM + scipy.sparse.linalg.spsolve

### Requirement: benchmark 返回 -1 兜底
**Reason**: 违反 R03（禁止 fall-back）—— -1 是假数据
**Migration**: raise RuntimeError

### Requirement: adjoint_optimizer.py 死代码文件
**Reason**: 99% 重复 topology_adjoint_optimizer.py，违反规则"代码文件只有一份"
**Migration**: 删除文件，引用迁移至 topology_adjoint_optimizer
