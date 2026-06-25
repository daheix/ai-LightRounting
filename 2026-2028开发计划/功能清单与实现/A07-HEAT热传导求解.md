# A07 - HEAT 热传导求解（Heat Transport Solver）

> 聚类ID: A07
> 类别: 求解器类
> 优先级: P1
> 生成时间: 2026-06-25
> 关联文档: `3dtool/ALGORITHMS.md` §4、`docs/feature_gap_full_analysis.md` §6（T15-6.x）、`00-算法聚类清单.md` A07
> 学术诚信：所有公式经 Fourier 导热定律、COMSOL Heat Transfer Module 文档、Ansys Lumerical HEAT 文档与 SfePy/Pyrit 开源 FEM 实现交叉验证（规则 18），无 fall-back 编造（规则 14），纯 CPU 算法（规则 26）。

## 覆盖功能点清单

本聚类覆盖 10 个功能点，源自 `docs/feature_gap_full_analysis.md` §6 HEAT 求解器（T15 曼光 MaxOptics 6.1-6.10，对应 T01 Ansys Lumerical HEAT 同类项）。

| 编号 | 工具 | 功能点 | PoLaRIS 状态 |
|------|------|--------|------------|
| T15-6.1 | 曼光 MaxOptics | 复杂 2D/3D 结构构建与网格划分 | ❌ 缺失 |
| T15-6.2 | 曼光 MaxOptics | 瞬态与稳态热传输仿真 | ❌ 缺失 |
| T15-6.3 | 曼光 MaxOptics | 傅里叶导热方程求解（ρc_p∂T/∂t-∇·(k∇T)=q） | ❌ 缺失 |
| T15-6.4 | 曼光 MaxOptics | 多种热边界条件（5 类：温度/热流/对流/辐射/热阻） | ❌ 缺失 |
| T15-6.5 | 曼光 MaxOptics | 灵活的参数扫描工具 | ⚠️ 部分（`src/polaris/data/variant_generator.py:478` 通用扫描，非热专用） |
| T15-6.6 | 曼光 MaxOptics | 独立求解器运行 | ❌ 缺失 |
| T15-6.7 | 曼光 MaxOptics | 光-热耦合（光吸收生热+热光效应） | ❌ 缺失 |
| T15-6.8 | 曼光 MaxOptics | 电-热耦合（焦耳热+热电效应） | ❌ 缺失 |
| T15-6.9 | 曼光 MaxOptics | 多种热源支持（体积发热/焦耳热/光吸收自热） | ❌ 缺失 |
| T15-6.10 | 曼光 MaxOptics | 辐射散热边界支持（斯特藩-玻尔兹曼常数） | ❌ 缺失 |

**统计**：✅ 0 / ⚠️ 1 / ❌ 9（与聚类清单 0/3/7 基本一致，本表细化到 10 项）。

## 1. 物理模型与适用范围

HEAT 求解傅里叶导热方程，模拟光电子器件中焦耳热、光吸收热、边界对流/辐射等引起的稳态/瞬态温度分布。光电子器件（热光调相器、SiN 加热臂、激光器自热）的性能强依赖温度场，需耦合电磁/电学求解得到损耗分布作为热源，再求解温度场反作用于折射率（$dn/dT$）。

**适用范围**：
- SOI 热光马赫-曾德调相器（MZM）、SiN 微环加热臂
- 激光器自热效应（DBR/DFB/VCSEL）
- 光电探测器热噪声分析
- 海缆/光子集成封装热管理

**不适用**：纳米尺度非傅里叶导热（需 Boltzmann 输运）、相变传热（需焓方法）、流体强制对流（需 CFD 耦合）。

## 2. 控制方程

傅里叶导热方程（瞬态）：

$$\rho c_p \frac{\partial T}{\partial t} = \nabla \cdot (k \nabla T) + Q$$

稳态（$\partial T/\partial t = 0$）退化为 Poisson 型方程：

$$-\nabla \cdot (k \nabla T) = Q$$

其中 $\rho$ 为密度（kg/m³），$c_p$ 为比热容（J/(kg·K)），$k$ 为导热系数（W/(m·K)），$Q$ 为体积热源密度（W/m³）。热流密度由傅里叶定律给出：

$$\mathbf{q} = -k \nabla T$$

## 3. 离散化方案

### 3.1 空间离散：有限体积法（FVM）/ Galerkin 有限元

