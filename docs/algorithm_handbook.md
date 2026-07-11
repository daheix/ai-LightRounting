# PoLaRIS 算法手册

> 版本 v6.1 · 2026-07 · 核心算法数学推导与调优指南
> 数据来源：modules/*/src/polaris_* 实际代码 + 学术文献（R02 学术诚信）

---

## 目录

- [第 1 章：布局算法](#第-1-章布局算法)
- [第 2 章：布线算法](#第-2-章布线算法)
- [第 3 章：物理求解器算法](#第-3-章物理求解器算法)
- [第 4 章：逆向设计算法](#第-4-章逆向设计算法)
- [第 5 章：优化器算法](#第-5-章优化器算法)
- [第 6 章：量子光子算法](#第-6-章量子光子算法)
- [第 7 章：验证算法](#第-7-章验证算法)
- [第 8 章：光电协同算法](#第-8-章光电协同算法)

---

## 第 1 章：布局算法

### 1.1 DREAMPlace 解析法布局（analytical 模式）

#### 1.1.1 算法原理

将布局问题转化为连续优化，通过加权平均初始布局 → 平滑 HPWL 梯度下降（Adam）→ FFDH 合法化 → 端口对齐后处理，消除器件重叠。

**目标函数：**

```
min  HPWL_smooth(x) + λ_d · D(x)
```

**HPWL（半周长线长）平滑近似（log-sum-exp）：**

```
HPWL = Σ_{net} (max_i(x_i) - min_i(x_i) + max_i(y_i) - min_i(y_i))

平滑 HPWL（gamma → 0 时趋近真实 HPWL）:
HPWL_smooth ≈ γ · [ln(Σ_i exp(x_i/γ)) + ln(Σ_i exp(-x_i/γ))]
```

**密度惩罚：**

```
D(x) = Σ_i ρ_i(x) - target_density
```

其中 ρ_i(x) 为位置 x 处的器件密度场（高斯核/成对排斥力）。

**Adam 优化器更新：**

```
m_t = β₁·m_{t-1} + (1-β₁)·g_t
v_t = β₂·v_{t-1} + (1-β₂)·g_t²
x_t = x_{t-1} - lr · m̂_t / (√v̂_t + ε)

β₁=0.9, β₂=0.999, ε=1e-8
```

**FFDH 合法化（First-Fit Decreasing Height）：** 消除重叠，自适应行高，将连续坐标映射到合法离散位置。

#### 1.1.2 参数表（从代码提取真实默认值）

| 参数名 | 默认值 | 范围 | 说明 | 来源 |
|--------|--------|------|------|------|
| `gamma` | 4.0 | 0.1-10.0 | log-sum-exp 平滑系数（越小越接近真实 HPWL） | DREAMPlace TCAD 2020 |
| `density_weight` | 1.0e-3 | 1e-5 - 1.0 | 密度惩罚权重（越大越强制无重叠） | DREAMPlace TCAD 2020 |
| `learning_rate` | 0.01 | 0.001 - 0.1 | Adam 优化器学习率 | DREAMPlace TCAD 2020 |
| `max_iterations` | 200 | 50-1000 | 最大迭代次数 | PoLaRIS 默认（DREAMPlace 参考 1000） |
| `density_bandwidth` | 10.0 | 5.0-50.0 | 密度场带宽 (μm)，距离 < bandwidth 的器件对施加排斥力 | DREAMPlace 默认 |
| `convergence_threshold` | 1.0 | 0.01-10.0 | 收敛阈值（HPWL 变化 < 阈值则提前停止） | PoLaRIS 默认 |
| `seed` | 42 | 任意整数 | 随机种子（可复现） | DREAMPlace torch.manual_seed 约定 |

**Adam 内部常量（硬编码）：** β₁=0.9, β₂=0.999, ε=1e-8

#### 1.1.3 调优指南

- **大电路（>20 器件）**：用低学习率（0.005），增大 max_iterations（300+），增大 density_bandwidth（20.0+）
- **小电路（<10 器件）**：可高学习率（0.05），减少 max_iterations（100）
- **高密度画布**：增大 density_weight（0.01），降低 DENSITY_MAX 违规风险
- **收敛缓慢**：降低 gamma（1.0-2.0），使 HPWL 更接近真实值
- **DENSITY_MIN 自适应**（*创新*）：当器件总面积/画布面积 > 0.5 时，自动放大画布 3× 使密度 ≈33%

#### 1.1.4 文献来源

- DREAMPlace DAC 2019: https://cseweb.ucsd.edu/classes/fa23/cse248-a/papers/placement/dreamplace.pdf
- DREAMPlace TCAD 2020 (Lin et al.): https://arxiv.org/abs/2004.10746
- log-sum-exp 平滑: Nesterov 2005 "Smooth minimization of non-smooth functions"
- Adam 优化器: Kingma & Ba 2014 https://arxiv.org/abs/1412.6980
- FFDH 合法化: Coffman et al. SIAM J. Comput. 9(4) 1980 https://epubs.siam.org/doi/10.1137/0209062
- HPWL 指标: Kahng & Lienig IEEE TCAD 2009 https://ieeexplore.ieee.org/document/4685534

#### 1.1.5 代码位置

`modules/place/src/polaris_place/analytical.py` — `AnalyticalConfig` 类、`place_analytical()` 函数
辅助模块：`metrics.py`（HPWL/密度梯度）、`legalize.py`（FFDH）、`align.py`（端口对齐）

---

### 1.2 AlphaChip PPO-GNN 布局（ppo_gnn 模式）

#### 1.2.1 算法原理

基于 AlphaChip 的 Edge-GNN + PPO ActorCritic 框架，将布局建模为逐器件马尔可夫决策过程（MDP）。

**Edge-GNN 状态编码：**

```
节点特征 [N, 4]: [width_norm, height_norm, type_hash, idx_norm]
边特征 [E, 15]: [曼哈顿距离, 带宽需求, 优先级, 类型one-hot(4), 波段one-hot(3), 折射率差, 波导损耗, 串扰, 弯曲半径, net关系]
图嵌入 [16]: GlobalAttention 读出 → gate_softmax · feat_linear
```

**消息传递（2 层 GNN）：**

```
h^{l+1}_i = ReLU(W_upd · [proj_i ‖ agg_i])
agg_i = (1/|N(i)|) Σ_{j∈N(i)} tanh(W_msg · [proj_j ‖ e_ji])
proj_i = W_proj · h^l_i
```

**PPO 策略梯度（训练阶段，Schulman et al. 2017）：**

```
L_CLIP = E[min(r_t · A_t, clip(r_t, 1-ε, 1+ε) · A_t)]
GAE 优势估计: A_t = Σ_l (γλ)^l · δ_{t+l}
δ_t = r_t + γ·V(s_{t+1}) - V(s_t)
```

**推理阶段：** action = action_mean（确定性，无采样噪声），sigmoid 压缩到画布坐标。

#### 1.2.2 参数表（从代码提取真实默认值）

| 参数名 | 默认值 | 说明 | 来源 |
|--------|--------|------|------|
| `_OBS_DIM` | 8 | PPO 基础观测维度（器件级特征） | AlphaChip Nature 2021 |
| `_GNN_OUT_DIM` | 16 | Edge-GNN 输出维度（图级嵌入） | AlphaChip Nature 2021 |
| `_GNN_HIDDEN_DIM` | 32 | Edge-GNN 隐藏层维度 | AlphaChip Nature 2021 |
| `_GNN_NUM_LAYERS` | 2 | Edge-GNN 消息传递层数 | AlphaChip Nature 2021 |
| `_GNN_NODE_FEAT_DIM` | 4 | 节点特征维度 | AlphaChip Nature 2021 |
| `PHOTONIC_EDGE_DIM` | 15 | 边特征维度 | PoLaRIS 与 stage3 对齐 |
| `_ACTION_DIM` | 2 | 动作维度（归一化坐标 x, y） | AlphaChip Nature 2021 |
| `_HIDDEN_DIM` | 64 | PPO 网络隐藏层维度 | AlphaChip Nature 2021 |
| `_GNN_OBS_DIM` | 24 | GNN 拼接观测维度（8+16） | AlphaChip Nature 2021 |
| 重叠消解步长 | 5.0 μm | 贪心重叠消解网格步进 | Kahng & Lienig 2009 |
| 最大重叠消解尝试 | 200 | 超出即 raise RuntimeError | PoLaRIS R03 |

#### 1.2.3 调优指南

- **必须预训练 checkpoint**：无可用 checkpoint 时 raise RuntimeError（R03 禁止 fall-back）
- **checkpoint 路径**：`checkpoints/polaris_place_ppo_gnn.json` 或环境变量 `POLARIS_PLACE_CHECKPOINT`
- **器件类型哈希**：使用 `zlib.crc32` 稳定跨进程（R389 修复，原 `hash()` 受 PYTHONHASHSEED 影响）
- **大电路**：需更多 expert demos 预训练，22 expert demos 为基准
- **权重形状不匹配**：即 raise，不降级到初始化网络

#### 1.2.4 文献来源

- AlphaChip: Mirhoseini et al., Nature 2021 https://www.nature.com/articles/s41586-021-03544-w
- Chip Placement with Deep RL: https://arxiv.org/abs/2004.10746
- GAT 注意力: Veličković et al., ICLR 2018 https://arxiv.org/abs/1710.10903
- PPO: Schulman et al. 2017 https://arxiv.org/abs/1707.06347
- Engstrom et al. 2020 "Implementation Matters in PPO" https://arxiv.org/abs/2005.12729
- HPWL 指标: Kahng & Lienig IEEE TCAD 2009 https://ieeexplore.ieee.org/document/4685534

#### 1.2.5 代码位置

`modules/place/src/polaris_place/ppo_gnn.py` — `EdgeGNN` 类、`ActorCritic` 类、`place_ppo_gnn()` 函数
训练模块：`modules/trainer/src/polaris_trainer/ppo.py`

---

## 第 2 章：布线算法

### 2.1 Euler 螺旋曲线波导（curvy router）

#### 2.1.1 算法原理

使用 Euler 螺旋（clothoid）连接两个端口，曲率从 0 线性增至 1/R，实现低损耗弯曲过渡。

**Euler 螺旋公式（clothoid 数学定义）：**

```
曲率: κ(s) = s / (R·L)    （s∈[0, L]，从 0 线性增至 1/R）
转角: θ = L / (2R)
弧长: L = 2·R·θ            （单段 0→1/R clothoid）
对 90° 弯曲 (θ=π/2): L = π·R
```

**终点位移近似（*创新*，经验近似系数 0.6）：**

```
对 90° 单段 clothoid，数值积分得位移/L ≈ 0.596
取 0.6 作为保守上界，用于缩放预判
actual_dist_approx = L × 0.6
```

**弯曲数计算：** 遍历路径点序列，当中间点的入射方向与出射方向不一致时计为一次弯曲。

**损耗模型：**

```
loss_db = propagation_loss + n_bends × bend_loss + n_crossings × crossing_loss

propagation_loss = loss_db_cm × path_length(μm) / 1e4    （cm = 1e4 μm）
bend_loss = 0.05 dB/bend
crossing_loss = 0.3 dB/crossing
```

#### 2.1.2 参数表（从代码提取真实默认值）

| 参数名 | 默认值 | 范围 | 说明 | 来源 |
|--------|--------|------|------|------|
| `PROPAGATION_LOSS_DB_CM` | 3.0 | 0.5-10.0 | SOI 波导传播损耗 (dB/cm) | Soref 1993 IEEE Proc. 41(9) |
| `BEND_LOSS_DB` | 0.05 | 0.01-0.5 | 单弯损耗 (dB/bend) | SiEPIC EBeam PDK |
| `CROSSING_LOSS_DB` | 0.3 | 0.1-1.0 | 单次交叉损耗 (dB/crossing) | SiEPIC EBeam PDK crossing_te1550 |
| `DEFAULT_MIN_BEND_RADIUS_UM` | 5.0 | 5.0-50.0 | 默认最小弯曲半径 (μm) | SiEPIC EBeam PDK bend_euler |
| `n_curve_points` | 20 | 10-100 | 曲线采样点数 | PoLaRIS 默认 |
| `_BEND_TOLERANCE` | 1e-9 | - | 弯曲检测浮点容差 (μm) | PoLaRIS 默认 |

#### 2.1.3 调优指南

- **低损耗设计**：增大 `min_bend_radius_um`（10-20 μm），减少弯曲数
- **紧凑布局**：用 Euler 螺旋（曲率线性变化）替代圆弧（恒定曲率），损耗更低
- **S-bend 布线**：step 拓扑（水平→垂直→水平），弯曲数 = 2
- **同 x/同 y 端口**：直线布线，0 弯曲
- **两点距离过近**：自动放大 radius_um 使 actual_dist_approx = target_dist

#### 2.1.4 文献来源

- LiDAR ISPD'25: https://dl.acm.org/doi/pdf/10.1145/3698364.3705355
- LiDAR 2.0 TCAD 2025: https://scopex-asu.github.io/files/publications/PD_TCAD2025_LiDARv2.pdf
- SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- Klauss et al., "Euler spiral waveguide bends", Opt Express 2018 https://doi.org/10.1364/OE.26.029637
- Fujisawa et al. 2017 Optics Express 25(8) 9150 https://opg.optica.org/oe/fulltext.cfm?uri=oe-25-8-9150
- Soref et al. 1993 IEEE Proc. 41(9) https://ieeexplore.ieee.org/document/1148303
- Chrostowski & Hochberg 2015 §6.4 https://www.cambridge.org/core/search?searchField=isbn&searchTerms=1107007731
- Flexcompute Tidy3D clothoid 公式: https://docs.flexcompute.com/projects/tidy3d/en/v2.9.2/notebooks/EulerWaveguideBend.html

#### 2.1.5 代码位置

`modules/route/src/polaris_route/curvy.py` — `CurvyRouter` 类、`CurvyRouteConfig` 类、`generate_euler_bend()` 函数

---

### 2.2 Rip-up & Reroute

#### 2.2.1 算法原理

布线失败时的冲突路径移除重布机制，核心思想：

1. **拥塞感知网排序**：按连接难度（曼哈顿距离/障碍密度）排序，先布难连接
2. **顺序布线**：每条连接用 A* 布线，将路径标记为障碍
3. **冲突重布**：若某连接布线失败，移除冲突路径后重布
4. **迭代**：最多 max_iterations 轮，直到全部成功或达到上限

**A* 搜索代价函数：**

```
f(n) = g(n) + h(n)
g(n) = 从起点到 n 的实际代价
h(n) = 从 n 到终点的启发式估计（曼哈顿距离）
```

#### 2.2.2 参数表（从代码提取真实默认值）

| 参数名 | 默认值 | 范围 | 说明 | 来源 |
|--------|--------|------|------|------|
| `max_iterations` | 3 | 1-10 | 最大重布迭代次数 | LiDAR ISPD'25 |
| `allow_diagonal` | True | bool | 是否允许 8 方向（对角线）布线 | PoLaRIS 默认 |
| `congestion_weight` | 1.0 | 0.1-5.0 | 拥塞感知排序权重 | LiDAR ISPD'25 |
| `loss_db_cm` | 3.0 | 0.5-10.0 | 波导传播损耗 (dB/cm) | SiEPIC EBeam PDK |

#### 2.2.3 调优指南

- **高拥塞电路**：增大 `max_iterations`（5-10），降低 `congestion_weight`（0.5）
- **快速布线**：减少 `max_iterations`（1-2），`allow_diagonal=True` 加速搜索
- **布线失败**：检查画布空间是否充足，或增大网格尺寸

#### 2.2.4 文献来源

- LiDAR ISPD 2025: https://dl.acm.org/doi/pdf/10.1145/3698364.3705355
- LiDAR 2.0 arXiv:2505.17239v2: https://arxiv.org/html/2505.17239v2
- Lillis & Dutt, DAC 1999: https://dl.acm.org/doi/10.1145/309847.309970
- A* 搜索: Hart, Nilsson & Raphael 1968 https://ieeexplore.ieee.org/document/4082128
- SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK

#### 2.2.5 代码位置

`modules/router_advanced/src/polaris_router_advanced/rip_reroute.py` — `RipRerouteConfig` 类
A* 核心：`modules/router_advanced/src/polaris_router_advanced/curvy_astar_core.py`

---

## 第 3 章：物理求解器算法

### 3.1 FDTD（时域有限差分）

#### 3.1.1 算法原理

基于 Yee 1966 交错网格，在时域逐步推进 Maxwell 方程组。

**Yee 网格：** E/H 场空间交错，Ex(i+½,j,k), Ey(i,j+½,k), Ez(i,j,k+½)，H 场在半点。

**更新方程（Maxwell 安培定律 + 法拉第定律）：**

```
∂E/∂t = (1/ε) ∇×H    →  E^{n+1} = Ca·E^n + Cb·(∇×H)
∂H/∂t = -(1/μ) ∇×E   →  H^{n+1} = Da·H^n - Db·(∇×E)

E 场前向差分: (∂f/∂x)_i ≈ (f[i] - f[i-1]) / h
H 场后向差分: (∂f/∂x)_i ≈ (f[i+1] - f[i]) / h
```

**CFL 稳定性条件（Taflove 2005 §4.1）：**

```
Δt ≤ CFL_SAFETY × √(ε_r) / (c × √(1/Δx² + 1/Δy² + 1/Δz²))
CFL_SAFETY = 0.95
```

**Gedney 1996 单轴 PML 吸收边界：**

```
σ(d) = σ_max × (d/L)^m        m=3（梯度幂指数）
σ_max = 0.8×(m+1) / (η₀×Δx×√(ε_r))    （Taflove 2005 §7.6.2 优化值）
Ca = (1 - σΔt/2ε) / (1 + σΔt/2ε)
Cb = (Δt/ε) / (1 + σΔt/2ε)
```

#### 3.1.2 参数表（从代码提取真实默认值）

| 参数名 | 默认值 | 说明 | 来源 |
|--------|--------|------|------|
| `C0` | 2.99792458e8 m/s | 真空光速（NIST CODATA 2018 精确值） | https://physics.nist.gov/cuu/Constants/ |
| `EPS0` | 8.8541878128e-12 F/m | 真空介电常数（NIST CODATA 2018） | https://physics.nist.gov/cuu/Constants/ |
| `MU0` | 1.25663706212e-6 H/m | 真空磁导率（μ₀=4π×10⁻⁷） | https://physics.nist.gov/cuu/Constants/ |
| `SOI_N_SI` | 3.476 | 硅折射率 @1.55μm | Soref 1993 IEEE JQE |
| `SOI_N_SIO2` | 1.444 | 二氧化硅折射率 @1.55μm | Soref 1993 IEEE JQE |
| `SOI_EPS_R_SI` | 12.08 | 硅相对介电常数 (3.476²) | Soref 1993 |
| `SOI_EPS_R_SIO2` | 2.085 | 二氧化硅相对介电常数 (1.444²) | Soref 1993 |
| `CFL_SAFETY` | 0.95 | CFL 安全系数 | Taflove 2005 §4.1 |
| PML `n_layers` | 8 | PML 层数（每侧） | Gedney 1996 |
| PML `m` | 3 | σ 梯度幂指数 | Gedney 1996 |
| PML `sigma_ratio` | 1.0 | σ 比例系数 | Gedney 1996 |
| `GRID_DX_M` | 0.2e-6 (200nm) | 默认网格步长 | Taflove 2005 λ/10 建议 |
| `FDTD_N_STEPS` | 600 | 默认时间步数 | PoLaRIS 默认 |
| `FDTD_DT_SAFETY` | 0.3 | dt 安全系数（dt=0.3×CFL） | Taflove 2005 §4.4 |

#### 3.1.3 调优指南

- **精度要求高**：减小网格步长（λ/20 = 77.5nm），但计算量增 8×（3D）
- **稳定性**：确保 dt ≤ CFL_SAFETY × CFL_max，否则数值发散
- **PML 吸收效果**：n_layers=8-16，m=3（Gedney 1996 建议）
- **波导仿真**：注入 Ey（准 TE 横向分量），避免 Ex（纵向）形成驻波
- **自动微分**（*创新*）：JAX `jax.grad` 自动计算 epsilon_r → FoM 梯度，替代手动伴随方程
- **CPU 强制**：`JAX_PLATFORMS=cpu`（R04 不参与 GPU）

#### 3.1.4 文献来源

- Yee 1966 IEEE TAP https://doi.org/10.1109/TAP.1966.1138693
- Taflove & Hagness 2005 "Computational Electrodynamics: The FDTD Method"
- Mahau 2024 arXiv:2412.12360 "Differentiable FDTD for inverse design" https://arxiv.org/abs/2412.12360
- Gedney 1996 IEEE TAP（单轴各向异性 PML）https://doi.org/10.1109/8.546249
- Berenger 1994 JCP（PML 原始论文）https://doi.org/10.1006/jcph.1994.1159
- Soref 1993 IEEE J. Quantum Electron. https://ieeexplore.ieee.org/document/1148303
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
- Hughes 2018 ACS Photonics（autograd = adjoint）https://arxiv.org/abs/1811.01255

#### 3.1.5 代码位置

`modules/fdtd/src/polaris_fdtd/solver.py` — `YeeGrid3D` 类、`GedneyPML` 类、`DifferentiableFDTD` 类

---

### 3.2 FDE（本征模展开）

#### 3.2.1 算法原理

求解 2D 标量 Helmholtz 方程，得到波导本征模（neff 与模场分布）。

**本征值方程：**

```
∇²E(x,y) + k₀² n²(x,y) E(x,y) = β² E(x,y)

k₀ = 2π/λ    β = k₀·n_eff
导模条件: k₀²·n_clad² < β² < k₀²·n_core²
```

**5 点拉普拉斯离散化（Dirichlet 边界 E=0）：**

```
(E[i+1,j] + E[i-1,j] + E[i,j+1] + E[i,j-1] - 4E[i,j]) / dx² + k₀²n²[i,j]·E[i,j] = β²·E[i,j]

构建稀疏矩阵 M = L_5pt + diag(k₀²n²)，ARPACK Lanczos 求解最大代数特征值（β²）
```

**三重严格过滤伪模（R05 修复）：**

1. β² ∈ (k₀²n_clad², k₀²n_core²)（必要条件）
2. Confinement factor Γ = ∫_core|E|² / ∫_all|E|² > 0.6
3. V 参数 < 2.405 时强制单模（LP11 截止）

**V 参数单模条件：**

```
V = (2π/λ) × (W/2) × √(n_core² - n_clad²) < 2.405
```

#### 3.2.2 参数表（从代码提取真实默认值）

| 参数名 | 默认值 | 说明 | 来源 |
|--------|--------|------|------|
| `width_um` | 0.5 | 波导芯宽度 (μm) | SiEPIC EBeam PDK |
| `height_um` | 0.22 | 波导芯高度 (μm) | SOI 220nm 工艺 |
| `wavelength_um` | 1.55 | 真空波长 (μm) | C 波段 |
| `n_core` | 3.476 | 芯区折射率（Si） | Soref 1993 |
| `n_clad` | 1.444 | 包层折射率（SiO₂） | Soref 1993 |
| `n_modes` | 4 | 求解模式数 | PoLaRIS 默认 |
| `dx_um` | 0.02 | 网格步长 (μm) | PoLaRIS 默认（提高分辨率避免伪模） |
| `pad_um` | 1.0 | 包层 padding (μm，每侧) | PoLaRIS 默认 |
| `CONFINEMENT_THRESHOLD` | 0.6 | 导模 confinement 阈值 | Snyder & Love 1983 §13.5 |
| `V_CUTOFF_SINGLE_MODE` | 2.405 | V 参数 LP11 截止值 | Snyder & Love 1983 §13.5 |

#### 3.2.3 调优指南

- **高阶模**：增大 `n_modes`（8+），减小 `dx_um`（0.01）
- **伪模过滤**：确保 `CONFINEMENT_THRESHOLD=0.6`，避免泄漏模误判
- **单模波导**：V < 2.405 时自动只保留基模
- **SOI 500nm 条形波导**：TE0 Γ≈0.77，TM0 Γ≈0.57（近 cutoff）

#### 3.2.4 文献来源

- Smit & van Dam 1996 IEEE/OSA JLT https://opg.optica.org/jlt/abstract.cfm?uri=jlt-14-7-1746
- Silvester & Ferrari 1996 Cambridge（FD/FEM 本征模求解）
- Soref 1993 IEEE JQE https://ieeexplore.ieee.org/document/1148303
- scipy.sparse.linalg.eigsh https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html
- Snyder & Love 1983 "Optical Waveguide Theory" §13.5 https://link.springer.com/book/10.1007/978-94-009-6875-2
- Saleh & Teich 2019 "Fundamentals of Photonics" 3rd ed.
- Lumerical MODE FDE https://optics.ansys.com/hc/en-us/articles/360034902413

#### 3.2.5 代码位置

`modules/fde/src/polaris_fde/solver.py` — `solve_modes()` 函数

---

### 3.3 FDFD（频域有限差分）

#### 3.3.1 算法原理

在频域求解 Helmholtz 方程，构建稀疏线性系统直接求解稳态场分布。

**方程：**

```
∇×(1/μ)∇×E - k₀²εE = 0

离散化为: A·E = b
A = ∇² + diag(k₀²n²)    （5 点拉普拉斯 + 折射率项）
b = 高斯线源（z=0 处横向高斯分布）
```

使用 `scipy.sparse.linalg.spsolve` 直接求解稀疏线性系统。

#### 3.3.2 参数表（从代码提取真实默认值）

| 参数名 | 默认值 | 说明 | 来源 |
|--------|--------|------|------|
| `width_um` | 0.5 | 波导芯宽度 (μm) | SiEPIC EBeam PDK |
| `length_um` | 10.0 | 传播长度 (μm) | PoLaRIS 默认 |
| `wavelength_um` | 1.55 | 波长 (μm) | C 波段 |
| `n_core` | 3.476 | 芯区折射率（Si） | Soref 1993 |
| `n_clad` | 1.444 | 包层折射率（SiO₂） | Soref 1993 |
| `dx_um` | 0.05 | 网格步长 (μm) | PoLaRIS 默认 |
| `pad_um` | 1.5 | 包层 padding (μm) | PoLaRIS 默认 |

#### 3.3.3 调优指南

- **精度**：减小 `dx_um`（0.02），但内存需求增 6×（2D）
- **长波导**：增大 `length_um`，但稀疏矩阵维度增长
- **传输率提取**：输出端 z=L 处功率 / 输入端功率

#### 3.3.4 文献来源

- Taflove & Hagness 2005 "Computational Electrodynamics" §5（FDFD）
- Shin & Fan, Opt. Express 2014 https://opg.optica.org/oe/fulltext.cfm?uri=oe-22-5-5230
- scipy.sparse.linalg.spsolve https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.spsolve.html
- Lumerical FDFD https://optics.ansys.com/hc/en-us/articles/360034902393
- Soref 1993 IEEE JQE https://ieeexplore.ieee.org/document/1148303
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/

#### 3.3.5 代码位置

`modules/fdfd/src/polaris_fdfd/solver.py` — `solve_fdfd()` 函数

---

### 3.4 EME（传输矩阵法）

#### 3.4.1 算法原理

将光子结构沿传播方向 z 切片为多个均匀段，每段求解本地本征模，界面用模式匹配计算透射/反射，段内相位传播，级联 S 矩阵。

**段内相位传播：**

```
P = diag(exp(j·β_i·L))    （前向）/ diag(exp(-j·β_i·L))    （后向）
```

**界面模式匹配（E/H 连续性 + 单模 Galerkin 投影，*创新*）：**

```
场重叠: P = ∫ E_a · E_b* dx    （∫|E|²dx=1 归一化）
TE 导纳: Y = β/ωμ
反射: r = (β_a - β_b) / (β_a + β_b)    （阻抗失配）
透射: t = 2·β_a / (β_a + β_b) · P    （β 匹配 × 场重叠）
```

**Redheffer 星积级联：**

```
S_total = S_1 ⊗ P_1 ⊗ S_2 ⊗ ... ⊗ S_N

denom = 1 - S1[1,1]·S2[0,0]
S11 = S1[0,0] + S1[0,1]·S2[0,0]·S1[1,0] / denom
S12 = S1[0,1]·S2[0,1] / denom
S21 = S2[1,0]·S1[1,0] / denom
S22 = S2[1,1] + S2[1,0]·S1[1,1]·S2[0,1] / denom
```

#### 3.4.2 参数表（从代码提取真实默认值）

| 参数名 | 默认值 | 说明 | 来源 |
|--------|--------|------|------|
| `wavelength_um` | 1.55 | 波长 (μm) | C 波段 |
| `n_modes_per_section` | 2 | 每段求解模式数（仅取基模单模级联） | PoLaRIS 默认 |
| `dx_um` | 0.01 | 横向网格步长 (μm) | PoLaRIS 默认 |
| `pad_um` | 1.0 | 包层 padding (μm) | PoLaRIS 默认 |

#### 3.4.3 调优指南

- **多模器件**：增大 `n_modes_per_section`（4+），但计算量增长
- **统一窗口**：各段强制共用同一窗口（max_width + 2×pad），保证模式匹配
- **级联稳定性**：Redheffer 分母为零时 raise（级联奇异）

#### 3.4.4 文献来源

- Smit & van Dam 1996 IEEE/OSA JLT https://opg.optica.org/jlt/abstract.cfm?uri=jlt-14-7-1746
- Bienstman 2001 Ghent PhD https://www.photonics.intec.ugent.be/publications/PhD_Bienstman.pdf
- Lumerical EME https://optics.ansys.com/hc/en-us/articles/360034902433
- Collin 2001 "Foundations for Microwave Engineering" §5.1 https://ieeexplore.ieee.org/book/5263073
- Marcuse 1981 "Light Transmission Optics" §8.5 https://onlinelibrary.wiley.com/doi/book/10.1002/9783527619742
- scipy.sparse.linalg.eigsh https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html

#### 3.4.5 代码位置

`modules/eme/src/polaris_eme/solver.py` — `solve_eme()` 函数、`redheffer_star()` 函数

---

### 3.5 BPM（光束传播法）

#### 3.5.1 算法原理

使用 Crank-Nicolson 隐式格式求解抛物波动方程（慢变包络近似）。

**抛物波动方程：**

```
∂E/∂z = (j/(2k₀n₀)) ∂²E/∂x² + j·k₀(n²(x) - n₀²)/(2n₀) · E

n₀ = 参考折射率（取包层 n_clad）
k₀ = 2π/λ
```

**Crank-Nicolson 隐式格式：**

```
(I - dz·H/2) E^{n+1} = (I + dz·H/2) E^n

H = (j/(2k₀n₀)) L_x + j·k₀(n²-n₀²)/(2n₀) I

LHS 和 RHS 均为三对角矩阵，scipy.linalg.solve_banded O(N) 求解
```

**Symmetric split-step 物理损耗（RP Photonics 标准方案）：**

```
E^{n+1} = exp(-α·dz/2) · CN(E^n) · exp(-α·dz/2)    [O(dz³)]

α(x) = Soref 芯区材料吸收 + CAP 边界渐变衰减
```

#### 3.5.2 参数表（从代码提取真实默认值）

| 参数名 | 默认值 | 说明 | 来源 |
|--------|--------|------|------|
| `width_um` | 0.5 | 波导芯宽度 (μm) | SiEPIC EBeam PDK |
| `length_um` | 50.0 | 传播长度 (μm) | PoLaRIS 默认 |
| `wavelength_um` | 1.55 | 波长 (μm) | C 波段 |
| `n_core` | 3.476 | 芯区折射率（Si） | Soref 1993 |
| `n_clad` | 1.444 | 包层折射率（SiO₂） | Soref 1993 |
| `dz_um` | 0.1 | 纵向步长 (μm) | PoLaRIS 默认（dz << λ） |
| `dx_um` | 0.01 | 横向步长 (μm) | PoLaRIS 默认 |
| `pad_um` | 2.0 | 包层 padding (μm) | PoLaRIS 默认 |
| `LOSS_DB_PER_CM_SI` | 3.0 | SOI 传播损耗 (dB/cm) | Soref 1993 Proc. IEEE 81(12) |
| `CAP_STRENGTH` | 0.5 | CAP 边界最大功率衰减系数 (μm⁻¹) | Hadley 1992 Opt. Lett. |
| `CAP_FRACTION` | 0.3 | pad 外侧作为 CAP 的比例 | Hadley 1992 Opt. Lett. |

#### 3.5.3 调优指南

- **无条件稳定**：CN 格式任意 dz 都不发散，但精度要求 dz << λ（典型 0.1μm）
- **长波导**：增大 `length_um`，步数 nz = length_um / dz_um
- **CAP 边界**：确保 `CAP_STRENGTH > 0`，避免 Dirichlet 反射导致 transmission≡1
- **损耗校准**：`LOSS_DB_PER_CM_SI=3.0` 为 SOI 上界，实测 0.5-10 dB/cm

#### 3.5.4 文献来源

- Feit & Fleck 1978 Appl. Opt. https://opg.optica.org/ao/abstract.cfm?uri=ao-17-24-3990
- Crank & Nicolson 1947 Math. Proc. Cambridge
- Chung & Dagli 1990 IEEE JQE（ADI）https://ieeexplore.ieee.org/document/59635
- Hadley 1992 Opt. Lett. 17(10) 726（TBC/CAP 边界）https://opg.optica.org/ol/abstract.cfm?uri=ol-17-10-726
- Soref 1993 Proc. IEEE 81(12) https://ieeexplore.ieee.org/document/249720
- Rickman & Reed 1994 Electron. Lett. 30(10) https://digital-library.theiet.org/doi/abs/10.1049/el:19931356
- Grillot 2006 JLT 24(2) https://opg.optica.org/jlt/abstract.cfm?uri=jlt-24-2-891
- RP Photonics BPM https://www.rp-photonics.com/numerical_beam_propagation.html
- scipy.linalg.solve_banded https://docs.scipy.org/doc/scipy/reference/generated/scipy.linalg.solve_banded.html

#### 3.5.5 代码位置

`modules/bpm/src/polaris_bpm/solver.py` — `solve_bpm()` 函数、`build_cn_matrices()` 函数

---

### 3.6 RCWA（严格耦合波分析）

#### 3.6.1 算法原理

通过傅里叶展开求解周期性光栅结构的衍射问题。

**傅里叶展开：**

```
E(x,z) = Σ_R S_R · exp(i·k_x·x + i·k_{z,R}·z)

k_x = (2π/Λ)·m    m = 0, ±1, ±2, ...    （Λ 为光栅周期）
k_{z,R} = √(k₀²n² - k_x²)
```

在每一均匀层内构建本征值问题，界面匹配边界条件，级联传输矩阵。

#### 3.6.2 参数表

| 参数名 | 默认值 | 说明 | 来源 |
|--------|--------|------|------|
| 傅里叶谐波数 | 5-15 | 截断阶数（越多精度越高） | Moharam & Gaylord 1981 |
| 光栅周期 | 器件相关 | Λ (μm) | 器件定义 |
| 介质层数 | 器件相关 | 均匀层数 | 器件定义 |

#### 3.6.3 文献来源

- Moharam & Gaylord 1981 JOSA https://doi.org/10.1364/JOSA.71.000811
- Li 1996 JOSA A（傅里叶因子化规则改进收敛性）
- Lumerical RCWA https://optics.ansys.com/hc/en-us/articles/360034902433

#### 3.6.4 代码位置

`2026-2028开发计划/功能清单与实现/A01-RCWA严格耦合波分析.md` — 算法规格文档

---

## 第 4 章：逆向设计算法

### 4.1 JAX 伴随优化（adjoint）

#### 4.1.1 算法原理

*创新*：用 JAX `jax.grad` 自动微分计算 FoM 对设计参数的梯度，替代 lumopt 手动推导伴随方程。

**目标函数（归一化传输率）：**

```
FoM(width) = max(|monitor_signal|) / max(|source_waveform|)
FoM ∈ [0, 1]    （归一化，lumopt FoM 惯例）
```

**梯度计算（*创新*，自动微分替代手动伴随方程）：**

```
dFoM/d(width) = jax.grad(FoM)(width)

底层逻辑: 反向模式自动微分（reverse-mode AD）= 伴随方法
（Giles & Pierce 2000 SIAM Review 数学等价）
梯度计算开销与参数数无关（链式法则 + 一次反向）
```

**heavy-ball 动量优化器（Polyak 1964）：**

```
v_{t+1} = μ·v_t + lr·clip(grad, [-1, 1])
width_{t+1} = width_t + v_{t+1}

梯度裁剪 [-1, 1] 防 NaN 爆炸
```

#### 4.1.2 参数表（从代码提取真实默认值）

| 参数名 | 默认值 | 说明 | 来源 |
|--------|--------|------|------|
| `GRID_NX` | 24 | FDTD 网格 x 方向点数 | Taflove 2005 §4.1 |
| `GRID_NY` | 12 | FDTD 网格 y 方向点数 | Taflove 2005 §4.1 |
| `GRID_NZ` | 8 | FDTD 网格 z 方向点数 | Taflove 2005 §4.1 |
| `GRID_DX_M` | 0.2e-6 (200nm) | 网格步长 (m) | Taflove 2005 λ/10 建议 |
| `PML_N_LAYERS` | 2 | PML 层数（每侧） | Gedney 1996 |
| `FDTD_DT_SAFETY` | 0.3 | dt 安全系数（dt=0.3×CFL） | Taflove 2005 §4.4 |
| `FDTD_N_STEPS` | 600 | 时间步数 | PoLaRIS 默认 |
| `N_ITERATIONS` | 50 | 优化迭代次数 | Jensen & Sigmund 2011 §3 |
| `LEARNING_RATE` | 0.5 | 学习率 | Kingma & Ba 2014 |
| `MOMENTUM` | 0.3 | 动量系数（heavy-ball） | Polyak 1964；Smith 2017 arXiv:1711.00489 |
| `INITIAL_WIDTH_PIXELS` | 2.0 | 初始波导半宽度（像素） | PoLaRIS 默认 |
| `TARGET_WAVELENGTH_UM` | 1.55 | 目标波长 (μm) | C 波段 |
| `EPS_R_SI` | 12.08 | 硅相对介电常数 (3.476²) | Soref 1993 |
| `EPS_R_SIO2` | 2.085 | 二氧化硅相对介电常数 (1.444²) | Soref 1993 |

#### 4.1.3 真实 benchmark 结果

| 器件 | 优化参数 | FoM 改善 | 关键指标 | 来源文件 |
|------|---------|----------|----------|----------|
| 硅波导宽度 | width (像素) | +14.72 dB (50步) | 归一化传输率提升 | `modules/inverse/src/polaris_inverse/adjoint.py` |
| MMI 1x2 分束器 | [W, L] (μm) | 16.59 dB | IL=0.001dB, 不均匀性=0.0005dB | `showcase.py` |
| WDM 滤波器 | [g, L] (μm) | 10.06 dB | 带宽=28.34nm, 隔离度=60dB | `showcase.py` |
| Y 分支 | [θ] (rad) | 10.92 dB | IL=0.016dB | `showcase.py` |

**3/3 showcase 器件 FoM 改善 ≥ 10 dB，全部物理指标达标。**

#### 4.1.4 调优指南

- **动量选择**：200nm 网格下 MOMENTUM=0.3（非 0.9），适配嘈杂 FoM 景观
  - m=0.9 时有效步长 ≈ lr/(1-m) = 5.0（严重过冲）
  - m=0.3 时有效步长 ≈ 0.71（稳定收敛）
- **网格精度**：200nm 网格 = 7.75 点/λ，低于 Taflove λ/10 建议，数值色散较大但优化方向有效
- **迭代次数**：50 次为最小可收敛值，lumopt 商业工具通常 50-200 次
- **梯度裁剪**：归一化后梯度 O(0.01-0.1)，裁剪 [-1,1] 仅作安全网
- **best-checkpoint**：迭代中追踪历史最优 FoM（非凸优化标准做法）

#### 4.1.5 文献来源

- Hughes 2018 ACS Photonics（autograd = adjoint）https://arxiv.org/abs/1811.01255
- Lalau-Keraly 2013 Opt. Express https://doi.org/10.1364/OE.21.0021693
- Mahau 2024 arXiv:2412.12360 https://arxiv.org/abs/2412.12360
- Polyak 1964 "Some methods of speeding up the convergence of iteration methods"
- Jensen & Sigmund 2011 "Topology optimization for nano-photonics" https://doi.org/10.1002/lpor.201000014
- lumopt: https://github.com/chriskeraly/lumopt
- Giles & Pierce 2000 SIAM Review "An Introduction to the Adjoint Approach"
- Smith 2017 "Don't Decay the Learning Rate, Increase the Batch Size" arXiv:1711.00489

#### 4.1.6 代码位置

`modules/inverse/src/polaris_inverse/adjoint.py` — `run_adjoint_optimization()` 函数
Showcase：`modules/inverse/src/polaris_inverse/showcase.py`

---

### 4.2 拓扑优化（Topology Optimization）

#### 4.2.1 算法原理

使用密度法 + 灵敏度滤波 + Heaviside 投影实现可制造二值化版图。

**密度法参数化：**

```
ρ_raw → sigmoid → ρ ∈ [0, 1]
```

**SIMP 插值（Solid Isotropic Material with Penalization）：**

```
ε(ρ) = ε_bg + (ε_core - ε_bg) × ρ^p
p = 3.0    （SIMP 惩罚因子，推动 0-1 二值化）
```

**Heaviside 投影（Wang 2011 robust formulation）：**

```
ρ̃ = [tanh(β·η) + tanh(β·(ρ-η))] / [tanh(β·η) + tanh(β·(1-η))]
β 退火: 1 → 50    （逐步锐化边界）
```

**灵敏度滤波（Sigmund 2007，消除棋盘格）：**

```
/filter_radius = 2 像素（锥形滤波核）
```

#### 4.2.2 参数表（从代码提取真实默认值）

| 参数名 | 默认值 | 说明 | 来源 |
|--------|--------|------|------|
| `grid_size` | 50 | 水平集网格分辨率 | PoLaRIS 默认 |
| `max_iterations` | 50 | 最大迭代次数 | 拓扑优化默认 |
| `learning_rate` | 0.1 | 水平集演化学习率 | 水平集方法默认 |
| `convergence_threshold` | 1e-6 | 收敛阈值 | PoLaRIS 默认 |
| `smooth_sigma` | 1.0 | 水平集平滑核标准差 | Sigmund 2007 |
| `min_feature_size` | 2.0 | 最小特征尺寸约束 (DRC) | 制造约束 |
| `SIMP_PENALTY_P` | 3.0 | SIMP 惩罚因子 | Sigmund 2001 |
| `PROJECTION_BETA` | 退火 1→50 | Heaviside 投影锐化参数 | Wang 2011 |
| `PROJECTION_ETA` | 0.5 | Heaviside 投影阈值 | Wang 2011 |
| `FILTER_RADIUS_PX` | 2 | 灵敏度滤波半径（像素） | Sigmund 2007 |

#### 4.2.3 文献来源

- Jensen & Sigmund 2011 "Topology optimization for nano-photonics" https://doi.org/10.1002/lpor.201000014
- Sigmund 2001 (99-line code) https://doi.org/10.1007/s00158-005-0543-x
- Wang, Lazarov & Sigmund 2011 (projection/robust) https://doi.org/10.1007/s00158-010-0602-y
- Bourdin 2001 (filters in TO) https://doi.org/10.1002/nme.116
- Wang 2005 (conic filter) https://doi.org/10.1007/s00158-004-0512-9
- Piggott 2017 Nature Photonics https://www.nature.com/articles/nphoton.2017.102

#### 4.2.4 代码位置

`modules/optimizer/src/polaris_optimizer/topology.py` — `TopologyOptimizer` 类、`TopologyConfig` 类
`modules/inverse/src/polaris_inverse/topology_opt.py` — 密度法实现

---

### 4.3 Level-Set 演化

#### 4.3.1 算法原理

用隐式函数 φ(x,y) 表示器件边界，通过 Hamilton-Jacobi 方程演化形状。

**水平集表示：**

```
φ(x,y) > 0: 材料区域（如硅）
φ(x,y) < 0: 背景区域（如空气/二氧化硅）
φ(x,y) = 0: 材料边界
```

**Hamilton-Jacobi 方程：**

```
∂φ/∂t + H(φ, ∇φ) = 0
H = v(x,y) · |∇φ|    （速度场 Hamiltonian，由 adjoint 梯度决定）
```

**Lax-Friedrichs 数值 Hamiltonian：**

```
Ĥ(a⁻, a⁺, b⁻, b⁺) = H((a⁻+a⁺)/2, (b⁻+b⁺)/2) - αx/2·(a⁺-a⁻) - αy/2·(b⁺-b⁻)
```

**离散格式：** ENO（3阶）/ WENO（5阶）/ UPWIND（1阶）

#### 4.3.2 参数表（从代码提取真实默认值）

| 参数名 | 默认值 | 说明 | 来源 |
|--------|--------|------|------|
| `DT_LEVELSET` | 0.01 | Level-set 时间步长 | Osher & Sethian 1988 |
| `HEAVISIDE_EPS` | 1e-3 | Heaviside 正则化参数 | PoLaRIS 默认 |
| `REINIT_INTERVAL` | 10 | 重新初始化间隔（步） | Osher & Sethian 1988 |
| `REINIT_N_STEPS` | 5 | 重新初始化步数 | Osher & Sethian 1988 |
| `LEARNING_RATE` | 0.5 | Level-set 演化学习率 | PoLaRIS 默认 |
| `MOMENTUM` | 0.3 | 动量系数 | Polyak 1964 |
| `N_ITERATIONS` | 50 | 迭代次数 | PoLaRIS 默认 |
| CFL 时间步 | 自动计算 | CFL 稳定性条件 | Osher & Shu 1991 |

#### 4.3.3 文献来源

- Osher & Sethian 1988 JCP https://doi.org/10.1016/S0021-9991(88)80002-2
- Osher & Shu 1991 SIAM J. Numer. Anal. https://doi.org/10.1137/0728049
- Jiang & Peng 2000 SIAM J. Sci. Comput. https://doi.org/10.1137/S1064827597324553
- Osher & Fedkiw 2001 JCP https://doi.org/10.1006/jcph.2000.6636
- Shu 2009 SIAM Review 51(1) https://doi.org/10.1137/070679065

#### 4.3.4 代码位置

`modules/optimizer/src/polaris_optimizer/level_set.py` — `HJSolver` 类、`HJSolverConfig` 类
`modules/inverse/src/polaris_inverse/level_set.py` — Level-set 逆向设计实现

---

## 第 5 章：优化器算法

PoLaRIS 提供 12 种光子学优化器，统一接口位于 `modules/optimizer/src/polaris_optimizer/`。

### 5.1 L-BFGS（拟牛顿法）

#### 算法原理

L-BFGS（Limited-memory BFGS）只保存最近 m 次 (s, y) 对，两循环递归计算搜索方向。

```
s_k = x_{k+1} - x_k    （参数差）
y_k = ∇f_{k+1} - ∇f_k  （梯度差）
搜索方向: p = H · g    （逆 Hessian 近似 H，两循环递归）
线搜索: Wolfe 条件（c1 充分下降 + c2 曲率条件）
```

#### 参数表

| 参数名 | 默认值 | 说明 | 来源 |
|--------|--------|------|------|
| `max_iterations` | 100 | 最大迭代次数 | lumopt 默认 |
| `memory_size` | 10 | 历史记忆长度 m | Nocedal 推荐 3-20 |
| `convergence_threshold` | 1e-5 | 收敛阈值（梯度范数） | Nocedal & Wright 2006 |
| `wolfe_c1` | 1e-4 | Wolfe 充分下降条件 | Nocedal 推荐 |
| `wolfe_c2` | 0.9 | Wolfe 曲率条件 | Nocedal 推荐 |
| `line_search_max_iter` | 20 | 线搜索最大迭代 | PoLaRIS 默认 |
| `line_search_init` | 1.0 | 初始步长 | PoLaRIS 默认 |

**适用场景**：局部二阶优化，收敛速度快于 Adam。适合 adjoint 逆向设计。
**收敛性**：超线性收敛（拟牛顿法特性）。

**文献**：Liu & Nocedal 1989 https://doi.org/10.1007/BF01589116；Nocedal & Wright 2006 https://doi.org/10.1007/978-0-387-40065-5

**代码位置**：`modules/optimizer/src/polaris_optimizer/lbfgs.py`

---

### 5.2 CMA-ES（协方差矩阵自适应进化策略）

#### 算法原理

全局优化策略，自适应更新协方差矩阵引导搜索方向。

```
x_{k+1} = m_k + σ_k · N(0, C_k)    （采样）
m_{k+1} = m_k + c_m · Σ w_i · (x_{i:λ} - m_k)    （均值更新）
C_{k+1} = 协方差矩阵更新（rank-μ + rank-one）    （协方差自适应）
σ_{k+1} = 步长控制（CSA 路径累积）    （步长自适应）
```

#### 参数表

| 参数名 | 默认值 | 说明 | 来源 |
|--------|--------|------|------|
| `population_size` | 自动计算 | 种群大小（4+3ln(n)） | Hansen 2001 |
| `sigma_init` | 0.5 | 初始步长 | Hansen 2001 |
| `max_iterations` | 1000 | 最大迭代次数 | PoLaRIS 默认 |
| `convergence_threshold` | 1e-8 | 收敛阈值 | Hansen 2001 |

**适用场景**：全局优化，跳出局部最优。适合非凸光子器件参数空间。
**收敛性**：在凸问题上线性收敛，非凸问题上表现鲁棒。

**文献**：Hansen & Ostermeier 2001 https://doi.org/10.1162/106365601750190398

**代码位置**：`modules/optimizer/src/polaris_optimizer/global_opt.py`

---

### 5.3 NSGA-II（多目标进化算法）

#### 算法原理

快速非支配排序 + 拥挤距离选择，处理 ≤3 目标的 Pareto 前沿。

```
1. 初始化种群 P（N 个个体）
2. 快速非支配排序 → 分层 F1, F2, ...
3. 计算拥挤距离
4. 锦标赛选择 + SBX 交叉 + 多项式变异 → 子代 Q
5. P ∪ Q → 非支配排序 → 选前 N 个 → 新 P
6. 重复 2-5 直到收敛
```

**非支配排序**：解 a 支配解 b 当且仅当 a 在所有目标上不劣于 b 且至少一个目标严格更优。

**SBX 交叉（Simulated Binary Crossover）：**

```
c₁ = 0.5·[(1-β)·p₁ + (1+β)·p₂]
c₂ = 0.5·[(1+β)·p₁ + (1-β)·p₂]
β 由分布指数 eta 控制
```

#### 参数表

| 参数名 | 默认值 | 说明 | 来源 |
|--------|--------|------|------|
| `population_size` | 100 | 种群大小 | Deb 2002 建议 100-200 |
| `max_generations` | 200 | 最大代数 | Deb 2002 |
| `crossover_prob` | 0.9 | 交叉概率 | Deb 2002 |
| `mutation_prob` | 0.1 | 变异概率 | Deb 2002（1/n_params） |
| `crossover_eta` | 20.0 | SBX 分布指数 | Deb 2002 |
| `mutation_eta` | 20.0 | 多项式变异分布指数 | Deb 2002 |

**适用场景**：多目标优化（如透过率 vs 带宽 vs 损耗），≤3 目标。

**文献**：Deb et al. 2002 https://doi.org/10.1109/4235.996017；Deb & Agrawal 1995 SBX https://complex-systems.com/abstracts/vol09_i02_a02/

**代码位置**：`modules/optimizer/src/polaris_optimizer/nsga.py`

---

### 5.4 NSGA-III（参考点多目标进化）

#### 算法原理

用参考点机制（Das-Dennis）替代拥挤距离，处理 >3 目标时多样性保持更强。

```
参考点生成: Das-Dennis 在超平面上均匀分布
小生境选择: 每个参考点维护一个小生境，保持解的多样性
```

#### 参数表

与 NSGA-II 类似，增加参考点参数：

| 参数名 | 默认值 | 说明 | 来源 |
|--------|--------|------|------|
| `n_reference_points` | 自动计算 | 参考点数（Das-Dennis） | Deb & Jain 2014 |
| `n_objectives` | ≥4 | 目标数 | Deb & Jain 2014 |

**适用场景**：多目标优化，>3 目标（如同时优化透过率、带宽、损耗、面积）。

**文献**：Deb & Jain 2014 https://doi.org/10.1109/TEVC.2013.2281535；Das & Dennis 1998 https://doi.org/10.1137/S1052623496307510

**代码位置**：`modules/optimizer/src/polaris_optimizer/nsga.py`

---

### 5.5 PSO（粒子群优化）

#### 算法原理

群体智能搜索，每个粒子根据自身历史最优和群体历史最优更新速度和位置。

```
v_{t+1} = w·v_t + c1·r1·(pbest - x_t) + c2·r2·(gbest - x_t)
x_{t+1} = x_t + v_{t+1}
```

#### 参数表

| 参数名 | 默认值 | 说明 | 来源 |
|--------|--------|------|------|
| `num_particles` | 30 | 粒子数量 | Kennedy & Eberhart 1995 |
| `inertia_weight` | 0.7 | 惯性权重 w | Kennedy & Eberhart 1995 |
| `cognitive_coef` | 1.5 | 认知系数 c1（自我学习） | Kennedy & Eberhart 1995 |
| `social_coef` | 1.5 | 社会系数 c2（群体学习） | Kennedy & Eberhart 1995 |
| `max_iterations` | 100 | 最大迭代次数 | PoLaRIS 默认 |
| `convergence_threshold` | 1e-6 | 收敛阈值 | PoLaRIS 默认 |
| `seed` | 42 | 随机种子 | PoLaRIS 默认 |

**适用场景**：全局优化，简单高效。适合连续参数空间。
**收敛性**：w < 1 时收敛，w=0.7 为经验最优。

**文献**：Kennedy & Eberhart 1995 https://ieeexplore.ieee.org/document/488968

**代码位置**：`modules/optimizer/src/polaris_optimizer/global_opt.py`

---

### 5.6 Topology（拓扑优化）

#### 算法原理

基于水平集方法的拓扑优化，通过演化 φ(x,y) 改变器件形状（详见 §4.2）。

#### 参数表

| 参数名 | 默认值 | 说明 |
|--------|--------|------|
| `grid_size` | 50 | 水平集网格分辨率 |
| `max_iterations` | 50 | 最大迭代次数 |
| `learning_rate` | 0.1 | 水平集演化学习率 |
| `smooth_sigma` | 1.0 | 平滑核标准差 |
| `min_feature_size` | 2.0 | 最小特征尺寸约束 |

**适用场景**：任意形状逆向设计，超越参数化方法。

**文献**：Osher & Sethian 1988 https://doi.org/10.1016/S0021-9991(88)80002-2；Jensen & Sigmund 2011 https://doi.org/10.1364/OE.19.020152

**代码位置**：`modules/optimizer/src/polaris_optimizer/topology.py`

---

### 5.7 HJ（Hamilton-Jacobi 求解器）

#### 算法原理

高阶 Hamilton-Jacobi 方程求解器，替代一阶显式 Euler，支持 ENO/WENO/UPWIND 格式（详见 §4.3）。

#### 参数表

| 参数名 | 默认值 | 说明 |
|--------|--------|------|
| `HJScheme` | WENO | 离散格式（ENO/WENO/UPWIND） |
| `dx` | 1.0 | x 方向步长 |
| `dy` | 1.0 | y 方向步长 |
| CFL 时间步 | 自动计算 | 稳定性条件 |

**适用场景**：水平集演化的高精度数值求解。

**文献**：Osher & Shu 1991 https://doi.org/10.1137/0728049；Jiang & Peng 2000 https://doi.org/10.1137/S1064827597324553

**代码位置**：`modules/optimizer/src/polaris_optimizer/level_set.py`

---

### 5.8 Robust（鲁棒优化）

#### 算法原理

考虑制造公差的鲁棒性优化，蒙特卡洛采样评估公差扰动下的性能。

```
worst-case: max(min_fom(perturbed_params))
mean-case:  max(mean_fom(perturbed_params))
mean-std:   max(mean_fom - std_fom)
```

#### 参数表

| 参数名 | 默认值 | 说明 | 来源 |
|--------|--------|------|------|
| `tol_type` | GAUSSIAN | 公差类型（GAUSSIAN/UNIFORM） | Wang 2018 |
| `relative_std` | 0.05 | 相对标准差（5%） | Wang 2018 |
| `absolute_std` | 0.0 | 绝对标准差 | PoLaRIS 默认 |
| `n_samples` | 50 | 蒙特卡洛采样数 | PoLaRIS 默认 |

**适用场景**：优化后器件在实际制造后仍能保持性能。

**文献**：Wang et al. 2018 Opt. Express 26(18) https://doi.org/10.1364/OE.26.023273；Alexander et al. 2021 Phys. Rev. Applied https://doi.org/10.1103/PhysRevApplied.16.014013

**代码位置**：`modules/optimizer/src/polaris_optimizer/robust.py`

---

### 5.9 Shape Adjoint（形状伴随）

#### 算法原理

基于 adjoint method 的光子器件参数优化，lumopt 风格。

```
1. 正向仿真: F(θ) = ∫ field(x,θ) · objective(x) dx
2. 伴随仿真: 注入伴随场 λ(x) = objective(x)
3. 梯度: dF/dθ = ∫ λ(x) · dField/dθ(x) dx
   只需 2 次仿真（正向+伴随），与参数数无关
```

#### 参数表

| 参数名 | 默认值 | 说明 | 来源 |
|--------|--------|------|------|
| `max_iterations` | 100 | 最大迭代次数 | lumopt 默认 |
| `learning_rate` | 0.01 | Adam 学习率 | lumopt 默认 |
| `convergence_threshold` | 1e-6 | 收敛阈值 | PoLaRIS 默认 |
| `min_feature_size_um` | 0.1 | 最小特征尺寸 (μm) | DRC 约束 |
| `symmetry` | "none" | 对称约束（none/x/y/xy） | PoLaRIS 默认 |
| `backend` | ANALYTICAL | 优化后端（MEEP/TIDY3D/ANALYTICAL） | lumopt 风格 |

**适用场景**：参数化几何优化，需 2 次仿真即可得到全参数梯度。

**文献**：lumopt https://github.com/chriskeraly/lumopt；Keraly et al. 2023 https://www.nature.com/articles/s41377-023-01196-8

**代码位置**：`modules/optimizer/src/polaris_optimizer/shape_adjoint.py`

---

### 5.10 Density Adjoint（密度伴随）

#### 算法原理

*创新*：JAX autograd + 伴随方法共生 + 密度法二值化。

```
1. 密度参数化: ρ_raw → sigmoid → [0,1] 密度
2. 锥形滤波: 消除棋盘格（Wang 2005）
3. tanh-sigmoid 投影: 保证 ρ=0→0, ρ=1→1（β 退火 1→50）
4. 三层投影: eroded/nominal/dilated（Wang 2011 robust）
5. 可微仿真: JAX 角谱法 + 模式重叠积分
6. jax.grad 自动求梯度（= 伴随方法解析梯度，Hughes 2018 证明）
```

**物理模型（标量衍射理论）：**

```
E₁ = E_in · exp(i·φ_max·ρ)    φ_max = 2π·Δn·Δz/λ
FoM = |⟨E_out, E_target⟩|² / (‖E_out‖²·‖E_target‖²)
```

**适用场景**：像素化拓扑优化，二值化版图生成。
**收敛性**：JAX autograd 梯度 = 伴随方法解析梯度（O(1) 复杂度，对比有限差分 O(n) 加速 5000×）。

**文献**：Sigmund 2001 https://doi.org/10.1007/s00158-005-0543-x；Wang 2011 https://doi.org/10.1007/s00158-010-0602-y；Piggott 2017 https://www.nature.com/articles/nphoton.2017.102；Hughes 2018 https://arxiv.org/abs/1811.01255

**代码位置**：`modules/optimizer/src/polaris_optimizer/density_adjoint.py`

---

### 5.11 Feedback Adapt（反馈适配）

#### 算法原理

将仿真约束违规转化为布局布线调整建议，指导下一轮优化。

```
Violation → ViolationType 分类 → PlacementHint / RoutingHint → 调整建议
```

**违规类型**（17 种）：BEND_RADIUS / SPACING / INSERTION_LOSS / CROSSTALK / CROSSING / OVERLAP / THERMAL / MIN_WIDTH / COUPLING_GAP / MIN_LENGTH / MAX_LENGTH / MIN_AREA / ENCLOSURE / NOTCH / PORT_CONNECTIVITY / PIN_MATCH / LAYER_DENSITY

**适用场景**：DRC/LVS 违规驱动的迭代布局布线优化。

**文献**：Apollo arXiv 2025 https://arxiv.org/html/2504.18813v1；ICLR'26 专家 RL https://openreview.net/forum?id=yqvNwfxRR6

**代码位置**：`modules/optimizer/src/polaris_optimizer/feedback.py`

---

### 5.12 Global Unified（全局统一）

#### 算法原理

PSO + CMA-ES 统一接口（`GlobalOptimizer`），支持自动选择全局优化方法。

```
GlobalMethod.PSO → ParticleSwarmOptimizer
GlobalMethod.CMAES → CMAESOptimizer
```

**适用场景**：全局优化自动选型，跳出 L-BFGS 局部最优。

**文献**：Kennedy & Eberhart 1995 PSO；Hansen & Ostermeier 2001 CMA-ES

**代码位置**：`modules/optimizer/src/polaris_optimizer/global_opt.py`

---

### 优化器选择指南

| 场景 | 推荐优化器 | 理由 |
|------|-----------|------|
| 局部二阶优化（有梯度） | L-BFGS | 超线性收敛，适合 adjoint |
| 全局优化（无梯度） | CMA-ES | 自适应协方差，鲁棒 |
| 多目标 ≤3 | NSGA-II | 快速非支配排序 + 拥挤距离 |
| 多目标 >3 | NSGA-III | 参考点法多样性更好 |
| 快速全局探索 | PSO | 简单高效 |
| 拓扑优化 | Topology + HJ | 水平集 + 高阶格式 |
| 制造鲁棒性 | Robust | 蒙特卡洛公差扰动 |
| 参数化形状 | Shape Adjoint | 2 次仿真全梯度 |
| 像素化版图 | Density Adjoint | JAX autograd 二值化 |
| 迭代反馈 | Feedback Adapt | 违规驱动调整 |

---

## 第 6 章：量子光子算法

### 6.1 Clements 酉矩阵分解

#### 6.1.1 算法原理

任意 M×M 酉矩阵可分解为 O(M²) 个分束器 + 相移器（Clements 网格交替层）。

**分束器酉矩阵：**

```
U_BS(θ, φ) = [[cos(θ),           -e^{-iφ} sin(θ)],
              [e^{iφ} sin(θ),    cos(θ)]]

50:50 分束器: θ=π/4
```

**Clements 网格：** 交替层（偶数层从 0 开始，奇数层从 1 开始）左乘分束器，左乘酉保酉性，浮点误差 ~1e-15。

**4×4 mesh**：6 个分束器（O(4²/2)=8 个，对角线省略 2 个）。

#### 6.1.2 参数表

| 参数名 | 默认值 | 说明 | 来源 |
|--------|--------|------|------|
| `n_modes` | 4 | 模式数 M | Clements 2016 |
| `seed` | 42 | 随机种子（决定分束器角度与相移） | PoLaRIS 默认 |
| `_UNITARITY_TOL` | 1e-10 | 酉性校验阈值 | Clements 2016 |

#### 6.1.3 文献来源

- Clements et al., Optica 2016 https://opg.optica.org/optica/fulltext.cfm?uri=optica-3-12-1460
- Reck et al., PRL 1994 https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.73.58
- Aaronson & Arkhipov, STOC 2011 https://arxiv.org/abs/0910.4698
- Seron et al., Quantum 2024 https://arxiv.org/abs/2212.09537
- Knill, Laflamme, Milburn, Nature 2001 https://www.nature.com/articles/35051009

#### 6.1.4 代码位置

`modules/boson/src/polaris_boson/clements.py` — `clements_unitary()` 函数

---

### 6.2 HOM 干涉

#### 6.2.1 算法原理

两个光子输入 50:50 分束器，高斯波包重叠模型计算量子干涉可见度。

```
overlap²(θ) = exp(-θ² / (2σ²))        σ=1 归一化波包宽度
P_coinc(θ)  = 0.5 × (1 - overlap²(θ))  量子符合计数率
dip_depth(θ) = overlap²(θ) = 1 - P_coinc/0.5   HOM dip 深度
```

**物理含义：**
- θ=0 → 完全不可区分 → P_coinc=0, dip_depth=1.0（HOM dip，量子干涉）
- θ→∞ → 完全可分辨 → P_coinc=0.5, dip_depth=0.0（经典极限）

#### 6.2.2 参数表

| 参数名 | 默认值 | 说明 | 来源 |
|--------|--------|------|------|
| `theta` | 0.0 | 可分辨性/时间延迟参数 | HOM 1987 |
| `_CLASSICAL_COINCIDENCE` | 0.5 | 经典符合计数率 | HOM 1987 |
| `_WAVEPACKET_SIGMA_SQ` | 1.0 | 归一化高斯波包宽度平方 | HOM 1987 |

#### 6.2.3 文献来源

- Hong, Ou, Mandel, PRL 1987 https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.59.2044
- Bouwmeester et al., Springer 2000 §3.1 https://doi.org/10.1007/978-3-662-04209-0
- Sanaka et al., PRA 2001 https://doi.org/10.1103/PhysRevA.64.023817
- Knill, Laflamme, Milburn, Nature 2001 https://www.nature.com/articles/35051009
- Pan et al., PRL 1998 https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.80.3891

#### 6.2.4 代码位置

`modules/boson/src/polaris_boson/hom.py` — `hom_interference()` 函数

---

### 6.3 玻色采样

#### 6.3.1 算法原理

线性光学玻色采样，计算 n 个光子通过 M×M 酉网络后的输出概率分布。

**输出概率：**

```
P(S) = |Perm(U_S)|² / (s₁! · s₂! · ... · s_M!)

其中 U_S 为 U 的子矩阵（按输入/输出模式选取）
Perm() 为矩阵积和式（permanent）
```

**积和式计算（Glynn-Gray 公式）：**

```
Perm(A) = (1/2^{n-1}) · Σ_{δ∈{±1}^n} (Π δ_i) · Π_j (Σ_i δ_i · A_{ij})
```

复杂度：#P-hard（Aaronson-Arkhipov 2011），n 光子 M 模式需 O(M·2^n) 计算。

#### 6.3.2 参数表

| 参数名 | 默认值 | 说明 | 来源 |
|--------|--------|------|------|
| `unitary` | Clements 生成 | M×M 酉矩阵 | Aaronson-Arkhipov 2011 |
| `input_state` | [1,1,0,...] | 输入光子分布 | Aaronson-Arkhipov 2011 |

#### 6.3.3 文献来源

- Aaronson & Arkhipov, STOC 2011 https://arxiv.org/abs/0910.4698
- Glynn, Eur. J. Comb. 2010 https://doi.org/10.1016/j.ejc.2010.01.010
- Björklund 2012 https://arxiv.org/abs/1203.5687
- Knill, Laflamme, Milburn, Nature 2001 https://www.nature.com/articles/35051009

#### 6.3.4 代码位置

`modules/boson/src/polaris_boson/sampler.py` — `boson_sampling()` 函数
`modules/boson/src/polaris_boson/permanent.py` — `permanent_glynn_gray()` 函数

---

### 6.4 KLM 线性光学量子门

#### 6.4.1 算法原理

Knill-Laflamme-Milburn 方案，用线性光学元件 + 后选测量实现量子门。

**概率量子门**：通过光子探测后选实现纠缠，成功概率 < 1，需多次重复。

#### 6.4.2 文献来源

- Knill, Laflamme, Milburn, Nature 2001 https://www.nature.com/articles/35051009

#### 6.4.3 代码位置

`modules/klm/src/polaris_klm/gates.py`

---

### 6.5 BB84 QKD（量子密钥分发）

#### 6.5.1 算法原理

BB84 协议使用两组共轭基（直角基 ± / 对角基 ×）实现量子密钥分发。

```
1. Alice 随机选择基和比特发送光子
2. Bob 随机选择基测量
3. 公开比对基（不泄露比特值），保留相同基的结果
4. 误码率检测（窃听检测）
5. 隐私放大
```

#### 6.5.2 文献来源

- Bennett & Brassard 1984 "Quantum cryptography: Public key distribution and coin tossing"

---

## 第 7 章：验证算法

### 7.1 DRC（设计规则检查）

#### 7.1.1 算法原理

基于 SiEPIC EBeam PDK 的 18 条 DRC 规则集，使用 AABB（轴对齐包围盒）几何相交检测。

**规则分类：**
- 12 条 SiEPIC EBeam PDK 基础规则（几何 + 端口 + 密度）
- 6 条 P0 波导级规则（弯曲半径/宽度匹配/凹槽/Manhattan/封闭面积/交叉角度）
- 4 条 P1 跨层规则（间距/包围/延伸/禁止重叠）
- 3 条 P1 波导级规则（角度/锥形角/单模宽度）

#### 7.1.2 参数表（18 条规则真实阈值，从代码提取）

| 规则名 | 阈值 | 严重度 | 说明 | 来源 |
|--------|------|--------|------|------|
| MIN_SPACING | 1.0 μm | 1.0 | 器件最小间距（WG_MIN_SPACE） | SiEPIC EBeam PDK |
| MIN_WIDTH | 0.5 μm | 1.0 | 器件最小宽度（SLAB150_MIN_WIDTH） | SiEPIC EBeam PDK |
| MIN_HEIGHT | 0.4 μm | 1.0 | 器件最小高度（WG_MIN_WIDTH） | SiEPIC EBeam PDK |
| MIN_AREA | 0.1 μm² | 1.0 | 器件最小面积（WG_MIN_AREA） | SiEPIC EBeam PDK |
| BOUNDARY | 0.0 | 1.0 | 器件不超出画布边界 | PoLaRIS |
| NO_OVERLAP | 0.0 | 1.0 | 器件之间不能重叠 | SiEPIC EBeam PDK |
| PORT_ALIGNMENT | 10.0 μm | 0.5 | 端口坐标对齐容差 | SiEPIC EBeam PDK |
| PORT_DIRECTION | 0.0 | 0.8 | 端口方向合法（N/S/E/W） | SiEPIC EBeam PDK |
| PORT_CONNECTIVITY | 0.0 | 0.9 | 每个器件至少一个端口被连接 | SiEPIC EBeam PDK |
| PORT_FACING | 0.0 | 0.7 | 连接端口方向相对（E↔W / N↔S） | SiEPIC EBeam PDK |
| DENSITY_MAX | 80.0% | 0.6 | 布局密度上限（CMP 工艺均匀性） | Banerjee 2024 |
| DENSITY_MIN | 0.01% | 0.6 | 布局密度下限（分级阈值） | PoLaRIS |
| BEND_RADIUS_MIN | 5.0 μm | 1.0 | 最小弯曲半径 | SiEPIC/IMEC/AMF/LiDAR |
| WAVEGUIDE_WIDTH_MATCH | 0.0 | 0.9 | 连接两端波导宽度匹配 | SiEPIC Verification |
| MIN_NOTCH | 0.1 μm | 0.8 | 最小凹槽宽度（100nm） | KLayout notch() / FluxCore |
| WAVEGUIDE_MANHATTAN | 0.0 | 0.8 | 波导首末段必须 Manhattan | SiEPIC Verification |
| ENCLOSED_AREA_MIN | 0.01 μm² | 0.7 | 最小封闭面积（100nm×100nm） | KLayout area_check |
| CROSSING_ANGULAR | 90.0° | 0.7 | 波导交叉角度 90° 优选 | LiDAR 2.0 II-B3 |

**P1 跨层规则（4 条）：**

| 规则名 | 阈值 | 配对层 | 说明 | 来源 |
|--------|------|--------|------|------|
| SEPARATION | 1.0 μm | M1_HEATER | 跨层最小间距 | gdsfactory DRC |
| ENCLOSURE | 0.5 μm | M1_HEATER | VIAC 须被 M1_HEATER 包围 | SiEPIC PDK |
| EXTENSION | 0.2 μm | CONTACT | metal1 延伸超出 contact | Synopsys OptoDesigner |
| EXCLUSION | 0.0 μm | DEEPTRENCH | 禁止层重叠（零容忍） | FluxCore |

**P1 波导级规则（3 条）：**

| 规则名 | 阈值 | 说明 | 来源 |
|--------|------|------|------|
| ANGLE_LIMIT | [45°, 135°] | 路径段内角范围 | FluxCore |
| WAVEGUIDE_TAPER_ANGLE | 10.0° | 锥形波导半顶角上限 | Milton & Burns 1987 |
| SINGLEMODE_WIDTH | 1.0 μm | 单模波导宽度上限（V<2.405） | Snyder & Love 1983 |

#### 7.1.3 AABB 几何相交检测

```
两矩形 AABB 重叠判定:
NOT (x1+w1 <= x2 OR x2+w2 <= x1 OR y1+h1 <= y2 OR y2+h2 <= y1)
```

#### 7.1.4 文献来源

- SiEPIC EBeam PDK https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- SiEPIC-Tools Verification https://github-wiki-see.page/m/SiEPIC/SiEPIC-Tools/wiki/SiEPIC-Tools-Menu-descriptions
- Chrostowski & Hochberg 2015 CUP p.353 https://www.cambridge.org/core/search?searchField=isbn&searchTerms=1107007731
- KLayout DRC https://www.klayout.org/doc-qt5/manual/drc_runsets.html
- OpenDRC: He et al., DAC 2023 https://doi.org/10.1109/DAC56929.2023.10247734
- LiDAR 2.0 arXiv:2505.17239v1 https://arxiv.org/html/2505.17239v1
- FluxCore DRC https://www.fluxcoredynamics.com/docs/design-rules
- Milton & Burns 1987 JLT https://opg.optica.org/jlt/abstract.cfm?uri=jl-5-8-1079
- Snyder & Love 1983 §13.5 https://link.springer.com/book/10.1007/978-94-009-6875-2

#### 7.1.5 代码位置

`modules/drc/src/polaris_drc/rules.py` — `DEFAULT_DRC_RULES` 列表（18 条规则）
`modules/drc/src/polaris_drc/engine.py` — DRC 检查引擎

---

### 7.2 LVS（版图 vs 网表）

#### 7.2.1 算法原理

从 circuit dict 提取参考网表（器件名+类型 + 拓扑连接），与提取网表比对。

**比对方法：**

```
1. 器件集合差集: ref_devices - ext_devices → 缺失器件
                 ext_devices - ref_devices → 多余器件
2. 器件类型一致性: 同名器件类型必须匹配
3. 连接集合差集: ref_connections - ext_connections → 缺失连接
                 ext_connections - ref_connections → 多余连接
```

**不匹配类型（5 种）：**

| 类型 | 说明 |
|------|------|
| MISSING_DEVICE | 缺失器件 |
| EXTRA_DEVICE | 多余器件 |
| DEVICE_TYPE_MISMATCH | 器件类型不匹配 |
| MISSING_CONNECTION | 缺失连接 |
| EXTRA_CONNECTION | 多余连接 |

#### 7.2.2 文献来源

- KLayout LVS https://www.klayout.org/doc-qt5/manual/lvs.html
- SiEPIC EBeam PDK DEVREC 标准（器件识别层 layer 68）https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- Chrostowski & Hochberg 2015 CUP p.353
- gdsfactory PDK 文档 https://gdsfactory.github.io/gdsfactory/notebooks/09_pdk_import.html
- Luceda IPKISS https://www.lucedaphotonics.com/en/products/ipkiss
- Calibre nmLVS https://eda.sw.siemens.com/en-US/calibre/

#### 7.2.3 代码位置

`modules/lvs/src/polaris_lvs/compare.py` — `run_lvs_check()` 函数、`compare_netlists()` 函数

---

## 第 8 章：光电协同算法

### 8.1 寄生提取

#### 8.1.1 算法原理

从版图提取光电协同仿真的寄生参数（电容/电阻/电感）。

**寄生电容模型：**

```
C = C_unit × length = 1.0 pF/mm × length(mm)
```

**阻抗匹配：**

```
Z₀ = 50 Ω    （射频标准阻抗）
```

#### 8.1.2 参数表（从代码提取真实默认值）

| 参数名 | 默认值 | 说明 | 来源 |
|--------|--------|------|------|
| `DEFAULT_WAVELENGTH_UM` | 1.55 | 默认波长 (μm) | SiEPIC EBeam PDK 1550nm |
| `DEFAULT_WAVEGUIDE_LOSS_DB_CM` | 0.5 | SOI 波导损耗 (dB/cm) | Chrostowski 2015 §3.2 |
| `DEFAULT_LOAD_RESISTANCE_OHM` | 50.0 | 探测器负载电阻 (Ω) | 50Ω 射频标准 |
| `DEFAULT_DETECTOR_RESPONSIVITY` | 1.0 | 探测器响应度 (A/W) | Chrostowski 2015 §9.2 |
| `DEFAULT_MODULATOR_EFFICIENCY` | 0.1 | 调制器效率 (W/V²) | Chrostowski 2015 §8.4 |
| `DEFAULT_SPICE_TIMESTEP_S` | 1e-12 | SPICE 时间步 (s) | Lumerical INTERCONNECT |
| `DEFAULT_OPTICAL_TIMESTEP_S` | 1e-13 | 光子仿真器时间步 (s) | Lumerical INTERCONNECT |

#### 8.1.3 文献来源

- SiEPIC EBeam PDK https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- Chrostowski & Hochberg 2015 CUP §8/§9 https://www.cambridge.org/9781107083456
- Lumerical INTERCONNECT https://optics.ansys.com/hc/en-us/articles/49697869166611
- Ansys Lumerical CML Compiler https://optics.ansys.com/hc/en-us/sections/360005039133-CML-Compiler
- Simphony waveguide 模型 https://simphonyphotonics.readthedocs.io/

#### 8.1.4 代码位置

`modules/parasitic/src/polaris_parasitic/constants.py` — 默认物理参数
`modules/parasitic/src/polaris_parasitic/capacitance.py` — 寄生电容提取
`modules/parasitic/src/polaris_parasitic/resistance.py` — 寄生电阻提取

---

### 8.2 多物理场耦合

#### 8.2.1 算法原理

6 种多物理场耦合效应：

| 耦合类型 | 物理机制 | 影响参数 |
|----------|----------|----------|
| 电磁-光 | 波导模式与电磁场相互作用 | neff, 传输率 |
| 热-光 | 热光效应（dn/dT） | neff = n₀ + (dn/dT)×ΔT |
| 应力-光 | 弹光效应（光弹张量） | neff 修正 |
| 载流子-光 | 等离子体色散效应 | Δn = -Δn_e × (ΔN_e/N_e) |
| 电-光 | Pockels/Kerr 效应 | Δn = -½·n³·r·E |
| 热-载流子 | 热载流子产生/复合 | 载流子浓度变化 |

#### 8.2.2 文献来源

- Chrostowski & Hochberg 2015 CUP §8/§9 https://www.cambridge.org/9781107083456
- Soref & Bennett 1987 "Electrooptical effects in silicon" IEEE JQE
- Cocorullo et al. 1999 "Thermo-optic effect in silicon"

#### 8.2.3 代码位置

`modules/multiphysics/` — 多物理场耦合模块

---

## 附录：学术诚信声明（R02/R03）

### 数据来源

- 所有算法参数均从 `modules/*/src/polaris_*` 实际代码提取，禁止编造
- 所有公式标注文献 URL，来源可溯源
- benchmark 数据标注来源文件路径
- 无 fall-back：算法不存在即不写，不编造

### 物理常量来源

| 常量 | 值 | 来源 |
|------|-----|------|
| C0 | 2.99792458e8 m/s | NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/ |
| EPS0 | 8.8541878128e-12 F/m | NIST CODATA 2018 |
| MU0 | 1.25663706212e-6 H/m | NIST CODATA 2018（μ₀=4π×10⁻⁷） |
| n_Si @1.55μm | 3.476 | Soref 1993 IEEE JQE |
| n_SiO2 @1.55μm | 1.444 | Soref 1993 IEEE JQE |
| SOI 传播损耗 | 3.0 dB/cm | Soref 1993 IEEE Proc. 41(9) |

### 创新点标注

| 创新点 | 底层逻辑 | 支持理论 |
|--------|----------|----------|
| JAX autograd 替代手动伴随方程 | 反向模式 AD = 伴随方法（Giles & Pierce 2000） | Hughes 2018 ACS Photonics |
| DENSITY_MIN 自适应画布 | 根据器件总面积动态调整画布尺寸 | DREAMPlace TCAD 2020 |
| Euler 螺旋终点位移系数 0.6 | 90° clothoid 数值积分得位移/L ≈ 0.596 | Fresnel 积分数值解 |
| heavy-ball 低动量 0.3 | 适配 200nm 网格嘈杂 FoM 景观 | Smith 2017 arXiv:1711.00489 |
| EME 单模 Galerkin 投影 | Maxwell 界面连续性严格推导 | Collin 2001 §5.1 |
| 密度法 JAX autograd + 伴随共生 | 角谱法 + 模式重叠积分可微计算图 | Hughes 2018；Giles & Pierce 2000 |

---

> **文档结束** · PoLaRIS 算法手册 v6.1 · 2026-07
> 覆盖 8 章节、35+ 核心算法、120+ 文献来源
> 所有参数从实际代码提取，学术诚信可溯源（R02/R03）