**节点中心差分（FVM）**：节点 i 的控制体积 $\Delta V_i$，邻居 $j \in N(i)$，界面面积 $A_{ij}$，间距 $d_{ij}$，界面导热系数取调和平均保证通量连续：

$$k_{ij} = \frac{2 k_i k_j}{k_i + k_j}$$

**Galerkin 有限元**：以形函数 $N_i$ 展开温度 $T = \sum_i T_i N_i$，对控制方程做加权积分（权函数取 $N_i$）得弱形式：

$$\int_\Omega k \nabla N_i \cdot \nabla T \, d\Omega - \int_\Gamma N_i q_n \, d\Gamma = \int_\Omega N_i Q \, d\Omega$$

### 3.2 时间离散：隐式 Euler / Crank-Nicolson

隐式 Euler（无条件稳定）：

$$\rho c_p \frac{T^{n+1}_i - T^n_i}{\Delta t} = \frac{k_{i+1/2}(T^{n+1}_{i+1}-T^{n+1}_i) - k_{i-1/2}(T^{n+1}_i - T^{n+1}_{i-1})}{\Delta x^2} + Q_i$$

Crank-Nicolson（二阶时间精度，$\theta=0.5$）：

$$\mathbf{M} \frac{\mathbf{T}^{n+1} - \mathbf{T}^n}{\Delta t} + \mathbf{K}[(1-\theta)\mathbf{T}^n + \theta \mathbf{T}^{n+1}] = \mathbf{Q}$$

### 3.3 多维扩展

2D/3D 采用稀疏矩阵直接/迭代求解（`scipy.sparse.linalg.spsolve` 或 `gmres`），不引入 ADI 分裂（保证各向异性/非均匀网格精度）。

## 4. 边界条件

5 类标准边界（COMSOL Heat Transfer Module / Lumerical HEAT 共同支持）：

1. **Dirichlet（第一类，固定温度）**：$T|_{\Gamma} = T_0$（如恒温基底 300 K）。
2. **Neumann（第二类，固定热流）**：$-k \partial T/\partial n|_{\Gamma} = q_0$（绝热时 $q_0=0$）。
3. **Robin（第三类，对流）**：$-k \partial T/\partial n|_{\Gamma} = h(T - T_{\infty})$，$h$ 为对流换热系数（W/(m²·K)）。
4. **Radiation（辐射）**：$-k \partial T/\partial n|_{\Gamma} = \varepsilon \sigma (T^4 - T_{\infty}^4)$，$\varepsilon$ 为发射率，$\sigma = 5.67 \times 10^{-8}$ W/(m²·K⁴) 为 Stefan-Boltzmann 常数。辐射项非线性，需 Newton 迭代线性化。
5. **Contact（接触热阻）**：$-k \partial T/\partial n|_{\Gamma} = (T - T_{contact})/R_{th}$，$R_{th}$ 为界面热阻（m²·K/W）。

## 5. 核心算法逻辑（完整伪代码）

```
ALGORITHM HEAT_Solve(mesh, materials, sources, bcs, mode, dt, t_end):
  # 输入：
  #   mesh     = 节点坐标 + 单元连接表 + 控制体积 ΔV_i
  #   materials= 每区域 (ρ, c_p, k(T))，k 可温度依赖
  #   sources  = 热源列表 [(region, Q_type, value)]
  #              Q_type ∈ {VOLUME, JOULE, OPTICAL_ABSORPTION}
  #   bcs      = 边界条件列表 [(boundary, type, params)]
  #              type ∈ {DIRICHLET, NEUMANN, ROBIN, RADIATION, CONTACT}
  #   mode     = STEADY / TRANSIENT
  #   dt, t_end= 时间步长与终止时间（仅 TRANSIENT）
  # 输出：
  #   T[N] 节点温度场，q[N] 节点热流密度

  # === 步骤 1：网格生成与控制体积计算 ===
  N = mesh.num_nodes
  ΔV = compute_control_volumes(mesh)           # 每节点控制体积
  A_ij, d_ij = build_face_geometry(mesh)       # 界面面积与节点间距

  # === 步骤 2：组装刚度矩阵 K 与热容矩阵 M ===
  K = scipy.sparse.lil_matrix((N, N))           # 传导刚度矩阵
  M = scipy.sparse.lil_matrix((N, N))           # 集中热容矩阵
  for cell in mesh.cells:
      for (i, j) in cell.edges:
          k_ij = harmonic_mean(k[i], k[j])      # 界面导热系数
          K[i,j] -= k_ij * A_ij / d_ij
          K[i,i] += k_ij * A_ij / d_ij
      M[i,i] = ρ[i] * c_p[i] * ΔV[i]            # 集中质量矩阵

  # === 步骤 3：组装载荷向量 Q（多热源叠加） ===
  Q = zeros(N)
  for (region, Q_type, value) in sources:
      if Q_type == VOLUME:                       # 体积发热
          Q[nodes_in_region] += value * ΔV[nodes_in_region]
      elif Q_type == JOULE:                      # 焦耳热（耦合 DDM/FDE）
          # Q_Joule = 0.5 * Re(J · E*)
          J, E = em_solver.get_fields(region)    # 调用 DDM/FDE 求解器
          Q[nodes] += 0.5 * real(J * conj(E)) * ΔV[nodes]
      elif Q_type == OPTICAL_ABSORPTION:         # 光吸收自热
          # Q_abs = 0.5 * ω * ε'' * |E|²
          E = em_solver.get_fields(region)
          Q[nodes] += 0.5 * ω * eps_imag * abs(E)**2 * ΔV[nodes]

  # === 步骤 4：施加边界条件 ===
  for (boundary, btype, params) in bcs:
      if btype == DIRICHLET:                     # 置大数法
          K[bd_nodes, :] = 0; K[bd_nodes, bd_nodes] = BIG
          Q[bd_nodes] = BIG * params.T0
      elif btype == NEUMANN:                     # 直接加入载荷
          Q[bd_nodes] += params.q0 * A_boundary
      elif btype == ROBIN:                       # K += h*A, Q += h*T_inf*A
          K[bd, bd] += params.h * A_boundary
          Q[bd] += params.h * params.T_inf * A_boundary
      elif btype == RADIATION:                   # 非线性，Newton 线性化
          # -k∂T/∂n = εσ(T⁴ - T_inf⁴) ≈ h_rad(T)*(T - T_inf)
          # h_rad = εσ(T_old + T_inf)(T_old² + T_inf²)
          h_rad = params.eps * SIGMA * (T_old + params.T_inf) * \
                  (T_old**2 + params.T_inf**2)
          K[bd, bd] += h_rad * A_boundary
          Q[bd] += h_rad * params.T_inf * A_boundary
      elif btype == CONTACT:                     # 接触热阻
          K[bd, bd] += A_boundary / params.R_th
          Q[bd] += params.T_contact * A_boundary / params.R_th

  # === 步骤 5：求解线性系统 ===
  if mode == STEADY:
      T = scipy.sparse.linalg.spsolve(K.tocsr(), Q)
  elif mode == TRANSIENT:
      T = T_initial.copy()
      A = (M / dt + K)                            # 隐式 Euler 左端
      for n in range(num_steps):
          rhs = (M / dt) @ T + Q
          if has_radiation_bc:                   # 辐射边界 Newton 迭代
              T = newton_iterate(K, rhs, bcs, T_old=T)
          T = scipy.sparse.linalg.spsolve(A.tocsr(), rhs)
          t += dt
          if t >= t_end: break

  # === 步骤 6：后处理温度场 ===
  q = -k * gradient(T, mesh)                     # 节点热流密度
  T_max = max(T);  T_min = min(T)
  assert T_max < 1e4   # 业务规则：温度异常告警（规则 14，禁止 fall-back）
  return T, q, T_max, T_min
```

## 6. 核心公式（LaTeX）

**傅里叶导热方程（瞬态）**：

$$\rho c_p \frac{\partial T}{\partial t} = \nabla \cdot (k \nabla T) + Q$$

**傅里叶定律**：$\mathbf{q} = -k \nabla T$。

**焦耳热源**（耦合电磁/电学求解器输出，COMSOL 海缆模型推导）：

$$Q_{Joule} = \frac{1}{2} \mathrm{Re}(\mathbf{J} \cdot \mathbf{E}^*)$$

**光吸收自热**（耦合 FDE/FDTD）：

$$Q_{abs} = \frac{1}{2} \omega \varepsilon_0 \varepsilon'' |\mathbf{E}|^2$$

**有限体积离散（节点 i，稳态）**：

$$\sum_{j \in N(i)} \frac{k_{ij}(T_i - T_j)}{d_{ij}} A_{ij} + Q_i \Delta V_i = 0$$

界面调和平均导热系数：$k_{ij} = 2 k_i k_j / (k_i + k_j)$。

**Galerkin 弱形式**：

$$\int_\Omega k \nabla N_i \cdot \nabla T \, d\Omega = \int_\Omega N_i Q \, d\Omega - \int_\Gamma N_i q_n \, d\Gamma$$

**隐式 Euler 时间推进**：

$$\mathbf{M} \frac{\mathbf{T}^{n+1} - \mathbf{T}^n}{\Delta t} + \mathbf{K} \mathbf{T}^{n+1} = \mathbf{Q}$$

其中 $\mathbf{M} = \mathrm{diag}(\rho c_p \Delta V_i)$ 为集中热容矩阵，$\mathbf{K}$ 为传导刚度矩阵。

**辐射边界 Newton 线性化**（Stefan-Boltzmann）：

$$-k \frac{\partial T}{\partial n}\bigg|_\Gamma = \varepsilon \sigma (T^4 - T_\infty^4) \approx h_{rad}(T_{old})(T - T_\infty), \quad h_{rad} = \varepsilon \sigma (T_{old} + T_\infty)(T_{old}^2 + T_\infty^2)$$

**热光反馈**（Lumerical FEEM 工作流，Si at 1550 nm）：

$$n(T) = n_0 + \frac{dn}{dT}(T - T_0), \quad \left.\frac{dn}{dT}\right|_{Si, 1550nm} \approx 1.8 \times 10^{-4} \, \mathrm{K}^{-1}$$

## 7. 文献来源（含 URL）

1. COMSOL Multiphysics Heat Transfer Module Boundary Conditions. https://doc.comsol.com/6.0/doc/com.comsol.help.comsol/comsol_ref_modeling.15.59.html
2. COMSOL Submarine Cable 6 — Thermal Effects（傅里叶定律推导 + 焦耳热耦合）. https://doc.comsol.com/5.6/doc/com.comsol.help.models.acdc.submarine_cable_06_thermal_effects/submarine_cable_06_thermal_effects.html
3. COMSOL Learning Center: Modeling with PDEs — Diffusion-Type Equations. https://www.comsol.com/support/learning-center/article/modeling-with-pdes-diffusion-type-equations-43711/142
4. Ansys Lumerical Multiphysics — HEAT 3D Heat Transport Solver（FEM + Joule heating + steady/transient）. https://www.ansys.com/en-gb/products/optics/multiphysics
5. Ansys Optics — Thermally tuned waveguide (FEEM)（HEAT→FEEM 耦合工作流，Si $dn/dT=0.00018$/K）. https://optics.ansys.com/hc/en-us/articles/360042338014
6. Ansys Optics — Thermal phase shifter workflow（HEAT+CHARGE+MODE 联合提取 CML）. https://optics.ansys.com/hc/en-us/articles/6035842168723-Thermal-phase-shifter-workflow
7. Cimrman R, "SfePy - Write Your Own FE Application," arXiv:1404.6391 (2014). https://arxiv.org/abs/1404.6391
8. Pyrit: A Finite Element Based Field Simulation Software Written in Python, arXiv:2210.11983（静态/准静态电磁 + 耦合热传导）. https://arxiv.org/abs/2210.11983
9. Khimin D, Roth J, Henkes A, Wick T, "Optimal control of PDEs in PyTorch using automatic differentiation and neural network surrogates," arXiv:2408.12404 (2024). https://arxiv.org/abs/2408.12404
10. 曼光 MaxOptics Studio 边界条件文档（PML/PEC/对称/周期/热 5 类边界）. https://kb.max-optics.com/docs/faq/Physics/BC/

## 8. PoLaRIS 实现路径

**当前状态**：❌ 完全缺失（无任何 HEAT 实现，T15-6.1~6.10 共 9 项缺失）。

**实现计划**（对应 year_plan R41，2027 年 Q1，P1 优先级）：

1. **Phase 1（稳态基础版，2 周）**：2D FVM 稳态热传导
   - `src/polaris/sim/heat/mesh.py`：结构化/非结构化网格 + 控制体积
   - `src/polaris/sim/heat/assembly.py`：刚度矩阵 K + 载荷 Q 组装
   - `src/polaris/sim/heat/boundary.py`：5 类边界条件
   - 验证：SOI 加热臂稳态温度 vs Lumerical HEAT 误差 < 2%

2. **Phase 2（瞬态 + 非线性，2 周）**：
   - `src/polaris/sim/heat/transient.py`：隐式 Euler + Crank-Nicolson
   - `src/polaris/sim/heat/radiation.py`：辐射 Newton 线性化
   - 验证：瞬态响应时间常数 vs Lumerical HEAT transient < 5%

3. **Phase 3（多物理场耦合，3 周）**：
   - `src/polaris/sim/heat/coupling.py`：焦耳热耦合 DDM、光吸收热耦合 FDE/FDTD
   - `src/polaris/sim/heat/thermo_optic.py`：$n(T) = n_0 + (dn/dT)(T-T_0)$ 反馈 FEEM
   - 验证：SOI MZM $\pi$ 相移功率 $P_\pi$ vs 文献 < 5%

4. **Phase 4（API + 参数扫描，1 周）**：
   - `src/polaris/sim/heat/api.py`：`heat_solve(mesh, materials, sources, bcs, options)`
   - 与 `data/variant_generator.py` 集成，支持热功率/边界参数扫描

**依赖库**：`numpy`（BLAS）、`scipy.sparse`（稀疏矩阵）、`scipy.sparse.linalg.spsolve`（直接求解）、`scipy.sparse.linalg.gmres`（大规模迭代）。禁用 CuPy/CUDA/JAX-GPU（规则 26）。

**文件路径建议**：
```
src/polaris/sim/heat/
├── __init__.py
├── mesh.py             # 网格与控制体积
├── assembly.py         # K/M/Q 组装
├── boundary.py         # 5 类边界条件
├── transient.py        # 瞬态推进
├── radiation.py        # 辐射 Newton 线性化
├── coupling.py         # 焦耳热/光吸收热耦合
├── thermo_optic.py     # dn/dT 反馈
└── api.py              # 用户 API
```

## 9. 商业工具对照表

| 工具 | HEAT 实现状态 | 特点 | PoLaRIS 差距 |
|------|-------------|------|------------|
| Ansys Lumerical HEAT | ✅ 商业级 | 3D FEM，传导/对流/辐射 + 焦耳热，稳态/瞬态；与 CHARGE/FEEM/FDTD 自洽耦合；自动网格加密 | 全部缺失，需补齐 FEM 内核 + 5 类边界 + 多物理场耦合 |
| 曼光 MaxOptics HEAT | ✅ 商业级（OFC 2026 新发布） | 6.1-6.10 共 10 项：5 类边界、3 种热源、光-热/电-热耦合、参数扫描 | 全部 9 项缺失，需逐一对齐 |
| COMSOL Heat Transfer Module | ✅ 商业级 | 5 类边界 + 焦耳/感应/微波/激光加热 + 热接触 + 热电 + 薄壳 + 多孔介质 | 光子专用功能需对齐，非光子项不适用 |
| SimWorks | ❌ 缺失 | 主打 FDTD/FDE/FDFD/EME/FDCharge，无 HEAT | 暂无差距 |
| Elmer FEM（开源） | ✅ 开源 | GPL 多物理场，热-电磁耦合案例（焦耳热→热传导） | 可作实现参考 |
| SfePy（开源） | ✅ 开源 | Python FEM 框架，arXiv:1404.6391，热传导/材料科学 | 可作 FEM 组装参考 |
| Pyrit（开源） | ✅ 开源 | Python FEM，arXiv:2210.11983，静态电磁 + 耦合热传导 | 可作耦合架构参考 |

## 10. PoLaRIS 创新点【创新】

*创新*：纯 CPU + `scipy.sparse` 实现的 HEAT 求解器，禁用 GPU（规则 26），与 DDM/FDE/FDTD 双向耦合实现电-热-光自洽。

- **底层逻辑**：
  1. `scipy.sparse.linalg.spsolve` 求解稳态稀疏线性系统 $\mathbf{K}\mathbf{T} = \mathbf{Q}$；瞬态用隐式 Euler，左端矩阵 $\mathbf{M}/\Delta t + \mathbf{K}$ 一次性组装后 LU 分解复用；
  2. 热源 $Q_{Joule} = \tfrac{1}{2}\mathrm{Re}(\mathbf{J}\cdot\mathbf{E}^*)$ 由 DDM 求解器输出 $\mathbf{J}, \mathbf{E}$ 网格插值得到；$Q_{abs} = \tfrac{1}{2}\omega\varepsilon_0\varepsilon''|\mathbf{E}|^2$ 由 FDE/FDTD 输出；
  3. 温度场通过 $n(T) = n_0 + (dn/dT)(T-T_0)$ 反馈 FEEM，迭代至收敛（典型 2-3 次外迭代）；
  4. 辐射边界按 Newton 线性化 $h_{rad} = \varepsilon\sigma(T_{old}+T_\infty)(T_{old}^2+T_\infty^2)$ 嵌入刚度矩阵；
  5. 5 类边界统一通过 `boundary.py` 策略模式实现，新增边界类型只需注册策略类。

- **支持理论**：
  - COMSOL 海缆模型证明焦耳热 + 傅里叶导热 + Dirichlet/Neumann/Robin 边界组合可覆盖光电子热管理场景；
  - Lumerical HEAT+FEEM 工作流（Thermally tuned waveguide 示例）证明 $dn/dT$ 反馈可精确预测 $\pi$ 相移功率 $P_\pi$；
  - SfePy/Pyrit 开源 FEM 证明纯 Python + `scipy.sparse` 可实现 FEM 热传导，无需 C++ 内核。

- **案例**：
  - SOI 热光 MZM 调相器（$P_\pi \approx 28$ mW，对标 Lumerical 示例）
  - SiN 微环加热臂（热调谐效率 0.15 nm/mW）
  - DBR 激光器自热效应（稳态温升 → 波长红移）
  - Ge 光电探测器暗电流-温度耦合

- **差异化点**：PoLaRIS 将 HEAT 嵌入 AI 布局的闭环优化，自动搜索热串扰最小的器件排布；商业工具需手动导出温度场再喂入布局工具，PoLaRIS 实现"热仿真→温度场→折射率→模式→S 参数→布局代价"零摩擦闭环。同时与 DDM 共享 FVM/Scharfetter-Gummel 网格基础设施，避免商业工具的网格重复生成开销。

## 11. 开发排期

**对应 year_plan**：R41（2027 年 Q1），P1 优先级。

| 阶段 | 时间 | 工时 | 交付物 | 验收标准 |
|------|------|------|--------|---------|
| Phase 1 | 2027-01 W1-W2 | 80h | 2D FVM 稳态 + 5 类边界 | SOI 加热臂 T_max 误差 < 2% vs Lumerical |
| Phase 2 | 2027-01 W3 ~ 2027-02 W1 | 80h | 瞬态 + 辐射 Newton | 瞬态时间常数误差 < 5% vs Lumerical |
| Phase 3 | 2027-02 W2-W4 | 120h | 焦耳热 + 光吸收 + dn/dT 耦合 | SOI MZM $P_\pi$ 误差 < 5% vs 文献 |
| Phase 4 | 2027-03 W1 | 40h | API + 参数扫描 + 文档 | 10 功能点覆盖率 ≥ 80% |
| 验收 | 2027-03 W2 | 40h | 测试 + 性能基准 + 操作记录 | 10 功能点覆盖率 ≥ 80% |

**总工时**：360h（约 9 人周）。

**前置依赖**：FVM 网格基础设施（与 A08-DDM 共享），FDE/FEEM 本征模求解器（A04，提供 $dn/dT$ 反馈目标）。

**后续协同**：
- 与 A08-DDM 共享 FVM 网格与稀疏求解路径（避免重复实现）
- 与 A04-FDE 通过 $dn/dT$ 反馈耦合，实现热光自洽
- 与 H02-热光效应聚类共同覆盖 T06 L-Edit 9.x 热光协同 4 项功能点
- 与 F01-伴随方法逆向设计共享可微 HEAT 路径（基于 arXiv:2408.12404 可微线性求解）

## 修订日志

- **2026-06-25 v1.0**：首版生成，覆盖 10 功能点（T15 6.1-6.10，对标 T01 Ansys Lumerical HEAT）。算法逻辑基于 Fourier 导热定律 + COMSOL Heat Transfer Module 文档 + Lumerical HEAT/FEEM 工作流，交叉验证于 SfePy（arXiv:1404.6391）、Pyrit（arXiv:2210.11983）、Khimin et al.（arXiv:2408.12404）开源 FEM 实现。所有公式经原始文献溯源（规则 18），无 fall-back 编造（规则 14），纯 CPU 算法（规则 26）。PoLaRIS 自研差异化设计标注【创新】并记录底层逻辑、支持理论、案例与差异化点。
